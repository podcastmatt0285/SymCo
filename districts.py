"""
districts.py

District management module for the economic simulation.
Districts are special mega-facilities created by combining multiple land plots.

Handles:
- District creation (combining plots into special land)
- Fibonacci progression for plot requirements (5, 8, 13, 21, 34...)
- Cost escalation (1M base * 1.25^merge_count per player)
- Heavy taxation system for high-value facilities
- Plot validation (same terrain, occupied, business removal)
- Database models for districts
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import create_engine, Column, String, Float, DateTime, Integer, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from stats_ux import log_transaction
# ==========================
# DATABASE SETUP
# ==========================
DATABASE_URL = "sqlite:///./symco.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ==========================
# CONSTANTS
# ==========================
BASE_MERGE_COST = 1000000.0  # $1M for first merge
COST_MULTIPLIER = 1.25  # Each subsequent merge costs 1.25x more
DISTRICT_TAX_MULTIPLIER = 15.0  # Districts pay 15x normal land tax
GOVERNMENT_PLAYER_ID = 0  # Tax payments go to player ID 0

# Fibonacci sequence for plot requirements: 5, 8, 13, 21, 34, 55...
FIBONACCI_START = [5, 8]

# District types and their allowed terrain
DISTRICT_TYPES = {
    "aerospace": {
        "name": "Aerospace Complex",
        "description": "Aircraft parts manufacturing and assembly",
        "allowed_terrain": ["prairie", "desert", "savanna"],
        "base_tax": 65000.0,
        "district_terrain": "district_aerospace"
    },
    "education": {
        "name": "Education Campus",
        "description": "Schools, universities, and educational publishing",
        "allowed_terrain": ["prairie", "hills", "forest"],
        "base_tax": 48000.0,
        "district_terrain": "district_education"
    },
    "entertainment": {
        "name": "Entertainment District",
        "description": "Stadiums, concert venues, casinos, and cinemas",
        "allowed_terrain": ["prairie", "island", "hills"],
        "base_tax": 55000.0,
        "district_terrain": "district_entertainment"
    },
    "food": {
        "name": "Food Production Zone",
        "description": "Fast food kitchens, beverage plants, and packaging",
        "allowed_terrain": ["prairie", "hills"],
        "base_tax": 36000.0,
        "district_terrain": "district_food"
    },
    "food_court": {
        "name": "Food Court District",
        "description": "Multi-vendor food service destination",
        "allowed_terrain": ["prairie", "hills"],
        "base_tax": 35000.0,
        "district_terrain": "district_food_court"
    },
    "hospital": {
        "name": "Hospital District",
        "description": "Comprehensive medical care facility",
        "allowed_terrain": ["prairie", "hills", "island"],
        "base_tax": 58000.0,
        "district_terrain": "district_hospital"
    },
    "industrial": {
        "name": "Industrial Zone",
        "description": "Steel mills, foundries, refineries, and heavy manufacturing",
        "allowed_terrain": ["prairie", "mountain", "desert", "hills"],
        "base_tax": 42000.0,
        "district_terrain": "district_industrial"
    },
    "mall": {
        "name": "Shopping Mall District",
        "description": "Premium retail for fashion, electronics, and furnishings",
        "allowed_terrain": ["prairie", "hills", "island"],
        "base_tax": 45000.0,
        "district_terrain": "district_mall"
    },
    "medical": {
        "name": "Medical Production Zone",
        "description": "Pharmaceuticals, medical equipment, and supplies",
        "allowed_terrain": ["prairie", "hills"],
        "base_tax": 54000.0,
        "district_terrain": "district_medical"
    },
    "military": {
        "name": "Military Base",
        "description": "Weapons, vehicles, aircraft, ships, and training",
        "allowed_terrain": ["mountain", "desert", "tundra"],
        "base_tax": 70000.0,
        "district_terrain": "district_military"
    },
    "neighborhood": {
        "name": "Neighborhood Services Hub",
        "description": "Utilities, home maintenance, and security services",
        "allowed_terrain": ["prairie", "hills", "forest"],
        "base_tax": 38000.0,
        "district_terrain": "district_neighborhood"
    },
    "prison": {
        "name": "Prison Complex",
        "description": "Correctional facilities, supplies, and rehabilitation",
        "allowed_terrain": ["desert", "mountain", "tundra"],
        "base_tax": 40000.0,
        "district_terrain": "district_prison"
    },
    "shipyard": {
        "name": "Shipyard District",
        "description": "Marine parts and commercial vessel construction",
        "allowed_terrain": ["marsh", "island"],
        "base_tax": 60000.0,
        "district_terrain": "district_shipyard"
    },
    "tech": {
        "name": "Technology Park",
        "description": "Semiconductor fabs, electronics, and scientific equipment",
        "allowed_terrain": ["prairie", "hills"],
        "base_tax": 52000.0,
        "district_terrain": "district_tech"
    },
    "transport": {
        "name": "Transportation Hub",
        "description": "Airlines, cruises, rail, and freight operations",
        "allowed_terrain": ["prairie", "hills", "desert"],
        "base_tax": 56000.0,
        "district_terrain": "district_transport"
    },
    "utilities": {
        "name": "Utilities Zone",
        "description": "Water treatment and power generation",
        "allowed_terrain": ["prairie", "desert", "marsh"],
        "base_tax": 44000.0,
        "district_terrain": "district_utilities"
    },
    "zoo": {
        "name": "Zoo & Wildlife District",
        "description": "Animal preserves, aquariums, and conservation centers",
        "allowed_terrain": ["prairie", "jungle", "savanna", "forest"],
        "base_tax": 48000.0,
        "district_terrain": "district_zoo"
    }
}

# ==========================
# DATABASE MODELS
# ==========================
class District(Base):
    """
    District model - represents a mega-facility created from merged plots.
    """
    __tablename__ = "districts"
    
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, index=True, nullable=False)
    
    # District attributes
    district_type = Column(String, nullable=False)  # airport, mega_mall, etc.
    terrain_type = Column(String, nullable=False)  # Inherited from source plots
    size = Column(Float, nullable=False)  # Total size from all merged plots
    plots_merged = Column(Integer, nullable=False)  # How many plots were combined
    
    # Tax system (districts are heavily taxed)
    monthly_tax = Column(Float, nullable=False)
    last_tax_payment = Column(DateTime, default=datetime.utcnow)
    
    # Business occupation
    occupied_by_business_id = Column(Integer, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    source_plot_ids = Column(Text, nullable=True)  # Comma-separated IDs of destroyed plots
    

class PlayerDistrictStats(Base):
    """
    Track each player's district merge statistics.
    Used to calculate escalating costs.
    """
    __tablename__ = "player_district_stats"
    
    player_id = Column(Integer, primary_key=True, index=True)
    total_merges_completed = Column(Integer, default=0)  # Total number of merges ever done
    current_merge_cost = Column(Float, default=BASE_MERGE_COST)  # Next merge cost
    last_merge_date = Column(DateTime, nullable=True)


# ==========================
# HELPER FUNCTIONS
# ==========================
def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        return db
    except Exception as e:
        print(f"[Districts] Database error: {e}")
        db.close()
        raise


def calculate_fibonacci_requirement(merge_count: int) -> int:
    """
    Calculate how many plots are required for the nth merge.
    Follows Fibonacci: 5, 8, 13, 21, 34, 55, 89...
    
    Args:
        merge_count: 0-indexed merge number (0 = first merge)
    
    Returns:
        Number of plots required
    """
    if merge_count == 0:
        return FIBONACCI_START[0]  # 5
    elif merge_count == 1:
        return FIBONACCI_START[1]  # 8
    
    # Generate Fibonacci for higher merges
    fib = FIBONACCI_START[:]
    for i in range(2, merge_count + 1):
        fib.append(fib[-1] + fib[-2])
    
    return fib[merge_count]


def get_player_merge_stats(player_id: int) -> PlayerDistrictStats:
    """Get or create player's district merge statistics."""
    db = get_db()
    
    stats = db.query(PlayerDistrictStats).filter(
        PlayerDistrictStats.player_id == player_id
    ).first()
    
    if not stats:
        stats = PlayerDistrictStats(
            player_id=player_id,
            total_merges_completed=0,
            current_merge_cost=BASE_MERGE_COST
        )
        db.add(stats)
        db.commit()
        db.refresh(stats)
    
    db.close()
    return stats


