"""
trusted_trade_ux.py

All HTML routes for the Trusted-Trader / Item-Swap system.

Pages
─────
  GET  /inventory/trusted-list          manage your trusted list
  GET  /inventory/swaps                 view + create swaps
  GET  /inventory/swaps/{swap_id}       detail view for one swap

API endpoints
─────────────
  POST /api/trusted-trade/add           add player to trusted list
  POST /api/trusted-trade/remove        remove player from trusted list
  POST /api/trusted-trade/swap/create   create a new swap offer
  POST /api/trusted-trade/swap/accept   accept a pending swap
  POST /api/trusted-trade/swap/reject   reject a pending swap
  POST /api/trusted-trade/swap/cancel   cancel your own pending swap
"""

from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Cookie, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse

router = APIRouter()


# ─── Shared helpers ───────────────────────────────────────────────────────────

def require_auth(session_token):
    try:
        import auth
        db = auth.get_db()
        try:
            player = auth.get_player_from_session(db, session_token)
        finally:
            db.close()
        if not player:
            return RedirectResponse(url="/login", status_code=303)
        return player
    except Exception:
        return RedirectResponse(url="/login", status_code=303)


def shell(title: str, body: str, balance: float = 0.0, player_id=None) -> str:
    from ux import shell as main_shell
    return main_shell(title, body, balance, player_id)


def _player_name(player_id: int) -> str:
    try:
        from auth import get_db, Player
        db = get_db()
        try:
            p = db.query(Player).filter(Player.id == player_id).first()
            return p.business_name if p else f"Player {player_id}"
        finally:
            db.close()
    except Exception:
        return f"Player {player_id}"


# ─── Trusted-List Page ────────────────────────────────────────────────────────

