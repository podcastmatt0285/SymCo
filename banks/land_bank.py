"""
banks/land_bank.py - ENHANCED WITH INSOLVENCY SYSTEM

Land Bank with Failure Mechanics:
- Reverse dividends (solvency levies) when reserves go negative
- Bank Lien system for unpaid levies with interest accrual
- Automated garnishment of player cash
- "Quantitative easing" via emergency land auctions
- Full recovery cycle from insolvency to stability
"""

from datetime import datetime, timedelta
from typing import Optional, List
import random

# ==========================
# BANK IDENTITY
# ==========================
BANK_ID = "land_bank"
BANK_NAME = "Land Bank"
BANK_DESCRIPTION = "Government land auction house and real estate investment fund"

# Bank's player ID (used for market operations)
BANK_PLAYER_ID = -2

# ==========================
# CONSTANTS
# ==========================

# IPO Settings
IPO_SHARES = 1000000000000
IPO_PRICE = 25
SEED_CAPITAL = 0

# Dividend system
DIVIDEND_INTERVAL_TICKS = 600
DIVIDEND_PAYOUT_PERCENTAGE = 0.35
MIN_RESERVE_FOR_DIVIDENDS = 5000000000

# Stock split triggers
SPLIT_PRICE_THRESHOLD = 80.0
SPLIT_RATIO = 5
SPLIT_CHECK_INTERVAL = 720
MAX_TOTAL_SHARES = 50000000000000

# Buyback triggers
BUYBACK_RESERVE_THRESHOLD = 750000000
BUYBACK_PERCENTAGE = 0.33
BUYBACK_PREMIUM = 1.15
BUYBACK_CHECK_INTERVAL = 72
MAX_BUYBACK_COST_RATIO = 0.20

# ==========================
# INSOLVENCY SYSTEM CONSTANTS
# ==========================

# Levy (Reverse Dividend) System
INSOLVENCY_THRESHOLD = 0.0  # Trigger when reserves go negative
LEVY_FREQUENCY = 60  # Check/collect every 60 ticks (1 minute)

# Lien System
LIEN_INTEREST_RATE = 0.0001  # 0.01% per minute (~5.3% annual)
LIEN_GARNISHMENT_PERCENTAGE = 0.5  # Take 50% of available cash each minute

# Quantitative Easing (Land Printing)
QE_TRIGGER_SHARE_PRICE = -49.99  # Emergency land creation threshold
QE_AUCTION_INTERVAL = 60
QE_PRICE_DISCOUNT = 1.0  # No markup (vs normal 1.5x)
QE_MINIMUM_PRICE_RATIO = 0.75  # Floor at 75% of base

# State tracking
last_dividend_tick = 0
last_asset_valuation = 0.0
last_split_check_tick = 0
last_buyback_check_tick = 0
last_levy_tick = 0
last_lien_processing_tick = 0
last_qe_auction_tick = 0

# Special item type for bank shares
SHARE_ITEM_TYPE = "land_bank_shares"

# ==========================
# DATABASE MODELS (Additional)
# ==========================

from sqlalchemy import create_engine, Column, String, Float, DateTime, Integer, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./wadsworth.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class BankLien(Base):
    """Player debt to the bank from unpaid solvency levies."""
    __tablename__ = "bank_liens"
    
    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, index=True, nullable=False)
    bank_id = Column(String, index=True, nullable=False)
    
    # Debt details
    principal = Column(Float, default=0.0)  # Original debt amount
    interest_accrued = Column(Float, default=0.0)  # Accumulated interest
    total_paid = Column(Float, default=0.0)  # Total payments made
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    last_interest_accrual = Column(DateTime, default=datetime.utcnow)
    last_payment = Column(DateTime, nullable=True)
    
    @property
    def total_owed(self):
        """Total debt including interest."""
        return self.principal + self.interest_accrued - self.total_paid


# ==========================
# INITIALIZATION (UPDATED)
# ==========================

