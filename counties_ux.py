"""
counties_ux.py

UX module for the counties system.
Provides web interface and API endpoints for:
- County Dashboard (overview, join/form, mining, exchange)
- Join/Form County petition flow
- County Mining Node (deposit city currency, view mining stats)
- Wadsworth Crypto Exchange (buy/sell/swap crypto)
"""

from typing import Optional, List
from fastapi import APIRouter, Cookie, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse

router = APIRouter()

# ==========================
# HELPER: Get Player
# ==========================
def get_current_player(session_token: Optional[str]):
    """Get player from session token."""
    from auth import get_player_from_session, get_db
    db = get_db()
    player = get_player_from_session(db, session_token)
    db.close()
    return player


# ==========================
# STYLES
# ==========================
COUNTY_STYLES = """
<style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        background: #0b1220;
        color: #e5e7eb;
        min-height: 100vh;
        padding: 20px;
    }
    .container { max-width: 1200px; margin: 0 auto; }
    .header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 24px;
        padding-bottom: 16px;
        border-bottom: 1px solid #1e293b;
    }
    .header h1 { font-size: 24px; }
    .nav-link {
        color: #38bdf8;
        text-decoration: none;
        margin-left: 16px;
    }
    .nav-link:hover { text-decoration: underline; }

    .card {
        background: #020617;
        border: 1px solid #1e293b;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 16px;
    }
    .card h2 {
        font-size: 18px;
        margin-bottom: 12px;
        color: #38bdf8;
    }
    .card h3 {
        font-size: 16px;
        margin-bottom: 8px;
        color: #94a3b8;
    }

    .grid { display: grid; gap: 16px; }
    .grid-2 { grid-template-columns: repeat(2, 1fr); }
    .grid-3 { grid-template-columns: repeat(3, 1fr); }
    @media (max-width: 768px) {
        .grid-2, .grid-3 { grid-template-columns: 1fr; }
    }

    .stat {
        display: flex;
        justify-content: space-between;
        padding: 8px 0;
        border-bottom: 1px solid #1e293b;
    }
    .stat:last-child { border-bottom: none; }
    .stat-label { color: #94a3b8; }
    .stat-value { font-weight: 600; }
    .stat-value.positive { color: #4ade80; }
    .stat-value.negative { color: #f87171; }
    .stat-value.crypto { color: #a78bfa; }

    .btn {
        display: inline-block;
        padding: 10px 20px;
        border-radius: 8px;
        font-size: 14px;
        font-weight: 600;
        cursor: pointer;
        text-decoration: none;
        border: none;
        transition: all 0.2s;
    }
    .btn-primary { background: #38bdf8; color: #020617; }
    .btn-primary:hover { background: #0ea5e9; }
    .btn-secondary { background: #1e293b; color: #e5e7eb; }
    .btn-secondary:hover { background: #334155; }
    .btn-crypto { background: #7c3aed; color: #fff; }
    .btn-crypto:hover { background: #6d28d9; }
    .btn-danger { background: #dc2626; color: #fff; }
    .btn-danger:hover { background: #b91c1c; }
    .btn-sm { padding: 6px 12px; font-size: 12px; }

    .form-group { margin-bottom: 16px; }
    .form-group label {
        display: block;
        margin-bottom: 6px;
        color: #94a3b8;
        font-size: 14px;
    }
    .form-group input, .form-group select {
        width: 100%;
        padding: 10px 12px;
        background: #0b1220;
        border: 1px solid #1e293b;
        border-radius: 6px;
        color: #e5e7eb;
        font-size: 14px;
    }
    .form-group input:focus, .form-group select:focus {
        outline: none;
        border-color: #7c3aed;
    }

    .table { width: 100%; border-collapse: collapse; }
    .table th, .table td {
        padding: 12px;
        text-align: left;
        border-bottom: 1px solid #1e293b;
    }
    .table th {
        color: #94a3b8;
        font-weight: 500;
        font-size: 13px;
    }
    .table tr:hover { background: #0b1220; }

    .badge {
        display: inline-block;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: 600;
    }
    .badge-success { background: #166534; color: #4ade80; }
    .badge-warning { background: #854d0e; color: #fbbf24; }
    .badge-info { background: #1e40af; color: #60a5fa; }
    .badge-crypto { background: #4c1d95; color: #c4b5fd; }

    .alert {
        padding: 12px 16px;
        border-radius: 8px;
        margin-bottom: 16px;
    }
    .alert-success { background: #166534; border: 1px solid #22c55e; }
    .alert-error { background: #991b1b; border: 1px solid #ef4444; }
    .alert-info { background: #1e40af; border: 1px solid #3b82f6; }

    .poll-card {
        background: #0b1220;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
    }
    .poll-header {
        display: flex;
        justify-content: space-between;
        margin-bottom: 12px;
    }
    .poll-votes {
        display: flex;
        gap: 16px;
        margin-top: 12px;
    }
    .vote-btn {
        flex: 1;
        padding: 10px;
        border-radius: 6px;
        cursor: pointer;
        text-align: center;
        font-weight: 600;
    }
    .vote-yes { background: #166534; color: #4ade80; border: 1px solid #22c55e; }
    .vote-yes:hover { background: #15803d; }
    .vote-no { background: #991b1b; color: #fca5a5; border: 1px solid #ef4444; }
    .vote-no:hover { background: #b91c1c; }

    .mining-node {
        background: linear-gradient(135deg, #1a0533 0%, #020617 100%);
        border: 1px solid #7c3aed;
        border-radius: 12px;
        padding: 24px;
    }
    .exchange-panel {
        background: linear-gradient(135deg, #0c1a33 0%, #020617 100%);
        border: 1px solid #38bdf8;
        border-radius: 12px;
        padding: 24px;
    }

    .wallet-card {
        background: #0b1220;
        border: 1px solid #4c1d95;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
    }
    .wallet-balance {
        font-size: 24px;
        font-weight: 700;
        color: #a78bfa;
    }
    .wallet-value {
        font-size: 14px;
        color: #94a3b8;
    }

    /* Governance Voting Styles */
    .governance-panel {
        background: linear-gradient(135deg, #1a0a2e 0%, #020617 100%);
        border: 1px solid #f59e0b;
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 16px;
    }
    .phase-indicator {
        display: inline-block;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .phase-proposal { background: #854d0e; color: #fbbf24; }
    .phase-voting { background: #166534; color: #4ade80; }
    .phase-completed { background: #1e293b; color: #94a3b8; }

    .proposal-card {
        background: #0b1220;
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 14px;
    }
    .proposal-card:hover { border-color: #f59e0b; }
    .proposal-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 10px;
    }
    .proposal-type {
        display: inline-block;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 11px;
        font-weight: 600;
        background: #1e293b;
        color: #f59e0b;
        text-transform: uppercase;
    }
    .vote-bar {
        width: 100%;
        height: 28px;
        background: #1e293b;
        border-radius: 6px;
        overflow: hidden;
        display: flex;
        margin: 10px 0;
    }
    .vote-bar-yes {
        background: linear-gradient(90deg, #166534, #22c55e);
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 12px;
        font-weight: 600;
        color: white;
        min-width: 0;
    }
    .vote-bar-no {
        background: linear-gradient(90deg, #991b1b, #ef4444);
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 12px;
        font-weight: 600;
        color: white;
        min-width: 0;
    }
    .burn-input-group {
        display: flex;
        gap: 8px;
        align-items: end;
    }
    .burn-input-group input {
        flex: 1;
    }
    .btn-governance { background: #f59e0b; color: #020617; }
    .btn-governance:hover { background: #d97706; }
    .btn-vote-yes { background: #166534; color: #4ade80; border: 1px solid #22c55e; }
    .btn-vote-yes:hover { background: #15803d; }
    .btn-vote-no { background: #991b1b; color: #fca5a5; border: 1px solid #ef4444; }
    .btn-vote-no:hover { background: #b91c1c; }
    .badge-governance { background: #78350f; color: #fbbf24; }

    .cycle-info {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 16px;
        margin-bottom: 20px;
    }
    @media (max-width: 768px) {
        .cycle-info { grid-template-columns: 1fr; }
    }
    .cycle-stat {
        text-align: center;
        padding: 12px;
        background: #0b1220;
        border-radius: 8px;
    }
    .cycle-stat-value {
        font-size: 20px;
        font-weight: 700;
        color: #f59e0b;
    }
    .cycle-stat-label {
        font-size: 12px;
        color: #94a3b8;
        margin-top: 4px;
    }

    /* Crypto Ticker */
    .crypto-ticker {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: #020617;
        border-top: 1px solid #7c3aed;
        padding: 8px 0;
        font-size: 0.85rem;
        white-space: nowrap;
        overflow: hidden;
        z-index: 100;
    }
    .crypto-ticker-inner {
        display: inline-block;
        animation: crypto-scroll 60s linear infinite;
    }
    @keyframes crypto-scroll {
        0% { transform: translateX(0); }
        100% { transform: translateX(-50%); }
    }
    .ticker-item {
        display: inline-block;
        padding: 0 20px;
        cursor: pointer;
        text-decoration: none;
        color: #e5e7eb;
        transition: color 0.2s;
    }
    .ticker-item:hover { color: #a78bfa; }
    .ticker-symbol { font-weight: 700; color: #a78bfa; }
    .ticker-price { margin-left: 6px; }
    .ticker-change { margin-left: 6px; font-weight: 600; }
    .ticker-up { color: #4ade80; }
    .ticker-down { color: #f87171; }
    .ticker-flat { color: #94a3b8; }
    .ticker-sep { color: #334155; padding: 0 4px; }

    /* Token Info Screen */
    .token-hero {
        background: linear-gradient(135deg, #1a0533 0%, #0c1a33 50%, #020617 100%);
        border: 1px solid #7c3aed;
        border-radius: 16px;
        padding: 32px;
        margin-bottom: 20px;
    }
    .token-logo {
        display: inline-block;
        border-radius: 8px;
        overflow: hidden;
        border: 2px solid #4c1d95;
        vertical-align: middle;
        margin-right: 12px;
    }
    .token-price-big {
        font-size: 36px;
        font-weight: 800;
        color: #e5e7eb;
    }
    .token-change-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 14px;
        font-weight: 700;
        margin-left: 12px;
    }
    .token-change-up { background: #166534; color: #4ade80; }
    .token-change-down { background: #991b1b; color: #fca5a5; }
    .token-change-flat { background: #1e293b; color: #94a3b8; }
    .info-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 12px;
        margin-bottom: 20px;
    }
    @media (max-width: 768px) {
        .info-grid { grid-template-columns: repeat(2, 1fr); }
    }
    .info-stat {
        background: #0b1220;
        border: 1px solid #1e293b;
        border-radius: 8px;
        padding: 14px;
        text-align: center;
    }
    .info-stat-value {
        font-size: 16px;
        font-weight: 700;
        color: #a78bfa;
    }
    .info-stat-label {
        font-size: 11px;
        color: #64748b;
        margin-top: 4px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .supply-bar {
        width: 100%;
        height: 20px;
        background: #1e293b;
        border-radius: 10px;
        overflow: hidden;
        margin: 8px 0;
    }
    .supply-bar-fill {
        height: 100%;
        background: linear-gradient(90deg, #7c3aed, #a78bfa);
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 11px;
        font-weight: 600;
        color: white;
        min-width: 30px;
    }
    .holder-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px 0;
        border-bottom: 1px solid #1e293b;
    }
    .holder-row:last-child { border-bottom: none; }
    .holder-rank {
        width: 24px;
        height: 24px;
        border-radius: 50%;
        background: #4c1d95;
        color: #c4b5fd;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 11px;
        font-weight: 700;
        margin-right: 8px;
    }
    .mini-chart {
        display: flex;
        align-items: flex-end;
        gap: 2px;
        height: 40px;
        margin: 8px 0;
    }
    .mini-chart-bar {
        flex: 1;
        background: #7c3aed;
        border-radius: 2px 2px 0 0;
        min-width: 3px;
        opacity: 0.7;
    }
    .mini-chart-bar:last-child { opacity: 1; }
</style>
"""


