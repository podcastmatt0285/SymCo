"""
market.py

Market module for the economic simulation.
Handles:
- Player-driven buy and sell orders
- Order matching engine (tick-driven)
- Market orders vs limit orders
- Order book display
- Price discovery
- Trade execution
- Market statistics
- Initial inventory distribution for new players
"""

from datetime import datetime
from typing import Optional, List, Tuple
from enum import Enum
from sqlalchemy import create_engine, Column, String, Float, DateTime, Integer, Boolean
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
# ENUMS
# ==========================
class OrderType(str, Enum):
    BUY = "buy"
    SELL = "sell"

class OrderMode(str, Enum):
    LIMIT = "limit"      # Execute at specified price or better
    MARKET = "market"    # Execute at best available price immediately

class OrderStatus(str, Enum):
    ACTIVE = "active"          # Order is open and waiting
    FILLED = "filled"          # Order completely filled
    PARTIALLY_FILLED = "partial"  # Order partially filled
    CANCELLED = "cancelled"    # Order cancelled by user
    EXPIRED = "expired"        # Order expired (if we add time limits)

# ==========================
# DATABASE MODELS
# ==========================
class MarketOrder(Base):
    """Market order model."""
    __tablename__ = "market_orders"
    
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

class Trade(Base):
    """Trade history model."""
    __tablename__ = "trades"
    
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
# STARTER INVENTORY
# ==========================
STARTER_INVENTORY = {
    "apple_seeds": 1,
    "orange_seeds": 1,
    "water": 5000,
    "energy": 1500,
    "paper": 15000,
    "wheat_seeds": 15,
    "barley_seeds": 13,
    "corn_seeds": 15,
    "coffee_seeds": 12,
    "cherry_seeds": 12,
    "cocoa_seeds": 12,
    "grape_seeds": 12
}

# ==========================
# HELPER FUNCTIONS
# ==========================
def get_db():
    db = SessionLocal()
    try:
        return db
    except Exception as e:
        print(f"[Market] Database error: {e}")
        db.close()
        raise

