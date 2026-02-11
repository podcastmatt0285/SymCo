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
from sqlalchemy import create_engine, Column, String, Float, DateTime, Integer, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# ==========================
# DATABASE SETUP
# ==========================
DATABASE_URL = "sqlite:///./wadsworth.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ==========================
# CONSTANTS
# ==========================
RESERVE_TAX_RATE = 0.0000000001  # 0.00000001% per tick (~3.15% annual on cash reserves)
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
    total_shares_issued = Column(Integer, default=1000000)  # Total shares in circulation
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
                for attr in required:
                    if not hasattr(module, attr):
                        print(f"[Banks] ✗ {module_name} missing required attribute: {attr}")
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
    """
    Apply per-tick tax on cash reserves (operational costs).
    This creates natural decay and prevents infinite accumulation.
    """
    db = get_db()
    try:
        bank = db.query(BankEntity).filter(BankEntity.bank_id == bank_id).first()
        
        if not bank or bank.cash_reserves <= 0:
            return
        
        tax_amount = bank.cash_reserves * RESERVE_TAX_RATE
        bank.cash_reserves -= tax_amount
        bank.lifetime_expenses += tax_amount
        
        # Log every hour
        if current_tick % 3600 == 0:
            print(f"[Banks] {bank_id} reserve tax: ${tax_amount:.2f} (reserves: ${bank.cash_reserves:.2f})")
        
        db.commit()
        
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


async def tick(current_tick: int, now: datetime):
    """
    Banking system tick handler.
    
    Handles:
    - Reserve tax collection
    - Share price updates
    - Coordinated tick for all bank modules
    """
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
            
            # Call bank's tick handler
            await module.tick(current_tick, now, bank_entity)
            
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
    'BankEntity',
    'BankShareholding',
    'BankTransaction',
    'BANK_MODULES',
    'get_db'
]
