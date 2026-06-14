"""
port_authority_ux.py

HTML frontend for the player-controlled Port Authority military institution.
Reuses the shared `ux.shell` page wrapper so it automatically inherits the
fast-load navigation loader, the player's skin/theme, and standard chrome.
All mutations go through the existing JSON API in port_authority.router.
"""

import json
from typing import Optional
from fastapi import APIRouter, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse

router = APIRouter()


def _require_auth(session_token: Optional[str]):
    from auth import get_db, get_player_from_session
    db = get_db()
    player = get_player_from_session(db, session_token)
    db.close()
    if not player:
        return RedirectResponse(url="/login", status_code=303)
    return player


def _shell(title: str, body: str, balance: float = 0.0, player_id: int = None) -> str:
    try:
        from ux import shell as ux_shell
        return ux_shell(title, body, balance, player_id)
    except Exception:
        try:
            from ux import _nav_loader_html as _nav_loader
            loader = _nav_loader()
        except Exception:
            loader = ""
        return (f"<!DOCTYPE html><html><head><meta charset='utf-8'>"
                f"<meta name='viewport' content='width=device-width, initial-scale=1'>"
                f"<title>{title}</title></head><body>{body}{loader}</body></html>")


def _label(slug: str) -> str:
    return slug.replace("_", " ").title()


def _readiness_rows(breakdown: dict) -> str:
    rows = []
    for slot, info in breakdown.items():
        have, need, met = info["have"], info["need"], info["met"]
        color = "#4ade80" if met else "#f87171"
        mark = "✓" if met else "✗"
        rows.append(
            f"<tr><td style='padding:4px 10px;'>{_label(slot)}</td>"
            f"<td style='padding:4px 10px;text-align:right;color:{color};'>"
            f"{have:g} / {need} {mark}</td></tr>"
        )
    return "".join(rows)


