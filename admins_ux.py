"""
admins_ux.py - Admin Dashboard UI

The admin command center for managing the game.
Features:
- Post messages to the Updates channel
- View and edit all player data
- Kick / ban / timeout players
- View P2P contract activity
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
    ban_player, timeout_player, kick_player, revoke_ban, get_active_ban,
    post_update, get_p2p_overview, get_admin_logs,
)

router = APIRouter()


# ==========================
# SHELL
# ==========================

def admin_shell(title: str, body: str, player_name: str = "") -> str:
    """Admin dashboard shell - dark theme with red accent."""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{title} - Admin</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            * {{ box-sizing: border-box; margin: 0; padding: 0; }}
            body {{
                background: #020617;
                color: #e5e7eb;
                font-family: 'JetBrains Mono', monospace;
                font-size: 14px;
            }}
            a {{ color: #38bdf8; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}

            .header {{
                border-bottom: 1px solid #7f1d1d;
                padding: 10px 16px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                background: #0a0f1e;
            }}
            .header-left {{
                display: flex; align-items: center; gap: 10px;
            }}
            .brand {{ font-weight: bold; color: #ef4444; font-size: 1rem; }}
            .header-right {{
                display: flex; align-items: center; gap: 12px; font-size: 0.8rem;
            }}

            .nav {{
                display: flex;
                gap: 0;
                border-bottom: 1px solid #1e293b;
                background: #0a0f1e;
                overflow-x: auto;
            }}
            .nav a {{
                padding: 10px 16px;
                color: #94a3b8;
                font-size: 0.8rem;
                white-space: nowrap;
                border-bottom: 2px solid transparent;
            }}
            .nav a:hover {{ color: #e5e7eb; text-decoration: none; background: #1e293b; }}
            .nav a.active {{ color: #ef4444; border-bottom-color: #ef4444; font-weight: bold; }}

            .container {{
                max-width: 1100px;
                margin: 0 auto;
                padding: 20px 16px;
            }}

            .card {{
                background: #0f172a;
                border: 1px solid #1e293b;
                padding: 16px;
                margin-bottom: 16px;
                border-radius: 4px;
            }}
            .card h3 {{
                font-size: 0.9rem;
                color: #e5e7eb;
                margin-bottom: 12px;
                border-bottom: 1px solid #1e293b;
                padding-bottom: 8px;
            }}

            table {{
                width: 100%;
                border-collapse: collapse;
                font-size: 0.8rem;
            }}
            th {{
                text-align: left;
                padding: 8px 6px;
                color: #64748b;
                font-size: 0.7rem;
                text-transform: uppercase;
                border-bottom: 1px solid #1e293b;
            }}
            td {{
                padding: 8px 6px;
                border-bottom: 1px solid #0f172a;
                vertical-align: middle;
            }}
            tr:hover {{ background: #1e293b; }}

            .badge {{
                font-size: 0.65rem;
                padding: 2px 6px;
                border-radius: 3px;
                font-weight: bold;
            }}
            .badge-red {{ background: #7f1d1d; color: #fca5a5; }}
            .badge-yellow {{ background: #78350f; color: #fcd34d; }}
            .badge-green {{ background: #14532d; color: #86efac; }}
            .badge-blue {{ background: #1e3a5f; color: #93c5fd; }}

            .btn {{
                border: none;
                padding: 6px 12px;
                cursor: pointer;
                font-size: 0.75rem;
                font-family: inherit;
                border-radius: 3px;
                font-weight: bold;
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

            input, select, textarea {{
                background: #020617;
                border: 1px solid #1e293b;
                color: #e5e7eb;
                padding: 6px 10px;
                font-family: inherit;
                font-size: 0.85rem;
                border-radius: 3px;
            }}
            input:focus, select:focus, textarea:focus {{
                outline: none;
                border-color: #ef4444;
            }}
            textarea {{
                resize: vertical;
                width: 100%;
            }}

            .stat-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
                gap: 10px;
                margin-bottom: 16px;
            }}
            .stat-box {{
                background: #0f172a;
                border: 1px solid #1e293b;
                padding: 12px;
                border-radius: 4px;
                text-align: center;
            }}
            .stat-box .stat-value {{
                font-size: 1.4rem;
                font-weight: bold;
                color: #e5e7eb;
            }}
            .stat-box .stat-label {{
                font-size: 0.65rem;
                color: #64748b;
                text-transform: uppercase;
                margin-top: 4px;
            }}

            .detail-row {{
                display: flex;
                justify-content: space-between;
                padding: 8px 0;
                border-bottom: 1px solid #1e293b;
                font-size: 0.82rem;
            }}
            .detail-row .label {{ color: #64748b; }}
            .detail-row .value {{ color: #e5e7eb; }}

            .flash {{
                padding: 10px 14px;
                border-radius: 4px;
                margin-bottom: 12px;
                font-size: 0.8rem;
            }}
            .flash-success {{ background: #14532d; color: #86efac; border: 1px solid #166534; }}
            .flash-error {{ background: #7f1d1d; color: #fca5a5; border: 1px solid #991b1b; }}

            @media (max-width: 640px) {{
                .container {{ padding: 12px 8px; }}
                table {{ font-size: 0.72rem; }}
                .stat-grid {{ grid-template-columns: repeat(2, 1fr); }}
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="header-left">
                <span class="brand">ADMIN PANEL</span>
                <span style="color: #475569; font-size: 0.75rem;">Wadsworth</span>
            </div>
            <div class="header-right">
                <span style="color: #94a3b8;">{player_name}</span>
                <a href="/dashboard" style="color: #94a3b8;">Game</a>
                <a href="/chat" style="color: #94a3b8;">Chat</a>
                <a href="/api/logout" style="color: #ef4444;">Logout</a>
            </div>
        </div>
        <div class="nav">
            <a href="/admin">Dashboard</a>
            <a href="/admin/players">Players</a>
            <a href="/admin/updates">Updates</a>
            <a href="/admin/p2p">P2P</a>
            <a href="/admin/logs">Logs</a>
        </div>
        <div class="container">
            {body}
        </div>
    </body>
    </html>
    """


