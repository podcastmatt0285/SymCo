"""
inventory.py (Patched)

Inventory management module for the economic simulation.
"""

import json
from typing import Dict, Optional
from sqlalchemy import create_engine, Column, String, Float, Integer
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# ==========================
# DATABASE SETUP
# ==========================
DATABASE_URL = "sqlite:///./wadsworth.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ==========================
# ITEM CONFIGURATION
# ==========================
ITEM_RECIPES = {}

def load_item_config():
    """Load item types and descriptions from JSON."""
    global ITEM_RECIPES
    try:
        with open("item_types.json", "r") as f:
            ITEM_RECIPES = json.load(f)
        print(f"[Inventory] Loaded {len(ITEM_RECIPES)} item types.")
    except FileNotFoundError:
        print("[Inventory] item_types.json not found!")
        ITEM_RECIPES = {}

# ==========================
# DATABASE MODELS
# ==========================
class InventoryItem(Base):
    __tablename__ = "inventory"
    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, index=True, nullable=False)
    item_type = Column(String, index=True, nullable=False)
    quantity = Column(Float, default=0.0)

# ==========================
# HELPER FUNCTIONS
# ==========================
def get_db():
    db = SessionLocal()
    try:
        return db
    except Exception as e:
        print(f"[Inventory] Database error: {e}")
        db.close()
        raise

def get_player_inventory(player_id: int) -> Dict[str, float]:
    db = get_db()
    items = db.query(InventoryItem).filter(InventoryItem.player_id == player_id).all()
    inventory = {item.item_type: item.quantity for item in items if item.quantity > 0}
    db.close()
    return inventory

def get_item_info(item_type: str) -> Optional[dict]:
    return ITEM_RECIPES.get(item_type)

def get_item_quantity(player_id: int, item_type: str) -> float:
    """Gets the specific quantity of an item for a player."""
    db = get_db()
    item = db.query(InventoryItem).filter(
        InventoryItem.player_id == player_id, 
        InventoryItem.item_type == item_type
    ).first()
    qty = item.quantity if item else 0.0
    db.close()
    return qty

# ==========================
# CORE ACTIONS
# ==========================
def add_item(player_id: int, item_type: str, quantity: float):
    if quantity <= 0: return
    db = get_db()
    item = db.query(InventoryItem).filter(InventoryItem.player_id == player_id, InventoryItem.item_type == item_type).first()
    if item: 
        item.quantity += quantity
    else:
        item = InventoryItem(player_id=player_id, item_type=item_type, quantity=quantity)
        db.add(item)
    db.commit()
    db.close()

def remove_item(player_id: int, item_type: str, quantity: float) -> bool:
    if quantity <= 0: return True
    db = get_db()
    item = db.query(InventoryItem).filter(InventoryItem.player_id == player_id, InventoryItem.item_type == item_type).first()
    if not item or item.quantity < quantity:
        db.close()
        return False
    item.quantity -= quantity
    db.commit()
    db.close()
    return True

def transfer_item(from_player_id: int, to_player_id: int, item_type: str, quantity: float) -> bool:
    db = get_db()
    sender_item = db.query(InventoryItem).filter(InventoryItem.player_id == from_player_id, InventoryItem.item_type == item_type).first()
    if not sender_item or sender_item.quantity < quantity:
        db.close()
        return False
    receiver_item = db.query(InventoryItem).filter(InventoryItem.player_id == to_player_id, InventoryItem.item_type == item_type).first()
    if not receiver_item:
        receiver_item = InventoryItem(player_id=to_player_id, item_type=item_type, quantity=0.0)
        db.add(receiver_item)
    sender_item.quantity -= quantity
    receiver_item.quantity += quantity
    db.commit()
    db.close()
    return True

# ==========================
# MODULE LIFECYCLE
# ==========================
def initialize():
    print("[Inventory] Creating database tables...")
    Base.metadata.create_all(bind=engine)
    load_item_config()
    print("[Inventory] Module initialized")

async def tick(current_tick: int, now):
    pass

__all__ = [
    'add_item', 
    'remove_item', 
    'transfer_item', 
    'get_player_inventory', 
    'get_item_info', 
    'get_item_quantity', 
    'InventoryItem'
]
