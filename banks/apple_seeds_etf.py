"""
banks/apple_seeds_etf.py

Apple Seeds ETF Bank - Commodity-backed investment fund

Features:
- Asset valuation based on total market value of apple_seeds divided by total money supply
- Automated market making: buys at low prices, sells at high inventory levels
- IPO: Limited shares representing fractional ownership of seed reserves
- Holder fees: Small per-tick fee to fund operations
- Stock splits and buybacks (similar to Land Bank)
- Prevents price crashes by hoarding during oversupply
"""

from datetime import datetime, timedelta
from typing import Optional, List
import random

# ==========================
# BANK IDENTITY
# ==========================
BANK_ID = "apple_seeds_etf"
BANK_NAME = "Apple Seeds ETF"
BANK_DESCRIPTION = "Exchange-traded fund backed by apple seed reserves - stabilizing agricultural commodity markets"

# Bank's player ID (used for inventory/market operations - NOT a real player)
BANK_PLAYER_ID = -3

# ==========================
# CONSTANTS
# ==========================

# IPO Settings
IPO_SHARES = 10_000_000       # 10M shares (realistic ETF scale)
IPO_PRICE = None               # Calculated from NAV at init
SEED_CAPITAL = 10_000_000      # $10M seed capital

# Target commodity
TARGET_COMMODITY = "apple_seeds"

# Market Making Parameters
BUY_PRICE_THRESHOLD = 0.98
BUY_PREMIUM = 1.02
BUY_PERCENTAGE = 0.05

SELL_INVENTORY_THRESHOLD = 0.85
SELL_DISCOUNT = 0.95
SELL_PERCENTAGE = 1.0

# Fee System
HOLDER_FEE_PER_TICK = 0.00011918  

# Dividend system
DIVIDEND_INTERVAL_TICKS = 60
DIVIDEND_PAYOUT_PERCENTAGE = 0.5
MIN_RESERVE_FOR_DIVIDENDS = 10000

# Stock split triggers
SPLIT_PRICE_THRESHOLD = 50.0   # Split at $50/share
SPLIT_RATIO = 5                # 5-for-1 split
SPLIT_CHECK_INTERVAL = 60
MAX_TOTAL_SHARES = 10_000_000_000  # 10B max after splits

# Buyback triggers
BUYBACK_PRICE_THRESHOLD = None
BUYBACK_PERCENTAGE = 0.80
BUYBACK_CHECK_INTERVAL = 120
MAX_BUYBACK_COST_RATIO = 0.90

# ==========================
# INSOLVENCY SYSTEM CONSTANTS
# ==========================

INSOLVENCY_THRESHOLD = 0.0
LEVY_FREQUENCY = 60

LIEN_INTEREST_RATE = 0.0001
LIEN_GARNISHMENT_PERCENTAGE = 0.5

QE_TRIGGER_SHARE_PRICE = None
QE_BUY_INTERVAL = 360
QE_BUY_PERCENTAGE = 0.15
QE_MAX_BUY_COST_RATIO = 0.05

# State tracking
last_dividend_tick = 0
last_split_check_tick = 0
last_buyback_check_tick = 0
last_fee_collection_tick = 0
last_market_making_tick = 0
last_levy_tick = 0
last_lien_processing_tick = 0
last_qe_buy_tick = 0
price_history = []
MAX_PRICE_HISTORY = 3600
ipo_share_price = None

# Share item type
SHARE_ITEM_TYPE = "apple_seeds_etf_shares"

# ==========================
# DATABASE SETUP
# ==========================

from sqlalchemy import create_engine, Column, String, Float, DateTime, Integer, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./symco.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class BankLien(Base):
    """Player debt to the ETF bank from unpaid solvency levies."""
    __tablename__ = "etf_bank_liens"
    
    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, index=True, nullable=False)
    bank_id = Column(String, index=True, nullable=False)
    
    principal = Column(Float, default=0.0)
    interest_accrued = Column(Float, default=0.0)
    total_paid = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    last_interest_accrual = Column(DateTime, default=datetime.utcnow)
    last_payment = Column(DateTime, nullable=True)
    
    @property
    def total_owed(self):
        return self.principal + self.interest_accrued - self.total_paid


# ==========================
# HELPER FUNCTIONS
# ==========================

def get_total_money_supply() -> float:
    """Calculate total money in the game economy (real players only)."""
    try:
        from auth import get_db as get_auth_db, Player
        
        auth_db = get_auth_db()
        try:
            # Only count REAL players (positive IDs)
            players = auth_db.query(Player).filter(Player.id > 0).all()
            total_cash = sum(p.cash_balance for p in players)
            return total_cash if total_cash > 0 else 1.0
        finally:
            auth_db.close()
    except:
        return 1.0


