"""
port_authority.py

Player-controlled military institution.  Players move weapons and weapon
platforms from their own inventory into the Port Authority (PA).  When the
held items satisfy the Fleet or Army threshold the player can deploy that
force on a mission.  Mission outcomes are pure RNG.  Maintenance is
auto-deducted from the owner's USD balance once per game day.

Design choices (per product spec):
  • Pure RNG mission outcomes — no stat weighting.
  • Fleet / Army composition comes entirely from the player's inventory.
  • Revenue model: maintenance costs only (deducted automatically).
  • Geography: global — no home-port constraint.
"""

import random
from datetime import datetime
from typing import Optional, List, Dict, Tuple

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Text,
    UniqueConstraint, update as sa_update,
)
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.declarative import declarative_base

from database import engine, SessionLocal

Base = declarative_base()

# ─────────────────────────────────────────────────────────────────────────────
# Item category sets (all weapon / platform item_type slugs)
# ─────────────────────────────────────────────────────────────────────────────

CARRIERS = frozenset({
    "ford_class_carrier", "queen_elizabeth_carrier",
    "charles_degaulle_carrier", "fujian_carrier", "ins_vikrant_carrier",
})

SUBMARINES = frozenset({
    "virginia_class_sub", "astute_class_sub", "barracuda_class_sub",
    "yasen_class_sub", "type093_sub", "arihant_class_sub",
})

DESTROYERS = frozenset({
    "arleigh_burke_destroyer", "type045_destroyer", "type055_destroyer",
    "atago_class_destroyer", "kdx3_destroyer", "visakhapatnam_destroyer",
    "gorshkov_frigate", "milgem_frigate", "al_riyadh_frigate",
    "baynunah_corvette",
})

FIGHTER_JETS = frozenset({
    "f22_raptor", "f35_lightning", "su57_felon", "j20_chengdu", "tai_tfx",
    "f16_falcon", "f15_eagle", "su35_flanker", "mig29_fulcrum",
    "rafale", "eurofighter_typhoon", "j16_flanker", "hal_tejas",
    "kf21_boramae",
})

HELICOPTERS = frozenset({
    "ah64_apache", "ka52_alligator", "z10_thunderbolt", "t129_atak",
    "uh60_blackhawk", "mi24_hind", "airbus_h225m", "hal_dhruv",
})

TANKS = frozenset({
    "m1a2_abrams", "leopard_2a7", "challenger_3", "t14_armata",
    "k2_black_panther", "t90m_proryv", "amx_leclerc", "type_99a",
    "arjun_mk2", "altay_tank", "type10_tank", "ee_t1_osorio",
})

RIFLES = frozenset({
    "m4_carbine", "m249_saw", "ak_47", "ak_74m", "hk416", "hk_g36",
    "l85a2", "famas_f1", "qbz_95", "insas_rifle", "k2_rifle", "mpt_76",
    "vektor_r4", "howa_type89", "sig_sg550", "fx05_xiuhcoatl",
    "imbel_md97", "caracal_car816",
})

ALL_PA_ITEMS = CARRIERS | SUBMARINES | DESTROYERS | FIGHTER_JETS | HELICOPTERS | TANKS | RIFLES

# ─────────────────────────────────────────────────────────────────────────────
# Fleet / Army deployment thresholds
# Each entry: (item_category_set, minimum_total_quantity_needed)
# ─────────────────────────────────────────────────────────────────────────────

FLEET_THRESHOLDS: Dict[str, Tuple[frozenset, int]] = {
    "carriers":     (CARRIERS,     1),
    "submarines":   (SUBMARINES,   2),
    "destroyers":   (DESTROYERS,   4),
    "fighter_jets": (FIGHTER_JETS, 12),
}

ARMY_THRESHOLDS: Dict[str, Tuple[frozenset, int]] = {
    "tanks":        (TANKS,        10),
    "helicopters":  (HELICOPTERS,  5),
    "rifles":       (RIFLES,       100),
    "fighter_jets": (FIGHTER_JETS, 6),
}