@router.get("/inventory/trusted-list", response_class=HTMLResponse)
def trusted_list_page(
    session_token: Optional[str] = Cookie(None),
    msg: Optional[str]   = Query(None),
    error: Optional[str] = Query(None),
    search: str          = Query(""),
):
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player

    from trusted_trade import (
        get_trusted_list, MAX_TRUSTED_SLOTS, SLOT_ADD_PRICES,
        MIN_DAYS_BEFORE_REMOVAL
    )

    entries = get_trusted_list(player.id)

    # Build current-list rows
    list_rows = ""
    for e in entries:
        tname = _player_name(e.trusted_player_id)
        days_on  = (datetime.utcnow() - e.added_at).days
        removal_fee = e.cost_paid * 2
        days_left = max(0, MIN_DAYS_BEFORE_REMOVAL - days_on)
        if days_left == 0:
            remove_btn = f'''
            <form action="/api/trusted-trade/remove" method="post" style="display:inline;"
                  onsubmit="return confirm('Remove {tname} from your trusted list? This costs ${removal_fee:,.0f}.');">
                <input type="hidden" name="entry_id" value="{e.id}">
                <button type="submit"
                        style="background:#7f1d1d;color:#fca5a5;border:none;padding:3px 10px;border-radius:3px;cursor:pointer;font-size:0.8rem;">
                    Remove (${removal_fee:,.0f})
                </button>
            </form>'''
        else:
            remove_btn = (
                f'<span style="color:#64748b;font-size:0.8rem;">'
                f'Locked {days_left}d</span>'
            )

        list_rows += f'''
        <tr style="border-bottom:1px solid #1e293b;">
            <td style="padding:10px 8px;">{e.slot_number}</td>
            <td style="padding:10px 8px;font-weight:bold;">{tname}</td>
            <td style="padding:10px 8px;color:#94a3b8;">{e.added_at.strftime("%Y-%m-%d")}</td>
            <td style="padding:10px 8px;color:#94a3b8;">{days_on}d</td>
            <td style="padding:10px 8px;color:#f59e0b;">${e.cost_paid:,.0f}</td>
            <td style="padding:10px 8px;color:#ef4444;">${removal_fee:,.0f}</td>
            <td style="padding:10px 8px;">{remove_btn}</td>
        </tr>'''

    if not list_rows:
        list_rows = (
            '<tr><td colspan="7" style="padding:16px;text-align:center;color:#64748b;">'
            'Your trusted list is empty.</td></tr>'
        )

    used_slots = len(entries)
    free_slots = MAX_TRUSTED_SLOTS - used_slots
    next_slot  = used_slots + 1 if free_slots > 0 else None
    next_fee   = SLOT_ADD_PRICES[next_slot - 1] if next_slot else None

    # Slot pricing table
    pricing_rows = ""
    for i, price in enumerate(SLOT_ADD_PRICES, start=1):
        taken = any(e.slot_number == i for e in entries)
        status_cell = (
            f'<span style="color:#22c55e;">Occupied</span>'
            if taken else
            f'<span style="color:#64748b;">Empty</span>'
        )
        pricing_rows += f'''
        <tr style="border-bottom:1px solid #1e293b;">
            <td style="padding:8px;">Slot {i}</td>
            <td style="padding:8px;color:#38bdf8;">${price:,.0f}</td>
            <td style="padding:8px;color:#ef4444;">${price*2:,.0f}</td>
            <td style="padding:8px;">{status_cell}</td>
        </tr>'''

    # Player search for adding
    search_results = ""
    if search:
        from auth import get_db as get_auth_db, Player
        adb = get_auth_db()
        try:
            already = {e.trusted_player_id for e in entries}
            players = (
                adb.query(Player)
                .filter(
                    Player.id != player.id,
                    Player.id > 0,
                    Player.business_name.ilike(f"%{search}%"),
                )
                .limit(20)
                .all()
            )
            for p in players:
                if p.id in already:
                    status = '<span style="color:#f59e0b;font-size:0.8rem;">Already on list</span>'
                    btn    = ""
                elif free_slots == 0:
                    status = '<span style="color:#64748b;font-size:0.8rem;">List full</span>'
                    btn    = ""
                else:
                    status = f'<span style="color:#22c55e;font-size:0.8rem;">Slot {next_slot} — ${next_fee:,.0f}</span>'
                    btn    = f'''
                    <form action="/api/trusted-trade/add" method="post" style="display:inline;">
                        <input type="hidden" name="target_id" value="{p.id}">
                        <button type="submit"
                                style="background:#15803d;color:#fff;border:none;padding:3px 10px;border-radius:3px;cursor:pointer;font-size:0.8rem;">
                            Add
                        </button>
                    </form>'''
                search_results += f'''
                <div style="display:flex;justify-content:space-between;align-items:center;
                            padding:8px 12px;border-bottom:1px solid #1e293b;">
                    <span style="font-weight:bold;">{p.business_name}</span>
                    <div style="display:flex;align-items:center;gap:10px;">
                        {status}
                        {btn}
                    </div>
                </div>'''
        finally:
            adb.close()

    alert_html = ""
    if msg:
        alert_html = f'<div style="background:#14532d;border:1px solid #16a34a;border-radius:6px;padding:10px 14px;margin-bottom:16px;color:#86efac;">{msg}</div>'
    if error:
        alert_html += f'<div style="background:#450a0a;border:1px solid #dc2626;border-radius:6px;padding:10px 14px;margin-bottom:16px;color:#fca5a5;">{error}</div>'

    body = f'''
    <a href="/inventory" style="color:#38bdf8;">&#8592; Inventory</a>
    <h1>Trusted Trader List</h1>
    {alert_html}

    <p style="color:#64748b;margin-bottom:18px;">
        Build a private list of up to {MAX_TRUSTED_SLOTS} trusted partners.
        You and a partner <strong>must each add the other</strong> before you can swap.
        Slots use <strong>Fibonacci pricing</strong> and carry a
        <strong>{MIN_DAYS_BEFORE_REMOVAL}-day minimum lock-in</strong>.
        Removing a player costs <strong>double</strong> what it cost to add them.
    </p>

    <!-- Current list -->
    <div class="card">
        <h3>Your Trusted List ({used_slots}/{MAX_TRUSTED_SLOTS} slots used)</h3>
        <table style="width:100%;border-collapse:collapse;">
            <thead>
                <tr style="border-bottom:1px solid #1e293b;font-size:0.85rem;color:#64748b;text-align:left;">
                    <th style="padding:8px;">Slot</th>
                    <th style="padding:8px;">Player</th>
                    <th style="padding:8px;">Added</th>
                    <th style="padding:8px;">Days</th>
                    <th style="padding:8px;">Add Cost</th>
                    <th style="padding:8px;">Remove Cost</th>
                    <th style="padding:8px;">Action</th>
                </tr>
            </thead>
            <tbody>{list_rows}</tbody>
        </table>
    </div>

    <!-- Slot pricing reference -->
    <div class="card" style="margin-top:18px;">
        <h3>Slot Pricing</h3>
        <table style="width:100%;border-collapse:collapse;">
            <thead>
                <tr style="border-bottom:1px solid #1e293b;font-size:0.85rem;color:#64748b;text-align:left;">
                    <th style="padding:8px;">Slot</th>
                    <th style="padding:8px;color:#38bdf8;">Add Cost</th>
                    <th style="padding:8px;color:#ef4444;">Remove Cost</th>
                    <th style="padding:8px;">Status</th>
                </tr>
            </thead>
            <tbody>{pricing_rows}</tbody>
        </table>
    </div>

    <!-- Add a player -->
    <div class="card" style="margin-top:18px;">
        <h3>Add a Player</h3>
        {'<p style="color:#ef4444;">Your list is full. Remove someone to add a new player.</p>' if free_slots == 0 else f'<p style="color:#64748b;font-size:0.85rem;margin-bottom:12px;">Next slot (slot {next_slot}) costs <strong style="color:#38bdf8;">${next_fee:,.0f}</strong>.</p>'}
        <form action="/inventory/trusted-list" method="get" style="display:flex;gap:8px;margin-bottom:12px;">
            <input type="text" name="search" value="{search}"
                   placeholder="Search player name..."
                   style="flex:1;background:#0f172a;border:1px solid #334155;color:#e2e8f0;padding:8px 12px;border-radius:4px;">
            <button type="submit"
                    style="background:#1d4ed8;color:#fff;border:none;padding:8px 16px;border-radius:4px;cursor:pointer;">
                Search
            </button>
        </form>
        {f'<div style="border:1px solid #1e293b;border-radius:6px;">{search_results}</div>' if search_results else ('<p style="color:#64748b;font-size:0.85rem;">No results.</p>' if search else '')}
    </div>

    <div style="margin-top:18px;">
        <a href="/inventory/swaps" style="color:#a78bfa;">&#8594; Go to Item Swaps</a>
    </div>
    '''

    return shell("Trusted List", body, player.cash_balance, player.id)


