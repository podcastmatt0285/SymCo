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

USD is a reserve currency like all others, backed by the Federal Reserve of
Wadsworth and stored in PlayerCurrencyBalance just like JPY, EUR, etc.
All currencies require a reserve bank.

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
  - Available maturities: 7 / 14 / 30 calendar days (player bonds).
  - Interbank swap bonds use a fixed 3-day maturity and pay no interest.
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

from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime, text, update as sa_update
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
FX_YIELD_LINK      = 0.02          # usd_per_unit fractional change per 1 % yield Δ (4× more sensitive)

# Direct FX impact from bond market actions (buys, sells, calls).
# Each $1 of bond activity moves usd_per_unit by this fraction of the current rate, immediately.
# e.g. 0.00001 → a $10 000 bond purchase appreciates the currency by ~0.1%.
FX_DIRECT_BOND_LINK = 0.00001      # fractional usd_per_unit change per $1 of bond face value

FOREX_FEE_RATE     = 0.002         # 0.2 % fee on each forex conversion
BOND_MATURITIES             = [7, 14, 30]  # calendar days available to players
INTERBANK_BOND_MATURITY_DAYS = 3           # interbank swap bonds mature after 3 days

# Early redemption: 1.5 % flat fee if a bond is sold within the first 7 days.
BOND_EARLY_REDEMPTION_DAYS = 7
BOND_EARLY_REDEMPTION_FEE  = 0.015   # fraction of face value (in foreign currency)

# Bank call provision: if the current yield falls to ≤ BOND_CALL_YIELD_THRESHOLD
# fraction of the purchase yield, the bank may call (force-redeem) the bond at a
# small premium (BOND_CALL_PREMIUM) to compensate the holder.
BOND_CALL_YIELD_THRESHOLD = 0.40   # called when rate ≤ 40 % of purchase yield
BOND_CALL_PREMIUM         = 0.03   # 3 % bonus on face value (in foreign currency)

# Daily WSC liquidity swap: reserve banks convert accumulated WSC holdings to
# currency reserves once per day.  Banks with urgent reserve shortfalls earn a
# small premium to attract liquidity from WSC-rich banks.
WSC_DAILY_SWAP_TICKS      = 17280   # 24 h × 720 ticks/h
DAILY_SWAP_URGENCY_PREMIUM = 1.005  # 0.5 % premium paid by a bank urgently needing reserves

# Default reserve banks seeded on initialize()
DEFAULT_BANKS = [
    # code, name, symbol, flag, initial_yield, usd_per_unit, min_yield, max_yield
    ("USD", "Federal Reserve of Wadsworth",      "$",  "🇺🇸", 0.053,  1.000,  -0.005, 0.25),
    ("JPY", "Bank of Wadsworth Japan",           "¥",  "🇯🇵", 0.001,  0.0067, -0.030, 0.30),
    ("MXP", "Banco de Reserva Wadsworth",        "M$", "🇲🇽", 0.080,  0.058,  -0.020, 0.80),
    ("GBP", "Wadsworth Bank of England",         "£",  "🇬🇧", 0.045,  1.270,  -0.030, 0.40),
    ("CHF", "Wadsworth National Bank",           "Fr", "🇨🇭", 0.015,  1.120,  -0.050, 0.30),
    ("CNY", "People's Reserve Bank of Wadsworth","¥",  "🇨🇳", 0.025,  0.138,  -0.010, 0.45),
    ("EUR", "Wadsworth Central Bank",            "€",  "🇪🇺", 0.030,  1.080,  -0.030, 0.40),
    ("INR", "Reserve Bank of Wadsworth India",   "₹",  "🇮🇳", 0.065,  0.012,  -0.010, 0.60),
    ("RUB", "Wadsworth Central Reserve Bank",    "₽",  "🇷🇺", 0.160,  0.011,   0.010, 0.99),
    ("KRW", "Bank of Wadsworth Korea",           "₩",  "🇰🇷", 0.035,  0.00073,-0.020, 0.45),
    ("ZAR", "Wadsworth South African Reserve Bank","R", "🇿🇦", 0.085,  0.055,  -0.010, 0.70),
    ("BRL", "Central Bank of Wadsworth Brazil",  "R$", "🇧🇷", 0.105,  0.180,  -0.010, 0.85),
    ("TRY", "Central Bank of the Wadsworth Republic","₺","🇹🇷",0.400,  0.029,   0.030, 0.99),
    ("SAR", "Wadsworth Saudi Central Bank",      "﷼",  "🇸🇦", 0.050,  0.267,  -0.010, 0.25),
    ("AED", "Central Bank of Wadsworth UAE",     "د.إ","🇦🇪", 0.040,  0.272,  -0.010, 0.25),
    ("ANA", "Sovereign Reserve Blunt Spliff of Anacostia", "{J}", "🌿", 4.20,  10.00, -1.12, 4.20),
]

# How long a player must wait between legal-tender switches (days).
TENDER_SWITCH_COOLDOWN_DAYS = 7

# One-time conversion cost charged on the player's EXISTING foreign-currency
# balance whenever they switch away from a non-USD tender.  The fee is taken
# by the reserve bank as a "repatriation" cost.
TENDER_SWITCH_FEE_RATE = 0.02   # 2 % of current foreign balance

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

    # WSC accumulated from bond sales, pending daily liquidity conversion
    wsc_holdings          = Column(Float,   default=0.0)

    founded_at       = Column(DateTime, default=datetime.utcnow)


class ReserveBankBond(Base):
    """A bond held by a player in a specific reserve bank."""
    __tablename__ = "reserve_bank_bonds"

    id               = Column(Integer, primary_key=True, index=True)
    bank_id          = Column(Integer, index=True,  nullable=False)
    holder_player_id = Column(Integer, index=True,  nullable=False)
    face_value_wsc   = Column(Float,   nullable=False)   # WSC paid at purchase
    purchase_yield   = Column(Float,   nullable=False)   # yield locked at issuance
    purchase_fx_rate = Column(Float,   default=None)     # bank.usd_per_unit locked at purchase
    maturity_days    = Column(Integer, nullable=False)   # 30 / 90 / 180 / 365
    purchased_at     = Column(DateTime, default=datetime.utcnow)
    matures_at       = Column(DateTime, nullable=False)
    interest_accrued = Column(Float,   default=0.0)      # in the bank's own currency
    total_interest_paid = Column(Float, default=0.0)
    status           = Column(String,  default="active") # active / matured / sold / called


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

