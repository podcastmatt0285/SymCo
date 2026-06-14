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
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Text, Boolean,
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

ARMORED_VEHICLES = frozenset({
    "m2_bradley", "stryker_apc", "bmp3_ifv", "btr82_apc",
    "boxer_apc", "puma_ifv",
})

DRONES = frozenset({
    "mq9_reaper", "bayraktar_tb2", "wing_loong_2",
    "switchblade_600", "lancet_3",
})

ALL_PA_ITEMS = (
    CARRIERS | SUBMARINES | DESTROYERS | FIGHTER_JETS
    | HELICOPTERS | TANKS | RIFLES | ARMORED_VEHICLES | DRONES
)

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
    "tanks":             (TANKS,             10),
    "helicopters":       (HELICOPTERS,        5),
    "rifles":            (RIFLES,           100),
    "fighter_jets":      (FIGHTER_JETS,       6),
    "armored_vehicles":  (ARMORED_VEHICLES,   8),
    "drones":            (DRONES,             4),
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
    **{i: 15_000.0  for i in ARMORED_VEHICLES},
    **{i: 8_000.0   for i in DRONES},
    **{i: 10.0      for i in RIFLES},
}

MAINTENANCE_INTERVAL = 86_400  # ticks between automatic maintenance charges

# On failure: this fraction of PA inventory is destroyed (random items)
LOSS_FRACTION = 0.10

# Daily maintenance: a small share flows to the federal government ledger.
PA_MAINTENANCE_TAX_RATE = 0.10


def _fire_pa_push(player_id: int, title: str, body: str, url: str = "/port-authority"):
    """Fire an 'institutions' push notification for a Port Authority event.

    Honours the player's notif_push_institutions toggle (handled inside
    send_push_notification). Never raises.
    """
    try:
        from push_ux import send_push_notification
        send_push_notification(player_id, title, body, url,
                               notif_type="institutions", tag="port-authority")
    except Exception as e:
        print(f"[PortAuthority] push error: {e}")


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
    # The Institution (special plot) this Port Authority is built on.
    special_plot_id       = Column(Integer, index=True, nullable=True)
    # Immigration policy multipliers
    immigration_volume    = Column(Float, default=1.0)   # 0.0–3.0, multiplier on retail sales volume
    immigration_wealth    = Column(Float, default=1.0)   # 0.5–2.0, multiplier on price/elasticity


class PortAuthorityInventory(Base):
    __tablename__ = "port_authority_inventory"
    __table_args__ = (UniqueConstraint("pa_id", "item_type"),)

    id        = Column(Integer, primary_key=True)
    pa_id     = Column(Integer, index=True, nullable=False)
    item_type = Column(String, nullable=False)
    quantity  = Column(Float, default=0.0)


class PortAuthorityMission(Base):
    __tablename__ = "port_authority_missions"

    id               = Column(Integer, primary_key=True)
    pa_id            = Column(Integer, index=True, nullable=False)
    mission_subtype  = Column(String, nullable=False)   # "procurement" | "blockade"
    target_player_id = Column(Integer, nullable=True)
    target_item_type = Column(String, nullable=True)
    target_quantity  = Column(Integer, default=1)
    items_acquired   = Column(Text, nullable=True)      # JSON: {item_type: qty} on success
    items_lost       = Column(Text, nullable=True)      # JSON: {item_type: qty} on failure
    outcome          = Column(String, nullable=True)    # "success" | "failure"
    created_at       = Column(DateTime, default=datetime.utcnow)
    resolved_at      = Column(DateTime, nullable=True)


class ProcurementSubmission(Base):
    __tablename__ = "procurement_submissions"

    id                   = Column(Integer, primary_key=True)
    player_id            = Column(Integer, index=True, nullable=False)
    event_id             = Column(Integer, nullable=False, index=True)
    submitted_at         = Column(DateTime, default=datetime.utcnow)
    payment_received_usd = Column(Float, default=0.0)


