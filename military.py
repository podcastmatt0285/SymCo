"""
military.py

Branch Warfare system for the Port Authority — a deterministic, dice-based
military combat layer that replaces the old RNG coin-flip mission system.

Players raise four Branches of units (Navy, Army, Air Force, Intelligence),
move them into Port Authority *command* (the existing PortAuthorityInventory
depot, where they incur daily upkeep), and fight one-unit-at-a-time battles:

  • PROCUREMENT — an admin-run event in which attackers pick 3 targets and
    fight one battle per week, looting a slice of each defeated defender's
    inventory proportional to their surviving attack power.
  • BLOCKADES  — player-initiated anytime; the deployer DEFENDS, the blockaded
    party must defeat them within 72h or pay a trophy tribute. While active,
    the blockaded player cannot trade on retail / market / district markets.
  • ESPIONAGE  — spend Intelligence units (drones) to "go dark" and hide from
    a specific rival's target search for up to a week.

Combat (chosen by design, do not change):
  • d20 dice. Each exchange, attacker rolls (current ATTACK) d20s, defender
    rolls (current DEFENSE) d20s; compare each side's single highest die.
  • Attacker wins ties. Loser's unit takes damage = max(1, |high diff|) when
    the attacker wins (a tie still chips 1), else defender_high - attacker_high.
  • A unit's HP *is* the stat in play (attack when attacking, defense when
    defending): damage erodes it, so it rolls fewer dice as it weakens; at 0
    it dies and is permanently deleted from PA command.
  • Strongest-first: each side fields its strongest remaining unit; on death
    the next strongest steps in. Battle ends when one side has no units left.
"""

import json
import random
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, Index
from sqlalchemy.ext.declarative import declarative_base

from database import engine, SessionLocal

# Reuse the Port Authority depot + item taxonomy (no circular import: PA does
# not import military).
from port_authority import (
    CARRIERS, SUBMARINES, DESTROYERS, FIGHTER_JETS, HELICOPTERS,
    TANKS, ARMORED_VEHICLES, RIFLES, DRONES, ALL_PA_ITEMS,
    PortAuthorityInstance, PortAuthorityInventory,
    _get_pa_inventory, _pa_remove_item,
)

Base = declarative_base()

# ─────────────────────────────────────────────────────────────────────────────
# Branch taxonomy + unit stats
# ─────────────────────────────────────────────────────────────────────────────

# category name → (frozenset of slugs)
CATEGORY_SETS: Dict[str, frozenset] = {
    "carriers": CARRIERS, "submarines": SUBMARINES, "destroyers": DESTROYERS,
    "fighter_jets": FIGHTER_JETS, "helicopters": HELICOPTERS,
    "tanks": TANKS, "armored_vehicles": ARMORED_VEHICLES, "rifles": RIFLES,
    "drones": DRONES,
}

# branch → list of category names
BRANCHES: Dict[str, List[str]] = {
    "navy":         ["carriers", "submarines", "destroyers"],
    "army":         ["tanks", "armored_vehicles", "rifles"],
    "air_force":    ["fighter_jets", "helicopters"],
    "intelligence": ["drones"],
}
BRANCH_LABELS = {"navy": "Navy", "army": "Army",
                 "air_force": "Air Force", "intelligence": "Intelligence"}

# category → (ATTACK, DEFENSE)
UNIT_STATS: Dict[str, Tuple[int, int]] = {
    "carriers":         (20, 20),
    "submarines":       (17, 16),
    "destroyers":       (14, 13),
    "fighter_jets":     (13, 9),
    "helicopters":      (10, 8),
    "tanks":            (9, 12),
    "armored_vehicles": (6, 10),
    "drones":           (5, 4),
    "rifles":           (2, 2),
}

# Reverse maps, built once at import.
CATEGORY_OF: Dict[str, str] = {}
BRANCH_OF_CATEGORY: Dict[str, str] = {}
for _br, _cats in BRANCHES.items():
    for _cat in _cats:
        BRANCH_OF_CATEGORY[_cat] = _br
        for _slug in CATEGORY_SETS[_cat]:
            CATEGORY_OF[_slug] = _cat


def category_of(slug: str) -> Optional[str]:
    return CATEGORY_OF.get(slug)


def branch_of(slug: str) -> Optional[str]:
    cat = CATEGORY_OF.get(slug)
    return BRANCH_OF_CATEGORY.get(cat) if cat else None


def unit_attack(slug: str) -> int:
    cat = CATEGORY_OF.get(slug)
    return UNIT_STATS[cat][0] if cat else 0


def unit_defense(slug: str) -> int:
    cat = CATEGORY_OF.get(slug)
    return UNIT_STATS[cat][1] if cat else 0


# Tunables
MAX_ROUNDS        = 200_000     # safety cap (the 1-HP tie chip already guarantees progress)
MAX_UNITS_PER_SIDE = 5_000      # performance guard — strongest units kept
BLOCKADE_HOURS    = 72
GO_DARK_DAYS      = 7
SECURITY_BAN_DAYS = 60
DEFAULT_BATTLE_HOURS = 168      # 1 week between procurement battles
WIPE_TROPHY_PENALTY  = 200      # steep penalty if attacker is wiped mid-campaign
BLOCKADE_TRIBUTE     = 25       # light tribute if the blockaded party fails to lift in time


# ─────────────────────────────────────────────────────────────────────────────
# DB Models
# ─────────────────────────────────────────────────────────────────────────────

class MilitaryEvent(Base):
    """Admin-created Procurement Event configuration."""
    __tablename__ = "military_events"

    id                  = Column(Integer, primary_key=True)
    kind                = Column(String, default="procurement")   # "procurement"
    title               = Column(String, nullable=False)
    status              = Column(String, default="open", index=True)  # open|running|finished
    branches_allowed    = Column(Text, default="[]")              # JSON list of branch keys
    max_branch_strength = Column(Integer, default=0)              # 0 = uncapped
    loot_fraction       = Column(Float, default=0.10)             # of defender's lootable inventory
    trophy_penalty      = Column(Integer, default=WIPE_TROPHY_PENALTY)
    battle_hours        = Column(Integer, default=DEFAULT_BATTLE_HOURS)
    opens_at            = Column(DateTime, default=datetime.utcnow)
    starts_at           = Column(DateTime, default=datetime.utcnow)
    created_by          = Column(Integer, nullable=True)
    created_at          = Column(DateTime, default=datetime.utcnow)


