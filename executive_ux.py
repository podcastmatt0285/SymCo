"""
executive_ux.py

UX module for the executive system.
Provides web interface and API endpoints for:
- Executive dashboard (view your hired executives)
- Executive marketplace (hire new executives)
- Firing executives
- Sending executives to school
- Selecting school upgrades
"""

from typing import Optional
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
EXEC_STYLES = """
<style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
        font-family: 'JetBrains Mono', 'Fira Code', monospace;
        background: #020617;
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
    .header h1 { font-size: 24px; color: #c084fc; }
    .nav-link {
        color: #38bdf8;
        text-decoration: none;
        font-size: 14px;
        padding: 8px 16px;
        border: 1px solid #38bdf8;
        border-radius: 6px;
    }
    .nav-link:hover { background: #38bdf822; }
    .nav-row {
        display: flex;
        gap: 12px;
        margin-bottom: 20px;
        flex-wrap: wrap;
    }
    .card {
        background: #0f172a;
        border: 1px solid #1e293b;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 16px;
    }
    .card-special {
        background: #0f172a;
        border: 2px solid #d4af37;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 16px;
        box-shadow: 0 0 15px #d4af3744;
    }
    .exec-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
        gap: 16px;
    }
    .exec-name {
        font-size: 18px;
        font-weight: bold;
        color: #f1f5f9;
        margin-bottom: 4px;
    }
    .exec-title {
        font-size: 13px;
        color: #d4af37;
        margin-bottom: 8px;
        font-style: italic;
    }
    .exec-special-tag {
        display: inline-block;
        background: #d4af3722;
        color: #d4af37;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 11px;
        font-weight: bold;
        margin-bottom: 8px;
    }
    .stat-row {
        display: flex;
        justify-content: space-between;
        padding: 4px 0;
        border-bottom: 1px solid #1e293b44;
        font-size: 13px;
    }
    .stat-label { color: #94a3b8; }
    .stat-value { color: #e5e7eb; font-weight: bold; }
    .stat-value.green { color: #22c55e; }
    .stat-value.orange { color: #f59e0b; }
    .stat-value.red { color: #ef4444; }
    .stat-value.purple { color: #c084fc; }
    .stat-value.gold { color: #d4af37; }
    .level-bar {
        width: 100%;
        height: 8px;
        background: #1e293b;
        border-radius: 4px;
        margin: 8px 0;
        overflow: hidden;
    }
    .level-fill {
        height: 100%;
        border-radius: 4px;
        background: linear-gradient(90deg, #38bdf8, #c084fc);
    }
    .school-bar .level-fill {
        background: linear-gradient(90deg, #f59e0b, #22c55e);
    }
    .age-bar .level-fill {
        background: linear-gradient(90deg, #22c55e, #f59e0b, #ef4444);
    }
    .btn {
        display: inline-block;
        padding: 8px 16px;
        border-radius: 6px;
        text-decoration: none;
        font-size: 13px;
        font-weight: bold;
        cursor: pointer;
        border: none;
        font-family: inherit;
        text-align: center;
    }
    .btn-blue { background: #38bdf8; color: #020617; }
    .btn-blue:hover { background: #7dd3fc; }
    .btn-orange { background: #f59e0b; color: #020617; }
    .btn-orange:hover { background: #fbbf24; }
    .btn-red { background: #ef4444; color: #fff; }
    .btn-red:hover { background: #f87171; }
    .btn-green { background: #22c55e; color: #020617; }
    .btn-green:hover { background: #4ade80; }
    .btn-purple { background: #c084fc; color: #020617; }
    .btn-purple:hover { background: #d8b4fe; }
    .btn-gold { background: #d4af37; color: #020617; }
    .btn-gold:hover { background: #e5c54a; }
    .btn-small { padding: 5px 12px; font-size: 12px; }
    .actions { display: flex; gap: 8px; margin-top: 12px; flex-wrap: wrap; }
    .msg-success {
        background: #22c55e22;
        border: 1px solid #22c55e;
        color: #22c55e;
        padding: 12px;
        border-radius: 6px;
        margin-bottom: 16px;
    }
    .msg-error {
        background: #ef444422;
        border: 1px solid #ef4444;
        color: #ef4444;
        padding: 12px;
        border-radius: 6px;
        margin-bottom: 16px;
    }
    .flavor-text {
        font-style: italic;
        color: #94a3b8;
        font-size: 12px;
        margin-top: 8px;
        padding: 8px;
        border-left: 2px solid #d4af37;
    }
    .badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 11px;
        font-weight: bold;
    }
    .badge-new { background: #22c55e22; color: #22c55e; }
    .badge-fired { background: #ef444422; color: #ef4444; }
    .badge-retired { background: #f59e0b22; color: #f59e0b; }
    .badge-school { background: #38bdf822; color: #38bdf8; }
    .badge-pension { background: #c084fc22; color: #c084fc; }
    .summary-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
        gap: 12px;
        margin-bottom: 20px;
    }
    .summary-card {
        background: #1e293b;
        border-radius: 6px;
        padding: 12px;
        text-align: center;
    }
    .summary-card .label { color: #94a3b8; font-size: 12px; }
    .summary-card .value { font-size: 22px; font-weight: bold; color: #f1f5f9; }
    .upgrade-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
        gap: 12px;
    }
    .upgrade-option {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 16px;
        cursor: pointer;
        transition: border-color 0.2s;
    }
    .upgrade-option:hover { border-color: #c084fc; }
    .upgrade-name { font-weight: bold; color: #c084fc; margin-bottom: 4px; }
    .upgrade-desc { font-size: 13px; color: #94a3b8; }
    .empty-state {
        text-align: center;
        padding: 40px;
        color: #64748b;
    }
    .empty-state h3 { color: #94a3b8; margin-bottom: 8px; }
    @media (max-width: 640px) {
        .exec-grid { grid-template-columns: 1fr; }
        .summary-grid { grid-template-columns: 1fr 1fr; }
        .nav-row { flex-direction: column; }
    }
</style>
"""