def get_total_commodity_supply() -> float:
    """Calculate total apple_seeds in the entire game."""
    try:
        import inventory
        
        inv_db = inventory.get_db()
        try:
            holdings = inv_db.query(inventory.InventoryItem).filter(
                inventory.InventoryItem.item_type == TARGET_COMMODITY
            ).all()
            
            total = sum(h.quantity for h in holdings)
            return total if total > 0 else 1.0
        finally:
            inv_db.close()
    except:
        return 1.0


def calculate_ipo_price() -> float:
    """
    Calculate IPO share price based on Net Asset Value (NAV).
    IPO Price = (Seed Capital + Commodity Holdings Value) / Total Shares

    At IPO the fund holds only seed capital (no commodities yet),
    so price = SEED_CAPITAL / IPO_SHARES.
    """
    try:
        import market

        # Calculate value of any pre-existing commodity holdings
        commodity_holdings = 0.0
        try:
            import inventory
            held = inventory.get_item_quantity(BANK_PLAYER_ID, TARGET_COMMODITY)
            if held > 0:
                market_price = market.get_market_price(TARGET_COMMODITY)
                if not market_price:
                    market_price = 0.15  # Apple seeds base cost fallback
                commodity_holdings = held * market_price
        except:
            pass

        nav = SEED_CAPITAL + commodity_holdings
        ipo_price = nav / IPO_SHARES

        # Sanity bounds
        if ipo_price < 0.01:
            print(f"[{BANK_NAME}] ⚠️ IPO price too low ({ipo_price:.8f}), using minimum $0.01")
            ipo_price = 0.01
        elif ipo_price > 1000.0:
            print(f"[{BANK_NAME}] ⚠️ IPO price too high ({ipo_price:.2f}), capping at $1000")
            ipo_price = 1000.0

        print(f"[{BANK_NAME}] IPO Price Calculation (NAV-based):")
        print(f"  → Seed Capital: ${SEED_CAPITAL:,.2f}")
        print(f"  → Commodity Holdings Value: ${commodity_holdings:,.2f}")
        print(f"  → NAV: ${nav:,.2f}")
        print(f"  → Shares: {IPO_SHARES:,}")
        print(f"  → IPO Price: ${ipo_price:.4f}")

        return ipo_price

    except Exception as e:
        print(f"[{BANK_NAME}] IPO price calculation error: {e}")
        import traceback
        traceback.print_exc()
        return SEED_CAPITAL / IPO_SHARES if IPO_SHARES > 0 else 1.0


# ==========================
# IPO EXECUTION
# ==========================

def execute_ipo():
    """Execute Initial Public Offering."""
    try:
        import market
        import inventory
        
        if not ipo_share_price:
            print(f"[{BANK_NAME}] ✗ IPO aborted - price not calculated")
            return
        
        db = market.get_db()
        try:
            existing = db.query(market.MarketOrder).filter(
                market.MarketOrder.player_id == BANK_PLAYER_ID,
                market.MarketOrder.item_type == SHARE_ITEM_TYPE,
                market.MarketOrder.status == market.OrderStatus.ACTIVE
            ).first()
            
            if existing:
                print(f"[{BANK_NAME}] IPO already exists (Order #{existing.id})")
                return
        finally:
            db.close()
        
        # Register share as tradeable item
        if SHARE_ITEM_TYPE not in inventory.ITEM_RECIPES:
            inventory.ITEM_RECIPES[SHARE_ITEM_TYPE] = {
                "name": "Apple Seeds ETF Shares",
                "description": "Tradeable ETF shares backed by apple seed reserves",
                "category": "financial"
            }
        
        # Give shares to bank's inventory
        inventory.add_item(BANK_PLAYER_ID, SHARE_ITEM_TYPE, IPO_SHARES)
        
        # List all shares on market at calculated IPO price
        order = market.create_order(
            player_id=BANK_PLAYER_ID,
            order_type=market.OrderType.SELL,
            order_mode=market.OrderMode.LIMIT,
            item_type=SHARE_ITEM_TYPE,
            quantity=IPO_SHARES,
            price=ipo_share_price
        )
        
        if order:
            print(f"[{BANK_NAME}] 🎉 IPO EXECUTED: {IPO_SHARES:,} shares listed at ${ipo_share_price:.4f} (Order #{order.id})")
    
    except Exception as e:
        print(f"[{BANK_NAME}] ✗ IPO error: {e}")


# ==========================
# INITIALIZATION
# ==========================