# ─────────────────────────────────────────────────────────────────────────────
# Maintenance costs (USD per item per game-day)
# 1 game-day = MAINTENANCE_INTERVAL ticks (86 400 ticks @ 1 tick/second)
# ─────────────────────────────────────────────────────────────────────────────

MAINTENANCE_DAILY: Dict[str, float] = {
    **{i: 500_000.0 for i in CARRIERS},
    **{i: 200_000.0 for i in SUBMARINES},
    **{i: 100_000.0 for i in DESTROYERS},
    **{i: 50_000.0  for i in FIGHTER_JETS},
    **{i: 40_000.0  for i in HELICOPTERS},
    **{i: 30_000.0  for i in TANKS},
    **{i: 10.0      for i in RIFLES},
}

MAINTENANCE_INTERVAL = 86_400  # ticks between automatic maintenance charges

# Attack mission: winner steals this fraction of target's USD balance
LOOT_FRACTION = 0.05
LOOT_CAP_USD  = 10_000_000.0   # maximum loot per successful attack

# On failure: this fraction of PA inventory is destroyed (random items)
LOSS_FRACTION = 0.10


# ─────────────────────────────────────────────────────────────────────────────
# DB Models
# ─────────────────────────────────────────────────────────────────────────────

class PortAuthorityInstance(Base):
    __tablename__ = "port_authority_instances"

    id                    = Column(Integer, primary_key=True)
    owner_id              = Column(Integer, index=True, unique=True, nullable=False)
    name                  = Column(String, default="Port Authority")
    created_at            = Column(DateTime, default=datetime.utcnow)
    last_maintenance_tick = Column(Integer, default=0)


class PortAuthorityInventory(Base):
    __tablename__ = "port_authority_inventory"
    __table_args__ = (UniqueConstraint("pa_id", "item_type"),)

    id        = Column(Integer, primary_key=True)
    pa_id     = Column(Integer, index=True, nullable=False)
    item_type = Column(String, nullable=False)
    quantity  = Column(Float, default=0.0)


class PortAuthorityMission(Base):
    __tablename__ = "port_authority_missions"

    id            = Column(Integer, primary_key=True)
    pa_id         = Column(Integer, index=True, nullable=False)
    mission_type  = Column(String, nullable=False)   # "attack" | "defend"
    force_type    = Column(String, nullable=False)   # "fleet"  | "army"
    target_player = Column(Integer, nullable=True)
    target_note   = Column(String, nullable=True)
    outcome       = Column(String, nullable=True)    # "success" | "failure"
    loot_usd      = Column(Float, default=0.0)
    items_lost    = Column(Text, nullable=True)       # JSON summary of losses
    created_at    = Column(DateTime, default=datetime.utcnow)
    resolved_at   = Column(DateTime, nullable=True)


def init_db():
    Base.metadata.create_all(bind=engine)


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_pa_inventory(db, pa_id: int) -> Dict[str, float]:
    rows = db.query(PortAuthorityInventory).filter_by(pa_id=pa_id).all()
    return {r.item_type: r.quantity for r in rows if r.quantity > 0}


def _category_total(inventory: Dict[str, float], category: frozenset) -> float:
    return sum(qty for item, qty in inventory.items() if item in category)


def _check_thresholds(inventory: Dict[str, float], thresholds: Dict) -> Tuple[bool, Dict]:
    """Return (ready, {slot: (have, need)}) for each threshold slot."""
    breakdown = {}
    ready = True
    for slot, (cat, minimum) in thresholds.items():
        have = _category_total(inventory, cat)
        breakdown[slot] = {"have": have, "need": minimum, "met": have >= minimum}
        if have < minimum:
            ready = False
    return ready, breakdown


def _pa_add_item(db, pa_id: int, item_type: str, quantity: float):
    stmt = (
        pg_insert(PortAuthorityInventory.__table__)
        .values(pa_id=pa_id, item_type=item_type, quantity=quantity)
        .on_conflict_do_update(
            index_elements=["pa_id", "item_type"],
            set_={"quantity": PortAuthorityInventory.quantity + quantity},
        )
    )
    db.execute(stmt)


