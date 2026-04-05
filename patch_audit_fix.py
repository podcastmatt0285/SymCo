#!/usr/bin/env python3
"""
patch_audit_fix.py — Comprehensive audit fix pass
1. Fix 123 category errors in item_types.json
2. Add 35 missing retail items to district_items.json
3. Wire 21 dead-end flowers into flower_shop + recipes
4. Wire chrysanthemum_essential_oil, floral_dye, elderflower downstream
"""
import json

def load(p):
    with open(p) as f: return json.load(f)
def save(p, d):
    with open(p,'w') as f: json.dump(d, f, indent=2)
    print(f"Saved {p}")

# ── LOAD ──────────────────────────────────────────────────────────────────────
items  = load("item_types.json")
biz    = load("business_types.json")
dbiz   = load("district_businesses.json")
ditems = load("district_items.json")

# ── 1. CATEGORY FIXES in item_types.json ─────────────────────────────────────
CAT_FIXES = {
    # Animals
    **{k: "animals" for k in [
        "chimpanzee","clownfish","crocodile","dolphin","eagle","elephant",
        "flamingo","giraffe","gorilla","hippo","jellyfish","kangaroo","koala",
        "lion","manta_ray","orangutan","panda","polar_bear","puffer_fish",
        "python","rhino","sea_lion","sea_turtle","seal","shark","sturgeon",
        "tiger","tortoise","tropical_fish","zebra",
    ]},
    # Prison
    **{k: "prison" for k in [
        "commissary_snacks","counseling_materials","ged_materials","hygiene_kit",
        "prison_bedding","vocational_kit","dog_tags","mre","prison_produce_crate",
        "license_plate_batch",
    ]},
    # Prison infrastructure (kept separate from consumables)
    **{k: "prison_infrastructure" for k in [
        "cell_door","taser","razor_wire","handcuffs",
        "surveillance_system","institutional_furniture_set",
    ]},
    # Education
    **{k: "education" for k in [
        "curriculum_package","diploma_certificate","dissection_kit","lab_kit",
        "school_lunch","standardized_test","student_desk","sports_equipment",
        "projector","smartboard","scoreboard",
    ]},
    # Medical
    **{k: "medical_supplies" for k in [
        "iv_bag","gauze","sutures","cast_material",
    ]},
    **{k: "medical_equipment" for k in [
        "iv_pump","crutches","defibrillator","prosthetic","wheelchair","ventilator",
    ]},
    # Entertainment
    **{k: "entertainment" for k in [
        "concert_stage","jumbotron","lighting_rig","popcorn_machine","poker_table",
        "pyrotechnics","roulette_wheel","slot_machine","sound_system","team_jersey",
        "theater_seat","film_reel","barracks_bunk",
    ]},
    # Fast food / prepared
    **{k: "prepared_food" for k in [
        "hot_dog","fried_rice","fries","gyro","milkshake","pad_thai",
        "smoothie","soda_cup","soft_serve","ramen_bowl",
    ]},
    # Food service
    **{k: "food_service" for k in [
        "food_tray","takeout_container","disposable_utensils",
    ]},
    # Logistics
    **{k: "logistics" for k in [
        "freight_container","refrigerated_container","freight_manifest",
    ]},
    # Appliances
    **{k: "appliances" for k in [
        "hvac_unit","water_heater","washer_dryer","refrigerator","stove",
    ]},
    # Utilities
    **{k: "utilities" for k in [
        "drinking_water","natural_gas","residential_electricity","wastewater_service",
    ]},
    # Fuel
    "diesel": "fuel",
    # Military
    **{k: "military" for k in [
        "encryption_device","explosive_ordnance","firing_range","humvee",
        "night_vision","obstacle_course","radar_array","tactical_vest",
    ]},
    # Electronics
    **{k: "electronics" for k in [
        "laptop","lcd_panel","memory_module","security_camera","tablet","television",
    ]},
    # Misc single fixes
    "hospitality_linen_set": "hospitality",
    "passenger_train":       "vehicles",
    "viewing_platform":      "zoo_infrastructure",
}

