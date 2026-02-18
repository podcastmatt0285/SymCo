"""
memecoins.py

Layer-2 meme coin / shitcoin system built on top of county blockchains.

City members in a county can launch their own tokens using the county's
native token as the base asset.

Key mechanics:
  CREATION:
    - Any city member in the county can launch a meme coin
    - Creation burns a fee in native county tokens (30 native tokens burned)
    - Creator receives 10% founder allocation immediately
    - 90% goes to mining pool (mined by staking native tokens)

  MINING (Staking):
    - Any county member can stake native tokens to mine meme coins
    - Rewards distributed proportionally to stake every hour
    - Reward rate halves every MEME_HALVING_INTERVAL tokens minted
    - Native tokens remain locked; can be unstaked at any time (partial OK)

  TRADING (Order Book):
    - Limit and market orders, priced in native county tokens
    - Fee: 2% total (1% to creator, 0.5% to county treasury, 0.5% burned)
    - OHLCV candlestick data recorded per hour

  PRICE DISCOVERY:
    - Pure order book matching engine
    - Last trade price is the market price
    - Hourly OHLCV candles stored for charting
"""

from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from sqlalchemy import create_engine, Column, String, Float, DateTime, Integer, Boolean, Text, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import math
import hashlib
import random

# ==========================
# DATABASE SETUP
# ==========================
DATABASE_URL = "sqlite:///./wadsworth.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ==========================
# CONSTANTS
# ==========================
MEME_CREATION_FEE_NATIVE = 30.0        # Native tokens burned to create a meme coin
MEME_FOUNDER_ALLOCATION_PCT = 0.10     # 10% to creator immediately
MEME_MINING_ALLOCATION_PCT = 0.90      # 90% to mining pool
MEME_INITIAL_BLOCK_REWARD = 1000.0     # Meme coins per native token staked per cycle (initial)
MEME_HALVING_INTERVAL = 500_000.0      # Meme coins minted before reward halves
MEME_MIN_BLOCK_REWARD = 0.00000001
MEME_MINING_PAYOUT_INTERVAL_TICKS = 720  # Every hour
MEME_CANDLE_INTERVAL_TICKS = 720         # Hourly candles
MEME_TRADE_FEE_TOTAL = 0.02             # 2% fee on trades
MEME_FEE_TO_CREATOR = 0.50             # 50% of fee to creator
MEME_FEE_TO_TREASURY = 0.25            # 25% of fee to county treasury
MEME_FEE_BURNED = 0.25                 # 25% of fee burned
MIN_MEME_SUPPLY = 1_000_000.0          # Minimum total supply: 1 million
MAX_MEME_SUPPLY = 1_000_000_000_000.0  # Maximum total supply: 1 trillion
MEME_SYMBOL_MIN_LEN = 3
MEME_SYMBOL_MAX_LEN = 6
MEME_MIN_STAKE = 0.000001              # Minimum native tokens to stake


# ==========================
# DATABASE MODELS
# ==========================

class MemeCoin(Base):
    """A meme coin / shitcoin launched by a city member on a county's blockchain."""
    __tablename__ = "meme_coins"

    id = Column(Integer, primary_key=True, index=True)
    county_id = Column(Integer, index=True, nullable=False)
    creator_id = Column(Integer, index=True, nullable=False)
    city_id = Column(Integer, index=True, nullable=False)  # Creator's city

    name = Column(String, nullable=False)           # e.g., "DogWifHat"
    symbol = Column(String, unique=True, nullable=False)  # e.g., "DWH" (3-6 chars)
    description = Column(Text, default="")
    logo_svg = Column(Text, nullable=True)

    # Supply
    total_supply = Column(Float, nullable=False)         # Total ever possible
    minted_supply = Column(Float, default=0.0)           # How much has been minted
    mining_allocation = Column(Float, nullable=False)    # Amount going to miners
    mining_minted = Column(Float, default=0.0)           # How much of mining_allocation minted

    # Mining pool
    mining_pool_native = Column(Float, default=0.0)     # Native tokens currently staked
    mining_reward_base = Column(Float, nullable=False)   # Base reward rate (set at creation)
    mining_enabled = Column(Boolean, default=True)

    # Price tracking (in native tokens)
    last_price = Column(Float, default=0.0)
    all_time_high = Column(Float, default=0.0)
    all_time_low = Column(Float, nullable=True)

    # Stats
    total_volume_native = Column(Float, default=0.0)
    total_trades = Column(Integer, default=0)

    # Creation fee burned
    creation_fee_burned = Column(Float, default=MEME_CREATION_FEE_NATIVE)

    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)


class MemeCoinWallet(Base):
    """Player's meme coin holdings."""
    __tablename__ = "meme_coin_wallets"

    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, index=True, nullable=False)
    meme_symbol = Column(String, index=True, nullable=False)

    balance = Column(Float, default=0.0)
    total_mined = Column(Float, default=0.0)
    total_bought = Column(Float, default=0.0)
    total_sold = Column(Float, default=0.0)

    created_at = Column(DateTime, default=datetime.utcnow)


class MemeCoinMiningDeposit(Base):
    """Native tokens staked by a player to mine a meme coin."""
    __tablename__ = "meme_coin_mining_deposits"

    id = Column(Integer, primary_key=True, index=True)
    meme_symbol = Column(String, index=True, nullable=False)
    player_id = Column(Integer, index=True, nullable=False)
    native_symbol = Column(String, nullable=False)  # County's native crypto symbol

    quantity = Column(Float, nullable=False)         # Native tokens staked
    deposited_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    total_earned = Column(Float, default=0.0)        # Total meme coins earned from this deposit


class MemeCoinCandlestick(Base):
    """OHLCV candlestick data for a meme coin (hourly)."""
    __tablename__ = "meme_coin_candlesticks"

    id = Column(Integer, primary_key=True, index=True)
    meme_symbol = Column(String, index=True, nullable=False)

    open_price = Column(Float, nullable=False)    # In native tokens
    high_price = Column(Float, nullable=False)
    low_price = Column(Float, nullable=False)
    close_price = Column(Float, nullable=False)
    volume = Column(Float, default=0.0)           # Volume in native tokens

    candle_open_time = Column(DateTime, nullable=False, index=True)
    candle_close_time = Column(DateTime, nullable=False)
    is_closed = Column(Boolean, default=False)    # False = current forming candle