class BlockadeInstance(Base):
    __tablename__ = "blockade_instances"

    id                = Column(Integer, primary_key=True)
    blocker_player_id = Column(Integer, index=True, nullable=False)
    target_player_id  = Column(Integer, index=True, nullable=False)
    item_type         = Column(String, nullable=False)
    created_at        = Column(DateTime, default=datetime.utcnow)
    expires_at        = Column(DateTime, nullable=False)
    lifted            = Column(Boolean, default=False)


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

def get_unbuilt_pa_plot(player_id: int):
    """Return the player's first vacant 'port_authority' Institution plot, or None.

    A Port Authority is a true Institution — it must be built on a special plot
    of type 'port_authority' that the player created by sacrificing land
    (Wadsworth Pro required). This finds a plot ready to host one.
    """
    try:
        from special_plots import get_player_special_plots
        for sp in get_player_special_plots(player_id):
            if sp.special_type == "port_authority" and not sp.occupied_by_business_id:
                return sp
    except Exception as e:
        print(f"[PortAuthority] plot lookup error: {e}")
    return None


def build_port_authority(player_id: int, special_plot_id: int) -> Tuple[bool, str]:
    """Build a Port Authority on a 'port_authority' Institution plot the player owns.

    Mirrors create_mint_business: the player must already own a vacant special
    plot of the right type (which required Wadsworth Pro + a land sacrifice to
    create). Marks the plot occupied so it pays the monthly institution tax.
    """
    from special_plots import get_special_plot, occupy_special_plot

    sp = get_special_plot(special_plot_id)
    if not sp or sp.owner_id != player_id:
        return False, "Institution not found."
    if sp.special_type != "port_authority":
        return False, "That Institution is not a Port Authority plot."
    if sp.occupied_by_business_id is not None:
        return False, "This Institution already hosts a Port Authority."

    db = SessionLocal()
    try:
        if db.query(PortAuthorityInstance).filter_by(owner_id=player_id).first():
            return False, "You already operate a Port Authority."
        pa = PortAuthorityInstance(owner_id=player_id, special_plot_id=special_plot_id)
        db.add(pa)
        db.commit()
        pa_id = pa.id
    except Exception as e:
        db.rollback()
        return False, str(e)
    finally:
        db.close()

    # Mark the Institution plot occupied (occupy_special_plot uses its own
    # session) only after the PA is safely committed — reusing
    # occupied_by_business_id as the "facility present" marker, like the Mint.
    try:
        occupy_special_plot(special_plot_id, pa_id)
    except Exception as e:
        print(f"[PortAuthority] occupy plot error: {e}")
    return True, "Port Authority established on your Institution."


