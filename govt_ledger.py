"""
govt_ledger.py

Federal Government Transaction Ledger.
Records every government fiscal event for player-facing transparency on /government.
Uses the main game database (same engine as cities.py).
"""

from datetime import datetime
from sqlalchemy import Column, Integer, Float, String, DateTime, Index
from sqlalchemy.ext.declarative import declarative_base
from database import engine, SessionLocal

Base = declarative_base()

# Human-readable metadata per event type: (label, default direction, badge color)
EVENT_META = {
    # ── Existing revenue ──────────────────────────────────────────────────────
    "bond_interest_tax":   ("Bond Interest Tax",        "in",  "#fbbf24"),
    "reserve_balance_tax": ("Reserve Balance Tax",      "in",  "#f59e0b"),
    "bond_issuance_fee":   ("Bond Issuance Fee",        "in",  "#fcd34d"),
    "charter_fee":         ("Charter Renewal Fee",      "in",  "#4ade80"),
    "autonomous_bank_tax": ("Autonomous Bank Tax",      "in",  "#22c55e"),
    "loan_repayment":      ("Loan Repayment",            "in",  "#34d399"),
    "petrodollar_customs": ("Petrodollar Customs",      "in",  "#38bdf8"),
    "estate_sale":         ("Estate Sale",               "in",  "#a78bfa"),
    "bond_sale":           ("Bond Liquidation",          "in",  "#4ade80"),
    # ── New tax / fee revenue ─────────────────────────────────────────────────
    "federal_sales_tax":   ("Federal Sales Tax",        "in",  "#60a5fa"),
    "startup_fee":         ("Business Startup Fee",     "in",  "#34d399"),
    "district_startup_fee":("District Startup Fee",     "in",  "#6ee7b7"),
    "executive_fee":       ("Executive Fee",            "in",  "#a78bfa"),
    "wage_tax":            ("Executive Wage",            "in",  "#c084fc"),
    "land_hoarding_tax":   ("Land Hoarding Tax",        "in",  "#fb923c"),
    "death_tax":           ("Estate / Death Tax",       "in",  "#f472b6"),
    "forex_fee":           ("Forex Transaction Fee",    "in",  "#38bdf8"),
    # ── Outlays ───────────────────────────────────────────────────────────────
    "city_grant":          ("City Bank Grant",          "out", "#f87171"),
    "bond_purchase":       ("Bond Purchase",            "out", "#818cf8"),
    "loan_disbursement":   ("Emergency Loan Issued",    "out", "#fb923c"),
}


class GovernmentLedger(Base):
    """One row per significant government fiscal event."""
    __tablename__ = "government_ledger"

    id           = Column(Integer, primary_key=True, index=True)
    event_type   = Column(String, nullable=False, index=True)
    direction    = Column(String(3), nullable=False)   # "in" or "out"
    amount       = Column(Float, nullable=False)        # always positive
    currency     = Column(String(8), default="USD")
    counterparty = Column(String, nullable=True)        # bank name, city name, etc.
    description  = Column(String, nullable=True)
    timestamp    = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("ix_gov_ledger_ts_type", "timestamp", "event_type"),
    )


def get_db():
    db = SessionLocal()
    return db


def log_gov_event(
    event_type: str,
    direction: str,
    amount: float,
    currency: str = "USD",
    counterparty: str = None,
    description: str = None,
) -> None:
    """Record a government fiscal event. Never raises — safe to call from anywhere."""
    if not amount or amount <= 0:
        return
    db = get_db()
    try:
        db.add(GovernmentLedger(
            event_type   = event_type,
            direction    = direction,
            amount       = abs(amount),
            currency     = currency,
            counterparty = counterparty,
            description  = description,
        ))
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[GovLedger] Log error ({event_type}): {e}")
    finally:
        db.close()


def get_recent_events(limit: int = 100, event_type: str = None):
    """Return the most recent ledger entries, newest first."""
    db = get_db()
    try:
        q = db.query(GovernmentLedger).order_by(GovernmentLedger.timestamp.desc())
        if event_type:
            q = q.filter(GovernmentLedger.event_type == event_type)
        return q.limit(limit).all()
    finally:
        db.close()


def initialize():
    Base.metadata.create_all(bind=engine)
    print("[GovLedger] Table ready.")
