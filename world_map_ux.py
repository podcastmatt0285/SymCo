"""
world_map_ux.py — World Map page (/world-map)

Shows a live political atlas of the Wadsworth game world:
  - World stats (total plots, districts, cities, counties)
  - Terrain distribution (plot counts by terrain type)
  - County → City hierarchy with crypto info and member counts
  - Independent cities (not yet in a county)
"""

from typing import Optional
from fastapi import APIRouter, Cookie, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from pydantic import BaseModel

router = APIRouter()

# ── Terrain display config ────────────────────────────────────────────────────
_TERRAIN_COLOR = {
    "prairie":  "#86efac",
    "forest":   "#22c55e",
    "desert":   "#fbbf24",
    "marsh":    "#67e8f9",
    "mountain": "#94a3b8",
    "tundra":   "#bae6fd",
    "jungle":   "#4ade80",
    "savanna":  "#d97706",
    "hills":    "#a3e635",
    "island":   "#f472b6",
    "coastal":  "#60a5fa",
    "lake":     "#38bdf8",
    "ocean":    "#1e40af",
}

_TERRAIN_ICON = {
    "prairie":  "🌾",
    "forest":   "🌲",
    "desert":   "🏜️",
    "marsh":    "🌿",
    "mountain": "⛰️",
    "tundra":   "❄️",
    "jungle":   "🌴",
    "savanna":  "🦁",
    "hills":    "🏔️",
    "island":   "🏝️",
    "coastal":  "🌊",
    "lake":     "💧",
    "ocean":    "🌐",
}


def _require_auth(session_token):
    try:
        import auth
        db = auth.get_db()
        player = auth.get_player_from_session(db, session_token)
        db.close()
        if not player:
            return RedirectResponse(url="/login", status_code=303)
        return player
    except Exception:
        return RedirectResponse(url="/login", status_code=303)


def _fmt(n: float) -> str:
    if n >= 1_000_000:
        return f"${n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"${n/1_000:.1f}K"
    return f"${n:,.0f}"


def _build_world_map(player) -> str:
    # ── Pull data ─────────────────────────────────────────────────────────────
    try:
        from counties import get_all_counties, CountyCity, get_db as get_county_db
        counties = get_all_counties()
        cdb = get_county_db()
        county_city_links = {cc.city_id: cc.county_id for cc in cdb.query(CountyCity).all()}
        cdb.close()
    except Exception:
        counties = []
        county_city_links = {}

    try:
        from cities import get_all_cities
        all_cities = get_all_cities()
    except Exception:
        all_cities = []

    try:
        from auth import get_db as get_auth_db, Player
        adb = get_auth_db()
        mayor_names = {
            p.id: (p.username or f"Player {p.id}")
            for p in adb.query(Player).all()
        }
        adb.close()
    except Exception:
        mayor_names = {}

    try:
        from districts import District, get_db as get_dist_db
        ddb = get_dist_db()
        district_count = ddb.query(District).count()
        ddb.close()
    except Exception:
        district_count = 0

    try:
        from land import LandPlot, get_db as get_land_db
        from sqlalchemy import func
        ldb = get_land_db()
        terrain_rows = (
            ldb.query(LandPlot.terrain_type, func.count(LandPlot.id))
            .filter(LandPlot.is_government_owned == False)
            .group_by(LandPlot.terrain_type)
            .all()
        )
        terrain_counts = {row[0]: row[1] for row in terrain_rows if not str(row[0]).startswith("district_")}
        total_plots = sum(terrain_counts.values())
        ldb.close()
    except Exception:
        terrain_counts = {}
        total_plots = 0

    city_count  = len(all_cities)
    county_count = len(counties)

    # ── Global stats bar ─────────────────────────────────────────────────────
    def _stat_card(val, lbl, col):
        return (
            '<div style="background:#0f172a;border:1px solid #1e293b;border-radius:6px;padding:16px;text-align:center;">'
            f'<div style="font-size:1.6rem;font-weight:900;color:{col};margin-bottom:4px;">{val}</div>'
            f'<div style="font-size:0.72rem;color:#64748b;text-transform:uppercase;letter-spacing:.06em;">{lbl}</div>'
            '</div>'
        )
    stat_cards = (
        _stat_card(f"{total_plots:,}",    "Land Plots", "#60a5fa") +
        _stat_card(f"{district_count:,}", "Districts",  "#a78bfa") +
        _stat_card(f"{city_count:,}",     "Cities",     "#34d399") +
        _stat_card(f"{county_count:,}",   "Counties",   "#f59e0b")
    )
    stats_bar = (
        '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:28px;">'
        + stat_cards +
        '</div>'
    )

    # ── Terrain distribution ──────────────────────────────────────────────────
    terrain_html = ""
    if terrain_counts:
        max_count = max(terrain_counts.values()) or 1
        rows = ""
        for terrain, count in sorted(terrain_counts.items(), key=lambda x: -x[1]):
            if terrain.startswith("district_"):
                continue
            color = _TERRAIN_COLOR.get(terrain, "#94a3b8")
            icon  = _TERRAIN_ICON.get(terrain, "🌍")
            pct   = int(count / max_count * 100)
            rows += f"""
<div style="display:grid;grid-template-columns:110px 1fr 40px;align-items:center;gap:10px;margin-bottom:6px;">
  <div style="font-size:0.78rem;color:#cbd5e1;display:flex;align-items:center;gap:6px;">
    <span>{icon}</span><span style="text-transform:capitalize;">{terrain}</span>
  </div>
  <div style="background:#1e293b;border-radius:3px;height:8px;overflow:hidden;">
    <div style="background:{color};height:100%;width:{pct}%;border-radius:3px;"></div>
  </div>
  <div style="font-size:0.72rem;color:#64748b;text-align:right;">{count:,}</div>
</div>"""
        terrain_html = f"""
<div style="background:#0f172a;border:1px solid #1e293b;border-radius:8px;padding:20px 24px;margin-bottom:28px;">
  <div style="font-size:0.78rem;font-weight:bold;color:#94a3b8;text-transform:uppercase;
              letter-spacing:.06em;margin-bottom:16px;">Terrain Distribution</div>
  {rows}
</div>"""

    # ── Build county → city map ───────────────────────────────────────────────
    # Group cities by county
    cities_by_county: dict[int, list] = {c["id"]: [] for c in counties}
    independent_cities = []
    for city in all_cities:
        cty_id = county_city_links.get(city["id"])
        if cty_id and cty_id in cities_by_county:
            cities_by_county[cty_id].append(city)
        else:
            independent_cities.append(city)

    # ── County cards ─────────────────────────────────────────────────────────
    def _city_chip(city: dict) -> str:
        mayor = mayor_names.get(city["mayor_id"], "?")
        currency = city["currency_type"].replace("_", " ").title() if city.get("currency_type") else "—"
        return f"""
<a href="/city/{city['id']}" style="display:block;background:#0f172a;border:1px solid #334155;
   border-radius:6px;padding:12px 14px;text-decoration:none;transition:border-color .2s;"
   onmouseover="this.style.borderColor='#4ade80'" onmouseout="this.style.borderColor='#334155'">
  <div style="font-size:0.85rem;font-weight:bold;color:#f1f5f9;margin-bottom:4px;">{city['name']}</div>
  <div style="font-size:0.72rem;color:#64748b;">
    Mayor: <span style="color:#94a3b8;">{mayor}</span>
    &nbsp;·&nbsp; {city['member_count']}/25 members
    &nbsp;·&nbsp; Currency: <span style="color:#34d399;">{currency}</span>
  </div>
</a>"""

    county_cards = ""
    for county in counties:
        cid    = county["id"]
        cities = cities_by_county.get(cid, [])
        logo   = county.get("logo_svg") or ""

        price_change = county.get("price_change_24h", 0.0)
        change_color = "#4ade80" if price_change >= 0 else "#ef4444"
        change_arrow = "▲" if price_change >= 0 else "▼"
        change_str   = f"{change_arrow} {abs(price_change):.1f}%"

        city_chips = "".join(_city_chip(c) for c in cities)
        if not city_chips:
            city_chips = '<div style="font-size:0.78rem;color:#475569;padding:8px 0;">No cities yet</div>'
        else:
            city_chips = f'<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:8px;margin-top:12px;">{city_chips}</div>'

        county_cards += f"""
<div style="background:#0a0f1a;border:1px solid #2d4a22;border-radius:10px;padding:20px 24px;margin-bottom:16px;
            box-shadow:0 0 30px rgba(245,158,11,0.04);">
  <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:16px;flex-wrap:wrap;">
    <div style="display:flex;align-items:center;gap:14px;">
      {"<div style='width:48px;height:48px;flex-shrink:0;'>" + logo + "</div>" if logo else
       "<div style='width:48px;height:48px;border-radius:50%;background:#1e293b;display:flex;align-items:center;justify-content:center;font-size:1.4rem;'>🏛️</div>"}
      <div>
        <div style="font-size:1.1rem;font-weight:900;color:#f1f5f9;">{county['name']}</div>
        <div style="font-size:0.78rem;color:#64748b;margin-top:2px;">
          {county['city_count']}/{county['max_cities']} cities
          &nbsp;·&nbsp;
          <a href="/county/{cid}" style="color:#f59e0b;text-decoration:none;">{county['crypto_symbol']} →</a>
        </div>
      </div>
    </div>
    <div style="text-align:right;flex-shrink:0;">
      <div style="font-size:1rem;font-weight:bold;color:#f59e0b;">${county['crypto_price']:.4f}</div>
      <div style="font-size:0.72rem;color:{change_color};">{change_str} (24h)</div>
      <div style="font-size:0.7rem;color:#475569;margin-top:2px;">
        MCap: {_fmt(county['market_cap'])}
      </div>
    </div>
  </div>
  {city_chips}
</div>"""

    if not county_cards:
        county_cards = """
<div style="text-align:center;padding:32px;color:#475569;font-style:italic;">
  No counties have been formed yet. <a href="/counties" style="color:#f59e0b;">View County requirements →</a>
</div>"""

    counties_section = f"""
<div style="margin-bottom:28px;">
  <div style="font-size:0.78rem;font-weight:bold;color:#94a3b8;text-transform:uppercase;
              letter-spacing:.06em;margin-bottom:14px;">Counties</div>
  {county_cards}
</div>"""

    # ── Independent cities ─────────────────────────────────────────────────────
    indep_section = ""
    if independent_cities:
        chips = "".join(_city_chip(c) for c in independent_cities)
        indep_section = f"""
<div style="margin-bottom:28px;">
  <div style="font-size:0.78rem;font-weight:bold;color:#94a3b8;text-transform:uppercase;
              letter-spacing:.06em;margin-bottom:14px;">Independent Cities
    <span style="font-weight:normal;color:#475569;text-transform:none;letter-spacing:0;
                 margin-left:8px;font-size:0.72rem;">(not yet in a county)</span>
  </div>
  <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:8px;">
    {chips}
  </div>
</div>"""

    # ── Bottom CTA cards ──────────────────────────────────────────────────────
    cta = """
<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px;margin-top:8px;">
  <a href="/land" style="display:flex;align-items:center;gap:10px;padding:14px 16px;
     background:#0f172a;border:1px solid #1e293b;border-radius:6px;text-decoration:none;
     color:#f1f5f9;font-size:0.82rem;font-weight:bold;">
    🗺️ My Land
  </a>
  <a href="/districts" style="display:flex;align-items:center;gap:10px;padding:14px 16px;
     background:#0f172a;border:1px solid #1e293b;border-radius:6px;text-decoration:none;
     color:#f1f5f9;font-size:0.82rem;font-weight:bold;">
    🏛️ Districts
  </a>
  <a href="/cities" style="display:flex;align-items:center;gap:10px;padding:14px 16px;
     background:#0f172a;border:1px solid #1e293b;border-radius:6px;text-decoration:none;
     color:#f1f5f9;font-size:0.82rem;font-weight:bold;">
    🏙️ Cities
  </a>
  <a href="/counties" style="display:flex;align-items:center;gap:10px;padding:14px 16px;
     background:#0f172a;border:1px solid #1e293b;border-radius:6px;text-decoration:none;
     color:#f1f5f9;font-size:0.82rem;font-weight:bold;">
    🏛️ Counties
  </a>
  <a href="/land-market" style="display:flex;align-items:center;gap:10px;padding:14px 16px;
     background:#0f172a;border:1px solid #1e293b;border-radius:6px;text-decoration:none;
     color:#f1f5f9;font-size:0.82rem;font-weight:bold;">
    🛒 Land Market
  </a>
</div>"""

    return stats_bar + terrain_html + counties_section + indep_section + cta


