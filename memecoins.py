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
from sqlalchemy import Column, String, Float, DateTime, Integer, Boolean, Text, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import math
import hashlib
import random

# ==========================
# DATABASE SETUP
# ==========================
from database import engine, SessionLocal
Base = declarative_base()

# ==========================
# CONSTANTS
# ==========================
# DESIGN NOTE — INTENTIONAL TAX HAVEN: crypto and meme-coin activity is
# deliberately invisible to the government tax/fee system. No portion of any
# crypto transaction routes to government ledgers. This is a core strategic
# feature (players can shelter wealth in county tokens), not a missing
# integration. Do NOT "fix" this by adding government fee routing.
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

# ---- Anti-manipulation guards ----
# Minimum age (seconds) a resting order must have before it can be filled.
# Prevents instant self-trade round-trips.
MAKER_MIN_AGE_SECONDS: int = 5

# Maximum price deviation factor from the 24-hour VWAP.
# A trade that would execute above VWAP * factor or below VWAP / factor is skipped.
# 20× allows genuine discovery on new/thin coins while blocking astronomical manipulation.
PRICE_DEVIATION_MAX_FACTOR: float = 20.0

# Look-back window used when computing the reference VWAP.
PRICE_DEVIATION_LOOKBACK_HOURS: int = 24
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

    # Total native tokens burned directly via burn-to-mint mechanism
    total_directly_burned = Column(Float, default=0.0)

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


def _compute_24h_vwap(db, meme_symbol: str) -> Optional[float]:
    """
    Return the 24-hour volume-weighted average price for a meme coin.

    Uses MemeCoinTrade records from the last PRICE_DEVIATION_LOOKBACK_HOURS hours.
    Returns None when there are no trades in the window (new / illiquid coin),
    allowing the caller to skip the VWAP guard for the first trade on a coin.
    """
    cutoff = datetime.utcnow() - timedelta(hours=PRICE_DEVIATION_LOOKBACK_HOURS)
    trades = (
        db.query(MemeCoinTrade)
        .filter(
            MemeCoinTrade.meme_symbol == meme_symbol,
            MemeCoinTrade.executed_at >= cutoff,
        )
        .all()
    )
    if not trades:
        return None
    # VWAP = Σ(price × quantity) / Σ(quantity) = Σ(native_volume) / Σ(quantity)
    # native_volume = price * quantity, so dividing by total quantity gives true VWAP.
    # Dividing native_volume by native_volume (old code) re-multiplied by price,
    # squaring price in the numerator and inflating the result.
    total_quantity = sum(t.quantity for t in trades)
    if total_quantity <= 0:
        return None
    return sum(t.native_volume for t in trades) / total_quantity


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
# BURN-TO-MINT
# ==========================