def initialize():
    """Initialize the Land Bank with insolvency system."""
    import banks
    
    # Create lien table
    Base.metadata.create_all(bind=engine)
    
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
                entity.share_price = IPO_PRICE
                bank_db.commit()
        finally:
            bank_db.close()
    
    # Execute IPO
    execute_ipo()
    
    print(f"[{BANK_NAME}] Enhanced Module initialized")
    print(f"  → Insolvency System: Active")
    print(f"  → Lien Interest: {LIEN_INTEREST_RATE*100:.2f}% per minute")
    print(f"  → QE Trigger: Share price < ${QE_TRIGGER_SHARE_PRICE:.2f}")


# ==========================
# IPO EXECUTION (Unchanged)
# ==========================

def execute_ipo():
    """Execute Initial Public Offering."""
    try:
        import market
        
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
        
        import inventory
        
        if SHARE_ITEM_TYPE not in inventory.ITEM_RECIPES:
            inventory.ITEM_RECIPES[SHARE_ITEM_TYPE] = {
                "name": "Land Bank Shares",
                "description": "Tradeable equity shares in the Land Bank",
                "category": "financial"
            }
        
        inventory.add_item(BANK_PLAYER_ID, SHARE_ITEM_TYPE, IPO_SHARES)
        
        order = market.create_order(
            player_id=BANK_PLAYER_ID,
            order_type=market.OrderType.SELL,
            order_mode=market.OrderMode.LIMIT,
            item_type=SHARE_ITEM_TYPE,
            quantity=IPO_SHARES,
            price=IPO_PRICE
        )
        
        if order:
            print(f"[{BANK_NAME}] 🎉 IPO EXECUTED: {IPO_SHARES:,} shares at ${IPO_PRICE:.2f}")
    
    except Exception as e:
        print(f"[{BANK_NAME}] ✗ IPO error: {e}")


# ==========================
# INSOLVENCY SYSTEM
# ==========================

def check_and_levy_shareholders(current_tick: int):
    """
    Levy shareholders when bank reserves are negative.
    This is the "reverse dividend" that bills shareholders for losses.
    """
    global last_levy_tick
    
    # Check every LEVY_FREQUENCY ticks
    if current_tick - last_levy_tick < LEVY_FREQUENCY:
        return
    
    last_levy_tick = current_tick
    
    import banks
    from auth import get_db as get_auth_db, Player
    
    bank_entity = banks.get_bank_entity(BANK_ID)
    
    if not bank_entity or bank_entity.cash_reserves >= INSOLVENCY_THRESHOLD:
        return  # Bank is solvent
    
    # Calculate total deficit
    deficit = abs(bank_entity.cash_reserves)
    
    print(f"[{BANK_NAME}] 🚨 INSOLVENCY DETECTED: ${deficit:,.2f} deficit")
    
    # Get all shareholders
    shareholders = get_all_shareholders()
    shareholders.pop(BANK_PLAYER_ID, None)  # Exclude bank itself
    
    if not shareholders:
        print(f"[{BANK_NAME}] No shareholders to levy")
        return
    
    total_levied = 0.0
    total_unpaid = 0.0
    
    # Levy each shareholder proportionally
    for player_id, shares_owned in shareholders.items():
        ownership_fraction = shares_owned / bank_entity.total_shares_issued
        levy_amount = deficit * ownership_fraction
        
        if levy_amount < 0.01:
            continue
        
        # Attempt to collect from player
        auth_db = get_auth_db()
        try:
            player = auth_db.query(Player).filter(Player.id == player_id).first()
            if not player:
                continue
            
            if player.cash_balance >= levy_amount:
                # Full payment
                player.cash_balance -= levy_amount
                total_levied += levy_amount
                
                print(f"[{BANK_NAME}] Levy ${levy_amount:,.2f} collected from Player {player_id}")
            else:
                # Partial payment + create lien for remainder
                paid_amount = player.cash_balance
                unpaid_amount = levy_amount - paid_amount
                
                player.cash_balance = 0.0
                total_levied += paid_amount
                total_unpaid += unpaid_amount
                
                # Create or update lien
                create_or_update_lien(player_id, unpaid_amount)
                
                print(f"[{BANK_NAME}] Player {player_id}: Paid ${paid_amount:.2f}, Lien created for ${unpaid_amount:.2f}")
            
            auth_db.commit()
        finally:
            auth_db.close()
    
    # Add collected funds to bank reserves
    if total_levied > 0:
        banks.add_bank_revenue(BANK_ID, total_levied, "Solvency levy collection")
    
    print(f"[{BANK_NAME}] 📊 LEVY COMPLETE: ${total_levied:,.2f} collected, ${total_unpaid:,.2f} in liens")