@router.get("/api/my-properties", response_class=JSONResponse)
def api_my_properties(
    session_token: Optional[str] = Cookie(None),
    player_id: Optional[int] = Query(None),
):
    viewer = _require_auth(session_token)
    if isinstance(viewer, RedirectResponse):
        return JSONResponse({"error": "auth"}, status_code=401)

    target_id = player_id if player_id else viewer.id

    try:
        import auth as _auth
        adb = _auth.get_db()
        target = adb.query(_auth.Player).filter_by(id=target_id).first()
        player_name = (getattr(target, "business_name", None)
                       or getattr(target, "username", None)
                       or f"Player {target_id}")
        adb.close()
    except Exception:
        player_name = f"Player {target_id}"

    plots_out = []
    try:
        from land import get_db as _ldb, LandPlot
        from business import Business, BUSINESS_TYPES, get_district_business_types

        ldb = _ldb()
        _dist_types = get_district_business_types()

        plots = (ldb.query(LandPlot)
                    .filter(LandPlot.owner_id == target_id,
                            LandPlot.is_government_owned == False)
                    .order_by(LandPlot.id)
                    .all())

        biz_ids = [p.occupied_by_business_id for p in plots if p.occupied_by_business_id]
        biz_map = {}
        if biz_ids:
            for b in ldb.query(Business).filter(Business.id.in_(biz_ids)).all():
                cfg = BUSINESS_TYPES.get(b.business_type) or _dist_types.get(b.business_type) or {}
                biz_map[b.id] = {
                    "type": b.business_type,
                    "name": cfg.get("name", b.business_type.replace("_", " ").title()),
                    "class": cfg.get("class", "production"),
                }
        ldb.close()

        for p in plots:
            biz = biz_map.get(p.occupied_by_business_id) if p.occupied_by_business_id else None
            _prox_str = p.proximity_features or ""
            plots_out.append({
                "id":          p.id,
                "terrain":     p.terrain_type,
                "proximity":   [f.strip() for f in _prox_str.split(",") if f.strip()],
                "efficiency":  round(p.efficiency or 0, 1),
                "monthly_tax": round(p.monthly_tax or 0, 2),
                "biz_type":    biz["type"]  if biz else None,
                "biz_name":    biz["name"]  if biz else None,
                "biz_class":   biz["class"] if biz else None,
            })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

    # Include contacts' plots when viewing your own properties (max 6 contacts)
    contacts_out = []
    if target_id == viewer.id:
        try:
            from contacts import get_contacts
            from land import get_db as _ldb2, LandPlot as _LandPlot2
            from business import Business as _Biz2, BUSINESS_TYPES as _BT2, get_district_business_types as _gdbt2

            contact_list = get_contacts(viewer.id)[:6]
            _dt2 = _gdbt2()

            for (_row, other_id, _notes) in contact_list:
                try:
                    adb2 = _auth.get_db()
                    other = adb2.query(_auth.Player).filter_by(id=other_id).first()
                    other_name = (getattr(other, "business_name", None)
                                  or getattr(other, "username", None)
                                  or f"Player {other_id}")
                    adb2.close()

                    ldb2 = _ldb2()
                    other_plots = (ldb2.query(_LandPlot2)
                                       .filter(_LandPlot2.owner_id == other_id,
                                               _LandPlot2.is_government_owned == False)
                                       .order_by(_LandPlot2.id)
                                       .all())
                    obiz_ids = [p.occupied_by_business_id for p in other_plots if p.occupied_by_business_id]
                    obiz_map = {}
                    if obiz_ids:
                        for b in ldb2.query(_Biz2).filter(_Biz2.id.in_(obiz_ids)).all():
                            cfg = _BT2.get(b.business_type) or _dt2.get(b.business_type) or {}
                            obiz_map[b.id] = {
                                "type":  b.business_type,
                                "name":  cfg.get("name", b.business_type.replace("_", " ").title()),
                                "class": cfg.get("class", "production"),
                            }
                    ldb2.close()

                    cplots = []
                    for p in other_plots:
                        ob = obiz_map.get(p.occupied_by_business_id) if p.occupied_by_business_id else None
                        _cprox_str = p.proximity_features or ""
                        cplots.append({
                            "id":          p.id,
                            "terrain":     p.terrain_type,
                            "proximity":   [f.strip() for f in _cprox_str.split(",") if f.strip()],
                            "efficiency":  round(p.efficiency or 0, 1),
                            "monthly_tax": round(p.monthly_tax or 0, 2),
                            "biz_type":    ob["type"]  if ob else None,
                            "biz_name":    ob["name"]  if ob else None,
                            "biz_class":   ob["class"] if ob else None,
                        })
                    contacts_out.append({"player_id": other_id, "player_name": other_name, "plots": cplots})
                except Exception:
                    pass
        except Exception:
            pass

    return JSONResponse({"player_id": target_id, "player_name": player_name,
                         "plots": plots_out, "contacts": contacts_out})


class _MoveBizBody(BaseModel):
    from_plot_id: int
    to_plot_id: int


@router.post("/api/move-business", response_class=JSONResponse)
def api_move_business(
    body: _MoveBizBody,
    session_token: Optional[str] = Cookie(None),
):
    viewer = _require_auth(session_token)
    if isinstance(viewer, RedirectResponse):
        return JSONResponse({"error": "auth"}, status_code=401)

    try:
        from land import get_db as _ldb, LandPlot
        from business import Business

        ldb = _ldb()
        from_plot = ldb.query(LandPlot).filter_by(id=body.from_plot_id).first()
        to_plot   = ldb.query(LandPlot).filter_by(id=body.to_plot_id).first()

        if not from_plot or not to_plot:
            ldb.close()
            return JSONResponse({"error": "plot not found"}, status_code=404)
        if from_plot.owner_id != viewer.id or to_plot.owner_id != viewer.id:
            ldb.close()
            return JSONResponse({"error": "not your plot"}, status_code=403)
        if not from_plot.occupied_by_business_id:
            ldb.close()
            return JSONResponse({"error": "no business on source plot"}, status_code=400)
        if to_plot.occupied_by_business_id:
            ldb.close()
            return JSONResponse({"error": "destination plot occupied"}, status_code=400)

        biz_id = from_plot.occupied_by_business_id
        biz = ldb.query(Business).filter_by(id=biz_id).first()

        from_plot.occupied_by_business_id = None
        to_plot.occupied_by_business_id   = biz_id
        if biz:
            biz.land_plot_id = body.to_plot_id

        ldb.commit()
        ldb.close()
        return JSONResponse({"ok": True})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)



