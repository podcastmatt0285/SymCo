"""
land.py

Land management module for the economic simulation.
Handles:
- Land plot creation and ownership
- Land efficiency degradation (0.00001% per minute)
- Location ratings (determines business compatibility)
- Land tax system (monthly payments to government)
- Free starter plot for new players
- Database models for land plots
"""

from datetime import datetime
from typing import Optional, List
import threading
from sqlalchemy import Column, String, Float, DateTime, Integer, Boolean, func, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

_EFF_FLOOR_COOLDOWN  = 86400     # re-notify at most once per day
_EFF_FLOOR_THRESHOLD = 50.0      # below this, business efficiency multiplier is capped


def _fire_govt_push(player_id: int, title: str, body: str, url: str = "/land"):
    """Send a government push notification (non-blocking)."""
    def _send():
        try:
            from push_ux import send_push_notification
            send_push_notification(player_id, title, body, url,
                                   notif_type="govt",
                                   tag=f"govt-{player_id}-{title[:20]}")
        except Exception as e:
            print(f"[Land] Push error: {e}")
    threading.Thread(target=_send, daemon=True).start()


def _fire_eff_floor_push(owner_id: int, plot_id: int, terrain: str, efficiency: float) -> None:
    if owner_id <= 0:
        return
    from push_ux import push_rate_ok, push_rate_mark
    db_key = f"land-eff-floor-{plot_id}"
    if not push_rate_ok(db_key, _EFF_FLOOR_COOLDOWN):
        return
    push_rate_mark(db_key)
    def _send():
        try:
            from push_ux import send_push_notification
            send_push_notification(
                owner_id,
                "Plot Efficiency Floor Reached",
                f"Plot #{plot_id} ({terrain}) is at {efficiency:.0f}% — business productivity is now capped",
                url="/land", notif_type="land", tag=f"eff-floor-{plot_id}",
            )
        except Exception as e:
            print(f"[Land] Push error for player {owner_id}: {e}")
    threading.Thread(target=_send, daemon=True).start()

# ==========================
# DATABASE SETUP
# ==========================
from database import engine, SessionLocal
Base = declarative_base()

# ==========================
# CONSTANTS
# ==========================
EFFICIENCY_DECAY_PER_TICK = 100.0 / (14 * 24 * 720)  # 100% over 14 days; 1 tick = 5s → 720 ticks/hr
STARTING_EFFICIENCY = 100.0  # All land starts at 100% efficiency

# Land hoarding tax - discourages accumulating excessive plots
HOARDING_FREE_PLOTS = 5          # First 5 plots carry no hoarding tax
HOARDING_BASE_TAX_MONTHLY = 5000.0  # $5000/month base rate per excess plot
HOARDING_HOURS_PER_MONTH = 720   # 30 days × 24 hours
GOVERNMENT_PLAYER_ID = 0

# Business types exempt from land hoarding tax (food carts / trucks occupy plots
# but are considered transient street vendors, not land holdings)
FOOD_CART_TYPES = {"fish_cart", "hot_dog_cart", "burrito_truck", "street_flower_cart"}

# Terrain types - the base land type
TERRAIN_TYPES = {
    "urban": {"description": "City center plot, high foot traffic and demand", "base_tax": 120.0},
    "prairie": {"description": "Flat grassland, good for farming", "base_tax": 50.0},
    "forest": {"description": "Wooded area, good for lumber", "base_tax": 60.0},
    "desert": {"description": "Arid land, challenging conditions", "base_tax": 30.0},
    "marsh": {"description": "Wetland, unique opportunities", "base_tax": 40.0},
    "mountain": {"description": "Rocky highlands, mining potential", "base_tax": 70.0},
    "tundra": {"description": "Cold climate, harsh conditions", "base_tax": 35.0},
    "jungle": {"description": "Dense vegetation, exotic resources", "base_tax": 55.0},
    "savanna": {"description": "Tropical grassland", "base_tax": 45.0},
    "hills": {"description": "Rolling terrain", "base_tax": 52.0},
    "island": {"description": "Isolated landmass", "base_tax": 65.0},
    "coastal": {"description": "Shoreline with ocean access, fishing and trade hub", "base_tax": 80.0},
    "ocean": {"description": "Open water, offshore and deep-sea operations", "base_tax": 100.0},
    "lake": {"description": "Freshwater lake, fishing and aquaculture potential", "base_tax": 60.0},
    "district_food": {"description": "Food production zone", "base_tax": 500.0},
    "district_hospital": {"description": "Medical services complex", "base_tax": 800.0},
    "district_industrial": {"description": "Heavy manufacturing zone", "base_tax": 600.0},
    "district_medical": {"description": "Pharmaceutical production zone", "base_tax": 750.0},
    "district_neighborhood": {"description": "Residential services hub", "base_tax": 550.0},
    "district_transport": {"description": "Transportation hub", "base_tax": 700.0},
    "district_utilities": {"description": "Utility infrastructure zone", "base_tax": 650.0},
    "district_zoo": {"description": "Wildlife conservation zone", "base_tax": 600.0},
    # Additional district terrain types used by district businesses
    "district_aerospace": {"description": "Aerospace and aviation manufacturing district", "base_tax": 900.0},
    "district_coastal": {"description": "Coastal marine and fishing industry district", "base_tax": 700.0},
    "district_education": {"description": "Schools and educational facilities district", "base_tax": 600.0},
    "district_entertainment": {"description": "Entertainment venues and media district", "base_tax": 650.0},
    "district_food_court": {"description": "Multi-vendor food service district", "base_tax": 500.0},
    "district_mall": {"description": "Premium retail shopping district", "base_tax": 700.0},
    "district_military": {"description": "Military base and defense operations", "base_tax": 800.0},
    "district_prison": {"description": "Correctional facility complex", "base_tax": 500.0},
    "district_shipyard": {"description": "Shipbuilding and marine manufacturing district", "base_tax": 750.0},
    "district_tech": {"description": "Technology and semiconductor manufacturing district", "base_tax": 850.0},
    # Legacy district terrain keys used in BUSINESS_COMPATIBILITY
    "district_airport": {"description": "Airport and aerospace terminal district", "base_tax": 900.0},
    "district_convention_center": {"description": "Convention and events district", "base_tax": 650.0},
    "district_entertainment_district": {"description": "Casino and entertainment complex", "base_tax": 650.0},
    "district_mega_mall": {"description": "Large-scale wholesale and retail district", "base_tax": 750.0},
    "district_military_base": {"description": "Military base and defense manufacturing", "base_tax": 800.0},
    "district_prison_complex": {"description": "Prison facility and support services", "base_tax": 500.0},
    "district_research_campus": {"description": "University and research facility district", "base_tax": 800.0},
    "district_seaport": {"description": "Seaport shipping and trade district", "base_tax": 750.0},
    "district_tech_park": {"description": "Technology park and data center district", "base_tax": 850.0},
    # ── Subscriber special plot terrains ──────────────────────────────────────
    "special_mint": {"description": "Precious metal minting facility (subscriber special plot)", "base_tax": 1200.0},
}

# Proximity features - special attributes (can have multiple)
PROXIMITY_FEATURES = {
    "urban": {"description": "Near city center, high demand", "tax_modifier": 2.0},
    "coastal": {"description": "Ocean access, trade benefits", "tax_modifier": 1.5},
    "riverside": {"description": "Fresh water access", "tax_modifier": 1.3},
    "lakeside": {"description": "Lake access, fishing potential", "tax_modifier": 1.2},
    "oasis": {"description": "Desert water source", "tax_modifier": 1.6},
    "hot_springs": {"description": "Geothermal activity", "tax_modifier": 1.4},
    "caves": {"description": "Natural shelter, mining opportunities", "tax_modifier": 1.1},
    "volcanic": {"description": "Volcanic soil", "tax_modifier": 1.3},
    "road": {"description": "Major transportation route", "tax_modifier": 1.25},
    "deposits": {"description": "Oil, minerals, or other extractable resources", "tax_modifier": 1.7},
    "remote": {"description": "Far from civilization", "tax_modifier": 0.7}
}

