"""
p2p.py

Peer-to-Peer module for the economic simulation.
Handles:
- P2P Dashboard access fees (money sink)
- Contract creation (multi-item, delivery intervals, contract lengths)
- Contract Trading Market (listing, bidding, winning)
- Contract fulfillment tracking (tick-driven deliveries)
- Breach of contract detection and penalties
"""

from datetime import datetime, timedelta
from typing import Optional, List
from enum import Enum
from sqlalchemy import create_engine, Column, String, Float, DateTime, Integer, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# ==========================
# DATABASE SETUP
# ==========================
DATABASE_URL = "sqlite:///./symco.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ==========================
# CONSTANTS
# ==========================

P2P_DASHBOARD_FEE = 5000.0  # $5,000 entry fee each time you access the P2P dashboard

# Delivery intervals (in ticks). 1 tick = 5 seconds.
# 1 game-day ~ 120 ticks (10 min real time based on business cycle patterns)
DELIVERY_INTERVALS = {
    "hourly": {"ticks": 720, "label": "Hourly (1 real hour)", "multiplier": 1.0},
    "daily": {"ticks": 17280, "label": "Daily (1 real day)", "multiplier": 0.9},
    "weekly": {"ticks": 120960, "label": "Weekly (1 real week)", "multiplier": 0.8},
}

# Contract lengths (number of deliveries)
CONTRACT_LENGTHS = {
    "short": {"deliveries": 3, "label": "Short (3 deliveries)"},
    "medium": {"deliveries": 7, "label": "Medium (7 deliveries)"},
    "long": {"deliveries": 14, "label": "Long (14 deliveries)"},
    "extended": {"deliveries": 30, "label": "Extended (30 deliveries)"},
}

# Breach penalties
BREACH_PENALTY_GOV_PCT = 0.25      # 25% of total contract value to government
BREACH_PENALTY_DAMAGED_PCT = 0.50  # 50% of total contract value to damaged party
# Total: 75% of contract value as penalty

# Grace period before a missed delivery becomes a breach (in ticks)
DELIVERY_GRACE_PERIOD = 360  # 30 minutes real time

# Bidding duration for contract market listings (in ticks)
DEFAULT_BID_DURATION = 4320  # 6 real hours


# ==========================
# ENUMS
# ==========================
class ContractStatus(str, Enum):
    DRAFT = "draft"              # Created, not yet listed
    LISTED = "listed"            # On the trading market
    ACTIVE = "active"            # Won/acquired, deliveries in progress
    COMPLETED = "completed"      # All deliveries fulfilled
    BREACHED = "breached"        # Contract breached by one party
    VOIDED = "voided"            # Contract voided after breach


class BidStatus(str, Enum):
    ACTIVE = "active"
    OUTBID = "outbid"
    WON = "won"
    LOST = "lost"


# ==========================
# DATABASE MODELS
# ==========================
class Contract(Base):
    """A P2P delivery contract."""
    __tablename__ = "p2p_contracts"

    id = Column(Integer, primary_key=True, index=True)
    creator_id = Column(Integer, index=True, nullable=False)       # Player who created the contract
    holder_id = Column(Integer, index=True, nullable=True)         # Player who holds/fulfills the contract (set when won)
    buyer_id = Column(Integer, index=True, nullable=True)          # Player who receives deliveries (the creator becomes buyer after selling)

    status = Column(String, default=ContractStatus.DRAFT, index=True)

    # Contract terms
    delivery_interval = Column(String, nullable=False)             # Key into DELIVERY_INTERVALS
    contract_length = Column(String, nullable=False)               # Key into CONTRACT_LENGTHS
    total_deliveries = Column(Integer, nullable=False)             # Total number of deliveries required
    deliveries_completed = Column(Integer, default=0)              # Deliveries successfully made
    price_per_delivery = Column(Float, nullable=False)             # $ paid per delivery by buyer to holder

    # Timing
    next_delivery_tick = Column(Integer, nullable=True)            # Tick when next delivery is due
    last_delivery_tick = Column(Integer, nullable=True)            # Tick when last delivery was made
    activated_at = Column(DateTime, nullable=True)                 # When the contract went active
    completed_at = Column(DateTime, nullable=True)
    breached_at = Column(DateTime, nullable=True)

    # Market listing
    listed_at = Column(DateTime, nullable=True)
    bid_end_tick = Column(Integer, nullable=True)                  # Tick when bidding ends
    minimum_bid = Column(Float, default=0.0)                       # Minimum bid (can be $0)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Breach info
    breached_by = Column(Integer, nullable=True)                   # Player who breached
    breach_reason = Column(String, nullable=True)


