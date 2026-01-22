# business.py (Full Version with Dismantling System and Retail Pricing Patch)
import json
import random
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Integer, Boolean, DateTime, Float
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# Integrated Algebraic Engine
from supplydemand import SupplyDemandEngine

DATABASE_URL = "sqlite:///./symco.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ==========================
# DATABASE MODELS
# ==========================

class Business(Base):
    __tablename__ = "businesses"
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, index=True, nullable=False)
    land_plot_id = Column(Integer, unique=True, nullable=False)
    business_type = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    progress_ticks = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class RetailPrice(Base):
    __tablename__ = "retail_prices"
    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, index=True, nullable=False)
    item_type = Column(String, index=True, nullable=False)
    price = Column(Float, nullable=False)

class BusinessSale(Base):
    """Tracks businesses being dismantled over time."""
    __tablename__ = "business_sales"
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, index=True, nullable=False)
    owner_id = Column(Integer, index=True, nullable=False)
    total_refund = Column(Float, nullable=False)
    refund_per_tick = Column(Float, nullable=False)
    ticks_remaining = Column(Integer, nullable=False)
    ticks_total = Column(Integer, nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)

# ==========================
# CONFIG & LIFECYCLE
# ==========================

BUSINESS_TYPES = {}
DISMANTLING_TICKS = 100 # Number of ticks to dismantle a business

def load_business_config():
    global BUSINESS_TYPES
    try:
        with open("business_types.json", "r") as f:
            BUSINESS_TYPES = json.load(f)
    except Exception as e:
        print(f"[Business] Config load error: {e}")

def initialize():
    Base.metadata.create_all(bind=engine)
    load_business_config()
    print("[Business] Module initialized with production patches and dismantling system")

async def tick(current_tick: int, now: datetime):
    db = SessionLocal()
    try:
        process_business_tick(db)
        process_dismantling_tick(db)
    finally:
        db.close()

# ==========================
# DISMANTLING SYSTEM
# ==========================

def process_dismantling_tick(db):
    """Process one tick of all ongoing business dismantling sales."""
    from auth import Player
    from land import LandPlot
    active_sales = db.query(BusinessSale).all()
    for sale in active_sales:
        if sale.ticks_remaining <= 0:
            continue
        
        # Pay the owner this tick's refund
        player = db.query(Player).filter(Player.id == sale.owner_id).first()
        if player:
            player.cash_balance += sale.refund_per_tick
            sale.ticks_remaining -= 1
        
        # If dismantling is complete
        if sale.ticks_remaining <= 0:
            # Delete the business
            biz = db.query(Business).filter(Business.id == sale.business_id).first()
            if biz:
                # Free up the land
                plot = db.query(LandPlot).filter(LandPlot.id == biz.land_plot_id).first()
                if plot:
                    plot.occupied_by_business_id = None
                db.delete(biz)
                print(f"[Business] Dismantling complete for business {sale.business_id}")
            
            # Delete the sale record
            db.delete(sale)
    db.commit()

def start_business_dismantling(player_id: int, business_id: int) -> bool:
    """
    Begin dismantling a business.
    Returns 50% of startup cost paid over DISMANTLING_TICKS.
    """
    db = SessionLocal()
    try:
        from auth import Player
        biz = db.query(Business).filter(
            Business.id == business_id,
            Business.owner_id == player_id
        ).first()
        
        if not biz:
            db.close()
            return False
            
        existing_sale = db.query(BusinessSale).filter(
            BusinessSale.business_id == business_id
        ).first()
        if existing_sale:
            db.close()
            return False 

        config = BUSINESS_TYPES.get(biz.business_type, {})
        base_cost = config.get("startup_cost", 2500.0)
        
        older_businesses = db.query(Business).filter(
            Business.owner_id == player_id,
            Business.created_at < biz.created_at
        ).count()
        multiplier = max(1, older_businesses)
        total_refund = (base_cost * multiplier) * 0.5
        refund_per_tick = total_refund / DISMANTLING_TICKS
        
        sale = BusinessSale(
            business_id=business_id,
            owner_id=player_id,
            total_refund=total_refund,
            refund_per_tick=refund_per_tick,
            ticks_remaining=DISMANTLING_TICKS,
            ticks_total=DISMANTLING_TICKS
        )
        db.add(sale)
        biz.is_active = False
        db.commit()
        print(f"[Business] Started dismantling business {business_id}, will pay ${total_refund:.2f} over {DISMANTLING_TICKS} ticks")
        db.close()
        return True
    except Exception as e:
        print(f"[Business] Error starting dismantling: {e}")
        db.close()
        return False

