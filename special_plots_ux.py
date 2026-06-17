"""
special_plots_ux.py

UI for the Subscriber Special Plots system (Precious Metal Mints).

Routes:
  GET  /special-plots               — dashboard
  GET  /special-plots/create        — creation wizard
  POST /api/special-plots/create    — sacrifice plots → create special plot
  GET  /special-plots/<id>/build    — build-a-mint form
  POST /api/special-plots/<id>/build — place mint business on special plot
"""

from typing import Optional, List
from fastapi import APIRouter, Cookie, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse

router = APIRouter()


def _require_auth(session_token):
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
        return f"<!DOCTYPE html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><title>{title}</title></head><body>{body}{loader}</body></html>"


# ── Coin currency display helpers ────────────────────────────────────────────

_COIN_INFO = {
    "AU24":   {"name": "Gold (24-karat)",       "alloy": "Pure gold 99.9%",                      "metal": "gold",     "emoji": "🥇"},
    "AU22":   {"name": "Gold (22-karat)",        "alloy": "91.7% gold + 8.3% copper",             "metal": "gold",     "emoji": "🥇"},
    "AG999":  {"name": "Silver (999-fine)",      "alloy": "Pure silver 99.9%",                    "metal": "silver",   "emoji": "🥈"},
    "AG925":  {"name": "Silver (925 Sterling)",  "alloy": "92.5% silver + 7.5% copper",           "metal": "silver",   "emoji": "🥈"},
    "PT9995": {"name": "Platinum (9995-fine)",   "alloy": "Pure platinum 99.95%",                 "metal": "platinum", "emoji": "🔩"},
    "PT950":  {"name": "Platinum (950)",         "alloy": "95% platinum + 5% copper",             "metal": "platinum", "emoji": "🔩"},
}

_MINT_TO_COIN = {
    "mint_au24":   "AU24",
    "mint_au22":   "AU22",
    "mint_ag999":  "AG999",
    "mint_ag925":  "AG925",
    "mint_pt9995": "PT9995",
    "mint_pt950":  "PT950",
}


# ── Dashboard ────────────────────────────────────────────────────────────────

@router.get("/special-plots", response_class=HTMLResponse)
def special_plots_dashboard(
    session_token: Optional[str] = Cookie(None),
    msg: str = "",
    err: str = "",
):
    player = _require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player

    from reserve_banks import get_player_display_currency, fmt_usd
    from skin_utils import is_pro
    disp = get_player_display_currency(player.id)

    try:
        from special_plots import (
            get_player_special_plots,
            get_plots_required,
            get_next_sacrifice_cost,
            get_player_sacrifice_stats,
            get_mint_business_types,
            SPECIAL_PLOT_TYPES,
        )
        from land import get_player_land

        special_plots = get_player_special_plots(player.id)
        land_plots = get_player_land(player.id)
        stats = get_player_sacrifice_stats(player.id)
        plots_req = get_plots_required(player.id)
        sac_cost = get_next_sacrifice_cost(player.id)
        is_sub = is_pro(player)

        banner = ""
        if msg:
            banner = f'<div style="padding:12px 16px;background:#052e16;border:1px solid #16a34a;color:#4ade80;margin:8px 0;border-radius:4px;">{msg}</div>'
        elif err:
            banner = f'<div style="padding:12px 16px;background:#1a0505;border:1px solid #dc2626;color:#f87171;margin:8px 0;border-radius:4px;">{err}</div>'

        sub_badge = (
            '<span style="background:#7c3aed;color:#fff;padding:2px 8px;border-radius:10px;font-size:0.75rem;margin-left:6px;">✨ Pro</span>'
            if is_sub else
            '<span style="background:#374151;color:#9ca3af;padding:2px 8px;border-radius:10px;font-size:0.75rem;margin-left:6px;">🔒 Requires Pro</span>'
        )

        html = f"""
        <a href="/land" style="color:#38bdf8;font-size:0.85rem;">← Land Portfolio</a>
        <h1 style="margin:12px 0;">🏛️ Institutions{sub_badge}</h1>
        {banner}

        <div class="card" style="background:linear-gradient(135deg,#1e1b4b 0%,#0f172a 100%);border-left:4px solid #7c3aed;">
          <h2 style="margin-top:0;color:#a78bfa;">What are Institutions?</h2>
          <p style="color:#94a3b8;font-size:0.9rem;margin:0 0 8px;">
            Institutions are subscriber-exclusive mega-facilities created by sacrificing
            regular land plots using the Fibonacci progression (5, 8, 13, 21…).
            Unlike district merges, sacrificed plots <strong>do not need to be occupied</strong>.
          </p>
          <p style="color:#94a3b8;font-size:0.9rem;margin:0;">
            Available types: <strong style="color:#e2e8f0;">Precious Metal Mint</strong> —
            converts gold, silver, or platinum into real in-game coinage backed by live
            commodity prices; and <strong style="color:#e2e8f0;">Port Authority</strong> —
            a military command where you deploy Fleet and Army forces on global missions.
          </p>
        </div>

        <div class="card" style="background:#0f172a;border-left:4px solid #7c3aed;">
          <h2 style="margin-top:0;color:#a78bfa;">📊 Your Status</h2>
          <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px;margin-top:12px;">
            <div>
              <div style="color:#64748b;font-size:0.75rem;">INSTITUTIONS OWNED</div>
              <div style="font-size:2rem;font-weight:bold;color:#7c3aed;">{len(special_plots)}</div>
            </div>
            <div>
              <div style="color:#64748b;font-size:0.75rem;">SACRIFICES COMPLETED</div>
              <div style="font-size:2rem;font-weight:bold;color:#a78bfa;">{stats.total_sacrifices_completed}</div>
            </div>
            <div>
              <div style="color:#64748b;font-size:0.75rem;">PLOTS REQUIRED (NEXT)</div>
              <div style="font-size:2rem;font-weight:bold;color:#38bdf8;">{plots_req}</div>
              <div style="color:#64748b;font-size:0.7rem;">Empty plots OK</div>
            </div>
            <div>
              <div style="color:#64748b;font-size:0.75rem;">SACRIFICE COST (NEXT)</div>
              <div style="font-size:1.8rem;font-weight:bold;color:#f59e0b;">{fmt_usd(sac_cost, disp, precision=0)}</div>
            </div>
            <div>
              <div style="color:#64748b;font-size:0.75rem;">YOUR LAND PLOTS</div>
              <div style="font-size:2rem;font-weight:bold;color:{"#22c55e" if len(land_plots) >= plots_req else "#ef4444"};">{len(land_plots)}</div>
              <div style="color:#64748b;font-size:0.7rem;">{"✓ Enough" if len(land_plots) >= plots_req else "⚠ Need more"}</div>
            </div>
          </div>
          <div style="margin-top:16px;">
            {"" if not is_sub else f'<a href="/special-plots/create" class="btn-blue" style="display:inline-block;padding:10px 20px;background:#7c3aed;color:#fff;border-radius:4px;text-decoration:none;font-weight:bold;">🏛️ Create Institution</a>'}
            {"" if is_sub else '<span style="color:#64748b;font-size:0.85rem;">Subscribe to Wadsworth Pro to create institutions.</span>'}
          </div>
        </div>
        """

        # Your institutions — each card opens that institution's own dashboard.
        # Only the owner's institutions are ever listed here.
        if special_plots:
            html += '<h2 style="color:#a78bfa;margin-top:32px;">🏛️ Your Institutions</h2>'
            for sp in special_plots:
                cfg = SPECIAL_PLOT_TYPES.get(sp.special_type, {})
                plot_name = cfg.get("name", sp.special_type.title())
                status = "OCCUPIED" if sp.occupied_by_business_id else "VACANT"
                status_color = "#22c55e" if sp.occupied_by_business_id else "#64748b"
                html += f'''
                <a href="/special-plots/{sp.id}" style="text-decoration:none;color:inherit;display:block;">
                <div class="card" style="border-left:4px solid {status_color};cursor:pointer;">
                  <div style="display:flex;justify-content:space-between;align-items:start;flex-wrap:wrap;gap:12px;">
                    <div>
                      <h3 style="margin:0;color:#a78bfa;">{plot_name}
                        <span style="background:{status_color};color:#020617;font-size:0.7rem;padding:2px 6px;border-radius:3px;margin-left:6px;">{status}</span>
                      </h3>
                      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px;margin-top:10px;">
                        <div><div style="color:#64748b;font-size:0.7rem;">SIZE</div>
                          <div style="color:#e5e7eb;font-size:0.85rem;">{sp.size:.1f} units</div></div>
                        <div><div style="color:#64748b;font-size:0.7rem;">PLOTS SACRIFICED</div>
                          <div style="color:#e5e7eb;font-size:0.85rem;">{sp.plots_merged}</div></div>
                        <div><div style="color:#64748b;font-size:0.7rem;">MONTHLY TAX</div>
                          <div style="color:#f59e0b;font-size:0.85rem;">{fmt_usd(sp.monthly_tax, disp, precision=0)}</div></div>
                      </div>
                    </div>
                    <div style="align-self:center;">
                      <span style="display:inline-block;padding:8px 16px;background:#7c3aed;color:#fff;border-radius:4px;font-size:0.9rem;">Open →</span>
                    </div>
                  </div>
                </div></a>'''
        else:
            html += '<div class="card" style="background:#0f172a;text-align:center;padding:40px;color:#64748b;"><p style="margin:0;">No institutions yet. Create your first by sacrificing land.</p></div>'

        return HTMLResponse(_shell("Institutions", html, 0.0, player.id))

    except Exception as e:
        import traceback
        return HTMLResponse(_shell("Institutions", f'<div style="color:#ef4444;">Error: {e}<pre style="font-size:0.75rem;color:#64748b;">{traceback.format_exc()}</pre></div>', 0.0, player.id))


