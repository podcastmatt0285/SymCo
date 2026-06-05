"""
events.py

Server-wide events, market effects, and player task tracking.
Supports daily/weekly/monthly/special/task duration classes and
gov/bank/market/task/city/production event types.
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, Float, String, Boolean, DateTime, Text, ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.ext.declarative import declarative_base
from database import engine, SessionLocal

Base = declarative_base()


# ── Land Grant constants ──────────────────────────────────────────────────────
GRANT_ENTRY_COST_TROPHIES = 425
GRANT_TIERS = [
    {"name": "platinum", "plots": 20, "winners": 1,  "trophy_reward": 100},
    {"name": "gold",     "plots": 15, "winners": 3,  "trophy_reward": 50},
    {"name": "silver",   "plots": 13, "winners": 7,  "trophy_reward": 25},
    {"name": "bronze",   "plots": 10, "winners": 15, "trophy_reward": 10},
]


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


class LandGrantEntry(Base):
    __tablename__ = "land_grant_entries"
    id                 = Column(Integer, primary_key=True)
    event_id           = Column(Integer, nullable=False, index=True)
    player_id          = Column(Integer, nullable=False, index=True)
    entered_at         = Column(DateTime, default=datetime.utcnow)
    net_worth_at_entry = Column(Float, nullable=False)
    preferred_terrain  = Column(String, nullable=True)
    tier_awarded       = Column(String, nullable=True)
    plots_awarded      = Column(Integer, default=0)
    awarded_at         = Column(DateTime, nullable=True)
    __table_args__ = (UniqueConstraint("event_id", "player_id", name="uq_grant_entry"),)


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
                    _word = "trophy" if prog.trophies_awarded == 1 else "trophies"
                    try:
                        from push_ux import send_push_notification
                        send_push_notification(
                            player_id,
                            f"🏆 Task Complete: {ev.title}",
                            f"You earned {prog.trophies_awarded} {_word}!",
                            url="/events",
                            notif_type="tasks_events",
                            tag=f"task-complete-{ev.id}",
                        )
                    except Exception as _e:
                        print(f"[Events] push notification failed for player {player_id}: {_e}")
                    try:
                        from push_ux import create_game_notification
                        create_game_notification(
                            player_id,
                            f"🏆 {ev.title}",
                            f"You earned {prog.trophies_awarded} {_word}!",
                            url="/events",
                            notif_type="tasks_events",
                        )
                    except Exception as _e:
                        print(f"[Events] in-game banner failed for player {player_id}: {_e}")
                    try:
                        from stats_ux import log_transaction
                        log_transaction(
                            player_id,
                            transaction_type="trophy_award",
                            category="tasks",
                            amount=0.0,
                            description=f"Task completed: {ev.title}",
                            reference_id=f"event-{ev.id}",
                            item_type="trophy",
                            quantity=float(prog.trophies_awarded),
                        )
                    except Exception as _e:
                        print(f"[Events] ledger entry failed for player {player_id}: {_e}")

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


def get_active_market_shutdown() -> bool:
    """Return True if a Marketplace Shutdown event is currently active."""
    for eff in get_active_effects():
        if eff.get("effect_data", {}).get("market_shutdown"):
            return True
    return False


def cancel_all_open_market_orders() -> int:
    """Cancel every ACTIVE/PARTIALLY_FILLED order on both commodity and district markets.

    Called once when a market_shutdown event is activated. Returns total orders cancelled.
    All imports are local to avoid circular imports (market/district_market import events).
    """
    import collections as _col
    import threading as _thr
    cancelled = 0
    _mkt_by_player: dict = {}
    _mkt_order_info: list = []
    _dmt_by_player: dict = {}
    _dmt_order_info: list = []

    # Commodity market
    try:
        from market import get_db as _mkt_db, MarketOrder, OrderStatus as _OS
        mdb = _mkt_db()
        try:
            rows = mdb.query(MarketOrder).filter(
                MarketOrder.status.in_([_OS.ACTIVE, _OS.PARTIALLY_FILLED])
            ).all()
            _mkt_by_player = _col.defaultdict(int)
            _mkt_order_info = [
                (r.id, r.player_id, r.order_type, r.item_type, r.quantity) for r in rows
            ]
            for row in rows:
                row.status = _OS.CANCELLED
                _mkt_by_player[row.player_id] += 1
                cancelled += 1
            mdb.commit()
        except Exception as _e:
            mdb.rollback()
            print(f"[Events] cancel commodity orders: {_e}")
            _mkt_by_player = {}
            _mkt_order_info = []
        finally:
            mdb.close()
    except Exception as _e:
        print(f"[Events] cancel commodity orders import error: {_e}")

    # District market
    try:
        from district_market import get_db as _dmt_db, DistrictMarketOrder, OrderStatus as _DOS
        ddb = _dmt_db()
        try:
            rows = ddb.query(DistrictMarketOrder).filter(
                DistrictMarketOrder.status.in_([_DOS.ACTIVE, _DOS.PARTIALLY_FILLED])
            ).all()
            _dmt_by_player = _col.defaultdict(int)
            _dmt_order_info = [
                (r.id, r.player_id, r.order_type, r.item_type, r.quantity) for r in rows
            ]
            for row in rows:
                row.status = _DOS.CANCELLED
                _dmt_by_player[row.player_id] += 1
                cancelled += 1
            ddb.commit()
        except Exception as _e:
            ddb.rollback()
            print(f"[Events] cancel district orders: {_e}")
            _dmt_by_player = {}
            _dmt_order_info = []
        finally:
            ddb.close()
    except Exception as _e:
        print(f"[Events] cancel district orders import error: {_e}")

    # Wipe trade history so all prices reset to 0 when markets reopen
    try:
        from market import get_db as _mkt_db2, Trade as _Trade
        _mdb2 = _mkt_db2()
        try:
            _mdb2.query(_Trade).delete(synchronize_session=False)
            _mdb2.commit()
            print("[Events] Marketplace Shutdown: commodity trade history cleared (prices reset to 0)")
        except Exception as _e:
            _mdb2.rollback()
            print(f"[Events] clear commodity trades: {_e}")
        finally:
            _mdb2.close()
    except Exception as _e:
        print(f"[Events] clear commodity trades import error: {_e}")

    try:
        from district_market import get_db as _dmt_db2, DistrictTrade as _DTrade
        _ddb2 = _dmt_db2()
        try:
            _ddb2.query(_DTrade).delete(synchronize_session=False)
            _ddb2.commit()
            print("[Events] Marketplace Shutdown: district trade history cleared (prices reset to 0)")
        except Exception as _e:
            _ddb2.rollback()
            print(f"[Events] clear district trades: {_e}")
        finally:
            _ddb2.close()
    except Exception as _e:
        print(f"[Events] clear district trades import error: {_e}")

    # Notify affected players + log ledger entries in background (non-blocking)
    def _notify_and_log():
        try:
            from push_ux import send_push_notification as _push
            from stats_ux import log_transaction as _log_tx
        except Exception as _ie:
            print(f"[Events] CRITICAL: shutdown notify imports failed — player notifications will not be sent: {_ie}")
            return

        for pid, count in _mkt_by_player.items():
            try:
                _s = "s" if count != 1 else ""
                _push(pid, "Pandemic — Market Closed",
                      f"Your {count} commodity market order{_s} "
                      f"{'were' if count != 1 else 'was'} cancelled due to the emergency closure.",
                      url="/market", notif_type="trades",
                      tag=f"shutdown-mkt-{pid}")
            except Exception as _e:
                print(f"[Events] shutdown push error (player {pid}): {_e}")

        for pid, count in _dmt_by_player.items():
            try:
                _s = "s" if count != 1 else ""
                _push(pid, "Pandemic — Market Closed",
                      f"Your {count} district market order{_s} "
                      f"{'were' if count != 1 else 'was'} cancelled due to the emergency closure.",
                      url="/district-market", notif_type="trades",
                      tag=f"shutdown-dmt-{pid}")
            except Exception as _e:
                print(f"[Events] shutdown push error district (player {pid}): {_e}")

        for oid, pid, otype, itype, qty in _mkt_order_info:
            try:
                _log_tx(pid, "order_cancelled",
                        "money" if otype == "buy" else "resource",
                        0.0,
                        description=f"Pandemic shutdown: {otype} order cancelled",
                        reference_id=str(oid), item_type=itype, quantity=qty)
            except Exception as _e:
                print(f"[Events] log_tx error order {oid}: {_e}")

        for oid, pid, otype, itype, qty in _dmt_order_info:
            try:
                _log_tx(pid, "order_cancelled",
                        "money" if otype == "buy" else "resource",
                        0.0,
                        description=f"Pandemic shutdown: district {otype} order cancelled",
                        reference_id=str(oid), item_type=itype, quantity=qty)
            except Exception as _e:
                print(f"[Events] log_tx error district order {oid}: {_e}")

    _thr.Thread(target=_notify_and_log, daemon=True).start()
    print(f"[Events] Marketplace Shutdown: cancelled {cancelled} open orders")
    return cancelled


def get_active_production_factor() -> float:
    """Return combined production output multiplier from active production/city events.

    effect_data field checked: {"production_factor": <float>}
    Returns 1.0 if no active production-altering events.

    NOTE: item_crisis events are intentionally excluded here — their per-item
    production_factor is applied separately via get_active_item_crisis_factors()
    in the production tick. Including them here would double-penalize the crisis
    item and incorrectly penalize *all* items for a single-item crisis.
    """
    factor = 1.0
    for eff in get_active_effects():
        if eff.get("event_type") == "item_crisis":
            continue  # handled per-item by get_active_item_crisis_factors()
        ed = eff.get("effect_data", {})
        pf = ed.get("production_factor")
        if isinstance(pf, (int, float)) and pf > 0:
            factor *= pf
    return factor


_item_name_cache: dict = {}

def _get_item_display_name(item_type: str) -> str:
    """Return human-readable item name from item_types.json, cached in memory."""
    if item_type in _item_name_cache:
        return _item_name_cache[item_type]
    name = item_type.replace("_", " ").title()
    try:
        import json as _j2, os as _os
        _path = _os.path.join(_os.path.dirname(__file__), "item_types.json")
        with open(_path) as _f:
            name = _j2.load(_f).get(item_type, {}).get("name", name)
    except Exception:
        pass
    _item_name_cache[item_type] = name
    return name


def get_active_item_crisis_factors() -> dict:
    """Return {item_type: production_factor} for all active item_crisis events.

    Multiple simultaneous crises on the same item have their factors multiplied.
    e.g. effect_data = {"item_type": "coffee_beans", "production_factor": 0.5}
    means coffee output is halved globally.
    """
    factors: dict = {}
    for eff in get_active_effects():
        if eff.get("event_type") != "item_crisis":
            continue
        ed = eff.get("effect_data", {})
        item = ed.get("item_type")
        pf = ed.get("production_factor")
        if item and isinstance(pf, (int, float)) and 0 < pf <= 2.0:
            factors[item] = factors.get(item, 1.0) * pf
    return factors


def get_active_item_crisis_summary() -> list:
    """Return list of active crisis dicts for display: [{item_type, item_name, drop_pct, title, ends_at}]."""
    import json as _json
    crises = []
    try:
        db = SessionLocal()
        try:
            now = datetime.utcnow()
            rows = db.query(GameEvent).filter(
                GameEvent.event_type == "item_crisis",
                GameEvent.is_active == True,
                GameEvent.starts_at <= now,
            ).filter(
                (GameEvent.ends_at == None) | (GameEvent.ends_at > now)
            ).all()
            for ev in rows:
                try:
                    ed = _json.loads(ev.effect_data or "{}")
                except Exception:
                    ed = {}
                item_type = ed.get("item_type", "")
                pf = ed.get("production_factor", 1.0)
                drop_pct = round((1.0 - pf) * 100) if pf < 1.0 else 0
                crises.append({
                    "item_type":  item_type,
                    "item_name":  _get_item_display_name(item_type) if item_type else "",
                    "drop_pct":   drop_pct,
                    "production_factor": pf,
                    "title":      ev.title,
                    "ends_at":    ev.ends_at,
                })
        finally:
            db.close()
    except Exception as e:
        print(f"[Events] get_active_item_crisis_summary error: {e}")
    return crises


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


def _snapshot_index_challenge_members(db, ev: "GameEvent"):
    """Populate effect_data with the set of player_ids currently in the WBC-50 index.

    Called when an index_challenge event goes live so we know who starts inside
    vs outside the index, determining each player's personal challenge direction.
    """
    import json as _json
    try:
        from banks.wbc50_index_fund import get_wbc50_constituents
        from banks.brokerage_firm import CompanyShares, get_db as firm_db
        eq_db = firm_db()
        try:
            constituents = get_wbc50_constituents()
            cids = [c.id for c in constituents]
            if not cids:
                return
            rows = eq_db.query(CompanyShares).filter(
                CompanyShares.id.in_(cids)
            ).all()
            member_pids = [r.founder_id for r in rows if (r.founder_id or 0) > 0]
        finally:
            eq_db.close()
        existing = {}
        try:
            existing = _json.loads(ev.effect_data or "{}")
        except Exception:
            pass
        existing["index_members_at_start"] = member_pids
        ev.effect_data = _json.dumps(existing)
        print(f"[Events] index_challenge snapshot: {len(member_pids)} players in WBC-50")
    except Exception as e:
        print(f"[Events] _snapshot_index_challenge_members error: {e}")


# ── Federal Development Grant ─────────────────────────────────────────────────

def enter_land_grant_event(player_id: int, event_id: int) -> dict:
    """Validate entry, deduct trophies, snapshot net worth, create entry row."""
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        ev = db.query(GameEvent).filter(GameEvent.id == event_id).first()
        if not ev:
            return {"ok": False, "message": "Event not found."}
        if ev.event_type != "land_grant":
            return {"ok": False, "message": "Not a land grant event."}
        if not ev.is_active or ev.starts_at > now or (ev.ends_at and ev.ends_at < now):
            return {"ok": False, "message": "Event is not currently active."}

        existing = db.query(LandGrantEntry).filter(
            LandGrantEntry.event_id == event_id,
            LandGrantEntry.player_id == player_id,
        ).first()
        if existing:
            return {"ok": False, "message": "You have already entered this event."}

        rank = db.query(PlayerRank).filter(PlayerRank.player_id == player_id).first()
        trophies = rank.trophies if rank else 0
        if trophies < GRANT_ENTRY_COST_TROPHIES:
            return {"ok": False, "message": f"Not enough trophies. Need {GRANT_ENTRY_COST_TROPHIES}, have {trophies}."}

        try:
            from stats_ux import calculate_player_stats
            stats = calculate_player_stats(player_id)
            nw = float(stats["total_net_worth"]) if stats else 0.0
        except Exception as _e:
            print(f"[LandGrant] stats error for player {player_id}: {_e}")
            nw = 0.0

        preferred_terrain = None
        try:
            from land import LandPlot, SessionLocal as _LandDB
            from sqlalchemy import func as _func
            ldb = _LandDB()
            try:
                row = (
                    ldb.query(LandPlot.terrain_type, _func.count(LandPlot.id).label("cnt"))
                    .filter(LandPlot.owner_id == player_id)
                    .group_by(LandPlot.terrain_type)
                    .order_by(_func.count(LandPlot.id).desc())
                    .first()
                )
                if row:
                    preferred_terrain = row.terrain_type
            finally:
                ldb.close()
        except Exception as _e:
            print(f"[LandGrant] terrain lookup error: {_e}")

        rank.trophies -= GRANT_ENTRY_COST_TROPHIES
        level = 1
        for i, threshold in enumerate(LEVEL_THRESHOLDS):
            if rank.trophies >= threshold:
                level = i + 2
            else:
                break
        rank.level = level
        rank.updated_at = now

        entry = LandGrantEntry(
            event_id=event_id,
            player_id=player_id,
            net_worth_at_entry=nw,
            preferred_terrain=preferred_terrain,
        )
        db.add(entry)
        db.commit()

        try:
            from stats_ux import log_transaction
            log_transaction(
                player_id, "trophy_spend", "events", 0.0,
                description="Federal Development Grant entry — 425 trophies",
                reference_id=f"grant-{event_id}",
                item_type="trophy", quantity=-425.0,
            )
        except Exception as _e:
            print(f"[LandGrant] log_transaction error: {_e}")

        try:
            from push_ux import create_game_notification
            create_game_notification(
                player_id,
                "Federal Development Grant",
                "You have entered! Compete on net worth growth to win government land plots.",
                url=f"/events/land-grant/{event_id}",
                notif_type="tasks_events",
            )
        except Exception as _e:
            print(f"[LandGrant] in-game notification error: {_e}")

        return {"ok": True, "message": "Entry successful! Good luck."}
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        print(f"[LandGrant] enter_land_grant_event error: {e}")
        return {"ok": False, "message": "An error occurred. Please try again."}
    finally:
        db.close()


def _execute_foreign_land_sale(ev) -> str:
    """Fire the foreign_land_sale event effect.

    Deletes all government-owned land plots and credits the government with
    10% of their estimated value in the highest-value foreign reserve currency.
    Returns a human-readable summary string for the push notification body.
    """
    from sqlalchemy import func as _sqlfunc
    from land import LandPlot as _LP, get_db as _ldb
    from land_market import GovernmentAuction as _GA, LandBank as _LBank
    from reserve_banks import (
        get_db as _rdb, StateReserveBank as _SRB,
        _adjust_currency_balance,
    )
    from govt_ledger import log_gov_event

    # ── 1. Delete all government plots, plus the auction / land-bank rows that
    #       reference them (they live in the same main DB — land and land_market
    #       share one engine). Skipping this cleanup would leave dangling
    #       GovernmentAuction rows that still look biddable on /land-market but
    #       reference a plot that no longer exists — a win would then crash
    #       finalize_land_sale.
    #
    #       Everything is done with SQL-side aggregates and bulk DELETEs (no ORM
    #       hydration) so this stays fast even when the reserve holds thousands
    #       of plots — which is exactly the frozen-economy backlog this event is
    #       meant to clear.
    land_db = _ldb()
    try:
        _gov = lambda q: q.filter(_LP.is_government_owned == True)  # noqa: E731
        agg = _gov(land_db.query(
            _sqlfunc.count(_LP.id),
            _sqlfunc.coalesce(_sqlfunc.sum(_LP.monthly_tax), 0.0),
        )).one()
        plot_count  = int(agg[0] or 0)
        total_value = float(agg[1] or 0.0) * 12 * 10
        sale_usd    = total_value * 0.10

        # Clear EVERY government auction and land-bank row — not just the ones
        # whose plot is still flagged is_government_owned. Filtering by the
        # current gov-plot set (the old behaviour) left orphaned/expired
        # auctions behind: rows whose plot was already transferred or deleted
        # are not in that set, so they survived the wipe and kept showing on
        # /land-market as "no time left" listings that never clear. This event
        # liquidates the entire government land reserve, so by definition NO
        # government auction or land-bank entry should outlive it. Delete the
        # references first, then the plots (FK-safe ordering).
        auctions_cleared = land_db.query(_GA).delete(synchronize_session=False)
        bank_cleared     = land_db.query(_LBank).delete(synchronize_session=False)
        if plot_count:
            _gov(land_db.query(_LP)).delete(synchronize_session=False)
        land_db.commit()
    finally:
        land_db.close()

    if plot_count == 0:
        return "The government land treaty was signed, but there were no plots to transfer."

    # ── 2. Find the highest-value foreign reserve currency ───────────────────
    res_db = _rdb()
    try:
        banks = res_db.query(_SRB).all()
        foreign = [b for b in banks if b.currency_code != "USD"]
        best = max(foreign, key=lambda b: b.usd_per_unit) if foreign else (
            next((b for b in banks if b.currency_code == "USD"), None)
        )
        if not best:
            raise ValueError("No reserve banks found")
        currency_code   = best.currency_code
        usd_per_unit    = best.usd_per_unit or 1.0
        foreign_amount  = sale_usd / usd_per_unit
        currency_symbol = best.currency_symbol or currency_code
        flag            = best.flag_emoji or ""

        # ── 3. Credit government (player_id=0) ──────────────────────────────
        _adjust_currency_balance(res_db, 0, currency_code, foreign_amount)
        res_db.commit()
    finally:
        res_db.close()

    # ── 4. Log to govt ledger ────────────────────────────────────────────────
    log_gov_event(
        event_type   = "foreign_land_sale",
        direction    = "in",
        amount       = sale_usd,
        currency     = currency_code,
        counterparty = "Foreign Sovereign Buyer",
        description  = (
            f"Land treaty (event: {ev.title}): {plot_count:,} plots sold, "
            f"10% value = {flag} {currency_symbol} {foreign_amount:,.2f} "
            f"@ {usd_per_unit:.6f} USD/{currency_code}"
        ),
    )

    print(
        f"[Events] foreign_land_sale: {plot_count:,} plots deleted "
        f"({auctions_cleared} auctions + {bank_cleared} land-bank rows cleared), "
        f"credited {flag} {currency_symbol} {foreign_amount:,.2f} {currency_code} "
        f"(≈ ${sale_usd:,.2f})"
    )

    return (
        f"The federal government has sold its land reserves to a foreign power. "
        f"{plot_count:,} plots transferred. Government received "
        f"{flag} {currency_symbol} {foreign_amount:,.2f} {currency_code} "
        f"(≈ ${sale_usd:,.2f} USD)."
    )


def resolve_land_grant_event(event_id: int) -> dict:
    """Score entries, assign tiers, transfer plots, notify all entrants."""
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        entries = db.query(LandGrantEntry).filter(
            LandGrantEntry.event_id == event_id,
        ).all()
        if not entries:
            return {"ok": True, "message": "No entries to resolve."}

        pending = [e for e in entries if not e.tier_awarded]
        if not pending:
            return {"ok": True, "message": "Already resolved."}

        try:
            from stats_ux import calculate_player_stats
        except Exception as _e:
            return {"ok": False, "message": f"Cannot import stats: {_e}"}

        scored = []
        for entry in pending:
            try:
                stats = calculate_player_stats(entry.player_id)
                current_nw = float(stats["total_net_worth"]) if stats else 0.0
            except Exception:
                current_nw = entry.net_worth_at_entry
            base = entry.net_worth_at_entry
            growth_pct = (current_nw - base) / base * 100.0 if base and base > 0 else 0.0
            scored.append((entry, growth_pct))

        scored.sort(key=lambda x: x[1], reverse=True)

        winners = []
        rank_pos = 0
        for tier in GRANT_TIERS:
            for _ in range(tier["winners"]):
                if rank_pos >= len(scored):
                    break
                winners.append((scored[rank_pos][0], tier["name"], tier["plots"]))
                rank_pos += 1

        winner_pids = {e.player_id for e, _, _ in winners}
        for entry, _ in scored:
            if entry.player_id not in winner_pids:
                entry.tier_awarded = "none"
                entry.plots_awarded = 0
                entry.awarded_at = now

        try:
            from land import LandPlot, SessionLocal as _LandDB
            ldb = _LandDB()
            try:
                gov_plots = ldb.query(LandPlot).filter(
                    LandPlot.is_government_owned == True
                ).all()
            finally:
                ldb.close()
        except Exception as _e:
            print(f"[LandGrant] land import error: {_e}")
            gov_plots = []

        from collections import defaultdict as _dd
        gov_by_terrain: dict = _dd(list)
        for p in gov_plots:
            gov_by_terrain[p.terrain_type].append(p)

        total_plots = 0
        n_winners = 0

        for entry, tier_name, plot_count in winners:
            entry.tier_awarded = tier_name
            entry.awarded_at = now

            if not gov_plots:
                print(f"[LandGrant] WARNING: no government plots available — skipping player {entry.player_id}")
                entry.plots_awarded = 0
                continue

            terrain = entry.preferred_terrain
            available = list(gov_by_terrain.get(terrain, [])) if terrain else []
            if len(available) < plot_count:
                fallback = [p for tlist in gov_by_terrain.values() for p in tlist]
                available = fallback if len(fallback) >= plot_count else fallback
                plot_count = min(plot_count, len(available))

            awarded = available[:plot_count]
            entry.plots_awarded = len(awarded)

            try:
                from land import LandPlot as _LP, SessionLocal as _LandDB2
                ldb2 = _LandDB2()
                try:
                    for plot in awarded:
                        p = ldb2.query(_LP).filter(_LP.id == plot.id).first()
                        if p:
                            p.owner_id = entry.player_id
                            p.is_government_owned = False
                            t = p.terrain_type
                            if t in gov_by_terrain and plot in gov_by_terrain[t]:
                                gov_by_terrain[t].remove(plot)
                    ldb2.commit()
                except Exception as _e2:
                    ldb2.rollback()
                    print(f"[LandGrant] plot transfer error for player {entry.player_id}: {_e2}")
                    entry.plots_awarded = 0
                finally:
                    ldb2.close()
            except Exception as _e:
                print(f"[LandGrant] land import error during transfer: {_e}")
                entry.plots_awarded = 0

            if entry.plots_awarded > 0:
                total_plots += entry.plots_awarded
                n_winners += 1
                try:
                    from stats_ux import log_transaction
                    log_transaction(
                        entry.player_id, "land_grant_award", "events", 0.0,
                        description=f"Federal Development Grant — {tier_name} tier: {entry.plots_awarded} plots",
                        reference_id=f"grant-{event_id}",
                        item_type="land", quantity=float(entry.plots_awarded),
                    )
                except Exception as _e:
                    print(f"[LandGrant] log_transaction award error: {_e}")

                # Award trophies for winning
                tier_data = next((t for t in GRANT_TIERS if t["name"] == tier_name), None)
                trophy_count = tier_data["trophy_reward"] if tier_data else 0
                if trophy_count > 0:
                    try:
                        rank = db.query(PlayerRank).filter(
                            PlayerRank.player_id == entry.player_id
                        ).first()
                        if not rank:
                            rank = PlayerRank(player_id=entry.player_id, trophies=0, level=1)
                            db.add(rank)
                        rank.trophies = (rank.trophies or 0) + trophy_count
                        level = 1
                        for i, threshold in enumerate(LEVEL_THRESHOLDS):
                            if rank.trophies >= threshold:
                                level = i + 2
                            else:
                                break
                        rank.level = level
                        rank.updated_at = now
                        from stats_ux import log_transaction as _lt2
                        _lt2(
                            entry.player_id, "trophy_award", "events", 0.0,
                            description=f"Federal Development Grant — {tier_name} tier winner",
                            reference_id=f"grant-{event_id}",
                            item_type="trophy", quantity=float(trophy_count),
                        )
                    except Exception as _e:
                        print(f"[LandGrant] trophy award error for player {entry.player_id}: {_e}")

        db.commit()

        if total_plots > 0:
            try:
                from govt_ledger import log_gov_event
                log_gov_event(
                    "land_grant_disbursement", "out", float(total_plots),
                    "USD", "Federal Development Grant",
                    f"{total_plots} plots to {n_winners} winners",
                )
            except Exception as _e:
                print(f"[LandGrant] log_gov_event error: {_e}")

        for entry, growth_pct in scored:
            tier = entry.tier_awarded
            if tier and tier != "none":
                _td = next((t for t in GRANT_TIERS if t["name"] == tier), None)
                _tc = _td["trophy_reward"] if _td else 0
                p_title = "Federal Development Grant — Winner!"
                p_body = (
                    f"🏆 {tier.title()} tier — {entry.plots_awarded} plot(s) awarded"
                    + (f" + {_tc} trophies!" if _tc else "!")
                )
            else:
                p_title = "Federal Development Grant — Results"
                p_body = "The event has ended. Check the leaderboard to see the results."
            try:
                from push_ux import send_push_notification, create_game_notification
                send_push_notification(
                    entry.player_id, p_title, p_body,
                    url=f"/events/land-grant/{event_id}",
                    notif_type="tasks_events",
                    tag=f"grant-result-{event_id}-{entry.player_id}",
                )
                create_game_notification(
                    entry.player_id, p_title, p_body,
                    url=f"/events/land-grant/{event_id}",
                    notif_type="tasks_events",
                )
            except Exception as _e:
                print(f"[LandGrant] notification error for player {entry.player_id}: {_e}")

        return {"ok": True, "message": f"Resolved: {n_winners} winner(s), {total_plots} plots awarded."}
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        print(f"[LandGrant] resolve error: {e}")
        return {"ok": False, "message": str(e)}
    finally:
        db.close()


def get_land_grant_leaderboard(event_id: int) -> list:
    """Return sorted list of entries with current growth % for live display."""
    db = SessionLocal()
    try:
        entries = db.query(LandGrantEntry).filter(
            LandGrantEntry.event_id == event_id,
        ).all()
        if not entries:
            return []

        try:
            from stats_ux import calculate_player_stats
            from auth import Player, get_db as _auth_db
            adb = _auth_db()
            try:
                pnames = {
                    p.id: (p.business_name or getattr(p, 'username', None) or f"Player {p.id}")
                    for p in adb.query(Player).filter(
                        Player.id.in_([e.player_id for e in entries])
                    ).all()
                }
            finally:
                adb.close()
        except Exception:
            pnames = {}
            calculate_player_stats = None

        rows = []
        for entry in entries:
            try:
                if calculate_player_stats:
                    stats = calculate_player_stats(entry.player_id)
                    current_nw = float(stats["total_net_worth"]) if stats else 0.0
                else:
                    current_nw = entry.net_worth_at_entry
            except Exception:
                current_nw = entry.net_worth_at_entry
            base = entry.net_worth_at_entry
            growth_pct = (current_nw - base) / base * 100.0 if base and base > 0 else 0.0
            rows.append({
                "player_id":          entry.player_id,
                "player_name":        pnames.get(entry.player_id, f"Player {entry.player_id}"),
                "net_worth_at_entry": entry.net_worth_at_entry,
                "current_net_worth":  current_nw,
                "growth_pct":         round(growth_pct, 4),
                "tier_awarded":       entry.tier_awarded,
                "plots_awarded":      entry.plots_awarded,
                "entered_at":         entry.entered_at.isoformat() if entry.entered_at else None,
            })

        rows.sort(key=lambda r: r["growth_pct"], reverse=True)
        for i, row in enumerate(rows):
            row["rank"] = i + 1
        return rows
    except Exception as e:
        print(f"[LandGrant] leaderboard error: {e}")
        return []
    finally:
        db.close()


def _on_event_live(event_id: int):
    """Timer callback: fires when a scheduled event's starts_at arrives."""
    import json as _json
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
            if ev.event_type == "land_grant":
                body = (
                    "The Federal Development Grant is now open for entry! "
                    f"Spend {GRANT_ENTRY_COST_TROPHIES} trophies to compete on net worth growth "
                    "and win government land plots."
                )
            elif ev.event_type == "index_challenge":
                _snapshot_index_challenge_members(db, ev)
                db.commit()
            elif ev.event_type == "item_crisis":
                try:
                    ed = _json.loads(ev.effect_data or "{}")
                    item_type = ed.get("item_type", "")
                    pf = ed.get("production_factor", 1.0)
                    drop_pct = round((1.0 - pf) * 100)
                    if item_type and drop_pct > 0:
                        item_name = _get_item_display_name(item_type)
                        body = (
                            f"Cartel violence has disrupted {item_name} supply chains. "
                            f"Production output reduced by {drop_pct}%. "
                            f"Prices may rise — check your businesses."
                        )
                except Exception:
                    pass
                invalidate_effects_cache()
            elif ev.event_type == "foreign_land_sale":
                try:
                    _fls_result = _execute_foreign_land_sale(ev)
                    body = _fls_result
                except Exception as _fls_e:
                    print(f"[Events] foreign_land_sale error: {_fls_e}")
                    body = "The government has concluded a foreign land treaty."
                # One-shot event: deactivate immediately so it never lingers as
                # "live" and can't re-fire on a server-restart rearm.
                ev.is_active = False
                ev.ends_at   = datetime.utcnow()
                db.commit()
                invalidate_effects_cache()
                cancel_event_timers(event_id)
    except Exception as e:
        print(f"[Events] _on_event_live DB error: {e}")
    finally:
        db.close()
    if title:
        broadcast_event_push(event_id, title, body, tag=f"event-{event_id}-live")


