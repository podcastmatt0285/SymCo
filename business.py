# business.py (Full Version with Dismantling System and Retail Pricing Patch)
import json
import random
import threading
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Float
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from stats_ux import log_transaction
# Integrated Algebraic Engine
from supplydemand import SupplyDemandEngine

from database import engine, SessionLocal
Base = declarative_base()

# ── Business push-notification helpers ────────────────────────────────────────
_BIZ_PUSH_COOLDOWN = 21600         # notify at most once per 6 hours per issue

def _fire_business_push(player_id: int, biz_id: int, issue_key: str,
                         title: str, body: str) -> None:
    """Send a push notification for a business issue, rate-limited to once per 6 hours.
    Rate limit is persisted in DB so it survives server restarts."""
    if player_id <= 0:
        return  # NPCs have no push subscribers
    from push_ux import push_rate_ok, push_rate_mark
    db_key = f"biz-{biz_id}-{issue_key}"
    if not push_rate_ok(db_key, _BIZ_PUSH_COOLDOWN):
        return
    push_rate_mark(db_key)
    def _send():
        try:
            from push_ux import send_push_notification
            send_push_notification(
                player_id, title, body,
                url="/businesses",
                notif_type="business",
                tag=f"biz-{biz_id}-{issue_key}",
            )
        except Exception as e:
            print(f"[Business] Push error for player {player_id}: {e}")
    threading.Thread(target=_send, daemon=True).start()

def _fmt_item(item: str) -> str:
    """'raw_leather' → 'Raw Leather'"""
    return item.replace("_", " ").title()

# ==========================
# DATABASE MODELS
# ==========================

class Business(Base):
    __tablename__ = "businesses"
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, index=True, nullable=False)
    land_plot_id = Column(Integer, unique=True, nullable=True)
    business_type = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    progress_ticks = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    district_id = Column(Integer, nullable=True)  # District ID if business is on a district
    special_plot_id = Column(Integer, nullable=True)  # SpecialPlot ID if on a special plot
    # Per-line pause: JSON arrays of paused line indices / product keys
    paused_lines = Column(String, default="[]")      # e.g. "[0, 2]"
    paused_products = Column(String, default="[]")   # e.g. '["bread", "milk"]'
    is_tutorial_reward = Column(Boolean, default=False)  # True → permanently wage-free
    total_minted = Column(Float, default=0.0)  # cumulative coinage struck (mints only)

class RetailPrice(Base):
    __tablename__ = "retail_prices"
    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, index=True, nullable=False)
    item_type = Column(String, index=True, nullable=False)
    price = Column(Float, nullable=False)

class BusinessSale(Base):
    """Tracks businesses being dismantled over time."""
    __tablename__ = "business_sales"
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, index=True, nullable=False)
    owner_id = Column(Integer, index=True, nullable=False)
    total_refund = Column(Float, nullable=False)
    refund_per_tick = Column(Float, nullable=False)
    ticks_remaining = Column(Integer, nullable=False)
    ticks_total = Column(Integer, nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)

# ==========================
# CONFIG & LIFECYCLE
# ==========================

BUSINESS_TYPES = {}
DISMANTLING_TICKS = 100 # Number of ticks to dismantle a business

def load_business_config():
    global BUSINESS_TYPES
    try:
        with open("business_types.json", "r") as f:
            BUSINESS_TYPES = json.load(f)
    except Exception as e:
        print(f"[Business] Config load error: {e}")

def initialize():
    Base.metadata.create_all(bind=engine)
    # Safe migration: add per-line pause columns if they don't exist yet
    from database import run_ddl_migration
    run_ddl_migration(engine, [
        "ALTER TABLE businesses ADD COLUMN IF NOT EXISTS paused_lines TEXT DEFAULT '[]'",
        "ALTER TABLE businesses ADD COLUMN IF NOT EXISTS paused_products TEXT DEFAULT '[]'",
        "ALTER TABLE businesses ADD COLUMN IF NOT EXISTS is_tutorial_reward BOOLEAN DEFAULT FALSE",
        "ALTER TABLE businesses ADD COLUMN IF NOT EXISTS special_plot_id INTEGER DEFAULT NULL",
        "ALTER TABLE businesses ADD COLUMN IF NOT EXISTS total_minted DOUBLE PRECISION DEFAULT 0.0",
    ])
    load_business_config()
    print("[Business] Module initialized with production patches and dismantling system")

def tick(current_tick: int, now: datetime):
    db = SessionLocal()
    try:
        # Run the two phases independently so a failure in production can never
        # block dismantling refunds (or vice versa). Previously a single raised
        # exception in process_business_tick aborted the whole tick, leaving
        # dismantling permanently stuck and no business producing.
        try:
            process_business_tick(db)
        except Exception as e:
            print(f"[Business] process_business_tick failed: {e}")
            try:
                db.rollback()
            except Exception:
                pass
        try:
            process_dismantling_tick(db)
        except Exception as e:
            print(f"[Business] process_dismantling_tick failed: {e}")
            try:
                db.rollback()
            except Exception:
                pass
    finally:
        db.close()

# ==========================
# DISMANTLING SYSTEM
# ==========================

