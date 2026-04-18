"""
corporate_actions_ui.py - HTML UX for Corporate Actions
"""

from fastapi import APIRouter, HTTPException, Cookie, Request
from fastapi.responses import HTMLResponse
from typing import Optional

from corporate_actions import (
    BuybackProgram, StockSplitRule, SecondaryOffering, CorporateActionHistory,
    BuybackTrigger, SplitTrigger, OfferingTrigger, ActionStatus,
    get_db,
    VALID_REVERSE_SPLIT_RATIOS, TAX_VOUCHER_RATE, ACQUISITION_OFFER_DAYS, DIFFUSE_RETURN_DAYS,
    ACQUISITION_DEFAULT_LOCKUP_DAYS, ACQUISITION_TERM_OPTIONS,
    AcquisitionOffer, AcquisitionStake, DiffuseNotice, BankruptcyRecord, StakeRenegotiation,
    get_tax_voucher_balance, is_player_bankrupt,
)
from banks.brokerage_firm import CompanyShares, ShareholderPosition
from auth import get_player_from_session, get_db as get_auth_db
from ux import _nav_loader_html as _nav_loader

router = APIRouter(prefix="/corporate-actions", tags=["corporate-actions-ui"])

# ── Shared CSS used across all sub-pages ──────────────────────────────────────
_BASE_CSS = """
* { box-sizing: border-box; }
body {
    font-family: 'JetBrains Mono', 'Courier New', monospace;
    margin: 0; padding: 0;
    background: #020617;
    color: #e5e7eb;
    font-size: 14px;
    min-height: 100vh;
}
.page-wrap { max-width: 1100px; margin: 0 auto; padding: 20px 16px 60px; }
.topbar {
    display: flex; align-items: center; gap: 16px;
    padding: 12px 16px;
    background: #0a1628;
    border-bottom: 1px solid #1e293b;
    flex-wrap: wrap;
}
.topbar-brand { color: #d4af37; font-weight: bold; font-size: 0.85rem; letter-spacing: 0.04em; }
.topbar-sep { color: #334155; }
.topbar-crumb { color: #94a3b8; font-size: 0.8rem; }
.topbar a { color: #38bdf8; text-decoration: none; font-size: 0.8rem; }
.topbar a:hover { text-decoration: underline; }
.topbar-right { margin-left: auto; display: flex; gap: 12px; align-items: center; }

.page-header { margin: 24px 0 8px; }
.page-header h1 { color: #e5e7eb; font-size: 1.4rem; margin: 0 0 6px 0; font-weight: bold; }
.page-header .subtitle { color: #64748b; font-size: 0.85rem; margin: 0; line-height: 1.6; }

.section-card {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 6px;
    padding: 20px 22px;
    margin-bottom: 14px;
}
.section-card.accent-blue  { border-left: 3px solid #38bdf8; }
.section-card.accent-green { border-left: 3px solid #22c55e; }
.section-card.accent-amber { border-left: 3px solid #f59e0b; }
.section-card.accent-red   { border-left: 3px solid #ef4444; }
.section-card.accent-gold  { border-left: 3px solid #d4af37; }
.section-card.accent-purple{ border-left: 3px solid #a78bfa; }

.section-title {
    font-size: 0.95rem; font-weight: bold;
    color: #e5e7eb; margin: 0 0 4px 0;
    display: flex; align-items: center; gap: 8px;
}
.section-desc {
    color: #64748b; font-size: 0.78rem; line-height: 1.6;
    margin: 0 0 14px 0;
}
.info-box {
    background: #0a1628;
    border: 1px solid #1e293b;
    border-radius: 4px;
    padding: 10px 14px;
    margin-bottom: 14px;
    font-size: 0.78rem;
    color: #64748b;
    line-height: 1.7;
}
.info-box strong { color: #94a3b8; }
.info-box.tip { border-left: 3px solid #38bdf8; }
.info-box.warning { border-left: 3px solid #f59e0b; color: #f59e0b; }
.info-box.success { border-left: 3px solid #22c55e; }

.prog-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; flex-wrap: wrap; gap: 6px; }
.prog-bar { height: 5px; background: #1e293b; border-radius: 3px; overflow: hidden; margin-bottom: 6px; }
.prog-fill { height: 100%; border-radius: 3px; transition: width .3s; }

.badge {
    display: inline-block;
    padding: 2px 9px;
    border-radius: 10px;
    font-size: 0.68rem;
    font-weight: bold;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}
.badge-active    { background: rgba(34,197,94,.15); color: #22c55e; border: 1px solid rgba(34,197,94,.3); }
.badge-paused    { background: rgba(245,158,11,.15); color: #f59e0b; border: 1px solid rgba(245,158,11,.3); }
.badge-completed { background: rgba(100,116,139,.15); color: #64748b; border: 1px solid rgba(100,116,139,.3); }
.badge-enabled   { background: rgba(34,197,94,.15); color: #22c55e; border: 1px solid rgba(34,197,94,.3); }
.badge-disabled  { background: rgba(100,116,139,.15); color: #64748b; border: 1px solid rgba(100,116,139,.3); }
.badge-pending   { background: rgba(56,189,248,.15); color: #38bdf8; border: 1px solid rgba(56,189,248,.3); }

.program-row {
    background: #070f1e;
    border: 1px solid #1e293b;
    border-radius: 4px;
    padding: 12px 14px;
    margin-bottom: 10px;
}
.program-row:last-child { margin-bottom: 0; }
.program-meta { color: #64748b; font-size: 0.76rem; margin: 6px 0; line-height: 1.7; }
.program-meta span { color: #94a3b8; }

.btn {
    display: inline-block;
    padding: 6px 14px;
    border: none; border-radius: 4px;
    cursor: pointer;
    text-decoration: none;
    font-size: 0.78rem;
    font-weight: bold;
    font-family: inherit;
    margin: 4px 4px 0 0;
    transition: opacity .15s;
    letter-spacing: 0.02em;
}
.btn:hover { opacity: 0.85; }
.btn-primary  { background: #38bdf8; color: #020617; }
.btn-success  { background: #22c55e; color: #020617; }
.btn-warning  { background: #f59e0b; color: #020617; }
.btn-danger   { background: #ef4444; color: #fff; }
.btn-ghost    { background: transparent; color: #64748b; border: 1px solid #334155; }
.btn-gold     { background: #d4af37; color: #020617; }

.empty-state {
    text-align: center;
    padding: 20px;
    color: #334155;
    font-size: 0.82rem;
    line-height: 1.8;
}
.empty-state p { margin: 0 0 4px 0; }

.stat-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
    gap: 10px;
    margin-bottom: 14px;
}
.stat-box {
    background: #070f1e;
    border: 1px solid #1e293b;
    border-radius: 4px;
    padding: 12px 14px;
    text-align: center;
}
.stat-label { color: #475569; font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px; }
.stat-value { color: #e5e7eb; font-size: 1.1rem; font-weight: bold; }
.stat-value.green { color: #22c55e; }
.stat-value.blue  { color: #38bdf8; }
.stat-value.amber { color: #f59e0b; }
.stat-value.gold  { color: #d4af37; }

.company-header-card {
    background: linear-gradient(135deg, #07111f, #0f172a);
    border: 1px solid #1e293b;
    border-radius: 8px;
    padding: 18px 22px;
    margin-bottom: 12px;
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 14px;
}
.company-ticker { font-size: 1.8rem; font-weight: bold; color: #38bdf8; line-height: 1; }
.company-name   { color: #94a3b8; font-size: 0.85rem; margin-top: 4px; }
.company-price  { font-size: 1.3rem; font-weight: bold; color: #22c55e; }
.company-outstanding { color: #64748b; font-size: 0.78rem; margin-top: 4px; }

.form-inline { display: flex; gap: 10px; align-items: flex-end; flex-wrap: wrap; }
.form-group { display: flex; flex-direction: column; gap: 4px; }
.form-label { color: #94a3b8; font-size: 0.75rem; }
.form-input {
    background: #070f1e;
    color: #e5e7eb;
    border: 1px solid #334155;
    border-radius: 3px;
    padding: 7px 10px;
    font-family: inherit;
    font-size: 0.82rem;
}
.form-input:focus { outline: none; border-color: #38bdf8; }
select.form-input { cursor: pointer; }

.divider { border: none; border-top: 1px solid #1e293b; margin: 16px 0; }

@media (max-width: 640px) {
    .page-wrap { padding: 16px 12px 40px; }
    .company-ticker { font-size: 1.4rem; }
    .company-price  { font-size: 1rem; }
    .form-inline { flex-direction: column; }
    .form-input  { width: 100%; }
}
"""

# ==========================
# CORPORATE ACTIONS DASHBOARD
# ==========================

@router.get("/dashboard", response_class=HTMLResponse)
async def corporate_actions_dashboard(
    request: Request,
    session_token: Optional[str] = Cookie(None)
):
    """Main dashboard showing all corporate actions for player's companies."""
    auth_db = get_auth_db()
    player = get_player_from_session(auth_db, session_token)
    auth_db.close()

    if not player:
        return HTMLResponse(
            content='<script>location.href="/login"</script>',
            status_code=302
        )

    t4_reward = request.query_params.get("t4_reward") == "1"
    t5_reward = request.query_params.get("t5_reward") == "1"

    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)

    db = get_db()
    try:
        companies = db.query(CompanyShares).filter(
            CompanyShares.founder_id == player.id,
            CompanyShares.is_delisted == False
        ).all()

        voucher_balance = get_tax_voucher_balance(player.id)

        # ── page shell open ────────────────────────────────────────────────────
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Corporate Actions — Wadsworth</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>{_BASE_CSS}</style>
</head>
<body>
<!-- top nav bar -->
<div class="topbar">
    <span class="topbar-brand">WADSWORTH</span>
    <span class="topbar-sep">/</span>
    <a href="/">Dashboard</a>
    <span class="topbar-sep">/</span>
    <a href="/banks/brokerage-firm">Brokerage Firm</a>
    <span class="topbar-sep">/</span>
    <span class="topbar-crumb">Corporate Actions</span>
    <div class="topbar-right">
        <span style="color:#64748b;font-size:0.75rem;">Tax Voucher Balance:</span>
        <span style="color:#22c55e;font-size:0.82rem;font-weight:bold;">{fmt_usd(voucher_balance, disp)}</span>
    </div>
</div>

<div class="page-wrap">
<div class="page-header">
    <h1>Corporate Actions</h1>
    <p class="subtitle">
        Automate share management for your public companies — buybacks, splits, secondary offerings,
        dividends, and acquisitions. All programs run automatically on game ticks based on the
        conditions you configure. Monitor execution history and adjust triggers at any time.
    </p>
</div>

<div class="info-box tip" style="margin-bottom:18px;">
    <strong>How Corporate Actions Work</strong><br>
    Each program you set up watches for a trigger condition (price level, cash balance, schedule) and
    executes automatically when met. You don't need to be online — the game engine processes them
    every few minutes. Use the dashboard below to create, pause, or cancel programs at any time.
</div>
"""

        # ── Tutorial 4 reward banner ───────────────────────────────────────────
        if t4_reward:
            html += f"""
