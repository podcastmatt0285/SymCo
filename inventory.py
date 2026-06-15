"""
inventory.py (Patched)

Inventory management module for the economic simulation.
"""

import json
from typing import Dict, Optional
from sqlalchemy import Column, String, Float, Integer, Index, update as sa_update
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# ==========================
# DATABASE SETUP
# ==========================
from database import engine, SessionLocal
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
    __table_args__ = (
        Index("ix_inv_lookup", "player_id", "item_type"),
    )

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
    # SUM across rows per item_type. A unique (player_id, item_type) constraint
    # is enforced at startup, but we still aggregate defensively so a transient
    # duplicate row can never make this disagree with get_item_quantity().
    db = get_db()
    try:
        inventory: Dict[str, float] = {}
        for item in db.query(InventoryItem).filter(InventoryItem.player_id == player_id).all():
            inventory[item.item_type] = inventory.get(item.item_type, 0.0) + (item.quantity or 0.0)
        return {k: v for k, v in inventory.items() if v > 0}
    finally:
        db.close()

def get_item_info(item_type: str) -> Optional[dict]:
    return ITEM_RECIPES.get(item_type)

def get_item_quantity(player_id: int, item_type: str) -> float:
    """Gets the total quantity of an item for a player (summed across any rows)."""
    from sqlalchemy import func
    db = get_db()
    try:
        total = db.query(
            func.coalesce(func.sum(InventoryItem.quantity), 0.0)
        ).filter(
            InventoryItem.player_id == player_id,
            InventoryItem.item_type == item_type,
        ).scalar()
        return float(total or 0.0)
    finally:
        db.close()

# ==========================
# CORE ACTIONS
# ==========================
def add_item(player_id: int, item_type: str, quantity: float):
    if quantity <= 0: return
    db = get_db()
    try:
        # Atomic upsert: with a unique (player_id, item_type) index, two
        # concurrent add_item calls can no longer both insert a fresh row and
        # create a duplicate (the classic check-then-insert race that left the
        # display and the sell-check reading different rows). ON CONFLICT folds
        # the second write into the existing row's quantity.
        try:
            from sqlalchemy.dialects.postgresql import insert as _pg_insert
            stmt = _pg_insert(InventoryItem.__table__).values(
                player_id=player_id, item_type=item_type, quantity=quantity
            ).on_conflict_do_update(
                index_elements=["player_id", "item_type"],
                set_={"quantity": InventoryItem.__table__.c.quantity + quantity},
            )
            db.execute(stmt)
            db.commit()
            return
        except Exception as _ue:
            # Fallback (e.g. unique index not yet created): read-modify-write.
            db.rollback()
            item = db.query(InventoryItem).filter(
                InventoryItem.player_id == player_id,
                InventoryItem.item_type == item_type,
            ).first()
            if item:
                item.quantity += quantity
            else:
                db.add(InventoryItem(player_id=player_id, item_type=item_type, quantity=quantity))
            db.commit()
    finally:
        db.close()

def remove_item(player_id: int, item_type: str, quantity: float) -> bool:
    """Atomically deduct quantity from inventory.

    Uses a single SQL UPDATE … WHERE quantity >= quantity so concurrent
    requests cannot both pass a Python-level balance check and double-spend
    the same items (the classic lost-update / infinite-money race condition).
    Returns True only if a row was actually updated (sufficient balance found).
    """
    if quantity <= 0:
        return True
    db = get_db()
    try:
        result = db.execute(
            sa_update(InventoryItem)
            .where(InventoryItem.player_id == player_id)
            .where(InventoryItem.item_type == item_type)
            .where(InventoryItem.quantity >= quantity)
            .values(quantity=InventoryItem.quantity - quantity)
        )
        db.commit()
        return result.rowcount > 0
    except Exception:
        db.rollback()
        return False
    finally:
        db.close()

def transfer_item(from_player_id: int, to_player_id: int, item_type: str, quantity: float) -> bool:
    # Atomically deduct from the sender (UPDATE ... WHERE quantity >= quantity),
    # then upsert the credit to the receiver. Reuses the hardened primitives so
    # neither side can oversell or create duplicate rows under concurrency.
    if quantity <= 0:
        return True
    # Reject transfers from a player whose commerce is under an active blockade.
    try:
        from military import is_player_blockaded
        if is_player_blockaded(from_player_id):
            return False  # Blockade in effect — transfer rejected
    except Exception:
        pass  # military module unavailable — proceed normally
    if not remove_item(from_player_id, item_type, quantity):
        return False
    try:
        add_item(to_player_id, item_type, quantity)
        return True
    except Exception:
        # Receiver credit failed — refund the sender so items aren't destroyed.
        add_item(from_player_id, item_type, quantity)
        return False

# ==========================
# MODULE LIFECYCLE
# ==========================
def initialize():
    print("[Inventory] Creating database tables...")
    Base.metadata.create_all(bind=engine)
    from database import run_ddl_migration
    run_ddl_migration(engine, [
        "CREATE INDEX IF NOT EXISTS ix_inv_lookup ON inventory (player_id, item_type)",
        # --- Repair + prevent duplicate inventory rows -----------------------
        # Historically (player_id, item_type) had no unique constraint, so two
        # concurrent inserts (a production tick crediting goods while a trade
        # also wrote) could create duplicate rows for the same item. The page
        # summed one set of rows while the sell-check read another, so the
        # displayed quantity disagreed with what a sell order could actually
        # find. These statements (a) fold every player's duplicate rows into
        # the lowest-id keeper with the summed quantity, (b) delete the now-
        # redundant rows, then (c) add a UNIQUE index so it can never recur
        # (add_item's upsert relies on this index).
        "UPDATE inventory i SET quantity = s.total "
        "FROM (SELECT player_id, item_type, SUM(quantity) AS total, MIN(id) AS keep_id "
        "      FROM inventory GROUP BY player_id, item_type) s "
        "WHERE i.id = s.keep_id",
        "DELETE FROM inventory i "
        "USING (SELECT player_id, item_type, MIN(id) AS keep_id "
        "       FROM inventory GROUP BY player_id, item_type) s "
        "WHERE i.player_id = s.player_id AND i.item_type = s.item_type AND i.id <> s.keep_id",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_inv_player_item ON inventory (player_id, item_type)",
    ])
    load_item_config()
    print("[Inventory] Module initialized")

def tick(current_tick: int, now):
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