def process_dismantling_tick(db):
    """Process one tick of all ongoing business dismantling sales."""
    from auth import Player
    from land import LandPlot
    active_sales = db.query(BusinessSale).all()
    for sale in active_sales:
        if sale.ticks_remaining <= 0:
            continue

        # Isolate each sale and commit it independently, so a single failing
        # refund can never block (or roll back) progress on every other
        # dismantling. Previously one raised exception aborted the whole pass
        # with no commit, freezing all dismantling indefinitely.
        try:
            # Pay the owner this tick's refund, auto-converting to legal tender.
            player = db.query(Player).filter(Player.id == sale.owner_id).first()
            if player:
                try:
                    from reserve_banks import convert_to_legal_tender
                    convert_to_legal_tender(player.id, sale.refund_per_tick)
                except Exception:
                    try:
                        from reserve_banks import credit_usd
                        credit_usd(player.id, sale.refund_per_tick)
                    except Exception as _pay_e:
                        # Could not pay this tick — log and still advance the
                        # counter so dismantling cannot wedge on a payout error.
                        print(f"[Business] dismantling payout error sale {sale.id}: {_pay_e}")
                sale.ticks_remaining -= 1

            # If dismantling is complete
            if sale.ticks_remaining <= 0:
                # Delete the business
                biz = db.query(Business).filter(Business.id == sale.business_id).first()
                if biz:
                    # Notify owner before deleting
                    try:
                        if getattr(biz, 'special_plot_id', None):
                            _cfg = get_mint_business_types().get(biz.business_type, {})
                        elif biz.district_id or getattr(biz, 'is_tutorial_reward', False):
                            _cfg = get_district_business_types().get(biz.business_type, {})
                        else:
                            _cfg = BUSINESS_TYPES.get(biz.business_type, {})
                        _biz_name = _cfg.get("name", biz.business_type)
                        _fire_business_push(sale.owner_id, biz.id, "dismantled",
                            _biz_name, f"Dismantling complete — full refund of ${sale.total_refund:,.0f} has been paid")
                    except Exception:
                        pass
                    # Free up the land
                    plot = db.query(LandPlot).filter(LandPlot.id == biz.land_plot_id).first()
                    if plot:
                        plot.occupied_by_business_id = None
                    # Free up a special plot (mints) — biz.land_plot_id is None for these,
                    # so the LandPlot lookup above never clears them.
                    if getattr(biz, 'special_plot_id', None):
                        try:
                            from special_plots import vacate_special_plot
                            vacate_special_plot(biz.special_plot_id)
                        except Exception as _vsp_e:
                            print(f"[Business] could not vacate special plot {biz.special_plot_id}: {_vsp_e}")
                    db.delete(biz)
                    print(f"[Business] Dismantling complete for business {sale.business_id}")

                # Delete the sale record
                db.delete(sale)

            db.commit()
        except Exception as _sale_e:
            print(f"[Business] dismantling tick error sale {getattr(sale, 'id', '?')}: {_sale_e}")
            try:
                db.rollback()
            except Exception:
                pass

def start_business_dismantling(player_id: int, business_id: int) -> bool:
    """
    Begin dismantling a business.
    Returns 50% of startup cost paid over DISMANTLING_TICKS.
    """
    db = SessionLocal()
    try:
        from auth import Player
        biz = db.query(Business).filter(
            Business.id == business_id,
            Business.owner_id == player_id
        ).first()
        
        if not biz:
            db.close()
            return False
            
        existing_sale = db.query(BusinessSale).filter(
            BusinessSale.business_id == business_id
        ).first()
        if existing_sale:
            db.close()
            return False 

        # Tutorial reward businesses were free — no refund on dismantling
        if getattr(biz, 'is_tutorial_reward', False):
            total_refund = 0.0
        else:
            if getattr(biz, 'special_plot_id', None):
                config = get_mint_business_types().get(biz.business_type, {})
            elif biz.district_id:
                config = get_district_business_types().get(biz.business_type, {})
            else:
                config = BUSINESS_TYPES.get(biz.business_type, {})
            base_cost = config.get("startup_cost", 2500.0)
            older_businesses = db.query(Business).filter(
                Business.owner_id == player_id,
                Business.created_at < biz.created_at
            ).count()
            multiplier = max(1, older_businesses)
            total_refund = (base_cost * multiplier) * 0.5
        refund_per_tick = total_refund / DISMANTLING_TICKS
        
        sale = BusinessSale(
            business_id=business_id,
            owner_id=player_id,
            total_refund=total_refund,
            refund_per_tick=refund_per_tick,
            ticks_remaining=DISMANTLING_TICKS,
            ticks_total=DISMANTLING_TICKS
        )
        db.add(sale)
        biz.is_active = False
        db.commit()
        print(f"[Business] Started dismantling business {business_id}, will pay ${total_refund:.2f} over {DISMANTLING_TICKS} ticks")
        db.close()
        return True
    except Exception as e:
        print(f"[Business] Error starting dismantling: {e}")
        db.close()
        return False

def get_dismantling_status(business_id: int):
    """Get dismantling status for a business."""
    db = SessionLocal()
    sale = db.query(BusinessSale).filter(BusinessSale.business_id == business_id).first()
    db.close()
    if not sale:
        return None
    progress_pct = ((sale.ticks_total - sale.ticks_remaining) / sale.ticks_total) * 100
    return {
        "ticks_remaining": sale.ticks_remaining,
        "ticks_total": sale.ticks_total,
        "progress_pct": progress_pct,
        "total_refund": sale.total_refund,
        "refund_per_tick": sale.refund_per_tick,
        "paid_so_far": sale.refund_per_tick * (sale.ticks_total - sale.ticks_remaining)
    }

# ==========================
# CORE SIMULATION LOGIC
# ==========================

