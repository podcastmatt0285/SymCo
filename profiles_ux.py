"""
profiles_ux.py — Public, shareable player "snapshot" profile.

A player who has linked a Bluesky account can opt into a public, shareable snapshot
page at /player/{id}. The page:
  - renders in that player's *own* in-game skin (via skin_utils.skin_links), so anyone
    — logged in or not — sees it themed;
  - reuses the existing P2P contact-card content (contacts.build_contact_card_html),
    re-skinned by mapping the card's fixed palette onto skin CSS variables, and laid out
    like a social-media profile;
  - exposes OpenGraph tags whose og:image is a skin-themed card PNG (rendered with Pillow),
    so the Bluesky feed shows an on-brand preview;
  - offers the owner a "Post Snapshot" button (opens Bluesky's composer pre-filled — no
    OAuth, nothing stored) and a "Copy Snapshot Link" button.

Gate: requires a linked Bluesky account + public_profile opt-in (default OFF). The owner
can always preview their own page (with controls) even while it is disabled.
"""

import os
import io
import re
import glob
import html
import hashlib
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Cookie, Form
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse

router = APIRouter()

# Absolute base used for share links + og:image (matches the og:image domain used across
# the app, e.g. auth.py / stats_ux.py).
SITE_BASE = "https://wadsworth.notifly.cc"

_CARD_CACHE_DIR = "static/cache/profile_cards"

# Per-skin logo (mirrors SKIN_SYSTEM mapping). Falls back to the default logo.
_SKIN_LOGOS = {
    "default":           "static/logo.png",
    "dark_nature":       "static/logo-dark-nature.png",
    "soul_vinyl_dark":   "static/logo-soul-vinyl-dark.png",
    "soul_vinyl_light":  "static/logo-soul-vinyl-light.png",
    "expressive_nature": "static/logo-nature.png",
    "kawaii":            "static/logo-kawaii.png",
}

# ──────────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def _effective_skin(player_id: int) -> str:
    """The skin name actually applied for a player (re-gating Pro skins), mirroring
    skin_utils.skin_links so the og:image matches the page."""
    skin = "default"
    try:
        from skin_utils import _SAFE_SKIN_RE, _get_pro_skins, is_pro
        from auth import get_db, Player
        db = get_db()
        try:
            p = db.query(Player).filter(Player.id == player_id).first()
            if p and getattr(p, "skin", None) and _SAFE_SKIN_RE.match(p.skin):
                skin = p.skin
                if skin in _get_pro_skins() and not is_pro(p):
                    skin = "default"
        finally:
            db.close()
    except Exception:
        skin = "default"
    if skin != "default" and not os.path.exists(f"static/skins/{skin}.css"):
        skin = "default"
    return skin


def _player_basics(player_id: int) -> Optional[dict]:
    """name + level/trophies + headline stats for a player, or None if no such player."""
    from auth import get_db, Player
    db = get_db()
    try:
        p = db.query(Player).filter(Player.id == player_id).first()
        if not p:
            return None
        name = p.business_name
        is_npc = bool(getattr(p, "is_npc", False))
    finally:
        db.close()

    info = {"id": player_id, "name": name, "is_npc": is_npc,
            "level": None, "trophies": None,
            "net_worth": None, "rank": None}
    try:
        from events import get_player_level
        lvl = get_player_level(player_id)
        info["level"] = lvl.get("level")
        info["trophies"] = lvl.get("trophies")
    except Exception:
        pass
    try:
        from stats_ux import PlayerStats, get_db as get_stats_db
        sdb = get_stats_db()
        try:
            ps = sdb.query(PlayerStats).filter(PlayerStats.player_id == player_id).first()
        finally:
            sdb.close()
        if ps:
            info["net_worth"] = ps.total_net_worth
            info["rank"] = ps.wealth_rank
    except Exception:
        pass
    return info


def _resolve_viewer(session_token: Optional[str]) -> Optional[int]:
    try:
        import auth
        db = auth.get_db()
        try:
            p = auth.get_player_from_session(db, session_token)
            return p.id if p else None
        finally:
            db.close()
    except Exception:
        return None


def _caption(info: dict, abs_url: str, fmt_usd_fn, disp) -> str:
    bits = [f"📈 {info['name']} on Wadsworth"]
    if info.get("net_worth") is not None:
        try:
            bits.append(f"💰 Net worth {_compact_money(info['net_worth'], disp)}")
        except Exception:
            pass
    if info.get("rank"):
        bits.append(f"🏆 Rank #{info['rank']}")
    line = " · ".join(bits)
    return f"{line}\n\nBuild your own economic empire 👉 {abs_url}\n#Wadsworth"


