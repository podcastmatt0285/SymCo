"""
banks/brokerage_firm.py - THE SYMCO BROKERAGE FIRM

A comprehensive financial intermediary providing:

SCPE (SymCo Player Exchange):
- Player company IPOs with 6 different offering structures
- Multiple share classes (Common, Preferred, Series A/B, Dual-Class)
- Margin trading with credit-based leverage (2x-10x)
- Short selling with borrow fees
- Real-time order book with price discovery

SCCE (SymCo Commodities Exchange):
- Commodity borrowing/lending between players
- Dynamic due dates based on volatility and credit
- 105% collateral requirements
- Fee split between lender and Firm

IPO Valuation:
- Based on player's TOTAL NET WORTH
- Includes: cash, inventory, land, businesses, share holdings
- More realistic company valuation

Fee Structure:
- Trading Commission: 0.25% per trade
- Margin Interest: 8-20% annually (credit-based)
- IPO Underwriting: 5-10% depending on type
- Short Borrow Fee: 3-15% annually
- Commodity Lending Fee: 2% (split 50/50)

The Firm:
- Starting capital: $100,000,000
- Revenue from commissions, interest, underwriting, lending fees
- Can go broke (freezes operations)
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum
import math

from sqlalchemy import create_engine, Column, String, Float, DateTime, Integer, Boolean, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

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
BANK_DESCRIPTION = "Full-service brokerage: IPOs, margin trading, short selling, commodity lending"
BANK_PLAYER_ID = -5

# ==========================
# FINANCIAL CONSTANTS
# ==========================
STARTING_CAPITAL = 100_000_000_000_000_000_000_000_000.00
MINIMUM_OPERATING_RESERVE = 50_000_000.00

EQUITY_TRADE_COMMISSION = 0.125
MIN_COMMISSION = 1.00

MARGIN_BASE_INTEREST_RATE = 0.18
MARGIN_MAINTENANCE_RATIO = 0.30
MIN_MARGIN_MULTIPLIER = 2.0
MAX_MARGIN_MULTIPLIER = 10.0

SHORT_COLLATERAL_REQUIREMENT = 1.50
SHORT_BORROW_FEE_BASE = 0.05
SHORT_FEE_FIRM_SPLIT = 0.40

COMMODITY_COLLATERAL_REQUIREMENT = 1.05
COMMODITY_LENDING_FEE_SPLIT = 0.50
LATE_FEE_DAILY_RATE = 0.10
MAX_LATE_DAYS_BEFORE_FORCE_CLOSE = 3

COLLATERAL_REQUIREMENT = COMMODITY_COLLATERAL_REQUIREMENT
LENDING_FEE_SPLIT = COMMODITY_LENDING_FEE_SPLIT

DEFAULT_CREDIT_RATING = 350
CREDIT_RATING_MIN = 230
CREDIT_RATING_MAX = 850

# ==========================
# ENUMS
# ==========================

class IPOType(str, Enum):
    DIRECT_LISTING = "direct_listing"
    FIRM_UNDERWRITTEN = "firm_underwritten"
    PREFERRED_OFFERING = "preferred_offering"
    SERIES_A_GROWTH = "series_a_growth"
    SERIES_B_INCOME = "series_b_income"
    DUAL_CLASS = "dual_class"


class ShareClass(str, Enum):
    COMMON = "common"
    PREFERRED = "preferred"
    SERIES_A = "series_a"
    SERIES_B = "series_b"
    CLASS_A = "class_a"
    CLASS_B = "class_b"


class DividendType(str, Enum):
    CASH = "cash"
    STOCK = "stock"
    COMMODITY = "commodity"
    SCRIP = "scrip"


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
    PRIME = "prime"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    RESTRICTED = "restricted"


class LiquidationLevel(str, Enum):
    WARNING = "warning"
    MARGIN_CALL = "margin_call"
    FORCED_STOCK_SALE = "forced_stock_sale"
    FORCED_COMMODITY_CLOSE = "forced_commodity_close"
    COLLATERAL_SEIZURE = "collateral_seizure"
    LIEN_CREATION = "lien_creation"
    BANKRUPTCY = "bankruptcy"


CREDIT_TIERS = {
    CreditTier.PRIME: (80, 100, 0.08, 10.0, 0.03),
    CreditTier.GOOD: (60, 79, 0.10, 6.0, 0.05),
    CreditTier.FAIR: (40, 59, 0.12, 4.0, 0.08),
    CreditTier.POOR: (20, 39, 0.16, 2.0, 0.12),
    CreditTier.RESTRICTED: (0, 19, 0.20, 1.0, 0.15),
}

CREDIT_MODIFIERS = {
    "trade_completed": +1,
    "margin_position_closed_profit": +3,
    "margin_position_closed_loss": -1,
    "margin_call_triggered": -15,
    "margin_call_resolved": +5,
    "forced_liquidation": -25,
    "short_returned_on_time": +2,
    "short_returned_late": -5,
    "short_defaulted": -20,
    "commodity_returned_on_time": +3,
    "commodity_returned_late": -5,
    "commodity_defaulted": -20,
    "ipo_completed": +10,
    "dividend_paid": +2,
    "dividend_missed": -5,
    "lien_created": -15,
    "lien_paid_off": +10,
    "short_position_profitable": +2,
    "short_position_loss": -1,
    "margin_trade_profitable": +2,
    "margin_trade_loss": -1,
}

IPO_CONFIG = {
    IPOType.DIRECT_LISTING: {
        "name": "Direct Listing",
        "description": "List shares directly on exchange. Low cost, you sell at market price.",
        "share_class": ShareClass.COMMON,
        "firm_underwritten": False,
        "fee_type": "flat",
        "fee_amount": 5000.00,
        "min_shares": 1000,
        "max_float_pct": 0.80,
        "min_valuation": 25000,
        "voting_rights": "1 vote per share",
        "dividend_priority": "Standard",
    },
    IPOType.FIRM_UNDERWRITTEN: {
        "name": "Firm Underwritten IPO",
        "description": "The Firm purchases your shares at 7% discount, guaranteeing immediate capital.",
        "share_class": ShareClass.COMMON,
        "firm_underwritten": True,
        "discount_rate": 0.07,
        "min_shares": 10000,
        "max_float_pct": 0.60,
        "min_valuation": 50000,
        "voting_rights": "1 vote per share",
        "dividend_priority": "Standard",
    },
    IPOType.PREFERRED_OFFERING: {
        "name": "Preferred Stock Offering",
        "description": "Issue preferred shares with guaranteed dividends and liquidation priority.",
        "share_class": ShareClass.PREFERRED,
        "firm_underwritten": True,
        "discount_rate": 0.05,
        "min_shares": 5000,
        "max_float_pct": 0.40,
        "min_valuation": 75000,
        "voting_rights": "No voting rights",
        "dividend_priority": "First priority - paid before common",
        "fixed_dividend_rate": 0.08,
        "liquidation_preference": 1.0,
    },
    IPOType.SERIES_A_GROWTH: {
        "name": "Series A Growth Shares",
        "description": "Convertible shares for growth investors. Convert to common at 1:1.5 ratio.",
        "share_class": ShareClass.SERIES_A,
        "firm_underwritten": True,
        "discount_rate": 0.10,
        "min_shares": 10000,
        "max_float_pct": 0.30,
        "min_valuation": 100000,
        "voting_rights": "1 vote per share (as-converted basis)",
        "dividend_priority": "Same as common",
        "conversion_ratio": 1.5,
        "anti_dilution": True,
    },
    IPOType.SERIES_B_INCOME: {
        "name": "Series B Income Shares",
        "description": "High fixed dividends for income seekers. 12% annual dividend.",
        "share_class": ShareClass.SERIES_B,
        "firm_underwritten": True,
        "discount_rate": 0.03,
        "min_shares": 5000,
        "max_float_pct": 0.25,
        "min_valuation": 100000,
        "voting_rights": "No voting rights",
        "dividend_priority": "Second priority - after preferred, before common",
        "fixed_dividend_rate": 0.12,
        "callable": True,
    },
    IPOType.DUAL_CLASS: {
        "name": "Dual-Class Structure",
        "description": "Issue Class B shares to public while keeping Class A (10x voting) for yourself.",
        "share_class": ShareClass.CLASS_B,
        "founder_class": ShareClass.CLASS_A,
        "firm_underwritten": True,
        "discount_rate": 0.08,
        "min_shares": 20000,
        "max_float_pct": 0.70,
        "min_valuation": 150000,
        "voting_rights": "Class A: 10 votes/share, Class B: 1 vote/share",
        "dividend_priority": "Equal dividends per share",
        "founder_control_minimum": 0.51,
    },
}


# ==========================
# DATABASE MODELS
# ==========================

class FirmEntity(Base):
    __tablename__ = "brokerage_firm_entity"
    
    id = Column(Integer, primary_key=True)
    cash_reserves = Column(Float, default=STARTING_CAPITAL)
    
    total_trading_commissions = Column(Float, default=0.0)
    total_trading_commissions_earned = Column(Float, default=0.0)
    total_margin_interest = Column(Float, default=0.0)
    total_margin_interest_earned = Column(Float, default=0.0)
    total_underwriting_fees = Column(Float, default=0.0)
    total_underwriting_fees_earned = Column(Float, default=0.0)
    total_listing_fees = Column(Float, default=0.0)
    total_short_borrow_fees = Column(Float, default=0.0)
    total_commodity_lending_fees = Column(Float, default=0.0)
    total_lending_fees_earned = Column(Float, default=0.0)
    total_late_fees_earned = Column(Float, default=0.0)
    total_dividends_received = Column(Float, default=0.0)
    total_spread_profit = Column(Float, default=0.0)
    
    total_underwriting_costs = Column(Float, default=0.0)
    total_underwriting_losses = Column(Float, default=0.0)
    total_bad_debt_losses = Column(Float, default=0.0)
    total_default_losses = Column(Float, default=0.0)
    total_stabilization_costs = Column(Float, default=0.0)
    total_stabilization_commitments = Column(Float, default=0.0)
    
    shares_held_value = Column(Float, default=0.0)
    margin_loans_outstanding = Column(Float, default=0.0)
    
    is_accepting_ipos = Column(Boolean, default=True)
    is_accepting_margin = Column(Boolean, default=True)
    is_accepting_shorts = Column(Boolean, default=True)
    is_accepting_lending = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PlayerCreditRating(Base):
    __tablename__ = "player_credit_ratings"
    
    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, unique=True, index=True, nullable=False)
    
    credit_score = Column(Integer, default=DEFAULT_CREDIT_RATING)
    tier = Column(String, default=CreditTier.FAIR.value)
    
    total_trades = Column(Integer, default=0)
    total_margin_trades = Column(Integer, default=0)
    profitable_margin_trades = Column(Integer, default=0)
    margin_calls_received = Column(Integer, default=0)
    forced_liquidations = Column(Integer, default=0)
    total_commodity_loans = Column(Integer, default=0)
    on_time_returns = Column(Integer, default=0)
    total_dividends_paid = Column(Integer, default=0)
    total_dividends_skipped = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CompanyShares(Base):
    __tablename__ = "company_shares"
    
    id = Column(Integer, primary_key=True)
    business_id = Column(Integer, index=True, default=0)
    founder_id = Column(Integer, index=True, nullable=False)
    
    company_name = Column(String, nullable=False)
    ticker_symbol = Column(String, unique=True, nullable=False)
    share_class = Column(String, default=ShareClass.COMMON.value)
    
    total_shares_authorized = Column(Integer, nullable=False)
    shares_outstanding = Column(Integer, default=0)
    shares_held_by_founder = Column(Integer, default=0)
    shares_held_by_firm = Column(Integer, default=0)
    shares_in_float = Column(Integer, default=0)
    
    founder_class_a_shares = Column(Integer, default=0)
    
    current_price = Column(Float, default=0.0)
    ipo_price = Column(Float, default=0.0)
    high_52_week = Column(Float, default=0.0)
    low_52_week = Column(Float, default=0.0)
    
    volume_today = Column(Integer, default=0)
    volume_avg_30d = Column(Float, default=0.0)
    
    dividend_config = Column(JSON, default=list)
    consecutive_dividend_payouts = Column(Integer, default=0)
    last_dividend_date = Column(DateTime, nullable=True)
    dividend_warning_active = Column(Boolean, default=False)
    last_dividend_warning = Column(DateTime, nullable=True)
    
    fixed_dividend_rate = Column(Float, nullable=True)
    conversion_ratio = Column(Float, nullable=True)
    liquidation_preference = Column(Float, nullable=True)
    is_callable = Column(Boolean, default=False)
    
    ipo_type = Column(String, nullable=True)
    ipo_date = Column(DateTime, nullable=True)
    ipo_valuation = Column(Float, default=0.0)
    
    drip_shares_remaining = Column(Integer, default=0)
    drip_last_release = Column(DateTime, nullable=True)
    shelf_shares_remaining = Column(Integer, default=0)
    shelf_tranches_used = Column(Integer, default=0)
    shelf_expiry = Column(DateTime, nullable=True)
    stabilization_active = Column(Boolean, default=False)
    stabilization_floor_price = Column(Float, nullable=True)
    stabilization_commitment_remaining = Column(Float, default=0.0)
    is_tbtf = Column(Boolean, default=False)
    
    is_delisted = Column(Boolean, default=False)
    delisted_at = Column(DateTime, nullable=True)
    can_relist_after = Column(DateTime, nullable=True)
    trading_halted = Column(Boolean, default=False)
    trading_halted_until = Column(DateTime, nullable=True)
    halt_reason = Column(String, nullable=True)
    
    is_dual_class = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class ShareholderPosition(Base):
    __tablename__ = "shareholder_positions"
    
    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, index=True, nullable=False)
    company_shares_id = Column(Integer, ForeignKey("company_shares.id"), index=True, nullable=False)
    
    shares_owned = Column(Integer, default=0)
    shares_available_to_lend = Column(Integer, default=0)
    shares_lent_out = Column(Integer, default=0)
    average_cost_basis = Column(Float, default=0.0)
    
    is_margin_position = Column(Boolean, default=False)
    margin_shares = Column(Integer, default=0)
    margin_debt = Column(Float, default=0.0)
    margin_multiplier_used = Column(Float, default=1.0)
    margin_interest_accrued = Column(Float, default=0.0)
    last_interest_accrual = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ShareLoan(Base):
    __tablename__ = "share_loans"
    
    id = Column(Integer, primary_key=True)
    lender_player_id = Column(Integer, index=True, nullable=False)
    borrower_player_id = Column(Integer, index=True, nullable=False)
    company_shares_id = Column(Integer, ForeignKey("company_shares.id"), nullable=False)
    
    shares_borrowed = Column(Integer, nullable=False)
    borrow_price = Column(Float, nullable=False)
    collateral_locked = Column(Float, nullable=False)
    borrow_rate_weekly = Column(Float, nullable=False)
    
    borrowed_at = Column(DateTime, default=datetime.utcnow)
    due_date = Column(DateTime, nullable=False)
    returned_at = Column(DateTime, nullable=True)
    
    total_fees_paid = Column(Float, default=0.0)
    last_interest_charge = Column(DateTime, default=datetime.utcnow)
    fees_to_lender = Column(Float, default=0.0)
    fees_to_firm = Column(Float, default=0.0)
    
    status = Column(String, default=ShareLoanStatus.ACTIVE.value)


class CommodityListing(Base):
    __tablename__ = "commodity_listings"
    
    id = Column(Integer, primary_key=True)
    lender_player_id = Column(Integer, index=True, nullable=False)
    item_type = Column(String, index=True, nullable=False)
    
    quantity_available = Column(Float, nullable=False)
    quantity_lent_out = Column(Float, default=0.0)
    weekly_rate = Column(Float, nullable=False)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class CommodityLoan(Base):
    __tablename__ = "commodity_loans"
    
    id = Column(Integer, primary_key=True)
    listing_id = Column(Integer, ForeignKey("commodity_listings.id"), nullable=False)
    lender_player_id = Column(Integer, index=True, nullable=False)
    borrower_player_id = Column(Integer, index=True, nullable=False)
    
    item_type = Column(String, nullable=False)
    quantity_borrowed = Column(Float, nullable=False)
    borrow_price = Column(Float, nullable=False)
    collateral_locked = Column(Float, nullable=False)
    weekly_rate = Column(Float, nullable=False)
    
    borrowed_at = Column(DateTime, default=datetime.utcnow)
    due_date = Column(DateTime, nullable=False)
    returned_at = Column(DateTime, nullable=True)
    
    total_fees_paid = Column(Float, default=0.0)
    fees_to_lender = Column(Float, default=0.0)
    fees_to_firm = Column(Float, default=0.0)
    
    days_late = Column(Integer, default=0)
    late_fees_paid = Column(Float, default=0.0)
    
    extensions_used = Column(Integer, default=0)
    max_extensions = Column(Integer, default=3)
    
    status = Column(String, default=CommodityLoanStatus.ACTIVE.value)


class MarginCall(Base):
    __tablename__ = "margin_calls"
    
    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, index=True, nullable=False)
    
    amount_required = Column(Float, nullable=False)
    deadline = Column(DateTime, nullable=False)
    
    is_resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime, nullable=True)
    resolution_type = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class BrokerageLien(Base):
    __tablename__ = "brokerage_liens"
    
    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, index=True, nullable=False)
    
    principal = Column(Float, default=0.0)
    interest_accrued = Column(Float, default=0.0)
    total_paid = Column(Float, default=0.0)
    
    source = Column(String, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    last_interest_accrual = Column(DateTime, default=datetime.utcnow)
    last_payment = Column(DateTime, nullable=True)
    
    @property
    def total_owed(self):
        return self.principal + self.interest_accrued - self.total_paid


class PriceHistory(Base):
    __tablename__ = "price_history"
    
    id = Column(Integer, primary_key=True)
    company_shares_id = Column(Integer, ForeignKey("company_shares.id"), index=True, nullable=True)
    item_type = Column(String, index=True, nullable=True)
    
    price = Column(Float, nullable=False)
    volume = Column(Float, default=0.0)
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)


class FirmTransaction(Base):
    __tablename__ = "firm_transactions"
    
    id = Column(Integer, primary_key=True)
    transaction_type = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(String, nullable=True)
    
    player_id = Column(Integer, nullable=True)
    company_shares_id = Column(Integer, nullable=True)
    loan_id = Column(Integer, nullable=True)
    
    timestamp = Column(DateTime, default=datetime.utcnow)


DutchAuctionBid = None


# ==========================
# HELPER FUNCTIONS
# ==========================

def get_db():
    return SessionLocal()


def get_firm_entity() -> FirmEntity:
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
    db = get_db()
    try:
        firm = db.query(FirmEntity).first()
        if firm:
            firm.cash_reserves += amount
            firm.last_updated = datetime.utcnow()
            
            if transaction_type in ["trading_commission", "trade_commission"]:
                firm.total_trading_commissions += amount
                firm.total_trading_commissions_earned += amount
            elif transaction_type == "margin_interest":
                firm.total_margin_interest += amount
                firm.total_margin_interest_earned += amount
            elif transaction_type in ["underwriting_fee", "ipo_fee"]:
                firm.total_underwriting_fees += amount
                firm.total_underwriting_fees_earned += amount
            elif transaction_type == "listing_fee":
                firm.total_listing_fees += amount
            elif transaction_type in ["short_borrow_fee", "short_interest"]:
                firm.total_short_borrow_fees += amount
            elif transaction_type in ["lending_fee", "extension_fee"]:
                firm.total_commodity_lending_fees += amount
                firm.total_lending_fees_earned += amount
            elif transaction_type == "late_fee":
                firm.total_late_fees_earned += amount
            elif transaction_type == "dividend":
                firm.total_dividends_received += amount
            
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
    finally:
        db.close()


def firm_deduct_cash(amount: float, transaction_type: str, description: str = None) -> bool:
    db = get_db()
    try:
        firm = db.query(FirmEntity).first()
        if not firm or firm.cash_reserves < amount:
            return False
        
        if firm.cash_reserves - amount < MINIMUM_OPERATING_RESERVE:
            print(f"[{BANK_NAME}] Cannot deduct - would breach minimum reserve")
            return False
        
        firm.cash_reserves -= amount
        firm.last_updated = datetime.utcnow()
        
        if transaction_type in ["underwriting_cost", "ipo_underwrite"]:
            firm.total_underwriting_costs += amount
        elif transaction_type == "bad_debt":
            firm.total_bad_debt_losses += amount
            firm.total_default_losses += amount
        elif transaction_type in ["stabilization_buy", "stabilization_cost"]:
            firm.total_stabilization_costs += amount
        
        transaction = FirmTransaction(
            transaction_type=transaction_type,
            amount=-amount,
            description=description
        )
        db.add(transaction)
        db.commit()
        return True
    finally:
        db.close()


def firm_is_solvent() -> bool:
    firm = get_firm_entity()
    return firm.cash_reserves >= MINIMUM_OPERATING_RESERVE


def check_firm_can_operate():
    db = get_db()
    try:
        firm = db.query(FirmEntity).first()
        if not firm:
            return
        
        if firm.cash_reserves < MINIMUM_OPERATING_RESERVE:
            firm.is_accepting_ipos = False
            firm.is_accepting_margin = False
            firm.is_accepting_shorts = False
            firm.is_accepting_lending = False
        elif firm.cash_reserves < MINIMUM_OPERATING_RESERVE * 2:
            firm.is_accepting_ipos = False
            firm.is_accepting_margin = True
            firm.is_accepting_shorts = True
            firm.is_accepting_lending = True
        else:
            firm.is_accepting_ipos = True
            firm.is_accepting_margin = True
            firm.is_accepting_shorts = True
            firm.is_accepting_lending = True
        
        db.commit()
    finally:
        db.close()


# ==========================
# CREDIT RATING SYSTEM
# ==========================

def get_player_credit(player_id: int) -> PlayerCreditRating:
    db = get_db()
    try:
        rating = db.query(PlayerCreditRating).filter(
            PlayerCreditRating.player_id == player_id
        ).first()
        
        if not rating:
            rating = PlayerCreditRating(
                player_id=player_id,
                credit_score=DEFAULT_CREDIT_RATING,
                tier=CreditTier.FAIR.value
            )
            db.add(rating)
            db.commit()
            db.refresh(rating)
        
        return rating
    finally:
        db.close()


def get_credit_tier(score: int) -> CreditTier:
    for tier, (min_score, max_score, _, _, _) in CREDIT_TIERS.items():
        if min_score <= score <= max_score:
            return tier
    return CreditTier.RESTRICTED


def modify_credit_score(player_id: int, event: str) -> int:
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
        
        rating.credit_score = max(CREDIT_RATING_MIN, 
                                  min(CREDIT_RATING_MAX, rating.credit_score + modifier))
        rating.tier = get_credit_tier(rating.credit_score).value
        rating.last_updated = datetime.utcnow()
        
        db.commit()
        
        return rating.credit_score
    finally:
        db.close()


def get_credit_interest_rate(player_id: int) -> float:
    rating = get_player_credit(player_id)
    tier = get_credit_tier(rating.credit_score)
    
    for t, (_, _, interest_rate, _, _) in CREDIT_TIERS.items():
        if t == tier:
            return interest_rate
    return 0.20


def get_max_leverage_for_player(player_id: int) -> float:
    rating = get_player_credit(player_id)
    tier = get_credit_tier(rating.credit_score)
    
    for t, (_, _, _, max_leverage, _) in CREDIT_TIERS.items():
        if t == tier:
            return max_leverage
    return 1.0


def get_short_borrow_rate(player_id: int) -> float:
    rating = get_player_credit(player_id)
    tier = get_credit_tier(rating.credit_score)
    
    for t, (_, _, _, _, borrow_rate) in CREDIT_TIERS.items():
        if t == tier:
            return borrow_rate
    return 0.15


# ==========================
# PRICE & VOLATILITY
# ==========================

def record_price(company_shares_id: int = None, item_type: str = None, 
                 price: float = 0.0, volume: float = 0.0):
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


def calculate_stock_volatility(company_shares_id: int, days: int = 30) -> float:
    db = get_db()
    try:
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        prices = db.query(PriceHistory).filter(
            PriceHistory.company_shares_id == company_shares_id,
            PriceHistory.recorded_at >= cutoff
        ).order_by(PriceHistory.recorded_at.asc()).all()
        
        if len(prices) < 2:
            return 0.15
        
        returns = []
        for i in range(1, len(prices)):
            if prices[i-1].price > 0:
                daily_return = (prices[i].price - prices[i-1].price) / prices[i-1].price
                returns.append(daily_return)
        
        if not returns:
            return 0.15
        
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        return math.sqrt(variance)
    finally:
        db.close()


def calculate_commodity_volatility(item_type: str, days: int = 7) -> float:
    db = get_db()
    try:
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        prices = db.query(PriceHistory).filter(
            PriceHistory.item_type == item_type,
            PriceHistory.recorded_at >= cutoff
        ).order_by(PriceHistory.recorded_at.asc()).all()
        
        if len(prices) < 2:
            return 0.15
        
        returns = []
        for i in range(1, len(prices)):
            if prices[i-1].price > 0:
                daily_return = (prices[i].price - prices[i-1].price) / prices[i-1].price
                returns.append(daily_return)
        
        if not returns:
            return 0.15
        
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        return math.sqrt(variance)
    finally:
        db.close()


# ==========================
# TOTAL PLAYER NET WORTH VALUATION
# ==========================

def calculate_player_total_net_worth(player_id: int) -> dict:
    """Calculate a player's TOTAL NET WORTH for IPO valuation."""
    db = get_db()
    try:
        breakdown = {
            "cash_value": 0.0,
            "inventory_value": 0.0,
            "land_value": 0.0,
            "business_value": 0.0,
            "shares_value": 0.0,
            "total_net_worth": 0.0,
            "details": {
                "inventory_items": [],
                "land_plots": [],
                "businesses": [],
                "share_holdings": []
            }
        }
        
        # 1. CASH BALANCE
        try:
            from auth import Player, get_db as get_auth_db
            auth_db = get_auth_db()
            try:
                player = auth_db.query(Player).filter(Player.id == player_id).first()
                if player:
                    breakdown["cash_value"] = player.cash_balance
            finally:
                auth_db.close()
        except ImportError:
            pass
        
        # 2. INVENTORY VALUE
        try:
            import inventory
            import market as market_mod
            
            inv_db = inventory.get_db()
            try:
                items = inv_db.query(inventory.InventoryItem).filter(
                    inventory.InventoryItem.player_id == player_id,
                    inventory.InventoryItem.quantity > 0
                ).all()
                
                for item in items:
                    market_price = market_mod.get_market_price(item.item_type) or 1.0
                    item_value = item.quantity * market_price
                    breakdown["inventory_value"] += item_value
                    breakdown["details"]["inventory_items"].append({
                        "item_type": item.item_type,
                        "quantity": item.quantity,
                        "unit_price": market_price,
                        "total_value": item_value
                    })
            finally:
                inv_db.close()
        except ImportError:
            pass
        
        # 3. LAND VALUE
        try:
            from land import LandPlot, get_db as get_land_db
            
            land_db = get_land_db()
            try:
                plots = land_db.query(LandPlot).filter(
                    LandPlot.owner_id == player_id
                ).all()
                
                for plot in plots:
                    plot_value = plot.monthly_tax * 150
                    breakdown["land_value"] += plot_value
                    breakdown["details"]["land_plots"].append({
                        "plot_id": plot.id,
                        "terrain": getattr(plot, 'terrain_type', 'unknown'),
                        "monthly_tax": plot.monthly_tax,
                        "value": plot_value
                    })
            finally:
                land_db.close()
        except ImportError:
            pass
        except Exception as e:
            print(f"[{BANK_NAME}] Land valuation error: {e}")
        
        # 4. BUSINESS VALUE
        try:
            from business import Business, BUSINESS_TYPES
            from land import LandPlot, get_db as get_land_db
            
            # Use the business module's database directly via SQLAlchemy
            # This is more resilient than importing get_db which may not exist
            try:
                from business import get_db as get_business_db
                biz_db = get_business_db()
            except (ImportError, AttributeError):
                # Fallback: create session from business module's engine
                from business import SessionLocal as BusinessSessionLocal
                biz_db = BusinessSessionLocal()
            
            try:
                businesses = biz_db.query(Business).filter(
                    Business.owner_id == player_id,
                    Business.is_active == True
                ).all()
                print(f"[{BANK_NAME}] Found {len(businesses)} businesses for player {player_id}")
            finally:
                biz_db.close()
            
            land_db = get_land_db()
            try:
                for biz in businesses:
                    config = BUSINESS_TYPES.get(biz.business_type, {})
                    startup_cost = config.get("startup_cost", 5000)
                    
                    plot = land_db.query(LandPlot).filter(
                        LandPlot.id == biz.land_plot_id
                    ).first()
                    land_value = plot.monthly_tax * 100 if plot else 5000
                    
                    estimated_monthly_profit = startup_cost * 0.05
                    biz_value = startup_cost + land_value + (estimated_monthly_profit * 8)
                    
                    breakdown["business_value"] += biz_value
                    breakdown["details"]["businesses"].append({
                        "business_id": biz.id,
                        "business_type": biz.business_type,
                        "business_name": config.get("name", biz.business_type),
                        "startup_cost": startup_cost,
                        "land_value": land_value,
                        "total_value": biz_value
                    })
            finally:
                land_db.close()
        except ImportError as e:
            print(f"[{BANK_NAME}] Business import error: {e}")
        except Exception as e:
            print(f"[{BANK_NAME}] Business valuation error: {e}")
        
        # 5. SHARE HOLDINGS VALUE
        positions = db.query(ShareholderPosition).filter(
            ShareholderPosition.player_id == player_id,
            ShareholderPosition.shares_owned > 0
        ).all()
        
        for pos in positions:
            company = db.query(CompanyShares).filter(
                CompanyShares.id == pos.company_shares_id
            ).first()
            
            if company and not company.is_delisted:
                holding_value = pos.shares_owned * company.current_price
                breakdown["shares_value"] += holding_value
                breakdown["details"]["share_holdings"].append({
                    "ticker": company.ticker_symbol,
                    "shares": pos.shares_owned,
                    "price": company.current_price,
                    "value": holding_value
                })
        
        breakdown["total_net_worth"] = (
            breakdown["cash_value"] +
            breakdown["inventory_value"] +
            breakdown["land_value"] +
            breakdown["business_value"] +
            breakdown["shares_value"]
        )
        
        return breakdown
    
    except Exception as e:
        print(f"[{BANK_NAME}] Net worth calculation error: {e}")
        return {
            "cash_value": 0.0,
            "inventory_value": 0.0,
            "land_value": 0.0,
            "business_value": 0.0,
            "shares_value": 0.0,
            "total_net_worth": 10000.0,
            "details": {}
        }
    finally:
        db.close()


