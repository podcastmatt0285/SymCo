"""
banks.py

Dynamic banking system manager for the economic simulation.
Handles:
- Dynamic loading of bank modules from /banks directory
- Bank entity state management (assets, reserves, shares)
- Reserve tax collection (cash decay)
- Coordinated tick management for all banks
- Bank valuation and performance tracking
"""

import os
import importlib
from datetime import datetime
from typing import Dict, Optional, List
from sqlalchemy import Column, String, Float, DateTime, Integer, BigInteger, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# ==========================
# DATABASE SETUP
# ==========================
from database import engine, SessionLocal
Base = declarative_base()

# ==========================
# CONSTANTS
# ==========================
AUTONOMOUS_BANK_TAX_RATE = 0.0001  # 0.01% daily → ~3.65% annual on cash reserves
TICKS_PER_DAY = 17280              # 24 h × 720 ticks/h (5 sec/tick)
BANKS_DIRECTORY = "./banks"

# ==========================
# DATABASE MODELS
# ==========================

class BankEntity(Base):
    """
    Core bank entity model.
    Tracks the financial state of each autonomous bank.
    """
    __tablename__ = "bank_entities"
    
    id = Column(Integer, primary_key=True, index=True)
    bank_id = Column(String, unique=True, index=True, nullable=False)  # e.g., "land_bank"
    
    # Financial state
    cash_reserves = Column(Float, default=0.0)  # Liquid cash
    asset_value = Column(Float, default=0.0)    # Value of illiquid assets (land, inventory, etc.)
    
    # Share system
    total_shares_issued = Column(BigInteger, default=1000000)  # Total shares in circulation
    share_price = Column(Float, default=1.0)  # Current share price
    
    # Dividend tracking
    accumulated_profits = Column(Float, default=0.0)  # Profits since last dividend
    last_dividend_date = Column(DateTime, default=datetime.utcnow)
    total_dividends_paid = Column(Float, default=0.0)
    
    # Performance metrics
    lifetime_revenue = Column(Float, default=0.0)
    lifetime_expenses = Column(Float, default=0.0)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    description = Column(String, nullable=True)


class BankShareholding(Base):
    """
    Player ownership of bank shares.
    """
    __tablename__ = "bank_shareholdings"
    
    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, index=True, nullable=False)
    bank_id = Column(String, index=True, nullable=False)
    
    shares_owned = Column(Integer, default=0)
    
    # Purchase history
    total_invested = Column(Float, default=0.0)  # How much cash spent on shares
    total_dividends_received = Column(Float, default=0.0)
    
    # Timestamps
    first_purchase = Column(DateTime, default=datetime.utcnow)
    last_transaction = Column(DateTime, default=datetime.utcnow)


class BankTransaction(Base):
    """
    Transaction history for banks.
    """
    __tablename__ = "bank_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    bank_id = Column(String, index=True, nullable=False)
    
    transaction_type = Column(String, nullable=False)  # revenue, expense, dividend, split, buyback
    amount = Column(Float, nullable=False)
    description = Column(String, nullable=True)
    
    # For share-related transactions
    shares_affected = Column(Integer, nullable=True)
    player_id = Column(Integer, nullable=True)
    
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)


# ==========================
# IN-MEMORY STATE
# ==========================

# Registry of loaded bank modules
BANK_MODULES = {}

# Cache of bank entities (refreshed from DB periodically)
BANK_CACHE = {}

# ==========================
# HELPER FUNCTIONS
# ==========================

def get_db():
    """Get database session."""
    db = SessionLocal()
    return db


def get_bank_entity(bank_id: str) -> Optional[BankEntity]:
    """Get a bank entity from database."""
    db = get_db()
    try:
        bank = db.query(BankEntity).filter(BankEntity.bank_id == bank_id).first()
        return bank
    finally:
        db.close()


def update_bank_cache():
    """Refresh the in-memory cache of bank entities."""
    global BANK_CACHE
    db = get_db()
    try:
        banks = db.query(BankEntity).filter(BankEntity.is_active == True).all()
        BANK_CACHE = {bank.bank_id: bank for bank in banks}
    finally:
        db.close()


# ==========================
# DYNAMIC MODULE LOADING
# ==========================