class MemeCoinOrder(Base):
    """An order on the meme coin order book."""
    __tablename__ = "meme_coin_orders"

    id = Column(Integer, primary_key=True, index=True)
    meme_symbol = Column(String, index=True, nullable=False)
    player_id = Column(Integer, index=True, nullable=False)

    order_type = Column(String, nullable=False)   # "buy" or "sell"
    order_mode = Column(String, default="limit")  # "limit" or "market"

    price = Column(Float, nullable=True)          # In native tokens; None for market orders
    quantity = Column(Float, nullable=False)       # Meme coins
    quantity_filled = Column(Float, default=0.0)

    # For buy limit orders: native tokens reserved from wallet
    native_reserved = Column(Float, default=0.0)

    status = Column(String, default="active")     # active, filled, partial, cancelled
    created_at = Column(DateTime, default=datetime.utcnow)
    filled_at = Column(DateTime, nullable=True)


class MemeCoinTrade(Base):
    """Executed trade record for a meme coin pair."""
    __tablename__ = "meme_coin_trades"

    id = Column(Integer, primary_key=True, index=True)
    meme_symbol = Column(String, index=True, nullable=False)

    buyer_id = Column(Integer, nullable=False)
    seller_id = Column(Integer, nullable=False)
    buy_order_id = Column(Integer, nullable=True)
    sell_order_id = Column(Integer, nullable=True)

    quantity = Column(Float, nullable=False)           # Meme coins traded
    price = Column(Float, nullable=False)              # Native tokens per meme coin
    native_volume = Column(Float, nullable=False)      # quantity * price
    fee_native = Column(Float, default=0.0)           # Total fee in native tokens

    executed_at = Column(DateTime, default=datetime.utcnow)


# ==========================
# DATABASE HELPERS
# ==========================

def get_db():
    db = SessionLocal()
    try:
        return db
    except Exception as e:
        print(f"[MemeCoin] DB error: {e}")
        db.close()
        raise


def get_or_create_meme_wallet(db, player_id: int, meme_symbol: str) -> MemeCoinWallet:
    wallet = db.query(MemeCoinWallet).filter(
        MemeCoinWallet.player_id == player_id,
        MemeCoinWallet.meme_symbol == meme_symbol
    ).first()
    if not wallet:
        wallet = MemeCoinWallet(player_id=player_id, meme_symbol=meme_symbol)
        db.add(wallet)
        db.flush()
    return wallet


def get_meme_wallet_balance(player_id: int, meme_symbol: str) -> float:
    db = get_db()
    try:
        wallet = db.query(MemeCoinWallet).filter(
            MemeCoinWallet.player_id == player_id,
            MemeCoinWallet.meme_symbol == meme_symbol
        ).first()
        return wallet.balance if wallet else 0.0
    finally:
        db.close()


# ==========================
# SVG LOGO GENERATION
# ==========================

def generate_meme_logo_svg(symbol: str, seed_extra: str = "") -> str:
    """Generate a chaotic, colorful pixel art logo for a meme coin."""
    seed = hashlib.sha256((symbol + seed_extra).encode()).hexdigest()
    rng = random.Random(seed)

    # Meme coins get brighter, more chaotic colors
    def rand_bright_color():
        h = rng.randint(0, 360)
        s = rng.randint(80, 100)
        l = rng.randint(45, 70)
        return f"hsl({h},{s}%,{l}%)"

    bg = f"hsl({rng.randint(0,360)},{rng.randint(5,20)}%,{rng.randint(8,15)}%)"
    colors = [rand_bright_color() for _ in range(rng.randint(3, 5))]

    grid_size = 8
    pixel_size = 4
    pixels = []
    for y in range(grid_size):
        for x in range(grid_size // 2):
            if rng.random() > 0.35:  # More dense than county tokens
                color = rng.choice(colors)
                pixels.append((x, y, color))
                pixels.append((grid_size - 1 - x, y, color))

    svg_size = grid_size * pixel_size
    rects = "".join(
        f'<rect x="{px*pixel_size}" y="{py*pixel_size}" width="{pixel_size}" height="{pixel_size}" fill="{c}"/>'
        for px, py, c in pixels
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_size} {svg_size}" '
        f'width="32" height="32"><rect width="{svg_size}" height="{svg_size}" fill="{bg}"/>'
        f'{rects}</svg>'
    )


# ==========================
# HALVING / REWARD CALC
# ==========================

def calculate_meme_block_reward(meme_coin: MemeCoin) -> float:
    """Reward per native token staked per cycle (decays with halvings)."""
    halvings = int(meme_coin.mining_minted / MEME_HALVING_INTERVAL)
    reward = meme_coin.mining_reward_base / (2 ** halvings)
    return max(reward, MEME_MIN_BLOCK_REWARD)


# ==========================
# MEME COIN CREATION
# ==========================

