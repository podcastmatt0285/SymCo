"""
executive.py

Executive management module for the economic simulation.
Handles:
- 23 executive types across 11 categories (land, business, sales, production,
  taxes, banking, crypto, cities, districts, counties, p2p)
- Each executive spawns with 3-5 unique abilities drawn from their job's pool
- Legendary executives receive one extra bonus ability from the legendary pool
- Automatic 7.85% wage raise every time an executive ages up
- Late payment triggers instant quit + full pension AND severance package
- Exec school boosts existing ability performance only — never adds new abilities
- Pension tracked by player who owes it; severance deducted immediately on quit
- Marketplace: fired, retired, and quit-by-nonpayment execs can re-enter workforce
"""

import json
import random
import threading
from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, String, Float, DateTime, Integer, Boolean, Text, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# ==========================
# DATABASE SETUP
# ==========================
from database import engine, SessionLocal
Base = declarative_base()

# ==========================
# CONSTANTS
# ==========================

MAX_EXECUTIVES_PER_PLAYER = 8
TICKS_PER_YEAR   = 1440          # 2 real hours at 5 s/tick
PENSION_DURATION_TICKS = 120     # 10 real minutes  (1 game-month)
WAGE_RAISE_ON_AGEUP  = 0.0785   # 7.85% automatic raise each year
WAGE_RAISE_ON_SCHOOL = 0.15     # 15% raise on school graduation
SPAWN_INTERVAL_TICKS = 180
MAX_MARKETPLACE_SIZE = 20
SPECIAL_CHANCE = 0.05            # 5% chance legendary on normal spawn
SCHOOL_BASE_COST  = 5000.0
SCHOOL_BASE_TICKS = 360          # ~30 min real time

ABILITIES_PER_EXEC_MIN = 3
ABILITIES_PER_EXEC_MAX = 5

PAY_CYCLES = {
    "tick":   1,
    "minute": 12,    # 60 s / 5 s
    "hour":   720,   # 3600 s / 5 s
    "day":    17280  # 86400 s / 5 s
}
PAY_CYCLE_LABELS = {
    "tick":   "per tick",
    "minute": "per minute",
    "hour":   "per hour",
    "day":    "per day"
}

# ==========================
# EXECUTIVE CATEGORIES
# ==========================
EXECUTIVE_CATEGORIES = {
    "land":       {"label": "Land",       "color": "#86efac"},
    "business":   {"label": "Business",   "color": "#c084fc"},
    "sales":      {"label": "Sales",      "color": "#38bdf8"},
    "production": {"label": "Production", "color": "#f59e0b"},
    "taxes":      {"label": "Taxes",      "color": "#fca5a5"},
    "banking":    {"label": "Banking",    "color": "#22c55e"},
    "crypto":     {"label": "Crypto",     "color": "#a78bfa"},
    "cities":     {"label": "Cities",     "color": "#67e8f9"},
    "districts":  {"label": "Districts",  "color": "#fbbf24"},
    "counties":   {"label": "Counties",   "color": "#d9f99d"},
    "p2p":        {"label": "P2P",        "color": "#f9a8d4"},
}

# ==========================
# EXECUTIVE JOBS  (23 types)
# ==========================
EXECUTIVE_JOBS = {
    # ── BUSINESS ──────────────────────────────────────────────────────────────
    "ceo": {
        "title": "Chief Executive Officer", "abbr": "CEO",
        "category": "business",
        "description": "Drives company-wide strategy and lifts the whole executive team",
        "effect": "business",
    },
    "president": {
        "title": "President", "abbr": "PRES",
        "category": "business",
        "description": "Oversees daily operations and corporate governance",
        "effect": "business",
    },
    "chairperson": {
        "title": "Chairperson", "abbr": "CHAIR",
        "category": "business",
        "description": "Leads the board and sets long-term corporate vision",
        "effect": "business",
    },
    "chief_strategy": {
        "title": "Chief Strategy Officer", "abbr": "CSO",
        "category": "business",
        "description": "Develops competitive strategies and market positioning",
        "effect": "business",
    },
    "vp": {
        "title": "Vice President", "abbr": "VP",
        "category": "business",
        "description": "Senior divisional leadership across operations",
        "effect": "business",
    },
    "chro": {
        "title": "Chief Human Resources Officer", "abbr": "CHRO",
        "category": "business",
        "description": "Manages talent acquisition, compensation, and culture",
        "effect": "wages",
    },
    # ── SALES ─────────────────────────────────────────────────────────────────
    "cmo": {
        "title": "Chief Marketing Officer", "abbr": "CMO",
        "category": "sales",
        "description": "Drives brand growth, demand generation, and market expansion",
        "effect": "sales",
    },
    "cxo": {
        "title": "Chief Experience Officer", "abbr": "CXO",
        "category": "sales",
        "description": "Optimises customer journey and end-to-end brand engagement",
        "effect": "sales",
    },
    "cco_content": {
        "title": "Chief Content Officer", "abbr": "CCO",
        "category": "sales",
        "description": "Leads content strategy and digital audience growth",
        "effect": "sales",
    },
    # ── PRODUCTION ────────────────────────────────────────────────────────────
    "coo": {
        "title": "Chief Operating Officer", "abbr": "COO",
        "category": "production",
        "description": "Optimises production cycles and operational efficiency",
        "effect": "production",
    },
    "cpo": {
        "title": "Chief Product Officer", "abbr": "CPO",
        "category": "production",
        "description": "Leads product development and the production roadmap",
        "effect": "production",
    },
    "cio_innovation": {
        "title": "Chief Innovation Officer", "abbr": "CINO",
        "category": "production",
        "description": "Pioneers new production methods and operational breakthroughs",
        "effect": "production",
    },
    "dir_ops": {
        "title": "Director of Operations", "abbr": "DOO",
        "category": "production",
        "description": "Executes operational plans and manages production teams",
        "effect": "production",
    },
    # ── BANKING ───────────────────────────────────────────────────────────────
    "cfo": {
        "title": "Chief Financial Officer", "abbr": "CFO",
        "category": "banking",
        "description": "Maximises financial returns, dividends, and capital efficiency",
        "effect": "banking",
    },
    "cao": {
        "title": "Chief Accounting Officer", "abbr": "CAO",
        "category": "banking",
        "description": "Controls financial reporting, auditing, and accounting accuracy",
        "effect": "banking",
    },
    "cdo_data": {
        "title": "Chief Data Officer", "abbr": "CDO",
        "category": "banking",
        "description": "Monetises data assets and drives data-driven financial decisions",
        "effect": "banking",
    },
    # ── TAXES ─────────────────────────────────────────────────────────────────
    "general_counsel": {
        "title": "General Counsel", "abbr": "GC",
        "category": "taxes",
        "description": "Navigates tax law, legal risk, and compliance obligations",
        "effect": "taxes",
    },
    "cco_compliance": {
        "title": "Chief Compliance Officer", "abbr": "CCO",
        "category": "taxes",
        "description": "Shields the organisation from regulatory fines and tax penalties",
        "effect": "taxes",
    },
    # ── CRYPTO ────────────────────────────────────────────────────────────────
    "cto": {
        "title": "Chief Technology Officer", "abbr": "CTO",
        "category": "crypto",
        "description": "Drives blockchain strategy, DeFi operations, and crypto infrastructure",
        "effect": "crypto",
    },
    "cio": {
        "title": "Chief Information Officer", "abbr": "CIO",
        "category": "crypto",
        "description": "Manages information systems and crypto data infrastructure",
        "effect": "crypto",
    },
    "ciso": {
        "title": "Chief Information Security Officer", "abbr": "CISO",
        "category": "crypto",
        "description": "Protects digital assets, wallets, and secures crypto operations",
        "effect": "crypto",
    },
    "cdo_digital": {
        "title": "Chief Digital Officer", "abbr": "CDO",
        "category": "crypto",
        "description": "Leads digital transformation and crypto-native growth strategy",
        "effect": "crypto",
    },
    # ── LAND ──────────────────────────────────────────────────────────────────
    "vp_land": {
        "title": "VP of Land Development", "abbr": "VPLD",
        "category": "land",
        "description": "Reduces land efficiency decay and optimises the land portfolio",
        "effect": "land",
    },
    "cso": {
        "title": "Chief Sustainability Officer", "abbr": "CSO",
        "category": "land",
        "description": "Drives green initiatives, land sustainability, and environmental compliance",
        "effect": "land",
    },
    # ── CITIES ────────────────────────────────────────────────────────────────
    "vp_cities": {
        "title": "VP of City Affairs", "abbr": "VPCA",
        "category": "cities",
        "description": "Maximises city fund generation, grants, and urban development",
        "effect": "cities",
    },
    # ── DISTRICTS ─────────────────────────────────────────────────────────────
    "vp_districts": {
        "title": "VP of District Operations", "abbr": "VPDO",
        "category": "districts",
        "description": "Boosts district output and lowers district-level taxes",
        "effect": "districts",
    },
    # ── COUNTIES ──────────────────────────────────────────────────────────────
    "vp_counties": {
        "title": "VP of County Relations", "abbr": "VPCR",
        "category": "counties",
        "description": "Negotiates county regulations, grants, and regional development",
        "effect": "counties",
    },
    # ── P2P ───────────────────────────────────────────────────────────────────
    "vp_partnerships": {
        "title": "VP of Partnerships", "abbr": "VPP",
        "category": "p2p",
        "description": "Expands P2P network reach, lowers fees, and manages strategic alliances",
        "effect": "p2p",
    },
    "chief_comms": {
        "title": "Chief Communications Officer", "abbr": "CCO",
        "category": "p2p",
        "description": "Manages DMs, contract notifications, and P2P deal flow. Unlocks push notifications, in-app sounds, and app icon badges.",
        "effect": "p2p",
    },
    # ── SPECIAL: FIRST LADY (tutorial reward) ─────────────────────────────────
    "first_lady": {
        "title": "Former First Lady", "abbr": "FL",
        "category": "business",
        "description": "A legendary figure from American history — free forever, unique buff, levels up to 18",
        "effect": "special",
    },
}