# ── Creation wizard ──────────────────────────────────────────────────────────

@router.get("/special-plots/create", response_class=HTMLResponse)
def special_plots_create_page(session_token: Optional[str] = Cookie(None)):
    player = _require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player

    from reserve_banks import get_player_display_currency, fmt_usd
    from skin_utils import is_pro
    disp = get_player_display_currency(player.id)

    if not is_pro(player):
        return RedirectResponse(url="/special-plots?err=Pro+subscription+required", status_code=303)

    from special_plots import (
        get_plots_required, get_next_sacrifice_cost, SPECIAL_PLOT_TYPES
    )
    from land import get_player_land

    plots_req = get_plots_required(player.id)
    sac_cost = get_next_sacrifice_cost(player.id)
    land_plots = get_player_land(player.id)

    # Group by terrain
    terrain_groups: dict = {}
    for p in land_plots:
        if getattr(p, 'is_tutorial_reward', False):
            continue
        t = p.terrain_type
        terrain_groups.setdefault(t, []).append(p)

    plot_options_html = ""
    for terrain, plist in sorted(terrain_groups.items()):
        plot_options_html += f'<div style="margin-bottom:14px;"><div style="color:#94a3b8;font-size:0.85rem;font-weight:bold;margin-bottom:6px;">{terrain.replace("_"," ").title()} ({len(plist)} available)</div><div style="display:flex;flex-wrap:wrap;gap:6px;">'
        for p in plist:
            occ = "★ occupied" if p.occupied_by_business_id else "empty"
            plot_options_html += f'<label style="cursor:pointer;"><input type="checkbox" name="plot_ids" value="{p.id}" data-terrain="{terrain}" class="sp-plot-cb" onchange="spUpdateSel()" style="margin-right:4px;"><span style="font-size:0.8rem;color:#94a3b8;">Plot #{p.id} {p.size:.1f}u ({occ})</span></label>'
        plot_options_html += "</div></div>"

    type_opts = "".join(
        f'<option value="{k}">{v["name"]}</option>'
        for k, v in SPECIAL_PLOT_TYPES.items()
    )

    html = f"""
    <a href="/special-plots" style="color:#38bdf8;font-size:0.85rem;">← Institutions</a>
    <h1 style="margin:12px 0;">🏛️ Create Institution</h1>

    <div class="card" style="background:#1e1b4b;border-left:4px solid #7c3aed;">
      <h2 style="color:#a78bfa;margin-top:0;">Requirements</h2>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;">
        <div><div style="color:#64748b;font-size:0.75rem;">PLOTS TO SACRIFICE</div>
          <div style="color:#38bdf8;font-size:1.8rem;font-weight:bold;">{plots_req}</div>
          <div style="color:#64748b;font-size:0.7rem;">Any terrain mix · empty OK</div></div>
        <div><div style="color:#64748b;font-size:0.75rem;">SACRIFICE COST</div>
          <div style="color:#f59e0b;font-size:1.8rem;font-weight:bold;">{fmt_usd(sac_cost, disp, precision=0)}</div></div>
        <div><div style="color:#64748b;font-size:0.75rem;">YOUR PLOTS</div>
          <div style="color:{"#22c55e" if len(land_plots) >= plots_req else "#ef4444"};font-size:1.8rem;font-weight:bold;">{len(land_plots)}</div></div>
      </div>
    </div>

    <form action="/api/special-plots/create" method="post">
      <div class="card">
        <h2 style="color:#a78bfa;margin-top:0;">1. Choose Type</h2>
        <select name="special_type" style="background:#1e293b;color:#e2e8f0;border:1px solid #334155;padding:8px 12px;border-radius:4px;width:100%;font-size:0.95rem;">
          {type_opts}
        </select>
      </div>

      <div class="card">
        <h2 style="color:#a78bfa;margin-top:0;">2. Select {plots_req} Plots to Sacrifice</h2>
        <p style="color:#64748b;font-size:0.85rem;margin-top:0;">Plots from different terrains can be mixed freely. Empty plots are allowed.</p>
        {plot_options_html if plot_options_html else '<p style="color:#64748b;">No eligible plots found.</p>'}
      </div>

      <div class="card">
        <p style="color:#f87171;font-size:0.85rem;margin-top:0;">⚠️ Sacrificed plots will be permanently destroyed. Any businesses on them will be removed with no refund.</p>
        <div id="sp-sel-status" style="font-size:0.9rem;margin-bottom:10px;color:#94a3b8;">Selected: <strong>0</strong> / {plots_req}</div>
        <button id="sp-submit" type="submit" disabled style="padding:12px 28px;background:#3f3f46;color:#9ca3af;border:none;border-radius:4px;font-size:1rem;font-weight:bold;cursor:not-allowed;">
          🏛️ Sacrifice Plots & Create Institution
        </button>
      </div>
    </form>
    <script>
      var SP_REQ = {plots_req};
      function spUpdateSel() {{
        var boxes = document.querySelectorAll('.sp-plot-cb:checked');
        var n = boxes.length;
        var status = document.getElementById('sp-sel-status');
        var btn = document.getElementById('sp-submit');
        var ok = (n === SP_REQ);
        var msg = 'Selected: <strong>' + n + '</strong> / ' + SP_REQ;
        if (n > SP_REQ) msg += ' <span style="color:#f87171;">— too many</span>';
        else if (n === SP_REQ) msg += ' <span style="color:#22c55e;">✓ ready</span>';
        status.innerHTML = msg;
        btn.disabled = !ok;
        btn.style.background = ok ? '#7c3aed' : '#3f3f46';
        btn.style.color = ok ? '#fff' : '#9ca3af';
        btn.style.cursor = ok ? 'pointer' : 'not-allowed';
      }}
    </script>
    """
    return HTMLResponse(_shell("Create Institution", html, 0.0, player.id))


