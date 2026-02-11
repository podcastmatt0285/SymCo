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
from sqlalchemy import create_engine, Column, String, Float, DateTime, Integer, Boolean, func, Index
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
EFFICIENCY_DECAY_PER_TICK = 0.00001 / 60  # 0.00001% per minute = per 60 ticks
STARTING_EFFICIENCY = 100.0  # All land starts at 100% efficiency

# Land hoarding tax - discourages accumulating excessive plots
HOARDING_FREE_PLOTS = 5          # First 5 plots carry no hoarding tax
HOARDING_BASE_TAX_MONTHLY = 5000.0  # $5000/month base rate per excess plot
HOARDING_HOURS_PER_MONTH = 720   # 30 days × 24 hours
GOVERNMENT_PLAYER_ID = 0

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
    "island": {"description": "Isolated landmass", "base_tax": 65.0},
    "district_food": {"description": "Food production zone", "base_tax": 500.0},
    "district_hospital": {"description": "Medical services complex", "base_tax": 800.0},
    "district_industrial": {"description": "Heavy manufacturing zone", "base_tax": 600.0},
    "district_medical": {"description": "Pharmaceutical production zone", "base_tax": 750.0},
    "district_neighborhood": {"description": "Residential services hub", "base_tax": 550.0},
    "district_transport": {"description": "Transportation hub", "base_tax": 700.0},
    "district_utilities": {"description": "Utility infrastructure zone", "base_tax": 650.0},
    "district_zoo": {"description": "Wildlife conservation zone", "base_tax": 600.0}
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