# ==========================
# EXECUTIVE ABILITIES
# ==========================
EXEC_ABILITIES = {
    # ── BUSINESS ──────────────────────────────────────────────────────────────
    # Hookpoints: hire_executive (board_influence, talent_scout), _process_aging (culture_builder)
    # Global multipliers in get_player_job_bonus: corp_synergy, executive_aura, fl_shadow_exec, fl_dar_organizer
    "corp_synergy":        {"name": "Corporate Synergy",       "desc": "All executive bonuses +5% across the board",            "effect": "business", "value": 0.05},
    "talent_scout":        {"name": "Talent Scout",            "desc": "Executives you hire retire 15% later than normal",      "effect": "business", "value": 0.15},
    "board_influence":     {"name": "Board Influence",         "desc": "All executive hiring fees −20%",                        "effect": "business", "value": 0.20},
    "strategic_vision":    {"name": "Strategic Vision",        "desc": "Business production output +8%",                       "effect": "production","value": 0.08},
    "culture_builder":     {"name": "Culture Builder",         "desc": "All executives age 10% slower",                        "effect": "business", "value": 0.10},
    "executive_aura":      {"name": "Executive Aura",          "desc": "All other executive effects +3%",                      "effect": "business", "value": 0.03},
    "hr_mastery":          {"name": "HR Mastery",              "desc": "All executive wages −8%",                              "effect": "wages",    "value": 0.08},
    "retention_bonus":     {"name": "Retention Bonus",         "desc": "Executive school costs −12%",                          "effect": "school",   "value": 0.12},
    "succession_plan":     {"name": "Succession Planning",     "desc": "On this exec's retirement the next hire fee is waived", "effect": "special",  "value": 0.0},
    # ── SALES ─────────────────────────────────────────────────────────────────
    # Hookpoint: business.py retail revenue * (1 + sales_bonus)
    "demand_surge":        {"name": "Demand Surge",            "desc": "Retail/sales revenue +12%",                            "effect": "sales",   "value": 0.12},
    "brand_equity":        {"name": "Brand Equity",            "desc": "Retail/sales revenue +6%",                             "effect": "sales",   "value": 0.06},
    "viral_campaign":      {"name": "Viral Campaign",          "desc": "Retail/sales revenue +10%",                            "effect": "sales",   "value": 0.10},
    "conversion_pro":      {"name": "Conversion Pro",          "desc": "Retail/sales revenue +8%",                             "effect": "sales",   "value": 0.08},
    "loyalty_program":     {"name": "Loyalty Program",         "desc": "Retail/sales revenue +8%",                             "effect": "sales",   "value": 0.08},
    "influencer_network":  {"name": "Influencer Network",      "desc": "City production bonuses +10%",                         "effect": "cities",  "value": 0.10},
    "market_intelligence": {"name": "Market Intelligence",     "desc": "Retail/sales revenue +7%",                             "effect": "sales",   "value": 0.07},
    "upsell_mastery":      {"name": "Upsell Mastery",          "desc": "Retail/sales revenue +10%",                            "effect": "sales",   "value": 0.10},
    # ── PRODUCTION ────────────────────────────────────────────────────────────
    # Hookpoint: wma.py production output qty * (1 + production_bonus)
    "lean_ops":            {"name": "Lean Operations",         "desc": "Business production output +10%",                      "effect": "production", "value": 0.10},
    "supply_chain_opt":    {"name": "Supply Chain Optimization","desc": "Business input costs −8%",                            "effect": "production", "value": 0.08},
    "automation_drive":    {"name": "Automation Drive",        "desc": "Production output +12%",                               "effect": "production", "value": 0.12},
    "quality_control":     {"name": "Quality Control",         "desc": "Production output +10%",                               "effect": "production", "value": 0.10},
    "capacity_expand":     {"name": "Capacity Expansion",      "desc": "Business production output +10%",                      "effect": "production", "value": 0.10},
    "process_reeng":       {"name": "Process Reengineering",   "desc": "Executive school duration −15%",                       "effect": "school",     "value": 0.15},
    "ops_excellence":      {"name": "Operational Excellence",  "desc": "Land purchase prices and hoarding taxes −10%",         "effect": "land",       "value": 0.10},
    "throughput_boost":    {"name": "Throughput Boost",        "desc": "Production output +10%",                               "effect": "production", "value": 0.10},
    # ── BANKING ───────────────────────────────────────────────────────────────
    # Hookpoint: ETF pay_dividends() — dividend_amount * (1 + banking_bonus) per player
    "interest_arb":        {"name": "Interest Arbitrage",      "desc": "Banking/ETF income +15%",                              "effect": "banking", "value": 0.15},
    "dividend_boost":      {"name": "Dividend Booster",        "desc": "ETF dividend returns +12%",                            "effect": "banking", "value": 0.12},
    "capital_reserve":     {"name": "Capital Reserve Protocol","desc": "$5,000 negative balance buffer before penalties",       "effect": "banking", "value": 5000.0},
    "portfolio_hedge":     {"name": "Portfolio Hedge",         "desc": "ETF dividend returns +20%",                            "effect": "banking", "value": 0.20},
    "cost_center_audit":   {"name": "Cost Center Audit",       "desc": "All executive wages −8%",                              "effect": "wages",   "value": 0.08},
    "investment_grade":    {"name": "Investment Grade",        "desc": "Banking/ETF income +15%",                              "effect": "banking", "value": 0.15},
    "debt_restructure":    {"name": "Debt Restructuring",      "desc": "Banking/ETF income +10%",                              "effect": "banking", "value": 0.10},
    "banking_synergy":     {"name": "Banking Synergy",         "desc": "Banking/ETF income +5%",                               "effect": "banking", "value": 0.05},
    # ── TAXES ─────────────────────────────────────────────────────────────────
    # Hookpoint: districts.py monthly tax * (1 - taxes_bonus - districts_bonus)
    "tax_shield":          {"name": "Tax Shield",              "desc": "All taxes −10%",                                       "effect": "taxes",  "value": 0.10},
    "compliance_expert":   {"name": "Compliance Expert",       "desc": "All taxes −10%",                                       "effect": "taxes",  "value": 0.10},
    "loophole_finder":     {"name": "Loophole Finder",         "desc": "All taxes −15%",                                       "effect": "taxes",  "value": 0.15},
    "deduction_master":    {"name": "Deduction Master",        "desc": "All taxes −12%",                                       "effect": "taxes",  "value": 0.12},
    "audit_defense":       {"name": "Audit Defense",           "desc": "All taxes −10%",                                       "effect": "taxes",  "value": 0.10},
    "tax_treaty":          {"name": "Tax Treaty Expertise",    "desc": "All taxes −10%",                                       "effect": "taxes",  "value": 0.10},
    "legal_arb":           {"name": "Legal Arbitrage",         "desc": "All taxes −8%",                                        "effect": "taxes",  "value": 0.08},
    "county_exemption":    {"name": "County Exemption",        "desc": "All taxes −20%",                                       "effect": "taxes",  "value": 0.20},
    # ── CRYPTO ────────────────────────────────────────────────────────────────
    # Hookpoint: wallet.py yield farming + memecoins.py mining payout * (1 + crypto_bonus)
    "blockchain_native":   {"name": "Blockchain Native",       "desc": "WSC yield farming returns +20%",                       "effect": "crypto",  "value": 0.20},
    "defi_specialist":     {"name": "DeFi Specialist",         "desc": "WSC yield farming returns +15%",                       "effect": "crypto",  "value": 0.15},
    "security_hard":       {"name": "Security Hardening",      "desc": "WSC yield farming returns +10%",                       "effect": "crypto",  "value": 0.10},
    "algo_trading":        {"name": "Algorithmic Trading",     "desc": "WSC yield farming returns +5%",                        "effect": "crypto",  "value": 0.05},
    "smart_contract_aud":  {"name": "Smart Contract Auditing", "desc": "Meme coin / WSC yield +20%",                           "effect": "crypto",  "value": 0.20},
    "data_analytics":      {"name": "Data Analytics",          "desc": "Meme coin / WSC yield +8%",                            "effect": "crypto",  "value": 0.08},
    "web3_native":         {"name": "Web3 Native",             "desc": "Meme coin / WSC yield +8%",                            "effect": "crypto",  "value": 0.08},
    "token_strategy":      {"name": "Token Strategy",          "desc": "Meme coin / WSC yield +10%",                           "effect": "crypto",  "value": 0.10},
    # ── LAND ──────────────────────────────────────────────────────────────────
    # Hookpoints: land.py hoarding tax * (1 - land_bonus), land_market.py asking_price * (1 - land_bonus)
    "land_survey_exp":     {"name": "Land Survey Expertise",   "desc": "Land purchase prices and hoarding taxes −20%",         "effect": "land", "value": 0.20},
    "zoning_expert":       {"name": "Zoning Expert",           "desc": "Land purchase prices and hoarding taxes −10%",         "effect": "land", "value": 0.10},
    "green_cert":          {"name": "Green Certification",     "desc": "Land purchase prices and hoarding taxes −15%",         "effect": "land", "value": 0.15},
    "property_dev":        {"name": "Property Development",    "desc": "Land purchase prices and hoarding taxes −8%",          "effect": "land", "value": 0.08},
    "easement_neg":        {"name": "Easement Negotiator",     "desc": "Land hoarding tax −15%",                               "effect": "land", "value": 0.15},
    "urban_planning":      {"name": "Urban Planning",          "desc": "City production bonuses +8%",                          "effect": "cities","value": 0.08},
    "env_compliance":      {"name": "Environmental Compliance","desc": "Land purchase prices and hoarding taxes −25%",          "effect": "land", "value": 0.25},
    "land_banking":        {"name": "Land Banking",            "desc": "Land purchase prices and hoarding taxes −5%",          "effect": "land", "value": 0.05},
    # ── CITIES ────────────────────────────────────────────────────────────────
    # Hookpoint: city_projects.py get_city_production_buffs output_multiplier * (1 + cities_bonus)
    "grant_writer":        {"name": "Grant Writer",            "desc": "City production bonuses +20%",                         "effect": "cities","value": 0.20},
    "infra_push":          {"name": "Infrastructure Push",     "desc": "City production bonuses +15%",                         "effect": "cities","value": 0.15},
    "civic_partner":       {"name": "Civic Partnership",       "desc": "City production bonuses +10%",                         "effect": "cities","value": 0.10},
    "urban_renewal":       {"name": "Urban Renewal",           "desc": "City production bonuses +12%",                         "effect": "cities","value": 0.12},
    "public_relations":    {"name": "Public Relations",        "desc": "City production bonuses +10%",                         "effect": "cities","value": 0.10},
    "mayoral_liaison":     {"name": "Mayoral Liaison",         "desc": "City production bonuses +25%",                         "effect": "cities","value": 0.25},
    "smart_city":          {"name": "Smart City Initiative",   "desc": "City production bonuses +12%",                         "effect": "cities","value": 0.12},
    # ── DISTRICTS ─────────────────────────────────────────────────────────────
    # Hookpoint: districts.py monthly tax * (1 - taxes_bonus - districts_bonus)
    "district_champ":      {"name": "District Champion",       "desc": "District monthly taxes −15%",                          "effect": "districts","value": 0.15},
    "tax_incentive_zone":  {"name": "Tax Incentive Zone",      "desc": "District monthly taxes −20%",                          "effect": "districts","value": 0.20},
    "biz_incubator":       {"name": "Business Incubator",      "desc": "District monthly taxes −10%",                          "effect": "districts","value": 0.10},
    "corridor_dev":        {"name": "Corridor Development",    "desc": "District monthly taxes −5%",                           "effect": "districts","value": 0.05},
    "rezoning_expert":     {"name": "Rezoning Expert",         "desc": "District monthly taxes −15%",                          "effect": "districts","value": 0.15},
    "cluster_effect":      {"name": "Cluster Effect",          "desc": "District monthly taxes −8%",                           "effect": "districts","value": 0.08},
    "local_partnership":   {"name": "Local Partnership",       "desc": "District monthly taxes −15%",                          "effect": "districts","value": 0.15},
    # ── COUNTIES (redirected to real effect types — county-specific systems TBD) ─
    "county_commission":   {"name": "County Commissioner",     "desc": "All taxes −25%",                                       "effect": "taxes",      "value": 0.25},
    "land_grant_prog":     {"name": "Land Grant Program",      "desc": "All taxes −20%",                                       "effect": "taxes",      "value": 0.20},
    "rural_dev":           {"name": "Rural Development",       "desc": "Business production output +12%",                      "effect": "production", "value": 0.12},
    "county_bond":         {"name": "County Bond Access",      "desc": "All executive wages −5%",                              "effect": "wages",      "value": 0.05},
    "annexation_right":    {"name": "Annexation Rights",       "desc": "District monthly taxes −15%",                          "effect": "districts",  "value": 0.15},
    "agri_bonus":          {"name": "Agricultural Bonus",      "desc": "Land purchase prices and hoarding taxes −15%",         "effect": "land",       "value": 0.15},
    "regional_hub":        {"name": "Regional Hub",            "desc": "Business production output +10%",                      "effect": "production", "value": 0.10},
    # ── P2P ───────────────────────────────────────────────────────────────────
    # Hookpoint: p2p.py charge_p2p_access fee * (1 - p2p_bonus)
    # Special UI abilities use effect "special" — checked via player_has_ability(), not get_player_job_bonus()
    "p2p_notification":    {"name": "P2P Notification System", "desc": "Enables DM and contract icons on P2P dashboard button", "effect": "special","value": 1.0},
    "dm_threeway":         {"name": "Multi-Party DMs",         "desc": "Unlocks adding 3rd parties to direct messages",        "effect": "special","value": 1.0},
    "contract_tracker":    {"name": "Contract Tracker",        "desc": "Real-time contract status alerts in dashboard",        "effect": "special","value": 1.0},
    "fee_negotiator":      {"name": "Fee Negotiator",          "desc": "P2P access fee −25%",                                  "effect": "p2p","value": 0.25},
    "network_expander":    {"name": "Network Expander",        "desc": "P2P access fee −15%",                                  "effect": "p2p","value": 0.15},
    "deal_scout":          {"name": "Deal Scout",              "desc": "P2P access fee −15%",                                  "effect": "p2p","value": 0.15},
    "rep_shield":          {"name": "Reputation Shield",       "desc": "P2P access fee −10%",                                  "effect": "p2p","value": 0.10},
    "mediation_svc":       {"name": "Mediation Service",       "desc": "P2P access fee −20%",                                  "effect": "p2p","value": 0.20},
    # ── FIRST LADIES (unique — one per exec, tutorial reward) ─────────────────
    "fl_estate_manager":   {"name": "Estate Management",       "desc": "All farming & plantation output +15%",                 "effect": "production","value": 0.15},
    "fl_political_advisor":{"name": "Political Advisor",       "desc": "Overall business strategy output +10%",               "effect": "production","value": 0.10},
    "fl_social_diplomat":  {"name": "Social Diplomacy",        "desc": "All P2P transaction fees −20%",                        "effect": "p2p","value": 0.20},
    "fl_un_diplomat":      {"name": "UN Diplomacy",            "desc": "Market listing/transaction fees −15%",                 "effect": "sales","value": 0.15},
    "fl_retail_entrepreneur":{"name":"Retail Entrepreneur",    "desc": "Retail sales revenue +12%",                           "effect": "sales","value": 0.12},
    "fl_base_logistics":   {"name": "Base Logistics",          "desc": "All production cycles 12% faster",                    "effect": "production","value": 0.12},
    "fl_photojournalist":  {"name": "Photojournalist",         "desc": "Brand equity and media income +12%",                  "effect": "sales","value": 0.12},
    "fl_broadcaster":      {"name": "Broadcasting Executive",  "desc": "Passive income from all businesses +14%",             "effect": "sales","value": 0.14},
    "fl_retail_teacher":   {"name": "Retail & Teaching",       "desc": "Sales volume and demand multiplier +10%",             "effect": "sales","value": 0.10},
    "fl_performing_artist":{"name": "Performing Artist",       "desc": "All executive wages −12%",                            "effect": "wages","value": 0.12},
    "fl_health_advocate":  {"name": "Health Advocate",         "desc": "All executives age 15% slower",                       "effect": "business","value": 0.15},
    "fl_silver_screen":    {"name": "Silver Screen Star",      "desc": "Business consumer demand +10%",                       "effect": "sales","value": 0.10},
    "fl_literacy_author":  {"name": "Literacy Author",         "desc": "Executive school duration −22%",                      "effect": "school","value": 0.22},
    "fl_secretary_state":  {"name": "Secretary of State",      "desc": "All property and land taxes −14%",                    "effect": "taxes","value": 0.14},
    "fl_librarian":        {"name": "Librarian & Educator",    "desc": "Executive school costs −18%",                         "effect": "school","value": 0.18},
    "fl_corporate_attorney":{"name":"Corporate Attorney",      "desc": "Full compliance/audit immunity + all taxes −8%",      "effect": "taxes","value": 0.08},
    "fl_professor":        {"name": "English Professor",       "desc": "School upgrade effectiveness +25%",                   "effect": "school","value": 0.25},
    # ── ADDITIONAL FIRST LADIES (chronological, missing from original list) ───
    "fl_paris_diplomat":        {"name": "Paris Diplomat",          "desc": "All market listing and transaction fees −15%",         "effect": "sales",      "value": 0.15},
    "fl_court_musician":        {"name": "Court Musician & Poet",   "desc": "Brand equity across all businesses +12%",             "effect": "sales",      "value": 0.12},
    "fl_estate_steward":        {"name": "Estate Steward",          "desc": "Farming and rural land output +12%",                  "effect": "production", "value": 0.12},
    "fl_congressional_lobbyist":{"name": "Congressional Lobbyist",  "desc": "Land purchase prices −15%",                           "effect": "land",       "value": 0.15},
    "fl_exec_secretary":        {"name": "Executive Secretary",     "desc": "All business production 10% more efficient",          "effect": "production", "value": 0.10},
    "fl_frontier_supply":       {"name": "Frontier Supply Officer", "desc": "All business input costs −12%",                       "effect": "production", "value": 0.12},
    "fl_school_librarian":      {"name": "Schoolteacher & Librarian","desc": "Executive school costs −20%",                        "effect": "school",     "value": 0.20},
    "fl_correspondence_mgr":    {"name": "Correspondence Manager",  "desc": "All P2P message and contract fees −18%",              "effect": "p2p",        "value": 0.18},
    "fl_arts_patroness":        {"name": "Arts Patroness",          "desc": "City production bonuses +12%",                        "effect": "cities",     "value": 0.12},
    "fl_fashion_linguist":      {"name": "Fashion & Linguistics",   "desc": "Retail/sales revenue +12%",                          "effect": "sales",      "value": 0.12},
    "fl_reading_teacher":       {"name": "Reading Teacher",         "desc": "Executive school costs and duration −22%",            "effect": "school",     "value": 0.22},
    "fl_social_climber":        {"name": "Social Architect",        "desc": "P2P access fee −18%",                                 "effect": "p2p",        "value": 0.18},
    "fl_temperance_scholar":    {"name": "Temperance Scholar",      "desc": "All executive wages −10%",                            "effect": "wages",      "value": 0.10},
    "fl_classical_scholar":     {"name": "Classical Scholar",       "desc": "Executive school duration −18%",                      "effect": "school",     "value": 0.18},
    "fl_celebrity_endorser":    {"name": "Celebrity Endorser",      "desc": "Retail/sales revenue +15%",                           "effect": "sales",      "value": 0.15},
    "fl_dar_organizer":         {"name": "DAR Organizer",           "desc": "All active executive ability effects +10%",            "effect": "business",   "value": 0.10},
    "fl_bank_president":        {"name": "Bank President",          "desc": "ETF dividend returns +15%",                           "effect": "banking",    "value": 0.15},
    "fl_whitehouse_coo":        {"name": "White House COO",         "desc": "All production output +12%",                          "effect": "production", "value": 0.12},
    "fl_city_diplomat":         {"name": "City Diplomat",           "desc": "City production bonuses +18%",                        "effect": "cities",     "value": 0.18},
    "fl_housing_reformer":      {"name": "Housing Reformer",        "desc": "City production bonuses +15%",                        "effect": "cities",     "value": 0.15},
    "fl_shadow_exec":           {"name": "Shadow Executive",        "desc": "All active executive ability effects +10%",            "effect": "business",   "value": 0.10},
    "fl_press_publisher":       {"name": "Press Publisher",         "desc": "Passive income from all businesses +15%",             "effect": "sales",      "value": 0.15},
    "fl_deaf_educator":         {"name": "School for the Deaf",     "desc": "Executive school duration −25%",                      "effect": "school",     "value": 0.25},
    "fl_mining_geologist":      {"name": "Mining Geologist",        "desc": "Production output +12% and input costs −8%",          "effect": "production", "value": 0.12},
}

