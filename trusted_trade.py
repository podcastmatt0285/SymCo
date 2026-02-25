"""
trusted_trade.py

Trusted-Trader system: players maintain a private list of up to 5 trusted
partners and execute item-for-item swaps that can involve up to 5 parties.

Slot pricing (Fibonacci × $10,000):
    Slot 1  →  $10,000   removal  $20,000
    Slot 2  →  $10,000   removal  $20,000
    Slot 3  →  $20,000   removal  $40,000
    Slot 4  →  $30,000   removal  $60,000
    Slot 5  →  $50,000   removal  $100,000

Rules:
  • Each pair of participants must be mutually on each other's list.
  • Swaps are item-for-item only (no cash transfers).
  • A player added to a list must stay ≥ 30 days before removal.
  • Removal costs 2× the original add cost for that slot.
  • Up to 5 participants per swap, up to 15 transfer legs.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String
from sqlalchemy.orm import Session

from database import Base, SessionLocal

# ─── Constants ────────────────────────────────────────────────────────────────

MAX_TRUSTED_SLOTS       = 5
MIN_DAYS_BEFORE_REMOVAL = 30
# Fibonacci × $10k: F(1)..F(5) = 1,1,2,3,5
SLOT_ADD_PRICES = [10_000, 10_000, 20_000, 30_000, 50_000]

MAX_SWAP_PARTIES = 5
MAX_SWAP_LEGS    = 15     # max item-transfer legs in one swap
SWAP_TTL_DAYS    = 7      # pending swaps expire after 7 days

# ─── Models ───────────────────────────────────────────────────────────────────

class TrustedTraderEntry(Base):
    """One slot on a player's trusted-trader list."""
    __tablename__ = "trusted_trader_entries"

    id                = Column(Integer, primary_key=True, index=True)
    owner_player_id   = Column(Integer, index=True, nullable=False)
    trusted_player_id = Column(Integer, index=True, nullable=False)
    slot_number       = Column(Integer, nullable=False)          # 1-5
    added_at          = Column(DateTime, default=datetime.utcnow)
    cost_paid         = Column(Float,   nullable=False)          # add fee paid


class SwapOffer(Base):
    """A multi-party item-for-item swap proposal."""
    __tablename__ = "swap_offers"

    id           = Column(Integer, primary_key=True, index=True)
    initiator_id = Column(Integer, index=True, nullable=False)
    # pending | executed | failed | rejected | cancelled
    status       = Column(String, default="pending")
    notes        = Column(String, nullable=True)
    created_at   = Column(DateTime, default=datetime.utcnow)
    expires_at   = Column(DateTime, nullable=True)


class SwapOfferLeg(Base):
    """One transfer leg inside a swap: from_player gives qty of item to to_player."""
    __tablename__ = "swap_offer_legs"

    id             = Column(Integer, primary_key=True, index=True)
    swap_id        = Column(Integer, index=True, nullable=False)
    from_player_id = Column(Integer, nullable=False)
    to_player_id   = Column(Integer, nullable=False)
    item_type      = Column(String,  nullable=False)
    quantity       = Column(Float,   nullable=False)


class SwapOfferAcceptance(Base):
    """One participant's vote on a swap (accept / reject)."""
    __tablename__ = "swap_offer_acceptances"

    id           = Column(Integer, primary_key=True, index=True)
    swap_id      = Column(Integer, index=True, nullable=False)
    player_id    = Column(Integer, nullable=False)
    accepted     = Column(Boolean, default=False)
    responded_at = Column(DateTime, nullable=True)


# ─── DB helper ────────────────────────────────────────────────────────────────

def get_db():
    return SessionLocal()


# ─── Trusted-list helpers ─────────────────────────────────────────────────────

def get_trusted_list(owner_id: int) -> List[TrustedTraderEntry]:
    db = get_db()
    try:
        return (
            db.query(TrustedTraderEntry)
            .filter(TrustedTraderEntry.owner_player_id == owner_id)
            .order_by(TrustedTraderEntry.slot_number)
            .all()
        )
    finally:
        db.close()


def _next_free_slot(db: Session, owner_id: int) -> Optional[int]:
    used = {
        e.slot_number
        for e in db.query(TrustedTraderEntry)
        .filter(TrustedTraderEntry.owner_player_id == owner_id)
        .all()
    }
    for s in range(1, MAX_TRUSTED_SLOTS + 1):
        if s not in used:
            return s
    return None


