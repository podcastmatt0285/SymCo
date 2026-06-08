"""
banks/brokerage_firm.py - THE WADSWORTH BROKERAGE FIRM

A comprehensive financial intermediary providing:

WPE (Wadsworth Player Exchange):
- Player company IPOs with 6 different offering structures
- Multiple share classes (Common, Preferred, Series A/B, Dual-Class)
- Margin trading with credit-based leverage (2x-10x)
- Short selling with borrow fees
- Real-time order book with price discovery

WCE (Wadsworth Commodities Exchange):
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

from sqlalchemy import Column, String, Float, DateTime, Integer, BigInteger, Boolean, JSON, ForeignKey, text, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# ==========================
# DATABASE SETUP
# ==========================
from database import engine, SessionLocal
Base = declarative_base()

# ==========================
# BANK IDENTITY
# ==========================
BANK_ID = "brokerage_firm"
BANK_NAME = "Wadsworth Brokerage Firm"
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
# Maximum fraction of a company's float that may be shorted simultaneously
MAX_SHORT_FLOAT_PCT = 0.80

COMMODITY_COLLATERAL_REQUIREMENT = 1.05
COMMODITY_LENDING_FEE_SPLIT = 0.50
LATE_FEE_DAILY_RATE = 0.10
MAX_LATE_DAYS_BEFORE_FORCE_CLOSE = 3

COLLATERAL_REQUIREMENT = COMMODITY_COLLATERAL_REQUIREMENT
LENDING_FEE_SPLIT = COMMODITY_LENDING_FEE_SPLIT

DEFAULT_CREDIT_RATING = 25
CREDIT_RATING_MIN = 0
CREDIT_RATING_MAX = 100

CALL_PREMIUM = 0.05           # 5% premium over current price when calling shares back
CLASS_A_VOTE_MULTIPLIER = 10  # Class A shares count 10× in governance votes
PROPOSAL_DURATION_HOURS = 72  # Governance proposals stay open for 72 hours

# Quad-Class share split (fractions of the offered shares)
QUAD_CLASS_B_FRACTION = 0.60  # 60% voting common
QUAD_CLASS_C_FRACTION = 0.25  # 25% preferred dividend
QUAD_CLASS_D_FRACTION = 0.15  # 15% non-voting equity

# ==========================
# ENUMS
# ==========================

class IPOType(str, Enum):
    DIRECT_LISTING = "direct_listing"
    FIRM_UNDERWRITTEN = "firm_underwritten"
    INCOME_SHARES = "income_shares"
    PREFERRED_OFFERING = "preferred_offering"
    SERIES_A_GROWTH = "series_a_growth"
    SERIES_B_INCOME = "series_b_income"  # legacy stub, no processor
    DUAL_CLASS = "dual_class"
    QUAD_CLASS = "quad_class"


class ShareClass(str, Enum):
    COMMON = "common"
    PREFERRED = "preferred"
    SERIES_A = "series_a"
    SERIES_B = "series_b"
    CLASS_A = "class_a"
    CLASS_B = "class_b"
    CLASS_C = "class_c"
    CLASS_D = "class_d"


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
    RECALLED = "recalled"   # lender-initiated force-close


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
    "short_closed_profit": +3,       # voluntary close, profitable
    "short_closed_loss": -1,         # voluntary close, small loss (market moved against you)
    "short_force_closed": -20,       # collateral exhausted — lender reclaimed position
    # Legacy names kept for any existing credit records that reference them
    "short_returned_on_time": +2,
    "short_returned_late": -5,
    "short_defaulted": -20,
    "short_position_profitable": +2,
    "short_position_loss": -1,
    "commodity_returned_on_time": +3,
    "commodity_returned_late": -5,
    "commodity_defaulted": -20,
    "ipo_completed": +10,
    "dividend_paid": +2,
    "dividend_missed": -5,
    "lien_created": -15,
    "lien_paid_off": +10,
    "margin_trade_profitable": +2,
    "margin_trade_loss": -1,
    "multi_account_detected": -30,
}

IPO_CONFIG = {
    IPOType.DIRECT_LISTING: {
        "name": "Direct Listing",
        "description": "List your shares on the exchange with no underwriter. You pay a flat $5,000 listing fee and place your own sell orders. The market decides the price \u2014 nobody guarantees your shares will sell.",
        "share_class": ShareClass.COMMON,
        "firm_underwritten": False,
        "fee_type": "flat",
        "fee_amount": 5000.00,
        "min_shares": 1000,
        "max_float_pct": 0.80,
        "min_valuation": 25000,
    },
    IPOType.FIRM_UNDERWRITTEN: {
        "name": "Underwritten IPO",
        "description": "The Firm buys your shares upfront at a 7% discount and resells them on the exchange at full price. You get guaranteed capital immediately \u2014 the Firm takes on the risk of finding buyers.",
        "share_class": ShareClass.COMMON,
        "firm_underwritten": True,
        "discount_rate": 0.07,
        "min_shares": 10000,
        "max_float_pct": 0.60,
        "min_valuation": 50000,
    },
    IPOType.INCOME_SHARES: {
        "name": "Income Shares IPO",
        "description": "The Firm buys your shares at only a 3% discount \u2014 the best price available. In exchange, you commit to paying investors a 10% annual dividend every quarter. Miss a payment and your credit score takes a serious hit.",
        "share_class": ShareClass.COMMON,
        "firm_underwritten": True,
        "discount_rate": 0.03,
        "min_shares": 5000,
        "max_float_pct": 0.40,
        "min_valuation": 75000,
        "fixed_dividend_rate": 0.10,
    },
    IPOType.DUAL_CLASS: {
        "name": "Dual-Class IPO",
        "description": "The Firm underwrites a Class B public offering at an 8% discount while you retain all Class A founder shares. Investors get full economic rights; you keep permanent voting control \u2014 no shareholder vote can ever outvote you.",
        "share_class": ShareClass.CLASS_B,
        "firm_underwritten": True,
        "discount_rate": 0.08,
        "min_shares": 10000,
        "max_float_pct": 0.49,
        "min_valuation": 100000,
        "founder_control_minimum": 0.51,
    },
    IPOType.PREFERRED_OFFERING: {
        "name": "Preferred Share Offering",
        "description": "Issue preferred shares with guaranteed quarterly dividends and liquidation priority. The Firm underwrites at only a 5% discount. Preferred shareholders receive 1.5\u00d7 their investment before common shareholders in any liquidation event — and shares are callable if you ever want to buy them back.",
        "share_class": ShareClass.PREFERRED,
        "firm_underwritten": True,
        "discount_rate": 0.05,
        "min_shares": 5000,
        "max_float_pct": 0.40,
        "min_valuation": 50000,
        "fixed_dividend_rate": 0.12,
        "liquidation_preference": 1.5,
        "is_callable": True,
    },
    IPOType.SERIES_A_GROWTH: {
        "name": "Series A Growth Round",
        "description": "A venture-style growth financing round. The Firm takes a 12% underwriting discount \u2014 the steepest of any offering \u2014 but delivers a 20% growth capital bonus on top of standard proceeds. Best for established companies that need a large capital injection to accelerate expansion.",
        "share_class": ShareClass.SERIES_A,
        "firm_underwritten": True,
        "discount_rate": 0.12,
        "growth_bonus_pct": 0.20,
        "min_shares": 10000,
        "max_float_pct": 0.30,
        "min_valuation": 150000,
    },
    IPOType.QUAD_CLASS: {
        "name": "Quad-Class IPO",
        "description": "The most complex offering structure available. Four classes of economic rights: Class A founder super-shares (non-lendable, can't be shorted), Class B public voting common, Class C preferred dividend shares, and Class D non-voting equity. Combines voting insulation, mandatory quarterly dividends, 1.2\u00d7 liquidation priority, and a 15% growth capital injection \u2014 at a 10% underwriting cost.",
        "share_class": ShareClass.CLASS_B,
        "firm_underwritten": True,
        "discount_rate": 0.10,
        "growth_bonus_pct": 0.15,
        "fixed_dividend_rate": 0.10,
        "liquidation_preference": 1.2,
        "founder_control_minimum": 0.40,
        "is_callable": True,
        "min_shares": 20000,
        "max_float_pct": 0.60,
        "min_valuation": 200000,
    },
}

# Lockup duration (days) per IPO type — founder cannot sell before expiry
IPO_LOCKUP_DAYS = {
    "direct_listing":   15,
    "firm_underwritten": 30,
    "income_shares":    30,
    "preferred_offering": 30,
    "dual_class":       60,
    "series_a_growth":  60,
    "quad_class":       90,
}

# Monthly listing fee charged to founder; 3 misses triggers distressed status
MONTHLY_LISTING_FEE = 500.0
LISTING_FEE_DISTRESSED_THRESHOLD = 3

# Sector keywords mapped from business_type key substrings (checked in order)
_SECTOR_KEYWORDS = [
    ("Technology",       ["semiconductor", "quantum", "laser", "data_center", "robotics",
                          "satellite", "radar", "particle", "space_launch", "server_farm",
                          "electronics", "telecom", "fiber", "display", "wbc_chip",
                          "oscillator", "led_fab", "circuit", "solar_panel"]),
    ("Energy",           ["oil_refinery", "oil_well", "refinery", "energy", "solar",
                          "nuclear", "wind_farm", "coal", "petroleum"]),
    ("Mining",           ["mine", "quarry", "alluvial", "mineral_processing",
                          "gem_mine", "lapidary", "crystal_shop", "tallow_works"]),
    ("Agriculture",      ["farm", "orchard", "vineyard", "greenhouse", "plantation",
                          "fishery", "aquaculture", "apiary", "flower_farm", "tea"]),
    ("Food & Beverage",  ["brewery", "winery", "distillery", "bakery", "kitchen",
                          "cannery", "dairy", "slaughterhouse", "smokehouse",
                          "food", "restaurant", "cart", "truck", "coffee"]),
    ("Manufacturing",    ["factory", "plant", "forge", "foundry", "workshop",
                          "mill", "press", "works", "alloy", "chemical",
                          "polymer", "glass", "textile", "paper", "rubber"]),
    ("Healthcare",       ["hospital", "pharmacy", "medical", "clinic", "biotech",
                          "pharmaceutical", "lab", "extract"]),
    ("Retail & Commerce", ["shop", "store", "market", "mall", "boutique", "bazaar",
                           "showroom", "duty_free", "superstore", "warehouse"]),
    ("Finance",          ["bank", "exchange", "fund", "brokerage", "insurance", "mint"]),
    ("Construction",     ["construction", "lumber", "sawmill", "quarry", "cement",
                          "brick", "tile", "plumbing"]),
    ("Transport",        ["transport", "logistics", "port", "shipyard", "dock",
                          "railway", "airline", "freight"]),
    ("Real Estate",      ["estate", "property", "hotel", "resort", "casino"]),
    ("Media & Services", ["studio", "press", "printing", "publishing", "media",
                          "theater", "arena", "service"]),
]

def derive_sector(business_type_key: str) -> str:
    """Return a sector label derived from the business type key."""
    key = (business_type_key or "").lower()
    for sector, keywords in _SECTOR_KEYWORDS:
        if any(kw in key for kw in keywords):
            return sector
    return "General"

# Human-readable descriptions for share classes shown in tooltips
SHARE_CLASS_DESCRIPTIONS = {
    "common":    "1 vote/share · standard economic rights",
    "preferred": "Priority in liquidation (1.5×) · fixed quarterly dividend · callable",
    "series_a":  "Growth-round equity · 1 vote/share · no fixed dividend",
    "class_a":   "Founder super-shares · 10× voting · non-lendable · not shortable",
    "class_b":   "Public voting shares · 1 vote/share · full economic rights",
    "class_c":   "Preferred dividend shares · 0 votes · 1.2× liquidation priority",
    "class_d":   "Non-voting equity · 0 votes · participates in appreciation",
}

# Loyalty tier multipliers applied at dividend time
LOYALTY_TIERS = [
    (90, 1.25, "Long-term holder (90 d)"),
    (30, 1.10, "Established holder (30 d)"),
    (7,  1.00, "Active holder (7 d)"),
    (0,  1.00, "New holder"),
]

def get_loyalty_tier(first_held_at) -> tuple:
    """Return (multiplier, label) for a shareholder based on holding duration."""
    if not first_held_at:
        return 1.00, "New holder"
    days = (datetime.utcnow() - first_held_at).days
    for min_days, mult, label in LOYALTY_TIERS:
        if days >= min_days:
            return mult, label
    return 1.00, "New holder"


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
    
    total_shares_authorized = Column(BigInteger, nullable=False)
    shares_outstanding = Column(BigInteger, default=0)
    shares_held_by_founder = Column(BigInteger, default=0)
    shares_held_by_firm = Column(BigInteger, default=0)
    shares_in_float = Column(BigInteger, default=0)

    founder_class_a_shares = Column(BigInteger, default=0)
    
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
    
    drip_shares_remaining = Column(BigInteger, default=0)
    drip_last_release = Column(DateTime, nullable=True)
    shelf_shares_remaining = Column(BigInteger, default=0)
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

    # Quad-Class sub-records: non-null for Class C / Class D records
    parent_company_id = Column(Integer, nullable=True, index=True)
    share_class_label = Column(String, default="main")  # "main" | "class_c" | "class_d"

    # ── Sector classification (auto-derived at IPO) ──
    sector = Column(String, nullable=True)

    # ── IPO lockup: founder cannot sell before this date ──
    lockup_expires_at = Column(DateTime, nullable=True)

    # ── Profit siphon: auto-divert % of founder revenue → escrow ──
    profit_siphon_rate = Column(Float, default=0.0)       # 0.0–0.10 (0–10 %)
    dividend_escrow_balance = Column(Float, default=0.0)  # accumulated, released by vote

    # ── Monthly listing fee tracking ──
    listing_fee_next_due = Column(DateTime, nullable=True)
    listing_fee_missed_count = Column(Integer, default=0)

    # ── Rolling revenue for earnings display ──
    revenue_7d  = Column(Float, default=0.0)
    revenue_30d = Column(Float, default=0.0)
    revenue_reset_7d  = Column(DateTime, nullable=True)
    revenue_reset_30d = Column(DateTime, nullable=True)

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
    
    # ── Loyalty: when this player first held any shares in this company ──
    first_held_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CompanyEarningsReport(Base):
    """Weekly earnings snapshot for investor visibility."""
    __tablename__ = "company_earnings_reports"

    id = Column(Integer, primary_key=True)
    company_shares_id = Column(Integer, ForeignKey("company_shares.id"), index=True, nullable=False)
    period_end = Column(DateTime, nullable=False)
    period_days = Column(Integer, default=7)

    total_revenue    = Column(Float, default=0.0)
    eps              = Column(Float, default=0.0)   # earnings per share
    payout_ratio     = Column(Float, default=0.0)   # dividends paid / earnings
    dividends_paid   = Column(Float, default=0.0)

    created_at = Column(DateTime, default=datetime.utcnow)


class CompanyProposal(Base):
    """Governance proposal that shareholders vote on."""
    __tablename__ = "company_proposals"

    id = Column(Integer, primary_key=True)
    company_shares_id = Column(Integer, ForeignKey("company_shares.id"), index=True, nullable=False)
    proposer_id = Column(Integer, index=True, nullable=False)

    proposal_type = Column(String, nullable=False)
    # "dividend_change" | "secondary_offering" | "trading_halt" | "custom"
    # "force_dividend_from_escrow"  ← minority protection: ignores 10× founder vote weight
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    # Structured parameter for executable proposals. Stored as a JSON dict.
    # dividend_change:            {"new_rate": 0.08}   (annual rate as decimal)
    # secondary_offering:         {"shares": 50000}    (new shares to add to float)
    # trading_halt:               {"hours": 24}        (duration)
    # force_dividend_from_escrow: {"amount": 10000}    (USD to release from escrow)
    # custom:                     {}
    proposal_param = Column(JSON, nullable=True, default=dict)

    yes_votes = Column(Float, default=0.0)   # weighted vote tally
    no_votes = Column(Float, default=0.0)
    total_voters = Column(Integer, default=0)

    status = Column(String, default="open")  # "open" | "passed" | "rejected" | "cancelled"
    result_applied = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    voting_ends_at = Column(DateTime, nullable=False)


class CompanyVote(Base):
    """A single player's vote on a governance proposal."""
    __tablename__ = "company_votes"

    id = Column(Integer, primary_key=True)
    proposal_id = Column(Integer, ForeignKey("company_proposals.id"), index=True, nullable=False)
    voter_id = Column(Integer, index=True, nullable=False)

    vote = Column(Boolean, nullable=False)   # True = yes, False = no
    voting_power = Column(Float, nullable=False)  # weighted shares at time of vote
    voted_at = Column(DateTime, default=datetime.utcnow)


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
    due_date = Column(DateTime, nullable=True)   # None = no fixed expiry (open-ended)
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
# ANNUITY CONSTANTS & MODELS
# ==========================