# ==========================
# FIRST LADY EXECUTIVES
# Tutorial reward — player chooses one; she starts age 18, retires at 110, max level 18
# ==========================
FIRST_LADY_EXECUTIVES = [
    # ── Founding Era ─────────────────────────────────────────────────────────
    {
        "key":       "martha_washington",
        "name":      "Martha Washington",
        "years":     "1789–1797",
        "real_role": "Plantation & estate manager for Mount Vernon",
        "ability":   "fl_estate_manager",
        "flavor":    "America's first First Lady oversaw one of Virginia's largest working plantations, managing hundreds of workers, crops, and supply chains.",
    },
    {
        "key":       "abigail_adams",
        "name":      "Abigail Adams",
        "years":     "1797–1801",
        "real_role": "Political writer, policy advisor, and farmer",
        "ability":   "fl_political_advisor",
        "flavor":    "One of the most politically astute First Ladies, Abigail Adams actively advised her husband on policy and ran the family farm entirely on her own during the Revolution.",
    },
    {
        "key":       "dolley_madison",
        "name":      "Dolley Madison",
        "years":     "1809–1817",
        "real_role": "Renowned social diplomat and hostess",
        "ability":   "fl_social_diplomat",
        "flavor":    "Dolley Madison redefined the role of First Lady through masterful social diplomacy, forging alliances and easing tensions through relationship-building.",
    },
    {
        "key":       "elizabeth_monroe",
        "name":      "Elizabeth Monroe",
        "years":     "1817–1825",
        "real_role": "French-educated diplomat's wife and Parisian social figure",
        "ability":   "fl_paris_diplomat",
        "flavor":    "Elizabeth Monroe lived in Paris during the Revolution and was fluent in French court customs — her diplomatic polish lowered every barrier she encountered.",
    },
    {
        "key":       "louisa_adams",
        "name":      "Louisa Adams",
        "years":     "1825–1829",
        "real_role": "Musician, poet, playwright, and silkworm farmer",
        "ability":   "fl_court_musician",
        "flavor":    "Born in London and raised across Europe, Louisa Adams was a composer, lyricist, and the only First Lady born outside the US. She raised silkworms to produce her own silk.",
    },
    # ── Antebellum Era ───────────────────────────────────────────────────────
    {
        "key":       "letitia_tyler",
        "name":      "Letitia Tyler",
        "years":     "1841–1842",
        "real_role": "Virginia plantation estate manager",
        "ability":   "fl_estate_steward",
        "flavor":    "Letitia Tyler managed the Tyler family's sprawling Virginia plantation and domestic operations with quiet efficiency — a skilled estate steward before she ever entered the White House.",
    },
    {
        "key":       "julia_tyler",
        "name":      "Julia Tyler",
        "years":     "1844–1845",
        "real_role": "Debutante and congressional lobbyist for Texas annexation",
        "ability":   "fl_congressional_lobbyist",
        "flavor":    "Julia Tyler personally lobbied senators and cultivated political alliances to secure Texas annexation — one of the most effective White House lobbying campaigns of the 19th century.",
    },
    {
        "key":       "sarah_polk",
        "name":      "Sarah Polk",
        "years":     "1845–1849",
        "real_role": "Presidential executive secretary and political strategist",
        "ability":   "fl_exec_secretary",
        "flavor":    "Sarah Polk handled all of President Polk's correspondence, managed his schedule, and co-authored policy documents — she was effectively his chief of staff.",
    },
    {
        "key":       "margaret_taylor",
        "name":      "Margaret Taylor",
        "years":     "1849–1850",
        "real_role": "Army quartermaster's wife and frontier supply manager",
        "ability":   "fl_frontier_supply",
        "flavor":    "Margaret Taylor spent 40 years following General Taylor across the frontier, managing household supply chains in remote postings where every resource had to be accounted for.",
    },
    {
        "key":       "abigail_fillmore",
        "name":      "Abigail Fillmore",
        "years":     "1850–1853",
        "real_role": "Schoolteacher and founder of the White House library",
        "ability":   "fl_school_librarian",
        "flavor":    "Abigail Fillmore was the first First Lady to hold a job after marriage. She founded the White House library and believed deeply that access to knowledge was the great equaliser.",
    },
    {
        "key":       "jane_pierce",
        "name":      "Jane Pierce",
        "years":     "1853–1857",
        "real_role": "Political letter writer and correspondence manager",
        "ability":   "fl_correspondence_mgr",
        "flavor":    "Jane Pierce managed vast personal and political correspondence for her husband throughout his Senate career — her letters were known for precision, clarity, and strategic timing.",
    },
    {
        "key":       "harriet_lane",
        "name":      "Harriet Lane",
        "years":     "1857–1861",
        "real_role": "White House hostess, arts patroness, and Native American advocate",
        "ability":   "fl_arts_patroness",
        "flavor":    "Harriet Lane, niece of bachelor President Buchanan, served as official White House hostess and championed arts funding and Native American welfare — a civic force ahead of her time.",
    },
    {
        "key":       "mary_todd_lincoln",
        "name":      "Mary Todd Lincoln",
        "years":     "1861–1865",
        "real_role": "Educated linguist, political strategist, and fashion consumer",
        "ability":   "fl_fashion_linguist",
        "flavor":    "Mary Todd Lincoln spoke French, understood consumer demand acutely, and used fashion spending as a political statement — she knew how supply, desire, and image move markets.",
    },
    # ── Reconstruction & Gilded Age ───────────────────────────────────────────
    {
        "key":       "eliza_johnson",
        "name":      "Eliza Johnson",
        "years":     "1865–1869",
        "real_role": "Schoolteacher who taught her own husband to read and write",
        "ability":   "fl_reading_teacher",
        "flavor":    "Eliza Johnson personally taught Andrew Johnson literacy skills and basic education from scratch. She believed that with the right instruction, anyone could rise.",
    },
    {
        "key":       "julia_grant",
        "name":      "Julia Grant",
        "years":     "1869–1877",
        "real_role": "Social Washington architect and networking powerhouse",
        "ability":   "fl_social_climber",
        "flavor":    "Julia Grant thrived in Washington society like no First Lady before her, cultivating relationships across party lines and turning the White House into the social hub of a nation.",
    },
    {
        "key":       "lucy_hayes",
        "name":      "Lucy Hayes",
        "years":     "1877–1881",
        "real_role": "First college-educated First Lady and temperance advocate",
        "ability":   "fl_temperance_scholar",
        "flavor":    "Lucy Hayes was the first First Lady with a university degree and ran the White House on strict budget discipline. Her staff loved her — she kept wages fair and waste zero.",
    },
    {
        "key":       "lucretia_garfield",
        "name":      "Lucretia Garfield",
        "years":     "1881",
        "real_role": "Classical scholar, teacher, and languages expert",
        "ability":   "fl_classical_scholar",
        "flavor":    "Lucretia Garfield studied Latin, Greek, and classical literature and taught school before the White House. She believed that learning faster, not harder, was the real advantage.",
    },
    {
        "key":       "frances_cleveland",
        "name":      "Frances Cleveland",
        "years":     "1886–1889, 1893–1897",
        "real_role": "First celebrity endorsement icon in American advertising",
        "ability":   "fl_celebrity_endorser",
        "flavor":    "Frances Cleveland's image was used in ads without consent across the country — soap, thread, and tobacco brands all claimed her endorsement. She was America's first national brand.",
    },
    {
        "key":       "caroline_harrison",
        "name":      "Caroline Harrison",
        "years":     "1889–1892",
        "real_role": "Art teacher, musician, and co-founder of the DAR",
        "ability":   "fl_dar_organizer",
        "flavor":    "Caroline Harrison taught china painting and watercolour, co-founded the Daughters of the American Revolution, and used civic organisation to multiply the impact of every community dollar.",
    },
    # ── Progressive Era ───────────────────────────────────────────────────────
    {
        "key":       "ida_mckinley",
        "name":      "Ida McKinley",
        "years":     "1897–1901",
        "real_role": "Bank cashier and manager before marriage",
        "ability":   "fl_bank_president",
        "flavor":    "Before the White House, Ida McKinley worked as a cashier and bank manager at her father's Canton bank — one of the first women to hold such a role in American finance.",
    },
    {
        "key":       "edith_roosevelt",
        "name":      "Edith Roosevelt",
        "years":     "1901–1909",
        "real_role": "White House chief operating officer and press manager",
        "ability":   "fl_whitehouse_coo",
        "flavor":    "Edith Roosevelt reorganised the entire White House operation, created the executive wing, and established a dedicated press secretary — the first modern COO of the presidency.",
    },
    {
        "key":       "helen_taft",
        "name":      "Helen Taft",
        "years":     "1909–1913",
        "real_role": "Politically astute power broker and city beautification diplomat",
        "ability":   "fl_city_diplomat",
        "flavor":    "Helen Taft was the driving political force behind her husband's presidency and personally arranged the donation of cherry blossoms that transformed Washington DC into a civic landmark.",
    },
    {
        "key":       "ellen_wilson",
        "name":      "Ellen Wilson",
        "years":     "1913–1914",
        "real_role": "Professional artist, art teacher, and housing reform advocate",
        "ability":   "fl_housing_reformer",
        "flavor":    "Ellen Wilson sold paintings at professional exhibitions and used her political position to pass landmark legislation improving alley housing conditions in Washington DC.",
    },
    {
        "key":       "edith_wilson",
        "name":      "Edith Wilson",
        "years":     "1915–1921",
        "real_role": "De facto executive branch manager after president's stroke",
        "ability":   "fl_shadow_exec",
        "flavor":    "After Woodrow Wilson's 1919 stroke, Edith Wilson screened all government communications, decided what reached the president, and effectively ran the executive branch for 17 months.",
    },
    {
        "key":       "florence_harding",
        "name":      "Florence Harding",
        "years":     "1921–1923",
        "real_role": "Newspaper circulation manager and press publisher",
        "ability":   "fl_press_publisher",
        "flavor":    "Florence Harding ran the circulation department of the Marion Daily Star for years, turning a struggling paper into a profitable operation through relentless commercial instinct.",
    },
    {
        "key":       "grace_coolidge",
        "name":      "Grace Coolidge",
        "years":     "1923–1929",
        "real_role": "Teacher at the Clarke School for the Deaf",
        "ability":   "fl_deaf_educator",
        "flavor":    "Grace Coolidge taught lip-reading and speech at the Clarke School for the Deaf for years before the White House. She knew that the fastest learner wins — and she made every session count.",
    },
    {
        "key":       "lou_hoover",
        "name":      "Lou Hoover",
        "years":     "1929–1933",
        "real_role": "Stanford geology graduate, multilingual mining expert",
        "ability":   "fl_mining_geologist",
        "flavor":    "Lou Hoover was the first woman to earn a geology degree from Stanford, co-translated a 16th-century Latin mining treatise into English, and spoke five languages including Mandarin Chinese.",
    },
    # ── Modern Era ────────────────────────────────────────────────────────────
    {
        "key":       "eleanor_roosevelt",
        "name":      "Eleanor Roosevelt",
        "years":     "1933–1945",
        "real_role": "Journalist, UN delegate, and civil rights diplomat",
        "ability":   "fl_un_diplomat",
        "flavor":    "Eleanor Roosevelt was the first US delegate to the UN and wrote a syndicated newspaper column. She negotiated, wrote, and advocated on the world stage.",
    },
    {
        "key":       "bess_truman",
        "name":      "Bess Truman",
        "years":     "1945–1953",
        "real_role": "Co-manager of the family clothing business",
        "ability":   "fl_retail_entrepreneur",
        "flavor":    "Before Washington, Bess helped manage her family's retail clothing operation in Missouri — she knew margins, inventory, and customers firsthand.",
    },
    {
        "key":       "mamie_eisenhower",
        "name":      "Mamie Eisenhower",
        "years":     "1953–1961",
        "real_role": "Military household logistics & base management",
        "ability":   "fl_base_logistics",
        "flavor":    "Having moved 27 times across military postings worldwide, Mamie became an expert at rapid operational setup and efficient household logistics.",
    },
    {
        "key":       "jacqueline_kennedy",
        "name":      "Jacqueline Kennedy",
        "years":     "1961–1963",
        "real_role": "Photojournalist and Inquiring Camera Girl",
        "ability":   "fl_photojournalist",
        "flavor":    "Before the White House, Jackie Kennedy worked as a photojournalist for the Washington Times-Herald, developing a keen eye for brand storytelling.",
    },
    {
        "key":       "lady_bird_johnson",
        "name":      "Lady Bird Johnson",
        "years":     "1963–1969",
        "real_role": "Broadcasting company owner and media executive",
        "ability":   "fl_broadcaster",
        "flavor":    "Lady Bird personally ran LBJ Holding Company, a profitable Texas broadcasting empire, making her one of the few First Ladies who was a genuine media executive.",
    },
    {
        "key":       "pat_nixon",
        "name":      "Pat Nixon",
        "years":     "1969–1974",
        "real_role": "Retail worker, teacher, and stage actress",
        "ability":   "fl_retail_teacher",
        "flavor":    "Pat Nixon worked retail, taught typing and shorthand, and acted on stage — a practical, demand-focused background that gave her deep consumer insight.",
    },
    {
        "key":       "betty_ford",
        "name":      "Betty Ford",
        "years":     "1974–1977",
        "real_role": "Professional dancer and fashion model",
        "ability":   "fl_performing_artist",
        "flavor":    "Betty Ford trained as a dancer under Martha Graham and modeled in New York. She understood the performance economy and made every dollar count.",
    },
    {
        "key":       "rosalynn_carter",
        "name":      "Rosalynn Carter",
        "years":     "1977–1981",
        "real_role": "Mental health advocate and business partner",
        "ability":   "fl_health_advocate",
        "flavor":    "Rosalynn co-managed the Carter family peanut business and devoted her career to mental health reform — her staff always outlasted the competition.",
    },
    {
        "key":       "nancy_reagan",
        "name":      "Nancy Reagan",
        "years":     "1981–1989",
        "real_role": "MGM actress and television star",
        "ability":   "fl_silver_screen",
        "flavor":    "Nancy Reagan appeared in 11 MGM films, understanding how image, audience, and demand drive consumer behaviour at a national scale.",
    },
    {
        "key":       "barbara_bush",
        "name":      "Barbara Bush",
        "years":     "1989–1993",
        "real_role": "Literacy advocate and published author",
        "ability":   "fl_literacy_author",
        "flavor":    "Barbara Bush founded the Barbara Bush Foundation for Family Literacy and authored multiple books. She believed education was the fastest path to any goal.",
    },
    {
        "key":       "hillary_clinton",
        "name":      "Hillary Clinton",
        "years":     "1993–2001",
        "real_role": "Attorney, US Senator, and Secretary of State",
        "ability":   "fl_secretary_state",
        "flavor":    "Hillary Clinton was a practicing attorney before the White House, then a US Senator, then the nation's chief diplomat — she knows how to cut through red tape.",
    },
    {
        "key":       "laura_bush",
        "name":      "Laura Bush",
        "years":     "2001–2009",
        "real_role": "Librarian and public school teacher",
        "ability":   "fl_librarian",
        "flavor":    "Laura Bush worked as a librarian and second-grade teacher in Houston public schools — two careers defined by patience, low budgets, and doing more with less.",
    },
    {
        "key":       "michelle_obama",
        "name":      "Michelle Obama",
        "years":     "2009–2017",
        "real_role": "Corporate attorney and hospital VP of Community Affairs",
        "ability":   "fl_corporate_attorney",
        "flavor":    "Michelle Obama was a partner-track corporate lawyer at Sidley Austin and a VP at University of Chicago Medical Center — the definition of strategic compliance.",
    },
    {
        "key":       "jill_biden",
        "name":      "Jill Biden",
        "years":     "2021–2025",
        "real_role": "English professor and career educator",
        "ability":   "fl_professor",
        "flavor":    "Dr. Jill Biden holds a doctorate in education and continued teaching full-time while serving as First Lady — the first to do so. School, to her, is everything.",
    },
]

