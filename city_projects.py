"""
city_projects.py — Municipal Mega-Projects for Wadsworth city governments.

30 city-aesthetic project types across 8 categories. No operational consumption.
Projects are permanent once built — the mayor controls pause/unpause/deconstruct.

KEY MECHANICS
─────────────
City Post Office (MUST be built first, no prerequisites, no licenses required)
  • Generates LICENSES per tick (5 × level). Licenses are stored in CityBank.city_licenses.
  • All other projects consume licenses when construction begins.

Per-project vault
  • Each project type has its own vault keyed by (city_id, project_type, item_type).
  • Players deposit construction materials to the vault (capped at the cost for the target level).
  • Once the vault holds all required materials AND the city has enough licenses, any member
    can trigger "Start Construction" / "Start Upgrade".  Materials + licenses are consumed
    at that moment; vault is cleared when construction completes.
  • Vault cannot be overfilled — deposit is rejected if it would exceed the cap.

Sales tax
  • Active projects with debuffs carry a `sales_tax` debuff (rate per level).
  • `get_city_sales_tax_rate(city_id)` sums all active project debuffs.
  • Deducted in market.py on every player-to-player sell; routed to the city bank.

Special projects (no buff/debuff)
  city_post_office   Generates licenses (5 × level / tick)
  city_extractor     Mines city currency into bank reserves (3 × level / tick)
  municipal_center   Adds 3 member slots per level (default 25 + 3 × level)
  comptroller_office Invests 0.05 % of bank reserves per tick (compound bond returns)
                     [Stable-coin at level 12 is a future dashboard feature]

Construction rules
  • Max 1 new project under construction at a time
  • Max 2 simultaneous upgrades
  • Only the mayor may plan a new project (creates the vault row when materials are needed)
  • Any city member may deposit materials to a project vault
  • Any city member may trigger start construction / upgrade (when vault full + licenses ok)
  • Only the mayor may pause / resume / deconstruct
  • Deconstruction yields nothing; vault is cleared
  • Max 30 non-deconstructed projects per city
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime, UniqueConstraint, text
from sqlalchemy.ext.declarative import declarative_base

from database import engine, SessionLocal, run_ddl_migration

Base = declarative_base()


def get_db():
    return SessionLocal()


# ──────────────────────────────────────────────────────────────
# CONSTANTS
# ──────────────────────────────────────────────────────────────
MAX_PROJECTS_PER_CITY   = 30
MAX_PROJECT_LEVEL       = 12
HIGH_LEVEL_THRESHOLD    = 7       # levels 8-12 use extra cost multiplier
DEFAULT_MEMBER_SLOTS    = 25      # base slots before Municipal Center
LICENSES_PER_TICK_BASE  = 5.0     # city_post_office: per level per tick
EXTRACTOR_CURRENCY_BASE = 3.0     # city_extractor: units city-currency / level / tick
COMPTROLLER_INVEST_RATE = 0.0005  # 0.05 % of cash_reserves per tick

STATUS_CONSTRUCTING   = "constructing"
STATUS_UPGRADING      = "upgrading"
STATUS_ACTIVE         = "active"
STATUS_PAUSED         = "paused"
STATUS_DECONSTRUCTED  = "deconstructed"

POST_OFFICE_KEY      = "city_post_office"
EXTRACTOR_KEY        = "city_extractor"
MUNICIPAL_CENTER_KEY = "municipal_center"
COMPTROLLER_KEY      = "comptroller_office"
SPECIAL_KEYS         = {POST_OFFICE_KEY, EXTRACTOR_KEY, MUNICIPAL_CENTER_KEY, COMPTROLLER_KEY}


# ──────────────────────────────────────────────────────────────
# 30 PROJECT DEFINITIONS
#
# buffs / debuffs scale linearly with level. Keys:
#   output               — adds to output multiplier (0.01 = +1 % / lv)
#   wage_savings         — reduces wage fraction per level
#   input_savings        — reduces input qty fraction per level
#   cycle_speed          — speeds up business cycle (reduces cycles_to_complete fraction)
#   market_fee_reduction — reduces market listing/commission fraction
#   license_production   — bonus licenses / tick / level (float, additive)
#   construction_speed   — reduces construction ticks fraction per level
#   loan_interest_reduction — reduces bank loan interest fraction per level
#
#   sales_tax            — ALWAYS present for non-special projects; rate / level
#   wage_penalty         — increases wage fraction per level (debuff)
#   input_penalty        — increases input qty fraction per level (debuff)
#
# licenses_per_level  — licenses consumed from city bank when construction of each level begins
# base_project_value  — USD contribution to City NAV per level
# ──────────────────────────────────────────────────────────────
CITY_PROJECT_TYPES: Dict[str, Dict[str, Any]] = {

    # ── FOUNDATION ─────────────────────────────────────────────

    POST_OFFICE_KEY: {
        "name": "City Post Office", "category": "foundation",
        "description": (
            "The first building that must be constructed before any other city project. "
            "Issues construction licenses continuously, fuelling all future municipal growth. "
            "No buffs or debuffs — it is simply the cornerstone of city governance."
        ),
        "construction_materials": {
            "lumber": 3_000, "iron": 2_000, "glass": 1_500,
            "paper": 5_000, "copper": 1_000,
        },
        "licenses_per_level": 0,
        "buffs": {}, "debuffs": {},
        "base_project_value": 500_000,
    },

    "city_hall": {
        "name": "City Hall", "category": "foundation",
        "description": (
            "The seat of city government. A grand civic building that accelerates license "
            "production, speeds up all municipal construction, and boosts resident output. "
            "Its bureaucratic overhead adds a small wage burden and sales levy."
        ),
        "construction_materials": {
            "concrete": 8_000, "steel": 6_000, "copper_wire": 3_000,
            "glass": 4_000, "iron": 5_000,
        },
        "licenses_per_level": 50_000,
        "buffs":   {"license_production": 0.5, "construction_speed": 0.008, "output": 0.010},
        "debuffs": {"sales_tax": 0.002, "wage_penalty": 0.004, "input_penalty": 0.002},
        "base_project_value": 1_000_000,
    },

    MUNICIPAL_CENTER_KEY: {
        "name": "Municipal Center", "category": "foundation",
        "description": (
            "A large administrative and civic complex that expands the city's residential "
            "capacity by 3 member slots per level. No production buffs or debuffs — its "
            "value is purely in allowing the city to grow its population."
        ),
        "construction_materials": {
            "concrete": 12_000, "steel": 10_000, "glass": 6_000,
            "copper_wire": 3_000, "aluminum": 4_000,
        },
        "licenses_per_level": 75_000,
        "buffs": {}, "debuffs": {},
        "base_project_value": 750_000,
    },

    EXTRACTOR_KEY: {
        "name": "City Extractor", "category": "foundation",
        "description": (
            "A network of automated mining, drilling, and harvesting facilities that "
            "continuously extract value from the city's territory and deposit city "
            "currency directly into the bank's reserves (3 × level units / tick). "
            "No buffs or debuffs — pure passive income for the city."
        ),
        "construction_materials": {
            "iron": 15_000, "steel": 12_000, "aluminum": 6_000,
            "copper": 8_000, "coal": 8_000,
        },
        "licenses_per_level": 100_000,
        "buffs": {}, "debuffs": {},
        "base_project_value": 2_000_000,
    },

    COMPTROLLER_KEY: {
        "name": "Office of the Comptroller", "category": "foundation",
        "description": (
            "The city's sovereign wealth engine. Each tick it invests 0.05 % of the city "
            "bank's cash reserves in municipal bonds, compounding returns directly back into "
            "reserves. At level 12 it mints a city-backed stable coin pegged 1:1 to the "
            "mayor's selected currency (0.01 % of reserves / tick). No member buffs or debuffs."
        ),
        "construction_materials": {
            "concrete": 10_000, "steel": 8_000, "circuit_board": 4_000,
            "glass": 6_000, "paper": 15_000,
        },
        "licenses_per_level": 150_000,
        "buffs": {}, "debuffs": {},
        "base_project_value": 5_000_000,
    },

    # ── PUBLIC SAFETY ──────────────────────────────────────────

    "police_department": {
        "name": "Police Department", "category": "public_safety",
        "description": (
            "City law-enforcement infrastructure that reduces fraud and theft risk, "
            "lowers overhead wage costs for member businesses, and generates modest "
            "output gains. Funded through a small municipal sales levy."
        ),
        "construction_materials": {
            "concrete": 10_000, "steel": 6_000, "aluminum": 4_000,
            "circuit_board": 2_000, "rubber": 3_000,
        },
        "licenses_per_level": 50_000,
        "buffs":   {"wage_savings": 0.008, "market_fee_reduction": 0.010, "output": 0.008},
        "debuffs": {"sales_tax": 0.002, "wage_penalty": 0.004, "input_penalty": 0.003},
        "base_project_value": 800_000,
    },

    "fire_station": {
        "name": "Fire Station & Emergency Services", "category": "public_safety",
        "description": (
            "A network of fire halls and emergency response centres that protect member "
            "businesses from loss and speed up all city construction timelines. "
            "Staffing costs introduce a small wage drag and municipal sales tax."
        ),
        "construction_materials": {
            "concrete": 8_000, "steel": 5_000, "aluminum": 3_000,
            "copper": 1_500, "rubber": 2_500,
        },
        "licenses_per_level": 50_000,
        "buffs":   {"construction_speed": 0.010, "wage_savings": 0.008, "cycle_speed": 0.006},
        "debuffs": {"sales_tax": 0.002, "wage_penalty": 0.004, "input_penalty": 0.003},
        "base_project_value": 600_000,
    },

    "city_hospital": {
        "name": "City Hospital", "category": "public_safety",
        "description": (
            "A full-service municipal hospital that keeps workers healthy, dramatically "
            "accelerating business cycle throughput and cutting wage overhead. "
            "High construction and operating complexity adds a significant sales levy."
        ),
        "construction_materials": {
            "concrete": 18_000, "steel": 12_000, "glass": 8_000,
            "copper": 4_000, "circuit_board": 5_000,
        },
        "licenses_per_level": 100_000,
        "buffs":   {"cycle_speed": 0.012, "wage_savings": 0.010, "output": 0.010},
        "debuffs": {"sales_tax": 0.003, "wage_penalty": 0.004, "input_penalty": 0.003},
        "base_project_value": 2_000_000,
    },

    # ── UTILITIES ──────────────────────────────────────────────

    "power_grid": {
        "name": "Municipal Power Grid", "category": "utilities",
        "description": (
            "City-owned electrical infrastructure providing cheap energy to all "
            "member businesses, boosting output, cutting input material needs, "
            "and shortening production cycles. High capital intensity raises the "
            "input overhead and sales levy for residents."
        ),
        "construction_materials": {
            "iron": 18_000, "copper": 12_000, "steel": 8_000,
            "aluminum": 6_000, "glass": 4_000,
        },
        "licenses_per_level": 80_000,
        "buffs":   {"output": 0.015, "input_savings": 0.010, "cycle_speed": 0.008},
        "debuffs": {"sales_tax": 0.003, "wage_penalty": 0.004, "input_penalty": 0.004},
        "base_project_value": 1_500_000,
    },

    "water_treatment": {
        "name": "Water Treatment Facility", "category": "utilities",
        "description": (
            "Industrial-scale water purification delivering clean water to every "
            "production facility, reducing input material waste and lowering wage "
            "overhead. Maintenance costs add a modest municipal levy."
        ),
        "construction_materials": {
            "concrete": 12_000, "steel": 8_000, "copper": 6_000,
            "iron": 10_000, "cement": 5_000,
        },
        "licenses_per_level": 60_000,
        "buffs":   {"input_savings": 0.012, "wage_savings": 0.008, "output": 0.008},
        "debuffs": {"sales_tax": 0.002, "wage_penalty": 0.004, "input_penalty": 0.003},
        "base_project_value": 1_000_000,
    },

    "waste_management": {
        "name": "Waste Management", "category": "utilities",
        "description": (
            "A city-wide waste collection, sorting, and recycling system that turns "
            "industrial byproducts back into usable inputs, speeds up cycles, and "
            "reduces raw material demand. The associated levy is light."
        ),
        "construction_materials": {
            "concrete": 8_000, "steel": 6_000, "iron": 5_000,
            "rubber": 3_000, "cement": 4_000,
        },
        "licenses_per_level": 50_000,
        "buffs":   {"input_savings": 0.010, "cycle_speed": 0.008, "wage_savings": 0.006},
        "debuffs": {"sales_tax": 0.002, "wage_penalty": 0.003, "input_penalty": 0.003},
        "base_project_value": 600_000,
    },

    # ── TRANSPORTATION ─────────────────────────────────────────

    "public_transit": {
        "name": "City Transit Authority", "category": "transportation",
        "description": (
            "A network of buses, trams, and rail lines that reduces worker commute "
            "times, shortening every production cycle. Cheaper freight movement also "
            "compresses market listing fees. Staffing costs add a modest levy."
        ),
        "construction_materials": {
            "steel": 10_000, "concrete": 12_000, "copper_wire": 6_000,
            "rubber": 5_000, "aluminum": 4_000,
        },
        "licenses_per_level": 70_000,
        "buffs":   {"cycle_speed": 0.012, "market_fee_reduction": 0.010, "input_savings": 0.008},
        "debuffs": {"sales_tax": 0.002, "wage_penalty": 0.004, "input_penalty": 0.003},
        "base_project_value": 1_000_000,
    },

    "port_authority": {
        "name": "Port Authority", "category": "transportation",
        "description": (
            "Deepwater docking, warehousing, and customs facilities that dramatically "
            "expand export capacity, cutting market fees and boosting production output. "
            "Enormous infrastructure demands and a significant sales levy."
        ),
        "construction_materials": {
            "concrete": 20_000, "steel": 16_000, "iron": 12_000,
            "aluminum": 6_000, "lumber": 8_000,
        },
        "licenses_per_level": 150_000,
        "buffs":   {"output": 0.018, "market_fee_reduction": 0.015, "input_savings": 0.010},
        "debuffs": {"sales_tax": 0.004, "wage_penalty": 0.006, "input_penalty": 0.005},
        "base_project_value": 3_000_000,
    },

    "city_airport": {
        "name": "Municipal Airport", "category": "transportation",
        "description": (
            "A full international airport connecting the city to global markets. "
            "The largest single infrastructure project available — it provides the "
            "highest output boost and market fee reduction in the game, but requires "
            "massive construction resources, high licenses, and a heavy sales levy."
        ),
        "construction_materials": {
            "concrete": 25_000, "steel": 20_000, "aluminum": 12_000,
            "glass": 8_000, "copper_wire": 6_000, "rebar": 10_000,
        },
        "licenses_per_level": 200_000,
        "buffs":   {"output": 0.020, "market_fee_reduction": 0.018, "cycle_speed": 0.010},
        "debuffs": {"sales_tax": 0.005, "wage_penalty": 0.006, "input_penalty": 0.005},
        "base_project_value": 5_000_000,
    },

    "rail_terminal": {
        "name": "Rail Terminal", "category": "transportation",
        "description": (
            "An intermodal rail hub connecting city districts and reducing freight "
            "transit times. Speeds production cycles, cuts input material needs, "
            "and raises overall output. Labor-intensive operations add a sales levy."
        ),
        "construction_materials": {
            "steel": 16_000, "concrete": 14_000, "iron": 10_000,
            "copper_wire": 5_000, "lumber": 6_000,
        },
        "licenses_per_level": 100_000,
        "buffs":   {"cycle_speed": 0.015, "input_savings": 0.012, "output": 0.010},
        "debuffs": {"sales_tax": 0.003, "wage_penalty": 0.005, "input_penalty": 0.004},
        "base_project_value": 2_000_000,
    },

    # ── COMMERCE & FINANCE ─────────────────────────────────────

    "city_market": {
        "name": "City Market Hall", "category": "commerce",
        "description": (
            "A permanent, city-operated market hall that dramatically reduces listing "
            "and commission fees for all member traders, while boosting output and "
            "speeding up business cycles. Light levy and modest debuffs."
        ),
        "construction_materials": {
            "lumber": 12_000, "sand": 8_000, "steel": 6_000,
            "glass": 5_000, "copper": 3_000,
        },
        "licenses_per_level": 80_000,
        "buffs":   {"market_fee_reduction": 0.015, "output": 0.010, "cycle_speed": 0.008},
        "debuffs": {"sales_tax": 0.002, "wage_penalty": 0.004, "input_penalty": 0.003},
        "base_project_value": 1_200_000,
    },

    "trade_district": {
        "name": "Commercial Trade District", "category": "commerce",
        "description": (
            "A dedicated commercial zone with standardised contracts and bulk-trading "
            "infrastructure. Slashes market fees, boosts production output, and "
            "reduces raw material consumption. Significant levy due to high land cost."
        ),
        "construction_materials": {
            "concrete": 16_000, "steel": 12_000, "glass": 10_000,
            "lumber": 6_000, "copper_wire": 5_000,
        },
        "licenses_per_level": 100_000,
        "buffs":   {"market_fee_reduction": 0.018, "output": 0.012, "input_savings": 0.008},
        "debuffs": {"sales_tax": 0.003, "wage_penalty": 0.004, "input_penalty": 0.004},
        "base_project_value": 2_000_000,
    },

    "stock_exchange": {
        "name": "City Stock Exchange", "category": "commerce",
        "description": (
            "A state-of-the-art electronic trading floor providing the highest market "
            "fee reduction in the game alongside significant loan interest savings. "
            "Its enormous financial leverage comes at the cost of the highest sales tax "
            "of any city project — it attracts revenue but also takes a large cut."
        ),
        "construction_materials": {
            "concrete": 15_000, "steel": 12_000, "glass": 10_000,
            "circuit_board": 6_000, "copper_wire": 5_000,
        },
        "licenses_per_level": 150_000,
        "buffs":   {"market_fee_reduction": 0.020, "loan_interest_reduction": 0.015, "output": 0.012},
        "debuffs": {"sales_tax": 0.006, "wage_penalty": 0.005, "input_penalty": 0.004},
        "base_project_value": 3_000_000,
    },

    "city_treasury": {
        "name": "City Treasury", "category": "commerce",
        "description": (
            "The municipal vault and fiscal management authority. Cuts bank loan interest "
            "for all member businesses, reduces wage overhead, and trims market costs. "
            "Its regulatory burden adds a modest sales levy."
        ),
        "construction_materials": {
            "concrete": 12_000, "steel": 10_000, "copper_wire": 6_000,
            "circuit_board": 6_000, "paper": 12_000,
        },
        "licenses_per_level": 120_000,
        "buffs":   {"loan_interest_reduction": 0.015, "wage_savings": 0.012, "market_fee_reduction": 0.010},
        "debuffs": {"sales_tax": 0.003, "wage_penalty": 0.004, "input_penalty": 0.003},
        "base_project_value": 2_500_000,
    },

    "customs_authority": {
        "name": "Customs & Trade Authority", "category": "commerce",
        "description": (
            "Streamlined customs clearance and trade facilitation that cuts market fees, "
            "boosts production output, and reduces input material waste. Staffed by "
            "inspectors whose wages are offset by a light municipal levy."
        ),
        "construction_materials": {
            "concrete": 10_000, "steel": 8_000, "circuit_board": 5_000,
            "copper_wire": 3_000, "aluminum": 3_000,
        },
        "licenses_per_level": 80_000,
        "buffs":   {"market_fee_reduction": 0.012, "output": 0.015, "input_savings": 0.008},
        "debuffs": {"sales_tax": 0.002, "wage_penalty": 0.004, "input_penalty": 0.003},
        "base_project_value": 1_500_000,
    },

    # ── EDUCATION ──────────────────────────────────────────────

    "public_schools": {
        "name": "Public School System", "category": "education",
        "description": (
            "A network of schools, vocational colleges, and training centres that "
            "produces a more skilled workforce. Speeds up every business cycle, "
            "accelerates city construction, and generates a small license bonus. "
            "Teacher salaries add a modest levy and wage drag."
        ),
        "construction_materials": {
            "concrete": 10_000, "lumber": 6_000, "glass": 5_000,
            "paper": 15_000, "copper_wire": 2_500,
        },
        "licenses_per_level": 60_000,
        "buffs":   {"cycle_speed": 0.010, "construction_speed": 0.010, "license_production": 0.30},
        "debuffs": {"sales_tax": 0.002, "wage_penalty": 0.005, "input_penalty": 0.003},
        "base_project_value": 800_000,
    },

    "city_library": {
        "name": "City Library", "category": "education",
        "description": (
            "A grand public library and archival complex that is the city's primary "
            "secondary license producer. Also speeds up all construction projects and "
            "reduces workforce wages. Light levy and modest debuffs."
        ),
        "construction_materials": {
            "iron": 10_000, "lumber": 8_000, "glass": 6_000,
            "concrete": 8_000, "paper": 20_000,
        },
        "licenses_per_level": 70_000,
        "buffs":   {"license_production": 0.50, "construction_speed": 0.012, "wage_savings": 0.008},
        "debuffs": {"sales_tax": 0.002, "wage_penalty": 0.004, "input_penalty": 0.003},
        "base_project_value": 800_000,
    },

    "research_institute": {
        "name": "City Research Institute", "category": "education",
        "description": (
            "A world-class R&D campus that translates cutting-edge science into higher "
            "production output, faster business cycles, and accelerated city construction. "
            "Expensive to equip, with notable input and sales-tax costs."
        ),
        "construction_materials": {
            "steel": 12_000, "glass": 10_000, "circuit_board": 8_000,
            "fiberglass": 6_000, "copper": 5_000,
        },
        "licenses_per_level": 100_000,
        "buffs":   {"output": 0.015, "cycle_speed": 0.012, "construction_speed": 0.015},
        "debuffs": {"sales_tax": 0.003, "wage_penalty": 0.005, "input_penalty": 0.004},
        "base_project_value": 2_000_000,
    },

    # ── CULTURE & TOURISM ──────────────────────────────────────

    "city_park": {
        "name": "City Park & Recreation", "category": "culture",
        "description": (
            "Expansive parks, sports facilities, and green spaces that improve resident "
            "wellbeing, reducing worker absenteeism (wage savings) and boosting "
            "motivation (cycle speed and output). A light levy funds maintenance."
        ),
        "construction_materials": {
            "iron": 8_000, "lumber": 10_000, "sand": 8_000,
            "glass": 3_000, "copper": 2_500,
        },
        "licenses_per_level": 50_000,
        "buffs":   {"wage_savings": 0.010, "cycle_speed": 0.008, "output": 0.008},
        "debuffs": {"sales_tax": 0.002, "wage_penalty": 0.003, "input_penalty": 0.002},
        "base_project_value": 600_000,
    },

    "convention_center": {
        "name": "Convention Center", "category": "culture",
        "description": (
            "A massive events and trade-show venue that draws outside buyers to the city, "
            "cutting market fees and boosting production output. Cycle times shrink as "
            "local commerce accelerates. Construction and upkeep add a notable levy."
        ),
        "construction_materials": {
            "concrete": 16_000, "steel": 12_000, "glass": 10_000,
            "copper_wire": 5_000, "circuit_board": 4_000,
        },
        "licenses_per_level": 100_000,
        "buffs":   {"market_fee_reduction": 0.015, "output": 0.012, "cycle_speed": 0.010},
        "debuffs": {"sales_tax": 0.003, "wage_penalty": 0.004, "input_penalty": 0.003},
        "base_project_value": 1_500_000,
    },

    "cultural_arts_center": {
        "name": "Cultural Arts Center", "category": "culture",
        "description": (
            "A museum, theatre, and arts complex that elevates civic pride. Generates "
            "a modest license bonus, cuts wage costs through community investment, and "
            "gently speeds up production. Light levy and minor debuffs."
        ),
        "construction_materials": {
            "iron": 10_000, "concrete": 8_000, "lumber": 6_000,
            "glass": 5_000, "copper": 3_500,
        },
        "licenses_per_level": 70_000,
        "buffs":   {"license_production": 0.40, "wage_savings": 0.010, "cycle_speed": 0.008},
        "debuffs": {"sales_tax": 0.002, "wage_penalty": 0.003, "input_penalty": 0.002},
        "base_project_value": 800_000,
    },

    "media_tower": {
        "name": "City Media Tower", "category": "culture",
        "description": (
            "A broadcast tower, streaming hub, and civic communications centre that "
            "amplifies market visibility, boosts output, and tightens business cycles. "
            "High tech infrastructure raises input and wage pressure with a sales levy."
        ),
        "construction_materials": {
            "steel": 12_000, "aluminum": 10_000, "circuit_board": 8_000,
            "glass": 6_000, "copper_wire": 4_000,
        },
        "licenses_per_level": 90_000,
        "buffs":   {"market_fee_reduction": 0.012, "output": 0.015, "cycle_speed": 0.010},
        "debuffs": {"sales_tax": 0.003, "wage_penalty": 0.004, "input_penalty": 0.003},
        "base_project_value": 1_500_000,
    },

    # ── INDUSTRY & ENVIRONMENT ─────────────────────────────────

    "industrial_zone": {
        "name": "Industrial Zone Authority", "category": "industry",
        "description": (
            "A managed heavy-industrial district with shared infrastructure that provides "
            "the highest production output and input savings of any single project. "
            "The trade-off: significant input penalty and sales levy reflect the city's "
            "dependence on raw industrial throughput."
        ),
        "construction_materials": {
            "concrete": 20_000, "steel": 16_000, "iron": 12_000,
            "aluminum": 6_000, "rebar": 8_000,
        },
        "licenses_per_level": 120_000,
        "buffs":   {"output": 0.020, "input_savings": 0.015, "cycle_speed": 0.010},
        "debuffs": {"sales_tax": 0.004, "wage_penalty": 0.005, "input_penalty": 0.005},
        "base_project_value": 3_000_000,
    },

    "environmental_agency": {
        "name": "Environmental Protection Agency", "category": "industry",
        "description": (
            "A regulatory and remediation authority that enforces cleaner production "
            "standards, reducing raw material waste and cutting workforce costs. "
            "Compliance costs impose a mild input overhead and modest sales levy."
        ),
        "construction_materials": {
            "steel": 10_000, "concrete": 8_000, "circuit_board": 5_000,
            "glass": 4_000, "paper": 12_000,
        },
        "licenses_per_level": 80_000,
        "buffs":   {"input_savings": 0.012, "wage_savings": 0.010, "output": 0.008},
        "debuffs": {"sales_tax": 0.002, "wage_penalty": 0.004, "input_penalty": 0.003},
        "base_project_value": 1_000_000,
    },

    "zoning_office": {
        "name": "Zoning & Planning Office", "category": "industry",
        "description": (
            "The city's land-use planning authority. Pre-approved construction permits "
            "slash build times for all projects, and a dedicated licensing division "
            "boosts license production. Bureaucratic complexity adds a light levy."
        ),
        "construction_materials": {
            "concrete": 8_000, "steel": 6_000, "glass": 4_000,
            "circuit_board": 3_000, "paper": 10_000,
        },
        "licenses_per_level": 70_000,
        "buffs":   {"construction_speed": 0.015, "license_production": 0.40, "wage_savings": 0.008},
        "debuffs": {"sales_tax": 0.002, "wage_penalty": 0.004, "input_penalty": 0.002},
        "base_project_value": 1_000_000,
    },
}


# ──────────────────────────────────────────────────────────────
# DATABASE MODELS
# ──────────────────────────────────────────────────────────────

class CityProjectInstance(Base):
    """A city's active or in-progress project instance."""
    __tablename__ = "city_project_instances"

    id = Column(Integer, primary_key=True, index=True)
    city_id = Column(Integer, index=True, nullable=False)
    project_type = Column(String, nullable=False)
    level = Column(Integer, default=0)
    target_level = Column(Integer, default=1)
    status = Column(String, default=STATUS_CONSTRUCTING)
    construction_ticks_required = Column(Integer, default=2160)
    construction_ticks_completed = Column(Integer, default=0)
    construction_started_at = Column(DateTime, nullable=True)
    started_by = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    total_ticks_active = Column(Integer, default=0)


