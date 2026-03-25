"""
push_ux.py — Web Push / VAPID infrastructure for Wadsworth.

Routes:
  GET  /api/push/public-key            — VAPID public key (base64url)
  POST /api/push/subscribe             — Store a push subscription
  POST /api/push/unsubscribe           — Remove subscriptions
  GET  /api/notifications/unread-count — Total unread count for the authed player

Helper (called from other modules):
  send_push_notification(player_id, title, body, url, notif_type)

VAPID keys are auto-generated on first startup and stored in the system_config DB table.
Encryption is implemented per RFC 8291 + RFC 8188 (aes128gcm) using pycryptodome
for ECC / AES-GCM and stdlib hmac/hashlib for HKDF — no Rust-based dependencies needed.
"""

import base64
import hashlib
import hmac as _hmac
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


# ── Base64url helpers ──────────────────────────────────────────────────────────

def _b64d(s: str) -> bytes:
    s = s + '=' * (4 - len(s) % 4)
    return base64.urlsafe_b64decode(s)


def _b64e(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b'=').decode()


# ── HKDF (RFC 5869) via stdlib ─────────────────────────────────────────────────

def _hkdf_extract(salt: bytes, ikm: bytes) -> bytes:
    return _hmac.new(salt, ikm, hashlib.sha256).digest()


def _hkdf_expand(prk: bytes, info: bytes, length: int) -> bytes:
    t = b''
    okm = b''
    counter = 1
    while len(okm) < length:
        t = _hmac.new(prk, t + info + bytes([counter]), hashlib.sha256).digest()
        okm += t
        counter += 1
    return okm[:length]


def _hkdf(salt: bytes, ikm: bytes, info: bytes, length: int) -> bytes:
    return _hkdf_expand(_hkdf_extract(salt, ikm), info, length)


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
    Uses pycryptodome for ECC/AES-GCM and stdlib hmac/hashlib for HKDF.
    Returns the raw encrypted body bytes to POST.
    """
    from Crypto.PublicKey import ECC
    from Crypto.Cipher import AES

    auth_secret    = _b64d(auth_b64)
    recv_pub_bytes = _b64d(p256dh_b64)

    # Load recipient public key from uncompressed EC point (0x04 || x || y)
    rx = int.from_bytes(recv_pub_bytes[1:33], 'big')
    ry = int.from_bytes(recv_pub_bytes[33:65], 'big')
    recv_pub = ECC.construct(curve='P-256', point_x=rx, point_y=ry)

    # Ephemeral sender key pair
    sender_priv = ECC.generate(curve='P-256')
    sp = sender_priv.public_key().pointQ
    sender_pub_bytes = b'\x04' + int(sp.x).to_bytes(32, 'big') + int(sp.y).to_bytes(32, 'big')

    # ECDH shared secret — x-coordinate of scalar multiplication
    shared_point = sender_priv.d * recv_pub.pointQ
    ecdh_secret  = int(shared_point.x).to_bytes(32, 'big')

    # Random 16-byte salt for content encryption
    salt = os.urandom(16)

    # IKM derivation — RFC 8291 §3.3
    ikm = _hkdf(
        salt=auth_secret,
        ikm=ecdh_secret,
        info=b"WebPush: info\x00" + recv_pub_bytes + sender_pub_bytes,
        length=32,
    )

    # CEK + nonce — RFC 8188 §2.3
    cek   = _hkdf(salt=salt, ikm=ikm, info=b"Content-Encoding: aes128gcm\x00\x01", length=16)
    nonce = _hkdf(salt=salt, ikm=ikm, info=b"Content-Encoding: nonce\x00\x01",     length=12)

    # Encrypt with AES-128-GCM; append 0x02 padding delimiter
    cipher = AES.new(cek, AES.MODE_GCM, nonce=nonce)
    ct, tag = cipher.encrypt_and_digest(plaintext.encode('utf-8') + b'\x02')

    # aes128gcm content: salt(16) + rs(uint32be) + idlen(uint8) + key_id + ciphertext+tag
    header = salt + struct.pack('>I', 4096) + bytes([len(sender_pub_bytes)]) + sender_pub_bytes
    return header + ct + tag


def _vapid_auth_header(private_pem: str, public_key_b64: str, endpoint: str) -> str:
    """
    Build a VAPID Authorization header using pycryptodome (ES256 JWT).
    Returns the full header value: 'vapid t=<JWT>,k=<pubkey>'
    """
    from Crypto.PublicKey import ECC
    from Crypto.Signature import DSS
    from Crypto.Hash import SHA256

    aud = urlparse(endpoint).scheme + "://" + urlparse(endpoint).netloc

    hdr    = _b64e(json.dumps({"typ": "JWT", "alg": "ES256"}, separators=(',', ':')).encode())
    claims = _b64e(json.dumps({
        "aud": aud,
        "exp": int(time.time()) + 12 * 3600,
        "sub": "mailto:admin@wadsworth.game",
    }, separators=(',', ':')).encode())

    signing_input = (hdr + "." + claims).encode()
    priv    = ECC.import_key(private_pem)
    signer  = DSS.new(priv, 'fips-186-3')
    h       = SHA256.new(signing_input)
    sig_raw = signer.sign(h)   # raw r||s (64 bytes for P-256)
    sig     = _b64e(sig_raw)

    return f"vapid t={hdr}.{claims}.{sig},k={public_key_b64}"


def _send_web_push(
    endpoint: str, payload_bytes: bytes, vapid_private_pem: str, public_key_b64: str
) -> int:
    """POST an encrypted push message and return the HTTP status code."""
    import requests as _req

    auth = _vapid_auth_header(vapid_private_pem, public_key_b64, endpoint)
    headers = {
        "Authorization":    auth,
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
                enc  = _encrypt_push(payload, sub.auth, sub.p256dh)
                code = _send_web_push(sub.endpoint, enc, keys["private_key"], keys["public_key"])
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