def create_port_authority(player_id: int) -> Tuple[bool, str]:
    """Build a Port Authority — requires a vacant 'port_authority' Institution plot.

    Kept as the public entry point used by the API/UI: it locates the player's
    ready Institution plot and builds on it, or explains the prerequisite.
    """
    db = SessionLocal()
    try:
        if db.query(PortAuthorityInstance).filter_by(owner_id=player_id).first():
            return False, "You already operate a Port Authority."
    finally:
        db.close()
    sp = get_unbuilt_pa_plot(player_id)
    if not sp:
        return False, ("A Port Authority is an Institution. First sacrifice land to "
                       "create a Port Authority Institution (Wadsworth Pro required), "
                       "then build here.")
    return build_port_authority(player_id, sp.id)


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
            "immigration_volume":    pa.immigration_volume if pa.immigration_volume is not None else 1.0,
            "immigration_wealth":    pa.immigration_wealth if pa.immigration_wealth is not None else 1.0,
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
    mission_subtype: str,       # "procurement" | "blockade"
    target_player_id: int,
    target_item_type: str,
    target_quantity: int = 1,
) -> Tuple[bool, dict]:
    """
    Launch a procurement or blockade mission.  Returns (ok, result_dict).

    Either fleet or army readiness is sufficient to deploy.

    procurement:
      success → steal target_quantity of target_item_type from target's PA inventory
      failure → lose 10% of own PA inventory

    blockade:
      success → create a 24-hour blockade on target's item transfers
      failure → lose 10% of own PA inventory

    Outcome is a pure 50/50 coin-flip.
    """
    import json

    if mission_subtype not in ("procurement", "blockade"):
        return False, {"error": "mission_subtype must be 'procurement' or 'blockade'"}

    db = SessionLocal()
    try:
        pa = db.query(PortAuthorityInstance).filter_by(owner_id=player_id).first()
        if not pa:
            return False, {"error": "You do not own a Port Authority."}

        inventory = _get_pa_inventory(db, pa.id)

        # Check fleet OR army readiness — either qualifies the player to deploy
        fleet_ready, fleet_bd = _check_thresholds(inventory, FLEET_THRESHOLDS)
        army_ready, army_bd   = _check_thresholds(inventory, ARMY_THRESHOLDS)
        if not fleet_ready and not army_ready:
            return False, {
                "error": "Neither fleet nor army is ready for deployment.",
                "fleet_breakdown": fleet_bd,
                "army_breakdown":  army_bd,
            }

        # ── Pure RNG resolution ──────────────────────────────────────────────
        success = random.random() < 0.5

        items_acquired_summary: Dict[str, float] = {}
        items_lost_summary: Dict[str, float] = {}

        if not success:
            # Destroy LOSS_FRACTION of each PA item
            for item_type, qty in list(inventory.items()):
                loss = max(1, int(qty * LOSS_FRACTION))
                loss = min(loss, int(qty))
                if loss > 0:
                    _pa_remove_item(db, pa.id, item_type, float(loss))
                    items_lost_summary[item_type] = float(loss)

        if success and mission_subtype == "procurement":
            # Find target's PA and steal target_item_type
            target_pa = db.query(PortAuthorityInstance).filter_by(owner_id=target_player_id).first()
            if target_pa:
                target_inv = _get_pa_inventory(db, target_pa.id)
                qty_available = min(target_quantity, target_inv.get(target_item_type, 0))
                if qty_available > 0:
                    _pa_remove_item(db, target_pa.id, target_item_type, float(qty_available))
                    _pa_add_item(db, pa.id, target_item_type, float(qty_available))
                    items_acquired_summary[target_item_type] = float(qty_available)
                    # Notify target
                    _fire_pa_push(
                        target_player_id,
                        "Port Authority: Procurement Alert",
                        f"Your {target_item_type} inventory was raided — {qty_available} units acquired.",
                    )
                    # Log transactions for both players
                    try:
                        from stats_ux import log_transaction
                        log_transaction(
                            player_id, "pa_procurement_acquired", "resource", 0.0,
                            f"Acquired {qty_available:g} × {target_item_type} via procurement from player {target_player_id}",
                            item_type=target_item_type, quantity=qty_available,
                        )
                        log_transaction(
                            target_player_id, "pa_procurement_lost", "resource", 0.0,
                            f"Lost {qty_available:g} × {target_item_type} to procurement by player {player_id}",
                            item_type=target_item_type, quantity=qty_available,
                        )
                    except Exception:
                        pass

        if success and mission_subtype == "blockade":
            blockade = BlockadeInstance(
                blocker_player_id=player_id,
                target_player_id=target_player_id,
                item_type=target_item_type,
                expires_at=datetime.utcnow() + timedelta(hours=24),
            )
            db.add(blockade)
            _fire_pa_push(
                target_player_id,
                "Port Authority: Blockade Imposed",
                f"A blockade on your {target_item_type} transfers is now active for 24 hours.",
            )

        mission = PortAuthorityMission(
            pa_id=pa.id,
            mission_subtype=mission_subtype,
            target_player_id=target_player_id,
            target_item_type=target_item_type,
            target_quantity=target_quantity,
            items_acquired=json.dumps(items_acquired_summary) if items_acquired_summary else None,
            items_lost=json.dumps(items_lost_summary) if items_lost_summary else None,
            outcome="success" if success else "failure",
            resolved_at=datetime.utcnow(),
        )
        db.add(mission)
        db.commit()

        # Log losses to player ledger
        try:
            from stats_ux import log_transaction
            for it, qty in items_lost_summary.items():
                log_transaction(player_id, "pa_loss", "resource", 0.0,
                                f"Lost {qty:g} × {it} in failed {mission_subtype} mission",
                                item_type=it, quantity=qty)
        except Exception:
            pass

        outcome = "success" if success else "failure"
        if outcome == "success" and mission_subtype == "procurement" and items_acquired_summary:
            total_acq = sum(items_acquired_summary.values())
            body = f"Procurement succeeded — acquired {total_acq:g} × {target_item_type}."
        elif outcome == "success" and mission_subtype == "blockade":
            body = f"Blockade on {target_item_type} imposed for 24 hours."
        elif outcome == "success":
            body = f"{mission_subtype.capitalize()} mission succeeded."
        else:
            lost = sum(items_lost_summary.values())
            body = f"{mission_subtype.capitalize()} mission failed — lost {lost:g} units of materiel."
        _fire_pa_push(player_id, f"Port Authority: {mission_subtype.capitalize()} {outcome}", body)

        return True, {
            "outcome":          outcome,
            "mission_subtype":  mission_subtype,
            "target_player_id": target_player_id,
            "target_item_type": target_item_type,
            "items_acquired":   items_acquired_summary,
            "items_lost":       items_lost_summary,
        }
    except Exception as e:
        db.rollback()
        return False, {"error": str(e)}
    finally:
        db.close()