def get_next_merge_cost(player_id: int) -> float:
    """Calculate the cost for this player's next district merge."""
    stats = get_player_merge_stats(player_id)
    return stats.current_merge_cost


def get_plots_required(player_id: int) -> int:
    """Calculate how many plots required for this player's next merge."""
    stats = get_player_merge_stats(player_id)
    return calculate_fibonacci_requirement(stats.total_merges_completed)


def validate_plots_for_merge(plot_ids: List[int], player_id: int) -> tuple[bool, str]:
    """
    Validate that plots can be merged into a district.
    
    Requirements:
    - All plots must be owned by the same player
    - All plots must have the same terrain type
    - All plots must be occupied (have businesses)
    - Correct number of plots (Fibonacci progression)
    
    Returns:
        (success: bool, error_message: str)
    """
    from land import LandPlot
    
    db = get_db()
    
    # Check we have the right number of plots
    required_count = get_plots_required(player_id)
    if len(plot_ids) != required_count:
        db.close()
        return False, f"District requires exactly {required_count} plots (you provided {len(plot_ids)})"
    
    # Get all plots
    plots = db.query(LandPlot).filter(LandPlot.id.in_(plot_ids)).all()
    
    if len(plots) != len(plot_ids):
        db.close()
        return False, "One or more plot IDs are invalid"
    
    # Validate ownership
    for plot in plots:
        if plot.owner_id != player_id:
            db.close()
            return False, f"Plot {plot.id} is not owned by you"
    
    # Validate terrain type (all must match)
    terrain_types = set(plot.terrain_type for plot in plots)
    if len(terrain_types) != 1:
        db.close()
        return False, f"All plots must have the same terrain type (found: {', '.join(terrain_types)})"
    
    # Validate all plots are occupied
    for plot in plots:
        if plot.occupied_by_business_id is None:
            db.close()
            return False, f"Plot {plot.id} must have a business on it (all plots must be occupied)"
    
    db.close()
    return True, "Valid"


