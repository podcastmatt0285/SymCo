"""
bluesky.py

Bluesky / atproto account linking for Wadsworth (Phase 1 — identity only).

Players link and verify ownership of a Bluesky/atproto account, then opt in/out of
surfacing their handle + profile picture across the P2P system (contact card, DMs,
contract market, active contracts).

Design:
- Verification uses a Bluesky **App Password**: com.atproto.server.createSession is
  called once to prove ownership; we keep only the stable `did` + `handle` and discard
  the password and session JWTs. The app password is NEVER stored or logged.
- The avatar is hotlinked from the bsky CDN (we store the URL and render an <img>).
- Linking exposes nothing until the player toggles `show_on_p2p` on (default OFF).
- Self-contained module owning its own `bluesky_links` table (mirrors play_billing.py:
  CREATE TABLE via run_ddl_migration, raw SQL via text()). Other modules depend on the
  small render helpers here, not the reverse.
"""

from typing import Optional
from datetime import datetime, timedelta
import time
import html

import requests
from fastapi import APIRouter, Cookie, Form
from fastapi.responses import RedirectResponse

# ==========================
# CONSTANTS
# ==========================

# User's PDS for ownership verification (App Password -> createSession). bsky.social
# hosts the large majority of accounts; per-handle PDS discovery is a later enhancement.
BSKY_PDS = "https://bsky.social"
# Unauthenticated AppView for public reads (profile + avatar).
BSKY_PUBLIC = "https://public.api.bsky.app"

HTTP_TIMEOUT = 10  # seconds, applied to every outbound call
AVATAR_REFRESH_AFTER = timedelta(hours=24)  # staleness threshold for tick refresh
_CACHE_TTL = 30  # seconds; keeps per-row identity rendering off the DB hot path


# ==========================
# SCHEMA
# ==========================

def _ensure_table():
    from database import engine, run_ddl_migration
    run_ddl_migration(engine, [
        """CREATE TABLE IF NOT EXISTS bluesky_links (
                player_id     INTEGER     PRIMARY KEY,
                did           TEXT        NOT NULL,
                handle        TEXT        NOT NULL,
                avatar_url    TEXT,
                show_on_p2p   BOOLEAN     NOT NULL DEFAULT FALSE,
                linked_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                refreshed_at  TIMESTAMPTZ
            )""",
        # show_on_p2p == "show my handle" (available to all). show_avatar gates the
        # profile picture separately and is additionally Pro-gated at render time.
        "ALTER TABLE bluesky_links ADD COLUMN IF NOT EXISTS show_avatar BOOLEAN NOT NULL DEFAULT FALSE",
        # public_profile == the player opted into a public, shareable /player/{id}
        # snapshot page. Default OFF — linking alone exposes nothing publicly.
        "ALTER TABLE bluesky_links ADD COLUMN IF NOT EXISTS public_profile BOOLEAN NOT NULL DEFAULT FALSE",
        # banner_url == the player's Bluesky profile banner (used as the snapshot hero).
        # Empty string means "checked, none"; NULL means "not yet fetched".
        "ALTER TABLE bluesky_links ADD COLUMN IF NOT EXISTS banner_url TEXT",
    ])


def initialize():
    _ensure_table()
    print("[Bluesky] Account-linking module initialized")


# ==========================
# LINK STORAGE  (raw SQL, mirrors play_billing.py)
# ==========================

# player_id -> (expiry_epoch, link_dict_or_None). Short TTL so identity rendering across
# many rows (DM inbox, contract market) doesn't hit the DB once per name.
_link_cache: dict = {}


def _invalidate(player_id: int):
    _link_cache.pop(player_id, None)


def get_link(player_id: int) -> Optional[dict]:
    """Full link record for a player, or None if not linked. Short-TTL cached."""
    cached = _link_cache.get(player_id)
    if cached and cached[0] > time.time():
        return cached[1]

    from auth import get_db
    from sqlalchemy import text
    db = get_db()
    try:
        row = db.execute(text(
            "SELECT b.player_id, b.did, b.handle, b.avatar_url, b.banner_url, b.show_on_p2p, "
            "       b.show_avatar, b.public_profile, b.linked_at, "
            "       COALESCE(p.subscriber, FALSE) AS subscriber "
            "FROM bluesky_links b LEFT JOIN players p ON p.id = b.player_id "
            "WHERE b.player_id = :pid"
        ), {"pid": player_id}).mappings().first()
    finally:
        db.close()

    link = dict(row) if row else None
    _link_cache[player_id] = (time.time() + _CACHE_TTL, link)
    return link