class MilitaryCampaign(Base):
    """One attacker's 3-target procurement run."""
    __tablename__ = "military_campaigns"

    id                    = Column(Integer, primary_key=True)
    event_id              = Column(Integer, index=True, nullable=False)
    attacker_id           = Column(Integer, index=True, nullable=False)
    targets_json          = Column(Text, default="[]")     # ordered list of 3 player ids
    current_index         = Column(Integer, default=0)
    status                = Column(String, default="committed", index=True)  # committed|in_battle|complete|wiped
    committed_force       = Column(Text, default="{}")     # {slug: qty} surviving committed snapshot
    original_attack_power = Column(Integer, default=0)
    total_loot_json       = Column(Text, default="{}")     # {defender_id: {slug: qty}} for wipe-reversal
    next_battle_at        = Column(DateTime, index=True)
    created_at            = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (Index("ix_mil_campaign_attacker", "event_id", "attacker_id"),)


class MilitaryBattle(Base):
    """One attacker-vs-defender fight + result."""
    __tablename__ = "military_battles"

    id                       = Column(Integer, primary_key=True)
    campaign_id              = Column(Integer, index=True, nullable=True)  # null for blockade breaks
    kind                     = Column(String, default="procurement")
    attacker_id              = Column(Integer, index=True, nullable=False)
    defender_id              = Column(Integer, index=True, nullable=False)
    target_slot              = Column(Integer, default=0)
    scheduled_at             = Column(DateTime, default=datetime.utcnow)
    resolved_at              = Column(DateTime, nullable=True)
    winner                   = Column(String, nullable=True)  # attacker|defender|draw
    rounds                   = Column(Integer, default=0)
    attacker_losses          = Column(Text, default="{}")
    defender_losses          = Column(Text, default="{}")
    attacker_survivors_power = Column(Integer, default=0)
    loot_json                = Column(Text, default="{}")
    summary_json             = Column(Text, default="{}")


class Blockade(Base):
    """Player-initiated commerce blockade (deployer DEFENDS)."""
    __tablename__ = "military_blockades"

    id              = Column(Integer, primary_key=True)
    deployer_id     = Column(Integer, index=True, nullable=False)  # the defender
    target_id       = Column(Integer, index=True, nullable=False)  # the blocked party / attacker
    committed_force = Column(Text, default="{}")                   # deployer's defending snapshot
    status          = Column(String, default="active", index=True)  # active|lifted|expired
    created_at      = Column(DateTime, default=datetime.utcnow)
    expires_at      = Column(DateTime, index=True)
    lifted_at       = Column(DateTime, nullable=True)
    __table_args__ = (Index("ix_blockade_target_status", "target_id", "status"),)


class GoDarkRecord(Base):
    """Espionage hide — hider invisible to `hidden_from`'s target search."""
    __tablename__ = "military_go_dark"

    id              = Column(Integer, primary_key=True)
    hider_id        = Column(Integer, index=True, nullable=False)
    hidden_from     = Column(Integer, index=True, nullable=False)
    drones_committed = Column(Integer, default=0)
    status          = Column(String, default="active", index=True)
    created_at      = Column(DateTime, default=datetime.utcnow)
    expires_at      = Column(DateTime, index=True)


class SecurityBan(Base):
    """60-day ban on raising/using a security force after a campaign wipe."""
    __tablename__ = "military_security_bans"

    id         = Column(Integer, primary_key=True)
    player_id  = Column(Integer, index=True, nullable=False)
    reason     = Column(String, nullable=True)
    status     = Column(String, default="active", index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, index=True)


def init_db():
    Base.metadata.create_all(bind=engine)


# ─────────────────────────────────────────────────────────────────────────────
# Notifications + trophies (reuse shared systems)
# ─────────────────────────────────────────────────────────────────────────────

def _notify(player_id: int, title: str, body: str, url: str = "/port-authority"):
    """Push alert + persistent in-game banner (long battle summaries OK)."""
    if not player_id or player_id <= 0:
        return
    try:
        from push_ux import send_push_notification
        send_push_notification(player_id, title, body, url,
                               notif_type="institutions", tag="military")
    except Exception as e:
        print(f"[Military] push error: {e}")
    try:
        from push_ux import create_game_notification
        create_game_notification(player_id, title, body, url, notif_type="institutions")
    except Exception as e:
        print(f"[Military] banner error: {e}")


def _recompute_level(trophies: int) -> int:
    try:
        from events import LEVEL_THRESHOLDS
    except Exception:
        return 1
    level = 1
    for i, threshold in enumerate(LEVEL_THRESHOLDS):
        if trophies >= threshold:
            level = i + 2
        else:
            break
    return level


def adjust_trophies(player_id: int, delta: int) -> int:
    """Add (or subtract, clamped at 0) trophies. Returns the actual delta applied."""
    if not player_id or player_id <= 0 or delta == 0:
        return 0
    try:
        from events import PlayerRank
    except Exception:
        return 0
    db = SessionLocal()
    try:
        rank = db.query(PlayerRank).filter(PlayerRank.player_id == player_id).first()
        if not rank:
            rank = PlayerRank(player_id=player_id, trophies=0, level=1)
            db.add(rank)
        cur = rank.trophies or 0
        new = max(0, cur + delta)
        applied = new - cur
        rank.trophies = new
        rank.level = _recompute_level(new)
        rank.updated_at = datetime.utcnow()
        db.commit()
        return applied
    except Exception as e:
        db.rollback()
        print(f"[Military] trophy adjust error: {e}")
        return 0
    finally:
        db.close()


def get_trophies(player_id: int) -> int:
    try:
        from events import PlayerRank
    except Exception:
        return 0
    db = SessionLocal()
    try:
        rank = db.query(PlayerRank).filter(PlayerRank.player_id == player_id).first()
        return (rank.trophies or 0) if rank else 0
    except Exception:
        return 0
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# Force assembly + battle engine (pure / deterministic)
# ─────────────────────────────────────────────────────────────────────────────

def _max_d20(n: int, rng: random.Random) -> int:
    """Highest of n d20 rolls, sampled analytically (O(20), independent of n)."""
    if n <= 0:
        return 0
    u = rng.random()
    # P(max <= k) = (k/20)^n ; return smallest k with that >= u
    for k in range(1, 21):
        if (k / 20.0) ** n >= u:
            return k
    return 20


