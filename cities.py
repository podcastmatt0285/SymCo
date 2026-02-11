"""
cities.py

City management module for the economic simulation.
Cities are formed by merging districts and create powerful economic zones
with their own central banks, currencies, and governance.

Handles:
- City creation (10 districts sacrificed, $10M cost)
- City membership (max 25, application process with voting)
- City Bank operations (currency exchange, production subsidies)
- Petrodollar system (forced currency for outsider trades)
- Government grants and loans to city banks
- Democratic voting (applications, currency changes, banishments)
- Reserve requirements for members
- Poll tax system
"""

from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from sqlalchemy import create_engine, Column, String, Float, DateTime, Integer, Boolean, Text, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from enum import Enum
from stats_ux import log_transaction

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
CITY_CREATION_COST = 10_000_000.0  # $10M
DISTRICTS_REQUIRED = 10
MAX_CITY_MEMBERS = 25
MIN_APPLICATION_FEE_PERCENT = 10.0
MAX_APPLICATION_FEE_PERCENT = 45.0
PRODUCTION_SUBSIDY_RATE = 0.0475  # 4.75%
CURRENCY_SELL_DISCOUNT = 0.03  # Bank sells at 3% below market
RESERVE_REQUIREMENT_PERCENT = 0.10  # 10% of total value
RESERVE_SHORTFALL_FEE_MULTIPLIER = 1.25  # 125% fee for shortfall
MAX_POLL_TAX_PERCENT = 0.035  # 3.5% of bank reserves
GOVERNMENT_PLAYER_ID = 0
GOV_GRANT_INTERVAL_TICKS = 8640  # 12 hours at 5 sec/tick
GOV_GRANT_PERCENT = 0.02  # 2% of gov reserves
GOV_LOAN_INTEREST_RATE = 0.07  # 7% per installment
GOV_LOAN_INSTALLMENTS = 30
GOV_LOAN_INSTALLMENT_INTERVAL_TICKS = 8640  # 12 hours
MAX_CITY_BANK_LOANS = 5
DEBT_ASSUMPTION_FRACTION = 1 / 25  # Members can assume 1/25th of debt

# Poll durations in ticks (5 sec each)
APPLICATION_POLL_DURATION_TICKS = 17280  # 24 hours
BANISHMENT_POLL_DURATION_TICKS = 17280  # 24 hours
CURRENCY_POLL_DURATION_TICKS = 120960  # 7 days
CURRENCY_CHANGE_COOLDOWN_TICKS = 518400  # 30 days

# ==========================
# ENUMS
# ==========================
class PollType(str, Enum):
    APPLICATION = "application"
    BANISHMENT = "banishment"
    CURRENCY_CHANGE = "currency_change"

class PollStatus(str, Enum):
    ACTIVE = "active"
    PASSED = "passed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class VoteChoice(str, Enum):
    YES = "yes"
    NO = "no"

# ==========================
# DATABASE MODELS
# ==========================
class City(Base):
    """City entity - a merged group of districts with governance."""
    __tablename__ = "cities"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    mayor_id = Column(Integer, index=True, nullable=False)  # Founder/creator
    
    # Currency (commodity type used as petrodollar)
    currency_type = Column(String, nullable=True)  # Item type from inventory
    
    # Fee settings (Mayor controlled)
    application_fee_percent = Column(Float, default=25.0)  # 10-45%
    relocation_fee_percent = Column(Float, default=10.0)  # Fee to leave voluntarily
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    last_currency_change_vote = Column(DateTime, nullable=True)  # For monthly cooldown


class CityBank(Base):
    """The First Bank of {city} - handles currency and subsidies."""
    __tablename__ = "city_banks"
    
    id = Column(Integer, primary_key=True, index=True)
    city_id = Column(Integer, index=True, nullable=False)
    
    # Bank reserves
    cash_reserves = Column(Float, default=0.0)
    
    # Currency inventory (the commodity)
    currency_type = Column(String, nullable=True)
    currency_quantity = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class CityMember(Base):
    """City membership record."""
    __tablename__ = "city_members"
    
    id = Column(Integer, primary_key=True, index=True)
    city_id = Column(Integer, index=True, nullable=False)
    player_id = Column(Integer, index=True, nullable=False)
    
    # Track for banishment reimbursement
    application_fee_paid = Column(Float, default=0.0)
    
    joined_at = Column(DateTime, default=datetime.utcnow)
    is_mayor = Column(Boolean, default=False)


class CityApplication(Base):
    """Pending city membership application."""
    __tablename__ = "city_applications"
    
    id = Column(Integer, primary_key=True, index=True)
    city_id = Column(Integer, index=True, nullable=False)
    applicant_id = Column(Integer, index=True, nullable=False)
    
    # Calculated fee at application time
    calculated_fee = Column(Float, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="pending")  # pending, approved, rejected


class CityPoll(Base):
    """Active poll for city governance."""
    __tablename__ = "city_polls"
    
    id = Column(Integer, primary_key=True, index=True)
    city_id = Column(Integer, index=True, nullable=False)
    poll_type = Column(String, nullable=False)  # application, banishment, currency_change
    
    # Target of the poll
    target_player_id = Column(Integer, nullable=True)  # For application/banishment
    proposed_currency = Column(String, nullable=True)  # For currency change
    
    # Poll tax collected
    poll_tax_amount = Column(Float, default=0.0)
    
    # Timing
    created_at = Column(DateTime, default=datetime.utcnow)
    closes_at = Column(DateTime, nullable=False)
    
    # Status
    status = Column(String, default=PollStatus.ACTIVE)
    
    # Results (calculated when closed)
    yes_votes = Column(Integer, default=0)
    no_votes = Column(Integer, default=0)


class CityVote(Base):
    """Individual vote on a poll."""
    __tablename__ = "city_votes"
    
    id = Column(Integer, primary_key=True, index=True)
    poll_id = Column(Integer, index=True, nullable=False)
    voter_id = Column(Integer, index=True, nullable=False)
    
    vote = Column(String, nullable=False)  # yes, no
    vote_weight = Column(Integer, default=1)  # Mayor gets extra votes
    
    cast_at = Column(DateTime, default=datetime.utcnow)


class CityBankLoan(Base):
    """Government loan to a city bank."""
    __tablename__ = "city_bank_loans"
    
    id = Column(Integer, primary_key=True, index=True)
    city_bank_id = Column(Integer, index=True, nullable=False)
    
    # Loan terms
    principal = Column(Float, nullable=False)
    interest_rate = Column(Float, default=GOV_LOAN_INTEREST_RATE)
    
    # Repayment tracking
    total_owed = Column(Float, nullable=False)
    amount_paid = Column(Float, default=0.0)
    installment_amount = Column(Float, nullable=False)
    installments_remaining = Column(Integer, default=GOV_LOAN_INSTALLMENTS)
    
    # Timing
    created_at = Column(DateTime, default=datetime.utcnow)
    next_payment_tick = Column(Integer, nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True)


class CityDebtAssumption(Base):
    """Track member debt assumption from loans."""
    __tablename__ = "city_debt_assumptions"
    
    id = Column(Integer, primary_key=True, index=True)
    loan_id = Column(Integer, index=True, nullable=False)
    player_id = Column(Integer, index=True, nullable=False)
    
    amount_assumed = Column(Float, nullable=False)
    assumed_at = Column(DateTime, default=datetime.utcnow)


class CityProductionLog(Base):
    """Track production for subsidy calculations."""
    __tablename__ = "city_production_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    city_id = Column(Integer, index=True, nullable=False)
    player_id = Column(Integer, index=True, nullable=False)
    business_id = Column(Integer, index=True, nullable=False)
    
    # Production details
    production_cost = Column(Float, nullable=False)  # Market value of inputs
    subsidy_paid = Column(Float, nullable=False)
    
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
        print(f"[Cities] Database error: {e}")
        db.close()
        raise


