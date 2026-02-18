"""
world_map_ux.py

World Map feature for the Wadsworth Economic Simulation.
Provides a Leaflet.js-powered interactive visualization of the player's
entire economic empire: land plots, districts, cities, and counties.

Coordinate System:
  - Uses real geographic coordinates (WGS-84 lat/lng) rendered on OpenStreetMap tiles
  - Game plot grid is mapped to a ~15km × 33km area in central Maryland
  - Cities are pinned to curated real Maryland city positions
  - Counties are pinned to real Maryland county seat positions
  - Zoom in from state level → county → city → individual 111m × 115m land plots

Terrain colours match the game's established hex palette.
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
# PAGE: WORLD MAP
# ==========================

@router.get("/world-map", response_class=HTMLResponse)
def world_map_page(session_token: Optional[str] = Cookie(None)):
    """
    Renders the interactive World Map page for the authenticated player.
    The map uses Leaflet.js with L.CRS.Simple to display the player's empire
    on a flat game-grid coordinate system.
    """
    from fastapi.responses import RedirectResponse
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player

    body = """
<div style="margin-bottom: 12px;">
    <a href="/" style="color: #38bdf8; font-size: 0.85rem;">&larr; Dashboard</a>
    <span style="color: #64748b; font-size: 0.85rem; margin-left: 12px;">|</span>
    <span style="color: #94a3b8; font-size: 0.85rem; margin-left: 12px;">World Map &mdash; Your Economic Empire</span>
</div>

<div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; margin-bottom: 12px;">
    <h1 style="margin: 0; font-size: 1.4rem;">World Map</h1>
    <div style="display: flex; gap: 8px; flex-wrap: wrap; align-items: center;">
        <button id="btn-world" onclick="fitWorld()" style="padding: 6px 12px; background: #1e293b; color: #94a3b8; border: 1px solid #334155; cursor: pointer; font-size: 0.8rem; border-radius: 3px;">World View</button>
        <button id="btn-fit" onclick="fitAll()" style="padding: 6px 12px; background: #38bdf8; color: #020617; border: none; cursor: pointer; font-size: 0.8rem; border-radius: 3px;">My Assets</button>
        <button id="btn-refresh" onclick="loadMapData()" style="padding: 6px 12px; background: #1e293b; color: #94a3b8; border: 1px solid #334155; cursor: pointer; font-size: 0.8rem; border-radius: 3px;">Refresh</button>
    </div>
</div>

<!-- Legend -->
<div id="map-legend" style="display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px; font-size: 0.72rem; color: #94a3b8;">
    <span style="display:inline-flex;align-items:center;gap:4px;"><span style="width:12px;height:12px;background:#22c55e;display:inline-block;border-radius:2px;"></span>Prairie</span>
    <span style="display:inline-flex;align-items:center;gap:4px;"><span style="width:12px;height:12px;background:#f59e0b;display:inline-block;border-radius:2px;"></span>Desert</span>
    <span style="display:inline-flex;align-items:center;gap:4px;"><span style="width:12px;height:12px;background:#3b82f6;display:inline-block;border-radius:2px;"></span>Island</span>
    <span style="display:inline-flex;align-items:center;gap:4px;"><span style="width:12px;height:12px;background:#78716c;display:inline-block;border-radius:2px;"></span>Mountain</span>
    <span style="display:inline-flex;align-items:center;gap:4px;"><span style="width:12px;height:12px;background:#16a34a;display:inline-block;border-radius:2px;"></span>Forest</span>
    <span style="display:inline-flex;align-items:center;gap:4px;"><span style="width:12px;height:12px;background:#0891b2;display:inline-block;border-radius:2px;"></span>Marsh</span>
    <span style="display:inline-flex;align-items:center;gap:4px;"><span style="width:12px;height:12px;background:#94a3b8;display:inline-block;border-radius:2px;"></span>Tundra</span>
    <span style="display:inline-flex;align-items:center;gap:4px;"><span style="width:12px;height:12px;background:#ca8a04;display:inline-block;border-radius:2px;"></span>Savanna</span>
    <span style="display:inline-flex;align-items:center;gap:4px;"><span style="width:12px;height:12px;background:#a16207;display:inline-block;border-radius:2px;"></span>Hills</span>
    <span style="display:inline-flex;align-items:center;gap:4px;"><span style="width:12px;height:12px;background:#15803d;display:inline-block;border-radius:2px;"></span>Jungle</span>
    <span style="color:#64748b;">|</span>
    <span style="display:inline-flex;align-items:center;gap:4px;"><span style="width:12px;height:12px;background:#334155;border:2px solid #64748b;display:inline-block;border-radius:2px;"></span>District</span>
    <span style="display:inline-flex;align-items:center;gap:4px;">&#127981; Business</span>
    <span style="display:inline-flex;align-items:center;gap:4px;"><span style="width:12px;height:12px;background:#0c2340;border:2px solid #38bdf8;display:inline-block;border-radius:50%;"></span>&#127963; City</span>
    <span style="display:inline-flex;align-items:center;gap:4px;"><span style="width:12px;height:12px;background:#78350f;border:2px dashed #d4af37;display:inline-block;border-radius:50%;"></span>&#128506; County</span>
    <span style="color:#64748b;">|</span>
    <span style="color:#94a3b8;">Zoom in to see land plots &bull; Opacity = Efficiency</span>
