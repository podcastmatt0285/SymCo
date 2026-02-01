"""
district_market.py

District Market module for the economic simulation.
Separate marketplace for district-produced items (steel, electronics, etc.)

Handles:
- Player-driven buy and sell orders for district items
- Order matching engine (tick-driven)
- Market orders vs limit orders
- Order book display
- Price discovery
- Trade execution
- Market statistics
- District market ticker
"""

import json
from datetime import datetime, timedelta
from typing import Optional, List
from enum import Enum
from sqlalchemy import create_engine, Column, String, Float, DateTime, Integer
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
# DISTRICT ITEM CONFIGURATION
# ==========================
DISTRICT_ITEMS = {}

def load_district_items():
    """Load district item types from JSON."""
    global DISTRICT_ITEMS
    try:
        with open("district_items.json", "r") as f:
            DISTRICT_ITEMS = json.load(f)
        print(f"[DistrictMarket] Loaded {len(DISTRICT_ITEMS)} district item types.")
    except FileNotFoundError:
        print("[DistrictMarket] district_items.json not found!")
        DISTRICT_ITEMS = {}

def get_district_item_info(item_type: str) -> Optional[dict]:
    """Get info about a district item."""
    return DISTRICT_ITEMS.get(item_type)

# ==========================
# ENUMS
# ==========================
class OrderType(str, Enum):
    BUY = "buy"
    SELL = "sell"

class OrderMode(str, Enum):
    LIMIT = "limit"
    MARKET = "market"

class OrderStatus(str, Enum):
    ACTIVE = "active"
    FILLED = "filled"
    PARTIALLY_FILLED = "partial"
    CANCELLED = "cancelled"
    EXPIRED = "expired"

# ==========================
# DATABASE MODELS
# ==========================
class DistrictMarketOrder(Base):
    """District market order model."""
    __tablename__ = "district_market_orders"
    
    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, index=True, nullable=False)
    order_type = Column(String, nullable=False)
    order_mode = Column(String, nullable=False)
    item_type = Column(String, index=True, nullable=False)
    price = Column(Float, nullable=True)
    quantity = Column(Float, nullable=False)
    quantity_filled = Column(Float, default=0.0)
    status = Column(String, default=OrderStatus.ACTIVE)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    filled_at = Column(DateTime, nullable=True)

class DistrictTrade(Base):
    """District trade history model."""
    __tablename__ = "district_trades"
    
    id = Column(Integer, primary_key=True, index=True)
    buyer_id = Column(Integer, index=True, nullable=False)
    seller_id = Column(Integer, index=True, nullable=False)
    buy_order_id = Column(Integer, nullable=False)
    sell_order_id = Column(Integer, nullable=False)
    item_type = Column(String, index=True, nullable=False)
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    executed_at = Column(DateTime, default=datetime.utcnow, index=True)

# ==========================
# HELPER FUNCTIONS
# ==========================
def get_db():
    db = SessionLocal()
    try:
        return db
    except Exception as e:
        print(f"[DistrictMarket] Database error: {e}")
        db.close()
        raise

# ==========================
# TICKER GENERATION
# ==========================
def get_district_ticker_html() -> str:
    """Generate HTML for district market ticker with slower scroll."""
    ticker_items = []
    
    # Get prices for all district items (limit to avoid massive ticker)
    sampled_items = list(DISTRICT_ITEMS.keys())[:50]  # Sample first 50
    
    for item in sampled_items:
        price = get_market_price(item)
        display_name = item.replace('_', ' ').upper()
        if price:
            ticker_items.append(f"{display_name}: ${price:,.2f}")
        else:
            ticker_items.append(f"{display_name}: --")
    
    ticker_text = " ⬥ ".join(ticker_items) if ticker_items else "DISTRICT MARKET OPENING..."
    
    # Duplicate for seamless loop
    ticker_content = f"{ticker_text} ⬥ {ticker_text}"
    
    return f'''
    <div class="district-ticker" style="
        position: fixed;
        bottom: 28px;
        left: 0;
        right: 0;
        background: #0f172a;
        border-top: 1px solid #334155;
        padding: 5px 0;
        font-size: 0.8rem;
        color: #f59e0b;
        white-space: nowrap;
        overflow: hidden;
        z-index: 99;
    ">
        <div style="
            display: inline-block;
            animation: district-scroll 120s linear infinite;
        ">
            {ticker_content}
        </div>
    </div>
    <style>
        @keyframes district-scroll {{
            0% {{ transform: translateX(0); }}
            100% {{ transform: translateX(-50%); }}
        }}
    </style>
    '''

