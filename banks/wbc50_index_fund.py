"""
banks/wbc50_index_fund.py — WBC-50 Index Fund

Full-replication index fund that tracks the Wadsworth Blue-Chip 50.

Strategy:
  - Holds 18–21 % of each constituent's outstanding shares, weighted
    proportionally to each company's market-cap share within the WBC-50.
  - Midpoint target is 19.5 %. A position is only rebalanced when it drifts
    outside the 18–21 % band (avoids constant churn).
  - When a company enters the WBC-50 it is bought up to 19.5 %. When a
    company leaves the WBC-50 its entire position is sold.

Funding:
  - Seeded at initialisation by the Brokerage Firm (SEED_CAPITAL).
  - During each rebalance cycle the Firm may top up the fund's cash reserves
    by up to BROKERAGE_TOPUP_PER_CYCLE until BROKERAGE_TOTAL_FUNDING_CAP is
    reached. Spending is tracked via firm_deduct_cash().

Tick schedule (5 s / tick assumed):
  - VALUATION_INTERVAL   =  30 ticks  (~2.5 min)  – recalc asset_value
  - REBALANCE_INTERVAL   = 720 ticks  (~60 min)   – buy / sell constituents
  - EXPENSE_INTERVAL     = 3600 ticks (~5 h)      – deduct 0.5 % annual fee
"""

from datetime import datetime
from typing import Optional

# ==========================
# BANK IDENTITY
# ==========================

BANK_ID          = "wbc50_index_fund"
BANK_NAME        = "WBC-50 Index Fund"
BANK_DESCRIPTION = ("Full-replication index fund tracking the Wadsworth Blue-Chip 50. "
                    "Holds 18–21 % of each constituent — real equity in public "
                    "companies plus cash-settled synthetic stakes in NPC private "
                    "enterprises — so the fund mirrors the full index basket.")
BANK_PLAYER_ID   = -7   # Unique negative player-ID for this fund

# ==========================
# CONSTANTS
# ==========================

SEED_CAPITAL      = 50_000_000.0     # $50 M initial cash from Brokerage Firm
IPO_SHARES        = 500_000_000      # 500 M tradeable ETF shares
SHARE_ITEM_TYPE   = "wbc50_index_fund_shares"

# Full-replication target band (fraction of each company's outstanding shares)
TARGET_HOLDING     = 0.195   # 19.5 % midpoint
TARGET_HOLDING_MIN = 0.18    # 18 % — buy trigger if below this
TARGET_HOLDING_MAX = 0.21    # 21 % — sell trigger if above this

# Operational cash buffer — keep this fraction of NAV liquid for redemptions
CASH_RESERVE_RATIO = 0.02   # 2 %

# Tick intervals
VALUATION_INTERVAL = 30     # Update asset_value every 30 ticks
REBALANCE_INTERVAL = 720    # Rebalance portfolio every 720 ticks (~60 min)
EXPENSE_INTERVAL   = 3600   # Collect expense ratio every 3600 ticks (~5 h)

# Annual management fee (expense ratio) — paid to Brokerage Firm
EXPENSE_RATIO_ANNUAL = 0.005    # 0.5 % per year
TICKS_PER_YEAR       = 6_307_200  # 365 d × 24 h × 3 600 s / 5 s per tick

# State tracking
last_rebalance_tick = 0
last_valuation_tick = 0
last_expense_tick   = 0
ipo_share_price     = None

# ==========================
# DATABASE SETUP
# ==========================

from sqlalchemy import Column, Integer, Float, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from database import engine, SessionLocal

Base = declarative_base()


