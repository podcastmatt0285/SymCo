"""
counties.py

County management module for the economic simulation.
Counties are democratically founded federations of Cities.

Each county has a NATIVE CRYPTOCURRENCY (like a Layer 1 blockchain):
- The county token is the native/base token on the county's blockchain
- City members mine the native token by depositing city currency as energy
- The native token is required for governance voting (burn-to-vote)
- In the future, city members can mint their own tokens ("shitcoins")
  on their county's blockchain using the native token as gas/base
- Supply is capped at 21 million with Bitcoin-like halving rewards
- The blockchain requires ENERGY (mining deposits) to function at all

Handles:
- County creation (Join/Form County petition system)
- Government review period (1 day) for county petitions
- County membership voting (city member vote, mayors get 3 votes)
- County Parliament (lower house: all city members, upper house: mayors with 3 votes)
- County Mining Node (deposit city currency, mine county crypto)
- County cryptocurrency with value pegged to total member cash / 1,000,000,000
- Supply cap with halving rewards (50 -> 25 -> 12.5 -> ... per payout)
- County treasury (holds cash from token purchases, pays out on sales)
- Wadsworth Crypto Exchange (crypto-to-crypto, crypto-to-cash, cash-to-crypto)
- Token info screens with full tokenomics data
- Real-time price ticker with movement indicators
"""

from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from sqlalchemy import create_engine, Column, String, Float, DateTime, Integer, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from enum import Enum
from stats_ux import log_transaction
import math
import hashlib
import random

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
MAX_COUNTY_CITIES = 5
GOVERNMENT_PLAYER_ID = 0
GOV_REVIEW_DURATION_TICKS = 17280  # 24 hours at 5 sec/tick
COUNTY_PETITION_POLL_DURATION_TICKS = 17280  # 24 hours
MAYOR_VOTE_WEIGHT = 3
CRYPTO_PEG_DIVISOR = 1_000_000_000  # Price = total member cash value / 1B
MIN_MINING_DEPOSIT = 1.0
MINING_PAYOUT_INTERVAL_TICKS = 720  # Every hour (720 ticks * 5s = 3600s)
MINING_ENERGY_CONSUMPTION_RATE = 0.10  # 10% of deposits consumed per payout cycle
MINING_REWARD_MULTIPLIER = 1.0  # Crypto minted per unit of consumed energy value
EXCHANGE_FEE_PERCENT = 0.02  # 2% fee on all exchange transactions
EXCHANGE_FEE_TO_GOV_PERCENT = 0.50  # 50% of fees go to government

# Token Supply & Halving (Bitcoin-like)
MAX_TOKEN_SUPPLY = 21_000_000.0  # 21 million max supply per token
INITIAL_BLOCK_REWARD = 50.0  # Initial mining reward per payout cycle
HALVING_INTERVAL = 210_000.0  # Halve reward after this many tokens minted (like BTC blocks)
MIN_BLOCK_REWARD = 0.00000001  # Smallest possible reward (satoshi equivalent)

# Price snapshot interval
PRICE_SNAPSHOT_INTERVAL_TICKS = 720  # Snapshot price every hour (same as mining)

# Intercounty Governance Voting
GOVERNANCE_VOTE_CYCLE_TICKS = 86400  # 5 days (5 * 17280 ticks/day)
GOVERNANCE_PROPOSAL_WINDOW_TICKS = 51840  # First 3 days for proposals (3 * 17280)
GOVERNANCE_VOTING_WINDOW_TICKS = 34560  # Last 2 days for voting (2 * 17280)
MIN_GOVERNANCE_BURN = 0.000001  # Minimum tokens to burn per vote

# ==========================
# ENUMS
# ==========================
class CountyPetitionStatus(str, Enum):
    PENDING_GOV_REVIEW = "pending_gov_review"
    GOV_APPROVED_NEW = "gov_approved_new"        # Approved to form new county
    GOV_APPROVED_JOIN = "gov_approved_join"       # Approved to petition existing county
    GOV_REJECTED = "gov_rejected"
    POLL_ACTIVE = "poll_active"                   # County members are voting
    POLL_PASSED = "poll_passed"
    POLL_FAILED = "poll_failed"

class CountyPollType(str, Enum):
    ADD_CITY = "add_city"  # Vote to add a new city to the county

class CountyPollStatus(str, Enum):
    ACTIVE = "active"
    PASSED = "passed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class VoteChoice(str, Enum):
    YES = "yes"
    NO = "no"

class ExchangeOrderType(str, Enum):
    CRYPTO_TO_CASH = "crypto_to_cash"
    CASH_TO_CRYPTO = "cash_to_crypto"
    CRYPTO_TO_CRYPTO = "crypto_to_crypto"


class GovernanceProposalType(str, Enum):
    PROTOCOL_UPGRADE = "protocol_upgrade"       # Change to crypto mechanics (mining rate, peg, etc.)
    FEE_ADJUSTMENT = "fee_adjustment"           # Adjust exchange fees
    MINING_PARAMETER = "mining_parameter"       # Change mining energy/payout parameters
    COUNTY_POLICY = "county_policy"             # General county policy proposal
    TREASURY_SPEND = "treasury_spend"           # Spend from county burned tokens reserve
    MEMBERSHIP_RULE = "membership_rule"         # Change membership rules


class GovernanceProposalStatus(str, Enum):
    ACTIVE = "active"             # Open for voting during voting window
    PENDING = "pending"           # Submitted during proposal window, awaiting voting window
    PASSED = "passed"
    FAILED = "failed"
    EXPIRED = "expired"           # Never entered voting (cycle ended)


class GovernanceCycleStatus(str, Enum):
    PROPOSAL_PHASE = "proposal_phase"   # First 3 days: submit proposals
    VOTING_PHASE = "voting_phase"       # Last 2 days: burn tokens to vote
    COMPLETED = "completed"

# ==========================
# DATABASE MODELS
# ==========================
class County(Base):
    """County entity - a federation of up to 5 cities."""
    __tablename__ = "counties"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    crypto_name = Column(String, unique=True, nullable=False)  # e.g., "WadCoin"
    crypto_symbol = Column(String, unique=True, nullable=False)  # e.g., "WDC"

    # Crypto supply tracking
    total_crypto_minted = Column(Float, default=0.0)
    total_crypto_burned = Column(Float, default=0.0)
    max_supply = Column(Float, default=MAX_TOKEN_SUPPLY)  # 21M cap, governance can increase

    # Mining node energy pool
    mining_energy_pool = Column(Float, default=0.0)  # Deposited city currency value

    # Treasury - holds cash from token purchases, pays out on token sales
    treasury_balance = Column(Float, default=0.0)

    # Permanent SVG pixel art logo (generated once, stored forever)
    logo_svg = Column(Text, nullable=True)

    # Mining payout counter (for halving calculation)
    total_mining_payouts = Column(Integer, default=0)  # Number of payout cycles completed

    created_at = Column(DateTime, default=datetime.utcnow)


class CountyCity(Base):
    """Links a city to a county."""
    __tablename__ = "county_cities"

    id = Column(Integer, primary_key=True, index=True)
    county_id = Column(Integer, index=True, nullable=False)
    city_id = Column(Integer, index=True, nullable=False)
    joined_at = Column(DateTime, default=datetime.utcnow)


class CountyPetition(Base):
    """
    A petition by a city mayor to join/form a county.
    Goes through a 1-day government review, then (if joining existing)
    a 1-day county member vote.
    """
    __tablename__ = "county_petitions"

    id = Column(Integer, primary_key=True, index=True)
    city_id = Column(Integer, index=True, nullable=False)
    mayor_id = Column(Integer, index=True, nullable=False)

    # If joining an existing county, this is set after gov review
    target_county_id = Column(Integer, nullable=True)

    # Proposed county details (for new county formation)
    proposed_county_name = Column(String, nullable=True)
    proposed_crypto_name = Column(String, nullable=True)
    proposed_crypto_symbol = Column(String, nullable=True)

    status = Column(String, default=CountyPetitionStatus.PENDING_GOV_REVIEW)

    # Timing
    created_at = Column(DateTime, default=datetime.utcnow)
    gov_review_ends_at = Column(DateTime, nullable=False)

    # If a poll was created for joining existing county
    poll_id = Column(Integer, nullable=True)


class CountyPoll(Base):
    """Poll for county-level decisions (e.g., adding a new city)."""
    __tablename__ = "county_polls"

    id = Column(Integer, primary_key=True, index=True)
    county_id = Column(Integer, index=True, nullable=False)
    poll_type = Column(String, nullable=False)

    # Target of the poll
    target_city_id = Column(Integer, nullable=True)  # City requesting to join

    # Timing
    created_at = Column(DateTime, default=datetime.utcnow)
    closes_at = Column(DateTime, nullable=False)

    # Status
    status = Column(String, default=CountyPollStatus.ACTIVE)

    # Results
    yes_votes = Column(Integer, default=0)
    no_votes = Column(Integer, default=0)


class CountyVote(Base):
    """Individual vote on a county poll."""
    __tablename__ = "county_votes"

    id = Column(Integer, primary_key=True, index=True)
    poll_id = Column(Integer, index=True, nullable=False)
    voter_id = Column(Integer, index=True, nullable=False)

    vote = Column(String, nullable=False)  # yes, no
    vote_weight = Column(Integer, default=1)  # Mayors get 3 votes

    cast_at = Column(DateTime, default=datetime.utcnow)


class MiningDeposit(Base):
    """Tracks city currency deposited into the county mining node."""
    __tablename__ = "county_mining_deposits"

    id = Column(Integer, primary_key=True, index=True)
    county_id = Column(Integer, index=True, nullable=False)
    player_id = Column(Integer, index=True, nullable=False)
    city_id = Column(Integer, index=True, nullable=False)

    # What was deposited
    currency_type = Column(String, nullable=False)  # The city's currency item type
    quantity_deposited = Column(Float, nullable=False)
    cash_value_at_deposit = Column(Float, nullable=False)  # Snapshot of value

    deposited_at = Column(DateTime, default=datetime.utcnow)
    consumed = Column(Boolean, default=False)  # Has this been used as mining energy