class CityProjectVault(Base):
    """
    Per-project staging vault for construction materials.
    Keyed by (city_id, project_type, item_type).
    Vault capacity = construction cost for the next target level.
    Vault is cleared when construction completes or the project is deconstructed.
    """
    __tablename__ = "city_project_vaults"
    __table_args__ = (UniqueConstraint("city_id", "project_type", "item_type"),)

    id = Column(Integer, primary_key=True, index=True)
    city_id = Column(Integer, index=True, nullable=False)
    project_type = Column(String, nullable=False)
    item_type = Column(String, nullable=False)
    quantity = Column(Float, default=0.0)
    last_updated = Column(DateTime, default=datetime.utcnow)


# Legacy table — kept for schema compatibility; no longer used operationally.
class CityResourceVault(Base):
    __tablename__ = "city_resource_vaults"
    __table_args__ = (UniqueConstraint("city_id", "item_type"),)

    id = Column(Integer, primary_key=True, index=True)
    city_id = Column(Integer, index=True, nullable=False)
    item_type = Column(String, nullable=False)
    quantity = Column(Float, default=0.0)
    last_updated = Column(DateTime, default=datetime.utcnow)


# ──────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────

def _construction_qty(base_qty: float, level: int) -> float:
    """Scale construction material cost by level."""
    if level <= HIGH_LEVEL_THRESHOLD:
        return base_qty * level
    return base_qty * level * (level - HIGH_LEVEL_THRESHOLD)


