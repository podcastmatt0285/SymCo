"""
banks/brokerage_firm.py - THE SYMCO BROKERAGE FIRM

A comprehensive financial intermediary providing:

SCPE (SymCo Player Exchange):
- Player company IPOs with 10 different offering structures
- Multiple share classes with various dividend types
- Margin trading with dynamic 2x-25x leverage
- Short selling of player company shares
- Circuit breakers for "too big to fail" companies

SCCE (SymCo Commodities Exchange):
- Commodity borrowing/lending between players
- Dynamic due dates based on volatility and credit
- 105% collateral requirements
- 50/50 fee split between lender and Firm

Risk Engine:
- Credit rating system (0-100)
- Net Liquidation Value monitoring
- 6-level liquidation cascade
- Lien creation and garnishment

The Firm:
- Starting capital: $500,000,000
- No shares of its own issued
- Revenue from fees, spreads, dividends on held shares
- Can go broke (freezes operations)
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum
import random
import json

from sqlalchemy import create_engine, Column, String, Float, DateTime, Integer, Boolean, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

from brokerage_order_book import (
    place_limit_order, place_market_order, cancel_order,
    get_order_book_depth, get_recent_fills,
    OrderBook, OrderFill, OrderType, OrderSide, OrderStatus
)
import brokerage_order_book

# ==========================
# DATABASE SETUP
# ==========================
DATABASE_URL = "sqlite:///./symco.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ==========================
# BANK IDENTITY
# ==========================
BANK_ID = "brokerage_firm"
BANK_NAME = "SymCo Brokerage Firm"
BANK_DESCRIPTION = "Full-service financial intermediary: IPOs, margin trading, short selling, and commodity lending"
BANK_PLAYER_ID = -5  # The Firm's vault/trading account

# ==========================
# FINANCIAL CONSTANTS
# ==========================
STARTING_CAPITAL = 500_000_000.00  # $500 million
MINIMUM_OPERATING_RESERVE = 10_000_000.00  # $10 million floor

# Trading fees
EQUITY_TRADE_COMMISSION = 0.001  # 0.1% per trade
MARGIN_BASE_INTEREST_RATE = 0.05  # 5% annual base (modified by credit)

# Commodity lending
COLLATERAL_REQUIREMENT = 1.05  # 105%
LENDING_FEE_SPLIT = 0.50  # 50% to Firm, 50% to lender
LATE_FEE_DAILY_RATE = 0.10  # 10% per day on collateral value
LATE_FEE_SPLIT = 0.50  # 50% to Firm, 50% to lender
MAX_LATE_DAYS_BEFORE_FORCE_CLOSE = 3

# Margin trading
MIN_MARGIN_MULTIPLIER = 2.0
MAX_MARGIN_MULTIPLIER = 25.0
MARGIN_MAINTENANCE_RATIO = 0.25  # 25% maintenance margin

# Short selling
SHORT_COLLATERAL_REQUIREMENT = 1.50  # 150% for share shorts

# Circuit breakers (TBTF only)
TBTF_MIN_MARKET_CAP = 1_000_000  # $1M
TBTF_MIN_SHAREHOLDERS = 20
TBTF_MIN_DAYS_PUBLIC = 90
TBTF_MIN_DIVIDEND_STREAK = 10
TBTF_MIN_FOUNDER_CREDIT = 70

CIRCUIT_BREAKER_LEVEL_1 = (-0.15, 60, 15)  # 15% drop in 60min = 15min halt
CIRCUIT_BREAKER_LEVEL_2 = (-0.25, 60, 60)  # 25% drop in 60min = 1hr halt
CIRCUIT_BREAKER_LEVEL_3 = (-0.35, None, 1440)  # 35% drop any time = day halt

# Credit rating
DEFAULT_CREDIT_RATING = 50
CREDIT_RATING_MIN = 0
CREDIT_RATING_MAX = 100

# Delisting
DELISTING_COOLDOWN_TICKS = 7200  # Must wait 7200 ticks before re-IPO

# ==========================
# ENUMS
# ==========================

class IPOType(str, Enum):
    # Direct-to-Market (4 types)
    DUTCH_AUCTION = "dutch_auction"
    PRIVATE_PLACEMENT = "private_placement"
    RIGHTS_OFFERING = "rights_offering"
    DIRECT_LISTING = "direct_listing"
    # Firm-Underwritten (6 types)
    STANDARD_UNDERWRITE = "standard_underwrite"
    BEST_EFFORTS = "best_efforts"
    BOUGHT_DEAL = "bought_deal"
    STABILIZED_OFFERING = "stabilized_offering"
    DRIP_RELEASE = "drip_release"
    SHELF_REGISTRATION = "shelf_registration"


class DividendType(str, Enum):
    CASH = "cash"  # % of profits or fixed per share
    COMMODITY = "commodity"  # Physical goods per share
    SCRIP = "scrip"  # More shares instead of cash
    PRODUCT_CREDIT = "product_credit"  # Discount at owner's businesses
    PRIORITY_ACCESS = "priority_access"  # First dibs on production
    LIQUIDATION_RIGHTS = "liquidation_rights"  # Pro-rata on dissolution
    CONVERTIBLE_CLAIM = "convertible_claim"  # Convert to commodities at date
    TIERED_BONUS = "tiered_bonus"  # Extra if holding X+ shares


class DividendFrequency(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


class ShareLoanStatus(str, Enum):
    ACTIVE = "active"
    RETURNED = "returned"
    DEFAULTED = "defaulted"
    FORCE_CLOSED = "force_closed"


class CommodityLoanStatus(str, Enum):
    ACTIVE = "active"
    RETURNED = "returned"
    LATE = "late"
    DEFAULTED = "defaulted"
    FORCE_CLOSED = "force_closed"


class CreditTier(str, Enum):
    PRIME = "prime"  # 90-100
    STANDARD = "standard"  # 70-89
    FAIR = "fair"  # 50-69
    SUBPRIME = "subprime"  # 30-49
    JUNK = "junk"  # 0-29


class LiquidationLevel(str, Enum):
    WARNING = "warning"
    FORCED_STOCK_SALE = "forced_stock_sale"
    FORCED_COMMODITY_CLOSE = "forced_commodity_close"
    COLLATERAL_SEIZURE = "collateral_seizure"
    LIEN_CREATION = "lien_creation"
    BANKRUPTCY = "bankruptcy"


# ==========================
# IPO CONFIGURATION
# ==========================

IPO_CONFIG = {
    # Direct-to-Market IPOs
    IPOType.DUTCH_AUCTION: {
        "name": "Dutch Auction",
        "description": "Players bid, highest bids win shares at clearing price",
        "firm_underwritten": False,
        "fee_type": "percentage",
        "fee_rate": 0.03,  # 3% of proceeds
        "requires_firm_funds": False,
    },
    IPOType.PRIVATE_PLACEMENT: {
        "name": "Private Placement",
        "description": "Sell shares to ONE specific player (negotiated deal)",
        "firm_underwritten": False,
        "fee_type": "percentage",
        "fee_rate": 0.01,  # 1% flat
        "requires_firm_funds": False,
    },
    IPOType.RIGHTS_OFFERING: {
        "name": "Rights Offering",
        "description": "Only existing shareholders can buy new shares at discount",
        "firm_underwritten": False,
        "fee_type": "percentage",
        "fee_rate": 0.02,  # 2% of proceeds
        "requires_firm_funds": False,
    },
    IPOType.DIRECT_LISTING: {
        "name": "Direct Listing",
        "description": "Founder's existing shares listed, no new shares created",
        "firm_underwritten": False,
        "fee_type": "flat",
        "fee_amount": 5000,  # $5,000 flat
        "requires_firm_funds": False,
    },
    # Firm-Underwritten IPOs
    IPOType.STANDARD_UNDERWRITE: {
        "name": "Standard Underwrite",
        "description": "Firm buys 100% of offered shares at 85% of valuation, resells at 100%+",
        "firm_underwritten": True,
        "discount_rate": 0.15,  # Buy at 85%
        "requires_firm_funds": True,
    },
    IPOType.BEST_EFFORTS: {
        "name": "Best Efforts",
        "description": "Firm tries to sell shares but returns unsold to founder",
        "firm_underwritten": True,
        "fee_type": "percentage",
        "fee_rate": 0.08,  # 8% of sold
        "requires_firm_funds": False,  # No upfront commitment
    },
    IPOType.BOUGHT_DEAL: {
        "name": "Bought Deal",
        "description": "Firm commits to buy ALL shares regardless of demand (premium for certainty)",
        "firm_underwritten": True,
        "discount_rate": 0.20,  # Buy at 80%
        "requires_firm_funds": True,
    },
    IPOType.STABILIZED_OFFERING: {
        "name": "Stabilized Offering",
        "description": "Firm buys shares AND commits to buy more if price drops >10% post-IPO",
        "firm_underwritten": True,
        "discount_rate": 0.12,  # Buy at 88%
        "stabilization_threshold": 0.10,  # 10% price drop triggers stabilization
        "requires_firm_funds": True,
    },
    IPOType.DRIP_RELEASE: {
        "name": "Drip Release",
        "description": "Firm buys large block, releases only 5% per week to create scarcity",
        "firm_underwritten": True,
        "discount_rate": 0.25,  # Buy at 75%
        "weekly_release_pct": 0.05,  # 5% per week
        "requires_firm_funds": True,
    },
    IPOType.SHELF_REGISTRATION: {
        "name": "Shelf Registration",
        "description": "Firm pre-approves large offering, founder draws down portions over time",
        "firm_underwritten": True,
        "fee_type": "percentage",
        "fee_rate": 0.10,  # 10% per tranche
        "max_tranches": 6,
        "tranche_window_ticks": 43200,  # 6 months (in ticks)
        "requires_firm_funds": False,  # On-demand funding
    },
}

# ==========================
# CREDIT RATING MODIFIERS
# ==========================

CREDIT_MODIFIERS = {
    "margin_trade_profitable": +2,
    "margin_trade_loss": -1,
    "margin_call_triggered": -10,
    "commodity_returned_on_time": +3,
    "commodity_returned_late": -5,
    "commodity_defaulted": -20,
    "dividend_paid": +1,
    "dividend_skipped_while_profitable": -3,
    "business_ipo_successful": +5,
    "lien_created": -15,
    "lien_paid_off": +10,
    "short_position_profitable": +2,
    "short_position_loss": -1,
    "short_default": -15,
    "company_went_private": -10,
}

CREDIT_TIERS = {
    CreditTier.PRIME: (90, 100, 0.01, 25.0),  # (min, max, interest_rate, max_leverage)
    CreditTier.STANDARD: (70, 89, 0.03, 15.0),
    CreditTier.FAIR: (50, 69, 0.06, 8.0),
    CreditTier.SUBPRIME: (30, 49, 0.10, 4.0),
    CreditTier.JUNK: (0, 29, 0.15, 2.0),
}

# ==========================
# DATABASE MODELS
# ==========================

class FirmEntity(Base):
    """The Brokerage Firm's state - singleton entity."""
    __tablename__ = "brokerage_firm_entity"
    
    id = Column(Integer, primary_key=True)
    cash_reserves = Column(Float, default=STARTING_CAPITAL)
    
    # Revenue tracking
    total_underwriting_fees_earned = Column(Float, default=0.0)
    total_trading_commissions_earned = Column(Float, default=0.0)
    total_margin_interest_earned = Column(Float, default=0.0)
    total_lending_fees_earned = Column(Float, default=0.0)
    total_dividends_received = Column(Float, default=0.0)
    total_late_fees_earned = Column(Float, default=0.0)
    total_spread_profit = Column(Float, default=0.0)
    
    # Loss tracking
    total_underwriting_losses = Column(Float, default=0.0)
    total_stabilization_costs = Column(Float, default=0.0)
    total_default_losses = Column(Float, default=0.0)
    
    # Obligations
    total_stabilization_commitments = Column(Float, default=0.0)
    
    # Operational state
    is_accepting_ipos = Column(Boolean, default=True)
    is_accepting_margin = Column(Boolean, default=True)
    is_accepting_lending = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PlayerCreditRating(Base):
    """Player credit score for the Firm."""
    __tablename__ = "player_credit_ratings"
    
    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, unique=True, index=True, nullable=False)
    
    credit_score = Column(Integer, default=DEFAULT_CREDIT_RATING)
    tier = Column(String, default=CreditTier.FAIR.value)
    
    # History
    total_margin_trades = Column(Integer, default=0)
    profitable_margin_trades = Column(Integer, default=0)
    total_commodity_loans = Column(Integer, default=0)
    on_time_returns = Column(Integer, default=0)
    total_dividends_paid = Column(Integer, default=0)
    total_dividends_skipped = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CompanyShares(Base):
    """Tracks all issued company shares for a business."""
    __tablename__ = "company_shares"
    
    id = Column(Integer, primary_key=True)
    business_id = Column(Integer, index=True, nullable=False)
    founder_id = Column(Integer, index=True, nullable=False)
    share_class = Column(String, default="A")  # A, B, Preferred, etc.
    
    # Company info
    company_name = Column(String, nullable=False)
    ticker_symbol = Column(String, unique=True, nullable=False)
    
    # Share structure
    total_shares_authorized = Column(Integer, nullable=False)
    shares_outstanding = Column(Integer, default=0)  # Actually issued
    shares_held_by_founder = Column(Integer, default=0)
    shares_held_by_firm = Column(Integer, default=0)
    shares_in_float = Column(Integer, default=0)  # Publicly tradeable
    
    # Pricing
    current_price = Column(Float, default=0.0)
    ipo_price = Column(Float, default=0.0)
    high_52_week = Column(Float, default=0.0)
    low_52_week = Column(Float, default=0.0)
    
    # Dividend configuration (JSON list)
    dividend_config = Column(JSON, default=list)
    # Example: [
    #   {"type": "cash", "amount": 0.30, "basis": "profit_pct", "frequency": "weekly"},
    #   {"type": "commodity", "item": "paper", "amount": 1, "per_shares": 100, "frequency": "monthly"}
    # ]
    
    # IPO details
    ipo_type = Column(String, nullable=True)
    ipo_date = Column(DateTime, nullable=True)
    
    # Drip release tracking (for DRIP_RELEASE IPO type)
    drip_shares_remaining = Column(Integer, default=0)
    drip_last_release = Column(DateTime, nullable=True)
    
    # Shelf registration tracking
    shelf_shares_remaining = Column(Integer, default=0)
    shelf_tranches_used = Column(Integer, default=0)
    shelf_expiry = Column(DateTime, nullable=True)
    
    # Stabilization tracking
    stabilization_active = Column(Boolean, default=False)
    stabilization_floor_price = Column(Float, nullable=True)
    stabilization_commitment_remaining = Column(Float, default=0.0)
    
    # Circuit breaker eligibility
    is_tbtf = Column(Boolean, default=False)
    trading_halted_until = Column(DateTime, nullable=True)
    consecutive_dividend_payouts = Column(Integer, default=0)
    
    # Delisting
    is_delisted = Column(Boolean, default=False)
    delisted_at = Column(DateTime, nullable=True)
    can_relist_after = Column(DateTime, nullable=True)
    
    # Warnings
    dividend_warning_active = Column(Boolean, default=False)
    last_dividend_warning = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class ShareholderPosition(Base):
    """Who owns what shares."""
    __tablename__ = "shareholder_positions"
    
    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, index=True, nullable=False)  # Can be -5 for Firm
    company_shares_id = Column(Integer, ForeignKey("company_shares.id"), index=True, nullable=False)
    
    shares_owned = Column(Integer, default=0)
    shares_available_to_lend = Column(Integer, default=0)  # For short selling
    shares_lent_out = Column(Integer, default=0)
    average_cost_basis = Column(Float, default=0.0)
    
    # Margin position tracking
    is_margin_position = Column(Boolean, default=False)
    margin_shares = Column(Integer, default=0)  # Shares bought on margin
    margin_debt = Column(Float, default=0.0)
    margin_multiplier_used = Column(Float, default=1.0)
    margin_interest_accrued = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ShareLoan(Base):
    """Tracks borrowed shares for short selling."""
    __tablename__ = "share_loans"
    
    id = Column(Integer, primary_key=True)
    lender_player_id = Column(Integer, index=True, nullable=False)
    borrower_player_id = Column(Integer, index=True, nullable=False)
    company_shares_id = Column(Integer, ForeignKey("company_shares.id"), nullable=False)
    
    shares_borrowed = Column(Integer, nullable=False)
    borrow_price = Column(Float, nullable=False)  # Price at time of borrow
    collateral_locked = Column(Float, nullable=False)  # 150% of value
    borrow_rate_weekly = Column(Float, nullable=False)  # Interest rate
    
    borrowed_at = Column(DateTime, default=datetime.utcnow)
    due_date = Column(DateTime, nullable=False)
    returned_at = Column(DateTime, nullable=True)
    
    # Fees paid
    total_fees_paid = Column(Float, default=0.0)
    fees_to_lender = Column(Float, default=0.0)
    fees_to_firm = Column(Float, default=0.0)
    
    status = Column(String, default=ShareLoanStatus.ACTIVE.value)