def mint_by_burning(meme_id: int, player_id: int, native_amount: float) -> tuple:
    """
    Burn native county tokens to mint new meme coins (bonding curve mechanism).

    Mint price = (total_creation_fee_burned + total_directly_burned) / max(minted_supply, 1)
    This ensures value is always proportional to total native tokens ever burned.

    Returns (coins_minted, new_mint_price, error_message)
    """
    if native_amount <= 0:
        return 0.0, 0.0, "Burn amount must be positive"

    db = get_db()
    county_db = None
    try:
        meme = db.query(MemeCoin).filter(MemeCoin.id == meme_id, MemeCoin.is_active == True).first()
        if not meme:
            return 0.0, 0.0, "Meme coin not found or inactive"

        # Find the county for this meme coin
        from counties import County, get_db as get_county_db, CryptoWallet
        county_db = get_county_db()
        county = county_db.query(County).filter(County.id == meme.county_id).first()
        if not county:
            return 0.0, 0.0, "County not found"

        # Check player has enough native tokens in their wallet (burn + gas)
        from counties import _apply_gas, GAS_UNITS_MEME_TRADE
        native_wallet = county_db.query(CryptoWallet).filter(
            CryptoWallet.player_id == player_id,
            CryptoWallet.crypto_symbol == county.crypto_symbol,
        ).first()
        balance = native_wallet.balance if native_wallet else 0.0
        if balance < native_amount:
            return 0.0, 0.0, f"Insufficient {county.crypto_symbol} balance (have {balance:.4f}, need {native_amount:.4f})"

        # Calculate current backing price (native tokens per meme coin)
        total_burned = (meme.creation_fee_burned or MEME_CREATION_FEE_NATIVE) + (meme.total_directly_burned or 0.0)
        current_minted = max(meme.minted_supply or 1.0, 1.0)
        backing_price = total_burned / current_minted  # native tokens per meme coin

        if backing_price <= 0:
            backing_price = 1.0  # floor at 1:1

        # Coins minted = burned / current backing price
        coins_minted = native_amount / backing_price

        # Check we don't exceed total_supply
        remaining_supply = meme.total_supply - (meme.minted_supply or 0.0)
        if coins_minted > remaining_supply:
            if remaining_supply <= 0:
                return 0.0, 0.0, "Max supply already reached"
            coins_minted = remaining_supply
            native_amount = coins_minted * backing_price  # adjust burn to match

        # Charge gas fee (on top of the burn amount)
        gas_fee, gas_err = _apply_gas(county, native_wallet, GAS_UNITS_MEME_TRADE)
        if gas_err:
            return 0.0, 0.0, gas_err

        # Deduct native tokens from player wallet
        if not native_wallet or native_wallet.balance < native_amount:
            return 0.0, 0.0, "Insufficient balance after gas fee"
        native_wallet.balance -= native_amount

        # Burn: reduce county circulating supply
        county.total_crypto_burned = (county.total_crypto_burned or 0.0) + native_amount

        # Add meme coins to player wallet
        meme_wallet = get_or_create_meme_wallet(db, player_id, meme.symbol)
        meme_wallet.balance += coins_minted
        meme_wallet.total_bought = (meme_wallet.total_bought or 0.0) + coins_minted

        # Update meme coin state
        meme.minted_supply = (meme.minted_supply or 0.0) + coins_minted
        meme.total_directly_burned = (meme.total_directly_burned or 0.0) + native_amount

        # Update last_price to reflect new backing price
        new_total_burned = total_burned + native_amount
        new_minted = meme.minted_supply
        new_backing_price = new_total_burned / max(new_minted, 1.0)
        meme.last_price = new_backing_price

        # Commit both DBs together — county first (simpler), then meme DB
        county_db.commit()
        db.commit()

        print(f"[Memecoins] Burn-to-mint: player {player_id} burned {native_amount:.4f} {county.crypto_symbol} "
              f"-> minted {coins_minted:.4f} {meme.symbol} @ {backing_price:.6f} backing price")

        try:
            from stats_ux import log_transaction as _log
            _log(
                player_id, "meme_burn_mint", "crypto", -native_amount,
                f"Burned {native_amount:.4f} {county.crypto_symbol} → minted {coins_minted:.4f} {meme.symbol}",
                item_type=meme.symbol, quantity=coins_minted,
            )
        except Exception:
            pass

        return coins_minted, new_backing_price, None

    except Exception as e:
        db.rollback()
        if county_db:
            county_db.rollback()
        print(f"[Memecoins] mint_by_burning error: {e}")
        import traceback; traceback.print_exc()
        return 0.0, 0.0, str(e)
    finally:
        db.close()
        if county_db:
            county_db.close()


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
    creation_burn_native: float = None,
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

        # Resolve burn amount — must be at least the minimum creation fee
        if creation_burn_native is None:
            creation_burn_native = MEME_CREATION_FEE_NATIVE
        creation_burn_native = float(creation_burn_native)
        if creation_burn_native < MEME_CREATION_FEE_NATIVE:
            return None, (
                f"Burn amount must be at least {MEME_CREATION_FEE_NATIVE:.2f} {native_symbol} "
                f"(the minimum creation fee)."
            )

        # Check player has enough native tokens for the chosen burn amount + gas
        from counties import _apply_gas, GAS_UNITS_MEME_LAUNCH, BASE_GAS_PRICE
        native_wallet = county_db.query(CryptoWallet).filter(
            CryptoWallet.player_id == player_id,
            CryptoWallet.crypto_symbol == native_symbol,
        ).first()
        gas_preview = max(county.gas_price or BASE_GAS_PRICE, BASE_GAS_PRICE) * GAS_UNITS_MEME_LAUNCH
        total_needed = creation_burn_native + gas_preview
        if not native_wallet or native_wallet.balance < total_needed:
            have = native_wallet.balance if native_wallet else 0.0
            return None, (
                f"Insufficient native tokens. Need {creation_burn_native:.2f} creation fee + "
                f"{gas_preview:.6f} gas = {total_needed:.6f} {native_symbol}. Have {have:.4f}."
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

        # --- Charge gas fee (before deducting creation burn) ---
        gas_fee, gas_err = _apply_gas(county, native_wallet, GAS_UNITS_MEME_LAUNCH)
        if gas_err:
            county_db.close()
            return None, gas_err

        # --- Deduct creation fee (burn native tokens) ---
        native_wallet.balance -= creation_burn_native
        native_wallet.total_sold = (native_wallet.total_sold or 0.0) + creation_burn_native
        county_db.commit()

        # Also reduce county's circulating supply (tokens burned)
        county.total_crypto_burned = (county.total_crypto_burned or 0.0) + creation_burn_native
        county_db.commit()

        # --- Create meme coin ---
        founder_alloc = total_supply * MEME_FOUNDER_ALLOCATION_PCT
        mining_alloc = total_supply * MEME_MINING_ALLOCATION_PCT

        # Base reward scales with mining_alloc so that any supply size mines at a
        # comparable pace.  A flat 1.0 was a placeholder that caused "heat death"
        # for large-supply coins: the reward decays to MEME_MIN_BLOCK_REWARD after
        # only ~60 halvings regardless of supply, leaving trillions of coins unmined
        # forever.  Scaling by mining_alloc / MEME_HALVING_INTERVAL means the first
        # halving always occurs after the same fraction of the mining pool is minted,
        # regardless of total supply size.
        mining_reward_base = mining_alloc / MEME_HALVING_INTERVAL

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
            creation_fee_burned=creation_burn_native,
        )
        db.add(meme)
        db.flush()

        # Give creator the founder allocation
        wallet = get_or_create_meme_wallet(db, player_id, symbol)
        wallet.balance += founder_alloc
        wallet.total_mined += founder_alloc  # Count as "mined" for founder

        db.commit()

        try:
            from stats_ux import log_transaction as _log
            _log(
                player_id, "meme_launch", "crypto", -creation_burn_native,
                f"Launched '{name}' ({symbol}): burned {creation_burn_native:.2f} "
                f"{native_symbol}, received {founder_alloc:,.2f} founder tokens",
                item_type=symbol, quantity=founder_alloc,
            )
        except Exception:
            pass

        # Return the symbol string (not the ORM object) — accessing meme attributes
        # after db.close() in the finally block would raise DetachedInstanceError.
        initial_backing = creation_burn_native / max(founder_alloc, 1.0)
        return symbol, (
            f"'{name}' ({symbol}) launched! You received {founder_alloc:,.2f} founder tokens. "
            f"{creation_burn_native:.2f} {native_symbol} burned → opening backing price "
            f"{initial_backing:.6f} {native_symbol}/{symbol}."
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
    from counties import CryptoWallet, County, get_db as county_get_db, _apply_gas, GAS_UNITS_MEME_STAKE

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
        if not county:
            return False, f"County for {meme_symbol} not found — the blockchain may have been removed."
        native_symbol = county.crypto_symbol

        # Check player's native token balance (stake + gas)
        native_wallet = county_db.query(CryptoWallet).filter(
            CryptoWallet.player_id == player_id,
            CryptoWallet.crypto_symbol == native_symbol,
        ).first()
        if not native_wallet or native_wallet.balance < native_amount:
            return False, f"Insufficient {native_symbol}. You have {native_wallet.balance if native_wallet else 0:.6f}."

        # Charge gas (on top of the stake amount)
        gas_fee, gas_err = _apply_gas(county, native_wallet, GAS_UNITS_MEME_STAKE)
        if gas_err:
            return False, gas_err

        # Re-check balance after gas
        if native_wallet.balance < native_amount:
            return False, f"Insufficient {native_symbol} after gas fee. Have {native_wallet.balance:.6f}, need {native_amount:.6f} to stake."

        # Lock native tokens
        native_wallet.balance -= native_amount

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

        # Commit both DBs together so neither change persists without the other
        county_db.commit()
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
    from counties import CryptoWallet, County, get_db as county_get_db, _apply_gas, GAS_UNITS_MEME_STAKE

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

        # Look up county to compute gas fee
        county = county_db.query(County).filter(County.crypto_symbol == deposit.native_symbol).first()

        # Return native tokens (gas is deducted from the returned amount)
        native_wallet = county_db.query(CryptoWallet).filter(
            CryptoWallet.player_id == player_id,
            CryptoWallet.crypto_symbol == deposit.native_symbol,
        ).first()
        if not native_wallet:
            new_wallet = CryptoWallet(
                player_id=player_id,
                crypto_symbol=deposit.native_symbol,
                balance=0.0,
            )
            county_db.add(new_wallet)
            county_db.flush()
            native_wallet = new_wallet

        return_amount = deposit.quantity
        if county:
            from counties import BASE_GAS_PRICE, GAS_SURGE_MULTIPLIER, MAX_GAS_PRICE
            gas_fee = max(county.gas_price or BASE_GAS_PRICE, BASE_GAS_PRICE) * GAS_UNITS_MEME_STAKE
            return_amount = max(deposit.quantity - gas_fee, 0.0)
            county.mining_energy_pool = (county.mining_energy_pool or 0.0) + gas_fee
            county.gas_price = min(
                max(county.gas_price or BASE_GAS_PRICE, BASE_GAS_PRICE) * (1.0 + GAS_SURGE_MULTIPLIER),
                MAX_GAS_PRICE,
            )
            county.recent_tx_count = (county.recent_tx_count or 0) + 1

        native_wallet.balance += return_amount

        deposit.is_active = False
        db.commit()
        county_db.commit()

        return True, f"Unstaked {deposit.quantity:.6f} {deposit.native_symbol} from {deposit.meme_symbol} mining (received {return_amount:.6f} after gas)."

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

        _all_meme_rewards: list = []  # (player_id, amount, symbol) — logged after commit

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

                # Apply crypto exec bonus (token_strategy, smart_contract_aud, etc.)
                try:
                    from executive import get_player_job_bonus, get_db as exec_get_db
                    _exec_db = exec_get_db()
                    _crypto_bonus = get_player_job_bonus(_exec_db, dep.player_id, "crypto")
                    _exec_db.close()
                    if _crypto_bonus > 0:
                        player_reward = round(player_reward * (1.0 + _crypto_bonus), 8)
                except Exception:
                    pass

                wallet = get_or_create_meme_wallet(db, dep.player_id, meme.symbol)
                wallet.balance += player_reward
                wallet.total_mined += player_reward
                dep.total_earned += player_reward
                _all_meme_rewards.append((dep.player_id, player_reward, meme.symbol))

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

        try:
            from stats_ux import log_transaction as _log
            for _pid, _amt, _sym in _all_meme_rewards:
                _log(
                    _pid, "meme_mining_reward", "crypto", _amt,
                    f"Meme mining reward: {_amt:.6f} {_sym}",
                    item_type=_sym, quantity=_amt,
                )
        except Exception:
            pass

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
    from counties import CryptoWallet, County, get_db as county_get_db, _apply_gas, GAS_UNITS_MEME_TRADE

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

        # --- VWAP deviation guard (limit orders only) ---
        if order_mode == "limit" and price is not None:
            vwap_ref = _compute_24h_vwap(db, meme_symbol)
            if vwap_ref is not None and vwap_ref > 0:
                ratio = price / vwap_ref
                if ratio > PRICE_DEVIATION_MAX_FACTOR or ratio < (1.0 / PRICE_DEVIATION_MAX_FACTOR):
                    return None, (
                        f"Order price {price:.6f} deviates more than {PRICE_DEVIATION_MAX_FACTOR:.0f}× "
                        f"from the 24-hour VWAP ({vwap_ref:.6f}). Adjust your price."
                    )

        county = county_db.query(County).filter(County.id == meme.county_id).first()
        if not county:
            return None, f"County for {meme_symbol} not found — the blockchain may have been removed."
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
                # Gas is charged on top of the order cost
                gas_fee, gas_err = _apply_gas(county, native_wallet, GAS_UNITS_MEME_TRADE)
                if gas_err:
                    return None, gas_err
                if native_balance - gas_fee < cost:
                    county_db.rollback()
                    db.rollback()
                    return None, (
                        f"Insufficient {native_symbol}. Need {cost:.6f} + {gas_fee:.6f} gas = {cost + gas_fee:.6f}, have {native_balance:.6f}."
                    )
                # Reserve native tokens (gas already deducted by _apply_gas)
                if native_wallet:
                    native_wallet.balance -= cost
                native_reserved = cost
                county_db.commit()
            else:
                # Market buy: charge gas upfront; fills happen at whatever ask prices exist
                gas_fee, gas_err = _apply_gas(county, native_wallet, GAS_UNITS_MEME_TRADE)
                if gas_err:
                    return None, gas_err
                county_db.commit()

        elif order_type == "sell":
            if meme_balance < quantity:
                return None, (
                    f"Insufficient {meme_symbol}. Need {quantity:.6f}, have {meme_balance:.6f}."
                )
            # Gas is paid from native wallet for sell orders
            gas_fee, gas_err = _apply_gas(county, native_wallet, GAS_UNITS_MEME_TRADE)
            if gas_err:
                return None, gas_err
            county_db.commit()
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

        # Ledger entries for every fill this order produced — both sides, after
        # commit so only settled trades are logged. Amounts are in native tokens
        # (category "crypto"), mirroring the mining-reward logging pattern.
        try:
            from stats_ux import log_transaction as _log
            fills = db.query(MemeCoinTrade).filter(
                (MemeCoinTrade.buy_order_id == order.id) |
                (MemeCoinTrade.sell_order_id == order.id)
            ).all()
            for t in fills:
                if t.buyer_id and t.buyer_id > 0:
                    _log(
                        t.buyer_id, "meme_buy", "crypto", -t.native_volume,
                        f"Bought {t.quantity:.6f} {meme_symbol} @ {t.price:.6f} {native_symbol}",
                        reference_id=str(t.id), item_type=meme_symbol,
                        quantity=t.quantity, unit_price=t.price,
                    )
                if t.seller_id and t.seller_id > 0:
                    _log(
                        t.seller_id, "meme_sell", "crypto",
                        t.native_volume - (t.fee_native or 0.0),
                        f"Sold {t.quantity:.6f} {meme_symbol} @ {t.price:.6f} {native_symbol} "
                        f"(fee {t.fee_native or 0.0:.6f} {native_symbol})",
                        reference_id=str(t.id), item_type=meme_symbol,
                        quantity=t.quantity, unit_price=t.price,
                    )
        except Exception:
            pass

        # Track meme buy volume in USD for weekly task progress — AFTER commit so
        # we only record progress for trades that actually settled.
        try:
            from counties import get_crypto_price_by_symbol as _gcps
            from events import record_task_progress as _rtp
            _usd_per_native = _gcps(native_symbol) or 0.0
            if _usd_per_native > 0:
                if order_type == "buy" and order.quantity_filled > 0 and player_id > 0:
                    # Incoming buy filled immediately
                    fills = db.query(MemeCoinTrade).filter(
                        MemeCoinTrade.buy_order_id == order.id
                    ).all()
                    total_native = sum(t.native_volume for t in fills)
                    if total_native > 0:
                        _rtp(player_id, "meme_buy_usd", total_native * _usd_per_native)
                elif order_type == "sell" and order.quantity_filled > 0:
                    # Incoming sell filled resting buy limit orders — credit each buyer
                    fills = db.query(MemeCoinTrade).filter(
                        MemeCoinTrade.sell_order_id == order.id
                    ).all()
                    buyer_totals: dict = {}
                    for t in fills:
                        if t.buyer_id > 0:
                            buyer_totals[t.buyer_id] = buyer_totals.get(t.buyer_id, 0.0) + t.native_volume
                    for bid, tvol in buyer_totals.items():
                        if tvol > 0:
                            _rtp(bid, "meme_buy_usd", tvol * _usd_per_native)
        except Exception:
            pass

        remaining = order.quantity - order.quantity_filled
        if order.status == "filled":
            return order, f"Order fully filled! Traded {order.quantity_filled:.6f} {meme_symbol}."
        elif order.status == "partial":
            return order, f"Order partially filled. {order.quantity_filled:.6f} filled, {remaining:.6f} remaining on the book."
        elif order.status == "cancelled":
            side = "sell" if order_type == "buy" else "buy"
            return order, (
                f"Market order cancelled — no {side} orders exist on the book yet. "
                f"Use a Limit order to post the first listing."
            )
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
        )
        if incoming_order.order_mode == "limit":
            query = query.filter(MemeCoinOrder.price >= incoming_order.price)
        # Sort: best bid first (highest price)
        counterpart_orders = query.order_by(MemeCoinOrder.price.desc(), MemeCoinOrder.created_at.asc()).all()

    incoming_remaining = incoming_order.quantity - incoming_order.quantity_filled

    # Pre-compute reference values used by the per-fill guards below.
    now = datetime.utcnow()
    vwap_ref = _compute_24h_vwap(db, symbol)   # None on a brand-new coin

    for counter in counterpart_orders:
        if incoming_remaining <= 0:
            break

        # ── Guard 1: Self-trade prevention ──────────────────────────────────
        # Reject any fill where the same player sits on both sides of the book.
        if counter.player_id == incoming_order.player_id:
            continue

        # ── Guard 2: Maker-taker delay ───────────────────────────────────────
        # The resting (maker) order must be at least MAKER_MIN_AGE_SECONDS old.
        # This breaks instant round-trip bots that place and immediately fill
        # their own orders (self-trade prevention alone isn't enough for
        # two-account schemes where the accounts were set up in advance).
        maker_age = (now - counter.created_at).total_seconds()
        if maker_age < MAKER_MIN_AGE_SECONDS:
            continue

        counter_remaining = counter.quantity - counter.quantity_filled
        fill_qty = min(incoming_remaining, counter_remaining)
        if fill_qty <= 0:
            continue

        # Trade price = the counter-party's limit price (price improvement for taker)
        trade_price = counter.price if counter.price else meme.last_price
        if trade_price is None or trade_price <= 0:
            continue

        # ── Guard 3: VWAP price-deviation cap ────────────────────────────────
        # When 24-hour trade history exists, refuse fills that are more than
        # PRICE_DEVIATION_MAX_FACTOR× away from the VWAP.  On a brand-new coin
        # with no history vwap_ref is None and this guard is intentionally skipped
        # so the first real trade can establish a price.
        if vwap_ref is not None and vwap_ref > 0:
            ratio = trade_price / vwap_ref
            if ratio > PRICE_DEVIATION_MAX_FACTOR or ratio < (1.0 / PRICE_DEVIATION_MAX_FACTOR):
                continue   # skip this resting order; its price is too far from VWAP

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

        # Keep native_reserved in sync with actual remaining locked funds
        # so cancel_order refunds are always accurate regardless of fill path.
        if counter.order_type == "buy" and counter.order_mode == "limit":
            counter.native_reserved = max(0.0, (counter.native_reserved or 0.0) - fill_qty * trade_price)

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
            # Refund the actual remaining locked amount tracked in native_reserved.
            # For fully-unstarted orders this equals unfilled * order.price.
            # For partially-filled orders native_reserved is decremented per fill
            # so this is always the precise amount still in escrow.
            refund_native = order.native_reserved if order.native_reserved is not None else unfilled * order.price
            county = county_db.query(County).filter(County.id == meme.county_id).first()
            if not county:
                return False, "County for this order's meme coin not found."
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