def calculate_player_company_valuation(player_id: int) -> dict:
    """Calculate valuation for IPO purposes based on total net worth."""
    net_worth = calculate_player_total_net_worth(player_id)
    
    total_valuation = net_worth["total_net_worth"]
    
    if total_valuation < 50000:
        suggested_shares = 10000
    elif total_valuation < 250000:
        suggested_shares = 50000
    elif total_valuation < 500000:
        suggested_shares = 100000
    elif total_valuation < 1000000:
        suggested_shares = 500000
    else:
        suggested_shares = 1000000
    
    suggested_price = total_valuation / suggested_shares
    
    return {
        "total_businesses": len(net_worth["details"].get("businesses", [])),
        "total_book_value": net_worth["land_value"] + net_worth["business_value"],
        "total_earnings_value": 0,
        "total_valuation": total_valuation,
        "businesses_breakdown": net_worth["details"].get("businesses", []),
        "suggested_ipo_shares": suggested_shares,
        "suggested_share_price": suggested_price,
        "net_worth_breakdown": net_worth
    }


def calculate_business_valuation(business_id: int) -> dict:
    """Legacy function - calculates single business value."""
    try:
        from business import Business, BUSINESS_TYPES
        from land import LandPlot, get_db as get_land_db
        
        db = get_db()
        try:
            business = db.query(Business).filter(Business.id == business_id).first()
            if not business:
                return None
            
            config = BUSINESS_TYPES.get(business.business_type, {})
            startup_cost = config.get("startup_cost", 5000)
            
            land_db = get_land_db()
            try:
                plot = land_db.query(LandPlot).filter(
                    LandPlot.id == business.land_plot_id
                ).first()
                land_value = plot.monthly_tax * 150 if plot else 10000
            finally:
                land_db.close()
            
            book_value = land_value + startup_cost
            earnings_value = startup_cost * 0.05 * 8
            
            return {
                "book_value": book_value,
                "land_value": land_value,
                "building_cost": startup_cost,
                "estimated_weekly_profit": startup_cost * 0.01,
                "earnings_multiple": 8,
                "earnings_value": earnings_value,
                "total_valuation": book_value + earnings_value,
                "suggested_share_price": (book_value + earnings_value) / 10000,
            }
        finally:
            db.close()
    except ImportError:
        return None