# Ability pools per job — execs draw 3-5 at creation
JOB_ABILITY_POOLS = {
    "ceo":            ["corp_synergy","talent_scout","board_influence","strategic_vision","culture_builder","executive_aura","retention_bonus"],
    "president":      ["corp_synergy","board_influence","strategic_vision","culture_builder","executive_aura","retention_bonus","succession_plan"],
    "chairperson":    ["board_influence","corp_synergy","strategic_vision","talent_scout","succession_plan","executive_aura","retention_bonus"],
    "chief_strategy": ["strategic_vision","corp_synergy","board_influence","culture_builder","retention_bonus","executive_aura","talent_scout"],
    "vp":             ["executive_aura","corp_synergy","board_influence","strategic_vision","talent_scout","retention_bonus","hr_mastery"],
    "chro":           ["hr_mastery","culture_builder","talent_scout","retention_bonus","executive_aura","succession_plan","board_influence"],
    "cmo":            ["demand_surge","brand_equity","viral_campaign","conversion_pro","loyalty_program","market_intelligence","upsell_mastery"],
    "cxo":            ["demand_surge","loyalty_program","brand_equity","conversion_pro","market_intelligence","upsell_mastery","viral_campaign"],
    "cco_content":    ["brand_equity","viral_campaign","demand_surge","market_intelligence","loyalty_program","influencer_network","conversion_pro"],
    "coo":            ["lean_ops","supply_chain_opt","automation_drive","quality_control","process_reeng","ops_excellence","throughput_boost"],
    "cpo":            ["automation_drive","quality_control","lean_ops","throughput_boost","capacity_expand","supply_chain_opt","process_reeng"],
    "cio_innovation": ["automation_drive","process_reeng","capacity_expand","lean_ops","throughput_boost","ops_excellence","supply_chain_opt"],
    "dir_ops":        ["lean_ops","ops_excellence","quality_control","supply_chain_opt","throughput_boost","process_reeng","automation_drive"],
    "cfo":            ["interest_arb","dividend_boost","capital_reserve","portfolio_hedge","investment_grade","debt_restructure","banking_synergy"],
    "cao":            ["cost_center_audit","investment_grade","interest_arb","banking_synergy","capital_reserve","debt_restructure","dividend_boost"],
    "cdo_data":       ["data_analytics","portfolio_hedge","investment_grade","banking_synergy","capital_reserve","dividend_boost","interest_arb"],
    "general_counsel":["tax_shield","compliance_expert","loophole_finder","audit_defense","legal_arb","county_exemption","deduction_master"],
    "cco_compliance": ["compliance_expert","audit_defense","tax_shield","deduction_master","tax_treaty","legal_arb","loophole_finder"],
    "cto":            ["blockchain_native","defi_specialist","security_hard","algo_trading","web3_native","token_strategy","data_analytics"],
    "cio":            ["data_analytics","blockchain_native","security_hard","web3_native","algo_trading","token_strategy","defi_specialist"],
    "ciso":           ["security_hard","blockchain_native","smart_contract_aud","data_analytics","web3_native","algo_trading","defi_specialist"],
    "cdo_digital":    ["blockchain_native","web3_native","token_strategy","defi_specialist","data_analytics","algo_trading","smart_contract_aud"],
    "vp_land":        ["land_survey_exp","zoning_expert","property_dev","easement_neg","env_compliance","land_banking","urban_planning"],
    "cso":            ["green_cert","env_compliance","land_survey_exp","urban_planning","land_banking","zoning_expert","easement_neg"],
    "vp_cities":      ["grant_writer","infra_push","civic_partner","urban_renewal","public_relations","mayoral_liaison","smart_city"],
    "vp_districts":   ["district_champ","tax_incentive_zone","biz_incubator","corridor_dev","rezoning_expert","cluster_effect","local_partnership"],
    "vp_counties":    ["county_commission","land_grant_prog","rural_dev","county_bond","annexation_right","agri_bonus","regional_hub"],
    "vp_partnerships":["p2p_notification","fee_negotiator","network_expander","deal_scout","rep_shield","mediation_svc","dm_threeway"],
    "chief_comms":    ["p2p_notification","dm_threeway","contract_tracker","fee_negotiator","network_expander","deal_scout","rep_shield"],
}