def _construction_ticks(level: int) -> int:
    """Ticks required to construct or upgrade to the given level."""
    if level <= 3:
        return 2_160    # 3 h
    if level <= 6:
        return 4_320    # 6 h
    if level <= 9:
        return 8_640    # 12 h
    return 17_280 * (level - 9)   # 24 h / 48 h / 72 h for levels 10/11/12


def _is_city_mayor(player_id: int, city_id: int) -> bool:
    try:
        from cities import is_mayor
        return is_mayor(player_id, city_id)
    except Exception:
        return False


def _is_city_member(player_id: int, city_id: int) -> bool:
    try:
        from cities import is_city_member
        return is_city_member(player_id, city_id)
    except Exception:
        return False


def _get_player_city_id(player_id: int) -> Optional[int]:
    try:
        from cities import get_player_city
        city = get_player_city(player_id)
        return city.id if city else None
    except Exception:
        return None


def _get_city_licenses(db, city_id: int) -> float:
    """Return current city license balance from CityBank."""
    try:
        from cities import CityBank, get_db as city_get_db
        bank = db.query(CityBank).filter(CityBank.city_id == city_id).first()
        if bank:
            return getattr(bank, "city_licenses", 0.0) or 0.0
        return 0.0
    except Exception:
        return 0.0


