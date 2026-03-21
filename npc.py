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

Pricing rule (normal):  sell_price = max(market_price * 1.02, unit_cost * 1.02)
Pricing rule (low):     sell_price = max(market_price * 1.01, unit_cost * 1.01)
Pricing rule (hard_low):sell_price = market_price  (cost floor bypassed entirely)

Order dedup: always check quantity already listed before placing a new order.
Order cancel: evaluate each open order individually — never bulk-nuke.
"""

import json
import os
from datetime import datetime
from typing import Optional, Tuple, Type

from database import engine, SessionLocal

# ===========================
# CONSTANTS
# ===========================

NPC_TICK_INTERVAL    = 12   # run NPC logic every N game ticks
PRICE_ROLLING_WINDOW = 20   # number of recent trades for the rolling average

# Sell markup rates by cash state
_MARKUP = {
    "hard_high":   0.02,
    "high":        0.02,
    "comfortable": 0.02,
    "low":         0.01,
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


# ===========================
# ROLLING AVERAGE PRICE
# ===========================

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

def _manage_sell_orders(player_id: int, cfg: dict, state: str):
    """
    For each item in sell_items:
    1. Evaluate each open order individually; cancel where warranted.
    2. Sum remaining listed quantity after cancellations.
    3. Place a new order only for the delta still needed.
    """
    import inventory as inv

    markup = _MARKUP[state]

    for item_type, sell_cfg in cfg.get("sell_items", {}).items():
        try:
            market_key = sell_cfg.get("market", "regular")
            min_keep   = sell_cfg.get("min_inventory_to_keep", 0)
            max_order  = sell_cfg.get("max_order_quantity", 10_000)

            current_inv  = inv.get_item_quantity(player_id, item_type)
            want_to_sell = current_inv - min_keep
            if want_to_sell <= 0:
                continue

            market_price = _get_market_price(item_type, market_key)
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
            finally:
                db.close()

            # --- Step 2: sum remaining listed quantity after cancellations ---
            db = SessionLocal()
            try:
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

def _manage_buy_orders(player_id: int, cfg: dict, state: str):
    """
    For each item in buy_items:
    1. Cancel open buy orders that are no longer needed or are stale/unaffordable.
    2. Place a new buy order for the delta needed to reach target_inventory.
    """
    import inventory as inv

    for item_type, buy_cfg in cfg.get("buy_items", {}).items():
        try:
            market_key = buy_cfg.get("market", "regular")
            reorder_at = buy_cfg.get("reorder_at", 0)
            target_inv = buy_cfg.get("target_inventory", 0)
            max_mult   = buy_cfg.get("max_price_multiplier", 1.10)

            current_inv  = inv.get_item_quantity(player_id, item_type)
            market_price = _get_market_price(item_type, market_key)
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


def _seed_businesses(player_id: int, cfg: dict, db, plot_ids: list):
    """
    Create Business rows for the NPC and mark land plots as occupied.
    Called both on first-time seed and on partial-seed recovery.
    """
    from business import Business, BUSINESS_TYPES, get_district_business_types
    from land import LandPlot

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

        paused_lines = _build_paused_lines(btype, biz_cfg.get("active_lines", []))

        biz = Business(
            owner_id     = player_id,
            land_plot_id = plot_id,
            district_id  = district_id,
            business_type= btype,
            is_active    = True,
            paused_lines = paused_lines,
        )
        db.add(biz)
        db.commit()
        db.refresh(biz)

        if plot_id:
            plot = db.query(LandPlot).filter(LandPlot.id == plot_id).first()
            if plot:
                plot.occupied_by_business_id = biz.id
                db.commit()

        print(f"[NPC]   Business {biz.id} ({btype}) — paused lines: {paused_lines} — on "
              f"{'district ' + str(district_id) if district_id else 'plot ' + str(plot_id)}")


# ===========================
# SEEDING
# ===========================

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
                if biz_cfg.get("district_id"):
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

            _seed_businesses(player_id, {**cfg, "businesses": missing_biz_cfgs},
                             db, plot_ids_for_missing)
            _NPC_PLAYERS[player_id] = cfg
            print(f"[NPC] Update complete: {cfg['business_name']}")
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

        # Businesses (with active_lines respected)
        _seed_businesses(player_id, cfg, db, plot_ids)

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

    # These columns are also added by auth.migrate_player_table(), but adding
    # them here makes npc.py independently safe even if initialised first.
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