def _nav_active(current: str) -> str:
    """Return JS snippet to highlight current nav tab."""
    return f"""
    <script>
    document.querySelectorAll('.nav a').forEach(a => {{
        if (a.getAttribute('href') === '{current}') {{
            a.classList.add('active');
        }}
    }});
    </script>
    """


# ==========================
# AUTH GUARD
# ==========================

def _require_admin(session_token):
    """Check admin auth; returns (player, redirect_or_none)."""
    player = require_admin(session_token)
    if not player:
        return None, RedirectResponse(url="/login", status_code=303)
    return player, None


# ==========================
# DASHBOARD (overview)
# ==========================

@router.get("/admin", response_class=HTMLResponse)
def admin_dashboard(session_token: Optional[str] = Cookie(None)):
    player, redirect = _require_admin(session_token)
    if redirect:
        return redirect

    players = get_all_players()
    total_players = len(players)
    total_cash = sum(p["cash_balance"] for p in players)
    banned_count = sum(1 for p in players if p["ban_status"] == "ban")
    timed_out_count = sum(1 for p in players if p["ban_status"] == "timeout")

    # Online count from chat manager
    try:
        from chat import manager
        online_count = manager.get_online_count()
    except Exception:
        online_count = 0

    # Recent admin actions
    logs = get_admin_logs(limit=10)
    log_rows = ""
    for log in logs:
        ts = log["created_at"][:16].replace("T", " ") if log["created_at"] else "-"
        target = f"#{log['target_player_id']}" if log["target_player_id"] else "-"
        log_rows += f"""
        <tr>
            <td style="color: #64748b;">{ts}</td>
            <td>{log["action"]}</td>
            <td>{target}</td>
            <td style="color: #94a3b8; max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{log["details"][:60]}</td>
        </tr>
        """

    body = f"""
    <h2 style="font-size: 1rem; margin-bottom: 16px; color: #ef4444;">Command Center</h2>

    <div class="stat-grid">
        <div class="stat-box">
            <div class="stat-value">{total_players}</div>
            <div class="stat-label">Total Players</div>
        </div>
        <div class="stat-box">
            <div class="stat-value" style="color: #22c55e;">{online_count}</div>
            <div class="stat-label">Online Now</div>
        </div>
        <div class="stat-box">
            <div class="stat-value" style="color: #22c55e;">${total_cash:,.0f}</div>
            <div class="stat-label">Total Cash</div>
        </div>
        <div class="stat-box">
            <div class="stat-value" style="color: #ef4444;">{banned_count}</div>
            <div class="stat-label">Banned</div>
        </div>
        <div class="stat-box">
            <div class="stat-value" style="color: #f59e0b;">{timed_out_count}</div>
            <div class="stat-label">Timed Out</div>
        </div>
    </div>

    <div class="card">
        <h3>Recent Admin Actions</h3>
        {f'''
        <table>
            <tr><th>Time</th><th>Action</th><th>Target</th><th>Details</th></tr>
            {log_rows}
        </table>
        ''' if log_rows else '<p style="color: #64748b; font-size: 0.8rem;">No admin actions yet.</p>'}
    </div>

    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
        <a href="/admin/updates" class="card" style="text-decoration: none; text-align: center;">
            <div style="font-size: 1.5rem; margin-bottom: 6px;">📢</div>
            <div style="color: #e5e7eb; font-weight: bold; font-size: 0.85rem;">Post Update</div>
            <div style="color: #64748b; font-size: 0.7rem; margin-top: 4px;">Send message to Updates channel</div>
        </a>
        <a href="/admin/players" class="card" style="text-decoration: none; text-align: center;">
            <div style="font-size: 1.5rem; margin-bottom: 6px;">👥</div>
            <div style="color: #e5e7eb; font-weight: bold; font-size: 0.85rem;">Manage Players</div>
            <div style="color: #64748b; font-size: 0.7rem; margin-top: 4px;">View, edit, kick, ban players</div>
        </a>
        <a href="/admin/p2p" class="card" style="text-decoration: none; text-align: center;">
            <div style="font-size: 1.5rem; margin-bottom: 6px;">📋</div>
            <div style="color: #e5e7eb; font-weight: bold; font-size: 0.85rem;">P2P Contracts</div>
            <div style="color: #64748b; font-size: 0.7rem; margin-top: 4px;">View contract activity</div>
        </a>
        <a href="/admin/logs" class="card" style="text-decoration: none; text-align: center;">
            <div style="font-size: 1.5rem; margin-bottom: 6px;">📜</div>
            <div style="color: #e5e7eb; font-weight: bold; font-size: 0.85rem;">Audit Log</div>
            <div style="color: #64748b; font-size: 0.7rem; margin-top: 4px;">All admin actions</div>
        </a>
    </div>

    {_nav_active("/admin")}
    """

    return HTMLResponse(admin_shell("Dashboard", body, player.business_name))


