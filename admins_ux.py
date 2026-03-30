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

from fastapi import APIRouter, Cookie, File, Form, Query, UploadFile
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
    admin_create_city, admin_delete_city,
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
    admin_delete_county,
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
        ("/admin/notification-sound", "Notif Sound"),
        ("/admin/updates", "Updates"),
        ("/admin/chat", "Chat"),
        ("/admin/p2p", "P2P"),
        ("/admin/landbank", "Land Bank"),
        ("/admin/etf", "ETF Banks"),
        ("/admin/bonds", "Bonds"),
        ("/admin/logs", "Logs"),
        ("/admin/wiki", "Wiki Media"),
        ("/admin/item-routes", "Item Routes"),
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
        tab_body = _player_info_tab(pid, detail)
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
    from reserve_banks import (
        get_player_currency_balances, get_player_legal_tender,
        get_usd_balance,
    )

    legal_tender = get_player_legal_tender(pid)

    # get_usd_balance has the legacy cash_balance rescue path — always call it
    # so stale legacy money is migrated before we display.
    usd_balance = get_usd_balance(pid)

    # get_player_currency_balances filters out zero rows, so USD may be absent.
    # Build a merged dict keyed by currency_code, ensuring USD is always present.
    pcb_list = get_player_currency_balances(pid)
    balances_by_code = {b["currency_code"]: b for b in pcb_list}
    if "USD" not in balances_by_code:
        balances_by_code["USD"] = {
            "currency_code": "USD",
            "currency_symbol": "$",
            "flag": "🇺🇸",
            "balance": usd_balance,
            "usd_value": usd_balance,
        }
    else:
        # Use the rescue-accurate value rather than whatever PCB cached
        balances_by_code["USD"]["balance"] = usd_balance
        balances_by_code["USD"]["usd_value"] = usd_balance

    # Sort: legal tender first, then alphabetical
    def _sort_key(code):
        return (0 if code == legal_tender else 1, code)

    balance_rows = ""
    for code in sorted(balances_by_code.keys(), key=_sort_key):
        b    = balances_by_code[code]
        sym  = b.get("currency_symbol") or ""
        flag = b.get("flag") or ""
        bal  = b.get("balance", 0.0)
        usd  = b.get("usd_value", 0.0)
        is_lt = " ★" if code == legal_tender else ""
        usd_str = f" (≈ ${usd:,.2f} USD)" if code != "USD" else ""
        balance_rows += f"""
        <div style="border:1px solid #1e3a5f;border-radius:6px;padding:10px 12px;margin-bottom:8px;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
            <span style="font-weight:600;color:#e5e7eb;">{flag} {code}{is_lt}</span>
            <span style="color:#22c55e;font-weight:700;">{sym}{bal:,.4f}{usd_str}</span>
          </div>
          <form method="post" action="/admin/player/{pid}/set-currency" style="display:flex;gap:6px;align-items:center;">
            <input type="hidden" name="currency_code" value="{code}">
            <input type="hidden" name="tab" value="info">
            <input type="number" name="new_balance" step="0.0001" value="{bal:.4f}" style="flex:1;font-size:0.8rem;">
            <button type="submit" class="btn btn-blue" style="font-size:0.75rem;padding:4px 10px;">Set</button>
          </form>
        </div>"""

    # Always provide a freeform "set any currency" form for currencies with no existing row
    set_any_form = f"""
    <div style="border:1px solid #374151;border-radius:6px;padding:10px 12px;margin-top:12px;">
      <div style="color:#6b7280;font-size:0.72rem;margin-bottom:6px;text-transform:uppercase;letter-spacing:.04em;">Set Other Currency</div>
      <form method="post" action="/admin/player/{pid}/set-currency" style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;">
        <input type="hidden" name="tab" value="info">
        <input type="text"   name="currency_code" placeholder="e.g. JPY, USD" style="flex:1;min-width:80px;font-size:0.8rem;">
        <input type="number" name="new_balance" step="0.0001" value="0" style="flex:1;min-width:80px;font-size:0.8rem;">
        <button type="submit" class="btn btn-blue" style="font-size:0.75rem;padding:4px 10px;">Set</button>
      </form>
    </div>"""

    return f"""
    <div class="card">
        <h3>Player Info</h3>
        <div class="detail-row"><span class="label">ID</span><span class="value">#{detail["id"]}</span></div>
        <div class="detail-row"><span class="label">Name</span><span class="value">{detail["business_name"]}</span></div>
        <div class="detail-row"><span class="label">Legal Tender</span><span class="value">{legal_tender}</span></div>
        <div class="detail-row"><span class="label">City</span><span class="value">{detail["city"] or "None"}</span></div>
        <div class="detail-row"><span class="label">Registered</span><span class="value">{_ts(detail["created_at"])}</span></div>
        <div class="detail-row"><span class="label">Last Login</span><span class="value">{_ts(detail["last_login"])}</span></div>
    </div>
    <div class="card">
        <h3>Currency Balances</h3>
        <p style="color:#4b5563;font-size:0.75rem;margin-bottom:10px;">★ = legal tender. Amounts in native units — no conversion applied.</p>
        {balance_rows}
        {set_any_form}
    </div>
    <div class="card">
        <div style="border-top:1px solid #7f1d1d;padding-top:16px;">
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

    # Build vacant plot options
    vacant_plots = [p for p in get_player_land(pid) if not p["occupied_by_business_id"]]
    plot_opts = "".join(
        f'<option value="{p["id"]}">#{p["id"]} — {p["terrain_type"].title()} ({p["proximity_features"] or "no proximity"})</option>'
        for p in vacant_plots
    )

    # Build business type options
    try:
        from business import BUSINESS_TYPES
        biz_opts = "".join(
            f'<option value="{k}">{v.get("name", k.replace("_"," ").title())}</option>'
            for k, v in sorted(BUSINESS_TYPES.items(), key=lambda x: x[1].get("name", x[0]))
        )
    except Exception:
        biz_opts = ""

    create_form = ""
    if vacant_plots and biz_opts:
        create_form = f"""
    <div class="card">
        <h3>Place Business on Plot</h3>
        <form method="post" action="/admin/player/{pid}/create-business">
            <input type="hidden" name="tab" value="businesses">
            <div class="form-row">
                <div style="flex:1;"><div class="form-label">Vacant Plot</div><select name="plot_id">{plot_opts}</select></div>
                <div style="flex:2;"><div class="form-label">Business Type</div><select name="business_type">{biz_opts}</select></div>
                <button type="submit" class="btn btn-green">Place</button>
            </div>
        </form>
    </div>"""
    elif not vacant_plots:
        create_form = '<div class="card"><p style="color:#64748b;font-size:0.75rem;">No vacant land plots — create a land plot first.</p></div>'

    return f"""
    {create_form}
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


