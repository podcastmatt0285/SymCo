"""
city_projects.py — Municipal Mega Projects for Wadsworth city governments.

48 project types, max 12 levels each (levels 8-12 exponentially expensive).
Projects consume commodities from the city vault and provide production buffs.
One special project (city_mint) produces city currency deposited in the city bank.

Construction rules:
  - Max 1 new project under construction at a time
  - Max 2 upgrades simultaneously (even while a new one is building)
  - Any city member can start construction or an upgrade
  - Only the mayor can pause/resume/deconstruct/downgrade
  - Deconstruction yields nothing
  - Max 12 active projects per city
"""

import json
from collections import defaultdict
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple

from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime, Text, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from database import engine, SessionLocal

Base = declarative_base()


def get_db():
    return SessionLocal()

# ──────────────────────────────────────────────────────────────
# CONSTANTS
# ──────────────────────────────────────────────────────────────
MAX_PROJECTS_PER_CITY = 12
MAX_PROJECT_LEVEL = 12
HIGH_LEVEL_THRESHOLD = 7   # levels 8-12 use extra cost multiplier

STATUS_CONSTRUCTING  = "constructing"
STATUS_UPGRADING     = "upgrading"
STATUS_ACTIVE        = "active"
STATUS_PAUSED        = "paused"
STATUS_DECONSTRUCTED = "deconstructed"


# ──────────────────────────────────────────────────────────────
# 48 PROJECT DEFINITIONS
# ──────────────────────────────────────────────────────────────
# buffs/debuffs scale linearly with level. Keys:
#   output        — adds to output multiplier per level (0.01 = +1%/lv)
#   wage_savings  — reduces wage fraction per level
#   input_savings — reduces input qty fraction per level
#   wage_penalty  — increases wage fraction per level (debuff)
#   input_penalty — increases input qty fraction per level (debuff)
# currency_per_tick: City Mint only — units of city currency produced per level per tick
# base_project_value: USD contribution to City NAV per level