def _on_event_ended(event_id: int):
    """Timer callback: fires when an event's ends_at arrives."""
    import json as _json
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
            if ev.event_type == "land_grant":
                try:
                    result = resolve_land_grant_event(event_id)
                    print(f"[Events] land_grant auto-resolve: {result}")
                except Exception as _rge:
                    print(f"[Events] land_grant auto-resolve error: {_rge}")
                body = "The Federal Development Grant has ended. Winners have been notified and plots awarded!"
            elif ev.event_type == "item_crisis":
                try:
                    ed = _json.loads(ev.effect_data or "{}")
                    item_type = ed.get("item_type", "")
                    if item_type:
                        item_name = _get_item_display_name(item_type)
                        body = (
                            f"The {item_name} Crisis has resolved. "
                            f"Production output returns to normal levels."
                        )
                except Exception:
                    pass
                invalidate_effects_cache()
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


import json as _json_mod

_DEFAULT_SPECIAL_EVENTS = [
    {
        "title":          "Marketplace Shutdown",
        "description":    (
            "A rapidly spreading pandemic has forced health authorities to issue an emergency "
            "order closing all commodity and district markets until further notice. "
            "All pending buy and sell orders have been cancelled. Markets will reopen "
            "once the public health emergency is lifted."
        ),
        "duration_class": "special",
        "event_type":     "market",
        "effect_data":    {"market_shutdown": True},
        "trophy_reward":  0,
    },
    {
        "title":          "Crypto Scam",
        "description":    (
            "A limited-time event where you can purchase WSC (Wadsworth Stable Coin) "
            "directly with your cash. WSC is pegged at $1.00 USD — your cash is burned "
            "instantly to mint whole WSC units. You may spend up to 90% of your available "
            "cash balance. Use the buy panel on this card to enter an amount, preview the "
            "cost in your currency, and confirm the purchase."
        ),
        "duration_class": "special",
        "event_type":     "crypto_scam",
        "effect_data":    {"type": "crypto_scam", "wsc_pool": 10000},
        "trophy_reward":  0,
    },
]

