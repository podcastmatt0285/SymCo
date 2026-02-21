"""
corporate_actions_ux.py - UX Endpoints for Corporate Actions

FastAPI endpoints for managing automated corporate actions:
- Create buyback programs during/after IPO
- Set up stock split rules
- Configure secondary offerings
- View action history and status
"""

from fastapi import APIRouter, HTTPException, Cookie
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

# Import from corporate actions module
from fastapi import Form
from corporate_actions import (
    create_buyback_program, create_stock_split_rule, create_secondary_offering,
    BuybackProgram, StockSplitRule, SecondaryOffering, CorporateActionHistory,
    BuybackTrigger, SplitTrigger, OfferingTrigger, ActionStatus,
    execute_reverse_split, pay_special_dividend, get_tax_voucher_balance, redeem_tax_vouchers,
    create_acquisition_offer, accept_acquisition_offer, reject_acquisition_offer,
    get_acquisition_notifications, mark_acquisition_notifications_seen,
    initiate_diffuse, complete_diffuse_return,
    declare_bankruptcy, is_player_bankrupt,
    AcquisitionOffer, AcquisitionStake, DiffuseNotice, BankruptcyRecord,
    TaxVoucher, VALID_REVERSE_SPLIT_RATIOS, TAX_VOUCHER_RATE,
    ACQUISITION_OFFER_DAYS, DIFFUSE_RETURN_DAYS, BANKRUPTCY_RESTART_CASH,
    get_db
)
from banks.brokerage_firm import CompanyShares, ShareholderPosition, BANK_NAME
from auth import get_player_from_session, get_db as get_auth_db

router = APIRouter(prefix="/api/corporate-actions", tags=["corporate-actions"])

# ==========================
# REQUEST MODELS
# ==========================

class CreateBuybackRequest(BaseModel):
    company_shares_id: int
    trigger_type: str  # "price_drop", "earnings_surplus", "schedule"
    trigger_params: dict
    max_shares_to_buy: int
    max_price_per_share: float

class CreateSplitRuleRequest(BaseModel):
    company_shares_id: int
    trigger_type: str  # "price_threshold", "trading_volume"
    trigger_params: dict
    split_ratio: int  # 2, 3, 5, 10

class CreateOfferingRequest(BaseModel):
    company_shares_id: int
    trigger_type: str  # "cash_need", "expansion"
    trigger_params: dict
    shares_to_issue: int
    min_price_per_share: float

class UpdateProgramStatusRequest(BaseModel):
    status: str  # "active", "paused", "cancelled"

# ==========================
# BUYBACK ENDPOINTS
# ==========================