def create_or_update_lien(player_id: int, amount: float):
    """Create or update a bank lien for a player."""
    db = SessionLocal()
    try:
        lien = db.query(BankLien).filter(
            BankLien.player_id == player_id,
            BankLien.bank_id == BANK_ID
        ).first()
        
        if lien:
            # Add to existing lien
            lien.principal += amount
        else:
            # Create new lien
            lien = BankLien(
                player_id=player_id,
                bank_id=BANK_ID,
                principal=amount,
                interest_accrued=0.0,
                total_paid=0.0
            )
            db.add(lien)
        
        db.commit()
        print(f"[{BANK_NAME}] Lien for Player {player_id}: ${lien.total_owed:.2f} owed")
    finally:
        db.close()


def process_lien_system(current_tick: int):
    """
    Process all active liens:
    1. Accrue interest
    2. Attempt garnishment
    """
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
            # Skip if fully paid
            if lien.total_owed <= 0:
                continue
            
            # Accrue interest
            lien.interest_accrued += lien.total_owed * LIEN_INTEREST_RATE
            lien.last_interest_accrual = datetime.utcnow()
            
            # Attempt garnishment
            auth_db = get_auth_db()
            try:
                player = auth_db.query(Player).filter(Player.id == lien.player_id).first()
                if not player or player.cash_balance <= 0:
                    continue
                
                # Garnish percentage of available cash
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
                    
                    remaining = lien.total_owed
                    if remaining <= 0:
                        print(f"[{BANK_NAME}] ✅ Lien CLEARED for Player {lien.player_id}")
                    else:
                        print(f"[{BANK_NAME}] Garnished ${garnish_amount:.2f} from Player {lien.player_id} (${remaining:.2f} remains)")
            finally:
                auth_db.close()
        
        db.commit()
        
        # Add garnished funds to bank
        if total_garnished > 0:
            banks.add_bank_revenue(BANK_ID, total_garnished, "Lien garnishment")
            print(f"[{BANK_NAME}] 💰 Total garnishment: ${total_garnished:.2f}")
    
    finally:
        db.close()


# ==========================
# QUANTITATIVE EASING (LAND PRINTING)
# ==========================

def check_and_trigger_qe(current_tick: int):
    """
    Emergency land creation when share price is deeply negative.
    Creates discounted land auctions to restore bank NAV.
    """
    global last_qe_auction_tick
    
    import banks
    
    bank_entity = banks.get_bank_entity(BANK_ID)
    
    if not bank_entity:
        return
    
    # Check if QE is needed
    if bank_entity.share_price >= QE_TRIGGER_SHARE_PRICE:
        return
    
    # Check if enough time has passed
    if current_tick - last_qe_auction_tick < QE_AUCTION_INTERVAL:
        return
    
    last_qe_auction_tick = current_tick
    
    print(f"[{BANK_NAME}] 🏦 QUANTITATIVE EASING ACTIVATED")
    print(f"[{BANK_NAME}] Share price: ${bank_entity.share_price:.2f} (Crisis threshold: ${QE_TRIGGER_SHARE_PRICE:.2f})")
    
    # Create emergency land auction
    create_qe_auction()


