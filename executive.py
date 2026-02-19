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
from datetime import datetime
from typing import Optional, List
from sqlalchemy import create_engine, Column, String, Float, DateTime, Integer, Boolean, Text, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# ==========================
# DATABASE SETUP
# ==========================
DATABASE_URL = "sqlite:///./wadsworth.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
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
        "description": "Manages DMs, contract notifications, and P2P deal flow",
        "effect": "p2p",
    },
}

# ==========================
# EXECUTIVE ABILITIES
# ==========================
EXEC_ABILITIES = {
    # ── BUSINESS ──────────────────────────────────────────────────────────────
    "corp_synergy":        {"name": "Corporate Synergy",       "desc": "All executive bonuses +5% across the board",            "effect": "business", "value": 0.05},
    "talent_scout":        {"name": "Talent Scout",            "desc": "New executives appear on marketplace 15% more often",   "effect": "business", "value": 0.15},
    "board_influence":     {"name": "Board Influence",         "desc": "All executive hiring fees −20%",                        "effect": "business", "value": 0.20},
    "strategic_vision":    {"name": "Strategic Vision",        "desc": "Business production output +8%",                       "effect": "business", "value": 0.08},
    "culture_builder":     {"name": "Culture Builder",         "desc": "All executives age 10% slower",                        "effect": "business", "value": 0.10},
    "executive_aura":      {"name": "Executive Aura",          "desc": "All other executive effects +3%",                      "effect": "business", "value": 0.03},
    "hr_mastery":          {"name": "HR Mastery",              "desc": "All executive wages −8%",                              "effect": "wages",    "value": 0.08},
    "retention_bonus":     {"name": "Retention Bonus",         "desc": "Executive school costs −12%",                          "effect": "school",   "value": 0.12},
    "succession_plan":     {"name": "Succession Planning",     "desc": "On this exec's retirement the next hire fee is waived", "effect": "business", "value": 1.0},
    # ── SALES ─────────────────────────────────────────────────────────────────
    "demand_surge":        {"name": "Demand Surge",            "desc": "Retail/sales volume +12%",                             "effect": "sales",   "value": 0.12},
    "brand_equity":        {"name": "Brand Equity",            "desc": "Passive income from all businesses +6%",               "effect": "sales",   "value": 0.06},
    "viral_campaign":      {"name": "Viral Campaign",          "desc": "Business demand multiplier +10%",                      "effect": "sales",   "value": 0.10},
    "conversion_pro":      {"name": "Conversion Pro",          "desc": "Business sale price +8%",                              "effect": "sales",   "value": 0.08},
    "loyalty_program":     {"name": "Loyalty Program",         "desc": "Sales tax on businesses −8%",                          "effect": "sales",   "value": 0.08},
    "influencer_network":  {"name": "Influencer Network",      "desc": "Cities generate 10% more revenue",                     "effect": "cities",  "value": 0.10},
    "market_intelligence": {"name": "Market Intelligence",     "desc": "Reveals real-time demand trends for all markets",       "effect": "sales",   "value": 0.07},
    "upsell_mastery":      {"name": "Upsell Mastery",          "desc": "Average transaction value +10%",                       "effect": "sales",   "value": 0.10},
    # ── PRODUCTION ────────────────────────────────────────────────────────────
    "lean_ops":            {"name": "Lean Operations",         "desc": "Business production cycles 10% faster",                "effect": "production", "value": 0.10},
    "supply_chain_opt":    {"name": "Supply Chain Optimization","desc": "Business input costs −8%",                            "effect": "production", "value": 0.08},
    "automation_drive":    {"name": "Automation Drive",        "desc": "Production output +12%",                               "effect": "production", "value": 0.12},
    "quality_control":     {"name": "Quality Control",         "desc": "Business waste / output loss −10%",                    "effect": "production", "value": 0.10},
    "capacity_expand":     {"name": "Capacity Expansion",      "desc": "Business slot cap +1 for this player",                 "effect": "production", "value": 1.0},
    "process_reeng":       {"name": "Process Reengineering",   "desc": "Executive school duration −15%",                       "effect": "school",     "value": 0.15},
    "ops_excellence":      {"name": "Operational Excellence",  "desc": "Land efficiency decay slowed −10%",                    "effect": "land",       "value": 0.10},
    "throughput_boost":    {"name": "Throughput Boost",        "desc": "Production output +10%, speed +5%",                    "effect": "production", "value": 0.10},
    # ── BANKING ───────────────────────────────────────────────────────────────
    "interest_arb":        {"name": "Interest Arbitrage",      "desc": "Loan interest rates −15%",                             "effect": "banking", "value": 0.15},
    "dividend_boost":      {"name": "Dividend Booster",        "desc": "Bank dividend returns +12%",                           "effect": "banking", "value": 0.12},
    "capital_reserve":     {"name": "Capital Reserve Protocol","desc": "$5,000 negative balance buffer before penalties",       "effect": "banking", "value": 5000.0},
    "portfolio_hedge":     {"name": "Portfolio Hedge",         "desc": "Crypto market volatility impact −20%",                  "effect": "banking", "value": 0.20},
    "cost_center_audit":   {"name": "Cost Center Audit",       "desc": "All executive wages −8% through efficiency gains",     "effect": "wages",   "value": 0.08},
    "investment_grade":    {"name": "Investment Grade",        "desc": "Banking bonus effectiveness +15%",                     "effect": "banking", "value": 0.15},
    "debt_restructure":    {"name": "Debt Restructuring",      "desc": "Can renegotiate loans at 10% better terms",            "effect": "banking", "value": 0.10},
    "banking_synergy":     {"name": "Banking Synergy",         "desc": "All banking effects compound an extra 5%",             "effect": "banking", "value": 0.05},
    # ── TAXES ─────────────────────────────────────────────────────────────────
    "tax_shield":          {"name": "Tax Shield",              "desc": "All property taxes −10%",                              "effect": "taxes",  "value": 0.10},
    "compliance_expert":   {"name": "Compliance Expert",       "desc": "Immune to random tax penalty events",                  "effect": "taxes",  "value": 1.0},
    "loophole_finder":     {"name": "Loophole Finder",         "desc": "Land taxes −15%",                                      "effect": "taxes",  "value": 0.15},
    "deduction_master":    {"name": "Deduction Master",        "desc": "Business taxes −12%",                                  "effect": "taxes",  "value": 0.12},
    "audit_defense":       {"name": "Audit Defense",           "desc": "Immunity to audit events and related penalties",       "effect": "taxes",  "value": 1.0},
    "tax_treaty":          {"name": "Tax Treaty Expertise",    "desc": "District taxes −10%",                                  "effect": "taxes",  "value": 0.10},
    "legal_arb":           {"name": "Legal Arbitrage",         "desc": "All platform fees −8%",                                "effect": "taxes",  "value": 0.08},
    "county_exemption":    {"name": "County Exemption",        "desc": "County taxes −20%",                                    "effect": "taxes",  "value": 0.20},
    # ── CRYPTO ────────────────────────────────────────────────────────────────
    "blockchain_native":   {"name": "Blockchain Native",       "desc": "Crypto transaction fees −20%",                         "effect": "crypto",  "value": 0.20},
    "defi_specialist":     {"name": "DeFi Specialist",         "desc": "Yield farming / staking returns +15%",                 "effect": "crypto",  "value": 0.15},
    "security_hard":       {"name": "Security Hardening",      "desc": "Crypto wallet protected from theft/hack events",       "effect": "crypto",  "value": 1.0},
    "algo_trading":        {"name": "Algorithmic Trading",     "desc": "Automated crypto positions earn +5% more",             "effect": "crypto",  "value": 0.05},
    "smart_contract_aud":  {"name": "Smart Contract Auditing", "desc": "P2P contract disputes resolved +20% in your favour",   "effect": "crypto",  "value": 0.20},
    "data_analytics":      {"name": "Data Analytics",          "desc": "Reveals live market trend data for all assets",        "effect": "crypto",  "value": 1.0},
    "web3_native":         {"name": "Web3 Native",             "desc": "All crypto bonuses +8%",                               "effect": "crypto",  "value": 0.08},
    "token_strategy":      {"name": "Token Strategy",          "desc": "Meme coin / WSC yield +10%",                           "effect": "crypto",  "value": 0.10},
    # ── LAND ──────────────────────────────────────────────────────────────────
    "land_survey_exp":     {"name": "Land Survey Expertise",   "desc": "Land efficiency decay −20%",                           "effect": "land", "value": 0.20},
    "zoning_expert":       {"name": "Zoning Expert",           "desc": "Land purchase prices −10%",                            "effect": "land", "value": 0.10},
    "green_cert":          {"name": "Green Certification",     "desc": "Sustainable land plots get 15% tax exemption",         "effect": "land", "value": 0.15},
    "property_dev":        {"name": "Property Development",    "desc": "Land appreciation value +8% per cycle",                "effect": "land", "value": 0.08},
    "easement_neg":        {"name": "Easement Negotiator",     "desc": "Land hoarding tax −15%",                               "effect": "land", "value": 0.15},
    "urban_planning":      {"name": "Urban Planning",          "desc": "City bonus effects +8%",                               "effect": "cities","value": 0.08},
    "env_compliance":      {"name": "Environmental Compliance","desc": "Regulatory fines and land penalties −25%",              "effect": "land", "value": 0.25},
    "land_banking":        {"name": "Land Banking",            "desc": "Owned land plots passively appreciate 5%/cycle",       "effect": "land", "value": 0.05},
    # ── CITIES ────────────────────────────────────────────────────────────────
    "grant_writer":        {"name": "Grant Writer",            "desc": "City grants +20%",                                     "effect": "cities","value": 0.20},
    "infra_push":          {"name": "Infrastructure Push",     "desc": "City fund generation +15%",                            "effect": "cities","value": 0.15},
    "civic_partner":       {"name": "Civic Partnership",       "desc": "District output +10% from city investment",            "effect": "cities","value": 0.10},
    "urban_renewal":       {"name": "Urban Renewal",           "desc": "City growth rate +12%",                                "effect": "cities","value": 0.12},
    "public_relations":    {"name": "Public Relations",        "desc": "City-level taxes −10%",                                "effect": "cities","value": 0.10},
    "mayoral_liaison":     {"name": "Mayoral Liaison",         "desc": "Government grants appear 25% more often",              "effect": "cities","value": 0.25},
    "smart_city":          {"name": "Smart City Initiative",   "desc": "Tech investments multiply city output +12%",           "effect": "cities","value": 0.12},
    # ── DISTRICTS ─────────────────────────────────────────────────────────────
    "district_champ":      {"name": "District Champion",       "desc": "District business output +15%",                        "effect": "districts","value": 0.15},
    "tax_incentive_zone":  {"name": "Tax Incentive Zone",      "desc": "District taxes −20%",                                  "effect": "districts","value": 0.20},
    "biz_incubator":       {"name": "Business Incubator",      "desc": "New businesses in district cost 10% less",             "effect": "districts","value": 0.10},
    "corridor_dev":        {"name": "Corridor Development",    "desc": "Connected districts share a 5% bonus",                 "effect": "districts","value": 0.05},
    "rezoning_expert":     {"name": "Rezoning Expert",         "desc": "District type conversion costs −15%",                  "effect": "districts","value": 0.15},
    "cluster_effect":      {"name": "Cluster Effect",          "desc": "Multiple businesses in same district +8% each",        "effect": "districts","value": 0.08},
    "local_partnership":   {"name": "Local Partnership",       "desc": "District P2P fees −15%",                               "effect": "districts","value": 0.15},
    # ── COUNTIES ──────────────────────────────────────────────────────────────
    "county_commission":   {"name": "County Commissioner",     "desc": "County taxes −25%",                                    "effect": "counties","value": 0.25},
    "land_grant_prog":     {"name": "Land Grant Program",      "desc": "Occasional free land plot in county",                  "effect": "counties","value": 1.0},
    "rural_dev":           {"name": "Rural Development",       "desc": "County business output +12%",                          "effect": "counties","value": 0.12},
    "county_bond":         {"name": "County Bond Access",      "desc": "County infrastructure loans at 5% lower rates",        "effect": "counties","value": 0.05},
    "annexation_right":    {"name": "Annexation Rights",       "desc": "Expand district territory into county land",           "effect": "counties","value": 1.0},
    "agri_bonus":          {"name": "Agricultural Bonus",      "desc": "Farming/rural land efficiency +15%",                   "effect": "counties","value": 0.15},
    "regional_hub":        {"name": "Regional Hub",            "desc": "County as trade hub: P2P traffic +10%",                "effect": "counties","value": 0.10},
    # ── P2P ───────────────────────────────────────────────────────────────────
    "p2p_notification":    {"name": "P2P Notification System", "desc": "Enables envelope (DM) and paper (contract) icons on the P2P dashboard button", "effect": "p2p","value": 1.0},
    "dm_threeway":         {"name": "Multi-Party DMs",         "desc": "Unlocks adding 3rd parties to direct messages",        "effect": "p2p","value": 1.0},
    "contract_tracker":    {"name": "Contract Tracker",        "desc": "Real-time contract status alerts in dashboard",        "effect": "p2p","value": 1.0},
    "fee_negotiator":      {"name": "Fee Negotiator",          "desc": "P2P entry/listing fees −25%",                          "effect": "p2p","value": 0.25},
    "network_expander":    {"name": "Network Expander",        "desc": "P2P reach increased: more players discoverable",       "effect": "p2p","value": 1.0},
    "deal_scout":          {"name": "Deal Scout",              "desc": "Early access to new P2P marketplace listings",         "effect": "p2p","value": 1.0},
    "rep_shield":          {"name": "Reputation Shield",       "desc": "P2P reputation score protected from dispute fallout",  "effect": "p2p","value": 1.0},
    "mediation_svc":       {"name": "Mediation Service",       "desc": "P2P disputes resolved in your favour 20% more often", "effect": "p2p","value": 0.20},
}

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
    "crisis_manager":    {"name": "Crisis Manager",           "desc": "Blocks all negative random events for the player"},
    "rainmaker":         {"name": "Rainmaker",                "desc": "Randomly triggers bonus income events worth $2,000–$10,000"},
    "polymath":          {"name": "Polymath",                 "desc": "Contributes bonuses across two additional job categories"},
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

        exec_bonus = 0.0
        for key in ability_keys:
            adef = EXEC_ABILITIES.get(key)
            if not adef:
                continue
            if adef["effect"] != effect:
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

    # Apply corp_synergy global boost (business executives)
    for ex in executives:
        for key in (ex.abilities or "").split(","):
            if key == "corp_synergy":
                adef = EXEC_ABILITIES.get("corp_synergy")
                if adef:
                    total *= (1.0 + adef["value"])
                    break

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


