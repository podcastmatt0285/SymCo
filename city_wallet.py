"""
city_wallet.py

City Stable Coin (CCC) wallet backend.

Mirrors wallet.py but scoped to each city's comptroller-issued stable coin.

For every city that has an active comptroller (CityBank.stable_coin_symbol is set)
there is a self-contained token economy:

  AMM Pool   : WSC ↔ CCC constant-product pool at the live forex rate.
               Swapping WSC in mints CCC; swapping CCC in redeems back to WSC.
  Treasury   : per-city pool with yield_pool, faucet_pool, airdrop_pool.
               Funded by 90 % of AMM fee value, split 40 / 30 / 30.
  Yield Farm : stake meme coins → earn CCC hourly from the yield pool.
  Faucet     : city members claim CCC (0.50–5.00) with a 1 h cooldown.
  Airdrops   : periodic CCC drops to all city members every ~4 h.

Redemption (CCC → in-game cash) is handled by cities.redeem_stable_coins().
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple, List

from sqlalchemy import Column, String, Float, DateTime, Integer, Boolean, update as sa_update, func as sqlfunc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from database import engine, SessionLocal

Base = declarative_base()

# ──────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ──────────────────────────────────────────────────────────────────────────────
CCC_AMM_FEE              = 0.003   # 0.3 % swap fee — stays in pool + seeds treasury
CCC_MINT_RATE            = 0.90    # 90 % of fee → new CCC minted into treasury
CCC_POOL_YIELD           = 0.40
CCC_POOL_FAUCET          = 0.30
CCC_POOL_AIRDROP         = 0.30

CCC_AMM_SEED_CCC         = 10_000.0   # CCC seeded into each new pool
# WSC seed = CCC_AMM_SEED_CCC * usd_per_coin  (set when pool is created)

CCC_INITIAL_TREASURY_SEED = 500.0   # CCC pre-loaded into a new treasury
# split: 200 yield / 150 faucet / 150 airdrop

CCC_YIELD_PAYOUT_TICKS   = 720     # ~1 h at 5 s/tick
CCC_YIELD_APY_PER_CYCLE  = 0.001   # 0.1 % of yield pool per payout

CCC_FAUCET_COOLDOWN_HOURS = 1
CCC_FAUCET_AMOUNT_MIN     = 0.50
CCC_FAUCET_AMOUNT_MAX     = 5.00

CCC_AIRDROP_INTERVAL_TICKS   = 2880    # ~4 h
CCC_AIRDROP_POOL_PCT_PER_RUN = 0.10
CCC_AIRDROP_MAX_PER_MEMBER   = 1.0


# ──────────────────────────────────────────────────────────────────────────────
# MODELS
# ──────────────────────────────────────────────────────────────────────────────

class CityWalletTreasury(Base):
    """Per-city treasury backing the CCC reward pools."""
    __tablename__ = "city_wallet_treasuries"
    id            = Column(Integer, primary_key=True, index=True)
    city_id       = Column(Integer, unique=True, index=True, nullable=False)
    total_minted  = Column(Float, default=0.0)
    total_burned  = Column(Float, default=0.0)   # WSC burned via AMM fees
    yield_pool    = Column(Float, default=0.0)
    faucet_pool   = Column(Float, default=0.0)
    airdrop_pool  = Column(Float, default=0.0)
    last_updated  = Column(DateTime, default=datetime.utcnow)


class CityAMMPool(Base):
    """
    Constant-product WSC ↔ CCC pool for a single city.
    Invariant: wsc_reserve * ccc_reserve = k
    """
    __tablename__ = "city_amm_pools"
    id            = Column(Integer, primary_key=True, index=True)
    city_id       = Column(Integer, unique=True, index=True, nullable=False)
    wsc_reserve   = Column(Float, default=0.0)
    ccc_reserve   = Column(Float, default=0.0)
    total_swaps   = Column(Integer, default=0)
    total_fees_wsc= Column(Float, default=0.0)
    created_at    = Column(DateTime, default=datetime.utcnow)
    updated_at    = Column(DateTime, default=datetime.utcnow)


class CityYieldDeposit(Base):
    """A player's meme coin staked to earn a specific city's CCC."""
    __tablename__ = "city_yield_deposits"
    id              = Column(Integer, primary_key=True, index=True)
    city_id         = Column(Integer, index=True, nullable=False)
    player_id       = Column(Integer, index=True, nullable=False)
    meme_symbol     = Column(String, nullable=False)
    quantity        = Column(Float, default=0.0)
    is_active       = Column(Boolean, default=True)
    total_earned    = Column(Float, default=0.0)
    deposited_at    = Column(DateTime, default=datetime.utcnow)


class CityFaucetClaim(Base):
    """Record of per-city CCC faucet claims."""
    __tablename__ = "city_faucet_claims"
    id          = Column(Integer, primary_key=True, index=True)
    city_id     = Column(Integer, index=True, nullable=False)
    player_id   = Column(Integer, index=True, nullable=False)
    amount      = Column(Float, default=0.0)
    claimed_at  = Column(DateTime, default=datetime.utcnow)


Base.metadata.create_all(engine)


def get_db():
    return SessionLocal()


# ──────────────────────────────────────────────────────────────────────────────
# INTERNAL HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def _get_or_create_treasury(db, city_id: int) -> CityWalletTreasury:
    t = db.query(CityWalletTreasury).filter(
        CityWalletTreasury.city_id == city_id
    ).first()
    if not t:
        seed = CCC_INITIAL_TREASURY_SEED
        t = CityWalletTreasury(
            city_id      = city_id,
            total_minted = seed,
            yield_pool   = seed * CCC_POOL_YIELD,
            faucet_pool  = seed * CCC_POOL_FAUCET,
            airdrop_pool = seed * CCC_POOL_AIRDROP,
        )
        db.add(t)
        db.flush()
    return t


def _credit_pools(db, city_id: int, fee_usd_value: float) -> float:
    """Burn `fee_usd_value` USD-worth; mint CCC at CCC_MINT_RATE; add to pools."""
    if fee_usd_value <= 0:
        return 0.0
    minted = fee_usd_value * CCC_MINT_RATE
    t = _get_or_create_treasury(db, city_id)
    t.total_burned  += fee_usd_value
    t.total_minted  += minted
    t.yield_pool    += minted * CCC_POOL_YIELD
    t.faucet_pool   += minted * CCC_POOL_FAUCET
    t.airdrop_pool  += minted * CCC_POOL_AIRDROP
    t.last_updated   = datetime.utcnow()
    return minted


def _get_or_create_amm_pool(db, city_id: int, usd_per_coin: float = 1.0) -> CityAMMPool:
    """Return the AMM pool for a city, seeding it on first use."""
    pool = db.query(CityAMMPool).filter(CityAMMPool.city_id == city_id).first()
    if not pool:
        # Seed so that 1 CCC ≈ usd_per_coin WSC at opening
        seed_wsc = CCC_AMM_SEED_CCC * max(usd_per_coin, 1e-9)
        pool = CityAMMPool(
            city_id     = city_id,
            ccc_reserve = CCC_AMM_SEED_CCC,
            wsc_reserve = seed_wsc,
        )
        db.add(pool)
        # Record the seeded CCC in the treasury ledger
        t = _get_or_create_treasury(db, city_id)
        t.total_minted += CCC_AMM_SEED_CCC
        t.last_updated  = datetime.utcnow()
        db.flush()
    return pool


def _oracle_sync_pool(db, pool: CityAMMPool, usd_per_coin: float) -> None:
    """Re-peg the WSC reserve to match the live forex rate if >10 % off."""
    if pool.ccc_reserve <= 0 or usd_per_coin <= 0:
        return
    implied = pool.wsc_reserve / pool.ccc_reserve   # WSC per 1 CCC
    if abs(implied - usd_per_coin) / usd_per_coin < 0.10:
        return
    new_wsc = pool.ccc_reserve * usd_per_coin
    delta   = new_wsc - pool.wsc_reserve
    pool.wsc_reserve = new_wsc
    pool.updated_at  = datetime.utcnow()
    t = _get_or_create_treasury(db, pool.city_id)
    t.total_minted = max(0.0, t.total_minted + delta)
    t.last_updated = datetime.utcnow()


def _get_city_coin_info(city_id: int):
    """Return (symbol, peg_label, usd_per_coin) for a city's stable coin, or None."""
    from cities import CityBank, get_db as cities_get_db, _get_peg_usd_per_unit
    db = cities_get_db()
    try:
        bank = db.query(CityBank).filter(CityBank.city_id == city_id).first()
        if not bank or not bank.stable_coin_symbol:
            return None
        sym = bank.stable_coin_symbol
        peg = sym.split("-", 1)[1] if "-" in sym else sym
        usd = _get_peg_usd_per_unit(peg)
        return {"symbol": sym, "peg_label": peg, "usd_per_coin": usd}
    finally:
        db.close()