def create_qe_auction():
    """Create a discounted land auction during QE mode."""
    from land import create_land_plot, get_land_plot, TERRAIN_TYPES, PROXIMITY_FEATURES
    from land_market import TERRAIN_BASE_PRICES, GOVERNMENT_ID, generate_random_proximity_features
    
    # Pick random terrain
    terrain = random.choice(list(TERRAIN_TYPES.keys()))
    
    # Generate random proximity features for variety
    proximity_features = generate_random_proximity_features()
    
    # Create government-owned land with proximity features
    plot = create_land_plot(
        owner_id=GOVERNMENT_ID,
        terrain_type=terrain,
        proximity_features=proximity_features if proximity_features else None,
        size=1.0,
        is_starter=False,
        is_government=True
    )
    
    # QE pricing: no markup, aggressive floor
    base_price = TERRAIN_BASE_PRICES.get(terrain, 15000)
    
    # Apply proximity modifiers to base price
    price_modifier = 1.0
    for feature in (proximity_features or []):
        if feature in PROXIMITY_FEATURES:
            price_modifier *= PROXIMITY_FEATURES[feature]["tax_modifier"]
    
    base_price *= price_modifier
    starting_price = base_price * QE_PRICE_DISCOUNT
    minimum_price = base_price * QE_MINIMUM_PRICE_RATIO
    
    # Create auction directly
    from land_market import GovernmentAuction, AUCTION_DURATION_TICKS, SessionLocal as LandMarketSession
    
    db = LandMarketSession()
    try:
        auction = GovernmentAuction(
            land_plot_id=plot.id,
            starting_price=starting_price,
            current_price=starting_price,
            minimum_price=minimum_price,
            end_time=datetime.utcnow() + timedelta(seconds=AUCTION_DURATION_TICKS)
        )
        
        db.add(auction)
        db.commit()
        
        features_str = f" + {', '.join(proximity_features)}" if proximity_features else ""
        print(f"[{BANK_NAME}] 🚨 QE AUCTION #{auction.id}: {terrain.title()}{features_str} @ ${starting_price:,.2f} (Floor: ${minimum_price:,.2f})")
    finally:
        db.close()


# ==========================
# ASSET VALUATION (Unchanged)
# ==========================

def calculate_land_assets() -> float:
    """Calculate total value of land assets held by the bank."""
    try:
        from land_market import get_active_auctions, get_land_bank_plots
        
        total_value = 0.0
        
        auctions = get_active_auctions()
        for auction in auctions:
            total_value += auction.current_price
        
        bank_plots = get_land_bank_plots()
        for plot_entry in bank_plots:
            if plot_entry.last_auction_price:
                total_value += plot_entry.last_auction_price * 0.9
        
        return total_value
    except:
        return 0.0


def update_asset_valuation():
    """Update the bank's asset value."""
    import banks
    
    land_value = calculate_land_assets()
    banks.update_bank_assets(BANK_ID, land_value)
    
    global last_asset_valuation
    last_asset_valuation = land_value


# ==========================
# SHARE OWNERSHIP TRACKING (Unchanged)
# ==========================

def get_all_shareholders() -> dict:
    """Get all current shareholders."""
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
        
        # Get lien information
        lien_amount = get_player_lien_balance(player_id)
        
        return {
            "shares_owned": shares,
            "current_value": current_value,
            "ownership_percentage": ownership_pct,
            "share_price": bank_entity.share_price,
            "lien_balance": lien_amount
        }
    except:
        return {
            "shares_owned": 0,
            "current_value": 0.0,
            "ownership_percentage": 0.0,
            "lien_balance": 0.0
        }


def get_player_lien_balance(player_id: int) -> float:
    """Get player's total lien balance."""
    db = SessionLocal()
    try:
        lien = db.query(BankLien).filter(
            BankLien.player_id == player_id,
            BankLien.bank_id == BANK_ID
        ).first()
        
        return lien.total_owed if lien else 0.0
    finally:
        db.close()


# ==========================
# REVENUE TRACKING (Unchanged)
# ==========================

def record_auction_sale(sale_price: float, plot_id: int):
    """Record revenue from a successful land auction."""
    import banks
    
    banks.add_bank_revenue(
        BANK_ID,
        sale_price,
        f"Land auction sale - Plot #{plot_id}"
    )
    
    print(f"[{BANK_NAME}] Revenue: ${sale_price:,.2f} from plot #{plot_id} auction")