<div style="background:linear-gradient(135deg,#061620,#0f172a);border:2px solid #38bdf8;
            border-radius:6px;padding:18px 22px;margin-bottom:18px;">
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;flex-wrap:wrap;">
        <span style="background:#38bdf8;color:#020617;padding:3px 10px;border-radius:10px;
                     font-size:0.7rem;font-weight:bold;letter-spacing:0.05em;">TUTORIAL 4 COMPLETE</span>
        <strong style="color:#38bdf8;">ETFs &amp; Market Indices</strong>
    </div>
    <p style="color:#e5e7eb;margin:0 0 6px 0;line-height:1.6;">
        The government has awarded you a
        <strong style="color:#22c55e;">Tax Voucher worth {fmt_usd(100_000.0, disp)}</strong>
        for completing Tutorial 4. It's been added to your Tax Voucher balance below —
        redeem it any time for instant cash.
    </p>
    <p style="color:#64748b;font-size:0.8rem;margin:0;">
        Tax vouchers never expire. Redeem now or hold them for when you need liquidity.
    </p>
</div>
"""

        # ── Tutorial 5 reward banner ───────────────────────────────────────────
        if t5_reward:
            html += f"""
<div style="background:linear-gradient(135deg,#1a0e00,#0f172a);border:2px solid #f59e0b;
            border-radius:6px;padding:18px 22px;margin-bottom:18px;">
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;flex-wrap:wrap;">
        <span style="background:#f59e0b;color:#020617;padding:3px 10px;border-radius:10px;
                     font-size:0.7rem;font-weight:bold;letter-spacing:0.05em;">TUTORIAL 5 COMPLETE</span>
        <strong style="color:#f59e0b;">Acquisitions &amp; Income Stakes</strong>
    </div>
    <p style="color:#e5e7eb;margin:0 0 6px 0;line-height:1.6;">
        The government has awarded you a
        <strong style="color:#22c55e;">Tax Voucher worth {fmt_usd(150_000.0, disp)}</strong>
        for completing Tutorial 5. It's been added to your Tax Voucher balance below —
        redeem it any time for instant cash.
    </p>
    <p style="color:#64748b;font-size:0.8rem;margin:0;">
        Tax vouchers never expire. Redeem now or hold them for when you need liquidity.
    </p>
</div>
"""

        # ── Tutorial 5 overlay ─────────────────────────────────────────────────
        try:
            from tutorial_ux import get_tutorial5_overlay_html
            html += get_tutorial5_overlay_html(player, "corporate_actions_dashboard")
        except Exception:
            pass

        # ── No companies state ─────────────────────────────────────────────────
        if not companies:
            html += """
<div class="section-card">
    <div class="empty-state" style="padding:40px 20px;">
        <p style="font-size:1.1rem;color:#475569;margin-bottom:8px;">No public companies yet.</p>
        <p style="color:#334155;margin-bottom:20px;">
            Corporate actions require at least one IPO-listed company.<br>
            Go to the Brokerage Firm to list your first company.
        </p>
        <a href="/banks/brokerage-firm" class="btn btn-primary">Go to Brokerage Firm →</a>
    </div>
</div>
"""

        # ── Per-company sections ───────────────────────────────────────────────
        for company in companies:
            buybacks  = db.query(BuybackProgram).filter(BuybackProgram.company_shares_id == company.id).all()
            splits    = db.query(StockSplitRule).filter(StockSplitRule.company_shares_id == company.id).all()
            offerings = db.query(SecondaryOffering).filter(SecondaryOffering.company_shares_id == company.id).all()
            history   = db.query(CorporateActionHistory).filter(
                CorporateActionHistory.company_shares_id == company.id
            ).order_by(CorporateActionHistory.executed_at.desc()).limit(8).all()
            founder_pos = db.query(ShareholderPosition).filter(
                ShareholderPosition.company_shares_id == company.id,
                ShareholderPosition.player_id == player.id
            ).first()
            founder_pos_shares = founder_pos.shares_owned if founder_pos else 0

            active_buybacks   = sum(1 for b in buybacks  if b.status == "active")
            active_splits     = sum(1 for s in splits    if s.is_enabled)
            active_offerings  = sum(1 for o in offerings if o.status == "active")

            html += f"""
<!-- ═══ {company.ticker_symbol} ═══════════════════════════════════════════ -->
<div class="company-header-card">
    <div>
        <div class="company-ticker">{company.ticker_symbol}</div>
        <div class="company-name">{company.company_name}</div>
        <div class="company-outstanding">{company.shares_outstanding:,} shares outstanding</div>
    </div>
    <div style="text-align:right;">
        <div class="company-price">{fmt_usd(company.current_price, disp)}</div>
        <div style="color:#64748b;font-size:0.75rem;margin-top:4px;">
            Mkt cap ≈ {fmt_usd(company.current_price * company.shares_outstanding, disp)}
        </div>
        <div style="margin-top:8px;display:flex;gap:8px;justify-content:flex-end;flex-wrap:wrap;">
            <span style="color:#64748b;font-size:0.72rem;">{active_buybacks} buyback{'s' if active_buybacks!=1 else ''} active</span>
            <span style="color:#64748b;font-size:0.72rem;">{active_splits} split rule{'s' if active_splits!=1 else ''}</span>
            <span style="color:#64748b;font-size:0.72rem;">{active_offerings} offering{'s' if active_offerings!=1 else ''} active</span>
        </div>
    </div>
</div>

<!-- Buyback Programs -->
<div class="section-card accent-blue" style="margin-bottom:10px;">
    <div class="section-title">Share Buyback Programs</div>
    <div class="section-desc">
        A buyback program instructs the game to automatically repurchase your company's shares
        from the open market using company cash. Repurchased shares become treasury shares,
        reducing float and typically supporting the share price. You can hold or cancel them later.
        Maximum program size: 30% of outstanding shares ({int(company.shares_outstanding*0.30):,} shares).
    </div>
"""
            if buybacks:
                for bb in buybacks:
                    pct = (bb.shares_bought / bb.max_shares_to_buy * 100) if bb.max_shares_to_buy > 0 else 0
                    badge_cls = "badge-active" if bb.status == "active" else ("badge-paused" if bb.status == "paused" else "badge-completed")
                    trigger_label = bb.trigger_type.replace("_", " ").title()
                    html += f"""
    <div class="program-row">
        <div class="prog-row">
            <div>
                <strong style="color:#e5e7eb;">{trigger_label}</strong>
                <span class="badge {badge_cls}" style="margin-left:8px;">{bb.status.upper()}</span>
            </div>
            <span style="color:#94a3b8;font-size:0.8rem;">{bb.shares_bought:,} / {bb.max_shares_to_buy:,} shares</span>
        </div>
        <div class="prog-bar"><div class="prog-fill" style="background:#38bdf8;width:{pct:.1f}%;"></div></div>
        <div class="program-meta">
            Spent: <span>{fmt_usd(bb.total_spent, disp)}</span> &nbsp;|&nbsp;
            Avg price: <span>{fmt_usd(bb.average_buy_price, disp)}</span> &nbsp;|&nbsp;
            Treasury shares held: <span>{bb.treasury_shares:,}</span>
        </div>
        <div>
"""
                    if bb.status == "active":
                        html += f'<a href="/corporate-actions/buyback/{bb.id}/pause" class="btn btn-warning">Pause</a>'
                    elif bb.status == "paused":
                        html += f'<a href="/corporate-actions/buyback/{bb.id}/resume" class="btn btn-success">Resume</a>'
                    html += "</div></div>"
            else:
                html += '<div class="empty-state"><p>No buyback programs configured yet.</p><p style="color:#475569;">Create one to automatically support your share price during dips.</p></div>'

            html += f"""
    <div style="margin-top:14px;padding-top:14px;border-top:1px solid #1e293b;">
        <a href="/corporate-actions/buyback/create/{company.id}" class="btn btn-primary">+ New Buyback Program</a>
    </div>
</div>

<!-- Stock Split Rules -->
<div class="section-card accent-amber" style="margin-bottom:10px;">
    <div class="section-title">Stock Split Rules</div>
    <div class="section-desc">
        A forward split automatically multiplies all shareholders' holdings when your share price
        reaches a set threshold. For example: a 2-for-1 split at {fmt_usd(100, disp)} doubles everyone's
        shares and halves the price to {fmt_usd(50, disp)}, leaving total value unchanged.
        Splits make your stock more accessible to smaller investors and are a signal of growth.
    </div>
"""
            if splits:
                for sp in splits:
                    badge_cls = "badge-enabled" if sp.is_enabled else "badge-disabled"
                    last_date = sp.last_split_date.strftime("%Y-%m-%d") if sp.last_split_date else "never"
                    html += f"""
    <div class="program-row">
        <div class="prog-row">
            <div>
                <strong style="color:#e5e7eb;">{sp.split_ratio}-for-1 split</strong>
                <span class="badge {badge_cls}" style="margin-left:8px;">{'ENABLED' if sp.is_enabled else 'DISABLED'}</span>
            </div>
            <span style="color:#94a3b8;font-size:0.8rem;">Trigger: {sp.trigger_type.replace('_',' ').title()}</span>
        </div>
        <div class="program-meta">
            Executed: <span>{sp.total_splits_executed} time(s)</span> &nbsp;|&nbsp;
            Last split: <span>{last_date}</span>
        </div>
        <div>
"""
                    if sp.is_enabled:
                        html += f'<a href="/corporate-actions/split/{sp.id}/disable" class="btn btn-warning">Disable</a>'
                    else:
                        html += f'<a href="/corporate-actions/split/{sp.id}/enable" class="btn btn-success">Enable</a>'
                    html += "</div></div>"
            else:
                html += '<div class="empty-state"><p>No split rules configured yet.</p><p style="color:#475569;">Set a price threshold to automatically split when your stock gets expensive.</p></div>'

            html += f"""
    <div style="margin-top:14px;padding-top:14px;border-top:1px solid #1e293b;">
        <a href="/corporate-actions/split/create/{company.id}" class="btn btn-primary">+ New Split Rule</a>
    </div>
</div>

<!-- Secondary Offerings -->
<div class="section-card accent-purple" style="margin-bottom:10px;">
    <div class="section-title">Secondary Offerings</div>
    <div class="section-desc">
        A secondary offering issues new shares into the market to raise capital. Unlike a buyback,
        this <em>dilutes</em> existing shareholders — each share represents a slightly smaller slice
        of the company. Use sparingly and only when capital is genuinely needed for growth.
        Maximum dilution per offering: 20% of outstanding shares ({int(company.shares_outstanding*0.20):,} shares).
    </div>
"""
            if offerings:
                for of in offerings:
                    pct = (of.shares_issued / of.shares_to_issue * 100) if of.shares_to_issue > 0 else 0
                    badge_cls = "badge-active" if of.status == "active" else "badge-completed"
                    last_date = of.last_offering_date.strftime("%Y-%m-%d") if of.last_offering_date else "—"
                    html += f"""
    <div class="program-row">
        <div class="prog-row">
            <div>
                <strong style="color:#e5e7eb;">{of.trigger_type.replace('_',' ').title()}</strong>
                <span class="badge {badge_cls}" style="margin-left:8px;">{of.status.upper()}</span>
            </div>
            <span style="color:#94a3b8;font-size:0.8rem;">{of.shares_issued:,} / {of.shares_to_issue:,} shares issued</span>
        </div>
        <div class="prog-bar"><div class="prog-fill" style="background:#a78bfa;width:{pct:.1f}%;"></div></div>
        <div class="program-meta">
            Raised: <span>{fmt_usd(of.total_raised, disp)}</span> &nbsp;|&nbsp;
            Dilution: <span>{of.dilution_pct*100:.1f}%</span> &nbsp;|&nbsp;
            Last: <span>{last_date}</span>
        </div>
    </div>