def get_all_meme_coins_global(sort: str = "volume") -> List[dict]:
    """
    Return all active meme coins across every county.
    Used by the global /memecoins discovery hub.
    sort: 'volume' | 'change' | 'new' | 'holders' | 'market_cap'
    Each record includes county_name and native_symbol for display.
    """
    db = get_db()
    try:
        memes = db.query(MemeCoin).filter(MemeCoin.is_active == True).all()

        from counties import County, get_db as county_get_db
        county_db = county_get_db()
        county_cache: dict = {}
        for c in county_db.query(County).all():
            county_cache[c.id] = c
        county_db.close()

        from auth import Player
        result = []
        for m in memes:
            county = county_cache.get(m.county_id)
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
                "county_name": county.name if county else "Unknown",
                "native_symbol": county.crypto_symbol if county else "???",
                "creator_name": creator.business_name if creator else f"Player {m.creator_id}",
                "total_supply": m.total_supply,
                "minted_supply": m.minted_supply or 0.0,
                "mining_allocation": m.mining_allocation,
                "mining_minted": m.mining_minted or 0.0,
                "mining_pool_native": m.mining_pool_native or 0.0,
                "mining_enabled": m.mining_enabled,
                "last_price": m.last_price or 0.0,
                "all_time_high": m.all_time_high or 0.0,
                "total_volume_native": m.total_volume_native or 0.0,
                "total_trades": m.total_trades or 0,
                "holder_count": holder_count,
                "price_change_24h": change_24h,
                "market_cap_native": (m.last_price or 0.0) * (m.minted_supply or 0.0),
                "created_at": m.created_at,
            })

        if sort == "volume":
            result.sort(key=lambda x: x["total_volume_native"], reverse=True)
        elif sort == "change":
            result.sort(key=lambda x: x["price_change_24h"], reverse=True)
        elif sort == "new":
            result.sort(key=lambda x: x["created_at"], reverse=True)
        elif sort == "holders":
            result.sort(key=lambda x: x["holder_count"], reverse=True)
        elif sort == "market_cap":
            result.sort(key=lambda x: x["market_cap_native"], reverse=True)

        return result
    except Exception as e:
        print(f"[MemeCoin] Error in get_all_meme_coins_global: {e}")
        return []
    finally:
        db.close()


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
            "total_directly_burned": meme.total_directly_burned or 0.0,
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


