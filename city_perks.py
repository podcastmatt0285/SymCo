"""
City Perks — Wadsworth Pro subscriber perk (City Perk "option B").

The City Perk is a one-time subscriber redemption with two mutually exclusive paths:
  • Option A — found a free city + become its mayor (see cities.create_free_city).
  • Option B — pick up to MAX_PERKS city-wide perks from PERK_CATALOG below.

Option B perks are stored ON THE PLAYER (auth.players.city_perks JSON), not on a city.
They are city-wide and "travel" with the subscriber:
  • Active for whatever city the subscriber currently belongs to (member or mayor).
  • Dormant while the subscriber has no city.
  • Auto-apply when the subscriber later joins or founds a city.

A city's total perk effect = the SUM of the chosen perks of EVERY subscriber-member.
So a perk a subscriber picks benefits all members of their city (including the mayor),
which is exactly the "perks for your city" intent — and works whether the subscriber
owns the city or joined someone else's.

The aggregation is wired into city_projects.py at three single hook points so the perks
are real (not cosmetic):
  • get_city_production_buffs()  — output / wage / input / cycle / market-fee /
                                   construction / loan / license / sales-tax dimensions
  • get_effective_max_members()  — member_slots dimension
  • get_city_sales_tax_rate()    — sales_tax dimension (reduction)

Every perk effect uses the SAME dimension names the city-project buff engine already
aggregates, so folding them in is a simple additive step.

Effect dimensions (matching city_projects buff/debuff keys):
  output              additive to output bonus     (+ = more production output)
  wage_savings        additive wage reduction       (+ = cheaper wages)
  input_savings       additive input reduction      (+ = fewer input materials)
  cycle_speed         additive cycle speed-up        (+ = faster business cycles)
  market_fee_reduction additive market-fee cut       (+ = cheaper market fees)
  construction_speed  additive build speed-up        (+ = faster city projects)
  loan_interest_reduction additive loan-rate cut      (+ = cheaper member loans)
  license_production  flat extra licenses / tick     (added to city base)
  sales_tax_reduction flat city sales-tax cut         (+ = lower member trade tax)
  member_slots        flat extra member capacity     (added to city cap)
  wage_penalty        additive wage INCREASE (tradeoff perks)
  input_penalty       additive input INCREASE (tradeoff perks)
"""

import json
import time
from typing import Dict, List

MAX_PERKS = 3  # subscriber may pick up to this many perks (Option B)

# Short-TTL cache for get_city_perk_buffs — it sits on the production hot path
# (called per-business per-tick). Perk selections are one-time/permanent, so a
# 30s cache is safe and removes nearly all DB load. Invalidated on commit.
_PERK_BUFF_CACHE: Dict[int, tuple] = {}   # city_id → (expires_at, buffs_dict)
_PERK_BUFF_TTL = 30.0

