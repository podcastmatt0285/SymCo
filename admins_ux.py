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
import re
import os
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Cookie, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse

from admins import (
    ADMIN_PLAYER_IDS,
    is_admin, require_admin, is_moderator, require_moderator,
    get_all_players, get_player_detail, edit_player_balance,
    get_player_inventory, admin_add_item, admin_remove_item, get_all_item_types,
    get_player_land, admin_delete_land_plot, admin_create_land_plot,
    get_player_districts, get_player_businesses,
    get_land_bank_entries, admin_add_to_land_bank, admin_remove_from_land_bank,
    get_chat_rooms_overview, get_chat_room_messages, admin_delete_chat_message,
    ban_player, timeout_player, kick_player, revoke_ban, get_active_ban,
    post_update, get_p2p_overview, get_admin_logs, log_action,
    get_dm_threads_overview, get_dm_thread_messages,
    # District admin
    admin_create_district, admin_delete_district, admin_edit_district_tax,
    # City admin
    admin_create_city,
    get_all_cities_admin, get_player_city_info,
    admin_add_player_to_city, admin_remove_player_from_city,
    admin_get_city_polls, admin_resolve_city_poll,
    admin_get_city_projects, admin_force_complete_project,
    admin_set_project_level, admin_set_project_status,
    admin_deconstruct_project, admin_construct_project,
    # County admin
    get_all_counties_admin, get_player_county_info,
    admin_add_city_to_county, admin_remove_city_from_county,
    admin_get_county_polls, admin_resolve_county_poll,
    # Moderator management
    add_moderator, remove_moderator, get_all_moderators,
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
        ("/admin/cities", "Cities"),
        ("/admin/moderators", "Moderators"),
        ("/admin/updates", "Updates"),
        ("/admin/chat", "Chat"),
        ("/admin/p2p", "P2P"),
        ("/admin/landbank", "Land Bank"),
        ("/admin/etf", "ETF Banks"),
        ("/admin/logs", "Logs"),
        ("/admin/wiki", "Wiki Media"),
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
                <a href="/" style="color: #94a3b8;">Game</a>
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
    """Full admin required."""
    player = require_admin(session_token)
    if not player:
        return None, RedirectResponse(url="/login", status_code=303)
    return player, None


def _mod_guard(session_token):
    """Admin OR moderator. Returns (player, is_full_admin, redirect)."""
    player, is_full = require_moderator(session_token)
    if not player:
        return None, False, RedirectResponse(url="/login", status_code=303)
    return player, is_full, None


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
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)

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
        <div class="stat-box"><div class="stat-value" style="color:#22c55e;">{fmt_usd(total_cash, disp, precision=0)}</div><div class="stat-label">Total Cash</div></div>
        <div class="stat-box"><div class="stat-value" style="color:#ef4444;">{banned_count}</div><div class="stat-label">Banned</div></div>
    </div>

    <div class="link-grid" style="margin-bottom: 12px;">
        <a href="/admin/updates" class="link-card"><div class="lc-icon">📢</div><div class="lc-title">Post Update</div><div class="lc-desc">Updates channel</div></a>
        <a href="/admin/players" class="link-card"><div class="lc-icon">👥</div><div class="lc-title">Players</div><div class="lc-desc">View &amp; edit all</div></a>
        <a href="/admin/cities" class="link-card"><div class="lc-icon">🏙️</div><div class="lc-title">Cities &amp; Counties</div><div class="lc-desc">Manage memberships</div></a>
        <a href="/admin/chat" class="link-card"><div class="lc-icon">💬</div><div class="lc-title">Chat Rooms</div><div class="lc-desc">Monitor chat</div></a>
        <a href="/admin/p2p" class="link-card"><div class="lc-icon">📋</div><div class="lc-title">P2P Contracts</div><div class="lc-desc">View activity</div></a>
        <a href="/admin/landbank" class="link-card"><div class="lc-icon">🏦</div><div class="lc-title">Land Bank</div><div class="lc-desc">Manage plots</div></a>
        <a href="/admin/etf" class="link-card"><div class="lc-icon">📈</div><div class="lc-title">ETF Banks</div><div class="lc-desc">Share audit &amp; repair</div></a>
        <a href="/admin/logs" class="link-card"><div class="lc-icon">📜</div><div class="lc-title">Audit Log</div><div class="lc-desc">Admin actions</div></a>
        <a href="/admin/wiki" class="link-card"><div class="lc-icon">📖</div><div class="lc-title">Wiki / Media</div><div class="lc-desc">Tutorial videos &amp; audio</div></a>
        <a href="/admin/soundtrack" class="link-card"><div class="lc-icon">🎵</div><div class="lc-title">WLOL 92.8 FM</div><div class="lc-desc">Music playlist uploads</div></a>
        <a href="/admin/wcpr" class="link-card"><div class="lc-icon">📻</div><div class="lc-title">WCPR 104.1 FM</div><div class="lc-desc">Talk radio uploads</div></a>
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
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)

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

        rows += f'<tr><td>{dot} #{p["id"]}</td><td><a href="/admin/player/{p["id"]}">{p["business_name"]}</a> {badges}</td><td style="color:#22c55e;">{fmt_usd(p["cash_balance"], disp, precision=0)}</td><td style="color:#64748b;">{_ts(p["last_login"])}</td></tr>'

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
    admin, is_full, redirect = _mod_guard(session_token)
    if redirect:
        return redirect
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(admin.id)

    # Moderators can only access the moderation tab
    if not is_full:
        tab = "moderation"

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

    # Tab navigation — moderators only see the Moderation tab
    if is_full:
        tab_list = [("info", "Info"), ("inventory", "Inventory"), ("land", "Land"), ("districts", "Districts"), ("cities", "City/County"), ("businesses", "Businesses"), ("moderation", "Moderation"), ("linked", "Linked Accounts")]
    else:
        tab_list = [("moderation", "Moderation")]
    tabs_html = ""
    for t_id, t_label in tab_list:
        active = ' class="active"' if tab == t_id else ""
        tabs_html += f'<a href="/admin/player/{pid}?tab={t_id}"{active}>{t_label}</a>'

    # Tab content
    tab_body = ""
    if tab == "info" and is_full:
        tab_body = _player_info_tab(pid, detail, disp)
    elif tab == "inventory" and is_full:
        tab_body = _player_inventory_tab(pid)
    elif tab == "land" and is_full:
        tab_body = _player_land_tab(pid)
    elif tab == "districts" and is_full:
        tab_body = _player_districts_tab(pid)
    elif tab == "cities" and is_full:
        tab_body = _player_cities_tab(pid)
    elif tab == "businesses" and is_full:
        tab_body = _player_businesses_tab(pid)
    elif tab == "moderation":
        tab_body = _player_moderation_tab(pid, detail, is_full_admin=is_full)
    elif tab == "linked" and is_full:
        tab_body = _player_linked_tab(pid)

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


def _player_info_tab(pid, detail, disp=None):
    from reserve_banks import get_player_display_currency, fmt_usd
    if disp is None:
        disp = get_player_display_currency(pid)
    return f"""
    <div class="card">
        <h3>Player Info</h3>
        <div class="detail-row"><span class="label">ID</span><span class="value">#{detail["id"]}</span></div>
        <div class="detail-row"><span class="label">Name</span><span class="value">{detail["business_name"]}</span></div>
        <div class="detail-row"><span class="label">Cash</span><span class="value" style="color:#22c55e;">{fmt_usd(detail["cash_balance"], disp)}</span></div>
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
        <div style="margin-top:24px;border-top:1px solid #7f1d1d;padding-top:16px;">
          <p style="color:#ef4444;font-size:0.85rem;margin:0 0 10px 0;">⚠️ Delete permanently triggers the estate/death liquidation for this player.</p>
          <form method="post" action="/admin/player/{pid}/delete" onsubmit="return confirm('Permanently trigger death/estate for player {pid}? This cannot be undone.')">
            <button type="submit" style="background:#7f1d1d;color:#fca5a5;border:1px solid #ef4444;padding:8px 18px;border-radius:4px;cursor:pointer;font-weight:bold;">💀 Delete Player (Trigger Death)</button>
          </form>
        </div>
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
    from reserve_banks import fmt_usd
    districts = get_player_districts(pid)
    _usd_disp = {"code": "USD", "symbol": "$", "usd_per_unit": 1.0, "flag": "🇺🇸"}

    try:
        from districts import DISTRICT_TYPES
        dist_type_opts = "".join(
            f'<option value="{k}">{v["name"]} — {fmt_usd(v["base_tax"], _usd_disp, precision=0)}/mo base</option>'
            for k, v in sorted(DISTRICT_TYPES.items(), key=lambda x: x[1]["name"])
        )
    except Exception:
        dist_type_opts = '<option value="industrial">industrial</option>'

    rows = ""
    for d in districts:
        did = d["id"]
        occupied = f"Biz #{d['occupied_by_business_id']}" if d["occupied_by_business_id"] else '<span style="color:#22c55e;">Vacant</span>'
        rows += f"""<tr>
            <td>#{did}</td>
            <td>{d["district_type"]}</td>
            <td style="color:#94a3b8;">{d["terrain_type"]}</td>
            <td>{d["size"]:.1f}</td>
            <td>{fmt_usd(d["monthly_tax"], _usd_disp, precision=0)}</td>
            <td>{occupied}</td>
            <td>
                <form method="post" action="/admin/player/{pid}/edit-district-tax" style="display:inline;margin-right:4px;">
                    <input type="hidden" name="district_id" value="{did}">
                    <input type="hidden" name="tab" value="districts">
                    <div style="display:flex;gap:3px;align-items:center;">
                        <input type="number" name="new_tax" step="1000" min="0" value="{d['monthly_tax']:.0f}" style="width:90px;font-size:0.7rem;">
                        <button type="submit" class="btn btn-blue" style="font-size:0.6rem;padding:3px 5px;">Tax</button>
                    </div>
                </form>
                <form method="post" action="/admin/player/{pid}/delete-district" style="display:inline;">
                    <input type="hidden" name="district_id" value="{did}">
                    <input type="hidden" name="tab" value="districts">
                    <button type="submit" class="btn btn-red" style="font-size:0.6rem;padding:3px 5px;" onclick="return confirm('Delete district #{did}?')">Del</button>
                </form>
            </td>
        </tr>"""

    return f"""
    <div class="card">
        <h3>Grant District</h3>
        <form method="post" action="/admin/player/{pid}/create-district">
            <input type="hidden" name="tab" value="districts">
            <div class="form-row">
                <div style="flex:2;"><div class="form-label">Type</div><select name="district_type">{dist_type_opts}</select></div>
                <div style="flex:0 0 80px;"><div class="form-label">Size</div><input type="number" name="size" min="1" step="1" value="5"></div>
                <button type="submit" class="btn btn-green">Grant</button>
            </div>
        </form>
    </div>
    <div class="card">
        <h3>Districts ({len(districts)})</h3>
        {f'<div class="table-wrap"><table><tr><th>ID</th><th>Type</th><th>Terrain</th><th>Size</th><th>Tax/mo</th><th>Status</th><th>Actions</th></tr>{rows}</table></div>' if rows else '<p style="color:#64748b;font-size:0.75rem;">No districts.</p>'}
    </div>
    """


def _player_cities_tab(pid):
    city_info = get_player_city_info(pid)
    county_info = get_player_county_info(pid)
    all_cities = get_all_cities_admin()

    city_opts = "".join(
        '<option value="' + str(c["id"]) + '">#' + str(c["id"]) + " — " + c["name"] + " (" + str(c.get("member_count", 0)) + " members)</option>"
        for c in all_cities
    ) if all_cities else '<option value="">No cities exist</option>'

    if city_info:
        role = "Mayor" if city_info.get("is_mayor") else "Member"
        city_id_str = str(city_info["id"])
        city_name_str = city_info["name"]
        if city_info.get("is_mayor"):
            remove_action = '<div class="flash flash-error" style="margin-top:6px;">Cannot remove the mayor — reassign mayor in-game first.</div>'
        else:
            remove_action = (
                '<form method="post" action="/admin/player/' + str(pid) + '/remove-from-city" style="margin-top:8px;">'
                '<input type="hidden" name="tab" value="cities">'
                '<button type="submit" class="btn btn-red" onclick="return confirm(\'Force-remove from city?\')">Force Remove from City</button>'
                '</form>'
            )
        city_html = (
            '<div class="detail-row"><span class="label">City</span><span class="value">#' + city_id_str + " — " + city_name_str + "</span></div>"
            '<div class="detail-row"><span class="label">Role</span><span class="value">' + role + "</span></div>"
            + remove_action
        )
    else:
        city_html = (
            '<p style="color:#64748b;font-size:0.75rem;margin-bottom:10px;">Player is not in any city.</p>'
            '<form method="post" action="/admin/player/' + str(pid) + '/add-to-city">'
            '<input type="hidden" name="tab" value="cities">'
            '<div class="form-row">'
            '<div style="flex:1;"><div class="form-label">City</div><select name="city_id">' + city_opts + "</select></div>"
            '<button type="submit" class="btn btn-green">Force Add</button>'
            "</div></form>"
        )

    if county_info:
        county_html = (
            '<div class="detail-row"><span class="label">County</span><span class="value">#'
            + str(county_info["id"]) + " — " + county_info["name"] + "</span></div>"
            '<div class="detail-row"><span class="label">Token</span><span class="value">'
            + county_info.get("crypto_symbol", "-") + "</span></div>"
        )
    else:
        county_html = "<p style=\"color:#64748b;font-size:0.75rem;\">Player's city is not in a county (or player has no city).</p>"

    return f"""
    <div class="card">
        <h3>City Membership</h3>
        {city_html}
    </div>
    <div class="card">
        <h3>County</h3>
        {county_html}
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