"""
            else:
                html += '<div class="empty-state"><p>No secondary offerings configured yet.</p><p style="color:#475569;">Issue new shares to raise capital — use with caution as it dilutes existing holders.</p></div>'

            html += f"""
    <div style="margin-top:14px;padding-top:14px;border-top:1px solid #1e293b;">
        <a href="/corporate-actions/offering/create/{company.id}" class="btn btn-primary">+ New Secondary Offering</a>
    </div>
</div>

<!-- Reverse Split -->
<div class="section-card accent-amber" style="margin-bottom:10px;">
    <div class="section-title">Reverse Stock Split</div>
    <div class="section-desc">
        A reverse split consolidates shares at a ratio — a 4:1 reverse split converts every 4 shares
        into 1 share and multiplies the price by 4. Total value is unchanged, but the share count drops
        and price rises. Used to prevent penny-stock status or meet exchange listing minimums.
        <strong style="color:#f59e0b;">This immediately affects ALL shareholders.</strong>
    </div>
    <div class="info-box warning">
        One-time manual action — executes immediately when you click the button.
        Cannot be undone. Confirm you understand before proceeding.
    </div>
"""
            ratio_options = "".join(f'<option value="{r}">{r}:1 — {company.shares_outstanding // r:,} shares @ approx {fmt_usd(company.current_price * r, disp)}</option>' for r in VALID_REVERSE_SPLIT_RATIOS)
            html += f"""
    <form action="/api/corporate-actions/reverse-split/execute" method="post">
        <input type="hidden" name="company_shares_id" value="{company.id}">
        <div class="form-inline">
            <div class="form-group">
                <label class="form-label">Consolidation Ratio</label>
                <select name="ratio" class="form-input">{ratio_options}</select>
            </div>
            <button type="submit" class="btn btn-warning"
                    onclick="return confirm('Execute reverse split for {company.ticker_symbol}? This immediately affects ALL shareholders and cannot be undone.')">
                Execute Reverse Split
            </button>
        </div>
    </form>
</div>

<!-- Special Dividend -->
<div class="section-card accent-green" style="margin-bottom:10px;">
    <div class="section-title">Special One-Time Dividend</div>
    <div class="section-desc">
        Pay an immediate cash dividend to all float shareholders, distributed proportionally
        by their share count. The government rewards you for distributing capital:
        for every <strong style="color:#22c55e;">{disp["symbol"]}1</strong> you pay out,
        you receive <strong style="color:#22c55e;">{disp["symbol"]}{TAX_VOUCHER_RATE:.4f}</strong>
        in redeemable Tax Vouchers ({TAX_VOUCHER_RATE*100:.2f}% back) — essentially a tax rebate
        that you can redeem below for instant cash at any time.
    </div>
    <div class="info-box success">
        Tax Vouchers from dividends never expire. Pay a large dividend now and redeem
        the vouchers later when you need liquidity.
    </div>
    <form action="/api/corporate-actions/special-dividend/pay" method="post">
        <input type="hidden" name="company_shares_id" value="{company.id}">
        <div class="form-inline">
            <div class="form-group">
                <label class="form-label">Total Dividend Amount ({disp["symbol"]})</label>
                <input type="number" name="total_amount" min="1" step="0.01"
                       placeholder="e.g. 50,000" class="form-input" style="width:160px;" required>
            </div>
            <button type="submit" class="btn btn-success"
                    onclick="return confirm('Pay this special dividend to all float shareholders of {company.ticker_symbol}?')">
                Pay Dividend
            </button>
        </div>
    </form>
</div>

<!-- Acquisition Offer -->
<div class="section-card accent-blue" style="margin-bottom:20px;">
    <div class="section-title">Send Acquisition Offer</div>
    <div class="info-box tip" style="margin-bottom:14px;">
        <strong>How acquisitions work:</strong> You offer shares of <strong style="color:#38bdf8;">{company.ticker_symbol}</strong>
        (and optionally cash) to another player in exchange for an ongoing income stake in their business — similar to how
        one company buys a revenue share in another. The target reviews your offer and can <strong>accept</strong>,
        <strong>reject</strong>, or <strong>counter-offer</strong> with different terms. Once accepted, a percentage of their
        business income flows to you automatically every 24 hours. You can later initiate a <em>diffuse</em> to end the
        arrangement and reclaim your shares (the target has {DIFFUSE_RETURN_DAYS} days to return them or a financial lien is created).
        Offers expire after {ACQUISITION_OFFER_DAYS} days — any escrowed cash is refunded automatically.
    </div>
    <form action="/api/corporate-actions/acquisition/offer" method="post" id="acq-offer-form-{company.id}">
        <input type="hidden" name="offeror_company_id" value="{company.id}">
        <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:14px;margin-bottom:14px;">
            <div class="form-group">
                <label class="form-label">Target Player ID</label>
                <input type="number" name="target_player_id" min="1" placeholder="e.g. 42"
                       class="form-input" id="acq-target-{company.id}" required
                       oninput="acqFetchVal('{company.id}',this.value)">
                <div style="font-size:0.72rem;color:#475569;margin-top:3px;">Find player IDs on Leaderboard</div>
            </div>
            <div class="form-group">
                <label class="form-label">{company.ticker_symbol} Shares to Offer</label>
                <input type="number" name="shares_offered" min="1" placeholder="e.g. 1,000"
                       class="form-input" id="acq-shares-{company.id}"
                       oninput="acqCalc('{company.id}',{company.current_price})" required>
                <div style="font-size:0.72rem;color:#475569;margin-top:3px;">
                    Current price: <strong style="color:#38bdf8;">{disp["symbol"]}{company.current_price:,.4f}</strong>
                    &nbsp;·&nbsp; You hold: <strong style="color:#e5e7eb;">{founder_pos_shares:,} shares</strong>
                </div>
            </div>
            <div class="form-group">
                <label class="form-label">Income Stake % Requested</label>
                <input type="number" name="stake_pct" min="0.1" max="50" step="0.1"
                       placeholder="e.g. 25" class="form-input" id="acq-pct-{company.id}"
                       oninput="acqCalc('{company.id}',{company.current_price})" required>
                <div style="font-size:0.72rem;color:#475569;margin-top:3px;">Max 50% · % of their net business income</div>
            </div>
            <div class="form-group">
                <label class="form-label">Cash Sweetener (optional)</label>
                <input type="number" name="cash_component" min="0" step="0.01" value="0"
                       placeholder="e.g. 50,000" class="form-input" id="acq-cash-{company.id}"
                       oninput="acqCalc('{company.id}',{company.current_price})">
                <div style="font-size:0.72rem;color:#475569;margin-top:3px;">Extra cash included — escrowed until outcome</div>
            </div>
            <div class="form-group">
                <label class="form-label">Deal Term</label>
                <select name="term_days" class="form-input">
                    <option value="0">Perpetual (no end date)</option>
                    <option value="30">30 days</option>
                    <option value="60">60 days</option>
                    <option value="90">90 days</option>
                    <option value="180">180 days</option>
                    <option value="365">365 days (1 year)</option>
                </select>
                <div style="font-size:0.72rem;color:#475569;margin-top:3px;">Stake auto-closes when term expires</div>
            </div>
            <div class="form-group">
                <label class="form-label">Lock-Up Period (days)</label>
                <input type="number" name="lock_up_days" min="0" max="365" value="7"
                       placeholder="7" class="form-input">
                <div style="font-size:0.72rem;color:#475569;margin-top:3px;">Minimum hold before exit is allowed (default 7)</div>
            </div>
        </div>
        <div class="form-group" style="margin-bottom:14px;">
            <label class="form-label">Deal Memo (optional — visible to recipient)</label>
            <textarea name="offer_memo" maxlength="500" placeholder="Explain why this deal benefits both parties, your company growth plans, etc."
                      class="form-input" style="width:100%;height:64px;resize:vertical;font-size:0.82rem;"></textarea>
        </div>
        <!-- Valuation basis panel -->
        <div id="acq-valuation-{company.id}" style="display:none;background:#0f172a;border:1px solid #1e293b;
             border-radius:6px;padding:10px 14px;margin-bottom:10px;font-size:0.82rem;">
            <div style="color:#94a3b8;margin-bottom:4px;font-weight:600;">Target Income Estimate (30-day basis)</div>
            <div id="acq-val-body-{company.id}" style="color:#e5e7eb;"></div>
        </div>
        <div id="acq-preview-{company.id}" style="display:none;background:#0f172a;border:1px solid #1e293b;
             border-radius:6px;padding:10px 14px;margin-bottom:14px;font-size:0.82rem;">
            <span style="color:#64748b;">Offer value preview: </span>
            <span id="acq-preview-val-{company.id}" style="color:#38bdf8;font-weight:bold;"></span>
        </div>
        <button type="submit" class="btn btn-primary"
                onclick="return confirm('Send this acquisition offer? The cash component (if any) will be escrowed from your balance immediately.')">
            Send Acquisition Offer
        </button>
    </form>
    <script>
    var _acqSym = '{disp["symbol"]}';
    function acqCalc(cid, price) {{
        var sym = _acqSym;
        var shares = parseFloat(document.getElementById('acq-shares-'+cid)?.value) || 0;
        var cash = parseFloat(document.getElementById('acq-cash-'+cid)?.value) || 0;
        var pct = parseFloat(document.getElementById('acq-pct-'+cid)?.value) || 0;
        var total = shares * price + cash;
        var prev = document.getElementById('acq-preview-'+cid);
        var val = document.getElementById('acq-preview-val-'+cid);
        var valPanel = document.getElementById('acq-valuation-'+cid);
        var valBody = document.getElementById('acq-val-body-'+cid);
        if (total > 0 && prev && val) {{
            var shareStr = shares > 0 ? shares.toLocaleString() + ' shares @ ' + sym + price.toFixed(4) + ' = ' + sym + (shares*price).toLocaleString(undefined,{{minimumFractionDigits:2,maximumFractionDigits:2}}) : '';
            var cashStr = cash > 0 ? ' + ' + sym + cash.toLocaleString(undefined,{{minimumFractionDigits:2,maximumFractionDigits:2}}) + ' cash' : '';
            var totalStr = ' = Total offer: ' + sym + total.toLocaleString(undefined,{{minimumFractionDigits:2,maximumFractionDigits:2}});
            val.textContent = shareStr + cashStr + totalStr;
            prev.style.display = 'block';
        }} else if (prev) {{
            prev.style.display = 'none';
        }}
        // Update implied return if valuation data exists
        if (valBody && valBody.dataset.dailyAvg && pct > 0) {{
            var daily = parseFloat(valBody.dataset.dailyAvg) * (pct / 100);
            var annual = daily * 365;
            var multiple = total > 0 ? (annual / total).toFixed(2) : '—';
            valBody.dataset.impliedLine = 'Your ' + pct.toFixed(1) + '% → ~' + _acqSym + daily.toLocaleString(undefined,{{maximumFractionDigits:0}}) + '/day · ~' + _acqSym + annual.toLocaleString(undefined,{{maximumFractionDigits:0}}) + '/yr · ' + multiple + 'x implied multiple';
            _acqRefreshValBody(cid);
        }}
    }}
    function _acqRefreshValBody(cid) {{
        var valBody = document.getElementById('acq-val-body-'+cid);
        if (!valBody) return;
        var html = '';
        if (valBody.dataset.summaryLine) html += '<div>' + valBody.dataset.summaryLine + '</div>';
        if (valBody.dataset.impliedLine) html += '<div style="color:#38bdf8;margin-top:3px;">' + valBody.dataset.impliedLine + '</div>';
        valBody.innerHTML = html;
    }}
    window._acqValTimer = window._acqValTimer || {{}};
    function acqFetchVal(cid, targetId) {{
        clearTimeout(window._acqValTimer[cid]);
        if (!targetId || parseInt(targetId) < 1) return;
        window._acqValTimer[cid] = setTimeout(function() {{
            fetch('/api/corporate-actions/acquisition/valuation/' + parseInt(targetId))
                .then(function(r){{return r.json();}})
                .then(function(d){{
                    if (!d.ok) return;
                    var valPanel = document.getElementById('acq-valuation-'+cid);
                    var valBody = document.getElementById('acq-val-body-'+cid);
                    if (!valPanel || !valBody) return;
                    var fmt = function(n){{return _acqSym+Math.round(n).toLocaleString();}};
                    valBody.dataset.dailyAvg = d.daily_avg;
                    valBody.dataset.summaryLine = '30-day net: ' + fmt(d.net_income) + ' · Daily avg: ' + fmt(d.daily_avg) + ' · Annual est: ' + fmt(d.annual_est);
                    _acqRefreshValBody(cid);
                    valPanel.style.display = 'block';
                    // Trigger implied return calc if pct is already filled
                    var pct = parseFloat(document.getElementById('acq-pct-'+cid)?.value) || 0;
                    if (pct > 0) acqCalc(cid, {company.current_price});
                }}).catch(function(){{}});
        }}, 600);
    }}
    </script>