def _is_pro_pid(player_id: int, link: Optional[dict] = None) -> bool:
    """True if the player has Wadsworth Pro (subscriber or admin). Uses the cached
    subscriber flag from get_link to avoid an extra query per render."""
    link = link if link is not None else get_link(player_id)
    if link and link.get("subscriber"):
        return True
    try:
        from admins import is_admin
        return bool(is_admin(player_id))
    except Exception:
        return False


def public_handle(player_id: int) -> Optional[str]:
    """The player's handle iff they opted into showing it (available to everyone)."""
    link = get_link(player_id)
    if link and link.get("show_on_p2p"):
        return link.get("handle")
    return None


def public_avatar(player_id: int) -> Optional[str]:
    """The player's avatar URL iff they opted in AND are Pro (profile picture is a
    Pro-gated perk). Gating is enforced here so every render site agrees."""
    link = get_link(player_id)
    if (link and link.get("show_avatar") and link.get("avatar_url")
            and _is_pro_pid(player_id, link)):
        return link.get("avatar_url")
    return None


def is_public_profile(player_id: int) -> bool:
    """True iff the player has linked Bluesky AND opted into a public snapshot page."""
    link = get_link(player_id)
    return bool(link and link.get("public_profile"))


def set_public_profile(player_id: int, on: bool):
    """Toggle the public snapshot page. No-op if the player has no link."""
    from auth import get_db
    from sqlalchemy import text
    db = get_db()
    try:
        db.execute(
            text("UPDATE bluesky_links SET public_profile = :v WHERE player_id = :pid"),
            {"v": bool(on), "pid": player_id},
        )
        db.commit()
    finally:
        db.close()
    _invalidate(player_id)


def public_banner(player_id: int, fetch_if_missing: bool = False) -> Optional[str]:
    """The player's Bluesky banner URL for a linked account, or None. Not Pro-gated —
    the snapshot page that uses it is itself opt-in. When fetch_if_missing is set and the
    banner has never been fetched (NULL), do a one-time lazy backfill so existing links
    get a banner without waiting for the refresh tick. '' is stored to mean "no banner"
    so we don't refetch every render."""
    link = get_link(player_id)
    if not link:
        return None
    url = link.get("banner_url")
    if url:
        return url
    if url is None and fetch_if_missing and link.get("did"):
        profile = fetch_profile(link["did"]) or {}
        _store_banner(player_id, profile.get("banner") or "")
        return profile.get("banner") or None
    return None


def _store_banner(player_id: int, banner_url: str):
    from auth import get_db
    from sqlalchemy import text
    db = get_db()
    try:
        db.execute(text("UPDATE bluesky_links SET banner_url = :b WHERE player_id = :pid"),
                   {"b": banner_url, "pid": player_id})
        db.commit()
    finally:
        db.close()
    _invalidate(player_id)


def upsert_link(player_id: int, did: str, handle: str, avatar_url: Optional[str],
                banner_url: Optional[str] = None):
    """Create or update a player's link, preserving the existing show_on_p2p preference
    on re-link. New links default to hidden (show_on_p2p stays FALSE)."""
    from auth import get_db
    from sqlalchemy import text
    db = get_db()
    try:
        db.execute(text("""
            INSERT INTO bluesky_links (player_id, did, handle, avatar_url, banner_url, refreshed_at)
            VALUES (:pid, :did, :handle, :avatar, :banner, NOW())
            ON CONFLICT (player_id) DO UPDATE SET
                did          = EXCLUDED.did,
                handle       = EXCLUDED.handle,
                avatar_url   = EXCLUDED.avatar_url,
                banner_url   = EXCLUDED.banner_url,
                refreshed_at = NOW()
        """), {"pid": player_id, "did": did, "handle": handle, "avatar": avatar_url,
               "banner": banner_url})
        db.commit()
    finally:
        db.close()
    _invalidate(player_id)