class ContractItem(Base):
    """Items required per delivery in a contract (up to 3)."""
    __tablename__ = "p2p_contract_items"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, index=True, nullable=False)
    item_type = Column(String, nullable=False)
    quantity_per_delivery = Column(Float, nullable=False)


class ContractBid(Base):
    """A bid on a listed contract."""
    __tablename__ = "p2p_contract_bids"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, index=True, nullable=False)
    bidder_id = Column(Integer, index=True, nullable=False)
    bid_amount = Column(Float, nullable=False)                     # Not a cash bid - this is reputation/willingness
    status = Column(String, default=BidStatus.ACTIVE)
    created_at = Column(DateTime, default=datetime.utcnow)


class P2PAccessLog(Base):
    """Tracks each time a player pays to access the P2P dashboard."""
    __tablename__ = "p2p_access_log"

    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, index=True, nullable=False)
    fee_paid = Column(Float, nullable=False)
    accessed_at = Column(DateTime, default=datetime.utcnow)


class ContractDelivery(Base):
    """Record of each delivery made on a contract."""
    __tablename__ = "p2p_contract_deliveries"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, index=True, nullable=False)
    delivery_number = Column(Integer, nullable=False)
    delivered_at = Column(DateTime, default=datetime.utcnow)
    delivered_tick = Column(Integer, nullable=False)
    payment_amount = Column(Float, nullable=False)


# ==========================
# HELPER FUNCTIONS
# ==========================
def get_db():
    db = SessionLocal()
    try:
        return db
    except Exception as e:
        print(f"[P2P] Database error: {e}")
        db.close()
        raise


def charge_p2p_access(player_id: int) -> bool:
    """
    Charge the P2P dashboard entry fee.
    Returns True if successful, False if insufficient funds.
    """
    from auth import get_db as get_auth_db, Player
    from stats_ux import log_transaction

    auth_db = get_auth_db()
    player = auth_db.query(Player).filter(Player.id == player_id).first()
    if not player or player.cash_balance < P2P_DASHBOARD_FEE:
        auth_db.close()
        return False

    player.cash_balance -= P2P_DASHBOARD_FEE
    auth_db.commit()
    auth_db.close()

    # Pay to government (player 0)
    from auth import transfer_cash
    gov_db = get_auth_db()
    gov = gov_db.query(Player).filter(Player.id == 0).first()
    if gov:
        gov.cash_balance += P2P_DASHBOARD_FEE
        gov_db.commit()
    gov_db.close()

    # Log access
    db = get_db()
    access_log = P2PAccessLog(player_id=player_id, fee_paid=P2P_DASHBOARD_FEE)
    db.add(access_log)
    db.commit()
    db.close()

    log_transaction(
        player_id=player_id,
        transaction_type="p2p_access",
        category="money",
        amount=-P2P_DASHBOARD_FEE,
        description=f"P2P Dashboard access fee: ${P2P_DASHBOARD_FEE:,.0f}"
    )

    return True


