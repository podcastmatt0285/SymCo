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
        player_name = getattr(target, "username", None) or f"Player {target_id}"
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
            plots_out.append({
                "id":          p.id,
                "terrain":     p.terrain_type,
                "efficiency":  round(p.efficiency or 0, 1),
                "monthly_tax": round(p.monthly_tax or 0, 2),
                "biz_type":    biz["type"]  if biz else None,
                "biz_name":    biz["name"]  if biz else None,
                "biz_class":   biz["class"] if biz else None,
            })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

    return JSONResponse({"player_id": target_id, "player_name": player_name, "plots": plots_out})


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

  var TERRAIN_COLOR={
    urban:'#64748b', prairie:'#86efac', forest:'#16a34a', desert:'#fbbf24',
    marsh:'#22d3ee', mountain:'#94a3b8', tundra:'#bae6fd', jungle:'#4ade80',
    savanna:'#d97706', hills:'#a3e635', island:'#f472b6', coastal:'#60a5fa',
    ocean:'#1e40af', lake:'#38bdf8',
    district_food:'#f97316', district_hospital:'#ec4899', district_industrial:'#f59e0b',
    district_medical:'#a78bfa', district_neighborhood:'#34d399', district_transport:'#60a5fa',
  };

  function spriteFor(t,cls){
    if(!t) return null;
    if(/mine|alluvial|quarry|mineral/.test(t))           return 'warehouse';
    if(/solar|power_plant|powerplant/.test(t))           return 'powerplant';
    if(/water_facility|water_tower|watertower/.test(t))  return 'watertower';
    if(/plantation|cotton|agave|apiary|pasture|paddock|farm|field|orchard/.test(t)) return 'park';
    if(/lumber|timber|logging/.test(t))                  return 'park_medium';
    if(/hospital|clinic|medical|infirmary/.test(t))      return 'hospital';
    if(/university|college/.test(t))                     return 'university';
    if(/school|academy/.test(t))                         return 'school';
    if(/police/.test(t))                                 return 'police_station';
    if(/fire_station|firehouse/.test(t))                 return 'fire_station';
    if(/airport|aviation/.test(t))                       return 'airport';
    if(/stadium|arena|coliseum/.test(t))                 return 'stadium';
    if(/warehouse|storage|depot|silo/.test(t))           return 'warehouse';
    if(/grocery|supermarket|market|mall/.test(t))        return 'shop_medium';
    if(/shop|store|boutique|kiosk|stationery|arts_and_crafts/.test(t)) return 'shop_small';
    if(/refinery|factory|mill|foundry|plant|smelter|distillery|brewery|winery|cannery|processing/.test(t)) return 'industrial';
    if(/ritual|church|temple|shrine/.test(t))            return 'space';
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

  function drawRoad(sx,sy,cross){
    drawDiamond(sx,sy,cross?'#1f2937':'#2d3748');
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

  function drawWater(sx,sy){
    drawDiamond(sx,sy,'#0c2340');
    var hw=(TW/2)*scale,hh=(TH/2)*scale;
    ctx.save(); ctx.globalAlpha=0.22; ctx.fillStyle='#38bdf8';
    ctx.beginPath();
    ctx.ellipse(sx+hw,sy+hh, hw*0.5,hh*0.35, 0,0,Math.PI*2);
    ctx.fill(); ctx.globalAlpha=1; ctx.restore();
  }

  var cv,ctx,plots=[],imgs={},scale=1,offX=0,offY=0;
  var dragSX=0,dragSY=0,dragOX=0,dragOY=0,didDrag=false;
  var hovId=-1,swapAIdx=-1,swapMode=false;
  var selfId=-1,viewingId=-1;
  var _cache={gs:-1,items:null};

  function getItems(){
    var gs=gridSz(plots.length||1);
    if(_cache.gs===gs) return _cache.items;
    var tv=totalVC(gs);
    var dtVcB=getDtVcBase(gs);
    var items=[];

    /* Build downtown lookup: "vc,vr" → {d:building} | {park:true} */
    var dtMap={};
    DOWNTOWN.forEach(function(d){
      dtMap[(dtVcB+d.col)+','+(DT_VR_TOP+d.row)]={d:d};
    });
    /* centre tile = park */
    dtMap[(dtVcB+1)+','+(DT_VR_TOP+1)]={park:true};

    /* Full bounding box — every cell is explicitly assigned a tile type.
       This eliminates bare canvas gaps around the downtown block.
       vcLo/vcHi and vrLo/vrHi are the water-border edge rows/cols. */
    var vcLo=-1, vcHi=tv;
    var vrLo=DT_VR_TOP-1, vrHi=tv+1; /* one row above downtown, one below grid */

    for(var vr2=vrLo;vr2<=vrHi;vr2++){
      for(var vc2=vcLo;vc2<=vcHi;vc2++){
        var depth=vc2+vr2;
        /* outer border → water */
        if(vc2===vcLo||vc2===vcHi||vr2===vrLo||vr2===vrHi){
          items.push({t:'water',vc:vc2,vr:vr2,depth:depth}); continue;
        }
        /* downtown zone (vr < 0) */
        if(vr2<0){
          var key=vc2+','+vr2, e=dtMap[key];
          if(e){
            items.push(e.park
              ?{t:'park',vc:vc2,vr:vr2,depth:depth}
              :{t:'down',vc:vc2,vr:vr2,depth:depth,d:e.d});
          } else {
            items.push({t:'water',vc:vc2,vr:vr2,depth:depth});
          }
          continue;
        }
        /* road separator (vr=0) */
        if(vr2===0){ items.push({t:'road',vc:vc2,vr:0,depth:depth}); continue; }
        /* player grid (vr≥1) */
        var rc=isRd(vc2),rr=isRd(vr2-1);
        if(rc||rr){
          items.push({t:rc&&rr?'cross':'road',vc:vc2,vr:vr2,depth:depth});
        } else {
          var pi=v2p(vr2-1)*gs+v2p(vc2);
          items.push({t:'cell',vc:vc2,vr:vr2,depth:depth,pi:pi<plots.length?pi:-1});
        }
      }
    }

    items.sort(function(a,b){return a.depth-b.depth;});
    _cache={gs:gs,items:items};
    return items;
  }

  function render(){
    if(!cv||!ctx) return;
    var W=cv.offsetWidth,H=cv.offsetHeight;
    var grad=ctx.createLinearGradient(0,0,0,H);
    grad.addColorStop(0,'#010912'); grad.addColorStop(0.6,'#040e1c'); grad.addColorStop(1,'#030a06');
    ctx.fillStyle=grad; ctx.fillRect(0,0,W,H);

    if(!plots.length){
      ctx.fillStyle='#475569';ctx.font='16px sans-serif';ctx.textAlign='center';
      ctx.fillText('No plots owned.',W/2,H/2);ctx.textAlign='left';
      return;
    }

    var items=getItems();
    var hw0=(TW/2)*scale,hh0=(TH/2)*scale;
    var cullM=TW*scale*4;

    items.forEach(function(it){
      var s=g2s(it.vc,it.vr);
      if(s.sx+hw0*2<-cullM||s.sx>W+cullM||s.sy+hh0*2<-cullM||s.sy>H+cullM) return;

      if(it.t==='water'){ drawWater(s.sx,s.sy); return; }
      if(it.t==='cross'){ drawDiamond(s.sx,s.sy,'#1f2937'); return; }
      if(it.t==='road') { drawRoad(s.sx,s.sy,false); return; }
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
      var color=TERRAIN_COLOR[p.terrain]||'#86efac';
      var isHov=(hovId===it.pi), isSel=(swapAIdx===it.pi);
      drawDiamond(s.sx,s.sy,
        isSel?shade(color,50):isHov?shade(color,25):color,
        isSel?'#f59e0b':isHov?'#60a5fa':null);

      if(p.biz_type){
        var spr=spriteFor(p.biz_type,p.biz_class);
        if(spr) drawSprite(s.sx,s.sy,spr);
      }
      if(isSel&&swapMode){
        ctx.fillStyle='rgba(245,158,11,0.7)';
        ctx.font='bold '+Math.max(10,Math.round(13*scale))+'px sans-serif';
        ctx.textAlign='center';
        ctx.fillText('⇄',s.sx+(TW/2)*scale,s.sy+(TH/2)*scale*0.9);
        ctx.textAlign='left';
      }
    });

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
    var keys=Object.keys(needed),pending=0;
    keys.forEach(function(k){
      if(imgs[k]&&imgs[k].complete&&imgs[k].naturalWidth>0) return;
      pending++;
      var img=new Image();
      img.onload=img.onerror=function(){if(--pending===0)cb();};
      img.src=SPRITE_BASE+k+'.png'; imgs[k]=img;
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
    var W=cv.offsetWidth, H=cv.offsetHeight;
    /* scene spans vc=[vcLo..vcHi], vr=[vrLo..vrHi] where vcLo=-1,vcHi=tv,vrLo=DT_VR_TOP-1,vrHi=tv+1
       iso screen extent = (vcHi+vrHi - vcLo - vrLo) for both W and H (diamond):
       isoW = ((tv-(-1)) + (tv+1 - (DT_VR_TOP-1))) * TW/2 = (tv+1 + tv-DT_VR_TOP+2) * TW/2
       Simplified: fit to canvas using total tile spans */
    var vcSpan=tv+2, vrSpan=tv-DT_VR_TOP+2; /* DT_VR_TOP negative so this is tv+DT_N+2 */
    var isoW=(vcSpan+vrSpan)*TW/2, isoH=(vcSpan+vrSpan)*TH/2;
    var fit=Math.min(W/isoW, H/isoH)*0.85;
    scale=Math.max(0.15, Math.min(1.8, fit));
    /* geometric centre of bounding box → screen centre */
    var midVc=((-1)+tv)/2, midVr=((DT_VR_TOP-1)+(tv+1))/2;
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
    /* downtown tiles (8 buildings — park center is not interactive) */
    for(var di=0;di<DOWNTOWN.length;di++){
      var d=DOWNTOWN[di];
      var s=g2s(dtVcB+d.col, DT_VR_TOP+d.row);
      var ddx=mx-(s.sx+hwh), ddy=my-(s.sy+hhh);
      if(Math.abs(ddx/hwh)+Math.abs(ddy/hhh)<=1) return {downtown:d};
    }
    /* player grid: vr=1..tv */
    for(var vr=tv;vr>=1;vr--){
      for(var vc=tv-1;vc>=0;vc--){
        if(isRd(vc)||isRd(vr-1)) continue;
        var s2=g2s(vc,vr);
        var dx2=mx-(s2.sx+hwh), dy2=my-(s2.sy+hhh);
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
    } else {
      var p=hit.plot;
      html='<div style="display:flex;justify-content:space-between;align-items:baseline;">'
        +'<strong style="color:#f59e0b;">Plot #'+p.id+'</strong>'
        +'<span style="font-size:0.62rem;color:#475569;text-transform:capitalize;">'
        +p.terrain+'</span></div>';
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
    var tmp={terrain:a.terrain,biz_type:a.biz_type,biz_name:a.biz_name,biz_class:a.biz_class};
    a.terrain=b.terrain; a.biz_type=b.biz_type; a.biz_name=b.biz_name; a.biz_class=b.biz_class;
    b.terrain=tmp.terrain; b.biz_type=tmp.biz_type; b.biz_name=tmp.biz_name; b.biz_class=tmp.biz_class;
    cancelSwap();
  }

  window.openMyProperties=function(pid){
    selfId=window._SELF_ID||0; viewingId=pid||selfId;
    document.getElementById('mpModal').style.display='flex';
    cv=document.getElementById('mpCanvas');
    ctx=cv.getContext('2d');
    swapMode=false; swapAIdx=-1; hovId=-1;
    _cache={gs:-1,items:null};
    document.getElementById('mpInfo').style.display='none';
    document.getElementById('mpMoveHint').style.display='none';
    document.getElementById('mpSwapBtn').style.display='none';
    document.getElementById('mpTitle').textContent='Loading…';
    document.getElementById('mpCount').textContent='';
    fetch('/api/my-properties'+(pid&&pid!==selfId?'?player_id='+pid:''))
      .then(function(r){return r.json();})
      .then(function(d){
        if(d.error){alert('Could not load: '+d.error);return;}
        plots=d.plots; _cache={gs:-1,items:null};
        document.getElementById('mpTitle').textContent=
          (viewingId===selfId?'My':d.player_name+"'s")+' Properties';
        document.getElementById('mpCount').textContent=
          plots.length+' plot'+(plots.length===1?'':'s');
        if(viewingId===selfId) document.getElementById('mpSwapBtn').style.display='';
        mpReset();
        preloadSprites(function(){render();});
        mpRadioSync();
        wireEvents();
      });
  };

  window.closeMpModal=function(){
    document.getElementById('mpModal').style.display='none';
    swapMode=false; swapAIdx=-1;
    if(cv) cv._wired=false;
  };

  var _tt=null;
  function showTip(hit,mx,my){
    if(!_tt) _tt=document.getElementById('mpTooltip');
    var html='';
    if(hit.plot){
      var p=hit.plot;
      html='<span style="color:#f59e0b;font-weight:600;">'
        +p.terrain.charAt(0).toUpperCase()+p.terrain.slice(1)+'</span>';
      html+=p.biz_name
        ?'<br><span style="color:#4ade80;">'+p.biz_name+'</span>'
        :'<br><span style="color:#475569;">Vacant</span>';
      html+='<br><span style="color:#64748b;font-size:0.65rem;">click for details</span>';
    } else if(hit.downtown){
      html='<span style="color:#60a5fa;">'+hit.downtown.label+'</span>'
        +'<br><span style="color:#64748b;font-size:0.65rem;">click to open</span>';
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
        if(nh!==hovId){hovId=nh;render();}
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