# ==========================
# IPO SYSTEM
# ==========================

def create_player_ipo(
    founder_id: int,
    company_name: str,
    ticker_symbol: str,
    ipo_type: IPOType,
    shares_to_offer: int,
    total_shares: int,
    share_class: str = None,
    dividend_config: list = None
) -> Optional[CompanyShares]:
    """Create an IPO for a player's holding company."""
    db = get_db()
    try:
        ticker_symbol = ticker_symbol.upper().strip()
        if len(ticker_symbol) < 2 or len(ticker_symbol) > 5:
            return None
        
        existing = db.query(CompanyShares).filter(
            CompanyShares.ticker_symbol == ticker_symbol
        ).first()
        if existing:
            return None
        
        existing_company = db.query(CompanyShares).filter(
            CompanyShares.founder_id == founder_id,
            CompanyShares.is_delisted == False
        ).first()
        if existing_company:
            return None
        
        valuation = calculate_player_company_valuation(founder_id)
        total_valuation = valuation["total_valuation"]
        
        config = IPO_CONFIG.get(ipo_type)
        if not config:
            return None
        
        if total_valuation < config.get("min_valuation", 25000):
            return None
        
        max_float = int(total_shares * config["max_float_pct"])
        if shares_to_offer > max_float:
            return None
        
        if shares_to_offer < config["min_shares"]:
            return None
        
        firm = get_firm_entity()
        if config.get("firm_underwritten") and not firm.is_accepting_ipos:
            return None
        
        share_price = total_valuation / total_shares
        actual_share_class = share_class or config["share_class"].value
        
        if ipo_type == IPOType.DIRECT_LISTING:
            return _process_direct_listing_ipo(
                db, founder_id, company_name, ticker_symbol, config,
                shares_to_offer, total_shares, share_price, actual_share_class,
                dividend_config, total_valuation
            )
        elif ipo_type == IPOType.DUAL_CLASS:
            return _process_dual_class_ipo(
                db, founder_id, company_name, ticker_symbol, config,
                shares_to_offer, total_shares, share_price,
                dividend_config, total_valuation
            )
        else:
            return _process_underwritten_ipo(
                db, founder_id, company_name, ticker_symbol, ipo_type, config,
                shares_to_offer, total_shares, share_price, actual_share_class,
                dividend_config, total_valuation
            )
    
    except Exception as e:
        print(f"[{BANK_NAME}] IPO error: {e}")
        return None
    finally:
        db.close()