# ─── Swaps Page ───────────────────────────────────────────────────────────────

@router.get("/inventory/swaps", response_class=HTMLResponse)
def swaps_page(
    session_token: Optional[str] = Cookie(None),
    msg: Optional[str]   = Query(None),
    error: Optional[str] = Query(None),
):
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player

    from trusted_trade import (
        get_trusted_list, get_swaps_for_player, get_swap_detail,
        MAX_SWAP_PARTIES, MAX_SWAP_LEGS
    )
    from inventory import get_player_inventory

    # Fetch trusted list for participant selection
    my_entries = get_trusted_list(player.id)

    # Find partners who mutually trust back
    from trusted_trade import get_db as get_tt_db, TrustedTraderEntry
    tt_db = get_tt_db()
    try:
        mutual_partners = []
        for e in my_entries:
            reverse = (
                tt_db.query(TrustedTraderEntry)
                .filter(
                    TrustedTraderEntry.owner_player_id   == e.trusted_player_id,
                    TrustedTraderEntry.trusted_player_id == player.id,
                )
                .first()
            )
            if reverse:
                mutual_partners.append({
                    "id":   e.trusted_player_id,
                    "name": _player_name(e.trusted_player_id),
                })
    finally:
        tt_db.close()

    # Fetch existing swaps
    swaps = get_swaps_for_player(player.id)

    # ── Build existing-swaps table ──
    swap_rows = ""
    for sw in swaps:
        _, legs, acceptances = get_swap_detail(sw.id)
        participants = list({a.player_id for a in acceptances})
        pnames = ", ".join(_player_name(pid) for pid in participants if pid != player.id)
        my_acc = next((a for a in acceptances if a.player_id == player.id), None)
        all_accepted = all(a.accepted for a in acceptances)
        status_color = {
            "pending":   "#f59e0b",
            "executed":  "#22c55e",
            "rejected":  "#ef4444",
            "cancelled": "#64748b",
            "failed":    "#ef4444",
        }.get(sw.status, "#64748b")

        actions = ""
        if sw.status == "pending":
            if my_acc and not my_acc.accepted:
                actions += f'''
                <form action="/api/trusted-trade/swap/accept" method="post" style="display:inline;">
                    <input type="hidden" name="swap_id" value="{sw.id}">
                    <button type="submit"
                            style="background:#15803d;color:#fff;border:none;padding:3px 8px;border-radius:3px;cursor:pointer;font-size:0.8rem;margin-right:4px;">
                        &#10003; Accept
                    </button>
                </form>
                <form action="/api/trusted-trade/swap/reject" method="post" style="display:inline;">
                    <input type="hidden" name="swap_id" value="{sw.id}">
                    <button type="submit"
                            style="background:#7f1d1d;color:#fca5a5;border:none;padding:3px 8px;border-radius:3px;cursor:pointer;font-size:0.8rem;">
                        &#10007; Reject
                    </button>
                </form>'''
            elif sw.initiator_id == player.id:
                actions += f'''
                <form action="/api/trusted-trade/swap/cancel" method="post" style="display:inline;">
                    <input type="hidden" name="swap_id" value="{sw.id}">
                    <button type="submit"
                            style="background:#374151;color:#9ca3af;border:none;padding:3px 8px;border-radius:3px;cursor:pointer;font-size:0.8rem;">
                        Cancel
                    </button>
                </form>'''
            else:
                actions = '<span style="color:#64748b;font-size:0.8rem;">Waiting for others</span>'

        swap_rows += f'''
        <tr style="border-bottom:1px solid #1e293b;">
            <td style="padding:10px 8px;">
                <a href="/inventory/swaps/{sw.id}" style="color:#38bdf8;">#{sw.id}</a>
            </td>
            <td style="padding:10px 8px;color:#94a3b8;">{pnames or "—"}</td>
            <td style="padding:10px 8px;">{len(legs)} leg(s)</td>
            <td style="padding:10px 8px;font-weight:bold;color:{status_color};">
                {sw.status.upper()}
            </td>
            <td style="padding:10px 8px;color:#94a3b8;">{sw.created_at.strftime("%m/%d %H:%M")}</td>
            <td style="padding:10px 8px;">{actions}</td>
        </tr>'''

    if not swap_rows:
        swap_rows = (
            '<tr><td colspan="6" style="padding:16px;text-align:center;color:#64748b;">'
            'No swaps yet.</td></tr>'
        )

    # ── Build create-swap form ──
    all_participants = [{"id": player.id, "name": "You"}] + mutual_partners
    participant_opts = "".join(
        f'<option value="{p["id"]}">{p["name"]}</option>'
        for p in all_participants
    )

    if not mutual_partners:
        create_form_html = '''
        <div style="background:#1e1b4b;border:1px solid #4f46e5;border-radius:6px;padding:14px;color:#c4b5fd;">
            You have no mutual trusted partners yet. Both you and a partner must add each
            other to your trusted lists before you can propose a swap.
            <br><a href="/inventory/trusted-list" style="color:#a78bfa;">Manage trusted list &#8594;</a>
        </div>'''
    else:
        # Leg rows (8 rows max in the static form)
        leg_rows = ""
        for i in range(8):
            leg_rows += f'''
            <tr>
                <td style="padding:6px 4px;">
                    <select name="from_player_ids" style="width:100%;font-size:0.8rem;background:#0f172a;border:1px solid #334155;color:#e2e8f0;padding:4px;">
                        <option value="">—</option>
                        {participant_opts}
                    </select>
                </td>
                <td style="padding:6px 4px;">
                    <select name="to_player_ids" style="width:100%;font-size:0.8rem;background:#0f172a;border:1px solid #334155;color:#e2e8f0;padding:4px;">
                        <option value="">—</option>
                        {participant_opts}
                    </select>
                </td>
                <td style="padding:6px 4px;">
                    <input type="text" name="item_types" placeholder="e.g. apples"
                           style="width:100%;font-size:0.8rem;background:#0f172a;border:1px solid #334155;color:#e2e8f0;padding:4px;">
                </td>
                <td style="padding:6px 4px;">
                    <input type="number" name="quantities" min="0.001" step="any"
                           placeholder="0"
                           style="width:70px;font-size:0.8rem;background:#0f172a;border:1px solid #334155;color:#e2e8f0;padding:4px;">
                </td>
            </tr>'''

        create_form_html = f'''
        <form action="/api/trusted-trade/swap/create" method="post">
            <p style="font-size:0.85rem;color:#64748b;margin-bottom:12px;">
                Fill in each transfer leg: <em>who gives what item to whom</em>.
                Leave rows blank to skip them. Up to {MAX_SWAP_PARTIES} parties,
                {MAX_SWAP_LEGS} legs. Items only — no cash.
                The initiator (you) auto-accepts; all other parties must also accept.
            </p>
            <div style="overflow-x:auto;">
                <table style="width:100%;border-collapse:collapse;min-width:500px;">
                    <thead>
                        <tr style="border-bottom:1px solid #1e293b;font-size:0.8rem;color:#64748b;text-align:left;">
                            <th style="padding:6px 4px;">From</th>
                            <th style="padding:6px 4px;">To</th>
                            <th style="padding:6px 4px;">Item</th>
                            <th style="padding:6px 4px;">Qty</th>
                        </tr>
                    </thead>
                    <tbody>
                        {leg_rows}
                    </tbody>
                </table>
            </div>
            <div style="margin-top:12px;">
                <label style="font-size:0.85rem;color:#64748b;display:block;margin-bottom:4px;">
                    Notes (optional, visible to all parties)
                </label>
                <input type="text" name="notes" maxlength="500"
                       placeholder="e.g. 3-way trade — let me know if you want adjustments"
                       style="width:100%;background:#0f172a;border:1px solid #334155;color:#e2e8f0;padding:8px 10px;border-radius:4px;font-size:0.85rem;box-sizing:border-box;">
            </div>
            <button type="submit"
                    style="margin-top:12px;background:linear-gradient(135deg,#7c3aed,#4f46e5);color:#fff;border:none;padding:9px 20px;border-radius:4px;cursor:pointer;font-weight:bold;">
                Propose Swap
            </button>
        </form>'''

    alert_html = ""
    if msg:
        alert_html = f'<div style="background:#14532d;border:1px solid #16a34a;border-radius:6px;padding:10px 14px;margin-bottom:16px;color:#86efac;">{msg}</div>'
    if error:
        alert_html += f'<div style="background:#450a0a;border:1px solid #dc2626;border-radius:6px;padding:10px 14px;margin-bottom:16px;color:#fca5a5;">{error}</div>'

    body = f'''
    <a href="/inventory" style="color:#38bdf8;">&#8592; Inventory</a>
    &nbsp;|&nbsp;
    <a href="/inventory/trusted-list" style="color:#a78bfa;">Manage Trusted List</a>
    <h1>Item Swaps</h1>
    {alert_html}

    <p style="color:#64748b;margin-bottom:18px;">
        Privately trade items with your trusted partners.
        Both parties must be on each other&#39;s trusted list.
        Up to <strong>5 parties</strong> per swap. <strong>Items only</strong> — no cash.
    </p>

    <!-- Existing swaps -->
    <div class="card">
        <h3>Your Swaps</h3>
        <table style="width:100%;border-collapse:collapse;">
            <thead>
                <tr style="border-bottom:1px solid #1e293b;font-size:0.85rem;color:#64748b;text-align:left;">
                    <th style="padding:8px;">ID</th>
                    <th style="padding:8px;">Parties</th>
                    <th style="padding:8px;">Legs</th>
                    <th style="padding:8px;">Status</th>
                    <th style="padding:8px;">Created</th>
                    <th style="padding:8px;">Actions</th>
                </tr>
            </thead>
            <tbody>{swap_rows}</tbody>
        </table>
    </div>

    <!-- Create new swap -->
    <div class="card" style="margin-top:18px;">
        <h3>Propose a New Swap</h3>
        {create_form_html}
    </div>
    '''

    return shell("Item Swaps", body, player.cash_balance, player.id)


