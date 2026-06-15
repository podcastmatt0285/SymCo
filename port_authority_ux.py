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


_SLIDER_DEFS = [
    ("s_quantity_affluence",  "Many Immigrants",    "Wealthy Immigrants",
     "demand, elasticity"),
    ("s_labor_consumers",     "Labor Force",        "Consumers",
     "production, demand"),
    ("s_skilled_unskilled",   "Skilled Workers",    "Unskilled Workers",
     "production, input costs"),
    ("s_young_mature",        "Young / Trendy",     "Mature / Families",
     "demand, elasticity"),
    ("s_assimilated_diverse", "Assimilated",        "Diverse / Cosmopolitan",
     "elasticity, demand"),
    ("s_selective_open",      "Selective Entry",    "Open Borders",
     "elasticity, demand"),
    ("s_urban_rural",         "Urban Settlers",     "Rural Settlers",
     "demand, land yield"),
    ("s_inland_coastal",      "Inland Communities", "Coastal Communities",
     "production, input costs"),
    ("s_farmer_urbanworker",  "Tenant Farmers",     "Urban Workers",
     "land yield, production"),
    ("s_conserve_intensive",  "Conservationist",    "Intensive Land Use",
     "input costs, land yield"),
]

# Mirror of port_authority._SLIDER_COEFFS for client-side preview (serialised to JS)
_COEFFS_JS = {
    "s_quantity_affluence":  [-1, -1,  0,  0,  0],
    "s_labor_consumers":     [ 1,  0, -1,  0,  0],
    "s_skilled_unskilled":   [ 0,  0, -1, -1,  0],
    "s_young_mature":        [-1, -1,  0,  0,  0],
    "s_assimilated_diverse": [ 1,  1,  0,  0,  0],
    "s_selective_open":      [ 1, -1,  0,  0,  0],
    "s_urban_rural":         [-1,  0,  0,  0,  1],
    "s_inland_coastal":      [ 0,  0, -1, -1,  0],
    "s_farmer_urbanworker":  [ 0,  0,  1,  0, -1],
    "s_conserve_intensive":  [ 0,  0,  0,  1,  1],
}