def _player_linked_tab(pid: int) -> str:
    """Show all accounts that share a registration or login IP with this player."""
    try:
        from admins import get_related_accounts
        accounts = get_related_accounts(pid)
    except Exception as e:
        return f'<div class="card"><p style="color:#ef4444;">Error loading linked accounts: {e}</p></div>'

    if not accounts:
        return '<div class="card"><h3>Linked Accounts</h3><p style="color:#64748b;font-size:0.8rem;">No shared IPs found. This account appears to have a unique fingerprint.</p></div>'

    rows = ""
    for a in accounts:
        ban_badge = ' <span class="badge badge-red">BANNED</span>' if a["is_banned"] else ""
        link_color = {
            "registration": "#ef4444",
            "login":        "#f59e0b",
            "reg→login":    "#f97316",
        }.get(a["link_type"], "#94a3b8")
        rows += (
            f'<tr>'
            f'<td><a href="/admin/player/{a["player_id"]}" style="color:#38bdf8;">#{a["player_id"]}</a></td>'
            f'<td><a href="/admin/player/{a["player_id"]}" style="color:#e2e8f0;">{a["business_name"]}</a>{ban_badge}</td>'
            f'<td style="color:#64748b;font-size:0.75rem;">{a["shared_ip"]}</td>'
            f'<td><span style="color:{link_color};font-size:0.75rem;font-weight:bold;">{a["link_type"].upper()}</span></td>'
            f'<td style="color:#64748b;font-size:0.75rem;">{a["seen_at"][:16].replace("T"," ") if a["seen_at"] else "-"}</td>'
            f'<td>'
            f'<form method="post" action="/admin/player/{a["player_id"]}/ban" style="display:inline;">'
            f'<input type="hidden" name="reason" value="Alt account — linked to #{pid} via shared IP">'
            f'<button type="submit" class="btn btn-red" style="font-size:0.65rem;padding:2px 6px;"'
            f'{"disabled" if a["is_banned"] else ""}>Ban</button></form>'
            f'</td>'
            f'</tr>'
        )

    legend = (
        '<p style="font-size:0.72rem;color:#64748b;margin-top:10px;">'
        '<span style="color:#ef4444;">■</span> REGISTRATION — same IP at sign-up &nbsp;|&nbsp; '
        '<span style="color:#f59e0b;">■</span> LOGIN — same IP used to log in &nbsp;|&nbsp; '
        '<span style="color:#f97316;">■</span> REG→LOGIN — this account\'s reg IP matches another account\'s login IP'
        '</p>'
    )

    return f"""
    <div class="card">
        <h3>Linked Accounts <span style="font-size:0.7rem;color:#64748b;">({len(accounts)} found)</span></h3>
        <p style="font-size:0.75rem;color:#94a3b8;margin-bottom:10px;">
            Accounts sharing a registration or login IP address with this player.
            Shared IPs may indicate alternate accounts or shared networks (VPN, household, school).
        </p>
        <div class="table-wrap">
            <table>
                <tr><th>ID</th><th>Account</th><th>Shared IP</th><th>Link Type</th><th>Last Seen</th><th>Action</th></tr>
                {rows}
            </table>
        </div>
        {legend}
    </div>
    """


def _player_moderation_tab(pid, detail, is_full_admin: bool = True):
    ban_rows = ""
    for b in detail.get("bans", []):
        exp = _ts(b["expires_at"]) if b["expires_at"] else "Never"
        if b["revoked"]:
            status = '<span style="color:#64748b;">Revoked</span>'
            revoke_btn = ""
        else:
            status = '<span style="color:#ef4444;">Active</span>'
            revoke_btn = f'<form method="post" action="/admin/player/{pid}/revoke" style="display:inline;margin-left:6px;"><input type="hidden" name="ban_id" value="{b["id"]}"><button type="submit" class="btn btn-green" style="font-size:0.65rem;padding:2px 6px;">Revoke</button></form>'
        ban_rows += f'<tr><td>#{b["id"]}</td><td>{b["ban_type"].upper()}</td><td style="color:#94a3b8;">{b["reason"] or "-"}</td><td style="color:#64748b;">{_ts(b["created_at"])}</td><td style="color:#64748b;">{exp}</td><td>{status}{revoke_btn}</td></tr>'

    ban_form = ""
    if is_full_admin:
        ban_form = f"""
    <div class="card">
        <h3>Ban (permanent) <span style="font-size:0.7rem;color:#ef4444;">Admin Only</span></h3>
        <form method="post" action="/admin/player/{pid}/ban">
            <div class="form-row"><div style="flex:1;"><input type="text" name="reason" placeholder="Reason (optional)"></div><button type="submit" class="btn btn-red">Ban</button></div>
        </form>
    </div>"""

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
    {ban_form}
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
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(admin.id)
    result = edit_player_balance(admin.id, pid, new_balance)
    if result["ok"]:
        return RedirectResponse(url=f"/admin/player/{pid}?tab=info&msg=Balance+set+to+{fmt_usd(new_balance, disp)}", status_code=303)
    return RedirectResponse(url=f"/admin/player/{pid}?tab=info&err={result['error']}", status_code=303)


@router.post("/admin/player/{pid}/add-item")
def post_add_item(pid: int, session_token: Optional[str] = Cookie(None), item_type: str = Form(...), quantity: float = Form(...), tab: str = Form("inventory")):
    admin, redirect = _guard(session_token)
    if redirect:
        return redirect
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(admin.id)
    result = admin_add_item(admin.id, pid, item_type, quantity)
    if result["ok"]:
        return RedirectResponse(url=f"/admin/player/{pid}?tab={tab}&msg=Added+{quantity:.0f}+{item_type}", status_code=303)
    return RedirectResponse(url=f"/admin/player/{pid}?tab={tab}&err={result['error']}", status_code=303)


@router.post("/admin/player/{pid}/remove-item")
def post_remove_item(pid: int, session_token: Optional[str] = Cookie(None), item_type: str = Form(...), quantity: float = Form(...), tab: str = Form("inventory")):
    admin, redirect = _guard(session_token)
    if redirect:
        return redirect
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(admin.id)
    result = admin_remove_item(admin.id, pid, item_type, quantity)
    if result["ok"]:
        return RedirectResponse(url=f"/admin/player/{pid}?tab={tab}&msg=Removed+{quantity:.0f}+{item_type}", status_code=303)
    return RedirectResponse(url=f"/admin/player/{pid}?tab={tab}&err={result['error']}", status_code=303)


@router.post("/admin/player/{pid}/create-land")
def post_create_land(pid: int, session_token: Optional[str] = Cookie(None), terrain_type: str = Form(...), proximity: str = Form(""), tab: str = Form("land")):
    admin, redirect = _guard(session_token)
    if redirect:
        return redirect
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(admin.id)
    result = admin_create_land_plot(admin.id, pid, terrain_type, proximity)
    if result["ok"]:
        return RedirectResponse(url=f"/admin/player/{pid}?tab={tab}&msg=Created+plot+%23{result['plot_id']}", status_code=303)
    return RedirectResponse(url=f"/admin/player/{pid}?tab={tab}&err={result['error']}", status_code=303)


@router.post("/admin/player/{pid}/delete-land")
def post_delete_land(pid: int, session_token: Optional[str] = Cookie(None), plot_id: int = Form(...), tab: str = Form("land")):
    admin, redirect = _guard(session_token)
    if redirect:
        return redirect
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(admin.id)
    result = admin_delete_land_plot(admin.id, plot_id)
    if result["ok"]:
        return RedirectResponse(url=f"/admin/player/{pid}?tab={tab}&msg=Deleted+plot+%23{plot_id}", status_code=303)
    return RedirectResponse(url=f"/admin/player/{pid}?tab={tab}&err={result['error']}", status_code=303)


