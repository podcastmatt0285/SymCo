"""
admins_ux.py - Admin Dashboard UI

The admin command center for managing the game.
Features:
- Post messages to the Updates channel
- View and edit all player data (cash, inventory, land, districts, businesses)
- Kick / ban / timeout players
- View P2P contract activity
- Chat room viewer
- Land bank management
- Admin action audit log
"""

import json
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Cookie, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse

from admins import (
    ADMIN_PLAYER_IDS,
    is_admin, require_admin,
    get_all_players, get_player_detail, edit_player_balance,
    get_player_inventory, admin_add_item, admin_remove_item, get_all_item_types,
    get_player_land, admin_delete_land_plot, admin_create_land_plot,
    get_player_districts, get_player_businesses,
    get_land_bank_entries, admin_add_to_land_bank, admin_remove_from_land_bank,
    get_chat_rooms_overview, get_chat_room_messages,
    ban_player, timeout_player, kick_player, revoke_ban, get_active_ban,
    post_update, get_p2p_overview, get_admin_logs, log_action,
)

router = APIRouter()


# ==========================
# SHELL
# ==========================

def admin_shell(title: str, body: str, player_name: str = "", active_nav: str = "/admin") -> str:
    """Admin dashboard shell - mobile-first dark theme with red accent."""
    nav_items = [
        ("/admin", "Home"),
        ("/admin/players", "Players"),
        ("/admin/updates", "Updates"),
        ("/admin/chat", "Chat"),
        ("/admin/p2p", "P2P"),
        ("/admin/landbank", "Land Bank"),
        ("/admin/logs", "Logs"),
    ]
    nav_html = ""
    for href, label in nav_items:
        active = ' class="active"' if href == active_nav else ""
        nav_html += f'<a href="{href}"{active}>{label}</a>'

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{title} - Admin</title>
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
        <style>
            * {{ box-sizing: border-box; margin: 0; padding: 0; }}
            body {{
                background: #020617;
                color: #e5e7eb;
                font-family: 'JetBrains Mono', monospace;
                font-size: 13px;
                min-height: 100vh;
                min-height: 100dvh;
            }}
            a {{ color: #38bdf8; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}

            /* HEADER */
            .header {{
                border-bottom: 1px solid #7f1d1d;
                padding: 8px 12px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                background: #0a0f1e;
                flex-wrap: wrap;
                gap: 6px;
            }}
            .brand {{ font-weight: bold; color: #ef4444; font-size: 0.9rem; }}
            .header-right {{
                display: flex; align-items: center; gap: 8px; font-size: 0.75rem;
                flex-wrap: wrap;
            }}

            /* NAV - horizontally scrollable on mobile */
            .nav {{
                display: flex;
                border-bottom: 1px solid #1e293b;
                background: #0a0f1e;
                overflow-x: auto;
                -webkit-overflow-scrolling: touch;
                scrollbar-width: none;
            }}
            .nav::-webkit-scrollbar {{ display: none; }}
            .nav a {{
                padding: 10px 14px;
                color: #94a3b8;
                font-size: 0.75rem;
                white-space: nowrap;
                border-bottom: 2px solid transparent;
                flex-shrink: 0;
            }}
            .nav a:hover {{ color: #e5e7eb; text-decoration: none; background: #1e293b; }}
            .nav a.active {{ color: #ef4444; border-bottom-color: #ef4444; font-weight: bold; }}

            /* CONTAINER */
            .container {{
                max-width: 1000px;
                margin: 0 auto;
                padding: 12px;
            }}

            /* CARDS */
            .card {{
                background: #0f172a;
                border: 1px solid #1e293b;
                padding: 12px;
                margin-bottom: 12px;
                border-radius: 4px;
                overflow: hidden;
            }}
            .card h3 {{
                font-size: 0.82rem;
                color: #e5e7eb;
                margin-bottom: 10px;
                padding-bottom: 6px;
                border-bottom: 1px solid #1e293b;
            }}

            /* TABLES - responsive */
            .table-wrap {{ overflow-x: auto; -webkit-overflow-scrolling: touch; }}
            table {{
                width: 100%;
                border-collapse: collapse;
                font-size: 0.75rem;
                min-width: 400px;
            }}
            th {{
                text-align: left;
                padding: 6px;
                color: #64748b;
                font-size: 0.65rem;
                text-transform: uppercase;
                border-bottom: 1px solid #1e293b;
                white-space: nowrap;
            }}
            td {{
                padding: 6px;
                border-bottom: 1px solid #0f172a;
                vertical-align: middle;
            }}
            tr:hover {{ background: #1e293b; }}

            /* BADGES */
            .badge {{
                font-size: 0.6rem;
                padding: 2px 5px;
                border-radius: 3px;
                font-weight: bold;
                white-space: nowrap;
            }}
            .badge-red {{ background: #7f1d1d; color: #fca5a5; }}
            .badge-yellow {{ background: #78350f; color: #fcd34d; }}
            .badge-green {{ background: #14532d; color: #86efac; }}
            .badge-blue {{ background: #1e3a5f; color: #93c5fd; }}

            /* BUTTONS */
            .btn {{
                border: none;
                padding: 6px 10px;
                cursor: pointer;
                font-size: 0.7rem;
                font-family: inherit;
                border-radius: 3px;
                font-weight: bold;
                white-space: nowrap;
            }}
            .btn-red {{ background: #ef4444; color: #fff; }}
            .btn-red:hover {{ background: #dc2626; }}
            .btn-yellow {{ background: #f59e0b; color: #020617; }}
            .btn-yellow:hover {{ background: #d97706; }}
            .btn-blue {{ background: #38bdf8; color: #020617; }}
            .btn-blue:hover {{ background: #0ea5e9; }}
            .btn-green {{ background: #22c55e; color: #020617; }}
            .btn-green:hover {{ background: #16a34a; }}
            .btn-gray {{ background: #334155; color: #94a3b8; }}
            .btn-gray:hover {{ background: #475569; }}

            /* FORMS */
            input, select, textarea {{
                background: #020617;
                border: 1px solid #1e293b;
                color: #e5e7eb;
                padding: 6px 8px;
                font-family: inherit;
                font-size: 16px; /* prevents iOS zoom */
                border-radius: 3px;
                width: 100%;
            }}
            input:focus, select:focus, textarea:focus {{
                outline: none;
                border-color: #ef4444;
            }}
            textarea {{
                resize: vertical;
                font-size: 14px;
            }}

            /* INLINE FORMS */
            .form-row {{
                display: flex;
                gap: 6px;
                margin-bottom: 8px;
                align-items: flex-end;
                flex-wrap: wrap;
            }}
            .form-row > * {{ flex: 1; min-width: 0; }}
            .form-row .btn {{ flex: 0 0 auto; }}
            .form-label {{
                font-size: 0.65rem;
                color: #64748b;
                margin-bottom: 3px;
                text-transform: uppercase;
            }}

            /* STAT GRID */
            .stat-grid {{
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 8px;
                margin-bottom: 12px;
            }}
            .stat-box {{
                background: #0f172a;
                border: 1px solid #1e293b;
                padding: 10px;
                border-radius: 4px;
                text-align: center;
            }}
            .stat-value {{
                font-size: 1.2rem;
                font-weight: bold;
                color: #e5e7eb;
            }}
            .stat-label {{
                font-size: 0.6rem;
                color: #64748b;
                text-transform: uppercase;
                margin-top: 2px;
            }}

            /* LINK GRID */
            .link-grid {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 8px;
            }}
            .link-card {{
                display: block;
                background: #0f172a;
                border: 1px solid #1e293b;
                border-radius: 4px;
                padding: 12px;
                text-decoration: none;
                text-align: center;
            }}
            .link-card:hover {{ border-color: #334155; text-decoration: none; }}
            .link-card .lc-icon {{ font-size: 1.3rem; margin-bottom: 4px; }}
            .link-card .lc-title {{ color: #e5e7eb; font-weight: bold; font-size: 0.8rem; }}
            .link-card .lc-desc {{ color: #64748b; font-size: 0.65rem; margin-top: 3px; }}

            /* DETAIL ROWS */
            .detail-row {{
                display: flex;
                justify-content: space-between;
                padding: 6px 0;
                border-bottom: 1px solid #1e293b;
                font-size: 0.78rem;
                flex-wrap: wrap;
                gap: 4px;
            }}
            .detail-row .label {{ color: #64748b; flex-shrink: 0; }}
            .detail-row .value {{ color: #e5e7eb; text-align: right; word-break: break-all; }}

            /* FLASH */
            .flash {{
                padding: 8px 12px;
                border-radius: 4px;
                margin-bottom: 10px;
                font-size: 0.75rem;
            }}
            .flash-success {{ background: #14532d; color: #86efac; border: 1px solid #166534; }}
            .flash-error {{ background: #7f1d1d; color: #fca5a5; border: 1px solid #991b1b; }}

            /* TABS (sub-nav within a page) */
            .tabs {{
                display: flex;
                gap: 0;
                border-bottom: 1px solid #1e293b;
                margin-bottom: 12px;
                overflow-x: auto;
                -webkit-overflow-scrolling: touch;
            }}
            .tabs a {{
                padding: 8px 12px;
                color: #64748b;
                font-size: 0.72rem;
                white-space: nowrap;
                border-bottom: 2px solid transparent;
                flex-shrink: 0;
            }}
            .tabs a:hover {{ color: #e5e7eb; text-decoration: none; }}
            .tabs a.active {{ color: #38bdf8; border-bottom-color: #38bdf8; }}

            /* CHAT MESSAGE */
            .chat-msg-row {{
                padding: 4px 0;
                border-bottom: 1px solid #0f172a;
                font-size: 0.75rem;
            }}
            .chat-msg-row .cm-name {{ color: #38bdf8; font-weight: bold; }}
            .chat-msg-row .cm-time {{ color: #475569; font-size: 0.6rem; margin-left: 6px; }}
            .chat-msg-row .cm-text {{ color: #cbd5e1; margin-top: 1px; word-break: break-word; }}

            /* DESKTOP */
            @media (min-width: 640px) {{
                .container {{ padding: 16px; }}
                .stat-grid {{ grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); }}
                table {{ font-size: 0.78rem; }}
                input, select {{ font-size: 0.85rem; }}
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <div style="display: flex; align-items: center; gap: 8px;">
                <span class="brand">ADMIN</span>
                <span style="color: #475569; font-size: 0.7rem;">Wadsworth</span>
            </div>
            <div class="header-right">
                <span style="color: #94a3b8;">{player_name}</span>
                <a href="/dashboard" style="color: #94a3b8;">Game</a>
                <a href="/chat" style="color: #94a3b8;">Chat</a>
                <a href="/api/logout" style="color: #ef4444;">Logout</a>
            </div>
        </div>
        <div class="nav">{nav_html}</div>
        <div class="container">
            {body}
        </div>
    </body>
    </html>
    """


# ==========================
# AUTH GUARD
# ==========================

def _guard(session_token):
    player = require_admin(session_token)
    if not player:
        return None, RedirectResponse(url="/login", status_code=303)
    return player, None


def _flash(msg=None, err=None):
    if msg:
        return f'<div class="flash flash-success">{msg}</div>'
    if err:
        return f'<div class="flash flash-error">{err}</div>'
    return ""


def _ts(iso_str):
    """Format ISO timestamp for display."""
    if not iso_str:
        return "-"
    return iso_str[:16].replace("T", " ")


# ==========================
# DASHBOARD (overview)
# ==========================

@router.get("/admin", response_class=HTMLResponse)
def admin_dashboard(session_token: Optional[str] = Cookie(None)):
    player, redirect = _guard(session_token)
    if redirect:
        return redirect

    players = get_all_players()
    total_players = len(players)
    total_cash = sum(p["cash_balance"] for p in players)
    banned_count = sum(1 for p in players if p["ban_status"] == "ban")
    timed_out_count = sum(1 for p in players if p["ban_status"] == "timeout")

    try:
        from chat import manager
        online_count = manager.get_online_count()
    except Exception:
        online_count = 0

    logs = get_admin_logs(limit=8)
    log_rows = ""
    for log in logs:
        target = f"#{log['target_player_id']}" if log["target_player_id"] else "-"
        log_rows += f'<tr><td style="color:#64748b;">{_ts(log["created_at"])}</td><td>{log["action"]}</td><td>{target}</td><td style="color:#94a3b8;max-width:150px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{log["details"][:50]}</td></tr>'

    body = f"""
    <div class="stat-grid">
        <div class="stat-box"><div class="stat-value">{total_players}</div><div class="stat-label">Players</div></div>
        <div class="stat-box"><div class="stat-value" style="color:#22c55e;">{online_count}</div><div class="stat-label">Online</div></div>
        <div class="stat-box"><div class="stat-value" style="color:#22c55e;">${total_cash:,.0f}</div><div class="stat-label">Total Cash</div></div>
        <div class="stat-box"><div class="stat-value" style="color:#ef4444;">{banned_count}</div><div class="stat-label">Banned</div></div>
    </div>

    <div class="link-grid" style="margin-bottom: 12px;">
        <a href="/admin/updates" class="link-card"><div class="lc-icon">📢</div><div class="lc-title">Post Update</div><div class="lc-desc">Updates channel</div></a>
        <a href="/admin/players" class="link-card"><div class="lc-icon">👥</div><div class="lc-title">Players</div><div class="lc-desc">View &amp; edit all</div></a>
        <a href="/admin/chat" class="link-card"><div class="lc-icon">💬</div><div class="lc-title">Chat Rooms</div><div class="lc-desc">Monitor chat</div></a>
        <a href="/admin/p2p" class="link-card"><div class="lc-icon">📋</div><div class="lc-title">P2P Contracts</div><div class="lc-desc">View activity</div></a>
        <a href="/admin/landbank" class="link-card"><div class="lc-icon">🏦</div><div class="lc-title">Land Bank</div><div class="lc-desc">Manage plots</div></a>
        <a href="/admin/logs" class="link-card"><div class="lc-icon">📜</div><div class="lc-title">Audit Log</div><div class="lc-desc">Admin actions</div></a>
    </div>

    <div class="card">
        <h3>Recent Actions</h3>
        {f'<div class="table-wrap"><table><tr><th>Time</th><th>Action</th><th>Target</th><th>Details</th></tr>{log_rows}</table></div>' if log_rows else '<p style="color:#64748b;font-size:0.75rem;">No actions yet.</p>'}
    </div>
    """
    return HTMLResponse(admin_shell("Dashboard", body, player.business_name, "/admin"))


# ==========================
# PLAYERS LIST
# ==========================

@router.get("/admin/players", response_class=HTMLResponse)
def admin_players(session_token: Optional[str] = Cookie(None), msg: Optional[str] = Query(None)):
    player, redirect = _guard(session_token)
    if redirect:
        return redirect

    players = get_all_players()
    rows = ""
    for p in players:
        badges = ""
        if p["is_admin"]:
            badges += '<span class="badge badge-blue">ADMIN</span> '
        if p["ban_status"] == "ban":
            badges += '<span class="badge badge-red">BANNED</span> '
        elif p["ban_status"] == "timeout":
            badges += '<span class="badge badge-yellow">TIMEOUT</span> '

        try:
            from chat import manager as cm
            online = p["id"] in cm.connections
        except Exception:
            online = False
        dot = '<span style="color:#22c55e;">●</span>' if online else '<span style="color:#475569;">○</span>'

        rows += f'<tr><td>{dot} #{p["id"]}</td><td><a href="/admin/player/{p["id"]}">{p["business_name"]}</a> {badges}</td><td style="color:#22c55e;">${p["cash_balance"]:,.0f}</td><td style="color:#64748b;">{_ts(p["last_login"])}</td></tr>'

    body = f"""
    <h2 style="font-size:0.9rem;margin-bottom:10px;">All Players ({len(players)})</h2>
    {_flash(msg=msg)}
    <div class="card"><div class="table-wrap">
        <table><tr><th>ID</th><th>Name</th><th>Cash</th><th>Last Login</th></tr>{rows}</table>
    </div></div>
    """
    return HTMLResponse(admin_shell("Players", body, player.business_name, "/admin/players"))


# ==========================
# PLAYER DETAIL
# ==========================

@router.get("/admin/player/{pid}", response_class=HTMLResponse)
def admin_player_detail(
    pid: int,
    session_token: Optional[str] = Cookie(None),
    tab: Optional[str] = Query("info"),
    msg: Optional[str] = Query(None),
    err: Optional[str] = Query(None),
):
    admin, redirect = _guard(session_token)
    if redirect:
        return redirect

    detail = get_player_detail(pid)
    if not detail:
        return HTMLResponse(admin_shell("Not Found", '<p style="color:#ef4444;">Player not found.</p>', admin.business_name, "/admin/players"))

    flash = _flash(msg=msg, err=err)

    try:
        from chat import manager as cm
        online = pid in cm.connections
    except Exception:
        online = False
    online_html = '<span style="color:#22c55e;">● Online</span>' if online else '<span style="color:#64748b;">○ Offline</span>'
    admin_badge = ' <span class="badge badge-blue">ADMIN</span>' if detail["is_admin"] else ""

    # Active ban banner
    ban_html = ""
    ab = detail.get("active_ban")
    if ab:
        if ab["type"] == "ban":
            ban_html = f'<div class="flash flash-error">BANNED — {ab["reason"] or "No reason"} <form method="post" action="/admin/player/{pid}/revoke" style="display:inline;margin-left:8px;"><input type="hidden" name="ban_id" value="{ab["id"]}"><button type="submit" class="btn btn-green" style="font-size:0.65rem;padding:3px 6px;">Unban</button></form></div>'
        else:
            ban_html = f'<div class="flash" style="background:#78350f;color:#fcd34d;border:1px solid #92400e;">TIMED OUT until {_ts(ab["expires_at"])} UTC — {ab["reason"] or "No reason"} <form method="post" action="/admin/player/{pid}/revoke" style="display:inline;margin-left:8px;"><input type="hidden" name="ban_id" value="{ab["id"]}"><button type="submit" class="btn btn-green" style="font-size:0.65rem;padding:3px 6px;">Remove</button></form></div>'

    # Tab navigation
    tabs_html = ""
    for t_id, t_label in [("info", "Info"), ("inventory", "Inventory"), ("land", "Land"), ("districts", "Districts"), ("businesses", "Businesses"), ("moderation", "Moderation")]:
        active = ' class="active"' if tab == t_id else ""
        tabs_html += f'<a href="/admin/player/{pid}?tab={t_id}"{active}>{t_label}</a>'

    # Tab content
    tab_body = ""
    if tab == "info":
        tab_body = _player_info_tab(pid, detail)
    elif tab == "inventory":
        tab_body = _player_inventory_tab(pid)
    elif tab == "land":
        tab_body = _player_land_tab(pid)
    elif tab == "districts":
        tab_body = _player_districts_tab(pid)
    elif tab == "businesses":
        tab_body = _player_businesses_tab(pid)
    elif tab == "moderation":
        tab_body = _player_moderation_tab(pid, detail)

    body = f"""
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;flex-wrap:wrap;">
        <a href="/admin/players" style="color:#64748b;font-size:0.75rem;">← Back</a>
        <span style="font-size:0.9rem;font-weight:bold;">#{pid}: {detail["business_name"]}{admin_badge}</span>
        <span style="font-size:0.75rem;">{online_html}</span>
    </div>
    {flash}
    {ban_html}
    <div class="tabs">{tabs_html}</div>
    {tab_body}
    """
    return HTMLResponse(admin_shell(f"Player #{pid}", body, admin.business_name, "/admin/players"))


def _player_info_tab(pid, detail):
    return f"""
    <div class="card">
        <h3>Player Info</h3>
        <div class="detail-row"><span class="label">ID</span><span class="value">#{detail["id"]}</span></div>
        <div class="detail-row"><span class="label">Name</span><span class="value">{detail["business_name"]}</span></div>
        <div class="detail-row"><span class="label">Cash</span><span class="value" style="color:#22c55e;">${detail["cash_balance"]:,.2f}</span></div>
        <div class="detail-row"><span class="label">City</span><span class="value">{detail["city"] or "None"}</span></div>
        <div class="detail-row"><span class="label">Registered</span><span class="value">{_ts(detail["created_at"])}</span></div>
        <div class="detail-row"><span class="label">Last Login</span><span class="value">{_ts(detail["last_login"])}</span></div>
    </div>
    <div class="card">
        <h3>Set Cash Balance</h3>
        <form method="post" action="/admin/player/{pid}/balance">
            <div class="form-row">
                <div><div class="form-label">Amount</div><input type="number" name="new_balance" step="0.01" value="{detail['cash_balance']:.2f}"></div>
                <button type="submit" class="btn btn-blue">Set</button>
            </div>
        </form>
    </div>
    """


def _player_inventory_tab(pid):
    items = get_player_inventory(pid)
    all_types = get_all_item_types()

    rows = ""
    for item in items:
        rows += f"""<tr>
            <td>{item["name"]}</td>
            <td style="color:#22c55e;">{item["quantity"]:,.1f}</td>
            <td>
                <form method="post" action="/admin/player/{pid}/remove-item" style="display:inline;">
                    <input type="hidden" name="item_type" value="{item["item_type"]}">
                    <input type="hidden" name="tab" value="inventory">
                    <div style="display:flex;gap:4px;">
                        <input type="number" name="quantity" step="0.1" min="0.1" value="1" style="width:60px;font-size:0.7rem;">
                        <button type="submit" class="btn btn-red" style="font-size:0.6rem;padding:3px 6px;">Remove</button>
                    </div>
                </form>
            </td>
        </tr>"""

    # Item type options
    opts = "".join(f'<option value="{t}">{t.replace("_"," ").title()}</option>' for t in all_types) if all_types else '<option value="">No item types loaded</option>'

    return f"""
    <div class="card">
        <h3>Add Item</h3>
        <form method="post" action="/admin/player/{pid}/add-item">
            <input type="hidden" name="tab" value="inventory">
            <div class="form-row">
                <div style="flex:2;"><div class="form-label">Item</div><select name="item_type">{opts}</select></div>
                <div style="flex:1;"><div class="form-label">Qty</div><input type="number" name="quantity" step="0.1" min="0.1" value="1"></div>
                <button type="submit" class="btn btn-green">Add</button>
            </div>
        </form>
    </div>
    <div class="card">
        <h3>Current Inventory ({len(items)} items)</h3>
        {f'<div class="table-wrap"><table><tr><th>Item</th><th>Qty</th><th>Action</th></tr>{rows}</table></div>' if rows else '<p style="color:#64748b;font-size:0.75rem;">Empty inventory.</p>'}
    </div>
    """


def _player_land_tab(pid):
    plots = get_player_land(pid)

    # Terrain options for creating new land
    terrains = ["prairie", "forest", "desert", "marsh", "mountain", "tundra", "jungle", "savanna", "hills", "island"]
    terrain_opts = "".join(f'<option value="{t}">{t.title()}</option>' for t in terrains)
    prox_opts = "urban, coastal, riverside, lakeside, oasis, hot_springs, caves, volcanic, road, deposits, remote"

    rows = ""
    for p in plots:
        occupied = f"Biz #{p['occupied_by_business_id']}" if p["occupied_by_business_id"] else '<span style="color:#22c55e;">Vacant</span>'
        features = p["proximity_features"] or "-"
        del_btn = ""
        if not p["occupied_by_business_id"]:
            del_btn = f'<form method="post" action="/admin/player/{pid}/delete-land" style="display:inline;"><input type="hidden" name="plot_id" value="{p["id"]}"><input type="hidden" name="tab" value="land"><button type="submit" class="btn btn-red" style="font-size:0.6rem;padding:3px 6px;">Del</button></form>'
        rows += f'<tr><td>#{p["id"]}</td><td>{p["terrain_type"]}</td><td style="font-size:0.65rem;">{features}</td><td>{p["efficiency"]:.1f}%</td><td>{occupied}</td><td>{del_btn}</td></tr>'

    return f"""
    <div class="card">
        <h3>Create Land Plot</h3>
        <form method="post" action="/admin/player/{pid}/create-land">
            <input type="hidden" name="tab" value="land">
            <div class="form-row">
                <div style="flex:1;"><div class="form-label">Terrain</div><select name="terrain_type">{terrain_opts}</select></div>
                <button type="submit" class="btn btn-green">Create</button>
            </div>
            <div><div class="form-label">Proximity (comma-sep, optional)</div><input type="text" name="proximity" placeholder="{prox_opts}"></div>
        </form>
    </div>
    <div class="card">
        <h3>Land Plots ({len(plots)})</h3>
        {f'<div class="table-wrap"><table><tr><th>ID</th><th>Terrain</th><th>Proximity</th><th>Eff.</th><th>Status</th><th></th></tr>{rows}</table></div>' if rows else '<p style="color:#64748b;font-size:0.75rem;">No land plots.</p>'}
    </div>
    """


def _player_districts_tab(pid):
    districts = get_player_districts(pid)
    rows = ""
    for d in districts:
        occupied = f"Biz #{d['occupied_by_business_id']}" if d["occupied_by_business_id"] else '<span style="color:#22c55e;">Vacant</span>'
        rows += f'<tr><td>#{d["id"]}</td><td>{d["district_type"]}</td><td>{d["terrain_type"]}</td><td>{d["size"]:.1f}</td><td>{d["plots_merged"]}</td><td>${d["monthly_tax"]:,.0f}</td><td>{occupied}</td></tr>'

    return f"""
    <div class="card">
        <h3>Districts ({len(districts)})</h3>
        {f'<div class="table-wrap"><table><tr><th>ID</th><th>Type</th><th>Terrain</th><th>Size</th><th>Plots</th><th>Tax</th><th>Status</th></tr>{rows}</table></div>' if rows else '<p style="color:#64748b;font-size:0.75rem;">No districts.</p>'}
    </div>
    """


def _player_businesses_tab(pid):
    businesses = get_player_businesses(pid)
    rows = ""
    for b in businesses:
        location = f"Plot #{b['land_plot_id']}" if b["land_plot_id"] else (f"District #{b['district_id']}" if b["district_id"] else "-")
        status = '<span style="color:#22c55e;">Active</span>' if b["is_active"] else '<span style="color:#64748b;">Paused</span>'
        rows += f'<tr><td>#{b["id"]}</td><td>{b["business_type"].replace("_"," ").title()}</td><td>{location}</td><td>{status}</td><td>{b["progress_ticks"]}</td></tr>'

    return f"""
    <div class="card">
        <h3>Businesses ({len(businesses)})</h3>
        {f'<div class="table-wrap"><table><tr><th>ID</th><th>Type</th><th>Location</th><th>Status</th><th>Ticks</th></tr>{rows}</table></div>' if rows else '<p style="color:#64748b;font-size:0.75rem;">No businesses.</p>'}
    </div>
    """


def _player_moderation_tab(pid, detail):
    ban_rows = ""
    for b in detail.get("bans", []):
        exp = _ts(b["expires_at"]) if b["expires_at"] else "Never"
        status = '<span style="color:#64748b;">Revoked</span>' if b["revoked"] else '<span style="color:#ef4444;">Active</span>'
        ban_rows += f'<tr><td>#{b["id"]}</td><td>{b["ban_type"].upper()}</td><td style="color:#94a3b8;">{b["reason"] or "-"}</td><td style="color:#64748b;">{_ts(b["created_at"])}</td><td style="color:#64748b;">{exp}</td><td>{status}</td></tr>'

    return f"""
    <div class="card">
        <h3>Kick (disconnect now)</h3>
        <form method="post" action="/admin/player/{pid}/kick">
            <div class="form-row"><div style="flex:1;"><input type="text" name="reason" placeholder="Reason (optional)"></div><button type="submit" class="btn btn-yellow">Kick</button></div>
        </form>
    </div>
    <div class="card">
        <h3>Timeout (temp block)</h3>
        <form method="post" action="/admin/player/{pid}/timeout">
            <div class="form-row">
                <div style="width:80px;flex:0 0 80px;"><div class="form-label">Minutes</div><input type="number" name="minutes" min="1" value="30"></div>
                <div style="flex:1;"><div class="form-label">Reason</div><input type="text" name="reason" placeholder="Optional"></div>
                <button type="submit" class="btn btn-yellow">Timeout</button>
            </div>
        </form>
    </div>
    <div class="card">
        <h3>Ban (permanent)</h3>
        <form method="post" action="/admin/player/{pid}/ban">
            <div class="form-row"><div style="flex:1;"><input type="text" name="reason" placeholder="Reason (optional)"></div><button type="submit" class="btn btn-red">Ban</button></div>
        </form>
    </div>
    <div class="card">
        <h3>History</h3>
        {f'<div class="table-wrap"><table><tr><th>ID</th><th>Type</th><th>Reason</th><th>Date</th><th>Expires</th><th>Status</th></tr>{ban_rows}</table></div>' if ban_rows else '<p style="color:#64748b;font-size:0.75rem;">No moderation history.</p>'}
    </div>
    """


# ==========================
# PLAYER ACTIONS (POST)
# ==========================

@router.post("/admin/player/{pid}/balance")
def post_balance(pid: int, session_token: Optional[str] = Cookie(None), new_balance: float = Form(...)):
    admin, redirect = _guard(session_token)
    if redirect:
        return redirect
    result = edit_player_balance(admin.id, pid, new_balance)
    if result["ok"]:
        return RedirectResponse(url=f"/admin/player/{pid}?tab=info&msg=Balance+set+to+${new_balance:,.2f}", status_code=303)
    return RedirectResponse(url=f"/admin/player/{pid}?tab=info&err={result['error']}", status_code=303)


@router.post("/admin/player/{pid}/add-item")
def post_add_item(pid: int, session_token: Optional[str] = Cookie(None), item_type: str = Form(...), quantity: float = Form(...), tab: str = Form("inventory")):
    admin, redirect = _guard(session_token)
    if redirect:
        return redirect
    result = admin_add_item(admin.id, pid, item_type, quantity)
    if result["ok"]:
        return RedirectResponse(url=f"/admin/player/{pid}?tab={tab}&msg=Added+{quantity:.0f}+{item_type}", status_code=303)
    return RedirectResponse(url=f"/admin/player/{pid}?tab={tab}&err={result['error']}", status_code=303)


@router.post("/admin/player/{pid}/remove-item")
def post_remove_item(pid: int, session_token: Optional[str] = Cookie(None), item_type: str = Form(...), quantity: float = Form(...), tab: str = Form("inventory")):
    admin, redirect = _guard(session_token)
    if redirect:
        return redirect
    result = admin_remove_item(admin.id, pid, item_type, quantity)
    if result["ok"]:
        return RedirectResponse(url=f"/admin/player/{pid}?tab={tab}&msg=Removed+{quantity:.0f}+{item_type}", status_code=303)
    return RedirectResponse(url=f"/admin/player/{pid}?tab={tab}&err={result['error']}", status_code=303)


@router.post("/admin/player/{pid}/create-land")
def post_create_land(pid: int, session_token: Optional[str] = Cookie(None), terrain_type: str = Form(...), proximity: str = Form(""), tab: str = Form("land")):
    admin, redirect = _guard(session_token)
    if redirect:
        return redirect
    result = admin_create_land_plot(admin.id, pid, terrain_type, proximity)
    if result["ok"]:
        return RedirectResponse(url=f"/admin/player/{pid}?tab={tab}&msg=Created+plot+%23{result['plot_id']}", status_code=303)
    return RedirectResponse(url=f"/admin/player/{pid}?tab={tab}&err={result['error']}", status_code=303)


@router.post("/admin/player/{pid}/delete-land")
def post_delete_land(pid: int, session_token: Optional[str] = Cookie(None), plot_id: int = Form(...), tab: str = Form("land")):
    admin, redirect = _guard(session_token)
    if redirect:
        return redirect
    result = admin_delete_land_plot(admin.id, plot_id)
    if result["ok"]:
        return RedirectResponse(url=f"/admin/player/{pid}?tab={tab}&msg=Deleted+plot+%23{plot_id}", status_code=303)
    return RedirectResponse(url=f"/admin/player/{pid}?tab={tab}&err={result['error']}", status_code=303)


@router.post("/admin/player/{pid}/kick")
def post_kick(pid: int, session_token: Optional[str] = Cookie(None), reason: str = Form("")):
    admin, redirect = _guard(session_token)
    if redirect:
        return redirect
    kick_player(admin.id, pid, reason)
    _force_disconnect(pid)
    _invalidate_sessions(pid)
    return RedirectResponse(url=f"/admin/player/{pid}?tab=moderation&msg=Player+kicked", status_code=303)


@router.post("/admin/player/{pid}/timeout")
def post_timeout(pid: int, session_token: Optional[str] = Cookie(None), minutes: int = Form(...), reason: str = Form("")):
    admin, redirect = _guard(session_token)
    if redirect:
        return redirect
    result = timeout_player(admin.id, pid, minutes, reason)
    if not result["ok"]:
        return RedirectResponse(url=f"/admin/player/{pid}?tab=moderation&err={result['error']}", status_code=303)
    _force_disconnect(pid)
    _invalidate_sessions(pid)
    return RedirectResponse(url=f"/admin/player/{pid}?tab=moderation&msg=Timed+out+{minutes}m", status_code=303)


@router.post("/admin/player/{pid}/ban")
def post_ban(pid: int, session_token: Optional[str] = Cookie(None), reason: str = Form("")):
    admin, redirect = _guard(session_token)
    if redirect:
        return redirect
    ban_player(admin.id, pid, reason)
    _force_disconnect(pid)
    _invalidate_sessions(pid)
    return RedirectResponse(url=f"/admin/player/{pid}?tab=moderation&msg=Player+banned", status_code=303)


@router.post("/admin/player/{pid}/revoke")
def post_revoke(pid: int, session_token: Optional[str] = Cookie(None), ban_id: int = Form(...)):
    admin, redirect = _guard(session_token)
    if redirect:
        return redirect
    result = revoke_ban(admin.id, ban_id)
    if result["ok"]:
        return RedirectResponse(url=f"/admin/player/{pid}?tab=moderation&msg=Ban+revoked", status_code=303)
    return RedirectResponse(url=f"/admin/player/{pid}?tab=moderation&err={result['error']}", status_code=303)


def _force_disconnect(pid):
    try:
        from chat import manager as cm
        import asyncio
        ws = cm.connections.get(pid)
        if ws:
            asyncio.create_task(ws.close(code=4002, reason="Admin action"))
    except Exception:
        pass


def _invalidate_sessions(pid):
    try:
        import auth
        db = auth.get_db()
        sessions = db.query(auth.Session).filter(auth.Session.player_id == pid).all()
        for s in sessions:
            auth.active_sessions.pop(s.session_token, None)
            db.delete(s)
        if sessions:
            db.commit()
        db.close()
    except Exception:
        pass


# ==========================
# UPDATES CHANNEL
# ==========================

@router.get("/admin/updates", response_class=HTMLResponse)
def admin_updates(session_token: Optional[str] = Cookie(None), msg: Optional[str] = Query(None)):
    player, redirect = _guard(session_token)
    if redirect:
        return redirect

    from chat import get_room_messages
    messages = get_room_messages("updates", limit=30)
    msg_rows = ""
    for m in messages:
        msg_rows += f'<tr><td style="color:#64748b;">{_ts(m.get("timestamp"))}</td><td style="color:#f59e0b;">{m["sender_name"]}</td><td>{m["content"]}</td></tr>'

    body = f"""
    <h2 style="font-size:0.9rem;margin-bottom:10px;">Updates Channel</h2>
    {_flash(msg=msg)}
    <div class="card">
        <h3>Post New Update</h3>
        <p style="font-size:0.7rem;color:#64748b;margin-bottom:8px;">Appears in the read-only Updates channel for all players.</p>
        <form method="post" action="/admin/updates/post">
            <textarea name="content" rows="3" maxlength="500" placeholder="Type your update..." required style="margin-bottom:8px;"></textarea>
            <button type="submit" class="btn btn-blue">Post Update</button>
        </form>
    </div>
    <div class="card">
        <h3>Recent Updates</h3>
        {f'<div class="table-wrap"><table><tr><th>Time</th><th>From</th><th>Message</th></tr>{msg_rows}</table></div>' if msg_rows else '<p style="color:#64748b;font-size:0.75rem;">No updates posted yet.</p>'}
    </div>
    """
    return HTMLResponse(admin_shell("Updates", body, player.business_name, "/admin/updates"))


@router.post("/admin/updates/post")
def post_update_msg(session_token: Optional[str] = Cookie(None), content: str = Form(...)):
    player, redirect = _guard(session_token)
    if redirect:
        return redirect
    result = post_update(player.id, content.strip())
    if result["ok"]:
        try:
            from chat import manager as cm
            import asyncio
            saved = result["message"]
            saved["type"] = "message"
            saved["avatar"] = cm.avatar_cache.get(player.id)
            asyncio.create_task(cm.broadcast_to_room("updates", saved))
        except Exception:
            pass
        return RedirectResponse(url="/admin/updates?msg=Update+posted", status_code=303)
    return RedirectResponse(url="/admin/updates?msg=Failed", status_code=303)


# ==========================
# CHAT ROOMS
# ==========================

@router.get("/admin/chat", response_class=HTMLResponse)
def admin_chat(session_token: Optional[str] = Cookie(None), room: Optional[str] = Query(None)):
    player, redirect = _guard(session_token)
    if redirect:
        return redirect

    rooms = get_chat_rooms_overview()

    # Room selector
    room_links = ""
    for r in rooms:
        active = ' class="active"' if room == r["id"] else ""
        room_links += f'<a href="/admin/chat?room={r["id"]}"{active}>{r["icon"]} {r["name"]} ({r["online_count"]})</a>'

    # Selected room messages
    messages_html = ""
    if room:
        messages = get_chat_room_messages(room, limit=50)
        room_info = next((r for r in rooms if r["id"] == room), None)
        room_name = room_info["name"] if room_info else room

        msg_items = ""
        for m in messages:
            ts = _ts(m.get("timestamp"))
            msg_items += f'<div class="chat-msg-row"><span class="cm-name">{m["sender_name"]}</span><span class="cm-time">{ts}</span><div class="cm-text">{m["content"]}</div></div>'

        messages_html = f"""
        <div class="card">
            <h3>{room_name} — Messages</h3>
            {msg_items if msg_items else '<p style="color:#64748b;font-size:0.75rem;">No messages.</p>'}
        </div>
        """
    else:
        messages_html = '<p style="color:#64748b;font-size:0.75rem;">Select a room above to view messages.</p>'

    body = f"""
    <h2 style="font-size:0.9rem;margin-bottom:10px;">Chat Rooms</h2>
    <div class="tabs">{room_links}</div>
    {messages_html}
    <div class="card">
        <h3>DMs</h3>
        <p style="color:#64748b;font-size:0.75rem;">Direct message system is not yet implemented. When DMs are added, admin monitoring will be available here.</p>
    </div>
    """
    return HTMLResponse(admin_shell("Chat", body, player.business_name, "/admin/chat"))


# ==========================
# P2P OVERVIEW
# ==========================

@router.get("/admin/p2p", response_class=HTMLResponse)
def admin_p2p(session_token: Optional[str] = Cookie(None)):
    player, redirect = _guard(session_token)
    if redirect:
        return redirect

    overview = get_p2p_overview()
    if "error" in overview:
        body = f'<h2 style="font-size:0.9rem;margin-bottom:10px;">P2P Contracts</h2><div class="card"><p style="color:#64748b;">P2P module error: {overview["error"]}</p></div>'
        return HTMLResponse(admin_shell("P2P", body, player.business_name, "/admin/p2p"))

    recent_rows = ""
    for c in overview.get("recent", []):
        sc_map = {"active": "#22c55e", "listed": "#38bdf8", "breached": "#ef4444", "completed": "#64748b", "draft": "#94a3b8", "voided": "#64748b"}
        sc = sc_map.get(c["status"], "#94a3b8")
        holder = f'#{c["holder_id"]}' if c["holder_id"] else "-"
        recent_rows += f'<tr><td>#{c["id"]}</td><td>#{c["creator_id"]}</td><td>{holder}</td><td style="color:{sc};">{c["status"].upper()}</td><td>{c["bid_mode"] or "-"}</td><td style="color:#64748b;">{_ts(c["created_at"])}</td></tr>'

    body = f"""
    <h2 style="font-size:0.9rem;margin-bottom:10px;">P2P Contracts</h2>
    <div class="stat-grid">
        <div class="stat-box"><div class="stat-value">{overview.get("total",0)}</div><div class="stat-label">Total</div></div>
        <div class="stat-box"><div class="stat-value" style="color:#22c55e;">{overview.get("active",0)}</div><div class="stat-label">Active</div></div>
        <div class="stat-box"><div class="stat-value" style="color:#38bdf8;">{overview.get("listed",0)}</div><div class="stat-label">Listed</div></div>
        <div class="stat-box"><div class="stat-value" style="color:#ef4444;">{overview.get("breached",0)}</div><div class="stat-label">Breached</div></div>
    </div>
    <div class="card">
        <h3>Recent Contracts</h3>
        {f'<div class="table-wrap"><table><tr><th>ID</th><th>Creator</th><th>Holder</th><th>Status</th><th>Mode</th><th>Created</th></tr>{recent_rows}</table></div>' if recent_rows else '<p style="color:#64748b;font-size:0.75rem;">No contracts.</p>'}
    </div>
    """
    return HTMLResponse(admin_shell("P2P", body, player.business_name, "/admin/p2p"))


# ==========================
# LAND BANK
# ==========================

@router.get("/admin/landbank", response_class=HTMLResponse)
def admin_landbank(session_token: Optional[str] = Cookie(None), msg: Optional[str] = Query(None), err: Optional[str] = Query(None)):
    player, redirect = _guard(session_token)
    if redirect:
        return redirect

    entries = get_land_bank_entries()

    terrains = ["prairie", "forest", "desert", "marsh", "mountain", "tundra", "jungle", "savanna", "hills", "island"]
    terrain_opts = "".join(f'<option value="{t}">{t.title()}</option>' for t in terrains)

    rows = ""
    for e in entries:
        price = f'${e["last_auction_price"]:,.0f}' if e["last_auction_price"] else "-"
        rows += f"""<tr>
            <td>#{e["land_plot_id"]}</td>
            <td>{e["terrain_type"]}</td>
            <td style="font-size:0.65rem;">{e["proximity_features"] or "-"}</td>
            <td>{e["times_auctioned"]}</td>
            <td>{price}</td>
            <td style="color:#64748b;">{_ts(e["added_at"])}</td>
            <td>
                <form method="post" action="/admin/landbank/remove" style="display:inline;">
                    <input type="hidden" name="land_plot_id" value="{e["land_plot_id"]}">
                    <button type="submit" name="delete_plot" value="false" class="btn btn-gray" style="font-size:0.6rem;padding:3px 5px;">Remove</button>
                    <button type="submit" name="delete_plot" value="true" class="btn btn-red" style="font-size:0.6rem;padding:3px 5px;">Delete</button>
                </form>
            </td>
        </tr>"""

    body = f"""
    <h2 style="font-size:0.9rem;margin-bottom:10px;">Land Bank ({len(entries)} plots)</h2>
    {_flash(msg=msg, err=err)}
    <div class="card">
        <h3>Add Plot to Land Bank</h3>
        <p style="font-size:0.7rem;color:#64748b;margin-bottom:8px;">Creates a new government-owned plot and adds it to the land bank.</p>
        <form method="post" action="/admin/landbank/add">
            <div class="form-row">
                <div style="flex:1;"><div class="form-label">Terrain</div><select name="terrain_type">{terrain_opts}</select></div>
                <button type="submit" class="btn btn-green">Add</button>
            </div>
            <div><div class="form-label">Proximity (comma-sep, optional)</div><input type="text" name="proximity" placeholder="coastal, riverside, urban..."></div>
        </form>
    </div>
    <div class="card">
        <h3>Plots in Bank</h3>
        {f'<div class="table-wrap"><table><tr><th>Plot</th><th>Terrain</th><th>Proximity</th><th>Auctions</th><th>Last Price</th><th>Added</th><th>Action</th></tr>{rows}</table></div>' if rows else '<p style="color:#64748b;font-size:0.75rem;">Land bank is empty.</p>'}
        <p style="font-size:0.65rem;color:#475569;margin-top:8px;"><b>Remove</b> = take out of bank (keep plot). <b>Delete</b> = remove from bank AND delete the plot.</p>
    </div>
    """
    return HTMLResponse(admin_shell("Land Bank", body, player.business_name, "/admin/landbank"))


@router.post("/admin/landbank/add")
def post_landbank_add(session_token: Optional[str] = Cookie(None), terrain_type: str = Form(...), proximity: str = Form("")):
    admin, redirect = _guard(session_token)
    if redirect:
        return redirect
    result = admin_add_to_land_bank(admin.id, terrain_type, proximity)
    if result["ok"]:
        return RedirectResponse(url=f"/admin/landbank?msg=Plot+%23{result['plot_id']}+added", status_code=303)
    return RedirectResponse(url=f"/admin/landbank?err={result['error']}", status_code=303)


@router.post("/admin/landbank/remove")
def post_landbank_remove(session_token: Optional[str] = Cookie(None), land_plot_id: int = Form(...), delete_plot: str = Form("false")):
    admin, redirect = _guard(session_token)
    if redirect:
        return redirect
    do_delete = delete_plot == "true"
    result = admin_remove_from_land_bank(admin.id, land_plot_id, delete_plot=do_delete)
    if result["ok"]:
        action = "Deleted" if do_delete else "Removed"
        return RedirectResponse(url=f"/admin/landbank?msg={action}+plot+%23{land_plot_id}", status_code=303)
    return RedirectResponse(url=f"/admin/landbank?err={result['error']}", status_code=303)


# ==========================
# AUDIT LOG
# ==========================

@router.get("/admin/logs", response_class=HTMLResponse)
def admin_logs(session_token: Optional[str] = Cookie(None)):
    player, redirect = _guard(session_token)
    if redirect:
        return redirect

    logs = get_admin_logs(limit=100)
    rows = ""
    for log in logs:
        target = f'<a href="/admin/player/{log["target_player_id"]}">#{log["target_player_id"]}</a>' if log["target_player_id"] else "-"
        ac_map = {"ban": "#ef4444", "kick": "#f59e0b", "timeout": "#f59e0b", "revoke_ban": "#22c55e", "edit_balance": "#38bdf8", "post_update": "#a78bfa", "add_item": "#22c55e", "remove_item": "#ef4444", "create_land": "#22c55e", "delete_land": "#ef4444", "add_land_bank": "#22c55e", "remove_land_bank": "#ef4444"}
        ac = ac_map.get(log["action"], "#94a3b8")
        rows += f'<tr><td style="color:#64748b;">{_ts(log["created_at"])}</td><td>#{log["admin_id"]}</td><td style="color:{ac};font-weight:bold;">{log["action"].upper()}</td><td>{target}</td><td style="color:#94a3b8;max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{log["details"]}</td></tr>'

    body = f"""
    <h2 style="font-size:0.9rem;margin-bottom:10px;">Audit Log</h2>
    <div class="card"><div class="table-wrap">
        {f'<table><tr><th>Time</th><th>Admin</th><th>Action</th><th>Target</th><th>Details</th></tr>{rows}</table>' if rows else '<p style="color:#64748b;font-size:0.75rem;">No actions recorded.</p>'}
    </div></div>
    """
    return HTMLResponse(admin_shell("Logs", body, player.business_name, "/admin/logs"))