def _intent_url(caption: str) -> str:
    return "https://bsky.app/intent/compose?text=" + quote(caption, safe="")


_MONEY_UNITS = ["", "K", "M", "B", "T", "Qa", "Qi", "Sx", "Sp", "Oc", "No", "Dc"]


def _compact_money(usd_amount, disp) -> str:
    """Abbreviate a (possibly astronomical) amount for the fixed-width card image,
    in the player's display currency. e.g. $1.73Qi, ¥4.2B JPY."""
    sym = (disp or {}).get("symbol", "$")
    code = (disp or {}).get("code", "USD")
    upu = (disp or {}).get("usd_per_unit", 1.0) or 1.0
    val = (usd_amount or 0.0) / upu
    sign = "-" if val < 0 else ""
    val = abs(val)
    i = 0
    while val >= 1000 and i < len(_MONEY_UNITS) - 1:
        val /= 1000.0
        i += 1
    num = (f"{val:,.0f}" if i == 0 else f"{val:.2f}".rstrip("0").rstrip("."))
    s = f"{sign}{sym}{num}{_MONEY_UNITS[i]}"
    return s if code == "USD" else f"{s} {code}"


# ──────────────────────────────────────────────────────────────────────────────
# SNAPSHOT PAGE
# ──────────────────────────────────────────────────────────────────────────────

_PAGE_CSS = """
    *{box-sizing:border-box;}
    body{margin:0;background:var(--bg-page,#020617);color:var(--text-primary,#e5e7eb);
         font-family:var(--font-body,system-ui,-apple-system,Segoe UI,Roboto,sans-serif);}
    a{color:var(--accent,#38bdf8);}
    .snap-wrap{max-width:760px;margin:0 auto;padding:0 14px 60px;}
    .snap-hero{margin:0 -14px 0;height:140px;
        background:linear-gradient(120deg,var(--accent,#38bdf8),var(--accent-2,#6366f1));
        display:flex;align-items:center;justify-content:center;position:relative;}
    .snap-hero img{height:54px;opacity:.96;filter:drop-shadow(0 2px 6px rgba(0,0,0,.35));}
    .snap-hero .snap-tag{position:absolute;bottom:8px;right:14px;font-size:.72rem;
        letter-spacing:.12em;text-transform:uppercase;color:rgba(255,255,255,.85);font-weight:700;}
    .snap-card{background:var(--bg-card,#0f172a);border:1px solid var(--border,#1e293b);
        border-radius:var(--radius-lg,14px);padding:20px;margin-top:-26px;
        box-shadow:var(--shadow-md,0 8px 30px rgba(0,0,0,.4));}
    .snap-bar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;
        margin-top:14px;padding:12px;border-radius:10px;
        background:var(--bg-card,#0f172a);border:1px solid var(--border,#1e293b);}
    .snap-btn{display:inline-flex;align-items:center;gap:6px;cursor:pointer;
        border:1px solid var(--accent,#38bdf8);background:var(--accent,#38bdf8);
        color:#04121e;font-weight:700;font-size:.85rem;padding:7px 14px;border-radius:8px;
        text-decoration:none;}
    .snap-btn.alt{background:transparent;color:var(--accent,#38bdf8);}
    .snap-foot{text-align:center;color:var(--text-muted,#64748b);font-size:.72rem;margin-top:18px;}
    .snap-note{color:var(--text-muted,#64748b);font-size:.78rem;margin:6px 0 0;}
"""