class CommodityListing(Base):
    """Player listing commodities available to lend."""
    __tablename__ = "commodity_listings"
    
    id = Column(Integer, primary_key=True)
    lender_player_id = Column(Integer, index=True, nullable=False)
    item_type = Column(String, index=True, nullable=False)
    
    quantity_available = Column(Float, nullable=False)
    quantity_lent_out = Column(Float, default=0.0)
    weekly_rate = Column(Float, nullable=False)  # Interest rate
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class CommodityLoan(Base):
    """Tracks borrowed commodities."""
    __tablename__ = "commodity_loans"
    
    id = Column(Integer, primary_key=True)
    listing_id = Column(Integer, ForeignKey("commodity_listings.id"), nullable=False)
    lender_player_id = Column(Integer, index=True, nullable=False)
    borrower_player_id = Column(Integer, index=True, nullable=False)
    
    item_type = Column(String, nullable=False)
    quantity_borrowed = Column(Float, nullable=False)
    borrow_price = Column(Float, nullable=False)  # Market price at borrow time
    collateral_locked = Column(Float, nullable=False)  # 105% of value
    weekly_rate = Column(Float, nullable=False)
    
    borrowed_at = Column(DateTime, default=datetime.utcnow)
    due_date = Column(DateTime, nullable=False)
    returned_at = Column(DateTime, nullable=True)
    
    # Fee tracking
    total_fees_paid = Column(Float, default=0.0)
    fees_to_lender = Column(Float, default=0.0)
    fees_to_firm = Column(Float, default=0.0)
    
    # Late fee tracking
    days_late = Column(Integer, default=0)
    late_fees_paid = Column(Float, default=0.0)
    
    # Extension tracking
    extensions_used = Column(Integer, default=0)
    max_extensions = Column(Integer, default=3)
    
    status = Column(String, default=CommodityLoanStatus.ACTIVE.value)


class DutchAuctionBid(Base):
    """Bids for Dutch Auction IPOs."""
    __tablename__ = "dutch_auction_bids"
    
    id = Column(Integer, primary_key=True)
    company_shares_id = Column(Integer, ForeignKey("company_shares.id"), nullable=False)
    bidder_player_id = Column(Integer, index=True, nullable=False)
    
    bid_price = Column(Float, nullable=False)
    bid_quantity = Column(Integer, nullable=False)
    
    is_winning = Column(Boolean, default=False)
    shares_awarded = Column(Integer, default=0)
    clearing_price = Column(Float, nullable=True)
    
    bid_at = Column(DateTime, default=datetime.utcnow)
    auction_end = Column(DateTime, nullable=False)
    settled = Column(Boolean, default=False)


class FirmTransaction(Base):
    """Transaction log for the Firm."""
    __tablename__ = "firm_transactions"
    
    id = Column(Integer, primary_key=True)
    transaction_type = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(String, nullable=True)
    
    # Related entities
    player_id = Column(Integer, nullable=True)
    company_shares_id = Column(Integer, nullable=True)
    loan_id = Column(Integer, nullable=True)
    
    timestamp = Column(DateTime, default=datetime.utcnow)


class PriceHistory(Base):
    """Track price history for volatility calculations."""
    __tablename__ = "price_history"
    
    id = Column(Integer, primary_key=True)
    company_shares_id = Column(Integer, ForeignKey("company_shares.id"), index=True, nullable=True)
    item_type = Column(String, index=True, nullable=True)  # For commodities
    
    price = Column(Float, nullable=False)
    volume = Column(Float, default=0.0)
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)


class MarginCall(Base):
    """Track margin call warnings and deadlines."""
    __tablename__ = "margin_calls"
    
    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, index=True, nullable=False)
    
    amount_required = Column(Float, nullable=False)
    deadline = Column(DateTime, nullable=False)
    
    is_resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime, nullable=True)
    resolution_type = Column(String, nullable=True)  # "deposited", "sold", "liquidated"
    
    created_at = Column(DateTime, default=datetime.utcnow)


class BrokerageLien(Base):
    """Liens created by the Firm for unpaid debts."""
    __tablename__ = "brokerage_liens"
    
    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, index=True, nullable=False)
    
    principal = Column(Float, default=0.0)
    interest_accrued = Column(Float, default=0.0)
    total_paid = Column(Float, default=0.0)
    
    source = Column(String, nullable=False)  # "margin", "commodity", "short"
    
    created_at = Column(DateTime, default=datetime.utcnow)
    last_interest_accrual = Column(DateTime, default=datetime.utcnow)
    last_payment = Column(DateTime, nullable=True)
    
    @property
    def total_owed(self):
        return self.principal + self.interest_accrued - self.total_paid


# ==========================
# HELPER FUNCTIONS
# ==========================

def get_db():
    """Get database session."""
    db = SessionLocal()
    return db


def get_firm_entity() -> FirmEntity:
    """Get or create the Firm entity."""
    db = get_db()
    try:
        firm = db.query(FirmEntity).first()
        if not firm:
            firm = FirmEntity(cash_reserves=STARTING_CAPITAL)
            db.add(firm)
            db.commit()
            db.refresh(firm)
        return firm
    finally:
        db.close()


def firm_add_cash(amount: float, transaction_type: str, description: str = None,
                  player_id: int = None, company_id: int = None, loan_id: int = None):
    """Add cash to the Firm and log transaction."""
    db = get_db()
    try:
        firm = db.query(FirmEntity).first()
        if firm:
            firm.cash_reserves += amount
            
            # Log transaction
            transaction = FirmTransaction(
                transaction_type=transaction_type,
                amount=amount,
                description=description,
                player_id=player_id,
                company_shares_id=company_id,
                loan_id=loan_id
            )
            db.add(transaction)
            db.commit()
            
            print(f"[{BANK_NAME}] +${amount:,.2f} ({transaction_type})")
    finally:
        db.close()


def firm_deduct_cash(amount: float, transaction_type: str, description: str = None) -> bool:
    """Deduct cash from the Firm. Returns False if insufficient funds."""
    db = get_db()
    try:
        firm = db.query(FirmEntity).first()
        if not firm or firm.cash_reserves < amount:
            return False
        
        # Check minimum reserve
        if firm.cash_reserves - amount < MINIMUM_OPERATING_RESERVE:
            print(f"[{BANK_NAME}] Cannot deduct ${amount:,.2f} - would breach minimum reserve")
            return False
        
        firm.cash_reserves -= amount
        
        transaction = FirmTransaction(
            transaction_type=transaction_type,
            amount=-amount,
            description=description
        )
        db.add(transaction)
        db.commit()
        
        print(f"[{BANK_NAME}] -${amount:,.2f} ({transaction_type})")
        return True
    finally:
        db.close()


def firm_is_solvent() -> bool:
    """Check if the Firm is solvent."""
    firm = get_firm_entity()
    
    # Calculate total assets
    db = get_db()
    try:
        # Cash
        cash = firm.cash_reserves
        
        # Value of share holdings
        holdings = db.query(ShareholderPosition).filter(
            ShareholderPosition.player_id == BANK_PLAYER_ID
        ).all()
        
        share_value = 0.0
        for holding in holdings:
            company = db.query(CompanyShares).filter(
                CompanyShares.id == holding.company_shares_id
            ).first()
            if company:
                share_value += holding.shares_owned * company.current_price
        
        # Outstanding margin loans (owed TO us)
        margin_loans = db.query(ShareholderPosition).filter(
            ShareholderPosition.margin_debt > 0
        ).all()
        margin_receivables = sum(p.margin_debt + p.margin_interest_accrued for p in margin_loans)
        
        # Locked collateral (held by us)
        commodity_loans = db.query(CommodityLoan).filter(
            CommodityLoan.status == CommodityLoanStatus.ACTIVE.value
        ).all()
        collateral_held = sum(l.collateral_locked for l in commodity_loans)
        
        total_assets = cash + share_value + margin_receivables + collateral_held
        
        # Calculate liabilities
        stabilization_commitments = firm.total_stabilization_commitments
        
        # Commodity return obligations (what we owe back to lenders)
        # Note: These are held by borrowers, not us, so this is our contingent liability
        
        total_liabilities = stabilization_commitments
        
        return total_assets > total_liabilities
    finally:
        db.close()


def check_firm_can_operate():
    """Check if Firm can accept new business. Updates operational flags if needed."""
    db = get_db()
    try:
        firm = db.query(FirmEntity).first()
        if not firm:
            return
        
        if not firm_is_solvent():
            firm.is_accepting_ipos = False
            firm.is_accepting_margin = False
            firm.is_accepting_lending = False
            db.commit()
            print(f"[{BANK_NAME}] ⚠️ FIRM INSOLVENT - Operations suspended")
        elif firm.cash_reserves < MINIMUM_OPERATING_RESERVE * 2:
            # Low on cash, be conservative
            firm.is_accepting_ipos = False
            firm.is_accepting_margin = True
            firm.is_accepting_lending = True
            db.commit()
            print(f"[{BANK_NAME}] ⚠️ Low reserves - IPO underwriting suspended")
        else:
            firm.is_accepting_ipos = True
            firm.is_accepting_margin = True
            firm.is_accepting_lending = True
            db.commit()
    finally:
        db.close()