def _contracts_section(player_id: int, player_inv: dict, fmt_usd=None) -> str:
    """Render the three government contracts panels.

    `fmt_usd` is the display-currency formatter from the page render (converts a
    USD amount to the player's legal tender for display). Falls back to plain USD.
    """
    if fmt_usd is None:
        fmt_usd = lambda amount, precision=0: f"${amount:,.{precision}f}"
    try:
        from port_authority import get_open_contracts, get_player_bids, get_won_contract
        from datetime import datetime, timezone
        open_contracts = get_open_contracts()
        my_bids = {b["contract_id"]: b for b in get_player_bids(player_id, limit=50)}
        won = get_won_contract(player_id)
    except Exception as e:
        return f"<p style='color:#f87171;'>Error loading contracts: {e}</p>"

    now = datetime.utcnow()

    # ── Panel A: Open Contracts ──────────────────────────────────────────
    if open_contracts:
        contract_cards = []
        for c in open_contracts:
            cid = c["id"]
            req = c["required_items"]
            closes = c["bid_closes_at"][:16] if c.get("bid_closes_at") else "—"
            def _req_row(it, qty):
                c_ok = "#4ade80" if player_inv.get(it, 0) >= qty else "#f87171"
                return (f"<tr><td style='padding:2px 8px;'>{_label(it)}</td>"
                        f"<td style='padding:2px 8px;text-align:right;'>"
                        f"<b style='color:{c_ok};'>{player_inv.get(it,0):g}</b>"
                        f" / {qty:g}</td></tr>")
            req_rows = "".join(_req_row(it, qty) for it, qty in req.items())
            existing_bid = my_bids.get(cid)
            if existing_bid:
                bid_html = (
                    f"<div style='margin-top:8px;padding:6px;background:#1a2a1a;border:1px solid #2D4A1A;'>"
                    f"<b style='color:#4ade80;'>✓ Bid Submitted</b> — "
                    f"Status: <b>{existing_bid['status'].title()}</b> &nbsp;•&nbsp; "
                    f"Deposit: {fmt_usd(existing_bid['deposit_paid_usd'])}"
                    f"</div>"
                )
            else:
                method = c.get("selection_method", "cheapest")
                if method == "best_volume":
                    bid_input = (
                        f"<label style='display:flex;flex-direction:column;gap:3px;'>"
                        f"Volume Multiplier (e.g. 1.5 = 50% extra delivery offered)<br>"
                        f"<input id='bid-vol-{cid}' type='number' min='1' step='0.01' value='1.0' "
                        f"style='padding:5px;width:140px;'></label>"
                    )
                    bid_param = f"null, parseFloat(document.getElementById('bid-vol-{cid}').value)"
                else:
                    bid_input = (
                        f"<label style='display:flex;flex-direction:column;gap:3px;'>"
                        f"Your TOTAL Bid Price — what you charge the government for everything, in USD "
                        f"<span style='color:#94a3b8;font-size:0.85em;'>(cheapest total bid wins, and you're "
                        f"paid your own winning bid — you keep the difference over your cost as profit. "
                        f"Bids quoted in USD for fair comparison; your deposit &amp; payout settle in your "
                        f"own currency.)</span><br>"
                        f"<input id='bid-price-{cid}' type='number' min='0' step='1000' "
                        f"placeholder='Enter your total price' "
                        f"style='padding:5px;width:200px;'></label>"
                    )
                    bid_param = f"parseFloat(document.getElementById('bid-price-{cid}').value||'0')"
                bid_html = f"""
                <div style="margin-top:10px;display:flex;gap:10px;flex-wrap:wrap;align-items:flex-end;">
                  {bid_input}
                  <button onclick="paSubmitBid({cid},{bid_param})"
                    style="padding:6px 16px;cursor:pointer;background:#8B4513;color:#F5F5DC;border:1px solid #B08D57;">
                    Submit Bid ({fmt_usd(c['security_deposit_usd'])} deposit)
                  </button>
                </div>"""

            _is_cheapest = c.get("selection_method", "cheapest") == "cheapest"
            selection_label = "Cheapest bid wins" if _is_cheapest else "Highest volume offered wins"
            # "cheapest" winners are paid their own winning bid, so there's no fixed payout
            # figure to show; "best_volume" has a fixed payment.
            pay_label = (f'💰 Pays: <b style="color:#4ade80;">your winning bid</b>'
                         if _is_cheapest else
                         f'💰 Payment: <b style="color:#4ade80;">{fmt_usd(c["payment_usd"])}</b>')
            contract_cards.append(f"""
            <div style="border:1px solid #2D1810;padding:12px;margin-bottom:10px;">
              <b style="color:#B08D57;font-size:1.05em;">{c['title']}</b>
              <p style="color:#94a3b8;margin:4px 0 8px;">{c.get('description') or ''}</p>
              <div style="display:flex;gap:16px;flex-wrap:wrap;margin-bottom:8px;">
                <span>{pay_label}</span>
                <span>🏆 Trophies: <b style="color:#fbbf24;">{c['trophy_reward']}</b></span>
                <span>📅 Bid closes: <b style="color:#F5F5DC;">{closes} UTC</b></span>
                <span>⏱ Fulfillment: <b>{c['fulfillment_days']} days</b> after winning</span>
                <span style="color:#94a3b8;font-size:0.85em;">{selection_label}</span>
              </div>
              <p style="margin:4px 0 6px;">Required items <span style="color:#94a3b8;font-size:0.85em;">(your inventory / needed)</span>:</p>
              <table style="border-collapse:collapse;margin-bottom:6px;">{req_rows}</table>
              {bid_html}
            </div>""")
        open_html = "".join(contract_cards)
    else:
        open_html = "<p style='color:#94a3b8;'>No government contracts are open for bidding right now. Check back after the next contract cycle.</p>"

    # ── Panel B: Active Won Contract ─────────────────────────────────────
    if won:
        req = won["required_items"]
        fulfilled_so_far = won.get("fulfilled_items", {})
        deadline = won.get("fulfill_deadline", "")[:16] if won.get("fulfill_deadline") else "—"

        def _won_row(it, qty):
            shipped = fulfilled_so_far.get(it, 0.0)
            pct = min(100.0, (shipped / qty * 100)) if qty > 0 else 100.0
            bar_color = "#4ade80" if pct >= 100 else "#fbbf24"
            have = player_inv.get(it, 0.0)
            have_label_color = "#4ade80" if have > 0 else "#94a3b8"
            return (
                f"<tr>"
                f"<td style='padding:4px 10px;'>{_label(it)}</td>"
                f"<td style='padding:4px 10px;text-align:right;'>"
                f"<b style='color:{bar_color};'>{shipped:g}</b> / {qty:g} shipped</td>"
                f"<td style='padding:4px 10px;min-width:120px;'>"
                f"<div style='background:#1a1a1a;height:8px;border-radius:4px;overflow:hidden;'>"
                f"<div style='background:{bar_color};width:{pct:.0f}%;height:100%;'></div></div></td>"
                f"<td style='padding:4px 10px;text-align:right;color:{have_label_color};'>"
                f"{have:g} in inv</td>"
                f"</tr>"
            )
        req_rows = "".join(_won_row(it, qty) for it, qty in req.items())

        has_any_to_ship = any(
            player_inv.get(it, 0.0) > 0 and fulfilled_so_far.get(it, 0.0) < qty
            for it, qty in req.items()
        )
        fully_done = all(fulfilled_so_far.get(it, 0.0) >= qty for it, qty in req.items())

        if fully_done:
            ship_btn = "<p style='color:#4ade80;margin-top:10px;font-size:1.1em;'>✅ All items shipped — awaiting government processing.</p>"
        elif has_any_to_ship:
            ship_btn = (
                f"<button onclick=\"paFulfill({won['id']})\" "
                f"style='padding:8px 20px;cursor:pointer;background:#1a4a1a;color:#4ade80;"
                f"border:2px solid #4ade80;font-size:1rem;margin-top:12px;'>"
                f"📦 Ship What I Have</button>"
                f"<p style='color:#94a3b8;font-size:0.85em;margin-top:4px;'>"
                f"Ships as much as possible from your inventory. Click again as you produce more.</p>"
            )
        else:
            ship_btn = (
                "<p style='color:#f87171;margin-top:10px;'>⚠ None of the required items are in your inventory yet. "
                "Produce or purchase them and return here to ship.</p>"
            )

        # For "cheapest" contracts the payout is the player's own winning bid, not the
        # contract's "up to" reference; "best_volume" pays the fixed payment_usd.
        _won_payout = (won.get("winning_bid_price_usd")
                       if won.get("selection_method", "cheapest") == "cheapest"
                       else won.get("payment_usd"))
        if _won_payout is None:
            _won_payout = won.get("payment_usd", 0)
        _payout_note = ("your winning bid, tax-free"
                        if won.get("selection_method", "cheapest") == "cheapest"
                        else "tax-free")
        won_html = f"""
        <div style="border:2px solid #4ade80;padding:14px;background:#0a1a0a;">
          <b style="color:#4ade80;font-size:1.1em;">🏆 Won Contract: {won['title']}</b>
          <p style="color:#94a3b8;margin:4px 0;">{won.get('description') or ''}</p>
          <p style="margin:6px 0;">
            Deadline: <b style="color:#fbbf24;">{deadline} UTC</b> &nbsp;•&nbsp;
            Payment on completion: <b style="color:#4ade80;">{fmt_usd(_won_payout)}</b> ({_payout_note}) &nbsp;•&nbsp;
            Trophies: <b style="color:#fbbf24;">{won['trophy_reward']}</b> &nbsp;•&nbsp;
            Deposit back: <b>{fmt_usd(won.get('deposit_paid_usd',0))}</b>
          </p>
          <p style="margin:4px 0;">Contract fulfillment progress:</p>
          <table style="border-collapse:collapse;width:100%;">{req_rows}</table>
          {ship_btn}
        </div>"""
    else:
        won_html = "<p style='color:#94a3b8;'>You have no active won contracts to fulfill.</p>"

    # ── Panel C: Bid History ─────────────────────────────────────────────
    bid_list = list(my_bids.values())
    if bid_list:
        status_colors = {"won": "#4ade80", "fulfilled": "#4ade80", "pending": "#fbbf24",
                         "lost": "#94a3b8", "forfeited": "#f87171"}
        def _bid_row(b):
            sc = status_colors.get(b["status"], "#F5F5DC")
            dep_color = "#4ade80" if b["deposit_returned"] else "#94a3b8"
            dep_label = "✓ Returned" if b["deposit_returned"] else "Held"
            return (f"<tr><td style='padding:4px 10px;'>{b['contract_title']}</td>"
                    f"<td style='padding:4px 10px;text-align:right;'>{fmt_usd(b['bid_price_usd'])}</td>"
                    f"<td style='padding:4px 10px;'><b style='color:{sc};'>{b['status'].title()}</b></td>"
                    f"<td style='padding:4px 10px;text-align:right;'>{fmt_usd(b['deposit_paid_usd'])}</td>"
                    f"<td style='padding:4px 10px;color:{dep_color};'>{dep_label}</td></tr>")
        history_rows = "".join(_bid_row(b) for b in bid_list[:15])
        history_html = f"""
        <table style="width:100%;border-collapse:collapse;border:1px solid #2D1810;">
          <tr style="color:#94a3b8;border-bottom:1px solid #2D1810;">
            <td style="padding:4px 10px;">Contract</td>
            <td style="padding:4px 10px;text-align:right;">Bid Price</td>
            <td style="padding:4px 10px;">Status</td>
            <td style="padding:4px 10px;text-align:right;">Deposit</td>
            <td style="padding:4px 10px;">Deposit</td>
          </tr>
          {history_rows}
        </table>"""
    else:
        history_html = "<p style='color:#94a3b8;'>No bids submitted yet.</p>"

    return f"""
    <!-- ── Panel B: Active Contract ──────────────────────────────────────── -->
    <h3 style="color:#4ade80;margin-top:0 0 10px;">Active Contract</h3>
    {won_html}

    <!-- ── Panel A: Open Contracts ──────────────────────────────────────── -->
    <h3 style="color:#B08D57;margin-top:22px;">Open Contracts — Bidding Now</h3>
    {open_html}

    <!-- ── Panel C: Bid History ──────────────────────────────────────────── -->
    <h3 style="color:#B08D57;margin-top:22px;">My Bid History</h3>
    {history_html}
    """


