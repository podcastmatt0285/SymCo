"""
beta.py
Founding-tester beta program for the Wadsworth Android app.

Three events:
  1. "Founding Operative" (special/task) — submit Google email, admin verifies
     group membership, approve → promo code delivered via persistent notification.
  2. "Pocket Empire"      (special/task) — first ever login from the TWA Android
     app after a code is issued → badge + trophies.
  3. "Active Duty"        (daily)        — log in from the TWA app on any day
     → daily trophy reward, resets at UTC midnight.

Events 1 & 2 end automatically when the last promo code is assigned.
"""

from datetime import datetime, date, timedelta
import json
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from database import engine, SessionLocal

Base = declarative_base()

# ── Constants ─────────────────────────────────────────────────────────────────

TWA_PACKAGE = "cc.notifly.wadsworth.twa"
PLAY_STORE_URL = "https://play.google.com/store/apps/details?id=cc.notifly.wadsworth.twa"
GOOGLE_GROUP_URL = "https://groups.google.com/g/wadstycoon"

FOUNDING_OPERATIVE_TROPHIES = 50
POCKET_EMPIRE_TROPHIES      = 100
ACTIVE_DUTY_TROPHIES        = 10

# Raw promo codes loaded from CSV
_RAW_CODES = [
    "Y3U603TZZNMW9Y29R8TYFW9", "UXG3NUMJZTKY7J6LJ76A820",
    "UFULN7YMQLDZDCV1MBD3NFV", "5ZS3WNLFD0FW2JKLCHTUJNT",
    "L0C3GU91Y10LTP2U8B5Z3R8", "NE11TUHX93Z2LQWMJR2M6AA",
    "SK5FE42HGSLWJWBUDUVMB4N", "YJCMEFVWHLCB1QSPNA1Y3VR",
    "2HV9M1UVE9HUXGGAF70ACMX", "KE6PSVRVBUYBT4KP5Q7FVEY",
    "C36UM33QCLWGXGZRBKT5BFT", "1JVS3M3G3TRK464L05MFBEE",
    "C5UUU8FTJWTHXPT0U8E73FC", "BKDB0PTQT8LES620DFUXUBL",
    "VKE6NHG6VJ5Q76DSYWP45TE", "XQTJ3G3JFA9VZW8VDVFXDEJ",
    "5DQ02DC4Z7E19Y247YSUNMX", "LT1YFMR71MKAQT4FBMWT21C",
    "9KUGQWVSMUL220GNA9ESH6B", "JV85N04934VBMFZQWXV7A85",
    "53CSRBA9B27UPF6AV8LFKVX", "JXJE6EVNUZ7VCB1XQ09J4EE",
    "N9YBVNSXX56KBRDBBKHGG4J", "HKYL7AZ7V3G70F9HM222AL5",
    "HN8UQNSV7SCB1XUBUK9BECA", "4333FZ6P170G3ARJWYV9406",
    "YSSD8E6VYFXFZ62R8HYN6FF", "Q1TCE4XM8LDDZ5VUCCYNRUP",
    "CC34QUMWHJMWJAVNAJB2A2T", "CS90NHQE4C7JM2LWBFQ4ZRA",
    "PH0SFGCPAT97MGFVYBZUY6P", "DMNA8376YUN6AM9BF503VF0",
    "34EMGJ1A5XBMAGRE1CJ3NJ0", "ZRDZ3G4AMTUNPZNG1KPDM5C",
    "BSUFPHKBKQAJ9CWHYU263EQ", "TC4W8AFU14M61SS5YKQTUKG",
    "QTB30HFQNQ6XYUNRBX0G040", "8PASL7ZT9U8BACKAPBBN29K",
    "FUM3AY2RF963J1QYKXKSDP7", "GK6H4TL89KUFATELX2R166P",
    "RKU53GC199TFA6ZNWF6S67L", "66M7HABJV7R3MQ0HW2SW7H7",
    "50BFHT3WL8JXPS9KYD9LR5K", "NBK6C2QG3CPHANSGSHVTWVV",
    "ZUSHDK3KJ88VFDF2UQ89SZA", "MQJXZB707M68UFL4ZQL1NVH",
    "5GN3WWNBPRYX6ATQEVHVT11", "9RM86CS05HJD9UF4ZENXEUE",
]

