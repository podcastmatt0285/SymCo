"""
world_map_ux.py

World Map feature for the Wadsworth Economic Simulation.
Provides a Leaflet.js-powered interactive visualization of the player's
entire economic empire: land plots, districts, cities, and counties.

Coordinate System:
  - Uses Leaflet's L.CRS.Simple (flat, non-geographic game grid)
  - Grid unit: 1 unit == 1 standard land plot
  - Land plot position: x = (id - 1) % GRID_WIDTH, y = (id - 1) // GRID_WIDTH
  - District position: centroid of source plot grid positions
  - City position: placed in a dedicated zone above the land grid (y >= CITY_ZONE_Y)
  - County position: placed above the city zone (y >= COUNTY_ZONE_Y)

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
CITY_ZONE_Y = 300.0       # Cities are placed starting at this Y
COUNTY_ZONE_Y = 500.0     # Counties are placed starting at this Y

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
    """Return (x, y) grid coordinates for a land plot from its ID."""
    idx = plot_id - 1
    return float(idx % GRID_WIDTH), float(idx // GRID_WIDTH)


def _district_center_and_bounds(district):
    """
    Derive a district's grid centre and bounding box from its source_plot_ids.
    The source plots are deleted at merge time, but their IDs are preserved
    in the district record, so we can recompute their original positions.

    Returns:
        center (cx, cy), bounds [x1, y1, x2, y2]
    """
    if district.source_plot_ids:
        try:
            ids = [int(s.strip()) for s in district.source_plot_ids.split(",") if s.strip()]
            if ids:
                positions = [_plot_pos(pid) for pid in ids]
                xs = [p[0] for p in positions]
                ys = [p[1] for p in positions]
                cx = sum(xs) / len(xs)
                cy = sum(ys) / len(ys)
                # Bounds extend +1 in each direction to cover the full 1×1 plot cells
                bounds = [min(xs), min(ys), max(xs) + 1.0, max(ys) + 1.0]
                return (cx + 0.5, cy + 0.5), bounds
        except Exception:
            pass
    # Fallback: synthetic position based on district ID
    col = (district.id - 1) % 20
    row = (district.id - 1) // 20
    cx = 110.0 + col * 6.0
    cy = 10.0 + row * 6.0
    return (cx, cy), [cx - 2.5, cy - 2.5, cx + 2.5, cy + 2.5]


def _city_pos(city_id: int):
    """Return (x, y) for a city marker in the city zone."""
    col = (city_id - 1) % 10
    row = (city_id - 1) // 10
    return 5.0 + col * 10.0, CITY_ZONE_Y + row * 30.0


def _county_pos(county_id: int):
    """Return (x, y) for a county marker in the county zone."""
    return 10.0 + (county_id - 1) * 25.0, COUNTY_ZONE_Y


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
            gx, gy = _plot_pos(plot.id)
            biz = biz_map.get(plot.occupied_by_business_id)
            biz_cfg = BUSINESS_TYPES.get(biz.business_type, {}) if biz else {}
            proximity = (
                [f.strip() for f in plot.proximity_features.split(",") if f.strip()]
                if plot.proximity_features else []
            )
            plot_data.append({
                "id": plot.id,
                "grid_x": gx,
                "grid_y": gy,
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
            (cx, cy), bounds = _district_center_and_bounds(dist)
            biz = dist_biz_map.get(dist.occupied_by_business_id)
            biz_cfg = BUSINESS_TYPES.get(biz.business_type, {}) if biz else {}
            district_data.append({
                "id": dist.id,
                "center_x": round(cx, 3),
                "center_y": round(cy, 3),
                "bounds": [round(v, 3) for v in bounds],
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
                cx, cy = _city_pos(city.id)
                city_data.append({
                    "id": city.id,
                    "name": city.name,
                    "center_x": cx,
                    "center_y": cy,
                    "is_mayor": city.id in mayor_set,
                    "currency_type": city.currency_type,
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
                cx, cy = _county_pos(county.id)
                county_data.append({
                    "id": county.id,
                    "name": county.name,
                    "crypto_symbol": county.crypto_symbol,
                    "center_x": cx,
                    "center_y": cy,
                    "url": f"/county/{county.id}",
                })

        # ---- Viewport bounds (with padding) ------------------------------
        all_x = (
            [p["grid_x"] for p in plot_data]
            + [d["center_x"] for d in district_data]
            + [c["center_x"] for c in city_data]
            + [c["center_x"] for c in county_data]
        )
        all_y = (
            [p["grid_y"] for p in plot_data]
            + [d["center_y"] for d in district_data]
            + [c["center_y"] for c in city_data]
            + [c["center_y"] for c in county_data]
        )
        if all_x:
            viewport = {
                "min_x": min(all_x) - 3,
                "min_y": min(all_y) - 3,
                "max_x": max(all_x) + 3,
                "max_y": max(all_y) + 3,
            }
        else:
            viewport = {"min_x": -5, "min_y": -5, "max_x": 10, "max_y": 10}

        return JSONResponse({
            "player_id": player.id,
            "player_name": player.business_name,
            "viewport": viewport,
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
        <button id="btn-fit" onclick="fitAll()" style="padding: 6px 12px; background: #38bdf8; color: #020617; border: none; cursor: pointer; font-size: 0.8rem; border-radius: 3px;">Fit All</button>
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
    <span style="display:inline-flex;align-items:center;gap:4px;">&#127959; District Biz</span>
    <span style="display:inline-flex;align-items:center;gap:4px;">&#127981; Plot Biz</span>
    <span style="display:inline-flex;align-items:center;gap:4px;">&#127963; City</span>
    <span style="display:inline-flex;align-items:center;gap:4px;">&#127758; County</span>
    <span style="color:#64748b;">|</span>
    <span style="color:#94a3b8;">Opacity = Efficiency</span>
</div>

<!-- Map container -->
<div id="map"
     style="width: 100%; height: 70vh; min-height: 480px; background: #020617;
            border: 1px solid #1e293b; border-radius: 4px; position: relative;">
    <div id="map-loading"
         style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);
                color:#64748b;font-size:0.9rem;z-index:999;">
        Loading map data&hellip;
    </div>
</div>

<div id="map-status" style="margin-top: 8px; font-size: 0.75rem; color: #64748b; text-align: right;">
    Click any element to navigate &bull; Scroll to zoom &bull; Drag to pan
</div>

<!-- Leaflet CSS -->
<link rel="stylesheet"
      href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
      integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY="
      crossorigin=""/>

<!-- Leaflet JS -->
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
        integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV/XN/WLcE="
        crossorigin=""></script>

<script>
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
const map = L.map('map', {
    crs: L.CRS.Simple,
    minZoom: -5,
    maxZoom: 6,
    zoomSnap: 0.5,
    attributionControl: false,
});

// Dark background tile (pure CSS via pane background)
map.getContainer().style.background = '#020617';

// Layer groups for toggling
const layerPlots     = L.layerGroup().addTo(map);
const layerDistricts = L.layerGroup().addTo(map);
const layerCities    = L.layerGroup().addTo(map);
const layerCounties  = L.layerGroup().addTo(map);

// We store all bounds to call fitAll()
let allBoundsPoints = [];

// ============================================================
// LOAD & RENDER
// ============================================================
function loadMapData() {
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
    (data.land_plots || []).forEach(plot => {
        const x1 = plot.grid_x, y1 = plot.grid_y;
        const x2 = x1 + 1,     y2 = y1 + 1;

        // Efficiency drives fill opacity (0.2 at 0%, 0.9 at 100%)
        const fillOpacity = 0.2 + (plot.efficiency / 100) * 0.7;

        const color = terrainColor(plot.terrain_type);

        // Border colour: brighter if business present
        const borderColor = plot.occupied_by_business_id ? '#f8fafc' : '#1e293b';
        const weight      = plot.occupied_by_business_id ? 1.5 : 0.5;

        const rect = L.rectangle(
            [[y1, x1], [y2, x2]],
            {
                color:       borderColor,
                weight:      weight,
                fillColor:   color,
                fillOpacity: fillOpacity,
            }
        );

        // Popup content
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

        rect.bindPopup(popupHtml, {
            className: 'wad-popup',
            maxWidth: 260,
        });

        // Single-click: open popup; double-click: navigate
        rect.on('dblclick', () => { window.location.href = plot.url; });

        rect.addTo(layerPlots);

        allBoundsPoints.push([y1, x1]);
        allBoundsPoints.push([y2, x2]);
    });

    // ---- DISTRICTS -------------------------------------------------
    (data.districts || []).forEach(dist => {
        const [x1, y1, x2, y2] = dist.bounds;

        const color = terrainColor(dist.terrain_type);

        let bizLine = '';
        if (dist.business_type) {
            const icon   = dist.business_active ? '&#127981;' : '&#9208;&#65039;';
            const status = dist.business_active ? 'Active' : 'Inactive';
            bizLine = `<br>${icon} <b>${dist.business_name || dist.business_type}</b> &mdash; ${status}`;
        }

        // District rectangle — slightly transparent overlay with bold border
        const rect = L.rectangle(
            [[y1, x1], [y2, x2]],
            {
                color:       color,
                weight:      2.5,
                fillColor:   color,
                fillOpacity: 0.25,
                dashArray:   '6 3',
            }
        );

        const popupHtml = `
            <div style="font-family:'JetBrains Mono',monospace;font-size:12px;color:#e5e7eb;min-width:160px">
                <b>&#127959;&#65039; ${dist.district_name}</b>
                <br><span style="color:${color}">${dist.district_type}</span> district
                <br>${dist.plots_merged} plots merged &mdash; size ${dist.size}${bizLine}
                <br>Tax: <span style="color:#94a3b8">$${dist.monthly_tax.toLocaleString()}/mo</span>
                <br><a href="${dist.url}" style="color:#38bdf8">&#8594; Manage District</a>
            </div>`;

        rect.bindPopup(popupHtml, { className: 'wad-popup', maxWidth: 260 });
        rect.on('dblclick', () => { window.location.href = dist.url; });
        rect.addTo(layerDistricts);

        // Add a centroid label marker (no circle, just a DivIcon)
        const labelIcon = L.divIcon({
            html: `<span style="font-size:9px;color:${color};font-family:monospace;white-space:nowrap;background:rgba(2,6,23,0.7);padding:1px 3px;border-radius:2px;">&#127959; ${dist.district_name}</span>`,
            className: '',
            iconAnchor: [0, 0],
        });
        L.marker([dist.center_y, dist.center_x], { icon: labelIcon, interactive: false })
         .addTo(layerDistricts);

        allBoundsPoints.push([y1, x1]);
        allBoundsPoints.push([y2, x2]);
    });

    // ---- CITIES ----------------------------------------------------
    (data.cities || []).forEach(city => {
        const cx = city.center_x, cy = city.center_y;

        const icon = L.divIcon({
            html: `<div style="font-size:22px;line-height:1;filter:drop-shadow(0 0 4px #38bdf8);">&#127961;&#65039;</div>`,
            className: '',
            iconAnchor: [11, 11],
        });

        const mayorBadge = city.is_mayor
            ? '<br><span style="color:#d4af37">&#9733; Mayor</span>' : '';

        const currLine = city.currency_type
            ? `<br>Currency: <span style="color:#f59e0b">${city.currency_type.replace(/_/g,' ')}</span>`
            : '';

        const popupHtml = `
            <div style="font-family:'JetBrains Mono',monospace;font-size:12px;color:#e5e7eb;min-width:160px">
                <b>&#127961;&#65039; ${city.name}</b>${mayorBadge}${currLine}
                <br><a href="${city.url}" style="color:#38bdf8">&#8594; City Hub</a>
            </div>`;

        const marker = L.marker([cy, cx], { icon });
        marker.bindPopup(popupHtml, { className: 'wad-popup', maxWidth: 260 });
        marker.on('dblclick', () => { window.location.href = city.url; });
        marker.addTo(layerCities);

        allBoundsPoints.push([cy - 5, cx - 5]);
        allBoundsPoints.push([cy + 5, cx + 5]);
    });

    // ---- COUNTIES --------------------------------------------------
    (data.counties || []).forEach(county => {
        const cx = county.center_x, cy = county.center_y;

        const icon = L.divIcon({
            html: `<div style="font-size:26px;line-height:1;filter:drop-shadow(0 0 6px #d4af37);">&#128506;&#65039;</div>`,
            className: '',
            iconAnchor: [13, 13],
        });

        const popupHtml = `
            <div style="font-family:'JetBrains Mono',monospace;font-size:12px;color:#e5e7eb;min-width:160px">
                <b>&#128506;&#65039; ${county.name}</b>
                <br>Token: <span style="color:#d4af37">${county.crypto_symbol}</span>
                <br><a href="${county.url}" style="color:#38bdf8">&#8594; County Hub</a>
            </div>`;

        const marker = L.marker([cy, cx], { icon });
        marker.bindPopup(popupHtml, { className: 'wad-popup', maxWidth: 260 });
        marker.on('dblclick', () => { window.location.href = county.url; });
        marker.addTo(layerCounties);

        allBoundsPoints.push([cy - 10, cx - 10]);
        allBoundsPoints.push([cy + 10, cx + 10]);
    });

    // ---- FIT VIEWPORT ----------------------------------------------
    if (allBoundsPoints.length > 0) {
        map.fitBounds(allBoundsPoints, { padding: [30, 30] });
    } else {
        map.setView([0, 0], 1);
    }

    document.getElementById('map-loading').style.display = 'none';

    const plotCount    = (data.land_plots    || []).length;
    const distCount    = (data.districts     || []).length;
    const cityCount    = (data.cities        || []).length;
    const countyCount  = (data.counties      || []).length;
    document.getElementById('map-status').textContent =
        `${plotCount} plots  \u2022  ${distCount} districts  \u2022  ${cityCount} cities  \u2022  ${countyCount} counties`;
}

function fitAll() {
    if (allBoundsPoints.length > 0) {
        map.fitBounds(allBoundsPoints, { padding: [30, 30] });
    }
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
// ZONE SEPARATORS (visual lines dividing plot / city / county zones)
// ============================================================
function drawZoneSeparators() {
    const lineStyle = { color: '#1e293b', weight: 1, dashArray: '4 6', interactive: false };

    // City zone separator
    L.polyline([
        [""" + str(int(CITY_ZONE_Y - 10)) + """, -20],
        [""" + str(int(CITY_ZONE_Y - 10)) + """, 200]
    ], lineStyle).addTo(map);
    L.marker([""" + str(int(CITY_ZONE_Y - 5)) + """, -15], {
        icon: L.divIcon({
            html: '<span style="font-size:9px;color:#334155;font-family:monospace">&#8213; CITY ZONE &#8213;</span>',
            className: '', iconAnchor: [0, 0]
        }), interactive: false
    }).addTo(map);

    // County zone separator
    L.polyline([
        [""" + str(int(COUNTY_ZONE_Y - 10)) + """, -20],
        [""" + str(int(COUNTY_ZONE_Y - 10)) + """, 200]
    ], lineStyle).addTo(map);
    L.marker([""" + str(int(COUNTY_ZONE_Y - 5)) + """, -15], {
        icon: L.divIcon({
            html: '<span style="font-size:9px;color:#334155;font-family:monospace">&#8213; COUNTY ZONE &#8213;</span>',
            className: '', iconAnchor: [0, 0]
        }), interactive: false
    }).addTo(map);
}

// ============================================================
// BOOT
// ============================================================
drawZoneSeparators();
loadMapData();
</script>
"""

    return HTMLResponse(shell("World Map", body, player.cash_balance, player.id))