def _pa_remove_item(db, pa_id: int, item_type: str, quantity: float) -> bool:
    result = db.execute(
        sa_update(PortAuthorityInventory)
        .where(PortAuthorityInventory.pa_id == pa_id)
        .where(PortAuthorityInventory.item_type == item_type)
        .where(PortAuthorityInventory.quantity >= quantity)
        .values(quantity=PortAuthorityInventory.quantity - quantity)
    )
    return result.rowcount > 0


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def create_port_authority(player_id: int) -> Tuple[bool, str]:
    """Create a Port Authority for *player_id*.  Returns (ok, message)."""
    db = SessionLocal()
    try:
        existing = db.query(PortAuthorityInstance).filter_by(owner_id=player_id).first()
        if existing:
            return False, "You already own a Port Authority."
        pa = PortAuthorityInstance(owner_id=player_id)
        db.add(pa)
        db.commit()
        return True, "Port Authority established."
    except Exception as e:
        db.rollback()
        return False, str(e)
    finally:
        db.close()


def get_port_authority(player_id: int) -> Optional[dict]:
    """Return PA info + inventory + fleet/army readiness for *player_id*."""
    db = SessionLocal()
    try:
        pa = db.query(PortAuthorityInstance).filter_by(owner_id=player_id).first()
        if not pa:
            return None
        inventory = _get_pa_inventory(db, pa.id)
        fleet_ready, fleet_bd = _check_thresholds(inventory, FLEET_THRESHOLDS)
        army_ready, army_bd   = _check_thresholds(inventory, ARMY_THRESHOLDS)
        daily_cost = sum(MAINTENANCE_DAILY.get(it, 0) * qty for it, qty in inventory.items())
        return {
            "id":                    pa.id,
            "owner_id":              pa.owner_id,
            "name":                  pa.name,
            "created_at":            pa.created_at.isoformat() if pa.created_at else None,
            "last_maintenance_tick": pa.last_maintenance_tick,
            "inventory":             inventory,
            "fleet_ready":           fleet_ready,
            "fleet_breakdown":       fleet_bd,
            "army_ready":            army_ready,
            "army_breakdown":        army_bd,
            "daily_maintenance_usd": daily_cost,
        }
    finally:
        db.close()


def deposit_weapon(player_id: int, item_type: str, quantity: float) -> Tuple[bool, str]:
    """Move *quantity* of *item_type* from player inventory into their PA."""
    if item_type not in ALL_PA_ITEMS:
        return False, f"{item_type} is not a valid Port Authority asset."
    if quantity <= 0:
        return False, "Quantity must be positive."

    db = SessionLocal()
    try:
        pa = db.query(PortAuthorityInstance).filter_by(owner_id=player_id).first()
        if not pa:
            return False, "You do not own a Port Authority."

        from inventory import remove_item
        if not remove_item(player_id, item_type, quantity):
            return False, "Insufficient quantity in your inventory."

        _pa_add_item(db, pa.id, item_type, quantity)
        db.commit()
        return True, f"Deposited {quantity:g} × {item_type} into your Port Authority."
    except Exception as e:
        db.rollback()
        return False, str(e)
    finally:
        db.close()


def withdraw_weapon(player_id: int, item_type: str, quantity: float) -> Tuple[bool, str]:
    """Move *quantity* of *item_type* from PA back to player inventory."""
    if quantity <= 0:
        return False, "Quantity must be positive."

    db = SessionLocal()
    try:
        pa = db.query(PortAuthorityInstance).filter_by(owner_id=player_id).first()
        if not pa:
            return False, "You do not own a Port Authority."

        if not _pa_remove_item(db, pa.id, item_type, quantity):
            return False, "Insufficient quantity in your Port Authority."

        from inventory import add_item
        add_item(player_id, item_type, quantity)
        db.commit()
        return True, f"Withdrew {quantity:g} × {item_type} from your Port Authority."
    except Exception as e:
        db.rollback()
        return False, str(e)
    finally:
        db.close()