def initialize():
    """Initialize the Apple Seeds ETF Bank."""
    import banks
    
    global ipo_share_price, QE_TRIGGER_SHARE_PRICE
    
    # Create lien table
    Base.metadata.create_all(bind=engine)
    
    # Calculate IPO price based on market fundamentals
    ipo_share_price = calculate_ipo_price()
    
    if not ipo_share_price or ipo_share_price <= 0:
        print(f"[{BANK_NAME}] ✗ CRITICAL: Invalid IPO price calculated: {ipo_share_price}")
        ipo_share_price = SEED_CAPITAL / IPO_SHARES
    
    # Set QE trigger
    QE_TRIGGER_SHARE_PRICE = -ipo_share_price * 0.5
    
    # Get or create bank entity
    bank_entity = banks.get_bank_entity(BANK_ID)
    
    if not bank_entity:
        print(f"[{BANK_NAME}] Creating new bank entity...")
        bank_entity = banks.register_bank_entity(BANK_ID, BANK_NAME, BANK_DESCRIPTION)
        
        # Seed initial capital
        banks.add_bank_revenue(BANK_ID, SEED_CAPITAL, "Initial seed funding")
        
        # Set initial share structure
        bank_db = banks.get_db()
        try:
            entity = bank_db.query(banks.BankEntity).filter(banks.BankEntity.bank_id == BANK_ID).first()
            if entity:
                entity.total_shares_issued = IPO_SHARES
                entity.share_price = ipo_share_price
                bank_db.commit()
                print(f"[{BANK_NAME}] Initial share structure set: {IPO_SHARES:,} shares at ${ipo_share_price:.4f}")
        finally:
            bank_db.close()
    
    # Execute IPO
    execute_ipo()
    
    print(f"[{BANK_NAME}] Module initialized")
    print(f"  → Target Commodity: {TARGET_COMMODITY}")
    print(f"  → IPO: {IPO_SHARES:,} shares at ${ipo_share_price:.6f}")
    print(f"  → Buy Threshold: {BUY_PRICE_THRESHOLD*100:.0f}% of moving average")
    print(f"  → Sell Threshold: {SELL_INVENTORY_THRESHOLD*100:.0f}% of total supply")
    print(f"  → Holder Fee: {HOLDER_FEE_PER_TICK*31536000:.2f}% per year")
    print(f"  → Split Trigger: ${SPLIT_PRICE_THRESHOLD:.2f}")
    print(f"  → Buyback Trigger: ${ipo_share_price * 0.5:.4f} (50% of IPO)")
    print(f"  → Insolvency System: Active (QE at ${QE_TRIGGER_SHARE_PRICE:.4f})")


# ==========================
# ASSET VALUATION
# ==========================

def calculate_commodity_value() -> float:
    """Calculate asset value based on commodity holdings."""
    try:
        import inventory
        import market
        
        seeds_held = inventory.get_item_quantity(BANK_PLAYER_ID, TARGET_COMMODITY)
        market_price = market.get_market_price(TARGET_COMMODITY)
        if not market_price:
            market_price = 10.0
        
        return seeds_held * market_price
    except:
        return 0.0


def update_asset_valuation():
    """Update the bank's asset value."""
    import banks
    
    commodity_value = calculate_commodity_value()
    banks.update_bank_assets(BANK_ID, commodity_value)


def update_price_history():
    """Track price history for moving average calculations."""
    global price_history
    
    try:
        import market
        
        current_price = market.get_market_price(TARGET_COMMODITY)
        if current_price:
            price_history.append(current_price)
            
            if len(price_history) > MAX_PRICE_HISTORY:
                price_history = price_history[-MAX_PRICE_HISTORY:]
    except:
        pass


def get_moving_average_price() -> Optional[float]:
    """Get moving average price from history."""
    if not price_history:
        return None
    
    return sum(price_history) / len(price_history)


# ==========================
# SHARE OWNERSHIP TRACKING
# ==========================

def get_all_shareholders() -> dict:
    """Get all current shareholders (excluding the bank itself)."""
    try:
        import inventory
        
        shareholders = {}
        inv_db = inventory.get_db()
        try:
            holdings = inv_db.query(inventory.InventoryItem).filter(
                inventory.InventoryItem.item_type == SHARE_ITEM_TYPE,
                inventory.InventoryItem.quantity > 0
            ).all()
            
            for holding in holdings:
                # Exclude bank's own inventory
                if holding.player_id != BANK_PLAYER_ID:
                    shareholders[holding.player_id] = int(holding.quantity)
        finally:
            inv_db.close()
        
        return shareholders
    except:
        return {}