# ==========================
# FIXED process_business_tick FUNCTION
# ==========================
def process_business_tick(db):
    from inventory import InventoryItem
    from land import LandPlot
    from auth import Player
    import market
    try:
        from events import get_active_production_factor as _get_prod_factor
        _ev_prod_factor = _get_prod_factor()
    except Exception:
        _ev_prod_factor = 1.0
    try:
        from events import get_active_item_crisis_factors as _get_crisis_factors
        _crisis_factors = _get_crisis_factors()
    except Exception:
        _crisis_factors = {}

    # Batch-load data needed in every iteration to eliminate N+1 query patterns.
    busy_biz_ids = {s.business_id for s in db.query(BusinessSale.business_id).all()}
    _city_buffs_cache: dict = {}  # owner_id → buffs dict, populated lazily per owner

    active_biz = db.query(Business).filter(Business.is_active == True).all()

    # Pre-load all players, plots, and inventory in 4 queries instead of N per business.
    _all_owner_ids = {b.owner_id for b in active_biz}
    _players_by_id = {p.id: p for p in db.query(Player).filter(Player.id.in_(_all_owner_ids)).all()}
    _plot_ids = [b.land_plot_id for b in active_biz if b.land_plot_id and not b.district_id]
    _plots_by_id = {p.id: p for p in (db.query(LandPlot).filter(LandPlot.id.in_(_plot_ids)).all() if _plot_ids else [])}

    # Pre-load ALL inventory as ORM objects — update in-place, commit once at end.
    _inv_objs: dict = {}  # (player_id, item_type) → InventoryItem ORM object
    _inv_qty: dict = {}   # player_id → {item_type: float}  (in-memory view)
    for _ii in db.query(InventoryItem).filter(InventoryItem.player_id.in_(list(_all_owner_ids))).all():
        _inv_objs[(_ii.player_id, _ii.item_type)] = _ii
        if _ii.quantity > 0:
            _inv_qty.setdefault(_ii.player_id, {})[_ii.item_type] = _ii.quantity

    def _inv_add(pid, itype, qty):
        if qty <= 0:
            return
        key = (pid, itype)
        if key in _inv_objs:
            _inv_objs[key].quantity += qty
        else:
            new_obj = InventoryItem(player_id=pid, item_type=itype, quantity=qty)
            db.add(new_obj)
            _inv_objs[key] = new_obj
        _inv_qty.setdefault(pid, {})[itype] = _inv_qty.get(pid, {}).get(itype, 0) + qty

    def _inv_remove(pid, itype, qty) -> bool:
        if qty <= 0:
            return True
        current = _inv_qty.get(pid, {}).get(itype, 0)
        if current < qty:
            return False
        key = (pid, itype)
        if key in _inv_objs:
            _inv_objs[key].quantity -= qty
        _inv_qty.setdefault(pid, {})[itype] = current - qty
        return True

    # Keep one brokerage session open for the whole tick to avoid 300 open/close cycles.
    _brok_db = None
    _brok_shares: dict = {}  # owner_id → CompanyShares (live objects in _brok_db)
    try:
        from banks.brokerage_firm import SessionLocal as _BrokDB2, CompanyShares as _CS2
        _brok_db = _BrokDB2()
        _brok_rows = _brok_db.query(_CS2).filter(
            _CS2.founder_id.in_(list(_all_owner_ids)),
            _CS2.is_delisted == False,
            _CS2.share_class_label == "main",
        ).all()
        for _r in _brok_rows:
            _brok_shares[_r.founder_id] = _r
    except Exception:
        if _brok_db:
            try:
                _brok_db.close()
            except Exception:
                pass
        _brok_db = None

    # Accumulate revenue credits per player — flush in batch after the loop.
    _pending_credits: dict = {}  # player_id → total founder_credit

    for biz in active_biz:
        try:
            if biz.id in busy_biz_ids:
                continue

            # Check if this is a district/special-plot business and load appropriate config.
            # Tutorial-reward businesses live on a land plot but use district business types.
            if getattr(biz, 'special_plot_id', None):
                mint_types = get_mint_business_types()
                config = mint_types.get(biz.business_type, {})
            elif biz.district_id or getattr(biz, 'is_tutorial_reward', False):
                district_business_types = get_district_business_types()
                config = district_business_types.get(biz.business_type, {})
            else:
                config = BUSINESS_TYPES.get(biz.business_type, {})

            # Mints are dormant without an active Wadsworth Pro subscription.
            # The mint is permanent and reactivates automatically on resubscribe —
            # while dormant it neither advances progress nor produces coinage.
            if getattr(biz, 'special_plot_id', None) and config.get("class") == "mint":
                _owner = _players_by_id.get(biz.owner_id)
                try:
                    from skin_utils import is_pro
                    _owner_pro = bool(_owner) and is_pro(_owner)
                except Exception:
                    _owner_pro = bool(_owner)
                if not _owner_pro:
                    continue

            cycles = config.get("cycles_to_complete", 1)
            # Apply city cycle-speed buff (reduces effective cycles_to_complete)
            try:
                from city_projects import get_city_production_buffs as _gcpb
                if biz.owner_id not in _city_buffs_cache:
                    _city_buffs_cache[biz.owner_id] = _gcpb(biz.owner_id)
                _cs_mult = _city_buffs_cache[biz.owner_id].get("cycle_speed_multiplier", 1.0)
                cycles = max(1, int(cycles * _cs_mult))
            except Exception:
                pass
            if biz.progress_ticks < cycles:
                biz.progress_ticks += 1

            if biz.progress_ticks < cycles:
                continue

            player = _players_by_id.get(biz.owner_id)

            # FIXED: For district/special-plot businesses, skip land plot lookup
            if biz.district_id or getattr(biz, 'special_plot_id', None):
                eff_multiplier = 1.0
            else:
                plot = _plots_by_id.get(biz.land_plot_id)
                if not plot:
                    continue
                eff_multiplier = max(0.005, min(1.0, plot.efficiency / 100.0))
        
            if not player:
                continue
        
            base_wage = config.get("base_wage_cost", 0.0)
            # Tutorial-reward businesses are permanently wage-free
            if getattr(biz, 'is_tutorial_reward', False):
                wage_cost = 0.0
            else:
                # Parse paused sets here (needed for per-line wage count)
                paused_line_idxs = set(json.loads(biz.paused_lines or "[]"))
                paused_product_keys = set(json.loads(biz.paused_products or "[]"))
                _n_active_lines = sum(
                    1 for i in range(len(config.get("production_lines", [])))
                    if i not in paused_line_idxs
                )
                _n_active_products = sum(
                    1 for pk in config.get("products", {})
                    if pk not in paused_product_keys
                )
                _active_count = _n_active_lines + _n_active_products
                wage_cost = base_wage * _active_count / eff_multiplier

            # Apply city project production buffs (if player is a city member)
            _city_output_mult = 1.0
            _city_wage_mult = 1.0
            _city_input_mult = 1.0
            try:
                _city_buffs = _city_buffs_cache[biz.owner_id]
                _city_output_mult = _city_buffs.get("output_multiplier", 1.0)
                _city_wage_mult   = _city_buffs.get("wage_multiplier",   1.0)
                _city_input_mult  = _city_buffs.get("input_multiplier",  1.0)
            except Exception:
                pass

            # Executive production bonus — applied once per business cycle
            _exec_prod_mult = 1.0
            try:
                from executive import get_player_job_bonus as _exec_gjb2
                _ep = _exec_gjb2(db, biz.owner_id, "production")
                if _ep > 0:
                    _exec_prod_mult = 1.0 + _ep
            except Exception:
                pass

            # Immigration policy multipliers — fetched once per business owner
            _imm_mults = {"demand": 1.0, "elasticity": 1.0,
                          "production": 1.0, "input_cost": 1.0, "land_yield": 1.0}
            try:
                from port_authority import get_player_immigration_mults as _get_imm
                _imm_mults = _get_imm(biz.owner_id)
            except Exception:
                pass
            _imm_prod_mult = _imm_mults.get("production", 1.0)
            # Land-based businesses additionally benefit from land_yield mult
            _imm_land_mult = _imm_mults.get("land_yield", 1.0) if biz.land_plot_id else 1.0
            _imm_input_cost = _imm_mults.get("input_cost", 1.0)

            if wage_cost > 0:
                wage_cost *= _city_wage_mult
                # NPCs always assumed to have funds — skip the per-business DB check.
                if player.id > 0:
                    from reserve_banks import can_afford_usd
                    if not can_afford_usd(player.id, wage_cost):
                        biz_name = config.get("name", biz.business_type)
                        _fire_business_push(player.id, biz.id, "wages",
                            biz_name, f"Can't afford wages — ${wage_cost:,.0f} needed to keep running")
                        continue

            player_inv = dict(_inv_qty.get(player.id, {}))
            lines_successfully_produced = 0
            total_revenue = 0.0
            has_retail = bool(config.get("products"))
            production_lines = config.get("production_lines", [])

            # paused_line_idxs and paused_product_keys already parsed above for wage calc
            # (tutorial-reward path skips the parse, so ensure they exist here)
            if getattr(biz, 'is_tutorial_reward', False):
                paused_line_idxs = set(json.loads(biz.paused_lines or "[]"))
                paused_product_keys = set(json.loads(biz.paused_products or "[]"))

            # ===== RETAIL PROCESSING =====
            if has_retail:
                for item, rule in config.get("products", {}).items():
                    if item in paused_product_keys:
                        continue
                    qty = player_inv.get(item, 0)
                    if qty <= 0:
                        biz_name = config.get("name", biz.business_type)
                        _fire_business_push(player.id, biz.id, f"stock-{item}",
                            biz_name, f"{_fmt_item(item)} is out of stock — restock to keep selling")
                        continue

                    price_entry = db.query(RetailPrice).filter(
                        RetailPrice.player_id == player.id,
                        RetailPrice.item_type == item
                    ).first()

                    mkt_p = _retail_reference_price(item)
                    current_p = price_entry.price if price_entry else mkt_p

                    try:
                        eff_elasticity = rule.get("elasticity", 1.0) * _imm_mults.get("elasticity", 1.0)
                        base_chance    = rule.get("base_sale_chance", 0.05) * _imm_mults.get("demand", 1.0)
                        multiplier = SupplyDemandEngine.get_sales_multiplier(
                            current_p, mkt_p, eff_elasticity
                        )
                        chance = SupplyDemandEngine.calculate_chance_per_tick(
                            base_chance, multiplier
                        )
                    except (ValueError, ZeroDivisionError) as e:
                        print(f"[Business] Skipping retail item {item} for biz {biz.id}: {e}")
                        continue

                    sold = sum(1 for _ in range(int(qty)) if random.random() < chance)
                    if sold > 0:
                        _inv_remove(player.id, item, sold)
                        total_revenue += sold * current_p
                        lines_successfully_produced += 1

            # ===== PRODUCTION PROCESSING =====
            for line_idx, line in enumerate(production_lines):
                if line_idx in paused_line_idxs:
                    continue
                line_can_run = True
                # Apply city project input multiplier (reduces qty needed).
                # round() is used instead of int() so that savings apply correctly
                # to larger quantities (e.g. 4.9 → 5 not 4).  Quantities of exactly
                # 1 are unaffected by savings below 50% — a known integer-rounding
                # limitation of discrete inventory items.
                effective_inputs = [
                    {**req, "quantity": max(1, round(req["quantity"] * _city_input_mult * _imm_input_cost))}
                    for req in line.get("inputs", [])
                ]
                for req in effective_inputs:
                    if player_inv.get(req["item"], 0) < req["quantity"]:
                        line_can_run = False
                        biz_name = config.get("name", biz.business_type)
                        _fire_business_push(player.id, biz.id, f"input-{req['item']}",
                            biz_name,
                            f"Out of {_fmt_item(req['item'])} — need {req['quantity']} to produce")
                        break

                # Mint guard: coinage is backed 1:1 by metal market value. Value
                # each metal at its live market price, falling back to the item's
                # base_price when the market is thin (empty book + no recent
                # trade) — otherwise the mint freezes at max tick forever on
                # low-liquidity metals. Skip BEFORE consuming inputs only when
                # a metal has no price by EITHER source.
                if line_can_run and config.get("class") == "mint":
                    for req in effective_inputs:
                        if req["item"] in ("energy", "paper", "water"):
                            continue
                        if not _retail_reference_price(req["item"], default=0.0) > 0:
                            line_can_run = False
                            biz_name = config.get("name", biz.business_type)
                            _fire_business_push(player.id, biz.id, f"mintprice-{req['item']}",
                                biz_name,
                                f"Mint paused — no reference price for {_fmt_item(req['item'])}")
                            break

                if line_can_run:
                    for req in effective_inputs:
                        _inv_remove(player.id, req["item"], req["quantity"])
                        # Log resource consumption
                        log_transaction(
                            biz.owner_id,
                            "resource_use",
                            "resource",
                            -req["quantity"],  # negative because consumed
                            f"Used {req['quantity']} {req['item']} in production",
                            str(biz.id)
                        )
                        player_inv[req["item"]] -= req["quantity"]
                        # Reduce WMA qty_basis for consumed inputs (players only — NPCs don't need cost tracking)
                        if player.id > 0:
                            try:
                                from wma import consume_wma
                                consume_wma(player.id, req["item"], req["quantity"])
                            except Exception:
                                pass
                    # Apply city project output multiplier + global event bonus + per-item crisis reduction
                    _item_crisis_f = _crisis_factors.get(line.get("output_item", ""), 1.0)
                    effective_output_qty = max(1, round(
                        line["output_qty"] * _city_output_mult * _ev_prod_factor
                        * _item_crisis_f * _exec_prod_mult
                        * _imm_prod_mult * _imm_land_mult
                    ))

                    # ── Mint hook: convert consumed metals into coinage currency ─────
                    # Hard money — coinage is pegged 1:1 to the USD value of the metal
                    # actually consumed (not boosted by exec/city/event multipliers, so
                    # the peg can never be inflated). credit_mint_coinage() also writes
                    # the ledger entry and returns the minted amount.
                    if config.get("class") == "mint":
                        _currency_code = line.get("output_item", "")
                        _metal_usd = sum(
                            req["quantity"] * _retail_reference_price(req["item"], default=0.0)
                            for req in effective_inputs
                            if req["item"] not in ("energy", "paper", "water")
                        )
                        if _metal_usd > 0 and _currency_code:
                            try:
                                from reserve_banks import credit_mint_coinage
                                _minted = credit_mint_coinage(player.id, _currency_code, _metal_usd)
                                if _minted > 0:
                                    biz.total_minted = (biz.total_minted or 0.0) + _minted
                                if player.id > 0 and _minted > 0:
                                    _biz_name = config.get("name", biz.business_type)
                                    _fire_business_push(player.id, biz.id, "mint-run",
                                        _biz_name,
                                        f"Minted {_minted:,.2f} {_currency_code} (${_metal_usd:,.0f} metal value)")
                            except Exception as _mint_e:
                                print(f"[Business] Mint coinage error: {_mint_e}")
                        lines_successfully_produced += 1
                        continue  # skip _inv_add and WMA for mint output
                    # ────────────────────────────────────────────────────────────────

                    _inv_add(player.id, line["output_item"], effective_output_qty)
                    # Update WMA cost basis for the newly produced output (players only)
                    if player.id > 0:
                        try:
                            from wma import compute_production_cost_basis, update_wma
                            _cb = compute_production_cost_basis(player.id, config, line)
                            if _cb["unit_cost"] > 0:
                                update_wma(player.id, line["output_item"],
                                           effective_output_qty, _cb["unit_cost"])
                        except Exception as _wma_e:
                            print(f"[Business] WMA update error: {_wma_e}")
                    # Log resource production — tag crisis in description when active
                    _prod_log_desc = f"Produced {effective_output_qty} {line['output_item']}"
                    if _item_crisis_f < 1.0:
                        _crisis_drop_pct = round((1.0 - _item_crisis_f) * 100)
                        _prod_log_desc += f" ⚠ crisis −{_crisis_drop_pct}%"
                    log_transaction(
                        biz.owner_id,
                        "resource_gain",
                        "resource",
                        effective_output_qty,
                        _prod_log_desc,
                        str(biz.id)
                    )
                    lines_successfully_produced += 1

            # ===== FINALIZE: pay wages once, reset progress, commit =====
            # Retail finalizes only when at least one product is active (not all paused).
            # Pure-production only finalizes when something was produced.
            _active_prod_set = set(config.get("products", {}).keys()) - paused_product_keys
            should_finalize = (has_retail and bool(_active_prod_set)) or lines_successfully_produced > 0
            if should_finalize:
                # Pay city production subsidy on any production that ran (players in cities only)
                if production_lines and lines_successfully_produced > 0 and player.id > 0:
                    try:
                        from cities import pay_production_subsidy
                        production_cost = 0.0
                        for line in production_lines:
                            for req in line.get("inputs", []):
                                item_price = market.get_market_price(req["item"]) or 1.0
                                production_cost += item_price * req["quantity"]

                        subsidy = pay_production_subsidy(player.id, biz.id, production_cost)
                        if subsidy > 0:
                            print(f"[Business] City subsidy: ${subsidy:.2f} to player {player.id}")
                            total_revenue += subsidy
                    except ImportError:
                        pass
                    except Exception as e:
                        print(f"[Business] Subsidy error: {e}")

                # Apply executive sales bonus to retail revenue
                if has_retail and total_revenue > 0:
                    try:
                        from executive import get_player_job_bonus as _exec_gjb
                        _sales_bonus = _exec_gjb(db, player.id, "sales")
                        if _sales_bonus > 0:
                            total_revenue = round(total_revenue * (1.0 + _sales_bonus), 2)
                    except Exception:
                        pass

                # ── Retail sales tax: 5% of gross retail revenue → federal government ──
                _retail_tax = 0.0
                if has_retail and total_revenue > 0:
                    _retail_tax = round(total_revenue * 0.05, 2)
                    try:
                        from reserve_banks import GOVERNMENT_PLAYER_ID as _RTGOV, credit_usd as _rt_credit
                        _rt_credit(_RTGOV, _retail_tax)
                        from govt_ledger import log_gov_event as _rt_lge
                        _rt_lge("retail_sales_tax", "in", _retail_tax, "USD",
                                f"Retail sales tax: {config.get('name', biz.business_type)} (biz {biz.id})")
                    except Exception as _rt_e:
                        print(f"[Business] Retail tax routing error biz {biz.id}: {_rt_e}")

                net_revenue = total_revenue - wage_cost - _retail_tax

                # ── Profit siphon: divert a % into the company's dividend escrow ──
                siphon_amount = 0.0
                try:
                    _cs = _brok_shares.get(player.id)
                    if _cs and net_revenue > 0:
                        _cs.revenue_7d  = (_cs.revenue_7d  or 0.0) + net_revenue
                        _cs.revenue_30d = (_cs.revenue_30d or 0.0) + net_revenue
                        if _cs.profit_siphon_rate:
                            siphon_amount = net_revenue * _cs.profit_siphon_rate
                            _cs.dividend_escrow_balance = (_cs.dividend_escrow_balance or 0.0) + siphon_amount
                except Exception:
                    pass

                founder_credit = net_revenue - siphon_amount
                # Accumulate revenue — credited in bulk after the loop to avoid
                # one DB session per business.
                if founder_credit > 0:
                    _pending_credits[player.id] = _pending_credits.get(player.id, 0.0) + founder_credit
                biz.progress_ticks = 0
                # Do NOT commit here — batch commit at end of loop is more efficient.
                if wage_cost > 0:
                    try:
                        log_transaction(
                            biz.owner_id,
                            "wage_payment",
                            "money",
                            -wage_cost,
                            f"Wages: {config.get('name', biz.business_type)}",
                            str(biz.id)
                        )
                    except Exception as _lt_e:
                        print(f"[Business] wage log error biz {biz.id}: {_lt_e}")
                if net_revenue > 0:
                    try:
                        log_transaction(
                            biz.owner_id,
                            "retail_sale",
                            "money",
                            founder_credit,
                            f"Retail revenue: {biz.business_type}",
                            str(biz.id)
                        )
                    except Exception as _lt_e:
                        print(f"[Business] retail log error biz {biz.id}: {_lt_e}")
        except Exception as _biz_tick_e:
            # Log the error but do NOT rollback — other businesses in this tick
            # have already modified the session (inventory, progress_ticks) and
            # rolling back would undo all of them.
            print(f"[Business] tick error for biz {getattr(biz, 'id', '?')} "
                  f"({getattr(biz, 'business_type', '?')}): {_biz_tick_e}")

    # Persist any progress_ticks and inventory increments not yet committed.
    try:
        db.commit()
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass

    # Flush accumulated revenue credits (one call per unique player instead of per business).
    if _pending_credits:
        from reserve_banks import convert_to_legal_tender, credit_usd
        for _pid, _amt in _pending_credits.items():
            try:
                convert_to_legal_tender(_pid, _amt)
            except Exception as e:
                print(f"[Business] tender conversion failed for player {_pid} (${_amt:,.2f}): {e} — falling back to credit_usd")
                try:
                    credit_usd(_pid, _amt)
                except Exception as e2:
                    print(f"[Business] credit fallback ALSO failed for player {_pid} (${_amt:,.2f}): {e2}")

    # Commit brokerage revenue/escrow updates and close the shared session.
    if _brok_db is not None:
        try:
            _brok_db.commit()
        except Exception:
            try:
                _brok_db.rollback()
            except Exception:
                pass
        finally:
            try:
                _brok_db.close()
            except Exception:
                pass