def get_player_total_value(player_id: int) -> float:
    """
    Calculate a player's total value (cash + inventory at market prices + business value).
    Used for application fees and reserve requirements.
    """
    from auth import Player
    import inventory
    import market
    from business import Business, BUSINESS_TYPES
    
    db = get_db()
    total = 0.0
    
    # Cash balance
    player = db.query(Player).filter(Player.id == player_id).first()
    if player:
        total += player.cash_balance
    
    # Inventory value at market prices
    player_inv = inventory.get_player_inventory(player_id)
    for item_type, quantity in player_inv.items():
        price = market.get_market_price(item_type) or 1.0
        total += quantity * price
    
    # Business value (startup costs)
    businesses = db.query(Business).filter(Business.owner_id == player_id).all()
    for biz in businesses:
        config = BUSINESS_TYPES.get(biz.business_type, {})
        total += config.get("startup_cost", 2500.0)
    
    db.close()
    return total


def get_city_by_id(city_id: int) -> Optional[City]:
    """Get a city by ID."""
    db = get_db()
    city = db.query(City).filter(City.id == city_id).first()
    db.close()
    return city


def get_city_by_name(name: str) -> Optional[City]:
    """Get a city by name."""
    db = get_db()
    city = db.query(City).filter(City.name == name).first()
    db.close()
    return city


def get_player_city(player_id: int) -> Optional[City]:
    """Get the city a player belongs to (if any)."""
    db = get_db()
    membership = db.query(CityMember).filter(CityMember.player_id == player_id).first()
    if not membership:
        db.close()
        return None
    city = db.query(City).filter(City.id == membership.city_id).first()
    db.close()
    return city


def get_city_bank(city_id: int) -> Optional[CityBank]:
    """Get the bank for a city."""
    db = get_db()
    bank = db.query(CityBank).filter(CityBank.city_id == city_id).first()
    db.close()
    return bank


def get_city_members(city_id: int) -> List[CityMember]:
    """Get all members of a city."""
    db = get_db()
    members = db.query(CityMember).filter(CityMember.city_id == city_id).all()
    db.close()
    return members


def is_city_member(player_id: int, city_id: int) -> bool:
    """Check if a player is a member of a specific city."""
    db = get_db()
    member = db.query(CityMember).filter(
        CityMember.player_id == player_id,
        CityMember.city_id == city_id
    ).first()
    db.close()
    return member is not None


def is_mayor(player_id: int, city_id: int) -> bool:
    """Check if a player is the mayor of a city."""
    db = get_db()
    city = db.query(City).filter(City.id == city_id).first()
    db.close()
    return city is not None and city.mayor_id == player_id


# ==========================
# CITY CREATION
# ==========================
def create_city(founder_id: int, city_name: str, district_ids: List[int]) -> Tuple[Optional[City], str]:
    """
    Create a new city by sacrificing 10 districts.
    
    Args:
        founder_id: Player ID of the city founder (becomes Mayor)
        city_name: Name for the new city
        district_ids: List of 10 district IDs to sacrifice
    
    Returns:
        (City instance or None, status message)
    """
    from auth import Player
    from districts import District
    
    db = get_db()
    
    try:
        # Validate founder
        player = db.query(Player).filter(Player.id == founder_id).first()
        if not player:
            return None, "Player not found"
        
        # Check founder isn't already in a city
        existing_membership = db.query(CityMember).filter(CityMember.player_id == founder_id).first()
        if existing_membership:
            return None, "You are already a member of a city"
        
        # Validate city name is unique
        existing_city = db.query(City).filter(City.name == city_name).first()
        if existing_city:
            return None, "A city with this name already exists"
        
        # Validate district count
        if len(district_ids) != DISTRICTS_REQUIRED:
            return None, f"Exactly {DISTRICTS_REQUIRED} districts are required"
        
        # Validate all districts exist and are owned by founder
        districts = []
        for district_id in district_ids:
            district = db.query(District).filter(District.id == district_id).first()
            if not district:
                return None, f"District {district_id} not found"
            if district.owner_id != founder_id:
                return None, f"District {district_id} is not owned by you"
            if district.occupied_by_business_id is not None:
                return None, f"District {district_id} has a business on it - remove it first"
            districts.append(district)
        
        # Check founder has enough cash
        if player.cash_balance < CITY_CREATION_COST:
            return None, f"Insufficient funds. Need ${CITY_CREATION_COST:,.2f}"
        
        # Deduct creation cost
        player.cash_balance -= CITY_CREATION_COST
        # Log city creation cost
        log_transaction(
            founder_id,
            "city_creation",
            "money",
            -CITY_CREATION_COST,
            f"Founded city: {city_name}",
            reference_id=f"city_creation"
        )
        
        # Create the city
        city = City(
            name=city_name,
            mayor_id=founder_id,
            application_fee_percent=25.0,  # Default middle ground
            relocation_fee_percent=10.0
        )
        db.add(city)
        db.flush()  # Get the city ID
        
        # Create the city bank with creation cost as initial reserves
        bank = CityBank(
            city_id=city.id,
            cash_reserves=CITY_CREATION_COST
        )
        db.add(bank)
        
        # Create founder as first member (and mayor)
        membership = CityMember(
            city_id=city.id,
            player_id=founder_id,
            application_fee_paid=0.0,  # Founder doesn't pay
            is_mayor=True
        )
        db.add(membership)
        
        # Destroy all sacrificed districts
        for district in districts:
            print(f"[Cities] Destroying district {district.id} ({district.district_type}) for city creation")
            db.delete(district)
        
        db.commit()
        
        print(f"[Cities] Created city '{city_name}' (ID: {city.id}) by player {founder_id}")
        print(f"[Cities] Sacrificed {len(districts)} districts, bank reserves: ${CITY_CREATION_COST:,.2f}")
        
        return city, "Success"
        
    except Exception as e:
        db.rollback()
        print(f"[Cities] Error creating city: {e}")
        import traceback
        traceback.print_exc()
        return None, str(e)
    finally:
        db.close()


# ==========================
# MEMBERSHIP MANAGEMENT
# ==========================
def apply_to_city(player_id: int, city_id: int) -> Tuple[Optional[CityApplication], str]:
    """
    Submit an application to join a city.
    Creates a poll for existing members to vote on.
    
    Returns:
        (CityApplication or None, status message)
    """
    from auth import Player
    
    db = get_db()
    
    try:
        # Validate player
        player = db.query(Player).filter(Player.id == player_id).first()
        if not player:
            return None, "Player not found"
        
        # Check player isn't already in a city
        existing_membership = db.query(CityMember).filter(CityMember.player_id == player_id).first()
        if existing_membership:
            return None, "You are already a member of a city"
        
        # Validate city
        city = db.query(City).filter(City.id == city_id).first()
        if not city:
            return None, "City not found"
        
        # Check city isn't full
        member_count = db.query(CityMember).filter(CityMember.city_id == city_id).count()
        if member_count >= MAX_CITY_MEMBERS:
            return None, "City is at maximum capacity"
        
        # Check for existing pending application
        existing_app = db.query(CityApplication).filter(
            CityApplication.city_id == city_id,
            CityApplication.applicant_id == player_id,
            CityApplication.status == "pending"
        ).first()
        if existing_app:
            return None, "You already have a pending application"
        
        # Calculate application fee
        total_value = get_player_total_value(player_id)
        fee = total_value * (city.application_fee_percent / 100.0)
        
        # Check player can afford the fee
        if player.cash_balance < fee:
            return None, f"Insufficient funds for application fee (${fee:,.2f})"
        
        # Create application
        application = CityApplication(
            city_id=city_id,
            applicant_id=player_id,
            calculated_fee=fee
        )
        db.add(application)
        db.flush()
        
        # Create poll for members to vote
        closes_at = datetime.utcnow() + timedelta(seconds=APPLICATION_POLL_DURATION_TICKS * 5)
        poll = CityPoll(
            city_id=city_id,
            poll_type=PollType.APPLICATION,
            target_player_id=player_id,
            closes_at=closes_at
        )
        db.add(poll)
        
        db.commit()
        
        print(f"[Cities] Application submitted: Player {player_id} → City {city_id}, fee: ${fee:,.2f}")
        
        return application, "Application submitted successfully"
        
    except Exception as e:
        db.rollback()
        print(f"[Cities] Error applying to city: {e}")
        return None, str(e)
    finally:
        db.close()


