"""
world_map_ux.py

World Map feature for the Wadsworth Economic Simulation.
Provides a D3.js Voronoi-powered nested territory visualization on a black
background, showing the full county → city → district (company) → business
hierarchy as interlocking puzzle-shaped cells.

The /api/world-map/data endpoint (legacy) returns individual player assets
with geographic coordinates. The /api/world-map/territory endpoint returns
the complete nested world hierarchy used by the new SVG visualization.
"""

from typing import Optional
from fastapi import APIRouter, Cookie
from fastapi.responses import HTMLResponse, JSONResponse

router = APIRouter()

# ==========================
# GRID CONSTANTS
# ==========================

GRID_WIDTH = 100          # Plots wrap after this many columns

# ==========================
# MARYLAND GEOGRAPHIC MAPPING
# ==========================

# Northwest corner of the game's plot grid (plot ID #1 cell NW corner).
# This anchors the 100-wide × N-row plot grid to central Maryland.
PLOT_ORIGIN_LAT =  39.550   # degrees N
PLOT_ORIGIN_LNG = -77.100   # degrees W

# Size of each 1×1 plot cell in geographic degrees.
# ~111 m N-S, ~115 m E-W at 39°N latitude.
PLOT_DLAT = -0.001   # degrees per row (negative = southward)
PLOT_DLNG =  0.0015  # degrees per column (positive = eastward)

# Curated real Maryland city positions (lat, lng).
# Game city IDs cycle through this list.
MD_CITY_LATLON = [
    (39.2904, -76.6122),  # Baltimore
    (38.9784, -76.4922),  # Annapolis
    (39.4143, -77.4105),  # Frederick
    (39.0840, -77.1528),  # Rockville
    (39.1434, -77.2014),  # Gaithersburg
    (38.9426, -76.7313),  # Bowie
    (39.6418, -77.7200),  # Hagerstown
    (38.9807, -76.9369),  # College Park
    (38.3607, -75.5994),  # Salisbury
    (39.2037, -76.8610),  # Columbia
    (39.3526, -76.6188),  # Towson
    (39.0176, -76.9750),  # Greenbelt
    (38.6773, -76.0766),  # Cambridge
    (39.5293, -76.1641),  # Bel Air
    (39.5754, -77.0050),  # Westminster
    (39.4526, -77.9884),  # Cumberland
    (38.5284, -76.9750),  # La Plata
    (38.8073, -77.0469),  # Waldorf
    (38.9162, -76.5973),  # Upper Marlboro
    (38.8862, -76.9175),  # Laurel
]

# Curated Maryland county seat positions (lat, lng).
# Game county IDs cycle through this list.
MD_COUNTY_LATLON = [
    (39.0840, -77.1528),  # Montgomery County (Rockville)
    (38.8190, -76.7497),  # Prince George's County (Upper Marlboro)
    (39.4015, -76.6019),  # Baltimore County (Towson)
    (38.9784, -76.4922),  # Anne Arundel County (Annapolis)
    (39.2673, -76.7986),  # Howard County (Ellicott City)
    (39.4143, -77.4105),  # Frederick County (Frederick)
    (38.5284, -76.9750),  # Charles County (La Plata)
    (39.5351, -76.3488),  # Harford County (Bel Air)
    (39.5754, -77.0050),  # Carroll County (Westminster)
    (39.6418, -77.7200),  # Washington County (Hagerstown)
    (38.2912, -76.6275),  # St. Mary's County (Leonardtown)
    (38.3607, -75.5994),  # Wicomico County (Salisbury)
    (38.1754, -75.3854),  # Worcester County (Snow Hill)
    (38.5773, -76.0776),  # Dorchester County (Cambridge)
    (38.9178, -76.0679),  # Queen Anne's County (Centreville)
    (39.2072, -76.0677),  # Kent County (Chestertown)
    (39.6065, -75.8330),  # Cecil County (Elkton)
    (38.6029, -76.5924),  # Calvert County (Prince Frederick)
    (38.7743, -76.0765),  # Talbot County (Easton)
    (39.2904, -76.6122),  # Baltimore City
    (39.6487, -78.7634),  # Allegany County (Cumberland)
    (39.4076, -79.4069),  # Garrett County (Oakland)
    (38.8868, -75.8270),  # Caroline County (Denton)
]

# ==========================
# TERRAIN / DISTRICT COLOURS
# ==========================

TERRAIN_COLORS = {
    # Natural terrain
    "prairie":  "#22c55e",
    "forest":   "#16a34a",
    "desert":   "#f59e0b",
    "marsh":    "#0891b2",
    "mountain": "#78716c",
    "tundra":   "#94a3b8",
    "jungle":   "#15803d",
    "savanna":  "#ca8a04",
    "hills":    "#a16207",
    "island":   "#3b82f6",
    # District terrain types
    "district_aerospace":            "#6366f1",
    "district_airport":              "#38bdf8",
    "district_convention_center":    "#7c3aed",
    "district_education":            "#8b5cf6",
    "district_entertainment":        "#ec4899",
    "district_entertainment_district": "#db2777",
    "district_food":                 "#f97316",
    "district_food_court":           "#fb923c",
    "district_hospital":             "#14b8a6",
    "district_industrial":           "#64748b",
    "district_mall":                 "#a855f7",
    "district_mega_mall":            "#c026d3",
    "district_medical":              "#06b6d4",
    "district_military":             "#dc2626",
    "district_military_base":        "#dc2626",
    "district_neighborhood":         "#84cc16",
    "district_prison":               "#475569",
    "district_prison_complex":       "#475569",
    "district_research_campus":      "#7c3aed",
    "district_seaport":              "#0891b2",
    "district_shipyard":             "#0369a1",
    "district_tech":                 "#2563eb",
    "district_tech_park":            "#2563eb",
    "district_transport":            "#d97706",
    "district_utilities":            "#0284c7",
    "district_zoo":                  "#4ade80",
}