class IndexFundHolding(Base):
    """Tracks the fund's current position in each WBC-50 constituent.

    Two position types share this table:
      • Equity (is_npc=False): a real shareholding in a public company. Valued
        at shares_held × current_price; bought/sold on the brokerage.
      • NPC synthetic (is_npc=True): a cash-settled stake in an NPC private
        enterprise (which has no tradeable shares). The fund "owns"
        stake_fraction of the NPC's enterprise value; valued at
        stake_fraction × current_npc_enterprise_value. This lets the ETF basket
        mirror the index, which also includes NPC enterprises.
    """
    __tablename__ = "wbc50_fund_holdings"

    id              = Column(Integer, primary_key=True, index=True)
    company_id      = Column(Integer, index=True, nullable=False)   # CompanyShares.id (0 for NPC rows)
    ticker          = Column(String,  nullable=False)
    shares_held     = Column(Integer, default=0)
    avg_cost_basis  = Column(Float,   default=0.0)
    last_rebalance  = Column(DateTime, default=datetime.utcnow)
    in_index        = Column(Boolean, default=True)   # False → sold, pending removal

    # NPC synthetic-stake fields (unused / default for equity holdings)
    is_npc          = Column(Boolean, default=False, index=True)
    npc_player_id   = Column(Integer, index=True, nullable=True)    # Player.id of the NPC
    stake_fraction  = Column(Float,   default=0.0)                  # fraction of NPC enterprise owned
    npc_cost_basis  = Column(Float,   default=0.0)                  # USD paid to acquire the stake


def get_db():
    return SessionLocal()


def initialize_tables():
    Base.metadata.create_all(bind=engine)
    # Migration: add NPC synthetic-stake columns to pre-existing installs.
    from database import run_ddl_migration
    run_ddl_migration(engine, [
        "ALTER TABLE wbc50_fund_holdings ADD COLUMN IF NOT EXISTS is_npc BOOLEAN DEFAULT FALSE",
        "ALTER TABLE wbc50_fund_holdings ADD COLUMN IF NOT EXISTS npc_player_id INTEGER",
        "ALTER TABLE wbc50_fund_holdings ADD COLUMN IF NOT EXISTS stake_fraction DOUBLE PRECISION DEFAULT 0.0",
        "ALTER TABLE wbc50_fund_holdings ADD COLUMN IF NOT EXISTS npc_cost_basis DOUBLE PRECISION DEFAULT 0.0",
        "CREATE INDEX IF NOT EXISTS ix_wbc50_holdings_npc ON wbc50_fund_holdings (npc_player_id)",
    ])


# ==========================
# WBC-50 CONSTITUENT HELPERS
# ==========================

def get_wbc50_constituents() -> list:
    """Return the public-company constituents of the WBC-50 — i.e. the equities
    among the *unified* top-50 basket (which also includes NPC enterprises).

    Using the shared basket from banks.indices guarantees the fund holds exactly
    the public names the index counts: if NPC enterprises occupy N of the 50
    slots, only the 50−N public companies in the basket are returned, so the
    ETF never over-holds equities the index has dropped.
    """
    try:
        from banks.brokerage_firm import CompanyShares, get_db as firm_db
        from banks.indices import get_wbc50_basket
        basket = get_wbc50_basket()
        company_ids = [e["company_id"] for e in basket["equities"]]
        if not company_ids:
            return []
        db = firm_db()
        try:
            rows = (db.query(CompanyShares)
                    .filter(CompanyShares.id.in_(company_ids),
                            CompanyShares.is_delisted == False,
                            CompanyShares.shares_outstanding > 0,
                            CompanyShares.current_price > 0)
                    .all())
        finally:
            db.close()
        rows.sort(key=lambda c: c.shares_outstanding * c.current_price, reverse=True)
        return rows
    except Exception as e:
        print(f"[{BANK_NAME}] get_wbc50_constituents error: {e}")
        return []


# ==========================
# ASSET VALUATION
# ==========================

