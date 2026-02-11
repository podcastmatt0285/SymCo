"""
executive.py

Executive management module for the economic simulation.
Handles:
- Executive creation with randomized names, stats, and abilities
- Aging, retirement, death lifecycle
- Schooling and upgrades
- Wage payments on configurable pay cycles
- Pension obligations
- Special/legendary executive generation
- Marketplace supply of new, retired, and fired executives
"""

import json
import random
from datetime import datetime
from typing import Optional, List
from sqlalchemy import create_engine, Column, String, Float, DateTime, Integer, Boolean, Text
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

MAX_EXECUTIVES_PER_PLAYER = 8

# Aging: 1 game-year every 1440 ticks (2 real hours at 5s ticks)
TICKS_PER_YEAR = 1440

# Pension duration: 1 game-month = 120 ticks (10 minutes real time)
PENSION_DURATION_TICKS = 120

# Pay cycle definitions (in ticks)
PAY_CYCLES = {
    "tick": 1,
    "minute": 12,       # 60s / 5s = 12 ticks
    "hour": 720,         # 3600s / 5s
    "day": 17280         # 86400s / 5s
}

PAY_CYCLE_LABELS = {
    "tick": "per tick",
    "minute": "per minute",
    "hour": "per hour",
    "day": "per day"
}

# School cost and duration scaling per level
SCHOOL_BASE_COST = 5000.0
SCHOOL_BASE_TICKS = 360  # ~30 min real time

# Marketplace: spawn new exec every N ticks
SPAWN_INTERVAL_TICKS = 180  # every 15 minutes
MAX_MARKETPLACE_SIZE = 20

# Special executive chance
SPECIAL_CHANCE = 0.05  # 5%

# ==========================
# EXECUTIVE JOBS
# ==========================
EXECUTIVE_JOBS = {
    "cfo": {
        "title": "Chief Financial Officer",
        "description": "Improves bank dividend returns and reduces loan interest",
        "effect": "banking"
    },
    "coo": {
        "title": "Chief Operating Officer",
        "description": "Speeds up business production cycles",
        "effect": "business"
    },
    "cto": {
        "title": "Chief Technology Officer",
        "description": "Reduces school costs and duration for all executives",
        "effect": "school"
    },
    "cmo": {
        "title": "Chief Marketing Officer",
        "description": "Boosts retail sales volume and demand",
        "effect": "retail"
    },
    "vp_land": {
        "title": "VP of Land Development",
        "description": "Slows land efficiency decay and reduces land taxes",
        "effect": "land"
    },
    "vp_districts": {
        "title": "VP of District Operations",
        "description": "Boosts district business output and reduces district taxes",
        "effect": "districts"
    },
    "vp_cities": {
        "title": "VP of City Affairs",
        "description": "Increases city fund generation and government grants",
        "effect": "cities"
    },
    "hr_director": {
        "title": "HR Director",
        "description": "Reduces wage costs for all executives and businesses",
        "effect": "wages"
    }
}

# Special abilities for legendary executives
SPECIAL_ABILITIES = {
    "double_efficiency": {
        "name": "Double Efficiency",
        "description": "This executive's effect is doubled"
    },
    "half_wages": {
        "name": "Half Wages",
        "description": "This executive works for half the normal wage"
    },
    "multi_job": {
        "name": "Multi-Talented",
        "description": "Provides a secondary bonus to a random additional job area"
    },
    "fast_learner": {
        "name": "Fast Learner",
        "description": "School upgrades take half the time"
    },
    "pension_free": {
        "name": "Golden Parachute Refusal",
        "description": "Waives pension rights - no pension owed on retirement or firing"
    },
    "eternal_youth": {
        "name": "Eternal Youth",
        "description": "Ages 50% slower than normal"
    },
    "mentor": {
        "name": "Mentor",
        "description": "All other executives gain +1 effective level while this one is employed"
    },
    "market_maker": {
        "name": "Market Maker",
        "description": "Provides a flat $500/tick passive income bonus"
    }
}