def set_visibility(player_id: int, show_handle: bool, show_avatar: bool):
    """Update both visibility switches. show_handle is available to everyone;
    show_avatar should only be set True for Pro players (callers enforce that)."""
    from auth import get_db
    from sqlalchemy import text
    db = get_db()
    try:
        db.execute(
            text("UPDATE bluesky_links SET show_on_p2p = :h, show_avatar = :a "
                 "WHERE player_id = :pid"),
            {"h": bool(show_handle), "a": bool(show_avatar), "pid": player_id},
        )
        db.commit()
    finally:
        db.close()
    _invalidate(player_id)


def delete_link(player_id: int):
    from auth import get_db
    from sqlalchemy import text
    db = get_db()
    try:
        db.execute(text("DELETE FROM bluesky_links WHERE player_id = :pid"), {"pid": player_id})
        db.commit()
    finally:
        db.close()
    _invalidate(player_id)


# ==========================
# ATPROTO HELPERS
# ==========================

def verify_app_password(handle: str, app_password: str) -> Optional[dict]:
    """Prove account ownership via a Bluesky App Password (createSession).

    Returns {"did", "handle"} on success and discards the JWTs + password. None on any
    failure. The password is used only for this single request and is never persisted.
    """
    handle = (handle or "").strip().lstrip("@")
    if not handle or not app_password:
        return None
    try:
        resp = requests.post(
            f"{BSKY_PDS}/xrpc/com.atproto.server.createSession",
            json={"identifier": handle, "password": app_password},
            timeout=HTTP_TIMEOUT,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        did = data.get("did")
        if not did:
            return None
        return {"did": did, "handle": data.get("handle", handle)}
    except Exception as e:
        print(f"[Bluesky] App-password verification failed: {e}")
        return None


def fetch_profile(actor: str, timeout: float = HTTP_TIMEOUT) -> Optional[dict]:
    """Fetch public profile (handle, displayName, avatar URL) for a did or handle."""
    if not actor:
        return None
    try:
        resp = requests.get(
            f"{BSKY_PUBLIC}/xrpc/app.bsky.actor.getProfile",
            params={"actor": actor},
            timeout=timeout,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        return {
            "did": data.get("did"),
            "handle": data.get("handle"),
            "displayName": data.get("displayName"),
            "avatar": data.get("avatar"),  # cdn.bsky.app URL or None
            "banner": data.get("banner"),  # cdn.bsky.app banner URL or None
        }
    except Exception as e:
        print(f"[Bluesky] Profile fetch failed: {e}")
        return None


def verify_link(method: str, **kwargs) -> Optional[dict]:
    """Swappable verification entry point -> canonical {"did","handle"} or None.
    Phase 1 supports "app_password"; "oauth" can be added here later without changing
    the callers."""
    if method == "app_password":
        return verify_app_password(kwargs.get("handle", ""), kwargs.get("app_password", ""))
    raise ValueError(f"Unknown verification method: {method}")


# ==========================
# RENDER HELPERS (used across the p2p system)
# ==========================

def avatar_img(player_id: int, size: int = 20, margin: bool = True) -> str:
    """Small inline avatar <img> for an opted-in Pro player, else "". Hotlinks the
    bsky CDN. URL is escaped defensively before injection into the attribute."""
    url = public_avatar(player_id)
    if not url:
        return ""
    mr = "margin-right:5px;" if margin else ""
    return (
        f'<img src="{html.escape(url, quote=True)}" alt="" '
        f'style="width:{size}px;height:{size}px;border-radius:50%;object-fit:cover;'
        f'vertical-align:middle;{mr}">'
    )


def handle_link(player_id: int, prefix: str = " ") -> str:
    """`@handle` link to the player's Bluesky profile for an opted-in player, else "".
    Handle is escaped defensively before injection into the href + text."""
    handle = public_handle(player_id)
    if not handle:
        return ""
    h = html.escape(handle, quote=True)
    return (
        f'{prefix}<a href="https://bsky.app/profile/{h}" target="_blank" '
        f'rel="noopener noreferrer" style="color:#38bdf8;font-size:0.78rem;'
        f'text-decoration:none;font-weight:normal;">@{h}</a>'
    )


# ==========================
# SETTINGS ROUTES (link / unlink / visibility toggle)
# ==========================

router = APIRouter()


def _require_auth(session_token):
    import auth
    db = auth.get_db()
    player = auth.get_player_from_session(db, session_token)
    db.close()
    return player


def _redirect_account(suffix: str = ""):
    return RedirectResponse(url=f"/settings?tab=account{suffix}", status_code=303)


@router.post("/api/settings/bluesky/link")
def bluesky_link(
    session_token: Optional[str] = Cookie(None),
    handle: str = Form(...),
    app_password: str = Form(...),
):
    player = _require_auth(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)

    verified = verify_link("app_password", handle=handle, app_password=app_password)
    # app_password goes out of scope here — never persisted or logged.
    if not verified:
        return _redirect_account("&bsky_err=1")
    profile = fetch_profile(verified["did"]) or {}
    handle_final = profile.get("handle") or verified["handle"]
    upsert_link(player.id, verified["did"], handle_final, profile.get("avatar"),
                banner_url=(profile.get("banner") or ""))
    return _redirect_account()


@router.post("/api/settings/bluesky/display")
def bluesky_display(
    session_token: Optional[str] = Cookie(None),
    show_handle: Optional[str] = Form(None),
    show_avatar: Optional[str] = Form(None),
):
    player = _require_auth(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)
    # Profile picture is a Pro-gated perk: only honor show_avatar for Pro players.
    want_avatar = show_avatar is not None
    if want_avatar:
        try:
            from skin_utils import is_pro
            if not is_pro(player):
                want_avatar = False
        except Exception:
            want_avatar = False
    set_visibility(player.id, show_handle is not None, want_avatar)
    return _redirect_account()


@router.post("/api/settings/bluesky/unlink")
def bluesky_unlink(session_token: Optional[str] = Cookie(None)):
    player = _require_auth(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)
    delete_link(player.id)
    return _redirect_account()


# ==========================
# BACKGROUND REFRESH
# ==========================

def tick(current_tick: int, now: datetime):
    """Periodically refresh handle + avatar URL for linked accounts (handles are mutable
    and hotlinked CDN URLs can rotate; the did is the stable key). Slow cadence + small
    batch keeps external HTTP out of the request hot path. ~hourly at the 5s tick.

    The actual network work runs in a DETACHED daemon thread so the main game tick loop is
    never blocked by outbound HTTP — previously, up to 10 sequential getProfile calls at a
    10s timeout could freeze the tick loop for ~45-100s when bsky egress was slow/blocked,
    which showed up as a 'SLOW module' and stalled the whole game."""
    if current_tick % 720 != 0:
        return
    import threading
    threading.Thread(target=_refresh_linked_accounts, args=(now,), daemon=True).start()


def _refresh_linked_accounts(now: datetime):
    """Background batch refresh of stale linked accounts. Runs off the tick loop."""
    from auth import get_db
    from sqlalchemy import text
    cutoff = now - AVATAR_REFRESH_AFTER
    db = get_db()
    try:
        rows = db.execute(text(
            "SELECT player_id, did FROM bluesky_links "
            "WHERE refreshed_at IS NULL OR refreshed_at < :cutoff LIMIT 5"
        ), {"cutoff": cutoff}).mappings().all()
        for r in rows:
            # Short per-call timeout so a slow/blocked endpoint can't drag the batch out.
            profile = fetch_profile(r["did"], timeout=4)
            if profile and profile.get("handle"):
                db.execute(text(
                    "UPDATE bluesky_links SET handle = :h, avatar_url = :a, banner_url = :b, "
                    "refreshed_at = NOW() WHERE player_id = :pid"
                ), {"h": profile["handle"], "a": profile.get("avatar"),
                    "b": (profile.get("banner") or ""), "pid": r["player_id"]})
            else:
                db.execute(text(
                    "UPDATE bluesky_links SET refreshed_at = NOW() WHERE player_id = :pid"
                ), {"pid": r["player_id"]})
            _invalidate(r["player_id"])
        db.commit()
    except Exception as e:
        print(f"[Bluesky] Refresh tick failed: {e}")
    finally:
        db.close()