# ─── Swap Detail Page ─────────────────────────────────────────────────────────

@router.get("/inventory/swaps/{swap_id}", response_class=HTMLResponse)
def swap_detail_page(
    swap_id: int,
    session_token: Optional[str] = Cookie(None),
):
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player

    from trusted_trade import get_swap_detail

    swap, legs, acceptances = get_swap_detail(swap_id)
    participant_ids = {a.player_id for a in acceptances}

    if not swap or player.id not in participant_ids:
        return shell(
            "Swap Not Found",
            '<a href="/inventory/swaps" style="color:#38bdf8;">&#8592; Swaps</a>'
            '<p style="color:#64748b;margin-top:12px;">Swap not found or you are not a participant.</p>',
            player.cash_balance, player.id
        )

    status_color = {
        "pending":   "#f59e0b",
        "executed":  "#22c55e",
        "rejected":  "#ef4444",
        "cancelled": "#64748b",
        "failed":    "#ef4444",
    }.get(swap.status, "#64748b")

    # Legs table
    leg_rows = ""
    for leg in legs:
        leg_rows += f'''
        <tr style="border-bottom:1px solid #1e293b;">
            <td style="padding:8px;">{_player_name(leg.from_player_id)}</td>
            <td style="padding:8px;color:#64748b;">&#8594;</td>
            <td style="padding:8px;">{_player_name(leg.to_player_id)}</td>
            <td style="padding:8px;color:#38bdf8;">{leg.item_type.replace("_", " ").title()}</td>
            <td style="padding:8px;color:#f59e0b;">{leg.quantity:,.4g}</td>
        </tr>'''

    # Acceptance status
    acc_rows = ""
    for a in acceptances:
        acc_color = "#22c55e" if a.accepted else "#f59e0b"
        acc_label = "Accepted" if a.accepted else "Pending"
        acc_rows += f'''
        <tr style="border-bottom:1px solid #1e293b;">
            <td style="padding:8px;">{_player_name(a.player_id)}</td>
            <td style="padding:8px;color:{acc_color};font-weight:bold;">{acc_label}</td>
            <td style="padding:8px;color:#64748b;">
                {a.responded_at.strftime("%Y-%m-%d %H:%M UTC") if a.responded_at else "—"}
            </td>
        </tr>'''

    # Action buttons
    my_acc = next((a for a in acceptances if a.player_id == player.id), None)
    actions_html = ""
    if swap.status == "pending":
        if my_acc and not my_acc.accepted:
            actions_html = f'''
            <form action="/api/trusted-trade/swap/accept" method="post" style="display:inline;margin-right:8px;">
                <input type="hidden" name="swap_id" value="{swap.id}">
                <input type="hidden" name="redirect" value="/inventory/swaps/{swap.id}">
                <button type="submit"
                        style="background:#15803d;color:#fff;border:none;padding:8px 18px;border-radius:4px;cursor:pointer;font-weight:bold;">
                    &#10003; Accept Swap
                </button>
            </form>
            <form action="/api/trusted-trade/swap/reject" method="post" style="display:inline;">
                <input type="hidden" name="swap_id" value="{swap.id}">
                <input type="hidden" name="redirect" value="/inventory/swaps">
                <button type="submit"
                        style="background:#7f1d1d;color:#fca5a5;border:none;padding:8px 18px;border-radius:4px;cursor:pointer;font-weight:bold;">
                    &#10007; Reject
                </button>
            </form>'''
        elif swap.initiator_id == player.id:
            actions_html = f'''
            <form action="/api/trusted-trade/swap/cancel" method="post" style="display:inline;">
                <input type="hidden" name="swap_id" value="{swap.id}">
                <input type="hidden" name="redirect" value="/inventory/swaps">
                <button type="submit"
                        style="background:#374151;color:#9ca3af;border:none;padding:8px 18px;border-radius:4px;cursor:pointer;">
                    Cancel Swap
                </button>
            </form>'''
        else:
            actions_html = '<p style="color:#64748b;">Waiting for other participants to respond.</p>'

    body = f'''
    <a href="/inventory/swaps" style="color:#38bdf8;">&#8592; Swaps</a>
    <h1>Swap #{swap.id}</h1>

    <div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:18px;">
        <div class="card" style="flex:1;min-width:160px;text-align:center;">
            <div style="font-size:0.75rem;color:#64748b;">STATUS</div>
            <div style="font-size:1.4rem;font-weight:bold;color:{status_color};">{swap.status.upper()}</div>
        </div>
        <div class="card" style="flex:1;min-width:160px;text-align:center;">
            <div style="font-size:0.75rem;color:#64748b;">INITIATOR</div>
            <div style="font-size:1rem;font-weight:bold;">{_player_name(swap.initiator_id)}</div>
        </div>
        <div class="card" style="flex:1;min-width:160px;text-align:center;">
            <div style="font-size:0.75rem;color:#64748b;">CREATED</div>
            <div style="font-size:0.9rem;">{swap.created_at.strftime("%Y-%m-%d %H:%M UTC")}</div>
        </div>
        <div class="card" style="flex:1;min-width:160px;text-align:center;">
            <div style="font-size:0.75rem;color:#64748b;">EXPIRES</div>
            <div style="font-size:0.9rem;">{swap.expires_at.strftime("%Y-%m-%d %H:%M UTC") if swap.expires_at else "—"}</div>
        </div>
    </div>

    {f'<div class="card" style="margin-bottom:16px;border-color:#4f46e5;"><strong style="color:#a78bfa;">Notes:</strong> {swap.notes}</div>' if swap.notes else ""}

    <div class="card">
        <h3>Transfer Legs</h3>
        <table style="width:100%;border-collapse:collapse;">
            <thead>
                <tr style="border-bottom:1px solid #1e293b;font-size:0.85rem;color:#64748b;text-align:left;">
                    <th style="padding:8px;">From</th>
                    <th style="padding:8px;"></th>
                    <th style="padding:8px;">To</th>
                    <th style="padding:8px;">Item</th>
                    <th style="padding:8px;">Qty</th>
                </tr>
            </thead>
            <tbody>{leg_rows}</tbody>
        </table>
    </div>

    <div class="card" style="margin-top:16px;">
        <h3>Acceptance Status</h3>
        <table style="width:100%;border-collapse:collapse;">
            <thead>
                <tr style="border-bottom:1px solid #1e293b;font-size:0.85rem;color:#64748b;text-align:left;">
                    <th style="padding:8px;">Participant</th>
                    <th style="padding:8px;">Status</th>
                    <th style="padding:8px;">Responded</th>
                </tr>
            </thead>
            <tbody>{acc_rows}</tbody>
        </table>
    </div>

    <div style="margin-top:18px;">{actions_html}</div>
    '''

    return shell(f"Swap #{swap.id}", body, player.cash_balance, player.id)