# Business type requirements (what can operate where) - ALL 138 BUSINESS TYPES
BUSINESS_COMPATIBILITY = {
    # ── Sheep & wool system ──────────────────────────────────────────────────
    "paddock":              {"allowed_terrain": ["prairie", "hills", "savanna", "mountain", "tundra"], "allowed_proximity": ["remote", "riverside", "oasis"]},
    "sheep_dog_kennel":     {"allowed_terrain": ["prairie", "hills", "forest", "mountain", "tundra"], "allowed_proximity": ["remote", "road"]},
    "wool_mill":            {"allowed_terrain": ["prairie", "hills", "savanna", "mountain", "tundra"], "allowed_proximity": ["riverside", "road", "remote"]},
    "yarn_mill":            {"allowed_terrain": ["prairie", "hills", "savanna", "forest"],           "allowed_proximity": ["riverside", "road", "urban"]},
    "thread_mill":          {"allowed_terrain": ["prairie", "hills", "savanna", "forest"],           "allowed_proximity": ["riverside", "road", "urban"]},
    "arts_and_crafts_store":{"allowed_terrain": ["prairie", "forest", "mountain", "savanna", "hills", "island", "coastal"], "allowed_proximity": ["urban", "road", "remote", "coastal", "riverside", "lakeside"]},
    "ritual_grounds":       {"allowed_terrain": ["prairie", "hills", "mountain", "desert", "savanna", "tundra", "jungle"], "allowed_proximity": ["remote", "oasis", "caves"]},
    "bookbindery": {"allowed_terrain": ['prairie', 'forest', 'hills', 'mountain', 'island'], "allowed_proximity": ['urban', 'road']},
    "dairy_and_fermentation": {"allowed_terrain": ['prairie', 'forest', 'hills', 'mountain'], "allowed_proximity": ['road', 'riverside']},
    "solar_plant": {"allowed_terrain": ['desert', 'prairie', 'savanna', 'hills', 'tundra'], "allowed_proximity": ['coastal', 'oasis', 'road', 'remote']},
    "water_facility": {"allowed_terrain": ['marsh', 'prairie', 'jungle', 'lake', 'tundra'], "allowed_proximity": ['riverside', 'lakeside', 'oasis', 'hot_springs']},
    "free_range_pasture": {"allowed_terrain": ['prairie', 'savanna'], "allowed_proximity": ['riverside', 'oasis', 'remote']},
    "rendering_plant": {"allowed_terrain": ['mountain', 'prairie', 'hills'], "allowed_proximity": ['urban', 'road']},
    "paper_mill": {"allowed_terrain": ['prairie', 'forest', 'jungle'], "allowed_proximity": ['riverside', 'road', 'urban']},
    "plantation": {"allowed_terrain": ['prairie', 'savanna', 'forest'], "allowed_proximity": ['riverside', 'oasis', 'remote']},
    "grocery_store": {"allowed_terrain": ['prairie', 'hills', 'island'], "allowed_proximity": ['urban', 'road']},
    "stationery_store": {"allowed_terrain": ['prairie', 'hills'], "allowed_proximity": ['urban']},
    "textile_and_tannery": {"allowed_terrain": ['forest', 'savanna', 'mountain', 'jungle', 'hills'], "allowed_proximity": ['urban', 'riverside', 'road']},
    "cotton_fields": {"allowed_terrain": ['prairie', 'savanna', 'hills'], "allowed_proximity": ['riverside', 'oasis', 'remote']},
    "lumber_mill": {"allowed_terrain": ['forest', 'jungle', 'mountain'], "allowed_proximity": ['riverside', 'road']},
    "mineral_mine": {"allowed_terrain": ['mountain', 'hills', 'desert', 'tundra'], "allowed_proximity": ['remote', 'road', 'caves', 'deposits']},
    "refinery": {"allowed_terrain": ['mountain', 'hills', 'prairie', 'desert'], "allowed_proximity": ['urban', 'road']},
    "fastener_factory": {"allowed_terrain": ['prairie', 'hills', 'urban'], "allowed_proximity": ['urban', 'road']},
    "apparel_factory": {"allowed_terrain": ['prairie', 'hills', 'savanna'], "allowed_proximity": ['urban', 'road']},
    "bag_and_luggage": {"allowed_terrain": ['prairie', 'hills', 'savanna'], "allowed_proximity": ['urban', 'road']},
    "cane_plantation": {"allowed_terrain": ['jungle', 'savanna', 'marsh'], "allowed_proximity": ['riverside', 'oasis', 'remote']},
    "bistro": {"allowed_terrain": ['prairie', 'hills', 'island'], "allowed_proximity": ['urban', 'lakeside']},
    "soup_kitchen": {"allowed_terrain": ['prairie', 'hills', 'savanna'], "allowed_proximity": ['urban', 'road']},
    "oil_rig": {"allowed_terrain": ['desert', 'marsh', 'ocean', 'tundra'], "allowed_proximity": ['coastal', 'remote', 'deposits']},
    "oil_refinery": {"allowed_terrain": ['urban', 'prairie', 'desert', 'coastal'], "allowed_proximity": ['road', 'urban', 'coastal']},
    "gas_station": {"allowed_terrain": ['urban', 'prairie', 'desert'], "allowed_proximity": ['urban', 'road']},
    "grain_farm": {"allowed_terrain": ['prairie', 'savanna', 'hills'], "allowed_proximity": ['riverside', 'remote']},
    "orchard": {"allowed_terrain": ['prairie', 'hills', 'forest'], "allowed_proximity": ['riverside', 'lakeside', 'road']},
    "vegetable_farm": {"allowed_terrain": ['prairie', 'savanna', 'marsh'], "allowed_proximity": ['riverside', 'oasis', 'road']},
    "vineyard_estate": {"allowed_terrain": ['hills', 'mountain'], "allowed_proximity": ['volcanic', 'riverside', 'lakeside']},
    "coffee_plantation": {"allowed_terrain": ['hills', 'mountain', 'jungle'], "allowed_proximity": ['volcanic', 'riverside']},
    "tea_plantation": {"allowed_terrain": ['hills', 'mountain', 'jungle'], "allowed_proximity": ['riverside', 'volcanic', 'lakeside']},
    "cocoa_plantation": {"allowed_terrain": ['jungle', 'island', 'marsh'], "allowed_proximity": ['riverside', 'coastal']},
    "hop_farm": {"allowed_terrain": ['prairie', 'hills', 'forest'], "allowed_proximity": ['riverside', 'road']},
    "spice_plantation": {"allowed_terrain": ['jungle', 'island', 'marsh'], "allowed_proximity": ['coastal', 'riverside']},
    "agave_plantation": {"allowed_terrain": ['desert', 'savanna'], "allowed_proximity": ['volcanic', 'road', 'remote', 'oasis']},
    "poultry_farm": {"allowed_terrain": ['prairie', 'savanna', 'hills'], "allowed_proximity": ['riverside', 'road', 'remote']},
    "apiary": {"allowed_terrain": ['prairie', 'forest', 'hills', 'savanna', 'lake'], "allowed_proximity": ['riverside', 'lakeside', 'remote']},
    "salt_works": {"allowed_terrain": ['desert', 'marsh', 'island', 'lake'], "allowed_proximity": ['coastal', 'lakeside', 'deposits']},
    "flour_mill": {"allowed_terrain": ['prairie', 'hills', 'urban'], "allowed_proximity": ['riverside', 'road', 'urban']},
    "sand_quarry": {"allowed_terrain": ['desert', 'prairie', 'hills'], "allowed_proximity": ['riverside', 'coastal', 'road', 'deposits']},
    "glass_works": {"allowed_terrain": ['desert', 'prairie', 'hills'], "allowed_proximity": ['road', 'urban']},
    "rubber_plant": {"allowed_terrain": ['jungle', 'marsh', 'coastal', 'island'], "allowed_proximity": ['road', 'urban', 'coastal', 'riverside']},
    "coffee_roastery": {"allowed_terrain": ['urban', 'prairie', 'hills'], "allowed_proximity": ['urban', 'road']},
    "chocolate_factory": {"allowed_terrain": ['urban', 'prairie'], "allowed_proximity": ['urban', 'road']},
    "malting_house": {"allowed_terrain": ['prairie', 'hills', 'urban'], "allowed_proximity": ['riverside', 'road']},
    "gelatin_plant": {"allowed_terrain": ['prairie', 'hills'], "allowed_proximity": ['road', 'urban']},
    "meat_processing": {"allowed_terrain": ['prairie', 'hills', 'mountain'], "allowed_proximity": ['road', 'urban']},
    "cooperage": {"allowed_terrain": ['forest', 'hills', 'prairie'], "allowed_proximity": ['riverside', 'road']},
    "ink_factory": {"allowed_terrain": ['prairie', 'urban', 'hills'], "allowed_proximity": ['urban', 'road']},
    "bedding_factory": {"allowed_terrain": ['prairie', 'urban', 'hills'], "allowed_proximity": ['urban', 'road']},
    "industrial_bakery": {"allowed_terrain": ['urban', 'prairie'], "allowed_proximity": ['urban', 'road']},
    "pastry_kitchen": {"allowed_terrain": ['urban', 'hills'], "allowed_proximity": ['urban']},
    "pie_bakery": {"allowed_terrain": ['urban', 'prairie'], "allowed_proximity": ['urban']},
    "cookie_factory": {"allowed_terrain": ['urban', 'prairie'], "allowed_proximity": ['urban', 'road']},
    "candy_factory": {"allowed_terrain": ['urban', 'prairie'], "allowed_proximity": ['urban', 'road']},
    "chocolate_confectioner": {"allowed_terrain": ['urban'], "allowed_proximity": ['urban']},
    "distillery": {"allowed_terrain": ['prairie', 'hills', 'mountain'], "allowed_proximity": ['riverside', 'urban', 'road']},
    "gin_distillery": {"allowed_terrain": ['hills', 'urban', 'prairie'], "allowed_proximity": ['urban', 'riverside']},
    "tequila_distillery": {"allowed_terrain": ['desert', 'savanna'], "allowed_proximity": ['volcanic', 'road']},
    "winery": {"allowed_terrain": ['hills', 'mountain'], "allowed_proximity": ['volcanic', 'lakeside', 'riverside']},
    "brewery": {"allowed_terrain": ['urban', 'prairie', 'hills'], "allowed_proximity": ['urban', 'riverside']},
    "pharmaceutical_lab": {"allowed_terrain": ['urban'], "allowed_proximity": ['urban']},
    "publishing_house": {"allowed_terrain": ['urban', 'prairie'], "allowed_proximity": ['urban', 'road']},
    "gourmet_kitchen": {"allowed_terrain": ['urban', 'hills'], "allowed_proximity": ['urban']},
    "coffeehouse_production": {"allowed_terrain": ['urban', 'hills'], "allowed_proximity": ['urban']},
    "auto_parts_factory": {"allowed_terrain": ['prairie', 'desert'], "allowed_proximity": ['road', 'urban']},
    "engine_plant": {"allowed_terrain": ['prairie', 'desert'], "allowed_proximity": ['road', 'urban']},
    "chassis_factory": {"allowed_terrain": ['prairie', 'desert'], "allowed_proximity": ['road', 'urban']},
    "auto_assembly": {"allowed_terrain": ['prairie', 'desert'], "allowed_proximity": ['road', 'urban']},
    "luxury_auto_plant": {"allowed_terrain": ['urban', 'prairie'], "allowed_proximity": ['urban']},
    "marine_factory": {"allowed_terrain": ['marsh', 'island', 'lake'], "allowed_proximity": ['coastal', 'riverside', 'lakeside']},
    "boat_yard": {"allowed_terrain": ['marsh', 'island', 'lake'], "allowed_proximity": ['coastal', 'riverside', 'lakeside']},
    "ceramics_factory": {"allowed_terrain": ['prairie', 'desert', 'hills'], "allowed_proximity": ['road', 'urban']},
    "lead_mine": {"allowed_terrain": ['mountain', 'hills', 'desert', 'tundra'], "allowed_proximity": ['remote', 'road', 'caves', 'deposits']},
    "candy_store": {"allowed_terrain": ['urban', 'prairie', 'island'], "allowed_proximity": ['urban', 'coastal']},
    "pharmacy": {"allowed_terrain": ['urban'], "allowed_proximity": ['urban', 'road']},
    "coffeehouse": {"allowed_terrain": ['urban', 'hills', 'island'], "allowed_proximity": ['urban', 'lakeside']},
    "bakery_retail": {"allowed_terrain": ['urban', 'prairie'], "allowed_proximity": ['urban']},
    "wine_bar": {"allowed_terrain": ['urban', 'hills'], "allowed_proximity": ['urban', 'lakeside']},
    "pub": {"allowed_terrain": ['urban', 'prairie'], "allowed_proximity": ['urban', 'road']},
    "auto_dealership": {"allowed_terrain": ['urban', 'prairie'], "allowed_proximity": ['urban', 'road']},
    "luxury_showroom": {"allowed_terrain": ['urban'], "allowed_proximity": ['urban']},
    "marina": {"allowed_terrain": ['marsh', 'island', 'lake'], "allowed_proximity": ['coastal', 'lakeside', 'riverside']},
    "bookstore": {"allowed_terrain": ['urban', 'prairie'], "allowed_proximity": ['urban', 'road']},
    "butcher_shop": {"allowed_terrain": ['urban', 'prairie'], "allowed_proximity": ['urban', 'road']},
    "gourmet_restaurant": {"allowed_terrain": ['urban', 'hills', 'island'], "allowed_proximity": ['urban', 'lakeside']},
    "home_goods_store": {"allowed_terrain": ['urban', 'prairie'], "allowed_proximity": ['urban', 'road']},
    "farmers_market": {"allowed_terrain": ['prairie', 'hills', 'savanna'], "allowed_proximity": ['road', 'riverside', 'remote']},
    "fashion_outlet": {"allowed_terrain": ['prairie', 'hills', 'island'], "allowed_proximity": ['urban', 'road']},
    # Marine / fishing businesses
    "trawler_fleet":          {"allowed_terrain": ['coastal', 'ocean'],                  "allowed_proximity": ['coastal']},
    "purse_seine_fleet":      {"allowed_terrain": ['coastal', 'ocean'],                  "allowed_proximity": ['coastal']},
    "deep_sea_fleet":         {"allowed_terrain": ['coastal', 'ocean'],                  "allowed_proximity": ['coastal']},
    "crustacean_trappers":    {"allowed_terrain": ['coastal', 'ocean', 'marsh'],         "allowed_proximity": ['coastal']},
    "shrimp_fleet":           {"allowed_terrain": ['coastal', 'ocean', 'marsh'],         "allowed_proximity": ['coastal']},
    "shellfish_beds":         {"allowed_terrain": ['coastal', 'marsh', 'island'],        "allowed_proximity": ['coastal']},
    "dive_operations":        {"allowed_terrain": ['coastal', 'ocean', 'island'],        "allowed_proximity": ['coastal']},
    "aquaculture_farm":       {"allowed_terrain": ['coastal', 'lake'],                   "allowed_proximity": ['coastal', 'lakeside']},
    "freshwater_fishing":     {"allowed_terrain": ['lake', 'marsh'],                     "allowed_proximity": ['lakeside', 'riverside']},
    "pearl_oyster_farm":      {"allowed_terrain": ['coastal', 'island'],                 "allowed_proximity": ['coastal']},
    "fish_processing_plant":  {"allowed_terrain": ['coastal', 'urban', 'prairie'],       "allowed_proximity": ['coastal', 'urban']},
    "cannery":                {"allowed_terrain": ['coastal', 'urban', 'prairie'],       "allowed_proximity": ['coastal', 'urban']},
    "seafood_smokehouse":     {"allowed_terrain": ['coastal', 'forest', 'hills'],        "allowed_proximity": ['coastal', 'urban']},
    "seafood_condiment_factory": {"allowed_terrain": ['coastal', 'urban', 'prairie'],   "allowed_proximity": ['coastal', 'urban']},
    "fish_market":            {"allowed_terrain": ['coastal', 'urban', 'marsh'],         "allowed_proximity": ['coastal', 'urban']},
    "seafood_restaurant":     {"allowed_terrain": ['coastal', 'urban', 'island'],        "allowed_proximity": ['coastal', 'urban']},
    "sushi_bar":              {"allowed_terrain": ['coastal', 'urban', 'island'],        "allowed_proximity": ['coastal', 'urban']},
    # Other businesses added since initial compatibility list
    "peanut_farm":            {"allowed_terrain": ['prairie', 'savanna'],                "allowed_proximity": ['riverside', 'road', 'remote']},
    "creamery":               {"allowed_terrain": ['prairie', 'hills'],                  "allowed_proximity": ['riverside', 'road', 'urban']},
    "coal_mine":              {"allowed_terrain": ['mountain', 'hills', 'tundra'],       "allowed_proximity": ['remote', 'road', 'caves', 'deposits']},
    "bottling_plant":         {"allowed_terrain": ['urban', 'prairie'],                  "allowed_proximity": ['urban', 'road', 'riverside']},
    "paint_factory":          {"allowed_terrain": ['urban', 'prairie'],                  "allowed_proximity": ['urban', 'road']},
    "personal_care_factory":  {"allowed_terrain": ['urban', 'prairie'],                  "allowed_proximity": ['urban', 'road']},
    "shoe_factory":           {"allowed_terrain": ['urban', 'prairie', 'hills'],         "allowed_proximity": ['urban', 'road']},
    "rope_works":             {"allowed_terrain": ['prairie', 'forest', 'hills'],        "allowed_proximity": ['road', 'riverside']},
    "towel_mill":             {"allowed_terrain": ['prairie', 'hills'],                  "allowed_proximity": ['urban', 'road']},
    "jeweler":                {"allowed_terrain": ['urban', 'prairie'],                  "allowed_proximity": ['urban']},
    "pet_store":              {"allowed_terrain": ['prairie', 'forest', 'desert', 'marsh', 'mountain', 'tundra', 'jungle', 'savanna', 'hills', 'island'], "allowed_proximity": ['urban', 'road', 'coastal', 'oasis', 'remote', 'riverside', 'lakeside', 'hot_springs', 'volcanic']},
    # Rice and tomato chain businesses
    "rice_paddy":             {"allowed_terrain": ['marsh', 'jungle', 'savanna', 'prairie', 'lake'],  "allowed_proximity": ['riverside', 'lakeside']},
    "sake_brewery":           {"allowed_terrain": ['urban', 'prairie', 'hills'],                       "allowed_proximity": ['urban', 'riverside']},
    "tomato_cannery":         {"allowed_terrain": ['prairie', 'savanna', 'urban'],                     "allowed_proximity": ['urban', 'road', 'riverside']},
    # Tobacco chain businesses
    "virginia_tobacco_farm":  {"allowed_terrain": ['prairie', 'hills', 'savanna'],                    "allowed_proximity": ['riverside', 'road', 'remote']},
    "burley_tobacco_farm":    {"allowed_terrain": ['hills', 'mountain', 'prairie'],                   "allowed_proximity": ['riverside', 'road', 'remote']},
    "oriental_tobacco_farm":  {"allowed_terrain": ['hills', 'mountain', 'savanna'],                   "allowed_proximity": ['volcanic', 'road', 'remote', 'riverside']},
    "cigar_wrapper_farm":     {"allowed_terrain": ['jungle', 'island', 'marsh'],                      "allowed_proximity": ['coastal', 'riverside', 'oasis']},
    "specialty_tobacco_farm": {"allowed_terrain": ['marsh', 'forest', 'hills'],                       "allowed_proximity": ['riverside', 'remote', 'road']},
    "tobacco_curing_house":   {"allowed_terrain": ['prairie', 'hills', 'forest'],                     "allowed_proximity": ['road', 'remote']},
    "cigarette_factory":      {"allowed_terrain": ['urban', 'prairie'],                               "allowed_proximity": ['urban', 'road']},
    "cigar_workshop":         {"allowed_terrain": ['urban', 'hills', 'island'],                       "allowed_proximity": ['urban', 'road']},
    "pipe_tobacco_house":     {"allowed_terrain": ['urban', 'prairie', 'hills'],                      "allowed_proximity": ['urban', 'road']},
    "snuff_and_chew_factory": {"allowed_terrain": ['urban', 'prairie'],                               "allowed_proximity": ['urban', 'road']},
    "tobacco_shop":           {"allowed_terrain": ['urban', 'prairie', 'hills', 'island'],            "allowed_proximity": ['urban', 'road']},
    # Candle chain
    "candle_maker":           {"allowed_terrain": ['urban', 'prairie', 'hills'],                      "allowed_proximity": ['urban', 'road']},
    # ── Airport district ─────────────────────────────────────────────────────
    "cargo_hub":                      {"allowed_terrain": ["district_airport"],              "allowed_proximity": ["remote", "road"]},
    "aircraft_maintenance_facility":  {"allowed_terrain": ["district_airport"],              "allowed_proximity": ["remote", "road"]},
    "duty_free_shop":                 {"allowed_terrain": ["district_airport"],              "allowed_proximity": ["remote", "road"]},
    "airport_fuel_depot":             {"allowed_terrain": ["district_airport"],              "allowed_proximity": ["remote", "road", "coastal"]},
    # ── Convention center district ────────────────────────────────────────────
    "convention_center":              {"allowed_terrain": ["district_convention_center"],    "allowed_proximity": ["urban", "road"]},
    "event_catering_service":         {"allowed_terrain": ["district_convention_center"],    "allowed_proximity": ["urban", "road"]},
    "hospitality_supply_factory":     {"allowed_terrain": ["district_convention_center"],    "allowed_proximity": ["urban", "road"]},
    # ── Entertainment district ────────────────────────────────────────────────
    "casino":                         {"allowed_terrain": ["district_entertainment_district", "district_entertainment"], "allowed_proximity": ["urban", "road", "coastal"]},
    "nightclub":                      {"allowed_terrain": ["district_entertainment_district", "district_entertainment"], "allowed_proximity": ["urban", "road"]},
    "theme_park":                     {"allowed_terrain": ["district_entertainment_district", "district_entertainment"], "allowed_proximity": ["urban", "road"]},
    "hotel":                          {"allowed_terrain": ["district_entertainment_district", "district_entertainment"], "allowed_proximity": ["urban", "road", "coastal"]},
    # ── Mega mall district ────────────────────────────────────────────────────
    "wholesale_warehouse":            {"allowed_terrain": ["district_mega_mall"],            "allowed_proximity": ["urban", "road"]},
    "furniture_megastore":            {"allowed_terrain": ["district_mega_mall"],            "allowed_proximity": ["urban", "road"]},
    "electronics_superstore":         {"allowed_terrain": ["district_mega_mall"],            "allowed_proximity": ["urban", "road"]},
    # ── Military base district ────────────────────────────────────────────────
    "munitions_depot":                {"allowed_terrain": ["district_military_base"],        "allowed_proximity": ["remote", "road"]},
    "armored_vehicle_depot":          {"allowed_terrain": ["district_military_base"],        "allowed_proximity": ["remote", "road"]},
    "military_commissary":            {"allowed_terrain": ["district_military_base"],        "allowed_proximity": ["remote", "road"]},
    # ── Prison complex district ───────────────────────────────────────────────
    "maximum_security_facility":      {"allowed_terrain": ["district_prison_complex"],       "allowed_proximity": ["remote", "road"]},
    "prison_farm_operations":         {"allowed_terrain": ["district_prison_complex"],       "allowed_proximity": ["remote", "road"]},
    "prison_workshop":                {"allowed_terrain": ["district_prison_complex"],       "allowed_proximity": ["remote", "road"]},
    # ── Research campus district ──────────────────────────────────────────────
    "biotech_lab":                    {"allowed_terrain": ["district_research_campus"],      "allowed_proximity": ["urban", "remote"]},
    "robotics_lab":                   {"allowed_terrain": ["district_research_campus"],      "allowed_proximity": ["urban", "remote"]},
    "advanced_materials_lab":         {"allowed_terrain": ["district_research_campus"],      "allowed_proximity": ["urban", "remote"]},
    "research_campus_hub":            {"allowed_terrain": ["district_research_campus"],      "allowed_proximity": ["urban", "remote"]},
    # ── Seaport district ──────────────────────────────────────────────────────
    "container_terminal":             {"allowed_terrain": ["district_seaport"],              "allowed_proximity": ["coastal", "road"]},
    "port_fuel_depot":                {"allowed_terrain": ["district_seaport"],              "allowed_proximity": ["coastal", "road"]},
    "cold_storage_warehouse":         {"allowed_terrain": ["district_seaport"],              "allowed_proximity": ["coastal", "road"]},
    "seaport_operations_hub":         {"allowed_terrain": ["district_seaport", "district_shipyard"], "allowed_proximity": ["coastal", "road"]},
    # ── Tech park district ────────────────────────────────────────────────────
    "software_company":               {"allowed_terrain": ["district_tech_park"],            "allowed_proximity": ["urban", "road", "remote"]},
    "cybersecurity_firm":             {"allowed_terrain": ["district_tech_park"],            "allowed_proximity": ["urban", "road", "remote"]},
    "data_center":                    {"allowed_terrain": ["district_tech_park"],            "allowed_proximity": ["urban", "road", "remote"]},
    "tech_startup_hub":               {"allowed_terrain": ["district_tech_park", "district_tech"], "allowed_proximity": ["urban", "road"]},
    # ── Gem & mineral system ──────────────────────────────────────────────────
    "gem_mine":                       {"allowed_terrain": ["mountain", "desert", "tundra", "jungle", "hills"],          "allowed_proximity": ["volcanic", "caves", "deposits", "remote"]},
    "alluvial_mine":                  {"allowed_terrain": ["marsh", "hills", "forest"],                                  "allowed_proximity": ["riverside", "lakeside"]},
    "mineral_processing_plant":       {"allowed_terrain": ["mountain", "hills", "prairie", "desert"],                   "allowed_proximity": ["road", "urban"]},
    "lapidary":                       {"allowed_terrain": ["urban", "prairie", "hills"],                                 "allowed_proximity": ["urban", "road"]},
    "crystal_shop":                   {"allowed_terrain": ["urban", "prairie", "hills", "island", "coastal"],           "allowed_proximity": ["urban", "road"]},
    "quartz_oscillator_plant":        {"allowed_terrain": ["urban", "prairie", "hills", "mountain"],                    "allowed_proximity": ["road", "urban"]},
    # ── Flower & botanical system ─────────────────────────────────────────────
    "flower_farm":                    {"allowed_terrain": ["prairie", "hills", "marsh", "savanna", "jungle", "island"], "allowed_proximity": ["remote", "riverside"]},
    "flower_shop":                    {"allowed_terrain": ["urban", "prairie", "hills"],                                 "allowed_proximity": ["urban", "road"]},
    "floral_studio":                  {"allowed_terrain": ["urban", "prairie", "hills"],                                 "allowed_proximity": ["urban", "road"]},
    "essential_oil_distillery":       {"allowed_terrain": ["prairie", "forest", "hills"],                               "allowed_proximity": ["riverside", "urban"]},
    "botanical_extract_lab":          {"allowed_terrain": ["urban", "prairie", "hills"],                                 "allowed_proximity": ["urban", "road"]},
    "street_flower_cart":             {"allowed_terrain": ["prairie", "forest", "desert", "marsh", "mountain", "tundra", "jungle", "savanna", "hills", "island", "coastal", "lake"], "allowed_proximity": ["urban", "road", "remote", "riverside", "lakeside", "oasis", "hot_springs", "caves", "volcanic", "deposits"]},
    # ── Food carts ───────────────────────────────────────────────────────────
    "fish_cart":                      {"allowed_terrain": ["coastal", "island", "urban", "desert", "lake"],             "allowed_proximity": ["urban", "road", "hot_springs"]},
    "hot_dog_cart":                   {"allowed_terrain": ["coastal", "island", "urban", "desert", "lake"],             "allowed_proximity": ["urban", "road", "hot_springs"]},
    "burrito_truck":                  {"allowed_terrain": ["coastal", "island", "urban", "desert", "lake"],             "allowed_proximity": ["urban", "road", "hot_springs"]},
    # ── Specialty production ──────────────────────────────────────────────────
    "bastilla_kitchen":               {"allowed_terrain": ["urban", "prairie"],                                          "allowed_proximity": ["urban", "road"]},
    "tallow_works":                   {"allowed_terrain": ["urban", "prairie", "hills"],                                 "allowed_proximity": ["urban", "road"]},

    # ── Aerospace / space ────────────────────────────────────────────────────
    "aircraft_assembly":              {"allowed_terrain": ["district_aerospace"],                        "allowed_proximity": ["remote", "road"]},
    "aircraft_parts_factory":         {"allowed_terrain": ["district_aerospace"],                        "allowed_proximity": ["remote", "road"]},
    "heat_shield_factory":            {"allowed_terrain": ["district_aerospace"],                        "allowed_proximity": ["remote", "road"]},
    "jet_engine_factory":             {"allowed_terrain": ["district_aerospace"],                        "allowed_proximity": ["remote", "road"]},
    "military_aircraft_plant":        {"allowed_terrain": ["district_aerospace", "district_military"],   "allowed_proximity": ["remote", "road"]},
    "reusable_rocket_program":        {"allowed_terrain": ["district_aerospace"],                        "allowed_proximity": ["remote", "road"]},
    "rocket_propellant_plant":        {"allowed_terrain": ["district_aerospace"],                        "allowed_proximity": ["remote", "road"]},
    "satellite_assembly_facility":    {"allowed_terrain": ["district_aerospace"],                        "allowed_proximity": ["remote", "road"]},
    "satellite_components_factory":   {"allowed_terrain": ["district_aerospace"],                        "allowed_proximity": ["remote", "road"]},
    "space_launch_complex":           {"allowed_terrain": ["district_aerospace"],                        "allowed_proximity": ["remote", "road", "coastal"]},
    # ── Technology & data ────────────────────────────────────────────────────
    "5g_tower_factory":               {"allowed_terrain": ["district_tech", "district_tech_park"],       "allowed_proximity": ["urban", "road", "remote"]},
    "ai_supercomputer_campus":        {"allowed_terrain": ["district_tech_park", "district_research_campus"], "allowed_proximity": ["urban", "road", "remote"]},
    "autonomous_vehicle_testing_complex": {"allowed_terrain": ["district_tech", "district_industrial"],  "allowed_proximity": ["urban", "road", "remote"]},
    "cdn_campus":                     {"allowed_terrain": ["district_tech_park"],                        "allowed_proximity": ["urban", "road", "remote"]},
    "defense_electronics_factory":    {"allowed_terrain": ["district_tech", "district_military"],        "allowed_proximity": ["urban", "road", "remote"]},
    "display_factory":                {"allowed_terrain": ["district_tech", "district_industrial"],      "allowed_proximity": ["urban", "road"]},
    "electronics_factory":            {"allowed_terrain": ["district_tech", "district_industrial"],      "allowed_proximity": ["urban", "road"]},
    "hyperscale_data_center":         {"allowed_terrain": ["district_tech_park"],                        "allowed_proximity": ["urban", "road", "remote"]},
    "internet_exchange_point":        {"allowed_terrain": ["district_tech_park"],                        "allowed_proximity": ["urban", "road"]},
    "quantum_chip_fab":               {"allowed_terrain": ["district_tech", "district_research_campus"], "allowed_proximity": ["urban", "road", "remote"]},
    "semiconductor_fab":              {"allowed_terrain": ["district_tech"],                             "allowed_proximity": ["urban", "road"]},
    "server_farm_factory":            {"allowed_terrain": ["district_tech_park"],                        "allowed_proximity": ["urban", "road", "remote"]},
    "storage_media_factory":          {"allowed_terrain": ["district_tech", "district_tech_park"],       "allowed_proximity": ["urban", "road"]},
    "telecom_switching_center":       {"allowed_terrain": ["district_tech_park", "district_tech"],       "allowed_proximity": ["urban", "road"]},
    # ── Research campus ──────────────────────────────────────────────────────
    "cryogenics_plant":               {"allowed_terrain": ["district_research_campus", "district_industrial"], "allowed_proximity": ["urban", "remote"]},
    "cryostat_factory":               {"allowed_terrain": ["district_research_campus"],                  "allowed_proximity": ["urban", "remote"]},
    "gravitational_wave_observatory": {"allowed_terrain": ["district_research_campus"],                  "allowed_proximity": ["remote"]},
    "humanoid_robotics_lab":          {"allowed_terrain": ["district_research_campus", "district_tech_park"], "allowed_proximity": ["urban", "road", "remote"]},
    "nuclear_research_reactor":       {"allowed_terrain": ["district_research_campus"],                  "allowed_proximity": ["remote", "road"]},
    "particle_accelerator":           {"allowed_terrain": ["district_research_campus"],                  "allowed_proximity": ["remote", "road"]},
    "quantum_computing_campus":       {"allowed_terrain": ["district_tech_park", "district_research_campus"], "allowed_proximity": ["urban", "road", "remote"]},
    "radio_telescope_array":          {"allowed_terrain": ["district_research_campus"],                  "allowed_proximity": ["remote"]},
    "scientific_equipment_factory":   {"allowed_terrain": ["district_research_campus", "district_tech"], "allowed_proximity": ["urban", "road"]},
    # ── Heavy industry ───────────────────────────────────────────────────────
    "alloy_forge":                    {"allowed_terrain": ["district_industrial"],                       "allowed_proximity": ["urban", "road"]},
    "aluminum_foundry":               {"allowed_terrain": ["district_industrial"],                       "allowed_proximity": ["urban", "road"]},
    "appliance_factory":              {"allowed_terrain": ["district_industrial"],                       "allowed_proximity": ["urban", "road"]},
    "battery_gigafactory":            {"allowed_terrain": ["district_industrial"],                       "allowed_proximity": ["urban", "road", "remote"]},
    "chemical_plant":                 {"allowed_terrain": ["district_industrial"],                       "allowed_proximity": ["urban", "road"]},
    "concrete_plant":                 {"allowed_terrain": ["district_industrial"],                       "allowed_proximity": ["urban", "road"]},
    "emergency_vehicle_factory":      {"allowed_terrain": ["district_industrial"],                       "allowed_proximity": ["urban", "road"]},
    "energy_infrastructure_factory":  {"allowed_terrain": ["district_industrial", "district_utilities"], "allowed_proximity": ["urban", "road"]},
    "food_packaging_factory":         {"allowed_terrain": ["district_food", "district_industrial"],      "allowed_proximity": ["urban", "road"]},
    "gas_refinery":                   {"allowed_terrain": ["district_industrial"],                       "allowed_proximity": ["road", "coastal"]},
    "plastics_factory":               {"allowed_terrain": ["district_industrial"],                       "allowed_proximity": ["urban", "road"]},
    "rail_factory":                   {"allowed_terrain": ["district_industrial", "district_transport"], "allowed_proximity": ["urban", "road"]},
    "rare_earth_processor":           {"allowed_terrain": ["district_industrial"],                       "allowed_proximity": ["urban", "road"]},
    "steel_mill":                     {"allowed_terrain": ["district_industrial"],                       "allowed_proximity": ["urban", "road"]},
    "titanium_smelter":               {"allowed_terrain": ["district_industrial"],                       "allowed_proximity": ["urban", "road"]},
    "train_parts_factory":            {"allowed_terrain": ["district_industrial", "district_transport"], "allowed_proximity": ["urban", "road"]},
    "truck_factory":                  {"allowed_terrain": ["district_industrial"],                       "allowed_proximity": ["urban", "road"]},
    "wire_plant":                     {"allowed_terrain": ["district_industrial"],                       "allowed_proximity": ["urban", "road"]},
    # ── Transport district ───────────────────────────────────────────────────
    "bus_factory":                    {"allowed_terrain": ["district_industrial", "district_transport"], "allowed_proximity": ["urban", "road"]},
    "bus_parts_factory":              {"allowed_terrain": ["district_industrial", "district_transport"], "allowed_proximity": ["urban", "road"]},
    "transportation_district":        {"allowed_terrain": ["district_transport"],                        "allowed_proximity": ["urban", "road"]},
    # ── Utilities ────────────────────────────────────────────────────────────
    "power_company":                  {"allowed_terrain": ["district_utilities"],                        "allowed_proximity": ["urban", "road", "remote"]},
    "tokamak_fusion_reactor":         {"allowed_terrain": ["district_utilities", "district_research_campus"], "allowed_proximity": ["remote", "road"]},
    "water_treatment":                {"allowed_terrain": ["district_utilities"],                        "allowed_proximity": ["urban", "road", "riverside"]},
    # ── Military ─────────────────────────────────────────────────────────────
    "armor_systems_factory":          {"allowed_terrain": ["district_military", "district_military_base"], "allowed_proximity": ["remote", "road"]},
    "military_base_district":         {"allowed_terrain": ["district_military_base"],                    "allowed_proximity": ["remote", "road"]},
    "military_shipyard":              {"allowed_terrain": ["district_shipyard", "district_military"],    "allowed_proximity": ["coastal", "road"]},
    "military_support_facility":      {"allowed_terrain": ["district_military", "district_military_base"], "allowed_proximity": ["remote", "road"]},
    "military_training_center":       {"allowed_terrain": ["district_military", "district_military_base"], "allowed_proximity": ["remote", "road"]},
    "military_vehicle_plant":         {"allowed_terrain": ["district_military", "district_military_base"], "allowed_proximity": ["remote", "road"]},
    "security_equipment_factory":     {"allowed_terrain": ["district_military", "district_tech"],        "allowed_proximity": ["urban", "road"]},
    "tactical_gear_factory":          {"allowed_terrain": ["district_military", "district_military_base"], "allowed_proximity": ["remote", "road"]},
    "weapons_factory":                {"allowed_terrain": ["district_military", "district_industrial"],  "allowed_proximity": ["remote", "road"]},
    # ── Shipyard district ────────────────────────────────────────────────────
    "marine_parts_factory":           {"allowed_terrain": ["district_shipyard", "district_coastal"],     "allowed_proximity": ["coastal", "road"]},
    "naval_shipyard":                 {"allowed_terrain": ["district_shipyard", "district_military"],           "allowed_proximity": ["coastal", "road"]},
    "shipyard":                       {"allowed_terrain": ["district_shipyard"],                         "allowed_proximity": ["coastal", "road"]},
    "submarine_cable_terminal":       {"allowed_terrain": ["district_seaport", "district_tech_park"],    "allowed_proximity": ["coastal", "road"]},
    # ── Entertainment district ────────────────────────────────────────────────
    "casino_equipment_factory":       {"allowed_terrain": ["district_entertainment_district", "district_industrial"], "allowed_proximity": ["urban", "road"]},
    "cinema_production":              {"allowed_terrain": ["district_entertainment"],                    "allowed_proximity": ["urban", "road"]},
    "concert_production":             {"allowed_terrain": ["district_entertainment"],                    "allowed_proximity": ["urban", "road"]},
    "entertainment_district":         {"allowed_terrain": ["district_entertainment"],                    "allowed_proximity": ["urban", "road"]},
    "sports_team_operations":         {"allowed_terrain": ["district_entertainment"],                    "allowed_proximity": ["urban", "road"]},
    "stadium_construction":           {"allowed_terrain": ["district_entertainment"],                    "allowed_proximity": ["urban", "road"]},
    # ── Food / food-court district ────────────────────────────────────────────
    "beverage_production":            {"allowed_terrain": ["district_food", "district_food_court"],      "allowed_proximity": ["urban", "road"]},
    "fast_food_kitchen":              {"allowed_terrain": ["district_food_court"],                       "allowed_proximity": ["urban", "road"]},
    "food_court_district":            {"allowed_terrain": ["district_food_court"],                       "allowed_proximity": ["urban", "road"]},
    "international_cuisine_kitchen":  {"allowed_terrain": ["district_food", "district_food_court"],      "allowed_proximity": ["urban", "road"]},
    "tagine_house":                   {"allowed_terrain": ["district_food_court"],                       "allowed_proximity": ["urban", "road"]},
    # ── Convention center ─────────────────────────────────────────────────────
    "floral_event_services":          {"allowed_terrain": ["district_convention_center"],                "allowed_proximity": ["urban", "road"]},
    # ── Mall / retail district ────────────────────────────────────────────────
    "crystal_market_cart":            {"allowed_terrain": ["district_mall"],                             "allowed_proximity": ["urban", "road"]},
    "flower_market_district":         {"allowed_terrain": ["district_mall"],                             "allowed_proximity": ["urban", "road"]},
    "gem_exchange_district":          {"allowed_terrain": ["district_mall"],                             "allowed_proximity": ["urban", "road"]},
    "luxury_jewelry_boutique":        {"allowed_terrain": ["district_mall"],                             "allowed_proximity": ["urban", "road"]},
    "perfume_atelier":                {"allowed_terrain": ["district_mall"],                             "allowed_proximity": ["urban", "road"]},
    "shopping_mall_district":         {"allowed_terrain": ["district_mall"],                             "allowed_proximity": ["urban", "road"]},
    # ── Education district ────────────────────────────────────────────────────
    "classroom_furniture_factory":    {"allowed_terrain": ["district_education"],                        "allowed_proximity": ["urban", "road"]},
    "education_district":             {"allowed_terrain": ["district_education"],                        "allowed_proximity": ["urban", "road"]},
    "educational_publishing":         {"allowed_terrain": ["district_education"],                        "allowed_proximity": ["urban", "road"]},
    "school_cafeteria":               {"allowed_terrain": ["district_education"],                        "allowed_proximity": ["urban", "road"]},
    "school_supplies_factory":        {"allowed_terrain": ["district_education"],                        "allowed_proximity": ["urban", "road"]},
    "school_uniform_factory":         {"allowed_terrain": ["district_education"],                        "allowed_proximity": ["urban", "road"]},
    # ── Medical / hospital district ───────────────────────────────────────────
    "hospital_district":              {"allowed_terrain": ["district_hospital"],                         "allowed_proximity": ["urban", "road"]},
    "medical_equipment_factory":      {"allowed_terrain": ["district_medical", "district_hospital"],     "allowed_proximity": ["urban", "road"]},
    "medical_supplies_factory":       {"allowed_terrain": ["district_medical"],                          "allowed_proximity": ["urban", "road"]},
    "pharmaceutical_plant":           {"allowed_terrain": ["district_medical"],                          "allowed_proximity": ["urban", "road"]},
    # ── Zoo / wildlife district ───────────────────────────────────────────────
    "african_wildlife_preserve":      {"allowed_terrain": ["district_zoo"],                              "allowed_proximity": ["remote", "road"]},
    "arctic_habitat_center":          {"allowed_terrain": ["district_zoo"],                              "allowed_proximity": ["remote", "road"]},
    "aviary_sanctuary":               {"allowed_terrain": ["district_zoo"],                              "allowed_proximity": ["urban", "remote", "road"]},
    "botanical_garden":               {"allowed_terrain": ["district_zoo", "district_research_campus"],  "allowed_proximity": ["urban", "remote", "road"]},
    "exotic_animal_facility":         {"allowed_terrain": ["district_zoo"],                              "allowed_proximity": ["remote", "road"]},
    "marine_life_aquarium":           {"allowed_terrain": ["district_coastal", "district_zoo"],          "allowed_proximity": ["coastal", "urban"]},
    "primate_conservation":           {"allowed_terrain": ["district_zoo"],                              "allowed_proximity": ["remote", "road"]},
    "sturgeon_farm":                  {"allowed_terrain": ["district_coastal"],                          "allowed_proximity": ["coastal", "lakeside"]},
    "zoo_district":                   {"allowed_terrain": ["district_zoo"],                              "allowed_proximity": ["remote", "road"]},
    "zoo_infrastructure_factory":     {"allowed_terrain": ["district_zoo", "district_industrial"],       "allowed_proximity": ["remote", "road"]},
    "zoo_supplies_factory":           {"allowed_terrain": ["district_zoo"],                              "allowed_proximity": ["urban", "road"]},
    # ── Prison complex ────────────────────────────────────────────────────────
    "prison_district":                {"allowed_terrain": ["district_prison_complex", "district_prison"], "allowed_proximity": ["remote", "road"]},
    "prison_food_service":            {"allowed_terrain": ["district_prison_complex", "district_prison"], "allowed_proximity": ["remote", "road"]},
    "prison_rehabilitation_center":   {"allowed_terrain": ["district_prison_complex", "district_prison"], "allowed_proximity": ["remote", "road"]},
    "prison_security_factory":        {"allowed_terrain": ["district_prison_complex", "district_prison"], "allowed_proximity": ["remote", "road"]},
    "prison_supply_factory":          {"allowed_terrain": ["district_prison_complex", "district_prison"], "allowed_proximity": ["remote", "road"]},
    # ── Neighborhood district ─────────────────────────────────────────────────
    "neighborhood_district":          {"allowed_terrain": ["district_neighborhood"],                     "allowed_proximity": ["urban", "road"]},
    # ── Subscriber special plots: mint businesses ─────────────────────────────
    "mint_au24":   {"allowed_terrain": ["special_mint"], "allowed_proximity": []},
    "mint_au22":   {"allowed_terrain": ["special_mint"], "allowed_proximity": []},
    "mint_ag999":  {"allowed_terrain": ["special_mint"], "allowed_proximity": []},
    "mint_ag925":  {"allowed_terrain": ["special_mint"], "allowed_proximity": []},
    "mint_pt9995": {"allowed_terrain": ["special_mint"], "allowed_proximity": []},
    "mint_pt950":  {"allowed_terrain": ["special_mint"], "allowed_proximity": []},
}