def calculate_portfolio_value() -> float:
    """Mark-to-market value of all fund positions:
      • Equity positions:  shares_held × current_price
      • NPC synthetic:     stake_fraction × current NPC enterprise value
    """
    try:
        from banks.brokerage_firm import CompanyShares, get_db as firm_db

        holdings_db = get_db()
        try:
            equity_holdings = holdings_db.query(IndexFundHolding).filter(
                IndexFundHolding.is_npc == False,
                IndexFundHolding.shares_held > 0,
            ).all()
            npc_holdings = holdings_db.query(IndexFundHolding).filter(
                IndexFundHolding.is_npc == True,
                IndexFundHolding.stake_fraction > 0,
            ).all()
        finally:
            holdings_db.close()

        total = 0.0

        # Equity positions
        db = firm_db()
        try:
            for h in equity_holdings:
                company = db.query(CompanyShares).filter(
                    CompanyShares.id == h.company_id
                ).first()
                if company and company.current_price:
                    total += h.shares_held * company.current_price
        finally:
            db.close()

        # NPC synthetic positions — valued off live enterprise value
        if npc_holdings:
            from banks.indices import get_npc_enterprise_values
            npc_vals = get_npc_enterprise_values()
            for h in npc_holdings:
                val, _name = npc_vals.get(h.npc_player_id, (0.0, ""))
                total += h.stake_fraction * val

        return total
    except Exception as e:
        print(f"[{BANK_NAME}] portfolio valuation error: {e}")
        return 0.0


def update_asset_valuation():
    """Push the latest portfolio value into the BankEntity asset_value field."""
    import banks
    value = calculate_portfolio_value()
    banks.update_bank_assets(BANK_ID, value)


# ==========================
# SHARE OWNERSHIP (ETF SHARES)
# ==========================

def get_all_shareholders() -> dict:
    """Return {player_id: shares_owned} for all ETF-share holders (excluding the fund itself)."""
    try:
        import inventory
        inv_db = inventory.get_db()
        try:
            holdings = inv_db.query(inventory.InventoryItem).filter(
                inventory.InventoryItem.item_type == SHARE_ITEM_TYPE,
                inventory.InventoryItem.quantity > 0,
            ).all()
            return {h.player_id: int(h.quantity) for h in holdings
                    if h.player_id != BANK_PLAYER_ID}
        finally:
            inv_db.close()
    except Exception:
        return {}


def get_player_shareholding(player_id: int) -> dict:
    """Detailed ETF-share position for a single player."""
    try:
        import inventory
        import banks
        shares = inventory.get_item_quantity(player_id, SHARE_ITEM_TYPE)
        entity = banks.get_bank_entity(BANK_ID)
        if not entity:
            return {"shares_owned": 0, "current_value": 0.0, "ownership_percentage": 0.0}
        value = shares * entity.share_price
        pct   = (shares / entity.total_shares_issued * 100) if entity.total_shares_issued else 0.0
        return {
            "shares_owned":          shares,
            "current_value":         value,
            "ownership_percentage":  pct,
            "share_price":           entity.share_price,
        }
    except Exception:
        return {"shares_owned": 0, "current_value": 0.0, "ownership_percentage": 0.0}


# ==========================
# PORTFOLIO REBALANCING
# ==========================

def _get_or_create_holding(db, company_id: int, ticker: str) -> "IndexFundHolding":
    h = db.query(IndexFundHolding).filter(
        IndexFundHolding.company_id == company_id
    ).first()
    if not h:
        h = IndexFundHolding(company_id=company_id, ticker=ticker, shares_held=0)
        db.add(h)
        db.flush()
    return h


def _fund_buy_shares(holding: "IndexFundHolding", company, shares_to_buy: int,
                     bank_db, fund_entity) -> float:
    """
    Directly credit the fund's position and debit its cash reserves.
    Returns total cost paid.
    """
    if shares_to_buy <= 0 or not company.current_price:
        return 0.0
    cost = shares_to_buy * company.current_price
    if fund_entity.cash_reserves < cost:
        # Buy only what cash allows
        affordable = int(fund_entity.cash_reserves / company.current_price)
        if affordable <= 0:
            return 0.0
        shares_to_buy = affordable
        cost = shares_to_buy * company.current_price

    # Update average cost basis
    total_value = holding.shares_held * holding.avg_cost_basis + cost
    holding.shares_held    += shares_to_buy
    holding.avg_cost_basis  = total_value / holding.shares_held if holding.shares_held else 0.0
    holding.in_index        = True
    holding.last_rebalance  = datetime.utcnow()

    fund_entity.cash_reserves -= cost
    return cost