@router.get("/port-authority", response_class=HTMLResponse)
def port_authority_dashboard(session_token: Optional[str] = Cookie(None)):
    player = _require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player

    try:
        from port_authority import (
            get_port_authority, get_missions, ALL_PA_ITEMS,
            FLEET_THRESHOLDS, ARMY_THRESHOLDS, MAINTENANCE_DAILY,
            get_active_blockades_against, get_active_blockades_by,
        )
        from inventory import get_player_inventory
        from reserve_banks import fmt_usd as _fmt_usd, get_player_display_currency
    except Exception as e:
        return HTMLResponse(_shell("Port Authority",
                                   f"<div style='color:#ef4444;'>Module error: {e}</div>",
                                   0.0, player.id))

    # Display currency for fmt_usd (player's legal tender). Local wrapper so the
    # body f-string can call fmt_usd(amount) without threading disp everywhere.
    try:
        _disp = get_player_display_currency(player.id)
    except Exception:
        _disp = {"code": "USD", "symbol": "$", "usd_per_unit": 1.0}

    def fmt_usd(amount, precision: int = 0):
        return _fmt_usd(amount, _disp, precision=precision)

    pa = get_port_authority(player.id)

    # ── No PA yet — route through land sacrifice ──────────────────────────────
    if pa is None:
        from port_authority import get_unbuilt_pa_plot
        ready_plot = get_unbuilt_pa_plot(player.id)

        intro = """
          <p>The Port Authority is a sovereign maritime <b>Institution</b> built on
          <b>water terrain</b> (coastal, island, lake, ocean, or riverside). It gives you
          control over three powerful systems:</p>
          <ul style="line-height:1.8;">
            <li><b>Federal Procurement Contracts</b> — fulfill government weapons contracts
              from your PA inventory for large USD payouts from the federal treasury.</li>
            <li><b>Immigration Control</b> — set volume (retail foot traffic) and wealth
              (customer spending power) to reshape demand across the entire economy.</li>
            <li><b>Naval &amp; Military Missions</b> — deploy Fleet or Army forces to
              <em>procurement-raid</em> another player's PA inventory or impose a
              24-hour <em>blockade</em> on their item transfers. Pure 50/50 RNG.</li>
          </ul>
          <p style="color:#94a3b8;">Any mission failure destroys 10% of your PA inventory.
          Maintenance is auto-deducted daily. Like the Mint, it pays a monthly institution tax.</p>
        """

        if ready_plot is not None:
            action = f"""
              <p style="color:#4ade80;">You have a vacant Port Authority Institution (plot #{ready_plot.id}). Build your command there:</p>
              <button onclick="paBuild({ready_plot.id})" style="margin-top:8px;padding:12px 24px;background:#8B4513;color:#F5F5DC;border:2px solid #B08D57;font-family:Georgia,serif;font-size:1rem;cursor:pointer;">
                ⚓ Build Port Authority
              </button>
              <div id="pa-msg" style="margin-top:14px;"></div>
              <script>
              async function paBuild(pid){{
                const r = await fetch('/special-plots/'+pid+'/build-port-authority', {{method:'POST'}});
                if (r.redirected) {{ location.href = '/port-authority'; return; }}
                location.reload();
              }}
              </script>
            """
        else:
            action = """
              <p style="color:#fbbf24;">A Port Authority is built on a water-terrain Institution.
              First sacrifice <b>coastal, island, lake, or ocean</b> land to create a
              <b>Port Authority</b> Institution (Wadsworth Pro required), then return here to build.</p>
              <a href="/special-plots/create" style="display:inline-block;margin-top:8px;padding:12px 24px;background:#8B4513;color:#F5F5DC;border:2px solid #B08D57;font-family:Georgia,serif;font-size:1rem;text-decoration:none;">
                🏛️ Create a Port Authority Institution
              </a>
            """

        body = f"""
        <div style="max-width:640px;margin:0 auto;padding:20px;color:#F5F5DC;font-family:Georgia,serif;">
          <h1 style="color:#B08D57;">⚓ Port Authority</h1>
          {intro}
          {action}
        </div>
        """
        return HTMLResponse(_shell("Port Authority", body, 0.0, player.id))

    # ── Dashboard ────────────────────────────────────────────────────────────
    inv = pa["inventory"]
    daily = pa["daily_maintenance_usd"]
    imm_vol = pa.get("immigration_volume", 1.0)
    imm_wlth = pa.get("immigration_wealth", 1.0)

    # PA inventory table
    if inv:
        inv_rows = "".join(
            f"<tr><td style='padding:4px 10px;'>{_label(it)}</td>"
            f"<td style='padding:4px 10px;text-align:right;'>{qty:g}</td>"
            f"<td style='padding:4px 10px;text-align:right;color:#94a3b8;'>"
            f"{fmt_usd(MAINTENANCE_DAILY.get(it,0.0)*qty)}/day</td>"
            f"<td style='padding:4px 10px;text-align:right;'>"
            f"<button onclick=\"paMove('withdraw','{it}')\" style='cursor:pointer;'>Withdraw</button></td></tr>"
            for it, qty in sorted(inv.items())
        )
    else:
        inv_rows = "<tr><td colspan='4' style='padding:10px;color:#94a3b8;'>Empty — deposit weapons below.</td></tr>"

    # Depositable items from player inventory (PA-eligible only)
    player_inv = get_player_inventory(player.id)
    depositable = {it: q for it, q in player_inv.items() if it in ALL_PA_ITEMS and q > 0}
    opts = "".join(f"<option value='{it}'>{_label(it)} ({q:g} held)</option>"
                   for it, q in sorted(depositable.items()))
    if not opts:
        opts = "<option value=''>No PA-eligible weapons in your inventory</option>"

    fleet_ready = pa["fleet_ready"]
    army_ready = pa["army_ready"]

    # Mission history
    missions = get_missions(player.id, limit=10)
    if missions:
        m_rows = []
        for m in missions:
            outcome_color = "#4ade80" if m["outcome"] == "success" else "#f87171"
            subtype = m.get("mission_subtype") or m.get("mission_type", "")
            detail = ""
            if m.get("items_acquired"):
                acq = m["items_acquired"] if isinstance(m["items_acquired"], dict) else {}
                detail = "Acquired: " + ", ".join(f"{v:g}×{_label(k)}" for k, v in acq.items())
            elif m.get("items_lost"):
                lost = m["items_lost"] if isinstance(m["items_lost"], dict) else {}
                detail = "Lost: " + ", ".join(f"{v:g}×{_label(k)}" for k, v in lost.items())
            m_rows.append(
                f"<tr><td style='padding:4px 10px;'>{_label(subtype)}</td>"
                f"<td style='padding:4px 10px;'>Player {m.get('target_player_id') or m.get('target_player','—')}</td>"
                f"<td style='padding:4px 10px;'>{_label(m.get('target_item_type','') or '')}</td>"
                f"<td style='padding:4px 10px;color:{outcome_color};'>{(m['outcome'] or '').title()}</td>"
                f"<td style='padding:4px 10px;color:#94a3b8;font-size:0.85em;'>{detail}</td></tr>"
            )
        m_rows_html = "".join(m_rows)
    else:
        m_rows_html = "<tr><td colspan='5' style='padding:10px;color:#94a3b8;'>No missions yet.</td></tr>"

    # Active blockades
    blockades_on_me = get_active_blockades_against(player.id)
    blockades_by_me = get_active_blockades_by(player.id)
    def _blockade_row(b, perspective):
        other = b.get("target_player_id") if perspective == "placed" else b.get("blocker_player_id")
        return (f"<tr><td style='padding:4px 10px;'>{perspective.title()}</td>"
                f"<td style='padding:4px 10px;'>Player {other}</td>"
                f"<td style='padding:4px 10px;'>{_label(b.get('item_type',''))}</td>"
                f"<td style='padding:4px 10px;color:#94a3b8;font-size:0.85em;'>"
                f"Expires {b.get('expires_at','')[:16]}</td></tr>")
    blockade_rows = (
        "".join(_blockade_row(b, "against you") for b in blockades_on_me) +
        "".join(_blockade_row(b, "placed") for b in blockades_by_me)
    ) or "<tr><td colspan='4' style='padding:10px;color:#94a3b8;'>No active blockades.</td></tr>"

    # Government contracts section (uses player's regular inventory, not PA inv)
    contracts_html = _contracts_section(player.id, player_inv, fmt_usd)

    # Executive military bonus
    mil_bonus = 0.0
    try:
        from executive import get_player_job_bonus
        from database import SessionLocal as _ES
        _edb = _ES()
        try:
            mil_bonus = get_player_job_bonus(_edb, player.id, "military")
        finally:
            _edb.close()
    except Exception:
        pass
    mil_bonus_note = (
        f' &nbsp;•&nbsp; <span style="color:#a78bfa;">CDO Bonus: −{mil_bonus*100:.0f}% upkeep / +{mil_bonus*100:.0f}% contracts</span>'
        if mil_bonus > 0 else ""
    )

    body = f"""
    <div style="max-width:800px;margin:0 auto;padding:16px;color:#F5F5DC;font-family:Georgia,serif;">
      <h1 style="color:#B08D57;">⚓ {pa['name']}</h1>
      <p style="color:#94a3b8;">
        Daily upkeep: <b style="color:#fbbf24;">{fmt_usd(daily)}/day</b>
        &nbsp;•&nbsp; Fleet: <b style="color:{'#4ade80' if fleet_ready else '#f87171'};">{'READY' if fleet_ready else 'not ready'}</b>
        &nbsp;•&nbsp; Army: <b style="color:{'#4ade80' if army_ready else '#f87171'};">{'READY' if army_ready else 'not ready'}</b>
        {mil_bonus_note}
      </p>

      <div style="display:flex;flex-wrap:wrap;gap:16px;margin-top:12px;">
        <div style="flex:1;min-width:260px;border:1px solid #2D1810;padding:10px;">
          <h3 style="color:#B08D57;margin:0 0 6px;">Fleet Readiness</h3>
          <table style="width:100%;border-collapse:collapse;">{_readiness_rows(pa['fleet_breakdown'])}</table>
        </div>
        <div style="flex:1;min-width:260px;border:1px solid #2D1810;padding:10px;">
          <h3 style="color:#B08D57;margin:0 0 6px;">Army Readiness</h3>
          <table style="width:100%;border-collapse:collapse;">{_readiness_rows(pa['army_breakdown'])}</table>
        </div>
      </div>

      <!-- ── Government Contracts ──────────────────────────────────── -->
      <h2 style="color:#B08D57;margin-top:28px;border-top:1px solid #2D1810;padding-top:16px;">
        📋 Government Contracts
      </h2>
      <p style="color:#94a3b8;margin:0 0 16px;font-size:0.9em;">
        Bid on federal procurement contracts — win by submitting the best bid,
        fulfill within the deadline to earn tax-free payment + trophies.
        Items ship from your regular inventory, not your PA military depot.
      </p>
      {contracts_html}

      <!-- ── Immigration Policy ─────────────────────────────────────── -->
      <h3 style="color:#B08D57;margin-top:22px;">🌍 Immigration Policy</h3>
      <div style="border:1px solid #2D1810;padding:12px;">
        <p style="color:#94a3b8;margin:0 0 10px;">
          Controls retail demand across the economy.
          Volume = foot traffic (0–3×). Wealth = spending power &amp; price tolerance (0.5–2×).
        </p>
        <div style="display:flex;gap:24px;flex-wrap:wrap;">
          <label style="flex:1;min-width:200px;">
            Volume <span id="vol-val">{imm_vol:.2f}</span>×
            <input type="range" min="0" max="3" step="0.05" value="{imm_vol}"
              oninput="document.getElementById('vol-val').textContent=parseFloat(this.value).toFixed(2)"
              id="imm-vol" style="width:100%;margin-top:4px;">
            <small style="color:#94a3b8;">0 = no immigration, 3 = triple retail demand</small>
          </label>
          <label style="flex:1;min-width:200px;">
            Wealth <span id="wlth-val">{imm_wlth:.2f}</span>×
            <input type="range" min="0.5" max="2" step="0.05" value="{imm_wlth}"
              oninput="document.getElementById('wlth-val').textContent=parseFloat(this.value).toFixed(2)"
              id="imm-wlth" style="width:100%;margin-top:4px;">
            <small style="color:#94a3b8;">0.5 = poor / price-sensitive, 2 = affluent / pays premium</small>
          </label>
        </div>
        <button onclick="paSetImmigration()" style="margin-top:10px;padding:6px 16px;cursor:pointer;background:#8B4513;color:#F5F5DC;border:1px solid #B08D57;">
          Apply Immigration Policy
        </button>
      </div>

      <!-- ── Inventory ──────────────────────────────────────────────── -->
      <h3 style="color:#B08D57;margin-top:22px;">Inventory</h3>
      <table style="width:100%;border-collapse:collapse;border:1px solid #2D1810;">{inv_rows}</table>

      <h3 style="color:#B08D57;margin-top:18px;">Deposit Weapons</h3>
      <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
        <select id="dep-item" style="padding:6px;flex:1;min-width:220px;">{opts}</select>
        <input id="dep-qty" type="number" min="1" value="1" style="padding:6px;width:90px;">
        <button onclick="paMove('deposit', document.getElementById('dep-item').value)" style="padding:6px 14px;cursor:pointer;">Deposit</button>
      </div>

      <!-- ── Deploy Mission ─────────────────────────────────────────── -->
      <h3 style="color:#B08D57;margin-top:22px;">⚔️ Deploy Mission</h3>
      <div style="border:1px solid #2D1810;padding:12px;">
        <p style="color:#94a3b8;margin:0 0 10px;">
          Requires Fleet (carriers/subs/destroyers/jets) or Army (tanks/helos/rifles/armored/drones) readiness.
          Outcome is 50/50 — failure destroys 10% of PA inventory.
        </p>
        <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:flex-end;">
          <label style="display:flex;flex-direction:column;gap:4px;flex:1;min-width:160px;">
            Mission type
            <select id="msubtype" style="padding:6px;">
              <option value="procurement">Procurement Raid (seize items)</option>
              <option value="blockade">Blockade (freeze transfers 24h)</option>
            </select>
          </label>
          <label style="display:flex;flex-direction:column;gap:4px;flex:1;min-width:160px;">
            Target Player ID
            <input id="target-pid" type="number" placeholder="Player ID" style="padding:6px;">
          </label>
          <label style="display:flex;flex-direction:column;gap:4px;flex:1;min-width:160px;">
            Target Item (slug)
            <input id="target-item" type="text" placeholder="e.g. m1a2_abrams" style="padding:6px;">
          </label>
          <label id="qty-wrap" style="display:flex;flex-direction:column;gap:4px;width:90px;">
            Quantity
            <input id="target-qty" type="number" min="1" value="1" style="padding:6px;">
          </label>
          <button onclick="paDeploy()" style="padding:6px 14px;cursor:pointer;background:#8B4513;color:#F5F5DC;border:1px solid #B08D57;">Deploy</button>
        </div>
      </div>

      <!-- ── Active Blockades ───────────────────────────────────────── -->
      <h3 style="color:#B08D57;margin-top:22px;">🚫 Active Blockades</h3>
      <table style="width:100%;border-collapse:collapse;border:1px solid #2D1810;">
        <tr style="color:#94a3b8;">
          <td style="padding:4px 10px;">Direction</td>
          <td style="padding:4px 10px;">Player</td>
          <td style="padding:4px 10px;">Item</td>
          <td style="padding:4px 10px;">Expires</td>
        </tr>
        {blockade_rows}
      </table>

      <!-- ── Mission History ────────────────────────────────────────── -->
      <h3 style="color:#B08D57;margin-top:22px;">Recent Missions</h3>
      <table style="width:100%;border-collapse:collapse;border:1px solid #2D1810;">
        <tr style="color:#94a3b8;">
          <td style="padding:4px 10px;">Type</td>
          <td style="padding:4px 10px;">Target</td>
          <td style="padding:4px 10px;">Item</td>
          <td style="padding:4px 10px;">Outcome</td>
          <td style="padding:4px 10px;">Detail</td>
        </tr>
        {m_rows_html}
      </table>

      <div id="pa-msg" style="margin-top:14px;min-height:20px;color:#fbbf24;"></div>
    </div>
    <script>
    function _show(t){{ document.getElementById('pa-msg').textContent = t; }}

    async function paMove(action, item){{
      if(!item){{ _show('Select an item first.'); return; }}
      const qty = action==='deposit' ? parseFloat(document.getElementById('dep-qty').value||'1') : 1;
      const r = await fetch('/api/port-authority/'+action, {{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{item_type:item, quantity:qty}})}});
      const j = await r.json(); _show(j.message || j.error || '');
      if(j.ok) setTimeout(()=>location.reload(), 600);
    }}

    async function paSubmitBid(contractId, bidPrice, bidVol){{
      if(bidPrice !== null && bidPrice !== undefined && !(bidVol > 0) && !(bidPrice > 0)){{
        _show('Enter a bid price greater than 0.'); return;
      }}
      const body = {{bid_price_usd: bidPrice || 0, bid_volume_multiplier: bidVol || 1.0}};
      const r = await fetch('/api/port-authority/contracts/'+contractId+'/bid', {{
        method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify(body)
      }});
      const j = await r.json();
      _show(j.message || j.error || '');
      if(j.ok) setTimeout(()=>location.reload(), 800);
    }}

    async function paFulfill(contractId){{
      const r = await fetch('/api/port-authority/contracts/'+contractId+'/fulfill', {{method:'POST'}});
      const j = await r.json();
      const result = j.result || j;
      _show(result.message || j.message || j.error || '');
      if(j.ok) setTimeout(()=>location.reload(), 800);
    }}

    async function paSetImmigration(){{
      const volume = parseFloat(document.getElementById('imm-vol').value);
      const wealth = parseFloat(document.getElementById('imm-wlth').value);
      const r = await fetch('/api/port-authority/immigration', {{
        method:'POST', headers:{{'Content-Type':'application/json'}},
        body: JSON.stringify({{volume, wealth}})
      }});
      const j = await r.json();
      _show(j.message || j.error || '');
    }}

    document.getElementById('msubtype').addEventListener('change', function(){{
      document.getElementById('qty-wrap').style.display = this.value==='procurement' ? '' : 'none';
    }});

    async function paDeploy(){{
      const subtype = document.getElementById('msubtype').value;
      const pid = parseInt(document.getElementById('target-pid').value||'0');
      const item = document.getElementById('target-item').value.trim();
      const qty  = parseInt(document.getElementById('target-qty').value||'1');
      if(!pid){{ _show('Enter target player ID.'); return; }}
      if(!item){{ _show('Enter target item slug.'); return; }}
      const body = {{mission_subtype: subtype, target_player_id: pid, target_item_type: item, target_quantity: qty}};
      const r = await fetch('/api/port-authority/deploy', {{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(body)}});
      const j = await r.json();
      if(j.error){{ _show(j.error); return; }}
      const outcome = j.outcome || '';
      let detail = '';
      if(j.items_acquired && Object.keys(j.items_acquired).length){{
        detail = ' — acquired: ' + Object.entries(j.items_acquired).map(([k,v])=>v+'×'+k).join(', ');
      }} else if(j.blockade_placed){{
        detail = ' — 24h blockade imposed';
      }}
      _show('Mission ' + outcome + detail);
      setTimeout(()=>location.reload(), 1500);
    }}
    </script>
    """
    return HTMLResponse(_shell("Port Authority", body, 0.0, player.id))