class CryptoWallet(Base):
    """Player's cryptocurrency holdings for each county crypto."""
    __tablename__ = "crypto_wallets"

    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, index=True, nullable=False)
    crypto_symbol = Column(String, index=True, nullable=False)  # Which county's crypto

    balance = Column(Float, default=0.0)
    total_mined = Column(Float, default=0.0)
    total_bought = Column(Float, default=0.0)
    total_sold = Column(Float, default=0.0)

    created_at = Column(DateTime, default=datetime.utcnow)


class CryptoExchangeOrder(Base):
    """Order on the Wadsworth Crypto Exchange."""
    __tablename__ = "crypto_exchange_orders"

    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, index=True, nullable=False)
    order_type = Column(String, nullable=False)  # crypto_to_cash, cash_to_crypto, crypto_to_crypto

    # For selling crypto
    sell_crypto_symbol = Column(String, nullable=True)
    sell_amount = Column(Float, default=0.0)

    # For buying crypto
    buy_crypto_symbol = Column(String, nullable=True)
    buy_amount = Column(Float, default=0.0)

    # For cash legs
    cash_amount = Column(Float, default=0.0)

    # Price per unit of the crypto being traded
    price_per_unit = Column(Float, nullable=False)

    # Status
    status = Column(String, default="open")  # open, filled, cancelled
    filled_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)


class CryptoPriceHistory(Base):
    """Hourly price snapshots for crypto tokens - enables charts and 24h tracking."""
    __tablename__ = "crypto_price_history"

    id = Column(Integer, primary_key=True, index=True)
    crypto_symbol = Column(String, index=True, nullable=False)
    price = Column(Float, nullable=False)
    market_cap = Column(Float, default=0.0)  # price * circulating supply
    circulating_supply = Column(Float, default=0.0)  # minted - burned
    volume_24h = Column(Float, default=0.0)  # Trading volume in cash
    treasury_balance = Column(Float, default=0.0)
    mining_energy = Column(Float, default=0.0)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)


class GovernanceCycle(Base):
    """
    A 5-day governance voting cycle for a county's blockchain.
    Days 1-3: Proposal phase (members submit proposals)
    Days 4-5: Voting phase (members burn tokens to vote YES/NO on proposals)
    """
    __tablename__ = "governance_cycles"

    id = Column(Integer, primary_key=True, index=True)
    county_id = Column(Integer, index=True, nullable=False)
    cycle_number = Column(Integer, nullable=False)  # Sequential cycle number per county

    status = Column(String, default=GovernanceCycleStatus.PROPOSAL_PHASE)

    # Timing (all in ticks)
    started_at_tick = Column(Integer, nullable=False)
    proposal_phase_ends_tick = Column(Integer, nullable=False)  # After 3 days
    voting_phase_ends_tick = Column(Integer, nullable=False)    # After 5 days total

    created_at = Column(DateTime, default=datetime.utcnow)


class GovernanceProposal(Base):
    """
    A proposal submitted during the proposal phase of a governance cycle.
    Any holder of the county's crypto can submit a proposal.
    """
    __tablename__ = "governance_proposals"

    id = Column(Integer, primary_key=True, index=True)
    cycle_id = Column(Integer, index=True, nullable=False)
    county_id = Column(Integer, index=True, nullable=False)
    proposer_id = Column(Integer, index=True, nullable=False)  # Player who submitted

    proposal_type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)

    status = Column(String, default=GovernanceProposalStatus.PENDING)

    # Vote tallies (total tokens burned)
    yes_token_votes = Column(Float, default=0.0)
    no_token_votes = Column(Float, default=0.0)

    created_at = Column(DateTime, default=datetime.utcnow)


class GovernanceVote(Base):
    """
    A vote on a governance proposal. Voters burn tokens to cast votes.
    More tokens burned = more voting weight.
    """
    __tablename__ = "governance_votes"

    id = Column(Integer, primary_key=True, index=True)
    proposal_id = Column(Integer, index=True, nullable=False)
    voter_id = Column(Integer, index=True, nullable=False)
    county_id = Column(Integer, index=True, nullable=False)

    vote = Column(String, nullable=False)  # "yes" or "no"
    tokens_burned = Column(Float, nullable=False)  # Amount of crypto burned for this vote
    crypto_symbol = Column(String, nullable=False)  # Which crypto was burned

    cast_at = Column(DateTime, default=datetime.utcnow)


# ==========================
# HELPER FUNCTIONS
# ==========================
def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        return db
    except Exception as e:
        print(f"[Counties] Database error: {e}")
        db.close()
        raise


def get_county_by_id(county_id: int) -> Optional[County]:
    """Get a county by ID."""
    db = get_db()
    county = db.query(County).filter(County.id == county_id).first()
    db.close()
    return county


def get_county_by_name(name: str) -> Optional[County]:
    """Get a county by name."""
    db = get_db()
    county = db.query(County).filter(County.name == name).first()
    db.close()
    return county


def get_all_counties() -> List[dict]:
    """Get basic info for all counties."""
    db = get_db()
    try:
        counties = db.query(County).all()
        result = []
        for county in counties:
            city_count = db.query(CountyCity).filter(CountyCity.county_id == county.id).count()
            crypto_price = calculate_crypto_price(county.id)
            circ_supply = get_circulating_supply(county)
            holder_count = db.query(CryptoWallet).filter(
                CryptoWallet.crypto_symbol == county.crypto_symbol,
                CryptoWallet.balance > 0
            ).count()
            # Get 24h price change
            price_change_24h = _get_price_change_24h(db, county.crypto_symbol, crypto_price)
            result.append({
                "id": county.id,
                "name": county.name,
                "crypto_name": county.crypto_name,
                "crypto_symbol": county.crypto_symbol,
                "city_count": city_count,
                "max_cities": MAX_COUNTY_CITIES,
                "crypto_price": crypto_price,
                "total_minted": county.total_crypto_minted,
                "total_burned": county.total_crypto_burned,
                "circulating_supply": circ_supply,
                "max_supply": county.max_supply,
                "remaining_supply": get_remaining_supply(county),
                "mining_energy": county.mining_energy_pool,
                "treasury_balance": county.treasury_balance or 0.0,
                "market_cap": crypto_price * circ_supply,
                "fdv": crypto_price * county.max_supply,
                "holder_count": holder_count,
                "logo_svg": county.logo_svg or "",
                "block_reward": calculate_block_reward(county.total_crypto_minted),
                "price_change_24h": price_change_24h,
                "total_mining_payouts": county.total_mining_payouts or 0,
            })
        return result
    except Exception as e:
        print(f"[Counties] Error getting counties: {e}")
        return []
    finally:
        db.close()


def _get_price_change_24h(db, crypto_symbol: str, current_price: float) -> float:
    """Get 24h price change percentage. Returns 0.0 if no history."""
    yesterday = datetime.utcnow() - timedelta(hours=24)
    old_snapshot = db.query(CryptoPriceHistory).filter(
        CryptoPriceHistory.crypto_symbol == crypto_symbol,
        CryptoPriceHistory.timestamp <= yesterday,
    ).order_by(CryptoPriceHistory.timestamp.desc()).first()
    if old_snapshot and old_snapshot.price > 0:
        return ((current_price - old_snapshot.price) / old_snapshot.price) * 100.0
    return 0.0


def get_24h_volume(crypto_symbol: str) -> float:
    """Get 24h trading volume for a crypto symbol."""
    db = get_db()
    try:
        yesterday = datetime.utcnow() - timedelta(hours=24)
        orders = db.query(CryptoExchangeOrder).filter(
            CryptoExchangeOrder.status == "filled",
            CryptoExchangeOrder.filled_at >= yesterday,
        ).all()
        volume = 0.0
        for order in orders:
            if order.sell_crypto_symbol == crypto_symbol or order.buy_crypto_symbol == crypto_symbol:
                volume += order.cash_amount if order.cash_amount else (order.sell_amount * order.price_per_unit)
        return volume
    except Exception as e:
        return 0.0
    finally:
        db.close()


def get_24h_high_low(crypto_symbol: str) -> tuple:
    """Get 24h high and low prices. Returns (high, low)."""
    db = get_db()
    try:
        yesterday = datetime.utcnow() - timedelta(hours=24)
        snapshots = db.query(CryptoPriceHistory).filter(
            CryptoPriceHistory.crypto_symbol == crypto_symbol,
            CryptoPriceHistory.timestamp >= yesterday,
        ).all()
        if not snapshots:
            return (0.0, 0.0)
        prices = [s.price for s in snapshots]
        return (max(prices), min(prices))
    except Exception as e:
        return (0.0, 0.0)
    finally:
        db.close()


def get_county_cities(county_id: int) -> List[CountyCity]:
    """Get all cities in a county."""
    db = get_db()
    cities = db.query(CountyCity).filter(CountyCity.county_id == county_id).all()
    db.close()
    return cities


def get_city_county(city_id: int) -> Optional[County]:
    """Get the county a city belongs to (if any)."""
    db = get_db()
    link = db.query(CountyCity).filter(CountyCity.city_id == city_id).first()
    if not link:
        db.close()
        return None
    county = db.query(County).filter(County.id == link.county_id).first()
    db.close()
    return county


def get_player_county(player_id: int) -> Optional[County]:
    """Get the county a player belongs to through their city membership."""
    from cities import CityMember
    db = get_db()
    membership = db.query(CityMember).filter(CityMember.player_id == player_id).first()
    if not membership:
        db.close()
        return None
    link = db.query(CountyCity).filter(CountyCity.city_id == membership.city_id).first()
    if not link:
        db.close()
        return None
    county = db.query(County).filter(County.id == link.county_id).first()
    db.close()
    return county