def deploy_mission(
    player_id: int,
    force_type: str,        # "fleet" | "army"
    mission_type: str,      # "attack" | "defend"
    target_player_id: Optional[int] = None,
    target_note: Optional[str] = None,
) -> Tuple[bool, dict]:
    """
    Launch a mission.  Returns (ok, result_dict).

    Attack:
      success → steal min(5 % of target's balance, $10 M) in cash
      failure → lose 10 % of PA inventory (random items destroyed)

    Defend:
      success → no loss, defence holds
      failure → lose 10 % of PA inventory (random items destroyed)

    Outcome is a pure 50/50 coin-flip.
    """
    if force_type not in ("fleet", "army"):
        return False, {"error": "force_type must be 'fleet' or 'army'"}
    if mission_type not in ("attack", "defend"):
        return False, {"error": "mission_type must be 'attack' or 'defend'"}

    db = SessionLocal()
    try:
        pa = db.query(PortAuthorityInstance).filter_by(owner_id=player_id).first()
        if not pa:
            return False, {"error": "You do not own a Port Authority."}

        inventory = _get_pa_inventory(db, pa.id)
        thresholds = FLEET_THRESHOLDS if force_type == "fleet" else ARMY_THRESHOLDS
        ready, breakdown = _check_thresholds(inventory, thresholds)
        if not ready:
            unmet = [k for k, v in breakdown.items() if not v["met"]]
            return False, {
                "error": f"{'Fleet' if force_type == 'fleet' else 'Army'} not ready. "
                         f"Missing: {', '.join(unmet)}.",
                "breakdown": breakdown,
            }

        # ── Pure RNG resolution ──────────────────────────────────────────────
        success = random.random() < 0.5

        loot_usd   = 0.0
        items_lost_summary: Dict[str, float] = {}

        if success and mission_type == "attack" and target_player_id is not None:
            from reserve_banks import get_usd_balance, spend_player_funds
            target_balance = get_usd_balance(target_player_id)
            loot = min(target_balance * LOOT_FRACTION, LOOT_CAP_USD)
            if loot > 0:
                ok, _ = spend_player_funds(target_player_id, loot)
                if ok:
                    from reserve_banks import credit_usd
                    credit_usd(player_id, loot)
                    loot_usd = loot

        if not success:
            # Destroy LOSS_FRACTION of each PA item
            for item_type, qty in list(inventory.items()):
                loss = max(1, int(qty * LOSS_FRACTION))
                loss = min(loss, int(qty))
                if loss > 0:
                    _pa_remove_item(db, pa.id, item_type, float(loss))
                    items_lost_summary[item_type] = float(loss)

        import json
        mission = PortAuthorityMission(
            pa_id=pa.id,
            mission_type=mission_type,
            force_type=force_type,
            target_player=target_player_id,
            target_note=target_note,
            outcome="success" if success else "failure",
            loot_usd=loot_usd,
            items_lost=json.dumps(items_lost_summary) if items_lost_summary else None,
            resolved_at=datetime.utcnow(),
        )
        db.add(mission)
        db.commit()

        return True, {
            "outcome":      "success" if success else "failure",
            "force_type":   force_type,
            "mission_type": mission_type,
            "loot_usd":     loot_usd,
            "items_lost":   items_lost_summary,
        }
    except Exception as e:
        db.rollback()
        return False, {"error": str(e)}
    finally:
        db.close()


def get_missions(player_id: int, limit: int = 20) -> List[dict]:
    """Return recent missions for *player_id*'s Port Authority."""
    db = SessionLocal()
    try:
        pa = db.query(PortAuthorityInstance).filter_by(owner_id=player_id).first()
        if not pa:
            return []
        rows = (
            db.query(PortAuthorityMission)
            .filter_by(pa_id=pa.id)
            .order_by(PortAuthorityMission.created_at.desc())
            .limit(limit)
            .all()
        )
        import json
        return [
            {
                "id":            r.id,
                "mission_type":  r.mission_type,
                "force_type":    r.force_type,
                "target_player": r.target_player,
                "target_note":   r.target_note,
                "outcome":       r.outcome,
                "loot_usd":      r.loot_usd,
                "items_lost":    json.loads(r.items_lost) if r.items_lost else {},
                "created_at":    r.created_at.isoformat() if r.created_at else None,
                "resolved_at":   r.resolved_at.isoformat() if r.resolved_at else None,
            }
            for r in rows
        ]
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# Tick — maintenance deduction
# ─────────────────────────────────────────────────────────────────────────────

