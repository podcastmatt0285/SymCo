"""
corporate_actions_ui.py - HTML UX for Corporate Actions

Add these endpoints to your ux.py file to give users actual forms and dashboards
for managing buybacks, splits, and secondary offerings.
"""

from fastapi import APIRouter, HTTPException, Cookie
from fastapi.responses import HTMLResponse
from typing import Optional

from corporate_actions import (
    BuybackProgram, StockSplitRule, SecondaryOffering, CorporateActionHistory,
    BuybackTrigger, SplitTrigger, OfferingTrigger, ActionStatus,
    get_db,
    VALID_REVERSE_SPLIT_RATIOS, TAX_VOUCHER_RATE,
    AcquisitionOffer, AcquisitionStake, DiffuseNotice, BankruptcyRecord,
    get_tax_voucher_balance, is_player_bankrupt,
)
from banks.brokerage_firm import CompanyShares, ShareholderPosition
from auth import get_player_from_session, get_db as get_auth_db

router = APIRouter(prefix="/corporate-actions", tags=["corporate-actions-ui"])

# ==========================
# CORPORATE ACTIONS DASHBOARD
# ==========================

@router.get("/dashboard", response_class=HTMLResponse)
async def corporate_actions_dashboard(session_token: Optional[str] = Cookie(None)):
    """Main dashboard showing all corporate actions for player's companies."""
    auth_db = get_auth_db()
    player = get_player_from_session(auth_db, session_token)
    auth_db.close()
    
    if not player:
        return HTMLResponse(content="<p>Please log in to view corporate actions.</p>", status_code=401)
    
    db = get_db()
    try:
        # Get player's companies
        companies = db.query(CompanyShares).filter(
            CompanyShares.founder_id == player.id,
            CompanyShares.is_delisted == False
        ).all()
        
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Corporate Actions Dashboard</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                * { box-sizing: border-box; }
                body { 
                    font-family: 'JetBrains Mono', monospace; 
                    margin: 0; 
                    padding: 20px 16px; 
                    background: #020617; 
                    color: #e5e7eb;
                    font-size: 14px;
                }
                .container { max-width: 1200px; margin: 0 auto; }
                .card { 
                    background: #0f172a; 
                    border: 1px solid #1e293b; 
                    padding: 20px; 
                    margin-bottom: 16px; 
                }
                .company-header { 
                    display: flex; 
                    justify-content: space-between; 
                    align-items: center; 
                    margin-bottom: 15px; 
                    border-bottom: 1px solid #1e293b; 
                    padding-bottom: 10px; 
                }
                .ticker { font-size: 1.5rem; font-weight: bold; color: #38bdf8; }
                .price { font-size: 1.2rem; color: #22c55e; }
                .action-section { 
                    margin: 15px 0; 
                    padding: 15px; 
                    background: #020617; 
                    border: 1px solid #1e293b;
                }
                .action-header { 
                    font-size: 1rem; 
                    font-weight: bold; 
                    margin-bottom: 10px; 
                    color: #94a3b8;
                }
                .badge { 
                    display: inline-block; 
                    padding: 2px 8px; 
                    border-radius: 3px; 
                    font-size: 0.7rem; 
                    margin-left: 8px;
                }
                .badge-active { background: #22c55e; color: #020617; }
                .badge-paused { background: #f59e0b; color: #020617; }
                .badge-completed { background: #64748b; color: #e5e7eb; }
                .program-item { 
                    background: #0f172a; 
                    padding: 12px; 
                    margin: 10px 0; 
                    border-left: 4px solid #38bdf8; 
                }
                .progress-bar { 
                    width: 100%; 
                    height: 8px; 
                    background: #020617; 
                    margin: 8px 0; 
                }
                .progress-fill { 
                    height: 100%; 
                    background: #38bdf8; 
                }
                .btn { 
                    padding: 6px 12px; 
                    border: none; 
                    cursor: pointer; 
                    text-decoration: none; 
                    display: inline-block; 
                    margin: 5px 5px 5px 0; 
                    font-size: 0.8rem;
                    border-radius: 3px;
                }
                .btn-primary { background: #38bdf8; color: #020617; }
                .btn-success { background: #22c55e; color: #020617; }
                .btn-warning { background: #f59e0b; color: #020617; }
                .btn-danger { background: #ef4444; color: #fff; }
                .create-section { 
                    margin-top: 15px; 
                    padding-top: 15px; 
                    border-top: 1px dashed #1e293b; 
                }
                .no-actions { 
                    color: #64748b; 
                    font-style: italic; 
                    text-align: center; 
                    padding: 20px; 
                }
                .history-item { 
                    padding: 8px; 
                    margin: 5px 0; 
                    background: #0f172a; 
                    border-left: 3px solid #64748b; 
                    font-size: 0.85rem;
                    color: #94a3b8;
                }
                
                @media (max-width: 640px) {
                    body { padding: 16px 12px; }
                    .card { padding: 16px; }
                    .company-header { flex-direction: column; align-items: flex-start; gap: 10px; }
                    .ticker { font-size: 1.2rem; }
                    .price { font-size: 1rem; }
                }
            </style>
        </head>
        <body>
            <div class="container">
                <a href="/banks/brokerage-firm" style="color: #38bdf8; text-decoration: none;">← Brokerage Firm</a>
                <h1 style="color: #e5e7eb; margin-top: 10px;">Corporate Actions Dashboard</h1>
                <p style="color: #64748b; margin-bottom: 20px;">Manage automated buybacks, splits, and offerings</p>
        """
        
        if not companies:
            html += """
                <div class="card">
                    <div class="no-actions">
                        <p>You don't have any public companies yet.</p>
                        <p>Create an IPO first, then configure corporate actions!</p>
                    </div>
                </div>
            """
        
        for company in companies:
            # Get active programs
            buybacks = db.query(BuybackProgram).filter(
                BuybackProgram.company_shares_id == company.id
            ).all()
            
            splits = db.query(StockSplitRule).filter(
                StockSplitRule.company_shares_id == company.id
            ).all()
            
            offerings = db.query(SecondaryOffering).filter(
                SecondaryOffering.company_shares_id == company.id
            ).all()
            
            # Recent history
            history = db.query(CorporateActionHistory).filter(
                CorporateActionHistory.company_shares_id == company.id
            ).order_by(CorporateActionHistory.executed_at.desc()).limit(5).all()
            
            html += f"""
                <div class="card">
                    <div class="company-header">
                        <div>
                            <span class="ticker">{company.ticker_symbol}</span>
                            <span style="color: #64748b; margin-left: 10px;">{company.company_name}</span>
                        </div>
                        <div class="price">${company.current_price:.2f}</div>
                    </div>
                    
                    <!-- Buyback Programs -->
                    <div class="action-section">
                        <div class="action-header">
                            📦 Share Buyback Programs
                        </div>
            """
            
            if buybacks:
                for buyback in buybacks:
                    progress_pct = (buyback.shares_bought / buyback.max_shares_to_buy * 100) if buyback.max_shares_to_buy > 0 else 0
                    status_badge = "badge-active" if buyback.status == "active" else ("badge-paused" if buyback.status == "paused" else "badge-completed")
                    
                    html += f"""
                        <div class="program-item">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <strong>{buyback.trigger_type.replace('_', ' ').title()}</strong>
                                    <span class="badge {status_badge}">{buyback.status.upper()}</span>
                                </div>
                                <div>
                                    {buyback.shares_bought:,} / {buyback.max_shares_to_buy:,} shares
                                </div>
                            </div>
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: {progress_pct}%"></div>
                            </div>
                            <div style="font-size: 12px; color: #7f8c8d; margin-top: 5px;">
                                Total spent: ${buyback.total_spent:,.2f} | Avg price: ${buyback.average_buy_price:.2f} | Treasury: {buyback.treasury_shares:,}
                            </div>
                    """
                    
                    if buyback.status == "active":
                        html += f'<a href="/corporate-actions/buyback/{buyback.id}/pause" class="btn btn-warning">⏸ Pause</a>'
                    elif buyback.status == "paused":
                        html += f'<a href="/corporate-actions/buyback/{buyback.id}/resume" class="btn btn-success">▶ Resume</a>'
                    
                    html += '</div>'
            else:
                html += '<div class="no-actions">No buyback programs configured</div>'
            
            html += f"""
                        <div class="create-section">
                            <a href="/corporate-actions/buyback/create/{company.id}" class="btn btn-primary">+ Create Buyback Program</a>
                        </div>
                    </div>
                    
                    <!-- Stock Splits -->
                    <div class="action-section">
                        <div class="action-header">
                            ✂️ Stock Split Rules
                        </div>
            """
            
            if splits:
                for split in splits:
                    status_badge = "badge-active" if split.is_enabled else "badge-paused"
                    
                    html += f"""
                        <div class="program-item">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <strong>{split.trigger_type.replace('_', ' ').title()}</strong>
                                    <span class="badge {status_badge}">{'ENABLED' if split.is_enabled else 'DISABLED'}</span>
                                </div>
                                <div>
                                    {split.split_ratio}:1 Split
                                </div>
                            </div>
                            <div style="font-size: 12px; color: #7f8c8d; margin-top: 5px;">
                                Executed {split.total_splits_executed} time(s)
                    """
                    
                    if split.last_split_date:
                        html += f" | Last: {split.last_split_date.strftime('%Y-%m-%d')}"
                    
                    html += '</div>'
                    
                    if split.is_enabled:
                        html += f'<a href="/corporate-actions/split/{split.id}/disable" class="btn btn-warning">⏸ Disable</a>'
                    else:
                        html += f'<a href="/corporate-actions/split/{split.id}/enable" class="btn btn-success">▶ Enable</a>'
                    
                    html += '</div>'
            else:
                html += '<div class="no-actions">No split rules configured</div>'
            
            html += f"""
                        <div class="create-section">
                            <a href="/corporate-actions/split/create/{company.id}" class="btn btn-primary">+ Create Split Rule</a>
                        </div>
                    </div>
                    
                    <!-- Secondary Offerings -->
                    <div class="action-section">
                        <div class="action-header">
                            📢 Secondary Offerings
                        </div>
            """
            
            if offerings:
                for offering in offerings:
                    progress_pct = (offering.shares_issued / offering.shares_to_issue * 100) if offering.shares_to_issue > 0 else 0
                    status_badge = "badge-active" if offering.status == "active" else "badge-completed"
                    
                    html += f"""
                        <div class="program-item">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <strong>{offering.trigger_type.replace('_', ' ').title()}</strong>
                                    <span class="badge {status_badge}">{offering.status.upper()}</span>
                                </div>
                                <div>
                                    {offering.shares_issued:,} / {offering.shares_to_issue:,} shares
                                </div>
                            </div>
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: {progress_pct}%"></div>
                            </div>
                            <div style="font-size: 12px; color: #7f8c8d; margin-top: 5px;">
                                Raised: ${offering.total_raised:,.2f} | Dilution: {offering.dilution_pct*100:.1f}%
                    """
                    
                    if offering.last_offering_date:
                        html += f" | Last: {offering.last_offering_date.strftime('%Y-%m-%d')}"
                    
                    html += '</div></div>'
            else:
                html += '<div class="no-actions">No offerings configured</div>'
            
            html += f"""
                        <div class="create-section">
                            <a href="/corporate-actions/offering/create/{company.id}" class="btn btn-primary">+ Create Offering</a>
                        </div>
                    </div>
                    
                    <!-- Recent History -->
                    <div class="action-section">
                        <div class="action-header">📜 Recent Actions</div>
            """
            
            if history:
                for action in history:
                    emoji_map = {"buyback": "📦", "split": "✂️", "secondary_offering": "📢"}
                    emoji = emoji_map.get(action.action_type, "📋")
                    
                    html += f"""
                        <div class="history-item">
                            {emoji} {action.description} - {action.executed_at.strftime('%Y-%m-%d %H:%M')}
                        </div>
                    """
            else:
                html += '<div class="no-actions">No actions executed yet</div>'
            
            html += """
                    </div>
                </div>
            """

            # --- Reverse Stock Split ---
            ratio_options = "".join(f'<option value="{r}">{r}:1</option>' for r in VALID_REVERSE_SPLIT_RATIOS)
            html += f"""
                <div class="card" style="border-left:4px solid #f59e0b;">
                    <div class="action-header">🔀 Reverse Stock Split — {company.ticker_symbol}</div>
                    <p style="color:#94a3b8;font-size:0.85rem;margin:0 0 12px 0;">
                        Consolidates all shares (yours and all shareholders') at the selected ratio. Current price: <strong>${company.current_price:.2f}</strong> &bull; Outstanding: <strong>{company.shares_outstanding:,}</strong>
                    </p>
                    <form action="/api/corporate-actions/reverse-split/execute" method="post" style="display:flex;gap:10px;align-items:flex-end;flex-wrap:wrap;">
                        <input type="hidden" name="company_shares_id" value="{company.id}">
                        <div>
                            <label style="color:#94a3b8;font-size:0.8rem;display:block;margin-bottom:4px;">Consolidation Ratio</label>
                            <select name="ratio" style="background:#0f172a;color:#e5e7eb;border:1px solid #334155;padding:6px 10px;border-radius:3px;">
                                {ratio_options}
                            </select>
                        </div>
                        <button type="submit" class="btn btn-warning" onclick="return confirm('This affects ALL shareholders. Proceed?')">Execute Reverse Split</button>
                    </form>
                </div>
            """

            # --- Special Dividend ---
            html += f"""
                <div class="card" style="border-left:4px solid #22c55e;">
                    <div class="action-header">💸 Special One-Time Dividend — {company.ticker_symbol}</div>
                    <p style="color:#94a3b8;font-size:0.85rem;margin:0 0 12px 0;">
                        Distribute a special dividend to all float shareholders proportionally. For every $1 paid, the government awards <strong style="color:#22c55e;">${TAX_VOUCHER_RATE:.4f}</strong> in redeemable tax vouchers to you.
                    </p>
                    <form action="/api/corporate-actions/special-dividend/pay" method="post" style="display:flex;gap:10px;align-items:flex-end;flex-wrap:wrap;">
                        <input type="hidden" name="company_shares_id" value="{company.id}">
                        <div>
                            <label style="color:#94a3b8;font-size:0.8rem;display:block;margin-bottom:4px;">Total Dividend Amount ($)</label>
                            <input type="number" name="total_amount" min="1" step="0.01" placeholder="e.g. 50000" style="background:#0f172a;color:#e5e7eb;border:1px solid #334155;padding:6px 10px;border-radius:3px;width:160px;" required>
                        </div>
                        <button type="submit" class="btn btn-success" onclick="return confirm('Pay this special dividend to all shareholders?')">Pay Dividend</button>
                    </form>
                </div>
            """

            # --- Acquisition Offer (send to another player) ---
            html += f"""
                <div class="card" style="border-left:4px solid #38bdf8;">
                    <div class="action-header">🤝 New Acquisition Offer — using {company.ticker_symbol} shares</div>
                    <p style="color:#94a3b8;font-size:0.85rem;margin:0 0 12px 0;">
                        Offer shares of <strong>{company.ticker_symbol}</strong> in exchange for an income stake (up to 50%) in another player's business. The target player must accept within 7 days.
                    </p>
                    <form action="/api/corporate-actions/acquisition/offer" method="post" style="display:flex;gap:10px;flex-wrap:wrap;align-items:flex-end;">
                        <input type="hidden" name="offeror_company_id" value="{company.id}">
                        <div>
                            <label style="color:#94a3b8;font-size:0.8rem;display:block;margin-bottom:4px;">Target Player ID</label>
                            <input type="number" name="target_player_id" min="1" placeholder="Player ID" style="background:#0f172a;color:#e5e7eb;border:1px solid #334155;padding:6px 10px;border-radius:3px;width:120px;" required>
                        </div>
                        <div>
                            <label style="color:#94a3b8;font-size:0.8rem;display:block;margin-bottom:4px;">Shares Offered</label>
                            <input type="number" name="shares_offered" min="1" placeholder="e.g. 1000" style="background:#0f172a;color:#e5e7eb;border:1px solid #334155;padding:6px 10px;border-radius:3px;width:130px;" required>
                        </div>
                        <div>
                            <label style="color:#94a3b8;font-size:0.8rem;display:block;margin-bottom:4px;">Income Stake % (0–50)</label>
                            <input type="number" name="stake_pct" min="0.1" max="50" step="0.1" placeholder="e.g. 25" style="background:#0f172a;color:#e5e7eb;border:1px solid #334155;padding:6px 10px;border-radius:3px;width:100px;" required>
                        </div>
                        <button type="submit" class="btn btn-primary">Send Offer →</button>
                    </form>
                </div>
            """

        # ---- Global sections (outside per-company loop) ----

        # Active Acquisition Stakes
        stakes_as_acquirer = db.query(AcquisitionStake).filter(
            AcquisitionStake.acquirer_id == player.id,
            AcquisitionStake.is_active == True
        ).all()
        stakes_as_target = db.query(AcquisitionStake).filter(
            AcquisitionStake.target_player_id == player.id,
            AcquisitionStake.is_active == True
        ).all()
        pending_offers_received = db.query(AcquisitionOffer).filter(
            AcquisitionOffer.target_player_id == player.id,
            AcquisitionOffer.status == "pending"
        ).all()
        diffuse_notices = db.query(DiffuseNotice).filter(
            DiffuseNotice.target_player_id == player.id,
            DiffuseNotice.status == "pending"
        ).all()

        html += """
            <div class="card" style="border-top:3px solid #38bdf8;margin-top:20px;">
                <h2 style="color:#38bdf8;margin:0 0 16px 0;font-size:1.1rem;">🤝 Acquisition Activity</h2>
        """

        if pending_offers_received:
            html += '<h3 style="color:#94a3b8;font-size:0.9rem;margin:0 0 10px 0;">Incoming Offers</h3>'
            for offer in pending_offers_received:
                html += f"""
                    <div class="program-item" style="border-left-color:#38bdf8;">
                        <strong style="color:#38bdf8;">{offer.stake_pct*100:.1f}%</strong> income stake requested &bull; {offer.shares_offered:,} shares offered
                        <div style="margin-top:8px;display:flex;gap:8px;">
                            <form action="/api/corporate-actions/acquisition/accept/{offer.id}" method="post" style="display:inline;">
                                <button class="btn btn-success" type="submit">Accept</button>
                            </form>
                            <form action="/api/corporate-actions/acquisition/reject/{offer.id}" method="post" style="display:inline;">
                                <button class="btn btn-danger" type="submit">Reject</button>
                            </form>
                        </div>
                    </div>"""

        if stakes_as_acquirer:
            html += '<h3 style="color:#94a3b8;font-size:0.9rem;margin:12px 0 10px 0;">Stakes You Hold</h3>'
            for stake in stakes_as_acquirer:
                html += f"""
                    <div class="program-item" style="border-left-color:#22c55e;">
                        <span style="color:#22c55e;">{stake.stake_pct*100:.1f}%</span> income stake &bull; Target player #{stake.target_player_id} &bull; Paid {stake.shares_paid:,} shares
                        <div style="margin-top:6px;">
                            <form action="/api/corporate-actions/diffuse/initiate/{stake.id}" method="post" style="display:inline;" onsubmit="return confirm('Initiate diffuse? You will demand share return within 30 days.')">
                                <button class="btn btn-warning" type="submit">⚡ Initiate Diffuse</button>
                            </form>
                        </div>
                    </div>"""

        if stakes_as_target:
            html += '<h3 style="color:#94a3b8;font-size:0.9rem;margin:12px 0 10px 0;">Stakes Held Against You</h3>'
            for stake in stakes_as_target:
                html += f"""
                    <div class="program-item" style="border-left-color:#f59e0b;">
                        Player #{stake.acquirer_id} holds <span style="color:#f59e0b;">{stake.stake_pct*100:.1f}%</span> income stake &bull; Paid you {stake.shares_paid:,} shares
                    </div>"""

        if diffuse_notices:
            html += '<h3 style="color:#f59e0b;font-size:0.9rem;margin:12px 0 10px 0;">⚠️ Pending Diffuse Notices</h3>'
            for notice in diffuse_notices:
                html += f"""
                    <div class="program-item" style="border-left-color:#ef4444;">
                        Must return <strong style="color:#ef4444;">{notice.shares_to_return:,} shares</strong> by {notice.deadline_at.strftime('%Y-%m-%d')} — value ${notice.share_value_at_notice:,.2f}
                        <div style="margin-top:6px;">
                            <form action="/api/corporate-actions/diffuse/return/{notice.id}" method="post" style="display:inline;">
                                <button class="btn btn-danger" type="submit">Return Shares Now</button>
                            </form>
                        </div>
                    </div>"""

        if not (pending_offers_received or stakes_as_acquirer or stakes_as_target or diffuse_notices):
            html += '<div class="no-actions">No active acquisitions or pending offers.</div>'

        html += '</div>'

        # Tax Vouchers
        voucher_balance = get_tax_voucher_balance(player.id)
        html += f"""
            <div class="card" style="border-top:3px solid #22c55e;margin-top:8px;">
                <h2 style="color:#22c55e;margin:0 0 12px 0;font-size:1.1rem;">🎟️ Tax Vouchers</h2>
                <p style="color:#94a3b8;font-size:0.85rem;margin:0 0 12px 0;">
                    Earned from special dividends at <strong>${TAX_VOUCHER_RATE:.4f}</strong> per $1 paid. Redeem for cash from the government at any time.
                    Current balance: <strong style="color:#22c55e;">${voucher_balance:,.4f}</strong>
                </p>
                <form action="/api/corporate-actions/vouchers/redeem" method="post" style="display:flex;gap:10px;align-items:flex-end;flex-wrap:wrap;">
                    <div>
                        <label style="color:#94a3b8;font-size:0.8rem;display:block;margin-bottom:4px;">Amount to Redeem ($)</label>
                        <input type="number" name="amount" min="0.01" step="0.01" max="{voucher_balance:.4f}" placeholder="e.g. 100" style="background:#0f172a;color:#e5e7eb;border:1px solid #334155;padding:6px 10px;border-radius:3px;width:160px;" {"required" if voucher_balance > 0 else "disabled"}>
                    </div>
                    <button type="submit" class="btn btn-success" {"disabled" if voucher_balance <= 0 else ""}>Redeem Vouchers</button>
                </form>
            </div>
        """

        # Bankruptcy
        bankrupt = is_player_bankrupt(player.id)
        if bankrupt:
            html += """
            <div class="card" style="border:2px solid #ef4444;margin-top:8px;">
                <h2 style="color:#ef4444;margin:0 0 8px 0;font-size:1.1rem;">🔴 Bankruptcy — Active</h2>
                <p style="color:#94a3b8;font-size:0.85rem;margin:0;">You are currently in a bankruptcy period. The red Q marker will be shown on the stock market next to your name for the duration.</p>
            </div>
            """
        else:
            html += """
            <div class="card" style="border:2px solid #ef4444;margin-top:8px;">
                <h2 style="color:#ef4444;margin:0 0 8px 0;font-size:1.1rem;">⚠️ Declare Bankruptcy</h2>
                <p style="color:#94a3b8;font-size:0.85rem;margin:0 0 12px 0;">
                    <strong style="color:#ef4444;">This is irreversible.</strong> All assets will be liquidated: businesses, land, districts, inventory, stocks, crypto, executives, and ETF positions.
                    All debts cleared. You will be restarted with <strong>$20,000 and one prairie land plot</strong>. A red Q will appear next to your name in the stock market for 30 days.
                    If you are a city mayor, you will be removed and a member vote will determine your replacement.
                </p>
                <form action="/api/corporate-actions/bankruptcy/declare" method="post" onsubmit="return confirm('FINAL WARNING: This permanently liquidates ALL your assets and restarts your account with $20,000. This CANNOT be undone. Type OK to confirm.') && prompt('Type BANKRUPT to confirm') === 'BANKRUPT'">
                    <button type="submit" class="btn btn-danger" style="font-size:1rem;padding:10px 24px;">💀 Declare Bankruptcy</button>
                </form>
            </div>
            """

        html += """
            </div>
        </body>
        </html>
        """
        
        return HTMLResponse(content=html)
    
    finally:
        db.close()


# ==========================
# CREATE BUYBACK FORM
# ==========================

@router.get("/buyback/create/{company_id}", response_class=HTMLResponse)
async def create_buyback_form(company_id: int, session_token: Optional[str] = Cookie(None)):
    """Form to create a new buyback program."""
    auth_db = get_auth_db()
    player = get_player_from_session(auth_db, session_token)
    auth_db.close()
    
    if not player:
        return HTMLResponse(content="<p>Please log in.</p>", status_code=401)
    
    db = get_db()
    try:
        company = db.query(CompanyShares).filter(
            CompanyShares.id == company_id,
            CompanyShares.founder_id == player.id
        ).first()
        
        if not company:
            return HTMLResponse(content="<p>Company not found.</p>", status_code=404)
        
        max_shares = int(company.shares_outstanding * 0.30)
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Create Buyback Program - {company.ticker_symbol}</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                * {{ box-sizing: border-box; }}
                body {{ font-family: 'JetBrains Mono', monospace; margin: 0; padding: 20px 16px; background: #020617; color: #e5e7eb; font-size: 14px; }}
                .container {{ max-width: 800px; margin: 0 auto; }}
                .card {{ background: #0f172a; border: 1px solid #1e293b; padding: 30px; }}
                h1 {{ color: #e5e7eb; }}
                .form-group {{ margin: 20px 0; }}
                label {{ display: block; margin-bottom: 5px; font-weight: bold; color: #94a3b8; font-size: 0.9rem; }}
                input, select {{ width: 100%; padding: 10px; border: 1px solid #1e293b; background: #020617; color: #e5e7eb; font-size: 0.9rem; font-family: inherit; }}
                input:focus, select:focus {{ outline: none; border-color: #38bdf8; }}
                .help-text {{ font-size: 0.85rem; color: #64748b; margin-top: 5px; }}
                .btn {{ padding: 12px 24px; border: none; cursor: pointer; font-size: 0.9rem; font-family: inherit; margin: 10px 5px 10px 0; border-radius: 3px; }}
                .btn-primary {{ background: #38bdf8; color: #020617; }}
                .btn-secondary {{ background: #64748b; color: #e5e7eb; }}
                .trigger-config {{ display: none; padding: 15px; background: #020617; border: 1px solid #1e293b; margin-top: 10px; }}
                .ticker {{ color: #38bdf8; font-weight: bold; }}
                a {{ color: #38bdf8; text-decoration: none; }}
                a:hover {{ text-decoration: underline; }}
                
                @media (max-width: 640px) {{
                    body {{ padding: 16px 12px; }}
                    .card {{ padding: 20px; }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <a href="/corporate-actions/dashboard">← Dashboard</a>
                <div class="card" style="margin-top: 15px;">
                <h1>📦 Create Buyback Program</h1>
                <p>Company: <span class="ticker">{company.ticker_symbol}</span> - {company.company_name}</p>
                <p style="color: #64748b;">Current Price: <strong>${company.current_price:.2f}</strong></p>
                
                <form id="buyback-form">
                    <div class="form-group">
                        <label>Trigger Type</label>
                        <select id="trigger-type" required>
                            <option value="">-- Select Trigger --</option>
                            <option value="price_drop">Price Support (Buy when price drops)</option>
                            <option value="earnings_surplus">Earnings Reinvestment (Buy with surplus cash)</option>
                            <option value="schedule">Regular Schedule (Buy periodically)</option>
                        </select>
                    </div>
                    
                    <!-- Price Drop Config -->
                    <div id="config-price-drop" class="trigger-config">
                        <div class="form-group">
                            <label>Target Price</label>
                            <input type="number" id="target-price" step="0.01" value="{company.current_price:.2f}">
                            <div class="help-text">The price you want to support (typically IPO price or higher)</div>
                        </div>
                        <div class="form-group">
                            <label>Drop Threshold (%)</label>
                            <input type="number" id="drop-threshold" value="15" min="5" max="50">
                            <div class="help-text">Buy when price drops this % below target (e.g., 15% = buy at $8.50 if target is $10)</div>
                        </div>
                    </div>
                    
                    <!-- Earnings Surplus Config -->
                    <div id="config-earnings-surplus" class="trigger-config">
                        <div class="form-group">
                            <label>Surplus Threshold ($)</label>
                            <input type="number" id="surplus-threshold" value="50000" step="1000">
                            <div class="help-text">Buy shares when your cash balance exceeds this amount</div>
                        </div>
                    </div>
                    
                    <!-- Schedule Config -->
                    <div id="config-schedule" class="trigger-config">
                        <div class="form-group">
                            <label>Frequency</label>
                            <select id="schedule-frequency">
                                <option value="3600">Every Hour</option>
                                <option value="86400">Every Day</option>
                                <option value="604800">Every Week</option>
                            </select>
                            <div class="help-text">How often to attempt buybacks</div>
                        </div>
                    </div>
                    
                    <!-- Common Settings -->
                    <div class="form-group">
                        <label>Maximum Shares to Buy</label>
                        <input type="number" id="max-shares" required min="1" max="{max_shares}">
                        <div class="help-text">Total program size (max 30% of outstanding = {max_shares:,} shares)</div>
                    </div>
                    
                    <div class="form-group">
                        <label>Maximum Price per Share</label>
                        <input type="number" id="max-price" step="0.01" required value="{company.current_price * 1.2:.2f}">
                        <div class="help-text">Won't buy above this price (typically 20% above current)</div>
                    </div>
                    
                    <div style="margin-top: 30px;">
                        <button type="submit" class="btn btn-primary">Create Buyback Program</button>
                        <a href="/corporate-actions/dashboard" class="btn btn-secondary">Cancel</a>
                    </div>
                </form>
                </div>
            </div>
            
            <script>
                const triggerType = document.getElementById('trigger-type');
                const configs = {{
                    'price_drop': document.getElementById('config-price-drop'),
                    'earnings_surplus': document.getElementById('config-earnings-surplus'),
                    'schedule': document.getElementById('config-schedule')
                }};
                
                triggerType.addEventListener('change', () => {{
                    Object.values(configs).forEach(el => el.style.display = 'none');
                    if (configs[triggerType.value]) {{
                        configs[triggerType.value].style.display = 'block';
                    }}
                }});
                
                document.getElementById('buyback-form').addEventListener('submit', async (e) => {{
                    e.preventDefault();
                    
                    const trigger = triggerType.value;
                    let trigger_params = {{}};
                    
                    if (trigger === 'price_drop') {{
                        trigger_params = {{
                            target_price: parseFloat(document.getElementById('target-price').value),
                            drop_threshold_pct: parseFloat(document.getElementById('drop-threshold').value) / 100
                        }};
                    }} else if (trigger === 'earnings_surplus') {{
                        trigger_params = {{
                            surplus_threshold: parseFloat(document.getElementById('surplus-threshold').value)
                        }};
                    }} else if (trigger === 'schedule') {{
                        trigger_params = {{
                            interval_ticks: parseInt(document.getElementById('schedule-frequency').value)
                        }};
                    }}
                    
                    const response = await fetch('/api/corporate-actions/buyback/create', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{
                            company_shares_id: {company.id},
                            trigger_type: trigger,
                            trigger_params: trigger_params,
                            max_shares_to_buy: parseInt(document.getElementById('max-shares').value),
                            max_price_per_share: parseFloat(document.getElementById('max-price').value)
                        }})
                    }});
                    
                    if (response.ok) {{
                        alert('Buyback program created successfully!');
                        window.location.href = '/corporate-actions/dashboard';
                    }} else {{
                        const error = await response.json();
                        alert('Error: ' + error.detail);
                    }}
                }});
            </script>
        </body>
        </html>
        """
        
        return HTMLResponse(content=html)
    
    finally:
        db.close()


# ==========================
# CREATE SPLIT FORM
# ==========================

@router.get("/split/create/{company_id}", response_class=HTMLResponse)
async def create_split_form(company_id: int, session_token: Optional[str] = Cookie(None)):
    """Form to create a new split rule."""
    auth_db = get_auth_db()
    player = get_player_from_session(auth_db, session_token)
    auth_db.close()
    
    if not player:
        return HTMLResponse(content="<p>Please log in.</p>", status_code=401)
    
    db = get_db()
    try:
        company = db.query(CompanyShares).filter(
            CompanyShares.id == company_id,
            CompanyShares.founder_id == player.id
        ).first()
        
        if not company:
            return HTMLResponse(content="<p>Company not found.</p>", status_code=404)
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Create Split Rule - {company.ticker_symbol}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
                .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; }}
                h1 {{ color: #2c3e50; }}
                .form-group {{ margin: 20px 0; }}
                label {{ display: block; margin-bottom: 5px; font-weight: bold; color: #34495e; }}
                input, select {{ width: 100%; padding: 10px; border: 1px solid #bdc3c7; border-radius: 5px; font-size: 16px; }}
                .help-text {{ font-size: 12px; color: #7f8c8d; margin-top: 5px; }}
                .btn {{ padding: 12px 24px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; margin: 10px 5px; }}
                .btn-primary {{ background: #3498db; color: white; }}
                .btn-secondary {{ background: #95a5a6; color: white; }}
                .ticker {{ color: #3498db; font-weight: bold; }}
                .example {{ background: #ecf0f1; padding: 10px; border-radius: 5px; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>✂️ Create Stock Split Rule</h1>
                <p>Company: <span class="ticker">{company.ticker_symbol}</span> - {company.company_name}</p>
                <p>Current Price: <strong>${company.current_price:.2f}</strong></p>
                
                <form id="split-form">
                    <div class="form-group">
                        <label>Price Threshold</label>
                        <input type="number" id="price-threshold" step="1" required value="100">
                        <div class="help-text">Split when share price reaches this level</div>
                    </div>
                    
                    <div class="form-group">
                        <label>Split Ratio</label>
                        <select id="split-ratio" required>
                            <option value="2">2-for-1 (Double shares, half price)</option>
                            <option value="3">3-for-1 (Triple shares, 1/3 price)</option>
                            <option value="5">5-for-1 (5x shares, 1/5 price)</option>
                            <option value="10">10-for-1 (10x shares, 1/10 price)</option>
                        </select>
                        <div class="help-text">Higher ratios for very expensive stocks</div>
                    </div>
                    
                    <div class="example">
                        <strong>Example:</strong> If price hits $100 with a 2:1 split:
                        <ul>
                            <li>Shareholders get 2x their shares</li>
                            <li>Price becomes $50</li>
                            <li>Total value unchanged</li>
                            <li>Makes stock more affordable for retail investors</li>
                        </ul>
                    </div>
                    
                    <div style="margin-top: 30px;">
                        <button type="submit" class="btn btn-primary">Create Split Rule</button>
                        <a href="/corporate-actions/dashboard" class="btn btn-secondary">Cancel</a>
                    </div>
                </form>
            </div>
            
            <script>
                document.getElementById('split-form').addEventListener('submit', async (e) => {{
                    e.preventDefault();
                    
                    const response = await fetch('/api/corporate-actions/split/create', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{
                            company_shares_id: {company.id},
                            trigger_type: 'price_threshold',
                            trigger_params: {{
                                price_threshold: parseFloat(document.getElementById('price-threshold').value)
                            }},
                            split_ratio: parseInt(document.getElementById('split-ratio').value)
                        }})
                    }});
                    
                    if (response.ok) {{
                        alert('Split rule created successfully!');
                        window.location.href = '/corporate-actions/dashboard';
                    }} else {{
                        const error = await response.json();
                        alert('Error: ' + error.detail);
                    }}
                }});
            </script>
        </body>
        </html>
        """
        
        return HTMLResponse(content=html)
    
    finally:
        db.close()


# ==========================
# CREATE OFFERING FORM
# ==========================

@router.get("/offering/create/{company_id}", response_class=HTMLResponse)
async def create_offering_form(company_id: int, session_token: Optional[str] = Cookie(None)):
    """Form to create a new secondary offering."""
    auth_db = get_auth_db()
    player = get_player_from_session(auth_db, session_token)
    auth_db.close()
    
    if not player:
        return HTMLResponse(content="<p>Please log in.</p>", status_code=401)
    
    db = get_db()
    try:
        company = db.query(CompanyShares).filter(
            CompanyShares.id == company_id,
            CompanyShares.founder_id == player.id
        ).first()
        
        if not company:
            return HTMLResponse(content="<p>Company not found.</p>", status_code=404)
        
        max_dilution_shares = int(company.shares_outstanding * 0.20)
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Create Secondary Offering - {company.ticker_symbol}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
                .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; }}
                h1 {{ color: #2c3e50; }}
                .form-group {{ margin: 20px 0; }}
                label {{ display: block; margin-bottom: 5px; font-weight: bold; color: #34495e; }}
                input, select {{ width: 100%; padding: 10px; border: 1px solid #bdc3c7; border-radius: 5px; font-size: 16px; }}
                .help-text {{ font-size: 12px; color: #7f8c8d; margin-top: 5px; }}
                .btn {{ padding: 12px 24px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; margin: 10px 5px; }}
                .btn-primary {{ background: #3498db; color: white; }}
                .btn-secondary {{ background: #95a5a6; color: white; }}
                .ticker {{ color: #3498db; font-weight: bold; }}
                .warning {{ background: #fff3cd; padding: 15px; border-left: 4px solid #f39c12; margin: 15px 0; }}
                .trigger-config {{ display: none; padding: 15px; background: #ecf0f1; border-radius: 5px; margin-top: 10px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>📢 Create Secondary Offering</h1>
                <p>Company: <span class="ticker">{company.ticker_symbol}</span> - {company.company_name}</p>
                <p>Current Price: <strong>${company.current_price:.2f}</strong></p>
                <p>Outstanding Shares: <strong>{company.shares_outstanding:,}</strong></p>
                
                <div class="warning">
                    <strong>⚠️ Warning:</strong> Secondary offerings dilute existing shareholders.
                    Only use when you need capital to grow the business!
                </div>
                
                <form id="offering-form">
                    <div class="form-group">
                        <label>Trigger Type</label>
                        <select id="trigger-type" required>
                            <option value="">-- Select Trigger --</option>
                            <option value="cash_need">Emergency Capital (When cash runs low)</option>
                            <option value="expansion">Expansion Funding (When growing business)</option>
                        </select>
                    </div>
                    
                    <!-- Cash Need Config -->
                    <div id="config-cash-need" class="trigger-config">
                        <div class="form-group">
                            <label>Cash Threshold ($)</label>
                            <input type="number" id="cash-threshold" value="5000" step="1000">
                            <div class="help-text">Issue shares when your cash balance drops below this</div>
                        </div>
                    </div>
                    
                    <!-- Expansion Config -->
                    <div id="config-expansion" class="trigger-config">
                        <div class="form-group">
                            <label>Business Count Trigger</label>
                            <input type="number" id="business-count" value="5" min="1">
                            <div class="help-text">Issue shares when you have this many active businesses</div>
                        </div>
                    </div>
                    
                    <div class="form-group">
                        <label>Shares to Issue</label>
                        <input type="number" id="shares-to-issue" required min="1" max="{max_dilution_shares}">
                        <div class="help-text">Max 20% dilution = {max_dilution_shares:,} shares</div>
                    </div>
                    
                    <div class="form-group">
                        <label>Minimum Price per Share</label>
                        <input type="number" id="min-price" step="0.01" required value="{company.current_price * 0.8:.2f}">
                        <div class="help-text">Won't issue below this price (typically 80% of current)</div>
                    </div>
                    
                    <div id="estimated-raise" style="background: #d4edda; padding: 15px; border-radius: 5px; margin: 15px 0; display: none;">
                        <strong>Estimated Raise:</strong> <span id="raise-amount">$0</span> (after 3% fee)
                    </div>
                    
                    <div style="margin-top: 30px;">
                        <button type="submit" class="btn btn-primary">Create Secondary Offering</button>
                        <a href="/corporate-actions/dashboard" class="btn btn-secondary">Cancel</a>
                    </div>
                </form>
            </div>
            
            <script>
                const triggerType = document.getElementById('trigger-type');
                const configs = {{
                    'cash_need': document.getElementById('config-cash-need'),
                    'expansion': document.getElementById('config-expansion')
                }};
                
                triggerType.addEventListener('change', () => {{
                    Object.values(configs).forEach(el => el.style.display = 'none');
                    if (configs[triggerType.value]) {{
                        configs[triggerType.value].style.display = 'block';
                    }}
                }});
                
                // Calculate estimated raise
                document.getElementById('shares-to-issue').addEventListener('input', () => {{
                    const shares = parseInt(document.getElementById('shares-to-issue').value) || 0;
                    const price = {company.current_price};
                    const gross = shares * price;
                    const net = gross * 0.97; // After 3% fee
                    document.getElementById('raise-amount').textContent = '$' + net.toFixed(2).replace(/\\B(?=(\\d{{3}})+(?!\\d))/g, ',');
                    document.getElementById('estimated-raise').style.display = shares > 0 ? 'block' : 'none';
                }});
                
                document.getElementById('offering-form').addEventListener('submit', async (e) => {{
                    e.preventDefault();
                    
                    const trigger = triggerType.value;
                    let trigger_params = {{}};
                    
                    if (trigger === 'cash_need') {{
                        trigger_params = {{
                            cash_threshold: parseFloat(document.getElementById('cash-threshold').value)
                        }};
                    }} else if (trigger === 'expansion') {{
                        trigger_params = {{
                            business_count: parseInt(document.getElementById('business-count').value)
                        }};
                    }}
                    
                    const response = await fetch('/api/corporate-actions/offering/create', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{
                            company_shares_id: {company.id},
                            trigger_type: trigger,
                            trigger_params: trigger_params,
                            shares_to_issue: parseInt(document.getElementById('shares-to-issue').value),
                            min_price_per_share: parseFloat(document.getElementById('min-price').value)
                        }})
                    }});
                    
                    if (response.ok) {{
                        alert('Secondary offering created successfully!');
                        window.location.href = '/corporate-actions/dashboard';
                    }} else {{
                        const error = await response.json();
                        alert('Error: ' + error.detail);
                    }}
                }});
            </script>
        </body>
        </html>
        """
        
        return HTMLResponse(content=html)
    
    finally:
        db.close()


# ==========================
# ACTION ENDPOINTS (Pause/Resume/Enable/Disable)
# ==========================

@router.get("/buyback/{program_id}/pause")
async def pause_buyback(program_id: int, session_token: Optional[str] = Cookie(None)):
    """Pause a buyback program."""
    auth_db = get_auth_db()
    player = get_player_from_session(auth_db, session_token)
    auth_db.close()
    
    if not player:
        return HTMLResponse(content="<p>Not authorized</p>", status_code=401)
    
    db = get_db()
    try:
        program = db.query(BuybackProgram).filter(BuybackProgram.id == program_id).first()
        if program:
            company = db.query(CompanyShares).filter(
                CompanyShares.id == program.company_shares_id,
                CompanyShares.founder_id == player.id
            ).first()
            
            if company:
                program.status = ActionStatus.PAUSED.value
                db.commit()
    finally:
        db.close()
    
    return HTMLResponse(content='<script>window.location.href="/corporate-actions/dashboard"</script>')


@router.get("/buyback/{program_id}/resume")
async def resume_buyback(program_id: int, session_token: Optional[str] = Cookie(None)):
    """Resume a paused buyback program."""
    auth_db = get_auth_db()
    player = get_player_from_session(auth_db, session_token)
    auth_db.close()
    
    if not player:
        return HTMLResponse(content="<p>Not authorized</p>", status_code=401)
    
    db = get_db()
    try:
        program = db.query(BuybackProgram).filter(BuybackProgram.id == program_id).first()
        if program:
            company = db.query(CompanyShares).filter(
                CompanyShares.id == program.company_shares_id,
                CompanyShares.founder_id == player.id
            ).first()
            
            if company:
                program.status = ActionStatus.ACTIVE.value
                db.commit()
    finally:
        db.close()
    
    return HTMLResponse(content='<script>window.location.href="/corporate-actions/dashboard"</script>')


@router.get("/split/{rule_id}/disable")
async def disable_split(rule_id: int, session_token: Optional[str] = Cookie(None)):
    """Disable a split rule."""
    auth_db = get_auth_db()
    player = get_player_from_session(auth_db, session_token)
    auth_db.close()
    
    if not player:
        return HTMLResponse(content="<p>Not authorized</p>", status_code=401)
    
    db = get_db()
    try:
        rule = db.query(StockSplitRule).filter(StockSplitRule.id == rule_id).first()
        if rule:
            company = db.query(CompanyShares).filter(
                CompanyShares.id == rule.company_shares_id,
                CompanyShares.founder_id == player.id
            ).first()
            
            if company:
                rule.is_enabled = False
                db.commit()
    finally:
        db.close()
    
    return HTMLResponse(content='<script>window.location.href="/corporate-actions/dashboard"</script>')


@router.get("/split/{rule_id}/enable")
async def enable_split(rule_id: int, session_token: Optional[str] = Cookie(None)):
    """Enable a split rule."""
    auth_db = get_auth_db()
    player = get_player_from_session(auth_db, session_token)
    auth_db.close()
    
    if not player:
        return HTMLResponse(content="<p>Not authorized</p>", status_code=401)
    
    db = get_db()
    try:
        rule = db.query(StockSplitRule).filter(StockSplitRule.id == rule_id).first()
        if rule:
            company = db.query(CompanyShares).filter(
                CompanyShares.id == rule.company_shares_id,
                CompanyShares.founder_id == player.id
            ).first()
            
            if company:
                rule.is_enabled = True
                db.commit()
    finally:
        db.close()
    
    return HTMLResponse(content='<script>window.location.href="/corporate-actions/dashboard"</script>')


# Export router
__all__ = ['router']