fixed = 0
for key, new_cat in CAT_FIXES.items():
    if key in items and isinstance(items[key], dict):
        old = items[key].get("category")
        if old != new_cat:
            items[key]["category"] = new_cat
            fixed += 1
print(f"Category fixes applied: {fixed}")

save("item_types.json", items)

# ── 2. MISSING RETAIL ITEMS → district_items.json ────────────────────────────
NEW_DISTRICT_ITEMS = {
    # Hotel
    "concierge_package":    ("Concierge Package",        "Full-service hotel concierge assistance",                        "retail_service"),
    "suite_night":          ("Suite Night",               "Luxury hotel suite stay for one night",                          "retail_service"),
    "penthouse_night":      ("Penthouse Night",           "Penthouse floor accommodation with premium amenities",           "retail_service"),
    # Nightclub
    "bottle_service":       ("Bottle Service",            "VIP table with premium bottle service",                          "retail_entertainment"),
    "club_entry":           ("Club Entry",                "General admission to nightclub",                                  "retail_entertainment"),
    "vip_lounge_pass":      ("VIP Lounge Pass",           "Access to VIP lounge with priority service",                     "retail_entertainment"),
    # Casino
    "casino_dining":        ("Casino Dining",             "Fine dining experience at the casino restaurant",                "retail_food"),
    "premium_show_ticket":  ("Premium Show Ticket",       "Front-row seating at casino headline show",                      "retail_entertainment"),
    "vip_gaming_package":   ("VIP Gaming Package",        "Private table access with casino credits and amenities",         "retail_entertainment"),
    # Theme Park
    "annual_pass":          ("Annual Pass",               "Unlimited park entry pass for one year",                         "retail_entertainment"),
    "vip_experience":       ("VIP Experience",            "Behind-the-scenes tour and fast-pass access",                    "retail_entertainment"),
    "park_merchandise":     ("Park Merchandise",          "Branded merchandise from theme park gift shops",                 "retail_shopping"),
    # Convention Center
    "banquet_ticket":       ("Banquet Ticket",            "Admission to convention center banquet event",                   "retail_entertainment"),
    "event_booth_package":  ("Event Booth Package",       "Exhibition booth rental for convention events",                  "retail_service"),
    "keynote_sponsorship":  ("Keynote Sponsorship",       "Headline sponsorship slot at major convention",                  "retail_service"),
    # Wholesale Warehouse
    "bulk_household_pallet":("Bulk Household Pallet",     "Pallet of household essentials at wholesale pricing",            "retail_shopping"),
    "bulk_industrial_pallet":("Bulk Industrial Pallet",   "Pallet of industrial supplies at wholesale pricing",             "industrial"),
    "members_subscription": ("Members Subscription",     "Annual wholesale warehouse membership",                          "retail_service"),
    # Seaport
    "cargo_insurance":      ("Cargo Insurance",           "Insurance policy covering port cargo shipments",                 "services"),
    "dock_berth_lease":     ("Dock Berth Lease",          "Long-term lease of a seaport berth",                            "services"),
    "port_logistics_package":("Port Logistics Package",   "End-to-end port handling and customs clearance",                "services"),
    # Electronics Superstore
    "gaming_setup":         ("Gaming Setup",              "Complete gaming PC or console setup bundle",                     "retail_shopping"),
    "home_appliance_set":   ("Home Appliance Set",        "Bundled major home appliances",                                  "retail_shopping"),
    "smart_home_kit":       ("Smart Home Kit",            "Connected home automation starter kit",                          "retail_shopping"),
    # Tech Startup Hub
    "startup_accelerator_seat":("Startup Accelerator Seat","Funded seat in a tech startup accelerator programme",          "retail_service"),
    "tech_consulting_day":  ("Tech Consulting Day",       "Full day of senior technology consulting",                       "retail_service"),
    "venture_capital_advisory":("Venture Capital Advisory","VC advisory session and pitch feedback",                        "retail_service"),
    # Research Campus
    "lab_access_package":   ("Lab Access Package",        "Monthly access to shared research laboratory facilities",        "retail_service"),
    "research_grant_contract":("Research Grant Contract", "Externally funded research engagement contract",                  "retail_service"),
    "technology_license":   ("Technology License",        "Commercial licence for campus-developed technology",             "retail_service"),
    # Maximum Security Facility
    "correctional_training":("Correctional Training",     "Accredited officer training programme for corrections staff",    "retail_service"),
    "prisoner_transport_service":("Prisoner Transport Service","Secure prisoner transportation contract",                   "services"),
    # Duty Free
    "duty_free_confections":("Duty Free Confections",     "Airport duty-free sweets, chocolate and confections",            "retail_food"),
    "duty_free_luxury":     ("Duty Free Luxury",          "Duty-free luxury goods including watches and jewellery",         "retail_shopping"),
    "duty_free_tobacco":    ("Duty Free Tobacco",         "Airport duty-free tobacco products",                             "retail_shopping"),
}

