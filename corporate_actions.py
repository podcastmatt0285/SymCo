"""
corporate_actions.py - Automated Corporate Actions for Wadsworth Brokerage Firm

Adds three automated corporate finance actions that founders configure at IPO:

1. BUYBACKS - Company automatically repurchases shares to support price
2. STOCK SPLITS - Automatically split shares when price gets too high
3. SECONDARY OFFERINGS - Issue new shares when company needs capital

Each action is configured with triggers and limits during IPO creation,
then executed automatically by the Firm's tick handler.
"""

import threading
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from enum import Enum

from sqlalchemy import Column, String, Float, DateTime, Integer, BigInteger, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from stats_ux import log_transaction
# Import from existing brokerage firm
from banks.brokerage_firm import (
    get_db, Base, CompanyShares, ShareholderPosition, 
    BANK_PLAYER_ID, BANK_NAME, get_firm_entity, firm_deduct_cash, firm_add_cash,
    modify_credit_score, record_price
)
from banks.brokerage_order_book import place_market_order, OrderSide

# ==========================
# CONSTANTS
# ==========================

# Buyback limits
MAX_BUYBACK_PER_TICK = 0.001  # Max 0.1% of outstanding shares per tick
MAX_BUYBACK_TREASURY_RATIO = 0.30  # Max 30% of shares can be in treasury
BUYBACK_FIRM_FEE = 0.002  # 0.2% fee to Firm

# Split ratios
VALID_SPLIT_RATIOS = [2, 3, 4, 5, 10]  # 2:1, 3:1, etc.
SPLIT_COOLDOWN_DAYS = 90  # Must wait 90 days between splits

# Secondary offering limits
MAX_DILUTION_PER_OFFERING = 0.20  # Max 20% dilution per offering
SECONDARY_FIRM_FEE = 0.03  # 3% underwriting fee
SECONDARY_COOLDOWN_DAYS = 180  # Must wait 180 days between offerings

# ==========================
# ENUMS
# ==========================

class BuybackTrigger(str, Enum):
    PRICE_DROP = "price_drop"  # When price drops X% below target
    EARNINGS_SURPLUS = "earnings_surplus"  # When company has excess cash
    SCHEDULE = "schedule"  # Every N ticks
    MANUAL = "manual"  # Founder manually triggers

class SplitTrigger(str, Enum):
    PRICE_THRESHOLD = "price_threshold"  # When price exceeds $X
    TRADING_VOLUME = "trading_volume"  # When avg volume drops (price too high)
    MANUAL = "manual"

class OfferingTrigger(str, Enum):
    CASH_NEED = "cash_need"  # When founder cash drops below X
    EXPANSION = "expansion"  # To fund business expansion
    MANUAL = "manual"

class ActionStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

# ==========================
# DATABASE MODELS
# ==========================

class BuybackProgram(Base):
    """
    Automated share buyback program.
    Company repurchases its own shares from the market.
    """
    __tablename__ = "buyback_programs"
    
    id = Column(Integer, primary_key=True, index=True)
    company_shares_id = Column(Integer, index=True, nullable=False)
    
    # Configuration
    trigger_type = Column(String, nullable=False)  # BuybackTrigger enum
    trigger_params = Column(JSON, nullable=False)  # Specific parameters
    
    # Example trigger_params:
    # {"price_drop_pct": 0.15, "target_price": 10.0}  # Buy when 15% below $10
    # {"surplus_threshold": 50000}  # Buy when founder has $50k+ surplus
    # {"schedule_ticks": 3600}  # Buy every hour
    
    # Limits
    max_shares_to_buy = Column(BigInteger, nullable=False)  # Total program size
    max_price_per_share = Column(Float, nullable=False)  # Won't buy above this
    max_treasury_pct = Column(Float, default=0.30)  # Max % to hold in treasury
    
    # Execution
    shares_bought = Column(BigInteger, default=0)
    total_spent = Column(Float, default=0.0)
    average_buy_price = Column(Float, default=0.0)
    last_execution = Column(DateTime, nullable=True)

    # Status
    status = Column(String, default=ActionStatus.ACTIVE.value)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Treasury shares (bought but not retired)
    treasury_shares = Column(BigInteger, default=0)


class StockSplitRule(Base):
    """
    Automated stock split rule.
    Splits shares when price gets too high for retail investors.
    """
    __tablename__ = "stock_split_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    company_shares_id = Column(Integer, index=True, nullable=False)
    
    # Configuration
    trigger_type = Column(String, nullable=False)  # SplitTrigger enum
    trigger_params = Column(JSON, nullable=False)
    
    # Example trigger_params:
    # {"price_threshold": 100.0, "split_ratio": 2}  # 2:1 split at $100
    # {"avg_volume_drop_pct": 0.50, "min_price": 50.0}  # Split if volume drops 50%
    
    split_ratio = Column(Integer, nullable=False)  # 2, 3, 5, 10
    
    # Execution tracking
    last_split_date = Column(DateTime, nullable=True)
    total_splits_executed = Column(Integer, default=0)
    
    # Status
    status = Column(String, default=ActionStatus.ACTIVE.value)
    is_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class SecondaryOffering(Base):
    """
    Automated secondary share offering.
    Issues new shares when company needs capital.
    """
    __tablename__ = "secondary_offerings"
    
    id = Column(Integer, primary_key=True, index=True)
    company_shares_id = Column(Integer, index=True, nullable=False)
    
    # Configuration
    trigger_type = Column(String, nullable=False)  # OfferingTrigger enum
    trigger_params = Column(JSON, nullable=False)
    
    # Example trigger_params:
    # {"cash_threshold": 10000}  # Offer shares when cash below $10k
    # {"business_count_trigger": 5}  # Offer when player has 5+ businesses (expansion)
    
    # Offering size
    shares_to_issue = Column(BigInteger, nullable=False)
    min_price_per_share = Column(Float, nullable=False)  # Won't sell below this
    
    # Execution
    shares_issued = Column(Integer, default=0)
    total_raised = Column(Float, default=0.0)
    average_sell_price = Column(Float, default=0.0)
    last_offering_date = Column(DateTime, nullable=True)
    
    # Dilution tracking
    dilution_pct = Column(Float, default=0.0)  # % of ownership diluted
    
    # Status
    status = Column(String, default=ActionStatus.ACTIVE.value)
    is_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class CorporateActionHistory(Base):
    """Transaction log for all corporate actions."""
    __tablename__ = "corporate_action_history"
    
    id = Column(Integer, primary_key=True, index=True)
    company_shares_id = Column(Integer, index=True, nullable=False)
    action_type = Column(String, nullable=False)  # buyback, split, offering
    
    # Details
    shares_affected = Column(BigInteger, nullable=False)
    price_per_share = Column(Float, nullable=True)
    total_value = Column(Float, nullable=True)
    
    description = Column(String, nullable=True)
    executed_at = Column(DateTime, default=datetime.utcnow)


# ==========================
# BUYBACK FUNCTIONS
# ==========================

def create_buyback_program(
    company_shares_id: int,
    trigger_type: BuybackTrigger,
    trigger_params: dict,
    max_shares_to_buy: int,
    max_price_per_share: float
) -> Optional[BuybackProgram]:
    """
    Create an automated buyback program.
    
    Example configurations:
    
    Price Support Buyback:
    trigger_type = PRICE_DROP
    trigger_params = {
        "target_price": 10.0,
        "drop_threshold_pct": 0.15  # Buy when 15% below target
    }
    
    Earnings Surplus Buyback:
    trigger_type = EARNINGS_SURPLUS
    trigger_params = {
        "surplus_threshold": 50000  # Buy when founder has $50k+ available
    }
    
    Scheduled Buyback:
    trigger_type = SCHEDULE
    trigger_params = {
        "interval_ticks": 3600  # Buy every hour
    }
    """
    db = get_db()
    try:
        company = db.query(CompanyShares).filter(
            CompanyShares.id == company_shares_id
        ).first()
        
        if not company:
            return None
        
        # Validate limits
        max_allowed = int(company.shares_outstanding * MAX_BUYBACK_TREASURY_RATIO)
        if max_shares_to_buy > max_allowed:
            print(f"[{BANK_NAME}] Buyback program too large: max {max_allowed} shares")
            return None
        
        program = BuybackProgram(
            company_shares_id=company_shares_id,
            trigger_type=trigger_type.value,
            trigger_params=trigger_params,
            max_shares_to_buy=max_shares_to_buy,
            max_price_per_share=max_price_per_share,
            status=ActionStatus.ACTIVE.value
        )
        
        db.add(program)
        db.commit()
        db.refresh(program)
        
        print(f"[{BANK_NAME}] 📦 BUYBACK PROGRAM: Created for {company.ticker_symbol}")
        print(f"  → Trigger: {trigger_type.value}")
        print(f"  → Max shares: {max_shares_to_buy:,}")
        print(f"  → Max price: ${max_price_per_share:.2f}")
        
        return program
    finally:
        db.close()