@router.post("/admin/player/{pid}/create-district")
def post_create_district(pid: int, session_token: Optional[str] = Cookie(None), district_type: str = Form(...), size: float = Form(5.0), tab: str = Form("districts")):
    admin, redirect = _guard(session_token)
    if redirect:
        return redirect
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(admin.id)
    result = admin_create_district(admin.id, pid, district_type, size)
    if result["ok"]:
        return RedirectResponse(url=f"/admin/player/{pid}?tab={tab}&msg=Created+{district_type}+district+%23{result['district_id']}", status_code=303)
    return RedirectResponse(url=f"/admin/player/{pid}?tab={tab}&err={result['error']}", status_code=303)


@router.post("/admin/player/{pid}/delete-district")
def post_delete_district(pid: int, session_token: Optional[str] = Cookie(None), district_id: int = Form(...), tab: str = Form("districts")):
    admin, redirect = _guard(session_token)
    if redirect:
        return redirect
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(admin.id)
    result = admin_delete_district(admin.id, district_id)
    if result["ok"]:
        return RedirectResponse(url=f"/admin/player/{pid}?tab={tab}&msg=Deleted+district+%23{district_id}", status_code=303)
    return RedirectResponse(url=f"/admin/player/{pid}?tab={tab}&err={result['error']}", status_code=303)


@router.post("/admin/player/{pid}/edit-district-tax")
def post_edit_district_tax(pid: int, session_token: Optional[str] = Cookie(None), district_id: int = Form(...), new_tax: float = Form(...), tab: str = Form("districts")):
    admin, redirect = _guard(session_token)
    if redirect:
        return redirect
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(admin.id)
    result = admin_edit_district_tax(admin.id, district_id, new_tax)
    if result["ok"]:
        return RedirectResponse(url=f"/admin/player/{pid}?tab={tab}&msg=Tax+updated+for+district+%23{district_id}", status_code=303)
    return RedirectResponse(url=f"/admin/player/{pid}?tab={tab}&err={result['error']}", status_code=303)


@router.post("/admin/player/{pid}/add-to-city")
def post_add_to_city(pid: int, session_token: Optional[str] = Cookie(None), city_id: int = Form(...), tab: str = Form("cities")):
    admin, redirect = _guard(session_token)
    if redirect:
        return redirect
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(admin.id)
    result = admin_add_player_to_city(admin.id, pid, city_id)
    if result["ok"]:
        return RedirectResponse(url=f"/admin/player/{pid}?tab={tab}&msg=Added+to+city+%23{city_id}", status_code=303)
    return RedirectResponse(url=f"/admin/player/{pid}?tab={tab}&err={result['error']}", status_code=303)


@router.post("/admin/player/{pid}/remove-from-city")
def post_remove_from_city(pid: int, session_token: Optional[str] = Cookie(None), tab: str = Form("cities")):
    admin, redirect = _guard(session_token)
    if redirect:
        return redirect
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(admin.id)
    result = admin_remove_player_from_city(admin.id, pid)
    if result["ok"]:
        return RedirectResponse(url=f"/admin/player/{pid}?tab={tab}&msg=Removed+from+city", status_code=303)
    return RedirectResponse(url=f"/admin/player/{pid}?tab={tab}&err={result['error']}", status_code=303)


# ==========================
# CITIES OVERVIEW
# ==========================

@router.get("/admin/cities", response_class=HTMLResponse)
def admin_cities(session_token: Optional[str] = Cookie(None), msg: Optional[str] = Query(None), err: Optional[str] = Query(None)):
    admin, redirect = _guard(session_token)
    if redirect:
        return redirect
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(admin.id)

    cities = get_all_cities_admin()
    counties = get_all_counties_admin()
    all_players = get_all_players()

    city_opts_county = "".join(f'<option value="{c["id"]}">#{c["id"]} — {c["name"]}</option>' for c in cities)
    county_opts = "".join(f'<option value="{cn["id"]}">#{cn["id"]} — {cn["name"]} ({cn.get("city_count",0)} cities)</option>' for cn in counties)
    player_opts = "".join(f'<option value="{p["id"]}">#{p["id"]} — {p["business_name"]}</option>' for p in all_players)

    city_rows = ""
    for c in cities:
        county_link = ""
        for cn in counties:
            if any(cc == c["id"] for cc in cn.get("city_ids", [])):
                county_link = f'<a href="/admin/counties">#{cn["id"]} {cn["name"]}</a>'
                break
        city_rows += f"""<tr>
            <td>#{c["id"]}</td>
            <td><a href="/admin/cities/{c['id']}">{c["name"]}</a></td>
            <td>{c.get("mayor_name", "-")}</td>
            <td>{c.get("member_count", 0)}</td>
            <td>{county_link or '<span style="color:#64748b;">—</span>'}</td>
            <td style="color:#22c55e;">{fmt_usd(c.get("bank_reserves", 0), disp, precision=0)}</td>
        </tr>"""

    county_rows = ""
    for cn in counties:
        county_rows += f"""<tr>
            <td>#{cn["id"]}</td>
            <td><a href="/admin/counties/{cn['id']}">{cn["name"]}</a></td>
            <td style="font-weight:bold;color:#f59e0b;">{cn.get("crypto_symbol","?")}</td>
            <td>{cn.get("city_count", 0)}</td>
            <td style="color:#94a3b8;">{cn.get("total_supply", 0):,.0f}</td>
            <td>
                <form method="post" action="/admin/counties/remove-city" style="display:inline;">
                    <input type="number" name="city_id" placeholder="City ID" style="width:70px;font-size:0.7rem;display:inline;">
                    <input type="hidden" name="county_id" value="{cn['id']}">
                    <button type="submit" class="btn btn-red" style="font-size:0.6rem;padding:3px 5px;">Remove City</button>
                </form>
            </td>
        </tr>"""

    body = f"""
    <h2 style="font-size:0.9rem;margin-bottom:10px;">Cities & Counties</h2>
    {_flash(msg=msg, err=err)}

    <div class="card">
        <h3>Create City</h3>
        <p style="color:#94a3b8;font-size:0.78rem;margin-bottom:10px;">Admin shortcut — bypasses the district and $10M requirements. The selected player becomes mayor.</p>
        <form method="post" action="/admin/cities/create">
            <div class="form-row">
                <div style="flex:2;">
                    <div class="form-label">City Name</div>
                    <input type="text" name="city_name" placeholder="City name" required style="width:100%;">
                </div>
                <div style="flex:2;">
                    <div class="form-label">Mayor (Player)</div>
                    <select name="mayor_id" style="width:100%;">{player_opts}</select>
                </div>
                <button type="submit" class="btn btn-green" style="align-self:flex-end;">Create</button>
            </div>
        </form>
    </div>

    <div class="card">
        <h3>Add City to County</h3>
        <form method="post" action="/admin/counties/add-city">
            <div class="form-row">
                <div style="flex:1;"><div class="form-label">City</div><select name="city_id">{city_opts_county}</select></div>
                <div style="flex:1;"><div class="form-label">County</div><select name="county_id">{county_opts}</select></div>
                <button type="submit" class="btn btn-green">Add</button>
            </div>
        </form>
    </div>

    <div class="card">
        <h3>All Cities ({len(cities)})</h3>
        {f'<div class="table-wrap"><table><tr><th>ID</th><th>Name</th><th>Mayor</th><th>Members</th><th>County</th><th>Bank</th></tr>{city_rows}</table></div>' if city_rows else '<p style="color:#64748b;font-size:0.75rem;">No cities yet.</p>'}
    </div>

    <div class="card">
        <h3>All Counties ({len(counties)})</h3>
        {f'<div class="table-wrap"><table><tr><th>ID</th><th>Name</th><th>Token</th><th>Cities</th><th>Supply</th><th>Action</th></tr>{county_rows}</table></div>' if county_rows else '<p style="color:#64748b;font-size:0.75rem;">No counties yet.</p>'}
    </div>
    """
    return HTMLResponse(admin_shell("Cities & Counties", body, admin.business_name, "/admin/cities"))


@router.post("/admin/cities/create")
def post_admin_create_city(session_token: Optional[str] = Cookie(None), city_name: str = Form(...), mayor_id: int = Form(...)):
    admin, redirect = _guard(session_token)
    if redirect:
        return redirect
    result = admin_create_city(admin.id, city_name, mayor_id)
    if result.get("ok"):
        return RedirectResponse(url=f"/admin/cities?msg={result['msg'].replace(' ', '+')}", status_code=303)
    return RedirectResponse(url=f"/admin/cities?err={result['error'].replace(' ', '+')}", status_code=303)


@router.post("/admin/counties/add-city")
def post_county_add_city(session_token: Optional[str] = Cookie(None), city_id: int = Form(...), county_id: int = Form(...)):
    admin, redirect = _guard(session_token)
    if redirect:
        return redirect
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(admin.id)
    result = admin_add_city_to_county(admin.id, city_id, county_id)
    if result["ok"]:
        return RedirectResponse(url=f"/admin/cities?msg=City+%23{city_id}+added+to+county+%23{county_id}", status_code=303)
    return RedirectResponse(url=f"/admin/cities?err={result['error']}", status_code=303)


@router.post("/admin/counties/remove-city")
def post_county_remove_city(session_token: Optional[str] = Cookie(None), city_id: int = Form(...)):
    admin, redirect = _guard(session_token)
    if redirect:
        return redirect
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(admin.id)
    result = admin_remove_city_from_county(admin.id, city_id)
    if result["ok"]:
        return RedirectResponse(url=f"/admin/cities?msg=City+%23{city_id}+removed+from+county", status_code=303)
    return RedirectResponse(url=f"/admin/cities?err={result['error']}", status_code=303)


# ──────────────────────────────────────────────────────────────
# CITY DETAIL PAGE (polls + members)
# ──────────────────────────────────────────────────────────────

