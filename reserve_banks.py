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

from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# ==========================
# DATABASE
# ==========================

from database import reserve_engine as engine, ReserveSessionLocal as SessionLocal
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


class BankReserveBalance(Base):
    """
    Foreign-currency reserves held by a reserve bank.
    One row per (bank, foreign_currency) pair.

    Banks accumulate reserves when:
      - They receive USD/foreign currency as the settlement leg of a player
        income conversion (e.g. USD income → JPY: JPY bank gains USD reserves).
      - They collect forex fees (in their own currency).
      - They receive interest on bonds they hold from other banks.
      - They complete an inter-bank bond swap (receive another currency).

    Banks consume reserves when:
      - A player with their legal tender pays someone in a different currency.
      - They redeem bonds they hold from other banks.
    """
    __tablename__ = "bank_reserve_balances"

    id            = Column(Integer, primary_key=True, index=True)
    bank_id       = Column(Integer, index=True, nullable=False)   # the holding bank
    currency_code = Column(String(8), index=True, nullable=False) # currency being held
    balance       = Column(Float, default=0.0)
    total_received= Column(Float, default=0.0)
    total_paid    = Column(Float, default=0.0)
    updated_at    = Column(DateTime, default=datetime.utcnow)


class BankDebt(Base):
    """
    Inter-bank debt created when a bank settled a trade it didn't have reserves for.
    The debtor bank must repay by selling its own bonds to the creditor bank.

    Unpaid debt raises the debtor bank's yield_rate (making bonds more attractive
    so investors will fund the shortfall).  This is the same mechanism central
    banks use: high rates attract capital inflows which cover balance-of-payments gaps.
    """
    __tablename__ = "bank_debts"

    id                  = Column(Integer, primary_key=True, index=True)
    debtor_bank_id      = Column(Integer, index=True, nullable=False)
    creditor_currency   = Column(String(8), nullable=False)  # currency owed to creditor
    amount_owed         = Column(Float, nullable=False)
    created_at          = Column(DateTime, default=datetime.utcnow)
    last_settled_at     = Column(DateTime, nullable=True)
    is_settled          = Column(Boolean, default=False)


class InterbankTrade(Base):
    """
    Record of every bank-to-bank bond swap / currency settlement.
    Shown in the forex dashboard trade feed instead of manual player swaps.
    """
    __tablename__ = "interbank_trades"

    id                  = Column(Integer, primary_key=True, index=True)
    buyer_bank_code     = Column(String(8), nullable=False)   # who buys bonds
    seller_bank_code    = Column(String(8), nullable=False)   # who sells bonds
    bond_currency       = Column(String(8), nullable=False)   # which bank's bonds
    face_value_usd      = Column(Float, nullable=False)       # USD equiv of bonds swapped
    consideration_curr  = Column(String(8), nullable=False)   # currency paid in return
    consideration_amount= Column(Float, nullable=False)
    trigger             = Column(String, default="auto")      # "auto" | "debt_repay"
    executed_at         = Column(DateTime, default=datetime.utcnow)


# ── Constants for inter-bank management ──────────────────────────────────────
BANK_MIN_RESERVE_RATIO  = 0.05   # trigger interbank swap when reserves < 5% of outstanding
DEBT_YIELD_PENALTY      = 0.001  # per $1 000 of net debt, yield rises by 0.1 %
DEBT_PENALTY_NORMALI    = 1000.0

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
        # Inter-bank settlement runs after all yield/FX adjustments are done
        _tick_interbank_settlement(db)
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
# INTER-BANK RESERVE HELPERS
# ==========================

def _get_or_create_bank_reserve(db, bank_id: int, currency_code: str) -> BankReserveBalance:
    r = db.query(BankReserveBalance).filter(
        BankReserveBalance.bank_id       == bank_id,
        BankReserveBalance.currency_code == currency_code,
    ).first()
    if not r:
        r = BankReserveBalance(bank_id=bank_id, currency_code=currency_code)
        db.add(r)
        db.flush()
    return r


