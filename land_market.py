"""
land_market.py (Patched)

Land market module for the economic simulation.
Handles:
- Player-to-player land trading
- Government land auctions (automated based on economy size)
- Land listing and browsing
- Price discovery for land plots
- Auction mechanics (price drops over 24-hour period)
- Land bank for expired/unsold plots
"""

from datetime import datetime, timedelta
from typing import Optional, List
import random
import threading

def _fire_land_push(player_id: int, tag: str, title: str, body: str) -> None:
    if player_id <= 0:
        return
    def _send():
        try:
            from push_ux import send_push_notification
            send_push_notification(player_id, title, body,
                                   url="/landmarket", notif_type="land", tag=tag)
        except Exception as e:
            print(f"[LandMarket] Push error for player {player_id}: {e}")
    threading.Thread(target=_send, daemon=True).start()
from sqlalchemy import Column, String, Float, DateTime, Integer, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from stats_ux import log_transaction
# ==========================
# DATABASE SETUP
# ==========================
from database import engine, SessionLocal
Base = declarative_base()

# ==========================
# DATABASE MODELS
# ==========================

class LandListing(Base):
    """Player listing of land for sale."""
    __tablename__ = "land_listings"
    
    id = Column(Integer, primary_key=True, index=True)
    seller_id = Column(Integer, index=True, nullable=False)
    land_plot_id = Column(Integer, unique=True, index=True, nullable=False)
    asking_price = Column(Float, nullable=False)
    listed_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)


class GovernmentAuction(Base):
    """Government land auction."""
    __tablename__ = "government_auctions"
    
    id = Column(Integer, primary_key=True, index=True)
    land_plot_id = Column(Integer, unique=True, nullable=False)
    
    # Pricing
    starting_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=False)
    minimum_price = Column(Float, nullable=False)  # Floor price
    
    # Timing
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True)
    winner_id = Column(Integer, nullable=True)
    final_price = Column(Float, nullable=True)


class LandSale(Base):
    """Record of completed land sales."""
    __tablename__ = "land_sales"
    
    id = Column(Integer, primary_key=True, index=True)
    land_plot_id = Column(Integer, nullable=False)
    seller_id = Column(Integer, nullable=False)
    buyer_id = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    sale_type = Column(String, nullable=False)  # "player" or "government"
    sold_at = Column(DateTime, default=datetime.utcnow)


class LandBank(Base):
    """Land bank for expired/unsold government plots."""
    __tablename__ = "land_bank"
    
    id = Column(Integer, primary_key=True, index=True)
    land_plot_id = Column(Integer, unique=True, nullable=False)
    original_auction_id = Column(Integer, nullable=True)
    added_at = Column(DateTime, default=datetime.utcnow)
    times_auctioned = Column(Integer, default=1)  # Track retry attempts
    last_auction_price = Column(Float, nullable=True)


class LandBuyOrder(Base):
    """Standing limit buy order for a land plot."""
    __tablename__ = "land_buy_orders"

    id         = Column(Integer, primary_key=True, index=True)
    buyer_id   = Column(Integer, index=True, nullable=False)
    max_price  = Column(Float, nullable=False)           # buyer's maximum acceptable price
    terrain    = Column(String(32), nullable=True)       # optional terrain filter, None = any
    proximity  = Column(String(64), nullable=True)       # optional proximity feature filter, None = any
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active  = Column(Boolean, default=True)


class EconomicMilestone(Base):
    """Track which economic milestones have triggered land creation."""
    __tablename__ = "economic_milestones"
    
    id = Column(Integer, primary_key=True, index=True)
    threshold_level = Column(Integer, unique=True, nullable=False)  # Which $100k milestone
    triggered_at = Column(DateTime, default=datetime.utcnow)
    land_plot_created = Column(Integer, nullable=True)  # Plot ID that was created

# ==========================
# CONSTANTS
# ==========================