CITY_PROJECT_TYPES: Dict[str, Dict[str, Any]] = {

    # ── ENERGY (6) ──────────────────────────────────────────
    "municipal_power_grid": {
        "name": "Municipal Power Grid", "category": "energy", "is_special": False,
        "description": "City-wide electrical infrastructure boosting output and cutting industrial wage overhead.",
        "construction_materials": {"iron": 800, "copper": 400, "coal": 300, "energy": 2000},
        "operational_consumption": {"water": 8, "copper": 1},
        "buffs":   {"output": 0.012, "wage_savings": 0.004},
        "debuffs": {"wage_penalty": 0.002},
        "currency_per_tick": 0.0, "base_project_value": 250_000,
    },
    "water_treatment_campus": {
        "name": "Water Treatment Campus", "category": "energy", "is_special": False,
        "description": "Industrial-scale water purification reducing input costs for all production.",
        "construction_materials": {"iron": 600, "copper": 200, "sand": 400, "lumber": 500},
        "operational_consumption": {"energy": 5, "iron": 1},
        "buffs":   {"output": 0.015, "input_savings": 0.003},
        "debuffs": {"input_penalty": 0.002},
        "currency_per_tick": 0.0, "base_project_value": 200_000,
    },
    "natural_gas_pipeline": {
        "name": "Natural Gas Pipeline", "category": "energy", "is_special": False,
        "description": "Regional gas distribution network providing cheap industrial fuel.",
        "construction_materials": {"iron": 1200, "copper": 300, "rubber": 200, "coal": 100},
        "operational_consumption": {"energy": 3, "iron": 1},
        "buffs":   {"wage_savings": 0.006, "input_savings": 0.004},
        "debuffs": {"input_penalty": 0.001},
        "currency_per_tick": 0.0, "base_project_value": 300_000,
    },
    "renewable_energy_park": {
        "name": "Renewable Energy Park", "category": "energy", "is_special": False,
        "description": "Vast solar and wind installation eliminating energy overhead for member businesses.",
        "construction_materials": {"glass": 600, "copper": 500, "iron": 400, "rubber": 300},
        "operational_consumption": {"copper": 1},
        "buffs":   {"wage_savings": 0.008, "output": 0.008},
        "debuffs": {"input_penalty": 0.002},
        "currency_per_tick": 0.0, "base_project_value": 350_000,
    },
    "nuclear_power_plant": {
        "name": "Nuclear Power Plant", "category": "energy", "is_special": False,
        "description": "Massive baseload power generation providing near-unlimited cheap energy.",
        "construction_materials": {"iron": 2000, "copper": 800, "lead": 600, "glass": 400, "coal": 500},
        "operational_consumption": {"water": 20, "lead": 2},
        "buffs":   {"wage_savings": 0.012, "output": 0.018},
        "debuffs": {"input_penalty": 0.003, "wage_penalty": 0.002},
        "currency_per_tick": 0.0, "base_project_value": 800_000,
    },
    "district_heating_network": {
        "name": "District Heating Network", "category": "energy", "is_special": False,
        "description": "Citywide thermal distribution reducing heating costs for all member operations.",
        "construction_materials": {"iron": 700, "copper": 300, "lumber": 400},
        "operational_consumption": {"energy": 4, "water": 5},
        "buffs":   {"wage_savings": 0.005, "input_savings": 0.003},
        "debuffs": {"wage_penalty": 0.001},
        "currency_per_tick": 0.0, "base_project_value": 180_000,
    },

    # ── TRANSPORTATION (6) ───────────────────────────────────
    "international_airport": {
        "name": "International Airport", "category": "transportation", "is_special": False,
        "description": "Full-service cargo hub connecting the city to global trade routes.",
        "construction_materials": {"iron": 1500, "glass": 800, "lumber": 600, "copper": 400, "rubber": 300},
        "operational_consumption": {"energy": 15, "rubber": 2},
        "buffs":   {"output": 0.018, "wage_savings": 0.003},
        "debuffs": {"wage_penalty": 0.003},
        "currency_per_tick": 0.0, "base_project_value": 600_000,
    },
    "deep_water_port": {
        "name": "Deep-Water Port", "category": "transportation", "is_special": False,
        "description": "Industrial marine terminal enabling bulk commodity imports at reduced cost.",
        "construction_materials": {"iron": 1800, "lumber": 1000, "copper": 300, "rubber": 400},
        "operational_consumption": {"energy": 10, "iron": 2},
        "buffs":   {"input_savings": 0.010, "output": 0.008},
        "debuffs": {"wage_penalty": 0.002},
        "currency_per_tick": 0.0, "base_project_value": 500_000,
    },
    "rail_network_hub": {
        "name": "Rail Network Hub", "category": "transportation", "is_special": False,
        "description": "Heavy freight rail terminus routing commodities efficiently across the region.",
        "construction_materials": {"iron": 2000, "lumber": 800, "copper": 500, "coal": 200},
        "operational_consumption": {"energy": 8, "iron": 1},
        "buffs":   {"input_savings": 0.008, "wage_savings": 0.004},
        "debuffs": {"input_penalty": 0.001},
        "currency_per_tick": 0.0, "base_project_value": 450_000,
    },
    "highway_interchange": {
        "name": "Highway Interchange", "category": "transportation", "is_special": False,
        "description": "Major overland logistics hub accelerating goods movement and production throughput.",
        "construction_materials": {"iron": 1000, "lumber": 700, "rubber": 300, "coal": 150},
        "operational_consumption": {"energy": 5},
        "buffs":   {"output": 0.010, "input_savings": 0.005},
        "debuffs": {"wage_penalty": 0.001},
        "currency_per_tick": 0.0, "base_project_value": 300_000,
    },
    "urban_metro_system": {
        "name": "Urban Metro System", "category": "transportation", "is_special": False,
        "description": "Underground transit network reducing worker commute times and cutting labour costs.",
        "construction_materials": {"iron": 2500, "copper": 700, "glass": 400, "rubber": 500, "lumber": 600},
        "operational_consumption": {"energy": 12, "copper": 2},
        "buffs":   {"wage_savings": 0.010, "output": 0.006},
        "debuffs": {"input_penalty": 0.001},
        "currency_per_tick": 0.0, "base_project_value": 700_000,
    },
    "cargo_dispatch_center": {
        "name": "Cargo Dispatch Center", "category": "transportation", "is_special": False,
        "description": "Automated logistics command centre coordinating city-wide supply chains.",
        "construction_materials": {"iron": 800, "copper": 400, "glass": 300, "lumber": 400},
        "operational_consumption": {"energy": 6, "copper": 1},
        "buffs":   {"output": 0.012, "input_savings": 0.004},
        "debuffs": {"wage_penalty": 0.002},
        "currency_per_tick": 0.0, "base_project_value": 250_000,
    },

    # ── INDUSTRY (6) ─────────────────────────────────────────
    "heavy_industrial_zone": {
        "name": "Heavy Industrial Zone", "category": "industry", "is_special": False,
        "description": "Concentrated manufacturing district with shared infrastructure for all member production.",
        "construction_materials": {"iron": 1500, "lumber": 800, "coal": 400, "rubber": 200},
        "operational_consumption": {"energy": 10, "water": 8, "coal": 2},
        "buffs":   {"output": 0.015, "wage_savings": 0.003},
        "debuffs": {"input_penalty": 0.003, "wage_penalty": 0.001},
        "currency_per_tick": 0.0, "base_project_value": 400_000,
    },
    "steel_foundry_complex": {
        "name": "Steel Foundry Complex", "category": "industry", "is_special": False,
        "description": "Mega-scale iron smelting and processing campus cutting metal input costs citywide.",
        "construction_materials": {"iron": 3000, "coal": 1000, "copper": 400, "lumber": 500},
        "operational_consumption": {"energy": 15, "water": 10, "coal": 4, "iron_ore": 5},
        "buffs":   {"input_savings": 0.012, "output": 0.010},
        "debuffs": {"wage_penalty": 0.002, "input_penalty": 0.004},
        "currency_per_tick": 0.0, "base_project_value": 600_000,
    },
    "chemical_processing_plant": {
        "name": "Chemical Processing Plant", "category": "industry", "is_special": False,
        "description": "Industrial chemistry facility producing feedstocks that lower input costs across sectors.",
        "construction_materials": {"iron": 1000, "copper": 600, "rubber": 400, "lead": 300},
        "operational_consumption": {"energy": 8, "water": 12, "oil": 3},
        "buffs":   {"input_savings": 0.010, "output": 0.008},
        "debuffs": {"input_penalty": 0.002, "wage_penalty": 0.002},
        "currency_per_tick": 0.0, "base_project_value": 400_000,
    },
    "oil_refinery": {
        "name": "Oil Refinery", "category": "industry", "is_special": False,
        "description": "Petroleum processing complex producing fuel and feedstocks at scale.",
        "construction_materials": {"iron": 2000, "copper": 500, "rubber": 600, "lead": 200},
        "operational_consumption": {"oil": 8, "water": 6, "energy": 10},
        "buffs":   {"input_savings": 0.008, "wage_savings": 0.006},
        "debuffs": {"input_penalty": 0.002},
        "currency_per_tick": 0.0, "base_project_value": 550_000,
    },
    "lumber_processing_complex": {
        "name": "Lumber Processing Complex", "category": "industry", "is_special": False,
        "description": "Industrial timber processing campus keeping wood input costs low for all member businesses.",
        "construction_materials": {"iron": 800, "timber": 1500, "copper": 300, "rubber": 200},
        "operational_consumption": {"energy": 6, "timber": 5, "water": 4},
        "buffs":   {"input_savings": 0.008, "output": 0.010},
        "debuffs": {"wage_penalty": 0.001},
        "currency_per_tick": 0.0, "base_project_value": 220_000,
    },
    "copper_smelting_plant": {
        "name": "Copper Smelting Plant", "category": "industry", "is_special": False,
        "description": "High-capacity copper extraction hub reducing metal and wire input costs.",
        "construction_materials": {"iron": 1200, "copper_ore": 800, "coal": 500, "rubber": 200},
        "operational_consumption": {"energy": 10, "copper_ore": 6, "water": 5},
        "buffs":   {"input_savings": 0.009, "output": 0.009},
        "debuffs": {"wage_penalty": 0.002},
        "currency_per_tick": 0.0, "base_project_value": 380_000,
    },

    # ── AGRICULTURE (6) ──────────────────────────────────────
    "agricultural_research_institute": {
        "name": "Agricultural Research Institute", "category": "agriculture", "is_special": False,
        "description": "State-of-the-art crop science campus improving yields across all agricultural operations.",
        "construction_materials": {"iron": 500, "glass": 400, "lumber": 800, "copper": 200},
        "operational_consumption": {"energy": 4, "water": 10, "paper": 3},
        "buffs":   {"output": 0.014, "input_savings": 0.004},
        "debuffs": {"input_penalty": 0.002},
        "currency_per_tick": 0.0, "base_project_value": 200_000,
    },
    "food_processing_megafacility": {
        "name": "Food Processing Megafacility", "category": "agriculture", "is_special": False,
        "description": "Industrial food production campus streamlining the entire agricultural supply chain.",
        "construction_materials": {"iron": 1000, "glass": 600, "copper": 400, "rubber": 300},
        "operational_consumption": {"energy": 8, "water": 15},
        "buffs":   {"output": 0.016, "input_savings": 0.006},
        "debuffs": {"input_penalty": 0.003},
        "currency_per_tick": 0.0, "base_project_value": 350_000,
    },
    "vertical_farm_complex": {
        "name": "Vertical Farm Complex", "category": "agriculture", "is_special": False,
        "description": "Multi-storey controlled-environment agriculture producing crops year-round.",
        "construction_materials": {"iron": 800, "glass": 1000, "copper": 500, "rubber": 200},
        "operational_consumption": {"energy": 15, "water": 20},
        "buffs":   {"output": 0.020, "input_savings": 0.003},
        "debuffs": {"input_penalty": 0.008},
        "currency_per_tick": 0.0, "base_project_value": 400_000,
    },
    "grain_storage_network": {
        "name": "Grain Storage Network", "category": "agriculture", "is_special": False,
        "description": "City-wide climate-controlled silos eliminating food spoilage and stabilising supply.",
        "construction_materials": {"iron": 700, "lumber": 1200, "copper": 200, "rubber": 150},
        "operational_consumption": {"energy": 4},
        "buffs":   {"input_savings": 0.012, "wage_savings": 0.002},
        "debuffs": {"wage_penalty": 0.001},
        "currency_per_tick": 0.0, "base_project_value": 200_000,
    },
    "livestock_integration_hub": {
        "name": "Livestock Integration Hub", "category": "agriculture", "is_special": False,
        "description": "Centralised animal husbandry facility boosting all animal product operations.",
        "construction_materials": {"iron": 600, "lumber": 1000, "copper": 200, "rubber": 150},
        "operational_consumption": {"water": 12, "energy": 4},
        "buffs":   {"output": 0.014, "input_savings": 0.003},
        "debuffs": {"input_penalty": 0.003},
        "currency_per_tick": 0.0, "base_project_value": 220_000,
    },
    "fishery_aquaculture_district": {
        "name": "Fishery and Aquaculture District", "category": "agriculture", "is_special": False,
        "description": "Marine research and industrial fish-farming complex supplying seafood inputs at scale.",
        "construction_materials": {"iron": 700, "copper": 300, "lumber": 600, "rubber": 400},
        "operational_consumption": {"water": 20, "energy": 5},
        "buffs":   {"output": 0.016, "input_savings": 0.004},
        "debuffs": {"input_penalty": 0.002},
        "currency_per_tick": 0.0, "base_project_value": 240_000,
    },

    # ── FINANCE (6) ──────────────────────────────────────────
    "stock_exchange_tower": {
        "name": "Stock Exchange Tower", "category": "finance", "is_special": False,
        "description": "Prestigious financial landmark boosting price confidence for all city-produced goods.",
        "construction_materials": {"iron": 1200, "glass": 900, "copper": 500, "lumber": 400},
        "operational_consumption": {"energy": 8, "paper": 4},
        "buffs":   {"output": 0.008, "wage_savings": 0.003},
        "debuffs": {"wage_penalty": 0.003},
        "currency_per_tick": 0.0, "base_project_value": 500_000,
    },
    "trade_finance_district": {
        "name": "Trade Finance District", "category": "finance", "is_special": False,
        "description": "Financial services hub providing cheap credit that reduces effective input costs.",
        "construction_materials": {"iron": 800, "glass": 600, "lumber": 400},
        "operational_consumption": {"energy": 6, "paper": 3},
        "buffs":   {"input_savings": 0.009, "wage_savings": 0.003},
        "debuffs": {"wage_penalty": 0.001},
        "currency_per_tick": 0.0, "base_project_value": 350_000,
    },
    "free_trade_zone": {
        "name": "Free Trade Zone", "category": "finance", "is_special": False,
        "description": "Deregulated trading enclave eliminating friction for member commodity transactions.",
        "construction_materials": {"iron": 600, "glass": 500, "lumber": 500, "copper": 200},
        "operational_consumption": {"energy": 5, "paper": 2},
        "buffs":   {"output": 0.010, "input_savings": 0.006},
        "debuffs": {"input_penalty": 0.003},
        "currency_per_tick": 0.0, "base_project_value": 300_000,
    },
    "commodity_futures_exchange": {
        "name": "Commodity Futures Exchange", "category": "finance", "is_special": False,
        "description": "Derivatives trading floor allowing city members to hedge input costs.",
        "construction_materials": {"iron": 700, "glass": 600, "copper": 300, "lumber": 300},
        "operational_consumption": {"energy": 7, "paper": 4},
        "buffs":   {"input_savings": 0.007, "output": 0.006},
        "debuffs": {"wage_penalty": 0.002},
        "currency_per_tick": 0.0, "base_project_value": 320_000,
    },
    "investment_banking_complex": {
        "name": "Investment Banking Complex", "category": "finance", "is_special": False,
        "description": "Capital markets hub raising the prestige and prices of city-produced goods.",
        "construction_materials": {"iron": 1000, "glass": 800, "lumber": 400},
        "operational_consumption": {"energy": 8, "paper": 5},
        "buffs":   {"output": 0.012, "wage_savings": 0.002},
        "debuffs": {"wage_penalty": 0.004},
        "currency_per_tick": 0.0, "base_project_value": 450_000,
    },
    "insurance_risk_hub": {
        "name": "Insurance & Risk Hub", "category": "finance", "is_special": False,
        "description": "Citywide risk-pooling institution reducing effective labour cost overhead.",
        "construction_materials": {"iron": 600, "glass": 500, "lumber": 400},
        "operational_consumption": {"energy": 5, "paper": 3},
        "buffs":   {"wage_savings": 0.006, "input_savings": 0.003},
        "debuffs": {"input_penalty": 0.001},
        "currency_per_tick": 0.0, "base_project_value": 250_000,
    },

    # ── EDUCATION (6) ────────────────────────────────────────
    "university_campus": {
        "name": "University Campus", "category": "education", "is_special": False,
        "description": "Full research university supplying a highly-educated workforce and cutting wage costs.",
        "construction_materials": {"iron": 700, "glass": 600, "lumber": 1000, "copper": 300},
        "operational_consumption": {"energy": 6, "water": 4, "paper": 8},
        "buffs":   {"wage_savings": 0.010, "output": 0.006},
        "debuffs": {"input_penalty": 0.002},
        "currency_per_tick": 0.0, "base_project_value": 350_000,
    },
    "research_development_institute": {
        "name": "Research & Development Institute", "category": "education", "is_special": False,
        "description": "Applied science campus driving continuous process improvements in all member production.",
        "construction_materials": {"iron": 600, "glass": 500, "copper": 400, "lumber": 400},
        "operational_consumption": {"energy": 8, "paper": 6, "water": 3},
        "buffs":   {"output": 0.012, "input_savings": 0.005},
        "debuffs": {"wage_penalty": 0.003},
        "currency_per_tick": 0.0, "base_project_value": 300_000,
    },
    "technology_incubator": {
        "name": "Technology Incubator", "category": "education", "is_special": False,
        "description": "High-tech startup hub fostering innovation that boosts precision output.",
        "construction_materials": {"iron": 500, "glass": 600, "copper": 500, "lumber": 300},
        "operational_consumption": {"energy": 7, "paper": 4},
        "buffs":   {"output": 0.014, "input_savings": 0.003},
        "debuffs": {"wage_penalty": 0.002},
        "currency_per_tick": 0.0, "base_project_value": 280_000,
    },
    "patent_office": {
        "name": "Patent Office & IP Registry", "category": "education", "is_special": False,
        "description": "Intellectual property protection giving city-produced specialised goods a market premium.",
        "construction_materials": {"iron": 400, "glass": 400, "lumber": 500, "copper": 150},
        "operational_consumption": {"energy": 4, "paper": 5},
        "buffs":   {"output": 0.008, "wage_savings": 0.002},
        "debuffs": {"wage_penalty": 0.001},
        "currency_per_tick": 0.0, "base_project_value": 180_000,
    },
    "national_library": {
        "name": "National Library & Archive", "category": "education", "is_special": False,
        "description": "Vast public knowledge repository providing free training resources that reduce wage costs.",
        "construction_materials": {"iron": 400, "glass": 400, "lumber": 800, "copper": 100},
        "operational_consumption": {"energy": 3, "paper": 6},
        "buffs":   {"wage_savings": 0.005, "output": 0.004},
        "debuffs": {"input_penalty": 0.001},
        "currency_per_tick": 0.0, "base_project_value": 150_000,
    },
    "vocational_training_center": {
        "name": "Vocational Training Centre", "category": "education", "is_special": False,
        "description": "Trade school producing skilled labour that reduces wages and improves production efficiency.",
        "construction_materials": {"iron": 500, "glass": 400, "lumber": 700, "copper": 200},
        "operational_consumption": {"energy": 4, "paper": 4, "water": 2},
        "buffs":   {"wage_savings": 0.008, "output": 0.005},
        "debuffs": {"input_penalty": 0.001},
        "currency_per_tick": 0.0, "base_project_value": 180_000,
    },

    # ── HEALTHCARE (6) ───────────────────────────────────────
    "regional_medical_center": {
        "name": "Regional Medical Center", "category": "healthcare", "is_special": False,
        "description": "Full-service hospital keeping the workforce healthy and reducing wage overhead.",
        "construction_materials": {"iron": 900, "glass": 700, "copper": 400, "lumber": 500},
        "operational_consumption": {"energy": 8, "water": 10},
        "buffs":   {"wage_savings": 0.007, "output": 0.005},
        "debuffs": {"input_penalty": 0.003},
        "currency_per_tick": 0.0, "base_project_value": 320_000,
    },
    "biotech_research_hospital": {
        "name": "Biotech Research Hospital", "category": "healthcare", "is_special": False,
        "description": "Cutting-edge medical research complex advancing pharmaceutical capabilities citywide.",
        "construction_materials": {"iron": 1000, "glass": 800, "copper": 500, "rubber": 300},
        "operational_consumption": {"energy": 10, "water": 8, "oil": 2},
        "buffs":   {"output": 0.018, "input_savings": 0.004},
        "debuffs": {"wage_penalty": 0.004},
        "currency_per_tick": 0.0, "base_project_value": 450_000,
    },
    "pharmaceutical_research_hub": {
        "name": "Pharmaceutical Research Hub", "category": "healthcare", "is_special": False,
        "description": "Drug development campus producing breakthroughs that lower medicine production costs.",
        "construction_materials": {"iron": 800, "glass": 700, "copper": 500, "rubber": 400},
        "operational_consumption": {"energy": 9, "water": 6, "oil": 3},
        "buffs":   {"output": 0.020, "input_savings": 0.008},
        "debuffs": {"wage_penalty": 0.005, "input_penalty": 0.002},
        "currency_per_tick": 0.0, "base_project_value": 400_000,
    },
    "emergency_services_network": {
        "name": "Emergency Services Network", "category": "healthcare", "is_special": False,
        "description": "Integrated response grid ensuring uninterrupted production operations city-wide.",
        "construction_materials": {"iron": 600, "copper": 400, "glass": 300, "lumber": 400},
        "operational_consumption": {"energy": 6, "water": 5},
        "buffs":   {"output": 0.006, "wage_savings": 0.004},
        "debuffs": {"wage_penalty": 0.002},
        "currency_per_tick": 0.0, "base_project_value": 220_000,
    },
    "public_health_department": {
        "name": "Public Health Department", "category": "healthcare", "is_special": False,
        "description": "City-run sanitation and preventive health bureau cutting sick-day production disruptions.",
        "construction_materials": {"iron": 500, "glass": 400, "lumber": 400, "copper": 150},
        "operational_consumption": {"energy": 4, "water": 8},
        "buffs":   {"wage_savings": 0.006, "output": 0.003},
        "debuffs": {"input_penalty": 0.001},
        "currency_per_tick": 0.0, "base_project_value": 180_000,
    },
    "rehabilitation_recovery_campus": {
        "name": "Rehabilitation & Recovery Campus", "category": "healthcare", "is_special": False,
        "description": "Worker recovery facility improving long-term output consistency and reducing turnover.",
        "construction_materials": {"iron": 500, "glass": 400, "lumber": 600, "copper": 200},
        "operational_consumption": {"energy": 5, "water": 6},
        "buffs":   {"wage_savings": 0.004, "output": 0.005},
        "debuffs": {"input_penalty": 0.002},
        "currency_per_tick": 0.0, "base_project_value": 180_000,
    },

    # ── CIVIC & SPECIAL (6) ──────────────────────────────────
    "city_mint": {
        "name": "City Mint", "category": "civic", "is_special": True,
        "description": (
            "★ SPECIAL — Official city currency press producing city currency every tick "
            "and depositing it directly into the city bank. "
            "Also grants a market confidence premium to all city-produced goods."
        ),
        "construction_materials": {"iron": 1500, "copper": 800, "lead": 500, "glass": 400},
        "operational_consumption": {"energy": 10, "lead": 2, "paper": 5},
        "buffs":   {"output": 0.005, "wage_savings": 0.002},
        "debuffs": {"wage_penalty": 0.002},
        "currency_per_tick": 2.0,   # units of city currency per level per tick
        "base_project_value": 750_000,
    },
    "cultural_arts_district": {
        "name": "Cultural Arts District", "category": "civic", "is_special": False,
        "description": "City prestige booster raising sale prices through civic pride and cultural tourism.",
        "construction_materials": {"iron": 600, "glass": 600, "lumber": 800, "copper": 300},
        "operational_consumption": {"energy": 6, "water": 4, "paper": 3},
        "buffs":   {"output": 0.010, "wage_savings": 0.004},
        "debuffs": {"input_penalty": 0.002},
        "currency_per_tick": 0.0, "base_project_value": 280_000,
    },
    "tourism_convention_center": {
        "name": "Tourism & Convention Center", "category": "civic", "is_special": False,
        "description": "World-class events venue drawing external trade and driving up member retail prices.",
        "construction_materials": {"iron": 800, "glass": 700, "lumber": 900, "copper": 300},
        "operational_consumption": {"energy": 8, "water": 6},
        "buffs":   {"output": 0.014, "wage_savings": 0.002},
        "debuffs": {"wage_penalty": 0.003},
        "currency_per_tick": 0.0, "base_project_value": 320_000,
    },
    "media_broadcasting_complex": {
        "name": "Media Broadcasting Complex", "category": "civic", "is_special": False,
        "description": "Regional media hub whose advertising reach boosts market prices for all city goods.",
        "construction_materials": {"iron": 700, "glass": 600, "copper": 500, "lumber": 300},
        "operational_consumption": {"energy": 10, "copper": 1, "paper": 3},
        "buffs":   {"output": 0.010, "input_savings": 0.003},
        "debuffs": {"input_penalty": 0.002},
        "currency_per_tick": 0.0, "base_project_value": 300_000,
    },
    "defense_security_hq": {
        "name": "Defense & Security HQ", "category": "civic", "is_special": False,
        "description": "Fortified operations command protecting member businesses and boosting secure output.",
        "construction_materials": {"iron": 1200, "copper": 500, "glass": 400, "rubber": 300},
        "operational_consumption": {"energy": 8, "iron": 2},
        "buffs":   {"output": 0.007, "wage_savings": 0.003},
        "debuffs": {"wage_penalty": 0.005},
        "currency_per_tick": 0.0, "base_project_value": 350_000,
    },
    "environmental_protection_agency": {
        "name": "Environmental Protection Agency", "category": "civic", "is_special": False,
        "description": "City environmental authority whose efficiency mandates cut water and energy consumption.",
        "construction_materials": {"iron": 500, "glass": 400, "lumber": 500, "copper": 200},
        "operational_consumption": {"energy": 4, "water": 5},
        "buffs":   {"input_savings": 0.008, "wage_savings": 0.003},
        "debuffs": {"wage_penalty": 0.002},
        "currency_per_tick": 0.0, "base_project_value": 220_000,
    },
}