def create_district(
    player_id: int,
    district_type: str,
    plot_ids: List[int]
) -> tuple[Optional[District], str]:
    """
    Create a district by merging multiple land plots.
    
    This destroys the original plots and creates a new district.
    Removes all businesses from the plots first.
    
    Args:
        player_id: Owner of the plots
        district_type: Type of district (airport, mega_mall, etc.)
        plot_ids: List of plot IDs to merge
    
    Returns:
        (Created district or None, error message)
    """
    from land import LandPlot
    from auth import Player, transfer_cash
    
    db = get_db()
    
    # Validate district type
    if district_type not in DISTRICT_TYPES:
        db.close()
        return None, f"Invalid district type: {district_type}"
    
    # Validate plots
    valid, error_msg = validate_plots_for_merge(plot_ids, player_id)
    if not valid:
        db.close()
        return None, error_msg
    
    # Get plots
    plots = db.query(LandPlot).filter(LandPlot.id.in_(plot_ids)).all()
    source_terrain = plots[0].terrain_type  # Original terrain (for validation)
    terrain_type = DISTRICT_TYPES[district_type]["district_terrain"]  # District's special terrain
    
    # Check terrain compatibility with district type
    if source_terrain not in DISTRICT_TYPES[district_type]["allowed_terrain"]:
        db.close()
        return None, f"{DISTRICT_TYPES[district_type]['name']} cannot be built on {terrain_type} terrain"
    
    # Get player and check cash
    player = db.query(Player).filter(Player.id == player_id).first()
    merge_cost = get_next_merge_cost(player_id)
    
    if player.cash_balance < merge_cost:
        db.close()
        return None, f"Insufficient funds. District merge costs ${merge_cost:,.2f}"
    
    # Deduct cost and pay government
    player.cash_balance -= merge_cost
    
    # Pay government (player ID 0)
    government = db.query(Player).filter(Player.id == GOVERNMENT_PLAYER_ID).first()
    if government:
        government.cash_balance += merge_cost
    
    # Calculate total size
    total_size = sum(plot.size for plot in plots)
    
    # Calculate district tax (very high)
    base_tax = DISTRICT_TYPES[district_type]["base_tax"]
    monthly_tax = base_tax * total_size * DISTRICT_TAX_MULTIPLIER
    
    # Remove businesses from all plots
    from business import Business
    for plot in plots:
        if plot.occupied_by_business_id:
            # Delete the business
            business = db.query(Business).filter(
                Business.id == plot.occupied_by_business_id
            ).first()
            if business:
                db.delete(business)
                print(f"[Districts] Removed business {business.id} from plot {plot.id}")
    
    # Create the district
    district = District(
        owner_id=player_id,
        district_type=district_type,
        terrain_type=terrain_type,
        size=total_size,
        plots_merged=len(plot_ids),
        monthly_tax=monthly_tax,
        source_plot_ids=",".join(str(id) for id in plot_ids)
    )
    
    db.add(district)
    
    # Delete the original plots
    for plot in plots:
        db.delete(plot)
        print(f"[Districts] Destroyed plot {plot.id}")
    
    # Update player's merge statistics
    stats = db.query(PlayerDistrictStats).filter(
        PlayerDistrictStats.player_id == player_id
    ).first()
    
    if not stats:
        stats = PlayerDistrictStats(player_id=player_id)
        db.add(stats)
    
    stats.total_merges_completed += 1
    stats.current_merge_cost = BASE_MERGE_COST * (COST_MULTIPLIER ** stats.total_merges_completed)
    stats.last_merge_date = datetime.utcnow()
    
    db.commit()
    db.refresh(district)
    db.close()
    
    district_name = DISTRICT_TYPES[district_type]["name"]
    print(f"[Districts] Created {district_name} (ID: {district.id}) for player {player_id}")
    print(f"[Districts] Merged {len(plot_ids)} plots, cost: ${merge_cost:,.2f}, tax: ${monthly_tax:,.2f}/mo")
    
    return district, "Success"