def get_dismantling_status(business_id: int):
    """Get dismantling status for a business."""
    db = SessionLocal()
    sale = db.query(BusinessSale).filter(BusinessSale.business_id == business_id).first()
    db.close()
    if not sale:
        return None
    progress_pct = ((sale.ticks_total - sale.ticks_remaining) / sale.ticks_total) * 100
    return {
        "ticks_remaining": sale.ticks_remaining,
        "ticks_total": sale.ticks_total,
        "progress_pct": progress_pct,
        "total_refund": sale.total_refund,
        "refund_per_tick": sale.refund_per_tick,
        "paid_so_far": sale.refund_per_tick * (sale.ticks_total - sale.ticks_remaining)
    }

# ==========================
# CORE SIMULATION LOGIC
# ==========================

def process_business_tick(db):
    from inventory import add_item, remove_item, get_player_inventory
    from land import LandPlot
    from auth import Player
    import market
    
    active_biz = db.query(Business).filter(Business.is_active == True).all()
    for biz in active_biz:
        sale = db.query(BusinessSale).filter(BusinessSale.business_id == biz.id).first()
        if sale:
            continue
            
        config = BUSINESS_TYPES.get(biz.business_type)
        if not config: continue
        
        cycles = config.get("cycles_to_complete", 1)
        if biz.progress_ticks < cycles:
            biz.progress_ticks += 1
            
        if biz.progress_ticks < cycles:
            continue
            
        player = db.query(Player).filter(Player.id == biz.owner_id).first()
        plot = db.query(LandPlot).filter(LandPlot.id == biz.land_plot_id).first()
        if not player or not plot: continue
        
        base_wage = config.get("base_wage_cost", 0.0)
        eff_multiplier = max(0.5, (plot.efficiency / 100.0))
        wage_cost = base_wage / eff_multiplier
        
        if player.cash_balance < wage_cost:
            continue 

        player_inv = get_player_inventory(player.id)
        lines_successfully_produced = 0
        
        # ===== RETAIL CLASS =====
        if config.get("class") == "retail":
            total_revenue = 0.0
            for item, rule in config.get("products", {}).items():
                qty = player_inv.get(item, 0)
                if qty <= 0: continue
                
                price_entry = db.query(RetailPrice).filter(
                    RetailPrice.player_id == player.id,
                    RetailPrice.item_type == item
                ).first()
                
                mkt_p = market.get_market_price(item) or 10.0
                current_p = price_entry.price if price_entry else mkt_p
                
                multiplier = SupplyDemandEngine.get_sales_multiplier(
                    current_p, mkt_p, rule.get("elasticity", 1.0)
                )
                chance = SupplyDemandEngine.calculate_chance_per_tick(
                    rule.get("base_sale_chance", 0.05), multiplier
                )
                
                sold = sum(1 for _ in range(int(qty)) if random.random() < chance)
                if sold > 0:
                    remove_item(player.id, item, sold)
                    total_revenue += sold * current_p
                    lines_successfully_produced += 1
            
            # Always pay wages and reset progress for retail, even if no sales
            # This prevents the business from getting stuck
            player.cash_balance += (total_revenue - wage_cost)
            biz.progress_ticks = 0
            db.commit()
            continue

        # ===== PRODUCTION CLASS =====
        production_lines = config.get("production_lines", [])
        for line in production_lines:
            line_can_run = True
            for req in line.get("inputs", []):
                if player_inv.get(req["item"], 0) < req["quantity"]:
                    line_can_run = False
                    break
            
            if line_can_run:
                for req in line.get("inputs", []):
                    remove_item(player.id, req["item"], req["quantity"])
                    player_inv[req["item"]] -= req["quantity"]
                add_item(player.id, line["output_item"], line["output_qty"])
                lines_successfully_produced += 1
                
        if lines_successfully_produced > 0:
            player.cash_balance -= wage_cost
            biz.progress_ticks = 0
            db.commit()