def _build_immigration_panel(status: dict) -> str:
    """Render the full immigration policy panel HTML."""
    import json as _json
    active    = status.get("active", False)
    cooldown  = status.get("cooldown", False)
    sliders   = status.get("sliders", {})
    df        = status.get("decay_factor", 0.0)
    expires   = status.get("expires_at")
    cd_until  = status.get("cooldown_until")

    # Status header
    if active:
        pct = int(df * 100)
        status_html = (
            f"<div style='background:#1a2a1a;border:1px solid #4ade80;padding:10px;margin-bottom:14px;'>"
            f"<span style='color:#4ade80;font-weight:bold;'>● Policy Active</span>"
            f"<span style='color:#94a3b8;margin-left:12px;'>expires {expires[:10] if expires else '?'}</span>"
            f"<div style='margin-top:6px;background:#0f1f0f;height:6px;border-radius:3px;'>"
            f"<div style='background:#4ade80;height:6px;border-radius:3px;width:{pct}%;transition:width 1s;'></div>"
            f"</div><small style='color:#94a3b8;'>Sliders locked — decaying to neutral over 3 days.</small>"
            f"</div>"
        )
        disabled = "disabled"
    elif cooldown:
        status_html = (
            f"<div style='background:#2a1a1a;border:1px solid #f87171;padding:10px;margin-bottom:14px;'>"
            f"<span style='color:#f87171;font-weight:bold;'>⏳ Cooldown</span>"
            f"<span style='color:#94a3b8;margin-left:12px;'>available after {cd_until[:10] if cd_until else '?'}</span>"
            f"</div>"
        )
        disabled = "disabled"
    else:
        status_html = (
            f"<div style='background:#1a1a2a;border:1px solid #B08D57;padding:10px;margin-bottom:14px;'>"
            f"<span style='color:#B08D57;'>No active policy — configure sliders below and commit.</span>"
            f"<br><small style='color:#94a3b8;'>Active for 3 days, then 7-day cooldown before reuse.</small>"
            f"</div>"
        )
        disabled = ""

    # Slider rows — values are committed_value × decay_factor for visual drift
    slider_rows = ""
    for field, left_label, right_label, affects in _SLIDER_DEFS:
        raw_val = sliders.get(field, 0.0)
        display_val = raw_val * df if active else raw_val
        int_val = int(round(display_val * 100))
        pct_pos = int((display_val + 1) / 2 * 100)
        slider_rows += (
            f"<div style='margin-bottom:14px;'>"
            f"<div style='display:flex;justify-content:space-between;font-size:0.85em;color:#94a3b8;margin-bottom:3px;'>"
            f"<span>← {left_label}</span>"
            f"<span style='color:#fbbf24;' id='lbl_{field}'>{display_val:+.2f}</span>"
            f"<span>{right_label} →</span></div>"
            f"<input type='range' min='-100' max='100' step='1' value='{int_val}' "
            f"id='{field}' {disabled} "
            f"oninput=\"document.getElementById('lbl_{field}').textContent=(this.value/100).toFixed(2).replace(/^(?!-)/, '+');paUpdatePreview();\""
            f" style='width:100%;accent-color:#B08D57;'>"
            f"<small style='color:#555;'>affects: {affects}</small>"
            f"</div>"
        )

    commit_btn = "" if (active or cooldown) else (
        "<button onclick='paCommitImmigration()' "
        "style='margin-top:12px;padding:8px 20px;cursor:pointer;background:#8B4513;"
        "color:#F5F5DC;border:1px solid #B08D57;font-size:1em;'>"
        "⚓ Commit Policy (3-day lock)</button>"
    )

    # Radar SVG placeholder — JS will draw it
    radar_html = (
        "<div id='imm-radar' style='margin-top:16px;text-align:center;min-height:200px;'>"
        "<button onclick='paPreviewScore()' "
        "style='padding:6px 14px;cursor:pointer;background:#1a2533;color:#B08D57;"
        "border:1px solid #B08D57;'>▶ Preview Score</button>"
        "<div id='imm-radar-svg' style='margin-top:10px;'></div>"
        "</div>"
    )

    coeffs_json = _json.dumps(_COEFFS_JS)
    return f"""
<div style="border:1px solid #2D1810;padding:16px;">
  {status_html}
  {slider_rows}
  {commit_btn}
  {radar_html}
  <script>
  const _IMM_COEFFS = {coeffs_json};
  const _IMM_FIELDS = {_json.dumps([d[0] for d in _SLIDER_DEFS])};
  const _IMM_DIM_NAMES = ['Retail Demand','Customer Loyalty','Production Output','Input Efficiency','Land Yield'];
  const _INTENSITY = 0.046;

  function _immSliderValues() {{
    const vals = {{}};
    for(const f of _IMM_FIELDS) {{
      const el = document.getElementById(f);
      vals[f] = el ? parseFloat(el.value)/100 : 0;
    }}
    return vals;
  }}

  function _computeImmScore(vals, decayFactor=1.0) {{
    const totals=[0,0,0,0,0], counts=[0,0,0,0,0];
    for(const [field, coeffs] of Object.entries(_IMM_COEFFS)) {{
      const v = (vals[field]||0) * decayFactor;
      for(let i=0;i<5;i++) {{ if(coeffs[i]!==0) {{ totals[i]+=v*coeffs[i]; counts[i]++; }} }}
    }}
    return totals.map((t,i)=>counts[i]?1+(t/counts[i])*_INTENSITY:1.0);
  }}

  function paUpdatePreview() {{
    const svg = document.getElementById('imm-radar-svg');
    if(svg && svg.children.length > 0) paPreviewScore();
  }}

  function paPreviewScore() {{
    const vals = _immSliderValues();
    const scores = _computeImmScore(vals);
    // Invert elasticity and input_cost for display (lower = better for player)
    const display = [scores[0], 2-scores[1], scores[2], 2-scores[3], scores[4]];
    _drawRadar(display);
  }}

  function _drawRadar(scores) {{
    const cx=160, cy=160, R=110, n=5;
    const neutral=1.0, minV=0.9, maxV=1.1;
    function pt(i,r){{
      const a=(2*Math.PI*i/n)-Math.PI/2;
      return [cx+r*Math.cos(a), cy+r*Math.sin(a)];
    }}
    function scoreToR(s){{
      const norm=(s-minV)/(maxV-minV);
      return 30+Math.max(0,Math.min(1,norm))*R;
    }}
    const neutralR=scoreToR(neutral);
    // Background polygon grid
    let grid='';
    for(let ring=0;ring<=4;ring++){{
      const rr=30+ring*(R/4);
      const pts=Array.from({{length:n}},(_,i)=>pt(i,rr).join(',')).join(' ');
      grid+=`<polygon points="${{pts}}" fill="none" stroke="#2D1810" stroke-width="1"/>`;
    }}
    // Neutral baseline
    const npts=Array.from({{length:n}},(_,i)=>pt(i,neutralR).join(',')).join(' ');
    grid+=`<polygon points="${{npts}}" fill="none" stroke="#555" stroke-width="1" stroke-dasharray="4"/>`;
    // Axes
    let axes='',labels='';
    for(let i=0;i<n;i++){{
      const [x2,y2]=pt(i,R+18);
      const [lx,ly]=pt(i,R+32);
      axes+=`<line x1="${{cx}}" y1="${{cy}}" x2="${{x2}}" y2="${{y2}}" stroke="#444" stroke-width="1"/>`;
      labels+=`<text x="${{lx}}" y="${{ly}}" fill="#94a3b8" font-size="10" text-anchor="middle"
        dominant-baseline="middle">${{_IMM_DIM_NAMES[i]}}</text>`;
    }}
    // Score polygon
    const spts=scores.map((s,i)=>pt(i,scoreToR(s)).join(',')).join(' ');
    const poly=`<polygon points="${{spts}}" fill="rgba(176,141,87,0.25)" stroke="#B08D57" stroke-width="2"/>`;
    // Score dots
    let dots='';
    scores.forEach((s,i)=>{{
      const [x,y]=pt(i,scoreToR(s));
      const color=s>=1?'#4ade80':'#f87171';
      dots+=`<circle cx="${{x}}" cy="${{y}}" r="4" fill="${{color}}"/>`;
    }});
    document.getElementById('imm-radar-svg').innerHTML=
      `<svg width="320" height="320" viewBox="0 0 320 320">${{grid}}${{axes}}${{labels}}${{poly}}${{dots}}</svg>`;
  }}

  async function paCommitImmigration() {{
    const vals = _immSliderValues();
    const body = {{}};
    for(const f of _IMM_FIELDS) body[f] = vals[f];
    const r = await fetch('/api/port-authority/immigration/commit', {{
      method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify(body)
    }});
    const j = await r.json();
    _show(j.message || j.error || '');
    if(j.ok) setTimeout(()=>location.reload(), 800);
  }}
  </script>
</div>"""


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
            get_port_authority, ALL_PA_ITEMS, MAINTENANCE_DAILY,
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
            <li><b>Branch Warfare</b> — raise Navy, Army, Air Force and Intelligence Branches
              in Port Authority command, then fight deterministic dice battles to
              <em>loot</em> rivals during Procurement Events, <em>blockade</em> their commerce,
              or <em>go dark</em> to hide from attackers.</li>
          </ul>
          <p style="color:#94a3b8;">Units destroyed in battle are gone for good.
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
    from port_authority import get_immigration_status
    imm_status = get_immigration_status(player.id)
    inv = pa["inventory"]
    daily = pa["daily_maintenance_usd"]

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

    # Branch Warfare panels (force composition, campaigns, blockades, espionage, history)
    try:
        from military_ux import build_warfare_panels
        warfare_html = build_warfare_panels(player.id, fmt_usd)
    except Exception as _e:
        warfare_html = f"<p style='color:#f87171;'>Warfare panel error: {_e}</p>"

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
        {mil_bonus_note}
      </p>

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
      <h2 style="color:#B08D57;margin-top:28px;border-top:1px solid #2D1810;padding-top:16px;">
        🌍 Immigration Policy
      </h2>
      {_build_immigration_panel(imm_status)}

      <!-- ── Port Authority Command (depot) ─────────────────────────── -->
      <h3 style="color:#B08D57;margin-top:22px;">🛡️ Port Authority Command</h3>
      <p style="color:#94a3b8;margin:0 0 8px;font-size:0.9em;">
        Units under command form your Branches and incur daily upkeep. Withdraw any you
        aren't fielding to cut costs.
      </p>
      <table style="width:100%;border-collapse:collapse;border:1px solid #2D1810;">{inv_rows}</table>

      <h3 style="color:#B08D57;margin-top:18px;">Move Units into Command</h3>
      <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
        <select id="dep-item" style="padding:6px;flex:1;min-width:220px;">{opts}</select>
        <input id="dep-qty" type="number" min="1" value="1" style="padding:6px;width:90px;">
        <button onclick="paMove('deposit', document.getElementById('dep-item').value)" style="padding:6px 14px;cursor:pointer;">Deposit</button>
      </div>

      <!-- ── Branch Warfare ─────────────────────────────────────────── -->
      {warfare_html}

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
    </script>
    """
    return HTMLResponse(_shell("Port Authority", body, 0.0, player.id))