def get_player_shareholding(player_id: int) -> dict:
    """Get detailed shareholding info for a player."""
    try:
        import inventory
        import banks
        
        shares = inventory.get_item_quantity(player_id, SHARE_ITEM_TYPE)
        bank_entity = banks.get_bank_entity(BANK_ID)
        
        if not bank_entity:
            return {
                "shares_owned": 0,
                "current_value": 0.0,
                "ownership_percentage": 0.0
            }
        
        current_value = shares * bank_entity.share_price
        ownership_pct = (shares / bank_entity.total_shares_issued * 100) if bank_entity.total_shares_issued > 0 else 0
        
        return {
            "shares_owned": shares,
            "current_value": current_value,
            "ownership_percentage": ownership_pct,
            "share_price": bank_entity.share_price
        }
    except:
        return {
            "shares_owned": 0,
            "current_value": 0.0,
            "ownership_percentage": 0.0
        }


# ==========================
# MARKET MAKING SYSTEM
# ==========================

def execute_market_making():
    """Execute automated market making strategy."""
    try:
        import market
        import inventory
        import banks
        
        current_price = market.get_market_price(TARGET_COMMODITY)
        if not current_price:
            return
        
        moving_avg = get_moving_average_price()
        if not moving_avg:
            return
        
        total_supply = get_total_commodity_supply()
        bank_inventory = inventory.get_item_quantity(BANK_PLAYER_ID, TARGET_COMMODITY)
        bank_entity = banks.get_bank_entity(BANK_ID)
        
        if not bank_entity:
            return
        
        # BUYING LOGIC: Price dropped below threshold
        if current_price < (moving_avg * BUY_PRICE_THRESHOLD):
            buy_quantity = total_supply * BUY_PERCENTAGE
            buy_price = current_price * BUY_PREMIUM
            buy_cost = buy_quantity * buy_price
            
            if bank_entity.cash_reserves >= buy_cost and buy_quantity >= 1:
                order = market.create_order(
                    player_id=BANK_PLAYER_ID,
                    order_type=market.OrderType.BUY,
                    order_mode=market.OrderMode.LIMIT,
                    item_type=TARGET_COMMODITY,
                    quantity=int(buy_quantity),
                    price=buy_price
                )
                
                if order:
                    banks.add_bank_expense(BANK_ID, buy_cost, f"Market making: buying {int(buy_quantity)} {TARGET_COMMODITY}")
                    print(f"[{BANK_NAME}] 📉 BUY ORDER: {int(buy_quantity)} {TARGET_COMMODITY} @ ${buy_price:.2f}")
        
        # SELLING LOGIC: Inventory too high
        inventory_percentage = bank_inventory / total_supply if total_supply > 0 else 0
        if inventory_percentage >= SELL_INVENTORY_THRESHOLD and bank_inventory >= 1:
            sell_quantity = bank_inventory * SELL_PERCENTAGE
            sell_price = current_price * SELL_DISCOUNT
            
            if sell_quantity >= 1:
                order = market.create_order(
                    player_id=BANK_PLAYER_ID,
                    order_type=market.OrderType.SELL,
                    order_mode=market.OrderMode.LIMIT,
                    item_type=TARGET_COMMODITY,
                    quantity=int(sell_quantity),
                    price=sell_price
                )
                
                if order:
                    print(f"[{BANK_NAME}] 📈 SELL ORDER: {int(sell_quantity)} {TARGET_COMMODITY} @ ${sell_price:.2f}")
    
    except Exception as e:
        print(f"[{BANK_NAME}] Market making error: {e}")


# ==========================
# HOLDER FEE SYSTEM
# ==========================

def collect_holder_fees():
    """Collect per-tick fees from all ETF shareholders."""
    try:
        import banks
        import inventory
        from auth import get_db as get_auth_db, Player
        
        bank_entity = banks.get_bank_entity(BANK_ID)
        if not bank_entity:
            return
        
        shareholders = get_all_shareholders()
        
        if not shareholders:
            return
        
        nav = bank_entity.cash_reserves + bank_entity.asset_value
        total_fees_collected = 0.0
        
        for player_id, shares_owned in shareholders.items():
            ownership_fraction = shares_owned / bank_entity.total_shares_issued
            fee_amount = nav * ownership_fraction * HOLDER_FEE_PER_TICK
            
            if fee_amount < 0.01:
                continue
            
            auth_db = get_auth_db()
            try:
                player = auth_db.query(Player).filter(Player.id == player_id).first()
                if player and player.cash_balance >= fee_amount:
                    player.cash_balance -= fee_amount
                    total_fees_collected += fee_amount
                    auth_db.commit()
            finally:
                auth_db.close()
        
        if total_fees_collected > 0:
            banks.add_bank_revenue(BANK_ID, total_fees_collected, "Holder fees")
    
    except Exception as e:
        print(f"[{BANK_NAME}] Fee collection error: {e}")