# ==========================
# ORDER PLACEMENT
# ==========================
def create_order(
    player_id: int,
    order_type: OrderType,
    order_mode: OrderMode,
    item_type: str,
    quantity: float,
    price: Optional[float] = None
) -> Optional[DistrictMarketOrder]:
    """Create a new district market order."""
    db = get_db()
    
    # Basic validation
    if order_mode == OrderMode.LIMIT and price is None:
        db.close()
        return None
    if quantity <= 0:
        db.close()
        return None
    
    # Verify item exists in district items
    if item_type not in DISTRICT_ITEMS:
        print(f"[DistrictMarket] Unknown district item: {item_type}")
        db.close()
        return None

    # Cash validation for buy orders
    if order_type == OrderType.BUY:
        from auth import Player
        player = db.query(Player).filter(Player.id == player_id).first()
        if not player or player.cash_balance < (quantity * (price or 0)):
            print(f"[DistrictMarket] Player {player_id} has insufficient funds for buy order")
            db.close()
            return None
    
    # Inventory validation for sell orders
    if order_type == OrderType.SELL:
        try:
            import inventory
            current_quantity = inventory.get_item_quantity(player_id, item_type)
            if current_quantity < quantity:
                print(f"[DistrictMarket] Player {player_id} has insufficient inventory (has {current_quantity}, needs {quantity} {item_type})")
                db.close()
                return None
        except Exception as e:
            print(f"[DistrictMarket] Failed to verify inventory: {e}")
            db.close()
            return None
    
    # Create order
    order = DistrictMarketOrder(
        player_id=player_id,
        order_type=order_type.value,
        order_mode=order_mode.value,
        item_type=item_type,
        quantity=quantity,
        price=price if order_mode == OrderMode.LIMIT else None,
        status=OrderStatus.ACTIVE
    )
    
    db.add(order)
    db.commit()
    db.refresh(order)
    
    print(f"[DistrictMarket] Order {order.id} created: {order_type.value} {quantity} {item_type}" + 
          (f" @ ${price}" if price else " at market price"))
    
    match_order(db, order)
    db.close()
    return order

# ==========================
# ORDER MATCHING ENGINE
# ==========================
def match_order(db, order: DistrictMarketOrder) -> bool:
    """Match an order against the book."""
    if order.status not in [OrderStatus.ACTIVE, OrderStatus.PARTIALLY_FILLED]:
        return False
    
    matched_any = False
    remaining_qty = order.quantity - order.quantity_filled
    
    if order.order_type == OrderType.BUY:
        potential_matches = db.query(DistrictMarketOrder).filter(
            DistrictMarketOrder.order_type == OrderType.SELL,
            DistrictMarketOrder.status.in_([OrderStatus.ACTIVE, OrderStatus.PARTIALLY_FILLED]),
            DistrictMarketOrder.item_type == order.item_type
        ).order_by(DistrictMarketOrder.price.asc()).all()
    else:
        potential_matches = db.query(DistrictMarketOrder).filter(
            DistrictMarketOrder.order_type == OrderType.BUY,
            DistrictMarketOrder.status.in_([OrderStatus.ACTIVE, OrderStatus.PARTIALLY_FILLED]),
            DistrictMarketOrder.item_type == order.item_type
        ).order_by(DistrictMarketOrder.price.desc()).all()
    
    for match in potential_matches:
        if remaining_qty <= 0:
            break
        
        # Price check
        if order.order_mode == OrderMode.LIMIT:
            if order.order_type == OrderType.BUY and (match.price is None or match.price > order.price):
                continue
            if order.order_type == OrderType.SELL and (match.price is None or match.price < order.price):
                continue
        
        # Calculate fill quantity
        match_remaining = match.quantity - match.quantity_filled
        fill_qty = min(remaining_qty, match_remaining)
        
        if fill_qty <= 0:
            continue
        
        # Determine execution price
        exec_price = match.price or order.price or 0
        
        # Execute the trade
        if order.order_type == OrderType.BUY:
            execute_trade(db, order, match, fill_qty, exec_price)
        else:
            execute_trade(db, match, order, fill_qty, exec_price)
        
        # Update order states
        order.quantity_filled += fill_qty
        match.quantity_filled += fill_qty
        remaining_qty -= fill_qty
        matched_any = True
        
        # Update statuses
        if order.quantity_filled >= order.quantity:
            order.status = OrderStatus.FILLED
            order.filled_at = datetime.utcnow()
        elif order.quantity_filled > 0:
            order.status = OrderStatus.PARTIALLY_FILLED
        
        if match.quantity_filled >= match.quantity:
            match.status = OrderStatus.FILLED
            match.filled_at = datetime.utcnow()
        elif match.quantity_filled > 0:
            match.status = OrderStatus.PARTIALLY_FILLED
    
    db.commit()
    return matched_any