# ── Models ────────────────────────────────────────────────────────────────────

class PromoCode(Base):
    __tablename__ = "beta_promo_codes"

    id                    = Column(Integer, primary_key=True)
    code                  = Column(String, unique=True, nullable=False)
    status                = Column(String, default="available")  # available | assigned
    assigned_to_player_id = Column(Integer, nullable=True, index=True)
    assigned_at           = Column(DateTime, nullable=True)


class BetaRequest(Base):
    __tablename__ = "beta_requests"

    id            = Column(Integer, primary_key=True)
    player_id     = Column(Integer, nullable=False, index=True)
    google_email  = Column(String, nullable=False)
    status        = Column(String, default="pending")  # pending | approved | rejected
    promo_code_id = Column(Integer, ForeignKey("beta_promo_codes.id"), nullable=True)
    requested_at  = Column(DateTime, default=datetime.utcnow)
    reviewed_at   = Column(DateTime, nullable=True)
    reviewed_by   = Column(Integer, nullable=True)


class PersistentNotification(Base):
    """In-game notification that stays on the dashboard until the player dismisses it."""
    __tablename__ = "persistent_notifications"

    id           = Column(Integer, primary_key=True)
    player_id    = Column(Integer, nullable=False, index=True)
    notif_type   = Column(String, nullable=False)   # promo_code | general
    title        = Column(String, nullable=False)
    body         = Column(Text, nullable=False)
    payload_json = Column(Text, default="{}")       # {"code": "...", ...}
    dismissed    = Column(Boolean, default=False)
    created_at   = Column(DateTime, default=datetime.utcnow)


class DailyTWALogin(Base):
    """One row per player per UTC calendar day they logged in from the TWA app."""
    __tablename__ = "daily_twa_logins"

    id               = Column(Integer, primary_key=True)
    player_id        = Column(Integer, nullable=False, index=True)
    login_date       = Column(Date, nullable=False)
    trophies_awarded = Column(Integer, default=0)
    awarded_at       = Column(DateTime, default=datetime.utcnow)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _get_db():
    return SessionLocal()


def _award_trophies(player_id: int, amount: int, event_id: int = None) -> bool:
    """Add trophies to PlayerRank and recalculate level. Returns True on success."""
    try:
        from events import PlayerRank, PlayerTaskProgress, LEVEL_THRESHOLDS, SessionLocal as _ES
        edb = _ES()
        try:
            rank = edb.query(PlayerRank).filter(PlayerRank.player_id == player_id).first()
            if not rank:
                rank = PlayerRank(player_id=player_id, trophies=0, level=1)
                edb.add(rank)
            rank.trophies   += amount
            rank.updated_at  = datetime.utcnow()
            lv = 1
            for i, t in enumerate(LEVEL_THRESHOLDS):
                if rank.trophies >= t:
                    lv = i + 2
                else:
                    break
            rank.level = lv
            if event_id:
                prog = edb.query(PlayerTaskProgress).filter(
                    PlayerTaskProgress.player_id == player_id,
                    PlayerTaskProgress.event_id  == event_id,
                ).first()
                if not prog:
                    prog = PlayerTaskProgress(player_id=player_id, event_id=event_id,
                                              progress=1.0, trophies_awarded=amount,
                                              completed_at=datetime.utcnow())
                    edb.add(prog)
                else:
                    prog.progress         = (prog.progress or 0) + 1.0
                    prog.trophies_awarded = (prog.trophies_awarded or 0) + amount
                    prog.completed_at     = datetime.utcnow()
            edb.commit()
            return True
        finally:
            edb.close()
    except Exception as _e:
        import traceback
        print(f"[Beta] Trophy award error: {_e}")
        print(traceback.format_exc())
        return False


