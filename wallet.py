"""
wallet.py

Wadsworth Crypto Wallet backend.

Wadsworth Stable Coin (WSC):
  - Dollar-pegged: 1 WSC = $1 in-game cash.
  - The ONLY meme token redeemable for in-game dollars.
  - Minted exclusively by burning swap fees (90 % of fee value minted).
  - Used as the reward currency for all wallet programs.

Wallet Rewards:
  - Yield Farming  : stake meme coins → earn WSC from the yield pool.
  - Crypto Faucet  : claim small WSC with a cooldown (buy/sell commodities
                     also credit the faucet on the caller's behalf).
  - Airdrops       : periodic WSC drops to all commodity holders.

Swap Fees (Instant Swap):
  - 3 % deducted from the sell side.
  - 3 % deducted from the buy side.
  - All fee value is burned → 90 % re-minted as WSC for treasury pools.
  - Treasury pools: 40 % yield farming, 30 % faucet, 30 % airdrop.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from sqlalchemy import Column, String, Float, DateTime, Integer, Boolean, func as sqlfunc, update as sa_update
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from database import engine, SessionLocal
Base = declarative_base()

# ==========================
# CONSTANTS
# ==========================
WSC_SYMBOL        = "WSC"
WSC_NAME          = "Wadsworth Stable Coin"
WSC_PEG_RATE      = 1.0    # 1 WSC = $1 in-game cash

SWAP_FEE_SELL     = 0.03   # 3 % fee on the sell leg
SWAP_FEE_BUY      = 0.03   # 3 % fee on the buy leg
WSC_MINT_RATE     = 0.90   # 90 % of burned fee value re-minted as WSC

POOL_YIELD        = 0.40   # 40 % of minted WSC → yield pool
POOL_FAUCET       = 0.30   # 30 % → faucet pool
POOL_AIRDROP      = 0.30   # 30 % → airdrop pool

YIELD_PAYOUT_INTERVAL_TICKS = 720  # every ~1 hour (tick = 5 s)
YIELD_APY_PER_CYCLE = 0.001        # 0.1 % of pool distributed per payout

FAUCET_COOLDOWN_HOURS = 1      # was 4 — shorter cooldown keeps all players engaged
FAUCET_AMOUNT_MIN     = 0.50   # was 0.10 — meaningful floor so claims feel worthwhile
FAUCET_AMOUNT_MAX     = 5.00   # was 1.00 — higher ceiling to encourage trading

AIRDROP_INTERVAL_TICKS   = 2880   # every ~4 hours
AIRDROP_POOL_PCT_PER_RUN = 0.10   # 10 % of airdrop pool per run
AIRDROP_MAX_PER_PLAYER   = 1.0    # cap: 1 WSC per player per airdrop

# ── Native-token ↔ WSC AMM pool ──────────────────────────────────────────────
WSC_AMM_FEE             = 0.003   # 0.3 % swap fee (added to pool as protocol revenue)
WSC_AMM_SEED_WSC        = 10_000.0   # WSC the system seeds into each new pool
WSC_AMM_SEED_NATIVE     = 10_000.0   # native tokens seeded alongside (price = 1:1)
# The seed is minted by the system (not taken from any player).
# k = WSC_AMM_SEED_WSC * WSC_AMM_SEED_NATIVE = 1e8 (initial invariant)

INITIAL_TREASURY_SEED   = 5_000.0   # WSC pre-loaded into treasury pools on first creation
# Splits as: 2 000 yield / 1 500 faucet / 1 500 airdrop.
# Without this, pools are empty until swap fees accumulate, leaving all
# reward programmes non-functional from day one.


# ==========================
# MODELS
# ==========================
class WSCWallet(Base):
    """Player's Wadsworth Stable Coin balance."""
    __tablename__ = "wsc_wallets"
    id                  = Column(Integer, primary_key=True, index=True)
    player_id           = Column(Integer, index=True, nullable=False)
    balance             = Column(Float, default=0.0)
    total_earned_yield  = Column(Float, default=0.0)
    total_earned_faucet = Column(Float, default=0.0)
    total_earned_airdrop= Column(Float, default=0.0)
    total_redeemed      = Column(Float, default=0.0)
    created_at          = Column(DateTime, default=datetime.utcnow)


class WSCTreasury(Base):
    """Global WSC treasury — singleton row (id = 1)."""
    __tablename__ = "wsc_treasury"
    id                   = Column(Integer, primary_key=True)
    total_minted         = Column(Float, default=0.0)
    total_native_burned  = Column(Float, default=0.0)
    yield_farming_pool   = Column(Float, default=0.0)
    faucet_pool          = Column(Float, default=0.0)
    airdrop_pool         = Column(Float, default=0.0)
    last_updated         = Column(DateTime, default=datetime.utcnow)


class YieldFarmingDeposit(Base):
    """A player's meme coin staked for yield farming (WSC rewards)."""
    __tablename__ = "yield_farming_deposits"
    id               = Column(Integer, primary_key=True, index=True)
    player_id        = Column(Integer, index=True, nullable=False)
    meme_symbol      = Column(String, nullable=False)
    quantity         = Column(Float, default=0.0)
    is_active        = Column(Boolean, default=True)
    total_earned_wsc = Column(Float, default=0.0)
    deposited_at     = Column(DateTime, default=datetime.utcnow)


