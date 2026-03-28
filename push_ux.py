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
from typing import Optional

from fastapi import APIRouter, Cookie, Request
from fastapi.responses import JSONResponse, PlainTextResponse

router = APIRouter()

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


def _load_or_create_vapid_keys() -> Optional[dict]:
    # 1. Prefer env vars (highest priority — pin keys across deploys)
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

        payload_data: dict = {"title": title, "body": body, "url": url, "tag": tag}
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