# ==========================
# CRYPTO TICKER HELPER
# ==========================
def get_crypto_ticker_html() -> str:
    """Generate a scrolling crypto ticker bar with all tokens and price movement indicators."""
    from counties import get_all_counties
    counties = get_all_counties()
    if not counties:
        return ""

    ticker_items = []
    for c in counties:
        symbol = c["crypto_symbol"]
        price = c["crypto_price"]
        change = c.get("price_change_24h", 0.0)
        logo = c.get("logo_svg", "")

        if change > 0:
            arrow = "&#9650;"  # up triangle
            change_class = "ticker-up"
            change_str = f"+{change:.2f}%"
        elif change < 0:
            arrow = "&#9660;"  # down triangle
            change_class = "ticker-down"
            change_str = f"{change:.2f}%"
        else:
            arrow = "&#9679;"  # dot
            change_class = "ticker-flat"
            change_str = "0.00%"

        logo_html = f'<span class="token-logo" style="display:inline-block;width:16px;height:16px;vertical-align:middle;margin-right:4px;border:none;">{logo}</span>' if logo else ""
        ticker_items.append(
            f'<a href="/token/{symbol}" class="ticker-item">'
            f'{logo_html}'
            f'<span class="ticker-symbol">{symbol}</span>'
            f'<span class="ticker-price">${price:,.4f}</span>'
            f'<span class="ticker-change {change_class}">{arrow} {change_str}</span>'
            f'</a>'
            f'<span class="ticker-sep">|</span>'
        )

    ticker_content = "".join(ticker_items)
    # Duplicate for seamless scrolling
    return f'''
    <div class="crypto-ticker">
        <div class="crypto-ticker-inner">
            {ticker_content}{ticker_content}
        </div>
    </div>
    '''