# ─── API: Trusted-List actions ────────────────────────────────────────────────

@router.post("/api/trusted-trade/add")
async def api_add_trusted(
    target_id: int        = Form(...),
    session_token: Optional[str] = Cookie(None),
):
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player

    from trusted_trade import add_trusted_player
    ok, msg = add_trusted_player(player.id, target_id)
    if ok:
        return RedirectResponse(
            url=f"/inventory/trusted-list?msg={msg.replace(' ', '+')}", status_code=303
        )
    return RedirectResponse(
        url=f"/inventory/trusted-list?error={msg.replace(' ', '+')}", status_code=303
    )


@router.post("/api/trusted-trade/remove")
async def api_remove_trusted(
    entry_id: int         = Form(...),
    session_token: Optional[str] = Cookie(None),
):
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player

    from trusted_trade import remove_trusted_player
    ok, msg = remove_trusted_player(player.id, entry_id)
    if ok:
        return RedirectResponse(
            url=f"/inventory/trusted-list?msg={msg.replace(' ', '+')}", status_code=303
        )
    return RedirectResponse(
        url=f"/inventory/trusted-list?error={msg.replace(' ', '+')}", status_code=303
    )


# ─── API: Swap actions ────────────────────────────────────────────────────────

@router.post("/api/trusted-trade/swap/create")
async def api_create_swap(
    from_player_ids: List[str] = Form(...),
    to_player_ids:   List[str] = Form(...),
    item_types:      List[str] = Form(...),
    quantities:      List[str] = Form(...),
    notes: str                 = Form(""),
    session_token: Optional[str] = Cookie(None),
):
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player

    # Build leg list, skipping blank rows
    legs = []
    for from_p, to_p, itype, qty_str in zip(
        from_player_ids, to_player_ids, item_types, quantities
    ):
        if not from_p or not to_p or not itype.strip() or not qty_str.strip():
            continue
        try:
            qty = float(qty_str)
        except ValueError:
            continue
        if qty <= 0:
            continue
        try:
            legs.append({
                "from_player_id": int(from_p),
                "to_player_id":   int(to_p),
                "item_type":      itype.strip().lower().replace(" ", "_"),
                "quantity":       qty,
            })
        except ValueError:
            continue

    if not legs:
        return RedirectResponse(
            url="/inventory/swaps?error=No+valid+legs+found.+Fill+in+at+least+one+row.",
            status_code=303
        )

    from trusted_trade import create_swap
    swap_id, err = create_swap(player.id, legs, notes=notes)
    if swap_id is None:
        safe_err = err.replace(" ", "+").replace("&", "and")
        return RedirectResponse(
            url=f"/inventory/swaps?error={safe_err}", status_code=303
        )
    return RedirectResponse(
        url=f"/inventory/swaps/{swap_id}?msg=Swap+proposed+successfully.",
        status_code=303
    )