# ==========================
# LEGENDARY BONUS ABILITIES
# Extra ability granted ONLY to legendary executives (on top of their 3-5)
# ==========================
LEGENDARY_BONUS_ABILITIES = {
    "double_efficiency": {"name": "Double Efficiency",        "desc": "All this executive's abilities are twice as effective"},
    "half_wages":        {"name": "Half Wages",               "desc": "Works for half the normal wage out of loyalty"},
    "fast_learner":      {"name": "Fast Learner",             "desc": "School upgrades complete in half the normal time"},
    "pension_free":      {"name": "Golden Parachute Refusal", "desc": "Waives all pension and severance rights on exit"},
    "eternal_youth":     {"name": "Eternal Youth",            "desc": "Ages 50% slower than any other executive"},
    "mentor":            {"name": "Mentor",                   "desc": "All other executives gain +1 effective level while employed"},
    "market_maker":      {"name": "Market Maker",             "desc": "Generates $500 passive income per tick"},
    "crisis_manager":    {"name": "Crisis Manager",           "desc": "Grants all co-workers a one-cycle grace period when wages can't be paid — no exec quits on the first missed payment while this exec is employed"},
    "rainmaker":         {"name": "Rainmaker",                "desc": "Randomly triggers bonus income events worth $2,000–$10,000"},
    "polymath":          {"name": "Polymath",                 "desc": "Applies all ability bonuses to every job category, not just this executive's primary specialisation"},
    "iron_will":         {"name": "Iron Will",                "desc": "Never quits due to late payment — issues a formal warning instead"},
}

# Backward-compat alias used by old code
SPECIAL_ABILITIES = LEGENDARY_BONUS_ABILITIES

# ==========================
# SCHOOL UPGRADES
# These boost performance of EXISTING abilities — never add a new ability.
# Universal options available at every school graduation (levels 2–7).
# ==========================
SCHOOL_UPGRADES = {
    "perf_focus": {
        "name": "Performance Focus",
        "description": "Intensive specialisation. All of this executive's existing abilities become 30% more effective. No new abilities granted.",
        "bonus": "perf_boost_30",
        "perf_mult": 1.30,
        "wage_mod": 1.0,
        "team_boost": 0.0,
    },
    "balanced_dev": {
        "name": "Balanced Development",
        "description": "Comprehensive training. All existing abilities +20% effective. The exec negotiates a modest 8% wage reduction in gratitude.",
        "bonus": "perf_boost_20_wage8",
        "perf_mult": 1.20,
        "wage_mod": 0.92,
        "team_boost": 0.0,
    },
    "team_lead": {
        "name": "Team Leadership",
        "description": "Leadership coaching. This exec's abilities +20% effective AND all other executives on your team gain +5% effectiveness.",
        "bonus": "perf_boost_20_team5",
        "perf_mult": 1.20,
        "wage_mod": 1.0,
        "team_boost": 0.05,
    },
}


# ==========================
# DATABASE MODEL
# ==========================
class Executive(Base):
    """Executive employee model."""
    __tablename__ = "executives"

    id          = Column(Integer, primary_key=True, index=True, autoincrement=True)
    first_name  = Column(String, nullable=False)
    last_name   = Column(String, nullable=False)
    player_id   = Column(Integer, nullable=True, index=True)  # null = on marketplace

    # Stats
    level       = Column(Integer, default=1)
    job         = Column(String, nullable=False)
    wage        = Column(Float,  default=100.0)
    pay_cycle   = Column(String, default="hour")

    # Age lifecycle
    current_age    = Column(Integer, default=22)
    retirement_age = Column(Integer, default=65)
    max_age        = Column(Integer, default=85)
    is_retired     = Column(Boolean, default=False)
    is_dead        = Column(Boolean, default=False)

    # School
    is_in_school           = Column(Boolean, default=False)
    school_ticks_remaining = Column(Integer, default=0)
    school_total_ticks     = Column(Integer, default=0)   # for progress bar
    school_cost_remaining  = Column(Float,   default=0.0)
    pending_upgrade        = Column(Boolean, default=False)

    # Pension / Severance
    pension_owed            = Column(Float,   default=0.0)
    pension_ticks_remaining = Column(Integer, default=0)
    pension_owed_by         = Column(Integer, nullable=True)   # player_id who owes it
    severance_owed          = Column(Float,   default=0.0)
    severance_owed_by       = Column(Integer, nullable=True)

    # Legendary
    is_special      = Column(Boolean, default=False)
    special_ability = Column(String,  nullable=True)   # key from LEGENDARY_BONUS_ABILITIES
    special_title   = Column(String,  nullable=True)
    special_flavor  = Column(Text,    nullable=True)

    # First Lady (tutorial reward)
    is_first_lady   = Column(Boolean, default=False)
    max_level       = Column(Integer, default=7)  # 18 for First Ladies

    # Per-exec abilities (3-5 keys from JOB_ABILITY_POOLS, comma-separated)
    abilities = Column(Text, default="")

    # School performance bonuses (comma-separated bonus keys like "perf_boost_30")
    bonuses = Column(Text, default="")

    # Payment tracking
    missed_payments = Column(Integer, default=0)

    # Timestamps
    created_at  = Column(DateTime, default=datetime.utcnow)
    hired_at    = Column(DateTime, nullable=True)
    fired_at    = Column(DateTime, nullable=True)

    # Marketplace
    on_marketplace    = Column(Boolean, default=True)
    marketplace_reason = Column(String, default="new")  # new | fired | retired_available | quit_nonpayment

    # Tick accumulators
    pay_tick_accumulator = Column(Integer, default=0)
    age_tick_accumulator = Column(Integer, default=0)