# School upgrade options by target level
SCHOOL_UPGRADES = {
    2: [
        {"name": "Efficiency Training", "description": "+10% job effect", "bonus": "efficiency_10"},
        {"name": "Cost Cutting", "description": "-15% wage cost", "bonus": "wage_reduction_15"},
        {"name": "Networking", "description": "+5% to a random secondary job area", "bonus": "secondary_5"}
    ],
    3: [
        {"name": "Advanced Efficiency", "description": "+20% job effect", "bonus": "efficiency_20"},
        {"name": "Lean Management", "description": "-25% wage cost", "bonus": "wage_reduction_25"},
        {"name": "Cross-Training", "description": "+10% to a random secondary job area", "bonus": "secondary_10"}
    ],
    4: [
        {"name": "Expert Efficiency", "description": "+30% job effect", "bonus": "efficiency_30"},
        {"name": "Budget Mastery", "description": "-35% wage cost", "bonus": "wage_reduction_35"},
        {"name": "Leadership", "description": "+15% to all executives' effects", "bonus": "team_boost_15"}
    ],
    5: [
        {"name": "Master Efficiency", "description": "+50% job effect", "bonus": "efficiency_50"},
        {"name": "Automation", "description": "-50% wage cost", "bonus": "wage_reduction_50"},
        {"name": "Synergy", "description": "+25% to a random secondary job area", "bonus": "secondary_25"}
    ],
    6: [
        {"name": "Legendary Focus", "description": "+75% job effect", "bonus": "efficiency_75"},
        {"name": "Volunteer Spirit", "description": "-65% wage cost", "bonus": "wage_reduction_65"},
        {"name": "Visionary", "description": "+20% to all executives' effects", "bonus": "team_boost_20"}
    ],
    7: [
        {"name": "Transcendent Mastery", "description": "+100% job effect", "bonus": "efficiency_100"},
        {"name": "Philanthropist", "description": "-75% wage cost", "bonus": "wage_reduction_75"},
        {"name": "Empire Builder", "description": "+30% to two random secondary areas", "bonus": "dual_secondary_30"}
    ]
}

# ==========================
# DATABASE MODEL
# ==========================
class Executive(Base):
    """Executive employee model."""
    __tablename__ = "executives"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    player_id = Column(Integer, nullable=True, index=True)  # null = on marketplace

    # Stats
    level = Column(Integer, default=1)
    job = Column(String, nullable=False)  # key from EXECUTIVE_JOBS
    wage = Column(Float, default=100.0)
    pay_cycle = Column(String, default="hour")  # tick, minute, hour, day

    # Age lifecycle
    current_age = Column(Integer, default=22)
    retirement_age = Column(Integer, default=65)
    max_age = Column(Integer, default=85)  # death age
    is_retired = Column(Boolean, default=False)
    is_dead = Column(Boolean, default=False)

    # School
    is_in_school = Column(Boolean, default=False)
    school_ticks_remaining = Column(Integer, default=0)
    school_cost_remaining = Column(Float, default=0.0)
    pending_upgrade = Column(Boolean, default=False)  # waiting for player to pick upgrade

    # Pension
    pension_owed = Column(Float, default=0.0)
    pension_ticks_remaining = Column(Integer, default=0)

    # Special
    is_special = Column(Boolean, default=False)
    special_ability = Column(String, nullable=True)  # key from SPECIAL_ABILITIES
    special_title = Column(String, nullable=True)
    special_flavor = Column(Text, nullable=True)

    # Upgrade bonuses (comma-separated list of bonus keys)
    bonuses = Column(Text, default="")

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    hired_at = Column(DateTime, nullable=True)
    fired_at = Column(DateTime, nullable=True)

    # Marketplace status
    on_marketplace = Column(Boolean, default=True)
    marketplace_reason = Column(String, default="new")  # new, fired, retired_available

    # Accumulated tick counters for pay and aging
    pay_tick_accumulator = Column(Integer, default=0)
    age_tick_accumulator = Column(Integer, default=0)


# ==========================
# LOAD NAME DATA
# ==========================
NAME_DATA = {}

def load_names():
    global NAME_DATA
    try:
        with open("executive_names.json", "r") as f:
            NAME_DATA = json.load(f)
    except FileNotFoundError:
        NAME_DATA = {
            "first_names": ["Alex", "Jordan", "Morgan", "Casey", "Riley"],
            "last_names": ["Smith", "Johnson", "Williams", "Brown", "Jones"],
            "special_titles": ["The Visionary"],
            "special_flavor": ["A truly remarkable individual."]
        }


# ==========================
# HELPER FUNCTIONS
# ==========================

def get_db():
    db = SessionLocal()
    return db


