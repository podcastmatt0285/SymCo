"""
world_map_ux.py — World Map page (/world-map)

Shows a live political atlas of the Wadsworth game world:
  - World stats (total plots, districts, cities, counties)
  - Terrain distribution (plot counts by terrain type)
  - County → City hierarchy with crypto info and member counts
  - Independent cities (not yet in a county)
"""

from typing import Optional
from fastapi import APIRouter, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse

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


@router.get("/world-map", response_class=HTMLResponse)
def world_map(session_token: Optional[str] = Cookie(None)):
    player = _require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player

    body = f"""
<a href="/" style="color:#38bdf8;">&larr; Dashboard</a>
<h1 style="margin:8px 0 4px 0;">🗺️ World Map</h1>
<p style="color:#64748b;margin-bottom:24px;">
  Live overview of all land, districts, cities, and counties in Wadsworth.
</p>
{_build_world_map(player)}
"""
    from ux import shell
    return HTMLResponse(shell("World Map", body, player.cash_balance, player.id))