</div>

<!-- Map container -->
<div id="map"
     style="width: 100%; height: 70vh; min-height: 480px; background: #c8d8e4;
            border: 1px solid #1e293b; border-radius: 4px; position: relative;">
    <div id="map-loading"
         style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);
                color:#64748b;font-size:0.9rem;z-index:999;">
        Loading map data&hellip;
    </div>
</div>

<div id="map-status" style="margin-top: 8px; font-size: 0.75rem; color: #64748b; text-align: right;">
    Click any element to open info &bull; Double-click to navigate &bull; Scroll to zoom &bull; Zoom in (~zoom 15) to see land plots
</div>

<!-- Leaflet CSS (served locally) -->
<link rel="stylesheet" href="/static/leaflet.css"/>

<!-- Leaflet JS (served locally) -->
<script src="/static/leaflet.js"></script>

<script>
// ============================================================
// MARYLAND GEO CONSTANTS  (mirror Python server values)
// ============================================================
const PLOT_ORIGIN_LAT = """ + str(PLOT_ORIGIN_LAT) + """;
const PLOT_ORIGIN_LNG = """ + str(PLOT_ORIGIN_LNG) + """;
const PLOT_DLAT       = """ + str(PLOT_DLAT)       + """;
const PLOT_DLNG       = """ + str(PLOT_DLNG)       + """;
const GRID_WIDTH      = """ + str(int(GRID_WIDTH)) + """;
// Maryland bounding box for "World View" button
const MD_SW = [37.88, -79.53];
const MD_NE = [39.72, -74.95];

// ============================================================
// TERRAIN / DISTRICT COLOUR PALETTE  (mirrors Python dict)
// ============================================================
const TERRAIN_COLORS = {
    prairie:  '#22c55e', forest:   '#16a34a', desert:   '#f59e0b',
    marsh:    '#0891b2', mountain: '#78716c', tundra:   '#94a3b8',
    jungle:   '#15803d', savanna:  '#ca8a04', hills:    '#a16207',
    island:   '#3b82f6',
    district_aerospace:              '#6366f1',
    district_airport:                '#38bdf8',
    district_convention_center:      '#7c3aed',
    district_education:              '#8b5cf6',
    district_entertainment:          '#ec4899',
    district_entertainment_district: '#db2777',
    district_food:                   '#f97316',
    district_food_court:             '#fb923c',
    district_hospital:               '#14b8a6',
    district_industrial:             '#64748b',
    district_mall:                   '#a855f7',
    district_mega_mall:              '#c026d3',
    district_medical:                '#06b6d4',
    district_military:               '#dc2626',
    district_military_base:          '#dc2626',
    district_neighborhood:           '#84cc16',
    district_prison:                 '#475569',
    district_prison_complex:         '#475569',
    district_research_campus:        '#7c3aed',
    district_seaport:                '#0891b2',
    district_shipyard:               '#0369a1',
    district_tech:                   '#2563eb',
    district_tech_park:              '#2563eb',
    district_transport:              '#d97706',
    district_utilities:              '#0284c7',
    district_zoo:                    '#4ade80',
};

function terrainColor(t) {
    return TERRAIN_COLORS[t] || '#334155';
}