def launch_meme_coin(
    player_id: int,
    name: str,
    symbol: str,
    description: str,
    total_supply: float,
    county_id: int,
) -> Tuple[Optional[str], str]:
    """
    Returns (symbol_str, message) on success or (None, error_message) on failure.
    Returns the symbol string (not the ORM object) to avoid DetachedInstanceError.
    """
    """
    Launch a new meme coin on a county's blockchain.

    Requirements:
    - Player must be a city member in the county
    - Symbol must be 3-6 uppercase letters, unique
    - Total supply between 1M and 1T
    - Player must hold >= MEME_CREATION_FEE_NATIVE of the county's native token

    Returns (MemeCoin, message) or (None, error_message)
    """
    from counties import (
        County, CryptoWallet, CountyCity, get_db as county_get_db,
        is_player_in_county
    )
    from cities import CityMember, get_db as city_get_db

    # --- Validation ---
    symbol = symbol.strip().upper()
    name = name.strip()
    description = description.strip()

    if not (MEME_SYMBOL_MIN_LEN <= len(symbol) <= MEME_SYMBOL_MAX_LEN):
        return None, f"Symbol must be {MEME_SYMBOL_MIN_LEN}-{MEME_SYMBOL_MAX_LEN} characters."
    if not symbol.isalpha():
        return None, "Symbol must contain only letters."
    if not name or len(name) > 40:
        return None, "Name must be 1-40 characters."
    if not (MIN_MEME_SUPPLY <= total_supply <= MAX_MEME_SUPPLY):
        return None, f"Total supply must be between {MIN_MEME_SUPPLY:,.0f} and {MAX_MEME_SUPPLY:,.0f}."

    # Check player is in county
    if not is_player_in_county(player_id, county_id):
        return None, "You must be a city member in this county to launch a meme coin here."

    db = get_db()
    county_db = county_get_db()
    try:
        # Check symbol uniqueness across ALL meme coins
        existing = db.query(MemeCoin).filter(MemeCoin.symbol == symbol).first()
        if existing:
            return None, f"Symbol '{symbol}' is already taken by another meme coin."

        # Also check not clashing with county native symbols
        existing_native = county_db.query(County).filter(County.crypto_symbol == symbol).first()
        if existing_native:
            return None, f"Symbol '{symbol}' is already a county native token."

        # Get the county's native token symbol
        county = county_db.query(County).filter(County.id == county_id).first()
        if not county:
            return None, "County not found."
        native_symbol = county.crypto_symbol

        # Check player has enough native tokens for creation fee
        native_wallet = county_db.query(CryptoWallet).filter(
            CryptoWallet.player_id == player_id,
            CryptoWallet.crypto_symbol == native_symbol,
        ).first()
        if not native_wallet or native_wallet.balance < MEME_CREATION_FEE_NATIVE:
            return None, (
                f"Insufficient native tokens. You need {MEME_CREATION_FEE_NATIVE:.2f} "
                f"{native_symbol} to launch a meme coin (creation fee, burned forever)."
            )

        # Get creator's city_id
        city_db = city_get_db()
        city_links = county_db.query(CountyCity).filter(CountyCity.county_id == county_id).all()
        city_ids = [l.city_id for l in city_links]
        membership = city_db.query(CityMember).filter(
            CityMember.player_id == player_id,
            CityMember.city_id.in_(city_ids)
        ).first()
        city_db.close()
        creator_city_id = membership.city_id if membership else 0

        # --- Deduct creation fee (burn native tokens) ---
        native_wallet.balance -= MEME_CREATION_FEE_NATIVE
        native_wallet.total_sold = (native_wallet.total_sold or 0.0) + MEME_CREATION_FEE_NATIVE
        county_db.commit()

        # Also reduce county's circulating supply (tokens burned)
        county.total_crypto_burned = (county.total_crypto_burned or 0.0) + MEME_CREATION_FEE_NATIVE
        county_db.commit()

        # --- Create meme coin ---
        founder_alloc = total_supply * MEME_FOUNDER_ALLOCATION_PCT
        mining_alloc = total_supply * MEME_MINING_ALLOCATION_PCT

        # Base reward: mine 1% of mining allocation per halving interval worth of activity
        # i.e., reward_base = (mining_alloc / MEME_HALVING_INTERVAL) * some scale
        # We want mining_alloc to be distributed over ~4 halvings (so reward_base chosen accordingly)
        # Simple: reward_base = 1.0 meme per native token per payout (adjusted by halving)
        mining_reward_base = 1.0  # 1 meme coin per native token staked per hourly payout cycle

        meme = MemeCoin(
            county_id=county_id,
            creator_id=player_id,
            city_id=creator_city_id,
            name=name,
            symbol=symbol,
            description=description,
            logo_svg=generate_meme_logo_svg(symbol, name),
            total_supply=total_supply,
            minted_supply=founder_alloc,
            mining_allocation=mining_alloc,
            mining_minted=0.0,
            mining_pool_native=0.0,
            mining_reward_base=mining_reward_base,
            mining_enabled=True,
            last_price=0.0,
            all_time_high=0.0,
            all_time_low=None,
            total_volume_native=0.0,
            total_trades=0,
            creation_fee_burned=MEME_CREATION_FEE_NATIVE,
        )
        db.add(meme)
        db.flush()

        # Give creator the founder allocation
        wallet = get_or_create_meme_wallet(db, player_id, symbol)
        wallet.balance += founder_alloc
        wallet.total_mined += founder_alloc  # Count as "mined" for founder

        db.commit()

        # Return the symbol string (not the ORM object) — accessing meme attributes
        # after db.close() in the finally block would raise DetachedInstanceError.
        return symbol, (
            f"'{name}' ({symbol}) launched! You received {founder_alloc:,.2f} founder tokens. "
            f"{MEME_CREATION_FEE_NATIVE:.2f} {native_symbol} burned as creation fee."
        )

    except Exception as e:
        db.rollback()
        county_db.rollback()
        print(f"[MemeCoin] Error launching meme coin: {e}")
        import traceback; traceback.print_exc()
        return None, f"Error launching meme coin: {str(e)}"
    finally:
        db.close()
        county_db.close()


# ==========================
# MINING (STAKING)
# ==========================

def stake_native_for_mining(
    player_id: int,
    meme_symbol: str,
    native_amount: float,
) -> Tuple[bool, str]:
    """
    Stake native tokens to mine a meme coin.
    Native tokens are locked until unstaked.
    """
    from counties import CryptoWallet, County, get_db as county_get_db

    if native_amount < MEME_MIN_STAKE:
        return False, f"Minimum stake is {MEME_MIN_STAKE} native tokens."

    db = get_db()
    county_db = county_get_db()
    try:
        meme = db.query(MemeCoin).filter(MemeCoin.symbol == meme_symbol, MemeCoin.is_active == True).first()
        if not meme:
            return False, "Meme coin not found."
        if not meme.mining_enabled:
            return False, "Mining is disabled for this coin."
        if meme.mining_minted >= meme.mining_allocation:
            return False, "All mining rewards have been distributed."

        # Get county native symbol
        county = county_db.query(County).filter(County.id == meme.county_id).first()
        native_symbol = county.crypto_symbol

        # Check player's native token balance
        native_wallet = county_db.query(CryptoWallet).filter(
            CryptoWallet.player_id == player_id,
            CryptoWallet.crypto_symbol == native_symbol,
        ).first()
        if not native_wallet or native_wallet.balance < native_amount:
            return False, f"Insufficient {native_symbol}. You have {native_wallet.balance if native_wallet else 0:.6f}."

        # Lock native tokens
        native_wallet.balance -= native_amount
        county_db.commit()

        # Create mining deposit
        deposit = MemeCoinMiningDeposit(
            meme_symbol=meme_symbol,
            player_id=player_id,
            native_symbol=native_symbol,
            quantity=native_amount,
            is_active=True,
        )
        db.add(deposit)

        # Update meme coin pool
        meme.mining_pool_native = (meme.mining_pool_native or 0.0) + native_amount
        db.commit()

        return True, f"Staked {native_amount:.6f} {native_symbol} to mine {meme_symbol}."

    except Exception as e:
        db.rollback()
        county_db.rollback()
        print(f"[MemeCoin] Stake error: {e}")
        return False, f"Error: {str(e)}"
    finally:
        db.close()
        county_db.close()


