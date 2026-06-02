"""
Wadsworth Skin System — Injection Utilities
===========================================
Imported by every shell function across all *_ux.py files.
Returns the <link> (and optional <script defer>) HTML tags that load the
skin CSS cascade for a given player.

Injection order (always this way):
  1. wadsworth-base.css   — shared component styles
  2. {skin}.css           — player's chosen skin (variables + optional component overrides)
  3. modules/{mod}.css    — page-group accent override (admin, executive, memecoins, mod)
  4. {skin}.js (deferred) — optional effects (particles, animations) if file exists

Cache busting: increment _SKIN_V on each deploy so browsers pick up updated files.
"""

import os as _os
import re as _re
import time as _time

_SKIN_V = 7  # ← increment on each deploy to bust browser CSS/JS cache

# Only allow safe filesystem-compatible skin names — prevents XSS and path traversal
_SAFE_SKIN_RE = _re.compile(r'^[a-z][a-z0-9_-]*\Z')  # \Z not $ to reject trailing newlines

# Cache which skins have a companion .js effects file (avoids os.path.exists on hot path)
_js_skins: set = set()
_js_skins_ts: float = 0.0
_JS_SKINS_TTL: float = 60.0  # refresh once per minute


def _get_js_skins() -> set:
    """Return the set of skin names that have a companion .js effects file."""
    global _js_skins, _js_skins_ts
    now = _time.monotonic()
    if (now - _js_skins_ts) > _JS_SKINS_TTL:
        import glob as _glob
        _js_skins = {
            _os.path.basename(p)[:-3]
            for p in _glob.glob("static/skins/*.js")
        }
        _js_skins_ts = now
    return _js_skins


def skin_links(player_id: int = None, module: str = None) -> str:
    """Return skin <link>/<script> tags for injection in the page <head>.

    Args:
        player_id: Logged-in player's ID. None → 'default' skin (login page etc).
        module:    Optional module override name — 'admin', 'executive',
                   'memecoins', or 'mod'.
    """
    skin = "default"
    if player_id:
        db = None
        try:
            from auth import get_db, Player as _Player
            db = get_db()
            p = db.query(_Player).filter(_Player.id == player_id).first()
            if p and getattr(p, "skin", None):
                raw = p.skin
                # Sanitise: only accept names matching [a-z][a-z0-9_-]* to prevent
                # XSS (value in a <script> setAttribute call) and path traversal.
                if _SAFE_SKIN_RE.match(raw):
                    skin = raw
        except Exception:
            pass
        finally:
            if db is not None:
                try:
                    db.close()
                except Exception:
                    pass

    # Guard: if the skin CSS file has been deleted since it was saved to the DB,
    # fall back to default so the page never emits a 404 <link>.
    if skin != "default" and not _os.path.exists(f"static/skins/{skin}.css"):
        skin = "default"

    v = _SKIN_V
    # Synchronous script sets data-skin on <html> before any page <style>
    # blocks are parsed. This lets [data-skin="kawaii"] selectors in the
    # skin CSS win via higher specificity (0,2,0,0 vs page styles' 0,1,0,0).
    tags = (
        f'<script>document.documentElement.setAttribute("data-skin","{skin}");</script>\n'
        f'        <link rel="stylesheet" href="/static/skins/wadsworth-base.css?v={v}">\n'
        f'        <link rel="stylesheet" href="/static/skins/{skin}.css?v={v}" id="skin-link">'
    )
    if module:
        tags += (
            f'\n        <link rel="stylesheet"'
            f' href="/static/skins/modules/{module}.css?v={v}">'
        )
    if skin in _get_js_skins():
        tags += (
            f'\n        <script src="/static/skins/{skin}.js?v={v}"'
            f' defer></script>'
        )
    return tags


def is_pro(player) -> bool:
    """Return True if player has Wadsworth Pro entitlement.

    Entitlement = subscriber (Google Play purchase verified) OR admin
    (admins get Pro for free).
    """
    if getattr(player, "subscriber", False):
        return True
    try:
        from admins import is_admin
        return is_admin(player.id)
    except Exception:
        return False