def _deduct_city_licenses(db, city_id: int, amount: float) -> bool:
    """Deduct licenses from city bank. Returns False if insufficient."""
    if amount <= 0:
        return True
    try:
        from cities import CityBank
        bank = db.query(CityBank).filter(CityBank.city_id == city_id).first()
        if not bank:
            return False
        current = getattr(bank, "city_licenses", 0.0) or 0.0
        if current < amount:
            return False
        bank.city_licenses = current - amount
        return True
    except Exception:
        return False


def _get_vault_row(db, city_id: int, project_type: str, item_type: str) -> CityProjectVault:
    """Fetch or create a vault row for the given (city, project, item)."""
    row = db.query(CityProjectVault).filter(
        CityProjectVault.city_id == city_id,
        CityProjectVault.project_type == project_type,
        CityProjectVault.item_type == item_type,
    ).first()
    if not row:
        row = CityProjectVault(
            city_id=city_id, project_type=project_type,
            item_type=item_type, quantity=0.0,
        )
        db.add(row)
        db.flush()
    return row


def _deduct_from_project_vault(db, city_id: int, project_type: str,
                                materials: Dict[str, float]) -> bool:
    """All-or-nothing deduction from a project's vault. Returns False if any item insufficient."""
    rows: Dict[str, tuple] = {}
    for item_type, qty in materials.items():
        if qty <= 0:
            continue
        row = _get_vault_row(db, city_id, project_type, item_type)
        if row.quantity < qty:
            return False
        rows[item_type] = (row, qty)
    for item_type, (row, qty) in rows.items():
        row.quantity -= qty
        row.last_updated = datetime.utcnow()
    return True


