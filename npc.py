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
  hard_low   → cash below floor: emergency sell at market price

Pricing rule (normal):  sell_price = max(market_price * 1.02, unit_cost * 1.02)
Pricing rule (low):     sell_price = max(market_price * 1.01, unit_cost * 1.01)
Pricing rule (hard_low):sell_price = market_price  (no markup, move inventory)

Order dedup: always check quantity already listed before placing a new order.
Order cancel: evaluate each open order individually — never bulk-nuke.
"""

import json
import os
from datetime import datetime
from typing import Optional

from database import engine, SessionLocal

# ===========================
# CONSTANTS
# ===========================

NPC_TICK_INTERVAL   = 12    # run NPC logic every N game ticks
PRICE_ROLLING_WINDOW = 20   # number of recent trades for the rolling average

# Sell markup rates by cash state
_MARKUP = {
    "hard_high":   0.02,
    "high":        0.02,
    "comfortable": 0.02,
    "low":         0.01,
    "hard_low":    0.00,   # list at market price, no profit margin
}

# Cancel a sell order if market has risen this much above our listed price
# (means we're leaving money on the table — relist higher)
_SELL_CANCEL_ROSE_THRESHOLD  = 0.10   # market > listed * 1.10

# ===========================
# IN-MEMORY STATE
# ===========================

_NPC_CONFIGS: dict = {}   # config_key  -> config dict
_NPC_PLAYERS: dict = {}   # player_id   -> config dict  (populated after seeding)


# ===========================
# CONFIG LOADING
# ===========================

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
            _NPC_CONFIGS[key] = cfg
            print(f"[NPC] Loaded config: {key}")
        except Exception as e:
            print(f"[NPC] Failed to load {fname}: {e}")


# ===========================
# ROLLING AVERAGE PRICE
# ===========================

def _rolling_avg(item_type: str, market: str = "regular") -> Optional[float]:
    """
    Return the rolling average price of the last PRICE_ROLLING_WINDOW trades
    for item_type on either the regular or district market.
    Returns None if no trades exist yet.
    """
    try:
        if market == "district":
            from district_market import Trade
        else:
            from market import Trade
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


def _get_market_price(item_type: str, market: str = "regular") -> Optional[float]:
    """Get current last-trade/midpoint price from the appropriate market."""
    try:
        if market == "district":
            from district_market import get_market_price
        else:
            from market import get_market_price
        return get_market_price(item_type)
    except Exception:
        return None


# ===========================
# UNIT COST CALCULATION
# ===========================

def _calculate_unit_cost(business_type: str, output_item: str) -> Optional[float]:
    """
    Calculate production cost per unit of output_item for a given business type.

    Cost = (sum of each input's rolling_avg_price * input_qty  +  base_wage_cost)
           / output_quantity

    Returns None only if the config can't be found; uses 0.0 for missing prices
    so that the market-price floor still applies.
    """
    try:
        from business import BUSINESS_TYPES, get_district_business_types
        all_types = {**BUSINESS_TYPES, **get_district_business_types()}
        config = all_types.get(business_type)
        if not config:
            return None

        wage = config.get("base_wage_cost", 0.0)

        for line in config.get("production_lines", []):
            outputs = line.get("outputs", {})
            if output_item not in outputs:
                continue
            output_qty = outputs[output_item]
            if output_qty <= 0:
                continue

            input_cost = 0.0
            for input_item, input_qty in line.get("inputs", {}).items():
                # Try regular market first, then district
                avg = _rolling_avg(input_item, "regular")
                if avg is None:
                    avg = _rolling_avg(input_item, "district")
                if avg is None:
                    avg = 0.0   # no trades yet; cost floor still applies via market price
                input_cost += avg * input_qty

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

def _manage_sell_orders(player_id: int, cfg: dict, state: str):
    """
    For each item in sell_items:
    1. Evaluate and individually cancel stale orders where appropriate.
    2. Calculate the delta between what's already listed and what should be listed.
    3. Place a new order only for that delta.
    """
    import inventory as inv

    markup = _MARKUP[state]

    for item_type, sell_cfg in cfg.get("sell_items", {}).items():
        try:
            market_key  = sell_cfg.get("market", "regular")
            min_keep    = sell_cfg.get("min_inventory_to_keep", 0)
            max_order   = sell_cfg.get("max_order_quantity", 10_000)

            current_inv = inv.get_item_quantity(player_id, item_type)
            want_to_sell = current_inv - min_keep
            if want_to_sell <= 0:
                continue

            market_price = _get_market_price(item_type, market_key)

            # --- Step 1: evaluate existing orders, cancel where warranted ---
            db = SessionLocal()
            try:
                if market_key == "district":
                    from district_market import MarketOrder, OrderType, OrderStatus
                else:
                    from market import MarketOrder, OrderType, OrderStatus

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
                        # Market rose >10% above our listing → relist higher
                        if market_price > order.price * (1 + _SELL_CANCEL_ROSE_THRESHOLD):
                            cancel = True
                            print(f"[NPC] Cancel sell #{order.id} {item_type}: "
                                  f"market ${market_price:.4f} > listed ${order.price:.4f} +10%")
                        # Hard-low cash emergency: cancel and relist at no-markup market price
                        elif state == "hard_low" and order.price > market_price * 1.005:
                            cancel = True
                            print(f"[NPC] Cancel sell #{order.id} {item_type}: "
                                  f"hard_low cash emergency, relisting at market")
                    if cancel:
                        order.status = OrderStatus.CANCELLED

                db.commit()
            finally:
                db.close()

            # --- Step 2: compute how much is already listed after cancellations ---
            db = SessionLocal()
            try:
                if market_key == "district":
                    from district_market import MarketOrder, OrderType, OrderStatus
                else:
                    from market import MarketOrder, OrderType, OrderStatus

                still_active = (
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
                already_listed = sum(
                    o.quantity - o.quantity_filled for o in still_active
                )
            finally:
                db.close()

            need_to_list = want_to_sell - already_listed
            if need_to_list <= 0:
                continue   # already fully covered by open orders

            # --- Step 3: calculate target sell price ---
            unit_cost = None
            for biz_cfg in cfg.get("businesses", []):
                uc = _calculate_unit_cost(biz_cfg["business_type"], item_type)
                if uc is not None:
                    unit_cost = uc
                    break

            base = market_price if market_price else (unit_cost or 1.0)
            sell_price = base * (1 + markup)
            if unit_cost and unit_cost > 0:
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

def _manage_buy_orders(player_id: int, cfg: dict, state: str):
    """
    For each item in buy_items:
    1. Cancel open buy orders that are no longer needed or are stale/unaffordable.
    2. Place a new buy order for the delta needed to reach target_inventory.
    """
    import inventory as inv

    for item_type, buy_cfg in cfg.get("buy_items", {}).items():
        try:
            market_key   = buy_cfg.get("market", "regular")
            reorder_at   = buy_cfg.get("reorder_at", 0)
            target_inv   = buy_cfg.get("target_inventory", 0)
            max_mult     = buy_cfg.get("max_price_multiplier", 1.10)

            current_inv   = inv.get_item_quantity(player_id, item_type)
            market_price  = _get_market_price(item_type, market_key)

            # --- Step 1: evaluate and cancel stale buy orders ---
            db = SessionLocal()
            try:
                if market_key == "district":
                    from district_market import MarketOrder, OrderType, OrderStatus
                else:
                    from market import MarketOrder, OrderType, OrderStatus

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
                    # Inventory target already met — no longer need this
                    if current_inv >= target_inv:
                        cancel = True
                        print(f"[NPC] Cancel buy #{order.id} {item_type}: "
                              f"inventory target met ({current_inv:.0f}/{target_inv})")
                    # Cash emergency: stop spending
                    elif state == "hard_low":
                        cancel = True
                        print(f"[NPC] Cancel buy #{order.id} {item_type}: hard_low cash")
                    # Our bid is now too low to ever fill (market moved up >30%)
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

            # Buy if below reorder threshold OR cash is above soft_high (deploy excess cash)
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
                if market_key == "district":
                    from district_market import MarketOrder, OrderType, OrderStatus
                else:
                    from market import MarketOrder, OrderType, OrderStatus

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

def _run_npc_cycle(player_id: int, cfg: dict):
    """
    Run one full automated decision cycle for a single NPC.
    Called every NPC_TICK_INTERVAL ticks.
    """
    try:
        from reserve_banks import get_usd_balance
        cash  = get_usd_balance(player_id)
        state = _cash_state(cash, cfg["cash_caps"])
        _manage_sell_orders(player_id, cfg, state)
        _manage_buy_orders(player_id, cfg, state)
    except Exception as e:
        import traceback
        print(f"[NPC] Cycle error for {cfg.get('business_name', player_id)}: {e}")
        traceback.print_exc()


# ===========================
# SEEDING
# ===========================

def _seed_npc(cfg: dict):
    """
    Create the NPC Player row and all starting assets if they don't already exist.
    Idempotent: safe to call on every startup; exits immediately if the row exists.
    """
    from auth import Player
    from reserve_banks import credit_usd

    player_id = cfg["player_id"]
    db = SessionLocal()
    try:
        existing = db.query(Player).filter(Player.id == player_id).first()
        if existing:
            _NPC_PLAYERS[player_id] = cfg
            print(f"[NPC] {cfg['business_name']} already exists (id={player_id}), skipping seed")
            return

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

        # Land plots (created in config order; assigned to businesses in the same order)
        from land import LandPlot
        plot_ids = []
        for plot_cfg in seed.get("land_plots", []):
            plot = LandPlot(
                owner_id    = player_id,
                terrain_type= plot_cfg["terrain_type"],
                size        = plot_cfg.get("size", 1),
                efficiency  = plot_cfg.get("efficiency", 100),
            )
            db.add(plot)
            db.commit()
            db.refresh(plot)
            plot_ids.append(plot.id)
            print(f"[NPC]   Land plot {plot.id} ({plot_cfg['terrain_type']})")

        # Businesses
        from business import Business, BUSINESS_TYPES, get_district_business_types
        all_types = {**BUSINESS_TYPES, **get_district_business_types()}
        plot_iter = iter(plot_ids)

        for biz_cfg in cfg.get("businesses", []):
            btype = biz_cfg["business_type"]
            if btype not in all_types:
                print(f"[NPC]   WARNING: unknown business_type {btype!r} — skipping")
                continue

            district_id = biz_cfg.get("district_id")
            plot_id     = None

            if not district_id:
                plot_id = next(plot_iter, None)
                if plot_id is None:
                    print(f"[NPC]   WARNING: no land plot available for {btype} — skipping")
                    continue

            biz = Business(
                owner_id     = player_id,
                land_plot_id = plot_id,
                district_id  = district_id,
                business_type= btype,
                is_active    = True,
            )
            db.add(biz)
            db.commit()
            db.refresh(biz)

            if plot_id:
                plot = db.query(LandPlot).filter(LandPlot.id == plot_id).first()
                if plot:
                    plot.occupied_by_business_id = biz.id
                    db.commit()

            print(f"[NPC]   Business {biz.id} ({btype}) on "
                  f"{'district ' + str(district_id) if district_id else 'plot ' + str(plot_id)}")

        _NPC_PLAYERS[player_id] = cfg
        print(f"[NPC] Seeding complete: {cfg['business_name']}")

    except Exception as e:
        import traceback
        print(f"[NPC] Seeding failed for {cfg.get('business_name')}: {e}")
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


# ===========================
# MODULE LIFECYCLE
# ===========================

def initialize():
    """Load configs, run DB migrations, seed NPC accounts."""
    from database import run_ddl_migration

    # These columns are also added by auth.migrate_player_table(), but we add
    # them here as well so npc.py is independently safe to initialize first.
    run_ddl_migration(engine, [
        "ALTER TABLE players ADD COLUMN IF NOT EXISTS is_npc BOOLEAN DEFAULT FALSE",
        "ALTER TABLE players ADD COLUMN IF NOT EXISTS npc_config_key VARCHAR(128)",
    ])

    _load_configs()

    for key, cfg in _NPC_CONFIGS.items():
        cfg["config_key"] = key
        _seed_npc(cfg)

    print(f"[NPC] Initialized — {len(_NPC_CONFIGS)} NPC config(s) loaded, "
          f"{len(_NPC_PLAYERS)} NPC(s) active")


def tick(current_tick: int, now: datetime):
    """Fire NPC decision cycles every NPC_TICK_INTERVAL ticks."""
    if current_tick % NPC_TICK_INTERVAL != 0:
        return
    for player_id, cfg in _NPC_PLAYERS.items():
        _run_npc_cycle(player_id, cfg)


__all__ = ["initialize", "tick"]