# ==========================
# DIVIDEND SYSTEM
# ==========================

def pay_dividends():
    """Distribute weekly dividends to shareholders."""
    import banks
    from auth import get_db as get_auth_db, Player
    
    bank_db = banks.get_db()
    try:
        bank_entity = bank_db.query(banks.BankEntity).filter(
            banks.BankEntity.bank_id == BANK_ID
        ).first()
        
        if not bank_entity:
            return
        
        if bank_entity.cash_reserves < MIN_RESERVE_FOR_DIVIDENDS:
            return
        
        dividend_pool = bank_entity.cash_reserves * DIVIDEND_PAYOUT_PERCENTAGE
        dividend_pool = min(dividend_pool, bank_entity.cash_reserves * 0.75)
        
        shareholders = get_all_shareholders()
        
        if not shareholders:
            return
        
        total_paid = 0.0
        
        for player_id, shares_owned in shareholders.items():
            ownership_fraction = shares_owned / bank_entity.total_shares_issued
            dividend_amount = dividend_pool * ownership_fraction
            
            if dividend_amount < 0.01:
                continue
            
            auth_db = get_auth_db()
            try:
                player = auth_db.query(Player).filter(Player.id == player_id).first()
                if player:
                    player.cash_balance += dividend_amount
                    auth_db.commit()
            finally:
                auth_db.close()
            
            transaction = banks.BankTransaction(
                bank_id=BANK_ID,
                transaction_type="dividend",
                amount=dividend_amount,
                shares_affected=shares_owned,
                player_id=player_id,
                description=f"Weekly dividend - {shares_owned} ETF shares"
            )
            bank_db.add(transaction)
            
            total_paid += dividend_amount
        
        bank_entity.cash_reserves -= total_paid
        bank_entity.total_dividends_paid += total_paid
        bank_entity.last_dividend_date = datetime.utcnow()
        
        bank_db.commit()
        
        print(f"[{BANK_NAME}] 📊 WEEKLY DIVIDEND: ${total_paid:,.2f} to {len(shareholders)} shareholders")
    
    finally:
        bank_db.close()


# ==========================
# STOCK SPLIT
# ==========================

def check_and_execute_split(current_tick: int):
    """Check if stock split should occur."""
    import banks
    
    global last_split_check_tick
    
    if current_tick - last_split_check_tick < SPLIT_CHECK_INTERVAL:
        return
    
    last_split_check_tick = current_tick
    
    bank_db = banks.get_db()
    try:
        bank_entity = bank_db.query(banks.BankEntity).filter(
            banks.BankEntity.bank_id == BANK_ID
        ).first()
        
        if not bank_entity:
            return
        
        if bank_entity.share_price <= SPLIT_PRICE_THRESHOLD:
            return
        
        if bank_entity.total_shares_issued * SPLIT_RATIO > MAX_TOTAL_SHARES:
            return
        
        print(f"[{BANK_NAME}] 🚀 STOCK SPLIT EVENT!")
        
        try:
            import inventory
            
            inv_db = inventory.get_db()
            try:
                holdings = inv_db.query(inventory.InventoryItem).filter(
                    inventory.InventoryItem.item_type == SHARE_ITEM_TYPE,
                    inventory.InventoryItem.quantity > 0
                ).all()
                
                for holding in holdings:
                    old_shares = holding.quantity
                    holding.quantity *= SPLIT_RATIO
                    print(f"[{BANK_NAME}] Split: Player {holding.player_id}: {old_shares:.0f} → {holding.quantity:.0f} shares")
                
                inv_db.commit()
            finally:
                inv_db.close()
        except Exception as e:
            print(f"[{BANK_NAME}] Split error: {e}")
        
        bank_entity.total_shares_issued *= SPLIT_RATIO
        bank_entity.share_price /= SPLIT_RATIO
        
        bank_db.commit()
        print(f"[{BANK_NAME}] Split completed")
    
    finally:
        bank_db.close()


# ==========================
# BUYBACK (FIXED - No Player table creation)
# ==========================