def _clear_project_vault(db, city_id: int, project_type: str) -> None:
    """Delete all vault rows for a given (city, project)."""
    db.query(CityProjectVault).filter(
        CityProjectVault.city_id == city_id,
        CityProjectVault.project_type == project_type,
    ).delete()


def _has_post_office(city_id: int) -> bool:
    """Return True if city has an active/paused/upgrading post office."""
    db = get_db()
    try:
        inst = db.query(CityProjectInstance).filter(
            CityProjectInstance.city_id == city_id,
            CityProjectInstance.project_type == POST_OFFICE_KEY,
            CityProjectInstance.status.in_([STATUS_ACTIVE, STATUS_PAUSED, STATUS_UPGRADING]),
        ).first()
        return inst is not None
    finally:
        db.close()


# ──────────────────────────────────────────────────────────────
# CONSTRUCTION REQUIREMENTS
# ──────────────────────────────────────────────────────────────

def get_construction_requirements(project_type: str, target_level: int) -> Dict[str, float]:
    """Return {item_type: quantity} for constructing/upgrading to target_level."""
    defn = CITY_PROJECT_TYPES.get(project_type)
    if not defn:
        return {}
    return {
        item: _construction_qty(qty, target_level)
        for item, qty in defn.get("construction_materials", {}).items()
    }


# ──────────────────────────────────────────────────────────────
# QUERY API
# ──────────────────────────────────────────────────────────────

def get_city_projects(city_id: int) -> List[dict]:
    db = get_db()
    try:
        instances = db.query(CityProjectInstance).filter(
            CityProjectInstance.city_id == city_id,
            CityProjectInstance.status != STATUS_DECONSTRUCTED,
        ).all()
        result = []
        for inst in instances:
            defn = CITY_PROJECT_TYPES.get(inst.project_type, {})
            ticks_req = inst.construction_ticks_required or 1
            result.append({
                "id":              inst.id,
                "project_type":    inst.project_type,
                "name":            defn.get("name", inst.project_type),
                "description":     defn.get("description", ""),
                "category":        defn.get("category", ""),
                "is_special":      inst.project_type in SPECIAL_KEYS,
                "level":           inst.level,
                "target_level":    inst.target_level,
                "status":          inst.status,
                "ticks_required":  ticks_req,
                "ticks_done":      inst.construction_ticks_completed,
                "progress_pct":    round(100 * min(inst.construction_ticks_completed, ticks_req) / ticks_req, 1),
                "buffs":           defn.get("buffs", {}),
                "debuffs":         defn.get("debuffs", {}),
                "licenses_per_level": defn.get("licenses_per_level", 0),
            })
        return result
    finally:
        db.close()


def get_project_vault_status(city_id: int, project_type: str) -> Dict[str, Any]:
    """
    Return vault contents and fill percentages for a project's next build level.
    Also returns whether construction can start (vault full + enough licenses).
    """
    db = get_db()
    try:
        # Determine the next target level
        inst = db.query(CityProjectInstance).filter(
            CityProjectInstance.city_id == city_id,
            CityProjectInstance.project_type == project_type,
            CityProjectInstance.status != STATUS_DECONSTRUCTED,
        ).first()

        if inst and inst.status in (STATUS_CONSTRUCTING, STATUS_UPGRADING):
            # Currently building — no deposits allowed
            return {"under_construction": True, "items": {}, "ready": False}

        current_level = inst.level if inst else 0
        target_level = current_level + 1
        if target_level > MAX_PROJECT_LEVEL:
            return {"at_max": True, "items": {}, "ready": False}

        required = get_construction_requirements(project_type, target_level)
        vault_rows = db.query(CityProjectVault).filter(
            CityProjectVault.city_id == city_id,
            CityProjectVault.project_type == project_type,
        ).all()
        vault = {r.item_type: r.quantity for r in vault_rows}

        defn = CITY_PROJECT_TYPES.get(project_type, {})
        licenses_needed = defn.get("licenses_per_level", 0)
        licenses_held = _get_city_licenses(db, city_id)

        items = {}
        all_materials_ready = True
        for item_type, qty_needed in required.items():
            held = vault.get(item_type, 0.0)
            pct = min(100.0, round(100 * held / qty_needed, 1)) if qty_needed else 100.0
            items[item_type] = {
                "needed": qty_needed,
                "held": held,
                "pct": pct,
                "full": held >= qty_needed,
            }
            if held < qty_needed:
                all_materials_ready = False

        licenses_ok = licenses_held >= licenses_needed
        return {
            "under_construction": False,
            "at_max": False,
            "target_level": target_level,
            "items": items,
            "licenses_needed": licenses_needed,
            "licenses_held": licenses_held,
            "licenses_ok": licenses_ok,
            "materials_ready": all_materials_ready,
            "ready": all_materials_ready and licenses_ok,
        }
    finally:
        db.close()


def get_city_project_value(city_id: int) -> float:
    db = get_db()
    try:
        instances = db.query(CityProjectInstance).filter(
            CityProjectInstance.city_id == city_id,
            CityProjectInstance.status.in_([STATUS_ACTIVE, STATUS_PAUSED, STATUS_UPGRADING]),
        ).all()
        total = 0.0
        for inst in instances:
            defn = CITY_PROJECT_TYPES.get(inst.project_type, {})
            total += defn.get("base_project_value", 0.0) * inst.level
        return total
    finally:
        db.close()


def get_city_production_buffs(player_id: int) -> Dict[str, float]:
    """
    Return combined production multipliers for a player based on their city's
    active projects.

    Returns:
      output_multiplier        (>= 0.5)  multiply all production output quantities
      wage_multiplier          (>= 0.1)  multiply all wage costs
      input_multiplier         (>= 0.1)  multiply all input quantities
      cycle_speed_multiplier   (<= 1.0)  multiply cycles_to_complete (lower = faster)
      market_fee_multiplier    (>= 0.0)  multiply market fees (lower = cheaper)
      construction_speed_mult  (<= 1.0)  multiply construction ticks (lower = faster)
      loan_interest_multiplier (>= 0.1)  multiply loan interest rates
      license_production_bonus (float)   extra licenses/tick added to city base
      sales_tax_rate           (0–0.5)   fraction of market sale proceeds taxed
    """
    city_id = _get_player_city_id(player_id)
    if not city_id:
        return {
            "output_multiplier": 1.0, "wage_multiplier": 1.0, "input_multiplier": 1.0,
            "cycle_speed_multiplier": 1.0, "market_fee_multiplier": 1.0,
            "construction_speed_mult": 1.0, "loan_interest_multiplier": 1.0,
            "license_production_bonus": 0.0, "sales_tax_rate": 0.0,
        }

    db = get_db()
    try:
        instances = db.query(CityProjectInstance).filter(
            CityProjectInstance.city_id == city_id,
            CityProjectInstance.status == STATUS_ACTIVE,
            CityProjectInstance.level > 0,
        ).all()

        total_output = total_wage_save = total_input_save = 0.0
        total_wage_pen = total_input_pen = 0.0
        total_cycle = total_fee = total_cs = total_loan = 0.0
        total_lic_bonus = total_tax = 0.0

        for inst in instances:
            defn = CITY_PROJECT_TYPES.get(inst.project_type, {})
            b = defn.get("buffs", {})
            d = defn.get("debuffs", {})
            lv = inst.level
            total_output    += b.get("output", 0.0)              * lv
            total_wage_save += b.get("wage_savings", 0.0)        * lv
            total_input_save+= b.get("input_savings", 0.0)       * lv
            total_cycle     += b.get("cycle_speed", 0.0)         * lv
            total_fee       += b.get("market_fee_reduction", 0.0)* lv
            total_cs        += b.get("construction_speed", 0.0)  * lv
            total_loan      += b.get("loan_interest_reduction", 0.0) * lv
            total_lic_bonus += b.get("license_production", 0.0)  * lv
            total_wage_pen  += d.get("wage_penalty", 0.0)        * lv
            total_input_pen += d.get("input_penalty", 0.0)       * lv
            total_tax       += d.get("sales_tax", 0.0)           * lv

        return {
            "output_multiplier":       max(0.5,  1.0 + total_output),
            "wage_multiplier":         max(0.1,  1.0 - (total_wage_save - total_wage_pen)),
            "input_multiplier":        max(0.1,  1.0 - (total_input_save - total_input_pen)),
            "cycle_speed_multiplier":  max(0.3,  1.0 - total_cycle),
            "market_fee_multiplier":   max(0.0,  1.0 - total_fee),
            "construction_speed_mult": max(0.2,  1.0 - total_cs),
            "loan_interest_multiplier":max(0.1,  1.0 - total_loan),
            "license_production_bonus":total_lic_bonus,
            "sales_tax_rate":          min(0.50, total_tax),
        }
    finally:
        db.close()