@router.post("/buyback/create")
async def api_create_buyback(
    request: CreateBuybackRequest,
    session_token: Optional[str] = Cookie(None)
):
    """
    Create an automated buyback program.
    
    Example request:
    {
        "company_shares_id": 1,
        "trigger_type": "price_drop",
        "trigger_params": {
            "target_price": 10.0,
            "drop_threshold_pct": 0.15
        },
        "max_shares_to_buy": 10000,
        "max_price_per_share": 12.0
    }
    """
    auth_db = get_auth_db()
    player = get_player_from_session(auth_db, session_token)
    auth_db.close()
    
    if not player:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Verify ownership
    db = get_db()
    try:
        company = db.query(CompanyShares).filter(
            CompanyShares.id == request.company_shares_id,
            CompanyShares.founder_id == player.id
        ).first()
        
        if not company:
            raise HTTPException(status_code=404, detail="Company not found or not owned by you")
    finally:
        db.close()
    
    # Convert trigger type string to enum
    try:
        trigger_enum = BuybackTrigger(request.trigger_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid trigger type: {request.trigger_type}")
    
    program = create_buyback_program(
        company_shares_id=request.company_shares_id,
        trigger_type=trigger_enum,
        trigger_params=request.trigger_params,
        max_shares_to_buy=request.max_shares_to_buy,
        max_price_per_share=request.max_price_per_share
    )
    
    if not program:
        raise HTTPException(status_code=400, detail="Failed to create buyback program")
    
    return {
        "success": True,
        "program_id": program.id,
        "message": f"Buyback program created for {company.ticker_symbol}"
    }


@router.get("/buyback/{company_shares_id}")
async def api_get_buybacks(
    company_shares_id: int,
    session_token: Optional[str] = Cookie(None)
):
    """Get all buyback programs for a company."""
    auth_db = get_auth_db()
    player = get_player_from_session(auth_db, session_token)
    auth_db.close()
    
    if not player:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    db = get_db()
    try:
        company = db.query(CompanyShares).filter(
            CompanyShares.id == company_shares_id,
            CompanyShares.founder_id == player.id
        ).first()
        
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        programs = db.query(BuybackProgram).filter(
            BuybackProgram.company_shares_id == company_shares_id
        ).all()
        
        return {
            "company": {
                "id": company.id,
                "ticker": company.ticker_symbol,
                "name": company.company_name,
                "current_price": company.current_price
            },
            "programs": [
                {
                    "id": p.id,
                    "trigger_type": p.trigger_type,
                    "trigger_params": p.trigger_params,
                    "max_shares": p.max_shares_to_buy,
                    "shares_bought": p.shares_bought,
                    "progress_pct": (p.shares_bought / p.max_shares_to_buy * 100) if p.max_shares_to_buy > 0 else 0,
                    "total_spent": p.total_spent,
                    "average_price": p.average_buy_price,
                    "treasury_shares": p.treasury_shares,
                    "status": p.status,
                    "last_execution": p.last_execution.isoformat() if p.last_execution else None
                }
                for p in programs
            ]
        }
    finally:
        db.close()


@router.patch("/buyback/{program_id}/status")
async def api_update_buyback_status(
    program_id: int,
    request: UpdateProgramStatusRequest,
    session_token: Optional[str] = Cookie(None)
):
    """Pause, resume, or cancel a buyback program."""
    auth_db = get_auth_db()
    player = get_player_from_session(auth_db, session_token)
    auth_db.close()
    
    if not player:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    db = get_db()
    try:
        program = db.query(BuybackProgram).filter(
            BuybackProgram.id == program_id
        ).first()
        
        if not program:
            raise HTTPException(status_code=404, detail="Program not found")
        
        # Verify ownership
        company = db.query(CompanyShares).filter(
            CompanyShares.id == program.company_shares_id,
            CompanyShares.founder_id == player.id
        ).first()
        
        if not company:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        # Update status
        try:
            new_status = ActionStatus(request.status)
            program.status = new_status.value
            db.commit()
            
            return {
                "success": True,
                "program_id": program.id,
                "new_status": program.status
            }
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {request.status}")
    finally:
        db.close()


# ==========================
# STOCK SPLIT ENDPOINTS
# ==========================

@router.post("/split/create")
async def api_create_split_rule(
    request: CreateSplitRuleRequest,
    session_token: Optional[str] = Cookie(None)
):
    """
    Create an automated stock split rule.
    
    Example request:
    {
        "company_shares_id": 1,
        "trigger_type": "price_threshold",
        "trigger_params": {
            "price_threshold": 100.0
        },
        "split_ratio": 2
    }
    """
    auth_db = get_auth_db()
    player = get_player_from_session(auth_db, session_token)
    auth_db.close()
    
    if not player:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Verify ownership
    db = get_db()
    try:
        company = db.query(CompanyShares).filter(
            CompanyShares.id == request.company_shares_id,
            CompanyShares.founder_id == player.id
        ).first()
        
        if not company:
            raise HTTPException(status_code=404, detail="Company not found or not owned by you")
    finally:
        db.close()
    
    # Convert trigger type
    try:
        trigger_enum = SplitTrigger(request.trigger_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid trigger type: {request.trigger_type}")
    
    rule = create_stock_split_rule(
        company_shares_id=request.company_shares_id,
        trigger_type=trigger_enum,
        trigger_params=request.trigger_params,
        split_ratio=request.split_ratio
    )
    
    if not rule:
        raise HTTPException(status_code=400, detail="Failed to create split rule")
    
    return {
        "success": True,
        "rule_id": rule.id,
        "message": f"Split rule created for {company.ticker_symbol}"
    }


@router.get("/split/{company_shares_id}")
async def api_get_split_rules(
    company_shares_id: int,
    session_token: Optional[str] = Cookie(None)
):
    """Get all split rules for a company."""
    auth_db = get_auth_db()
    player = get_player_from_session(auth_db, session_token)
    auth_db.close()
    
    if not player:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    db = get_db()
    try:
        company = db.query(CompanyShares).filter(
            CompanyShares.id == company_shares_id,
            CompanyShares.founder_id == player.id
        ).first()
        
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        rules = db.query(StockSplitRule).filter(
            StockSplitRule.company_shares_id == company_shares_id
        ).all()
        
        return {
            "company": {
                "id": company.id,
                "ticker": company.ticker_symbol,
                "name": company.company_name,
                "current_price": company.current_price
            },
            "rules": [
                {
                    "id": r.id,
                    "trigger_type": r.trigger_type,
                    "trigger_params": r.trigger_params,
                    "split_ratio": r.split_ratio,
                    "total_splits": r.total_splits_executed,
                    "last_split": r.last_split_date.isoformat() if r.last_split_date else None,
                    "is_enabled": r.is_enabled,
                    "status": r.status
                }
                for r in rules
            ]
        }
    finally:
        db.close()


@router.patch("/split/{rule_id}/toggle")
async def api_toggle_split_rule(
    rule_id: int,
    session_token: Optional[str] = Cookie(None)
):
    """Enable or disable a split rule."""
    auth_db = get_auth_db()
    player = get_player_from_session(auth_db, session_token)
    auth_db.close()
    
    if not player:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    db = get_db()
    try:
        rule = db.query(StockSplitRule).filter(
            StockSplitRule.id == rule_id
        ).first()
        
        if not rule:
            raise HTTPException(status_code=404, detail="Rule not found")
        
        # Verify ownership
        company = db.query(CompanyShares).filter(
            CompanyShares.id == rule.company_shares_id,
            CompanyShares.founder_id == player.id
        ).first()
        
        if not company:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        rule.is_enabled = not rule.is_enabled
        db.commit()
        
        return {
            "success": True,
            "rule_id": rule.id,
            "is_enabled": rule.is_enabled
        }
    finally:
        db.close()


# ==========================
# SECONDARY OFFERING ENDPOINTS
# ==========================

@router.post("/offering/create")
async def api_create_offering(
    request: CreateOfferingRequest,
    session_token: Optional[str] = Cookie(None)
):
    """
    Create an automated secondary offering.
    
    Example request:
    {
        "company_shares_id": 1,
        "trigger_type": "cash_need",
        "trigger_params": {
            "cash_threshold": 10000
        },
        "shares_to_issue": 5000,
        "min_price_per_share": 8.0
    }
    """
    auth_db = get_auth_db()
    player = get_player_from_session(auth_db, session_token)
    auth_db.close()
    
    if not player:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Verify ownership
    db = get_db()
    try:
        company = db.query(CompanyShares).filter(
            CompanyShares.id == request.company_shares_id,
            CompanyShares.founder_id == player.id
        ).first()
        
        if not company:
            raise HTTPException(status_code=404, detail="Company not found or not owned by you")
    finally:
        db.close()
    
    # Convert trigger type
    try:
        trigger_enum = OfferingTrigger(request.trigger_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid trigger type: {request.trigger_type}")
    
    offering = create_secondary_offering(
        company_shares_id=request.company_shares_id,
        trigger_type=trigger_enum,
        trigger_params=request.trigger_params,
        shares_to_issue=request.shares_to_issue,
        min_price_per_share=request.min_price_per_share
    )
    
    if not offering:
        raise HTTPException(status_code=400, detail="Failed to create offering")
    
    return {
        "success": True,
        "offering_id": offering.id,
        "dilution_pct": offering.dilution_pct * 100,
        "message": f"Secondary offering created for {company.ticker_symbol}"
    }


@router.get("/offering/{company_shares_id}")
async def api_get_offerings(
    company_shares_id: int,
    session_token: Optional[str] = Cookie(None)
):
    """Get all secondary offerings for a company."""
    auth_db = get_auth_db()
    player = get_player_from_session(auth_db, session_token)
    auth_db.close()
    
    if not player:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    db = get_db()
    try:
        company = db.query(CompanyShares).filter(
            CompanyShares.id == company_shares_id,
            CompanyShares.founder_id == player.id
        ).first()
        
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        offerings = db.query(SecondaryOffering).filter(
            SecondaryOffering.company_shares_id == company_shares_id
        ).all()
        
        return {
            "company": {
                "id": company.id,
                "ticker": company.ticker_symbol,
                "name": company.company_name,
                "current_price": company.current_price,
                "shares_outstanding": company.shares_outstanding
            },
            "offerings": [
                {
                    "id": o.id,
                    "trigger_type": o.trigger_type,
                    "trigger_params": o.trigger_params,
                    "shares_to_issue": o.shares_to_issue,
                    "shares_issued": o.shares_issued,
                    "min_price": o.min_price_per_share,
                    "total_raised": o.total_raised,
                    "dilution_pct": o.dilution_pct * 100,
                    "last_offering": o.last_offering_date.isoformat() if o.last_offering_date else None,
                    "is_enabled": o.is_enabled,
                    "status": o.status
                }
                for o in offerings
            ]
        }
    finally:
        db.close()


# ==========================
# HISTORY & ANALYTICS
# ==========================

@router.get("/history/{company_shares_id}")
async def api_get_corporate_action_history(
    company_shares_id: int,
    limit: int = 50,
    session_token: Optional[str] = Cookie(None)
):
    """Get corporate action history for a company."""
    auth_db = get_auth_db()
    player = get_player_from_session(auth_db, session_token)
    auth_db.close()
    
    if not player:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    db = get_db()
    try:
        company = db.query(CompanyShares).filter(
            CompanyShares.id == company_shares_id,
            CompanyShares.founder_id == player.id
        ).first()
        
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        history = db.query(CorporateActionHistory).filter(
            CorporateActionHistory.company_shares_id == company_shares_id
        ).order_by(
            CorporateActionHistory.executed_at.desc()
        ).limit(limit).all()
        
        return {
            "company": {
                "id": company.id,
                "ticker": company.ticker_symbol,
                "name": company.company_name
            },
            "actions": [
                {
                    "id": h.id,
                    "type": h.action_type,
                    "shares_affected": h.shares_affected,
                    "price_per_share": h.price_per_share,
                    "total_value": h.total_value,
                    "description": h.description,
                    "executed_at": h.executed_at.isoformat()
                }
                for h in history
            ]
        }
    finally:
        db.close()


@router.get("/dashboard")
async def api_corporate_actions_dashboard(
    session_token: Optional[str] = Cookie(None)
):
    """Get overview of all corporate actions for user's companies."""
    auth_db = get_auth_db()
    player = get_player_from_session(auth_db, session_token)
    auth_db.close()
    
    if not player:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    db = get_db()
    try:
        # Get player's companies
        companies = db.query(CompanyShares).filter(
            CompanyShares.founder_id == player.id,
            CompanyShares.is_delisted == False
        ).all()
        
        dashboard = []
        
        for company in companies:
            # Count active programs
            buyback_count = db.query(BuybackProgram).filter(
                BuybackProgram.company_shares_id == company.id,
                BuybackProgram.status == ActionStatus.ACTIVE.value
            ).count()
            
            split_count = db.query(StockSplitRule).filter(
                StockSplitRule.company_shares_id == company.id,
                StockSplitRule.status == ActionStatus.ACTIVE.value,
                StockSplitRule.is_enabled == True
            ).count()
            
            offering_count = db.query(SecondaryOffering).filter(
                SecondaryOffering.company_shares_id == company.id,
                SecondaryOffering.status == ActionStatus.ACTIVE.value,
                SecondaryOffering.is_enabled == True
            ).count()
            
            # Recent actions
            recent_actions = db.query(CorporateActionHistory).filter(
                CorporateActionHistory.company_shares_id == company.id
            ).order_by(
                CorporateActionHistory.executed_at.desc()
            ).limit(5).all()
            
            dashboard.append({
                "company": {
                    "id": company.id,
                    "ticker": company.ticker_symbol,
                    "name": company.company_name,
                    "current_price": company.current_price,
                    "shares_outstanding": company.shares_outstanding
                },
                "active_programs": {
                    "buybacks": buyback_count,
                    "splits": split_count,
                    "offerings": offering_count
                },
                "recent_actions": [
                    {
                        "type": a.action_type,
                        "description": a.description,
                        "executed_at": a.executed_at.isoformat()
                    }
                    for a in recent_actions
                ]
            })
        
        return {
            "player_id": player.id,
            "companies": dashboard
        }
    finally:
        db.close()


# ==========================
# TEMPLATES & PRESETS
# ==========================

@router.get("/templates")
async def api_get_templates():
    """
    Get pre-configured templates for common corporate action setups.
    Useful for IPO creation wizards.
    """
    return {
        "buyback_templates": [
            {
                "name": "Price Support",
                "description": "Buy when price drops 15% below target",
                "trigger_type": "price_drop",
                "trigger_params": {
                    "drop_threshold_pct": 0.15
                },
                "recommended_max_shares_pct": 0.10  # 10% of outstanding
            },
            {
                "name": "Earnings Reinvestment",
                "description": "Buy back shares with surplus profits",
                "trigger_type": "earnings_surplus",
                "trigger_params": {
                    "surplus_threshold": 50000
                },
                "recommended_max_shares_pct": 0.20
            },
            {
                "name": "Regular Schedule",
                "description": "Buy back shares every week",
                "trigger_type": "schedule",
                "trigger_params": {
                    "interval_ticks": 604800  # 1 week in ticks
                },
                "recommended_max_shares_pct": 0.05
            }
        ],
        "split_templates": [
            {
                "name": "High Price Split",
                "description": "Split when price exceeds $100",
                "trigger_type": "price_threshold",
                "trigger_params": {
                    "price_threshold": 100.0
                },
                "recommended_ratio": 2
            },
            {
                "name": "Mega Price Split",
                "description": "Split when price exceeds $500",
                "trigger_type": "price_threshold",
                "trigger_params": {
                    "price_threshold": 500.0
                },
                "recommended_ratio": 5
            }
        ],
        "offering_templates": [
            {
                "name": "Emergency Capital",
                "description": "Issue shares when cash runs low",
                "trigger_type": "cash_need",
                "trigger_params": {
                    "cash_threshold": 5000
                },
                "recommended_shares_pct": 0.10  # 10% dilution
            },
            {
                "name": "Expansion Funding",
                "description": "Issue shares to fund new businesses",
                "trigger_type": "expansion",
                "trigger_params": {
                    "business_count": 5
                },
                "recommended_shares_pct": 0.15
            }
        ]
    }


# ==========================
# REVERSE STOCK SPLIT
# ==========================

@router.post("/reverse-split/execute")
async def api_execute_reverse_split(
    session_token: Optional[str] = Cookie(None),
    company_shares_id: int = Form(...),
    ratio: int = Form(...)
):
    """Execute a manual reverse stock split (N:1 — N shares become 1, price × N)."""
    auth_db = get_auth_db()
    player = get_player_from_session(auth_db, session_token)
    auth_db.close()
    if not player:
        raise HTTPException(status_code=401, detail="Not authenticated")
    result = execute_reverse_split(company_shares_id, player.id, ratio)
    if not result["ok"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ==========================
# SPECIAL DIVIDENDS + TAX VOUCHERS
# ==========================

@router.post("/special-dividend/pay")
async def api_pay_special_dividend(
    session_token: Optional[str] = Cookie(None),
    company_shares_id: int = Form(...),
    total_amount: float = Form(...)
):
    """Pay a one-time special dividend to all shareholders and earn tax vouchers."""
    auth_db = get_auth_db()
    player = get_player_from_session(auth_db, session_token)
    auth_db.close()
    if not player:
        raise HTTPException(status_code=401, detail="Not authenticated")
    result = pay_special_dividend(company_shares_id, player.id, total_amount)
    if not result["ok"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/vouchers/balance")
async def api_voucher_balance(session_token: Optional[str] = Cookie(None)):
    auth_db = get_auth_db()
    player = get_player_from_session(auth_db, session_token)
    auth_db.close()
    if not player:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {"player_id": player.id, "voucher_balance": get_tax_voucher_balance(player.id),
            "voucher_rate": TAX_VOUCHER_RATE}


@router.post("/vouchers/redeem")
async def api_redeem_vouchers(
    session_token: Optional[str] = Cookie(None),
    amount: float = Form(...)
):
    """Redeem tax vouchers for cash from the government."""
    auth_db = get_auth_db()
    player = get_player_from_session(auth_db, session_token)
    auth_db.close()
    if not player:
        raise HTTPException(status_code=401, detail="Not authenticated")
    result = redeem_tax_vouchers(player.id, amount)
    if not result["ok"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ==========================
# ACQUISITION ENDPOINTS
# ==========================

@router.post("/acquisition/offer")
async def api_create_acquisition_offer(
    session_token: Optional[str] = Cookie(None),
    target_player_id: int = Form(...),
    offeror_company_id: int = Form(...),
    shares_offered: int = Form(...),
    stake_pct: float = Form(...)
):
    """
    Offer shares in your company for a % stake (≤50%) in another player's business income.
    Both parties see a dashboard notification.
    """
    auth_db = get_auth_db()
    player = get_player_from_session(auth_db, session_token)
    auth_db.close()
    if not player:
        raise HTTPException(status_code=401, detail="Not authenticated")
    result = create_acquisition_offer(player.id, target_player_id, offeror_company_id,
                                      shares_offered, stake_pct / 100.0)
    if not result["ok"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/acquisition/accept/{offer_id}")
async def api_accept_acquisition(
    offer_id: int,
    session_token: Optional[str] = Cookie(None)
):
    auth_db = get_auth_db()
    player = get_player_from_session(auth_db, session_token)
    auth_db.close()
    if not player:
        raise HTTPException(status_code=401, detail="Not authenticated")
    result = accept_acquisition_offer(offer_id, player.id)
    if not result["ok"]:
        raise HTTPException(status_code=400, detail=result["error"])
    mark_acquisition_notifications_seen(player.id)
    return result


@router.post("/acquisition/reject/{offer_id}")
async def api_reject_acquisition(
    offer_id: int,
    session_token: Optional[str] = Cookie(None)
):
    auth_db = get_auth_db()
    player = get_player_from_session(auth_db, session_token)
    auth_db.close()
    if not player:
        raise HTTPException(status_code=401, detail="Not authenticated")
    result = reject_acquisition_offer(offer_id, player.id)
    if not result["ok"]:
        raise HTTPException(status_code=400, detail=result["error"])
    mark_acquisition_notifications_seen(player.id)
    return result


@router.get("/acquisition/notifications")
async def api_acquisition_notifications(session_token: Optional[str] = Cookie(None)):
    auth_db = get_auth_db()
    player = get_player_from_session(auth_db, session_token)
    auth_db.close()
    if not player:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return get_acquisition_notifications(player.id)


@router.get("/acquisition/stakes")
async def api_my_stakes(session_token: Optional[str] = Cookie(None)):
    """Get all active acquisition stakes where player is acquirer or target."""
    auth_db = get_auth_db()
    player = get_player_from_session(auth_db, session_token)
    auth_db.close()
    if not player:
        raise HTTPException(status_code=401, detail="Not authenticated")
    db = get_db()
    try:
        as_acquirer = db.query(AcquisitionStake).filter(
            AcquisitionStake.acquirer_id == player.id
        ).all()
        as_target = db.query(AcquisitionStake).filter(
            AcquisitionStake.target_player_id == player.id
        ).all()
        def _stake_dict(s):
            return {"id": s.id, "acquirer_id": s.acquirer_id, "target_player_id": s.target_player_id,
                    "stake_pct": s.stake_pct * 100, "shares_paid": s.shares_paid,
                    "is_active": s.is_active, "created_at": s.created_at.isoformat(),
                    "diffuse_initiated": s.diffuse_initiated_at is not None}
        return {"as_acquirer": [_stake_dict(s) for s in as_acquirer],
                "as_target": [_stake_dict(s) for s in as_target]}
    finally:
        db.close()


# ==========================
# DIFFUSE ENDPOINTS
# ==========================

@router.post("/diffuse/initiate/{stake_id}")
async def api_initiate_diffuse(
    stake_id: int,
    session_token: Optional[str] = Cookie(None)
):
    """Acquirer gives back the stake and demands return of shares within 30 days."""
    auth_db = get_auth_db()
    player = get_player_from_session(auth_db, session_token)
    auth_db.close()
    if not player:
        raise HTTPException(status_code=401, detail="Not authenticated")
    result = initiate_diffuse(stake_id, player.id)
    if not result["ok"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/diffuse/return/{notice_id}")
async def api_complete_diffuse_return(
    notice_id: int,
    session_token: Optional[str] = Cookie(None)
):
    """Target returns the shares, resolving the diffuse notice."""
    auth_db = get_auth_db()
    player = get_player_from_session(auth_db, session_token)
    auth_db.close()
    if not player:
        raise HTTPException(status_code=401, detail="Not authenticated")
    result = complete_diffuse_return(notice_id, player.id)
    if not result["ok"]:
        raise HTTPException(status_code=400, detail=result["error"])
    mark_acquisition_notifications_seen(player.id)
    return result


# ==========================
# BANKRUPTCY ENDPOINT
# ==========================

@router.post("/bankruptcy/declare")
async def api_declare_bankruptcy(session_token: Optional[str] = Cookie(None)):
    """
    Declare bankruptcy: all assets liquidated, shares bought back at $0,
    restarted with $20,000 and one prairie plot. Red-Q shown for 30 days.
    """
    auth_db = get_auth_db()
    player = get_player_from_session(auth_db, session_token)
    auth_db.close()
    if not player:
        raise HTTPException(status_code=401, detail="Not authenticated")
    import time
    current_tick = int(time.time() / 5)
    result = declare_bankruptcy(player.id, current_tick)
    if not result["ok"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/bankruptcy/status")
async def api_bankruptcy_status(session_token: Optional[str] = Cookie(None)):
    """Check if player is currently in a bankruptcy red-Q period."""
    auth_db = get_auth_db()
    player = get_player_from_session(auth_db, session_token)
    auth_db.close()
    if not player:
        raise HTTPException(status_code=401, detail="Not authenticated")
    db = get_db()
    try:
        rec = db.query(BankruptcyRecord).filter(
            BankruptcyRecord.player_id == player.id,
            BankruptcyRecord.is_active == True
        ).first()
        if rec:
            return {"bankrupt": True, "red_q_expires": rec.red_q_expires_at.isoformat(),
                    "restart_cash": rec.restart_cash}
        return {"bankrupt": False}
    finally:
        db.close()


# Export router
__all__ = ['router']
