"""
push_ux.py — Web Push / VAPID infrastructure for Wadsworth.

Routes:
  GET  /api/push/public-key            — VAPID public key (base64url)
  POST /api/push/subscribe             — Store a push subscription
  POST /api/push/unsubscribe           — Remove subscriptions
  GET  /api/notifications/unread-count — Total unread count for the authed player

Helper (called from other modules):
  send_push_notification(player_id, title, body, url, notif_type)

VAPID keys are auto-generated on first startup and stored in the system_config DB table,
or loaded from VAPID_PUBLIC_KEY / VAPID_PRIVATE_KEY environment variables if set.
Encryption is implemented per RFC 8291 + RFC 8188 (aes128gcm) using pycryptodome
for ECC / AES-GCM and stdlib hmac/hashlib for HKDF.
"""

import base64
import json
import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Cookie, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from database import engine, SessionLocal

router = APIRouter()

_Base = declarative_base()

class PlayerNotification(_Base):
    """In-game banner notifications — NOT Android push."""
    __tablename__ = "player_notifications"
    id         = Column(Integer, primary_key=True, index=True)
    player_id  = Column(Integer, index=True, nullable=False)
    title      = Column(String, nullable=False)
    body       = Column(String, nullable=False)
    url        = Column(String, default="/")
    notif_type = Column(String, default="general")
    is_seen    = Column(Boolean, default=False, index=True)
    cleared    = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

try:
    _Base.metadata.create_all(bind=engine)
except Exception as _e:
    print(f"[Push] Could not create player_notifications table: {_e}")

try:
    from sqlalchemy import text as _sqlt
    with engine.connect() as _mc:
        _mc.execute(_sqlt(
            "ALTER TABLE player_notifications "
            "ADD COLUMN IF NOT EXISTS cleared BOOLEAN NOT NULL DEFAULT FALSE"
        ))
        _mc.commit()
except Exception:
    pass

_KEYS_FILE = os.path.join(os.path.dirname(__file__), ".vapid_keys.json")
_VAPID_KEYS: Optional[dict] = None


# ── Base64url helpers ──────────────────────────────────────────────────────────

def _b64d(s: str) -> bytes:
    s = s + '=' * (4 - len(s) % 4)
    return base64.urlsafe_b64decode(s)


def _b64e(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b'=').decode()



# ── VAPID key management ───────────────────────────────────────────────────────

def _generate_keys() -> Optional[dict]:
    """Generate a fresh VAPID key pair using pycryptodome."""
    try:
        from Crypto.PublicKey import ECC
        priv = ECC.generate(curve='P-256')
        pub_point = priv.public_key().pointQ
        x_bytes = int(pub_point.x).to_bytes(32, 'big')
        y_bytes = int(pub_point.y).to_bytes(32, 'big')
        pub_bytes = b'\x04' + x_bytes + y_bytes
        priv_pem = priv.export_key(format='PEM', use_pkcs8=True)
        if isinstance(priv_pem, bytes):
            priv_pem = priv_pem.decode()
        return {"private_key": priv_pem, "public_key": _b64e(pub_bytes)}
    except Exception as e:
        print(f"[Push] VAPID key generation failed: {e}")
        return None


def _db_get_vapid_keys() -> Optional[dict]:
    """Load VAPID keys from the system_config table in the DB."""
    try:
        from database import engine
        from sqlalchemy import text
        with engine.connect() as c:
            row = c.execute(text(
                "SELECT value FROM system_config WHERE key = 'vapid_keys' LIMIT 1"
            )).fetchone()
        if row:
            return json.loads(row[0])
    except Exception:
        pass
    return None


def _db_save_vapid_keys(keys: dict) -> None:
    """Persist VAPID keys to the system_config table."""
    try:
        from database import engine
        from sqlalchemy import text
        val = json.dumps(keys)
        with engine.connect() as c:
            c.execute(text(
                "INSERT INTO system_config (key, value) VALUES ('vapid_keys', :v) "
                "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value"
            ), {"v": val})
            c.commit()
    except Exception as e:
        print(f"[Push] Could not persist VAPID keys to DB: {e}")


# ── In-game notification banners ──────────────────────────────────────────────
# Uses PlayerNotification ORM model (table created via create_all above).
# NOT sent as web push — shown only inside the game UI.

