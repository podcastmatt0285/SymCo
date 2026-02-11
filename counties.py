"""
counties.py

County management module for the economic simulation.
Counties are democratically founded federations of Cities.

Handles:
- County creation (Join/Form County petition system)
- Government review period (1 day) for county petitions
- County membership voting (city member vote, mayors get 3 votes)
- County Parliament (lower house: all city members, upper house: mayors with 3 votes)
- County Mining Node (deposit city currency, mine county crypto)
- County cryptocurrency with value pegged to total member cash / 1,000,000,000
- Wadsworth Crypto Exchange (crypto-to-crypto, crypto-to-cash, cash-to-crypto)
"""

from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from sqlalchemy import create_engine, Column, String, Float, DateTime, Integer, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from enum import Enum
from stats_ux import log_transaction
import math

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

    # Mining node energy pool
    mining_energy_pool = Column(Float, default=0.0)  # Deposited city currency value

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
            result.append({
                "id": county.id,
                "name": county.name,
                "crypto_name": county.crypto_name,
                "crypto_symbol": county.crypto_symbol,
                "city_count": city_count,
                "max_cities": MAX_COUNTY_CITIES,
                "crypto_price": crypto_price,
                "total_minted": county.total_crypto_minted,
                "mining_energy": county.mining_energy_pool,
            })
        return result
    except Exception as e:
        print(f"[Counties] Error getting counties: {e}")
        return []
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
# CRYPTO PRICE CALCULATION
# ==========================
def calculate_crypto_price(county_id: int) -> float:
    """
    Calculate the price of a county's cryptocurrency.
    Price = total cash value of every city member in the county / 1,000,000,000
    Rounded down to the nearest penny.
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
        # Round down to nearest penny
        price = math.floor(raw_price * 100) / 100.0
        return max(price, 0.01)  # Minimum price of $0.01
    except Exception as e:
        print(f"[Counties] Error calculating crypto price: {e}")
        return 0.01
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
            county = County(
                name=petition.proposed_county_name,
                crypto_name=petition.proposed_crypto_name,
                crypto_symbol=petition.proposed_crypto_symbol,
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
    """
    db = get_db()
    try:
        counties = db.query(County).filter(County.mining_energy_pool > 0).all()

        for county in counties:
            energy_to_consume = county.mining_energy_pool * MINING_ENERGY_CONSUMPTION_RATE
            if energy_to_consume <= 0:
                continue

            # Get crypto price
            crypto_price = calculate_crypto_price(county.id)
            if crypto_price <= 0:
                continue

            # Calculate total crypto to mint
            crypto_to_mint = (energy_to_consume * MINING_REWARD_MULTIPLIER) / crypto_price

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

            print(f"[Counties] Mining payout: County '{county.name}' minted {crypto_to_mint:.6f} {county.crypto_symbol}")

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
    """
    from auth import Player

    db = get_db()
    try:
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

        player = db.query(Player).filter(Player.id == player_id).first()
        if not player:
            return False, "Player not found"

        # Execute sale
        wallet.balance -= amount
        wallet.total_sold += amount
        player.cash_balance += net_value

        # Burn the sold crypto (reducing supply)
        county = db.query(County).filter(County.crypto_symbol == crypto_symbol).first()
        if county:
            county.total_crypto_burned += amount

        # Fee distribution
        gov = db.query(Player).filter(Player.id == GOVERNMENT_PLAYER_ID).first()
        if gov:
            gov_fee = fee * EXCHANGE_FEE_TO_GOV_PERCENT
            gov.cash_balance += gov_fee

        db.commit()

        log_transaction(
            player_id,
            "crypto_sell",
            "money",
            net_value,
            f"Sold {amount:.6f} {crypto_symbol} @ ${price:,.2f}",
            reference_id=f"exchange_sell_{crypto_symbol}",
        )

        print(f"[Counties] Crypto sale: Player {player_id} sold {amount:.6f} {crypto_symbol} for ${net_value:,.2f}")
        return True, f"Sold {amount:.6f} {crypto_symbol} for ${net_value:,.2f} (fee: ${fee:,.2f})"

    except Exception as e:
        db.rollback()
        print(f"[Counties] Error selling crypto: {e}")
        return False, str(e)
    finally:
        db.close()


def buy_crypto_with_cash(player_id: int, crypto_symbol: str, cash_amount: float) -> Tuple[bool, str]:
    """
    Buy crypto with cash at the pegged price. 2% exchange fee.
    """
    from auth import Player

    db = get_db()
    try:
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

        # Deduct cash
        player.cash_balance -= cash_amount

        # Credit crypto
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

        # Mint new crypto (increasing supply)
        county = db.query(County).filter(County.crypto_symbol == crypto_symbol).first()
        if county:
            county.total_crypto_minted += crypto_amount

        # Fee distribution
        gov = db.query(Player).filter(Player.id == GOVERNMENT_PLAYER_ID).first()
        if gov:
            gov_fee = fee * EXCHANGE_FEE_TO_GOV_PERCENT
            gov.cash_balance += gov_fee

        db.commit()

        log_transaction(
            player_id,
            "crypto_buy",
            "money",
            -cash_amount,
            f"Bought {crypto_amount:.6f} {crypto_symbol} @ ${price:,.2f}",
            reference_id=f"exchange_buy_{crypto_symbol}",
        )

        print(f"[Counties] Crypto buy: Player {player_id} bought {crypto_amount:.6f} {crypto_symbol} for ${cash_amount:,.2f}")
        return True, f"Bought {crypto_amount:.6f} {crypto_symbol} for ${cash_amount:,.2f} (fee: ${fee:,.2f})"

    except Exception as e:
        db.rollback()
        print(f"[Counties] Error buying crypto: {e}")
        return False, str(e)
    finally:
        db.close()


def swap_crypto(player_id: int, sell_symbol: str, buy_symbol: str, sell_amount: float) -> Tuple[bool, str]:
    """
    Swap one crypto for another through the exchange.
    Converts sell crypto → cash → buy crypto. 2% fee on each leg.
    """
    from auth import Player

    db = get_db()
    try:
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

        # Execute sell side
        sell_wallet.balance -= sell_amount
        sell_wallet.total_sold += sell_amount

        sell_county = db.query(County).filter(County.crypto_symbol == sell_symbol).first()
        if sell_county:
            sell_county.total_crypto_burned += sell_amount

        # Execute buy side
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

        buy_county = db.query(County).filter(County.crypto_symbol == buy_symbol).first()
        if buy_county:
            buy_county.total_crypto_minted += buy_amount

        # Fee distribution
        gov = db.query(Player).filter(Player.id == GOVERNMENT_PLAYER_ID).first()
        if gov:
            gov_fee = fee * EXCHANGE_FEE_TO_GOV_PERCENT
            gov.cash_balance += gov_fee

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
        return True, f"Swapped {sell_amount:.6f} {sell_symbol} for {buy_amount:.6f} {buy_symbol} (fee: ${fee:,.2f})"

    except Exception as e:
        db.rollback()
        print(f"[Counties] Error swapping crypto: {e}")
        return False, str(e)
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
    db.close()

    print(f"[Counties] Current state: {county_count} counties")
    print("[Counties] Module initialized")


async def tick(current_tick: int, now: datetime):
    """
    Counties module tick handler.

    Handles:
    - Government review of petitions (auto-approve after 1 day)
    - Poll closing for county admission votes
    - Mining payouts
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

    # Enums
    'CountyPetitionStatus', 'CountyPollType', 'CountyPollStatus',
    'VoteChoice', 'ExchangeOrderType',

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

    # Crypto
    'calculate_crypto_price', 'get_crypto_price_by_symbol',
    'get_player_wallets',
    'sell_crypto_for_cash', 'buy_crypto_with_cash', 'swap_crypto',

    # Constants
    'MAX_COUNTY_CITIES', 'MAYOR_VOTE_WEIGHT',
]