def create_business(player_id: int, plot_id: int, business_type_key: str):
    """Create a business on a vacant land plot owned by the player."""
    from land import LandPlot
    from auth import Player
    if business_type_key not in BUSINESS_TYPES:
        print(f"[Business] Unknown business type: {business_type_key}")
        return None
        
    config = BUSINESS_TYPES[business_type_key]
    db = SessionLocal()
    try:
        plot = db.query(LandPlot).filter(LandPlot.id == plot_id).first()
        if not plot or plot.owner_id != player_id or plot.occupied_by_business_id is not None:
            print("[Business] Invalid plot, ownership, or occupancy.")
            db.close()
            return None

        # Block building on a plot that is currently listed for sale
        from land_market import LandListing
        active_listing = db.query(LandListing).filter(
            LandListing.land_plot_id == plot_id,
            LandListing.is_active == True,
        ).first()
        if active_listing:
            print(f"[Business] Plot {plot_id} is listed for sale — cancel the listing before building.")
            db.close()
            return None
            
        allowed = config.get("allowed_terrain")
        if allowed and plot.terrain_type not in allowed:
            print(f"[Business] Terrain {plot.terrain_type} not allowed.")
            db.close()
            return None
            
        player = db.query(Player).filter(Player.id == player_id).first()
        if not player:
            db.close()
            return None
        
        base_cost = config.get("startup_cost", 2500.0)
        owned_businesses = db.query(Business).filter(Business.owner_id == player_id).count()
        
        # FIXED: Proper progressive cost increase
        # 0 businesses = 1.0x base cost
        # 1 business = 1.25x base cost
        # 2 businesses = 1.5x base cost
        # 3 businesses = 1.75x base cost, etc.
        multiplier = 1.0 + (owned_businesses * 0.25)
        startup_cost = base_cost * multiplier
        
        print(f"[Business] Startup cost for {business_type_key}: ${base_cost:.2f} × {multiplier:.2f} = ${startup_cost:,.2f}")
        
        from reserve_banks import spend_player_funds
        ok, _err = spend_player_funds(player_id, startup_cost)
        if not ok:
            print(f"[Business] Player {player_id} insufficient funds for startup: {_err}")
            db.close()
            return None
        # Route startup fee to federal government
        try:
            from reserve_banks import GOVERNMENT_PLAYER_ID as _GOV_ID, credit_usd as _credit_usd
            _credit_usd(_GOV_ID, startup_cost)
            from govt_ledger import log_gov_event as _lge
            _lge("startup_fee", "in", startup_cost, "USD",
                 counterparty=str(player_id),
                 description=f"Business startup: {business_type_key}")
        except Exception as _gfe:
            print(f"[Business] Gov fee routing error (non-fatal): {_gfe}")
        business = Business(
            owner_id=player_id,
            land_plot_id=plot.id,
            business_type=business_type_key,
            progress_ticks=0,
            is_active=True
        )
        db.add(business)
        db.commit()
        db.refresh(business)
        plot.occupied_by_business_id = business.id
        db.commit()
        
        print(f"[Business] Created {business_type_key} on plot {plot.id} for Player {player_id} (cost: ${startup_cost:,.2f})")
        log_transaction(player_id, "business_startup", "money", -startup_cost,
                        f"Business created: {config.get('name', business_type_key)}",
                        reference_id=str(business.id))
        return business
    except Exception as e:
        print(f"[Business] Error creating business: {e}")
        import traceback
        traceback.print_exc()
        db.close()
        return None
    finally:
        db.close()

