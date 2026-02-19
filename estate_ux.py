"""
estate_ux.py - Death Dashboard & Estate Management UI

Provides:
- Death Dashboard (death certificate aesthetic)
- Account deletion confirmation screen
- Heir selection interface with player search
- Deceased players memorial wall with stats
- Inheritance installment status
- Estate information display
"""

from typing import Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Cookie, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse

router = APIRouter()

# ==========================
# AUTHENTICATION HELPER
# ==========================

def require_auth(session_token: Optional[str] = Cookie(None)):
    """Check if user is authenticated."""
    try:
        import auth
        db = auth.get_db()
        player = auth.get_player_from_session(db, session_token)
        db.close()
        if not player:
            return RedirectResponse(url="/login", status_code=303)
        return player
    except Exception as e:
        print(f"[Estate UX] Auth check failed: {e}")
        return RedirectResponse(url="/login", status_code=303)


# ==========================
# HTML SHELL - DEATH CERTIFICATE AESTHETIC
# ==========================

def death_shell(title: str, body: str, balance: float = 0.0, player_name: str = "") -> str:
    """Dark, solemn shell with death certificate aesthetic."""
    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>{title} - Wadsworth Estate</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            background: #020617;
            color: #e5e7eb;
            font-family: 'JetBrains Mono', 'Courier New', monospace;
            margin: 0;
            padding: 0;
            font-size: 14px;
        }}
        a {{ color: #94a3b8; text-decoration: none; }}
        a:hover {{ text-decoration: underline; color: #e5e7eb; }}

        .header {{
            border-bottom: 1px solid #1a1a2e;
            padding: 12px 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: #0a0a14;
        }}
        .brand {{
            font-weight: bold;
            color: #475569;
            font-size: 1.1rem;
            letter-spacing: 0.05em;
        }}
        .header-right {{
            display: flex;
            align-items: center;
            gap: 16px;
        }}
        .balance {{ color: #22c55e; font-weight: 600; }}

        .nav {{
            background: #0a0a14;
            border-bottom: 1px solid #1a1a2e;
            padding: 8px 16px;
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }}
        .nav a {{
            padding: 6px 12px;
            border-radius: 4px;
            background: #111827;
            color: #64748b;
            font-size: 0.85rem;
        }}
        .nav a:hover, .nav a.active {{
            background: #475569;
            color: #e5e7eb;
            text-decoration: none;
        }}

        .container {{
            max-width: 1100px;
            margin: 0 auto;
            padding: 20px 16px;
        }}

        .page-title {{
            font-size: 1.5rem;
            font-weight: 700;
            margin-bottom: 4px;
            color: #94a3b8;
            letter-spacing: 0.02em;
        }}
        .page-subtitle {{
            color: #475569;
            font-size: 0.85rem;
            margin-bottom: 24px;
            font-style: italic;
        }}

        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 16px;
        }}

        /* Death Certificate Card */
        .cert-card {{
            background: linear-gradient(135deg, #0a0a14 0%, #111827 100%);
            border: 1px solid #1e293b;
            border-radius: 8px;
            padding: 24px;
            position: relative;
        }}
        .cert-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(90deg, #475569, #1e293b, #475569);
            border-radius: 8px 8px 0 0;
        }}
        .cert-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }}
        .cert-title {{
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: #64748b;
        }}
        .cert-badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.7rem;
            font-weight: 600;
        }}
        .cert-badge-idle {{ background: #78350f; color: #fbbf24; }}
        .cert-badge-voluntary {{ background: #1e1b4b; color: #818cf8; }}

        .stat-row {{
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #111827;
        }}
        .stat-row:last-child {{ border-bottom: none; }}
        .stat-label {{ color: #64748b; }}
        .stat-value {{ color: #e5e7eb; font-weight: 500; }}
        .stat-value.positive {{ color: #22c55e; }}
        .stat-value.negative {{ color: #ef4444; }}

        /* Rank badges */
        .rank-1 {{ color: #fbbf24; font-weight: 700; }}
        .rank-2 {{ color: #d1d5db; font-weight: 700; }}
        .rank-3 {{ color: #d97706; font-weight: 700; }}

        /* Table */
        .table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.85rem;
        }}
        .table th {{
            text-align: left;
            padding: 12px 8px;
            border-bottom: 2px solid #1e293b;
            color: #64748b;
            font-weight: 500;
        }}
        .table td {{
            padding: 10px 8px;
            border-bottom: 1px solid #111827;
        }}
        .table tr:hover {{ background: #0f172a; }}

        /* Buttons */
        .btn {{
            border: none;
            padding: 8px 16px;
            cursor: pointer;
            font-size: 0.85rem;
            border-radius: 4px;
            font-family: inherit;
            font-weight: 500;
            text-decoration: none;
            display: inline-block;
        }}
        .btn-danger {{
            background: #7f1d1d;
            color: #fca5a5;
            border: 1px solid #991b1b;
        }}
        .btn-danger:hover {{ background: #991b1b; text-decoration: none; }}
        .btn-secondary {{
            background: #1e293b;
            color: #94a3b8;
        }}
        .btn-secondary:hover {{ background: #334155; text-decoration: none; }}
        .btn-primary {{
            background: #1e3a5f;
            color: #93c5fd;
            border: 1px solid #1e40af;
        }}
        .btn-primary:hover {{ background: #1e40af; text-decoration: none; }}

        /* Search box */
        .search-box {{
            width: 100%;
            padding: 10px 14px;
            background: #111827;
            border: 1px solid #1e293b;
            border-radius: 6px;
            color: #e5e7eb;
            font-size: 0.9rem;
            font-family: inherit;
            margin-bottom: 16px;
        }}
        .search-box:focus {{
            outline: none;
            border-color: #475569;
        }}

        /* Heir slot */
        .heir-slot {{
            background: #0f172a;
            border: 1px solid #1e293b;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 12px;
        }}
        .heir-slot-empty {{
            border-style: dashed;
            text-align: center;
            color: #475569;
        }}
        .heir-number {{
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: #64748b;
            margin-bottom: 8px;
        }}

        /* Delete confirmation */
        .delete-zone {{
            border: 2px solid #7f1d1d;
            border-radius: 8px;
            padding: 24px;
            background: linear-gradient(135deg, #0a0a14 0%, #1a0a0a 100%);
            margin-top: 24px;
        }}
        .delete-zone h3 {{
            color: #ef4444;
            margin-bottom: 12px;
        }}

        /* Inheritance alert */
        .inheritance-alert {{
            background: #1a1a2e;
            border: 1px solid #312e81;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 16px;
        }}

        /* Ornamental divider */
        .divider {{
            text-align: center;
            color: #1e293b;
            margin: 24px 0;
            font-size: 0.8rem;
            letter-spacing: 0.5em;
        }}

        /* Player list for heir selection */
        .player-list-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 12px;
            border-bottom: 1px solid #111827;
            transition: background 0.15s;
        }}
        .player-list-item:hover {{ background: #0f172a; }}
        .player-name {{ color: #e5e7eb; font-weight: 500; }}
        .player-worth {{ color: #64748b; font-size: 0.8rem; }}

        @media (max-width: 640px) {{
            .grid {{ grid-template-columns: 1fr; }}
            .header {{ flex-direction: column; gap: 8px; text-align: center; }}
            .table {{ font-size: 0.75rem; }}
            .table th, .table td {{ padding: 8px 4px; }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="brand">WADSWORTH ESTATE REGISTRY</div>
        <div class="header-right">
            <span style="color: #64748b;">{player_name}</span>
            <span class="balance">${balance:,.2f}</span>
            <a href="/" style="color: #64748b;">Dashboard</a>
        </div>
    </div>

    <div class="nav">
        <a href="/estate">Overview</a>
        <a href="/estate/heirs">Heirs</a>
        <a href="/estate/deceased">Deceased</a>
        <a href="/estate/delete-account">Leave Game</a>
    </div>

    <div class="container">
        {body}
    </div>
</body>
</html>
"""


# ==========================
# ROUTES - ESTATE OVERVIEW
# ==========================

@router.get("/estate", response_class=HTMLResponse)
async def estate_overview(session_token: Optional[str] = Cookie(None)):
    """Estate overview dashboard - death information and heir management."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player

    from estate import (
        get_player_heirs, get_heir_installments, calculate_estate_value,
        calculate_total_debts, get_all_deceased, DEATH_TAX_RATE,
        DEBT_PAYMENT_PERCENTAGE, IDLE_DAYS_BEFORE_DEATH
    )
    from auth import get_db, Player

    db = get_db()

    # Get heir info
    heirs = db.query(
        __import__('estate').HeirDesignation
    ).filter(
        __import__('estate').HeirDesignation.player_id == player.id
    ).order_by(__import__('estate').HeirDesignation.priority.asc()).all()

    heir_names = {}
    for h in heirs:
        hp = db.query(Player).filter(Player.id == h.heir_player_id).first()
        if hp:
            heir_names[h.priority] = hp.business_name

    # Get pending installments (as heir)
    installments = db.query(
        __import__('estate').InheritanceInstallment
    ).filter(
        __import__('estate').InheritanceInstallment.heir_player_id == player.id,
        __import__('estate').InheritanceInstallment.completed == False
    ).all()

    # Get estate valuation
    estate = calculate_estate_value(player.id, db)
    debts = calculate_total_debts(player.id, db)

    # Deceased count
    deceased_count = db.query(__import__('estate').DeceasedPlayer).count()

    db.close()

    # Build installment alerts
    installment_html = ""
    if installments:
        for inst in installments:
            installment_html += f"""
            <div class="inheritance-alert">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div style="color: #818cf8; font-weight: 600;">Death Tax Installment Due</div>
                        <div style="color: #64748b; font-size: 0.8rem; margin-top: 4px;">
                            ${inst.installment_amount:,.2f} per installment | {inst.installments_remaining} remaining
                        </div>
                    </div>
                    <div style="text-align: right;">
                        <div style="color: #e5e7eb;">${inst.total_tax_paid:,.2f} / ${inst.total_tax_owed:,.2f}</div>
                        <div style="color: #64748b; font-size: 0.75rem;">paid</div>
                    </div>
                </div>
            </div>
            """

    # Build heir summary
    heir_summary = ""
    for i in range(1, 4):
        label = ["Primary", "Secondary", "Tertiary"][i-1]
        name = heir_names.get(i, "Not Designated")
        style = "color: #e5e7eb;" if i in heir_names else "color: #475569; font-style: italic;"
        heir_summary += f"""
        <div class="stat-row">
            <span class="stat-label">{label} Heir</span>
            <span class="stat-value" style="{style}">{name}</span>
        </div>
        """

    body = f"""
    <h1 class="page-title">Estate & Succession</h1>
    <p class="page-subtitle">Manage your estate plan, designate heirs, and view the registry of the deceased.</p>

    {installment_html}

    <div class="grid">
        <div class="cert-card">
            <div class="cert-header">
                <span class="cert-title">Your Estate Value</span>
            </div>
            <div style="font-size: 1.75rem; font-weight: 700; color: #e5e7eb; margin-bottom: 16px;">
                ${estate['total']:,.2f}
            </div>
            <div class="stat-row"><span class="stat-label">Cash</span><span class="stat-value">${estate['cash']:,.2f}</span></div>
            <div class="stat-row"><span class="stat-label">Inventory</span><span class="stat-value">${estate['inventory']:,.2f}</span></div>
            <div class="stat-row"><span class="stat-label">Land ({estate['land_count']})</span><span class="stat-value">${estate['land']:,.2f}</span></div>
            <div class="stat-row"><span class="stat-label">Businesses ({estate['business_count']})</span><span class="stat-value">${estate['businesses']:,.2f}</span></div>
            <div class="stat-row"><span class="stat-label">Shares</span><span class="stat-value">${estate['shares']:,.2f}</span></div>
            <div class="stat-row"><span class="stat-label">Districts ({estate['district_count']})</span><span class="stat-value">${estate['districts']:,.2f}</span></div>
            <div class="divider">- - -</div>
            <div class="stat-row"><span class="stat-label">Outstanding Debts</span><span class="stat-value negative">${debts:,.2f}</span></div>
        </div>

        <div>
            <div class="cert-card" style="margin-bottom: 16px;">
                <div class="cert-header">
                    <span class="cert-title">Designated Heirs</span>
                    <a href="/estate/heirs" class="btn btn-secondary" style="font-size: 0.75rem;">Manage</a>
                </div>
                {heir_summary}
            </div>

            <div class="cert-card">
                <div class="cert-header">
                    <span class="cert-title">What Happens at Death</span>
                </div>
                <div style="color: #64748b; font-size: 0.8rem; line-height: 1.6;">
                    <p>When a player account is deleted (voluntarily or after {IDLE_DAYS_BEFORE_DEATH} days idle):</p>
                    <ol style="padding-left: 16px; margin-top: 8px;">
                        <li>Government seizes all assets (land, businesses, inventory, shares, districts)</li>
                        <li>Assets are liquidated at 85% market value</li>
                        <li>{int(DEBT_PAYMENT_PERCENTAGE*100)}% of outstanding debts are settled</li>
                        <li>Remaining proceeds split equally among designated heirs</li>
                        <li>Heirs pay {int(DEATH_TAX_RATE*100)}% death tax in 7 daily installments</li>
                        <li>If no heirs exist, government keeps everything</li>
                    </ol>
                </div>
            </div>
        </div>
    </div>

    <div style="margin-top: 24px; display: flex; gap: 12px; flex-wrap: wrap;">
        <a href="/estate/deceased" class="btn btn-secondary">
            View Deceased Registry ({deceased_count})
        </a>
        <a href="/estate/delete-account" class="btn btn-danger">
            Delete Account
        </a>
    </div>
    """

    return HTMLResponse(death_shell("Estate", body, player.cash_balance, player.business_name))


# ==========================
# ROUTES - HEIR MANAGEMENT
# ==========================

@router.get("/estate/heirs", response_class=HTMLResponse)
async def heir_management(
    session_token: Optional[str] = Cookie(None),
    search: str = Query("")
):
    """Heir selection screen with player search."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player

    from auth import get_db, Player
    from estate import HeirDesignation
    from stats_ux import PlayerStats

    db = get_db()

    # Get current heirs
    heirs = db.query(HeirDesignation).filter(
        HeirDesignation.player_id == player.id
    ).order_by(HeirDesignation.priority.asc()).all()

    heir_map = {}
    for h in heirs:
        hp = db.query(Player).filter(Player.id == h.heir_player_id).first()
        if hp:
            heir_map[h.priority] = {"id": hp.id, "name": hp.business_name}

    # Build heir slots
    slots_html = ""
    for i in range(1, 4):
        label = ["Primary", "Secondary", "Tertiary"][i-1]
        if i in heir_map:
            heir = heir_map[i]
            slots_html += f"""
            <div class="heir-slot">
                <div class="heir-number">{label} Heir</div>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span class="player-name">{heir['name']}</span>
                    <form action="/api/estate/remove-heir" method="post" style="margin: 0;">
                        <input type="hidden" name="priority" value="{i}">
                        <button type="submit" class="btn btn-danger" style="font-size: 0.75rem; padding: 4px 10px;">Remove</button>
                    </form>
                </div>
            </div>
            """
        else:
            slots_html += f"""
            <div class="heir-slot heir-slot-empty">
                <div class="heir-number">{label} Heir</div>
                <div style="padding: 8px 0;">No heir designated</div>
            </div>
            """

    # Get available players for selection
    query = db.query(Player).filter(
        Player.id != player.id,
        Player.id > 0
    )

    if search:
        query = query.filter(Player.business_name.ilike(f"%{search}%"))

    available_players = query.order_by(Player.business_name.asc()).limit(50).all()

    # Build player list
    player_list_html = ""
    existing_heir_ids = [h.get("id") for h in heir_map.values()]
    available_slots = [i for i in range(1, 4) if i not in heir_map]

    for p in available_players:
        if p.id in existing_heir_ids:
            continue

        # Get net worth
        stats = db.query(PlayerStats).filter(PlayerStats.player_id == p.id).first()
        net_worth = stats.total_net_worth if stats else 0.0

        if available_slots:
            assign_buttons = ""
            for slot in available_slots:
                label = ["1st", "2nd", "3rd"][slot-1]
                assign_buttons += f"""
                <form action="/api/estate/set-heir" method="post" style="display: inline; margin: 0;">
                    <input type="hidden" name="heir_player_id" value="{p.id}">
                    <input type="hidden" name="priority" value="{slot}">
                    <button type="submit" class="btn btn-primary" style="font-size: 0.7rem; padding: 3px 8px;">{label}</button>
                </form>
                """
        else:
            assign_buttons = '<span style="color: #475569; font-size: 0.75rem;">All slots filled</span>'

        player_list_html += f"""
        <div class="player-list-item">
            <div>
                <span class="player-name">{p.business_name}</span>
                <span class="player-worth"> - ${net_worth:,.0f} net worth</span>
            </div>
            <div style="display: flex; gap: 6px;">
                {assign_buttons}
            </div>
        </div>
        """

    db.close()

    body = f"""
    <h1 class="page-title">Heir Designation</h1>
    <p class="page-subtitle">Designate up to 3 heirs who will inherit your estate upon account deletion.</p>

    <div class="grid">
        <div>
            <div class="cert-card">
                <div class="cert-header">
                    <span class="cert-title">Your Heirs</span>
                </div>
                {slots_html}
                <div style="margin-top: 12px; color: #475569; font-size: 0.75rem;">
                    Heirs receive equal shares of your liquidated estate minus debts and death tax.
                </div>
            </div>
        </div>

        <div>
            <div class="cert-card">
                <div class="cert-header">
                    <span class="cert-title">Select Players</span>
                </div>
                <form method="get" action="/estate/heirs" style="margin: 0;">
                    <input type="text" name="search" value="{search}" class="search-box"
                           placeholder="Search players by name..."
                           style="margin-bottom: 12px;">
                </form>
                <div style="max-height: 400px; overflow-y: auto;">
                    {player_list_html if player_list_html else '<div style="padding: 20px; text-align: center; color: #475569;">No players found</div>'}
                </div>
            </div>
        </div>
    </div>

    <div style="margin-top: 16px;">
        <a href="/estate" class="btn btn-secondary">Back to Estate</a>
    </div>
    """

    return HTMLResponse(death_shell("Heirs", body, player.cash_balance, player.business_name))


# ==========================
# ROUTES - DECEASED REGISTRY
# ==========================

@router.get("/estate/deceased", response_class=HTMLResponse)
async def deceased_registry(session_token: Optional[str] = Cookie(None)):
    """Memorial wall - list of all deceased players with death certificates."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player

    from estate import DeceasedPlayer
    from auth import get_db

    db = get_db()
    deceased = db.query(DeceasedPlayer).order_by(
        DeceasedPlayer.date_of_death.desc()
    ).all()
    db.close()

    if not deceased:
        body = """
        <h1 class="page-title">Deceased Registry</h1>
        <p class="page-subtitle">A record of all departed players and their legacies.</p>
        <div class="cert-card" style="text-align: center; padding: 40px;">
            <div style="color: #475569; font-size: 1.1rem;">No deceased players yet.</div>
            <div style="color: #334155; font-size: 0.85rem; margin-top: 8px;">
                The registry will be populated as players depart the simulation.
            </div>
        </div>
        <div style="margin-top: 16px;">
            <a href="/estate" class="btn btn-secondary">Back to Estate</a>
        </div>
        """
        return HTMLResponse(death_shell("Deceased", body, player.cash_balance, player.business_name))

    # Build death certificate cards
    cards_html = ""
    for d in deceased:
        cause_badge = (
            '<span class="cert-badge cert-badge-voluntary">VOLUNTARY</span>'
            if d.cause_of_death == "voluntary"
            else '<span class="cert-badge cert-badge-idle">IDLE TIMEOUT</span>'
        )

        rank_class = ""
        rank_display = f"#{d.highest_leaderboard_rank}" if d.highest_leaderboard_rank else "Unranked"
        if d.highest_leaderboard_rank == 1:
            rank_class = "rank-1"
        elif d.highest_leaderboard_rank == 2:
            rank_class = "rank-2"
        elif d.highest_leaderboard_rank == 3:
            rank_class = "rank-3"

        date_str = d.date_of_death.strftime("%Y-%m-%d %H:%M") if d.date_of_death else "Unknown"
        created_str = d.account_created.strftime("%Y-%m-%d") if d.account_created else "Unknown"
        last_login_str = d.last_login.strftime("%Y-%m-%d %H:%M") if d.last_login else "Unknown"

        heir_info = ""
        if d.government_took_all:
            heir_info = '<span style="color: #64748b;">Government claimed all</span>'
        elif d.total_inherited > 0:
            heir_info = f'<span style="color: #22c55e;">${d.total_inherited:,.2f} distributed</span>'

        cards_html += f"""
        <div class="cert-card">
            <div class="cert-header">
                <span style="color: #e5e7eb; font-weight: 700; font-size: 1.1rem;">{d.business_name}</span>
                {cause_badge}
            </div>

            <div class="divider">CERTIFICATE OF DISSOLUTION</div>

            <div class="stat-row">
                <span class="stat-label">Date of Death</span>
                <span class="stat-value">{date_str}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Account Created</span>
                <span class="stat-value">{created_str}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Last Active</span>
                <span class="stat-value">{last_login_str}</span>
            </div>

            <div class="divider">- - -</div>

            <div class="stat-row">
                <span class="stat-label">Final Net Worth</span>
                <span class="stat-value">${d.final_net_worth:,.2f}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Final Cash</span>
                <span class="stat-value">${d.final_cash:,.2f}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Highest Rank</span>
                <span class="stat-value {rank_class}">{rank_display}</span>
            </div>

            <div class="divider">- - -</div>

            <div class="stat-row">
                <span class="stat-label">Land Plots</span>
                <span class="stat-value">{d.final_land_count}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Businesses</span>
                <span class="stat-value">{d.final_business_count}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Districts</span>
                <span class="stat-value">{d.final_district_count}</span>
            </div>

            <div class="divider">ESTATE SETTLEMENT</div>

            <div class="stat-row">
                <span class="stat-label">Assets Liquidated</span>
                <span class="stat-value">${d.total_assets_liquidated:,.2f}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Debts Settled</span>
                <span class="stat-value negative">${d.total_debts_settled:,.2f}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Inheritance</span>
                <span class="stat-value">{heir_info}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Death Tax Collected</span>
                <span class="stat-value">${d.total_death_tax:,.2f}</span>
            </div>
        </div>
        """

    body = f"""
    <h1 class="page-title">Deceased Registry</h1>
    <p class="page-subtitle">A record of all departed players and their legacies.</p>

    <div style="margin-bottom: 16px; color: #475569; font-size: 0.85rem;">
        {len(deceased)} player{"s" if len(deceased) != 1 else ""} in the registry
    </div>

    <div class="grid">
        {cards_html}
    </div>

    <div style="margin-top: 16px;">
        <a href="/estate" class="btn btn-secondary">Back to Estate</a>
    </div>
    """

    return HTMLResponse(death_shell("Deceased", body, player.cash_balance, player.business_name))


# ==========================
# ROUTES - DELETE ACCOUNT
# ==========================

@router.get("/estate/delete-account", response_class=HTMLResponse)
async def delete_account_page(session_token: Optional[str] = Cookie(None)):
    """Account deletion confirmation page."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player

    from estate import (
        calculate_estate_value, calculate_total_debts, get_player_heirs,
        DEATH_TAX_RATE, DEBT_PAYMENT_PERCENTAGE, IDLE_DAYS_BEFORE_DEATH,
        LIQUIDATION_DISCOUNT, HeirDesignation
    )
    from auth import get_db, Player

    db = get_db()
    estate = calculate_estate_value(player.id, db)
    debts = calculate_total_debts(player.id, db)

    heirs = db.query(HeirDesignation).filter(
        HeirDesignation.player_id == player.id
    ).order_by(HeirDesignation.priority.asc()).all()

    heir_names = []
    for h in heirs:
        hp = db.query(Player).filter(Player.id == h.heir_player_id).first()
        if hp:
            heir_names.append(hp.business_name)

    db.close()

    # Calculate projections
    projected_liquidation = estate["total"] * LIQUIDATION_DISCOUNT
    projected_debt_payment = min(debts * DEBT_PAYMENT_PERCENTAGE, projected_liquidation * 0.5)
    projected_remainder = max(0, projected_liquidation - projected_debt_payment)

    if heir_names:
        per_heir = projected_remainder / len(heir_names)
        per_heir_tax = per_heir * DEATH_TAX_RATE
        per_heir_net = per_heir - per_heir_tax
    else:
        per_heir = 0
        per_heir_tax = 0
        per_heir_net = 0

    # Build heir projection
    heir_projection_html = ""
    if heir_names:
        for name in heir_names:
            heir_projection_html += f"""
            <div class="stat-row">
                <span class="stat-label">{name}</span>
                <span class="stat-value positive">${per_heir_net:,.2f} <span style="color: #64748b; font-size: 0.75rem;">(tax: ${per_heir_tax:,.2f})</span></span>
            </div>
            """
    else:
        heir_projection_html = """
        <div class="stat-row">
            <span class="stat-label">Government</span>
            <span class="stat-value">Takes all remaining proceeds</span>
        </div>
        <div style="color: #fbbf24; font-size: 0.8rem; margin-top: 8px;">
            You have no heirs designated. <a href="/estate/heirs" style="color: #818cf8;">Designate heirs</a> to pass on your wealth.
        </div>
        """

    body = f"""
    <h1 class="page-title">Account Deletion</h1>
    <p class="page-subtitle">Permanently leave the simulation. This action cannot be undone.</p>

    <div class="grid">
        <div class="cert-card">
            <div class="cert-header">
                <span class="cert-title">Estate Liquidation Projection</span>
            </div>

            <div class="stat-row">
                <span class="stat-label">Total Estate Value</span>
                <span class="stat-value">${estate['total']:,.2f}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Liquidation Value (85%)</span>
                <span class="stat-value">${projected_liquidation:,.2f}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Debt Settlement ({int(DEBT_PAYMENT_PERCENTAGE*100)}%)</span>
                <span class="stat-value negative">-${projected_debt_payment:,.2f}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label" style="font-weight: 600;">Net Proceeds</span>
                <span class="stat-value" style="font-weight: 600;">${projected_remainder:,.2f}</span>
            </div>

            <div class="divider">HEIR DISTRIBUTION</div>

            {heir_projection_html}
        </div>

        <div class="cert-card">
            <div class="cert-header">
                <span class="cert-title">Process Overview</span>
            </div>
            <div style="color: #94a3b8; font-size: 0.85rem; line-height: 1.8;">
                <div style="margin-bottom: 12px;">
                    <span style="color: #475569;">1.</span> All assets are seized by the government<br>
                    <span style="color: #475569;">2.</span> Everything is liquidated at 85% market value<br>
                    <span style="color: #475569;">3.</span> {int(DEBT_PAYMENT_PERCENTAGE*100)}% of debts are paid from proceeds<br>
                    <span style="color: #475569;">4.</span> Remainder is distributed to {'your ' + str(len(heir_names)) + ' heir(s)' if heir_names else 'government (no heirs)'}<br>
                    <span style="color: #475569;">5.</span> {'Heirs pay ' + str(int(DEATH_TAX_RATE*100)) + '% death tax in 7 daily installments' if heir_names else 'No death tax (government takes all)'}<br>
                    <span style="color: #475569;">6.</span> Your account is permanently deleted<br>
                    <span style="color: #475569;">7.</span> A death certificate is created in the registry
                </div>
            </div>
            <div style="color: #64748b; font-size: 0.8rem; margin-top: 8px; border-top: 1px solid #1e293b; padding-top: 12px;">
                Accounts inactive for {IDLE_DAYS_BEFORE_DEATH}+ days are automatically processed through this same system.
            </div>
        </div>
    </div>

    <div class="delete-zone">
        <h3>Permanent Account Deletion</h3>
        <p style="color: #94a3b8; margin-bottom: 16px; font-size: 0.85rem;">
            Type your business name <strong style="color: #fca5a5;">{player.business_name}</strong> to confirm deletion.
            This action is immediate and irreversible.
        </p>
        <form action="/api/estate/delete-account" method="post">
            <div style="display: flex; gap: 12px; align-items: center; flex-wrap: wrap;">
                <input type="text" name="confirm_name" placeholder="Type your business name..."
                       style="flex: 1; min-width: 200px; padding: 10px 14px; background: #111827;
                              border: 1px solid #7f1d1d; border-radius: 6px; color: #e5e7eb;
                              font-family: inherit; font-size: 0.9rem;"
                       required autocomplete="off">
                <button type="submit" class="btn btn-danger"
                        onclick="return confirm('Are you absolutely sure? Your account will be permanently deleted and your assets liquidated.')">
                    Delete My Account
                </button>
            </div>
        </form>
    </div>

    <div style="margin-top: 16px;">
        <a href="/estate" class="btn btn-secondary">Cancel - Back to Estate</a>
    </div>
    """

    return HTMLResponse(death_shell("Delete Account", body, player.cash_balance, player.business_name))


# ==========================
# API ENDPOINTS
# ==========================

@router.post("/api/estate/set-heir")
async def api_set_heir(
    session_token: Optional[str] = Cookie(None),
    heir_player_id: int = Form(...),
    priority: int = Form(...)
):
    """Set a player as heir at given priority."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player

    from estate import set_heir
    success = set_heir(player.id, heir_player_id, priority)

    if not success:
        return RedirectResponse(url="/estate/heirs?error=Failed+to+set+heir", status_code=303)

    return RedirectResponse(url="/estate/heirs", status_code=303)


@router.post("/api/estate/remove-heir")
async def api_remove_heir(
    session_token: Optional[str] = Cookie(None),
    priority: int = Form(...)
):
    """Remove an heir designation."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player

    from estate import remove_heir
    remove_heir(player.id, priority)

    return RedirectResponse(url="/estate/heirs", status_code=303)


@router.post("/api/estate/delete-account")
async def api_delete_account(
    session_token: Optional[str] = Cookie(None),
    confirm_name: str = Form(...)
):
    """Delete a player's account after confirmation."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player

    # Verify confirmation matches business name
    if confirm_name.strip() != player.business_name.strip():
        return RedirectResponse(
            url="/estate/delete-account?error=Business+name+does+not+match",
            status_code=303
        )

    # Don't allow government deletion
    if player.id <= 0:
        return RedirectResponse(
            url="/estate/delete-account?error=Cannot+delete+system+accounts",
            status_code=303
        )

    from estate import liquidate_estate
    from app import current_tick

    deceased = liquidate_estate(player.id, "voluntary", current_tick)

    if not deceased:
        return RedirectResponse(
            url="/estate/delete-account?error=Account+deletion+failed",
            status_code=303
        )

    # Clear session cookie and redirect to login
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(key="session_token")
    return response


# ==========================
# PUBLIC API
# ==========================

__all__ = [
    'router'
]