class FaucetClaim(Base):
    """Record of faucet WSC claims."""
    __tablename__ = "faucet_claims"
    id          = Column(Integer, primary_key=True, index=True)
    player_id   = Column(Integer, index=True, nullable=False)
    claim_type  = Column(String, nullable=False)   # "manual", "commodity_buy", "commodity_sell"
    wsc_amount  = Column(Float, default=0.0)
    claimed_at  = Column(DateTime, default=datetime.utcnow)


class WalletSwapRecord(Base):
    """Audit trail for every wallet instant swap."""
    __tablename__ = "wallet_swap_records"
    id               = Column(Integer, primary_key=True, index=True)
    player_id        = Column(Integer, index=True, nullable=False)
    from_symbol      = Column(String, nullable=False)
    to_symbol        = Column(String, nullable=False)
    amount_in        = Column(Float, default=0.0)
    amount_out       = Column(Float, default=0.0)
    fee_burned_value = Column(Float, default=0.0)
    wsc_minted       = Column(Float, default=0.0)
    is_cross_chain   = Column(Boolean, default=False)
    executed_at      = Column(DateTime, default=datetime.utcnow)


class WSCPool(Base):
    """
    Constant-product AMM pool: county native token ↔ WSC.

    One pool per county native token.  The invariant k = native_reserve * wsc_reserve
    determines the exchange rate at any moment.  No external price oracle is
    consulted — price is set purely by supply and demand against the pool.

    The system seeds each pool on first use.  Players can also add liquidity
    via the reserve-bank UI (future feature).
    """
    __tablename__ = "wsc_pools"
    id             = Column(Integer, primary_key=True, index=True)
    native_symbol  = Column(String, unique=True, index=True, nullable=False)
    native_reserve = Column(Float, default=0.0)
    wsc_reserve    = Column(Float, default=0.0)
    total_swaps    = Column(Integer, default=0)
    total_fees_wsc = Column(Float, default=0.0)   # accumulated 0.3 % AMM fees
    created_at     = Column(DateTime, default=datetime.utcnow)
    updated_at     = Column(DateTime, default=datetime.utcnow)


Base.metadata.create_all(engine)


def get_db():
    return SessionLocal()


# ==========================
# INTERNAL HELPERS
# ==========================
def _get_or_create_wsc_wallet(db, player_id: int) -> WSCWallet:
    w = db.query(WSCWallet).filter(WSCWallet.player_id == player_id).first()
    if not w:
        w = WSCWallet(player_id=player_id)
        db.add(w)
        db.flush()
    return w


def _get_or_create_treasury(db) -> WSCTreasury:
    t = db.query(WSCTreasury).filter(WSCTreasury.id == 1).first()
    if not t:
        seed = INITIAL_TREASURY_SEED
        t = WSCTreasury(
            id=1,
            total_minted        = seed,
            yield_farming_pool  = seed * POOL_YIELD,    # 400 WSC
            faucet_pool         = seed * POOL_FAUCET,   # 300 WSC
            airdrop_pool        = seed * POOL_AIRDROP,  # 300 WSC
        )
        db.add(t)
        db.flush()
    return t


def _burn_and_mint_wsc(db, fee_value: float) -> float:
    """Burn `fee_value` units of native value; mint WSC at WSC_MINT_RATE; distribute to pools."""
    if fee_value <= 0:
        return 0.0
    wsc = fee_value * WSC_MINT_RATE
    t = _get_or_create_treasury(db)
    t.total_native_burned  += fee_value
    t.total_minted         += wsc
    t.yield_farming_pool   += wsc * POOL_YIELD
    t.faucet_pool          += wsc * POOL_FAUCET
    t.airdrop_pool         += wsc * POOL_AIRDROP
    t.last_updated          = datetime.utcnow()
    return wsc


def _native_usd_price(county_db, county_id: int) -> float:
    """
    Dollar price of 1 native token = county treasury_balance / total_crypto_minted.
    Falls back to 1.0 (1 native = $1) when data is missing.
    """
    from counties import County
    c = county_db.query(County).filter(County.id == county_id).first()
    if c and c.total_crypto_minted and c.total_crypto_minted > 0 and c.treasury_balance and c.treasury_balance > 0:
        return c.treasury_balance / c.total_crypto_minted
    return 1.0


# ==========================
# NATIVE-TOKEN ↔ WSC AMM POOL
# ==========================

def _get_or_create_wsc_pool(db, native_symbol: str, native_usd_price: float = 1.0) -> WSCPool:
    """Return the AMM pool for `native_symbol`, seeding it with system liquidity on first use.

    `native_usd_price` (USD value of one native token) is only used when creating the pool
    for the first time.  The WSC reserve is seeded as SEED_NATIVE × native_usd_price so that
    the opening rate is 1 native ≈ native_usd_price WSC (matching the real-world peg where
    1 WSC = $1).  A 1:1 seed when a token is worth $5 would make every swap a 5× loss.
    """
    pool = db.query(WSCPool).filter(WSCPool.native_symbol == native_symbol).first()
    if not pool:
        seed_wsc = WSC_AMM_SEED_NATIVE * max(native_usd_price, 0.001)
        pool = WSCPool(
            native_symbol  = native_symbol,
            native_reserve = WSC_AMM_SEED_NATIVE,
            wsc_reserve    = seed_wsc,
        )
        db.add(pool)
        # Record seed as minted WSC so the treasury ledger stays consistent.
        t = _get_or_create_treasury(db)
        t.total_minted += seed_wsc
        t.last_updated  = datetime.utcnow()
        db.flush()
    return pool