# ──────────────────────────────────────────────────────────────
# MODELS
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
    construction_ticks_required = Column(Integer, default=720)
    construction_ticks_completed = Column(Integer, default=0)
    construction_started_at = Column(DateTime, nullable=True)
    started_by = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    total_ticks_active = Column(Integer, default=0)


class CityResourceVault(Base):
    """City-level commodity stockpile shared by all projects."""
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
    if level <= HIGH_LEVEL_THRESHOLD:
        return base_qty * level
    return base_qty * level * (level - HIGH_LEVEL_THRESHOLD)


def _construction_ticks(level: int) -> int:
    if level <= 4:
        return 720
    if level <= 7:
        return 2160
    return 4320 * (level - 7)


def _get_vault_row(db, city_id: int, item_type: str) -> CityResourceVault:
    row = db.query(CityResourceVault).filter(
        CityResourceVault.city_id == city_id,
        CityResourceVault.item_type == item_type
    ).first()
    if not row:
        row = CityResourceVault(city_id=city_id, item_type=item_type, quantity=0.0)
        db.add(row)
        db.flush()
    return row


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


def _deduct_from_vault(db, city_id: int, materials: Dict[str, float]) -> bool:
    rows = {}
    for item_type, qty in materials.items():
        if qty <= 0:
            continue
        row = _get_vault_row(db, city_id, item_type)
        if row.quantity < qty:
            return False
        rows[item_type] = (row, qty)
    for item_type, (row, qty) in rows.items():
        row.quantity -= qty
        row.last_updated = datetime.utcnow()
    return True