def submit_procurement_delivery(player_id: int, event_id: int) -> Tuple[bool, str]:
    """Submit PA inventory items to fulfill a federal procurement contract (GameEvent).

    The GameEvent must have event_type="procurement_contract" and be active.
    effect_data JSON schema: {
        "required_items": {"item_slug": quantity, ...},
        "per_slot_payment": 1500000.0,
        "slots_available": 3,
        "slots_filled": 0
    }
    """
    import json
    db = SessionLocal()
    try:
        pa = db.query(PortAuthorityInstance).filter_by(owner_id=player_id).first()
        if not pa:
            return False, "You do not own a Port Authority."

        from events import GameEvent
        ev = db.query(GameEvent).filter(
            GameEvent.id == event_id,
            GameEvent.is_active == True,
            GameEvent.event_type == "procurement_contract",
        ).first()
        if not ev:
            return False, "Contract not found or no longer active."

        now = datetime.utcnow()
        if ev.ends_at and ev.ends_at < now:
            return False, "Contract has expired."

        effect = json.loads(ev.effect_data or "{}")
        required_items = effect.get("required_items", {})
        per_slot_payment = float(effect.get("per_slot_payment", 0.0))
        slots_available = int(effect.get("slots_available", 1))
        slots_filled = int(effect.get("slots_filled", 0))

        if slots_filled >= slots_available:
            return False, "Contract is fully filled — no slots remaining."

        # Check PA inventory has all required items
        pa_inv = _get_pa_inventory(db, pa.id)
        for item_slug, qty_needed in required_items.items():
            if pa_inv.get(item_slug, 0) < qty_needed:
                return False, f"Insufficient {item_slug} in Port Authority inventory (need {qty_needed})."

        # Deduct items
        for item_slug, qty_needed in required_items.items():
            if not _pa_remove_item(db, pa.id, item_slug, float(qty_needed)):
                return False, f"Failed to deduct {item_slug}."

        # Pay player from government
        if per_slot_payment > 0:
            from reserve_banks import credit_usd
            credit_usd(player_id, per_slot_payment)
            try:
                from govt_ledger import log_gov_event
                log_gov_event("procurement_payment", "out", per_slot_payment, "USD",
                              counterparty=f"player:{player_id}",
                              description=f"PA procurement contract #{event_id} slot payment")
            except Exception:
                pass
            try:
                from stats_ux import log_transaction
                log_transaction(player_id, "procurement_contract", "money", per_slot_payment,
                                f"Federal procurement contract fulfilled (event #{event_id})",
                                reference_id=f"event-{event_id}")
            except Exception:
                pass

        # Update slots_filled
        effect["slots_filled"] = slots_filled + 1
        ev.effect_data = json.dumps(effect)
        if effect["slots_filled"] >= slots_available:
            ev.is_active = False  # contract fully filled

        # Record submission
        sub = ProcurementSubmission(
            player_id=player_id,
            event_id=event_id,
            payment_received_usd=per_slot_payment,
        )
        db.add(sub)
        db.commit()

        try:
            from events import record_task_progress
            record_task_progress(player_id, "procurement_delivery", 1)
        except Exception:
            pass

        _fire_pa_push(player_id, "Procurement Contract Filled",
                      f"Delivered items for contract #{event_id}. Received ${per_slot_payment:,.0f}.")

        return True, f"Contract fulfilled — ${per_slot_payment:,.0f} credited."
    except Exception as e:
        db.rollback()
        return False, str(e)
    finally:
        db.close()