ANNUITY_IMMEDIATE_RATES   = {30: 0.08, 90: 0.10, 180: 0.12, 365: 0.15}
ANNUITY_CREDITED_RATE     = 0.05       # deferred accumulation annual growth
ANNUITY_CREDIT_INTERVAL   = 518_400    # ticks between monthly credited-interest credits (~30d)
ANNUITY_ISSUANCE_FEE      = 0.0025     # 0.25% non-qualified purchase fee → government
ANNUITY_NONQUAL_TAX_RATE  = 0.15       # tax on interest portion (non-qualified)
ANNUITY_QUAL_TAX_RATE     = 0.20       # tax on full payment (qualified)
ANNUITY_SURRENDER_SCHEDULE = [0.07, 0.06, 0.05, 0.04, 0.03, 0.02, 0.01, 0.0]
ANNUITY_FREE_WITHDRAWAL_PCT = 0.10     # 10% of value per contract year, no surrender charge
ANNUITY_IMMEDIATE_MIN     = 10_000.0   # min SPIA purchase
ANNUITY_DEFERRED_CONTRIB_MIN = 100.0   # min individual contribution
ANNUITY_MIN_TO_ANNUITIZE  = 5_000.0    # min accumulated value to start payouts
ANNUITY_PAYMENT_TICKS     = {"weekly": 120_960, "monthly": 518_400}
ANNUITY_YEAR_TICKS        = 6_307_200  # 365 × 86400 / 5


class AnnuityContract(Base):
    __tablename__ = "annuity_contracts"
    id                     = Column(Integer, primary_key=True, autoincrement=True)
    player_id              = Column(Integer, index=True, nullable=False)
    annuity_type           = Column(String, nullable=False)   # "immediate" | "deferred"
    is_qualified           = Column(Boolean, default=False)
    phase                  = Column(String, default="accumulation")  # accumulation|payout|completed|surrendered
    # Accumulation phase
    initial_premium        = Column(Float, default=0.0)
    total_contributions    = Column(Float, default=0.0)   # cost basis
    accumulated_value      = Column(Float, default=0.0)
    credited_rate          = Column(Float, default=ANNUITY_CREDITED_RATE)
    next_credit_tick       = Column(BigInteger, nullable=True)
    accumulation_term_days = Column(Integer, nullable=True)   # None = open-ended
    accumulation_end_tick  = Column(BigInteger, nullable=True)
    # Payout phase
    payout_rate            = Column(Float, nullable=True)
    payment_frequency      = Column(String, nullable=True)    # "weekly" | "monthly"
    payment_amount         = Column(Float, nullable=True)
    total_payments         = Column(Integer, nullable=True)
    payments_made          = Column(Integer, default=0)
    payments_remaining     = Column(Integer, nullable=True)
    next_payment_tick      = Column(BigInteger, nullable=True)
    total_paid_out         = Column(Float, default=0.0)
    total_interest_paid    = Column(Float, default=0.0)
    annuitized_at          = Column(DateTime, nullable=True)
    annuitized_value       = Column(Float, nullable=True)
    payout_term_days       = Column(Integer, nullable=True)
    # Surrender / free withdrawal
    free_withdrawal_used   = Column(Float, default=0.0)
    contract_year_tick     = Column(BigInteger, nullable=True)
    # Metadata
    opened_at              = Column(DateTime, default=datetime.utcnow)
    status                 = Column(String, default="active")   # active|completed|surrendered
    surrender_payout       = Column(Float, nullable=True)
    completed_at           = Column(DateTime, nullable=True)


class AnnuityContribution(Base):
    __tablename__ = "annuity_contributions"
    id             = Column(Integer, primary_key=True, autoincrement=True)
    contract_id    = Column(Integer, index=True, nullable=False)
    player_id      = Column(Integer, index=True, nullable=False)
    amount         = Column(Float, nullable=False)
    tick           = Column(BigInteger, nullable=True)
    contributed_at = Column(DateTime, default=datetime.utcnow)


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
            rating = PlayerCreditRating(player_id=player_id, credit_score=DEFAULT_CREDIT_RATING)
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

    base_rate = 0.20
    for t, (_, _, interest_rate, _, _) in CREDIT_TIERS.items():
        if t == tier:
            base_rate = interest_rate
            break

    try:
        from city_projects import get_city_production_buffs
        mult = get_city_production_buffs(player_id).get("loan_interest_multiplier", 1.0)
        base_rate = max(0.01, base_rate * mult)
    except Exception:
        pass
    return base_rate


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