def get_city_sales_tax_rate(city_id: int) -> float:
    """Return combined sales tax rate for a city (sum of all active project debuffs)."""
    db = get_db()
    try:
        instances = db.query(CityProjectInstance).filter(
            CityProjectInstance.city_id == city_id,
            CityProjectInstance.status == STATUS_ACTIVE,
            CityProjectInstance.level > 0,
        ).all()
        total = sum(
            CITY_PROJECT_TYPES.get(inst.project_type, {}).get("debuffs", {}).get("sales_tax", 0.0)
            * inst.level
            for inst in instances
        )
        return min(0.50, total)
    finally:
        db.close()


def get_effective_max_members(city_id: int) -> int:
    """Return maximum city members after Municipal Center bonus (3 × level)."""
    db = get_db()
    try:
        inst = db.query(CityProjectInstance).filter(
            CityProjectInstance.city_id == city_id,
            CityProjectInstance.project_type == MUNICIPAL_CENTER_KEY,
            CityProjectInstance.status == STATUS_ACTIVE,
        ).first()
        bonus = (inst.level * 3) if inst else 0
        return DEFAULT_MEMBER_SLOTS + bonus
    finally:
        db.close()


# ──────────────────────────────────────────────────────────────
# VAULT MANAGEMENT
# ──────────────────────────────────────────────────────────────

def deposit_to_project_vault(player_id: int, city_id: int,
                              project_type: str, item_type: str,
                              quantity: float) -> Tuple[bool, str]:
    """
    Any city member may deposit materials to a project's construction vault.
    Deposits are capped at the construction requirement for the next target level.
    Deposits are rejected while the project is actively under construction.
    """
    if quantity <= 0:
        return False, "Quantity must be positive."
    if project_type not in CITY_PROJECT_TYPES:
        return False, f"Unknown project type '{project_type}'."
    if not _is_city_member(player_id, city_id):
        return False, "You must be a city member to deposit resources."

    db = get_db()
    try:
        # Check if project is under construction / upgrading
        inst = db.query(CityProjectInstance).filter(
            CityProjectInstance.city_id == city_id,
            CityProjectInstance.project_type == project_type,
            CityProjectInstance.status != STATUS_DECONSTRUCTED,
        ).first()
        if inst and inst.status in (STATUS_CONSTRUCTING, STATUS_UPGRADING):
            return False, "Cannot deposit while the project is under construction."

        current_level = inst.level if inst else 0
        target_level = current_level + 1
        if target_level > MAX_PROJECT_LEVEL:
            return False, "This project is already at maximum level."

        required = get_construction_requirements(project_type, target_level)
        if item_type not in required:
            defn = CITY_PROJECT_TYPES[project_type]
            return False, (f"{item_type} is not a required material for "
                           f"{defn['name']} level {target_level}.")

        max_qty = required[item_type]
        vault_row = _get_vault_row(db, city_id, project_type, item_type)
        space = max(0.0, max_qty - vault_row.quantity)
        if space <= 0:
            return False, f"The vault already holds the maximum {max_qty:,.0f} {item_type}."

        deposit_qty = min(quantity, space)

        from inventory import get_player_inventory, remove_item
        inv = get_player_inventory(player_id)
        if inv.get(item_type, 0) < deposit_qty:
            return False, f"You only have {inv.get(item_type, 0):,.2f} {item_type}."

        remove_item(player_id, item_type, deposit_qty)
        vault_row.quantity += deposit_qty
        vault_row.last_updated = datetime.utcnow()
        db.commit()

        msg = f"Deposited {deposit_qty:,.2f} {item_type} to the {CITY_PROJECT_TYPES[project_type]['name']} vault."
        if deposit_qty < quantity:
            msg += f" (Vault capped; {quantity - deposit_qty:,.2f} not deposited.)"
        return True, msg
    except Exception as e:
        db.rollback()
        return False, f"Deposit failed: {e}"
    finally:
        db.close()


def withdraw_from_project_vault(player_id: int, city_id: int,
                                 project_type: str, item_type: str,
                                 quantity: float) -> Tuple[bool, str]:
    """Only the mayor may withdraw materials from a project vault."""
    if not _is_city_mayor(player_id, city_id):
        return False, "Only the mayor can withdraw from a project vault."
    if quantity <= 0:
        return False, "Quantity must be positive."

    db = get_db()
    try:
        row = _get_vault_row(db, city_id, project_type, item_type)
        if row.quantity < quantity:
            return False, f"Vault only holds {row.quantity:,.2f} {item_type}."

        from inventory import add_item
        add_item(player_id, item_type, quantity)
        row.quantity -= quantity
        row.last_updated = datetime.utcnow()
        db.commit()
        return True, f"Withdrew {quantity:,.2f} {item_type} from vault."
    except Exception as e:
        db.rollback()
        return False, f"Withdrawal failed: {e}"
    finally:
        db.close()


# ──────────────────────────────────────────────────────────────
# PROJECT MANAGEMENT
# ──────────────────────────────────────────────────────────────

def start_project(player_id: int, city_id: int, project_type: str) -> Tuple[Optional[dict], str]:
    """
    Start constructing a new project (level 0 → 1). Any city member can trigger this
    once the vault is fully loaded and the city has sufficient licenses.
    """
    if not _is_city_member(player_id, city_id):
        return None, "You must be a city member to start a project."
    if project_type not in CITY_PROJECT_TYPES:
        return None, f"Unknown project type '{project_type}'."

    # All projects (except the post office) require the post office to be built first
    if project_type != POST_OFFICE_KEY and not _has_post_office(city_id):
        return None, ("The City Post Office must be constructed before any other project. "
                      "Build the Post Office first to unlock municipal licenses.")

    db = get_db()
    try:
        active_count = db.query(CityProjectInstance).filter(
            CityProjectInstance.city_id == city_id,
            CityProjectInstance.status != STATUS_DECONSTRUCTED,
        ).count()
        if active_count >= MAX_PROJECTS_PER_CITY:
            return None, f"City has reached the maximum of {MAX_PROJECTS_PER_CITY} projects."

        if db.query(CityProjectInstance).filter(
            CityProjectInstance.city_id == city_id,
            CityProjectInstance.status == STATUS_CONSTRUCTING,
        ).count() >= 1:
            return None, "A new project is already under construction. Wait for it to complete."

        if db.query(CityProjectInstance).filter(
            CityProjectInstance.city_id == city_id,
            CityProjectInstance.project_type == project_type,
            CityProjectInstance.status != STATUS_DECONSTRUCTED,
        ).first():
            return None, f"This city already has a {CITY_PROJECT_TYPES[project_type]['name']}."

        defn = CITY_PROJECT_TYPES[project_type]
        required = get_construction_requirements(project_type, 1)
        licenses_needed = defn.get("licenses_per_level", 0)

        # Check vault has all required materials
        vault = {r.item_type: r.quantity for r in db.query(CityProjectVault).filter(
            CityProjectVault.city_id == city_id,
            CityProjectVault.project_type == project_type,
        ).all()}
        shortage = [
            f"{item}: need {qty:,.0f}, have {vault.get(item, 0):,.0f}"
            for item, qty in required.items()
            if vault.get(item, 0) < qty
        ]
        if shortage:
            return None, "Vault is not fully loaded:\n" + "\n".join(shortage)

        # Check city licenses
        lic_held = _get_city_licenses(db, city_id)
        if lic_held < licenses_needed:
            return None, (f"City needs {licenses_needed:,.0f} licenses but only has "
                          f"{lic_held:,.0f}. The Post Office generates more licenses each tick.")

        # Deduct materials and licenses
        if not _deduct_from_project_vault(db, city_id, project_type, required):
            return None, "Vault deduction failed — check vault contents."
        if not _deduct_city_licenses(db, city_id, licenses_needed):
            return None, "License deduction failed."

        ticks = _construction_ticks(1)
        # Apply construction speed buff from active city projects
        try:
            cs_mult = get_city_production_buffs(player_id).get("construction_speed_mult", 1.0)
            ticks = max(60, int(ticks * cs_mult))
        except Exception:
            pass
        inst = CityProjectInstance(
            city_id=city_id, project_type=project_type,
            level=0, target_level=1, status=STATUS_CONSTRUCTING,
            construction_ticks_required=ticks, construction_ticks_completed=0,
            construction_started_at=datetime.utcnow(), started_by=player_id,
        )
        db.add(inst)
        db.commit()
        db.refresh(inst)
        return {"id": inst.id, "name": defn["name"], "status": inst.status, "ticks": ticks}, \
               f"Construction of {defn['name']} (Level 1) has begun!"
    except Exception as e:
        db.rollback()
        return None, f"Construction failed: {e}"
    finally:
        db.close()