def process_application_approval(application_id: int) -> Tuple[bool, str]:
    """
    Process an approved application - collect fee and add member.
    Called when application poll passes.
    """
    from auth import Player
    
    db = get_db()
    
    try:
        application = db.query(CityApplication).filter(CityApplication.id == application_id).first()
        if not application:
            return False, "Application not found"
        
        if application.status != "pending":
            return False, "Application is not pending"
        
        player = db.query(Player).filter(Player.id == application.applicant_id).first()
        if not player:
            return False, "Applicant not found"
        
        city = db.query(City).filter(City.id == application.city_id).first()
        if not city:
            return False, "City not found"
        
        # Collect fee - goes to Mayor personally
        mayor = db.query(Player).filter(Player.id == city.mayor_id).first()
        if not mayor:
            return False, "Mayor not found"
        
        if player.cash_balance < application.calculated_fee:
            application.status = "rejected"
            db.commit()
            return False, "Applicant can no longer afford the fee"
        
        player.cash_balance -= application.calculated_fee
        mayor.cash_balance += application.calculated_fee
        # Log application fee transactions
        log_transaction(
            application.applicant_id,
            "city_application_fee",
            "money",
            -application.calculated_fee,
            f"City membership fee: {city.name}",
            reference_id=f"city_{city.id}_join"
        )
        log_transaction(
            city.mayor_id,
            "city_application_income",
            "money",
            application.calculated_fee,
            f"Membership fee received from new member",
            reference_id=f"city_{city.id}_join"
        )
        
        # Create membership
        membership = CityMember(
            city_id=application.city_id,
            player_id=application.applicant_id,
            application_fee_paid=application.calculated_fee
        )
        db.add(membership)
        
        application.status = "approved"
        db.commit()
        
        print(f"[Cities] Application approved: Player {application.applicant_id} joined City {application.city_id}")
        print(f"[Cities] Fee ${application.calculated_fee:,.2f} paid to Mayor {city.mayor_id}")
        
        return True, "Welcome to the city!"
        
    except Exception as e:
        db.rollback()
        print(f"[Cities] Error processing application: {e}")
        return False, str(e)
    finally:
        db.close()


def leave_city(player_id: int) -> Tuple[bool, str]:
    """
    Voluntarily leave a city. Player pays relocation fee.
    """
    from auth import Player
    
    db = get_db()
    
    try:
        membership = db.query(CityMember).filter(CityMember.player_id == player_id).first()
        if not membership:
            return False, "You are not a member of any city"
        
        city = db.query(City).filter(City.id == membership.city_id).first()
        if not city:
            return False, "City not found"
        
        # Mayors cannot leave
        if city.mayor_id == player_id:
            return False, "Mayors cannot leave their city"
        
        player = db.query(Player).filter(Player.id == player_id).first()
        if not player:
            return False, "Player not found"
        
        # Calculate and collect relocation fee
        total_value = get_player_total_value(player_id)
        relocation_fee = total_value * (city.relocation_fee_percent / 100.0)
        
        if player.cash_balance < relocation_fee:
            return False, f"Insufficient funds for relocation fee (${relocation_fee:,.2f})"
        
        # Pay relocation fee to city bank
        bank = db.query(CityBank).filter(CityBank.city_id == city.id).first()
        if bank:
            player.cash_balance -= relocation_fee
            bank.cash_reserves += relocation_fee
            # Log relocation fee
            log_transaction(
                player_id,
                "city_relocation_fee",
                "money",
                -relocation_fee,
                f"Left city: {city.name}",
                reference_id=f"city_{city.id}_leave"
            )
        
        # Remove membership
        db.delete(membership)
        db.commit()
        
        print(f"[Cities] Player {player_id} left City {city.id}, paid ${relocation_fee:,.2f} relocation fee")
        
        return True, "You have left the city"
        
    except Exception as e:
        db.rollback()
        print(f"[Cities] Error leaving city: {e}")
        return False, str(e)
    finally:
        db.close()


def initiate_banishment(mayor_id: int, target_player_id: int, city_id: int) -> Tuple[Optional[CityPoll], str]:
    """
    Mayor initiates a banishment vote against a city member.
    """
    db = get_db()
    
    try:
        city = db.query(City).filter(City.id == city_id).first()
        if not city:
            return None, "City not found"
        
        if city.mayor_id != mayor_id:
            return None, "Only the Mayor can initiate banishment"
        
        if target_player_id == mayor_id:
            return None, "Mayor cannot banish themselves"
        
        # Verify target is a member
        membership = db.query(CityMember).filter(
            CityMember.city_id == city_id,
            CityMember.player_id == target_player_id
        ).first()
        if not membership:
            return None, "Target is not a city member"
        
        # Check no active banishment poll exists for this player
        existing_poll = db.query(CityPoll).filter(
            CityPoll.city_id == city_id,
            CityPoll.poll_type == PollType.BANISHMENT,
            CityPoll.target_player_id == target_player_id,
            CityPoll.status == PollStatus.ACTIVE
        ).first()
        if existing_poll:
            return None, "A banishment vote is already in progress for this player"
        
        # Create banishment poll
        closes_at = datetime.utcnow() + timedelta(seconds=BANISHMENT_POLL_DURATION_TICKS * 5)
        poll = CityPoll(
            city_id=city_id,
            poll_type=PollType.BANISHMENT,
            target_player_id=target_player_id,
            closes_at=closes_at
        )
        db.add(poll)
        db.commit()
        
        print(f"[Cities] Banishment poll started: City {city_id} vs Player {target_player_id}")
        
        return poll, "Banishment vote initiated"
        
    except Exception as e:
        db.rollback()
        print(f"[Cities] Error initiating banishment: {e}")
        return None, str(e)
    finally:
        db.close()


def process_banishment(city_id: int, player_id: int) -> Tuple[bool, str]:
    """
    Execute banishment - Mayor reimburses the entry fee.
    Called when banishment poll passes.
    """
    from auth import Player
    
    db = get_db()
    
    try:
        membership = db.query(CityMember).filter(
            CityMember.city_id == city_id,
            CityMember.player_id == player_id
        ).first()
        if not membership:
            return False, "Player is not a member"
        
        city = db.query(City).filter(City.id == city_id).first()
        if not city:
            return False, "City not found"
        
        player = db.query(Player).filter(Player.id == player_id).first()
        mayor = db.query(Player).filter(Player.id == city.mayor_id).first()
        
        if not player or not mayor:
            return False, "Player or Mayor not found"
        
        # Mayor reimburses the original entry fee
        reimbursement = membership.application_fee_paid
        
        if mayor.cash_balance < reimbursement:
            return False, f"Mayor cannot afford reimbursement (${reimbursement:,.2f})"
        
        mayor.cash_balance -= reimbursement
        player.cash_balance += reimbursement
        
        # Remove membership
        db.delete(membership)
        db.commit()
        
        print(f"[Cities] Player {player_id} banished from City {city_id}, reimbursed ${reimbursement:,.2f}")
        
        return True, "Player has been banished"
        
    except Exception as e:
        db.rollback()
        print(f"[Cities] Error processing banishment: {e}")
        return False, str(e)
    finally:
        db.close()


