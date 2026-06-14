"""
port_authority_ux.py

HTML frontend for the player-controlled Port Authority military institution.
Reuses the shared `ux.shell` page wrapper so it automatically inherits the
fast-load navigation loader, the player's skin/theme, and standard chrome.
All mutations go through the existing JSON API in port_authority.router.
"""

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


@router.get("/port-authority", response_class=HTMLResponse)
def port_authority_dashboard(session_token: Optional[str] = Cookie(None)):
    player = _require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player

    try:
        from port_authority import (
            get_port_authority, get_missions, ALL_PA_ITEMS,
            FLEET_THRESHOLDS, ARMY_THRESHOLDS, MAINTENANCE_DAILY,
        )
        from inventory import get_player_inventory
        from reserve_banks import fmt_usd
    except Exception as e:
        return HTMLResponse(_shell("Port Authority",
                                   f"<div style='color:#ef4444;'>Module error: {e}</div>",
                                   0.0, player.id))

    pa = get_port_authority(player.id)

    # ── No PA yet — it's an Institution, so route through land sacrifice ──────
    if pa is None:
        from port_authority import get_unbuilt_pa_plot
        ready_plot = get_unbuilt_pa_plot(player.id)

        intro = """
          <p>The Port Authority is a sovereign military <b>Institution</b>. Deposit
          weapons and platforms from your inventory, then deploy <b>Fleet</b> or
          <b>Army</b> forces on global missions — attack rivals for loot, or defend
          your assets.</p>
          <ul style="line-height:1.7;">
            <li>Mission outcomes are a pure 50/50 coin-flip.</li>
            <li>Successful attack → steal up to 5% of the target's balance (cap $10M); a federal loot tax applies.</li>
            <li>Any failure → lose 10% of your Port Authority inventory.</li>
            <li>Daily upkeep is auto-deducted; if you can't pay, a random item is lost.</li>
            <li>As an Institution it also pays a monthly federal tax, like a Mint.</li>
          </ul>
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
              <p style="color:#fbbf24;">A Port Authority is built on an Institution. First sacrifice
              land to create a <b>Port Authority</b> Institution (Wadsworth Pro required), then return here to build.</p>
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
        m_rows = "".join(
            f"<tr><td style='padding:4px 10px;'>{m['force_type'].title()}</td>"
            f"<td style='padding:4px 10px;'>{m['mission_type'].title()}</td>"
            f"<td style='padding:4px 10px;color:{'#4ade80' if m['outcome']=='success' else '#f87171'};'>{(m['outcome'] or '').title()}</td>"
            f"<td style='padding:4px 10px;text-align:right;'>{fmt_usd(m['loot_usd']) if m['loot_usd'] else '—'}</td></tr>"
            for m in missions
        )
    else:
        m_rows = "<tr><td colspan='4' style='padding:10px;color:#94a3b8;'>No missions yet.</td></tr>"

    body = f"""
    <div style="max-width:760px;margin:0 auto;padding:16px;color:#F5F5DC;font-family:Georgia,serif;">
      <h1 style="color:#B08D57;">⚓ {pa['name']}</h1>
      <p style="color:#94a3b8;">Daily upkeep: <b style="color:#fbbf24;">{fmt_usd(daily)}/day</b>
      &nbsp;•&nbsp; Fleet: <b style="color:{'#4ade80' if fleet_ready else '#f87171'};">{'READY' if fleet_ready else 'not ready'}</b>
      &nbsp;•&nbsp; Army: <b style="color:{'#4ade80' if army_ready else '#f87171'};">{'READY' if army_ready else 'not ready'}</b></p>

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

      <h3 style="color:#B08D57;margin-top:18px;">Inventory</h3>
      <table style="width:100%;border-collapse:collapse;border:1px solid #2D1810;">{inv_rows}</table>

      <h3 style="color:#B08D57;margin-top:18px;">Deposit Weapons</h3>
      <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
        <select id="dep-item" style="padding:6px;flex:1;min-width:220px;">{opts}</select>
        <input id="dep-qty" type="number" min="1" value="1" style="padding:6px;width:90px;">
        <button onclick="paMove('deposit', document.getElementById('dep-item').value)" style="padding:6px 14px;cursor:pointer;">Deposit</button>
      </div>

      <h3 style="color:#B08D57;margin-top:18px;">Deploy Mission</h3>
      <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
        <select id="force" style="padding:6px;"><option value="fleet">Fleet</option><option value="army">Army</option></select>
        <select id="mtype" style="padding:6px;"><option value="attack">Attack</option><option value="defend">Defend</option></select>
        <input id="target" type="number" placeholder="Target player ID (attack)" style="padding:6px;width:200px;">
        <button onclick="paDeploy()" style="padding:6px 14px;cursor:pointer;background:#8B4513;color:#F5F5DC;border:1px solid #B08D57;">Deploy</button>
      </div>

      <h3 style="color:#B08D57;margin-top:18px;">Recent Missions</h3>
      <table style="width:100%;border-collapse:collapse;border:1px solid #2D1810;">
        <tr style="color:#94a3b8;"><td style="padding:4px 10px;">Force</td><td style="padding:4px 10px;">Type</td><td style="padding:4px 10px;">Outcome</td><td style="padding:4px 10px;text-align:right;">Loot</td></tr>
        {m_rows}
      </table>

      <div id="pa-msg" style="margin-top:14px;min-height:20px;"></div>
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
    async function paDeploy(){{
      const body = {{force_type:document.getElementById('force').value, mission_type:document.getElementById('mtype').value}};
      const t = document.getElementById('target').value;
      if(t) body.target_player_id = parseInt(t);
      const r = await fetch('/api/port-authority/deploy', {{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(body)}});
      const j = await r.json();
      if(j.error){{ _show(j.error); return; }}
      _show('Mission '+(j.outcome||'')+ (j.loot_usd? ' — looted $'+Math.round(j.loot_usd).toLocaleString():''));
      setTimeout(()=>location.reload(), 1200);
    }}
    </script>
    """
    return HTMLResponse(_shell("Port Authority", body, 0.0, player.id))