def _get_event_ids() -> dict:
    """Return {'founding': id, 'pocket': id, 'duty': id} from game_events table."""
    try:
        from events import GameEvent, SessionLocal as _ES
        edb = _ES()
        try:
            ids = {}
            for title, key in [
                ("Founding Operative", "founding"),
                ("Pocket Empire",      "pocket"),
                ("Active Duty",        "duty"),
            ]:
                row = edb.query(GameEvent).filter(GameEvent.title == title).first()
                if row:
                    ids[key] = row.id
            return ids
        finally:
            edb.close()
    except Exception:
        return {}


def _end_beta_events():
    """Mark Founding Operative and Pocket Empire as inactive — codes exhausted."""
    try:
        from events import GameEvent, SessionLocal as _ES
        edb = _ES()
        try:
            for title in ("Founding Operative", "Pocket Empire"):
                ev = edb.query(GameEvent).filter(GameEvent.title == title).first()
                if ev and ev.is_active:
                    ev.is_active = False
                    ev.ends_at   = datetime.utcnow()
            edb.commit()
        finally:
            edb.close()
    except Exception as _e:
        print(f"[Beta] End-events error: {_e}")


def _push_notify(player_id: int, title: str, body: str):
    import threading
    def _go():
        try:
            from push_ux import send_push_notification
            send_push_notification(player_id, title, body,
                                   url="/", notif_type="general",
                                   tag=f"beta-{player_id}")
        except Exception:
            pass
    threading.Thread(target=_go, daemon=True).start()


# ── Public API ────────────────────────────────────────────────────────────────

def get_available_count() -> int:
    db = _get_db()
    try:
        return db.query(PromoCode).filter(PromoCode.status == "available").count()
    finally:
        db.close()


def get_total_count() -> int:
    db = _get_db()
    try:
        return db.query(PromoCode).count()
    finally:
        db.close()


def get_player_request(player_id: int):
    """Return the player's BetaRequest row or None."""
    db = _get_db()
    try:
        return db.query(BetaRequest).filter(BetaRequest.player_id == player_id).first()
    finally:
        db.close()


def submit_request(player_id: int, google_email: str) -> tuple[bool, str]:
    """Player submits their Google account email for group verification."""
    email = google_email.strip().lower()
    if not email or "@" not in email:
        return False, "Please enter a valid Google account email address."

    db = _get_db()
    try:
        existing = db.query(BetaRequest).filter(BetaRequest.player_id == player_id).first()
        if existing:
            if existing.status == "approved":
                return False, "Your request has already been approved — check your notification."
            if existing.status == "pending":
                return False, "Your request is already pending review."
            if existing.status == "rejected":
                return False, "Your request was not approved. Contact support if you believe this is an error."

        if get_available_count() == 0:
            return False, "All founding tester slots have been filled. Check back for future programs."

        req = BetaRequest(player_id=player_id, google_email=email)
        db.add(req)
        db.commit()
        return True, "Request submitted! We'll verify your group membership and notify you in-game."
    finally:
        db.close()


def get_pending_requests() -> list:
    """Return pending requests with player names for admin review."""
    db = _get_db()
    try:
        rows = (db.query(BetaRequest)
                .filter(BetaRequest.status == "pending")
                .order_by(BetaRequest.requested_at.asc())
                .all())
        result = []
        from auth import Player, get_db as _adb
        adb = _adb()
        try:
            for r in rows:
                p = adb.query(Player).filter(Player.id == r.player_id).first()
                result.append({
                    "id":           r.id,
                    "player_id":    r.player_id,
                    "player_name":  p.business_name if p else f"#{r.player_id}",
                    "google_email": r.google_email,
                    "requested_at": r.requested_at.strftime("%Y-%m-%d %H:%M") if r.requested_at else "",
                })
        finally:
            adb.close()
        return result
    finally:
        db.close()