# ==========================
# LOAD NAME DATA
# ==========================
NAME_DATA: dict = {}

def load_names():
    global NAME_DATA
    try:
        with open("executive_names.json", "r") as f:
            NAME_DATA = json.load(f)
    except FileNotFoundError:
        NAME_DATA = {
            "first_names":    ["Alex","Jordan","Morgan","Casey","Riley"],
            "last_names":     ["Smith","Johnson","Williams","Brown","Jones"],
            "special_titles": ["The Visionary"],
            "special_flavor": ["A truly remarkable individual."]
        }


# ==========================
# CORE HELPERS
# ==========================

def get_db():
    return SessionLocal()


def get_active_executives(db, player_id: int) -> List[Executive]:
    """Return all currently active (employed, alive, not retired) executives."""
    return db.query(Executive).filter(
        Executive.player_id  == player_id,
        Executive.is_dead    == False,
        Executive.is_retired == False,
        Executive.is_in_school == False,
    ).all()


def get_school_performance_multiplier(executive: Executive) -> float:
    """Total performance multiplier from all school sessions."""
    mult = 1.0
    for b in (executive.bonuses or "").split(","):
        if not b:
            continue
        if b == "perf_boost_30":
            mult *= 1.30
        elif "perf_boost_20" in b:
            mult *= 1.20
    return mult


def get_team_performance_boost(db, player_id: int) -> float:
    """Extra multiplier applied to the whole team from 'team_lead' school sessions."""
    execs = db.query(Executive).filter(
        Executive.player_id  == player_id,
        Executive.is_dead    == False,
        Executive.is_retired == False,
    ).all()
    boost = 1.0
    for ex in execs:
        for b in (ex.bonuses or "").split(","):
            if "team5" in b:
                boost *= 1.05
    return boost


def get_player_job_bonus(db, player_id: int, effect: str) -> float:
    """
    Calculate the total bonus percentage (0.0–0.95) contributed by all active
    executives whose abilities match `effect`.

    Handles:  banking | production | sales | land | cities | districts |
              counties | p2p | taxes | crypto | wages | business | school
    Legacy aliases: retail→sales, school→school
    """
    _aliases = {"retail": "sales"}
    effect = _aliases.get(effect, effect)

    executives = db.query(Executive).filter(
        Executive.player_id    == player_id,
        Executive.is_dead      == False,
        Executive.is_retired   == False,
        Executive.is_in_school == False,
    ).all()
    if not executives:
        return 0.0

    mentor_count = sum(
        1 for ex in executives
        if ex.is_special and ex.special_ability == "mentor"
    )

    total = 0.0
    for ex in executives:
        ability_keys = [a for a in (ex.abilities or "").split(",") if a]
        school_mult  = get_school_performance_multiplier(ex)
        level_mult   = 1.0 + 0.02 * (ex.level + mentor_count)

        # Polymath: contributes bonuses across ALL categories, not just their own
        is_polymath = ex.is_special and ex.special_ability == "polymath"

        exec_bonus = 0.0
        for key in ability_keys:
            adef = EXEC_ABILITIES.get(key)
            if not adef:
                continue
            if adef["effect"] != effect and not is_polymath:
                continue
            v = adef["value"]
            if isinstance(v, float) and v <= 1.0:
                exec_bonus += v

        exec_bonus *= level_mult * school_mult

        # Legendary double-efficiency
        if ex.is_special and ex.special_ability == "double_efficiency":
            exec_bonus *= 2.0

        total += exec_bonus

    total *= get_team_performance_boost(db, player_id)

    # Apply global multiplier abilities (corp_synergy, executive_aura, fl_shadow_exec, fl_dar_organizer)
    _global_mult_keys = ("corp_synergy", "executive_aura", "fl_shadow_exec", "fl_dar_organizer")
    for key in _global_mult_keys:
        for ex in executives:
            if key in (ex.abilities or "").split(","):
                adef = EXEC_ABILITIES.get(key)
                if adef:
                    total *= (1.0 + adef["value"])
                break  # one application per ability type

    return min(total, 0.95)


def get_specific_ability_bonus(db, player_id: int, ability_key: str) -> float:
    """Sum the effective value of one specific ability across all active execs."""
    adef = EXEC_ABILITIES.get(ability_key)
    if not adef:
        return 0.0
    execs = get_active_executives(db, player_id)
    total = 0.0
    for ex in execs:
        if ability_key in (ex.abilities or "").split(","):
            school_mult = get_school_performance_multiplier(ex)
            level_mult  = 1.0 + 0.02 * ex.level
            v = adef["value"]
            if isinstance(v, float) and v <= 1.0:
                total += v * school_mult * level_mult
    return min(total, 0.95)


def player_has_ability(db, player_id: int, ability_key: str) -> bool:
    """True if any active executive carries the named ability."""
    execs = get_active_executives(db, player_id)
    for ex in execs:
        if ability_key in (ex.abilities or "").split(","):
            return True
        if ex.is_special and ex.special_ability == ability_key:
            return True
    return False


def player_has_cco(db, player_id: int) -> bool:
    """True if player has p2p_notification from an active exec OR an active FCC licence."""
    if player_has_ability(db, player_id, "p2p_notification"):
        return True
    try:
        from auth import get_db as _adb_fn, Player as _Player
        _adb = _adb_fn()
        p = _adb.query(_Player).filter_by(id=player_id).first()
        expires = getattr(p, "cco_rental_expires", None) if p else None
        _adb.close()
        if expires and expires > datetime.utcnow():
            return True
    except Exception:
        pass
    return False


def get_school_discount(db, player_id: int) -> float:
    """Combined school cost/time discount from all school-effect executive abilities."""
    return min(get_player_job_bonus(db, player_id, "school"), 0.75)


def get_player_executives(db, player_id: int) -> List[Executive]:
    return db.query(Executive).filter(
        Executive.player_id == player_id,
        Executive.is_dead   == False
    ).all()


def get_marketplace_executives(db) -> List[Executive]:
    return db.query(Executive).filter(
        Executive.on_marketplace == True,
        Executive.is_dead        == False
    ).order_by(Executive.is_special.desc(), Executive.level.desc()).all()


# ==========================
# GENERATE / CREATE
# ==========================

def generate_executive(force_special: bool = False) -> dict:
    if not NAME_DATA:
        load_names()

    first_name = random.choice(NAME_DATA["first_names"])
    last_name  = random.choice(NAME_DATA["last_names"])
    _spawnable_jobs = [k for k in EXECUTIVE_JOBS if k != "first_lady"]
    job        = random.choice(_spawnable_jobs)

    current_age = random.randint(18, 50)

    if current_age < 25:
        level = random.choices([1, 2],       weights=[80, 20])[0]
    elif current_age < 35:
        level = random.choices([1, 2, 3],    weights=[30, 50, 20])[0]
    elif current_age < 45:
        level = random.choices([2, 3, 4],    weights=[30, 45, 25])[0]
    else:
        level = random.choices([3, 4, 5],    weights=[35, 40, 25])[0]

    retirement_age = random.randint(55, 75)
    max_age        = retirement_age + random.randint(10, 30)

    pay_cycle = random.choices(
        ["tick","minute","hour","day"],
        weights=[5, 20, 50, 25]
    )[0]

    base_hourly = 50.0 + (level * 40.0) + random.uniform(-10, 30)
    cycle_ticks = PAY_CYCLES[pay_cycle]
    wage = round(base_hourly * (cycle_ticks / 720.0), 2)

    # Pick abilities from job pool (3-5)
    pool = JOB_ABILITY_POOLS.get(job, [])
    n    = random.randint(ABILITIES_PER_EXEC_MIN, min(ABILITIES_PER_EXEC_MAX, len(pool)))
    chosen_abilities = random.sample(pool, n) if pool else []

    is_special     = force_special or (random.random() < SPECIAL_CHANCE)
    special_ability = None
    special_title   = None
    special_flavor  = None

    if is_special:
        special_ability = random.choice(list(LEGENDARY_BONUS_ABILITIES.keys()))
        special_title   = random.choice(NAME_DATA.get("special_titles", ["The Legend"]))
        special_flavor  = random.choice(NAME_DATA.get("special_flavor", ["Truly extraordinary."]))
        level = min(level + random.randint(1, 3), 7)
        base_hourly = 100.0 + (level * 60.0) + random.uniform(0, 50)
        wage = round(base_hourly * (cycle_ticks / 720.0), 2)

    return {
        "first_name":      first_name,
        "last_name":       last_name,
        "job":             job,
        "level":           level,
        "current_age":     current_age,
        "retirement_age":  retirement_age,
        "max_age":         max_age,
        "wage":            wage,
        "pay_cycle":       pay_cycle,
        "abilities":       ",".join(chosen_abilities),
        "is_special":      is_special,
        "special_ability": special_ability,
        "special_title":   special_title,
        "special_flavor":  special_flavor,
        "on_marketplace":  True,
        "marketplace_reason": "new",
    }


def _fire_exec_push(player_id: int, title: str, body: str, url: str = "/executives"):
    """Send a push notification for executive events (non-blocking)."""
    def _send():
        try:
            from push_ux import send_push_notification
            send_push_notification(player_id, title, body, url, notif_type="execs",
                                   tag=f"exec-{player_id}-{title[:20]}")
        except Exception as e:
            print(f"[Executive] Push error: {e}")
    threading.Thread(target=_send, daemon=True).start()


def create_executive(db, force_special: bool = False) -> Executive:
    attrs    = generate_executive(force_special=force_special)
    exec_obj = Executive(**attrs)
    db.add(exec_obj)
    db.commit()
    db.refresh(exec_obj)
    return exec_obj


# ==========================
# HIRE / FIRE
# ==========================