# ── Column migrations ─────────────────────────────────────────────────────────
# create_all only adds missing *tables*, not missing columns in existing tables.
# Run safe ALTER TABLE … ADD COLUMN IF NOT EXISTS for any columns added after
# initial deployment so the app doesn't crash on startup after a code update.
def _run_column_migrations():
    with engine.connect() as _conn:
        _conn.execute(text(
            "ALTER TABLE reserve_bank_bonds "
            "ADD COLUMN IF NOT EXISTS purchase_fx_rate DOUBLE PRECISION DEFAULT NULL"
        ))
        _conn.commit()

try:
    _run_column_migrations()
except Exception as _mig_err:
    print(f"[ReserveBanks] Column migration warning: {_mig_err}")


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
    from database import run_ddl_migration
    run_ddl_migration(
        engine,
        "ALTER TABLE state_reserve_banks"
        " ADD COLUMN IF NOT EXISTS wsc_holdings FLOAT DEFAULT 0.0",
        admin_env_var="RESERVE_DATABASE_ADMIN_URL",
    )

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
            else:
                # Always sync yield bands from DEFAULT_BANKS so widened limits take
                # effect on existing databases without a manual SQL migration.
                exists.min_yield = min_y
                exists.max_yield = max_y
                # Clamp yield_rate into the new band in case it was already at an
                # old boundary that falls outside the new range.
                exists.yield_rate = max(min_y, min(max_y, exists.yield_rate))
        db.commit()
        print(f"[ReserveBanks] {len(DEFAULT_BANKS)} banks seeded/verified (yield bands synced).")
    except Exception as e:
        db.rollback()
        print(f"[ReserveBanks] Initialize error: {e}")
    finally:
        db.close()


# ==========================
# TICK (called hourly by app)
# ==========================

def tick(app_tick: int, now: datetime):
    """Hourly housekeeping: accrue bond interest, adjust yields + FX rates, snapshot history."""
    if app_tick % RESERVE_BANKS_TICK_INTERVAL != 0:
        return

    db = get_db()
    try:
        banks = db.query(StateReserveBank).all()
        for bank in banks:
            _accrue_interest(db, bank, now)
            _adjust_yield_and_fx(db, bank)
            _call_bonds_if_needed(db, bank)
            _mature_bonds(db, bank, now)
            _snapshot_history(db, bank, now)
        # Inter-bank settlement runs after all yield/FX adjustments are done
        _tick_interbank_settlement(db)
        # Daily WSC → currency liquidity swap (once per 24 h)
        if app_tick % WSC_DAILY_SWAP_TICKS == 0:
            _daily_wsc_liquidity_swap(db)
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
        # Interbank bonds (holder_player_id == 0) carry no interest — they are
        # purely a reserve-management instrument and will be expired by _mature_bonds.
        if bond.holder_player_id <= 0:
            continue

        # Hourly interest in the bank's own currency:
        #   face_value_wsc / usd_per_unit  → face value in bank currency (1 WSC = $1)
        #   × purchase_yield / TICKS_PER_YEAR → one hour's slice of the LOCKED annual rate
        #
        # FIX: use bond.purchase_yield (rate locked at issuance) NOT bank.yield_rate.
        # The coupon on a fixed-rate bond never changes after it is issued.
        hourly = bond.face_value_wsc / bank.usd_per_unit * bond.purchase_yield / TICKS_PER_YEAR

        # Credit (or debit) the player's currency balance.
        # Negative-yield bonds are unusual but legal; clamp the balance at zero so
        # a player can never owe currency back to the bank.
        actual_credit = hourly
        if hourly < 0:
            # Find out how much will actually be deducted (balance may already be 0)
            actual_credit = _get_clamp_amount(db, bond.holder_player_id, bank.currency_code, hourly)

        _adjust_currency_balance(
            db, bond.holder_player_id, bank.currency_code, hourly,
            floor=0.0 if hourly < 0 else None,
        )

        # FIX: only book the amount actually credited so interest_accrued stays in
        # sync with the player's real balance (previously negative hours were tracked
        # even when the floor prevented any deduction).
        bond.interest_accrued   += actual_credit
        bank.total_interest_paid += abs(actual_credit)


def _call_bonds_if_needed(db, bank: StateReserveBank):
    """
    Bank call provision: if the current yield has fallen to ≤ BOND_CALL_YIELD_THRESHOLD
    of a bond's purchase yield, the bank exercises its call option and force-redeems
    that bond at face value plus BOND_CALL_PREMIUM in the bank's currency.

    This prevents players from holding old high-yield bonds indefinitely after the bank
    has significantly cut its rate (just like callable bonds in real markets).
    """
    callable_bonds = db.query(ReserveBankBond).filter(
        ReserveBankBond.bank_id == bank.id,
        ReserveBankBond.status  == "active",
    ).all()

    for bond in callable_bonds:
        if bond.holder_player_id <= 0:
            continue  # never call interbank bonds
        if bond.purchase_yield <= 0:
            # Negative- or zero-yield bonds are never callable: there is no
            # interest-rate benefit for the bank to call a bond it is already
            # paying nothing (or receiving) for.
            continue
        # Only call when current yield is well below purchase yield
        if bank.yield_rate > bond.purchase_yield * BOND_CALL_YIELD_THRESHOLD:
            continue

        # FIX: call value uses purchase FX rate so the player is made whole on the
        # principal — same logic as maturity redemption.  The 3% premium is their
        # compensation for losing a high-yield position ahead of schedule.
        fx_at_purchase = bond.purchase_fx_rate or bank.usd_per_unit
        call_value     = bond.face_value_wsc * (1.0 + BOND_CALL_PREMIUM) / fx_at_purchase
        bond.status    = "called"
        bank.total_face_value_wsc = max(0.0, bank.total_face_value_wsc - bond.face_value_wsc)
        bank.wsc_holdings         = max(0.0, bank.wsc_holdings         - bond.face_value_wsc)
        # Negative demand: bank is effectively buying back the bond
        bank.net_demand_wsc -= bond.face_value_wsc
        # Immediate FX depreciation: forced redemption signals reduced demand for this currency.
        if bank.currency_code != "USD":
            bank.usd_per_unit = max(
                0.000001,
                bank.usd_per_unit - bond.face_value_wsc * FX_DIRECT_BOND_LINK * bank.usd_per_unit,
            )

        # Credit player: face value + call premium + accumulated interest
        total_call_payout = call_value + bond.interest_accrued
        _adjust_currency_balance(db, bond.holder_player_id, bank.currency_code, total_call_payout)
        try:
            from stats_ux import log_transaction as _lt
            _lt(bond.holder_player_id, "bond_called", "money",
                total_call_payout * bank.usd_per_unit,
                f"Bond called by {bank.currency_code} bank: {total_call_payout:.4f} {bank.currency_code} (face+premium+interest)",
                reference_id=str(bond.id))
        except Exception:
            pass
        print(f"[ReserveBanks] Bank {bank.currency_code} called bond #{bond.id} "
              f"(purchase yield {bond.purchase_yield:.4f}, current {bank.yield_rate:.4f}). "
              f"Player {bond.holder_player_id} received {call_value + bond.interest_accrued:.4f} "
              f"{bank.currency_code} (face + {BOND_CALL_PREMIUM*100:.0f}% premium + interest).")


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
    # USD is always pegged at 1.0 — its exchange rate never moves.
    if bank.currency_code != "USD":
        yield_change_pct = (new_yield - old_yield)   # e.g. -0.001 means yield fell 0.1 %
        fx_change = -yield_change_pct * FX_YIELD_LINK * bank.usd_per_unit
        bank.usd_per_unit = max(0.000001, bank.usd_per_unit + fx_change)
    else:
        bank.usd_per_unit = 1.0   # enforce peg