def _process_direct_listing_ipo(db, founder_id, company_name, ticker_symbol, config,
                                 shares_to_offer, total_shares, share_price, share_class,
                                 dividend_config, total_valuation):
    listing_fee = config["fee_amount"]
    
    from auth import Player, get_db as get_auth_db
    auth_db = get_auth_db()
    try:
        founder = auth_db.query(Player).filter(Player.id == founder_id).first()
        if not founder or founder.cash_balance < listing_fee:
            return None
        
        founder.cash_balance -= listing_fee
        auth_db.commit()
    finally:
        auth_db.close()
    
    firm_add_cash(listing_fee, "listing_fee", f"Direct listing: {ticker_symbol}", founder_id)
    
    company = CompanyShares(
        founder_id=founder_id,
        business_id=0,
        company_name=company_name,
        ticker_symbol=ticker_symbol,
        share_class=share_class,
        total_shares_authorized=total_shares,
        shares_outstanding=total_shares,
        shares_held_by_founder=total_shares,
        shares_held_by_firm=0,
        shares_in_float=0,
        current_price=share_price,
        ipo_price=share_price,
        high_52_week=share_price,
        low_52_week=share_price,
        dividend_config=dividend_config or [],
        ipo_type=IPOType.DIRECT_LISTING.value,
        ipo_date=datetime.utcnow(),
        ipo_valuation=total_valuation
    )
    
    db.add(company)
    db.commit()
    db.refresh(company)
    
    founder_position = ShareholderPosition(
        player_id=founder_id,
        company_shares_id=company.id,
        shares_owned=total_shares,
        shares_available_to_lend=total_shares,
        average_cost_basis=0.0
    )
    db.add(founder_position)
    db.commit()
    
    try:
        from banks.brokerage_order_book import place_limit_order, OrderSide
        place_limit_order(
            player_id=founder_id,
            company_shares_id=company.id,
            side=OrderSide.SELL,
            quantity=shares_to_offer,
            limit_price=share_price
        )
    except ImportError:
        pass
    
    modify_credit_score(founder_id, "ipo_completed")
    
    print(f"[{BANK_NAME}] 🎉 DIRECT LISTING: {ticker_symbol}")
    
    return company