@router.post("/api/special-plots/create")
async def api_create_special_plot(
    session_token: Optional[str] = Cookie(None),
    special_type: str = Form(...),
    plot_ids: List[int] = Form(...),
):
    player = _require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player

    from special_plots import create_special_plot
    sp, err = create_special_plot(player.id, special_type, plot_ids)
    if sp:
        return RedirectResponse(
            url=f"/special-plots?msg=Institution+created+successfully",
            status_code=303,
        )
    return RedirectResponse(
        url=f"/special-plots/create?err={err.replace(' ', '+')}",
        status_code=303,
    )


@router.post("/special-plots/{plot_id}/build-port-authority")
async def api_build_port_authority(
    plot_id: int,
    session_token: Optional[str] = Cookie(None),
):
    player = _require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    try:
        from port_authority import build_port_authority
        ok, msg = build_port_authority(player.id, plot_id)
    except Exception as e:
        ok, msg = False, str(e)
    qs = ("msg=" if ok else "err=") + msg.replace(" ", "+")
    return RedirectResponse(url=f"/special-plots/{plot_id}?{qs}", status_code=303)


# ── Per-institution dashboard ────────────────────────────────────────────────

@router.get("/special-plots/{plot_id}", response_class=HTMLResponse)
def institution_dashboard(
    plot_id: int,
    session_token: Optional[str] = Cookie(None),
    msg: str = "",
    err: str = "",
):
    player = _require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player

    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)

    try:
        from special_plots import get_special_plot, SPECIAL_PLOT_TYPES

        sp = get_special_plot(plot_id)
        # Only the owner may view an institution's dashboard.
        if not sp or sp.owner_id != player.id:
            return RedirectResponse(url="/special-plots?err=Institution+not+found", status_code=303)

        cfg = SPECIAL_PLOT_TYPES.get(sp.special_type, {})
        plot_name = cfg.get("name", sp.special_type.title())
        is_mint = sp.special_type == "mint"
        is_pa = sp.special_type == "port_authority"

        banner = ""
        if msg:
            banner = f'<div style="padding:12px 16px;background:#052e16;border:1px solid #16a34a;color:#4ade80;margin:8px 0;border-radius:4px;">{msg}</div>'
        elif err:
            banner = f'<div style="padding:12px 16px;background:#1a0505;border:1px solid #dc2626;color:#f87171;margin:8px 0;border-radius:4px;">{err}</div>'

        status = "OCCUPIED" if sp.occupied_by_business_id else "VACANT"
        status_color = "#22c55e" if sp.occupied_by_business_id else "#64748b"

        html = f"""
        <a href="/special-plots" style="color:#38bdf8;font-size:0.85rem;">← Institutions</a>
        <h1 style="margin:12px 0;">🏛️ {plot_name} #{sp.id}
          <span style="background:{status_color};color:#020617;font-size:0.7rem;padding:2px 8px;border-radius:3px;vertical-align:middle;">{status}</span>
        </h1>
        {banner}

        <div class="card" style="background:#0f172a;border-left:4px solid #7c3aed;">
          <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:14px;">
            <div><div style="color:#64748b;font-size:0.7rem;">TERRAIN</div>
              <div style="color:#e5e7eb;font-size:0.95rem;">{sp.terrain_type.replace("_", " ").title()}</div></div>
            <div><div style="color:#64748b;font-size:0.7rem;">SIZE</div>
              <div style="color:#e5e7eb;font-size:0.95rem;">{sp.size:.1f} units</div></div>
            <div><div style="color:#64748b;font-size:0.7rem;">PLOTS SACRIFICED</div>
              <div style="color:#e5e7eb;font-size:0.95rem;">{sp.plots_merged}</div></div>
            <div><div style="color:#64748b;font-size:0.7rem;">MONTHLY TAX</div>
              <div style="color:#f59e0b;font-size:0.95rem;">{fmt_usd(sp.monthly_tax, disp, precision=0)}</div></div>
          </div>
        </div>
        """

        if not sp.occupied_by_business_id:
            if is_pa:
                html += f'''
                <div class="card" style="text-align:center;padding:32px;">
                  <p style="color:#94a3b8;margin:0 0 16px;">This Institution is vacant. Establish your Port Authority to deploy Fleet and Army forces.</p>
                  <form action="/special-plots/{sp.id}/build-port-authority" method="post" style="margin:0;">
                    <button type="submit" style="padding:10px 24px;background:#7c3aed;color:#fff;border:none;border-radius:4px;font-weight:bold;cursor:pointer;">⚓ Build Port Authority</button>
                  </form>
                </div>'''
            else:
                html += f'''
                <div class="card" style="text-align:center;padding:32px;">
                  <p style="color:#94a3b8;margin:0 0 16px;">This institution is vacant. Build a facility to put it to work.</p>
                  <a href="/special-plots/{sp.id}/build" style="display:inline-block;padding:10px 24px;background:#7c3aed;color:#fff;border-radius:4px;text-decoration:none;font-weight:bold;">🏗️ Build Mint</a>
                </div>'''
        elif is_mint:
            html += _mint_dashboard_html(sp, player)
        elif is_pa:
            html += '''
            <div class="card" style="text-align:center;padding:32px;">
              <p style="color:#4ade80;margin:0 0 16px;">⚓ Your Port Authority is operational on this Institution.</p>
              <a href="/port-authority" style="display:inline-block;padding:10px 24px;background:#7c3aed;color:#fff;border-radius:4px;text-decoration:none;font-weight:bold;">Open Port Authority Command →</a>
            </div>'''

        return HTMLResponse(_shell(plot_name, html, 0.0, player.id))

    except Exception as e:
        import traceback
        return HTMLResponse(_shell("Institution", f'<div style="color:#ef4444;">Error: {e}<pre style="font-size:0.75rem;color:#64748b;">{traceback.format_exc()}</pre></div>', 0.0, player.id))