// ============================================================
// MAP INITIALISATION
// ============================================================

// Declare layer variables at module scope so function declarations
// that reference them never hit the temporal dead zone even if Leaflet
// fails to load.
let map = null;
let layerPlots = null, layerDistricts = null,
    layerCities = null, layerCounties = null;
let allBoundsPoints = [];

if (typeof L === 'undefined') {
    // Leaflet failed to load (served locally so this means a file error)
    document.getElementById('map-loading').textContent =
        'Map library failed to load. Check your connection and reload.';
} else {
    try {
        map = L.map('map', {
            minZoom: 5,
            maxZoom: 19,
            zoomSnap: 0.5,
            attributionControl: false,
        });

        // Start centered on Maryland while data loads
        map.setView([39.0, -76.8], 9);

        // OpenStreetMap tile layer — gives the real-world map feel
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19,
            subdomains: 'abc',
        }).addTo(map);

        // Layer groups for toggling
        layerPlots     = L.layerGroup().addTo(map);
        layerDistricts = L.layerGroup().addTo(map);
        layerCities    = L.layerGroup().addTo(map);
        layerCounties  = L.layerGroup().addTo(map);
    } catch(initErr) {
        document.getElementById('map-loading').textContent =
            'Map init error: ' + initErr.message;
        console.error('[world-map] init', initErr);
    }
}

// ============================================================
// LOAD & RENDER
// ============================================================
function loadMapData() {
    if (!map) {
        document.getElementById('map-loading').textContent =
            'Map not initialized. Reload the page.';
        return;
    }
    document.getElementById('map-loading').style.display = 'block';
    document.getElementById('map-status').textContent = 'Loading\u2026';

    fetch('/api/world-map/data')
        .then(r => {
            if (!r.ok) {
                return r.text().then(t => {
                    throw new Error('HTTP ' + r.status + ' \u2014 ' + t.substring(0, 300));
                });
            }
            return r.json();
        })
        .then(data => {
            if (data.error) {
                document.getElementById('map-loading').textContent = 'Error: ' + data.error;
                return;
            }
            renderMap(data);
        })
        .catch(err => {
            document.getElementById('map-loading').textContent = 'Failed to load map data: ' + err.message;
            console.error('[world-map]', err);
        });
}

