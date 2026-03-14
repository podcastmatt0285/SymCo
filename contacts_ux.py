"""
contacts_ux.py — Contact system routes.

Pages:
  GET  /contacts              — main contacts hub
  GET  /contacts/card/{id}   — AJAX: returns contact card HTML fragment

API endpoints:
  POST /api/contacts/request
  POST /api/contacts/accept
  POST /api/contacts/decline
  POST /api/contacts/remove
  POST /api/contacts/notes
  GET  /api/contacts/search?q=
"""

from typing import Optional
from fastapi import APIRouter, Cookie, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from datetime import datetime

router = APIRouter()


# ──────────────────────────────────────────────────────────────────────────────
# AUTH HELPER (mirrors p2p_ux pattern)
# ──────────────────────────────────────────────────────────────────────────────

def _require_auth(session_token):
    from auth import get_player_from_session, get_db
    db = get_db()
    player = get_player_from_session(db, session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)
    return player


def _shell(title, body, cash, pid):
    from ux import shell as main_shell
    return main_shell(title, body, cash, pid)


# ──────────────────────────────────────────────────────────────────────────────
# CONTACTS PAGE
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/contacts", response_class=HTMLResponse)
def contacts_page(
    session_token: Optional[str] = Cookie(None),
    view: int = 0,          # player_id whose card to display
    msg: str = "",
    err: str = "",
    q: str = "",            # search query pre-fill
):
    player = _require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player

    from reserve_banks import get_player_display_currency, fmt_usd
    disp    = get_player_display_currency(player.id)
    fmt_fn  = lambda amount, d=disp: fmt_usd(amount, d)

    from contacts import (
        get_contacts, get_incoming_requests, get_outgoing_requests,
        build_contact_card_html, get_contact_row, search_players,
    )
    from auth import Player, get_db as get_auth_db

    contacts      = get_contacts(player.id)
    incoming      = get_incoming_requests(player.id)
    outgoing      = get_outgoing_requests(player.id)
    search_res    = search_players(q, player.id) if q else []

    # Resolve display names for incoming/outgoing requests
    def _name(pid):
        db = get_auth_db()
        try:
            p = db.query(Player).filter(Player.id == pid).first()
            return p.business_name if p else f"Player #{pid}"
        finally:
            db.close()

    # ── feedback banners ──
    banner = ""
    if msg:
        banner = f'<div style="padding:10px 16px;background:#052e16;border:1px solid #16a34a;color:#4ade80;margin-bottom:12px;">{msg}</div>'
    elif err:
        banner = f'<div style="padding:10px 16px;background:#1a0505;border:1px solid #dc2626;color:#f87171;margin-bottom:12px;">{err}</div>'

    # ── header ──
    html = f'''
    <a href="/p2p/dashboard" style="color:#38bdf8;">&larr; P2P Dashboard</a>
    <h1 style="margin:8px 0 4px 0;">Contacts</h1>
    <p style="color:#64748b;margin-bottom:20px;">
        Your private contact list. Contact cards reveal detailed player information visible only to mutual contacts.
    </p>
    {banner}
    <div style="display:grid;grid-template-columns:320px 1fr;gap:20px;align-items:start;">
    '''

    # ═══════════════════════ LEFT COLUMN ═══════════════════════
    left = ""

    # ── Incoming requests ──
    if incoming:
        left += f'<div class="card" style="margin-bottom:16px;border-color:#22c55e;">'
        left += f'<h3 style="color:#22c55e;margin:0 0 12px 0;">Incoming Requests ({len(incoming)})</h3>'
        for req in incoming:
            rname = _name(req.requester_id)
            since = req.created_at.strftime("%b %d") if req.created_at else ""
            left += f'''
            <div style="padding:8px 0;border-bottom:1px solid #0f172a;display:flex;justify-content:space-between;align-items:center;gap:8px;">
                <div>
                    <div style="color:#e5e7eb;font-weight:500;">{rname}</div>
                    <div style="font-size:0.75rem;color:#64748b;">{since}</div>
                </div>
                <div style="display:flex;gap:6px;flex-shrink:0;">
                    <form action="/api/contacts/accept" method="post">
                        <input type="hidden" name="contact_id" value="{req.id}">
                        <button class="btn-blue" style="padding:4px 10px;font-size:0.8rem;">Accept</button>
                    </form>
                    <form action="/api/contacts/decline" method="post">
                        <input type="hidden" name="contact_id" value="{req.id}">
                        <button class="btn-red" style="padding:4px 10px;font-size:0.8rem;">Decline</button>
                    </form>
                </div>
            </div>'''
        left += "</div>"

    # ── Search players ──
    left += f'''
    <div class="card" style="margin-bottom:16px;">
        <h3 style="margin:0 0 10px 0;">Find Players</h3>
        <form method="get" action="/contacts" style="display:flex;gap:8px;">
            <input type="text" name="q" value="{q}" placeholder="Search by name…"
                   style="flex:1;background:#020617;border:1px solid #334155;color:#e5e7eb;padding:8px;">
            <button type="submit" class="btn-blue" style="padding:8px 14px;">Search</button>
        </form>'''
    if q and search_res:
        for r in search_res:
            rel = get_contact_row(player.id, r["id"])
            if rel and rel.status == "accepted":
                action_html = f'<a href="/contacts?view={r["id"]}" class="btn-blue" style="padding:3px 10px;font-size:0.8rem;">View Card</a>'
            elif rel and rel.status == "pending":
                action_html = '<span style="color:#64748b;font-size:0.8rem;">Pending…</span>'
            else:
                action_html = f'''<form action="/api/contacts/request" method="post" style="display:inline;">
                    <input type="hidden" name="recipient_id" value="{r["id"]}">
                    <button class="btn-blue" style="padding:3px 10px;font-size:0.8rem;">Add</button>
                </form>'''
            left += f'''
            <div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid #0f172a;">
                <span style="color:#e5e7eb;">{r["name"]}</span>
                {action_html}
            </div>'''
    elif q and not search_res:
        left += '<p style="color:#64748b;font-size:0.85rem;margin-top:8px;">No players found.</p>'
    left += "</div>"

    # ── Outgoing pending ──
    if outgoing:
        left += f'<div class="card" style="margin-bottom:16px;border-color:#f59e0b;">'
        left += f'<h3 style="color:#f59e0b;margin:0 0 10px 0;">Sent Requests ({len(outgoing)})</h3>'
        for req in outgoing:
            rname = _name(req.recipient_id)
            left += f'''
            <div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid #0f172a;">
                <span style="color:#e5e7eb;">{rname}</span>
                <span style="color:#64748b;font-size:0.8rem;">Pending</span>
            </div>'''
        left += "</div>"

    # ── Contact list ──
    if contacts:
        left += f'<div class="card">'
        left += f'<h3 style="margin:0 0 12px 0;">My Contacts ({len(contacts)})</h3>'
        for row, other_id, my_notes in contacts:
            oname    = _name(other_id)
            is_view  = (view == other_id)
            left += f'''
            <div style="padding:8px 0;border-bottom:1px solid #0f172a;">
                <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;">
                    <a href="/contacts?view={other_id}" style="color:{"#38bdf8" if is_view else "#e5e7eb"};font-weight:{"bold" if is_view else "normal"};">
                        {oname}
                    </a>
                    <form action="/api/contacts/remove" method="post">
                        <input type="hidden" name="contact_id" value="{row.id}">
                        <button class="btn-red" style="padding:2px 8px;font-size:0.75rem;"
                                onclick="return confirm('Remove {oname} from contacts?')">Remove</button>
                    </form>
                </div>
                <!-- Private notes inline editor -->
                <form action="/api/contacts/notes" method="post" style="margin-top:6px;">
                    <input type="hidden" name="contact_id" value="{row.id}">
                    <textarea name="notes" rows="2" placeholder="Private notes about this contact…"
                              style="width:100%;background:#020617;border:1px solid #1e293b;color:#94a3b8;
                                     font-size:0.75rem;padding:4px;resize:vertical;box-sizing:border-box;"
                    >{my_notes}</textarea>
                    <button type="submit" class="btn-blue"
                            style="margin-top:4px;padding:2px 10px;font-size:0.75rem;">Save Notes</button>
                </form>
            </div>'''
        left += "</div>"
    else:
        left += '''
        <div class="card" style="text-align:center;padding:30px;">
            <p style="color:#94a3b8;">No contacts yet.</p>
            <p style="font-size:0.8rem;color:#64748b;">Search for players above to send contact requests.</p>
        </div>'''

    html += f'<div>{left}</div>'

    # ═══════════════════════ RIGHT COLUMN — Contact Card ═══════════════════════
    if view and view != player.id:
        # Verify the viewer actually has this contact accepted (or is viewing their own)
        rel = get_contact_row(player.id, view)
        if rel and rel.status == "accepted":
            card_html = build_contact_card_html(view, disp, fmt_usd)
            view_name = _name(view)
            html += f'''
            <div>
                <div class="card" style="border-color:#38bdf8;">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
                        <h3 style="margin:0;color:#38bdf8;">Contact Card — {view_name}</h3>
                        <a href="/contacts" style="color:#64748b;font-size:0.85rem;">✕ Close</a>
                    </div>
                    {card_html}
                </div>
            </div>'''
        else:
            html += '<div><div class="card"><p style="color:#64748b;">You must be mutual contacts to view this card.</p></div></div>'
    else:
        html += '''
        <div>
            <div class="card" style="text-align:center;padding:40px;color:#64748b;">
                <div style="font-size:2rem;margin-bottom:12px;">🤝</div>
                <p>Select a contact from the list to view their detailed profile card.</p>
                <p style="font-size:0.8rem;margin-top:8px;">Contact cards are private — only you can see this information.</p>
            </div>
        </div>'''

    html += "</div>"  # close grid

    return _shell("Contacts", html, player.cash_balance, player.id)