def get_school_discount(db, player_id: int) -> float:
    """Combined school cost/time discount from process_reeng + retention_bonus abilities."""
    d = (get_specific_ability_bonus(db, player_id, "process_reeng") +
         get_specific_ability_bonus(db, player_id, "retention_bonus"))
    return min(d, 0.75)


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
    job        = random.choice(list(EXECUTIVE_JOBS.keys()))

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
    if player.cash_balance < hiring_fee:
        return {"success": False, "error": f"Insufficient funds. Hiring fee: ${hiring_fee:,.2f}"}

    player.cash_balance     -= hiring_fee
    exec_obj.player_id       = player_id
    exec_obj.on_marketplace  = False
    exec_obj.hired_at        = datetime.utcnow()
    exec_obj.fired_at        = None
    exec_obj.is_retired      = False
    exec_obj.missed_payments = 0
    exec_obj.marketplace_reason = None
    db.commit()

    job_info = EXECUTIVE_JOBS.get(exec_obj.job, {})
    return {
        "success": True,
        "message": f"Hired {exec_obj.first_name} {exec_obj.last_name} as {job_info.get('title', exec_obj.job)}",
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

    # Severance deducted immediately
    if player and severance > 0:
        player.cash_balance -= severance

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
    if exec_obj.level >= 7:
        return {"success": False, "error": "Executive is at maximum level (7)"}

    target_level = exec_obj.level + 1
    cost  = SCHOOL_BASE_COST * target_level
    ticks = SCHOOL_BASE_TICKS * target_level

    school_discount = get_school_discount(db, player_id)
    cost  *= max(0.20, 1.0 - school_discount)
    ticks  = int(ticks * max(0.20, 1.0 - school_discount))

    if exec_obj.is_special and exec_obj.special_ability == "fast_learner":
        ticks = ticks // 2

    if player.cash_balance < cost:
        return {"success": False, "error": f"Insufficient funds. School costs ${cost:,.2f}"}

    player.cash_balance             -= cost
    exec_obj.is_in_school            = True
    exec_obj.school_ticks_remaining  = ticks
    exec_obj.school_total_ticks      = ticks
    exec_obj.school_cost_remaining   = 0.0
    db.commit()

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

    # Wage: school graduation = +15% raise, then apply any wage modifier
    exec_obj.wage = round(exec_obj.wage * (1.0 + WAGE_RAISE_ON_SCHOOL) * upgrade["wage_mod"], 2)
    if exec_obj.wage < 0.01:
        exec_obj.wage = 0.01

    db.commit()

    return {
        "success": True,
        "message": (f"{exec_obj.first_name} {exec_obj.last_name} graduated to level {exec_obj.level}! "
                    f"Upgrade: {upgrade['name']}.")
    }


# ==========================
# TICK PROCESSING
# ==========================

async def tick(current_tick: int, now: datetime):
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
    for ex in living:
        ex.age_tick_accumulator += 1

        ticks_needed = TICKS_PER_YEAR
        if ex.is_special and ex.special_ability == "eternal_youth":
            ticks_needed = int(TICKS_PER_YEAR * 2)  # ages half speed

        if ex.age_tick_accumulator < ticks_needed:
            continue

        ex.age_tick_accumulator = 0
        ex.current_age         += 1

        # ── 7.85% automatic pay raise every birthday ──────────────────────────
        ex.wage = round(ex.wage * (1.0 + WAGE_RAISE_ON_AGEUP), 2)

        # Death check
        if ex.current_age >= ex.max_age:
            ex.is_dead       = True
            ex.on_marketplace = False
            if ex.player_id is not None:
                print(f"[Executive] {ex.first_name} {ex.last_name} has passed away at age {ex.current_age}.")
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


def _quit_for_nonpayment(db, ex: Executive, player):
    """
    Executive quits instantly due to missed wage payment.
    Player owes: immediate severance (2 months) + ongoing pension (1 month).
    Executive re-enters the marketplace.
    """
    cycle_ticks = PAY_CYCLES[ex.pay_cycle]
    pension     = ex.wage * (PENSION_DURATION_TICKS       / cycle_ticks)
    severance   = ex.wage * (PENSION_DURATION_TICKS * 2.0 / cycle_ticks)

    # Severance deducted immediately (can push balance negative)
    player.cash_balance -= severance

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


def _process_wages(db, current_tick: int):
    from auth import Player
    employed = db.query(Executive).filter(
        Executive.player_id != None,
        Executive.is_dead    == False,
        Executive.is_retired == False,
    ).all()

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

        if player.cash_balance < wage:
            # ── Can't pay ─────────────────────────────────────────────────────
            if ex.is_special and ex.special_ability == "iron_will":
                # Issues a formal warning instead of quitting
                ex.missed_payments += 1
                print(f"[Executive] {ex.first_name} {ex.last_name} (Iron Will) issues formal "
                      f"warning #{ex.missed_payments} — payment missed but will not quit.")
            else:
                _quit_for_nonpayment(db, ex, player)
        else:
            # ── Normal payment ────────────────────────────────────────────────
            player.cash_balance -= wage
            ex.missed_payments   = 0  # reset on successful pay


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
                player.cash_balance -= payment

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
    migrations = [
        "ALTER TABLE executives ADD COLUMN abilities TEXT DEFAULT ''",
        "ALTER TABLE executives ADD COLUMN school_total_ticks INTEGER DEFAULT 0",
        "ALTER TABLE executives ADD COLUMN missed_payments INTEGER DEFAULT 0",
        "ALTER TABLE executives ADD COLUMN pension_owed_by INTEGER",
        "ALTER TABLE executives ADD COLUMN severance_owed REAL DEFAULT 0.0",
        "ALTER TABLE executives ADD COLUMN severance_owed_by INTEGER",
    ]
    with engine.connect() as conn:
        for stmt in migrations:
            try:
                conn.execute(text(stmt))
                conn.commit()
            except Exception:
                pass  # column already exists

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