# ──────────────────────────────────────────────────────────────
# QUERY API
# ──────────────────────────────────────────────────────────────

def get_city_vault(city_id: int) -> Dict[str, float]:
    db = get_db()
    try:
        rows = db.query(CityResourceVault).filter(
            CityResourceVault.city_id == city_id,
            CityResourceVault.quantity > 0
        ).all()
        return {r.item_type: r.quantity for r in rows}
    finally:
        db.close()


def get_city_projects(city_id: int) -> List[dict]:
    db = get_db()
    try:
        instances = db.query(CityProjectInstance).filter(
            CityProjectInstance.city_id == city_id,
            CityProjectInstance.status != STATUS_DECONSTRUCTED
        ).all()
        result = []
        for inst in instances:
            defn = CITY_PROJECT_TYPES.get(inst.project_type, {})
            ticks_req = inst.construction_ticks_required or 1
            result.append({
                "id": inst.id,
                "project_type": inst.project_type,
                "name": defn.get("name", inst.project_type),
                "description": defn.get("description", ""),
                "category": defn.get("category", ""),
                "is_special": defn.get("is_special", False),
                "level": inst.level,
                "target_level": inst.target_level,
                "status": inst.status,
                "ticks_required": ticks_req,
                "ticks_done": inst.construction_ticks_completed,
                "progress_pct": round(100 * min(inst.construction_ticks_completed, ticks_req) / ticks_req, 1),
                "buffs": defn.get("buffs", {}),
                "debuffs": defn.get("debuffs", {}),
                "currency_per_tick": defn.get("currency_per_tick", 0.0),
                "is_special": defn.get("is_special", False),
            })
        return result
    finally:
        db.close()