def load_bank_modules():
    """
    Dynamically load all bank modules from /banks directory.
    Each module must define:
    - BANK_ID: str
    - BANK_NAME: str
    - BANK_DESCRIPTION: str
    - initialize() function
    - async tick(current_tick, now, bank_entity) function
    """
    global BANK_MODULES
    
    if not os.path.exists(BANKS_DIRECTORY):
        os.makedirs(BANKS_DIRECTORY)
        print(f"[Banks] Created {BANKS_DIRECTORY} directory")
        return
    
    print(f"[Banks] Loading bank modules from {BANKS_DIRECTORY}/")
    
    for filename in os.listdir(BANKS_DIRECTORY):
        if filename.endswith(".py") and not filename.startswith("_"):
            module_name = filename[:-3]
            
            try:
                # Import the module
                module = importlib.import_module(f"banks.{module_name}")
                
                # Validate required attributes
                required = ["BANK_ID", "BANK_NAME", "BANK_DESCRIPTION", "initialize", "tick"]
                missing = [attr for attr in required if not hasattr(module, attr)]
                if missing:
                    print(f"[Banks] ✗ {module_name} missing required attributes: {', '.join(missing)} — skipping")
                    continue

                bank_id = module.BANK_ID
                BANK_MODULES[bank_id] = module

                print(f"[Banks] ✓ Loaded {bank_id} ({module.BANK_NAME})")
                
            except Exception as e:
                print(f"[Banks] ✗ Failed to load {module_name}: {e}")
    
    print(f"[Banks] Loaded {len(BANK_MODULES)} bank module(s)")


def register_bank_entity(bank_id: str, name: str, description: str) -> BankEntity:
    """
    Register a bank entity in the database.
    Called by each bank module during initialization.
    """
    db = get_db()
    try:
        # Check if already exists
        existing = db.query(BankEntity).filter(BankEntity.bank_id == bank_id).first()
        
        if existing:
            print(f"[Banks] Bank {bank_id} already registered")
            return existing
        
        # Create new bank entity
        bank = BankEntity(
            bank_id=bank_id,
            description=description,
            cash_reserves=0.0,
            asset_value=0.0,
            total_shares_issued=1000000,  # Start with 1M shares
            share_price=1.0  # $1.00 per share initial price
        )
        
        db.add(bank)
        db.commit()
        db.refresh(bank)
        
        print(f"[Banks] ✓ Registered {name} (ID: {bank_id})")
        return bank
        
    finally:
        db.close()


# ==========================
# FINANCIAL OPERATIONS
# ==========================

def add_bank_revenue(bank_id: str, amount: float, description: str):
    """
    Add revenue to a bank (from sales, fees, interest, etc.).
    Increases cash reserves and accumulated profits.
    """
    db = get_db()
    try:
        bank = db.query(BankEntity).filter(BankEntity.bank_id == bank_id).first()
        
        if not bank:
            return
        
        bank.cash_reserves += amount
        bank.accumulated_profits += amount
        bank.lifetime_revenue += amount
        
        # Record transaction
        transaction = BankTransaction(
            bank_id=bank_id,
            transaction_type="revenue",
            amount=amount,
            description=description
        )
        db.add(transaction)
        
        db.commit()
        
    finally:
        db.close()


def add_bank_expense(bank_id: str, amount: float, description: str) -> bool:
    """
    Deduct expense from a bank (for operations, purchases, etc.).
    Returns False if insufficient reserves.
    """
    # Guard against negative amounts: subtracting a negative number would
    # silently *add* cash to reserves and reduce lifetime_expenses, which can
    # be exploited to print money.
    if amount <= 0:
        return False

    db = get_db()
    try:
        bank = db.query(BankEntity).filter(BankEntity.bank_id == bank_id).first()

        if not bank or bank.cash_reserves < amount:
            return False
        
        bank.cash_reserves -= amount
        bank.accumulated_profits -= amount
        bank.lifetime_expenses += amount
        
        # Record transaction
        transaction = BankTransaction(
            bank_id=bank_id,
            transaction_type="expense",
            amount=amount,
            description=description
        )
        db.add(transaction)
        
        db.commit()
        return True
        
    finally:
        db.close()


