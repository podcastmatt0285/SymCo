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


class PortAuthorityInventory(Base):
    __tablename__ = "port_authority_inventory"
    __table_args__ = (UniqueConstraint("pa_id", "item_type"),)

    id        = Column(Integer, primary_key=True)
    pa_id     = Column(Integer, index=True, nullable=False)
    item_type = Column(String, nullable=False)
    quantity  = Column(Float, default=0.0)


class PAContract(Base):
    """Government procurement contract — admin-created, bid by PA owners."""
    __tablename__ = "pa_contracts"

    id                   = Column(Integer, primary_key=True)
    title                = Column(String, nullable=False)
    description          = Column(Text, nullable=True)
    required_items       = Column(Text, nullable=False)   # JSON {item_slug: qty}
    payment_usd          = Column(Float, nullable=False)  # total payout on fulfillment
    security_deposit_usd = Column(Float, nullable=False)  # deposit per bidder
    trophy_reward        = Column(Integer, default=0)
    fulfillment_days     = Column(Integer, default=14)    # days after bid close to fulfill
    selection_method     = Column(String, default="cheapest")  # "cheapest" | "best_volume"
    bid_opens_at         = Column(DateTime, nullable=False)
    bid_closes_at        = Column(DateTime, nullable=False)    # bid_opens_at + 5 days
    status               = Column(String, default="bidding")   # bidding|awarded|fulfilled|forfeited|expired
    winner_player_id     = Column(Integer, nullable=True)
    winning_bid_id       = Column(Integer, nullable=True)
    fulfill_deadline     = Column(DateTime, nullable=True)
    created_by           = Column(Integer, nullable=True)
    created_at           = Column(DateTime, default=datetime.utcnow)


class PAContractBid(Base):
    """A player's bid on a PAContract."""
    __tablename__ = "pa_contract_bids"

    id                    = Column(Integer, primary_key=True)
    contract_id           = Column(Integer, index=True, nullable=False)
    player_id             = Column(Integer, index=True, nullable=False)
    bid_price_usd         = Column(Float, default=0.0)        # for "cheapest" — player's charge
    bid_volume_multiplier = Column(Float, default=1.0)        # for "best_volume" — extra volume offered
    deposit_paid_usd      = Column(Float, default=0.0)
    status                = Column(String, default="pending") # pending|won|lost|fulfilled|forfeited
    submitted_at          = Column(DateTime, default=datetime.utcnow)
    deposit_returned      = Column(Boolean, default=False)
    # Progressive fulfillment: {item_slug: qty_shipped_so_far}
    fulfilled_items       = Column(Text, default="{}")


class ImmigrationPolicy(Base):
    """Per-player immigration slider policy with 3-day decay and 7-day cooldown."""
    __tablename__ = "immigration_policies"

    id           = Column(Integer, primary_key=True)
    pa_id        = Column(Integer, index=True, nullable=False)
    player_id    = Column(Integer, index=True, nullable=False, unique=True)
    # Slider values: -1.0 (full left) to +1.0 (full right), 0.0 = neutral
    s_quantity_affluence  = Column(Float, default=0.0)   # −=many  +=wealthy
    s_labor_consumers     = Column(Float, default=0.0)   # −=labor +=consumers
    s_skilled_unskilled   = Column(Float, default=0.0)   # −=skilled +=unskilled
    s_young_mature        = Column(Float, default=0.0)   # −=young +=mature
    s_assimilated_diverse = Column(Float, default=0.0)   # −=assimilated +=diverse
    s_selective_open      = Column(Float, default=0.0)   # −=selective +=open
    s_urban_rural         = Column(Float, default=0.0)   # −=urban +=rural
    s_inland_coastal      = Column(Float, default=0.0)   # −=inland +=coastal
    s_farmer_urbanworker  = Column(Float, default=0.0)   # −=farmer +=urban worker
    s_conserve_intensive  = Column(Float, default=0.0)   # −=conserve +=intensive
    # Timing
    committed_at   = Column(DateTime, nullable=True)   # when policy was committed
    expires_at     = Column(DateTime, nullable=True)   # committed_at + 3 days
    cooldown_until = Column(DateTime, nullable=True)   # expires_at + 7 days (10d from commit)


# ─────────────────────────────────────────────────────────────────────────────
# Immigration score computation (pure, no DB calls)
# ─────────────────────────────────────────────────────────────────────────────

_SLIDER_FIELDS = [
    "s_quantity_affluence", "s_labor_consumers", "s_skilled_unskilled",
    "s_young_mature", "s_assimilated_diverse", "s_selective_open",
    "s_urban_rural", "s_inland_coastal", "s_farmer_urbanworker", "s_conserve_intensive",
]