def _add_bank_reserve(db, bank_id: int, currency_code: str, amount: float):
    r = _get_or_create_bank_reserve(db, bank_id, currency_code)
    r.balance       += amount
    r.total_received += max(amount, 0.0)
    r.total_paid     += max(-amount, 0.0)
    r.updated_at     = datetime.utcnow()


def _debit_bank_reserve(db, bank_id: int, currency_code: str, amount: float) -> bool:
    """Debit `amount` from a bank's reserves. Returns True if sufficient, False if not."""
    r = _get_or_create_bank_reserve(db, bank_id, currency_code)
    if r.balance >= amount:
        r.balance   -= amount
        r.total_paid += amount
        r.updated_at  = datetime.utcnow()
        return True
    return False


def _record_bank_debt(db, debtor_bank_id: int, creditor_currency: str, amount: float):
    """Record that the debtor bank owes `amount` of creditor's currency."""
    debt = db.query(BankDebt).filter(
        BankDebt.debtor_bank_id    == debtor_bank_id,
        BankDebt.creditor_currency == creditor_currency,
        BankDebt.is_settled        == False,
    ).first()
    if debt:
        debt.amount_owed += amount
    else:
        debt = BankDebt(
            debtor_bank_id    = debtor_bank_id,
            creditor_currency = creditor_currency,
            amount_owed       = amount,
        )
        db.add(debt)
    db.flush()


# ==========================
# INTER-BANK BOND SWAP (automatic)
# ==========================

def _interbank_bond_swap(db, buyer_bank: StateReserveBank, seller_bank: StateReserveBank, usd_equiv: float):
    """
    Buyer bank acquires `usd_equiv` worth of seller bank's currency reserves
    by sending its own bonds to the seller bank (the seller bank earns interest
    on those bonds, denominated in the buyer bank's currency).

    Example: JPY bank (buyer) swaps with USD bank (seller):
      - JPY bank issues bonds worth `usd_equiv` in JPY face value to USD bank.
      - USD bank credits JPY bank with `usd_equiv` in USD.
      - USD bank earns JPY interest on those bonds → appreciates JPY (positive demand).
      - JPY bank's yield falls slightly (more demand for JPY bonds from USD bank).
    """
    usd_per_buyer = buyer_bank.usd_per_unit   # e.g. 0.0067 for JPY
    if usd_per_buyer <= 0:
        return

    # How many of buyer's currency does usd_equiv buy?
    buyer_amount = usd_equiv / usd_per_buyer

    # Seller bank gets buyer bank's bonds → earns buyer-currency interest → holds buyer-currency reserves
    seller_interest = buyer_amount * buyer_bank.yield_rate
    _add_bank_reserve(db, seller_bank.id, buyer_bank.currency_code, seller_interest)

    # Buyer bank gets USD (seller's currency) reserves
    usd_per_seller = seller_bank.usd_per_unit
    seller_amount   = usd_equiv / usd_per_seller if usd_per_seller > 0 else usd_equiv
    _add_bank_reserve(db, buyer_bank.id, seller_bank.currency_code, seller_amount)

    # Demand effects: USD bank just bought JPY bonds → positive demand for JPY bonds
    buyer_bank.net_demand_wsc  += usd_equiv   # JPY bond demand up → yield falls
    seller_bank.net_demand_wsc -= usd_equiv * 0.1  # small negative on USD (capital outflow)

    # Record inter-bank trade
    trade = InterbankTrade(
        buyer_bank_code      = seller_bank.currency_code,   # seller bank bought buyer's bonds
        seller_bank_code     = buyer_bank.currency_code,    # buyer bank sold its own bonds
        bond_currency        = buyer_bank.currency_code,
        face_value_usd       = usd_equiv,
        consideration_curr   = seller_bank.currency_code,
        consideration_amount = seller_amount,
        trigger              = "auto",
    )
    db.add(trade)


