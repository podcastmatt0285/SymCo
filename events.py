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


# ── Task progress helper ──────────────────────────────────────────────────────

def record_task_progress(player_id: int, metric: str, amount: float):
    """Add `amount` toward every active task event with task_metric == metric.

    Marks completed and awards trophies (+ push notification) when progress
    reaches task_target.  Safe to call from any thread; swallows all errors.
    """
    if player_id <= 0 or amount <= 0:
        return
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        active_tasks = db.query(GameEvent).filter(
            GameEvent.is_active == True,
            GameEvent.event_type == "task",
            GameEvent.task_metric == metric,
            GameEvent.starts_at <= now,
            (GameEvent.ends_at == None) | (GameEvent.ends_at >= now),
        ).all()

        for ev in active_tasks:
            prog = db.query(PlayerTaskProgress).filter(
                PlayerTaskProgress.player_id == player_id,
                PlayerTaskProgress.event_id == ev.id,
            ).first()
            if prog and prog.completed_at:
                continue  # already completed
            if not prog:
                prog = PlayerTaskProgress(
                    player_id=player_id,
                    event_id=ev.id,
                    progress=0.0,
                )
                db.add(prog)

            prog.progress = (prog.progress or 0.0) + amount

            if ev.task_target and prog.progress >= ev.task_target and not prog.completed_at:
                prog.completed_at = now
                prog.trophies_awarded = ev.trophy_reward or 0

                # Award trophies + recalculate level
                rank = db.query(PlayerRank).filter(
                    PlayerRank.player_id == player_id).first()
                if not rank:
                    rank = PlayerRank(player_id=player_id, trophies=0, level=1)
                    db.add(rank)
                rank.trophies = (rank.trophies or 0) + prog.trophies_awarded
                rank.updated_at = now
                level = 1
                for i, threshold in enumerate(LEVEL_THRESHOLDS):
                    if rank.trophies >= threshold:
                        level = i + 2
                    else:
                        break
                rank.level = level

                # Notify the player of completion
                if prog.trophies_awarded > 0:
                    try:
                        from push_ux import send_push_notification
                        _word = "trophy" if prog.trophies_awarded == 1 else "trophies"
                        send_push_notification(
                            player_id,
                            f"🏆 Task Complete: {ev.title}",
                            f"You earned {prog.trophies_awarded} {_word}!",
                            url="/events",
                            notif_type="tasks_events",
                            tag=f"task-complete-{ev.id}",
                        )
                    except Exception:
                        pass

        db.commit()
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        print(f"[Events] record_task_progress error: {e}")
    finally:
        db.close()


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
                (GameEvent.ends_at == None) | (GameEvent.ends_at >= now),
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
                GameEvent.is_active == False,
                GameEvent.ends_at != None,
            )
            .order_by(GameEvent.ends_at.desc())
            .limit(limit)
            .all()
        )
    finally:
        db.close()


def _serialize_event(ev: GameEvent) -> dict:
    import json as _json
    try:
        _ed = _json.loads(ev.effect_data or "{}")
    except Exception:
        _ed = {}
    return {
        "id":             ev.id,
        "title":          ev.title,
        "description":    ev.description,
        "duration_class": ev.duration_class,
        "event_type":     ev.event_type,
        "starts_at":      ev.starts_at.isoformat() if ev.starts_at else None,
        "ends_at":        ev.ends_at.isoformat() if ev.ends_at else None,
        "trophy_reward":  ev.trophy_reward,
        "task_target":    ev.task_target,
        "task_metric":    ev.task_metric,
        "effect_data":    _ed,
    }


def get_event_summary() -> dict:
    """Return a dict with active, upcoming, and recently finished events."""
    active   = [_serialize_event(e) for e in get_active_events()]
    upcoming = [_serialize_event(e) for e in get_upcoming_events(5)]
    finished = [_serialize_event(e) for e in get_recent_finished_events(5)]
    return {"active": active, "upcoming": upcoming, "finished": finished}