def exec_shell(title: str, body: str, player=None) -> str:
    """Wrap content in executive page template."""
    balance_html = ""
    if player:
        balance_html = f'<span style="color: #22c55e;">${player.cash_balance:,.2f}</span>'

    return f"""<!DOCTYPE html>
<html><head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>SymCo - {title}</title>
    {EXEC_STYLES}
</head><body>
    <div class="container">
        <div class="header">
            <h1>{title}</h1>
            <div style="display:flex;gap:16px;align-items:center;">
                {balance_html}
                <a href="/" class="nav-link">Dashboard</a>
            </div>
        </div>
        {body}
    </div>
</body></html>"""


def render_exec_card(ex, show_actions=True, is_owner=False, marketplace=False) -> str:
    """Render an executive as an HTML card."""
    from executive import EXECUTIVE_JOBS, PAY_CYCLE_LABELS, PAY_CYCLES, SPECIAL_ABILITIES

    job_info = EXECUTIVE_JOBS.get(ex.job, {"title": ex.job, "description": ""})
    card_class = "card-special" if ex.is_special else "card"

    # Name line
    name = f"{ex.first_name} {ex.last_name}"
    if ex.is_special and ex.special_title:
        name += f' "{ex.special_title}"'

    # Special tag
    special_html = ""
    if ex.is_special and ex.special_ability:
        ability = SPECIAL_ABILITIES.get(ex.special_ability, {})
        special_html = f"""
        <span class="exec-special-tag">LEGENDARY - {ability.get('name', ex.special_ability)}</span><br>
        <span style="font-size:11px;color:#94a3b8;">{ability.get('description', '')}</span>
        """

    # Flavor text
    flavor_html = ""
    if ex.is_special and ex.special_flavor:
        flavor_html = f'<div class="flavor-text">{ex.special_flavor}</div>'

    # Level bar
    level_pct = min(ex.level / 7.0, 1.0) * 100
    level_html = f"""
    <div class="stat-row">
        <span class="stat-label">Level</span>
        <span class="stat-value purple">{ex.level}/7</span>
    </div>
    <div class="level-bar"><div class="level-fill" style="width:{level_pct:.0f}%"></div></div>
    """

    # Age bar
    age_pct = min(ex.current_age / ex.max_age, 1.0) * 100
    age_color = "green" if ex.current_age < ex.retirement_age - 10 else ("orange" if ex.current_age < ex.retirement_age else "red")
    age_html = f"""
    <div class="stat-row">
        <span class="stat-label">Age</span>
        <span class="stat-value {age_color}">{ex.current_age} / retires at {ex.retirement_age}</span>
    </div>
    <div class="level-bar age-bar"><div class="level-fill" style="width:{age_pct:.0f}%"></div></div>
    """

    # School status
    school_html = ""
    if ex.is_in_school:
        school_html = f"""
        <div class="stat-row">
            <span class="stat-label">School</span>
            <span class="stat-value orange">In session - {ex.school_ticks_remaining} ticks remaining</span>
        </div>
        <div class="level-bar school-bar"><div class="level-fill" style="width:{max(5, 100 - (ex.school_ticks_remaining / max(1, ex.school_ticks_remaining + 1) * 100)):.0f}%"></div></div>
        """
    elif ex.pending_upgrade:
        school_html = f"""
        <div style="background:#c084fc22;border:1px solid #c084fc;padding:8px;border-radius:6px;margin-top:8px;">
            <strong style="color:#c084fc;">Upgrade Ready!</strong> - Select an upgrade for this executive.
            <div class="actions">
                <a href="/executives/upgrade/{ex.id}" class="btn btn-purple btn-small">Select Upgrade</a>
            </div>
        </div>
        """

    # Pension indicator
    pension_html = ""
    if ex.pension_ticks_remaining > 0:
        pension_html = f"""
        <div class="stat-row">
            <span class="stat-label">Pension</span>
            <span class="stat-value orange">${ex.pension_owed:,.2f} - {ex.pension_ticks_remaining} ticks left</span>
        </div>
        """

    # Marketplace badge
    badge_html = ""
    if marketplace:
        reason_map = {
            "new": ("NEW", "badge-new"),
            "fired": ("FIRED", "badge-fired"),
            "retired_available": ("BACK FROM RETIREMENT", "badge-retired")
        }
        reason = ex.marketplace_reason or "new"
        label, cls = reason_map.get(reason, ("AVAILABLE", "badge-new"))
        badge_html = f'<span class="badge {cls}">{label}</span> '

    # Pay info
    cycle_label = PAY_CYCLE_LABELS.get(ex.pay_cycle, ex.pay_cycle)
    wage_html = f"""
    <div class="stat-row">
        <span class="stat-label">Wage</span>
        <span class="stat-value green">${ex.wage:,.2f} {cycle_label}</span>
    </div>
    """

    # Hiring fee for marketplace
    hiring_fee_html = ""
    if marketplace:
        cycle_ticks = PAY_CYCLES[ex.pay_cycle]
        hiring_fee = ex.wage * (PAY_CYCLES["day"] / cycle_ticks)
        hiring_fee_html = f"""
        <div class="stat-row">
            <span class="stat-label">Hiring Fee</span>
            <span class="stat-value gold">${hiring_fee:,.2f}</span>
        </div>
        """

    # Actions
    actions_html = ""
    if show_actions and is_owner:
        btns = []
        if not ex.is_in_school and not ex.pending_upgrade and ex.level < 7:
            btns.append(f'<a href="/executives/school/{ex.id}" class="btn btn-orange btn-small">Send to School</a>')
        btns.append(f"""
            <form method="POST" action="/api/executives/fire" style="display:inline;">
                <input type="hidden" name="executive_id" value="{ex.id}">
                <button type="submit" class="btn btn-red btn-small" onclick="return confirm('Fire {ex.first_name}? Pension will still be owed.')">Fire</button>
            </form>
        """)
        actions_html = f'<div class="actions">{"".join(btns)}</div>'
    elif show_actions and marketplace:
        actions_html = f"""
        <div class="actions">
            <form method="POST" action="/api/executives/hire" style="display:inline;">
                <input type="hidden" name="executive_id" value="{ex.id}">
                <button type="submit" class="btn btn-green btn-small">Hire</button>
            </form>
        </div>
        """

    return f"""
    <div class="{card_class}">
        {badge_html}
        <div class="exec-name">{name}</div>
        <div class="exec-title">{job_info['title']}</div>
        <div style="font-size:12px;color:#64748b;margin-bottom:8px;">{job_info['description']}</div>
        {special_html}
        {level_html}
        {age_html}
        {wage_html}
        {hiring_fee_html}
        {school_html}
        {pension_html}
        {flavor_html}
        {actions_html}
    </div>
    """