def unstake_native(
    player_id: int,
    deposit_id: int,
) -> Tuple[bool, str]:
    """
    Unstake native tokens from a meme coin mining pool.
    Returns native tokens to player's wallet.
    """
    from counties import CryptoWallet, get_db as county_get_db

    db = get_db()
    county_db = county_get_db()
    try:
        deposit = db.query(MemeCoinMiningDeposit).filter(
            MemeCoinMiningDeposit.id == deposit_id,
            MemeCoinMiningDeposit.player_id == player_id,
            MemeCoinMiningDeposit.is_active == True,
        ).first()
        if not deposit:
            return False, "Active deposit not found."

        meme = db.query(MemeCoin).filter(MemeCoin.symbol == deposit.meme_symbol).first()
        if meme:
            meme.mining_pool_native = max(0.0, (meme.mining_pool_native or 0.0) - deposit.quantity)

        # Return native tokens
        native_wallet = county_db.query(CryptoWallet).filter(
            CryptoWallet.player_id == player_id,
            CryptoWallet.crypto_symbol == deposit.native_symbol,
        ).first()
        if native_wallet:
            native_wallet.balance += deposit.quantity
        else:
            from counties import CryptoWallet
            new_wallet = CryptoWallet(
                player_id=player_id,
                crypto_symbol=deposit.native_symbol,
                balance=deposit.quantity,
            )
            county_db.add(new_wallet)

        deposit.is_active = False
        db.commit()
        county_db.commit()

        return True, f"Unstaked {deposit.quantity:.6f} {deposit.native_symbol} from {deposit.meme_symbol} mining."

    except Exception as e:
        db.rollback()
        county_db.rollback()
        print(f"[MemeCoin] Unstake error: {e}")
        return False, f"Error: {str(e)}"
    finally:
        db.close()
        county_db.close()


def process_meme_mining_payouts():
    """
    Distribute meme coin mining rewards to all active stakers.
    Called every hour (MEME_MINING_PAYOUT_INTERVAL_TICKS).
    Rewards are proportional to stake size.
    """
    db = get_db()
    try:
        # Get all active meme coins with mining
        active_memes = db.query(MemeCoin).filter(
            MemeCoin.is_active == True,
            MemeCoin.mining_enabled == True,
        ).all()

        for meme in active_memes:
            if meme.mining_minted >= meme.mining_allocation:
                continue  # Fully minted
            if (meme.mining_pool_native or 0.0) <= 0:
                continue  # No stakers

            # Get all active deposits for this meme coin
            deposits = db.query(MemeCoinMiningDeposit).filter(
                MemeCoinMiningDeposit.meme_symbol == meme.symbol,
                MemeCoinMiningDeposit.is_active == True,
            ).all()
            if not deposits:
                continue

            total_staked = sum(d.quantity for d in deposits)
            if total_staked <= 0:
                continue

            # Block reward = reward_base * total_staked (with halving)
            reward_per_native = calculate_meme_block_reward(meme)
            total_reward = reward_per_native * total_staked

            # Cap at remaining mining allocation
            remaining = meme.mining_allocation - meme.mining_minted
            total_reward = min(total_reward, remaining)
            if total_reward <= 0:
                continue

            # Distribute proportionally
            for dep in deposits:
                share = dep.quantity / total_staked
                player_reward = total_reward * share
                if player_reward <= 0:
                    continue

                wallet = get_or_create_meme_wallet(db, dep.player_id, meme.symbol)
                wallet.balance += player_reward
                wallet.total_mined += player_reward
                dep.total_earned += player_reward

            # Update meme coin totals
            meme.mining_minted = min(
                meme.mining_minted + total_reward,
                meme.mining_allocation
            )
            meme.minted_supply = min(
                meme.minted_supply + total_reward,
                meme.total_supply
            )

            if meme.mining_minted >= meme.mining_allocation:
                meme.mining_enabled = False
                print(f"[MemeCoin] {meme.symbol} mining complete.")

        db.commit()

    except Exception as e:
        db.rollback()
        print(f"[MemeCoin] Mining payout error: {e}")
        import traceback; traceback.print_exc()
    finally:
        db.close()


# ==========================
# ORDER BOOK TRADING
# ==========================

def place_order(
    player_id: int,
    meme_symbol: str,
    order_type: str,       # "buy" or "sell"
    order_mode: str,       # "limit" or "market"
    quantity: float,       # Meme coins
    price: Optional[float] = None,  # In native tokens; None for market
) -> Tuple[Optional[MemeCoinOrder], str]:
    """
    Place a buy or sell order on the meme coin order book.

    Buy limit: reserves native tokens from CryptoWallet.
    Sell limit: reserves meme coins from MemeCoinWallet.
    Market orders execute immediately against best available.
    """
    from counties import CryptoWallet, County, get_db as county_get_db

    if quantity <= 0:
        return None, "Quantity must be positive."
    if order_mode == "limit" and (price is None or price <= 0):
        return None, "Limit orders require a positive price."

    db = get_db()
    county_db = county_get_db()
    try:
        meme = db.query(MemeCoin).filter(
            MemeCoin.symbol == meme_symbol,
            MemeCoin.is_active == True,
        ).first()
        if not meme:
            return None, "Meme coin not found or inactive."

        county = county_db.query(County).filter(County.id == meme.county_id).first()
        native_symbol = county.crypto_symbol

        native_wallet = county_db.query(CryptoWallet).filter(
            CryptoWallet.player_id == player_id,
            CryptoWallet.crypto_symbol == native_symbol,
        ).first()
        meme_wallet = db.query(MemeCoinWallet).filter(
            MemeCoinWallet.player_id == player_id,
            MemeCoinWallet.meme_symbol == meme_symbol,
        ).first()

        native_balance = native_wallet.balance if native_wallet else 0.0
        meme_balance = meme_wallet.balance if meme_wallet else 0.0

        native_reserved = 0.0

        if order_type == "buy":
            if order_mode == "limit":
                cost = quantity * price
                if native_balance < cost:
                    return None, (
                        f"Insufficient {native_symbol}. Need {cost:.6f}, have {native_balance:.6f}."
                    )
                # Reserve native tokens
                if native_wallet:
                    native_wallet.balance -= cost
                native_reserved = cost
                county_db.commit()
            # market buy: we'll try to fill at whatever ask prices are available

        elif order_type == "sell":
            if meme_balance < quantity:
                return None, (
                    f"Insufficient {meme_symbol}. Need {quantity:.6f}, have {meme_balance:.6f}."
                )
            # Reserve meme coins
            meme_wallet_obj = get_or_create_meme_wallet(db, player_id, meme_symbol)
            meme_wallet_obj.balance -= quantity
            db.flush()

        order = MemeCoinOrder(
            meme_symbol=meme_symbol,
            player_id=player_id,
            order_type=order_type,
            order_mode=order_mode,
            price=price,
            quantity=quantity,
            quantity_filled=0.0,
            native_reserved=native_reserved,
            status="active",
        )
        db.add(order)
        db.flush()

        # Try to match immediately
        _match_orders(db, county_db, meme, native_symbol, order)

        db.commit()
        county_db.commit()

        remaining = order.quantity - order.quantity_filled
        if order.status == "filled":
            return order, f"Order fully filled! Traded {order.quantity_filled:.6f} {meme_symbol}."
        elif order.status == "partial":
            return order, f"Order partially filled. {order.quantity_filled:.6f} filled, {remaining:.6f} remaining."
        else:
            return order, f"Order placed. Waiting for matching orders."

    except Exception as e:
        db.rollback()
        county_db.rollback()
        print(f"[MemeCoin] Order error: {e}")
        import traceback; traceback.print_exc()
        return None, f"Error placing order: {str(e)}"
    finally:
        db.close()
        county_db.close()