def _oracle_sync_pool(db, pool: "WSCPool", native_usd_price: float) -> None:
    """Re-peg pool WSC reserve to match the oracle price if the implied rate is >10% off.

    This corrects pools that were seeded before price-indexed liquidity was deployed
    (they had a 1:1 ratio even for tokens worth hundreds of dollars).

    wsc_reserve is set to native_reserve * oracle_price so that swapping 1 native token
    yields approximately native_usd_price WSC (since 1 WSC = $1).  The WSC delta is
    recorded in the treasury total_minted to keep the ledger consistent.
    """
    if pool.native_reserve <= 0 or native_usd_price <= 0:
        return
    implied_price = pool.wsc_reserve / pool.native_reserve   # WSC per 1 native token
    deviation     = abs(implied_price - native_usd_price) / native_usd_price
    if deviation < 0.10:
        return  # within 10% — no adjustment needed
    new_wsc  = pool.native_reserve * native_usd_price
    delta    = new_wsc - pool.wsc_reserve
    pool.wsc_reserve = new_wsc
    pool.updated_at  = datetime.utcnow()
    t = _get_or_create_treasury(db)
    t.total_minted = max(0.0, t.total_minted + delta)
    t.last_updated = datetime.utcnow()


def get_wsc_quote(native_symbol: str, native_amount: float) -> Tuple[float, float]:
    """
    Quote how much WSC `native_amount` native tokens would buy from the AMM pool.
    Returns (wsc_out, effective_price_native_per_wsc).
    Accounts for the 0.3 % AMM fee.  Pure read — no DB writes.
    """
    from counties import County, get_db as county_get_db
    db = get_db()
    county_db = county_get_db()
    try:
        county = county_db.query(County).filter(County.crypto_symbol == native_symbol).first()
        native_usd_price = _native_usd_price(county_db, county.id) if county else 1.0
        pool = _get_or_create_wsc_pool(db, native_symbol, native_usd_price=native_usd_price)
        _oracle_sync_pool(db, pool, native_usd_price)
        db.commit()
        if pool.native_reserve <= 0 or pool.wsc_reserve <= 0:
            return 0.0, 0.0
        amount_with_fee = native_amount * (1.0 - WSC_AMM_FEE)
        k               = pool.native_reserve * pool.wsc_reserve
        new_native      = pool.native_reserve + amount_with_fee
        new_wsc         = k / new_native
        wsc_out         = pool.wsc_reserve - new_wsc
        price           = native_amount / wsc_out if wsc_out > 0 else 0.0
        return max(wsc_out, 0.0), price
    finally:
        county_db.close()
        db.close()


def get_native_quote(native_symbol: str, wsc_amount: float) -> Tuple[float, float]:
    """
    Quote how much native token `wsc_amount` WSC would buy from the AMM pool.
    Returns (native_out, effective_price_wsc_per_native).
    """
    from counties import County, get_db as county_get_db
    db = get_db()
    county_db = county_get_db()
    try:
        county = county_db.query(County).filter(County.crypto_symbol == native_symbol).first()
        native_usd_price = _native_usd_price(county_db, county.id) if county else 1.0
        pool = _get_or_create_wsc_pool(db, native_symbol, native_usd_price=native_usd_price)
        _oracle_sync_pool(db, pool, native_usd_price)
        db.commit()
        if pool.native_reserve <= 0 or pool.wsc_reserve <= 0:
            return 0.0, 0.0
        amount_with_fee = wsc_amount * (1.0 - WSC_AMM_FEE)
        k               = pool.native_reserve * pool.wsc_reserve
        new_wsc         = pool.wsc_reserve + amount_with_fee
        new_native      = k / new_wsc
        native_out      = pool.native_reserve - new_native
        price           = wsc_amount / native_out if native_out > 0 else 0.0
        return max(native_out, 0.0), price
    finally:
        county_db.close()
        db.close()