</div>

<!-- Recent History -->
<div class="section-card" style="margin-bottom:28px;">
    <div class="section-title" style="margin-bottom:10px;">Execution History — {company.ticker_symbol}</div>
    <div class="section-desc">The last 8 automated actions executed for this company by the game engine.</div>
"""
            if history:
                emoji_map = {{"buyback": "BB", "split": "SP", "secondary_offering": "SO"}}
                for act in history:
                    tag = emoji_map.get(act.action_type, "CA")
                    html += f"""
    <div style="display:flex;gap:12px;align-items:flex-start;padding:8px 0;border-bottom:1px solid #0f172a;">
        <span style="background:#1e293b;color:#64748b;font-size:0.68rem;font-weight:bold;
                     padding:2px 6px;border-radius:3px;flex-shrink:0;margin-top:1px;">{tag}</span>
        <div>
            <span style="color:#94a3b8;font-size:0.82rem;">{act.description}</span>
            <span style="color:#334155;font-size:0.72rem;display:block;">{act.executed_at.strftime('%Y-%m-%d %H:%M')}</span>
        </div>
    </div>
"""
            else:
                html += '<div class="empty-state"><p>No actions executed yet.</p><p style="color:#475569;">Actions appear here once your programs trigger for the first time.</p></div>'

            html += "</div>"

        # ── Global: Acquisition Activity ──────────────────────────────────────
        from datetime import datetime as _dt
        _now = _dt.utcnow()

        stakes_as_acquirer  = db.query(AcquisitionStake).filter(
            AcquisitionStake.acquirer_id == player.id, AcquisitionStake.is_active == True).all()
        stakes_as_target    = db.query(AcquisitionStake).filter(
            AcquisitionStake.target_player_id == player.id, AcquisitionStake.is_active == True).all()
        # Incoming: pending or countered-back-to-pending offers for this player
        pending_offers_recv = db.query(AcquisitionOffer).filter(
            AcquisitionOffer.target_player_id == player.id,
            AcquisitionOffer.status == "pending").all()
        # Counter-offers this player sent that are now awaiting the original offeror's decision
        countered_outgoing  = db.query(AcquisitionOffer).filter(
            AcquisitionOffer.offeror_id == player.id,
            AcquisitionOffer.status == "countered").all()
        diffuse_notices     = db.query(DiffuseNotice).filter(
            DiffuseNotice.target_player_id == player.id, DiffuseNotice.status == "pending").all()
        # Recent completed/rejected/expired offers for history
        recent_offers_hist  = db.query(AcquisitionOffer).filter(
            (AcquisitionOffer.offeror_id == player.id) | (AcquisitionOffer.target_player_id == player.id),
            AcquisitionOffer.status.in_(["accepted", "rejected", "expired", "diffused"])
        ).order_by(AcquisitionOffer.responded_at.desc()).limit(6).all()

        def _ticker_for(company_id):
            c = db.query(CompanyShares).filter(CompanyShares.id == company_id).first()
            return (c.ticker_symbol, c.company_name, c.current_price) if c else (f"#{company_id}", "Unknown", 0.0)

        def _days_until(dt):
            if not dt:
                return "—"
            delta = (dt - _now).total_seconds()
            if delta < 0:
                return "Expired"
            d = int(delta // 86400)
            h = int((delta % 86400) // 3600)
            return f"{d}d {h}h"

        def _time_ago(dt):
            if not dt:
                return "never"
            delta = (_now - dt).total_seconds()
            if delta < 3600:
                return f"{int(delta//60)}m ago"
            if delta < 86400:
                return f"{int(delta//3600)}h ago"
            return f"{int(delta//86400)}d ago"

        html += """
<div class="section-card accent-blue" style="margin-bottom:14px;">
    <div class="section-title" style="margin-bottom:4px;">Acquisition Activity</div>
    <div class="info-box tip" style="margin-bottom:14px;">
        <strong>Acquisitions</strong> let you buy a revenue stake in another player's business by offering
        shares (and optionally cash). Once active, a percentage of their net income flows to you every 24 hours.
        To end the arrangement, initiate a <strong>Diffuse</strong> — the other party has 30 days to return your
        shares or a financial lien is issued against them. You can also negotiate by sending a
        <strong>Counter-Offer</strong> with different terms.
    </div>
"""
        # ── Incoming Offers (pending) ──────────────────────────────────────────
        if pending_offers_recv:
            html += '<div style="color:#38bdf8;font-size:0.78rem;font-weight:bold;margin-bottom:8px;text-transform:uppercase;letter-spacing:0.05em;">Incoming Offers — Action Required</div>'
            for offer in pending_offers_recv:
                ticker, cname, cprice = _ticker_for(offer.offeror_company_id)
                share_val = cprice * offer.shares_offered
                cash_c = offer.cash_component or 0.0
                total_val = share_val + cash_c
                memo = (offer.offer_memo or '').strip()
                expires_str = _days_until(offer.expires_at)
                expires_color = "#ef4444" if expires_str in ("Expired", "—") else ("#f59e0b" if expires_str.startswith("0d") else "#64748b")
                html += f"""
    <div class="program-row" style="border-left-color:#38bdf8;">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px;margin-bottom:8px;">
            <div>
                <span style="background:#38bdf8;color:#020617;padding:2px 8px;border-radius:10px;
                             font-size:0.68rem;font-weight:bold;letter-spacing:0.04em;">INCOMING OFFER</span>
                <span style="color:#64748b;font-size:0.72rem;margin-left:10px;">from Player #{offer.offeror_id}</span>
            </div>
            <span style="font-size:0.72rem;color:{expires_color};">Expires: {expires_str}</span>
        </div>
        <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:8px;margin-bottom:10px;">
            <div style="background:#0f172a;border-radius:4px;padding:8px 10px;">
                <div style="color:#64748b;font-size:0.68rem;text-transform:uppercase;letter-spacing:0.04em;">Shares Offered</div>
                <div style="color:#38bdf8;font-weight:bold;font-size:0.9rem;">{offer.shares_offered:,} {ticker}</div>
                <div style="color:#64748b;font-size:0.72rem;">{cname[:24]}</div>
            </div>
            <div style="background:#0f172a;border-radius:4px;padding:8px 10px;">
                <div style="color:#64748b;font-size:0.68rem;text-transform:uppercase;letter-spacing:0.04em;">Share Value</div>
                <div style="color:#e5e7eb;font-weight:bold;font-size:0.9rem;">{fmt_usd(share_val, disp)}</div>
                <div style="color:#64748b;font-size:0.72rem;">@ {fmt_usd(cprice, disp)} / share</div>
            </div>
            {'<div style="background:#0f172a;border-radius:4px;padding:8px 10px;"><div style="color:#64748b;font-size:0.68rem;text-transform:uppercase;letter-spacing:0.04em;">Cash Sweetener</div><div style="color:#22c55e;font-weight:bold;font-size:0.9rem;">' + fmt_usd(cash_c, disp) + '</div><div style="color:#64748b;font-size:0.72rem;">paid to you on accept</div></div>' if cash_c > 0 else ''}
            <div style="background:#0f172a;border-radius:4px;padding:8px 10px;">
                <div style="color:#64748b;font-size:0.68rem;text-transform:uppercase;letter-spacing:0.04em;">Total Offer Value</div>
                <div style="color:#d4af37;font-weight:bold;font-size:0.9rem;">{fmt_usd(total_val, disp)}</div>
                <div style="color:#64748b;font-size:0.72rem;">shares + cash combined</div>
            </div>
            <div style="background:#0f172a;border-radius:4px;padding:8px 10px;">
                <div style="color:#64748b;font-size:0.68rem;text-transform:uppercase;letter-spacing:0.04em;">Stake Requested</div>
                <div style="color:#f59e0b;font-weight:bold;font-size:0.9rem;">{offer.stake_pct*100:.1f}% of income</div>
                <div style="color:#64748b;font-size:0.72rem;">swept daily from your earnings</div>
            </div>
        </div>
        {'<div style="background:#0a1628;border:1px solid #1e3a5f;border-radius:4px;padding:8px 12px;margin-bottom:10px;font-size:0.82rem;color:#94a3b8;font-style:italic;">' + memo + '</div>' if memo else ''}
        <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px;">
            <form action="/api/corporate-actions/acquisition/accept/{offer.id}" method="post" style="display:inline;"
                  onsubmit="return confirm('Accept this offer? {offer.stake_pct*100:.1f}% of your net income will flow to Player #{offer.offeror_id} every 24 hours.')">
                <button class="btn btn-success" type="submit">Accept Offer</button>
            </form>
            <form action="/api/corporate-actions/acquisition/reject/{offer.id}" method="post" style="display:inline;"
                  onsubmit="return confirm('Reject this offer? The offeror will be notified and any escrowed cash returned to them.')">
                <button class="btn btn-danger" type="submit">Reject</button>
            </form>
        </div>
        <details style="margin-top:6px;">
            <summary style="cursor:pointer;color:#94a3b8;font-size:0.8rem;user-select:none;">
                ↔ Counter-Offer — propose different terms
            </summary>
            <div style="background:#0a1628;border:1px solid #1e293b;border-radius:4px;padding:12px;margin-top:8px;">
                <div style="color:#94a3b8;font-size:0.78rem;margin-bottom:10px;">
                    Propose new terms. The offeror will be notified and can accept or decline —
                    if declined the original offer reverts to pending and you can still accept/reject it.
                </div>
                <form action="/api/corporate-actions/acquisition/counter/{offer.id}" method="post">
                    <div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:10px;">
                        <div class="form-group">
                            <label class="form-label">Counter Shares Requested</label>
                            <input type="number" name="counter_shares" min="1"
                                   placeholder="e.g. {offer.shares_offered:,}" value="{offer.shares_offered}"
                                   class="form-input" style="width:140px;" required>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Counter Stake %</label>
                            <input type="number" name="counter_stake_pct" min="0.1" max="50" step="0.1"
                                   placeholder="e.g. {offer.stake_pct*100:.1f}" value="{offer.stake_pct*100:.1f}"
                                   class="form-input" style="width:110px;" required>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Cash Also Requested</label>
                            <input type="number" name="counter_cash" min="0" step="0.01" value="0"
                                   placeholder="e.g. 10,000" class="form-input" style="width:130px;">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Counter Term (days)</label>
                            <select name="counter_term_days" class="form-input" style="width:120px;">
                                <option value="0">Keep original</option>
                                <option value="30">30 days</option>
                                <option value="60">60 days</option>
                                <option value="90">90 days</option>
                                <option value="180">180 days</option>
                                <option value="365">365 days</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Counter Lock-up (days)</label>
                            <input type="number" name="counter_lock_up_days" min="0" max="365"
                                   placeholder="keep original" class="form-input" style="width:110px;">
                        </div>
                        <button type="submit" class="btn btn-primary" style="align-self:flex-end;margin-bottom:4px;">Send Counter</button>
                    </div>
                </form>
            </div>
        </details>
    </div>