# District type display names
DISTRICT_NAMES = {
    "aerospace":           "Aerospace Complex",
    "education":           "Education Campus",
    "entertainment":       "Entertainment District",
    "food":                "Food Production Zone",
    "food_court":          "Food Court District",
    "hospital":            "Hospital District",
    "industrial":          "Industrial Zone",
    "mall":                "Shopping Mall District",
    "medical":             "Medical District",
    "military":            "Military District",
    "neighborhood":        "Neighborhood District",
    "prison":              "Prison Complex",
    "research_campus":     "Research Campus",
    "shipyard":            "Shipyard District",
    "tech":                "Tech Park",
    "transport":           "Transportation Hub",
    "utilities":           "Utilities Zone",
    "zoo":                 "Zoo & Wildlife District",
    "airport":             "Airport Complex",
    "mega_mall":           "Mega Mall District",
    "seaport":             "Seaport District",
    "convention_center":   "Convention Center",
    "entertainment_district": "Entertainment District",
}

# ==========================
# COORDINATE HELPERS
# ==========================

def _plot_pos(plot_id: int):
    """Return (lat, lng) of the NW corner of a land plot cell."""
    idx = plot_id - 1
    col = idx % GRID_WIDTH
    row = idx // GRID_WIDTH
    lat = PLOT_ORIGIN_LAT + row * PLOT_DLAT
    lng = PLOT_ORIGIN_LNG + col * PLOT_DLNG
    return lat, lng