def _get_or_create_csc_balance(cities_db, player_id: int, city_id: int):
    """Get or create a player's CityStableCoinBalance row."""
    from cities import CityStableCoinBalance
    row = cities_db.query(CityStableCoinBalance).filter(
        CityStableCoinBalance.player_id == player_id,
        CityStableCoinBalance.city_id   == city_id,
    ).first()
    if not row:
        row = CityStableCoinBalance(player_id=player_id, city_id=city_id)
        cities_db.add(row)
        cities_db.flush()
    return row


# ──────────────────────────────────────────────────────────────────────────────
# QUOTES (read-only)
# ──────────────────────────────────────────────────────────────────────────────

def get_wsc_to_ccc_quote(city_id: int, wsc_amount: float) -> Tuple[float, float]:
    """How much CCC does `wsc_amount` WSC buy?  Returns (ccc_out, rate)."""
    info = _get_city_coin_info(city_id)
    if not info or wsc_amount <= 0:
        return 0.0, 0.0
    db = get_db()
    try:
        pool = _get_or_create_amm_pool(db, city_id, info["usd_per_coin"])
        _oracle_sync_pool(db, pool, info["usd_per_coin"])
        db.commit()
        if pool.wsc_reserve <= 0 or pool.ccc_reserve <= 0:
            return 0.0, 0.0
        amt   = wsc_amount * (1.0 - CCC_AMM_FEE)
        k     = pool.wsc_reserve * pool.ccc_reserve
        new_w = pool.wsc_reserve + amt
        new_c = k / new_w
        out   = pool.ccc_reserve - new_c
        rate  = wsc_amount / out if out > 0 else 0.0
        return max(out, 0.0), rate
    finally:
        db.close()