"""

        # ── Countered Outgoing (awaiting other party's response to your counter) ─
        if countered_outgoing:
            html += '<div style="color:#a78bfa;font-size:0.78rem;font-weight:bold;margin:12px 0 8px;text-transform:uppercase;letter-spacing:0.05em;">Your Counter-Offers — Awaiting Response</div>'
            for offer in countered_outgoing:
                ticker, cname, cprice = _ticker_for(offer.offeror_company_id)
                counter_cash = offer.counter_cash or 0.0
                expires_str = _days_until(offer.expires_at)
                html += f"""
    <div class="program-row" style="border-left-color:#a78bfa;">
        <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px;margin-bottom:8px;">
            <span style="background:#a78bfa;color:#020617;padding:2px 8px;border-radius:10px;
                         font-size:0.68rem;font-weight:bold;">COUNTER-OFFER PENDING</span>
            <span style="color:#64748b;font-size:0.72rem;">to Player #{offer.target_player_id} · Expires: {expires_str}</span>
        </div>
        <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:8px;margin-bottom:10px;">
            <div style="background:#0f172a;border-radius:4px;padding:8px 10px;">
                <div style="color:#64748b;font-size:0.68rem;text-transform:uppercase;">Original Offer</div>
                <div style="color:#94a3b8;font-size:0.82rem;">{offer.shares_offered:,} {ticker} shares for {offer.stake_pct*100:.1f}%</div>
            </div>
            <div style="background:#0f172a;border-radius:4px;padding:8px 10px;">
                <div style="color:#64748b;font-size:0.68rem;text-transform:uppercase;">Counter Requests</div>
                <div style="color:#a78bfa;font-weight:bold;font-size:0.82rem;">{offer.counter_shares:,} shares for {(offer.counter_stake_pct or 0)*100:.1f}%{'  +  ' + fmt_usd(counter_cash, disp) + ' cash' if counter_cash > 0 else ''}</div>
            </div>
        </div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;">
            <form action="/api/corporate-actions/acquisition/counter/accept/{offer.id}" method="post" style="display:inline;"
                  onsubmit="return confirm('Accept counter-offer? You will transfer {offer.counter_shares:,} shares and {offer.counter_stake_pct and offer.counter_stake_pct*100:.1f}% income stake begins.')">
                <button class="btn btn-success" type="submit">Accept Counter</button>
            </form>
            <form action="/api/corporate-actions/acquisition/counter/reject/{offer.id}" method="post" style="display:inline;"
                  onsubmit="return confirm('Decline this counter? The offer reverts to pending — Player #{offer.target_player_id} can still accept/reject your original terms.')">
                <button class="btn btn-warning" type="submit">Decline Counter</button>
            </form>
        </div>
    </div>
"""

        # ── Stakes You Hold ────────────────────────────────────────────────────
        from datetime import timedelta as _td, datetime as _dt2
        if stakes_as_acquirer:
            html += '<div style="color:#22c55e;font-size:0.78rem;font-weight:bold;margin:12px 0 8px;text-transform:uppercase;letter-spacing:0.05em;">Income Stakes You Hold</div>'
            for stake in stakes_as_acquirer:
                _stake_offer = db.query(AcquisitionOffer).filter(
                    AcquisitionOffer.id == stake.acquisition_offer_id).first() if stake.acquisition_offer_id else None
                ticker, cname, cprice = _ticker_for(_stake_offer.offeror_company_id if _stake_offer else 0)
                share_cur_val = cprice * stake.shares_paid
                last_sweep_str = _time_ago(stake.last_income_sweep)
                stake_date = stake.created_at.strftime('%Y-%m-%d') if stake.created_at else "—"
                # Lock-up / expiry metadata
                _lockup_days = stake.lock_up_days or 0
                _lockup_expiry = (stake.created_at + _td(days=_lockup_days)) if stake.created_at and _lockup_days > 0 else None
                _lockup_active = _lockup_expiry and _dt2.utcnow() < _lockup_expiry
                _lockup_label = f"Lock-up active until {_lockup_expiry.strftime('%Y-%m-%d')}" if _lockup_active else (f"Lock-up ended {_lockup_expiry.strftime('%Y-%m-%d')}" if _lockup_expiry else "No lock-up")
                _lockup_color = "#ef4444" if _lockup_active else "#22c55e"
                _expires_label = stake.expires_at.strftime('%Y-%m-%d') if stake.expires_at else "Perpetual"
                _term_label = f"{stake.term_days}-day term · expires {_expires_label}" if stake.term_days else "Perpetual deal"
                # Pending renegotiation for this stake?
                _stake_reneg = db.query(StakeRenegotiation).filter(
                    StakeRenegotiation.stake_id == stake.id,
                    StakeRenegotiation.status == "pending"
                ).first() if StakeRenegotiation else None
                _reneg_pending = _stake_reneg is not None
                html += f"""
    <div class="program-row" style="border-left-color:#22c55e;">
        <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px;margin-bottom:8px;">
            <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;">
                <span style="background:#22c55e;color:#020617;padding:2px 8px;border-radius:10px;
                             font-size:0.68rem;font-weight:bold;">ACTIVE STAKE</span>
                <span style="background:{_lockup_color};color:#020617;padding:2px 7px;border-radius:10px;
                             font-size:0.63rem;font-weight:bold;">{"LOCKED" if _lockup_active else "UNLOCKED"}</span>
            </div>
            <span style="color:#64748b;font-size:0.72rem;">in Player #{stake.target_player_id} · since {stake_date}</span>
        </div>
        <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:8px;margin-bottom:10px;">
            <div style="background:#0f172a;border-radius:4px;padding:8px 10px;">
                <div style="color:#64748b;font-size:0.68rem;text-transform:uppercase;">Income Share</div>
                <div style="color:#22c55e;font-weight:bold;font-size:0.95rem;">{stake.stake_pct*100:.1f}%</div>
                <div style="color:#64748b;font-size:0.72rem;">of their net daily income</div>
            </div>
            <div style="background:#0f172a;border-radius:4px;padding:8px 10px;">
                <div style="color:#64748b;font-size:0.68rem;text-transform:uppercase;">Shares Paid</div>
                <div style="color:#e5e7eb;font-weight:bold;font-size:0.9rem;">{stake.shares_paid:,} {ticker}</div>
                <div style="color:#64748b;font-size:0.72rem;">now worth ≈ {fmt_usd(share_cur_val, disp)}</div>
            </div>
            <div style="background:#0f172a;border-radius:4px;padding:8px 10px;">
                <div style="color:#64748b;font-size:0.68rem;text-transform:uppercase;">Last Sweep</div>
                <div style="color:#94a3b8;font-size:0.9rem;">{last_sweep_str}</div>
                <div style="color:#64748b;font-size:0.72rem;">income sweeps every 24h</div>
            </div>
            <div style="background:#0f172a;border-radius:4px;padding:8px 10px;">
                <div style="color:#64748b;font-size:0.68rem;text-transform:uppercase;">Term</div>
                <div style="color:#94a3b8;font-size:0.82rem;">{_term_label}</div>
                <div style="color:{_lockup_color};font-size:0.68rem;">{_lockup_label}</div>
            </div>
        </div>
        {"<div class='info-box' style='font-size:0.78rem;padding:6px 12px;margin-bottom:10px;border-color:#a78bfa;'>A renegotiation proposal is currently pending on this stake.</div>" if _reneg_pending else ""}
        {"<div class='info-box warning' style='font-size:0.78rem;padding:6px 12px;margin-bottom:10px;'>Lock-up period is active — exit not allowed until " + (_lockup_expiry.strftime('%Y-%m-%d') if _lockup_expiry else "") + ".</div>" if _lockup_active else ""}
        <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px;">
            <form action="/api/corporate-actions/diffuse/initiate/{stake.id}" method="post" style="display:inline;">
                <input type="hidden" name="diffuse_type" value="share_return">
                <button class="btn btn-warning" type="submit" {"disabled" if _lockup_active else ""}
                        onclick="return confirm('Request share return? Income stops now. Player #{stake.target_player_id} has {DIFFUSE_RETURN_DAYS} days to return {stake.shares_paid:,} shares or a lien is created.')">
                    Request Share Return
                </button>
            </form>
            <form action="/api/corporate-actions/diffuse/initiate/{stake.id}" method="post" style="display:inline;">
                <input type="hidden" name="diffuse_type" value="cash_buyout">
                <button class="btn btn-primary" type="submit" {"disabled" if _lockup_active else ""}
                        onclick="return confirm('Cash buyout: you pay ≈{fmt_usd(share_cur_val, disp)} now to exit cleanly. Target keeps the shares. Confirm?')">
                    Cash Buyout (~{fmt_usd(share_cur_val, disp)})
                </button>
            </form>
        </div>
        <details style="margin-top:6px;">
            <summary style="cursor:pointer;color:#a78bfa;font-size:0.78rem;font-weight:600;">Propose Renegotiation</summary>
            <div style="background:#0a1628;border:1px solid #1e293b;border-radius:4px;padding:12px;margin-top:8px;">
                <form action="/api/corporate-actions/stake/renegotiate/{stake.id}" method="post">
                    <div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:8px;">
                        <div class="form-group">
                            <label class="form-label">New Stake %</label>
                            <input type="number" name="new_stake_pct" min="0.1" max="50" step="0.1"
                                   value="{stake.stake_pct*100:.1f}" class="form-input" style="width:100px;" required>
                        </div>
                        <div class="form-group">
                            <label class="form-label">New Term (days, 0=perpetual)</label>
                            <input type="number" name="new_term_days" min="0" value="0"
                                   class="form-input" style="width:110px;">
                        </div>
                        <div class="form-group" style="flex:1;min-width:140px;">
                            <label class="form-label">Note (optional)</label>
                            <input type="text" name="note" maxlength="200" placeholder="Why are you proposing this?"
                                   class="form-input">
                        </div>
                        <button type="submit" class="btn btn-primary" style="align-self:flex-end;margin-bottom:4px;">
                            Send Proposal
                        </button>
                    </div>
                </form>
            </div>
        </details>
    </div>