@router.post("/admin/player/{pid}/set-currency")
def post_set_currency(
    pid: int,
    session_token: Optional[str] = Cookie(None),
    currency_code: str = Form(...),
    new_balance: float = Form(...),
    tab: str = Form("info"),
):
    admin, redirect = _guard(session_token)
    if redirect:
        return redirect
    from admins import admin_set_currency_balance
    result = admin_set_currency_balance(admin.id, pid, currency_code, new_balance)
    if result["ok"]:
        return RedirectResponse(
            url=f"/admin/player/{pid}?tab={tab}&msg={currency_code}+set+to+{new_balance:.4f}",
            status_code=303,
        )
    return RedirectResponse(
        url=f"/admin/player/{pid}?tab={tab}&err={result['error']}",
        status_code=303,
    )


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


@router.post("/admin/player/{pid}/create-business")
def post_create_business(pid: int, session_token: Optional[str] = Cookie(None), plot_id: int = Form(...), business_type: str = Form(...), tab: str = Form("businesses")):
    admin, redirect = _guard(session_token)
    if redirect:
        return redirect
    from admins import admin_create_business
    result = admin_create_business(admin.id, pid, plot_id, business_type)
    if result["ok"]:
        return RedirectResponse(url=f"/admin/player/{pid}?tab={tab}&msg=Created+{business_type}+%28biz+%23{result['business_id']}%29+on+plot+%23{plot_id}", status_code=303)
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
            <td>
                <form method="post" action="/admin/cities/{c['id']}/delete"
                      onsubmit="return confirm('PERMANENTLY delete city {c[\"name\"]} and ALL its data? This cannot be undone.');">
                    <button type="submit" class="btn btn-red" style="font-size:0.6rem;padding:3px 6px;">Delete</button>
                </form>
            </td>
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
                <form method="post" action="/admin/counties/{cn['id']}/delete" style="display:inline;margin-left:4px;"
                      onsubmit="return confirm('PERMANENTLY delete county {cn[\"name\"]} and ALL its crypto/data? This cannot be undone.');">
                    <button type="submit" class="btn btn-red" style="font-size:0.6rem;padding:3px 6px;">Delete County</button>
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
        {f'<div class="table-wrap"><table><tr><th>ID</th><th>Name</th><th>Mayor</th><th>Members</th><th>County</th><th>Bank</th><th></th></tr>{city_rows}</table></div>' if city_rows else '<p style="color:#64748b;font-size:0.75rem;">No cities yet.</p>'}
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


@router.post("/admin/cities/{city_id}/delete")
def post_admin_delete_city(city_id: int, session_token: Optional[str] = Cookie(None)):
    admin, redirect = _guard(session_token)
    if redirect:
        return redirect
    result = admin_delete_city(admin.id, city_id)
    if result.get("ok"):
        msg = result.get("msg", f"City #{city_id} deleted").replace(" ", "+")
        return RedirectResponse(url=f"/admin/cities?msg={msg}", status_code=303)
    err = result.get("error", "Unknown error").replace(" ", "+")
    return RedirectResponse(url=f"/admin/cities?err={err}", status_code=303)