def toggle_business(player_id: int, business_id: int) -> bool:
    """Toggle a business between active and paused."""
    db = SessionLocal()
    try:
        biz = db.query(Business).filter(Business.id == business_id, Business.owner_id == player_id).first()
        if not biz:
            db.close()
            return False
        sale = db.query(BusinessSale).filter(BusinessSale.business_id == business_id).first()
        if sale:
            db.close()
            return False
        biz.is_active = not biz.is_active
        db.commit()
        db.close()
        return True
    except Exception as e:
        print(f"[Business] Error toggling business: {e}")
        db.close()
        return False


def toggle_production_line(player_id: int, business_id: int, line_index: int) -> dict:
    """Toggle pause/resume on a single production line by index."""
    db = SessionLocal()
    try:
        biz = db.query(Business).filter(Business.id == business_id, Business.owner_id == player_id).first()
        if not biz:
            return {"ok": False, "error": "Business not found"}
        paused = json.loads(biz.paused_lines or "[]")
        if line_index in paused:
            paused.remove(line_index)
            now_paused = False
        else:
            paused.append(line_index)
            now_paused = True
        biz.paused_lines = json.dumps(paused)
        db.commit()
        return {"ok": True, "paused": now_paused}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        db.close()


def toggle_retail_item(player_id: int, business_id: int, item_type: str) -> dict:
    """Toggle pause/resume on a single retail product."""
    db = SessionLocal()
    try:
        biz = db.query(Business).filter(Business.id == business_id, Business.owner_id == player_id).first()
        if not biz:
            return {"ok": False, "error": "Business not found"}
        paused = json.loads(biz.paused_products or "[]")
        if item_type in paused:
            paused.remove(item_type)
            now_paused = False
        else:
            paused.append(item_type)
            now_paused = True
        biz.paused_products = json.dumps(paused)
        db.commit()
        return {"ok": True, "paused": now_paused}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        db.close()


