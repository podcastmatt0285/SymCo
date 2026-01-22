"""
land.py

Land management module for the economic simulation.
Handles:
- Land plot creation and ownership
- Land efficiency degradation (0.00001% per minute)
- Location ratings (determines business compatibility)
- Land tax system (monthly payments to government)
- Free starter plot for new players
- Database models for land plots
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import create_engine, Column, String, Float, DateTime, Integer, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

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
EFFICIENCY_DECAY_PER_TICK = 0.00001 / 60  # 0.00001% per minute = per 60 ticks
STARTING_EFFICIENCY = 100.0  # All land starts at 100% efficiency

# Terrain types - the base land type
TERRAIN_TYPES = {
    "prairie": {"description": "Flat grassland, good for farming", "base_tax": 50.0},
    "forest": {"description": "Wooded area, good for lumber", "base_tax": 60.0},
    "desert": {"description": "Arid land, challenging conditions", "base_tax": 30.0},
    "marsh": {"description": "Wetland, unique opportunities", "base_tax": 40.0},
    "mountain": {"description": "Rocky highlands, mining potential", "base_tax": 70.0},
    "tundra": {"description": "Cold climate, harsh conditions", "base_tax": 35.0},
    "jungle": {"description": "Dense vegetation, exotic resources", "base_tax": 55.0},
    "savanna": {"description": "Tropical grassland", "base_tax": 45.0},
    "hills": {"description": "Rolling terrain", "base_tax": 52.0},
    "island": {"description": "Isolated landmass", "base_tax": 65.0}
}

# Proximity features - special attributes (can have multiple)
PROXIMITY_FEATURES = {
    "urban": {"description": "Near city center, high demand", "tax_modifier": 2.0},
    "coastal": {"description": "Ocean access, trade benefits", "tax_modifier": 1.5},
    "riverside": {"description": "Fresh water access", "tax_modifier": 1.3},
    "lakeside": {"description": "Lake access, fishing potential", "tax_modifier": 1.2},
    "oasis": {"description": "Desert water source", "tax_modifier": 1.6},
    "hot_springs": {"description": "Geothermal activity", "tax_modifier": 1.4},
    "caves": {"description": "Natural shelter, mining opportunities", "tax_modifier": 1.1},
    "volcanic": {"description": "Volcanic soil", "tax_modifier": 1.3},
    "road": {"description": "Major transportation route", "tax_modifier": 1.25},
    "deposits": {"description": "Oil, minerals, or other extractable resources", "tax_modifier": 1.7},
    "remote": {"description": "Far from civilization", "tax_modifier": 0.7}
}

# Business type requirements (what can operate where)
BUSINESS_COMPATIBILITY = {
    "bookbindery": {"allowed_terrain": ["prairie", "forest", "desert", "marsh", "mountain", "tundra", "jungle", "savanna", "hills", "island"], "allowed_proximity": ["urban"]},
    "solar_plant": {"allowed_terrain": ["desert", "prairie", "savanna", "hills"], "allowed_proximity": ["coastal", "oasis", "road", "remote"]},
    "water_facility": {"allowed_terrain": ["marsh", "prairie", "jungle"], "allowed_proximity": ["riverside", "lakeside", "oasis", "hot_springs"]},
    "free_range_pasture": {"allowed_terrain": ["prairie", "savanna"], "allowed_proximity": ["riverside", "oasis", "remote"]},
    "rendering_plant": {"allowed_terrain": ["mountain", "prairie", "hills"], "allowed_proximity": ["urban", "road"]},
    "paper_mill": {"allowed_terrain": ["prairie", "forest"], "allowed_proximity": ["riverside", "road"]},
    "plantation": {"allowed_terrain": ["prairie", "savanna", "forest"], "allowed_proximity": ["riverside", "oasis", "remote"]},
    "grocery_store": {"allowed_terrain": ["prairie", "hills", "island"], "allowed_proximity": ["urban", "road"]},
    "stationery_store": {"allowed_terrain": ["prairie", "hills"], "allowed_proximity": ["urban", "road"]},
    "textile_and_tannery": {"allowed_terrain": ["forest", "savanna", "mountain", "jungle", "hills"], "allowed_proximity": ["urban", "riverside", "road"]},
}

# ==========================
# DATABASE MODELS
# ==========================
class LandPlot(Base):
    """
    Land plot model.
    Represents a single plot of land in the game.
    """
    __tablename__ = "land_plots"
    
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, index=True, nullable=False)  # Player ID who owns this
    
    # Land attributes
    terrain_type = Column(String, nullable=False)  # prairie, desert, mountain, etc.
    proximity_features = Column(String, nullable=True)  # Comma-separated: "coastal,riverside"
    efficiency = Column(Float, default=STARTING_EFFICIENCY)  # Starts at 100%, degrades over time
    size = Column(Float, default=1.0)  # Size in arbitrary units (1.0 = standard plot)
    
    # Tax system
    monthly_tax = Column(Float, nullable=False)  # Tax amount owed per month
    last_tax_payment = Column(DateTime, default=datetime.utcnow)
    
    # Business occupation
    occupied_by_business_id = Column(Integer, nullable=True)  # NULL if vacant
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    is_starter_plot = Column(Boolean, default=False)  # True if this was the free starting plot
    
    # Government/Bank flag
    is_government_owned = Column(Boolean, default=False)  # True if owned by AI gov/bank


# ==========================
# IN-MEMORY STATE
# ==========================
# Track last tick for efficiency degradation
last_efficiency_update_tick = 0

# Track last month for tax collection
last_tax_month = datetime.utcnow().month


# ==========================
# HELPER FUNCTIONS
# ==========================
def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        return db
    except Exception as e:
        print(f"[Land] Database error: {e}")
        db.close()
        raise


def create_land_plot(
    owner_id: int,
    terrain_type: str = "prairie",
    proximity_features: List[str] = None,
    size: float = 1.0,
    is_starter: bool = False,
    is_government: bool = False
) -> LandPlot:
    """
    Create a new land plot.
    
    Args:
        owner_id: Player ID who will own this plot
        terrain_type: Type of terrain (prairie, desert, mountain, etc.)
        proximity_features: List of proximity features (coastal, riverside, etc.)
        size: Size of the plot (1.0 = standard)
        is_starter: Whether this is a free starter plot
        is_government: Whether this is government-owned
    
    Returns:
        Created LandPlot instance
    """
    db = get_db()
    
    if terrain_type not in TERRAIN_TYPES:
        terrain_type = "prairie"
    
    # Calculate monthly tax based on terrain and proximity
    base_tax = TERRAIN_TYPES[terrain_type]["base_tax"]
    tax_modifier = 1.0
    
    # Apply proximity modifiers
    if proximity_features:
        for feature in proximity_features:
            if feature in PROXIMITY_FEATURES:
                tax_modifier *= PROXIMITY_FEATURES[feature]["tax_modifier"]
    
    monthly_tax = base_tax * size * tax_modifier
    
    # Starter plots have reduced tax
    if is_starter:
        monthly_tax *= 0.5
    
    # Store proximity features as comma-separated string
    proximity_str = ",".join(proximity_features) if proximity_features else None
    
    plot = LandPlot(
        owner_id=owner_id,
        terrain_type=terrain_type,
        proximity_features=proximity_str,
        efficiency=STARTING_EFFICIENCY,
        size=size,
        monthly_tax=monthly_tax,
        is_starter_plot=is_starter,
        is_government_owned=is_government
    )
    
    db.add(plot)
    db.commit()
    db.refresh(plot)
    db.close()
    
    features_str = f" + {proximity_str}" if proximity_str else ""
    print(f"[Land] Created plot {plot.id} for player {owner_id} ({terrain_type}{features_str}, tax: ${monthly_tax:.2f}/mo)")
    
    return plot


def get_player_land(player_id: int) -> List[LandPlot]:
    """Get all land plots owned by a player."""
    db = get_db()
    plots = db.query(LandPlot).filter(LandPlot.owner_id == player_id).all()
    db.close()
    return plots


def get_vacant_land(player_id: int) -> List[LandPlot]:
    """Get all vacant land plots owned by a player."""
    db = get_db()
    plots = db.query(LandPlot).filter(
        LandPlot.owner_id == player_id,
        LandPlot.occupied_by_business_id == None
    ).all()
    db.close()
    return plots


def transfer_land(plot_id: int, new_owner_id: int) -> bool:
    """
    Transfer land ownership.
    Used by market when land is sold.
    
    Returns:
        True if successful, False if plot doesn't exist or is occupied
    """
    db = get_db()
    
    plot = db.query(LandPlot).filter(LandPlot.id == plot_id).first()
    
    if not plot:
        db.close()
        return False
    
    # Cannot transfer occupied land (business must be removed first)
    if plot.occupied_by_business_id is not None:
        db.close()
        return False
    
    plot.owner_id = new_owner_id
    db.commit()
    db.close()
    
    print(f"[Land] Plot {plot_id} transferred to player {new_owner_id}")
    return True


def occupy_land(plot_id: int, business_id: int) -> bool:
    """
    Mark land as occupied by a business.
    
    Returns:
        True if successful, False if already occupied
    """
    db = get_db()
    
    plot = db.query(LandPlot).filter(LandPlot.id == plot_id).first()
    
    if not plot:
        db.close()
        return False
    
    if plot.occupied_by_business_id is not None:
        db.close()
        return False
    
    plot.occupied_by_business_id = business_id
    db.commit()
    db.close()
    
    return True


def vacate_land(plot_id: int) -> bool:
    """
    Mark land as vacant (business removed).
    
    Returns:
        True if successful
    """
    db = get_db()
    
    plot = db.query(LandPlot).filter(LandPlot.id == plot_id).first()
    
    if not plot:
        db.close()
        return False
    
    plot.occupied_by_business_id = None
    db.commit()
    db.close()
    
    return True


def create_starter_plot(player_id: int) -> LandPlot:
    """
    Create the free starter plot for a new player.
    Always prairie with riverside access for easy farming.
    """
    return create_land_plot(
        owner_id=player_id,
        terrain_type="prairie",
        proximity_features=["riverside"],
        size=1.0,
        is_starter=True
    )


def degrade_efficiency(current_tick: int):
    """
    Degrade efficiency of all land plots.
    Called every tick.
    Efficiency decreases by 0.00001% per minute (per 60 ticks).
    """
    global last_efficiency_update_tick
    
    # Only update every tick (continuous degradation)
    db = get_db()
    
    plots = db.query(LandPlot).all()
    
    for plot in plots:
        # Efficiency can never go below 0
        if plot.efficiency > 0:
            plot.efficiency = max(0, plot.efficiency - EFFICIENCY_DECAY_PER_TICK)
    
    if plots:
        db.commit()
    
    db.close()
    
    last_efficiency_update_tick = current_tick


def collect_monthly_taxes(current_month: int):
    """
    Collect monthly taxes from all land plots.
    Called when month changes.
    
    Note: This will integrate with the player cash balance system
    once that's fully connected. For now, just updates last_tax_payment.
    """
    db = get_db()
    
    plots = db.query(LandPlot).all()
    
    total_tax_collected = 0.0
    
    for plot in plots:
        # Skip government-owned land (they don't pay themselves)
        if plot.is_government_owned:
            continue
        
        # TODO: Deduct from player balance
        # For now, just record that tax was "paid"
        plot.last_tax_payment = datetime.utcnow()
        total_tax_collected += plot.monthly_tax
    
    db.commit()
    db.close()
    
    print(f"[Land] Monthly tax collection: ${total_tax_collected:.2f}")
    
    # TODO: Add this amount to government account


def get_land_stats() -> dict:
    """Get statistics about all land in the game."""
    db = get_db()
    
    total_plots = db.query(LandPlot).count()
    occupied_plots = db.query(LandPlot).filter(LandPlot.occupied_by_business_id != None).count()
    government_plots = db.query(LandPlot).filter(LandPlot.is_government_owned == True).count()
    
    avg_efficiency = db.query(LandPlot).all()
    avg_eff_value = sum(p.efficiency for p in avg_efficiency) / len(avg_efficiency) if avg_efficiency else 100.0
    
    db.close()
    
    return {
        "total_plots": total_plots,
        "occupied_plots": occupied_plots,
        "vacant_plots": total_plots - occupied_plots,
        "government_plots": government_plots,
        "player_plots": total_plots - government_plots,
        "average_efficiency": avg_eff_value
    }

def get_land_plot(plot_id: int) -> Optional[LandPlot]:
    db = get_db()
    plot = db.query(LandPlot).filter(LandPlot.id == plot_id).first()
    db.close()
    return plot

# ==========================
# MODULE LIFECYCLE
# ==========================
def initialize():
    """
    Initialize land module.
    Creates database tables if they don't exist.
    """
    print("[Land] Creating database tables...")
    Base.metadata.create_all(bind=engine)
    
    stats = get_land_stats()
    print(f"[Land] Current state: {stats['total_plots']} plots, {stats['average_efficiency']:.2f}% avg efficiency")
    print("[Land] Module initialized")


async def tick(current_tick: int, now: datetime):
    """
    Land module tick handler.
    
    Handles:
    - Efficiency degradation (every tick)
    - Monthly tax collection (when month changes)
    """
    global last_tax_month
    
    # Degrade efficiency every tick
    degrade_efficiency(current_tick)
    
    # Check if month has changed for tax collection
    current_month = now.month
    if current_month != last_tax_month:
        print(f"[Land] Month changed: {last_tax_month} -> {current_month}")
        collect_monthly_taxes(current_month)
        last_tax_month = current_month
    
    # Log stats every hour (3600 ticks)
    if current_tick % 3600 == 0:
        stats = get_land_stats()
        print(f"[Land] Stats: {stats}")


# ==========================
# PUBLIC API
# ==========================
# These functions are exposed for use by other modules

__all__ = [
    'create_land_plot',
    'create_starter_plot',
    'get_player_land',
    'get_vacant_land',
    'transfer_land',
    'occupy_land',
    'vacate_land',
    'get_land_stats',
    'TERRAIN_TYPES',
    'PROXIMITY_FEATURES',
    'BUSINESS_COMPATIBILITY',
    'LandPlot'
]