def get_construction_requirements(project_type: str, target_level: int) -> Dict[str, float]:
    defn = CITY_PROJECT_TYPES.get(project_type)
    if not defn:
        return {}
    return {item: _construction_qty(qty, target_level)
            for item, qty in defn.get("construction_materials", {}).items()}


def get_city_production_buffs(player_id: int) -> Dict[str, float]:
    """
    Return combined production multipliers for a player based on their city's
    active projects.

    Returns dict with:
      output_multiplier  (>= 1.0)  — multiply all production output quantities
      wage_multiplier    (>= 0.1)  — multiply all wage costs
      input_multiplier   (>= 0.1)  — multiply all input quantities
    """
    city_id = _get_player_city_id(player_id)
    if not city_id:
        return {"output_multiplier": 1.0, "wage_multiplier": 1.0, "input_multiplier": 1.0}

    db = get_db()
    try:
        instances = db.query(CityProjectInstance).filter(
            CityProjectInstance.city_id == city_id,
            CityProjectInstance.status == STATUS_ACTIVE,
            CityProjectInstance.level > 0
        ).all()

        total_output = 0.0
        total_wage_save = 0.0
        total_input_save = 0.0
        total_wage_pen = 0.0
        total_input_pen = 0.0

        for inst in instances:
            defn = CITY_PROJECT_TYPES.get(inst.project_type, {})
            b = defn.get("buffs", {})
            d = defn.get("debuffs", {})
            lv = inst.level
            total_output     += b.get("output",       0.0) * lv
            total_wage_save  += b.get("wage_savings",  0.0) * lv
            total_input_save += b.get("input_savings", 0.0) * lv
            total_wage_pen   += d.get("wage_penalty",  0.0) * lv
            total_input_pen  += d.get("input_penalty", 0.0) * lv

        return {
            "output_multiplier": max(0.5, 1.0 + total_output),
            "wage_multiplier":   max(0.1, 1.0 - (total_wage_save - total_wage_pen)),
            "input_multiplier":  max(0.1, 1.0 - (total_input_save - total_input_pen)),
        }
    finally:
        db.close()


