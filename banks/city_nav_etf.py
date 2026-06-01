"""
banks/city_nav_etf.py

City NAV ETF — an exchange-traded fund that traces worldwide City Net Asset Value.

Key characteristics:
  - 420 billion shares, no stock splits
  - $100,000 starting cash (seed capital)
  - NO dividends
  - Buys and sells land from the land market instead of commodities
  - Share price is pegged to ETF NAV / total shares
  - ETF NAV = cash reserves + market value of land holdings

Land valuation method: monthly_tax × 120 (10-year capitalisation) OR the
most recent sale price for that land plot, whichever is available and higher.

The ETF automatically:
  - Buys the cheapest available land listings when it has excess cash (>20% buffer)
  - Lists its own land for sale when its land portfolio is oversized vs. its cash
  - Updates its share price every PRICE_UPDATE_INTERVAL ticks
"""

from datetime import datetime
from typing import Optional, List

# ──────────────────────────────────────────────────────────────
# BANK IDENTITY
# ──────────────────────────────────────────────────────────────
BANK_ID          = "city_nav_etf"
BANK_NAME        = "City NAV ETF"
BANK_DESCRIPTION = ("Exchange-traded fund tracking worldwide City Net Asset Value. "
                    "Asset-backed by land holdings. No dividends.")
BANK_PLAYER_ID   = -6   # unique negative player ID for the ETF

# ──────────────────────────────────────────────────────────────
# CONSTANTS
# ──────────────────────────────────────────────────────────────
IPO_SHARES        = 420_000_000_000   # 420 billion shares
SEED_CAPITAL      = 100_000.0         # $100,000 starting cash
SHARE_ITEM_TYPE   = "city_nav_etf_shares"

# Land portfolio management
CASH_RESERVE_RATIO    = 0.20   # Always keep ≥20% of NAV as cash
BUY_MAX_LISTINGS      = 5      # Buy up to 5 land plots per tick cycle
SELL_MAX_LISTINGS     = 3      # Sell up to 3 land plots per tick cycle
LAND_SELL_MARKUP      = 1.10   # List land at 110% of estimated value

# Tick intervals
PRICE_UPDATE_INTERVAL  = 30    # Update share price every 30 ticks (2.5 min)
LAND_BUY_INTERVAL      = 60    # Check for land buys every 60 ticks (5 min)
LAND_SELL_INTERVAL     = 360   # Check for land sells every 360 ticks (30 min)
LAND_VALUE_CAP_MULT    = 120   # monthly_tax × 120 = land value estimate

# State
last_price_update_tick = 0
last_land_buy_tick     = 0
last_land_sell_tick    = 0
ipo_share_price        = None

# ──────────────────────────────────────────────────────────────
# DATABASE
# ──────────────────────────────────────────────────────────────
from sqlalchemy import Column, Integer, Float, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from database import engine, SessionLocal

Base = declarative_base()


def get_db():
    return SessionLocal()


# ──────────────────────────────────────────────────────────────
# LAND VALUATION
# ──────────────────────────────────────────────────────────────

def _estimate_land_value(plot_id: int, monthly_tax: float) -> float:
    """
    Estimate a land plot's market value.
    Uses the most recent sale price if available, otherwise monthly_tax × LAND_VALUE_CAP_MULT.
    """
    try:
        from land_market import LandSale, get_db as lm_get_db
        lm_db = lm_get_db()
        try:
            recent_sale = lm_db.query(LandSale).filter(
                LandSale.land_plot_id == plot_id
            ).order_by(LandSale.sold_at.desc()).first()
            if recent_sale and recent_sale.price > 0:
                return max(recent_sale.price, monthly_tax * LAND_VALUE_CAP_MULT)
        finally:
            lm_db.close()
    except Exception:
        pass
    return monthly_tax * LAND_VALUE_CAP_MULT


def calculate_land_portfolio_value() -> float:
    """Calculate the total market value of all land owned by the ETF."""
    try:
        from land import LandPlot, get_db as land_get_db
        land_db = land_get_db()
        try:
            plots = land_db.query(LandPlot).filter(
                LandPlot.owner_id == BANK_PLAYER_ID
            ).all()
            return sum(_estimate_land_value(p.id, p.monthly_tax) for p in plots)
        finally:
            land_db.close()
    except Exception as e:
        print(f"[{BANK_NAME}] Land portfolio valuation error: {e}")
        return 0.0


