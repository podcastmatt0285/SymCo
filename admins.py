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

from sqlalchemy import create_engine, Column, String, Float, DateTime, Integer, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# ==========================
# DATABASE SETUP
# ==========================

DATABASE_URL = "sqlite:///./wadsworth.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
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


def get_db():
    return SessionLocal()


def initialize():
    Base.metadata.create_all(bind=engine)
    print("[Admins] Module initialized")


# ==========================
# AUTH HELPERS
# ==========================

def is_admin(player_id: int) -> bool:
    return player_id in ADMIN_PLAYER_IDS


def require_admin(session_token: str):
    """Return player if admin, None otherwise."""
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


def get_admin_logs(limit: int = 50) -> list:
    db = get_db()
    logs = db.query(AdminLog).order_by(AdminLog.created_at.desc()).limit(limit).all()
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


# ==========================
# UPDATES CHANNEL POSTING
# ==========================

def post_update(admin_id: int, content: str) -> dict:
    """Post a message to the updates channel as the admin."""
    import auth
    from chat import save_message

    db = auth.get_db()
    player = db.query(auth.Player).filter(auth.Player.id == admin_id).first()
    if not player:
        db.close()
        return {"ok": False, "error": "Admin player not found"}
    admin_name = player.business_name
    db.close()

    saved = save_message("updates", admin_id, admin_name, content)
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


def get_all_item_types() -> list:
    """Get all known item types for the admin dropdown."""
    try:
        import inventory
        return sorted(inventory.ITEM_RECIPES.keys())
    except Exception:
        return []


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
    """Get all districts owned by a player."""
    try:
        from districts import get_player_districts as _get
        districts = _get(player_id)
        result = []
        for d in districts:
            result.append({
                "id": d.id,
                "district_type": d.district_type,
                "terrain_type": d.terrain_type,
                "size": d.size,
                "plots_merged": d.plots_merged,
                "monthly_tax": d.monthly_tax,
                "occupied_by_business_id": d.occupied_by_business_id,
            })
        return result
    except Exception:
        return []


# ==========================
# BUSINESS MANAGEMENT
# ==========================

def get_player_businesses(player_id: int) -> list:
    """Get all businesses owned by a player."""
    try:
        from business import SessionLocal as BizSession, Business
        db = BizSession()
        businesses = db.query(Business).filter(Business.owner_id == player_id).all()
        result = []
        for b in businesses:
            result.append({
                "id": b.id,
                "business_type": b.business_type,
                "land_plot_id": b.land_plot_id,
                "district_id": b.district_id,
                "is_active": b.is_active,
                "progress_ticks": b.progress_ticks,
            })
        db.close()
        return result
    except Exception:
        return []


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
        from land_market import add_to_land_bank, TERRAIN_BASE_PRICES
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
        from chat import get_room_messages
        return get_room_messages(room_id, limit=limit)
    except Exception:
        return []


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


# ==========================
# TICK
# ==========================

async def tick(current_tick, now):
    pass