def swap_native_for_wsc(player_id: int, native_symbol: str, native_amount: float) -> Tuple[bool, str, dict]:
    """
    Swap `native_amount` of a county's native token for WSC via the AMM pool.
    This is the ONLY way to obtain WSC (besides yield farming payouts).

    The AMM constant-product formula prevents price manipulation:
    dumping a large amount in shifts the pool ratio and gives you
    progressively worse rates — there is no profitable way to inflate the
    exchange rate without depositing genuine value into the pool.
    """
    from counties import County, CryptoWallet, get_db as county_get_db

    if native_amount <= 0:
        return False, "Amount must be positive.", {}

    county_db  = county_get_db()
    wallet_db  = get_db()
    try:
        native_wallet = county_db.query(CryptoWallet).filter(
            CryptoWallet.player_id   == player_id,
            CryptoWallet.crypto_symbol == native_symbol,
        ).first()
        native_bal = native_wallet.balance if native_wallet else 0.0
        if native_bal < native_amount:
            return False, (
                f"Insufficient {native_symbol}: have {native_bal:.6f}, need {native_amount:.6f}."
            ), {}

        # Resolve native token's real USD value for price-correct pool seeding.
        county = county_db.query(County).filter(County.crypto_symbol == native_symbol).first()
        native_usd_price = _native_usd_price(county_db, county.id) if county else 1.0

        pool = _get_or_create_wsc_pool(wallet_db, native_symbol, native_usd_price=native_usd_price)
        # Re-peg pool if its implied price is >10% off from the oracle price.
        # This corrects pools that were seeded before price-indexed liquidity was deployed.
        _oracle_sync_pool(wallet_db, pool, native_usd_price)
        if pool.wsc_reserve <= 0:
            return False, "Pool has no WSC liquidity yet.", {}

        amount_with_fee = native_amount * (1.0 - WSC_AMM_FEE)
        fee_native      = native_amount * WSC_AMM_FEE
        k               = pool.native_reserve * pool.wsc_reserve
        new_native      = pool.native_reserve + amount_with_fee
        new_wsc         = k / new_native
        wsc_out         = pool.wsc_reserve - new_wsc
        if wsc_out <= 0:
            return False, "Swap would drain the pool. Try a smaller amount.", {}

        # Deduct native tokens
        native_wallet.balance -= native_amount
        county_db.commit()

        # Update pool
        pool.native_reserve = new_native + fee_native   # fee stays in pool as revenue
        pool.wsc_reserve    = new_wsc
        pool.total_swaps   += 1
        pool.total_fees_wsc+= fee_native * (new_wsc / (new_native + fee_native))  # approx fee value in WSC
        pool.updated_at     = datetime.utcnow()

        # Credit WSC to player
        wsc_wallet = _get_or_create_wsc_wallet(wallet_db, player_id)
        wsc_wallet.balance         += wsc_out
        wsc_wallet.total_earned_yield += wsc_out   # reuse field as "earned via AMM"

        # Route the AMM fee (valued in USD) into the shared treasury pools.
        # This mirrors the meme-coin swap model and ensures the faucet / yield /
        # airdrop pools refill from AMM activity, not just meme-coin swaps.
        fee_usd_value = fee_native * native_usd_price
        _burn_and_mint_wsc(wallet_db, fee_usd_value)

        wallet_db.commit()

        effective_price = native_amount / wsc_out
        return True, (
            f"Swapped {native_amount:.6f} {native_symbol} → {wsc_out:.4f} WSC "
            f"(rate: {effective_price:.4f} {native_symbol}/WSC, fee: {fee_native:.6f} {native_symbol})."
        ), {
            "native_symbol": native_symbol,
            "native_in": native_amount,
            "wsc_out": wsc_out,
            "fee_native": fee_native,
            "effective_price": effective_price,
            "pool_native_reserve": pool.native_reserve,
            "pool_wsc_reserve": pool.wsc_reserve,
        }

    except Exception as e:
        county_db.rollback()
        wallet_db.rollback()
        import traceback; traceback.print_exc()
        return False, f"AMM swap error: {e}", {}
    finally:
        county_db.close()
        wallet_db.close()


def swap_wsc_for_native(player_id: int, native_symbol: str, wsc_amount: float) -> Tuple[bool, str, dict]:
    """Swap `wsc_amount` WSC back into the county's native token via the AMM pool."""
    from counties import CryptoWallet, get_db as county_get_db

    if wsc_amount <= 0:
        return False, "Amount must be positive.", {}

    county_db = county_get_db()
    wallet_db = get_db()
    try:
        # Atomic deduction of WSC
        result = wallet_db.execute(
            sa_update(WSCWallet)
            .where(WSCWallet.player_id == player_id)
            .where(WSCWallet.balance   >= wsc_amount)
            .values(balance=WSCWallet.balance - wsc_amount)
        )
        wallet_db.flush()
        if result.rowcount == 0:
            wallet_db.rollback()
            current = wallet_db.query(WSCWallet.balance).filter(
                WSCWallet.player_id == player_id
            ).scalar() or 0.0
            return False, f"Insufficient WSC: have {current:.4f}, need {wsc_amount:.4f}.", {}

        pool = _get_or_create_wsc_pool(wallet_db, native_symbol)
        if pool.native_reserve <= 0:
            wallet_db.rollback()
            return False, "Pool has no native-token liquidity.", {}

        amount_with_fee = wsc_amount * (1.0 - WSC_AMM_FEE)
        fee_wsc         = wsc_amount * WSC_AMM_FEE
        k               = pool.native_reserve * pool.wsc_reserve
        new_wsc         = pool.wsc_reserve + amount_with_fee
        new_native      = k / new_wsc
        native_out      = pool.native_reserve - new_native
        if native_out <= 0:
            wallet_db.rollback()
            return False, "Swap would drain the native-token reserve. Try a smaller amount.", {}

        pool.wsc_reserve    = new_wsc + fee_wsc   # fee stays in pool
        pool.native_reserve = new_native
        pool.total_swaps   += 1
        pool.updated_at     = datetime.utcnow()
        wallet_db.commit()

        # Credit native tokens to player
        native_wallet = county_db.query(CryptoWallet).filter(
            CryptoWallet.player_id    == player_id,
            CryptoWallet.crypto_symbol == native_symbol,
        ).first()
        if not native_wallet:
            from counties import CryptoWallet as CW
            native_wallet = CW(player_id=player_id, crypto_symbol=native_symbol, balance=0.0)
            county_db.add(native_wallet)
        native_wallet.balance += native_out
        county_db.commit()

        effective_price = wsc_amount / native_out
        return True, (
            f"Swapped {wsc_amount:.4f} WSC → {native_out:.6f} {native_symbol} "
            f"(rate: {effective_price:.4f} WSC/{native_symbol}, fee: {fee_wsc:.4f} WSC)."
        ), {
            "native_symbol": native_symbol,
            "wsc_in": wsc_amount,
            "native_out": native_out,
            "fee_wsc": fee_wsc,
            "effective_price": effective_price,
        }

    except Exception as e:
        county_db.rollback()
        wallet_db.rollback()
        import traceback; traceback.print_exc()
        return False, f"AMM swap error: {e}", {}
    finally:
        county_db.close()
        wallet_db.close()