def generate_executive(force_special: bool = False) -> dict:
    """Generate random executive stats. Returns a dict of attributes."""
    if not NAME_DATA:
        load_names()

    first_name = random.choice(NAME_DATA["first_names"])
    last_name = random.choice(NAME_DATA["last_names"])
    job = random.choice(list(EXECUTIVE_JOBS.keys()))

    # Age: 18-50, younger ones are cheaper but lower level
    current_age = random.randint(18, 50)

    # Level correlates loosely with age (older = more experienced)
    if current_age < 25:
        level = random.choices([1, 2], weights=[80, 20])[0]
    elif current_age < 35:
        level = random.choices([1, 2, 3], weights=[30, 50, 20])[0]
    elif current_age < 45:
        level = random.choices([2, 3, 4], weights=[30, 45, 25])[0]
    else:
        level = random.choices([3, 4, 5], weights=[35, 40, 25])[0]

    # Retirement age: 55-75
    retirement_age = random.randint(55, 75)

    # Max age (death): retirement_age + 10 to 30
    max_age = retirement_age + random.randint(10, 30)

    # Wage scales with level and pay cycle preference
    pay_cycle = random.choices(
        ["tick", "minute", "hour", "day"],
        weights=[5, 20, 50, 25]
    )[0]

    # Base wage per hour equivalent, then convert
    base_hourly = 50.0 + (level * 40.0) + random.uniform(-10, 30)
    cycle_ticks = PAY_CYCLES[pay_cycle]
    # Convert hourly rate to per-cycle rate
    wage = round(base_hourly * (cycle_ticks / 720.0), 2)

    # Special check
    is_special = force_special or (random.random() < SPECIAL_CHANCE)
    special_ability = None
    special_title = None
    special_flavor = None

    if is_special:
        special_ability = random.choice(list(SPECIAL_ABILITIES.keys()))
        special_title = random.choice(NAME_DATA.get("special_titles", ["The Legend"]))
        special_flavor = random.choice(NAME_DATA.get("special_flavor", ["Truly extraordinary."]))
        # Specials get a level boost
        level = min(level + random.randint(1, 3), 7)
        # And higher wages to match
        base_hourly = 100.0 + (level * 60.0) + random.uniform(0, 50)
        wage = round(base_hourly * (cycle_ticks / 720.0), 2)

    return {
        "first_name": first_name,
        "last_name": last_name,
        "job": job,
        "level": level,
        "current_age": current_age,
        "retirement_age": retirement_age,
        "max_age": max_age,
        "wage": wage,
        "pay_cycle": pay_cycle,
        "is_special": is_special,
        "special_ability": special_ability,
        "special_title": special_title,
        "special_flavor": special_flavor,
        "on_marketplace": True,
        "marketplace_reason": "new"
    }


def create_executive(db, force_special: bool = False) -> Executive:
    """Create a new executive and add to the database."""
    attrs = generate_executive(force_special=force_special)
    exec_obj = Executive(**attrs)
    db.add(exec_obj)
    db.commit()
    db.refresh(exec_obj)
    return exec_obj


def hire_executive(db, player_id: int, executive_id: int) -> dict:
    """Hire an executive from the marketplace."""
    from auth import Player
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        return {"success": False, "error": "Player not found"}

    exec_obj = db.query(Executive).filter(
        Executive.id == executive_id,
        Executive.on_marketplace == True,
        Executive.is_dead == False
    ).first()
    if not exec_obj:
        return {"success": False, "error": "Executive not available"}

    # Check player executive count
    current_count = db.query(Executive).filter(
        Executive.player_id == player_id,
        Executive.is_dead == False
    ).count()
    if current_count >= MAX_EXECUTIVES_PER_PLAYER:
        return {"success": False, "error": f"Maximum {MAX_EXECUTIVES_PER_PLAYER} executives allowed"}

    # Hiring fee = 1 day worth of wages
    hiring_fee = exec_obj.wage * (PAY_CYCLES["day"] / PAY_CYCLES[exec_obj.pay_cycle])
    if player.cash_balance < hiring_fee:
        return {"success": False, "error": f"Insufficient funds. Hiring fee: ${hiring_fee:,.2f}"}

    player.cash_balance -= hiring_fee
    exec_obj.player_id = player_id
    exec_obj.on_marketplace = False
    exec_obj.hired_at = datetime.utcnow()
    exec_obj.fired_at = None
    exec_obj.is_retired = False
    exec_obj.marketplace_reason = None
    db.commit()

    return {
        "success": True,
        "message": f"Hired {exec_obj.first_name} {exec_obj.last_name} as {EXECUTIVE_JOBS[exec_obj.job]['title']}",
        "fee": hiring_fee
    }