def create_contract(creator_id: int, items: list, delivery_interval: str,
                    contract_length: str, price_per_delivery: float) -> Optional[int]:
    """
    Create a new contract in DRAFT status.
    items: list of {"item_type": str, "quantity": float} (max 3)
    Returns contract ID or None on failure.
    """
    if delivery_interval not in DELIVERY_INTERVALS:
        return None
    if contract_length not in CONTRACT_LENGTHS:
        return None
    if len(items) < 1 or len(items) > 3:
        return None
    if price_per_delivery <= 0:
        return None

    total_deliveries = CONTRACT_LENGTHS[contract_length]["deliveries"]

    db = get_db()
    contract = Contract(
        creator_id=creator_id,
        status=ContractStatus.DRAFT,
        delivery_interval=delivery_interval,
        contract_length=contract_length,
        total_deliveries=total_deliveries,
        price_per_delivery=price_per_delivery,
    )
    db.add(contract)
    db.commit()
    db.refresh(contract)

    for item_data in items:
        ci = ContractItem(
            contract_id=contract.id,
            item_type=item_data["item_type"],
            quantity_per_delivery=item_data["quantity"],
        )
        db.add(ci)

    db.commit()
    contract_id = contract.id
    db.close()
    return contract_id


def list_contract(contract_id: int, player_id: int, minimum_bid: float = 0.0) -> bool:
    """
    List a DRAFT contract on the trading market.
    The creator becomes the buyer (they want someone to fulfill deliveries to them).
    """
    import app as app_mod

    db = get_db()
    contract = db.query(Contract).filter(
        Contract.id == contract_id,
        Contract.creator_id == player_id,
        Contract.status == ContractStatus.DRAFT
    ).first()

    if not contract:
        db.close()
        return False

    contract.status = ContractStatus.LISTED
    contract.buyer_id = player_id  # Creator becomes the buyer
    contract.listed_at = datetime.utcnow()
    contract.bid_end_tick = app_mod.current_tick + DEFAULT_BID_DURATION
    contract.minimum_bid = minimum_bid
    db.commit()
    db.close()
    return True


def place_bid(contract_id: int, bidder_id: int) -> Optional[str]:
    """
    Place a bid on a listed contract. Bids are free.
    Returns None on success, error message on failure.
    """
    db = get_db()
    contract = db.query(Contract).filter(
        Contract.id == contract_id,
        Contract.status == ContractStatus.LISTED
    ).first()

    if not contract:
        db.close()
        return "Contract not found or not listed."

    if contract.creator_id == bidder_id:
        db.close()
        return "Cannot bid on your own contract."

    # Check if already bid
    existing = db.query(ContractBid).filter(
        ContractBid.contract_id == contract_id,
        ContractBid.bidder_id == bidder_id,
        ContractBid.status == BidStatus.ACTIVE
    ).first()

    if existing:
        db.close()
        return "You already have an active bid on this contract."

    bid = ContractBid(
        contract_id=contract_id,
        bidder_id=bidder_id,
        bid_amount=0.0,  # Free bidding
    )
    db.add(bid)
    db.commit()
    db.close()
    return None


def resolve_listing(contract_id: int) -> bool:
    """
    Resolve a listing whose bid period has ended.
    Picks a random winner from all active bids.
    Returns True if a winner was found.
    """
    import random

    db = get_db()
    contract = db.query(Contract).filter(
        Contract.id == contract_id,
        Contract.status == ContractStatus.LISTED
    ).first()

    if not contract:
        db.close()
        return False

    bids = db.query(ContractBid).filter(
        ContractBid.contract_id == contract_id,
        ContractBid.status == BidStatus.ACTIVE
    ).all()

    if not bids:
        # No bids - return to draft
        contract.status = ContractStatus.DRAFT
        contract.listed_at = None
        contract.bid_end_tick = None
        db.commit()
        db.close()
        return False

    # Pick random winner
    winner_bid = random.choice(bids)

    # Mark all bids
    for bid in bids:
        if bid.id == winner_bid.id:
            bid.status = BidStatus.WON
        else:
            bid.status = BidStatus.LOST

    # Activate the contract
    import app as app_mod
    interval_ticks = DELIVERY_INTERVALS[contract.delivery_interval]["ticks"]

    contract.status = ContractStatus.ACTIVE
    contract.holder_id = winner_bid.bidder_id
    contract.activated_at = datetime.utcnow()
    contract.next_delivery_tick = app_mod.current_tick + interval_ticks

    db.commit()
    db.close()
    return True