def _mint_dashboard_html(sp, owner=None) -> str:
    """Render the full Mint institution dashboard: production status, progress, inputs, quick-buy, and coinage prices."""
    import json as _json
    from reserve_banks import (StateReserveBank, PlayerCurrencyBalance,
                               get_db as rb_get_db, get_player_display_currency, fmt_usd,
                               COIN_SEIGNIORAGE_RATE)
    from business import Business, SessionLocal as biz_session
    from special_plots import get_mint_business_types
    from inventory import InventoryItem, SessionLocal as inv_session
    from skin_utils import is_pro

    disp = get_player_display_currency(sp.owner_id)
    owner_pro = bool(owner) and is_pro(owner)

    # ── Load the Business record + ALL of the owner's mints ──────────────────
    biz = None
    # Sum of total_minted across every mint the owner runs that strikes the SAME
    # coin as this one. The wallet balance is global (one balance per coin code,
    # shared by all sources), so a single mint's total_minted will be LESS than
    # the wallet whenever the owner runs more than one mint of that coin. This
    # aggregate lets the dashboard reconcile the two and prove there's no leak.
    minted_by_coin: dict = {}      # coin_code → summed total_minted across owner's mints
    mint_count_by_coin: dict = {}  # coin_code → how many mints strike it
    try:
        bdb = biz_session()
        biz = bdb.query(Business).filter(Business.id == sp.occupied_by_business_id).first()
        for ob in bdb.query(Business).filter(Business.owner_id == sp.owner_id).all():
            _cc = _MINT_TO_COIN.get(ob.business_type, "")
            if _cc:
                minted_by_coin[_cc] = minted_by_coin.get(_cc, 0.0) + (ob.total_minted or 0.0)
                mint_count_by_coin[_cc] = mint_count_by_coin.get(_cc, 0) + 1
        bdb.close()
    except Exception:
        pass
    if not biz:
        return '<div class="card" style="color:#f87171;">Error loading mint business data.</div>'

    minted_code = _MINT_TO_COIN.get(biz.business_type, "")
    mint_cfg    = get_mint_business_types().get(biz.business_type, {})
    biz_name    = mint_cfg.get("name", biz.business_type.replace("_", " ").title())
    cycles_total = mint_cfg.get("cycles_to_complete", 1)
    base_wage    = mint_cfg.get("base_wage_cost", 0.0)
    progress_pct = min(100.0, biz.progress_ticks / cycles_total * 100) if cycles_total > 0 else 0.0

    # ── Load player inventory ───────────────────────────────────────────────
    inv: dict = {}
    try:
        idb = inv_session()
        for ii in idb.query(InventoryItem).filter(InventoryItem.player_id == sp.owner_id).all():
            inv[ii.item_type] = ii.quantity
        idb.close()
    except Exception:
        pass

    # ── Load ALL coinage balances (prices come from the live metal peg) ─────
    # Current holdings of the struck coin (the player's live coinage balance).
    holdings = 0.0
    all_coin_balances: dict = {}   # code → balance for every non-zero coin the player holds
    try:
        rb_db = rb_get_db()
        # Load ALL coinage balances so the dashboard can show which silver/gold/platinum
        # coins the player owns — prevents confusion when they have both AG999 and AG925.
        from reserve_banks import COIN_CURRENCY_CODES
        for cb in rb_db.query(PlayerCurrencyBalance).filter(
            PlayerCurrencyBalance.player_id == sp.owner_id,
            PlayerCurrencyBalance.currency_code.in_(list(COIN_CURRENCY_CODES)),
            PlayerCurrencyBalance.balance != 0.0,
        ).all():
            all_coin_balances[cb.currency_code] = cb.balance
        if minted_code:
            holdings = all_coin_balances.get(minted_code, 0.0)
        rb_db.close()
    except Exception:
        pass

    total_minted = getattr(biz, "total_minted", 0.0) or 0.0

    # Status is subscription-driven: a Mint is permanent but goes dormant when the
    # owner's Wadsworth Pro subscription lapses (and reactivates on resubscribe).
    if not owner_pro:
        status_label = "DORMANT"
        status_color = "#ef4444"
    elif biz.is_active:
        status_label = "ACTIVE"
        status_color = "#22c55e"
    else:
        status_label = "PAUSED"
        status_color = "#f59e0b"
    toggle_lbl   = "Pause" if biz.is_active else "Resume"
    toggle_cls   = "btn-sm-orange" if biz.is_active else "btn-sm-green"
    paused_line_idxs = set(_json.loads(biz.paused_lines or "[]"))

    # ── Production lines with input check + quick-buy ───────────────────────
    # NOTE: identical markup + behaviour to the /businesses page Quick Buy panel
    # (uses the same qb-* classes and the shared qbSchedule/qbSubmit/qbToggle JS).
    def _qb_panel_html(item_type: str, panel_id: str, default_qty: int) -> str:
        item_disp = item_type.replace("_", " ").title()
        return (
            f'<div class="qb-panel" id="{panel_id}" data-item="{item_type}">'
            f'<div style="font-size:0.72rem;color:#64748b;margin-bottom:8px;">Quick Buy: '
            f'<b style="color:#e2e8f0;">{item_disp}</b></div>'
            f'<div style="display:flex;gap:8px;flex-wrap:wrap;align-items:flex-end;">'
            f'<div><div style="font-size:0.65rem;color:#64748b;margin-bottom:2px;">Quantity</div>'
            f'<input type="number" class="qb-input qb-qty" value="{default_qty}" min="1" step="1"'
            f' oninput="qbSchedule(this)"></div>'
            f'<div><div style="font-size:0.65rem;color:#64748b;margin-bottom:2px;">Cap price ({disp["code"]})</div>'
            f'<input type="number" class="qb-input qb-cap" min="0.000001" step="any" placeholder="auto"'
            f' oninput="qbSchedule(this)"></div></div>'
            f'<div class="qb-preview" style="margin-top:8px;min-height:30px;"></div>'
            f'<form method="post" action="/api/market/quick-buy/execute" style="margin-top:8px;" onsubmit="return qbSubmit(this)">'
            f'<input type="hidden" name="item_type" value="{item_type}">'
            f'<input type="hidden" name="quantity" value="{default_qty}">'
            f'<input type="hidden" name="cap_price" value="">'
            f'<div style="display:flex;gap:6px;">'
            f'<button type="submit" class="btn-sm btn-sm-blue" style="font-size:0.7rem;">Confirm Buy</button>'
            f'<button type="button" class="btn-sm" style="background:#1e293b;color:#94a3b8;font-size:0.7rem;"'
            f' onclick="document.getElementById(\'{panel_id}\').style.display=\'none\'">Cancel</button>'
            f'</div></form></div>'
        )

    lines_html = ""
    for li, line in enumerate(mint_cfg.get("production_lines", [])):
        if not isinstance(line, dict):
            continue
        inp_parts = [f"{req['quantity']:,}× {req['item'].replace('_',' ').title()}" for req in line.get("inputs", [])]
        inp_str   = " + ".join(inp_parts) if inp_parts else "No inputs"
        out_str   = f"{line.get('output_qty',1):,}× {line.get('output_item','?').replace('_',' ').title()}"
        lp        = li in paused_line_idxs

        missing_items = []
        for req in line.get("inputs", []):
            have = inv.get(req["item"], 0)
            need = req["quantity"]
            if have < need:
                missing_items.append((req["item"], have, need))

        if not missing_items:
            dot = '<span style="color:#22c55e;font-size:0.85rem;flex-shrink:0;" title="All inputs available">●</span>'
        else:
            tip = "Missing — " + " | ".join(f"{i.replace('_',' ').title()}: {h:,.0f}/{n:,}" for i,h,n in missing_items)
            dot = f'<span style="color:#ef4444;font-size:0.85rem;flex-shrink:0;" title="{tip}">●</span>'

        missing_html = ""
        qb_panels    = ""
        for item, have, need in missing_items:
            safe  = item.replace("'","").replace('"',"")
            pid   = f"mqbp-{biz.id}-{li}-{safe}"
            dqty  = max(1, int(need * 5 - have))
            iname = item.replace("_"," ").title()
            missing_html += (
                f'<span style="font-size:0.68rem;color:#f59e0b;">{iname} {have:,.0f}/{need:,}</span>'
                f'<button type="button" class="btn-sm btn-sm-blue" style="font-size:0.62rem;padding:2px 5px;"'
                f' onclick="qbToggle(\'{pid}\')">Buy</button> '
            )
            qb_panels += _qb_panel_html(item, pid, dqty)

        missing_row = (
            f'<div style="display:flex;flex-wrap:wrap;gap:5px;align-items:center;'
            f'padding:3px 8px 3px;background:#0a0e1a;border-radius:0 0 3px 3px;'
            f'margin-top:-4px;margin-bottom:4px;">'
            f'<span style="font-size:0.62rem;color:#475569;">Missing:</span> {missing_html}</div>'
        ) if missing_html else ""

        lines_html += f'''<div style="display:flex;align-items:center;gap:8px;padding:7px 10px;
            background:#111827;border-radius:4px;margin-bottom:4px;flex-wrap:wrap;">
            {dot}
            <span style="font-size:0.78rem;color:#94a3b8;flex:1;">{inp_str} → <strong style="color:#fbbf24;">{out_str}</strong></span>
            <form action="/api/business/toggle-line" method="post" style="flex-shrink:0;display:inline;">
                <input type="hidden" name="business_id" value="{biz.id}">
                <input type="hidden" name="line_index" value="{li}">
                <button type="submit" class="btn-sm {'btn-sm-green' if lp else 'btn-sm-orange'}">{'Resume' if lp else 'Pause'}</button>
            </form>
        </div>{missing_row}{qb_panels}'''

    # ── Government redemption queue for this coin ───────────────────────────
    iou_card = ""
    if minted_code:
        try:
            from reserve_banks import (get_coin_iou_queue, get_gov_coin_reserve,
                                       get_player_coin_iou_notes)
            if True:
                queue       = get_coin_iou_queue(minted_code)
                on_hand     = get_gov_coin_reserve(minted_code)   # held by the federal treasury
                total_owed  = sum(n.coin_amount_owed - n.filled_amount for n in queue)
                n_notes     = len(queue)
                # Player's own unfulfilled note for this coin (if any)
                my_notes = [n for n in get_player_coin_iou_notes(sp.owner_id)
                            if n.currency_code == minted_code and not n.is_fulfilled]
                my_note_html = ""
                for n in my_notes:
                    remaining = n.coin_amount_owed - n.filled_amount
                    pct = n.filled_amount / n.coin_amount_owed * 100 if n.coin_amount_owed > 0 else 0
                    my_note_html += f'''
                    <div style="background:#0a1a0a;border:1px solid #16a34a;border-radius:4px;padding:8px;margin-top:8px;">
                      <div style="font-size:0.72rem;color:#4ade80;font-weight:bold;">Your IOU</div>
                      <div style="font-size:0.82rem;color:#e2e8f0;margin-top:2px;">
                        {n.filled_amount:,.4f} / {n.coin_amount_owed:,.4f} {minted_code} filled
                        ({remaining:,.4f} remaining)
                      </div>
                      <div style="background:#1e293b;border-radius:3px;height:6px;margin-top:4px;overflow:hidden;">
                        <div style="background:#22c55e;height:100%;width:{min(pct,100):.1f}%;"></div>
                      </div>
                    </div>'''
                queue_color = "#22c55e" if total_owed == 0 else "#f59e0b"
                iou_card = f'''
                <div class="card" style="background:#0f172a;border-left:4px solid #f59e0b;">
                  <div style="font-size:0.72rem;color:#64748b;text-transform:uppercase;letter-spacing:.05em;margin-bottom:8px;">
                    {minted_code} · Government Redemption Queue
                  </div>
                  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;">
                    <div style="background:#111827;border-radius:6px;padding:8px;">
                      <div style="color:#64748b;font-size:0.68rem;">TREASURY ON HAND</div>
                      <div style="color:#fbbf24;font-weight:bold;">{on_hand:,.4f}</div>
                    </div>
                    <div style="background:#111827;border-radius:6px;padding:8px;">
                      <div style="color:#64748b;font-size:0.68rem;">OUTSTANDING IOUs</div>
                      <div style="color:{queue_color};font-weight:bold;">{total_owed:,.4f}</div>
                      <div style="color:#475569;font-size:0.65rem;">{n_notes} note{"s" if n_notes != 1 else ""} in queue</div>
                    </div>
                  </div>
                  <div style="color:#64748b;font-size:0.72rem;margin-top:8px;">
                    Each mint run skims {int(COIN_SEIGNIORAGE_RATE*100)}% seigniorage to the federal
                    treasury, which fills this queue. Demurrage on stored coinage also flows here.
                  </div>
                  {my_note_html}
                </div>'''
        except Exception:
            pass

    # ── Live coin price for the struck coin ─────────────────────────────────
    coin_card = ""
    if minted_code:
        info = _COIN_INFO.get(minted_code, {})
        from reserve_banks import get_live_coin_usd_per_unit
        rate = get_live_coin_usd_per_unit(minted_code)   # live metal peg (no bank row)
        rate_str = fmt_usd(rate, disp)
        coin_card = f'''<div class="card" style="background:linear-gradient(135deg,#3a2e0a 0%,#0f172a 100%);border-left:4px solid #f59e0b;">
          <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
            <span style="font-size:2rem;">{info.get("emoji","💰")}</span>
            <div>
              <div style="color:#fbbf24;font-weight:bold;font-size:1.1rem;">Strikes {minted_code} — {info.get("name","")}</div>
              <div style="color:#94a3b8;font-size:0.82rem;">{info.get("alloy","")}</div>
            </div>
            <div style="margin-left:auto;text-align:right;">
              <div style="color:#fbbf24;font-weight:bold;font-size:1.5rem;">{rate_str}</div>
              <div style="color:#64748b;font-size:0.72rem;">per coin · live metal peg</div>
            </div>
          </div>
        </div>'''

    # ── Full coinage price board ─────────────────────────────────────────────
    from reserve_banks import get_live_coin_usd_per_unit as _coin_rate
    price_board = '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:10px;">'
    for code, info in _COIN_INFO.items():
        rate = _coin_rate(code)               # live metal peg (no bank row)
        rate_str = fmt_usd(rate, disp)
        highlight = ';border:2px solid #f59e0b' if code == minted_code else ''
        price_board += f'''<div style="background:#1e293b;border-radius:6px;padding:10px{highlight};">
          <div style="font-size:1.2rem;">{info["emoji"]}</div>
          <div style="color:#e2e8f0;font-weight:bold;font-size:0.9rem;">{code}</div>
          <div style="color:#94a3b8;font-size:0.72rem;">{info["name"]}</div>
          <div style="color:#fbbf24;font-weight:bold;margin-top:4px;">{rate_str}</div>
          <div style="color:#475569;font-size:0.65rem;">{info["alloy"]}</div>
        </div>'''
    price_board += '</div>'

    wage_str = fmt_usd(base_wage, disp)

    # Coinage counts (not USD — display in coin units alongside the code).
    minted_str   = f"{total_minted:,.4f} {minted_code}" if minted_code else f"{total_minted:,.4f}"
    holdings_str = f"{holdings:,.4f} {minted_code}" if minted_code else f"{holdings:,.4f}"

    # Build "all coinage balances" panel so AG999 vs AG925 is never confused.
    if all_coin_balances:
        _coin_chips = ""
        for _c, _v in sorted(all_coin_balances.items()):
            _is_mine = (_c == minted_code)
            _bg    = "#0a1f0a" if _is_mine else "#111827"
            _br    = "#166534" if _is_mine else "#334155"
            _col   = "#4ade80" if _is_mine else "#94a3b8"
            _vcol  = "#4ade80" if _is_mine else "#e2e8f0"
            _tag   = ' <span style="color:#166534;font-size:0.65rem;">← this Mint</span>' if _is_mine else ""
            _coin_chips += (
                f'<span style="display:inline-block;background:{_bg};border:1px solid {_br};'
                f'border-radius:4px;padding:4px 8px;font-size:0.82rem;margin:2px 4px 2px 0;">'
                f'<strong style="color:{_col};">{_c}</strong> '
                f'<span style="color:{_vcol};">{_v:,.4f}</span>{_tag}</span>'
            )
        all_coin_html = (
            '<div style="margin-top:8px;padding:8px 10px;background:#1a1505;'
            'border:1px solid #78350f;border-radius:6px;">'
            '<div style="color:#f59e0b;font-size:0.68rem;text-transform:uppercase;'
            'font-weight:bold;margin-bottom:4px;">🪙 All your coinage balances</div>'
            f'<div style="display:flex;flex-wrap:wrap;">{_coin_chips}</div>'
            '<div style="color:#78350f;font-size:0.62rem;margin-top:4px;">'
            'AG999 = Silver 999-fine · AG925 = Silver 925 Sterling · AU24/22 = Gold · PT9995/950 = Platinum'
            ' — each code is a separate, non-interchangeable currency.</div>'
            '</div>'
        )
    else:
        all_coin_html = ""

    # ── Reconciliation panel: explain why wallet (global) ≠ this mint's total_minted ──
    recon_html = ""
    if minted_code:
        coin_total_minted = minted_by_coin.get(minted_code, 0.0)
        n_mints           = mint_count_by_coin.get(minted_code, 1)
        wallet_bal        = holdings  # global wallet balance for this coin
        # Difference between everything your mints struck (net of seigniorage) and
        # what's in your wallet. Positive → you've spent/traded some away.
        diff = coin_total_minted - wallet_bal
        if n_mints > 1:
            recon_intro = (
                f'You run <strong>{n_mints} {minted_code} mints</strong>. Your wallet shows one '
                f'<strong>combined</strong> {minted_code} balance shared by all of them — that\'s why '
                f'this single mint\'s "Total Minted" ({total_minted:,.4f}) is smaller than your wallet.'
            )
        else:
            recon_intro = (
                f'Your wallet holds one {minted_code} balance. It should equal this mint\'s total '
                f'minted minus anything you\'ve spent or traded.'
            )
        # Flag a genuine leak: wallet exceeds total ever struck across ALL your mints.
        if wallet_bal - coin_total_minted > 0.01:
            leak = wallet_bal - coin_total_minted
            flag = (
                f'<div style="color:#fca5a5;font-size:0.7rem;margin-top:4px;">'
                f'⚠️ Your wallet ({wallet_bal:,.4f}) exceeds the total ever struck by all your '
                f'{minted_code} mints ({coin_total_minted:,.4f}) by {leak:,.4f}. '
                f'If you never received {minted_code} from another player or income conversion, '
                f'please report this — it may indicate a minting accounting bug.</div>'
            )
        else:
            flag = (
                f'<div style="color:#16a34a;font-size:0.7rem;margin-top:4px;">'
                f'✓ Reconciles: all {minted_code} mints struck {coin_total_minted:,.4f} total · '
                f'wallet holds {wallet_bal:,.4f}'
                + (f' · {diff:,.4f} spent/traded away' if diff > 0.01 else '')
                + '</div>'
            )
        recon_html = (
            '<div style="margin-top:8px;padding:8px 10px;background:#0a1525;'
            'border:1px solid #1e3a5f;border-radius:6px;">'
            '<div style="color:#38bdf8;font-size:0.68rem;text-transform:uppercase;'
            'font-weight:bold;margin-bottom:4px;">🔎 Why does my wallet differ from this mint?</div>'
            f'<div style="color:#94a3b8;font-size:0.72rem;line-height:1.5;">{recon_intro}</div>'
            f'{flag}</div>'
        )
    all_coin_html += recon_html

    # Dormant banner — shown only when the subscription has lapsed.
    dormant_banner = ""
    if not owner_pro:
        dormant_banner = '''
        <div class="card" style="background:#1a0505;border-left:4px solid #ef4444;">
          <div style="color:#fca5a5;font-weight:bold;">⚠️ This Mint is dormant</div>
          <div style="color:#f87171;font-size:0.85rem;margin-top:4px;">
            Your Wadsworth Pro subscription has lapsed, so this Mint is not striking coinage.
            The Mint is <strong>permanent</strong> and your coinage holdings are safe — minting resumes
            automatically as soon as you resubscribe.
          </div>
        </div>'''

    html = f'''
    <style>
    .btn-sm{{padding:5px 10px;font-size:0.78rem;border:none;border-radius:3px;cursor:pointer;font-family:inherit;font-weight:600;}}
    .btn-sm-blue{{background:#38bdf8;color:#020617;}} .btn-sm-orange{{background:#f59e0b;color:#020617;}}
    .btn-sm-red{{background:#ef4444;color:#fff;}} .btn-sm-green{{background:#22c55e;color:#020617;}}
    .qb-panel{{display:none;margin:6px 0 0;background:#060c18;border:1px solid #334155;border-radius:4px;padding:10px;}}
    .qb-input{{padding:4px 6px;font-size:0.78rem;background:#0f172a;border:1px solid #334155;color:#e2e8f0;border-radius:3px;width:100px;}}
    </style>

    {coin_card}
    {iou_card}
    {dormant_banner}

    <div class="card" style="background:#0f172a;border-left:4px solid #7c3aed;">
      <div style="display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:10px;">
        <div>
          <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
            <span style="font-weight:bold;font-size:1.05rem;">{biz_name}</span>
            <span class="badge" style="background:{status_color};color:#020617;font-size:0.72rem;padding:2px 8px;">{status_label}</span>
            <span class="badge" style="background:#7c3aed;color:#fff;font-size:0.72rem;padding:2px 8px;">MINT</span>
          </div>
          <div style="font-size:0.75rem;color:#64748b;margin-top:4px;">
            Institution #{sp.id} · Business #{biz.id} · Wage {wage_str}/cycle
          </div>
        </div>
        <div style="display:flex;gap:6px;flex-wrap:wrap;">
          <form action="/api/business/toggle" method="post" style="display:inline;">
            <input type="hidden" name="business_id" value="{biz.id}">
            <button type="submit" class="btn-sm {toggle_cls}">{toggle_lbl}</button>
          </form>
        </div>
      </div>

      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-top:14px;">
        <div style="background:#111827;border-radius:6px;padding:10px;">
          <div style="color:#64748b;font-size:0.68rem;text-transform:uppercase;letter-spacing:.05em;">Total Minted (Lifetime)</div>
          <div style="color:#fbbf24;font-weight:bold;font-size:1.05rem;margin-top:2px;">{minted_str}</div>
          <div style="color:#475569;font-size:0.65rem;">all {minted_code or "coins"} ever struck by this Mint — includes 2% seigniorage paid to the federal government, never decreases</div>
        </div>
        <div style="background:#0a1f0a;border:1px solid #166534;border-radius:6px;padding:10px;">
          <div style="color:#4ade80;font-size:0.68rem;text-transform:uppercase;letter-spacing:.05em;font-weight:bold;">⬆ {minted_code or "Coins"} in Hand (Spendable)</div>
          <div style="color:#4ade80;font-weight:bold;font-size:1.05rem;margin-top:2px;">{holdings_str}</div>
          <div style="color:#16a34a;font-size:0.65rem;">your {minted_code} wallet — same value shown on Forex/Bonds page</div>
        </div>
      </div>
      {all_coin_html}

      <div style="margin-top:14px;">
        <div style="display:flex;justify-content:space-between;font-size:0.75rem;color:#94a3b8;margin-bottom:4px;">
          <span>Minting Progress</span>
          <span>{biz.progress_ticks:,} / {cycles_total:,} ticks ({progress_pct:.1f}%)</span>
        </div>
        <div style="background:#1e293b;border-radius:4px;height:10px;overflow:hidden;">
          <div style="background:#f59e0b;height:100%;width:{min(progress_pct,100):.1f}%;transition:width 0.3s;"></div>
        </div>
      </div>

      <div style="margin-top:16px;">
        <div style="font-size:0.72rem;color:#64748b;margin-bottom:8px;text-transform:uppercase;letter-spacing:.05em;">Production Lines</div>
        {lines_html or '<span style="color:#475569;font-size:0.82rem;">No production lines configured.</span>'}
      </div>
    </div>

    <div class="card" style="background:#0f172a;border-left:4px solid #f59e0b;">
      <h3 style="margin-top:0;color:#fbbf24;">💰 Coinage Live Prices</h3>
      <p style="color:#64748b;font-size:0.8rem;margin-bottom:12px;">
        Metal-pegged exchange rates update each game tick.
        <strong style="color:#fbbf24;">Hard money:</strong> coinage enters circulation only by minting and is
        issued by the federal government (not a bank). Stored coins carry a small demurrage (carry cost) reclaimed
        by the government; coinage never pays positive interest.
      </p>
      {price_board}
    </div>

    <script>
    (function(){{
      var _t = {{}};
      window.qbToggle = function(id) {{
        var p = document.getElementById(id);
        if (!p) return;
        var hidden = p.style.display === 'none' || p.style.display === '';
        document.querySelectorAll('.qb-panel').forEach(function(x){{ x.style.display='none'; }});
        if (hidden) {{ p.style.display='block'; qbFetch(p); }}
      }};
      window.qbSchedule = function(el) {{
        var p = el.closest('.qb-panel'); if (!p) return;
        clearTimeout(_t[p.id]);
        _t[p.id] = setTimeout(function(){{ qbFetch(p); }}, 450);
      }};
      window.qbFetch = function(p) {{
        var item = p.dataset.item;
        var qty  = p.querySelector('.qb-qty').value || '1';
        var cap  = p.querySelector('.qb-cap').value;
        var prev = p.querySelector('.qb-preview');
        prev.innerHTML = '<span style="color:#475569;">Loading…</span>';
        var params = new URLSearchParams({{item_type:item, quantity:qty}});
        if (cap) params.set('cap_price', cap);
        fetch('/api/market/quick-buy/preview?' + params)
          .then(function(r){{ return r.json(); }})
          .then(function(d) {{
            if (d.error) {{ prev.innerHTML='<span style="color:#ef4444;">'+d.error+'</span>'; return; }}
            var capIn = p.querySelector('.qb-cap');
            if (d.suggested_cap_raw != null && !capIn.value) {{
              p.dataset.suggestedCap = d.suggested_cap_raw;
              capIn.placeholder = d.suggested_cap_disp || String(d.suggested_cap_raw);
            }}
            var h = '';
            if (d.fills && d.fills.length) {{
              h += '<div style="color:#64748b;font-size:0.68rem;margin-bottom:2px;">Order book:</div>';
              d.fills.forEach(function(f){{
                h += '<div style="margin-left:8px;color:#94a3b8;font-size:0.7rem;">'+Number(f.qty).toLocaleString()+'× @ '+f.price_disp+'</div>';
              }});
              h += '<div style="margin-top:4px;padding-top:4px;border-top:1px solid #1e293b;font-size:0.72rem;">';
              h += '<span style="color:#22c55e;">'+Number(d.total_filled).toLocaleString()+' filled</span>';
              if (d.avg_price_disp) h += ' @ '+d.avg_price_disp+' avg';
              if (d.immediate_cost_disp) h += ' = <b style="color:#38bdf8;">'+d.immediate_cost_disp+'</b>';
              h += '</div>';
            }}
            if (d.unfilled_qty > 0) {{
              h += '<div style="color:#f59e0b;font-size:0.7rem;margin-top:3px;">'+Number(d.unfilled_qty).toLocaleString()+' unavailable → buy order at cap price</div>';
              if (d.reservation_disp) h += '<div style="color:#64748b;font-size:0.7rem;">Max reservation: '+d.reservation_disp+'</div>';
            }}
            if ((!d.fills || !d.fills.length) && !d.unfilled_qty) h += '<span style="color:#64748b;font-size:0.7rem;">No active sell orders found.</span>';
            if (d.forex_fee_disp) h += '<div style="color:#64748b;font-size:0.7rem;margin-top:2px;">Forex fee: '+d.forex_fee_disp+'</div>';
            prev.innerHTML = h;
          }})
          .catch(function(){{ prev.innerHTML='<span style="color:#ef4444;font-size:0.7rem;">Preview unavailable.</span>'; }});
      }};
      window.qbSubmit = function(form) {{
        var p   = form.closest('.qb-panel');
        var qty = p.querySelector('.qb-qty').value;
        var cap = p.querySelector('.qb-cap').value;
        if (!cap || parseFloat(cap) <= 0) {{
          cap = p.dataset.suggestedCap || '';
          if (!cap || parseFloat(cap) <= 0) {{
            alert('Please enter a cap price before confirming.');
            return false;
          }}
        }}
        var prev = p.querySelector('.qb-preview');
        prev.innerHTML = '<span style="color:#475569;font-size:0.8rem;">Placing order…</span>';
        var data = new FormData(form);
        data.set('quantity', qty);
        data.set('cap_price', cap);
        fetch(form.action, {{method:'POST', body:data}})
          .then(function(r){{ return r.json(); }})
          .then(function(d){{
            if (d.ok) {{
              prev.innerHTML = '<span style="color:#22c55e;font-size:0.8rem;">✓ '+d.message+'</span>';
              setTimeout(function(){{ p.style.display='none'; }}, 2500);
            }} else {{
              prev.innerHTML = '<span style="color:#ef4444;font-size:0.8rem;">'+(d.error||'Order failed.')+'</span>';
            }}
          }})
          .catch(function(){{ prev.innerHTML='<span style="color:#ef4444;font-size:0.8rem;">Request failed.</span>'; }});
        return false;
      }};
    }})();
    </script>
    '''
    return html