_effects_cache: list = []
_effects_cache_ts: float = 0.0
_EFFECTS_TTL: float = 30.0  # seconds


def get_active_effects() -> list[dict]:
    """Return a list of effect dicts from all currently active non-task events.

    Each entry: {"event_id", "title", "event_type", "effect_data"}.
    Cached for 30 s so high-frequency callers (market, production ticks)
    do not create a DB round-trip on every request.
    """
    import json as _json, time as _time
    global _effects_cache, _effects_cache_ts
    now = _time.time()
    if _effects_cache_ts and (now - _effects_cache_ts) < _EFFECTS_TTL:
        return _effects_cache
    events = get_active_events()
    result = []
    for ev in events:
        if ev.event_type == "task":
            continue
        try:
            ed = _json.loads(ev.effect_data or "{}")
        except Exception:
            ed = {}
        if ed:
            result.append({
                "event_id":    ev.id,
                "title":       ev.title,
                "event_type":  ev.event_type,
                "effect_data": ed,
            })
    _effects_cache    = result
    _effects_cache_ts = now
    return result


def invalidate_effects_cache() -> None:
    """Call after creating/updating/stopping events so the cache refreshes immediately."""
    global _effects_cache_ts
    _effects_cache_ts = 0.0


def get_active_market_price_factor() -> float:
    """Return combined price multiplier from active market/bank/gov events.

    effect_data field checked: {"price_factor": <float>}
    Returns 1.0 if no active price-altering events.
    """
    factor = 1.0
    for eff in get_active_effects():
        ed = eff.get("effect_data", {})
        pf = ed.get("price_factor")
        if isinstance(pf, (int, float)) and pf > 0:
            factor *= pf
    return factor


def get_active_production_factor() -> float:
    """Return combined production output multiplier from active production/city events.

    effect_data field checked: {"production_factor": <float>}
    Returns 1.0 if no active production-altering events.
    """
    factor = 1.0
    for eff in get_active_effects():
        ed = eff.get("effect_data", {})
        pf = ed.get("production_factor")
        if isinstance(pf, (int, float)) and pf > 0:
            factor *= pf
    return factor


def get_player_task_progress_map(player_id: int, event_ids: list) -> dict:
    """Return {event_id: {"progress": float, "completed": bool}} for the given event IDs."""
    if not player_id or not event_ids:
        return {}
    db = SessionLocal()
    try:
        rows = db.query(PlayerTaskProgress).filter(
            PlayerTaskProgress.player_id == player_id,
            PlayerTaskProgress.event_id.in_(event_ids),
        ).all()
        return {
            r.event_id: {
                "progress":  r.progress or 0.0,
                "completed": r.completed_at is not None,
            }
            for r in rows
        }
    finally:
        db.close()


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


# ── Broadcast helper ──────────────────────────────────────────────────────────

def broadcast_event_push(event_id: int, title: str, body: str,
                          tag: str = None) -> int:
    """Send a push + in-game notification to every subscribed player.
    Returns the count sent. Safe to call from any thread.
    """
    try:
        from push_ux import send_push_notification
        from auth import get_db, PushSubscription
        adb = get_db()
        try:
            pids = [r[0] for r in adb.query(PushSubscription.player_id).distinct().all()]
        finally:
            adb.close()
        _tag = tag or f"event-{event_id}"
        sent = 0
        for pid in pids:
            try:
                send_push_notification(pid, title, body, url="/events",
                                       notif_type="tasks_events", tag=_tag)
                sent += 1
            except Exception:
                pass
        return sent
    except Exception as e:
        print(f"[Events] broadcast failed: {e}")
        return 0


# ── Event-driven notifications (threading.Timer, no polling) ──────────────────

import threading as _threading

_pending_timers: dict = {}      # event_id → [Timer, ...]
_timers_lock = _threading.Lock()