# ==========================
# CREDIT RATING SYSTEM
# ==========================

def get_player_credit(player_id: int) -> PlayerCreditRating:
    """Get or create player credit rating."""
    db = get_db()
    try:
        rating = db.query(PlayerCreditRating).filter(
            PlayerCreditRating.player_id == player_id
        ).first()
        
        if not rating:
            rating = PlayerCreditRating(player_id=player_id)
            db.add(rating)
            db.commit()
            db.refresh(rating)
        
        return rating
    finally:
        db.close()


def modify_credit_score(player_id: int, event: str) -> int:
    """Modify a player's credit score based on an event."""
    if event not in CREDIT_MODIFIERS:
        return 0
    
    modifier = CREDIT_MODIFIERS[event]
    
    db = get_db()
    try:
        rating = db.query(PlayerCreditRating).filter(
            PlayerCreditRating.player_id == player_id
        ).first()
        
        if not rating:
            rating = PlayerCreditRating(player_id=player_id)
            db.add(rating)
        
        old_score = rating.credit_score
        rating.credit_score = max(CREDIT_RATING_MIN, 
                                  min(CREDIT_RATING_MAX, rating.credit_score + modifier))
        
        # Update tier
        rating.tier = get_credit_tier(rating.credit_score).value
        rating.last_updated = datetime.utcnow()
        
        db.commit()
        
        direction = "+" if modifier > 0 else ""
        print(f"[{BANK_NAME}] Credit: Player {player_id} {direction}{modifier} ({event}) → {rating.credit_score}")
        
        return rating.credit_score
    finally:
        db.close()


def get_credit_tier(score: int) -> CreditTier:
    """Get credit tier from score."""
    for tier, (min_score, max_score, _, _) in CREDIT_TIERS.items():
        if min_score <= score <= max_score:
            return tier
    return CreditTier.JUNK


def get_credit_interest_rate(player_id: int) -> float:
    """Get interest rate based on credit rating."""
    rating = get_player_credit(player_id)
    tier = get_credit_tier(rating.credit_score)
    
    for t, (_, _, interest_rate, _) in CREDIT_TIERS.items():
        if t == tier:
            return interest_rate
    
    return 0.15  # Default to junk rate


def get_max_leverage_for_player(player_id: int) -> float:
    """Get maximum leverage multiplier based on credit."""
    rating = get_player_credit(player_id)
    tier = get_credit_tier(rating.credit_score)
    
    for t, (_, _, _, max_leverage) in CREDIT_TIERS.items():
        if t == tier:
            return max_leverage
    
    return MIN_MARGIN_MULTIPLIER


# ==========================
# VOLATILITY CALCULATIONS
# ==========================

def calculate_stock_volatility(company_shares_id: int, days: int = 30) -> float:
    """Calculate price volatility for a stock over N days."""
    db = get_db()
    try:
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        prices = db.query(PriceHistory).filter(
            PriceHistory.company_shares_id == company_shares_id,
            PriceHistory.recorded_at >= cutoff
        ).order_by(PriceHistory.recorded_at.asc()).all()
        
        if len(prices) < 2:
            return 0.5  # Default to medium volatility
        
        # Calculate daily returns
        returns = []
        for i in range(1, len(prices)):
            if prices[i-1].price > 0:
                daily_return = (prices[i].price - prices[i-1].price) / prices[i-1].price
                returns.append(daily_return)
        
        if not returns:
            return 0.5
        
        # Standard deviation of returns
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        volatility = variance ** 0.5
        
        return volatility
    finally:
        db.close()


def calculate_commodity_volatility(item_type: str, days: int = 7) -> float:
    """Calculate price volatility for a commodity over N days."""
    db = get_db()
    try:
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        prices = db.query(PriceHistory).filter(
            PriceHistory.item_type == item_type,
            PriceHistory.recorded_at >= cutoff
        ).order_by(PriceHistory.recorded_at.asc()).all()
        
        if len(prices) < 2:
            return 0.15  # Default moderate
        
        returns = []
        for i in range(1, len(prices)):
            if prices[i-1].price > 0:
                daily_return = (prices[i].price - prices[i-1].price) / prices[i-1].price
                returns.append(daily_return)
        
        if not returns:
            return 0.15
        
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        volatility = variance ** 0.5
        
        return volatility
    finally:
        db.close()


def record_price(company_shares_id: int = None, item_type: str = None, price: float = 0.0, volume: float = 0.0):
    """Record a price point for volatility tracking."""
    db = get_db()
    try:
        record = PriceHistory(
            company_shares_id=company_shares_id,
            item_type=item_type,
            price=price,
            volume=volume
        )
        db.add(record)
        db.commit()
    finally:
        db.close()


# ==========================
# MARGIN MULTIPLIER CALCULATION
# ==========================

def calculate_margin_multiplier(buyer_id: int, company_shares_id: int, seller_id: int = None) -> float:
    """
    Calculate dynamic margin multiplier (2x - 25x).
    
    Factors:
    - Buyer credit rating and financial health
    - Stock volatility and dividend history
    - Seller reliability (if applicable)
    """
    base = MIN_MARGIN_MULTIPLIER
    
    # Get buyer info
    buyer_credit = get_player_credit(buyer_id)
    max_for_tier = get_max_leverage_for_player(buyer_id)
    
    # BUYER FACTORS (+0 to +10)
    buyer_score = 0
    
    if buyer_credit.credit_score > 80:
        buyer_score += 4
    elif buyer_credit.credit_score > 60:
        buyer_score += 2
    
    # Check buyer's cash position
    from auth import get_db as get_auth_db, Player
    auth_db = get_auth_db()
    try:
        buyer = auth_db.query(Player).filter(Player.id == buyer_id).first()
        if buyer:
            if buyer.cash_balance > 100000:
                buyer_score += 3
            elif buyer.cash_balance > 50000:
                buyer_score += 2
            elif buyer.cash_balance > 20000:
                buyer_score += 1
    finally:
        auth_db.close()
    
    # Check existing margin debt
    db = get_db()
    try:
        existing_margin = db.query(ShareholderPosition).filter(
            ShareholderPosition.player_id == buyer_id,
            ShareholderPosition.margin_debt > 0
        ).all()
        
        if not existing_margin:
            buyer_score += 3  # No existing margin debt
        elif sum(p.margin_debt for p in existing_margin) < 10000:
            buyer_score += 1
    finally:
        db.close()
    
    # STOCK FACTORS (+0 to +8)
    stock_score = 0
    
    volatility = calculate_stock_volatility(company_shares_id)
    if volatility < 0.05:
        stock_score += 4  # Very stable
    elif volatility < 0.15:
        stock_score += 2  # Moderate
    # High volatility = +0
    
    db = get_db()
    try:
        company = db.query(CompanyShares).filter(
            CompanyShares.id == company_shares_id
        ).first()
        
        if company:
            # Dividend track record
            if company.consecutive_dividend_payouts > 10:
                stock_score += 2
            elif company.consecutive_dividend_payouts > 5:
                stock_score += 1
            
            # Seasoned stock
            if company.ipo_date:
                days_public = (datetime.utcnow() - company.ipo_date).days
                if days_public > 90:
                    stock_score += 2
                elif days_public > 30:
                    stock_score += 1
            
            # Not under warning
            if not company.dividend_warning_active:
                stock_score += 1
    finally:
        db.close()
    
    # SELLER FACTORS (+0 to +5) - only if seller is known
    seller_score = 0
    if seller_id and seller_id > 0:
        seller_credit = get_player_credit(seller_id)
        if seller_credit.credit_score > 70:
            seller_score += 3
        elif seller_credit.credit_score > 50:
            seller_score += 1
        
        # Check seller's business count (diversification)
        from business import Business
        biz_db = get_db()
        try:
            biz_count = biz_db.query(Business).filter(
                Business.owner_id == seller_id
            ).count()
            if biz_count > 3:
                seller_score += 2
            elif biz_count > 1:
                seller_score += 1
        except:
            pass
        finally:
            biz_db.close()
    
    # Final calculation
    total_score = buyer_score + stock_score + seller_score
    multiplier = base + (total_score * 1.0)
    
    # Cap at tier maximum and absolute maximum
    multiplier = min(multiplier, max_for_tier, MAX_MARGIN_MULTIPLIER)
    multiplier = max(multiplier, MIN_MARGIN_MULTIPLIER)
    
    return round(multiplier, 1)


# ==========================
# COMMODITY LOAN DUE DATE CALCULATION
# ==========================

def calculate_commodity_due_date(item_type: str, borrower_id: int) -> datetime:
    """
    Calculate due date for commodity loan.
    
    Factors:
    - Commodity volatility (higher = shorter term)
    - Borrower credit (better = longer term)
    - Market supply (scarce = shorter term)
    """
    base_hours = 168  # 7 days default
    
    # VOLATILITY FACTOR
    volatility = calculate_commodity_volatility(item_type)
    
    if volatility > 0.30:  # Crisis-level
        base_hours = 24
    elif volatility > 0.15:  # High
        base_hours = 48
    elif volatility > 0.08:  # Moderate
        base_hours = 96
    # else: stable, keep 168
    
    # BORROWER TRUST BONUS
    borrower_credit = get_player_credit(borrower_id)
    
    if borrower_credit.credit_score > 85:
        base_hours *= 1.5  # Extra time for trusted borrowers
    elif borrower_credit.credit_score < 40:
        base_hours *= 0.5  # Short leash for risky borrowers
    
    # SUPPLY SCARCITY
    try:
        import inventory
        
        # Get total supply in all inventories
        inv_db = inventory.get_db()
        try:
            total_supply = 0
            all_items = inv_db.query(inventory.InventoryItem).filter(
                inventory.InventoryItem.item_type == item_type,
                inventory.InventoryItem.quantity > 0
            ).all()
            total_supply = sum(i.quantity for i in all_items)
        finally:
            inv_db.close()
        
        if total_supply < 1000:  # Rare commodity
            base_hours *= 0.7
    except:
        pass
    
    # Clamp to reasonable range (12 hours to 14 days)
    base_hours = max(12, min(336, base_hours))
    
    return datetime.utcnow() + timedelta(hours=base_hours)


# ==========================
# BUSINESS VALUATION
# ==========================

def calculate_business_valuation(business_id: int) -> dict:
    """
    Calculate the valuation of a business for IPO purposes.
    
    Returns:
        dict with book_value, earnings_value, total_valuation, etc.
    """
    from business import Business, BUSINESS_TYPES
    from land import LandPlot
    
    db = get_db()
    try:
        # This is a simplified version - would need full business module integration
        
        # Get business
        business = db.query(Business).filter(Business.id == business_id).first()
        if not business:
            return None
        
        # Book value = Land value + Building cost
        land_db = get_db()
        try:
            plot = land_db.query(LandPlot).filter(
                LandPlot.id == business.land_plot_id
            ).first()
            
            # Estimate land value from tax (rough proxy)
            land_value = plot.monthly_tax * 200 if plot else 10000
        finally:
            land_db.close()
        
        # Building cost
        config = BUSINESS_TYPES.get(business.business_type, {})
        building_cost = config.get("startup_cost", 5000)
        
        book_value = land_value + building_cost
        
        # Earnings value (would need profit tracking - estimate for now)
        # Using cycles_to_complete as proxy for productivity
        cycles = config.get("cycles_to_complete", 60)
        estimated_weekly_profit = building_cost * 0.02  # 2% of cost per week estimate
        
        earnings_multiple = 12  # 12x earnings
        earnings_value = estimated_weekly_profit * earnings_multiple
        
        total_valuation = book_value + earnings_value
        
        return {
            "book_value": book_value,
            "land_value": land_value,
            "building_cost": building_cost,
            "estimated_weekly_profit": estimated_weekly_profit,
            "earnings_multiple": earnings_multiple,
            "earnings_value": earnings_value,
            "total_valuation": total_valuation,
            "suggested_share_price": total_valuation / 10000,  # Assuming 10k shares
        }
    except Exception as e:
        print(f"[{BANK_NAME}] Valuation error: {e}")
        return None
    finally:
        db.close()


# ==========================
# IPO SYSTEM
# ==========================


# ==========================
# PLAYER HOLDING COMPANY VALUATION
# ==========================