def get_player_districts(player_id: int) -> List[District]:
    """Get all districts owned by a player."""
    db = get_db()
    districts = db.query(District).filter(District.owner_id == player_id).all()
    db.close()
    return districts


def get_vacant_districts(player_id: int) -> List[District]:
    """Get all vacant districts owned by a player."""
    db = get_db()
    districts = db.query(District).filter(
        District.owner_id == player_id,
        District.occupied_by_business_id == None
    ).all()
    db.close()
    return districts


def occupy_district(district_id: int, business_id: int) -> bool:
    """Mark district as occupied by a business."""
    db = get_db()
    
    district = db.query(District).filter(District.id == district_id).first()
    
    if not district:
        db.close()
        return False
    
    if district.occupied_by_business_id is not None:
        db.close()
        return False
    
    district.occupied_by_business_id = business_id
    db.commit()
    db.close()
    
    return True


def vacate_district(district_id: int) -> bool:
    """Mark district as vacant (business removed)."""
    db = get_db()
    
    district = db.query(District).filter(District.id == district_id).first()
    
    if not district:
        db.close()
        return False
    
    district.occupied_by_business_id = None
    db.commit()
    db.close()
    
    return True


def collect_district_taxes(current_month: int):
    """
    Collect monthly taxes from all districts.
    Districts pay heavy taxes to government (player ID 0).
    """
    from auth import Player
    
    db = get_db()
    
    districts = db.query(District).all()
    government = db.query(Player).filter(Player.id == GOVERNMENT_PLAYER_ID).first()
    
    total_tax_collected = 0.0
    
    for district in districts:
        # Get owner
        owner = db.query(Player).filter(Player.id == district.owner_id).first()
        
        if not owner:
            continue
        
        # Check if owner can pay
        if owner.cash_balance >= district.monthly_tax:
            owner.cash_balance -= district.monthly_tax
            if government:
                government.cash_balance += district.monthly_tax
            total_tax_collected += district.monthly_tax
            district.last_tax_payment = datetime.utcnow()
            print(f"[Districts] Player {owner.id} paid ${district.monthly_tax:,.2f} tax for district {district.id}")
        else:
            print(f"[Districts] WARNING: Player {owner.id} cannot afford tax for district {district.id}")
            # TODO: Implement foreclosure/seizure
    
    db.commit()
    db.close()
    
    print(f"[Districts] Monthly district tax collection: ${total_tax_collected:,.2f}")