_DEFAULT_WEEKLY_TASKS = [
    {
        "title":          "Meme Token Buyer",
        "description":    (
            "Spend $2,500 USD equivalent buying any meme token on the meme coin "
            "order book. Purchases are tracked in real-time at current native token "
            "prices. Every fill counts — market and limit orders both apply."
        ),
        "duration_class": "weekly",
        "event_type":     "task",
        "task_metric":    "meme_buy_usd",
        "task_target":    2500.0,
        "trophy_reward":  5,
    },
    {
        "title":          "Executive Shuffle",
        "description":    (
            "Fire or hire at least one executive this week. The boardroom never "
            "sleeps — shake up your leadership team to complete this task."
        ),
        "duration_class": "weekly",
        "event_type":     "task",
        "task_metric":    "executive_action",
        "task_target":    1.0,
        "trophy_reward":  3,
    },
    {
        "title":          "Tax Contributor",
        "description":    (
            "Accumulate $15,000 in sales tax deducted from your sell orders on "
            "the market and district market combined. Sales tax is automatically "
            "taken from your proceeds each time a sell order fills — no special "
            "setup required. Sell more volume to reach the target faster."
        ),
        "duration_class": "weekly",
        "event_type":     "task",
        "task_metric":    "market_sales_tax_usd",
        "task_target":    15000.0,
        "trophy_reward":  8,
    },
]