# ==========================
# DATABASE MODELS
# ==========================
class LandPlot(Base):
    """
    Land plot model.
    Represents a single plot of land in the game.
    """
    __tablename__ = "land_plots"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, index=True, nullable=False)  # Player ID who owns this

    # Land attributes
    terrain_type = Column(String, nullable=False)  # prairie, desert, mountain, etc.
    proximity_features = Column(String, nullable=True)  # Comma-separated: "coastal,riverside"
    efficiency = Column(Float, default=STARTING_EFFICIENCY)  # Starts at 100%, degrades over time
    size = Column(Float, default=1.0)  # Size in arbitrary units (1.0 = standard plot)

    # Tax system
    monthly_tax = Column(Float, nullable=False)  # Tax amount owed per month
    last_tax_payment = Column(DateTime, default=datetime.utcnow)

    # Business occupation
    occupied_by_business_id = Column(Integer, index=True, nullable=True)  # NULL if vacant

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    is_starter_plot = Column(Boolean, default=False)  # True if this was the free starting plot

    # Government/Bank flag
    is_government_owned = Column(Boolean, index=True, default=False)  # True if owned by AI gov/bank

    # Tutorial reward flag - permanently tax-free, can be sold at market
    is_tutorial_reward = Column(Boolean, default=False)

    # Set True while an active LandRestoration job covers this plot
    is_restoring = Column(Boolean, default=False)

    # Tracks the highest efficiency a plot has ever been restored to.
    # Starts at 100.0; grows by 1.5× each completed restoration.
    # The next restoration targets max_efficiency * 1.5.
    max_efficiency = Column(Float, default=100.0)

    # Per-plot restoration target set at job start (max_efficiency * 1.5).
    # Cleared (set NULL) when restoration completes.
    restoration_target = Column(Float, nullable=True)

    # Composite index for efficiency degradation queries (efficiency > 0)
    __table_args__ = (
        Index('ix_land_plots_efficiency', 'efficiency'),
        Index('ix_land_plots_gov_tax', 'is_government_owned', 'monthly_tax'),
    )


