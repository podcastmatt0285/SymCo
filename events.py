"""
events.py

Server-wide events, market effects, and player task tracking.
Supports daily/weekly/monthly/special/task duration classes and
gov/bank/market/task/city/production event types.
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, Float, String, Boolean, DateTime, Text, ForeignKey
)
from sqlalchemy.ext.declarative import declarative_base
from database import engine, SessionLocal

Base = declarative_base()


# ── Level thresholds ──────────────────────────────────────────────────────────
# Fibonacci from index 3: fib(3)=2, fib(4)=3, fib(5)=5, ...
# LEVEL_THRESHOLDS[i] = cumulative trophies needed to reach level (i+2)
# so LEVEL_THRESHOLDS[0] = trophies to reach level 2, etc.

def _fib_from_index3(count: int):
    """Return `count` Fibonacci numbers starting from fib(3)=2."""
    a, b = 1, 2  # fib(2)=1, fib(3)=2
    result = []
    for _ in range(count):
        result.append(b)
        a, b = b, a + b
    return result

def _cumulative_sum(values):
    total = 0
    result = []
    for v in values:
        total += v
        result.append(total)
    return result

# 49 thresholds: level 2 through level 50
LEVEL_THRESHOLDS = _cumulative_sum(_fib_from_index3(49))


# ── Models ────────────────────────────────────────────────────────────────────

class GameEvent(Base):
    __tablename__ = "game_events"

    id             = Column(Integer, primary_key=True, index=True)
    title          = Column(String, nullable=False)
    description    = Column(Text, nullable=True)
    duration_class = Column(String, nullable=False)   # daily|weekly|monthly|special|task
    event_type     = Column(String, nullable=False)   # gov|bank|market|task|city|production
    starts_at      = Column(DateTime, nullable=False)
    ends_at        = Column(DateTime, nullable=True)
    effect_data    = Column(Text, default="{}")
    is_active      = Column(Boolean, default=True)
    created_by     = Column(Integer, nullable=True)
    trophy_reward  = Column(Integer, default=0)
    task_target    = Column(Float, nullable=True)
    task_metric    = Column(String, nullable=True)
    created_at     = Column(DateTime, default=datetime.utcnow)

    # Status is computed, not stored:
    #   active   → starts_at <= now <= ends_at  AND  is_active == True
    #   upcoming → starts_at > now
    #   finished → ends_at < now  OR  is_active == False


class PlayerTaskProgress(Base):
    """Tracks per-player progress on task-type events."""
    __tablename__ = "player_task_progress"

    id              = Column(Integer, primary_key=True, index=True)
    player_id       = Column(Integer, nullable=False, index=True)
    event_id        = Column(Integer, ForeignKey("game_events.id"), nullable=False)
    progress        = Column(Float, default=0.0)
    completed_at    = Column(DateTime, nullable=True)
    trophies_awarded = Column(Integer, default=0)


class PlayerRank(Base):
    """Trophy / level tracking per player."""
    __tablename__ = "player_ranks"

    id         = Column(Integer, primary_key=True, index=True)
    player_id  = Column(Integer, unique=True, nullable=False, index=True)
    trophies   = Column(Integer, default=0)
    level      = Column(Integer, default=1)
    updated_at = Column(DateTime, default=datetime.utcnow)


# ── Query helpers ─────────────────────────────────────────────────────────────

def get_active_events():
    """Return all currently active GameEvent rows ordered by ends_at asc."""
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        return (
            db.query(GameEvent)
            .filter(
                GameEvent.is_active == True,
                GameEvent.starts_at <= now,
                GameEvent.ends_at >= now,
            )
            .order_by(GameEvent.ends_at.asc())
            .all()
        )
    finally:
        db.close()


def get_upcoming_events(limit: int = 5):
    """Return the next upcoming events ordered by starts_at asc."""
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        return (
            db.query(GameEvent)
            .filter(
                GameEvent.is_active == True,
                GameEvent.starts_at > now,
            )
            .order_by(GameEvent.starts_at.asc())
            .limit(limit)
            .all()
        )
    finally:
        db.close()


def get_recent_finished_events(limit: int = 5):
    """Return recently finished events ordered by ends_at desc."""
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        return (
            db.query(GameEvent)
            .filter(
                (GameEvent.ends_at < now) | (GameEvent.is_active == False)
            )
            .order_by(GameEvent.ends_at.desc())
            .limit(limit)
            .all()
        )
    finally:
        db.close()


def _serialize_event(ev: GameEvent) -> dict:
    return {
        "id":             ev.id,
        "title":          ev.title,
        "description":    ev.description,
        "duration_class": ev.duration_class,
        "event_type":     ev.event_type,
        "starts_at":      ev.starts_at.isoformat() if ev.starts_at else None,
        "ends_at":        ev.ends_at.isoformat() if ev.ends_at else None,
        "trophy_reward":  ev.trophy_reward,
    }


def get_event_summary() -> dict:
    """Return a dict with active, upcoming, and recently finished events."""
    active   = [_serialize_event(e) for e in get_active_events()]
    upcoming = [_serialize_event(e) for e in get_upcoming_events(5)]
    finished = [_serialize_event(e) for e in get_recent_finished_events(5)]
    return {"active": active, "upcoming": upcoming, "finished": finished}


def get_player_level(player_id: int) -> dict:
    """Return the player's current level, trophies, and progress to next level.

    Returns:
        {"level": int, "trophies": int, "next_threshold": int | None,
         "prev_threshold": int, "progress_pct": float}
    """
    if player_id <= 0:
        return {"level": 1, "trophies": 0, "next_threshold": LEVEL_THRESHOLDS[0],
                "prev_threshold": 0, "progress_pct": 0.0}

    trophies = 0
    try:
        db = SessionLocal()
        try:
            row = db.query(PlayerRank).filter(PlayerRank.player_id == player_id).first()
            trophies = row.trophies if row else 0
        finally:
            db.close()
    except Exception:
        pass

    # Recalculate level from trophies in case it drifted
    level = 1
    for i, threshold in enumerate(LEVEL_THRESHOLDS):
        if trophies >= threshold:
            level = i + 2
        else:
            break

    prev_threshold = LEVEL_THRESHOLDS[level - 2] if level >= 2 else 0
    next_threshold = LEVEL_THRESHOLDS[level - 1] if level - 1 < len(LEVEL_THRESHOLDS) else None

    if next_threshold is not None:
        span = next_threshold - prev_threshold
        progress_pct = ((trophies - prev_threshold) / span * 100) if span > 0 else 100.0
    else:
        progress_pct = 100.0  # max level

    return {
        "level":          level,
        "trophies":       trophies,
        "next_threshold": next_threshold,
        "prev_threshold": prev_threshold,
        "progress_pct":   round(progress_pct, 1),
    }


# ── Lifecycle ─────────────────────────────────────────────────────────────────

def initialize():
    """Create all events tables."""
    Base.metadata.create_all(bind=engine)


def tick(current_tick, now):
    """Stub — no mechanical event effects defined yet."""
    pass