def check_and_execute_buyback(current_tick: int):
    """Check if buyback should occur."""
    import banks
    
    global last_buyback_check_tick
    
    if current_tick - last_buyback_check_tick < BUYBACK_CHECK_INTERVAL:
        return
    
    last_buyback_check_tick = current_tick
    
    bank_entity = banks.get_bank_entity(BANK_ID)
    
    if not bank_entity or not ipo_share_price:
        return
    
    buyback_trigger_price = ipo_share_price * 0.5
    
    if bank_entity.share_price > buyback_trigger_price:
        return
    
    shares_to_buyback = int(bank_entity.total_shares_issued * BUYBACK_PERCENTAGE)
    buyback_price = bank_entity.share_price * 1.20
    total_cost = shares_to_buyback * buyback_price
    
    max_cost = bank_entity.cash_reserves * MAX_BUYBACK_COST_RATIO
    if total_cost > max_cost:
        shares_to_buyback = int(max_cost / buyback_price)
        total_cost = shares_to_buyback * buyback_price
    
    if shares_to_buyback == 0 or bank_entity.cash_reserves < total_cost:
        return
    
    print(f"[{BANK_NAME}] 💰 EMERGENCY BUYBACK TRIGGERED!")
    print(f"  → Share Price: ${bank_entity.share_price:.4f} (Trigger: ${buyback_trigger_price:.4f})")
    print(f"  → Buying: {shares_to_buyback:,} shares ({BUYBACK_PERCENTAGE*100:.0f}% of outstanding)")
    print(f"  → Buyback Price: ${buyback_price:.4f} (+20% premium to push price up)")
    
    try:
        import market
        
        # Place buy order - NO Player table entry needed
        order = market.create_order(
            player_id=BANK_PLAYER_ID,
            order_type=market.OrderType.BUY,
            order_mode=market.OrderMode.LIMIT,
            item_type=SHARE_ITEM_TYPE,
            quantity=shares_to_buyback,
            price=buyback_price
        )
        
        if order:
            bank_db = banks.get_db()
            try:
                entity = bank_db.query(banks.BankEntity).filter(
                    banks.BankEntity.bank_id == BANK_ID
                ).first()
                if entity:
                    entity.cash_reserves -= total_cost
                    bank_db.commit()
                    print(f"[{BANK_NAME}] Buyback order placed (Order #{order.id})")
            finally:
                bank_db.close()
    
    except Exception as e:
        print(f"[{BANK_NAME}] Buyback error: {e}")


def retire_bought_shares():
    """Retire shares bought back by the ETF bank."""
    try:
        import inventory
        import banks
        import market
        
        bank_shares = inventory.get_item_quantity(BANK_PLAYER_ID, SHARE_ITEM_TYPE)
        
        if bank_shares <= 0:
            return
        
        market_db = market.get_db()
        try:
            sell_orders = market_db.query(market.MarketOrder).filter(
                market.MarketOrder.player_id == BANK_PLAYER_ID,
                market.MarketOrder.item_type == SHARE_ITEM_TYPE,
                market.MarketOrder.order_type == market.OrderType.SELL,
                market.MarketOrder.status.in_([market.OrderStatus.ACTIVE, market.OrderStatus.PARTIALLY_FILLED])
            ).all()
            
            locked_shares = sum(order.quantity - order.quantity_filled for order in sell_orders)
        finally:
            market_db.close()
        
        shares_to_retire = bank_shares - locked_shares
        
        if shares_to_retire <= 0:
            return
        
        print(f"[{BANK_NAME}] Share retirement analysis:")
        print(f"  → Total in inventory: {bank_shares:.0f}")
        print(f"  → Locked in IPO: {locked_shares:.0f}")
        print(f"  → Available to retire: {shares_to_retire:.0f}")
        
        success = inventory.remove_item(BANK_PLAYER_ID, SHARE_ITEM_TYPE, shares_to_retire)
        
        if not success:
            print(f"[{BANK_NAME}] ✗ Failed to remove shares from inventory")
            return
        
        bank_db = banks.get_db()
        try:
            bank_entity = bank_db.query(banks.BankEntity).filter(
                banks.BankEntity.bank_id == BANK_ID
            ).first()
            
            if bank_entity:
                old_total = bank_entity.total_shares_issued
                bank_entity.total_shares_issued -= shares_to_retire
                
                if bank_entity.total_shares_issued < 0:
                    bank_entity.total_shares_issued = 0
                
                bank_db.commit()
                
                print(f"[{BANK_NAME}] 🔥 RETIRED {shares_to_retire:.0f} shares")
                print(f"[{BANK_NAME}]   Total shares: {old_total:,} → {bank_entity.total_shares_issued:,}")
                print(f"[{BANK_NAME}]   New share price: ${bank_entity.share_price:.4f}")
        finally:
            bank_db.close()
    
    except Exception as e:
        print(f"[{BANK_NAME}] Retire error: {e}")
        import traceback
        traceback.print_exc()


# ==========================
# INSOLVENCY SYSTEM
# ==========================