def _match_orders(db, county_db, meme: MemeCoin, native_symbol: str, incoming_order: MemeCoinOrder):
    """
    Match the incoming order against the book.
    Updates order statuses, wallets, trade records, and OHLCV.
    """
    from counties import CryptoWallet

    symbol = meme.symbol

    if incoming_order.order_type == "buy":
        # Find sell orders at or below buy price (or any if market)
        query = db.query(MemeCoinOrder).filter(
            MemeCoinOrder.meme_symbol == symbol,
            MemeCoinOrder.order_type == "sell",
            MemeCoinOrder.status.in_(["active", "partial"]),
            MemeCoinOrder.player_id != incoming_order.player_id,
        )
        if incoming_order.order_mode == "limit":
            query = query.filter(MemeCoinOrder.price <= incoming_order.price)
        # Sort: best ask first (lowest price)
        counterpart_orders = query.order_by(MemeCoinOrder.price.asc(), MemeCoinOrder.created_at.asc()).all()
    else:
        # Find buy orders at or above sell price (or any if market)
        query = db.query(MemeCoinOrder).filter(
            MemeCoinOrder.meme_symbol == symbol,
            MemeCoinOrder.order_type == "buy",
            MemeCoinOrder.status.in_(["active", "partial"]),
            MemeCoinOrder.player_id != incoming_order.player_id,
        )
        if incoming_order.order_mode == "limit":
            query = query.filter(MemeCoinOrder.price >= incoming_order.price)
        # Sort: best bid first (highest price)
        counterpart_orders = query.order_by(MemeCoinOrder.price.desc(), MemeCoinOrder.created_at.asc()).all()

    incoming_remaining = incoming_order.quantity - incoming_order.quantity_filled

    for counter in counterpart_orders:
        if incoming_remaining <= 0:
            break

        counter_remaining = counter.quantity - counter.quantity_filled
        fill_qty = min(incoming_remaining, counter_remaining)
        if fill_qty <= 0:
            continue

        # Trade price = the counter-party's limit price (price improvement for taker)
        trade_price = counter.price if counter.price else meme.last_price
        if trade_price is None or trade_price <= 0:
            continue

        native_volume = fill_qty * trade_price
        total_fee = native_volume * MEME_TRADE_FEE_TOTAL
        creator_fee = total_fee * MEME_FEE_TO_CREATOR
        treasury_fee = total_fee * MEME_FEE_TO_TREASURY
        # burned_fee = total_fee * MEME_FEE_BURNED  (simply not distributed)

        if incoming_order.order_type == "buy":
            buyer_id = incoming_order.player_id
            seller_id = counter.player_id
            buy_order_id = incoming_order.id
            sell_order_id = counter.id
        else:
            buyer_id = counter.player_id
            seller_id = incoming_order.player_id
            buy_order_id = counter.id
            sell_order_id = incoming_order.id

        # --- Settle buyer (gets meme coins) ---
        buyer_meme_wallet = get_or_create_meme_wallet(db, buyer_id, symbol)
        buyer_meme_wallet.balance += fill_qty
        buyer_meme_wallet.total_bought += fill_qty

        # --- Settle seller (gets native tokens, minus fee) ---
        net_native_to_seller = native_volume - creator_fee - treasury_fee
        # (burned fee is just not paid out)
        net_native_to_seller -= total_fee * MEME_FEE_BURNED  # ensure burned portion deducted

        seller_native_wallet = county_db.query(CryptoWallet).filter(
            CryptoWallet.player_id == seller_id,
            CryptoWallet.crypto_symbol == native_symbol,
        ).first()
        if not seller_native_wallet:
            seller_native_wallet = CryptoWallet(
                player_id=seller_id,
                crypto_symbol=native_symbol,
                balance=0.0,
            )
            county_db.add(seller_native_wallet)
        seller_native_wallet.balance += net_native_to_seller
        seller_meme_w = get_or_create_meme_wallet(db, seller_id, symbol)
        seller_meme_w.total_sold += fill_qty

        # --- Refund buyer's over-reserved native tokens if buying below limit price ---
        if incoming_order.order_type == "buy" and incoming_order.order_mode == "limit":
            reserved_for_this_fill = fill_qty * incoming_order.price
            actual_cost = native_volume  # fill_qty * trade_price
            refund = reserved_for_this_fill - actual_cost
            if refund > 0.0001:
                buyer_native_wallet = county_db.query(CryptoWallet).filter(
                    CryptoWallet.player_id == buyer_id,
                    CryptoWallet.crypto_symbol == native_symbol,
                ).first()
                if buyer_native_wallet:
                    buyer_native_wallet.balance += refund
                incoming_order.native_reserved -= refund
        elif counter.order_type == "buy" and counter.order_mode == "limit":
            reserved_for_fill = fill_qty * counter.price
            actual_cost = native_volume
            refund = reserved_for_fill - actual_cost
            if refund > 0.0001:
                buyer_native_wallet = county_db.query(CryptoWallet).filter(
                    CryptoWallet.player_id == counter.player_id,
                    CryptoWallet.crypto_symbol == native_symbol,
                ).first()
                if buyer_native_wallet:
                    buyer_native_wallet.balance += refund

        # --- Pay creator fee ---
        creator_native_wallet = county_db.query(CryptoWallet).filter(
            CryptoWallet.player_id == meme.creator_id,
            CryptoWallet.crypto_symbol == native_symbol,
        ).first()
        if not creator_native_wallet:
            creator_native_wallet = CryptoWallet(
                player_id=meme.creator_id,
                crypto_symbol=native_symbol,
                balance=0.0,
            )
            county_db.add(creator_native_wallet)
        creator_native_wallet.balance += creator_fee

        # --- Pay treasury fee (to county treasury balance) ---
        from counties import County
        county_obj = county_db.query(County).filter(County.id == meme.county_id).first()
        if county_obj:
            county_obj.treasury_balance = (county_obj.treasury_balance or 0.0) + treasury_fee

        # --- Update order fill quantities ---
        incoming_order.quantity_filled += fill_qty
        counter.quantity_filled += fill_qty
        incoming_remaining -= fill_qty

        if counter.quantity_filled >= counter.quantity:
            counter.status = "filled"
            counter.filled_at = datetime.utcnow()
        else:
            counter.status = "partial"

        # --- Record trade ---
        trade = MemeCoinTrade(
            meme_symbol=symbol,
            buyer_id=buyer_id,
            seller_id=seller_id,
            buy_order_id=buy_order_id,
            sell_order_id=sell_order_id,
            quantity=fill_qty,
            price=trade_price,
            native_volume=native_volume,
            fee_native=total_fee,
        )
        db.add(trade)

        # --- Update meme coin price & stats ---
        old_price = meme.last_price or 0.0
        meme.last_price = trade_price
        if meme.all_time_high is None or trade_price > meme.all_time_high:
            meme.all_time_high = trade_price
        if meme.all_time_low is None or trade_price < meme.all_time_low:
            meme.all_time_low = trade_price
        meme.total_volume_native = (meme.total_volume_native or 0.0) + native_volume
        meme.total_trades = (meme.total_trades or 0) + 1

        # --- Update OHLCV candle ---
        _update_candle(db, symbol, trade_price, native_volume)

    # Update incoming order status
    if incoming_order.quantity_filled >= incoming_order.quantity:
        incoming_order.status = "filled"
        incoming_order.filled_at = datetime.utcnow()
    elif incoming_order.quantity_filled > 0:
        incoming_order.status = "partial"

    # For market orders that didn't fill: cancel and refund
    if incoming_order.order_mode == "market" and incoming_order.status not in ("filled",):
        unfilled = incoming_order.quantity - incoming_order.quantity_filled
        if unfilled > 0:
            if incoming_order.order_type == "sell":
                # Return unsold meme coins
                wallet = get_or_create_meme_wallet(db, incoming_order.player_id, symbol)
                wallet.balance += unfilled
            incoming_order.status = "filled" if incoming_order.quantity_filled > 0 else "cancelled"