def _fund_sell_shares(holding: "IndexFundHolding", company, shares_to_sell: int,
                      fund_entity) -> float:
    """
    Reduce fund position and credit proceeds to cash reserves.
    Returns total proceeds received.
    """
    if shares_to_sell <= 0 or not company.current_price:
        return 0.0
    shares_to_sell  = min(shares_to_sell, holding.shares_held)
    proceeds        = shares_to_sell * company.current_price
    holding.shares_held     = max(0, holding.shares_held - shares_to_sell)
    holding.last_rebalance  = datetime.utcnow()
    fund_entity.cash_reserves += proceeds
    return proceeds


def _get_or_create_npc_holding(holdings_db, npc_player_id: int, name: str) -> "IndexFundHolding":
    h = holdings_db.query(IndexFundHolding).filter(
        IndexFundHolding.is_npc == True,
        IndexFundHolding.npc_player_id == npc_player_id,
    ).first()
    if not h:
        h = IndexFundHolding(
            company_id=0, ticker=(name or f"NPC#{npc_player_id}")[:24],
            shares_held=0, avg_cost_basis=0.0, in_index=True,
            is_npc=True, npc_player_id=npc_player_id,
            stake_fraction=0.0, npc_cost_basis=0.0,
        )
        holdings_db.add(h)
        holdings_db.flush()
    return h


def _fund_buy_npc_stake(holding: "IndexFundHolding", npc_value: float,
                        target_fraction: float, fund_entity) -> float:
    """Acquire additional synthetic stake in an NPC enterprise (cash-settled).

    Mirrors the equity buy: pay cash equal to (fraction bought × current
    enterprise value); if cash is short, buy only the affordable fraction.
    Returns USD spent.
    """
    if npc_value <= 0:
        return 0.0
    frac_to_buy = target_fraction - holding.stake_fraction
    if frac_to_buy <= 0:
        return 0.0
    cost = frac_to_buy * npc_value
    if fund_entity.cash_reserves < cost:
        affordable_frac = fund_entity.cash_reserves / npc_value
        if affordable_frac <= 0:
            return 0.0
        frac_to_buy = affordable_frac
        cost = frac_to_buy * npc_value
    holding.stake_fraction += frac_to_buy
    holding.npc_cost_basis += cost
    holding.in_index        = True
    holding.last_rebalance  = datetime.utcnow()
    fund_entity.cash_reserves -= cost
    return cost


def _fund_sell_npc_stake(holding: "IndexFundHolding", npc_value: float,
                         fraction_to_sell: float, fund_entity) -> float:
    """Unwind part (or all) of a synthetic NPC stake, crediting cash proceeds."""
    fraction_to_sell = min(fraction_to_sell, holding.stake_fraction)
    if fraction_to_sell <= 0:
        return 0.0
    proceeds = fraction_to_sell * npc_value
    # Reduce cost basis proportionally
    if holding.stake_fraction > 0:
        holding.npc_cost_basis *= max(0.0, 1.0 - fraction_to_sell / holding.stake_fraction)
    holding.stake_fraction = max(0.0, holding.stake_fraction - fraction_to_sell)
    holding.last_rebalance = datetime.utcnow()
    fund_entity.cash_reserves += proceeds
    return proceeds