def update_bank_assets(bank_id: str, new_asset_value: float):
    """
    Update the asset value of a bank.
    Called by bank modules to report their illiquid asset valuations.
    """
    db = get_db()
    try:
        bank = db.query(BankEntity).filter(BankEntity.bank_id == bank_id).first()
        
        if not bank:
            return
        
        bank.asset_value = new_asset_value
        db.commit()
        
    finally:
        db.close()


def apply_reserve_tax(bank_id: str, current_tick: int):
    """Daily tax on autonomous bank cash reserves, credited to the federal government.

    Runs once per day (every TICKS_PER_DAY ticks). Prevents indefinite accumulation
    and provides a steady revenue stream for the federal government.
    """
    if current_tick % TICKS_PER_DAY != 0:
        return
    db = get_db()
    try:
        bank = db.query(BankEntity).filter(BankEntity.bank_id == bank_id).first()
        if not bank or bank.cash_reserves <= 0:
            return
        tax_amount = bank.cash_reserves * AUTONOMOUS_BANK_TAX_RATE
        bank.cash_reserves   -= tax_amount
        bank.lifetime_expenses += tax_amount
        db.commit()

        # Credit the federal government's operating cash (auth DB, player_id = 0)
        try:
            from auth import get_db as _adb, Player as _Player
            _adb_conn = _adb()
            gov = _adb_conn.query(_Player).filter(_Player.id == 0).first()
            if gov:
                gov.cash_balance = (gov.cash_balance or 0.0) + tax_amount
                _adb_conn.commit()
            _adb_conn.close()
        except Exception as _e:
            print(f"[Banks] Gov credit error ({bank_id}): {_e}")

        try:
            from govt_ledger import log_gov_event
            log_gov_event("autonomous_bank_tax", "in", tax_amount, "USD",
                          bank_id.replace("_", " ").title(),
                          f"Daily 0.01% reserve tax on ${bank.cash_reserves + tax_amount:,.2f} reserves")
        except Exception:
            pass
        print(f"[Banks] {bank_id} daily reserve tax: ${tax_amount:.4f} → federal gov")
    finally:
        db.close()


def calculate_bank_value(bank_id: str) -> float:
    """
    Calculate total value of a bank (NAV = Net Asset Value).
    NAV = Cash Reserves + Asset Value
    """
    bank = get_bank_entity(bank_id)
    if not bank:
        return 0.0
    
    return bank.cash_reserves + bank.asset_value


def update_share_price(bank_id: str):
    """
    Update share price based on bank NAV.
    Share Price = NAV / Total Shares Issued
    """
    db = get_db()
    try:
        bank = db.query(BankEntity).filter(BankEntity.bank_id == bank_id).first()
        
        if not bank or bank.total_shares_issued == 0:
            return
        
        nav = bank.cash_reserves + bank.asset_value
        bank.share_price = nav / bank.total_shares_issued
        
        db.commit()
        
    finally:
        db.close()


# ==========================
# MODULE LIFECYCLE
# ==========================

def initialize():
    """
    Initialize the banking system.
    Creates database tables and loads all bank modules.
    """
    print("[Banks] Creating database tables...")
    Base.metadata.create_all(bind=engine)
    
    # Load bank modules
    load_bank_modules()
    
    # Initialize each bank module
    for bank_id, module in BANK_MODULES.items():
        try:
            module.initialize()
        except Exception as e:
            print(f"[Banks] ✗ Failed to initialize {bank_id}: {e}")
    
    # Update cache
    update_bank_cache()
    
    print(f"[Banks] System initialized with {len(BANK_MODULES)} active bank(s)")


def tick(current_tick: int, now: datetime):
    """
    Banking system tick handler.

    Handles:
    - Reserve tax collection
    - Share price updates
    - Coordinated tick for all bank modules

    SYNC on purpose: app.py dispatches sync ticks via run_in_threadpool, so
    all the DB work below runs in a worker thread. The previous async version
    executed every bank's queries directly on the event loop, blocking all
    HTTP requests each tick. The bank modules' tick() functions are async in
    signature only (zero awaits), so each is driven to completion here with
    asyncio.run() inside the worker thread.
    """
    import asyncio

    # Update cache every 60 ticks (1 minute)
    if current_tick % 60 == 0:
        update_bank_cache()

    # Process each registered bank
    for bank_id, module in BANK_MODULES.items():
        try:
            # Apply reserve tax
            apply_reserve_tax(bank_id, current_tick)

            # Get fresh bank entity
            bank_entity = get_bank_entity(bank_id)

            if not bank_entity:
                continue

            # Call bank's tick handler (async signature, sync body)
            asyncio.run(module.tick(current_tick, now, bank_entity))

            # Update share price based on latest NAV
            update_share_price(bank_id)

        except Exception as e:
            print(f"[Banks] ERROR in {bank_id} tick: {e}")

    # Log system stats every hour
    if current_tick % 3600 == 0:
        log_banking_stats()