def _update_candle(db, meme_symbol: str, price: float, volume: float):
    """Update or create the current hourly OHLCV candle."""
    now = datetime.utcnow()
    # Floor to the nearest hour
    candle_open = now.replace(minute=0, second=0, microsecond=0)
    candle_close = candle_open + timedelta(hours=1)

    candle = db.query(MemeCoinCandlestick).filter(
        MemeCoinCandlestick.meme_symbol == meme_symbol,
        MemeCoinCandlestick.candle_open_time == candle_open,
        MemeCoinCandlestick.is_closed == False,
    ).first()

    if candle:
        candle.high_price = max(candle.high_price, price)
        candle.low_price = min(candle.low_price, price)
        candle.close_price = price
        candle.volume += volume
    else:
        # Close previous open candle
        db.query(MemeCoinCandlestick).filter(
            MemeCoinCandlestick.meme_symbol == meme_symbol,
            MemeCoinCandlestick.is_closed == False,
        ).update({"is_closed": True})

        candle = MemeCoinCandlestick(
            meme_symbol=meme_symbol,
            open_price=price,
            high_price=price,
            low_price=price,
            close_price=price,
            volume=volume,
            candle_open_time=candle_open,
            candle_close_time=candle_close,
            is_closed=False,
        )
        db.add(candle)


def cancel_order(player_id: int, order_id: int) -> Tuple[bool, str]:
    """Cancel an active or partial order and refund reserved assets."""
    from counties import CryptoWallet, County, get_db as county_get_db

    db = get_db()
    county_db = county_get_db()
    try:
        order = db.query(MemeCoinOrder).filter(
            MemeCoinOrder.id == order_id,
            MemeCoinOrder.player_id == player_id,
            MemeCoinOrder.status.in_(["active", "partial"]),
        ).first()
        if not order:
            return False, "Order not found or not cancellable."

        unfilled = order.quantity - order.quantity_filled
        meme = db.query(MemeCoin).filter(MemeCoin.symbol == order.meme_symbol).first()

        if order.order_type == "buy" and order.order_mode == "limit":
            # Refund remaining reserved native tokens
            refund_native = unfilled * order.price
            county = county_db.query(County).filter(County.id == meme.county_id).first()
            native_wallet = county_db.query(CryptoWallet).filter(
                CryptoWallet.player_id == player_id,
                CryptoWallet.crypto_symbol == county.crypto_symbol,
            ).first()
            if native_wallet:
                native_wallet.balance += refund_native
            county_db.commit()

        elif order.order_type == "sell":
            # Return unsold meme coins
            wallet = get_or_create_meme_wallet(db, player_id, order.meme_symbol)
            wallet.balance += unfilled

        order.status = "cancelled"
        db.commit()
        return True, f"Order #{order_id} cancelled."

    except Exception as e:
        db.rollback()
        county_db.rollback()
        return False, f"Error: {str(e)}"
    finally:
        db.close()
        county_db.close()


# ==========================
# DATA QUERIES
# ==========================

