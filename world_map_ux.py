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
<div id="mpModal" style="display:none;position:fixed;inset:0;z-index:9999;background:rgba(0,0,0,.88);
     flex-direction:column;align-items:stretch;">
  <div style="display:flex;align-items:center;justify-content:space-between;padding:10px 16px;
              background:#0a0f1a;border-bottom:1px solid #1e293b;flex-shrink:0;flex-wrap:wrap;gap:6px;">
    <div>
      <span id="mpTitle" style="font-size:1rem;font-weight:700;color:#f1f5f9;">My Properties</span>
      <span id="mpCount" style="font-size:0.75rem;color:#64748b;margin-left:10px;"></span>
      <span id="mpMoveHint" style="display:none;font-size:0.72rem;color:#f59e0b;
            margin-left:12px;background:#451a03;padding:2px 8px;border-radius:4px;">
        Move mode — click an empty plot to place, Esc to cancel
      </span>
    </div>
    <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;">
      <button id="mpMoveBuildingBtn" onclick="mpEnterMoveMode()"
              style="display:none;background:#1e293b;border:1px solid #334155;color:#fbbf24;
                     padding:4px 10px;border-radius:4px;cursor:pointer;font-size:0.72rem;">
        📦 Move Building
      </button>
      <button onclick="mpZoom(1.2)" style="background:#1e293b;border:none;color:#94a3b8;
              padding:4px 10px;border-radius:4px;cursor:pointer;font-size:1rem;">+</button>
      <button onclick="mpZoom(1/1.2)" style="background:#1e293b;border:none;color:#94a3b8;
              padding:4px 10px;border-radius:4px;cursor:pointer;font-size:1rem;">−</button>
      <button onclick="mpReset()" style="background:#1e293b;border:none;color:#94a3b8;
              padding:4px 10px;border-radius:4px;cursor:pointer;font-size:0.72rem;">Reset</button>
      <button onclick="closeMpModal()" style="background:#7f1d1d;border:none;color:#fca5a5;
              padding:4px 12px;border-radius:4px;cursor:pointer;font-weight:bold;">✕</button>
    </div>
  </div>
  <canvas id="mpCanvas" style="flex:1;width:100%;cursor:grab;touch-action:none;display:block;"></canvas>
  <div id="mpTooltip" style="display:none;position:fixed;background:#0f172a;border:1px solid #334155;
       border-radius:6px;padding:8px 12px;font-size:0.75rem;color:#e2e8f0;pointer-events:none;
       max-width:200px;z-index:10000;line-height:1.6;"></div>
</div>