# ==========================
# PLAYERS LIST
# ==========================

@router.get("/admin/players", response_class=HTMLResponse)
def admin_players(
    session_token: Optional[str] = Cookie(None),
    msg: Optional[str] = Query(None),
):
    player, redirect = _require_admin(session_token)
    if redirect:
        return redirect

    players = get_all_players()

    flash = ""
    if msg:
        flash = f'<div class="flash flash-success">{msg}</div>'

    rows = ""
    for p in players:
        admin_badge = '<span class="badge badge-blue">ADMIN</span>' if p["is_admin"] else ""
        ban_badge = ""
        if p["ban_status"] == "ban":
            ban_badge = '<span class="badge badge-red">BANNED</span>'
        elif p["ban_status"] == "timeout":
            ban_badge = '<span class="badge badge-yellow">TIMEOUT</span>'

        last_login = p["last_login"][:16].replace("T", " ") if p["last_login"] else "-"

        # Online check
        try:
            from chat import manager as chat_mgr
            online = p["id"] in chat_mgr.connections
        except Exception:
            online = False
        online_dot = '<span style="color: #22c55e;">●</span>' if online else '<span style="color: #475569;">○</span>'

        rows += f"""
        <tr>
            <td>{online_dot} #{p["id"]}</td>
            <td><a href="/admin/player/{p["id"]}">{p["business_name"]}</a> {admin_badge} {ban_badge}</td>
            <td style="color: #22c55e;">${p["cash_balance"]:,.2f}</td>
            <td style="color: #64748b;">{last_login}</td>
            <td>
                <a href="/admin/player/{p["id"]}" class="btn btn-blue" style="font-size: 0.7rem; padding: 3px 8px; text-decoration: none;">View</a>
            </td>
        </tr>
        """

    body = f"""
    <h2 style="font-size: 1rem; margin-bottom: 16px;">All Players ({len(players)})</h2>
    {flash}
    <div class="card" style="overflow-x: auto;">
        <table>
            <tr><th>ID</th><th>Name</th><th>Cash</th><th>Last Login</th><th></th></tr>
            {rows}
        </table>
    </div>
    {_nav_active("/admin/players")}
    """

    return HTMLResponse(admin_shell("Players", body, player.business_name))


