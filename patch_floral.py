#!/usr/bin/env python3
"""
patch_floral.py — Comprehensive floral expansion patch
Adds 43 flower varieties, floral products, extracts, and businesses.
ALL flower production requires MASSIVE pollen quantities.
"""
import json, copy

def load(path):
    with open(path) as f:
        return json.load(f)

def save(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Saved {path}")

# ─── LOAD ────────────────────────────────────────────────────────────────────
items   = load("item_types.json")
biz     = load("business_types.json")
dbiz    = load("district_businesses.json")
ditems  = load("district_items.json")

# ─── 1. ITEM TYPES — flowers ─────────────────────────────────────────────────
FLOWERS = {
    # Dedicated flower varieties — flower_farm
    "rose":            ("Rose",            "Prized cut flower; base of rose oil and rose water"),
    "lily":            ("Lily",            "Elegant long-stemmed flower for arrangements and funerals"),
    "tulip":           ("Tulip",           "Spring bulb flower; one of the most traded cut flowers"),
    "orchid":          ("Orchid",          "Exotic tropical flower; premium bloom with intense fragrance"),
    "lavender":        ("Lavender",        "Aromatic herb-flower; base of lavender essential oil"),
    "sunflower":       ("Sunflower",       "Large bright flower; seeds yield sunflower oil"),
    "chrysanthemum":   ("Chrysanthemum",   "High-volume cut flower; used in teas and arrangements"),
    "carnation":       ("Carnation",       "Mass-market cut flower with long vase life"),
    "peony":           ("Peony",           "Premium luxury bloom; prized in wedding bouquets"),
    "hydrangea":       ("Hydrangea",       "Full decorative bloom for event and home arrangements"),
    "iris":            ("Iris",            "Distinctive blade-petalled cut flower"),
    "dahlia":          ("Dahlia",          "Vibrant decorative bloom with many colour forms"),
    "jasmine":         ("Jasmine",         "Intensely fragrant flower; cornerstone of high perfumery"),
    "marigold":        ("Marigold",        "Pungent flower; primary source of natural floral dye"),
    "lotus":           ("Lotus",           "Sacred aquatic flower; used in cosmetics and luxury decor"),
    "gardenia":        ("Gardenia",        "Creamy white flower with heavy jasmine-like scent"),
    "freesia":         ("Freesia",         "Delicate funnel-shaped flower with sweet fragrance"),
    "narcissus":       ("Narcissus",       "Spring bulb flower including daffodils"),
    "snapdragon":      ("Snapdragon",      "Tall spike flower popular in mixed bouquets"),
    "zinnia":          ("Zinnia",          "Vivid summer flower; excellent for dried arrangements"),
    "violet":          ("Violet",          "Small purple flower; used in perfumery and confectionery"),
    "magnolia":        ("Magnolia",        "Large-cupped tree flower with a lemony fragrance"),
    "hibiscus":        ("Hibiscus",        "Tropical flower used in teas, dyes, and cosmetics"),
    "anemone":         ("Anemone",         "Windflower with striking dark centres"),
    "ranunculus":      ("Ranunculus",      "Multi-layered luxury bloom resembling a tight rose"),
    "wisteria":        ("Wisteria",        "Cascading purple fragrant flower"),
    "lilac":           ("Lilac",           "Intensely fragrant spring cluster flower"),
    "geranium":        ("Geranium",        "Aromatic flower used in perfumery and insect repellent"),
    "foxglove":        ("Foxglove",        "Tall bell flower; source of medicinal digitalis"),
    "heather":         ("Heather",         "Hardy moorland flower; used in dried arrangements"),
    "clover_flower":   ("Clover Flower",   "Pollinator favourite; used in teas and honey flavouring"),
    "elderflower":     ("Elderflower",     "Delicate white flower; used in cordials and liqueurs"),
    "chamomile":       ("Chamomile",       "Daisy-like herb flower; used in teas and skin care"),
    "echinacea":       ("Echinacea",       "Purple coneflower; medicinal herb and ornamental bloom"),
    "passionflower":   ("Passionflower",   "Exotic climbing flower; used in relaxation supplements"),
    # Blossoms from existing game plants
    "apple_blossom":   ("Apple Blossom",   "Spring flower of apple trees; aromatic and highly attractive to pollinators"),
    "orange_blossom":  ("Orange Blossom",  "Delicate citrus flower; base of neroli oil and orange blossom water"),
    "cherry_blossom":  ("Cherry Blossom",  "Iconic spring flower of cherry trees; prized decorative bloom"),
    "coffee_blossom":  ("Coffee Blossom",  "Jasmine-scented white flower of the coffee plant"),
    "tobacco_flower":  ("Tobacco Flower",  "Tubular white flower of the tobacco plant; fragrant at night"),
    "tea_flower":      ("Tea Flower",      "Small white camellia-like flower of the tea plant"),
    "vanilla_blossom": ("Vanilla Blossom", "Delicate orchid-like flower; must be hand-pollinated for pods"),
    "agave_flower":    ("Agave Flower",    "Towering bloom spike of the agave; plant dies after flowering"),
}

FLORAL_PRODUCTS = {
    "bouquet":             ("Flower Bouquet",       "Mixed fresh-cut arrangement of seasonal flowers",          "floral_products"),
    "wedding_bouquet":     ("Wedding Bouquet",       "Premium bridal arrangement of peonies, roses and orchids", "floral_products"),
    "funeral_wreath":      ("Funeral Wreath",        "Memorial wreath of lilies, chrysanthemums and roses",      "floral_products"),
    "corsage":             ("Corsage",               "Small wearable orchid-and-rose flower piece",              "floral_products"),
    "floral_centerpiece":  ("Floral Centerpiece",    "Statement table centrepiece for events and hospitality",   "floral_products"),
    "dried_flower_bundle": ("Dried Flower Bundle",   "Preserved bundle of lavender, rose and zinnia",           "floral_products"),
    "potpourri":           ("Potpourri",              "Aromatic jar of dried petals and essential oils",         "floral_products"),
    "flower_crown":        ("Flower Crown",           "Wearable floral crown of roses and carnations",           "floral_products"),
    "pressed_flower_art":  ("Pressed Flower Art",    "Framed art piece of pressed iris and peony blooms",       "floral_products"),
}

FLORAL_OILS = {
    "rose_essential_oil":          ("Rose Essential Oil",          "Intensely concentrated attar of roses; the most prized perfume base"),
    "lavender_essential_oil":      ("Lavender Essential Oil",      "Classic calming oil distilled from lavender spikes"),
    "jasmine_essential_oil":       ("Jasmine Essential Oil",       "Heady floral absolute from jasmine; cornerstone of oriental perfumes"),
    "neroli_oil":                  ("Neroli Oil",                  "Steam-distilled oil of orange blossom; fresh and floral"),
    "chrysanthemum_essential_oil": ("Chrysanthemum Essential Oil", "Clean herbal oil distilled from chrysanthemum blooms"),
}

FLORAL_INGREDIENTS = {
    "rose_water":           ("Rose Water",           "Rose distillate used in cooking, cosmetics and perfumery",    "ingredients"),
    "orange_blossom_water": ("Orange Blossom Water", "Floral hydrosol used in pastry, cocktails and skin care",     "ingredients"),
    "floral_dye":           ("Floral Dye",           "Natural textile dye extracted from marigold and hibiscus",    "ingredients"),
}

FLORAL_LUXURY = {
    "signature_perfume":   ("Signature Perfume",   "Hand-crafted luxury fragrance from rose and jasmine absolutes", "luxury"),
    "artisan_fragrance":   ("Artisan Fragrance",   "Small-batch aromatic blend of lavender and rose water",         "luxury"),
    "cologne":             ("Cologne",             "Fresh eau de cologne of neroli, jasmine and lavender",           "luxury"),
    "rare_orchid_specimen":("Rare Orchid Specimen","Museum-quality potted exotic orchid from botanical gardens",     "luxury"),
}

# Add to items
for key, (name, desc) in FLOWERS.items():
    if key not in items:
        items[key] = {"name": name, "description": desc, "category": "flowers"}

for key, (name, desc, cat) in FLORAL_PRODUCTS.items():
    if key not in items:
        items[key] = {"name": name, "description": desc, "category": cat}

for key, (name, desc) in FLORAL_OILS.items():
    if key not in items:
        items[key] = {"name": name, "description": desc, "category": "essential_oils"}

for key, (name, desc, cat) in FLORAL_INGREDIENTS.items():
    if key not in items:
        items[key] = {"name": name, "description": desc, "category": cat}

for key, (name, desc, cat) in FLORAL_LUXURY.items():
    if key not in items:
        items[key] = {"name": name, "description": desc, "category": cat}

save("item_types.json", items)
print(f"item_types: {len(items)} items total")

# ─── 2. BUSINESS TYPES ───────────────────────────────────────────────────────
items   = load("item_types.json")   # reload after part-1 save
biz     = load("business_types.json")

# ── 2a. flower_farm ──────────────────────────────────────────────────────────
# Every line consumes MASSIVE pollen.  Standard base: water+energy+paper+pollen.
def _flower_line(flower, pollen, water=300, energy=150, paper=2, extra=None):
    inputs = [
        {"item": "water",  "quantity": water},
        {"item": "energy", "quantity": energy},
        {"item": "paper",  "quantity": paper},
        {"item": "pollen", "quantity": pollen},
    ]
    if extra:
        inputs.extend(extra)
    return {"output_item": flower, "output_qty": 100, "inputs": inputs}

FLOWER_FARM_LINES = [
    # Common blooms — pollen 20,000-28,000
    _flower_line("rose",           25000, water=400, energy=200),
    _flower_line("lily",           22000, water=350, energy=160),
    _flower_line("tulip",          20000, water=300, energy=150),
    _flower_line("carnation",      20000, water=280, energy=140),
    _flower_line("sunflower",      22000, water=350, energy=180),
    _flower_line("chrysanthemum",  21000, water=300, energy=150),
    _flower_line("snapdragon",     20000, water=280, energy=140),
    _flower_line("zinnia",         19000, water=260, energy=130),
    _flower_line("marigold",       21000, water=300, energy=150),
    _flower_line("violet",         20000, water=280, energy=140),
    _flower_line("narcissus",      21000, water=320, energy=160),
    _flower_line("freesia",        22000, water=330, energy=160),
    _flower_line("heather",        18000, water=240, energy=120),
    _flower_line("clover_flower",  18000, water=240, energy=110),
    _flower_line("chamomile",      20000, water=280, energy=140),
    _flower_line("echinacea",      21000, water=290, energy=145),
    # Mid-tier blooms — pollen 28,000-38,000
    _flower_line("lavender",       30000, water=350, energy=200),
    _flower_line("hydrangea",      30000, water=400, energy=200),
    _flower_line("iris",           28000, water=360, energy=180),
    _flower_line("dahlia",         30000, water=380, energy=190),
    _flower_line("anemone",        28000, water=340, energy=170),
    _flower_line("ranunculus",     32000, water=400, energy=200),
    _flower_line("foxglove",       28000, water=340, energy=170),
    _flower_line("hibiscus",       32000, water=420, energy=210),
    _flower_line("elderflower",    30000, water=360, energy=180),
    _flower_line("passionflower",  34000, water=440, energy=220),
    _flower_line("geranium",       29000, water=350, energy=175),
    # Premium blooms — pollen 38,000-55,000
    _flower_line("peony",          45000, water=500, energy=250),
    _flower_line("jasmine",        48000, water=520, energy=260),
    _flower_line("gardenia",       46000, water=500, energy=250),
    _flower_line("magnolia",       42000, water=480, energy=240),
    _flower_line("wisteria",       40000, water=460, energy=230),
    _flower_line("lilac",          40000, water=460, energy=230),
    _flower_line("flower_crown",   0),   # placeholder removed below
    # Ultra-premium / exotic — pollen 50,000-65,000
    _flower_line("orchid",         60000, water=600, energy=300,
                 extra=[{"item": "fertilizer_npk", "quantity": 20}]),
    _flower_line("lotus",          55000, water=800, energy=300),
]
# Remove placeholder
FLOWER_FARM_LINES = [l for l in FLOWER_FARM_LINES if l["output_item"] != "flower_crown"]

biz["flower_farm"] = {
    "name": "Flower Farm",
    "description": "Commercial flower farm growing 35 varieties of cut flowers and blooms. Every line requires massive quantities of pollen for pollination.",
    "class": "production",
    "startup_cost": 18000,
    "base_wage_cost": 65,
    "cycles_to_complete": 480,
    "allowed_terrain": ["prairie", "hills", "marsh", "savanna", "jungle", "island"],
    "allowed_proximity": ["rural", "riverside", "remote"],
    "production_lines": FLOWER_FARM_LINES,
}

# ── 2b. Add blossom lines to existing farms ──────────────────────────────────
def _blossom_line(flower, pollen, water=250, energy=120, paper=1):
    return {
        "output_item": flower,
        "output_qty": 80,
        "inputs": [
            {"item": "water",  "quantity": water},
            {"item": "energy", "quantity": energy},
            {"item": "paper",  "quantity": paper},
            {"item": "pollen", "quantity": pollen},
        ]
    }

# plantation → apple_blossom, orange_blossom
if "plantation" in biz:
    biz["plantation"]["production_lines"].append(_blossom_line("apple_blossom",  18000, 300, 140))
    biz["plantation"]["production_lines"].append(_blossom_line("orange_blossom", 20000, 320, 150))

# orchard → cherry_blossom
if "orchard" in biz:
    biz["orchard"]["production_lines"].append(_blossom_line("cherry_blossom", 22000, 350, 160))

# hop_farm → lavender (fits the herb/botanical theme), elderflower
if "hop_farm" in biz:
    biz["hop_farm"]["production_lines"].append(_blossom_line("lavender",    28000, 350, 180))
    biz["hop_farm"]["production_lines"].append(_blossom_line("elderflower", 24000, 300, 150))
    biz["hop_farm"]["production_lines"].append(_blossom_line("chamomile",   20000, 280, 140))

# coffee_plantation → coffee_blossom
if "coffee_plantation" in biz:
    biz["coffee_plantation"]["production_lines"].append(_blossom_line("coffee_blossom", 28000, 400, 200))

# tea_plantation → tea_flower
if "tea_plantation" in biz:
    biz["tea_plantation"]["production_lines"].append(_blossom_line("tea_flower", 26000, 350, 175))

# spice_plantation → vanilla_blossom
if "spice_plantation" in biz:
    biz["spice_plantation"]["production_lines"].append(_blossom_line("vanilla_blossom", 35000, 400, 200))

# agave_plantation → agave_flower
if "agave_plantation" in biz:
    biz["agave_plantation"]["production_lines"].append(_blossom_line("agave_flower", 30000, 300, 150))

# tobacco farms → tobacco_flower
for farm in ["virginia_tobacco_farm", "burley_tobacco_farm", "oriental_tobacco_farm"]:
    if farm in biz:
        biz[farm]["production_lines"].append(_blossom_line("tobacco_flower", 20000, 200, 100))

# ── 2c. floral_studio ────────────────────────────────────────────────────────
biz["floral_studio"] = {
    "name": "Floral Studio",
    "description": "Artisan studio crafting bouquets, wreaths, corsages and centrepieces. Pollen is required at every stage of the design and preservation process.",
    "class": "production",
    "startup_cost": 15000,
    "base_wage_cost": 120,
    "cycles_to_complete": 240,
    "allowed_terrain": ["urban", "prairie", "hills"],
    "allowed_proximity": ["urban", "road"],
    "production_lines": [
        {
            "output_item": "bouquet", "output_qty": 10,
            "inputs": [
                {"item": "rose",       "quantity": 20},
                {"item": "lily",       "quantity": 15},
                {"item": "carnation",  "quantity": 25},
                {"item": "tulip",      "quantity": 15},
                {"item": "pollen",     "quantity": 50000},
                {"item": "paper",      "quantity": 5},
                {"item": "energy",     "quantity": 50},
            ]
        },
        {
            "output_item": "wedding_bouquet", "output_qty": 5,
            "inputs": [
                {"item": "peony",      "quantity": 20},
                {"item": "rose",       "quantity": 30},
                {"item": "lily",       "quantity": 15},
                {"item": "orchid",     "quantity": 8},
                {"item": "carnation",  "quantity": 15},
                {"item": "freesia",    "quantity": 12},
                {"item": "pollen",     "quantity": 90000},
                {"item": "paper",      "quantity": 5},
                {"item": "energy",     "quantity": 80},
            ]
        },
        {
            "output_item": "funeral_wreath", "output_qty": 5,
            "inputs": [
                {"item": "lily",           "quantity": 30},
                {"item": "chrysanthemum",  "quantity": 30},
                {"item": "rose",           "quantity": 20},
                {"item": "iris",           "quantity": 15},
                {"item": "pollen",         "quantity": 60000},
                {"item": "paper",          "quantity": 5},
                {"item": "energy",         "quantity": 60},
            ]
        },
        {
            "output_item": "corsage", "output_qty": 20,
            "inputs": [
                {"item": "orchid",    "quantity": 10},
                {"item": "rose",      "quantity": 10},
                {"item": "freesia",   "quantity": 8},
                {"item": "pollen",    "quantity": 40000},
                {"item": "paper",     "quantity": 2},
                {"item": "energy",    "quantity": 30},
            ]
        },
        {
            "output_item": "floral_centerpiece", "output_qty": 8,
            "inputs": [
                {"item": "hydrangea", "quantity": 20},
                {"item": "rose",      "quantity": 20},
                {"item": "dahlia",    "quantity": 15},
                {"item": "peony",     "quantity": 10},
                {"item": "pollen",    "quantity": 70000},
                {"item": "glass",     "quantity": 8},
                {"item": "energy",    "quantity": 60},
                {"item": "paper",     "quantity": 3},
            ]
        },
        {
            "output_item": "dried_flower_bundle", "output_qty": 20,
            "inputs": [
                {"item": "lavender",  "quantity": 40},
                {"item": "rose",      "quantity": 30},
                {"item": "zinnia",    "quantity": 30},
                {"item": "heather",   "quantity": 25},
                {"item": "pollen",    "quantity": 45000},
                {"item": "paper",     "quantity": 3},
                {"item": "energy",    "quantity": 40},
            ]
        },
        {
            "output_item": "potpourri", "output_qty": 15,
            "inputs": [
                {"item": "dried_flower_bundle", "quantity": 10},
                {"item": "lavender_essential_oil", "quantity": 2},
                {"item": "pollen",    "quantity": 50000},
                {"item": "jar",       "quantity": 15},
                {"item": "energy",    "quantity": 30},
                {"item": "paper",     "quantity": 2},
            ]
        },
        {
            "output_item": "flower_crown", "output_qty": 10,
            "inputs": [
                {"item": "rose",      "quantity": 20},
                {"item": "carnation", "quantity": 20},
                {"item": "lily",      "quantity": 15},
                {"item": "violet",    "quantity": 15},
                {"item": "pollen",    "quantity": 55000},
                {"item": "paper",     "quantity": 2},
                {"item": "energy",    "quantity": 40},
            ]
        },
        {
            "output_item": "pressed_flower_art", "output_qty": 5,
            "inputs": [
                {"item": "iris",      "quantity": 15},
                {"item": "peony",     "quantity": 10},
                {"item": "violet",    "quantity": 15},
                {"item": "narcissus", "quantity": 10},
                {"item": "pollen",    "quantity": 65000},
                {"item": "glass",     "quantity": 5},
                {"item": "paper",     "quantity": 10},
                {"item": "energy",    "quantity": 50},
            ]
        },
    ]
}

# ── 2d. botanical_extract_lab ─────────────────────────────────────────────────
biz["botanical_extract_lab"] = {
    "name": "Botanical Extract Lab",
    "description": "Distills and concentrates floral essential oils, hydrosols, and natural dyes. Enormous quantities of pollen are co-processed with each flower batch.",
    "class": "production",
    "startup_cost": 38000,
    "base_wage_cost": 200,
    "cycles_to_complete": 720,
    "allowed_terrain": ["urban", "prairie", "hills"],
    "allowed_proximity": ["urban", "road"],
    "production_lines": [
        {
            "output_item": "rose_essential_oil", "output_qty": 5,
            "inputs": [
                {"item": "rose",   "quantity": 600},
                {"item": "pollen", "quantity": 80000},
                {"item": "water",  "quantity": 400},
                {"item": "energy", "quantity": 600},
                {"item": "paper",  "quantity": 5},
            ]
        },
        {
            "output_item": "lavender_essential_oil", "output_qty": 8,
            "inputs": [
                {"item": "lavender", "quantity": 500},
                {"item": "pollen",   "quantity": 65000},
                {"item": "water",    "quantity": 350},
                {"item": "energy",   "quantity": 500},
                {"item": "paper",    "quantity": 5},
            ]
        },
        {
            "output_item": "jasmine_essential_oil", "output_qty": 4,
            "inputs": [
                {"item": "jasmine", "quantity": 400},
                {"item": "pollen",  "quantity": 90000},
                {"item": "water",   "quantity": 300},
                {"item": "energy",  "quantity": 700},
                {"item": "paper",   "quantity": 5},
            ]
        },
        {
            "output_item": "neroli_oil", "output_qty": 5,
            "inputs": [
                {"item": "orange_blossom", "quantity": 500},
                {"item": "pollen",         "quantity": 70000},
                {"item": "water",          "quantity": 350},
                {"item": "energy",         "quantity": 550},
                {"item": "paper",          "quantity": 5},
            ]
        },
        {
            "output_item": "chrysanthemum_essential_oil", "output_qty": 6,
            "inputs": [
                {"item": "chrysanthemum", "quantity": 700},
                {"item": "pollen",        "quantity": 55000},
                {"item": "water",         "quantity": 300},
                {"item": "energy",        "quantity": 450},
                {"item": "paper",         "quantity": 5},
            ]
        },
        {
            "output_item": "rose_water", "output_qty": 50,
            "inputs": [
                {"item": "rose",   "quantity": 200},
                {"item": "pollen", "quantity": 30000},
                {"item": "water",  "quantity": 800},
                {"item": "energy", "quantity": 200},
                {"item": "paper",  "quantity": 2},
            ]
        },
        {
            "output_item": "orange_blossom_water", "output_qty": 50,
            "inputs": [
                {"item": "orange_blossom", "quantity": 200},
                {"item": "pollen",         "quantity": 30000},
                {"item": "water",          "quantity": 800},
                {"item": "energy",         "quantity": 200},
                {"item": "paper",          "quantity": 2},
            ]
        },
        {
            "output_item": "floral_dye", "output_qty": 30,
            "inputs": [
                {"item": "marigold", "quantity": 400},
                {"item": "hibiscus", "quantity": 200},
                {"item": "pollen",   "quantity": 35000},
                {"item": "water",    "quantity": 400},
                {"item": "energy",   "quantity": 300},
                {"item": "paper",    "quantity": 2},
            ]
        },
    ]
}

# ── 2e. flower_shop (retail) ──────────────────────────────────────────────────
biz["flower_shop"] = {
    "name": "Flower Shop",
    "description": "Retail florist selling fresh-cut flowers and finished arrangements.",
    "class": "retail",
    "startup_cost": 5000,
    "base_wage_cost": 80,
    "cycles_to_complete": 10,
    "allowed_terrain": ["urban", "prairie", "hills"],
    "allowed_proximity": ["urban", "road"],
    "products": {
        "rose":               {"base_sale_chance": 0.30, "elasticity": 1.4},
        "lily":               {"base_sale_chance": 0.25, "elasticity": 1.3},
        "tulip":              {"base_sale_chance": 0.25, "elasticity": 1.3},
        "carnation":          {"base_sale_chance": 0.28, "elasticity": 1.3},
        "orchid":             {"base_sale_chance": 0.15, "elasticity": 1.8},
        "sunflower":          {"base_sale_chance": 0.22, "elasticity": 1.2},
        "lavender":           {"base_sale_chance": 0.20, "elasticity": 1.2},
        "chrysanthemum":      {"base_sale_chance": 0.22, "elasticity": 1.3},
        "peony":              {"base_sale_chance": 0.12, "elasticity": 2.0},
        "bouquet":            {"base_sale_chance": 0.20, "elasticity": 1.5},
        "wedding_bouquet":    {"base_sale_chance": 0.06, "elasticity": 2.2},
        "funeral_wreath":     {"base_sale_chance": 0.08, "elasticity": 1.6},
        "corsage":            {"base_sale_chance": 0.10, "elasticity": 1.5},
        "floral_centerpiece": {"base_sale_chance": 0.08, "elasticity": 1.8},
        "dried_flower_bundle":{"base_sale_chance": 0.15, "elasticity": 1.3},
        "potpourri":          {"base_sale_chance": 0.15, "elasticity": 1.2},
        "flower_crown":       {"base_sale_chance": 0.10, "elasticity": 1.5},
        "pressed_flower_art": {"base_sale_chance": 0.05, "elasticity": 2.0},
        "rose_water":         {"base_sale_chance": 0.18, "elasticity": 1.3},
    }
}

# ── 2f. Update personal_care_factory with new floral oil variants ─────────────
if "personal_care_factory" in biz:
    pcf_lines = biz["personal_care_factory"]["production_lines"]
    pcf_lines.extend([
        {
            "output_item": "perfume", "output_qty": 10,
            "inputs": [
                {"item": "rose_essential_oil",    "quantity": 5},
                {"item": "jasmine_essential_oil", "quantity": 3},
                {"item": "pollen",                "quantity": 40000},
                {"item": "water",                 "quantity": 10},
                {"item": "bottle",                "quantity": 12},
                {"item": "energy",                "quantity": 12},
                {"item": "paper",                 "quantity": 3},
            ]
        },
        {
            "output_item": "lotion", "output_qty": 20,
            "inputs": [
                {"item": "rose_water",             "quantity": 15},
                {"item": "lavender_essential_oil", "quantity": 5},
                {"item": "pollen",                 "quantity": 35000},
                {"item": "water",                  "quantity": 20},
                {"item": "bottle",                 "quantity": 30},
                {"item": "energy",                 "quantity": 10},
                {"item": "paper",                  "quantity": 2},
            ]
        },
        {
            "output_item": "soap", "output_qty": 30,
            "inputs": [
                {"item": "rose_essential_oil",     "quantity": 3},
                {"item": "lavender_essential_oil", "quantity": 3},
                {"item": "pollen",                 "quantity": 30000},
                {"item": "water",                  "quantity": 15},
                {"item": "energy",                 "quantity": 10},
                {"item": "paper",                  "quantity": 2},
            ]
        },
    ])

save("business_types.json", biz)
print(f"business_types: saved with flower_farm, floral_studio, botanical_extract_lab, flower_shop")

# ─── 3. DISTRICT BUSINESSES ──────────────────────────────────────────────────
dbiz    = load("district_businesses.json")
ALL_DISTRICT_TERRAINS = [
    "district_aerospace", "district_airport", "district_coastal",
    "district_convention_center", "district_education", "district_entertainment",
    "district_entertainment_district", "district_food", "district_food_court",
    "district_hospital", "district_industrial", "district_mall",
    "district_medical", "district_mega_mall", "district_military",
    "district_military_base", "district_neighborhood", "district_prison",
    "district_prison_complex", "district_research_campus", "district_seaport",
    "district_shipyard", "district_tech", "district_tech_park",
    "district_transport", "district_utilities", "district_zoo",
]

# ── 3a. street_flower_cart ────────────────────────────────────────────────────
# Zero startup, zero wages, retail pass-through. Sells single stems
# extremely slowly. The game's lifeline — costs nothing to run.
dbiz["street_flower_cart"] = {
    "name": "Street Flower Cart",
    "description": (
        "A humble wooden cart selling single-stem flowers one at a time. "
        "Earns almost nothing per cycle, but costs absolutely nothing to operate — "
        "no startup capital, no wages, no overhead. Can slowly pull a struggling "
        "company out of the red while better businesses are being rebuilt."
    ),
    "class": "retail",
    "startup_cost": 0,
    "base_wage_cost": 0,
    "cycles_to_complete": 60,
    "allowed_terrain": ALL_DISTRICT_TERRAINS,
    "products": {
        "rose":        {"base_sale_chance": 0.04, "elasticity": 1.1},
        "lily":        {"base_sale_chance": 0.04, "elasticity": 1.1},
        "carnation":   {"base_sale_chance": 0.04, "elasticity": 1.1},
        "tulip":       {"base_sale_chance": 0.03, "elasticity": 1.1},
        "sunflower":   {"base_sale_chance": 0.03, "elasticity": 1.1},
        "chrysanthemum":{"base_sale_chance": 0.03, "elasticity": 1.1},
        "lavender":    {"base_sale_chance": 0.03, "elasticity": 1.1},
        "bouquet":     {"base_sale_chance": 0.02, "elasticity": 1.2},
    }
}

# ── 3b. botanical_garden ──────────────────────────────────────────────────────
dbiz["botanical_garden"] = {
    "name": "Botanical Garden",
    "description": "Premium public botanical garden offering garden passes, rare orchid cultivation, and botanical research. Requires heavy pollination resources.",
    "class": "production",
    "startup_cost": 2000000,
    "base_wage_cost": 8000,
    "cycles_to_complete": 2880,
    "allowed_terrain": ["district_entertainment", "district_entertainment_district", "district_neighborhood", "district_zoo"],
    "production_lines": [
        {
            "output_item": "garden_pass", "output_qty": 50,
            "inputs": [
                {"item": "water",       "quantity": 2000},
                {"item": "energy",      "quantity": 1000},
                {"item": "fertilizer_npk", "quantity": 200},
                {"item": "pollen",      "quantity": 120000},
                {"item": "paper",       "quantity": 50},
            ]
        },
        {
            "output_item": "rare_orchid_specimen", "output_qty": 5,
            "inputs": [
                {"item": "orchid",      "quantity": 50},
                {"item": "lotus",       "quantity": 20},
                {"item": "pollen",      "quantity": 200000},
                {"item": "water",       "quantity": 500},
                {"item": "fertilizer_npk", "quantity": 100},
                {"item": "energy",      "quantity": 800},
                {"item": "glass",       "quantity": 20},
                {"item": "paper",       "quantity": 10},
            ]
        },
        {
            "output_item": "pressed_flower_art", "output_qty": 10,
            "inputs": [
                {"item": "iris",        "quantity": 80},
                {"item": "peony",       "quantity": 60},
                {"item": "violet",      "quantity": 80},
                {"item": "cherry_blossom", "quantity": 60},
                {"item": "pollen",      "quantity": 150000},
                {"item": "glass",       "quantity": 10},
                {"item": "paper",       "quantity": 20},
                {"item": "energy",      "quantity": 400},
            ]
        },
    ]
}

# ── 3c. flower_market_district ────────────────────────────────────────────────
dbiz["flower_market_district"] = {
    "name": "Flower Market",
    "description": "Wholesale district flower market trading bulk cut flowers and finished arrangements. High throughput, pollen-intensive operations.",
    "class": "production",
    "startup_cost": 800000,
    "base_wage_cost": 3500,
    "cycles_to_complete": 1440,
    "allowed_terrain": ["district_food", "district_food_court", "district_mall", "district_mega_mall", "district_neighborhood"],
    "production_lines": [
        {
            "output_item": "bouquet", "output_qty": 80,
            "inputs": [
                {"item": "rose",      "quantity": 200},
                {"item": "lily",      "quantity": 150},
                {"item": "carnation", "quantity": 250},
                {"item": "tulip",     "quantity": 150},
                {"item": "freesia",   "quantity": 100},
                {"item": "pollen",    "quantity": 180000},
                {"item": "paper",     "quantity": 40},
                {"item": "energy",    "quantity": 400},
            ]
        },
        {
            "output_item": "dried_flower_bundle", "output_qty": 100,
            "inputs": [
                {"item": "lavender",  "quantity": 300},
                {"item": "rose",      "quantity": 200},
                {"item": "zinnia",    "quantity": 200},
                {"item": "heather",   "quantity": 200},
                {"item": "chamomile", "quantity": 150},
                {"item": "pollen",    "quantity": 160000},
                {"item": "paper",     "quantity": 30},
                {"item": "energy",    "quantity": 300},
            ]
        },
        {
            "output_item": "floral_centerpiece", "output_qty": 40,
            "inputs": [
                {"item": "hydrangea", "quantity": 150},
                {"item": "peony",     "quantity": 100},
                {"item": "dahlia",    "quantity": 120},
                {"item": "rose",      "quantity": 150},
                {"item": "pollen",    "quantity": 220000},
                {"item": "glass",     "quantity": 40},
                {"item": "energy",    "quantity": 500},
                {"item": "paper",     "quantity": 20},
            ]
        },
    ]
}

# ── 3d. perfume_atelier ───────────────────────────────────────────────────────
dbiz["perfume_atelier"] = {
    "name": "Perfume Atelier",
    "description": "Luxury artisan perfume house hand-crafting signature fragrances from floral absolutes and essential oils. Pollen is used throughout blending and fixation.",
    "class": "production",
    "startup_cost": 1200000,
    "base_wage_cost": 5000,
    "cycles_to_complete": 2160,
    "allowed_terrain": ["district_mall", "district_mega_mall", "district_entertainment_district"],
    "production_lines": [
        {
            "output_item": "signature_perfume", "output_qty": 20,
            "inputs": [
                {"item": "rose_essential_oil",    "quantity": 10},
                {"item": "jasmine_essential_oil", "quantity": 6},
                {"item": "neroli_oil",            "quantity": 4},
                {"item": "orange_essential_oil",  "quantity": 5},
                {"item": "pollen",                "quantity": 100000},
                {"item": "bottle",                "quantity": 20},
                {"item": "energy",                "quantity": 600},
                {"item": "paper",                 "quantity": 10},
            ]
        },
        {
            "output_item": "artisan_fragrance", "output_qty": 25,
            "inputs": [
                {"item": "lavender_essential_oil", "quantity": 12},
                {"item": "rose_water",             "quantity": 20},
                {"item": "neroli_oil",             "quantity": 5},
                {"item": "pollen",                 "quantity": 80000},
                {"item": "bottle",                 "quantity": 25},
                {"item": "energy",                 "quantity": 500},
                {"item": "paper",                  "quantity": 10},
            ]
        },
        {
            "output_item": "cologne", "output_qty": 30,
            "inputs": [
                {"item": "jasmine_essential_oil",  "quantity": 5},
                {"item": "neroli_oil",             "quantity": 5},
                {"item": "lavender_essential_oil", "quantity": 5},
                {"item": "orange_blossom_water",   "quantity": 15},
                {"item": "pollen",                 "quantity": 70000},
                {"item": "bottle",                 "quantity": 30},
                {"item": "energy",                 "quantity": 450},
                {"item": "paper",                  "quantity": 10},
            ]
        },
    ]
}

# ── 3e. floral_event_services ─────────────────────────────────────────────────
dbiz["floral_event_services"] = {
    "name": "Floral Event Services",
    "description": "Full-service floral design studio for weddings, corporate events and funerals. Assembles large-scale arrangements requiring massive pollen at every stage.",
    "class": "production",
    "startup_cost": 600000,
    "base_wage_cost": 2500,
    "cycles_to_complete": 1440,
    "allowed_terrain": ["district_entertainment", "district_convention_center", "district_entertainment_district", "district_neighborhood", "district_mall"],
    "production_lines": [
        {
            "output_item": "wedding_floral_package", "output_qty": 10,
            "inputs": [
                {"item": "wedding_bouquet",    "quantity": 1},
                {"item": "floral_centerpiece", "quantity": 8},
                {"item": "flower_crown",       "quantity": 4},
                {"item": "corsage",            "quantity": 10},
                {"item": "pollen",             "quantity": 200000},
                {"item": "energy",             "quantity": 800},
                {"item": "paper",              "quantity": 20},
            ]
        },
        {
            "output_item": "event_decor_package", "output_qty": 15,
            "inputs": [
                {"item": "floral_centerpiece",  "quantity": 12},
                {"item": "dried_flower_bundle", "quantity": 20},
                {"item": "potpourri",           "quantity": 10},
                {"item": "bouquet",             "quantity": 8},
                {"item": "pollen",              "quantity": 160000},
                {"item": "energy",              "quantity": 600},
                {"item": "paper",               "quantity": 15},
            ]
        },
    ]
}

save("district_businesses.json", dbiz)
print(f"district_businesses: saved with 5 new floral businesses")

# ─── 4. DISTRICT ITEMS ───────────────────────────────────────────────────────
ditems = load("district_items.json")

new_ditems = {
    "garden_pass": {
        "name": "Garden Pass",
        "description": "Day admission to the botanical garden including guided tours",
        "category": "retail_entertainment"
    },
    "wedding_floral_package": {
        "name": "Wedding Floral Package",
        "description": "Complete floral design service for wedding ceremonies and receptions",
        "category": "retail_service"
    },
    "event_decor_package": {
        "name": "Event Decor Package",
        "description": "Full floral decoration service for corporate and private events",
        "category": "retail_service"
    },
}

for key, val in new_ditems.items():
    if key not in ditems:
        ditems[key] = val

save("district_items.json", ditems)
print(f"district_items: {len(ditems)} items total")
print("\nFloral patch complete.")