AUCTION_DURATION_TICKS = 4000
PRICE_DROP_RATE = 0.15  # Price drops to 35% every hour
ECONOMIC_THRESHOLD = 10000000  # $1M triggers 1 new plot
LAND_BANK_ID = -1  # Special owner ID for land bank
GOVERNMENT_ID = 0  # Government owner ID
LAND_BANK_MAX_SLOTS = 100  # Maximum plots the land bank can hold

# Base prices by terrain
TERRAIN_BASE_PRICES = {
    "prairie": 150000,
    "forest": 180000,
    "desert": 120000,
    "marsh": 140000,
    "mountain": 200000,
    "tundra": 130000,
    "jungle": 170000,
    "savanna": 160000
}

# ==========================
# PROXIMITY GENERATION
# ==========================

def generate_random_proximity_features() -> List[str]:
    """
    Generate random proximity features for auction land plots.
    
    Returns:
        List of 0-3 randomly selected proximity features
    """
    from land import PROXIMITY_FEATURES
    
    all_features = list(PROXIMITY_FEATURES.keys())
    
    # Weighted chance for number of features:
    # 20% chance: 0 features (remote/basic land)
    # 40% chance: 1 feature
    # 30% chance: 2 features
    # 10% chance: 3 features
    roll = random.random()
    if roll < 0.20:
        num_features = 0
    elif roll < 0.60:
        num_features = 1
    elif roll < 0.90:
        num_features = 2
    else:
        num_features = 3
    
    if num_features == 0:
        return []
    
    # Select random features (no duplicates)
    selected = random.sample(all_features, min(num_features, len(all_features)))
    
    # "remote" is mutually exclusive with "urban" - remove one if both present
    if "remote" in selected and "urban" in selected:
        selected.remove("remote")
    
    return selected

# ==========================
# HELPER FUNCTIONS
# ==========================

def get_db():
    """Get database session."""
    db = SessionLocal()
    return db

# ==========================
# PLAYER-TO-PLAYER TRADING
# ==========================

def list_land_for_sale(seller_id: int, land_plot_id: int, asking_price: float) -> Optional[LandListing]:
    """
    List a land plot for sale.
    
    Args:
        seller_id: Player listing the land
        land_plot_id: ID of the land plot
        asking_price: Price the seller wants
    
    Returns:
        Created listing or None if invalid
    """
    from land import get_land_plot
    
    db = get_db()
    try:
        # Validate ownership and vacancy
        plot = get_land_plot(land_plot_id)
        if not plot or plot.owner_id != seller_id:
            print("[LandMarket] Player doesn't own this plot")
            return None
        
        if plot.occupied_by_business_id is not None:
            print("[LandMarket] Cannot sell occupied land")
            return None
        
        if asking_price <= 0:
            print("[LandMarket] Invalid price")
            return None
        
        # Check if already listed (active)
        existing_active = db.query(LandListing).filter(
            LandListing.land_plot_id == land_plot_id,
            LandListing.is_active == True
        ).first()
        
        if existing_active:
            print("[LandMarket] Land already listed")
            return None
        
        # Delete any inactive listings for this plot (to avoid UNIQUE constraint)
        db.query(LandListing).filter(
            LandListing.land_plot_id == land_plot_id,
            LandListing.is_active == False
        ).delete()
        db.commit()
        
        # Create listing
        listing = LandListing(
            seller_id=seller_id,
            land_plot_id=land_plot_id,
            asking_price=asking_price
        )
        
        db.add(listing)
        db.commit()
        db.refresh(listing)
        
        print(f"[LandMarket] Plot {land_plot_id} listed for ${asking_price:,.2f}")
        return listing
    finally:
        db.close()