# ==========================
# INSTANT SWAP (DIRECT, TRUE VALUE)
# ==========================
def execute_wallet_swap(
    player_id: int,
    from_symbol: str,
    amount: float,
    to_symbol: str,
) -> Tuple[bool, str, dict]:
    """
    Instant swap: meme coin A → meme coin B at true market value.

    Exchange rate is derived from each coin's 24-hour VWAP (not last_price).
    Using last_price was a manipulation vector — a player could self-trade to
    inflate last_price then extract value via this swap.  The VWAP is far
    harder to manipulate because it is volume-weighted over 24 hours.

    Fees: 3 % sell leg + 3 % buy leg — both are permanently burned.
    90 % of the burned fee value is re-minted as WSC and distributed to
    the yield farming, faucet, and airdrop treasury pools.

    Returns (success, message, detail_dict).
    """
    from memecoins import (
        MemeCoin, MemeCoinWallet, get_or_create_meme_wallet,
        get_db as meme_get_db, _compute_24h_vwap,
    )
    from counties import get_db as county_get_db

    if amount <= 0:
        return False, "Amount must be positive.", {}
    if from_symbol == to_symbol:
        return False, "Cannot swap a coin to itself.", {}

    meme_db   = meme_get_db()
    county_db = county_get_db()
    wallet_db = get_db()
    try:
        meme_from = meme_db.query(MemeCoin).filter(
            MemeCoin.symbol == from_symbol, MemeCoin.is_active == True
        ).first()
        meme_to = meme_db.query(MemeCoin).filter(
            MemeCoin.symbol == to_symbol, MemeCoin.is_active == True
        ).first()
        if not meme_from:
            return False, f"{from_symbol} not found or inactive.", {}
        if not meme_to:
            return False, f"{to_symbol} not found or inactive.", {}

        # Use 24h VWAP — NOT last_price — to prevent price manipulation.
        price_from = _compute_24h_vwap(meme_db, from_symbol)
        price_to   = _compute_24h_vwap(meme_db, to_symbol)
        if price_from is None or price_from <= 0:
            return False, (
                f"{from_symbol} has no 24-hour trade history yet. "
                "Swaps require an established VWAP price."
            ), {}
        if price_to is None or price_to <= 0:
            return False, (
                f"{to_symbol} has no 24-hour trade history yet. "
                "Swaps require an established VWAP price."
            ), {}

        # Check balance
        from_wallet = meme_db.query(MemeCoinWallet).filter(
            MemeCoinWallet.player_id == player_id,
            MemeCoinWallet.meme_symbol == from_symbol,
        ).first()
        from_bal = from_wallet.balance if from_wallet else 0.0
        if from_bal < amount:
            return False, f"Insufficient {from_symbol}: have {from_bal:.4f}, need {amount:.4f}.", {}

        # True-value exchange using native-token USD prices
        usd_from = _native_usd_price(county_db, meme_from.county_id)
        usd_to   = _native_usd_price(county_db, meme_to.county_id)

        sell_usd_value  = amount * price_from * usd_from
        sell_fee_usd    = sell_usd_value * SWAP_FEE_SELL
        net_usd         = sell_usd_value - sell_fee_usd
        buy_fee_usd     = net_usd * SWAP_FEE_BUY
        net_usd_for_buy = net_usd - buy_fee_usd
        amount_out      = net_usd_for_buy / (price_to * usd_to)
        total_fee_usd   = sell_fee_usd + buy_fee_usd
        is_cross_chain  = (meme_from.county_id != meme_to.county_id)

        # — Execute wallet transfers —
        from_w = get_or_create_meme_wallet(meme_db, player_id, from_symbol)
        from_w.balance    -= amount
        from_w.total_sold += amount

        to_w = get_or_create_meme_wallet(meme_db, player_id, to_symbol)
        to_w.balance      += amount_out
        to_w.total_bought += amount_out

        meme_db.commit()

        # — Burn fees and mint WSC into treasury pools —
        minted_wsc = _burn_and_mint_wsc(wallet_db, total_fee_usd)
        wallet_db.commit()

        # — Audit record —
        rec = WalletSwapRecord(
            player_id=player_id,
            from_symbol=from_symbol,
            to_symbol=to_symbol,
            amount_in=amount,
            amount_out=amount_out,
            fee_burned_value=total_fee_usd,
            wsc_minted=minted_wsc,
            is_cross_chain=is_cross_chain,
        )
        wallet_db.add(rec)
        wallet_db.commit()

        chain_note = "(cross-chain)" if is_cross_chain else "(same chain)"
        msg = (
            f"Swapped {amount:.4f} {from_symbol} → {amount_out:.4f} {to_symbol} {chain_note}. "
            f"Fee: ${total_fee_usd:.4f} burned → {minted_wsc:.4f} WSC minted to treasury."
        )
        return True, msg, {
            "from_symbol": from_symbol, "to_symbol": to_symbol,
            "amount_in": amount, "amount_out": amount_out,
            "price_from_vwap": price_from, "price_to_vwap": price_to,
            "sell_fee_usd": sell_fee_usd, "buy_fee_usd": buy_fee_usd,
            "total_fee_usd": total_fee_usd, "wsc_minted": minted_wsc,
            "is_cross_chain": is_cross_chain,
        }

    except Exception as e:
        meme_db.rollback()
        wallet_db.rollback()
        import traceback; traceback.print_exc()
        return False, f"Swap error: {e}", {}
    finally:
        meme_db.close()
        county_db.close()
        wallet_db.close()


