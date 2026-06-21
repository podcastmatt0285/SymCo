"""
npc.py

NPC (Non-Player Character) module for the economic simulation.

Each NPC is a real Player account that:
  - Owns land plots and runs businesses (production/retail only)
  - Participates in both the regular and district markets
  - Is driven by automated logic every NPC_TICK_INTERVAL ticks
  - Never appears on leaderboards (is_npc = True)
  - Cannot log in and has no city/county/crypto involvement

NPC configs live in npc_configs/<key>.json.
Add a new NPC by dropping a new config file — the engine picks it up on next boot.

Cash state tiers (per NPC config):
  hard_high  → cash above ceiling: buy aggressively to draw down
  high       → between soft_high and hard_high: spend more freely
  comfortable→ between soft_low and soft_high: normal operation
  low        → between hard_low and soft_low: tighten sell margins
  hard_low   → cash below floor: emergency sell at market price, no cost floor

Pricing rule (normal):  sell_price = max(market_price * 1.0002, unit_cost * 1.0002)
Pricing rule (low):     sell_price = max(market_price * 1.0001, unit_cost * 1.0001)
Pricing rule (hard_low):sell_price = market_price  (cost floor bypassed entirely)

Markups are deliberately tiny (0.02% / 0.01%): the price is pegged to a rolling
average of recent trades, so a markup compounds on every fill. A larger markup
(the old 2%) ratcheted the market upward on every NPC sale → runaway inflation.

Order dedup: always check quantity already listed before placing a new order.
Order cancel: evaluate each open order individually — never bulk-nuke.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Optional, Tuple, Type

from database import engine, SessionLocal

# ===========================
# CONSTANTS
# ===========================

# Spread NPC cycles across this many ticks. Each NPC re-quoting ~20 items costs ~1.8s
# (placing + matching orders — inherent matching-engine work), so the more NPCs that run
# in the SAME tick, the longer that tick. At 12 it bunched ~8 NPCs/tick (~15s); 48 spreads
# to ~2/tick (~4s) so the game loop stays responsive. NPCs still re-quote on a steady
# cadence — they're market-makers of last resort, not HFT. Env-tunable for live tuning.
NPC_TICK_INTERVAL    = int(os.environ.get("NPC_TICK_INTERVAL", "48"))  # run NPC logic every N game ticks
PRICE_ROLLING_WINDOW = 20   # number of recent trades for the rolling average

# Sell markup rates by cash state.
# NOTE: these are tiny on purpose. NPC sell prices are pegged to a rolling
# average of recent trades, so any markup compounds every time an NPC order
# fills (each fill nudges the average up, which raises the next listing). A 2%
# markup here produced runaway inflation; 0.02% keeps the market essentially
# flat while still giving NPCs a sliver of margin.
_MARKUP = {
    "hard_high":   0.0002,
    "high":        0.0002,
    "comfortable": 0.0002,
    "low":         0.0001,
    "hard_low":    0.00,   # list at market price, cost floor is bypassed
}

# Cancel a sell order when market has risen this much above the listed price
# (we're leaving money on the table — relist higher)
_SELL_CANCEL_ROSE_THRESHOLD = 0.10   # market > listed * 1.10

# ===========================
# IN-MEMORY STATE
# ===========================

_NPC_CONFIGS: dict = {}   # config_key  -> config dict
_NPC_PLAYERS: dict = {}   # player_id   -> config dict  (populated after seeding)

# Per-tick phase timing (diagnostic): how long the NPC cycle spends in each phase.
_NPC_PHASE: dict = {"spendable": 0.0, "sell": 0.0, "buy": 0.0, "cycles": 0.0}

# Populated by seed_npcs_background(); read by is_ready() and the status endpoint.
_seeding_done:     bool = False
_seeding_progress: int  = 0
_seeding_total:    int  = 0


# ===========================
# CONFIG LOADING
# ===========================

def is_ready() -> bool:
    """Return True once all NPC seeding is complete."""
    return _seeding_done


def seeding_status() -> dict:
    return {"ready": _seeding_done, "progress": _seeding_progress, "total": _seeding_total}


def _load_configs():
    """Load all NPC config files from npc_configs/."""
    global _NPC_CONFIGS
    config_dir = os.path.join(os.path.dirname(__file__), "npc_configs")
    if not os.path.isdir(config_dir):
        return
    for fname in sorted(os.listdir(config_dir)):
        if not fname.endswith(".json"):
            continue
        key = fname[:-5]
        try:
            with open(os.path.join(config_dir, fname)) as f:
                cfg = json.load(f)
            cfg["config_key"] = key   # needed by _seed_npc and batch seeding
            _NPC_CONFIGS[key] = cfg
            print(f"[NPC] Loaded config: {key}")
        except Exception as e:
            print(f"[NPC] Failed to load {fname}: {e}")


# ===========================
# MARKET CLASS HELPERS
# ===========================

def _order_classes(market_key: str) -> Tuple[Type, Type, Type, Type]:
    """
    Return (MarketOrderClass, OrderType, OrderStatus, OrderMode) for the
    requested market.

    district_market exports DistrictMarketOrder / DistrictTrade (not the
    generic names), so we alias them here to keep the rest of the code uniform.
    """
    if market_key == "district":
        from district_market import (
            DistrictMarketOrder as MarketOrder,
            OrderType, OrderStatus, OrderMode,
        )
    else:
        from market import MarketOrder, OrderType, OrderStatus, OrderMode
    return MarketOrder, OrderType, OrderStatus, OrderMode


def _trade_class(market_key: str) -> Type:
    """Return the Trade model for the requested market."""
    if market_key == "district":
        from district_market import DistrictTrade as Trade
    else:
        from market import Trade
    return Trade


def _ttl_memo(ttl: float = 3.0):
    """Tiny per-process TTL cache for the NPC price-reference helpers. These run a
    90-day aggregate query every call and are invoked per-item for every NPC each tick;
    memoizing for a few seconds collapses hundreds of identical queries into one without
    changing behaviour (these are slow-moving valuation references, not the live book)."""
    import time as _t

    def deco(fn):
        store: dict = {}

        def wrapper(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            now = _t.monotonic()
            hit = store.get(key)
            if hit is not None and (now - hit[0]) < ttl:
                return hit[1]
            val = fn(*args, **kwargs)
            store[key] = (now, val)
            return val
        wrapper.__name__ = getattr(fn, "__name__", "memoized")
        return wrapper
    return deco


# ===========================
# ROLLING AVERAGE PRICE
# ===========================

@_ttl_memo(3.0)
def _rolling_avg(item_type: str, market_key: str = "regular") -> Optional[float]:
    """
    Return the rolling average price of the last PRICE_ROLLING_WINDOW trades
    for item_type on either the regular or district market.
    Returns None if no trades exist yet.
    """
    try:
        Trade = _trade_class(market_key)
        db = SessionLocal()
        try:
            recent = (
                db.query(Trade)
                .filter(Trade.item_type == item_type)
                .order_by(Trade.executed_at.desc())
                .limit(PRICE_ROLLING_WINDOW)
                .all()
            )
            if not recent:
                return None
            return sum(t.price for t in recent) / len(recent)
        finally:
            db.close()
    except Exception:
        return None


def _get_market_price(item_type: str, market_key: str = "regular") -> Optional[float]:
    """Get current last-trade/midpoint price from the appropriate market."""
    try:
        if market_key == "district":
            from district_market import get_market_price
        else:
            from market import get_market_price
        return get_market_price(item_type)
    except Exception:
        return None


@_ttl_memo(3.0)
def _human_anchor(item_type: str, market_key: str = "regular") -> Optional[float]:
    """Average price of recent trades involving at least one HUMAN player
    (buyer_id > 0 or seller_id > 0), last 90 days.

    This is the wash-proof price reference: NPC↔NPC trades cannot move it.
    The plain rolling average is useless as a runaway guard because the wash
    loop raises the average itself — the 5× cap then climbs with the disease
    it's meant to stop (observed: two grocer NPCs ratcheting jam from $4.86
    to $110 BILLION/unit by ping-ponging it at +5-10% per round trip).

    Fallback when NO human traded the item in the window: 4× the 90-day
    MINIMUM trade price. Wash trading only ever pushes prices UP, so the
    minimum is the one statistic the ratchet cannot poison. (With the 5×
    cap applied on top, NPC references stay within 20× of the pre-ratchet
    floor until a human trade re-anchors the item at its real level.)
    Returns None only when the item has no trades at all.
    """
    try:
        from sqlalchemy import func as _f
        Trade = _trade_class(market_key)
        db = SessionLocal()
        try:
            cutoff = datetime.utcnow() - timedelta(days=90)
            rows = (
                db.query(Trade.price)
                .filter(
                    Trade.item_type == item_type,
                    Trade.executed_at >= cutoff,
                    (Trade.buyer_id > 0) | (Trade.seller_id > 0),
                )
                .order_by(Trade.executed_at.desc())
                .limit(PRICE_ROLLING_WINDOW)
                .all()
            )
            if rows:
                return sum(r[0] for r in rows) / len(rows)
            min_px = (
                db.query(_f.min(Trade.price))
                .filter(Trade.item_type == item_type,
                        Trade.executed_at >= cutoff,
                        Trade.price > 0)
                .scalar()
            )
            if min_px and min_px > 0:
                return float(min_px) * 4
            return None
        finally:
            db.close()
    except Exception:
        return None


def _tame_reference_price(item_type: str, market_key: str,
                          market_price: Optional[float]) -> Optional[float]:
    """Clamp a market-price reference to 5× the human-anchored average.

    Every downstream NPC decision (cancel thresholds, bid prices, ask prices)
    keys off this reference; clamping it once here means a wash-ratcheted
    midpoint/last-trade can never drag NPC pricing along with it."""
    if not market_price:
        return market_price
    anchor = _human_anchor(item_type, market_key)
    if anchor and anchor > 0 and market_price > anchor * 5:
        return anchor * 5
    return market_price


# ===========================
# UNIT COST CALCULATION
# ===========================

def _calculate_unit_cost(business_type: str, output_item: str) -> Optional[float]:
    """
    Calculate production cost per unit of output_item for a given business type.

    Cost = (sum of each input's rolling_avg_price * input_qty  +  base_wage_cost)
           / output_quantity

    Returns None if the business config can't be found.
    Uses 0.0 for missing prices so the market-price floor still applies.
    """
    try:
        from business import BUSINESS_TYPES, get_district_business_types
        all_types = {**BUSINESS_TYPES, **get_district_business_types()}
        config = all_types.get(business_type)
        if not config:
            return None

        wage = config.get("base_wage_cost", 0.0)

        for line in config.get("production_lines", []):
            if line.get("output_item") != output_item:
                continue
            output_qty = line.get("output_qty", 0)
            if output_qty <= 0:
                continue

            input_cost = 0.0
            for inp in line.get("inputs", []):
                inp_item = inp["item"]
                inp_qty  = inp["quantity"]
                # Try regular market first, then district
                avg = _rolling_avg(inp_item, "regular")
                if avg is None:
                    avg = _rolling_avg(inp_item, "district")
                input_cost += (avg or 0.0) * inp_qty

            return (input_cost + wage) / output_qty

    except Exception as e:
        print(f"[NPC] Unit cost error ({business_type}/{output_item}): {e}")
    return None


# ===========================
# CASH STATE
# ===========================

def _cash_state(cash: float, caps: dict) -> str:
    """
    Map a cash balance to one of five named states using the NPC's cap config.
    """
    if cash >= caps["hard_high"]:
        return "hard_high"
    if cash >= caps["soft_high"]:
        return "high"
    if cash >= caps["soft_low"]:
        return "comfortable"
    if cash >= caps["hard_low"]:
        return "low"
    return "hard_low"


# ===========================
# SELL ORDER MANAGEMENT
# ===========================

def _manage_sell_orders(player_id: int, cfg: dict, state: str, inv_qty: dict = None):
    """
    For each item in sell_items:
    1. Evaluate each open order individually; cancel where warranted.
    2. Sum remaining listed quantity after cancellations.
    3. Place a new order only for the delta still needed.
    """
    if inv_qty is None:
        inv_qty = _load_inventory_map(player_id)

    markup = _MARKUP[state]

    for item_type, sell_cfg in cfg.get("sell_items", {}).items():
        try:
            market_key = sell_cfg.get("market", "regular")
            min_keep   = sell_cfg.get("min_inventory_to_keep", 0)
            max_order  = sell_cfg.get("max_order_quantity", 10_000)

            current_inv  = inv_qty.get(item_type, 0.0)
            want_to_sell = current_inv - min_keep
            if want_to_sell <= 0:
                continue

            market_price = _tame_reference_price(
                item_type, market_key, _get_market_price(item_type, market_key))
            MarketOrder, OrderType, OrderStatus, _ = _order_classes(market_key)

            # --- Step 1: evaluate existing orders, cancel where warranted ---
            db = SessionLocal()
            try:
                active = (
                    db.query(MarketOrder)
                    .filter(
                        MarketOrder.player_id == player_id,
                        MarketOrder.order_type == OrderType.SELL,
                        MarketOrder.item_type  == item_type,
                        MarketOrder.status.in_([OrderStatus.ACTIVE,
                                                OrderStatus.PARTIALLY_FILLED]),
                    )
                    .all()
                )

                for order in active:
                    cancel = False
                    if market_price and order.price:
                        # Market rose >10% above our listing — relist higher
                        if market_price > order.price * (1 + _SELL_CANCEL_ROSE_THRESHOLD):
                            cancel = True
                            print(f"[NPC] Cancel sell #{order.id} {item_type}: "
                                  f"market ${market_price:.4f} > listed ${order.price:.4f} +10%")
                        # Hard-low emergency: cancel and relist at bare market price
                        elif state == "hard_low" and order.price > market_price * 1.005:
                            cancel = True
                            print(f"[NPC] Cancel sell #{order.id} {item_type}: "
                                  f"hard_low emergency, relisting at market")
                    if cancel:
                        order.status = OrderStatus.CANCELLED

                db.commit()
                # Step 2 (merged): remaining listed qty = the orders we did NOT cancel,
                # computed in-memory from the rows we already loaded — no second query/session.
                already_listed = sum(
                    (o.quantity - o.quantity_filled)
                    for o in active if o.status != OrderStatus.CANCELLED
                )
            finally:
                db.close()

            need_to_list = want_to_sell - already_listed
            if need_to_list <= 0:
                continue   # fully covered by open orders

            # --- Step 3: calculate target sell price ---
            unit_cost = None
            for biz_cfg in cfg.get("businesses", []):
                uc = _calculate_unit_cost(biz_cfg["business_type"], item_type)
                if uc is not None:
                    unit_cost = uc
                    break

            base = market_price if market_price else (unit_cost or 1.0)
            sell_price = base * (1 + markup)

            # Apply cost floor except in hard_low emergency (must move inventory)
            if state != "hard_low" and unit_cost and unit_cost > 0:
                sell_price = max(sell_price, unit_cost * (1 + markup))

            qty = min(need_to_list, max_order)

            # --- Step 4: place the order ---
            if market_key == "district":
                from district_market import create_order, OrderType, OrderMode
            else:
                from market import create_order, OrderType, OrderMode

            create_order(
                player_id  = player_id,
                order_type = OrderType.SELL,
                order_mode = OrderMode.LIMIT,
                item_type  = item_type,
                quantity   = qty,
                price      = round(sell_price, 4),
            )
            print(f"[NPC] {cfg['business_name']}: listed {qty:.0f}x {item_type} "
                  f"@ ${sell_price:.4f} (state={state})")

        except Exception as e:
            import traceback
            print(f"[NPC] Sell order error ({cfg['business_name']}/{item_type}): {e}")
            traceback.print_exc()


# ===========================
# BUY ORDER MANAGEMENT
# ===========================

def _manage_buy_orders(player_id: int, cfg: dict, state: str, inv_qty: dict = None):
    """
    For each item in buy_items:
    1. Cancel open buy orders that are no longer needed or are stale/unaffordable.
    2. Place a new buy order for the delta needed to reach target_inventory.
    """
    if inv_qty is None:
        inv_qty = _load_inventory_map(player_id)

    for item_type, buy_cfg in cfg.get("buy_items", {}).items():
        try:
            market_key = buy_cfg.get("market", "regular")
            reorder_at = buy_cfg.get("reorder_at", 0)
            target_inv = buy_cfg.get("target_inventory", 0)
            max_mult   = buy_cfg.get("max_price_multiplier", 1.10)

            current_inv  = inv_qty.get(item_type, 0.0)
            market_price = _tame_reference_price(
                item_type, market_key, _get_market_price(item_type, market_key))
            MarketOrder, OrderType, OrderStatus, _ = _order_classes(market_key)

            # --- Step 1: evaluate and cancel stale buy orders ---
            db = SessionLocal()
            try:
                active = (
                    db.query(MarketOrder)
                    .filter(
                        MarketOrder.player_id == player_id,
                        MarketOrder.order_type == OrderType.BUY,
                        MarketOrder.item_type  == item_type,
                        MarketOrder.status.in_([OrderStatus.ACTIVE,
                                                OrderStatus.PARTIALLY_FILLED]),
                    )
                    .all()
                )

                for order in active:
                    cancel = False
                    # Inventory target already met — no longer need more
                    if current_inv >= target_inv:
                        cancel = True
                        print(f"[NPC] Cancel buy #{order.id} {item_type}: "
                              f"inventory target met ({current_inv:.0f}/{target_inv})")
                    # Cash emergency: stop all spending
                    elif state == "hard_low":
                        cancel = True
                        print(f"[NPC] Cancel buy #{order.id} {item_type}: hard_low cash")
                    # Bid is now >30% below market — will never fill
                    elif (market_price and order.price
                          and order.price < market_price * 0.70):
                        cancel = True
                        print(f"[NPC] Cancel buy #{order.id} {item_type}: "
                              f"stale bid ${order.price:.4f} vs market ${market_price:.4f}")
                    if cancel:
                        order.status = OrderStatus.CANCELLED

                db.commit()
            finally:
                db.close()

            # --- Step 2: decide whether to buy at all ---
            if state == "hard_low":
                continue   # no spending in emergency cash state

            # Buy if below reorder threshold OR deploying excess cash
            should_buy = (
                current_inv < reorder_at
                or state in ("hard_high", "high")
            )
            if not should_buy:
                continue

            if not market_price:
                continue   # no price reference — can't bid

            # --- Step 3: calculate order delta ---
            db = SessionLocal()
            try:
                pending = (
                    db.query(MarketOrder)
                    .filter(
                        MarketOrder.player_id == player_id,
                        MarketOrder.order_type == OrderType.BUY,
                        MarketOrder.item_type  == item_type,
                        MarketOrder.status.in_([OrderStatus.ACTIVE,
                                                OrderStatus.PARTIALLY_FILLED]),
                    )
                    .all()
                )
                already_ordered = sum(o.quantity - o.quantity_filled for o in pending)
            finally:
                db.close()

            target_buy = target_inv - current_inv - already_ordered
            if target_buy <= 0:
                continue   # already covered by pending orders

            # --- Step 4: place the buy order ---
            buy_price = round(market_price * max_mult, 4)

            # Sanity cap (defense-in-depth): never bid more than 5× the rolling
            # trade average. Without this, any price-source that reflects resting
            # bids can ratchet upward every cycle (NPC bids above "market" →
            # becomes new "market" → next NPC bids higher), exploding into a
            # runaway that floods the order book and overloads the database.
            _ref = _rolling_avg(item_type, market_key)
            if _ref and _ref > 0 and buy_price > _ref * 5:
                buy_price = round(_ref * 5, 4)
                print(f"[NPC] Capped {item_type} bid to 5× rolling avg "
                      f"(${_ref:.4f}) — runaway guard")

            if market_key == "district":
                from district_market import create_order, OrderType, OrderMode
            else:
                from market import create_order, OrderType, OrderMode

            create_order(
                player_id  = player_id,
                order_type = OrderType.BUY,
                order_mode = OrderMode.LIMIT,
                item_type  = item_type,
                quantity   = target_buy,
                price      = buy_price,
            )
            print(f"[NPC] {cfg['business_name']}: buy order {target_buy:.0f}x {item_type} "
                  f"@ ${buy_price:.4f} (state={state})")

        except Exception as e:
            import traceback
            print(f"[NPC] Buy order error ({cfg['business_name']}/{item_type}): {e}")
            traceback.print_exc()


# ===========================
# NPC DECISION CYCLE
# ===========================

def _load_inventory_map(player_id: int) -> dict:
    """All of an NPC's item quantities in one query → {item_type: qty}. Replaces dozens of
    per-item get_item_quantity() calls (each its own session/round-trip) per cycle."""
    try:
        from inventory import InventoryItem
        from sqlalchemy import func as _f
        db = SessionLocal()
        try:
            rows = (db.query(InventoryItem.item_type, _f.sum(InventoryItem.quantity))
                    .filter(InventoryItem.player_id == player_id)
                    .group_by(InventoryItem.item_type).all())
            return {it: float(q or 0.0) for it, q in rows}
        finally:
            db.close()
    except Exception:
        return {}


def _run_npc_cycle(player_id: int, cfg: dict):
    """
    Run one full automated decision cycle for a single NPC.
    Called every NPC_TICK_INTERVAL ticks.
    """
    try:
        # Tender-aware buying power: an NPC mandated to a foreign currency earns and
        # holds that currency (income routes through convert_to_legal_tender), so its
        # USD balance drains to ~0. get_spendable_usd expresses tender + USD holdings
        # in USD terms, so cash-state stays accurate after a currency mandate. For
        # USD-tender NPCs this returns exactly the USD balance — no behavior change.
        import time as _pt
        from reserve_banks import get_spendable_usd
        _a = _pt.monotonic()
        cash  = get_spendable_usd(player_id)
        state = _cash_state(cash, cfg["cash_caps"])
        # Load this NPC's whole inventory in ONE query and reuse it across every sell/buy
        # item, instead of a per-item get_item_quantity() that opened a fresh DB session
        # (a round-trip) each time.
        inv_qty = _load_inventory_map(player_id)
        _b = _pt.monotonic()
        _manage_sell_orders(player_id, cfg, state, inv_qty)
        _c = _pt.monotonic()
        _manage_buy_orders(player_id, cfg, state, inv_qty)
        _d = _pt.monotonic()
        _NPC_PHASE["spendable"] += _b - _a
        _NPC_PHASE["sell"]      += _c - _b
        _NPC_PHASE["buy"]       += _d - _c
        _NPC_PHASE["cycles"]    += 1
    except Exception as e:
        import traceback
        print(f"[NPC] Cycle error for {cfg.get('business_name', player_id)}: {e}")
        traceback.print_exc()


# ===========================
# SEEDING HELPERS
# ===========================

def _build_paused_lines(business_type: str, active_lines: list) -> str:
    """
    Given a business type and the list of output-item names that should be
    ACTIVE, return a JSON string of line indices to pause (all others).

    If active_lines is empty or None, all lines run (returns "[]").
    """
    if not active_lines:
        return "[]"

    try:
        from business import BUSINESS_TYPES, get_district_business_types
        all_types = {**BUSINESS_TYPES, **get_district_business_types()}
        config = all_types.get(business_type, {})
        lines  = config.get("production_lines", [])

        paused = []
        for idx, line in enumerate(lines):
            # Pause this line if its output item is not in active_lines
            if line.get("output_item") not in active_lines:
                paused.append(idx)

        return json.dumps(paused)
    except Exception as e:
        print(f"[NPC] Could not build paused_lines for {business_type}: {e}")
        return "[]"


def _seed_businesses(player_id: int, cfg: dict, db, plot_ids: list,
                     seeded_district_ids: list = None):
    """
    Create Business rows for the NPC and mark land plots/districts as occupied.
    Called both on first-time seed and on partial-seed recovery.

    seeded_district_ids: list of district DB IDs created during this seed run,
    referenced by businesses via the ``district_seed_index`` config field.

    Batches all business inserts into a single commit, then batches all
    plot/district occupation updates into a second commit.
    """
    from business import Business, BUSINESS_TYPES, get_district_business_types
    from land import LandPlot

    all_types = {**BUSINESS_TYPES, **get_district_business_types()}
    plot_iter = iter(plot_ids)
    seeded_district_ids = seeded_district_ids or []

    # Accumulate (biz_obj, plot_id, district_id) — insert all at once below.
    pending = []

    for biz_cfg in cfg.get("businesses", []):
        btype = biz_cfg["business_type"]
        if btype not in all_types:
            print(f"[NPC]   WARNING: unknown business_type {btype!r} — skipping")
            continue

        district_id = biz_cfg.get("district_id")
        plot_id     = None

        seed_idx = biz_cfg.get("district_seed_index")
        if seed_idx is not None:
            if seed_idx < len(seeded_district_ids):
                district_id = seeded_district_ids[seed_idx]
            else:
                print(f"[NPC]   WARNING: district_seed_index {seed_idx} out of range — skipping {btype}")
                continue

        if not district_id:
            plot_id = next(plot_iter, None)
            if plot_id is None:
                print(f"[NPC]   WARNING: no land plot available for {btype} — skipping")
                continue

        paused_lines       = _build_paused_lines(btype, biz_cfg.get("active_lines", []))
        cycles_to_complete = all_types[btype].get("cycles_to_complete", 1)

        biz = Business(
            owner_id        = player_id,
            land_plot_id    = plot_id,
            district_id     = district_id,
            business_type   = btype,
            is_active       = True,
            paused_lines    = paused_lines,
            progress_ticks  = cycles_to_complete,
        )
        db.add(biz)
        pending.append((biz, plot_id, district_id))

    # Flush to get DB-assigned IDs via RETURNING before committing.
    db.flush()
    # Capture everything we need before commit expires the ORM objects.
    resolved = [(biz.id, biz.business_type, biz.paused_lines, plot_id, district_id)
                for biz, plot_id, district_id in pending]
    db.commit()

    # Batch-update plot/district occupation (one commit for all).
    for biz_id, btype, paused, plot_id, district_id in resolved:
        if plot_id:
            plot = db.query(LandPlot).filter(LandPlot.id == plot_id).first()
            if plot:
                plot.occupied_by_business_id = biz_id
        if district_id:
            from districts import District
            dist = db.query(District).filter(District.id == district_id).first()
            if dist:
                dist.occupied_by_business_id = biz_id
        print(f"[NPC]   Business {biz_id} ({btype}) — paused: {paused} — "
              f"{'district ' + str(district_id) if district_id else 'plot ' + str(plot_id)}")
    db.commit()


# ===========================
# SEEDING
# ===========================

def _maybe_ipo_npc(player_id: int, cfg: dict):
    """Launch a Quad-Class IPO for an NPC if the config has an 'ipo' block and no
    active CompanyShares record exists yet."""
    ipo_cfg = cfg.get("ipo")
    if not ipo_cfg:
        return
    try:
        from banks.brokerage_firm import CompanyShares, create_player_ipo, IPOType
        db = SessionLocal()
        try:
            existing = db.query(CompanyShares).filter(
                CompanyShares.founder_id == player_id,
                CompanyShares.is_delisted == False,
                CompanyShares.parent_company_id == None,
            ).first()
            if existing:
                return
        finally:
            db.close()
        company, err = create_player_ipo(
            founder_id=player_id,
            company_name=cfg["business_name"],
            ticker_symbol=ipo_cfg["ticker"],
            ipo_type=IPOType.QUAD_CLASS,
            shares_to_offer=ipo_cfg["shares_to_offer"],
            total_shares=ipo_cfg["total_shares"],
        )
        if err:
            print(f"[NPC] IPO failed for {cfg['business_name']}: {err}")
        else:
            print(f"[NPC] IPO launched: {cfg['business_name']} ({ipo_cfg['ticker']}) — Quad-Class")
    except Exception as e:
        import traceback
        print(f"[NPC] IPO error for {cfg.get('business_name')}: {e}")
        traceback.print_exc()


def _seed_npc(cfg: dict):
    """
    Create the NPC Player row and all starting assets if they don't already exist.

    Idempotent and recovery-aware:
      - If the Player row exists AND has at least one business → fully seeded, skip.
      - If the Player row exists but has NO businesses → partial seed from a prior
        failed run; land plots are re-queried and business creation is completed.
      - If the Player row doesn't exist → full seed from scratch.
    """
    from auth import Player
    from reserve_banks import credit_usd
    from business import Business
    from land import LandPlot  # still needed for partial-seed recovery query

    player_id = cfg["player_id"]
    db = SessionLocal()
    try:
        existing = db.query(Player).filter(Player.id == player_id).first()

        if existing:
            cfg_businesses = cfg.get("businesses", [])
            existing_biz_count = (
                db.query(Business).filter(Business.owner_id == player_id).count()
            )

            if existing_biz_count >= len(cfg_businesses):
                _NPC_PLAYERS[player_id] = cfg
                print(f"[NPC] {cfg['business_name']} already seeded (id={player_id})")

                # Build a set of business types the config wants.
                cfg_types = [b["business_type"] for b in cfg_businesses]

                existing_bizs = (
                    db.query(Business)
                    .filter(Business.owner_id == player_id)
                    .order_by(Business.id.asc())
                    .all()
                )

                # Remove any businesses whose type is no longer in the config
                # (e.g. plantation removed from EO Co config).
                for biz in existing_bizs:
                    if biz.business_type not in cfg_types:
                        print(f"[NPC] {cfg['business_name']}: removing obsolete "
                              f"'{biz.business_type}' (id={biz.id}) — not in config")
                        db.delete(biz)
                db.flush()

                # Sync paused_lines by business_type (not positional index) so
                # changes to active_lines in the JSON take effect without a DB wipe.
                cfg_by_type = {b["business_type"]: b for b in cfg_businesses}
                for biz in existing_bizs:
                    if biz in db.deleted:
                        continue
                    biz_cfg = cfg_by_type.get(biz.business_type)
                    if biz_cfg:
                        new_paused = _build_paused_lines(
                            biz.business_type,
                            biz_cfg.get("active_lines", [])
                        )
                        if biz.paused_lines != new_paused:
                            biz.paused_lines = new_paused
                db.commit()

                # Cash rescue: if the NPC's balance has fallen below hard_low
                # (e.g. due to a prior routing bug), top it up to soft_low so
                # the NPC can immediately resume buying inputs.
                # Measured as the USD value of ALL currency balances — a
                # currency-mandated NPC (e.g. tender = TRY) holds little or no
                # USD by design and must not be "rescued" with fresh money it
                # doesn't need. credit_usd() itself converts the top-up into
                # the NPC's legal tender.
                from reserve_banks import get_player_currency_balances, credit_usd
                current_cash = sum(
                    b["usd_value"] for b in get_player_currency_balances(player_id)
                )
                caps = cfg.get("cash_caps", {})
                hard_low_cap = caps.get("hard_low", 0)
                soft_low_cap = caps.get("soft_low", 0)
                if current_cash < hard_low_cap and soft_low_cap > current_cash:
                    shortfall = soft_low_cap - current_cash
                    credit_usd(player_id, shortfall)
                    print(f"[NPC] {cfg['business_name']}: cash rescue "
                          f"${current_cash:,.0f} → ${soft_low_cap:,.0f}")

                # Inventory rescue: ensure the NPC has at least its configured
                # starting_inventory for each item.  Only tops up items where
                # the NPC has ZERO — avoids re-seeding normal operating stock.
                seed_inv = cfg.get("seed", {}).get("starting_inventory", {})
                if seed_inv:
                    import inventory as _inv
                    for item, qty in seed_inv.items():
                        current_qty = _inv.get_item_quantity(player_id, item)
                        if current_qty == 0:
                            _inv.add_item(player_id, item, qty)
                            print(f"[NPC] {cfg['business_name']}: inventory rescue "
                                  f"+{qty} {item} (was 0)")

                _maybe_ipo_npc(player_id, cfg)
                return

            # Config has more businesses than exist in DB — seed the remainder.
            # This covers both the "partial first-boot" case and "new business added
            # to config after NPC was already running" case.
            missing_biz_cfgs = cfg_businesses[existing_biz_count:]
            print(f"[NPC] {cfg['business_name']}: {existing_biz_count}/{len(cfg_businesses)} "
                  f"businesses present, seeding {len(missing_biz_cfgs)} more…")

            # Vacant plots already owned by this NPC (e.g. given via admin dashboard)
            vacant_ids = [
                p.id for p in
                db.query(LandPlot)
                .filter(LandPlot.owner_id == player_id,
                        LandPlot.occupied_by_business_id == None)
                .order_by(LandPlot.id.asc())
                .all()
            ]

            # Build the plot_id list for the missing land-based businesses,
            # creating new plots from seed config when no vacant plot is available.
            seed_plots = cfg.get("seed", {}).get("land_plots", [])
            seed_plot_idx = existing_biz_count
            plot_ids_for_missing = []

            for biz_cfg in missing_biz_cfgs:
                if biz_cfg.get("district_id") or biz_cfg.get("district_seed_index") is not None:
                    continue  # district business — consumes no land plot
                if vacant_ids:
                    plot_ids_for_missing.append(vacant_ids.pop(0))
                elif seed_plot_idx < len(seed_plots):
                    from land import create_land_plot
                    plot_cfg = seed_plots[seed_plot_idx]
                    plot = create_land_plot(
                        owner_id          = player_id,
                        terrain_type      = plot_cfg["terrain_type"],
                        proximity_features= plot_cfg.get("proximity_features", []),
                        size              = plot_cfg.get("size", 1.0),
                    )
                    plot_ids_for_missing.append(plot.id)
                    print(f"[NPC]   Land plot {plot.id} ({plot_cfg['terrain_type']})")
                else:
                    print(f"[NPC]   WARNING: no plot available for business at config "
                          f"index {seed_plot_idx} — will skip")
                seed_plot_idx += 1

            # Re-query existing districts owned by this NPC (ordered by id)
            from districts import District as DistrictModel, DISTRICT_TYPES
            existing_district_ids = [
                d.id for d in
                db.query(DistrictModel)
                .filter(DistrictModel.owner_id == player_id)
                .order_by(DistrictModel.id.asc())
                .all()
            ]

            # Create any districts in the config that don't exist yet
            seed_districts = cfg.get("seed", {}).get("districts", [])
            for dist_idx, dist_cfg in enumerate(seed_districts):
                if dist_idx < len(existing_district_ids):
                    continue  # already exists
                dtype = dist_cfg["district_type"]
                if dtype not in DISTRICT_TYPES:
                    print(f"[NPC]   WARNING: unknown district_type {dtype!r} — skipping")
                    continue
                dt_info = DISTRICT_TYPES[dtype]
                district = DistrictModel(
                    owner_id      = player_id,
                    district_type = dtype,
                    terrain_type  = dt_info["district_terrain"],
                    size          = dist_cfg.get("size", 3.0),
                    plots_merged  = dist_cfg.get("plots_merged", 3),
                    monthly_tax   = dt_info["base_tax"],
                )
                db.add(district)
                db.commit()
                db.refresh(district)
                existing_district_ids.append(district.id)
                print(f"[NPC]   District {district.id} ({dtype} → {dt_info['district_terrain']}) [recovery]")

            _seed_businesses(player_id, {**cfg, "businesses": missing_biz_cfgs},
                             db, plot_ids_for_missing,
                             seeded_district_ids=existing_district_ids)
            _NPC_PLAYERS[player_id] = cfg
            print(f"[NPC] Update complete: {cfg['business_name']}")
            _maybe_ipo_npc(player_id, cfg)
            return

        # ---- Full seed from scratch ----
        print(f"[NPC] Seeding: {cfg['business_name']} (player_id={player_id})")

        npc = Player(
            id             = player_id,
            business_name  = cfg["business_name"],
            password_hash  = "npc_no_login_" + str(player_id),
            is_npc         = True,
            npc_config_key = cfg.get("config_key", ""),
        )
        db.add(npc)
        db.commit()

        # Starting cash
        seed          = cfg.get("seed", {})
        starting_cash = seed.get("starting_cash", 50_000.0)
        credit_usd(player_id, starting_cash)
        print(f"[NPC]   Cash: ${starting_cash:,.0f}")

        # Starting inventory
        if seed.get("starting_inventory"):
            import inventory as inv
            for item, qty in seed["starting_inventory"].items():
                inv.add_item(player_id, item, qty)
            print(f"[NPC]   Inventory: {seed['starting_inventory']}")

        # Land plots
        plot_ids = []
        for plot_cfg in seed.get("land_plots", []):
            from land import create_land_plot
            proximity = plot_cfg.get("proximity_features", [])
            plot = create_land_plot(
                owner_id          = player_id,
                terrain_type      = plot_cfg["terrain_type"],
                proximity_features= proximity,
                size              = plot_cfg.get("size", 1.0),
            )
            plot_ids.append(plot.id)
            print(f"[NPC]   Land plot {plot.id} ({plot_cfg['terrain_type']})")

        # Districts (seeded directly — no merge cost for NPCs)
        seeded_district_ids = []
        for dist_cfg in seed.get("districts", []):
            from districts import District, DISTRICT_TYPES
            dtype = dist_cfg["district_type"]
            if dtype not in DISTRICT_TYPES:
                print(f"[NPC]   WARNING: unknown district_type {dtype!r} — skipping")
                continue
            dt_info = DISTRICT_TYPES[dtype]
            district = District(
                owner_id      = player_id,
                district_type = dtype,
                terrain_type  = dt_info["district_terrain"],
                size          = dist_cfg.get("size", 3.0),
                plots_merged  = dist_cfg.get("plots_merged", 3),
                monthly_tax   = dt_info["base_tax"],
            )
            db.add(district)
            db.commit()
            db.refresh(district)
            seeded_district_ids.append(district.id)
            print(f"[NPC]   District {district.id} ({dtype} → {dt_info['district_terrain']})")

        # Businesses (with active_lines respected)
        _seed_businesses(player_id, cfg, db, plot_ids,
                         seeded_district_ids=seeded_district_ids)

        _NPC_PLAYERS[player_id] = cfg
        print(f"[NPC] Seeding complete: {cfg['business_name']}")
        _maybe_ipo_npc(player_id, cfg)

    except Exception as e:
        import traceback
        print(f"[NPC] Seeding failed for {cfg.get('business_name')}: {e}")
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


# ===========================
# BATCH SEEDING HELPERS
# ===========================

def _create_land_plots_batch(player_id: int, plot_cfgs: list, db) -> list:
    """
    Create all LandPlot rows for one NPC in a single commit.
    Uses the same tax calculation as land.create_land_plot() but avoids
    opening a new session per plot.  Returns a list of plot IDs.
    """
    if not plot_cfgs:
        return []
    from land import LandPlot, TERRAIN_TYPES, PROXIMITY_FEATURES, STARTING_EFFICIENCY

    plots = []
    for cfg in plot_cfgs:
        terrain  = cfg.get("terrain_type", "prairie")
        if terrain not in TERRAIN_TYPES:
            terrain = "prairie"
        proximity = cfg.get("proximity_features", [])
        size      = cfg.get("size", 1.0)

        base_tax  = TERRAIN_TYPES[terrain]["base_tax"]
        tax_mod   = 1.0
        for feat in proximity:
            if feat in PROXIMITY_FEATURES:
                tax_mod *= PROXIMITY_FEATURES[feat]["tax_modifier"]

        plots.append(LandPlot(
            owner_id          = player_id,
            terrain_type      = terrain,
            proximity_features= ",".join(proximity) if proximity else None,
            efficiency        = STARTING_EFFICIENCY,
            size              = size,
            monthly_tax       = base_tax * size * tax_mod,
            is_starter_plot   = False,
            is_government_owned = False,
        ))

    db.add_all(plots)
    db.flush()                         # populates p.id via RETURNING before commit
    plot_ids = [p.id for p in plots]   # capture IDs before commit expires the objects
    summaries = [(p.id, p.terrain_type) for p in plots]
    db.commit()

    for pid, terrain in summaries:
        print(f"[NPC]   Land plot {pid} ({terrain})")

    return plot_ids


def _seed_npc_assets(cfg: dict):
    """
    Create land plots, districts, and businesses for an NPC whose Player row,
    currency balance, and starting inventory have already been batch-inserted.
    """
    player_id = cfg["player_id"]
    seed      = cfg.get("seed", {})
    db        = SessionLocal()
    try:
        plot_ids = _create_land_plots_batch(player_id, seed.get("land_plots", []), db)

        seeded_district_ids = []
        for dist_cfg in seed.get("districts", []):
            from districts import District, DISTRICT_TYPES
            dtype = dist_cfg["district_type"]
            if dtype not in DISTRICT_TYPES:
                print(f"[NPC]   WARNING: unknown district_type {dtype!r} — skipping")
                continue
            dt_info  = DISTRICT_TYPES[dtype]
            district = District(
                owner_id      = player_id,
                district_type = dtype,
                terrain_type  = dt_info["district_terrain"],
                size          = dist_cfg.get("size", 3.0),
                plots_merged  = dist_cfg.get("plots_merged", 3),
                monthly_tax   = dt_info["base_tax"],
            )
            db.add(district)
            db.commit()
            db.refresh(district)
            seeded_district_ids.append(district.id)
            print(f"[NPC]   District {district.id} ({dtype})")

        _seed_businesses(player_id, cfg, db, plot_ids,
                         seeded_district_ids=seeded_district_ids)
        print(f"[NPC] Seeding complete: {cfg['business_name']}")

    except Exception as e:
        import traceback
        print(f"[NPC] Asset seed failed for {cfg.get('business_name')}: {e}")
        traceback.print_exc()
        db.rollback()
        raise   # propagate so caller skips _NPC_PLAYERS registration
    finally:
        db.close()


def seed_npcs_background():
    """
    Seed all NPC accounts.  Designed to run in a background thread so the web
    server can start accepting requests immediately.

    Fresh NPCs (no Player row yet) are batch-inserted in 3 bulk commits
    (Players → currency balances → inventory items) before per-NPC land/business
    creation, reducing first-boot DB round-trips by ~7×.

    Existing NPCs go through the regular _seed_npc() update/rescue path.

    Sets _seeding_done = True when finished.
    """
    global _seeding_done, _seeding_progress, _seeding_total
    import traceback

    from auth import Player
    from inventory import InventoryItem
    from reserve_banks import PlayerCurrencyBalance, get_db as rb_get_db

    all_cfgs       = list(_NPC_CONFIGS.values())
    _seeding_total  = len(all_cfgs)

    # ── Step 1: find which NPCs already have a Player row ─────────────────────
    db = SessionLocal()
    try:
        existing_ids = {
            row[0] for row in
            db.query(Player.id)
              .filter(Player.id.in_([c["player_id"] for c in all_cfgs]))
              .all()
        }
    finally:
        db.close()

    fresh_cfgs    = [c for c in all_cfgs if c["player_id"] not in existing_ids]
    existing_cfgs = [c for c in all_cfgs if c["player_id"] in existing_ids]

    # ── Step 2: batch-insert base rows for fresh NPCs ─────────────────────────
    if fresh_cfgs:
        db = SessionLocal()
        batch_ok = False
        try:
            print(f"[NPC] Batch-seeding {len(fresh_cfgs)} new NPC(s)…")

            # 2a. All Player rows in one commit.
            db.add_all([
                Player(
                    id             = c["player_id"],
                    business_name  = c["business_name"],
                    password_hash  = "npc_no_login_" + str(c["player_id"]),
                    is_npc         = True,
                    npc_config_key = c.get("config_key", ""),
                )
                for c in fresh_cfgs
            ])
            db.commit()
            print(f"[NPC]   {len(fresh_cfgs)} Player rows inserted")

            # 2b. All USD currency balances — must use reserve_banks session,
            # not the main-app session (player_currency_balances lives there).
            rb_db = rb_get_db()
            try:
                rb_db.add_all([
                    PlayerCurrencyBalance(
                        player_id     = c["player_id"],
                        currency_code = "USD",
                        balance       = float(c.get("seed", {}).get("starting_cash", 50_000.0)),
                    )
                    for c in fresh_cfgs
                ])
                rb_db.commit()
            finally:
                rb_db.close()
            print(f"[NPC]   {len(fresh_cfgs)} currency balances inserted")

            # 2c. All starting inventory items in one commit.
            inv_rows = [
                InventoryItem(
                    player_id = c["player_id"],
                    item_type = item,
                    quantity  = float(qty),
                )
                for c in fresh_cfgs
                for item, qty in c.get("seed", {}).get("starting_inventory", {}).items()
                if qty > 0
            ]
            if inv_rows:
                db.add_all(inv_rows)
                db.commit()
                print(f"[NPC]   {len(inv_rows)} inventory rows inserted")

            batch_ok = True

        except Exception as e:
            print(f"[NPC] Batch base-seed failed, falling back to individual seeding: {e}")
            traceback.print_exc()
            db.rollback()
            # Merge all fresh configs into the individual-seed path.
            existing_cfgs = list(all_cfgs)
            fresh_cfgs    = []
        finally:
            db.close()

        if batch_ok:
            # 2d. Per fresh NPC: land plots + businesses.
            for c in fresh_cfgs:
                try:
                    _seed_npc_assets(c)
                    _NPC_PLAYERS[c["player_id"]] = c
                    _maybe_ipo_npc(c["player_id"], c)
                except Exception as e:
                    print(f"[NPC] Asset seed error {c.get('business_name')}: {e}")
                _seeding_progress += 1

    # ── Step 3: update / rescue existing NPCs via normal path ─────────────────
    for c in existing_cfgs:
        try:
            _seed_npc(c)
        except Exception as e:
            print(f"[NPC] Update error {c.get('business_name')}: {e}")
        _seeding_progress += 1

    _seeding_done = True
    missing = _seeding_total - len(_NPC_PLAYERS)
    if missing > 0:
        print(f"[NPC] WARNING: {missing} NPC(s) failed seeding and will not participate in "
              "market cycles. They will be retried on next boot.")
    print(f"[NPC] Background seeding complete — {len(_NPC_PLAYERS)} NPC(s) active")


# ===========================
# MODULE LIFECYCLE
# ===========================

def initialize():
    """
    Fast init: DDL migrations + config loading only.
    NPC account seeding is deferred — call seed_npcs_background() in a
    background thread (see app.py lifespan) so the web server starts
    accepting requests immediately.
    """
    from database import run_ddl_migration

    run_ddl_migration(engine, [
        "ALTER TABLE players ADD COLUMN IF NOT EXISTS is_npc BOOLEAN DEFAULT FALSE",
        "ALTER TABLE players ADD COLUMN IF NOT EXISTS npc_config_key VARCHAR(128)",
    ])

    _load_configs()

    print(f"[NPC] Configs loaded: {len(_NPC_CONFIGS)} NPC(s). "
          "Background seeding will start shortly.")

    _cancel_runaway_npc_orders()


def _cancel_runaway_npc_orders():
    """Startup hygiene: cancel active NPC orders priced beyond 5× the
    human-anchored reference — leftovers from the NPC↔NPC wash-trade ratchet
    (jam asks at $110B etc.). Idempotent; only touches offending NPC orders.
    Human players' orders are never touched."""
    try:
        from market import MarketOrder, OrderStatus
        db = SessionLocal()
        try:
            rows = (
                db.query(MarketOrder)
                .filter(
                    MarketOrder.player_id < 0,
                    MarketOrder.status.in_([OrderStatus.ACTIVE,
                                            OrderStatus.PARTIALLY_FILLED]),
                )
                .all()
            )
            anchors: dict = {}
            cancelled = 0
            for o in rows:
                if o.item_type not in anchors:
                    anchors[o.item_type] = _human_anchor(o.item_type)
                anchor = anchors[o.item_type]
                if anchor and anchor > 0 and o.price and o.price > anchor * 5:
                    o.status = OrderStatus.CANCELLED
                    cancelled += 1
            db.commit()
            if cancelled:
                print(f"[NPC] Hygiene: cancelled {cancelled} runaway NPC order(s) "
                      f"priced beyond 5× the human-anchored reference.")
        finally:
            db.close()
    except Exception as e:
        print(f"[NPC] Runaway-order hygiene error: {e}")


def tick(current_tick: int, now: datetime):
    """Fire NPC decision cycles, spread evenly across NPC_TICK_INTERVAL ticks.

    Previously every NPC ran in the SAME tick (when current_tick % interval == 0).
    With ~100 NPCs each opening several DB sessions per buy/sell item, that produced
    a ~14s burst every interval that saturated the shared Postgres connection pool
    and timed out concurrent page loads (/land, /businesses, /districts).

    We now process a rotating slice of NPCs each tick: NPC at list-index ``idx`` runs
    when ``current_tick % interval == idx % interval``. Each NPC still acts about once
    per interval, but the DB load is spread across every tick (~n/interval NPCs per
    tick, ~1s instead of ~14s) so page requests never hit a multi-second contention
    window.
    """
    npc_ids = list(_NPC_PLAYERS.keys())
    n = len(npc_ids)
    if n == 0:
        return
    interval = max(1, NPC_TICK_INTERVAL)
    slot = current_tick % interval
    import time as _pt
    for k in _NPC_PHASE:
        _NPC_PHASE[k] = 0.0
    _t0 = _pt.monotonic()
    for idx in range(slot, n, interval):
        player_id = npc_ids[idx]
        _run_npc_cycle(player_id, _NPC_PLAYERS[player_id])
    _total = _pt.monotonic() - _t0
    if _total > 2.0:
        c = max(1, int(_NPC_PHASE["cycles"]))
        print(f"[NPC tick] {_total:.1f}s over {int(_NPC_PHASE['cycles'])} NPCs "
              f"({_total/c:.2f}s each) — spendable {_NPC_PHASE['spendable']:.2f}s · "
              f"sell {_NPC_PHASE['sell']:.2f}s · buy {_NPC_PHASE['buy']:.2f}s", flush=True)


__all__ = ["initialize", "seed_npcs_background", "is_ready", "seeding_status", "tick"]