def check_and_levy_shareholders(current_tick: int):
    """Levy shareholders when bank reserves are negative."""
    global last_levy_tick
    
    if current_tick - last_levy_tick < LEVY_FREQUENCY:
        return
    
    last_levy_tick = current_tick
    
    import banks
    from auth import get_db as get_auth_db, Player
    
    bank_entity = banks.get_bank_entity(BANK_ID)
    
    if not bank_entity or bank_entity.cash_reserves >= INSOLVENCY_THRESHOLD:
        return
    
    deficit = abs(bank_entity.cash_reserves)
    
    print(f"[{BANK_NAME}] 🚨 INSOLVENCY: ${deficit:,.2f} deficit")
    
    shareholders = get_all_shareholders()
    
    if not shareholders:
        return
    
    total_levied = 0.0
    total_unpaid = 0.0
    
    for player_id, shares_owned in shareholders.items():
        ownership_fraction = shares_owned / bank_entity.total_shares_issued
        levy_amount = deficit * ownership_fraction
        
        if levy_amount < 0.01:
            continue
        
        auth_db = get_auth_db()
        try:
            player = auth_db.query(Player).filter(Player.id == player_id).first()
            if not player:
                continue
            
            if player.cash_balance >= levy_amount:
                player.cash_balance -= levy_amount
                total_levied += levy_amount
                print(f"[{BANK_NAME}] Levy ${levy_amount:,.2f} from Player {player_id}")
            else:
                paid_amount = player.cash_balance
                unpaid_amount = levy_amount - paid_amount
                player.cash_balance = 0.0
                total_levied += paid_amount
                total_unpaid += unpaid_amount
                create_or_update_lien(player_id, unpaid_amount)
                print(f"[{BANK_NAME}] Player {player_id}: Paid ${paid_amount:.2f}, Lien ${unpaid_amount:.2f}")
            
            auth_db.commit()
        finally:
            auth_db.close()
    
    if total_levied > 0:
        banks.add_bank_revenue(BANK_ID, total_levied, "Solvency levy")
    
    print(f"[{BANK_NAME}] LEVY: ${total_levied:,.2f} collected, ${total_unpaid:,.2f} in liens")


def create_or_update_lien(player_id: int, amount: float):
    """Create or update a bank lien."""
    db = SessionLocal()
    try:
        lien = db.query(BankLien).filter(
            BankLien.player_id == player_id,
            BankLien.bank_id == BANK_ID
        ).first()
        
        if lien:
            lien.principal += amount
        else:
            lien = BankLien(
                player_id=player_id,
                bank_id=BANK_ID,
                principal=amount
            )
            db.add(lien)
        
        db.commit()
    finally:
        db.close()


def process_lien_system(current_tick: int):
    """Process all active liens."""
    global last_lien_processing_tick
    
    if current_tick - last_lien_processing_tick < LEVY_FREQUENCY:
        return
    
    last_lien_processing_tick = current_tick
    
    db = SessionLocal()
    try:
        liens = db.query(BankLien).all()
        
        if not liens:
            return
        
        from auth import get_db as get_auth_db, Player
        import banks
        
        total_garnished = 0.0
        
        for lien in liens:
            if lien.total_owed <= 0:
                continue
            
            lien.interest_accrued += lien.total_owed * LIEN_INTEREST_RATE
            lien.last_interest_accrual = datetime.utcnow()
            
            auth_db = get_auth_db()
            try:
                player = auth_db.query(Player).filter(Player.id == lien.player_id).first()
                if not player or player.cash_balance <= 0:
                    continue
                
                garnish_amount = min(
                    player.cash_balance * LIEN_GARNISHMENT_PERCENTAGE,
                    lien.total_owed
                )
                
                if garnish_amount >= 0.01:
                    player.cash_balance -= garnish_amount
                    lien.total_paid += garnish_amount
                    lien.last_payment = datetime.utcnow()
                    total_garnished += garnish_amount
                    auth_db.commit()
                    
                    if lien.total_owed <= 0:
                        print(f"[{BANK_NAME}] ✅ Lien CLEARED for Player {lien.player_id}")
            finally:
                auth_db.close()
        
        db.commit()
        
        if total_garnished > 0:
            banks.add_bank_revenue(BANK_ID, total_garnished, "Lien garnishment")
            print(f"[{BANK_NAME}] 💰 Garnished: ${total_garnished:,.2f}")
    
    finally:
        db.close()