def execute_trade(db, buy_order: DistrictMarketOrder, sell_order: DistrictMarketOrder, quantity: float, price: float):
    """Execute a district trade between two orders."""
    total_cost = quantity * price
    
    # Create trade record
    trade = DistrictTrade(
        buyer_id=buy_order.player_id,
        seller_id=sell_order.player_id,
        buy_order_id=buy_order.id,
        sell_order_id=sell_order.id,
        item_type=buy_order.item_type,
        quantity=quantity,
        price=price
    )
    db.add(trade)
    
    print(f"[DistrictMarket] Trade: {quantity} {buy_order.item_type} @ ${price:.2f} "
          f"(Player {sell_order.player_id} -> Player {buy_order.player_id})")
    
    # Transfer cash
    try:
        from auth import transfer_cash
        success = transfer_cash(buy_order.player_id, sell_order.player_id, total_cost)
        if not success:
            print(f"[DistrictMarket] Cash transfer failed!")
            db.rollback()
            return
    except ImportError:
        print("[DistrictMarket] ERROR: Auth module not available")
        db.rollback()
        return
    
    # Transfer inventory
    try:
        import inventory
        success = inventory.transfer_item(
            sell_order.player_id,
            buy_order.player_id,
            buy_order.item_type,
            quantity
        )
        if not success:
            print(f"[DistrictMarket] Inventory transfer failed!")
            db.rollback()
            return
    except Exception as e:
        print(f"[DistrictMarket] Inventory error: {e}")
        db.rollback()
        return
    
    # Log transactions
    try:
        from stats_ux import log_transaction
        
        log_transaction(
            buy_order.player_id,
            "resource_gain",
            "resource",
            quantity,
            f"District market buy: {buy_order.item_type}",
            buy_order.item_type
        )
        log_transaction(
            buy_order.player_id,
            "cash_out",
            "money",
            -total_cost,
            f"District market purchase: {quantity} {buy_order.item_type}",
            buy_order.item_type
        )
        log_transaction(
            sell_order.player_id,
            "cash_in",
            "money",
            total_cost,
            f"District market sale: {quantity} {buy_order.item_type}",
            buy_order.item_type
        )
        log_transaction(
            sell_order.player_id,
            "resource_loss",
            "resource",
            -quantity,
            f"District market sale: {buy_order.item_type}",
            buy_order.item_type
        )
    except:
        pass  # Stats logging is optional
    
    db.commit()

# ==========================
# MARKET DATA FUNCTIONS
# ==========================
def get_order_book(item_type: str) -> dict:
    """Returns active bids and asks with player information."""
    db = get_db()
    
    buy_orders = db.query(DistrictMarketOrder).filter(
        DistrictMarketOrder.item_type == item_type,
        DistrictMarketOrder.order_type == OrderType.BUY,
        DistrictMarketOrder.status.in_([OrderStatus.ACTIVE, OrderStatus.PARTIALLY_FILLED])
    ).order_by(DistrictMarketOrder.price.desc()).all()
    
    sell_orders = db.query(DistrictMarketOrder).filter(
        DistrictMarketOrder.item_type == item_type,
        DistrictMarketOrder.order_type == OrderType.SELL,
        DistrictMarketOrder.status.in_([OrderStatus.ACTIVE, OrderStatus.PARTIALLY_FILLED])
    ).order_by(DistrictMarketOrder.price.asc()).all()
    
    from auth import Player
    
    bids = []
    for o in buy_orders:
        if o.price:
            player = db.query(Player).filter(Player.id == o.player_id).first()
            player_name = player.business_name if player else f"Player {o.player_id}"
            bids.append((o.price, o.quantity - o.quantity_filled, o.id, player_name, o.player_id))
    
    asks = []
    for o in sell_orders:
        if o.price:
            player = db.query(Player).filter(Player.id == o.player_id).first()
            player_name = player.business_name if player else f"Player {o.player_id}"
            asks.append((o.price, o.quantity - o.quantity_filled, o.id, player_name, o.player_id))
    
    db.close()
    return {"bids": bids, "asks": asks}