# ==========================
# RETAIL PRICING PATCH
# ==========================

def set_retail_price(player_id: int, item_type: str, price: float) -> bool:
    """Set or update the retail price for a specific item for a player."""
    if price <= 0:
        print(f"[Business] Rejected invalid retail price {price} for player {player_id} ({item_type})")
        return False
    db = SessionLocal()
    try:
        price_entry = db.query(RetailPrice).filter(
            RetailPrice.player_id == player_id,
            RetailPrice.item_type == item_type
        ).first()

        if price_entry:
            price_entry.price = price
        else:
            new_price = RetailPrice(
                player_id=player_id,
                item_type=item_type,
                price=price
            )
            db.add(new_price)
        
        db.commit()
        print(f"[Business] Player {player_id} set retail price for {item_type} to ${price:.2f}")
        return True
    except Exception as e:
        print(f"[Business] Error setting retail price: {e}")
        return False
    finally:
        db.close()

# =========================
# Districts
# =========================

def get_district_business_types():
    """Load district business types from district_businesses.json.

    Each business's retail "products" are augmented with its own production
    outputs (using per-item demand parameters from district_items.json) so
    every district item has a consumer demand sink — see _augment_district_retail.
    """
    try:
        with open('district_businesses.json', 'r') as f:
            types = json.load(f)
    except FileNotFoundError:
        print("[Business] Warning: district_businesses.json not found")
        return {}
    return {
        k: (_augment_district_retail(k, v) if isinstance(v, dict) else v)
        for k, v in types.items()
    }