"""

        # ── Stakes Held Against You ────────────────────────────────────────────
        if stakes_as_target:
            html += '<div style="color:#f59e0b;font-size:0.78rem;font-weight:bold;margin:12px 0 8px;text-transform:uppercase;letter-spacing:0.05em;">Obligations — Stakes in Your Business</div>'
            for stake in stakes_as_target:
                stake_date = stake.created_at.strftime('%Y-%m-%d') if stake.created_at else "—"
                last_sweep_str = _time_ago(stake.last_income_sweep)
                _stake_offer2 = db.query(AcquisitionOffer).filter(
                    AcquisitionOffer.id == stake.acquisition_offer_id).first() if stake.acquisition_offer_id else None
                ticker2, _, cprice2 = _ticker_for(_stake_offer2.offeror_company_id if _stake_offer2 else 0)
                buyout_val = cprice2 * stake.shares_paid
                _expires_label2 = stake.expires_at.strftime('%Y-%m-%d') if stake.expires_at else "Perpetual"
                _term_label2 = f"{stake.term_days}-day term · expires {_expires_label2}" if stake.term_days else "Perpetual"
                _stake_reneg2 = db.query(StakeRenegotiation).filter(
                    StakeRenegotiation.stake_id == stake.id,
                    StakeRenegotiation.status == "pending"
                ).first() if StakeRenegotiation else None
                _reneg_pending2 = _stake_reneg2 is not None
                html += f"""
    <div class="program-row" style="border-left-color:#f59e0b;">
        <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px;margin-bottom:8px;">
            <span style="background:#f59e0b;color:#020617;padding:2px 8px;border-radius:10px;
                         font-size:0.68rem;font-weight:bold;">INCOME OBLIGATION</span>
            <span style="color:#64748b;font-size:0.72rem;">to Player #{stake.acquirer_id} · since {stake_date}</span>
        </div>
        <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:8px;margin-bottom:8px;">
            <div style="background:#0f172a;border-radius:4px;padding:8px 10px;">
                <div style="color:#64748b;font-size:0.68rem;text-transform:uppercase;">Income Deducted</div>
                <div style="color:#f59e0b;font-weight:bold;font-size:0.95rem;">{stake.stake_pct*100:.1f}%</div>
                <div style="color:#64748b;font-size:0.72rem;">of your net daily income</div>
            </div>
            <div style="background:#0f172a;border-radius:4px;padding:8px 10px;">
                <div style="color:#64748b;font-size:0.68rem;text-transform:uppercase;">Shares You Hold</div>
                <div style="color:#e5e7eb;font-weight:bold;font-size:0.9rem;">{stake.shares_paid:,} {ticker2}</div>
                <div style="color:#64748b;font-size:0.72rem;">paid by Player #{stake.acquirer_id}</div>
            </div>
            <div style="background:#0f172a;border-radius:4px;padding:8px 10px;">
                <div style="color:#64748b;font-size:0.68rem;text-transform:uppercase;">Last Deduction</div>
                <div style="color:#94a3b8;font-size:0.9rem;">{last_sweep_str}</div>
                <div style="color:#64748b;font-size:0.72rem;">automatic 24h cycle</div>
            </div>
            <div style="background:#0f172a;border-radius:4px;padding:8px 10px;">
                <div style="color:#64748b;font-size:0.68rem;text-transform:uppercase;">Term</div>
                <div style="color:#94a3b8;font-size:0.82rem;">{_term_label2}</div>
            </div>
        </div>
        {"<div class='info-box' style='font-size:0.78rem;padding:6px 12px;margin-bottom:8px;border-color:#a78bfa;'>A renegotiation proposal is currently pending on this stake.</div>" if _reneg_pending2 else ""}
        <div style="color:#64748b;font-size:0.78rem;margin-bottom:10px;">
            Player #{stake.acquirer_id} holds this stake. To end it early, you can <strong>buy them out</strong> at
            current market value of the shares, or propose a <strong>renegotiation</strong>.
            If they initiate a diffuse, you'll have {DIFFUSE_RETURN_DAYS} days to return the shares.
        </div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px;">
            <form action="/api/corporate-actions/stake/buyout/{stake.id}" method="post" style="display:inline;"
                  onsubmit="return confirm('Buy out Player #{stake.acquirer_id}\\'s stake for ≈{fmt_usd(buyout_val, disp)}? This ends the income obligation immediately.')">
                <button class="btn btn-danger" type="submit">Buy Out Stake ({fmt_usd(buyout_val, disp)})</button>
            </form>
        </div>
        <details style="margin-top:4px;">
            <summary style="cursor:pointer;color:#a78bfa;font-size:0.78rem;font-weight:600;">Propose Renegotiation</summary>
            <div style="background:#0a1628;border:1px solid #1e293b;border-radius:4px;padding:12px;margin-top:8px;">
                <form action="/api/corporate-actions/stake/renegotiate/{stake.id}" method="post">
                    <div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:8px;">
                        <div class="form-group">
                            <label class="form-label">New Stake %</label>
                            <input type="number" name="new_stake_pct" min="0.1" max="50" step="0.1"
                                   value="{stake.stake_pct*100:.1f}" class="form-input" style="width:100px;" required>
                        </div>
                        <div class="form-group">
                            <label class="form-label">New Term (days, 0=perpetual)</label>
                            <input type="number" name="new_term_days" min="0" value="0"
                                   class="form-input" style="width:110px;">
                        </div>
                        <div class="form-group" style="flex:1;min-width:140px;">
                            <label class="form-label">Note (optional)</label>
                            <input type="text" name="note" maxlength="200" placeholder="Why are you proposing this?"
                                   class="form-input">
                        </div>
                        <button type="submit" class="btn btn-primary" style="align-self:flex-end;margin-bottom:4px;">
                            Send Proposal
                        </button>
                    </div>
                </form>
            </div>
        </details>
    </div>
"""

        # ── Pending Diffuse Notices ────────────────────────────────────────────
        if diffuse_notices:
            html += '<div style="color:#ef4444;font-size:0.78rem;font-weight:bold;margin:12px 0 8px;text-transform:uppercase;letter-spacing:0.05em;">Diffuse Notices — Urgent Action Required</div>'
            for notice in diffuse_notices:
                days_left = _days_until(notice.deadline_at)
                html += f"""
    <div class="program-row" style="border-left-color:#ef4444;">
        <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px;margin-bottom:8px;">
            <span style="background:#ef4444;color:#fff;padding:2px 8px;border-radius:10px;
                         font-size:0.68rem;font-weight:bold;">RETURN REQUIRED</span>
            <span style="color:#ef4444;font-size:0.72rem;font-weight:bold;">Deadline: {notice.deadline_at.strftime('%Y-%m-%d')} ({days_left})</span>
        </div>
        <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:8px;margin-bottom:10px;">
            <div style="background:#0f172a;border-radius:4px;padding:8px 10px;">
                <div style="color:#64748b;font-size:0.68rem;text-transform:uppercase;">Shares to Return</div>
                <div style="color:#ef4444;font-weight:bold;font-size:0.95rem;">{notice.shares_to_return:,}</div>
                <div style="color:#64748b;font-size:0.72rem;">to Player #{notice.acquirer_id}</div>
            </div>
            <div style="background:#0f172a;border-radius:4px;padding:8px 10px;">
                <div style="color:#64748b;font-size:0.68rem;text-transform:uppercase;">Value at Notice</div>
                <div style="color:#e5e7eb;font-weight:bold;font-size:0.9rem;">{fmt_usd(notice.share_value_at_notice, disp)}</div>
                <div style="color:#64748b;font-size:0.72rem;">lien amount if deadline missed</div>
            </div>
        </div>
        <div class="info-box warning" style="font-size:0.78rem;padding:8px 12px;margin-bottom:10px;">
            If you do not return the shares by the deadline, a financial lien of
            <strong>{fmt_usd(notice.share_value_at_notice, disp)}</strong> will be placed on your account
            (equivalent to a debt). Return them now to avoid the lien.
        </div>
        <form action="/api/corporate-actions/diffuse/return/{notice.id}" method="post" style="display:inline;"
              onsubmit="return confirm('Return {notice.shares_to_return:,} shares to Player #{notice.acquirer_id}? This will deduct them from your portfolio.')">
            <button class="btn btn-danger" type="submit">Return Shares Now</button>
        </form>
    </div>
"""

        # ── Pending Renegotiation Proposals ───────────────────────────────────
        pending_renegs = db.query(StakeRenegotiation).filter(
            StakeRenegotiation.status == "pending"
        ).join(AcquisitionStake, AcquisitionStake.id == StakeRenegotiation.stake_id).filter(
            ((AcquisitionStake.acquirer_id == player.id) |
             (AcquisitionStake.target_player_id == player.id))
        ).all() if StakeRenegotiation else []
        if pending_renegs:
            html += '<div style="color:#a78bfa;font-size:0.78rem;font-weight:bold;margin:12px 0 8px;text-transform:uppercase;letter-spacing:0.05em;">Renegotiation Proposals</div>'
            for r in pending_renegs:
                is_proposer = r.proposed_by_player_id == player.id
                other_label = f"Player #{r.proposed_by_player_id}" if not is_proposer else f"Waiting on other party"
                term_str = f"{r.new_term_days}-day term" if r.new_term_days else "Perpetual"
                html += f"""
    <div class="program-row" style="border-left-color:#a78bfa;">
        <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px;margin-bottom:8px;">
            <span style="background:#a78bfa;color:#020617;padding:2px 8px;border-radius:10px;
                         font-size:0.68rem;font-weight:bold;">{"PROPOSAL SENT" if is_proposer else "PROPOSAL RECEIVED"}</span>
            <span style="color:#64748b;font-size:0.72rem;">Stake #{r.stake_id} · {other_label}</span>
        </div>
        <div style="color:#e5e7eb;font-size:0.82rem;margin-bottom:8px;">
            Proposed terms: <strong>{r.new_stake_pct*100:.1f}% stake</strong> · {term_str}
            {"· <em>" + r.note + "</em>" if r.note else ""}
        </div>
        {"" if is_proposer else f'''
        <div style="display:flex;gap:8px;flex-wrap:wrap;">
            <form action="/api/corporate-actions/stake/renegotiate/respond/{r.id}" method="post" style="display:inline;">
                <input type="hidden" name="accept" value="true">
                <button class="btn btn-success" type="submit">Accept</button>
            </form>
            <form action="/api/corporate-actions/stake/renegotiate/respond/{r.id}" method="post" style="display:inline;">
                <input type="hidden" name="accept" value="false">
                <button class="btn btn-warning" type="submit">Decline</button>
            </form>
        </div>'''}
        {"<div style='color:#64748b;font-size:0.72rem;'>Waiting for the other party to respond.</div>" if is_proposer else ""}
    </div>