def _process_underwritten_ipo(db, founder_id, company_name, ticker_symbol, ipo_type, config,
                               shares_to_offer, total_shares, share_price, share_class,
                               dividend_config, total_valuation):
    discount_rate = config.get("discount_rate", 0.07)
    discounted_price = share_price * (1 - discount_rate)
    total_cost = shares_to_offer * discounted_price
    
    if not firm_deduct_cash(total_cost, "underwriting_cost", f"Underwriting {ticker_symbol}"):
        return None
    
    actual_dividend_config = dividend_config or []
    
    if config.get("fixed_dividend_rate"):
        actual_dividend_config.append({
            "type": "cash",
            "amount": share_price * config["fixed_dividend_rate"] / 4,
            "frequency": "quarterly",
            "required": True,
            "share_class": share_class
        })
    
    company = CompanyShares(
        founder_id=founder_id,
        business_id=0,
        company_name=company_name,
        ticker_symbol=ticker_symbol,
        share_class=share_class,
        total_shares_authorized=total_shares,
        shares_outstanding=total_shares,
        shares_held_by_founder=total_shares - shares_to_offer,
        shares_held_by_firm=shares_to_offer,
        shares_in_float=0,
        current_price=share_price,
        ipo_price=share_price,
        high_52_week=share_price,
        low_52_week=share_price,
        dividend_config=actual_dividend_config,
        ipo_type=ipo_type.value,
        ipo_date=datetime.utcnow(),
        ipo_valuation=total_valuation,
        fixed_dividend_rate=config.get("fixed_dividend_rate"),
        conversion_ratio=config.get("conversion_ratio"),
        liquidation_preference=config.get("liquidation_preference"),
        is_callable=config.get("callable", False)
    )
    
    db.add(company)
    db.commit()
    db.refresh(company)
    
    from auth import Player, get_db as get_auth_db
    auth_db = get_auth_db()
    try:
        founder = auth_db.query(Player).filter(Player.id == founder_id).first()
        if founder:
            founder.cash_balance += total_cost
            auth_db.commit()
    finally:
        auth_db.close()
    
    founder_shares = total_shares - shares_to_offer
    if founder_shares > 0:
        founder_position = ShareholderPosition(
            player_id=founder_id,
            company_shares_id=company.id,
            shares_owned=founder_shares,
            shares_available_to_lend=founder_shares,
            average_cost_basis=0.0
        )
        db.add(founder_position)
    
    firm_position = ShareholderPosition(
        player_id=BANK_PLAYER_ID,
        company_shares_id=company.id,
        shares_owned=shares_to_offer,
        shares_available_to_lend=shares_to_offer,
        average_cost_basis=discounted_price
    )
    db.add(firm_position)
    db.commit()
    
    try:
        from banks.brokerage_order_book import place_limit_order, OrderSide
        place_limit_order(
            player_id=BANK_PLAYER_ID,
            company_shares_id=company.id,
            side=OrderSide.SELL,
            quantity=shares_to_offer,
            limit_price=share_price
        )
    except ImportError:
        pass
    
    underwriting_profit = shares_to_offer * share_price * discount_rate
    firm_add_cash(underwriting_profit, "underwriting_fee", f"Spread: {ticker_symbol}", founder_id, company.id)
    
    modify_credit_score(founder_id, "ipo_completed")
    
    print(f"[{BANK_NAME}] 🎉 {ipo_type.value.upper()}: {ticker_symbol}")
    
    return company


def _process_dual_class_ipo(db, founder_id, company_name, ticker_symbol, config,
                             shares_to_offer, total_shares, share_price,
                             dividend_config, total_valuation):
    discount_rate = config.get("discount_rate", 0.08)
    discounted_price = share_price * (1 - discount_rate)
    total_cost = shares_to_offer * discounted_price
    
    if not firm_deduct_cash(total_cost, "underwriting_cost", f"Dual-class {ticker_symbol}"):
        return None
    
    class_b_shares = shares_to_offer
    class_a_shares = total_shares - shares_to_offer
    
    founder_votes = class_a_shares * 10
    public_votes = class_b_shares * 1
    total_votes = founder_votes + public_votes
    founder_voting_pct = founder_votes / total_votes
    
    min_control = config.get("founder_control_minimum", 0.51)
    if founder_voting_pct < min_control:
        return None
    
    company = CompanyShares(
        founder_id=founder_id,
        business_id=0,
        company_name=company_name,
        ticker_symbol=ticker_symbol,
        share_class=ShareClass.CLASS_B.value,
        total_shares_authorized=total_shares,
        shares_outstanding=total_shares,
        shares_held_by_founder=class_a_shares,
        shares_held_by_firm=class_b_shares,
        shares_in_float=0,
        founder_class_a_shares=class_a_shares,
        current_price=share_price,
        ipo_price=share_price,
        high_52_week=share_price,
        low_52_week=share_price,
        dividend_config=dividend_config or [],
        ipo_type=IPOType.DUAL_CLASS.value,
        ipo_date=datetime.utcnow(),
        ipo_valuation=total_valuation,
        is_dual_class=True
    )
    
    db.add(company)
    db.commit()
    db.refresh(company)
    
    from auth import Player, get_db as get_auth_db
    auth_db = get_auth_db()
    try:
        founder = auth_db.query(Player).filter(Player.id == founder_id).first()
        if founder:
            founder.cash_balance += total_cost
            auth_db.commit()
    finally:
        auth_db.close()
    
    if class_a_shares > 0:
        founder_position = ShareholderPosition(
            player_id=founder_id,
            company_shares_id=company.id,
            shares_owned=class_a_shares,
            shares_available_to_lend=0,
            average_cost_basis=0.0
        )
        db.add(founder_position)
    
    firm_position = ShareholderPosition(
        player_id=BANK_PLAYER_ID,
        company_shares_id=company.id,
        shares_owned=class_b_shares,
        shares_available_to_lend=class_b_shares,
        average_cost_basis=discounted_price
    )
    db.add(firm_position)
    db.commit()
    
    try:
        from banks.brokerage_order_book import place_limit_order, OrderSide
        place_limit_order(
            player_id=BANK_PLAYER_ID,
            company_shares_id=company.id,
            side=OrderSide.SELL,
            quantity=class_b_shares,
            limit_price=share_price
        )
    except ImportError:
        pass
    
    underwriting_profit = shares_to_offer * share_price * discount_rate
    firm_add_cash(underwriting_profit, "underwriting_fee", f"Dual-class: {ticker_symbol}", founder_id, company.id)
    
    modify_credit_score(founder_id, "ipo_completed")
    
    print(f"[{BANK_NAME}] 🎉 DUAL-CLASS: {ticker_symbol} (founder {founder_voting_pct*100:.0f}% voting)")
    
    return company


def create_ipo(founder_id, business_id, ipo_type, shares_to_offer, total_shares,
               share_class, company_name, ticker_symbol, dividend_config, target_player_id=None):
    """Legacy IPO function for compatibility."""
    return create_player_ipo(
        founder_id=founder_id,
        company_name=company_name,
        ticker_symbol=ticker_symbol,
        ipo_type=ipo_type,
        shares_to_offer=shares_to_offer,
        total_shares=total_shares,
        share_class=share_class,
        dividend_config=dividend_config
    )


# ==========================
# MARGIN TRADING
# ==========================

def calculate_margin_multiplier(buyer_id: int, company_shares_id: int, seller_id: int = None) -> float:
    max_leverage = get_max_leverage_for_player(buyer_id)
    
    volatility = calculate_stock_volatility(company_shares_id)
    if volatility > 0.30:
        max_leverage *= 0.5
    elif volatility > 0.15:
        max_leverage *= 0.75
    
    return min(max_leverage, MAX_MARGIN_MULTIPLIER)


def check_margin_calls():
    db = get_db()
    try:
        positions = db.query(ShareholderPosition).filter(
            ShareholderPosition.margin_debt > 0
        ).all()
        
        for position in positions:
            company = db.query(CompanyShares).filter(
                CompanyShares.id == position.company_shares_id
            ).first()
            
            if not company:
                continue
            
            position_value = position.shares_owned * company.current_price
            equity = position_value - position.margin_debt
            equity_ratio = equity / position_value if position_value > 0 else 0
            
            if equity_ratio < MARGIN_MAINTENANCE_RATIO:
                required_equity = position_value * MARGIN_MAINTENANCE_RATIO
                shortfall = required_equity - equity
                
                existing_call = db.query(MarginCall).filter(
                    MarginCall.player_id == position.player_id,
                    MarginCall.is_resolved == False
                ).first()
                
                if not existing_call:
                    call = MarginCall(
                        player_id=position.player_id,
                        amount_required=shortfall,
                        deadline=datetime.utcnow() + timedelta(hours=24)
                    )
                    db.add(call)
                    modify_credit_score(position.player_id, "margin_call_triggered")
        
        db.commit()
    finally:
        db.close()


def process_margin_call_deadlines():
    db = get_db()
    try:
        expired = db.query(MarginCall).filter(
            MarginCall.is_resolved == False,
            MarginCall.deadline < datetime.utcnow()
        ).all()
        
        for call in expired:
            trigger_liquidation(call.player_id, "margin")
            call.is_resolved = True
            call.resolved_at = datetime.utcnow()
            call.resolution_type = "liquidated"
            modify_credit_score(call.player_id, "forced_liquidation")
        
        db.commit()
    finally:
        db.close()


def trigger_liquidation(player_id: int, source: str):
    try:
        from banks.brokerage_order_book import place_market_order, OrderSide
    except ImportError:
        return
    
    db = get_db()
    try:
        positions = db.query(ShareholderPosition).filter(
            ShareholderPosition.player_id == player_id,
            ShareholderPosition.shares_owned > 0
        ).all()
        
        for position in positions:
            company = db.query(CompanyShares).filter(
                CompanyShares.id == position.company_shares_id
            ).first()
            
            if company and position.shares_owned > 0:
                place_market_order(
                    player_id=player_id,
                    company_shares_id=position.company_shares_id,
                    side=OrderSide.SELL,
                    quantity=position.shares_owned
                )
                position.margin_debt = 0
                position.margin_shares = 0
                position.is_margin_position = False
        
        db.commit()
    finally:
        db.close()