# ==========================
# PLAYER DETAIL
# ==========================

@router.get("/admin/player/{player_id}", response_class=HTMLResponse)
def admin_player_detail(
    player_id: int,
    session_token: Optional[str] = Cookie(None),
    msg: Optional[str] = Query(None),
    err: Optional[str] = Query(None),
):
    admin, redirect = _require_admin(session_token)
    if redirect:
        return redirect

    detail = get_player_detail(player_id)
    if not detail:
        return HTMLResponse(admin_shell("Not Found", '<p style="color: #ef4444;">Player not found.</p>', admin.business_name))

    flash = ""
    if msg:
        flash = f'<div class="flash flash-success">{msg}</div>'
    if err:
        flash = f'<div class="flash flash-error">{err}</div>'

    # Online check
    try:
        from chat import manager as chat_mgr
        online = player_id in chat_mgr.connections
    except Exception:
        online = False
    online_html = '<span style="color: #22c55e;">● Online</span>' if online else '<span style="color: #64748b;">○ Offline</span>'

    admin_badge = '<span class="badge badge-blue" style="margin-left: 8px;">ADMIN</span>' if detail["is_admin"] else ""
    ban_html = ""
    if detail["active_ban"]:
        ab = detail["active_ban"]
        if ab["type"] == "ban":
            ban_html = f"""
            <div class="flash flash-error">
                PERMANENTLY BANNED — {ab["reason"] or "No reason given"}
                <form method="post" action="/admin/player/{player_id}/revoke" style="display: inline; margin-left: 10px;">
                    <input type="hidden" name="ban_id" value="{ab["id"]}">
                    <button type="submit" class="btn btn-green" style="font-size: 0.7rem;">Unban</button>
                </form>
            </div>
            """
        elif ab["type"] == "timeout":
            ban_html = f"""
            <div class="flash" style="background: #78350f; color: #fcd34d; border: 1px solid #92400e;">
                TIMED OUT until {ab["expires_at"][:16].replace("T", " ")} UTC — {ab["reason"] or "No reason given"}
                <form method="post" action="/admin/player/{player_id}/revoke" style="display: inline; margin-left: 10px;">
                    <input type="hidden" name="ban_id" value="{ab["id"]}">
                    <button type="submit" class="btn btn-green" style="font-size: 0.7rem;">Remove</button>
                </form>
            </div>
            """

    created = detail["created_at"][:16].replace("T", " ") if detail["created_at"] else "-"
    last_login = detail["last_login"][:16].replace("T", " ") if detail["last_login"] else "-"

    # Ban history table
    ban_rows = ""
    for b in detail.get("bans", []):
        ts = b["created_at"][:16].replace("T", " ") if b["created_at"] else "-"
        exp = b["expires_at"][:16].replace("T", " ") if b["expires_at"] else "Never"
        status = "Revoked" if b["revoked"] else "Active"
        status_color = "#64748b" if b["revoked"] else "#ef4444"
        ban_rows += f"""
        <tr>
            <td>#{b["id"]}</td>
            <td>{b["ban_type"].upper()}</td>
            <td style="color: #94a3b8;">{b["reason"] or "-"}</td>
            <td style="color: #64748b;">{ts}</td>
            <td style="color: #64748b;">{exp}</td>
            <td style="color: {status_color};">{status}</td>
        </tr>
        """

    body = f"""
    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 16px;">
        <a href="/admin/players" style="color: #64748b; font-size: 0.8rem;">&larr; Back</a>
        <h2 style="font-size: 1rem;">Player #{player_id}: {detail["business_name"]}{admin_badge}</h2>
        <span style="font-size: 0.8rem;">{online_html}</span>
    </div>
    {flash}
    {ban_html}

    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
        <!-- Info -->
        <div class="card">
            <h3>Player Info</h3>
            <div class="detail-row"><span class="label">ID</span><span class="value">#{detail["id"]}</span></div>
            <div class="detail-row"><span class="label">Business Name</span><span class="value">{detail["business_name"]}</span></div>
            <div class="detail-row"><span class="label">Cash Balance</span><span class="value" style="color: #22c55e;">${detail["cash_balance"]:,.2f}</span></div>
            <div class="detail-row"><span class="label">City</span><span class="value">{detail["city"] or "None"}</span></div>
            <div class="detail-row"><span class="label">Registered</span><span class="value">{created}</span></div>
            <div class="detail-row"><span class="label">Last Login</span><span class="value">{last_login}</span></div>
        </div>

        <!-- Actions -->
        <div class="card">
            <h3>Admin Actions</h3>

            <!-- Edit Balance -->
            <form method="post" action="/admin/player/{player_id}/balance" style="margin-bottom: 16px;">
                <div style="font-size: 0.75rem; color: #64748b; margin-bottom: 4px;">Set Cash Balance</div>
                <div style="display: flex; gap: 6px;">
                    <input type="number" name="new_balance" step="0.01" value="{detail['cash_balance']:.2f}" style="flex: 1; min-width: 0;">
                    <button type="submit" class="btn btn-blue">Set</button>
                </div>
            </form>

            <!-- Kick -->
            <form method="post" action="/admin/player/{player_id}/kick" style="margin-bottom: 10px;">
                <div style="font-size: 0.75rem; color: #64748b; margin-bottom: 4px;">Kick (disconnect now)</div>
                <div style="display: flex; gap: 6px;">
                    <input type="text" name="reason" placeholder="Reason (optional)" style="flex: 1; min-width: 0;">
                    <button type="submit" class="btn btn-yellow">Kick</button>
                </div>
            </form>

            <!-- Timeout -->
            <form method="post" action="/admin/player/{player_id}/timeout" style="margin-bottom: 10px;">
                <div style="font-size: 0.75rem; color: #64748b; margin-bottom: 4px;">Timeout (temp block)</div>
                <div style="display: flex; gap: 6px;">
                    <input type="number" name="minutes" placeholder="Minutes" min="1" style="width: 80px;">
                    <input type="text" name="reason" placeholder="Reason (optional)" style="flex: 1; min-width: 0;">
                    <button type="submit" class="btn btn-yellow">Timeout</button>
                </div>
            </form>

            <!-- Ban -->
            <form method="post" action="/admin/player/{player_id}/ban">
                <div style="font-size: 0.75rem; color: #64748b; margin-bottom: 4px;">Ban (permanent)</div>
                <div style="display: flex; gap: 6px;">
                    <input type="text" name="reason" placeholder="Reason (optional)" style="flex: 1; min-width: 0;">
                    <button type="submit" class="btn btn-red">Ban</button>
                </div>
            </form>
        </div>
    </div>

    <!-- Ban History -->
    <div class="card">
        <h3>Moderation History</h3>
        {f'''
        <table>
            <tr><th>ID</th><th>Type</th><th>Reason</th><th>Date</th><th>Expires</th><th>Status</th></tr>
            {ban_rows}
        </table>
        ''' if ban_rows else '<p style="color: #64748b; font-size: 0.8rem;">No moderation history.</p>'}
    </div>

    {_nav_active("/admin/players")}
    """

    return HTMLResponse(admin_shell(f"Player #{player_id}", body, admin.business_name))