def get_all_meme_coins(county_id: int) -> List[dict]:
    """Get all active meme coins for a county."""
    db = get_db()
    try:
        memes = db.query(MemeCoin).filter(
            MemeCoin.county_id == county_id,
            MemeCoin.is_active == True,
        ).order_by(MemeCoin.created_at.desc()).all()

        result = []
        for m in memes:
            from auth import Player
            creator = db.query(Player).filter(Player.id == m.creator_id).first()
            holder_count = db.query(MemeCoinWallet).filter(
                MemeCoinWallet.meme_symbol == m.symbol,
                MemeCoinWallet.balance > 0,
            ).count()
            change_24h = _get_meme_price_change_24h(db, m.symbol, m.last_price or 0.0)
            result.append({
                "id": m.id,
                "name": m.name,
                "symbol": m.symbol,
                "description": m.description,
                "logo_svg": m.logo_svg or "",
                "county_id": m.county_id,
                "creator_name": creator.business_name if creator else f"Player {m.creator_id}",
                "total_supply": m.total_supply,
                "minted_supply": m.minted_supply or 0.0,
                "mining_allocation": m.mining_allocation,
                "mining_minted": m.mining_minted or 0.0,
                "mining_pool_native": m.mining_pool_native or 0.0,
                "mining_enabled": m.mining_enabled,
                "last_price": m.last_price or 0.0,
                "all_time_high": m.all_time_high or 0.0,
                "all_time_low": m.all_time_low,
                "total_volume_native": m.total_volume_native or 0.0,
                "total_trades": m.total_trades or 0,
                "holder_count": holder_count,
                "price_change_24h": change_24h,
                "market_cap_native": (m.last_price or 0.0) * (m.minted_supply or 0.0),
                "created_at": m.created_at,
            })
        return result
    except Exception as e:
        print(f"[MemeCoin] Error getting meme coins: {e}")
        return []
    finally:
        db.close()


def get_meme_coin_detail(symbol: str) -> Optional[dict]:
    """Get full detail for a meme coin including order book snapshot."""
    db = get_db()
    try:
        meme = db.query(MemeCoin).filter(MemeCoin.symbol == symbol).first()
        if not meme:
            return None

        from auth import Player
        creator = db.query(Player).filter(Player.id == meme.creator_id).first()
        holder_count = db.query(MemeCoinWallet).filter(
            MemeCoinWallet.meme_symbol == symbol,
            MemeCoinWallet.balance > 0,
        ).count()
        change_24h = _get_meme_price_change_24h(db, symbol, meme.last_price or 0.0)
        high_24h, low_24h = _get_meme_24h_high_low(db, symbol)
        vol_24h = _get_meme_24h_volume(db, symbol)

        # Order book snapshot (top 10 bids and asks)
        bids = db.query(MemeCoinOrder).filter(
            MemeCoinOrder.meme_symbol == symbol,
            MemeCoinOrder.order_type == "buy",
            MemeCoinOrder.status.in_(["active", "partial"]),
        ).order_by(MemeCoinOrder.price.desc()).limit(10).all()

        asks = db.query(MemeCoinOrder).filter(
            MemeCoinOrder.meme_symbol == symbol,
            MemeCoinOrder.order_type == "sell",
            MemeCoinOrder.status.in_(["active", "partial"]),
        ).order_by(MemeCoinOrder.price.asc()).limit(10).all()

        # Recent trades
        recent_trades = db.query(MemeCoinTrade).filter(
            MemeCoinTrade.meme_symbol == symbol,
        ).order_by(MemeCoinTrade.executed_at.desc()).limit(20).all()

        from counties import County, get_db as county_get_db
        county_db = county_get_db()
        county = county_db.query(County).filter(County.id == meme.county_id).first()
        native_symbol = county.crypto_symbol if county else "???"
        county_db.close()

        # Block reward calc
        block_reward = calculate_meme_block_reward(meme)

        return {
            "id": meme.id,
            "name": meme.name,
            "symbol": symbol,
            "description": meme.description,
            "logo_svg": meme.logo_svg or "",
            "county_id": meme.county_id,
            "native_symbol": native_symbol,
            "creator_id": meme.creator_id,
            "creator_name": creator.business_name if creator else f"Player {meme.creator_id}",
            "total_supply": meme.total_supply,
            "minted_supply": meme.minted_supply or 0.0,
            "mining_allocation": meme.mining_allocation,
            "mining_minted": meme.mining_minted or 0.0,
            "mining_pool_native": meme.mining_pool_native or 0.0,
            "mining_enabled": meme.mining_enabled,
            "block_reward": block_reward,
            "last_price": meme.last_price or 0.0,
            "all_time_high": meme.all_time_high or 0.0,
            "all_time_low": meme.all_time_low,
            "price_change_24h": change_24h,
            "high_24h": high_24h,
            "low_24h": low_24h,
            "volume_24h": vol_24h,
            "total_volume_native": meme.total_volume_native or 0.0,
            "total_trades": meme.total_trades or 0,
            "market_cap_native": (meme.last_price or 0.0) * (meme.minted_supply or 0.0),
            "holder_count": holder_count,
            "creation_fee_burned": meme.creation_fee_burned or MEME_CREATION_FEE_NATIVE,
            "created_at": meme.created_at,
            "is_active": meme.is_active,
            "bids": [
                {
                    "id": o.id,
                    "price": o.price,
                    "quantity": o.quantity - o.quantity_filled,
                    "player_id": o.player_id,
                }
                for o in bids
            ],
            "asks": [
                {
                    "id": o.id,
                    "price": o.price,
                    "quantity": o.quantity - o.quantity_filled,
                    "player_id": o.player_id,
                }
                for o in asks
            ],
            "recent_trades": [
                {
                    "buyer_id": t.buyer_id,
                    "seller_id": t.seller_id,
                    "quantity": t.quantity,
                    "price": t.price,
                    "native_volume": t.native_volume,
                    "executed_at": t.executed_at.isoformat(),
                }
                for t in recent_trades
            ],
        }
    except Exception as e:
        print(f"[MemeCoin] Error getting detail: {e}")
        import traceback; traceback.print_exc()
        return None
    finally:
        db.close()


def get_meme_candles(symbol: str, limit: int = 168) -> List[dict]:
    """
    Get OHLCV candlestick data for charting.
    Returns up to `limit` hourly candles (default 168 = 7 days).
    """
    db = get_db()
    try:
        candles = db.query(MemeCoinCandlestick).filter(
            MemeCoinCandlestick.meme_symbol == symbol,
        ).order_by(MemeCoinCandlestick.candle_open_time.desc()).limit(limit).all()

        # Return oldest first (for chart display)
        candles = list(reversed(candles))
        return [
            {
                "time": int(c.candle_open_time.timestamp()),
                "open": c.open_price,
                "high": c.high_price,
                "low": c.low_price,
                "close": c.close_price,
                "volume": c.volume,
            }
            for c in candles
        ]
    except Exception as e:
        print(f"[MemeCoin] Error getting candles: {e}")
        return []
    finally:
        db.close()