def accrue_margin_interest():
    db = get_db()
    try:
        positions = db.query(ShareholderPosition).filter(
            ShareholderPosition.margin_debt > 0
        ).all()
        
        now = datetime.utcnow()
        total_interest = 0.0
        
        for position in positions:
            if position.last_interest_accrual:
                hours = (now - position.last_interest_accrual).total_seconds() / 3600
            else:
                hours = 1
            
            if hours < 1:
                continue
            
            annual_rate = get_credit_interest_rate(position.player_id)
            hourly_rate = annual_rate / (365 * 24)
            
            interest = position.margin_debt * hourly_rate * hours
            position.margin_interest_accrued += interest
            position.margin_debt += interest
            position.last_interest_accrual = now
            
            total_interest += interest
        
        if total_interest > 0:
            firm_add_cash(total_interest, "margin_interest", "Margin interest accrual")
        
        db.commit()
    finally:
        db.close()


# ==========================
# SHORT SELLING
# ==========================

def short_sell_shares(borrower_id: int, company_shares_id: int, quantity: int) -> Optional[ShareLoan]:
    db = get_db()
    try:
        firm = get_firm_entity()
        if not firm.is_accepting_shorts:
            return None
        
        company = db.query(CompanyShares).filter(
            CompanyShares.id == company_shares_id,
            CompanyShares.is_delisted == False
        ).first()
        
        if not company or company.trading_halted:
            return None
        
        lenders = db.query(ShareholderPosition).filter(
            ShareholderPosition.company_shares_id == company_shares_id,
            ShareholderPosition.shares_available_to_lend >= quantity,
            ShareholderPosition.player_id != borrower_id
        ).all()
        
        if not lenders:
            return None
        
        lender_position = lenders[0]
        
        borrow_value = quantity * company.current_price
        collateral_required = borrow_value * SHORT_COLLATERAL_REQUIREMENT
        annual_rate = get_short_borrow_rate(borrower_id)
        weekly_rate = annual_rate / 52
        
        volatility = calculate_stock_volatility(company_shares_id)
        if volatility > 0.20:
            due_days = 7
        elif volatility > 0.10:
            due_days = 14
        else:
            due_days = 30
        
        due_date = datetime.utcnow() + timedelta(days=due_days)
        
        from auth import Player, get_db as get_auth_db
        auth_db = get_auth_db()
        try:
            borrower = auth_db.query(Player).filter(Player.id == borrower_id).first()
            if not borrower or borrower.cash_balance < collateral_required:
                return None
            
            borrower.cash_balance -= collateral_required
            auth_db.commit()
        finally:
            auth_db.close()
        
        lender_position.shares_available_to_lend -= quantity
        lender_position.shares_lent_out += quantity
        
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
        
        return loan
    
    except Exception as e:
        print(f"[{BANK_NAME}] Short error: {e}")
        return None
    finally:
        db.close()


def close_short_position(loan_id: int) -> bool:
    try:
        from banks.brokerage_order_book import place_market_order, OrderSide
    except ImportError:
        return False
    
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
        
        borrower_position = db.query(ShareholderPosition).filter(
            ShareholderPosition.player_id == loan.borrower_player_id,
            ShareholderPosition.company_shares_id == loan.company_shares_id
        ).first()
        
        has_shares = borrower_position and borrower_position.shares_owned >= loan.shares_borrowed
        
        from auth import Player, get_db as get_auth_db
        
        if not has_shares:
            auth_db = get_auth_db()
            try:
                borrower = auth_db.query(Player).filter(Player.id == loan.borrower_player_id).first()
                if borrower:
                    borrower.cash_balance += loan.collateral_locked
                    auth_db.commit()
            finally:
                auth_db.close()
            
            success = place_market_order(
                player_id=loan.borrower_player_id,
                company_shares_id=loan.company_shares_id,
                side=OrderSide.BUY,
                quantity=loan.shares_borrowed
            )
            
            if not success:
                auth_db = get_auth_db()
                try:
                    borrower = auth_db.query(Player).filter(Player.id == loan.borrower_player_id).first()
                    if borrower:
                        borrower.cash_balance -= loan.collateral_locked
                        auth_db.commit()
                finally:
                    auth_db.close()
                return False
        else:
            borrower_position.shares_owned -= loan.shares_borrowed
            
            auth_db = get_auth_db()
            try:
                borrower = auth_db.query(Player).filter(Player.id == loan.borrower_player_id).first()
                if borrower:
                    borrower.cash_balance += loan.collateral_locked
                    auth_db.commit()
            finally:
                auth_db.close()
        
        lender_position = db.query(ShareholderPosition).filter(
            ShareholderPosition.player_id == loan.lender_player_id,
            ShareholderPosition.company_shares_id == loan.company_shares_id
        ).first()
        
        if lender_position:
            lender_position.shares_lent_out -= loan.shares_borrowed
            lender_position.shares_available_to_lend += loan.shares_borrowed
        
        original_value = loan.shares_borrowed * loan.borrow_price
        current_value = loan.shares_borrowed * company.current_price
        pnl = original_value - current_value - loan.total_fees_paid
        
        loan.status = ShareLoanStatus.RETURNED.value
        loan.returned_at = datetime.utcnow()
        
        db.commit()
        
        if pnl > 0:
            modify_credit_score(loan.borrower_player_id, "short_position_profitable")
        else:
            modify_credit_score(loan.borrower_player_id, "short_position_loss")
        
        return True
    
    except Exception as e:
        print(f"[{BANK_NAME}] Close short error: {e}")
        return False
    finally:
        db.close()


def process_share_loan_interest():
    db = get_db()
    try:
        loans = db.query(ShareLoan).filter(
            ShareLoan.status == ShareLoanStatus.ACTIVE.value
        ).all()
        
        now = datetime.utcnow()
        
        for loan in loans:
            days = (now - loan.last_interest_charge).total_seconds() / (24 * 3600)
            if days < 1:
                continue
            
            weekly_fee = loan.shares_borrowed * loan.borrow_price * loan.borrow_rate_weekly
            daily_fee = weekly_fee / 7
            fee = daily_fee * days
            
            if loan.collateral_locked >= fee:
                loan.collateral_locked -= fee
                loan.total_fees_paid += fee
                
                fee_to_lender = fee * (1 - SHORT_FEE_FIRM_SPLIT)
                fee_to_firm = fee * SHORT_FEE_FIRM_SPLIT
                
                loan.fees_to_lender += fee_to_lender
                loan.fees_to_firm += fee_to_firm
                loan.last_interest_charge = now
                
                from auth import Player, get_db as get_auth_db
                auth_db = get_auth_db()
                try:
                    lender = auth_db.query(Player).filter(Player.id == loan.lender_player_id).first()
                    if lender:
                        lender.cash_balance += fee_to_lender
                        auth_db.commit()
                finally:
                    auth_db.close()
                
                firm_add_cash(fee_to_firm, "short_borrow_fee", f"Borrow fee", loan.borrower_player_id)
        
        db.commit()
    finally:
        db.close()


# ==========================
# COMMODITY LENDING (SCCE)
# ==========================

def list_commodity_for_lending(lender_id: int, item_type: str, quantity: float, weekly_rate: float) -> Optional[CommodityListing]:
    try:
        import inventory
        available = inventory.get_item_quantity(lender_id, item_type)
        
        if available < quantity:
            return None
    except Exception as e:
        return None
    
    db = get_db()
    try:
        existing = db.query(CommodityListing).filter(
            CommodityListing.lender_player_id == lender_id,
            CommodityListing.item_type == item_type,
            CommodityListing.is_active == True
        ).first()
        
        if existing:
            existing.quantity_available += quantity
            existing.weekly_rate = weekly_rate
            db.commit()
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
        
        return listing
    finally:
        db.close()


def borrow_commodity(borrower_id: int, listing_id: int, quantity: float) -> Optional[CommodityLoan]:
    db = get_db()
    try:
        firm = get_firm_entity()
        if not firm.is_accepting_lending:
            return None
        
        listing = db.query(CommodityListing).filter(
            CommodityListing.id == listing_id,
            CommodityListing.is_active == True
        ).first()
        
        if not listing:
            return None
        
        if listing.quantity_available - listing.quantity_lent_out < quantity:
            return None
        
        if listing.lender_player_id == borrower_id:
            return None
        
        try:
            import market as market_mod
            market_price = market_mod.get_market_price(listing.item_type) or 1.0
        except ImportError:
            market_price = 1.0
        
        borrow_value = quantity * market_price
        collateral_required = borrow_value * COMMODITY_COLLATERAL_REQUIREMENT
        due_date = calculate_commodity_due_date(listing.item_type, borrower_id)
        
        weeks = max(1, (due_date - datetime.utcnow()).days / 7)
        total_fee = borrow_value * listing.weekly_rate * weeks
        fee_to_lender = total_fee * (1 - COMMODITY_LENDING_FEE_SPLIT)
        fee_to_firm = total_fee * COMMODITY_LENDING_FEE_SPLIT
        
        from auth import Player, get_db as get_auth_db
        auth_db = get_auth_db()
        try:
            borrower = auth_db.query(Player).filter(Player.id == borrower_id).first()
            if not borrower or borrower.cash_balance < collateral_required + total_fee:
                return None
            
            borrower.cash_balance -= (collateral_required + total_fee)
            auth_db.commit()
        finally:
            auth_db.close()
        
        try:
            import inventory
            
            if not inventory.remove_item(listing.lender_player_id, listing.item_type, quantity):
                auth_db = get_auth_db()
                try:
                    borrower = auth_db.query(Player).filter(Player.id == borrower_id).first()
                    if borrower:
                        borrower.cash_balance += collateral_required + total_fee
                        auth_db.commit()
                finally:
                    auth_db.close()
                return None
            
            inventory.add_item(borrower_id, listing.item_type, quantity)
        except Exception as e:
            return None
        
        auth_db = get_auth_db()
        try:
            lender = auth_db.query(Player).filter(Player.id == listing.lender_player_id).first()
            if lender:
                lender.cash_balance += fee_to_lender
                auth_db.commit()
        finally:
            auth_db.close()
        
        firm_add_cash(fee_to_firm, "lending_fee", f"Commodity: {listing.item_type}", borrower_id)
        
        listing.quantity_lent_out += quantity
        
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
        
        return loan
    
    except Exception as e:
        print(f"[{BANK_NAME}] Borrow error: {e}")
        return None
    finally:
        db.close()