@router.post("/admin/counties/{county_id}/delete")
def post_admin_delete_county(county_id: int, session_token: Optional[str] = Cookie(None)):
    admin, redirect = _guard(session_token)
    if redirect:
        return redirect
    result = admin_delete_county(admin.id, county_id)
    if result.get("ok"):
        msg = result.get("msg", f"County #{county_id} deleted").replace(" ", "+")
        return RedirectResponse(url=f"/admin/cities?msg={msg}", status_code=303)
    err = result.get("error", "Unknown error").replace(" ", "+")
    return RedirectResponse(url=f"/admin/cities?err={err}", status_code=303)


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
    {
        "bank_id": "wbc50_index_fund",
        "name": "WBC-50 Index Fund",
        "share_item_type": "wbc50_index_fund_shares",
        "bank_player_id": -7,
        "ipo_shares": 500_000_000,
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

    # Cash reserves
    cash_reserves = 0.0
    try:
        bank_entity = banks.get_bank_entity(cfg["bank_id"])
        if bank_entity:
            cash_reserves = bank_entity.cash_reserves
    except Exception:
        pass

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
        "cash_reserves": cash_reserves,
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
                <span style="color:#f5a855;">Cash reserves: <b>${a["cash_reserves"]:,.2f}</b></span>
            </div>
            <div style="margin-bottom:12px;">
                <form method="post" action="/admin/etf/set-cash" style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;">
                    <input type="hidden" name="bank_id" value="{a["bank_id"]}">
                    <span style="font-size:0.72rem;color:#9ca3af;white-space:nowrap;">Set cash reserves:</span>
                    <input type="number" name="new_balance" step="0.01" value="{a["cash_reserves"]:.2f}"
                           style="flex:1;min-width:160px;font-size:0.8rem;">
                    <button class="btn btn-blue" type="submit"
                            onclick="return confirm('Set {a["name"]} cash reserves?')">Set Cash</button>
                </form>
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
                <form method="post" action="/admin/etf/reconcile">
                    <input type="hidden" name="bank_id" value="{a["bank_id"]}">
                    <input type="hidden" name="share_item_type" value="{a["share_item_type"]}">
                    <input type="hidden" name="bank_player_id" value="{a["bank_player_id"]}">
                    <input type="hidden" name="ipo_shares" value="{expected}">
                    <button class="btn btn-green" type="submit"
                        onclick="return confirm('Reconcile {a["name"]}? This cancels all active bank orders and sets bank inventory to IPO_SUPPLY − PLAYER_HOLDINGS, restoring the correct total supply.')">
                        ✦ Reconcile to IPO Supply
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

    # ── Orphan share scan ────────────────────────────────────────────────────
    from admins import scan_orphan_shares
    try:
        scan = scan_orphan_shares()
        scan_badge = (
            f'<span class="badge badge-red" style="margin-left:6px;">{scan["total"]:,} ORPHAN RECORDS</span>'
            if scan["total"] > 0 else
            '<span class="badge badge-green" style="margin-left:6px;">Clean</span>'
        )

        gov_broker_rows = "".join(
            f'<tr><td>{d["ticker"]}</td><td>{d["shares"]:,}</td>'
            f'<td>{"yes" if d["delisted"] else "no"}</td></tr>'
            for d in scan["gov_broker_detail"]
        ) or '<tr><td colspan="3" style="color:#64748b;">None</td></tr>'

        gov_bank_rows = "".join(
            f'<tr><td>{d["bank_id"]}</td><td>{d["shares"]:,}</td></tr>'
            for d in scan["gov_bank_detail"]
        ) or '<tr><td colspan="2" style="color:#64748b;">None</td></tr>'

        zombie_rows = "".join(
            f'<tr><td>{d["ticker"]}</td><td>#{d["founder_id"]}</td><td>{d["reason"]}</td></tr>'
            for d in scan["zombie_companies"]
        ) or '<tr><td colspan="3" style="color:#64748b;">None</td></tr>'

        orphan_section = f"""
        <div class="card">
            <h3>Brokerage &amp; Bank Share Cleanup {scan_badge}</h3>
            <p style="font-size:0.75rem;color:#94a3b8;margin-bottom:10px;">
                Records left behind by the old estate liquidation code.
                Government-held brokerage positions are deleted and shares returned to float.
                Government-held bank shares are retired. Zero-share ghost records are deleted.
                Zombie companies (founder deceased or permanently banned, still listed) are force-delisted.
            </p>
            <div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:12px;font-size:0.75rem;">
                <span>Gov broker positions: <b>{scan["gov_broker_positions"]}</b></span>
                <span>Gov bank holdings: <b>{scan["gov_bank_holdings"]}</b></span>
                <span>Zero-share broker: <b>{scan["zero_broker_positions"]}</b></span>
                <span>Zero-share bank: <b>{scan["zero_bank_holdings"]}</b></span>
                <span style="color:#f97316;">Zombie companies: <b>{len(scan["zombie_companies"])}</b></span>
            </div>
            <div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:12px;">
                <div style="flex:1;min-width:200px;">
                    <div style="font-size:0.65rem;color:#64748b;text-transform:uppercase;margin-bottom:4px;">Gov Brokerage Positions</div>
                    <div class="table-wrap"><table>
                        <tr><th>Ticker</th><th>Shares</th><th>Delisted</th></tr>
                        {gov_broker_rows}
                    </table></div>
                </div>
                <div style="flex:1;min-width:200px;">
                    <div style="font-size:0.65rem;color:#64748b;text-transform:uppercase;margin-bottom:4px;">Gov Bank Holdings</div>
                    <div class="table-wrap"><table>
                        <tr><th>Bank</th><th>Shares</th></tr>
                        {gov_bank_rows}
                    </table></div>
                </div>
                <div style="flex:1;min-width:200px;">
                    <div style="font-size:0.65rem;color:#64748b;text-transform:uppercase;margin-bottom:4px;">Zombie Companies (still listed, founder inactive)</div>
                    <div class="table-wrap"><table>
                        <tr><th>Ticker</th><th>Founder</th><th>Reason</th></tr>
                        {zombie_rows}
                    </table></div>
                </div>
            </div>
            <form method="post" action="/admin/etf/cleanup-orphan-shares">
                <button class="btn btn-red" type="submit"
                    onclick="return confirm('Delete all {scan["total"]:,} orphan records and force-delist {len(scan["zombie_companies"])} zombie companies? This cannot be undone.')">
                    ✦ Clean Up {scan["total"]:,} Orphan Records
                </button>
            </form>
        </div>
        """
    except Exception as scan_ex:
        orphan_section = f'<div class="card"><h3>Brokerage &amp; Bank Share Cleanup</h3><p style="color:#ef4444;">Scan error: {scan_ex}</p></div>'

    # ── Brokerage Firm cash card ─────────────────────────────────────────────
    brokerage_html = ""
    try:
        from banks.brokerage_firm import get_db as firm_db_fn, FirmEntity, MINIMUM_OPERATING_RESERVE
        fdb = firm_db_fn()
        firm = fdb.query(FirmEntity).first()
        fdb.close()
        if firm:
            status_color = "#22c55e" if firm.cash_reserves >= MINIMUM_OPERATING_RESERVE else "#ef4444"
            status_label = "Solvent" if firm.cash_reserves >= MINIMUM_OPERATING_RESERVE else "INSOLVENT"
            brokerage_html = f"""
            <div class="card">
                <h3>Wadsworth Brokerage Firm</h3>
                <div style="display:flex;gap:16px;flex-wrap:wrap;margin-bottom:10px;font-size:0.75rem;">
                    <span style="color:{status_color};">Status: <b>{status_label}</b></span>
                    <span style="color:#f5a855;">Cash reserves: <b>${firm.cash_reserves:,.2f}</b></span>
                    <span style="color:#9ca3af;">Min. reserve: <b>${MINIMUM_OPERATING_RESERVE:,.2f}</b></span>
                </div>
                <form method="post" action="/admin/etf/set-brokerage-cash"
                      style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;">
                    <span style="font-size:0.72rem;color:#9ca3af;white-space:nowrap;">Set cash reserves:</span>
                    <input type="number" name="new_balance" step="0.01" value="{firm.cash_reserves:.2f}"
                           style="flex:1;min-width:160px;font-size:0.8rem;">
                    <button class="btn btn-blue" type="submit"
                            onclick="return confirm('Set Brokerage Firm cash reserves?')">Set Cash</button>
                </form>
            </div>"""
    except Exception as brk_ex:
        brokerage_html = f'<div class="card"><h3>Wadsworth Brokerage Firm</h3><p style="color:#ef4444;">Error: {brk_ex}</p></div>'

    body = f"""
    <h2 style="font-size:0.9rem;margin-bottom:10px;">ETF Bank Management</h2>
    {alert}
    {cards_html}
    {brokerage_html}
    {orphan_section}
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


@router.post("/admin/etf/reconcile")
def admin_etf_reconcile(
    session_token: Optional[str] = Cookie(None),
    bank_id: str = Form(...),
    share_item_type: str = Form(...),
    bank_player_id: int = Form(...),
    ipo_shares: int = Form(...),
):
    """Restore the bank's share inventory to exactly (ipo_shares − player_holdings).

    Steps executed atomically:
      1. Cancel every active market order the bank has placed for this share type
         (orders are cancelled, not returned to inventory — the bank never "receives"
         shares from a cancelled sell order; it just stops offering them).
      2. Calculate the correct bank inventory = ipo_shares − sum(all player holdings).
      3. Set the bank's InventoryItem to that exact quantity, eliminating any orphan
         shares or shortfalls in one operation.

    Player holdings are never touched.
    """
    admin, redirect = _guard(session_token)
    if redirect:
        return redirect

    try:
        import inventory
        import market
        from urllib.parse import quote_plus

        # ── Step 1: cancel all active bank sell orders ───────────────────────
        mkt_db = market.get_db()
        try:
            orders = mkt_db.query(market.MarketOrder).filter(
                market.MarketOrder.player_id == bank_player_id,
                market.MarketOrder.item_type == share_item_type,
                market.MarketOrder.status    == market.OrderStatus.ACTIVE,
            ).all()
            cancelled = len(orders)
            for o in orders:
                o.status = market.OrderStatus.CANCELLED
            mkt_db.commit()
        finally:
            mkt_db.close()

        # ── Step 2: sum legitimate player holdings (exclude the bank itself) ─
        inv_db = inventory.get_db()
        try:
            player_holdings = inv_db.query(inventory.InventoryItem).filter(
                inventory.InventoryItem.item_type  == share_item_type,
                inventory.InventoryItem.quantity   > 0,
                inventory.InventoryItem.player_id  != bank_player_id,
            ).all()
            player_total = sum(int(h.quantity) for h in player_holdings)
        finally:
            inv_db.close()

        # ── Step 3: set bank inventory to correct amount ─────────────────────
        correct_qty = max(0, ipo_shares - player_total)

        inv_db2 = inventory.get_db()
        try:
            bank_item = inv_db2.query(inventory.InventoryItem).filter(
                inventory.InventoryItem.player_id == bank_player_id,
                inventory.InventoryItem.item_type == share_item_type,
            ).first()
            if bank_item:
                old_qty = int(bank_item.quantity)
                bank_item.quantity = correct_qty
            else:
                old_qty = 0
                bank_item = inventory.InventoryItem(
                    player_id=bank_player_id,
                    item_type=share_item_type,
                    quantity=correct_qty,
                )
                inv_db2.add(bank_item)
            inv_db2.commit()
        finally:
            inv_db2.close()

        log_action(
            admin.id, "etf_reconcile", None,
            f"Reconciled {bank_id}: bank inventory {old_qty:,} → {correct_qty:,}; "
            f"{cancelled} orders cancelled; player total {player_total:,}",
        )
        msg = (
            f"Reconciled {bank_id}: bank inventory set to {correct_qty:,} "
            f"(IPO {ipo_shares:,} \u2212 {player_total:,} player shares). "
            f"{cancelled} bank order(s) cancelled."
        )
        return RedirectResponse(url=f"/admin/etf?msg={quote_plus(msg)}", status_code=303)

    except Exception as ex:
        from urllib.parse import quote_plus
        return RedirectResponse(url=f"/admin/etf?err={quote_plus(str(ex)[:120])}", status_code=303)


@router.post("/admin/etf/cleanup-orphan-shares")
def admin_cleanup_orphan_shares(session_token: Optional[str] = Cookie(None)):
    admin, redirect = _guard(session_token)
    if redirect:
        return redirect
    from admins import cleanup_orphan_shares
    from urllib.parse import quote_plus
    result = cleanup_orphan_shares(admin.id)
    if result["ok"]:
        msg = (
            f"Cleaned up {result['total']} orphan records: "
            f"{result['gov_broker']} gov broker positions (shares returned to float), "
            f"{result['gov_bank']} gov bank holdings (shares retired), "
            f"{result['zero_broker']} zero-share broker, "
            f"{result['zero_bank']} zero-share bank, "
            f"{result['zombie_delisted']} zombie companies force-delisted, "
            f"{result['orders_cancelled']} open orders cancelled, "
            f"{result['wbc50_cleared']} WBC50 holdings zeroed."
        )
        return RedirectResponse(url=f"/admin/etf?msg={quote_plus(msg)}", status_code=303)
    return RedirectResponse(url=f"/admin/etf?err={quote_plus(result['error'][:120])}", status_code=303)


@router.post("/admin/etf/set-cash")
def admin_etf_set_cash(
    session_token: Optional[str] = Cookie(None),
    bank_id: str = Form(...),
    new_balance: float = Form(...),
):
    admin, redirect = _guard(session_token)
    if redirect:
        return redirect
    from admins import admin_set_etf_cash
    from urllib.parse import quote_plus
    result = admin_set_etf_cash(admin.id, bank_id, new_balance)
    if result["ok"]:
        msg = f"{bank_id} cash set to ${new_balance:,.2f}"
        return RedirectResponse(url=f"/admin/etf?msg={quote_plus(msg)}", status_code=303)
    return RedirectResponse(url=f"/admin/etf?err={quote_plus(result['error'][:120])}", status_code=303)


@router.post("/admin/etf/set-brokerage-cash")
def admin_etf_set_brokerage_cash(
    session_token: Optional[str] = Cookie(None),
    new_balance: float = Form(...),
):
    admin, redirect = _guard(session_token)
    if redirect:
        return redirect
    from admins import admin_set_brokerage_cash
    from urllib.parse import quote_plus
    result = admin_set_brokerage_cash(admin.id, new_balance)
    if result["ok"]:
        msg = f"Brokerage Firm cash set to ${new_balance:,.2f}"
        return RedirectResponse(url=f"/admin/etf?msg={quote_plus(msg)}", status_code=303)
    return RedirectResponse(url=f"/admin/etf?err={quote_plus(result['error'][:120])}", status_code=303)


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


# ── Admin: Item Routes ────────────────────────────────────────
@router.get("/admin/item-routes", response_class=HTMLResponse)
def admin_item_routes(
    session_token: Optional[str] = Cookie(None),
    category: str = Query("all"),
    item_set: str = Query("all"),
):
    """Production & consumption routes for every regular and district item."""
    admin, redirect = _guard(session_token)
    if redirect:
        return redirect

    # ── Load item catalogues ──────────────────────────────────
    regular_items: dict = {}
    district_items: dict = {}
    try:
        with open("item_types.json") as f:
            regular_items = json.load(f)
    except Exception:
        pass
    try:
        with open("district_items.json") as f:
            district_items = json.load(f)
    except Exception:
        pass

    # ── Load business catalogues ──────────────────────────────
    biz_regular: dict = {}
    biz_district: dict = {}
    try:
        with open("business_types.json") as f:
            biz_regular = json.load(f)
    except Exception:
        pass
    try:
        with open("district_businesses.json") as f:
            biz_district = json.load(f)
    except Exception:
        pass

    all_items: dict = {}
    for k, v in regular_items.items():
        all_items[k] = dict(v, _set="regular")
    for k, v in district_items.items():
        all_items[k] = dict(v, _set="district")

    # ── Build routes index ────────────────────────────────────
    produced_by: dict = {k: [] for k in all_items}
    consumed_by: dict = {k: [] for k in all_items}

    for biz_set_label, biz_dict in (("regular", biz_regular), ("district", biz_district)):
        for biz_key, biz in biz_dict.items():
            if not isinstance(biz, dict):
                continue
            biz_name = biz.get("name", biz_key.replace("_", " ").title())
            for line in biz.get("production_lines", []):
                out_item = line.get("output_item", "")
                out_qty  = line.get("output_qty", 0)
                inputs   = line.get("inputs", [])
                if out_item in produced_by:
                    produced_by[out_item].append({
                        "biz_key":  biz_key,
                        "biz_name": biz_name,
                        "output_qty": out_qty,
                        "inputs": inputs,
                        "biz_set": biz_set_label,
                    })
                for inp in inputs:
                    inp_item = inp.get("item", "")
                    inp_qty  = inp.get("quantity", 0)
                    if inp_item in consumed_by:
                        consumed_by[inp_item].append({
                            "biz_key":  biz_key,
                            "biz_name": biz_name,
                            "qty_needed": inp_qty,
                            "biz_set": biz_set_label,
                        })

    # ── Filter pool ───────────────────────────────────────────
    cats = sorted({v.get("category", "misc") for v in all_items.values() if isinstance(v, dict)})

    if item_set == "regular":
        pool = {k: v for k, v in all_items.items() if v.get("_set") == "regular"}
    elif item_set == "district":
        pool = {k: v for k, v in all_items.items() if v.get("_set") == "district"}
    else:
        pool = all_items

    if category != "all":
        pool = {k: v for k, v in pool.items() if v.get("category") == category}

    # ── CSV data ──────────────────────────────────────────────
    csv_rows = ["item_key,item_name,item_set,category,produced_by_business,producer_biz_set,output_qty,consumed_by_business,consumer_biz_set,qty_needed_as_input"]
    for key in sorted(all_items.keys()):
        item = all_items[key]
        name = item.get("name", key.replace("_", " ").title())
        iset = item.get("_set", "regular")
        cat  = item.get("category", "misc")
        producers = produced_by.get(key, [])
        consumers = consumed_by.get(key, [])
        max_rows = max(len(producers), len(consumers), 1)
        for i in range(max_rows):
            p = producers[i] if i < len(producers) else {}
            c = consumers[i] if i < len(consumers) else {}
            p_name = p.get("biz_name", "").replace(",", ";") if p else ""
            p_set  = p.get("biz_set", "") if p else ""
            p_qty  = str(p.get("output_qty", "")) if p else ""
            c_name = c.get("biz_name", "").replace(",", ";") if c else ""
            c_set  = c.get("biz_set", "") if c else ""
            c_qty  = str(c.get("qty_needed", "")) if c else ""
            if i == 0:
                csv_rows.append(f'"{key}","{name}",{iset},{cat},{p_name},{p_set},{p_qty},{c_name},{c_set},{c_qty}')
            else:
                csv_rows.append(f'"","","","",{p_name},{p_set},{p_qty},{c_name},{c_set},{c_qty}')
    csv_data_js = json.dumps("\n".join(csv_rows))

    # ── Filter tabs ───────────────────────────────────────────
    set_tabs = ""
    for s_val, s_label in [("all", f"All ({len(all_items)})"),
                            ("regular", f"Regular ({len(regular_items)})"),
                            ("district", f"District ({len(district_items)})")]:
        act = " active" if item_set == s_val else ""
        set_tabs += (
            f'<a href="/admin/item-routes?item_set={s_val}&category={category}" '
            f'class="ir-ft{act}">{s_label}</a>'
        )

    cur_set_param = f"item_set={item_set}"
    cat_filters = ""
    act = " active" if category == "all" else ""
    cat_filters += f'<a href="/admin/item-routes?{cur_set_param}&category=all" class="ir-ft{act}">All Categories</a>'
    for cat in cats:
        cnt = sum(1 for v in pool.values() if v.get("category") == cat)
        if cnt == 0 and category != cat:
            continue
        act = " active" if category == cat else ""
        cat_filters += (
            f'<a href="/admin/item-routes?{cur_set_param}&category={cat}" class="ir-ft{act}">'
            f'{cat.replace("_"," ").title()}</a>'
        )

    # ── Build cards ───────────────────────────────────────────
    def _inp_badges(inputs: list) -> str:
        parts = []
        for inp in inputs[:6]:
            nm  = inp.get("item", "").replace("_", " ").title()
            qty = inp.get("quantity", 0)
            parts.append(f'<span class="ir-inp">{nm} ×{qty:g}</span>')
        if len(inputs) > 6:
            parts.append(f'<span class="ir-inp ir-more">+{len(inputs)-6} more</span>')
        return "".join(parts)

    def _biz_pill(biz_set: str) -> str:
        if biz_set == "district":
            return '<span class="ir-pill ir-pill-d">district</span>'
        return '<span class="ir-pill ir-pill-r">regular</span>'

    cards_html = ""
    for key, item in sorted(pool.items(), key=lambda x: x[1].get("name", x[0])):
        name  = item.get("name", key.replace("_", " ").title())
        cat   = item.get("category", "misc")
        iset  = item.get("_set", "regular")
        producers = produced_by.get(key, [])
        consumers = consumed_by.get(key, [])

        iset_pill = ('<span class="ir-pill ir-pill-d">District</span>' if iset == "district"
                     else '<span class="ir-pill ir-pill-r">Regular</span>')
        cat_pill  = f'<span class="ir-pill ir-pill-c">{cat.replace("_"," ").title()}</span>'

        if producers:
            prod_html = ""
            for p in producers:
                prod_html += (
                    f'<div class="ir-biz-row">'
                    f'<span class="ir-biz-name">{p["biz_name"]}</span>'
                    f'{_biz_pill(p["biz_set"])}'
                    f'<span class="ir-qty">→ {p["output_qty"]:g} units/cycle</span>'
                    f'<div class="ir-inps">{_inp_badges(p["inputs"])}</div>'
                    f'</div>'
                )
        else:
            prod_html = '<span class="ir-none">Not produced in any business</span>'

        if consumers:
            cons_html = ""
            for c in consumers:
                cons_html += (
                    f'<div class="ir-biz-row">'
                    f'<span class="ir-biz-name">{c["biz_name"]}</span>'
                    f'{_biz_pill(c["biz_set"])}'
                    f'<span class="ir-qty">← {c["qty_needed"]:g} units consumed</span>'
                    f'</div>'
                )
        else:
            cons_html = '<span class="ir-none">Not consumed by any business</span>'

        safe_name = name.lower().replace('"', '')
        cards_html += f"""
<div class="ir-card" data-n="{safe_name}" data-c="{cat}" data-s="{iset}">
  <div class="ir-card-hdr">
    <div>
      <div class="ir-item-name">{name}</div>
      <div class="ir-item-key">{key}</div>
    </div>
    <div class="ir-pills">{iset_pill}{cat_pill}</div>
  </div>
  <div class="ir-body">
    <div class="ir-col">
      <div class="ir-col-hdr ir-prod-hdr">⚙ Produced By</div>
      {prod_html}
    </div>
    <div class="ir-col">
      <div class="ir-col-hdr ir-cons-hdr">⬇ Consumed By</div>
      {cons_html}
    </div>
  </div>
</div>"""

    total_shown = len(pool)

    body = f"""
<style>
.ir-toolbar{{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:20px;}}
.ir-dl-btn{{padding:8px 18px;background:rgba(239,68,68,0.15);border:1px solid rgba(239,68,68,0.5);border-radius:6px;color:#ef4444;font-size:0.8rem;font-weight:600;cursor:pointer;font-family:inherit;transition:all .15s;}}
.ir-dl-btn:hover{{background:rgba(239,68,68,0.25);box-shadow:0 0 10px rgba(239,68,68,0.2);}}
.ir-stat{{color:#4b5563;font-size:0.8rem;margin-left:auto;}}
.ir-filters{{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px;}}
.ir-ft{{padding:5px 12px;border-radius:4px;font-size:0.75rem;font-weight:500;color:#6b7280;background:#0f172a;border:1px solid #1e3a5f;text-decoration:none;transition:all .15s;}}
.ir-ft:hover{{color:#38bdf8;border-color:#38bdf8;}}
.ir-ft.active{{color:#38bdf8;background:rgba(56,189,248,0.08);border-color:#38bdf8;}}
.ir-search-wrap{{position:relative;margin-bottom:16px;}}
.ir-search-ico{{position:absolute;left:12px;top:50%;transform:translateY(-50%);color:#4b5563;pointer-events:none;font-size:0.9rem;}}
.ir-search{{width:100%;padding:10px 14px 10px 36px;background:#0f172a;border:1px solid #1e3a5f;border-radius:6px;color:#e5e7eb;font-size:0.85rem;outline:none;font-family:inherit;transition:border-color .15s;}}
.ir-search:focus{{border-color:#38bdf8;}}
.ir-card{{background:#0a0f1e;border:1px solid #1e293b;border-radius:8px;margin-bottom:12px;overflow:hidden;}}
.ir-card-hdr{{display:flex;justify-content:space-between;align-items:flex-start;padding:14px 16px 10px;border-bottom:1px solid #0f1a30;}}
.ir-item-name{{font-size:0.92rem;font-weight:700;color:#e5e7eb;}}
.ir-item-key{{color:#4b5563;font-size:0.68rem;font-family:monospace;margin-top:2px;}}
.ir-pills{{display:flex;gap:5px;flex-wrap:wrap;justify-content:flex-end;}}
.ir-pill{{display:inline-block;padding:2px 7px;border-radius:3px;font-size:0.63rem;font-weight:600;letter-spacing:.03em;}}
.ir-pill-d{{background:rgba(56,189,248,0.12);color:#38bdf8;border:1px solid rgba(56,189,248,0.3);}}
.ir-pill-r{{background:rgba(75,85,99,0.2);color:#9ca3af;border:1px solid rgba(75,85,99,0.35);}}
.ir-pill-c{{background:rgba(239,68,68,0.1);color:#ef4444;border:1px solid rgba(239,68,68,0.25);}}
.ir-body{{display:grid;grid-template-columns:1fr 1fr;}}
@media(max-width:640px){{.ir-body{{grid-template-columns:1fr;}}}}
.ir-col{{padding:12px 16px;}}
.ir-col:first-child{{border-right:1px solid #0f1a30;}}
.ir-col-hdr{{font-size:0.68rem;font-weight:700;text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px;padding-bottom:5px;border-bottom:1px solid #0f1a30;}}
.ir-prod-hdr{{color:#86efac;}}
.ir-cons-hdr{{color:#fca5a5;}}
.ir-biz-row{{margin-bottom:9px;padding-bottom:7px;border-bottom:1px solid #080e1d;}}
.ir-biz-row:last-child{{border-bottom:none;margin-bottom:0;}}
.ir-biz-name{{font-size:0.78rem;font-weight:600;color:#e5e7eb;}}
.ir-qty{{font-size:0.72rem;color:#4b5563;margin-left:6px;}}
.ir-inps{{display:flex;flex-wrap:wrap;gap:3px;margin-top:4px;}}
.ir-inp{{padding:2px 6px;background:#0c1528;border:1px solid #1e293b;border-radius:3px;font-size:0.63rem;color:#6b7280;}}
.ir-more{{color:#ef4444;border-color:rgba(239,68,68,0.3);}}
.ir-none{{font-size:0.75rem;color:#374151;font-style:italic;}}
.ir-section-lbl{{font-size:0.68rem;color:#4b5563;text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px;}}
</style>

<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
  <h2 style="color:#ef4444;font-size:1.1rem;font-weight:700;">🔗 Item Production &amp; Consumption Routes</h2>
</div>
<p style="color:#4b5563;font-size:0.8rem;margin-bottom:18px;">Every regular and district item — which businesses produce it and which consume it as an input. Download the full dataset as CSV for offline reference.</p>

<div class="ir-toolbar">
  <button class="ir-dl-btn" onclick="downloadCSV()">⬇ Download CSV</button>
  <span class="ir-stat" id="ir-count">Showing {total_shown} items</span>
</div>

<div class="ir-section-lbl">Item Set</div>
<div class="ir-filters" style="margin-bottom:14px;">{set_tabs}</div>

<div class="ir-section-lbl">Category</div>
<div class="ir-filters" style="max-height:110px;overflow-y:auto;margin-bottom:14px;">{cat_filters}</div>

<div class="ir-search-wrap">
  <span class="ir-search-ico">🔍</span>
  <input class="ir-search" id="ir-search" placeholder="Search items by name or key…" oninput="filterCards()">
</div>

<div id="ir-list">
{cards_html if cards_html else '<p style="color:#4b5563;font-style:italic;">No items found.</p>'}
</div>

<script>
var CSV_DATA = {csv_data_js};
function downloadCSV() {{
  var blob = new Blob([CSV_DATA], {{type: 'text/csv;charset=utf-8;'}});
  var a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'item_routes.csv';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(a.href);
}}
function filterCards() {{
  var q = document.getElementById('ir-search').value.toLowerCase().trim();
  var cards = document.querySelectorAll('#ir-list .ir-card');
  var shown = 0;
  cards.forEach(function(c) {{
    var ok = !q || c.dataset.n.includes(q);
    c.style.display = ok ? '' : 'none';
    if (ok) shown++;
  }});
  document.getElementById('ir-count').textContent = 'Showing ' + shown + ' items';
}}
</script>
"""
    return HTMLResponse(admin_shell("Item Routes", body, admin.business_name, "/admin/item-routes"))


# ==========================
# BONDS ADMIN
# ==========================

@router.get("/admin/bonds", response_class=HTMLResponse)
def admin_bonds(
    session_token: Optional[str] = Cookie(None),
    currency: Optional[str] = Query(None),
    player: Optional[str] = Query(None),
):
    admin, redirect = _guard(session_token)
    if redirect:
        return redirect

    from reserve_banks import get_all_active_bonds, get_all_banks
    from auth import SessionLocal as AuthSession, Player

    all_bonds = get_all_active_bonds()
    banks     = get_all_banks()

    # Build player-name lookup from the auth DB for all holder IDs
    player_ids = {b["holder_player_id"] for b in all_bonds if not b["is_interbank"]}
    auth_db = AuthSession()
    try:
        players_map = {
            p.id: p.business_name
            for p in auth_db.query(Player).filter(Player.id.in_(player_ids)).all()
        } if player_ids else {}
    finally:
        auth_db.close()

    # Filter controls
    currency_filter = (currency or "").upper().strip()
    player_filter   = (player or "").strip().lower()

    filtered = all_bonds
    if currency_filter:
        filtered = [b for b in filtered if b["currency_code"] == currency_filter]
    if player_filter:
        filtered = [
            b for b in filtered
            if player_filter in str(b["holder_player_id"])
            or player_filter in players_map.get(b["holder_player_id"], "").lower()
        ]

    # Summary stats per currency
    summary: dict = {}
    for b in all_bonds:
        c = b["currency_code"]
        if c not in summary:
            summary[c] = {"flag": b["flag"], "count": 0, "face_wsc": 0.0, "interbank": 0}
        summary[c]["count"]    += 1
        summary[c]["face_wsc"] += b["face_value_wsc"]
        if b["is_interbank"]:
            summary[c]["interbank"] += 1

    currency_opts = "".join(
        f'<option value="{b["code"]}" {"selected" if b["code"] == currency_filter else ""}>{b["flag"]} {b["code"]}</option>'
        for b in banks
    )

    summary_rows = "".join(
        f'<tr>'
        f'<td>{v["flag"]} {c}</td>'
        f'<td>{v["count"]}</td>'
        f'<td style="color:#94a3b8;">{v["interbank"]}</td>'
        f'<td>${v["face_wsc"]:,.2f}</td>'
        f'</tr>'
        for c, v in sorted(summary.items())
    )

    bond_rows = ""
    for b in filtered:
        if b["is_interbank"]:
            holder_cell = '<span style="color:#64748b;font-size:0.7rem;">INTERBANK</span>'
        else:
            name = players_map.get(b["holder_player_id"], "?")
            holder_cell = f'<a href="/admin/player/{b["holder_player_id"]}" style="color:#38bdf8;">#{b["holder_player_id"]} {name}</a>'

        # Highlight if yield is stuck at floor
        at_floor = abs(b["current_yield_pct"] - b["min_yield_pct"]) < 0.0001
        yield_style = ' style="color:#f87171;font-weight:bold;"' if at_floor else ""
        floor_note  = ' ⚠ floor' if at_floor else ""

        bond_rows += (
            f'<tr>'
            f'<td>#{b["id"]}</td>'
            f'<td>{b["flag"]} {b["currency_code"]}</td>'
            f'<td>{holder_cell}</td>'
            f'<td>${b["face_value_wsc"]:,.2f}</td>'
            f'<td>{b["purchase_yield_pct"]:.4f}%</td>'
            f'<td{yield_style}>{b["current_yield_pct"]:.4f}%{floor_note}</td>'
            f'<td style="color:#64748b;font-size:0.7rem;">[{b["min_yield_pct"]:.3f}%, {b["max_yield_pct"]:.3f}%]</td>'
            f'<td>{b["interest_accrued"]:.6f} {b["currency_code"]}</td>'
            f'<td>{b["remaining_days"]}d</td>'
            f'<td style="color:#64748b;font-size:0.7rem;">{b["matures_at"]}</td>'
            f'</tr>'
        )

    body = f"""
<h2 style="font-size:0.9rem;margin-bottom:10px;">Bond Holdings — {len(all_bonds)} active bonds</h2>

<div class="card">
    <h3>By Currency</h3>
    <div class="table-wrap">
        <table>
            <tr><th>Currency</th><th>Bonds</th><th>Interbank</th><th>Face Value (WSC)</th></tr>
            {summary_rows}
        </table>
    </div>
</div>

<div class="card">
    <h3>Filter</h3>
    <form method="get" action="/admin/bonds" style="display:flex;gap:8px;flex-wrap:wrap;align-items:flex-end;">
        <div>
            <div class="form-label">Currency</div>
            <select name="currency">
                <option value="">All</option>
                {currency_opts}
            </select>
        </div>
        <div>
            <div class="form-label">Player ID or name</div>
            <input type="text" name="player" value="{player_filter}" placeholder="ID or name fragment">
        </div>
        <button type="submit" class="btn btn-gray">Filter</button>
        <a href="/admin/bonds" class="btn btn-gray">Clear</a>
    </form>
</div>

<div class="card">
    <h3>Active Bonds ({len(filtered)} shown)</h3>
    {'<div class="table-wrap"><table>'
     '<tr><th>#</th><th>Currency</th><th>Holder</th><th>Face WSC</th>'
     '<th>Buy Yield</th><th>Cur Yield</th><th>Band</th>'
     '<th>Accrued Interest</th><th>Remaining</th><th>Matures</th></tr>'
     + bond_rows + '</table></div>'
     if bond_rows else '<p style="color:#64748b;font-size:0.75rem;">No bonds match the filter.</p>'}
    <p style="font-size:0.65rem;color:#475569;margin-top:8px;">
        ⚠ <span style="color:#f87171;">Red yield</span> = bond is at its floor. Interbank bonds (holder=0) are system instruments — no interest, no payout.
    </p>
</div>
"""
    return HTMLResponse(admin_shell("Bonds", body, admin.business_name, "/admin/bonds"))


# ── Notification Sound Admin ───────────────────────────────────────────────────

import shutil as _shutil

_SOUNDS_DIR = os.path.join(os.path.dirname(__file__), "static", "sounds")
_NOTIF_SOUND_PATH = os.path.join(_SOUNDS_DIR, "notification.mp3")
_ALLOWED_SOUND_EXTS = {".mp3", ".ogg", ".wav", ".m4a", ".aac"}


@router.get("/admin/notification-sound", response_class=HTMLResponse)
def admin_notif_sound(
    session_token: Optional[str] = Cookie(None),
    msg: Optional[str] = Query(None),
    err: Optional[str] = Query(None),
):
    admin, redirect = _guard(session_token)
    if redirect:
        return redirect

    has_sound = os.path.exists(_NOTIF_SOUND_PATH)
    size_kb   = round(os.path.getsize(_NOTIF_SOUND_PATH) / 1024, 1) if has_sound else 0

    _audio_tag  = '<audio controls src="/static/sounds/notification.mp3" style="width:100%;margin-bottom:8px;"></audio>' if has_sound else '<p style="color:#64748b;font-size:0.82rem;">No sound file uploaded yet.</p>'
    _size_tag   = f'<p style="font-size:0.72rem;color:#64748b;">notification.mp3 &nbsp;·&nbsp; {size_kb} KB</p>' if has_sound else ''
    current_html = f"""
<div style="background:#0f172a;border:1px solid #1e293b;border-radius:6px;padding:16px 20px;margin-bottom:20px;">
  <div style="font-size:0.72rem;font-weight:bold;color:#475569;text-transform:uppercase;
              letter-spacing:.08em;margin-bottom:10px;">Current Sound File</div>
  {_audio_tag}
  {_size_tag}
</div>"""

    _delete_form = '<form method="post" action="/admin/notification-sound/delete" style="margin-top:12px;"><button type="submit" onclick="return confirm(\'Delete the current notification sound?\')" style="padding:5px 14px;background:transparent;border:1px solid #7f1d1d;border-radius:5px;color:#ef4444;font-size:0.75rem;cursor:pointer;">Delete Current Sound</button></form>' if has_sound else ''
    msg_html = f'<div style="background:#14532d;border:1px solid #4ade80;color:#4ade80;padding:8px 14px;border-radius:5px;margin-bottom:16px;font-size:0.82rem;">{msg}</div>' if msg else ""
    err_html = f'<div style="background:#450a0a;border:1px solid #ef4444;color:#ef4444;padding:8px 14px;border-radius:5px;margin-bottom:16px;font-size:0.82rem;">{err}</div>' if err else ""

    body = f"""
<h2 style="margin:0 0 20px;color:#e5e7eb;">🔔 Notification Sound</h2>
{msg_html}{err_html}
{current_html}
<div style="background:#0f172a;border:1px solid #1e293b;border-radius:6px;padding:16px 20px;">
  <div style="font-size:0.72rem;font-weight:bold;color:#475569;text-transform:uppercase;
              letter-spacing:.08em;margin-bottom:10px;">Upload New Sound</div>
  <p style="font-size:0.78rem;color:#64748b;margin:0 0 14px;">
    Accepted formats: mp3, ogg, wav, m4a, aac. The file is saved as
    <code style="color:#94a3b8;">notification.mp3</code> and played to all players when
    a new in-app notification arrives (if they have sounds enabled).
  </p>
  <form method="post" action="/admin/notification-sound/upload"
        enctype="multipart/form-data" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;">
    <input type="file" name="sound_file" accept=".mp3,.ogg,.wav,.m4a,.aac"
           required style="font-size:0.82rem;color:#e5e7eb;">
    <button type="submit"
            style="padding:7px 18px;background:#6366f1;border:none;border-radius:5px;
                   color:white;font-size:0.82rem;cursor:pointer;font-weight:bold;">
      Upload &amp; Replace
    </button>
  </form>
  {_delete_form}
</div>
"""
    return HTMLResponse(admin_shell("Notification Sound", body, admin.business_name, "/admin/notification-sound"))


@router.post("/admin/notification-sound/upload", response_class=HTMLResponse)
async def admin_notif_sound_upload(
    session_token: Optional[str] = Cookie(None),
    sound_file: UploadFile = File(...),
):
    admin, redirect = _guard(session_token)
    if redirect:
        return redirect

    ext = os.path.splitext(sound_file.filename or "")[1].lower()
    if ext not in _ALLOWED_SOUND_EXTS:
        return RedirectResponse(
            url=f"/admin/notification-sound?err=Invalid+file+type+{ext}",
            status_code=303,
        )

    os.makedirs(_SOUNDS_DIR, exist_ok=True)
    try:
        content = await sound_file.read()
        if len(content) > 10 * 1024 * 1024:  # 10 MB limit
            return RedirectResponse(
                url="/admin/notification-sound?err=File+too+large+(max+10+MB)",
                status_code=303,
            )
        with open(_NOTIF_SOUND_PATH, "wb") as f:
            f.write(content)
    except Exception as e:
        return RedirectResponse(
            url=f"/admin/notification-sound?err=Upload+failed:+{str(e)[:60]}",
            status_code=303,
        )

    return RedirectResponse(
        url="/admin/notification-sound?msg=Sound+uploaded+successfully",
        status_code=303,
    )


@router.post("/admin/notification-sound/delete", response_class=HTMLResponse)
def admin_notif_sound_delete(session_token: Optional[str] = Cookie(None)):
    admin, redirect = _guard(session_token)
    if redirect:
        return redirect
    try:
        if os.path.exists(_NOTIF_SOUND_PATH):
            os.remove(_NOTIF_SOUND_PATH)
    except Exception as e:
        return RedirectResponse(
            url=f"/admin/notification-sound?err=Delete+failed:+{str(e)[:60]}",
            status_code=303,
        )
    return RedirectResponse(
        url="/admin/notification-sound?msg=Sound+deleted",
        status_code=303,
    )


# ── VAPID key viewer (admin only) ─────────────────────────────────────────────

@router.get("/admin/push-keys", response_class=HTMLResponse)
def admin_push_keys(session_token: Optional[str] = Cookie(None)):
    admin, redirect = _guard(session_token)
    if redirect:
        return redirect

    from push_ux import get_vapid_keys
    keys    = get_vapid_keys()
    pub     = keys["public_key"]  if keys else "— not generated —"
    priv    = keys["private_key"] if keys else "— not generated —"
    env_set = bool(os.environ.get("VAPID_PUBLIC_KEY"))

    env_status = (
        '<span style="color:#4ade80;">✓ VAPID_PUBLIC_KEY env var is set — keys pinned</span>'
        if env_set else
        '<span style="color:#f59e0b;">⚠ Env vars not set — keys stored in DB (will regenerate if DB is wiped)</span>'
    )

    body = f"""
<h2 style="margin:0 0 20px;color:#e5e7eb;">🔑 VAPID Push Keys</h2>
<p style="color:#64748b;font-size:0.82rem;margin-bottom:16px;">
  To pin keys permanently, set these as environment variables on your server.
  Without env vars, keys are stored in the DB and regenerate if the DB is wiped —
  which invalidates all existing push subscriptions.
</p>
<div style="margin-bottom:8px;">{env_status}</div>

<div style="background:#0f172a;border:1px solid #1e293b;border-radius:6px;padding:20px;margin-top:16px;">
  <div style="margin-bottom:16px;">
    <div style="font-size:0.72rem;font-weight:bold;color:#475569;text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px;">VAPID_PUBLIC_KEY</div>
    <code style="display:block;background:#020617;padding:10px 14px;border-radius:4px;
                 color:#a5f3fc;font-size:0.75rem;word-break:break-all;border:1px solid #1e293b;">{pub}</code>
  </div>
  <div>
    <div style="font-size:0.72rem;font-weight:bold;color:#475569;text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px;">VAPID_PRIVATE_KEY</div>
    <code style="display:block;background:#020617;padding:10px 14px;border-radius:4px;
                 color:#fca5a5;font-size:0.75rem;word-break:break-all;border:1px solid #1e293b;">{priv}</code>
  </div>
</div>
<p style="color:#475569;font-size:0.72rem;margin-top:12px;">
  Set both as environment variables on your server and restart — the 503 on /api/push/public-key will be gone.
</p>
"""
    return HTMLResponse(admin_shell("VAPID Keys", body, admin.business_name, "/admin/notification-sound"))