def _tick_interbank_settlement(db):
    """
    Called each hourly tick. For every bank whose foreign reserves have fallen
    below BANK_MIN_RESERVE_RATIO of outstanding bond liabilities, trigger a
    swap with the relevant foreign bank.

    Also applies a yield penalty for outstanding debt
    (high debt → higher yield to attract more bond buyers).
    """
    banks = db.query(StateReserveBank).all()
    bank_map = {b.currency_code: b for b in banks}

    for bank in banks:
        # Debt penalty: outstanding debt pushes yield up
        total_debt_usd = 0.0
        debts = db.query(BankDebt).filter(
            BankDebt.debtor_bank_id == bank.id,
            BankDebt.is_settled     == False,
        ).all()
        for d in debts:
            cred_bank = bank_map.get(d.creditor_currency)
            usd_per_cred = cred_bank.usd_per_unit if cred_bank else 1.0
            total_debt_usd += d.amount_owed * usd_per_cred

        if total_debt_usd > 0:
            penalty = (total_debt_usd / DEBT_PENALTY_NORMALI) * DEBT_YIELD_PENALTY
            bank.yield_rate = min(bank.max_yield, bank.yield_rate + penalty)

        # Check if reserves are below the minimum ratio for any foreign currency
        outstanding_usd = bank.total_face_value_wsc  # proxy for liabilities
        if outstanding_usd <= 0:
            continue

        foreign_reserves = db.query(BankReserveBalance).filter(
            BankReserveBalance.bank_id == bank.id,
        ).all()
        for reserve in foreign_reserves:
            if reserve.currency_code == bank.currency_code:
                continue  # own-currency reserves are unlimited
            usd_val = reserve.balance * _get_usd_rate(db, reserve.currency_code)
            if usd_val < outstanding_usd * BANK_MIN_RESERVE_RATIO:
                # Trigger swap: acquire more of this currency from the issuing bank
                shortfall_usd = outstanding_usd * BANK_MIN_RESERVE_RATIO - usd_val
                target_bank   = bank_map.get(reserve.currency_code)
                if target_bank:
                    _interbank_bond_swap(db, bank, target_bank, min(shortfall_usd, outstanding_usd * 0.05))


# ==========================
# PLAYER INCOME CONVERSION  (replaces player-facing forex_swap)
# ==========================

def process_income_conversion(player_id: int, usd_amount: float) -> Tuple[float, str]:
    """
    Convert USD income to the player's legal tender via the reserve bank system.

    This is called automatically when any USD-denominated income reaches a player.
    The conversion is never initiated by the player directly — the reserve bank does it.

    Flow (example: player's legal tender = JPY, income = $100 USD):
      1. JPY bank receives $100 USD → adds to its USD reserves.
      2. JPY bank creates ¥X = 100 / usd_per_unit at current rate (no reserve needed —
         the bank is the issuer of its own currency).
      3. 0.2% fee kept by JPY bank as own-currency reserves.
      4. Player receives net ¥X in their PlayerCurrencyBalance row.
      5. ForexTrade record created for the dashboard feed.
      6. Bank's net_demand_wsc adjusted (USD inflow → positive demand for JPY bonds).

    Returns (converted_amount, currency_code).
    """
    code = get_player_legal_tender(player_id)
    if code == "USD" or usd_amount <= 0:
        return usd_amount, "USD"

    db = get_db()
    try:
        bank = db.query(StateReserveBank).filter(
            StateReserveBank.currency_code == code
        ).first()
        if not bank:
            return usd_amount, "USD"

        # Gross foreign amount at current rate
        gross_foreign = usd_amount / bank.usd_per_unit
        fee_foreign   = gross_foreign * FOREX_FEE_RATE
        net_foreign   = gross_foreign - fee_foreign

        # JPY bank gains USD reserves (it just sold JPY to the player)
        _add_bank_reserve(db, bank.id, "USD", usd_amount)
        # JPY bank earns fee in own currency
        _add_bank_reserve(db, bank.id, code, fee_foreign)

        # Credit player's foreign currency balance
        _adjust_currency_balance(db, player_id, code, net_foreign)

        # Demand signal: USD inflow = capital coming IN to this bank's currency = positive demand
        bank.net_demand_wsc += usd_amount

        # Audit
        db.add(ForexTrade(
            player_id     = player_id,
            from_currency = "USD",
            to_currency   = code,
            amount_from   = usd_amount,
            amount_to     = net_foreign,
            exchange_rate = 1.0 / bank.usd_per_unit,
            fee_usd       = fee_foreign * bank.usd_per_unit,
        ))
        db.commit()
        return net_foreign, code

    except Exception as e:
        db.rollback()
        print(f"[ReserveBanks] Income conversion error: {e}")
        return usd_amount, "USD"
    finally:
        db.close()