def is_player_mayor_in_county(player_id: int, county_id: int) -> bool:
    """Check if a player is a mayor of any city in the county."""
    from cities import City
    db = get_db()
    county_city_links = db.query(CountyCity).filter(CountyCity.county_id == county_id).all()
    for link in county_city_links:
        city = db.query(City).filter(City.id == link.city_id).first()
        if city and city.mayor_id == player_id:
            db.close()
            return True
    db.close()
    return False


def is_player_in_county(player_id: int, county_id: int) -> bool:
    """Check if a player is a member of any city in the county."""
    from cities import CityMember
    db = get_db()
    county_city_links = db.query(CountyCity).filter(CountyCity.county_id == county_id).all()
    city_ids = [link.city_id for link in county_city_links]
    if not city_ids:
        db.close()
        return False
    member = db.query(CityMember).filter(
        CityMember.player_id == player_id,
        CityMember.city_id.in_(city_ids)
    ).first()
    db.close()
    return member is not None


# ==========================
# SVG PIXEL ART LOGO GENERATION
# ==========================
def generate_token_logo_svg(symbol: str) -> str:
    """
    Generate a permanent random SVG pixel art logo for a token.
    Uses the symbol as a seed for deterministic but random-looking art.
    Creates an 8x8 pixel grid with horizontal symmetry (like identicons).
    """
    seed = hashlib.sha256(symbol.encode()).hexdigest()
    rng = random.Random(seed)

    # Generate a random color palette (2-4 colors)
    def rand_color():
        h = rng.randint(0, 360)
        s = rng.randint(50, 100)
        l = rng.randint(35, 65)
        return f"hsl({h}, {s}%, {l}%)"

    bg_color = f"hsl({rng.randint(0, 360)}, {rng.randint(10, 30)}%, {rng.randint(10, 20)}%)"
    colors = [rand_color() for _ in range(rng.randint(2, 4))]

    pixels = []
    grid_size = 8
    # Generate left half, mirror to right for symmetry
    for y in range(grid_size):
        for x in range(grid_size // 2):
            if rng.random() > 0.45:
                color = rng.choice(colors)
                # Left pixel
                pixels.append((x, y, color))
                # Mirror pixel
                pixels.append((grid_size - 1 - x, y, color))

    pixel_size = 4
    svg_size = grid_size * pixel_size
    rects = ""
    for px, py, color in pixels:
        rects += f'<rect x="{px * pixel_size}" y="{py * pixel_size}" width="{pixel_size}" height="{pixel_size}" fill="{color}"/>'

    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_size} {svg_size}" width="32" height="32"><rect width="{svg_size}" height="{svg_size}" fill="{bg_color}"/>{rects}</svg>'


# ==========================
# HALVING CALCULATION
# ==========================
def calculate_block_reward(total_minted: float) -> float:
    """
    Calculate the current mining block reward based on total tokens minted.
    Halvings occur every HALVING_INTERVAL tokens minted (like Bitcoin).
    """
    halvings = int(total_minted / HALVING_INTERVAL)
    reward = INITIAL_BLOCK_REWARD / (2 ** halvings)
    return max(reward, MIN_BLOCK_REWARD)


def get_circulating_supply(county: County) -> float:
    """Get the circulating supply (minted minus burned)."""
    return max(county.total_crypto_minted - county.total_crypto_burned, 0.0)


def get_remaining_supply(county: County) -> float:
    """Get how many tokens can still be minted before hitting max supply."""
    return max(county.max_supply - county.total_crypto_minted, 0.0)


# ==========================
# CRYPTO PRICE CALCULATION
# ==========================
def calculate_crypto_price(county_id: int) -> float:
    """
    Calculate the price of a county's cryptocurrency.
    Price = total cash value of every city member in the county / 1,000,000,000
    Rounded down to 4 decimal places for precision.
    """
    from cities import CityMember, get_player_total_value
    db = get_db()
    try:
        county_city_links = db.query(CountyCity).filter(CountyCity.county_id == county_id).all()
        city_ids = [link.city_id for link in county_city_links]
        if not city_ids:
            return 0.0

        members = db.query(CityMember).filter(CityMember.city_id.in_(city_ids)).all()
        total_cash_value = 0.0
        for member in members:
            total_cash_value += get_player_total_value(member.player_id)

        raw_price = total_cash_value / CRYPTO_PEG_DIVISOR
        # Round down to 4 decimal places for precision
        price = math.floor(raw_price * 10000) / 10000.0
        return max(price, 0.0001)  # Minimum price of $0.0001
    except Exception as e:
        print(f"[Counties] Error calculating crypto price: {e}")
        return 0.0001
    finally:
        db.close()


# ==========================
# COUNTY FORMATION / JOINING
# ==========================
def petition_join_form_county(
    mayor_id: int,
    city_id: int,
    proposed_name: Optional[str] = None,
    proposed_crypto_name: Optional[str] = None,
    proposed_crypto_symbol: Optional[str] = None,
    target_county_id: Optional[int] = None
) -> Tuple[Optional[CountyPetition], str]:
    """
    A city mayor petitions the government to join or form a county.
    After a 1-day gov review, the city will either:
    - Start a new county (if no target_county_id)
    - Be allowed to petition an existing county (if target_county_id)
    """
    from cities import City, CityMember

    db = get_db()
    try:
        # Validate mayor
        city = db.query(City).filter(City.id == city_id).first()
        if not city:
            return None, "City not found"
        if city.mayor_id != mayor_id:
            return None, "Only the city mayor can petition for county membership"

        # Check city isn't already in a county
        existing = db.query(CountyCity).filter(CountyCity.city_id == city_id).first()
        if existing:
            return None, "Your city is already in a county"

        # Check for existing pending petition
        pending = db.query(CountyPetition).filter(
            CountyPetition.city_id == city_id,
            CountyPetition.status.in_([
                CountyPetitionStatus.PENDING_GOV_REVIEW,
                CountyPetitionStatus.GOV_APPROVED_JOIN,
                CountyPetitionStatus.GOV_APPROVED_NEW,
                CountyPetitionStatus.POLL_ACTIVE,
            ])
        ).first()
        if pending:
            return None, "Your city already has an active petition"

        # Validate for new county
        if target_county_id is None:
            if not proposed_name or not proposed_crypto_name or not proposed_crypto_symbol:
                return None, "New county requires a name, crypto name, and crypto symbol"
            # Check name uniqueness
            if db.query(County).filter(County.name == proposed_name).first():
                return None, "A county with this name already exists"
            if db.query(County).filter(County.crypto_symbol == proposed_crypto_symbol).first():
                return None, "A county with this crypto symbol already exists"
        else:
            # Validate target county exists and has room
            target = db.query(County).filter(County.id == target_county_id).first()
            if not target:
                return None, "Target county not found"
            city_count = db.query(CountyCity).filter(CountyCity.county_id == target_county_id).count()
            if city_count >= MAX_COUNTY_CITIES:
                return None, f"Target county is full ({MAX_COUNTY_CITIES} cities max)"

        # Create petition
        review_ends = datetime.utcnow() + timedelta(seconds=GOV_REVIEW_DURATION_TICKS * 5)
        petition = CountyPetition(
            city_id=city_id,
            mayor_id=mayor_id,
            target_county_id=target_county_id,
            proposed_county_name=proposed_name,
            proposed_crypto_name=proposed_crypto_name,
            proposed_crypto_symbol=proposed_crypto_symbol,
            gov_review_ends_at=review_ends,
            status=CountyPetitionStatus.PENDING_GOV_REVIEW,
        )
        db.add(petition)
        db.commit()

        action = "form a new county" if target_county_id is None else "join an existing county"
        print(f"[Counties] Petition filed: City {city_id} (Mayor {mayor_id}) to {action}")
        return petition, f"Petition submitted. Government review ends at {review_ends.strftime('%Y-%m-%d %H:%M UTC')}"

    except Exception as e:
        db.rollback()
        print(f"[Counties] Error filing petition: {e}")
        return None, str(e)
    finally:
        db.close()


def process_gov_review(petition_id: int) -> Tuple[bool, str]:
    """
    Process a government review of a county petition.
    Called automatically when the review period expires.

    - If forming new county: auto-approve and create the county.
    - If joining existing county: approve and start a county-wide vote.
    """
    from cities import City

    db = get_db()
    try:
        petition = db.query(CountyPetition).filter(CountyPetition.id == petition_id).first()
        if not petition:
            return False, "Petition not found"

        if petition.status != CountyPetitionStatus.PENDING_GOV_REVIEW:
            return False, "Petition is not pending review"

        if petition.target_county_id is None:
            # === FORMING NEW COUNTY ===
            logo = generate_token_logo_svg(petition.proposed_crypto_symbol)
            county = County(
                name=petition.proposed_county_name,
                crypto_name=petition.proposed_crypto_name,
                crypto_symbol=petition.proposed_crypto_symbol,
                logo_svg=logo,
            )
            db.add(county)
            db.flush()

            # Add the founding city
            link = CountyCity(
                county_id=county.id,
                city_id=petition.city_id,
            )
            db.add(link)

            petition.status = CountyPetitionStatus.GOV_APPROVED_NEW
            db.commit()

            print(f"[Counties] New county '{county.name}' created (ID: {county.id}) by City {petition.city_id}")
            return True, f"County '{county.name}' formed successfully!"

        else:
            # === JOINING EXISTING COUNTY ===
            # Check target county still has room
            target = db.query(County).filter(County.id == petition.target_county_id).first()
            if not target:
                petition.status = CountyPetitionStatus.GOV_REJECTED
                db.commit()
                return False, "Target county no longer exists"

            city_count = db.query(CountyCity).filter(
                CountyCity.county_id == petition.target_county_id
            ).count()
            if city_count >= MAX_COUNTY_CITIES:
                petition.status = CountyPetitionStatus.GOV_REJECTED
                db.commit()
                return False, "Target county is now full"

            # Create a poll for county members to vote
            closes_at = datetime.utcnow() + timedelta(seconds=COUNTY_PETITION_POLL_DURATION_TICKS * 5)
            poll = CountyPoll(
                county_id=petition.target_county_id,
                poll_type=CountyPollType.ADD_CITY,
                target_city_id=petition.city_id,
                closes_at=closes_at,
            )
            db.add(poll)
            db.flush()

            petition.status = CountyPetitionStatus.POLL_ACTIVE
            petition.poll_id = poll.id
            db.commit()

            city = db.query(City).filter(City.id == petition.city_id).first()
            city_name = city.name if city else f"City {petition.city_id}"
            print(f"[Counties] Poll started: Should county '{target.name}' admit city '{city_name}'?")
            return True, "Government approved. County members are now voting."

    except Exception as e:
        db.rollback()
        print(f"[Counties] Error processing gov review: {e}")
        import traceback
        traceback.print_exc()
        return False, str(e)
    finally:
        db.close()