def get_ccc_to_wsc_quote(city_id: int, ccc_amount: float) -> Tuple[float, float]:
    """How much WSC does `ccc_amount` CCC buy?  Returns (wsc_out, rate)."""
    info = _get_city_coin_info(city_id)
    if not info or ccc_amount <= 0:
        return 0.0, 0.0
    db = get_db()
    try:
        pool = _get_or_create_amm_pool(db, city_id, info["usd_per_coin"])
        _oracle_sync_pool(db, pool, info["usd_per_coin"])
        db.commit()
        if pool.wsc_reserve <= 0 or pool.ccc_reserve <= 0:
            return 0.0, 0.0
        amt   = ccc_amount * (1.0 - CCC_AMM_FEE)
        k     = pool.wsc_reserve * pool.ccc_reserve
        new_c = pool.ccc_reserve + amt
        new_w = k / new_c
        out   = pool.wsc_reserve - new_w
        rate  = ccc_amount / out if out > 0 else 0.0
        return max(out, 0.0), rate
    finally:
        db.close()


# ──────────────────────────────────────────────────────────────────────────────
# AMM SWAPS
# ──────────────────────────────────────────────────────────────────────────────

def swap_wsc_for_city_coin(player_id: int, city_id: int, wsc_amount: float) -> Tuple[bool, str]:
    """Buy CCC with WSC via the city AMM pool."""
    if wsc_amount <= 0:
        return False, "Amount must be positive."

    info = _get_city_coin_info(city_id)
    if not info:
        return False, "This city has no active stable coin."

    from wallet import WSCWallet, get_db as wallet_get_db
    from cities import CityStableCoinBalance, get_db as cities_get_db

    cw_db  = get_db()         # city_wallet tables
    wsc_db = wallet_get_db()  # WSCWallet
    csc_db = cities_get_db()  # CityStableCoinBalance
    try:
        pool = _get_or_create_amm_pool(cw_db, city_id, info["usd_per_coin"])
        _oracle_sync_pool(cw_db, pool, info["usd_per_coin"])
        if pool.ccc_reserve <= 0:
            return False, "Pool has no CCC liquidity yet."

        fee_wsc  = wsc_amount * CCC_AMM_FEE
        amt      = wsc_amount - fee_wsc
        k        = pool.wsc_reserve * pool.ccc_reserve
        new_wsc  = pool.wsc_reserve + amt
        new_ccc  = k / new_wsc
        ccc_out  = pool.ccc_reserve - new_ccc
        if ccc_out <= 0:
            return False, "Swap would drain the pool. Try a smaller amount."

        # Atomic WSC deduction
        res = wsc_db.execute(
            sa_update(WSCWallet)
            .where(WSCWallet.player_id == player_id)
            .where(WSCWallet.balance   >= wsc_amount)
            .values(balance=WSCWallet.balance - wsc_amount)
        )
        wsc_db.commit()
        if res.rowcount == 0:
            have = wsc_db.query(WSCWallet.balance).filter(WSCWallet.player_id == player_id).scalar() or 0.0
            return False, f"Insufficient WSC: have {have:.4f}, need {wsc_amount:.4f}."

        # Update pool
        pool.wsc_reserve  = new_wsc + fee_wsc   # fee stays in pool
        pool.ccc_reserve  = new_ccc
        pool.total_swaps += 1
        pool.updated_at   = datetime.utcnow()

        # Credit CCC
        bal = _get_or_create_csc_balance(csc_db, player_id, city_id)
        bal.balance        += ccc_out
        bal.total_received += ccc_out

        # Seed treasury from fee
        fee_usd = fee_wsc   # 1 WSC = $1
        _credit_pools(cw_db, city_id, fee_usd)

        cw_db.commit()
        csc_db.commit()

        sym  = info["symbol"]
        rate = wsc_amount / ccc_out if ccc_out > 0 else 0.0
        return True, (
            f"Swapped {wsc_amount:.4f} WSC → {ccc_out:.4f} {sym} "
            f"(rate: {rate:.6f} WSC/{sym}, fee: {fee_wsc:.4f} WSC)."
        )
    except Exception as e:
        cw_db.rollback(); wsc_db.rollback(); csc_db.rollback()
        return False, f"Swap error: {e}"
    finally:
        cw_db.close(); wsc_db.close(); csc_db.close()