def buy_listed_land(buyer_id: int, listing_id: int) -> bool:
    """
    Purchase land from a player listing.
    
    Args:
        buyer_id: Player buying the land
        listing_id: ID of the listing
    
    Returns:
        True if successful
    """
    from land import transfer_land
    from auth import transfer_cash
    
    db = get_db()
    try:
        # Get listing
        listing = db.query(LandListing).filter(
            LandListing.id == listing_id,
            LandListing.is_active == True
        ).first()
        
        if not listing:
            return False
        
        # Can't buy your own land
        if listing.seller_id == buyer_id:
            return False
        
        # Apply zoning_expert / land-effect exec bonus to reduce purchase price
        effective_price = listing.asking_price
        try:
            from executive import get_player_job_bonus
            _land_bonus = get_player_job_bonus(db, buyer_id, "land")
            if _land_bonus > 0:
                effective_price = round(listing.asking_price * max(0.05, 1.0 - _land_bonus), 2)
        except Exception:
            pass

        # Transfer cash
        if not transfer_cash(buyer_id, listing.seller_id, effective_price):
            print("[LandMarket] Insufficient funds")
            return False
        
        # Transfer land ownership
        if not transfer_land(listing.land_plot_id, buyer_id):
            # Refund if land transfer fails (e.g. plot was occupied after listing)
            transfer_cash(listing.seller_id, buyer_id, listing.asking_price)
            print(f"[LandMarket] Transfer failed for plot {listing.land_plot_id} (occupied?) — cancelling stale listing")
            listing.is_active = False
            db.commit()
            return False
       
        # Get plot details for logging
        from land import get_land_plot
        plot = get_land_plot(listing.land_plot_id)
        terrain = plot.terrain_type if plot else "unknown"
        
        # Record sale
        sale = LandSale(
            land_plot_id=listing.land_plot_id,
            seller_id=listing.seller_id,
            buyer_id=buyer_id,
            price=listing.asking_price,
            sale_type="player"
        )
        db.add(sale)
        
        # Deactivate listing
        listing.is_active = False
        
        db.commit()
        
        # Log transactions
        # Buyer logs
        log_transaction(
            buyer_id,
            "land_buy",
            "land",
            1,  # 1 plot acquired
            f"Purchased plot #{listing.land_plot_id} ({terrain})",
            str(listing.land_plot_id)
        )
        
        log_transaction(
            buyer_id,
            "cash_out",
            "money",
            -listing.asking_price,
            f"Land purchase: Plot #{listing.land_plot_id}",
            str(listing.land_plot_id)
        )
        
        # Seller logs
        log_transaction(
            listing.seller_id,
            "land_sell",
            "land",
            -1,  # 1 plot sold (negative)
            f"Sold plot #{listing.land_plot_id}",
            str(listing.land_plot_id)
        )
        
        log_transaction(
            listing.seller_id,
            "cash_in",
            "money",
            listing.asking_price,
            f"Land sale: Plot #{listing.land_plot_id}",
            str(listing.land_plot_id)
        )
        
        print(f"[LandMarket] Plot {listing.land_plot_id} sold for ${listing.asking_price:,.2f}")
        _fire_land_push(listing.seller_id, f"land-sold-{listing.land_plot_id}",
            "Plot Sold",
            f"Plot #{listing.land_plot_id} ({terrain}) sold for ${listing.asking_price:,.0f}")
        return True
    finally:
        db.close()


def cancel_listing(seller_id: int, listing_id: int) -> bool:
    """Cancel a land listing."""
    db = get_db()
    try:
        listing = db.query(LandListing).filter(
            LandListing.id == listing_id,
            LandListing.seller_id == seller_id,
            LandListing.is_active == True
        ).first()
        
        if not listing:
            return False
        
        listing.is_active = False
        db.commit()
        
        print(f"[LandMarket] Listing {listing_id} cancelled")
        return True
    finally:
        db.close()