def _rebalance_npc_stakes(holdings_db, bank_db, fund_entity) -> tuple[float, float, list, list]:
    """Rebalance the NPC synthetic-stake sleeve to mirror the index basket.

    Returns (total_bought, total_sold, entered_names, exited_names).
    """
    from banks.indices import get_wbc50_basket, get_npc_enterprise_values

    basket   = get_wbc50_basket()
    npc_vals = get_npc_enterprise_values()
    target_npc = {n["npc_id"]: n for n in basket["npcs"]}

    total_bought = 0.0
    total_sold   = 0.0
    entered, exited = [], []

    # 1. Exit NPC stakes no longer in the index basket.
    held = holdings_db.query(IndexFundHolding).filter(
        IndexFundHolding.is_npc == True,
        IndexFundHolding.stake_fraction > 0,
    ).all()
    held_ids = {h.npc_player_id for h in held}
    for h in held:
        if h.npc_player_id in target_npc:
            continue
        val, _name = npc_vals.get(h.npc_player_id, (0.0, ""))
        proceeds = _fund_sell_npc_stake(h, val, h.stake_fraction, fund_entity)
        total_sold += proceeds
        h.in_index = False
        exited.append(h.ticker)

    holdings_db.commit()
    bank_db.commit()

    # 2. Build/adjust stakes for current NPC constituents toward TARGET_HOLDING.
    for n in basket["npcs"]:
        pid  = n["npc_id"]
        val, name = npc_vals.get(pid, (n["value"], n["name"]))
        if val <= 0:
            continue
        h = _get_or_create_npc_holding(holdings_db, pid, name)
        if pid not in held_ids:
            entered.append(h.ticker)
        if h.stake_fraction > TARGET_HOLDING_MAX:
            sell_frac = h.stake_fraction - TARGET_HOLDING
            total_sold += _fund_sell_npc_stake(h, val, sell_frac, fund_entity)
        elif h.stake_fraction < TARGET_HOLDING_MIN:
            total_bought += _fund_buy_npc_stake(h, val, TARGET_HOLDING, fund_entity)

    holdings_db.commit()
    bank_db.commit()
    return total_bought, total_sold, entered, exited