def _district_center_and_bounds(district):
    """
    Derive a district's geographic centre (lat, lng) and bounding box
    [[sw_lat, sw_lng], [ne_lat, ne_lng]] from its source_plot_ids.

    The source plots are deleted at merge time, but their IDs are preserved
    in the district record, so we can recompute their original positions.

    Returns:
        center (lat, lng), bounds [[sw_lat, sw_lng], [ne_lat, ne_lng]]
    """
    if district.source_plot_ids:
        try:
            ids = [int(s.strip()) for s in district.source_plot_ids.split(",") if s.strip()]
            if ids:
                positions = [_plot_pos(pid) for pid in ids]
                lats = [p[0] for p in positions]
                lngs = [p[1] for p in positions]
                clat = sum(lats) / len(lats)
                clng = sum(lngs) / len(lngs)
                # Bounds extend by one plot cell to cover the full cell footprints
                sw = [min(lats) + PLOT_DLAT, min(lngs)]  # PLOT_DLAT<0 → more south
                ne = [max(lats), max(lngs) + PLOT_DLNG]
                return (clat, clng), [sw, ne]
        except Exception:
            pass
    # Fallback: place near the top of the plot grid
    fallback_lat = PLOT_ORIGIN_LAT + ((district.id - 1) % 10) * PLOT_DLAT * 3
    fallback_lng = PLOT_ORIGIN_LNG + ((district.id - 1) // 10) * PLOT_DLNG * 3
    margin = abs(PLOT_DLAT * 3)
    sw = [fallback_lat - margin, fallback_lng - margin * 1.5]
    ne = [fallback_lat + margin, fallback_lng + margin * 1.5]
    return (fallback_lat, fallback_lng), [sw, ne]


def _city_latlon(city_id: int):
    """Return (lat, lng) for a game city, mapped to a real Maryland city."""
    return MD_CITY_LATLON[(city_id - 1) % len(MD_CITY_LATLON)]


def _county_latlon(county_id: int):
    """Return (lat, lng) for a game county, mapped to a real Maryland county seat."""
    return MD_COUNTY_LATLON[(county_id - 1) % len(MD_COUNTY_LATLON)]


# ==========================
# HELPER FUNCTIONS
# ==========================

def require_auth(session_token):
    from auth import get_db, get_player_from_session
    from fastapi.responses import RedirectResponse
    db = get_db()
    player = get_player_from_session(db, session_token)
    db.close()
    if not player:
        return RedirectResponse(url="/login", status_code=303)
    return player


def shell(title: str, body: str, balance: float = 0.0, player_id: int = None) -> str:
    try:
        from ux import shell as ux_shell
        return ux_shell(title, body, balance, player_id)
    except Exception:
        return f"""<!DOCTYPE html><html><head>
        <title>{title} · Wadsworth</title>
        <style>body{{background:#020617;color:#e5e7eb;font-family:monospace;margin:0}}</style>
        </head><body>{body}</body></html>"""


# ==========================
# API: MAP DATA
# ==========================

@router.get("/api/world-map/data")
async def world_map_data(session_token: Optional[str] = Cookie(None)):
    """
    Return a JSON payload describing the authenticated player's entire economic
    empire: land plots, districts, cities, and counties with spatial coordinates.
    """
    from fastapi.responses import RedirectResponse
    from auth import get_db, get_player_from_session
    from land import LandPlot
    from districts import District
    from cities import City, CityMember
    from counties import County, CountyCity
    from business import Business, BUSINESS_TYPES

    db = get_db()
    try:
        player = get_player_from_session(db, session_token)
        if not player:
            return JSONResponse({"error": "Not authenticated"}, status_code=401)

        # ---- Land Plots --------------------------------------------------
        plots = db.query(LandPlot).filter(LandPlot.owner_id == player.id).all()

        # Batch-load businesses that occupy plots
        occ_plot_ids = [p.occupied_by_business_id for p in plots if p.occupied_by_business_id]
        biz_map = {}
        if occ_plot_ids:
            for b in db.query(Business).filter(Business.id.in_(occ_plot_ids)).all():
                biz_map[b.id] = b

        plot_data = []
        for plot in plots:
            plat, plng = _plot_pos(plot.id)
            biz = biz_map.get(plot.occupied_by_business_id)
            biz_cfg = BUSINESS_TYPES.get(biz.business_type, {}) if biz else {}
            proximity = (
                [f.strip() for f in plot.proximity_features.split(",") if f.strip()]
                if plot.proximity_features else []
            )
            plot_data.append({
                "id": plot.id,
                "lat": round(plat, 6),   # NW corner latitude
                "lng": round(plng, 6),   # NW corner longitude
                "terrain_type": plot.terrain_type,
                "proximity_features": proximity,
                "efficiency": round(plot.efficiency, 2),
                "occupied_by_business_id": plot.occupied_by_business_id,
                "business_type": biz.business_type if biz else None,
                "business_name": biz_cfg.get("name", biz.business_type if biz else None),
                "business_active": biz.is_active if biz else False,
                "monthly_tax": round(plot.monthly_tax, 2),
                "is_starter": plot.is_starter_plot,
                "url": "/land",
            })

        # ---- Districts ---------------------------------------------------
        districts = db.query(District).filter(District.owner_id == player.id).all()

        occ_dist_ids = [d.occupied_by_business_id for d in districts if d.occupied_by_business_id]
        dist_biz_map = {}
        if occ_dist_ids:
            for b in db.query(Business).filter(Business.id.in_(occ_dist_ids)).all():
                dist_biz_map[b.id] = b

        district_data = []
        for dist in districts:
            (clat, clng), (sw, ne) = _district_center_and_bounds(dist)
            biz = dist_biz_map.get(dist.occupied_by_business_id)
            biz_cfg = BUSINESS_TYPES.get(biz.business_type, {}) if biz else {}
            # Source-plot NW-corner positions — used on the frontend to draw the
            # exact cell-by-cell footprint rather than just the bounding box.
            src_ids = [int(i.strip()) for i in dist.source_plot_ids.split(",")
                       if i.strip()] if dist.source_plot_ids else []
            src_positions = [list(_plot_pos(pid)) for pid in src_ids]
            district_data.append({
                "id": dist.id,
                "lat": round(clat, 6),
                "lng": round(clng, 6),
                "bounds_sw": [round(sw[0], 6), round(sw[1], 6)],
                "bounds_ne": [round(ne[0], 6), round(ne[1], 6)],
                "source_positions": [[round(lat, 6), round(lng, 6)]
                                     for lat, lng in src_positions],
                "district_type": dist.district_type,
                "district_name": DISTRICT_NAMES.get(dist.district_type, dist.district_type),
                "terrain_type": dist.terrain_type,
                "plots_merged": dist.plots_merged,
                "size": round(dist.size, 2),
                "occupied_by_business_id": dist.occupied_by_business_id,
                "business_type": biz.business_type if biz else None,
                "business_name": biz_cfg.get("name", biz.business_type if biz else None),
                "business_active": biz.is_active if biz else False,
                "monthly_tax": round(dist.monthly_tax, 2),
                "url": f"/district/{dist.id}",
            })

        # ---- Cities ------------------------------------------------------
        memberships = db.query(CityMember).filter(CityMember.player_id == player.id).all()
        city_ids = [m.city_id for m in memberships]
        mayor_set = {m.city_id for m in memberships if m.is_mayor}

        city_data = []
        if city_ids:
            for city in db.query(City).filter(City.id.in_(city_ids)).all():
                clat, clng = _city_latlon(city.id)
                member_count = db.query(CityMember).filter(
                    CityMember.city_id == city.id).count()
                city_data.append({
                    "id": city.id,
                    "name": city.name,
                    "lat": clat,
                    "lng": clng,
                    "is_mayor": city.id in mayor_set,
                    "currency_type": city.currency_type,
                    "member_count": member_count,
                    "url": f"/city/{city.id}",
                })

        # ---- Counties ----------------------------------------------------
        county_links = (
            db.query(CountyCity).filter(CountyCity.city_id.in_(city_ids)).all()
            if city_ids else []
        )
        county_ids = list({cc.county_id for cc in county_links})

        county_data = []
        if county_ids:
            for county in db.query(County).filter(County.id.in_(county_ids)).all():
                clat, clng = _county_latlon(county.id)
                member_city_count = db.query(CountyCity).filter(
                    CountyCity.county_id == county.id).count()
                county_data.append({
                    "id": county.id,
                    "name": county.name,
                    "crypto_symbol": county.crypto_symbol,
                    "lat": clat,
                    "lng": clng,
                    "member_city_count": member_city_count,
                    "url": f"/county/{county.id}",
                })

        return JSONResponse({
            "player_id": player.id,
            "player_name": player.business_name,
            "land_plots": plot_data,
            "districts": district_data,
            "cities": city_data,
            "counties": county_data,
        })

    except Exception as exc:
        import traceback
        print("[world-map] API error:", traceback.format_exc())
        return JSONResponse({"error": str(exc)}, status_code=500)

    finally:
        db.close()


# ==========================
# API: TERRITORY HIERARCHY
# ==========================

@router.get("/api/world-map/territory")
async def world_map_territory(session_token: Optional[str] = Cookie(None)):
    """
    Return the full nested territory hierarchy for the world map.
    Includes ALL counties, their cities, city members' districts, and businesses.
    Used by the D3.js Voronoi territory visualization.
    """
    from auth import get_db, get_player_from_session
    from counties import County, CountyCity
    from cities import City, CityMember
    from districts import District
    from business import Business, BUSINESS_TYPES

    db = get_db()
    try:
        player = get_player_from_session(db, session_token)
        if not player:
            return JSONResponse({"error": "Not authenticated"}, status_code=401)

        all_counties = db.query(County).all()
        territory = []

        for county in all_counties:
            city_links = db.query(CountyCity).filter(
                CountyCity.county_id == county.id
            ).all()
            city_ids = [cl.city_id for cl in city_links]

            cities_out = []
            if city_ids:
                cities = db.query(City).filter(City.id.in_(city_ids)).all()
                for city in cities:
                    members = db.query(CityMember).filter(
                        CityMember.city_id == city.id
                    ).all()
                    member_player_ids = [m.player_id for m in members]

                    districts_out = []
                    if member_player_ids:
                        city_districts = db.query(District).filter(
                            District.owner_id.in_(member_player_ids)
                        ).all()

                        biz_ids = [
                            d.occupied_by_business_id
                            for d in city_districts
                            if d.occupied_by_business_id
                        ]
                        biz_map = {}
                        if biz_ids:
                            for b in db.query(Business).filter(
                                Business.id.in_(biz_ids)
                            ).all():
                                biz_map[b.id] = b

                        for dist in city_districts:
                            biz = biz_map.get(dist.occupied_by_business_id)
                            biz_cfg = BUSINESS_TYPES.get(biz.business_type, {}) if biz else {}
                            businesses_out = []
                            if biz:
                                businesses_out.append({
                                    "id": biz.id,
                                    "name": biz_cfg.get("name", biz.business_type),
                                    "type": biz.business_type,
                                    "active": biz.is_active,
                                })
                            districts_out.append({
                                "id": dist.id,
                                "name": DISTRICT_NAMES.get(
                                    dist.district_type, dist.district_type
                                ),
                                "type": dist.district_type,
                                "is_mine": dist.owner_id == player.id,
                                "businesses": businesses_out,
                                "url": f"/district/{dist.id}",
                            })

                    cities_out.append({
                        "id": city.id,
                        "name": city.name,
                        "member_count": len(members),
                        "districts": districts_out,
                        "url": f"/city/{city.id}",
                    })

            territory.append({
                "id": county.id,
                "name": county.name,
                "crypto_symbol": county.crypto_symbol,
                "city_count": len(cities_out),
                "cities": cities_out,
                "url": f"/county/{county.id}",
            })

        return JSONResponse({
            "player_id": player.id,
            "player_name": player.business_name,
            "counties": territory,
        })

    except Exception as exc:
        import traceback
        print("[world-map] territory error:", traceback.format_exc())
        return JSONResponse({"error": str(exc)}, status_code=500)

    finally:
        db.close()


# ==========================
# PAGE: WORLD MAP
# ==========================

@router.get("/world-map", response_class=HTMLResponse)
def world_map_page(session_token: Optional[str] = Cookie(None)):
    """
    Renders the interactive World Map page.
    Uses D3.js Voronoi tessellation on a black canvas to show the nested
    territory hierarchy: counties → cities → districts/companies → businesses.
    """
    from fastapi.responses import RedirectResponse
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player

    body = """
<div style="margin-bottom: 12px;">
    <a href="/" style="color: #38bdf8; font-size: 0.85rem;">&larr; Dashboard</a>
    <span style="color: #64748b; font-size: 0.85rem; margin-left: 12px;">|</span>
    <span style="color: #94a3b8; font-size: 0.85rem; margin-left: 12px;">World Map &mdash; Territory Overview</span>
</div>

<div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; margin-bottom: 12px;">
    <h1 style="margin: 0; font-size: 1.4rem;">World Map</h1>
    <div style="display: flex; gap: 8px; flex-wrap: wrap; align-items: center;">
        <button onclick="loadTerritoryData()" style="padding: 6px 12px; background: #1e293b; color: #94a3b8; border: 1px solid #334155; cursor: pointer; font-size: 0.8rem; border-radius: 3px;">Refresh</button>
    </div>
</div>

<!-- Legend -->
<div style="display:flex; flex-wrap:wrap; gap:10px; margin-bottom:10px; font-size:0.72rem; color:#94a3b8; align-items:center;">
    <span style="display:inline-flex;align-items:center;gap:5px;">
        <span style="width:14px;height:14px;background:#7c3aed33;border:2px solid #7c3aed;display:inline-block;border-radius:2px;"></span>County
    </span>
    <span style="display:inline-flex;align-items:center;gap:5px;">
        <span style="width:14px;height:14px;background:#b07aff33;border:1.5px solid #b07affcc;display:inline-block;border-radius:2px;"></span>City
    </span>
    <span style="display:inline-flex;align-items:center;gap:5px;">
        <span style="width:14px;height:14px;background:#2563eb55;border:1px solid #2563ebaa;display:inline-block;border-radius:2px;"></span>District / Company
    </span>
    <span style="display:inline-flex;align-items:center;gap:5px;">
        <span style="width:14px;height:14px;background:#2563eb88;border:0.5px solid #2563eb;display:inline-block;border-radius:2px;"></span>Business
    </span>
    <span style="color:#475569;">|</span>
    <span style="color:#94a3b8;">Hover for details &bull; Click to navigate</span>
</div>

<!-- Map container -->
<div id="map-container"
     style="width:100%; height:70vh; min-height:500px; position:relative;
            background:#000; border:1px solid #1e293b; border-radius:4px; overflow:hidden;">
    <div id="map-loading"
         style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);
                color:#64748b;font-size:0.9rem;z-index:20;pointer-events:none;">
        Loading territory data&hellip;
    </div>
    <svg id="territory-svg" style="width:100%;height:100%;display:block;"></svg>
    <div id="wm-tooltip"
         style="position:absolute;display:none;background:#0f172a;border:1px solid #334155;
                border-radius:4px;padding:8px 12px;font-family:monospace;font-size:12px;
                color:#e5e7eb;pointer-events:none;z-index:30;max-width:230px;
                box-shadow:0 4px 24px rgba(0,0,0,0.8);line-height:1.5;">
    </div>
</div>

<div id="map-status" style="margin-top:8px; font-size:0.75rem; color:#64748b; text-align:right;">
    Loading&hellip;
</div>

<!-- D3.js for Voronoi tessellation -->
<script src="https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js"></script>

<script>
// ============================================================
// WORLD MAP — NESTED VORONOI TERRITORY VISUALIZATION
// Counties → Cities → Districts (Companies) → Businesses
// ============================================================

// ============================================================
// COLOUR PALETTES
// ============================================================

// Distinct bright colours for county cells (rendered on black)
const COUNTY_PALETTE = [
    '#7c3aed','#0ea5e9','#22c55e','#f59e0b','#ec4899',
    '#14b8a6','#f97316','#a855f7','#06b6d4','#84cc16',
    '#fb7185','#38bdf8','#4ade80','#facc15','#c084fc',
    '#2dd4bf','#fb923c','#818cf8','#34d399','#fbbf24',
    '#f472b6','#60a5fa','#a3e635','#e879f9',
];

// District-type colours (same as backend TERRAIN_COLORS for districts)
const DIST_COLORS = {
    aerospace:'#6366f1', airport:'#38bdf8', convention_center:'#7c3aed',
    education:'#8b5cf6', entertainment:'#ec4899', entertainment_district:'#db2777',
    food:'#f97316', food_court:'#fb923c', hospital:'#14b8a6',
    industrial:'#64748b', mall:'#a855f7', mega_mall:'#c026d3',
    medical:'#06b6d4', military:'#dc2626', military_base:'#dc2626',
    neighborhood:'#84cc16', prison:'#475569', prison_complex:'#475569',
    research_campus:'#7c3aed', seaport:'#0891b2', shipyard:'#0369a1',
    tech:'#2563eb', tech_park:'#2563eb', transport:'#d97706',
    utilities:'#0284c7', zoo:'#4ade80',
};

// ============================================================
// GEOMETRY UTILITIES
// ============================================================

// Seeded LCG random number generator (deterministic, fast)
function mkRng(seed) {
    let s = ((Math.abs(seed | 0)) % 2147483647) || 1;
    return () => { s = (s * 16807) % 2147483647; return (s - 1) / 2147483646; };
}

// Point-in-polygon (ray casting)
function pip(pt, poly) {
    let inside = false;
    for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
        const xi = poly[i][0], yi = poly[i][1], xj = poly[j][0], yj = poly[j][1];
        if (((yi > pt[1]) !== (yj > pt[1])) &&
            (pt[0] < (xj - xi) * (pt[1] - yi) / (yj - yi) + xi))
            inside = !inside;
    }
    return inside;
}

// Sample a deterministic point inside a polygon
function sampleInPoly(poly, seed) {
    const rng = mkRng(seed);
    const xs = poly.map(p => p[0]), ys = poly.map(p => p[1]);
    const x0 = Math.min(...xs), x1 = Math.max(...xs);
    const y0 = Math.min(...ys), y1 = Math.max(...ys);
    for (let i = 0; i < 400; i++) {
        const pt = [x0 + rng() * (x1 - x0), y0 + rng() * (y1 - y0)];
        if (pip(pt, poly)) return pt;
    }
    return [(x0 + x1) / 2, (y0 + y1) / 2]; // fallback to bbox centre
}

// Polygon centroid (signed-area formula)
function centroid(poly) {
    let area = 0, cx = 0, cy = 0;
    const n = poly.length;
    for (let i = 0, j = n - 1; i < n; j = i++) {
        const a = poly[j][0] * poly[i][1] - poly[i][0] * poly[j][1];
        area += a; cx += (poly[j][0] + poly[i][0]) * a; cy += (poly[j][1] + poly[i][1]) * a;
    }
    area /= 2;
    if (Math.abs(area) < 0.01) {
        const xs = poly.map(p => p[0]), ys = poly.map(p => p[1]);
        return [(Math.min(...xs)+Math.max(...xs))/2, (Math.min(...ys)+Math.max(...ys))/2];
    }
    return [cx / (6 * area), cy / (6 * area)];
}

// Bounding box [x0, y0, x1, y1]
function bbox(poly) {
    const xs = poly.map(p => p[0]), ys = poly.map(p => p[1]);
    return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
}

// Lighten a hex colour toward white by factor t (0–1)
function lighten(hex, t) {
    const r = parseInt(hex.slice(1,3),16), g = parseInt(hex.slice(3,5),16), b = parseInt(hex.slice(5,7),16);
    const m = c => Math.min(255, Math.round(c + (255-c)*t)).toString(16).padStart(2,'0');
    return '#' + m(r) + m(g) + m(b);
}

// Hex-encode an alpha byte (0–255) as 2-char hex suffix
function alpha(hex, a) { return hex + Math.round(a).toString(16).padStart(2,'0'); }

// Distribute county seed points as a jittered grid across the canvas
function countySeeds(counties, W, H) {
    const n = counties.length;
    if (!n) return [];
    if (n === 1) return [[W/2, H/2]];
    const cols = Math.max(2, Math.ceil(Math.sqrt(n * (W / H))));
    const rows = Math.ceil(n / cols);
    const cw = W / cols, ch = H / rows;
    return counties.map((c, i) => {
        const rng = mkRng(c.id * 31337 + i * 9901);
        const col = i % cols, row = Math.floor(i / cols);
        return [col * cw + cw * (0.2 + rng() * 0.6), row * ch + ch * (0.2 + rng() * 0.6)];
    });
}

// Build SVG polygon points attribute string
function polyPts(pts) { return pts.map(p => p.join(',')).join(' '); }

// ============================================================
// TERRITORY RENDERING
// ============================================================
let _lastData = null;

function renderTerritories(data) {
    _lastData = data;
    const counties = data.counties || [];

    const container = document.getElementById('map-container');
    const W = container.clientWidth  || 1200;
    const H = container.clientHeight || 700;

    // Check D3 loaded
    if (typeof d3 === 'undefined') {
        document.getElementById('map-loading').textContent =
            'D3.js failed to load. Check network connection and reload.';
        return;
    }

    const svg = d3.select('#territory-svg').attr('width', W).attr('height', H)
                  .attr('viewBox', '0 0 ' + W + ' ' + H);
    svg.selectAll('*').remove();

    const defs = svg.append('defs');

    // County-border glow filter
    const gf = defs.append('filter').attr('id', 'glow')
                   .attr('x','-50%').attr('y','-50%')
                   .attr('width','200%').attr('height','200%');
    gf.append('feGaussianBlur').attr('stdDeviation','4').attr('result','blur');
    const fm = gf.append('feMerge');
    fm.append('feMergeNode').attr('in','blur');
    fm.append('feMergeNode').attr('in','SourceGraphic');

    // Subtle glow for labels
    const lf = defs.append('filter').attr('id', 'lglow')
                   .attr('x','-50%').attr('y','-50%')
                   .attr('width','200%').attr('height','200%');
    lf.append('feGaussianBlur').attr('stdDeviation','2').attr('result','blur');
    const lm = lf.append('feMerge');
    lm.append('feMergeNode').attr('in','blur');
    lm.append('feMergeNode').attr('in','SourceGraphic');

    // Black background
    svg.append('rect').attr('width', W).attr('height', H).attr('fill', '#000');

    if (!counties.length) {
        svg.append('text').attr('x', W/2).attr('y', H/2)
           .attr('text-anchor','middle').attr('dominant-baseline','middle')
           .attr('fill','#475569').attr('font-size',16).attr('font-family','monospace')
           .text('No counties found. Create or join a county to see the territory map.');
        document.getElementById('map-loading').style.display = 'none';
        document.getElementById('map-status').textContent = 'No territory data';
        return;
    }

    // ---- COUNTY VORONOI ----
    const cSeeds = countySeeds(counties, W, H);
    const cDel   = d3.Delaunay.from(cSeeds);
    const cVor   = cDel.voronoi([0, 0, W, H]);

    // Draw order: fills group → borders group → labels group
    const fillsG   = svg.append('g');
    const bordersG = svg.append('g');
    const labelsG  = svg.append('g');

    const tooltip = document.getElementById('wm-tooltip');

    function showTip(html, evt) {
        tooltip.innerHTML = html;
        tooltip.style.display = 'block';
        const rect = container.getBoundingClientRect();
        let x = evt.clientX - rect.left + 14;
        let y = evt.clientY - rect.top  + 14;
        const tw = tooltip.offsetWidth  || 200;
        const th = tooltip.offsetHeight || 80;
        if (x + tw > W - 8) x = evt.clientX - rect.left - tw - 14;
        if (y + th > H - 8) y = evt.clientY - rect.top  - th - 14;
        tooltip.style.left = x + 'px';
        tooltip.style.top  = y + 'px';
    }
    svg.on('mouseleave', () => { tooltip.style.display = 'none'; });

    counties.forEach((county, ci) => {
        const cPoly = cVor.cellPolygon(ci);
        if (!cPoly || cPoly.length < 4) return;
        const cPts  = cPoly.slice(0, -1);   // drop closing duplicate
        const cColor = COUNTY_PALETTE[ci % COUNTY_PALETTE.length];
        const cClip  = 'county-clip-' + county.id;

        defs.append('clipPath').attr('id', cClip)
            .append('polygon').attr('points', polyPts(cPts));

        // County group (everything inside is clipped to county polygon)
        const cG = fillsG.append('g').attr('clip-path', 'url(#' + cClip + ')');

        // County fill — subtle tinted background
        cG.append('polygon').attr('points', polyPts(cPts))
          .attr('fill', alpha(cColor, 22))   // ~8% opacity
          .style('cursor','pointer')
          .on('mousemove', evt => showTip(
              '<b style="color:' + cColor + '">' + county.name + '</b>' +
              (county.crypto_symbol ? '<br>Token: <span style="color:#f59e0b">' + county.crypto_symbol + '</span>' : '') +
              '<br>Cities: ' + (county.city_count || 0) +
              '<br><span style="color:#38bdf8;font-size:11px">click to visit county</span>', evt))
          .on('click', () => { window.location.href = county.url; });

        // ---- CITY LEVEL ----
        const cities = county.cities || [];
        if (cities.length > 0) {
            const citySeeds = cities.map((city, j) =>
                sampleInPoly(cPts, city.id * 997 + county.id * 31 + j));

            const [bx0,by0,bx1,by1] = bbox(cPts);
            const cityDel = d3.Delaunay.from(citySeeds);
            const cityVor = cityDel.voronoi([bx0-1, by0-1, bx1+1, by1+1]);

            cities.forEach((city, j) => {
                const cityPoly = cityVor.cellPolygon(j);
                if (!cityPoly || cityPoly.length < 4) return;
                const cityPts  = cityPoly.slice(0, -1);
                const cityColor = lighten(cColor, 0.38);
                const cityClip  = 'city-clip-' + city.id;

                defs.append('clipPath').attr('id', cityClip)
                    .append('polygon').attr('points', polyPts(cityPts));

                // City group (clipped to city polygon; parent cG clips to county)
                const cityG = cG.append('g').attr('clip-path', 'url(#' + cityClip + ')');

                cityG.append('polygon').attr('points', polyPts(cityPts))
                     .attr('fill', alpha(cityColor, 35))  // ~14% opacity
                     .style('cursor','pointer')
                     .on('mousemove', evt => showTip(
                         '<b style="color:' + cityColor + '">' + city.name + '</b>' +
                         '<br>Members: ' + city.member_count +
                         '<br>Districts: ' + (city.districts ? city.districts.length : 0) +
                         '<br><span style="color:#38bdf8;font-size:11px">click to visit city</span>', evt))
                     .on('click', () => { window.location.href = city.url; });

                // ---- DISTRICT (COMPANY) LEVEL ----
                const districts = city.districts || [];
                if (districts.length > 0) {
                    const distSeeds = districts.map((dist, k) =>
                        sampleInPoly(cityPts, dist.id * 1009 + city.id * 37 + k));

                    const [dx0,dy0,dx1,dy1] = bbox(cityPts);
                    const distDel = d3.Delaunay.from(distSeeds);
                    const distVor = distDel.voronoi([dx0-1, dy0-1, dx1+1, dy1+1]);

                    districts.forEach((dist, k) => {
                        const distPoly = distVor.cellPolygon(k);
                        if (!distPoly || distPoly.length < 4) return;
                        const distPts  = distPoly.slice(0, -1);
                        const dColor   = DIST_COLORS[dist.type] || '#475569';
                        const distClip = 'dist-clip-' + dist.id;
                        const isMine   = dist.is_mine;

                        defs.append('clipPath').attr('id', distClip)
                            .append('polygon').attr('points', polyPts(distPts));

                        // District group (clipped to district; parents clip to city × county)
                        const distG = cityG.append('g')
                                          .attr('clip-path', 'url(#' + distClip + ')');

                        // District fill
                        distG.append('polygon').attr('points', polyPts(distPts))
                             .attr('fill', alpha(dColor, 70))   // ~27% opacity
                             .style('cursor','pointer')
                             .on('mousemove', evt => {
                                 const biz = dist.businesses && dist.businesses[0];
                                 showTip(
                                     (isMine ? '<span style="color:#fbbf24">&#9733; MINE</span><br>' : '') +
                                     '<b style="color:' + dColor + '">' + dist.name + '</b>' +
                                     '<br>Type: ' + dist.type.replace(/_/g,' ') +
                                     (biz ? '<br>&#127981; ' + biz.name + (biz.active ? ' <span style="color:#22c55e">(active)</span>' : ' <span style="color:#ef4444">(inactive)</span>') : '') +
                                     '<br><span style="color:#38bdf8;font-size:11px">click to manage</span>', evt);
                             })
                             .on('click', () => { window.location.href = dist.url; });

                        // ---- BUSINESS LEVEL (innermost fill) ----
                        const bizList = dist.businesses || [];
                        if (bizList.length > 0) {
                            // Single business per district: shade the whole cell slightly darker
                            distG.append('polygon').attr('points', polyPts(distPts))
                                 .attr('fill', alpha(dColor, 50))
                                 .attr('pointer-events','none');
                        }

                        // District border (inside cityG so clipped to city × county)
                        cityG.append('polygon').attr('points', polyPts(distPts))
                             .attr('fill','none')
                             .attr('stroke', alpha(dColor, isMine ? 255 : 170))
                             .attr('stroke-width', isMine ? 1.8 : 0.9)
                             .attr('pointer-events','none');

                        // District label — tiny, centred
                        const [dlx, dly] = centroid(distPts);
                        cityG.append('text')
                             .attr('x', dlx).attr('y', dly)
                             .attr('text-anchor','middle').attr('dominant-baseline','middle')
                             .attr('fill', alpha(dColor, 230))
                             .attr('font-size','7px').attr('font-family','monospace')
                             .attr('pointer-events','none')
                             .text(dist.name.length > 14 ? dist.name.slice(0,12)+'…' : dist.name);
                    });
                }

                // City border (inside cG so clipped to county)
                cG.append('polygon').attr('points', polyPts(cityPts))
                  .attr('fill','none')
                  .attr('stroke', alpha(cityColor, 200))
                  .attr('stroke-width', 1.5)
                  .attr('pointer-events','none');

                // City label
                const [clx, cly] = centroid(cityPts);
                cG.append('text')
                  .attr('x', clx).attr('y', cly)
                  .attr('text-anchor','middle').attr('dominant-baseline','middle')
                  .attr('fill', cityColor)
                  .attr('font-size','11px').attr('font-weight','bold')
                  .attr('font-family','monospace').attr('pointer-events','none')
                  .attr('filter','url(#lglow)')
                  .text(city.name);
            });
        }

        // County border — drawn on top of all fills (in bordersG, not inside cG)
        bordersG.append('polygon').attr('points', polyPts(cPts))
                .attr('fill','none')
                .attr('stroke', cColor)
                .attr('stroke-width', 3)
                .attr('filter','url(#glow)')
                .attr('pointer-events','none');

        // County label — topmost layer
        const [clx, cly] = centroid(cPts);
        const yOff = cities.length > 0 ? -22 : 0;
        labelsG.append('text')
               .attr('x', clx).attr('y', cly + yOff)
               .attr('text-anchor','middle').attr('dominant-baseline','middle')
               .attr('fill', cColor)
               .attr('font-size','15px').attr('font-weight','bold')
               .attr('font-family','monospace').attr('pointer-events','none')
               .attr('filter','url(#glow)')
               .text(county.name);

        if (county.crypto_symbol) {
            labelsG.append('text')
                   .attr('x', clx).attr('y', cly + yOff + 16)
                   .attr('text-anchor','middle').attr('dominant-baseline','middle')
                   .attr('fill', alpha(cColor, 170))
                   .attr('font-size','10px').attr('font-family','monospace')
                   .attr('pointer-events','none')
                   .text('[' + county.crypto_symbol + ']');
        }
    });

    // Status bar
    const totalCities    = counties.reduce((s,c) => s + (c.cities ? c.cities.length : 0), 0);
    const totalDistricts = counties.reduce((s,c) =>
        s + (c.cities ? c.cities.reduce((s2,city) => s2 + (city.districts ? city.districts.length : 0), 0) : 0), 0);
    document.getElementById('map-status').textContent =
        counties.length + ' counties  \u2022  ' + totalCities + ' cities  \u2022  ' + totalDistricts + ' districts/companies';

    document.getElementById('map-loading').style.display = 'none';
}

// ============================================================
// DATA FETCH
// ============================================================
function loadTerritoryData() {
    document.getElementById('map-loading').style.display = 'block';
    document.getElementById('map-status').textContent = 'Loading\u2026';

    fetch('/api/world-map/territory')
        .then(r => {
            if (!r.ok) return r.text().then(t => { throw new Error('HTTP ' + r.status + ': ' + t.slice(0,200)); });
            return r.json();
        })
        .then(data => {
            if (data.error) {
                document.getElementById('map-loading').textContent = 'Error: ' + data.error;
                return;
            }
            renderTerritories(data);
        })
        .catch(err => {
            document.getElementById('map-loading').textContent = 'Failed: ' + err.message;
            console.error('[world-map]', err);
        });
}

// Rerender on window resize
window.addEventListener('resize', () => { if (_lastData) renderTerritories(_lastData); });

// ============================================================
// BOOT
// ============================================================
loadTerritoryData();

</script>
"""

    return HTMLResponse(shell("World Map", body, player.cash_balance, player.id))