# ==========================
# PLAYER ACTIONS (POST)
# ==========================

@router.post("/admin/player/{player_id}/balance")
def admin_set_balance(
    player_id: int,
    session_token: Optional[str] = Cookie(None),
    new_balance: float = Form(...),
):
    admin, redirect = _require_admin(session_token)
    if redirect:
        return redirect
    result = edit_player_balance(admin.id, player_id, new_balance)
    if result["ok"]:
        return RedirectResponse(
            url=f"/admin/player/{player_id}?msg=Balance+updated+to+${new_balance:,.2f}",
            status_code=303,
        )
    return RedirectResponse(
        url=f"/admin/player/{player_id}?err={result['error']}",
        status_code=303,
    )


@router.post("/admin/player/{player_id}/kick")
def admin_kick(
    player_id: int,
    session_token: Optional[str] = Cookie(None),
    reason: str = Form(""),
):
    admin, redirect = _require_admin(session_token)
    if redirect:
        return redirect
    kick_player(admin.id, player_id, reason)

    # Force disconnect from chat websocket
    try:
        from chat import manager as chat_mgr
        import asyncio
        ws = chat_mgr.connections.get(player_id)
        if ws:
            asyncio.create_task(ws.close(code=4002, reason="Kicked by admin"))
    except Exception:
        pass

    # Invalidate sessions
    _invalidate_player_sessions(player_id)

    return RedirectResponse(
        url=f"/admin/player/{player_id}?msg=Player+kicked",
        status_code=303,
    )