def fire_executive(db, player_id: int, executive_id: int) -> dict:
    """Fire an executive. Pension is still owed."""
    exec_obj = db.query(Executive).filter(
        Executive.id == executive_id,
        Executive.player_id == player_id
    ).first()
    if not exec_obj:
        return {"success": False, "error": "Executive not found in your employ"}

    # Calculate pension owed (1 month of wages)
    cycle_ticks = PAY_CYCLES[exec_obj.pay_cycle]
    monthly_wages = exec_obj.wage * (PENSION_DURATION_TICKS / cycle_ticks)

    # Check for pension_free special
    if exec_obj.is_special and exec_obj.special_ability == "pension_free":
        monthly_wages = 0.0

    exec_obj.player_id = None
    exec_obj.on_marketplace = True
    exec_obj.marketplace_reason = "fired"
    exec_obj.fired_at = datetime.utcnow()
    exec_obj.is_in_school = False
    exec_obj.school_ticks_remaining = 0
    exec_obj.school_cost_remaining = 0.0
    exec_obj.pending_upgrade = False
    exec_obj.pension_owed = monthly_wages
    exec_obj.pension_ticks_remaining = PENSION_DURATION_TICKS
    db.commit()

    return {
        "success": True,
        "message": f"Fired {exec_obj.first_name} {exec_obj.last_name}. Pension owed: ${monthly_wages:,.2f}",
        "pension": monthly_wages
    }


def send_to_school(db, player_id: int, executive_id: int) -> dict:
    """Send an executive to school for level upgrade."""
    from auth import Player
    player = db.query(Player).filter(Player.id == player_id).first()
    exec_obj = db.query(Executive).filter(
        Executive.id == executive_id,
        Executive.player_id == player_id
    ).first()

    if not exec_obj:
        return {"success": False, "error": "Executive not found in your employ"}
    if exec_obj.is_in_school:
        return {"success": False, "error": "Executive is already in school"}
    if exec_obj.pending_upgrade:
        return {"success": False, "error": "Executive has a pending upgrade selection"}
    if exec_obj.level >= 7:
        return {"success": False, "error": "Executive is at maximum level"}

    target_level = exec_obj.level + 1

    # Cost and duration scale with target level
    cost = SCHOOL_BASE_COST * target_level
    ticks = SCHOOL_BASE_TICKS * target_level

    # CTO bonus: reduces cost and duration
    cto_bonus = get_player_job_bonus(db, player_id, "school")
    cost *= max(0.2, 1.0 - cto_bonus)
    ticks = int(ticks * max(0.2, 1.0 - cto_bonus))

    # Fast learner special
    if exec_obj.is_special and exec_obj.special_ability == "fast_learner":
        ticks = ticks // 2

    if player.cash_balance < cost:
        return {"success": False, "error": f"Insufficient funds. School costs ${cost:,.2f}"}

    player.cash_balance -= cost
    exec_obj.is_in_school = True
    exec_obj.school_ticks_remaining = ticks
    exec_obj.school_cost_remaining = 0.0  # paid upfront
    db.commit()

    return {
        "success": True,
        "message": f"Sent {exec_obj.first_name} {exec_obj.last_name} to school. Graduating in {ticks} ticks.",
        "cost": cost,
        "ticks": ticks
    }


def apply_school_upgrade(db, player_id: int, executive_id: int, bonus_key: str) -> dict:
    """Apply a selected upgrade after school completion."""
    exec_obj = db.query(Executive).filter(
        Executive.id == executive_id,
        Executive.player_id == player_id
    ).first()
    if not exec_obj:
        return {"success": False, "error": "Executive not found"}
    if not exec_obj.pending_upgrade:
        return {"success": False, "error": "No pending upgrade"}

    target_level = exec_obj.level + 1
    available = SCHOOL_UPGRADES.get(target_level, [])
    valid_keys = [u["bonus"] for u in available]
    if bonus_key not in valid_keys:
        return {"success": False, "error": "Invalid upgrade selection"}

    # Apply the bonus
    existing = exec_obj.bonuses or ""
    if existing:
        exec_obj.bonuses = existing + "," + bonus_key
    else:
        exec_obj.bonuses = bonus_key

    exec_obj.level = target_level
    exec_obj.pending_upgrade = False

    # Wage increases with level
    cycle_ticks = PAY_CYCLES[exec_obj.pay_cycle]
    base_hourly = 50.0 + (exec_obj.level * 40.0)
    if exec_obj.is_special:
        base_hourly = 100.0 + (exec_obj.level * 60.0)
    exec_obj.wage = round(base_hourly * (cycle_ticks / 720.0), 2)

    # Apply wage reduction bonuses
    for b in (exec_obj.bonuses or "").split(","):
        if b.startswith("wage_reduction_"):
            pct = int(b.split("_")[-1])
            exec_obj.wage *= (1.0 - pct / 100.0)
    exec_obj.wage = round(exec_obj.wage, 2)

    db.commit()

    upgrade_info = next((u for u in available if u["bonus"] == bonus_key), {})
    return {
        "success": True,
        "message": f"{exec_obj.first_name} {exec_obj.last_name} upgraded to level {target_level}: {upgrade_info.get('name', bonus_key)}"
    }