def log_banking_stats():
    """Log statistics about the banking system."""
    db = get_db()
    try:
        banks = db.query(BankEntity).filter(BankEntity.is_active == True).all()
        
        total_reserves = sum(b.cash_reserves for b in banks)
        total_assets = sum(b.asset_value for b in banks)
        total_nav = total_reserves + total_assets
        
        print(f"[Banks] System Stats: {len(banks)} bank(s), Total NAV: ${total_nav:,.2f} " +
              f"(Reserves: ${total_reserves:,.2f}, Assets: ${total_assets:,.2f})")
        
    finally:
        db.close()


# ==========================
# ETF SHARE LIQUIDITY
# ==========================

_etf_bid_last_tick: dict = {}  # bank_id -> last tick when bid was placed

def maintain_etf_share_bid(
    bank_id: str,
    bank_player_id: int,
    share_item: str,
    bank_entity,
    current_tick: int,
    interval: int = 360,
    bid_pct: float = 0.92,
    qty_pct: float = 0.005,
    reserve_pct: float = 0.03,
) -> None:
    """Post a standing buy order for ETF/fund shares to provide sell-side liquidity.

    Runs every *interval* ticks. Cancels the previous bid and places a new one at
    *bid_pct* × current share price. The bid quantity is limited to *qty_pct* of
    total_shares_issued and by *reserve_pct* of cash_reserves (so the bank never
    over-commits its cash on share buybacks).
    """
    global _etf_bid_last_tick
    last = _etf_bid_last_tick.get(bank_id, 0)
    if current_tick - last < interval:
        return
    _etf_bid_last_tick[bank_id] = current_tick

    try:
        import market as _mkt
        share_price = bank_entity.share_price or 0
        if share_price <= 0:
            return

        mdb = _mkt.get_db()
        try:
            # Cancel existing standing bids from this bank
            old_bids = mdb.query(_mkt.MarketOrder).filter(
                _mkt.MarketOrder.player_id == bank_player_id,
                _mkt.MarketOrder.item_type == share_item,
                _mkt.MarketOrder.order_type == _mkt.OrderType.BUY.value,
                _mkt.MarketOrder.status.in_([
                    _mkt.OrderStatus.ACTIVE.value,
                    _mkt.OrderStatus.PARTIALLY_FILLED.value,
                ]),
            ).all()
            for bid in old_bids:
                bid.status = _mkt.OrderStatus.CANCELLED.value
            mdb.commit()
        finally:
            mdb.close()

        bid_price = share_price * bid_pct
        total_shares = bank_entity.total_shares_issued or 0
        cash = bank_entity.cash_reserves or 0
        if cash <= 0 or bid_price <= 0:
            return

        max_by_qty = total_shares * qty_pct
        max_by_cash = (cash * reserve_pct) / bid_price
        qty = max(1.0, min(max_by_qty, max_by_cash))

        _mkt.create_order(
            player_id=bank_player_id,
            order_type=_mkt.OrderType.BUY,
            order_mode=_mkt.OrderMode.LIMIT,
            item_type=share_item,
            quantity=qty,
            price=bid_price,
        )
        print(f"[Banks/{bank_id}] Standing bid: {qty:,.0f} {share_item} @ ${bid_price:.6f}")
    except Exception as e:
        print(f"[Banks/{bank_id}] Standing bid error: {e}")


# ==========================
# PUBLIC API
# ==========================

__all__ = [
    'get_bank_entity',
    'register_bank_entity',
    'add_bank_revenue',
    'add_bank_expense',
    'update_bank_assets',
    'calculate_bank_value',
    'update_share_price',
    'maintain_etf_share_bid',
    'BankEntity',
    'BankShareholding',
    'BankTransaction',
    'BANK_MODULES',
    'get_db'
]