def place_land_buy_order(buyer_id: int, max_price: float,
                          terrain: Optional[str] = None,
                          proximity: Optional[str] = None) -> Optional[LandBuyOrder]:
    """Place a standing limit buy order for land.

    terrain  – restrict to a specific terrain type (None = any)
    proximity – require a specific proximity feature (None = any)
    Returns the new LandBuyOrder, or None if it auto-executed immediately.
    """
    if max_price <= 0:
        return None
    db = get_db()
    try:
        # Auto-execute if a matching active listing already exists
        candidates = db.query(LandListing).filter(
            LandListing.is_active == True,
            LandListing.asking_price <= max_price,
            LandListing.seller_id != buyer_id,
        ).order_by(LandListing.asking_price.asc()).all()

        matching = None
        if terrain or proximity:
            from land import LandPlot
            for listing in candidates:
                plot = db.query(LandPlot).filter(LandPlot.id == listing.land_plot_id).first()
                if not plot:
                    continue
                if terrain and plot.terrain_type != terrain:
                    continue
                if proximity:
                    feats = [f.strip() for f in (plot.proximity_features or "").split(",")]
                    if proximity not in feats:
                        continue
                matching = listing
                break
        elif candidates:
            matching = candidates[0]

        if matching:
            _match_price    = matching.asking_price
            _match_plot_id  = matching.land_plot_id
            db.close()
            ok = buy_listed_land(buyer_id, matching.id)
            if ok:
                _fire_land_push(buyer_id, f"land-order-{_match_plot_id}",
                    "Buy Order Filled",
                    f"Plot #{_match_plot_id} acquired for ${_match_price:,.0f}")
                return None  # executed immediately, no standing order needed
            db = get_db()  # reopen for the standing order insert below

        order = LandBuyOrder(buyer_id=buyer_id, max_price=max_price,
                              terrain=terrain, proximity=proximity)
        db.add(order)
        db.commit()
        db.refresh(order)
        print(f"[LandMarket] Buy order placed: player {buyer_id} max ${max_price:,.2f} "
              f"terrain={terrain} proximity={proximity}")
        return order
    finally:
        try:
            db.close()
        except Exception:
            pass


def cancel_land_buy_order(buyer_id: int, order_id: int) -> bool:
    """Cancel a standing land buy order."""
    db = get_db()
    try:
        order = db.query(LandBuyOrder).filter(
            LandBuyOrder.id == order_id,
            LandBuyOrder.buyer_id == buyer_id,
            LandBuyOrder.is_active == True,
        ).first()
        if not order:
            return False
        order.is_active = False
        db.commit()
        return True
    finally:
        db.close()


def get_player_buy_orders(player_id: int) -> List[LandBuyOrder]:
    """Get all active buy orders for a player."""
    db = get_db()
    try:
        return db.query(LandBuyOrder).filter(
            LandBuyOrder.buyer_id == player_id,
            LandBuyOrder.is_active == True,
        ).order_by(LandBuyOrder.created_at.desc()).all()
    finally:
        db.close()


def get_all_active_buy_orders() -> List[LandBuyOrder]:
    """Get all active buy orders (for market display)."""
    db = get_db()
    try:
        return db.query(LandBuyOrder).filter(
            LandBuyOrder.is_active == True,
        ).order_by(LandBuyOrder.max_price.desc()).all()
    finally:
        db.close()


def get_active_listings() -> List[LandListing]:
    """Get all active land listings."""
    db = get_db()
    try:
        listings = db.query(LandListing).filter(LandListing.is_active == True).all()
        return listings
    finally:
        db.close()

# ==========================
# LAND BANK SYSTEM
# ==========================

def add_to_land_bank(land_plot_id: int, auction_id: Optional[int] = None, last_price: Optional[float] = None) -> bool:
    """
    Add an unsold plot to the land bank.
    
    Args:
        land_plot_id: Plot that failed to sell
        auction_id: Original auction ID
        last_price: Last auction price attempted
    
    Returns:
        True if successful
    """
    from land import LandPlot
    
    db = get_db()
    try:
        # Check if plot exists
        from land import get_land_plot
        plot = get_land_plot(land_plot_id)
        if not plot:
            print(f"[LandMarket] Cannot add non-existent plot {land_plot_id} to land bank")
            return False
        
        # Check if already in land bank
        existing = db.query(LandBank).filter(
            LandBank.land_plot_id == land_plot_id
        ).first()
        
        if existing:
            # Already in bank, increment retry counter
            existing.times_auctioned += 1
            existing.last_auction_price = last_price
            existing.added_at = datetime.utcnow()
            db.commit()
            print(f"[LandMarket] Plot {land_plot_id} returned to land bank (attempt #{existing.times_auctioned})")
            return True

        # Check capacity before adding a new entry
        current_count = db.query(LandBank).count()
        if current_count >= LAND_BANK_MAX_SLOTS:
            print(f"[LandMarket] Land bank full ({current_count}/{LAND_BANK_MAX_SLOTS}) - cannot add plot {land_plot_id}")
            return False

        # Add new entry to land bank
        bank_entry = LandBank(
            land_plot_id=land_plot_id,
            original_auction_id=auction_id,
            times_auctioned=1,
            last_auction_price=last_price
        )
        
        db.add(bank_entry)
        db.commit()
        
        print(f"[LandMarket] Plot {land_plot_id} added to land bank")
        return True
    finally:
        db.close()