def get_player_order_history(player_id: int, meme_symbol: str, limit: int = 20) -> List[dict]:
    """Get recent order history (all statuses) for a player on a specific meme coin."""
    db = get_db()
    try:
        orders = db.query(MemeCoinOrder).filter(
            MemeCoinOrder.player_id == player_id,
            MemeCoinOrder.meme_symbol == meme_symbol,
        ).order_by(MemeCoinOrder.created_at.desc()).limit(limit).all()
        return [
            {
                "id": o.id,
                "order_type": o.order_type,
                "order_mode": o.order_mode,
                "price": o.price,
                "quantity": o.quantity,
                "quantity_filled": o.quantity_filled,
                "status": o.status,
                "created_at": o.created_at.isoformat(),
                "filled_at": o.filled_at.isoformat() if o.filled_at else None,
            }
            for o in orders
        ]
    except Exception:
        return []
    finally:
        db.close()


def get_all_player_mining_deposits(player_id: int) -> List[dict]:
    """Get all active mining/staking deposits across all meme coins for a player."""
    db = get_db()
    try:
        deposits = db.query(MemeCoinMiningDeposit).filter(
            MemeCoinMiningDeposit.player_id == player_id,
            MemeCoinMiningDeposit.is_active == True,
        ).all()
        result = []
        for d in deposits:
            meme = db.query(MemeCoin).filter(MemeCoin.symbol == d.meme_symbol).first()
            result.append({
                "id": d.id,
                "meme_symbol": d.meme_symbol,
                "meme_name": meme.name if meme else d.meme_symbol,
                "native_symbol": d.native_symbol,
                "quantity": d.quantity,
                "total_earned": d.total_earned or 0.0,
                "deposited_at": d.deposited_at.isoformat(),
            })
        return result
    except Exception:
        return []
    finally:
        db.close()