# ==========================
# IN-MEMORY STATE
# ==========================
# Track last tick for efficiency degradation
last_efficiency_update_tick = 0

# Track last month for tax collection
last_tax_month = datetime.utcnow().month
# Track last hoarding tax collection time for hourly deduction
last_hoarding_collection: Optional[datetime] = None


# ==========================
# HELPER FUNCTIONS
# ==========================
def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        return db
    except Exception as e:
        print(f"[Land] Database error: {e}")
        db.close()
        raise


def create_land_plot(
    owner_id: int,
    terrain_type: str = "prairie",
    proximity_features: List[str] = None,
    size: float = 1.0,
    is_starter: bool = False,
    is_government: bool = False
) -> LandPlot:
    """
    Create a new land plot.
    
    Args:
        owner_id: Player ID who will own this plot
        terrain_type: Type of terrain (prairie, desert, mountain, etc.)
        proximity_features: List of proximity features (coastal, riverside, etc.)
        size: Size of the plot (1.0 = standard)
        is_starter: Whether this is a free starter plot
        is_government: Whether this is government-owned
    
    Returns:
        Created LandPlot instance
    """
    db = get_db()
    
    if terrain_type not in TERRAIN_TYPES:
        terrain_type = "prairie"
    
    # Calculate monthly tax based on terrain and proximity
    base_tax = TERRAIN_TYPES[terrain_type]["base_tax"]
    tax_modifier = 1.0
    
    # Apply proximity modifiers
    if proximity_features:
        for feature in proximity_features:
            if feature in PROXIMITY_FEATURES:
                tax_modifier *= PROXIMITY_FEATURES[feature]["tax_modifier"]
    
    monthly_tax = base_tax * size * tax_modifier
    
    # Starter plots have reduced tax
    if is_starter:
        monthly_tax *= 0.5
    
    # Store proximity features as comma-separated string
    proximity_str = ",".join(proximity_features) if proximity_features else None
    
    plot = LandPlot(
        owner_id=owner_id,
        terrain_type=terrain_type,
        proximity_features=proximity_str,
        efficiency=STARTING_EFFICIENCY,
        size=size,
        monthly_tax=monthly_tax,
        is_starter_plot=is_starter,
        is_government_owned=is_government
    )
    
    db.add(plot)
    db.commit()
    db.refresh(plot)
    db.close()
    
    features_str = f" + {proximity_str}" if proximity_str else ""
    print(f"[Land] Created plot {plot.id} for player {owner_id} ({terrain_type}{features_str}, tax: ${monthly_tax:.2f}/mo)")
    
    return plot