# ==========================
# COUNTY DASHBOARD (main page)
# ==========================
@router.get("/counties", response_class=HTMLResponse)
async def counties_dashboard(
    session_token: Optional[str] = Cookie(None),
    msg: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
):
    """Main county dashboard."""
    player = get_current_player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)

    from counties import (
        get_all_counties, get_player_county, get_player_wallets,
        is_player_mayor_in_county, CountyPetition, CountyPetitionStatus,
    )
    from cities import get_player_city, City, get_db

    player_city = get_player_city(player.id)
    player_county = get_player_county(player.id)
    counties = get_all_counties()
    wallets = get_player_wallets(player.id)

    # Alert messages
    alert_html = ""
    if msg:
        alert_html = f'<div class="alert alert-success">{msg}</div>'
    if error:
        alert_html = f'<div class="alert alert-error">{error}</div>'

    # Wallets summary
    wallets_html = ""
    if wallets:
        wallets_html = '<div class="card"><h2>Your Crypto Wallets</h2>'
        for w in wallets:
            wallets_html += f'''
            <div class="wallet-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <span class="badge badge-crypto">{w["symbol"]}</span>
                        <span class="wallet-balance" style="margin-left: 12px;">{w["balance"]:.6f}</span>
                        <span class="wallet-value">(${w["value"]:,.2f} @ ${w["price"]:,.2f}/unit)</span>
                    </div>
                    <div>
                        <a href="/exchange?symbol={w["symbol"]}" class="btn btn-crypto btn-sm">Trade</a>
                    </div>
                </div>
            </div>
            '''
        wallets_html += '</div>'

    # Your county section
    your_county_html = ""
    if player_county:
        your_county_html = f'''
        <div class="card">
            <h2>Your County: {player_county.name}</h2>
            <p style="color: #94a3b8;">You are a member of <strong>{player_county.name}</strong> through your city.</p>
            <div style="margin-top: 12px; display: flex; gap: 12px;">
                <a href="/county/{player_county.id}" class="btn btn-primary">View County</a>
                <a href="/county/{player_county.id}/mining" class="btn btn-crypto">Mining Node</a>
                <a href="/county/{player_county.id}/governance" class="btn btn-governance">Governance</a>
                <a href="/exchange" class="btn btn-secondary">Crypto Exchange</a>
            </div>
        </div>
        '''
    elif player_city:
        # Check for pending petition
        db = get_db()
        from counties import CountyPetition, CountyPetitionStatus
        pending_petition = db.query(CountyPetition).filter(
            CountyPetition.city_id == player_city.id,
            CountyPetition.status.in_([
                CountyPetitionStatus.PENDING_GOV_REVIEW,
                CountyPetitionStatus.GOV_APPROVED_JOIN,
                CountyPetitionStatus.POLL_ACTIVE,
            ])
        ).first()
        db.close()

        is_mayor = player_city.mayor_id == player.id

        if pending_petition:
            status_text = {
                CountyPetitionStatus.PENDING_GOV_REVIEW: "Under government review",
                CountyPetitionStatus.GOV_APPROVED_JOIN: "Government approved - awaiting county vote",
                CountyPetitionStatus.POLL_ACTIVE: "County members are voting",
            }.get(pending_petition.status, pending_petition.status)

            your_county_html = f'''
            <div class="card">
                <h2>County Petition Status</h2>
                <div class="alert alert-info">
                    Your city has an active petition: <strong>{status_text}</strong>
                </div>
            </div>
            '''
        elif is_mayor:
            your_county_html = f'''
            <div class="card">
                <h2>Join or Form a County</h2>
                <p style="color: #94a3b8; margin-bottom: 16px;">
                    As Mayor of <strong>{player_city.name}</strong>, you can petition the government to
                    form a new county or join an existing one. There is a 1-day government review period.
                </p>
                <div style="display: flex; gap: 12px;">
                    <a href="/county/petition/new" class="btn btn-primary">Form New County</a>
                    <a href="/county/petition/join" class="btn btn-secondary">Join Existing County</a>
                </div>
            </div>
            '''
        else:
            your_county_html = '''
            <div class="card">
                <h2>Join or Form a County</h2>
                <p style="color: #94a3b8;">
                    Only city mayors can petition to form or join a county.
                    Ask your mayor to submit a petition.
                </p>
            </div>
            '''
    else:
        your_county_html = '''
        <div class="card">
            <h2>Join or Form a County</h2>
            <p style="color: #94a3b8;">
                You must be a member of a city before you can participate in a county.
                <a href="/cities" class="nav-link">View Cities</a>
            </p>
        </div>
        '''

    # All counties table
    counties_table_html = ""
    if counties:
        db = get_db()
        from auth import Player
        counties_table_html = '''
        <table class="table">
            <thead>
                <tr>
                    <th></th>
                    <th>County</th>
                    <th>Cities</th>
                    <th>Crypto</th>
                    <th>Price</th>
                    <th>24h</th>
                    <th>Market Cap</th>
                    <th>Mining Energy</th>
                    <th>Action</th>
                </tr>
            </thead>
            <tbody>
        '''
        for c in counties:
            change = c.get("price_change_24h", 0.0)
            if change > 0:
                change_html = f'<span class="stat-value positive">+{change:.2f}%</span>'
            elif change < 0:
                change_html = f'<span class="stat-value negative">{change:.2f}%</span>'
            else:
                change_html = '<span style="color:#94a3b8;">0.00%</span>'
            logo = c.get("logo_svg", "")
            logo_html = f'<span style="display:inline-block;width:20px;height:20px;vertical-align:middle;">{logo}</span>' if logo else ""
            counties_table_html += f'''
                <tr>
                    <td>{logo_html}</td>
                    <td><strong>{c["name"]}</strong></td>
                    <td>{c["city_count"]}/{c["max_cities"]}</td>
                    <td><a href="/token/{c["crypto_symbol"]}" class="nav-link" style="margin:0;"><span class="badge badge-crypto">{c["crypto_symbol"]}</span> {c["crypto_name"]}</a></td>
                    <td class="stat-value crypto">${c["crypto_price"]:,.4f}</td>
                    <td>{change_html}</td>
                    <td>${c.get("market_cap", 0):,.2f}</td>
                    <td>${c["mining_energy"]:,.2f}</td>
                    <td><a href="/county/{c["id"]}" class="btn btn-secondary btn-sm">View</a></td>
                </tr>
            '''
        db.close()
        counties_table_html += '</tbody></table>'
    else:
        counties_table_html = '<p style="color: #94a3b8;">No counties exist yet. Be the first to form one!</p>'

    ticker_html = get_crypto_ticker_html()

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Counties · Wadsworth</title>
        {COUNTY_STYLES}
    </head>
    <body>
        <div class="container" style="padding-bottom: 50px;">
            <div class="header">
                <h1>Counties</h1>
                <div>
                    <span style="color: #94a3b8;">{player.business_name}</span>
                    <a href="/city/my" class="nav-link">My City</a>
                    <a href="/exchange" class="nav-link">Crypto Exchange</a>
                    <a href="/" class="nav-link">Dashboard</a>
                </div>
            </div>

            {alert_html}
            {your_county_html}
            {wallets_html}

            <div class="card">
                <h2>All Counties</h2>
                {counties_table_html}
            </div>
        </div>
        {ticker_html}
    </body>
    </html>
    """


# ==========================
# VIEW COUNTY DETAIL
# ==========================
@router.get("/county/{county_id}", response_class=HTMLResponse)
async def view_county(
    county_id: int,
    session_token: Optional[str] = Cookie(None),
    msg: Optional[str] = Query(None),
):
    """View a specific county's details."""
    player = get_current_player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)

    from counties import (
        get_county_by_id, get_county_cities, calculate_crypto_price,
        is_player_in_county, is_player_mayor_in_county,
        CountyPoll, CountyPollStatus, CountyVote, CountyPollType,
    )
    from cities import City, CityMember, get_db
    from auth import Player

    county = get_county_by_id(county_id)
    if not county:
        return RedirectResponse(url="/counties?error=County+not+found", status_code=303)

    db = get_db()
    is_member = is_player_in_county(player.id, county_id)
    crypto_price = calculate_crypto_price(county_id)
    county_city_links = get_county_cities(county_id)

    alert_html = ""
    if msg:
        alert_html = f'<div class="alert alert-info">{msg}</div>'

    # Member cities
    cities_html = '<div class="grid grid-2" style="display:grid; grid-template-columns:1fr 1fr; gap:16px;">'
    total_members = 0
    for link in county_city_links:
        city = db.query(City).filter(City.id == link.city_id).first()
        if not city:
            continue
        mayor = db.query(Player).filter(Player.id == city.mayor_id).first()
        mayor_name = mayor.business_name if mayor else f"Player {city.mayor_id}"
        member_count = db.query(CityMember).filter(CityMember.city_id == city.id).count()
        total_members += member_count

        cities_html += f'''
        <div style="background: #0b1220; border: 1px solid #1e293b; border-radius: 8px; padding: 16px;">
            <h3 style="color: #38bdf8; margin-bottom: 8px;">{city.name}</h3>
            <div class="stat">
                <span class="stat-label">Mayor</span>
                <span class="stat-value">{mayor_name}</span>
            </div>
            <div class="stat">
                <span class="stat-label">Members</span>
                <span class="stat-value">{member_count}</span>
            </div>
            <div class="stat">
                <span class="stat-label">Currency</span>
                <span class="stat-value">{city.currency_type or "Not set"}</span>
            </div>
            <div class="stat">
                <span class="stat-label">Joined</span>
                <span class="stat-value">{link.joined_at.strftime("%Y-%m-%d") if link.joined_at else "N/A"}</span>
            </div>
        </div>
        '''
    cities_html += '</div>'

    # Active polls (for county members)
    polls_html = ""
    if is_member:
        polls = db.query(CountyPoll).filter(
            CountyPoll.county_id == county_id,
            CountyPoll.status == CountyPollStatus.ACTIVE,
        ).all()

        if polls:
            polls_html = '<h3>Active Polls</h3>'
            for poll in polls:
                existing_vote = db.query(CountyVote).filter(
                    CountyVote.poll_id == poll.id,
                    CountyVote.voter_id == player.id,
                ).first()

                poll_title = ""
                if poll.poll_type == CountyPollType.ADD_CITY:
                    target_city = db.query(City).filter(City.id == poll.target_city_id).first()
                    city_name = target_city.name if target_city else f"City {poll.target_city_id}"
                    poll_title = f"Add City: {city_name}"

                vote_buttons = ""
                if existing_vote:
                    vote_buttons = f'<span class="badge badge-info">You voted: {existing_vote.vote.upper()}</span>'
                else:
                    vote_buttons = f'''
                    <div class="poll-votes">
                        <form action="/api/county/vote" method="post" style="flex:1;">
                            <input type="hidden" name="poll_id" value="{poll.id}">
                            <input type="hidden" name="vote" value="yes">
                            <button type="submit" class="vote-btn vote-yes" style="width:100%;">YES</button>
                        </form>
                        <form action="/api/county/vote" method="post" style="flex:1;">
                            <input type="hidden" name="poll_id" value="{poll.id}">
                            <input type="hidden" name="vote" value="no">
                            <button type="submit" class="vote-btn vote-no" style="width:100%;">NO</button>
                        </form>
                    </div>
                    '''

                polls_html += f'''
                <div class="poll-card">
                    <div class="poll-header">
                        <strong>{poll_title}</strong>
                        <span class="badge badge-warning">Closes: {poll.closes_at.strftime("%Y-%m-%d %H:%M")}</span>
                    </div>
                    {vote_buttons}
                </div>
                '''
        else:
            polls_html = '<p style="color: #64748b;">No active polls.</p>'

    # County Parliament info
    parliament_html = ""
    if is_member:
        parliament_html = '''
        <div class="card">
            <h2>County Parliament</h2>
            <div class="grid grid-2" style="display:grid; grid-template-columns:1fr 1fr; gap:16px;">
                <div>
                    <h3>Lower House</h3>
                    <p style="color: #94a3b8; font-size: 13px;">
                        All city members from every city in the county form the lower house.
                        Each member gets 1 vote on county matters.
                    </p>
                </div>
                <div>
                    <h3>Upper House</h3>
                    <p style="color: #94a3b8; font-size: 13px;">
                        City mayors form the upper house and always receive <strong style="color: #fbbf24;">3 votes</strong>
                        on all county decisions. Abstaining members' votes follow their mayor's vote.
                    </p>
                </div>
            </div>
        </div>
        '''

    db.close()

    # Navigation buttons for members
    member_nav = ""
    if is_member:
        member_nav = f'''
        <div style="display: flex; gap: 12px; margin-bottom: 16px;">
            <a href="/county/{county_id}/mining" class="btn btn-crypto">Mining Node</a>
            <a href="/county/{county_id}/governance" class="btn btn-governance">Governance Voting</a>
            <a href="/exchange" class="btn btn-secondary">Crypto Exchange</a>
        </div>
        '''

    circulating_supply = county.total_crypto_minted - county.total_crypto_burned

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>{county.name} · Wadsworth</title>
        {COUNTY_STYLES}
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>{county.name}</h1>
                <div>
                    <a href="/counties" class="nav-link">All Counties</a>
                    <a href="/city/my" class="nav-link">My City</a>
                    <a href="/" class="nav-link">Dashboard</a>
                </div>
            </div>

            {alert_html}
            {member_nav}

            <div class="grid grid-2" style="display:grid; grid-template-columns:1fr 1fr; gap:16px;">
                <div class="card">
                    <h2>County Info</h2>
                    <div class="stat">
                        <span class="stat-label">Cities</span>
                        <span class="stat-value">{len(county_city_links)}/{5}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Total Members</span>
                        <span class="stat-value">{total_members}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Founded</span>
                        <span class="stat-value">{county.created_at.strftime("%Y-%m-%d") if county.created_at else "N/A"}</span>
                    </div>
                </div>

                <div class="card">
                    <h2>Cryptocurrency: {county.crypto_name}</h2>
                    <div class="stat">
                        <span class="stat-label">Symbol</span>
                        <span class="stat-value crypto"><span class="badge badge-crypto">{county.crypto_symbol}</span></span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Price</span>
                        <span class="stat-value crypto">${crypto_price:,.2f}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Circulating Supply</span>
                        <span class="stat-value">{circulating_supply:,.6f}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Total Minted</span>
                        <span class="stat-value">{county.total_crypto_minted:,.6f}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Total Burned</span>
                        <span class="stat-value">{county.total_crypto_burned:,.6f}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Mining Energy Pool</span>
                        <span class="stat-value">${county.mining_energy_pool:,.2f}</span>
                    </div>
                </div>
            </div>

            <div class="card">
                <h2>Member Cities ({len(county_city_links)}/{5})</h2>
                {cities_html}
            </div>

            {"" if not is_member else f'''
            <div class="card">
                <h2>Active Polls</h2>
                {polls_html}
            </div>
            '''}

            {parliament_html}
        </div>
    </body>
    </html>
    """


# ==========================
# PETITION: FORM NEW COUNTY
# ==========================
@router.get("/county/petition/new", response_class=HTMLResponse)
async def petition_new_county_page(session_token: Optional[str] = Cookie(None)):
    """Page to form a new county."""
    player = get_current_player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)

    from cities import get_player_city

    player_city = get_player_city(player.id)
    if not player_city:
        return RedirectResponse(url="/counties?error=You+must+be+in+a+city", status_code=303)
    if player_city.mayor_id != player.id:
        return RedirectResponse(url="/counties?error=Only+mayors+can+petition", status_code=303)

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Form New County · Wadsworth</title>
        {COUNTY_STYLES}
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Form New County</h1>
                <div>
                    <a href="/counties" class="nav-link">Back to Counties</a>
                </div>
            </div>

            <div class="card">
                <h2>Petition to Form a New County</h2>
                <p style="color: #94a3b8; margin-bottom: 16px;">
                    As Mayor of <strong>{player_city.name}</strong>, you can petition the government to form a new county.
                    After a 1-day review period, your city will be the founding member.
                    You must choose a name for the county and its cryptocurrency.
                </p>

                <form action="/api/county/petition" method="post">
                    <input type="hidden" name="petition_type" value="new">
                    <div class="form-group">
                        <label>County Name</label>
                        <input type="text" name="county_name" required placeholder="e.g., Wadsworth County" maxlength="50">
                    </div>
                    <div class="form-group">
                        <label>Cryptocurrency Name</label>
                        <input type="text" name="crypto_name" required placeholder="e.g., WadCoin" maxlength="30">
                    </div>
                    <div class="form-group">
                        <label>Crypto Symbol (3-5 characters)</label>
                        <input type="text" name="crypto_symbol" required placeholder="e.g., WDC" maxlength="5" minlength="2"
                               style="text-transform: uppercase;">
                    </div>
                    <button type="submit" class="btn btn-primary">Submit Petition</button>
                </form>
            </div>
        </div>
    </body>
    </html>
    """