# ==========================
# PAGES
# ==========================

@router.get("/executives", response_class=HTMLResponse)
def executives_dashboard(session_token: Optional[str] = Cookie(None), msg: Optional[str] = Query(None)):
    """Main executives dashboard - shows player's hired executives."""
    player = get_current_player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)

    from executive import get_player_executives, MAX_EXECUTIVES_PER_PLAYER, get_db

    db = get_db()
    try:
        execs = get_player_executives(db, player.id)

        # Message display
        msg_html = ""
        if msg:
            css_class = "msg-success" if "success" in msg.lower() or "hired" in msg.lower() or "fired" in msg.lower() or "upgraded" in msg.lower() or "sent" in msg.lower() else "msg-error"
            msg_html = f'<div class="{css_class}">{msg}</div>'

        # Navigation
        nav_html = """
        <div class="nav-row">
            <a href="/executives" class="btn btn-purple">My Executives</a>
            <a href="/executives/marketplace" class="btn btn-blue">Marketplace</a>
            <a href="/" class="nav-link">Dashboard</a>
        </div>
        """

        # Summary stats
        total_wages_per_hour = 0
        active_count = 0
        school_count = 0
        pending_count = 0

        from executive import PAY_CYCLES
        for ex in execs:
            if not ex.is_retired:
                active_count += 1
                cycle_ticks = PAY_CYCLES.get(ex.pay_cycle, 720)
                hourly_wage = ex.wage * (720 / cycle_ticks)
                total_wages_per_hour += hourly_wage
            if ex.is_in_school:
                school_count += 1
            if ex.pending_upgrade:
                pending_count += 1

        summary_html = f"""
        <div class="summary-grid">
            <div class="summary-card">
                <div class="label">Executives</div>
                <div class="value">{len(execs)}/{MAX_EXECUTIVES_PER_PLAYER}</div>
            </div>
            <div class="summary-card">
                <div class="label">Active</div>
                <div class="value" style="color:#22c55e;">{active_count}</div>
            </div>
            <div class="summary-card">
                <div class="label">In School</div>
                <div class="value" style="color:#f59e0b;">{school_count}</div>
            </div>
            <div class="summary-card">
                <div class="label">Wages/Hour</div>
                <div class="value" style="color:#ef4444;">${total_wages_per_hour:,.2f}</div>
            </div>
        </div>
        """

        # Pending upgrades alert
        pending_html = ""
        if pending_count > 0:
            pending_html = f"""
            <div style="background:#c084fc22;border:1px solid #c084fc;padding:12px;border-radius:6px;margin-bottom:16px;">
                <strong style="color:#c084fc;">{pending_count} executive(s) graduated!</strong> Select their upgrades below.
            </div>
            """

        # Executive cards
        if execs:
            cards_html = '<div class="exec-grid">'
            for ex in execs:
                cards_html += render_exec_card(ex, show_actions=True, is_owner=True)
            cards_html += '</div>'
        else:
            cards_html = """
            <div class="empty-state">
                <h3>No Executives Hired</h3>
                <p>Visit the marketplace to hire your first executive.</p>
                <br>
                <a href="/executives/marketplace" class="btn btn-blue">Browse Marketplace</a>
            </div>
            """

        body = f"{msg_html}{nav_html}{summary_html}{pending_html}{cards_html}"
        return exec_shell("Executives Dashboard", body, player)
    finally:
        db.close()