# ── Build mint on a special plot ─────────────────────────────────────────────

@router.get("/special-plots/{plot_id}/build", response_class=HTMLResponse)
def special_plot_build_page(
    plot_id: int,
    session_token: Optional[str] = Cookie(None),
    err: str = "",
):
    player = _require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player

    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)

    from special_plots import get_special_plot, get_mint_business_types, SPECIAL_PLOT_TYPES
    sp = get_special_plot(plot_id)
    if not sp or sp.owner_id != player.id:
        return RedirectResponse(url="/special-plots?err=Plot+not+found", status_code=303)

    if sp.occupied_by_business_id:
        return RedirectResponse(url="/special-plots?err=Plot+already+has+a+mint", status_code=303)

    mint_types = get_mint_business_types()
    cfg = SPECIAL_PLOT_TYPES.get(sp.special_type, {})

    # Only show mint types compatible with this plot terrain.
    # Guard the "_comment" key first: its value is a string (no .get) so the
    # startswith check MUST short-circuit before we call v.get(...).
    compatible = {
        k: v for k, v in mint_types.items()
        if not k.startswith("_")
        and isinstance(v, dict)
        and sp.terrain_type in v.get("allowed_terrain", [])
    }

    options_html = ""
    for btype, bcfg in compatible.items():
        coin_code = _MINT_TO_COIN.get(btype, "")
        coin_info = _COIN_INFO.get(coin_code, {})
        startup = bcfg.get("startup_cost", 0)
        cycles = bcfg.get("cycles_to_complete", 720)
        line = bcfg.get("production_lines", [{}])[0]
        inputs = line.get("inputs", [])
        input_str = ", ".join(f'{i["quantity"]} {i["item"]}' for i in inputs)
        options_html += f"""
        <label style="display:block;cursor:pointer;margin-bottom:10px;">
          <input type="radio" name="business_type" value="{btype}" style="margin-right:8px;">
          <strong style="color:#e2e8f0;">{coin_info.get("emoji", "⚗️")} {bcfg["name"]}</strong>
          <span style="color:#7c3aed;margin-left:8px;">{coin_code}</span><br>
          <span style="color:#64748b;font-size:0.8rem;margin-left:20px;">{bcfg["description"]}</span><br>
          <span style="color:#64748b;font-size:0.75rem;margin-left:20px;">
            Cost: <strong style="color:#f59e0b;">{fmt_usd(startup, disp, precision=0)}</strong>
            · Alloy: {coin_info.get("alloy", "")}
            · Inputs per run: {input_str}
            · Cycle: {cycles} ticks
          </span>
        </label>"""

    err_html = f'<div style="color:#f87171;margin-bottom:12px;">{err}</div>' if err else ""

    html = f"""
    <a href="/special-plots" style="color:#38bdf8;font-size:0.85rem;">← Institutions</a>
    <h1 style="margin:12px 0;">🏗️ Build Mint on Institution #{sp.id}</h1>
    {err_html}

    <div class="card" style="background:#1e293b;">
      <div style="color:#64748b;font-size:0.75rem;">PLOT</div>
      <div style="color:#e2e8f0;">Institution #{sp.id} · {sp.terrain_type.replace("_"," ").title()} · {sp.size:.1f} units</div>
    </div>

    <form action="/api/special-plots/{sp.id}/build" method="post">
      <div class="card">
        <h2 style="color:#a78bfa;margin-top:0;">Choose Mint Type</h2>
        {options_html if options_html else '<p style="color:#64748b;">No compatible mint types found.</p>'}
      </div>
      <div class="card">
        <button type="submit" style="padding:12px 28px;background:#7c3aed;color:#fff;border:none;border-radius:4px;font-size:1rem;font-weight:bold;cursor:pointer;">
          ⚗️ Build Mint
        </button>
      </div>
    </form>
    """
    return HTMLResponse(_shell(f"Build Mint — Plot #{sp.id}", html, 0.0, player.id))


@router.post("/api/special-plots/{plot_id}/build")
async def api_build_mint(
    plot_id: int,
    session_token: Optional[str] = Cookie(None),
    business_type: str = Form(...),
):
    player = _require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player

    from special_plots import create_mint_business
    biz, err = create_mint_business(player.id, plot_id, business_type)
    if biz:
        return RedirectResponse(url=f"/special-plots/{plot_id}?msg=Mint+built+successfully", status_code=303)
    return RedirectResponse(
        url=f"/special-plots/{plot_id}/build?err={err.replace(' ', '+')}",
        status_code=303,
    )
