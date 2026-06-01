"""
Wadsworth Skin System — Injection Utilities
===========================================
Imported by every shell function across all *_ux.py files.
Returns the <link> (and optional <script defer>) HTML tags that load the
skin CSS cascade for a given player.

Injection order (always this way):
  1. wadsworth-base.css   — shared component styles (Phase 2 extracts these)
  2. {skin}.css           — player's chosen skin (variables + optional component overrides)
  3. modules/{mod}.css    — page-group accent override (admin, executive, memecoins, mod)
  4. {skin}.js (deferred) — optional effects (particles, animations) if file exists

Cache busting: increment _SKIN_V on each deploy so browsers pick up updated files.
"""

import os as _os

_SKIN_V = 1  # ← increment on each deploy to bust browser CSS/JS cache


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
                skin = p.skin
        except Exception:
            pass
        finally:
            if db is not None:
                try:
                    db.close()
                except Exception:
                    pass

    v = _SKIN_V
    tags = (
        f'<link rel="stylesheet" href="/static/skins/wadsworth-base.css?v={v}">\n'
        f'        <link rel="stylesheet" href="/static/skins/{skin}.css?v={v}">'
    )
    if module:
        tags += (
            f'\n        <link rel="stylesheet"'
            f' href="/static/skins/modules/{module}.css?v={v}">'
        )
    if _os.path.exists(f"static/skins/{skin}.js"):
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