# Coefficient table: each slider contributes its value × coeff to each dimension.
# demand/production/land_yield: >1.0 is a buff. elasticity/input_cost: >1.0 is a debuff.
_SLIDER_COEFFS = {
    #                           demand  elasticity  production  input_cost  land_yield
    "s_quantity_affluence":  (  -1,     -1,          0,          0,          0  ),
    "s_labor_consumers":     (  +1,      0,         -1,          0,          0  ),
    "s_skilled_unskilled":   (   0,      0,         -1,         -1,          0  ),
    "s_young_mature":        (  -1,     -1,          0,          0,          0  ),
    "s_assimilated_diverse": (  +1,     +1,          0,          0,          0  ),
    "s_selective_open":      (  +1,     -1,          0,          0,          0  ),
    "s_urban_rural":         (  -1,      0,          0,          0,         +1  ),
    "s_inland_coastal":      (   0,      0,         -1,         -1,          0  ),
    "s_farmer_urbanworker":  (   0,      0,         +1,          0,         -1  ),
    "s_conserve_intensive":  (   0,      0,          0,         +1,         +1  ),
}
_DIM_IDX = {"demand": 0, "elasticity": 1, "production": 2, "input_cost": 3, "land_yield": 4}
_INTENSITY = 0.046   # 4.6% max shift per dimension


def compute_immigration_score(sliders: dict, decay_factor: float = 1.0) -> dict:
    """Pure function: compute output dimension multipliers from slider values + decay.

    sliders: {field_name: float, ...} for all 10 slider columns
    decay_factor: 1.0 at commit, 0.0 at expiry

    Returns dict with keys: demand, elasticity, production, input_cost, land_yield.
    All values are multipliers (1.0 = no effect).
    """
    totals = [0.0, 0.0, 0.0, 0.0, 0.0]
    counts = [0,   0,   0,   0,   0  ]
    for field, coeffs in _SLIDER_COEFFS.items():
        v = sliders.get(field, 0.0) * decay_factor
        for i, c in enumerate(coeffs):
            if c != 0:
                totals[i] += v * c
                counts[i] += 1

    dims = {}
    for name, idx in _DIM_IDX.items():
        avg = totals[idx] / counts[idx] if counts[idx] else 0.0
        dims[name] = round(1.0 + avg * _INTENSITY, 6)
    return dims


