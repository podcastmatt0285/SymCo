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
        from skin_utils import skin_links
        return ux_shell(title, body, balance, player_id)
    except Exception:
        return f"<!DOCTYPE html><html><head><title>{title}</title></head><body>{body}</body></html>"


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
        from reserve_banks import StateReserveBank, get_db as rb_get_db

        special_plots = get_player_special_plots(player.id)
        land_plots = get_player_land(player.id)
        stats = get_player_sacrifice_stats(player.id)
        plots_req = get_plots_required(player.id)
        sac_cost = get_next_sacrifice_cost(player.id)
        is_sub = is_pro(player)

        # Load coin currency prices
        rb_db = rb_get_db()
        coin_banks = {b.currency_code: b for b in rb_db.query(StateReserveBank).filter(
            StateReserveBank.currency_code.in_(list(_COIN_INFO.keys()))
        ).all()}
        rb_db.close()

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
        <h1 style="margin:12px 0;">⚗️ Special Plots{sub_badge}</h1>
        {banner}

        <div class="card" style="background:linear-gradient(135deg,#1e1b4b 0%,#0f172a 100%);border-left:4px solid #7c3aed;">
          <h2 style="margin-top:0;color:#a78bfa;">What are Special Plots?</h2>
          <p style="color:#94a3b8;font-size:0.9rem;margin:0 0 8px;">
            Special Plots are subscriber-exclusive mega-facilities created by sacrificing
            regular land plots using the Fibonacci progression (5, 8, 13, 21…).
            Unlike district merges, sacrificed plots <strong>do not need to be occupied</strong>.
          </p>
          <p style="color:#94a3b8;font-size:0.9rem;margin:0;">
            Currently available: <strong style="color:#e2e8f0;">Precious Metal Mint</strong> —
            a sovereign minting facility that converts gold, silver, or platinum into real
            in-game coinage currencies backed by live commodity prices.
          </p>
        </div>

        <div class="card" style="background:#0f172a;border-left:4px solid #7c3aed;">
          <h2 style="margin-top:0;color:#a78bfa;">📊 Your Status</h2>
          <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px;margin-top:12px;">
            <div>
              <div style="color:#64748b;font-size:0.75rem;">SPECIAL PLOTS OWNED</div>
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
            {"" if not is_sub else f'<a href="/special-plots/create" class="btn-blue" style="display:inline-block;padding:10px 20px;background:#7c3aed;color:#fff;border-radius:4px;text-decoration:none;font-weight:bold;">⚗️ Create Special Plot</a>'}
            {"" if is_sub else '<span style="color:#64748b;font-size:0.85rem;">Subscribe to Wadsworth Pro to create special plots.</span>'}
          </div>
        </div>
        """

        # Coin currency live prices
        html += '<div class="card" style="background:#0f172a;border-left:4px solid #f59e0b;">'
        html += '<h2 style="margin-top:0;color:#fbbf24;">💰 Coinage Live Prices</h2>'
        html += '<p style="color:#64748b;font-size:0.8rem;margin-bottom:12px;">Metal-pegged exchange rates update each game tick.</p>'
        html += '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px;">'
        for code, info in _COIN_INFO.items():
            bank = coin_banks.get(code)
            rate = bank.usd_per_unit if bank else 0.0
            rate_str = f"${rate:,.2f}" if rate > 1 else f"${rate:.4f}"
            html += f'''<div style="background:#1e293b;border-radius:6px;padding:10px;">
              <div style="font-size:1.4rem;">{info["emoji"]}</div>
              <div style="color:#e2e8f0;font-weight:bold;font-size:0.9rem;">{code}</div>
              <div style="color:#94a3b8;font-size:0.75rem;">{info["name"]}</div>
              <div style="color:#fbbf24;font-weight:bold;margin-top:4px;">{rate_str}</div>
              <div style="color:#475569;font-size:0.68rem;">{info["alloy"]}</div>
            </div>'''
        html += '</div></div>'

        # Existing special plots
        if special_plots:
            html += '<h2 style="color:#a78bfa;margin-top:32px;">⚗️ Your Special Plots</h2>'
            mint_types = get_mint_business_types()
            for sp in special_plots:
                cfg = SPECIAL_PLOT_TYPES.get(sp.special_type, {})
                plot_name = cfg.get("name", sp.special_type.title())
                status = "OCCUPIED" if sp.occupied_by_business_id else "VACANT"
                status_color = "#22c55e" if sp.occupied_by_business_id else "#64748b"
                html += f'''
                <div class="card" style="border-left:4px solid {status_color};">
                  <div style="display:flex;justify-content:space-between;align-items:start;flex-wrap:wrap;gap:12px;">
                    <div>
                      <h3 style="margin:0;color:#a78bfa;">{plot_name}
                        <span style="background:{status_color};color:#020617;font-size:0.7rem;padding:2px 6px;border-radius:3px;margin-left:6px;">{status}</span>
                      </h3>
                      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px;margin-top:10px;">
                        <div><div style="color:#64748b;font-size:0.7rem;">TERRAIN</div>
                          <div style="color:#e5e7eb;font-size:0.85rem;">{sp.terrain_type.replace("_", " ").title()}</div></div>
                        <div><div style="color:#64748b;font-size:0.7rem;">SIZE</div>
                          <div style="color:#e5e7eb;font-size:0.85rem;">{sp.size:.1f} units</div></div>
                        <div><div style="color:#64748b;font-size:0.7rem;">PLOTS SACRIFICED</div>
                          <div style="color:#e5e7eb;font-size:0.85rem;">{sp.plots_merged}</div></div>
                        <div><div style="color:#64748b;font-size:0.7rem;">MONTHLY TAX</div>
                          <div style="color:#f59e0b;font-size:0.85rem;">{fmt_usd(sp.monthly_tax, disp, precision=0)}</div></div>
                      </div>
                    </div>
                    <div>
                      {"" if sp.occupied_by_business_id else f'<a href="/special-plots/{sp.id}/build" style="display:inline-block;padding:8px 16px;background:#7c3aed;color:#fff;border-radius:4px;text-decoration:none;font-size:0.9rem;">🏗️ Build Mint</a>'}
                    </div>
                  </div>
                </div>'''
        else:
            html += '<div class="card" style="background:#0f172a;text-align:center;padding:40px;color:#64748b;"><p style="margin:0;">No special plots yet. Create your first by sacrificing land.</p></div>'

        return HTMLResponse(_shell("Special Plots", html, 0.0, player.id))

    except Exception as e:
        import traceback
        return HTMLResponse(_shell("Special Plots", f'<div style="color:#ef4444;">Error: {e}<pre style="font-size:0.75rem;color:#64748b;">{traceback.format_exc()}</pre></div>', 0.0, player.id))


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
        enough = len(plist) >= plots_req
        col = "#22c55e" if enough else "#64748b"
        plot_options_html += f'<div style="margin-bottom:14px;"><div style="color:{col};font-size:0.85rem;font-weight:bold;margin-bottom:6px;">{terrain.replace("_"," ").title()} ({len(plist)} available — need {plots_req})</div><div style="display:flex;flex-wrap:wrap;gap:6px;">'
        for p in plist:
            occ = "★ occupied" if p.occupied_by_business_id else "empty"
            plot_options_html += f'<label style="cursor:pointer;"><input type="checkbox" name="plot_ids" value="{p.id}" data-terrain="{terrain}" class="sp-plot-cb" onchange="spUpdateSel()" style="margin-right:4px;"><span style="font-size:0.8rem;color:#94a3b8;">Plot #{p.id} {p.size:.1f}u ({occ})</span></label>'
        plot_options_html += "</div></div>"

    type_opts = "".join(
        f'<option value="{k}">{v["name"]}</option>'
        for k, v in SPECIAL_PLOT_TYPES.items()
    )

    html = f"""
    <a href="/special-plots" style="color:#38bdf8;font-size:0.85rem;">← Special Plots</a>
    <h1 style="margin:12px 0;">⚗️ Create Special Plot</h1>

    <div class="card" style="background:#1e1b4b;border-left:4px solid #7c3aed;">
      <h2 style="color:#a78bfa;margin-top:0;">Requirements</h2>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;">
        <div><div style="color:#64748b;font-size:0.75rem;">PLOTS TO SACRIFICE</div>
          <div style="color:#38bdf8;font-size:1.8rem;font-weight:bold;">{plots_req}</div>
          <div style="color:#64748b;font-size:0.7rem;">Same terrain · empty OK</div></div>
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
        <p style="color:#64748b;font-size:0.85rem;margin-top:0;">All selected plots must share the same terrain type. Empty plots are allowed.</p>
        {plot_options_html if plot_options_html else '<p style="color:#64748b;">No eligible plots found.</p>'}
      </div>

      <div class="card">
        <p style="color:#f87171;font-size:0.85rem;margin-top:0;">⚠️ Sacrificed plots will be permanently destroyed. Any businesses on them will be removed with no refund.</p>
        <div id="sp-sel-status" style="font-size:0.9rem;margin-bottom:10px;color:#94a3b8;">Selected: <strong>0</strong> / {plots_req}</div>
        <button id="sp-submit" type="submit" disabled style="padding:12px 28px;background:#3f3f46;color:#9ca3af;border:none;border-radius:4px;font-size:1rem;font-weight:bold;cursor:not-allowed;">
          ⚗️ Sacrifice Plots & Create Special Plot
        </button>
      </div>
    </form>
    <script>
      var SP_REQ = {plots_req};
      function spUpdateSel() {{
        var boxes = document.querySelectorAll('.sp-plot-cb:checked');
        var n = boxes.length;
        var terrains = {{}};
        boxes.forEach(function(b) {{ terrains[b.dataset.terrain] = 1; }});
        var nTerr = Object.keys(terrains).length;
        var status = document.getElementById('sp-sel-status');
        var btn = document.getElementById('sp-submit');
        var ok = (n === SP_REQ && nTerr <= 1);
        var msg = 'Selected: <strong>' + n + '</strong> / ' + SP_REQ;
        if (nTerr > 1) msg += ' <span style="color:#f87171;">— mixed terrain not allowed</span>';
        else if (n > SP_REQ) msg += ' <span style="color:#f87171;">— too many</span>';
        else if (n === SP_REQ) msg += ' <span style="color:#22c55e;">✓ ready</span>';
        status.innerHTML = msg;
        btn.disabled = !ok;
        btn.style.background = ok ? '#7c3aed' : '#3f3f46';
        btn.style.color = ok ? '#fff' : '#9ca3af';
        btn.style.cursor = ok ? 'pointer' : 'not-allowed';
      }}
    </script>
    """
    return HTMLResponse(_shell("Create Special Plot", html, 0.0, player.id))


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
            url=f"/special-plots?msg=Special+plot+created+successfully",
            status_code=303,
        )
    return RedirectResponse(
        url=f"/special-plots/create?err={err.replace(' ', '+')}",
        status_code=303,
    )


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
    <a href="/special-plots" style="color:#38bdf8;font-size:0.85rem;">← Special Plots</a>
    <h1 style="margin:12px 0;">🏗️ Build Mint on Special Plot #{sp.id}</h1>
    {err_html}

    <div class="card" style="background:#1e293b;">
      <div style="color:#64748b;font-size:0.75rem;">PLOT</div>
      <div style="color:#e2e8f0;">Special Plot #{sp.id} · {sp.terrain_type.replace("_"," ").title()} · {sp.size:.1f} units</div>
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
        return RedirectResponse(url="/special-plots?msg=Mint+built+successfully", status_code=303)
    return RedirectResponse(
        url=f"/special-plots/{plot_id}/build?err={err.replace(' ', '+')}",
        status_code=303,
    )