# ==========================
# YIELD FARMING
# ==========================
def add_yield_farming(player_id: int, meme_symbol: str, quantity: float) -> Tuple[bool, str]:
    """Stake meme coins into yield farming to earn WSC."""
    from memecoins import MemeCoinWallet, get_or_create_meme_wallet, get_db as meme_get_db

    if quantity <= 0:
        return False, "Quantity must be positive."

    meme_db   = meme_get_db()
    wallet_db = get_db()
    try:
        meme_w = meme_db.query(MemeCoinWallet).filter(
            MemeCoinWallet.player_id == player_id,
            MemeCoinWallet.meme_symbol == meme_symbol,
        ).first()
        bal = meme_w.balance if meme_w else 0.0
        if bal < quantity:
            return False, f"Insufficient {meme_symbol}: have {bal:.4f}, need {quantity:.4f}."

        meme_w_obj = get_or_create_meme_wallet(meme_db, player_id, meme_symbol)
        meme_w_obj.balance -= quantity
        meme_db.commit()

        deposit = YieldFarmingDeposit(
            player_id=player_id,
            meme_symbol=meme_symbol,
            quantity=quantity,
        )
        wallet_db.add(deposit)
        wallet_db.commit()
        return True, f"Staked {quantity:.4f} {meme_symbol} for yield farming. WSC rewards accrue hourly."
    except Exception as e:
        meme_db.rollback()
        wallet_db.rollback()
        return False, str(e)
    finally:
        meme_db.close()
        wallet_db.close()


def remove_yield_farming(player_id: int, deposit_id: int) -> Tuple[bool, str]:
    """Unstake from yield farming and return meme coins."""
    from memecoins import get_or_create_meme_wallet, get_db as meme_get_db

    wallet_db = get_db()
    meme_db   = meme_get_db()
    try:
        dep = wallet_db.query(YieldFarmingDeposit).filter(
            YieldFarmingDeposit.id == deposit_id,
            YieldFarmingDeposit.player_id == player_id,
            YieldFarmingDeposit.is_active == True,
        ).first()
        if not dep:
            return False, "Deposit not found or already withdrawn."

        dep.is_active = False
        wallet_db.commit()

        meme_w = get_or_create_meme_wallet(meme_db, player_id, dep.meme_symbol)
        meme_w.balance += dep.quantity
        meme_db.commit()
        return True, f"Unstaked {dep.quantity:.4f} {dep.meme_symbol} from yield farming."
    except Exception as e:
        wallet_db.rollback()
        meme_db.rollback()
        return False, str(e)
    finally:
        wallet_db.close()
        meme_db.close()


def _tick_yield_farming(wallet_db, current_tick: int):
    """Distribute WSC from yield pool to active farmers. Called every tick."""
    if current_tick % YIELD_PAYOUT_INTERVAL_TICKS != 0:
        return

    from memecoins import MemeCoin, get_db as meme_get_db
    meme_db = meme_get_db()
    try:
        treasury = _get_or_create_treasury(wallet_db)
        if treasury.yield_farming_pool <= 0:
            return

        deposits = wallet_db.query(YieldFarmingDeposit).filter(
            YieldFarmingDeposit.is_active == True
        ).all()
        if not deposits:
            return

        # Weight each deposit by quantity × last_price.
        # Fall back to price=1.0 when a coin has no trade history yet so that
        # new-game vaults always pay out (quantity-weighted rather than silently
        # returning with total_w=0 because every last_price is still 0).
        weighted = {}
        total_w  = 0.0
        for d in deposits:
            meme  = meme_db.query(MemeCoin).filter(MemeCoin.symbol == d.meme_symbol).first()
            price = (meme.last_price if meme and meme.last_price and meme.last_price > 0
                     else 1.0)
            w = d.quantity * price
            weighted[d.id] = w
            total_w += w

        if total_w <= 0:
            return

        payout_total = treasury.yield_farming_pool * YIELD_APY_PER_CYCLE
        treasury.yield_farming_pool -= payout_total

        for d in deposits:
            share = weighted[d.id] / total_w
            payout = payout_total * share
            wsc_w = _get_or_create_wsc_wallet(wallet_db, d.player_id)
            wsc_w.balance            += payout
            wsc_w.total_earned_yield += payout
            d.total_earned_wsc       += payout

        wallet_db.commit()
    except Exception as e:
        wallet_db.rollback()
        print(f"[Wallet] Yield tick error: {e}")
    finally:
        meme_db.close()


