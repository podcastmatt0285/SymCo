"""
corporate_actions.py - Automated Corporate Actions for SymCo Brokerage Firm

Adds three automated corporate finance actions that founders configure at IPO:

1. BUYBACKS - Company automatically repurchases shares to support price
2. STOCK SPLITS - Automatically split shares when price gets too high
3. SECONDARY OFFERINGS - Issue new shares when company needs capital

Each action is configured with triggers and limits during IPO creation,
then executed automatically by the Firm's tick handler.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from enum import Enum

from sqlalchemy import Column, String, Float, DateTime, Integer, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base

# Import from existing brokerage firm
from banks.brokerage_firm import (
    get_db, Base, CompanyShares, ShareholderPosition, 
    BANK_PLAYER_ID, BANK_NAME, get_firm_entity, firm_deduct_cash, firm_add_cash,
    modify_credit_score, record_price
)
from brokerage_order_book import place_market_order, OrderSide

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
    max_shares_to_buy = Column(Integer, nullable=False)  # Total program size
    max_price_per_share = Column(Float, nullable=False)  # Won't buy above this
    max_treasury_pct = Column(Float, default=0.30)  # Max % to hold in treasury
    
    # Execution
    shares_bought = Column(Integer, default=0)
    total_spent = Column(Float, default=0.0)
    average_buy_price = Column(Float, default=0.0)
    last_execution = Column(DateTime, nullable=True)
    
    # Status
    status = Column(String, default=ActionStatus.ACTIVE.value)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Treasury shares (bought but not retired)
    treasury_shares = Column(Integer, default=0)


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
    shares_to_issue = Column(Integer, nullable=False)
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
    shares_affected = Column(Integer, nullable=False)
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
                if founder and founder.cash_balance >= surplus_threshold:
                    should_buy = True
                    print(f"[{BANK_NAME}] 💰 BUYBACK TRIGGER: Founder has ${founder.cash_balance:,.2f}")
            finally:
                auth_db.close()
        
        elif program.trigger_type == BuybackTrigger.SCHEDULE.value:
            interval = program.trigger_params.get("interval_ticks", 3600)
            
            if program.last_execution:
                # Would need tick tracking - simplified for now
                should_buy = True
            else:
                should_buy = True
        
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
        
        # Check founder has funds
        from auth import Player, get_db as get_auth_db
        auth_db = get_auth_db()
        try:
            founder = auth_db.query(Player).filter(Player.id == company.founder_id).first()
            
            if not founder or founder.cash_balance < total_cost:
                print(f"[{BANK_NAME}] BUYBACK SKIPPED: Insufficient founder funds")
                return False
            
            # Deduct from founder
            founder.cash_balance -= total_cost
            auth_db.commit()
        finally:
            auth_db.close()
        
        # Execute buyback via market order
        # We'll use the Firm's account as intermediary
        temp_cash = cost
        firm_add_cash(temp_cash, "buyback_funding", f"Temp funding for {company.ticker_symbol} buyback", company.founder_id)
        
        success = place_market_order(
            player_id=BANK_PLAYER_ID,
            company_shares_id=company.id,
            side=OrderSide.BUY,
            quantity=shares_to_buy
        )
        
        if success:
            # Update program
            program.shares_bought += shares_to_buy
            program.total_spent += cost
            program.average_buy_price = program.total_spent / program.shares_bought if program.shares_bought > 0 else 0
            program.treasury_shares += shares_to_buy
            program.last_execution = datetime.utcnow()
            
            # Firm keeps the fee
            firm_add_cash(fee, "buyback_fee", f"Buyback fee for {company.ticker_symbol}", company.founder_id)
            
            # Update company
            company.shares_in_float -= shares_to_buy
            company.shares_held_by_firm += shares_to_buy
            
            # Log action
            log_corporate_action(
                company_shares_id=company.id,
                action_type="buyback",
                shares_affected=shares_to_buy,
                price_per_share=company.current_price,
                total_value=cost,
                description=f"Buyback executed: {program.trigger_type}"
            )
            
            db.commit()
            
            print(f"[{BANK_NAME}] 📦 BUYBACK EXECUTED: {shares_to_buy} {company.ticker_symbol} @ ${company.current_price:.2f}")
            print(f"  → Total cost: ${total_cost:,.2f} (Fee: ${fee:.2f})")
            print(f"  → Progress: {program.shares_bought}/{program.max_shares_to_buy}")
            
            return True
        else:
            # Refund if market order failed
            firm_deduct_cash(temp_cash, "buyback_refund", "Failed buyback refund")
            auth_db = get_auth_db()
            try:
                founder = auth_db.query(Player).filter(Player.id == company.founder_id).first()
                if founder:
                    founder.cash_balance += total_cost
                    auth_db.commit()
            finally:
                auth_db.close()
            
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
        
        db.commit()
        
        print(f"[{BANK_NAME}] ✂️ SPLIT EXECUTED: {company.ticker_symbol} {ratio}:1")
        print(f"  → Shares: {old_shares:,} → {company.shares_outstanding:,}")
        print(f"  → Price: ${old_price:.2f} → ${company.current_price:.2f}")
        
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
                if founder and founder.cash_balance < threshold:
                    should_offer = True
                    print(f"[{BANK_NAME}] 💵 OFFERING TRIGGER: Founder cash ${founder.cash_balance:,.2f} " +
                          f"below ${threshold:,.2f}")
            finally:
                auth_db.close()
        
        elif offering.trigger_type == OfferingTrigger.EXPANSION.value:
            business_count = offering.trigger_params.get("business_count", 5)
            
            from business import Business
            biz_db = get_db()
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
# TICK HANDLER
# ==========================

def process_corporate_actions():
    """
    Process all active corporate action programs.
    Called from the main Firm tick handler.
    """
    db = get_db()
    try:
        # Process buybacks
        active_buybacks = db.query(BuybackProgram).filter(
            BuybackProgram.status == ActionStatus.ACTIVE.value
        ).all()
        
        for program in active_buybacks:
            check_and_execute_buyback(program.id)
        
        # Process splits
        active_splits = db.query(StockSplitRule).filter(
            StockSplitRule.status == ActionStatus.ACTIVE.value,
            StockSplitRule.is_enabled == True
        ).all()
        
        for rule in active_splits:
            check_and_execute_split(rule.id)
        
        # Process secondary offerings
        active_offerings = db.query(SecondaryOffering).filter(
            SecondaryOffering.status == ActionStatus.ACTIVE.value,
            SecondaryOffering.is_enabled == True
        ).all()
        
        for offering in active_offerings:
            check_and_execute_offering(offering.id)
    
    finally:
        db.close()


# ==========================
# INITIALIZATION
# ==========================

def initialize():
    """Initialize corporate actions module."""
    print("[Corporate Actions] Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("[Corporate Actions] Module initialized")


# ==========================
# PUBLIC API
# ==========================

__all__ = [
    # Models
    'BuybackProgram',
    'StockSplitRule',
    'SecondaryOffering',
    'CorporateActionHistory',
    
    # Enums
    'BuybackTrigger',
    'SplitTrigger',
    'OfferingTrigger',
    'ActionStatus',
    
    # Functions
    'create_buyback_program',
    'create_stock_split_rule',
    'create_secondary_offering',
    'process_corporate_actions',
    'initialize',
]
