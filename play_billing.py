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
    from database import engine, run_ddl_migration
    run_ddl_migration(engine, [
        """CREATE TABLE IF NOT EXISTS play_subscriptions (
                id              SERIAL PRIMARY KEY,
                player_id       INTEGER NOT NULL,
                purchase_token  TEXT    NOT NULL UNIQUE,
                product_id      TEXT    NOT NULL DEFAULT 'wads_basic',
                order_id        TEXT,
                sub_state       TEXT    NOT NULL DEFAULT 'ACTIVE',
                expiry_time     TIMESTAMPTZ,
                linked_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                last_verified   TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )""",
        "CREATE INDEX IF NOT EXISTS ix_play_sub_player ON play_subscriptions(player_id)",
    ])


def _upsert_subscription(player_id: int, token: str, product_id: str,
                         order_id: str | None, state: str,
                         expiry: datetime | None):
    from auth import get_db
    from sqlalchemy import text
    db = get_db()
    try:
        db.execute(text("""
            INSERT INTO play_subscriptions
                (player_id, purchase_token, product_id, order_id, sub_state, expiry_time, last_verified)
            VALUES (:pid, :tok, :prod, :oid, :state, :exp, NOW())
            ON CONFLICT (purchase_token) DO UPDATE SET
                sub_state     = EXCLUDED.sub_state,
                order_id      = EXCLUDED.order_id,
                expiry_time   = EXCLUDED.expiry_time,
                last_verified = NOW()
        """), dict(pid=player_id, tok=token, prod=product_id,
                   oid=order_id, state=state, exp=expiry))
        db.commit()
    finally:
        db.close()


def _set_subscriber(player_id: int, value: bool):
    from auth import get_db
    from sqlalchemy import text
    db = get_db()
    try:
        db.execute(
            text("UPDATE players SET subscriber = :v WHERE id = :pid"),
            dict(v=value, pid=player_id)
        )
        db.commit()
    finally:
        db.close()


def _player_id_for_token(token: str) -> int | None:
    """Reverse-lookup player from a purchase token (used by RTDN)."""
    from auth import get_db
    from sqlalchemy import text
    db = get_db()
    try:
        row = db.execute(
            text("SELECT player_id FROM play_subscriptions WHERE purchase_token = :tok"),
            dict(tok=token)
        ).fetchone()
        return row[0] if row else None
    finally:
        db.close()