def give_starter_inventory(player_id: int) -> dict:
    try:
        import inventory
        print(f"[Market] Giving starter inventory to player {player_id}:")
        for item, quantity in STARTER_INVENTORY.items():
            inventory.add_item(player_id, item, quantity)
            print(f"  → {quantity}x {item}")
    except ImportError:
        print("[Market] Inventory module not available - starter items not given")
    return STARTER_INVENTORY

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
) -> Optional[MarketOrder]:
    db = get_db()
    
    # 1. Basic Validation 
    if order_mode == OrderMode.LIMIT and price is None:
        db.close()
        return None
    if quantity <= 0:
        db.close()
        return None

    # 2. Cash Validation: Prevent buy orders if player is broke
    if order_type == OrderType.BUY:
        from auth import Player
        player = db.query(Player).filter(Player.id == player_id).first()
        if not player or player.cash_balance < (quantity * (price or 0)):
            print(f"[Market] Player {player_id} has insufficient funds for buy order")
            db.close()
            return None
    
    # 3. NEW: Inventory Validation: Prevent sell orders if player doesn't have the items
    if order_type == OrderType.SELL:
        try:
            import inventory
            current_quantity = inventory.get_item_quantity(player_id, item_type)
            if current_quantity < quantity:
                print(f"[Market] Player {player_id} has insufficient inventory for sell order (has {current_quantity}, needs {quantity} {item_type})")
                db.close()
                return None
        except Exception as e:
            print(f"[Market] Failed to verify inventory: {e}")
            db.close()
            return None
    
    # 4. Create order record 
    order = MarketOrder(
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
    
    print(f"[Market] Order {order.id} created: {order_type.value} {quantity} {item_type}" + 
          (f" @ ${price}" if price else " at market price"))
    
    match_order(db, order)
    db.close()
    return order

# ==========================
# ORDER MATCHING ENGINE
# ==========================
def match_order(db, order: MarketOrder) -> bool:
    if order.status not in [OrderStatus.ACTIVE, OrderStatus.PARTIALLY_FILLED]:
        return False 
    
    matched_any = False
    remaining_qty = order.quantity - order.quantity_filled
    
    if order.order_type == OrderType.BUY:
        potential_matches = db.query(MarketOrder).filter(
            MarketOrder.order_type == OrderType.SELL,
            MarketOrder.status.in_([OrderStatus.ACTIVE, OrderStatus.PARTIALLY_FILLED]),
            MarketOrder.item_type == order.item_type
        ).order_by(MarketOrder.price.asc()).all()
    else:
        potential_matches = db.query(MarketOrder).filter(
            MarketOrder.order_type == OrderType.BUY,
            MarketOrder.status.in_([OrderStatus.ACTIVE, OrderStatus.PARTIALLY_FILLED]),
            MarketOrder.item_type == order.item_type
        ).order_by(MarketOrder.price.desc()).all()

    for match in potential_matches:
        if remaining_qty <= 0: break
        
        # Price Check
        if order.order_mode == OrderMode.LIMIT:
            if order.order_type == OrderType.BUY and (match.price is None or match.price > order.price): continue
            if order.order_type == OrderType.SELL and (match.price is None or match.price < order.price): continue

        trade_qty = min(remaining_qty, match.quantity - match.quantity_filled)
        trade_price = match.price if match.price else order.price
        
        # Determine Buy/Sell roles for execute_trade
        if order.order_type == OrderType.BUY:
            execute_trade(db, order, match, trade_qty, trade_price)
        else:
            execute_trade(db, match, order, trade_qty, trade_price)
            
        remaining_qty -= trade_qty
        matched_any = True
        
    return matched_any

# ==========================
# TRADE EXECUTION (With Bank IPO Hook)
# ==========================

def execute_trade(db, buy_order, sell_order, quantity, price):
    """
    Transfers inventory and cash between players.
    Special handling for bank IPO sales - routes money to bank reserves instead of player accounts.
    """
    # 1. Update order quantities
    buy_order.quantity_filled += quantity
    sell_order.quantity_filled += quantity
    
    # 2. Update order statuses
    for order in [buy_order, sell_order]:
        if order.quantity_filled >= order.quantity:
            order.status = OrderStatus.FILLED
            order.filled_at = datetime.utcnow()
        else:
            order.status = OrderStatus.PARTIALLY_FILLED

    # 3. Record the trade
    trade = Trade(
        buyer_id=buy_order.player_id,
        seller_id=sell_order.player_id,
        buy_order_id=buy_order.id,
        sell_order_id=sell_order.id,
        item_type=buy_order.item_type,
        quantity=quantity,
        price=price
    )
    db.add(trade)
    
    total_cost = quantity * price
    
    # 4. Determine if this is a bank IPO sale
    is_bank_ipo = False
    bank_id = None
    
    # Land Bank IPO detection
    if sell_order.player_id == -2 and sell_order.item_type == "land_bank_shares":
        is_bank_ipo = True
        bank_id = "land_bank"
    
    # ETF Bank IPO detection
    elif sell_order.player_id == -3 and sell_order.item_type == "apple_seeds_etf_shares":
        is_bank_ipo = True
        bank_id = "apple_seeds_etf"
    
    # Energy ETF Bank IPO detection
    elif sell_order.player_id == -4 and sell_order.item_type == "energy_etf_shares":
        is_bank_ipo = True
        bank_id = "energy_etf"
    
    # 5. Handle cash transfer
    if is_bank_ipo:
        # Special bank IPO handling: buyer pays, money goes to BANK RESERVES (not player account)
        try:
            from auth import Player
            import banks
            
            # Get buyer
            buyer = db.query(Player).filter(Player.id == buy_order.player_id).first()
            if not buyer:
                print(f"[Market] CRITICAL ERROR: Buyer {buy_order.player_id} not found!")
                db.rollback()
                return
            
            # Verify buyer has enough money
            if buyer.cash_balance < total_cost:
                print(f"[Market] CRITICAL ERROR: Buyer {buy_order.player_id} has insufficient funds (need ${total_cost:.2f}, have ${buyer.cash_balance:.2f})")
                db.rollback()
                return
            
            # Deduct from buyer's account
            buyer.cash_balance -= total_cost
            
            # Add to bank reserves (this is the economic sink)
            banks.add_bank_revenue(
                bank_id, 
                total_cost, 
                f"IPO Sale: {quantity} shares to Player {buy_order.player_id}"
            )
            
            print(f"[Market] {bank_id.upper()} IPO SALE: Player {buy_order.player_id} paid ${total_cost:.2f} → Bank Reserves")
            
        except Exception as e:
            print(f"[Market] Bank IPO Transfer Error: {e}")
            import traceback
            traceback.print_exc()
            db.rollback()
            return
    else:
        # Standard player-to-player cash transfer
        cities_handled_transfer = False
        
        # Check if cities module needs to handle currency conversion
        try:
            from cities import handle_outsider_trade
            proceed, msg = handle_outsider_trade(buy_order.player_id, sell_order.player_id, 
                                                  buy_order.item_type, quantity, price)
            if not proceed:
                print(f"[Market] Trade blocked: {msg}")
                return
            
            # Check if cities module already handled the cash transfer
            cities_handled_transfer = "handled" in msg.lower()
            
        except ImportError:
            pass
        
        # Only do P2P transfer if cities module didn't already handle it
        if not cities_handled_transfer:
            try:
                from auth import transfer_cash
                success = transfer_cash(buy_order.player_id, sell_order.player_id, total_cost)
                if not success:
                    print(f"[Market] P2P transfer failed: Player {buy_order.player_id} → Player {sell_order.player_id} ${total_cost:.2f}")
                    db.rollback()
                    return
            except ImportError:
                print("[Market] ERROR: Auth module not available for cash transfer")
                db.rollback()
                return

    # 6. Transfer inventory
    try:
        import inventory
        success = inventory.transfer_item(
            sell_order.player_id,
            buy_order.player_id,
            buy_order.item_type,
            quantity
        )
        if not success:
            print(f"[Market] Inventory transfer failed!")
            db.rollback()
            return
    except Exception as e:
        print(f"[Market] Inventory Transfer Error: {e}")
        db.rollback()
        return

    # 7. Commit everything
    db.commit()
    
    # 8. Log transactions
    # Log buyer's resource gain
    log_transaction(
        buy_order.player_id,
        "resource_gain",
        "resource",
        quantity,
        f"Market buy: {buy_order.item_type}",
        buy_order.item_type
    )
    
    # Log buyer's cash payment
    log_transaction(
        buy_order.player_id,
        "cash_out",
        "money",
        -total_cost,  # negative for expense
        f"Market purchase: {quantity} {buy_order.item_type}",
        buy_order.item_type
    )
    
    # Log seller's cash receipt (only for non-bank sales)
    if not is_bank_ipo:
        log_transaction(
            sell_order.player_id,
            "cash_in",
            "money",
            total_cost,
            f"Market sale: {quantity} {buy_order.item_type}",
            buy_order.item_type
        )
        
        # Log seller's resource loss
        log_transaction(
            sell_order.player_id,
            "resource_loss",
            "resource",
            -quantity,  # negative because sold
            f"Market sale: {buy_order.item_type}",
            buy_order.item_type
        )

# ==========================
# MARKET DATA FUNCTIONS
# ==========================
def get_order_book(item_type: str) -> dict:
    """Returns active bids (buys) and asks (sells) with player information."""
    db = get_db()
    
    buy_orders = db.query(MarketOrder).filter(
        MarketOrder.item_type == item_type, 
        MarketOrder.order_type == OrderType.BUY,
        MarketOrder.status.in_([OrderStatus.ACTIVE, OrderStatus.PARTIALLY_FILLED])
    ).order_by(MarketOrder.price.desc()).all() 
    
    sell_orders = db.query(MarketOrder).filter(
        MarketOrder.item_type == item_type, 
        MarketOrder.order_type == OrderType.SELL,
        MarketOrder.status.in_([OrderStatus.ACTIVE, OrderStatus.PARTIALLY_FILLED])
    ).order_by(MarketOrder.price.asc()).all()
    
    # Get player names for display
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
    """Midpoint bid/ask or last trade price."""
    db = get_db()
    last_trade = db.query(Trade).filter(Trade.item_type == item_type).order_by(Trade.executed_at.desc()).first()
    if last_trade:
        db.close()
        return last_trade.price
    
    best_bid = db.query(MarketOrder).filter(MarketOrder.item_type == item_type, MarketOrder.order_type == OrderType.BUY, MarketOrder.status == OrderStatus.ACTIVE, MarketOrder.price != None).order_by(MarketOrder.price.desc()).first()
    best_ask = db.query(MarketOrder).filter(MarketOrder.item_type == item_type, MarketOrder.order_type == OrderType.SELL, MarketOrder.status == OrderStatus.ACTIVE, MarketOrder.price != None).order_by(MarketOrder.price.asc()).first()
    db.close()
    if best_bid and best_ask: return (best_bid.price + best_ask.price) / 2
    return best_bid.price if best_bid else best_ask.price if best_ask else None

def cancel_order(order_id: int, player_id: int) -> bool:
    db = get_db()
    order = db.query(MarketOrder).filter(MarketOrder.id == order_id, MarketOrder.player_id == player_id, MarketOrder.status == OrderStatus.ACTIVE).first()
    if not order:
        db.close()
        return False
    order.status = OrderStatus.CANCELLED
    db.commit()
    db.close()
    return True

def get_market_stats() -> dict:
    db = get_db()
    from datetime import timedelta
    yesterday = datetime.utcnow() - timedelta(days=1)
    recent_trades = db.query(Trade).filter(Trade.executed_at >= yesterday).all() 
    volume = sum(t.quantity * t.price for t in recent_trades)
    stats = {
        "total_orders": db.query(MarketOrder).count(),
        "active_orders": db.query(MarketOrder).filter(MarketOrder.status == OrderStatus.ACTIVE).count(),
        "total_trades": db.query(Trade).count(),
        "volume_24h": volume
    }
    db.close()
    return stats

# ==========================
# MODULE LIFECYCLE
# ==========================
def initialize():
    print("[Market] Initializing database...")
    Base.metadata.create_all(bind=engine)
    print("[Market] Module initialized")

async def tick(current_tick: int, now: datetime):
    db = get_db()
    active_orders = db.query(MarketOrder).filter(MarketOrder.status.in_([OrderStatus.ACTIVE, OrderStatus.PARTIALLY_FILLED])).order_by(MarketOrder.created_at.asc()).all()
    for order in active_orders:
        match_order(db, order)
    if current_tick % 3600 == 0:
        print(f"[Market] Hourly Stats: {get_market_stats()}")
    db.close()

__all__ = ['create_order', 'cancel_order', 'get_order_book', 'get_market_price', 'get_market_stats', 'give_starter_inventory']