def process_delivery(contract_id: int, current_tick: int) -> Optional[str]:
    """
    Process a delivery for an active contract.
    The holder must have the items in inventory to deliver.
    The buyer must have the cash to pay.
    Returns None on success, error string on failure/breach.
    """
    from inventory import get_item_quantity, remove_item, add_item
    from auth import get_db as get_auth_db, Player
    from stats_ux import log_transaction

    db = get_db()
    contract = db.query(Contract).filter(
        Contract.id == contract_id,
        Contract.status == ContractStatus.ACTIVE
    ).first()

    if not contract:
        db.close()
        return "Contract not found."

    items = db.query(ContractItem).filter(ContractItem.contract_id == contract_id).all()

    # Check holder has all items
    holder_id = contract.holder_id
    buyer_id = contract.buyer_id
    can_deliver = True

    for item in items:
        qty = get_item_quantity(holder_id, item.item_type)
        if qty < item.quantity_per_delivery:
            can_deliver = False
            break

    if not can_deliver:
        # Check if grace period expired
        if current_tick > contract.next_delivery_tick + DELIVERY_GRACE_PERIOD:
            # BREACH by holder - can't deliver
            _handle_breach(db, contract, holder_id, "Holder failed to deliver items within grace period")
            db.close()
            return "breach_holder"
        db.close()
        return "holder_missing_items"

    # Check buyer has cash
    auth_db = get_auth_db()
    buyer = auth_db.query(Player).filter(Player.id == buyer_id).first()
    if not buyer or buyer.cash_balance < contract.price_per_delivery:
        auth_db.close()
        # Check grace period for buyer
        if current_tick > contract.next_delivery_tick + DELIVERY_GRACE_PERIOD:
            _handle_breach(db, contract, buyer_id, "Buyer failed to pay within grace period")
            db.close()
            return "breach_buyer"
        db.close()
        return "buyer_insufficient_funds"
    auth_db.close()

    # Execute delivery: transfer items holder -> buyer
    for item in items:
        remove_item(holder_id, item.item_type, item.quantity_per_delivery)
        add_item(buyer_id, item.item_type, item.quantity_per_delivery)

        log_transaction(
            player_id=holder_id,
            transaction_type="p2p_contract_delivery",
            category="resource",
            amount=0,
            description=f"Contract #{contract_id} delivery: {item.quantity_per_delivery:.1f}x {item.item_type}",
            item_type=item.item_type,
            quantity=item.quantity_per_delivery
        )

    # Transfer payment: buyer -> holder
    from auth import transfer_cash
    transfer_cash(buyer_id, holder_id, contract.price_per_delivery)

    log_transaction(
        player_id=holder_id,
        transaction_type="p2p_contract_payment",
        category="money",
        amount=contract.price_per_delivery,
        description=f"Contract #{contract_id} delivery payment received"
    )
    log_transaction(
        player_id=buyer_id,
        transaction_type="p2p_contract_payment",
        category="money",
        amount=-contract.price_per_delivery,
        description=f"Contract #{contract_id} delivery payment sent"
    )

    # Record delivery
    contract.deliveries_completed += 1
    contract.last_delivery_tick = current_tick

    delivery_record = ContractDelivery(
        contract_id=contract_id,
        delivery_number=contract.deliveries_completed,
        delivered_tick=current_tick,
        payment_amount=contract.price_per_delivery,
    )
    db.add(delivery_record)

    # Check if contract is complete
    if contract.deliveries_completed >= contract.total_deliveries:
        contract.status = ContractStatus.COMPLETED
        contract.completed_at = datetime.utcnow()
        contract.next_delivery_tick = None
    else:
        # Schedule next delivery
        interval_ticks = DELIVERY_INTERVALS[contract.delivery_interval]["ticks"]
        contract.next_delivery_tick = current_tick + interval_ticks

    db.commit()
    db.close()
    return None