# ==========================
# VOTING SYSTEM
# ==========================
def cast_vote(voter_id: int, poll_id: int, vote: VoteChoice) -> Tuple[bool, str]:
    """
    Cast a vote on a poll. Mayor gets extra votes depending on poll type.
    """
    db = get_db()
    
    try:
        poll = db.query(CityPoll).filter(CityPoll.id == poll_id).first()
        if not poll:
            return False, "Poll not found"
        
        if poll.status != PollStatus.ACTIVE:
            return False, "Poll is no longer active"
        
        if datetime.utcnow() > poll.closes_at:
            return False, "Poll has closed"
        
        # Verify voter is a city member
        membership = db.query(CityMember).filter(
            CityMember.city_id == poll.city_id,
            CityMember.player_id == voter_id
        ).first()
        if not membership:
            return False, "You are not a member of this city"
        
        # Check for existing vote
        existing_vote = db.query(CityVote).filter(
            CityVote.poll_id == poll_id,
            CityVote.voter_id == voter_id
        ).first()
        if existing_vote:
            return False, "You have already voted on this poll"
        
        # Determine vote weight
        city = db.query(City).filter(City.id == poll.city_id).first()
        vote_weight = 1
        
        if city and city.mayor_id == voter_id:
            if poll.poll_type == PollType.BANISHMENT:
                vote_weight = 1  # Mayor gets 1 vote on banishment
            else:
                vote_weight = 3  # Mayor gets 3 votes on applications and currency changes
        
        # Record vote
        city_vote = CityVote(
            poll_id=poll_id,
            voter_id=voter_id,
            vote=vote.value,
            vote_weight=vote_weight
        )
        db.add(city_vote)
        db.commit()
        
        print(f"[Cities] Vote cast: Player {voter_id} voted {vote.value} on poll {poll_id} (weight: {vote_weight})")
        
        return True, f"Vote recorded ({vote_weight}x weight)"
        
    except Exception as e:
        db.rollback()
        print(f"[Cities] Error casting vote: {e}")
        return False, str(e)
    finally:
        db.close()


def close_poll(poll_id: int) -> Tuple[bool, str]:
    """
    Close a poll and process the results.
    """
    db = get_db()
    
    try:
        poll = db.query(CityPoll).filter(CityPoll.id == poll_id).first()
        if not poll:
            return False, "Poll not found"
        
        if poll.status != PollStatus.ACTIVE:
            return False, "Poll is not active"
        
        # Count votes
        votes = db.query(CityVote).filter(CityVote.poll_id == poll_id).all()
        
        yes_votes = sum(v.vote_weight for v in votes if v.vote == VoteChoice.YES)
        no_votes = sum(v.vote_weight for v in votes if v.vote == VoteChoice.NO)
        
        poll.yes_votes = yes_votes
        poll.no_votes = no_votes
        
        # Determine outcome (simple majority)
        passed = yes_votes > no_votes
        poll.status = PollStatus.PASSED if passed else PollStatus.FAILED
        
        db.commit()
        db.close()
        
        # Process based on poll type
        if passed:
            if poll.poll_type == PollType.APPLICATION:
                # Find and approve application
                app = get_db().query(CityApplication).filter(
                    CityApplication.city_id == poll.city_id,
                    CityApplication.applicant_id == poll.target_player_id,
                    CityApplication.status == "pending"
                ).first()
                if app:
                    process_application_approval(app.id)
            
            elif poll.poll_type == PollType.BANISHMENT:
                process_banishment(poll.city_id, poll.target_player_id)
            
            elif poll.poll_type == PollType.CURRENCY_CHANGE:
                set_city_currency(poll.city_id, poll.proposed_currency)
        
        else:
            # Reject application if it failed
            if poll.poll_type == PollType.APPLICATION:
                db2 = get_db()
                app = db2.query(CityApplication).filter(
                    CityApplication.city_id == poll.city_id,
                    CityApplication.applicant_id == poll.target_player_id,
                    CityApplication.status == "pending"
                ).first()
                if app:
                    app.status = "rejected"
                    db2.commit()
                db2.close()
        
        print(f"[Cities] Poll {poll_id} closed: {poll.status} (YES: {yes_votes}, NO: {no_votes})")
        
        return True, f"Poll closed: {poll.status}"
        
    except Exception as e:
        print(f"[Cities] Error closing poll: {e}")
        import traceback
        traceback.print_exc()
        return False, str(e)


# ==========================
# CURRENCY MANAGEMENT
# ==========================
def initiate_currency_change(mayor_id: int, city_id: int, new_currency: str, poll_tax_amount: float) -> Tuple[Optional[CityPoll], str]:
    """
    Mayor initiates a vote to change the city currency.
    Can only be done once per month.
    """
    from auth import Player
    
    db = get_db()
    
    try:
        city = db.query(City).filter(City.id == city_id).first()
        if not city:
            return None, "City not found"
        
        if city.mayor_id != mayor_id:
            return None, "Only the Mayor can initiate currency changes"
        
        # Check monthly cooldown
        if city.last_currency_change_vote:
            cooldown_ends = city.last_currency_change_vote + timedelta(seconds=CURRENCY_CHANGE_COOLDOWN_TICKS * 5)
            if datetime.utcnow() < cooldown_ends:
                return None, "Currency change can only be initiated once per month"
        
        # Validate poll tax
        bank = db.query(CityBank).filter(CityBank.city_id == city_id).first()
        if not bank:
            return None, "City bank not found"
        
        max_poll_tax = bank.cash_reserves * MAX_POLL_TAX_PERCENT
        if poll_tax_amount > max_poll_tax:
            return None, f"Poll tax cannot exceed ${max_poll_tax:,.2f} (3.5% of bank reserves)"
        
        if poll_tax_amount < 0:
            return None, "Poll tax cannot be negative"
        
        # Collect poll tax from Mayor
        mayor = db.query(Player).filter(Player.id == mayor_id).first()
        if not mayor:
            return None, "Mayor not found"
        
        if mayor.cash_balance < poll_tax_amount:
            return None, f"Insufficient funds for poll tax (${poll_tax_amount:,.2f})"
        
        mayor.cash_balance -= poll_tax_amount
        bank.cash_reserves += poll_tax_amount
        
        # Create poll
        closes_at = datetime.utcnow() + timedelta(seconds=CURRENCY_POLL_DURATION_TICKS * 5)
        poll = CityPoll(
            city_id=city_id,
            poll_type=PollType.CURRENCY_CHANGE,
            proposed_currency=new_currency,
            poll_tax_amount=poll_tax_amount,
            closes_at=closes_at
        )
        db.add(poll)
        
        city.last_currency_change_vote = datetime.utcnow()
        
        db.commit()
        
        print(f"[Cities] Currency change poll started: City {city_id} → {new_currency}")
        
        return poll, "Currency change vote initiated"
        
    except Exception as e:
        db.rollback()
        print(f"[Cities] Error initiating currency change: {e}")
        return None, str(e)
    finally:
        db.close()


def set_city_currency(city_id: int, currency_type: str) -> bool:
    """
    Set the city's currency (called when currency change poll passes).
    """
    db = get_db()
    
    try:
        city = db.query(City).filter(City.id == city_id).first()
        bank = db.query(CityBank).filter(CityBank.city_id == city_id).first()
        
        if not city or not bank:
            return False
        
        city.currency_type = currency_type
        bank.currency_type = currency_type
        
        db.commit()
        
        print(f"[Cities] City {city_id} currency set to: {currency_type}")
        
        return True
        
    except Exception as e:
        db.rollback()
        print(f"[Cities] Error setting currency: {e}")
        return False
    finally:
        db.close()


