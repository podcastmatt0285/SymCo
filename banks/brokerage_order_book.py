"""
banks/brokerage_order_book.py - ORDER BOOK & MATCHING ENGINE

Adds price discovery to the brokerage firm through:
- Limit orders (buy/sell at specific prices)
- Market orders (execute at best available price)
- Order matching engine
- Real-time price updates based on trades
- Order book display (bid/ask spreads)

To integrate into brokerage_firm.py:
1. Import this module
2. Replace direct buy_shares/sell_shares calls with place_order
3. Add tick handler for order matching
"""

from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from enum import Enum

from sqlalchemy import create_engine, Column, String, Float, DateTime, Integer, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from stats_ux import log_transaction
# ==========================
# DATABASE SETUP
# ==========================
DATABASE_URL = "sqlite:///./symco.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ==========================
# CONSTANTS
# ==========================
ORDER_EXPIRY_TICKS = 86400  # 24 hours in ticks (at 1 second per tick)
MAX_PRICE_IMPACT = 0.10  # Market orders can't move price more than 10% per trade
MIN_ORDER_SIZE = 1  # Minimum 1 share
MAX_ORDER_SIZE = 1000000  # Max 1M shares per order

# ==========================
# ENUMS
# ==========================

class OrderType(str, Enum):
    LIMIT = "limit"  # Execute at specified price or better
    MARKET = "market"  # Execute at best available price immediately
    STOP_LOSS = "stop_loss"  # Converts to market order when price drops to trigger
    STOP_LIMIT = "stop_limit"  # Converts to limit order when price hits trigger


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(str, Enum):
    PENDING = "pending"  # Waiting in order book
    PARTIAL = "partial"  # Partially filled
    FILLED = "filled"  # Completely filled
    CANCELLED = "cancelled"  # Manually cancelled by player
    EXPIRED = "expired"  # Expired due to time limit
    REJECTED = "rejected"  # Rejected due to insufficient funds/shares


# ==========================
# DATABASE MODELS
# ==========================

class OrderBook(Base):
    """
    Individual order in the order book.
    """
    __tablename__ = "order_book"
    
    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, index=True, nullable=False)
    company_shares_id = Column(Integer, index=True, nullable=False)
    
    # Order details
    order_type = Column(String, nullable=False)  # OrderType enum
    order_side = Column(String, nullable=False)  # OrderSide enum
    status = Column(String, default=OrderStatus.PENDING.value)
    
    # Pricing
    limit_price = Column(Float, nullable=True)  # For limit orders
    stop_price = Column(Float, nullable=True)  # For stop orders
    
    # Quantities
    quantity = Column(Integer, nullable=False)  # Total shares
    filled_quantity = Column(Integer, default=0)  # Shares filled so far
    
    # Margin trading
    use_margin = Column(Boolean, default=False)
    margin_multiplier = Column(Float, default=1.0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    expires_at = Column(DateTime, nullable=True)
    filled_at = Column(DateTime, nullable=True)
    
    # Reserved funds/shares (locked when order placed)
    reserved_cash = Column(Float, default=0.0)  # For buy orders
    reserved_shares = Column(Integer, default=0)  # For sell orders


class OrderFill(Base):
    """
    Record of a matched trade between two orders.
    """
    __tablename__ = "order_fills"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Orders involved
    buy_order_id = Column(Integer, ForeignKey("order_book.id"), index=True)
    sell_order_id = Column(Integer, ForeignKey("order_book.id"), index=True)
    
    # Players involved
    buyer_id = Column(Integer, index=True, nullable=False)
    seller_id = Column(Integer, index=True, nullable=False)
    
    # Company
    company_shares_id = Column(Integer, index=True, nullable=False)
    ticker_symbol = Column(String, nullable=False)
    
    # Trade details
    price = Column(Float, nullable=False)  # Execution price
    quantity = Column(Integer, nullable=False)  # Shares traded
    total_value = Column(Float, nullable=False)  # price * quantity
    
    # Commissions
    buyer_commission = Column(Float, default=0.0)
    seller_commission = Column(Float, default=0.0)
    
    # Margin info
    margin_used = Column(Boolean, default=False)
    margin_debt = Column(Float, default=0.0)
    
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)