def create_business(player_id: int, plot_id: int, business_type_key: str):
    """Create a business on a vacant land plot owned by the player."""
    from land import LandPlot
    from auth import Player
    if business_type_key not in BUSINESS_TYPES:
        print(f"[Business] Unknown business type: {business_type_key}")
        return None
        
    config = BUSINESS_TYPES[business_type_key]
    db = SessionLocal()
    try:
        plot = db.query(LandPlot).filter(LandPlot.id == plot_id).first()
        if not plot or plot.owner_id != player_id or plot.occupied_by_business_id is not None:
            print("[Business] Invalid plot, ownership, or occupancy.")
            db.close()
            return None
            
        allowed = config.get("allowed_terrain")
        if allowed and plot.terrain_type not in allowed:
            print(f"[Business] Terrain {plot.terrain_type} not allowed.")
            db.close()
            return None
            
        player = db.query(Player).filter(Player.id == player_id).first()
        if not player:
            db.close()
            return None
        
        base_cost = config.get("startup_cost", 2500.0)
        owned_businesses = db.query(Business).filter(Business.owner_id == player_id).count()
        
        # FIXED: Proper progressive cost increase
        # 0 businesses = 1.0x base cost
        # 1 business = 1.25x base cost
        # 2 businesses = 1.5x base cost
        # 3 businesses = 1.75x base cost, etc.
        multiplier = 1.0 + (owned_businesses * 0.25)
        startup_cost = base_cost * multiplier
        
        print(f"[Business] Startup cost for {business_type_key}: ${base_cost:.2f} × {multiplier:.2f} = ${startup_cost:,.2f}")
        
        if player.cash_balance < startup_cost:
            print(f"[Business] Player {player_id} has insufficient funds (need ${startup_cost:,.2f}, have ${player.cash_balance:,.2f})")
            db.close()
            return None
            
        player.cash_balance -= startup_cost
        business = Business(
            owner_id=player_id,
            land_plot_id=plot.id,
            business_type=business_type_key,
            progress_ticks=0,
            is_active=True
        )
        db.add(business)
        db.commit()
        db.refresh(business)
        plot.occupied_by_business_id = business.id
        db.commit()
        
        print(f"[Business] Created {business_type_key} on plot {plot.id} for Player {player_id} (cost: ${startup_cost:,.2f})")
        return business
    except Exception as e:
        print(f"[Business] Error creating business: {e}")
        import traceback
        traceback.print_exc()
        db.close()
        return None
    finally:
        db.close()

def toggle_business(player_id: int, business_id: int) -> bool:
    """Toggle a business between active and paused."""
    db = SessionLocal()
    try:
        biz = db.query(Business).filter(Business.id == business_id, Business.owner_id == player_id).first()
        if not biz:
            db.close()
            return False
        sale = db.query(BusinessSale).filter(BusinessSale.business_id == business_id).first()
        if sale:
            db.close()
            return False
        biz.is_active = not biz.is_active
        db.commit()
        db.close()
        return True
    except Exception as e:
        print(f"[Business] Error toggling business: {e}")
        db.close()
        return False

# ==========================
# RETAIL PRICING PATCH
# ==========================

def set_retail_price(player_id: int, item_type: str, price: float) -> bool:
    """Set or update the retail price for a specific item for a player."""
    db = SessionLocal()
    try:
        price_entry = db.query(RetailPrice).filter(
            RetailPrice.player_id == player_id,
            RetailPrice.item_type == item_type
        ).first()

        if price_entry:
            price_entry.price = price
        else:
            new_price = RetailPrice(
                player_id=player_id,
                item_type=item_type,
                price=price
            )
            db.add(new_price)
        
        db.commit()
        print(f"[Business] Player {player_id} set retail price for {item_type} to ${price:.2f}")
        return True
    except Exception as e:
        print(f"[Business] Error setting retail price: {e}")
        return False
    finally:
        db.close()

# ==========================
# PUBLIC API
# ==========================

__all__ = [
    'Business',
    'RetailPrice',
    'BusinessSale',
    'BUSINESS_TYPES',
    'create_business',
    'toggle_business',
    'start_business_dismantling',
    'get_dismantling_status',
    'set_retail_price',
    'DISMANTLING_TICKS'
]