def get_player_land(player_id: int) -> List[LandPlot]:
    """Get all land plots owned by a player."""
    db = get_db()
    plots = db.query(LandPlot).filter(LandPlot.owner_id == player_id).all()
    db.close()
    return plots


def count_player_land(player_id: int) -> int:
    """Return the number of land plots owned by a player (COUNT query, no row fetch)."""
    db = get_db()
    n = db.query(LandPlot).filter(LandPlot.owner_id == player_id).count()
    db.close()
    return n


def get_vacant_land(player_id: int) -> List[LandPlot]:
    """Get all vacant land plots owned by a player."""
    db = get_db()
    plots = db.query(LandPlot).filter(
        LandPlot.owner_id == player_id,
        LandPlot.occupied_by_business_id == None
    ).all()
    db.close()
    return plots


def transfer_land(plot_id: int, new_owner_id: int) -> bool:
    """
    Transfer land ownership.
    Used by market when land is sold.
    
    Returns:
        True if successful, False if plot doesn't exist or is occupied
    """
    db = get_db()
    
    plot = db.query(LandPlot).filter(LandPlot.id == plot_id).first()
    
    if not plot:
        db.close()
        return False
    
    # Cannot transfer occupied land (business must be removed first)
    if plot.occupied_by_business_id is not None:
        db.close()
        return False
    
    plot.owner_id = new_owner_id
    plot.is_government_owned = False
    db.commit()
    db.close()
    
    print(f"[Land] Plot {plot_id} transferred to player {new_owner_id}")
    return True