def create_game_notification(
    player_id: int,
    title: str,
    body: str,
    url: str = "/",
    notif_type: str = "general",
    cooldown_key: str = None,
    cooldown_secs: float = 0,
) -> None:
    """Store an in-game banner notification (not a web push).
    cooldown_key + cooldown_secs prevent duplicate banners within a time window."""
    if player_id <= 0:
        return
    if cooldown_key and cooldown_secs > 0:
        if not push_rate_ok(f"gn-{cooldown_key}", cooldown_secs):
            return
        push_rate_mark(f"gn-{cooldown_key}")
    try:
        db = SessionLocal()
        try:
            db.add(PlayerNotification(
                player_id=player_id, title=title, body=body,
                url=url, notif_type=notif_type,
            ))
            db.commit()
        finally:
            db.close()
    except Exception as e:
        print(f"[Push] create_game_notification error: {e}")


def get_game_notifications(player_id: int) -> list:
    """Return unseen, non-cleared in-game notifications (legacy — used by old callers)."""
    try:
        db = SessionLocal()
        try:
            rows = (
                db.query(PlayerNotification)
                .filter(
                    PlayerNotification.player_id == player_id,
                    PlayerNotification.is_seen == False,
                    PlayerNotification.cleared == False,
                )
                .order_by(PlayerNotification.id.desc())
                .limit(20)
                .all()
            )
            return [{"id": r.id, "title": r.title, "body": r.body,
                     "url": r.url, "notif_type": r.notif_type,
                     "is_seen": r.is_seen,
                     "created_at": r.created_at}
                    for r in rows]
        finally:
            db.close()
    except Exception as e:
        print(f"[Push] get_game_notifications error: {e}")
        return []


def get_all_game_notifications(player_id: int) -> list:
    """Return all non-cleared in-game notifications for a player, newest first."""
    try:
        db = SessionLocal()
        try:
            rows = (
                db.query(PlayerNotification)
                .filter(
                    PlayerNotification.player_id == player_id,
                    PlayerNotification.cleared == False,
                )
                .order_by(PlayerNotification.id.desc())
                .all()
            )
            return [{"id": r.id, "title": r.title, "body": r.body,
                     "url": r.url, "notif_type": r.notif_type,
                     "is_seen": r.is_seen,
                     "created_at": r.created_at}
                    for r in rows]
        finally:
            db.close()
    except Exception as e:
        print(f"[Push] get_all_game_notifications error: {e}")
        return []


def get_unread_game_notification_count(player_id: int) -> int:
    """Return count of unseen, non-cleared in-game notifications."""
    try:
        db = SessionLocal()
        try:
            return db.query(PlayerNotification).filter(
                PlayerNotification.player_id == player_id,
                PlayerNotification.is_seen == False,
                PlayerNotification.cleared == False,
            ).count()
        finally:
            db.close()
    except Exception as e:
        print(f"[Push] get_unread_game_notification_count error: {e}")
        return 0


def clear_game_notifications(player_id: int, ids=None) -> None:
    """Mark selected (or all) non-cleared notifications as cleared for a player."""
    try:
        db = SessionLocal()
        try:
            q = db.query(PlayerNotification).filter(
                PlayerNotification.player_id == player_id,
                PlayerNotification.cleared == False,
            )
            if ids is not None:
                q = q.filter(PlayerNotification.id.in_(ids))
            q.update({"cleared": True}, synchronize_session=False)
            db.commit()
        finally:
            db.close()
    except Exception as e:
        print(f"[Push] clear_game_notifications error: {e}")


def mark_game_notifications_seen(player_id: int) -> None:
    """Mark all unseen, non-cleared in-game notifications as seen for a player."""
    try:
        db = SessionLocal()
        try:
            db.query(PlayerNotification).filter(
                PlayerNotification.player_id == player_id,
                PlayerNotification.is_seen == False,
                PlayerNotification.cleared == False,
            ).update({"is_seen": True})
            db.commit()
        finally:
            db.close()
    except Exception as e:
        print(f"[Push] mark_game_notifications_seen error: {e}")


# ── Persistent push rate-limiting ─────────────────────────────────────────────
# Stored in the push_rate_limit table (key TEXT PK, last_sent REAL).
# Survives server restarts unlike in-memory dicts.