# ==========================
# COUNTY VOTING SYSTEM
# ==========================
def cast_county_vote(voter_id: int, poll_id: int, vote: VoteChoice) -> Tuple[bool, str]:
    """
    Cast a vote on a county poll.
    All city members in the county can vote.
    Mayors get 3 votes. Abstaining votes follow mayor's vote.
    """
    from cities import City, CityMember

    db = get_db()
    try:
        poll = db.query(CountyPoll).filter(CountyPoll.id == poll_id).first()
        if not poll:
            return False, "Poll not found"
        if poll.status != CountyPollStatus.ACTIVE:
            return False, "Poll is no longer active"
        if datetime.utcnow() > poll.closes_at:
            return False, "Poll has closed"

        # Verify voter is in a city that's part of this county
        if not is_player_in_county(voter_id, poll.county_id):
            return False, "You are not a member of this county"

        # Check for existing vote
        existing = db.query(CountyVote).filter(
            CountyVote.poll_id == poll_id,
            CountyVote.voter_id == voter_id
        ).first()
        if existing:
            return False, "You have already voted on this poll"

        # Determine vote weight (mayors get 3 votes)
        vote_weight = 1
        if is_player_mayor_in_county(voter_id, poll.county_id):
            vote_weight = MAYOR_VOTE_WEIGHT

        county_vote = CountyVote(
            poll_id=poll_id,
            voter_id=voter_id,
            vote=vote.value,
            vote_weight=vote_weight,
        )
        db.add(county_vote)
        db.commit()

        print(f"[Counties] Vote cast: Player {voter_id} voted {vote.value} on poll {poll_id} (weight: {vote_weight})")
        return True, f"Vote recorded ({vote_weight}x weight)"

    except Exception as e:
        db.rollback()
        print(f"[Counties] Error casting vote: {e}")
        return False, str(e)
    finally:
        db.close()


def close_county_poll(poll_id: int) -> Tuple[bool, str]:
    """
    Close a county poll and process results.
    Abstaining members' votes follow their respective city mayor's vote.
    """
    from cities import City, CityMember

    db = get_db()
    try:
        poll = db.query(CountyPoll).filter(CountyPoll.id == poll_id).first()
        if not poll:
            return False, "Poll not found"
        if poll.status != CountyPollStatus.ACTIVE:
            return False, "Poll is not active"

        # Get all votes
        votes = db.query(CountyVote).filter(CountyVote.poll_id == poll_id).all()
        voted_player_ids = {v.voter_id for v in votes}

        # Get all county members and their mayors
        county_city_links = db.query(CountyCity).filter(
            CountyCity.county_id == poll.county_id
        ).all()
        city_ids = [link.city_id for link in county_city_links]

        # Calculate explicit votes
        yes_votes = sum(v.vote_weight for v in votes if v.vote == VoteChoice.YES)
        no_votes = sum(v.vote_weight for v in votes if v.vote == VoteChoice.NO)

        # Process abstaining votes - they follow their mayor
        for city_id in city_ids:
            city = db.query(City).filter(City.id == city_id).first()
            if not city:
                continue

            # Find mayor's vote
            mayor_vote = None
            for v in votes:
                if v.voter_id == city.mayor_id:
                    mayor_vote = v.vote
                    break

            if mayor_vote is None:
                # Mayor didn't vote, abstainers default to YES (in favor of growth)
                mayor_vote = VoteChoice.YES

            # Find city members who didn't vote
            city_members = db.query(CityMember).filter(
                CityMember.city_id == city_id
            ).all()
            for member in city_members:
                if member.player_id not in voted_player_ids:
                    # Abstaining - follows mayor
                    if mayor_vote == VoteChoice.YES:
                        yes_votes += 1
                    else:
                        no_votes += 1

        poll.yes_votes = yes_votes
        poll.no_votes = no_votes

        # Determine outcome (simple majority)
        passed = yes_votes > no_votes
        poll.status = CountyPollStatus.PASSED if passed else CountyPollStatus.FAILED
        db.commit()
        db.close()

        # Process result
        if passed and poll.poll_type == CountyPollType.ADD_CITY:
            _add_city_to_county(poll.county_id, poll.target_city_id, poll_id)

        # Update petition status
        db2 = get_db()
        petition = db2.query(CountyPetition).filter(
            CountyPetition.poll_id == poll_id
        ).first()
        if petition:
            petition.status = CountyPetitionStatus.POLL_PASSED if passed else CountyPetitionStatus.POLL_FAILED
            db2.commit()
        db2.close()

        print(f"[Counties] Poll {poll_id} closed: {'PASSED' if passed else 'FAILED'} (YES: {yes_votes}, NO: {no_votes})")
        return True, f"Poll closed: {'Passed' if passed else 'Failed'}"

    except Exception as e:
        print(f"[Counties] Error closing poll: {e}")
        import traceback
        traceback.print_exc()
        return False, str(e)


def _add_city_to_county(county_id: int, city_id: int, poll_id: int):
    """Internal: Add a city to a county after poll passes."""
    db = get_db()
    try:
        # Verify county has room
        city_count = db.query(CountyCity).filter(CountyCity.county_id == county_id).count()
        if city_count >= MAX_COUNTY_CITIES:
            print(f"[Counties] Cannot add city {city_id} - county {county_id} is full")
            return

        # Verify city isn't already in a county
        existing = db.query(CountyCity).filter(CountyCity.city_id == city_id).first()
        if existing:
            print(f"[Counties] City {city_id} is already in county {existing.county_id}")
            return

        link = CountyCity(
            county_id=county_id,
            city_id=city_id,
        )
        db.add(link)
        db.commit()
        print(f"[Counties] City {city_id} added to county {county_id}")
    except Exception as e:
        db.rollback()
        print(f"[Counties] Error adding city to county: {e}")
    finally:
        db.close()


# ==========================
# MINING NODE
# ==========================
def deposit_to_mining_node(player_id: int, county_id: int, quantity: float) -> Tuple[bool, str]:
    """
    City member deposits their city's currency into the county mining node.
    The deposited currency is consumed as mining energy.
    """
    from cities import CityMember, City, get_player_city
    import inventory
    import market

    db = get_db()
    try:
        # Verify player is in a city that's part of this county
        if not is_player_in_county(player_id, county_id):
            return False, "You are not a member of this county"

        if quantity < MIN_MINING_DEPOSIT:
            return False, f"Minimum deposit is {MIN_MINING_DEPOSIT}"

        # Get player's city and its currency
        membership = db.query(CityMember).filter(CityMember.player_id == player_id).first()
        if not membership:
            return False, "City membership not found"

        city = db.query(City).filter(City.id == membership.city_id).first()
        if not city or not city.currency_type:
            return False, "Your city has no currency set"

        # Check player has enough currency
        player_qty = inventory.get_item_quantity(player_id, city.currency_type)
        if player_qty < quantity:
            return False, f"Insufficient {city.currency_type} (have {player_qty:.2f})"

        # Get market value of deposit
        market_price = market.get_market_price(city.currency_type) or 1.0
        cash_value = quantity * market_price

        # Remove currency from player
        inventory.remove_item(player_id, city.currency_type, quantity)

        # Record deposit
        deposit = MiningDeposit(
            county_id=county_id,
            player_id=player_id,
            city_id=membership.city_id,
            currency_type=city.currency_type,
            quantity_deposited=quantity,
            cash_value_at_deposit=cash_value,
        )
        db.add(deposit)

        # Add to mining energy pool
        county = db.query(County).filter(County.id == county_id).first()
        if county:
            county.mining_energy_pool += cash_value

        db.commit()

        log_transaction(
            player_id,
            "county_mining_deposit",
            "resource",
            -cash_value,
            f"Mining deposit: {quantity:.2f} {city.currency_type}",
            reference_id=f"county_{county_id}_mine",
            item_type=city.currency_type,
            quantity=quantity,
        )

        print(f"[Counties] Mining deposit: Player {player_id} deposited {quantity:.2f} {city.currency_type} (${cash_value:,.2f})")
        return True, f"Deposited {quantity:.2f} {city.currency_type} (${cash_value:,.2f} energy value)"

    except Exception as e:
        db.rollback()
        print(f"[Counties] Error depositing to mining node: {e}")
        return False, str(e)
    finally:
        db.close()