def process_cross_currency_payment(
    payer_id: int,
    recipient_currency: str,
    amount_in_payer_currency: float,
) -> Tuple[bool, float, str]:
    """
    Settle a payment where the payer's legal tender differs from the recipient's.
    Called when a player with JPY legal tender pays someone who uses GBP.

    Flow:
      1. Debit payer's JPY balance.
      2. JPY bank needs to provide GBP to the recipient.
      3. If JPY bank has sufficient GBP reserves: pays from reserves.
      4. If not: records a GBP debt (yield penalty applies next tick) and still pays.
         The deficit is covered by the next interbank bond swap in _tick_interbank_settlement.

    Returns (success, amount_in_recipient_currency, recipient_currency).
    """
    db = get_db()
    try:
        payer_code = get_player_legal_tender(payer_id)
        if payer_code == recipient_currency:
            return True, amount_in_payer_currency, recipient_currency

        payer_bank = db.query(StateReserveBank).filter(
            StateReserveBank.currency_code == payer_code
        ).first() if payer_code != "USD" else None

        # Convert payer amount → USD → recipient amount
        payer_usd_rate = _get_usd_rate(db, payer_code)
        recip_usd_rate = _get_usd_rate(db, recipient_currency)
        if payer_usd_rate <= 0 or recip_usd_rate <= 0:
            return False, 0.0, recipient_currency

        usd_value     = amount_in_payer_currency * payer_usd_rate
        fee_usd       = usd_value * FOREX_FEE_RATE
        net_usd       = usd_value - fee_usd
        recip_amount  = net_usd / recip_usd_rate

        # Debit payer
        bal = db.query(PlayerCurrencyBalance).filter(
            PlayerCurrencyBalance.player_id     == payer_id,
            PlayerCurrencyBalance.currency_code == payer_code,
        ).first()
        payer_bal = bal.balance if bal else 0.0
        if payer_bal < amount_in_payer_currency:
            return False, 0.0, recipient_currency

        _adjust_currency_balance(db, payer_id, payer_code, -amount_in_payer_currency)

        # Payer's bank needs to provide recipient currency
        if payer_bank:
            has_reserves = _debit_bank_reserve(db, payer_bank.id, recipient_currency, recip_amount)
            if not has_reserves:
                # Bank creates debt; will be settled next tick via bond swap
                _record_bank_debt(db, payer_bank.id, recipient_currency, recip_amount)
                # Still provide the funds (central banks can run temporary overdrafts)

            # Payer bank keeps USD in reserves (receives value from the payment)
            _add_bank_reserve(db, payer_bank.id, "USD", usd_value)
            # Fee kept as own currency reserves
            _add_bank_reserve(db, payer_bank.id, payer_code, fee_usd / payer_usd_rate)

            payer_bank.net_demand_wsc -= usd_value  # capital outflow → negative demand

        db.add(ForexTrade(
            player_id     = payer_id,
            from_currency = payer_code,
            to_currency   = recipient_currency,
            amount_from   = amount_in_payer_currency,
            amount_to     = recip_amount,
            exchange_rate = payer_usd_rate / recip_usd_rate,
            fee_usd       = fee_usd,
        ))
        db.commit()
        return True, recip_amount, recipient_currency

    except Exception as e:
        db.rollback()
        print(f"[ReserveBanks] Cross-currency payment error: {e}")
        return False, 0.0, recipient_currency
    finally:
        db.close()


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