def _mature_bonds(db, bank: StateReserveBank, now: datetime):
    """Return face value in bank's own currency to players whose bonds have matured.

    Since 1 WSC = $1 (peg), the face value converts to bank currency at the current
    FX rate: foreign_return = face_value_wsc / bank.usd_per_unit.
    The bank is the issuer of its own currency so it can always satisfy this obligation.
    """
    matured = db.query(ReserveBankBond).filter(
        ReserveBankBond.bank_id    == bank.id,
        ReserveBankBond.status     == "active",
        ReserveBankBond.matures_at <= now,
    ).all()

    if not matured:
        return

    for bond in matured:
        bond.status = "matured"
        # Reduce outstanding liabilities so reserve-ratio checks stay accurate
        bank.total_face_value_wsc = max(0.0, bank.total_face_value_wsc - bond.face_value_wsc)
        # Reduce WSC holdings — this WSC is now being redeemed as bank currency
        bank.wsc_holdings = max(0.0, bank.wsc_holdings - bond.face_value_wsc)

        # Interbank bonds (holder_player_id == 0) have no player to pay out to.
        # They exist solely to throttle swap frequency; just expire them silently.
        if bond.holder_player_id <= 0:
            continue

        # Return face value in the bank's own currency using the FX rate that was
        # locked at purchase time.  This guarantees the player receives exactly the
        # same number of foreign-currency units they originally exchanged for the
        # bond — they bear no FX risk on the principal at maturity.
        # FIX: was using current bank.usd_per_unit, which silently exposed players
        # to principal loss/gain from FX moves they had no visibility into.
        fx_at_purchase = bond.purchase_fx_rate or bank.usd_per_unit  # fallback for old rows
        foreign_return = bond.face_value_wsc / fx_at_purchase
        _adjust_currency_balance(db, bond.holder_player_id, bank.currency_code, foreign_return)
        try:
            from stats_ux import log_transaction as _lt
            _lt(bond.holder_player_id, "bond_maturity", "money",
                foreign_return * bank.usd_per_unit,
                f"Bond matured: {foreign_return:.4f} {bank.currency_code} received",
                reference_id=str(bond.id))
        except Exception:
            pass


def _snapshot_history(db, bank: StateReserveBank, now: datetime):
    """Record hourly yield/FX snapshot for the dashboard chart. Prunes records older than 7 days."""
    snap = BondYieldHistory(
        bank_id      = bank.id,
        yield_rate   = bank.yield_rate,
        usd_per_unit = bank.usd_per_unit,
        recorded_at  = now,
    )
    db.add(snap)
    # Keep only the last 7 days of history (168 hourly snapshots per bank)
    cutoff = now - timedelta(days=7)
    db.query(BondYieldHistory).filter(
        BondYieldHistory.bank_id     == bank.id,
        BondYieldHistory.recorded_at <  cutoff,
    ).delete(synchronize_session=False)


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


def _get_clamp_amount(db, player_id: int, currency_code: str, amount: float) -> float:
    """Return how much of `amount` will actually be applied given a floor=0 clamp.

    Used by _accrue_interest to keep bond.interest_accrued in sync with what was
    really credited/debited — prevents bookkeeping drift on negative-yield bonds.
    """
    bal = _get_or_create_currency_balance(db, player_id, currency_code)
    return max(-bal.balance, amount)   # amount is negative; clamp at -balance


def _adjust_currency_balance(
    db, player_id: int, currency_code: str, amount: float, floor: float = None
):
    """Add (or subtract if negative) `amount` to a player's currency balance.

    If `floor` is provided the resulting balance is clamped to that value.
    Use floor=0.0 for negative-interest accrual so balances never go below zero.
    """
    bal = _get_or_create_currency_balance(db, player_id, currency_code)
    new_bal = bal.balance + amount
    if floor is not None:
        new_bal = max(floor, new_bal)
    effective_delta  = new_bal - bal.balance
    bal.balance      = new_bal
    bal.updated_at   = datetime.utcnow()
    if effective_delta > 0:
        bal.total_earned += effective_delta
    elif effective_delta < 0:
        bal.total_spent  += abs(effective_delta)


def _debit_currency_balance_atomic(
    db, player_id: int, currency_code: str, amount: float
) -> bool:
    """Atomically debit `amount` from a player's foreign-currency balance.

    Uses a SQL-level UPDATE … WHERE balance >= amount so concurrent requests
    cannot both pass a Python-level balance check and double-spend the same funds.
    Returns True on success, False if the balance was insufficient.
    """
    result = db.execute(
        sa_update(PlayerCurrencyBalance)
        .where(PlayerCurrencyBalance.player_id     == player_id)
        .where(PlayerCurrencyBalance.currency_code == currency_code)
        .where(PlayerCurrencyBalance.balance       >= amount)
        .values(
            balance     = PlayerCurrencyBalance.balance     - amount,
            total_spent = PlayerCurrencyBalance.total_spent + amount,
            updated_at  = datetime.utcnow(),
        )
    )
    return result.rowcount > 0


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

    # Seller bank acquires buyer bank's bonds at face value (full principal in buyer's currency).
    # The seller bank holds these as reserves — the bond face value, not just one period's interest,
    # represents the actual collateral backing the cross-currency settlement.
    _add_bank_reserve(db, seller_bank.id, buyer_bank.currency_code, buyer_amount)

    # Buyer bank gets USD (seller's currency) reserves
    usd_per_seller = seller_bank.usd_per_unit
    seller_amount   = usd_equiv / usd_per_seller if usd_per_seller > 0 else usd_equiv
    _add_bank_reserve(db, buyer_bank.id, seller_bank.currency_code, seller_amount)

    # Demand effects: USD bank just bought JPY bonds → positive demand for JPY bonds
    buyer_bank.net_demand_wsc  += usd_equiv   # JPY bond demand up → yield falls
    seller_bank.net_demand_wsc -= usd_equiv * 0.1  # small negative on USD (capital outflow)

    # Create a 3-day interbank bond on the buyer bank so _tick_interbank_settlement
    # will not trigger another swap for this bank until it matures.  holder_player_id=0
    # marks it as a system/interbank bond (no interest accrual, no payout on maturity).
    interbank_bond = ReserveBankBond(
        bank_id          = buyer_bank.id,
        holder_player_id = 0,
        face_value_wsc   = usd_equiv,
        purchase_yield   = buyer_bank.yield_rate,
        maturity_days    = INTERBANK_BOND_MATURITY_DAYS,
        purchased_at     = datetime.utcnow(),
        matures_at       = datetime.utcnow() + timedelta(days=INTERBANK_BOND_MATURITY_DAYS),
        interest_accrued = 0.0,
        status           = "active",
    )
    db.add(interbank_bond)

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

        # Only trigger a new swap if no active interbank bond (holder=0) exists for
        # this bank.  Interbank bonds are 3-day instruments; while one is active the
        # bank is already "in settlement" and should not compound yield suppression.
        active_interbank = db.query(ReserveBankBond).filter(
            ReserveBankBond.bank_id          == bank.id,
            ReserveBankBond.holder_player_id == 0,
            ReserveBankBond.status           == "active",
        ).first()
        if active_interbank:
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
                    break  # one swap per bank per settlement cycle