def rebalance_portfolio():
    """
    Core rebalancing pass:

    1.  Fetch current WBC-50 constituents.
    2.  Sell out any positions in companies that have left the index.
    3.  For each constituent:
          - If current holding < 18 % of outstanding → buy up to 19.5 %.
          - If current holding > 21 % of outstanding → sell down to 19.5 %.
    4.  Request a Brokerage Firm top-up if cash is low before buying.
    """
    import banks
    from banks.brokerage_firm import CompanyShares, get_db as firm_db

    bank_db = banks.get_db()
    try:
        fund_entity = bank_db.query(banks.BankEntity).filter(
            banks.BankEntity.bank_id == BANK_ID
        ).first()
        if not fund_entity:
            return

        constituents     = get_wbc50_constituents()
        constituent_ids  = {c.id for c in constituents}
        eq_db            = firm_db()
        holdings_db      = get_db()

        try:
            total_bought  = 0.0
            total_sold    = 0.0
            buys_needed   = 0
            sells_done    = 0

            # ── Step 1: sell companies no longer in WBC-50 ────────────────
            stale = holdings_db.query(IndexFundHolding).filter(
                IndexFundHolding.in_index == True,
                IndexFundHolding.shares_held > 0,
            ).all()
            pre_rebalance_member_ids  = {h.company_id for h in stale if h.in_index}
            newly_exited_company_ids  = []
            for h in stale:
                if h.company_id in constituent_ids:
                    continue
                company = eq_db.query(CompanyShares).filter(
                    CompanyShares.id == h.company_id
                ).first()
                if company:
                    proceeds = _fund_sell_shares(h, company, h.shares_held, fund_entity)
                    total_sold += proceeds
                    sells_done += 1
                    print(f"[{BANK_NAME}] 📤 Exited {h.ticker}: sold {h.shares_held:,} shares, "
                          f"proceeds ${proceeds:,.2f}")
                    newly_exited_company_ids.append(h.company_id)
                h.in_index = False

            holdings_db.commit()
            bank_db.commit()

            # ── Step 2: check drift for each constituent ───────────────────
            sells_list = []
            buys_list  = []
            newly_entered_company_ids = []

            for company in constituents:
                was_member = company.id in pre_rebalance_member_ids
                h = _get_or_create_holding(holdings_db, company.id, company.ticker_symbol)
                holdings_db.flush()
                if not was_member:
                    newly_entered_company_ids.append(company.id)

                current_pct = (h.shares_held / company.shares_outstanding
                               if company.shares_outstanding else 0.0)
                target_shares = int(company.shares_outstanding * TARGET_HOLDING)
                min_shares    = int(company.shares_outstanding * TARGET_HOLDING_MIN)
                max_shares    = int(company.shares_outstanding * TARGET_HOLDING_MAX)

                if current_pct > TARGET_HOLDING_MAX:
                    sells_list.append((company, h, h.shares_held - target_shares))
                elif current_pct < TARGET_HOLDING_MIN:
                    buys_list.append((company, h, target_shares - h.shares_held))

            # Execute sells first to free up cash
            for company, h, qty in sells_list:
                proceeds     = _fund_sell_shares(h, company, qty, fund_entity)
                total_sold  += proceeds
                sells_done  += 1

            holdings_db.commit()
            bank_db.commit()

            # ── Step 3: execute buys ───────────────────────────────────────
            for company, h, qty in buys_list:
                cost         = _fund_buy_shares(h, company, qty, bank_db, fund_entity)
                total_bought += cost
                if cost > 0:
                    buys_needed += 1

            holdings_db.commit()
            bank_db.commit()

            # ── Step 4: rebalance NPC synthetic-stake sleeve ──────────────
            # The index includes NPC private enterprises; the fund mirrors them
            # as cash-settled stakes so its NAV tracks the full index basket.
            try:
                npc_bought, npc_sold, npc_in, npc_out = _rebalance_npc_stakes(
                    holdings_db, bank_db, fund_entity
                )
                total_bought += npc_bought
                total_sold   += npc_sold
                if npc_in or npc_out:
                    print(f"[{BANK_NAME}] 🏢 NPC sleeve — entered {len(npc_in)}, "
                          f"exited {len(npc_out)} (bought ${npc_bought:,.2f}, "
                          f"sold ${npc_sold:,.2f})")
            except Exception as _npce:
                print(f"[{BANK_NAME}] NPC sleeve rebalance error: {_npce}")

            if buys_needed or sells_done:
                print(f"[{BANK_NAME}] ⚖️  Rebalance complete — "
                      f"bought {buys_needed} positions (${total_bought:,.2f}), "
                      f"sold {sells_done} positions (${total_sold:,.2f})")

            if newly_entered_company_ids or newly_exited_company_ids:
                _fire_index_challenge_events(
                    eq_db, newly_entered_company_ids, newly_exited_company_ids
                )
        finally:
            eq_db.close()
            holdings_db.close()
    finally:
        bank_db.close()


def _fire_index_challenge_events(eq_db, entered_ids: list, exited_ids: list):
    """Award index_challenge task progress to qualifying players after a rebalance.

    Players who were OUTSIDE the index at event start and just ENTERED are rewarded.
    Players who were INSIDE the index at event start and just EXITED are rewarded.
    """
    if not entered_ids and not exited_ids:
        return
    import json as _json
    from datetime import datetime
    try:
        from events import record_task_progress, SessionLocal as events_db, GameEvent
        ev_db = events_db()
        try:
            now = datetime.utcnow()
            challenges = ev_db.query(GameEvent).filter(
                GameEvent.is_active == True,
                GameEvent.event_type == "index_challenge",
                GameEvent.starts_at <= now,
                (GameEvent.ends_at == None) | (GameEvent.ends_at >= now),
            ).all()
            if not challenges:
                return
            from banks.brokerage_firm import CompanyShares
            all_cids = list(set(entered_ids) | set(exited_ids))
            company_map = {r.id: r for r in eq_db.query(CompanyShares).filter(
                CompanyShares.id.in_(all_cids)
            ).all()} if all_cids else {}
            for ev in challenges:
                try:
                    ed = _json.loads(ev.effect_data or "{}")
                except Exception:
                    ed = {}
                members_at_start = set(ed.get("index_members_at_start", []))

                for cid in entered_ids:
                    row = company_map.get(cid)
                    if row and (row.founder_id or 0) > 0:
                        if row.founder_id not in members_at_start:
                            record_task_progress(
                                row.founder_id, "wbc50_index_challenge", 1.0
                            )

                for cid in exited_ids:
                    row = company_map.get(cid)
                    if row and (row.founder_id or 0) > 0:
                        if row.founder_id in members_at_start:
                            record_task_progress(
                                row.founder_id, "wbc50_index_challenge", 1.0
                            )
        finally:
            ev_db.close()
    except Exception as e:
        print(f"[{BANK_NAME}] _fire_index_challenge_events error: {e}")