def forex_swap(player_id: int, from_currency: str, amount: float, to_currency: str) -> Tuple[bool, str, dict]:
    """
    Removed — players do not manually swap currencies.
    All forex is handled automatically by the reserve bank system:
      - Income in USD is auto-converted to the player's legal tender via process_income_conversion().
      - Cross-currency payments are settled via process_cross_currency_payment().
    Change your legal tender on the Corporate Actions dashboard.
    """
    return False, (
        "Manual forex swaps are not available. "
        "Currency conversion happens automatically when you receive income or make payments. "
        "Use the Corporate Actions dashboard to change your legal tender."
    ), {}


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
    Helper called by income functions: convert USD income to the player's legal tender.
    Delegates to process_income_conversion() which runs the full inter-bank settlement flow.
    Returns (converted_amount, currency_code).
    """
    return process_income_conversion(player_id, usd_amount)


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


def get_bank_reserves(bank_id: int) -> List[dict]:
    """Return the foreign-currency reserves held by a specific bank."""
    db = get_db()
    try:
        rows = db.query(BankReserveBalance).filter(
            BankReserveBalance.bank_id == bank_id,
            BankReserveBalance.balance != 0.0,
        ).all()
        return [
            {
                "currency_code": r.currency_code,
                "balance": round(r.balance, 4),
                "total_received": round(r.total_received, 4),
                "total_paid": round(r.total_paid, 4),
            }
            for r in rows
        ]
    finally:
        db.close()


def get_all_bank_reserves() -> List[dict]:
    """Return reserves for all banks (for the forex dashboard overview)."""
    db = get_db()
    try:
        banks = db.query(StateReserveBank).all()
        result = []
        for bank in banks:
            reserves = db.query(BankReserveBalance).filter(
                BankReserveBalance.bank_id == bank.id,
                BankReserveBalance.balance >  0.0,
            ).all()
            debts = db.query(BankDebt).filter(
                BankDebt.debtor_bank_id == bank.id,
                BankDebt.is_settled     == False,
            ).all()
            total_debt_usd = sum(
                d.amount_owed * _get_usd_rate(db, d.creditor_currency) for d in debts
            )
            result.append({
                "bank_code": bank.currency_code,
                "bank_name": bank.currency_name,
                "flag": bank.flag_emoji,
                "yield_pct": round(bank.yield_rate * 100, 4),
                "usd_per_unit": bank.usd_per_unit,
                "reserves": [
                    {
                        "currency_code": r.currency_code,
                        "balance": round(r.balance, 4),
                    }
                    for r in reserves
                ],
                "total_debt_usd": round(total_debt_usd, 2),
            })
        return result
    finally:
        db.close()


def get_interbank_trades(limit: int = 50) -> List[dict]:
    """Return recent inter-bank settlement trades for the forex dashboard feed."""
    db = get_db()
    try:
        rows = db.query(InterbankTrade).order_by(
            InterbankTrade.executed_at.desc()
        ).limit(limit).all()
        return [
            {
                "buyer_bank":          r.buyer_bank_code,
                "seller_bank":         r.seller_bank_code,
                "bond_currency":       r.bond_currency,
                "face_value_usd":      round(r.face_value_usd, 2),
                "consideration_curr":  r.consideration_curr,
                "consideration_amount":round(r.consideration_amount, 4),
                "trigger":             r.trigger,
                "executed_at":         r.executed_at.strftime("%Y-%m-%d %H:%M"),
            }
            for r in rows
        ]
    finally:
        db.close()


__all__ = [
    "initialize", "tick",
    "purchase_bond", "sell_bond",
    "forex_swap",                                         # stub — always returns error
    "process_income_conversion", "process_cross_currency_payment",
    "get_exchange_rate",
    "get_player_legal_tender", "set_player_legal_tender", "convert_to_legal_tender",
    "get_all_banks", "get_player_bonds", "get_player_currency_balances",
    "get_recent_forex_trades", "get_yield_history",
    "get_bank_reserves", "get_all_bank_reserves", "get_interbank_trades",
    "StateReserveBank", "ReserveBankBond", "PlayerLegalTender",
    "PlayerCurrencyBalance", "ForexTrade", "BondYieldHistory",
    "BankReserveBalance", "BankDebt", "InterbankTrade",
    "get_db",
]