import time as _time

def _ensure_rate_limit_table() -> None:
    try:
        from database import engine
        from sqlalchemy import text
        with engine.connect() as c:
            c.execute(text(
                "CREATE TABLE IF NOT EXISTS push_rate_limit "
                "(key TEXT PRIMARY KEY, last_sent REAL NOT NULL)"
            ))
            c.commit()
    except Exception as e:
        print(f"[Push] Could not create push_rate_limit table: {e}")


def push_rate_ok(key: str, cooldown_secs: float) -> bool:
    """Return True if the notification identified by key is allowed (cooldown elapsed)."""
    try:
        from database import engine
        from sqlalchemy import text
        with engine.connect() as c:
            row = c.execute(
                text("SELECT last_sent FROM push_rate_limit WHERE key = :k"),
                {"k": key}
            ).fetchone()
        if row is None:
            return True
        return (_time.time() - row[0]) >= cooldown_secs
    except Exception:
        return True  # fail open — better to over-notify than silently drop


def push_rate_mark(key: str) -> None:
    """Record that a notification with key was just sent."""
    try:
        from database import engine
        from sqlalchemy import text
        with engine.connect() as c:
            c.execute(text(
                "INSERT INTO push_rate_limit (key, last_sent) VALUES (:k, :t) "
                "ON CONFLICT (key) DO UPDATE SET last_sent = EXCLUDED.last_sent"
            ), {"k": key, "t": _time.time()})
            c.commit()
    except Exception as e:
        print(f"[Push] Could not write rate limit for {key!r}: {e}")


def _load_or_create_vapid_keys() -> Optional[dict]:
    priv = os.environ.get("VAPID_PRIVATE_KEY")
    pub  = os.environ.get("VAPID_PUBLIC_KEY")
    if priv and pub:
        return {"private_key": priv, "public_key": pub}

    # 2. Load from DB (persists across restarts)
    keys = _db_get_vapid_keys()
    if keys:
        return keys

    # 3. Load from local file (dev fallback)
    if os.path.exists(_KEYS_FILE):
        try:
            with open(_KEYS_FILE) as f:
                keys = json.load(f)
            _db_save_vapid_keys(keys)   # migrate file → DB
            return keys
        except Exception:
            pass

    # 4. Generate new keys and store in DB + file
    keys = _generate_keys()
    if keys:
        _db_save_vapid_keys(keys)
        try:
            with open(_KEYS_FILE, "w") as f:
                json.dump(keys, f, indent=2)
        except Exception:
            pass
        print("[Push] Generated new VAPID key pair and stored in DB.")
        print(f"[Push] VAPID_PUBLIC_KEY={keys['public_key']}")
        print("[Push] Add VAPID_PUBLIC_KEY and VAPID_PRIVATE_KEY to env vars to pin these keys.")
    return keys


def get_vapid_keys() -> Optional[dict]:
    global _VAPID_KEYS
    if _VAPID_KEYS is None:
        _ensure_rate_limit_table()
        _VAPID_KEYS = _load_or_create_vapid_keys()
    return _VAPID_KEYS


# ── Push delivery via pywebpush ────────────────────────────────────────────────

def _send_web_push(endpoint: str, auth: str, p256dh: str, payload: str, private_pem: str) -> int:
    """Send an encrypted push notification via pywebpush. Returns HTTP status code."""
    from pywebpush import webpush, WebPushException
    from Crypto.PublicKey import ECC

    # pywebpush expects the raw base64url-encoded private scalar, not a PEM string
    priv = ECC.import_key(private_pem)
    raw_key = _b64e(int(priv.d).to_bytes(32, 'big'))

    subscription_info = {
        "endpoint": endpoint,
        "keys": {"auth": auth, "p256dh": p256dh},
    }
    try:
        resp = webpush(
            subscription_info=subscription_info,
            data=payload,
            vapid_private_key=raw_key,
            vapid_claims={"sub": "mailto:admin@wadsworth.game"},
            timeout=10,
        )
        return resp.status_code if resp else 201
    except WebPushException as e:
        if e.response is not None:
            return e.response.status_code
        raise


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.get("/api/push/public-key")
def api_push_public_key():
    keys = get_vapid_keys()
    if not keys:
        return PlainTextResponse("", status_code=503)
    return PlainTextResponse(keys["public_key"])


