"""
push_ux.py — Web Push / VAPID infrastructure for Wadsworth.

Routes:
  GET  /api/push/public-key            — VAPID public key (base64url)
  POST /api/push/subscribe             — Store a push subscription
  POST /api/push/unsubscribe           — Remove subscriptions
  GET  /api/notifications/unread-count — Total unread count for the authed player

Helper (called from other modules):
  send_push_notification(player_id, title, body, url, notif_type)

VAPID keys are auto-generated on first startup and stored in .vapid_keys.json.
Encryption is implemented per RFC 8291 + RFC 8188 (aes128gcm) using the
cryptography package — no pywebpush dependency needed.
"""

import base64
import json
import os
import struct
import time
from typing import Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Cookie, Request
from fastapi.responses import JSONResponse, PlainTextResponse

router = APIRouter()

_KEYS_FILE = os.path.join(os.path.dirname(__file__), ".vapid_keys.json")
_VAPID_KEYS: Optional[dict] = None


# ── VAPID key management ───────────────────────────────────────────────────────

def _b64d(s: str) -> bytes:
    s = s + '=' * (4 - len(s) % 4)
    return base64.urlsafe_b64decode(s)


def _b64e(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b'=').decode()


def _generate_keys() -> Optional[dict]:
    """Generate a fresh VAPID key pair using py_vapid + cryptography."""
    try:
        from py_vapid import Vapid
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
        v = Vapid()
        v.generate_keys()
        pub_bytes = v.public_key.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
        return {
            "private_key": v.private_pem().decode(),
            "public_key":  _b64e(pub_bytes),
        }
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
    # 1. Prefer env vars (Railway / production)
    priv = os.environ.get("VAPID_PRIVATE_KEY")
    pub  = os.environ.get("VAPID_PUBLIC_KEY")
    if priv and pub:
        return {"private_key": priv, "public_key": pub}

    # 2. Load from DB (survives Railway deploys)
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


# ── RFC 8291 payload encryption ────────────────────────────────────────────────

def _encrypt_push(plaintext: str, auth_b64: str, p256dh_b64: str) -> bytes:
    """
    Encrypt a push payload per RFC 8291 (WebPush) + RFC 8188 (aes128gcm).
    Returns the raw encrypted body bytes to POST.
    """
    from cryptography.hazmat.primitives.asymmetric.ec import (
        generate_private_key, ECDH, SECP256R1, EllipticCurvePublicKey,
    )
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF
    from cryptography.hazmat.primitives.hashes import SHA256
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
    from cryptography.hazmat.backends import default_backend

    backend = default_backend()

    auth_secret    = _b64d(auth_b64)
    recv_pub_bytes = _b64d(p256dh_b64)

    # Load recipient public key (uncompressed EC point)
    recv_pub = EllipticCurvePublicKey.from_encoded_point(SECP256R1(), recv_pub_bytes)

    # Ephemeral sender key pair
    sender_priv      = generate_private_key(SECP256R1(), backend)
    sender_pub       = sender_priv.public_key()
    sender_pub_bytes = sender_pub.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)

    # ECDH shared secret
    ecdh_secret = sender_priv.exchange(ECDH(), recv_pub)

    # Random 16-byte salt for content encryption
    salt = os.urandom(16)

    # IKM derivation — RFC 8291 §3.3
    ikm = HKDF(
        algorithm=SHA256(), length=32,
        salt=auth_secret,
        info=b"WebPush: info\x00" + recv_pub_bytes + sender_pub_bytes,
        backend=backend,
    ).derive(ecdh_secret)

    # CEK + nonce — RFC 8188 §2.3
    cek = HKDF(
        algorithm=SHA256(), length=16, salt=salt,
        info=b"Content-Encoding: aes128gcm\x00\x01",
        backend=backend,
    ).derive(ikm)
    nonce = HKDF(
        algorithm=SHA256(), length=12, salt=salt,
        info=b"Content-Encoding: nonce\x00\x01",
        backend=backend,
    ).derive(ikm)

    # Encrypt: plaintext + 0x02 padding delimiter
    ct = AESGCM(cek).encrypt(nonce, plaintext.encode('utf-8') + b'\x02', None)

    # aes128gcm content: salt(16) + rs(uint32be) + idlen(uint8) + key_id + ciphertext
    header = salt + struct.pack('>I', 4096) + bytes([len(sender_pub_bytes)]) + sender_pub_bytes
    return header + ct


def _send_web_push(endpoint: str, payload_bytes: bytes, vapid_private_pem: str) -> int:
    """POST an encrypted push message and return the HTTP status code."""
    import requests as _req
    from py_vapid import Vapid

    aud = urlparse(endpoint).scheme + "://" + urlparse(endpoint).netloc
    v   = Vapid.from_pem(vapid_private_pem.encode())
    auth_headers = v.sign({
        "sub": "mailto:admin@wadsworth.game",
        "aud": aud,
        "exp": int(time.time()) + 12 * 3600,
    })

    headers = {
        **auth_headers,
        "Content-Type":     "application/octet-stream",
        "Content-Encoding": "aes128gcm",
        "TTL":              "86400",
    }
    r = _req.post(endpoint, data=payload_bytes, headers=headers, timeout=10)
    return r.status_code


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
        data     = await request.json()
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
):
    """
    Send an encrypted web push notification to all subscriptions for player_id.
    notif_type: 'dm' | 'contract' | 'general'
    """
    try:
        from auth import get_db, PushSubscription, Player
        db = get_db()
        player = db.query(Player).filter_by(id=player_id).first()
        if not player:
            db.close()
            return
        if notif_type == "dm"       and not getattr(player, "notif_push_dms",       True):
            db.close()
            return
        if notif_type == "contract" and not getattr(player, "notif_push_contracts", True):
            db.close()
            return

        subs = db.query(PushSubscription).filter_by(player_id=player_id).all()
        if not subs:
            db.close()
            return

        keys = get_vapid_keys()
        if not keys:
            db.close()
            return

        payload  = json.dumps({"title": title, "body": body, "url": url})
        to_purge = []

        for sub in subs:
            try:
                enc   = _encrypt_push(payload, sub.auth, sub.p256dh)
                code  = _send_web_push(sub.endpoint, enc, keys["private_key"])
                if code in (404, 410):
                    to_purge.append(sub.id)
                elif code >= 400:
                    print(f"[Push] HTTP {code} for player {player_id} sub {sub.id}")
            except Exception as e:
                print(f"[Push] Error sending to player {player_id}: {e}")

        for sid in to_purge:
            db.query(PushSubscription).filter_by(id=sid).delete()
        if to_purge:
            db.commit()
        db.close()
    except Exception as e:
        print(f"[Push] send_push_notification error: {e}")