"""

        # ── Recent Acquisition History ─────────────────────────────────────────
        if recent_offers_hist:
            html += '<div style="color:#475569;font-size:0.78rem;font-weight:bold;margin:16px 0 8px;text-transform:uppercase;letter-spacing:0.05em;">Recent Acquisition History</div>'
            status_colors = {"accepted": "#22c55e", "rejected": "#ef4444", "expired": "#64748b", "diffused": "#f59e0b"}
            for offer in recent_offers_hist:
                ticker, _, _ = _ticker_for(offer.offeror_company_id)
                sc = status_colors.get(offer.status, "#64748b")
                role = "You offered" if offer.offeror_id == player.id else "You received"
                other_id = offer.target_player_id if offer.offeror_id == player.id else offer.offeror_id
                date_str = offer.responded_at.strftime('%Y-%m-%d') if offer.responded_at else "—"
                html += f"""
    <div style="display:flex;align-items:center;gap:10px;padding:6px 0;border-bottom:1px solid #0f172a;font-size:0.8rem;">
        <span style="background:{sc};color:#000;padding:1px 7px;border-radius:10px;
                     font-size:0.65rem;font-weight:bold;flex-shrink:0;">{offer.status.upper()}</span>
        <span style="color:#94a3b8;">{role} {offer.shares_offered:,} {ticker} shares for {offer.stake_pct*100:.1f}% stake
              {'(+' + fmt_usd(offer.cash_component, disp) + ' cash)' if (offer.cash_component or 0) > 0 else ''}
              · Player #{other_id}</span>
        <span style="color:#475569;margin-left:auto;flex-shrink:0;">{date_str}</span>
    </div>
"""

        if not (pending_offers_recv or countered_outgoing or stakes_as_acquirer or stakes_as_target or diffuse_notices or pending_renegs):
            html += '<div class="empty-state"><p>No active acquisitions or pending offers.</p><p style="color:#475569;">Use the "Send Acquisition Offer" form above to begin a deal with another player.</p></div>'

        html += "</div>"

        # ── Tax Vouchers ───────────────────────────────────────────────────────
        redeem_max = voucher_balance / disp["usd_per_unit"] if disp["usd_per_unit"] else 0
        can_redeem = voucher_balance > 0
        html += f"""
<div class="section-card accent-gold">
    <div class="section-title" style="margin-bottom:4px;">Tax Vouchers</div>
    <div class="section-desc">
        Tax vouchers are government-issued credit instruments you earn automatically whenever
        you pay a special dividend. For every <strong>{disp["symbol"]}1</strong> distributed to shareholders,
        you receive <strong style="color:#d4af37;">{disp["symbol"]}{TAX_VOUCHER_RATE:.4f}</strong> in vouchers
        ({TAX_VOUCHER_RATE*100:.2f}% rebate). Vouchers can also be awarded by tutorials and government events.
        Redeem them below for instant cash deposited to your wallet — they never expire.
    </div>
    <div class="stat-grid" style="max-width:380px;margin-bottom:16px;">
        <div class="stat-box">
            <div class="stat-label">Voucher Balance</div>
            <div class="stat-value gold">{fmt_usd(voucher_balance, disp)}</div>
        </div>
        <div class="stat-box">
            <div class="stat-label">Rebate Rate</div>
            <div class="stat-value amber">{TAX_VOUCHER_RATE*100:.2f}%</div>
        </div>
    </div>
    <form action="/api/corporate-actions/vouchers/redeem" method="post">
        <div class="form-inline">
            <div class="form-group">
                <label class="form-label">Amount to Redeem ({disp["symbol"]})</label>
                <input type="number" name="amount" min="0.01" step="0.01"
                       max="{redeem_max:.4f}"
                       placeholder="e.g. {fmt_usd(min(voucher_balance, 10000), disp)}"
                       class="form-input" style="width:170px;"
                       {'required' if can_redeem else 'disabled'}>
            </div>
            <button type="submit" class="btn btn-gold"
                    {'disabled' if not can_redeem else ''}>
                {'Redeem for Cash' if can_redeem else 'No Vouchers to Redeem'}
            </button>
        </div>
    </form>
</div>