# ==========================
# PETITION: JOIN EXISTING COUNTY
# ==========================
@router.get("/county/petition/join", response_class=HTMLResponse)
async def petition_join_county_page(session_token: Optional[str] = Cookie(None)):
    """Page to join an existing county."""
    player = get_current_player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)

    from cities import get_player_city
    from counties import get_all_counties, MAX_COUNTY_CITIES

    player_city = get_player_city(player.id)
    if not player_city:
        return RedirectResponse(url="/counties?error=You+must+be+in+a+city", status_code=303)
    if player_city.mayor_id != player.id:
        return RedirectResponse(url="/counties?error=Only+mayors+can+petition", status_code=303)

    counties = get_all_counties()
    available = [c for c in counties if c["city_count"] < MAX_COUNTY_CITIES]

    options_html = ""
    if available:
        for c in available:
            options_html += f'<option value="{c["id"]}">{c["name"]} ({c["city_count"]}/{c["max_cities"]} cities) - Crypto: {c["crypto_symbol"]}</option>'
    else:
        options_html = '<option disabled>No counties with available slots</option>'

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Join County · Wadsworth</title>
        {COUNTY_STYLES}
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Join Existing County</h1>
                <div>
                    <a href="/counties" class="nav-link">Back to Counties</a>
                </div>
            </div>

            <div class="card">
                <h2>Petition to Join a County</h2>
                <p style="color: #94a3b8; margin-bottom: 16px;">
                    As Mayor of <strong>{player_city.name}</strong>, you can petition to join an existing county.
                    After a 1-day government review, the county's members will vote on your admission.
                    The admission poll is open for 1 day. Mayors get 3 votes and abstaining members
                    vote with their mayor.
                </p>

                <form action="/api/county/petition" method="post">
                    <input type="hidden" name="petition_type" value="join">
                    <div class="form-group">
                        <label>Select County</label>
                        <select name="target_county_id" required>
                            <option value="">-- Select a County --</option>
                            {options_html}
                        </select>
                    </div>
                    <button type="submit" class="btn btn-primary" {"disabled" if not available else ""}>
                        Submit Petition
                    </button>
                </form>
            </div>
        </div>
    </body>
    </html>
    """


# ==========================
# MINING NODE
# ==========================
@router.get("/county/{county_id}/mining", response_class=HTMLResponse)
async def county_mining_node(
    county_id: int,
    session_token: Optional[str] = Cookie(None),
    msg: Optional[str] = Query(None),
):
    """County Mining Node dashboard."""
    player = get_current_player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)

    from counties import (
        get_county_by_id, is_player_in_county, calculate_crypto_price,
        MiningDeposit, CryptoWallet, calculate_block_reward,
        get_circulating_supply, get_remaining_supply,
        MAX_TOKEN_SUPPLY, HALVING_INTERVAL,
    )
    from cities import CityMember, City, get_db
    import inventory
    import market

    county = get_county_by_id(county_id)
    if not county:
        return RedirectResponse(url="/counties?error=County+not+found", status_code=303)

    if not is_player_in_county(player.id, county_id):
        return RedirectResponse(url=f"/county/{county_id}?msg=Members+only", status_code=303)

    db = get_db()

    # Get player's city and currency info
    membership = db.query(CityMember).filter(CityMember.player_id == player.id).first()
    player_city = db.query(City).filter(City.id == membership.city_id).first() if membership else None
    currency_type = player_city.currency_type if player_city else None
    currency_qty = 0.0
    currency_price = 0.0

    if currency_type:
        currency_qty = inventory.get_item_quantity(player.id, currency_type)
        currency_price = market.get_market_price(currency_type) or 1.0

    # Get player's crypto wallet
    wallet = db.query(CryptoWallet).filter(
        CryptoWallet.player_id == player.id,
        CryptoWallet.crypto_symbol == county.crypto_symbol,
    ).first()

    crypto_balance = wallet.balance if wallet else 0.0
    total_mined = wallet.total_mined if wallet else 0.0
    crypto_price = calculate_crypto_price(county_id)
    block_reward = calculate_block_reward(county.total_crypto_minted or 0.0)
    circ_supply = get_circulating_supply(county)
    remaining_supply = get_remaining_supply(county)
    max_supply = county.max_supply or MAX_TOKEN_SUPPLY
    minted = county.total_crypto_minted or 0.0
    supply_pct = (minted / max_supply * 100) if max_supply > 0 else 0
    halvings = int(minted / HALVING_INTERVAL)

    # Recent deposits by this player
    recent_deposits = db.query(MiningDeposit).filter(
        MiningDeposit.county_id == county_id,
        MiningDeposit.player_id == player.id,
    ).order_by(MiningDeposit.deposited_at.desc()).limit(10).all()

    deposits_html = ""
    if recent_deposits:
        deposits_html = '''
        <table class="table">
            <thead><tr><th>Date</th><th>Currency</th><th>Amount</th><th>Energy Value</th><th>Status</th></tr></thead>
            <tbody>
        '''
        for dep in recent_deposits:
            status = '<span class="badge badge-success">Consumed</span>' if dep.consumed else '<span class="badge badge-warning">Pending</span>'
            deposits_html += f'''
            <tr>
                <td>{dep.deposited_at.strftime("%m/%d %H:%M") if dep.deposited_at else "N/A"}</td>
                <td>{dep.currency_type}</td>
                <td>{dep.quantity_deposited:,.2f}</td>
                <td>${dep.cash_value_at_deposit:,.2f}</td>
                <td>{status}</td>
            </tr>
            '''
        deposits_html += '</tbody></table>'
    else:
        deposits_html = '<p style="color: #64748b;">No deposits yet. Deposit your city currency to start mining!</p>'

    alert_html = f'<div class="alert alert-info">{msg}</div>' if msg else ""

    deposit_form = ""
    if currency_type:
        deposit_form = f'''
        <form action="/api/county/mining/deposit" method="post">
            <input type="hidden" name="county_id" value="{county_id}">
            <div class="form-group">
                <label>Deposit {currency_type} (You have: {currency_qty:,.2f} @ ${currency_price:,.2f} each)</label>
                <input type="number" name="quantity" min="1" max="{currency_qty}" step="0.01"
                       placeholder="Amount to deposit" required>
            </div>
            <button type="submit" class="btn btn-crypto">Deposit to Mining Node</button>
        </form>
        '''
    else:
        deposit_form = '<p style="color: #f87171;">Your city has no currency set. Currency must be set before you can mine.</p>'

    db.close()

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Mining Node · {county.name} · Wadsworth</title>
        {COUNTY_STYLES}
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Mining Node</h1>
                <div>
                    <a href="/county/{county_id}" class="nav-link">Back to County</a>
                    <a href="/exchange" class="nav-link">Crypto Exchange</a>
                </div>
            </div>

            {alert_html}

            <div class="mining-node" style="margin-bottom: 16px;">
                <h2 style="color: #a78bfa; margin-bottom: 16px;">{county.crypto_name} Mining Node</h2>
                <p style="color: #94a3b8; margin-bottom: 20px;">
                    Deposit your city's currency into the mining node. Deposits are consumed as mining energy
                    and you receive <span class="badge badge-crypto">{county.crypto_symbol}</span> cryptocurrency
                    in return. Mining payouts occur every hour, distributing rewards proportionally to depositors.
                </p>

                <div class="grid grid-3" style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:16px; margin-bottom:20px;">
                    <div>
                        <h3 style="color: #a78bfa;">Your {county.crypto_symbol} Balance</h3>
                        <div class="wallet-balance">{crypto_balance:,.6f}</div>
                        <div class="wallet-value">${crypto_balance * crypto_price:,.4f}</div>
                    </div>
                    <div>
                        <h3 style="color: #a78bfa;">Total Mined</h3>
                        <div class="wallet-balance">{total_mined:,.6f}</div>
                        <div class="wallet-value">${total_mined * crypto_price:,.4f}</div>
                    </div>
                    <div>
                        <h3 style="color: #a78bfa;">Node Energy Pool</h3>
                        <div class="wallet-balance">${county.mining_energy_pool:,.2f}</div>
                        <div class="wallet-value">Total energy available</div>
                    </div>
                </div>

                <div class="grid grid-3" style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:16px; margin-bottom:20px;">
                    <div style="background:#0b1220;border-radius:8px;padding:12px;text-align:center;">
                        <div style="font-size:11px;color:#64748b;text-transform:uppercase;">Block Reward</div>
                        <div style="font-size:18px;font-weight:700;color:#a78bfa;">{block_reward:,.6f}</div>
                        <div style="font-size:11px;color:#64748b;">{county.crypto_symbol}/payout (halving {halvings})</div>
                    </div>
                    <div style="background:#0b1220;border-radius:8px;padding:12px;text-align:center;">
                        <div style="font-size:11px;color:#64748b;text-transform:uppercase;">Supply Progress</div>
                        <div class="supply-bar" style="margin:6px 0;">
                            <div class="supply-bar-fill" style="width:{min(supply_pct, 100):.1f}%;">{supply_pct:.1f}%</div>
                        </div>
                        <div style="font-size:11px;color:#64748b;">{circ_supply:,.2f} / {max_supply:,.0f}</div>
                    </div>
                    <div style="background:#0b1220;border-radius:8px;padding:12px;text-align:center;">
                        <div style="font-size:11px;color:#64748b;text-transform:uppercase;">Remaining to Mine</div>
                        <div style="font-size:18px;font-weight:700;color:#4ade80;">{remaining_supply:,.2f}</div>
                        <div style="font-size:11px;color:#64748b;"><a href="/token/{county.crypto_symbol}" class="nav-link" style="margin:0;">View Token Info</a></div>
                    </div>
                </div>

                {deposit_form}
            </div>

            <div class="card">
                <h2>How Mining Works</h2>
                <div class="grid grid-2" style="display:grid; grid-template-columns:1fr 1fr; gap:16px;">
                    <div>
                        <h3>Energy System</h3>
                        <p style="color: #94a3b8; font-size: 13px;">
                            City members deposit their respective city currency into the mining node.
                            The node consumes those deposits as <strong>mining energy</strong>.
                            This energy powers the entire blockchain - without energy, no transactions
                            (buys, sells, swaps) can occur on the exchange.
                        </p>
                    </div>
                    <div>
                        <h3>Halving & Supply Cap</h3>
                        <p style="color: #94a3b8; font-size: 13px;">
                            Like Bitcoin, <span class="badge badge-crypto">{county.crypto_symbol}</span> has a
                            <strong>max supply of {max_supply:,.0f}</strong> tokens. Mining rewards start at
                            50 tokens/payout and halve every {HALVING_INTERVAL:,.0f} tokens minted.
                            Current reward: <strong>{block_reward:,.6f}</strong>.
                            Rewards decrease over time, making early mining more valuable.
                        </p>
                    </div>
                </div>
            </div>

            <div class="card">
                <h2>Your Recent Deposits</h2>
                {deposits_html}
            </div>
        </div>
    </body>
    </html>
    """