@router.get("/executives/marketplace", response_class=HTMLResponse)
def executives_marketplace(session_token: Optional[str] = Cookie(None), msg: Optional[str] = Query(None)):
    """Executive marketplace - hire new executives."""
    player = get_current_player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)

    from executive import get_marketplace_executives, get_db

    db = get_db()
    try:
        available = get_marketplace_executives(db)

        msg_html = ""
        if msg:
            css_class = "msg-success" if "success" in msg.lower() or "hired" in msg.lower() else "msg-error"
            msg_html = f'<div class="{css_class}">{msg}</div>'

        nav_html = """
        <div class="nav-row">
            <a href="/executives" class="btn btn-purple">My Executives</a>
            <a href="/executives/marketplace" class="btn btn-blue">Marketplace</a>
            <a href="/" class="nav-link">Dashboard</a>
        </div>
        """

        count_html = f'<p style="color:#94a3b8;margin-bottom:16px;">{len(available)} executive(s) available for hire</p>'

        if available:
            # Separate specials from regulars
            specials = [e for e in available if e.is_special]
            regulars = [e for e in available if not e.is_special]

            cards_html = ""
            if specials:
                cards_html += '<h3 style="color:#d4af37;margin-bottom:12px;">Legendary Executives</h3>'
                cards_html += '<div class="exec-grid">'
                for ex in specials:
                    cards_html += render_exec_card(ex, show_actions=True, marketplace=True)
                cards_html += '</div><br>'

            if regulars:
                cards_html += '<h3 style="color:#94a3b8;margin-bottom:12px;">Available Executives</h3>'
                cards_html += '<div class="exec-grid">'
                for ex in regulars:
                    cards_html += render_exec_card(ex, show_actions=True, marketplace=True)
                cards_html += '</div>'
        else:
            cards_html = """
            <div class="empty-state">
                <h3>No Executives Available</h3>
                <p>Check back later - new executives enter the workforce periodically.</p>
            </div>
            """

        body = f"{msg_html}{nav_html}{count_html}{cards_html}"
        return exec_shell("Executive Marketplace", body, player)
    finally:
        db.close()