# ==========================
# DAILY WSC LIQUIDITY SWAP
# ==========================

def _daily_wsc_liquidity_swap(db):
    """
    Once per day each reserve bank converts its accumulated WSC holdings into
    currency reserves.  Since 1 WSC = $1 (peg), the conversion is:

        bank_currency_received = wsc_amount / bank.usd_per_unit

    Two paths, whichever offers more value to the selling bank:
      (A) Direct own-currency issuance: bank creates its own currency from WSC.
      (B) Inter-bank sale: sell WSC to the reserve bank that has the most
          urgent shortfall in the selling bank's currency.  That bank pays a
          DAILY_SWAP_URGENCY_PREMIUM (0.5 %) in its own currency to attract
          the liquidity.  The buying bank converts the WSC to its own currency
          and the selling bank keeps the buying bank's currency as reserves.

    Every swap is recorded as a ForexTrade (player_id=None = system operation).
    """
    banks     = db.query(StateReserveBank).all()
    bank_map  = {b.currency_code: b for b in banks}

    for bank in banks:
        if bank.wsc_holdings < 0.01:
            continue

        wsc = bank.wsc_holdings
        bank.wsc_holdings = 0.0

        # -- Find best inter-bank buyer -------------------------------------------
        best_buyer      = None
        best_gap_usd    = 0.0

        for other in banks:
            if other.id == bank.id or other.total_face_value_wsc <= 0:
                continue
            their_reserve = db.query(BankReserveBalance).filter(
                BankReserveBalance.bank_id       == other.id,
                BankReserveBalance.currency_code == bank.currency_code,
            ).first()
            reserve_usd = (their_reserve.balance * bank.usd_per_unit) if their_reserve else 0.0
            gap = max(0.0, other.total_face_value_wsc * BANK_MIN_RESERVE_RATIO - reserve_usd)
            if gap > best_gap_usd:
                best_gap_usd = gap
                best_buyer   = other

        if best_buyer and best_gap_usd > 0:
            # Path B: inter-bank sale — buyer pays a small premium in its own currency
            buyer_currency_per_wsc = (1.0 / best_buyer.usd_per_unit) * DAILY_SWAP_URGENCY_PREMIUM
            buyer_currency_received = wsc * buyer_currency_per_wsc

            # Selling bank gains buyer's currency as reserves
            _add_bank_reserve(db, bank.id, best_buyer.currency_code, buyer_currency_received)

            # Buying bank receives WSC and converts to its own currency (it is the issuer)
            buyer_own_gain = wsc / best_buyer.usd_per_unit
            _add_bank_reserve(db, best_buyer.id, best_buyer.currency_code, buyer_own_gain)

            db.add(ForexTrade(
                player_id     = None,
                from_currency = "WSC",
                to_currency   = best_buyer.currency_code,
                amount_from   = wsc,
                amount_to     = buyer_currency_received,
                exchange_rate = buyer_currency_per_wsc,
                fee_usd       = 0.0,
            ))
        else:
            # Path A: direct own-currency issuance (bank is the issuer, no limit)
            own_gain = wsc / bank.usd_per_unit
            _add_bank_reserve(db, bank.id, bank.currency_code, own_gain)

            db.add(ForexTrade(
                player_id     = None,
                from_currency = "WSC",
                to_currency   = bank.currency_code,
                amount_from   = wsc,
                amount_to     = own_gain,
                exchange_rate = 1.0 / bank.usd_per_unit,
                fee_usd       = 0.0,
            ))


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
    if usd_amount <= 0:
        return 0.0, "USD"

    code = get_player_legal_tender(player_id)

    if code == "USD":
        # USD is now a reserve currency stored in PlayerCurrencyBalance like all others.
        db = get_db()
        try:
            _adjust_currency_balance(db, player_id, "USD", usd_amount)
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"[ReserveBanks] USD income credit error (player {player_id}): {e}")
        finally:
            db.close()
        return usd_amount, "USD"

    db = get_db()
    try:
        bank = db.query(StateReserveBank).filter(
            StateReserveBank.currency_code == code
        ).first()
        if not bank:
            # Unknown tender — fall back to crediting USD
            _adjust_currency_balance(db, player_id, "USD", usd_amount)
            db.commit()
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

        # Atomically debit payer — SQL-level WHERE prevents TOCTOU double-spend.
        if not _debit_currency_balance_atomic(db, payer_id, payer_code, amount_in_payer_currency):
            return False, 0.0, recipient_currency

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
    stable_coin_symbol: str = "WSC",
) -> Tuple[bool, str]:
    """
    Buy a bond from the specified reserve bank using WSC or any comptroller
    stable coin.  When a comptroller coin is used (e.g. 'AQUA-JPY') the coin
    amount is converted to its USD-equivalent face value and deducted from the
    player's CityStableCoinBalance; bank stats are updated in WSC-equivalent
    terms so downstream interest accrual is unchanged.
    """
    if wsc_amount <= 0:
        return False, "Bond face value must be positive."
    if maturity_days not in BOND_MATURITIES:
        return False, f"Invalid maturity. Choose from {BOND_MATURITIES} days."

    from wallet import get_db as wallet_get_db, WSCWallet, sa_update
    use_wsc = (stable_coin_symbol.upper() == "WSC")

    db = get_db()
    wallet_db = wallet_get_db()
    try:
        bank = db.query(StateReserveBank).filter(
            StateReserveBank.currency_code == currency_code.upper()
        ).first()
        if not bank:
            return False, f"No reserve bank found for currency '{currency_code}'."

        if use_wsc:
            # ── WSC path (original behaviour) ──────────────────────────────
            face_value_usd = wsc_amount
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
            coin_db   = None
            coin_row  = None
        else:
            # ── Comptroller stable-coin path ────────────────────────────────
            from cities import get_db as cities_get_db, CityStableCoinBalance, CityBank, _get_peg_usd_per_unit
            sym = stable_coin_symbol.upper()
            peg = sym.split("-", 1)[1] if "-" in sym else sym
            usd_per_coin = _get_peg_usd_per_unit(peg)
            face_value_usd = wsc_amount * usd_per_coin   # USD-equivalent face value

            coin_db = cities_get_db()
            # Find the city bank that issued this coin
            city_bank = coin_db.query(CityBank).filter(
                CityBank.stable_coin_symbol == sym
            ).first()
            if not city_bank:
                coin_db.close()
                return False, f"No city bank found for stable coin '{sym}'."

            coin_row = coin_db.query(CityStableCoinBalance).filter(
                CityStableCoinBalance.player_id == player_id,
                CityStableCoinBalance.city_id   == city_bank.city_id,
            ).first()
            if not coin_row or (coin_row.balance or 0) < wsc_amount:
                have = coin_row.balance if coin_row else 0.0
                coin_db.close()
                return False, f"Insufficient {sym}: have {have:.4f}, need {wsc_amount:.4f}."

            coin_row.balance -= wsc_amount
            coin_db.commit()

        # ── Create bond ─────────────────────────────────────────────────────
        try:
            bond = ReserveBankBond(
                bank_id          = bank.id,
                holder_player_id = player_id,
                face_value_wsc   = face_value_usd,   # stored as USD-equiv for interest calc
                purchase_yield   = bank.yield_rate,
                purchase_fx_rate = bank.usd_per_unit,  # FX rate locked at issuance
                maturity_days    = maturity_days,
                matures_at       = datetime.utcnow() + timedelta(days=maturity_days),
            )
            db.add(bond)

            bank.total_bonds_issued   += 1
            bank.total_face_value_wsc += face_value_usd
            bank.net_demand_wsc       += face_value_usd
            bank.wsc_holdings         += face_value_usd
            # Immediate FX appreciation: bond purchase = capital inflow = stronger currency.
            if bank.currency_code != "USD":
                bank.usd_per_unit = max(
                    0.000001,
                    bank.usd_per_unit + face_value_usd * FX_DIRECT_BOND_LINK * bank.usd_per_unit,
                )

            db.commit()
        except Exception as bond_err:
            db.rollback()
            # Refund whichever coin was deducted
            if use_wsc:
                wallet_db.execute(
                    sa_update(WSCWallet)
                    .where(WSCWallet.player_id == player_id)
                    .values(balance=WSCWallet.balance + wsc_amount)
                )
                wallet_db.commit()
            else:
                coin_row.balance += wsc_amount
                coin_db.commit()
            if not use_wsc:
                coin_db.close()
            return False, f"Bond creation failed (coins refunded): {bond_err}"

        if not use_wsc and coin_db:
            coin_db.close()

        paid_label = f"{wsc_amount:.2f} {stable_coin_symbol}" if not use_wsc else f"{wsc_amount:.2f} WSC"
        try:
            from stats_ux import log_transaction as _lt
            _lt(player_id, "bond_purchase", "money", -face_value_usd,
                f"Bond purchased: {paid_label} → {currency_code} {maturity_days}d",
                reference_id=str(bond.id))
        except Exception:
            pass

        annual_pct   = bank.yield_rate * 100
        daily_int    = face_value_usd * bank.yield_rate / 365
        currency_sym = bank.currency_symbol
        return True, (
            f"Bond purchased: {paid_label} → {currency_code} {maturity_days}-day bond. "
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
    Sell a bond before maturity. Returns value in the bank's own currency
    (not WSC) at a price reflecting current yield vs purchase yield.

    Price formula (simplified duration model):
      price_factor = 1 + (purchase_yield - current_yield) × remaining_years
    If current_yield > purchase_yield: bond is worth less (rising rates hurt bonds).
    If current_yield < purchase_yield: bond is worth more (falling rates help bonds).

    Since 1 WSC = $1 (peg), the WSC price converts to bank currency at current FX:
      foreign_return = wsc_return / bank.usd_per_unit
    """
    db = get_db()
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
        wsc_equiv    = bond.face_value_wsc * price_factor

        # Convert WSC equivalent to bank's own currency.
        # Secondary-market sale uses current FX — you bear FX risk if you sell early,
        # just as in real foreign-currency bond markets.
        foreign_return = wsc_equiv / bank.usd_per_unit
        currency_sym   = bank.currency_symbol
        currency_code  = bank.currency_code

        # Early-redemption penalty: charged if sold within BOND_EARLY_REDEMPTION_DAYS.
        # FIX: penalty is expressed as a % of face value, which the player paid at the
        # purchase FX rate — so compute the penalty at that locked rate, not the
        # current rate (otherwise a weaker currency inflates the penalty arbitrarily).
        early_penalty = 0.0
        days_held     = (now - bond.purchased_at).total_seconds() / 86400
        if days_held < BOND_EARLY_REDEMPTION_DAYS:
            fx_at_purchase = bond.purchase_fx_rate or bank.usd_per_unit
            early_penalty  = bond.face_value_wsc * BOND_EARLY_REDEMPTION_FEE / fx_at_purchase
            foreign_return = max(0.0, foreign_return - early_penalty)

        bond.status                = "sold"
        bank.net_demand_wsc       -= bond.face_value_wsc   # selling = negative demand
        bank.total_face_value_wsc  = max(0.0, bank.total_face_value_wsc - bond.face_value_wsc)
        bank.wsc_holdings          = max(0.0, bank.wsc_holdings - bond.face_value_wsc)
        # Immediate FX depreciation: selling a bond = capital outflow = weaker currency.
        if bank.currency_code != "USD":
            bank.usd_per_unit = max(
                0.000001,
                bank.usd_per_unit - bond.face_value_wsc * FX_DIRECT_BOND_LINK * bank.usd_per_unit,
            )

        # Credit foreign currency to player
        _adjust_currency_balance(db, player_id, currency_code, foreign_return)
        db.commit()

        try:
            from stats_ux import log_transaction as _lt
            _lt(player_id, "bond_sell", "money", foreign_return * bank.usd_per_unit,
                f"Bond sold early: {foreign_return:.4f} {currency_code} received",
                reference_id=str(bond_id))
        except Exception:
            pass

        face_foreign  = bond.face_value_wsc / bank.usd_per_unit
        gain_foreign  = foreign_return - face_foreign
        sign          = "+" if gain_foreign >= 0 else ""
        penalty_note  = (
            f" Early redemption penalty: {currency_sym}{early_penalty:.4f} {currency_code}."
            if early_penalty > 0 else ""
        )
        return True, (
            f"Bond sold: received {currency_sym}{foreign_return:.4f} {currency_code} "
            f"({sign}{gain_foreign:.4f} vs face value, price factor {price_factor:.4f}).{penalty_note} "
            f"Accumulated interest ({bond.interest_accrued:.4f} {currency_code}) also remains in your balance."
        )

    except Exception as e:
        db.rollback()
        return False, f"Bond sale error: {e}"
    finally:
        db.close()


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
    """USD value of one unit of currency_code.  USD itself = 1.0 (always fixed)."""
    if currency_code == "USD":
        return 1.0
    bank = db.query(StateReserveBank).filter(
        StateReserveBank.currency_code == currency_code.upper()
    ).first()
    rate = bank.usd_per_unit if bank else 1.0
    # USD bank row exists for bond purposes but its exchange rate is always 1.0
    return 1.0 if currency_code.upper() == "USD" else rate


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


def _debit_currency(db, player_id: int, currency_code: str, amount: float) -> Tuple[bool, str]:
    """Debit any currency (including USD) from PlayerCurrencyBalance."""
    bal_row = db.query(PlayerCurrencyBalance).filter(
        PlayerCurrencyBalance.player_id     == player_id,
        PlayerCurrencyBalance.currency_code == currency_code,
    ).first()
    bal = bal_row.balance if bal_row else 0.0
    if bal < amount:
        return False, f"Insufficient {currency_code}: have {bal:.4f}, need {amount:.4f}."
    bal_row.balance     -= amount
    bal_row.total_spent += amount
    return True, ""


def _credit_currency(db, player_id: int, currency_code: str, amount: float):
    """Credit any currency (including USD) to PlayerCurrencyBalance."""
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
    """
    Change a player's legal tender.

    Restrictions
    ============
    1. Cooldown: players must wait TENDER_SWITCH_COOLDOWN_DAYS days between switches.
    2. Repatriation fee: switching away from a non-USD tender costs
       TENDER_SWITCH_FEE_RATE of the current foreign-currency balance (taken by
       the reserve bank as a conversion/exit cost).
    3. The new currency must have an active reserve bank (or be USD).
    """
    code = currency_code.upper()

    db = get_db()
    try:
        # ── Validate new currency ─────────────────────────────────────────────
        new_bank = None
        if code != "USD":
            new_bank = db.query(StateReserveBank).filter(
                StateReserveBank.currency_code == code
            ).first()
            if not new_bank:
                return False, f"No reserve bank found for '{code}'. Available: {_available_codes(db)}"

        # ── Load existing legal-tender row ────────────────────────────────────
        row = db.query(PlayerLegalTender).filter(
            PlayerLegalTender.player_id == player_id
        ).first()
        current_code = row.currency_code if row else "USD"

        if current_code == code:
            return False, f"Your legal tender is already {code}."

        # ── Cooldown check ────────────────────────────────────────────────────
        if row and row.changed_at:
            days_since = (datetime.utcnow() - row.changed_at).total_seconds() / 86400
            if days_since < TENDER_SWITCH_COOLDOWN_DAYS:
                days_left = TENDER_SWITCH_COOLDOWN_DAYS - days_since
                return False, (
                    f"Currency switch on cooldown. "
                    f"You can switch again in {days_left:.1f} days."
                )

        # ── Repatriation fee on the outgoing currency balance ─────────────────
        fee_msg = ""
        bal = db.query(PlayerCurrencyBalance).filter(
            PlayerCurrencyBalance.player_id     == player_id,
            PlayerCurrencyBalance.currency_code == current_code,
        ).first()
        if bal and bal.balance > 0:
            fee = bal.balance * TENDER_SWITCH_FEE_RATE
            old_bank = db.query(StateReserveBank).filter(
                StateReserveBank.currency_code == current_code
            ).first()
            # Deduct fee from player's balance (taken by the reserve bank)
            _adjust_currency_balance(db, player_id, current_code, -fee)
            if old_bank:
                _add_bank_reserve(db, old_bank.id, current_code, fee)
            sym = old_bank.currency_symbol if old_bank else current_code
            fee_msg = (
                f" A {TENDER_SWITCH_FEE_RATE*100:.0f}% repatriation fee of "
                f"{sym}{fee:,.2f} {current_code} was charged."
            )
            try:
                from stats_ux import log_transaction as _lt
                fee_usd = fee * (old_bank.usd_per_unit if old_bank else 1.0)
                _lt(player_id, "forex_fee", "money", -fee_usd,
                    f"Legal tender switch fee: {sym}{fee:,.4f} {current_code} → {code}")
            except Exception:
                pass

        # ── Convert all existing currency balances into the new legal tender ─
        usd_per_new  = _get_usd_rate(db, code)
        all_balances = db.query(PlayerCurrencyBalance).filter(
            PlayerCurrencyBalance.player_id == player_id,
            PlayerCurrencyBalance.balance   >  0,
        ).all()

        conversion_details = []
        for cb in all_balances:
            if cb.currency_code == code:
                continue  # already in the target currency
            amt = cb.balance
            if amt <= 0:
                continue

            usd_per_from = _get_usd_rate(db, cb.currency_code)

            # Apply forex fee on the source amount before converting
            fee_native = amt * FOREX_FEE_RATE
            net_native = amt - fee_native
            usd_val    = net_native * usd_per_from
            new_amt    = usd_val / usd_per_new if usd_per_new > 0 else 0.0

            # Credit the fee to the source bank's reserves
            src_bank = db.query(StateReserveBank).filter(
                StateReserveBank.currency_code == cb.currency_code
            ).first()
            if src_bank:
                _add_bank_reserve(db, src_bank.id, cb.currency_code, fee_native)

            # Zero the old balance and credit new currency
            _adjust_currency_balance(db, player_id, cb.currency_code, -amt)
            _adjust_currency_balance(db, player_id, code, new_amt)

            conversion_details.append(
                f"{cb.currency_code} {amt:,.2f} → {code} {new_amt:,.2f}"
            )

        conversion_msg = ""
        if conversion_details:
            conversion_msg = " Converted: " + "; ".join(conversion_details) + "."

        # ── Persist the change ────────────────────────────────────────────────
        if row:
            row.currency_code = code
            row.changed_at    = datetime.utcnow()
        else:
            db.add(PlayerLegalTender(player_id=player_id, currency_code=code))

        db.commit()

        if code == "USD":
            return True, f"Legal tender set back to USD (default game currency).{fee_msg}{conversion_msg}"

        return True, (
            f"Legal tender changed to {new_bank.flag_emoji} {new_bank.currency_name} ({code}). "
            f"Future income will be auto-converted at the live forex rate.{fee_msg}{conversion_msg}"
        )
    except Exception as e:
        db.rollback()
        return False, str(e)
    finally:
        db.close()


def _available_codes(db) -> List[str]:
    return ["USD"] + [b.currency_code for b in db.query(StateReserveBank).all()]


def get_player_display_currency(player_id: int) -> dict:
    """
    Returns display formatting info for a player's legal tender.
    Used by UX routes to show prices in the player's preferred currency.

    Returns a dict with keys: code, symbol, usd_per_unit, flag.
    Falls back to USD defaults if no foreign tender is set.
    """
    code = get_player_legal_tender(player_id)
    if code == "USD":
        return {"code": "USD", "symbol": "$", "usd_per_unit": 1.0, "flag": "🇺🇸"}
    db = get_db()
    try:
        bank = db.query(StateReserveBank).filter(
            StateReserveBank.currency_code == code
        ).first()
        if not bank:
            return {"code": "USD", "symbol": "$", "usd_per_unit": 1.0, "flag": "🇺🇸"}
        return {
            "code":         code,
            "symbol":       bank.currency_symbol,
            "usd_per_unit": bank.usd_per_unit,
            "flag":         bank.flag_emoji,
        }
    finally:
        db.close()


def fmt_usd(usd_amount: float, disp: dict, *, precision: int = 2) -> str:
    """
    Format a USD-denominated amount in the player's display currency.

    `disp` is the dict returned by get_player_display_currency().

    For USD players  →  "$1,234.56"
    For JPY players  →  "¥1,234,567 JPY"

    All prices stored as USD in the DB pass through here before being
    rendered in any UX route so players always see their own currency.
    """
    amount = (usd_amount or 0.0) / disp["usd_per_unit"]
    formatted = f"{amount:,.{precision}f}"
    sym  = disp["symbol"]
    code = disp["code"]
    return f"{sym}{formatted}" if code == "USD" else f"{sym}{formatted}\u00a0{code}"


def can_afford_usd(player_id: int, usd_cost: float) -> bool:
    """
    Returns True if the player can afford usd_cost using their legal tender.
    All balances (including USD) now live in PlayerCurrencyBalance.
    For non-USD tender players, falls back to checking their USD balance.
    """
    if usd_cost <= 0:
        return True
    tender = get_player_legal_tender(player_id)
    db = get_db()
    try:
        if tender == "USD":
            row = db.query(PlayerCurrencyBalance).filter(
                PlayerCurrencyBalance.player_id     == player_id,
                PlayerCurrencyBalance.currency_code == "USD",
            ).first()
            return (row.balance if row else 0.0) >= usd_cost

        bank = db.query(StateReserveBank).filter(
            StateReserveBank.currency_code == tender
        ).first()
        if not bank:
            # Unknown tender — check USD fallback
            row = db.query(PlayerCurrencyBalance).filter(
                PlayerCurrencyBalance.player_id     == player_id,
                PlayerCurrencyBalance.currency_code == "USD",
            ).first()
            return (row.balance if row else 0.0) >= usd_cost

        foreign_cost = usd_cost / bank.usd_per_unit
        foreign_row = db.query(PlayerCurrencyBalance).filter(
            PlayerCurrencyBalance.player_id     == player_id,
            PlayerCurrencyBalance.currency_code == tender,
        ).first()
        if (foreign_row.balance if foreign_row else 0.0) >= foreign_cost:
            return True
        # USD fallback
        usd_row = db.query(PlayerCurrencyBalance).filter(
            PlayerCurrencyBalance.player_id     == player_id,
            PlayerCurrencyBalance.currency_code == "USD",
        ).first()
        return (usd_row.balance if usd_row else 0.0) >= usd_cost
    finally:
        db.close()


def convert_to_legal_tender(player_id: int, usd_amount: float) -> Tuple[float, str]:
    """
    Helper called by income functions: convert USD income to the player's legal tender.
    Delegates to process_income_conversion() which runs the full inter-bank settlement flow.
    For all currencies (including USD) the balance is credited to PlayerCurrencyBalance.
    Returns (converted_amount, currency_code).
    """
    return process_income_conversion(player_id, usd_amount)


# ==========================
# USD BALANCE HELPERS  (USD is now a reserve currency like all others)
# ==========================

def get_usd_balance(player_id: int) -> float:
    """Return the player's current USD balance from PlayerCurrencyBalance.

    Also checks the legacy players.cash_balance column (in the auth DB) in case
    the migration hasn't been applied yet on this server — if so, the legacy value
    is rescued into PlayerCurrencyBalance automatically.
    """
    db = get_db()
    try:
        row = db.query(PlayerCurrencyBalance).filter(
            PlayerCurrencyBalance.player_id     == player_id,
            PlayerCurrencyBalance.currency_code == "USD",
        ).first()
        pcb_balance = float(row.balance) if row else 0.0
    finally:
        db.close()

    # Fallback: if PCB says $0, check whether the legacy players.cash_balance column
    # still exists in the auth DB. If it has a non-zero value, rescue it now.
    if pcb_balance == 0.0:
        try:
            from database import engine as auth_engine
            from sqlalchemy import text
            with auth_engine.connect() as conn:
                col = conn.execute(text(
                    "SELECT 1 FROM information_schema.columns "
                    "WHERE table_name='players' AND column_name='cash_balance' LIMIT 1"
                )).fetchone()
                if col:
                    legacy = conn.execute(text(
                        "SELECT cash_balance FROM players WHERE id = :pid"
                    ), {"pid": player_id}).fetchone()
                    if legacy and legacy[0] and float(legacy[0]) > 0:
                        rescued = float(legacy[0])
                        credit_usd(player_id, rescued)
                        print(f"[ReserveBanks] Rescued ${rescued:,.4f} legacy USD for player {player_id}")
                        return rescued
        except Exception:
            pass

    return pcb_balance


# Alias used by reserve_banks_ux
get_player_usd_pcb_balance = get_usd_balance


def credit_usd(player_id: int, amount: float):
    """Credit USD to a player's PlayerCurrencyBalance. Auto-commits."""
    if amount <= 0:
        return
    db = get_db()
    try:
        _adjust_currency_balance(db, player_id, "USD", amount)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[ReserveBanks] credit_usd error (player {player_id}, ${amount}): {e}")
    finally:
        db.close()


def debit_usd(player_id: int, amount: float) -> bool:
    """Atomically debit USD from a player's PlayerCurrencyBalance. Returns True on success."""
    if amount <= 0:
        return True
    db = get_db()
    try:
        success = _debit_currency_balance_atomic(db, player_id, "USD", amount)
        if success:
            db.commit()
        return success
    except Exception as e:
        db.rollback()
        print(f"[ReserveBanks] debit_usd error (player {player_id}, ${amount}): {e}")
        return False
    finally:
        db.close()


def set_usd_balance(player_id: int, value: float):
    """Set a player's USD balance to an exact value (may go negative). Auto-commits."""
    db = get_db()
    try:
        current = get_usd_balance(player_id)
        diff = value - current
        if diff != 0:
            _adjust_currency_balance(db, player_id, "USD", diff)
            db.commit()
    except Exception as e:
        db.rollback()
        print(f"[ReserveBanks] set_usd_balance error (player {player_id}, value={value}): {e}")
    finally:
        db.close()


def set_currency_balance(player_id: int, currency_code: str, value: float):
    """Set a player's balance in any currency to an exact value. Admin use only. Auto-commits."""
    if currency_code == "USD":
        set_usd_balance(player_id, value)
        return
    db = get_db()
    try:
        current = get_player_currency_balance(player_id, currency_code)
        diff = value - current
        if diff != 0:
            _adjust_currency_balance(db, player_id, currency_code, diff)
            db.commit()
    except Exception as e:
        db.rollback()
        print(f"[ReserveBanks] set_currency_balance error (player {player_id}, {currency_code}, value={value}): {e}")
    finally:
        db.close()


def spend_player_funds(player_id: int, usd_cost: float) -> Tuple[bool, str]:
    """
    Deduct a USD-denominated cost from the player using their preferred legal tender.

    All balances (including USD) now live in PlayerCurrencyBalance in the reserve DB.
    For non-USD tender players, falls back to their USD balance if foreign balance
    is insufficient.  Auto-commits on success.

    Returns (True, "") on success or (False, error_message) on failure.
    """
    if usd_cost <= 0:
        return True, ""

    tender = get_player_legal_tender(player_id)
    db = get_db()
    try:
        if tender == "USD":
            if _debit_currency_balance_atomic(db, player_id, "USD", usd_cost):
                db.commit()
                return True, ""
            usd_row = db.query(PlayerCurrencyBalance).filter(
                PlayerCurrencyBalance.player_id     == player_id,
                PlayerCurrencyBalance.currency_code == "USD",
            ).first()
            bal = usd_row.balance if usd_row else 0.0
            return False, f"Insufficient funds. Need ${usd_cost:,.2f}, have ${bal:,.2f}."

        bank = db.query(StateReserveBank).filter(
            StateReserveBank.currency_code == tender
        ).first()
        if not bank:
            # Unknown tender — try USD fallback
            if _debit_currency_balance_atomic(db, player_id, "USD", usd_cost):
                db.commit()
                return True, ""
            usd_row = db.query(PlayerCurrencyBalance).filter(
                PlayerCurrencyBalance.player_id     == player_id,
                PlayerCurrencyBalance.currency_code == "USD",
            ).first()
            bal = usd_row.balance if usd_row else 0.0
            return False, f"Insufficient funds. Need ${usd_cost:,.2f}, have ${bal:,.2f}."

        foreign_cost = usd_cost / bank.usd_per_unit

        # Attempt atomic foreign-currency debit (eliminates TOCTOU race).
        if _debit_currency_balance_atomic(db, player_id, tender, foreign_cost):
            db.commit()
            return True, ""

        # Insufficient foreign balance — try USD fallback.
        if _debit_currency_balance_atomic(db, player_id, "USD", usd_cost):
            db.commit()
            return True, ""

        # Both insufficient — report foreign balance in the error message.
        bal_row = db.query(PlayerCurrencyBalance).filter(
            PlayerCurrencyBalance.player_id     == player_id,
            PlayerCurrencyBalance.currency_code == tender,
        ).first()
        foreign_balance = bal_row.balance if bal_row else 0.0
        symbol = bank.currency_symbol or tender
        return False, (
            f"Insufficient funds. Need {symbol}{foreign_cost:,.2f} {tender} "
            f"(≈ ${usd_cost:,.2f}), have {symbol}{foreign_balance:,.2f} {tender}."
        )
    except Exception as e:
        db.rollback()
        return False, f"Payment processing error: {e}"
    finally:
        db.close()


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
            if not bank:
                continue  # reserve bank was removed; skip orphaned bond
            now  = datetime.utcnow()
            remaining_days = max((bond.matures_at - now).days, 0)
            remaining_years = max((bond.matures_at - now).total_seconds() / (365 * 86400), 0.0)
            price_factor = 1.0 + (bond.purchase_yield - bank.yield_rate) * remaining_years
            price_factor = max(0.50, min(2.0, price_factor))
            wsc_sell_equiv = bond.face_value_wsc * price_factor
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
                # sell_value_wsc: WSC-equivalent (= USD value, since 1 WSC = $1)
                "sell_value_wsc": round(wsc_sell_equiv, 4),
                # sell_value_foreign: amount actually returned in the bank's currency
                "sell_value_foreign": round(wsc_sell_equiv / bank.usd_per_unit, 4),
                # maturity_value_foreign: face value in bank's currency at current FX
                "maturity_value_foreign": round(bond.face_value_wsc / bank.usd_per_unit, 4),
                "price_factor": round(price_factor, 4),
            })
        return result
    finally:
        db.close()


def get_player_currency_balance(player_id: int, currency_code: str) -> float:
    """Return a player's balance in any currency (including USD) from PlayerCurrencyBalance."""
    db = get_db()
    try:
        row = db.query(PlayerCurrencyBalance).filter(
            PlayerCurrencyBalance.player_id     == player_id,
            PlayerCurrencyBalance.currency_code == currency_code,
        ).first()
        return float(row.balance) if row else 0.0
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
    "spend_player_funds", "can_afford_usd", "get_player_display_currency",
    "get_usd_balance", "credit_usd", "debit_usd", "set_usd_balance",
    "get_player_currency_balance", "get_player_currency_balances",
    "get_all_banks", "get_player_bonds",
    "get_recent_forex_trades", "get_yield_history",
    "get_bank_reserves", "get_all_bank_reserves", "get_interbank_trades",
    "StateReserveBank", "ReserveBankBond", "PlayerLegalTender",
    "PlayerCurrencyBalance", "ForexTrade", "BondYieldHistory",
    "BankReserveBalance", "BankDebt", "InterbankTrade",
    "get_db",
]