# ==========================
# CITY BANK OPERATIONS
# ==========================
def pay_production_subsidy(player_id: int, business_id: int, production_cost: float) -> float:
    """
    Pay production subsidy (4.75%) to a city member.
    Called from business.py when production completes.
    
    Returns:
        Amount of subsidy paid (0 if not a city member or bank can't afford it)
    """
    from auth import Player
    
    db = get_db()
    
    try:
        # Check if player is in a city
        membership = db.query(CityMember).filter(CityMember.player_id == player_id).first()
        if not membership:
            return 0.0
        
        bank = db.query(CityBank).filter(CityBank.city_id == membership.city_id).first()
        if not bank:
            return 0.0
        
        subsidy = production_cost * PRODUCTION_SUBSIDY_RATE
        
        # Check if bank can afford it
        if bank.cash_reserves < subsidy:
            print(f"[Cities] Bank cannot afford subsidy ${subsidy:,.2f}")
            return 0.0
        
        player = db.query(Player).filter(Player.id == player_id).first()
        if not player:
            return 0.0
        
        # Pay subsidy
        bank.cash_reserves -= subsidy
        player.cash_balance += subsidy
        # Log the subsidy transaction
        log_transaction(
            player_id,
            "city_subsidy",
            "money",
            subsidy,
            f"Production subsidy from city bank",
            reference_id=f"business_{business_id}"
        )
        
        # Log the subsidy
        log = CityProductionLog(
            city_id=membership.city_id,
            player_id=player_id,
            business_id=business_id,
            production_cost=production_cost,
            subsidy_paid=subsidy
        )
        db.add(log)
        
        db.commit()
        
        return subsidy
        
    except Exception as e:
        db.rollback()
        print(f"[Cities] Error paying subsidy: {e}")
        return 0.0
    finally:
        db.close()


def exchange_currency_for_member(player_id: int, quantity: float) -> Tuple[bool, str]:
    """
    City member sells city currency to the bank at market price.
    Bank will list it at 3% below market (handled separately).
    """
    from auth import Player
    import inventory
    import market
    
    db = get_db()
    
    try:
        membership = db.query(CityMember).filter(CityMember.player_id == player_id).first()
        if not membership:
            return False, "Not a city member"
        
        bank = db.query(CityBank).filter(CityBank.city_id == membership.city_id).first()
        if not bank or not bank.currency_type:
            return False, "City has no currency set"
        
        # Check player has the currency
        player_qty = inventory.get_item_quantity(player_id, bank.currency_type)
        if player_qty < quantity:
            return False, f"Insufficient {bank.currency_type}"
        
        # Get market price
        market_price = market.get_market_price(bank.currency_type) or 1.0
        total_value = quantity * market_price
        
        # Check bank can afford it
        if bank.cash_reserves < total_value:
            return False, "City bank has insufficient reserves"
        
        player = db.query(Player).filter(Player.id == player_id).first()
        if not player:
            return False, "Player not found"
        
        # Execute exchange
        inventory.remove_item(player_id, bank.currency_type, quantity)
        player.cash_balance += total_value
        bank.cash_reserves -= total_value
        bank.currency_quantity += quantity
        
        db.commit()
        
        print(f"[Cities] Member {player_id} sold {quantity} {bank.currency_type} to bank for ${total_value:,.2f}")
        
        return True, f"Exchanged {quantity} {bank.currency_type} for ${total_value:,.2f}"
        
    except Exception as e:
        db.rollback()
        print(f"[Cities] Error in currency exchange: {e}")
        return False, str(e)
    finally:
        db.close()


def bank_list_currency_at_discount(city_id: int) -> Tuple[bool, str]:
    """
    City bank lists its currency inventory at 3% below market price.
    Called periodically from tick.
    """
    import market
    
    db = get_db()
    
    try:
        bank = db.query(CityBank).filter(CityBank.city_id == city_id).first()
        if not bank or bank.currency_quantity <= 0 or not bank.currency_type:
            return False, "No currency to list"
        
        # Get market price
        market_price = market.get_market_price(bank.currency_type)
        if not market_price or market_price <= 0:
            return False, "Cannot determine market price"
        
        # Calculate discounted price (3% below market)
        discounted_price = market_price * (1 - CURRENCY_SELL_DISCOUNT)
        
        # Create sell order for bank (using negative player ID)
        # Bank ID is -(1000 + city_id) to avoid collision with other special IDs
        bank_player_id = -(1000 + city_id)
        
        # First, ensure bank has the inventory item
        import inventory
        inventory.add_item(bank_player_id, bank.currency_type, bank.currency_quantity)
        
        order = market.create_order(
            player_id=bank_player_id,
            order_type=market.OrderType.SELL,
            order_mode=market.OrderMode.LIMIT,
            item_type=bank.currency_type,
            quantity=bank.currency_quantity,
            price=discounted_price
        )
        
        if order:
            bank.currency_quantity = 0  # Inventory is now in market order
            db.commit()
            print(f"[Cities] Bank {city_id} listed {order.quantity} {bank.currency_type} at ${discounted_price:,.2f} (3% discount)")
            return True, "Currency listed"
        
        return False, "Failed to create order"
        
    except Exception as e:
        db.rollback()
        print(f"[Cities] Error listing currency: {e}")
        return False, str(e)
    finally:
        db.close()


# ==========================
# RESERVE REQUIREMENT
# ==========================
def check_member_reserves(player_id: int) -> Tuple[bool, float]:
    """
    Check if a city member meets the reserve requirement.
    Returns (meets_requirement, shortfall_amount).
    """
    import inventory
    import market
    
    db = get_db()
    
    try:
        membership = db.query(CityMember).filter(CityMember.player_id == player_id).first()
        if not membership:
            return True, 0.0  # Not a member, no requirement
        
        city = db.query(City).filter(City.id == membership.city_id).first()
        if not city or not city.currency_type:
            return True, 0.0  # No currency set
        
        # Calculate required reserve
        total_value = get_player_total_value(player_id)
        required_value = total_value * RESERVE_REQUIREMENT_PERCENT
        
        # Get player's currency holdings
        currency_qty = inventory.get_item_quantity(player_id, city.currency_type)
        currency_price = market.get_market_price(city.currency_type) or 1.0
        current_value = currency_qty * currency_price
        
        if current_value >= required_value:
            return True, 0.0
        
        shortfall_value = required_value - current_value
        return False, shortfall_value
        
    except Exception as e:
        print(f"[Cities] Error checking reserves: {e}")
        return True, 0.0
    finally:
        db.close()


def enforce_reserve_requirement(player_id: int) -> Tuple[bool, str]:
    """
    Enforce reserve requirement - charge 125% fee and buy currency for member.
    """
    from auth import Player
    import inventory
    import market
    
    meets_requirement, shortfall = check_member_reserves(player_id)
    if meets_requirement:
        return True, "Reserve requirement met"
    
    db = get_db()
    
    try:
        membership = db.query(CityMember).filter(CityMember.player_id == player_id).first()
        if not membership:
            return False, "Not a city member"
        
        city = db.query(City).filter(City.id == membership.city_id).first()
        if not city or not city.currency_type:
            return False, "No currency set"
        
        player = db.query(Player).filter(Player.id == player_id).first()
        if not player:
            return False, "Player not found"
        
        # Calculate fee (125% of shortfall)
        fee = shortfall * RESERVE_SHORTFALL_FEE_MULTIPLIER
        
        if player.cash_balance < fee:
            # Player can't afford - log warning but don't fail
            print(f"[Cities] WARNING: Player {player_id} cannot afford reserve fee ${fee:,.2f}")
            return False, "Insufficient funds for reserve fee"
        
        # Deduct fee
        player.cash_balance -= fee
        
        # Calculate how much currency to buy
        currency_price = market.get_market_price(city.currency_type) or 1.0
        quantity_to_buy = shortfall / currency_price
        
        # Try to buy from market (create market buy order)
        order = market.create_order(
            player_id=player_id,
            order_type=market.OrderType.BUY,
            order_mode=market.OrderMode.MARKET,
            item_type=city.currency_type,
            quantity=quantity_to_buy
        )
        
        # If market order doesn't fill immediately, add directly (bank provides)
        # This ensures the reserve is always met
        current_qty = inventory.get_item_quantity(player_id, city.currency_type)
        required_qty = (get_player_total_value(player_id) * RESERVE_REQUIREMENT_PERCENT) / currency_price
        
        if current_qty < required_qty:
            # Bank provides the shortfall
            bank = db.query(CityBank).filter(CityBank.city_id == city.id).first()
            if bank:
                gap = required_qty - current_qty
                inventory.add_item(player_id, city.currency_type, gap)
                bank.cash_reserves += fee  # Fee goes to bank
        
        db.commit()
        
        print(f"[Cities] Reserve enforced for Player {player_id}: fee ${fee:,.2f}, bought {quantity_to_buy:.2f} {city.currency_type}")
        
        return True, f"Reserve requirement enforced. Fee: ${fee:,.2f}"
        
    except Exception as e:
        db.rollback()
        print(f"[Cities] Error enforcing reserve: {e}")
        return False, str(e)
    finally:
        db.close()