def get_player_job_bonus(db, player_id: int, effect: str) -> float:
    """Calculate total bonus for a given job effect from player's executives."""
    executives = db.query(Executive).filter(
        Executive.player_id == player_id,
        Executive.is_dead == False,
        Executive.is_in_school == False,
        Executive.is_retired == False
    ).all()

    total_bonus = 0.0
    mentor_count = 0

    for ex in executives:
        if ex.is_special and ex.special_ability == "mentor":
            mentor_count += 1

    for ex in executives:
        job_info = EXECUTIVE_JOBS.get(ex.job, {})
        if job_info.get("effect") != effect:
            continue

        # Base bonus: 2% per level
        bonus = 0.02 * (ex.level + mentor_count)

        # Apply efficiency bonuses from upgrades
        for b in (ex.bonuses or "").split(","):
            if b.startswith("efficiency_"):
                pct = int(b.split("_")[-1])
                bonus *= (1.0 + pct / 100.0)
            if b.startswith("team_boost_"):
                pass  # handled globally

        # Double efficiency special
        if ex.is_special and ex.special_ability == "double_efficiency":
            bonus *= 2.0

        total_bonus += bonus

    # Team boost bonuses (from any executive's upgrades)
    for ex in executives:
        for b in (ex.bonuses or "").split(","):
            if b.startswith("team_boost_"):
                pct = int(b.split("_")[-1])
                total_bonus *= (1.0 + pct / 100.0)

    return min(total_bonus, 0.95)  # Cap at 95%


def get_player_executives(db, player_id: int) -> List[Executive]:
    """Get all living executives for a player."""
    return db.query(Executive).filter(
        Executive.player_id == player_id,
        Executive.is_dead == False
    ).all()


def get_marketplace_executives(db) -> List[Executive]:
    """Get all executives available on the marketplace."""
    return db.query(Executive).filter(
        Executive.on_marketplace == True,
        Executive.is_dead == False
    ).order_by(Executive.level.desc()).all()


# ==========================
# TICK PROCESSING
# ==========================

async def tick(current_tick: int, now: datetime):
    """Process executive lifecycle each tick."""
    db = get_db()
    try:
        _process_aging(db, current_tick)
        _process_wages(db, current_tick)
        _process_pensions(db, current_tick)
        _process_school(db, current_tick)
        _process_marketplace_spawn(db, current_tick)
        _process_market_maker(db, current_tick)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[Executive Tick {current_tick}] ERROR: {e}")
    finally:
        db.close()


def _process_aging(db, current_tick: int):
    """Age all living executives."""
    living = db.query(Executive).filter(Executive.is_dead == False).all()
    for ex in living:
        ex.age_tick_accumulator += 1

        # Eternal youth special: ages at half speed
        ticks_needed = TICKS_PER_YEAR
        if ex.is_special and ex.special_ability == "eternal_youth":
            ticks_needed = int(TICKS_PER_YEAR * 1.5)

        if ex.age_tick_accumulator >= ticks_needed:
            ex.age_tick_accumulator = 0
            ex.current_age += 1

            # Check for death
            if ex.current_age >= ex.max_age:
                ex.is_dead = True
                ex.on_marketplace = False
                if ex.player_id is not None:
                    ex.player_id = None
                continue

            # Check for retirement
            if ex.current_age >= ex.retirement_age and not ex.is_retired and ex.player_id is not None:
                _retire_executive(db, ex)


def _retire_executive(db, ex: Executive):
    """Handle executive retirement."""
    cycle_ticks = PAY_CYCLES[ex.pay_cycle]
    monthly_wages = ex.wage * (PENSION_DURATION_TICKS / cycle_ticks)

    if ex.is_special and ex.special_ability == "pension_free":
        monthly_wages = 0.0

    ex.is_retired = True
    ex.pension_owed = monthly_wages
    ex.pension_ticks_remaining = PENSION_DURATION_TICKS
    ex.player_id = None
    ex.on_marketplace = True
    ex.marketplace_reason = "retired_available"
    ex.is_in_school = False
    ex.school_ticks_remaining = 0
    ex.pending_upgrade = False