# ==========================
# EXPENSE RATIO COLLECTION
# ==========================

def collect_expense_ratio():
    """
    Deduct the pro-rated annual management fee (0.5 %) from NAV and
    transfer it to the Brokerage Firm as revenue.
    """
    import banks
    from banks.brokerage_firm import firm_add_cash

    bank_db = banks.get_db()
    try:
        entity = bank_db.query(banks.BankEntity).filter(
            banks.BankEntity.bank_id == BANK_ID
        ).first()
        if not entity:
            return

        nav = entity.cash_reserves + entity.asset_value
        if nav <= 0:
            return

        fraction = EXPENSE_RATIO_ANNUAL * EXPENSE_INTERVAL / TICKS_PER_YEAR
        fee = nav * fraction
        if fee <= 0 or entity.cash_reserves < fee:
            return

        entity.cash_reserves    -= fee
        entity.lifetime_expenses += fee
        bank_db.commit()

        firm_add_cash(fee, "index_fund_fee",
                      f"WBC-50 Index Fund management fee (pro-rata {EXPENSE_RATIO_ANNUAL*100:.2f}% annual)")
        print(f"[{BANK_NAME}] 💼 Expense ratio collected: ${fee:,.2f}")
    finally:
        bank_db.close()


# ==========================
# IPO
# ==========================

def execute_ipo():
    """
    Issue all ETF shares into the fund's inventory then list them on the
    open market at the IPO price so players can buy in.
    """
    global ipo_share_price
    try:
        import inventory
        import market

        # Abort if shares already in circulation
        inv_db = inventory.get_db()
        try:
            existing = inv_db.query(inventory.InventoryItem).filter(
                inventory.InventoryItem.item_type == SHARE_ITEM_TYPE,
                inventory.InventoryItem.quantity > 0,
            ).first()
            if existing:
                print(f"[{BANK_NAME}] IPO already executed — shares in circulation. Skipping.")
                return
        finally:
            inv_db.close()

        # Register item type
        if SHARE_ITEM_TYPE not in inventory.ITEM_RECIPES:
            inventory.ITEM_RECIPES[SHARE_ITEM_TYPE] = {
                "name":        "WBC-50 Index Fund Shares",
                "description": "ETF shares tracking the Wadsworth Blue-Chip 50 index",
                "category":    "financial",
            }

        inventory.add_item(BANK_PLAYER_ID, SHARE_ITEM_TYPE, IPO_SHARES)

        order = market.create_order(
            player_id   = BANK_PLAYER_ID,
            order_type  = market.OrderType.SELL,
            order_mode  = market.OrderMode.LIMIT,
            item_type   = SHARE_ITEM_TYPE,
            quantity    = IPO_SHARES,
            price       = ipo_share_price,
        )
        if order:
            print(f"[{BANK_NAME}] 🎉 IPO: {IPO_SHARES:,} shares listed at "
                  f"${ipo_share_price:.4f} (Order #{order.id})")
    except Exception as e:
        print(f"[{BANK_NAME}] IPO error: {e}")
        import traceback; traceback.print_exc()


# ==========================
# INITIALIZATION
# ==========================