def get_all_requests() -> list:
    """Return all requests (any status) for admin history view."""
    db = _get_db()
    try:
        rows = (db.query(BetaRequest)
                .order_by(BetaRequest.requested_at.desc())
                .limit(100)
                .all())
        result = []
        codes_map = {r.id: r.code for r in db.query(PromoCode).all()}
        from auth import Player, get_db as _adb
        adb = _adb()
        try:
            for r in rows:
                p = adb.query(Player).filter(Player.id == r.player_id).first()
                result.append({
                    "id":           r.id,
                    "player_id":    r.player_id,
                    "player_name":  p.business_name if p else f"#{r.player_id}",
                    "google_email": r.google_email,
                    "status":       r.status,
                    "promo_code":   codes_map.get(r.promo_code_id, "") if r.promo_code_id else "",
                    "requested_at": r.requested_at.strftime("%Y-%m-%d %H:%M") if r.requested_at else "",
                    "reviewed_at":  r.reviewed_at.strftime("%Y-%m-%d %H:%M") if r.reviewed_at else "",
                })
        finally:
            adb.close()
        return result
    finally:
        db.close()


def approve_request(request_id: int, admin_id: int) -> tuple[bool, str]:
    """Assign a promo code, create persistent notification, award Founding Operative trophies."""
    db = _get_db()
    try:
        req = db.query(BetaRequest).filter(BetaRequest.id == request_id).first()
        if not req:
            return False, "Request not found."
        if req.status != "pending":
            return False, f"Request is already {req.status}."

        # Grab an available code
        code_row = (db.query(PromoCode)
                    .filter(PromoCode.status == "available")
                    .first())
        if not code_row:
            return False, "No promo codes remaining — all slots are filled."

        code_row.status                = "assigned"
        code_row.assigned_to_player_id = req.player_id
        code_row.assigned_at           = datetime.utcnow()

        req.status        = "approved"
        req.promo_code_id = code_row.id
        req.reviewed_at   = datetime.utcnow()
        req.reviewed_by   = admin_id

        # Persistent notification with the code
        notif_payload = json.dumps({
            "code":        code_row.code,
            "play_store":  PLAY_STORE_URL,
            "group_url":   GOOGLE_GROUP_URL,
        })
        notif = PersistentNotification(
            player_id  = req.player_id,
            notif_type = "promo_code",
            title      = "🎉 Your Founding Tester Code is Ready!",
            body       = (
                "You've been verified as a Founding Operative of Wadsworth. "
                "Use your exclusive Google Play promo code to download the Android app for free. "
                "Log in from the app to unlock the Pocket Empire badge and bonus trophies!"
            ),
            payload_json = notif_payload,
        )
        db.add(notif)
        db.commit()

        # Award Founding Operative trophies
        ev_ids = _get_event_ids()
        _award_trophies(req.player_id, FOUNDING_OPERATIVE_TROPHIES,
                        ev_ids.get("founding"))

        # Push notification so they know to check the dashboard
        _push_notify(req.player_id,
                     "🎉 Founding Operative — Code Ready",
                     "Your Google Play promo code is waiting in your dashboard!")

        remaining = get_available_count()
        if remaining == 0:
            _end_beta_events()

        return True, f"Approved. Code {code_row.code} assigned. {remaining} codes remaining."
    finally:
        db.close()


def reject_request(request_id: int, admin_id: int) -> tuple[bool, str]:
    db = _get_db()
    try:
        req = db.query(BetaRequest).filter(BetaRequest.id == request_id).first()
        if not req or req.status != "pending":
            return False, "Request not found or not pending."
        req.status      = "rejected"
        req.reviewed_at = datetime.utcnow()
        req.reviewed_by = admin_id
        db.commit()
        return True, "Request rejected."
    finally:
        db.close()


def get_player_notifications(player_id: int) -> list:
    """Return undismissed persistent notifications for the player."""
    db = _get_db()
    try:
        rows = (db.query(PersistentNotification)
                .filter(
                    PersistentNotification.player_id == player_id,
                    PersistentNotification.dismissed == False,
                )
                .order_by(PersistentNotification.created_at.desc())
                .all())
        result = []
        for r in rows:
            try:
                payload = json.loads(r.payload_json or "{}")
            except Exception:
                payload = {}
            result.append({
                "id":       r.id,
                "type":     r.notif_type,
                "title":    r.title,
                "body":     r.body,
                "payload":  payload,
            })
        return result
    finally:
        db.close()


