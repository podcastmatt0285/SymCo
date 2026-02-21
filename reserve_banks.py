"""
reserve_banks.py — State Reserve Banks, Multi-Currency, Bonds & Forex

Architecture
============
State Reserve Banks are government-chartered institutions that issue foreign
currencies.  Currency enters circulation ONLY through bond-interest payments:

  1. Player obtains WSC (via native-token AMM pool in wallet.py).
  2. Player buys a bond from a reserve bank using WSC.
  3. Bond accrues interest each hour (game tick).
  4. Interest is paid in the issuing bank's currency.
  5. Player now holds foreign currency they can use for trade or save.

Cross-currency trades trigger an automatic forex conversion via the reserve
banks (each bank holds reserves of other currencies, backed by swapped bonds).

USD is the default game currency — no reserve bank is needed for it.
All other currencies require a reserve bank.

Supported currencies (plus USD as base):
  JPY  Japanese Yen         ¥
  MXP  Mexican Peso         $
  GBP  British Pound        £
  CHF  Swiss Franc          Fr
  CNY  Chinese Yuan         ¥
  EUR  Euro                 €
  INR  Indian Rupee         ₹
  RUB  Russian Ruble        ₽

Bond mechanics
==============
  - Face value: 1 bond = 1 WSC paid at purchase time.
  - Yield rate: dynamic; adjusts each tick based on net bond demand.
    More buying → yield falls (currency appreciates).
    More selling/redemption → yield rises.
    Yield can go negative (just like real-world JGBs, Bunds, etc.).
  - Interest accrues hourly: interest = face_value × yield_rate / TICKS_PER_YEAR
  - Interest paid in the bank's own currency (credited to player's
    currency_balances row).
  - Available maturities: 30 / 90 / 180 / 365 calendar days.
  - Selling before maturity: player receives WSC back at a discount/premium
    calculated from the current yield vs. the purchase yield.
  - At maturity: face value returned in WSC + all accrued interest.

Forex
=====
  - usd_per_unit: how many USD one unit of the currency is worth.
  - Adjusts each tick based on yield changes (higher yield → depreciation
    in the long run; lower yield → appreciation — same as real bond-forex link).
  - Forex swap fee: 0.2 % on each conversion.
  - Auto-conversion happens when a player with a non-USD legal tender
    receives USD-denominated income (salary, business revenue, etc.) — the
    helper convert_to_legal_tender() is called by income functions.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Tuple

from sqlalchemy import create_engine, Column, Integer, Float, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# ==========================
# DATABASE
# ==========================

DATABASE_URL = "sqlite:///./reserve_banks.db"
engine       = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base         = declarative_base()

# ==========================
# CONSTANTS
# ==========================

RESERVE_BANKS_TICK_INTERVAL = 720   # app ticks between bond-interest accruals (~1 h)
TICKS_PER_YEAR              = 8760  # 365 days × 24 hourly ticks

# Yield dynamics: yield shifts by ±YIELD_SENSITIVITY per $1 000 net WSC flow per tick.
# Positive net flow (buys > redeems) → yield falls.
YIELD_SENSITIVITY  = 0.00001       # yield change per $1 of net demand per tick

# FX dynamics: each 1 % yield change causes a proportional FX movement.
FX_YIELD_LINK      = 0.005         # usd_per_unit fractional change per 1 % yield Δ (inverse)

FOREX_FEE_RATE     = 0.002         # 0.2 % fee on each forex conversion
BOND_MATURITIES    = [30, 90, 180, 365]   # calendar days

# Default reserve banks seeded on initialize()
DEFAULT_BANKS = [
    # code, name, symbol, flag, initial_yield, usd_per_unit, min_yield, max_yield
    ("JPY", "Bank of Wadsworth Japan",           "¥",  "🇯🇵", 0.001,  0.0067, -0.005, 0.15),
    ("MXP", "Banco de Reserva Wadsworth",        "$",  "🇲🇽", 0.080,  0.058,   0.020, 0.50),
    ("GBP", "Wadsworth Bank of England",         "£",  "🇬🇧", 0.045,  1.270,  -0.010, 0.20),
    ("CHF", "Wadsworth National Bank",           "Fr", "🇨🇭", 0.015,  1.120,  -0.020, 0.10),
    ("CNY", "People's Reserve Bank of Wadsworth","¥",  "🇨🇳", 0.025,  0.138,   0.005, 0.25),
    ("EUR", "Wadsworth Central Bank",            "€",  "🇪🇺", 0.030,  1.080,  -0.010, 0.20),
    ("INR", "Reserve Bank of Wadsworth India",   "₹",  "🇮🇳", 0.065,  0.012,   0.030, 0.35),
    ("RUB", "Wadsworth Central Reserve Bank",    "₽",  "🇷🇺", 0.160,  0.011,   0.050, 0.99),
]

# ==========================
# MODELS
# ==========================

class StateReserveBank(Base):
    """One row per foreign currency.  Owns all bonds denominated in that currency."""
    __tablename__ = "state_reserve_banks"

    id               = Column(Integer, primary_key=True, index=True)
    currency_code    = Column(String(8),  unique=True, index=True, nullable=False)   # "JPY"
    currency_name    = Column(String(80), nullable=False)                             # "Japanese Yen"
    currency_symbol  = Column(String(8),  nullable=False)                             # "¥"
    flag_emoji       = Column(String(8),  nullable=False, default="🏦")

    # Yield / FX
    yield_rate       = Column(Float, default=0.05)    # e.g. 0.05 = 5 % annual
    min_yield        = Column(Float, default=-0.02)
    max_yield        = Column(Float, default=0.50)
    usd_per_unit     = Column(Float, default=1.0)     # e.g. 0.0067 for JPY

    # Rolling demand tracker (reset each tick after yield adjustment)
    net_demand_wsc   = Column(Float, default=0.0)     # +buy / -sell this period

    # Aggregate stats
    total_bonds_issued    = Column(Integer, default=0)
    total_face_value_wsc  = Column(Float,   default=0.0)
    total_interest_paid   = Column(Float,   default=0.0)
    total_forex_volume    = Column(Float,   default=0.0)

    founded_at       = Column(DateTime, default=datetime.utcnow)


class ReserveBankBond(Base):
    """A bond held by a player in a specific reserve bank."""
    __tablename__ = "reserve_bank_bonds"

    id               = Column(Integer, primary_key=True, index=True)
    bank_id          = Column(Integer, index=True,  nullable=False)
    holder_player_id = Column(Integer, index=True,  nullable=False)
    face_value_wsc   = Column(Float,   nullable=False)   # WSC paid at purchase
    purchase_yield   = Column(Float,   nullable=False)   # yield at time of purchase
    maturity_days    = Column(Integer, nullable=False)   # 30 / 90 / 180 / 365
    purchased_at     = Column(DateTime, default=datetime.utcnow)
    matures_at       = Column(DateTime, nullable=False)
    interest_accrued = Column(Float,   default=0.0)      # in the bank's own currency
    total_interest_paid = Column(Float, default=0.0)
    status           = Column(String,  default="active") # active / matured / sold


class PlayerLegalTender(Base):
    """Records each player's chosen legal tender.  Absence = USD (default)."""
    __tablename__ = "player_legal_tenders"

    player_id     = Column(Integer, primary_key=True, index=True)
    currency_code = Column(String(8), nullable=False, default="USD")
    changed_at    = Column(DateTime, default=datetime.utcnow)