def check_and_execute_buyback(program_id: int) -> bool:
    """
    Check if buyback should execute and do it if conditions met.
    Returns True if buyback executed.
    """
    db = get_db()
    try:
        program = db.query(BuybackProgram).filter(
            BuybackProgram.id == program_id
        ).first()
        
        if not program or program.status != ActionStatus.ACTIVE.value:
            return False
        
        # Check if program complete
        if program.shares_bought >= program.max_shares_to_buy:
            program.status = ActionStatus.COMPLETED.value
            program.completed_at = datetime.utcnow()
            db.commit()
            return False
        
        company = db.query(CompanyShares).filter(
            CompanyShares.id == program.company_shares_id
        ).first()
        
        if not company:
            return False
        
        # Check trigger condition
        should_buy = False
        
        if program.trigger_type == BuybackTrigger.PRICE_DROP.value:
            target_price = program.trigger_params.get("target_price", company.ipo_price)
            drop_threshold = program.trigger_params.get("drop_threshold_pct", 0.15)
            trigger_price = target_price * (1 - drop_threshold)
            
            if company.current_price < trigger_price:
                should_buy = True
                print(f"[{BANK_NAME}] 📉 BUYBACK TRIGGER: {company.ticker_symbol} at ${company.current_price:.2f} " +
                      f"(below ${trigger_price:.2f})")
        
        elif program.trigger_type == BuybackTrigger.EARNINGS_SURPLUS.value:
            surplus_threshold = program.trigger_params.get("surplus_threshold", 50000)
            
            from auth import Player, get_db as get_auth_db
            auth_db = get_auth_db()
            try:
                founder = auth_db.query(Player).filter(Player.id == company.founder_id).first()
                from reserve_banks import can_afford_usd
                if founder and can_afford_usd(founder.id, surplus_threshold):
                    should_buy = True
                    print(f"[{BANK_NAME}] 💰 BUYBACK TRIGGER: Founder has sufficient funds for surplus_threshold ${surplus_threshold:,.2f}")
            finally:
                auth_db.close()
        
        elif program.trigger_type == BuybackTrigger.SCHEDULE.value:
            interval = program.trigger_params.get("interval_ticks", 3600)
            if program.last_execution is None:
                should_buy = True
            else:
                elapsed_seconds = (datetime.utcnow() - program.last_execution).total_seconds()
                should_buy = elapsed_seconds >= (interval * 5)  # 5 seconds per tick
        
        if not should_buy:
            return False
        
        # Check price limit
        if company.current_price > program.max_price_per_share:
            print(f"[{BANK_NAME}] BUYBACK SKIPPED: Price ${company.current_price:.2f} " +
                  f"above limit ${program.max_price_per_share:.2f}")
            return False
        
        # Calculate shares to buy this tick
        remaining = program.max_shares_to_buy - program.shares_bought
        max_per_tick = max(1, int(company.shares_outstanding * MAX_BUYBACK_PER_TICK))
        shares_to_buy = min(remaining, max_per_tick)
        
        if shares_to_buy < 1:
            return False
        
        # Check treasury limit
        current_treasury_pct = (program.treasury_shares + shares_to_buy) / company.shares_outstanding
        if current_treasury_pct > program.max_treasury_pct:
            print(f"[{BANK_NAME}] BUYBACK PAUSED: Treasury limit reached")
            program.status = ActionStatus.PAUSED.value
            db.commit()
            return False
        
        # Calculate cost
        cost = shares_to_buy * company.current_price
        fee = cost * BUYBACK_FIRM_FEE
        total_cost = cost + fee
        
        # Check founder has sufficient funds (trade cost + firm fee).
        from auth import Player, get_db as get_auth_db
        auth_db = get_auth_db()
        try:
            founder = auth_db.query(Player).filter(Player.id == company.founder_id).first()
            from reserve_banks import can_afford_usd
            if not founder or not can_afford_usd(founder.id, total_cost):
                print(f"[{BANK_NAME}] BUYBACK SKIPPED: Insufficient founder funds")
                return False
        finally:
            auth_db.close()

        # Record founder's share position before the order so we can measure
        # the actual fill.  Place the order under the founder's ID so the
        # trading engine handles all cash deductions and partial-fill refunds
        # naturally — no black hole where the firm's system account pockets
        # the unspent reserved cash.
        old_founder_position = db.query(ShareholderPosition).filter(
            ShareholderPosition.player_id == company.founder_id,
            ShareholderPosition.company_shares_id == company.id
        ).first()
        old_founder_shares = old_founder_position.shares_owned if old_founder_position else 0

        success = place_market_order(
            player_id=company.founder_id,
            company_shares_id=company.id,
            side=OrderSide.BUY,
            quantity=shares_to_buy
        )

        if success:
            # Determine how many shares the founder actually acquired.
            db.expire_all()
            new_founder_position = db.query(ShareholderPosition).filter(
                ShareholderPosition.player_id == company.founder_id,
                ShareholderPosition.company_shares_id == company.id
            ).first()
            actual_bought = max(0, (new_founder_position.shares_owned if new_founder_position else 0) - old_founder_shares)

            if actual_bought > 0:
                # Transfer shares from founder into treasury.
                new_founder_position.shares_owned -= actual_bought

                actual_cost = actual_bought * company.current_price

                # Charge the firm fee directly from the founder.
                auth_db = get_auth_db()
                try:
                    founder = auth_db.query(Player).filter(Player.id == company.founder_id).first()
                    if founder:
                        from reserve_banks import spend_player_funds
                        ok, _ = spend_player_funds(founder.id, fee)
                        if ok:
                            auth_db.commit()
                finally:
                    auth_db.close()

                program.shares_bought += actual_bought
                program.total_spent += actual_cost
                program.average_buy_price = program.total_spent / program.shares_bought if program.shares_bought > 0 else 0
                program.treasury_shares += actual_bought
                program.last_execution = datetime.utcnow()

                firm_add_cash(fee, "buyback_fee", f"Buyback fee for {company.ticker_symbol}", company.founder_id)

                company.shares_in_float -= actual_bought
                company.shares_held_by_firm += actual_bought

                log_corporate_action(
                    company_shares_id=company.id,
                    action_type="buyback",
                    shares_affected=actual_bought,
                    price_per_share=company.current_price,
                    total_value=actual_cost,
                    description=f"Buyback executed: {program.trigger_type}"
                )

                db.commit()

                print(f"[{BANK_NAME}] BUYBACK EXECUTED: {actual_bought}/{shares_to_buy} {company.ticker_symbol} @ ${company.current_price:.2f}")
                print(f"  → Actual cost: ${actual_cost:,.2f} (Fee: ${fee:.2f})")
                print(f"  → Progress: {program.shares_bought}/{program.max_shares_to_buy}")

                _push_corp(company.founder_id, f"Buyback Executed — {company.ticker_symbol}",
                           f"Bought back {actual_bought:,} {company.ticker_symbol} shares @ ${company.current_price:.2f} "
                           f"(cost ${actual_cost:,.2f}). Progress: {program.shares_bought:,}/{program.max_shares_to_buy:,} shares.")

            return True
        else:
            print(f"[{BANK_NAME}] BUYBACK FAILED: Market order unsuccessful")
            return False
    
    except Exception as e:
        print(f"[{BANK_NAME}] Buyback error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


# ==========================
# STOCK SPLIT FUNCTIONS
# ==========================

def create_stock_split_rule(
    company_shares_id: int,
    trigger_type: SplitTrigger,
    trigger_params: dict,
    split_ratio: int
) -> Optional[StockSplitRule]:
    """
    Create an automated stock split rule.
    
    Example configurations:
    
    Price Threshold Split:
    trigger_type = PRICE_THRESHOLD
    trigger_params = {
        "price_threshold": 100.0  # Split when price hits $100
    }
    split_ratio = 2  # 2:1 split
    
    Trading Volume Split:
    trigger_type = TRADING_VOLUME
    trigger_params = {
        "volume_drop_pct": 0.50,  # Volume dropped 50% from avg
        "min_price": 50.0  # Only if price above $50
    }
    split_ratio = 3  # 3:1 split
    """
    if split_ratio not in VALID_SPLIT_RATIOS:
        print(f"[{BANK_NAME}] Invalid split ratio: {split_ratio}")
        return None
    
    db = get_db()
    try:
        rule = StockSplitRule(
            company_shares_id=company_shares_id,
            trigger_type=trigger_type.value,
            trigger_params=trigger_params,
            split_ratio=split_ratio,
            status=ActionStatus.ACTIVE.value
        )
        
        db.add(rule)
        db.commit()
        db.refresh(rule)
        
        company = db.query(CompanyShares).filter(CompanyShares.id == company_shares_id).first()
        print(f"[{BANK_NAME}] ✂️ SPLIT RULE: Created for {company.ticker_symbol if company else 'company'}")
        print(f"  → Trigger: {trigger_type.value}")
        print(f"  → Ratio: {split_ratio}:1")
        
        return rule
    finally:
        db.close()


def check_and_execute_split(rule_id: int) -> bool:
    """
    Check if split should execute and do it if conditions met.
    Returns True if split executed.
    """
    db = get_db()
    try:
        rule = db.query(StockSplitRule).filter(
            StockSplitRule.id == rule_id
        ).first()
        
        if not rule or rule.status != ActionStatus.ACTIVE.value or not rule.is_enabled:
            return False
        
        # Check cooldown
        if rule.last_split_date:
            days_since = (datetime.utcnow() - rule.last_split_date).days
            if days_since < SPLIT_COOLDOWN_DAYS:
                return False
        
        company = db.query(CompanyShares).filter(
            CompanyShares.id == rule.company_shares_id
        ).first()
        
        if not company:
            return False
        
        # Check trigger condition
        should_split = False
        
        if rule.trigger_type == SplitTrigger.PRICE_THRESHOLD.value:
            threshold = rule.trigger_params.get("price_threshold", 100.0)
            
            if company.current_price >= threshold:
                should_split = True
                print(f"[{BANK_NAME}] 📈 SPLIT TRIGGER: {company.ticker_symbol} at ${company.current_price:.2f}")
        
        elif rule.trigger_type == SplitTrigger.TRADING_VOLUME.value:
            # Would need volume tracking - simplified
            min_price = rule.trigger_params.get("min_price", 50.0)
            if company.current_price >= min_price:
                should_split = True
        
        if not should_split:
            return False
        
        # Execute the split
        old_price = company.current_price
        old_shares = company.shares_outstanding
        ratio = rule.split_ratio
        
        # Update all shareholder positions
        positions = db.query(ShareholderPosition).filter(
            ShareholderPosition.company_shares_id == company.id
        ).all()
        
        for position in positions:
            position.shares_owned *= ratio
            position.shares_available_to_lend *= ratio
            position.shares_lent_out *= ratio
            position.average_cost_basis /= ratio
            
            if position.is_margin_position:
                position.margin_shares *= ratio
        
        # Update company
        company.shares_outstanding *= ratio
        company.total_shares_authorized *= ratio
        company.shares_in_float *= ratio
        company.shares_held_by_founder *= ratio
        company.shares_held_by_firm *= ratio
        
        # Update prices
        company.current_price /= ratio
        company.ipo_price /= ratio
        company.high_52_week /= ratio
        company.low_52_week /= ratio
        
        # Update rule
        rule.last_split_date = datetime.utcnow()
        rule.total_splits_executed += 1
        
        # Log action
        log_corporate_action(
            company_shares_id=company.id,
            action_type="split",
            shares_affected=old_shares * (ratio - 1),  # New shares created
            price_per_share=company.current_price,
            description=f"{ratio}:1 stock split"
        )
        
        # Capture shareholder IDs and post-split price before commit expires ORM objects
        _split_shareholder_ids = [p.player_id for p in positions if p.player_id > 0]
        _split_ticker = company.ticker_symbol
        _split_ratio = ratio
        _post_split_price = company.current_price  # already divided by ratio above

        db.commit()

        print(f"[{BANK_NAME}] ✂️ SPLIT EXECUTED: {_split_ticker} {_split_ratio}:1")
        print(f"  → Price: ${old_price:.2f} → ${_post_split_price:.2f}")

        # Notify all shareholders (including founder)
        try:
            for _pid in _split_shareholder_ids:
                _push_corp(_pid, f"Stock Split — {_split_ticker}",
                           f"{_split_ticker} executed a {_split_ratio}:1 split. "
                           f"Your shares multiplied ×{_split_ratio} and price adjusted to ${_post_split_price:.2f}.")
        except Exception:
            pass

        # Update credit (splits are positive events)
        modify_credit_score(company.founder_id, "stock_split_executed")
        
        return True
    
    except Exception as e:
        print(f"[{BANK_NAME}] Split error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


# ==========================
# SECONDARY OFFERING FUNCTIONS
# ==========================

def create_secondary_offering(
    company_shares_id: int,
    trigger_type: OfferingTrigger,
    trigger_params: dict,
    shares_to_issue: int,
    min_price_per_share: float
) -> Optional[SecondaryOffering]:
    """
    Create an automated secondary offering.
    
    Example configurations:
    
    Cash Need Offering:
    trigger_type = CASH_NEED
    trigger_params = {
        "cash_threshold": 10000  # Issue shares when cash below $10k
    }
    
    Expansion Offering:
    trigger_type = EXPANSION
    trigger_params = {
        "business_count": 5  # Issue when player has 5+ businesses
    }
    """
    db = get_db()
    try:
        company = db.query(CompanyShares).filter(
            CompanyShares.id == company_shares_id
        ).first()
        
        if not company:
            return None
        
        # Calculate dilution
        dilution = shares_to_issue / (company.shares_outstanding + shares_to_issue)
        
        if dilution > MAX_DILUTION_PER_OFFERING:
            print(f"[{BANK_NAME}] Offering too dilutive: {dilution*100:.1f}% (max {MAX_DILUTION_PER_OFFERING*100:.1f}%)")
            return None
        
        offering = SecondaryOffering(
            company_shares_id=company_shares_id,
            trigger_type=trigger_type.value,
            trigger_params=trigger_params,
            shares_to_issue=shares_to_issue,
            min_price_per_share=min_price_per_share,
            dilution_pct=dilution,
            status=ActionStatus.ACTIVE.value
        )
        
        db.add(offering)
        db.commit()
        db.refresh(offering)
        
        print(f"[{BANK_NAME}] 📢 SECONDARY OFFERING: Created for {company.ticker_symbol}")
        print(f"  → Trigger: {trigger_type.value}")
        print(f"  → Shares: {shares_to_issue:,} ({dilution*100:.1f}% dilution)")
        print(f"  → Min price: ${min_price_per_share:.2f}")
        
        return offering
    finally:
        db.close()


def check_and_execute_offering(offering_id: int) -> bool:
    """
    Check if offering should execute and do it if conditions met.
    Returns True if offering executed.
    """
    db = get_db()
    try:
        offering = db.query(SecondaryOffering).filter(
            SecondaryOffering.id == offering_id
        ).first()
        
        if not offering or offering.status != ActionStatus.ACTIVE.value or not offering.is_enabled:
            return False
        
        # Check cooldown
        if offering.last_offering_date:
            days_since = (datetime.utcnow() - offering.last_offering_date).days
            if days_since < SECONDARY_COOLDOWN_DAYS:
                return False
        
        company = db.query(CompanyShares).filter(
            CompanyShares.id == offering.company_shares_id
        ).first()
        
        if not company:
            return False
        
        # Check trigger condition
        should_offer = False
        
        if offering.trigger_type == OfferingTrigger.CASH_NEED.value:
            threshold = offering.trigger_params.get("cash_threshold", 10000)
            
            from auth import Player, get_db as get_auth_db
            auth_db = get_auth_db()
            try:
                founder = auth_db.query(Player).filter(Player.id == company.founder_id).first()
                from reserve_banks import can_afford_usd
                if founder and not can_afford_usd(founder.id, threshold):
                    should_offer = True
                    print(f"[{BANK_NAME}] 💵 OFFERING TRIGGER: Founder below ${threshold:,.2f} threshold")
            finally:
                auth_db.close()
        
        elif offering.trigger_type == OfferingTrigger.EXPANSION.value:
            business_count = offering.trigger_params.get("business_count", 5)
            
            from business import Business, SessionLocal as BizSession
            biz_db = BizSession()
            try:
                count = biz_db.query(Business).filter(
                    Business.owner_id == company.founder_id,
                    Business.is_active == True
                ).count()
                
                if count >= business_count:
                    should_offer = True
                    print(f"[{BANK_NAME}] 🏭 OFFERING TRIGGER: {count} businesses")
            finally:
                biz_db.close()
        
        if not should_offer:
            return False
        
        # Check price floor
        if company.current_price < offering.min_price_per_share:
            print(f"[{BANK_NAME}] OFFERING DELAYED: Price ${company.current_price:.2f} " +
                  f"below minimum ${offering.min_price_per_share:.2f}")
            return False
        
        # Calculate offering details
        shares_to_issue = offering.shares_to_issue - offering.shares_issued
        offering_value = shares_to_issue * company.current_price
        firm_fee = offering_value * SECONDARY_FIRM_FEE
        net_to_founder = offering_value - firm_fee
        
        # Check Firm can underwrite
        if not firm_deduct_cash(firm_fee, "secondary_offering_fee", 
                               f"Underwriting {company.ticker_symbol} secondary"):
            print(f"[{BANK_NAME}] OFFERING FAILED: Firm cannot underwrite")
            return False
        
        # Issue new shares
        company.shares_outstanding += shares_to_issue
        company.total_shares_authorized += shares_to_issue
        company.shares_in_float += shares_to_issue
        
        # Give founder the proceeds
        from auth import Player, get_db as get_auth_db
        auth_db = get_auth_db()
        try:
            founder = auth_db.query(Player).filter(Player.id == company.founder_id).first()
            if founder:
                try:
                    from reserve_banks import convert_to_legal_tender
                    convert_to_legal_tender(founder.id, net_to_founder)
                except Exception:
                    founder.cash_balance += net_to_founder
                auth_db.commit()
        finally:
            auth_db.close()

        # Firm keeps fee
        firm_add_cash(firm_fee, "secondary_offering_fee", 
                     f"Secondary offering fee for {company.ticker_symbol}", company.founder_id)
        
        # Update offering
        offering.shares_issued += shares_to_issue
        offering.total_raised += net_to_founder
        offering.average_sell_price = company.current_price
        offering.last_offering_date = datetime.utcnow()
        offering.status = ActionStatus.COMPLETED.value
        
        # Log action
        log_corporate_action(
            company_shares_id=company.id,
            action_type="secondary_offering",
            shares_affected=shares_to_issue,
            price_per_share=company.current_price,
            total_value=offering_value,
            description=f"Secondary offering: {shares_to_issue:,} shares"
        )
        
        db.commit()
        
        print(f"[{BANK_NAME}] 📢 SECONDARY OFFERING EXECUTED: {company.ticker_symbol}")
        print(f"  → Shares issued: {shares_to_issue:,}")
        print(f"  → Price: ${company.current_price:.2f}")
        print(f"  → Net to founder: ${net_to_founder:,.2f}")
        print(f"  → Dilution: {offering.dilution_pct*100:.1f}%")

        # Notify founder
        _push_corp(company.founder_id, f"Secondary Offering Executed — {company.ticker_symbol}",
                   f"{shares_to_issue:,} new shares issued at ${company.current_price:.2f}. "
                   f"Net proceeds: ${net_to_founder:,.2f} ({offering.dilution_pct*100:.1f}% dilution).")

        # Notify existing shareholders of dilution
        try:
            _sh_positions = db.query(ShareholderPosition).filter(
                ShareholderPosition.company_shares_id == company.id,
                ShareholderPosition.player_id != company.founder_id,
                ShareholderPosition.shares_owned > 0
            ).all()
            for _sh in _sh_positions:
                if _sh.player_id > 0:
                    _push_corp(_sh.player_id, f"Share Dilution — {company.ticker_symbol}",
                               f"{company.ticker_symbol} issued {shares_to_issue:,} new shares "
                               f"({offering.dilution_pct*100:.1f}% dilution). New price: ${company.current_price:.2f}.")
        except Exception:
            pass

        # Dilution hurts credit slightly
        modify_credit_score(company.founder_id, "secondary_offering_dilution")
        
        return True
    
    except Exception as e:
        print(f"[{BANK_NAME}] Offering error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

def log_dividend_payment(shareholder_id: int, company_ticker: str, amount: float):
    """
    Helper function to log dividend payments.
    Call this whenever dividends are paid to shareholders.
    """
    log_transaction(
        shareholder_id,
        "cash_in",
        "money",
        amount,
        f"Dividend: {company_ticker}",
        company_ticker
    )

# ==========================
# UTILITY FUNCTIONS
# ==========================

def log_corporate_action(
    company_shares_id: int,
    action_type: str,
    shares_affected: int,
    price_per_share: float = None,
    total_value: float = None,
    description: str = None
):
    """Log a corporate action for audit trail."""
    db = get_db()
    try:
        log = CorporateActionHistory(
            company_shares_id=company_shares_id,
            action_type=action_type,
            shares_affected=shares_affected,
            price_per_share=price_per_share,
            total_value=total_value,
            description=description
        )
        db.add(log)
        db.commit()
    finally:
        db.close()


# ==========================
# NEW CONSTANTS
# ==========================

TAX_VOUCHER_RATE = 0.1375
VALID_REVERSE_SPLIT_RATIOS = [2, 3, 5, 10]
ACQUISITION_OFFER_DAYS = 7
DIFFUSE_RETURN_DAYS = 30
BANKRUPTCY_RESTART_CASH = 20000.0
BANKRUPTCY_RED_Q_DAYS = 30

# Acquisition term / lock-up options
ACQUISITION_DEFAULT_LOCKUP_DAYS = 7       # minimum hold before diffuse allowed
ACQUISITION_TERM_OPTIONS = [None, 30, 60, 90, 180, 365]  # None = perpetual

# Income transaction types included in the daily acquisition sweep.
# Covers all real business earnings: sales, market activity, bonds, dividends,
# P2P payments, crypto proceeds, city income, and district market sales.
ACQUISITION_INCOME_TYPES = [
    "retail_sale", "market_sell", "dividend",
    "bond_maturity", "bond_called", "bond_sell",
    "district_market_sell", "share_sell",
    "p2p_contract_payment", "crypto_sell",
    "city_application_income",
]
# Tax-like deductions subtracted before calculating the acquirer's share
ACQUISITION_TAX_TYPES = ["tax", "district_tax"]


# ==========================
# NEW MODELS
# ==========================

class ReverseSplitRecord(Base):
    __tablename__ = "reverse_split_records"
    id = Column(Integer, primary_key=True, index=True)
    company_shares_id = Column(Integer, index=True, nullable=False)
    ratio = Column(Integer, nullable=False)
    old_price = Column(Float, nullable=False)
    new_price = Column(Float, nullable=False)
    old_shares_outstanding = Column(BigInteger, nullable=False)
    new_shares_outstanding = Column(BigInteger, nullable=False)
    executed_at = Column(DateTime, default=datetime.utcnow)
    executed_by = Column(Integer, nullable=False)


class SpecialDividendRecord(Base):
    __tablename__ = "special_dividend_records"
    id = Column(Integer, primary_key=True, index=True)
    company_shares_id = Column(Integer, index=True, nullable=False)
    total_amount = Column(Float, nullable=False)
    per_share_amount = Column(Float, nullable=False)
    shares_at_time = Column(BigInteger, nullable=False)
    vouchers_granted = Column(Float, nullable=False)
    paid_at = Column(DateTime, default=datetime.utcnow)
    paid_by = Column(Integer, nullable=False)


class TaxVoucher(Base):
    """Government tax voucher earned by paying special dividends. Redeemable for cash."""
    __tablename__ = "tax_vouchers"
    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, index=True, nullable=False)
    amount = Column(Float, nullable=False)
    granted_at = Column(DateTime, default=datetime.utcnow)
    source_dividend_id = Column(Integer, nullable=True)
    redeemed = Column(Boolean, default=False)
    redeemed_at = Column(DateTime, nullable=True)


class AcquisitionOffer(Base):
    """Offer to acquire up to 50% income stake in another player's business in exchange for shares."""
    __tablename__ = "acquisition_offers"
    id = Column(Integer, primary_key=True, index=True)
    offeror_id = Column(Integer, index=True, nullable=False)
    target_player_id = Column(Integer, index=True, nullable=False)
    offeror_company_id = Column(Integer, nullable=False)
    shares_offered = Column(Integer, nullable=False)
    stake_pct = Column(Float, nullable=False)
    status = Column(String, default="pending")  # pending/countered/accepted/rejected/expired/diffused
    notification_seen_offeror = Column(Boolean, default=False)
    notification_seen_target = Column(Boolean, default=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    responded_at = Column(DateTime, nullable=True)
    # Cash component — escrowed from offeror at creation, released on accept/reject
    cash_component = Column(Float, default=0.0)
    # Optional memo explaining the deal rationale
    offer_memo = Column(String, default='')
    # --- Gap 1: deal duration (None = perpetual) and lock-up period ---
    term_days = Column(Integer, nullable=True)           # None = perpetual
    lock_up_days = Column(Integer, default=ACQUISITION_DEFAULT_LOCKUP_DAYS)
    # Counter-offer terms proposed by the target (includes their preferred duration)
    counter_stake_pct = Column(Float, nullable=True)
    counter_shares = Column(Integer, nullable=True)
    counter_cash = Column(Float, default=0.0)
    counter_term_days = Column(Integer, nullable=True)   # None = keep original term
    counter_lock_up_days = Column(Integer, nullable=True)


class AcquisitionStake(Base):
    """Active income-sharing stake from an accepted acquisition."""
    __tablename__ = "acquisition_stakes"
    id = Column(Integer, primary_key=True, index=True)
    acquirer_id = Column(Integer, index=True, nullable=False)
    target_player_id = Column(Integer, index=True, nullable=False)
    stake_pct = Column(Float, nullable=False)
    shares_paid = Column(Integer, nullable=False)
    acquisition_offer_id = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_income_sweep = Column(DateTime, nullable=True)
    diffuse_initiated_at = Column(DateTime, nullable=True)
    # --- Gap 1 & 2: term + lock-up (copied from offer at acceptance) ---
    term_days = Column(Integer, nullable=True)           # None = perpetual
    lock_up_days = Column(Integer, default=ACQUISITION_DEFAULT_LOCKUP_DAYS)
    expires_at = Column(DateTime, nullable=True)         # created_at + term_days, or None


class DiffuseNotice(Base):
    """Exit notice: share-return demand (30-day deadline) or immediate cash buyout."""
    __tablename__ = "diffuse_notices"
    id = Column(Integer, primary_key=True, index=True)
    stake_id = Column(Integer, index=True, nullable=False)
    acquirer_id = Column(Integer, nullable=False)
    target_player_id = Column(Integer, nullable=False)
    shares_to_return = Column(Integer, nullable=False)
    share_value_at_notice = Column(Float, nullable=False)
    deadline_at = Column(DateTime, nullable=False)
    status = Column(String, default="pending")  # pending/returned/lien_created/buyout_paid/target_bought_out
    # --- Gap 3: diffuse type ---
    diffuse_type = Column(String, default="share_return")  # share_return | cash_buyout | target_buyout
    buyout_amount = Column(Float, nullable=True)           # cash paid in buyout scenarios
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    notification_seen_target = Column(Boolean, default=False)
    notification_seen_acquirer = Column(Boolean, default=False)


class StakeRenegotiation(Base):
    """Either party can propose amended stake terms on an active stake."""
    __tablename__ = "stake_renegotiations"
    id = Column(Integer, primary_key=True, index=True)
    stake_id = Column(Integer, index=True, nullable=False)
    proposed_by_player_id = Column(Integer, nullable=False)
    new_stake_pct = Column(Float, nullable=False)          # proposed new income %
    new_term_days = Column(Integer, nullable=True)         # None = keep current / extend perpetual
    note = Column(String, default='')                      # optional reason
    status = Column(String, default="pending")             # pending/accepted/rejected
    created_at = Column(DateTime, default=datetime.utcnow)
    responded_at = Column(DateTime, nullable=True)
    notification_seen_proposer = Column(Boolean, default=False)
    notification_seen_respondent = Column(Boolean, default=False)


class BankruptcyRecord(Base):
    """Bankruptcy filing — tracks red-Q period and liquidation totals."""
    __tablename__ = "bankruptcy_records"
    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, index=True, nullable=False)
    filed_at = Column(DateTime, default=datetime.utcnow)
    red_q_expires_at = Column(DateTime, nullable=False)
    total_assets_liquidated = Column(Float, default=0.0)
    total_debts_cleared = Column(Float, default=0.0)
    restart_cash = Column(Float, default=BANKRUPTCY_RESTART_CASH)
    is_active = Column(Boolean, default=True)


# ==========================
# REVERSE STOCK SPLIT
# ==========================

def execute_reverse_split(company_shares_id: int, founder_id: int, ratio: int) -> dict:
    """N:1 reverse split — every N shares become 1 share, price multiplies by N."""
    if ratio not in VALID_REVERSE_SPLIT_RATIOS:
        return {"ok": False, "error": f"Invalid ratio. Must be one of {VALID_REVERSE_SPLIT_RATIOS}"}
    db = get_db()
    try:
        company = db.query(CompanyShares).filter(
            CompanyShares.id == company_shares_id,
            CompanyShares.founder_id == founder_id
        ).first()
        if not company:
            return {"ok": False, "error": "Company not found or not owned by you"}
        old_price, old_shares = company.current_price, company.shares_outstanding
        positions = db.query(ShareholderPosition).filter(
            ShareholderPosition.company_shares_id == company_shares_id
        ).all()
        for pos in positions:
            pos.shares_owned = max(1, pos.shares_owned // ratio)
            pos.shares_available_to_lend = pos.shares_owned
            pos.shares_lent_out = max(0, pos.shares_lent_out // ratio)
            pos.average_cost_basis = pos.average_cost_basis * ratio
            if pos.is_margin_position:
                pos.margin_shares = max(0, pos.margin_shares // ratio)
        company.shares_outstanding = max(1, company.shares_outstanding // ratio)
        if hasattr(company, 'total_shares_authorized'):
            company.total_shares_authorized = max(1, company.total_shares_authorized // ratio)
        company.shares_in_float = max(0, company.shares_in_float // ratio)
        company.shares_held_by_founder = max(0, company.shares_held_by_founder // ratio)
        company.shares_held_by_firm = max(0, company.shares_held_by_firm // ratio)
        company.current_price = old_price * ratio
        company.ipo_price = company.ipo_price * ratio
        if company.high_52_week:
            company.high_52_week *= ratio
        if company.low_52_week:
            company.low_52_week *= ratio
        record = ReverseSplitRecord(
            company_shares_id=company_shares_id, ratio=ratio,
            old_price=old_price, new_price=company.current_price,
            old_shares_outstanding=old_shares, new_shares_outstanding=company.shares_outstanding,
            executed_by=founder_id
        )
        db.add(record)
        log_corporate_action(company_shares_id, "reverse_split", old_shares - company.shares_outstanding,
                             company.current_price,
                             description=f"1:{ratio} reverse split ${old_price:.2f}→${company.current_price:.2f}")
        db.commit()
        return {"ok": True, "new_price": company.current_price, "new_shares": company.shares_outstanding}
    except Exception as e:
        db.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        db.close()


# ==========================
# SPECIAL DIVIDENDS + TAX VOUCHERS
# ==========================

def pay_special_dividend(company_shares_id: int, founder_id: int, total_amount: float) -> dict:
    """
    Pay a one-time special dividend to all float shareholders.
    Founder receives TAX_VOUCHER_RATE * total_amount in TaxVoucher credits from the government.
    """
    if total_amount <= 0:
        return {"ok": False, "error": "Amount must be positive"}
    db = get_db()
    try:
        company = db.query(CompanyShares).filter(
            CompanyShares.id == company_shares_id,
            CompanyShares.founder_id == founder_id
        ).first()
        if not company:
            return {"ok": False, "error": "Company not found or not owned by you"}
        if company.shares_in_float <= 0:
            return {"ok": False, "error": "No shares in float"}

        from auth import Player, get_db as get_auth_db
        auth_db = get_auth_db()
        try:
            founder = auth_db.query(Player).filter(Player.id == founder_id).first()
            from reserve_banks import can_afford_usd, spend_player_funds
            if not founder or not can_afford_usd(founder_id, total_amount):
                return {"ok": False, "error": f"Insufficient funds (need ${total_amount:,.2f})"}
            ok, err = spend_player_funds(founder.id, total_amount)
            if not ok:
                return {"ok": False, "error": f"Payment failed: {err}"}
            auth_db.commit()
        finally:
            auth_db.close()

        per_share = total_amount / company.shares_in_float
        positions = db.query(ShareholderPosition).filter(
            ShareholderPosition.company_shares_id == company_shares_id,
            ShareholderPosition.player_id != founder_id
        ).all()
        distributed = 0.0
        auth_db2 = get_auth_db()
        try:
            for pos in positions:
                payout = pos.shares_owned * per_share
                if payout <= 0:
                    continue
                from banks.brokerage_firm import BANK_PLAYER_ID, firm_add_cash
                if pos.player_id == BANK_PLAYER_ID:
                    firm_add_cash(payout, "dividend",
                                  f"Special dividend: {company.ticker_symbol} (${per_share:.4f}/share × {pos.shares_owned:,})")
                    distributed += payout
                    continue
                holder = auth_db2.query(Player).filter(Player.id == pos.player_id).first()
                if holder:
                    try:
                        from reserve_banks import convert_to_legal_tender
                        convert_to_legal_tender(holder.id, payout)
                    except Exception as _ce:
                        print(f"[SpecialDividend] convert_to_legal_tender failed for player {pos.player_id}: {_ce}")
                    distributed += payout
                    log_transaction(pos.player_id, "dividend", "money", payout,
                                    f"Special dividend: {company.ticker_symbol} (${per_share:.4f}/share × {pos.shares_owned:,})")
                    _push_corp(pos.player_id, f"Dividend Received — {company.ticker_symbol}",
                               f"You received a special dividend of ${payout:,.2f} "
                               f"(${per_share:.4f}/share × {pos.shares_owned:,} shares).")
            auth_db2.commit()
        finally:
            auth_db2.close()

        voucher_amount = total_amount * TAX_VOUCHER_RATE
        div_record = SpecialDividendRecord(
            company_shares_id=company_shares_id, total_amount=total_amount,
            per_share_amount=per_share, shares_at_time=company.shares_in_float,
            vouchers_granted=voucher_amount, paid_by=founder_id
        )
        db.add(div_record)
        db.flush()
        voucher = TaxVoucher(player_id=founder_id, amount=voucher_amount, source_dividend_id=div_record.id)
        db.add(voucher)
        log_corporate_action(company_shares_id, "special_dividend", company.shares_in_float,
                             per_share, total_amount,
                             f"Special dividend ${per_share:.4f}/share — ${distributed:,.2f} total")
        log_transaction(founder_id, "corporate", "money", -total_amount,
                        f"Special dividend: {company.ticker_symbol} — earned ${voucher_amount:.2f} tax vouchers")
        db.commit()
        return {"ok": True, "per_share": per_share, "distributed": distributed, "vouchers_earned": voucher_amount}
    except Exception as e:
        db.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        db.close()


def get_tax_voucher_balance(player_id: int) -> float:
    db = get_db()
    try:
        vouchers = db.query(TaxVoucher).filter(
            TaxVoucher.player_id == player_id, TaxVoucher.redeemed == False
        ).all()
        return sum(v.amount for v in vouchers)
    finally:
        db.close()


def redeem_tax_vouchers(player_id: int, amount: float) -> dict:
    """Redeem tax vouchers for government cash payout."""
    if amount <= 0:
        return {"ok": False, "error": "Amount must be positive"}
    db = get_db()
    try:
        vouchers = db.query(TaxVoucher).filter(
            TaxVoucher.player_id == player_id, TaxVoucher.redeemed == False
        ).order_by(TaxVoucher.granted_at.asc()).all()
        total_available = sum(v.amount for v in vouchers)
        if total_available <= 0:
            return {"ok": False, "error": "No unredeemed vouchers"}
        amount = min(amount, total_available)
        redeemed_total = 0.0
        for v in vouchers:
            if redeemed_total >= amount:
                break
            take = min(v.amount, amount - redeemed_total)
            if take >= v.amount:
                v.redeemed = True
                v.redeemed_at = datetime.utcnow()
                redeemed_total += v.amount
            else:
                v.amount -= take
                new_v = TaxVoucher(player_id=player_id, amount=take,
                                   source_dividend_id=v.source_dividend_id,
                                   redeemed=True, redeemed_at=datetime.utcnow())
                db.add(new_v)
                redeemed_total += take
        from auth import Player, get_db as get_auth_db
        auth_db = get_auth_db()
        try:
            p = auth_db.query(Player).filter(Player.id == player_id).first()
            if p:
                try:
                    from reserve_banks import convert_to_legal_tender
                    convert_to_legal_tender(p.id, redeemed_total)
                except Exception as _ce:
                    print(f"[TaxVoucher] convert_to_legal_tender failed for player {player_id}: {_ce}")
                auth_db.commit()
        finally:
            auth_db.close()
        log_transaction(player_id, "tax_voucher", "money", redeemed_total,
                        f"Tax vouchers redeemed: ${redeemed_total:,.2f}")
        db.commit()
        return {"ok": True, "redeemed": redeemed_total, "remaining": total_available - redeemed_total}
    except Exception as e:
        db.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        db.close()


def _push_corp(player_id: int, title: str, body: str):
    """Fire a corporate push notification (non-blocking)."""
    def _send():
        try:
            from push_ux import send_push_notification
            send_push_notification(player_id, title, body,
                                   url="/corporate",
                                   notif_type="corporate",
                                   tag=f"corp-{player_id}-{title[:20]}")
        except Exception as e:
            print(f"[Corporate] Push error: {e}")
    threading.Thread(target=_send, daemon=True).start()


# ==========================
# ACQUISITION
# ==========================

def create_acquisition_offer(offeror_id: int, target_player_id: int,
                              offeror_company_id: int, shares_offered: int,
                              stake_pct: float, cash_component: float = 0.0,
                              offer_memo: str = '',
                              term_days: Optional[int] = None,
                              lock_up_days: int = ACQUISITION_DEFAULT_LOCKUP_DAYS) -> dict:
    """Offer shares (+ optional cash) in exchange for stake_pct (≤50%) of target's business income.
    term_days: None=perpetual; 30/60/90/180/365=time-limited (auto-closes, shares returned).
    lock_up_days: minimum hold period before acquirer can initiate diffuse (default 7).
    Cash component is escrowed immediately and returned if the offer is rejected/expired."""
    if not (0 < stake_pct <= 0.50):
        return {"ok": False, "error": "Stake must be 0%–50%"}
    if shares_offered <= 0:
        return {"ok": False, "error": "Must offer at least 1 share"}
    if offeror_id == target_player_id:
        return {"ok": False, "error": "Cannot acquire yourself"}
    if cash_component < 0:
        return {"ok": False, "error": "Cash component cannot be negative"}
    if term_days is not None and term_days not in ACQUISITION_TERM_OPTIONS[1:]:
        return {"ok": False, "error": f"Term must be one of {ACQUISITION_TERM_OPTIONS[1:]} days, or omit for perpetual"}
    lock_up_days = max(0, int(lock_up_days))

    # Escrow the cash component from the offeror before creating the offer
    if cash_component > 0:
        from reserve_banks import spend_player_funds
        _ok, _err = spend_player_funds(offeror_id, cash_component)
        if not _ok:
            return {"ok": False, "error": f"Insufficient cash for escrow: {_err}"}

    db = get_db()
    try:
        company = db.query(CompanyShares).filter(
            CompanyShares.id == offeror_company_id,
            CompanyShares.founder_id == offeror_id
        ).first()
        if not company:
            # Refund escrowed cash
            if cash_component > 0:
                _refund_cash_to(offeror_id, cash_component)
            return {"ok": False, "error": "Company not found or not owned by you"}
        pos = db.query(ShareholderPosition).filter(
            ShareholderPosition.company_shares_id == offeror_company_id,
            ShareholderPosition.player_id == offeror_id
        ).first()
        if not pos or pos.shares_owned < shares_offered:
            if cash_component > 0:
                _refund_cash_to(offeror_id, cash_component)
            return {"ok": False, "error": f"Insufficient shares (have {pos.shares_owned if pos else 0})"}
        existing = db.query(AcquisitionOffer).filter(
            AcquisitionOffer.offeror_id == offeror_id,
            AcquisitionOffer.target_player_id == target_player_id,
            AcquisitionOffer.status.in_(["pending", "countered"])
        ).first()
        if existing:
            if cash_component > 0:
                _refund_cash_to(offeror_id, cash_component)
            return {"ok": False, "error": "A pending offer to this player already exists"}
        expires_at = datetime.utcnow() + timedelta(days=ACQUISITION_OFFER_DAYS)
        offer = AcquisitionOffer(
            offeror_id=offeror_id, target_player_id=target_player_id,
            offeror_company_id=offeror_company_id, shares_offered=shares_offered,
            stake_pct=stake_pct, expires_at=expires_at,
            cash_component=cash_component, offer_memo=(offer_memo or '')[:500],
            term_days=term_days, lock_up_days=lock_up_days
        )
        db.add(offer)
        db.commit()
        db.refresh(offer)
        _share_value = company.current_price * shares_offered
        _ticker = company.ticker_symbol
        _offer_id = offer.id
    except Exception as e:
        db.rollback()
        if cash_component > 0:
            _refund_cash_to(offeror_id, cash_component)
        return {"ok": False, "error": str(e)}
    finally:
        db.close()

    cash_str = f" + ${cash_component:,.0f} cash" if cash_component > 0 else ""
    term_str = f" ({term_days}d term)" if term_days else " (perpetual)"
    _push_corp(target_player_id, "Acquisition Offer Received",
               f"Player #{offeror_id} ({_ticker}) offers {shares_offered:,} shares{cash_str} for {stake_pct*100:.1f}% income stake{term_str}")
    return {"ok": True, "offer_id": _offer_id,
            "share_value": _share_value,
            "expires_at": expires_at.isoformat()}


def _refund_cash_to(player_id: int, amount: float):
    """Internal helper: return escrowed cash to a player in their legal tender."""
    try:
        from reserve_banks import convert_to_legal_tender
        convert_to_legal_tender(player_id, amount)
    except Exception as _e:
        print(f"[Corporate Actions] Cash refund error for player {player_id}: {_e}")


def accept_acquisition_offer(offer_id: int, target_player_id: int) -> dict:
    """Target accepts offer — shares transfer, income stake begins."""
    db = get_db()
    try:
        offer = db.query(AcquisitionOffer).filter(
            AcquisitionOffer.id == offer_id,
            AcquisitionOffer.target_player_id == target_player_id,
            AcquisitionOffer.status == "pending"
        ).first()
        if not offer:
            return {"ok": False, "error": "Offer not found or already responded to"}
        if datetime.utcnow() > offer.expires_at:
            offer.status = "expired"
            _exp_offeror_id = offer.offeror_id
            _exp_stake_pct = offer.stake_pct
            _exp_cash = offer.cash_component or 0.0
            db.commit()
            if _exp_cash > 0:
                _refund_cash_to(_exp_offeror_id, _exp_cash)
            _push_corp(_exp_offeror_id, "Acquisition Offer Expired",
                       f"Your offer for a {_exp_stake_pct*100:.1f}% income stake expired without a response.")
            return {"ok": False, "error": "Offer expired"}

        offeror_pos = db.query(ShareholderPosition).filter(
            ShareholderPosition.company_shares_id == offer.offeror_company_id,
            ShareholderPosition.player_id == offer.offeror_id
        ).first()
        if not offeror_pos or offeror_pos.shares_owned < offer.shares_offered:
            offer.status = "expired"
            _exp_cash2 = offer.cash_component or 0.0
            _exp_offeror2 = offer.offeror_id
            db.commit()
            if _exp_cash2 > 0:
                _refund_cash_to(_exp_offeror2, _exp_cash2)
            return {"ok": False, "error": "Offeror no longer has sufficient shares"}

        offeror_pos.shares_owned -= offer.shares_offered
        target_pos = db.query(ShareholderPosition).filter(
            ShareholderPosition.company_shares_id == offer.offeror_company_id,
            ShareholderPosition.player_id == target_player_id
        ).first()
        if target_pos:
            target_pos.shares_owned += offer.shares_offered
        else:
            company = db.query(CompanyShares).filter(CompanyShares.id == offer.offeror_company_id).first()
            db.add(ShareholderPosition(
                player_id=target_player_id, company_shares_id=offer.offeror_company_id,
                shares_owned=offer.shares_offered, shares_available_to_lend=offer.shares_offered,
                average_cost_basis=company.current_price if company else 0.0
            ))

        _now = datetime.utcnow()
        _stake_expires = (_now + timedelta(days=offer.term_days)) if offer.term_days else None
        stake = AcquisitionStake(
            acquirer_id=offer.offeror_id, target_player_id=target_player_id,
            stake_pct=offer.stake_pct, shares_paid=offer.shares_offered,
            acquisition_offer_id=offer.id, last_income_sweep=_now,
            term_days=offer.term_days, lock_up_days=(offer.lock_up_days or ACQUISITION_DEFAULT_LOCKUP_DAYS),
            expires_at=_stake_expires
        )
        db.add(stake)
        offer.status = "accepted"
        offer.responded_at = _now
        offer.notification_seen_offeror = False
        _cash = offer.cash_component or 0.0
        db.commit()
        db.refresh(stake)
        log_transaction(target_player_id, "corporate", "money", _cash,
                        f"Acquisition accepted: sold {offer.stake_pct*100:.1f}% income stake for {offer.shares_offered:,} shares"
                        + (f" + ${_cash:,.2f} cash" if _cash > 0 else ""))
        log_transaction(offer.offeror_id, "corporate", "money", 0,
                        f"Acquisition accepted: acquired {offer.stake_pct*100:.1f}% of player {target_player_id} income")
        _offeror_id = offer.offeror_id
        _stake_pct = offer.stake_pct
        _shares = offer.shares_offered
        _stake_id = stake.id
        _result = {"ok": True, "stake_id": _stake_id}
    except Exception as e:
        db.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        db.close()

    # Release escrowed cash to target in their legal tender
    if _cash > 0:
        try:
            from reserve_banks import convert_to_legal_tender
            convert_to_legal_tender(target_player_id, _cash)
        except Exception as _ce:
            print(f"[Corporate Actions] Cash release error: {_ce}")

    cash_str = f" + ${_cash:,.0f} cash" if _cash > 0 else ""
    _push_corp(_offeror_id, "Acquisition Offer Accepted",
               f"Accepted — you hold {_stake_pct*100:.1f}% income stake (paid {_shares:,} shares{cash_str})")
    return _result


def reject_acquisition_offer(offer_id: int, target_player_id: int) -> dict:
    db = get_db()
    try:
        offer = db.query(AcquisitionOffer).filter(
            AcquisitionOffer.id == offer_id,
            AcquisitionOffer.target_player_id == target_player_id,
            AcquisitionOffer.status.in_(["pending", "countered"])
        ).first()
        if not offer:
            return {"ok": False, "error": "Offer not found"}
        offer.status = "rejected"
        offer.responded_at = datetime.utcnow()
        offer.notification_seen_offeror = False
        _offeror_id = offer.offeror_id
        _stake_pct = offer.stake_pct
        _cash = offer.cash_component or 0.0
        db.commit()
    except Exception as e:
        db.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        db.close()

    # Return escrowed cash to offeror
    if _cash > 0:
        _refund_cash_to(_offeror_id, _cash)

    _push_corp(_offeror_id, "Acquisition Offer Rejected",
               f"Your offer for a {_stake_pct*100:.1f}% income stake was rejected.")
    return {"ok": True}


def counter_acquisition_offer(offer_id: int, target_player_id: int,
                               counter_stake_pct: float, counter_shares: int,
                               counter_cash: float = 0.0,
                               counter_term_days: Optional[int] = None,
                               counter_lock_up_days: Optional[int] = None) -> dict:
    """Target proposes different terms (stake %, shares, cash, duration, lock-up).
    Offer status → 'countered'; offeror gets push notification."""
    if not (0 < counter_stake_pct <= 0.50):
        return {"ok": False, "error": "Counter stake must be 0%–50%"}
    if counter_shares <= 0:
        return {"ok": False, "error": "Counter shares must be > 0"}
    if counter_cash < 0:
        return {"ok": False, "error": "Counter cash cannot be negative"}
    if counter_term_days is not None and counter_term_days not in ACQUISITION_TERM_OPTIONS[1:]:
        return {"ok": False, "error": f"Counter term must be one of {ACQUISITION_TERM_OPTIONS[1:]} days or omit"}
    db = get_db()
    try:
        offer = db.query(AcquisitionOffer).filter(
            AcquisitionOffer.id == offer_id,
            AcquisitionOffer.target_player_id == target_player_id,
            AcquisitionOffer.status == "pending"
        ).first()
        if not offer:
            return {"ok": False, "error": "Offer not found or no longer pending"}
        if datetime.utcnow() > offer.expires_at:
            offer.status = "expired"
            _cash = offer.cash_component or 0.0
            _exp_offeror = offer.offeror_id
            db.commit()
            if _cash > 0:
                _refund_cash_to(_exp_offeror, _cash)
            return {"ok": False, "error": "Offer has expired"}
        offer.counter_stake_pct = counter_stake_pct
        offer.counter_shares = counter_shares
        offer.counter_cash = counter_cash
        offer.counter_term_days = counter_term_days      # None = keep offeror's original term
        offer.counter_lock_up_days = counter_lock_up_days
        offer.status = "countered"
        offer.notification_seen_offeror = False
        _offeror_id = offer.offeror_id
        _ticker = _company_ticker_local(db, offer.offeror_company_id)
        db.commit()
    except Exception as e:
        db.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        db.close()

    cash_str = f" + ${counter_cash:,.0f} cash" if counter_cash > 0 else ""
    _push_corp(_offeror_id, "Counter-Offer Received",
               f"Player #{target_player_id} countered: {counter_shares:,} {_ticker} shares{cash_str} for {counter_stake_pct*100:.1f}% stake")
    return {"ok": True}


def accept_counter_offer(offer_id: int, offeror_id: int) -> dict:
    """Offeror accepts the target's counter-offer terms. Shares and optional cash transfer accordingly."""
    db = get_db()
    try:
        offer = db.query(AcquisitionOffer).filter(
            AcquisitionOffer.id == offer_id,
            AcquisitionOffer.offeror_id == offeror_id,
            AcquisitionOffer.status == "countered"
        ).first()
        if not offer:
            return {"ok": False, "error": "Counter-offer not found or already responded to"}
        if datetime.utcnow() > offer.expires_at:
            offer.status = "expired"
            _cash = offer.cash_component or 0.0
            db.commit()
            if _cash > 0:
                _refund_cash_to(offeror_id, _cash)
            return {"ok": False, "error": "Offer expired"}
        if not offer.counter_shares or not offer.counter_stake_pct:
            return {"ok": False, "error": "No counter terms on this offer"}

        counter_shares = offer.counter_shares
        counter_stake = offer.counter_stake_pct
        counter_cash = offer.counter_cash or 0.0
        original_cash = offer.cash_component or 0.0

        # Validate shares for counter amount
        offeror_pos = db.query(ShareholderPosition).filter(
            ShareholderPosition.company_shares_id == offer.offeror_company_id,
            ShareholderPosition.player_id == offeror_id
        ).first()
        if not offeror_pos or offeror_pos.shares_owned < counter_shares:
            return {"ok": False, "error": f"Insufficient shares for counter terms (need {counter_shares:,})"}

        # Handle cash difference between original escrow and counter terms
        cash_delta = counter_cash - original_cash
        target_player_id = offer.target_player_id

        if cash_delta > 0:
            # Counter asks for MORE cash than originally escrowed — charge the difference
            from reserve_banks import spend_player_funds
            _ok2, _err2 = spend_player_funds(offeror_id, cash_delta)
            if not _ok2:
                return {"ok": False, "error": f"Insufficient cash for counter terms: {_err2}"}
        elif cash_delta < 0:
            # Counter asks for LESS cash — refund the surplus escrow to offeror
            _refund_cash_to(offeror_id, abs(cash_delta))

        # Transfer shares: offeror → target
        offeror_pos.shares_owned -= counter_shares
        target_pos = db.query(ShareholderPosition).filter(
            ShareholderPosition.company_shares_id == offer.offeror_company_id,
            ShareholderPosition.player_id == target_player_id
        ).first()
        if target_pos:
            target_pos.shares_owned += counter_shares
        else:
            company = db.query(CompanyShares).filter(CompanyShares.id == offer.offeror_company_id).first()
            db.add(ShareholderPosition(
                player_id=target_player_id, company_shares_id=offer.offeror_company_id,
                shares_owned=counter_shares, shares_available_to_lend=counter_shares,
                average_cost_basis=company.current_price if company else 0.0
            ))

        _now2 = datetime.utcnow()
        # Use counter's preferred term/lock-up if set, otherwise fall back to original offer values
        _final_term = offer.counter_term_days if offer.counter_term_days is not None else offer.term_days
        _final_lockup = offer.counter_lock_up_days if offer.counter_lock_up_days is not None else (offer.lock_up_days or ACQUISITION_DEFAULT_LOCKUP_DAYS)
        _final_expires = (_now2 + timedelta(days=_final_term)) if _final_term else None
        stake = AcquisitionStake(
            acquirer_id=offeror_id, target_player_id=target_player_id,
            stake_pct=counter_stake, shares_paid=counter_shares,
            acquisition_offer_id=offer.id, last_income_sweep=_now2,
            term_days=_final_term, lock_up_days=_final_lockup, expires_at=_final_expires
        )
        db.add(stake)

        # Update offer to reflect final accepted terms
        offer.shares_offered = counter_shares
        offer.stake_pct = counter_stake
        offer.cash_component = counter_cash
        offer.term_days = _final_term
        offer.lock_up_days = _final_lockup
        offer.status = "accepted"
        offer.responded_at = _now2
        offer.notification_seen_target = False
        db.commit()
        db.refresh(stake)

        log_transaction(target_player_id, "corporate", "money", counter_cash,
                        f"Counter-offer accepted: sold {counter_stake*100:.1f}% income stake for {counter_shares:,} shares"
                        + (f" + ${counter_cash:,.2f} cash" if counter_cash > 0 else ""))
        log_transaction(offeror_id, "corporate", "money", 0,
                        f"Counter-offer accepted: acquired {counter_stake*100:.1f}% of player {target_player_id} income")
        _stake_id = stake.id
    except Exception as e:
        db.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        db.close()

    # Release counter_cash escrow to target in their legal tender
    if counter_cash > 0:
        try:
            from reserve_banks import convert_to_legal_tender
            convert_to_legal_tender(target_player_id, counter_cash)
        except Exception as _ce:
            print(f"[Corporate Actions] Counter-offer cash release error: {_ce}")

    _push_corp(target_player_id, "Counter-Offer Accepted",
               f"Player #{offeror_id} accepted your counter-offer — income stake active")
    return {"ok": True, "stake_id": _stake_id}


def reject_counter_offer(offer_id: int, offeror_id: int) -> dict:
    """Offeror rejects counter-offer — offer reverts to 'pending' so target can still accept/reject original terms."""
    db = get_db()
    try:
        offer = db.query(AcquisitionOffer).filter(
            AcquisitionOffer.id == offer_id,
            AcquisitionOffer.offeror_id == offeror_id,
            AcquisitionOffer.status == "countered"
        ).first()
        if not offer:
            return {"ok": False, "error": "Counter-offer not found"}
        offer.status = "pending"
        offer.counter_stake_pct = None
        offer.counter_shares = None
        offer.counter_cash = 0.0
        offer.counter_term_days = None
        offer.counter_lock_up_days = None
        offer.notification_seen_target = False
        _target_id = offer.target_player_id
        db.commit()
    except Exception as e:
        db.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        db.close()

    _push_corp(_target_id, "Counter-Offer Declined",
               f"Player #{offeror_id} declined your counter. Original offer terms are still active.")
    return {"ok": True}


def _company_ticker_local(db, company_id: int) -> str:
    """Helper to get ticker symbol from an open DB session."""
    try:
        c = db.query(CompanyShares).filter(CompanyShares.id == company_id).first()
        return c.ticker_symbol if c else f"Co#{company_id}"
    except Exception:
        return f"Co#{company_id}"


def get_acquisition_notifications(player_id: int) -> dict:
    """Pending offers, counter-offers, and diffuse notices for dashboard banners."""
    db = get_db()
    try:
        incoming = db.query(AcquisitionOffer).filter(
            AcquisitionOffer.target_player_id == player_id,
            AcquisitionOffer.status == "pending",
            AcquisitionOffer.notification_seen_target == False
        ).all()
        # Counter-offers awaiting offeror's decision
        countered = db.query(AcquisitionOffer).filter(
            AcquisitionOffer.offeror_id == player_id,
            AcquisitionOffer.status == "countered",
            AcquisitionOffer.notification_seen_offeror == False
        ).all()
        outgoing_updates = db.query(AcquisitionOffer).filter(
            AcquisitionOffer.offeror_id == player_id,
            AcquisitionOffer.status.in_(["accepted", "rejected"]),
            AcquisitionOffer.notification_seen_offeror == False
        ).all()
        diffuse_notices = db.query(DiffuseNotice).filter(
            DiffuseNotice.target_player_id == player_id,
            DiffuseNotice.status == "pending",
            DiffuseNotice.notification_seen_target == False
        ).all()
        diffuse_resolved = db.query(DiffuseNotice).filter(
            DiffuseNotice.acquirer_id == player_id,
            DiffuseNotice.status.in_(["returned", "lien_created"]),
            DiffuseNotice.notification_seen_acquirer == False
        ).all()

        def _company_ticker(company_id):
            try:
                c = db.query(CompanyShares).filter(CompanyShares.id == company_id).first()
                return c.ticker_symbol if c else f"#{company_id}"
            except Exception:
                return f"#{company_id}"

        def _share_value(company_id, shares):
            try:
                c = db.query(CompanyShares).filter(CompanyShares.id == company_id).first()
                return (c.current_price * shares) if c else 0.0
            except Exception:
                return 0.0

        # Renegotiation proposals where player is the respondent (not proposer)
        pending_renegs_for_me = db.query(StakeRenegotiation).filter(
            StakeRenegotiation.status == "pending",
            StakeRenegotiation.proposed_by_player_id != player_id,
            StakeRenegotiation.notification_seen_respondent == False
        ).join(AcquisitionStake, AcquisitionStake.id == StakeRenegotiation.stake_id).filter(
            ((AcquisitionStake.acquirer_id == player_id) |
             (AcquisitionStake.target_player_id == player_id))
        ).all()
        # Renegotiation responses to proposals I made
        reneg_responses = db.query(StakeRenegotiation).filter(
            StakeRenegotiation.proposed_by_player_id == player_id,
            StakeRenegotiation.status.in_(["accepted", "rejected"]),
            StakeRenegotiation.notification_seen_proposer == False
        ).all()

        return {
            "incoming_offers": [{"id": o.id, "offeror_id": o.offeror_id,
                                  "company_id": o.offeror_company_id,
                                  "ticker": _company_ticker(o.offeror_company_id),
                                  "share_value": _share_value(o.offeror_company_id, o.shares_offered),
                                  "shares_offered": o.shares_offered, "stake_pct": o.stake_pct,
                                  "cash_component": o.cash_component or 0.0,
                                  "offer_memo": o.offer_memo or '',
                                  "expires_at": o.expires_at.isoformat()} for o in incoming],
            "countered_offers": [{"id": o.id, "target_id": o.target_player_id,
                                   "original_stake_pct": o.stake_pct,
                                   "original_shares": o.shares_offered,
                                   "counter_stake_pct": o.counter_stake_pct,
                                   "counter_shares": o.counter_shares,
                                   "counter_cash": o.counter_cash or 0.0,
                                   "ticker": _company_ticker(o.offeror_company_id)} for o in countered],
            "outgoing_updates": [{"id": o.id, "target_id": o.target_player_id,
                                   "status": o.status} for o in outgoing_updates],
            "diffuse_notices": [{"id": d.id, "acquirer_id": d.acquirer_id,
                                  "shares_to_return": d.shares_to_return,
                                  "value": d.share_value_at_notice,
                                  "deadline": d.deadline_at.isoformat()} for d in diffuse_notices],
            "diffuse_resolved": [{"id": d.id, "target_id": d.target_player_id,
                                   "status": d.status} for d in diffuse_resolved],
            "renegotiation_proposals": [{"id": r.id, "stake_id": r.stake_id,
                                          "proposed_by": r.proposed_by_player_id,
                                          "new_stake_pct": r.new_stake_pct,
                                          "new_term_days": r.new_term_days,
                                          "note": r.note} for r in pending_renegs_for_me],
            "renegotiation_responses": [{"id": r.id, "stake_id": r.stake_id,
                                          "status": r.status,
                                          "new_stake_pct": r.new_stake_pct,
                                          "new_term_days": r.new_term_days} for r in reneg_responses],
        }
    finally:
        db.close()


def mark_acquisition_notifications_seen(player_id: int):
    db = get_db()
    try:
        db.query(AcquisitionOffer).filter(
            AcquisitionOffer.target_player_id == player_id,
            AcquisitionOffer.notification_seen_target == False
        ).update({"notification_seen_target": True})
        db.query(AcquisitionOffer).filter(
            AcquisitionOffer.offeror_id == player_id,
            AcquisitionOffer.notification_seen_offeror == False
        ).update({"notification_seen_offeror": True})
        # Also mark countered offers seen for offeror
        db.query(AcquisitionOffer).filter(
            AcquisitionOffer.offeror_id == player_id,
            AcquisitionOffer.status == "countered",
            AcquisitionOffer.notification_seen_offeror == False
        ).update({"notification_seen_offeror": True})
        db.query(DiffuseNotice).filter(
            DiffuseNotice.target_player_id == player_id,
            DiffuseNotice.notification_seen_target == False
        ).update({"notification_seen_target": True})
        db.query(DiffuseNotice).filter(
            DiffuseNotice.acquirer_id == player_id,
            DiffuseNotice.notification_seen_acquirer == False
        ).update({"notification_seen_acquirer": True})
        # Renegotiation proposals addressed to me
        seen_reneg_ids = [
            r.id for r in db.query(StakeRenegotiation).filter(
                StakeRenegotiation.status == "pending",
                StakeRenegotiation.proposed_by_player_id != player_id,
                StakeRenegotiation.notification_seen_respondent == False
            ).join(AcquisitionStake, AcquisitionStake.id == StakeRenegotiation.stake_id).filter(
                ((AcquisitionStake.acquirer_id == player_id) |
                 (AcquisitionStake.target_player_id == player_id))
            ).all()
        ]
        if seen_reneg_ids:
            db.query(StakeRenegotiation).filter(
                StakeRenegotiation.id.in_(seen_reneg_ids)
            ).update({"notification_seen_respondent": True}, synchronize_session=False)
        # Renegotiation responses to my proposals
        db.query(StakeRenegotiation).filter(
            StakeRenegotiation.proposed_by_player_id == player_id,
            StakeRenegotiation.notification_seen_proposer == False
        ).update({"notification_seen_proposer": True})
        db.commit()
    finally:
        db.close()


def process_acquisition_income(current_tick: int):
    """Daily sweep: distribute stake_pct of target's income to acquirer."""
    db = get_db()
    try:
        stakes = db.query(AcquisitionStake).filter(AcquisitionStake.is_active == True).all()
        for stake in stakes:
            if stake.last_income_sweep is None:
                stake.last_income_sweep = datetime.utcnow()
                continue
            try:
                from stats_ux import TransactionLog, get_db as get_stats_db
                stats_db = get_stats_db()
                try:
                    income_txs = stats_db.query(TransactionLog).filter(
                        TransactionLog.player_id == stake.target_player_id,
                        TransactionLog.amount > 0,
                        TransactionLog.transaction_type.in_(ACQUISITION_INCOME_TYPES),
                        TransactionLog.timestamp > stake.last_income_sweep
                    ).all()
                    tax_txs = stats_db.query(TransactionLog).filter(
                        TransactionLog.player_id == stake.target_player_id,
                        TransactionLog.amount < 0,
                        TransactionLog.transaction_type.in_(ACQUISITION_TAX_TYPES),
                        TransactionLog.timestamp > stake.last_income_sweep
                    ).all()
                    total_income = sum(tx.amount for tx in income_txs)
                    total_taxes = sum(abs(tx.amount) for tx in tax_txs)
                finally:
                    stats_db.close()
                net = (total_income - total_taxes) * stake.stake_pct
                if abs(net) > 0.01:
                    from reserve_banks import spend_player_funds, convert_to_legal_tender
                    ok, _ = spend_player_funds(stake.target_player_id, net)
                    if ok:
                        try:
                            convert_to_legal_tender(stake.acquirer_id, net)
                        except Exception:
                            from reserve_banks import credit_usd
                            credit_usd(stake.acquirer_id, net)
                        log_transaction(stake.acquirer_id, "corporate", "money", net,
                                        f"Acquisition income ({stake.stake_pct*100:.1f}% of player {stake.target_player_id})")
                        log_transaction(stake.target_player_id, "corporate", "money", -net,
                                        f"Acquisition deduction ({stake.stake_pct*100:.1f}% to player {stake.acquirer_id})")
                        _acq_id = stake.acquirer_id
                        _tgt_id = stake.target_player_id
                        _net = net
                        _pct = stake.stake_pct
                        _push_corp(_acq_id, "Income Sweep Received",
                                   f"${_net:,.0f} income sweep ({_pct*100:.1f}% stake) deposited")
                        _push_corp(_tgt_id, "Acquisition Income Deducted",
                                   f"${_net:,.0f} swept by Player #{_acq_id} ({_pct*100:.1f}% acquisition stake)")
                stake.last_income_sweep = datetime.utcnow()
            except Exception as e:
                print(f"[Corporate Actions] Acquisition stake {stake.id} sweep error: {e}")
        db.commit()
    except Exception as e:
        print(f"[Corporate Actions] Acquisition income sweep error: {e}")
    finally:
        db.close()


def process_expired_stakes():
    """Auto-close term-limited stakes that have passed their expiry date."""
    db = get_db()
    try:
        expired = db.query(AcquisitionStake).filter(
            AcquisitionStake.is_active == True,
            AcquisitionStake.expires_at.isnot(None),
            AcquisitionStake.expires_at < datetime.utcnow()
        ).all()
        for stake in expired:
            stake.is_active = False
            stake.diffuse_initiated_at = datetime.utcnow()
            if stake.acquisition_offer_id:
                offer = db.query(AcquisitionOffer).filter(
                    AcquisitionOffer.id == stake.acquisition_offer_id
                ).first()
                if offer:
                    offer.status = "diffused"
            _push_corp(stake.acquirer_id, "Acquisition Stake Expired",
                       f"Your term-limited stake in Player #{stake.target_player_id} has expired naturally. "
                       f"Shares remain with the target.")
            _push_corp(stake.target_player_id, "Acquisition Stake Expired",
                       f"The {stake.stake_pct*100:.1f}% income stake held by Player #{stake.acquirer_id} "
                       f"has reached its term end and closed automatically.")
        if expired:
            db.commit()
    except Exception as e:
        print(f"[Corporate Actions] Expired stakes error: {e}")
    finally:
        db.close()


# ==========================
# DIFFUSE
# ==========================

def initiate_diffuse(stake_id: int, acquirer_id: int,
                     diffuse_type: str = "share_return") -> dict:
    """Exit an active income stake.

    diffuse_type="share_return"  — target must return shares within DIFFUSE_RETURN_DAYS.
                                   Lien created on default (existing behaviour).
    diffuse_type="cash_buyout"   — acquirer pays market-value cash immediately;
                                   stake ends at once, target keeps their shares.
    """
    if diffuse_type not in ("share_return", "cash_buyout"):
        return {"ok": False, "error": "diffuse_type must be 'share_return' or 'cash_buyout'"}
    db = get_db()
    try:
        stake = db.query(AcquisitionStake).filter(
            AcquisitionStake.id == stake_id,
            AcquisitionStake.acquirer_id == acquirer_id,
            AcquisitionStake.is_active == True
        ).first()
        if not stake:
            return {"ok": False, "error": "Active stake not found"}
        if stake.diffuse_initiated_at:
            return {"ok": False, "error": "Diffuse already initiated"}

        # --- Gap 2: lock-up check ---
        lock_up = stake.lock_up_days or ACQUISITION_DEFAULT_LOCKUP_DAYS
        if lock_up > 0:
            lock_up_expiry = stake.created_at + timedelta(days=lock_up)
            if datetime.utcnow() < lock_up_expiry:
                days_left = (lock_up_expiry - datetime.utcnow()).days + 1
                return {"ok": False,
                        "error": f"Lock-up period active — diffuse not allowed for {days_left} more day(s) "
                                 f"(lock-up expires {lock_up_expiry.strftime('%Y-%m-%d')})"}

        offer = db.query(AcquisitionOffer).filter(
            AcquisitionOffer.id == stake.acquisition_offer_id
        ).first() if stake.acquisition_offer_id else None
        company = db.query(CompanyShares).filter(
            CompanyShares.id == offer.offeror_company_id
        ).first() if offer else None
        share_value_now = (company.current_price * stake.shares_paid) if company else 0.0
        _now = datetime.utcnow()
        _target_id = stake.target_player_id
        _shares_paid = stake.shares_paid

        # --- Gap 3: cash buyout path ---
        if diffuse_type == "cash_buyout":
            # Acquirer pays market value of shares to target; stake ends immediately.
            from reserve_banks import spend_player_funds, convert_to_legal_tender
            _ok_buy, _err_buy = spend_player_funds(acquirer_id, share_value_now)
            if not _ok_buy:
                return {"ok": False,
                        "error": f"Insufficient cash for buyout (need ${share_value_now:,.2f}): {_err_buy}"}
            convert_to_legal_tender(_target_id, share_value_now)

            # Create a resolved notice for audit trail
            notice = DiffuseNotice(
                stake_id=stake_id, acquirer_id=acquirer_id, target_player_id=_target_id,
                shares_to_return=_shares_paid, share_value_at_notice=share_value_now,
                deadline_at=_now, status="buyout_paid",
                diffuse_type="cash_buyout", buyout_amount=share_value_now,
                resolved_at=_now
            )
            db.add(notice)
            stake.is_active = False
            stake.diffuse_initiated_at = _now
            if offer:
                offer.status = "diffused"
            db.commit()
            db.refresh(notice)
            log_transaction(acquirer_id, "corporate", "money", -share_value_now,
                            f"Diffuse cash buyout: paid ${share_value_now:,.2f} to exit stake in player {_target_id}")
            log_transaction(_target_id, "corporate", "money", share_value_now,
                            f"Diffuse cash buyout: received ${share_value_now:,.2f} from player {acquirer_id}")
            _push_corp(_target_id, "Acquisition Stake Bought Out",
                       f"Player #{acquirer_id} bought out their income stake for ${share_value_now:,.2f} cash. "
                       f"Your {_shares_paid:,} shares are yours to keep.")
            return {"ok": True, "notice_id": notice.id, "buyout_amount": share_value_now,
                    "diffuse_type": "cash_buyout"}

        # --- share_return path (existing behaviour) ---
        deadline = _now + timedelta(days=DIFFUSE_RETURN_DAYS)
        notice = DiffuseNotice(
            stake_id=stake_id, acquirer_id=acquirer_id, target_player_id=_target_id,
            shares_to_return=_shares_paid, share_value_at_notice=share_value_now,
            deadline_at=deadline, diffuse_type="share_return"
        )
        db.add(notice)
        stake.diffuse_initiated_at = _now
        stake.is_active = False
        db.commit()
        db.refresh(notice)
        log_transaction(acquirer_id, "corporate", "money", 0,
                        f"Diffuse initiated: {_shares_paid:,} shares worth ${share_value_now:,.2f} — "
                        f"return deadline {deadline.strftime('%Y-%m-%d')}")
        _result = {"ok": True, "notice_id": notice.id, "deadline": deadline.isoformat(),
                   "shares_to_return": _shares_paid, "share_value": share_value_now,
                   "diffuse_type": "share_return"}
    except Exception as e:
        db.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        db.close()

    _push_corp(_target_id, "Diffuse Notice: Return Shares Required",
               f"Player #{acquirer_id} has ended their stake. Return {_shares_paid:,} shares "
               f"by {deadline.strftime('%Y-%m-%d')} or a financial lien will be created.")
    return _result


def target_buyout_stake(stake_id: int, target_player_id: int) -> dict:
    """Target proactively buys out the acquirer's stake (defensive exit).
    Target pays market value of the shares; stake ends immediately; acquirer is made whole in cash."""
    db = get_db()
    try:
        stake = db.query(AcquisitionStake).filter(
            AcquisitionStake.id == stake_id,
            AcquisitionStake.target_player_id == target_player_id,
            AcquisitionStake.is_active == True
        ).first()
        if not stake:
            return {"ok": False, "error": "Active stake not found"}
        if stake.diffuse_initiated_at:
            return {"ok": False, "error": "A diffuse is already in progress on this stake"}

        offer = db.query(AcquisitionOffer).filter(
            AcquisitionOffer.id == stake.acquisition_offer_id
        ).first() if stake.acquisition_offer_id else None
        company = db.query(CompanyShares).filter(
            CompanyShares.id == offer.offeror_company_id
        ).first() if offer else None
        buyout_amount = (company.current_price * stake.shares_paid) if company else 0.0
        _now = datetime.utcnow()
        _acquirer_id = stake.acquirer_id

        from reserve_banks import spend_player_funds, convert_to_legal_tender
        _ok_tbo, _err_tbo = spend_player_funds(target_player_id, buyout_amount)
        if not _ok_tbo:
            return {"ok": False,
                    "error": f"Insufficient cash for buyout (need ${buyout_amount:,.2f}): {_err_tbo}"}
        convert_to_legal_tender(_acquirer_id, buyout_amount)

        notice = DiffuseNotice(
            stake_id=stake_id, acquirer_id=_acquirer_id, target_player_id=target_player_id,
            shares_to_return=stake.shares_paid, share_value_at_notice=buyout_amount,
            deadline_at=_now, status="target_bought_out",
            diffuse_type="target_buyout", buyout_amount=buyout_amount, resolved_at=_now
        )
        db.add(notice)
        stake.is_active = False
        stake.diffuse_initiated_at = _now
        if offer:
            offer.status = "diffused"
        db.commit()
        db.refresh(notice)
        log_transaction(target_player_id, "corporate", "money", -buyout_amount,
                        f"Target buyout: paid ${buyout_amount:,.2f} to end player {_acquirer_id}'s income stake")
        log_transaction(_acquirer_id, "corporate", "money", buyout_amount,
                        f"Target buyout: player {target_player_id} paid ${buyout_amount:,.2f} to end income stake")
        _push_corp(_acquirer_id, "Stake Bought Out by Target",
                   f"Player #{target_player_id} bought out your income stake for ${buyout_amount:,.2f} cash.")
        return {"ok": True, "notice_id": notice.id, "buyout_amount": buyout_amount}
    except Exception as e:
        db.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        db.close()


def get_target_income_estimate(target_player_id: int, days: int = 30) -> dict:
    """Return income stats for a target player over the last `days` days.
    Used to show valuation basis when creating an acquisition offer."""
    try:
        from stats_ux import TransactionLog, get_db as get_stats_db
        stats_db = get_stats_db()
        try:
            since = datetime.utcnow() - timedelta(days=days)
            income_txs = stats_db.query(TransactionLog).filter(
                TransactionLog.player_id == target_player_id,
                TransactionLog.amount > 0,
                TransactionLog.transaction_type.in_(ACQUISITION_INCOME_TYPES),
                TransactionLog.timestamp > since
            ).all()
            tax_txs = stats_db.query(TransactionLog).filter(
                TransactionLog.player_id == target_player_id,
                TransactionLog.amount < 0,
                TransactionLog.transaction_type.in_(ACQUISITION_TAX_TYPES),
                TransactionLog.timestamp > since
            ).all()
        finally:
            stats_db.close()
        gross = sum(tx.amount for tx in income_txs)
        taxes = sum(abs(tx.amount) for tx in tax_txs)
        net = gross - taxes
        daily_avg = net / max(days, 1)
        annual_est = daily_avg * 365
        return {
            "ok": True,
            "days": days,
            "gross_income": round(gross, 2),
            "taxes": round(taxes, 2),
            "net_income": round(net, 2),
            "daily_avg": round(daily_avg, 2),
            "annual_est": round(annual_est, 2),
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "daily_avg": 0, "annual_est": 0, "net_income": 0}


def propose_stake_renegotiation(stake_id: int, player_id: int,
                                 new_stake_pct: float, new_term_days=None,
                                 note: str = '') -> dict:
    """Either party proposes amended terms on an active stake."""
    db = get_db()
    try:
        stake = db.query(AcquisitionStake).filter(
            AcquisitionStake.id == stake_id,
            AcquisitionStake.is_active == True
        ).first()
        if not stake:
            return {"ok": False, "error": "Active stake not found"}
        if player_id not in (stake.acquirer_id, stake.target_player_id):
            return {"ok": False, "error": "Not a party to this stake"}
        # Only one pending proposal at a time
        existing = db.query(StakeRenegotiation).filter(
            StakeRenegotiation.stake_id == stake_id,
            StakeRenegotiation.status == "pending"
        ).first()
        if existing:
            return {"ok": False, "error": "A renegotiation proposal is already pending for this stake"}
        if not (0 < new_stake_pct <= 1.0):
            return {"ok": False, "error": "new_stake_pct must be between 0 and 1"}

        reneg = StakeRenegotiation(
            stake_id=stake_id,
            proposed_by_player_id=player_id,
            new_stake_pct=new_stake_pct,
            new_term_days=new_term_days,
            note=note or ''
        )
        db.add(reneg)
        db.commit()
        db.refresh(reneg)

        other_id = stake.target_player_id if player_id == stake.acquirer_id else stake.acquirer_id
        _push_corp(other_id, "Stake Renegotiation Proposed",
                   f"Player #{player_id} has proposed new terms for your income stake: "
                   f"{new_stake_pct*100:.1f}% stake"
                   + (f", {new_term_days}-day term" if new_term_days else ", perpetual term")
                   + (f" — \"{note}\"" if note else ""))
        return {"ok": True, "reneg_id": reneg.id}
    except Exception as e:
        db.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        db.close()


def respond_to_renegotiation(reneg_id: int, player_id: int, accept: bool) -> dict:
    """Accept or reject a pending stake renegotiation proposal."""
    db = get_db()
    try:
        reneg = db.query(StakeRenegotiation).filter(
            StakeRenegotiation.id == reneg_id,
            StakeRenegotiation.status == "pending"
        ).first()
        if not reneg:
            return {"ok": False, "error": "Pending renegotiation not found"}

        stake = db.query(AcquisitionStake).filter(
            AcquisitionStake.id == reneg.stake_id
        ).first()
        if not stake:
            return {"ok": False, "error": "Stake not found"}
        # Only the other party (not the proposer) can respond
        if player_id == reneg.proposed_by_player_id:
            return {"ok": False, "error": "Cannot respond to your own proposal"}
        if player_id not in (stake.acquirer_id, stake.target_player_id):
            return {"ok": False, "error": "Not a party to this stake"}

        _now = datetime.utcnow()
        reneg.status = "accepted" if accept else "rejected"
        reneg.responded_at = _now
        reneg.notification_seen_proposer = False

        if accept:
            stake.stake_pct = reneg.new_stake_pct
            if reneg.new_term_days is not None:
                stake.term_days = reneg.new_term_days
                stake.expires_at = _now + timedelta(days=reneg.new_term_days)
            db.commit()
            _push_corp(reneg.proposed_by_player_id, "Renegotiation Accepted",
                       f"Player #{player_id} accepted your proposed terms: "
                       f"{reneg.new_stake_pct*100:.1f}% stake"
                       + (f", {reneg.new_term_days}-day term" if reneg.new_term_days else ""))
        else:
            db.commit()
            _push_corp(reneg.proposed_by_player_id, "Renegotiation Rejected",
                       f"Player #{player_id} declined your proposed stake renegotiation.")

        return {"ok": True, "status": reneg.status}
    except Exception as e:
        db.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        db.close()


def complete_diffuse_return(notice_id: int, target_player_id: int) -> dict:
    """Target returns shares — diffuse resolved without lien."""
    db = get_db()
    try:
        notice = db.query(DiffuseNotice).filter(
            DiffuseNotice.id == notice_id,
            DiffuseNotice.target_player_id == target_player_id,
            DiffuseNotice.status == "pending"
        ).first()
        if not notice:
            return {"ok": False, "error": "Notice not found"}
        if datetime.utcnow() > notice.deadline_at:
            return {"ok": False, "error": "Deadline passed — lien will be created"}

        stake = db.query(AcquisitionStake).filter(AcquisitionStake.id == notice.stake_id).first()
        offer = db.query(AcquisitionOffer).filter(
            AcquisitionOffer.id == stake.acquisition_offer_id
        ).first() if (stake and stake.acquisition_offer_id) else None

        if offer:
            target_pos = db.query(ShareholderPosition).filter(
                ShareholderPosition.company_shares_id == offer.offeror_company_id,
                ShareholderPosition.player_id == target_player_id
            ).first()
            if not target_pos or target_pos.shares_owned < notice.shares_to_return:
                return {"ok": False, "error": "Insufficient shares to return"}
            target_pos.shares_owned -= notice.shares_to_return
            acquirer_pos = db.query(ShareholderPosition).filter(
                ShareholderPosition.company_shares_id == offer.offeror_company_id,
                ShareholderPosition.player_id == notice.acquirer_id
            ).first()
            if acquirer_pos:
                acquirer_pos.shares_owned += notice.shares_to_return
            else:
                company = db.query(CompanyShares).filter(
                    CompanyShares.id == offer.offeror_company_id
                ).first()
                db.add(ShareholderPosition(
                    player_id=notice.acquirer_id,
                    company_shares_id=offer.offeror_company_id,
                    shares_owned=notice.shares_to_return,
                    shares_available_to_lend=notice.shares_to_return,
                    average_cost_basis=company.current_price if company else 0.0
                ))
            if offer:
                offer.status = "diffused"

        notice.status = "returned"
        notice.resolved_at = datetime.utcnow()
        notice.notification_seen_acquirer = False
        db.commit()
        log_transaction(target_player_id, "corporate", "money", 0,
                        f"Diffuse complete: {notice.shares_to_return} shares returned")
        return {"ok": True}
    except Exception as e:
        db.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        db.close()


def process_diffuse_deadlines():
    db = get_db()
    try:
        expired = db.query(DiffuseNotice).filter(
            DiffuseNotice.status == "pending",
            DiffuseNotice.deadline_at < datetime.utcnow()
        ).all()
        for notice in expired:
            try:
                from banks.brokerage_firm import BrokerageLien
                db.add(BrokerageLien(
                    player_id=notice.target_player_id,
                    principal=notice.share_value_at_notice,
                    source=f"diffuse_default_stake_{notice.stake_id}"
                ))
                log_transaction(notice.acquirer_id, "corporate", "money",
                                -notice.share_value_at_notice,
                                f"Diffuse default loss: player {notice.target_player_id} failed to return shares")
            except Exception as lien_err:
                print(f"[Corporate Actions] Lien error: {lien_err}")
            notice.status = "lien_created"
            notice.resolved_at = datetime.utcnow()
            notice.notification_seen_acquirer = False
            notice.notification_seen_target = False
            if notice.stake_id:
                stake = db.query(AcquisitionStake).filter(
                    AcquisitionStake.id == notice.stake_id
                ).first()
                if stake and stake.acquisition_offer_id:
                    offer = db.query(AcquisitionOffer).filter(
                        AcquisitionOffer.id == stake.acquisition_offer_id
                    ).first()
                    if offer:
                        offer.status = "diffused"
        db.commit()
    except Exception as e:
        print(f"[Corporate Actions] Diffuse deadline error: {e}")
    finally:
        db.close()


# ==========================
# BANKRUPTCY
# ==========================

def is_player_bankrupt(player_id: int) -> bool:
    db = get_db()
    try:
        return db.query(BankruptcyRecord).filter(
            BankruptcyRecord.player_id == player_id,
            BankruptcyRecord.is_active == True
        ).first() is not None
    finally:
        db.close()


def declare_bankruptcy(player_id: int, current_tick: int) -> dict:
    """
    Full liquidation and restart: clears all assets/debts, removes as mayor,
    gives $20k cash + 1 prairie plot, applies 30-day red-Q.
    """
    from auth import Player, get_db as get_auth_db
    auth_db = get_auth_db()
    total_liquidated = 0.0
    total_debts_cleared = 0.0

    try:
        player = auth_db.query(Player).filter(Player.id == player_id).first()
        if not player:
            return {"ok": False, "error": "Player not found"}
        if is_player_bankrupt(player_id):
            return {"ok": False, "error": "Already in bankruptcy red-Q period"}

        # 1. Clear inventory
        try:
            import inventory as inv_mod
            for item_type, qty in inv_mod.get_player_inventory(player_id).items():
                if qty > 0:
                    inv_mod.remove_item(player_id, item_type, qty)
        except Exception as e:
            print(f"[Bankruptcy] Inventory error: {e}")

        # 2. Delete all businesses
        try:
            from business import Business, SessionLocal as BizSession
            biz_db = BizSession()
            for biz in biz_db.query(Business).filter(Business.owner_id == player_id).all():
                biz_db.delete(biz)
            biz_db.commit(); biz_db.close()
        except Exception as e:
            print(f"[Bankruptcy] Business error: {e}")

        # 3. Cede land to government
        try:
            from land import LandPlot, get_db as get_land_db
            land_db = get_land_db()
            for plot in land_db.query(LandPlot).filter(LandPlot.owner_id == player_id).all():
                plot.owner_id = 0
                plot.is_government_owned = True
            land_db.commit(); land_db.close()
        except Exception as e:
            print(f"[Bankruptcy] Land error: {e}")

        # 4. Delete districts
        try:
            from districts import District, get_db as get_dist_db
            dist_db = get_dist_db()
            for d in dist_db.query(District).filter(District.owner_id == player_id).all():
                dist_db.delete(d)
            dist_db.commit(); dist_db.close()
        except Exception as e:
            print(f"[Bankruptcy] District error: {e}")

        # 5. Liquidate stock positions at current price
        try:
            db = get_db()
            for pos in db.query(ShareholderPosition).filter(
                ShareholderPosition.player_id == player_id,
                ShareholderPosition.shares_owned > 0
            ).all():
                co = db.query(CompanyShares).filter(CompanyShares.id == pos.company_shares_id).first()
                if co and co.current_price > 0:
                    total_liquidated += pos.shares_owned * co.current_price
                    co.shares_in_float += pos.shares_owned
                pos.shares_owned = 0
                pos.shares_available_to_lend = 0
            db.commit(); db.close()
        except Exception as e:
            print(f"[Bankruptcy] Stock liquidation error: {e}")

        # 6. Delist own companies — pay liquidation preference to shareholders first, then zero all
        try:
            from banks.brokerage_firm import firm_deduct_cash
            db = get_db()
            for co in db.query(CompanyShares).filter(
                CompanyShares.founder_id == player_id,
                CompanyShares.is_delisted == False
            ).all():
                # Pay liquidation preference to non-founder shareholders before zeroing
                if co.liquidation_preference and co.liquidation_preference > 1.0 and co.ipo_price:
                    payout_per_share = co.ipo_price * co.liquidation_preference
                    for pos in db.query(ShareholderPosition).filter(
                        ShareholderPosition.company_shares_id == co.id,
                        ShareholderPosition.player_id != player_id,
                        ShareholderPosition.shares_owned > 0,
                    ).all():
                        payout = payout_per_share * pos.shares_owned
                        if firm_deduct_cash(payout, "liquidation_pref",
                                            f"Liq pref {co.ticker_symbol} → player {pos.player_id}"):
                            try:
                                from reserve_banks import convert_to_legal_tender
                                convert_to_legal_tender(pos.player_id, payout)
                            except Exception:
                                shareholder = auth_db.query(Player).filter(
                                    Player.id == pos.player_id
                                ).first()
                                if shareholder:
                                    shareholder.cash_balance += payout
                    auth_db.commit()
                for pos in db.query(ShareholderPosition).filter(
                    ShareholderPosition.company_shares_id == co.id
                ).all():
                    pos.shares_owned = 0
                    pos.shares_available_to_lend = 0
                co.shares_in_float = 0
                co.is_delisted = True
            db.commit(); db.close()
        except Exception as e:
            print(f"[Bankruptcy] Company delist error: {e}")

        # 7. Clear brokerage liens
        try:
            from banks.brokerage_firm import BrokerageLien
            db = get_db()
            for lien in db.query(BrokerageLien).filter(BrokerageLien.player_id == player_id).all():
                total_debts_cleared += lien.principal
                db.delete(lien)
            db.commit(); db.close()
        except Exception as e:
            print(f"[Bankruptcy] Lien error: {e}")

        # 8. Cancel active acquisition stakes
        try:
            db = get_db()
            for s in db.query(AcquisitionStake).filter(
                ((AcquisitionStake.acquirer_id == player_id) |
                 (AcquisitionStake.target_player_id == player_id)),
                AcquisitionStake.is_active == True
            ).all():
                s.is_active = False
            db.commit(); db.close()
        except Exception as e:
            print(f"[Bankruptcy] Acquisition stake error: {e}")

        # 8b. Cancel pending acquisition offers; refund escrowed cash to offeror
        try:
            db = get_db()
            pending_offers = db.query(AcquisitionOffer).filter(
                (AcquisitionOffer.offeror_id == player_id) |
                (AcquisitionOffer.target_player_id == player_id),
                AcquisitionOffer.status.in_(["pending", "countered"]),
            ).all()
            for offer in pending_offers:
                offer.status = "expired"
                cash = offer.cash_component or 0.0
                if cash > 0 and offer.offeror_id != player_id:
                    # Target went bankrupt — refund escrow to offeror
                    _refund_cash_to(offer.offeror_id, cash)
            # Delete pending diffuse notices
            db.query(DiffuseNotice).filter(
                (DiffuseNotice.acquirer_id == player_id) |
                (DiffuseNotice.target_player_id == player_id),
                DiffuseNotice.status == "pending",
            ).delete(synchronize_session=False)
            db.commit(); db.close()
        except Exception as e:
            print(f"[Bankruptcy] Acquisition offer/diffuse cleanup error: {e}")

        # 8c. Void active P2P contracts (no breach penalty — player bankrupt)
        try:
            from p2p import Contract, ContractStatus, get_db as get_p2p_db
            p2p_db = get_p2p_db()
            try:
                p2p_db.query(Contract).filter(
                    (Contract.creator_id == player_id) |
                    (Contract.holder_id == player_id) |
                    (Contract.buyer_id == player_id),
                    Contract.status.in_([
                        ContractStatus.ACTIVE, ContractStatus.LISTED, ContractStatus.DRAFT,
                    ]),
                ).update(
                    {"status": ContractStatus.VOIDED, "breach_reason": "Party declared bankruptcy"},
                    synchronize_session=False,
                )
                p2p_db.commit()
            finally:
                p2p_db.close()
        except Exception as e:
            print(f"[Bankruptcy] P2P contract cleanup error: {e}")

        # 8d. Remove trusted-trade entries
        try:
            from trusted_trade import TrustedTraderEntry, get_db as get_tt_db
            tt_db = get_tt_db()
            try:
                tt_db.query(TrustedTraderEntry).filter(
                    (TrustedTraderEntry.owner_player_id == player_id) |
                    (TrustedTraderEntry.trusted_player_id == player_id),
                ).delete(synchronize_session=False)
                tt_db.commit()
            finally:
                tt_db.close()
        except Exception as e:
            print(f"[Bankruptcy] Trusted-trade cleanup error: {e}")

        # 8e. Remove from group DMs; delete empty conversations
        try:
            from dm import GroupParticipant, GroupConversation, get_db as get_dm_db
            dm_db = get_dm_db()
            try:
                dm_db.query(GroupParticipant).filter(
                    GroupParticipant.player_id == player_id,
                ).delete(synchronize_session=False)
                for g in dm_db.query(GroupConversation).filter(
                    GroupConversation.created_by == player_id,
                ).all():
                    remaining = dm_db.query(GroupParticipant).filter(
                        GroupParticipant.conversation_id == g.id,
                    ).count()
                    if remaining == 0:
                        dm_db.delete(g)
                dm_db.commit()
            finally:
                dm_db.close()
        except Exception as e:
            print(f"[Bankruptcy] Group DM cleanup error: {e}")

        # 8f. Remove contact relationships
        try:
            from contacts import Contact, get_db as get_ct_db
            ct_db = get_ct_db()
            try:
                ct_db.query(Contact).filter(
                    (Contact.requester_id == player_id) |
                    (Contact.recipient_id == player_id),
                ).delete(synchronize_session=False)
                ct_db.commit()
            finally:
                ct_db.close()
        except Exception as e:
            print(f"[Bankruptcy] Contacts cleanup error: {e}")

        # 9. Transfer mayor role if applicable
        try:
            from cities import City, CityMember, get_db as get_city_db
            city_db = get_city_db()
            city = city_db.query(City).filter(City.mayor_id == player_id).first()
            if city:
                others = city_db.query(CityMember).filter(
                    CityMember.city_id == city.id,
                    CityMember.player_id != player_id
                ).all()
                city.mayor_id = others[0].player_id if others else None
            member = city_db.query(CityMember).filter(CityMember.player_id == player_id).first()
            if member:
                city_db.delete(member)
            city_db.commit(); city_db.close()
        except Exception as e:
            print(f"[Bankruptcy] Mayor error: {e}")

        # 10. Cancel all open market and brokerage orders
        try:
            from market import MarketOrder, get_db as get_mkt_db
            mkt_db = get_mkt_db()
            try:
                mkt_db.query(MarketOrder).filter(
                    MarketOrder.player_id == player_id,
                    MarketOrder.status.in_(["active", "partial"])
                ).update({"status": "cancelled"}, synchronize_session=False)
                mkt_db.commit()
            finally:
                mkt_db.close()
        except Exception as e:
            print(f"[Bankruptcy] Market order cleanup error: {e}")

        try:
            from district_market import DistrictMarketOrder, get_db as get_dm_db
            dm_db = get_dm_db()
            try:
                dm_db.query(DistrictMarketOrder).filter(
                    DistrictMarketOrder.player_id == player_id,
                    DistrictMarketOrder.status.in_(["active", "partial"])
                ).update({"status": "cancelled"}, synchronize_session=False)
                dm_db.commit()
            finally:
                dm_db.close()
        except Exception as e:
            print(f"[Bankruptcy] District market order cleanup error: {e}")

        try:
            from banks.brokerage_order_book import OrderBook, get_db as get_ob_db
            ob_db = get_ob_db()
            try:
                ob_db.query(OrderBook).filter(
                    OrderBook.player_id == player_id,
                    OrderBook.status.in_(["pending", "partial"])
                ).update({"status": "cancelled"}, synchronize_session=False)
                ob_db.commit()
            finally:
                ob_db.close()
        except Exception as e:
            print(f"[Bankruptcy] Brokerage order book cleanup error: {e}")

        # 11. Clear orphaned records left by deleted businesses
        try:
            from business import RetailPrice, SessionLocal as BizSession
            biz_db = BizSession()
            biz_db.query(RetailPrice).filter(RetailPrice.player_id == player_id).delete(synchronize_session=False)
            biz_db.commit(); biz_db.close()
        except Exception as e:
            print(f"[Bankruptcy] Retail price cleanup error: {e}")

        try:
            from stats_ux import PlayerStats, PlayerCostAverage, get_db as get_stats_db
            stats_db = get_stats_db()
            try:
                stats_db.query(PlayerStats).filter(PlayerStats.player_id == player_id).delete(synchronize_session=False)
                stats_db.query(PlayerCostAverage).filter(PlayerCostAverage.player_id == player_id).delete(synchronize_session=False)
                stats_db.commit()
            finally:
                stats_db.close()
        except Exception as e:
            print(f"[Bankruptcy] Stats cache cleanup error: {e}")

        try:
            from executive import Executive, get_db as get_exec_db
            exec_db = get_exec_db()
            try:
                exec_db.query(Executive).filter(
                    Executive.employer_id == player_id
                ).update({"employer_id": None}, synchronize_session=False)
                exec_db.commit()
            finally:
                exec_db.close()
        except Exception as e:
            print(f"[Bankruptcy] Executive cleanup error: {e}")

        # Clear non-USD currency balances (player restarts fresh)
        try:
            from reserve_banks import PlayerCurrencyBalance, PlayerLegalTender, get_db as get_rb_db
            rb_db = get_rb_db()
            try:
                rb_db.query(PlayerCurrencyBalance).filter(
                    PlayerCurrencyBalance.player_id == player_id,
                    PlayerCurrencyBalance.currency_code != "USD"
                ).delete(synchronize_session=False)
                rb_db.query(PlayerLegalTender).filter(
                    PlayerLegalTender.player_id == player_id
                ).delete(synchronize_session=False)
                rb_db.commit()
            finally:
                rb_db.close()
        except Exception as e:
            print(f"[Bankruptcy] Reserve bank record cleanup error: {e}")

        # 12. Reset cash (resets USD PlayerCurrencyBalance to restart amount)
        total_liquidated += player.cash_balance
        player.cash_balance = BANKRUPTCY_RESTART_CASH
        auth_db.commit()

        # 13. Create starter land plot
        try:
            from land import LandPlot, get_db as get_land_db
            land_db = get_land_db()
            land_db.add(LandPlot(
                owner_id=player_id, terrain_type="prairie",
                proximity_features="", efficiency=100.0, size=1.0,
                monthly_tax=500.0, is_starter_plot=True, is_government_owned=False
            ))
            land_db.commit(); land_db.close()
        except Exception as e:
            print(f"[Bankruptcy] Starter plot error: {e}")

        # 14. Create bankruptcy record
        red_q_expires = datetime.utcnow() + timedelta(days=BANKRUPTCY_RED_Q_DAYS)
        db = get_db()
        db.add(BankruptcyRecord(
            player_id=player_id, red_q_expires_at=red_q_expires,
            total_assets_liquidated=total_liquidated,
            total_debts_cleared=total_debts_cleared,
            restart_cash=BANKRUPTCY_RESTART_CASH
        ))
        db.commit(); db.close()

        log_transaction(player_id, "corporate", "money", BANKRUPTCY_RESTART_CASH,
                        f"Bankruptcy declared — restarted with ${BANKRUPTCY_RESTART_CASH:,.0f}; "
                        f"red-Q until {red_q_expires.strftime('%Y-%m-%d')}")

        print(f"[Bankruptcy] Player {player_id} complete: liquidated=${total_liquidated:,.2f}, debts={total_debts_cleared:,.2f}")
        return {"ok": True, "total_liquidated": total_liquidated,
                "total_debts_cleared": total_debts_cleared,
                "restart_cash": BANKRUPTCY_RESTART_CASH,
                "red_q_expires": red_q_expires.isoformat()}

    except Exception as e:
        print(f"[Bankruptcy] Fatal error: {e}")
        import traceback; traceback.print_exc()
        return {"ok": False, "error": str(e)}
    finally:
        auth_db.close()


# ==========================
# TICK HANDLER
# ==========================

CORPORATE_ACTIONS_TICK_INTERVAL = 720   # Hourly (720 × 5s)
ACQUISITION_SWEEP_INTERVAL = 17280      # Daily (17280 × 5s)
_last_ca_tick = 0
_last_acq_tick = 0


def process_corporate_actions():
    """Process all active automated corporate action programs."""
    _refunds = []
    db = get_db()
    try:
        for program in db.query(BuybackProgram).filter(
            BuybackProgram.status == ActionStatus.ACTIVE.value
        ).all():
            check_and_execute_buyback(program.id)

        for rule in db.query(StockSplitRule).filter(
            StockSplitRule.status == ActionStatus.ACTIVE.value,
            StockSplitRule.is_enabled == True
        ).all():
            check_and_execute_split(rule.id)

        for offering in db.query(SecondaryOffering).filter(
            SecondaryOffering.status == ActionStatus.ACTIVE.value,
            SecondaryOffering.is_enabled == True
        ).all():
            check_and_execute_offering(offering.id)

        # Expire stale acquisition offers — refund any escrowed cash first
        _now_expire = datetime.utcnow()
        stale_offers = db.query(AcquisitionOffer).filter(
            AcquisitionOffer.status == "pending",
            AcquisitionOffer.expires_at < _now_expire
        ).all()
        _refunds = [(o.offeror_id, o.cash_component) for o in stale_offers if (o.cash_component or 0) > 0]
        for o in stale_offers:
            o.status = "expired"
        db.flush()

        # Expire old red-Q records
        db.query(BankruptcyRecord).filter(
            BankruptcyRecord.is_active == True,
            BankruptcyRecord.red_q_expires_at < datetime.utcnow()
        ).update({"is_active": False})

        db.commit()
    finally:
        db.close()

    # Refund escrowed cash for offers expired this tick (done outside the main session to avoid locking)
    for _pid, _amt in _refunds:
        _refund_cash_to(_pid, _amt)

    process_diffuse_deadlines()
    process_expired_stakes()


def tick(current_tick: int, now):
    global _last_ca_tick, _last_acq_tick
    if current_tick - _last_ca_tick >= CORPORATE_ACTIONS_TICK_INTERVAL:
        _last_ca_tick = current_tick
        try:
            process_corporate_actions()
        except Exception as e:
            print(f"[Corporate Actions] tick error: {e}")
    if current_tick - _last_acq_tick >= ACQUISITION_SWEEP_INTERVAL:
        _last_acq_tick = current_tick
        try:
            process_acquisition_income(current_tick)
        except Exception as e:
            print(f"[Corporate Actions] acquisition sweep error: {e}")


# ==========================
# INITIALIZATION
# ==========================

def _run_acquisition_migrations():
    """Add columns introduced after initial deployment (create_all only adds missing tables)."""
    from banks.brokerage_firm import engine as _engine
    from sqlalchemy import text
    _new_cols = [
        # --- batch 1 (counter-offer, cash, memo) ---
        "ALTER TABLE acquisition_offers ADD COLUMN IF NOT EXISTS cash_component DOUBLE PRECISION DEFAULT 0.0",
        "ALTER TABLE acquisition_offers ADD COLUMN IF NOT EXISTS offer_memo TEXT DEFAULT ''",
        "ALTER TABLE acquisition_offers ADD COLUMN IF NOT EXISTS counter_stake_pct DOUBLE PRECISION",
        "ALTER TABLE acquisition_offers ADD COLUMN IF NOT EXISTS counter_shares INTEGER",
        "ALTER TABLE acquisition_offers ADD COLUMN IF NOT EXISTS counter_cash DOUBLE PRECISION DEFAULT 0.0",
        # --- batch 2 (term + lock-up) ---
        "ALTER TABLE acquisition_offers ADD COLUMN IF NOT EXISTS term_days INTEGER",
        f"ALTER TABLE acquisition_offers ADD COLUMN IF NOT EXISTS lock_up_days INTEGER DEFAULT {ACQUISITION_DEFAULT_LOCKUP_DAYS}",
        "ALTER TABLE acquisition_offers ADD COLUMN IF NOT EXISTS counter_term_days INTEGER",
        "ALTER TABLE acquisition_offers ADD COLUMN IF NOT EXISTS counter_lock_up_days INTEGER",
        "ALTER TABLE acquisition_stakes ADD COLUMN IF NOT EXISTS term_days INTEGER",
        f"ALTER TABLE acquisition_stakes ADD COLUMN IF NOT EXISTS lock_up_days INTEGER DEFAULT {ACQUISITION_DEFAULT_LOCKUP_DAYS}",
        "ALTER TABLE acquisition_stakes ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP",
        # --- batch 3 (diffuse type + buyout) ---
        "ALTER TABLE diffuse_notices ADD COLUMN IF NOT EXISTS diffuse_type TEXT DEFAULT 'share_return'",
        "ALTER TABLE diffuse_notices ADD COLUMN IF NOT EXISTS buyout_amount DOUBLE PRECISION",
        # --- batch 4 (stake renegotiations table) ---
        """CREATE TABLE IF NOT EXISTS stake_renegotiations (
            id SERIAL PRIMARY KEY,
            stake_id INTEGER NOT NULL,
            proposed_by_player_id INTEGER NOT NULL,
            new_stake_pct DOUBLE PRECISION NOT NULL,
            new_term_days INTEGER,
            note TEXT DEFAULT '',
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT NOW(),
            responded_at TIMESTAMP,
            notification_seen_proposer BOOLEAN DEFAULT FALSE,
            notification_seen_respondent BOOLEAN DEFAULT FALSE
        )""",
    ]
    with _engine.connect() as _conn:
        for _stmt in _new_cols:
            try:
                _conn.execute(text(_stmt))
            except Exception:
                pass
        _conn.commit()


def initialize():
    """Initialize corporate actions module."""
    from banks.brokerage_firm import engine as _engine
    print("[Corporate Actions] Creating database tables...")
    Base.metadata.create_all(bind=_engine)
    try:
        _run_acquisition_migrations()
    except Exception as _mig_err:
        print(f"[Corporate Actions] Migration warning: {_mig_err}")
    print("[Corporate Actions] Module initialized")


# ==========================
# PUBLIC API
# ==========================

__all__ = [
    'BuybackProgram', 'StockSplitRule', 'SecondaryOffering', 'CorporateActionHistory',
    'ReverseSplitRecord', 'SpecialDividendRecord', 'TaxVoucher',
    'AcquisitionOffer', 'AcquisitionStake', 'DiffuseNotice', 'BankruptcyRecord',
    'StakeRenegotiation',
    'BuybackTrigger', 'SplitTrigger', 'OfferingTrigger', 'ActionStatus',
    'create_buyback_program', 'create_stock_split_rule', 'create_secondary_offering',
    'execute_reverse_split',
    'pay_special_dividend', 'get_tax_voucher_balance', 'redeem_tax_vouchers',
    'create_acquisition_offer', 'accept_acquisition_offer', 'reject_acquisition_offer',
    'counter_acquisition_offer', 'accept_counter_offer', 'reject_counter_offer',
    'get_acquisition_notifications', 'mark_acquisition_notifications_seen',
    'initiate_diffuse', 'complete_diffuse_return',
    'target_buyout_stake',
    'get_target_income_estimate',
    'propose_stake_renegotiation', 'respond_to_renegotiation',
    'declare_bankruptcy', 'is_player_bankrupt',
    'process_corporate_actions', 'initialize', 'tick',
    'TAX_VOUCHER_RATE', 'VALID_REVERSE_SPLIT_RATIOS', 'BANKRUPTCY_RESTART_CASH',
    'BANKRUPTCY_RED_Q_DAYS', 'ACQUISITION_OFFER_DAYS', 'DIFFUSE_RETURN_DAYS',
    'ACQUISITION_DEFAULT_LOCKUP_DAYS', 'ACQUISITION_TERM_OPTIONS',
    'ACQUISITION_INCOME_TYPES', 'ACQUISITION_TAX_TYPES', 'get_db',
]