def get_meme_holders(symbol: str) -> List[dict]:
    """Get holder distribution for pie chart."""
    db = get_db()
    try:
        wallets = db.query(MemeCoinWallet).filter(
            MemeCoinWallet.meme_symbol == symbol,
            MemeCoinWallet.balance > 0,
        ).order_by(MemeCoinWallet.balance.desc()).limit(20).all()

        from auth import Player
        result = []
        for w in wallets:
            p = db.query(Player).filter(Player.id == w.player_id).first()
            result.append({
                "player_id": w.player_id,
                "name": p.business_name if p else f"Player {w.player_id}",
                "balance": w.balance,
                "total_mined": w.total_mined or 0.0,
                "total_bought": w.total_bought or 0.0,
                "total_sold": w.total_sold or 0.0,
            })
        return result
    except Exception as e:
        print(f"[MemeCoin] Error getting holders: {e}")
        return []
    finally:
        db.close()


def get_player_meme_wallets(player_id: int) -> List[dict]:
    """Get all meme coin wallets for a player."""
    db = get_db()
    try:
        wallets = db.query(MemeCoinWallet).filter(
            MemeCoinWallet.player_id == player_id,
            MemeCoinWallet.balance > 0,
        ).all()
        result = []
        for w in wallets:
            meme = db.query(MemeCoin).filter(MemeCoin.symbol == w.meme_symbol).first()
            result.append({
                "symbol": w.meme_symbol,
                "name": meme.name if meme else w.meme_symbol,
                "balance": w.balance,
                "last_price": meme.last_price if meme else 0.0,
                "county_id": meme.county_id if meme else None,
                "total_mined": w.total_mined or 0.0,
                "total_bought": w.total_bought or 0.0,
                "total_sold": w.total_sold or 0.0,
            })
        return result
    except Exception as e:
        return []
    finally:
        db.close()


def get_player_mining_deposits(player_id: int, meme_symbol: str) -> List[dict]:
    """Get a player's active mining deposits for a meme coin."""
    db = get_db()
    try:
        deposits = db.query(MemeCoinMiningDeposit).filter(
            MemeCoinMiningDeposit.player_id == player_id,
            MemeCoinMiningDeposit.meme_symbol == meme_symbol,
            MemeCoinMiningDeposit.is_active == True,
        ).all()
        return [
            {
                "id": d.id,
                "native_symbol": d.native_symbol,
                "quantity": d.quantity,
                "total_earned": d.total_earned or 0.0,
                "deposited_at": d.deposited_at.isoformat(),
            }
            for d in deposits
        ]
    except Exception as e:
        return []
    finally:
        db.close()


def get_player_open_orders(player_id: int, meme_symbol: str) -> List[dict]:
    """Get a player's open orders for a meme coin."""
    db = get_db()
    try:
        orders = db.query(MemeCoinOrder).filter(
            MemeCoinOrder.player_id == player_id,
            MemeCoinOrder.meme_symbol == meme_symbol,
            MemeCoinOrder.status.in_(["active", "partial"]),
        ).order_by(MemeCoinOrder.created_at.desc()).all()
        return [
            {
                "id": o.id,
                "order_type": o.order_type,
                "order_mode": o.order_mode,
                "price": o.price,
                "quantity": o.quantity,
                "quantity_filled": o.quantity_filled,
                "native_reserved": o.native_reserved,
                "status": o.status,
                "created_at": o.created_at.isoformat(),
            }
            for o in orders
        ]
    except Exception as e:
        return []
    finally:
        db.close()


def _get_meme_price_change_24h(db, symbol: str, current_price: float) -> float:
    yesterday = datetime.utcnow() - timedelta(hours=24)
    old = db.query(MemeCoinCandlestick).filter(
        MemeCoinCandlestick.meme_symbol == symbol,
        MemeCoinCandlestick.candle_open_time <= yesterday,
    ).order_by(MemeCoinCandlestick.candle_open_time.desc()).first()
    if old and old.close_price > 0:
        return ((current_price - old.close_price) / old.close_price) * 100.0
    return 0.0


def _get_meme_24h_high_low(db, symbol: str) -> Tuple[float, float]:
    yesterday = datetime.utcnow() - timedelta(hours=24)
    candles = db.query(MemeCoinCandlestick).filter(
        MemeCoinCandlestick.meme_symbol == symbol,
        MemeCoinCandlestick.candle_open_time >= yesterday,
    ).all()
    if not candles:
        return 0.0, 0.0
    return max(c.high_price for c in candles), min(c.low_price for c in candles)


def _get_meme_24h_volume(db, symbol: str) -> float:
    yesterday = datetime.utcnow() - timedelta(hours=24)
    trades = db.query(MemeCoinTrade).filter(
        MemeCoinTrade.meme_symbol == symbol,
        MemeCoinTrade.executed_at >= yesterday,
    ).all()
    return sum(t.native_volume for t in trades)


# ==========================
# MODULE LIFECYCLE
# ==========================

def initialize():
    """Create database tables for meme coins."""
    print("[MemeCoin] Creating database tables...")
    Base.metadata.create_all(bind=engine)
    db = get_db()
    count = db.query(MemeCoin).count()
    db.close()
    print(f"[MemeCoin] {count} meme coins active. Module initialized.")


async def tick(current_tick: int, now: datetime):
    """
    Meme coin tick handler.
    - Mining payouts every hour
    - Hourly candle closure happens automatically via _update_candle
    """
    try:
        if current_tick % MEME_MINING_PAYOUT_INTERVAL_TICKS == 0:
            process_meme_mining_payouts()
    except Exception as e:
        print(f"[MemeCoin] Tick error: {e}")
        import traceback; traceback.print_exc()


# ==========================
# PUBLIC API
# ==========================
__all__ = [
    'MemeCoin', 'MemeCoinWallet', 'MemeCoinMiningDeposit',
    'MemeCoinCandlestick', 'MemeCoinOrder', 'MemeCoinTrade',
    'launch_meme_coin', 'stake_native_for_mining', 'unstake_native',
    'place_order', 'cancel_order',
    'get_all_meme_coins', 'get_meme_coin_detail', 'get_meme_candles',
    'get_meme_holders', 'get_player_meme_wallets',
    'get_player_mining_deposits', 'get_player_open_orders',
    'MEME_CREATION_FEE_NATIVE', 'MEME_TRADE_FEE_TOTAL',
]