def swap_city_coin_for_wsc(player_id: int, city_id: int, ccc_amount: float) -> Tuple[bool, str]:
    """Sell CCC back for WSC via the city AMM pool."""
    if ccc_amount <= 0:
        return False, "Amount must be positive."

    info = _get_city_coin_info(city_id)
    if not info:
        return False, "This city has no active stable coin."

    from wallet import WSCWallet, get_db as wallet_get_db
    from cities import CityStableCoinBalance, get_db as cities_get_db

    cw_db  = get_db()
    wsc_db = wallet_get_db()
    csc_db = cities_get_db()
    try:
        pool = _get_or_create_amm_pool(cw_db, city_id, info["usd_per_coin"])
        _oracle_sync_pool(cw_db, pool, info["usd_per_coin"])
        if pool.wsc_reserve <= 0:
            return False, "Pool has no WSC liquidity."

        bal = _get_or_create_csc_balance(csc_db, player_id, city_id)
        if (bal.balance or 0.0) < ccc_amount:
            return False, f"Insufficient {info['symbol']}: have {bal.balance:.4f}, need {ccc_amount:.4f}."

        fee_ccc = ccc_amount * CCC_AMM_FEE
        amt     = ccc_amount - fee_ccc
        k       = pool.wsc_reserve * pool.ccc_reserve
        new_ccc = pool.ccc_reserve + amt
        new_wsc = k / new_ccc
        wsc_out = pool.wsc_reserve - new_wsc
        if wsc_out <= 0:
            return False, "Swap would drain the WSC reserve. Try a smaller amount."

        # Deduct CCC
        bal.balance -= ccc_amount

        # Update pool
        pool.ccc_reserve  = new_ccc + fee_ccc
        pool.wsc_reserve  = new_wsc
        pool.total_swaps += 1
        pool.updated_at   = datetime.utcnow()

        # Credit WSC
        w = wsc_db.query(WSCWallet).filter(WSCWallet.player_id == player_id).first()
        if not w:
            w = WSCWallet(player_id=player_id)
            wsc_db.add(w)
        w.balance += wsc_out

        # Treasury: fee valued in USD
        fee_usd = fee_ccc * info["usd_per_coin"]
        _credit_pools(cw_db, city_id, fee_usd)

        cw_db.commit(); wsc_db.commit(); csc_db.commit()

        sym  = info["symbol"]
        rate = ccc_amount / wsc_out if wsc_out > 0 else 0.0
        return True, (
            f"Swapped {ccc_amount:.4f} {sym} → {wsc_out:.4f} WSC "
            f"(rate: {rate:.6f} {sym}/WSC, fee: {fee_ccc:.4f} {sym})."
        )
    except Exception as e:
        cw_db.rollback(); wsc_db.rollback(); csc_db.rollback()
        return False, f"Swap error: {e}"
    finally:
        cw_db.close(); wsc_db.close(); csc_db.close()