def get_land_bank_plots() -> List[LandBank]:
    """Get all plots currently in the land bank."""
    db = get_db()
    try:
        plots = db.query(LandBank).order_by(LandBank.added_at.asc()).all()
        return plots
    finally:
        db.close()


def get_land_bank_count() -> int:
    """Get the current number of plots in the land bank."""
    db = get_db()
    try:
        return db.query(LandBank).count()
    finally:
        db.close()


def is_land_bank_full() -> bool:
    """Check if the land bank has reached its maximum capacity."""
    return get_land_bank_count() >= LAND_BANK_MAX_SLOTS


def remove_from_land_bank(land_plot_id: int) -> bool:
    """Remove a plot from the land bank (sold successfully)."""
    db = get_db()
    try:
        bank_entry = db.query(LandBank).filter(
            LandBank.land_plot_id == land_plot_id
        ).first()
        
        if not bank_entry:
            return False
        
        db.delete(bank_entry)
        db.commit()
        
        print(f"[LandMarket] Plot {land_plot_id} removed from land bank")
        return True
    finally:
        db.close()

# ==========================
# GOVERNMENT AUCTIONS
# ==========================

def check_economic_triggers() -> int:
    """
    Check if economy has grown enough to warrant new land.
    Returns number of plots to create.
    Uses milestone tracking to prevent duplicate creation.
    """
    from auth import get_db as get_auth_db, Player
    from reserve_banks import get_usd_balance

    auth_db = get_auth_db()
    try:
        players = auth_db.query(Player).all()
        total_cash = sum(get_usd_balance(p.id) for p in players)
    finally:
        auth_db.close()
    
    # Calculate current milestone level
    current_milestone = int(total_cash / ECONOMIC_THRESHOLD)
    
    if current_milestone == 0:
        return 0
    
    # Check which milestones have already been triggered
    db = get_db()
    try:
        triggered_milestones = db.query(EconomicMilestone).all()
        triggered_levels = {m.threshold_level for m in triggered_milestones}
        
        # Find milestones that need to be created
        new_plots_needed = 0
        for level in range(1, current_milestone + 1):
            if level not in triggered_levels:
                new_plots_needed += 1
        
        return new_plots_needed
    finally:
        db.close()


def record_economic_milestone(threshold_level: int, land_plot_id: Optional[int] = None):
    """Record that an economic milestone has been triggered."""
    db = get_db()
    try:
        milestone = EconomicMilestone(
            threshold_level=threshold_level,
            land_plot_created=land_plot_id
        )
        db.add(milestone)
        db.commit()
        print(f"[LandMarket] Recorded economic milestone level {threshold_level}")
    finally:
        db.close()