@router.get("/admin/cities/{city_id}", response_class=HTMLResponse)
def admin_city_detail(city_id: int, session_token: Optional[str] = Cookie(None),
                      msg: Optional[str] = Query(None), err: Optional[str] = Query(None)):
    admin, redirect = _guard(session_token)
    if redirect:
        return redirect
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(admin.id)

    # Load city info
    city_info = None
    try:
        from cities import City, CityMember, get_db as get_city_db
        from auth import Player, get_db as auth_get_db
        city_db = get_city_db()
        try:
            city = city_db.query(City).filter(City.id == city_id).first()
            if not city:
                return HTMLResponse(admin_shell("Not Found",
                    '<p style="color:#ef4444;">City not found.</p>', admin.business_name, "/admin/cities"))
            members = city_db.query(CityMember).filter(CityMember.city_id == city_id).all()
            member_ids = [m.player_id for m in members]
        finally:
            city_db.close()

        auth_db = auth_get_db()
        try:
            players = {p.id: p.business_name for p in
                       auth_db.query(Player).filter(Player.id.in_(member_ids)).all()}
            mayor_name = players.get(city.mayor_id, f"#{city.mayor_id}")
        finally:
            auth_db.close()

        city_info = {"id": city.id, "name": city.name, "mayor_id": city.mayor_id,
                     "mayor_name": mayor_name, "currency_type": city.currency_type}
        member_count = len(members)
        member_rows = "".join(
            f'<tr><td>#{m.player_id}</td><td>{players.get(m.player_id, "?")}</td>'
            f'<td>{"👑 Mayor" if m.player_id == city.mayor_id else "Member"}</td>'
            f'<td style="color:#64748b;font-size:0.7rem;">{m.joined_at.strftime("%Y-%m-%d") if m.joined_at else "—"}</td>'
            f'<td><a href="/admin/player/{m.player_id}" style="font-size:0.7rem;">View</a></td></tr>'
            for m in members
        )
    except Exception as e:
        return HTMLResponse(admin_shell("Error",
            f'<p style="color:#ef4444;">Error loading city: {e}</p>', admin.business_name, "/admin/cities"))

    # Load city polls
    polls = admin_get_city_polls(city_id)
    active_polls = [p for p in polls if p["status"] == "active"]
    past_polls   = [p for p in polls if p["status"] != "active"]

    def _poll_type_label(pt):
        return {"application": "🗳️ Application", "banishment": "⚖️ Banishment",
                "currency_change": "💱 Currency Change"}.get(pt, pt)

    def _status_color(st):
        return {"active": "#22c55e", "passed": "#60a5fa", "failed": "#ef4444",
                "cancelled": "#94a3b8"}.get(st, "#94a3b8")

    active_poll_rows = ""
    for p in active_polls:
        target_label = ""
        if p.get("target_name"):
            target_label = f'<br><span style="color:#94a3b8;font-size:0.7rem;">Target: {p["target_name"]}</span>'
        if p.get("proposed_currency"):
            target_label = f'<br><span style="color:#94a3b8;font-size:0.7rem;">Currency: {p["proposed_currency"]}</span>'
        active_poll_rows += f"""<tr>
            <td>#{p['id']}</td>
            <td>{_poll_type_label(p['poll_type'])}{target_label}</td>
            <td style="color:#22c55e;">{p['yes_votes']} ✓ / {p['no_votes']} ✗ ({p['vote_count']} voters)</td>
            <td style="color:#94a3b8;font-size:0.7rem;">{p.get('closes_at','')[:16]}</td>
            <td>
                <form method="post" action="/admin/cities/{city_id}/resolve-poll" style="display:inline;">
                    <input type="hidden" name="poll_id" value="{p['id']}">
                    <button name="force_result" value="pass" class="btn btn-green" style="font-size:0.65rem;padding:3px 6px;">Force Pass</button>
                    <button name="force_result" value="fail" class="btn btn-red" style="font-size:0.65rem;padding:3px 6px;margin-left:3px;">Force Fail</button>
                    <button name="force_result" value="cancel" style="background:#475569;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:0.65rem;padding:3px 6px;margin-left:3px;">Cancel</button>
                </form>
            </td>
        </tr>"""

    past_poll_rows = ""
    for p in past_polls[:10]:
        target_label = p.get("target_name") or p.get("proposed_currency") or "—"
        past_poll_rows += f"""<tr>
            <td>#{p['id']}</td>
            <td>{_poll_type_label(p['poll_type'])}</td>
            <td>{target_label}</td>
            <td style="color:{_status_color(p['status'])};font-weight:bold;">{p['status'].upper()}</td>
            <td style="color:#64748b;">{p['yes_votes']} / {p['no_votes']}</td>
        </tr>"""

    # ── City Projects panel ──────────────────────────────────────
    from city_projects import CITY_PROJECT_TYPES as _ALL_PROJ_TYPES
    city_projects = admin_get_city_projects(city_id)
    existing_types = {p["project_type"] for p in city_projects}

    def _status_badge(st):
        colours = {"active": "#22c55e", "constructing": "#f59e0b", "upgrading": "#60a5fa",
                   "paused": "#94a3b8", "deconstructed": "#ef4444"}
        return f'<span style="color:{colours.get(st,"#94a3b8")};font-weight:600;">{st}</span>'

    proj_rows = ""
    for p in city_projects:
        bar_w = int(p["progress_pct"])
        bar_html = ""
        if p["status"] in ("constructing", "upgrading"):
            bar_html = (
                f'<div style="background:#1e293b;border-radius:3px;height:4px;width:80px;'
                f'display:inline-block;vertical-align:middle;margin-left:4px;">'
                f'<div style="background:#60a5fa;height:4px;border-radius:3px;width:{bar_w}%;"></div></div>'
                f'<span style="font-size:0.65rem;color:#94a3b8;margin-left:3px;">{p["progress_pct"]:.0f}%</span>'
            )
        proj_rows += f"""<tr>
            <td style="font-size:0.75rem;">#{p['id']}</td>
            <td style="font-size:0.75rem;"><strong>{p['name']}</strong><br>
                <span style="color:#64748b;font-size:0.65rem;">{p['project_type']}</span></td>
            <td style="text-align:center;font-size:0.75rem;">{p['level']} / {p['target_level']}</td>
            <td>{_status_badge(p['status'])} {bar_html}</td>
            <td style="white-space:nowrap;display:flex;flex-wrap:wrap;gap:3px;align-items:center;">
                <form method="post" action="/admin/cities/{city_id}/projects/{p['id']}/complete" style="display:inline;">
                    <button class="btn btn-green" style="font-size:0.6rem;padding:2px 6px;"
                        {'disabled' if p["status"] not in ("constructing","upgrading") else ''}>Complete</button>
                </form>
                <form method="post" action="/admin/cities/{city_id}/projects/{p['id']}/set-level" style="display:inline;">
                    <input type="number" name="level" value="{p['level']}" min="0" max="12"
                           style="width:38px;font-size:0.7rem;display:inline;">
                    <button class="btn" style="font-size:0.6rem;padding:2px 5px;background:#475569;color:#fff;border:none;border-radius:4px;cursor:pointer;">
                        Set Lvl</button>
                </form>
                <form method="post" action="/admin/cities/{city_id}/projects/{p['id']}/set-status" style="display:inline;">
                    <select name="status" style="font-size:0.65rem;padding:1px 3px;">
                        <option value="active" {'selected' if p["status"]=="active" else ''}>Active</option>
                        <option value="paused" {'selected' if p["status"]=="paused" else ''}>Paused</option>
                    </select>
                    <button class="btn" style="font-size:0.6rem;padding:2px 5px;background:#475569;color:#fff;border:none;border-radius:4px;cursor:pointer;">
                        Set</button>
                </form>
                <form method="post" action="/admin/cities/{city_id}/projects/{p['id']}/deconstruct"
                      style="display:inline;"
                      onsubmit="return confirm('Deconstruct {p["name"]}? Vault contents will be lost.');">
                    <button class="btn btn-red" style="font-size:0.6rem;padding:2px 6px;">Deconstruct</button>
                </form>
            </td>
        </tr>"""

    # Build dropdown of project types not yet built in this city
    available_opts = "".join(
        f'<option value="{k}">{v["name"]} ({v["category"]})</option>'
        for k, v in sorted(_ALL_PROJ_TYPES.items(), key=lambda x: (x[1]["category"], x[1]["name"]))
        if k not in existing_types
    )

    projects_panel = f"""
    <div class="card">
        <h3>City Projects ({len(city_projects)})</h3>
        {f'<div class="table-wrap"><table><tr><th>ID</th><th>Project</th><th>Lvl</th><th>Status</th><th style="min-width:320px;">Actions</th></tr>{proj_rows}</table></div>'
          if city_projects else '<p style="color:#64748b;font-size:0.75rem;">No projects yet.</p>'}
        <div style="margin-top:12px;padding-top:10px;border-top:1px solid #334155;">
            <span style="font-size:0.75rem;font-weight:600;color:#94a3b8;">Construct new project (bypasses vault &amp; licenses):</span><br>
            <form method="post" action="/admin/cities/{city_id}/projects/construct" style="margin-top:6px;display:flex;gap:6px;align-items:center;">
                {'<select name="project_type" style="font-size:0.75rem;">' + available_opts + '</select>' if available_opts else '<span style="color:#64748b;font-size:0.75rem;">All project types already built.</span>'}
                {f'<button class="btn btn-green" style="font-size:0.7rem;padding:3px 10px;">Construct</button>' if available_opts else ''}
            </form>
        </div>
    </div>"""

    body = f"""
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
        <a href="/admin/cities" style="color:#64748b;font-size:0.75rem;">← Cities</a>
        <span style="font-size:0.9rem;font-weight:bold;">🏙️ {city_info['name']} (#{city_id})</span>
        <span style="color:#94a3b8;font-size:0.75rem;">Mayor: {city_info['mayor_name']}</span>
        {f'<span style="color:#f59e0b;font-size:0.75rem;">Currency: {city_info["currency_type"]}</span>' if city_info.get("currency_type") else ""}
    </div>
    {_flash(msg=msg, err=err)}

    <div class="card">
        <h3>Active Polls ({len(active_polls)})</h3>
        {f'<div class="table-wrap"><table><tr><th>ID</th><th>Type</th><th>Votes</th><th>Closes</th><th>Actions</th></tr>{active_poll_rows}</table></div>'
          if active_polls else '<p style="color:#64748b;font-size:0.75rem;">No active polls.</p>'}
    </div>

    <div class="card">
        <h3>Members ({member_count})</h3>
        {f'<div class="table-wrap"><table><tr><th>ID</th><th>Name</th><th>Role</th><th>Joined</th><th></th></tr>{member_rows}</table></div>'
          if member_rows else '<p style="color:#64748b;font-size:0.75rem;">No members.</p>'}
    </div>

    {projects_panel}

    {f'''<div class="card">
        <h3>Recent Polls (last {len(past_polls[:10])})</h3>
        <div class="table-wrap"><table><tr><th>ID</th><th>Type</th><th>Target</th><th>Result</th><th>Y/N</th></tr>{past_poll_rows}</table></div>
    </div>''' if past_polls else ""}
    """
    return HTMLResponse(admin_shell(f"City: {city_info['name']}", body, admin.business_name, "/admin/cities"))


@router.post("/admin/cities/{city_id}/resolve-poll")
def post_resolve_city_poll(city_id: int, session_token: Optional[str] = Cookie(None),
                           poll_id: int = Form(...), force_result: str = Form(...)):
    admin, redirect = _guard(session_token)
    if redirect:
        return redirect
    result = admin_resolve_city_poll(admin.id, poll_id, force_result)
    if result["ok"]:
        return RedirectResponse(url=f"/admin/cities/{city_id}?msg=Poll+%23{poll_id}+{force_result}ed", status_code=303)
    return RedirectResponse(url=f"/admin/cities/{city_id}?err={result['error']}", status_code=303)