class PlayerCurrencyBalance(Base):
    """
    A player's balance in a foreign currency earned as bond interest.
    One row per (player, currency_code) pair.
    """
    __tablename__ = "player_currency_balances"

    id            = Column(Integer, primary_key=True, index=True)
    player_id     = Column(Integer, index=True, nullable=False)
    currency_code = Column(String(8), index=True, nullable=False)
    balance       = Column(Float, default=0.0)
    total_earned  = Column(Float, default=0.0)
    total_spent   = Column(Float, default=0.0)
    updated_at    = Column(DateTime, default=datetime.utcnow)


class ForexTrade(Base):
    """Audit trail of every automatic or manual forex conversion."""
    __tablename__ = "forex_trades"

    id             = Column(Integer, primary_key=True, index=True)
    player_id      = Column(Integer, index=True, nullable=True)   # None = system/bank swap
    from_currency  = Column(String(8), nullable=False)
    to_currency    = Column(String(8), nullable=False)
    amount_from    = Column(Float, nullable=False)
    amount_to      = Column(Float, nullable=False)
    exchange_rate  = Column(Float, nullable=False)   # to_per_from
    fee_usd        = Column(Float, default=0.0)
    executed_at    = Column(DateTime, default=datetime.utcnow)


class BondYieldHistory(Base):
    """Hourly snapshot of each bank's yield and FX rate (for charting)."""
    __tablename__ = "bond_yield_history"

    id            = Column(Integer, primary_key=True, index=True)
    bank_id       = Column(Integer, index=True, nullable=False)
    yield_rate    = Column(Float, nullable=False)
    usd_per_unit  = Column(Float, nullable=False)
    recorded_at   = Column(DateTime, default=datetime.utcnow)