function renderMap(data) {
    // Clear previous layers
    layerPlots.clearLayers();
    layerDistricts.clearLayers();
    layerCities.clearLayers();
    layerCounties.clearLayers();
    allBoundsPoints = [];

    // ---- LAND PLOTS ------------------------------------------------
    // Each plot is a ~111m × 115m rectangle on the real map.
    // The API returns the NW corner (lat, lng); we derive SE from PLOT_D*.
    (data.land_plots || []).forEach(plot => {
        // NW corner lat/lng
        const nwLat = plot.lat, nwLng = plot.lng;
        // SW and NE corners (PLOT_DLAT is negative so nwLat + PLOT_DLAT < nwLat)
        const sw = [nwLat + PLOT_DLAT, nwLng];
        const ne = [nwLat, nwLng + PLOT_DLNG];
        const center = [(sw[0] + ne[0]) / 2, (sw[1] + ne[1]) / 2];

        // Efficiency drives fill opacity (0.6–0.95)
        const fillOpacity = 0.6 + (plot.efficiency / 100) * 0.35;
        const color = terrainColor(plot.terrain_type);
        const borderColor = plot.occupied_by_business_id ? '#f8fafc' : '#334155';
        const weight      = plot.occupied_by_business_id ? 1.5 : 0.8;

        const rect = L.rectangle([sw, ne], {
            color: borderColor, weight,
            fillColor: color, fillOpacity,
        });

        let bizLine = '';
        if (plot.business_type) {
            const icon   = plot.business_active ? '&#127981;' : '&#9208;&#65039;';
            const status = plot.business_active ? 'Active' : 'Inactive';
            bizLine = `<br>${icon} <b>${plot.business_name || plot.business_type}</b> &mdash; ${status}`;
        }
        const proxLine = plot.proximity_features.length
            ? `<br><span style="color:#94a3b8">+${plot.proximity_features.join(', ')}</span>`
            : '';
        const effColor = plot.efficiency >= 75 ? '#22c55e'
                       : plot.efficiency >= 40 ? '#f59e0b' : '#ef4444';

        const popupHtml = `
            <div style="font-family:'JetBrains Mono',monospace;font-size:12px;color:#e5e7eb;min-width:160px">
                <b>Plot #${plot.id}</b> &mdash;
                <span style="color:${color}">${plot.terrain_type}</span>${proxLine}${bizLine}
                <br>Efficiency: <span style="color:${effColor}">${plot.efficiency}%</span>
                <br>Tax: <span style="color:#94a3b8">$${plot.monthly_tax.toLocaleString()}/mo</span>
                <br><a href="${plot.url}" style="color:#38bdf8">&#8594; Manage Land</a>
            </div>`;

        rect.bindPopup(popupHtml, { className: 'wad-popup', maxWidth: 260 });
        rect.on('dblclick', () => { window.location.href = plot.url; });
        rect.addTo(layerPlots);

        // Business icon centred on the plot cell (visible from zoom ~15)
        if (plot.occupied_by_business_id) {
            const bIcon = L.divIcon({
                html: `<div style="font-size:12px;line-height:1;filter:drop-shadow(0 0 3px #000);` +
                      `transform:translate(-50%,-50%);">` +
                      (plot.business_active ? '&#127981;' : '&#9208;&#65039;') + `</div>`,
                className: '', iconAnchor: [0, 0],
            });
            L.marker(center, { icon: bIcon, interactive: false }).addTo(layerPlots);
        }

        allBoundsPoints.push(sw);
        allBoundsPoints.push(ne);
    });

    // ---- DISTRICTS -------------------------------------------------
    (data.districts || []).forEach(dist => {
        const color = terrainColor(dist.terrain_type);
        const bSW = dist.bounds_sw, bNE = dist.bounds_ne;

        let bizLine = '';
        if (dist.business_type) {
            const icon   = dist.business_active ? '&#127981;' : '&#9208;&#65039;';
            const status = dist.business_active ? 'Active' : 'Inactive';
            bizLine = `<br>${icon} <b>${dist.business_name || dist.business_type}</b> &mdash; ${status}`;
        }

        const popupHtml = `
            <div style="font-family:'JetBrains Mono',monospace;font-size:12px;color:#e5e7eb;min-width:160px">
                <b>&#127959;&#65039; ${dist.district_name}</b>
                <br><span style="color:${color}">${dist.district_type}</span> district
                <br>${dist.plots_merged} plots merged &mdash; size ${dist.size}${bizLine}
                <br>Tax: <span style="color:#94a3b8">$${dist.monthly_tax.toLocaleString()}/mo</span>
                <br><a href="${dist.url}" style="color:#38bdf8">&#8594; Manage District</a>
            </div>`;

        // Each source_position is the NW corner [lat, lng] of a 1×1 plot cell
        const srcPositions = dist.source_positions || [];
        if (srcPositions.length > 0) {
            srcPositions.forEach(([nwLat, nwLng]) => {
                const csw = [nwLat + PLOT_DLAT, nwLng];
                const cne = [nwLat, nwLng + PLOT_DLNG];
                const cell = L.rectangle([csw, cne],
                    { color, weight: 1, fillColor: color, fillOpacity: 0.55 });
                cell.bindPopup(popupHtml, { className: 'wad-popup', maxWidth: 260 });
                cell.on('dblclick', () => { window.location.href = dist.url; });
                cell.addTo(layerDistricts);
            });
            // Dashed bounding-box outline ties the footprint together
            L.rectangle([bSW, bNE],
                { color, weight: 2, fillOpacity: 0, dashArray: '7 4', interactive: false }
            ).addTo(layerDistricts);
        } else {
            const rect = L.rectangle([bSW, bNE],
                { color, weight: 2.5, fillColor: color, fillOpacity: 0.4, dashArray: '6 3' });
            rect.bindPopup(popupHtml, { className: 'wad-popup', maxWidth: 260 });
            rect.on('dblclick', () => { window.location.href = dist.url; });
            rect.addTo(layerDistricts);
        }

        // Centroid label
        const labelIcon = L.divIcon({
            html: `<span style="font-size:9px;color:${color};font-family:monospace;white-space:nowrap;` +
                  `background:rgba(2,6,23,0.82);padding:1px 4px;border-radius:2px;">` +
                  `&#127959; ${dist.district_name}</span>`,
            className: '', iconAnchor: [0, 0],
        });
        L.marker([dist.lat, dist.lng], { icon: labelIcon, interactive: false }).addTo(layerDistricts);

        if (dist.occupied_by_business_id) {
            const bIcon = L.divIcon({
                html: `<div style="font-size:14px;line-height:1;filter:drop-shadow(0 0 3px #000);` +
                      `transform:translate(-50%,-50%);">` +
                      (dist.business_active ? '&#127981;' : '&#9208;&#65039;') + `</div>`,
                className: '', iconAnchor: [0, 0],
            });
            L.marker([dist.lat, dist.lng], { icon: bIcon, interactive: false }).addTo(layerDistricts);
        }

        allBoundsPoints.push(bSW);
        allBoundsPoints.push(bNE);
    });

    // ---- CITIES ----------------------------------------------------
    // Cities are pinned to real Maryland city positions.
    // A semi-transparent circle shows approximate city territory;
    // radius scales with member count so larger cities look bigger.
    (data.cities || []).forEach(city => {
        const clat = city.lat, clng = city.lng;

        const mayorStar = city.is_mayor ? ' &#9733;' : '';
        const icon = L.divIcon({
            html: `<div style="display:inline-flex;align-items:center;gap:5px;` +
                  `background:rgba(2,6,23,0.88);border:1.5px solid #38bdf8;` +
                  `border-radius:5px;padding:4px 9px;font-family:monospace;` +
                  `font-size:12px;color:#e2e8f0;white-space:nowrap;` +
                  `filter:drop-shadow(0 0 8px #0ea5e9);transform:translate(-50%,-50%);` +
                  `cursor:pointer;">` +
                  `<span style="font-size:17px">&#127961;</span>` +
                  ` <strong>${city.name}</strong>${mayorStar}</div>`,
            className: '',
            iconAnchor: [0, 0],
        });

        const mayorBadge = city.is_mayor
            ? '<br><span style="color:#d4af37">&#9733; Mayor</span>' : '';
        const currLine = city.currency_type
            ? `<br>Currency: <span style="color:#f59e0b">${city.currency_type.replace(/_/g,' ')}</span>`
            : '';

        const popupHtml = `
            <div style="font-family:'JetBrains Mono',monospace;font-size:12px;color:#e5e7eb;min-width:160px">
                <b>&#127961;&#65039; ${city.name}</b>${mayorBadge}${currLine}
                <br>Members: <span style="color:#38bdf8">${city.member_count || 1}</span>
                <br><a href="${city.url}" style="color:#38bdf8">&#8594; City Hub</a>
            </div>`;

        // Semi-transparent circle showing city territory.
        // Radius grows with member count: 1.5 km base + 500 m per member.
        const cityRadius = 1500 + Math.min((city.member_count || 1) - 1, 20) * 500;
        const cityCircle = L.circle([clat, clng], {
            radius: cityRadius,
            color: '#0ea5e9', weight: 2,
            fillColor: '#0c2340', fillOpacity: 0.18,
        });
        cityCircle.bindPopup(popupHtml, { className: 'wad-popup', maxWidth: 260 });
        cityCircle.on('dblclick', () => { window.location.href = city.url; });
        cityCircle.addTo(layerCities);

        const marker = L.marker([clat, clng], { icon });
        marker.bindPopup(popupHtml, { className: 'wad-popup', maxWidth: 260 });
        marker.on('dblclick', () => { window.location.href = city.url; });
        marker.addTo(layerCities);

        // Rough lat/lng extent of the city circle (1° lat ≈ 111 km)
        const degR = cityRadius / 111000;
        allBoundsPoints.push([clat - degR, clng - degR]);
        allBoundsPoints.push([clat + degR, clng + degR]);
    });

    // ---- COUNTIES --------------------------------------------------
    // Counties are pinned to real Maryland county seat positions.
    // A dashed amber circle shows county territory extent.
    (data.counties || []).forEach(county => {
        const clat = county.lat, clng = county.lng;

        const icon = L.divIcon({
            html: `<div style="display:inline-flex;align-items:center;gap:5px;` +
                  `background:rgba(2,6,23,0.88);border:1.5px solid #d4af37;` +
                  `border-radius:5px;padding:4px 9px;font-family:monospace;` +
                  `font-size:13px;color:#fde68a;white-space:nowrap;` +
                  `filter:drop-shadow(0 0 8px #d4af37);transform:translate(-50%,-50%);` +
                  `cursor:pointer;">` +
                  `<span style="font-size:19px">&#128506;</span>` +
                  ` <strong>${county.name}</strong></div>`,
            className: '', iconAnchor: [0, 0],
        });

        const popupHtml = `
            <div style="font-family:'JetBrains Mono',monospace;font-size:12px;color:#e5e7eb;min-width:160px">
                <b>&#128506;&#65039; ${county.name}</b>
                <br>Token: <span style="color:#d4af37">${county.crypto_symbol}</span>
                <br>Member cities: <span style="color:#d4af37">${county.member_city_count || 1}</span>
                <br><a href="${county.url}" style="color:#38bdf8">&#8594; County Hub</a>
            </div>`;

        // Dashed circle for county territory.
        // Radius: 10 km base + 3 km per member city (up to 10 cities).
        const countyRadius = 10000 + Math.min((county.member_city_count || 1) - 1, 10) * 3000;
        const countyCircle = L.circle([clat, clng], {
            radius: countyRadius,
            color: '#d4af37', weight: 2,
            fillColor: '#78350f', fillOpacity: 0.08,
            dashArray: '8 6',
        });
        countyCircle.bindPopup(popupHtml, { className: 'wad-popup', maxWidth: 260 });
        countyCircle.on('dblclick', () => { window.location.href = county.url; });
        countyCircle.addTo(layerCounties);

        const marker = L.marker([clat, clng], { icon });
        marker.bindPopup(popupHtml, { className: 'wad-popup', maxWidth: 260 });
        marker.on('dblclick', () => { window.location.href = county.url; });
        marker.addTo(layerCounties);

        const degR = countyRadius / 111000;
        allBoundsPoints.push([clat - degR, clng - degR]);
        allBoundsPoints.push([clat + degR, clng + degR]);
    });

    // ---- FIT VIEWPORT ----------------------------------------------
    if (allBoundsPoints.length > 0) {
        // Fit to the player's assets with comfortable padding
        map.fitBounds(allBoundsPoints, { padding: [60, 60], maxZoom: 16 });
    } else {
        // No assets yet — show all of Maryland
        map.fitBounds([MD_SW, MD_NE], { padding: [20, 20] });
    }

    document.getElementById('map-loading').style.display = 'none';

    const plotCount    = (data.land_plots    || []).length;
    const distCount    = (data.districts     || []).length;
    const cityCount    = (data.cities        || []).length;
    const countyCount  = (data.counties      || []).length;
    document.getElementById('map-status').textContent =
        `${plotCount} plots  \u2022  ${distCount} districts  \u2022  ${cityCount} cities  \u2022  ${countyCount} counties`;
}