def render_snapshot(player_id: int, info: dict, *, owner: bool,
                    abs_url: str, disp, fmt_usd_fn) -> str:
    """Build the social-profile body: hero banner, owner share bar, then the skinified
    contact card."""
    from contacts import build_contact_card_html
    skin = _effective_skin(player_id)
    logo = "/" + _SKIN_LOGOS.get(skin, "static/logo.png")

    # build_contact_card_html already skinifies its output (contacts.skinify_card), so it
    # themes to this player's skin. No viewer on a public snapshot → shows total contacts.
    card = build_contact_card_html(player_id, disp, fmt_usd_fn)

    share_bar = ""
    if owner:
        caption = _caption(info, abs_url, fmt_usd_fn, disp)
        intent = html.escape(_intent_url(caption), quote=True)
        url_js = abs_url.replace("'", "\\'")
        enabled = info.get("public_profile")
        toggle = (
            '<form action="/api/settings/profile/toggle" method="post" style="margin:0;">'
            + ('<input type="hidden" name="public_profile" value="1">'
               if not enabled else "")
            + f'<button class="snap-btn alt" type="submit">'
              f'{"🔓 Enable public profile" if not enabled else "🔒 Disable"}</button>'
            '</form>'
        )
        state = ("✅ Your snapshot is <strong>public</strong> — anyone with the link can see it."
                 if enabled else
                 "🙈 Your snapshot is <strong>private</strong>. Enable it to share, "
                 "or preview it here first.")
        share_bar = (
            '<div class="snap-bar">'
            f'<a class="snap-btn" href="{intent}" target="_blank" rel="noopener noreferrer">🦋 Post Snapshot</a>'
            f"<button class=\"snap-btn alt\" type=\"button\" onclick=\"navigator.clipboard&&navigator.clipboard.writeText('{url_js}');this.textContent='✓ Copied';\">🔗 Copy Snapshot Link</button>"
            f'{toggle}'
            f'</div><p class="snap-note">{state}</p>'
        )

    return (
        '<div class="snap-hero">'
        f'<img src="{html.escape(logo, quote=True)}" alt="Wadsworth">'
        '<span class="snap-tag">Player Snapshot</span>'
        '</div>'
        '<div class="snap-wrap">'
        f'{share_bar}'
        f'<div class="snap-card">{card}</div>'
        '<p class="snap-foot">Powered by '
        '<a href="/login">Wadsworth</a> — a living, player-driven economy.</p>'
        '</div>'
    )


def _public_shell(player_id: int, title: str, body: str, *, info: dict, abs_url: str) -> str:
    """Minimal skinned shell for a public page (no logout/balance/ticker)."""
    from skin_utils import skin_links as _skin_links
    try:
        from ux import _nav_loader_html
        loader = _nav_loader_html()
    except Exception:
        loader = ""

    name = html.escape(info["name"], quote=True)
    desc_bits = []
    if info.get("net_worth") is not None:
        try:
            desc_bits.append(f"Net worth {_compact_money(info['net_worth'], None)}")
        except Exception:
            pass
    if info.get("rank"):
        desc_bits.append(f"Rank #{info['rank']}")
    if info.get("level") is not None:
        desc_bits.append(f"Level {info['level']}")
    og_desc = html.escape((" · ".join(desc_bits) or
                           "An economic-tycoon empire on Wadsworth."), quote=True)
    card_v = info.get("card_v", "")
    og_img = f"{SITE_BASE}/api/player/{player_id}/card.png"
    if card_v:
        og_img += f"?v={card_v}"

    return (
        "<!DOCTYPE html><html><head>"
        f"<title>{name} · Wadsworth</title>"
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">'
        '<meta name="theme-color" content="#020617">'
        '<link rel="apple-touch-icon" href="/static/icons/apple-touch-icon.png">'
        '<meta property="og:type" content="profile">'
        f'<meta property="og:title" content="{name} on Wadsworth">'
        f'<meta property="og:description" content="{og_desc}">'
        f'<meta property="og:image" content="{html.escape(og_img, quote=True)}">'
        f'<meta property="og:url" content="{html.escape(abs_url, quote=True)}">'
        '<meta name="twitter:card" content="summary_large_image">'
        f"{_skin_links(player_id)}"
        f"<style>{_PAGE_CSS}</style>"
        "</head><body>"
        f"{body}"
        f"{loader}"
        "</body></html>"
    )


@router.get("/player/{player_id:int}", response_class=HTMLResponse)
def public_player_profile(player_id: int, session_token: Optional[str] = Cookie(None)):
    from reserve_banks import get_player_display_currency, fmt_usd
    import bluesky

    info = _player_basics(player_id)
    if not info:
        return HTMLResponse(_simple_page("Player not found",
                            "No such player."), status_code=404)

    viewer = _resolve_viewer(session_token)
    owner = (viewer == player_id)
    linked = bluesky.get_link(player_id) is not None
    public = bluesky.is_public_profile(player_id)
    info["public_profile"] = public

    # Visible only when linked + opted-in — unless the owner is previewing their own.
    if not (linked and public) and not owner:
        return HTMLResponse(_simple_page(
            "Profile not available",
            "This player hasn't published a public snapshot."), status_code=404)
    if not linked and owner:
        return HTMLResponse(_simple_page(
            "Link Bluesky first",
            'Link a Bluesky account in <a href="/settings?tab=account">Settings</a> '
            "to publish a shareable snapshot."), status_code=200)

    try:
        disp = get_player_display_currency(player_id)
    except Exception:
        disp = {"code": "USD", "symbol": "$", "usd_per_unit": 1.0, "flag": "🇺🇸"}
    abs_url = f"{SITE_BASE}/player/{player_id}"
    info["card_v"] = _card_hash(player_id, info)
    body = render_snapshot(player_id, info, owner=owner, abs_url=abs_url,
                           disp=disp, fmt_usd_fn=fmt_usd)
    return HTMLResponse(_public_shell(player_id, info["name"], body,
                                      info=info, abs_url=abs_url))