@router.post("/admin/player/{player_id}/timeout")
def admin_timeout(
    player_id: int,
    session_token: Optional[str] = Cookie(None),
    minutes: int = Form(...),
    reason: str = Form(""),
):
    admin, redirect = _require_admin(session_token)
    if redirect:
        return redirect
    result = timeout_player(admin.id, player_id, minutes, reason)
    if not result["ok"]:
        return RedirectResponse(
            url=f"/admin/player/{player_id}?err={result['error']}",
            status_code=303,
        )

    # Force disconnect
    try:
        from chat import manager as chat_mgr
        import asyncio
        ws = chat_mgr.connections.get(player_id)
        if ws:
            asyncio.create_task(ws.close(code=4003, reason="Timed out by admin"))
    except Exception:
        pass

    _invalidate_player_sessions(player_id)

    return RedirectResponse(
        url=f"/admin/player/{player_id}?msg=Player+timed+out+for+{minutes}+minutes",
        status_code=303,
    )


@router.post("/admin/player/{player_id}/ban")
def admin_ban(
    player_id: int,
    session_token: Optional[str] = Cookie(None),
    reason: str = Form(""),
):
    admin, redirect = _require_admin(session_token)
    if redirect:
        return redirect
    ban_player(admin.id, player_id, reason)

    # Force disconnect
    try:
        from chat import manager as chat_mgr
        import asyncio
        ws = chat_mgr.connections.get(player_id)
        if ws:
            asyncio.create_task(ws.close(code=4004, reason="Banned by admin"))
    except Exception:
        pass

    _invalidate_player_sessions(player_id)

    return RedirectResponse(
        url=f"/admin/player/{player_id}?msg=Player+banned",
        status_code=303,
    )


@router.post("/admin/player/{player_id}/revoke")
def admin_revoke(
    player_id: int,
    session_token: Optional[str] = Cookie(None),
    ban_id: int = Form(...),
):
    admin, redirect = _require_admin(session_token)
    if redirect:
        return redirect
    result = revoke_ban(admin.id, ban_id)
    if result["ok"]:
        return RedirectResponse(
            url=f"/admin/player/{player_id}?msg=Ban+revoked",
            status_code=303,
        )
    return RedirectResponse(
        url=f"/admin/player/{player_id}?err={result['error']}",
        status_code=303,
    )