@router.get("/executives/school/{executive_id}", response_class=HTMLResponse)
def school_confirm(executive_id: int, session_token: Optional[str] = Cookie(None)):
    """Confirm sending executive to school."""
    player = get_current_player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)

    from executive import (
        Executive, EXECUTIVE_JOBS, SCHOOL_BASE_COST, SCHOOL_BASE_TICKS,
        get_player_job_bonus, get_db
    )

    db = get_db()
    try:
        ex = db.query(Executive).filter(
            Executive.id == executive_id,
            Executive.player_id == player.id
        ).first()

        if not ex:
            return RedirectResponse(url="/executives?msg=Executive not found", status_code=303)
        if ex.level >= 7:
            return RedirectResponse(url="/executives?msg=Executive is at max level", status_code=303)

        target_level = ex.level + 1
        cost = SCHOOL_BASE_COST * target_level
        ticks = SCHOOL_BASE_TICKS * target_level

        cto_bonus = get_player_job_bonus(db, player.id, "school")
        cost *= max(0.2, 1.0 - cto_bonus)
        ticks = int(ticks * max(0.2, 1.0 - cto_bonus))

        if ex.is_special and ex.special_ability == "fast_learner":
            ticks = ticks // 2

        job_info = EXECUTIVE_JOBS.get(ex.job, {"title": ex.job})

        # Approximate real time
        real_seconds = ticks * 5
        if real_seconds < 60:
            time_str = f"{real_seconds}s"
        elif real_seconds < 3600:
            time_str = f"{real_seconds // 60}m {real_seconds % 60}s"
        else:
            time_str = f"{real_seconds // 3600}h {(real_seconds % 3600) // 60}m"

        can_afford = player.cash_balance >= cost

        body = f"""
        <div class="nav-row">
            <a href="/executives" class="nav-link">Back to Executives</a>
        </div>
        <div class="card">
            <h2>Send to School: {ex.first_name} {ex.last_name}</h2>
            <p style="color:#94a3b8;">{job_info['title']} - Level {ex.level}</p>
            <br>
            <div class="stat-row">
                <span class="stat-label">Target Level</span>
                <span class="stat-value purple">{target_level}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Tuition Cost</span>
                <span class="stat-value {'green' if can_afford else 'red'}">${cost:,.2f}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Duration</span>
                <span class="stat-value orange">{ticks} ticks (~{time_str})</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Your Balance</span>
                <span class="stat-value green">${player.cash_balance:,.2f}</span>
            </div>
            {'' if not cto_bonus else f'<div class="stat-row"><span class="stat-label">CTO Discount</span><span class="stat-value purple">{cto_bonus*100:.1f}%</span></div>'}
            <br>
            <p style="color:#94a3b8;font-size:13px;">While in school, this executive will not provide any bonuses. After graduation, you will choose from available upgrades.</p>
            <div class="actions">
                {'<form method="POST" action="/api/executives/school"><input type="hidden" name="executive_id" value="' + str(ex.id) + '"><button type="submit" class="btn btn-orange">Enroll Now</button></form>' if can_afford else '<span class="btn btn-red" style="cursor:not-allowed;">Insufficient Funds</span>'}
                <a href="/executives" class="btn btn-blue">Cancel</a>
            </div>
        </div>
        """
        return exec_shell("School Enrollment", body, player)
    finally:
        db.close()