// "My Assets" button — zoom tightly to the player's economic empire
function fitAll() {
    if (!map) return;
    if (allBoundsPoints.length > 0) {
        map.fitBounds(allBoundsPoints, { padding: [60, 60], maxZoom: 16 });
    } else {
        fitWorld();
    }
}

// "World View" button — zoom out to show all of Maryland
function fitWorld() {
    if (!map) return;
    map.fitBounds([MD_SW, MD_NE], { padding: [10, 10] });
}

// ============================================================
// POPUP DARK STYLING  (injected once)
// ============================================================
(function injectPopupStyle() {
    const style = document.createElement('style');
    style.textContent = `
        .wad-popup .leaflet-popup-content-wrapper {
            background: #0f172a !important;
            border: 1px solid #1e293b !important;
            border-radius: 4px !important;
            color: #e5e7eb !important;
            box-shadow: 0 4px 24px rgba(0,0,0,0.7) !important;
        }
        .wad-popup .leaflet-popup-tip {
            background: #0f172a !important;
        }
        .wad-popup .leaflet-popup-close-button {
            color: #64748b !important;
        }
        .wad-popup .leaflet-popup-close-button:hover {
            color: #e5e7eb !important;
        }
    `;
    document.head.appendChild(style);
})();

// ============================================================
// BOOT
// ============================================================
if (map) {
    loadMapData();
}
</script>
"""

    return HTMLResponse(shell("World Map", body, player.cash_balance, player.id))