def get_etf_cash() -> float:
    """Return ETF cash reserves from the bank entity."""
    try:
        import banks
        entity = banks.get_bank_entity(BANK_ID)
        return entity.cash_reserves if entity else SEED_CAPITAL
    except Exception:
        return SEED_CAPITAL


def calculate_nav() -> float:
    """
    Calculate total ETF Net Asset Value.
    NAV = ETF cash balance + land portfolio value.
    """
    cash = get_etf_cash()
    land_value = calculate_land_portfolio_value()
    return cash + land_value


def calculate_share_price() -> float:
    """Return current ETF share price = NAV / total_shares_issued."""
    nav = calculate_nav()
    try:
        import banks as _banks
        entity = _banks.get_bank_entity(BANK_ID)
        denom = entity.total_shares_issued if entity and entity.total_shares_issued > 0 else IPO_SHARES
    except Exception:
        denom = IPO_SHARES
    return nav / denom if denom > 0 else 0.0


# ──────────────────────────────────────────────────────────────
# INITIALIZATION
# ──────────────────────────────────────────────────────────────

def execute_ipo():
    """
    Execute the IPO: create the share item, issue all shares to the ETF player,
    and list them on the market at the calculated IPO price.
    """
    global ipo_share_price
    import inventory
    import market
    import banks

    # Check if IPO was already done (check across ALL holders, not just the bank)
    inv_db = inventory.get_db()
    try:
        any_holder = inv_db.query(inventory.InventoryItem).filter(
            inventory.InventoryItem.item_type == SHARE_ITEM_TYPE,
            inventory.InventoryItem.quantity > 0
        ).first()
        if any_holder:
            print(f"[{BANK_NAME}] IPO already executed — shares in circulation. Skipping.")
            return
    finally:
        inv_db.close()

    nav = calculate_nav()
    ipo_share_price = nav / IPO_SHARES
    print(f"[{BANK_NAME}] NAV: ${nav:,.2f} | IPO price: ${ipo_share_price:.8f}/share")

    # Register item type in inventory system if needed
    if SHARE_ITEM_TYPE not in getattr(inventory, 'ITEM_RECIPES', {}):
        try:
            inventory.ITEM_RECIPES[SHARE_ITEM_TYPE] = {
                "name": "City NAV ETF Shares",
                "category": "financial"
            }
        except Exception:
            pass

    from market import create_order, OrderType, OrderMode

    # Mint shares into ETF's inventory
    inventory.add_item(BANK_PLAYER_ID, SHARE_ITEM_TYPE, IPO_SHARES)

    # List on market in batches (market may have order size limits)
    batch_size = 10_000_000_000   # 10B per batch = 42 batches
    batches = int(IPO_SHARES // batch_size)
    remainder = IPO_SHARES % batch_size

    for _ in range(batches):
        create_order(
            player_id=BANK_PLAYER_ID,
            order_type=OrderType.SELL,
            order_mode=OrderMode.LIMIT,
            item_type=SHARE_ITEM_TYPE,
            quantity=batch_size,
            price=ipo_share_price
        )
    if remainder > 0:
        create_order(
            player_id=BANK_PLAYER_ID,
            order_type=OrderType.SELL,
            order_mode=OrderMode.LIMIT,
            item_type=SHARE_ITEM_TYPE,
            quantity=remainder,
            price=ipo_share_price
        )

    print(f"[{BANK_NAME}] IPO complete: {IPO_SHARES:,} shares listed at ${ipo_share_price:.8f}")


def initialize():
    """Initialize the City NAV ETF."""
    global ipo_share_price
    import banks

    Base.metadata.create_all(bind=engine)

    # Get or create bank entity
    bank_entity = banks.get_bank_entity(BANK_ID)
    if not bank_entity:
        print(f"[{BANK_NAME}] Creating new bank entity...")
        bank_entity = banks.register_bank_entity(BANK_ID, BANK_NAME, BANK_DESCRIPTION)
        banks.add_bank_revenue(BANK_ID, SEED_CAPITAL, "Seed capital")

        bank_db = banks.get_db()
        try:
            entity = bank_db.query(banks.BankEntity).filter(
                banks.BankEntity.bank_id == BANK_ID
            ).first()
            if entity:
                entity.total_shares_issued = IPO_SHARES
                entity.share_price = SEED_CAPITAL / IPO_SHARES
                bank_db.commit()
        finally:
            bank_db.close()

        # Execute IPO (only on first creation)
        execute_ipo()

    ipo_share_price = calculate_share_price()
    print(f"[{BANK_NAME}] Initialized — {IPO_SHARES:,} shares, "
          f"seed capital ${SEED_CAPITAL:,.0f}, no dividends.")


# ──────────────────────────────────────────────────────────────
# LAND MARKET OPERATIONS
# ──────────────────────────────────────────────────────────────

def _buy_cheap_land(max_plots: int = BUY_MAX_LISTINGS):
    """
    Buy the cheapest available land listings using ETF cash reserves.
    Only buys if the ETF has cash above the CASH_RESERVE_RATIO threshold.
    """
    try:
        import banks
        from land_market import LandListing, buy_listed_land, get_db as lm_get_db
        from auth import Player, get_db as auth_get_db

        cash = get_etf_cash()
        nav = calculate_nav()
        max_spend = max(0.0, cash - nav * CASH_RESERVE_RATIO)
        if max_spend <= 0:
            return

        lm_db = lm_get_db()
        try:
            listings = lm_db.query(LandListing).filter(
                LandListing.is_active == True,
                LandListing.seller_id != BANK_PLAYER_ID
            ).order_by(LandListing.asking_price.asc()).limit(max_plots * 3).all()
            listing_data = [(l.id, l.asking_price, l.land_plot_id) for l in listings]
        finally:
            lm_db.close()

        # Sync ETF cash to auth Player so transfer_cash works
        auth_db = auth_get_db()
        try:
            etf_player = auth_db.query(Player).filter(Player.id == BANK_PLAYER_ID).first()
            if not etf_player:
                etf_player = Player(
                    id=BANK_PLAYER_ID,
                    business_name=BANK_NAME,
                    password_hash="SYSTEM_BANK",
                    cash_balance=cash,
                )
                auth_db.add(etf_player)
            else:
                etf_player.cash_balance = cash
            auth_db.commit()
        finally:
            auth_db.close()

        bought = 0
        spent = 0.0
        for listing_id, asking_price, plot_id in listing_data:
            if bought >= max_plots:
                break
            if asking_price > max_spend - spent:
                continue
            try:
                success = buy_listed_land(BANK_PLAYER_ID, listing_id)
                if success:
                    spent += asking_price
                    bought += 1
                    # Deduct from ETF bank balance
                    banks.add_bank_expense(BANK_ID, asking_price,
                                           f"Land purchase plot #{plot_id}")
            except Exception as e:
                print(f"[{BANK_NAME}] Land buy error: {e}")
                break

        if bought > 0:
            print(f"[{BANK_NAME}] Bought {bought} land plots for ${spent:,.2f}")

    except Exception as e:
        print(f"[{BANK_NAME}] _buy_cheap_land error: {e}")


def _sell_land_holdings(max_plots: int = SELL_MAX_LISTINGS):
    """
    List the ETF's land holdings for sale when the portfolio is oversized.
    Targets plots where the land market price has exceeded the ETF's purchase cost.
    """
    try:
        from land import LandPlot, get_db as land_get_db
        from land_market import LandListing, list_land_for_sale, get_db as lm_get_db

        nav = calculate_nav()
        land_value = calculate_land_portfolio_value()
        cash = get_etf_cash()

        # Sell land if land portfolio exceeds 90% of total NAV
        if land_value < nav * 0.90:
            return

        land_db = land_get_db()
        try:
            plots = land_db.query(LandPlot).filter(
                LandPlot.owner_id == BANK_PLAYER_ID
            ).order_by(LandPlot.monthly_tax.desc()).limit(max_plots * 2).all()
        finally:
            land_db.close()

        # Check which plots are already listed
        lm_db = lm_get_db()
        try:
            already_listed = {
                r.land_plot_id for r in lm_db.query(LandListing).filter(
                    LandListing.seller_id == BANK_PLAYER_ID,
                    LandListing.is_active == True
                ).all()
            }
        finally:
            lm_db.close()

        listed = 0
        for plot in plots:
            if listed >= max_plots:
                break
            if plot.id in already_listed:
                continue
            estimated_value = _estimate_land_value(plot.id, plot.monthly_tax)
            ask_price = estimated_value * LAND_SELL_MARKUP
            try:
                listing = list_land_for_sale(BANK_PLAYER_ID, plot.id, ask_price)
                if listing:
                    listed += 1
            except Exception as e:
                print(f"[{BANK_NAME}] Land list error: {e}")

        if listed > 0:
            print(f"[{BANK_NAME}] Listed {listed} land plots for sale")

    except Exception as e:
        print(f"[{BANK_NAME}] _sell_land_holdings error: {e}")


# ──────────────────────────────────────────────────────────────
# PRICE UPDATE
# ──────────────────────────────────────────────────────────────

def update_share_price():
    """Recalculate and publish the current share price based on NAV."""
    try:
        import banks

        price = calculate_share_price()
        if price <= 0:
            return

        # Update bank entity share price
        bank_db = banks.get_db()
        try:
            entity = bank_db.query(banks.BankEntity).filter(
                banks.BankEntity.bank_id == BANK_ID
            ).first()
            if entity:
                entity.share_price = price
                bank_db.commit()
        finally:
            bank_db.close()

        # Note: individual order prices aren't updated retroactively;
        # new orders placed by the ETF will use the current NAV price.

    except Exception as e:
        print(f"[{BANK_NAME}] Price update error: {e}")


# ──────────────────────────────────────────────────────────────
# TICK
# ──────────────────────────────────────────────────────────────

async def tick(current_tick: int, now: datetime, bank_entity=None):
    global last_price_update_tick, last_land_buy_tick, last_land_sell_tick

    try:
        # Update share price
        if current_tick - last_price_update_tick >= PRICE_UPDATE_INTERVAL:
            update_share_price()
            last_price_update_tick = current_tick

        # Buy land
        if current_tick - last_land_buy_tick >= LAND_BUY_INTERVAL:
            _buy_cheap_land()
            last_land_buy_tick = current_tick

        # Sell land
        if current_tick - last_land_sell_tick >= LAND_SELL_INTERVAL:
            _sell_land_holdings()
            last_land_sell_tick = current_tick

        # Maintain standing buy order so players can always sell shares
        if bank_entity:
            from banks import maintain_etf_share_bid
            maintain_etf_share_bid(BANK_ID, BANK_PLAYER_ID, SHARE_ITEM_TYPE, bank_entity, current_tick)

    except Exception as e:
        print(f"[{BANK_NAME}] Tick error: {e}")


# ──────────────────────────────────────────────────────────────
# PUBLIC QUERY API
# ──────────────────────────────────────────────────────────────

def get_etf_info() -> dict:
    """Return a summary of the ETF's current state."""
    cash = get_etf_cash()
    land_value = calculate_land_portfolio_value()
    nav = cash + land_value
    try:
        import banks as _banks
        _entity = _banks.get_bank_entity(BANK_ID)
        _denom = _entity.total_shares_issued if _entity and _entity.total_shares_issued > 0 else IPO_SHARES
    except Exception:
        _denom = IPO_SHARES
    share_price = nav / _denom if _denom > 0 else 0.0

    try:
        from land import LandPlot, get_db as land_get_db
        land_db = land_get_db()
        try:
            land_count = land_db.query(LandPlot).filter(
                LandPlot.owner_id == BANK_PLAYER_ID
            ).count()
        finally:
            land_db.close()
    except Exception:
        land_count = 0

    return {
        "bank_id": BANK_ID,
        "name": BANK_NAME,
        "total_shares": IPO_SHARES,
        "share_price": share_price,
        "nav": nav,
        "cash_reserves": cash,
        "land_portfolio_value": land_value,
        "land_plots_owned": land_count,
        "pays_dividends": False,
        "seed_capital": SEED_CAPITAL,
    }


def get_player_shareholding(player_id: int) -> dict:
    """Return shareholding info for a player."""
    try:
        import inventory
        import banks

        shares = inventory.get_item_quantity(player_id, SHARE_ITEM_TYPE)
        bank_entity = banks.get_bank_entity(BANK_ID)

        if not bank_entity:
            return {"shares_owned": 0, "current_value": 0.0, "ownership_percentage": 0.0}

        current_value = shares * bank_entity.share_price
        ownership_pct = (shares / bank_entity.total_shares_issued * 100) if bank_entity.total_shares_issued > 0 else 0.0

        return {
            "shares_owned": shares,
            "current_value": current_value,
            "ownership_percentage": ownership_pct,
            "share_price": bank_entity.share_price,
        }
    except Exception:
        return {"shares_owned": 0, "current_value": 0.0, "ownership_percentage": 0.0}