# ==========================
# WADSWORTH CRYPTO EXCHANGE
# ==========================
@router.get("/exchange", response_class=HTMLResponse)
async def crypto_exchange(
    session_token: Optional[str] = Cookie(None),
    msg: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    symbol: Optional[str] = Query(None),
):
    """Wadsworth Crypto Exchange - buy, sell, swap crypto."""
    player = get_current_player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)

    from counties import get_all_counties, get_player_wallets, County
    from cities import get_db

    wallets = get_player_wallets(player.id)
    counties = get_all_counties()

    alert_html = ""
    if msg:
        alert_html = f'<div class="alert alert-success">{msg}</div>'
    if error:
        alert_html = f'<div class="alert alert-error">{error}</div>'

    # Portfolio summary
    total_portfolio_value = sum(w["value"] for w in wallets)
    wallets_html = ""
    if wallets:
        wallets_html = '<div style="margin-bottom: 20px;">'
        for w in wallets:
            wallets_html += f'''
            <div class="wallet-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <span class="badge badge-crypto">{w["symbol"]}</span>
                        <span class="wallet-balance" style="margin-left: 12px;">{w["balance"]:.6f}</span>
                        <span class="wallet-value">(${w["value"]:,.2f} @ ${w["price"]:,.2f}/unit)</span>
                    </div>
                    <div style="font-size: 12px; color: #94a3b8;">
                        Mined: {w["total_mined"]:.6f} | Bought: {w["total_bought"]:.6f} | Sold: {w["total_sold"]:.6f}
                    </div>
                </div>
            </div>
            '''
        wallets_html += '</div>'
    else:
        wallets_html = '<p style="color: #94a3b8; margin-bottom: 20px;">You have no crypto yet. Mine some through a County Mining Node or buy on this exchange.</p>'

    # Available cryptos dropdown
    crypto_options = ""
    for c in counties:
        selected = 'selected' if symbol and symbol == c["crypto_symbol"] else ""
        crypto_options += f'<option value="{c["crypto_symbol"]}" {selected}>{c["crypto_symbol"]} - {c["crypto_name"]} (${c["crypto_price"]:,.4f})</option>'

    # Wallet options for selling
    sell_options = ""
    for w in wallets:
        if w["balance"] > 0:
            selected = 'selected' if symbol and symbol == w["symbol"] else ""
            sell_options += f'<option value="{w["symbol"]}" {selected}>{w["symbol"]} (Balance: {w["balance"]:.6f})</option>'

    # Market overview table with full data
    market_html = '''
    <table class="table">
        <thead><tr>
            <th></th><th>Token</th><th>Price</th><th>24h</th>
            <th>Market Cap</th><th>Circ. Supply</th><th>Max Supply</th>
            <th>Treasury</th><th>Energy</th>
        </tr></thead>
        <tbody>
    '''
    for c in counties:
        change = c.get("price_change_24h", 0.0)
        if change > 0:
            change_html = f'<span class="stat-value positive">+{change:.2f}%</span>'
        elif change < 0:
            change_html = f'<span class="stat-value negative">{change:.2f}%</span>'
        else:
            change_html = '<span style="color:#94a3b8;">0.00%</span>'
        logo = c.get("logo_svg", "")
        logo_html = f'<span style="display:inline-block;width:18px;height:18px;vertical-align:middle;">{logo}</span>' if logo else ""
        market_html += f'''
        <tr>
            <td>{logo_html}</td>
            <td><a href="/token/{c["crypto_symbol"]}" style="text-decoration:none;color:#e5e7eb;">
                <span class="badge badge-crypto">{c["crypto_symbol"]}</span>
                <span style="margin-left:4px;">{c["crypto_name"]}</span>
            </a></td>
            <td class="stat-value crypto">${c["crypto_price"]:,.4f}</td>
            <td>{change_html}</td>
            <td>${c.get("market_cap", 0):,.2f}</td>
            <td>{c.get("circulating_supply", 0):,.2f}</td>
            <td>{c.get("max_supply", 0):,.0f}</td>
            <td>${c.get("treasury_balance", 0):,.2f}</td>
            <td>${c["mining_energy"]:,.2f}</td>
        </tr>
        '''
    market_html += '</tbody></table>'

    ticker_html = get_crypto_ticker_html()

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Wadsworth Crypto Exchange</title>
        {COUNTY_STYLES}
    </head>
    <body>
        <div class="container" style="padding-bottom: 50px;">
            <div class="header">
                <h1>Wadsworth Crypto Exchange</h1>
                <div>
                    <span style="color: #94a3b8;">Cash: ${player.cash_balance:,.2f}</span>
                    <a href="/counties" class="nav-link">Counties</a>
                    <a href="/" class="nav-link">Dashboard</a>
                </div>
            </div>

            {alert_html}

            <div class="exchange-panel" style="margin-bottom: 16px;">
                <h2 style="color: #38bdf8; margin-bottom: 4px;">Your Portfolio</h2>
                <p style="color: #94a3b8; margin-bottom: 16px;">Total crypto value: <strong style="color: #a78bfa;">${total_portfolio_value:,.2f}</strong></p>
                {wallets_html}
            </div>

            <div class="grid grid-3" style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:16px; margin-bottom: 16px;">
                <!-- Buy Crypto -->
                <div class="card">
                    <h2>Buy Crypto</h2>
                    <p style="color: #94a3b8; font-size: 13px; margin-bottom: 12px;">
                        Buy cryptocurrency with cash. 2% exchange fee.
                        <br><span style="color:#f59e0b;font-size:11px;">Requires blockchain energy. Cash goes to county treasury.</span>
                    </p>
                    <form action="/api/exchange/buy" method="post">
                        <div class="form-group">
                            <label>Crypto to Buy</label>
                            <select name="crypto_symbol" required>
                                <option value="">-- Select --</option>
                                {crypto_options}
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Cash Amount ($)</label>
                            <input type="number" name="cash_amount" min="0.01" step="0.0001"
                                   max="{player.cash_balance}" placeholder="Amount in $" required>
                        </div>
                        <button type="submit" class="btn btn-primary">Buy</button>
                    </form>
                </div>

                <!-- Sell Crypto -->
                <div class="card">
                    <h2>Sell Crypto</h2>
                    <p style="color: #94a3b8; font-size: 13px; margin-bottom: 12px;">
                        Sell cryptocurrency for cash. 2% exchange fee.
                        <br><span style="color:#f59e0b;font-size:11px;">Cash paid from county treasury. Tokens burned.</span>
                    </p>
                    <form action="/api/exchange/sell" method="post">
                        <div class="form-group">
                            <label>Crypto to Sell</label>
                            <select name="crypto_symbol" required>
                                <option value="">-- Select --</option>
                                {sell_options if sell_options else '<option disabled>No crypto to sell</option>'}
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Amount</label>
                            <input type="number" name="amount" min="0.000001" step="0.000001"
                                   placeholder="Crypto amount" required>
                        </div>
                        <button type="submit" class="btn btn-crypto">Sell</button>
                    </form>
                </div>

                <!-- Swap Crypto -->
                <div class="card">
                    <h2>Swap Crypto</h2>
                    <p style="color: #94a3b8; font-size: 13px; margin-bottom: 12px;">
                        Swap one crypto for another. 2% exchange fee.
                        <br><span style="color:#f59e0b;font-size:11px;">Both blockchains must have energy.</span>
                    </p>
                    <form action="/api/exchange/swap" method="post">
                        <div class="form-group">
                            <label>Sell</label>
                            <select name="sell_symbol" required>
                                <option value="">-- Select --</option>
                                {sell_options if sell_options else '<option disabled>No crypto to swap</option>'}
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Sell Amount</label>
                            <input type="number" name="sell_amount" min="0.000001" step="0.000001"
                                   placeholder="Amount to sell" required>
                        </div>
                        <div class="form-group">
                            <label>Buy</label>
                            <select name="buy_symbol" required>
                                <option value="">-- Select --</option>
                                {crypto_options}
                            </select>
                        </div>
                        <button type="submit" class="btn btn-secondary">Swap</button>
                    </form>
                </div>
            </div>

            <div class="card">
                <h2>Market Overview</h2>
                <p style="color: #94a3b8; font-size: 13px; margin-bottom: 12px;">
                    Click any token symbol to view full tokenomics. Prices are pegged to total member wealth / 1B.
                    All tokens have a max supply of 21M with Bitcoin-like halving rewards.
                </p>
                {market_html if counties else '<p style="color: #64748b;">No cryptocurrencies exist yet.</p>'}
            </div>
        </div>
        {ticker_html}
    </body>
    </html>
    """


# ==========================
# TOKEN INFO PAGE
# ==========================
@router.get("/token/{crypto_symbol}", response_class=HTMLResponse)
async def token_info_page(
    crypto_symbol: str,
    session_token: Optional[str] = Cookie(None),
):
    """Full token information screen with tokenomics, holders, charts."""
    player = get_current_player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)

    from counties import get_token_info, get_price_history, CryptoWallet, get_db as counties_get_db

    info = get_token_info(crypto_symbol)
    if not info:
        return RedirectResponse(url="/exchange?error=Token+not+found", status_code=303)

    # Price history for mini chart
    history = get_price_history(crypto_symbol, hours=24)

    # Player's wallet for this token
    db = counties_get_db()
    wallet = db.query(CryptoWallet).filter(
        CryptoWallet.player_id == player.id,
        CryptoWallet.crypto_symbol == crypto_symbol,
    ).first()
    player_balance = wallet.balance if wallet else 0.0
    player_value = player_balance * info["price"]
    db.close()

    # Price change badge
    change = info["price_change_24h"]
    if change > 0:
        change_badge = f'<span class="token-change-badge token-change-up">&#9650; +{change:.2f}%</span>'
    elif change < 0:
        change_badge = f'<span class="token-change-badge token-change-down">&#9660; {change:.2f}%</span>'
    else:
        change_badge = '<span class="token-change-badge token-change-flat">&#9679; 0.00%</span>'

    # Mini price chart
    chart_html = ""
    if history and len(history) > 1:
        prices = [h["price"] for h in history]
        max_p = max(prices) if prices else 1
        min_p = min(prices) if prices else 0
        price_range = max_p - min_p if max_p != min_p else 1
        chart_html = '<div class="mini-chart">'
        for p in prices[-48:]:  # Last 48 data points
            height_pct = max(5, ((p - min_p) / price_range) * 100)
            chart_html += f'<div class="mini-chart-bar" style="height:{height_pct}%;"></div>'
        chart_html += '</div>'
        chart_html += f'<div style="display:flex;justify-content:space-between;font-size:11px;color:#64748b;"><span>24h ago</span><span>Now</span></div>'

    # Supply progress bar
    supply_pct = info["supply_pct_minted"]
    supply_bar_html = f'''
    <div class="supply-bar">
        <div class="supply-bar-fill" style="width:{min(supply_pct, 100):.1f}%;">{supply_pct:.2f}%</div>
    </div>
    <div style="display:flex;justify-content:space-between;font-size:11px;color:#64748b;">
        <span>Minted: {info["total_minted"]:,.2f}</span>
        <span>Burned: {info["total_burned"]:,.2f}</span>
        <span>Max: {info["max_supply"]:,.0f}</span>
    </div>
    '''

    # Top holders list
    holders_html = ""
    if info["top_holders"]:
        for i, h in enumerate(info["top_holders"], 1):
            holders_html += f'''
            <div class="holder-row">
                <div>
                    <span class="holder-rank">{i}</span>
                    <span style="color: #e5e7eb;">{h["name"]}</span>
                </div>
                <div style="text-align:right;">
                    <div style="color: #a78bfa; font-weight: 600;">{h["balance"]:,.6f} {crypto_symbol}</div>
                    <div style="font-size: 11px; color: #64748b;">{h["pct_of_supply"]:.2f}% of supply</div>
                </div>
            </div>
            '''
    else:
        holders_html = '<p style="color: #64748b;">No holders yet.</p>'

    # Halving info
    next_halving = info["next_halving_at"]
    halvings_done = info["halvings_completed"]

    from counties import HALVING_INTERVAL
    halving_progress = (info["total_minted"] % HALVING_INTERVAL) / HALVING_INTERVAL * 100 if HALVING_INTERVAL > 0 else 0

    logo_html = f'<span class="token-logo">{info["logo_svg"]}</span>' if info["logo_svg"] else ""

    ticker_html = get_crypto_ticker_html()

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>{info["crypto_name"]} ({crypto_symbol}) · Token Info</title>
        {COUNTY_STYLES}
    </head>
    <body>
        <div class="container" style="padding-bottom: 50px;">
            <div class="header">
                <h1>Token Info</h1>
                <div>
                    <a href="/exchange?symbol={crypto_symbol}" class="nav-link">Trade</a>
                    <a href="/exchange" class="nav-link">Exchange</a>
                    <a href="/county/{info['county_id']}" class="nav-link">{info['county_name']}</a>
                    <a href="/" class="nav-link">Dashboard</a>
                </div>
            </div>

            <!-- Hero Section -->
            <div class="token-hero">
                <div style="display:flex;align-items:center;gap:16px;margin-bottom:20px;">
                    <span class="token-logo" style="width:48px;height:48px;border-radius:12px;">{info["logo_svg"].replace('width="32" height="32"', 'width="48" height="48"') if info["logo_svg"] else ""}</span>
                    <div>
                        <div style="font-size:14px;color:#94a3b8;">{info["crypto_name"]}</div>
                        <div style="display:flex;align-items:center;">
                            <span class="badge badge-crypto" style="font-size:16px;padding:6px 14px;">{crypto_symbol}</span>
                            <span style="margin-left:12px;color:#64748b;font-size:13px;">on {info["county_name"]} Blockchain</span>
                        </div>
                    </div>
                </div>

                <div style="display:flex;align-items:baseline;gap:8px;margin-bottom:16px;">
                    <span class="token-price-big">${info["price"]:,.4f}</span>
                    {change_badge}
                </div>

                {chart_html}

                <div style="display:flex;gap:24px;font-size:13px;color:#94a3b8;margin-top:12px;">
                    <span>24h High: <strong style="color:#4ade80;">${info["high_24h"]:,.4f}</strong></span>
                    <span>24h Low: <strong style="color:#f87171;">${info["low_24h"]:,.4f}</strong></span>
                    <span>24h Volume: <strong style="color:#38bdf8;">${info["volume_24h"]:,.2f}</strong></span>
                </div>
            </div>

            <!-- Your Holdings -->
            <div class="card">
                <h2>Your Holdings</h2>
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div>
                        <div class="wallet-balance">{player_balance:,.6f} {crypto_symbol}</div>
                        <div class="wallet-value">${player_value:,.4f}</div>
                    </div>
                    <div style="display:flex;gap:8px;">
                        <a href="/exchange?symbol={crypto_symbol}" class="btn btn-primary btn-sm">Buy</a>
                        <a href="/exchange?symbol={crypto_symbol}" class="btn btn-crypto btn-sm">Sell</a>
                        <a href="/county/{info['county_id']}/mining" class="btn btn-secondary btn-sm">Mine</a>
                    </div>
                </div>
            </div>

            <!-- Key Stats Grid -->
            <div class="info-grid">
                <div class="info-stat">
                    <div class="info-stat-value">${info["market_cap"]:,.2f}</div>
                    <div class="info-stat-label">Market Cap</div>
                </div>
                <div class="info-stat">
                    <div class="info-stat-value">${info["fdv"]:,.2f}</div>
                    <div class="info-stat-label">Fully Diluted Val.</div>
                </div>
                <div class="info-stat">
                    <div class="info-stat-value">${info["volume_24h"]:,.2f}</div>
                    <div class="info-stat-label">24h Volume</div>
                </div>
                <div class="info-stat">
                    <div class="info-stat-value">{info["holder_count"]}</div>
                    <div class="info-stat-label">Holders</div>
                </div>
                <div class="info-stat">
                    <div class="info-stat-value">{info["circulating_supply"]:,.2f}</div>
                    <div class="info-stat-label">Circulating Supply</div>
                </div>
                <div class="info-stat">
                    <div class="info-stat-value">{info["max_supply"]:,.0f}</div>
                    <div class="info-stat-label">Max Supply</div>
                </div>
                <div class="info-stat">
                    <div class="info-stat-value">${info["treasury_balance"]:,.2f}</div>
                    <div class="info-stat-label">Treasury</div>
                </div>
                <div class="info-stat">
                    <div class="info-stat-value">${info["mining_energy"]:,.2f}</div>
                    <div class="info-stat-label">Mining Energy</div>
                </div>
            </div>

            <!-- Supply & Mining -->
            <div class="grid grid-2" style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">
                <div class="card">
                    <h2>Supply & Tokenomics</h2>
                    {supply_bar_html}
                    <div class="stat" style="margin-top:12px;">
                        <span class="stat-label">Circulating Supply</span>
                        <span class="stat-value crypto">{info["circulating_supply"]:,.6f}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Total Minted</span>
                        <span class="stat-value">{info["total_minted"]:,.6f}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Total Burned</span>
                        <span class="stat-value negative">{info["total_burned"]:,.6f}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Remaining to Mine</span>
                        <span class="stat-value positive">{info["remaining_supply"]:,.2f}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Max Supply</span>
                        <span class="stat-value">{info["max_supply"]:,.0f}</span>
                    </div>
                </div>

                <div class="card">
                    <h2>Mining & Halving</h2>
                    <div class="stat">
                        <span class="stat-label">Current Block Reward</span>
                        <span class="stat-value crypto">{info["block_reward"]:,.6f} {crypto_symbol}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Halvings Completed</span>
                        <span class="stat-value">{halvings_done}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Next Halving At</span>
                        <span class="stat-value">{next_halving:,.0f} minted</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Progress to Next Halving</span>
                        <span class="stat-value">{halving_progress:.1f}%</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Total Mining Payouts</span>
                        <span class="stat-value">{info["total_mining_payouts"]}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Mining Energy Pool</span>
                        <span class="stat-value positive">${info["mining_energy"]:,.2f}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">County Cities</span>
                        <span class="stat-value">{info["city_count"]}</span>
                    </div>
                </div>
            </div>

            <!-- Treasury & Safety -->
            <div class="card">
                <h2>Treasury & Trust</h2>
                <div class="grid grid-3" style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;">
                    <div>
                        <div class="stat">
                            <span class="stat-label">Treasury Balance</span>
                            <span class="stat-value positive">${info["treasury_balance"]:,.4f}</span>
                        </div>
                        <p style="color:#64748b;font-size:11px;margin-top:4px;">
                            Cash held by the county from token purchases.
                            Pays out when tokens are sold.
                        </p>
                    </div>
                    <div>
                        <div class="stat">
                            <span class="stat-label">Blockchain Energy</span>
                            <span class="stat-value {'positive' if info['mining_energy'] > 0 else 'negative'}">${info["mining_energy"]:,.2f}</span>
                        </div>
                        <p style="color:#64748b;font-size:11px;margin-top:4px;">
                            {'&#9679; Blockchain ACTIVE - transactions enabled' if info['mining_energy'] > 0 else '&#9679; Blockchain OFFLINE - no energy, no transactions'}
                        </p>
                    </div>
                    <div>
                        <div class="stat">
                            <span class="stat-label">Created</span>
                            <span class="stat-value">{info["created_at"].strftime("%Y-%m-%d") if info["created_at"] else "N/A"}</span>
                        </div>
                        <p style="color:#64748b;font-size:11px;margin-top:4px;">
                            Native county token. Used for governance voting (burn to vote)
                            and as the base token on this county's blockchain.
                        </p>
                    </div>
                </div>
            </div>

            <!-- Top Holders -->
            <div class="card">
                <h2>Top Holders (Whales)</h2>
                <p style="color:#94a3b8;font-size:13px;margin-bottom:12px;">
                    {info["holder_count"]} unique wallet{"s" if info["holder_count"] != 1 else ""} holding {crypto_symbol}
                </p>
                {holders_html}
            </div>
        </div>
        {ticker_html}
    </body>
    </html>
    """