# ──────────────────────────────────────────────────────────────────────────────
# YIELD FARMING
# ──────────────────────────────────────────────────────────────────────────────

def add_city_yield_farming(player_id: int, city_id: int, meme_symbol: str, quantity: float) -> Tuple[bool, str]:
    """Stake meme coins to earn a city's CCC from its yield pool."""
    if quantity <= 0:
        return False, "Quantity must be positive."

    info = _get_city_coin_info(city_id)
    if not info:
        return False, "This city has no active stable coin."

    from memecoins import MemeCoinWallet, get_or_create_meme_wallet, get_db as meme_get_db

    meme_db = meme_get_db()
    cw_db   = get_db()
    try:
        w = meme_db.query(MemeCoinWallet).filter(
            MemeCoinWallet.player_id   == player_id,
            MemeCoinWallet.meme_symbol == meme_symbol,
        ).first()
        bal = w.balance if w else 0.0
        if bal < quantity:
            return False, f"Insufficient {meme_symbol}: have {bal:.4f}, need {quantity:.4f}."

        meme_w = get_or_create_meme_wallet(meme_db, player_id, meme_symbol)
        meme_w.balance -= quantity
        meme_db.commit()

        dep = CityYieldDeposit(city_id=city_id, player_id=player_id,
                               meme_symbol=meme_symbol, quantity=quantity)
        cw_db.add(dep)
        cw_db.commit()
        return True, f"Staked {quantity:.4f} {meme_symbol} for {info['symbol']} yield. Rewards accrue hourly."
    except Exception as e:
        meme_db.rollback(); cw_db.rollback()
        return False, str(e)
    finally:
        meme_db.close(); cw_db.close()


def remove_city_yield_farming(player_id: int, deposit_id: int) -> Tuple[bool, str]:
    """Unstake from city yield farming and return meme coins."""
    from memecoins import get_or_create_meme_wallet, get_db as meme_get_db

    cw_db   = get_db()
    meme_db = meme_get_db()
    try:
        dep = cw_db.query(CityYieldDeposit).filter(
            CityYieldDeposit.id        == deposit_id,
            CityYieldDeposit.player_id == player_id,
            CityYieldDeposit.is_active == True,
        ).first()
        if not dep:
            return False, "Deposit not found or already withdrawn."
        dep.is_active = False
        cw_db.commit()

        mw = get_or_create_meme_wallet(meme_db, player_id, dep.meme_symbol)
        mw.balance += dep.quantity
        meme_db.commit()
        return True, f"Unstaked {dep.quantity:.4f} {dep.meme_symbol}."
    except Exception as e:
        cw_db.rollback(); meme_db.rollback()
        return False, str(e)
    finally:
        cw_db.close(); meme_db.close()


def _tick_city_yield_farming(cw_db, city_id: int, current_tick: int):
    """Distribute CCC from city yield pool to active stakers. Called every tick."""
    if current_tick % CCC_YIELD_PAYOUT_TICKS != 0:
        return

    from memecoins import MemeCoin, get_db as meme_get_db
    from cities import CityStableCoinBalance, get_db as cities_get_db

    meme_db  = meme_get_db()
    csc_db   = cities_get_db()
    try:
        t = _get_or_create_treasury(cw_db, city_id)
        if t.yield_pool <= 0:
            return

        deposits = cw_db.query(CityYieldDeposit).filter(
            CityYieldDeposit.city_id   == city_id,
            CityYieldDeposit.is_active == True,
        ).all()
        if not deposits:
            return

        weighted = {}
        total_w  = 0.0
        for d in deposits:
            meme  = meme_db.query(MemeCoin).filter(MemeCoin.symbol == d.meme_symbol).first()
            price = (meme.last_price if meme and meme.last_price and meme.last_price > 0 else 1.0)
            w = d.quantity * price
            weighted[d.id] = w
            total_w += w

        if total_w <= 0:
            return

        payout_total = t.yield_pool * CCC_YIELD_APY_PER_CYCLE
        t.yield_pool -= payout_total

        for d in deposits:
            share  = weighted[d.id] / total_w
            payout = payout_total * share
            bal    = _get_or_create_csc_balance(csc_db, d.player_id, city_id)
            bal.balance        += payout
            bal.total_received += payout
            d.total_earned     += payout

        cw_db.commit()
        csc_db.commit()
    except Exception as e:
        cw_db.rollback(); csc_db.rollback()
        print(f"[CityWallet] Yield tick error (city {city_id}): {e}")
    finally:
        meme_db.close(); csc_db.close()