@router.post("/api/push/subscribe")
async def api_push_subscribe(
    request: Request,
    session_token: Optional[str] = Cookie(None),
):
    from auth import get_player_from_session, get_db, PushSubscription
    db = get_db()
    player = get_player_from_session(db, session_token)
    if not player:
        db.close()
        return JSONResponse({"error": "not authenticated"}, status_code=401)
    try:
        sub      = await request.json()
        endpoint = sub.get("endpoint", "")
        keys     = sub.get("keys", {})
        auth_key = keys.get("auth", "")
        p256dh   = keys.get("p256dh", "")
        if not endpoint:
            db.close()
            return JSONResponse({"error": "missing endpoint"}, status_code=400)
        existing = db.query(PushSubscription).filter_by(
            player_id=player.id, endpoint=endpoint
        ).first()
        if existing:
            existing.auth   = auth_key
            existing.p256dh = p256dh
        else:
            db.add(PushSubscription(
                player_id=player.id, endpoint=endpoint,
                auth=auth_key, p256dh=p256dh,
            ))
        db.commit()
        db.close()
        return JSONResponse({"ok": True})
    except Exception as e:
        db.close()
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/api/push/unsubscribe")
async def api_push_unsubscribe(
    request: Request,
    session_token: Optional[str] = Cookie(None),
):
    from auth import get_player_from_session, get_db, PushSubscription
    db = get_db()
    player = get_player_from_session(db, session_token)
    if not player:
        db.close()
        return JSONResponse({"error": "not authenticated"}, status_code=401)
    try:
        try:
            data = await request.json()
        except Exception:
            data = {}
        endpoint = data.get("endpoint")
        q = db.query(PushSubscription).filter_by(player_id=player.id)
        if endpoint:
            q = q.filter_by(endpoint=endpoint)
        q.delete()
        db.commit()
        db.close()
        return JSONResponse({"ok": True})
    except Exception as e:
        db.close()
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/api/avatar/{player_id}")
def api_player_avatar(player_id: int):
    """
    Serve a player's DM avatar as an image response so it can be used
    as a URL in Web Push notification `icon` fields (data URIs are not
    allowed there).  Falls back to a 1×1 transparent PNG if no avatar.
    """
    from chat import get_avatar
    import base64, re
    from fastapi.responses import Response

    data_uri = get_avatar(player_id)
    if data_uri:
        # data:[<mime>];base64,<data>
        m = re.match(r"data:([^;]+);base64,(.+)", data_uri, re.DOTALL)
        if m:
            mime   = m.group(1)
            raw    = base64.b64decode(m.group(2))
            return Response(content=raw, media_type=mime,
                            headers={"Cache-Control": "public, max-age=300"})
    # 1×1 transparent PNG fallback
    fallback = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhf"
        "DwAChwGA60e6kgAAAABJRU5ErkJggg=="
    )
    return Response(content=fallback, media_type="image/png",
                    headers={"Cache-Control": "public, max-age=60"})


@router.get("/api/notifications/unread-count")
def api_unread_count(session_token: Optional[str] = Cookie(None)):
    from auth import get_player_from_session, get_db
    db = get_db()
    player = get_player_from_session(db, session_token)
    if not player:
        db.close()
        return JSONResponse({"count": 0})
    try:
        from chat import get_unread_dm_count
        count = get_unread_dm_count(player.id)
    except Exception:
        count = 0
    db.close()
    return JSONResponse({"count": count})


# ── Server-side push sender ────────────────────────────────────────────────────