Base.metadata.create_all(engine)


# ==========================
# DB HELPER
# ==========================

def get_db():
    return SessionLocal()


# ==========================
# INITIALIZATION
# ==========================

def initialize():
    """Seed default reserve banks if they don't exist yet."""
    db = get_db()
    try:
        for (code, name, sym, flag, yield_r, usd_rate, min_y, max_y) in DEFAULT_BANKS:
            exists = db.query(StateReserveBank).filter(
                StateReserveBank.currency_code == code
            ).first()
            if not exists:
                bank = StateReserveBank(
                    currency_code   = code,
                    currency_name   = name,
                    currency_symbol = sym,
                    flag_emoji      = flag,
                    yield_rate      = yield_r,
                    usd_per_unit    = usd_rate,
                    min_yield       = min_y,
                    max_yield       = max_y,
                )
                db.add(bank)
        db.commit()
        print(f"[ReserveBanks] {len(DEFAULT_BANKS)} banks seeded/verified.")
    except Exception as e:
        db.rollback()
        print(f"[ReserveBanks] Initialize error: {e}")
    finally:
        db.close()


# ==========================
# TICK (called hourly by app)
# ==========================

async def tick(app_tick: int, now: datetime):
    """Hourly housekeeping: accrue bond interest, adjust yields + FX rates, snapshot history."""
    if app_tick % RESERVE_BANKS_TICK_INTERVAL != 0:
        return

    db = get_db()
    try:
        banks = db.query(StateReserveBank).all()
        for bank in banks:
            _accrue_interest(db, bank, now)
            _adjust_yield_and_fx(db, bank)
            _mature_bonds(db, bank, now)
            _snapshot_history(db, bank, now)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[ReserveBanks] Tick error: {e}")
    finally:
        db.close()


def _accrue_interest(db, bank: StateReserveBank, now: datetime):
    """Credit one hour's interest on all active bonds for this bank."""
    active_bonds = db.query(ReserveBankBond).filter(
        ReserveBankBond.bank_id == bank.id,
        ReserveBankBond.status  == "active",
    ).all()
    for bond in active_bonds:
        # Hourly interest = face_value_wsc × yield_rate / TICKS_PER_YEAR
        # Negative yield accrues negative interest (reduces balance).
        hourly = bond.face_value_wsc * bank.yield_rate / TICKS_PER_YEAR
        bond.interest_accrued += hourly

        # Credit (or debit) the player's currency balance.
        _adjust_currency_balance(db, bond.holder_player_id, bank.currency_code, hourly)

        bank.total_interest_paid += abs(hourly)


def _adjust_yield_and_fx(db, bank: StateReserveBank):
    """
    Shift yield based on net WSC demand this period.
    Positive demand (buys exceed redemptions) → lower yield (more buyers = richer bond).
    Negative demand → higher yield (nobody wants the bond → must offer more return).
    Then link FX rate to yield change: lower yield → stronger currency (appreciation).
    """
    old_yield = bank.yield_rate
    demand    = bank.net_demand_wsc

    # Yield change proportional to net demand
    delta_yield = -demand * YIELD_SENSITIVITY
    new_yield   = old_yield + delta_yield
    new_yield   = max(bank.min_yield, min(bank.max_yield, new_yield))
    bank.yield_rate     = new_yield
    bank.net_demand_wsc = 0.0   # reset for next period

    # FX: lower yield (more demand) → currency appreciates
    yield_change_pct = (new_yield - old_yield)   # e.g. -0.001 means yield fell 0.1 %
    fx_change = -yield_change_pct * FX_YIELD_LINK * bank.usd_per_unit
    bank.usd_per_unit = max(0.000001, bank.usd_per_unit + fx_change)


