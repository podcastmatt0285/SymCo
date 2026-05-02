"""
admins.py - Admin Command Center Backend

Provides:
- Admin player ID registry
- Player ban / kick / timeout system
- Player data lookup and editing
- Updates channel posting
- Admin action logging
"""

from datetime import datetime, timedelta
from typing import Optional, List

from sqlalchemy import Column, String, Float, DateTime, Integer, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# ==========================
# DATABASE SETUP
# ==========================

from database import engine, SessionLocal
Base = declarative_base()


# ==========================
# CONSTANTS
# ==========================

# Player IDs with admin access (same set used by chat.py)
ADMIN_PLAYER_IDS = {1}


# ==========================
# MODELS
# ==========================

class PlayerBan(Base):
    """Tracks bans, timeouts, and kicks issued by admins."""
    __tablename__ = "player_bans"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    player_id = Column(Integer, index=True, nullable=False)
    admin_id = Column(Integer, nullable=False)
    ban_type = Column(String, nullable=False)  # "ban", "timeout", "kick"
    reason = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)  # None = permanent (for bans)
    revoked = Column(Boolean, default=False)
    revoked_at = Column(DateTime, nullable=True)
    revoked_by = Column(Integer, nullable=True)


class AdminLog(Base):
    """Audit log of all admin actions."""
    __tablename__ = "admin_logs"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    admin_id = Column(Integer, nullable=False)
    action = Column(String, nullable=False)  # e.g. "ban", "kick", "edit_balance", "post_update"
    target_player_id = Column(Integer, nullable=True)
    details = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)


class Moderator(Base):
    """
    Partial-admin players (moderators).
    Moderators can view all players and kick/timeout, but cannot ban,
    edit balances/inventory, or access financial admin tools.
    """
    __tablename__ = "moderators"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    player_id = Column(Integer, unique=True, index=True, nullable=False)
    granted_by = Column(Integer, nullable=False)  # Admin who granted moderator status
    note = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)


class ChatMute(Base):
    """Chat-scoped mute: silences a player in all chat rooms without banning their account."""
    __tablename__ = "chat_mutes"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    player_id = Column(Integer, index=True, nullable=False)
    muted_by = Column(Integer, nullable=False)
    reason = Column(Text, default="")
    expires_at = Column(DateTime, nullable=True)  # None = permanent chat mute
    created_at = Column(DateTime, default=datetime.utcnow)
    lifted = Column(Boolean, default=False)
    lifted_at = Column(DateTime, nullable=True)
    lifted_by = Column(Integer, nullable=True)


class ModAction(Base):
    """Audit log of moderator actions (separate from full admin AdminLog)."""
    __tablename__ = "mod_actions"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    mod_id = Column(Integer, nullable=False)
    action = Column(String, nullable=False)  # "mute", "lift_mute", "warn", "delete_message", "kick"
    target_player_id = Column(Integer, nullable=True)
    room_id = Column(String, nullable=True)
    details = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)


# In-memory cache — refreshed on each relevant operation
MODERATOR_PLAYER_IDS: set = set()


def _refresh_moderator_cache():
    """Reload the moderator ID set from DB into the in-memory cache."""
    global MODERATOR_PLAYER_IDS
    db = get_db()
    try:
        mods = db.query(Moderator).all()
        MODERATOR_PLAYER_IDS = {m.player_id for m in mods}
    except Exception:
        MODERATOR_PLAYER_IDS = set()
    finally:
        db.close()


def get_db():
    return SessionLocal()


def initialize():
    Base.metadata.create_all(bind=engine)
    _refresh_moderator_cache()
    print("[Admins] Module initialized")


# ==========================
# AUTH HELPERS
# ==========================

def is_admin(player_id: int) -> bool:
    return player_id in ADMIN_PLAYER_IDS


def is_moderator(player_id: int) -> bool:
    """Returns True for both full admins AND partial moderators."""
    return player_id in ADMIN_PLAYER_IDS or player_id in MODERATOR_PLAYER_IDS


def require_admin(session_token: str):
    """Return player if FULL admin, None otherwise."""
    try:
        import auth
        db = auth.get_db()
        player = auth.get_player_from_session(db, session_token)
        db.close()
        if player and is_admin(player.id):
            return player
        return None
    except Exception:
        return None


def require_moderator(session_token: str):
    """Return (player, is_full_admin) if player is admin or moderator, else (None, False)."""
    try:
        import auth
        db = auth.get_db()
        player = auth.get_player_from_session(db, session_token)
        db.close()
        if player and is_admin(player.id):
            return player, True
        if player and is_moderator(player.id):
            return player, False
        return None, False
    except Exception:
        return None, False


# ==========================
# ADMIN LOGGING
# ==========================

def log_action(admin_id: int, action: str, target_player_id: int = None, details: str = ""):
    db = get_db()
    entry = AdminLog(
        admin_id=admin_id,
        action=action,
        target_player_id=target_player_id,
        details=details,
    )
    db.add(entry)
    db.commit()
    db.close()