def tick(current_tick: int, now: datetime):
    """Called every game tick.  Charges daily maintenance once per interval."""
    if current_tick % MAINTENANCE_INTERVAL != 0:
        return

    db = SessionLocal()
    try:
        from reserve_banks import spend_player_funds
        pas = db.query(PortAuthorityInstance).all()
        for pa in pas:
            inventory = _get_pa_inventory(db, pa.id)
            if not inventory:
                continue
            daily_cost = sum(
                MAINTENANCE_DAILY.get(it, 0.0) * qty
                for it, qty in inventory.items()
            )
            if daily_cost <= 0:
                continue
            ok, _ = spend_player_funds(pa.owner_id, daily_cost)
            if not ok:
                # Cannot afford maintenance — destroy a random PA item as penalty
                items = [it for it, qty in inventory.items() if qty >= 1]
                if items:
                    victim = random.choice(items)
                    _pa_remove_item(db, pa.id, victim, 1.0)
            pa.last_maintenance_tick = current_tick
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[PortAuthority] maintenance tick error: {e}")
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI router
# ─────────────────────────────────────────────────────────────────────────────

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/port-authority", tags=["port-authority"])


def _player_id(request: Request) -> Optional[int]:
    from auth import get_player_from_session, get_db
    db = next(get_db())
    player = get_player_from_session(request, db)
    return player.id if player else None


@router.post("/create")
async def api_create(request: Request):
    pid = _player_id(request)
    if not pid:
        return JSONResponse({"error": "Not logged in."}, status_code=401)
    ok, msg = create_port_authority(pid)
    return JSONResponse({"ok": ok, "message": msg}, status_code=200 if ok else 400)


@router.get("")
async def api_get(request: Request):
    pid = _player_id(request)
    if not pid:
        return JSONResponse({"error": "Not logged in."}, status_code=401)
    data = get_port_authority(pid)
    if data is None:
        return JSONResponse({"error": "No Port Authority found."}, status_code=404)
    return JSONResponse(data)


@router.post("/deposit")
async def api_deposit(request: Request):
    pid = _player_id(request)
    if not pid:
        return JSONResponse({"error": "Not logged in."}, status_code=401)
    body = await request.json()
    item_type = body.get("item_type", "")
    quantity  = float(body.get("quantity", 0))
    ok, msg = deposit_weapon(pid, item_type, quantity)
    return JSONResponse({"ok": ok, "message": msg}, status_code=200 if ok else 400)


@router.post("/withdraw")
async def api_withdraw(request: Request):
    pid = _player_id(request)
    if not pid:
        return JSONResponse({"error": "Not logged in."}, status_code=401)
    body = await request.json()
    item_type = body.get("item_type", "")
    quantity  = float(body.get("quantity", 0))
    ok, msg = withdraw_weapon(pid, item_type, quantity)
    return JSONResponse({"ok": ok, "message": msg}, status_code=200 if ok else 400)


@router.post("/deploy")
async def api_deploy(request: Request):
    pid = _player_id(request)
    if not pid:
        return JSONResponse({"error": "Not logged in."}, status_code=401)
    body         = await request.json()
    force_type   = body.get("force_type", "")
    mission_type = body.get("mission_type", "")
    target_pid   = body.get("target_player_id")
    target_note  = body.get("target_note")
    ok, result = deploy_mission(pid, force_type, mission_type, target_pid, target_note)
    return JSONResponse({"ok": ok, **result}, status_code=200 if ok else 400)


@router.get("/missions")
async def api_missions(request: Request):
    pid = _player_id(request)
    if not pid:
        return JSONResponse({"error": "Not logged in."}, status_code=401)
    return JSONResponse({"missions": get_missions(pid)})


# Run table creation when module is imported
init_db()