def set_immigration_policy(player_id: int, volume: float, wealth: float) -> Tuple[bool, str]:
    """Update immigration policy for a player's Port Authority.

    volume: 0.0–3.0 multiplier on retail base_sale_chance
    wealth: 0.5–2.0 multiplier on effective price/elasticity
    """
    volume = max(0.0, min(3.0, float(volume)))
    wealth = max(0.5, min(2.0, float(wealth)))
    db = SessionLocal()
    try:
        pa = db.query(PortAuthorityInstance).filter_by(owner_id=player_id).first()
        if not pa:
            return False, "You do not own a Port Authority."
        pa.immigration_volume = volume
        pa.immigration_wealth = wealth
        db.commit()
        return True, f"Immigration policy updated: volume={volume:.2f}, wealth={wealth:.2f}."
    except Exception as e:
        db.rollback()
        return False, str(e)
    finally:
        db.close()


def get_active_blockades_against(player_id: int) -> list:
    """Return active blockades targeting this player."""
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        rows = db.query(BlockadeInstance).filter(
            BlockadeInstance.target_player_id == player_id,
            BlockadeInstance.expires_at > now,
            BlockadeInstance.lifted == False,
        ).all()
        return [{"id": r.id, "blocker_player_id": r.blocker_player_id,
                 "item_type": r.item_type, "expires_at": r.expires_at.isoformat()} for r in rows]
    finally:
        db.close()


def get_active_blockades_by(player_id: int) -> list:
    """Return active blockades placed by this player."""
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        rows = db.query(BlockadeInstance).filter(
            BlockadeInstance.blocker_player_id == player_id,
            BlockadeInstance.expires_at > now,
            BlockadeInstance.lifted == False,
        ).all()
        return [{"id": r.id, "target_player_id": r.target_player_id,
                 "item_type": r.item_type, "expires_at": r.expires_at.isoformat()} for r in rows]
    finally:
        db.close()


# Module-level cache for immigration modifiers
_imm_cache: tuple = (1.0, 1.0)
_imm_cache_ts: float = 0.0


def get_immigration_modifiers() -> tuple:
    """Return (volume_multiplier, wealth_multiplier) averaged across all active PAs.

    Called by supplydemand integration to adjust retail base_sale_chance and price.
    Cached for 60 seconds.
    """
    import time
    global _imm_cache, _imm_cache_ts
    now = time.time()
    if now - _imm_cache_ts < 60:
        return _imm_cache
    db = SessionLocal()
    try:
        pas = db.query(PortAuthorityInstance).all()
        if not pas:
            _imm_cache = (1.0, 1.0)
        else:
            avg_vol = sum(pa.immigration_volume or 1.0 for pa in pas) / len(pas)
            avg_wlth = sum(pa.immigration_wealth or 1.0 for pa in pas) / len(pas)
            _imm_cache = (avg_vol, avg_wlth)
        _imm_cache_ts = now
        return _imm_cache
    finally:
        db.close()


def is_item_blockaded(player_id: int, item_type: str) -> bool:
    """Check if player has an active blockade on this item type."""
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        row = db.query(BlockadeInstance).filter(
            BlockadeInstance.target_player_id == player_id,
            BlockadeInstance.item_type == item_type,
            BlockadeInstance.expires_at > now,
            BlockadeInstance.lifted == False,
        ).first()
        return row is not None
    finally:
        db.close()