def calculate_player_company_valuation(player_id: int) -> dict:
    """
    Calculate total valuation for a player's holding company.
    
    This represents the player's entire business empire, not individual businesses.
    
    Returns:
        dict with:
        - total_businesses: count of active businesses
        - total_book_value: sum of all land + building values
        - total_earnings_value: estimated based on business performance
        - total_valuation: book + earnings
        - businesses_breakdown: list of individual business values
        - suggested_ipo_shares: 10,000 - 1,000,000 based on size
        - suggested_share_price: valuation / shares
    """
    from business import Business, BUSINESS_TYPES
    from land import LandPlot, get_db as get_land_db
    
    db = get_db()
    try:
        # Get all active businesses owned by player
        businesses = db.query(Business).filter(
            Business.owner_id == player_id,
            Business.is_active == True
        ).all()
        
        if not businesses:
            return {
                "total_businesses": 0,
                "total_book_value": 0,
                "total_earnings_value": 0,
                "total_valuation": 0,
                "businesses_breakdown": [],
                "suggested_ipo_shares": 10000,
                "suggested_share_price": 0
            }
        
        total_book_value = 0
        total_earnings_value = 0
        businesses_breakdown = []
        
        land_db = get_land_db()
        try:
            for biz in businesses:
                # Get land value
                plot = land_db.query(LandPlot).filter(
                    LandPlot.id == biz.land_plot_id
                ).first()
                land_value = plot.monthly_tax * 200 if plot else 10000
                
                # Get building cost
                config = BUSINESS_TYPES.get(biz.business_type, {})
                building_cost = config.get("startup_cost", 5000)
                
                # Book value for this business
                biz_book_value = land_value + building_cost
                
                # Earnings estimate (simplified - would use actual profit tracking)
                cycles = config.get("cycles_to_complete", 60)
                est_weekly_profit = building_cost * 0.02
                earnings_multiple = 12
                biz_earnings_value = est_weekly_profit * earnings_multiple
                
                biz_total_value = biz_book_value + biz_earnings_value
                
                businesses_breakdown.append({
                    "business_id": biz.id,
                    "business_type": biz.business_type,
                    "business_name": config.get("name", biz.business_type),
                    "land_value": land_value,
                    "building_cost": building_cost,
                    "book_value": biz_book_value,
                    "earnings_value": biz_earnings_value,
                    "total_value": biz_total_value
                })
                
                total_book_value += biz_book_value
                total_earnings_value += biz_earnings_value
        
        finally:
            land_db.close()
        
        total_valuation = total_book_value + total_earnings_value
        
        # Suggest share count based on valuation
        if total_valuation < 50000:
            suggested_shares = 10000
        elif total_valuation < 500000:
            suggested_shares = 100000
        else:
            suggested_shares = 1000000
        
        suggested_price = total_valuation / suggested_shares if suggested_shares > 0 else 1.0
        
        return {
            "total_businesses": len(businesses),
            "total_book_value": total_book_value,
            "total_earnings_value": total_earnings_value,
            "total_valuation": total_valuation,
            "businesses_breakdown": businesses_breakdown,
            "suggested_ipo_shares": suggested_shares,
            "suggested_share_price": suggested_price
        }
    
    except Exception as e:
        print(f"[{BANK_NAME}] Player valuation error: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        db.close()


def create_player_ipo(
    founder_id: int,
    company_name: str,
    ticker_symbol: str,
    ipo_type: IPOType,
    shares_to_offer: int,
    total_shares: int,
    share_class: str,
    dividend_config: list = None
) -> Optional[CompanyShares]:
    """
    Create an IPO for a player's holding company.
    
    This IPO represents the player's entire business empire,
    not individual businesses.
    
    Args:
        founder_id: Player creating the IPO
        company_name: Name of the holding company (e.g., "Matt Co.")
        ticker_symbol: 3-5 character ticker (e.g., "MATT")
        ipo_type: Type of IPO offering
        shares_to_offer: How many shares to sell to public
        total_shares: Total authorized shares
        share_class: A, B, or Preferred
        dividend_config: Optional dividend setup
    
    Returns:
        CompanyShares object if successful
    """
    db = get_db()
    try:
        # Check if player already has a public company
        existing = db.query(CompanyShares).filter(
            CompanyShares.founder_id == founder_id,
            CompanyShares.is_delisted == False
        ).first()
        
        if existing:
            print(f"[{BANK_NAME}] Player {founder_id} already has public company: {existing.ticker_symbol}")
            return None
        
        # Check ticker uniqueness
        ticker_exists = db.query(CompanyShares).filter(
            CompanyShares.ticker_symbol == ticker_symbol.upper()
        ).first()
        
        if ticker_exists:
            print(f"[{BANK_NAME}] Ticker {ticker_symbol} already in use")
            return None
        
        # Get player's holding company valuation
        valuation = calculate_player_company_valuation(founder_id)
        
        if not valuation or valuation["total_businesses"] == 0:
            print(f"[{BANK_NAME}] Player {founder_id} has no businesses to IPO")
            return None
        
        # Calculate IPO pricing based on valuation
        suggested_price = valuation["suggested_share_price"]
        
        # Get IPO config
        ipo_config = IPO_CONFIG.get(ipo_type)
        if not ipo_config:
            return None
        
        # Calculate founder retention
        shares_to_founder = total_shares - shares_to_offer
        
        # Create the company listing
        company = CompanyShares(
            founder_id=founder_id,
            company_name=company_name,
            ticker_symbol=ticker_symbol.upper(),
            share_class=share_class,
            ipo_type=ipo_type.value,
            ipo_date=datetime.utcnow(),
            ipo_price=suggested_price,
            current_price=suggested_price,
            shares_outstanding=total_shares,
            total_shares_authorized=total_shares,
            shares_in_float=shares_to_offer,
            shares_held_by_founder=shares_to_founder,
            dividend_config=dividend_config,
            business_id=0,  # 0 = holding company
            high_52_week=suggested_price,
            low_52_week=suggested_price
        )
        
        db.add(company)
        db.commit()
        db.refresh(company)
        
        # Process IPO based on type
        if ipo_config['firm_underwritten']:
            # Firm buys the shares
            process_underwritten_ipo(company, shares_to_offer, ipo_config)
        else:
            # Direct to market
            process_direct_ipo(company, shares_to_offer, ipo_config)
        
        print(f"[{BANK_NAME}] IPO created: {ticker_symbol} for {company_name} ({valuation['total_businesses']} businesses)")
        
        return company
    
    except Exception as e:
        print(f"[{BANK_NAME}] IPO creation error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return None
# CORRECTED IPO PROCESSING FUNCTIONS
# Replace in brokerage_firm.py around line 1447

def process_underwritten_ipo(company: CompanyShares, shares: int, config: dict):
    """
    Process firm-underwritten IPO.
    
    The firm buys all shares from the founder at the IPO price,
    then gradually sells them to the market.
    """
    from brokerage_order_book import place_limit_order, OrderSide
    
    db = get_db()
    try:
        # Firm buys all shares from founder
        # Create position for firm
        firm_position = db.query(ShareholderPosition).filter(
            ShareholderPosition.player_id == BANK_PLAYER_ID,
            ShareholderPosition.company_shares_id == company.id
        ).first()
        
        if not firm_position:
            firm_position = ShareholderPosition(
                player_id=BANK_PLAYER_ID,
                company_shares_id=company.id,
                shares_owned=0,
                shares_available_to_lend=0,
                average_cost_basis=company.ipo_price
            )
            db.add(firm_position)
        
        # Firm takes possession of shares
        firm_position.shares_owned += shares
        firm_position.shares_available_to_lend += shares
        
        # Update company records
        company.shares_held_by_firm = shares
        
        # Pay founder for shares (firm buys at discount per config)
        discount_pct = config.get('firm_discount_pct', 0.15)
        payment_per_share = company.ipo_price * (1 - discount_pct)
        total_payment = payment_per_share * shares
        
        # Deduct from firm cash
        firm = get_firm_entity()
        firm.cash_reserves -= total_payment
        
        # Credit founder (need to access player account)
        from auth import Player, get_db as get_auth_db
        auth_db = get_auth_db()
        try:
            founder = auth_db.query(Player).filter(Player.id == company.founder_id).first()
            if founder:
                founder.cash_balance += total_payment
                auth_db.commit()
        finally:
            auth_db.close()
        
        db.commit()
        
        print(f"[{BANK_NAME}] Underwritten IPO: Firm bought {shares:,} shares of {company.ticker_symbol} for ${total_payment:,.2f}")
        
        # Place initial sell orders to start market making
        # Firm sells at IPO price + small markup
        initial_offering = min(shares // 10, 10000)  # Offer 10% or 10k shares initially
        if initial_offering > 0:
            place_limit_order(
                player_id=BANK_PLAYER_ID,
                company_shares_id=company.id,
                side=OrderSide.SELL,
                quantity=initial_offering,
                limit_price=company.ipo_price * 1.02  # 2% markup
            )
            print(f"[{BANK_NAME}] Placed initial sell order: {initial_offering:,} shares @ ${company.ipo_price * 1.02:.4f}")
        
    except Exception as e:
        print(f"[{BANK_NAME}] Error processing underwritten IPO: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


def process_direct_ipo(company: CompanyShares, shares: int, config: dict):
    """
    Process direct-to-market IPO.
    
    Shares are placed directly in the order book for public trading.
    Founder retains ownership initially and sells to market.
    """
    from brokerage_order_book import place_limit_order, OrderSide
    
    db = get_db()
    try:
        # Create founder's initial position with all shares
        founder_position = db.query(ShareholderPosition).filter(
            ShareholderPosition.player_id == company.founder_id,
            ShareholderPosition.company_shares_id == company.id
        ).first()
        
        if not founder_position:
            founder_position = ShareholderPosition(
                player_id=company.founder_id,
                company_shares_id=company.id,
                shares_owned=company.shares_held_by_founder,
                shares_available_to_lend=company.shares_held_by_founder,
                average_cost_basis=0.0  # Founder's shares have zero cost basis
            )
            db.add(founder_position)
        
        db.commit()
        
        # Place shares being offered as sell orders at IPO price
        # This makes them available for trading
        place_limit_order(
            player_id=company.founder_id,
            company_shares_id=company.id,
            side=OrderSide.SELL,
            quantity=shares,
            limit_price=company.ipo_price
        )
        
        print(f"[{BANK_NAME}] Direct IPO: Placed {shares:,} shares of {company.ticker_symbol} @ ${company.ipo_price:.4f}")
        
    except Exception as e:
        print(f"[{BANK_NAME}] Error processing direct IPO: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()
def create_ipo(
    founder_id: int,
    business_id: int,
    ipo_type: IPOType,
    shares_to_offer: int,
    total_shares: int,
    share_class: str,
    company_name: str,
    ticker_symbol: str,
    dividend_config: List[dict],
    target_player_id: int = None,  # For private placement
) -> Optional[CompanyShares]:
    """
    Create an IPO for a business.
    
    Returns:
        CompanyShares object if successful, None otherwise
    """
    config = IPO_CONFIG.get(ipo_type)
    if not config:
        print(f"[{BANK_NAME}] Unknown IPO type: {ipo_type}")
        return None
    
    # Validate business ownership
    from business import Business
    biz_db = get_db()
    try:
        business = biz_db.query(Business).filter(
            Business.id == business_id,
            Business.owner_id == founder_id
        ).first()
        
        if not business:
            print(f"[{BANK_NAME}] Business not found or not owned by founder")
            return None
    finally:
        biz_db.close()
    
    # Check if already public
    db = get_db()
    try:
        existing = db.query(CompanyShares).filter(
            CompanyShares.business_id == business_id,
            CompanyShares.is_delisted == False
        ).first()
        
        if existing:
            print(f"[{BANK_NAME}] Business already has public shares")
            return None
    finally:
        db.close()
    
    # Check delisting cooldown
    db = get_db()
    try:
        delisted = db.query(CompanyShares).filter(
            CompanyShares.business_id == business_id,
            CompanyShares.is_delisted == True
        ).first()
        
        if delisted and delisted.can_relist_after:
            if datetime.utcnow() < delisted.can_relist_after:
                print(f"[{BANK_NAME}] Business in IPO cooldown until {delisted.can_relist_after}")
                return None
    finally:
        db.close()
    
    # Check Firm can operate
    firm = get_firm_entity()
    if not firm.is_accepting_ipos:
        print(f"[{BANK_NAME}] Firm not accepting IPOs")
        return None
    
    # Get valuation
    valuation = calculate_business_valuation(business_id)
    if not valuation:
        print(f"[{BANK_NAME}] Could not value business")
        return None
    
    # Calculate offering value
    offering_pct = shares_to_offer / total_shares
    offering_value = valuation["total_valuation"] * offering_pct
    price_per_share = valuation["total_valuation"] / total_shares
    
    # Check if Firm-underwritten and can afford
    if config.get("requires_firm_funds"):
        discount_rate = config.get("discount_rate", 0.15)
        firm_cost = offering_value * (1 - discount_rate)
        
        if not firm_deduct_cash(firm_cost, "ipo_underwrite", 
                                f"Underwriting {ticker_symbol} IPO"):
            print(f"[{BANK_NAME}] Cannot afford to underwrite ${firm_cost:,.2f}")
            return None
        
        founder_receives = firm_cost
    else:
        founder_receives = 0  # Direct-to-market, founder gets paid when shares sell
    
    db = get_db()
    try:
        # Create company shares entry
        company_shares = CompanyShares(
            business_id=business_id,
            founder_id=founder_id,
            share_class=share_class,
            company_name=company_name,
            ticker_symbol=ticker_symbol,
            total_shares_authorized=total_shares,
            shares_outstanding=total_shares,
            shares_held_by_founder=total_shares - shares_to_offer,
            shares_held_by_firm=shares_to_offer if config.get("firm_underwritten") else 0,
            shares_in_float=0 if config.get("firm_underwritten") else shares_to_offer,
            current_price=price_per_share,
            ipo_price=price_per_share,
            high_52_week=price_per_share,
            low_52_week=price_per_share,
            dividend_config=dividend_config,
            ipo_type=ipo_type.value,
            ipo_date=datetime.utcnow(),
        )
        
        # Handle special IPO types
        if ipo_type == IPOType.DRIP_RELEASE:
            company_shares.drip_shares_remaining = shares_to_offer
            company_shares.drip_last_release = datetime.utcnow()
        
        elif ipo_type == IPOType.SHELF_REGISTRATION:
            company_shares.shelf_shares_remaining = shares_to_offer
            company_shares.shelf_tranches_used = 0
            company_shares.shelf_expiry = datetime.utcnow() + timedelta(
                seconds=config.get("tranche_window_ticks", 43200)
            )
        
        elif ipo_type == IPOType.STABILIZED_OFFERING:
            company_shares.stabilization_active = True
            company_shares.stabilization_floor_price = price_per_share * (1 - config.get("stabilization_threshold", 0.10))
            company_shares.stabilization_commitment_remaining = offering_value * 0.5  # Commit to buy up to 50% more
            
            # Update Firm's stabilization commitments
            firm_db = get_db()
            try:
                firm_entity = firm_db.query(FirmEntity).first()
                if firm_entity:
                    firm_entity.total_stabilization_commitments += company_shares.stabilization_commitment_remaining
                    firm_db.commit()
            finally:
                firm_db.close()
        
        db.add(company_shares)
        db.commit()
        db.refresh(company_shares)
        
        # Create founder's shareholder position
        founder_position = ShareholderPosition(
            player_id=founder_id,
            company_shares_id=company_shares.id,
            shares_owned=company_shares.shares_held_by_founder,
            average_cost_basis=0.0  # Founder's cost is 0
        )
        db.add(founder_position)
        
        # Create Firm's position if underwritten
        if config.get("firm_underwritten") and shares_to_offer > 0:
            firm_position = ShareholderPosition(
                player_id=BANK_PLAYER_ID,
                company_shares_id=company_shares.id,
                shares_owned=shares_to_offer,
                average_cost_basis=price_per_share * (1 - config.get("discount_rate", 0.15))
            )
            db.add(firm_position)
        
        db.commit()
        
        # Pay founder if underwritten
        if founder_receives > 0:
            from auth import get_db as get_auth_db, Player
            auth_db = get_auth_db()
            try:
                founder = auth_db.query(Player).filter(Player.id == founder_id).first()
                if founder:
                    founder.cash_balance += founder_receives
                    auth_db.commit()
                    print(f"[{BANK_NAME}] Paid founder ${founder_receives:,.2f} for IPO")
            finally:
                auth_db.close()
        
        # Calculate and collect fee for direct-to-market IPOs
        if not config.get("firm_underwritten"):
            if config.get("fee_type") == "flat":
                fee = config.get("fee_amount", 5000)
            else:
                fee = offering_value * config.get("fee_rate", 0.03)
            
            # Deduct fee from founder
            from auth import get_db as get_auth_db, Player
            auth_db = get_auth_db()
            try:
                founder = auth_db.query(Player).filter(Player.id == founder_id).first()
                if founder and founder.cash_balance >= fee:
                    founder.cash_balance -= fee
                    auth_db.commit()
                    firm_add_cash(fee, "ipo_fee", f"IPO fee for {ticker_symbol}", founder_id)
            finally:
                auth_db.close()
        
        # Update credit score
        modify_credit_score(founder_id, "business_ipo_successful")
        
        print(f"[{BANK_NAME}] 🎉 IPO COMPLETE: {ticker_symbol} ({ipo_type.value})")
        print(f"  → Shares: {shares_to_offer:,} @ ${price_per_share:.2f}")
        print(f"  → Valuation: ${valuation['total_valuation']:,.2f}")
        
        return company_shares
    
    except Exception as e:
        print(f"[{BANK_NAME}] IPO error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return None
    finally:
        db.close()


def check_delisting(company_shares_id: int) -> bool:
    """
    Check if a company should be delisted (founder reacquired 100% of shares).
    
    Returns True if delisted.
    """
    db = get_db()
    try:
        company = db.query(CompanyShares).filter(
            CompanyShares.id == company_shares_id
        ).first()
        
        if not company or company.is_delisted:
            return False
        
        # Check if founder owns all shares
        if company.shares_held_by_founder >= company.shares_outstanding:
            company.is_delisted = True
            company.delisted_at = datetime.utcnow()
            company.can_relist_after = datetime.utcnow() + timedelta(seconds=DELISTING_COOLDOWN_TICKS)
            
            db.commit()
            
            # Credit penalty
            modify_credit_score(company.founder_id, "company_went_private")
            
            print(f"[{BANK_NAME}] 📉 DELISTED: {company.ticker_symbol} - Founder reacquired 100%")
            print(f"  → Can re-IPO after {company.can_relist_after}")
            
            return True
        
        return False
    finally:
        db.close()


# ==========================
# SCPE: EQUITY TRADING
# ==========================

def player_place_buy_order(
    player_id: int,
    company_shares_id: int,
    quantity: int,
    limit_price: Optional[float] = None,
    use_margin: bool = False,
    margin_multiplier: float = 1.0
) -> Optional[OrderBook]:
    """
    Player places a buy order.
    
    Args:
        limit_price: If None, places market order. If specified, places limit order.
    """
    if limit_price is None:
        # Market order - execute immediately at best price
        success = place_market_order(
            player_id, company_shares_id, OrderSide.BUY, 
            quantity, use_margin, margin_multiplier
        )
        return "MARKET_ORDER_EXECUTED" if success else None
    else:
        # Limit order - place in order book
        return place_limit_order(
            player_id, company_shares_id, OrderSide.BUY,
            quantity, limit_price, use_margin, margin_multiplier
        )


def player_place_sell_order(
    player_id: int,
    company_shares_id: int,
    quantity: int,
    limit_price: Optional[float] = None
) -> Optional[OrderBook]:
    """
    Player places a sell order.
    
    Args:
        limit_price: If None, places market order. If specified, places limit order.
    """
    if limit_price is None:
        # Market order
        success = place_market_order(
            player_id, company_shares_id, OrderSide.SELL, quantity
        )
        return "MARKET_ORDER_EXECUTED" if success else None
    else:
        # Limit order
        return place_limit_order(
            player_id, company_shares_id, OrderSide.SELL,
            quantity, limit_price
        )

# ==========================
# SCPE: SHORT SELLING
# ==========================

def short_sell_shares(
    borrower_id: int,
    company_shares_id: int,
    quantity: int
) -> Optional[ShareLoan]:
    """
    Short sell shares by borrowing from lenders.
    
    Flow:
    1. Find lender with shares available
    2. Lock collateral (150%)
    3. Transfer shares to borrower
    4. Borrower sells immediately (or holds)
    
    Returns ShareLoan if successful.
    """
    db = get_db()
    try:
        company = db.query(CompanyShares).filter(
            CompanyShares.id == company_shares_id
        ).first()
        
        if not company or company.is_delisted:
            return None
        
        if company.trading_halted_until and datetime.utcnow() < company.trading_halted_until:
            print(f"[{BANK_NAME}] Trading halted")
            return None
        
        # Find a lender
        potential_lenders = db.query(ShareholderPosition).filter(
            ShareholderPosition.company_shares_id == company_shares_id,
            ShareholderPosition.shares_available_to_lend >= quantity,
            ShareholderPosition.player_id != borrower_id
        ).all()
        
        if not potential_lenders:
            print(f"[{BANK_NAME}] No shares available to borrow")
            return None
        
        # Pick first available lender
        lender_position = potential_lenders[0]
        
        # Calculate collateral
        borrow_value = quantity * company.current_price
        collateral_required = borrow_value * SHORT_COLLATERAL_REQUIREMENT
        
        # Get borrower's credit for rate
        borrower_credit = get_player_credit(borrower_id)
        weekly_rate = get_credit_interest_rate(borrower_id) / 52 * 2  # Double the normal rate for shorts
        
        # Calculate due date
        volatility = calculate_stock_volatility(company_shares_id)
        if volatility > 0.20:
            due_days = 3
        elif volatility > 0.10:
            due_days = 7
        else:
            due_days = 14
        
        # Adjust for credit
        if borrower_credit.credit_score > 80:
            due_days *= 1.5
        elif borrower_credit.credit_score < 40:
            due_days *= 0.5
        
        due_date = datetime.utcnow() + timedelta(days=max(1, due_days))
        
        # Lock collateral from borrower
        from auth import get_db as get_auth_db, Player
        auth_db = get_auth_db()
        try:
            borrower = auth_db.query(Player).filter(Player.id == borrower_id).first()
            if not borrower or borrower.cash_balance < collateral_required:
                print(f"[{BANK_NAME}] Insufficient collateral")
                return None
            
            borrower.cash_balance -= collateral_required
            auth_db.commit()
        finally:
            auth_db.close()
        
        # Update lender's position
        lender_position.shares_available_to_lend -= quantity
        lender_position.shares_lent_out += quantity
        
        # Create loan record
        loan = ShareLoan(
            lender_player_id=lender_position.player_id,
            borrower_player_id=borrower_id,
            company_shares_id=company_shares_id,
            shares_borrowed=quantity,
            borrow_price=company.current_price,
            collateral_locked=collateral_required,
            borrow_rate_weekly=weekly_rate,
            due_date=due_date
        )
        db.add(loan)
        db.commit()
        db.refresh(loan)
        
        print(f"[{BANK_NAME}] SHORT: {quantity} {company.ticker_symbol} borrowed")
        print(f"  → Collateral: ${collateral_required:,.2f}")
        print(f"  → Due: {due_date}")
        print(f"  → Weekly rate: {weekly_rate*100:.2f}%")
        
        return loan
    
    except Exception as e:
        print(f"[{BANK_NAME}] Short error: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        db.close()


def close_short_position(loan_id: int) -> bool:
    """
    Close a short position by returning borrowed shares.
    
    Returns True if successful.
    """
    db = get_db()
    try:
        loan = db.query(ShareLoan).filter(
            ShareLoan.id == loan_id,
            ShareLoan.status == ShareLoanStatus.ACTIVE.value
        ).first()
        
        if not loan:
            return False
        
        company = db.query(CompanyShares).filter(
            CompanyShares.id == loan.company_shares_id
        ).first()
        
        if not company:
            return False
        
        # Borrower needs to have/buy the shares to return
        borrower_position = db.query(ShareholderPosition).filter(
            ShareholderPosition.player_id == loan.borrower_player_id,
            ShareholderPosition.company_shares_id == loan.company_shares_id
        ).first()
        
        has_shares = borrower_position and borrower_position.shares_owned >= loan.shares_borrowed
        
        if not has_shares:
            # Must buy shares at current price
            buy_cost = loan.shares_borrowed * company.current_price
            
            from auth import get_db as get_auth_db, Player
            auth_db = get_auth_db()
            try:
                borrower = auth_db.query(Player).filter(Player.id == loan.borrower_player_id).first()
                
                # Can use collateral if short on cash
                available_cash = borrower.cash_balance + loan.collateral_locked
                
                if available_cash < buy_cost:
                    print(f"[{BANK_NAME}] Cannot afford to close short")
                    return False
                
                # Deduct from cash first, then collateral
                cash_used = min(borrower.cash_balance, buy_cost)
                borrower.cash_balance -= cash_used
                collateral_used = buy_cost - cash_used
                
                auth_db.commit()
            finally:
                auth_db.close()
            
            remaining_collateral = loan.collateral_locked - collateral_used
        else:
            # Has shares, just return them
            borrower_position.shares_owned -= loan.shares_borrowed
            remaining_collateral = loan.collateral_locked
            buy_cost = 0
        
        # Calculate profit/loss
        original_value = loan.shares_borrowed * loan.borrow_price
        close_value = loan.shares_borrowed * company.current_price
        pnl = original_value - close_value - loan.total_fees_paid
        
        # Return remaining collateral
        from auth import get_db as get_auth_db, Player
        auth_db = get_auth_db()
        try:
            borrower = auth_db.query(Player).filter(Player.id == loan.borrower_player_id).first()
            if borrower and remaining_collateral > 0:
                borrower.cash_balance += remaining_collateral
                auth_db.commit()
        finally:
            auth_db.close()
        
        # Update lender's position
        lender_position = db.query(ShareholderPosition).filter(
            ShareholderPosition.player_id == loan.lender_player_id,
            ShareholderPosition.company_shares_id == loan.company_shares_id
        ).first()
        
        if lender_position:
            lender_position.shares_lent_out -= loan.shares_borrowed
            lender_position.shares_available_to_lend += loan.shares_borrowed
        
        # Close loan
        loan.status = ShareLoanStatus.RETURNED.value
        loan.returned_at = datetime.utcnow()
        
        db.commit()
        
        # Update credit
        if pnl > 0:
            modify_credit_score(loan.borrower_player_id, "short_position_profitable")
        else:
            modify_credit_score(loan.borrower_player_id, "short_position_loss")
        
        print(f"[{BANK_NAME}] SHORT CLOSED: P/L ${pnl:,.2f}")
        
        return True
    
    except Exception as e:
        print(f"[{BANK_NAME}] Close short error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


# ==========================
# SCCE: COMMODITY LENDING
# ==========================

def list_commodity_for_lending(
    lender_id: int,
    item_type: str,
    quantity: float,
    weekly_rate: float
) -> Optional[CommodityListing]:
    """
    List commodities available for borrowing.
    """
    # Verify lender has the items
    try:
        import inventory
        available = inventory.get_item_quantity(lender_id, item_type)
        
        if available < quantity:
            print(f"[{BANK_NAME}] Insufficient inventory to list")
            return None
    except Exception as e:
        print(f"[{BANK_NAME}] Inventory check error: {e}")
        return None
    
    db = get_db()
    try:
        # Check for existing listing
        existing = db.query(CommodityListing).filter(
            CommodityListing.lender_player_id == lender_id,
            CommodityListing.item_type == item_type,
            CommodityListing.is_active == True
        ).first()
        
        if existing:
            existing.quantity_available += quantity
            existing.weekly_rate = weekly_rate
            db.commit()
            print(f"[{BANK_NAME}] Updated listing: {quantity} more {item_type}")
            return existing
        
        listing = CommodityListing(
            lender_player_id=lender_id,
            item_type=item_type,
            quantity_available=quantity,
            weekly_rate=weekly_rate
        )
        db.add(listing)
        db.commit()
        db.refresh(listing)
        
        print(f"[{BANK_NAME}] Listed {quantity} {item_type} @ {weekly_rate*100:.1f}%/week")
        
        return listing
    finally:
        db.close()


def borrow_commodity(
    borrower_id: int,
    listing_id: int,
    quantity: float
) -> Optional[CommodityLoan]:
    """
    Borrow commodities from a lender.
    
    Flow:
    1. Lock 105% collateral
    2. Transfer items from lender to borrower
    3. Calculate due date based on volatility and credit
    """
    db = get_db()
    try:
        listing = db.query(CommodityListing).filter(
            CommodityListing.id == listing_id,
            CommodityListing.is_active == True
        ).first()
        
        if not listing:
            print(f"[{BANK_NAME}] Listing not found")
            return None
        
        if listing.quantity_available - listing.quantity_lent_out < quantity:
            print(f"[{BANK_NAME}] Insufficient quantity available")
            return None
        
        # Can't borrow from yourself
        if listing.lender_player_id == borrower_id:
            print(f"[{BANK_NAME}] Cannot borrow from yourself")
            return None
        
        # Check Firm is accepting
        firm = get_firm_entity()
        if not firm.is_accepting_lending:
            print(f"[{BANK_NAME}] Commodity lending suspended")
            return None
        
        # Get market price
        import market as market_mod
        market_price = market_mod.get_market_price(listing.item_type) or 1.0
        
        # Calculate collateral (105%)
        borrow_value = quantity * market_price
        collateral_required = borrow_value * COLLATERAL_REQUIREMENT
        
        # Calculate due date
        due_date = calculate_commodity_due_date(listing.item_type, borrower_id)
        
        # Calculate fee
        weeks = (due_date - datetime.utcnow()).days / 7
        total_fee = borrow_value * listing.weekly_rate * max(1, weeks)
        fee_to_lender = total_fee * (1 - LENDING_FEE_SPLIT)
        fee_to_firm = total_fee * LENDING_FEE_SPLIT
        
        # Lock collateral + fee from borrower
        from auth import get_db as get_auth_db, Player
        auth_db = get_auth_db()
        try:
            borrower = auth_db.query(Player).filter(Player.id == borrower_id).first()
            if not borrower or borrower.cash_balance < collateral_required + total_fee:
                print(f"[{BANK_NAME}] Insufficient funds for collateral + fee")
                return None
            
            borrower.cash_balance -= (collateral_required + total_fee)
            auth_db.commit()
        finally:
            auth_db.close()
        
        # Transfer items from lender to borrower
        try:
            import inventory
            
            # Remove from lender
            if not inventory.remove_item(listing.lender_player_id, listing.item_type, quantity):
                # Refund borrower
                auth_db = get_auth_db()
                try:
                    borrower = auth_db.query(Player).filter(Player.id == borrower_id).first()
                    if borrower:
                        borrower.cash_balance += collateral_required + total_fee
                        auth_db.commit()
                finally:
                    auth_db.close()
                print(f"[{BANK_NAME}] Lender doesn't have items")
                return None
            
            # Add to borrower
            inventory.add_item(borrower_id, listing.item_type, quantity)
        except Exception as e:
            print(f"[{BANK_NAME}] Item transfer error: {e}")
            return None
        
        # Pay fee to lender
        auth_db = get_auth_db()
        try:
            lender = auth_db.query(Player).filter(Player.id == listing.lender_player_id).first()
            if lender:
                lender.cash_balance += fee_to_lender
                auth_db.commit()
        finally:
            auth_db.close()
        
        # Firm keeps its cut
        firm_add_cash(fee_to_firm, "lending_fee", 
                     f"Lending fee for {listing.item_type}", borrower_id)
        
        # Update listing
        listing.quantity_lent_out += quantity
        
        # Create loan record
        loan = CommodityLoan(
            listing_id=listing_id,
            lender_player_id=listing.lender_player_id,
            borrower_player_id=borrower_id,
            item_type=listing.item_type,
            quantity_borrowed=quantity,
            borrow_price=market_price,
            collateral_locked=collateral_required,
            weekly_rate=listing.weekly_rate,
            due_date=due_date,
            total_fees_paid=total_fee,
            fees_to_lender=fee_to_lender,
            fees_to_firm=fee_to_firm
        )
        db.add(loan)
        db.commit()
        db.refresh(loan)
        
        print(f"[{BANK_NAME}] BORROWED: {quantity} {listing.item_type}")
        print(f"  → Collateral: ${collateral_required:,.2f}")
        print(f"  → Fee: ${total_fee:,.2f} (Lender: ${fee_to_lender:.2f}, Firm: ${fee_to_firm:.2f})")
        print(f"  → Due: {due_date}")
        
        return loan
    
    except Exception as e:
        print(f"[{BANK_NAME}] Borrow error: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        db.close()


def return_commodity(loan_id: int) -> bool:
    """
    Return borrowed commodities.
    
    Returns True if successful.
    """
    db = get_db()
    try:
        loan = db.query(CommodityLoan).filter(
            CommodityLoan.id == loan_id,
            CommodityLoan.status.in_([CommodityLoanStatus.ACTIVE.value, CommodityLoanStatus.LATE.value])
        ).first()
        
        if not loan:
            return False
        
        # Check borrower has items
        try:
            import inventory
            available = inventory.get_item_quantity(loan.borrower_player_id, loan.item_type)
            
            if available < loan.quantity_borrowed:
                print(f"[{BANK_NAME}] Borrower doesn't have items to return")
                return False
        except:
            return False
        
        # Transfer items back
        try:
            import inventory
            
            inventory.remove_item(loan.borrower_player_id, loan.item_type, loan.quantity_borrowed)
            inventory.add_item(loan.lender_player_id, loan.item_type, loan.quantity_borrowed)
        except Exception as e:
            print(f"[{BANK_NAME}] Return transfer error: {e}")
            return False
        
        # Return collateral
        from auth import get_db as get_auth_db, Player
        auth_db = get_auth_db()
        try:
            borrower = auth_db.query(Player).filter(Player.id == loan.borrower_player_id).first()
            if borrower:
                borrower.cash_balance += loan.collateral_locked
                auth_db.commit()
        finally:
            auth_db.close()
        
        # Update listing
        listing = db.query(CommodityListing).filter(
            CommodityListing.id == loan.listing_id
        ).first()
        if listing:
            listing.quantity_lent_out -= loan.quantity_borrowed
        
        # Close loan
        loan.status = CommodityLoanStatus.RETURNED.value
        loan.returned_at = datetime.utcnow()
        
        db.commit()
        
        # Update credit
        if loan.days_late > 0:
            modify_credit_score(loan.borrower_player_id, "commodity_returned_late")
        else:
            modify_credit_score(loan.borrower_player_id, "commodity_returned_on_time")
        
        print(f"[{BANK_NAME}] RETURNED: {loan.quantity_borrowed} {loan.item_type}")
        
        return True
    
    except Exception as e:
        print(f"[{BANK_NAME}] Return error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def extend_commodity_loan(loan_id: int) -> bool:
    """
    Extend a commodity loan due date (pay additional fee).
    """
    db = get_db()
    try:
        loan = db.query(CommodityLoan).filter(
            CommodityLoan.id == loan_id,
            CommodityLoan.status == CommodityLoanStatus.ACTIVE.value
        ).first()
        
        if not loan:
            return False
        
        if loan.extensions_used >= loan.max_extensions:
            print(f"[{BANK_NAME}] Max extensions reached")
            return False
        
        # Check collateral still covers at current prices
        import market as market_mod
        current_price = market_mod.get_market_price(loan.item_type) or loan.borrow_price
        current_value = loan.quantity_borrowed * current_price
        
        if loan.collateral_locked < current_value * COLLATERAL_REQUIREMENT:
            print(f"[{BANK_NAME}] Must top up collateral to extend")
            return False
        
        # Calculate extension fee (1.5x normal rate)
        extension_fee = current_value * loan.weekly_rate * 1.5
        fee_to_lender = extension_fee * (1 - LENDING_FEE_SPLIT)
        fee_to_firm = extension_fee * LENDING_FEE_SPLIT
        
        # Charge borrower
        from auth import get_db as get_auth_db, Player
        auth_db = get_auth_db()
        try:
            borrower = auth_db.query(Player).filter(Player.id == loan.borrower_player_id).first()
            if not borrower or borrower.cash_balance < extension_fee:
                print(f"[{BANK_NAME}] Cannot afford extension")
                return False
            
            borrower.cash_balance -= extension_fee
            auth_db.commit()
        finally:
            auth_db.close()
        
        # Pay lender
        auth_db = get_auth_db()
        try:
            lender = auth_db.query(Player).filter(Player.id == loan.lender_player_id).first()
            if lender:
                lender.cash_balance += fee_to_lender
                auth_db.commit()
        finally:
            auth_db.close()
        
        # Firm's cut
        firm_add_cash(fee_to_firm, "extension_fee", 
                     f"Loan extension for {loan.item_type}", loan.borrower_player_id)
        
        # Extend due date
        new_due = calculate_commodity_due_date(loan.item_type, loan.borrower_player_id)
        loan.due_date = new_due
        loan.extensions_used += 1
        loan.total_fees_paid += extension_fee
        loan.fees_to_lender += fee_to_lender
        loan.fees_to_firm += fee_to_firm
        
        db.commit()
        
        print(f"[{BANK_NAME}] EXTENDED: Loan #{loan_id} to {new_due}")
        
        return True
    
    except Exception as e:
        print(f"[{BANK_NAME}] Extension error: {e}")
        return False
    finally:
        db.close()


# ==========================
# DIVIDEND PROCESSING
# ==========================

def process_dividends(current_tick: int):
    """Process all due dividends for public companies."""
    db = get_db()
    try:
        companies = db.query(CompanyShares).filter(
            CompanyShares.is_delisted == False
        ).all()
        
        for company in companies:
            if not company.dividend_config:
                continue
            
            for div_config in company.dividend_config:
                div_type = div_config.get("type")
                frequency = div_config.get("frequency", "weekly")
                
                # Check if due (simplified - would need proper scheduling)
                freq_ticks = {
                    "daily": 86400,
                    "weekly": 604800,
                    "biweekly": 1209600,
                    "monthly": 2592000,
                    "quarterly": 7776000
                }.get(frequency, 604800)
                
                if current_tick % freq_ticks != 0:
                    continue
                
                # Get all shareholders
                positions = db.query(ShareholderPosition).filter(
                    ShareholderPosition.company_shares_id == company.id,
                    ShareholderPosition.shares_owned > 0
                ).all()
                
                if div_type == "cash":
                    process_cash_dividend(company, div_config, positions)
                elif div_type == "commodity":
                    process_commodity_dividend(company, div_config, positions)
                elif div_type == "scrip":
                    process_scrip_dividend(company, div_config, positions)
                # ... other dividend types
        
        db.commit()
    finally:
        db.close()


def process_cash_dividend(company: CompanyShares, config: dict, positions: List[ShareholderPosition]):
    """Process cash dividends."""
    from auth import get_db as get_auth_db, Player
    from business import Business
    
    amount = config.get("amount", 0)
    basis = config.get("basis", "fixed")  # "fixed" or "profit_pct"
    
    if basis == "profit_pct":
        # Would need profit tracking - simplified
        estimated_profit = 1000  # Placeholder
        total_dividend_pool = estimated_profit * amount
    else:
        total_dividend_pool = amount * company.shares_outstanding
    
    # Get founder's cash
    auth_db = get_auth_db()
    try:
        founder = auth_db.query(Player).filter(Player.id == company.founder_id).first()
        
        if not founder or founder.cash_balance < total_dividend_pool:
            # Can't pay dividend
            company.dividend_warning_active = True
            company.last_dividend_warning = datetime.utcnow()
            company.consecutive_dividend_payouts = 0
            
            modify_credit_score(company.founder_id, "dividend_skipped_while_profitable")
            
            print(f"[{BANK_NAME}] ⚠️ {company.ticker_symbol}: Dividend SKIPPED - Insufficient funds")
            return
        
        # Deduct from founder
        founder.cash_balance -= total_dividend_pool
        auth_db.commit()
    finally:
        auth_db.close()
    
    # Distribute to shareholders
    per_share = total_dividend_pool / company.shares_outstanding if company.shares_outstanding > 0 else 0
    
    for position in positions:
        dividend_amount = position.shares_owned * per_share
        
        if dividend_amount < 0.01:
            continue
        
        auth_db = get_auth_db()
        try:
            player = auth_db.query(Player).filter(Player.id == position.player_id).first()
            if player:
                player.cash_balance += dividend_amount
                auth_db.commit()
                
                # If Firm, track it
                if position.player_id == BANK_PLAYER_ID:
                    firm_db = get_db()
                    try:
                        firm = firm_db.query(FirmEntity).first()
                        if firm:
                            firm.total_dividends_received += dividend_amount
                            firm_db.commit()
                    finally:
                        firm_db.close()
        finally:
            auth_db.close()
    
    # Update company
    company.dividend_warning_active = False
    company.consecutive_dividend_payouts += 1
    
    modify_credit_score(company.founder_id, "dividend_paid")
    
    print(f"[{BANK_NAME}] 💰 {company.ticker_symbol}: Paid ${total_dividend_pool:,.2f} dividend")


def process_commodity_dividend(company: CompanyShares, config: dict, positions: List[ShareholderPosition]):
    """Process commodity dividends."""
    import inventory
    
    item = config.get("item")
    amount = config.get("amount", 1)
    per_shares = config.get("per_shares", 100)
    
    for position in positions:
        units = (position.shares_owned // per_shares) * amount
        
        if units < 1:
            continue
        
        # Check founder has inventory
        founder_qty = inventory.get_item_quantity(company.founder_id, item)
        
        if founder_qty < units:
            company.dividend_warning_active = True
            print(f"[{BANK_NAME}] ⚠️ {company.ticker_symbol}: Commodity dividend skipped - No inventory")
            return
        
        # Transfer
        inventory.remove_item(company.founder_id, item, units)
        inventory.add_item(position.player_id, item, units)
    
    company.dividend_warning_active = False
    company.consecutive_dividend_payouts += 1
    
    print(f"[{BANK_NAME}] 📦 {company.ticker_symbol}: Paid {item} dividend")


def process_scrip_dividend(company: CompanyShares, config: dict, positions: List[ShareholderPosition]):
    """Process scrip (stock) dividends."""
    db = get_db()
    try:
        rate = config.get("rate", 0.05)  # 5% more shares
        
        for position in positions:
            new_shares = int(position.shares_owned * rate)
            
            if new_shares < 1:
                continue
            
            position.shares_owned += new_shares
            company.shares_outstanding += new_shares
            company.total_shares_authorized += new_shares
        
        db.commit()
        
        company.consecutive_dividend_payouts += 1
        
        print(f"[{BANK_NAME}] 📈 {company.ticker_symbol}: Paid {rate*100:.1f}% scrip dividend")
    finally:
        db.close()


# ==========================
# CIRCUIT BREAKERS (TBTF)
# ==========================

def check_tbtf_eligibility(company_shares_id: int) -> bool:
    """Check if a company qualifies for Too Big To Fail protections."""
    db = get_db()
    try:
        company = db.query(CompanyShares).filter(
            CompanyShares.id == company_shares_id
        ).first()
        
        if not company:
            return False
        
        # Market cap
        market_cap = company.current_price * company.shares_outstanding
        if market_cap < TBTF_MIN_MARKET_CAP:
            return False
        
        # Shareholder count
        shareholder_count = db.query(ShareholderPosition).filter(
            ShareholderPosition.company_shares_id == company_shares_id,
            ShareholderPosition.shares_owned > 0
        ).count()
        if shareholder_count < TBTF_MIN_SHAREHOLDERS:
            return False
        
        # Days public
        if company.ipo_date:
            days_public = (datetime.utcnow() - company.ipo_date).days
            if days_public < TBTF_MIN_DAYS_PUBLIC:
                return False
        else:
            return False
        
        # Dividend streak
        if company.consecutive_dividend_payouts < TBTF_MIN_DIVIDEND_STREAK:
            return False
        
        # Founder credit
        founder_credit = get_player_credit(company.founder_id)
        if founder_credit.credit_score < TBTF_MIN_FOUNDER_CREDIT:
            return False
        
        return True
    finally:
        db.close()


def check_circuit_breakers(company_shares_id: int, new_price: float):
    """Check and trigger circuit breakers if needed."""
    db = get_db()
    try:
        company = db.query(CompanyShares).filter(
            CompanyShares.id == company_shares_id
        ).first()
        
        if not company or not company.is_tbtf:
            return
        
        if company.trading_halted_until and datetime.utcnow() < company.trading_halted_until:
            return  # Already halted
        
        # Get price from 60 minutes ago
        cutoff = datetime.utcnow() - timedelta(minutes=60)
        old_price_record = db.query(PriceHistory).filter(
            PriceHistory.company_shares_id == company_shares_id,
            PriceHistory.recorded_at <= cutoff
        ).order_by(PriceHistory.recorded_at.desc()).first()
        
        if not old_price_record or old_price_record.price == 0:
            return
        
        price_change_pct = (new_price - old_price_record.price) / old_price_record.price
        
        # Check circuit breaker levels
        halt_minutes = 0
        level = None
        
        if price_change_pct <= CIRCUIT_BREAKER_LEVEL_3[0]:
            halt_minutes = CIRCUIT_BREAKER_LEVEL_3[2]
            level = 3
        elif price_change_pct <= CIRCUIT_BREAKER_LEVEL_2[0]:
            halt_minutes = CIRCUIT_BREAKER_LEVEL_2[2]
            level = 2
        elif price_change_pct <= CIRCUIT_BREAKER_LEVEL_1[0]:
            halt_minutes = CIRCUIT_BREAKER_LEVEL_1[2]
            level = 1
        
        if halt_minutes > 0:
            company.trading_halted_until = datetime.utcnow() + timedelta(minutes=halt_minutes)
            db.commit()
            
            print(f"[{BANK_NAME}] 🛑 CIRCUIT BREAKER L{level}: {company.ticker_symbol} HALTED for {halt_minutes} minutes")
            print(f"  → Price change: {price_change_pct*100:.1f}%")
    finally:
        db.close()


def update_tbtf_status():
    """Update TBTF status for all companies."""
    db = get_db()
    try:
        companies = db.query(CompanyShares).filter(
            CompanyShares.is_delisted == False
        ).all()
        
        for company in companies:
            old_status = company.is_tbtf
            company.is_tbtf = check_tbtf_eligibility(company.id)
            
            if company.is_tbtf and not old_status:
                print(f"[{BANK_NAME}] 🛡️ {company.ticker_symbol} now qualifies for TBTF protection")
            elif not company.is_tbtf and old_status:
                print(f"[{BANK_NAME}] {company.ticker_symbol} lost TBTF status")
        
        db.commit()
    finally:
        db.close()


# ==========================
# RISK ENGINE: LIQUIDATION
# ==========================

def check_margin_calls():
    """Check all margin positions for maintenance requirements."""
    db = get_db()
    try:
        margin_positions = db.query(ShareholderPosition).filter(
            ShareholderPosition.margin_debt > 0
        ).all()
        
        for position in margin_positions:
            company = db.query(CompanyShares).filter(
                CompanyShares.id == position.company_shares_id
            ).first()
            
            if not company:
                continue
            
            # Calculate position value
            position_value = position.shares_owned * company.current_price
            
            # Maintenance requirement
            maintenance_required = position.margin_debt * (1 + MARGIN_MAINTENANCE_RATIO)
            
            if position_value < maintenance_required:
                # Margin call!
                shortfall = maintenance_required - position_value
                
                # Check for existing margin call
                existing_call = db.query(MarginCall).filter(
                    MarginCall.player_id == position.player_id,
                    MarginCall.is_resolved == False
                ).first()
                
                if not existing_call:
                    call = MarginCall(
                        player_id=position.player_id,
                        amount_required=shortfall,
                        deadline=datetime.utcnow() + timedelta(hours=1)
                    )
                    db.add(call)
                    
                    print(f"[{BANK_NAME}] 📞 MARGIN CALL: Player {position.player_id} needs ${shortfall:,.2f}")
                    
                    modify_credit_score(position.player_id, "margin_call_triggered")
        
        db.commit()
    finally:
        db.close()


def process_margin_call_deadlines():
    """Process expired margin calls - trigger liquidation."""
    db = get_db()
    try:
        expired_calls = db.query(MarginCall).filter(
            MarginCall.is_resolved == False,
            MarginCall.deadline < datetime.utcnow()
        ).all()
        
        for call in expired_calls:
            print(f"[{BANK_NAME}] ⚠️ MARGIN CALL EXPIRED: Player {call.player_id}")
            
            # Start liquidation cascade
            trigger_liquidation(call.player_id, "margin")
            
            call.is_resolved = True
            call.resolved_at = datetime.utcnow()
            call.resolution_type = "liquidated"
        
        db.commit()
    finally:
        db.close()


def check_commodity_loan_due_dates():
    """Check for overdue commodity loans."""
    db = get_db()
    try:
        overdue_loans = db.query(CommodityLoan).filter(
            CommodityLoan.status == CommodityLoanStatus.ACTIVE.value,
            CommodityLoan.due_date < datetime.utcnow()
        ).all()
        
        for loan in overdue_loans:
            loan.status = CommodityLoanStatus.LATE.value
            loan.days_late += 1
            
            # Calculate late fee
            late_fee = loan.collateral_locked * LATE_FEE_DAILY_RATE
            fee_to_lender = late_fee * (1 - LATE_FEE_SPLIT)
            fee_to_firm = late_fee * LATE_FEE_SPLIT
            
            # Deduct from collateral
            if loan.collateral_locked >= late_fee:
                loan.collateral_locked -= late_fee
                loan.late_fees_paid += late_fee
                
                # Pay lender
                from auth import get_db as get_auth_db, Player
                auth_db = get_auth_db()
                try:
                    lender = auth_db.query(Player).filter(Player.id == loan.lender_player_id).first()
                    if lender:
                        lender.cash_balance += fee_to_lender
                        auth_db.commit()
                finally:
                    auth_db.close()
                
                firm_add_cash(fee_to_firm, "late_fee", 
                             f"Late fee for {loan.item_type}", loan.borrower_player_id)
                
                print(f"[{BANK_NAME}] ⏰ LATE: Loan #{loan.id} - Day {loan.days_late} fee ${late_fee:.2f}")
            
            # Force close after max late days
            if loan.days_late >= MAX_LATE_DAYS_BEFORE_FORCE_CLOSE:
                force_close_commodity_loan(loan.id)
        
        db.commit()
    finally:
        db.close()


def force_close_commodity_loan(loan_id: int):
    """Force close a commodity loan - buy items at market to return."""
    db = get_db()
    try:
        loan = db.query(CommodityLoan).filter(
            CommodityLoan.id == loan_id
        ).first()
        
        if not loan:
            return
        
        # Get current market price
        import market as market_mod
        current_price = market_mod.get_market_price(loan.item_type) or loan.borrow_price * 1.5
        
        buy_cost = loan.quantity_borrowed * current_price
        
        # Use collateral to buy
        if loan.collateral_locked >= buy_cost:
            # Can cover - buy and return
            remaining = loan.collateral_locked - buy_cost
            
            # Return items to lender
            import inventory
            inventory.add_item(loan.lender_player_id, loan.item_type, loan.quantity_borrowed)
            
            # Return remaining collateral to borrower
            if remaining > 0:
                from auth import get_db as get_auth_db, Player
                auth_db = get_auth_db()
                try:
                    borrower = auth_db.query(Player).filter(Player.id == loan.borrower_player_id).first()
                    if borrower:
                        borrower.cash_balance += remaining
                        auth_db.commit()
                finally:
                    auth_db.close()
            
            loan.status = CommodityLoanStatus.FORCE_CLOSED.value
            print(f"[{BANK_NAME}] 🔨 FORCE CLOSED: Loan #{loan_id}")
        else:
            # Collateral insufficient - create lien for difference
            shortfall = buy_cost - loan.collateral_locked
            
            # Use all collateral to buy what we can
            # (simplified - would need partial buy logic)
            
            # Create lien
            create_lien(loan.borrower_player_id, shortfall, "commodity")
            
            # Return what we can to lender
            import inventory
            partial_qty = loan.collateral_locked / current_price
            inventory.add_item(loan.lender_player_id, loan.item_type, partial_qty)
            
            loan.status = CommodityLoanStatus.DEFAULTED.value
            
            modify_credit_score(loan.borrower_player_id, "commodity_defaulted")
            
            print(f"[{BANK_NAME}] 💀 DEFAULT: Loan #{loan_id} - Lien ${shortfall:.2f}")
        
        # Update listing
        listing = db.query(CommodityListing).filter(
            CommodityListing.id == loan.listing_id
        ).first()
        if listing:
            listing.quantity_lent_out -= loan.quantity_borrowed
        
        db.commit()
    finally:
        db.close()


def trigger_liquidation(player_id: int, source: str):
    """
    Trigger liquidation cascade for a player.
    
    Levels:
    1. Warning (already sent via margin call)
    2. Force sell stocks
    3. Force close commodity shorts
    4. Seize collateral
    5. Create lien
    6. Bankruptcy (optional)
    """
    print(f"[{BANK_NAME}] 🚨 LIQUIDATION TRIGGERED: Player {player_id} ({source})")
    
    # Level 2: Force sell stocks
    db = get_db()
    try:
        positions = db.query(ShareholderPosition).filter(
            ShareholderPosition.player_id == player_id,
            ShareholderPosition.shares_owned > 0
        ).all()
        
        total_raised = 0.0
        
        for position in positions:
            company = db.query(CompanyShares).filter(
                CompanyShares.id == position.company_shares_id
            ).first()
            
            if company:
                # Sell all shares
                proceeds = position.shares_owned * company.current_price
                total_raised += proceeds
                
                # Update company
                company.shares_in_float += position.shares_owned
                
                # Clear position
                position.shares_owned = 0
                position.margin_debt = 0
                position.margin_shares = 0
                position.is_margin_position = False
        
        db.commit()
        
        if total_raised > 0:
            from auth import get_db as get_auth_db, Player
            auth_db = get_auth_db()
            try:
                player = auth_db.query(Player).filter(Player.id == player_id).first()
                if player:
                    player.cash_balance += total_raised
                    auth_db.commit()
            finally:
                auth_db.close()
            
            print(f"[{BANK_NAME}] L2: Sold stocks for ${total_raised:,.2f}")
    finally:
        db.close()
    
    # Level 3: Force close commodity positions
    db = get_db()
    try:
        loans = db.query(CommodityLoan).filter(
            CommodityLoan.borrower_player_id == player_id,
            CommodityLoan.status.in_([CommodityLoanStatus.ACTIVE.value, CommodityLoanStatus.LATE.value])
        ).all()
        
        for loan in loans:
            force_close_commodity_loan(loan.id)
            print(f"[{BANK_NAME}] L3: Force closed commodity loan #{loan.id}")
    finally:
        db.close()
    
    # Check if still has debt
    db = get_db()
    try:
        remaining_margin = db.query(ShareholderPosition).filter(
            ShareholderPosition.player_id == player_id,
            ShareholderPosition.margin_debt > 0
        ).all()
        
        total_debt = sum(p.margin_debt for p in remaining_margin)
        
        if total_debt > 0:
            # Level 5: Create lien
            create_lien(player_id, total_debt, source)
            print(f"[{BANK_NAME}] L5: Created lien for ${total_debt:,.2f}")
    finally:
        db.close()


def create_lien(player_id: int, amount: float, source: str):
    """Create or update a lien for a player."""
    db = get_db()
    try:
        lien = db.query(BrokerageLien).filter(
            BrokerageLien.player_id == player_id,
            BrokerageLien.source == source
        ).first()
        
        if lien:
            lien.principal += amount
        else:
            lien = BrokerageLien(
                player_id=player_id,
                principal=amount,
                source=source
            )
            db.add(lien)
        
        db.commit()
        
        modify_credit_score(player_id, "lien_created")
        
        print(f"[{BANK_NAME}] 📋 LIEN: Player {player_id} owes ${amount:,.2f} ({source})")
    finally:
        db.close()


def process_liens():
    """Process lien interest accrual and garnishment."""
    db = get_db()
    try:
        liens = db.query(BrokerageLien).all()
        
        for lien in liens:
            if lien.total_owed <= 0:
                continue
            
            # Accrue interest
            interest_rate = get_credit_interest_rate(lien.player_id) / 525600  # Per minute
            lien.interest_accrued += lien.total_owed * interest_rate
            lien.last_interest_accrual = datetime.utcnow()
            
            # Attempt garnishment (50% of cash)
            from auth import get_db as get_auth_db, Player
            auth_db = get_auth_db()
            try:
                player = auth_db.query(Player).filter(Player.id == lien.player_id).first()
                if player and player.cash_balance > 0:
                    garnish = min(player.cash_balance * 0.5, lien.total_owed)
                    
                    if garnish >= 0.01:
                        player.cash_balance -= garnish
                        lien.total_paid += garnish
                        lien.last_payment = datetime.utcnow()
                        
                        auth_db.commit()
                        
                        firm_add_cash(garnish, "lien_payment", 
                                     f"Garnishment from Player {lien.player_id}", lien.player_id)
                        
                        if lien.total_owed <= 0:
                            modify_credit_score(lien.player_id, "lien_paid_off")
                            print(f"[{BANK_NAME}] ✅ Lien CLEARED for Player {lien.player_id}")
            finally:
                auth_db.close()
        
        db.commit()
    finally:
        db.close()


# ==========================
# DRIP RELEASE PROCESSING
# ==========================

def process_drip_releases(current_tick: int):
    """Release shares from Drip Release IPOs."""
    if current_tick % 604800 != 0:  # Weekly
        return
    
    db = get_db()
    try:
        drip_companies = db.query(CompanyShares).filter(
            CompanyShares.ipo_type == IPOType.DRIP_RELEASE.value,
            CompanyShares.drip_shares_remaining > 0,
            CompanyShares.is_delisted == False
        ).all()
        
        for company in drip_companies:
            release_pct = IPO_CONFIG[IPOType.DRIP_RELEASE]["weekly_release_pct"]
            shares_to_release = int(company.drip_shares_remaining * release_pct)
            
            if shares_to_release < 1:
                shares_to_release = company.drip_shares_remaining  # Release remainder
            
            # Move from Firm holdings to float
            firm_position = db.query(ShareholderPosition).filter(
                ShareholderPosition.player_id == BANK_PLAYER_ID,
                ShareholderPosition.company_shares_id == company.id
            ).first()
            
            if firm_position and firm_position.shares_owned >= shares_to_release:
                firm_position.shares_owned -= shares_to_release
                company.shares_held_by_firm -= shares_to_release
                company.shares_in_float += shares_to_release
                company.drip_shares_remaining -= shares_to_release
                company.drip_last_release = datetime.utcnow()
                
                print(f"[{BANK_NAME}] 💧 DRIP: Released {shares_to_release} {company.ticker_symbol}")
        
        db.commit()
    finally:
        db.close()


# ==========================
# STABILIZATION PROCESSING
# ==========================

def process_stabilization():
    """Process stabilization commitments - buy if price drops too far."""
    db = get_db()
    try:
        stabilized = db.query(CompanyShares).filter(
            CompanyShares.stabilization_active == True,
            CompanyShares.stabilization_commitment_remaining > 0,
            CompanyShares.is_delisted == False
        ).all()
        
        for company in stabilized:
            if company.current_price < company.stabilization_floor_price:
                # Price below floor - Firm buys
                buy_amount = min(
                    company.stabilization_commitment_remaining,
                    company.current_price * 100  # Buy up to 100 shares at a time
                )
                
                shares_to_buy = int(buy_amount / company.current_price)
                
                if shares_to_buy > 0 and company.shares_in_float >= shares_to_buy:
                    cost = shares_to_buy * company.current_price
                    
                    if firm_deduct_cash(cost, "stabilization_buy", 
                                       f"Stabilization buy for {company.ticker_symbol}"):
                        # Add to Firm's holdings
                        firm_position = db.query(ShareholderPosition).filter(
                            ShareholderPosition.player_id == BANK_PLAYER_ID,
                            ShareholderPosition.company_shares_id == company.id
                        ).first()
                        
                        if firm_position:
                            firm_position.shares_owned += shares_to_buy
                        else:
                            firm_position = ShareholderPosition(
                                player_id=BANK_PLAYER_ID,
                                company_shares_id=company.id,
                                shares_owned=shares_to_buy,
                                average_cost_basis=company.current_price
                            )
                            db.add(firm_position)
                        
                        company.shares_in_float -= shares_to_buy
                        company.shares_held_by_firm += shares_to_buy
                        company.stabilization_commitment_remaining -= cost
                        
                        # Update Firm's total commitments
                        firm = db.query(FirmEntity).first()
                        if firm:
                            firm.total_stabilization_commitments -= cost
                            firm.total_stabilization_costs += cost
                        
                        print(f"[{BANK_NAME}] 📊 STABILIZATION: Bought {shares_to_buy} {company.ticker_symbol} @ ${company.current_price:.2f}")
            
            # End stabilization if commitment exhausted
            if company.stabilization_commitment_remaining <= 0:
                company.stabilization_active = False
                print(f"[{BANK_NAME}] Stabilization ended for {company.ticker_symbol}")
        
        db.commit()
    finally:
        db.close()


# ==========================
# INITIALIZATION
# ==========================

def initialize():
    """Initialize the Brokerage Firm module."""
    print(f"[{BANK_NAME}] Creating database tables...")
    Base.metadata.create_all(bind=engine)
    
    brokerage_order_book.initialize() 

    # Get or create Firm entity
    firm = get_firm_entity()
    
    print(f"[{BANK_NAME}] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"[{BANK_NAME}] THE SYMCO BROKERAGE FIRM - INITIALIZED")
    print(f"[{BANK_NAME}] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"[{BANK_NAME}] Cash Reserves: ${firm.cash_reserves:,.2f}")
    print(f"[{BANK_NAME}] IPO Underwriting: {'✓ ACTIVE' if firm.is_accepting_ipos else '✗ SUSPENDED'}")
    print(f"[{BANK_NAME}] Margin Trading: {'✓ ACTIVE' if firm.is_accepting_margin else '✗ SUSPENDED'}")
    print(f"[{BANK_NAME}] Commodity Lending: {'✓ ACTIVE' if firm.is_accepting_lending else '✗ SUSPENDED'}")
    print(f"[{BANK_NAME}] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


# ==========================
# TICK HANDLER
# ==========================

async def tick(current_tick: int, now: datetime, bank_entity=None):
    """
    Brokerage Firm tick handler.
    
    Processes:
    - Margin calls and liquidations
    - Commodity loan due dates and late fees
    - Lien interest and garnishment
    - Dividend payouts
    - Drip releases
    - Stabilization buys
    - Circuit breaker status
    - Firm solvency check
    """

    brokerage_order_book.tick(current_tick)

    # Every tick: process liens
    process_liens()
    
    # Every 60 ticks (1 minute): check margins and loans
    if current_tick % 60 == 0:
        check_margin_calls()
        process_margin_call_deadlines()
        check_commodity_loan_due_dates()
        check_firm_can_operate()
    
    # Every 3600 ticks (1 hour): update TBTF status
    if current_tick % 3600 == 0:
        update_tbtf_status()
        process_stabilization()
    
    # Process dividends (handled by frequency in config)
    process_dividends(current_tick)
    
    # Weekly: drip releases
    process_drip_releases(current_tick)
    
    # Hourly stats
    if current_tick % 3600 == 0:
        firm = get_firm_entity()
        
        db = get_db()
        try:
            company_count = db.query(CompanyShares).filter(
                CompanyShares.is_delisted == False
            ).count()
            
            active_margin = db.query(ShareholderPosition).filter(
                ShareholderPosition.margin_debt > 0
            ).count()
            
            active_loans = db.query(CommodityLoan).filter(
                CommodityLoan.status.in_([CommodityLoanStatus.ACTIVE.value, CommodityLoanStatus.LATE.value])
            ).count()
            
            active_liens = db.query(BrokerageLien).count()
        finally:
            db.close()
        
        solvent = "✓ SOLVENT" if firm_is_solvent() else "✗ INSOLVENT"
        
        print(f"[{BANK_NAME}] {solvent} | Cash: ${firm.cash_reserves:,.2f} | " +
              f"Companies: {company_count} | Margin Positions: {active_margin} | " +
              f"Commodity Loans: {active_loans} | Liens: {active_liens}")


# ==========================
# PUBLIC API
# ==========================

__all__ = [
    # Identity
    'BANK_ID',
    'BANK_NAME',
    'BANK_DESCRIPTION',
    'BANK_PLAYER_ID',
    
    # Lifecycle
    'initialize',
    'tick',
    
    # Firm
    'get_firm_entity',
    'firm_is_solvent',
    
    # Credit
    'get_player_credit',
    'modify_credit_score',
    'get_credit_tier',
    'get_credit_interest_rate',
    'get_max_leverage_for_player',
    
    # IPO
    'create_ipo',
    'calculate_business_valuation',
    'IPOType',
    'IPO_CONFIG',
    
    # SCPE Trading
    'buy_shares',
    'sell_shares',
    'calculate_margin_multiplier',
    
    # Short Selling
    'short_sell_shares',
    'close_short_position',
    
    # SCCE Lending
    'list_commodity_for_lending',
    'borrow_commodity',
    'return_commodity',
    'extend_commodity_loan',
    
    # Models
    'CompanyShares',
    'ShareholderPosition',
    'ShareLoan',
    'CommodityListing',
    'CommodityLoan',
    'PlayerCreditRating',
    'BrokerageLien',
    'FirmEntity',
    
    # Enums
    'DividendType',
    'DividendFrequency',
    'CreditTier',
]