def get_mint_business_types():
    """Load mint business types from mint_businesses.json"""
    try:
        with open('mint_businesses.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("[Business] Warning: mint_businesses.json not found")
        return {}


# ==========================
# DISTRICT RETAIL DEMAND
# ==========================
# Every district item carries elasticity/base_sale_chance in district_items.json,
# so district businesses can retail anything they produce — not just the items
# hand-listed in their "products" block. The order book remains the B2B channel;
# this gives district production a guaranteed consumer demand sink.

_district_retail_cache: dict = {}

def _augment_district_retail(business_type: str, config: dict) -> dict:
    """Return config with auto-generated retail products for each production
    output that has demand parameters in district_items.json. Cached per type."""
    cached = _district_retail_cache.get(business_type)
    if cached is not None:
        return cached
    try:
        from district_market import DISTRICT_ITEMS
        from inventory import ITEM_RECIPES
        auto = {}
        for line in config.get("production_lines", []) or []:
            out = line.get("output_item")
            # demand params live in district_items.json; some district outputs
            # are defined in item_types.json instead, so fall back there
            d = DISTRICT_ITEMS.get(out) or ITEM_RECIPES.get(out)
            if not out or not isinstance(d, dict):
                continue
            if "elasticity" not in d or "base_sale_chance" not in d:
                continue
            auto[out] = {"elasticity": d["elasticity"],
                         "base_sale_chance": d["base_sale_chance"]}
        if auto:
            merged = dict(config)
            merged["products"] = {**auto, **(config.get("products") or {})}
            config = merged
    except Exception as e:
        print(f"[Business] district retail augment failed for {business_type}: {e}")
    _district_retail_cache[business_type] = config
    return config


def _retail_reference_price(item: str, default: float = 10.0) -> float:
    """Reference market price: live market → district market → item base_price
    (item_types/district_items) → `default`. Retail uses the $10 last-resort;
    the mint peg passes default=0 so an unpriceable metal halts the run instead
    of minting against a made-up valuation."""
    try:
        import market
        p = market.get_market_price(item)
        if p and p > 0:
            return p
    except Exception:
        pass
    try:
        import district_market as _dm
        if item in _dm.DISTRICT_ITEMS:
            try:
                p = _dm.get_market_price(item)
            except Exception:
                p = None
            if p and p > 0:
                return p
            bp = _dm.DISTRICT_ITEMS[item].get("base_price")
            if bp and bp > 0:
                return float(bp)
    except Exception:
        pass
    try:
        import inventory as _inv_mod
        bp = (_inv_mod.ITEM_RECIPES.get(item) or {}).get("base_price")
        if bp and bp > 0:
            return float(bp)
    except Exception:
        pass
    return default

# ==========================
# FIXED create_district_business FUNCTION
# ==========================
# Replace the create_district_business function in business.py with this corrected version

def create_district_business(owner_id: int, district_id: int, business_type: str):
    """
    Create a business on a district.
    Similar to create_business() but for districts instead of land plots.
    
    Args:
        owner_id: Player ID who owns the district
        district_id: District ID to build on
        business_type: Type of district business to create
    
    Returns:
        (Business instance or None, error message)
    """
    from districts import get_district, occupy_district
    from auth import Player
    
    db = SessionLocal()  # FIXED: Use SessionLocal() not get_db()
    
    try:
        # Verify district exists and is owned by player
        district = get_district(district_id)
        if not district:
            return None, "District not found"
        
        if district.owner_id != owner_id:
            return None, "You don't own this district"
        
        if district.occupied_by_business_id is not None:
            return None, "District already has a business"
        
        # Load district business types
        district_business_types = get_district_business_types()
        
        if business_type not in district_business_types:
            return None, f"Invalid district business type: {business_type}"
        
        config = district_business_types[business_type]
        
        # Verify terrain compatibility
        district_terrain_key = f"district_{district.district_type}"
        if district_terrain_key not in config.get("allowed_terrain", []):
            return None, f"This business cannot be built on a {district.district_type} district"
        
        # Calculate cost with multiplier
        base_cost = config.get("startup_cost", 2500.0)
        owned_businesses = db.query(Business).filter(Business.owner_id == owner_id).count()
        
        # FIXED: Use same multiplier formula as create_business
        multiplier = 1.0 + (owned_businesses * 0.25)
        total_cost = base_cost * multiplier
        
        # Check player has enough money
        player = db.query(Player).filter(Player.id == owner_id).first()
        if not player:
            return None, "Player not found"
        
        from reserve_banks import spend_player_funds
        ok, err = spend_player_funds(owner_id, total_cost)
        if not ok:
            return None, err
        # Route district startup fee to federal government
        try:
            from reserve_banks import GOVERNMENT_PLAYER_ID as _GOV_ID, credit_usd as _credit_usd
            _credit_usd(_GOV_ID, total_cost)
            from govt_ledger import log_gov_event as _lge
            _lge("district_startup_fee", "in", total_cost, "USD",
                 counterparty=str(owner_id),
                 description=f"District business startup: {business_type}")
        except Exception as _gfe:
            print(f"[Business] Gov district fee routing error (non-fatal): {_gfe}")

        # Create business
        business = Business(
            owner_id=owner_id,
            business_type=business_type,
            district_id=district_id,  # District businesses use this
            land_plot_id=None,  # No land plot for district businesses (REQUIRES nullable column)
            progress_ticks=0,
            is_active=True
        )
        
        db.add(business)
        db.commit()
        db.refresh(business)
        
        # Occupy the district
        occupy_district(district_id, business.id)
        
        print(f"[Business] Created district business {business.id} ({business_type}) for player {owner_id} on district {district_id}")
        return business, "Success"
        
    except Exception as e:
        print(f"[Business] Error creating district business: {e}")
        import traceback
        traceback.print_exc()
        return None, str(e)
    finally:
        db.close()  # FIXED: Always close the session

# ==========================
# PUBLIC API
# ==========================

__all__ = [
    'Business',
    'RetailPrice',
    'BusinessSale',
    'BUSINESS_TYPES',
    'create_business',
    'toggle_business',
    'start_business_dismantling',
    'get_dismantling_status',
    'set_retail_price',
    'DISMANTLING_TICKS'
]