def check_and_trigger_qe(current_tick: int):
    """QE: Buy commodities when share price is deeply negative."""
    global last_qe_buy_tick
    
    if current_tick - last_qe_buy_tick < QE_BUY_INTERVAL:
        return
    
    import banks
    
    bank_entity = banks.get_bank_entity(BANK_ID)
    
    if not bank_entity or not QE_TRIGGER_SHARE_PRICE:
        return
    
    if bank_entity.share_price >= QE_TRIGGER_SHARE_PRICE:
        return
    
    last_qe_buy_tick = current_tick
    
    print(f"[{BANK_NAME}] 🏦 QE ACTIVATED")
    print(f"[{BANK_NAME}] Share: ${bank_entity.share_price:.4f} (Trigger: ${QE_TRIGGER_SHARE_PRICE:.4f})")
    
    try:
        import market
        
        total_supply = get_total_commodity_supply()
        buy_quantity = total_supply * QE_BUY_PERCENTAGE
        
        current_price = market.get_market_price(TARGET_COMMODITY)
        if not current_price:
            return
        
        buy_price = current_price * 1.05
        total_cost = buy_quantity * buy_price
        
        max_cost = abs(bank_entity.cash_reserves) * QE_MAX_BUY_COST_RATIO
        if total_cost > max_cost:
            buy_quantity = int(max_cost / buy_price)
            total_cost = buy_quantity * buy_price
        
        if buy_quantity < 1:
            return
        
        order = market.create_order(
            player_id=BANK_PLAYER_ID,
            order_type=market.OrderType.BUY,
            order_mode=market.OrderMode.LIMIT,
            item_type=TARGET_COMMODITY,
            quantity=int(buy_quantity),
            price=buy_price
        )
        
        if order:
            banks.add_bank_expense(BANK_ID, total_cost, f"QE: buying {int(buy_quantity)} {TARGET_COMMODITY}")
            print(f"[{BANK_NAME}] 🚨 QE BUY: {int(buy_quantity)} seeds @ ${buy_price:.2f}")
    
    except Exception as e:
        print(f"[{BANK_NAME}] QE error: {e}")


# ==========================
# TICK HANDLER
# ==========================

async def tick(current_tick: int, now: datetime, bank_entity):
    """ETF Bank tick handler with insolvency protection."""
    global last_dividend_tick, last_fee_collection_tick, last_market_making_tick
    
    update_price_history()
    
    if current_tick % 60 == 0:
        update_asset_valuation()
    
    # INSOLVENCY SYSTEM
    check_and_levy_shareholders(current_tick)
    process_lien_system(current_tick)
    check_and_trigger_qe(current_tick)
    
    # Normal operations (only if solvent)
    if bank_entity.cash_reserves >= INSOLVENCY_THRESHOLD:
        if current_tick % 60 == 0:
            collect_holder_fees()
        
        if current_tick % 300 == 0:
            execute_market_making()
        
        if current_tick - last_dividend_tick >= DIVIDEND_INTERVAL_TICKS:
            pay_dividends()
            last_dividend_tick = current_tick
        
        check_and_execute_split(current_tick)
        check_and_execute_buyback(current_tick)
    
    if current_tick % 3600 == 0:
        retire_bought_shares()
    
    # Log stats every hour
    if current_tick % 3600 == 0:
        try:
            import inventory
            
            nav = bank_entity.cash_reserves + bank_entity.asset_value
            seeds_held = inventory.get_item_quantity(BANK_PLAYER_ID, TARGET_COMMODITY)
            total_supply = get_total_commodity_supply()
            inventory_pct = (seeds_held / total_supply * 100) if total_supply > 0 else 0
            
            db = SessionLocal()
            active_liens = db.query(BankLien).filter(
                BankLien.principal + BankLien.interest_accrued - BankLien.total_paid > 0
            ).count()
            total_lien_debt = sum(l.total_owed for l in db.query(BankLien).all())
            db.close()
            
            status = "INSOLVENT" if bank_entity.cash_reserves < 0 else "SOLVENT"
            qe_status = " [QE ACTIVE]" if bank_entity.share_price < QE_TRIGGER_SHARE_PRICE else ""
            
            print(f"[{BANK_NAME}] {status}{qe_status} | NAV: ${nav:,.2f} | " +
                  f"Share: ${bank_entity.share_price:.4f} | " +
                  f"Seeds: {seeds_held:,.0f} ({inventory_pct:.1f}%) | " +
                  f"Liens: {active_liens} (${total_lien_debt:,.2f})")
        except:
            pass


# ==========================
# PUBLIC API
# ==========================

__all__ = [
    'BANK_ID',
    'BANK_NAME',
    'BANK_DESCRIPTION',
    'SHARE_ITEM_TYPE',
    'initialize',
    'tick',
    'get_player_shareholding',
    'get_all_shareholders'
]