# ==========================
# GOVERNMENT INTERACTIONS
# ==========================
def process_government_grants(current_tick: int):
    """
    Process government grants to all city banks.
    2% of gov reserves divided equally among all city banks.
    Called every 12 hours.
    """
    from auth import Player
    
    db = get_db()
    
    try:
        # Get government account
        government = db.query(Player).filter(Player.id == GOVERNMENT_PLAYER_ID).first()
        if not government or government.cash_balance <= 0:
            return
        
        # Count city banks
        banks = db.query(CityBank).all()
        if not banks:
            return
        
        # Calculate grant amount per bank
        total_grant = government.cash_balance * GOV_GRANT_PERCENT
        grant_per_bank = total_grant / len(banks)
        
        # Distribute grants
        for bank in banks:
            government.cash_balance -= grant_per_bank
            bank.cash_reserves += grant_per_bank
        
        db.commit()
        
        print(f"[Cities] Government grants distributed: ${grant_per_bank:,.2f} to each of {len(banks)} banks")
        
    except Exception as e:
        db.rollback()
        print(f"[Cities] Error processing grants: {e}")
    finally:
        db.close()


def request_government_loan(city_id: int, amount: float, current_tick: int) -> Tuple[Optional[CityBankLoan], str]:
    """
    City bank requests a loan from government.
    Happens automatically if bank becomes insolvent.
    """
    from auth import Player
    
    db = get_db()
    
    try:
        bank = db.query(CityBank).filter(CityBank.city_id == city_id).first()
        if not bank:
            return None, "Bank not found"
        
        # Check loan limit
        active_loans = db.query(CityBankLoan).filter(
            CityBankLoan.city_bank_id == bank.id,
            CityBankLoan.is_active == True
        ).count()
        
        if active_loans >= MAX_CITY_BANK_LOANS:
            return None, f"Bank has reached maximum loans ({MAX_CITY_BANK_LOANS})"
        
        # Get government account
        government = db.query(Player).filter(Player.id == GOVERNMENT_PLAYER_ID).first()
        if not government:
            return None, "Government account not found"
        
        if government.cash_balance < amount:
            return None, "Government has insufficient funds"
        
        # Calculate loan terms
        total_owed = amount * (1 + GOV_LOAN_INTEREST_RATE * GOV_LOAN_INSTALLMENTS)
        installment_amount = total_owed / GOV_LOAN_INSTALLMENTS
        
        # Create loan
        loan = CityBankLoan(
            city_bank_id=bank.id,
            principal=amount,
            total_owed=total_owed,
            installment_amount=installment_amount,
            next_payment_tick=current_tick + GOV_LOAN_INSTALLMENT_INTERVAL_TICKS
        )
        db.add(loan)
        
        # Transfer funds
        government.cash_balance -= amount
        bank.cash_reserves += amount
        
        db.commit()
        
        print(f"[Cities] Loan granted to bank {bank.id}: ${amount:,.2f} principal, ${total_owed:,.2f} total owed")
        
        return loan, "Loan granted"
        
    except Exception as e:
        db.rollback()
        print(f"[Cities] Error requesting loan: {e}")
        return None, str(e)
    finally:
        db.close()


def process_loan_repayments(current_tick: int):
    """
    Process loan installment payments from city banks to government.
    """
    from auth import Player
    
    db = get_db()
    
    try:
        government = db.query(Player).filter(Player.id == GOVERNMENT_PLAYER_ID).first()
        if not government:
            return
        
        # Find loans due for payment
        due_loans = db.query(CityBankLoan).filter(
            CityBankLoan.is_active == True,
            CityBankLoan.next_payment_tick <= current_tick
        ).all()
        
        for loan in due_loans:
            bank = db.query(CityBank).filter(CityBank.id == loan.city_bank_id).first()
            if not bank:
                continue
            
            payment = min(loan.installment_amount, loan.total_owed - loan.amount_paid)
            
            if bank.cash_reserves >= payment:
                # Make payment
                bank.cash_reserves -= payment
                government.cash_balance += payment
                loan.amount_paid += payment
                loan.installments_remaining -= 1
                
                print(f"[Cities] Loan payment: Bank {bank.id} paid ${payment:,.2f} to government")
            else:
                # Bank is insolvent - needs another loan
                shortfall = payment - bank.cash_reserves
                print(f"[Cities] Bank {bank.id} is insolvent, needs ${shortfall:,.2f}")
                
                # Auto-request emergency loan
                request_government_loan(bank.city_id, shortfall * 1.5, current_tick)
            
            # Check if loan is fully paid
            if loan.amount_paid >= loan.total_owed:
                loan.is_active = False
                print(f"[Cities] Loan {loan.id} fully repaid")
            else:
                loan.next_payment_tick = current_tick + GOV_LOAN_INSTALLMENT_INTERVAL_TICKS
        
        db.commit()
        
    except Exception as e:
        db.rollback()
        print(f"[Cities] Error processing loan repayments: {e}")
    finally:
        db.close()


def assume_bank_debt(player_id: int, loan_id: int) -> Tuple[bool, str]:
    """
    City member assumes 1/25th of a bank loan's remaining debt.
    Each member can only do this once per loan.
    """
    from auth import Player
    
    db = get_db()
    
    try:
        membership = db.query(CityMember).filter(CityMember.player_id == player_id).first()
        if not membership:
            return False, "Not a city member"
        
        loan = db.query(CityBankLoan).filter(CityBankLoan.id == loan_id).first()
        if not loan or not loan.is_active:
            return False, "Loan not found or inactive"
        
        bank = db.query(CityBank).filter(CityBank.id == loan.city_bank_id).first()
        if not bank or bank.city_id != membership.city_id:
            return False, "Loan is not from your city's bank"
        
        # Check if already assumed debt from this loan
        existing = db.query(CityDebtAssumption).filter(
            CityDebtAssumption.loan_id == loan_id,
            CityDebtAssumption.player_id == player_id
        ).first()
        if existing:
            return False, "You have already assumed debt from this loan"
        
        # Calculate debt to assume
        remaining_debt = loan.total_owed - loan.amount_paid
        debt_amount = remaining_debt * DEBT_ASSUMPTION_FRACTION
        
        player = db.query(Player).filter(Player.id == player_id).first()
        if not player:
            return False, "Player not found"
        
        if player.cash_balance < debt_amount:
            return False, f"Insufficient funds (need ${debt_amount:,.2f})"
        
        # Assume the debt
        player.cash_balance -= debt_amount
        loan.amount_paid += debt_amount
        
        # Record assumption
        assumption = CityDebtAssumption(
            loan_id=loan_id,
            player_id=player_id,
            amount_assumed=debt_amount
        )
        db.add(assumption)
        
        # Check if loan is now fully paid
        if loan.amount_paid >= loan.total_owed:
            loan.is_active = False
        
        db.commit()
        
        print(f"[Cities] Player {player_id} assumed ${debt_amount:,.2f} of loan {loan_id}")
        
        return True, f"Assumed ${debt_amount:,.2f} of bank debt"
        
    except Exception as e:
        db.rollback()
        print(f"[Cities] Error assuming debt: {e}")
        return False, str(e)
    finally:
        db.close()