def _invalidate_player_sessions(player_id: int):
    """Remove all sessions for a player so they're forced to re-login."""
    try:
        import auth
        db = auth.get_db()
        sessions = db.query(auth.Session).filter(auth.Session.player_id == player_id).all()
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
def admin_updates_page(
    session_token: Optional[str] = Cookie(None),
    msg: Optional[str] = Query(None),
):
    player, redirect = _require_admin(session_token)
    if redirect:
        return redirect

    flash = ""
    if msg:
        flash = f'<div class="flash flash-success">{msg}</div>'

    # Show recent updates messages
    from chat import get_room_messages
    messages = get_room_messages("updates", limit=30)
    msg_rows = ""
    for m in messages:
        ts = m["timestamp"][:16].replace("T", " ") if m.get("timestamp") else "-"
        msg_rows += f"""
        <tr>
            <td style="color: #64748b;">{ts}</td>
            <td style="color: #f59e0b;">{m["sender_name"]}</td>
            <td>{m["content"]}</td>
        </tr>
        """

    body = f"""
    <h2 style="font-size: 1rem; margin-bottom: 16px;">Updates Channel</h2>
    {flash}

    <div class="card">
        <h3>Post New Update</h3>
        <p style="font-size: 0.75rem; color: #64748b; margin-bottom: 10px;">
            This message will appear in the read-only Updates channel visible to all players.
        </p>
        <form method="post" action="/admin/updates/post">
            <textarea name="content" rows="3" maxlength="500" placeholder="Type your update message..." style="margin-bottom: 8px;" required></textarea>
            <button type="submit" class="btn btn-blue">Post Update</button>
        </form>
    </div>

    <div class="card">
        <h3>Recent Updates</h3>
        {f'''
        <table>
            <tr><th>Time</th><th>From</th><th>Message</th></tr>
            {msg_rows}
        </table>
        ''' if msg_rows else '<p style="color: #64748b; font-size: 0.8rem;">No updates posted yet.</p>'}
    </div>

    {_nav_active("/admin/updates")}
    """

    return HTMLResponse(admin_shell("Updates", body, player.business_name))


@router.post("/admin/updates/post")
def admin_post_update(
    session_token: Optional[str] = Cookie(None),
    content: str = Form(...),
):
    player, redirect = _require_admin(session_token)
    if redirect:
        return redirect

    result = post_update(player.id, content.strip())
    if result["ok"]:
        # Broadcast to connected chat users
        try:
            from chat import manager as chat_mgr
            import asyncio
            saved = result["message"]
            saved["type"] = "message"
            saved["avatar"] = chat_mgr.avatar_cache.get(player.id)
            asyncio.create_task(chat_mgr.broadcast_to_room("updates", saved))
        except Exception:
            pass

        return RedirectResponse(url="/admin/updates?msg=Update+posted", status_code=303)
    return RedirectResponse(url="/admin/updates?msg=Failed+to+post", status_code=303)


# ==========================
# P2P OVERVIEW
# ==========================