def _mature_bonds(db, bank: StateReserveBank, now: datetime):
    """Return WSC face value to players whose bonds have matured."""
    from auth import get_db as auth_get_db, Player

    matured = db.query(ReserveBankBond).filter(
        ReserveBankBond.bank_id   == bank.id,
        ReserveBankBond.status    == "active",
        ReserveBankBond.matures_at <= now,
    ).all()

    if not matured:
        return

    auth_db = auth_get_db()
    try:
        for bond in matured:
            bond.status = "matured"
            # Return face value in WSC
            from wallet import get_db as wallet_get_db, WSCWallet, _get_or_create_wsc_wallet
            wdb = wallet_get_db()
            try:
                wsc_w = _get_or_create_wsc_wallet(wdb, bond.holder_player_id)
                wsc_w.balance += bond.face_value_wsc
                wdb.commit()
            finally:
                wdb.close()
    finally:
        auth_db.close()


def _snapshot_history(db, bank: StateReserveBank, now: datetime):
    """Record hourly yield/FX snapshot for the dashboard chart."""
    snap = BondYieldHistory(
        bank_id      = bank.id,
        yield_rate   = bank.yield_rate,
        usd_per_unit = bank.usd_per_unit,
        recorded_at  = now,
    )
    db.add(snap)


# ==========================
# CURRENCY BALANCE HELPERS
# ==========================

def _get_or_create_currency_balance(db, player_id: int, currency_code: str) -> PlayerCurrencyBalance:
    bal = db.query(PlayerCurrencyBalance).filter(
        PlayerCurrencyBalance.player_id     == player_id,
        PlayerCurrencyBalance.currency_code == currency_code,
    ).first()
    if not bal:
        bal = PlayerCurrencyBalance(player_id=player_id, currency_code=currency_code)
        db.add(bal)
        db.flush()
    return bal


def _adjust_currency_balance(db, player_id: int, currency_code: str, amount: float):
    """Add (or subtract if negative) `amount` to a player's currency balance."""
    bal = _get_or_create_currency_balance(db, player_id, currency_code)
    bal.balance     += amount
    bal.updated_at   = datetime.utcnow()
    if amount > 0:
        bal.total_earned += amount
    else:
        bal.total_spent  += abs(amount)


# ==========================
# BOND PURCHASE / SALE
# ==========================

def purchase_bond(
    player_id: int,
    currency_code: str,
    wsc_amount: float,
    maturity_days: int,
) -> Tuple[bool, str]:
    """
    Buy a bond from the specified reserve bank using WSC.
    The bond pays interest in the bank's currency over its lifetime.
    """
    if wsc_amount <= 0:
        return False, "Bond face value must be positive."
    if maturity_days not in BOND_MATURITIES:
        return False, f"Invalid maturity. Choose from {BOND_MATURITIES} days."

    from wallet import get_db as wallet_get_db, WSCWallet, sa_update

    db = get_db()
    wallet_db = wallet_get_db()
    try:
        bank = db.query(StateReserveBank).filter(
            StateReserveBank.currency_code == currency_code.upper()
        ).first()
        if not bank:
            return False, f"No reserve bank found for currency '{currency_code}'."

        # Atomic WSC deduction
        result = wallet_db.execute(
            sa_update(WSCWallet)
            .where(WSCWallet.player_id == player_id)
            .where(WSCWallet.balance   >= wsc_amount)
            .values(balance=WSCWallet.balance - wsc_amount)
        )
        wallet_db.commit()
        if result.rowcount == 0:
            current = wallet_db.query(WSCWallet.balance).filter(
                WSCWallet.player_id == player_id
            ).scalar() or 0.0
            return False, f"Insufficient WSC: have {current:.4f}, need {wsc_amount:.4f}."

        # Create bond
        bond = ReserveBankBond(
            bank_id          = bank.id,
            holder_player_id = player_id,
            face_value_wsc   = wsc_amount,
            purchase_yield   = bank.yield_rate,
            maturity_days    = maturity_days,
            matures_at       = datetime.utcnow() + timedelta(days=maturity_days),
        )
        db.add(bond)

        # Update bank stats and demand tracker (positive = bought)
        bank.total_bonds_issued   += 1
        bank.total_face_value_wsc += wsc_amount
        bank.net_demand_wsc       += wsc_amount

        db.commit()

        annual_pct  = bank.yield_rate * 100
        daily_int   = wsc_amount * bank.yield_rate / 365
        currency_sym = bank.currency_symbol
        return True, (
            f"Bond purchased: {wsc_amount:.2f} WSC → {currency_code} {maturity_days}-day bond. "
            f"Current yield: {annual_pct:.3f}% p.a. "
            f"Est. daily interest: {currency_sym}{daily_int:.4f} {currency_code}. "
            f"Matures: {bond.matures_at.strftime('%Y-%m-%d')}."
        )

    except Exception as e:
        db.rollback()
        wallet_db.rollback()
        return False, f"Bond purchase error: {e}"
    finally:
        db.close()
        wallet_db.close()