def occupy_land(plot_id: int, business_id: int) -> bool:
    """
    Mark land as occupied by a business.
    
    Returns:
        True if successful, False if already occupied
    """
    db = get_db()
    
    plot = db.query(LandPlot).filter(LandPlot.id == plot_id).first()
    
    if not plot:
        db.close()
        return False
    
    if plot.occupied_by_business_id is not None:
        db.close()
        return False
    
    plot.occupied_by_business_id = business_id
    db.commit()
    db.close()
    
    return True


def vacate_land(plot_id: int) -> bool:
    """
    Mark land as vacant (business removed).
    
    Returns:
        True if successful
    """
    db = get_db()
    
    plot = db.query(LandPlot).filter(LandPlot.id == plot_id).first()
    
    if not plot:
        db.close()
        return False
    
    plot.occupied_by_business_id = None
    db.commit()
    db.close()
    
    return True


def create_starter_plot(player_id: int) -> LandPlot:
    """
    Create the free starter plot for a new player.
    Always prairie with riverside access for easy farming.
    """
    return create_land_plot(
        owner_id=player_id,
        terrain_type="prairie",
        proximity_features=["riverside"],
        size=1.0,
        is_starter=True
    )


def degrade_efficiency(current_tick: int):
    """
    Degrade efficiency of all land plots.
    Called every tick.
    Efficiency decreases by 0.00001% per minute (per 60 ticks).
    Uses a single bulk SQL UPDATE instead of loading all rows into Python.
    """
    global last_efficiency_update_tick

    db = get_db()

    # Single bulk UPDATE: subtract decay from all plots with efficiency > 0
    # Tutorial reward plots and actively-restoring plots are excluded.
    db.query(LandPlot).filter(
        LandPlot.efficiency > 0,
        LandPlot.is_tutorial_reward == False,
        LandPlot.is_restoring == False,
    ).update(
        {LandPlot.efficiency: func.greatest(0, LandPlot.efficiency - EFFICIENCY_DECAY_PER_TICK)},
        synchronize_session=False
    )

    db.commit()

    # Notify owners whose plots just crossed the efficiency floor
    floor_plots = db.query(LandPlot).filter(
        LandPlot.owner_id > 0,
        LandPlot.efficiency <= _EFF_FLOOR_THRESHOLD,
        LandPlot.efficiency > 0,
        LandPlot.is_tutorial_reward == False,
        LandPlot.is_restoring == False,
    ).all()
    for p in floor_plots:
        _fire_eff_floor_push(p.owner_id, p.id, p.terrain_type or "unknown", p.efficiency)

    db.close()
    last_efficiency_update_tick = current_tick