# ==========================
# API ENDPOINTS
# ==========================
@router.post("/api/county/petition")
async def api_petition(
    petition_type: str = Form(...),
    county_name: Optional[str] = Form(None),
    crypto_name: Optional[str] = Form(None),
    crypto_symbol: Optional[str] = Form(None),
    target_county_id: Optional[int] = Form(None),
    session_token: Optional[str] = Cookie(None),
):
    """Submit a county petition."""
    player = get_current_player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)

    from cities import get_player_city
    from counties import petition_join_form_county

    player_city = get_player_city(player.id)
    if not player_city:
        return RedirectResponse(url="/counties?error=You+must+be+in+a+city", status_code=303)

    if petition_type == "new":
        petition, message = petition_join_form_county(
            mayor_id=player.id,
            city_id=player_city.id,
            proposed_name=county_name,
            proposed_crypto_name=crypto_name,
            proposed_crypto_symbol=crypto_symbol.upper() if crypto_symbol else None,
        )
    elif petition_type == "join":
        if not target_county_id:
            return RedirectResponse(url="/county/petition/join?error=Select+a+county", status_code=303)
        petition, message = petition_join_form_county(
            mayor_id=player.id,
            city_id=player_city.id,
            target_county_id=target_county_id,
        )
    else:
        return RedirectResponse(url="/counties?error=Invalid+petition+type", status_code=303)

    if petition:
        return RedirectResponse(url=f"/counties?msg={message.replace(' ', '+')}", status_code=303)
    else:
        return RedirectResponse(url=f"/counties?error={message.replace(' ', '+')}", status_code=303)