def get_decay_factor(committed_at, expires_at) -> float:
    """Linear decay from 1.0 at commit to 0.0 at expiry."""
    if committed_at is None or expires_at is None:
        return 0.0
    now = datetime.utcnow()
    if now >= expires_at:
        return 0.0
    total = (expires_at - committed_at).total_seconds()
    if total <= 0:
        return 0.0
    elapsed = (now - committed_at).total_seconds()
    return max(0.0, 1.0 - elapsed / total)


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
    """Return PA info + command inventory for *player_id*."""
    db = SessionLocal()
    try:
        pa = db.query(PortAuthorityInstance).filter_by(owner_id=player_id).first()
        if not pa:
            return None
        inventory = _get_pa_inventory(db, pa.id)
        daily_cost = sum(MAINTENANCE_DAILY.get(it, 0) * qty for it, qty in inventory.items())
        return {
            "id":                    pa.id,
            "owner_id":              pa.owner_id,
            "name":                  pa.name,
            "created_at":            pa.created_at.isoformat() if pa.created_at else None,
            "last_maintenance_tick": pa.last_maintenance_tick,
            "inventory":             inventory,
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


GOVERNMENT_PLAYER_ID = 0


def submit_contract_bid(
    player_id: int,
    contract_id: int,
    bid_price_usd: float,
    bid_volume_multiplier: float = 1.0,
) -> Tuple[bool, str]:
    """Submit a bid on an open PAContract.

    Deducts the security deposit from the player and credits it to government.
    Only one bid per player per contract is allowed.
    """
    import json as _j
    db = SessionLocal()
    try:
        pa = db.query(PortAuthorityInstance).filter_by(owner_id=player_id).first()
        if not pa:
            return False, "You do not own a Port Authority."

        contract = db.query(PAContract).filter_by(id=contract_id).first()
        if not contract:
            return False, "Contract not found."
        now = datetime.utcnow()
        if contract.status != "bidding":
            return False, "This contract is no longer accepting bids."
        if now >= contract.bid_closes_at:
            return False, "Bidding window has closed."

        existing = db.query(PAContractBid).filter_by(
            contract_id=contract_id, player_id=player_id
        ).first()
        if existing:
            return False, "You have already submitted a bid for this contract."

        deposit = contract.security_deposit_usd
        from reserve_banks import spend_player_funds, credit_usd
        ok_dep, dep_err = spend_player_funds(player_id, deposit)
        if not ok_dep:
            return False, dep_err or f"Insufficient funds — security deposit of ${deposit:,.0f} required."
        credit_usd(GOVERNMENT_PLAYER_ID, deposit)

        bid = PAContractBid(
            contract_id=contract_id,
            player_id=player_id,
            bid_price_usd=float(bid_price_usd),
            bid_volume_multiplier=float(bid_volume_multiplier),
            deposit_paid_usd=deposit,
            status="pending",
            deposit_returned=False,
        )
        db.add(bid)
        db.commit()
        db.refresh(bid)

        try:
            from stats_ux import log_transaction
            log_transaction(player_id, "pa_contract_deposit", "money", -deposit,
                            f"Security deposit — PA contract #{contract_id}: {contract.title}")
        except Exception:
            pass
        try:
            from govt_ledger import log_gov_event
            log_gov_event("pa_contract_deposit", "in", deposit, "USD",
                          counterparty=f"player:{player_id}",
                          description=f"Security deposit for PA contract #{contract_id}")
        except Exception:
            pass

        _fire_pa_push(player_id, "Bid Submitted",
                      f"Your bid on '{contract.title}' has been received. "
                      f"Security deposit of ${deposit:,.0f} held. Bid closes "
                      f"{contract.bid_closes_at.strftime('%Y-%m-%d %H:%M UTC')}.")
        return True, f"Bid submitted. Security deposit of ${deposit:,.0f} deducted."
    except Exception as e:
        db.rollback()
        return False, str(e)
    finally:
        db.close()


def close_contract_bids(contract_id: int):
    """Select a winner from pending bids, return deposits to losers.

    Called from tick() when bid_closes_at has passed.
    """
    db = SessionLocal()
    try:
        contract = db.query(PAContract).filter_by(id=contract_id).first()
        if not contract or contract.status != "bidding":
            return
        bids = db.query(PAContractBid).filter_by(
            contract_id=contract_id, status="pending"
        ).all()
        if not bids:
            contract.status = "expired"
            db.commit()
            print(f"[PA] Contract #{contract_id} expired — no bids.")
            return

        # Select winner
        if contract.selection_method == "best_volume":
            winner_bid = max(bids, key=lambda b: b.bid_volume_multiplier)
        else:
            winner_bid = min(bids, key=lambda b: b.bid_price_usd)

        now = datetime.utcnow()
        winner_bid.status = "won"
        contract.status = "awarded"
        contract.winner_player_id = winner_bid.player_id
        contract.winning_bid_id = winner_bid.id
        contract.fulfill_deadline = now + timedelta(days=contract.fulfillment_days)

        from reserve_banks import credit_usd, debit_usd
        # Return deposits to losers
        for bid in bids:
            if bid.id == winner_bid.id:
                continue
            bid.status = "lost"
            if not bid.deposit_returned:
                credit_usd(bid.player_id, bid.deposit_paid_usd)
                debit_usd(GOVERNMENT_PLAYER_ID, bid.deposit_paid_usd)
                bid.deposit_returned = True
                try:
                    from stats_ux import log_transaction
                    log_transaction(bid.player_id, "pa_contract_deposit_return", "money",
                                    bid.deposit_paid_usd,
                                    f"Security deposit returned — lost bid on contract #{contract_id}")
                except Exception:
                    pass
            _fire_pa_push(bid.player_id, "Contract Bid Lost",
                          f"Your bid on '{contract.title}' was not selected. "
                          f"Security deposit of ${bid.deposit_paid_usd:,.0f} has been returned.")

        db.commit()

        _fire_pa_push(winner_bid.player_id, "🏆 Government Contract Won!",
                      f"You won the contract: '{contract.title}'! "
                      f"Fulfill by {contract.fulfill_deadline.strftime('%Y-%m-%d %H:%M UTC')}. "
                      f"Gather the required items and declare shipment from your Port Authority.")
        print(f"[PA] Contract #{contract_id} awarded to player {winner_bid.player_id}.")
    except Exception as e:
        db.rollback()
        print(f"[PA] close_contract_bids #{contract_id} error: {e}")
    finally:
        db.close()


def fulfill_contract(player_id: int, contract_id: int) -> Tuple[bool, dict]:
    """Progressive fulfillment: auto-pull what the player has toward the contract quota.

    Each call ships as much as possible from the player's regular inventory.
    Returns (ok, result) where result contains progress per item and whether fully_completed.
    """
    import json as _j
    db = SessionLocal()
    try:
        contract = db.query(PAContract).filter_by(id=contract_id).first()
        if not contract:
            return False, {"error": "Contract not found."}
        if contract.status != "awarded":
            return False, {"error": "This contract is not in an awarded state."}
        if contract.winner_player_id != player_id:
            return False, {"error": "You did not win this contract."}

        now = datetime.utcnow()
        if contract.fulfill_deadline and now > contract.fulfill_deadline:
            return False, {"error": "Fulfillment deadline has passed."}

        bid = db.query(PAContractBid).filter_by(
            contract_id=contract_id, player_id=player_id
        ).first()
        if not bid or bid.status != "won":
            return False, {"error": "No active winning bid found."}

        required_items = _j.loads(contract.required_items or "{}")
        fulfilled_so_far = _j.loads(bid.fulfilled_items or "{}")

        from inventory import get_player_inventory, transfer_item
        inv = get_player_inventory(player_id)

        shipped_now: Dict[str, float] = {}
        for item_slug, qty_total in required_items.items():
            already = fulfilled_so_far.get(item_slug, 0.0)
            still_needed = qty_total - already
            if still_needed <= 0:
                continue
            available = inv.get(item_slug, 0.0)
            can_ship = min(available, still_needed)
            if can_ship > 0:
                ok = transfer_item(player_id, GOVERNMENT_PLAYER_ID, item_slug, can_ship)
                if ok:
                    fulfilled_so_far[item_slug] = already + can_ship
                    shipped_now[item_slug] = can_ship

        bid.fulfilled_items = _j.dumps(fulfilled_so_far)

        # Check if fully complete
        fully_complete = all(
            fulfilled_so_far.get(slug, 0.0) >= qty
            for slug, qty in required_items.items()
        )

        if fully_complete:
            from reserve_banks import credit_usd, debit_usd
            # Reverse auction: "cheapest" winners are paid THEIR winning bid (they keep
            # the margin over their cost); "best_volume" winners are paid the fixed payment.
            base_payment = (bid.bid_price_usd
                            if contract.selection_method == "cheapest"
                            else contract.payment_usd)
            # CDO executive boosts contract payment
            effective_payment = base_payment
            try:
                from executive import get_player_job_bonus
                from database import SessionLocal as _ES
                _edb = _ES()
                try:
                    _mil_bonus = get_player_job_bonus(_edb, player_id, "military")
                finally:
                    _edb.close()
                effective_payment = base_payment * (1.0 + _mil_bonus)
            except Exception:
                pass
            credit_usd(player_id, effective_payment)
            debit_usd(GOVERNMENT_PLAYER_ID, effective_payment)

            if bid and not bid.deposit_returned:
                credit_usd(player_id, bid.deposit_paid_usd)
                debit_usd(GOVERNMENT_PLAYER_ID, bid.deposit_paid_usd)
                bid.deposit_returned = True

            bid.status = "fulfilled"
            contract.status = "fulfilled"
            db.commit()

            # Award trophies
            if contract.trophy_reward and contract.trophy_reward > 0:
                try:
                    from events import _award_event_trophies, SessionLocal as _ES

                    class _SyntheticEv:
                        id = contract.id
                        title = contract.title
                        task_metric = None

                    _tdb = _ES()
                    try:
                        _award_event_trophies(_tdb, _SyntheticEv(), player_id,
                                             contract.trophy_reward, now)
                        _tdb.commit()
                    finally:
                        _tdb.close()
                except Exception as _te:
                    print(f"[PA] trophy award error: {_te}")

            try:
                from stats_ux import log_transaction
                log_transaction(player_id, "pa_contract_payment", "money", effective_payment,
                                f"Gov contract fulfilled (tax-free): {contract.title}",
                                reference_id=f"pa-contract-{contract_id}")
            except Exception:
                pass
            try:
                from govt_ledger import log_gov_event
                log_gov_event("pa_contract_payment", "out", effective_payment, "USD",
                              counterparty=f"player:{player_id}",
                              description=f"PA contract fulfilled: {contract.title} (#{contract_id})")
            except Exception:
                pass

            dep_back = bid.deposit_paid_usd if bid else 0
            _fire_pa_push(player_id, "🎉 Contract Fully Fulfilled!",
                          f"'{contract.title}' — received ${effective_payment:,.0f} "
                          f"(tax-free) + {contract.trophy_reward} trophies + "
                          f"${dep_back:,.0f} security deposit returned.")
            return True, {
                "fully_completed": True,
                "shipped_now": shipped_now,
                "fulfilled": fulfilled_so_far,
                "payment_usd": effective_payment,
                "trophies": contract.trophy_reward,
                "message": f"Contract fully fulfilled! ${effective_payment:,.0f} credited + {contract.trophy_reward} trophies.",
            }
        else:
            db.commit()
            progress = {
                slug: {"shipped": fulfilled_so_far.get(slug, 0.0), "required": qty}
                for slug, qty in required_items.items()
            }
            shipped_total = sum(shipped_now.values())
            if shipped_total == 0:
                msg = "Nothing new to ship — check your inventory for the required items."
            else:
                msg = f"Shipped {shipped_total:g} units. Contract progress updated."
            return True, {
                "fully_completed": False,
                "shipped_now": shipped_now,
                "fulfilled": fulfilled_so_far,
                "progress": progress,
                "message": msg,
            }
    except Exception as e:
        db.rollback()
        return False, {"error": str(e)}
    finally:
        db.close()


def check_contract_forfeitures():
    """Forfeit overdue awarded contracts — government keeps deposit, contract restarts."""
    import json as _j
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        overdue = db.query(PAContract).filter(
            PAContract.status == "awarded",
            PAContract.fulfill_deadline < now,
        ).all()
        for contract in overdue:
            # Mark forfeited
            contract.status = "forfeited"
            winner_pid = contract.winner_player_id
            winning_bid = db.query(PAContractBid).filter_by(
                contract_id=contract.id, player_id=winner_pid
            ).first()
            if winning_bid:
                winning_bid.status = "forfeited"

            db.flush()

            # Notify the forfeiting winner
            if winner_pid:
                _fire_pa_push(winner_pid, "Contract Forfeited",
                              f"You failed to fulfill '{contract.title}' by the deadline. "
                              f"Your security deposit of ${winning_bid.deposit_paid_usd if winning_bid else 0:,.0f} "
                              f"has been kept by the government.")
                try:
                    from govt_ledger import log_gov_event
                    dep = winning_bid.deposit_paid_usd if winning_bid else 0
                    log_gov_event("pa_contract_forfeiture", "in", dep, "USD",
                                  counterparty=f"player:{winner_pid}",
                                  description=f"Forfeited deposit: PA contract #{contract.id}")
                except Exception:
                    pass

            # Restart: create a new contract with same parameters, preserving the
            # original bid window (don't reset everything to a hardcoded 5 days).
            window = contract.bid_closes_at - contract.bid_opens_at
            if window <= timedelta(0):
                window = timedelta(days=5)
            new_contract = PAContract(
                title=contract.title,
                description=contract.description,
                required_items=contract.required_items,
                payment_usd=contract.payment_usd,
                security_deposit_usd=contract.security_deposit_usd,
                trophy_reward=contract.trophy_reward,
                fulfillment_days=contract.fulfillment_days,
                selection_method=contract.selection_method,
                bid_opens_at=now,
                bid_closes_at=now + window,
                status="bidding",
                created_by=contract.created_by,
            )
            db.add(new_contract)
            db.flush()

            # Push to all PA owners about the re-issued contract
            try:
                owners = db.query(PortAuthorityInstance).all()
                for pa in owners:
                    _fire_pa_push(pa.owner_id, "📋 Government Contract Re-Issued",
                                  f"'{contract.title}' is available for bidding again. "
                                  f"Bid window closes in {window.days} day(s).")
            except Exception:
                pass

        if overdue:
            db.commit()
            print(f"[PA] Forfeited {len(overdue)} overdue contract(s).")
    except Exception as e:
        db.rollback()
        print(f"[PA] check_contract_forfeitures error: {e}")
    finally:
        db.close()


def get_open_contracts() -> List[dict]:
    """Return all contracts currently accepting bids."""
    import json as _j
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        rows = db.query(PAContract).filter(
            PAContract.status == "bidding",
            PAContract.bid_closes_at > now,
        ).order_by(PAContract.bid_closes_at).all()
        return [_contract_to_dict(c) for c in rows]
    finally:
        db.close()


def get_player_bids(player_id: int, limit: int = 20) -> List[dict]:
    """Return recent bids by this player."""
    db = SessionLocal()
    try:
        bids = (
            db.query(PAContractBid)
            .filter_by(player_id=player_id)
            .order_by(PAContractBid.submitted_at.desc())
            .limit(limit)
            .all()
        )
        result = []
        for b in bids:
            c = db.query(PAContract).filter_by(id=b.contract_id).first()
            result.append({
                "bid_id":              b.id,
                "contract_id":         b.contract_id,
                "contract_title":      c.title if c else "—",
                "bid_price_usd":       b.bid_price_usd,
                "bid_volume_multiplier": b.bid_volume_multiplier,
                "deposit_paid_usd":    b.deposit_paid_usd,
                "status":              b.status,
                "deposit_returned":    b.deposit_returned,
                "submitted_at":        b.submitted_at.isoformat() if b.submitted_at else None,
            })
        return result
    finally:
        db.close()


def get_won_contract(player_id: int) -> Optional[dict]:
    """Return the player's currently active awarded (won, not fulfilled) contract with progress."""
    import json as _j
    db = SessionLocal()
    try:
        bid = db.query(PAContractBid).filter_by(
            player_id=player_id, status="won"
        ).first()
        if not bid:
            return None
        contract = db.query(PAContract).filter_by(id=bid.contract_id).first()
        if not contract or contract.status != "awarded":
            return None
        d = _contract_to_dict(contract)
        d["deposit_paid_usd"] = bid.deposit_paid_usd
        d["bid_id"] = bid.id
        d["winning_bid_price_usd"] = bid.bid_price_usd
        d["fulfilled_items"] = _j.loads(bid.fulfilled_items or "{}")
        return d
    finally:
        db.close()


def _contract_to_dict(c: PAContract) -> dict:
    import json as _j
    return {
        "id":                   c.id,
        "title":                c.title,
        "description":          c.description,
        "required_items":       _j.loads(c.required_items or "{}"),
        "payment_usd":          c.payment_usd,
        "security_deposit_usd": c.security_deposit_usd,
        "trophy_reward":        c.trophy_reward,
        "fulfillment_days":     c.fulfillment_days,
        "selection_method":     c.selection_method,
        "bid_opens_at":         c.bid_opens_at.isoformat() if c.bid_opens_at else None,
        "bid_closes_at":        c.bid_closes_at.isoformat() if c.bid_closes_at else None,
        "status":               c.status,
        "winner_player_id":     c.winner_player_id,
        "fulfill_deadline":     c.fulfill_deadline.isoformat() if c.fulfill_deadline else None,
    }


def admin_get_all_contracts(limit: int = 100) -> List[dict]:
    """Admin: all PAContracts ordered by newest first."""
    import json as _j
    db = SessionLocal()
    try:
        rows = db.query(PAContract).order_by(PAContract.id.desc()).limit(limit).all()
        result = []
        for c in rows:
            bid_count = db.query(PAContractBid).filter_by(contract_id=c.id).count()
            d = _contract_to_dict(c)
            d["bid_count"] = bid_count
            result.append(d)
        return result
    finally:
        db.close()


def admin_cancel_contract(contract_id: int) -> Tuple[bool, str]:
    """Admin: cancel a contract and void it.

    Works on both "bidding" (return all pending deposits) and "awarded" contracts
    (return the winner's deposit AND any items they already shipped progressively).
    """
    import json as _j
    db = SessionLocal()
    try:
        contract = db.query(PAContract).filter_by(id=contract_id).first()
        if not contract:
            return False, "Contract not found."
        if contract.status not in ("bidding", "awarded"):
            return False, f"Cannot cancel a contract with status '{contract.status}'."

        from reserve_banks import credit_usd, debit_usd

        # Return deposits for any still-active bids (pending on bidding, won on awarded).
        bids = db.query(PAContractBid).filter(
            PAContractBid.contract_id == contract_id,
            PAContractBid.status.in_(("pending", "won")),
        ).all()
        returned_items_note = ""
        for bid in bids:
            if not bid.deposit_returned:
                credit_usd(bid.player_id, bid.deposit_paid_usd)
                debit_usd(GOVERNMENT_PLAYER_ID, bid.deposit_paid_usd)
                bid.deposit_returned = True

            # If this is the awarded winner, return any items they already shipped.
            if bid.status == "won" and bid.fulfilled_items:
                try:
                    from inventory import transfer_item
                    shipped = _j.loads(bid.fulfilled_items or "{}")
                    for slug, qty in shipped.items():
                        if qty and qty > 0:
                            transfer_item(GOVERNMENT_PLAYER_ID, bid.player_id, slug, float(qty))
                    if shipped:
                        returned_items_note = " Shipped items were returned."
                except Exception as _ie:
                    print(f"[PA] item return on cancel error: {_ie}")

            bid.status = "lost"
            _fire_pa_push(bid.player_id, "Contract Cancelled",
                          f"The contract '{contract.title}' was cancelled by the government. "
                          f"Your security deposit of ${bid.deposit_paid_usd:,.0f} has been returned.")

        contract.status = "expired"
        db.commit()
        return True, (f"Contract #{contract_id} cancelled; "
                      f"{len(bids)} deposit(s) returned.{returned_items_note}")
    except Exception as e:
        db.rollback()
        return False, str(e)
    finally:
        db.close()


# ======================================================================
# CONTRACT LIBRARY  —  hand-authored contracts, added one at a time
# ======================================================================
#
# Contracts are NOT created from a blank admin form. Each one is authored
# here in code as a fully-specified Python definition, then posted to
# players (when ready) from the admin PA Contracts page.
#
# To add a contract: append one dict to CONTRACT_LIBRARY below. Schema:
#
#   {
#       "key":            "feed_the_homeless",      # unique stable slug
#       "title":          "Federal Government: Feeding the Homeless",
#       "description":    "Short flavor text shown to players.",
#       "required_items": {"burger": 100000, "bread": 1000000},  # slug -> qty
#       "payment_usd":            50_000_000,       # ONLY for "best_volume" (fixed payout).
#                                                   #   OMIT for "cheapest" — those winners
#                                                   #   are paid their own winning bid.
#       "security_deposit_usd":    5_000_000,       # refundable bid deposit
#       "trophy_reward":   500,
#       "fulfillment_days": 14,                     # days to fulfill after bid window closes
#       "bid_window_days":  5,                      # optional, days bidding stays open (default 5)
#       "selection_method": "cheapest",             # "cheapest" | "best_volume"
#   }
#
# Item slugs are validated against the live item catalog at post time, so a
# typo is caught before the contract goes live (no silent broken contracts).
#
CONTRACT_LIBRARY: List[dict] = [
    {
        "key": "wazzy_appleseed",
        "title": "Wazzy Appleseed",
        "description": (
            "In the spirit of Johnny Appleseed, the federal government is launching a "
            "nationwide planting drive to grow food across the country. It needs a vast "
            "supply of seeds and fresh greens. The government will pay up to $1 per apple "
            "seed, up to $1 per orange seed, and up to $7 per head of lettuce. Submit your "
            "best TOTAL price — the cheapest total bid wins, and you are paid your winning "
            "bid (you keep the difference over your production cost as profit)."
        ),
        "required_items": {
            "apple_seeds": 10_000_000,
            "orange_seeds": 10_000_000,
            "lettuce": 1_000_000,
        },
        "security_deposit_usd": 500_000,
        "trophy_reward": 125,
        "fulfillment_days": 27,
        "bid_window_days": 3,
        "selection_method": "cheapest",
    },
]


def get_contract_library() -> List[dict]:
    """Return the hand-authored contract definitions for the admin page."""
    return CONTRACT_LIBRARY


def _valid_item_slugs() -> set:
    """Live item catalog used to validate contract item slugs at post time."""
    try:
        from admins import get_all_item_types
        return set(get_all_item_types())
    except Exception:
        return set()


def post_library_contract(key: str, admin_id: int,
                          bid_opens_at: Optional[datetime] = None) -> Tuple[bool, str]:
    """Create a live PAContract from a CONTRACT_LIBRARY definition and notify PA owners.

    Validates every required-item slug against the live catalog first.
    """
    import json as _j

    definition = next((c for c in CONTRACT_LIBRARY if c.get("key") == key), None)
    if not definition:
        return False, f"No contract definition found for key '{key}'."

    req = definition.get("required_items") or {}
    if not isinstance(req, dict) or not req:
        return False, "Contract definition has no required_items."

    # Validate slugs against the live catalog (skip if catalog unavailable)
    catalog = _valid_item_slugs()
    if catalog:
        bad = [slug for slug in req if slug not in catalog]
        if bad:
            return False, f"Unknown item slug(s) in '{key}': {', '.join(bad)}"

    now = datetime.utcnow()
    opens = bid_opens_at or now
    window_days = int(definition.get("bid_window_days", 5))
    closes = opens + timedelta(days=window_days)

    db = SessionLocal()
    try:
        contract = PAContract(
            title=definition["title"].strip(),
            description=(definition.get("description") or "").strip() or None,
            required_items=_j.dumps(req),
            payment_usd=float(definition.get("payment_usd", 0) or 0),
            security_deposit_usd=float(definition["security_deposit_usd"]),
            trophy_reward=int(definition.get("trophy_reward", 500)),
            fulfillment_days=int(definition.get("fulfillment_days", 14)),
            selection_method=definition.get("selection_method", "cheapest"),
            bid_opens_at=opens,
            bid_closes_at=closes,
            status="bidding",
            created_by=admin_id,
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)
        cid = contract.id
        title = contract.title
        payment = contract.payment_usd
        method = contract.selection_method
        trophies = contract.trophy_reward
    except Exception as e:
        db.rollback()
        return False, str(e)
    finally:
        db.close()

    # Payment phrasing: "cheapest" pays the winner's own bid, so there's no figure
    # to advertise; "best_volume" has a fixed payout.
    if method == "best_volume" and payment > 0:
        pay_phrase = f"${payment:,.0f} + {trophies} trophies"
    else:
        pay_phrase = f"{trophies} trophies + your winning bid"

    # Notify all PA owners
    try:
        from push_ux import send_push_notification
        _db2 = SessionLocal()
        try:
            owners = _db2.query(PortAuthorityInstance).all()
            for pa in owners:
                send_push_notification(
                    pa.owner_id,
                    "📋 New Government Contract Available",
                    f"'{title}' — {pay_phrase}. "
                    f"Bidding closes in {window_days} day(s).",
                    url="/port-authority",
                    notif_type="institutions",
                    tag=f"pa-contract-{cid}",
                )
        finally:
            _db2.close()
    except Exception as ne:
        print(f"[PortAuthority] contract post push error: {ne}")

    return True, f"Contract '{title}' posted (ID {cid}). PA owners notified."


def commit_immigration_policy(player_id: int, sliders: dict) -> Tuple[bool, str]:
    """Commit an immigration slider policy for this player's PA.

    sliders: {field: float} for all 10 s_* columns, values clamped to [-1.0, 1.0].
    Requires cooldown_until IS NULL or in the past.
    Sets expires_at = now+3d, cooldown_until = now+10d.
    """
    db = SessionLocal()
    try:
        pa = db.query(PortAuthorityInstance).filter_by(owner_id=player_id).first()
        if not pa:
            return False, "You do not own a Port Authority."
        now = datetime.utcnow()
        # Check cooldown
        existing = db.query(ImmigrationPolicy).filter_by(player_id=player_id).first()
        if existing and existing.cooldown_until and existing.cooldown_until > now:
            delta = existing.cooldown_until - now
            days = delta.days
            hrs  = delta.seconds // 3600
            return False, f"Immigration cooldown active — available in {days}d {hrs}h."
        # Validate and clamp slider values
        clean = {}
        for field in _SLIDER_FIELDS:
            val = float(sliders.get(field, 0.0))
            clean[field] = max(-1.0, min(1.0, val))
        expires   = now + timedelta(days=3)
        cooldown  = now + timedelta(days=10)
        if existing:
            for f, v in clean.items():
                setattr(existing, f, v)
            existing.committed_at   = now
            existing.expires_at     = expires
            existing.cooldown_until = cooldown
        else:
            existing = ImmigrationPolicy(
                pa_id=pa.id, player_id=player_id,
                committed_at=now, expires_at=expires, cooldown_until=cooldown,
                **clean,
            )
            db.add(existing)
        db.commit()
        _imm_player_cache.pop(player_id, None)
        _fire_pa_push(player_id,
                      "Immigration Policy Active",
                      "Your immigration policy is now in effect for 3 days.",
                      "/port-authority")
        return True, "Immigration policy committed — active for 3 days, then 7-day cooldown."
    except Exception as e:
        db.rollback()
        return False, str(e)
    finally:
        db.close()


def get_player_immigration_mults(player_id: int) -> dict:
    """Return immigration dimension multipliers for *player_id*.

    If no active policy (or expired), returns all-1.0 dict (no effect).
    Cached per-player for 30 seconds.
    """
    import time
    now_ts = time.time()
    cached = _imm_player_cache.get(player_id)
    if cached and now_ts - cached[1] < _IMM_CACHE_TTL:
        return cached[0]

    neutral = {"demand": 1.0, "elasticity": 1.0, "production": 1.0,
               "input_cost": 1.0, "land_yield": 1.0}
    db = SessionLocal()
    try:
        pol = db.query(ImmigrationPolicy).filter_by(player_id=player_id).first()
        if not pol or not pol.expires_at:
            result = neutral
        else:
            df = get_decay_factor(pol.committed_at, pol.expires_at)
            if df <= 0.0:
                result = neutral
            else:
                sliders = {f: getattr(pol, f, 0.0) for f in _SLIDER_FIELDS}
                result = compute_immigration_score(sliders, df)
        _imm_player_cache[player_id] = (result, now_ts)
        return result
    finally:
        db.close()


def get_immigration_status(player_id: int) -> dict:
    """Return full immigration status dict for the UI (sliders, decay, cooldown, mults)."""
    db = SessionLocal()
    try:
        pol = db.query(ImmigrationPolicy).filter_by(player_id=player_id).first()
        now = datetime.utcnow()
        if not pol:
            return {
                "active": False, "cooldown": False,
                "sliders": {f: 0.0 for f in _SLIDER_FIELDS},
                "decay_factor": 0.0, "mults": None,
                "expires_at": None, "cooldown_until": None,
            }
        df = get_decay_factor(pol.committed_at, pol.expires_at) if pol.expires_at else 0.0
        in_cooldown = bool(pol.cooldown_until and pol.cooldown_until > now)
        active = df > 0.0
        sliders = {f: getattr(pol, f, 0.0) for f in _SLIDER_FIELDS}
        mults = compute_immigration_score(sliders, df) if active else None
        return {
            "active": active,
            "cooldown": in_cooldown and not active,
            "sliders": sliders,
            "decay_factor": round(df, 4),
            "mults": mults,
            "expires_at":     pol.expires_at.isoformat() if pol.expires_at else None,
            "cooldown_until": pol.cooldown_until.isoformat() if pol.cooldown_until else None,
            "committed_at":   pol.committed_at.isoformat() if pol.committed_at else None,
        }
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
            out.append({
                "id":                pa.id,
                "owner_id":          pa.owner_id,
                "name":              pa.name,
                "inventory_types":   len(inv),
                "total_units":       sum(inv.values()),
                "daily_maintenance": daily_cost,
                "created_at":        pa.created_at.isoformat() if pa.created_at else None,
            })
        return out
    finally:
        db.close()


def _process_contract_bids(now: datetime):
    """Close any contracts whose bid window has ended."""
    db = SessionLocal()
    try:
        overdue_bids = db.query(PAContract).filter(
            PAContract.status == "bidding",
            PAContract.bid_closes_at <= now,
        ).all()
        contract_ids = [c.id for c in overdue_bids]
    finally:
        db.close()
    for cid in contract_ids:
        close_contract_bids(cid)


def tick(current_tick: int, now: datetime):
    """Called every game tick.  Charges daily maintenance once per interval,
    and processes contract bid closing + forfeiture checks every 60 seconds."""

    # Contract processing — every 60 ticks (≈ 60s)
    if current_tick % 60 == 0:
        _process_contract_bids(now)
        check_contract_forfeitures()

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
            # Executive CDO bonus reduces maintenance cost
            try:
                from executive import get_player_job_bonus
                from database import SessionLocal as _ES
                _edb = _ES()
                try:
                    _mil_bonus = get_player_job_bonus(_edb, pa.owner_id, "military")
                finally:
                    _edb.close()
                daily_cost = daily_cost * max(0.0, 1.0 - _mil_bonus)
            except Exception:
                pass
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
    session_token = request.cookies.get("session_token")
    db = get_db()
    try:
        player = get_player_from_session(db, session_token)
        return player.id if player else None
    finally:
        db.close()


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


@router.get("/contracts")
async def api_contracts_list(request: Request):
    pid = _player_id(request)
    if not pid:
        return JSONResponse({"error": "Not logged in."}, status_code=401)
    return JSONResponse({"contracts": get_open_contracts()})


@router.post("/contracts/{contract_id}/bid")
async def api_contract_bid(contract_id: int, request: Request):
    pid = _player_id(request)
    if not pid:
        return JSONResponse({"error": "Not logged in."}, status_code=401)
    body = await request.json()
    bid_price = float(body.get("bid_price_usd", 0.0))
    bid_vol   = float(body.get("bid_volume_multiplier", 1.0))
    ok, msg = submit_contract_bid(pid, contract_id, bid_price, bid_vol)
    return JSONResponse({"ok": ok, "message": msg}, status_code=200 if ok else 400)


@router.post("/contracts/{contract_id}/fulfill")
async def api_contract_fulfill(contract_id: int, request: Request):
    pid = _player_id(request)
    if not pid:
        return JSONResponse({"error": "Not logged in."}, status_code=401)
    ok, result = fulfill_contract(pid, contract_id)
    if ok:
        return JSONResponse({"ok": True, "result": result})
    return JSONResponse({"ok": False, "error": result.get("error", "Unknown error")}, status_code=400)


@router.get("/contracts/mine")
async def api_my_bids(request: Request):
    pid = _player_id(request)
    if not pid:
        return JSONResponse({"error": "Not logged in."}, status_code=401)
    return JSONResponse({
        "bids": get_player_bids(pid),
        "active_contract": get_won_contract(pid),
    })


@router.post("/immigration/commit")
async def api_immigration_commit(request: Request):
    pid = _player_id(request)
    if not pid:
        return JSONResponse({"error": "Not logged in."}, status_code=401)
    body = await request.json()
    ok, msg = commit_immigration_policy(pid, body)
    return JSONResponse({"ok": ok, "message": msg}, status_code=200 if ok else 400)


@router.get("/immigration/status")
async def api_immigration_status(request: Request):
    pid = _player_id(request)
    if not pid:
        return JSONResponse({"error": "Not logged in."}, status_code=401)
    return JSONResponse(get_immigration_status(pid))


# Run table creation when module is imported. Guard it: a transient DB
# error at import time must NOT prevent the router from being imported and
# registered (otherwise every /api/port-authority route 404s). Tables are
# also ensured by the startup migration, so deferring here is safe.
try:
    init_db()
except Exception as _pa_initdb_err:
    print(f"[PortAuthority] init_db deferred: {_pa_initdb_err}")