def hire_executive(db, player_id: int, executive_id: int) -> dict:
    from auth import Player
    player   = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        return {"success": False, "error": "Player not found"}

    exec_obj = db.query(Executive).filter(
        Executive.id == executive_id,
        Executive.on_marketplace == True,
        Executive.is_dead == False
    ).first()
    if not exec_obj:
        return {"success": False, "error": "Executive not available"}

    current_count = db.query(Executive).filter(
        Executive.player_id == player_id,
        Executive.is_dead   == False
    ).count()
    if current_count >= MAX_EXECUTIVES_PER_PLAYER:
        return {"success": False, "error": f"Maximum {MAX_EXECUTIVES_PER_PLAYER} executives allowed"}

    hiring_fee = exec_obj.wage * (PAY_CYCLES["day"] / PAY_CYCLES[exec_obj.pay_cycle])

    # Apply board_influence ability: reduces all hiring fees
    board_bonus = get_specific_ability_bonus(db, player_id, "board_influence")
    if board_bonus > 0:
        hiring_fee = round(hiring_fee * max(0.05, 1.0 - board_bonus), 2)

    from reserve_banks import can_afford_usd, spend_player_funds
    if not can_afford_usd(player_id, hiring_fee):
        return {"success": False, "error": f"Insufficient funds. Hiring fee: ${hiring_fee:,.2f}"}

    ok, err = spend_player_funds(player.id, hiring_fee)
    if not ok:
        return {"success": False, "error": err}
    # Apply talent_scout ability: extends hired exec's retirement age
    talent_bonus = get_specific_ability_bonus(db, player_id, "talent_scout")
    if talent_bonus > 0:
        extra_years = max(1, int(exec_obj.retirement_age * min(talent_bonus, 0.50)))
        exec_obj.retirement_age += extra_years
        exec_obj.max_age        += extra_years

    exec_obj.player_id       = player_id
    exec_obj.on_marketplace  = False
    exec_obj.hired_at        = datetime.utcnow()
    exec_obj.fired_at        = None
    exec_obj.is_retired      = False
    exec_obj.missed_payments = 0
    exec_obj.marketplace_reason = None
    db.commit()

    job_info = EXECUTIVE_JOBS.get(exec_obj.job, {})
    title_str = job_info.get('title', exec_obj.job)
    try:
        from reserve_banks import get_player_display_currency, fmt_usd as _rfmt
        _fee_str = _rfmt(hiring_fee, get_player_display_currency(player_id), precision=0)
    except Exception:
        _fee_str = f"${hiring_fee:,.0f}"
    _fire_exec_push(
        player_id,
        f"{exec_obj.first_name} {exec_obj.last_name} Hired",
        f"{title_str} — hiring fee {_fee_str} paid",
    )
    return {
        "success": True,
        "message": f"Hired {exec_obj.first_name} {exec_obj.last_name} as {title_str}",
        "fee": hiring_fee
    }


def fire_executive(db, player_id: int, executive_id: int) -> dict:
    from auth import Player
    exec_obj = db.query(Executive).filter(
        Executive.id == executive_id,
        Executive.player_id == player_id
    ).first()
    if not exec_obj:
        return {"success": False, "error": "Executive not found in your employ"}

    player = db.query(Player).filter(Player.id == player_id).first()

    cycle_ticks   = PAY_CYCLES[exec_obj.pay_cycle]
    monthly_wages = exec_obj.wage * (PENSION_DURATION_TICKS / cycle_ticks)
    severance     = monthly_wages  # 1 month pension + 1 month severance = 2x monthly

    # Golden-parachute-refusal waives everything
    if exec_obj.is_special and exec_obj.special_ability == "pension_free":
        monthly_wages = 0.0
        severance     = 0.0

    # Severance deducted immediately; respects legal tender preference
    if player and severance > 0:
        from reserve_banks import spend_player_funds
        ok, _ = spend_player_funds(player.id, severance)
        if not ok:
            player.cash_balance -= severance  # force-deduct as unavoidable obligation

    exec_obj.player_id              = None
    exec_obj.on_marketplace         = True
    exec_obj.marketplace_reason     = "fired"
    exec_obj.fired_at               = datetime.utcnow()
    exec_obj.is_in_school           = False
    exec_obj.school_ticks_remaining = 0
    exec_obj.school_total_ticks     = 0
    exec_obj.school_cost_remaining  = 0.0
    exec_obj.pending_upgrade        = False
    exec_obj.pension_owed           = monthly_wages
    exec_obj.pension_ticks_remaining = PENSION_DURATION_TICKS if monthly_wages > 0 else 0
    exec_obj.pension_owed_by        = player_id if monthly_wages > 0 else None
    exec_obj.severance_owed         = severance
    exec_obj.severance_owed_by      = player_id
    db.commit()

    total_exit = monthly_wages + severance
    try:
        from reserve_banks import get_player_display_currency, fmt_usd as _rfmt
        _disp = get_player_display_currency(player_id)
        _sev_str = _rfmt(severance,     _disp, precision=0)
        _pen_str = _rfmt(monthly_wages, _disp, precision=0)
        _tot_str = _rfmt(total_exit,    _disp, precision=0)
    except Exception:
        _sev_str = f"${severance:,.0f}"
        _pen_str = f"${monthly_wages:,.0f}"
        _tot_str = f"${total_exit:,.0f}"
    _fire_exec_push(
        player_id,
        f"{exec_obj.first_name} {exec_obj.last_name} Fired",
        f"Severance {_sev_str} paid, pension {_pen_str} owed (total {_tot_str})",
    )
    return {
        "success":  True,
        "message":  (f"Fired {exec_obj.first_name} {exec_obj.last_name}. "
                     f"Severance paid: ${severance:,.2f}. Pension owed: ${monthly_wages:,.2f} "
                     f"(total exit cost: ${total_exit:,.2f})"),
        "pension":  monthly_wages,
        "severance": severance,
    }


# ==========================
# SCHOOL
# ==========================

def send_to_school(db, player_id: int, executive_id: int) -> dict:
    from auth import Player
    player   = db.query(Player).filter(Player.id == player_id).first()
    exec_obj = db.query(Executive).filter(
        Executive.id == executive_id,
        Executive.player_id == player_id
    ).first()

    if not exec_obj:
        return {"success": False, "error": "Executive not found in your employ"}
    if exec_obj.is_in_school:
        return {"success": False, "error": "Executive is already in school"}
    if exec_obj.pending_upgrade:
        return {"success": False, "error": "Executive has a pending upgrade selection"}
    max_lvl = getattr(exec_obj, "max_level", 7) or 7
    if exec_obj.level >= max_lvl:
        return {"success": False, "error": f"Executive is at maximum level ({max_lvl})"}

    target_level = exec_obj.level + 1
    cost  = SCHOOL_BASE_COST * target_level
    ticks = SCHOOL_BASE_TICKS * target_level

    school_discount = get_school_discount(db, player_id)
    cost  *= max(0.20, 1.0 - school_discount)
    ticks  = int(ticks * max(0.20, 1.0 - school_discount))

    if exec_obj.is_special and exec_obj.special_ability == "fast_learner":
        ticks = ticks // 2

    from reserve_banks import spend_player_funds
    ok, err = spend_player_funds(player.id, cost)
    if not ok:
        return {"success": False, "error": err}

    exec_obj.is_in_school            = True
    exec_obj.school_ticks_remaining  = ticks
    exec_obj.school_total_ticks      = ticks
    exec_obj.school_cost_remaining   = 0.0
    db.commit()

    try:
        from reserve_banks import get_player_display_currency, fmt_usd as _rfmt
        _cost_str = _rfmt(cost, get_player_display_currency(player_id), precision=0)
    except Exception:
        _cost_str = f"${cost:,.0f}"
    _fire_exec_push(
        player_id,
        f"{exec_obj.first_name} {exec_obj.last_name} Enrolled",
        f"Sent to school — graduates in {ticks} ticks, cost {_cost_str}",
    )
    return {
        "success": True,
        "message": f"Enrolled {exec_obj.first_name} {exec_obj.last_name}. Graduation in {ticks} ticks.",
        "cost":    cost,
        "ticks":   ticks
    }


def apply_school_upgrade(db, player_id: int, executive_id: int, bonus_key: str) -> dict:
    """
    Apply a school graduation option.
    Valid keys: perf_focus | balanced_dev | team_lead
    School NEVER adds new abilities — it only boosts existing ones.
    """
    exec_obj = db.query(Executive).filter(
        Executive.id == executive_id,
        Executive.player_id == player_id
    ).first()
    if not exec_obj:
        return {"success": False, "error": "Executive not found"}
    if not exec_obj.pending_upgrade:
        return {"success": False, "error": "No pending upgrade"}

    upgrade = SCHOOL_UPGRADES.get(bonus_key)
    if not upgrade:
        return {"success": False, "error": "Invalid upgrade selection"}

    # Record the performance boost in bonuses column
    existing = exec_obj.bonuses or ""
    exec_obj.bonuses = (existing + "," + upgrade["bonus"]).lstrip(",")

    # Level increases
    exec_obj.level          += 1
    exec_obj.pending_upgrade = False

    # Wage: school graduation = +15% raise, then apply any wage modifier.
    # First Ladies have a permanent $0 wage (free forever) — do not inflate it.
    if not getattr(exec_obj, 'is_first_lady', False):
        exec_obj.wage = round(exec_obj.wage * (1.0 + WAGE_RAISE_ON_SCHOOL) * upgrade["wage_mod"], 2)
        if exec_obj.wage < 0.01:
            exec_obj.wage = 0.01

    db.commit()

    _fire_exec_push(
        player_id,
        f"{exec_obj.first_name} {exec_obj.last_name} Graduated",
        f"Now level {exec_obj.level} — {upgrade['name']} unlocked",
    )
    return {
        "success": True,
        "message": (f"{exec_obj.first_name} {exec_obj.last_name} graduated to level {exec_obj.level}! "
                    f"Upgrade: {upgrade['name']}.")
    }


# ==========================
# TICK PROCESSING
# ==========================

def tick(current_tick: int, now: datetime):
    db = get_db()
    try:
        _process_aging(db, current_tick)
        _process_wages(db, current_tick)
        _process_pensions(db, current_tick)
        _process_school(db, current_tick)
        _process_marketplace_spawn(db, current_tick)
        _process_market_maker(db, current_tick)
        _process_rainmaker(db, current_tick)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[Executive Tick {current_tick}] ERROR: {e}")
    finally:
        db.close()


def _process_aging(db, current_tick: int):
    living = db.query(Executive).filter(Executive.is_dead == False).all()

    # Pre-compute per-player aging slowdown from culture_builder + fl_health_advocate
    from collections import defaultdict
    _player_aging_bonus: dict = defaultdict(float)
    for be in living:
        if be.player_id is None or be.is_retired or be.is_in_school:
            continue
        for key in (be.abilities or "").split(","):
            adef = EXEC_ABILITIES.get(key)
            if adef and key in ("culture_builder", "fl_health_advocate"):
                _player_aging_bonus[be.player_id] += adef["value"]

    for ex in living:
        ex.age_tick_accumulator += 1

        ticks_needed = TICKS_PER_YEAR
        if ex.is_special and ex.special_ability == "eternal_youth":
            ticks_needed = int(TICKS_PER_YEAR * 2)  # ages half speed

        # Apply culture_builder / fl_health_advocate aging slowdown
        if ex.player_id and ex.player_id in _player_aging_bonus:
            aging_bonus = min(_player_aging_bonus[ex.player_id], 0.75)
            ticks_needed = int(ticks_needed * (1.0 + aging_bonus))

        if ex.age_tick_accumulator < ticks_needed:
            continue

        ex.age_tick_accumulator = 0
        ex.current_age         += 1

        # ── 7.85% automatic pay raise every birthday (not for free First Ladies) ─
        if not getattr(ex, 'is_first_lady', False):
            ex.wage = round(ex.wage * (1.0 + WAGE_RAISE_ON_AGEUP), 2)

        # Death check
        if ex.current_age >= ex.max_age:
            ex.is_dead        = True
            ex.on_marketplace = False
            if ex.player_id is not None:
                _deceased_pid = ex.player_id
                print(f"[Executive] {ex.first_name} {ex.last_name} has passed away at age {ex.current_age}.")
                _fire_exec_push(
                    _deceased_pid,
                    f"{ex.first_name} {ex.last_name} Has Passed Away",
                    f"Your executive passed away at age {ex.current_age}. Their position is now vacant.",
                )
                ex.player_id = None
            continue

        # Retirement check
        if (ex.current_age >= ex.retirement_age
                and not ex.is_retired
                and ex.player_id is not None):
            _retire_executive(db, ex)