@router.post("/api/county/vote")
async def api_county_vote(
    poll_id: int = Form(...),
    vote: str = Form(...),
    session_token: Optional[str] = Cookie(None),
):
    """Cast a vote on a county poll."""
    player = get_current_player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)

    from counties import cast_county_vote, VoteChoice, CountyPoll, get_db

    vote_choice = VoteChoice.YES if vote == "yes" else VoteChoice.NO
    success, message = cast_county_vote(player.id, poll_id, vote_choice)

    db = get_db()
    poll = db.query(CountyPoll).filter(CountyPoll.id == poll_id).first()
    county_id = poll.county_id if poll else 0
    db.close()

    return RedirectResponse(url=f"/county/{county_id}?msg={message.replace(' ', '+')}", status_code=303)


@router.post("/api/county/mining/deposit")
async def api_mining_deposit(
    county_id: int = Form(...),
    quantity: float = Form(...),
    session_token: Optional[str] = Cookie(None),
):
    """Deposit city currency into the mining node."""
    player = get_current_player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)

    from counties import deposit_to_mining_node

    success, message = deposit_to_mining_node(player.id, county_id, quantity)

    return RedirectResponse(
        url=f"/county/{county_id}/mining?msg={message.replace(' ', '+')}",
        status_code=303,
    )


@router.post("/api/exchange/buy")
async def api_exchange_buy(
    crypto_symbol: str = Form(...),
    cash_amount: float = Form(...),
    session_token: Optional[str] = Cookie(None),
):
    """Buy crypto with cash."""
    player = get_current_player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)

    from counties import buy_crypto_with_cash

    success, message = buy_crypto_with_cash(player.id, crypto_symbol, cash_amount)

    if success:
        return RedirectResponse(url=f"/exchange?msg={message.replace(' ', '+')}", status_code=303)
    else:
        return RedirectResponse(url=f"/exchange?error={message.replace(' ', '+')}", status_code=303)


@router.post("/api/exchange/sell")
async def api_exchange_sell(
    crypto_symbol: str = Form(...),
    amount: float = Form(...),
    session_token: Optional[str] = Cookie(None),
):
    """Sell crypto for cash."""
    player = get_current_player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)

    from counties import sell_crypto_for_cash

    success, message = sell_crypto_for_cash(player.id, crypto_symbol, amount)

    if success:
        return RedirectResponse(url=f"/exchange?msg={message.replace(' ', '+')}", status_code=303)
    else:
        return RedirectResponse(url=f"/exchange?error={message.replace(' ', '+')}", status_code=303)


@router.post("/api/exchange/swap")
async def api_exchange_swap(
    sell_symbol: str = Form(...),
    sell_amount: float = Form(...),
    buy_symbol: str = Form(...),
    session_token: Optional[str] = Cookie(None),
):
    """Swap one crypto for another."""
    player = get_current_player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)

    from counties import swap_crypto

    if sell_symbol == buy_symbol:
        return RedirectResponse(url="/exchange?error=Cannot+swap+a+crypto+for+itself", status_code=303)

    success, message = swap_crypto(player.id, sell_symbol, buy_symbol, sell_amount)

    if success:
        return RedirectResponse(url=f"/exchange?msg={message.replace(' ', '+')}", status_code=303)
    else:
        return RedirectResponse(url=f"/exchange?error={message.replace(' ', '+')}", status_code=303)