def dismiss_notification(notif_id: int, player_id: int) -> bool:
    db = _get_db()
    try:
        n = db.query(PersistentNotification).filter(
            PersistentNotification.id        == notif_id,
            PersistentNotification.player_id == player_id,
        ).first()
        if not n:
            return False
        n.dismissed = True
        db.commit()
        return True
    finally:
        db.close()


def has_pocket_empire(player_id: int) -> bool:
    """True if the player has completed the Pocket Empire event (founding badge)."""
    try:
        ev_ids = _get_event_ids()
        ev_id  = ev_ids.get("pocket")
        if not ev_id:
            return False
        from events import PlayerTaskProgress, SessionLocal as _ES
        edb = _ES()
        try:
            prog = edb.query(PlayerTaskProgress).filter(
                PlayerTaskProgress.player_id  == player_id,
                PlayerTaskProgress.event_id   == ev_id,
                PlayerTaskProgress.completed_at != None,
            ).first()
            return prog is not None
        finally:
            edb.close()
    except Exception:
        return False


def handle_twa_login(player_id: int):
    """Awards daily Active Duty trophies. Called on every dashboard load;
    deduplicates to once per UTC calendar day per player."""
    if player_id <= 0:
        return
    today = date.today()
    db    = _get_db()
    try:
        already_today = db.query(DailyTWALogin).filter(
            DailyTWALogin.player_id  == player_id,
            DailyTWALogin.login_date == today,
        ).first()
        if already_today:
            print(f"[Beta] Active Duty already awarded today for player {player_id}")
            # Still check Pocket Empire below
        else:
            ev_ids  = _get_event_ids()
            print(f"[Beta] Awarding Active Duty to player {player_id}, event_id={ev_ids.get('duty')}")
            awarded = _award_trophies(player_id, ACTIVE_DUTY_TROPHIES, ev_ids.get("duty"))
            print(f"[Beta] _award_trophies returned {awarded}")
            if awarded:
                db.add(DailyTWALogin(
                    player_id        = player_id,
                    login_date       = today,
                    trophies_awarded = ACTIVE_DUTY_TROPHIES,
                ))
                db.commit()
                print(f"[Beta] Active Duty committed for player {player_id}")
                _push_notify(player_id, "⚔️ Active Duty",
                             f"+{ACTIVE_DUTY_TROPHIES} trophies for logging in today!")
            else:
                print(f"[Beta] Active Duty trophy award FAILED for player {player_id}")

        # Pocket Empire (first-ever app login as an approved tester)
        if not has_pocket_empire(player_id):
            req = (db.query(BetaRequest)
                   .filter(BetaRequest.player_id == player_id,
                           BetaRequest.status    == "approved")
                   .first())
            if req:
                ev_ids = _get_event_ids()
                _award_trophies(player_id, POCKET_EMPIRE_TROPHIES, ev_ids.get("pocket"))
                notif = PersistentNotification(
                    player_id    = player_id,
                    notif_type   = "general",
                    title        = "📱 Pocket Empire — Unlocked!",
                    body         = (
                        f"You've logged in from the Android app and earned {POCKET_EMPIRE_TROPHIES} trophies! "
                        "Your exclusive Founding Tester badge is now visible on your contact card."
                    ),
                    payload_json = "{}",
                )
                db.add(notif)
                db.commit()
                _push_notify(player_id, "📱 Pocket Empire Unlocked!",
                             f"Founding Tester badge applied. +{POCKET_EMPIRE_TROPHIES} trophies!")
    except Exception as _e:
        import traceback
        print(f"[Beta] handle_twa_login error for player {player_id}: {_e}")
        print(traceback.format_exc())
    finally:
        db.close()