def _process_wages(db, current_tick: int):
    """Pay wages to employed executives."""
    from auth import Player
    employed = db.query(Executive).filter(
        Executive.player_id != None,
        Executive.is_dead == False,
        Executive.is_retired == False
    ).all()

    for ex in employed:
        ex.pay_tick_accumulator += 1
        cycle_ticks = PAY_CYCLES.get(ex.pay_cycle, 720)

        if ex.pay_tick_accumulator >= cycle_ticks:
            ex.pay_tick_accumulator = 0
            wage = ex.wage

            # HR Director bonus: reduce wages
            hr_bonus = get_player_job_bonus(db, ex.player_id, "wages")
            wage *= max(0.2, 1.0 - hr_bonus)

            # Half wages special
            if ex.is_special and ex.special_ability == "half_wages":
                wage *= 0.5

            player = db.query(Player).filter(Player.id == ex.player_id).first()
            if player:
                player.cash_balance -= wage


def _process_pensions(db, current_tick: int):
    """Process pension payments for retired/fired executives."""
    from auth import Player
    pensioners = db.query(Executive).filter(
        Executive.pension_ticks_remaining > 0,
        Executive.pension_owed > 0
    ).all()

    for ex in pensioners:
        # Find the last employer (the one who owes pension)
        # Pension is collected from any player who fired/had them retire
        # We track this as a global cost - pension payments happen each tick
        ex.pension_ticks_remaining -= 1
        payment = ex.pension_owed / (PENSION_DURATION_TICKS)  # even payments

        # Pension is owed by the system (simplification) - but if executive
        # was fired by a specific player, we'd need to track that.
        # For now, pension is handled on firing/retirement by calculating total owed.
        if ex.pension_ticks_remaining <= 0:
            ex.pension_owed = 0.0
            # If still young enough after pension, can re-enter workforce
            if not ex.is_dead and ex.current_age < ex.max_age - 5:
                ex.is_retired = False
                ex.on_marketplace = True
                ex.marketplace_reason = "retired_available"


def _process_school(db, current_tick: int):
    """Process executives in school."""
    in_school = db.query(Executive).filter(
        Executive.is_in_school == True,
        Executive.school_ticks_remaining > 0
    ).all()

    for ex in in_school:
        ex.school_ticks_remaining -= 1
        if ex.school_ticks_remaining <= 0:
            ex.is_in_school = False
            ex.pending_upgrade = True  # Player must select upgrade


def _process_marketplace_spawn(db, current_tick: int):
    """Periodically spawn new executives on the marketplace."""
    if current_tick % SPAWN_INTERVAL_TICKS != 0:
        return

    marketplace_count = db.query(Executive).filter(
        Executive.on_marketplace == True,
        Executive.is_dead == False
    ).count()

    if marketplace_count < MAX_MARKETPLACE_SIZE:
        # Spawn 1-3 new executives
        num_to_spawn = random.randint(1, 3)
        for _ in range(num_to_spawn):
            if marketplace_count + num_to_spawn <= MAX_MARKETPLACE_SIZE:
                create_executive(db)

        # Small chance to spawn a special one
        if random.random() < 0.10:
            create_executive(db, force_special=True)


def _process_market_maker(db, current_tick: int):
    """Process market_maker special ability passive income."""
    from auth import Player
    market_makers = db.query(Executive).filter(
        Executive.player_id != None,
        Executive.is_dead == False,
        Executive.is_retired == False,
        Executive.is_in_school == False,
        Executive.is_special == True,
        Executive.special_ability == "market_maker"
    ).all()

    for ex in market_makers:
        player = db.query(Player).filter(Player.id == ex.player_id).first()
        if player:
            player.cash_balance += 500.0


# ==========================
# INITIALIZATION
# ==========================

def initialize():
    """Initialize executive module - create tables and seed marketplace."""
    Base.metadata.create_all(bind=engine)
    load_names()

    db = get_db()
    try:
        # Seed marketplace if empty
        count = db.query(Executive).filter(Executive.on_marketplace == True, Executive.is_dead == False).count()
        if count == 0:
            for _ in range(10):
                create_executive(db)
            # Always seed at least 1 special
            create_executive(db, force_special=True)
            print(f"  Seeded {11} executives on marketplace")
    finally:
        db.close()
