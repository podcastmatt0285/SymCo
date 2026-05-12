"""
Admin push + in-game notifications for game-wide events.
Always delivered to all ADMIN_PLAYER_IDS; bypasses every player preference
check, executive gate, and payment requirement.
"""
import time

# In-process rate cache: event_key -> last_sent_unix_timestamp
_rate_cache: dict = {}
_ONLINE_COOLDOWN = 300   # 5 min — guards online/offline spam per player
_P2P_COOLDOWN    = 3600  # 1 hr  — guards P2P-entry spam per player


def _rate_ok(key: str, cooldown_secs: int) -> bool:
    now = time.time()
    if now - _rate_cache.get(key, 0.0) >= cooldown_secs:
        _rate_cache[key] = now
        return True
    return False


def _push_admins(title: str, body: str, url: str = "/admin", tag: str = "admin-watch") -> None:
    """Fire push + in-game banner to every admin, no preference checks."""
    try:
        from admins import ADMIN_PLAYER_IDS
        from push_ux import send_push_notification
        for aid in ADMIN_PLAYER_IDS:
            send_push_notification(
                aid, title, body, url,
                notif_type="admin_watch",
                tag=tag,
            )
    except Exception as exc:
        import traceback
        print(f"[AdminNotif] error: {exc}")
        traceback.print_exc()


def _player_name(player_id: int) -> str:
    try:
        from auth import get_db, Player
        db = get_db()
        try:
            p = db.query(Player).filter(Player.id == player_id).first()
            return p.business_name if p else f"#{player_id}"
        finally:
            db.close()
    except Exception:
        return f"#{player_id}"


# ── Event hooks ───────────────────────────────────────────────────────────────

def notify_new_player(business_name: str, player_id: int) -> None:
    _push_admins(
        "👤 New Player",
        f"{business_name} (#{player_id}) just registered.",
        f"/admin/player/{player_id}",
        tag=f"new-player-{player_id}",
    )


def notify_tutorial_complete(player_id: int, tutorial_num: int) -> None:
    name = _player_name(player_id)
    _push_admins(
        f"🎓 Tutorial {tutorial_num} Complete",
        f"{name} finished Tutorial {tutorial_num}.",
        f"/admin/player/{player_id}",
        tag=f"tut{tutorial_num}-done-{player_id}",
    )


def notify_bankruptcy(player_id: int) -> None:
    name = _player_name(player_id)
    _push_admins(
        "💸 Bankruptcy Declared",
        f"{name} declared bankruptcy and restarted.",
        f"/admin/player/{player_id}",
        tag=f"bankrupt-{player_id}",
    )


def notify_moderation(player_id: int, action: str, reason: str = "", duration_min: int = 0) -> None:
    name = _player_name(player_id)
    detail = f" ({duration_min}m)" if duration_min else ""
    if reason:
        detail += f": {reason}"
    labels = {"ban": "🚫 Banned", "timeout": "⏱ Timed Out", "kick": "👢 Kicked", "mute": "🔇 Muted"}
    label = labels.get(action, action.title())
    _push_admins(
        f"{label}: {name}",
        f"{name} was {action}d{detail}.",
        f"/admin/player/{player_id}",
        tag=f"mod-{action}-{player_id}",
    )


def notify_city_created(city_name: str, city_id: int, founder_id: int) -> None:
    founder = _player_name(founder_id)
    _push_admins(
        "🏙️ City Founded",
        f"{founder} founded \"{city_name}\" (City #{city_id}).",
        "/admin/cities",
        tag=f"city-created-{city_id}",
    )


def notify_county_created(county_name: str, county_id: int, founding_city_id: int) -> None:
    _push_admins(
        "🗺️ County Formed",
        f"New county \"{county_name}\" (#{county_id}) formed by City #{founding_city_id}.",
        "/admin/cities",
        tag=f"county-created-{county_id}",
    )


def notify_city_joined_county(city_id: int, county_id: int,
                               city_name: str = "", county_name: str = "") -> None:
    c  = city_name   or f"City #{city_id}"
    co = county_name or f"County #{county_id}"
    _push_admins(
        "🤝 City Joined County",
        f"{c} joined {co}.",
        "/admin/cities",
        tag=f"city-join-{city_id}-{county_id}",
    )


def notify_city_left_county(city_id: int, county_id: int,
                              city_name: str = "", county_name: str = "") -> None:
    c  = city_name   or f"City #{city_id}"
    co = county_name or f"County #{county_id}"
    _push_admins(
        "↩️ City Left County",
        f"{c} was removed from {co}.",
        "/admin/cities",
        tag=f"city-leave-{city_id}",
    )


def notify_player_online(player_id: int, player_name: str) -> None:
    if not _rate_ok(f"online-{player_id}", _ONLINE_COOLDOWN):
        return
    _push_admins(
        "🟢 Player Online",
        f"{player_name} connected.",
        f"/admin/player/{player_id}",
        tag=f"online-{player_id}",
    )


def notify_player_offline(player_id: int, player_name: str) -> None:
    if not _rate_ok(f"offline-{player_id}", _ONLINE_COOLDOWN):
        return
    _push_admins(
        "⚫ Player Offline",
        f"{player_name} disconnected.",
        f"/admin/player/{player_id}",
        tag=f"offline-{player_id}",
    )


def notify_p2p_entered(player_id: int) -> None:
    if not _rate_ok(f"p2p-{player_id}", _P2P_COOLDOWN):
        return
    name = _player_name(player_id)
    _push_admins(
        "📋 P2P Dashboard",
        f"{name} entered the P2P marketplace.",
        f"/admin/player/{player_id}",
        tag=f"p2p-entry-{player_id}",
    )