# ==========================
# DIVIDEND SYSTEM (Modified)
# ==========================

def pay_dividends():
    """
    Distribute dividends - ONLY if bank is solvent.
    No dividends during insolvency.
    """
    import banks
    from auth import get_db as get_auth_db, Player
    
    bank_db = banks.get_db()
    try:
        bank_entity = bank_db.query(banks.BankEntity).filter(
            banks.BankEntity.bank_id == BANK_ID
        ).first()
        
        if not bank_entity:
            return
        
        # Check solvency
        if bank_entity.cash_reserves < INSOLVENCY_THRESHOLD:
            print(f"[{BANK_NAME}] ⚠️  Dividends SUSPENDED - Bank is insolvent")
            return
        
        # Check minimum reserves
        if bank_entity.cash_reserves < MIN_RESERVE_FOR_DIVIDENDS:
            print(f"[{BANK_NAME}] ⚠️  Dividends SUSPENDED - Reserves below ${MIN_RESERVE_FOR_DIVIDENDS:,.0f}")
            return
        
        # Calculate dividend pool
        dividend_pool = bank_entity.cash_reserves * DIVIDEND_PAYOUT_PERCENTAGE
        dividend_pool = min(dividend_pool, bank_entity.cash_reserves * 0.75)
        
        # Get shareholders
        shareholders = get_all_shareholders()
        shareholders.pop(BANK_PLAYER_ID, None)
        
        if not shareholders:
            return
        
        total_paid = 0.0
        
        # Distribute to each shareholder
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
                description=f"Biweekly dividend - {shares_owned} shares"
            )
            bank_db.add(transaction)
            
            total_paid += dividend_amount
        
        bank_entity.cash_reserves -= total_paid
        bank_entity.total_dividends_paid += total_paid
        bank_entity.last_dividend_date = datetime.utcnow()
        
        bank_db.commit()
        
        print(f"[{BANK_NAME}] 📊 DIVIDEND: ${total_paid:,.2f} to {len(shareholders)} shareholders")
    
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
        
        # Check trigger
        if bank_entity.share_price <= SPLIT_PRICE_THRESHOLD:
            return
        
        # Check max shares
        if bank_entity.total_shares_issued * SPLIT_RATIO > MAX_TOTAL_SHARES:
            return
        
        print(f"[{BANK_NAME}] 🚀 STOCK SPLIT EVENT!")
        print(f"[{BANK_NAME}] Share price ${bank_entity.share_price:.2f} exceeds ${SPLIT_PRICE_THRESHOLD:.2f} threshold")
        print(f"[{BANK_NAME}] Executing {SPLIT_RATIO}-for-1 split...")
        
        # Update all shareholder inventories
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
            print(f"[{BANK_NAME}] Split inventory error: {e}")
            import traceback
            traceback.print_exc()
        
        # Update bank entity
        old_price = bank_entity.share_price
        old_shares = bank_entity.total_shares_issued
        
        bank_entity.total_shares_issued *= SPLIT_RATIO
        bank_entity.share_price /= SPLIT_RATIO
        
        bank_db.commit()
        
        print(f"[{BANK_NAME}] ✓ Split completed:")
        print(f"[{BANK_NAME}]   Shares: {old_shares:,} → {bank_entity.total_shares_issued:,}")
        print(f"[{BANK_NAME}]   Price: ${old_price:.2f} → ${bank_entity.share_price:.2f}")
    
    finally:
        bank_db.close()


# ==========================
# SHARE BUYBACK
# ==========================