def _retire_executive(db, ex: Executive):
    cycle_ticks   = PAY_CYCLES[ex.pay_cycle]
    monthly_wages = ex.wage * (PENSION_DURATION_TICKS / cycle_ticks)

    if ex.is_special and ex.special_ability == "pension_free":
        monthly_wages = 0.0

    retiring_from = ex.player_id
    ex.is_retired                = True
    ex.pension_owed              = monthly_wages
    ex.pension_ticks_remaining   = PENSION_DURATION_TICKS if monthly_wages > 0 else 0
    ex.pension_owed_by           = retiring_from if monthly_wages > 0 else None
    ex.player_id                 = None
    ex.on_marketplace            = True
    ex.marketplace_reason        = "retired_available"
    ex.is_in_school              = False
    ex.school_ticks_remaining    = 0
    ex.school_total_ticks        = 0
    ex.pending_upgrade           = False
    print(f"[Executive] {ex.first_name} {ex.last_name} retired at age {ex.current_age}. "
          f"Pension: ${monthly_wages:,.2f}")
    _fire_exec_push(
        retiring_from,
        f"{ex.first_name} {ex.last_name} Retired",
        f"Reached retirement age {ex.current_age} — pension ${monthly_wages:,.0f} owed",
    )


def _quit_for_nonpayment(db, ex: Executive, player):
    """
    Executive quits instantly due to missed wage payment.
    Player owes: immediate severance (2 months) + ongoing pension (1 month).
    Executive re-enters the marketplace.
    """
    cycle_ticks = PAY_CYCLES[ex.pay_cycle]
    pension     = ex.wage * (PENSION_DURATION_TICKS       / cycle_ticks)
    severance   = ex.wage * (PENSION_DURATION_TICKS * 2.0 / cycle_ticks)

    # Severance deducted immediately; respects legal tender preference
    from reserve_banks import spend_player_funds
    ok, _ = spend_player_funds(player.id, severance)
    if not ok:
        player.cash_balance -= severance  # force-deduct as unavoidable obligation

    quitting_from = ex.player_id
    ex.pension_owed              = pension
    ex.pension_ticks_remaining   = PENSION_DURATION_TICKS
    ex.pension_owed_by           = quitting_from
    ex.severance_owed            = severance
    ex.severance_owed_by         = quitting_from

    ex.player_id                 = None
    ex.on_marketplace            = True
    ex.marketplace_reason        = "quit_nonpayment"
    ex.fired_at                  = datetime.utcnow()
    ex.is_in_school              = False
    ex.school_ticks_remaining    = 0
    ex.school_total_ticks        = 0
    ex.pending_upgrade           = False

    print(f"[Executive] {ex.first_name} {ex.last_name} QUIT due to non-payment! "
          f"Severance ${severance:,.2f} deducted, pension ${pension:,.2f} owed.")
    _fire_exec_push(
        quitting_from,
        f"{ex.first_name} {ex.last_name} Quit",
        f"Resigned due to non-payment — severance ${severance:,.0f} deducted, pension ${pension:,.0f} owed",
    )


def _process_wages(db, current_tick: int):
    from auth import Player
    employed = db.query(Executive).filter(
        Executive.player_id != None,
        Executive.is_dead    == False,
        Executive.is_retired == False,
    ).all()

    # Build set of player IDs protected by a crisis_manager legendary exec
    crisis_managed_players = {
        e.player_id for e in employed
        if e.is_special and e.special_ability == "crisis_manager"
    }

    for ex in employed:
        ex.pay_tick_accumulator += 1
        cycle_ticks = PAY_CYCLES.get(ex.pay_cycle, 720)

        if ex.pay_tick_accumulator < cycle_ticks:
            continue

        ex.pay_tick_accumulator = 0
        wage = ex.wage

        # HR / cost-center bonus reduces the wage bill
        hr_bonus  = get_player_job_bonus(db, ex.player_id, "wages")
        wage     *= max(0.10, 1.0 - hr_bonus)

        # Legendary half-wages
        if ex.is_special and ex.special_ability == "half_wages":
            wage *= 0.5

        wage = round(wage, 2)
        player = db.query(Player).filter(Player.id == ex.player_id).first()
        if not player:
            continue

        from reserve_banks import can_afford_usd, spend_player_funds
        if not can_afford_usd(player.id, wage):
            # ── Can't pay ─────────────────────────────────────────────────────
            if ex.is_special and ex.special_ability == "iron_will":
                # Issues a formal warning instead of quitting
                ex.missed_payments += 1
                print(f"[Executive] {ex.first_name} {ex.last_name} (Iron Will) issues formal "
                      f"warning #{ex.missed_payments} — payment missed but will not quit.")
                _fire_exec_push(
                    player.id,
                    f"Salary Warning — {ex.first_name} {ex.last_name}",
                    f"Missed payment #{ex.missed_payments} (${wage:,.0f} owed) — they won't quit yet, but pay soon",
                )
            elif ex.player_id in crisis_managed_players and ex.missed_payments == 0:
                # Crisis Manager grants all co-workers a one-cycle grace on first miss
                ex.missed_payments += 1
                print(f"[Executive] Crisis Manager shields {ex.first_name} {ex.last_name} "
                      f"from immediate quit — one pay cycle grace period granted.")
                _fire_exec_push(
                    ex.player_id,
                    f"Crisis Manager Intervened — {ex.first_name} {ex.last_name}",
                    f"Your Crisis Manager granted {ex.first_name} {ex.last_name} a one-cycle wage grace. Pay soon or they will quit.",
                )
            else:
                _quit_for_nonpayment(db, ex, player)
        else:
            # ── Normal payment ────────────────────────────────────────────────
            ok, _err = spend_player_funds(player.id, wage)
            if ok:
                ex.missed_payments = 0  # reset on successful pay
            else:
                _quit_for_nonpayment(db, ex, player)


def _process_pensions(db, current_tick: int):
    from auth import Player
    pensioners = db.query(Executive).filter(
        Executive.pension_ticks_remaining > 0,
        Executive.pension_owed > 0
    ).all()

    for ex in pensioners:
        ex.pension_ticks_remaining -= 1
        payment = ex.pension_owed / PENSION_DURATION_TICKS  # even spread

        if ex.pension_owed_by:
            player = db.query(Player).filter(Player.id == ex.pension_owed_by).first()
            if player:
                from reserve_banks import spend_player_funds
                ok, _ = spend_player_funds(player.id, payment)
                if not ok:
                    player.cash_balance -= payment  # force-deduct as unavoidable obligation

        if ex.pension_ticks_remaining <= 0:
            ex.pension_owed      = 0.0
            ex.pension_owed_by   = None
            # Re-enter workforce if still healthy
            if not ex.is_dead and ex.current_age < ex.max_age - 5:
                ex.is_retired     = False
                ex.on_marketplace = True
                if ex.marketplace_reason == "retired_available":
                    pass  # already set
                else:
                    ex.marketplace_reason = "retired_available"


def _process_school(db, current_tick: int):
    in_school = db.query(Executive).filter(
        Executive.is_in_school         == True,
        Executive.school_ticks_remaining > 0
    ).all()

    for ex in in_school:
        ex.school_ticks_remaining -= 1
        if ex.school_ticks_remaining <= 0:
            ex.is_in_school   = False
            ex.pending_upgrade = True
            if ex.player_id:
                _fire_exec_push(
                    ex.player_id,
                    f"{ex.first_name} {ex.last_name} Graduated",
                    "School complete — choose an upgrade in the Executives panel",
                )


def _process_marketplace_spawn(db, current_tick: int):
    if current_tick % SPAWN_INTERVAL_TICKS != 0:
        return

    count = db.query(Executive).filter(
        Executive.on_marketplace == True,
        Executive.is_dead        == False
    ).count()

    if count < MAX_MARKETPLACE_SIZE:
        num = random.randint(1, 3)
        for _ in range(num):
            if count + num <= MAX_MARKETPLACE_SIZE:
                create_executive(db)

        if random.random() < 0.10:
            create_executive(db, force_special=True)


def _process_market_maker(db, current_tick: int):
    from auth import Player
    market_makers = db.query(Executive).filter(
        Executive.player_id    != None,
        Executive.is_dead      == False,
        Executive.is_retired   == False,
        Executive.is_in_school == False,
        Executive.is_special   == True,
        Executive.special_ability == "market_maker"
    ).all()

    for ex in market_makers:
        player = db.query(Player).filter(Player.id == ex.player_id).first()
        if player:
            try:
                from reserve_banks import convert_to_legal_tender
                _amt, _code = convert_to_legal_tender(player.id, 500.0)
                if _code == "USD":
                    player.cash_balance += _amt
            except Exception:
                player.cash_balance += 500.0


def _process_rainmaker(db, current_tick: int):
    """Rainmaker legendary ability: random bonus income events."""
    if current_tick % 720 != 0:  # check every hour
        return
    from auth import Player
    rainmakers = db.query(Executive).filter(
        Executive.player_id    != None,
        Executive.is_dead      == False,
        Executive.is_retired   == False,
        Executive.is_in_school == False,
        Executive.is_special   == True,
        Executive.special_ability == "rainmaker"
    ).all()

    for ex in rainmakers:
        if random.random() < 0.30:  # 30% chance each hour check
            bonus = random.uniform(2000, 10000)
            player = db.query(Player).filter(Player.id == ex.player_id).first()
            if player:
                try:
                    from reserve_banks import convert_to_legal_tender
                    _amt, _code = convert_to_legal_tender(player.id, bonus)
                    if _code == "USD":
                        player.cash_balance += _amt
                except Exception:
                    player.cash_balance += bonus
                print(f"[Rainmaker] {ex.first_name} {ex.last_name} brought in ${bonus:,.2f}!")


# ==========================
# INITIALIZATION
# ==========================

def initialize():
    """Create tables, run column migrations, seed marketplace."""
    Base.metadata.create_all(bind=engine)
    load_names()

    # ── Column migrations for existing databases ──────────────────────────────
    from database import run_ddl_migration
    run_ddl_migration(engine, [
        "ALTER TABLE executives ADD COLUMN abilities TEXT DEFAULT ''",
        "ALTER TABLE executives ADD COLUMN school_total_ticks INTEGER DEFAULT 0",
        "ALTER TABLE executives ADD COLUMN missed_payments INTEGER DEFAULT 0",
        "ALTER TABLE executives ADD COLUMN pension_owed_by INTEGER",
        "ALTER TABLE executives ADD COLUMN severance_owed REAL DEFAULT 0.0",
        "ALTER TABLE executives ADD COLUMN severance_owed_by INTEGER",
        "ALTER TABLE executives ADD COLUMN is_first_lady BOOLEAN DEFAULT FALSE",
        "ALTER TABLE executives ADD COLUMN max_level INTEGER DEFAULT 7",
    ])

    db = get_db()
    try:
        count = db.query(Executive).filter(
            Executive.on_marketplace == True,
            Executive.is_dead        == False
        ).count()
        if count == 0:
            for _ in range(10):
                create_executive(db)
            create_executive(db, force_special=True)
            print("  [Executive] Seeded 11 executives on marketplace")
    finally:
        db.close()