@router.post("/admin/cities/{city_id}/projects/{instance_id}/complete")
def post_admin_complete_project(city_id: int, instance_id: int,
                                session_token: Optional[str] = Cookie(None)):
    admin, redirect = _guard(session_token)
    if redirect:
        return redirect
    result = admin_force_complete_project(admin.id, instance_id)
    if result["ok"]:
        return RedirectResponse(url=f"/admin/cities/{city_id}?msg=Project+%23{instance_id}+completed", status_code=303)
    return RedirectResponse(url=f"/admin/cities/{city_id}?err={result['error']}", status_code=303)


@router.post("/admin/cities/{city_id}/projects/{instance_id}/set-level")
def post_admin_set_project_level(city_id: int, instance_id: int,
                                 session_token: Optional[str] = Cookie(None),
                                 level: int = Form(...)):
    admin, redirect = _guard(session_token)
    if redirect:
        return redirect
    result = admin_set_project_level(admin.id, instance_id, level)
    if result["ok"]:
        return RedirectResponse(url=f"/admin/cities/{city_id}?msg=Project+%23{instance_id}+set+to+level+{level}", status_code=303)
    return RedirectResponse(url=f"/admin/cities/{city_id}?err={result['error']}", status_code=303)


@router.post("/admin/cities/{city_id}/projects/{instance_id}/set-status")
def post_admin_set_project_status(city_id: int, instance_id: int,
                                  session_token: Optional[str] = Cookie(None),
                                  status: str = Form(...)):
    admin, redirect = _guard(session_token)
    if redirect:
        return redirect
    result = admin_set_project_status(admin.id, instance_id, status)
    if result["ok"]:
        return RedirectResponse(url=f"/admin/cities/{city_id}?msg=Project+%23{instance_id}+set+to+{status}", status_code=303)
    return RedirectResponse(url=f"/admin/cities/{city_id}?err={result['error']}", status_code=303)


@router.post("/admin/cities/{city_id}/projects/{instance_id}/deconstruct")
def post_admin_deconstruct_project(city_id: int, instance_id: int,
                                   session_token: Optional[str] = Cookie(None)):
    admin, redirect = _guard(session_token)
    if redirect:
        return redirect
    result = admin_deconstruct_project(admin.id, instance_id)
    if result["ok"]:
        return RedirectResponse(url=f"/admin/cities/{city_id}?msg=Project+%23{instance_id}+deconstructed", status_code=303)
    return RedirectResponse(url=f"/admin/cities/{city_id}?err={result['error']}", status_code=303)


@router.post("/admin/cities/{city_id}/projects/construct")
def post_admin_construct_project(city_id: int,
                                 session_token: Optional[str] = Cookie(None),
                                 project_type: str = Form(...)):
    admin, redirect = _guard(session_token)
    if redirect:
        return redirect
    result = admin_construct_project(admin.id, city_id, project_type)
    if result["ok"]:
        return RedirectResponse(url=f"/admin/cities/{city_id}?msg={result.get('msg','Project+constructed')}", status_code=303)
    return RedirectResponse(url=f"/admin/cities/{city_id}?err={result['error']}", status_code=303)


# ──────────────────────────────────────────────────────────────
# COUNTY DETAIL PAGE (polls)
# ──────────────────────────────────────────────────────────────

@router.get("/admin/counties/{county_id}", response_class=HTMLResponse)
def admin_county_detail(county_id: int, session_token: Optional[str] = Cookie(None),
                        msg: Optional[str] = Query(None), err: Optional[str] = Query(None)):
    admin, redirect = _guard(session_token)
    if redirect:
        return redirect
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(admin.id)

    county_info = None
    try:
        from counties import County, get_db as get_county_db
        county_db = get_county_db()
        try:
            county = county_db.query(County).filter(County.id == county_id).first()
            if not county:
                return HTMLResponse(admin_shell("Not Found",
                    '<p style="color:#ef4444;">County not found.</p>', admin.business_name, "/admin/cities"))
            county_info = {"id": county.id, "name": county.name,
                           "crypto_symbol": county.crypto_symbol, "crypto_name": county.crypto_name}
        finally:
            county_db.close()
    except Exception as e:
        return HTMLResponse(admin_shell("Error",
            f'<p style="color:#ef4444;">Error loading county: {e}</p>', admin.business_name, "/admin/cities"))

    polls = admin_get_county_polls(county_id)
    active_polls = [p for p in polls if p["status"] == "active"]
    past_polls   = [p for p in polls if p["status"] != "active"]

    def _status_color(st):
        return {"active": "#22c55e", "passed": "#60a5fa", "failed": "#ef4444",
                "cancelled": "#94a3b8"}.get(st, "#94a3b8")

    active_poll_rows = ""
    for p in active_polls:
        target_label = p.get("target_city_name") or f"City #{p.get('target_city_id','?')}"
        active_poll_rows += f"""<tr>
            <td>#{p['id']}</td>
            <td>🏙️ Add City</td>
            <td>{target_label}</td>
            <td style="color:#22c55e;">{p['yes_votes']} ✓ / {p['no_votes']} ✗ ({p['vote_count']} voters)</td>
            <td style="color:#94a3b8;font-size:0.7rem;">{p.get('closes_at','')[:16]}</td>
            <td>
                <form method="post" action="/admin/counties/{county_id}/resolve-poll" style="display:inline;">
                    <input type="hidden" name="poll_id" value="{p['id']}">
                    <button name="force_result" value="pass" class="btn btn-green" style="font-size:0.65rem;padding:3px 6px;">Force Pass</button>
                    <button name="force_result" value="fail" class="btn btn-red" style="font-size:0.65rem;padding:3px 6px;margin-left:3px;">Force Fail</button>
                    <button name="force_result" value="cancel" style="background:#475569;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:0.65rem;padding:3px 6px;margin-left:3px;">Cancel</button>
                </form>
            </td>
        </tr>"""

    past_poll_rows = ""
    for p in past_polls[:10]:
        past_poll_rows += f"""<tr>
            <td>#{p['id']}</td>
            <td>{p.get('target_city_name') or f"City #{p.get('target_city_id','?')}"}</td>
            <td style="color:{_status_color(p['status'])};font-weight:bold;">{p['status'].upper()}</td>
            <td style="color:#64748b;">{p['yes_votes']} / {p['no_votes']}</td>
        </tr>"""

    body = f"""
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
        <a href="/admin/cities" style="color:#64748b;font-size:0.75rem;">← Cities</a>
        <span style="font-size:0.9rem;font-weight:bold;">🏛️ {county_info['name']} (#{county_id})</span>
        <span style="color:#f59e0b;font-size:0.75rem;">{county_info['crypto_symbol']} — {county_info['crypto_name']}</span>
    </div>
    {_flash(msg=msg, err=err)}

    <div class="card">
        <h3>Active Polls ({len(active_polls)})</h3>
        {f'<div class="table-wrap"><table><tr><th>ID</th><th>Type</th><th>Target City</th><th>Votes</th><th>Closes</th><th>Actions</th></tr>{active_poll_rows}</table></div>'
          if active_polls else '<p style="color:#64748b;font-size:0.75rem;">No active polls.</p>'}
    </div>

    {f'''<div class="card">
        <h3>Recent Polls (last {len(past_polls[:10])})</h3>
        <div class="table-wrap"><table><tr><th>ID</th><th>Target City</th><th>Result</th><th>Y/N</th></tr>{past_poll_rows}</table></div>
    </div>''' if past_polls else ""}
    """
    return HTMLResponse(admin_shell(f"County: {county_info['name']}", body, admin.business_name, "/admin/cities"))


@router.post("/admin/counties/{county_id}/resolve-poll")
def post_resolve_county_poll(county_id: int, session_token: Optional[str] = Cookie(None),
                             poll_id: int = Form(...), force_result: str = Form(...)):
    admin, redirect = _guard(session_token)
    if redirect:
        return redirect
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(admin.id)
    result = admin_resolve_county_poll(admin.id, poll_id, force_result)
    if result["ok"]:
        return RedirectResponse(url=f"/admin/counties/{county_id}?msg=Poll+%23{poll_id}+{force_result}ed", status_code=303)
    return RedirectResponse(url=f"/admin/counties/{county_id}?err={result['error']}", status_code=303)


@router.post("/admin/player/{pid}/kick")
def post_kick(pid: int, session_token: Optional[str] = Cookie(None), reason: str = Form("")):
    admin, _is_full, redirect = _mod_guard(session_token)
    if redirect:
        return redirect
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(admin.id)
    kick_player(admin.id, pid, reason)
    _force_disconnect(pid)
    _invalidate_sessions(pid)
    return RedirectResponse(url=f"/admin/player/{pid}?tab=moderation&msg=Player+kicked", status_code=303)


@router.post("/admin/player/{pid}/timeout")
def post_timeout(pid: int, session_token: Optional[str] = Cookie(None), minutes: int = Form(...), reason: str = Form("")):
    admin, _is_full, redirect = _mod_guard(session_token)
    if redirect:
        return redirect
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(admin.id)
    result = timeout_player(admin.id, pid, minutes, reason)
    if not result["ok"]:
        return RedirectResponse(url=f"/admin/player/{pid}?tab=moderation&err={result['error']}", status_code=303)
    _force_disconnect(pid)
    _invalidate_sessions(pid)
    return RedirectResponse(url=f"/admin/player/{pid}?tab=moderation&msg=Timed+out+{minutes}m", status_code=303)


@router.post("/admin/player/{pid}/ban")
def post_ban(pid: int, session_token: Optional[str] = Cookie(None), reason: str = Form("")):
    # Ban requires full admin (not just moderator)
    admin, redirect = _guard(session_token)
    if redirect:
        return redirect
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(admin.id)
    ban_player(admin.id, pid, reason)
    _force_disconnect(pid)
    _invalidate_sessions(pid)
    return RedirectResponse(url=f"/admin/player/{pid}?tab=moderation&msg=Player+banned", status_code=303)


@router.post("/admin/player/{pid}/revoke")
def post_revoke(pid: int, session_token: Optional[str] = Cookie(None), ban_id: int = Form(...)):
    admin, _is_full, redirect = _mod_guard(session_token)
    if redirect:
        return redirect
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(admin.id)
    result = revoke_ban(admin.id, ban_id)
    if result["ok"]:
        return RedirectResponse(url=f"/admin/player/{pid}?tab=moderation&msg=Ban+revoked", status_code=303)
    return RedirectResponse(url=f"/admin/player/{pid}?tab=moderation&err={result['error']}", status_code=303)