def assemble_force(force_qty: Dict[str, float], allowed_branches: List[str],
                   max_branch_strength: int, role: str) -> List[dict]:
    """Expand {slug: qty} into individual unit dicts for the given role.

    role: "attacker" (HP/dice = ATTACK) or "defender" (HP/dice = DEFENSE).
    Filters to allowed branches and greedily caps per-branch power if set.
    Keeps the strongest units up to MAX_UNITS_PER_SIDE.
    """
    expanded: List[Tuple[int, str, str, str]] = []  # (stat, slug, cat, branch)
    for slug, qty in force_qty.items():
        cat = CATEGORY_OF.get(slug)
        if not cat:
            continue
        branch = BRANCH_OF_CATEGORY.get(cat)
        if allowed_branches and branch not in allowed_branches:
            continue
        stat = UNIT_STATS[cat][0 if role == "attacker" else 1]
        n = int(qty)
        for _ in range(n):
            expanded.append((stat, slug, cat, branch))
    expanded.sort(reverse=True)   # strongest first
    units: List[dict] = []
    per_branch = defaultdict(int)
    for stat, slug, cat, branch in expanded:
        if max_branch_strength and per_branch[branch] + stat > max_branch_strength:
            continue
        per_branch[branch] += stat
        units.append({"slug": slug, "cat": cat, "stat": stat, "branch": branch})
        if len(units) >= MAX_UNITS_PER_SIDE:
            break
    return units