def return_commodity(loan_id: int) -> bool:
    db = get_db()
    try:
        loan = db.query(CommodityLoan).filter(
            CommodityLoan.id == loan_id,
            CommodityLoan.status.in_([CommodityLoanStatus.ACTIVE.value, CommodityLoanStatus.LATE.value])
        ).first()
        
        if not loan:
            return False
        
        try:
            import inventory
            available = inventory.get_item_quantity(loan.borrower_player_id, loan.item_type)
            
            if available < loan.quantity_borrowed:
                return False
        except:
            return False
        
        try:
            import inventory
            inventory.remove_item(loan.borrower_player_id, loan.item_type, loan.quantity_borrowed)
            inventory.add_item(loan.lender_player_id, loan.item_type, loan.quantity_borrowed)
        except Exception as e:
            return False
        
        from auth import Player, get_db as get_auth_db
        auth_db = get_auth_db()
        try:
            borrower = auth_db.query(Player).filter(Player.id == loan.borrower_player_id).first()
            if borrower:
                borrower.cash_balance += loan.collateral_locked
                auth_db.commit()
        finally:
            auth_db.close()
        
        listing = db.query(CommodityListing).filter(
            CommodityListing.id == loan.listing_id
        ).first()
        if listing:
            listing.quantity_lent_out -= loan.quantity_borrowed
        
        loan.status = CommodityLoanStatus.RETURNED.value
        loan.returned_at = datetime.utcnow()
        
        db.commit()
        
        if loan.days_late > 0:
            modify_credit_score(loan.borrower_player_id, "commodity_returned_late")
        else:
            modify_credit_score(loan.borrower_player_id, "commodity_returned_on_time")
        
        return True
    
    except Exception as e:
        return False
    finally:
        db.close()


def extend_commodity_loan(loan_id: int) -> bool:
    db = get_db()
    try:
        loan = db.query(CommodityLoan).filter(
            CommodityLoan.id == loan_id,
            CommodityLoan.status == CommodityLoanStatus.ACTIVE.value
        ).first()
        
        if not loan or loan.extensions_used >= loan.max_extensions:
            return False
        
        try:
            import market as market_mod
            current_price = market_mod.get_market_price(loan.item_type) or loan.borrow_price
        except ImportError:
            current_price = loan.borrow_price
        
        current_value = loan.quantity_borrowed * current_price
        extension_fee = current_value * loan.weekly_rate * 1.5
        fee_to_lender = extension_fee * (1 - COMMODITY_LENDING_FEE_SPLIT)
        fee_to_firm = extension_fee * COMMODITY_LENDING_FEE_SPLIT
        
        from auth import Player, get_db as get_auth_db
        auth_db = get_auth_db()
        try:
            borrower = auth_db.query(Player).filter(Player.id == loan.borrower_player_id).first()
            if not borrower or borrower.cash_balance < extension_fee:
                return False
            
            borrower.cash_balance -= extension_fee
            auth_db.commit()
        finally:
            auth_db.close()
        
        auth_db = get_auth_db()
        try:
            lender = auth_db.query(Player).filter(Player.id == loan.lender_player_id).first()
            if lender:
                lender.cash_balance += fee_to_lender
                auth_db.commit()
        finally:
            auth_db.close()
        
        firm_add_cash(fee_to_firm, "extension_fee", f"Extension: {loan.item_type}", loan.borrower_player_id)
        
        new_due = calculate_commodity_due_date(loan.item_type, loan.borrower_player_id)
        loan.due_date = new_due
        loan.extensions_used += 1
        loan.total_fees_paid += extension_fee
        loan.fees_to_lender += fee_to_lender
        loan.fees_to_firm += fee_to_firm
        
        db.commit()
        
        return True
    
    except Exception as e:
        return False
    finally:
        db.close()


def calculate_commodity_due_date(item_type: str, borrower_id: int) -> datetime:
    base_hours = 168
    
    volatility = calculate_commodity_volatility(item_type)
    if volatility > 0.30:
        base_hours = 24
    elif volatility > 0.15:
        base_hours = 48
    elif volatility > 0.08:
        base_hours = 96
    
    credit = get_player_credit(borrower_id)
    if credit.credit_score > 85:
        base_hours *= 1.5
    elif credit.credit_score < 40:
        base_hours *= 0.5
    
    base_hours = max(12, min(336, base_hours))
    
    return datetime.utcnow() + timedelta(hours=base_hours)


def check_commodity_loan_due_dates():
    db = get_db()
    try:
        overdue = db.query(CommodityLoan).filter(
            CommodityLoan.status == CommodityLoanStatus.ACTIVE.value,
            CommodityLoan.due_date < datetime.utcnow()
        ).all()
        
        for loan in overdue:
            loan.status = CommodityLoanStatus.LATE.value
            loan.days_late += 1
            
            late_fee = loan.collateral_locked * LATE_FEE_DAILY_RATE
            fee_to_lender = late_fee * (1 - COMMODITY_LENDING_FEE_SPLIT)
            fee_to_firm = late_fee * COMMODITY_LENDING_FEE_SPLIT
            
            if loan.collateral_locked >= late_fee:
                loan.collateral_locked -= late_fee
                loan.late_fees_paid += late_fee
                
                from auth import Player, get_db as get_auth_db
                auth_db = get_auth_db()
                try:
                    lender = auth_db.query(Player).filter(Player.id == loan.lender_player_id).first()
                    if lender:
                        lender.cash_balance += fee_to_lender
                        auth_db.commit()
                finally:
                    auth_db.close()
                
                firm_add_cash(fee_to_firm, "late_fee", f"Late: {loan.item_type}", loan.borrower_player_id)
            
            if loan.days_late >= MAX_LATE_DAYS_BEFORE_FORCE_CLOSE:
                force_close_commodity_loan(loan.id)
        
        db.commit()
    finally:
        db.close()


def force_close_commodity_loan(loan_id: int):
    db = get_db()
    try:
        loan = db.query(CommodityLoan).filter(CommodityLoan.id == loan_id).first()
        
        if not loan:
            return
        
        try:
            import market as market_mod
            current_price = market_mod.get_market_price(loan.item_type) or loan.borrow_price * 1.5
        except ImportError:
            current_price = loan.borrow_price * 1.5
        
        buy_cost = loan.quantity_borrowed * current_price
        
        if loan.collateral_locked >= buy_cost:
            remaining = loan.collateral_locked - buy_cost
            
            try:
                import inventory
                inventory.add_item(loan.lender_player_id, loan.item_type, loan.quantity_borrowed)
            except:
                pass
            
            if remaining > 0:
                from auth import Player, get_db as get_auth_db
                auth_db = get_auth_db()
                try:
                    borrower = auth_db.query(Player).filter(Player.id == loan.borrower_player_id).first()
                    if borrower:
                        borrower.cash_balance += remaining
                        auth_db.commit()
                finally:
                    auth_db.close()
            
            loan.status = CommodityLoanStatus.FORCE_CLOSED.value
        else:
            shortfall = buy_cost - loan.collateral_locked
            create_lien(loan.borrower_player_id, shortfall, "commodity")
            loan.status = CommodityLoanStatus.DEFAULTED.value
            modify_credit_score(loan.borrower_player_id, "commodity_defaulted")
        
        listing = db.query(CommodityListing).filter(CommodityListing.id == loan.listing_id).first()
        if listing:
            listing.quantity_lent_out -= loan.quantity_borrowed
        
        db.commit()
    finally:
        db.close()


def create_lien(player_id: int, amount: float, source: str):
    db = get_db()
    try:
        lien = db.query(BrokerageLien).filter(
            BrokerageLien.player_id == player_id,
            BrokerageLien.source == source
        ).first()
        
        if lien:
            lien.principal += amount
        else:
            lien = BrokerageLien(player_id=player_id, principal=amount, source=source)
            db.add(lien)
        
        db.commit()
        modify_credit_score(player_id, "lien_created")
    finally:
        db.close()


def process_liens():
    db = get_db()
    try:
        liens = db.query(BrokerageLien).all()
        
        for lien in liens:
            if lien.total_owed <= 0:
                continue
            
            interest_rate = get_credit_interest_rate(lien.player_id) / 525600
            lien.interest_accrued += lien.total_owed * interest_rate
            lien.last_interest_accrual = datetime.utcnow()
            
            from auth import Player, get_db as get_auth_db
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
                        
                        firm_add_cash(garnish, "lien_payment", f"Garnishment", lien.player_id)
                        
                        if lien.total_owed <= 0:
                            modify_credit_score(lien.player_id, "lien_paid_off")
            finally:
                auth_db.close()
        
        db.commit()
    finally:
        db.close()