<script>
(function(){
  /* ── constants ── */
  var TW=64, TH=38, COLS=8;
  var SPRITE_BASE='/static/iso/buildings/';

  /* ── downtown buildings shown below player plots ── */
  var DOWNTOWN=[
    {label:'Commodity\nMarket', sprite:'commercial',     col:0},
    {label:'District\nMarket',  sprite:'shop_medium',    col:1},
    {label:'Land\nRegistry',    sprite:'mansion',        col:2},
    {label:'Stock\nExchange',   sprite:'university',     col:3},
    {label:'City Hall',         sprite:'mansion',        col:4},
    {label:'Reserve\nBank',     sprite:'commercial',     col:5},
  ];

  /* ── terrain colours ── */
  var TERRAIN_COLOR={
    urban:'#64748b', prairie:'#86efac', forest:'#16a34a', desert:'#fbbf24',
    marsh:'#22d3ee', mountain:'#94a3b8', tundra:'#bae6fd', jungle:'#4ade80',
    savanna:'#d97706', hills:'#a3e635', island:'#f472b6', coastal:'#60a5fa',
    ocean:'#1e40af', lake:'#38bdf8',
    district_food:'#f97316', district_hospital:'#ec4899', district_industrial:'#f59e0b',
    district_medical:'#a78bfa', district_neighborhood:'#34d399', district_transport:'#60a5fa',
  };

  /* ── sprite picker ── */
  function spriteFor(t, cls){
    if(!t) return null;
    if(/mine|alluvial|quarry|mineral/.test(t))                       return 'warehouse';
    if(/solar|power_plant|powerplant/.test(t))                       return 'powerplant';
    if(/water_facility|water_tower|watertower/.test(t))              return 'watertower';
    if(/plantation|cotton|agave|apiary|pasture|paddock|farm|field|orchard/.test(t)) return 'park';
    if(/lumber|timber|logging/.test(t))                              return 'park_medium';
    if(/hospital|clinic|medical|infirmary/.test(t))                  return 'hospital';
    if(/university|college/.test(t))                                 return 'university';
    if(/school|academy/.test(t))                                     return 'school';
    if(/police/.test(t))                                             return 'police_station';
    if(/fire_station|firehouse/.test(t))                             return 'fire_station';
    if(/airport|aviation/.test(t))                                   return 'airport';
    if(/stadium|arena|coliseum/.test(t))                             return 'stadium';
    if(/warehouse|storage|depot|silo/.test(t))                       return 'warehouse';
    if(/grocery|supermarket|market|mall/.test(t))                    return 'shop_medium';
    if(/shop|store|boutique|kiosk|stationery|arts_and_crafts/.test(t)) return 'shop_small';
    if(/refinery|factory|mill|foundry|plant|smelter|distillery|brewery|winery|cannery|processing/.test(t)) return 'industrial';
    if(/ritual|church|temple|shrine/.test(t))                        return 'space';
    if(cls==='retail') return 'shop_medium';
    return 'industrial';
  }

  /* ── shade helper ── */
  function shade(hex,amt){
    var n=parseInt(hex.slice(1),16);
    var r=Math.min(255,Math.max(0,(n>>16)+amt));
    var g=Math.min(255,Math.max(0,((n>>8)&0xff)+amt));
    var b=Math.min(255,Math.max(0,(n&0xff)+amt));
    return '#'+((1<<24)|(r<<16)|(g<<8)|b).toString(16).slice(1);
  }

  /* ── state ── */
  var cv,ctx,plots=[],imgs={},scale=1,offX=0,offY=0;
  var dragActive=false,dragSX=0,dragSY=0,dragOX=0,dragOY=0,didDrag=false;
  var hovId=-1;
  var moveMode=false,selId=-1;
  var selfId=-1,viewingId=-1;

  /* ── layout helpers ── */
  function nRows(){ return Math.ceil((plots.length||1)/COLS); }
  function roadRow(){ return nRows(); }
  function downRow(){ return nRows()+1; }
  function plotCoord(i){ return {col:i%COLS, row:Math.floor(i/COLS)}; }

  /* ── iso math ── */
  function g2s(col,row){
    return {sx:(col-row)*(TW/2)*scale+offX, sy:(col+row)*(TH/2)*scale+offY};
  }

  /* ── draw helpers ── */
  function drawDiamond(sx,sy,color){
    var hw=(TW/2)*scale,hh=(TH/2)*scale;
    ctx.beginPath();
    ctx.moveTo(sx+hw,sy);
    ctx.lineTo(sx+hw*2,sy+hh);
    ctx.lineTo(sx+hw,sy+hh*2);
    ctx.lineTo(sx,sy+hh);
    ctx.closePath();
    ctx.fillStyle=color; ctx.fill();
    ctx.strokeStyle='rgba(0,0,0,0.18)'; ctx.lineWidth=0.5; ctx.stroke();
  }

  function drawSprite(sx,sy,name){
    var img=imgs[name];
    if(!img||!img.complete||!img.naturalWidth) return;
    var hw=(TW/2)*scale,hh=(TH/2)*scale;
    var sh=img.naturalHeight/img.naturalWidth*TW*scale*1.6;
    var sw=TW*scale*1.1;
    ctx.drawImage(img,sx+hw-sw/2,sy+hh*2-sh,sw,sh);
  }

  /* ── render ── */
  function render(){
    if(!cv||!ctx) return;
    var W=cv.offsetWidth,H=cv.offsetHeight;
    ctx.clearRect(0,0,W,H);

    if(!plots.length){
      ctx.fillStyle='#475569'; ctx.font='16px sans-serif'; ctx.textAlign='center';
      ctx.fillText('No plots owned.',W/2,H/2); ctx.textAlign='left';
      return;
    }

    /* build draw list */
    var items=[];
    plots.forEach(function(p,i){
      var c=plotCoord(i);
      items.push({type:'plot',p:p,col:c.col,row:c.row,depth:c.col+c.row});
    });
    var rr=roadRow();
    for(var rc=0;rc<COLS;rc++) items.push({type:'road',col:rc,row:rr,depth:rc+rr});
    var dr=downRow();
    DOWNTOWN.forEach(function(d){
      items.push({type:'down',d:d,col:d.col,row:dr,depth:d.col+dr});
    });
    items.sort(function(a,b){return a.depth-b.depth;});

    items.forEach(function(it){
      var s=g2s(it.col,it.row);
      var hw=(TW/2)*scale,hh=(TH/2)*scale;

      if(it.type==='road'){
        drawDiamond(s.sx,s.sy,'#374151');
        ctx.save();
        ctx.strokeStyle='rgba(253,224,71,0.45)';
        ctx.lineWidth=Math.max(1,scale);
        ctx.setLineDash([3*scale,4*scale]);
        ctx.beginPath();
        /* dashes running NW→SE (col direction) across tile centre */
        ctx.moveTo(s.sx+hw*0.55,s.sy+hh*1.55);
        ctx.lineTo(s.sx+hw*1.45,s.sy+hh*0.45);
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.restore();
        return;
      }

      if(it.type==='down'){
        drawDiamond(s.sx,s.sy,'#1e293b');
        if(it.d.sprite) drawSprite(s.sx,s.sy,it.d.sprite);
        if(scale>0.5){
          ctx.save();
          ctx.font='bold '+Math.round(9*scale)+'px sans-serif';
          ctx.textAlign='center';
          ctx.fillStyle='rgba(148,163,184,0.92)';
          var lines=it.d.label.split('\n');
          var lx=s.sx+hw, ly=s.sy-4*scale;
          lines.forEach(function(ln,li){
            ctx.fillText(ln,lx,ly+li*11*scale);
          });
          ctx.restore();
        }
        return;
      }

      /* player plot */
      var p=it.p;
      var color=TERRAIN_COLOR[p.terrain]||'#86efac';
      var isHov=(hovId===p.id);
      var isSel=(selId===p.id);

      if(isHov||isSel){
        ctx.save();
        ctx.shadowColor=isSel?'#f59e0b':'#60a5fa';
        ctx.shadowBlur=14*scale;
      }
      drawDiamond(s.sx,s.sy,isSel?shade(color,40):isHov?shade(color,20):color);
      if(isHov||isSel) ctx.restore();

      if(p.biz_type&&!(moveMode&&isSel)){
        var spr=spriteFor(p.biz_type,p.biz_class);
        if(spr) drawSprite(s.sx,s.sy,spr);
      }

      /* selection "lift" icon */
      if(isSel&&moveMode){
        ctx.fillStyle='#f59e0b'; ctx.font='bold '+Math.round(14*scale)+'px sans-serif';
        ctx.textAlign='center';
        ctx.fillText('↑',s.sx+hw,s.sy+hh);
        ctx.textAlign='left';
      }
    });

    /* move mode banner */
    if(moveMode){
      ctx.fillStyle='rgba(0,0,0,0.55)';
      ctx.fillRect(0,0,W,26);
      ctx.fillStyle='#fbbf24'; ctx.font='bold 12px sans-serif'; ctx.textAlign='center';
      ctx.fillText('Click an empty plot to place  ·  Esc to cancel',W/2,17);
      ctx.textAlign='left';
    }
  }

  /* ── preload sprites ── */
  function preloadSprites(cb){
    var needed={};
    plots.forEach(function(p){
      if(p.biz_type){var s=spriteFor(p.biz_type,p.biz_class); if(s) needed[s]=1;}
    });
    DOWNTOWN.forEach(function(d){if(d.sprite) needed[d.sprite]=1;});
    var keys=Object.keys(needed), pending=0;
    keys.forEach(function(k){
      if(imgs[k]&&imgs[k].complete&&imgs[k].naturalWidth>0) return;
      pending++;
      var img=new Image();
      img.onload=img.onerror=function(){if(--pending===0) cb();};
      img.src=SPRITE_BASE+k+'.png';
      imgs[k]=img;
    });
    if(pending===0) cb();
  }

  /* ── resize canvas (DPR-correct) ── */
  function resizeCv(){
    if(!cv||!ctx) return;
    var dpr=window.devicePixelRatio||1;
    cv.width=cv.offsetWidth*dpr;
    cv.height=cv.offsetHeight*dpr;
    ctx.scale(dpr,dpr);
  }

  /* ── zoom ── */
  window.mpZoom=function(f){
    var W=cv.offsetWidth,H=cv.offsetHeight;
    var cx=W/2,cy=H/2;
    offX=cx-(cx-offX)*f; offY=cy-(cy-offY)*f;
    scale=Math.max(0.3,Math.min(4,scale*f));
    render();
  };

  /* ── reset ── */
  window.mpReset=function(){
    if(!cv) return;
    scale=1;
    var rows=nRows();
    var midCol=(COLS-1)/2, midRow=(rows-1)/2;
    offX=cv.offsetWidth/2  - (midCol-midRow)*(TW/2)*scale;
    offY=cv.offsetHeight/3 - (midCol+midRow)*(TH/2)*scale;
    render();
  };

  /* ── hit test ── */
  function plotAt(mx,my){
    for(var i=plots.length-1;i>=0;i--){
      var c=plotCoord(i),s=g2s(c.col,c.row);
      var hw=(TW/2)*scale,hh=(TH/2)*scale;
      var dx=mx-(s.sx+hw),dy=my-(s.sy+hh);
      if(Math.abs(dx/hw)+Math.abs(dy/hh)<=1) return i;
    }
    return -1;
  }

  /* ── tooltip ── */
  function showTip(p,mx,my){
    var tt=document.getElementById('mpTooltip');
    var html='<strong style="color:#f59e0b;">Plot #'+p.id+'</strong><br>'
      +'<span style="color:#94a3b8;">'+p.terrain+'</span><br>';
    if(moveMode&&selId===p.id){
      html+='<span style="color:#fbbf24;">Selected — pick a destination</span>';
    } else if(p.biz_name){
      html+='<span style="color:#4ade80;">'+p.biz_name+'</span><br>';
      if(viewingId===selfId) html+='<span style="color:#64748b;font-size:0.68rem;">Click to move building</span><br>';
      html+='Eff: '+p.efficiency+'%  Tax: $'+p.monthly_tax+'/mo';
    } else {
      html+='<span style="color:#475569;">Vacant</span>';
      if(moveMode) html+='<br><span style="color:#34d399;">Click to place here</span>';
    }
    tt.innerHTML=html;
    tt.style.display='block';
    tt.style.left=Math.min(mx+14,window.innerWidth-220)+'px';
    tt.style.top =Math.min(my+14,window.innerHeight-130)+'px';
  }
  function hideTip(){ document.getElementById('mpTooltip').style.display='none'; }

  /* ── move mode ── */
  window.mpEnterMoveMode=function(){
    moveMode=true; selId=-1;
    document.getElementById('mpMoveHint').style.display='';
    document.getElementById('mpMoveBuildingBtn').style.display='none';
    render();
  };
  function cancelMove(){
    moveMode=false; selId=-1;
    document.getElementById('mpMoveHint').style.display='none';
    if(viewingId===selfId)
      document.getElementById('mpMoveBuildingBtn').style.display='';
    render();
  }
  function doMove(fromId,toId){
    fetch('/api/move-business',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({from_plot_id:fromId,to_plot_id:toId})
    }).then(function(r){return r.json();}).then(function(d){
      if(d.error){alert('Move failed: '+d.error);return;}
      var fp=plots.find(function(p){return p.id===fromId;});
      var tp=plots.find(function(p){return p.id===toId;});
      if(fp&&tp){
        tp.biz_type=fp.biz_type; tp.biz_name=fp.biz_name; tp.biz_class=fp.biz_class;
        fp.biz_type=null; fp.biz_name=null; fp.biz_class=null;
      }
      cancelMove();
    });
  }

  /* ── open / close ── */
  window.openMyProperties=function(pid){
    selfId=window._SELF_ID||0; viewingId=pid||selfId;
    var modal=document.getElementById('mpModal');
    modal.style.display='flex';
    cv=document.getElementById('mpCanvas');
    ctx=cv.getContext('2d');
    moveMode=false; selId=-1; hovId=-1;
    document.getElementById('mpMoveHint').style.display='none';
    document.getElementById('mpMoveBuildingBtn').style.display='none';
    resizeCv();
    document.getElementById('mpTitle').textContent='Loading…';
    document.getElementById('mpCount').textContent='';
    fetch('/api/my-properties'+(pid&&pid!==selfId?'?player_id='+pid:''))
      .then(function(r){return r.json();})
      .then(function(d){
        if(d.error){alert('Could not load: '+d.error);return;}
        plots=d.plots;
        document.getElementById('mpTitle').textContent=
          (viewingId===selfId?'My':d.player_name+"'s")+' Properties';
        document.getElementById('mpCount').textContent=
          plots.length+' plot'+(plots.length===1?'':'s');
        if(viewingId===selfId)
          document.getElementById('mpMoveBuildingBtn').style.display='';
        mpReset();
        preloadSprites(function(){render();});
        wireEvents();
      });
  };

  window.closeMpModal=function(){
    document.getElementById('mpModal').style.display='none';
    moveMode=false; selId=-1;
    if(cv) cv._wired=false;
  };

  /* ── events ── */
  function wireEvents(){
    if(cv._wired) return;
    cv._wired=true;

    cv.addEventListener('mousedown',function(e){
      dragActive=true; didDrag=false;
      dragSX=e.clientX; dragSY=e.clientY; dragOX=offX; dragOY=offY;
    });
    window.addEventListener('mouseup',function(e){
      if(dragActive&&!didDrag){
        /* treat as click */
        var rect=cv.getBoundingClientRect();
        var mx=e.clientX-rect.left,my=e.clientY-rect.top;
        var idx=plotAt(mx,my);
        if(idx>=0){
          var p=plots[idx];
          if(moveMode){
            if(p.id===selId){ cancelMove(); }
            else if(!p.biz_type&&selId>=0){ doMove(selId,p.id); }
            else if(p.biz_type){ selId=p.id; render(); }
          } else if(p.biz_type&&viewingId===selfId){
            selId=p.id; moveMode=true;
            document.getElementById('mpMoveHint').style.display='';
            document.getElementById('mpMoveBuildingBtn').style.display='none';
            render();
          }
        } else {
          if(moveMode) cancelMove();
        }
      }
      dragActive=false; didDrag=false; cv.style.cursor='grab';
    });
    cv.addEventListener('mousemove',function(e){
      if(dragActive){
        var dx=e.clientX-dragSX,dy=e.clientY-dragSY;
        if(Math.abs(dx)>3||Math.abs(dy)>3){
          didDrag=true; offX=dragOX+dx; offY=dragOY+dy;
          cv.style.cursor='grabbing'; render();
        }
      } else {
        var rect=cv.getBoundingClientRect();
        var mx=e.clientX-rect.left,my=e.clientY-rect.top;
        var idx=plotAt(mx,my);
        var nh=idx>=0?plots[idx].id:-1;
        if(nh!==hovId){hovId=nh;render();}
        if(idx>=0) showTip(plots[idx],e.clientX,e.clientY);
        else hideTip();
      }
    });
    cv.addEventListener('mouseleave',function(){hovId=-1;hideTip();render();});

    cv.addEventListener('wheel',function(e){
      e.preventDefault();
      var rect=cv.getBoundingClientRect();
      var mx=e.clientX-rect.left,my=e.clientY-rect.top;
      var f=e.deltaY<0?1.12:1/1.12;
      offX=mx-(mx-offX)*f; offY=my-(my-offY)*f;
      scale=Math.max(0.3,Math.min(4,scale*f)); render();
    },{passive:false});

    var t0=null;
    cv.addEventListener('touchstart',function(e){
      if(e.touches.length===1) t0={x:e.touches[0].clientX,y:e.touches[0].clientY,ox:offX,oy:offY};
    },{passive:true});
    cv.addEventListener('touchmove',function(e){
      if(e.touches.length===1&&t0){
        offX=t0.ox+(e.touches[0].clientX-t0.x);
        offY=t0.oy+(e.touches[0].clientY-t0.y); render();
      }
    },{passive:true});

    window.addEventListener('resize',function(){resizeCv();render();});
    document.addEventListener('keydown',function(e){
      if(e.key==='Escape'){ if(moveMode) cancelMove(); else closeMpModal(); }
    });
  }

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
<script>var _SELF_ID={player.id};</script>
"""
    from ux import shell
    return HTMLResponse(shell("World Map", body, player.cash_balance, player.id))