def start_upgrade(player_id: int, city_id: int, instance_id: int) -> Tuple[bool, str]:
    """Start upgrading an active project to the next level. Any city member can trigger."""
    if not _is_city_member(player_id, city_id):
        return False, "You must be a city member to upgrade a project."

    db = get_db()
    try:
        inst = db.query(CityProjectInstance).filter(
            CityProjectInstance.id == instance_id,
            CityProjectInstance.city_id == city_id,
        ).first()
        if not inst:
            return False, "Project not found."
        if inst.status not in (STATUS_ACTIVE, STATUS_PAUSED):
            return False, "Only active or paused projects can be upgraded."
        if inst.level >= MAX_PROJECT_LEVEL:
            return False, f"Already at maximum level {MAX_PROJECT_LEVEL}."

        if db.query(CityProjectInstance).filter(
            CityProjectInstance.city_id == city_id,
            CityProjectInstance.status == STATUS_UPGRADING,
        ).count() >= 2:
            return False, "Already 2 upgrades in progress. Wait for one to finish."

        target = inst.level + 1
        defn = CITY_PROJECT_TYPES.get(inst.project_type, {})
        required = get_construction_requirements(inst.project_type, target)
        licenses_needed = defn.get("licenses_per_level", 0)

        # Check vault
        vault = {r.item_type: r.quantity for r in db.query(CityProjectVault).filter(
            CityProjectVault.city_id == city_id,
            CityProjectVault.project_type == inst.project_type,
        ).all()}
        shortage = [
            f"{item}: need {qty:,.0f}, have {vault.get(item, 0):,.0f}"
            for item, qty in required.items()
            if vault.get(item, 0) < qty
        ]
        if shortage:
            return False, "Vault not fully loaded for this level:\n" + "\n".join(shortage)

        lic_held = _get_city_licenses(db, city_id)
        if lic_held < licenses_needed:
            return False, (f"City needs {licenses_needed:,.0f} licenses for this upgrade "
                           f"but only has {lic_held:,.0f}.")

        if not _deduct_from_project_vault(db, city_id, inst.project_type, required):
            return False, "Vault deduction failed."
        if not _deduct_city_licenses(db, city_id, licenses_needed):
            return False, "License deduction failed."

        ticks = _construction_ticks(target)
        # Apply construction speed buff from active city projects
        try:
            cs_mult = get_city_production_buffs(player_id).get("construction_speed_mult", 1.0)
            ticks = max(60, int(ticks * cs_mult))
        except Exception:
            pass
        inst.status = STATUS_UPGRADING
        inst.target_level = target
        inst.construction_ticks_required = ticks
        inst.construction_ticks_completed = 0
        inst.construction_started_at = datetime.utcnow()
        inst.started_by = player_id
        db.commit()
        return True, f"Upgrade of {defn.get('name', inst.project_type)} to Level {target} started!"
    except Exception as e:
        db.rollback()
        return False, f"Upgrade failed: {e}"
    finally:
        db.close()


def pause_project(mayor_id: int, city_id: int, instance_id: int) -> Tuple[bool, str]:
    if not _is_city_mayor(mayor_id, city_id):
        return False, "Only the city mayor can pause projects."
    db = get_db()
    try:
        inst = db.query(CityProjectInstance).filter(
            CityProjectInstance.id == instance_id,
            CityProjectInstance.city_id == city_id,
        ).first()
        if not inst or inst.status != STATUS_ACTIVE:
            return False, "Active project not found."
        inst.status = STATUS_PAUSED
        db.commit()
        name = CITY_PROJECT_TYPES.get(inst.project_type, {}).get("name", inst.project_type)
        return True, f"{name} paused."
    finally:
        db.close()


def resume_project(mayor_id: int, city_id: int, instance_id: int) -> Tuple[bool, str]:
    if not _is_city_mayor(mayor_id, city_id):
        return False, "Only the city mayor can resume projects."
    db = get_db()
    try:
        inst = db.query(CityProjectInstance).filter(
            CityProjectInstance.id == instance_id,
            CityProjectInstance.city_id == city_id,
        ).first()
        if not inst or inst.status != STATUS_PAUSED:
            return False, "Paused project not found."
        inst.status = STATUS_ACTIVE
        db.commit()
        name = CITY_PROJECT_TYPES.get(inst.project_type, {}).get("name", inst.project_type)
        return True, f"{name} resumed."
    finally:
        db.close()


def deconstruct_project(mayor_id: int, city_id: int, instance_id: int) -> Tuple[bool, str]:
    """Deconstruct a project. Yields nothing; vault is cleared."""
    if not _is_city_mayor(mayor_id, city_id):
        return False, "Only the city mayor can deconstruct projects."
    db = get_db()
    try:
        inst = db.query(CityProjectInstance).filter(
            CityProjectInstance.id == instance_id,
            CityProjectInstance.city_id == city_id,
        ).first()
        if not inst or inst.status == STATUS_DECONSTRUCTED:
            return False, "Project not found or already deconstructed."
        project_type = inst.project_type
        inst.status = STATUS_DECONSTRUCTED
        _clear_project_vault(db, city_id, project_type)
        db.commit()
        name = CITY_PROJECT_TYPES.get(project_type, {}).get("name", project_type)
        return True, f"{name} has been deconstructed. All vault materials were lost."
    except Exception as e:
        db.rollback()
        return False, f"Deconstruction failed: {e}"
    finally:
        db.close()


# ──────────────────────────────────────────────────────────────
# TICK
# ──────────────────────────────────────────────────────────────