def send_push_notification(
    player_id: int,
    title: str,
    body: str,
    url: str = "/",
    notif_type: str = "general",
    tag: str = "wadsworth-notif",
    icon: Optional[str] = None,
):
    """
    Send an encrypted web push notification to all subscriptions for player_id.
    notif_type: 'dm' | 'contract' | 'general'
    tag: unique per notification group so each conversation/event gets its own card.
    icon: absolute URL for the notification icon (e.g. sender avatar). Falls back
          to /static/icons/icon-192.png in the service worker if omitted.
    """
    try:
        if player_id <= 0:
            return  # NPCs and government player have no push subscriptions
        from auth import get_db, PushSubscription, Player
        db = get_db()
        player = db.query(Player).filter_by(id=player_id).first()
        if not player:
            print(f"[Push] player {player_id} not found — skipping")
            db.close()
            return
        if notif_type == "dm" and not getattr(player, "notif_push_dms", True):
            print(f"[Push] DM notifications disabled for player {player_id} — skipping")
            db.close()
            return
        if notif_type == "contract" and not getattr(player, "notif_push_contracts", True):
            print(f"[Push] contract notifications disabled for player {player_id} — skipping")
            db.close()
            return
        if notif_type == "land" and not getattr(player, "notif_push_land", True):
            print(f"[Push] land notifications disabled for player {player_id} — skipping")
            db.close()
            return
        if notif_type == "execs" and not getattr(player, "notif_push_execs", True):
            print(f"[Push] exec notifications disabled for player {player_id} — skipping")
            db.close()
            return
        if notif_type == "trades" and not getattr(player, "notif_push_trades", True):
            print(f"[Push] trade notifications disabled for player {player_id} — skipping")
            db.close()
            return
        if notif_type == "corporate" and not getattr(player, "notif_push_corporate", True):
            print(f"[Push] corporate notifications disabled for player {player_id} — skipping")
            db.close()
            return
        if notif_type == "business" and not getattr(player, "notif_push_business", True):
            print(f"[Push] business notifications disabled for player {player_id} — skipping")
            db.close()
            return
        if notif_type == "govt" and not getattr(player, "notif_push_govt", True):
            print(f"[Push] govt notifications disabled for player {player_id} — skipping")
            db.close()
            return
        if notif_type == "tasks_events" and not getattr(player, "notif_push_tasks_events", True):
            print(f"[Push] tasks/events notifications disabled for player {player_id} — skipping")
            db.close()
            return
        if notif_type == "annuities" and not getattr(player, "notif_push_annuities", True):
            print(f"[Push] annuity notifications disabled for player {player_id} — skipping")
            db.close()
            return
        if notif_type == "institutions" and not getattr(player, "notif_push_institutions", True):
            print(f"[Push] institution notifications disabled for player {player_id} — skipping")
            db.close()
            return

        # Also write an in-game banner (same preference gates above already passed)
        try:
            _gn_db = SessionLocal()
            try:
                _gn_db.add(PlayerNotification(
                    player_id=player_id, title=title, body=body,
                    url=url, notif_type=notif_type,
                ))
                _gn_db.commit()
            finally:
                _gn_db.close()
        except Exception as _ge:
            print(f"[Push] in-game write error: {_ge}")

        subs = db.query(PushSubscription).filter_by(player_id=player_id).all()
        if not subs:
            print(f"[Push] no subscriptions for player {player_id} — they need to enable push in Settings")
            db.close()
            return

        keys = get_vapid_keys()
        if not keys:
            print(f"[Push] no VAPID keys — skipping")
            db.close()
            return

        sounds_on = getattr(player, "notif_sounds", True)
        payload_data: dict = {
            "title":  title,
            "body":   body,
            "url":    url,
            "tag":    tag,
            "silent": not sounds_on,   # sw.js sets silent flag; also triggers foreground MP3
        }
        if icon:
            payload_data["icon"] = icon
        payload  = json.dumps(payload_data)
        to_purge = []

        print(f"[Push] Sending to player {player_id} ({len(subs)} sub(s))…")
        for sub in subs:
            try:
                code = _send_web_push(sub.endpoint, sub.auth, sub.p256dh, payload, keys["private_key"])
                if code in (404, 410):
                    to_purge.append(sub.id)
                    print(f"[Push] Sub {sub.id} expired (HTTP {code}), purging")
                elif code >= 400:
                    print(f"[Push] HTTP {code} for player {player_id} sub {sub.id}")
                else:
                    print(f"[Push] Delivered to player {player_id} (HTTP {code})")
            except Exception as e:
                print(f"[Push] Error sending to player {player_id}: {e}")

        for sid in to_purge:
            db.query(PushSubscription).filter_by(id=sid).delete()
        if to_purge:
            db.commit()
        db.close()
    except Exception as e:
        print(f"[Push] send_push_notification error: {e}")