def add_trusted_player(owner_id: int, target_id: int) -> Tuple[bool, str]:
    """Add target_id to owner_id's trusted list and charge the slot fee."""
    if owner_id == target_id:
        return False, "You cannot add yourself."

    from auth import get_db as get_auth_db, Player

    db = get_db()
    try:
        existing = (
            db.query(TrustedTraderEntry)
            .filter(
                TrustedTraderEntry.owner_player_id   == owner_id,
                TrustedTraderEntry.trusted_player_id == target_id,
            )
            .first()
        )
        if existing:
            return False, "That player is already on your trusted list."

        slot = _next_free_slot(db, owner_id)
        if slot is None:
            return False, f"Your trusted list is full ({MAX_TRUSTED_SLOTS} slots)."

        fee = SLOT_ADD_PRICES[slot - 1]

        auth_db = get_auth_db()
        try:
            owner  = auth_db.query(Player).filter(Player.id == owner_id).first()
            target = auth_db.query(Player).filter(Player.id == target_id).first()
            if not target or target_id == 0:
                return False, "Player not found."
            if not owner or owner.cash_balance < fee:
                return False, f"Insufficient funds. Slot {slot} costs ${fee:,.0f}."
            gov = auth_db.query(Player).filter(Player.id == 0).first()
            owner.cash_balance -= fee
            if gov:
                gov.cash_balance += fee
            auth_db.commit()
        finally:
            auth_db.close()

        db.add(TrustedTraderEntry(
            owner_player_id   = owner_id,
            trusted_player_id = target_id,
            slot_number       = slot,
            cost_paid         = fee,
        ))
        db.commit()
        return True, f"Added to trusted list (slot {slot}, fee ${fee:,.0f})."

    except Exception as e:
        db.rollback()
        return False, f"Error: {e}"
    finally:
        db.close()


def remove_trusted_player(owner_id: int, entry_id: int) -> Tuple[bool, str]:
    """Remove a trusted-list entry, enforcing the 30-day lock and charging 2× fee."""
    from auth import get_db as get_auth_db, Player

    db = get_db()
    try:
        entry = (
            db.query(TrustedTraderEntry)
            .filter(
                TrustedTraderEntry.id              == entry_id,
                TrustedTraderEntry.owner_player_id == owner_id,
            )
            .first()
        )
        if not entry:
            return False, "Entry not found."

        days_on_list = (datetime.utcnow() - entry.added_at).days
        if days_on_list < MIN_DAYS_BEFORE_REMOVAL:
            remaining = MIN_DAYS_BEFORE_REMOVAL - days_on_list
            return False, (
                f"Cannot remove yet — {remaining} day(s) remaining "
                f"(30-day minimum lock-in)."
            )

        removal_fee = entry.cost_paid * 2

        auth_db = get_auth_db()
        try:
            owner = auth_db.query(Player).filter(Player.id == owner_id).first()
            if not owner or owner.cash_balance < removal_fee:
                return False, (
                    f"Insufficient funds. Removing this slot costs "
                    f"${removal_fee:,.0f} (2× the ${entry.cost_paid:,.0f} add fee)."
                )
            gov = auth_db.query(Player).filter(Player.id == 0).first()
            owner.cash_balance -= removal_fee
            if gov:
                gov.cash_balance += removal_fee
            auth_db.commit()
        finally:
            auth_db.close()

        db.delete(entry)
        db.commit()
        return True, f"Removed from trusted list (removal fee ${removal_fee:,.0f})."

    except Exception as e:
        db.rollback()
        return False, f"Error: {e}"
    finally:
        db.close()


# ─── Mutual-trust helper ──────────────────────────────────────────────────────

def _are_mutually_trusted(player_a: int, player_b: int, db: Session) -> bool:
    a_trusts_b = (
        db.query(TrustedTraderEntry)
        .filter(
            TrustedTraderEntry.owner_player_id   == player_a,
            TrustedTraderEntry.trusted_player_id == player_b,
        )
        .first()
    )
    b_trusts_a = (
        db.query(TrustedTraderEntry)
        .filter(
            TrustedTraderEntry.owner_player_id   == player_b,
            TrustedTraderEntry.trusted_player_id == player_a,
        )
        .first()
    )
    return bool(a_trusts_b and b_trusts_a)


# ─── Swap helpers ─────────────────────────────────────────────────────────────