def get_city_currency_production(city_id: int) -> float:
    db = get_db()
    try:
        instances = db.query(CityProjectInstance).filter(
            CityProjectInstance.city_id == city_id,
            CityProjectInstance.status == STATUS_ACTIVE,
            CityProjectInstance.level > 0
        ).all()
        total = 0.0
        for inst in instances:
            defn = CITY_PROJECT_TYPES.get(inst.project_type, {})
            cpt = defn.get("currency_per_tick", 0.0)
            if cpt > 0:
                total += cpt * inst.level
        return total
    finally:
        db.close()


def get_city_project_value(city_id: int) -> float:
    db = get_db()
    try:
        instances = db.query(CityProjectInstance).filter(
            CityProjectInstance.city_id == city_id,
            CityProjectInstance.status.in_([STATUS_ACTIVE, STATUS_PAUSED, STATUS_UPGRADING])
        ).all()
        total = 0.0
        for inst in instances:
            defn = CITY_PROJECT_TYPES.get(inst.project_type, {})
            total += defn.get("base_project_value", 0.0) * inst.level
        return total
    finally:
        db.close()


# ──────────────────────────────────────────────────────────────
# VAULT MANAGEMENT
# ──────────────────────────────────────────────────────────────

def deposit_to_vault(player_id: int, city_id: int, item_type: str, quantity: float) -> Tuple[bool, str]:
    if quantity <= 0:
        return False, "Quantity must be positive."
    if not _is_city_member(player_id, city_id):
        return False, "You must be a city member to deposit resources."
    try:
        from inventory import get_player_inventory, remove_item
        inv = get_player_inventory(player_id)
        if inv.get(item_type, 0) < quantity:
            return False, f"You don't have {quantity:,.2f} {item_type} in your inventory."
        remove_item(player_id, item_type, quantity)
        db = get_db()
        try:
            row = _get_vault_row(db, city_id, item_type)
            row.quantity += quantity
            row.last_updated = datetime.utcnow()
            db.commit()
        finally:
            db.close()
        return True, f"Deposited {quantity:,.2f} {item_type} to city vault."
    except Exception as e:
        return False, f"Deposit failed: {e}"