# ──────────────────────────────────────────────────────────────────────────────
# PERK CATALOG
# Each entry: key → {icon, name, desc, effects{dimension: value}}
# Magnitudes are deliberately moderate: comparable to a few city-project levels,
# so 3 stacked perks meaningfully help a city without dwarfing the project system.
# ──────────────────────────────────────────────────────────────────────────────
PERK_CATALOG: Dict[str, dict] = {
    # ── Production output ──────────────────────────────────────────────────────
    "industrial_charter": {
        "icon": "🏭", "name": "Industrial Charter",
        "desc": "+5% production output for every business in the city.",
        "effects": {"output": 0.05},
    },
    "overdrive_mandate": {
        "icon": "⚡", "name": "Overdrive Mandate",
        "desc": "+9% output, but +3% wage cost — push the throttle.",
        "effects": {"output": 0.09, "wage_penalty": 0.03},
    },
    "artisan_guild": {
        "icon": "🎨", "name": "Artisan Guild",
        "desc": "+4% output and +3% faster business cycles.",
        "effects": {"output": 0.04, "cycle_speed": 0.03},
    },
    # ── Labor / wages ──────────────────────────────────────────────────────────
    "labor_accord": {
        "icon": "🤝", "name": "Labor Accord",
        "desc": "−6% wage costs city-wide.",
        "effects": {"wage_savings": 0.06},
    },
    "union_pact": {
        "icon": "✊", "name": "Union Pact",
        "desc": "−4% wages and −3% input materials.",
        "effects": {"wage_savings": 0.04, "input_savings": 0.03},
    },
    # ── Inputs / procurement ───────────────────────────────────────────────────
    "bulk_procurement": {
        "icon": "📦", "name": "Bulk Procurement",
        "desc": "−6% input materials on every production line.",
        "effects": {"input_savings": 0.06},
    },
    "supply_chain_mastery": {
        "icon": "🔗", "name": "Supply Chain Mastery",
        "desc": "−4% inputs and +4% faster cycles.",
        "effects": {"input_savings": 0.04, "cycle_speed": 0.04},
    },
    # ── Cycle speed ────────────────────────────────────────────────────────────
    "assembly_optimization": {
        "icon": "⚙️", "name": "Assembly Optimization",
        "desc": "+7% faster business production cycles.",
        "effects": {"cycle_speed": 0.07},
    },
    "night_shift": {
        "icon": "🌙", "name": "Night Shift",
        "desc": "+11% faster cycles, but +3% wage cost.",
        "effects": {"cycle_speed": 0.11, "wage_penalty": 0.03},
    },
    # ── Market fees ────────────────────────────────────────────────────────────
    "merchant_guild": {
        "icon": "🏪", "name": "Merchant Guild",
        "desc": "−5% market fees on all member trades.",
        "effects": {"market_fee_reduction": 0.05},
    },
    "free_trade_zone": {
        "icon": "🚢", "name": "Free Trade Zone",
        "desc": "−8% market fees city-wide.",
        "effects": {"market_fee_reduction": 0.08},
    },
    "trade_hub": {
        "icon": "🌐", "name": "Trade Hub",
        "desc": "−4% market fees and +3% output.",
        "effects": {"market_fee_reduction": 0.04, "output": 0.03},
    },
    # ── Finance / loans ────────────────────────────────────────────────────────
    "credit_union": {
        "icon": "🏦", "name": "Credit Union",
        "desc": "−6% interest on member business loans.",
        "effects": {"loan_interest_reduction": 0.06},
    },
    "investment_charter": {
        "icon": "📈", "name": "Investment Charter",
        "desc": "−4% loan interest and −4% market fees.",
        "effects": {"loan_interest_reduction": 0.04, "market_fee_reduction": 0.04},
    },
    # ── City sales tax (member-trade tax) ──────────────────────────────────────
    "tax_haven": {
        "icon": "🏝️", "name": "Tax Haven",
        "desc": "−1.5% city sales tax on member-to-member trades.",
        "effects": {"sales_tax_reduction": 0.015},
    },
    "duty_free_charter": {
        "icon": "🎫", "name": "Duty-Free Charter",
        "desc": "−2.5% city sales tax city-wide.",
        "effects": {"sales_tax_reduction": 0.025},
    },
    # ── Licenses / construction ────────────────────────────────────────────────
    "permit_office_boost": {
        "icon": "📋", "name": "Permit Office Boost",
        "desc": "+3 construction licenses generated per tick.",
        "effects": {"license_production": 3.0},
    },
    "fast_track_permits": {
        "icon": "🏗️", "name": "Fast-Track Permits",
        "desc": "+9% faster city-project construction.",
        "effects": {"construction_speed": 0.09},
    },
    "civic_works": {
        "icon": "🚧", "name": "Civic Works",
        "desc": "+5% construction speed and +1.5 licenses/tick.",
        "effects": {"construction_speed": 0.05, "license_production": 1.5},
    },
    # ── Member capacity ────────────────────────────────────────────────────────
    "welcome_center": {
        "icon": "🪧", "name": "Welcome Center",
        "desc": "+3 member slots for the city.",
        "effects": {"member_slots": 3.0},
    },
    "metropolitan_expansion": {
        "icon": "🏙️", "name": "Metropolitan Expansion",
        "desc": "+6 member slots for the city.",
        "effects": {"member_slots": 6.0},
    },
    # ── Balanced / generalist ──────────────────────────────────────────────────
    "founders_blessing": {
        "icon": "🌟", "name": "Founder's Blessing",
        "desc": "+3% output, −3% wages, −3% inputs — a little of everything.",
        "effects": {"output": 0.03, "wage_savings": 0.03, "input_savings": 0.03},
    },
    "boomtown_charter": {
        "icon": "💥", "name": "Boomtown Charter",
        "desc": "+5% cycle speed, −3% market fees, +2 member slots.",
        "effects": {"cycle_speed": 0.05, "market_fee_reduction": 0.03, "member_slots": 2.0},
    },
    "green_initiative": {
        "icon": "🌱", "name": "Green Initiative",
        "desc": "−5% inputs and −1% city sales tax.",
        "effects": {"input_savings": 0.05, "sales_tax_reduction": 0.01},
    },
    "logistics_network": {
        "icon": "🚚", "name": "Logistics Network",
        "desc": "−4% inputs, −2% market fees, +3% cycle speed.",
        "effects": {"input_savings": 0.04, "market_fee_reduction": 0.02, "cycle_speed": 0.03},
    },
}