def collect_monthly_taxes(current_month: int):
    """
    Collect monthly taxes from all land plots.
    Called when month changes.
    Uses bulk SQL operations instead of loading all rows.
    Skips tutorial reward plots (permanently tax-free).
    """
    db = get_db()

    # Calculate total tax using SQL SUM (exclude government and tutorial reward plots)
    total_tax_collected = db.query(func.sum(LandPlot.monthly_tax)).filter(
        LandPlot.is_government_owned == False,
        LandPlot.is_tutorial_reward == False
    ).scalar() or 0.0

    # Bulk update last_tax_payment for all non-government, non-tutorial-reward plots
    db.query(LandPlot).filter(
        LandPlot.is_government_owned == False,
        LandPlot.is_tutorial_reward == False
    ).update(
        {LandPlot.last_tax_payment: datetime.utcnow()},
        synchronize_session=False
    )

    db.commit()
    db.close()

    print(f"[Land] Monthly tax collection: ${total_tax_collected:.2f}")


def get_land_stats() -> dict:
    """Get statistics about all land in the game using SQL aggregation."""
    db = get_db()

    total_plots = db.query(LandPlot).count()
    occupied_plots = db.query(LandPlot).filter(LandPlot.occupied_by_business_id != None).count()
    government_plots = db.query(LandPlot).filter(LandPlot.is_government_owned == True).count()

    # Use SQL AVG instead of fetching all rows
    avg_eff_value = db.query(func.avg(LandPlot.efficiency)).scalar() or 100.0

    db.close()

    return {
        "total_plots": total_plots,
        "occupied_plots": occupied_plots,
        "vacant_plots": total_plots - occupied_plots,
        "government_plots": government_plots,
        "player_plots": total_plots - government_plots,
        "average_efficiency": avg_eff_value
    }