def _handle_breach(db, contract, breacher_id: int, reason: str):
    """Handle a contract breach with penalties."""
    from auth import get_db as get_auth_db, Player
    from stats_ux import log_transaction

    total_value = contract.price_per_delivery * contract.total_deliveries
    gov_penalty = total_value * BREACH_PENALTY_GOV_PCT
    damaged_penalty = total_value * BREACH_PENALTY_DAMAGED_PCT

    # Determine damaged party
    damaged_id = contract.buyer_id if breacher_id == contract.holder_id else contract.holder_id

    # Charge breacher
    auth_db = get_auth_db()
    breacher = auth_db.query(Player).filter(Player.id == breacher_id).first()
    gov = auth_db.query(Player).filter(Player.id == 0).first()
    damaged = auth_db.query(Player).filter(Player.id == damaged_id).first()

    if breacher:
        total_penalty = gov_penalty + damaged_penalty
        breacher.cash_balance -= total_penalty  # Can go negative (debt)

        if gov:
            gov.cash_balance += gov_penalty
        if damaged:
            damaged.cash_balance += damaged_penalty

        auth_db.commit()

        log_transaction(
            player_id=breacher_id,
            transaction_type="p2p_breach_penalty",
            category="money",
            amount=-total_penalty,
            description=f"Contract #{contract.id} breach penalty: ${total_penalty:,.0f}"
        )
        log_transaction(
            player_id=damaged_id,
            transaction_type="p2p_breach_damages",
            category="money",
            amount=damaged_penalty,
            description=f"Contract #{contract.id} breach damages received: ${damaged_penalty:,.0f}"
        )

    auth_db.close()

    # Void the contract
    contract.status = ContractStatus.BREACHED
    contract.breached_at = datetime.utcnow()
    contract.breached_by = breacher_id
    contract.breach_reason = reason
    contract.next_delivery_tick = None
    db.commit()


def get_contract_details(contract_id: int) -> Optional[dict]:
    """Get full contract details including items."""
    db = get_db()
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        db.close()
        return None

    items = db.query(ContractItem).filter(ContractItem.contract_id == contract_id).all()
    bids = db.query(ContractBid).filter(ContractBid.contract_id == contract_id).all()
    deliveries = db.query(ContractDelivery).filter(ContractDelivery.contract_id == contract_id).all()

    result = {
        "contract": contract,
        "items": items,
        "bids": bids,
        "deliveries": deliveries,
        "total_value": contract.price_per_delivery * contract.total_deliveries,
        "breach_penalty": contract.price_per_delivery * contract.total_deliveries * (BREACH_PENALTY_GOV_PCT + BREACH_PENALTY_DAMAGED_PCT),
    }
    db.close()
    return result


def get_player_contracts(player_id: int) -> dict:
    """Get all contracts where the player is involved (as creator, holder, or buyer)."""
    db = get_db()
    as_creator = db.query(Contract).filter(Contract.creator_id == player_id).all()
    as_holder = db.query(Contract).filter(Contract.holder_id == player_id).all()
    as_buyer = db.query(Contract).filter(Contract.buyer_id == player_id).all()

    result = {
        "created": as_creator,
        "holding": as_holder,
        "buying": as_buyer,
    }
    db.close()
    return result


# ==========================
# MODULE LIFECYCLE
# ==========================
def initialize():
    """Initialize the P2P module."""
    print("[P2P] Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("[P2P] Module initialized")


async def tick(current_tick: int, now):
    """
    Tick handler for P2P module.
    - Resolve expired listings
    - Process pending deliveries
    - Check for breaches
    """
    # Only run every 12 ticks (~1 minute) to save resources
    if current_tick % 12 != 0:
        return

    db = get_db()

    try:
        # 1. Resolve expired listings
        expired_listings = db.query(Contract).filter(
            Contract.status == ContractStatus.LISTED,
            Contract.bid_end_tick <= current_tick
        ).all()

        for contract in expired_listings:
            db.close()
            resolve_listing(contract.id)
            db = get_db()

        # 2. Process deliveries for active contracts
        active_contracts = db.query(Contract).filter(
            Contract.status == ContractStatus.ACTIVE,
            Contract.next_delivery_tick <= current_tick
        ).all()

        contract_ids = [c.id for c in active_contracts]
        db.close()

        for cid in contract_ids:
            process_delivery(cid, current_tick)

    except Exception as e:
        print(f"[P2P] Tick error: {e}")
        try:
            db.close()
        except:
            pass