def create_swap(
    initiator_id: int,
    legs: List[dict],   # [{from_player_id, to_player_id, item_type, quantity}]
    notes: str = "",
) -> Tuple[Optional[int], str]:
    """
    Create a pending multi-party swap.
    Returns (swap_id, "") on success, (None, error_msg) on failure.
    """
    if not legs:
        return None, "A swap must have at least one transfer leg."
    if len(legs) > MAX_SWAP_LEGS:
        return None, f"Swap cannot exceed {MAX_SWAP_LEGS} legs."

    participants: set = set()
    for leg in legs:
        participants.add(int(leg["from_player_id"]))
        participants.add(int(leg["to_player_id"]))

    if initiator_id not in participants:
        return None, "Initiator must be a participant in the swap."
    if len(participants) > MAX_SWAP_PARTIES:
        return None, f"Swap cannot involve more than {MAX_SWAP_PARTIES} parties."
    if len(participants) < 2:
        return None, "A swap needs at least 2 parties."

    db = get_db()
    try:
        # Validate mutual trust for every pair
        participant_list = list(participants)
        for i, pa in enumerate(participant_list):
            for pb in participant_list[i + 1:]:
                if not _are_mutually_trusted(pa, pb, db):
                    from auth import get_db as get_auth_db, Player
                    adb = get_auth_db()
                    try:
                        na = (adb.query(Player).filter(Player.id == pa).first() or
                              type("_", (), {"business_name": str(pa)})())
                        nb = (adb.query(Player).filter(Player.id == pb).first() or
                              type("_", (), {"business_name": str(pb)})())
                        na, nb = na.business_name, nb.business_name
                    finally:
                        adb.close()
                    return None, (
                        f"{na} and {nb} are not mutually on each other's "
                        f"trusted list."
                    )

        # Validate quantities
        for leg in legs:
            if float(leg["quantity"]) <= 0:
                return None, "All transfer quantities must be positive."

        # Pre-flight inventory check
        from inventory import get_item_quantity
        from collections import defaultdict
        needed: dict = defaultdict(lambda: defaultdict(float))
        for leg in legs:
            needed[int(leg["from_player_id"])][leg["item_type"]] += float(leg["quantity"])
        for pid, items in needed.items():
            for itype, qty in items.items():
                if get_item_quantity(pid, itype) < qty:
                    from auth import get_db as get_auth_db, Player
                    adb = get_auth_db()
                    try:
                        p = adb.query(Player).filter(Player.id == pid).first()
                        pname = p.business_name if p else str(pid)
                    finally:
                        adb.close()
                    return None, (
                        f"{pname} does not have enough "
                        f"{itype.replace('_', ' ')} to fulfill this swap."
                    )

        swap = SwapOffer(
            initiator_id = initiator_id,
            status       = "pending",
            notes        = (notes or "")[:500],
            expires_at   = datetime.utcnow() + timedelta(days=SWAP_TTL_DAYS),
        )
        db.add(swap)
        db.flush()  # populate swap.id

        for leg in legs:
            db.add(SwapOfferLeg(
                swap_id        = swap.id,
                from_player_id = int(leg["from_player_id"]),
                to_player_id   = int(leg["to_player_id"]),
                item_type      = leg["item_type"],
                quantity       = float(leg["quantity"]),
            ))

        # Acceptance stubs — initiator auto-accepts
        for pid in participants:
            db.add(SwapOfferAcceptance(
                swap_id      = swap.id,
                player_id    = pid,
                accepted     = (pid == initiator_id),
                responded_at = datetime.utcnow() if pid == initiator_id else None,
            ))

        db.commit()
        swap_id = swap.id
    except Exception as e:
        db.rollback()
        return None, f"Error creating swap: {e}"
    finally:
        db.close()

    _try_execute_swap(swap_id)
    return swap_id, ""


def _try_execute_swap(swap_id: int) -> bool:
    """Execute the swap if every participant has accepted. Returns True if executed."""
    from inventory import transfer_item

    db = get_db()
    try:
        swap = (
            db.query(SwapOffer)
            .filter(SwapOffer.id == swap_id, SwapOffer.status == "pending")
            .first()
        )
        if not swap:
            return False

        acceptances = (
            db.query(SwapOfferAcceptance)
            .filter(SwapOfferAcceptance.swap_id == swap_id)
            .all()
        )
        if not all(a.accepted for a in acceptances):
            return False

        legs = (
            db.query(SwapOfferLeg)
            .filter(SwapOfferLeg.swap_id == swap_id)
            .all()
        )

        for leg in legs:
            ok = transfer_item(
                leg.from_player_id, leg.to_player_id,
                leg.item_type, leg.quantity
            )
            if not ok:
                swap.status = "failed"
                db.commit()
                print(f"[TrustedTrade] Swap {swap_id} failed on leg {leg.id}")
                return False

        swap.status = "executed"
        db.commit()
        print(f"[TrustedTrade] Swap {swap_id} executed successfully.")
        return True

    except Exception as e:
        db.rollback()
        print(f"[TrustedTrade] Execute swap {swap_id} error: {e}")
        return False
    finally:
        db.close()