# ==========================
# GOVERNANCE VOTING PAGE
# ==========================
@router.get("/county/{county_id}/governance", response_class=HTMLResponse)
async def county_governance(
    county_id: int,
    session_token: Optional[str] = Cookie(None),
    msg: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
):
    """Intercounty Governance Voting dashboard."""
    player = get_current_player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)

    from counties import (
        get_county_by_id, is_player_in_county, calculate_crypto_price,
        CryptoWallet, GovernanceCycle, GovernanceProposal, GovernanceVote,
        GovernanceProposalType, GovernanceProposalStatus, GovernanceCycleStatus,
        get_current_governance_cycle, get_governance_proposals,
        get_governance_history,
        GOVERNANCE_VOTE_CYCLE_TICKS, GOVERNANCE_PROPOSAL_WINDOW_TICKS,
        GOVERNANCE_VOTING_WINDOW_TICKS,
    )
    from cities import get_db
    import app as app_module

    county = get_county_by_id(county_id)
    if not county:
        return RedirectResponse(url="/counties?error=County+not+found", status_code=303)

    is_member = is_player_in_county(player.id, county_id)
    crypto_price = calculate_crypto_price(county_id)
    current_tick = app_module.current_tick

    # Get player's crypto wallet
    db = get_db()
    wallet = db.query(CryptoWallet).filter(
        CryptoWallet.player_id == player.id,
        CryptoWallet.crypto_symbol == county.crypto_symbol,
    ).first()
    crypto_balance = wallet.balance if wallet else 0.0
    db.close()

    # Get current governance cycle
    cycle = get_current_governance_cycle(county_id, current_tick)

    alert_html = ""
    if msg:
        alert_html = f'<div class="alert alert-success">{msg}</div>'
    if error:
        alert_html = f'<div class="alert alert-error">{error}</div>'

    # Cycle status display
    cycle_html = ""
    proposals_html = ""
    submit_form_html = ""

    if cycle:
        # Phase indicator
        if cycle["phase"] == "proposal_phase":
            phase_badge = '<span class="phase-indicator phase-proposal">Proposal Phase</span>'
            ticks_remaining = cycle["proposal_phase_ends_tick"] - current_tick
            phase_desc = "Submit proposals for county governance decisions. Voting begins when this phase ends."
        elif cycle["phase"] == "voting_phase":
            phase_badge = '<span class="phase-indicator phase-voting">Voting Phase</span>'
            ticks_remaining = cycle["voting_phase_ends_tick"] - current_tick
            phase_desc = "Burn tokens to cast votes on active proposals. More tokens burned = more voting weight."
        else:
            phase_badge = '<span class="phase-indicator phase-completed">Completed</span>'
            ticks_remaining = 0
            phase_desc = "This cycle has completed. Results are final."

        # Convert ticks to human-readable time
        hours_remaining = (ticks_remaining * 5) / 3600
        days_remaining = hours_remaining / 24

        time_display = ""
        if days_remaining >= 1:
            time_display = f"{days_remaining:.1f} days"
        else:
            time_display = f"{hours_remaining:.1f} hours"

        # Get proposals for this cycle
        proposals = get_governance_proposals(county_id, cycle["id"])

        cycle_html = f'''
        <div class="governance-panel">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                <h2 style="color: #f59e0b;">Governance Cycle #{cycle["cycle_number"]}</h2>
                {phase_badge}
            </div>
            <p style="color: #94a3b8; margin-bottom: 16px;">{phase_desc}</p>

            <div class="cycle-info">
                <div class="cycle-stat">
                    <div class="cycle-stat-value">{time_display}</div>
                    <div class="cycle-stat-label">Time Remaining</div>
                </div>
                <div class="cycle-stat">
                    <div class="cycle-stat-value">{len(proposals)}</div>
                    <div class="cycle-stat-label">Proposals</div>
                </div>
                <div class="cycle-stat">
                    <div class="cycle-stat-value">{crypto_balance:.6f}</div>
                    <div class="cycle-stat-label">Your {county.crypto_symbol} Balance</div>
                </div>
            </div>
        </div>
        '''

        # Proposal submission form (only during proposal phase and for members with tokens)
        if cycle["phase"] == "proposal_phase" and is_member and crypto_balance > 0:
            proposal_type_options = ""
            for pt in GovernanceProposalType:
                label = pt.value.replace("_", " ").title()
                proposal_type_options += f'<option value="{pt.value}">{label}</option>'

            submit_form_html = f'''
            <div class="card">
                <h2>Submit a Proposal</h2>
                <p style="color: #94a3b8; margin-bottom: 16px;">
                    As a holder of <span class="badge badge-crypto">{county.crypto_symbol}</span>,
                    you can submit governance proposals for the county to vote on.
                </p>
                <form action="/api/county/governance/propose" method="post">
                    <input type="hidden" name="county_id" value="{county_id}">
                    <div class="form-group">
                        <label>Proposal Type</label>
                        <select name="proposal_type" required>
                            <option value="">-- Select Type --</option>
                            {proposal_type_options}
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Title</label>
                        <input type="text" name="title" required placeholder="Brief title for your proposal" maxlength="100">
                    </div>
                    <div class="form-group">
                        <label>Description</label>
                        <input type="text" name="description" required placeholder="Detailed description of the proposal and its impact" maxlength="500">
                    </div>
                    <button type="submit" class="btn btn-governance">Submit Proposal</button>
                </form>
            </div>
            '''
        elif cycle["phase"] == "proposal_phase" and is_member and crypto_balance <= 0:
            submit_form_html = f'''
            <div class="card">
                <h2>Submit a Proposal</h2>
                <div class="alert alert-info">
                    You need to hold <span class="badge badge-crypto">{county.crypto_symbol}</span> to submit proposals.
                    Mine some through the <a href="/county/{county_id}/mining" class="nav-link">Mining Node</a>
                    or buy on the <a href="/exchange" class="nav-link">Crypto Exchange</a>.
                </div>
            </div>
            '''

        # Proposals list
        if proposals:
            proposals_html = '<div class="card"><h2>Proposals</h2>'
            for p in proposals:
                # Status badge
                if p["status"] == GovernanceProposalStatus.PENDING:
                    status_badge = '<span class="badge badge-warning">Pending Vote</span>'
                elif p["status"] == GovernanceProposalStatus.ACTIVE:
                    status_badge = '<span class="badge badge-success">Voting Open</span>'
                elif p["status"] == GovernanceProposalStatus.PASSED:
                    status_badge = '<span class="badge badge-success">Passed</span>'
                elif p["status"] == GovernanceProposalStatus.FAILED:
                    status_badge = '<span class="badge" style="background:#991b1b;color:#fca5a5;">Failed</span>'
                else:
                    status_badge = f'<span class="badge badge-info">{p["status"]}</span>'

                # Vote bar
                vote_bar_html = ""
                if p["total_votes"] > 0:
                    vote_bar_html = f'''
                    <div class="vote-bar">
                        <div class="vote-bar-yes" style="width: {p["yes_percent"]:.1f}%;">
                            {"YES " + f'{p["yes_percent"]:.1f}%' if p["yes_percent"] > 15 else ""}
                        </div>
                        <div class="vote-bar-no" style="width: {p["no_percent"]:.1f}%;">
                            {"NO " + f'{p["no_percent"]:.1f}%' if p["no_percent"] > 15 else ""}
                        </div>
                    </div>
                    <div style="display:flex; justify-content:space-between; font-size:12px; color:#94a3b8;">
                        <span>YES: {p["yes_token_votes"]:.6f} {county.crypto_symbol}</span>
                        <span>Total: {p["total_votes"]:.6f} burned</span>
                        <span>NO: {p["no_token_votes"]:.6f} {county.crypto_symbol}</span>
                    </div>
                    '''
                elif p["status"] in (GovernanceProposalStatus.ACTIVE, GovernanceProposalStatus.PENDING):
                    vote_bar_html = '<p style="color: #64748b; font-size: 13px;">No votes cast yet.</p>'

                # Voting form (only during voting phase, for members with tokens)
                vote_form_html = ""
                if (cycle["phase"] == "voting_phase" and
                    p["status"] == GovernanceProposalStatus.ACTIVE and
                    is_member and crypto_balance > 0):
                    vote_form_html = f'''
                    <div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid #1e293b;">
                        <div style="display: flex; gap: 8px;">
                            <form action="/api/county/governance/vote" method="post" style="flex: 1; display: flex; gap: 8px;">
                                <input type="hidden" name="proposal_id" value="{p["id"]}">
                                <input type="hidden" name="vote" value="yes">
                                <input type="number" name="tokens_to_burn" min="0.000001" step="0.000001"
                                       max="{crypto_balance}" placeholder="Tokens to burn"
                                       style="flex:1; padding:8px; background:#0b1220; border:1px solid #1e293b; border-radius:6px; color:#e5e7eb; font-size:13px;" required>
                                <button type="submit" class="btn btn-vote-yes btn-sm">Vote YES</button>
                            </form>
                            <form action="/api/county/governance/vote" method="post" style="display: flex; gap: 8px;">
                                <input type="hidden" name="proposal_id" value="{p["id"]}">
                                <input type="hidden" name="vote" value="no">
                                <input type="number" name="tokens_to_burn" min="0.000001" step="0.000001"
                                       max="{crypto_balance}" placeholder="Tokens to burn"
                                       style="width:140px; padding:8px; background:#0b1220; border:1px solid #1e293b; border-radius:6px; color:#e5e7eb; font-size:13px;" required>
                                <button type="submit" class="btn btn-vote-no btn-sm">Vote NO</button>
                            </form>
                        </div>
                        <p style="font-size: 11px; color: #64748b; margin-top: 6px;">
                            Tokens are permanently burned when voting. You can vote multiple times to add more weight.
                            Balance: {crypto_balance:.6f} {county.crypto_symbol}
                        </p>
                    </div>
                    '''

                proposals_html += f'''
                <div class="proposal-card">
                    <div class="proposal-header">
                        <div>
                            <span class="proposal-type">{p["proposal_type"].replace("_", " ")}</span>
                            <h3 style="color: #e5e7eb; margin-top: 6px;">{p["title"]}</h3>
                        </div>
                        {status_badge}
                    </div>
                    <p style="color: #94a3b8; font-size: 14px; margin-bottom: 8px;">{p["description"]}</p>
                    <p style="color: #64748b; font-size: 12px;">Proposed by: {p["proposer_name"]}</p>
                    {vote_bar_html}
                    {vote_form_html}
                </div>
                '''
            proposals_html += '</div>'
        else:
            proposals_html = '''
            <div class="card">
                <h2>Proposals</h2>
                <p style="color: #64748b;">No proposals submitted for this cycle yet.</p>
            </div>
            '''
    else:
        cycle_html = '''
        <div class="governance-panel">
            <h2 style="color: #f59e0b;">No Active Governance Cycle</h2>
            <p style="color: #94a3b8;">
                A new governance cycle will begin automatically. Cycles run every 5 days:
                3 days for proposals, 2 days for voting.
            </p>
        </div>
        '''

    # Governance history
    history = get_governance_history(county_id)
    history_html = ""
    if history:
        history_html = '''
        <div class="card">
            <h2>Past Cycles</h2>
            <table class="table">
                <thead><tr><th>Cycle</th><th>Proposals</th><th>Passed</th><th>Failed</th><th>Date</th></tr></thead>
                <tbody>
        '''
        for h in history:
            history_html += f'''
            <tr>
                <td>Cycle #{h["cycle_number"]}</td>
                <td>{h["total_proposals"]}</td>
                <td style="color: #4ade80;">{h["passed"]}</td>
                <td style="color: #f87171;">{h["failed"]}</td>
                <td>{h["created_at"].strftime("%Y-%m-%d") if h["created_at"] else "N/A"}</td>
            </tr>
            '''
        history_html += '</tbody></table></div>'

    # Non-member notice
    non_member_html = ""
    if not is_member:
        non_member_html = '''
        <div class="alert alert-info">
            You are not a member of this county. Only county members who hold the county's
            cryptocurrency can submit proposals and vote.
        </div>
        '''

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Governance · {county.name} · Wadsworth</title>
        {COUNTY_STYLES}
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Governance Voting</h1>
                <div>
                    <span style="color: #94a3b8;">{county.name}</span>
                    <a href="/county/{county_id}" class="nav-link">County</a>
                    <a href="/county/{county_id}/mining" class="nav-link">Mining</a>
                    <a href="/exchange" class="nav-link">Exchange</a>
                    <a href="/" class="nav-link">Dashboard</a>
                </div>
            </div>

            {alert_html}
            {non_member_html}

            <div class="card" style="margin-bottom: 16px;">
                <h2>How Governance Works</h2>
                <p style="color: #94a3b8; font-size: 14px; margin-bottom: 12px;">
                    Every 5 days, an intercounty governance vote takes place for the
                    <span class="badge badge-crypto">{county.crypto_symbol}</span> blockchain.
                    County members who hold {county.crypto_symbol} can participate.
                </p>
                <div class="grid grid-3" style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:16px;">
                    <div>
                        <h3 style="color: #f59e0b;">1. Proposal Phase (3 days)</h3>
                        <p style="color: #94a3b8; font-size: 13px;">
                            County members who hold {county.crypto_symbol} submit proposals for
                            protocol upgrades, fee adjustments, mining parameters, county policies, and more.
                        </p>
                    </div>
                    <div>
                        <h3 style="color: #f59e0b;">2. Voting Phase (2 days)</h3>
                        <p style="color: #94a3b8; font-size: 13px;">
                            Members burn {county.crypto_symbol} tokens to cast votes.
                            More tokens burned = more voting weight.
                            Tokens are permanently destroyed.
                        </p>
                    </div>
                    <div>
                        <h3 style="color: #f59e0b;">3. Results</h3>
                        <p style="color: #94a3b8; font-size: 13px;">
                            Proposals pass if YES token votes exceed NO token votes.
                            Only county members (members of cities in this county) can participate.
                        </p>
                    </div>
                </div>
            </div>

            {cycle_html}
            {submit_form_html}
            {proposals_html}
            {history_html}
        </div>
    </body>
    </html>
    """


# ==========================
# GOVERNANCE API ENDPOINTS
# ==========================
@router.post("/api/county/governance/propose")
async def api_governance_propose(
    county_id: int = Form(...),
    proposal_type: str = Form(...),
    title: str = Form(...),
    description: str = Form(...),
    session_token: Optional[str] = Cookie(None),
):
    """Submit a governance proposal."""
    player = get_current_player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)

    from counties import submit_governance_proposal
    import app as app_module

    proposal, message = submit_governance_proposal(
        player_id=player.id,
        county_id=county_id,
        proposal_type=proposal_type,
        title=title,
        description=description,
        current_tick=app_module.current_tick,
    )

    if proposal:
        return RedirectResponse(
            url=f"/county/{county_id}/governance?msg={message.replace(' ', '+')}",
            status_code=303,
        )
    else:
        return RedirectResponse(
            url=f"/county/{county_id}/governance?error={message.replace(' ', '+')}",
            status_code=303,
        )


@router.post("/api/county/governance/vote")
async def api_governance_vote(
    proposal_id: int = Form(...),
    vote: str = Form(...),
    tokens_to_burn: float = Form(...),
    session_token: Optional[str] = Cookie(None),
):
    """Cast a governance vote by burning tokens."""
    player = get_current_player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)

    from counties import cast_governance_vote, GovernanceProposal, get_db
    import app as app_module

    success, message = cast_governance_vote(
        player_id=player.id,
        proposal_id=proposal_id,
        vote=vote,
        tokens_to_burn=tokens_to_burn,
        current_tick=app_module.current_tick,
    )

    # Get county_id from proposal for redirect
    db = get_db()
    proposal = db.query(GovernanceProposal).filter(GovernanceProposal.id == proposal_id).first()
    county_id = proposal.county_id if proposal else 0
    db.close()

    if success:
        return RedirectResponse(
            url=f"/county/{county_id}/governance?msg={message.replace(' ', '+')}",
            status_code=303,
        )
    else:
        return RedirectResponse(
            url=f"/county/{county_id}/governance?error={message.replace(' ', '+')}",
            status_code=303,
        )


# ==========================
# PUBLIC API
# ==========================
__all__ = ['router']