def check_and_execute_buyback(current_tick: int):
    """
    Check if buyback should occur.
    Triggers when reserves are high and executes at premium to market price.
    """
    import banks
    
    global last_buyback_check_tick
    
    if current_tick - last_buyback_check_tick < BUYBACK_CHECK_INTERVAL:
        return
    
    last_buyback_check_tick = current_tick
    
    bank_entity = banks.get_bank_entity(BANK_ID)
    
    if not bank_entity:
        return
    
    # Check trigger: High reserves
    if bank_entity.cash_reserves < BUYBACK_RESERVE_THRESHOLD:
        return
    
    # Calculate buyback parameters
    shares_to_buyback = int(bank_entity.total_shares_issued * BUYBACK_PERCENTAGE)
    buyback_price = bank_entity.share_price * BUYBACK_PREMIUM
    total_cost = shares_to_buyback * buyback_price
    
    # Safety cap - don't spend more than 20% of reserves
    max_cost = bank_entity.cash_reserves * MAX_BUYBACK_COST_RATIO
    if total_cost > max_cost:
        shares_to_buyback = int(max_cost / buyback_price)
        total_cost = shares_to_buyback * buyback_price
    
    if shares_to_buyback == 0 or bank_entity.cash_reserves < total_cost:
        return
    
    print(f"[{BANK_NAME}] 💰 BUYBACK TRIGGERED!")
    print(f"  → Cash Reserves: ${bank_entity.cash_reserves:,.2f} (Threshold: ${BUYBACK_RESERVE_THRESHOLD:,.2f})")
    print(f"  → Buying: {shares_to_buyback:,} shares ({BUYBACK_PERCENTAGE*100:.0f}% of outstanding)")
    print(f"  → Buyback Price: ${buyback_price:.2f} ({BUYBACK_PREMIUM*100:.1f}% premium)")
    print(f"  → Total Cost: ${total_cost:,.2f}")
    
    try:
        import market
        from auth import get_db as get_auth_db, Player
        
        # Fund the bank's market account for the buyback
        auth_db = get_auth_db()
        try:
            bank_account = auth_db.query(Player).filter(Player.id == BANK_PLAYER_ID).first()
            if not bank_account:
                # Create bank account if it doesn't exist
                bank_account = Player(
                    id=BANK_PLAYER_ID,
                    business_name=BANK_NAME,
                    password_hash="SYSTEM_BANK",
                    cash_balance=total_cost
                )
                auth_db.add(bank_account)
            else:
                # Add buyback funds to account
                bank_account.cash_balance += total_cost
            auth_db.commit()
        finally:
            auth_db.close()
        
        # Place buy order at premium price
        order = market.create_order(
            player_id=BANK_PLAYER_ID,
            order_type=market.OrderType.BUY,
            order_mode=market.OrderMode.LIMIT,
            item_type=SHARE_ITEM_TYPE,
            quantity=shares_to_buyback,
            price=buyback_price
        )
        
        if order:
            # Deduct from bank reserves
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
        else:
            print(f"[{BANK_NAME}] ✗ Buyback failed - could not create order")
    
    except Exception as e:
        print(f"[{BANK_NAME}] Buyback error: {e}")
        import traceback
        traceback.print_exc()