# ==========================
# HELPER FUNCTIONS
# ==========================

def get_db():
    """Get database session."""
    db = SessionLocal()
    return db


def get_company_ticker(company_shares_id: int) -> Optional[str]:
    """Get ticker symbol for a company."""
    from banks.brokerage_firm import CompanyShares
    db = get_db()
    try:
        company = db.query(CompanyShares).filter(
            CompanyShares.id == company_shares_id
        ).first()
        return company.ticker_symbol if company else None
    finally:
        db.close()


def get_player_cash(player_id: int) -> float:
    """Get player's available cash."""
    from auth import Player, get_db as get_auth_db
    db = get_auth_db()
    try:
        player = db.query(Player).filter(Player.id == player_id).first()
        return player.cash_balance if player else 0.0
    finally:
        db.close()


def get_player_shares(player_id: int, company_shares_id: int) -> int:
    """Get player's available shares (not lent out or reserved)."""
    from banks.brokerage_firm import ShareholderPosition
    db = get_db()
    try:
        position = db.query(ShareholderPosition).filter(
            ShareholderPosition.player_id == player_id,
            ShareholderPosition.company_shares_id == company_shares_id
        ).first()
        
        if not position:
            return 0
        
        # Calculate truly available shares
        available = position.shares_owned - position.shares_lent_out
        
        # Subtract shares reserved in pending sell orders
        reserved = db.query(OrderBook).filter(
            OrderBook.player_id == player_id,
            OrderBook.company_shares_id == company_shares_id,
            OrderBook.order_side == OrderSide.SELL.value,
            OrderBook.status.in_([OrderStatus.PENDING.value, OrderStatus.PARTIAL.value])
        ).with_entities(
            OrderBook.reserved_shares
        ).all()
        
        total_reserved = sum(r[0] for r in reserved)
        
        return max(0, available - total_reserved)
    finally:
        db.close()


# ==========================
# ORDER PLACEMENT
# ==========================