def sell_bond(player_id: int, bond_id: int) -> Tuple[bool, str]:
    """
    Sell a bond before maturity for WSC at a price reflecting current yield vs purchase yield.

    Price formula (simplified duration model):
      price_factor = 1 + (purchase_yield - current_yield) × remaining_years
    If current_yield > purchase_yield: bond is worth less (rising rates hurt bonds).
    If current_yield < purchase_yield: bond is worth more (falling rates help bonds).
    """
    from wallet import get_db as wallet_get_db, WSCWallet, _get_or_create_wsc_wallet

    db        = get_db()
    wallet_db = wallet_get_db()
    try:
        bond = db.query(ReserveBankBond).filter(
            ReserveBankBond.id               == bond_id,
            ReserveBankBond.holder_player_id == player_id,
            ReserveBankBond.status           == "active",
        ).first()
        if not bond:
            return False, "Bond not found or already matured/sold."

        bank = db.query(StateReserveBank).filter(StateReserveBank.id == bond.bank_id).first()
        now  = datetime.utcnow()

        remaining_seconds = (bond.matures_at - now).total_seconds()
        remaining_years   = max(remaining_seconds / (365 * 86400), 0.0)

        # Modified-duration price model
        price_factor = 1.0 + (bond.purchase_yield - bank.yield_rate) * remaining_years
        price_factor = max(0.50, min(2.0, price_factor))   # cap to ±50 % of face value
        wsc_return   = bond.face_value_wsc * price_factor

        bond.status                = "sold"
        bank.net_demand_wsc       -= bond.face_value_wsc   # selling = negative demand
        bank.total_face_value_wsc  = max(0.0, bank.total_face_value_wsc - bond.face_value_wsc)
        db.commit()

        # Return WSC to player
        wsc_w = _get_or_create_wsc_wallet(wallet_db, player_id)
        wsc_w.balance += wsc_return
        wallet_db.commit()

        gain_loss = wsc_return - bond.face_value_wsc
        sign      = "+" if gain_loss >= 0 else ""
        return True, (
            f"Bond sold: received {wsc_return:.4f} WSC "
            f"({sign}{gain_loss:.4f} vs face value, price factor {price_factor:.4f}). "
            f"Accumulated interest ({bond.interest_accrued:.4f} {bank.currency_code}) remains in your balance."
        )

    except Exception as e:
        db.rollback()
        wallet_db.rollback()
        return False, f"Bond sale error: {e}"
    finally:
        db.close()
        wallet_db.close()


# ==========================
# FOREX
# ==========================

def get_exchange_rate(from_currency: str, to_currency: str) -> float:
    """
    Return how many units of `to_currency` one unit of `from_currency` buys.
    USD is the base; all rates are expressed via their usd_per_unit.
    """
    if from_currency == to_currency:
        return 1.0

    db = get_db()
    try:
        usd_per_from = _get_usd_rate(db, from_currency)
        usd_per_to   = _get_usd_rate(db, to_currency)
        if usd_per_to <= 0:
            return 0.0
        return usd_per_from / usd_per_to
    finally:
        db.close()