def withdraw_from_vault(player_id: int, city_id: int, item_type: str, quantity: float) -> Tuple[bool, str]:
    if not _is_city_mayor(player_id, city_id):
        return False, "Only the mayor can withdraw from the city vault."
    if quantity <= 0:
        return False, "Quantity must be positive."
    try:
        from inventory import add_item
        db = get_db()
        try:
            row = _get_vault_row(db, city_id, item_type)
            if row.quantity < quantity:
                return False, f"Vault only has {row.quantity:,.2f} {item_type}."
            row.quantity -= quantity
            row.last_updated = datetime.utcnow()
            db.commit()
        finally:
            db.close()
        add_item(player_id, item_type, quantity)
        return True, f"Withdrew {quantity:,.2f} {item_type} from city vault."
    except Exception as e:
        return False, f"Withdrawal failed: {e}"


# ──────────────────────────────────────────────────────────────
# CONSTRUCTION & UPGRADES
# ──────────────────────────────────────────────────────────────

def start_project(player_id: int, city_id: int, project_type: str) -> Tuple[Optional[dict], str]:
    """Start constructing a new project (level 0 → 1). Any city member can initiate."""
    if not _is_city_member(player_id, city_id):
        return None, "You must be a city member to start a project."
    if project_type not in CITY_PROJECT_TYPES:
        return None, f"Unknown project type '{project_type}'."

    db = get_db()
    try:
        active_count = db.query(CityProjectInstance).filter(
            CityProjectInstance.city_id == city_id,
            CityProjectInstance.status != STATUS_DECONSTRUCTED
        ).count()
        if active_count >= MAX_PROJECTS_PER_CITY:
            return None, f"City already has the maximum of {MAX_PROJECTS_PER_CITY} projects."

        existing_construction = db.query(CityProjectInstance).filter(
            CityProjectInstance.city_id == city_id,
            CityProjectInstance.status == STATUS_CONSTRUCTING
        ).count()
        if existing_construction >= 1:
            return None, "A new project is already under construction. Wait for it to complete."

        existing = db.query(CityProjectInstance).filter(
            CityProjectInstance.city_id == city_id,
            CityProjectInstance.project_type == project_type,
            CityProjectInstance.status != STATUS_DECONSTRUCTED
        ).first()
        if existing:
            return None, f"This city already has a {CITY_PROJECT_TYPES[project_type]['name']}."

        required = get_construction_requirements(project_type, 1)
        if not _deduct_from_vault(db, city_id, required):
            vault = {r.item_type: r.quantity for r in db.query(CityResourceVault).filter(
                CityResourceVault.city_id == city_id).all()}
            shortage = [f"{item}: need {qty:,.1f}, have {vault.get(item, 0):,.1f}"
                        for item, qty in required.items() if vault.get(item, 0) < qty]
            return None, "Insufficient vault resources:\n" + "\n".join(shortage)

        ticks = _construction_ticks(1)
        inst = CityProjectInstance(
            city_id=city_id, project_type=project_type,
            level=0, target_level=1, status=STATUS_CONSTRUCTING,
            construction_ticks_required=ticks, construction_ticks_completed=0,
            construction_started_at=datetime.utcnow(), started_by=player_id
        )
        db.add(inst)
        db.commit()
        db.refresh(inst)
        defn = CITY_PROJECT_TYPES[project_type]
        return {"id": inst.id, "name": defn["name"], "status": inst.status, "ticks": ticks}, \
               f"Construction of {defn['name']} has begun!"
    except Exception as e:
        db.rollback()
        return None, f"Construction failed: {e}"
    finally:
        db.close()


def start_upgrade(player_id: int, city_id: int, instance_id: int) -> Tuple[bool, str]:
    """Start upgrading an active project to the next level. Any city member can initiate."""
    if not _is_city_member(player_id, city_id):
        return False, "You must be a city member to upgrade a project."

    db = get_db()
    try:
        inst = db.query(CityProjectInstance).filter(
            CityProjectInstance.id == instance_id,
            CityProjectInstance.city_id == city_id
        ).first()
        if not inst:
            return False, "Project not found."
        if inst.status not in (STATUS_ACTIVE, STATUS_PAUSED):
            return False, "Only active or paused projects can be upgraded."
        if inst.level >= MAX_PROJECT_LEVEL:
            return False, f"Already at maximum level {MAX_PROJECT_LEVEL}."

        in_progress = db.query(CityProjectInstance).filter(
            CityProjectInstance.city_id == city_id,
            CityProjectInstance.status == STATUS_UPGRADING
        ).count()
        if in_progress >= 2:
            return False, "Already 2 upgrades in progress. Wait for one to finish."

        target = inst.level + 1
        required = get_construction_requirements(inst.project_type, target)
        if not _deduct_from_vault(db, city_id, required):
            vault = {r.item_type: r.quantity for r in db.query(CityResourceVault).filter(
                CityResourceVault.city_id == city_id).all()}
            shortage = [f"{item}: need {qty:,.1f}, have {vault.get(item, 0):,.1f}"
                        for item, qty in required.items() if vault.get(item, 0) < qty]
            return False, "Insufficient vault resources:\n" + "\n".join(shortage)

        ticks = _construction_ticks(target)
        inst.status = STATUS_UPGRADING
        inst.target_level = target
        inst.construction_ticks_required = ticks
        inst.construction_ticks_completed = 0
        inst.construction_started_at = datetime.utcnow()
        inst.started_by = player_id
        db.commit()
        defn = CITY_PROJECT_TYPES.get(inst.project_type, {})
        return True, f"Upgrade of {defn.get('name', inst.project_type)} to level {target} started."
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
            CityProjectInstance.id == instance_id, CityProjectInstance.city_id == city_id).first()
        if not inst or inst.status != STATUS_ACTIVE:
            return False, "Active project not found."
        inst.status = STATUS_PAUSED
        db.commit()
        return True, f"{CITY_PROJECT_TYPES.get(inst.project_type, {}).get('name', inst.project_type)} paused."
    finally:
        db.close()