def place_limit_order(
    player_id: int,
    company_shares_id: int,
    side: OrderSide,
    quantity: int,
    limit_price: float,
    use_margin: bool = False,
    margin_multiplier: float = 1.0
) -> Optional[OrderBook]:
    """
    Place a limit order to buy/sell at a specific price.
    
    Args:
        player_id: Player placing the order
        company_shares_id: Company to trade
        side: BUY or SELL
        quantity: Number of shares
        limit_price: Price per share
        use_margin: Whether to use margin (buy orders only)
        margin_multiplier: Leverage multiplier (if margin)
    
    Returns:
        OrderBook object if successful, None otherwise
    """
    if quantity < MIN_ORDER_SIZE or quantity > MAX_ORDER_SIZE:
        print(f"[OrderBook] Invalid order size: {quantity}")
        return None
    
    if limit_price <= 0:
        print(f"[OrderBook] Invalid limit price: {limit_price}")
        return None
    
    db = get_db()
    try:
        from banks.brokerage_firm import CompanyShares, get_player_credit, get_max_leverage_for_player
        
        # Verify company exists and is tradeable
        company = db.query(CompanyShares).filter(
            CompanyShares.id == company_shares_id
        ).first()
        
        if not company or company.is_delisted:
            print(f"[OrderBook] Company not found or delisted")
            return None
        
        if company.trading_halted_until and datetime.utcnow() < company.trading_halted_until:
            print(f"[OrderBook] Trading halted for {company.ticker_symbol}")
            return None
        
        # Create order
        order = OrderBook(
            player_id=player_id,
            company_shares_id=company_shares_id,
            order_type=OrderType.LIMIT.value,
            order_side=side.value,
            status=OrderStatus.PENDING.value,
            limit_price=limit_price,
            quantity=quantity,
            filled_quantity=0,
            use_margin=use_margin if side == OrderSide.BUY else False,
            margin_multiplier=margin_multiplier if use_margin else 1.0,
            expires_at=datetime.utcnow() + timedelta(seconds=ORDER_EXPIRY_TICKS)
        )
        
        # Reserve funds or shares
        if side == OrderSide.BUY:
            # Reserve cash for buy order
            total_cost = quantity * limit_price
            
            if use_margin:
                # Verify margin eligibility
                max_leverage = get_max_leverage_for_player(player_id)
                if margin_multiplier > max_leverage:
                    print(f"[OrderBook] Margin multiplier {margin_multiplier}x exceeds max {max_leverage}x")
                    return None
                
                # Only need to reserve player's portion
                player_portion = total_cost / margin_multiplier
                order.reserved_cash = player_portion
            else:
                order.reserved_cash = total_cost
            
            # Check if player has enough cash
            available_cash = get_player_cash(player_id)
            if available_cash < order.reserved_cash:
                print(f"[OrderBook] Insufficient cash: need ${order.reserved_cash:.2f}, have ${available_cash:.2f}")
                return None
            
            # Lock the cash (deduct from player)
            from auth import Player, get_db as get_auth_db
            auth_db = get_auth_db()
            try:
                player = auth_db.query(Player).filter(Player.id == player_id).first()
                if player:
                    player.cash_balance -= order.reserved_cash
                    auth_db.commit()
            finally:
                auth_db.close()
        
        else:  # SELL
            # Reserve shares for sell order
            available_shares = get_player_shares(player_id, company_shares_id)
            if available_shares < quantity:
                print(f"[OrderBook] Insufficient shares: need {quantity}, have {available_shares}")
                return None
            
            order.reserved_shares = quantity
            # Shares stay in player's position, just marked as reserved
        
        db.add(order)
        db.commit()
        db.refresh(order)
        
        print(f"[OrderBook] {side.value.upper()} LIMIT: {quantity} {company.ticker_symbol} @ ${limit_price:.2f}" +
              (f" (margin {margin_multiplier}x)" if use_margin else ""))
        
        # Try to match immediately
        match_orders(company_shares_id)
        
        return order
    
    except Exception as e:
        print(f"[OrderBook] Error placing limit order: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        db.close()


def place_market_order(
    player_id: int,
    company_shares_id: int,
    side: OrderSide,
    quantity: int,
    use_margin: bool = False,
    margin_multiplier: float = 1.0
) -> bool:
    """
    Place a market order to buy/sell immediately at best available price.
    
    Market orders execute against existing limit orders in the order book.
    If no matching orders exist, the market order is rejected.
    
    Returns True if order was placed and executed.
    """
    if quantity < MIN_ORDER_SIZE or quantity > MAX_ORDER_SIZE:
        return False
    
    db = get_db()
    try:
        from banks.brokerage_firm import CompanyShares
        
        company = db.query(CompanyShares).filter(
            CompanyShares.id == company_shares_id
        ).first()
        
        if not company or company.is_delisted:
            return False
        
        if company.trading_halted_until and datetime.utcnow() < company.trading_halted_until:
            print(f"[OrderBook] Trading halted")
            return False
        
        # Get best available price from order book
        if side == OrderSide.BUY:
            # Buy at lowest ask
            best_order = db.query(OrderBook).filter(
                OrderBook.company_shares_id == company_shares_id,
                OrderBook.order_side == OrderSide.SELL.value,
                OrderBook.status.in_([OrderStatus.PENDING.value, OrderStatus.PARTIAL.value])
            ).order_by(OrderBook.limit_price.asc()).first()
            
            if not best_order:
                print(f"[OrderBook] No sell orders available for market buy")
                return False
            
            # Estimate price (could be higher if order book is thin)
            estimated_price = best_order.limit_price * 1.05  # Add 5% buffer
            
        else:  # SELL
            # Sell at highest bid
            best_order = db.query(OrderBook).filter(
                OrderBook.company_shares_id == company_shares_id,
                OrderBook.order_side == OrderSide.BUY.value,
                OrderBook.status.in_([OrderStatus.PENDING.value, OrderStatus.PARTIAL.value])
            ).order_by(OrderBook.limit_price.desc()).first()
            
            if not best_order:
                print(f"[OrderBook] No buy orders available for market sell")
                return False
            
            estimated_price = best_order.limit_price * 0.95  # Subtract 5% buffer
        
        # For market orders, we place a limit order at an extreme price
        # This ensures it executes against any available orders
        if side == OrderSide.BUY:
            # Buy at up to 10% above current best ask
            max_price = estimated_price * 1.10
            order = place_limit_order(
                player_id, company_shares_id, side, quantity, 
                max_price, use_margin, margin_multiplier
            )
        else:
            # Sell at down to 10% below current best bid
            min_price = max(0.01, estimated_price * 0.90)
            order = place_limit_order(
                player_id, company_shares_id, side, quantity, min_price
            )
        
        if order:
            # Mark as market order for tracking
            order.order_type = OrderType.MARKET.value
            db.commit()
            
            # Immediately try to match
            match_orders(company_shares_id)
            
            return True
        
        return False
    
    except Exception as e:
        print(f"[OrderBook] Market order error: {e}")
        return False
    finally:
        db.close()


# ==========================
# ORDER MATCHING ENGINE
# ==========================

def match_orders(company_shares_id: int):
    """
    Match buy and sell orders for a specific company.
    
    Matching algorithm:
    1. Get all active buy orders (highest price first)
    2. Get all active sell orders (lowest price first)
    3. Match where buy_price >= sell_price
    4. Execute trades, update positions, record fills
    5. Update company's current_price to last trade price
    """
    db = get_db()
    try:
        from banks.brokerage_firm import (
            CompanyShares, ShareholderPosition, firm_add_cash,
            EQUITY_TRADE_COMMISSION, record_price, BANK_NAME, BANK_PLAYER_ID
        )
        from auth import Player, get_db as get_auth_db
        
        company = db.query(CompanyShares).filter(
            CompanyShares.id == company_shares_id
        ).first()
        
        if not company or company.is_delisted:
            return
        
        # Get active orders
        buy_orders = db.query(OrderBook).filter(
            OrderBook.company_shares_id == company_shares_id,
            OrderBook.order_side == OrderSide.BUY.value,
            OrderBook.status.in_([OrderStatus.PENDING.value, OrderStatus.PARTIAL.value])
        ).order_by(
            OrderBook.limit_price.desc(),  # Highest price first
            OrderBook.created_at.asc()  # Earlier orders first
        ).all()
        
        sell_orders = db.query(OrderBook).filter(
            OrderBook.company_shares_id == company_shares_id,
            OrderBook.order_side == OrderSide.SELL.value,
            OrderBook.status.in_([OrderStatus.PENDING.value, OrderStatus.PARTIAL.value])
        ).order_by(
            OrderBook.limit_price.asc(),  # Lowest price first
            OrderBook.created_at.asc()
        ).all()
        
        if not buy_orders or not sell_orders:
            return
        
        trades_executed = 0
        last_trade_price = company.current_price
        
        # Match orders
        for buy_order in buy_orders:
            if buy_order.filled_quantity >= buy_order.quantity:
                buy_order.status = OrderStatus.FILLED.value
                buy_order.filled_at = datetime.utcnow()
                continue
            
            for sell_order in sell_orders:
                if sell_order.filled_quantity >= sell_order.quantity:
                    sell_order.status = OrderStatus.FILLED.value
                    sell_order.filled_at = datetime.utcnow()
                    continue
                
                # Check if prices cross
                if buy_order.limit_price < sell_order.limit_price:
                    break  # No more matches possible
                
                # Determine execution price (typically seller's price)
                execution_price = sell_order.limit_price
                
                # Determine quantity to trade
                buy_remaining = buy_order.quantity - buy_order.filled_quantity
                sell_remaining = sell_order.quantity - sell_order.filled_quantity
                trade_quantity = min(buy_remaining, sell_remaining)
                
                # Execute the trade
                if execute_trade(
                    buy_order, sell_order, trade_quantity, 
                    execution_price, company, db
                ):
                    trades_executed += 1
                    last_trade_price = execution_price
                    
                    # Update fill quantities
                    buy_order.filled_quantity += trade_quantity
                    sell_order.filled_quantity += trade_quantity
                    
                    # Update statuses
                    if buy_order.filled_quantity >= buy_order.quantity:
                        buy_order.status = OrderStatus.FILLED.value
                        buy_order.filled_at = datetime.utcnow()
                    else:
                        buy_order.status = OrderStatus.PARTIAL.value
                    
                    if sell_order.filled_quantity >= sell_order.quantity:
                        sell_order.status = OrderStatus.FILLED.value
                        sell_order.filled_at = datetime.utcnow()
                    else:
                        sell_order.status = OrderStatus.PARTIAL.value
                
                # If buy order is filled, move to next buy order
                if buy_order.filled_quantity >= buy_order.quantity:
                    break
        
        # Update company's current price to last trade price
        if trades_executed > 0:
            company.current_price = last_trade_price
            print(f"[OrderBook] Matched {trades_executed} trade(s) for {company.ticker_symbol}, new price: ${last_trade_price:.2f}")
        
        db.commit()
    
    except Exception as e:
        print(f"[OrderBook] Matching error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


def execute_trade(
    buy_order: OrderBook,
    sell_order: OrderBook,
    quantity: int,
    price: float,
    company: 'CompanyShares',
    db
) -> bool:
    """
    Execute a trade between a buy order and sell order.
    
    Handles:
    - Share transfer
    - Cash settlement
    - Margin debt creation
    - Commission payment
    - Position updates
    - Trade recording
    """
    try:
        from banks.brokerage_firm import (
            ShareholderPosition, firm_add_cash, firm_deduct_cash,
            EQUITY_TRADE_COMMISSION, record_price, BANK_PLAYER_ID
        )
        from auth import Player, get_db as get_auth_db
        
        buyer_id = buy_order.player_id
        seller_id = sell_order.player_id
        
        total_value = quantity * price
        
        # Calculate commissions
        buyer_commission = total_value * EQUITY_TRADE_COMMISSION
        seller_commission = total_value * EQUITY_TRADE_COMMISSION
        
        # === BUYER SIDE ===
        
        # Get buyer's position
        buyer_position = db.query(ShareholderPosition).filter(
            ShareholderPosition.player_id == buyer_id,
            ShareholderPosition.company_shares_id == company.id
        ).first()
        
        if not buyer_position:
            buyer_position = ShareholderPosition(
                player_id=buyer_id,
                company_shares_id=company.id,
                shares_owned=0,
                average_cost_basis=price,
                is_margin_position=buy_order.use_margin,
                margin_shares=0,
                margin_debt=0.0,
                margin_multiplier_used=buy_order.margin_multiplier
            )
            db.add(buyer_position)
        
        # Add shares
        buyer_position.shares_owned += quantity
        
        # Handle margin
        margin_debt = 0.0
        if buy_order.use_margin:
            player_portion = total_value / buy_order.margin_multiplier
            firm_portion = total_value - player_portion
            margin_debt = firm_portion
            
            buyer_position.is_margin_position = True
            buyer_position.margin_shares += quantity
            buyer_position.margin_debt += margin_debt
            buyer_position.margin_multiplier_used = buy_order.margin_multiplier
        
        # Update average cost basis
        total_shares = buyer_position.shares_owned
        old_value = (total_shares - quantity) * buyer_position.average_cost_basis
        new_value = old_value + (quantity * price)
        buyer_position.average_cost_basis = new_value / total_shares if total_shares > 0 else price
        
        # Release reserved cash (partial release for partial fill)
        cash_per_share = buy_order.reserved_cash / buy_order.quantity
        cash_to_release = cash_per_share * (buy_order.quantity - buy_order.filled_quantity - quantity)
        
        if cash_to_release > 0:
            auth_db = get_auth_db()
            try:
                buyer = auth_db.query(Player).filter(Player.id == buyer_id).first()
                if buyer:
                    buyer.cash_balance += cash_to_release
                    auth_db.commit()
            finally:
                auth_db.close()
        
        # Pay commission
        auth_db = get_auth_db()
        try:
            buyer = auth_db.query(Player).filter(Player.id == buyer_id).first()
            if buyer:
                buyer.cash_balance -= buyer_commission
                auth_db.commit()
                
                # Log share purchase and payment
                log_transaction(
                    buyer_id, 
                    "share_buy", 
                    "share", 
                    quantity,
                    f"Bought {quantity} {company.ticker_symbol} @ ${price:.2f}",
                    company.ticker_symbol
                )
                
                total_cost = (quantity * price) + buyer_commission
                log_transaction(
                    buyer_id,
                    "cash_out",
                    "money",
                    -total_cost,
                    f"Share purchase: {company.ticker_symbol}",
                    company.ticker_symbol
                )
        finally:
            auth_db.close()
        
        firm_add_cash(buyer_commission, "trade_commission", 
                     f"Commission on {company.ticker_symbol}", buyer_id, company.id)
        
        # === SELLER SIDE ===
        
        # Get seller's position
        seller_position = db.query(ShareholderPosition).filter(
            ShareholderPosition.player_id == seller_id,
            ShareholderPosition.company_shares_id == company.id
        ).first()
        
        if not seller_position or seller_position.shares_owned < quantity:
            print(f"[OrderBook] ERROR: Seller {seller_id} doesn't have {quantity} shares")
            return False
        
        # Remove shares
        seller_position.shares_owned -= quantity
        
        # Handle margin repayment if seller had margin position
        if seller_position.is_margin_position and seller_position.margin_shares > 0:
            margin_shares_sold = min(quantity, seller_position.margin_shares)
            if margin_shares_sold > 0 and seller_position.margin_debt > 0:
                debt_per_share = seller_position.margin_debt / seller_position.margin_shares
                debt_to_pay = debt_per_share * margin_shares_sold
                debt_to_pay = min(debt_to_pay, total_value)
                
                seller_position.margin_debt -= debt_to_pay
                seller_position.margin_shares -= margin_shares_sold
                
                # Reduce proceeds by debt payment
                total_value -= debt_to_pay
                
                # Pay debt to Firm
                firm_add_cash(debt_to_pay, "margin_repayment", 
                             f"Margin repayment on {company.ticker_symbol}", seller_id)
                
                if seller_position.margin_debt <= 0:
                    seller_position.is_margin_position = False
                    seller_position.margin_multiplier_used = 1.0
        
        # If founder selling, update company
        if seller_id == company.founder_id:
            company.shares_held_by_founder -= quantity
        
        # Add to float
        company.shares_in_float += quantity
        
        # Pay seller (minus commission)
        proceeds = total_value - seller_commission
        
        auth_db = get_auth_db()
        try:
            seller = auth_db.query(Player).filter(Player.id == seller_id).first()
            if seller:
                seller.cash_balance += proceeds
                auth_db.commit()
                
                # Log share sale and payment
                log_transaction(
                    seller_id,
                    "share_sell",
                    "share",
                    -quantity,  # negative because shares leaving
                    f"Sold {quantity} {company.ticker_symbol} @ ${price:.2f}",
                    company.ticker_symbol
                )
                
                log_transaction(
                    seller_id,
                    "cash_in",
                    "money",
                    proceeds,
                    f"Share sale: {company.ticker_symbol}",
                    company.ticker_symbol
                )
        finally:
            auth_db.close()
        
        firm_add_cash(seller_commission, "trade_commission", 
                     f"Commission on {company.ticker_symbol}", seller_id, company.id)
        
        # === RECORD TRADE ===
        
        fill = OrderFill(
            buy_order_id=buy_order.id,
            sell_order_id=sell_order.id,
            buyer_id=buyer_id,
            seller_id=seller_id,
            company_shares_id=company.id,
            ticker_symbol=company.ticker_symbol,
            price=price,
            quantity=quantity,
            total_value=quantity * price,
            buyer_commission=buyer_commission,
            seller_commission=seller_commission,
            margin_used=buy_order.use_margin,
            margin_debt=margin_debt
        )
        db.add(fill)
        
        # Record price for chart
        record_price(company_shares_id=company.id, price=price, volume=quantity)
        
        print(f"[OrderBook] TRADE: {quantity} {company.ticker_symbol} @ ${price:.2f} " +
              f"(buyer: {buyer_id}, seller: {seller_id})")
        
        return True
    
    except Exception as e:
        print(f"[OrderBook] Trade execution error: {e}")
        import traceback
        traceback.print_exc()
        return False


# ==========================
# ORDER MANAGEMENT
# ==========================

def cancel_order(player_id: int, order_id: int) -> bool:
    """
    Cancel a pending order and release reserved funds/shares.
    """
    db = get_db()
    try:
        order = db.query(OrderBook).filter(
            OrderBook.id == order_id,
            OrderBook.player_id == player_id,
            OrderBook.status.in_([OrderStatus.PENDING.value, OrderStatus.PARTIAL.value])
        ).first()
        
        if not order:
            return False
        
        # Release reserved resources
        if order.order_side == OrderSide.BUY.value and order.reserved_cash > 0:
            # Release unfilled portion of reserved cash
            unfilled_quantity = order.quantity - order.filled_quantity
            cash_per_share = order.reserved_cash / order.quantity
            cash_to_release = cash_per_share * unfilled_quantity
            
            from auth import Player, get_db as get_auth_db
            auth_db = get_auth_db()
            try:
                player = auth_db.query(Player).filter(Player.id == player_id).first()
                if player:
                    player.cash_balance += cash_to_release
                    auth_db.commit()
            finally:
                auth_db.close()
        
        # Note: For sell orders, shares are already in player's position
        # just marked as reserved by the order existing
        
        order.status = OrderStatus.CANCELLED.value
        db.commit()
        
        print(f"[OrderBook] Cancelled order {order_id}")
        return True
    
    except Exception as e:
        print(f"[OrderBook] Cancel error: {e}")
        return False
    finally:
        db.close()


def expire_old_orders():
    """
    Expire orders that have passed their expiry time.
    Called periodically by tick handler.
    """
    db = get_db()
    try:
        now = datetime.utcnow()
        
        expired = db.query(OrderBook).filter(
            OrderBook.status.in_([OrderStatus.PENDING.value, OrderStatus.PARTIAL.value]),
            OrderBook.expires_at <= now
        ).all()
        
        for order in expired:
            # Release resources
            if order.order_side == OrderSide.BUY.value and order.reserved_cash > 0:
                unfilled_quantity = order.quantity - order.filled_quantity
                cash_per_share = order.reserved_cash / order.quantity
                cash_to_release = cash_per_share * unfilled_quantity
                
                from auth import Player, get_db as get_auth_db
                auth_db = get_auth_db()
                try:
                    player = auth_db.query(Player).filter(Player.id == order.player_id).first()
                    if player:
                        player.cash_balance += cash_to_release
                        auth_db.commit()
                finally:
                    auth_db.close()
            
            order.status = OrderStatus.EXPIRED.value
        
        if expired:
            print(f"[OrderBook] Expired {len(expired)} old order(s)")
            db.commit()
    
    except Exception as e:
        print(f"[OrderBook] Expire error: {e}")
    finally:
        db.close()


# ==========================
# ORDER BOOK DISPLAY
# ==========================

def get_order_book_depth(company_shares_id: int, depth: int = 10) -> dict:
    """
    Get current order book depth (bid/ask ladder).

    Returns:
        {
            'bids': [(price, quantity), ...],  # Highest to lowest
            'asks': [(price, quantity), ...],  # Lowest to highest
            'spread': float,
            'spread_pct': float,
            'mid_price': float
        }
    """
    db = get_db()
    try:
        # Get buy orders (bids)
        buy_orders = db.query(OrderBook).filter(
            OrderBook.company_shares_id == company_shares_id,
            OrderBook.order_side == OrderSide.BUY.value,
            OrderBook.status.in_([OrderStatus.PENDING.value, OrderStatus.PARTIAL.value])
        ).order_by(OrderBook.limit_price.desc()).limit(depth).all()
        
        # Get sell orders (asks)
        sell_orders = db.query(OrderBook).filter(
            OrderBook.company_shares_id == company_shares_id,
            OrderBook.order_side == OrderSide.SELL.value,
            OrderBook.status.in_([OrderStatus.PENDING.value, OrderStatus.PARTIAL.value])
        ).order_by(OrderBook.limit_price.asc()).limit(depth).all()
        
        bids = [(o.limit_price, o.quantity - o.filled_quantity) for o in buy_orders]
        asks = [(o.limit_price, o.quantity - o.filled_quantity) for o in sell_orders]
        
        best_bid = bids[0][0] if bids else 0.0
        best_ask = asks[0][0] if asks else 0.0
        
        spread = best_ask - best_bid if (best_bid > 0 and best_ask > 0) else 0.0
        mid_price = (best_bid + best_ask) / 2 if (best_bid > 0 and best_ask > 0) else 0.0
        spread_pct = (spread / mid_price * 100) if mid_price > 0 else 0.0

        return {
            'bids': bids,
            'asks': asks,
            'spread': spread,
            'spread_pct': spread_pct,
            'mid_price': mid_price,
            'best_bid': best_bid,
            'best_ask': best_ask
        }
    finally:
        db.close()


def get_recent_fills(company_shares_id: int, limit: int = 20) -> List[dict]:
    """Get recent trade history for a company."""
    db = get_db()
    try:
        fills = db.query(OrderFill).filter(
            OrderFill.company_shares_id == company_shares_id
        ).order_by(OrderFill.timestamp.desc()).limit(limit).all()
        
        return [{
            'price': f.price,
            'quantity': f.quantity,
            'timestamp': f.timestamp.isoformat(),
            'total_value': f.total_value
        } for f in fills]
    finally:
        db.close()


# ==========================
# INITIALIZATION & TICK
# ==========================

def player_place_buy_order(
    player_id: int,
    company_shares_id: int,
    quantity: int,
    limit_price: Optional[float] = None,
    use_margin: bool = False,
    margin_multiplier: float = 1.0
) -> bool:
    """
    Simplified buy order interface for UX layer.
    
    Args:
        player_id: Player placing the order
        company_shares_id: Company to buy shares from
        quantity: Number of shares to buy
        limit_price: Price per share (None = market order)
        use_margin: Whether to use margin
        margin_multiplier: Leverage multiplier (if margin)
    
    Returns:
        True if order was placed successfully
    """
    try:
        if limit_price is not None:
            # Place limit order
            order = place_limit_order(
                player_id=player_id,
                company_shares_id=company_shares_id,
                side=OrderSide.BUY,
                quantity=quantity,
                limit_price=limit_price,
                use_margin=use_margin,
                margin_multiplier=margin_multiplier
            )
            return order is not None
        else:
            # Place market order
            return place_market_order(
                player_id=player_id,
                company_shares_id=company_shares_id,
                side=OrderSide.BUY,
                quantity=quantity,
                use_margin=use_margin,
                margin_multiplier=margin_multiplier
            )
    except Exception as e:
        print(f"[OrderBook] player_place_buy_order error: {e}")
        return False


def player_place_sell_order(
    player_id: int,
    company_shares_id: int,
    quantity: int,
    limit_price: Optional[float] = None
) -> bool:
    """
    Simplified sell order interface for UX layer.
    
    Args:
        player_id: Player placing the order
        company_shares_id: Company to sell shares from
        quantity: Number of shares to sell
        limit_price: Price per share (None = market order)
    
    Returns:
        True if order was placed successfully
    """
    try:
        if limit_price is not None:
            # Place limit order
            order = place_limit_order(
                player_id=player_id,
                company_shares_id=company_shares_id,
                side=OrderSide.SELL,
                quantity=quantity,
                limit_price=limit_price,
                use_margin=False
            )
            return order is not None
        else:
            # Place market order
            return place_market_order(
                player_id=player_id,
                company_shares_id=company_shares_id,
                side=OrderSide.SELL,
                quantity=quantity,
                use_margin=False
            )
    except Exception as e:
        print(f"[OrderBook] player_place_sell_order error: {e}")
        return False


def initialize():
    """Initialize order book tables."""
    print("[OrderBook] Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("[OrderBook] Order book system initialized")


def tick(current_tick: int):
    """
    Order book tick handler.
    
    Processes:
    - Order matching for all active companies
    - Order expiry
    """
    # Match orders every tick
    from banks.brokerage_firm import CompanyShares
    db = get_db()
    try:
        active_companies = db.query(CompanyShares).filter(
            CompanyShares.is_delisted == False
        ).all()
        
        for company in active_companies:
            match_orders(company.id)
    finally:
        db.close()
    
    # Expire old orders every 60 ticks (1 minute)
    if current_tick % 60 == 0:
        expire_old_orders()


# ==========================
# PUBLIC API
# ==========================

__all__ = [
    # Order placement
    'place_limit_order',
    'place_market_order',
    'player_place_buy_order',
    'player_place_sell_order',
    'cancel_order',
    
    # Order book display
    'get_order_book_depth',
    'get_recent_fills',
    
    # Lifecycle
    'initialize',
    'tick',
    
    # Models
    'OrderBook',
    'OrderFill',
    
    # Enums
    'OrderType',
    'OrderSide',
    'OrderStatus',
]