def _get_usd_rate(db, currency_code: str) -> float:
    """USD value of one unit of currency_code.  USD itself = 1.0."""
    if currency_code == "USD":
        return 1.0
    bank = db.query(StateReserveBank).filter(
        StateReserveBank.currency_code == currency_code.upper()
    ).first()
    return bank.usd_per_unit if bank else 1.0


def forex_swap(
    player_id: int,
    from_currency: str,
    amount: float,
    to_currency: str,
) -> Tuple[bool, str, dict]:
    """
    Exchange `amount` of `from_currency` into `to_currency` at the live rate.
    Debits from_currency balance; credits to_currency balance.
    For USD: debits/credits player.cash_balance directly.
    Charges FOREX_FEE_RATE (0.2 %) in USD, deducted from the to_currency proceeds.
    """
    if amount <= 0:
        return False, "Amount must be positive.", {}
    if from_currency == to_currency:
        return False, "Source and target currency are the same.", {}

    from auth import get_db as auth_get_db, Player

    db       = get_db()
    auth_db  = auth_get_db()
    try:
        rate = _get_exchange_rate_internal(db, from_currency, to_currency)
        if rate <= 0:
            return False, f"Cannot determine exchange rate for {from_currency} → {to_currency}.", {}

        gross_out = amount * rate
        fee_in_to = gross_out * FOREX_FEE_RATE
        net_out   = gross_out - fee_in_to

        # Debit source
        ok, err = _debit_currency(db, auth_db, player_id, from_currency, amount)
        if not ok:
            return False, err, {}
        db.commit()
        auth_db.commit()

        # Credit destination
        _credit_currency(db, auth_db, player_id, to_currency, net_out)
        db.commit()
        auth_db.commit()

        # Record forex trade
        trade = ForexTrade(
            player_id     = player_id,
            from_currency = from_currency,
            to_currency   = to_currency,
            amount_from   = amount,
            amount_to     = net_out,
            exchange_rate = rate,
            fee_usd       = fee_in_to * _get_usd_rate(db, to_currency),
        )
        db.add(trade)
        # Update bank forex volume stats
        for code in (from_currency, to_currency):
            if code != "USD":
                bank = db.query(StateReserveBank).filter(
                    StateReserveBank.currency_code == code
                ).first()
                if bank:
                    bank.total_forex_volume += amount * _get_usd_rate(db, from_currency)
        db.commit()

        return True, (
            f"Converted {amount:.4f} {from_currency} → {net_out:.4f} {to_currency} "
            f"(rate: {rate:.6f}, fee: {fee_in_to:.4f} {to_currency})."
        ), {
            "from_currency": from_currency, "to_currency": to_currency,
            "amount_from": amount, "amount_to": net_out,
            "rate": rate, "fee": fee_in_to,
        }

    except Exception as e:
        db.rollback()
        auth_db.rollback()
        return False, f"Forex error: {e}", {}
    finally:
        db.close()
        auth_db.close()


def _get_exchange_rate_internal(db, from_currency: str, to_currency: str) -> float:
    usd_from = _get_usd_rate(db, from_currency)
    usd_to   = _get_usd_rate(db, to_currency)
    return usd_from / usd_to if usd_to > 0 else 0.0


def _debit_currency(db, auth_db, player_id: int, currency_code: str, amount: float) -> Tuple[bool, str]:
    if currency_code == "USD":
        from auth import Player
        p = auth_db.query(Player).filter(Player.id == player_id).first()
        if not p or (p.cash_balance or 0.0) < amount:
            bal = p.cash_balance if p else 0.0
            return False, f"Insufficient USD: have ${bal:.2f}, need ${amount:.2f}."
        p.cash_balance -= amount
        return True, ""
    else:
        bal_row = db.query(PlayerCurrencyBalance).filter(
            PlayerCurrencyBalance.player_id     == player_id,
            PlayerCurrencyBalance.currency_code == currency_code,
        ).first()
        bal = bal_row.balance if bal_row else 0.0
        if bal < amount:
            return False, f"Insufficient {currency_code}: have {bal:.4f}, need {amount:.4f}."
        bal_row.balance  -= amount
        bal_row.total_spent += amount
        return True, ""