def admin_get_all_port_authorities(limit: int = 200) -> List[dict]:
    """Admin view: every Port Authority with owner, inventory size and daily upkeep."""
    db = SessionLocal()
    try:
        pas = db.query(PortAuthorityInstance).limit(limit).all()
        out = []
        for pa in pas:
            inv = _get_pa_inventory(db, pa.id)
            daily_cost = sum(MAINTENANCE_DAILY.get(it, 0.0) * qty for it, qty in inv.items())
            fleet_ready, _ = _check_thresholds(inv, FLEET_THRESHOLDS)
            army_ready, _  = _check_thresholds(inv, ARMY_THRESHOLDS)
            out.append({
                "id":                pa.id,
                "owner_id":          pa.owner_id,
                "name":              pa.name,
                "inventory_types":   len(inv),
                "total_units":       sum(inv.values()),
                "daily_maintenance": daily_cost,
                "fleet_ready":       fleet_ready,
                "army_ready":        army_ready,
                "created_at":        pa.created_at.isoformat() if pa.created_at else None,
            })
        return out
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
                "id":               r.id,
                "mission_subtype":  r.mission_subtype,
                "target_player_id": r.target_player_id,
                "target_item_type": r.target_item_type,
                "target_quantity":  r.target_quantity,
                "items_acquired":   json.loads(r.items_acquired) if r.items_acquired else {},
                "items_lost":       json.loads(r.items_lost) if r.items_lost else {},
                "outcome":          r.outcome,
                "created_at":       r.created_at.isoformat() if r.created_at else None,
                "resolved_at":      r.resolved_at.isoformat() if r.resolved_at else None,
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
            if ok:
                # Upkeep was paid — record it in the player's ledger and skim the
                # federal upkeep tax into the government ledger.
                try:
                    from stats_ux import log_transaction
                    log_transaction(pa.owner_id, "pa_maintenance", "money", -daily_cost,
                                    f"Port Authority daily maintenance (${daily_cost:,.0f})")
                except Exception:
                    pass
                try:
                    from govt_ledger import log_gov_event
                    log_gov_event("pa_maintenance_tax", "in",
                                  daily_cost * PA_MAINTENANCE_TAX_RATE, "USD",
                                  counterparty=f"player:{pa.owner_id}",
                                  description=f"PA upkeep tax (PA#{pa.id})")
                except Exception:
                    pass
            else:
                # Cannot afford maintenance — destroy a random PA item as penalty
                items = [it for it, qty in inventory.items() if qty >= 1]
                if items:
                    victim = random.choice(items)
                    _pa_remove_item(db, pa.id, victim, 1.0)
                    _fire_pa_push(pa.owner_id, "Port Authority: Maintenance Failed",
                                  f"Could not afford ${daily_cost:,.0f} upkeep — "
                                  f"lost 1 × {victim}.")
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
    body             = await request.json()
    mission_subtype  = body.get("mission_subtype", "")
    target_player_id = body.get("target_player_id")
    target_item_type = body.get("target_item_type", "")
    target_quantity  = int(body.get("target_quantity", 1))
    ok, result = deploy_mission(pid, mission_subtype, target_player_id, target_item_type, target_quantity)
    return JSONResponse({"ok": ok, **result}, status_code=200 if ok else 400)


@router.post("/procurement/{event_id}")
async def api_procurement_delivery(event_id: int, request: Request):
    pid = _player_id(request)
    if not pid:
        return JSONResponse({"error": "Not logged in."}, status_code=401)
    ok, msg = submit_procurement_delivery(pid, event_id)
    return JSONResponse({"ok": ok, "message": msg}, status_code=200 if ok else 400)


@router.post("/immigration")
async def api_immigration(request: Request):
    pid = _player_id(request)
    if not pid:
        return JSONResponse({"error": "Not logged in."}, status_code=401)
    body   = await request.json()
    volume = float(body.get("volume", 1.0))
    wealth = float(body.get("wealth", 1.0))
    ok, msg = set_immigration_policy(pid, volume, wealth)
    return JSONResponse({"ok": ok, "message": msg}, status_code=200 if ok else 400)


@router.get("/missions")
async def api_missions(request: Request):
    pid = _player_id(request)
    if not pid:
        return JSONResponse({"error": "Not logged in."}, status_code=401)
    return JSONResponse({"missions": get_missions(pid)})


# Run table creation when module is imported
init_db()