# ──────────────────────────────────────────────────────────────────────────────
# FAUCET
# ──────────────────────────────────────────────────────────────────────────────

def claim_city_faucet(player_id: int, city_id: int) -> Tuple[bool, str, float]:
    """Claim CCC from the city faucet pool (1 h cooldown)."""
    import random
    from cities import CityMember, CityStableCoinBalance, get_db as cities_get_db

    cw_db  = get_db()
    csc_db = cities_get_db()
    try:
        info = _get_city_coin_info(city_id)
        if not info:
            return False, "This city has no active stable coin.", 0.0

        # Must be a city member to use the faucet
        member = csc_db.query(CityMember).filter(
            CityMember.city_id   == city_id,
            CityMember.player_id == player_id,
        ).first()
        if not member:
            return False, "You must be a city member to use this faucet.", 0.0

        # Cooldown check
        cutoff = datetime.utcnow() - timedelta(hours=CCC_FAUCET_COOLDOWN_HOURS)
        last   = cw_db.query(CityFaucetClaim).filter(
            CityFaucetClaim.city_id   == city_id,
            CityFaucetClaim.player_id == player_id,
            CityFaucetClaim.claimed_at > cutoff,
        ).first()
        if last:
            ends      = last.claimed_at + timedelta(hours=CCC_FAUCET_COOLDOWN_HOURS)
            remaining = ends - datetime.utcnow()
            hrs  = int(remaining.total_seconds() // 3600)
            mins = int((remaining.total_seconds() % 3600) // 60)
            return False, f"Faucet cooldown: {hrs}h {mins}m remaining.", 0.0

        t = cw_db.query(CityWalletTreasury).filter(
            CityWalletTreasury.city_id == city_id
        ).with_for_update().first()
        if not t:
            t = _get_or_create_treasury(cw_db, city_id)
        if t.faucet_pool <= 0:
            return False, "Faucet pool is empty — more swaps are needed to refill it.", 0.0

        amount = min(round(random.uniform(CCC_FAUCET_AMOUNT_MIN, CCC_FAUCET_AMOUNT_MAX), 4),
                     t.faucet_pool)
        t.faucet_pool -= amount

        bal = _get_or_create_csc_balance(csc_db, player_id, city_id)
        bal.balance        += amount
        bal.total_received += amount

        cw_db.add(CityFaucetClaim(city_id=city_id, player_id=player_id, amount=amount))
        cw_db.commit()
        csc_db.commit()
        return True, f"Faucet: you received {amount:.4f} {info['symbol']}!", amount
    except Exception as e:
        cw_db.rollback(); csc_db.rollback()
        return False, str(e), 0.0
    finally:
        cw_db.close(); csc_db.close()


def _tick_city_airdrops(cw_db, city_id: int, current_tick: int):
    """Airdrop CCC to all city members every CCC_AIRDROP_INTERVAL_TICKS."""
    if current_tick % CCC_AIRDROP_INTERVAL_TICKS != 0:
        return

    from cities import CityMember, get_db as cities_get_db

    csc_db = cities_get_db()
    try:
        t = _get_or_create_treasury(cw_db, city_id)
        if t.airdrop_pool <= 0:
            return

        members = csc_db.query(CityMember).filter(
            CityMember.city_id == city_id
        ).all()
        if not members:
            return

        payout = min(
            t.airdrop_pool * CCC_AIRDROP_POOL_PCT_PER_RUN / max(len(members), 1),
            CCC_AIRDROP_MAX_PER_MEMBER,
        )
        if payout <= 0:
            return

        total = 0.0
        for m in members:
            bal = _get_or_create_csc_balance(csc_db, m.player_id, city_id)
            bal.balance        += payout
            bal.total_received += payout
            total              += payout

        t.airdrop_pool -= total
        cw_db.commit()
        csc_db.commit()
    except Exception as e:
        cw_db.rollback(); csc_db.rollback()
        print(f"[CityWallet] Airdrop tick error (city {city_id}): {e}")
    finally:
        csc_db.close()


# ──────────────────────────────────────────────────────────────────────────────
# READ HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def get_city_treasury_info(city_id: int) -> dict:
    db = get_db()
    try:
        t = db.query(CityWalletTreasury).filter(CityWalletTreasury.city_id == city_id).first()
        if not t:
            return {"yield_pool": 0.0, "faucet_pool": 0.0, "airdrop_pool": 0.0,
                    "total_minted": 0.0, "total_burned": 0.0}
        return {
            "yield_pool":   t.yield_pool,
            "faucet_pool":  t.faucet_pool,
            "airdrop_pool": t.airdrop_pool,
            "total_minted": t.total_minted,
            "total_burned": t.total_burned,
        }
    finally:
        db.close()


def get_city_amm_pool_info(city_id: int) -> dict:
    db = get_db()
    try:
        pool = db.query(CityAMMPool).filter(CityAMMPool.city_id == city_id).first()
        if not pool:
            return {"wsc_reserve": 0.0, "ccc_reserve": 0.0, "total_swaps": 0}
        return {
            "wsc_reserve": pool.wsc_reserve,
            "ccc_reserve": pool.ccc_reserve,
            "total_swaps": pool.total_swaps,
        }
    finally:
        db.close()


def get_player_city_yield_deposits(player_id: int, city_id: int) -> List[dict]:
    from memecoins import MemeCoin, get_db as meme_get_db
    cw_db   = get_db()
    meme_db = meme_get_db()
    try:
        deps = cw_db.query(CityYieldDeposit).filter(
            CityYieldDeposit.player_id == player_id,
            CityYieldDeposit.city_id   == city_id,
            CityYieldDeposit.is_active == True,
        ).all()
        result = []
        for d in deps:
            meme  = meme_db.query(MemeCoin).filter(MemeCoin.symbol == d.meme_symbol).first()
            price = (meme.last_price or 0.0) if meme else 0.0
            result.append({
                "id":           d.id,
                "meme_symbol":  d.meme_symbol,
                "meme_name":    meme.name if meme else d.meme_symbol,
                "quantity":     d.quantity,
                "last_price":   price,
                "total_earned": d.total_earned,
                "deposited_at": d.deposited_at.isoformat(),
            })
        return result
    finally:
        cw_db.close(); meme_db.close()


def get_city_faucet_status(player_id: int, city_id: int) -> dict:
    db = get_db()
    try:
        cutoff = datetime.utcnow() - timedelta(hours=CCC_FAUCET_COOLDOWN_HOURS)
        last = db.query(CityFaucetClaim).filter(
            CityFaucetClaim.player_id == player_id,
            CityFaucetClaim.city_id   == city_id,
            CityFaucetClaim.claimed_at > cutoff,
        ).first()
        if not last:
            return {"can_claim": True, "remaining_seconds": 0}
        ends = last.claimed_at + timedelta(hours=CCC_FAUCET_COOLDOWN_HOURS)
        secs = max(0, int((ends - datetime.utcnow()).total_seconds()))
        return {"can_claim": secs <= 0, "remaining_seconds": secs}
    finally:
        db.close()


# ──────────────────────────────────────────────────────────────────────────────
# TICK
# ──────────────────────────────────────────────────────────────────────────────

async def tick(current_tick: int, now):
    """Called every app tick. Runs yield + airdrop for all active city coins."""
    from cities import CityBank, get_db as cities_get_db

    cities_db = cities_get_db()
    try:
        active_banks = cities_db.query(CityBank).filter(
            CityBank.stable_coin_symbol.isnot(None),
            CityBank.stable_coin_symbol != "",
        ).all()
        city_ids = [b.city_id for b in active_banks]
    finally:
        cities_db.close()

    if not city_ids:
        return

    cw_db = get_db()
    try:
        for cid in city_ids:
            _tick_city_yield_farming(cw_db, cid, current_tick)
            _tick_city_airdrops(cw_db, cid, current_tick)
    except Exception as e:
        print(f"[CityWallet] Tick error: {e}")
    finally:
        cw_db.close()