@router.post("/admin/player/{pid}/delete")
def post_delete_player(pid: int, session_token: Optional[str] = Cookie(None)):
    admin, redirect = _guard(session_token)
    if redirect:
        return redirect
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(admin.id)
    try:
        from estate import liquidate_estate
        import time
        current_tick = int(time.time() / 5)  # approximate tick from uptime
        result = liquidate_estate(pid, "admin_delete", current_tick)
        if result:
            log_action(admin.id, "delete_player", pid, f"Admin-triggered death/estate liquidation")
            return RedirectResponse(url=f"/admin/players?msg=Player+{pid}+death+triggered", status_code=303)
        else:
            return RedirectResponse(url=f"/admin/player/{pid}?err=Death+function+failed+or+player+already+deceased", status_code=303)
    except Exception as e:
        return RedirectResponse(url=f"/admin/player/{pid}?err={str(e)[:80]}", status_code=303)


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
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)

    from chat import get_patch_notes
    messages = get_patch_notes()
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
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)
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
def admin_chat(session_token: Optional[str] = Cookie(None), room: Optional[str] = Query(None), msg: Optional[str] = Query(None)):
    player, redirect = _guard(session_token)
    if redirect:
        return redirect
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)

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
            msg_id = m.get("id", "")
            msg_items += (
                f'<div class="chat-msg-row" style="display:flex;align-items:flex-start;gap:6px;">'
                f'<div style="flex:1;min-width:0;">'
                f'<span class="cm-name">{m["sender_name"]}</span>'
                f'<span class="cm-time">{ts}</span>'
                f'<div class="cm-text">{m["content"]}</div>'
                f'</div>'
                f'<form method="post" action="/admin/chat/delete-message" style="flex-shrink:0;" onsubmit="return confirm(\'Delete this message?\')">'
                f'<input type="hidden" name="message_id" value="{msg_id}">'
                f'<input type="hidden" name="room" value="{room}">'
                f'<button type="submit" style="background:none;border:none;color:#ef4444;cursor:pointer;font-size:0.85rem;padding:2px 4px;" title="Delete message">✕</button>'
                f'</form>'
                f'</div>'
            )

        sync_btn = (
            '<form method="post" action="/admin/chat/sync-patch-notes" style="margin-bottom:10px;">'
            '<button type="submit" class="btn btn-blue">&#8595; Sync Patch Notes from GitHub</button>'
            '</form>'
        ) if room == "updates" else ""

        messages_html = f"""
        <div class="card">
            <h3>{room_name} — Messages</h3>
            {sync_btn}
            {msg_items if msg_items else '<p style="color:#64748b;font-size:0.75rem;">No messages.</p>'}
        </div>
        """
    else:
        messages_html = '<p style="color:#64748b;font-size:0.75rem;">Select a room above to view messages.</p>'

    # DM threads overview
    dm_threads = get_dm_threads_overview(limit=20)
    dm_rows = ""
    for t in dm_threads:
        ts = _ts(t["last_time"])
        dm_rows += f'<tr><td><a href="/admin/chat/dm?a={t["player_a"]}&b={t["player_b"]}">{t["name_a"]}</a></td><td><a href="/admin/chat/dm?a={t["player_a"]}&b={t["player_b"]}">{t["name_b"]}</a></td><td style="color:#94a3b8;max-width:150px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{t["last_message"]}</td><td style="color:#64748b;">{ts}</td></tr>'

    dm_html = f"""
    <div class="card">
        <h3>Direct Messages</h3>
        {f'<div class="table-wrap"><table><tr><th>Player A</th><th>Player B</th><th>Last Message</th><th>Time</th></tr>{dm_rows}</table></div>' if dm_rows else '<p style="color:#64748b;font-size:0.75rem;">No DM conversations yet.</p>'}
    </div>
    """

    body = f"""
    <h2 style="font-size:0.9rem;margin-bottom:10px;">Chat Rooms</h2>
    {_flash(msg=msg)}
    <div class="tabs">{room_links}</div>
    {messages_html}
    {dm_html}
    """
    return HTMLResponse(admin_shell("Chat", body, player.business_name, "/admin/chat"))


@router.get("/admin/chat/dm", response_class=HTMLResponse)
def admin_chat_dm(session_token: Optional[str] = Cookie(None), a: int = Query(...), b: int = Query(...)):
    """Admin view of a DM thread between two players."""
    player, redirect = _guard(session_token)
    if redirect:
        return redirect
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)

    messages = get_dm_thread_messages(a, b, limit=100)

    # Look up names
    import auth
    db = auth.get_db()
    pa = db.query(auth.Player).filter(auth.Player.id == a).first()
    pb = db.query(auth.Player).filter(auth.Player.id == b).first()
    db.close()
    name_a = pa.business_name if pa else f"#{a}"
    name_b = pb.business_name if pb else f"#{b}"

    msg_items = ""
    for m in messages:
        ts = _ts(m.get("created_at"))
        msg_items += f'<div class="chat-msg-row"><span class="cm-name">{m["from_name"]}</span><span class="cm-time">{ts}</span><div class="cm-text">{m["content"]}</div></div>'

    body = f"""
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">
        <a href="/admin/chat" style="color:#64748b;font-size:0.75rem;">← Chat</a>
        <span style="font-size:0.9rem;font-weight:bold;">DM: {name_a} ↔ {name_b}</span>
    </div>
    <div class="card">
        <h3>Messages ({len(messages)})</h3>
        {msg_items if msg_items else '<p style="color:#64748b;font-size:0.75rem;">No messages in this thread.</p>'}
    </div>
    """
    return HTMLResponse(admin_shell("DM Thread", body, player.business_name, "/admin/chat"))


@router.post("/admin/chat/delete-message")
def admin_chat_delete_message(
    session_token: Optional[str] = Cookie(None),
    message_id: int = Form(...),
    room: Optional[str] = Form(None),
):
    """Admin deletes a chat message."""
    player, redirect = _guard(session_token)
    if redirect:
        return redirect
    admin_delete_chat_message(player.id, message_id)
    dest = f"/admin/chat?room={room}" if room else "/admin/chat"
    return RedirectResponse(dest, status_code=303)


@router.post("/admin/chat/sync-patch-notes")
def admin_sync_patch_notes(session_token: Optional[str] = Cookie(None)):
    """Run post_patch_notes.py to pull all commits from GitHub into the Updates channel."""
    player, redirect = _guard(session_token)
    if redirect:
        return redirect
    import subprocess
    import sys
    script = os.path.join(os.path.dirname(__file__), "post_patch_notes.py")
    try:
        result = subprocess.run(
            [sys.executable, script],
            capture_output=True, text=True, timeout=120,
        )
        output = (result.stdout + result.stderr).strip()
        # Pull the last summary line as the flash message
        summary = output.splitlines()[-1] if output else "Done"
        log_action(player.id, "sync_patch_notes", details=summary[:200])
        from urllib.parse import quote
        return RedirectResponse(f"/admin/chat?room=updates&msg={quote(summary)}", status_code=303)
    except subprocess.TimeoutExpired:
        return RedirectResponse("/admin/chat?room=updates&msg=Timed+out", status_code=303)
    except Exception as e:
        return RedirectResponse(f"/admin/chat?room=updates&msg=Error:+{str(e)[:80]}", status_code=303)


# ==========================
# P2P OVERVIEW
# ==========================

@router.get("/admin/p2p", response_class=HTMLResponse)
def admin_p2p(session_token: Optional[str] = Cookie(None)):
    player, redirect = _guard(session_token)
    if redirect:
        return redirect
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)

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
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)

    entries = get_land_bank_entries()

    terrains = ["prairie", "forest", "desert", "marsh", "mountain", "tundra", "jungle", "savanna", "hills", "island"]
    terrain_opts = "".join(f'<option value="{t}">{t.title()}</option>' for t in terrains)

    rows = ""
    for e in entries:
        price = f'{fmt_usd(e["last_auction_price"], disp, precision=0)}' if e["last_auction_price"] else "-"
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
    <h2 style="font-size:0.9rem;margin-bottom:10px;">Land Bank ({len(entries)}/100 slots)</h2>
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
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(admin.id)
    result = admin_add_to_land_bank(admin.id, terrain_type, proximity)
    if result["ok"]:
        return RedirectResponse(url=f"/admin/landbank?msg=Plot+%23{result['plot_id']}+added", status_code=303)
    return RedirectResponse(url=f"/admin/landbank?err={result['error']}", status_code=303)


@router.post("/admin/landbank/remove")
def post_landbank_remove(session_token: Optional[str] = Cookie(None), land_plot_id: int = Form(...), delete_plot: str = Form("false")):
    admin, redirect = _guard(session_token)
    if redirect:
        return redirect
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(admin.id)
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
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)

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


# ==========================
# MODERATOR MANAGEMENT
# ==========================

@router.get("/admin/moderators", response_class=HTMLResponse)
def admin_moderators_page(session_token: Optional[str] = Cookie(None), msg: Optional[str] = Query(None), err: Optional[str] = Query(None)):
    """Moderator management page — full admins only."""
    admin, redirect = _guard(session_token)
    if redirect:
        return redirect
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(admin.id)

    from auth import Player
    import auth as _auth
    mods = get_all_moderators()
    all_players = get_all_players()

    # Build moderator table
    mod_ids = {m["player_id"] for m in mods}
    mod_rows = ""
    for m in mods:
        mod_rows += f'''<tr>
            <td>#{m["player_id"]}</td>
            <td><a href="/admin/player/{m["player_id"]}">{m["player_name"]}</a></td>
            <td style="color:#64748b;">{m["note"] or "-"}</td>
            <td style="color:#64748b;">{m["grantor_name"]}</td>
            <td style="color:#64748b;">{_ts(m["created_at"])}</td>
            <td>
                <form method="post" action="/admin/moderators/remove" style="display:inline;">
                    <input type="hidden" name="player_id" value="{m["player_id"]}">
                    <button type="submit" class="btn btn-red" style="font-size:0.65rem;padding:3px 6px;" onclick="return confirm(\'Revoke moderator?\')">Revoke</button>
                </form>
            </td>
        </tr>'''

    # Player options for grant form (exclude full admins and existing mods)
    player_opts = ""
    for p in all_players:
        if p["id"] not in ADMIN_PLAYER_IDS and p["id"] not in mod_ids:
            player_opts += f'<option value="{p["id"]}">#{p["id"]} {p["business_name"]}</option>'

    body = f"""
    <h2 style="font-size:0.9rem;margin-bottom:10px;">Moderator Management</h2>
    {_flash(msg=msg, err=err)}
    <div class="card">
        <h3>Current Moderators ({len(mods)})</h3>
        <p style="color:#64748b;font-size:0.75rem;margin-bottom:10px;">
            Moderators can kick, timeout, and revoke bans. They cannot ban permanently, edit balances, or access financial tools.
        </p>
        {f'<div class="table-wrap"><table><tr><th>ID</th><th>Player</th><th>Note</th><th>Granted By</th><th>Date</th><th>Action</th></tr>{mod_rows}</table></div>' if mod_rows else '<p style="color:#64748b;font-size:0.75rem;">No moderators yet.</p>'}
    </div>
    <div class="card">
        <h3>Grant Moderator Status</h3>
        <form method="post" action="/admin/moderators/add">
            <div class="form-row">
                <div style="flex:2;">
                    <div class="form-label">Player</div>
                    <select name="player_id" required style="width:100%;">
                        <option value="">-- Select Player --</option>
                        {player_opts}
                    </select>
                </div>
                <div style="flex:2;">
                    <div class="form-label">Note (optional)</div>
                    <input type="text" name="note" placeholder="e.g. Chat moderator">
                </div>
                <button type="submit" class="btn btn-green">Grant</button>
            </div>
        </form>
    </div>
    """
    return HTMLResponse(admin_shell("Moderators", body, admin.business_name, "/admin/moderators"))