def process_mining_payouts(current_tick: int):
    """
    Process mining payouts for all counties.
    Consumes energy from the mining pool and mints crypto to depositors.
    Called every MINING_PAYOUT_INTERVAL_TICKS.

    Mining rewards use Bitcoin-like halving:
    - Initial block reward: 50 tokens per payout cycle
    - Halves every 210,000 tokens minted
    - Hard cap at max_supply (21M default)
    - Energy is REQUIRED - no energy, no mining
    """
    db = get_db()
    try:
        counties = db.query(County).filter(County.mining_energy_pool > 0).all()

        for county in counties:
            energy_to_consume = county.mining_energy_pool * MINING_ENERGY_CONSUMPTION_RATE
            if energy_to_consume <= 0:
                continue

            # Check supply cap - no mining if max supply reached
            remaining = get_remaining_supply(county)
            if remaining <= 0:
                print(f"[Counties] Mining halted: {county.crypto_symbol} max supply ({county.max_supply:,.0f}) reached")
                continue

            # Calculate block reward with halving
            block_reward = calculate_block_reward(county.total_crypto_minted)
            crypto_to_mint = min(block_reward, remaining)  # Don't exceed max supply

            if crypto_to_mint <= 0:
                continue

            # Get all unconsumed deposits for this county, ordered by deposit time
            deposits = db.query(MiningDeposit).filter(
                MiningDeposit.county_id == county.id,
                MiningDeposit.consumed == False
            ).order_by(MiningDeposit.deposited_at.asc()).all()

            if not deposits:
                continue

            # Distribute rewards proportionally by deposit value
            total_deposit_value = sum(d.cash_value_at_deposit for d in deposits)
            if total_deposit_value <= 0:
                continue

            for deposit in deposits:
                share = deposit.cash_value_at_deposit / total_deposit_value
                reward = crypto_to_mint * share

                if reward > 0:
                    # Credit crypto to player's wallet
                    wallet = db.query(CryptoWallet).filter(
                        CryptoWallet.player_id == deposit.player_id,
                        CryptoWallet.crypto_symbol == county.crypto_symbol,
                    ).first()

                    if not wallet:
                        wallet = CryptoWallet(
                            player_id=deposit.player_id,
                            crypto_symbol=county.crypto_symbol,
                        )
                        db.add(wallet)
                        db.flush()

                    wallet.balance += reward
                    wallet.total_mined += reward

                # Mark as consumed (energy used up)
                deposit.consumed = True

            # Update county totals
            county.total_crypto_minted += crypto_to_mint
            county.mining_energy_pool -= energy_to_consume
            county.total_mining_payouts = (county.total_mining_payouts or 0) + 1

            halvings = int(county.total_crypto_minted / HALVING_INTERVAL)
            print(f"[Counties] Mining payout: County '{county.name}' minted {crypto_to_mint:.6f} {county.crypto_symbol} (reward: {block_reward:.4f}, halvings: {halvings}, supply: {county.total_crypto_minted:,.2f}/{county.max_supply:,.0f})")

        db.commit()

    except Exception as e:
        db.rollback()
        print(f"[Counties] Error processing mining payouts: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


# ==========================
# WADSWORTH CRYPTO EXCHANGE
# ==========================
def get_crypto_price_by_symbol(symbol: str) -> float:
    """Get current price of a crypto by its symbol."""
    db = get_db()
    try:
        county = db.query(County).filter(County.crypto_symbol == symbol).first()
        if not county:
            return 0.0
        return calculate_crypto_price(county.id)
    finally:
        db.close()


def get_player_wallets(player_id: int) -> List[dict]:
    """Get all crypto wallets for a player."""
    db = get_db()
    try:
        wallets = db.query(CryptoWallet).filter(CryptoWallet.player_id == player_id).all()
        result = []
        for w in wallets:
            price = get_crypto_price_by_symbol(w.crypto_symbol)
            result.append({
                "symbol": w.crypto_symbol,
                "balance": w.balance,
                "total_mined": w.total_mined,
                "total_bought": w.total_bought,
                "total_sold": w.total_sold,
                "price": price,
                "value": w.balance * price,
            })
        return result
    except Exception as e:
        print(f"[Counties] Error getting wallets: {e}")
        return []
    finally:
        db.close()


def sell_crypto_for_cash(player_id: int, crypto_symbol: str, amount: float) -> Tuple[bool, str]:
    """
    Sell crypto for cash at the pegged price. 2% exchange fee.
    Cash is paid out from the county treasury. If treasury has insufficient
    funds, the sale is limited to what the treasury can cover.
    The sold tokens are burned (reducing circulating supply).
    Requires the county's mining node to have energy (blockchain must be powered).
    """
    from auth import Player

    db = get_db()
    try:
        # Verify the blockchain has energy to function
        county = db.query(County).filter(County.crypto_symbol == crypto_symbol).first()
        if not county:
            return False, "Token not found"
        if (county.mining_energy_pool or 0) <= 0:
            return False, f"The {county.name} blockchain has no energy. Mining nodes must be powered before any transactions can occur."

        wallet = db.query(CryptoWallet).filter(
            CryptoWallet.player_id == player_id,
            CryptoWallet.crypto_symbol == crypto_symbol,
        ).first()
        if not wallet or wallet.balance < amount:
            return False, "Insufficient crypto balance"

        price = get_crypto_price_by_symbol(crypto_symbol)
        if price <= 0:
            return False, "Crypto has no value"

        gross_value = amount * price
        fee = gross_value * EXCHANGE_FEE_PERCENT
        net_value = gross_value - fee

        # Check treasury can cover the payout
        treasury = county.treasury_balance or 0.0
        if treasury < net_value:
            return False, f"County treasury has insufficient funds (${treasury:,.4f} available, ${net_value:,.4f} needed). More buyers needed to fund the treasury."

        player = db.query(Player).filter(Player.id == player_id).first()
        if not player:
            return False, "Player not found"

        # Execute sale
        wallet.balance -= amount
        wallet.total_sold += amount
        player.cash_balance += net_value

        # Cash comes FROM the county treasury
        county.treasury_balance -= (net_value + fee)

        # Burn the sold crypto (reducing circulating supply)
        county.total_crypto_burned += amount

        # Fee distribution
        gov = db.query(Player).filter(Player.id == GOVERNMENT_PLAYER_ID).first()
        if gov:
            gov_fee = fee * EXCHANGE_FEE_TO_GOV_PERCENT
            gov.cash_balance += gov_fee

        # Record the order
        order = CryptoExchangeOrder(
            player_id=player_id,
            order_type=ExchangeOrderType.CRYPTO_TO_CASH,
            sell_crypto_symbol=crypto_symbol,
            sell_amount=amount,
            cash_amount=net_value,
            price_per_unit=price,
            status="filled",
            filled_at=datetime.utcnow(),
        )
        db.add(order)

        db.commit()

        log_transaction(
            player_id,
            "crypto_sell",
            "money",
            net_value,
            f"Sold {amount:.6f} {crypto_symbol} @ ${price:,.4f}",
            reference_id=f"exchange_sell_{crypto_symbol}",
        )

        print(f"[Counties] Crypto sale: Player {player_id} sold {amount:.6f} {crypto_symbol} for ${net_value:,.4f}")
        return True, f"Sold {amount:.6f} {crypto_symbol} for ${net_value:,.4f} (fee: ${fee:,.4f})"

    except Exception as e:
        db.rollback()
        print(f"[Counties] Error selling crypto: {e}")
        return False, str(e)
    finally:
        db.close()


def buy_crypto_with_cash(player_id: int, crypto_symbol: str, cash_amount: float) -> Tuple[bool, str]:
    """
    Buy crypto with cash at the pegged price. 2% exchange fee.
    Cash goes INTO the county treasury. Tokens are drawn from circulating supply
    (not minted - buying doesn't create new tokens, only mining does).
    Requires the county's mining node to have energy (blockchain must be powered).
    """
    from auth import Player

    db = get_db()
    try:
        # Verify the blockchain has energy to function
        county = db.query(County).filter(County.crypto_symbol == crypto_symbol).first()
        if not county:
            return False, "Token not found"
        if (county.mining_energy_pool or 0) <= 0:
            return False, f"The {county.name} blockchain has no energy. Mining nodes must be powered before any transactions can occur."

        player = db.query(Player).filter(Player.id == player_id).first()
        if not player:
            return False, "Player not found"
        if player.cash_balance < cash_amount:
            return False, "Insufficient cash"

        price = get_crypto_price_by_symbol(crypto_symbol)
        if price <= 0:
            return False, "Crypto has no value"

        fee = cash_amount * EXCHANGE_FEE_PERCENT
        net_cash = cash_amount - fee
        crypto_amount = net_cash / price

        # Deduct cash from player
        player.cash_balance -= cash_amount

        # Cash goes INTO the county treasury
        county.treasury_balance = (county.treasury_balance or 0.0) + net_cash

        # Credit crypto to player wallet (tokens are exchanged, not newly minted)
        wallet = db.query(CryptoWallet).filter(
            CryptoWallet.player_id == player_id,
            CryptoWallet.crypto_symbol == crypto_symbol,
        ).first()
        if not wallet:
            wallet = CryptoWallet(
                player_id=player_id,
                crypto_symbol=crypto_symbol,
            )
            db.add(wallet)
            db.flush()

        wallet.balance += crypto_amount
        wallet.total_bought += crypto_amount

        # Buying on exchange mints tokens (increases supply, but capped)
        remaining = get_remaining_supply(county)
        if crypto_amount > remaining:
            return False, f"Not enough supply remaining. Only {remaining:,.6f} {crypto_symbol} left to mint (max supply: {county.max_supply:,.0f})"
        county.total_crypto_minted += crypto_amount

        # Fee distribution
        gov = db.query(Player).filter(Player.id == GOVERNMENT_PLAYER_ID).first()
        if gov:
            gov_fee = fee * EXCHANGE_FEE_TO_GOV_PERCENT
            gov.cash_balance += gov_fee

        # Record the order
        order = CryptoExchangeOrder(
            player_id=player_id,
            order_type=ExchangeOrderType.CASH_TO_CRYPTO,
            buy_crypto_symbol=crypto_symbol,
            buy_amount=crypto_amount,
            cash_amount=cash_amount,
            price_per_unit=price,
            status="filled",
            filled_at=datetime.utcnow(),
        )
        db.add(order)

        db.commit()

        log_transaction(
            player_id,
            "crypto_buy",
            "money",
            -cash_amount,
            f"Bought {crypto_amount:.6f} {crypto_symbol} @ ${price:,.4f}",
            reference_id=f"exchange_buy_{crypto_symbol}",
        )

        print(f"[Counties] Crypto buy: Player {player_id} bought {crypto_amount:.6f} {crypto_symbol} for ${cash_amount:,.4f}")
        return True, f"Bought {crypto_amount:.6f} {crypto_symbol} for ${cash_amount:,.4f} (fee: ${fee:,.4f})"

    except Exception as e:
        db.rollback()
        print(f"[Counties] Error buying crypto: {e}")
        return False, str(e)
    finally:
        db.close()


def swap_crypto(player_id: int, sell_symbol: str, buy_symbol: str, sell_amount: float) -> Tuple[bool, str]:
    """
    Swap one crypto for another through the exchange.
    Converts sell crypto → cash → buy crypto. 2% fee.
    Both blockchains must have energy to function.
    """
    from auth import Player

    db = get_db()
    try:
        # Verify both blockchains have energy
        sell_county = db.query(County).filter(County.crypto_symbol == sell_symbol).first()
        buy_county = db.query(County).filter(County.crypto_symbol == buy_symbol).first()
        if not sell_county or not buy_county:
            return False, "One or both tokens not found"
        if (sell_county.mining_energy_pool or 0) <= 0:
            return False, f"The {sell_county.name} blockchain has no energy. Mining nodes must be powered."
        if (buy_county.mining_energy_pool or 0) <= 0:
            return False, f"The {buy_county.name} blockchain has no energy. Mining nodes must be powered."

        # Validate sell side
        sell_wallet = db.query(CryptoWallet).filter(
            CryptoWallet.player_id == player_id,
            CryptoWallet.crypto_symbol == sell_symbol,
        ).first()
        if not sell_wallet or sell_wallet.balance < sell_amount:
            return False, f"Insufficient {sell_symbol} balance"

        sell_price = get_crypto_price_by_symbol(sell_symbol)
        buy_price = get_crypto_price_by_symbol(buy_symbol)
        if sell_price <= 0 or buy_price <= 0:
            return False, "One or both cryptos have no value"

        # Calculate swap
        gross_cash = sell_amount * sell_price
        fee = gross_cash * EXCHANGE_FEE_PERCENT
        net_cash = gross_cash - fee
        buy_amount = net_cash / buy_price

        # Check buy side supply cap
        remaining = get_remaining_supply(buy_county)
        if buy_amount > remaining:
            return False, f"Not enough {buy_symbol} supply remaining ({remaining:,.6f} left)"

        # Execute sell side
        sell_wallet.balance -= sell_amount
        sell_wallet.total_sold += sell_amount
        sell_county.total_crypto_burned += sell_amount
        # Sell side cash goes to sell county treasury
        sell_county.treasury_balance = (sell_county.treasury_balance or 0.0) + net_cash

        # Execute buy side - cash comes from buy county treasury
        buy_wallet = db.query(CryptoWallet).filter(
            CryptoWallet.player_id == player_id,
            CryptoWallet.crypto_symbol == buy_symbol,
        ).first()
        if not buy_wallet:
            buy_wallet = CryptoWallet(
                player_id=player_id,
                crypto_symbol=buy_symbol,
            )
            db.add(buy_wallet)
            db.flush()

        buy_wallet.balance += buy_amount
        buy_wallet.total_bought += buy_amount
        buy_county.total_crypto_minted += buy_amount

        # Fee distribution
        gov = db.query(Player).filter(Player.id == GOVERNMENT_PLAYER_ID).first()
        if gov:
            gov_fee = fee * EXCHANGE_FEE_TO_GOV_PERCENT
            gov.cash_balance += gov_fee

        # Record the order
        order = CryptoExchangeOrder(
            player_id=player_id,
            order_type=ExchangeOrderType.CRYPTO_TO_CRYPTO,
            sell_crypto_symbol=sell_symbol,
            sell_amount=sell_amount,
            buy_crypto_symbol=buy_symbol,
            buy_amount=buy_amount,
            cash_amount=gross_cash,
            price_per_unit=sell_price,
            status="filled",
            filled_at=datetime.utcnow(),
        )
        db.add(order)

        db.commit()

        log_transaction(
            player_id,
            "crypto_swap",
            "money",
            -fee,
            f"Swapped {sell_amount:.6f} {sell_symbol} → {buy_amount:.6f} {buy_symbol}",
            reference_id=f"exchange_swap_{sell_symbol}_{buy_symbol}",
        )

        print(f"[Counties] Crypto swap: Player {player_id} swapped {sell_amount:.6f} {sell_symbol} → {buy_amount:.6f} {buy_symbol}")
        return True, f"Swapped {sell_amount:.6f} {sell_symbol} for {buy_amount:.6f} {buy_symbol} (fee: ${fee:,.4f})"

    except Exception as e:
        db.rollback()
        print(f"[Counties] Error swapping crypto: {e}")
        return False, str(e)
    finally:
        db.close()


# ==========================
# INTERCOUNTY GOVERNANCE VOTING
# ==========================
def get_current_governance_cycle(county_id: int, current_tick: int) -> Optional[dict]:
    """Get the current active governance cycle for a county, or None if none is active."""
    db = get_db()
    try:
        cycle = db.query(GovernanceCycle).filter(
            GovernanceCycle.county_id == county_id,
            GovernanceCycle.voting_phase_ends_tick > current_tick,
        ).order_by(GovernanceCycle.cycle_number.desc()).first()

        if not cycle:
            return None

        # Determine current phase
        if current_tick < cycle.proposal_phase_ends_tick:
            phase = "proposal_phase"
        elif current_tick < cycle.voting_phase_ends_tick:
            phase = "voting_phase"
        else:
            phase = "completed"

        return {
            "id": cycle.id,
            "county_id": cycle.county_id,
            "cycle_number": cycle.cycle_number,
            "status": cycle.status,
            "phase": phase,
            "started_at_tick": cycle.started_at_tick,
            "proposal_phase_ends_tick": cycle.proposal_phase_ends_tick,
            "voting_phase_ends_tick": cycle.voting_phase_ends_tick,
            "created_at": cycle.created_at,
        }
    except Exception as e:
        print(f"[Counties] Error getting governance cycle: {e}")
        return None
    finally:
        db.close()


def start_governance_cycle(county_id: int, current_tick: int) -> Optional[GovernanceCycle]:
    """Start a new 5-day governance cycle for a county."""
    db = get_db()
    try:
        # Check county exists
        county = db.query(County).filter(County.id == county_id).first()
        if not county:
            return None

        # Get next cycle number
        last_cycle = db.query(GovernanceCycle).filter(
            GovernanceCycle.county_id == county_id,
        ).order_by(GovernanceCycle.cycle_number.desc()).first()

        cycle_number = (last_cycle.cycle_number + 1) if last_cycle else 1

        cycle = GovernanceCycle(
            county_id=county_id,
            cycle_number=cycle_number,
            started_at_tick=current_tick,
            proposal_phase_ends_tick=current_tick + GOVERNANCE_PROPOSAL_WINDOW_TICKS,
            voting_phase_ends_tick=current_tick + GOVERNANCE_VOTE_CYCLE_TICKS,
            status=GovernanceCycleStatus.PROPOSAL_PHASE,
        )
        db.add(cycle)
        db.commit()

        print(f"[Counties] Governance cycle #{cycle_number} started for county '{county.name}' (ID: {county_id})")
        return cycle
    except Exception as e:
        db.rollback()
        print(f"[Counties] Error starting governance cycle: {e}")
        return None
    finally:
        db.close()


def submit_governance_proposal(
    player_id: int,
    county_id: int,
    proposal_type: str,
    title: str,
    description: str,
    current_tick: int,
) -> tuple:
    """
    Submit a governance proposal during the proposal phase.
    Any holder of the county's crypto can submit.
    Returns (proposal, message).
    """
    db = get_db()
    try:
        # Validate county
        county = db.query(County).filter(County.id == county_id).first()
        if not county:
            return None, "County not found"

        # Verify player holds this county's crypto
        wallet = db.query(CryptoWallet).filter(
            CryptoWallet.player_id == player_id,
            CryptoWallet.crypto_symbol == county.crypto_symbol,
        ).first()
        if not wallet or wallet.balance <= 0:
            return None, f"You must hold {county.crypto_symbol} to submit proposals"

        # Verify player is a county member (member of a city in this county)
        if not is_player_in_county(player_id, county_id):
            return None, "Only county members can submit governance proposals"

        # Get current active cycle in proposal phase
        cycle = db.query(GovernanceCycle).filter(
            GovernanceCycle.county_id == county_id,
            GovernanceCycle.proposal_phase_ends_tick > current_tick,
            GovernanceCycle.started_at_tick <= current_tick,
        ).first()

        if not cycle:
            return None, "No governance cycle is currently in the proposal phase"

        if cycle.status != GovernanceCycleStatus.PROPOSAL_PHASE:
            return None, "The current cycle is no longer accepting proposals"

        # Validate proposal type
        try:
            GovernanceProposalType(proposal_type)
        except ValueError:
            return None, f"Invalid proposal type: {proposal_type}"

        # Create proposal
        proposal = GovernanceProposal(
            cycle_id=cycle.id,
            county_id=county_id,
            proposer_id=player_id,
            proposal_type=proposal_type,
            title=title,
            description=description,
            status=GovernanceProposalStatus.PENDING,
        )
        db.add(proposal)
        db.commit()

        log_transaction(
            player_id,
            "governance_proposal",
            "governance",
            0,
            f"Submitted governance proposal: {title}",
            reference_id=f"gov_proposal_{county_id}_{proposal.id}",
        )

        print(f"[Counties] Governance proposal submitted: '{title}' by Player {player_id} for county {county_id}")
        return proposal, "Proposal submitted successfully. It will enter voting when the voting phase begins."

    except Exception as e:
        db.rollback()
        print(f"[Counties] Error submitting governance proposal: {e}")
        return None, str(e)
    finally:
        db.close()


def cast_governance_vote(
    player_id: int,
    proposal_id: int,
    vote: str,
    tokens_to_burn: float,
    current_tick: int,
) -> tuple:
    """
    Cast a governance vote by burning tokens.
    Players burn their county crypto to weight their vote.
    Multiple votes on the same proposal are allowed (each burns more tokens).
    Returns (success, message).
    """
    db = get_db()
    try:
        # Get proposal
        proposal = db.query(GovernanceProposal).filter(
            GovernanceProposal.id == proposal_id
        ).first()
        if not proposal:
            return False, "Proposal not found"

        if proposal.status != GovernanceProposalStatus.ACTIVE:
            return False, "This proposal is not currently open for voting"

        # Verify cycle is in voting phase
        cycle = db.query(GovernanceCycle).filter(
            GovernanceCycle.id == proposal.cycle_id,
        ).first()
        if not cycle:
            return False, "Governance cycle not found"

        if current_tick < cycle.proposal_phase_ends_tick:
            return False, "Voting has not started yet (still in proposal phase)"

        if current_tick >= cycle.voting_phase_ends_tick:
            return False, "Voting has ended for this cycle"

        # Validate vote choice
        if vote not in ("yes", "no"):
            return False, "Vote must be 'yes' or 'no'"

        if tokens_to_burn < MIN_GOVERNANCE_BURN:
            return False, f"Minimum token burn is {MIN_GOVERNANCE_BURN}"

        # Get county
        county = db.query(County).filter(County.id == proposal.county_id).first()
        if not county:
            return False, "County not found"

        # Verify player holds enough tokens
        wallet = db.query(CryptoWallet).filter(
            CryptoWallet.player_id == player_id,
            CryptoWallet.crypto_symbol == county.crypto_symbol,
        ).first()
        if not wallet or wallet.balance < tokens_to_burn:
            return False, f"Insufficient {county.crypto_symbol} balance (have {wallet.balance if wallet else 0:.6f}, need {tokens_to_burn:.6f})"

        # Verify player is a county member
        if not is_player_in_county(player_id, proposal.county_id):
            return False, "Only county members can vote on governance proposals"

        # Burn tokens from wallet
        wallet.balance -= tokens_to_burn

        # Update county burn stats
        county.total_crypto_burned += tokens_to_burn

        # Record vote
        gov_vote = GovernanceVote(
            proposal_id=proposal_id,
            voter_id=player_id,
            county_id=proposal.county_id,
            vote=vote,
            tokens_burned=tokens_to_burn,
            crypto_symbol=county.crypto_symbol,
        )
        db.add(gov_vote)

        # Update proposal tallies
        if vote == "yes":
            proposal.yes_token_votes += tokens_to_burn
        else:
            proposal.no_token_votes += tokens_to_burn

        db.commit()

        log_transaction(
            player_id,
            "governance_vote",
            "governance",
            -tokens_to_burn,
            f"Burned {tokens_to_burn:.6f} {county.crypto_symbol} to vote {vote.upper()} on '{proposal.title}'",
            reference_id=f"gov_vote_{proposal_id}",
            item_type=county.crypto_symbol,
            quantity=tokens_to_burn,
        )

        print(f"[Counties] Governance vote: Player {player_id} burned {tokens_to_burn:.6f} {county.crypto_symbol} to vote {vote.upper()} on proposal {proposal_id}")
        return True, f"Vote recorded! Burned {tokens_to_burn:.6f} {county.crypto_symbol} for {vote.upper()}"

    except Exception as e:
        db.rollback()
        print(f"[Counties] Error casting governance vote: {e}")
        return False, str(e)
    finally:
        db.close()


def get_governance_proposals(county_id: int, cycle_id: Optional[int] = None) -> list:
    """Get all governance proposals for a county, optionally filtered by cycle."""
    db = get_db()
    try:
        query = db.query(GovernanceProposal).filter(
            GovernanceProposal.county_id == county_id,
        )
        if cycle_id:
            query = query.filter(GovernanceProposal.cycle_id == cycle_id)

        proposals = query.order_by(GovernanceProposal.created_at.desc()).all()

        from auth import Player
        result = []
        for p in proposals:
            proposer = db.query(Player).filter(Player.id == p.proposer_id).first()
            total_votes = p.yes_token_votes + p.no_token_votes
            result.append({
                "id": p.id,
                "cycle_id": p.cycle_id,
                "county_id": p.county_id,
                "proposer_id": p.proposer_id,
                "proposer_name": proposer.business_name if proposer else f"Player {p.proposer_id}",
                "proposal_type": p.proposal_type,
                "title": p.title,
                "description": p.description,
                "status": p.status,
                "yes_token_votes": p.yes_token_votes,
                "no_token_votes": p.no_token_votes,
                "total_votes": total_votes,
                "yes_percent": (p.yes_token_votes / total_votes * 100) if total_votes > 0 else 0,
                "no_percent": (p.no_token_votes / total_votes * 100) if total_votes > 0 else 0,
                "created_at": p.created_at,
            })
        return result
    except Exception as e:
        print(f"[Counties] Error getting governance proposals: {e}")
        return []
    finally:
        db.close()


def get_player_governance_votes(player_id: int, proposal_id: int) -> list:
    """Get all governance votes a player has cast on a specific proposal."""
    db = get_db()
    try:
        votes = db.query(GovernanceVote).filter(
            GovernanceVote.voter_id == player_id,
            GovernanceVote.proposal_id == proposal_id,
        ).order_by(GovernanceVote.cast_at.desc()).all()

        return [{
            "id": v.id,
            "vote": v.vote,
            "tokens_burned": v.tokens_burned,
            "crypto_symbol": v.crypto_symbol,
            "cast_at": v.cast_at,
        } for v in votes]
    except Exception as e:
        print(f"[Counties] Error getting player governance votes: {e}")
        return []
    finally:
        db.close()


def get_governance_history(county_id: int, limit: int = 10) -> list:
    """Get past governance cycles and their results."""
    db = get_db()
    try:
        cycles = db.query(GovernanceCycle).filter(
            GovernanceCycle.county_id == county_id,
            GovernanceCycle.status == GovernanceCycleStatus.COMPLETED,
        ).order_by(GovernanceCycle.cycle_number.desc()).limit(limit).all()

        result = []
        for cycle in cycles:
            proposals = db.query(GovernanceProposal).filter(
                GovernanceProposal.cycle_id == cycle.id,
            ).all()

            result.append({
                "cycle_number": cycle.cycle_number,
                "started_at_tick": cycle.started_at_tick,
                "total_proposals": len(proposals),
                "passed": sum(1 for p in proposals if p.status == GovernanceProposalStatus.PASSED),
                "failed": sum(1 for p in proposals if p.status == GovernanceProposalStatus.FAILED),
                "created_at": cycle.created_at,
            })
        return result
    except Exception as e:
        print(f"[Counties] Error getting governance history: {e}")
        return []
    finally:
        db.close()


def process_governance_cycles(current_tick: int):
    """
    Process governance cycle transitions:
    1. Start new cycles for counties that don't have an active one
    2. Transition proposal phase → voting phase
    3. Close voting phase and tally results
    """
    db = get_db()
    try:
        counties = db.query(County).all()

        for county in counties:
            # Check for active cycle
            active_cycle = db.query(GovernanceCycle).filter(
                GovernanceCycle.county_id == county.id,
                GovernanceCycle.voting_phase_ends_tick > current_tick,
            ).first()

            if not active_cycle:
                # Check if enough time has passed since last cycle
                last_cycle = db.query(GovernanceCycle).filter(
                    GovernanceCycle.county_id == county.id,
                ).order_by(GovernanceCycle.cycle_number.desc()).first()

                should_start = True
                if last_cycle and (current_tick - last_cycle.voting_phase_ends_tick) < 0:
                    should_start = False

                if should_start:
                    db.close()
                    start_governance_cycle(county.id, current_tick)
                    db = get_db()
                continue

            # Transition from proposal phase to voting phase
            if (active_cycle.status == GovernanceCycleStatus.PROPOSAL_PHASE and
                    current_tick >= active_cycle.proposal_phase_ends_tick):
                active_cycle.status = GovernanceCycleStatus.VOTING_PHASE

                # Activate all pending proposals for voting
                pending_proposals = db.query(GovernanceProposal).filter(
                    GovernanceProposal.cycle_id == active_cycle.id,
                    GovernanceProposal.status == GovernanceProposalStatus.PENDING,
                ).all()

                for proposal in pending_proposals:
                    proposal.status = GovernanceProposalStatus.ACTIVE

                db.commit()
                print(f"[Counties] County '{county.name}' governance cycle #{active_cycle.cycle_number}: Voting phase started ({len(pending_proposals)} proposals)")

            # Close voting phase
            elif (active_cycle.status == GovernanceCycleStatus.VOTING_PHASE and
                  current_tick >= active_cycle.voting_phase_ends_tick):
                active_cycle.status = GovernanceCycleStatus.COMPLETED

                # Tally all active proposals
                active_proposals = db.query(GovernanceProposal).filter(
                    GovernanceProposal.cycle_id == active_cycle.id,
                    GovernanceProposal.status == GovernanceProposalStatus.ACTIVE,
                ).all()

                for proposal in active_proposals:
                    total_votes = proposal.yes_token_votes + proposal.no_token_votes
                    if total_votes > 0 and proposal.yes_token_votes > proposal.no_token_votes:
                        proposal.status = GovernanceProposalStatus.PASSED
                    else:
                        proposal.status = GovernanceProposalStatus.FAILED

                db.commit()

                passed_count = sum(1 for p in active_proposals if p.status == GovernanceProposalStatus.PASSED)
                failed_count = sum(1 for p in active_proposals if p.status == GovernanceProposalStatus.FAILED)
                print(f"[Counties] County '{county.name}' governance cycle #{active_cycle.cycle_number} completed: {passed_count} passed, {failed_count} failed")

    except Exception as e:
        db.rollback()
        print(f"[Counties] Error processing governance cycles: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


# ==========================
# PRICE SNAPSHOT
# ==========================
def take_price_snapshots():
    """Take hourly price snapshots for all county cryptos. Enables 24h tracking and charts."""
    db = get_db()
    try:
        counties = db.query(County).all()
        for county in counties:
            price = calculate_crypto_price(county.id)
            circ_supply = get_circulating_supply(county)
            volume = get_24h_volume(county.crypto_symbol)
            snapshot = CryptoPriceHistory(
                crypto_symbol=county.crypto_symbol,
                price=price,
                market_cap=price * circ_supply,
                circulating_supply=circ_supply,
                volume_24h=volume,
                treasury_balance=county.treasury_balance or 0.0,
                mining_energy=county.mining_energy_pool or 0.0,
            )
            db.add(snapshot)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[Counties] Error taking price snapshots: {e}")
    finally:
        db.close()


def get_price_history(crypto_symbol: str, hours: int = 24) -> list:
    """Get price history snapshots for charting."""
    db = get_db()
    try:
        since = datetime.utcnow() - timedelta(hours=hours)
        snapshots = db.query(CryptoPriceHistory).filter(
            CryptoPriceHistory.crypto_symbol == crypto_symbol,
            CryptoPriceHistory.timestamp >= since,
        ).order_by(CryptoPriceHistory.timestamp.asc()).all()
        return [{
            "price": s.price,
            "market_cap": s.market_cap,
            "circulating_supply": s.circulating_supply,
            "volume_24h": s.volume_24h,
            "treasury_balance": s.treasury_balance,
            "mining_energy": s.mining_energy,
            "timestamp": s.timestamp.isoformat(),
        } for s in snapshots]
    except Exception as e:
        print(f"[Counties] Error getting price history: {e}")
        return []
    finally:
        db.close()


def get_token_holders(crypto_symbol: str) -> list:
    """Get all holders of a token sorted by balance descending."""
    from auth import Player
    db = get_db()
    try:
        wallets = db.query(CryptoWallet).filter(
            CryptoWallet.crypto_symbol == crypto_symbol,
            CryptoWallet.balance > 0
        ).order_by(CryptoWallet.balance.desc()).all()
        result = []
        for w in wallets:
            player = db.query(Player).filter(Player.id == w.player_id).first()
            result.append({
                "player_id": w.player_id,
                "player_name": player.business_name if player else f"Player {w.player_id}",
                "balance": w.balance,
                "total_mined": w.total_mined,
                "total_bought": w.total_bought,
                "total_sold": w.total_sold,
            })
        return result
    except Exception as e:
        print(f"[Counties] Error getting token holders: {e}")
        return []
    finally:
        db.close()


def get_token_info(crypto_symbol: str) -> Optional[dict]:
    """Get comprehensive token information for the info screen."""
    db = get_db()
    try:
        county = db.query(County).filter(County.crypto_symbol == crypto_symbol).first()
        if not county:
            return None

        price = calculate_crypto_price(county.id)
        circ_supply = get_circulating_supply(county)
        remaining = get_remaining_supply(county)
        holder_count = db.query(CryptoWallet).filter(
            CryptoWallet.crypto_symbol == crypto_symbol,
            CryptoWallet.balance > 0
        ).count()
        volume = get_24h_volume(crypto_symbol)
        high_24h, low_24h = get_24h_high_low(crypto_symbol)
        price_change = _get_price_change_24h(db, crypto_symbol, price)
        block_reward = calculate_block_reward(county.total_crypto_minted)
        halvings = int(county.total_crypto_minted / HALVING_INTERVAL)
        next_halving_at = (halvings + 1) * HALVING_INTERVAL
        city_count = db.query(CountyCity).filter(CountyCity.county_id == county.id).count()

        # Top holders (whales)
        top_holders = db.query(CryptoWallet).filter(
            CryptoWallet.crypto_symbol == crypto_symbol,
            CryptoWallet.balance > 0
        ).order_by(CryptoWallet.balance.desc()).limit(10).all()

        from auth import Player
        whale_list = []
        for w in top_holders:
            p = db.query(Player).filter(Player.id == w.player_id).first()
            pct = (w.balance / circ_supply * 100) if circ_supply > 0 else 0
            whale_list.append({
                "player_id": w.player_id,
                "name": p.business_name if p else f"Player {w.player_id}",
                "balance": w.balance,
                "pct_of_supply": pct,
            })

        return {
            "crypto_symbol": county.crypto_symbol,
            "crypto_name": county.crypto_name,
            "county_name": county.name,
            "county_id": county.id,
            "logo_svg": county.logo_svg or "",
            "price": price,
            "price_change_24h": price_change,
            "high_24h": high_24h,
            "low_24h": low_24h,
            "market_cap": price * circ_supply,
            "fdv": price * county.max_supply,
            "volume_24h": volume,
            "circulating_supply": circ_supply,
            "total_minted": county.total_crypto_minted,
            "total_burned": county.total_crypto_burned,
            "max_supply": county.max_supply,
            "remaining_supply": remaining,
            "supply_pct_minted": (county.total_crypto_minted / county.max_supply * 100) if county.max_supply > 0 else 0,
            "holder_count": holder_count,
            "treasury_balance": county.treasury_balance or 0.0,
            "mining_energy": county.mining_energy_pool or 0.0,
            "block_reward": block_reward,
            "halvings_completed": halvings,
            "next_halving_at": next_halving_at,
            "total_mining_payouts": county.total_mining_payouts or 0,
            "city_count": city_count,
            "top_holders": whale_list,
            "created_at": county.created_at,
        }
    except Exception as e:
        print(f"[Counties] Error getting token info: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        db.close()


# ==========================
# MODULE LIFECYCLE
# ==========================
def initialize():
    """Initialize counties module."""
    print("[Counties] Creating database tables...")
    Base.metadata.create_all(bind=engine)

    db = get_db()
    county_count = db.query(County).count()

    # Generate logos for any counties that don't have one
    counties = db.query(County).filter(County.logo_svg == None).all()
    for county in counties:
        county.logo_svg = generate_token_logo_svg(county.crypto_symbol)
    if counties:
        db.commit()
        print(f"[Counties] Generated {len(counties)} missing token logos")

    # Set max_supply for any counties that don't have it set
    no_supply = db.query(County).filter(County.max_supply == None).all()
    for county in no_supply:
        county.max_supply = MAX_TOKEN_SUPPLY
    if no_supply:
        db.commit()
        print(f"[Counties] Set max supply for {len(no_supply)} counties")

    db.close()

    print(f"[Counties] Current state: {county_count} counties")
    print("[Counties] Module initialized")


async def tick(current_tick: int, now: datetime):
    """
    Counties module tick handler.

    Handles:
    - Government review of petitions (auto-approve after 1 day)
    - Poll closing for county admission votes
    - Mining payouts (with halving)
    - Price snapshots
    """
    db = get_db()

    try:
        # Process expired government reviews
        expired_reviews = db.query(CountyPetition).filter(
            CountyPetition.status == CountyPetitionStatus.PENDING_GOV_REVIEW,
            CountyPetition.gov_review_ends_at <= now,
        ).all()

        for petition in expired_reviews:
            process_gov_review(petition.id)

        # Close expired county polls
        expired_polls = db.query(CountyPoll).filter(
            CountyPoll.status == CountyPollStatus.ACTIVE,
            CountyPoll.closes_at <= now,
        ).all()

        for poll in expired_polls:
            close_county_poll(poll.id)

        db.close()

        # Mining payouts every hour
        if current_tick % MINING_PAYOUT_INTERVAL_TICKS == 0:
            process_mining_payouts(current_tick)

        # Price snapshots every hour (same interval as mining)
        if current_tick % PRICE_SNAPSHOT_INTERVAL_TICKS == 0:
            take_price_snapshots()

        # Process governance cycles every 60 ticks (5 minutes)
        if current_tick % 60 == 0:
            process_governance_cycles(current_tick)

        # Log stats every 6 hours
        if current_tick % 4320 == 0:
            counties = get_all_counties()
            if counties:
                print(f"[Counties] Stats: {len(counties)} counties active")

    except Exception as e:
        print(f"[Counties] Tick error: {e}")
        import traceback
        traceback.print_exc()


# ==========================
# PUBLIC API
# ==========================
__all__ = [
    # Models
    'County', 'CountyCity', 'CountyPetition', 'CountyPoll', 'CountyVote',
    'MiningDeposit', 'CryptoWallet', 'CryptoExchangeOrder',
    'CryptoPriceHistory',
    'GovernanceCycle', 'GovernanceProposal', 'GovernanceVote',

    # Enums
    'CountyPetitionStatus', 'CountyPollType', 'CountyPollStatus',
    'VoteChoice', 'ExchangeOrderType',
    'GovernanceProposalType', 'GovernanceProposalStatus', 'GovernanceCycleStatus',

    # County management
    'get_county_by_id', 'get_county_by_name', 'get_all_counties',
    'get_county_cities', 'get_city_county', 'get_player_county',

    # Petition system
    'petition_join_form_county', 'process_gov_review',

    # Voting
    'cast_county_vote', 'close_county_poll',
    'is_player_in_county', 'is_player_mayor_in_county',

    # Mining
    'deposit_to_mining_node', 'process_mining_payouts',
    'calculate_block_reward', 'get_circulating_supply', 'get_remaining_supply',

    # Crypto
    'calculate_crypto_price', 'get_crypto_price_by_symbol',
    'get_player_wallets', 'get_token_info', 'get_token_holders',
    'sell_crypto_for_cash', 'buy_crypto_with_cash', 'swap_crypto',
    'get_24h_volume', 'get_24h_high_low', 'get_price_history',
    'generate_token_logo_svg',

    # Governance
    'get_current_governance_cycle', 'start_governance_cycle',
    'submit_governance_proposal', 'cast_governance_vote',
    'get_governance_proposals', 'get_player_governance_votes',
    'get_governance_history', 'process_governance_cycles',

    # Constants
    'MAX_COUNTY_CITIES', 'MAYOR_VOTE_WEIGHT', 'MAX_TOKEN_SUPPLY',
    'INITIAL_BLOCK_REWARD', 'HALVING_INTERVAL',
    'GOVERNANCE_VOTE_CYCLE_TICKS', 'GOVERNANCE_PROPOSAL_WINDOW_TICKS',
    'GOVERNANCE_VOTING_WINDOW_TICKS', 'MIN_GOVERNANCE_BURN',
]