def get_short_interest_multiplier(company_shares_id: int) -> float:
    """Return a borrow-rate multiplier based on short interest as a fraction of float.

    As more of the float is shorted, borrowing becomes progressively more
    expensive — this is what drives short-squeeze dynamics.

    SI %    Multiplier
    <25%    1.0×  (base rate)
    25-50%  1.5×
    50-65%  2.5×
    65-80%  4.0×  (approaching float cap)
    """
    db = get_db()
    try:
        company = db.query(CompanyShares).filter(
            CompanyShares.id == company_shares_id
        ).first()
        if not company or not company.shares_in_float:
            return 1.0
        total_shorted = db.query(func.sum(ShareLoan.shares_borrowed)).filter(
            ShareLoan.company_shares_id == company_shares_id,
            ShareLoan.status == ShareLoanStatus.ACTIVE.value,
        ).scalar() or 0
        si_pct = total_shorted / company.shares_in_float
        if si_pct < 0.25:
            return 1.0
        elif si_pct < 0.50:
            return 1.5
        elif si_pct < 0.65:
            return 2.5
        else:
            return 4.0
    finally:
        db.close()


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
                    from reserve_banks import get_usd_balance
                    breakdown["cash_value"] = get_usd_balance(player_id)
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
                    market_price = market_mod.get_market_price(item.item_type) or 0.0
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
                    # 10-year capitalisation (monthly_tax × 120) — matches the
                    # leaderboard, estate and government-dashboard land valuations.
                    plot_value = (plot.monthly_tax or 0.0) * 120
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
            from business import Business, BUSINESS_TYPES, get_district_business_types
            from land import LandPlot, get_db as get_land_db

            # Merge standard and district business configs so that high-tier
            # district facilities (e.g. $50M Aircraft Assembly Plant) are valued
            # correctly instead of falling back to the $5,000 default.
            all_business_types = {**BUSINESS_TYPES, **get_district_business_types()}

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
                    config = all_business_types.get(biz.business_type, {})
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

        # 5b. BANK SHARE HOLDINGS — matches estate/leaderboard valuations,
        # which both count bank shares (BankShareholding × share_price).
        try:
            from banks import BankShareholding, BankEntity
            bank_holdings = db.query(BankShareholding).filter(
                BankShareholding.player_id == player_id,
                BankShareholding.shares_owned > 0
            ).all()
            for h in bank_holdings:
                bank = db.query(BankEntity).filter(BankEntity.bank_id == h.bank_id).first()
                if bank:
                    bank_val = h.shares_owned * (bank.share_price or 0)
                    breakdown["shares_value"] += bank_val
                    breakdown["details"]["share_holdings"].append({
                        "ticker": h.bank_id,
                        "shares": h.shares_owned,
                        "price": bank.share_price or 0,
                        "value": bank_val
                    })
        except Exception as e:
            print(f"[{BANK_NAME}] Bank share valuation error: {e}")

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
    """Calculate valuation for IPO purposes based on total net worth.

    Applies a 0.4× discount to prevent inflated IPO prices — a player's
    full liquid net worth (cash, stocks, inventory) should not translate
    directly into company valuation.
    """
    net_worth = calculate_player_total_net_worth(player_id)

    total_valuation = net_worth["total_net_worth"] * 0.4
    
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
        from business import Business, BUSINESS_TYPES, get_district_business_types
        from land import LandPlot, get_db as get_land_db

        all_business_types = {**BUSINESS_TYPES, **get_district_business_types()}

        db = get_db()
        try:
            business = db.query(Business).filter(Business.id == business_id).first()
            if not business:
                return None

            config = all_business_types.get(business.business_type, {})
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
    dividend_config: list = None,
):
    """Create an IPO for a player's holding company.

    Returns (CompanyShares, None) on success, or (None, error_message) on failure.
    """
    db = get_db()
    try:
        ticker_symbol = ticker_symbol.upper().strip()
        if len(ticker_symbol) < 2 or len(ticker_symbol) > 5:
            return None, "Ticker symbol must be 2-5 characters."

        existing = db.query(CompanyShares).filter(
            CompanyShares.ticker_symbol == ticker_symbol
        ).first()
        if existing:
            return None, f"Ticker symbol '{ticker_symbol}' is already taken."

        existing_company = db.query(CompanyShares).filter(
            CompanyShares.founder_id == founder_id,
            CompanyShares.is_delisted == False,
            CompanyShares.parent_company_id == None  # exclude Quad-Class C/D sub-records
        ).first()
        if existing_company:
            return None, "You already have a public company. Delist it first to create a new one."

        # Enforce re-list cooldown (30 days after going private)
        recently_delisted = db.query(CompanyShares).filter(
            CompanyShares.founder_id == founder_id,
            CompanyShares.is_delisted == True,
            CompanyShares.can_relist_after != None
        ).order_by(CompanyShares.delisted_at.desc()).first()
        if recently_delisted and recently_delisted.can_relist_after and recently_delisted.can_relist_after > datetime.utcnow():
            days_left = (recently_delisted.can_relist_after - datetime.utcnow()).days + 1
            return None, f"You must wait {days_left} more day(s) before re-listing. Your previous company went private {RELIST_COOLDOWN_DAYS}-day cooldown is still active."

        valuation = calculate_player_company_valuation(founder_id)
        total_valuation = valuation["total_valuation"]

        config = IPO_CONFIG.get(ipo_type)
        if not config:
            return None, "Invalid IPO type selected."

        min_val = config.get("min_valuation", 25000)
        if total_valuation < min_val:
            return None, f"Your company valuation (${total_valuation:,.0f}) is below the ${min_val:,.0f} minimum for {config['name']}."

        max_float = int(total_shares * config["max_float_pct"])
        if shares_to_offer > max_float:
            return None, f"You can offer at most {max_float:,} shares ({config['max_float_pct']*100:.0f}% of total) for {config['name']}."

        if shares_to_offer < config["min_shares"]:
            return None, f"{config['name']} requires offering at least {config['min_shares']:,} shares."

        MAX_TOTAL_SHARES = 1_000_000_000  # 1 billion hard cap
        if total_shares > MAX_TOTAL_SHARES:
            return None, (f"Total shares cannot exceed 1,000,000,000 (1 billion). "
                          f"You entered {total_shares:,}. Lower your share count — "
                          f"a higher share price per unit is equivalent.")

        firm = get_firm_entity()
        if config.get("firm_underwritten") and not firm.is_accepting_ipos:
            return None, "The Firm is not currently accepting new underwritten IPOs. Its cash reserves are too low. Try again later or use a Direct Listing instead."

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
        elif ipo_type == IPOType.PREFERRED_OFFERING:
            return _process_preferred_ipo(
                db, founder_id, company_name, ticker_symbol, config,
                shares_to_offer, total_shares, share_price, actual_share_class,
                dividend_config, total_valuation
            )
        elif ipo_type == IPOType.SERIES_A_GROWTH:
            return _process_series_a_ipo(
                db, founder_id, company_name, ticker_symbol, config,
                shares_to_offer, total_shares, share_price, actual_share_class,
                dividend_config, total_valuation
            )
        elif ipo_type == IPOType.QUAD_CLASS:
            return _process_quad_class_ipo(
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
        return None, f"An unexpected error occurred: {e}"
    finally:
        db.close()


def _finalize_new_company(db, company, ipo_type_val: str, founder_id: int):
    """Set post-creation defaults shared by all IPO types."""
    # Lockup
    lockup_days = IPO_LOCKUP_DAYS.get(ipo_type_val, 30)
    company.lockup_expires_at = datetime.utcnow() + timedelta(days=lockup_days)
    # Monthly listing fee starts one month from now
    company.listing_fee_next_due = datetime.utcnow() + timedelta(days=30)
    # Reset revenue windows
    now = datetime.utcnow()
    company.revenue_reset_7d  = now
    company.revenue_reset_30d = now
    # Derive sector from founder's businesses
    try:
        from business import Business, BUSINESS_TYPES, get_district_business_types
        from land import get_db as get_land_db
        land_db = get_land_db()
        try:
            bizzes = land_db.query(Business).filter(
                Business.owner_id == founder_id, Business.is_active == True
            ).all()
        finally:
            land_db.close()
        all_types = {**BUSINESS_TYPES, **get_district_business_types()}
        if bizzes:
            from collections import Counter
            type_counts = Counter(b.business_type for b in bizzes)
            most_common_type = type_counts.most_common(1)[0][0]
            company.sector = derive_sector(most_common_type)
    except Exception:
        company.sector = "General"
    db.commit()


def _process_direct_listing_ipo(db, founder_id, company_name, ticker_symbol, config,
                                 shares_to_offer, total_shares, share_price, share_class,
                                 dividend_config, total_valuation):
    listing_fee = config["fee_amount"]
    
    from auth import Player, get_db as get_auth_db
    auth_db = get_auth_db()
    try:
        founder = auth_db.query(Player).filter(Player.id == founder_id).first()
        from reserve_banks import can_afford_usd, spend_player_funds
        if not founder or not can_afford_usd(founder_id, listing_fee):
            return None, f"You need ${listing_fee:,.0f} for the listing fee but have insufficient funds."
        ok, err = spend_player_funds(founder_id, listing_fee)
        if not ok:
            return None, f"Listing fee payment failed: {err}"
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
    _finalize_new_company(db, company, "direct_listing", founder_id)

    founder_position = ShareholderPosition(
        player_id=founder_id,
        company_shares_id=company.id,
        shares_owned=total_shares,
        shares_available_to_lend=total_shares,
        average_cost_basis=0.0,
        first_held_at=datetime.utcnow(),
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

    return company, None


def _process_underwritten_ipo(db, founder_id, company_name, ticker_symbol, ipo_type, config,
                               shares_to_offer, total_shares, share_price, share_class,
                               dividend_config, total_valuation):
    discount_rate = config.get("discount_rate", 0.07)
    discounted_price = share_price * (1 - discount_rate)
    total_cost = shares_to_offer * discounted_price
    
    if not firm_deduct_cash(total_cost, "underwriting_cost", f"Underwriting {ticker_symbol}"):
        return None, "The Firm doesn't have enough cash reserves to underwrite your IPO right now. Try again later or use a Direct Listing."
    
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
        fixed_dividend_rate=config.get("fixed_dividend_rate")
    )
    
    db.add(company)
    db.commit()
    db.refresh(company)
    _finalize_new_company(db, company, ipo_type.value, founder_id)

    from reserve_banks import credit_usd
    credit_usd(founder_id, total_cost)

    founder_shares = total_shares - shares_to_offer
    if founder_shares > 0:
        founder_position = ShareholderPosition(
            player_id=founder_id,
            company_shares_id=company.id,
            shares_owned=founder_shares,
            shares_available_to_lend=founder_shares,
            average_cost_basis=0.0,
            first_held_at=datetime.utcnow(),
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

    return company, None


def _process_dual_class_ipo(db, founder_id, company_name, ticker_symbol, config,
                             shares_to_offer, total_shares, share_price,
                             dividend_config, total_valuation):
    discount_rate = config.get("discount_rate", 0.08)
    discounted_price = share_price * (1 - discount_rate)
    total_cost = shares_to_offer * discounted_price
    
    if not firm_deduct_cash(total_cost, "underwriting_cost", f"Dual-class {ticker_symbol}"):
        return None, "The Firm doesn't have enough cash reserves to underwrite your IPO right now. Try again later or use a Direct Listing."

    class_b_shares = shares_to_offer
    class_a_shares = total_shares - shares_to_offer

    founder_ownership_pct = class_a_shares / total_shares

    min_control = config.get("founder_control_minimum", 0.51)
    if founder_ownership_pct < min_control:
        return None, f"You must retain at least {min_control*100:.0f}% ownership. Reduce the number of shares you're offering."
    
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
    _finalize_new_company(db, company, "dual_class", founder_id)

    from reserve_banks import credit_usd
    credit_usd(founder_id, total_cost)

    if class_a_shares > 0:
        founder_position = ShareholderPosition(
            player_id=founder_id,
            company_shares_id=company.id,
            shares_owned=class_a_shares,
            shares_available_to_lend=0,
            average_cost_basis=0.0,
            first_held_at=datetime.utcnow(),
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

    print(f"[{BANK_NAME}] 🎉 DUAL-CLASS: {ticker_symbol} (founder {class_a_shares} Class A, public {class_b_shares} Class B)")

    return company, None


def _process_preferred_ipo(db, founder_id, company_name, ticker_symbol, config,
                            shares_to_offer, total_shares, share_price, share_class,
                            dividend_config, total_valuation):
    discount_rate = config.get("discount_rate", 0.05)
    discounted_price = share_price * (1 - discount_rate)
    total_cost = shares_to_offer * discounted_price

    if not firm_deduct_cash(total_cost, "underwriting_cost", f"Preferred {ticker_symbol}"):
        return None, "The Firm doesn't have enough cash reserves to underwrite your IPO right now. Try again later or use a Direct Listing."

    actual_dividend_config = list(dividend_config) if dividend_config else []
    if config.get("fixed_dividend_rate"):
        actual_dividend_config.append({
            "type": "cash",
            "amount": share_price * config["fixed_dividend_rate"] / 4,
            "frequency": "quarterly",
            "required": True,
            "share_class": share_class,
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
        fixed_dividend_rate=config.get("fixed_dividend_rate"),
        liquidation_preference=config.get("liquidation_preference"),
        is_callable=config.get("is_callable", False),
        ipo_type=IPOType.PREFERRED_OFFERING.value,
        ipo_date=datetime.utcnow(),
        ipo_valuation=total_valuation,
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    _finalize_new_company(db, company, "preferred_offering", founder_id)

    from reserve_banks import credit_usd
    credit_usd(founder_id, total_cost)

    founder_shares = total_shares - shares_to_offer
    if founder_shares > 0:
        db.add(ShareholderPosition(
            player_id=founder_id,
            company_shares_id=company.id,
            shares_owned=founder_shares,
            shares_available_to_lend=founder_shares,
            average_cost_basis=0.0,
            first_held_at=datetime.utcnow(),
        ))
    db.add(ShareholderPosition(
        player_id=BANK_PLAYER_ID,
        company_shares_id=company.id,
        shares_owned=shares_to_offer,
        shares_available_to_lend=shares_to_offer,
        average_cost_basis=discounted_price,
    ))
    db.commit()

    try:
        from banks.brokerage_order_book import place_limit_order, OrderSide
        place_limit_order(
            player_id=BANK_PLAYER_ID,
            company_shares_id=company.id,
            side=OrderSide.SELL,
            quantity=shares_to_offer,
            limit_price=share_price,
        )
    except ImportError:
        pass

    underwriting_profit = shares_to_offer * share_price * discount_rate
    firm_add_cash(underwriting_profit, "underwriting_fee", f"Preferred: {ticker_symbol}", founder_id, company.id)
    modify_credit_score(founder_id, "ipo_completed")
    print(f"[{BANK_NAME}] 🎉 PREFERRED: {ticker_symbol} (12% div, 1.5× liq pref, callable)")
    return company, None


def _process_series_a_ipo(db, founder_id, company_name, ticker_symbol, config,
                           shares_to_offer, total_shares, share_price, share_class,
                           dividend_config, total_valuation):
    discount_rate = config.get("discount_rate", 0.12)
    growth_bonus_pct = config.get("growth_bonus_pct", 0.20)
    discounted_price = share_price * (1 - discount_rate)
    standard_proceeds = shares_to_offer * discounted_price
    growth_bonus = standard_proceeds * growth_bonus_pct
    total_payout = standard_proceeds + growth_bonus

    if not firm_deduct_cash(standard_proceeds, "underwriting_cost", f"Series A {ticker_symbol}"):
        return None, "The Firm doesn't have enough cash reserves to underwrite your IPO right now. Try again later or use a Direct Listing."
    if not firm_deduct_cash(growth_bonus, "growth_bonus", f"Series A bonus: {ticker_symbol}"):
        firm_add_cash(standard_proceeds, "underwriting_refund", f"Refund: {ticker_symbol}", founder_id)
        return None, "The Firm doesn't have enough reserves for the Series A growth bonus right now."

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
        dividend_config=dividend_config or [],
        ipo_type=IPOType.SERIES_A_GROWTH.value,
        ipo_date=datetime.utcnow(),
        ipo_valuation=total_valuation,
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    _finalize_new_company(db, company, "series_a_growth", founder_id)

    from reserve_banks import credit_usd
    credit_usd(founder_id, total_payout)

    founder_shares = total_shares - shares_to_offer
    if founder_shares > 0:
        db.add(ShareholderPosition(
            player_id=founder_id,
            company_shares_id=company.id,
            shares_owned=founder_shares,
            shares_available_to_lend=founder_shares,
            average_cost_basis=0.0,
            first_held_at=datetime.utcnow(),
        ))
    db.add(ShareholderPosition(
        player_id=BANK_PLAYER_ID,
        company_shares_id=company.id,
        shares_owned=shares_to_offer,
        shares_available_to_lend=shares_to_offer,
        average_cost_basis=discounted_price,
    ))
    db.commit()

    try:
        from banks.brokerage_order_book import place_limit_order, OrderSide
        place_limit_order(
            player_id=BANK_PLAYER_ID,
            company_shares_id=company.id,
            side=OrderSide.SELL,
            quantity=shares_to_offer,
            limit_price=share_price,
        )
    except ImportError:
        pass

    underwriting_profit = shares_to_offer * share_price * discount_rate
    firm_add_cash(underwriting_profit, "underwriting_fee", f"Series A: {ticker_symbol}", founder_id, company.id)
    modify_credit_score(founder_id, "ipo_completed")
    print(f"[{BANK_NAME}] 🎉 SERIES A: {ticker_symbol} (proceeds ${standard_proceeds:,.0f} + bonus ${growth_bonus:,.0f})")
    return company, None


def _process_quad_class_ipo(db, founder_id, company_name, ticker_symbol, config,
                             shares_to_offer, total_shares, share_price,
                             dividend_config, total_valuation):
    discount_rate = config.get("discount_rate", 0.10)
    growth_bonus_pct = config.get("growth_bonus_pct", 0.15)
    discounted_price = share_price * (1 - discount_rate)
    standard_proceeds = shares_to_offer * discounted_price
    growth_bonus = standard_proceeds * growth_bonus_pct
    total_payout = standard_proceeds + growth_bonus

    class_b_shares = shares_to_offer
    class_a_shares = total_shares - shares_to_offer
    founder_ownership_pct = class_a_shares / total_shares
    min_control = config.get("founder_control_minimum", 0.40)
    if founder_ownership_pct < min_control:
        return None, f"You must retain at least {min_control*100:.0f}% ownership (Class A) for a Quad-Class IPO. Reduce the number of shares offered."

    if not firm_deduct_cash(standard_proceeds, "underwriting_cost", f"Quad-class {ticker_symbol}"):
        return None, "The Firm doesn't have enough cash reserves to underwrite your IPO right now. Try again later or use a Direct Listing."
    if not firm_deduct_cash(growth_bonus, "growth_bonus", f"Quad-class bonus: {ticker_symbol}"):
        firm_add_cash(standard_proceeds, "underwriting_refund", f"Refund: {ticker_symbol}", founder_id)
        return None, "The Firm doesn't have enough reserves for the Quad-Class growth capital injection right now."

    actual_dividend_config = list(dividend_config) if dividend_config else []
    if config.get("fixed_dividend_rate"):
        actual_dividend_config.append({
            "type": "cash",
            "amount": share_price * config["fixed_dividend_rate"] / 4,
            "frequency": "quarterly",
            "required": True,
            "share_class": ShareClass.CLASS_B.value,
        })

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
        dividend_config=actual_dividend_config,
        fixed_dividend_rate=config.get("fixed_dividend_rate"),
        liquidation_preference=config.get("liquidation_preference"),
        is_callable=True,
        is_dual_class=True,
        ipo_type=IPOType.QUAD_CLASS.value,
        ipo_date=datetime.utcnow(),
        ipo_valuation=total_valuation,
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    _finalize_new_company(db, company, "quad_class", founder_id)

    from reserve_banks import credit_usd
    credit_usd(founder_id, total_payout)

    # Class A position (founder super-shares — non-lendable, non-shortable)
    if class_a_shares > 0:
        db.add(ShareholderPosition(
            player_id=founder_id,
            company_shares_id=company.id,
            shares_owned=class_a_shares,
            shares_available_to_lend=0,
            average_cost_basis=0.0,
            first_held_at=datetime.utcnow(),
        ))

    # Class B: 60% of offered shares — public voting common
    class_b_count = round(class_b_shares * QUAD_CLASS_B_FRACTION)
    # Class C: 25% of offered shares — preferred dividend (separate record)
    class_c_count = round(class_b_shares * QUAD_CLASS_C_FRACTION)
    # Class D: 15% of offered shares — non-voting equity (separate record)
    class_d_count = class_b_shares - class_b_count - class_c_count

    db.add(ShareholderPosition(
        player_id=BANK_PLAYER_ID,
        company_shares_id=company.id,
        shares_owned=class_b_count,
        shares_available_to_lend=class_b_count,
        average_cost_basis=discounted_price,
    ))
    db.commit()

    # ── Class C: preferred dividend sub-record ──────────────────────────
    class_c_div = [{
        "type": "cash",
        "amount": share_price * config["fixed_dividend_rate"] / 4,
        "frequency": "quarterly",
        "required": True,
        "share_class": ShareClass.CLASS_C.value,
    }]
    company_c = CompanyShares(
        founder_id=founder_id,
        business_id=0,
        company_name=f"{company_name} (Class C Preferred)",
        ticker_symbol=f"{ticker_symbol}-C",
        share_class=ShareClass.CLASS_C.value,
        total_shares_authorized=class_c_count,
        shares_outstanding=class_c_count,
        shares_held_by_founder=0,
        shares_held_by_firm=class_c_count,
        shares_in_float=0,
        current_price=share_price,
        ipo_price=share_price,
        high_52_week=share_price,
        low_52_week=share_price,
        dividend_config=class_c_div,
        fixed_dividend_rate=config.get("fixed_dividend_rate"),
        liquidation_preference=config.get("liquidation_preference"),
        is_callable=True,
        ipo_type=IPOType.QUAD_CLASS.value,
        ipo_date=datetime.utcnow(),
        ipo_valuation=total_valuation,
        parent_company_id=company.id,
        share_class_label="class_c",
    )
    db.add(company_c)
    db.commit()
    db.refresh(company_c)
    db.add(ShareholderPosition(
        player_id=BANK_PLAYER_ID,
        company_shares_id=company_c.id,
        shares_owned=class_c_count,
        shares_available_to_lend=class_c_count,
        average_cost_basis=discounted_price,
    ))
    db.commit()

    # ── Class D: non-voting equity sub-record ──────────────────────────
    company_d = CompanyShares(
        founder_id=founder_id,
        business_id=0,
        company_name=f"{company_name} (Class D Non-Voting)",
        ticker_symbol=f"{ticker_symbol}-D",
        share_class=ShareClass.CLASS_D.value,
        total_shares_authorized=class_d_count,
        shares_outstanding=class_d_count,
        shares_held_by_founder=0,
        shares_held_by_firm=class_d_count,
        shares_in_float=0,
        current_price=share_price,
        ipo_price=share_price,
        high_52_week=share_price,
        low_52_week=share_price,
        dividend_config=[],
        liquidation_preference=config.get("liquidation_preference"),
        is_callable=True,
        ipo_type=IPOType.QUAD_CLASS.value,
        ipo_date=datetime.utcnow(),
        ipo_valuation=total_valuation,
        parent_company_id=company.id,
        share_class_label="class_d",
    )
    db.add(company_d)
    db.commit()
    db.refresh(company_d)
    db.add(ShareholderPosition(
        player_id=BANK_PLAYER_ID,
        company_shares_id=company_d.id,
        shares_owned=class_d_count,
        shares_available_to_lend=class_d_count,
        average_cost_basis=discounted_price,
    ))
    db.commit()

    # Place sell orders for all three public classes
    try:
        from banks.brokerage_order_book import place_limit_order, OrderSide
        for cs_id, qty in [
            (company.id, class_b_count),
            (company_c.id, class_c_count),
            (company_d.id, class_d_count),
        ]:
            if qty > 0:
                place_limit_order(
                    player_id=BANK_PLAYER_ID,
                    company_shares_id=cs_id,
                    side=OrderSide.SELL,
                    quantity=qty,
                    limit_price=share_price,
                )
    except ImportError:
        pass

    underwriting_profit = shares_to_offer * share_price * discount_rate
    firm_add_cash(underwriting_profit, "underwriting_fee", f"Quad-class: {ticker_symbol}", founder_id, company.id)
    modify_credit_score(founder_id, "ipo_completed")
    print(f"[{BANK_NAME}] 🎉 QUAD-CLASS: {ticker_symbol} "
          f"(A:{class_a_shares} founder, B:{class_b_count} voting, "
          f"C:{class_c_count} preferred-div, D:{class_d_count} non-voting, "
          f"bonus ${growth_bonus:,.0f}, 10% div, 1.2× liq pref)")
    return company, None


# ==========================
# CALLABLE SHARE REDEMPTION
# ==========================

def call_shares(company_id: int, founder_id: int):
    """Buy back all publicly-held shares of a callable company at current price + CALL_PREMIUM.

    Unlike go-private (delist), this does NOT delist the company — it redeems the
    callable share class and consolidates ownership back with the founder.
    Returns (True, message) on success, (False, error) on failure.
    """
    db = get_db()
    try:
        company = db.query(CompanyShares).filter(
            CompanyShares.id == company_id,
            CompanyShares.founder_id == founder_id,
            CompanyShares.is_delisted == False,
            CompanyShares.is_callable == True,
        ).first()
        if not company:
            return False, "Company not found, not yours, already delisted, or not callable."

        public_positions = db.query(ShareholderPosition).filter(
            ShareholderPosition.company_shares_id == company_id,
            ShareholderPosition.player_id != founder_id,
            ShareholderPosition.shares_owned > 0,
        ).all()

        if not public_positions:
            return False, "There are no outstanding public shares to call back."

        call_price = company.current_price * (1 + CALL_PREMIUM)
        total_shares_called = sum(p.shares_owned for p in public_positions)
        total_cost = total_shares_called * call_price

        from reserve_banks import can_afford_usd, spend_player_funds, credit_usd
        if not can_afford_usd(founder_id, total_cost):
            return False, (
                f"Insufficient funds. Calling {total_shares_called:,} shares at "
                f"${call_price:.4f}/share (5% premium) costs ${total_cost:,.2f}."
            )

        ok, err = spend_player_funds(founder_id, total_cost)
        if not ok:
            return False, f"Payment failed: {err}"

        # Pay each holder and transfer shares to founder
        founder_pos = db.query(ShareholderPosition).filter(
            ShareholderPosition.company_shares_id == company_id,
            ShareholderPosition.player_id == founder_id,
        ).first()

        for pos in public_positions:
            payout = pos.shares_owned * call_price
            credit_usd(pos.player_id, payout)
            if founder_pos:
                founder_pos.shares_owned += pos.shares_owned
                founder_pos.shares_available_to_lend += pos.shares_owned
            pos.shares_owned = 0
            pos.shares_available_to_lend = 0
            pos.shares_lent_out = 0

        company.shares_held_by_founder = (founder_pos.shares_owned if founder_pos else total_shares_called)
        company.shares_held_by_firm = 0
        company.shares_in_float = 0
        db.commit()

        print(f"[{BANK_NAME}] 📞 CALL: {company.ticker_symbol} — {total_shares_called:,} shares redeemed "
              f"@ ${call_price:.4f}/share (${total_cost:,.2f} total)")
        return True, (
            f"Called {total_shares_called:,} shares at ${call_price:.4f}/share "
            f"(5% premium, total ${total_cost:,.2f}). Shares returned to founder."
        )

    except Exception as e:
        db.rollback()
        print(f"[{BANK_NAME}] call_shares error: {e}")
        return False, str(e)
    finally:
        db.close()


# ==========================
# SHAREHOLDER GOVERNANCE / VOTING
# ==========================

def get_voting_power(company: CompanyShares, position: ShareholderPosition) -> float:
    """Return the weighted voting power of a position.

    Dual-class / Quad-class founder (Class A): CLASS_A_VOTE_MULTIPLIER × shares.
    Class C / Class D sub-records: 0 votes (non-voting by design).
    All other shareholders: 1 × shares.
    """
    # Class C and D are non-voting — they live in sub-records (parent_company_id set)
    if company.share_class_label in ("class_c", "class_d"):
        return 0.0
    # Dual/Quad-class: founder's position gets the super-vote
    if company.is_dual_class and position.player_id == company.founder_id:
        return float(position.shares_owned) * CLASS_A_VOTE_MULTIPLIER
    return float(position.shares_owned)


def create_proposal(
    company_id: int,
    proposer_id: int,
    proposal_type: str,
    title: str,
    description: str,
    proposal_param: dict = None,
):
    """Create a governance proposal for a company.

    Any shareholder may propose; voting lasts PROPOSAL_DURATION_HOURS hours.
    Returns (CompanyProposal, None) or (None, error_str).
    """
    db = get_db()
    try:
        company = db.query(CompanyShares).filter(
            CompanyShares.id == company_id,
            CompanyShares.is_delisted == False,
            CompanyShares.parent_company_id == None,
        ).first()
        if not company:
            return None, "Company not found."

        # Confirm proposer holds shares
        pos = db.query(ShareholderPosition).filter(
            ShareholderPosition.company_shares_id == company_id,
            ShareholderPosition.player_id == proposer_id,
            ShareholderPosition.shares_owned > 0,
        ).first()
        if not pos:
            return None, "You must hold shares in this company to create a proposal."

        # Limit open proposals
        open_count = db.query(CompanyProposal).filter(
            CompanyProposal.company_shares_id == company_id,
            CompanyProposal.status == "open",
        ).count()
        if open_count >= 3:
            return None, "This company already has 3 open proposals. Wait for them to close."

        proposal = CompanyProposal(
            company_shares_id=company_id,
            proposer_id=proposer_id,
            proposal_type=proposal_type,
            title=title,
            description=description,
            proposal_param=proposal_param or {},
            voting_ends_at=datetime.utcnow() + timedelta(hours=PROPOSAL_DURATION_HOURS),
        )
        db.add(proposal)
        db.commit()
        db.refresh(proposal)
        return proposal, None
    except Exception as e:
        db.rollback()
        return None, str(e)
    finally:
        db.close()


def cast_vote(proposal_id: int, voter_id: int, vote: bool):
    """Cast a weighted vote on an open governance proposal.

    vote=True means YES, vote=False means NO.
    Returns (True, message) or (False, error).
    """
    db = get_db()
    try:
        proposal = db.query(CompanyProposal).filter(
            CompanyProposal.id == proposal_id,
            CompanyProposal.status == "open",
        ).first()
        if not proposal:
            return False, "Proposal not found or voting is closed."
        if proposal.voting_ends_at <= datetime.utcnow():
            return False, "Voting period has ended."

        existing = db.query(CompanyVote).filter(
            CompanyVote.proposal_id == proposal_id,
            CompanyVote.voter_id == voter_id,
        ).first()
        if existing:
            return False, "You have already voted on this proposal."

        company = db.query(CompanyShares).filter(
            CompanyShares.id == proposal.company_shares_id
        ).first()
        pos = db.query(ShareholderPosition).filter(
            ShareholderPosition.company_shares_id == proposal.company_shares_id,
            ShareholderPosition.player_id == voter_id,
            ShareholderPosition.shares_owned > 0,
        ).first()
        if not pos:
            return False, "You must hold shares in this company to vote."

        power = get_voting_power(company, pos)
        if power <= 0:
            return False, "Your share class carries no voting rights."

        # Minority protection: founder's 10× super-vote is neutralised for escrow releases
        if (proposal.proposal_type == "force_dividend_from_escrow"
                and voter_id == company.founder_id
                and company.is_dual_class):
            power = pos.shares_owned  # cap to 1× regardless of share class

        cv = CompanyVote(
            proposal_id=proposal_id,
            voter_id=voter_id,
            vote=vote,
            voting_power=power,
        )
        db.add(cv)

        if vote:
            proposal.yes_votes += power
        else:
            proposal.no_votes += power
        proposal.total_voters += 1

        db.commit()
        label = "YES" if vote else "NO"
        return True, f"Vote cast: {label} ({power:,.0f} weighted votes)"
    except Exception as e:
        db.rollback()
        return False, str(e)
    finally:
        db.close()


def _apply_proposal_effect(db, proposal: "CompanyProposal", company: "CompanyShares"):
    """Apply the real-world effect of a passed governance proposal.

    Modifies the company record in-place; caller must commit.
    Returns a human-readable description of what changed (or None for custom).
    """
    ptype = proposal.proposal_type
    param = proposal.proposal_param or {}

    if ptype == "dividend_change":
        new_rate = param.get("new_rate")
        if new_rate is None:
            return None
        new_rate = float(new_rate)
        # Update fixed rate; also patch the live dividend_config quarterly amounts
        company.fixed_dividend_rate = new_rate
        if company.dividend_config:
            configs = company.dividend_config
            if company.ipo_price and company.ipo_price > 0:
                quarterly_amount = company.ipo_price * new_rate / 4
                for cfg in configs:
                    cfg["amount"] = quarterly_amount
            company.dividend_config = configs
        return f"Dividend rate changed to {new_rate*100:.2f}%/year"

    elif ptype == "secondary_offering":
        new_shares = param.get("shares")
        if not new_shares:
            return None
        new_shares = int(new_shares)
        company.shares_outstanding = (company.shares_outstanding or 0) + new_shares
        company.shares_in_float = (company.shares_in_float or 0) + new_shares
        # Dilute the price proportionally
        if company.shares_outstanding > new_shares and company.current_price:
            old_total = company.shares_outstanding - new_shares
            company.current_price = company.current_price * old_total / company.shares_outstanding
        return f"Issued {new_shares:,} new shares into public float"

    elif ptype == "trading_halt":
        hours = int(param.get("hours", 24))
        hours = max(1, min(hours, 168))  # cap at 1 week
        company.trading_halted = True
        company.trading_halted_until = datetime.utcnow() + timedelta(hours=hours)
        return f"Trading halted for {hours} hours"

    elif ptype == "force_dividend_from_escrow":
        # Minority shareholder protection: release accumulated escrow to shareholders.
        # The founder's 10× vote is capped to 1× when casting (see cast_vote above).
        amount = float(param.get("amount", 0.0))
        if amount <= 0:
            return None
        available = company.dividend_escrow_balance or 0.0
        release = min(amount, available)
        if release < 0.01:
            return "No escrow balance to release"

        positions = db.query(ShareholderPosition).filter(
            ShareholderPosition.company_shares_id == company.id,
            ShareholderPosition.shares_owned > 0,
            ShareholderPosition.player_id != company.founder_id,
            ShareholderPosition.player_id != BANK_PLAYER_ID,
        ).all()

        public_shares = sum(p.shares_owned for p in positions)
        if public_shares > 0:
            per_share = release / public_shares
            from reserve_banks import credit_usd as _credit_usd
            for pos in positions:
                payout = pos.shares_owned * per_share
                if payout >= 0.01:
                    _credit_usd(pos.player_id, payout)

        company.dividend_escrow_balance = max(0.0, available - release)
        return f"Released ${release:,.2f} from escrow to {len(positions)} shareholders"

    # custom or unknown: no automatic effect
    return None


def resolve_proposals():
    """Close expired proposals, record their outcome, and apply effects for passed proposals."""
    db = get_db()
    try:
        expired = db.query(CompanyProposal).filter(
            CompanyProposal.status == "open",
            CompanyProposal.voting_ends_at <= datetime.utcnow(),
        ).all()
        for p in expired:
            p.status = "passed" if p.yes_votes > p.no_votes else "rejected"
            company = db.query(CompanyShares).filter(
                CompanyShares.id == p.company_shares_id
            ).first()
            ticker = company.ticker_symbol if company else f"id={p.company_shares_id}"
            print(f"[{BANK_NAME}] 🗳  Proposal #{p.id} '{p.title}' ({ticker}): "
                  f"{p.status.upper()} ({p.yes_votes:.0f}Y / {p.no_votes:.0f}N)")
            if p.status == "passed" and company and not p.result_applied:
                effect = _apply_proposal_effect(db, p, company)
                p.result_applied = True
                if effect:
                    print(f"[{BANK_NAME}]    ↳ Effect applied: {effect}")
        if expired:
            db.commit()
    finally:
        db.close()


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
# GO PRIVATE / DELISTING
# ==========================

DELISTING_FEE_PCT = 0.02  # 2% of market cap
BUYBACK_PREMIUM = 0.10  # 10% premium over market price to buy back shares
RELIST_COOLDOWN_DAYS = 30  # Must wait 30 days before re-IPOing


def calculate_delisting_cost(company_id: int):
    """Calculate what it would cost a founder to take their company private.

    Returns a dict with cost breakdown, or (None, error) on failure.
    """
    db = get_db()
    try:
        company = db.query(CompanyShares).filter(
            CompanyShares.id == company_id,
            CompanyShares.is_delisted == False
        ).first()
        if not company:
            return None, "Company not found or already delisted."

        # Count shares held by others (not the founder)
        positions = db.query(ShareholderPosition).filter(
            ShareholderPosition.company_shares_id == company.id,
            ShareholderPosition.shares_owned > 0,
            ShareholderPosition.player_id != company.founder_id
        ).all()

        public_shares = sum(p.shares_owned for p in positions)
        buyback_price = company.current_price * (1 + BUYBACK_PREMIUM)
        buyback_cost = public_shares * buyback_price

        market_cap = company.current_price * company.shares_outstanding
        delisting_fee = market_cap * DELISTING_FEE_PCT

        total_cost = buyback_cost + delisting_fee

        return {
            "company": company,
            "public_shares": public_shares,
            "buyback_price_per_share": buyback_price,
            "buyback_cost": buyback_cost,
            "delisting_fee": delisting_fee,
            "total_cost": total_cost,
            "current_price": company.current_price,
            "market_cap": market_cap,
        }, None
    finally:
        db.close()


def delist_company(founder_id: int, company_id: int):
    """Take a company private by buying back all public shares and delisting.

    Returns (True, None) on success, or (False, error_message) on failure.
    """
    db = get_db()
    try:
        company = db.query(CompanyShares).filter(
            CompanyShares.id == company_id,
            CompanyShares.founder_id == founder_id,
            CompanyShares.is_delisted == False
        ).first()
        if not company:
            return False, "Company not found, you're not the founder, or it's already delisted."

        # Calculate costs
        cost_info, err = calculate_delisting_cost(company_id)
        if err:
            return False, err

        total_cost = cost_info["total_cost"]
        buyback_price = cost_info["buyback_price_per_share"]

        # Check founder can afford it
        from auth import Player, get_db as get_auth_db
        auth_db = get_auth_db()
        try:
            founder = auth_db.query(Player).filter(Player.id == founder_id).first()
            from reserve_banks import can_afford_usd, spend_player_funds
            if not founder or not can_afford_usd(founder_id, total_cost):
                needed = total_cost - (founder.cash_balance if founder else 0)
                return False, f"You need ${total_cost:,.0f} to go private but you're ${needed:,.0f} short."
            ok, err = spend_player_funds(founder.id, total_cost)
            if not ok:
                return False, f"Go-private payment failed: {err}"
            auth_db.commit()
        finally:
            auth_db.close()

        # Pay the delisting fee to the firm
        firm_add_cash(cost_info["delisting_fee"], "delisting_fee",
                      f"Delisting: {company.ticker_symbol}", founder_id, company.id)

        # Buy back shares from all public holders and pay them
        positions = db.query(ShareholderPosition).filter(
            ShareholderPosition.company_shares_id == company.id,
            ShareholderPosition.shares_owned > 0,
            ShareholderPosition.player_id != founder_id
        ).all()

        auth_db = get_auth_db()
        try:
            for position in positions:
                payout = position.shares_owned * buyback_price
                holder = auth_db.query(Player).filter(Player.id == position.player_id).first()
                if holder:
                    try:
                        from reserve_banks import convert_to_legal_tender
                        _amt, _code = convert_to_legal_tender(holder.id, payout)
                        if _code == "USD":
                            holder.cash_balance += _amt
                    except Exception:
                        holder.cash_balance += payout

                # Transfer shares to founder
                position.shares_owned = 0
                position.shares_available_to_lend = 0

            auth_db.commit()
        finally:
            auth_db.close()

        # Cancel all open orders for this stock and refund reserved cash to buy-order holders
        try:
            from banks.brokerage_order_book import OrderBook, OrderStatus, OrderSide, get_db as get_ob_db
            from auth import Player, get_db as get_auth_db
            ob_db = get_ob_db()
            try:
                open_orders = ob_db.query(OrderBook).filter(
                    OrderBook.company_shares_id == company.id,
                    OrderBook.status.in_([OrderStatus.PENDING.value, OrderStatus.PARTIAL.value])
                ).all()
                auth_db_refund = get_auth_db()
                try:
                    for order in open_orders:
                        order.status = OrderStatus.CANCELLED.value
                        # Refund the unfilled reserved cash for buy orders
                        if order.order_side == OrderSide.BUY.value and order.reserved_cash > 0:
                            unfilled_qty = order.quantity - order.filled_quantity
                            cash_to_release = (order.reserved_cash / order.quantity) * unfilled_qty
                            holder = auth_db_refund.query(Player).filter(Player.id == order.player_id).first()
                            if holder:
                                holder.cash_balance += cash_to_release
                    auth_db_refund.commit()
                finally:
                    auth_db_refund.close()
                ob_db.commit()
            finally:
                ob_db.close()
        except ImportError:
            pass

        # Update company record
        founder_position = db.query(ShareholderPosition).filter(
            ShareholderPosition.company_shares_id == company.id,
            ShareholderPosition.player_id == founder_id
        ).first()
        if founder_position:
            founder_position.shares_owned = company.total_shares_authorized
            founder_position.shares_available_to_lend = 0

        company.is_delisted = True
        company.delisted_at = datetime.utcnow()
        company.can_relist_after = datetime.utcnow() + timedelta(days=RELIST_COOLDOWN_DAYS)
        company.shares_held_by_founder = company.total_shares_authorized
        company.shares_held_by_firm = 0
        company.shares_in_float = 0
        company.trading_halted = True
        company.halt_reason = "Delisted - company taken private"

        db.commit()

        print(f"[{BANK_NAME}] Company {company.ticker_symbol} delisted (taken private by founder)")
        return True, None

    except Exception as e:
        print(f"[{BANK_NAME}] Delisting error: {e}")
        return False, f"An unexpected error occurred: {e}"
    finally:
        db.close()


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
            ShareholderPosition.margin_debt > 0,
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

        # Class A shares are super-shares (non-lendable, non-shortable)
        if company.share_class_label == "class_a":
            return None

        # Float utilisation cap: refuse if this short would push SI over MAX_SHORT_FLOAT_PCT
        if company.shares_in_float:
            total_shorted = db.query(func.sum(ShareLoan.shares_borrowed)).filter(
                ShareLoan.company_shares_id == company_shares_id,
                ShareLoan.status == ShareLoanStatus.ACTIVE.value,
            ).scalar() or 0
            if total_shorted + quantity > company.shares_in_float * MAX_SHORT_FLOAT_PCT:
                return None

        # Lender selection: always prefer the brokerage firm first, then fall
        # back to other shareholders.  This ensures the firm bears the inventory
        # risk on its own underwritten positions before third-party lenders are
        # exposed.
        lender_position = db.query(ShareholderPosition).filter(
            ShareholderPosition.company_shares_id == company_shares_id,
            ShareholderPosition.player_id == BANK_PLAYER_ID,
            ShareholderPosition.shares_available_to_lend >= quantity,
        ).first()
        if lender_position is None:
            lender_position = db.query(ShareholderPosition).filter(
                ShareholderPosition.company_shares_id == company_shares_id,
                ShareholderPosition.shares_available_to_lend >= quantity,
                ShareholderPosition.player_id != borrower_id,
                ShareholderPosition.player_id != BANK_PLAYER_ID,
            ).first()
        if lender_position is None:
            return None

        borrow_value = quantity * company.current_price
        # Lock 150% collateral from the player, then immediately credit back the
        # 100% short-sale proceeds.  Net out-of-pocket = 50% additional margin.
        collateral_required = borrow_value * SHORT_COLLATERAL_REQUIREMENT
        # Base rate from credit tier, then scaled up by short-interest multiplier
        annual_rate = get_short_borrow_rate(borrower_id) * get_short_interest_multiplier(company_shares_id)
        weekly_rate = annual_rate / 52

        from auth import Player, get_db as get_auth_db
        from reserve_banks import spend_player_funds, credit_usd
        auth_db = get_auth_db()
        try:
            borrower = auth_db.query(Player).filter(Player.id == borrower_id).first()
            if not borrower:
                return None
            ok, _ = spend_player_funds(borrower.id, collateral_required)
            if not ok:
                return None
            auth_db.commit()
        finally:
            auth_db.close()

        # Credit the short-sale proceeds (shares were "sold" at borrow_price)
        credit_usd(borrower_id, borrow_value)

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
            due_date=None  # Open-ended — closed by borrower or collateral exhaustion
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


def close_short_position(loan_id: int, forced: bool = False) -> bool:
    """Close a short position voluntarily or via force-close (collateral exhaustion).

    Args:
        loan_id: The ShareLoan to close.
        forced: True when triggered by the system (collateral exhausted).  Applies
                the more severe 'short_force_closed' credit penalty instead of the
                normal voluntary-close modifiers.
    """
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
            # Refund collateral in-memory first; only commit after the market
            # order succeeds to prevent a TOCTOU exploit where a crash between
            # the commit and the order placement leaves the player with free money.
            auth_db = get_auth_db()
            try:
                borrower = auth_db.query(Player).filter(Player.id == loan.borrower_player_id).first()
                if borrower:
                    borrower.cash_balance += loan.collateral_locked
                # Deliberately NOT committing here — wait for market order result.

                success = place_market_order(
                    player_id=loan.borrower_player_id,
                    company_shares_id=loan.company_shares_id,
                    side=OrderSide.BUY,
                    quantity=loan.shares_borrowed
                )

                if not success:
                    # Discard the in-memory balance change without persisting it.
                    auth_db.rollback()
                    return False

                # Market order succeeded — now it is safe to persist the refund.
                auth_db.commit()
            except Exception:
                auth_db.rollback()
                raise
            finally:
                auth_db.close()
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
        
        if forced:
            # Collateral exhausted — treat as a default regardless of P&L sign
            modify_credit_score(loan.borrower_player_id, "short_force_closed")
        elif pnl > 0:
            modify_credit_score(loan.borrower_player_id, "short_closed_profit")
        else:
            modify_credit_score(loan.borrower_player_id, "short_closed_loss")
        
        return True
    
    except Exception as e:
        print(f"[{BANK_NAME}] Close short error: {e}")
        return False
    finally:
        db.close()


def recall_shares(lender_id: int, company_shares_id: int) -> tuple:
    """Recall all active share loans for a given lender + company pair.

    Force-closes each qualifying short position immediately (same mechanics as
    collateral-exhaustion force-close).  Loan status is set to RECALLED so the
    history distinguishes lender-initiated closures from system force-closes.

    Returns (count_recalled, error_str | None).
    """
    db = get_db()
    try:
        loan_ids = [
            row.id for row in db.query(ShareLoan.id).filter(
                ShareLoan.lender_player_id == lender_id,
                ShareLoan.company_shares_id == company_shares_id,
                ShareLoan.status == ShareLoanStatus.ACTIVE.value,
            ).all()
        ]
    finally:
        db.close()

    if not loan_ids:
        return 0, "No active loans to recall for this position."

    count = 0
    for loan_id in loan_ids:
        ok = close_short_position(loan_id, forced=True)
        if ok:
            count += 1
            # Upgrade the status from RETURNED → RECALLED so history is clear
            db2 = get_db()
            try:
                loan = db2.query(ShareLoan).filter(ShareLoan.id == loan_id).first()
                if loan and loan.status == ShareLoanStatus.RETURNED.value:
                    loan.status = ShareLoanStatus.RECALLED.value
                    db2.commit()
            finally:
                db2.close()

    if count == 0:
        return 0, "Could not recall any loans (market orders may have failed)."
    return count, None


def process_share_loan_interest():
    db = get_db()
    force_close_ids = []
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
                        try:
                            from reserve_banks import convert_to_legal_tender
                            _amt, _code = convert_to_legal_tender(lender.id, fee_to_lender)
                            if _code == "USD":
                                lender.cash_balance += _amt
                        except Exception:
                            lender.cash_balance += fee_to_lender
                        auth_db.commit()
                finally:
                    auth_db.close()

                firm_add_cash(fee_to_firm, "short_borrow_fee", "Borrow fee", loan.borrower_player_id)

                # Queue for force-close if collateral will run out within 3 days
                three_day_fee = daily_fee * 3
                if loan.collateral_locked < three_day_fee:
                    force_close_ids.append(loan.id)
            else:
                # Collateral fully exhausted — drain remainder and force-close
                remaining = max(loan.collateral_locked, 0.0)
                if remaining > 0:
                    loan.total_fees_paid += remaining
                    loan.fees_to_firm += remaining
                    loan.collateral_locked = 0.0
                    firm_add_cash(remaining, "short_borrow_fee", "Collateral exhausted", loan.borrower_player_id)
                force_close_ids.append(loan.id)

        db.commit()
    finally:
        db.close()

    # Force-close positions with exhausted/near-exhausted collateral (separate transactions)
    for loan_id in force_close_ids:
        try:
            close_short_position(loan_id, forced=True)
            print(f"[{BANK_NAME}] Force-closed short loan #{loan_id} — collateral exhausted")
        except Exception as e:
            print(f"[{BANK_NAME}] Error force-closing short loan #{loan_id}: {e}")


# ==========================
# COMMODITY LENDING (WCE)
# ==========================

def list_commodity_for_lending(lender_id: int, item_type: str, quantity: float, weekly_rate: float) -> Optional[CommodityListing]:
    # Fund/ETF shares (item types ending in "_shares") belong on the ETF
    # Trading Floor — they must not be listed as lendable commodities here.
    if item_type.endswith("_shares"):
        return None

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
        from reserve_banks import spend_player_funds
        auth_db = get_auth_db()
        try:
            borrower = auth_db.query(Player).filter(Player.id == borrower_id).first()
            if not borrower:
                return None
            ok, _ = spend_player_funds(borrower.id, collateral_required + total_fee)
            if not ok:
                return None
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
            # WMA: cost basis of borrowed items = total fee paid / quantity borrowed
            try:
                from wma import update_wma
                if quantity > 0:
                    update_wma(borrower_id, listing.item_type,
                               quantity, total_fee / quantity)
            except Exception:
                pass
        except Exception as e:
            return None
        
        auth_db = get_auth_db()
        try:
            lender = auth_db.query(Player).filter(Player.id == listing.lender_player_id).first()
            if lender:
                try:
                    from reserve_banks import convert_to_legal_tender
                    _amt, _code = convert_to_legal_tender(lender.id, fee_to_lender)
                    if _code == "USD":
                        lender.cash_balance += _amt
                except Exception:
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
                try:
                    from reserve_banks import convert_to_legal_tender
                    _amt, _code = convert_to_legal_tender(lender.id, fee_to_lender)
                    if _code == "USD":
                        lender.cash_balance += _amt
                except Exception:
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
                        try:
                            from reserve_banks import convert_to_legal_tender
                            _amt, _code = convert_to_legal_tender(lender.id, fee_to_lender)
                            if _code == "USD":
                                lender.cash_balance += _amt
                        except Exception:
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


def _fire_govt_push(player_id: int, title: str, body: str):
    import threading
    def _send():
        try:
            from push_ux import send_push_notification
            send_push_notification(player_id, title, body, url="/banking",
                                   notif_type="govt",
                                   tag=f"govt-{player_id}-{title[:20]}")
        except Exception as e:
            print(f"[BrokerageFirm] Push error: {e}")
    threading.Thread(target=_send, daemon=True).start()


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

    _fire_govt_push(player_id, "Lien Placed on Your Account",
                    f"${amount:,.0f} lien from {source} — funds will be garnished until cleared")


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
                        _fire_govt_push(lien.player_id, "Lien Garnishment",
                                        f"${garnish:,.0f} garnished from your balance — ${max(0, lien.total_owed):,.0f} remaining on lien")

                        if lien.total_owed <= 0:
                            modify_credit_score(lien.player_id, "lien_paid_off")
                            _fire_govt_push(lien.player_id, "Lien Cleared",
                                            "Your lien has been fully paid off — credit score updated")
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

    # Pre-compute per-position amounts (including loyalty multipliers) so we
    # charge the founder the true total rather than the unadjusted base total.
    positions = db.query(ShareholderPosition).filter(
        ShareholderPosition.company_shares_id == company.id,
        ShareholderPosition.shares_owned > 0
    ).all()

    position_payouts = []  # [(position, amount, loyalty_mult, loyalty_label)]
    total_adjusted = 0.0
    for position in positions:
        # Firm receives base rate only (no loyalty bonus for the brokerage itself)
        if position.player_id == BANK_PLAYER_ID:
            mult, label = 1.0, ""
        else:
            mult, label = get_loyalty_tier(position.first_held_at)
        amt = position.shares_owned * amount_per_share * mult
        position_payouts.append((position, amt, mult, label))
        total_adjusted += amt

    if total_adjusted < 0.01:
        return

    auth_db = get_auth_db()
    try:
        founder = auth_db.query(Player).filter(Player.id == company.founder_id).first()

        from reserve_banks import can_afford_usd, spend_player_funds
        if not founder or not can_afford_usd(company.founder_id, total_adjusted):
            company.consecutive_dividend_payouts = 0
            company.dividend_warning_active = True
            company.last_dividend_warning = datetime.utcnow()
            modify_credit_score(company.founder_id, "dividend_missed")
            return
        ok, _ = spend_player_funds(founder.id, total_adjusted)
        if not ok:
            company.consecutive_dividend_payouts = 0
            company.dividend_warning_active = True
            modify_credit_score(company.founder_id, "dividend_missed")
            return
        try:
            from stats_ux import log_transaction as _lt
            _lt(company.founder_id, "dividend_paid", "money", -total_adjusted,
                f"Dividend paid: {company.ticker_symbol} — {amount_per_share:.4f}/share",
                reference_id=str(company.id))
        except Exception:
            pass
        auth_db.commit()
    finally:
        auth_db.close()

    for position, dividend_amount, loyalty_mult, loyalty_label in position_payouts:

        if dividend_amount < 0.01:
            continue

        if position.player_id == BANK_PLAYER_ID:
            firm_add_cash(dividend_amount, "dividend",
                          f"Dividend received: {company.ticker_symbol} × {position.shares_owned:,.0f} shares",
                          company_id=company.id)
            continue

        from reserve_banks import credit_usd as _credit_usd
        _credit_usd(position.player_id, dividend_amount)
        try:
            from stats_ux import log_transaction as _lt
            tier_note = f" [{loyalty_label}]" if loyalty_mult != 1.0 else ""
            _lt(position.player_id, "dividend", "money", dividend_amount,
                f"Dividend received: {company.ticker_symbol} × {position.shares_owned:,.0f} shares{tier_note}",
                reference_id=str(company.id))
        except Exception:
            pass
        # Finance sector perk: +1 credit per dividend received
        if company.sector == "Finance":
            try:
                apply_finance_sector_dividend_credit(position.player_id)
            except Exception:
                pass

    company.consecutive_dividend_payouts += 1
    company.last_dividend_date = datetime.utcnow()
    company.dividend_warning_active = False

    modify_credit_score(company.founder_id, "dividend_paid")

    # Short sellers owe the dividend to the lender for every share they borrowed.
    # Deduct from their locked collateral first; if that runs dry, charge cash.
    active_loans = db.query(ShareLoan).filter(
        ShareLoan.company_shares_id == company.id,
        ShareLoan.status == ShareLoanStatus.ACTIVE.value,
    ).all()

    if active_loans:
        from reserve_banks import spend_player_funds, credit_usd
        auth_db = get_auth_db()
        try:
            for loan in active_loans:
                div_owed = loan.shares_borrowed * amount_per_share
                if div_owed < 0.01:
                    continue

                paid = 0.0
                if loan.collateral_locked >= div_owed:
                    loan.collateral_locked -= div_owed
                    paid = div_owed
                else:
                    # Drain whatever collateral remains, then hit cash
                    paid = loan.collateral_locked
                    remaining = div_owed - paid
                    loan.collateral_locked = 0.0
                    borrower = auth_db.query(Player).filter(
                        Player.id == loan.borrower_player_id
                    ).first()
                    if borrower and borrower.cash_balance >= remaining:
                        borrower.cash_balance -= remaining
                        paid += remaining
                    # If borrower can't pay the remainder, they absorb the shortfall
                    # (lender still gets what was available; position likely force-closes soon)
                loan.total_fees_paid += paid

                # Pay the lender
                if paid > 0:
                    if loan.lender_player_id == BANK_PLAYER_ID:
                        firm_add_cash(paid, "short_dividend",
                                      f"Short div: {company.ticker_symbol}", loan.borrower_player_id)
                    else:
                        lender = auth_db.query(Player).filter(
                            Player.id == loan.lender_player_id
                        ).first()
                        if lender:
                            lender.cash_balance += paid
        finally:
            auth_db.close()


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
    
    total_needed = sum((pos.shares_owned // per_shares) * amount for pos in positions if pos.player_id != BANK_PLAYER_ID)
    
    founder_qty = inventory.get_item_quantity(company.founder_id, item)
    
    if founder_qty < total_needed:
        company.dividend_warning_active = True
        company.last_dividend_warning = datetime.utcnow()
        modify_credit_score(company.founder_id, "dividend_missed")
        return
    
    for position in positions:
        if position.player_id == BANK_PLAYER_ID:
            continue  # Firm has no commodity inventory; its share is absorbed back
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
# LISTING FEE BILLING
# ==========================

def process_listing_fees():
    """Charge founders monthly listing fees; mark distressed after LISTING_FEE_DISTRESSED_THRESHOLD misses."""
    now = datetime.utcnow()
    db = get_db()
    try:
        due_companies = db.query(CompanyShares).filter(
            CompanyShares.is_delisted == False,
            CompanyShares.listing_fee_next_due != None,
            CompanyShares.listing_fee_next_due <= now,
        ).all()

        from reserve_banks import can_afford_usd, spend_player_funds
        for company in due_companies:
            ok = False
            if can_afford_usd(company.founder_id, MONTHLY_LISTING_FEE):
                ok2, _ = spend_player_funds(company.founder_id, MONTHLY_LISTING_FEE)
                if ok2:
                    firm_add_cash(MONTHLY_LISTING_FEE, "listing_fee",
                                  f"Monthly listing fee: {company.ticker_symbol}",
                                  company.founder_id, company.id)
                    company.listing_fee_missed_count = 0
                    ok = True
            if not ok:
                company.listing_fee_missed_count = (company.listing_fee_missed_count or 0) + 1
                if company.listing_fee_missed_count >= LISTING_FEE_DISTRESSED_THRESHOLD:
                    company.trading_halted = True
                    company.halt_reason = "Listing fee delinquent — trading suspended"
                    company.trading_halted_until = now + timedelta(days=7)
                    print(f"[{BANK_NAME}] ⚠ {company.ticker_symbol} SUSPENDED — listing fee missed "
                          f"{company.listing_fee_missed_count}×")

            company.listing_fee_next_due = now + timedelta(days=30)

        db.commit()
    finally:
        db.close()


# ==========================
# EARNINGS REPORT GENERATION
# ==========================

def generate_earnings_reports():
    """Snapshot weekly revenue and EPS for every listed company."""
    now = datetime.utcnow()
    db = get_db()
    try:
        companies = db.query(CompanyShares).filter(
            CompanyShares.is_delisted == False,
            CompanyShares.share_class_label == "main",
        ).all()

        for company in companies:
            shares_out = max(company.shares_outstanding, 1)
            rev = company.revenue_7d or 0.0
            eps = rev / shares_out

            # Compute dividends_paid this period from consecutive_dividend_payouts
            div_paid = 0.0
            if company.dividend_config:
                for dc in company.dividend_config:
                    div_paid += dc.get("amount", 0.0) * shares_out

            payout = div_paid / rev if rev > 0 else 0.0

            report = CompanyEarningsReport(
                company_shares_id=company.id,
                period_end=now,
                period_days=7,
                total_revenue=rev,
                eps=eps,
                payout_ratio=min(payout, 9.99),
                dividends_paid=div_paid,
            )
            db.add(report)

            # Reset 7-day counter
            company.revenue_7d = 0.0
            company.revenue_reset_7d = now

        db.commit()
    finally:
        db.close()


# ==========================
# SHAREHOLDER PERKS
# ==========================

# Sector → perk description table (displayed on company detail and portfolio pages)
SECTOR_PERKS = {
    "Technology":        "Reduced margin interest rate (−1%) on tech sector trades",
    "Energy":            "10% discount on fuel/energy-related commodity purchases",
    "Mining":            "Priority access to commodities from Mining companies",
    "Agriculture":       "Seasonal harvest bonus: 5% extra yield from farming businesses",
    "Food & Beverage":   "5% discount on food/drink items sold at the company's venues",
    "Manufacturing":     "2% production cost reduction for compatible factory types",
    "Healthcare":        "Reduced hospital and pharmaceutical costs",
    "Retail & Commerce": "5% discount at any Retail businesses in the same sector",
    "Finance":           "1 extra credit score point per dividend received",
    "Construction":      "5% discount on land plot upgrade costs",
    "Transport":         "Reduced freight and shipping fees",
    "Real Estate":       "Priority tenant access for hotel/resort stays",
    "Media & Services":  "Reduced advertising costs for related businesses",
}


def get_player_shareholder_perks(player_id: int) -> list:
    """Return a list of perk dicts for every company the player holds shares in."""
    db = get_db()
    try:
        positions = db.query(ShareholderPosition).filter(
            ShareholderPosition.player_id == player_id,
            ShareholderPosition.shares_owned > 0,
        ).all()

        perks = []
        seen_sectors = set()
        for pos in positions:
            company = db.query(CompanyShares).filter(
                CompanyShares.id == pos.company_shares_id,
                CompanyShares.is_delisted == False,
            ).first()
            if not company:
                continue
            sector = company.sector or "General"
            if sector in seen_sectors:
                continue  # deduplicate per sector
            seen_sectors.add(sector)
            perk_desc = SECTOR_PERKS.get(sector)
            if perk_desc:
                _, loyalty_label = get_loyalty_tier(pos.first_held_at)
                perks.append({
                    "ticker": company.ticker_symbol,
                    "company_name": company.company_name,
                    "sector": sector,
                    "perk": perk_desc,
                    "shares": pos.shares_owned,
                    "loyalty": loyalty_label,
                })
        return perks
    finally:
        db.close()


def apply_finance_sector_dividend_credit(player_id: int):
    """Finance sector perk: award +1 credit score when a dividend is received."""
    db = get_db()
    try:
        finance_pos = db.query(ShareholderPosition).join(
            CompanyShares, CompanyShares.id == ShareholderPosition.company_shares_id
        ).filter(
            ShareholderPosition.player_id == player_id,
            ShareholderPosition.shares_owned > 0,
            CompanyShares.sector == "Finance",
            CompanyShares.is_delisted == False,
        ).first()
        if finance_pos:
            modify_credit_score(player_id, "trade_completed")  # +1 point
    finally:
        db.close()


# ==========================
# LOCKUP CHECK (PUBLIC HELPER)
# ==========================

def is_founder_locked_up(company_id: int, player_id: int) -> bool:
    """Return True if the founder is still inside the post-IPO lockup window."""
    db = get_db()
    try:
        company = db.query(CompanyShares).filter(CompanyShares.id == company_id).first()
        if not company or company.founder_id != player_id:
            return False
        if not company.lockup_expires_at:
            return False
        return datetime.utcnow() < company.lockup_expires_at
    finally:
        db.close()


# ==========================
# INITIALIZATION
# ==========================

def initialize():
    print(f"[{BANK_NAME}] Creating database tables...")
    Base.metadata.create_all(bind=engine)

    # Add new columns to existing tables if they don't exist yet (safe for existing DBs)
    from database import run_ddl_migration
    run_ddl_migration(engine, [
        "ALTER TABLE company_shares ADD COLUMN IF NOT EXISTS can_relist_after TIMESTAMP",
        "ALTER TABLE company_shares ADD COLUMN IF NOT EXISTS delisted_at TIMESTAMP",
        # Quad-Class sub-record linkage
        "ALTER TABLE company_shares ADD COLUMN IF NOT EXISTS parent_company_id INTEGER",
        "ALTER TABLE company_shares ADD COLUMN IF NOT EXISTS share_class_label VARCHAR DEFAULT 'main'",
        # Governance tables (created by Base.metadata above, DDL guard for safety)
        "CREATE INDEX IF NOT EXISTS ix_company_proposals_company ON company_proposals (company_shares_id)",
        "CREATE INDEX IF NOT EXISTS ix_company_votes_proposal ON company_votes (proposal_id)",
        # Structured parameter for executable governance proposals
        "ALTER TABLE company_proposals ADD COLUMN IF NOT EXISTS proposal_param JSON",
        # Short loans: remove artificial expiry — positions are open-ended
        "ALTER TABLE share_loans ALTER COLUMN due_date DROP NOT NULL",
        # Phase-2 brokerage improvements
        "ALTER TABLE company_shares ADD COLUMN IF NOT EXISTS sector VARCHAR",
        "ALTER TABLE company_shares ADD COLUMN IF NOT EXISTS lockup_expires_at TIMESTAMP",
        "ALTER TABLE company_shares ADD COLUMN IF NOT EXISTS profit_siphon_rate FLOAT DEFAULT 0.0",
        "ALTER TABLE company_shares ADD COLUMN IF NOT EXISTS dividend_escrow_balance FLOAT DEFAULT 0.0",
        "ALTER TABLE company_shares ADD COLUMN IF NOT EXISTS listing_fee_next_due TIMESTAMP",
        "ALTER TABLE company_shares ADD COLUMN IF NOT EXISTS listing_fee_missed_count INTEGER DEFAULT 0",
        "ALTER TABLE company_shares ADD COLUMN IF NOT EXISTS revenue_7d FLOAT DEFAULT 0.0",
        "ALTER TABLE company_shares ADD COLUMN IF NOT EXISTS revenue_30d FLOAT DEFAULT 0.0",
        "ALTER TABLE company_shares ADD COLUMN IF NOT EXISTS revenue_reset_7d TIMESTAMP",
        "ALTER TABLE company_shares ADD COLUMN IF NOT EXISTS revenue_reset_30d TIMESTAMP",
        "ALTER TABLE shareholder_positions ADD COLUMN IF NOT EXISTS first_held_at TIMESTAMP",
    ])

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
    print(f"[{BANK_NAME}] WADSWORTH BROKERAGE FIRM - INITIALIZED")
    print(f"[{BANK_NAME}] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"[{BANK_NAME}] Cash Reserves: ${firm.cash_reserves:,.2f}")
    print(f"[{BANK_NAME}] IPO Types: {len(IPO_CONFIG)}")
    print(f"[{BANK_NAME}]   • Direct Listing ($5k flat fee, no underwriter)")
    print(f"[{BANK_NAME}]   • Underwritten IPO (7% discount, guaranteed capital)")
    print(f"[{BANK_NAME}]   • Income Shares IPO (3% discount, mandatory 10% dividend)")
    print(f"[{BANK_NAME}] WCE Commodity Lending: ACTIVE")
    print(f"[{BANK_NAME}] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


# ==========================
# ANNUITY FUNCTIONS
# ==========================

def _player_sym(player_id: int) -> str:
    """Return the display currency symbol for a player (e.g. '$', '¥', '£')."""
    try:
        from reserve_banks import get_player_display_currency
        return get_player_display_currency(player_id).get("symbol", "$")
    except Exception:
        return "$"


def _calc_pmt(principal: float, annual_rate: float, periods_per_year: int, n: int) -> float:
    """Standard annuity PMT with zero-division and overflow guards."""
    if n <= 0 or principal <= 0 or periods_per_year <= 0:
        return 0.0
    r = annual_rate / periods_per_year
    if r <= 0:
        return round(principal / n, 2)
    try:
        pmt = principal * r / (1.0 - (1.0 + r) ** (-n))
        return round(pmt, 2)
    except (OverflowError, ZeroDivisionError, ValueError):
        return round(principal / n, 2)


def _get_surrender_charge(contract: AnnuityContract, current_tick: int) -> float:
    """Return the applicable surrender charge rate (0.0–0.07) based on term elapsed."""
    try:
        if contract.phase == "payout":
            n = contract.total_payments or 1
            pct = (contract.payments_made or 0) / max(1, n)
        elif contract.accumulation_term_days and contract.accumulation_end_tick:
            total_ticks = contract.accumulation_term_days * 17_280
            elapsed = current_tick - (contract.accumulation_end_tick - total_ticks)
            pct = min(1.0, elapsed / max(1, total_ticks))
        else:
            # Open-ended deferred: flat 5% until 1 contract year elapsed, then 0%
            year_ticks = ANNUITY_YEAR_TICKS
            elapsed = current_tick - (contract.contract_year_tick or current_tick)
            pct = min(1.0, elapsed / max(1, year_ticks))
        tier = min(7, int(pct * 8))
        return ANNUITY_SURRENDER_SCHEDULE[tier]
    except Exception:
        return 0.05


def _calc_annuity_tax(payment_amount: float, principal_per_pmt: float, is_qualified: bool) -> float:
    """Tax on each annuity payment: qualified = full pmt × 20%; non-qualified = interest × 15%."""
    pa  = payment_amount   or 0.0
    ppp = principal_per_pmt or 0.0
    if is_qualified:
        return round(pa * ANNUITY_QUAL_TAX_RATE, 4)
    interest = max(0.0, pa - ppp)
    return round(interest * ANNUITY_NONQUAL_TAX_RATE, 4)


def open_immediate_annuity(player_id: int, purchase_price: float, term_days: int,
                           payment_frequency: str, is_qualified: bool, current_tick: int) -> dict:
    """Purchase a single-premium immediate annuity (SPIA). Payments start at next interval."""
    rate = ANNUITY_IMMEDIATE_RATES.get(term_days)
    if not rate:
        return {"ok": False, "error": f"Invalid term. Choose from: {list(ANNUITY_IMMEDIATE_RATES.keys())} days"}
    if payment_frequency not in ANNUITY_PAYMENT_TICKS:
        return {"ok": False, "error": "Payment frequency must be 'weekly' or 'monthly'"}
    if (purchase_price or 0.0) < ANNUITY_IMMEDIATE_MIN:
        return {"ok": False, "error": f"Minimum purchase is {ANNUITY_IMMEDIATE_MIN:,.0f}"}

    from reserve_banks import spend_player_funds, credit_usd
    ok, msg = spend_player_funds(player_id, purchase_price)
    if not ok:
        return {"ok": False, "error": msg}

    # Issuance fee for non-qualified contracts (like bond issuance fee)
    fee = 0.0
    if not is_qualified:
        fee = round(purchase_price * ANNUITY_ISSUANCE_FEE, 2)
        credit_usd(0, fee)   # government player_id = 0

    firm_add_cash(purchase_price, "annuity_premium", f"SPIA premium from player {player_id}", player_id=player_id)

    periods_per_year = 52 if payment_frequency == "weekly" else 12
    n = max(1, round(term_days / 365.0 * periods_per_year))
    pmt = _calc_pmt(purchase_price, rate, periods_per_year, n)

    db = get_db()
    try:
        contract = AnnuityContract(
            player_id=player_id,
            annuity_type="immediate",
            is_qualified=is_qualified,
            phase="payout",
            initial_premium=purchase_price,
            total_contributions=purchase_price,
            accumulated_value=purchase_price,
            annuitized_value=purchase_price,
            annuitized_at=datetime.utcnow(),
            payout_rate=rate,
            payment_frequency=payment_frequency,
            payment_amount=pmt,
            total_payments=n,
            payments_remaining=n,
            payments_made=0,
            next_payment_tick=max(current_tick + 1, current_tick + ANNUITY_PAYMENT_TICKS[payment_frequency]),
            contract_year_tick=current_tick,
            payout_term_days=term_days,
            status="active",
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)
        cid = contract.id
    except Exception as e:
        db.rollback()
        # Funds were already deducted — refund the player so no money is lost
        try:
            from reserve_banks import credit_usd as _cu
            _cu(player_id, purchase_price)
            firm_deduct_cash(purchase_price, "refund", f"Compensating refund: SPIA creation failed")
        except Exception:
            pass
        return {"ok": False, "error": str(e)}
    finally:
        db.close()

    try:
        from stats_ux import log_transaction as _lt
        _sym = _player_sym(player_id)
        tax_label = "qualified — full pmt taxed 20%" if is_qualified else "non-qualified — interest taxed 15%"
        _lt(player_id, "annuity_purchase", "money", -(purchase_price + fee),
            description=f"Opened {term_days}-day SPIA @ {rate*100:.0f}% ({tax_label}) — "
                        f"{n} {payment_frequency} payments of {_sym}{pmt:,.2f}",
            reference_id=str(cid))
    except Exception:
        pass

    try:
        from push_ux import create_game_notification
        _sym = _player_sym(player_id)
        qual_label = "Qualified" if is_qualified else "Non-qualified"
        create_game_notification(
            player_id,
            "📋 Immediate Annuity Opened",
            f"{qual_label} {_sym}{purchase_price:,.0f} SPIA @ {rate*100:.0f}% — "
            f"{n} {payment_frequency} payments of {_sym}{pmt:,.2f}",
            url="/brokerage/annuities",
        )
    except Exception:
        pass

    return {"ok": True, "contract_id": cid, "payment_amount": pmt, "total_payments": n,
            "issuance_fee": fee, "rate": rate}


def open_deferred_annuity(player_id: int, initial_premium: float,
                          accumulation_term_days, is_qualified: bool, current_tick: int) -> dict:
    """Open a flexible-premium deferred annuity. Contributions grow at 5% annual until annuitized."""
    initial_premium = initial_premium or 0.0
    if initial_premium > 0 and initial_premium < 1000.0:
        return {"ok": False, "error": "Minimum opening deposit is 1,000 (or 0 to open empty)"}

    acc_end_tick = None
    if accumulation_term_days:
        try:
            accumulation_term_days = int(accumulation_term_days)
            if accumulation_term_days not in ANNUITY_IMMEDIATE_RATES:
                return {"ok": False, "error": f"Accumulation term must be one of: {list(ANNUITY_IMMEDIATE_RATES.keys())} days"}
            acc_end_tick = current_tick + accumulation_term_days * 17_280
        except (ValueError, TypeError):
            return {"ok": False, "error": "Invalid accumulation term"}

    if initial_premium > 0:
        from reserve_banks import spend_player_funds, credit_usd
        ok, msg = spend_player_funds(player_id, initial_premium)
        if not ok:
            return {"ok": False, "error": msg}
        if not is_qualified:
            fee = round(initial_premium * ANNUITY_ISSUANCE_FEE, 2)
            credit_usd(0, fee)
            firm_add_cash(initial_premium, "annuity_premium",
                          f"Deferred annuity opening from player {player_id}", player_id=player_id)
        else:
            firm_add_cash(initial_premium, "annuity_premium",
                          f"Deferred annuity opening (qualified) from player {player_id}", player_id=player_id)

    db = get_db()
    try:
        contract = AnnuityContract(
            player_id=player_id,
            annuity_type="deferred",
            is_qualified=is_qualified,
            phase="accumulation",
            initial_premium=initial_premium,
            total_contributions=initial_premium,
            accumulated_value=initial_premium,
            credited_rate=ANNUITY_CREDITED_RATE,
            next_credit_tick=current_tick + ANNUITY_CREDIT_INTERVAL,
            accumulation_term_days=accumulation_term_days if accumulation_term_days else None,
            accumulation_end_tick=acc_end_tick,
            contract_year_tick=current_tick,
            status="active",
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)
        cid = contract.id
    except Exception as e:
        db.rollback()
        # Funds were already deducted — refund the player so no money is lost
        if initial_premium > 0:
            try:
                from reserve_banks import credit_usd as _cu
                _cu(player_id, initial_premium)
                firm_deduct_cash(initial_premium, "refund", f"Compensating refund: deferred annuity creation failed")
            except Exception:
                pass
        return {"ok": False, "error": str(e)}
    finally:
        db.close()

    try:
        from stats_ux import log_transaction as _lt
        if initial_premium > 0:
            _sym = _player_sym(player_id)
            _lt(player_id, "annuity_contribution", "money", -initial_premium,
                description=f"Opened deferred annuity — initial deposit {_sym}{initial_premium:,.2f}",
                reference_id=str(cid))
    except Exception:
        pass

    try:
        from push_ux import create_game_notification
        qual_label = "Qualified" if is_qualified else "Non-qualified"
        term_label = f"{accumulation_term_days}-day term" if accumulation_term_days else "open-ended"
        create_game_notification(
            player_id,
            "💼 Deferred Annuity Opened",
            f"{qual_label} deferred annuity ({term_label}) — "
            f"earning {ANNUITY_CREDITED_RATE*100:.0f}% annual during accumulation",
            url="/brokerage/annuities",
        )
    except Exception:
        pass

    return {"ok": True, "contract_id": cid, "initial_premium": initial_premium}


def contribute_to_deferred(player_id: int, contract_id: int, amount: float, current_tick: int) -> dict:
    """Add funds to a deferred annuity's accumulation account."""
    if (amount or 0.0) < ANNUITY_DEFERRED_CONTRIB_MIN:
        return {"ok": False, "error": f"Minimum contribution is {ANNUITY_DEFERRED_CONTRIB_MIN:,.0f}"}

    db = get_db()
    try:
        contract = db.query(AnnuityContract).filter(
            AnnuityContract.id == contract_id,
            AnnuityContract.player_id == player_id,
            AnnuityContract.phase == "accumulation",
            AnnuityContract.status == "active",
        ).first()
        if not contract:
            return {"ok": False, "error": "Contract not found or not in accumulation phase"}

        from reserve_banks import spend_player_funds
        ok, msg = spend_player_funds(player_id, amount)
        if not ok:
            return {"ok": False, "error": msg}

        firm_add_cash(amount, "annuity_premium",
                      f"Deferred annuity contribution from player {player_id}", player_id=player_id)
        contract.accumulated_value = (contract.accumulated_value or 0.0) + amount
        contract.total_contributions = (contract.total_contributions or 0.0) + amount

        contrib = AnnuityContribution(
            contract_id=contract_id,
            player_id=player_id,
            amount=amount,
            tick=current_tick,
        )
        db.add(contrib)
        db.commit()
        new_balance = contract.accumulated_value
    except Exception as e:
        db.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        db.close()

    try:
        from stats_ux import log_transaction as _lt
        _sym = _player_sym(player_id)
        _lt(player_id, "annuity_contribution", "money", -amount,
            description=f"Contributed {_sym}{amount:,.2f} to deferred annuity #{contract_id}",
            reference_id=str(contract_id))
    except Exception:
        pass

    return {"ok": True, "new_balance": new_balance}


def annuitize_deferred(player_id: int, contract_id: int, payout_term_days: int,
                       payment_frequency: str, current_tick: int) -> dict:
    """Convert a deferred annuity's accumulated value into a fixed payout stream."""
    rate = ANNUITY_IMMEDIATE_RATES.get(payout_term_days)
    if not rate:
        return {"ok": False, "error": f"Invalid payout term. Choose from: {list(ANNUITY_IMMEDIATE_RATES.keys())} days"}
    if payment_frequency not in ANNUITY_PAYMENT_TICKS:
        return {"ok": False, "error": "Frequency must be 'weekly' or 'monthly'"}

    db = get_db()
    try:
        contract = db.query(AnnuityContract).filter(
            AnnuityContract.id == contract_id,
            AnnuityContract.player_id == player_id,
            AnnuityContract.phase == "accumulation",
            AnnuityContract.status == "active",
        ).first()
        if not contract:
            return {"ok": False, "error": "Contract not found or not in accumulation phase"}

        principal = contract.accumulated_value or 0.0
        if principal < ANNUITY_MIN_TO_ANNUITIZE:
            return {"ok": False, "error": f"Minimum {ANNUITY_MIN_TO_ANNUITIZE:,.0f} required to annuitize"}

        periods_per_year = 52 if payment_frequency == "weekly" else 12
        n = max(1, round(payout_term_days / 365.0 * periods_per_year))
        pmt = _calc_pmt(principal, rate, periods_per_year, n)

        contract.phase = "payout"
        contract.annuitized_at = datetime.utcnow()
        contract.annuitized_value = principal
        contract.payout_rate = rate
        contract.payout_term_days = payout_term_days
        contract.payment_frequency = payment_frequency
        contract.payment_amount = pmt
        contract.total_payments = n
        contract.payments_remaining = n
        contract.payments_made = 0
        contract.next_payment_tick = max(current_tick + 1, current_tick + ANNUITY_PAYMENT_TICKS[payment_frequency])
        db.commit()
        cid = contract.id
    except Exception as e:
        db.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        db.close()

    try:
        from stats_ux import log_transaction as _lt
        _sym = _player_sym(player_id)
        _lt(player_id, "annuity_purchase", "money", 0.0,
            description=f"Annuitized deferred contract #{contract_id} — "
                        f"{_sym}{principal:,.2f} @ {rate*100:.0f}% for {payout_term_days}d — "
                        f"{n} {payment_frequency} payments of {_sym}{pmt:,.2f}",
            reference_id=str(contract_id))
    except Exception:
        pass

    try:
        from push_ux import create_game_notification
        _sym = _player_sym(player_id)
        create_game_notification(
            player_id,
            "▶ Deferred Annuity Annuitized",
            f"{_sym}{principal:,.0f} locked in — {n} {payment_frequency} payments of {_sym}{pmt:,.2f} starting soon",
            url="/brokerage/annuities",
        )
    except Exception:
        pass

    return {"ok": True, "contract_id": cid, "payment_amount": pmt, "total_payments": n, "rate": rate}


def surrender_annuity(player_id: int, contract_id: int, current_tick: int) -> dict:
    """Surrender an annuity for remaining principal minus surrender charge."""
    db = get_db()
    try:
        contract = db.query(AnnuityContract).filter(
            AnnuityContract.id == contract_id,
            AnnuityContract.player_id == player_id,
            AnnuityContract.status == "active",
        ).first()
        if not contract:
            return {"ok": False, "error": "Contract not found or already closed"}

        if contract.phase == "payout":
            ann_val = contract.annuitized_value or contract.total_contributions or 0.0
            n = max(1, contract.total_payments or 1)
            remaining = (contract.payments_remaining or 0) / n
            base = ann_val * remaining
        else:
            base = contract.accumulated_value or 0.0

        # Free withdrawal: up to 10% of base per contract year with no charge
        year_elapsed = current_tick - (contract.contract_year_tick or current_tick)
        if year_elapsed >= ANNUITY_YEAR_TICKS:
            contract.free_withdrawal_used = 0.0
            contract.contract_year_tick = current_tick

        free_remaining = max(0.0, base * ANNUITY_FREE_WITHDRAWAL_PCT - (contract.free_withdrawal_used or 0.0))
        free_portion = min(base, free_remaining)
        charged_portion = max(0.0, base - free_portion)

        charge_rate = _get_surrender_charge(contract, current_tick)
        payout = round(free_portion + charged_portion * (1.0 - charge_rate), 2)
        payout = max(0.0, payout)

        from reserve_banks import credit_usd
        if not firm_deduct_cash(payout, "annuity_surrender", f"Surrender payout to player {player_id}"):
            return {"ok": False, "error": "Firm reserves insufficient to process surrender — try again later"}
        credit_usd(player_id, payout)

        contract.status = "surrendered"
        contract.phase = "surrendered"
        contract.surrender_payout = payout
        contract.completed_at = datetime.utcnow()
        db.commit()
    except Exception as e:
        db.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        db.close()

    try:
        from stats_ux import log_transaction as _lt
        _sym = _player_sym(player_id)
        _lt(player_id, "annuity_surrender", "money", payout,
            description=f"Annuity #{contract_id} surrendered — received {_sym}{payout:,.2f} "
                        f"(surrender charge: {charge_rate*100:.0f}%)",
            reference_id=str(contract_id))
    except Exception:
        pass

    try:
        from push_ux import create_game_notification, send_push_notification
        _sym = _player_sym(player_id)
        create_game_notification(
            player_id,
            "🔓 Annuity Surrendered",
            f"Received {_sym}{payout:,.2f} — surrender charge {charge_rate*100:.0f}%",
            url="/brokerage/annuities",
        )
    except Exception:
        pass

    return {"ok": True, "surrender_payout": payout, "charge_rate": charge_rate}


def get_player_annuities(player_id: int, current_tick: int) -> dict:
    """Return all annuity contracts for a player, grouped by status."""
    db = get_db()
    try:
        contracts = db.query(AnnuityContract).filter(
            AnnuityContract.player_id == player_id,
        ).order_by(AnnuityContract.opened_at.desc()).all()
    finally:
        db.close()

    active, completed, surrendered = [], [], []
    for c in contracts:
        pct = 0.0
        if c.phase == "payout" and c.total_payments:
            pct = (c.payments_made or 0) / max(1, c.total_payments)
        elif c.phase == "accumulation" and c.accumulation_term_days and c.accumulation_end_tick:
            total_t = c.accumulation_term_days * 17_280
            elapsed = current_tick - (c.accumulation_end_tick - total_t)
            pct = min(1.0, max(0.0, elapsed / max(1, total_t)))

        charge_rate = _get_surrender_charge(c, current_tick)

        if c.phase == "payout":
            ann_val = c.annuitized_value or c.total_contributions or 0.0
            remaining_frac = (c.payments_remaining or 0) / max(1, c.total_payments or 1)
            surr_base = ann_val * remaining_frac
        else:
            surr_base = c.accumulated_value or 0.0
        surr_est = round(surr_base * (1.0 - charge_rate), 2)

        row = {
            "id": c.id,
            "annuity_type": c.annuity_type,
            "is_qualified": c.is_qualified,
            "phase": c.phase,
            "status": c.status,
            "initial_premium": c.initial_premium or 0.0,
            "total_contributions": c.total_contributions or 0.0,
            "accumulated_value": c.accumulated_value or 0.0,
            "credited_rate": c.credited_rate or ANNUITY_CREDITED_RATE,
            "next_credit_tick": c.next_credit_tick,
            "accumulation_term_days": c.accumulation_term_days,
            "accumulation_end_tick": c.accumulation_end_tick,
            "payout_rate": c.payout_rate,
            "payment_frequency": c.payment_frequency,
            "payment_amount": c.payment_amount or 0.0,
            "total_payments": c.total_payments,
            "payments_made": c.payments_made or 0,
            "payments_remaining": c.payments_remaining,
            "next_payment_tick": c.next_payment_tick,
            "total_paid_out": c.total_paid_out or 0.0,
            "total_interest_paid": c.total_interest_paid or 0.0,
            "annuitized_value": c.annuitized_value,
            "payout_term_days": c.payout_term_days,
            "pct_complete": round(pct * 100, 1),
            "surrender_estimate": surr_est,
            "charge_rate": charge_rate,
            "opened_at": c.opened_at.isoformat() if c.opened_at else None,
            "annuitized_at": c.annuitized_at.isoformat() if c.annuitized_at else None,
            "completed_at": c.completed_at.isoformat() if c.completed_at else None,
        }
        if c.status == "surrendered":
            surrendered.append(row)
        elif c.status == "completed":
            completed.append(row)
        else:
            active.append(row)

    return {"active": active, "completed": completed, "surrendered": surrendered}


# ── Tick sub-handlers ─────────────────────────────────────────────────────────

def _process_annuity_credits(current_tick: int):
    """Credit monthly interest to deferred annuity accumulation accounts."""
    db = get_db()
    credit_log = []  # (player_id, contract_id, interest_amount, rate)
    try:
        contracts = db.query(AnnuityContract).filter(
            AnnuityContract.phase == "accumulation",
            AnnuityContract.status == "active",
            AnnuityContract.next_credit_tick <= current_tick,
        ).all()
        for c in contracts:
            acc = c.accumulated_value or 0.0
            rate = c.credited_rate or ANNUITY_CREDITED_RATE
            interest = round(acc * rate / 12.0, 4)
            c.accumulated_value = acc + interest
            c.next_credit_tick = current_tick + ANNUITY_CREDIT_INTERVAL
            credit_log.append((c.player_id, c.id, interest, rate))
        if contracts:
            db.commit()
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        print(f"[Brokerage] Annuity credit error: {e}")
    finally:
        db.close()

    for pid, cid, interest_amount, rate in credit_log:
        try:
            from stats_ux import log_transaction as _lt
            _lt(pid, "annuity_interest", "money", interest_amount,
                description=f"Deferred annuity interest @ {rate*100:.1f}% annual (monthly credit)",
                reference_id=str(cid))
        except Exception:
            pass


def _process_annuity_payments(current_tick: int):
    """Process due annuity payments to players."""
    from reserve_banks import credit_usd
    db = get_db()
    # Cache computed values for the notification pass (avoids second exec DB lookup)
    pmt_cache = {}  # contract_id -> (net_pmt, tax)
    contracts = []
    try:
        contracts = db.query(AnnuityContract).filter(
            AnnuityContract.phase == "payout",
            AnnuityContract.status == "active",
            AnnuityContract.next_payment_tick <= current_tick,
        ).all()

        for c in contracts:
            pmt = c.payment_amount or 0.0
            if pmt <= 0:
                pmt_cache[c.id] = (0.0, 0.0)
                continue

            ann_val = c.annuitized_value or c.total_contributions or 0.0
            n = max(1, c.total_payments or 1)
            principal_per_pmt = ann_val / n
            tax = _calc_annuity_tax(pmt, principal_per_pmt, c.is_qualified or False)

            exec_bonus = 0.0
            try:
                from executive import get_player_job_bonus, get_db as exec_get_db
                _edb = exec_get_db()
                try:
                    exec_bonus = get_player_job_bonus(_edb, c.player_id, "banking") or 0.0
                finally:
                    _edb.close()
            except Exception:
                pass

            net_pmt = round(max(0.0, pmt * (1.0 + exec_bonus) - tax), 4)
            pmt_cache[c.id] = (net_pmt, tax)

            if not firm_deduct_cash(pmt, "annuity_payment", f"Annuity payment to player {c.player_id}"):
                # Firm reserves too low — defer to next normal payment interval.
                # Must update next_payment_tick or this contract retries every tick.
                pmt_cache[c.id] = (0.0, 0.0)
                freq = c.payment_frequency or "monthly"
                c.next_payment_tick = current_tick + ANNUITY_PAYMENT_TICKS.get(freq, 518_400)
                print(f"[Brokerage] Insufficient reserves for annuity payment on contract {c.id} — deferred to tick {c.next_payment_tick}")
                continue
            credit_usd(c.player_id, net_pmt)
            if tax > 0:
                credit_usd(0, tax)

            c.payments_made = (c.payments_made or 0) + 1
            c.payments_remaining = max(0, (c.payments_remaining or 1) - 1)
            c.total_paid_out = (c.total_paid_out or 0.0) + pmt
            c.total_interest_paid = (c.total_interest_paid or 0.0) + max(0.0, pmt - principal_per_pmt)

            if c.payments_remaining <= 0:
                c.status = "completed"
                c.phase = "completed"
                c.completed_at = datetime.utcnow()
            else:
                freq = c.payment_frequency or "monthly"
                c.next_payment_tick = current_tick + ANNUITY_PAYMENT_TICKS.get(freq, 518_400)

        if contracts:
            db.commit()
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        print(f"[Brokerage] Annuity payment error: {e}")
        return
    finally:
        db.close()

    # Notifications and ledger entries — outside DB session, use cached pmt values
    for c in contracts:
        try:
            net_pmt, tax = pmt_cache.get(c.id, (0.0, 0.0))
            if net_pmt <= 0:
                continue
            from stats_ux import log_transaction as _lt
            from push_ux import create_game_notification, send_push_notification
            import auth as _auth

            _sym = _player_sym(c.player_id)
            _lt(c.player_id, "annuity_payout", "money", net_pmt,
                description=f"Annuity payment {c.payments_made}/{c.total_payments} — "
                            f"{_sym}{net_pmt:,.2f} net (tax: {_sym}{tax:,.2f})",
                reference_id=str(c.id))

            create_game_notification(
                c.player_id,
                "💰 Annuity Payment",
                f"{_sym}{net_pmt:,.2f} received — payment {c.payments_made}/{c.total_payments or '?'}",
                url="/brokerage/annuities",
            )

            if c.status == "completed":
                _lt(c.player_id, "annuity_maturity", "money", 0.0,
                    description=f"Annuity #{c.id} matured — all {c.total_payments or '?'} payments complete, "
                                f"{_sym}{(c.total_paid_out or 0.0):,.2f} total received",
                    reference_id=str(c.id))
                try:
                    _adb = _auth.get_db()
                    _player = _adb.query(_auth.Player).filter(_auth.Player.id == c.player_id).first()
                    can_push = getattr(_player, "notif_push_annuities", True) if _player else True
                    _adb.close()
                except Exception:
                    can_push = True
                if can_push:
                    send_push_notification(
                        c.player_id,
                        "🎉 Annuity Matured",
                        f"Your annuity is complete! All {c.total_payments} payments paid. "
                        f"Total received: {_sym}{(c.total_paid_out or 0.0):,.2f}",
                        url="/brokerage/annuities",
                        notif_type="annuities",
                    )
        except Exception:
            pass


def _process_annuity_auto_annuitizations(current_tick: int):
    """Auto-annuitize deferred contracts whose accumulation term has ended."""
    db = get_db()
    try:
        contracts = db.query(AnnuityContract).filter(
            AnnuityContract.phase == "accumulation",
            AnnuityContract.status == "active",
            AnnuityContract.accumulation_end_tick.isnot(None),
            AnnuityContract.accumulation_end_tick <= current_tick,
        ).all()
        due = [(c.id, c.player_id, c.accumulated_value or 0.0) for c in contracts]
    finally:
        db.close()

    for cid, pid, acc_val in due:
        try:
            if acc_val >= ANNUITY_MIN_TO_ANNUITIZE:
                annuitize_deferred(pid, cid, 365, "monthly", current_tick)
            else:
                # Not enough to annuitize — surrender it back
                surrender_annuity(pid, cid, current_tick)
        except Exception as e:
            print(f"[Brokerage] Auto-annuitization error for contract {cid}: {e}")


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
        resolve_proposals()

        try:
            from corporate_actions import process_corporate_actions
            process_corporate_actions()
        except ImportError:
            pass
    
    process_dividends(current_tick)

    _process_annuity_credits(current_tick)
    _process_annuity_payments(current_tick)
    _process_annuity_auto_annuitizations(current_tick)

    # Monthly listing fees: check every hour
    if current_tick % 3600 == 0:
        process_listing_fees()

    # Weekly earnings snapshots: every 604800 ticks (1 week in seconds)
    if current_tick % 604800 == 0:
        generate_earnings_reports()

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
    'create_player_ipo', 'create_ipo', 'delist_company', 'calculate_delisting_cost',
    'call_shares',
    'create_proposal', 'cast_vote', 'resolve_proposals', 'get_voting_power',
    'CompanyProposal', 'CompanyVote',
    'IPOType', 'IPO_CONFIG', 'ShareClass',
    'CALL_PREMIUM', 'CLASS_A_VOTE_MULTIPLIER', 'PROPOSAL_DURATION_HOURS',
    'calculate_margin_multiplier', 'record_price',
    'calculate_stock_volatility', 'calculate_commodity_volatility',
    'short_sell_shares', 'close_short_position', 'recall_shares',
    'MAX_SHORT_FLOAT_PCT', 'get_short_interest_multiplier',
    'list_commodity_for_lending', 'borrow_commodity', 'return_commodity',
    'extend_commodity_loan', 'calculate_commodity_due_date',
    'CompanyShares', 'ShareholderPosition', 'ShareLoan', 'CompanyProposal', 'CompanyVote',
    'CommodityListing', 'CommodityLoan', 'BrokerageLien',
    'PriceHistory', 'MarginCall', 'FirmTransaction',
    'DividendType', 'DividendFrequency', 'ShareLoanStatus',
    'CommodityLoanStatus', 'LiquidationLevel',
    # New Phase-2 additions
    'CompanyEarningsReport',
    'SHARE_CLASS_DESCRIPTIONS', 'LOYALTY_TIERS', 'SECTOR_PERKS',
    'IPO_LOCKUP_DAYS', 'MONTHLY_LISTING_FEE',
    'get_loyalty_tier', 'derive_sector', 'is_founder_locked_up',
    'process_listing_fees', 'generate_earnings_reports',
    'get_player_shareholder_perks',
]
