"""
mod_ux.py - Moderator Dashboard UI

Separate from /admin. Accessible by any player with moderator status (or full admin).
Features:
- Player search + recent message history
- Active chat mutes list with lift button
- Mod action audit log (last 100 actions)
- Mute / warn / delete-message actions
"""

from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Cookie, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse

from admins import (
    require_moderator,
    chat_mute_player, lift_chat_mute, get_active_chat_mutes,
    get_mod_actions, log_mod_action,
    get_all_players,
)

router = APIRouter()


# ==========================
# SHELL
# ==========================

def mod_shell(title: str, body: str, player_name: str = "", active_nav: str = "/mod") -> str:
    nav_items = [
        ("/mod", "Overview"),
        ("/mod/players", "Players"),
        ("/mod/mutes", "Mutes"),
        ("/mod/log", "Action Log"),
    ]
    nav_html = "".join(
        f'<a href="{url}" class="nav-item{"active" if url == active_nav else ""}">{label}</a>'
        for url, label in nav_items
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} – Mod Dashboard</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{background:#0f1117;color:#e2e8f0;font-family:'Inter',sans-serif;min-height:100vh}}
  .top-bar{{background:#1a1d2e;border-bottom:2px solid #7c3aed;padding:12px 20px;display:flex;align-items:center;gap:16px}}
  .top-bar h1{{font-size:1.1rem;font-weight:700;color:#a78bfa}}
  .top-bar .badge{{background:#7c3aed;color:#fff;font-size:0.65rem;padding:2px 8px;border-radius:99px;text-transform:uppercase;letter-spacing:.05em}}
  .top-bar .player-name{{margin-left:auto;font-size:0.85rem;color:#94a3b8}}
  nav{{background:#1e2130;border-bottom:1px solid #2d3147;display:flex;gap:4px;padding:6px 16px;overflow-x:auto}}
  nav a{{color:#94a3b8;text-decoration:none;padding:6px 14px;border-radius:6px;font-size:0.85rem;white-space:nowrap}}
  nav a:hover{{background:#2d3147;color:#e2e8f0}}
  nav a.active{{background:#7c3aed;color:#fff}}
  .container{{max-width:1100px;margin:0 auto;padding:24px 16px}}
  h2{{font-size:1.15rem;font-weight:600;color:#c4b5fd;margin-bottom:16px}}
  h3{{font-size:0.95rem;font-weight:600;color:#a78bfa;margin-bottom:10px}}
  .card{{background:#1a1d2e;border:1px solid #2d3147;border-radius:10px;padding:20px;margin-bottom:20px}}
  table{{width:100%;border-collapse:collapse;font-size:0.85rem}}
  th{{text-align:left;padding:8px 12px;color:#94a3b8;border-bottom:1px solid #2d3147;font-weight:500}}
  td{{padding:8px 12px;border-bottom:1px solid #1e2130;vertical-align:top}}
  tr:last-child td{{border-bottom:none}}
  .btn{{display:inline-block;padding:6px 14px;border-radius:6px;font-size:0.8rem;font-weight:600;cursor:pointer;border:none;text-decoration:none}}
  .btn-purple{{background:#7c3aed;color:#fff}}
  .btn-purple:hover{{background:#6d28d9}}
  .btn-red{{background:#dc2626;color:#fff}}
  .btn-red:hover{{background:#b91c1c}}
  .btn-green{{background:#16a34a;color:#fff}}
  .btn-green:hover{{background:#15803d}}
  .btn-gray{{background:#374151;color:#e2e8f0}}
  .btn-gray:hover{{background:#4b5563}}
  .form-row{{display:flex;flex-wrap:wrap;gap:10px;align-items:flex-end;margin-bottom:12px}}
  .form-group{{display:flex;flex-direction:column;gap:4px}}
  .form-group label{{font-size:0.75rem;color:#94a3b8}}
  input,select,textarea{{background:#0f1117;border:1px solid #374151;color:#e2e8f0;border-radius:6px;padding:7px 10px;font-size:0.85rem;outline:none}}
  input:focus,select:focus,textarea:focus{{border-color:#7c3aed}}
  .tag{{display:inline-block;padding:2px 8px;border-radius:99px;font-size:0.72rem;font-weight:600}}
  .tag-muted{{background:#7c3aed22;color:#a78bfa;border:1px solid #7c3aed44}}
  .tag-ok{{background:#16a34a22;color:#4ade80;border:1px solid #16a34a44}}
  .tag-warn{{background:#d9770622;color:#fb923c;border:1px solid #d9770644}}
  .empty{{color:#4b5563;font-style:italic;padding:12px 0}}
  .flash{{padding:10px 14px;border-radius:8px;margin-bottom:16px;font-size:0.85rem}}
  .flash-ok{{background:#16a34a22;border:1px solid #16a34a44;color:#4ade80}}
  .flash-err{{background:#dc262622;border:1px solid #dc262644;color:#f87171}}
  .msg-list{{display:flex;flex-direction:column;gap:6px;max-height:320px;overflow-y:auto}}
  .msg-item{{background:#0f1117;border:1px solid #2d3147;border-radius:6px;padding:8px 12px}}
  .msg-meta{{font-size:0.72rem;color:#64748b;margin-bottom:3px}}
  .msg-content{{font-size:0.85rem;word-break:break-word}}
  .del-btn{{float:right;background:#dc262633;border:1px solid #dc262666;color:#f87171;border-radius:4px;padding:2px 8px;font-size:0.72rem;cursor:pointer}}
  .del-btn:hover{{background:#dc2626;color:#fff}}
</style>
</head>
<body>
<div class="top-bar">
  <h1>Moderator Dashboard</h1>
  <span class="badge">MOD</span>
  <span class="player-name">{player_name}</span>
</div>
<nav>{nav_html}</nav>
<div class="container">
{body}
</div>
<script>
async function apiPost(url, data) {{
  const fd = new FormData();
  for (const [k, v] of Object.entries(data)) fd.append(k, v);
  const r = await fetch(url, {{method:'POST', body:fd}});
  return r.json();
}}
async function liftMute(playerId) {{
  if (!confirm('Lift mute for this player?')) return;
  const res = await apiPost('/api/mod/lift-mute', {{player_id: playerId}});
  if (res.ok) location.reload();
  else alert('Error: ' + (res.error || 'unknown'));
}}
async function deleteChatMsg(msgId, btn) {{
  if (!confirm('Delete this message?')) return;
  const res = await apiPost('/api/chat/mod/delete-message', {{message_id: msgId}});
  if (res.ok) btn.closest('.msg-item').remove();
  else alert('Error: ' + (res.error || 'unknown'));
}}
</script>
</body>
</html>"""


# ==========================
# OVERVIEW
# ==========================

@router.get("/mod", response_class=HTMLResponse)
async def mod_overview(session_token: str = Cookie(None)):
    mod, is_admin = require_moderator(session_token)
    if not mod:
        return RedirectResponse(url="/login", status_code=303)

    mutes = get_active_chat_mutes()
    recent_actions = get_mod_actions(limit=10)

    mute_rows = ""
    for m in mutes[:5]:
        exp = m["expires_at"] or "Permanent"
        mute_rows += f"""<tr>
          <td>{m['player_name']}</td>
          <td>{m['reason'] or '—'}</td>
          <td>{exp}</td>
          <td>{m['mod_name']}</td>
          <td><button class="btn btn-green" onclick="liftMute({m['player_id']})">Lift</button></td>
        </tr>"""
    if not mute_rows:
        mute_rows = '<tr><td colspan="5" class="empty">No active mutes.</td></tr>'

    action_rows = ""
    for a in recent_actions:
        target = a["target_name"] or "—"
        action_rows += f"""<tr>
          <td>{a['mod_name']}</td>
          <td><span class="tag tag-warn">{a['action']}</span></td>
          <td>{target}</td>
          <td>{a['details'] or '—'}</td>
          <td style="color:#64748b;font-size:0.75rem">{(a['created_at'] or '')[:16]}</td>
        </tr>"""
    if not action_rows:
        action_rows = '<tr><td colspan="5" class="empty">No actions yet.</td></tr>'

    body = f"""
<h2>Overview</h2>
<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px;margin-bottom:24px">
  <div class="card" style="text-align:center">
    <div style="font-size:2rem;font-weight:700;color:#a78bfa">{len(mutes)}</div>
    <div style="color:#94a3b8;font-size:0.85rem">Active Chat Mutes</div>
  </div>
</div>

<div class="card">
  <h3>Active Mutes <a href="/mod/mutes" style="font-size:0.75rem;color:#7c3aed;margin-left:8px">View all →</a></h3>
  <table>
    <thead><tr><th>Player</th><th>Reason</th><th>Expires</th><th>By</th><th></th></tr></thead>
    <tbody>{mute_rows}</tbody>
  </table>
</div>

<div class="card">
  <h3>Recent Actions <a href="/mod/log" style="font-size:0.75rem;color:#7c3aed;margin-left:8px">View all →</a></h3>
  <table>
    <thead><tr><th>Mod</th><th>Action</th><th>Target</th><th>Details</th><th>When</th></tr></thead>
    <tbody>{action_rows}</tbody>
  </table>
</div>
"""
    return HTMLResponse(mod_shell("Overview", body, mod.business_name, "/mod"))


# ==========================
# PLAYERS
# ==========================

@router.get("/mod/players", response_class=HTMLResponse)
async def mod_players(
    q: str = Query(""),
    player_id: int = Query(0),
    msg: str = Query(""),
    err: str = Query(""),
    session_token: str = Cookie(None),
):
    mod, is_admin_user = require_moderator(session_token)
    if not mod:
        return RedirectResponse(url="/login", status_code=303)

    flash = ""
    if msg:
        flash = f'<div class="flash flash-ok">{msg}</div>'
    if err:
        flash = f'<div class="flash flash-err">{err}</div>'

    # Search results
    search_rows = ""
    players = []
    if q:
        try:
            all_players = get_all_players()
            ql = q.lower()
            players = [p for p in all_players if ql in p["business_name"].lower() or str(p["id"]) == q][:20]
        except Exception:
            pass
    for p in players:
        mute = None
        try:
            from admins import get_active_chat_mute
            mute = get_active_chat_mute(p["id"])
        except Exception:
            pass
        status = '<span class="tag tag-muted">Muted</span>' if mute else '<span class="tag tag-ok">OK</span>'
        search_rows += f"""<tr>
          <td>{p['id']}</td>
          <td><a href="/mod/players?player_id={p['id']}" style="color:#a78bfa">{p['business_name']}</a></td>
          <td>{status}</td>
          <td><a href="/mod/players?player_id={p['id']}" class="btn btn-gray" style="font-size:0.75rem;padding:4px 10px">View</a></td>
        </tr>"""
    if q and not search_rows:
        search_rows = '<tr><td colspan="4" class="empty">No players found.</td></tr>'

    # Player detail pane
    detail_html = ""
    if player_id:
        detail_html = _build_player_detail(player_id, mod.id)

    body = f"""{flash}
<h2>Players</h2>
<div class="card">
  <form method="get" action="/mod/players" class="form-row">
    <div class="form-group">
      <label>Search by name or ID</label>
      <input name="q" value="{q}" placeholder="Business name or player ID" style="width:280px">
    </div>
    <button type="submit" class="btn btn-purple">Search</button>
  </form>
  {"<table><thead><tr><th>ID</th><th>Name</th><th>Status</th><th></th></tr></thead><tbody>" + search_rows + "</tbody></table>" if q else ""}
</div>
{detail_html}
"""
    return HTMLResponse(mod_shell("Players", body, mod.business_name, "/mod/players"))


def _build_player_detail(player_id: int, mod_id: int) -> str:
    """Build the player detail card including recent messages and action forms."""
    try:
        from admins import get_player_detail, get_active_chat_mute, get_active_ban
        from chat import get_db as chat_db_fn, ChatMessage

        detail = get_player_detail(player_id)
        if not detail:
            return '<div class="card"><p class="empty">Player not found.</p></div>'

        mute = get_active_chat_mute(player_id)
        ban = get_active_ban(player_id)

        mute_status = ""
        mute_action = ""
        if mute:
            exp = mute["expires_at"] or "Permanent"
            mute_status = f'<span class="tag tag-muted">Chat Muted</span> <span style="color:#94a3b8;font-size:0.75rem">{exp}</span>'
            mute_action = f'<button class="btn btn-green" onclick="liftMute({player_id})">Lift Mute</button>'
        else:
            mute_status = '<span class="tag tag-ok">Not Muted</span>'
            mute_action = f"""
<form method="post" action="/api/mod/mute" style="display:inline-flex;gap:6px;flex-wrap:wrap;align-items:flex-end">
  <input type="hidden" name="player_id" value="{player_id}">
  <div class="form-group">
    <label>Minutes (0=perm)</label>
    <input type="number" name="minutes" value="30" min="0" style="width:90px">
  </div>
  <div class="form-group">
    <label>Reason</label>
    <input name="reason" placeholder="Reason" style="width:180px">
  </div>
  <button type="submit" class="btn btn-red">Mute</button>
</form>"""

        ban_status = ""
        if ban:
            ban_status = f'<span class="tag tag-warn">{ban["type"].upper()}</span> <span style="color:#94a3b8;font-size:0.75rem">{ban.get("reason","")}</span>'
        else:
            ban_status = '<span class="tag tag-ok">No account ban</span>'

        # Recent chat messages
        msg_items = ""
        try:
            db = chat_db_fn()
            msgs = db.query(ChatMessage).filter(
                ChatMessage.sender_id == player_id
            ).order_by(ChatMessage.created_at.desc()).limit(20).all()
            db.close()
            for m in msgs:
                ts = m.created_at.strftime("%m/%d %H:%M") if m.created_at else ""
                content_esc = m.content.replace("<", "&lt;").replace(">", "&gt;")
                msg_items += f"""<div class="msg-item">
  <div class="msg-meta">{ts} · #{m.room_id}
    <button class="del-btn" onclick="deleteChatMsg({m.id}, this)">Delete</button>
  </div>
  <div class="msg-content">{content_esc}</div>
</div>"""
        except Exception:
            pass

        if not msg_items:
            msg_items = '<p class="empty">No recent messages.</p>'

        warn_form = f"""
<form method="post" action="/api/mod/warn" style="display:inline-flex;gap:6px;flex-wrap:wrap;align-items:flex-end">
  <input type="hidden" name="player_id" value="{player_id}">
  <div class="form-group">
    <label>Warning note</label>
    <input name="note" placeholder="Reason for warning" style="width:240px">
  </div>
  <button type="submit" class="btn btn-purple">Log Warning</button>
</form>"""

        return f"""
<div class="card">
  <h3>{detail['business_name']} <span style="color:#64748b;font-size:0.8rem">(#{detail['id']})</span></h3>
  <div style="display:flex;flex-wrap:wrap;gap:12px;margin-bottom:16px">
    <div><span style="color:#94a3b8;font-size:0.75rem">City:</span> {detail.get('city_name') or '—'}</div>
    <div><span style="color:#94a3b8;font-size:0.75rem">Chat:</span> {mute_status}</div>
    <div><span style="color:#94a3b8;font-size:0.75rem">Account:</span> {ban_status}</div>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">
    {mute_action}
    {warn_form}
  </div>
  <h3>Recent Messages</h3>
  <div class="msg-list">{msg_items}</div>
</div>"""
    except Exception as e:
        return f'<div class="card"><p class="empty">Error loading player: {e}</p></div>'


# ==========================
# MUTES
# ==========================

@router.get("/mod/mutes", response_class=HTMLResponse)
async def mod_mutes(
    msg: str = Query(""),
    err: str = Query(""),
    session_token: str = Cookie(None),
):
    mod, _ = require_moderator(session_token)
    if not mod:
        return RedirectResponse(url="/login", status_code=303)

    flash = ""
    if msg:
        flash = f'<div class="flash flash-ok">{msg}</div>'
    if err:
        flash = f'<div class="flash flash-err">{err}</div>'

    mutes = get_active_chat_mutes()
    rows = ""
    for m in mutes:
        exp = m["expires_at"] or "Permanent"
        rows += f"""<tr>
          <td>{m['player_id']}</td>
          <td>{m['player_name']}</td>
          <td>{m['reason'] or '—'}</td>
          <td>{exp}</td>
          <td>{m['created_at'][:16] if m['created_at'] else '—'}</td>
          <td>{m['mod_name']}</td>
          <td><button class="btn btn-green" onclick="liftMute({m['player_id']})">Lift</button></td>
        </tr>"""
    if not rows:
        rows = '<tr><td colspan="7" class="empty">No active chat mutes.</td></tr>'

    body = f"""{flash}
<h2>Active Chat Mutes</h2>
<div class="card">
  <table>
    <thead><tr><th>ID</th><th>Player</th><th>Reason</th><th>Expires</th><th>Issued</th><th>By</th><th></th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
</div>

<div class="card">
  <h3>Issue New Mute</h3>
  <form method="post" action="/api/mod/mute" class="form-row">
    <div class="form-group">
      <label>Player ID</label>
      <input type="number" name="player_id" placeholder="Player ID" required style="width:110px">
    </div>
    <div class="form-group">
      <label>Minutes (0 = permanent)</label>
      <input type="number" name="minutes" value="60" min="0" style="width:100px">
    </div>
    <div class="form-group">
      <label>Reason</label>
      <input name="reason" placeholder="Reason" style="width:220px">
    </div>
    <button type="submit" class="btn btn-red">Mute Player</button>
  </form>
</div>
"""
    return HTMLResponse(mod_shell("Mutes", body, mod.business_name, "/mod/mutes"))


# ==========================
# ACTION LOG
# ==========================

@router.get("/mod/log", response_class=HTMLResponse)
async def mod_log(session_token: str = Cookie(None)):
    mod, _ = require_moderator(session_token)
    if not mod:
        return RedirectResponse(url="/login", status_code=303)

    actions = get_mod_actions(limit=100)
    rows = ""
    for a in actions:
        target = a["target_name"] or (f"#{a['target_player_id']}" if a["target_player_id"] else "—")
        rows += f"""<tr>
          <td>{a['mod_name']}</td>
          <td><span class="tag tag-warn">{a['action']}</span></td>
          <td>{target}</td>
          <td>{a['room_id'] or '—'}</td>
          <td>{a['details'] or '—'}</td>
          <td style="color:#64748b;font-size:0.75rem">{(a['created_at'] or '')[:16]}</td>
        </tr>"""
    if not rows:
        rows = '<tr><td colspan="6" class="empty">No mod actions recorded yet.</td></tr>'

    body = f"""
<h2>Mod Action Log <span style="color:#64748b;font-size:0.85rem">(last 100)</span></h2>
<div class="card">
  <table>
    <thead><tr><th>Mod</th><th>Action</th><th>Target</th><th>Room</th><th>Details</th><th>When</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
</div>
"""
    return HTMLResponse(mod_shell("Action Log", body, mod.business_name, "/mod/log"))


# ==========================
# API ENDPOINTS
# ==========================

@router.post("/api/mod/mute")
async def api_mod_mute(
    player_id: int = Form(...),
    minutes: int = Form(0),
    reason: str = Form(""),
    session_token: str = Cookie(None),
):
    mod, _ = require_moderator(session_token)
    if not mod:
        return JSONResponse({"ok": False, "error": "Not authorized"}, status_code=403)
    result = chat_mute_player(mod.id, player_id, minutes, reason)
    # If request came from a browser form, redirect back
    return JSONResponse(result)


@router.post("/api/mod/lift-mute")
async def api_mod_lift_mute(
    player_id: int = Form(...),
    session_token: str = Cookie(None),
):
    mod, _ = require_moderator(session_token)
    if not mod:
        return JSONResponse({"ok": False, "error": "Not authorized"}, status_code=403)
    result = lift_chat_mute(mod.id, player_id)
    return JSONResponse(result)


@router.post("/api/mod/warn")
async def api_mod_warn(
    player_id: int = Form(...),
    note: str = Form(""),
    session_token: str = Cookie(None),
):
    mod, _ = require_moderator(session_token)
    if not mod:
        return JSONResponse({"ok": False, "error": "Not authorized"}, status_code=403)
    log_mod_action(mod.id, "warn", player_id, None, note)
    return JSONResponse({"ok": True})
