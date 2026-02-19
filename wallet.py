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
from sqlalchemy import create_engine, Column, String, Float, DateTime, Integer, Boolean, func as sqlfunc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./wadsworth.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
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

FAUCET_COOLDOWN_HOURS = 4
FAUCET_AMOUNT_MIN     = 0.10
FAUCET_AMOUNT_MAX     = 1.00

AIRDROP_INTERVAL_TICKS   = 2880   # every ~4 hours
AIRDROP_POOL_PCT_PER_RUN = 0.10   # 10 % of airdrop pool per run
AIRDROP_MAX_PER_PLAYER   = 1.0    # cap: 1 WSC per player per airdrop


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
        t = WSCTreasury(id=1)
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

    Exchange rate uses last_price × native-token USD price for both coins,
    enabling fair cross-chain swaps without needing a shared native token.

    Fees: 3 % on sell leg + 3 % on buy leg → all burned → 90 % minted as WSC.

    Returns (success, message, detail_dict).
    """
    from memecoins import MemeCoin, MemeCoinWallet, get_or_create_meme_wallet, get_db as meme_get_db
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

        price_from = meme_from.last_price or 0.0
        price_to   = meme_to.last_price   or 0.0
        if price_from <= 0:
            return False, f"{from_symbol} has no price yet (no trades have occurred).", {}
        if price_to <= 0:
            return False, f"{to_symbol} has no price yet (no trades have occurred).", {}

        # Check balance
        from_wallet = meme_db.query(MemeCoinWallet).filter(
            MemeCoinWallet.player_id == player_id,
            MemeCoinWallet.meme_symbol == from_symbol,
        ).first()
        from_bal = from_wallet.balance if from_wallet else 0.0
        if from_bal < amount:
            return False, f"Insufficient {from_symbol}: have {from_bal:.4f}, need {amount:.4f}.", {}

        # True-value exchange using native USD prices
        usd_from = _native_usd_price(county_db, meme_from.county_id)
        usd_to   = _native_usd_price(county_db, meme_to.county_id)

        # USD value being sold
        sell_usd_value = amount * price_from * usd_from

        # Apply 3 % sell fee
        sell_fee_usd   = sell_usd_value * SWAP_FEE_SELL
        net_usd        = sell_usd_value - sell_fee_usd

        # Apply 3 % buy fee
        buy_fee_usd    = net_usd * SWAP_FEE_BUY
        net_usd_for_buy = net_usd - buy_fee_usd

        # How many to_symbol coins the player receives
        amount_out = net_usd_for_buy / (price_to * usd_to)

        total_fee_usd = sell_fee_usd + buy_fee_usd
        is_cross_chain = (meme_from.county_id != meme_to.county_id)

        # — Execute wallet transfers —
        from_w = get_or_create_meme_wallet(meme_db, player_id, from_symbol)
        from_w.balance   -= amount
        from_w.total_sold += amount

        to_w = get_or_create_meme_wallet(meme_db, player_id, to_symbol)
        to_w.balance     += amount_out
        to_w.total_bought += amount_out

        meme_db.commit()

        # — Burn fee → mint WSC —
        wsc_minted = _burn_and_mint_wsc(wallet_db, total_fee_usd)
        wallet_db.commit()

        # — Audit record —
        rec = WalletSwapRecord(
            player_id=player_id,
            from_symbol=from_symbol,
            to_symbol=to_symbol,
            amount_in=amount,
            amount_out=amount_out,
            fee_burned_value=total_fee_usd,
            wsc_minted=wsc_minted,
            is_cross_chain=is_cross_chain,
        )
        wallet_db.add(rec)
        wallet_db.commit()

        chain_note = "(cross-chain)" if is_cross_chain else "(same chain)"
        msg = (
            f"Swapped {amount:.4f} {from_symbol} → {amount_out:.4f} {to_symbol} {chain_note}. "
            f"Fee: ${total_fee_usd:.4f} burned → {wsc_minted:.4f} WSC minted for rewards pool."
        )
        return True, msg, {
            "from_symbol": from_symbol, "to_symbol": to_symbol,
            "amount_in": amount, "amount_out": amount_out,
            "sell_fee_usd": sell_fee_usd, "buy_fee_usd": buy_fee_usd,
            "total_fee_usd": total_fee_usd, "wsc_minted": wsc_minted,
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

        # Weight each deposit by quantity × last_price
        weighted = {}
        total_w  = 0.0
        for d in deposits:
            meme = meme_db.query(MemeCoin).filter(MemeCoin.symbol == d.meme_symbol).first()
            price = (meme.last_price or 0.0) if meme else 0.0
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
    """
    if amount <= 0:
        return False, "Amount must be positive."

    wallet_db = get_db()
    try:
        wsc_w = wallet_db.query(WSCWallet).filter(WSCWallet.player_id == player_id).first()
        bal   = wsc_w.balance if wsc_w else 0.0
        if bal < amount:
            return False, f"Insufficient WSC: have {bal:.4f}, need {amount:.4f}."

        wsc_w = _get_or_create_wsc_wallet(wallet_db, player_id)
        wsc_w.balance        -= amount
        wsc_w.total_redeemed += amount
        wallet_db.commit()

        from auth import get_db as auth_get_db, Player
        auth_db = auth_get_db()
        try:
            p = auth_db.query(Player).filter(Player.id == player_id).first()
            if not p:
                # Roll back the deduction
                wsc_w.balance        += amount
                wsc_w.total_redeemed -= amount
                wallet_db.commit()
                return False, "Player not found."
            p.cash_balance = (p.cash_balance or 0.0) + amount
            auth_db.commit()
        finally:
            auth_db.close()

        return True, f"Redeemed {amount:.4f} WSC → ${amount:.2f} in-game cash credited."
    except Exception as e:
        wallet_db.rollback()
        return False, str(e)
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