@router.get("/admin/p2p", response_class=HTMLResponse)
def admin_p2p(session_token: Optional[str] = Cookie(None)):
    player, redirect = _require_admin(session_token)
    if redirect:
        return redirect

    overview = get_p2p_overview()

    if "error" in overview:
        body = f"""
        <h2 style="font-size: 1rem; margin-bottom: 16px;">P2P Contracts</h2>
        <div class="card">
            <p style="color: #64748b;">P2P module not available: {overview["error"]}</p>
        </div>
        {_nav_active("/admin/p2p")}
        """
        return HTMLResponse(admin_shell("P2P", body, player.business_name))

    recent_rows = ""
    for c in overview.get("recent", []):
        ts = c["created_at"][:16].replace("T", " ") if c.get("created_at") else "-"
        status_colors = {
            "active": "#22c55e", "listed": "#38bdf8", "breached": "#ef4444",
            "completed": "#64748b", "draft": "#94a3b8", "voided": "#64748b",
        }
        sc = status_colors.get(c["status"], "#94a3b8")
        recent_rows += f"""
        <tr>
            <td>#{c["id"]}</td>
            <td>#{c["creator_id"]}</td>
            <td>{f'#{c["holder_id"]}' if c["holder_id"] else "-"}</td>
            <td style="color: {sc};">{c["status"].upper()}</td>
            <td>{c["bid_mode"] or "-"}</td>
            <td style="color: #64748b;">{ts}</td>
        </tr>
        """

    body = f"""
    <h2 style="font-size: 1rem; margin-bottom: 16px;">P2P Contracts</h2>

    <div class="stat-grid">
        <div class="stat-box">
            <div class="stat-value">{overview.get("total", 0)}</div>
            <div class="stat-label">Total</div>
        </div>
        <div class="stat-box">
            <div class="stat-value" style="color: #22c55e;">{overview.get("active", 0)}</div>
            <div class="stat-label">Active</div>
        </div>
        <div class="stat-box">
            <div class="stat-value" style="color: #38bdf8;">{overview.get("listed", 0)}</div>
            <div class="stat-label">Listed</div>
        </div>
        <div class="stat-box">
            <div class="stat-value" style="color: #ef4444;">{overview.get("breached", 0)}</div>
            <div class="stat-label">Breached</div>
        </div>
        <div class="stat-box">
            <div class="stat-value" style="color: #64748b;">{overview.get("completed", 0)}</div>
            <div class="stat-label">Completed</div>
        </div>
    </div>

    <div class="card">
        <h3>Recent Contracts</h3>
        {f'''
        <div style="overflow-x: auto;">
        <table>
            <tr><th>ID</th><th>Creator</th><th>Holder</th><th>Status</th><th>Mode</th><th>Created</th></tr>
            {recent_rows}
        </table>
        </div>
        ''' if recent_rows else '<p style="color: #64748b; font-size: 0.8rem;">No contracts found.</p>'}
    </div>

    {_nav_active("/admin/p2p")}
    """

    return HTMLResponse(admin_shell("P2P", body, player.business_name))


# ==========================
# AUDIT LOG
# ==========================

@router.get("/admin/logs", response_class=HTMLResponse)
def admin_logs_page(session_token: Optional[str] = Cookie(None)):
    player, redirect = _require_admin(session_token)
    if redirect:
        return redirect

    logs = get_admin_logs(limit=100)

    rows = ""
    for log in logs:
        ts = log["created_at"][:16].replace("T", " ") if log["created_at"] else "-"
        target = f'<a href="/admin/player/{log["target_player_id"]}">#{log["target_player_id"]}</a>' if log["target_player_id"] else "-"
        action_colors = {
            "ban": "#ef4444", "kick": "#f59e0b", "timeout": "#f59e0b",
            "revoke_ban": "#22c55e", "edit_balance": "#38bdf8", "post_update": "#a78bfa",
        }
        ac = action_colors.get(log["action"], "#94a3b8")
        rows += f"""
        <tr>
            <td style="color: #64748b;">{ts}</td>
            <td>Admin #{log["admin_id"]}</td>
            <td style="color: {ac}; font-weight: bold;">{log["action"].upper()}</td>
            <td>{target}</td>
            <td style="color: #94a3b8; max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{log["details"]}</td>
        </tr>
        """

    body = f"""
    <h2 style="font-size: 1rem; margin-bottom: 16px;">Admin Audit Log</h2>

    <div class="card" style="overflow-x: auto;">
        {f'''
        <table>
            <tr><th>Time</th><th>Admin</th><th>Action</th><th>Target</th><th>Details</th></tr>
            {rows}
        </table>
        ''' if rows else '<p style="color: #64748b; font-size: 0.8rem;">No admin actions recorded.</p>'}
    </div>

    {_nav_active("/admin/logs")}
    """

    return HTMLResponse(admin_shell("Audit Log", body, player.business_name))