@router.post("/api/trusted-trade/swap/accept")
async def api_accept_swap(
    swap_id: int          = Form(...),
    redirect: str         = Form("/inventory/swaps"),
    session_token: Optional[str] = Cookie(None),
):
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player

    from trusted_trade import respond_to_swap
    ok, msg = respond_to_swap(swap_id, player.id, accept=True)
    safe_msg = msg.replace(" ", "+")
    if ok:
        return RedirectResponse(url=f"{redirect}?msg={safe_msg}", status_code=303)
    return RedirectResponse(url=f"{redirect}?error={safe_msg}", status_code=303)


@router.post("/api/trusted-trade/swap/reject")
async def api_reject_swap(
    swap_id: int          = Form(...),
    redirect: str         = Form("/inventory/swaps"),
    session_token: Optional[str] = Cookie(None),
):
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player

    from trusted_trade import respond_to_swap
    ok, msg = respond_to_swap(swap_id, player.id, accept=False)
    safe_msg = msg.replace(" ", "+")
    if ok:
        return RedirectResponse(url=f"{redirect}?msg={safe_msg}", status_code=303)
    return RedirectResponse(url=f"{redirect}?error={safe_msg}", status_code=303)


@router.post("/api/trusted-trade/swap/cancel")
async def api_cancel_swap(
    swap_id: int          = Form(...),
    redirect: str         = Form("/inventory/swaps"),
    session_token: Optional[str] = Cookie(None),
):
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player

    from trusted_trade import cancel_swap
    ok, msg = cancel_swap(swap_id, player.id)
    safe_msg = msg.replace(" ", "+")
    if ok:
        return RedirectResponse(url=f"{redirect}?msg={safe_msg}", status_code=303)
    return RedirectResponse(url=f"{redirect}?error={safe_msg}", status_code=303)