def respond_to_swap(swap_id: int, player_id: int, accept: bool) -> Tuple[bool, str]:
    """Accept or reject a pending swap. Executes the swap if all parties accept."""
    db = get_db()
    try:
        swap = (
            db.query(SwapOffer)
            .filter(SwapOffer.id == swap_id, SwapOffer.status == "pending")
            .first()
        )
        if not swap:
            return False, "Swap not found or no longer pending."

        acceptance = (
            db.query(SwapOfferAcceptance)
            .filter(
                SwapOfferAcceptance.swap_id   == swap_id,
                SwapOfferAcceptance.player_id == player_id,
            )
            .first()
        )
        if not acceptance:
            return False, "You are not a participant in this swap."
        if acceptance.accepted and accept:
            return False, "You have already accepted this swap."

        acceptance.accepted     = accept
        acceptance.responded_at = datetime.utcnow()

        if not accept:
            swap.status = "rejected"

        db.commit()
    except Exception as e:
        db.rollback()
        return False, f"Error: {e}"
    finally:
        db.close()

    if accept:
        _try_execute_swap(swap_id)
        return True, "Accepted. The swap will execute once all parties agree."
    return True, "Swap rejected."


def cancel_swap(swap_id: int, player_id: int) -> Tuple[bool, str]:
    """Initiator cancels their own pending swap."""
    db = get_db()
    try:
        swap = (
            db.query(SwapOffer)
            .filter(
                SwapOffer.id           == swap_id,
                SwapOffer.initiator_id == player_id,
                SwapOffer.status       == "pending",
            )
            .first()
        )
        if not swap:
            return False, "Swap not found or you are not the initiator."
        swap.status = "cancelled"
        db.commit()
        return True, "Swap cancelled."
    except Exception as e:
        db.rollback()
        return False, f"Error: {e}"
    finally:
        db.close()


def get_swaps_for_player(player_id: int) -> List[SwapOffer]:
    """Return all swaps (any status) where player_id is a participant."""
    db = get_db()
    try:
        swap_ids = [
            a.swap_id
            for a in db.query(SwapOfferAcceptance)
            .filter(SwapOfferAcceptance.player_id == player_id)
            .all()
        ]
        if not swap_ids:
            return []
        return (
            db.query(SwapOffer)
            .filter(SwapOffer.id.in_(swap_ids))
            .order_by(SwapOffer.created_at.desc())
            .limit(50)
            .all()
        )
    finally:
        db.close()


def get_swap_detail(swap_id: int):
    """Return (swap, legs, acceptances) or (None, [], []) if not found."""
    db = get_db()
    try:
        swap = db.query(SwapOffer).filter(SwapOffer.id == swap_id).first()
        if not swap:
            return None, [], []
        legs = (
            db.query(SwapOfferLeg)
            .filter(SwapOfferLeg.swap_id == swap_id)
            .all()
        )
        acceptances = (
            db.query(SwapOfferAcceptance)
            .filter(SwapOfferAcceptance.swap_id == swap_id)
            .all()
        )
        return swap, legs, acceptances
    finally:
        db.close()


# ─── Module lifecycle ─────────────────────────────────────────────────────────

def initialize():
    from database import Base, engine
    Base.metadata.create_all(bind=engine)
    print("[TrustedTrade] Tables ensured.")


async def tick(current_tick: int, now):
    """Expire pending swaps that have passed their TTL."""
    db = get_db()
    try:
        expired = (
            db.query(SwapOffer)
            .filter(
                SwapOffer.status     == "pending",
                SwapOffer.expires_at <= now,
            )
            .all()
        )
        for s in expired:
            s.status = "cancelled"
            print(f"[TrustedTrade] Swap {s.id} expired.")
        if expired:
            db.commit()
    except Exception as e:
        db.rollback()
        print(f"[TrustedTrade] Tick error: {e}")
    finally:
        db.close()