# ==========================
# MAYOR CONTROLS
# ==========================
def set_application_fee(mayor_id: int, city_id: int, fee_percent: float) -> Tuple[bool, str]:
    """Mayor sets the application fee percentage."""
    db = get_db()
    
    try:
        city = db.query(City).filter(City.id == city_id).first()
        if not city:
            return False, "City not found"
        
        if city.mayor_id != mayor_id:
            return False, "Only the Mayor can change fees"
        
        if fee_percent < MIN_APPLICATION_FEE_PERCENT or fee_percent > MAX_APPLICATION_FEE_PERCENT:
            return False, f"Fee must be between {MIN_APPLICATION_FEE_PERCENT}% and {MAX_APPLICATION_FEE_PERCENT}%"
        
        city.application_fee_percent = fee_percent
        db.commit()
        
        print(f"[Cities] City {city_id} application fee set to {fee_percent}%")
        
        return True, f"Application fee set to {fee_percent}%"
        
    except Exception as e:
        db.rollback()
        print(f"[Cities] Error setting fee: {e}")
        return False, str(e)
    finally:
        db.close()


def set_relocation_fee(mayor_id: int, city_id: int, fee_percent: float) -> Tuple[bool, str]:
    """Mayor sets the relocation fee percentage."""
    db = get_db()
    
    try:
        city = db.query(City).filter(City.id == city_id).first()
        if not city:
            return False, "City not found"
        
        if city.mayor_id != mayor_id:
            return False, "Only the Mayor can change fees"
        
        if fee_percent < 0 or fee_percent > 50:
            return False, "Fee must be between 0% and 50%"
        
        city.relocation_fee_percent = fee_percent
        db.commit()
        
        print(f"[Cities] City {city_id} relocation fee set to {fee_percent}%")
        
        return True, f"Relocation fee set to {fee_percent}%"
        
    except Exception as e:
        db.rollback()
        print(f"[Cities] Error setting fee: {e}")
        return False, str(e)
    finally:
        db.close()


# ==========================
# PETRODOLLAR TRADE HANDLING
# ==========================
def handle_outsider_trade(buyer_id: int, seller_id: int, item_type: str, quantity: float, price: float) -> Tuple[bool, str]:
    """
    Handle a trade where an outsider is trading with a city member.
    
    PETRODOLLAR SYSTEM:
    When outsider BUYS from city member:
    1. Outsider pays cash → City Bank
    2. Bank BUYS city currency from the open market using that cash
    3. Bank deposits purchased currency to seller's inventory
    4. Customs fee taken (5% - split between bank and gov)
    
    When outsider SELLS to city member:
    - Normal trade, no conversion needed
    
    Returns:
        (should_proceed, message)
        - "handled" in message means cash transfer was done internally
    """
    import market
    import inventory
    from auth import Player
    
    db = get_db()
    
    try:
        # Check if either party is in a city with a currency
        buyer_membership = db.query(CityMember).filter(CityMember.player_id == buyer_id).first()
        seller_membership = db.query(CityMember).filter(CityMember.player_id == seller_id).first()
        
        # If neither is in a city, proceed normally
        if not buyer_membership and not seller_membership:
            return True, "Normal trade"
        
        # If both are in the same city, proceed normally
        if buyer_membership and seller_membership:
            if buyer_membership.city_id == seller_membership.city_id:
                return True, "Same city trade"
        
        # Determine which city's currency applies (seller's city takes precedence)
        city = None
        city_member_id = None
        outsider_id = None
        outsider_is_buyer = False
        
        if seller_membership:
            city = db.query(City).filter(City.id == seller_membership.city_id).first()
            city_member_id = seller_id
            outsider_id = buyer_id
            outsider_is_buyer = True
        elif buyer_membership:
            city = db.query(City).filter(City.id == buyer_membership.city_id).first()
            city_member_id = buyer_id
            outsider_id = seller_id
            outsider_is_buyer = False
        
        if not city or not city.currency_type:
            return True, "City has no currency requirement"
        
        # If outsider is SELLER, no currency conversion needed
        if not outsider_is_buyer:
            return True, "Outsider is seller - normal transfer"
        
        # ========================================
        # PETRODOLLAR: Outsider BUYS from city member
        # ========================================
        trade_value = quantity * price
        
        if trade_value <= 0:
            return True, "Zero value trade"
        
        bank = db.query(CityBank).filter(CityBank.city_id == city.id).first()
        if not bank:
            return True, "No city bank"
        
        # Validate outsider (buyer)
        outsider = db.query(Player).filter(Player.id == outsider_id).first()
        if not outsider:
            return False, "Outsider not found"
        
        if outsider.cash_balance < trade_value:
            return False, "Outsider has insufficient funds"
        
        # Validate seller exists
        seller = db.query(Player).filter(Player.id == seller_id).first()
        if not seller:
            return False, "Seller not found"
        
        # ---- STEP 1: Calculate customs fee (5%) ----
        customs_fee = trade_value * 0.05
        cash_for_currency = trade_value - customs_fee  # What bank uses to buy currency
        
        # ---- STEP 2: Check market for available currency ----
        currency_price = market.get_market_price(city.currency_type)
        if not currency_price or currency_price <= 0:
            # No market price - can't do conversion, fall back to normal trade
            print(f"[Cities] No market price for {city.currency_type}, falling back to normal trade")
            return True, "No currency market price"
        
        currency_needed = cash_for_currency / currency_price
        
        # Check if there's enough currency available on the market
        order_book = market.get_order_book(city.currency_type)
        available_currency = sum(ask[1] for ask in order_book.get("asks", []))  # ask[1] is quantity
        
        if available_currency < currency_needed:
            # Not enough currency on market - check bank reserves
            total_available = available_currency + bank.currency_quantity
            if total_available < currency_needed:
                print(f"[Cities] Insufficient {city.currency_type} on market ({available_currency:.2f}) and bank reserves ({bank.currency_quantity:.2f}) for trade needing {currency_needed:.2f}")
                return False, f"Insufficient {city.currency_type} available for conversion"
        
        # ---- STEP 3: Outsider pays cash to bank ----
        outsider.cash_balance -= trade_value
        bank.cash_reserves += trade_value
        db.commit()  # Commit the cash transfer first
        
        # ---- STEP 4: Bank buys currency from market ----
        # Use a special bank player ID for market orders
        bank_player_id = -(1000 + city.id)
        
        # Give the bank cash to buy with (temporarily in player account)
        # We need to create a pseudo-player balance for the bank to place orders
        bank_pseudo = db.query(Player).filter(Player.id == bank_player_id).first()
        if not bank_pseudo:
            # Bank doesn't have a player record - we'll handle this differently
            # Instead, directly execute purchases from the order book
            pass
        
        # Buy from market by matching against sell orders directly
        currency_acquired = 0.0
        cash_spent = 0.0
        
        # Get fresh order book
        from market import MarketOrder, OrderType, OrderStatus
        sell_orders = db.query(MarketOrder).filter(
            MarketOrder.item_type == city.currency_type,
            MarketOrder.order_type == OrderType.SELL,
            MarketOrder.status.in_([OrderStatus.ACTIVE, OrderStatus.PARTIALLY_FILLED]),
            MarketOrder.price != None
        ).order_by(MarketOrder.price.asc()).all()
        
        for sell_order in sell_orders:
            if currency_acquired >= currency_needed:
                break
            if cash_spent >= cash_for_currency:
                break
            
            available_in_order = sell_order.quantity - sell_order.quantity_filled
            still_need = currency_needed - currency_acquired
            can_afford = (cash_for_currency - cash_spent) / sell_order.price
            
            buy_qty = min(available_in_order, still_need, can_afford)
            
            if buy_qty <= 0:
                continue
            
            cost = buy_qty * sell_order.price
            
            # Execute this purchase
            # 1. Bank pays the seller
            order_seller = db.query(Player).filter(Player.id == sell_order.player_id).first()
            if order_seller:
                bank.cash_reserves -= cost
                order_seller.cash_balance += cost
            
            # 2. Transfer inventory from seller to bank's holding
            inventory.remove_item(sell_order.player_id, city.currency_type, buy_qty)
            
            # 3. Update the sell order
            sell_order.quantity_filled += buy_qty
            if sell_order.quantity_filled >= sell_order.quantity:
                sell_order.status = OrderStatus.FILLED
            else:
                sell_order.status = OrderStatus.PARTIALLY_FILLED
            
            currency_acquired += buy_qty
            cash_spent += cost
            
            print(f"[Cities] Bank bought {buy_qty:.2f} {city.currency_type} @ ${sell_order.price:.2f} from order {sell_order.id}")
        
        # If we didn't get enough from market, use bank's own reserves
        if currency_acquired < currency_needed and bank.currency_quantity > 0:
            from_reserves = min(bank.currency_quantity, currency_needed - currency_acquired)
            bank.currency_quantity -= from_reserves
            currency_acquired += from_reserves
            print(f"[Cities] Bank used {from_reserves:.2f} {city.currency_type} from reserves")
        
        # ---- STEP 5: Deposit currency to seller ----
        if currency_acquired > 0:
            inventory.add_item(seller_id, city.currency_type, currency_acquired)
        
        # ---- STEP 6: Government gets share of customs ----
        government = db.query(Player).filter(Player.id == GOVERNMENT_PLAYER_ID).first()
        if government:
            gov_share = customs_fee * 0.5  # 50% of customs to gov
            bank.cash_reserves -= gov_share
            government.cash_balance += gov_share
        
        db.commit()
        
        print(f"[Cities] PETRODOLLAR: Outsider {outsider_id} paid ${trade_value:,.2f}")
        print(f"[Cities]   → Bank bought {currency_acquired:.2f} {city.currency_type} for ${cash_spent:,.2f}")
        print(f"[Cities]   → Seller {city_member_id} received {currency_acquired:.2f} {city.currency_type}")
        print(f"[Cities]   → Customs: ${customs_fee:,.2f} (bank: ${customs_fee * 0.5:,.2f}, gov: ${customs_fee * 0.5:,.2f})")
        
        return True, "Currency converted - transfer handled"
        
    except Exception as e:
        db.rollback()
        print(f"[Cities] Error handling outsider trade: {e}")
        import traceback
        traceback.print_exc()
        return True, str(e)  # Allow trade to proceed on error
    finally:
        db.close()