def get_player_subscription(player_id: int) -> dict | None:
    """Return the most recent Play subscription record for a player, or None.

    Shape: {product_id, sub_state, expiry_time (datetime|None)}. Used by the
    Account → Subscription panel to show renewal/expiry info. Safe to call even
    if the table doesn't exist yet (returns None on any error)."""
    from auth import get_db
    from sqlalchemy import text
    db = get_db()
    try:
        row = db.execute(
            text("SELECT product_id, sub_state, expiry_time "
                 "FROM play_subscriptions WHERE player_id = :pid "
                 "ORDER BY last_verified DESC LIMIT 1"),
            dict(pid=player_id)
        ).fetchone()
        if not row:
            return None
        return {"product_id": row[0], "sub_state": row[1], "expiry_time": row[2]}
    except Exception:
        return None
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
        "SUBSCRIPTION_STATE_ACTIVE":          "ACTIVE",
        "SUBSCRIPTION_STATE_PENDING":         "PENDING",   # first payment still processing
        "SUBSCRIPTION_STATE_CANCELED":        "CANCELED",
        "SUBSCRIPTION_STATE_IN_GRACE_PERIOD": "IN_GRACE_PERIOD",
        "SUBSCRIPTION_STATE_ON_HOLD":         "ON_HOLD",
        "SUBSCRIPTION_STATE_PAUSED":          "PAUSED",
        "SUBSCRIPTION_STATE_EXPIRED":         "EXPIRED",
    }
    state = state_map.get(raw_state, "EXPIRED")
    log.info("verify_play_subscription: raw_state=%s → state=%s", raw_state, state)

    # Parse expiry FIRST — entitlement for a CANCELED sub depends on it.
    expiry = None
    items  = result.get("lineItems", [])
    if items:
        exp_str = items[0].get("expiryTime")
        if exp_str:
            try:
                expiry = datetime.fromisoformat(exp_str.replace("Z", "+00:00"))
            except ValueError:
                pass

    now = datetime.now(timezone.utc)
    expiry_in_future = expiry is not None and expiry > now

    # Entitlement rules:
    #   ACTIVE / IN_GRACE_PERIOD / PENDING → entitled (payment current, in grace, or
    #     first payment still processing).
    #   CANCELED → entitled ONLY while the paid-through period hasn't ended. A refund
    #     or revocation cancels the sub AND moves expiry into the past (or drops the
    #     line item entirely), so a refunded token correctly resolves to inactive.
    #     Without this expiry gate, the TWA re-verifying the cached (refunded) token
    #     on every app launch would keep flipping subscriber back to True forever.
    #   ON_HOLD / PAUSED / EXPIRED → not entitled (no current access).
    if state in ("ACTIVE", "IN_GRACE_PERIOD", "PENDING"):
        active = True
    elif state == "CANCELED":
        active = expiry_in_future
    else:
        active = False

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

    The whole body is wrapped so the client ALWAYS receives a JSON error
    string (never a plain-text 500 that the front-end can't parse).
    """
    try:
        from auth import get_player_from_session, get_db
        try:
            _db = get_db()
            try:
                player = get_player_from_session(_db, session_token)
            finally:
                _db.close()
        except Exception as exc:
            log.exception("verify-subscription: session lookup failed: %s", exc)
            return JSONResponse({"ok": False, "error": "session lookup failed: " + str(exc)}, status_code=500)
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
            return JSONResponse({"ok": False, "error": "billing not configured (key file missing on this server)"}, status_code=503)

        try:
            info = verify_play_subscription(token)
        except Exception as exc:
            log.exception("Play API error for player %d: %s", player.id, exc)
            return JSONResponse({"ok": False, "error": "Play API error: " + str(exc)[:200]}, status_code=502)

        # Persist state. Defensively ensure the table exists first — on a fresh
        # server (e.g. migrated to a new machine) init() may not have run yet.
        try:
            _ensure_table()
            _upsert_subscription(
                player_id  = player.id,
                token      = token,
                product_id = _SUB_ID,
                order_id   = info["order_id"],
                state      = info["state"],
                expiry     = info["expiry"],
            )
            _set_subscriber(player.id, info["active"])
        except Exception as exc:
            log.exception("verify-subscription: DB write failed for player %d: %s", player.id, exc)
            return JSONResponse({"ok": False, "error": "db write failed: " + str(exc)[:200]}, status_code=500)

        return JSONResponse({
            "ok":        True,
            "active":    info["active"],
            "state":     info["state"],
            "expiry":    info["expiry"].isoformat() if info["expiry"] else None,
        })
    except Exception as exc:
        log.exception("verify-subscription: unhandled error: %s", exc)
        return JSONResponse({"ok": False, "error": "server error: " + str(exc)[:200]}, status_code=500)


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

    # REVOKED (type 12) = refund / chargeback → strip entitlement immediately,
    # mid-cycle, regardless of what the re-verify returned (the Play API can lag).
    revoked = notif_type == 12
    final_active = False if revoked else info["active"]
    final_state  = "EXPIRED" if revoked else info["state"]

    _upsert_subscription(
        player_id  = player_id,
        token      = token,
        product_id = _SUB_ID,
        order_id   = info["order_id"],
        state      = final_state,
        expiry     = info["expiry"],
    )
    _set_subscriber(player_id, final_active)

    log.info("RTDN: player %d sub_state=%s active=%s (notif_type=%d, revoked=%s)",
             player_id, final_state, final_active, notif_type, revoked)
    return JSONResponse({"ok": True})


# ---------------------------------------------------------------------------
# Periodic revalidation sweep
# ---------------------------------------------------------------------------

_SWEEP_EVERY_TICKS = 17_280  # ~24 h at 5 s / tick


def revalidate_active_subscriptions() -> int:
    """Re-verify stale non-terminal subscriptions via the Play API.

    Picks up to 50 rows whose sub_state is not EXPIRED and whose last_verified
    is older than 23 hours, re-calls the Play API, and syncs subscriber flags.
    Returns the count processed. Safe to call when the key file is absent.
    """
    if not os.path.exists(_KEY_FILE):
        return 0
    from auth import get_db
    from sqlalchemy import text as _sql
    db = get_db()
    try:
        rows = db.execute(_sql(
            "SELECT player_id, purchase_token, product_id "
            "FROM play_subscriptions "
            "WHERE sub_state IN ('ACTIVE','CANCELED','IN_GRACE_PERIOD','ON_HOLD','PENDING') "
            "  AND last_verified < NOW() - INTERVAL '23 hours' "
            "ORDER BY last_verified ASC LIMIT 50"
        )).fetchall()
    finally:
        db.close()

    processed = 0
    for row in rows:
        player_id, token, product_id = row[0], row[1], row[2]
        try:
            info = verify_play_subscription(token)
            _upsert_subscription(player_id, token, product_id,
                                 info["order_id"], info["state"], info["expiry"])
            _set_subscriber(player_id, info["active"])
            log.info("sub_sweep: player %d → %s active=%s", player_id, info["state"], info["active"])
            processed += 1
        except Exception as exc:
            log.warning("sub_sweep: player %d token %.12s: %s", player_id, token, exc)
    return processed


def tick(tick_num: int, now) -> None:
    """Game-tick hook: run a subscription revalidation sweep once per day."""
    if tick_num % _SWEEP_EVERY_TICKS == 0:
        import threading
        threading.Thread(target=revalidate_active_subscriptions, daemon=True).start()


# ---------------------------------------------------------------------------
# Admin endpoints
# ---------------------------------------------------------------------------

@router.post("/api/admin/sub-resync/{player_id}")
async def api_admin_sub_resync(player_id: int,
                                session_token: Optional[str] = Cookie(None)):
    """Admin: force re-verify all Play subscription records for a specific player."""
    from auth import get_player_from_session, get_db
    from admins import is_admin
    from sqlalchemy import text as _sql
    db = get_db()
    try:
        requester = get_player_from_session(db, session_token)
    finally:
        db.close()
    if not requester or not is_admin(requester.id):
        return JSONResponse({"ok": False, "error": "unauthorized"}, status_code=403)

    if not os.path.exists(_KEY_FILE):
        return JSONResponse({"ok": False,
                             "error": "Play service account key not found on this server"})

    db = get_db()
    try:
        rows = db.execute(_sql(
            "SELECT purchase_token, product_id FROM play_subscriptions "
            "WHERE player_id = :pid ORDER BY last_verified DESC LIMIT 5"
        ), dict(pid=player_id)).fetchall()
    finally:
        db.close()

    if not rows:
        return JSONResponse({"ok": False,
                             "error": "No subscription records found for this player"})

    results = []
    final_active = False
    for token, product_id in rows:
        try:
            info = verify_play_subscription(token)
            _upsert_subscription(player_id, token, product_id,
                                 info["order_id"], info["state"], info["expiry"])
            _set_subscriber(player_id, info["active"])
            if info["active"]:
                final_active = True
            results.append({
                "token":   token[:14] + "…",
                "state":   info["state"],
                "active":  info["active"],
                "expiry":  info["expiry"].isoformat() if info["expiry"] else None,
            })
        except Exception as exc:
            results.append({"token": token[:14] + "…", "error": str(exc)[:120]})

    return JSONResponse({"ok": True, "subscriber_flag_now": final_active, "records": results})


@router.post("/api/admin/sub-grant/{player_id}")
async def api_admin_sub_grant(player_id: int,
                               session_token: Optional[str] = Cookie(None)):
    """Admin: manually grant Wadsworth Pro (comp or test)."""
    return await _admin_set_subscriber(player_id, True, session_token)


@router.post("/api/admin/sub-revoke/{player_id}")
async def api_admin_sub_revoke(player_id: int,
                                session_token: Optional[str] = Cookie(None)):
    """Admin: manually revoke Wadsworth Pro (fraud / refund enforcement)."""
    return await _admin_set_subscriber(player_id, False, session_token)


async def _admin_set_subscriber(player_id: int, value: bool,
                                 session_token: Optional[str]):
    from auth import get_player_from_session, get_db
    from admins import is_admin, log_action
    from fastapi.responses import RedirectResponse
    db = get_db()
    try:
        requester = get_player_from_session(db, session_token)
    finally:
        db.close()
    if not requester or not is_admin(requester.id):
        return JSONResponse({"ok": False, "error": "unauthorized"}, status_code=403)
    _set_subscriber(player_id, value)
    log_action(requester.id, "sub_override", player_id,
               f"subscriber manually set to {value}")
    return RedirectResponse(f"/admin/player/{player_id}?tab=info&msg=subscriber+set+to+{value}",
                            status_code=303)


# ---------------------------------------------------------------------------
# Called once at startup
# ---------------------------------------------------------------------------

def init():
    _ensure_table()