def initialize():
    """Register the fund, seed capital from the Brokerage Firm, and execute the IPO."""
    global ipo_share_price, total_firm_funding
    import banks
    from banks.brokerage_firm import firm_deduct_cash

    initialize_tables()

    ipo_share_price = SEED_CAPITAL / IPO_SHARES  # $0.10 per share at launch

    entity = banks.get_bank_entity(BANK_ID)
    if not entity:
        print(f"[{BANK_NAME}] Creating new fund entity...")
        entity = banks.register_bank_entity(BANK_ID, BANK_NAME, BANK_DESCRIPTION)

        # Brokerage Firm seeds the fund
        seeded = firm_deduct_cash(
            SEED_CAPITAL, "index_fund_seed",
            f"{BANK_NAME} initial seed capital"
        )
        if seeded:
            banks.add_bank_revenue(BANK_ID, SEED_CAPITAL, "Brokerage Firm seed capital")
            print(f"[{BANK_NAME}] 💵 Seeded ${SEED_CAPITAL:,.2f} from Brokerage Firm")
        else:
            print(f"[{BANK_NAME}] ⚠️  Brokerage Firm could not seed capital — using $0")

        # Set share structure
        bank_db = banks.get_db()
        try:
            e = bank_db.query(banks.BankEntity).filter(
                banks.BankEntity.bank_id == BANK_ID
            ).first()
            if e:
                e.total_shares_issued = IPO_SHARES
                e.share_price         = ipo_share_price
                bank_db.commit()
        finally:
            bank_db.close()

        execute_ipo()

    print(f"[{BANK_NAME}] Module initialized")
    print(f"  → Strategy: Full Replication, hold {TARGET_HOLDING_MIN*100:.0f}–{TARGET_HOLDING_MAX*100:.0f}% of each WBC-50 constituent")
    print(f"  → IPO: {IPO_SHARES:,} shares at ${ipo_share_price:.4f}")
    print(f"  → Expense ratio: {EXPENSE_RATIO_ANNUAL*100:.2f}% annual")
    print(f"  → Rebalance interval: every {REBALANCE_INTERVAL} ticks")


# ==========================
# TICK HANDLER
# ==========================

async def tick(current_tick: int, now: datetime, bank_entity):
    """
    Periodic operations:
      - Every VALUATION_INTERVAL ticks : recalculate asset_value
      - Every REBALANCE_INTERVAL ticks : rebalance constituent holdings
      - Every EXPENSE_INTERVAL ticks   : collect management fee
    """
    global last_rebalance_tick, last_valuation_tick, last_expense_tick

    if current_tick - last_valuation_tick >= VALUATION_INTERVAL:
        update_asset_valuation()
        last_valuation_tick = current_tick

    if current_tick - last_rebalance_tick >= REBALANCE_INTERVAL:
        rebalance_portfolio()
        last_rebalance_tick = current_tick

    if current_tick - last_expense_tick >= EXPENSE_INTERVAL:
        collect_expense_ratio()
        last_expense_tick = current_tick

    # Maintain standing buy order so players can always sell shares
    from banks import maintain_etf_share_bid
    maintain_etf_share_bid(BANK_ID, BANK_PLAYER_ID, SHARE_ITEM_TYPE, bank_entity, current_tick)

    # Hourly stats
    if current_tick % 3600 == 0:
        try:
            import banks
            e    = banks.get_bank_entity(BANK_ID)
            nav  = (e.cash_reserves + e.asset_value) if e else 0.0
            db   = get_db()
            held = db.query(IndexFundHolding).filter(
                IndexFundHolding.in_index == True,
                IndexFundHolding.shares_held > 0,
            ).count()
            db.close()
            print(f"[{BANK_NAME}] NAV: ${nav:,.2f} | "
                  f"Share: ${e.share_price:.6f} | "
                  f"Positions: {held}/50 | "
                  f"Cash: ${e.cash_reserves:,.2f} | "
                  f"Equity: ${e.asset_value:,.2f}")
        except Exception:
            pass


__all__ = [
    "BANK_ID", "BANK_NAME", "BANK_DESCRIPTION", "BANK_PLAYER_ID",
    "SHARE_ITEM_TYPE", "TARGET_HOLDING_MIN", "TARGET_HOLDING_MAX",
    "initialize", "tick", "get_player_shareholding", "get_all_shareholders",
    "IndexFundHolding",
]