def get_beta_stats() -> dict:
    """Summary stats for admin dashboard."""
    db = _get_db()
    try:
        total     = db.query(PromoCode).count()
        available = db.query(PromoCode).filter(PromoCode.status == "available").count()
        assigned  = total - available
        pending   = db.query(BetaRequest).filter(BetaRequest.status == "pending").count()
        approved  = db.query(BetaRequest).filter(BetaRequest.status == "approved").count()
        rejected  = db.query(BetaRequest).filter(BetaRequest.status == "rejected").count()
        twa_today = db.query(DailyTWALogin).filter(
            DailyTWALogin.login_date == date.today()
        ).count()
        return {
            "total": total, "available": available, "assigned": assigned,
            "pending": pending, "approved": approved, "rejected": rejected,
            "twa_today": twa_today,
        }
    finally:
        db.close()


# ── Lifecycle ─────────────────────────────────────────────────────────────────

def _seed_events():
    """Create the three beta events in game_events if they don't exist yet."""
    try:
        from events import GameEvent, SessionLocal as _ES
        edb = _ES()
        try:
            now = datetime.utcnow()
            for ev_def in [
                dict(
                    title          = "Founding Operative",
                    description    = (
                        "Join the Wadsworth Tycoon Google Group and submit your Google account "
                        "email to be verified as a Founding Tester. Once approved you'll receive "
                        "an exclusive Google Play promo code to download the Android app for free."
                    ),
                    duration_class = "special",
                    event_type     = "task",
                    starts_at      = now,
                    ends_at        = None,
                    trophy_reward  = FOUNDING_OPERATIVE_TROPHIES,
                    task_metric    = "beta_group_verified",
                    task_target    = float(len(_RAW_CODES)),
                    created_by     = 1,
                    is_active      = True,
                ),
                dict(
                    title          = "Pocket Empire",
                    description    = (
                        "Download the Wadsworth Android app using your promo code and log in "
                        "from the app for the first time. Earn trophies and unlock your permanent "
                        "Founding Tester badge — visible to every player on your contact card."
                    ),
                    duration_class = "special",
                    event_type     = "task",
                    starts_at      = now,
                    ends_at        = None,
                    trophy_reward  = POCKET_EMPIRE_TROPHIES,
                    task_metric    = "twa_first_login",
                    task_target    = float(len(_RAW_CODES)),
                    created_by     = 1,
                    is_active      = True,
                ),
                dict(
                    title          = "Active Duty",
                    description    = (
                        "Log in to Wadsworth from the Android app each day to earn daily trophies. "
                        "Resets at UTC midnight. Available to all Android app users."
                    ),
                    duration_class = "daily",
                    event_type     = "task",
                    starts_at      = now,
                    ends_at        = None,
                    trophy_reward  = ACTIVE_DUTY_TROPHIES,
                    task_metric    = "daily_twa_login",
                    task_target    = None,
                    created_by     = 1,
                    is_active      = True,
                ),
            ]:
                exists = edb.query(GameEvent).filter(
                    GameEvent.title == ev_def["title"]
                ).first()
                if not exists:
                    edb.add(GameEvent(**ev_def))
            edb.commit()
        finally:
            edb.close()
    except Exception as _e:
        print(f"[Beta] Event seed error: {_e}")


def initialize():
    Base.metadata.create_all(bind=engine)

    db = _get_db()
    try:
        existing = db.query(PromoCode).count()
        if existing == 0:
            for code in _RAW_CODES:
                db.add(PromoCode(code=code))
            db.commit()
            print(f"[Beta] Seeded {len(_RAW_CODES)} promo codes.")
        else:
            print(f"[Beta] {existing} promo codes already in DB.")
    finally:
        db.close()

    _seed_events()
    print("[Beta] Initialized.")


def tick(current_tick: int, now: datetime):
    """Auto-end beta events when codes run out (checked once per minute)."""
    if current_tick % 720 != 0:
        return
    try:
        if get_available_count() == 0:
            _end_beta_events()
    except Exception:
        pass