@router.get("/me/snapshot")
def my_snapshot(session_token: Optional[str] = Cookie(None)):
    """Stable entry point (sitemap-friendly) → the viewer's own snapshot page."""
    viewer = _resolve_viewer(session_token)
    if not viewer:
        return RedirectResponse(url="/login", status_code=303)
    return RedirectResponse(url=f"/player/{viewer}", status_code=303)


def _simple_page(title: str, msg: str) -> str:
    from skin_utils import skin_links as _skin_links
    return (
        "<!DOCTYPE html><html><head>"
        f"<title>{html.escape(title)} · Wadsworth</title>"
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"{_skin_links(None)}"
        f"<style>{_PAGE_CSS}</style></head><body>"
        '<div class="snap-wrap" style="padding-top:60px;text-align:center;">'
        f'<h1 style="color:var(--accent,#38bdf8);">{html.escape(title)}</h1>'
        f'<p style="color:var(--text-secondary,#94a3b8);">{msg}</p>'
        '<p><a href="/login">← Back to Wadsworth</a></p>'
        "</div></body></html>"
    )


# ──────────────────────────────────────────────────────────────────────────────
# SKIN-THEMED OG CARD IMAGE  (Pillow; disk-cached, one file per player)
# ──────────────────────────────────────────────────────────────────────────────

def _card_hash(player_id: int, info: dict) -> str:
    skin = _effective_skin(player_id)
    avatar = ""
    try:
        import bluesky
        avatar = bluesky.public_avatar(player_id) or ""
    except Exception:
        pass
    key = f"{skin}|{info.get('name')}|{info.get('level')}|{info.get('trophies')}|" \
          f"{info.get('net_worth')}|{info.get('rank')}|{avatar}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]


def _parse_skin_colors(skin: str) -> dict:
    """Extract :root hex color vars from a skin CSS file."""
    colors = {}
    try:
        with open(f"static/skins/{skin}.css", encoding="utf-8") as f:
            css = f.read(20000)
        for name, val in re.findall(r"--([\w-]+):\s*(#[0-9a-fA-F]{3,8})", css):
            colors.setdefault(name, val)
    except Exception:
        pass
    return colors


def _hx(colors: dict, key: str, default: str) -> tuple:
    """Resolve a color var to an (r,g,b) tuple."""
    v = colors.get(key, default)
    v = v.lstrip("#")
    if len(v) == 3:
        v = "".join(c * 2 for c in v)
    try:
        return (int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16))
    except Exception:
        d = default.lstrip("#")
        return (int(d[0:2], 16), int(d[2:4], 16), int(d[4:6], 16))