def create_government_auction(from_land_bank: bool = False, bank_entry: Optional[LandBank] = None) -> Optional[GovernmentAuction]:
    """
    Create a new government land auction.
    Called automatically based on economic triggers or from land bank.
    
    Args:
        from_land_bank: If True, re-auction an existing plot from land bank
        bank_entry: The land bank entry to re-auction
    """
    from land import create_land_plot, get_land_plot, TERRAIN_TYPES, PROXIMITY_FEATURES
    
    # When creating new plots, check if land bank is at capacity
    # (unsold auctions end up in the bank, so don't create if it's full)
    if not from_land_bank and is_land_bank_full():
        print(f"[LandMarket] Skipping new auction - land bank at capacity ({LAND_BANK_MAX_SLOTS}/{LAND_BANK_MAX_SLOTS})")
        return None

    if from_land_bank and bank_entry:
        # Re-auctioning from land bank
        plot = get_land_plot(bank_entry.land_plot_id)
        if not plot:
            print(f"[LandMarket] Cannot re-auction non-existent plot {bank_entry.land_plot_id}")
            return None
        
        # Reduce price based on retry attempts (more aggressive pricing)
        base_price = TERRAIN_BASE_PRICES.get(plot.terrain_type, 15000)
        price_reduction = 0.9 ** bank_entry.times_auctioned  # 10% reduction per failed attempt
        starting_price = base_price * price_reduction
        minimum_price = starting_price * 0.3  # Lower floor for retry auctions
        
        print(f"[LandMarket] Re-auctioning plot {plot.id} (attempt #{bank_entry.times_auctioned + 1})")
    else:
        # Creating new land from economic growth
        # Pick random terrain (exclude district terrains - those are only created via merge)
        base_terrains = [t for t in TERRAIN_TYPES.keys() if not t.startswith("district_")]
        terrain = random.choice(base_terrains)
        
        # Generate random proximity features
        proximity_features = generate_random_proximity_features()
        
        # Create government-owned land with proximity features
        plot = create_land_plot(
            owner_id=GOVERNMENT_ID,  # Government ID = 0
            terrain_type=terrain,
            proximity_features=proximity_features if proximity_features else None,
            size=1.0,
            is_starter=False,
            is_government=True
        )
        
        # Set auction prices - factor in proximity for pricing
        base_price = TERRAIN_BASE_PRICES.get(terrain, 15000)
        
        # Apply proximity modifiers to auction price
        price_modifier = 1.0
        for feature in (proximity_features or []):
            if feature in PROXIMITY_FEATURES:
                price_modifier *= PROXIMITY_FEATURES[feature]["tax_modifier"]
        
        base_price *= price_modifier
        starting_price = base_price * 1.5  # Start 50% above base
        minimum_price = base_price * 0.5   # Floor at 50% of base
        
        features_str = f" + {', '.join(proximity_features)}" if proximity_features else " (no proximity features)"
        print(f"[LandMarket] Creating auction for {terrain}{features_str}")
    
    db = get_db()
    try:
        # Check if plot already has an active auction
        existing_active = db.query(GovernmentAuction).filter(
            GovernmentAuction.land_plot_id == plot.id,
            GovernmentAuction.is_active == True
        ).first()
        
        if existing_active:
            print(f"[LandMarket] Plot {plot.id} already has active auction")
            return None
        
        # Delete any inactive auctions for this plot (to avoid UNIQUE constraint)
        db.query(GovernmentAuction).filter(
            GovernmentAuction.land_plot_id == plot.id,
            GovernmentAuction.is_active == False
        ).delete()
        db.commit()
        
        auction = GovernmentAuction(
            land_plot_id=plot.id,
            starting_price=starting_price,
            current_price=starting_price,
            minimum_price=minimum_price,
            end_time=datetime.utcnow() + timedelta(seconds=AUCTION_DURATION_TICKS)
        )
        
        db.add(auction)
        db.commit()
        db.refresh(auction)
        
        # Remove from land bank if re-auctioning
        if from_land_bank and bank_entry:
            remove_from_land_bank(bank_entry.land_plot_id)
        
        print(f"[LandMarket] New {plot.terrain_type} auction created: ${starting_price:,.2f} -> ${minimum_price:,.2f}")
        return auction
    finally:
        db.close()