added = 0
for key, (name, desc, cat) in NEW_DISTRICT_ITEMS.items():
    if key not in ditems:
        ditems[key] = {"name": name, "description": desc, "category": cat}
        added += 1
print(f"New district items added: {added}")
save("district_items.json", ditems)

# ── 3. WIRE DEAD-END FLOWERS INTO FLOWER_SHOP ─────────────────────────────────
# Every dead-end flower gets added to flower_shop products with a modest sale chance
DEAD_END_FLOWERS = [
    "agave_flower","anemone","apple_blossom","clover_flower","coffee_blossom",
    "echinacea","elderflower","foxglove","gardenia","geranium","lilac",
    "magnolia","passionflower","ranunculus","snapdragon","tea_flower",
    "tobacco_flower","vanilla_blossom","wisteria",
]

biz = load("business_types.json")
fs_products = biz["flower_shop"]["products"]
for flower in DEAD_END_FLOWERS:
    if flower not in fs_products:
        fs_products[flower] = {"base_sale_chance": 0.08, "elasticity": 1.2}

# ── 4. WIRE FLOWERS INTO RECIPES ─────────────────────────────────────────────

# 4a. botanical_extract_lab: add apple_blossom_water, coffee_blossom_water,
#     geranium_oil (feeds perfume), elderflower extract
# First add missing items to item_types
items = load("item_types.json")
new_extras = {
    "apple_blossom_water":  ("Apple Blossom Water",  "Delicate floral hydrosol from apple blossoms",            "ingredients"),
    "coffee_blossom_water": ("Coffee Blossom Water", "Jasmine-scented hydrosol from coffee flowers",            "ingredients"),
    "geranium_essential_oil":("Geranium Essential Oil","Rose-like aromatic oil from scented geranium",           "essential_oils"),
    "elderflower_cordial":  ("Elderflower Cordial",   "Light syrup made from elderflowers and sugar",            "beverages"),
    "echinacea_extract":    ("Echinacea Extract",     "Herbal immune-support tincture from echinacea flowers",   "health"),
    "foxglove_extract":     ("Foxglove Extract",      "Digitalis-based medicinal extract used in cardiac drugs", "health"),
    "passionflower_extract":("Passionflower Extract", "Calming herbal extract used in supplements",              "health"),
}
for key,(name,desc,cat) in new_extras.items():
    if key not in items:
        items[key] = {"name":name,"description":desc,"category":cat}
save("item_types.json", items)