async def tick(current_tick: int, now: datetime):
    db = get_db()
    try:
        # ── 1. Advance construction / upgrade ticks ────────────
        building = db.query(CityProjectInstance).filter(
            CityProjectInstance.status.in_([STATUS_CONSTRUCTING, STATUS_UPGRADING])
        ).all()
        completed_ids = []
        for inst in building:
            inst.construction_ticks_completed += 1
            if inst.construction_ticks_completed >= inst.construction_ticks_required:
                inst.level = inst.target_level
                inst.status = STATUS_ACTIVE
                completed_ids.append((inst.id, inst.city_id, inst.project_type))
                defn = CITY_PROJECT_TYPES.get(inst.project_type, {})
                print(f"[CityProjects] {defn.get('name', inst.project_type)} "
                      f"(city {inst.city_id}) → Level {inst.level} COMPLETE")
        db.commit()

        # Clear vaults for newly completed projects
        for _id, city_id, project_type in completed_ids:
            _clear_project_vault(db, city_id, project_type)
        if completed_ids:
            db.commit()

        # ── 2. Increment active ticks counter ─────────────────
        db.query(CityProjectInstance).filter(
            CityProjectInstance.status == STATUS_ACTIVE
        ).update({"total_ticks_active": CityProjectInstance.total_ticks_active + 1},
                 synchronize_session=False)
        db.commit()

        # ── 3. Post Office — license generation ───────────────
        try:
            from cities import CityBank, get_db as city_get_db

            post_offices = db.query(CityProjectInstance).filter(
                CityProjectInstance.project_type == POST_OFFICE_KEY,
                CityProjectInstance.status == STATUS_ACTIVE,
                CityProjectInstance.level > 0,
            ).all()

            city_halls = db.query(CityProjectInstance).filter(
                CityProjectInstance.project_type == "city_hall",
                CityProjectInstance.status == STATUS_ACTIVE,
                CityProjectInstance.level > 0,
            ).all()
            city_hall_by_city: Dict[int, int] = {i.city_id: i.level for i in city_halls}

            libraries = db.query(CityProjectInstance).filter(
                CityProjectInstance.project_type == "city_library",
                CityProjectInstance.status == STATUS_ACTIVE,
                CityProjectInstance.level > 0,
            ).all()
            library_by_city: Dict[int, int] = {i.city_id: i.level for i in libraries}

            schools = db.query(CityProjectInstance).filter(
                CityProjectInstance.project_type == "public_schools",
                CityProjectInstance.status == STATUS_ACTIVE,
                CityProjectInstance.level > 0,
            ).all()
            schools_by_city: Dict[int, int] = {i.city_id: i.level for i in schools}

            arts = db.query(CityProjectInstance).filter(
                CityProjectInstance.project_type == "cultural_arts_center",
                CityProjectInstance.status == STATUS_ACTIVE,
                CityProjectInstance.level > 0,
            ).all()
            arts_by_city: Dict[int, int] = {i.city_id: i.level for i in arts}

            zoning = db.query(CityProjectInstance).filter(
                CityProjectInstance.project_type == "zoning_office",
                CityProjectInstance.status == STATUS_ACTIVE,
                CityProjectInstance.level > 0,
            ).all()
            zoning_by_city: Dict[int, int] = {i.city_id: i.level for i in zoning}

            if post_offices:
                city_db = city_get_db()
                try:
                    for inst in post_offices:
                        cid = inst.city_id
                        # Base license production from post office
                        base_lic = LICENSES_PER_TICK_BASE * inst.level
                        # Bonus from other projects' license_production buff
                        lic_bonus = (
                            CITY_PROJECT_TYPES["city_hall"]["buffs"].get("license_production", 0)
                            * city_hall_by_city.get(cid, 0)
                            + CITY_PROJECT_TYPES["city_library"]["buffs"].get("license_production", 0)
                            * library_by_city.get(cid, 0)
                            + CITY_PROJECT_TYPES["public_schools"]["buffs"].get("license_production", 0)
                            * schools_by_city.get(cid, 0)
                            + CITY_PROJECT_TYPES["cultural_arts_center"]["buffs"].get("license_production", 0)
                            * arts_by_city.get(cid, 0)
                            + CITY_PROJECT_TYPES["zoning_office"]["buffs"].get("license_production", 0)
                            * zoning_by_city.get(cid, 0)
                        )
                        total_lic = base_lic + lic_bonus
                        bank = city_db.query(CityBank).filter(CityBank.city_id == cid).first()
                        if bank:
                            current = getattr(bank, "city_licenses", 0.0) or 0.0
                            bank.city_licenses = current + total_lic
                    city_db.commit()
                finally:
                    city_db.close()
        except Exception as e:
            print(f"[CityProjects] License tick error: {e}")

        # ── 4. City Extractor — currency mining ───────────────
        try:
            from cities import CityBank, get_db as city_get_db

            extractors = db.query(CityProjectInstance).filter(
                CityProjectInstance.project_type == EXTRACTOR_KEY,
                CityProjectInstance.status == STATUS_ACTIVE,
                CityProjectInstance.level > 0,
            ).all()
            if extractors:
                city_db = city_get_db()
                try:
                    for inst in extractors:
                        bank = city_db.query(CityBank).filter(
                            CityBank.city_id == inst.city_id).first()
                        if bank:
                            bank.currency_quantity = (bank.currency_quantity or 0.0) + \
                                                     EXTRACTOR_CURRENCY_BASE * inst.level
                    city_db.commit()
                finally:
                    city_db.close()
        except Exception as e:
            print(f"[CityProjects] Extractor tick error: {e}")

        # ── 5. Comptroller — bond investment ──────────────────
        try:
            from cities import CityBank, get_db as city_get_db

            comptrollers = db.query(CityProjectInstance).filter(
                CityProjectInstance.project_type == COMPTROLLER_KEY,
                CityProjectInstance.status == STATUS_ACTIVE,
                CityProjectInstance.level > 0,
            ).all()
            if comptrollers:
                city_db = city_get_db()
                try:
                    for inst in comptrollers:
                        bank = city_db.query(CityBank).filter(
                            CityBank.city_id == inst.city_id).first()
                        if bank and bank.cash_reserves > 0:
                            # Bond investment scales with comptroller level
                            rate = COMPTROLLER_INVEST_RATE * inst.level
                            returns = bank.cash_reserves * rate
                            bank.cash_reserves += returns

                            # Level 12: mint stable coins backed by reserves
                            if inst.level >= MAX_PROJECT_LEVEL and bank.cash_reserves > 0:
                                from cities import City, get_db as _cities_get_db
                                _cdb = _cities_get_db()
                                try:
                                    city_row = _cdb.query(City).filter(City.id == inst.city_id).first()
                                    ctype = (city_row.currency_type or "CITY") if city_row else "CITY"
                                finally:
                                    _cdb.close()
                                symbol = ("x" + ctype.upper()[:5]).rstrip("_")
                                minted = bank.cash_reserves * 0.0001  # 0.01% per tick
                                bank.stable_coin_supply = (bank.stable_coin_supply or 0.0) + minted
                                if not bank.stable_coin_symbol:
                                    bank.stable_coin_symbol = symbol
                    city_db.commit()
                finally:
                    city_db.close()
        except Exception as e:
            print(f"[CityProjects] Comptroller tick error: {e}")

    except Exception as e:
        print(f"[CityProjects] Tick error: {e}")
        try:
            db.rollback()
        except Exception:
            pass
    finally:
        db.close()


# ──────────────────────────────────────────────────────────────
# MODULE LIFECYCLE
# ──────────────────────────────────────────────────────────────

def initialize():
    print("[CityProjects] Creating database tables...")
    Base.metadata.create_all(bind=engine)

    # city_project_instances may pre-date some columns; ensure they exist.
    # city_banks.city_licenses is owned by cities.py — do NOT touch it here.
    run_ddl_migration(engine, [
        "ALTER TABLE city_project_instances ADD COLUMN IF NOT EXISTS total_ticks_active INTEGER DEFAULT 0",
        "ALTER TABLE city_project_instances ADD COLUMN IF NOT EXISTS target_level INTEGER DEFAULT 1",
        "ALTER TABLE city_project_instances ADD COLUMN IF NOT EXISTS construction_started_at TIMESTAMP",
        "ALTER TABLE city_project_instances ADD COLUMN IF NOT EXISTS started_by INTEGER",
        # Comptroller level-12 stable coin
        "ALTER TABLE city_banks ADD COLUMN IF NOT EXISTS stable_coin_supply FLOAT DEFAULT 0.0",
        "ALTER TABLE city_banks ADD COLUMN IF NOT EXISTS stable_coin_symbol VARCHAR(16)",
    ])

    count = len(CITY_PROJECT_TYPES)
    print(f"[CityProjects] {count} project types available ({len(SPECIAL_KEYS)} special).")