def resolve_battle(att_units: List[dict], def_units: List[dict], seed: int) -> dict:
    """Run the full deterministic battle. Returns a result dict."""
    rng = random.Random(seed)
    att = sorted(att_units, key=lambda u: u["stat"], reverse=True)
    dfn = sorted(def_units, key=lambda u: u["stat"], reverse=True)

    a_losses: Dict[str, int] = defaultdict(int)
    d_losses: Dict[str, int] = defaultdict(int)
    log: List[dict] = []
    rounds = 0

    ai = di = 0
    a_hp = att[ai]["stat"] if att else 0
    d_hp = dfn[di]["stat"] if dfn else 0

    while ai < len(att) and di < len(dfn) and rounds < MAX_ROUNDS:
        rounds += 1
        ah = _max_d20(a_hp, rng)
        dh = _max_d20(d_hp, rng)
        if ah >= dh:                       # attacker wins ties
            dmg = max(1, ah - dh)
            d_hp -= dmg
            if d_hp <= 0:
                d_losses[dfn[di]["slug"]] += 1
                di += 1
                if di < len(dfn):
                    d_hp = dfn[di]["stat"]
        else:
            dmg = dh - ah
            a_hp -= dmg
            if a_hp <= 0:
                a_losses[att[ai]["slug"]] += 1
                ai += 1
                if ai < len(att):
                    a_hp = att[ai]["stat"]
        if len(log) < 40:
            log.append({"r": rounds, "ah": ah, "dh": dh, "dmg": dmg})

    att_emptied = ai >= len(att)
    def_emptied = di >= len(dfn)
    if def_emptied and not att_emptied:
        winner = "attacker"
    elif att_emptied and not def_emptied:
        winner = "defender"
    else:
        # MAX_ROUNDS hit (or both empty) — decide by remaining power, deterministic.
        a_remain = (a_hp if ai < len(att) else 0) + sum(u["stat"] for u in att[ai + 1:])
        d_remain = (d_hp if di < len(dfn) else 0) + sum(u["stat"] for u in dfn[di + 1:])
        winner = "attacker" if a_remain >= d_remain else "defender"

    # Surviving attacker attack power: damaged front unit at current hp + full rest.
    surviving_power = (a_hp if ai < len(att) else 0) + sum(u["stat"] for u in att[ai + 1:])

    return {
        "winner": winner,
        "rounds": rounds,
        "attacker_losses": dict(a_losses),
        "defender_losses": dict(d_losses),
        "attacker_survivors_power": max(0, surviving_power),
        "log": log,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Force / commitment helpers
# ─────────────────────────────────────────────────────────────────────────────

def _pa_for(db, player_id: int) -> Optional[PortAuthorityInstance]:
    return db.query(PortAuthorityInstance).filter_by(owner_id=player_id).first()


def _active_commitments(db, player_id: int) -> Dict[str, float]:
    """Sum of all units this player has committed to active campaigns/blockades."""
    committed: Dict[str, float] = defaultdict(float)
    camps = db.query(MilitaryCampaign).filter(
        MilitaryCampaign.attacker_id == player_id,
        MilitaryCampaign.status.in_(["committed", "in_battle"]),
    ).all()
    for c in camps:
        for slug, qty in json.loads(c.committed_force or "{}").items():
            committed[slug] += qty
    blocks = db.query(Blockade).filter(
        Blockade.deployer_id == player_id,
        Blockade.status == "active",
    ).all()
    for b in blocks:
        for slug, qty in json.loads(b.committed_force or "{}").items():
            committed[slug] += qty
    return committed


def available_home_force(player_id: int) -> Dict[str, float]:
    """PA-command inventory minus units already committed elsewhere."""
    db = SessionLocal()
    try:
        pa = _pa_for(db, player_id)
        if not pa:
            return {}
        inv = _get_pa_inventory(db, pa.id)
        committed = _active_commitments(db, player_id)
        out: Dict[str, float] = {}
        for slug, qty in inv.items():
            rem = qty - committed.get(slug, 0.0)
            if rem > 0 and slug in ALL_PA_ITEMS:
                out[slug] = rem
        return out
    finally:
        db.close()


def force_power(force_qty: Dict[str, float], role: str = "attacker") -> int:
    idx = 0 if role == "attacker" else 1
    total = 0
    for slug, qty in force_qty.items():
        cat = CATEGORY_OF.get(slug)
        if cat:
            total += UNIT_STATS[cat][idx] * int(qty)
    return total


def _select_force(requested: Dict[str, float], available: Dict[str, float],
                  allowed_branches: List[str]) -> Tuple[Dict[str, float], Optional[str]]:
    """Validate a requested force against availability + allowed branches."""
    chosen: Dict[str, float] = {}
    for slug, qty in (requested or {}).items():
        qty = int(qty)
        if qty <= 0:
            continue
        if slug not in ALL_PA_ITEMS:
            return {}, f"{slug} is not a military unit."
        br = branch_of(slug)
        if allowed_branches and br not in allowed_branches:
            return {}, f"{BRANCH_LABELS.get(br, br)} branch is not permitted in this event."
        if available.get(slug, 0) < qty:
            return {}, f"You only have {int(available.get(slug, 0))} × {slug} available at home."
        chosen[slug] = qty
    if not chosen:
        return {}, "Select at least one unit to commit."
    return chosen, None


# ─────────────────────────────────────────────────────────────────────────────
# Predicates (called from inventory / market / district / business)
# ─────────────────────────────────────────────────────────────────────────────

def is_player_blockaded(player_id: int) -> bool:
    """True if the player is currently under an active, unexpired blockade."""
    if not player_id or player_id <= 0:
        return False
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        row = db.query(Blockade.id).filter(
            Blockade.target_id == player_id,
            Blockade.status == "active",
            Blockade.expires_at > now,
        ).first()
        return row is not None
    except Exception:
        return False
    finally:
        db.close()


def is_security_banned(player_id: int) -> bool:
    if not player_id or player_id <= 0:
        return False
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        row = db.query(SecurityBan.id).filter(
            SecurityBan.player_id == player_id,
            SecurityBan.status == "active",
            SecurityBan.expires_at > now,
        ).first()
        return row is not None
    except Exception:
        return False
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# Loot
# ─────────────────────────────────────────────────────────────────────────────

def _lootable_inventory(player_id: int) -> Dict[str, float]:
    """Defender's personal goods eligible for looting (excludes military units)."""
    from inventory import get_player_inventory
    inv = get_player_inventory(player_id)
    return {slug: qty for slug, qty in inv.items()
            if slug not in ALL_PA_ITEMS and qty > 0}


def _apply_loot(attacker_id: int, defender_id: int, fraction: float,
                ratio: float) -> Dict[str, float]:
    """Transfer floor(qty * fraction * ratio) of each lootable stack. Returns taken."""
    from inventory import remove_item, add_item
    taken: Dict[str, float] = {}
    if fraction <= 0 or ratio <= 0:
        return taken
    for slug, qty in _lootable_inventory(defender_id).items():
        amt = int(qty * fraction * ratio)
        if amt <= 0:
            continue
        if remove_item(defender_id, slug, amt):
            add_item(attacker_id, slug, amt)
            taken[slug] = taken.get(slug, 0) + amt
    return taken


# ─────────────────────────────────────────────────────────────────────────────
# Battle execution (campaigns + blockade breaks)
# ─────────────────────────────────────────────────────────────────────────────

def _summary_text(kind: str, attacker_id: int, defender_id: int, res: dict,
                  loot: Dict[str, float]) -> str:
    def _fmt(d):
        return ", ".join(f"{v}× {k.replace('_', ' ')}" for k, v in d.items()) or "none"
    lines = [
        f"{kind.title()} battle vs player #{defender_id} — winner: {res['winner'].upper()}",
        f"Rounds fought: {res['rounds']}",
        f"Your losses: {_fmt(res['attacker_losses'])}",
        f"Enemy losses: {_fmt(res['defender_losses'])}",
    ]
    if loot:
        lines.append(f"Looted: {_fmt(loot)}")
    return "\n".join(lines)


def _run_battle(db, attacker_id: int, defender_id: int, attacker_force: Dict[str, float],
                event: Optional[MilitaryEvent], kind: str, campaign_id: Optional[int],
                target_slot: int) -> MilitaryBattle:
    """Assemble forces, resolve, apply losses + loot, persist, notify. Returns the battle row."""
    allowed = json.loads(event.branches_allowed) if event else list(BRANCHES.keys())
    cap = event.max_branch_strength if event else 0
    loot_fraction = event.loot_fraction if event else 0.0

    # Defender fights with whatever is at home (uncommitted) right now.
    def_home = available_home_force(defender_id)

    att_units = assemble_force(attacker_force, allowed, cap, "attacker")
    def_units = assemble_force(def_home, allowed, cap, "defender")

    # Create the battle row first so its id seeds the deterministic RNG.
    battle = MilitaryBattle(
        campaign_id=campaign_id, kind=kind, attacker_id=attacker_id,
        defender_id=defender_id, target_slot=target_slot,
        scheduled_at=datetime.utcnow(),
    )
    db.add(battle)
    db.flush()   # assigns battle.id

    if not att_units:
        res = {"winner": "defender", "rounds": 0, "attacker_losses": {},
               "defender_losses": {}, "attacker_survivors_power": 0, "log": []}
    elif not def_units:
        # Undefended target — automatic win, full survivor power.
        res = {"winner": "attacker", "rounds": 0, "attacker_losses": {},
               "defender_losses": {}, "log": [],
               "attacker_survivors_power": force_power(attacker_force, "attacker")}
    else:
        res = resolve_battle(att_units, def_units, seed=battle.id)

    # Apply unit deaths to both depots permanently.
    att_pa = _pa_for(db, attacker_id)
    def_pa = _pa_for(db, defender_id)
    if att_pa:
        for slug, qty in res["attacker_losses"].items():
            _pa_remove_item(db, att_pa.id, slug, qty)
    if def_pa:
        for slug, qty in res["defender_losses"].items():
            _pa_remove_item(db, def_pa.id, slug, qty)

    # Loot (procurement only, on attacker win with surviving power).
    loot: Dict[str, float] = {}
    if kind == "procurement" and res["winner"] == "attacker" and campaign_id:
        camp = db.query(MilitaryCampaign).filter_by(id=campaign_id).first()
        orig = camp.original_attack_power if camp else 0
        ratio = (res["attacker_survivors_power"] / orig) if orig > 0 else 0.0
        loot = _apply_loot(attacker_id, defender_id, loot_fraction, min(1.0, ratio))

    battle.resolved_at = datetime.utcnow()
    battle.winner = res["winner"]
    battle.rounds = res["rounds"]
    battle.attacker_losses = json.dumps(res["attacker_losses"])
    battle.defender_losses = json.dumps(res["defender_losses"])
    battle.attacker_survivors_power = res["attacker_survivors_power"]
    battle.loot_json = json.dumps(loot)
    battle.summary_json = json.dumps({**res, "loot": loot})

    # Notify both sides with a persistent summary.
    _notify(attacker_id, f"⚔️ Battle Report vs #{defender_id}",
            _summary_text(kind, attacker_id, defender_id, res, loot))
    enemy_res = dict(res)
    enemy_res["attacker_losses"], enemy_res["defender_losses"] = \
        res["defender_losses"], res["attacker_losses"]
    _notify(defender_id, f"🛡️ You were attacked by #{attacker_id}",
            _summary_text(kind, defender_id, attacker_id, enemy_res, {}))
    return battle


# ─────────────────────────────────────────────────────────────────────────────
# Procurement campaigns
# ─────────────────────────────────────────────────────────────────────────────

def get_active_event() -> Optional[MilitaryEvent]:
    db = SessionLocal()
    try:
        return db.query(MilitaryEvent).filter(
            MilitaryEvent.kind == "procurement",
            MilitaryEvent.status.in_(["open", "running"]),
        ).order_by(MilitaryEvent.id.desc()).first()
    finally:
        db.close()


def commit_campaign(attacker_id: int, target_ids: List[int],
                    force: Dict[str, float]) -> Tuple[bool, str]:
    if is_security_banned(attacker_id):
        return False, "Your security force is banned (post-wipe). Try again later."
    # Validate targets
    target_ids = [int(t) for t in (target_ids or []) if int(t) > 0]
    if len(target_ids) != 3:
        return False, "Select exactly 3 targets."
    if len(set(target_ids)) != 3:
        return False, "Targets must be distinct."
    if attacker_id in target_ids:
        return False, "You cannot target yourself."

    db = SessionLocal()
    try:
        event = db.query(MilitaryEvent).filter(
            MilitaryEvent.kind == "procurement",
            MilitaryEvent.status.in_(["open", "running"]),
        ).order_by(MilitaryEvent.id.desc()).first()
        if not event:
            return False, "There is no active Procurement Event."
        if not _pa_for(db, attacker_id):
            return False, "You do not own a Port Authority."
        existing = db.query(MilitaryCampaign).filter(
            MilitaryCampaign.event_id == event.id,
            MilitaryCampaign.attacker_id == attacker_id,
            MilitaryCampaign.status.in_(["committed", "in_battle"]),
        ).first()
        if existing:
            return False, "You already have an active campaign in this event."

        allowed = json.loads(event.branches_allowed or "[]")
        available = available_home_force(attacker_id)
        chosen, err = _select_force(force, available, allowed)
        if err:
            return False, err

        camp = MilitaryCampaign(
            event_id=event.id, attacker_id=attacker_id,
            targets_json=json.dumps(target_ids), current_index=0,
            status="committed", committed_force=json.dumps(chosen),
            original_attack_power=force_power(chosen, "attacker"),
            total_loot_json="{}",
            next_battle_at=datetime.utcnow() + timedelta(hours=event.battle_hours),
        )
        db.add(camp)
        if event.status == "open":
            event.status = "running"
        db.commit()
        return True, ("Campaign launched. First battle resolves in "
                      f"{event.battle_hours}h against target #{target_ids[0]}.")
    except Exception as e:
        db.rollback()
        return False, str(e)
    finally:
        db.close()


def _run_campaign_battle(db, camp: MilitaryCampaign, event: MilitaryEvent, now: datetime):
    targets = json.loads(camp.targets_json or "[]")
    if camp.current_index >= len(targets):
        _finalize_campaign(db, camp, wiped=False)
        return
    defender_id = int(targets[camp.current_index])
    attacker_force = json.loads(camp.committed_force or "{}")

    battle = _run_battle(db, camp.attacker_id, defender_id, attacker_force,
                         event, "procurement", camp.id, camp.current_index)

    # Shrink committed force by attacker losses (survivors carry to next battle).
    a_losses = json.loads(battle.attacker_losses or "{}")
    surviving = dict(attacker_force)
    for slug, qty in a_losses.items():
        surviving[slug] = max(0, surviving.get(slug, 0) - qty)
    surviving = {k: v for k, v in surviving.items() if v > 0}
    camp.committed_force = json.dumps(surviving)

    # Record loot for possible wipe-reversal.
    loot = json.loads(battle.loot_json or "{}")
    if loot:
        total = json.loads(camp.total_loot_json or "{}")
        bucket = total.setdefault(str(defender_id), {})
        for slug, qty in loot.items():
            bucket[slug] = bucket.get(slug, 0) + qty
        camp.total_loot_json = json.dumps(total)

    camp.current_index += 1

    if not surviving:                         # attacker wiped
        camp.status = "wiped"
        _finalize_campaign(db, camp, wiped=True)
    elif camp.current_index >= len(targets):  # made it home
        camp.status = "complete"
        _finalize_campaign(db, camp, wiped=False)
    else:
        camp.status = "in_battle"
        camp.next_battle_at = now + timedelta(hours=event.battle_hours)


def _finalize_campaign(db, camp: MilitaryCampaign, wiped: bool):
    if not wiped:
        _notify(camp.attacker_id, "🏁 Campaign Complete",
                "Your procurement campaign finished. Loot secured.")
        return
    # Wiped: return all loot to defenders + steep trophy penalty split among them.
    from inventory import remove_item, add_item
    total = json.loads(camp.total_loot_json or "{}")
    for did_str, items in total.items():
        did = int(did_str)
        for slug, qty in items.items():
            qty = int(qty)
            if qty > 0 and remove_item(camp.attacker_id, slug, qty):
                add_item(did, slug, qty)
    targets = [int(t) for t in json.loads(camp.targets_json or "[]")]
    penalty = 0
    try:
        ev = db.query(MilitaryEvent).filter_by(id=camp.event_id).first()
        penalty = ev.trophy_penalty if ev else WIPE_TROPHY_PENALTY
    except Exception:
        penalty = WIPE_TROPHY_PENALTY
    available = get_trophies(camp.attacker_id)
    taken = adjust_trophies(camp.attacker_id, -penalty)   # negative; clamped at 0
    share = (-taken) // max(1, len(targets)) if taken < 0 else 0
    for did in targets:
        if share > 0:
            adjust_trophies(did, share)
    if available < penalty:
        # Insufficient trophies → 60-day security ban.
        db.add(SecurityBan(player_id=camp.attacker_id, reason="campaign_wipe",
                           status="active",
                           expires_at=datetime.utcnow() + timedelta(days=SECURITY_BAN_DAYS)))
    _notify(camp.attacker_id, "💀 Forces Wiped Out",
            "Your campaign forces were destroyed. Loot returned to your victims and a "
            "trophy penalty applied." + (" Your security force is banned for 60 days."
                                         if available < penalty else ""))


# ─────────────────────────────────────────────────────────────────────────────
# Blockades
# ─────────────────────────────────────────────────────────────────────────────

def deploy_blockade(deployer_id: int, target_id: int,
                    force: Dict[str, float]) -> Tuple[bool, str]:
    if is_security_banned(deployer_id):
        return False, "Your security force is banned (post-wipe)."
    target_id = int(target_id)
    if target_id <= 0:
        return False, "Invalid target."
    if target_id == deployer_id:
        return False, "You cannot blockade yourself."
    db = SessionLocal()
    try:
        if not _pa_for(db, deployer_id):
            return False, "You do not own a Port Authority."
        dup = db.query(Blockade).filter(
            Blockade.deployer_id == deployer_id, Blockade.target_id == target_id,
            Blockade.status == "active",
        ).first()
        if dup:
            return False, "You already have an active blockade on that player."
        available = available_home_force(deployer_id)
        chosen, err = _select_force(force, available, list(BRANCHES.keys()))
        if err:
            return False, err
        db.add(Blockade(
            deployer_id=deployer_id, target_id=target_id,
            committed_force=json.dumps(chosen), status="active",
            expires_at=datetime.utcnow() + timedelta(hours=BLOCKADE_HOURS),
        ))
        db.commit()
        _notify(target_id, "🚫 You've been blockaded!",
                f"Player #{deployer_id} has blockaded your commerce. Defeat their forces "
                f"from your Port Authority within {BLOCKADE_HOURS}h to lift it.")
        return True, f"Blockade deployed on player #{target_id} for {BLOCKADE_HOURS} hours."
    except Exception as e:
        db.rollback()
        return False, str(e)
    finally:
        db.close()


def break_blockade(target_id: int, force: Dict[str, float]) -> Tuple[bool, str]:
    """The blockaded party commits a force to defeat the deployer and lift the blockade."""
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        block = db.query(Blockade).filter(
            Blockade.target_id == target_id, Blockade.status == "active",
            Blockade.expires_at > now,
        ).order_by(Blockade.id.asc()).first()
        if not block:
            return False, "You are not currently blockaded."
        if not _pa_for(db, target_id):
            return False, "You do not own a Port Authority."
        available = available_home_force(target_id)
        chosen, err = _select_force(force, available, list(BRANCHES.keys()))
        if err:
            return False, err

        # The blockaded party attacks the deployer's committed defending force.
        deployer_force = json.loads(block.committed_force or "{}")
        att_units = assemble_force(chosen, list(BRANCHES.keys()), 0, "attacker")
        def_units = assemble_force(deployer_force, list(BRANCHES.keys()), 0, "defender")

        battle = MilitaryBattle(
            campaign_id=None, kind="blockade", attacker_id=target_id,
            defender_id=block.deployer_id, target_slot=0, scheduled_at=now,
        )
        db.add(battle)
        db.flush()

        if not def_units:
            res = {"winner": "attacker", "rounds": 0, "attacker_losses": {},
                   "defender_losses": {}, "attacker_survivors_power": 0, "log": []}
        else:
            res = resolve_battle(att_units, def_units, seed=battle.id)

        att_pa = _pa_for(db, target_id)
        def_pa = _pa_for(db, block.deployer_id)
        if att_pa:
            for slug, qty in res["attacker_losses"].items():
                _pa_remove_item(db, att_pa.id, slug, qty)
        if def_pa:
            for slug, qty in res["defender_losses"].items():
                _pa_remove_item(db, def_pa.id, slug, qty)
        # Shrink the deployer's committed force by their losses.
        surviving = dict(deployer_force)
        for slug, qty in res["defender_losses"].items():
            surviving[slug] = max(0, surviving.get(slug, 0) - qty)
        block.committed_force = json.dumps({k: v for k, v in surviving.items() if v > 0})

        battle.resolved_at = now
        battle.winner = res["winner"]
        battle.rounds = res["rounds"]
        battle.attacker_losses = json.dumps(res["attacker_losses"])
        battle.defender_losses = json.dumps(res["defender_losses"])
        battle.summary_json = json.dumps(res)

        lifted = res["winner"] == "attacker"
        if lifted:
            block.status = "lifted"
            block.lifted_at = now
        db.commit()

        _notify(block.deployer_id,
                "🛡️ Blockade battle" + (" — LIFTED" if lifted else " — held"),
                _summary_text("blockade", block.deployer_id, target_id,
                              {**res,
                               "attacker_losses": res["defender_losses"],
                               "defender_losses": res["attacker_losses"]}, {}))
        if lifted:
            return True, "You defeated the blockading force — blockade lifted!"
        return True, "You damaged the blockading force but did not lift it. Try again before it expires."
    except Exception as e:
        db.rollback()
        return False, str(e)
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# Espionage
# ─────────────────────────────────────────────────────────────────────────────

def go_dark(hider_id: int, hidden_from: int, drones: int) -> Tuple[bool, str]:
    hidden_from = int(hidden_from)
    drones = int(drones)
    if hidden_from <= 0 or hidden_from == hider_id:
        return False, "Invalid target."
    if drones <= 0:
        return False, "Commit at least one Intelligence unit (drone)."
    db = SessionLocal()
    try:
        pa = _pa_for(db, hider_id)
        if not pa:
            return False, "You do not own a Port Authority."
        avail = available_home_force(hider_id)
        drone_pool = {s: q for s, q in avail.items() if branch_of(s) == "intelligence"}
        if sum(int(q) for q in drone_pool.values()) < drones:
            return False, "Not enough Intelligence units available at home."
        # Consume drones from the depot, strongest pools first.
        need = drones
        for slug in sorted(drone_pool, key=lambda s: -drone_pool[s]):
            if need <= 0:
                break
            take = min(int(drone_pool[slug]), need)
            if _pa_remove_item(db, pa.id, slug, take):
                need -= take
        existing = db.query(GoDarkRecord).filter(
            GoDarkRecord.hider_id == hider_id, GoDarkRecord.hidden_from == hidden_from,
            GoDarkRecord.status == "active",
        ).first()
        expires = datetime.utcnow() + timedelta(days=GO_DARK_DAYS)
        if existing:
            existing.expires_at = expires
            existing.drones_committed = (existing.drones_committed or 0) + drones
        else:
            db.add(GoDarkRecord(hider_id=hider_id, hidden_from=hidden_from,
                                drones_committed=drones, status="active",
                                expires_at=expires))
        db.commit()
        return True, f"You are now dark to player #{hidden_from} for up to {GO_DARK_DAYS} days."
    except Exception as e:
        db.rollback()
        return False, str(e)
    finally:
        db.close()


def search_targets(query: str, viewer_id: int) -> List[dict]:
    """Player search for target selection, hiding players who've gone dark to the viewer."""
    from contacts import search_players
    results = search_players(query or "", viewer_id)
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        hidden = {r.hider_id for r in db.query(GoDarkRecord.hider_id).filter(
            GoDarkRecord.hidden_from == viewer_id,
            GoDarkRecord.status == "active",
            GoDarkRecord.expires_at > now,
        ).all()}
    finally:
        db.close()
    return [r for r in results if r["id"] not in hidden]


# ─────────────────────────────────────────────────────────────────────────────
# Tick — scheduled lifecycle
# ─────────────────────────────────────────────────────────────────────────────

def _advance_campaigns(now: datetime):
    db = SessionLocal()
    try:
        due = db.query(MilitaryCampaign).filter(
            MilitaryCampaign.status.in_(["committed", "in_battle"]),
            MilitaryCampaign.next_battle_at <= now,
        ).all()
        for camp in due:
            event = db.query(MilitaryEvent).filter_by(id=camp.event_id).first()
            if not event:
                continue
            try:
                _run_campaign_battle(db, camp, event, now)
                db.commit()
            except Exception as e:
                db.rollback()
                print(f"[Military] campaign {camp.id} battle error: {e}")
    finally:
        db.close()


def _expire_blockades(now: datetime):
    db = SessionLocal()
    try:
        expired = db.query(Blockade).filter(
            Blockade.status == "active", Blockade.expires_at <= now,
        ).all()
        for b in expired:
            b.status = "expired"
            # Blockaded party failed to lift it in time → light trophy tribute.
            taken = adjust_trophies(b.target_id, -BLOCKADE_TRIBUTE)
            if taken < 0:
                adjust_trophies(b.deployer_id, -taken)
            _notify(b.target_id, "🚫 Blockade expired",
                    f"You failed to lift player #{b.deployer_id}'s blockade in time — "
                    f"a trophy tribute was paid.")
            _notify(b.deployer_id, "🚫 Blockade concluded",
                    f"Your blockade on player #{b.target_id} expired; you collected a tribute.")
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[Military] blockade expiry error: {e}")
    finally:
        db.close()


def _expire_go_dark(now: datetime):
    db = SessionLocal()
    try:
        db.query(GoDarkRecord).filter(
            GoDarkRecord.status == "active", GoDarkRecord.expires_at <= now,
        ).update({GoDarkRecord.status: "expired"}, synchronize_session=False)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[Military] go-dark expiry error: {e}")
    finally:
        db.close()


def _sweep_bans(now: datetime):
    db = SessionLocal()
    try:
        db.query(SecurityBan).filter(
            SecurityBan.status == "active", SecurityBan.expires_at <= now,
        ).update({SecurityBan.status: "expired"}, synchronize_session=False)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[Military] ban sweep error: {e}")
    finally:
        db.close()


def tick(current_tick: int, now: datetime):
    """Called every game tick; heavy work gated to once per ~60s."""
    if current_tick % 60 != 0:
        return
    _advance_campaigns(now)
    _expire_blockades(now)
    _expire_go_dark(now)
    _sweep_bans(now)


# ─────────────────────────────────────────────────────────────────────────────
# Admin event creation
# ─────────────────────────────────────────────────────────────────────────────

def create_military_event(admin_id: int, title: str, branches_allowed: List[str],
                          max_branch_strength: int, loot_fraction: float,
                          trophy_penalty: int, battle_hours: int,
                          activate: bool = True) -> Tuple[bool, str]:
    branches_allowed = [b for b in (branches_allowed or []) if b in BRANCHES]
    if not branches_allowed:
        return False, "Select at least one branch."
    db = SessionLocal()
    try:
        ev = MilitaryEvent(
            kind="procurement", title=title or "Procurement Event",
            status="open" if activate else "finished",
            branches_allowed=json.dumps(branches_allowed),
            max_branch_strength=max(0, int(max_branch_strength)),
            loot_fraction=max(0.0, min(1.0, float(loot_fraction))),
            trophy_penalty=max(0, int(trophy_penalty)),
            battle_hours=max(1, int(battle_hours)),
            created_by=admin_id,
        )
        db.add(ev)
        db.commit()
        if activate:
            try:
                from events import broadcast_event_push
                broadcast_event_push(ev.id, f"⚔️ {ev.title}",
                                     "A Procurement Event has begun — muster your Branches at the "
                                     "Port Authority and pick your targets.", tag="military-event")
            except Exception as e:
                print(f"[Military] broadcast error: {e}")
        return True, f"Procurement Event '{ev.title}' created (ID {ev.id})."
    except Exception as e:
        db.rollback()
        return False, str(e)
    finally:
        db.close()


def admin_list_events() -> List[dict]:
    db = SessionLocal()
    try:
        rows = db.query(MilitaryEvent).order_by(MilitaryEvent.id.desc()).limit(25).all()
        return [{
            "id": e.id, "title": e.title, "status": e.status,
            "branches": json.loads(e.branches_allowed or "[]"),
            "loot_fraction": e.loot_fraction, "battle_hours": e.battle_hours,
            "trophy_penalty": e.trophy_penalty,
        } for e in rows]
    finally:
        db.close()


def admin_cancel_event(event_id: int) -> Tuple[bool, str]:
    db = SessionLocal()
    try:
        ev = db.query(MilitaryEvent).filter_by(id=event_id).first()
        if not ev:
            return False, "Event not found."
        ev.status = "finished"
        db.commit()
        return True, f"Event {event_id} closed."
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# Status for the UI
# ─────────────────────────────────────────────────────────────────────────────

def get_military_status(player_id: int) -> dict:
    """Everything the /port-authority warfare panels need."""
    db = SessionLocal()
    try:
        pa = _pa_for(db, player_id)
        now = datetime.utcnow()

        # Force composition (PA command), split committed vs at-home.
        depot = _get_pa_inventory(db, pa.id) if pa else {}
        committed = _active_commitments(db, player_id)
        branches: Dict[str, dict] = {}
        for slug, qty in depot.items():
            br = branch_of(slug)
            if not br:
                continue
            b = branches.setdefault(br, {"label": BRANCH_LABELS[br], "units": [],
                                         "attack": 0, "defense": 0, "home": 0, "committed": 0})
            home_qty = max(0, qty - committed.get(slug, 0))
            b["units"].append({"slug": slug, "qty": qty, "home": home_qty,
                               "attack": unit_attack(slug), "defense": unit_defense(slug)})
            b["attack"] += unit_attack(slug) * int(qty)
            b["defense"] += unit_defense(slug) * int(qty)
            b["home"] += int(home_qty)
            b["committed"] += int(committed.get(slug, 0))

        # Active procurement event.
        event = db.query(MilitaryEvent).filter(
            MilitaryEvent.kind == "procurement",
            MilitaryEvent.status.in_(["open", "running"]),
        ).order_by(MilitaryEvent.id.desc()).first()
        event_d = None
        my_campaign = None
        if event:
            event_d = {"id": event.id, "title": event.title,
                       "branches": json.loads(event.branches_allowed or "[]"),
                       "max_branch_strength": event.max_branch_strength,
                       "loot_fraction": event.loot_fraction,
                       "battle_hours": event.battle_hours}
            camp = db.query(MilitaryCampaign).filter(
                MilitaryCampaign.event_id == event.id,
                MilitaryCampaign.attacker_id == player_id,
                MilitaryCampaign.status.in_(["committed", "in_battle"]),
            ).first()
            if camp:
                my_campaign = {
                    "targets": json.loads(camp.targets_json or "[]"),
                    "current_index": camp.current_index,
                    "next_battle_at": camp.next_battle_at.isoformat() if camp.next_battle_at else None,
                    "committed_force": json.loads(camp.committed_force or "{}"),
                }

        # Blockades.
        blocks_by = db.query(Blockade).filter(
            Blockade.deployer_id == player_id, Blockade.status == "active",
            Blockade.expires_at > now).all()
        blocks_on = db.query(Blockade).filter(
            Blockade.target_id == player_id, Blockade.status == "active",
            Blockade.expires_at > now).all()
        blockades = {
            "by_me": [{"target_id": b.target_id, "expires_at": b.expires_at.isoformat()}
                      for b in blocks_by],
            "on_me": [{"deployer_id": b.deployer_id, "expires_at": b.expires_at.isoformat()}
                      for b in blocks_on],
        }

        # Go-dark.
        darks = db.query(GoDarkRecord).filter(
            GoDarkRecord.hider_id == player_id, GoDarkRecord.status == "active",
            GoDarkRecord.expires_at > now).all()
        go_dark_list = [{"hidden_from": g.hidden_from, "expires_at": g.expires_at.isoformat()}
                        for g in darks]

        # Recent battles.
        recent = db.query(MilitaryBattle).filter(
            (MilitaryBattle.attacker_id == player_id) |
            (MilitaryBattle.defender_id == player_id)
        ).order_by(MilitaryBattle.id.desc()).limit(10).all()
        battles = [{
            "id": b.id, "kind": b.kind, "as": "attacker" if b.attacker_id == player_id else "defender",
            "opponent": b.defender_id if b.attacker_id == player_id else b.attacker_id,
            "winner": b.winner, "rounds": b.rounds,
            "attacker_losses": json.loads(b.attacker_losses or "{}"),
            "defender_losses": json.loads(b.defender_losses or "{}"),
            "loot": json.loads(b.loot_json or "{}"),
            "resolved_at": b.resolved_at.isoformat() if b.resolved_at else None,
        } for b in recent]

        return {
            "has_pa": pa is not None,
            "banned": is_security_banned(player_id),
            "branches": branches,
            "event": event_d,
            "campaign": my_campaign,
            "blockades": blockades,
            "go_dark": go_dark_list,
            "battles": battles,
        }
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI router
# ─────────────────────────────────────────────────────────────────────────────

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/military", tags=["military"])


def _pid(request: Request) -> Optional[int]:
    from auth import get_player_from_session, get_db
    db = get_db()
    try:
        player = get_player_from_session(db, request.cookies.get("session_token"))
        return player.id if player else None
    finally:
        db.close()


@router.get("/search")
async def api_search(request: Request, q: str = ""):
    pid = _pid(request)
    if not pid:
        return JSONResponse({"error": "Not logged in."}, status_code=401)
    return JSONResponse({"results": search_targets(q, pid)})


@router.get("/status")
async def api_status(request: Request):
    pid = _pid(request)
    if not pid:
        return JSONResponse({"error": "Not logged in."}, status_code=401)
    return JSONResponse(get_military_status(pid))


@router.post("/campaign/commit")
async def api_campaign_commit(request: Request):
    pid = _pid(request)
    if not pid:
        return JSONResponse({"error": "Not logged in."}, status_code=401)
    body = await request.json()
    ok, msg = commit_campaign(pid, body.get("targets", []), body.get("force", {}))
    return JSONResponse({"ok": ok, "message": msg}, status_code=200 if ok else 400)


@router.post("/blockade/deploy")
async def api_blockade_deploy(request: Request):
    pid = _pid(request)
    if not pid:
        return JSONResponse({"error": "Not logged in."}, status_code=401)
    body = await request.json()
    ok, msg = deploy_blockade(pid, body.get("target_id", 0), body.get("force", {}))
    return JSONResponse({"ok": ok, "message": msg}, status_code=200 if ok else 400)


@router.post("/blockade/break")
async def api_blockade_break(request: Request):
    pid = _pid(request)
    if not pid:
        return JSONResponse({"error": "Not logged in."}, status_code=401)
    body = await request.json()
    ok, msg = break_blockade(pid, body.get("force", {}))
    return JSONResponse({"ok": ok, "message": msg}, status_code=200 if ok else 400)


@router.post("/go-dark")
async def api_go_dark(request: Request):
    pid = _pid(request)
    if not pid:
        return JSONResponse({"error": "Not logged in."}, status_code=401)
    body = await request.json()
    ok, msg = go_dark(pid, body.get("hidden_from", 0), body.get("drones", 0))
    return JSONResponse({"ok": ok, "message": msg}, status_code=200 if ok else 400)


def initialize():
    init_db()


# Create tables on import (mirrors port_authority.py). Guarded so a transient DB
# outage at import time cannot crash module load / app startup.
try:
    init_db()
except Exception as _e:
    print(f"[Military] init_db deferred: {_e}")