def get_player_admin_logs(player_id: int, limit: int = 30) -> list:
    """Get admin action history targeting a specific player."""
    db = get_db()
    logs = (
        db.query(AdminLog)
        .filter(AdminLog.target_player_id == player_id)
        .order_by(AdminLog.created_at.desc())
        .limit(limit)
        .all()
    )
    result = [
        {
            "id": log.id,
            "admin_id": log.admin_id,
            "action": log.action,
            "details": log.details,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]
    db.close()
    return result


def get_economy_stats() -> dict:
    """Aggregate real-time economy metrics for the admin dashboard health panel."""
    stats = {}

    # Active players by last_login window
    try:
        players = get_all_players()
        now = datetime.utcnow()
        cutoff_24h = now - timedelta(hours=24)
        cutoff_7d  = now - timedelta(days=7)
        active_24h = active_7d = 0
        for p in players:
            ll = p.get("last_login")
            if ll:
                try:
                    dt = datetime.fromisoformat(ll.replace("Z", "")).replace(tzinfo=None)
                    if dt >= cutoff_24h:
                        active_24h += 1
                    if dt >= cutoff_7d:
                        active_7d += 1
                except Exception:
                    pass
        stats["active_24h"] = active_24h
        stats["active_7d"]  = active_7d
    except Exception:
        stats["active_24h"] = stats["active_7d"] = 0

    # Market volume and order count
    try:
        from market import get_market_stats
        ms = get_market_stats()
        stats["market_volume_24h"] = ms.get("volume_24h", 0)
        stats["active_orders"]     = ms.get("active_orders", 0)
    except Exception:
        stats["market_volume_24h"] = stats["active_orders"] = 0

    # Active businesses
    try:
        from business import Business, get_db as biz_get_db
        db = biz_get_db()
        stats["active_businesses"] = db.query(Business).filter(Business.is_active == True).count()
        db.close()
    except Exception:
        stats["active_businesses"] = 0

    # Total items in circulation across all inventories
    try:
        import inventory
        from sqlalchemy import func
        db = inventory.get_db()
        result = db.query(func.sum(inventory.InventoryItem.quantity)).scalar()
        stats["total_items"] = int(result or 0)
        db.close()
    except Exception:
        stats["total_items"] = 0

    return stats


def admin_ban_all_linked(admin_id: int, player_id: int, reason: str = "") -> dict:
    """Ban every IP-linked account of a player in one sweep."""
    try:
        accounts = get_related_accounts(player_id)
        banned, skipped = [], []
        for a in accounts:
            if a["is_banned"]:
                skipped.append(a["player_id"])
                continue
            r = ban_player(admin_id, a["player_id"],
                           reason or f"Alt account — linked to #{player_id} via shared IP")
            if r.get("ok"):
                banned.append(a["player_id"])
        log_action(admin_id, "ban_all_linked", player_id,
                   f"Banned {len(banned)} linked account(s) {banned}; {len(skipped)} already banned")
        return {"ok": True, "banned": banned, "skipped": skipped}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_player_push_subscriptions(player_id: int) -> list:
    """Get all push notification subscriptions registered for a player."""
    try:
        from auth import PushSubscription, get_db as auth_get_db
        db = auth_get_db()
        subs = (db.query(PushSubscription)
                  .filter(PushSubscription.player_id == player_id)
                  .order_by(PushSubscription.created_at.desc())
                  .all())
        result = [
            {
                "id": s.id,
                "endpoint_tail": ("…" + s.endpoint[-45:]) if s.endpoint else "?",
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in subs
        ]
        db.close()
        return result
    except Exception:
        return []


def get_admin_logs(limit: int = 100, action_filter: str = "", admin_id_filter: int = 0, days: int = 0) -> list:
    db = get_db()
    q = db.query(AdminLog).order_by(AdminLog.created_at.desc())
    if action_filter:
        q = q.filter(AdminLog.action.ilike(f"%{action_filter}%"))
    if admin_id_filter:
        q = q.filter(AdminLog.admin_id == admin_id_filter)
    if days > 0:
        cutoff = datetime.utcnow() - timedelta(days=days)
        q = q.filter(AdminLog.created_at >= cutoff)
    logs = q.limit(limit).all()
    result = []
    for log in logs:
        result.append({
            "id": log.id,
            "admin_id": log.admin_id,
            "action": log.action,
            "target_player_id": log.target_player_id,
            "details": log.details,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        })
    db.close()
    return result


# ==========================
# BAN / TIMEOUT / KICK
# ==========================

def ban_player(admin_id: int, player_id: int, reason: str = "") -> dict:
    """Permanently ban a player."""
    db = get_db()
    ban = PlayerBan(
        player_id=player_id,
        admin_id=admin_id,
        ban_type="ban",
        reason=reason,
        expires_at=None,
    )
    db.add(ban)
    db.commit()
    db.refresh(ban)
    ban_id = ban.id
    db.close()

    log_action(admin_id, "ban", player_id, reason)
    print(f"[Admins] Player {player_id} banned by admin {admin_id}: {reason}")
    return {"ok": True, "ban_id": ban_id}


def timeout_player(admin_id: int, player_id: int, minutes: int, reason: str = "") -> dict:
    """Temporarily timeout a player for N minutes."""
    if minutes < 1:
        return {"ok": False, "error": "Duration must be at least 1 minute"}
    db = get_db()
    expires = datetime.utcnow() + timedelta(minutes=minutes)
    ban = PlayerBan(
        player_id=player_id,
        admin_id=admin_id,
        ban_type="timeout",
        reason=reason,
        expires_at=expires,
    )
    db.add(ban)
    db.commit()
    db.refresh(ban)
    ban_id = ban.id
    db.close()

    log_action(admin_id, "timeout", player_id, f"{minutes}m - {reason}")
    print(f"[Admins] Player {player_id} timed out {minutes}m by admin {admin_id}: {reason}")
    return {"ok": True, "ban_id": ban_id, "expires_at": expires.isoformat()}


def kick_player(admin_id: int, player_id: int, reason: str = "") -> dict:
    """Record a kick (instant disconnect, no login block)."""
    db = get_db()
    ban = PlayerBan(
        player_id=player_id,
        admin_id=admin_id,
        ban_type="kick",
        reason=reason,
        expires_at=datetime.utcnow(),  # already expired = just a record
    )
    db.add(ban)
    db.commit()
    db.close()

    log_action(admin_id, "kick", player_id, reason)
    print(f"[Admins] Player {player_id} kicked by admin {admin_id}: {reason}")
    return {"ok": True}


def revoke_ban(admin_id: int, ban_id: int) -> dict:
    """Revoke (unban) an active ban or timeout."""
    db = get_db()
    ban = db.query(PlayerBan).filter(PlayerBan.id == ban_id).first()
    if not ban:
        db.close()
        return {"ok": False, "error": "Ban not found"}
    if ban.revoked:
        db.close()
        return {"ok": False, "error": "Already revoked"}
    ban.revoked = True
    ban.revoked_at = datetime.utcnow()
    ban.revoked_by = admin_id
    db.commit()
    db.close()

    log_action(admin_id, "revoke_ban", ban.player_id, f"Revoked ban #{ban_id}")
    print(f"[Admins] Ban #{ban_id} revoked by admin {admin_id}")
    return {"ok": True}


def get_active_ban(player_id: int) -> Optional[dict]:
    """Check if a player has an active ban or timeout. Returns the ban info or None."""
    db = get_db()
    now = datetime.utcnow()
    # Check for active permanent ban
    ban = db.query(PlayerBan).filter(
        PlayerBan.player_id == player_id,
        PlayerBan.ban_type == "ban",
        PlayerBan.revoked == False,
    ).order_by(PlayerBan.created_at.desc()).first()
    if ban:
        result = {
            "id": ban.id,
            "type": "ban",
            "reason": ban.reason,
            "created_at": ban.created_at.isoformat(),
            "admin_id": ban.admin_id,
        }
        db.close()
        return result

    # Check for active timeout
    timeout = db.query(PlayerBan).filter(
        PlayerBan.player_id == player_id,
        PlayerBan.ban_type == "timeout",
        PlayerBan.revoked == False,
        PlayerBan.expires_at > now,
    ).order_by(PlayerBan.expires_at.desc()).first()
    if timeout:
        result = {
            "id": timeout.id,
            "type": "timeout",
            "reason": timeout.reason,
            "created_at": timeout.created_at.isoformat(),
            "expires_at": timeout.expires_at.isoformat(),
            "admin_id": timeout.admin_id,
        }
        db.close()
        return result

    db.close()
    return None


def get_player_bans(player_id: int) -> list:
    """Get all ban/timeout/kick records for a player."""
    db = get_db()
    bans = db.query(PlayerBan).filter(
        PlayerBan.player_id == player_id
    ).order_by(PlayerBan.created_at.desc()).all()
    result = []
    for b in bans:
        result.append({
            "id": b.id,
            "ban_type": b.ban_type,
            "reason": b.reason,
            "created_at": b.created_at.isoformat() if b.created_at else None,
            "expires_at": b.expires_at.isoformat() if b.expires_at else None,
            "revoked": b.revoked,
            "admin_id": b.admin_id,
        })
    db.close()
    return result


# ==========================
# MULTI-ACCOUNT LINK DETECTION
# ==========================

def get_related_accounts(player_id: int) -> list:
    """
    Return all accounts that share a registration or login IP with *player_id*.

    Each entry: {player_id, business_name, shared_ip, link_type, seen_at, is_banned}
    link_type is one of: "registration", "login", or "reg→login"
    (the last meaning the OTHER account's login IP matches THIS account's reg IP).

    Uses lazy import to avoid a circular dependency with auth.py.
    """
    from auth import PlayerRegistrationIP, PlayerLoginIP, Player, get_db as auth_get_db

    adb = auth_get_db()   # auth / main DB (same engine as admins)
    try:
        # Collect all IPs ever associated with the target player.
        reg_ips   = {r.ip_address for r in adb.query(PlayerRegistrationIP)
                     .filter(PlayerRegistrationIP.player_id == player_id).all()}
        login_ips = {r.ip_address for r in adb.query(PlayerLoginIP)
                     .filter(PlayerLoginIP.player_id == player_id).all()}
        all_ips = reg_ips | login_ips

        if not all_ips:
            return []

        seen: dict = {}   # other_player_id → {shared_ip, link_type, seen_at}

        # Other accounts that registered from any of these IPs.
        for row in (adb.query(PlayerRegistrationIP)
                    .filter(PlayerRegistrationIP.ip_address.in_(all_ips),
                            PlayerRegistrationIP.player_id != player_id).all()):
            pid = row.player_id
            if pid not in seen:
                link = "registration" if row.ip_address in reg_ips else "reg→login"
                seen[pid] = {"shared_ip": row.ip_address,
                             "link_type": link,
                             "seen_at": row.registered_at}

        # Other accounts that logged in from any of these IPs.
        for row in (adb.query(PlayerLoginIP)
                    .filter(PlayerLoginIP.ip_address.in_(all_ips),
                            PlayerLoginIP.player_id != player_id).all()):
            pid = row.player_id
            if pid not in seen:
                link = "reg→login" if row.ip_address in reg_ips else "login"
                seen[pid] = {"shared_ip": row.ip_address,
                             "link_type": link,
                             "seen_at": row.logged_in_at}

        if not seen:
            return []

        # Enrich with player names.
        player_rows = (adb.query(Player)
                       .filter(Player.id.in_(list(seen.keys()))).all())
        name_map = {p.id: p.business_name for p in player_rows}

        # Enrich with ban status (query the admins DB — same engine, works fine).
        ban_db = get_db()
        try:
            banned_ids = {
                b.player_id for b in ban_db.query(PlayerBan).filter(
                    PlayerBan.player_id.in_(list(seen.keys())),
                    PlayerBan.ban_type == "ban",
                    PlayerBan.revoked == False,
                ).all()
            }
        finally:
            ban_db.close()

        return sorted(
            [
                {
                    "player_id":     pid,
                    "business_name": name_map.get(pid, f"#{pid}"),
                    "shared_ip":     info["shared_ip"],
                    "link_type":     info["link_type"],
                    "seen_at":       info["seen_at"].isoformat() if info["seen_at"] else "",
                    "is_banned":     pid in banned_ids,
                }
                for pid, info in seen.items()
            ],
            key=lambda x: x["seen_at"],
            reverse=True,
        )
    finally:
        adb.close()


# ==========================
# PLAYER DATA FUNCTIONS
# ==========================

def get_all_players() -> list:
    """Get summary info for all players."""
    import auth
    db = auth.get_db()
    players = db.query(auth.Player).order_by(auth.Player.id).all()
    result = []
    for p in players:
        active_ban = get_active_ban(p.id)
        result.append({
            "id": p.id,
            "business_name": p.business_name,
            "cash_balance": p.cash_balance,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "last_login": p.last_login.isoformat() if p.last_login else None,
            "is_admin": p.id in ADMIN_PLAYER_IDS,
            "ban_status": active_ban["type"] if active_ban else None,
        })
    db.close()
    return result


def get_player_detail(player_id: int) -> Optional[dict]:
    """Get full detail for a single player."""
    import auth
    db = auth.get_db()
    player = db.query(auth.Player).filter(auth.Player.id == player_id).first()
    if not player:
        db.close()
        return None

    result = {
        "id": player.id,
        "business_name": player.business_name,
        "cash_balance": player.cash_balance,
        "created_at": player.created_at.isoformat() if player.created_at else None,
        "last_login": player.last_login.isoformat() if player.last_login else None,
        "is_admin": player.id in ADMIN_PLAYER_IDS,
        "tutorial_step": getattr(player, "tutorial_step", 0),
    }
    db.close()

    # City membership
    try:
        from chat import get_player_city
        city = get_player_city(player_id)
        result["city"] = city["name"] if city else None
    except Exception:
        result["city"] = None

    # Ban history
    result["bans"] = get_player_bans(player_id)
    result["active_ban"] = get_active_ban(player_id)

    return result


def edit_player_balance(admin_id: int, player_id: int, new_balance: float) -> dict:
    """Set a player's cash balance."""
    import auth
    db = auth.get_db()
    player = db.query(auth.Player).filter(auth.Player.id == player_id).first()
    if not player:
        db.close()
        return {"ok": False, "error": "Player not found"}
    old_balance = player.cash_balance
    player.cash_balance = new_balance
    db.commit()
    db.close()

    log_action(admin_id, "edit_balance", player_id,
               f"${old_balance:,.2f} -> ${new_balance:,.2f}")
    return {"ok": True, "old_balance": old_balance, "new_balance": new_balance}


def admin_set_currency_balance(admin_id: int, player_id: int, currency_code: str, new_balance: float) -> dict:
    """Set a player's balance in any currency to an exact value."""
    from reserve_banks import get_player_currency_balance, set_currency_balance
    try:
        old = get_player_currency_balance(player_id, currency_code)
        set_currency_balance(player_id, currency_code, new_balance)
        log_action(admin_id, "edit_currency_balance", player_id,
                   f"{currency_code}: {old:,.4f} -> {new_balance:,.4f}")
        return {"ok": True, "currency_code": currency_code, "old_balance": old, "new_balance": new_balance}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def admin_set_etf_cash(admin_id: int, bank_id: str, new_balance: float) -> dict:
    """Set an ETF bank's cash_reserves to an exact value."""
    try:
        from banks import get_db, BankEntity
        db = get_db()
        entity = db.query(BankEntity).filter(BankEntity.bank_id == bank_id).first()
        if not entity:
            db.close()
            return {"ok": False, "error": f"Bank '{bank_id}' not found"}
        old = entity.cash_reserves
        entity.cash_reserves = new_balance
        db.commit()
        db.close()
        log_action(admin_id, "edit_etf_cash", None,
                   f"{bank_id}: ${old:,.2f} -> ${new_balance:,.2f}")
        return {"ok": True, "bank_id": bank_id, "old_balance": old, "new_balance": new_balance}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def admin_set_brokerage_cash(admin_id: int, new_balance: float) -> dict:
    """Set the Brokerage Firm's cash_reserves to an exact value."""
    try:
        from banks.brokerage_firm import get_db, FirmEntity
        db = get_db()
        firm = db.query(FirmEntity).first()
        if not firm:
            db.close()
            return {"ok": False, "error": "Brokerage Firm entity not found"}
        old = firm.cash_reserves
        firm.cash_reserves = new_balance
        db.commit()
        db.close()
        log_action(admin_id, "edit_brokerage_cash", None,
                   f"Brokerage Firm: ${old:,.2f} -> ${new_balance:,.2f}")
        return {"ok": True, "old_balance": old, "new_balance": new_balance}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ==========================
# UPDATES CHANNEL POSTING
# ==========================

def post_update(admin_id: int, content: str, tag: str = None) -> dict:
    """Post a message to the updates channel as the system.

    If `tag` is provided the message is upserted (update existing if the tag
    already exists in the updates room, otherwise insert).  This makes the
    operation idempotent so the patch-notes script can be re-run safely.
    """
    from chat import save_message, upsert_message

    if tag:
        saved = upsert_message(
            "updates", admin_id, "System", content,
            tag=tag, message_type="patch_note",
        )
    else:
        saved = save_message(
            "updates", admin_id, "System", content,
            message_type="patch_note",
        )
    if not saved:
        return {"ok": False, "error": "Failed to save message"}

    log_action(admin_id, "post_update", details=content[:200])
    return {"ok": True, "message": saved}


# ==========================
# INVENTORY MANAGEMENT
# ==========================

def get_player_inventory(player_id: int) -> list:
    """Get a player's full inventory as a list of dicts."""
    try:
        import inventory
        inv = inventory.get_player_inventory(player_id)
        items = []
        for item_type, qty in sorted(inv.items()):
            info = inventory.get_item_info(item_type)
            name = info.get("name", item_type.replace("_", " ").title()) if info else item_type.replace("_", " ").title()
            items.append({"item_type": item_type, "name": name, "quantity": qty})
        return items
    except Exception:
        return []


def admin_add_item(admin_id: int, player_id: int, item_type: str, quantity: float) -> dict:
    """Admin adds items to a player's inventory."""
    if quantity <= 0:
        return {"ok": False, "error": "Quantity must be positive"}
    try:
        import inventory
        inventory.add_item(player_id, item_type, quantity)
        log_action(admin_id, "add_item", player_id, f"+{quantity:.1f} {item_type}")
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def admin_remove_item(admin_id: int, player_id: int, item_type: str, quantity: float) -> dict:
    """Admin removes items from a player's inventory."""
    if quantity <= 0:
        return {"ok": False, "error": "Quantity must be positive"}
    try:
        import inventory
        success = inventory.remove_item(player_id, item_type, quantity)
        if not success:
            return {"ok": False, "error": "Insufficient quantity"}
        log_action(admin_id, "remove_item", player_id, f"-{quantity:.1f} {item_type}")
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def admin_set_tutorial_step(admin_id: int, player_id: int, step: int) -> dict:
    """Set a player's tutorial step directly (0=not started, 1-10=active, 11=complete)."""
    try:
        import auth
        db = auth.get_db()
        player = db.query(auth.Player).filter(auth.Player.id == player_id).first()
        if not player:
            db.close()
            return {"ok": False, "error": "Player not found"}
        player.tutorial_step = step
        db.commit()
        db.close()
        log_action(admin_id, "set_tutorial_step", player_id, f"tutorial_step → {step}")
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def admin_get_player_orders(player_id: int) -> list:
    """Return all open/partial market orders for a player."""
    try:
        from market import MarketOrder, OrderStatus, get_db as market_get_db
        db = market_get_db()
        try:
            orders = db.query(MarketOrder).filter(
                MarketOrder.player_id == player_id,
                MarketOrder.status.in_([OrderStatus.ACTIVE, OrderStatus.PARTIALLY_FILLED]),
            ).order_by(MarketOrder.created_at.desc()).all()
            return [
                {
                    "id": o.id,
                    "order_type": o.order_type,
                    "item_type": o.item_type,
                    "quantity": o.quantity,
                    "quantity_filled": o.quantity_filled,
                    "price": o.price,
                    "status": o.status,
                    "created_at": o.created_at.isoformat() if o.created_at else None,
                }
                for o in orders
            ]
        finally:
            db.close()
    except Exception:
        return []


def admin_cancel_market_order(admin_id: int, player_id: int, order_id: int) -> dict:
    """Admin force-cancels an open market order for a player."""
    try:
        from market import cancel_order
        ok = cancel_order(order_id, player_id)
        if not ok:
            return {"ok": False, "error": "Order not found or already closed"}
        log_action(admin_id, "cancel_market_order", player_id,
                   f"Cancelled market order #{order_id} for player #{player_id}")
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_all_item_types() -> list:
    """Get all known item types for the admin dropdown (regular + district items)."""
    items = set()
    try:
        import inventory
        items.update(inventory.ITEM_RECIPES.keys())
    except Exception:
        pass
    try:
        import json as _json
        with open("district_items.json") as f:
            di = _json.load(f)
        items.update(di.keys())
    except Exception:
        pass
    return sorted(items)


# ==========================
# LAND MANAGEMENT
# ==========================

def get_player_land(player_id: int) -> list:
    """Get all land plots owned by a player."""
    try:
        from land import get_player_land as _get, LandPlot
        plots = _get(player_id)
        result = []
        for p in plots:
            result.append({
                "id": p.id,
                "terrain_type": p.terrain_type,
                "proximity_features": p.proximity_features,
                "efficiency": p.efficiency,
                "size": p.size,
                "monthly_tax": p.monthly_tax,
                "occupied_by_business_id": p.occupied_by_business_id,
                "is_starter_plot": p.is_starter_plot,
                "is_government_owned": p.is_government_owned,
            })
        return result
    except Exception:
        return []


def admin_delete_land_plot(admin_id: int, plot_id: int) -> dict:
    """Admin deletes a land plot entirely."""
    try:
        from land import get_db as land_db, LandPlot
        db = land_db()
        plot = db.query(LandPlot).filter(LandPlot.id == plot_id).first()
        if not plot:
            db.close()
            return {"ok": False, "error": "Plot not found"}
        owner_id = plot.owner_id
        if plot.occupied_by_business_id:
            db.close()
            return {"ok": False, "error": "Plot is occupied by a business. Remove business first."}
        db.delete(plot)
        db.commit()
        db.close()
        log_action(admin_id, "delete_land", owner_id, f"Deleted plot #{plot_id}")
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def admin_create_land_plot(admin_id: int, owner_id: int, terrain_type: str, proximity: str = "") -> dict:
    """Admin creates a new land plot for a player."""
    try:
        from land import create_land_plot
        prox_list = [f.strip() for f in proximity.split(",") if f.strip()] if proximity else None
        plot = create_land_plot(
            owner_id=owner_id,
            terrain_type=terrain_type,
            proximity_features=prox_list,
            size=1.0,
            is_starter=False,
            is_government=(owner_id == 0),
        )
        log_action(admin_id, "create_land", owner_id, f"Created plot #{plot.id} ({terrain_type})")
        return {"ok": True, "plot_id": plot.id}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ==========================
# DISTRICT MANAGEMENT
# ==========================

def get_player_districts(player_id: int) -> list:
    """Get all districts owned by a player, enriched with config and tax state."""
    try:
        from districts import get_player_districts as _get, DISTRICT_TYPES, DISTRICT_TAX_MULTIPLIER
        districts = _get(player_id)
        result = []
        for d in districts:
            cfg = DISTRICT_TYPES.get(d.district_type, {})
            base_tax = cfg.get("base_tax", 0.0)
            result.append({
                "id": d.id,
                "district_type": d.district_type,
                "terrain_type": d.terrain_type,
                "size": d.size,
                "plots_merged": d.plots_merged,
                "monthly_tax": d.monthly_tax,
                "occupied_by_business_id": d.occupied_by_business_id,
                "last_tax_payment": d.last_tax_payment.isoformat() if d.last_tax_payment else None,
                "source_plot_ids": d.source_plot_ids or "",
                "base_tax": base_tax,
                "tax_multiplier": DISTRICT_TAX_MULTIPLIER,
            })
        return result
    except Exception:
        return []


def get_player_district_stats(player_id: int) -> dict:
    """Get PlayerDistrictStats for a player."""
    try:
        from districts import SessionLocal as DistSession, PlayerDistrictStats, BASE_MERGE_COST
        db = DistSession()
        stats = db.query(PlayerDistrictStats).filter(PlayerDistrictStats.player_id == player_id).first()
        db.close()
        if not stats:
            return {"total_merges_completed": 0, "current_merge_cost": BASE_MERGE_COST, "last_merge_date": None}
        return {
            "total_merges_completed": stats.total_merges_completed,
            "current_merge_cost": stats.current_merge_cost,
            "last_merge_date": stats.last_merge_date.isoformat() if stats.last_merge_date else None,
        }
    except Exception:
        return {}


def admin_reset_business_ticks(admin_id: int, business_id: int) -> dict:
    """Reset a business's progress_ticks to 0, restarting its production cycle."""
    try:
        from business import SessionLocal as BizSession, Business
        db = BizSession()
        biz = db.query(Business).filter(Business.id == business_id).first()
        if not biz:
            db.close()
            return {"ok": False, "error": f"Business #{business_id} not found"}
        owner_id = biz.owner_id
        biz.progress_ticks = 0
        db.commit()
        db.close()
        log_action(admin_id, "reset_business_ticks", owner_id, f"Reset progress_ticks on business #{business_id}")
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ==========================
# BUSINESS MANAGEMENT
# ==========================

def get_player_businesses(player_id: int) -> list:
    """Get all businesses owned by a player, enriched with config and runtime state."""
    try:
        from business import SessionLocal as BizSession, Business, BusinessSale, BUSINESS_TYPES
        db = BizSession()
        businesses = db.query(Business).filter(Business.owner_id == player_id).all()

        # Build a BusinessSale lookup keyed by business_id
        sale_map = {}
        try:
            sales = db.query(BusinessSale).filter(
                BusinessSale.owner_id == player_id,
                BusinessSale.ticks_remaining > 0
            ).all()
            for s in sales:
                sale_map[s.business_id] = {"ticks_remaining": s.ticks_remaining, "ticks_total": s.ticks_total}
        except Exception:
            pass

        # Build a CompanyShares revenue lookup keyed by business_id
        revenue_map = {}
        try:
            from banks.brokerage_firm import CompanyShares, SessionLocal as BrkSession
            bdb = BrkSession()
            shares = bdb.query(CompanyShares).filter(CompanyShares.owner_id == player_id).all()
            for cs in shares:
                if cs.business_id:
                    revenue_map[cs.business_id] = {
                        "revenue_7d": cs.revenue_7d or 0.0,
                        "revenue_30d": cs.revenue_30d or 0.0,
                    }
            bdb.close()
        except Exception:
            pass

        result = []
        for b in businesses:
            cfg = BUSINESS_TYPES.get(b.business_type, {})
            cycles = cfg.get("cycles_to_complete", 0)
            wage = cfg.get("base_wage_cost", 0.0)

            try:
                import json
                paused_lines = len(json.loads(b.paused_lines or "[]"))
                paused_products = len(json.loads(b.paused_products or "[]"))
            except Exception:
                paused_lines = paused_products = 0

            sale = sale_map.get(b.id)
            rev = revenue_map.get(b.id)

            result.append({
                "id": b.id,
                "business_type": b.business_type,
                "land_plot_id": b.land_plot_id,
                "district_id": b.district_id,
                "is_active": b.is_active,
                "progress_ticks": b.progress_ticks,
                "cycles_to_complete": cycles,
                "base_wage_cost": wage,
                "paused_lines": paused_lines,
                "paused_products": paused_products,
                "dismantling": sale,
                "revenue_7d": rev["revenue_7d"] if rev else None,
                "revenue_30d": rev["revenue_30d"] if rev else None,
            })
        db.close()
        return result
    except Exception:
        return []


def admin_create_business(admin_id: int, owner_id: int, plot_id: int, business_type_key: str) -> dict:
    """Create a business on a vacant land plot without charging the owner."""
    try:
        from business import SessionLocal as BizSession, Business, BUSINESS_TYPES
        from land import get_db as land_db_fn, LandPlot
        if business_type_key not in BUSINESS_TYPES:
            return {"ok": False, "error": f"Unknown business type: {business_type_key}"}
        config = BUSINESS_TYPES[business_type_key]
        db = BizSession()
        ldb = land_db_fn()
        try:
            plot = ldb.query(LandPlot).filter(LandPlot.id == plot_id).first()
            if not plot:
                return {"ok": False, "error": f"Plot #{plot_id} not found"}
            if plot.owner_id != owner_id:
                return {"ok": False, "error": f"Plot #{plot_id} not owned by player #{owner_id}"}
            if plot.occupied_by_business_id is not None:
                return {"ok": False, "error": f"Plot #{plot_id} already occupied by business #{plot.occupied_by_business_id}"}
            allowed = config.get("allowed_terrain")
            if allowed and plot.terrain_type not in allowed:
                return {"ok": False, "error": f"Terrain '{plot.terrain_type}' not allowed for {business_type_key} (needs: {', '.join(allowed)})"}
            business = Business(
                owner_id=owner_id,
                land_plot_id=plot_id,
                business_type=business_type_key,
                progress_ticks=0,
                is_active=True,
            )
            db.add(business)
            db.commit()
            db.refresh(business)
            plot.occupied_by_business_id = business.id
            ldb.commit()
            log_action(admin_id, "create_business", owner_id, f"Created {business_type_key} on plot #{plot_id} (biz #{business.id})")
            return {"ok": True, "business_id": business.id}
        finally:
            db.close()
            ldb.close()
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ==========================
# LAND BANK MANAGEMENT
# ==========================

def get_land_bank_entries() -> list:
    """Get all plots in the land bank."""
    try:
        from land_market import get_land_bank_plots, LandBank
        from land import get_db as land_db, LandPlot
        bank_plots = get_land_bank_plots()
        ldb = land_db()
        result = []
        for entry in bank_plots:
            plot = ldb.query(LandPlot).filter(LandPlot.id == entry.land_plot_id).first()
            result.append({
                "bank_id": entry.id,
                "land_plot_id": entry.land_plot_id,
                "terrain_type": plot.terrain_type if plot else "?",
                "proximity_features": plot.proximity_features if plot else "",
                "size": plot.size if plot else 0,
                "times_auctioned": entry.times_auctioned,
                "last_auction_price": entry.last_auction_price,
                "added_at": entry.added_at.isoformat() if entry.added_at else None,
            })
        ldb.close()
        return result
    except Exception:
        return []


def admin_add_to_land_bank(admin_id: int, terrain_type: str, proximity: str = "") -> dict:
    """Admin creates a new government plot and adds it to the land bank."""
    try:
        from land import create_land_plot
        from land_market import add_to_land_bank, TERRAIN_BASE_PRICES, is_land_bank_full, LAND_BANK_MAX_SLOTS
        if is_land_bank_full():
            return {"ok": False, "error": f"Land bank is full ({LAND_BANK_MAX_SLOTS}/{LAND_BANK_MAX_SLOTS} slots)"}
        prox_list = [f.strip() for f in proximity.split(",") if f.strip()] if proximity else None
        plot = create_land_plot(
            owner_id=0,
            terrain_type=terrain_type,
            proximity_features=prox_list,
            size=1.0,
            is_starter=False,
            is_government=True,
        )
        base_price = TERRAIN_BASE_PRICES.get(terrain_type, 15000)
        add_to_land_bank(plot.id, auction_id=None, last_price=base_price)
        log_action(admin_id, "add_land_bank", details=f"Plot #{plot.id} ({terrain_type})")
        return {"ok": True, "plot_id": plot.id}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def admin_remove_from_land_bank(admin_id: int, land_plot_id: int, delete_plot: bool = False) -> dict:
    """Admin removes a plot from the land bank, optionally deleting it."""
    try:
        from land_market import remove_from_land_bank
        removed = remove_from_land_bank(land_plot_id)
        if not removed:
            return {"ok": False, "error": "Plot not in land bank"}
        if delete_plot:
            from land import get_db as land_db, LandPlot
            db = land_db()
            plot = db.query(LandPlot).filter(LandPlot.id == land_plot_id).first()
            if plot:
                db.delete(plot)
                db.commit()
            db.close()
        log_action(admin_id, "remove_land_bank", details=f"Plot #{land_plot_id} (deleted={delete_plot})")
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ==========================
# CHAT ROOM OVERVIEW
# ==========================

def get_chat_rooms_overview() -> list:
    """Get all chat rooms with online counts."""
    try:
        from chat import STATIC_ROOMS, manager, get_room_messages
        rooms = []
        for r in STATIC_ROOMS:
            count = manager.get_online_count(r["id"])
            recent = get_room_messages(r["id"], limit=5)
            rooms.append({
                "id": r["id"],
                "name": r["name"],
                "icon": r["icon"],
                "read_only": r["read_only"],
                "online_count": count,
                "recent_messages": recent,
            })
        return rooms
    except Exception:
        return []


def get_chat_room_messages(room_id: str, limit: int = 50) -> list:
    """Get messages for a specific room."""
    try:
        from chat import get_room_messages, get_patch_notes
        if room_id == "updates":
            return get_patch_notes()
        return get_room_messages(room_id, limit=limit)
    except Exception:
        return []


def admin_delete_chat_message(admin_id: int, message_id: int) -> dict:
    """Delete a chat message as an admin action."""
    try:
        from chat import delete_chat_message, get_db as chat_get_db, ChatMessage
        db = chat_get_db()
        msg = db.query(ChatMessage).filter(ChatMessage.id == message_id).first()
        if not msg:
            db.close()
            return {"ok": False, "error": "Message not found"}
        room_id = msg.room_id
        snippet = msg.content[:100]
        db.close()
        success = delete_chat_message(message_id)
        if success:
            log_action(admin_id, "delete_chat_message", details=f"room={room_id} msg_id={message_id}: {snippet}")
        return {"ok": success}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ==========================
# P2P OVERVIEW (read-only for admin)
# ==========================

def get_p2p_overview() -> dict:
    """Get summary of P2P contract activity for the admin dashboard."""
    try:
        from p2p import get_db as p2p_db, Contract, ContractStatus
        db = p2p_db()
        total = db.query(Contract).count()
        active = db.query(Contract).filter(Contract.status == ContractStatus.ACTIVE.value).count()
        listed = db.query(Contract).filter(Contract.status == ContractStatus.LISTED.value).count()
        breached = db.query(Contract).filter(Contract.status == ContractStatus.BREACHED.value).count()
        completed = db.query(Contract).filter(Contract.status == ContractStatus.COMPLETED.value).count()

        recent = db.query(Contract).order_by(Contract.created_at.desc()).limit(20).all()
        recent_list = []
        for c in recent:
            recent_list.append({
                "id": c.id,
                "creator_id": c.creator_id,
                "holder_id": c.holder_id,
                "status": c.status,
                "bid_mode": c.bid_mode,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            })
        db.close()
        return {
            "total": total,
            "active": active,
            "listed": listed,
            "breached": breached,
            "completed": completed,
            "recent": recent_list,
        }
    except Exception as e:
        return {"error": str(e)}


def get_p2p_contract_detail(contract_id: int) -> Optional[dict]:
    """Get full detail for a single P2P contract including items, bids, and deliveries."""
    try:
        from p2p import get_db as p2p_db, Contract, ContractItem, ContractBid, ContractDelivery
        db = p2p_db()
        try:
            c = db.query(Contract).filter(Contract.id == contract_id).first()
            if not c:
                return None

            items = db.query(ContractItem).filter(ContractItem.contract_id == contract_id).all()
            bids = db.query(ContractBid).filter(ContractBid.contract_id == contract_id).order_by(ContractBid.created_at.desc()).all()
            deliveries = db.query(ContractDelivery).filter(ContractDelivery.contract_id == contract_id).order_by(ContractDelivery.delivery_number.desc()).limit(20).all()

            return {
                "id": c.id,
                "creator_id": c.creator_id,
                "lister_id": c.lister_id,
                "holder_id": c.holder_id,
                "buyer_id": c.buyer_id,
                "status": c.status,
                "contract_mode": c.contract_mode,
                "bid_mode": getattr(c, "bid_mode", None),
                "delivery_interval": c.delivery_interval,
                "contract_length": c.contract_length,
                "total_deliveries": c.total_deliveries,
                "deliveries_completed": c.deliveries_completed,
                "price_per_delivery": c.price_per_delivery,
                "max_price_per_delivery": c.max_price_per_delivery,
                "next_delivery_tick": c.next_delivery_tick,
                "listing_type": c.listing_type,
                "activated_at": c.activated_at.isoformat() if c.activated_at else None,
                "completed_at": c.completed_at.isoformat() if c.completed_at else None,
                "breached_at": c.breached_at.isoformat() if c.breached_at else None,
                "breach_reason": c.breach_reason,
                "breached_by": c.breached_by,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "items": [
                    {"item_type": i.item_type, "quantity_per_delivery": i.quantity_per_delivery}
                    for i in items
                ],
                "bids": [
                    {
                        "id": b.id,
                        "bidder_id": b.bidder_id,
                        "bid_amount": b.bid_amount,
                        "status": b.status,
                        "created_at": b.created_at.isoformat() if b.created_at else None,
                    }
                    for b in bids
                ],
                "deliveries": [
                    {
                        "delivery_number": d.delivery_number,
                        "delivered_at": d.delivered_at.isoformat() if d.delivered_at else None,
                    }
                    for d in deliveries
                ],
            }
        finally:
            db.close()
    except Exception as e:
        return {"error": str(e)}


# ==========================
# DM OVERVIEW (for admin monitoring)
# ==========================

def get_dm_threads_overview(limit: int = 30) -> list:
    """Get recent DM conversation threads for admin viewing."""
    try:
        from chat import get_all_dm_threads_admin
        return get_all_dm_threads_admin(limit=limit)
    except Exception:
        return []


def get_dm_thread_messages(player_a: int, player_b: int, limit: int = 100) -> list:
    """Get DM messages between two players for admin viewing."""
    try:
        from chat import get_dm_thread_admin
        return get_dm_thread_admin(player_a, player_b, limit=limit)
    except Exception:
        return []


# ==========================
# DISTRICT ADMIN
# ==========================

def admin_create_district(admin_id: int, player_id: int, district_type: str, size: float = 5.0) -> dict:
    """Admin grants a district directly to a player (no plot sacrifice required)."""
    try:
        from districts import District, DISTRICT_TYPES, get_db as get_dist_db, DISTRICT_TAX_MULTIPLIER
        if district_type not in DISTRICT_TYPES:
            return {"ok": False, "error": f"Unknown district type: {district_type}"}
        cfg = DISTRICT_TYPES[district_type]
        terrain_type = cfg["district_terrain"]
        monthly_tax = cfg["base_tax"] * size * DISTRICT_TAX_MULTIPLIER
        db = get_dist_db()
        district = District(
            owner_id=player_id,
            district_type=district_type,
            terrain_type=terrain_type,
            size=size,
            plots_merged=0,
            monthly_tax=monthly_tax,
            source_plot_ids="admin_grant",
        )
        db.add(district)
        db.commit()
        db.refresh(district)
        db.close()
        log_action(admin_id, "create_district", player_id, f"{district_type} size={size} → district #{district.id}")
        return {"ok": True, "district_id": district.id}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def admin_delete_district(admin_id: int, district_id: int) -> dict:
    """Admin deletes a district. Clears any occupying business link."""
    try:
        from districts import District, get_db as get_dist_db
        db = get_dist_db()
        district = db.query(District).filter(District.id == district_id).first()
        if not district:
            db.close()
            return {"ok": False, "error": "District not found"}
        owner_id = district.owner_id
        db.delete(district)
        db.commit()
        db.close()
        log_action(admin_id, "delete_district", owner_id, f"Deleted district #{district_id}")
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def admin_edit_district_tax(admin_id: int, district_id: int, new_tax: float) -> dict:
    """Admin overrides the monthly tax on a district."""
    try:
        from districts import District, get_db as get_dist_db
        db = get_dist_db()
        district = db.query(District).filter(District.id == district_id).first()
        if not district:
            db.close()
            return {"ok": False, "error": "District not found"}
        owner_id = district.owner_id   # capture before session closes
        old_tax = district.monthly_tax
        district.monthly_tax = new_tax
        db.commit()
        db.close()
        log_action(admin_id, "edit_district_tax", owner_id, f"District #{district_id} tax ${old_tax:,.0f} → ${new_tax:,.0f}")
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ==========================
# CITY ADMIN
# ==========================

def admin_create_city(admin_id: int, city_name: str, mayor_id: int) -> dict:
    """
    Admin shortcut: create a city without district or cost requirements.
    The named player becomes mayor and a bank is seeded with $0 reserves.
    """
    try:
        from cities import City, CityMember, CityBank, get_db as get_city_db, get_player_city
        from auth import Player

        city_name = city_name.strip()
        if not city_name:
            return {"ok": False, "error": "City name cannot be empty"}

        db = get_city_db()
        try:
            # Check name uniqueness
            existing = db.query(City).filter(City.name == city_name).first()
            if existing:
                return {"ok": False, "error": f"A city named '{city_name}' already exists"}

            # Validate mayor player
            player = db.query(Player).filter(Player.id == mayor_id).first()
            if not player:
                return {"ok": False, "error": "Mayor player not found"}

            # Check player isn't already in a city
            current = get_player_city(mayor_id)
            if current:
                return {"ok": False, "error": f"Player is already a member of '{current.name}'"}

            # Create city
            city = City(
                name=city_name,
                mayor_id=mayor_id,
                application_fee=50_000.0,
                relocation_fee=10_000.0,
                application_fee_percent=25.0,
                relocation_fee_percent=10.0,
            )
            db.add(city)
            db.flush()

            # Add mayor as member
            membership = CityMember(city_id=city.id, player_id=mayor_id)
            db.add(membership)

            # Create bank with zero reserves
            bank = CityBank(city_id=city.id, cash_reserves=0.0)
            db.add(bank)

            db.commit()
            return {"ok": True, "city_id": city.id, "msg": f"City '{city_name}' created (ID #{city.id})"}
        finally:
            db.close()
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_all_cities_admin() -> list:
    """Return all cities with member counts for admin overview."""
    try:
        from cities import get_all_cities
        return get_all_cities()
    except Exception:
        return []


def get_player_city_info(player_id: int) -> Optional[dict]:
    """Return the city a player belongs to, if any."""
    try:
        from cities import get_player_city
        city = get_player_city(player_id)
        if not city:
            return None
        return {"id": city.id, "name": city.name, "is_mayor": city.mayor_id == player_id}
    except Exception:
        return None


def admin_add_player_to_city(admin_id: int, player_id: int, city_id: int) -> dict:
    """Admin force-adds a player to a city, bypassing the application/fee system."""
    try:
        from cities import City, CityMember, is_city_member, get_db as get_city_db, get_player_city
        # Ensure not already in a city
        current = get_player_city(player_id)
        if current:
            return {"ok": False, "error": f"Player is already a member of {current.name}"}
        db = get_city_db()
        city = db.query(City).filter(City.id == city_id).first()
        if not city:
            db.close()
            return {"ok": False, "error": "City not found"}
        member_count = db.query(CityMember).filter(CityMember.city_id == city_id).count()
        try:
            from city_projects import get_effective_max_members
            _effective_max = get_effective_max_members(city_id)
        except Exception:
            from cities import MAX_CITY_MEMBERS
            _effective_max = MAX_CITY_MEMBERS
        if member_count >= _effective_max:
            db.close()
            return {"ok": False, "error": f"City is at max capacity ({_effective_max})"}
        member = CityMember(player_id=player_id, city_id=city_id, application_fee_paid=0.0)
        db.add(member)
        db.commit()
        db.close()
        log_action(admin_id, "city_add_member", player_id, f"Force-added to city #{city_id} ({city.name})")
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def admin_remove_player_from_city(admin_id: int, player_id: int) -> dict:
    """Admin force-removes a player from their current city."""
    try:
        from cities import CityMember, City, get_db as get_city_db
        db = get_city_db()
        member = db.query(CityMember).filter(CityMember.player_id == player_id).first()
        if not member:
            db.close()
            return {"ok": False, "error": "Player is not a city member"}
        city = db.query(City).filter(City.id == member.city_id).first()
        city_name = city.name if city else f"#{member.city_id}"
        if city and city.mayor_id == player_id:
            db.close()
            return {"ok": False, "error": "Cannot remove the mayor — reassign mayor first"}
        db.delete(member)
        db.commit()
        db.close()
        log_action(admin_id, "city_remove_member", player_id, f"Force-removed from city {city_name}")
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ==========================
# COUNTY ADMIN
# ==========================

def get_all_counties_admin() -> list:
    """Return all counties for admin overview."""
    try:
        from counties import get_all_counties
        return get_all_counties()
    except Exception:
        return []


def get_player_county_info(player_id: int) -> Optional[dict]:
    """Return county info for the player's city."""
    try:
        from counties import get_player_county
        county = get_player_county(player_id)
        if not county:
            return None
        return {"id": county.id, "name": county.name, "crypto_symbol": county.crypto_symbol}
    except Exception:
        return None


def admin_add_city_to_county(admin_id: int, city_id: int, county_id: int) -> dict:
    """Admin force-adds a city to a county, bypassing the petition system."""
    try:
        from counties import County, CountyCity, get_db as get_county_db, MAX_COUNTY_CITIES, get_county_cities
        db = get_county_db()
        county = db.query(County).filter(County.id == county_id).first()
        if not county:
            db.close()
            return {"ok": False, "error": "County not found"}
        existing = db.query(CountyCity).filter(CountyCity.city_id == city_id).first()
        if existing:
            db.close()
            return {"ok": False, "error": "City is already in a county"}
        city_count = db.query(CountyCity).filter(CountyCity.county_id == county_id).count()
        if city_count >= MAX_COUNTY_CITIES:
            db.close()
            return {"ok": False, "error": f"County is at max capacity ({MAX_COUNTY_CITIES} cities)"}
        link = CountyCity(county_id=county_id, city_id=city_id)
        db.add(link)
        db.commit()
        db.close()
        log_action(admin_id, "county_add_city", None, f"Force-added city #{city_id} to county #{county_id} ({county.name})")
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def admin_remove_city_from_county(admin_id: int, city_id: int) -> dict:
    """Admin force-removes a city from its county."""
    try:
        from counties import CountyCity, get_db as get_county_db
        db = get_county_db()
        link = db.query(CountyCity).filter(CountyCity.city_id == city_id).first()
        if not link:
            db.close()
            return {"ok": False, "error": "City is not in any county"}
        county_id = link.county_id
        db.delete(link)
        db.commit()
        db.close()
        log_action(admin_id, "county_remove_city", None, f"Force-removed city #{city_id} from county #{county_id}")
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def admin_delete_city(admin_id: int, city_id: int) -> dict:
    """
    Permanently delete a city and ALL associated data:
      cities, city_banks, city_members, city_applications, city_polls,
      city_votes, city_stable_coin_balances, city_bank_loans,
      city_debt_assumptions, city_project_instances (+ vaults),
      county_cities link.
    """
    try:
        from cities import (
            City, CityBank, CityMember, CityApplication, CityPoll,
            CityVote, CityStableCoinBalance, CityBankLoan,
            CityDebtAssumption, CityProductionLog,
            get_db as get_city_db,
        )
        from counties import CountyCity, get_db as get_county_db
        from city_projects import (
            CityProjectInstance, CityProjectVault,
            get_db as cp_get_db,
        )

        # Verify city exists and warn if it has members
        city_db = get_city_db()
        city = city_db.query(City).filter(City.id == city_id).first()
        if not city:
            city_db.close()
            return {"ok": False, "error": f"City #{city_id} not found"}
        city_name = city.name
        member_count = city_db.query(CityMember).filter(CityMember.city_id == city_id).count()
        city_db.close()
        if member_count > 0:
            log_action(admin_id, "delete_city_attempt", None,
                       f"Admin #{admin_id} force-deleted city #{city_id} '{city_name}' which had {member_count} member(s)")

        # 1. Remove city_project_instances and vaults
        cp_db = cp_get_db()
        try:
            cp_db.query(CityProjectVault).filter(
                CityProjectVault.city_id == city_id
            ).delete(synchronize_session=False)
            cp_db.query(CityProjectInstance).filter(
                CityProjectInstance.city_id == city_id
            ).delete(synchronize_session=False)
            cp_db.commit()
        finally:
            cp_db.close()

        # 2. Remove county link
        co_db = get_county_db()
        try:
            co_db.query(CountyCity).filter(
                CountyCity.city_id == city_id
            ).delete(synchronize_session=False)
            co_db.commit()
        finally:
            co_db.close()

        # 3. Remove all city-table records
        city_db = get_city_db()
        try:
            # CityVote has poll_id only — delete via poll subquery first
            poll_ids = [
                row.id for row in city_db.query(CityPoll.id).filter(
                    CityPoll.city_id == city_id
                ).all()
            ]
            if poll_ids:
                city_db.query(CityVote).filter(
                    CityVote.poll_id.in_(poll_ids)
                ).delete(synchronize_session=False)

            # CityBankLoan uses city_bank_id; CityDebtAssumption uses loan_id
            bank = city_db.query(CityBank).filter(
                CityBank.city_id == city_id
            ).first()
            if bank:
                loan_ids = [
                    row.id for row in city_db.query(CityBankLoan.id).filter(
                        CityBankLoan.city_bank_id == bank.id
                    ).all()
                ]
                if loan_ids:
                    city_db.query(CityDebtAssumption).filter(
                        CityDebtAssumption.loan_id.in_(loan_ids)
                    ).delete(synchronize_session=False)
                city_db.query(CityBankLoan).filter(
                    CityBankLoan.city_bank_id == bank.id
                ).delete(synchronize_session=False)

            for model in (
                CityApplication, CityPoll,
                CityStableCoinBalance, CityProductionLog,
                CityMember, CityBank,
            ):
                city_db.query(model).filter(
                    model.city_id == city_id
                ).delete(synchronize_session=False)
            city_db.query(City).filter(City.id == city_id).delete(
                synchronize_session=False
            )
            city_db.commit()
        finally:
            city_db.close()

        log_action(admin_id, "delete_city", None,
                   f"Deleted city #{city_id} '{city_name}' and all assets")
        return {"ok": True, "msg": f"City '{city_name}' (#{city_id}) permanently deleted."}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def admin_delete_county(admin_id: int, county_id: int) -> dict:
    """
    Permanently delete a county and ALL associated data:
      counties, county_cities, county_petitions, county_polls,
      county_votes, mining_deposits, crypto_wallets (for county symbol),
      governance_cycles, crypto_exchange_orders, crypto_price_history.
    """
    try:
        from counties import (
            County, CountyCity, CountyPetition, CountyPoll, CountyVote,
            MiningDeposit, CryptoWallet, GovernanceCycle,
            get_db as get_county_db,
        )

        co_db = get_county_db()
        county = co_db.query(County).filter(County.id == county_id).first()
        if not county:
            co_db.close()
            return {"ok": False, "error": f"County #{county_id} not found"}
        county_name   = county.name
        crypto_symbol = county.crypto_symbol  # may be None

        try:
            # Remove all wallets holding this county's crypto token
            if crypto_symbol:
                co_db.query(CryptoWallet).filter(
                    CryptoWallet.crypto_symbol == crypto_symbol
                ).delete(synchronize_session=False)

                # Remove exchange orders and price history for this token
                try:
                    from counties import CryptoExchangeOrder, CryptoPriceHistory
                    co_db.query(CryptoExchangeOrder).filter(
                        (CryptoExchangeOrder.sell_crypto_symbol == crypto_symbol) |
                        (CryptoExchangeOrder.buy_crypto_symbol  == crypto_symbol)
                    ).delete(synchronize_session=False)
                    co_db.query(CryptoPriceHistory).filter(
                        CryptoPriceHistory.crypto_symbol == crypto_symbol
                    ).delete(synchronize_session=False)
                except Exception:
                    pass  # tables may not exist yet

            # Remove governance cycles
            co_db.query(GovernanceCycle).filter(
                GovernanceCycle.county_id == county_id
            ).delete(synchronize_session=False)
            # CountyVote has poll_id only — delete via poll subquery first
            poll_ids = [
                row.id for row in co_db.query(CountyPoll.id).filter(
                    CountyPoll.county_id == county_id
                ).all()
            ]
            if poll_ids:
                co_db.query(CountyVote).filter(
                    CountyVote.poll_id.in_(poll_ids)
                ).delete(synchronize_session=False)
            co_db.query(CountyPoll).filter(
                CountyPoll.county_id == county_id
            ).delete(synchronize_session=False)
            # CountyPetition uses target_county_id for county membership
            co_db.query(CountyPetition).filter(
                CountyPetition.target_county_id == county_id
            ).delete(synchronize_session=False)
            co_db.query(MiningDeposit).filter(
                MiningDeposit.county_id == county_id
            ).delete(synchronize_session=False)
            co_db.query(CountyCity).filter(
                CountyCity.county_id == county_id
            ).delete(synchronize_session=False)
            co_db.query(County).filter(County.id == county_id).delete(
                synchronize_session=False
            )
            co_db.commit()
        finally:
            co_db.close()

        log_action(admin_id, "delete_county", None,
                   f"Deleted county #{county_id} '{county_name}' (symbol={crypto_symbol}) and all assets")
        return {"ok": True, "msg": f"County '{county_name}' (#{county_id}) permanently deleted."}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def admin_get_city_polls(city_id: int) -> list:
    """Return all polls for a city (active and recent)."""
    try:
        from cities import CityPoll, CityVote, get_db as get_city_db
        from auth import Player, get_db as auth_get_db
        db = get_city_db()
        try:
            polls = db.query(CityPoll).filter(
                CityPoll.city_id == city_id
            ).order_by(CityPoll.created_at.desc()).limit(20).all()
            result = []
            for p in polls:
                vote_count = db.query(CityVote).filter(CityVote.poll_id == p.id).count()
                target_name = None
                if p.target_player_id:
                    auth_db = auth_get_db()
                    try:
                        player = auth_db.query(Player).filter(Player.id == p.target_player_id).first()
                        target_name = player.business_name if player else f"#{p.target_player_id}"
                    finally:
                        auth_db.close()
                result.append({
                    "id": p.id,
                    "poll_type": p.poll_type,
                    "target_player_id": p.target_player_id,
                    "target_name": target_name,
                    "proposed_currency": p.proposed_currency,
                    "status": p.status,
                    "yes_votes": p.yes_votes,
                    "no_votes": p.no_votes,
                    "vote_count": vote_count,
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                    "closes_at": p.closes_at.isoformat() if p.closes_at else None,
                })
            return result
        finally:
            db.close()
    except Exception as e:
        return []


def admin_resolve_city_poll(admin_id: int, poll_id: int, force_result: str) -> dict:
    """
    Force-resolve a city poll. force_result must be 'pass', 'fail', or 'cancel'.
    For pass/fail, applies the poll's action (approve application, process banishment, etc.)
    """
    try:
        from cities import (CityPoll, CityApplication, PollStatus, PollType,
                            get_db as get_city_db, process_application_approval,
                            process_banishment, set_city_currency)
        if force_result not in ("pass", "fail", "cancel"):
            return {"ok": False, "error": "force_result must be pass, fail, or cancel"}

        db = get_city_db()
        try:
            poll = db.query(CityPoll).filter(CityPoll.id == poll_id).first()
            if not poll:
                db.close()
                return {"ok": False, "error": "Poll not found"}
            if poll.status != PollStatus.ACTIVE:
                db.close()
                return {"ok": False, "error": f"Poll is already {poll.status}"}

            poll_type = poll.poll_type
            city_id = poll.city_id
            target_player_id = poll.target_player_id
            proposed_currency = poll.proposed_currency

            if force_result == "cancel":
                poll.status = PollStatus.CANCELLED
                db.commit()
                db.close()
                log_action(admin_id, "city_poll_cancel", None,
                           f"Force-cancelled city poll #{poll_id} (type={poll_type})")
                return {"ok": True}

            elif force_result == "pass":
                poll.status = PollStatus.PASSED
                db.commit()
                db.close()
                # Apply the action
                if poll_type == PollType.APPLICATION:
                    db2 = get_city_db()
                    try:
                        app = db2.query(CityApplication).filter(
                            CityApplication.city_id == city_id,
                            CityApplication.applicant_id == target_player_id,
                            CityApplication.status == "pending"
                        ).first()
                        app_id = app.id if app else None
                    finally:
                        db2.close()
                    if app_id:
                        process_application_approval(app_id)
                elif poll_type == PollType.BANISHMENT:
                    process_banishment(city_id, target_player_id)
                elif poll_type == PollType.CURRENCY_CHANGE:
                    set_city_currency(city_id, proposed_currency)
                log_action(admin_id, "city_poll_force_pass", None,
                           f"Force-passed city poll #{poll_id} (type={poll_type})")
                return {"ok": True}

            else:  # fail
                poll.status = PollStatus.FAILED
                db.commit()
                # Reject pending application if applicable
                if poll_type == PollType.APPLICATION and target_player_id:
                    app = db.query(CityApplication).filter(
                        CityApplication.city_id == city_id,
                        CityApplication.applicant_id == target_player_id,
                        CityApplication.status == "pending"
                    ).first()
                    if app:
                        app.status = "rejected"
                        db.commit()
                db.close()
                log_action(admin_id, "city_poll_force_fail", None,
                           f"Force-failed city poll #{poll_id} (type={poll_type})")
                return {"ok": True}

        except Exception as e:
            try:
                db.close()
            except Exception:
                pass
            raise e
    except Exception as e:
        return {"ok": False, "error": str(e)}


def admin_get_county_polls(county_id: int) -> list:
    """Return all polls for a county (active and recent)."""
    try:
        from counties import CountyPoll, CountyVote, get_db as get_county_db
        from cities import City, get_db as get_city_db
        db = get_county_db()
        try:
            polls = db.query(CountyPoll).filter(
                CountyPoll.county_id == county_id
            ).order_by(CountyPoll.created_at.desc()).limit(20).all()
            result = []
            for p in polls:
                vote_count = db.query(CountyVote).filter(CountyVote.poll_id == p.id).count()
                target_city_name = None
                if p.target_city_id:
                    city_db = get_city_db()
                    try:
                        city = city_db.query(City).filter(City.id == p.target_city_id).first()
                        target_city_name = city.name if city else f"#{p.target_city_id}"
                    finally:
                        city_db.close()
                result.append({
                    "id": p.id,
                    "poll_type": p.poll_type,
                    "target_city_id": p.target_city_id,
                    "target_city_name": target_city_name,
                    "status": p.status,
                    "yes_votes": p.yes_votes,
                    "no_votes": p.no_votes,
                    "vote_count": vote_count,
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                    "closes_at": p.closes_at.isoformat() if p.closes_at else None,
                })
            return result
        finally:
            db.close()
    except Exception as e:
        return []


def admin_resolve_county_poll(admin_id: int, poll_id: int, force_result: str) -> dict:
    """Force-resolve a county poll. force_result must be 'pass', 'fail', or 'cancel'."""
    try:
        from counties import (CountyPoll, CountyPollStatus, CountyPollType,
                              get_db as get_county_db, _add_city_to_county)
        if force_result not in ("pass", "fail", "cancel"):
            return {"ok": False, "error": "force_result must be pass, fail, or cancel"}

        db = get_county_db()
        try:
            poll = db.query(CountyPoll).filter(CountyPoll.id == poll_id).first()
            if not poll:
                db.close()
                return {"ok": False, "error": "Poll not found"}
            if poll.status != CountyPollStatus.ACTIVE:
                db.close()
                return {"ok": False, "error": f"Poll is already {poll.status}"}

            poll_type = poll.poll_type
            county_id = poll.county_id
            target_city_id = poll.target_city_id

            if force_result == "cancel":
                poll.status = CountyPollStatus.CANCELLED
                db.commit()
                db.close()
                log_action(admin_id, "county_poll_cancel", None,
                           f"Force-cancelled county poll #{poll_id} (type={poll_type})")
                return {"ok": True}

            elif force_result == "pass":
                poll.status = CountyPollStatus.PASSED
                db.commit()
                db.close()
                if poll_type == CountyPollType.ADD_CITY and target_city_id:
                    _add_city_to_county(county_id, target_city_id, poll_id)
                log_action(admin_id, "county_poll_force_pass", None,
                           f"Force-passed county poll #{poll_id} (type={poll_type})")
                return {"ok": True}

            else:  # fail
                poll.status = CountyPollStatus.FAILED
                db.commit()
                db.close()
                log_action(admin_id, "county_poll_force_fail", None,
                           f"Force-failed county poll #{poll_id} (type={poll_type})")
                return {"ok": True}

        except Exception as e:
            try:
                db.close()
            except Exception:
                pass
            raise e
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ==========================
# MODERATOR MANAGEMENT
# ==========================

def add_moderator(admin_id: int, player_id: int, note: str = "") -> dict:
    """Grant moderator status to a player."""
    if player_id in ADMIN_PLAYER_IDS:
        return {"ok": False, "error": "Full admins cannot be assigned as moderators"}
    db = get_db()
    try:
        existing = db.query(Moderator).filter(Moderator.player_id == player_id).first()
        if existing:
            db.close()
            return {"ok": False, "error": "Player is already a moderator"}
        mod = Moderator(player_id=player_id, granted_by=admin_id, note=note)
        db.add(mod)
        db.commit()
        _refresh_moderator_cache()
        log_action(admin_id, "add_moderator", player_id, note or "Moderator granted")
        print(f"[Admins] Player {player_id} granted moderator by admin {admin_id}")
        return {"ok": True}
    except Exception as e:
        db.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        db.close()


def remove_moderator(admin_id: int, player_id: int) -> dict:
    """Revoke moderator status from a player."""
    db = get_db()
    try:
        mod = db.query(Moderator).filter(Moderator.player_id == player_id).first()
        if not mod:
            db.close()
            return {"ok": False, "error": "Player is not a moderator"}
        db.delete(mod)
        db.commit()
        _refresh_moderator_cache()
        log_action(admin_id, "remove_moderator", player_id, "Moderator revoked")
        print(f"[Admins] Player {player_id} moderator revoked by admin {admin_id}")
        return {"ok": True}
    except Exception as e:
        db.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        db.close()


def get_all_moderators() -> list:
    """Get all current moderators with player names."""
    db = get_db()
    try:
        from auth import Player
        mods = db.query(Moderator).order_by(Moderator.created_at.desc()).all()
        result = []
        for m in mods:
            p = db.query(Player).filter(Player.id == m.player_id).first()
            grantor = db.query(Player).filter(Player.id == m.granted_by).first()
            result.append({
                "id": m.id,
                "player_id": m.player_id,
                "player_name": p.business_name if p else f"Player {m.player_id}",
                "granted_by": m.granted_by,
                "grantor_name": grantor.business_name if grantor else f"Admin {m.granted_by}",
                "note": m.note or "",
                "created_at": m.created_at.isoformat() if m.created_at else None,
            })
        return result
    except Exception as e:
        print(f"[Admins] Error fetching moderators: {e}")
        return []
    finally:
        db.close()


# ==========================
# CHAT MUTE HELPERS
# ==========================

def chat_mute_player(mod_id: int, player_id: int, minutes: int = 0, reason: str = "") -> dict:
    """Mute a player in chat. minutes=0 means permanent."""
    db = get_db()
    expires = datetime.utcnow() + timedelta(minutes=minutes) if minutes > 0 else None
    mute = ChatMute(
        player_id=player_id,
        muted_by=mod_id,
        reason=reason,
        expires_at=expires,
    )
    db.add(mute)
    db.commit()
    db.refresh(mute)
    mute_id = mute.id
    db.close()
    log_mod_action(mod_id, "mute", player_id, None,
                   f"{minutes}m - {reason}" if minutes else f"permanent - {reason}")
    return {"ok": True, "mute_id": mute_id, "expires_at": expires.isoformat() if expires else None}


def lift_chat_mute(mod_id: int, player_id: int) -> dict:
    """Lift all active chat mutes for a player."""
    db = get_db()
    now = datetime.utcnow()
    mutes = db.query(ChatMute).filter(
        ChatMute.player_id == player_id,
        ChatMute.lifted == False,
    ).filter(
        (ChatMute.expires_at == None) | (ChatMute.expires_at > now)
    ).all()
    if not mutes:
        db.close()
        return {"ok": False, "error": "No active mute found"}
    for m in mutes:
        m.lifted = True
        m.lifted_at = now
        m.lifted_by = mod_id
    db.commit()
    db.close()
    log_mod_action(mod_id, "lift_mute", player_id, None, "Mute lifted")
    return {"ok": True}


def get_active_chat_mute(player_id: int) -> Optional[dict]:
    """Return the active chat mute for a player, or None."""
    db = get_db()
    now = datetime.utcnow()
    mute = db.query(ChatMute).filter(
        ChatMute.player_id == player_id,
        ChatMute.lifted == False,
    ).filter(
        (ChatMute.expires_at == None) | (ChatMute.expires_at > now)
    ).order_by(ChatMute.created_at.desc()).first()
    if not mute:
        db.close()
        return None
    result = {
        "id": mute.id,
        "muted_by": mute.muted_by,
        "reason": mute.reason,
        "expires_at": mute.expires_at.isoformat() if mute.expires_at else None,
        "created_at": mute.created_at.isoformat(),
    }
    db.close()
    return result


def get_active_chat_mutes() -> list:
    """Return all currently-active chat mutes."""
    db = get_db()
    now = datetime.utcnow()
    try:
        from auth import Player
        mutes = db.query(ChatMute).filter(
            ChatMute.lifted == False,
        ).filter(
            (ChatMute.expires_at == None) | (ChatMute.expires_at > now)
        ).order_by(ChatMute.created_at.desc()).all()
        result = []
        for m in mutes:
            p = db.query(Player).filter(Player.id == m.player_id).first()
            mod = db.query(Player).filter(Player.id == m.muted_by).first()
            result.append({
                "id": m.id,
                "player_id": m.player_id,
                "player_name": p.business_name if p else f"Player {m.player_id}",
                "muted_by": m.muted_by,
                "mod_name": mod.business_name if mod else f"Mod {m.muted_by}",
                "reason": m.reason or "",
                "expires_at": m.expires_at.isoformat() if m.expires_at else None,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            })
        return result
    except Exception as e:
        print(f"[Admins] get_active_chat_mutes error: {e}")
        return []
    finally:
        db.close()


# ==========================
# MOD ACTION LOG
# ==========================

def log_mod_action(mod_id: int, action: str, target_player_id: int = None,
                   room_id: str = None, details: str = ""):
    db = get_db()
    entry = ModAction(
        mod_id=mod_id,
        action=action,
        target_player_id=target_player_id,
        room_id=room_id,
        details=details,
    )
    db.add(entry)
    db.commit()
    db.close()


def get_mod_actions(limit: int = 100) -> list:
    """Return recent mod actions with actor/target names."""
    db = get_db()
    try:
        from auth import Player
        actions = db.query(ModAction).order_by(ModAction.created_at.desc()).limit(limit).all()
        result = []
        for a in actions:
            actor = db.query(Player).filter(Player.id == a.mod_id).first()
            target = db.query(Player).filter(Player.id == a.target_player_id).first() if a.target_player_id else None
            result.append({
                "id": a.id,
                "mod_id": a.mod_id,
                "mod_name": actor.business_name if actor else f"Mod {a.mod_id}",
                "action": a.action,
                "target_player_id": a.target_player_id,
                "target_name": target.business_name if target else None,
                "room_id": a.room_id,
                "details": a.details or "",
                "created_at": a.created_at.isoformat() if a.created_at else None,
            })
        return result
    except Exception as e:
        print(f"[Admins] get_mod_actions error: {e}")
        return []
    finally:
        db.close()


# ==========================
# CITY PROJECT ADMIN HELPERS
# ==========================

def admin_get_city_projects(city_id: int) -> list:
    """Return all non-deconstructed city project instances for a city."""
    try:
        from city_projects import (
            CityProjectInstance, CITY_PROJECT_TYPES,
            STATUS_DECONSTRUCTED, get_db as cp_get_db,
        )
        db = cp_get_db()
        try:
            instances = db.query(CityProjectInstance).filter(
                CityProjectInstance.city_id == city_id,
                CityProjectInstance.status != STATUS_DECONSTRUCTED,
            ).all()
            result = []
            for inst in instances:
                defn = CITY_PROJECT_TYPES.get(inst.project_type, {})
                ticks_req = inst.construction_ticks_required or 1
                result.append({
                    "id":            inst.id,
                    "project_type":  inst.project_type,
                    "name":          defn.get("name", inst.project_type),
                    "level":         inst.level,
                    "target_level":  inst.target_level,
                    "status":        inst.status,
                    "ticks_required": ticks_req,
                    "ticks_done":    inst.construction_ticks_completed,
                    "progress_pct":  round(100 * min(inst.construction_ticks_completed, ticks_req) / ticks_req, 1),
                })
            return result
        finally:
            db.close()
    except Exception as e:
        print(f"[Admins] admin_get_city_projects error: {e}")
        return []


def admin_force_complete_project(admin_id: int, instance_id: int) -> dict:
    """Force-complete construction/upgrade: set level = target_level, status = active."""
    try:
        from city_projects import CityProjectInstance, STATUS_ACTIVE, get_db as cp_get_db
        db = cp_get_db()
        try:
            inst = db.query(CityProjectInstance).filter(
                CityProjectInstance.id == instance_id
            ).first()
            if not inst:
                return {"ok": False, "error": "Project instance not found."}
            inst.level = inst.target_level
            inst.construction_ticks_completed = inst.construction_ticks_required
            inst.status = STATUS_ACTIVE
            db.commit()
            return {"ok": True}
        except Exception as e:
            db.rollback()
            return {"ok": False, "error": str(e)}
        finally:
            db.close()
    except Exception as e:
        return {"ok": False, "error": str(e)}


def admin_set_project_level(admin_id: int, instance_id: int, new_level: int) -> dict:
    """Directly set a project's level (1–12). Keeps status active."""
    try:
        from city_projects import (
            CityProjectInstance, STATUS_ACTIVE,
            MAX_PROJECT_LEVEL, get_db as cp_get_db,
        )
        if new_level < 0 or new_level > MAX_PROJECT_LEVEL:
            return {"ok": False, "error": f"Level must be 0–{MAX_PROJECT_LEVEL}."}
        db = cp_get_db()
        try:
            inst = db.query(CityProjectInstance).filter(
                CityProjectInstance.id == instance_id
            ).first()
            if not inst:
                return {"ok": False, "error": "Project instance not found."}
            inst.level = new_level
            inst.target_level = new_level
            inst.status = STATUS_ACTIVE
            db.commit()
            return {"ok": True}
        except Exception as e:
            db.rollback()
            return {"ok": False, "error": str(e)}
        finally:
            db.close()
    except Exception as e:
        return {"ok": False, "error": str(e)}


def admin_set_project_status(admin_id: int, instance_id: int, new_status: str) -> dict:
    """Force a project's status to active or paused. Use admin_deconstruct_project for deconstructing."""
    try:
        from city_projects import (
            CityProjectInstance, STATUS_ACTIVE, STATUS_PAUSED,
            STATUS_DECONSTRUCTED, get_db as cp_get_db,
        )
        allowed = {STATUS_ACTIVE, STATUS_PAUSED}
        if new_status not in allowed:
            return {"ok": False, "error": f"Use the Deconstruct button to deconstruct. Status must be one of: {', '.join(sorted(allowed))}."}
        db = cp_get_db()
        try:
            inst = db.query(CityProjectInstance).filter(
                CityProjectInstance.id == instance_id
            ).first()
            if not inst:
                return {"ok": False, "error": "Project instance not found."}
            inst.status = new_status
            db.commit()
            return {"ok": True}
        except Exception as e:
            db.rollback()
            return {"ok": False, "error": str(e)}
        finally:
            db.close()
    except Exception as e:
        return {"ok": False, "error": str(e)}


def admin_deconstruct_project(admin_id: int, instance_id: int) -> dict:
    """Deconstruct a project and clear its vault."""
    try:
        from city_projects import (
            CityProjectInstance, CityProjectVault,
            STATUS_DECONSTRUCTED, CITY_PROJECT_TYPES,
            get_db as cp_get_db,
        )
        db = cp_get_db()
        try:
            inst = db.query(CityProjectInstance).filter(
                CityProjectInstance.id == instance_id
            ).first()
            if not inst:
                return {"ok": False, "error": "Project instance not found."}
            if inst.status == STATUS_DECONSTRUCTED:
                return {"ok": False, "error": "Project is already deconstructed."}
            project_type = inst.project_type
            inst.status = STATUS_DECONSTRUCTED
            # Clear the vault
            db.query(CityProjectVault).filter(
                CityProjectVault.city_id == inst.city_id,
                CityProjectVault.project_type == project_type,
            ).delete()
            db.commit()
            name = CITY_PROJECT_TYPES.get(project_type, {}).get("name", project_type)
            return {"ok": True, "msg": f"{name} deconstructed."}
        except Exception as e:
            db.rollback()
            return {"ok": False, "error": str(e)}
        finally:
            db.close()
    except Exception as e:
        return {"ok": False, "error": str(e)}


def admin_construct_project(admin_id: int, city_id: int, project_type: str) -> dict:
    """Force-create a new project at level 1 (active), bypassing vault and license requirements."""
    try:
        from city_projects import (
            CityProjectInstance, CITY_PROJECT_TYPES,
            STATUS_ACTIVE, STATUS_DECONSTRUCTED,
            MAX_PROJECTS_PER_CITY, get_db as cp_get_db,
            _construction_ticks,
        )
        from datetime import datetime
        if project_type not in CITY_PROJECT_TYPES:
            return {"ok": False, "error": f"Unknown project type '{project_type}'."}
        db = cp_get_db()
        try:
            active_count = db.query(CityProjectInstance).filter(
                CityProjectInstance.city_id == city_id,
                CityProjectInstance.status != STATUS_DECONSTRUCTED,
            ).count()
            if active_count >= MAX_PROJECTS_PER_CITY:
                return {"ok": False, "error": f"City has reached the maximum of {MAX_PROJECTS_PER_CITY} projects."}
            existing = db.query(CityProjectInstance).filter(
                CityProjectInstance.city_id == city_id,
                CityProjectInstance.project_type == project_type,
                CityProjectInstance.status != STATUS_DECONSTRUCTED,
            ).first()
            if existing:
                name = CITY_PROJECT_TYPES[project_type]["name"]
                return {"ok": False, "error": f"City already has a {name}."}
            ticks = _construction_ticks(1)
            inst = CityProjectInstance(
                city_id=city_id,
                project_type=project_type,
                level=1,
                target_level=1,
                status=STATUS_ACTIVE,
                construction_ticks_required=ticks,
                construction_ticks_completed=ticks,
                construction_started_at=datetime.utcnow(),
                started_by=admin_id,
            )
            db.add(inst)
            db.commit()
            name = CITY_PROJECT_TYPES[project_type]["name"]
            return {"ok": True, "msg": f"{name} constructed at level 1."}
        except Exception as e:
            db.rollback()
            return {"ok": False, "error": str(e)}
        finally:
            db.close()
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ==========================
# SHARE CLEANUP
# ==========================

def scan_orphan_shares(db=None) -> dict:
    """Return counts of orphaned/government-accumulated share records without modifying anything."""
    close_db = db is None
    if db is None:
        db = get_db()
    try:
        from banks import BankShareholding, BankEntity
        from banks.brokerage_firm import ShareholderPosition, CompanyShares

        GOVERNMENT_PLAYER_ID = 0

        gov_broker = db.query(ShareholderPosition).filter(
            ShareholderPosition.player_id == GOVERNMENT_PLAYER_ID,
            ShareholderPosition.shares_owned > 0,
        ).all()

        gov_bank = db.query(BankShareholding).filter(
            BankShareholding.player_id == GOVERNMENT_PLAYER_ID,
            BankShareholding.shares_owned > 0,
        ).all()

        zero_broker = db.query(ShareholderPosition).filter(
            ShareholderPosition.shares_owned <= 0,
        ).count()

        zero_bank = db.query(BankShareholding).filter(
            BankShareholding.shares_owned <= 0,
        ).count()

        gov_broker_detail = []
        for pos in gov_broker:
            company = db.query(CompanyShares).filter(CompanyShares.id == pos.company_shares_id).first()
            gov_broker_detail.append({
                "ticker": company.ticker_symbol if company else f"id={pos.company_shares_id}",
                "shares": pos.shares_owned,
                "delisted": company.is_delisted if company else True,
            })

        gov_bank_detail = []
        for h in gov_bank:
            gov_bank_detail.append({"bank_id": h.bank_id, "shares": h.shares_owned})

        # Zombie companies: not delisted but founder is deceased or permanently banned
        from estate import get_db as get_estate_db, DeceasedPlayer
        estate_db = get_estate_db()
        try:
            zombie_companies = []
            live_companies = db.query(CompanyShares).filter(
                CompanyShares.is_delisted == False
            ).all()
            deceased_ids = {
                row.player_id
                for row in estate_db.query(DeceasedPlayer.player_id).all()
            }
        finally:
            estate_db.close()

        banned_ids = {
            row.player_id
            for row in db.query(PlayerBan.player_id).filter(
                PlayerBan.ban_type == "ban",
                PlayerBan.revoked == False,
            ).all()
        }
        inactive_ids = deceased_ids | banned_ids

        for c in live_companies:
            if c.founder_id in inactive_ids:
                reason = "deceased" if c.founder_id in deceased_ids else "banned"
                zombie_companies.append({
                    "ticker": c.ticker_symbol,
                    "founder_id": c.founder_id,
                    "company_id": c.id,
                    "reason": reason,
                })

        return {
            "gov_broker_positions": len(gov_broker),
            "gov_broker_detail": gov_broker_detail,
            "gov_bank_holdings": len(gov_bank),
            "gov_bank_detail": gov_bank_detail,
            "zero_broker_positions": zero_broker,
            "zero_bank_holdings": zero_bank,
            "zombie_companies": zombie_companies,
            "total": len(gov_broker) + len(gov_bank) + zero_broker + zero_bank + len(zombie_companies),
        }
    finally:
        if close_db:
            db.close()


def cleanup_orphan_shares(admin_id: int) -> dict:
    """
    Delete government-accumulated share positions and zero-share ghost records.

    Government brokerage positions: deleted, shares returned to company.shares_in_float.
    Government bank shareholdings: deleted, shares retired from bank.total_shares_issued.
    Zero-share positions/holdings: deleted outright.
    """
    db = get_db()
    try:
        from banks import BankShareholding, BankEntity
        from banks.brokerage_firm import ShareholderPosition, CompanyShares

        GOVERNMENT_PLAYER_ID = 0

        gov_broker = db.query(ShareholderPosition).filter(
            ShareholderPosition.player_id == GOVERNMENT_PLAYER_ID,
            ShareholderPosition.shares_owned > 0,
        ).all()
        for pos in gov_broker:
            company = db.query(CompanyShares).filter(CompanyShares.id == pos.company_shares_id).first()
            if company and not company.is_delisted:
                company.shares_in_float += pos.shares_owned
            db.delete(pos)

        gov_bank = db.query(BankShareholding).filter(
            BankShareholding.player_id == GOVERNMENT_PLAYER_ID,
            BankShareholding.shares_owned > 0,
        ).all()
        for h in gov_bank:
            bank = db.query(BankEntity).filter(BankEntity.bank_id == h.bank_id).first()
            if bank:
                bank.total_shares_issued -= h.shares_owned
            db.delete(h)

        zero_broker = db.query(ShareholderPosition).filter(
            ShareholderPosition.shares_owned <= 0,
        ).delete(synchronize_session=False)

        zero_bank = db.query(BankShareholding).filter(
            BankShareholding.shares_owned <= 0,
        ).delete(synchronize_session=False)

        # Delist zombie companies whose founders are deceased or permanently banned
        from datetime import datetime as _dt
        from estate import get_db as get_estate_db, DeceasedPlayer
        estate_db = get_estate_db()
        zombie_delisted = 0
        try:
            deceased_ids = {
                row.player_id
                for row in estate_db.query(DeceasedPlayer.player_id).all()
            }
        finally:
            estate_db.close()

        banned_ids = {
            row.player_id
            for row in db.query(PlayerBan.player_id).filter(
                PlayerBan.ban_type == "ban",
                PlayerBan.revoked == False,
            ).all()
        }
        inactive_ids = deceased_ids | banned_ids

        live_companies = db.query(CompanyShares).filter(
            CompanyShares.is_delisted == False
        ).all()
        zombie_company_ids = []
        for c in live_companies:
            if c.founder_id in inactive_ids:
                c.is_delisted = True
                c.delisted_at = _dt.utcnow()
                zombie_company_ids.append(c.id)
                zombie_delisted += 1

        # Remove stale WBC50 holdings for newly-delisted zombie companies
        # and cancel all active orders for those companies
        wbc50_cleared = 0
        orders_cancelled = 0
        if zombie_company_ids:
            # Cancel active orders and refund reserved cash to buy-order holders
            try:
                from banks.brokerage_order_book import (
                    OrderBook, OrderStatus, OrderSide, get_db as get_ob_db
                )
                from auth import Player, get_db as get_auth_db
                ob_db = get_ob_db()
                auth_db = get_auth_db()
                try:
                    active = ob_db.query(OrderBook).filter(
                        OrderBook.company_shares_id.in_(zombie_company_ids),
                        OrderBook.status.in_([
                            OrderStatus.PENDING.value, OrderStatus.PARTIAL.value
                        ]),
                    ).all()
                    for order in active:
                        if order.order_side == OrderSide.BUY.value and order.reserved_cash > 0:
                            unfilled = order.quantity - order.filled_quantity
                            cash_to_release = (order.reserved_cash / order.quantity) * unfilled
                            buyer = auth_db.query(Player).filter(
                                Player.id == order.player_id
                            ).first()
                            if buyer:
                                buyer.cash_balance += cash_to_release
                        order.status = OrderStatus.CANCELLED.value
                        orders_cancelled += 1
                    ob_db.commit()
                    auth_db.commit()
                finally:
                    ob_db.close()
                    auth_db.close()
            except Exception as ob_e:
                print(f"[cleanup_orphan_shares] Order cancel error: {ob_e}")

            try:
                from banks.wbc50_index_fund import IndexFundHolding, get_db as get_fund_db
                import banks
                fund_db = get_fund_db()
                bank_db = banks.get_db()
                try:
                    fund_entity = bank_db.query(banks.BankEntity).filter(
                        banks.BankEntity.bank_id == "wbc50_index_fund"
                    ).first()
                    stale = fund_db.query(IndexFundHolding).filter(
                        IndexFundHolding.company_id.in_(zombie_company_ids),
                        IndexFundHolding.shares_held > 0,
                    ).all()
                    for h in stale:
                        if fund_entity and h.shares_held > 0:
                            co = db.query(CompanyShares).filter(CompanyShares.id == h.company_id).first()
                            if co and co.current_price:
                                fund_entity.cash_reserves += h.shares_held * co.current_price
                        h.shares_held = 0
                        h.in_index = False
                        wbc50_cleared += 1
                    fund_db.commit()
                    if fund_entity:
                        bank_db.commit()
                finally:
                    fund_db.close()
                    bank_db.close()
            except Exception as wbc_e:
                print(f"[cleanup_orphan_shares] WBC50 holding cleanup error: {wbc_e}")

        db.commit()

        total = len(gov_broker) + len(gov_bank) + zero_broker + zero_bank + zombie_delisted
        log_action(
            admin_id, "cleanup_orphan_shares", None,
            f"Deleted {total} orphan records: "
            f"{len(gov_broker)} gov broker pos, {len(gov_bank)} gov bank holdings, "
            f"{zero_broker} zero-share broker, {zero_bank} zero-share bank, "
            f"{zombie_delisted} zombie companies delisted, "
            f"{orders_cancelled} open orders cancelled, "
            f"{wbc50_cleared} WBC50 holdings zeroed",
        )
        return {
            "ok": True,
            "total": total,
            "gov_broker": len(gov_broker),
            "gov_bank": len(gov_bank),
            "zero_broker": zero_broker,
            "zero_bank": zero_bank,
            "zombie_delisted": zombie_delisted,
            "orders_cancelled": orders_cancelled,
            "wbc50_cleared": wbc50_cleared,
        }
    except Exception as e:
        db.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        db.close()


# ==========================
# TICK
# ==========================

def tick(current_tick, now):
    pass