@router.post("/admin/moderators/add")
def post_add_moderator(session_token: Optional[str] = Cookie(None), player_id: int = Form(...), note: str = Form("")):
    admin, redirect = _guard(session_token)
    if redirect:
        return redirect
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(admin.id)
    result = add_moderator(admin.id, player_id, note)
    if result["ok"]:
        return RedirectResponse(url=f"/admin/moderators?msg=Moderator+granted+to+Player+%23{player_id}", status_code=303)
    return RedirectResponse(url=f"/admin/moderators?err={result['error']}", status_code=303)


@router.post("/admin/moderators/remove")
def post_remove_moderator(session_token: Optional[str] = Cookie(None), player_id: int = Form(...)):
    admin, redirect = _guard(session_token)
    if redirect:
        return redirect
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(admin.id)
    result = remove_moderator(admin.id, player_id)
    if result["ok"]:
        return RedirectResponse(url=f"/admin/moderators?msg=Moderator+revoked+from+Player+%23{player_id}", status_code=303)
    return RedirectResponse(url=f"/admin/moderators?err={result['error']}", status_code=303)


# ==========================
# ETF BANK MANAGEMENT
# ==========================

_ETF_CONFIGS = [
    {
        "bank_id": "apple_seeds_etf",
        "name": "Apple Seeds ETF",
        "share_item_type": "apple_seeds_etf_shares",
        "bank_player_id": -3,
        "ipo_shares": 10_000_000,
    },
    {
        "bank_id": "energy_etf",
        "name": "Wadsworth Energy ETF",
        "share_item_type": "energy_etf_shares",
        "bank_player_id": -4,
        "ipo_shares": 10_000_000,
    },
    {
        "bank_id": "city_nav_etf",
        "name": "City NAV ETF",
        "share_item_type": "city_nav_etf_shares",
        "bank_player_id": -6,
        "ipo_shares": 420_000_000_000,
    },
    {
        "bank_id": "land_bank",
        "name": "Land Bank",
        "share_item_type": "land_bank_shares",
        "bank_player_id": -2,
        "ipo_shares": 1_000_000_000_000,
    },
]


def _audit_etf(cfg: dict) -> dict:
    """Gather share audit data for one ETF."""
    import inventory
    import market
    import banks

    share_item_type = cfg["share_item_type"]
    bank_player_id = cfg["bank_player_id"]

    # All holders
    inv_db = inventory.get_db()
    try:
        holdings = inv_db.query(inventory.InventoryItem).filter(
            inventory.InventoryItem.item_type == share_item_type,
            inventory.InventoryItem.quantity > 0
        ).all()
        holders = [(h.player_id, int(h.quantity)) for h in holdings]
        total_in_inventory = sum(q for _, q in holders)
        bank_inventory = next((q for pid, q in holders if pid == bank_player_id), 0)
        player_inventory = total_in_inventory - bank_inventory
    finally:
        inv_db.close()

    # Active market orders from bank
    mkt_db = market.get_db()
    try:
        active_orders = mkt_db.query(market.MarketOrder).filter(
            market.MarketOrder.player_id == bank_player_id,
            market.MarketOrder.item_type == share_item_type,
            market.MarketOrder.status == market.OrderStatus.ACTIVE
        ).all()
        orders_data = [(o.id, int(o.quantity - o.quantity_filled), float(o.price)) for o in active_orders]
        shares_in_orders = sum(q for _, q, _ in orders_data)
    finally:
        mkt_db.close()

    # Bank entity info
    bank_entity = banks.get_bank_entity(cfg["bank_id"])
    total_issued = int(bank_entity.total_shares_issued) if bank_entity else 0
    share_price = bank_entity.share_price if bank_entity else 0.0

    return {
        "bank_id": cfg["bank_id"],
        "name": cfg["name"],
        "share_item_type": share_item_type,
        "bank_player_id": bank_player_id,
        "ipo_shares": cfg["ipo_shares"],
        "total_issued": total_issued,
        "total_in_inventory": total_in_inventory,
        "bank_inventory": bank_inventory,
        "player_inventory": player_inventory,
        "shares_in_orders": shares_in_orders,
        "share_price": share_price,
        "holders": holders,
        "active_orders": orders_data,
    }


@router.get("/admin/etf", response_class=HTMLResponse)
def admin_etf(session_token: Optional[str] = Cookie(None),
              msg: Optional[str] = Query(None),
              err: Optional[str] = Query(None)):
    admin, redirect = _guard(session_token)
    if redirect:
        return redirect
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(admin.id)

    alert = ""
    if msg:
        alert = f'<div style="background:#14532d;color:#86efac;padding:8px 12px;border-radius:4px;margin-bottom:12px;font-size:0.8rem;">{msg}</div>'
    if err:
        alert = f'<div style="background:#7f1d1d;color:#fca5a5;padding:8px 12px;border-radius:4px;margin-bottom:12px;font-size:0.8rem;">{err}</div>'

    cards_html = ""
    for cfg in _ETF_CONFIGS:
        try:
            a = _audit_etf(cfg)
        except Exception as ex:
            cards_html += f'<div class="card"><h3>{cfg["name"]}</h3><p style="color:#ef4444;">Audit error: {ex}</p></div>'
            continue

        expected = a["ipo_shares"]
        total_inv = a["total_in_inventory"]
        orphan_flag = ""
        if total_inv > expected:
            surplus = total_inv - expected
            orphan_flag = f'<span class="badge badge-red" style="margin-left:6px;">+{surplus:,} ORPHAN SHARES</span>'
        elif total_inv < expected * 0.01 and total_inv == 0:
            orphan_flag = f'<span class="badge badge-yellow" style="margin-left:6px;">NO SHARES IN CIRCULATION</span>'

        holder_rows = ""
        for pid, qty in sorted(a["holders"], key=lambda x: -x[1]):
            label = f"BANK ({pid})" if pid == a["bank_player_id"] else f"Player #{pid}"
            pct = qty / expected * 100 if expected > 0 else 0
            holder_rows += f"<tr><td>{label}</td><td>{qty:,}</td><td>{pct:.4f}%</td></tr>"

        order_rows = ""
        for oid, qty, price in a["active_orders"]:
            order_rows += f"<tr><td>#{oid}</td><td>{qty:,}</td><td>{fmt_usd(price, disp, precision=8)}</td></tr>"

        cards_html += f"""
        <div class="card">
            <h3>{a["name"]} <span style="color:#64748b;font-weight:normal;font-size:0.7rem;">({a["share_item_type"]})</span>{orphan_flag}</h3>
            <div style="display:flex;gap:16px;flex-wrap:wrap;margin-bottom:10px;font-size:0.75rem;">
                <span>IPO: <b>{expected:,}</b></span>
                <span>Issued: <b>{a["total_issued"]:,}</b></span>
                <span>In Inventory: <b>{total_inv:,}</b></span>
                <span style="color:#38bdf8;">Bank holds: <b>{a["bank_inventory"]:,}</b></span>
                <span style="color:#22c55e;">Players hold: <b>{a["player_inventory"]:,}</b></span>
                <span style="color:#a78bfa;">In orders: <b>{a["shares_in_orders"]:,}</b></span>
                <span>Price: <b>{fmt_usd(a["share_price"], disp, precision=8)}</b></span>
            </div>

            <div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:12px;">
                <form method="post" action="/admin/etf/cancel-orders">
                    <input type="hidden" name="bank_id" value="{a["bank_id"]}">
                    <input type="hidden" name="share_item_type" value="{a["share_item_type"]}">
                    <input type="hidden" name="bank_player_id" value="{a["bank_player_id"]}">
                    <button class="btn btn-yellow" type="submit"
                        onclick="return confirm('Cancel all active market orders for {a["name"]}?')">
                        Cancel All Bank Orders ({len(a["active_orders"])})
                    </button>
                </form>
                <form method="post" action="/admin/etf/zero-bank-inventory">
                    <input type="hidden" name="bank_id" value="{a["bank_id"]}">
                    <input type="hidden" name="share_item_type" value="{a["share_item_type"]}">
                    <input type="hidden" name="bank_player_id" value="{a["bank_player_id"]}">
                    <button class="btn btn-red" type="submit"
                        onclick="return confirm('Zero out bank inventory for {a["name"]}? This removes shares from the bank entity only.')">
                        Zero Bank Inventory ({a["bank_inventory"]:,})
                    </button>
                </form>
            </div>

            <div style="display:flex;gap:12px;flex-wrap:wrap;">
                <div style="flex:1;min-width:200px;">
                    <div style="font-size:0.65rem;color:#64748b;text-transform:uppercase;margin-bottom:4px;">All Holders</div>
                    <div class="table-wrap"><table>
                        <tr><th>Holder</th><th>Shares</th><th>%</th></tr>
                        {holder_rows if holder_rows else '<tr><td colspan="3" style="color:#64748b;">No holders</td></tr>'}
                    </table></div>
                </div>
                <div style="flex:1;min-width:200px;">
                    <div style="font-size:0.65rem;color:#64748b;text-transform:uppercase;margin-bottom:4px;">Active Bank Orders</div>
                    <div class="table-wrap"><table>
                        <tr><th>Order</th><th>Qty Remaining</th><th>Price</th></tr>
                        {order_rows if order_rows else '<tr><td colspan="3" style="color:#64748b;">No active orders</td></tr>'}
                    </table></div>
                </div>
            </div>
        </div>
        """

    body = f"""
    <h2 style="font-size:0.9rem;margin-bottom:10px;">ETF Bank Management</h2>
    {alert}
    {cards_html}
    """
    return HTMLResponse(admin_shell("ETF Banks", body, admin.business_name, "/admin/etf"))


