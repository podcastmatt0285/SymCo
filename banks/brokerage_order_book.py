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

import os
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from enum import Enum

from sqlalchemy import Column, String, Float, DateTime, Integer, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from stats_ux import log_transaction
# ==========================
# DATABASE SETUP
# ==========================
from database import engine, SessionLocal


def _push_ob(player_id: int, title: str, body: str, url: str = "/wpe"):
    """Fire an order-book push notification in a background thread."""
    import threading
    def _send():
        try:
            from push_ux import send_push_notification
            send_push_notification(player_id, title, body,
                                   url=url, notif_type="trades",
                                   tag=f"ob-{player_id}-{title[:20]}")
        except Exception as _e:
            print(f"[OrderBook] Push error: {_e}")
    threading.Thread(target=_send, daemon=True).start()
Base = declarative_base()

# ==========================
# CONSTANTS
# ==========================
ORDER_EXPIRY_TICKS = 86400  # 24 hours in ticks (at 1 second per tick)
MAX_PRICE_IMPACT = 0.10  # Market orders can't move price more than 10% per trade
MIN_ORDER_SIZE = 1          # Minimum 1 share
MAX_ORDER_SIZE = 1_000_000_000  # 1 billion shares — matches max IPO size

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
    """Get player's total available cash in USD-equivalent across all currency balances."""
    try:
        from reserve_banks import get_db as get_rb_db, PlayerCurrencyBalance, StateReserveBank
        rb_db = get_rb_db()
        try:
            balances = rb_db.query(PlayerCurrencyBalance).filter(
                PlayerCurrencyBalance.player_id == player_id
            ).all()
            total_usd = 0.0
            for b in balances:
                if (b.balance or 0.0) <= 0:
                    continue
                if b.currency_code == "USD":
                    total_usd += float(b.balance)
                else:
                    bank = rb_db.query(StateReserveBank).filter(
                        StateReserveBank.currency_code == b.currency_code
                    ).first()
                    if bank and bank.usd_per_unit > 0:
                        total_usd += float(b.balance) * float(bank.usd_per_unit)
            return total_usd
        finally:
            rb_db.close()
    except Exception as e:
        print(f"[OrderBook] get_player_cash error: {e}")
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
            if company and company.is_delisted:
                _push_ob(player_id, "Order Rejected",
                         f"{company.ticker_symbol} is currently delisted and cannot be traded.")
            return None

        if company.trading_halted_until and datetime.utcnow() < company.trading_halted_until:
            print(f"[OrderBook] Trading halted for {company.ticker_symbol}")
            _push_ob(player_id, "Order Rejected — Trading Halted",
                     f"Trading is temporarily halted for {company.ticker_symbol}. Try again later.")
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
                    _push_ob(player_id, "Order Rejected — Margin Limit",
                             f"Margin multiplier {margin_multiplier}x exceeds your approved limit of {max_leverage}x.")
                    return None
                
                # Only need to reserve player's portion
                player_portion = total_cost / margin_multiplier
                order.reserved_cash = player_portion
            else:
                order.reserved_cash = total_cost
            
            # Check and lock funds using multi-currency spend (handles all legal tenders)
            from reserve_banks import spend_player_funds
            ok, err = spend_player_funds(player_id, order.reserved_cash)
            if not ok:
                print(f"[OrderBook] Insufficient cash: {err}")
                _push_ob(player_id, "Order Rejected — Insufficient Funds",
                         f"Not enough funds to place a buy order for {quantity:,} {company.ticker_symbol} "
                         f"@ ${limit_price:.2f}. Required: ${order.reserved_cash:,.2f}.")
                return None
        
        else:  # SELL
            # Enforce post-IPO lockup: founder cannot sell before lockup expires
            if player_id == company.founder_id and company.lockup_expires_at:
                if datetime.utcnow() < company.lockup_expires_at:
                    remaining = (company.lockup_expires_at - datetime.utcnow()).days + 1
                    print(f"[OrderBook] Founder lockup active for {company.ticker_symbol}: "
                          f"{remaining} day(s) remaining")
                    _push_ob(player_id, "Order Rejected — Founder Lockup",
                             f"You cannot sell {company.ticker_symbol} yet. "
                             f"Founder lockup expires in {remaining} day(s).")
                    return None

            # Reserve shares for sell order
            available_shares = get_player_shares(player_id, company_shares_id)
            if available_shares < quantity:
                print(f"[OrderBook] Insufficient shares: need {quantity}, have {available_shares}")
                _push_ob(player_id, "Order Rejected — Insufficient Shares",
                         f"You have {available_shares:,} available {company.ticker_symbol} shares "
                         f"but the order requires {quantity:,}.")
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
                _push_ob(player_id, "Market Order Failed",
                         f"No sell orders are currently available for {company.ticker_symbol}. "
                         f"Place a limit order instead.")
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
                _push_ob(player_id, "Market Order Failed",
                         f"No buy orders are currently available for {company.ticker_symbol}. "
                         f"Place a limit order instead.")
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
                
                # Prevent self-trading (founder or any player cannot match their own orders)
                if buy_order.player_id == sell_order.player_id:
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
                    
                    # Update statuses and notify players
                    if buy_order.filled_quantity >= buy_order.quantity:
                        buy_order.status = OrderStatus.FILLED.value
                        buy_order.filled_at = datetime.utcnow()
                        _push_ob(buy_order.player_id, f"Buy Order Filled — {company.ticker_symbol}",
                                 f"Your order for {buy_order.quantity:,} {company.ticker_symbol} "
                                 f"@ ${buy_order.limit_price:.2f} was fully filled at ${execution_price:.2f}.")
                    else:
                        buy_order.status = OrderStatus.PARTIAL.value
                        _push_ob(buy_order.player_id, f"Partial Fill — {company.ticker_symbol}",
                                 f"{trade_quantity:,} of {buy_order.quantity:,} {company.ticker_symbol} "
                                 f"filled @ ${execution_price:.2f}. Order still active.")

                    if sell_order.filled_quantity >= sell_order.quantity:
                        sell_order.status = OrderStatus.FILLED.value
                        sell_order.filled_at = datetime.utcnow()
                        _push_ob(sell_order.player_id, f"Sell Order Filled — {company.ticker_symbol}",
                                 f"Your listing of {sell_order.quantity:,} {company.ticker_symbol} "
                                 f"@ ${sell_order.limit_price:.2f} was fully sold at ${execution_price:.2f}.")
                    else:
                        sell_order.status = OrderStatus.PARTIAL.value
                        _push_ob(sell_order.player_id, f"Partial Fill — {company.ticker_symbol}",
                                 f"{trade_quantity:,} of {sell_order.quantity:,} {company.ticker_symbol} "
                                 f"sold @ ${execution_price:.2f}. Listing still active.")
                
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

        # Calculate commissions (reduced by city market_fee_reduction buff)
        _buyer_fee_mult = _seller_fee_mult = 1.0
        try:
            from city_projects import get_city_production_buffs
            _buyer_fee_mult = get_city_production_buffs(buyer_id).get("market_fee_multiplier", 1.0)
            _seller_fee_mult = get_city_production_buffs(seller_id).get("market_fee_multiplier", 1.0)
        except Exception:
            pass
        buyer_commission = total_value * EQUITY_TRADE_COMMISSION * _buyer_fee_mult
        seller_commission = total_value * EQUITY_TRADE_COMMISSION * _seller_fee_mult
        
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
                margin_multiplier_used=buy_order.margin_multiplier,
                first_held_at=datetime.utcnow(),
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
            try:
                from reserve_banks import convert_to_legal_tender
                convert_to_legal_tender(buyer_id, cash_to_release)
            except Exception as _ex:
                print(f"[OrderBook] partial-fill refund error: {_ex}")

        # Pay commission (deduct from buyer's legal tender)
        if buyer_commission > 0:
            try:
                from reserve_banks import spend_player_funds
                spend_player_funds(buyer_id, buyer_commission)
            except Exception as _ex:
                print(f"[OrderBook] commission deduct error: {_ex}")

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
        
        # Pay seller proceeds in their legal tender (no double-credit)
        proceeds = total_value - seller_commission
        try:
            from reserve_banks import convert_to_legal_tender
            convert_to_legal_tender(seller_id, proceeds)
        except Exception as _ex:
            print(f"[OrderBook] seller credit error: {_ex}")
            try:
                from reserve_banks import credit_usd
                credit_usd(seller_id, proceeds)
            except Exception:
                pass

        # Log share sale and payment
        log_transaction(
            seller_id,
            "share_sell",
            "share",
            -quantity,
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
            # Release unfilled portion of reserved cash back to player's legal tender
            unfilled_quantity = order.quantity - order.filled_quantity
            cash_per_share = order.reserved_cash / order.quantity
            cash_to_release = cash_per_share * unfilled_quantity
            if cash_to_release > 0:
                try:
                    from reserve_banks import convert_to_legal_tender
                    convert_to_legal_tender(player_id, cash_to_release)
                except Exception as _ex:
                    print(f"[OrderBook] cancel refund error: {_ex}")
        
        # Note: For sell orders, shares are already in player's position
        # just marked as reserved by the order existing
        
        order.status = OrderStatus.CANCELLED.value
        db.commit()

        try:
            from banks.brokerage_firm import CompanyShares as _CS
            _comp = db.query(_CS).filter(_CS.id == order.company_shares_id).first()
            _ticker = _comp.ticker_symbol if _comp else "?"
        except Exception:
            _ticker = "?"
        _side = "buy" if order.order_side == OrderSide.BUY.value else "sell"
        _push_ob(player_id, f"Order Cancelled — {_ticker}",
                 f"Your {_side} order for {order.quantity:,} {_ticker} has been cancelled"
                 + (" and reserved funds released." if _side == "buy" else "."))

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

                try:
                    from reserve_banks import convert_to_legal_tender
                    convert_to_legal_tender(order.player_id, cash_to_release)
                except Exception as _ex:
                    print(f"[OrderBook] expiry refund error: {_ex}")

            order.status = OrderStatus.EXPIRED.value

            # Notify the player — look up ticker for the message
            try:
                from banks.brokerage_firm import CompanyShares as _CS
                _comp = db.query(_CS).filter(_CS.id == order.company_shares_id).first()
                _ticker = _comp.ticker_symbol if _comp else "?"
            except Exception:
                _ticker = "?"
            _unfilled = order.quantity - order.filled_quantity
            if order.order_side == OrderSide.BUY.value:
                _push_ob(order.player_id, f"Buy Order Expired — {_ticker}",
                         f"Your buy order for {_unfilled:,} {_ticker} expired unfilled. "
                         f"Reserved funds have been released.")
            else:
                _push_ob(order.player_id, f"Sell Order Expired — {_ticker}",
                         f"Your sell order for {_unfilled:,} {_ticker} expired unfilled.")
        
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


# Re-match resting equity orders only every N ticks, not every tick. Real crosses are
# matched SYNCHRONOUSLY when an order is placed (place_limit_order / place_market_order,
# which both call match_orders before returning — and the player_place_* wrappers route
# through them). Two resting orders that don't cross will never cross until a new order
# arrives, so the per-tick sweep was re-proving non-crosses for every active company —
# each company opening its own DB session (N+1 sessions/tick). Sweep every N ticks
# (~30s @ 5s tick) keeps the safety net for orders that bypassed placement (admin tools,
# restores, migrations) while cutting that churn ~6×. Shares the markets' env knob.
_MATCH_SWEEP_INTERVAL = max(1, int(os.environ.get("MARKET_MATCH_SWEEP_INTERVAL", "6")))


def tick(current_tick: int):
    """
    Order book tick handler.

    Processes:
    - Order matching for all active companies (throttled — see _MATCH_SWEEP_INTERVAL)
    - Order expiry
    """
    do_sweep  = (current_tick % _MATCH_SWEEP_INTERVAL == 0)
    do_expire = (current_tick % 60 == 0)
    if not (do_sweep or do_expire):
        return   # nothing to do this tick — don't even check out a DB session

    if do_sweep:
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
    if do_expire:
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
