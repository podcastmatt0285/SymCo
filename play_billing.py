"""
Google Play Billing — server-side subscription management
==========================================================
Handles the full lifecycle of Wadsworth Pro (wads_basic) subscriptions:

  POST /api/play/verify-subscription
      Called by the in-app Digital Goods API after a purchase or on every app
      launch (so reinstalls / account switches auto-restore entitlement).
      Verifies the purchaseToken with Google, persists state, sets
      player.subscriber = True.

  POST /api/play/rtdn
      Real-time Developer Notification webhook (Google Pub/Sub push).
      Handles renewals, cancellations, holds, and expirations so subscriber
      status stays in sync without the user needing to re-open the app.

Key: /etc/wadsworth/play-service-account.json  (never committed)
Env: GOOGLE_PLAY_SERVICE_ACCOUNT, PLAY_PACKAGE_NAME, PLAY_SUBSCRIPTION_ID
"""

import os
import json
import base64
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Request, Cookie
from fastapi.responses import JSONResponse
from typing import Optional

log = logging.getLogger(__name__)
router = APIRouter()

_PACKAGE   = os.environ.get("PLAY_PACKAGE_NAME",     "cc.notifly.wadsworth.twa")
_SUB_ID    = os.environ.get("PLAY_SUBSCRIPTION_ID",  "wads_basic")
_KEY_FILE  = os.environ.get("GOOGLE_PLAY_SERVICE_ACCOUNT",
                             "/etc/wadsworth/play-service-account.json")

# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _ensure_table():
    """Create play_subscriptions table if it doesn't exist."""
    from auth import get_db
    db = get_db()
    try:
        db.execute("""
            CREATE TABLE IF NOT EXISTS play_subscriptions (
                id              SERIAL PRIMARY KEY,
                player_id       INTEGER NOT NULL,
                purchase_token  TEXT    NOT NULL UNIQUE,
                product_id      TEXT    NOT NULL DEFAULT 'wads_basic',
                order_id        TEXT,
                sub_state       TEXT    NOT NULL DEFAULT 'ACTIVE',
                expiry_time     TIMESTAMPTZ,
                linked_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                last_verified   TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        db.execute(
            "CREATE INDEX IF NOT EXISTS ix_play_sub_player ON play_subscriptions(player_id)"
        )
        db.commit()
    finally:
        db.close()


def _upsert_subscription(player_id: int, token: str, product_id: str,
                         order_id: str | None, state: str,
                         expiry: datetime | None):
    from auth import get_db
    db = get_db()
    try:
        db.execute("""
            INSERT INTO play_subscriptions
                (player_id, purchase_token, product_id, order_id, sub_state, expiry_time, last_verified)
            VALUES (:pid, :tok, :prod, :oid, :state, :exp, NOW())
            ON CONFLICT (purchase_token) DO UPDATE SET
                sub_state     = EXCLUDED.sub_state,
                order_id      = EXCLUDED.order_id,
                expiry_time   = EXCLUDED.expiry_time,
                last_verified = NOW()
        """, dict(pid=player_id, tok=token, prod=product_id,
                  oid=order_id, state=state, exp=expiry))
        db.commit()
    finally:
        db.close()


def _set_subscriber(player_id: int, value: bool):
    from auth import get_db
    db = get_db()
    try:
        db.execute(
            "UPDATE players SET subscriber = :v WHERE id = :pid",
            dict(v=value, pid=player_id)
        )
        db.commit()
    finally:
        db.close()


def _player_id_for_token(token: str) -> int | None:
    """Reverse-lookup player from a purchase token (used by RTDN)."""
    from auth import get_db
    db = get_db()
    try:
        row = db.execute(
            "SELECT player_id FROM play_subscriptions WHERE purchase_token = :tok",
            dict(tok=token)
        ).fetchone()
        return row[0] if row else None
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Google Play Developer API
# ---------------------------------------------------------------------------

def _build_play_service():
    """Return an authenticated Google Play Developer API service object."""
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    creds = service_account.Credentials.from_service_account_file(
        _KEY_FILE,
        scopes=["https://www.googleapis.com/auth/androidpublisher"],
    )
    return build("androidpublisher", "v3", credentials=creds, cache_discovery=False)


def verify_play_subscription(purchase_token: str) -> dict:
    """
    Call the Play Developer API (subscriptionsv2) and return a normalised dict:
        {
          "state":   "ACTIVE" | "CANCELED" | "ON_HOLD" | "IN_GRACE_PERIOD" |
                     "PAUSED" | "EXPIRED",
          "expiry":  datetime (UTC) | None,
          "order_id": str | None,
          "active":  bool   — True while the user should have Pro entitlement
        }
    Raises on network/auth errors so the caller can return 500.
    """
    svc    = _build_play_service()
    result = (
        svc.purchases()
           .subscriptionsv2()
           .get(packageName=_PACKAGE, token=purchase_token)
           .execute()
    )

    # subscriptionsv2 response shape:
    #   result["subscriptionState"]  e.g. "SUBSCRIPTION_STATE_ACTIVE"
    #   result["lineItems"][0]["expiryTime"]  RFC3339
    raw_state = result.get("subscriptionState", "SUBSCRIPTION_STATE_EXPIRED")
    state_map = {
        "SUBSCRIPTION_STATE_ACTIVE":         "ACTIVE",
        "SUBSCRIPTION_STATE_CANCELED":       "CANCELED",
        "SUBSCRIPTION_STATE_IN_GRACE_PERIOD": "IN_GRACE_PERIOD",
        "SUBSCRIPTION_STATE_ON_HOLD":        "ON_HOLD",
        "SUBSCRIPTION_STATE_PAUSED":         "PAUSED",
        "SUBSCRIPTION_STATE_EXPIRED":        "EXPIRED",
    }
    state = state_map.get(raw_state, "EXPIRED")

    # Entitlement continues through grace period (user gets ~3-day buffer)
    active = state in ("ACTIVE", "CANCELED", "IN_GRACE_PERIOD")

    expiry = None
    items  = result.get("lineItems", [])
    if items:
        exp_str = items[0].get("expiryTime")
        if exp_str:
            try:
                expiry = datetime.fromisoformat(exp_str.replace("Z", "+00:00"))
            except ValueError:
                pass

    order_id = result.get("latestOrderId") or result.get("acknowledgementState")

    return {"state": state, "expiry": expiry, "order_id": order_id, "active": active}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/api/play/verify-subscription")
async def api_verify_subscription(request: Request,
                                   session_token: Optional[str] = Cookie(None)):
    """
    Called by the in-app Digital Goods API after purchase or on app launch
    to restore entitlement. Body: { "purchase_token": "..." }
    """
    from auth import get_session_player
    player = get_session_player(session_token)
    if not player:
        return JSONResponse({"ok": False, "error": "not authenticated"}, status_code=401)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"ok": False, "error": "invalid JSON"}, status_code=400)

    token = (body.get("purchase_token") or "").strip()
    if not token:
        return JSONResponse({"ok": False, "error": "missing purchase_token"}, status_code=400)

    if not os.path.exists(_KEY_FILE):
        log.error("Play service account key not found at %s", _KEY_FILE)
        return JSONResponse({"ok": False, "error": "billing not configured"}, status_code=503)

    try:
        info = verify_play_subscription(token)
    except Exception as exc:
        log.exception("Play API error for player %d: %s", player.id, exc)
        return JSONResponse({"ok": False, "error": "Play API error"}, status_code=502)

    _upsert_subscription(
        player_id  = player.id,
        token      = token,
        product_id = _SUB_ID,
        order_id   = info["order_id"],
        state      = info["state"],
        expiry     = info["expiry"],
    )
    _set_subscriber(player.id, info["active"])

    return JSONResponse({
        "ok":        True,
        "active":    info["active"],
        "state":     info["state"],
        "expiry":    info["expiry"].isoformat() if info["expiry"] else None,
    })


@router.post("/api/play/rtdn")
async def api_play_rtdn(request: Request):
    """
    Google Pub/Sub push endpoint for Real-time Developer Notifications.
    Google sends a POST with a base64-encoded DeveloperNotification in the
    Pub/Sub message envelope.  We decode it, look up the affected purchase
    token, re-verify with the Play API, and sync subscriber status.

    Set this URL in Play Console → Monetize → Subscriptions → RTDN:
        https://wadsworth.notifly.cc/api/play/rtdn
    """
    try:
        envelope = await request.json()
        data_b64 = envelope["message"]["data"]
        notification = json.loads(base64.b64decode(data_b64))
    except Exception as exc:
        log.warning("RTDN: could not decode message: %s", exc)
        # Return 200 so Pub/Sub doesn't keep retrying a malformed message
        return JSONResponse({"ok": False, "error": "decode error"})

    sub_notif = notification.get("subscriptionNotification")
    if not sub_notif:
        # Could be a test notification or a one-time product — ignore safely
        return JSONResponse({"ok": True, "skipped": True})

    token           = sub_notif.get("purchaseToken", "")
    notif_type      = sub_notif.get("notificationType", 0)
    # notificationType values:
    #  1=RECOVERED  2=RENEWED  3=CANCELED  4=PURCHASED  5=ON_HOLD
    #  6=IN_GRACE_PERIOD  7=RESTARTED  12=REVOKED  13=EXPIRED
    ACTIVE_TYPES  = {1, 2, 4, 7}    # renewal / purchase / restarted → verify & activate
    EXPIRED_TYPES = {3, 12, 13}     # cancel / revoke / expire → re-verify (may still be in grace)
    HOLD_TYPES    = {5, 6}          # on-hold / grace → re-verify (grace = still active)

    if not token:
        return JSONResponse({"ok": False, "error": "no token in notification"})

    if not os.path.exists(_KEY_FILE):
        log.error("RTDN: Play service account key not found")
        return JSONResponse({"ok": False, "error": "billing not configured"})

    # Re-verify with the API regardless of notificationType so our state
    # always reflects ground truth rather than trusting the notification alone.
    try:
        info = verify_play_subscription(token)
    except Exception as exc:
        log.exception("RTDN: Play API error for token %s: %s", token[:20], exc)
        return JSONResponse({"ok": False, "error": "Play API error"})

    player_id = _player_id_for_token(token)
    if player_id is None:
        # Token not in our DB yet — this can happen if RTDN arrives before the
        # user opens the app (e.g. renewal). We can't link to a player without
        # the obfuscatedExternalAccountId, so log and return 200.
        log.info("RTDN: unknown token %s (type %d) — no linked player",
                 token[:20], notif_type)
        return JSONResponse({"ok": True, "skipped": "unknown_token"})

    _upsert_subscription(
        player_id  = player_id,
        token      = token,
        product_id = _SUB_ID,
        order_id   = info["order_id"],
        state      = info["state"],
        expiry     = info["expiry"],
    )
    _set_subscriber(player_id, info["active"])

    log.info("RTDN: player %d sub_state=%s active=%s (notif_type=%d)",
             player_id, info["state"], info["active"], notif_type)
    return JSONResponse({"ok": True})


# ---------------------------------------------------------------------------
# Called once at startup
# ---------------------------------------------------------------------------

def init():
    _ensure_table()
