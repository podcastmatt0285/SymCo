"""
wma.py — Recursive Weighted Moving Average cost-basis ledger.

Tracks the actual per-unit cost of every (player, item_type) pair.
Updated on every acquisition:
  - Market purchase   (market.py :: execute_trade)
  - WCE borrow        (banks/brokerage_firm.py :: borrow_commodity)
  - Production output (business.py :: process_business_tick)

Core blend formula:
    new_wma = (old_wma × old_qty + unit_cost × new_qty) / (old_qty + new_qty)

CapEx amortization: startup_cost is spread over CAPEX_AMORTIZE_UNITS units.
Subsidy:           city bank pays PRODUCTION_SUBSIDY_RATE × gross_batch_cost
                   back to the producer — reduces effective net cost.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Integer, String, Float, DateTime, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base

from database import engine, SessionLocal

Base = declarative_base()

# ── tuneable constants ──────────────────────────────────────────────────────
CAPEX_AMORTIZE_UNITS    = 10_000   # units over which startup_cost is amortised
PRODUCTION_SUBSIDY_RATE = 0.0475   # 4.75 % city-bank refund on batch cost
# ────────────────────────────────────────────────────────────────────────────


def get_db():
    return SessionLocal()


# ==========================
# MODEL
# ==========================

class InventoryCostLedger(Base):
    """
    Running WMA cost basis for every (player, item_type) pair.

    wma_cost  — current weighted-average acquisition cost per unit
    qty_basis — quantity used in the WMA denominator; decreases as inventory
                is consumed, but wma_cost is preserved until the next buy.
    """
    __tablename__ = "inventory_cost_ledger"
    __table_args__ = (
        UniqueConstraint("player_id", "item_type", name="uq_icl_player_item"),
    )

    id           = Column(Integer, primary_key=True, index=True, autoincrement=True)
    player_id    = Column(Integer, index=True, nullable=False)
    item_type    = Column(String,  index=True, nullable=False)
    wma_cost     = Column(Float,   default=0.0)   # WMA cost per unit
    qty_basis    = Column(Float,   default=0.0)   # qty in WMA denominator
    last_updated = Column(DateTime, default=datetime.utcnow)


# ==========================
# CORE WMA OPERATIONS
# ==========================

def update_wma(player_id: int, item_type: str,
               acquired_qty: float, unit_cost: float) -> None:
    """
    Blend a new acquisition into the running WMA.
    new_wma = (old_wma × old_qty + unit_cost × acquired_qty) / (old_qty + acquired_qty)
    """
    if acquired_qty <= 0 or unit_cost < 0:
        return
    db = get_db()
    try:
        row = (
            db.query(InventoryCostLedger)
            .filter_by(player_id=player_id, item_type=item_type)
            .with_for_update()
            .first()
        )
        if row is None:
            db.add(InventoryCostLedger(
                player_id=player_id,
                item_type=item_type,
                wma_cost=unit_cost,
                qty_basis=acquired_qty,
            ))
        else:
            old_qty   = row.qty_basis or 0.0
            total_qty = old_qty + acquired_qty
            row.wma_cost  = (row.wma_cost * old_qty + unit_cost * acquired_qty) / total_qty
            row.qty_basis = total_qty
            row.last_updated = datetime.utcnow()
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[WMA] update_wma error ({player_id}, {item_type}): {e}")
    finally:
        db.close()


def consume_wma(player_id: int, item_type: str, consumed_qty: float) -> None:
    """
    Reduce qty_basis when items leave inventory.
    Preserves wma_cost — the average is kept for the next incoming batch.
    """
    if consumed_qty <= 0:
        return
    db = get_db()
    try:
        row = (
            db.query(InventoryCostLedger)
            .filter_by(player_id=player_id, item_type=item_type)
            .first()
        )
        if row:
            row.qty_basis    = max(0.0, (row.qty_basis or 0.0) - consumed_qty)
            row.last_updated = datetime.utcnow()
            db.commit()
    finally:
        db.close()


def get_wma(player_id: int, item_type: str) -> float:
    """Return current WMA cost per unit, or 0.0 if no record exists."""
    db = get_db()
    try:
        row = (
            db.query(InventoryCostLedger)
            .filter_by(player_id=player_id, item_type=item_type)
            .first()
        )
        return row.wma_cost if row else 0.0
    finally:
        db.close()


def get_all_wma(player_id: int) -> dict:
    """
    Return {item_type: {"wma_cost": float, "qty_basis": float}}
    for every item with a WMA record for this player.
    """
    db = get_db()
    try:
        rows = db.query(InventoryCostLedger).filter_by(player_id=player_id).all()
        return {
            r.item_type: {"wma_cost": r.wma_cost, "qty_basis": r.qty_basis}
            for r in rows
        }
    finally:
        db.close()


# ==========================
# PRODUCTION COST BASIS
# ==========================

def compute_production_cost_basis(player_id: int,
                                  biz_config: dict,
                                  line: dict) -> dict:
    """
    Compute the WMA-based cost basis for one production line.

    Applies (in the same order as the game tick):
      1. Land efficiency  — degradation raises effective wage
      2. City buffs       — output_multiplier, wage_multiplier, input_multiplier
      3. Exec bonuses     — production (output), wages, supply_chain_opt (input cost)
      4. City subsidy     — 4.75 % refund on gross batch cost
      5. CapEx            — startup_cost / CAPEX_AMORTIZE_UNITS per output unit

    Returns a dict with keys:
        unit_cost, operational_unit_cost, capex_per_unit,
        batch_cost_gross, batch_cost_net, actual_wage, gross_input_cost,
        actual_output_qty, inputs (list), has_all_wma, missing_wma_items,
        subsidy_rate, eff_pct,
        exec_output_bonus, exec_wage_reduction, exec_input_cost_reduction
    """
    from database import SessionLocal as _SL
    db = _SL()
    try:
        # ── Land efficiency ──────────────────────────────────────────────────
        eff_pct = 100.0
        try:
            from business import Business
            from land import LandPlot
            biz_rows = db.query(Business).filter(
                Business.owner_id    == player_id,
                Business.is_active   == True,
                Business.land_plot_id.isnot(None),
            ).all()
            plot_ids = [b.land_plot_id for b in biz_rows]
            if plot_ids:
                plots = db.query(LandPlot).filter(LandPlot.id.in_(plot_ids)).all()
                if plots:
                    eff_pct = sum(p.efficiency for p in plots) / len(plots)
        except Exception:
            pass
        eff_multiplier = max(0.5, eff_pct / 100.0)

        # ── City buffs ───────────────────────────────────────────────────────
        city_output_mult = city_wage_mult = city_input_mult = 1.0
        try:
            from city_projects import get_city_production_buffs
            cb = get_city_production_buffs(player_id)
            city_output_mult = cb.get("output_multiplier", 1.0)
            city_wage_mult   = cb.get("wage_multiplier",   1.0)
            city_input_mult  = cb.get("input_multiplier",  1.0)
        except Exception:
            pass

        # ── Exec bonuses ─────────────────────────────────────────────────────
        exec_output_bonus = exec_wage_reduction = exec_input_cost_reduction = 0.0
        try:
            from executive import get_player_job_bonus, get_specific_ability_bonus
            exec_output_bonus         = get_player_job_bonus(db, player_id, "production")
            exec_wage_reduction       = get_player_job_bonus(db, player_id, "wages")
            exec_input_cost_reduction = get_specific_ability_bonus(db, player_id, "supply_chain_opt")
        except Exception:
            pass

        # ── Recipe base values ───────────────────────────────────────────────
        base_wage       = biz_config.get("base_wage_cost", 0.0)
        base_output_qty = line.get("output_qty", 1)
        inputs          = line.get("inputs", [])
        startup_cost    = biz_config.get("startup_cost", 0.0)

        # ── Step 1: Adjusted wage ────────────────────────────────────────────
        # Efficiency < 1 ⇒ wages rise (business runs less efficiently).
        actual_wage = (
            base_wage
            / eff_multiplier
            * city_wage_mult
            * (1.0 - min(0.95, exec_wage_reduction))
        )

        # ── Step 2: Gross batch cost — WMA prices with theoretical fallback ──
        # Priority: player's WMA record → theoretical (vertical integration) → 0
        # Only flag an input as "missing" if there is truly no price source at all.
        wma_data = get_all_wma(player_id)
        try:
            from production_costs import get_calculator
            _calc = get_calculator()
            theo_costs = _calc.get_all_costs()
        except Exception:
            theo_costs = {}

        input_breakdown  = []
        gross_input_cost = 0.0
        missing_wma      = []   # inputs with NO price source at all

        for req in inputs:
            item     = req["item"]
            base_qty = req["quantity"]
            eff_qty  = max(1, round(base_qty * city_input_mult))
            wma      = wma_data.get(item, {}).get("wma_cost", 0.0)
            has_wma  = wma > 0

            if has_wma:
                price_used = wma
                price_source = "wma"
            else:
                theo = theo_costs.get(item, 0.0)
                if theo > 0:
                    price_used   = theo
                    price_source = "theoretical"
                else:
                    price_used   = 0.0
                    price_source = "unknown"
                    missing_wma.append(item)

            # supply_chain_opt lowers effective input cost (not quantity)
            eff_price = price_used * (1.0 - min(0.95, exec_input_cost_reduction))
            line_cost = eff_qty * eff_price
            gross_input_cost += line_cost

            input_breakdown.append({
                "item":          item,
                "base_qty":      base_qty,
                "effective_qty": eff_qty,
                "wma_cost":      wma,
                "price_used":    price_used,
                "price_source":  price_source,   # "wma" | "theoretical" | "unknown"
                "effective_cost": eff_price,
                "line_cost":     line_cost,
                "has_wma":       has_wma,
            })

        gross_batch_cost = gross_input_cost + actual_wage

        # ── Step 3: City production subsidy ──────────────────────────────────
        net_batch_cost = gross_batch_cost * (1.0 - PRODUCTION_SUBSIDY_RATE)

        # ── Step 4: Actual output qty ─────────────────────────────────────────
        actual_output_qty = max(1, round(
            base_output_qty * city_output_mult * (1.0 + exec_output_bonus)
        ))

        # ── Step 5: Unit cost + CapEx amortisation ───────────────────────────
        op_unit_cost   = net_batch_cost / actual_output_qty if actual_output_qty > 0 else 0.0
        capex_per_unit = startup_cost / CAPEX_AMORTIZE_UNITS
        true_unit_cost = op_unit_cost + capex_per_unit

        theo_count = sum(1 for i in input_breakdown if i["price_source"] == "theoretical")
        return {
            "unit_cost":               true_unit_cost,
            "operational_unit_cost":   op_unit_cost,
            "capex_per_unit":          capex_per_unit,
            "batch_cost_gross":        gross_batch_cost,
            "batch_cost_net":          net_batch_cost,
            "actual_wage":             actual_wage,
            "gross_input_cost":        gross_input_cost,
            "actual_output_qty":       actual_output_qty,
            "inputs":                  input_breakdown,
            # has_all_wma: True only when every input price came from the player's own WMA ledger
            "has_all_wma":             len(missing_wma) == 0 and theo_count == 0,
            # has_all_priced: True when every input has SOME price (WMA or theoretical)
            "has_all_priced":          len(missing_wma) == 0,
            "theoretical_fallback_count": theo_count,
            "missing_wma_items":       missing_wma,
            "subsidy_rate":            PRODUCTION_SUBSIDY_RATE,
            "eff_pct":                 eff_pct,
            "exec_output_bonus":       exec_output_bonus,
            "exec_wage_reduction":     exec_wage_reduction,
            "exec_input_cost_reduction": exec_input_cost_reduction,
        }
    finally:
        db.close()


def get_player_cost_basis_items(player_id: int) -> list:
    """
    For every producible item, compute the WMA cost basis for this player.
    Returns a list of dicts sorted cheapest-first.
    Each dict: item_key, name, category, unit_cost, has_all_wma, missing_wma,
               business, business_key, detail (full compute_production_cost_basis result).
    Items with no WMA data at all (unit_cost == 0 and has_all_wma == False) are
    included so the page can show which items are missing price data.
    """
    import json
    from pathlib import Path

    bt_path = Path("business_types.json")
    db_path = Path("district_businesses.json")
    it_path = Path("item_types.json")
    di_path = Path("district_items.json")

    try:
        with open(bt_path) as f:
            business_types = json.load(f)
    except FileNotFoundError:
        return []

    try:
        with open(db_path) as f:
            business_types.update(json.load(f))
    except FileNotFoundError:
        pass

    item_types: dict = {}
    try:
        with open(it_path) as f:
            item_types = json.load(f)
        try:
            with open(di_path) as f:
                item_types.update(json.load(f))
        except FileNotFoundError:
            pass
    except FileNotFoundError:
        pass

    results = []
    seen: set = set()

    for biz_key, biz_data in business_types.items():
        if not isinstance(biz_data, dict):
            continue
        if biz_data.get("class") != "production":
            continue
        for line in biz_data.get("production_lines", []):
            output = line.get("output_item")
            if not output or output in seen:
                continue
            seen.add(output)

            cb       = compute_production_cost_basis(player_id, biz_data, line)
            meta     = item_types.get(output, {})
            name     = (meta.get("name") if isinstance(meta, dict) else None) \
                       or output.replace("_", " ").title()
            category = (meta.get("category") if isinstance(meta, dict) else None) \
                       or "unknown"

            results.append({
                "item_key":    output,
                "name":        name,
                "category":    category,
                "unit_cost":   cb["unit_cost"],
                "has_all_wma": cb["has_all_wma"],
                "has_all_priced": cb["has_all_priced"],
                "theoretical_fallback_count": cb["theoretical_fallback_count"],
                "missing_wma": cb["missing_wma_items"],
                "business":    biz_data.get("name", biz_key),
                "business_key": biz_key,
                "detail":      cb,
            })

    return results


# ==========================
# INIT
# ==========================

def initialize():
    """Create inventory_cost_ledger table if it doesn't exist."""
    Base.metadata.create_all(bind=engine)
    print("[WMA] inventory_cost_ledger table ready")