def resume_project(mayor_id: int, city_id: int, instance_id: int) -> Tuple[bool, str]:
    if not _is_city_mayor(mayor_id, city_id):
        return False, "Only the city mayor can resume projects."
    db = get_db()
    try:
        inst = db.query(CityProjectInstance).filter(
            CityProjectInstance.id == instance_id, CityProjectInstance.city_id == city_id).first()
        if not inst or inst.status != STATUS_PAUSED:
            return False, "Paused project not found."
        inst.status = STATUS_ACTIVE
        db.commit()
        return True, f"{CITY_PROJECT_TYPES.get(inst.project_type, {}).get('name', inst.project_type)} resumed."
    finally:
        db.close()


def deconstruct_project(mayor_id: int, city_id: int, instance_id: int) -> Tuple[bool, str]:
    if not _is_city_mayor(mayor_id, city_id):
        return False, "Only the city mayor can deconstruct projects."
    db = get_db()
    try:
        inst = db.query(CityProjectInstance).filter(
            CityProjectInstance.id == instance_id, CityProjectInstance.city_id == city_id).first()
        if not inst or inst.status == STATUS_DECONSTRUCTED:
            return False, "Project not found or already deconstructed."
        name = CITY_PROJECT_TYPES.get(inst.project_type, {}).get("name", inst.project_type)
        inst.status = STATUS_DECONSTRUCTED
        db.commit()
        return True, f"{name} deconstructed. No materials returned."
    finally:
        db.close()


def downgrade_project(mayor_id: int, city_id: int, instance_id: int) -> Tuple[bool, str]:
    if not _is_city_mayor(mayor_id, city_id):
        return False, "Only the city mayor can downgrade projects."
    db = get_db()
    try:
        inst = db.query(CityProjectInstance).filter(
            CityProjectInstance.id == instance_id,
            CityProjectInstance.city_id == city_id,
            CityProjectInstance.status.in_([STATUS_ACTIVE, STATUS_PAUSED])
        ).first()
        if not inst:
            return False, "Active or paused project not found."
        name = CITY_PROJECT_TYPES.get(inst.project_type, {}).get("name", inst.project_type)
        inst.level -= 1
        if inst.level <= 0:
            inst.status = STATUS_DECONSTRUCTED
            db.commit()
            return True, f"{name} downgraded to level 0 and deconstructed. No materials returned."
        db.commit()
        return True, f"{name} downgraded to level {inst.level}. No materials returned."
    finally:
        db.close()


# ──────────────────────────────────────────────────────────────
# TICK
# ──────────────────────────────────────────────────────────────

async def tick(current_tick: int, now: datetime):
    db = get_db()
    try:
        # 1. Advance construction / upgrade ticks
        building = db.query(CityProjectInstance).filter(
            CityProjectInstance.status.in_([STATUS_CONSTRUCTING, STATUS_UPGRADING])
        ).all()
        for inst in building:
            inst.construction_ticks_completed += 1
            if inst.construction_ticks_completed >= inst.construction_ticks_required:
                inst.level = inst.target_level
                inst.status = STATUS_ACTIVE
                defn = CITY_PROJECT_TYPES.get(inst.project_type, {})
                print(f"[CityProjects] {defn.get('name', inst.project_type)} "
                      f"(city {inst.city_id}) completed → level {inst.level}")
        db.commit()

        # 2. Operational consumption for active projects
        active = db.query(CityProjectInstance).filter(
            CityProjectInstance.status == STATUS_ACTIVE
        ).all()

        # Evaluate operational consumption per project, not per city.
        # A single resource-starved project pauses only itself — it cannot
        # blackout every other project sharing the same city vault.
        for inst in active:
            defn = CITY_PROJECT_TYPES.get(inst.project_type, {})
            consumption = defn.get("operational_consumption", {})
            if not consumption:
                continue

            # Check all required resources before deducting any.
            can_run = True
            for item_type, qty_per_level in consumption.items():
                total_qty = qty_per_level * inst.level
                if total_qty <= 0:
                    continue
                row = _get_vault_row(db, inst.city_id, item_type)
                if row.quantity < total_qty:
                    can_run = False
                    print(f"[CityProjects] Project {inst.id} (city {inst.city_id}): "
                          f"insufficient {item_type} "
                          f"(need {total_qty:.1f}, have {row.quantity:.1f}) — pausing project")
                    break

            if can_run:
                for item_type, qty_per_level in consumption.items():
                    total_qty = qty_per_level * inst.level
                    if total_qty <= 0:
                        continue
                    row = _get_vault_row(db, inst.city_id, item_type)
                    row.quantity -= total_qty
                    row.last_updated = now
            else:
                inst.status = STATUS_PAUSED

        db.commit()

        # 3. City Mint currency production
        mint_active = db.query(CityProjectInstance).filter(
            CityProjectInstance.project_type == "city_mint",
            CityProjectInstance.status == STATUS_ACTIVE,
            CityProjectInstance.level > 0
        ).all()
        if mint_active:
            try:
                from cities import CityBank, get_db as city_get_db
                city_db = city_get_db()
                try:
                    defn = CITY_PROJECT_TYPES["city_mint"]
                    cpt = defn.get("currency_per_tick", 0.0)
                    for inst in mint_active:
                        if cpt <= 0:
                            continue
                        bank = city_db.query(CityBank).filter(CityBank.city_id == inst.city_id).first()
                        if bank:
                            bank.currency_quantity = (bank.currency_quantity or 0.0) + cpt * inst.level
                    city_db.commit()
                finally:
                    city_db.close()
            except Exception as e:
                print(f"[CityProjects] Mint error: {e}")

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
    count = len(CITY_PROJECT_TYPES)
    print(f"[CityProjects] {count} project types available.")


__all__ = [
    "CITY_PROJECT_TYPES",
    "CityProjectInstance", "CityResourceVault",
    "STATUS_CONSTRUCTING", "STATUS_UPGRADING", "STATUS_ACTIVE", "STATUS_PAUSED", "STATUS_DECONSTRUCTED",
    "MAX_PROJECTS_PER_CITY", "MAX_PROJECT_LEVEL",
    "get_city_vault", "get_city_projects", "get_construction_requirements",
    "get_city_production_buffs", "get_city_currency_production", "get_city_project_value",
    "deposit_to_vault", "withdraw_from_vault",
    "start_project", "start_upgrade",
    "pause_project", "resume_project", "deconstruct_project", "downgrade_project",
    "initialize", "tick",
]