def get_district_stats() -> dict:
    """Get statistics about all districts in the game."""
    db = get_db()
    
    total_districts = db.query(District).count()
    occupied_districts = db.query(District).filter(
        District.occupied_by_business_id != None
    ).count()
    
    # Count by type
    districts_by_type = {}
    for dtype in DISTRICT_TYPES.keys():
        count = db.query(District).filter(District.district_type == dtype).count()
        if count > 0:
            districts_by_type[dtype] = count
    
    db.close()
    
    return {
        "total_districts": total_districts,
        "occupied_districts": occupied_districts,
        "vacant_districts": total_districts - occupied_districts,
        "districts_by_type": districts_by_type
    }


def get_district(district_id: int) -> Optional[District]:
    """Get a specific district by ID."""
    db = get_db()
    district = db.query(District).filter(District.id == district_id).first()
    db.close()
    return district


# ==========================
# MODULE LIFECYCLE
# ==========================
def initialize():
    """Initialize districts module."""
    print("[Districts] Creating database tables...")
    Base.metadata.create_all(bind=engine)
    
    stats = get_district_stats()
    print(f"[Districts] Current state: {stats['total_districts']} districts")
    if stats['districts_by_type']:
        print(f"[Districts] By type: {stats['districts_by_type']}")
    print("[Districts] Module initialized")


async def tick(current_tick: int, now: datetime):
    """
    Districts module tick handler.
    Handles monthly tax collection.
    """
    global last_tax_month
    
    # Check if month has changed for tax collection
    current_month = now.month
    
    # Initialize last_tax_month if needed
    if 'last_tax_month' not in globals():
        globals()['last_tax_month'] = current_month
    
    if current_month != globals()['last_tax_month']:
        print(f"[Districts] Month changed: {globals()['last_tax_month']} -> {current_month}")
        collect_district_taxes(current_month)
        globals()['last_tax_month'] = current_month
    
    # Log stats every 6 hours (21600 ticks)
    if current_tick % 21600 == 0:
        stats = get_district_stats()
        if stats['total_districts'] > 0:
            print(f"[Districts] Stats: {stats}")


# ==========================
# PUBLIC API
# ==========================
__all__ = [
    'create_district',
    'get_player_districts',
    'get_vacant_districts',
    'occupy_district',
    'vacate_district',
    'get_district_stats',
    'get_next_merge_cost',
    'get_plots_required',
    'validate_plots_for_merge',
    'DISTRICT_TYPES',
    'District'
]