_MY_PROPS_MODAL = r"""
<div id="mpModal" style="display:none;position:fixed;inset:0;z-index:9999;background:#000;
     flex-direction:column;align-items:stretch;">
  <!-- Header bar -->
  <div style="display:flex;align-items:center;justify-content:space-between;padding:8px 14px;
              background:#060c18;border-bottom:1px solid #1e293b;flex-shrink:0;flex-wrap:wrap;gap:6px;">
    <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
      <span id="mpTitle" style="font-size:0.95rem;font-weight:700;color:#f1f5f9;">My Properties</span>
      <span id="mpCount" style="font-size:0.72rem;color:#475569;"></span>
      <span id="mpMoveHint" style="display:none;font-size:0.7rem;color:#f59e0b;
            background:rgba(69,26,3,0.8);padding:2px 8px;border-radius:4px;">
        Select a plot to swap — Esc to cancel
      </span>
    </div>
    <div style="display:flex;gap:5px;align-items:center;flex-wrap:wrap;">
      <button id="mpSwapBtn" onclick="mpEnterSwapMode()"
              style="display:none;background:#1e293b;border:1px solid #334155;color:#fbbf24;
                     padding:4px 10px;border-radius:4px;cursor:pointer;font-size:0.7rem;">
        ⇄ Swap Plots
      </button>
      <button onclick="mpZoom(1.25)" style="background:#1e293b;border:none;color:#94a3b8;
              padding:4px 10px;border-radius:4px;cursor:pointer;font-size:1rem;line-height:1;">+</button>
      <button onclick="mpZoom(1/1.25)" style="background:#1e293b;border:none;color:#94a3b8;
              padding:4px 10px;border-radius:4px;cursor:pointer;font-size:1rem;line-height:1;">−</button>
      <button onclick="mpReset()" style="background:#1e293b;border:none;color:#64748b;
              padding:4px 8px;border-radius:4px;cursor:pointer;font-size:0.68rem;">Fit</button>
      <button onclick="closeMpModal()" style="background:#7f1d1d;border:none;color:#fca5a5;
              padding:4px 12px;border-radius:4px;cursor:pointer;font-weight:bold;">✕</button>
    </div>
  </div>
  <!-- Canvas area -->
  <div style="position:relative;flex:1;overflow:hidden;">
    <canvas id="mpCanvas" style="width:100%;height:100%;cursor:grab;touch-action:none;display:block;"></canvas>
    <div id="mpInfo" style="display:none;position:absolute;top:10px;right:10px;
         background:rgba(6,12,24,0.97);border:1px solid #334155;border-radius:8px;
         padding:12px 14px;font-size:0.75rem;color:#e2e8f0;width:200px;line-height:1.6;
         box-shadow:0 4px 24px rgba(0,0,0,0.6);">
      <button onclick="document.getElementById('mpInfo').style.display='none'"
              style="position:absolute;top:6px;right:8px;background:none;border:none;
                     color:#475569;cursor:pointer;font-size:0.75rem;">✕</button>
      <div id="mpInfoContent"></div>
    </div>
  </div>
  <!-- Mini radio bar pinned to bottom of modal -->
  <div id="mpRadioBar" style="
       display:flex;align-items:center;gap:8px;padding:5px 12px;
       background:#1A0F0A;border-top:1px solid #B08D57;flex-shrink:0;
       font-size:0.72rem;color:#F5F5DC;font-family:Georgia,serif;">
    <span style="font-size:1rem;color:#B08D57;flex-shrink:0;">📻</span>
    <div style="flex:1;min-width:0;overflow:hidden;">
      <div id="mpRadioSname" style="font-size:0.55rem;color:#B08D57;opacity:0.7;
           text-transform:uppercase;letter-spacing:0.1em;white-space:nowrap;">WLOL 92.8 FM</div>
      <div id="mpRadioTitle" style="color:#e5e7eb;white-space:nowrap;overflow:hidden;
           text-overflow:ellipsis;">—</div>
    </div>
    <button onclick="mpRadioPlay()" id="mpRadioPP"
            style="background:none;border:none;color:#B08D57;font-size:1rem;cursor:pointer;padding:0;">▶</button>
    <button onclick="mpRadioSkip()"
            style="background:none;border:none;color:#B08D57;opacity:0.6;font-size:0.9rem;cursor:pointer;padding:0;">⏭</button>
    <input id="mpRadioVol" type="range" min="0" max="1" step="0.05" value="0.35"
           oninput="mpRadioSetVol(this.value)"
           style="width:48px;accent-color:#B08D57;cursor:pointer;">
    <div onclick="mpRadioTune()" title="Switch station"
         style="display:flex;flex-direction:column;align-items:center;gap:1px;cursor:pointer;">
      <div style="width:20px;height:20px;border-radius:50%;
                  background:linear-gradient(to bottom,#3d2b1f,#1a0f0a);
                  border:1px solid rgba(176,141,87,0.5);position:relative;">
        <div id="mpRadioKnob" style="position:absolute;top:2px;left:50%;width:2px;height:6px;
             background:#B08D57;border-radius:999px;
             transform:translateX(-50%) rotate(180deg);transform-origin:50% 100%;
             transition:transform 0.5s ease;"></div>
      </div>
      <span id="mpRadioKlbl" style="font-size:0.42rem;text-transform:uppercase;
            color:#B08D57;font-weight:bold;letter-spacing:0.06em;">WLOL</span>
    </div>
  </div>
  <div id="mpTooltip" style="display:none;position:fixed;background:rgba(6,12,24,0.95);
       border:1px solid #334155;border-radius:5px;padding:5px 10px;font-size:0.72rem;
       color:#e2e8f0;pointer-events:none;max-width:170px;z-index:10000;line-height:1.5;"></div>
</div>

<script>
(function(){
  var TW=64, TH=38, BLOCK=4;
  var SPRITE_BASE='/static/iso/buildings/';
  var TILE_BASE='/static/iso/tiles/';
  var ISO_BASE='/assets/iso/';
  var tileImgs={};

  /* 3×3 downtown block — 8 buildings surrounding a central park.
     Raw vc coordinates used (no p2v road-gap math) so tiles are adjacent. */
  var DOWNTOWN=[
    {label:'Reserve Bank',     sprite:'commercial',  url:'/reserve-bank',    row:0,col:0},
    {label:'Stock Exchange',   sprite:'university',  url:'/brokerage',       row:0,col:1},
    {label:'Commodity Market', sprite:'shop_medium', url:'/market',          row:0,col:2},
    {label:'Land Registry',    sprite:'mansion',     url:'/land-market',     row:1,col:0},
    /* (1,1) = center park tile — intentionally absent from this array */
    {label:'District Market',  sprite:'shop_medium', url:'/district-market', row:1,col:2},
    {label:'City Hall',        sprite:'mansion',     url:'/cities',          row:2,col:0},
    {label:'Businesses',       sprite:'industrial',  url:'/businesses',      row:2,col:1},
    {label:'Memecoin Exchange',sprite:'space',       url:'/memecoins',       row:2,col:2},
  ];
  var DT_N=3; /* side length of the square downtown block */

  /* downtown top-left visual col (raw, consecutive — no p2v road spacing) */
  function getDtVcBase(gs){ return Math.max(0, Math.round((totalVC(gs)-DT_N)/2)); }

  /* downtown occupies vr = -DT_N .. -1; road separator at vr=0; player grid vr=1..tv */
  var DT_VR_TOP=-DT_N; /* = -3 */

  /* Per-terrain color scheme: c=top fill, s=stroke/edge */
  var TERRAIN_SCHEME={
    urban:    {c:'#4a5568',s:'#2d3748'}, prairie:  {c:'#3d6634',s:'#254020'},
    forest:   {c:'#145228',s:'#0a3018'}, desert:   {c:'#b8861e',s:'#7a5a10'},
    marsh:    {c:'#1e6a58',s:'#124038'}, mountain: {c:'#5a6070',s:'#38404a'},
    tundra:   {c:'#6898b4',s:'#405a70'}, jungle:   {c:'#147828',s:'#0a4818'},
    savanna:  {c:'#9a6c2e',s:'#604018'}, hills:    {c:'#4a6828',s:'#2e4018'},
    island:   {c:'#5a9020',s:'#385810'}, coastal:  {c:'#2860a0',s:'#183860'},
    ocean:    {c:'#102858',s:'#081430'}, lake:     {c:'#1a5088',s:'#0e3050'},
    district_food:         {c:'#7a3a1a',s:'#4a2010'},
    district_hospital:     {c:'#781850',s:'#480a30'},
    district_industrial:   {c:'#785018',s:'#483208'},
    district_medical:      {c:'#522088',s:'#321058'},
    district_neighborhood: {c:'#1e6040',s:'#104028'},
    district_transport:    {c:'#1e3c70',s:'#0e2040'},
    district_utilities:    {c:'#504018',s:'#302808'},
    district_zoo:          {c:'#2a6020',s:'#183a10'},
    district_aerospace:    {c:'#183060',s:'#0a1838'},
    district_coastal:      {c:'#185068',s:'#0a2c38'},
    district_education:    {c:'#3a2870',s:'#221840'},
    district_entertainment:{c:'#701850',s:'#401030'},
    district_food_court:   {c:'#7a3e18',s:'#4a2408'},
    district_mall:         {c:'#4a2870',s:'#2a1040'},
    district_military:     {c:'#303a20',s:'#1a2210'},
    district_prison:       {c:'#3a2e20',s:'#201808'},
    district_shipyard:     {c:'#182e50',s:'#0a1830'},
    district_tech:         {c:'#12205a',s:'#080e30'},
    district_airport:         {c:'#2a3858',s:'#141c30'},
    district_convention_center:{c:'#582858',s:'#301430'},
    district_entertainment_district:{c:'#681858',s:'#380830'},
    district_mega_mall:    {c:'#4a3278',s:'#281848'},
    district_military_base:{c:'#202e18',s:'#101808'},
    district_prison_complex:{c:'#2e2418',s:'#180e08'},
    district_research_campus:{c:'#143a68',s:'#081e38'},
    district_seaport:      {c:'#143858',s:'#081e30'},
    district_tech_park:    {c:'#0a1e58',s:'#041030'},
  };
  /* Proximity overlay tints: fill + optional stroke color */
  var PROX_TINT={
    urban:     {f:'rgba(100,116,139,0.22)', k:'rgba(148,163,184,0.35)'},
    coastal:   {f:'rgba(56,189,248,0.18)',  k:'rgba(56,189,248,0.30)'},
    riverside: {f:'rgba(96,165,250,0.16)',  k:'rgba(96,165,250,0.25)'},
    lakeside:  {f:'rgba(56,189,248,0.13)',  k:'rgba(56,189,248,0.20)'},
    oasis:     {f:'rgba(74,222,128,0.22)',  k:'rgba(74,222,128,0.38)'},
    hot_springs:{f:'rgba(255,255,255,0.10)',k:'rgba(255,255,255,0.22)'},
    caves:     {f:'rgba(0,0,0,0.28)',       k:null},
    volcanic:  {f:'rgba(239,68,68,0.20)',   k:'rgba(239,68,68,0.35)'},
    road:      {f:'rgba(120,100,70,0.18)',  k:'rgba(161,128,80,0.28)'},
    deposits:  {f:'rgba(251,146,60,0.20)',  k:'rgba(251,146,60,0.38)'},
    remote:    {f:'rgba(0,0,0,0.22)',       k:null},
  };
  /* Terrain → PNG tile name(s) from /static/iso/tiles/ (tipsy/isometric-tiles, CC0).
     Multiple entries rotate deterministically per grid position for variety. */
  var TERRAIN_TILE={
    prairie:  ['terrain_grass','terrain_grass_v2','terrain_grass_v3','terrain_grass_v4'],
    hills:    ['terrain_grass_v2','terrain_grass_v4','terrain_grass_v5','terrain_savanna_v3'],
    forest:   ['terrain_grass_v3','terrain_grass','terrain_grass_v4','terrain_grass_v5'],
    jungle:   ['terrain_grass_v3','terrain_grass_v5','terrain_grass_v2','terrain_grass'],
    marsh:    ['terrain_grass_v4','terrain_grass_v5','terrain_grass_v3'],
    island:   ['terrain_grass_v2','terrain_savanna','terrain_arid'],
    savanna:  ['terrain_savanna','terrain_savanna_v2','terrain_savanna_v3'],
    desert:   ['terrain_arid','terrain_arid2','terrain_arid3','terrain_arid_v2','terrain_arid_v3','terrain_arid_v4'],
    mountain: ['terrain_snow_v3','terrain_snow_v4','terrain_arid_v3','terrain_snow2'],
    tundra:   ['terrain_snow','terrain_snow_v2','terrain_snow_v3','terrain_snow_v4'],
    urban:    ['tile1','tile2','tile3'],
    coastal:  ['iso_water2','terrain_water_a','terrain_savanna'],
    ocean:    ['iso_water2','terrain_water_b','iso_water2'],
    lake:     ['iso_water2','terrain_water_b','terrain_water_a'],
    district_food:              ['terrain_savanna_v3','terrain_grass_v4'],
    district_hospital:          ['terrain_arid2','terrain_arid_v3'],
    district_industrial:        ['terrain_arid_v4','terrain_arid_v3'],
    district_medical:           ['terrain_arid2','terrain_arid_v4'],
    district_neighborhood:      ['terrain_grass_v2','terrain_grass_v3'],
    district_transport:         ['terrain_arid_v3','terrain_arid_v4'],
    district_utilities:         ['terrain_arid_v4','terrain_arid3'],
    district_zoo:               ['terrain_grass_v3','terrain_savanna_v2'],
    district_aerospace:         ['terrain_snow_v3','terrain_arid_v3'],
    district_coastal:           ['terrain_water_a','terrain_arid'],
    district_education:         ['terrain_grass_v2','terrain_savanna_v3'],
    district_entertainment:     ['terrain_arid_v4','terrain_arid3'],
    district_food_court:        ['terrain_savanna_v2','terrain_grass_v5'],
    district_mall:              ['terrain_arid2','terrain_arid_v3'],
    district_military:          ['terrain_grass_v4','terrain_savanna_v3'],
    district_prison:            ['terrain_arid_v3','terrain_arid2'],
    district_shipyard:          ['terrain_water_a','terrain_arid_v3'],
    district_tech:              ['terrain_snow_v3','terrain_arid_v4'],
    district_airport:           ['terrain_arid_v3','terrain_snow_v3'],
    district_convention_center: ['terrain_arid2','terrain_arid_v2'],
    district_entertainment_district:['terrain_arid_v4','terrain_arid3'],
    district_mega_mall:         ['terrain_arid_v2','terrain_arid2'],
    district_military_base:     ['terrain_grass_v4','terrain_savanna_v3'],
    district_prison_complex:    ['terrain_arid_v3','terrain_snow_v3'],
    district_research_campus:   ['terrain_snow_v3','terrain_arid_v4'],
    district_seaport:           ['terrain_water_a','terrain_water_b'],
    district_tech_park:         ['terrain_snow_v4','terrain_arid_v4'],
  };

  function spriteFor(t,cls){
    if(!t) return null;
    /* extraction / mining */
    if(/mine|alluvial|quarry|mineral|oil_rig/.test(t))                return 'warehouse';
    /* energy */
    if(/solar|power_plant|powerplant/.test(t))                        return 'powerplant';
    /* water utility */
    if(/water_facility|water_tower|watertower/.test(t))               return 'watertower';
    /* health */
    if(/hospital|clinic|medical|infirmary|pharmaceutical/.test(t))    return 'hospital';
    /* education */
    if(/university|college/.test(t))                                  return 'university';
    if(/school|academy/.test(t))                                      return 'school';
    /* emergency */
    if(/police/.test(t))                                              return 'police_station';
    if(/fire_station|firehouse/.test(t))                              return 'fire_station';
    /* transport hub */
    if(/airport|aviation/.test(t))                                    return 'airport';
    /* sports & entertainment */
    if(/stadium|arena|coliseum/.test(t))                              return 'stadium';
    /* marine leisure (boat yards, marinas, dive ops) */
    if(/marina|boat_yard|dive_op/.test(t))                            return 'tennis';
    /* storage / logistics */
    if(/warehouse|storage|depot|silo/.test(t))                        return 'warehouse';
    /* luxury & upscale commerce */
    if(/jeweler|lapidary|luxury_show|publishing_house/.test(t))       return 'mansion';
    /* aquatic harvesting / marine fleets */
    if(/aquaculture|pearl_oyster|shellfish|crustacean|freshwater_fish|shrimp_fleet|trawler|deep_sea|purse_seine/.test(t)) return 'park_large';
    /* open field agriculture */
    if(/rice_paddy|cotton_fields|vegetable_farm|grain_farm|peanut_farm|flower_farm|poultry_farm|free_range/.test(t)) return 'park_large';
    /* orchards, vineyards & tree crops */
    if(/orchard|vineyard|hop_farm|tea_plant|coffee_plant|cocoa_plant|spice_plant/.test(t)) return 'trees';
    /* general plantation / farm / pasture */
    if(/plantation|agave|apiary|pasture|paddock|farm|field/.test(t))  return 'park';
    /* timber / forestry */
    if(/lumber|timber|logging/.test(t))                               return 'park_medium';
    /* sit-down dining & bars */
    if(/restaurant|sushi_bar|wine_bar|bistro|pub|gourmet/.test(t))    return 'house_medium';
    /* small food vendors & cafes */
    if(/coffeehouse|burrito_truck|fish_cart|hot_dog_cart|pie_bakery|pastry_kitchen|soup_kitchen|kitchen|street_flower/.test(t)) return 'house_small';
    /* artisan production "houses" */
    if(/malting_house|pipe_tobacco_house|tobacco_curing_house|smokehouse/.test(t)) return 'residential';
    /* big-box & general retail */
    if(/grocery|supermarket|market|mall|auto_deal|gas_station|home_goods|fashion|pet_store|pharmacy/.test(t)) return 'commercial';
    /* small specialty shops */
    if(/shop|store|boutique|kiosk|bookstore|bakery_retail|crystal|tobacco_shop|flower_shop|butcher|stationery|arts_and_crafts/.test(t)) return 'shop_small';
    /* heavy production */
    if(/refinery|factory|mill|foundry|plant|smelter|distillery|brewery|winery|cannery|processing|tannery|works|cooperage/.test(t)) return 'industrial';
    /* ritual / spiritual */
    if(/ritual|church|temple|shrine/.test(t))                         return 'space';
    if(cls==='retail') return 'shop_medium';
    return 'industrial';
  }

  function shade(hex,amt){
    var n=parseInt(hex.slice(1),16);
    var r=Math.min(255,Math.max(0,(n>>16)+amt));
    var g=Math.min(255,Math.max(0,((n>>8)&0xff)+amt));
    var b=Math.min(255,Math.max(0,(n&0xff)+amt));
    return '#'+((1<<24)|(r<<16)|(g<<8)|b).toString(16).slice(1);
  }

  /* Deterministic tile variant 1-3 based on position — avoids flicker on re-render */
  function tileVar(vc,vr){ return (Math.abs(vc)*3+Math.abs(vr)*7)%3+1; }

  /* Proximity feature overlays drawn as semi-transparent colored fills */
  function drawProxOverlay(sx,sy,prox){
    if(!prox||!prox.length) return;
    var hw=(TW/2)*scale,hh=(TH/2)*scale;
    prox.forEach(function(p){
      var t=PROX_TINT[p]; if(!t) return;
      ctx.save();
      ctx.beginPath();
      ctx.moveTo(sx+hw,sy); ctx.lineTo(sx+hw*2,sy+hh);
      ctx.lineTo(sx+hw,sy+hh*2); ctx.lineTo(sx,sy+hh);
      ctx.closePath();
      ctx.clip();
      if(t.f){ctx.fillStyle=t.f;ctx.fill();}
      if(t.k){ctx.strokeStyle=t.k;ctx.lineWidth=1;ctx.stroke();}
      /* deposits: scattered orange dots */
      if(p==='deposits'){
        ctx.fillStyle='rgba(251,146,60,0.65)';
        [[0.30,0.45],[0.65,0.35],[0.50,0.68],[0.72,0.60],[0.40,0.75]].forEach(function(d,i){
          var ox=sx+d[0]*TW*scale, oy=sy+d[1]*TH*scale;
          ctx.beginPath();ctx.arc(ox,oy,Math.max(1,1.4*scale),0,Math.PI*2);ctx.fill();
        });
      }
      /* volcanic: radial red glow from center */
      if(p==='volcanic'){
        var cx2=sx+hw,cy2=sy+hh;
        var gr=ctx.createRadialGradient(cx2,cy2,0,cx2,cy2,hw*0.9);
        gr.addColorStop(0,'rgba(239,68,68,0.28)');
        gr.addColorStop(1,'rgba(239,68,68,0)');
        ctx.fillStyle=gr;ctx.fill();
      }
      /* oasis: green radial glow from center */
      if(p==='oasis'){
        var cx3=sx+hw,cy3=sy+hh;
        var gr2=ctx.createRadialGradient(cx3,cy3,0,cx3,cy3,hw*0.7);
        gr2.addColorStop(0,'rgba(74,222,128,0.35)');
        gr2.addColorStop(1,'rgba(74,222,128,0)');
        ctx.fillStyle=gr2;ctx.fill();
      }
      ctx.restore();
    });
  }

  /* Pick a terrain tile name deterministically from TERRAIN_TILE variants array */
  function tileFor(terrain,vc,vr){
    var v=TERRAIN_TILE[terrain]; if(!v||!v.length) return null;
    return v[(Math.abs(vc||0)*3+Math.abs(vr||0)*7)%v.length];
  }

  /* Terrain-aware diamond: canvas gradient base + tipsy PNG texture + proximity overlays.
     vc,vr are grid coords used for deterministic tile variant selection. */
  function drawTerrainDiamond(sx,sy,terrain,prox,isHov,isSel,vc,vr){
    var hw=(TW/2)*scale,hh=(TH/2)*scale;
    var sc=TERRAIN_SCHEME[terrain]||TERRAIN_SCHEME.prairie;
    var base=isSel?shade(sc.c,50):isHov?shade(sc.c,25):sc.c;
    var glow=isSel?'#f59e0b':isHov?'#60a5fa':null;
    if(glow){ctx.save();ctx.shadowColor=glow;ctx.shadowBlur=14*scale;}
    ctx.beginPath();
    ctx.moveTo(sx+hw,sy); ctx.lineTo(sx+hw*2,sy+hh);
    ctx.lineTo(sx+hw,sy+hh*2); ctx.lineTo(sx,sy+hh);
    ctx.closePath();
    /* diagonal NW→SE gradient simulates isometric top-left light source */
    var gr=ctx.createLinearGradient(sx,sy,sx+hw*2,sy+hh*2);
    gr.addColorStop(0,shade(base,20)); gr.addColorStop(0.5,base); gr.addColorStop(1,shade(base,-25));
    ctx.fillStyle=gr; ctx.fill();
    ctx.strokeStyle=sc.s; ctx.lineWidth=0.5; ctx.stroke();
    if(glow) ctx.restore();
    /* overlay the tipsy terrain tile for real texture if loaded */
    var tn=tileFor(terrain,vc,vr); if(tn) drawTileOverlay(sx,sy,tn,0.65);
    drawProxOverlay(sx,sy,prox);
  }

  /* Draw a tile sprite clipped to the isometric diamond at (sx,sy) */
  function drawTileOverlay(sx,sy,name,alpha){
    var img=tileImgs[name];
    if(!img||!img.complete||!img.naturalWidth) return;
    var hw=(TW/2)*scale,hh=(TH/2)*scale;
    ctx.save();
    ctx.globalAlpha=alpha||0.5;
    ctx.beginPath();
    ctx.moveTo(sx+hw,sy); ctx.lineTo(sx+hw*2,sy+hh);
    ctx.lineTo(sx+hw,sy+hh*2); ctx.lineTo(sx,sy+hh);
    ctx.closePath();
    ctx.clip();
    ctx.drawImage(img,sx,sy,TW*scale,TH*scale);
    ctx.restore();
  }

  /* grid: smallest N in {8,16,32} where N*N >= plot count */
  function gridSz(n){ var s=8; while(s*s<n&&s<32) s*=2; return s; }

  /* plot-col to visual-col (road lanes inserted every BLOCK cols) */
  function p2v(pc){ return pc+Math.floor(pc/BLOCK); }
  function totalVC(gs){ return p2v(gs-1)+1; }
  function isRd(v){ return v%(BLOCK+1)===BLOCK; }
  function v2p(vc){ return vc-Math.floor(vc/(BLOCK+1)); }

  function g2s(vc,vr){
    return {sx:(vc-vr)*(TW/2)*scale+offX, sy:(vc+vr)*(TH/2)*scale+offY};
  }

  function drawDiamond(sx,sy,color,glow){
    var hw=(TW/2)*scale,hh=(TH/2)*scale;
    if(glow){ctx.save();ctx.shadowColor=glow;ctx.shadowBlur=14*scale;}
    ctx.beginPath();
    ctx.moveTo(sx+hw,sy); ctx.lineTo(sx+hw*2,sy+hh);
    ctx.lineTo(sx+hw,sy+hh*2); ctx.lineTo(sx,sy+hh);
    ctx.closePath();
    ctx.fillStyle=color; ctx.fill();
    ctx.strokeStyle='rgba(0,0,0,0.22)'; ctx.lineWidth=0.5; ctx.stroke();
    if(glow) ctx.restore();
  }

  /* isometric-city anchor formula: dy = sy + TH*scale - sh + sh*0.15 */
  function drawSprite(sx,sy,name){
    var img=imgs[name];
    if(!img||!img.complete||!img.naturalWidth) return;
    var ratio=img.naturalHeight/img.naturalWidth;
    var sw=TW*scale*1.2;
    var sh=Math.min(sw*ratio, sw*3.5);
    var hw=(TW/2)*scale;
    ctx.drawImage(img, sx+hw-sw/2, sy+TH*scale-sh+sh*0.15, sw, sh);
  }

  function drawDecorSprite(sx,sy,name,alpha){
    var img=tileImgs[name];
    if(!img||!img.complete||!img.naturalWidth) return;
    var ratio=img.naturalHeight/img.naturalWidth;
    var sw=TW*scale;
    var sh=Math.min(sw*ratio,sw*2.5);
    var hw=(TW/2)*scale;
    ctx.save();
    ctx.globalAlpha=alpha||0.88;
    ctx.drawImage(img,sx+hw-sw/2,sy+TH*scale-sh+sh*0.1,sw,sh);
    ctx.restore();
  }

  function decorFor(terrain,vc,vr){
    var h=Math.abs(vc*5+vr*11);
    if(/forest|jungle/.test(terrain))   return 'decor_tree'+((h%6)+1);
    if(/prairie|hills|marsh/.test(terrain)) return h%2?'decor_bush2':'decor_bush1';
    if(/savanna|island/.test(terrain))  return h%3?'decor_bush1':'decor_bush2';
    if(/coastal/.test(terrain))         return h%5?'decor_bush'+(h%2+1):'decor_tent';
    return null;
  }

  function drawRoad(sx,sy,cross,vc,vr){
    drawDiamond(sx,sy,cross?'#1f2937':'#2d3748');
    drawTileOverlay(sx,sy,'dirt'+tileVar(vc||0,vr||0),0.20);
    if(!cross){
      var hw=(TW/2)*scale,hh=(TH/2)*scale;
      ctx.save();
      ctx.strokeStyle='rgba(253,224,71,0.32)';
      ctx.lineWidth=Math.max(0.6,0.7*scale);
      ctx.setLineDash([3*scale,4*scale]);
      ctx.beginPath();
      ctx.moveTo(sx+hw*0.58,sy+hh*1.52); ctx.lineTo(sx+hw*1.42,sy+hh*0.48);
      ctx.stroke(); ctx.setLineDash([]); ctx.restore();
    }
  }

  function drawWater(sx,sy,vc,vr){
    drawDiamond(sx,sy,'#071828');
    drawTileOverlay(sx,sy,'iso_water2',0.78);
    var ph=(vc*0.6+vr*0.4+_waveT*0.7)%(Math.PI*2);
    var a=0.05+0.04*Math.sin(ph);
    var hw=(TW/2)*scale,hh=(TH/2)*scale;
    ctx.save();
    var gr=ctx.createLinearGradient(sx+hw*0.2,sy+hh,sx+hw*1.8,sy+hh);
    gr.addColorStop(0,'rgba(56,189,248,0)');
    gr.addColorStop(0.5,'rgba(56,189,248,'+a+')');
    gr.addColorStop(1,'rgba(56,189,248,0)');
    ctx.beginPath();
    ctx.moveTo(sx+hw,sy); ctx.lineTo(sx+hw*2,sy+hh);
    ctx.lineTo(sx+hw,sy+hh*2); ctx.lineTo(sx,sy+hh);
    ctx.closePath();
    ctx.fillStyle=gr; ctx.fill();
    ctx.restore();
  }

  var cv,ctx,plots=[],contacts=[],imgs={},scale=1,offX=0,offY=0;
  var dragSX=0,dragSY=0,dragOX=0,dragOY=0,didDrag=false;
  var hovId=-1,hovCI=-1,hovCPi=-1,swapAIdx=-1,swapMode=false;
  var selfId=-1,viewingId=-1;
  var _cache={key:'',items:null},_islands=null;
  var C_GAP=3;
  var _mpModal=null; /* cached once on first use */
  var _waveT=0;     /* Date.now()/1000 set once per render frame */

  var _waveAF=null, _waveLast=0;
  function _waveLoop(ts){
    if(!cv||(_mpModal||(_mpModal=document.getElementById('mpModal'))).style.display==='none'){_waveAF=null;return;}
    if(ts-_waveLast>83){_waveLast=ts;render();}
    _waveAF=requestAnimationFrame(_waveLoop);
  }
  function startWaveAnim(){if(!_waveAF)_waveAF=requestAnimationFrame(_waveLoop);}

  /* Compute (and cache) the layout of contact islands.
     Each island sits to the right of the player grid, separated by C_GAP water tiles.
     baseVc is the leftmost visual column of the contact's grid. */
  function getIslands(){
    if(_islands) return _islands;
    var gs=gridSz(plots.length||1), tv=totalVC(gs);
    var nextVc=tv+C_GAP;
    _islands=contacts.map(function(c,ci){
      var cgs=gridSz(c.plots.length||1), ctv=totalVC(cgs);
      var isl={ci:ci,c:c,cgs:cgs,ctv:ctv,baseVc:nextVc};
      nextVc+=ctv+C_GAP;
      return isl;
    });
    return _islands;
  }

  function getItems(){
    var gs=gridSz(plots.length||1), tv=totalVC(gs);
    var ckey=gs+'_'+contacts.length;
    if(_cache.key===ckey) return _cache.items;
    var islands=getIslands();
    var dtVcB=getDtVcBase(gs);
    var items=[];

    /* Scene bounds */
    var vcLo=-1;
    var vcHi=islands.length>0
      ? islands[islands.length-1].baseVc+islands[islands.length-1].ctv
      : tv;
    var maxCtv=islands.reduce(function(m,isl){return Math.max(m,isl.ctv);},tv);
    var vrLo=DT_VR_TOP-1, vrHi=maxCtv+1;

    /* Downtown tile lookup */
    var dtMap={};
    DOWNTOWN.forEach(function(d){
      dtMap[(dtVcB+d.col)+','+(DT_VR_TOP+d.row)]={d:d};
    });
    dtMap[(dtVcB+1)+','+(DT_VR_TOP+1)]={park:true};

    /* Quick vc → island lookup */
    var islByVc={};
    islands.forEach(function(isl){
      for(var v=isl.baseVc;v<isl.baseVc+isl.ctv;v++) islByVc[v]=isl;
    });

    for(var vr2=vrLo;vr2<=vrHi;vr2++){
      for(var vc2=vcLo;vc2<=vcHi;vc2++){
        var depth=vc2+vr2;
        /* outer border */
        if(vc2===vcLo||vc2===vcHi||vr2===vrLo||vr2===vrHi){
          items.push({t:'water',vc:vc2,vr:vr2,depth:depth}); continue;
        }
        /* player island (vc 0..tv-1) */
        if(vc2>=0&&vc2<tv){
          if(vr2<0){
            var key=vc2+','+vr2, e=dtMap[key];
            if(e) items.push(e.park?{t:'park',vc:vc2,vr:vr2,depth:depth}:{t:'down',vc:vc2,vr:vr2,depth:depth,d:e.d});
            else  items.push({t:'water',vc:vc2,vr:vr2,depth:depth});
            continue;
          }
          if(vr2===0){items.push({t:'road',vc:vc2,vr:0,depth:depth});continue;}
          if(vr2>=1&&vr2<=tv){
            var rc=isRd(vc2),rr=isRd(vr2-1);
            if(rc||rr){items.push({t:rc&&rr?'cross':'road',vc:vc2,vr:vr2,depth:depth});}
            else{var pi=v2p(vr2-1)*gs+v2p(vc2);items.push({t:'cell',vc:vc2,vr:vr2,depth:depth,pi:pi<plots.length?pi:-1});}
            continue;
          }
          items.push({t:'water',vc:vc2,vr:vr2,depth:depth}); continue;
        }
        /* contact island */
        var isl=islByVc[vc2];
        if(isl){
          var lvc=vc2-isl.baseVc;
          if(vr2===0){items.push({t:'road',vc:vc2,vr:0,depth:depth});continue;}
          if(vr2>=1&&vr2<=isl.ctv){
            var crc=isRd(lvc),crr=isRd(vr2-1);
            if(crc||crr){items.push({t:crc&&crr?'cross':'road',vc:vc2,vr:vr2,depth:depth});}
            else{
              var cpi=v2p(vr2-1)*isl.cgs+v2p(lvc);
              items.push({t:'cplot',vc:vc2,vr:vr2,depth:depth,ci:isl.ci,cpi:cpi<isl.c.plots.length?cpi:-1});
            }
            continue;
          }
          items.push({t:'water',vc:vc2,vr:vr2,depth:depth}); continue;
        }
        items.push({t:'water',vc:vc2,vr:vr2,depth:depth});
      }
    }

    items.sort(function(a,b){return a.depth-b.depth;});
    _cache={key:ckey,items:items};
    return items;
  }

  function render(){
    if(!cv||!ctx) return;
    _waveT=Date.now()/1000;
    var W=cv.offsetWidth,H=cv.offsetHeight;
    var grad=ctx.createLinearGradient(0,0,0,H);
    grad.addColorStop(0,'#010912'); grad.addColorStop(0.6,'#040e1c'); grad.addColorStop(1,'#030a06');
    ctx.fillStyle=grad; ctx.fillRect(0,0,W,H);

    var items=getItems();
    var islands=getIslands();
    var hw0=(TW/2)*scale,hh0=(TH/2)*scale;
    var cullM=TW*scale*4;

    items.forEach(function(it){
      var s=g2s(it.vc,it.vr);
      if(s.sx+hw0*2<-cullM||s.sx>W+cullM||s.sy+hh0*2<-cullM||s.sy>H+cullM) return;

      if(it.t==='water'){ drawWater(s.sx,s.sy,it.vc,it.vr); return; }
      if(it.t==='cross'){ drawRoad(s.sx,s.sy,true,it.vc,it.vr); return; }
      if(it.t==='road') { drawRoad(s.sx,s.sy,false,it.vc,it.vr); return; }

      /* contact island tile */
      if(it.t==='cplot'){
        var isl=islands[it.ci];
        var cp=it.cpi>=0?isl.c.plots[it.cpi]:null;
        var isHovC=(hovCI===it.ci&&hovCPi===it.cpi&&it.cpi>=0);
        if(cp) drawTerrainDiamond(s.sx,s.sy,cp.terrain,cp.proximity,isHovC,false,it.vc,it.vr);
        else drawDiamond(s.sx,s.sy,'#0d1a0d',null);
        if(cp&&cp.biz_type){var csp=spriteFor(cp.biz_type,cp.biz_class);if(csp)drawSprite(s.sx,s.sy,csp);}
        else if(cp){var cdec=decorFor(cp.terrain,it.vc,it.vr);if(cdec)drawDecorSprite(s.sx,s.sy,cdec);}
        if(!cp){
          ctx.save();ctx.globalAlpha=0.08;ctx.strokeStyle='#38bdf8';ctx.lineWidth=0.5;
          var hw2c=(TW/2)*scale,hh2c=(TH/2)*scale;
          ctx.beginPath();ctx.moveTo(s.sx+hw2c,s.sy);ctx.lineTo(s.sx+hw2c,s.sy+hh2c*2);ctx.stroke();
          ctx.restore();
        }
        return;
      }
      if(it.t==='park') {
        drawDiamond(s.sx,s.sy,'#14532d');
        drawSprite(s.sx,s.sy,'park');
        return;
      }
      if(it.t==='down') {
        drawDiamond(s.sx,s.sy,'#1e2d4a');
        if(it.d&&it.d.sprite) drawSprite(s.sx,s.sy,it.d.sprite);
        if(it.d&&scale>=0.45){
          ctx.save();
          ctx.font='bold '+Math.max(7,Math.round(8*scale))+'px sans-serif';
          ctx.fillStyle='rgba(148,163,184,0.88)';
          ctx.textAlign='center';
          var hw_d=(TW/2)*scale;
          ctx.fillText(it.d.label,s.sx+hw_d,(s.sy+TH*2*scale)+2);
          ctx.textAlign='left';
          ctx.restore();
        }
        return;
      }

      if(it.pi<0){
        drawDiamond(s.sx,s.sy,'#101a10');
        ctx.save(); ctx.globalAlpha=0.1; ctx.strokeStyle='#4ade80'; ctx.lineWidth=0.5;
        ctx.beginPath();
        var hw2=(TW/2)*scale,hh2=(TH/2)*scale;
        ctx.moveTo(s.sx+hw2,s.sy); ctx.lineTo(s.sx+hw2,s.sy+hh2*2); ctx.stroke();
        ctx.restore(); return;
      }

      var p=plots[it.pi];
      var isHov=(hovId===it.pi), isSel=(swapAIdx===it.pi);
      drawTerrainDiamond(s.sx,s.sy,p.terrain,p.proximity,isHov,isSel,it.vc,it.vr);

      if(p.biz_type){
        var spr=spriteFor(p.biz_type,p.biz_class);
        if(spr) drawSprite(s.sx,s.sy,spr);
      } else {
        var dec=decorFor(p.terrain,it.vc,it.vr);
        if(dec) drawDecorSprite(s.sx,s.sy,dec);
      }
      if(isSel&&swapMode){
        ctx.fillStyle='rgba(245,158,11,0.7)';
        ctx.font='bold '+Math.max(10,Math.round(13*scale))+'px sans-serif';
        ctx.textAlign='center';
        ctx.fillText('⇄',s.sx+(TW/2)*scale,s.sy+(TH/2)*scale*0.9);
        ctx.textAlign='left';
      }
    });

    /* second pass: contact island name labels (pill above road separator) */
    islands.forEach(function(isl){
      var lvc=isl.baseVc+(isl.ctv-1)/2, lvr=-0.4;
      var s=g2s(lvc,lvr);
      var hw=(TW/2)*scale;
      var lbl=isl.c.player_name;
      ctx.save();
      ctx.font='bold '+Math.max(9,Math.round(11*scale))+'px sans-serif';
      var tw=ctx.measureText(lbl).width;
      var ph=Math.max(14,Math.round(16*scale));
      var px=s.sx+hw-tw/2-6, py=s.sy-ph/2;
      ctx.fillStyle='rgba(14,30,60,0.88)';
      ctx.beginPath();
      ctx.rect(px,py,tw+12,ph);
      ctx.fill();
      ctx.strokeStyle='rgba(56,189,248,0.35)';ctx.lineWidth=1;ctx.stroke();
      ctx.fillStyle='#7dd3fc';
      ctx.textAlign='center';
      ctx.textBaseline='middle';
      ctx.fillText(lbl,s.sx+hw,s.sy+1);
      ctx.textAlign='left';ctx.textBaseline='alphabetic';
      ctx.restore();
    });

    /* "no plots" notice drawn in centre of player grid when grid is empty */
    if(!plots.length){
      var gs0=gridSz(1),tv0=totalVC(gs0),midVc0=(tv0-1)/2,midVr0=(tv0+1)/2;
      var ps=g2s(midVc0,midVr0);
      ctx.save();
      ctx.font='13px sans-serif';
      ctx.fillStyle='rgba(71,85,105,0.85)';
      ctx.textAlign='center';ctx.textBaseline='middle';
      ctx.fillText('No plots yet — visit Land Market',ps.sx+(TW/2)*scale,ps.sy+(TH/2)*scale);
      ctx.textAlign='left';ctx.textBaseline='alphabetic';
      ctx.restore();
    }

    if(swapMode){
      ctx.fillStyle='rgba(0,0,0,0.65)'; ctx.fillRect(0,0,W,26);
      ctx.fillStyle='#fbbf24'; ctx.font='bold 12px sans-serif'; ctx.textAlign='center';
      ctx.fillText(swapAIdx>=0?'Now click another plot to swap with it  ·  Esc to cancel'
        :'Click any plot to pick it up for swapping  ·  Esc to cancel',W/2,17);
      ctx.textAlign='left';
    }
  }

  function preloadSprites(cb){
    var needed={park:1};
    plots.forEach(function(p){if(p.biz_type){var s=spriteFor(p.biz_type,p.biz_class);if(s)needed[s]=1;}});
    DOWNTOWN.forEach(function(d){if(d.sprite)needed[d.sprite]=1;});
    contacts.forEach(function(c){c.plots.forEach(function(p){if(p.biz_type){var s=spriteFor(p.biz_type,p.biz_class);if(s)needed[s]=1;}});});
    var keys=Object.keys(needed);
    /* also load tile texture images: water/dirt/tile + all tipsy terrain variants */
    var TILES=[
      'tile1','tile2','tile3','water1','water2','water3','dirt1','dirt2','dirt3',
      'terrain_grass','terrain_grass_v2','terrain_grass_v3','terrain_grass_v4','terrain_grass_v5',
      'terrain_arid','terrain_arid2','terrain_arid3','terrain_arid_v2','terrain_arid_v3','terrain_arid_v4',
      'terrain_savanna','terrain_savanna2','terrain_savanna3','terrain_savanna_v2','terrain_savanna_v3',
      'terrain_snow','terrain_snow2','terrain_snow3','terrain_snow_v2','terrain_snow_v3','terrain_snow_v4',
      'terrain_water_a','terrain_water_b',
      'decor_bush1','decor_bush2','decor_tent',
      'decor_tree1','decor_tree2','decor_tree3','decor_tree4','decor_tree5','decor_tree6'
    ];
    /* iso assets served from /assets/iso/ — keyed with 'iso_' prefix */
    var ISO_TILES={'iso_water2':'water2.png'};
    var pending=0;
    function _onImg(){if(--pending===0)cb();}
    keys.forEach(function(k){
      if(imgs[k]&&imgs[k].complete&&imgs[k].naturalWidth>0) return;
      pending++;
      var img=new Image(); img.onload=img.onerror=_onImg;
      img.src=SPRITE_BASE+k+'.png'; imgs[k]=img;
    });
    TILES.forEach(function(k){
      if(tileImgs[k]&&tileImgs[k].complete&&tileImgs[k].naturalWidth>0) return;
      pending++;
      var img=new Image(); img.onload=img.onerror=_onImg;
      img.src=TILE_BASE+k+'.png'; tileImgs[k]=img;
    });
    Object.keys(ISO_TILES).forEach(function(k){
      if(tileImgs[k]&&tileImgs[k].complete&&tileImgs[k].naturalWidth>0) return;
      pending++;
      var img=new Image(); img.onload=img.onerror=_onImg;
      img.src=ISO_BASE+ISO_TILES[k]; tileImgs[k]=img;
    });
    if(pending===0) cb();
  }

  function resizeCv(){
    if(!cv||!ctx) return;
    var dpr=window.devicePixelRatio||1;
    cv.width=cv.offsetWidth*dpr; cv.height=cv.offsetHeight*dpr;
    ctx.scale(dpr,dpr);
  }

  window.mpReset=function(){
    if(!cv) return;
    resizeCv();
    var gs=gridSz(plots.length||1), tv=totalVC(gs);
    var islands=getIslands();
    var W=cv.offsetWidth, H=cv.offsetHeight;
    var vcLo=-1;
    var vcHi=islands.length>0
      ? islands[islands.length-1].baseVc+islands[islands.length-1].ctv
      : tv;
    var maxCtv=islands.reduce(function(m,isl){return Math.max(m,isl.ctv);},tv);
    var vrLo=DT_VR_TOP-1, vrHi=maxCtv+1;
    var vcSpan=vcHi-vcLo, vrSpan=vrHi-vrLo;
    var isoW=(vcSpan+vrSpan)*TW/2, isoH=(vcSpan+vrSpan)*TH/2;
    var fit=Math.min(W/isoW, H/isoH)*0.85;
    scale=Math.max(0.1, Math.min(1.8, fit));
    var midVc=(vcLo+vcHi)/2, midVr=(vrLo+vrHi)/2;
    offX=W/2-(midVc-midVr)*(TW/2)*scale;
    offY=H/2-(midVc+midVr)*(TH/2)*scale;
    render();
  };

  window.mpZoom=function(f){
    var W=cv.offsetWidth,H=cv.offsetHeight,cx=W/2,cy=H/2;
    offX=cx-(cx-offX)*f; offY=cy-(cy-offY)*f;
    scale=Math.max(0.2,Math.min(4,scale*f)); render();
  };

  function hitTest(mx,my){
    var gs=gridSz(plots.length||1), tv=totalVC(gs);
    var hwh=(TW/2)*scale, hhh=(TH/2)*scale;
    var dtVcB=getDtVcBase(gs);
    var islands=getIslands();
    /* downtown */
    for(var di=0;di<DOWNTOWN.length;di++){
      var d=DOWNTOWN[di];
      var s=g2s(dtVcB+d.col,DT_VR_TOP+d.row);
      var ddx=mx-(s.sx+hwh),ddy=my-(s.sy+hhh);
      if(Math.abs(ddx/hwh)+Math.abs(ddy/hhh)<=1) return {downtown:d};
    }
    /* contact islands (iterate in reverse so foreground beats background) */
    for(var ii=islands.length-1;ii>=0;ii--){
      var isl=islands[ii];
      for(var cvr=isl.ctv;cvr>=1;cvr--){
        for(var cvc=isl.ctv-1;cvc>=0;cvc--){
          if(isRd(cvc)||isRd(cvr-1)) continue;
          var cs=g2s(isl.baseVc+cvc,cvr);
          var cdx=mx-(cs.sx+hwh),cdy=my-(cs.sy+hhh);
          if(Math.abs(cdx/hwh)+Math.abs(cdy/hhh)<=1){
            var cpi=v2p(cvr-1)*isl.cgs+v2p(cvc);
            return {contact:isl.c,ci:ii,cpi:cpi,cplot:cpi<isl.c.plots.length?isl.c.plots[cpi]:null};
          }
        }
      }
    }
    /* player grid */
    for(var vr=tv;vr>=1;vr--){
      for(var vc=tv-1;vc>=0;vc--){
        if(isRd(vc)||isRd(vr-1)) continue;
        var s2=g2s(vc,vr);
        var dx2=mx-(s2.sx+hwh),dy2=my-(s2.sy+hhh);
        if(Math.abs(dx2/hwh)+Math.abs(dy2/hhh)<=1){
          var pi=v2p(vr-1)*gs+v2p(vc);
          if(pi<plots.length) return {plot:plots[pi],pi:pi};
          return {govt:true};
        }
      }
    }
    return null;
  }

  function showInfo(hit){
    var panel=document.getElementById('mpInfo');
    var html='';
    if(!hit||hit.govt){
      html='<strong style="color:#64748b;">Government Land</strong>'
        +'<div style="color:#475569;margin-top:6px;font-size:0.7rem;">'
        +'<a href="/land-market" style="color:#38bdf8;">Browse Land Market →</a></div>';
    } else if(hit.downtown){
      var d=hit.downtown;
      html='<strong style="color:#60a5fa;">'+d.label+'</strong>'
        +(d.url?'<div style="margin-top:6px;"><a href="'+d.url
          +'" style="color:#38bdf8;font-size:0.72rem;">Open →</a></div>':'');
    } else if(hit.contact){
      var cp=hit.cplot, c=hit.contact;
      html='<strong style="color:#38bdf8;">'+c.player_name+'</strong>';
      if(cp){
        html+='<div style="color:#64748b;font-size:0.68rem;text-transform:capitalize;margin-top:2px;">'+cp.terrain+'</div>';
        if(cp.proximity&&cp.proximity.length)
          html+='<div style="font-size:0.62rem;color:#475569;margin-top:1px;">'
            +cp.proximity.map(function(x){return x.replace(/_/g,' ');}).join(' · ')+'</div>';
        if(cp.biz_name) html+='<div style="color:#4ade80;margin-top:4px;">'+cp.biz_name+'</div>'
          +'<div style="color:#64748b;font-size:0.68rem;text-transform:capitalize;">'+cp.biz_class+'</div>';
        else html+='<div style="color:#475569;margin-top:4px;">Vacant</div>';
        html+='<div style="margin-top:8px;padding-top:8px;border-top:1px solid #1e293b;font-size:0.68rem;color:#64748b;">'
          +'Eff <span style="color:#cbd5e1;">'+cp.efficiency+'%</span>'
          +' &emsp; Tax <span style="color:#cbd5e1;">$'+cp.monthly_tax+'/mo</span></div>';
      }
      html+='<button onclick="openMyProperties('+c.player_id+')" style="margin-top:10px;width:100%;'
        +'background:#0f2040;border:1px solid #38bdf8;color:#7dd3fc;padding:4px;'
        +'border-radius:4px;cursor:pointer;font-size:0.7rem;">🏙️ View '+c.player_name+"'s Properties</button>";
    } else {
      var p=hit.plot;
      html='<div style="display:flex;justify-content:space-between;align-items:baseline;">'
        +'<strong style="color:#f59e0b;">Plot #'+p.id+'</strong>'
        +'<span style="font-size:0.62rem;color:#475569;text-transform:capitalize;">'
        +p.terrain+'</span></div>';
      if(p.proximity&&p.proximity.length)
        html+='<div style="font-size:0.62rem;color:#64748b;margin-top:1px;">'
          +p.proximity.map(function(x){return x.replace(/_/g,' ');}).join(' · ')+'</div>';
      if(p.biz_name){
        html+='<div style="color:#4ade80;margin-top:4px;">'+p.biz_name+'</div>'
          +'<div style="color:#64748b;font-size:0.68rem;text-transform:capitalize;">'+p.biz_class+'</div>';
      } else {
        html+='<div style="color:#475569;margin-top:4px;">Vacant</div>';
      }
      html+='<div style="margin-top:8px;padding-top:8px;border-top:1px solid #1e293b;'
        +'font-size:0.68rem;color:#64748b;">'
        +'Eff <span style="color:#cbd5e1;">'+p.efficiency+'%</span>'
        +' &emsp; Tax <span style="color:#cbd5e1;">$'+p.monthly_tax+'/mo</span></div>';
      if(viewingId===selfId){
        html+='<button onclick="mpStartSwapFrom('+hit.pi+')" style="margin-top:8px;width:100%;'
          +'background:#1e293b;border:1px solid #334155;color:#fbbf24;padding:4px;'
          +'border-radius:4px;cursor:pointer;font-size:0.7rem;">⇄ Swap This Plot</button>';
      }
    }
    document.getElementById('mpInfoContent').innerHTML=html;
    panel.style.display='block';
  }

  window.mpStartSwapFrom=function(pi){
    document.getElementById('mpInfo').style.display='none';
    swapMode=true; swapAIdx=pi;
    document.getElementById('mpMoveHint').style.display='';
    document.getElementById('mpSwapBtn').style.display='none';
    render();
  };

  function cancelSwap(){
    swapMode=false; swapAIdx=-1;
    document.getElementById('mpMoveHint').style.display='none';
    if(viewingId===selfId) document.getElementById('mpSwapBtn').style.display='';
    render();
  }

  window.mpEnterSwapMode=function(){
    swapMode=true; swapAIdx=-1;
    document.getElementById('mpMoveHint').style.display='';
    document.getElementById('mpSwapBtn').style.display='none';
    document.getElementById('mpInfo').style.display='none';
    render();
  };

  /* Visual-only swap: swap all display data between two plot indices */
  function doSwap(idxA, idxB){
    var a=plots[idxA], b=plots[idxB];
    var tmp={terrain:a.terrain,proximity:a.proximity,biz_type:a.biz_type,biz_name:a.biz_name,biz_class:a.biz_class};
    a.terrain=b.terrain; a.proximity=b.proximity; a.biz_type=b.biz_type; a.biz_name=b.biz_name; a.biz_class=b.biz_class;
    b.terrain=tmp.terrain; b.proximity=tmp.proximity; b.biz_type=tmp.biz_type; b.biz_name=tmp.biz_name; b.biz_class=tmp.biz_class;
    cancelSwap();
  }

  window.openMyProperties=function(pid){
    selfId=window._SELF_ID||0; viewingId=pid||selfId;
    document.getElementById('mpModal').style.display='flex';
    cv=document.getElementById('mpCanvas');
    ctx=cv.getContext('2d');
    swapMode=false; swapAIdx=-1; hovId=-1;
    _cache={key:'',items:null};
    document.getElementById('mpInfo').style.display='none';
    document.getElementById('mpMoveHint').style.display='none';
    document.getElementById('mpSwapBtn').style.display='none';
    document.getElementById('mpTitle').textContent='Loading…';
    document.getElementById('mpCount').textContent='';
    fetch('/api/my-properties'+(pid&&pid!==selfId?'?player_id='+pid:''))
      .then(function(r){return r.json();})
      .then(function(d){
        if(d.error){alert('Could not load: '+d.error);return;}
        plots=d.plots; contacts=d.contacts||[]; _cache={key:'',items:null}; _islands=null;
        document.getElementById('mpTitle').textContent=
          (viewingId===selfId?'My':d.player_name+"'s")+' Properties';
        var pStr=plots.length+' plot'+(plots.length===1?'':'s');
        var cStr=contacts.length?(' · '+contacts.length+' contact'+(contacts.length===1?'':'s')):'';
        document.getElementById('mpCount').textContent=pStr+cStr;
        if(viewingId===selfId) document.getElementById('mpSwapBtn').style.display='';
        mpReset();
        preloadSprites(function(){render();startWaveAnim();});
        mpRadioSync();
        wireEvents();
      });
  };

  window.closeMpModal=function(){
    document.getElementById('mpModal').style.display='none';
    swapMode=false; swapAIdx=-1; hovCI=-1; hovCPi=-1;
    if(_waveAF){cancelAnimationFrame(_waveAF);_waveAF=null;}
    if(cv) cv._wired=false;
  };

  var _tt=null;
  function showTip(hit,mx,my){
    if(!_tt) _tt=document.getElementById('mpTooltip');
    var html='';
    if(hit.plot){
      var p=hit.plot;
      html='<span style="color:#f59e0b;font-weight:600;">'
        +p.terrain.charAt(0).toUpperCase()+p.terrain.slice(1).replace(/_/g,' ')+'</span>';
      if(p.proximity&&p.proximity.length)
        html+='<br><span style="color:#94a3b8;font-size:0.65rem;">'
          +p.proximity.map(function(x){return x.replace(/_/g,' ');}).join(' · ')+'</span>';
      html+=p.biz_name
        ?'<br><span style="color:#4ade80;">'+p.biz_name+'</span>'
        :'<br><span style="color:#475569;">Vacant</span>';
      html+='<br><span style="color:#64748b;font-size:0.65rem;">click for details</span>';
    } else if(hit.downtown){
      html='<span style="color:#60a5fa;">'+hit.downtown.label+'</span>'
        +'<br><span style="color:#64748b;font-size:0.65rem;">click to open</span>';
    } else if(hit.contact){
      var cp=hit.cplot;
      html='<span style="color:#38bdf8;font-weight:600;">'+hit.contact.player_name+'</span>';
      if(cp) html+=cp.biz_name
        ?'<br><span style="color:#4ade80;">'+cp.biz_name+'</span>'
        :'<br><span style="color:#475569;">Vacant</span>';
      html+='<br><span style="color:#64748b;font-size:0.65rem;">click for details</span>';
    } else if(hit.govt){
      html='<span style="color:#475569;">Government land</span>';
    }
    _tt.innerHTML=html;
    _tt.style.display='block';
    _tt.style.left=Math.min(mx+12,window.innerWidth-180)+'px';
    _tt.style.top =Math.min(my+10,window.innerHeight-70)+'px';
  }
  function hideTip(){ if(_tt) _tt.style.display='none'; }

  function wireEvents(){
    if(cv._wired) return;
    cv._wired=true;

    cv.addEventListener('mousedown',function(e){
      didDrag=false; dragSX=e.clientX; dragSY=e.clientY; dragOX=offX; dragOY=offY;
    });
    window.addEventListener('mouseup',function(e){
      if(!didDrag&&e.target===cv){
        var rect=cv.getBoundingClientRect();
        var mx=e.clientX-rect.left, my=e.clientY-rect.top;
        var hit=hitTest(mx,my);
        if(swapMode){
          if(hit&&hit.plot&&hit.pi!==undefined){
            if(swapAIdx<0){
              swapAIdx=hit.pi; render();
            } else if(hit.pi===swapAIdx){
              cancelSwap();
            } else {
              doSwap(swapAIdx,hit.pi);
            }
          } else {
            cancelSwap();
          }
        } else {
          if(hit){ showInfo(hit); if(hit.plot) hovId=hit.pi; }
          else document.getElementById('mpInfo').style.display='none';
        }
      }
      didDrag=false; cv.style.cursor='grab';
    });

    cv.addEventListener('mousemove',function(e){
      var dx=e.clientX-dragSX, dy=e.clientY-dragSY;
      if(e.buttons&&(Math.abs(dx)>3||Math.abs(dy)>3)){
        didDrag=true; offX=dragOX+dx; offY=dragOY+dy;
        cv.style.cursor='grabbing'; render();
      } else if(!didDrag){
        var rect=cv.getBoundingClientRect();
        var mx=e.clientX-rect.left, my=e.clientY-rect.top;
        var hit=hitTest(mx,my);
        var nh=(hit&&hit.plot&&hit.pi!==undefined)?hit.pi:-1;
        var nci=(hit&&hit.contact)?hit.ci:-1;
        var ncpi=(hit&&hit.contact)?hit.cpi:-1;
        if(nh!==hovId||nci!==hovCI||ncpi!==hovCPi){hovId=nh;hovCI=nci;hovCPi=ncpi;render();}
        if(hit) showTip(hit,e.clientX,e.clientY);
        else hideTip();
      }
    });

    cv.addEventListener('mouseleave',function(){hovId=-1;hideTip();render();});

    cv.addEventListener('wheel',function(e){
      e.preventDefault();
      var rect=cv.getBoundingClientRect();
      var mx=e.clientX-rect.left, my=e.clientY-rect.top;
      var f=e.deltaY<0?1.12:1/1.12;
      offX=mx-(mx-offX)*f; offY=my-(my-offY)*f;
      scale=Math.max(0.2,Math.min(4,scale*f)); render();
    },{passive:false});

    var t0=null;
    cv.addEventListener('touchstart',function(e){
      if(e.touches.length===1)
        t0={x:e.touches[0].clientX,y:e.touches[0].clientY,ox:offX,oy:offY};
    },{passive:true});
    cv.addEventListener('touchmove',function(e){
      if(e.touches.length===1&&t0){
        offX=t0.ox+(e.touches[0].clientX-t0.x);
        offY=t0.oy+(e.touches[0].clientY-t0.y); render();
      }
    },{passive:true});

    window.addEventListener('resize',function(){resizeCv();mpReset();});
    document.addEventListener('keydown',function(e){
      if(e.key==='Escape'){if(swapMode)cancelSwap();else closeMpModal();}
    });
  }

  /* ── Mini radio bar bridging to shell player ──────────────────────────── */
  function mpRadioSync(){
    /* mirror station label from shell bar if it exists */
    var sname=document.getElementById('gsbar-sname');
    var title=document.getElementById('gs-title');
    var mps=document.getElementById('mpRadioSname');
    var mpt=document.getElementById('mpRadioTitle');
    var knob=document.getElementById('mpRadioKnob');
    var klbl=document.getElementById('mpRadioKlbl');
    var pp=document.getElementById('mpRadioPP');
    if(sname&&mps) mps.textContent=sname.textContent;
    if(title&&mpt) mpt.textContent=title.textContent;
    var isWcpr=(localStorage.getItem('wadsStation')==='wcpr');
    if(knob) knob.style.transform='translateX(-50%) rotate('+(isWcpr?'0':'180')+'deg)';
    if(klbl) klbl.textContent=isWcpr?'WCPR':'WLOL';
    var shellAudio=document.getElementById(isWcpr?'wcpr-shell-audio':'gs-audio');
    if(pp) pp.innerHTML=(shellAudio&&!shellAudio.paused)?'&#9646;&#9646;':'&#9658;';
  }

  window.mpRadioPlay=function(){
    try{ window.gsBarPlay(); }catch(e){}
    setTimeout(mpRadioSync,200);
  };
  window.mpRadioSkip=function(){
    try{ window.gsBarSkip(); }catch(e){}
    setTimeout(mpRadioSync,400);
  };
  window.mpRadioTune=function(){
    try{ window.gsBarTune(); }catch(e){}
    setTimeout(mpRadioSync,600);
  };
  window.mpRadioSetVol=function(v){
    try{ window.gsSetVolume(v); }catch(e){}
  };

  /* keep title in sync while modal is open */
  setInterval(function(){
    if(document.getElementById('mpModal').style.display!=='none') mpRadioSync();
  },2000);

})();
</script>
"""


@router.get("/world-map", response_class=HTMLResponse)
def world_map(session_token: Optional[str] = Cookie(None)):
    player = _require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player

    body = f"""
<div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;margin-bottom:4px;">
  <a href="/" style="color:#38bdf8;">&larr; Dashboard</a>
  <button onclick="openMyProperties({player.id})"
     style="background:linear-gradient(135deg,#1e40af,#7c3aed);border:none;color:#f1f5f9;
            padding:8px 18px;border-radius:6px;cursor:pointer;font-weight:700;font-size:0.82rem;
            display:flex;align-items:center;gap:6px;">
    🏙️ My Properties
  </button>
</div>
<h1 style="margin:4px 0 4px 0;">🗺️ World Map</h1>
<p style="color:#64748b;margin-bottom:24px;">
  Live overview of all land, districts, cities, and counties in Wadsworth.
</p>
{_build_world_map(player)}
{_MY_PROPS_MODAL}
<script>var _SELF_ID={player.id}; window._tkCategories=['land'];</script>
"""
    from ux import shell
    return HTMLResponse(shell("World Map", body, player.cash_balance, player.id))