def update_auction_prices(current_tick: int):
    """
    Update auction prices (Dutch auction - price drops over time).
    Called every tick.
    Moves expired auctions to land bank.
    """
    db = get_db()
    try:
        auctions = db.query(GovernmentAuction).filter(
            GovernmentAuction.is_active == True
        ).all()
        
        for auction in auctions:
            # Check if expired
            if datetime.utcnow() >= auction.end_time:
                auction.is_active = False
                
                # Move to land bank
                add_to_land_bank(
                    auction.land_plot_id,
                    auction.id,
                    auction.current_price
                )
                
                print(f"[LandMarket] Auction {auction.id} expired unsold -> moved to land bank")
                continue
            
            # Drop price every hour (3600 ticks)
            if current_tick % 3600 == 0:
                new_price = auction.current_price * PRICE_DROP_RATE
                
                # Don't go below minimum
                auction.current_price = max(new_price, auction.minimum_price)
                
                print(f"[LandMarket] Auction {auction.id} price dropped to ${auction.current_price:,.2f}")
        
        db.commit()
    finally:
        db.close()


def buy_auction_land(buyer_id: int, auction_id: int) -> bool:
    """
    Purchase land from government auction at current price.
    
    Args:
        buyer_id: Player buying the land
        auction_id: ID of the auction
    
    Returns:
        True if successful
    """
    from land import transfer_land
    from auth import get_db as get_auth_db, Player
    
    db = get_db()
    try:
        auction = db.query(GovernmentAuction).filter(
            GovernmentAuction.id == auction_id,
            GovernmentAuction.is_active == True
        ).first()
        
        if not auction:
            return False
        
        # Check if buyer has funds (supports foreign legal tender)
        from reserve_banks import can_afford_usd, spend_player_funds
        if not can_afford_usd(buyer_id, auction.current_price):
            return False

        # Deduct (economic sink — government does not receive it)
        ok, err = spend_player_funds(buyer_id, auction.current_price)
        if not ok:
            print(f"[LandMarket] Auction payment failed for player {buyer_id}: {err}")
            return False

        # Transfer land to buyer
        if not transfer_land(auction.land_plot_id, buyer_id):
            # Refund if transfer fails (convert back to buyer's legal tender)
            try:
                from reserve_banks import credit_usd
                credit_usd(buyer_id, auction.current_price)
            except Exception as _ref_e:
                print(f"[LandMarket] Refund error after failed land transfer: {_ref_e}")
            return False
        
        # Record sale
        sale = LandSale(
            land_plot_id=auction.land_plot_id,
            seller_id=GOVERNMENT_ID,  # Government
            buyer_id=buyer_id,
            price=auction.current_price,
            sale_type="government"
        )
        db.add(sale)
        
        # Close auction
        auction.is_active = False
        auction.winner_id = buyer_id
        auction.final_price = auction.current_price
        
        # Remove from land bank if it was there
        remove_from_land_bank(auction.land_plot_id)
        
        db.commit()
        
        # Log auction purchase
        from land import get_land_plot
        plot = get_land_plot(auction.land_plot_id)
        terrain = plot.terrain_type if plot else "unknown"
        
        log_transaction(
            buyer_id,
            "land_buy",
            "land",
            1,
            f"Won auction: plot #{auction.land_plot_id} ({terrain})",
            str(auction.land_plot_id)
        )
        
        log_transaction(
            buyer_id,
            "cash_out",
            "money",
            -auction.current_price,
            f"Auction payment: Plot #{auction.land_plot_id}",
            str(auction.land_plot_id)
        )
        
        print(f"[LandMarket] Auction won by player {buyer_id} for ${auction.current_price:,.2f}")
        
        # Record revenue to land bank
        try:
            from banks.land_bank import record_auction_sale
            record_auction_sale(auction.current_price, auction.land_plot_id)
        except Exception:
            pass
        
        return True
    finally:
        db.close()


def get_active_auctions() -> List[GovernmentAuction]:
    """Get all active government auctions."""
    db = get_db()
    try:
        auctions = db.query(GovernmentAuction).filter(
            GovernmentAuction.is_active == True
        ).order_by(GovernmentAuction.end_time.asc()).all()
        return auctions
    finally:
        db.close()


def get_recent_sales(limit: int = 10) -> List[LandSale]:
    """Get recent land sales for price history."""
    db = get_db()
    try:
        sales = db.query(LandSale).order_by(
            LandSale.sold_at.desc()
        ).limit(limit).all()
        return sales
    finally:
        db.close()