# Business type requirements (what can operate where) - ALL 106 BUSINESS TYPES
BUSINESS_COMPATIBILITY = {
    "bookbindery": {"allowed_terrain": ['prairie', 'forest', 'desert', 'marsh', 'mountain', 'tundra', 'jungle', 'savanna', 'hills', 'island'], "allowed_proximity": ['urban']},
    "dairy_and_fermentation": {"allowed_terrain": ['prairie', 'forest', 'desert', 'mountain'], "allowed_proximity": ['urban', 'road']},
    "solar_plant": {"allowed_terrain": ['desert', 'prairie', 'savanna', 'hills', 'tundra'], "allowed_proximity": ['coastal', 'oasis', 'road', 'remote']},
    "water_facility": {"allowed_terrain": ['marsh', 'prairie', 'jungle'], "allowed_proximity": ['riverside', 'lakeside', 'oasis', 'hot_springs']},
    "free_range_pasture": {"allowed_terrain": ['prairie', 'savanna'], "allowed_proximity": ['riverside', 'oasis', 'remote']},
    "rendering_plant": {"allowed_terrain": ['mountain', 'prairie', 'hills'], "allowed_proximity": ['urban', 'road']},
    "paper_mill": {"allowed_terrain": ['prairie', 'forest', 'jungle'], "allowed_proximity": ['riverside', 'road', 'urban']},
    "plantation": {"allowed_terrain": ['prairie', 'savanna', 'forest'], "allowed_proximity": ['riverside', 'oasis', 'remote']},
    "grocery_store": {"allowed_terrain": ['prairie', 'hills', 'island'], "allowed_proximity": ['urban', 'road']},
    "stationery_store": {"allowed_terrain": ['prairie', 'hills'], "allowed_proximity": ['urban', 'road']},
    "textile_and_tannery": {"allowed_terrain": ['forest', 'savanna', 'mountain', 'jungle', 'hills'], "allowed_proximity": ['urban', 'riverside', 'road']},
    "cotton_fields": {"allowed_terrain": ['prairie', 'savanna', 'hills'], "allowed_proximity": ['riverside', 'oasis', 'road']},
    "lumber_mill": {"allowed_terrain": ['forest', 'jungle', 'mountain'], "allowed_proximity": ['riverside', 'road']},
    "mineral_mine": {"allowed_terrain": ['mountain', 'hills', 'desert'], "allowed_proximity": ['remote', 'road']},
    "refinery": {"allowed_terrain": ['mountain', 'hills', 'prairie', 'desert'], "allowed_proximity": ['urban', 'road']},
    "fastener_factory": {"allowed_terrain": ['prairie', 'hills', 'urban'], "allowed_proximity": ['urban', 'road']},
    "apparel_factory": {"allowed_terrain": ['prairie', 'hills', 'savanna'], "allowed_proximity": ['urban', 'road']},
    "bag_and_luggage": {"allowed_terrain": ['prairie', 'hills', 'savanna'], "allowed_proximity": ['urban', 'road']},
    "cane_plantation": {"allowed_terrain": ['jungle', 'savanna', 'marsh'], "allowed_proximity": ['riverside', 'oasis', 'remote']},
    "bistro": {"allowed_terrain": ['prairie', 'hills', 'island'], "allowed_proximity": ['urban', 'road']},
    "soup_kitchen": {"allowed_terrain": ['prairie', 'hills', 'savanna'], "allowed_proximity": ['urban', 'road']},
    "oil_rig": {"allowed_terrain": ['desert', 'marsh', 'ocean'], "allowed_proximity": ['coastal', 'remote']},
    "grain_farm": {"allowed_terrain": ['prairie', 'savanna', 'hills'], "allowed_proximity": ['riverside', 'road', 'remote']},
    "orchard": {"allowed_terrain": ['prairie', 'hills', 'forest'], "allowed_proximity": ['riverside', 'lakeside', 'road']},
    "vegetable_farm": {"allowed_terrain": ['prairie', 'savanna', 'marsh'], "allowed_proximity": ['riverside', 'oasis', 'road']},
    "vineyard_estate": {"allowed_terrain": ['hills', 'mountain'], "allowed_proximity": ['volcanic', 'riverside', 'lakeside']},
    "coffee_plantation": {"allowed_terrain": ['hills', 'mountain', 'jungle'], "allowed_proximity": ['volcanic', 'riverside']},
    "tea_plantation": {"allowed_terrain": ['hills', 'mountain', 'jungle'], "allowed_proximity": ['riverside', 'volcanic', 'lakeside']},
    "cocoa_plantation": {"allowed_terrain": ['jungle', 'island', 'marsh'], "allowed_proximity": ['riverside', 'coastal']},
    "hop_farm": {"allowed_terrain": ['prairie', 'hills', 'forest'], "allowed_proximity": ['riverside', 'road']},
    "spice_plantation": {"allowed_terrain": ['jungle', 'island', 'marsh'], "allowed_proximity": ['coastal', 'riverside']},
    "agave_plantation": {"allowed_terrain": ['desert', 'savanna'], "allowed_proximity": ['volcanic', 'road', 'remote']},
    "poultry_farm": {"allowed_terrain": ['prairie', 'savanna', 'hills'], "allowed_proximity": ['riverside', 'road', 'remote']},
    "apiary": {"allowed_terrain": ['prairie', 'forest', 'hills', 'savanna'], "allowed_proximity": ['riverside', 'lakeside', 'remote']},
    "salt_works": {"allowed_terrain": ['desert', 'marsh', 'island'], "allowed_proximity": ['coastal', 'lakeside']},
    "flour_mill": {"allowed_terrain": ['prairie', 'hills', 'urban'], "allowed_proximity": ['riverside', 'road', 'urban']},
    "sand_quarry": {"allowed_terrain": ['desert', 'prairie', 'hills'], "allowed_proximity": ['riverside', 'coastal', 'road']},
    "glass_works": {"allowed_terrain": ['desert', 'prairie', 'hills'], "allowed_proximity": ['road', 'urban']},
    "rubber_plant": {"allowed_terrain": ['prairie', 'desert', 'marsh'], "allowed_proximity": ['road', 'urban', 'coastal']},
    "coffee_roastery": {"allowed_terrain": ['urban', 'prairie', 'hills'], "allowed_proximity": ['urban', 'road']},
    "chocolate_factory": {"allowed_terrain": ['urban', 'prairie'], "allowed_proximity": ['urban', 'road']},
    "malting_house": {"allowed_terrain": ['prairie', 'hills', 'urban'], "allowed_proximity": ['riverside', 'road']},
    "gelatin_plant": {"allowed_terrain": ['prairie', 'hills'], "allowed_proximity": ['road', 'urban']},
    "meat_processing": {"allowed_terrain": ['prairie', 'hills', 'mountain'], "allowed_proximity": ['road', 'urban']},
    "cooperage": {"allowed_terrain": ['forest', 'hills', 'prairie'], "allowed_proximity": ['riverside', 'road']},
    "ink_factory": {"allowed_terrain": ['prairie', 'urban', 'hills'], "allowed_proximity": ['urban', 'road']},
    "bedding_factory": {"allowed_terrain": ['prairie', 'urban', 'hills'], "allowed_proximity": ['urban', 'road']},
    "industrial_bakery": {"allowed_terrain": ['urban', 'prairie'], "allowed_proximity": ['urban', 'road']},
    "pastry_kitchen": {"allowed_terrain": ['urban', 'hills'], "allowed_proximity": ['urban']},
    "pie_bakery": {"allowed_terrain": ['urban', 'prairie'], "allowed_proximity": ['urban']},
    "cookie_factory": {"allowed_terrain": ['urban', 'prairie'], "allowed_proximity": ['urban', 'road']},
    "candy_factory": {"allowed_terrain": ['urban', 'prairie'], "allowed_proximity": ['urban', 'road']},
    "chocolate_confectioner": {"allowed_terrain": ['urban'], "allowed_proximity": ['urban']},
    "distillery": {"allowed_terrain": ['prairie', 'hills', 'mountain'], "allowed_proximity": ['riverside', 'urban', 'road']},
    "gin_distillery": {"allowed_terrain": ['hills', 'urban', 'prairie'], "allowed_proximity": ['urban', 'riverside']},
    "tequila_distillery": {"allowed_terrain": ['desert', 'savanna'], "allowed_proximity": ['volcanic', 'road']},
    "winery": {"allowed_terrain": ['hills', 'mountain'], "allowed_proximity": ['volcanic', 'lakeside', 'riverside']},
    "brewery": {"allowed_terrain": ['urban', 'prairie', 'hills'], "allowed_proximity": ['urban', 'riverside']},
    "pharmaceutical_lab": {"allowed_terrain": ['urban'], "allowed_proximity": ['urban']},
    "publishing_house": {"allowed_terrain": ['urban', 'prairie'], "allowed_proximity": ['urban', 'road']},
    "gourmet_kitchen": {"allowed_terrain": ['urban', 'hills'], "allowed_proximity": ['urban']},
    "coffeehouse_production": {"allowed_terrain": ['urban', 'hills'], "allowed_proximity": ['urban']},
    "auto_parts_factory": {"allowed_terrain": ['prairie', 'desert'], "allowed_proximity": ['road', 'urban']},
    "engine_plant": {"allowed_terrain": ['prairie', 'desert'], "allowed_proximity": ['road', 'urban']},
    "chassis_factory": {"allowed_terrain": ['prairie', 'desert'], "allowed_proximity": ['road', 'urban']},
    "auto_assembly": {"allowed_terrain": ['prairie', 'desert'], "allowed_proximity": ['road', 'urban']},
    "luxury_auto_plant": {"allowed_terrain": ['urban', 'prairie'], "allowed_proximity": ['urban']},
    "marine_factory": {"allowed_terrain": ['marsh', 'island'], "allowed_proximity": ['coastal', 'riverside', 'lakeside']},
    "boat_yard": {"allowed_terrain": ['marsh', 'island'], "allowed_proximity": ['coastal', 'riverside', 'lakeside']},
    "ceramics_factory": {"allowed_terrain": ['prairie', 'desert', 'hills'], "allowed_proximity": ['road', 'urban']},
    "lead_mine": {"allowed_terrain": ['mountain', 'hills', 'desert'], "allowed_proximity": ['remote', 'road']},
    "candy_store": {"allowed_terrain": ['urban', 'prairie', 'island'], "allowed_proximity": ['urban', 'coastal']},
    "pharmacy": {"allowed_terrain": ['urban'], "allowed_proximity": ['urban', 'road']},
    "coffeehouse": {"allowed_terrain": ['urban', 'hills', 'island'], "allowed_proximity": ['urban', 'lakeside']},
    "bakery_retail": {"allowed_terrain": ['urban', 'prairie'], "allowed_proximity": ['urban']},
    "wine_bar": {"allowed_terrain": ['urban', 'hills'], "allowed_proximity": ['urban', 'lakeside']},
    "pub": {"allowed_terrain": ['urban', 'prairie'], "allowed_proximity": ['urban', 'road']},
    "auto_dealership": {"allowed_terrain": ['urban', 'prairie'], "allowed_proximity": ['urban', 'road']},
    "luxury_showroom": {"allowed_terrain": ['urban'], "allowed_proximity": ['urban']},
    "marina": {"allowed_terrain": ['marsh', 'island'], "allowed_proximity": ['coastal', 'lakeside', 'riverside']},
    "bookstore": {"allowed_terrain": ['urban', 'prairie'], "allowed_proximity": ['urban', 'road']},
    "butcher_shop": {"allowed_terrain": ['urban', 'prairie'], "allowed_proximity": ['urban', 'road']},
    "gourmet_restaurant": {"allowed_terrain": ['urban', 'hills', 'island'], "allowed_proximity": ['urban', 'lakeside']},
    "home_goods_store": {"allowed_terrain": ['urban', 'prairie'], "allowed_proximity": ['urban', 'road']},
    "farmers_market": {"allowed_terrain": ['prairie', 'hills', 'savanna'], "allowed_proximity": ['road', 'urban', 'remote']},
    "fashion_outlet": {"allowed_terrain": ['prairie', 'hills', 'island'], "allowed_proximity": ['urban', 'road']},
    "aircraft_assembly": {"allowed_terrain": ['district_airport'], "allowed_proximity": []},
    "international_terminal": {"allowed_terrain": ['district_airport'], "allowed_proximity": []},
    "wholesale_distribution": {"allowed_terrain": ['district_mega_mall'], "allowed_proximity": []},
    "premium_shopping_plaza": {"allowed_terrain": ['district_mega_mall'], "allowed_proximity": []},
    "central_kitchen": {"allowed_terrain": ['district_food_court'], "allowed_proximity": []},
    "food_hall": {"allowed_terrain": ['district_food_court'], "allowed_proximity": []},
    "correctional_facility": {"allowed_terrain": ['district_prison_complex'], "allowed_proximity": []},
    "commissary": {"allowed_terrain": ['district_prison_complex'], "allowed_proximity": []},
    "shipping_container_facility": {"allowed_terrain": ['district_seaport'], "allowed_proximity": []},
    "port_trade_center": {"allowed_terrain": ['district_seaport'], "allowed_proximity": []},
    "event_planning_facility": {"allowed_terrain": ['district_convention_center'], "allowed_proximity": []},
    "convention_hall": {"allowed_terrain": ['district_convention_center'], "allowed_proximity": []},
    "defense_manufacturing": {"allowed_terrain": ['district_military_base'], "allowed_proximity": []},
    "military_commissary": {"allowed_terrain": ['district_military_base'], "allowed_proximity": []},
    "research_facility": {"allowed_terrain": ['district_research_campus'], "allowed_proximity": []},
    "university": {"allowed_terrain": ['district_research_campus'], "allowed_proximity": []},
    "data_center_operations": {"allowed_terrain": ['district_tech_park'], "allowed_proximity": []},
    "tech_incubator": {"allowed_terrain": ['district_tech_park'], "allowed_proximity": []},
    "casino_operations": {"allowed_terrain": ['district_entertainment_district'], "allowed_proximity": []},
    "entertainment_complex": {"allowed_terrain": ['district_entertainment_district'], "allowed_proximity": []},
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
    occupied_by_business_id = Column(Integer, index=True, nullable=True)  # NULL if vacant

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    is_starter_plot = Column(Boolean, default=False)  # True if this was the free starting plot

    # Government/Bank flag
    is_government_owned = Column(Boolean, index=True, default=False)  # True if owned by AI gov/bank

    # Composite index for efficiency degradation queries (efficiency > 0)
    __table_args__ = (
        Index('ix_land_plots_efficiency', 'efficiency'),
        Index('ix_land_plots_gov_tax', 'is_government_owned', 'monthly_tax'),
    )


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
    Uses a single bulk SQL UPDATE instead of loading all rows into Python.
    """
    global last_efficiency_update_tick

    db = get_db()

    # Single bulk UPDATE: subtract decay from all plots with efficiency > 0
    # max(0, efficiency - decay) is handled by the CASE expression
    db.query(LandPlot).filter(LandPlot.efficiency > 0).update(
        {LandPlot.efficiency: func.max(0, LandPlot.efficiency - EFFICIENCY_DECAY_PER_TICK)},
        synchronize_session=False
    )

    db.commit()
    db.close()

    last_efficiency_update_tick = current_tick


def collect_monthly_taxes(current_month: int):
    """
    Collect monthly taxes from all land plots.
    Called when month changes.
    Uses bulk SQL operations instead of loading all rows.
    """
    db = get_db()

    # Calculate total tax using SQL SUM (exclude government plots)
    total_tax_collected = db.query(func.sum(LandPlot.monthly_tax)).filter(
        LandPlot.is_government_owned == False
    ).scalar() or 0.0

    # Bulk update last_tax_payment for all non-government plots
    db.query(LandPlot).filter(
        LandPlot.is_government_owned == False
    ).update(
        {LandPlot.last_tax_payment: datetime.utcnow()},
        synchronize_session=False
    )

    db.commit()
    db.close()

    print(f"[Land] Monthly tax collection: ${total_tax_collected:.2f}")


def get_land_stats() -> dict:
    """Get statistics about all land in the game using SQL aggregation."""
    db = get_db()

    total_plots = db.query(LandPlot).count()
    occupied_plots = db.query(LandPlot).filter(LandPlot.occupied_by_business_id != None).count()
    government_plots = db.query(LandPlot).filter(LandPlot.is_government_owned == True).count()

    # Use SQL AVG instead of fetching all rows
    avg_eff_value = db.query(func.avg(LandPlot.efficiency)).scalar() or 100.0

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
# HOARDING TAX SYSTEM
# ==========================

def _hoarding_fib_multiplier(excess_index: int) -> float:
    """
    Calculate the hoarding tax multiplier for a given excess plot index.
    Uses a Fibonacci-based sequence for tiered increases.

    Multipliers: 1.0, 1.1, 1.2, 1.3, 1.5, 1.8, 2.3, 3.1, 4.4, ...
    The offset from 1.0 (×10) follows: 0, 1, 2, 3, 5, 8, 13, 21, 34, ...
    Seeds [0, 1, 2], then each value = sum of previous two.
    """
    if excess_index <= 0:
        return 1.0
    # Build the offset sequence up to the needed index
    seq = [0, 1, 2]
    while len(seq) <= excess_index:
        seq.append(seq[-1] + seq[-2])
    return 1.0 + seq[excess_index] / 10.0


def calculate_player_hoarding_tax(plot_count: int) -> dict:
    """
    Calculate the hoarding tax breakdown for a player with a given number of plots.

    Returns:
        dict with monthly_total, hourly_total, excess_plots, and per-plot breakdown
    """
    if plot_count <= HOARDING_FREE_PLOTS:
        return {
            "excess_plots": 0,
            "monthly_total": 0.0,
            "hourly_total": 0.0,
            "breakdown": []
        }

    excess = plot_count - HOARDING_FREE_PLOTS
    breakdown = []
    monthly_total = 0.0

    for i in range(excess):
        multiplier = _hoarding_fib_multiplier(i)
        monthly = HOARDING_BASE_TAX_MONTHLY * multiplier
        monthly_total += monthly
        breakdown.append({
            "plot_number": HOARDING_FREE_PLOTS + i + 1,
            "multiplier": multiplier,
            "monthly_tax": monthly
        })

    return {
        "excess_plots": excess,
        "monthly_total": monthly_total,
        "hourly_total": monthly_total / HOARDING_HOURS_PER_MONTH,
        "breakdown": breakdown
    }


def collect_hoarding_taxes():
    """
    Collect hourly hoarding tax from players with more than 5 plots.
    Each excess plot carries a $5000/month base tax with Fibonacci-scaled multipliers.
    Paid hourly as a cash sink to discourage land hoarding.
    """
    from auth import Player
    from stats_ux import log_transaction

    db = get_db()

    # Find players with more than HOARDING_FREE_PLOTS plots (exclude government)
    plot_counts = db.query(
        LandPlot.owner_id,
        func.count(LandPlot.id)
    ).filter(
        LandPlot.is_government_owned == False
    ).group_by(LandPlot.owner_id).having(
        func.count(LandPlot.id) > HOARDING_FREE_PLOTS
    ).all()

    total_collected = 0.0

    for owner_id, plot_count in plot_counts:
        if owner_id == GOVERNMENT_PLAYER_ID:
            continue

        tax_info = calculate_player_hoarding_tax(plot_count)
        hourly_payment = tax_info["hourly_total"]

        if hourly_payment <= 0:
            continue

        player = db.query(Player).filter(Player.id == owner_id).first()
        if not player:
            continue

        actual_payment = min(hourly_payment, max(0, player.cash_balance))
        if actual_payment > 0:
            player.cash_balance -= actual_payment
            total_collected += actual_payment

            log_transaction(
                player_id=owner_id,
                transaction_type="tax",
                category="money",
                amount=-actual_payment,
                description=f"Land hoarding fee: {tax_info['excess_plots']} excess plot(s) — ${tax_info['monthly_total']:,.0f}/mo"
            )

    # Pay to government
    if total_collected > 0:
        gov = db.query(Player).filter(Player.id == GOVERNMENT_PLAYER_ID).first()
        if gov:
            gov.cash_balance += total_collected

    db.commit()
    db.close()

    if total_collected > 0:
        print(f"[Land] Hoarding tax collected: ${total_collected:,.2f} from {len(plot_counts)} player(s)")


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
    
    # Collect hoarding taxes every hour (720 ticks = 3600 seconds)
    if current_tick % 720 == 0:
        collect_hoarding_taxes()

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
    'calculate_player_hoarding_tax',
    'TERRAIN_TYPES',
    'PROXIMITY_FEATURES',
    'BUSINESS_COMPATIBILITY',
    'HOARDING_FREE_PLOTS',
    'HOARDING_BASE_TAX_MONTHLY',
    'LandPlot'
]