@router.get("/executives/upgrade/{executive_id}", response_class=HTMLResponse)
def upgrade_select(executive_id: int, session_token: Optional[str] = Cookie(None)):
    """Select upgrade after school graduation."""
    player = get_current_player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)

    from executive import Executive, EXECUTIVE_JOBS, SCHOOL_UPGRADES, get_db

    db = get_db()
    try:
        ex = db.query(Executive).filter(
            Executive.id == executive_id,
            Executive.player_id == player.id
        ).first()

        if not ex:
            return RedirectResponse(url="/executives?msg=Executive not found", status_code=303)
        if not ex.pending_upgrade:
            return RedirectResponse(url="/executives?msg=No pending upgrade", status_code=303)

        target_level = ex.level + 1
        upgrades = SCHOOL_UPGRADES.get(target_level, [])
        job_info = EXECUTIVE_JOBS.get(ex.job, {"title": ex.job})

        if not upgrades:
            return RedirectResponse(url="/executives?msg=No upgrades available for this level", status_code=303)

        upgrade_cards = ""
        for u in upgrades:
            upgrade_cards += f"""
            <form method="POST" action="/api/executives/upgrade" class="upgrade-option">
                <input type="hidden" name="executive_id" value="{ex.id}">
                <input type="hidden" name="bonus_key" value="{u['bonus']}">
                <div class="upgrade-name">{u['name']}</div>
                <div class="upgrade-desc">{u['description']}</div>
                <br>
                <button type="submit" class="btn btn-purple btn-small">Select</button>
            </form>
            """

        body = f"""
        <div class="nav-row">
            <a href="/executives" class="nav-link">Back to Executives</a>
        </div>
        <div class="card">
            <h2>Graduation: {ex.first_name} {ex.last_name}</h2>
            <p style="color:#94a3b8;">{job_info['title']} - Upgrading to Level {target_level}</p>
            <br>
            <p style="color:#c084fc;">Choose one upgrade:</p>
        </div>
        <div class="upgrade-grid">
            {upgrade_cards}
        </div>
        """
        return exec_shell("Select Upgrade", body, player)
    finally:
        db.close()


# ==========================
# API ENDPOINTS
# ==========================

@router.post("/api/executives/hire", response_class=HTMLResponse)
def api_hire(executive_id: int = Form(...), session_token: Optional[str] = Cookie(None)):
    """Hire an executive from the marketplace."""
    player = get_current_player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)

    from executive import hire_executive, get_db

    db = get_db()
    try:
        result = hire_executive(db, player.id, executive_id)
        if result["success"]:
            return RedirectResponse(
                url=f"/executives?msg={result['message']}",
                status_code=303
            )
        else:
            return RedirectResponse(
                url=f"/executives/marketplace?msg={result['error']}",
                status_code=303
            )
    finally:
        db.close()


@router.post("/api/executives/fire", response_class=HTMLResponse)
def api_fire(executive_id: int = Form(...), session_token: Optional[str] = Cookie(None)):
    """Fire an executive."""
    player = get_current_player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)

    from executive import fire_executive, get_db

    db = get_db()
    try:
        result = fire_executive(db, player.id, executive_id)
        return RedirectResponse(
            url=f"/executives?msg={result['message'] if result['success'] else result['error']}",
            status_code=303
        )
    finally:
        db.close()


@router.post("/api/executives/school", response_class=HTMLResponse)
def api_school(executive_id: int = Form(...), session_token: Optional[str] = Cookie(None)):
    """Send an executive to school."""
    player = get_current_player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)

    from executive import send_to_school, get_db

    db = get_db()
    try:
        result = send_to_school(db, player.id, executive_id)
        return RedirectResponse(
            url=f"/executives?msg={result['message'] if result['success'] else result['error']}",
            status_code=303
        )
    finally:
        db.close()


@router.post("/api/executives/upgrade", response_class=HTMLResponse)
def api_upgrade(
    executive_id: int = Form(...),
    bonus_key: str = Form(...),
    session_token: Optional[str] = Cookie(None)
):
    """Apply a school upgrade."""
    player = get_current_player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)

    from executive import apply_school_upgrade, get_db

    db = get_db()
    try:
        result = apply_school_upgrade(db, player.id, executive_id, bonus_key)
        return RedirectResponse(
            url=f"/executives?msg={result['message'] if result['success'] else result['error']}",
            status_code=303
        )
    finally:
        db.close()