</div><!-- /page-wrap -->
{_nav_loader()}
</body>
</html>"""

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

    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)

    db = get_db()
    try:
        company = db.query(CompanyShares).filter(
            CompanyShares.id == company_id,
            CompanyShares.founder_id == player.id
        ).first()

        if not company:
            return HTMLResponse(content="<p>Company not found.</p>", status_code=404)

        max_shares = int(company.shares_outstanding * 0.30)
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>New Buyback — {company.ticker_symbol}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>{_BASE_CSS}
.fgroup {{ margin-bottom:18px; }}
.fgroup label {{ display:block;color:#94a3b8;font-size:0.78rem;margin-bottom:5px;font-weight:bold; }}
.fgroup input,.fgroup select {{ width:100%;padding:9px 12px;background:#070f1e;color:#e5e7eb;
    border:1px solid #334155;border-radius:4px;font-family:inherit;font-size:0.85rem; }}
.fgroup input:focus,.fgroup select:focus {{ outline:none;border-color:#38bdf8; }}
.fgroup .hint {{ color:#475569;font-size:0.72rem;margin-top:4px;line-height:1.5; }}
.tconfig {{ display:none;background:#070f1e;border:1px solid #1e293b;border-radius:4px;
    padding:14px 16px;margin-top:10px; }}
</style>
</head>
<body>
<div class="topbar">
    <span class="topbar-brand">WADSWORTH</span>
    <span class="topbar-sep">/</span>
    <a href="/">Dashboard</a>
    <span class="topbar-sep">/</span>
    <a href="/corporate-actions/dashboard">Corporate Actions</a>
    <span class="topbar-sep">/</span>
    <span class="topbar-crumb">New Buyback</span>
</div>
<div class="page-wrap" style="max-width:700px;">
<div class="page-header">
    <h1>New Buyback Program</h1>
    <p class="subtitle">
        <strong style="color:#38bdf8;">{company.ticker_symbol}</strong> — {company.company_name} &nbsp;&bull;&nbsp;
        Current price: <strong style="color:#22c55e;">{fmt_usd(company.current_price, disp)}</strong> &nbsp;&bull;&nbsp;
        Outstanding: <strong>{company.shares_outstanding:,}</strong>
    </p>
</div>
<div class="info-box tip" style="margin-bottom:20px;">
    <strong>What is a Buyback Program?</strong><br>
    The game engine automatically purchases your company's own shares from the open market
    using company cash whenever the trigger condition is met. Bought shares become treasury
    shares that reduce float, which can support the share price. Max program size is
    30% of outstanding shares ({max_shares:,} shares for {company.ticker_symbol}).
</div>
<div class="section-card accent-blue">
<form id="buyback-form">
    <div class="fgroup">
        <label>Trigger Type — when should the engine buy?</label>
        <select id="trigger-type" required>
            <option value="">— Select a trigger —</option>
            <option value="price_drop">Price Support — buy when price drops below a target</option>
            <option value="earnings_surplus">Earnings Surplus — buy when company cash exceeds a threshold</option>
            <option value="schedule">Scheduled — buy on a regular interval</option>
        </select>
    </div>
    <div id="config-price-drop" class="tconfig">
        <div class="fgroup">
            <label>Target Price ({disp["symbol"]})</label>
            <input type="number" id="target-price" step="0.01" value="{company.current_price:.2f}">
            <div class="hint">The price level you want to defend. Buybacks trigger when price falls below this.</div>
        </div>
        <div class="fgroup">
            <label>Drop Threshold (%)</label>
            <input type="number" id="drop-threshold" value="15" min="5" max="50">
            <div class="hint">Buy when price drops this % below target. At 15%, a {fmt_usd(10, disp)} target triggers at {fmt_usd(8.5, disp)}.</div>
        </div>
    </div>
    <div id="config-earnings-surplus" class="tconfig">
        <div class="fgroup">
            <label>Surplus Threshold ({disp["symbol"]})</label>
            <input type="number" id="surplus-threshold" value="50000" step="1000">
            <div class="hint">Trigger when your company cash balance exceeds this amount — reinvests excess earnings.</div>
        </div>
    </div>
    <div id="config-schedule" class="tconfig">
        <div class="fgroup">
            <label>Purchase Frequency</label>
            <select id="schedule-frequency">
                <option value="3600">Every Hour</option>
                <option value="86400">Every Day</option>
                <option value="604800">Every Week</option>
            </select>
            <div class="hint">The engine attempts a buyback purchase on each interval, if funds allow.</div>
        </div>
    </div>
    <hr class="divider">
    <div class="fgroup">
        <label>Maximum Shares to Buy (program total)</label>
        <input type="number" id="max-shares" required min="1" max="{max_shares}">
        <div class="hint">The program stops once this many shares have been repurchased. Max: {max_shares:,} (30% of outstanding).</div>
    </div>
    <div class="fgroup">
        <label>Maximum Price per Share ({disp["symbol"]})</label>
        <input type="number" id="max-price" step="0.01" required value="{company.current_price * 1.2:.2f}">
        <div class="hint">Engine will not buy above this price. Default is 20% above current to allow for normal fluctuation.</div>
    </div>
    <div style="margin-top:24px;display:flex;gap:10px;flex-wrap:wrap;">
        <button type="submit" class="btn btn-primary">Create Buyback Program</button>
        <a href="/corporate-actions/dashboard" class="btn btn-ghost">Cancel</a>
    </div>
</form>
</div>
</div>
{_nav_loader()}
<script>
(function() {{
    var sel = document.getElementById('trigger-type');
    var cfgs = {{
        price_drop: document.getElementById('config-price-drop'),
        earnings_surplus: document.getElementById('config-earnings-surplus'),
        schedule: document.getElementById('config-schedule')
    }};
    sel.addEventListener('change', function() {{
        Object.values(cfgs).forEach(function(el) {{ el.style.display = 'none'; }});
        if (cfgs[sel.value]) cfgs[sel.value].style.display = 'block';
    }});
    document.getElementById('buyback-form').addEventListener('submit', async function(e) {{
        e.preventDefault();
        var trigger = sel.value;
        if (!trigger) {{ alert('Please select a trigger type.'); return; }}
        var tp = {{}};
        if (trigger === 'price_drop') {{
            tp = {{ target_price: parseFloat(document.getElementById('target-price').value),
                    drop_threshold_pct: parseFloat(document.getElementById('drop-threshold').value) / 100 }};
        }} else if (trigger === 'earnings_surplus') {{
            tp = {{ surplus_threshold: parseFloat(document.getElementById('surplus-threshold').value) }};
        }} else if (trigger === 'schedule') {{
            tp = {{ interval_ticks: parseInt(document.getElementById('schedule-frequency').value) }};
        }}
        var res = await fetch('/api/corporate-actions/buyback/create', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{
                company_shares_id: {company.id},
                trigger_type: trigger,
                trigger_params: tp,
                max_shares_to_buy: parseInt(document.getElementById('max-shares').value),
                max_price_per_share: parseFloat(document.getElementById('max-price').value)
            }})
        }});
        if (res.ok) {{ window.location.href = '/corporate-actions/dashboard'; }}
        else {{ var err = await res.json(); alert('Error: ' + err.detail); }}
    }});
}})();
</script>
</body></html>"""
        
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

    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)

    db = get_db()
    try:
        company = db.query(CompanyShares).filter(
            CompanyShares.id == company_id,
            CompanyShares.founder_id == player.id
        ).first()

        if not company:
            return HTMLResponse(content="<p>Company not found.</p>", status_code=404)

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>New Split Rule — {company.ticker_symbol}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>{_BASE_CSS}
.fgroup {{ margin-bottom:18px; }}
.fgroup label {{ display:block;color:#94a3b8;font-size:0.78rem;margin-bottom:5px;font-weight:bold; }}
.fgroup input,.fgroup select {{ width:100%;padding:9px 12px;background:#070f1e;color:#e5e7eb;
    border:1px solid #334155;border-radius:4px;font-family:inherit;font-size:0.85rem; }}
.fgroup input:focus,.fgroup select:focus {{ outline:none;border-color:#f59e0b; }}
.fgroup .hint {{ color:#475569;font-size:0.72rem;margin-top:4px;line-height:1.5; }}
</style>
</head>
<body>
<div class="topbar">
    <span class="topbar-brand">WADSWORTH</span>
    <span class="topbar-sep">/</span>
    <a href="/">Dashboard</a>
    <span class="topbar-sep">/</span>
    <a href="/corporate-actions/dashboard">Corporate Actions</a>
    <span class="topbar-sep">/</span>
    <span class="topbar-crumb">New Split Rule</span>
</div>
<div class="page-wrap" style="max-width:700px;">
<div class="page-header">
    <h1>New Stock Split Rule</h1>
    <p class="subtitle">
        <strong style="color:#38bdf8;">{company.ticker_symbol}</strong> — {company.company_name} &nbsp;&bull;&nbsp;
        Current price: <strong style="color:#22c55e;">{fmt_usd(company.current_price, disp)}</strong> &nbsp;&bull;&nbsp;
        Outstanding: <strong>{company.shares_outstanding:,}</strong>
    </p>
</div>
<div class="info-box tip" style="margin-bottom:20px;">
    <strong>What is a Forward Stock Split?</strong><br>
    When your share price hits the threshold you set, the game multiplies every shareholder's holdings
    by the split ratio and divides the price by the same ratio. A 2-for-1 split doubles share count
    and halves price — total value is unchanged. Splits make your stock more accessible to smaller
    investors and are widely seen as a sign of sustained growth.
</div>
<div class="section-card accent-amber">
<form id="split-form">
    <div class="fgroup">
        <label>Price Threshold — trigger split when price reaches ({disp["symbol"]})</label>
        <input type="number" id="price-threshold" step="1" required
               value="{max(int(company.current_price * 2), 100)}">
        <div class="hint">
            The share price at which the split triggers automatically.
            Current price is {fmt_usd(company.current_price, disp)} — set this well above current for a future trigger.
        </div>
    </div>
    <div class="fgroup">
        <label>Split Ratio</label>
        <select id="split-ratio" required>
            <option value="2">2-for-1 — doubles shares, halves price (most common)</option>
            <option value="3">3-for-1 — triples shares, price becomes 1/3</option>
            <option value="5">5-for-1 — five times the shares at 1/5 the price</option>
            <option value="10">10-for-1 — for very high-priced stocks</option>
        </select>
        <div class="hint">Higher ratios are used when the share price has grown very large and you want to bring it back to a smaller number.</div>
    </div>
    <div class="info-box" style="margin-bottom:16px;">
        <strong>Example:</strong> At a 2-for-1 split with a {fmt_usd(100, disp)} threshold —
        every shareholder's 100 shares becomes 200 shares,
        and price drops from {fmt_usd(100, disp)} to {fmt_usd(50, disp)}.
        Total portfolio value is identical. The split can fire multiple times as the price keeps rising.
    </div>
    <div style="margin-top:24px;display:flex;gap:10px;flex-wrap:wrap;">
        <button type="submit" class="btn btn-warning">Create Split Rule</button>
        <a href="/corporate-actions/dashboard" class="btn btn-ghost">Cancel</a>
    </div>
</form>
</div>
</div>
{_nav_loader()}
<script>
document.getElementById('split-form').addEventListener('submit', async function(e) {{
    e.preventDefault();
    var res = await fetch('/api/corporate-actions/split/create', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{
            company_shares_id: {company.id},
            trigger_type: 'price_threshold',
            trigger_params: {{ price_threshold: parseFloat(document.getElementById('price-threshold').value) }},
            split_ratio: parseInt(document.getElementById('split-ratio').value)
        }})
    }});
    if (res.ok) {{ window.location.href = '/corporate-actions/dashboard'; }}
    else {{ var err = await res.json(); alert('Error: ' + err.detail); }}
}});
</script>
</body></html>"""
        
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

    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)

    db = get_db()
    try:
        company = db.query(CompanyShares).filter(
            CompanyShares.id == company_id,
            CompanyShares.founder_id == player.id
        ).first()

        if not company:
            return HTMLResponse(content="<p>Company not found.</p>", status_code=404)

        max_dilution_shares = int(company.shares_outstanding * 0.20)
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>New Secondary Offering — {company.ticker_symbol}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>{_BASE_CSS}
.fgroup {{ margin-bottom:18px; }}
.fgroup label {{ display:block;color:#94a3b8;font-size:0.78rem;margin-bottom:5px;font-weight:bold; }}
.fgroup input,.fgroup select {{ width:100%;padding:9px 12px;background:#070f1e;color:#e5e7eb;
    border:1px solid #334155;border-radius:4px;font-family:inherit;font-size:0.85rem; }}
.fgroup input:focus,.fgroup select:focus {{ outline:none;border-color:#a78bfa; }}
.fgroup .hint {{ color:#475569;font-size:0.72rem;margin-top:4px;line-height:1.5; }}
.tconfig {{ display:none;background:#070f1e;border:1px solid #1e293b;border-radius:4px;
    padding:14px 16px;margin-top:10px; }}
</style>
</head>
<body>
<div class="topbar">
    <span class="topbar-brand">WADSWORTH</span>
    <span class="topbar-sep">/</span>
    <a href="/">Dashboard</a>
    <span class="topbar-sep">/</span>
    <a href="/corporate-actions/dashboard">Corporate Actions</a>
    <span class="topbar-sep">/</span>
    <span class="topbar-crumb">New Secondary Offering</span>
</div>
<div class="page-wrap" style="max-width:700px;">
<div class="page-header">
    <h1>New Secondary Offering</h1>
    <p class="subtitle">
        <strong style="color:#38bdf8;">{company.ticker_symbol}</strong> — {company.company_name} &nbsp;&bull;&nbsp;
        Price: <strong style="color:#22c55e;">{fmt_usd(company.current_price, disp)}</strong> &nbsp;&bull;&nbsp;
        Outstanding: <strong>{company.shares_outstanding:,}</strong>
    </p>
</div>
<div class="info-box warning" style="margin-bottom:16px;">
    <strong>Dilution Warning</strong> — A secondary offering creates new shares and sells them into the market.
    Every existing shareholder's ownership percentage decreases. Only use this when you genuinely
    need capital and the growth it funds will outweigh the dilution impact.
</div>
<div class="info-box tip" style="margin-bottom:20px;">
    <strong>How it works:</strong> When the trigger condition is met, the game issues new shares at or above
    your minimum price, depositing proceeds into your company treasury. A 3% issuance fee applies.
    Maximum offering size: 20% of outstanding shares ({max_dilution_shares:,} shares).
</div>
<div class="section-card accent-purple">
<form id="offering-form">
    <div class="fgroup">
        <label>Trigger Type — when should new shares be issued?</label>
        <select id="trigger-type" required>
            <option value="">— Select a trigger —</option>
            <option value="cash_need">Emergency Capital — issue shares when cash runs low</option>
            <option value="expansion">Expansion Funding — issue shares when business count grows</option>
        </select>
    </div>
    <div id="config-cash-need" class="tconfig">
        <div class="fgroup">
            <label>Minimum Cash Threshold ({disp["symbol"]})</label>
            <input type="number" id="cash-threshold" value="5000" step="1000">
            <div class="hint">Issue shares when your company cash balance falls below this amount.</div>
        </div>
    </div>
    <div id="config-expansion" class="tconfig">
        <div class="fgroup">
            <label>Business Count Trigger</label>
            <input type="number" id="business-count" value="5" min="1">
            <div class="hint">Issue shares when you operate at least this many active businesses — fund expansion capital.</div>
        </div>
    </div>
    <hr class="divider">
    <div class="fgroup">
        <label>Number of Shares to Issue</label>
        <input type="number" id="shares-to-issue" required min="1" max="{max_dilution_shares}">
        <div class="hint">Max 20% dilution cap = {max_dilution_shares:,} shares. Gross raise shown below updates as you type.</div>
    </div>
    <div class="fgroup">
        <label>Minimum Issue Price per Share ({disp["symbol"]})</label>
        <input type="number" id="min-price" step="0.01" required value="{company.current_price * 0.85:.2f}">
        <div class="hint">Won't issue below this floor. Default is 85% of current price — protects against adverse conditions.</div>
    </div>
    <div id="est-raise" style="display:none;background:#0a1628;border:1px solid #1e293b;border-radius:4px;
         padding:12px 14px;margin-bottom:14px;">
        <span style="color:#64748b;font-size:0.78rem;">Estimated raise (after 3% fee):</span>
        <strong id="raise-val" style="color:#22c55e;margin-left:8px;"></strong>
    </div>
    <div style="margin-top:24px;display:flex;gap:10px;flex-wrap:wrap;">
        <button type="submit" class="btn btn-primary">Create Secondary Offering</button>
        <a href="/corporate-actions/dashboard" class="btn btn-ghost">Cancel</a>
    </div>
</form>
</div>
</div>
{_nav_loader()}
<script>
(function() {{
    var sel = document.getElementById('trigger-type');
    var cfgs = {{
        cash_need: document.getElementById('config-cash-need'),
        expansion: document.getElementById('config-expansion')
    }};
    sel.addEventListener('change', function() {{
        Object.values(cfgs).forEach(function(el) {{ el.style.display = 'none'; }});
        if (cfgs[sel.value]) cfgs[sel.value].style.display = 'block';
    }});
    var sharesInput = document.getElementById('shares-to-issue');
    sharesInput.addEventListener('input', function() {{
        var shares = parseInt(sharesInput.value) || 0;
        if (shares > 0) {{
            var net = shares * {company.current_price} * 0.97;
            document.getElementById('raise-val').textContent = '{disp["symbol"]}' +
                net.toFixed(2).replace(/\\B(?=(\\d{{3}})+(?!\\d))/g, ',');
            document.getElementById('est-raise').style.display = 'block';
        }} else {{
            document.getElementById('est-raise').style.display = 'none';
        }}
    }});
    document.getElementById('offering-form').addEventListener('submit', async function(e) {{
        e.preventDefault();
        var trigger = sel.value;
        if (!trigger) {{ alert('Please select a trigger type.'); return; }}
        var tp = {{}};
        if (trigger === 'cash_need') tp = {{ cash_threshold: parseFloat(document.getElementById('cash-threshold').value) }};
        else if (trigger === 'expansion') tp = {{ business_count: parseInt(document.getElementById('business-count').value) }};
        var res = await fetch('/api/corporate-actions/offering/create', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{
                company_shares_id: {company.id},
                trigger_type: trigger,
                trigger_params: tp,
                shares_to_issue: parseInt(document.getElementById('shares-to-issue').value),
                min_price_per_share: parseFloat(document.getElementById('min-price').value)
            }})
        }});
        if (res.ok) {{ window.location.href = '/corporate-actions/dashboard'; }}
        else {{ var err = await res.json(); alert('Error: ' + err.detail); }}
    }});
}})();
</script>
</body></html>"""
        
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