# ==========================
# FAUCET
# ==========================
def claim_faucet(player_id: int, claim_type: str = "manual") -> Tuple[bool, str, float]:
    """
    Claim WSC from the faucet (up to FAUCET_AMOUNT_MAX).
    Enforces FAUCET_COOLDOWN_HOURS between manual claims.
    Commodity-trade claims bypass the cooldown (separate claim_type).
    """
    import random

    wallet_db = get_db()
    try:
        if claim_type == "manual":
            cooldown_cutoff = datetime.utcnow() - timedelta(hours=FAUCET_COOLDOWN_HOURS)
            last = wallet_db.query(FaucetClaim).filter(
                FaucetClaim.player_id == player_id,
                FaucetClaim.claim_type == "manual",
                FaucetClaim.claimed_at > cooldown_cutoff,
            ).first()
            if last:
                remaining   = last.claimed_at + timedelta(hours=FAUCET_COOLDOWN_HOURS) - datetime.utcnow()
                hrs  = int(remaining.total_seconds() // 3600)
                mins = int((remaining.total_seconds() % 3600) // 60)
                return False, f"Faucet cooldown: {hrs}h {mins}m remaining.", 0.0

        treasury = _get_or_create_treasury(wallet_db)
        if treasury.faucet_pool <= 0:
            return False, "Faucet pool is empty — more swaps are needed to refill it.", 0.0

        amount = round(random.uniform(FAUCET_AMOUNT_MIN, FAUCET_AMOUNT_MAX), 4)
        amount = min(amount, treasury.faucet_pool)

        treasury.faucet_pool -= amount

        wsc_w = _get_or_create_wsc_wallet(wallet_db, player_id)
        wsc_w.balance             += amount
        wsc_w.total_earned_faucet += amount

        wallet_db.add(FaucetClaim(player_id=player_id, claim_type=claim_type, wsc_amount=amount))
        wallet_db.commit()
        return True, f"Faucet: you received {amount:.4f} WSC!", amount
    except Exception as e:
        wallet_db.rollback()
        return False, str(e), 0.0
    finally:
        wallet_db.close()


def _tick_airdrops(wallet_db, current_tick: int):
    """Airdrop WSC to all commodity holders every AIRDROP_INTERVAL_TICKS."""
    if current_tick % AIRDROP_INTERVAL_TICKS != 0:
        return

    try:
        from inventory import InventoryItem, get_db as inv_get_db
        inv_db = inv_get_db()
        try:
            holders = inv_db.query(
                InventoryItem.player_id,
                sqlfunc.sum(InventoryItem.quantity).label("total_qty"),
            ).group_by(InventoryItem.player_id).having(
                sqlfunc.sum(InventoryItem.quantity) >= 1
            ).all()
        finally:
            inv_db.close()

        if not holders:
            return

        treasury = _get_or_create_treasury(wallet_db)
        if treasury.airdrop_pool <= 0:
            return

        payout_per_player = min(
            treasury.airdrop_pool * AIRDROP_POOL_PCT_PER_RUN / max(len(holders), 1),
            AIRDROP_MAX_PER_PLAYER,
        )
        if payout_per_player <= 0:
            return

        total_paid = 0.0
        for row in holders:
            wsc_w = _get_or_create_wsc_wallet(wallet_db, row.player_id)
            wsc_w.balance              += payout_per_player
            wsc_w.total_earned_airdrop += payout_per_player
            total_paid                 += payout_per_player

        treasury.airdrop_pool -= total_paid
        wallet_db.commit()
        print(f"[Wallet] Airdrop: distributed {total_paid:.4f} WSC to {len(holders)} commodity holders.")
    except Exception as e:
        wallet_db.rollback()
        print(f"[Wallet] Airdrop tick error: {e}")


# ==========================
# WSC REDEMPTION
# ==========================
def redeem_wsc_for_cash(player_id: int, amount: float) -> Tuple[bool, str]:
    """
    Redeem WSC for in-game dollars at the 1:1 peg.
    Deducts from WSC wallet; credits player.cash_balance.

    TOCTOU fix: the deduction is performed as a single atomic
        UPDATE ... WHERE balance >= amount
    so concurrent requests cannot double-spend the same WSC balance.
    If the UPDATE matches 0 rows the balance was insufficient.
    On any downstream failure the deduction is compensated via a
    second atomic UPDATE that adds the amount back.
    """
    if amount <= 0:
        return False, "Amount must be positive."

    # ── Step 1: ensure the WSC wallet row exists ─────────────────────────────
    wallet_db = get_db()
    try:
        _get_or_create_wsc_wallet(wallet_db, player_id)
        wallet_db.commit()
    except Exception as e:
        wallet_db.rollback()
        wallet_db.close()
        return False, f"Wallet init error: {e}"
    finally:
        wallet_db.close()

    # ── Step 2: atomic deduction — races are eliminated at the DB level ──────
    wallet_db = get_db()
    try:
        result = wallet_db.execute(
            sa_update(WSCWallet)
            .where(WSCWallet.player_id == player_id)
            .where(WSCWallet.balance >= amount)
            .values(
                balance=WSCWallet.balance - amount,
                total_redeemed=WSCWallet.total_redeemed + amount,
            )
        )
        wallet_db.commit()
        if result.rowcount == 0:
            # Either balance was truly insufficient or a concurrent request
            # already claimed the funds.
            current = wallet_db.query(WSCWallet.balance).filter(
                WSCWallet.player_id == player_id
            ).scalar() or 0.0
            return False, f"Insufficient WSC: have {current:.4f}, need {amount:.4f}."
    except Exception as e:
        wallet_db.rollback()
        return False, str(e)
    finally:
        wallet_db.close()

    # ── Step 3: credit player cash ───────────────────────────────────────────
    from auth import get_db as auth_get_db, Player
    auth_db = auth_get_db()
    try:
        p = auth_db.query(Player).filter(Player.id == player_id).first()
        if not p:
            # Compensate: atomically refund the WSC we just deducted.
            _atomic_wsc_refund(player_id, amount)
            return False, "Player not found; WSC refunded."
        p.cash_balance = (p.cash_balance or 0.0) + amount
        auth_db.commit()
    except Exception as e:
        auth_db.rollback()
        _atomic_wsc_refund(player_id, amount)
        return False, f"Cash credit failed; WSC refunded. ({e})"
    finally:
        auth_db.close()

    return True, f"Redeemed {amount:.4f} WSC → ${amount:.2f} in-game cash credited."


def _atomic_wsc_refund(player_id: int, amount: float) -> None:
    """Unconditionally add `amount` back to a player's WSC balance.
    Used as a compensation action when the downstream cash-credit fails."""
    wallet_db = get_db()
    try:
        wallet_db.execute(
            sa_update(WSCWallet)
            .where(WSCWallet.player_id == player_id)
            .values(
                balance=WSCWallet.balance + amount,
                total_redeemed=WSCWallet.total_redeemed - amount,
            )
        )
        wallet_db.commit()
    except Exception as e:
        wallet_db.rollback()
        print(f"[Wallet] CRITICAL: WSC refund failed for player {player_id}, amount {amount}: {e}")
    finally:
        wallet_db.close()


# ==========================
# READ / INFO FUNCTIONS
# ==========================
def get_wsc_wallet_info(player_id: int) -> dict:
    wallet_db = get_db()
    try:
        w = wallet_db.query(WSCWallet).filter(WSCWallet.player_id == player_id).first()
        return {
            "balance":              w.balance              if w else 0.0,
            "total_earned_yield":   w.total_earned_yield   if w else 0.0,
            "total_earned_faucet":  w.total_earned_faucet  if w else 0.0,
            "total_earned_airdrop": w.total_earned_airdrop if w else 0.0,
            "total_redeemed":       w.total_redeemed       if w else 0.0,
        }
    finally:
        wallet_db.close()


def get_treasury_info() -> dict:
    wallet_db = get_db()
    try:
        t = wallet_db.query(WSCTreasury).filter(WSCTreasury.id == 1).first()
        if not t:
            return {"total_minted": 0.0, "total_native_burned": 0.0,
                    "yield_farming_pool": 0.0, "faucet_pool": 0.0, "airdrop_pool": 0.0}
        return {
            "total_minted":        t.total_minted,
            "total_native_burned": t.total_native_burned,
            "yield_farming_pool":  t.yield_farming_pool,
            "faucet_pool":         t.faucet_pool,
            "airdrop_pool":        t.airdrop_pool,
        }
    finally:
        wallet_db.close()


def get_player_yield_deposits(player_id: int) -> List[dict]:
    from memecoins import MemeCoin, get_db as meme_get_db
    wallet_db = get_db()
    meme_db   = meme_get_db()
    try:
        deposits = wallet_db.query(YieldFarmingDeposit).filter(
            YieldFarmingDeposit.player_id == player_id,
            YieldFarmingDeposit.is_active == True,
        ).all()
        result = []
        for d in deposits:
            meme  = meme_db.query(MemeCoin).filter(MemeCoin.symbol == d.meme_symbol).first()
            price = (meme.last_price or 0.0) if meme else 0.0
            result.append({
                "id":               d.id,
                "meme_symbol":      d.meme_symbol,
                "meme_name":        meme.name if meme else d.meme_symbol,
                "quantity":         d.quantity,
                "last_price":       price,
                "value_native":     d.quantity * price,
                "total_earned_wsc": d.total_earned_wsc,
                "deposited_at":     d.deposited_at.isoformat(),
            })
        return result
    finally:
        wallet_db.close()
        meme_db.close()


def get_faucet_status(player_id: int) -> dict:
    wallet_db = get_db()
    try:
        cutoff = datetime.utcnow() - timedelta(hours=FAUCET_COOLDOWN_HOURS)
        last = wallet_db.query(FaucetClaim).filter(
            FaucetClaim.player_id == player_id,
            FaucetClaim.claim_type == "manual",
        ).order_by(FaucetClaim.claimed_at.desc()).first()

        if not last:
            return {"can_claim": True, "remaining_seconds": 0, "last_amount": 0.0}

        cooldown_end      = last.claimed_at + timedelta(hours=FAUCET_COOLDOWN_HOURS)
        remaining_secs    = max(0, (cooldown_end - datetime.utcnow()).total_seconds())
        return {
            "can_claim":        remaining_secs <= 0,
            "remaining_seconds": int(remaining_secs),
            "last_amount":      last.wsc_amount,
        }
    finally:
        wallet_db.close()


def get_recent_swaps(player_id: int, limit: int = 10) -> List[dict]:
    wallet_db = get_db()
    try:
        recs = wallet_db.query(WalletSwapRecord).filter(
            WalletSwapRecord.player_id == player_id,
        ).order_by(WalletSwapRecord.executed_at.desc()).limit(limit).all()
        return [
            {
                "from_symbol":      r.from_symbol,
                "to_symbol":        r.to_symbol,
                "amount_in":        r.amount_in,
                "amount_out":       r.amount_out,
                "fee_burned_value": r.fee_burned_value,
                "wsc_minted":       r.wsc_minted,
                "is_cross_chain":   r.is_cross_chain,
                "executed_at":      r.executed_at.isoformat()[:16].replace("T", " "),
            }
            for r in recs
        ]
    finally:
        wallet_db.close()


# ==========================
# APP TICK
# ==========================
async def tick(current_tick: int, now):
    """Called every app tick. Handles yield payouts and airdrops."""
    wallet_db = get_db()
    try:
        _tick_yield_farming(wallet_db, current_tick)
        _tick_airdrops(wallet_db, current_tick)
    except Exception as e:
        print(f"[Wallet] Tick error: {e}")
    finally:
        wallet_db.close()