# 4b. Add new production lines to botanical_extract_lab
biz = load("business_types.json")
bel = biz["botanical_extract_lab"]["production_lines"]
bel.extend([
    {
        "output_item": "apple_blossom_water", "output_qty": 40,
        "inputs": [
            {"item": "apple_blossom", "quantity": 200},
            {"item": "pollen",        "quantity": 22000},
            {"item": "water",         "quantity": 700},
            {"item": "energy",        "quantity": 180},
            {"item": "paper",         "quantity": 2},
        ]
    },
    {
        "output_item": "coffee_blossom_water", "output_qty": 40,
        "inputs": [
            {"item": "coffee_blossom", "quantity": 200},
            {"item": "pollen",         "quantity": 25000},
            {"item": "water",          "quantity": 700},
            {"item": "energy",         "quantity": 180},
            {"item": "paper",          "quantity": 2},
        ]
    },
    {
        "output_item": "geranium_essential_oil", "output_qty": 6,
        "inputs": [
            {"item": "geranium", "quantity": 400},
            {"item": "pollen",   "quantity": 42000},
            {"item": "water",    "quantity": 300},
            {"item": "energy",   "quantity": 480},
            {"item": "paper",    "quantity": 4},
        ]
    },
    {
        "output_item": "elderflower_cordial", "output_qty": 30,
        "inputs": [
            {"item": "elderflower", "quantity": 300},
            {"item": "sugar",       "quantity": 500},
            {"item": "pollen",      "quantity": 28000},
            {"item": "water",       "quantity": 600},
            {"item": "energy",      "quantity": 200},
            {"item": "paper",       "quantity": 2},
        ]
    },
])

# 4c. Add herbal extracts to pharmaceutical_lab
pharma = biz.get("pharmaceutical_lab", {})
if pharma:
    pharma_lines = pharma.get("production_lines", [])
    pharma_lines.extend([
        {
            "output_item": "echinacea_extract", "output_qty": 20,
            "inputs": [
                {"item": "echinacea", "quantity": 300},
                {"item": "pollen",    "quantity": 35000},
                {"item": "water",     "quantity": 400},
                {"item": "energy",    "quantity": 300},
                {"item": "paper",     "quantity": 3},
            ]
        },
        {
            "output_item": "foxglove_extract", "output_qty": 10,
            "inputs": [
                {"item": "foxglove", "quantity": 200},
                {"item": "pollen",   "quantity": 45000},
                {"item": "water",    "quantity": 300},
                {"item": "energy",   "quantity": 400},
                {"item": "paper",    "quantity": 3},
            ]
        },
        {
            "output_item": "passionflower_extract", "output_qty": 20,
            "inputs": [
                {"item": "passionflower", "quantity": 250},
                {"item": "pollen",        "quantity": 38000},
                {"item": "water",         "quantity": 400},
                {"item": "energy",        "quantity": 300},
                {"item": "paper",         "quantity": 3},
            ]
        },
    ])

# 4d. Add chrysanthemum_essential_oil to personal_care_factory
pcf_lines = biz.get("personal_care_factory", {}).get("production_lines", [])
pcf_lines.append({
    "output_item": "shampoo", "output_qty": 20,
    "inputs": [
        {"item": "chrysanthemum_essential_oil", "quantity": 5},
        {"item": "pollen",                      "quantity": 30000},
        {"item": "water",                       "quantity": 25},
        {"item": "bottle",                      "quantity": 35},
        {"item": "energy",                      "quantity": 12},
        {"item": "paper",                       "quantity": 2},
    ]
})

# 4e. Add floral_dye to paint_factory as an input option
paint = biz.get("paint_factory", {})
if paint:
    paint["production_lines"].append({
        "output_item": "dye", "output_qty": 40,
        "inputs": [
            {"item": "floral_dye", "quantity": 30},
            {"item": "pollen",     "quantity": 20000},
            {"item": "water",      "quantity": 200},
            {"item": "energy",     "quantity": 150},
            {"item": "paper",      "quantity": 2},
        ]
    })

# 4f. Add botanical flowers to gin_distillery (elderflower gin)
gin = biz.get("gin_distillery", {})
if gin:
    gin_lines = gin.get("production_lines", [])
    # Check if elderflower gin already exists
    existing = [l["output_item"] for l in gin_lines]
    if "elderflower_gin" not in existing:
        # Add elderflower_gin item
        items = load("item_types.json")
        if "elderflower_gin" not in items:
            items["elderflower_gin"] = {
                "name": "Elderflower Gin",
                "description": "Premium small-batch gin infused with elderflower and botanicals",
                "category": "alcohol"
            }
            save("item_types.json", items)
        gin_lines.append({
            "output_item": "elderflower_gin", "output_qty": 10,
            "inputs": [
                {"item": "elderflower", "quantity": 200},
                {"item": "juniper_berries", "quantity": 100},
                {"item": "pollen",      "quantity": 32000},
                {"item": "water",       "quantity": 500},
                {"item": "energy",      "quantity": 400},
                {"item": "glass",       "quantity": 10},
                {"item": "paper",       "quantity": 5},
            ]
        })