@router.post("/admin/etf/cancel-orders")
def admin_etf_cancel_orders(
    session_token: Optional[str] = Cookie(None),
    bank_id: str = Form(...),
    share_item_type: str = Form(...),
    bank_player_id: int = Form(...),
):
    admin, redirect = _guard(session_token)
    if redirect:
        return redirect
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(admin.id)

    try:
        import market

        mkt_db = market.get_db()
        try:
            orders = mkt_db.query(market.MarketOrder).filter(
                market.MarketOrder.player_id == bank_player_id,
                market.MarketOrder.item_type == share_item_type,
                market.MarketOrder.status == market.OrderStatus.ACTIVE
            ).all()
            count = len(orders)
            for o in orders:
                o.status = market.OrderStatus.CANCELLED
            mkt_db.commit()
        finally:
            mkt_db.close()

        log_action(admin.id, "etf_cancel_orders", None, f"Cancelled {count} orders for {bank_id}")
        return RedirectResponse(url=f"/admin/etf?msg=Cancelled+{count}+orders+for+{bank_id}", status_code=303)
    except Exception as ex:
        return RedirectResponse(url=f"/admin/etf?err={str(ex)[:80]}", status_code=303)


@router.post("/admin/etf/zero-bank-inventory")
def admin_etf_zero_inventory(
    session_token: Optional[str] = Cookie(None),
    bank_id: str = Form(...),
    share_item_type: str = Form(...),
    bank_player_id: int = Form(...),
):
    admin, redirect = _guard(session_token)
    if redirect:
        return redirect
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(admin.id)

    try:
        import inventory

        inv_db = inventory.get_db()
        try:
            item = inv_db.query(inventory.InventoryItem).filter(
                inventory.InventoryItem.player_id == bank_player_id,
                inventory.InventoryItem.item_type == share_item_type
            ).first()
            removed = int(item.quantity) if item else 0
            if item:
                item.quantity = 0
                inv_db.commit()
        finally:
            inv_db.close()

        log_action(admin.id, "etf_zero_inventory", None, f"Zeroed {removed} bank shares for {bank_id}")
        return RedirectResponse(url=f"/admin/etf?msg=Zeroed+{removed}+bank+shares+for+{bank_id}", status_code=303)
    except Exception as ex:
        return RedirectResponse(url=f"/admin/etf?err={str(ex)[:80]}", status_code=303)


# ============================================================
# WIKI MEDIA MANAGEMENT  —  /admin/wiki
# ============================================================

_WIKI_MEDIA_PATH = os.path.join(os.path.dirname(__file__), "wiki_media.json")


def _load_wiki_media() -> dict:
    try:
        with open(_WIKI_MEDIA_PATH) as f:
            data = json.load(f)
        data.setdefault("videos", [])
        data.setdefault("audio", [])
        return data
    except Exception:
        return {"videos": [], "audio": []}


def _save_wiki_media(data: dict) -> None:
    with open(_WIKI_MEDIA_PATH, "w") as f:
        json.dump(data, f, indent=4)


def _extract_yt_id(raw: str) -> str:
    """Return bare 11-char YouTube video ID from any URL or ID string."""
    raw = raw.strip()
    # youtu.be/ID
    m = re.search(r"youtu\.be/([A-Za-z0-9_-]{11})", raw)
    if m:
        return m.group(1)
    # youtube.com/watch?v=ID or /embed/ID or /v/ID
    m = re.search(r"(?:v=|/embed/|/v/)([A-Za-z0-9_-]{11})", raw)
    if m:
        return m.group(1)
    # bare 11-char ID
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", raw):
        return raw
    return ""


@router.get("/admin/wiki", response_class=HTMLResponse)
def admin_wiki(
    session_token: Optional[str] = Cookie(None),
    msg: Optional[str] = Query(None),
    err: Optional[str] = Query(None),
):
    admin, redirect = _guard(session_token)
    if redirect:
        return redirect

    data = _load_wiki_media()
    videos = data["videos"]
    audio  = data["audio"]

    def _entry_row(entry: dict, kind: str, idx: int) -> str:
        ytid  = entry.get("youtube_id", "")
        title = entry.get("title", "")
        desc  = entry.get("description", "")
        thumb = f"https://img.youtube.com/vi/{ytid}/mqdefault.jpg"
        return (
            f'<tr>'
            f'<td style="width:100px;"><a href="https://youtube.com/watch?v={ytid}" target="_blank">'
            f'<img src="{thumb}" style="width:96px;border-radius:4px;"></a></td>'
            f'<td><strong style="color:#e5e7eb;">{title}</strong><br>'
            f'<span style="font-size:0.78rem;color:#94a3b8;">{desc[:120]}</span><br>'
            f'<code style="font-size:0.7rem;color:#64748b;">{ytid}</code></td>'
            f'<td>'
            f'<form method="post" action="/admin/wiki/delete" '
            f'onsubmit="return confirm(\'Delete this entry?\');">'
            f'<input type="hidden" name="kind" value="{kind}">'
            f'<input type="hidden" name="idx" value="{idx}">'
            f'<button class="btn btn-red" style="font-size:0.72rem;padding:4px 10px;">Delete</button>'
            f'</form>'
            f'</td></tr>'
        )

    vid_rows  = "".join(_entry_row(e, "video", i) for i, e in enumerate(videos))
    aud_rows  = "".join(_entry_row(e, "audio", i) for i, e in enumerate(audio))
    empty_vid = '<tr><td colspan="3" style="color:#64748b;font-size:0.8rem;padding:16px;">No video entries yet.</td></tr>'
    empty_aud = '<tr><td colspan="3" style="color:#64748b;font-size:0.8rem;padding:16px;">No audio deep dive entries yet.</td></tr>'

    msg_html = (f'<div class="card" style="background:rgba(34,197,94,0.1);border-color:#22c55e;'
                f'color:#86efac;margin-bottom:16px;">{msg}</div>') if msg else ""
    err_html = (f'<div class="card" style="background:rgba(239,68,68,0.1);border-color:#ef4444;'
                f'color:#fca5a5;margin-bottom:16px;">{err}</div>') if err else ""

    add_form = """
<div class="card" style="margin-top:24px;">
    <h3 style="font-size:0.85rem;color:#e5e7eb;margin-bottom:16px;">➕ Add Entry</h3>
    <form method="post" action="/admin/wiki/add">
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px;">
            <div>
                <label style="font-size:0.75rem;color:#94a3b8;display:block;margin-bottom:4px;">
                    YouTube URL or Video ID *
                </label>
                <input name="youtube_url" required placeholder="https://youtu.be/... or 11-char ID"
                       style="width:100%;padding:8px 10px;background:#1e293b;border:1px solid #334155;
                              border-radius:6px;color:#e5e7eb;font-size:0.85rem;">
            </div>
            <div>
                <label style="font-size:0.75rem;color:#94a3b8;display:block;margin-bottom:4px;">
                    Section *
                </label>
                <select name="kind" style="width:100%;padding:8px 10px;background:#1e293b;
                        border:1px solid #334155;border-radius:6px;color:#e5e7eb;font-size:0.85rem;">
                    <option value="video">📺 Video Tutorial</option>
                    <option value="audio">🎙️ Audio Deep Dive</option>
                </select>
            </div>
        </div>
        <div style="margin-bottom:12px;">
            <label style="font-size:0.75rem;color:#94a3b8;display:block;margin-bottom:4px;">Title *</label>
            <input name="title" required placeholder="e.g. Getting Started in Wadsworth"
                   style="width:100%;padding:8px 10px;background:#1e293b;border:1px solid #334155;
                          border-radius:6px;color:#e5e7eb;font-size:0.85rem;">
        </div>
        <div style="margin-bottom:16px;">
            <label style="font-size:0.75rem;color:#94a3b8;display:block;margin-bottom:4px;">
                Description (shown under the embed)
            </label>
            <textarea name="description" rows="2" placeholder="Brief description shown under the embed…"
                      style="width:100%;padding:8px 10px;background:#1e293b;border:1px solid #334155;
                             border-radius:6px;color:#e5e7eb;font-size:0.85rem;resize:vertical;
                             font-family:inherit;"></textarea>
        </div>
        <button class="btn" type="submit">Add to Wiki</button>
    </form>
</div>
"""

    body = f"""
{msg_html}{err_html}
<h2 style="font-size:1rem;color:#e5e7eb;margin-bottom:4px;">Wiki Media Manager</h2>
<p style="font-size:0.8rem;color:#64748b;margin-bottom:20px;">
    Paste any YouTube URL (watch / share / embed) or bare 11-character video ID.
    Entries appear on <a href="/stats/wiki" target="_blank" style="color:#38bdf8;">/stats/wiki</a> immediately.
</p>

<h3 style="font-size:0.85rem;color:#38bdf8;margin-bottom:10px;">📺 Video Tutorials ({len(videos)})</h3>
<div class="table-wrap">
<table>
    <tr><th>Thumbnail</th><th>Details</th><th></th></tr>
    {vid_rows or empty_vid}
</table>
</div>

<h3 style="font-size:0.85rem;color:#38bdf8;margin-top:24px;margin-bottom:10px;">
    🎙️ Audio Deep Dives ({len(audio)})
</h3>
<div class="table-wrap">
<table>
    <tr><th>Thumbnail</th><th>Details</th><th></th></tr>
    {aud_rows or empty_aud}
</table>
</div>

{add_form}
"""
    return HTMLResponse(admin_shell("Wiki Media", body, admin.business_name, "/admin/wiki"))


@router.post("/admin/wiki/add")
def admin_wiki_add(
    session_token: Optional[str] = Cookie(None),
    youtube_url: str  = Form(...),
    kind:        str  = Form(...),
    title:       str  = Form(...),
    description: str  = Form(""),
):
    admin, redirect = _guard(session_token)
    if redirect:
        return redirect

    ytid = _extract_yt_id(youtube_url)
    if not ytid:
        return RedirectResponse(url="/admin/wiki?err=Could+not+extract+a+valid+YouTube+video+ID", status_code=303)

    data = _load_wiki_media()
    entry = {"youtube_id": ytid, "title": title.strip(), "description": description.strip()}
    if kind == "audio":
        data["audio"].append(entry)
    else:
        data["videos"].append(entry)
    _save_wiki_media(data)

    log_action(admin.id, "wiki_media_add", None, f"{kind}: {title[:60]} ({ytid})")
    return RedirectResponse(url=f"/admin/wiki?msg=Added+{kind}%3A+{title[:40]}", status_code=303)


@router.post("/admin/wiki/delete")
def admin_wiki_delete(
    session_token: Optional[str] = Cookie(None),
    kind: str = Form(...),
    idx:  int = Form(...),
):
    admin, redirect = _guard(session_token)
    if redirect:
        return redirect

    data = _load_wiki_media()
    lst  = data["audio"] if kind == "audio" else data["videos"]
    if 0 <= idx < len(lst):
        removed = lst.pop(idx)
        _save_wiki_media(data)
        log_action(admin.id, "wiki_media_delete", None, f"{kind}: {removed.get('title','?')}")
        return RedirectResponse(url="/admin/wiki?msg=Entry+deleted", status_code=303)
    return RedirectResponse(url="/admin/wiki?err=Invalid+index", status_code=303)