# ──────────────────────────────────────────────────────────────────────────────
# API ENDPOINTS
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/api/contacts/request")
async def api_contact_request(
    recipient_id: int = Form(...),
    session_token: Optional[str] = Cookie(None),
):
    player = _require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    from contacts import send_contact_request
    ok, message = send_contact_request(player.id, recipient_id)
    param = "msg" if ok else "err"
    from urllib.parse import quote
    return RedirectResponse(f"/contacts?{param}={quote(message)}", status_code=303)


@router.post("/api/contacts/accept")
async def api_contact_accept(
    contact_id: int = Form(...),
    session_token: Optional[str] = Cookie(None),
):
    player = _require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    from contacts import accept_contact_request
    ok, message = accept_contact_request(player.id, contact_id)
    param = "msg" if ok else "err"
    from urllib.parse import quote
    return RedirectResponse(f"/contacts?{param}={quote(message)}", status_code=303)


@router.post("/api/contacts/decline")
async def api_contact_decline(
    contact_id: int = Form(...),
    session_token: Optional[str] = Cookie(None),
):
    player = _require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    from contacts import decline_contact_request
    ok, message = decline_contact_request(player.id, contact_id)
    param = "msg" if ok else "err"
    from urllib.parse import quote
    return RedirectResponse(f"/contacts?{param}={quote(message)}", status_code=303)


@router.post("/api/contacts/remove")
async def api_contact_remove(
    contact_id: int = Form(...),
    session_token: Optional[str] = Cookie(None),
):
    player = _require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    from contacts import remove_contact
    ok, message = remove_contact(player.id, contact_id)
    param = "msg" if ok else "err"
    from urllib.parse import quote
    return RedirectResponse(f"/contacts?{param}={quote(message)}", status_code=303)


@router.post("/api/contacts/notes")
async def api_contact_notes(
    contact_id: int = Form(...),
    notes: str = Form(""),
    session_token: Optional[str] = Cookie(None),
):
    player = _require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    from contacts import update_notes
    ok, message = update_notes(player.id, contact_id, notes)
    param = "msg" if ok else "err"
    from urllib.parse import quote
    return RedirectResponse(f"/contacts?{param}={quote(message)}", status_code=303)


@router.get("/api/contacts/search")
async def api_contact_search(
    q: str = Query(""),
    session_token: Optional[str] = Cookie(None),
):
    player = _require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return JSONResponse({"results": []})
    from contacts import search_players
    return JSONResponse({"results": search_players(q, player.id)})