# 4g. Add ranunculus, snapdragon, gardenia, magnolia, lilac, wisteria
#     to floral_studio bouquet variants
studio_lines = biz.get("floral_studio", {}).get("production_lines", [])
studio_lines.extend([
    {
        "output_item": "bouquet", "output_qty": 10,
        "inputs": [
            {"item": "ranunculus",  "quantity": 15},
            {"item": "snapdragon",  "quantity": 20},
            {"item": "anemone",     "quantity": 15},
            {"item": "lilac",       "quantity": 10},
            {"item": "pollen",      "quantity": 52000},
            {"item": "paper",       "quantity": 5},
            {"item": "energy",      "quantity": 50},
        ]
    },
    {
        "output_item": "floral_centerpiece", "output_qty": 8,
        "inputs": [
            {"item": "magnolia",    "quantity": 10},
            {"item": "gardenia",    "quantity": 15},
            {"item": "wisteria",    "quantity": 12},
            {"item": "orchid",      "quantity": 5},
            {"item": "pollen",      "quantity": 75000},
            {"item": "glass",       "quantity": 8},
            {"item": "energy",      "quantity": 65},
            {"item": "paper",       "quantity": 3},
        ]
    },
    {
        "output_item": "potpourri", "output_qty": 15,
        "inputs": [
            {"item": "wisteria",    "quantity": 20},
            {"item": "lilac",       "quantity": 20},
            {"item": "geranium",    "quantity": 20},
            {"item": "rose",        "quantity": 15},
            {"item": "pollen",      "quantity": 48000},
            {"item": "jar",         "quantity": 15},
            {"item": "energy",      "quantity": 30},
            {"item": "paper",       "quantity": 2},
        ]
    },
])

# 4h. Wire agave_flower, tobacco_flower, tea_flower, vanilla_blossom,
#     clover_flower, coffee_blossom into botanical_garden or perfume_atelier
dbiz = load("district_businesses.json")
pa_lines = dbiz.get("perfume_atelier", {}).get("production_lines", [])
pa_lines.append({
    "output_item": "artisan_fragrance", "output_qty": 20,
    "inputs": [
        {"item": "vanilla_blossom",   "quantity": 30},
        {"item": "tobacco_flower",    "quantity": 20},
        {"item": "clover_flower",     "quantity": 40},
        {"item": "pollen",            "quantity": 85000},
        {"item": "bottle",            "quantity": 20},
        {"item": "energy",            "quantity": 520},
        {"item": "paper",             "quantity": 10},
    ]
})
pa_lines.append({
    "output_item": "cologne", "output_qty": 25,
    "inputs": [
        {"item": "tea_flower",        "quantity": 40},
        {"item": "coffee_blossom",    "quantity": 30},
        {"item": "geranium_essential_oil", "quantity": 4},
        {"item": "pollen",            "quantity": 72000},
        {"item": "bottle",            "quantity": 25},
        {"item": "energy",            "quantity": 460},
        {"item": "paper",             "quantity": 10},
    ]
})

# Botanical garden: agave_flower specimen + tea_flower path
bg_lines = dbiz.get("botanical_garden", {}).get("production_lines", [])
bg_lines.append({
    "output_item": "garden_pass", "output_qty": 30,
    "inputs": [
        {"item": "agave_flower",    "quantity": 20},
        {"item": "tea_flower",      "quantity": 30},
        {"item": "vanilla_blossom", "quantity": 15},
        {"item": "pollen",          "quantity": 110000},
        {"item": "water",           "quantity": 1500},
        {"item": "energy",          "quantity": 800},
        {"item": "paper",           "quantity": 30},
    ]
})

save("business_types.json", biz)
save("district_businesses.json", dbiz)

print("\nAudit fix patch complete.")