def _seed_default_tasks():
    """Create the default weekly task events and special events if they don't already exist."""
    db = SessionLocal()
    try:
        for data in _DEFAULT_WEEKLY_TASKS:
            existing = db.query(GameEvent).filter(
                GameEvent.task_metric    == data["task_metric"],
                GameEvent.duration_class == "weekly",
            ).first()
            if existing:
                continue
            ev = GameEvent(
                title          = data["title"],
                description    = data["description"],
                duration_class = data["duration_class"],
                event_type     = data["event_type"],
                task_metric    = data["task_metric"],
                task_target    = data["task_target"],
                trophy_reward  = data["trophy_reward"],
                is_active      = False,
                starts_at      = datetime(9999, 12, 31),
                ends_at        = None,
            )
            db.add(ev)

        for data in _DEFAULT_SPECIAL_EVENTS:
            existing = db.query(GameEvent).filter(
                GameEvent.event_type     == data["event_type"],
                GameEvent.duration_class == data["duration_class"],
                GameEvent.title          == data["title"],
            ).first()
            if existing:
                continue
            ev = GameEvent(
                title          = data["title"],
                description    = data["description"],
                duration_class = data["duration_class"],
                event_type     = data["event_type"],
                effect_data    = _json_mod.dumps(data.get("effect_data", {})),
                trophy_reward  = data.get("trophy_reward", 0),
                is_active      = False,
                starts_at      = datetime(9999, 12, 31),
                ends_at        = None,
            )
            db.add(ev)

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[Events] seed default tasks failed: {e}")
    finally:
        db.close()


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
    _seed_default_tasks()
    _rearm_on_startup()


def tick(current_tick, now):
    """No-op — notifications are fired by admin actions and threading.Timer."""
    pass