# All dimensions a perk may contribute to (used for safe aggregation).
_PERK_DIMENSIONS = (
    "output", "wage_savings", "input_savings", "cycle_speed",
    "market_fee_reduction", "construction_speed", "loan_interest_reduction",
    "license_production", "sales_tax_reduction", "member_slots",
    "wage_penalty", "input_penalty",
)


def is_valid_perk(key: str) -> bool:
    return key in PERK_CATALOG


def parse_player_perks(raw) -> List[str]:
    """Parse a player's stored city_perks JSON into a validated list of perk keys."""
    if not raw:
        return []
    try:
        keys = json.loads(raw) if isinstance(raw, str) else list(raw)
    except Exception:
        return []
    return [k for k in keys if isinstance(k, str) and k in PERK_CATALOG][:MAX_PERKS]


def serialize_perks(keys: List[str]) -> str:
    """Validate + dedupe + cap a perk-key list and return JSON for storage."""
    seen = []
    for k in keys:
        if k in PERK_CATALOG and k not in seen:
            seen.append(k)
        if len(seen) >= MAX_PERKS:
            break
    return json.dumps(seen)


def get_player_perk_state(player_id: int) -> dict:
    """Return {"choice": None|"free_city"|"perks", "perks": [keys]} for a player."""
    try:
        from auth import Player, get_db as get_auth_db
        adb = get_auth_db()
        try:
            row = adb.query(Player.city_perk_choice, Player.city_perks).filter(
                Player.id == player_id
            ).first()
        finally:
            adb.close()
        if not row:
            return {"choice": None, "perks": []}
        return {"choice": row[0], "perks": parse_player_perks(row[1])}
    except Exception as e:
        print(f"[CityPerks] get_player_perk_state error (player {player_id}): {e}")
        return {"choice": None, "perks": []}


def set_player_perk_choice(player_id: int, choice: str, perks: List[str] = None) -> None:
    """Persist a player's one-time City Perk redemption (choice + optional perk list)."""
    from auth import Player, get_db as get_auth_db
    adb = get_auth_db()
    try:
        p = adb.query(Player).filter(Player.id == player_id).first()
        if not p:
            return
        p.city_perk_choice = choice
        if perks is not None:
            p.city_perks = serialize_perks(perks)
        adb.commit()
        _PERK_BUFF_CACHE.clear()   # selection changed → drop cached city totals
    except Exception as e:
        adb.rollback()
        print(f"[CityPerks] set_player_perk_choice error (player {player_id}): {e}")
    finally:
        adb.close()


def get_city_perk_buffs(city_id: int) -> Dict[str, float]:
    """
    Aggregate the city-wide perk effects for a city: the SUM of every
    subscriber-member's chosen perks, grouped by effect dimension.

    Returns a dict with every key in _PERK_DIMENSIONS (0.0 when unused).
    Safe to call for any city; returns all-zero if the city has no
    perk-bearing members or on any error.
    """
    totals = {dim: 0.0 for dim in _PERK_DIMENSIONS}
    if not city_id:
        return totals
    cached = _PERK_BUFF_CACHE.get(city_id)
    if cached and cached[0] > time.time():
        return dict(cached[1])
    try:
        from cities import CityMember, get_db as get_city_db
        from auth import Player, get_db as get_auth_db

        cdb = get_city_db()
        try:
            member_ids = [
                m.player_id for m in cdb.query(CityMember).filter(
                    CityMember.city_id == city_id
                ).all()
            ]
        finally:
            cdb.close()

        if not member_ids:
            return totals

        adb = get_auth_db()
        try:
            rows = adb.query(Player.city_perks).filter(
                Player.id.in_(member_ids),
                Player.city_perks.isnot(None),
            ).all()
        finally:
            adb.close()

        for (raw,) in rows:
            for key in parse_player_perks(raw):
                for dim, val in PERK_CATALOG[key]["effects"].items():
                    if dim in totals:
                        totals[dim] += val
        _PERK_BUFF_CACHE[city_id] = (time.time() + _PERK_BUFF_TTL, dict(totals))
        return totals
    except Exception as e:
        print(f"[CityPerks] get_city_perk_buffs error (city {city_id}): {e}")
        return totals