def retire_bought_shares():
    """
    Retire shares bought back by the bank.
    Removes them from circulation permanently.
    FIXED: Only retires shares NOT locked in active sell orders (IPO).
    """
    try:
        import inventory
        import banks
        import market
        
        # Check how many shares the bank holds in inventory
        bank_shares = inventory.get_item_quantity(BANK_PLAYER_ID, SHARE_ITEM_TYPE)
        
        if bank_shares <= 0:
            return  # Nothing to retire
        
        # Calculate shares locked in active sell orders (IPO)
        # IMPORTANT: Include both ACTIVE and PARTIALLY_FILLED orders
        market_db = market.get_db()
        try:
            # Get all active/partial sell orders from the bank
            sell_orders = market_db.query(market.MarketOrder).filter(
                market.MarketOrder.player_id == BANK_PLAYER_ID,
                market.MarketOrder.item_type == SHARE_ITEM_TYPE,
                market.MarketOrder.order_type == market.OrderType.SELL,
                market.MarketOrder.status.in_([market.OrderStatus.ACTIVE, market.OrderStatus.PARTIALLY_FILLED])
            ).all()
            
            # Sum up the unfilled quantity from each order
            locked_shares = sum(order.quantity - order.quantity_filled for order in sell_orders)
        finally:
            market_db.close()
        
        # Calculate shares available for retirement (bought back shares only)
        shares_to_retire = bank_shares - locked_shares
        
        if shares_to_retire <= 0:
            # All shares are locked in IPO, nothing to retire
            return
        
        print(f"[{BANK_NAME}] Share retirement analysis:")
        print(f"  → Total in inventory: {bank_shares:.0f}")
        print(f"  → Locked in IPO: {locked_shares:.0f}")
        print(f"  → Available to retire: {shares_to_retire:.0f}")
        
        # Remove only the buyback shares from inventory
        success = inventory.remove_item(BANK_PLAYER_ID, SHARE_ITEM_TYPE, shares_to_retire)
        
        if not success:
            print(f"[{BANK_NAME}] ✗ Failed to remove shares from inventory")
            return
        
        # Reduce total shares issued
        bank_db = banks.get_db()
        try:
            bank_entity = bank_db.query(banks.BankEntity).filter(
                banks.BankEntity.bank_id == BANK_ID
            ).first()
            
            if bank_entity:
                old_total = bank_entity.total_shares_issued
                bank_entity.total_shares_issued -= shares_to_retire
                
                # Prevent going negative
                if bank_entity.total_shares_issued < 0:
                    bank_entity.total_shares_issued = 0
                
                bank_db.commit()
                
                print(f"[{BANK_NAME}] 🔥 RETIRED {shares_to_retire:.0f} shares")
                print(f"[{BANK_NAME}]   Total shares: {old_total:,} → {bank_entity.total_shares_issued:,}")
                print(f"[{BANK_NAME}]   New share price: ${bank_entity.share_price:.2f}")
        finally:
            bank_db.close()
    
    except Exception as e:
        print(f"[{BANK_NAME}] Retire error: {e}")
        import traceback
        traceback.print_exc()

# ==========================
# TICK HANDLER (ENHANCED)
# ==========================

async def tick(current_tick: int, now: datetime, bank_entity):
    """
    Enhanced tick handler with insolvency system.
    """
    global last_dividend_tick
    
    # Update asset valuation every hour
    if current_tick % 3600 == 0:
        update_asset_valuation()
    
    # INSOLVENCY SYSTEM - Highest priority
    check_and_levy_shareholders(current_tick)
    process_lien_system(current_tick)
    check_and_trigger_qe(current_tick)
    
    # Normal operations (only if solvent)
    if bank_entity.cash_reserves >= INSOLVENCY_THRESHOLD:
        # Check for dividend distribution
        if current_tick - last_dividend_tick >= DIVIDEND_INTERVAL_TICKS:
            pay_dividends()
            last_dividend_tick = current_tick
        
        # Stock split checks
        check_and_execute_split(current_tick)
        
        # Buyback checks
        check_and_execute_buyback(current_tick)
        
        # Retire bought-back shares
        if current_tick % 3600 == 0:
            retire_bought_shares()
    
    # Log stats every hour
    if current_tick % 3600 == 0:
        nav = bank_entity.cash_reserves + bank_entity.asset_value
        shareholders = get_all_shareholders()
        total_player_shares = sum(shares for pid, shares in shareholders.items() if pid != BANK_PLAYER_ID)
        
        # Count active liens
        db = SessionLocal()
        active_liens = db.query(BankLien).filter(BankLien.principal + BankLien.interest_accrued - BankLien.total_paid > 0).count()
        total_lien_debt = sum(l.total_owed for l in db.query(BankLien).all())
        db.close()
        
        status = "INSOLVENT" if bank_entity.cash_reserves < 0 else "SOLVENT"
        qe_status = " [QE ACTIVE]" if bank_entity.share_price < QE_TRIGGER_SHARE_PRICE else ""
        
        print(f"[{BANK_NAME}] {status}{qe_status} | NAV: ${nav:,.2f} | " +
              f"Share Price: ${bank_entity.share_price:.2f} | " +
              f"Shares: {bank_entity.total_shares_issued:,} | " +
              f"Player Holdings: {total_player_shares:,.0f} | " +
              f"Active Liens: {active_liens} (${total_lien_debt:,.2f})")


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
    'get_all_shareholders',
    'record_auction_sale',
    'BankLien'
]