def _font(bold: bool, size: int):
    from PIL import ImageFont
    paths = (["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"] if bold
             else ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"])
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _generate_card_png(player_id: int, info: dict) -> Optional[bytes]:
    try:
        from PIL import Image, ImageDraw
    except Exception:
        return None
    skin = _effective_skin(player_id)
    colors = _parse_skin_colors(skin)
    bg = _hx(colors, "bg-page", "#020617")
    panel = _hx(colors, "bg-card", "#0f172a")
    accent = _hx(colors, "accent", "#38bdf8")
    text_p = _hx(colors, "text-primary", "#e5e7eb")
    text_s = _hx(colors, "text-secondary", "#94a3b8")
    gold = _hx(colors, "color-gold", "#d4af37")
    success = _hx(colors, "color-success", "#22c55e")

    W, H = 1200, 630
    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)
    m = 48
    d.rounded_rectangle([m, m, W - m, H - m], radius=28, fill=panel)
    d.rounded_rectangle([m, m, W - m, m + 12], radius=6, fill=accent)  # accent strip

    # Logo (skin-specific), top-right inside the panel.
    try:
        logo_path = _SKIN_LOGOS.get(skin, "static/logo.png")
        logo = Image.open(logo_path).convert("RGBA")
        lh = 70
        lw = int(logo.width * lh / logo.height)
        logo = logo.resize((lw, lh), Image.LANCZOS)
        img.paste(logo, (W - m - lw - 36, m + 40), logo)
    except Exception:
        pass

    # Avatar (left) — circular if a public avatar exists, else a letter disc.
    ax, ay, asz = m + 56, m + 150, 200
    avatar_url = None
    try:
        import bluesky
        avatar_url = bluesky.public_avatar(player_id)
    except Exception:
        pass
    pasted = False
    if avatar_url:
        try:
            import requests
            r = requests.get(avatar_url, timeout=6)
            if r.status_code == 200:
                av = Image.open(io.BytesIO(r.content)).convert("RGB")
                s = min(av.size)
                av = av.crop(((av.width - s) // 2, (av.height - s) // 2,
                             (av.width + s) // 2, (av.height + s) // 2)).resize((asz, asz), Image.LANCZOS)
                mask = Image.new("L", (asz, asz), 0)
                ImageDraw.Draw(mask).ellipse([0, 0, asz, asz], fill=255)
                img.paste(av, (ax, ay), mask)
                pasted = True
        except Exception:
            pasted = False
    if not pasted:
        d.ellipse([ax, ay, ax + asz, ay + asz], fill=accent)
        letter = (info["name"][:1] or "?").upper()
        lf = _font(True, 120)
        bb = d.textbbox((0, 0), letter, font=lf)
        d.text((ax + (asz - (bb[2] - bb[0])) / 2 - bb[0],
                ay + (asz - (bb[3] - bb[1])) / 2 - bb[1]),
               letter, font=lf, fill=bg)

    # Text column (right of avatar).
    tx = ax + asz + 50
    name = info["name"]
    if len(name) > 22:
        name = name[:21] + "…"
    d.text((tx, m + 140), name, font=_font(True, 64), fill=text_p)

    handle = ""
    try:
        import bluesky
        handle = bluesky.public_handle(player_id) or ""
    except Exception:
        pass
    y = m + 222
    if handle:
        d.text((tx, y), f"@{handle}", font=_font(False, 34), fill=accent)
        y += 52

    lvl = info.get("level")
    trp = info.get("trophies")
    if lvl is not None:
        sub = f"Level {lvl}" + (f"  ·  {trp:,} trophies" if trp is not None else "")
        d.text((tx, y), sub, font=_font(False, 34), fill=text_s)
        y += 58

    try:
        from reserve_banks import get_player_display_currency
        disp = get_player_display_currency(player_id)
    except Exception:
        disp = None
    if info.get("net_worth") is not None:
        d.text((tx, y), f"Net Worth  {_compact_money(info['net_worth'], disp)}",
               font=_font(True, 46), fill=success)
        y += 64
    if info.get("rank"):
        d.text((tx, y), f"Wealth Rank  #{info['rank']}", font=_font(True, 40), fill=gold)

    d.text((m + 56, H - m - 52), f"{SITE_BASE.replace('https://','')}/player/{player_id}",
           font=_font(False, 26), fill=text_s)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


@router.get("/api/player/{player_id:int}/card.png")
def player_card_png(player_id: int):
    import bluesky
    info = _player_basics(player_id)
    fallback = FileResponse("static/icons/apple-touch-icon.png", media_type="image/png")
    if not info:
        return fallback
    # Only render for visible profiles (or fall back to the app icon).
    if not (bluesky.get_link(player_id) and bluesky.is_public_profile(player_id)):
        return fallback

    os.makedirs(_CARD_CACHE_DIR, exist_ok=True)
    h = _card_hash(player_id, info)
    path = f"{_CARD_CACHE_DIR}/{player_id}-{h}.png"
    if not os.path.exists(path):
        data = _generate_card_png(player_id, info)
        if not data:
            return fallback
        # Keep exactly one cached image per player (bounded; no growth per post/view).
        for stale in glob.glob(f"{_CARD_CACHE_DIR}/{player_id}-*.png"):
            try:
                os.remove(stale)
            except Exception:
                pass
        with open(path, "wb") as f:
            f.write(data)
    return FileResponse(path, media_type="image/png",
                        headers={"Cache-Control": "public, max-age=300"})


# ──────────────────────────────────────────────────────────────────────────────
# SETTINGS TOGGLE
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/api/settings/profile/toggle")
def toggle_public_profile(
    session_token: Optional[str] = Cookie(None),
    public_profile: Optional[str] = Form(None),
):
    import auth, bluesky
    db = auth.get_db()
    try:
        player = auth.get_player_from_session(db, session_token)
    finally:
        db.close()
    if not player:
        return RedirectResponse(url="/login", status_code=303)
    # Only meaningful when a Bluesky account is linked.
    if bluesky.get_link(player.id):
        bluesky.set_public_profile(player.id, public_profile is not None)
    return RedirectResponse(url="/settings?tab=account", status_code=303)