# ==========================
# STATISTICS
# ==========================
def get_city_stats(city_id: int) -> dict:
    """Get statistics for a city."""
    db = get_db()
    
    try:
        city = db.query(City).filter(City.id == city_id).first()
        if not city:
            return {}
        
        bank = db.query(CityBank).filter(CityBank.city_id == city_id).first()
        members = db.query(CityMember).filter(CityMember.city_id == city_id).all()
        active_polls = db.query(CityPoll).filter(
            CityPoll.city_id == city_id,
            CityPoll.status == PollStatus.ACTIVE
        ).count()
        
        active_loans = 0
        total_debt = 0.0
        if bank:
            loans = db.query(CityBankLoan).filter(
                CityBankLoan.city_bank_id == bank.id,
                CityBankLoan.is_active == True
            ).all()
            active_loans = len(loans)
            total_debt = sum(l.total_owed - l.amount_paid for l in loans)
        
        return {
            "city_name": city.name,
            "mayor_id": city.mayor_id,
            "member_count": len(members),
            "max_members": MAX_CITY_MEMBERS,
            "currency_type": city.currency_type,
            "application_fee_percent": city.application_fee_percent,
            "relocation_fee_percent": city.relocation_fee_percent,
            "bank_reserves": bank.cash_reserves if bank else 0,
            "bank_currency_qty": bank.currency_quantity if bank else 0,
            "active_polls": active_polls,
            "active_loans": active_loans,
            "total_debt": total_debt,
            "created_at": city.created_at.isoformat() if city.created_at else None
        }
        
    except Exception as e:
        print(f"[Cities] Error getting stats: {e}")
        return {}
    finally:
        db.close()


def get_all_cities() -> List[dict]:
    """Get basic info for all cities."""
    db = get_db()
    
    try:
        cities = db.query(City).all()
        result = []
        
        for city in cities:
            member_count = db.query(CityMember).filter(CityMember.city_id == city.id).count()
            bank = db.query(CityBank).filter(CityBank.city_id == city.id).first()
            
            result.append({
                "id": city.id,
                "name": city.name,
                "mayor_id": city.mayor_id,
                "member_count": member_count,
                "currency_type": city.currency_type,
                "bank_reserves": bank.cash_reserves if bank else 0
            })
        
        return result
        
    except Exception as e:
        print(f"[Cities] Error getting cities: {e}")
        return []
    finally:
        db.close()


# ==========================
# MODULE LIFECYCLE
# ==========================
def initialize():
    """Initialize cities module."""
    print("[Cities] Creating database tables...")
    Base.metadata.create_all(bind=engine)
    
    db = get_db()
    city_count = db.query(City).count()
    db.close()
    
    print(f"[Cities] Current state: {city_count} cities")
    print("[Cities] Module initialized")


async def tick(current_tick: int, now: datetime):
    """
    Cities module tick handler.
    
    Handles:
    - Poll closing
    - Government grants (every 12 hours)
    - Loan repayments
    - Reserve requirement checks
    - Bank currency listing
    """
    db = get_db()
    
    try:
        # Close expired polls
        expired_polls = db.query(CityPoll).filter(
            CityPoll.status == PollStatus.ACTIVE,
            CityPoll.closes_at <= now
        ).all()
        
        for poll in expired_polls:
            close_poll(poll.id)
        
        db.close()
        
        # Government grants every 12 hours
        if current_tick % GOV_GRANT_INTERVAL_TICKS == 0:
            process_government_grants(current_tick)
        
        # Loan repayments
        process_loan_repayments(current_tick)
        
        # Reserve requirement checks every hour (720 ticks)
        if current_tick % 720 == 0:
            db2 = get_db()
            members = db2.query(CityMember).all()
            db2.close()
            
            for member in members:
                meets, shortfall = check_member_reserves(member.player_id)
                if not meets:
                    enforce_reserve_requirement(member.player_id)
        
        # Bank currency listing every 30 minutes (360 ticks)
        if current_tick % 360 == 0:
            db3 = get_db()
            banks = db3.query(CityBank).filter(CityBank.currency_quantity > 0).all()
            db3.close()
            
            for bank in banks:
                bank_list_currency_at_discount(bank.city_id)
        
        # Log stats every 6 hours
        if current_tick % 4320 == 0:
            cities = get_all_cities()
            if cities:
                print(f"[Cities] Stats: {len(cities)} cities active")
        
    except Exception as e:
        print(f"[Cities] Tick error: {e}")
        import traceback
        traceback.print_exc()


# ==========================
# PUBLIC API
# ==========================
__all__ = [
    # Models
    'City',
    'CityBank',
    'CityMember',
    'CityApplication',
    'CityPoll',
    'CityVote',
    'CityBankLoan',
    
    # City creation/management
    'create_city',
    'get_city_by_id',
    'get_city_by_name',
    'get_player_city',
    'get_city_stats',
    'get_all_cities',
    
    # Membership
    'apply_to_city',
    'leave_city',
    'initiate_banishment',
    'get_city_members',
    'is_city_member',
    'is_mayor',
    
    # Voting
    'cast_vote',
    'initiate_currency_change',
    
    # Bank operations
    'pay_production_subsidy',
    'exchange_currency_for_member',
    'get_city_bank',
    
    # Government
    'request_government_loan',
    'assume_bank_debt',
    
    # Mayor controls
    'set_application_fee',
    'set_relocation_fee',
    
    # Trade handling
    'handle_outsider_trade',
    
    # Constants
    'MAX_CITY_MEMBERS',
    'MIN_APPLICATION_FEE_PERCENT',
    'MAX_APPLICATION_FEE_PERCENT',
]