def get_land_plot(plot_id: int) -> Optional[LandPlot]:
    db = get_db()
    plot = db.query(LandPlot).filter(LandPlot.id == plot_id).first()
    db.close()
    return plot

# ==========================
# HOARDING TAX SYSTEM
# ==========================

def _hoarding_fib_multiplier(excess_index: int) -> float:
    """
    Calculate the hoarding tax multiplier for a given excess plot index.
    Uses a Fibonacci-based sequence for tiered increases.

    Multipliers: 1.0, 1.1, 1.2, 1.3, 1.5, 1.8, 2.3, 3.1, 4.4, ...
    The offset from 1.0 (×10) follows: 0, 1, 2, 3, 5, 8, 13, 21, 34, ...
    Seeds [0, 1, 2], then each value = sum of previous two.
    Capped at index 200 to prevent float overflow (seq[1476] > float max).
    """
    if excess_index <= 0:
        return 1.0
    # Cap at 200 — seq[200] ≈ 2.8e41, multiplier ≈ 2.8e40 — effectively infinite tax
    safe_index = min(excess_index, 200)
    seq = [0, 1, 2]
    while len(seq) <= safe_index:
        seq.append(seq[-1] + seq[-2])
    return 1.0 + seq[safe_index] / 10.0


def calculate_player_hoarding_tax(plot_count: int) -> dict:
    """
    Calculate the hoarding tax breakdown for a player with a given number of plots.

    Returns:
        dict with monthly_total, hourly_total, excess_plots, and per-plot breakdown
    """
    if plot_count <= HOARDING_FREE_PLOTS:
        return {
            "excess_plots": 0,
            "monthly_total": 0.0,
            "hourly_total": 0.0,
            "breakdown": []
        }

    excess = plot_count - HOARDING_FREE_PLOTS
    breakdown = []
    monthly_total = 0.0

    for i in range(excess):
        multiplier = _hoarding_fib_multiplier(i)
        monthly = HOARDING_BASE_TAX_MONTHLY * multiplier
        monthly_total += monthly
        breakdown.append({
            "plot_number": HOARDING_FREE_PLOTS + i + 1,
            "multiplier": multiplier,
            "monthly_tax": monthly
        })

    return {
        "excess_plots": excess,
        "monthly_total": monthly_total,
        "hourly_total": monthly_total / HOARDING_HOURS_PER_MONTH,
        "breakdown": breakdown
    }


def collect_hoarding_taxes():
    """
    Collect hourly hoarding tax from players with more than 5 plots.
    Each excess plot carries a $5000/month base tax with Fibonacci-scaled multipliers.
    Paid hourly as a cash sink to discourage land hoarding.
    """
    from auth import Player
    from stats_ux import log_transaction

    db = get_db()

    # Collect land_plot_ids occupied by food carts (exempt from hoarding count)
    from business import Business as _Business
    food_cart_plot_ids = [
        r.land_plot_id for r in db.query(_Business.land_plot_id).filter(
            _Business.business_type.in_(FOOD_CART_TYPES),
            _Business.land_plot_id != None
        ).all()
    ]

    # Find players with more than HOARDING_FREE_PLOTS plots (exclude government,
    # tutorial reward plots, and food-cart plots)
    plot_counts = db.query(
        LandPlot.owner_id,
        func.count(LandPlot.id)
    ).filter(
        LandPlot.is_government_owned == False,
        LandPlot.is_tutorial_reward == False,
        ~LandPlot.id.in_(food_cart_plot_ids)
    ).group_by(LandPlot.owner_id).having(
        func.count(LandPlot.id) > HOARDING_FREE_PLOTS
    ).all()

    total_collected = 0.0

    for owner_id, plot_count in plot_counts:
        if owner_id == GOVERNMENT_PLAYER_ID:
            continue

        tax_info = calculate_player_hoarding_tax(plot_count)
        hourly_payment = tax_info["hourly_total"]

        # Apply easement_neg / land-effect exec bonus to reduce hoarding tax
        try:
            from executive import get_player_job_bonus
            _land_bonus = get_player_job_bonus(db, owner_id, "land")
            if _land_bonus > 0:
                hourly_payment = round(hourly_payment * max(0.05, 1.0 - _land_bonus), 2)
        except Exception:
            pass

        if hourly_payment <= 0:
            continue

        player = db.query(Player).filter(Player.id == owner_id).first()
        if not player:
            continue

        from reserve_banks import get_usd_balance, debit_usd
        current_balance = get_usd_balance(owner_id)
        actual_payment = min(hourly_payment, max(0, current_balance))
        if actual_payment > 0:
            debit_usd(owner_id, actual_payment)
            total_collected += actual_payment
            if actual_payment >= 100:
                _fire_govt_push(
                    owner_id,
                    "Land Hoard Tax Charged",
                    f"${actual_payment:,.0f} hoard tax collected — you hold {plot_count} plots (>{HOARDING_FREE_PLOTS} free)",
                )

            log_transaction(
                player_id=owner_id,
                transaction_type="tax",
                category="money",
                amount=-actual_payment,
                description=f"Land hoarding fee: {tax_info['excess_plots']} excess plot(s) — ${tax_info['monthly_total']:,.0f}/mo"
            )

    # Pay to government
    if total_collected > 0:
        from reserve_banks import credit_usd
        credit_usd(GOVERNMENT_PLAYER_ID, total_collected)
        try:
            from govt_ledger import log_gov_event as _lge
            _lge("land_hoarding_tax", "in", total_collected, "USD",
                 description=f"Land hoarding tax: {len(plot_counts)} player(s)")
        except Exception:
            pass

    db.commit()
    db.close()

    if total_collected > 0:
        print(f"[Land] Hoarding tax collected: ${total_collected:,.2f} from {len(plot_counts)} player(s)")


# ==========================
# MODULE LIFECYCLE
# ==========================
def _migrate_land_plot_columns():
    """Add any missing columns to land_plots."""
    from database import run_ddl_migration
    for ddl in [
        "ALTER TABLE land_plots ADD COLUMN IF NOT EXISTS is_tutorial_reward BOOLEAN DEFAULT FALSE",
        "ALTER TABLE land_plots ADD COLUMN IF NOT EXISTS is_restoring BOOLEAN DEFAULT FALSE",
        "ALTER TABLE land_plots ADD COLUMN IF NOT EXISTS max_efficiency REAL DEFAULT 100.0",
        "ALTER TABLE land_plots ADD COLUMN IF NOT EXISTS restoration_target REAL",
    ]:
        run_ddl_migration(engine, ddl)


def initialize():
    """
    Initialize land module.
    Creates database tables if they don't exist.
    """
    print("[Land] Creating database tables...")
    Base.metadata.create_all(bind=engine)
    _migrate_land_plot_columns()

    stats = get_land_stats()
    print(f"[Land] Current state: {stats['total_plots']} plots, {stats['average_efficiency']:.2f}% avg efficiency")
    print("[Land] Module initialized")


def tick(current_tick: int, now: datetime):
    """
    Land module tick handler.

    Handles:
    - Efficiency degradation (every tick)
    - Monthly tax collection (when month changes)
    - Hourly hoarding tax deduction (proportionate to monthly rate)
    """
    global last_tax_month, last_hoarding_collection

    # Degrade efficiency every tick
    degrade_efficiency(current_tick)

    # Check if month has changed for tax collection
    current_month = now.month
    if current_month != last_tax_month:
        print(f"[Land] Month changed: {last_tax_month} -> {current_month}")
        collect_monthly_taxes(current_month)
        last_tax_month = current_month

    # Collect hoarding taxes every hour using real time (not tick modulo)
    # Rate is calculated monthly but deducted proportionately each hour (1/720 per hour)
    if last_hoarding_collection is None or (now - last_hoarding_collection).total_seconds() >= 3600:
        collect_hoarding_taxes()
        last_hoarding_collection = now

    # Log stats every hour (3600 ticks)
    if current_tick % 3600 == 0:
        stats = get_land_stats()
        print(f"[Land] Stats: {stats}")


# ==========================
# PUBLIC API
# ==========================
# These functions are exposed for use by other modules

__all__ = [
    'create_land_plot',
    'create_starter_plot',
    'get_player_land',
    'get_vacant_land',
    'transfer_land',
    'occupy_land',
    'vacate_land',
    'get_land_stats',
    'calculate_player_hoarding_tax',
    'TERRAIN_TYPES',
    'PROXIMITY_FEATURES',
    'BUSINESS_COMPATIBILITY',
    'HOARDING_FREE_PLOTS',
    'HOARDING_BASE_TAX_MONTHLY',
    'LandPlot'
]