def _credit_currency(db, auth_db, player_id: int, currency_code: str, amount: float):
    if currency_code == "USD":
        from auth import Player
        p = auth_db.query(Player).filter(Player.id == player_id).first()
        if p:
            p.cash_balance = (p.cash_balance or 0.0) + amount
    else:
        _adjust_currency_balance(db, player_id, currency_code, amount)


# ==========================
# LEGAL TENDER
# ==========================

def get_player_legal_tender(player_id: int) -> str:
    """Return the player's chosen legal tender currency code, defaulting to 'USD'."""
    db = get_db()
    try:
        row = db.query(PlayerLegalTender).filter(
            PlayerLegalTender.player_id == player_id
        ).first()
        return row.currency_code if row else "USD"
    finally:
        db.close()


def set_player_legal_tender(player_id: int, currency_code: str) -> Tuple[bool, str]:
    """Change a player's legal tender. The currency must have an active reserve bank (or be USD)."""
    code = currency_code.upper()
    if code == "USD":
        db = get_db()
        try:
            row = db.query(PlayerLegalTender).filter(
                PlayerLegalTender.player_id == player_id
            ).first()
            if row:
                row.currency_code = "USD"
                row.changed_at    = datetime.utcnow()
            else:
                db.add(PlayerLegalTender(player_id=player_id, currency_code="USD"))
            db.commit()
            return True, "Legal tender set to USD (default game currency)."
        except Exception as e:
            db.rollback()
            return False, str(e)
        finally:
            db.close()

    db = get_db()
    try:
        bank = db.query(StateReserveBank).filter(
            StateReserveBank.currency_code == code
        ).first()
        if not bank:
            return False, f"No reserve bank found for '{code}'. Available: {_available_codes(db)}"

        row = db.query(PlayerLegalTender).filter(
            PlayerLegalTender.player_id == player_id
        ).first()
        if row:
            row.currency_code = code
            row.changed_at    = datetime.utcnow()
        else:
            db.add(PlayerLegalTender(player_id=player_id, currency_code=code))
        db.commit()
        return True, (
            f"Legal tender changed to {bank.flag_emoji} {bank.currency_name} ({code}). "
            f"Future income will be auto-converted at the live forex rate."
        )
    except Exception as e:
        db.rollback()
        return False, str(e)
    finally:
        db.close()


def _available_codes(db) -> List[str]:
    return ["USD"] + [b.currency_code for b in db.query(StateReserveBank).all()]


def convert_to_legal_tender(player_id: int, usd_amount: float) -> Tuple[float, str]:
    """
    Helper called by income functions: converts a USD amount to the player's
    legal tender at the live exchange rate.  Returns (converted_amount, currency_code).
    If the player uses USD (or conversion fails), returns the original amount.
    """
    code = get_player_legal_tender(player_id)
    if code == "USD":
        return usd_amount, "USD"
    rate = get_exchange_rate("USD", code)
    if rate <= 0:
        return usd_amount, "USD"
    converted = usd_amount * rate * (1.0 - FOREX_FEE_RATE)
    return converted, code


# ==========================
# READ HELPERS (used by UX)
# ==========================

def get_all_banks() -> List[dict]:
    db = get_db()
    try:
        banks = db.query(StateReserveBank).all()
        return [
            {
                "id": b.id, "code": b.currency_code, "name": b.currency_name,
                "symbol": b.currency_symbol, "flag": b.flag_emoji,
                "yield_pct": round(b.yield_rate * 100, 4),
                "usd_per_unit": b.usd_per_unit,
                "min_yield_pct": round(b.min_yield * 100, 4),
                "max_yield_pct": round(b.max_yield * 100, 4),
                "total_bonds": b.total_bonds_issued,
                "total_face_wsc": round(b.total_face_value_wsc, 2),
                "total_interest_paid": round(b.total_interest_paid, 4),
            }
            for b in banks
        ]
    finally:
        db.close()