def get_market_price(item_type: str) -> Optional[float]:
    """Get market price from last trade or midpoint."""
    db = get_db()
    
    last_trade = db.query(DistrictTrade).filter(
        DistrictTrade.item_type == item_type
    ).order_by(DistrictTrade.executed_at.desc()).first()
    
    if last_trade:
        db.close()
        return last_trade.price
    
    best_bid = db.query(DistrictMarketOrder).filter(
        DistrictMarketOrder.item_type == item_type,
        DistrictMarketOrder.order_type == OrderType.BUY,
        DistrictMarketOrder.status == OrderStatus.ACTIVE,
        DistrictMarketOrder.price != None
    ).order_by(DistrictMarketOrder.price.desc()).first()
    
    best_ask = db.query(DistrictMarketOrder).filter(
        DistrictMarketOrder.item_type == item_type,
        DistrictMarketOrder.order_type == OrderType.SELL,
        DistrictMarketOrder.status == OrderStatus.ACTIVE,
        DistrictMarketOrder.price != None
    ).order_by(DistrictMarketOrder.price.asc()).first()
    
    db.close()
    
    if best_bid and best_ask:
        return (best_bid.price + best_ask.price) / 2
    return best_bid.price if best_bid else best_ask.price if best_ask else None

def cancel_order(order_id: int, player_id: int) -> bool:
    """Cancel a district market order."""
    db = get_db()
    order = db.query(DistrictMarketOrder).filter(
        DistrictMarketOrder.id == order_id,
        DistrictMarketOrder.player_id == player_id,
        DistrictMarketOrder.status == OrderStatus.ACTIVE
    ).first()
    
    if not order:
        db.close()
        return False
    
    order.status = OrderStatus.CANCELLED
    db.commit()
    db.close()
    return True

def get_market_stats() -> dict:
    """Get district market statistics."""
    db = get_db()
    
    yesterday = datetime.utcnow() - timedelta(days=1)
    recent_trades = db.query(DistrictTrade).filter(
        DistrictTrade.executed_at >= yesterday
    ).all()
    
    volume = sum(t.quantity * t.price for t in recent_trades)
    
    stats = {
        "total_orders": db.query(DistrictMarketOrder).count(),
        "active_orders": db.query(DistrictMarketOrder).filter(
            DistrictMarketOrder.status == OrderStatus.ACTIVE
        ).count(),
        "total_trades": db.query(DistrictTrade).count(),
        "volume_24h": volume
    }
    
    db.close()
    return stats

def get_player_orders(player_id: int) -> List[DistrictMarketOrder]:
    """Get all active orders for a player."""
    db = get_db()
    orders = db.query(DistrictMarketOrder).filter(
        DistrictMarketOrder.player_id == player_id,
        DistrictMarketOrder.status.in_([OrderStatus.ACTIVE, OrderStatus.PARTIALLY_FILLED])
    ).order_by(DistrictMarketOrder.created_at.desc()).all()
    db.close()
    return orders

# ==========================
# MODULE LIFECYCLE
# ==========================
def initialize():
    """Initialize district market module."""
    print("[DistrictMarket] Initializing database...")
    Base.metadata.create_all(bind=engine)
    load_district_items()
    print("[DistrictMarket] Module initialized")

async def tick(current_tick: int, now: datetime):
    """Tick handler - match pending orders."""
    db = get_db()
    active_orders = db.query(DistrictMarketOrder).filter(
        DistrictMarketOrder.status.in_([OrderStatus.ACTIVE, OrderStatus.PARTIALLY_FILLED])
    ).order_by(DistrictMarketOrder.created_at.asc()).all()
    
    for order in active_orders:
        match_order(db, order)
    
    if current_tick % 3600 == 0:
        print(f"[DistrictMarket] Hourly Stats: {get_market_stats()}")
    
    db.close()

__all__ = [
    'create_order', 
    'cancel_order', 
    'get_order_book', 
    'get_market_price', 
    'get_market_stats',
    'get_player_orders',
    'get_district_item_info',
    'get_district_ticker_html',
    'DISTRICT_ITEMS',
    'OrderType',
    'OrderMode'
]