def get_all_player_open_orders(player_id: int) -> List[dict]:
    """Get all open orders across all meme coins for a player."""
    db = get_db()
    try:
        orders = db.query(MemeCoinOrder).filter(
            MemeCoinOrder.player_id == player_id,
            MemeCoinOrder.status.in_(["active", "partial"]),
        ).order_by(MemeCoinOrder.created_at.desc()).all()
        return [
            {
                "id": o.id,
                "meme_symbol": o.meme_symbol,
                "order_type": o.order_type,
                "order_mode": o.order_mode,
                "price": o.price,
                "quantity": o.quantity,
                "quantity_filled": o.quantity_filled,
                "status": o.status,
                "created_at": o.created_at.isoformat(),
            }
            for o in orders
        ]
    except Exception:
        return []
    finally:
        db.close()


def get_wallet_portfolio(player_id: int) -> dict:
    """
    Full cross-chain wallet portfolio for a player.
    Returns native holdings, meme holdings with prices/24h change, staking, open orders.
    """
    from counties import CryptoWallet, get_db as county_get_db

    db = get_db()
    county_db = county_get_db()
    try:
        # --- Native token holdings ---
        native_wallets = county_db.query(CryptoWallet).filter(
            CryptoWallet.player_id == player_id,
            CryptoWallet.balance > 0,
        ).all()
        native_holdings = [
            {
                "symbol": w.crypto_symbol,
                "balance": w.balance,
                "total_mined": w.total_mined or 0.0,
            }
            for w in native_wallets
        ]

        # --- Meme coin holdings with price data ---
        meme_wallets = db.query(MemeCoinWallet).filter(
            MemeCoinWallet.player_id == player_id,
            MemeCoinWallet.balance > 0,
        ).all()
        meme_holdings = []
        for w in meme_wallets:
            meme = db.query(MemeCoin).filter(MemeCoin.symbol == w.meme_symbol).first()
            if not meme:
                continue
            price = meme.last_price or 0.0
            change_24h = _get_meme_price_change_24h(db, w.meme_symbol, price) if price > 0 else 0.0
            value_native = w.balance * price
            meme_holdings.append({
                "symbol": w.meme_symbol,
                "name": meme.name,
                "balance": w.balance,
                "last_price": price,
                "change_24h": change_24h,
                "value_native": value_native,
                "native_symbol": meme.county_id,  # resolved below
                "county_id": meme.county_id,
                "logo_svg": meme.logo_svg or "",
                "total_mined": w.total_mined or 0.0,
                "total_bought": w.total_bought or 0.0,
                "total_sold": w.total_sold or 0.0,
            })

        # Resolve native symbols for each meme holding
        from counties import County
        county_cache = {}
        for h in meme_holdings:
            cid = h["county_id"]
            if cid not in county_cache:
                c = county_db.query(County).filter(County.id == cid).first()
                county_cache[cid] = c.crypto_symbol if c else "?"
            h["native_symbol"] = county_cache[cid]

        # --- All active stakes ---
        deposits = db.query(MemeCoinMiningDeposit).filter(
            MemeCoinMiningDeposit.player_id == player_id,
            MemeCoinMiningDeposit.is_active == True,
        ).all()
        stakes = []
        for d in deposits:
            meme = db.query(MemeCoin).filter(MemeCoin.symbol == d.meme_symbol).first()
            stakes.append({
                "id": d.id,
                "meme_symbol": d.meme_symbol,
                "meme_name": meme.name if meme else d.meme_symbol,
                "native_symbol": d.native_symbol,
                "staked_native": d.quantity,
                "total_earned": d.total_earned or 0.0,
                "deposited_at": d.deposited_at.isoformat(),
            })

        # --- All open orders ---
        open_orders = db.query(MemeCoinOrder).filter(
            MemeCoinOrder.player_id == player_id,
            MemeCoinOrder.status.in_(["active", "partial"]),
        ).order_by(MemeCoinOrder.created_at.desc()).all()
        orders_out = [
            {
                "id": o.id,
                "meme_symbol": o.meme_symbol,
                "order_type": o.order_type,
                "order_mode": o.order_mode,
                "price": o.price,
                "quantity": o.quantity,
                "quantity_filled": o.quantity_filled,
                "status": o.status,
            }
            for o in open_orders
        ]

        return {
            "native_holdings": native_holdings,
            "meme_holdings": meme_holdings,
            "stakes": stakes,
            "open_orders": orders_out,
        }
    except Exception:
        return {"native_holdings": [], "meme_holdings": [], "stakes": [], "open_orders": []}
    finally:
        db.close()
        county_db.close()


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


def tick(current_tick: int, now: datetime):
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
    'place_order', 'cancel_order', 'mint_by_burning',
    'get_all_meme_coins', 'get_meme_coin_detail', 'get_meme_candles',
    'get_meme_holders', 'get_player_meme_wallets',
    'get_player_mining_deposits', 'get_player_open_orders',
    'MEME_CREATION_FEE_NATIVE', 'MEME_TRADE_FEE_TOTAL',
]