# ==========================
# DIVIDEND PROCESSING
# ==========================

def process_dividends(current_tick: int):
    db = get_db()
    try:
        companies = db.query(CompanyShares).filter(CompanyShares.is_delisted == False).all()
        
        for company in companies:
            if not company.dividend_config:
                continue
            
            for div_config in company.dividend_config:
                div_type = div_config.get("type", "cash")
                frequency = div_config.get("frequency", "monthly")
                
                freq_ticks = {
                    "daily": 86400,
                    "weekly": 604800,
                    "biweekly": 1209600,
                    "monthly": 2592000,
                    "quarterly": 7776000
                }.get(frequency, 2592000)
                
                if current_tick % freq_ticks != 0:
                    continue
                
                if div_type == "cash":
                    _process_cash_dividend(company, div_config, db)
                elif div_type == "commodity":
                    _process_commodity_dividend(company, div_config, db)
                elif div_type == "scrip":
                    _process_scrip_dividend(company, div_config, db)
        
        db.commit()
    finally:
        db.close()


def _process_cash_dividend(company, config, db):
    from auth import Player, get_db as get_auth_db
    
    amount_per_share = config.get("amount", 0.01)
    total_dividend = amount_per_share * company.shares_outstanding
    
    auth_db = get_auth_db()
    try:
        founder = auth_db.query(Player).filter(Player.id == company.founder_id).first()
        
        if not founder or founder.cash_balance < total_dividend:
            company.consecutive_dividend_payouts = 0
            company.dividend_warning_active = True
            company.last_dividend_warning = datetime.utcnow()
            modify_credit_score(company.founder_id, "dividend_missed")
            return
        
        founder.cash_balance -= total_dividend
        auth_db.commit()
    finally:
        auth_db.close()
    
    positions = db.query(ShareholderPosition).filter(
        ShareholderPosition.company_shares_id == company.id,
        ShareholderPosition.shares_owned > 0
    ).all()
    
    for position in positions:
        dividend_amount = position.shares_owned * amount_per_share
        
        if dividend_amount < 0.01:
            continue
        
        auth_db = get_auth_db()
        try:
            player = auth_db.query(Player).filter(Player.id == position.player_id).first()
            if player:
                player.cash_balance += dividend_amount
                auth_db.commit()
        finally:
            auth_db.close()
    
    company.consecutive_dividend_payouts += 1
    company.last_dividend_date = datetime.utcnow()
    company.dividend_warning_active = False
    
    modify_credit_score(company.founder_id, "dividend_paid")


def _process_commodity_dividend(company, config, db):
    try:
        import inventory
    except ImportError:
        return
    
    item = config.get("item")
    amount = config.get("amount", 1)
    per_shares = config.get("per_shares", 100)
    
    positions = db.query(ShareholderPosition).filter(
        ShareholderPosition.company_shares_id == company.id,
        ShareholderPosition.shares_owned > 0
    ).all()
    
    total_needed = sum((pos.shares_owned // per_shares) * amount for pos in positions)
    
    founder_qty = inventory.get_item_quantity(company.founder_id, item)
    
    if founder_qty < total_needed:
        company.dividend_warning_active = True
        company.last_dividend_warning = datetime.utcnow()
        modify_credit_score(company.founder_id, "dividend_missed")
        return
    
    for position in positions:
        units = (position.shares_owned // per_shares) * amount
        if units >= 1:
            inventory.remove_item(company.founder_id, item, units)
            inventory.add_item(position.player_id, item, units)
    
    company.consecutive_dividend_payouts += 1
    company.dividend_warning_active = False
    company.last_dividend_date = datetime.utcnow()
    modify_credit_score(company.founder_id, "dividend_paid")


def _process_scrip_dividend(company, config, db):
    ratio = config.get("ratio", 0.01)
    
    positions = db.query(ShareholderPosition).filter(
        ShareholderPosition.company_shares_id == company.id,
        ShareholderPosition.shares_owned > 0
    ).all()
    
    total_new_shares = 0
    
    for position in positions:
        new_shares = int(position.shares_owned * ratio)
        if new_shares > 0:
            position.shares_owned += new_shares
            total_new_shares += new_shares
    
    company.shares_outstanding += total_new_shares
    company.total_shares_authorized += total_new_shares
    company.consecutive_dividend_payouts += 1
    company.last_dividend_date = datetime.utcnow()
    modify_credit_score(company.founder_id, "dividend_paid")


# ==========================
# INITIALIZATION
# ==========================

def initialize():
    print(f"[{BANK_NAME}] Creating database tables...")
    Base.metadata.create_all(bind=engine)
    
    try:
        from banks import brokerage_order_book
        brokerage_order_book.initialize()
    except ImportError:
        pass
    
    try:
        from corporate_actions import initialize as init_corporate_actions
        init_corporate_actions()
    except ImportError:
        pass
    
    firm = get_firm_entity()
    
    print(f"[{BANK_NAME}] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"[{BANK_NAME}] SYMCO BROKERAGE FIRM - INITIALIZED")
    print(f"[{BANK_NAME}] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"[{BANK_NAME}] Cash Reserves: ${firm.cash_reserves:,.2f}")
    print(f"[{BANK_NAME}] IPO Types: {len(IPO_CONFIG)}")
    print(f"[{BANK_NAME}]   • Direct Listing ($5k flat)")
    print(f"[{BANK_NAME}]   • Firm Underwritten (7% spread)")
    print(f"[{BANK_NAME}]   • Preferred Stock (8% fixed dividend)")
    print(f"[{BANK_NAME}]   • Series A Growth (1.5x convertible)")
    print(f"[{BANK_NAME}]   • Series B Income (12% fixed dividend)")
    print(f"[{BANK_NAME}]   • Dual-Class (10x voting control)")
    print(f"[{BANK_NAME}] SCCE Commodity Lending: ACTIVE")
    print(f"[{BANK_NAME}] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


# ==========================
# TICK HANDLER
# ==========================

async def tick(current_tick: int, now: datetime, bank_entity=None):
    try:
        from banks import brokerage_order_book
        brokerage_order_book.tick(current_tick)
    except ImportError:
        pass
    
    process_liens()
    
    if current_tick % 300 == 0:
        check_margin_calls()
        process_margin_call_deadlines()
        check_commodity_loan_due_dates()
    
    if current_tick % 3600 == 0:
        accrue_margin_interest()
        process_share_loan_interest()
        check_firm_can_operate()
        
        try:
            from corporate_actions import process_corporate_actions
            process_corporate_actions()
        except ImportError:
            pass
    
    process_dividends(current_tick)
    
    if current_tick % 3600 == 0:
        firm = get_firm_entity()
        
        db = get_db()
        try:
            company_count = db.query(CompanyShares).filter(CompanyShares.is_delisted == False).count()
            margin_count = db.query(ShareholderPosition).filter(ShareholderPosition.margin_debt > 0).count()
            short_count = db.query(ShareLoan).filter(ShareLoan.status == ShareLoanStatus.ACTIVE.value).count()
            commodity_count = db.query(CommodityLoan).filter(
                CommodityLoan.status.in_([CommodityLoanStatus.ACTIVE.value, CommodityLoanStatus.LATE.value])
            ).count()
        finally:
            db.close()
        
        status = "✓ OPERATIONAL" if firm_is_solvent() else "✗ LOW RESERVES"
        print(f"[{BANK_NAME}] {status} | Cash: ${firm.cash_reserves:,.2f} | " +
              f"Companies: {company_count} | Margin: {margin_count} | " +
              f"Shorts: {short_count} | Commodity Loans: {commodity_count}")


# ==========================
# PUBLIC API
# ==========================

__all__ = [
    'BANK_ID', 'BANK_NAME', 'BANK_DESCRIPTION', 'BANK_PLAYER_ID',
    'EQUITY_TRADE_COMMISSION', 'MIN_COMMISSION',
    'COLLATERAL_REQUIREMENT', 'COMMODITY_COLLATERAL_REQUIREMENT',
    'LENDING_FEE_SPLIT', 'COMMODITY_LENDING_FEE_SPLIT',
    'LATE_FEE_DAILY_RATE', 'MAX_LATE_DAYS_BEFORE_FORCE_CLOSE',
    'initialize', 'tick',
    'get_db', 'Base',
    'get_firm_entity', 'firm_add_cash', 'firm_deduct_cash', 'firm_is_solvent', 'FirmEntity',
    'get_player_credit', 'modify_credit_score', 'get_credit_tier',
    'get_credit_interest_rate', 'get_max_leverage_for_player',
    'PlayerCreditRating', 'CreditTier',
    'calculate_player_total_net_worth', 'calculate_player_company_valuation',
    'calculate_business_valuation',
    'create_player_ipo', 'create_ipo', 'IPOType', 'IPO_CONFIG', 'ShareClass',
    'calculate_margin_multiplier', 'record_price',
    'calculate_stock_volatility', 'calculate_commodity_volatility',
    'short_sell_shares', 'close_short_position',
    'list_commodity_for_lending', 'borrow_commodity', 'return_commodity',
    'extend_commodity_loan', 'calculate_commodity_due_date',
    'CompanyShares', 'ShareholderPosition', 'ShareLoan',
    'CommodityListing', 'CommodityLoan', 'BrokerageLien',
    'PriceHistory', 'MarginCall', 'FirmTransaction',
    'DividendType', 'DividendFrequency', 'ShareLoanStatus',
    'CommodityLoanStatus', 'LiquidationLevel',
]