# ==========================
# MODULE LIFECYCLE
# ==========================

def initialize():
    """Initialize land market module."""
    print("[LandMarket] Creating database tables...")
    Base.metadata.create_all(bind=engine)

    # Migrations for columns added after initial deployment
    from database import run_ddl_migration
    run_ddl_migration(engine, "ALTER TABLE land_buy_orders ADD COLUMN IF NOT EXISTS proximity VARCHAR(64)")
    
    # Check land bank status
    db = get_db()
    try:
        bank_count = db.query(LandBank).count()
        print(f"[LandMarket] Land bank: {bank_count}/{LAND_BANK_MAX_SLOTS} slots used")
    finally:
        db.close()

    print("[LandMarket] Module initialized")


def tick(current_tick: int, now: datetime):
    """
    Land market tick handler.
    - Updates auction prices (Dutch auction)
    - Checks economic triggers for new land
    - Re-auctions plots from land bank
    """
    # Update auction prices every tick
    update_auction_prices(current_tick)
    
    if current_tick % 30 == 0:
        plots_needed = check_economic_triggers()

        if plots_needed > 0:
            # Check land bank capacity before creating new plots
            if is_land_bank_full():
                print(f"[LandMarket] Economy expanded but land bank full ({LAND_BANK_MAX_SLOTS}/{LAND_BANK_MAX_SLOTS}) - deferring plot creation")
                plots_needed = 0

        if plots_needed > 0:
            print(f"[LandMarket] Economy expanded! Creating {plots_needed} new auction(s)")

            # Get current milestone level
            from auth import get_db as get_auth_db, Player
            from reserve_banks import get_usd_balance
            auth_db = get_auth_db()
            try:
                players = auth_db.query(Player).all()
                total_cash = sum(get_usd_balance(p.id) for p in players)
            finally:
                auth_db.close()
            
            current_milestone = int(total_cash / ECONOMIC_THRESHOLD)
            
            # Find which milestones need creation
            db = get_db()
            try:
                triggered_milestones = db.query(EconomicMilestone).all()
                triggered_levels = {m.threshold_level for m in triggered_milestones}
                
                for level in range(1, current_milestone + 1):
                    if level not in triggered_levels:
                        auction = create_government_auction()
                        if auction:
                            record_economic_milestone(level, auction.land_plot_id)
            finally:
                db.close()
    
    # Re-auction plots from land bank every 30 minutes (1800 ticks)
    if current_tick % 140 == 0:
        bank_plots = get_land_bank_plots()
        
        if bank_plots:
            # Re-auction oldest plot in bank
            oldest = bank_plots[0]
            print(f"[LandMarket] Re-auctioning plot {oldest.land_plot_id} from land bank")
            create_government_auction(from_land_bank=True, bank_entry=oldest)
    
    # Log stats every hour
    if current_tick % 36 == 0:
        db = get_db()
        try:
            active_listings = db.query(LandListing).filter(LandListing.is_active == True).count()
            active_auctions = db.query(GovernmentAuction).filter(GovernmentAuction.is_active == True).count()
            bank_count = db.query(LandBank).count()
            
            print(f"[LandMarket] Stats: {active_listings} player listings, {active_auctions} gov auctions, {bank_count}/{LAND_BANK_MAX_SLOTS} land bank slots")
        finally:
            db.close()

# ==========================
# PUBLIC API
# ==========================

__all__ = [
    'list_land_for_sale',
    'buy_listed_land',
    'cancel_listing',
    'get_active_listings',
    'create_government_auction',
    'buy_auction_land',
    'get_active_auctions',
    'get_recent_sales',
    'get_land_bank_plots',
    'get_land_bank_count',
    'is_land_bank_full',
    'LAND_BANK_MAX_SLOTS',
    'generate_random_proximity_features',
    'LandListing',
    'GovernmentAuction',
    'LandSale',
    'LandBank',
    'EconomicMilestone'
]