def get_player_bonds(player_id: int) -> List[dict]:
    db = get_db()
    try:
        bonds = db.query(ReserveBankBond).filter(
            ReserveBankBond.holder_player_id == player_id,
            ReserveBankBond.status           == "active",
        ).all()
        result = []
        for bond in bonds:
            bank = db.query(StateReserveBank).filter(StateReserveBank.id == bond.bank_id).first()
            now  = datetime.utcnow()
            remaining_days = max((bond.matures_at - now).days, 0)
            remaining_years = max((bond.matures_at - now).total_seconds() / (365 * 86400), 0.0)
            price_factor = 1.0 + (bond.purchase_yield - bank.yield_rate) * remaining_years
            price_factor = max(0.50, min(2.0, price_factor))
            result.append({
                "id": bond.id,
                "currency_code": bank.currency_code,
                "currency_symbol": bank.currency_symbol,
                "flag": bank.flag_emoji,
                "face_value_wsc": round(bond.face_value_wsc, 4),
                "purchase_yield_pct": round(bond.purchase_yield * 100, 4),
                "current_yield_pct": round(bank.yield_rate * 100, 4),
                "interest_accrued": round(bond.interest_accrued, 6),
                "maturity_days": bond.maturity_days,
                "matures_at": bond.matures_at.strftime("%Y-%m-%d"),
                "remaining_days": remaining_days,
                "sell_value_wsc": round(bond.face_value_wsc * price_factor, 4),
                "price_factor": round(price_factor, 4),
            })
        return result
    finally:
        db.close()


def get_player_currency_balances(player_id: int) -> List[dict]:
    db = get_db()
    try:
        rows = db.query(PlayerCurrencyBalance).filter(
            PlayerCurrencyBalance.player_id == player_id,
            PlayerCurrencyBalance.balance   != 0.0,
        ).all()
        result = []
        for r in rows:
            bank = db.query(StateReserveBank).filter(
                StateReserveBank.currency_code == r.currency_code
            ).first()
            usd_val = r.balance * _get_usd_rate(db, r.currency_code)
            result.append({
                "currency_code": r.currency_code,
                "currency_symbol": bank.currency_symbol if bank else "",
                "flag": bank.flag_emoji if bank else "🏦",
                "balance": round(r.balance, 4),
                "usd_value": round(usd_val, 2),
                "total_earned": round(r.total_earned, 4),
            })
        return result
    finally:
        db.close()


def get_recent_forex_trades(limit: int = 50) -> List[dict]:
    db = get_db()
    try:
        trades = db.query(ForexTrade).order_by(
            ForexTrade.executed_at.desc()
        ).limit(limit).all()
        return [
            {
                "player_id": t.player_id,
                "from_currency": t.from_currency,
                "to_currency": t.to_currency,
                "amount_from": round(t.amount_from, 4),
                "amount_to": round(t.amount_to, 4),
                "rate": round(t.exchange_rate, 6),
                "fee_usd": round(t.fee_usd, 4),
                "executed_at": t.executed_at.strftime("%Y-%m-%d %H:%M"),
            }
            for t in trades
        ]
    finally:
        db.close()


def get_yield_history(bank_id: int, limit: int = 168) -> List[dict]:
    """Up to 168 hourly snapshots (7 days) for charting."""
    db = get_db()
    try:
        rows = db.query(BondYieldHistory).filter(
            BondYieldHistory.bank_id == bank_id
        ).order_by(BondYieldHistory.recorded_at.desc()).limit(limit).all()
        return [
            {
                "yield_pct": round(r.yield_rate * 100, 4),
                "usd_per_unit": round(r.usd_per_unit, 6),
                "recorded_at": r.recorded_at.strftime("%Y-%m-%d %H:%M"),
            }
            for r in reversed(rows)
        ]
    finally:
        db.close()


__all__ = [
    "initialize", "tick",
    "purchase_bond", "sell_bond",
    "forex_swap", "get_exchange_rate",
    "get_player_legal_tender", "set_player_legal_tender", "convert_to_legal_tender",
    "get_all_banks", "get_player_bonds", "get_player_currency_balances",
    "get_recent_forex_trades", "get_yield_history",
    "get_wsc_quote", "get_native_quote",
    "StateReserveBank", "ReserveBankBond", "PlayerLegalTender",
    "PlayerCurrencyBalance", "ForexTrade", "BondYieldHistory",
    "get_db",
]