def cancel_event_timers(event_id: int):
    """Cancel any scheduled notifications for this event (call on stop/delete)."""
    with _timers_lock:
        for t in _pending_timers.pop(event_id, []):
            t.cancel()


def _on_event_live(event_id: int):
    """Timer callback: fires when a scheduled event's starts_at arrives."""
    with _timers_lock:
        _pending_timers.pop(event_id, None)
    title = None
    body  = None
    db = SessionLocal()
    try:
        ev = db.query(GameEvent).filter(GameEvent.id == event_id).first()
        if ev and ev.is_active:
            title = f"🔴 {ev.title} is LIVE!"
            body  = ev.description or "The event is now active — join in!"
    except Exception as e:
        print(f"[Events] _on_event_live DB error: {e}")
    finally:
        db.close()
    if title:
        broadcast_event_push(event_id, title, body, tag=f"event-{event_id}-live")


def _on_event_ended(event_id: int):
    """Timer callback: fires when an event's ends_at arrives."""
    with _timers_lock:
        _pending_timers.pop(event_id, None)
    title = None
    body  = None
    db = SessionLocal()
    try:
        ev = db.query(GameEvent).filter(GameEvent.id == event_id).first()
        if ev:
            title = f"🏁 {ev.title} has ended"
            body  = "The event is over — check /events for details."
    except Exception as e:
        print(f"[Events] _on_event_ended DB error: {e}")
    finally:
        db.close()
    if title:
        broadcast_event_push(event_id, title, body, tag=f"event-{event_id}-ended")


def schedule_event_notifications(ev: GameEvent):
    """Arm one-shot timers for a future event's starts_at and/or ends_at.
    Call after create or restart. Cancels any existing timers first.
    """
    cancel_event_timers(ev.id)
    now    = datetime.utcnow()
    timers = []

    if ev.starts_at and ev.starts_at > now:
        delay = (ev.starts_at - now).total_seconds()
        t = _threading.Timer(delay, _on_event_live, args=[ev.id])
        t.daemon = True
        t.start()
        timers.append(t)
        print(f"[Events] '{ev.title}' go-live notification in {delay/60:.1f} min")

    if ev.ends_at and ev.ends_at > now:
        delay = (ev.ends_at - now).total_seconds()
        t = _threading.Timer(delay, _on_event_ended, args=[ev.id])
        t.daemon = True
        t.start()
        timers.append(t)
        print(f"[Events] '{ev.title}' end notification in {delay/60:.1f} min")

    if timers:
        with _timers_lock:
            _pending_timers[ev.id] = timers


# ── Lifecycle ─────────────────────────────────────────────────────────────────

def _rearm_on_startup():
    """After a server restart, reschedule timers for events not yet fired."""
    try:
        now = datetime.utcnow()
        db  = SessionLocal()
        try:
            pending = db.query(GameEvent).filter(
                GameEvent.is_active == True,
            ).all()
            for ev in pending:
                # Only arm if something is still in the future
                needs_live = ev.starts_at and ev.starts_at > now
                needs_end  = ev.ends_at and ev.ends_at > now
                if needs_live or needs_end:
                    schedule_event_notifications(ev)
        finally:
            db.close()
    except Exception as e:
        print(f"[Events] rearm on startup failed: {e}")


def initialize():
    """Create all events tables, then rearm timers for any pending events."""
    Base.metadata.create_all(bind=engine)
    # Migrate renamed metric: city_tax_paid_usd → market_sales_tax_usd
    _db = SessionLocal()
    try:
        _db.query(GameEvent).filter(
            GameEvent.task_metric == "city_tax_paid_usd"
        ).update({"task_metric": "market_sales_tax_usd"})
        _db.commit()
    except Exception:
        _db.rollback()
    finally:
        _db.close()
    _rearm_on_startup()


def tick(current_tick, now):
    """No-op — notifications are fired by admin actions and threading.Timer."""
    pass
