"""
dm.py - Direct Message System Backend

P2P direct messaging between players.
- Conversations auto-expire 3 days after the last message
- Max 50 messages per conversation thread
- Player search for starting new DMs
"""

import json
import uuid
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Set, List

from sqlalchemy import Column, String, Float, DateTime, Integer, Text
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

MAX_DM_LENGTH = 500
MAX_THREAD_MESSAGES = 50
CONVERSATION_TTL_DAYS = 3
DM_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_GROUP_PARTICIPANTS = 12


# ==========================
# MODELS
# ==========================

class DirectMessage(Base):
    __tablename__ = "dm_messages"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    conversation_id = Column(String, index=True, nullable=False)
    sender_id = Column(Integer, index=True, nullable=False)
    sender_name = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class Conversation(Base):
    """Tracks each DM conversation between two players."""
    __tablename__ = "dm_conversations"
    id = Column(String, primary_key=True)  # "min_id:max_id"
    player1_id = Column(Integer, index=True, nullable=False)
    player2_id = Column(Integer, index=True, nullable=False)
    last_message_at = Column(DateTime, default=datetime.utcnow, index=True)
    last_message_preview = Column(String, default="")


class GroupConversation(Base):
    __tablename__ = "dm_group_conversations"
    id                   = Column(String, primary_key=True)  # "grp_<hex>"
    name                 = Column(String, nullable=False, default="Group Chat")
    created_by           = Column(Integer, nullable=False)
    created_at           = Column(DateTime, default=datetime.utcnow)
    last_message_at      = Column(DateTime, default=datetime.utcnow, index=True)
    last_message_preview = Column(String, default="")


class GroupParticipant(Base):
    __tablename__ = "dm_group_participants"
    id              = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String, index=True, nullable=False)
    player_id       = Column(Integer, index=True, nullable=False)
    role            = Column(String, default="member", nullable=False)  # "creator", "mod", "member"
    joined_at       = Column(DateTime, default=datetime.utcnow)


def get_db():
    return SessionLocal()


def initialize():
    """Initialize the DM module."""
    print("[DM] Creating database tables...")
    Base.metadata.create_all(bind=engine)
    # Add role column to existing dm_group_participants tables (no-op if already present)
    try:
        from database import run_ddl_migration
        run_ddl_migration(engine, [
            "ALTER TABLE dm_group_participants ADD COLUMN IF NOT EXISTS role VARCHAR NOT NULL DEFAULT 'member'",
            # Backfill: mark existing creator rows based on GroupConversation.created_by
            """UPDATE dm_group_participants gp
               SET role = 'creator'
               FROM dm_group_conversations gc
               WHERE gp.conversation_id = gc.id
                 AND gp.player_id = gc.created_by
                 AND gp.role = 'member'""",
        ])
    except Exception as e:
        print(f"[DM] DDL migration warning: {e}")
    print("[DM] Module initialized")


# ==========================
# CONVERSATION HELPERS
# ==========================

def make_conversation_id(player1_id: int, player2_id: int) -> str:
    """Create a deterministic conversation ID from two player IDs."""
    a, b = sorted([player1_id, player2_id])
    return f"{a}:{b}"


def get_or_create_conversation(player1_id: int, player2_id: int) -> dict:
    """Get or create a conversation between two players."""
    conv_id = make_conversation_id(player1_id, player2_id)
    db = get_db()
    conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
    if not conv:
        a, b = sorted([player1_id, player2_id])
        conv = Conversation(
            id=conv_id,
            player1_id=a,
            player2_id=b,
            last_message_at=datetime.utcnow(),
            last_message_preview="",
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)
    result = _conv_to_dict(conv)
    db.close()
    return result


def _conv_to_dict(conv) -> dict:
    return {
        "id": conv.id,
        "player1_id": conv.player1_id,
        "player2_id": conv.player2_id,
        "last_message_at": conv.last_message_at.isoformat() if conv.last_message_at else None,
        "last_message_preview": conv.last_message_preview or "",
    }


# ==========================
# MESSAGE FUNCTIONS
# ==========================

def save_dm(conversation_id: str, sender_id: int, sender_name: str, content: str) -> Optional[dict]:
    """Save a DM and enforce the 50-message limit."""
    if not content or len(content) > MAX_DM_LENGTH:
        return None

    db = get_db()

    # Save message
    msg = DirectMessage(
        conversation_id=conversation_id,
        sender_id=sender_id,
        sender_name=sender_name,
        content=content,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)

    result = {
        "id": msg.id,
        "conversation_id": msg.conversation_id,
        "sender_id": msg.sender_id,
        "sender_name": msg.sender_name,
        "content": msg.content,
        "timestamp": msg.created_at.isoformat(),
    }

    # Update conversation last_message_at and preview
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if conv:
        conv.last_message_at = datetime.utcnow()
        conv.last_message_preview = content[:80]
        db.commit()

    # Enforce max 50 messages: delete oldest if over limit
    count = db.query(DirectMessage).filter(
        DirectMessage.conversation_id == conversation_id
    ).count()
    if count > MAX_THREAD_MESSAGES:
        excess = count - MAX_THREAD_MESSAGES
        oldest = db.query(DirectMessage).filter(
            DirectMessage.conversation_id == conversation_id
        ).order_by(DirectMessage.created_at.asc()).limit(excess).all()
        for old_msg in oldest:
            db.delete(old_msg)
        db.commit()

    db.close()
    return result


def get_dm_messages(conversation_id: str, limit: int = MAX_THREAD_MESSAGES) -> list:
    """Get messages for a conversation."""
    db = get_db()
    messages = db.query(DirectMessage).filter(
        DirectMessage.conversation_id == conversation_id
    ).order_by(DirectMessage.created_at.desc()).limit(limit).all()

    result = []
    for msg in reversed(messages):
        result.append({
            "id": msg.id,
            "conversation_id": msg.conversation_id,
            "sender_id": msg.sender_id,
            "sender_name": msg.sender_name,
            "content": msg.content,
            "timestamp": msg.created_at.isoformat(),
        })
    db.close()
    return result


def get_player_conversations(player_id: int) -> list:
    """Get all active conversations for a player, sorted by most recent."""
    db = get_db()
    cutoff = datetime.utcnow() - timedelta(days=CONVERSATION_TTL_DAYS)
    convs = db.query(Conversation).filter(
        ((Conversation.player1_id == player_id) | (Conversation.player2_id == player_id)),
        Conversation.last_message_at >= cutoff
    ).order_by(Conversation.last_message_at.desc()).all()

    result = [_conv_to_dict(c) for c in convs]
    db.close()
    return result


# ==========================
# PLAYER SEARCH
# ==========================

def search_players(query: str, exclude_player_id: int, limit: int = 10) -> list:
    """Case-insensitive progressive search for players by business_name."""
    from auth import get_db as get_auth_db, Player
    if not query or len(query) < 1:
        return []
    db = get_auth_db()
    players = db.query(Player).filter(
        Player.business_name.ilike(f"%{query}%"),
        Player.id != exclude_player_id,
        Player.id != 0,  # exclude government
    ).limit(limit).all()
    result = [{"id": p.id, "name": p.business_name} for p in players]
    db.close()
    return result


# ==========================
# CLEANUP / EXPIRY
# ==========================

def cleanup_expired_conversations():
    """Remove conversations and messages older than TTL."""
    db = get_db()
    cutoff = datetime.utcnow() - timedelta(days=CONVERSATION_TTL_DAYS)

    expired = db.query(Conversation).filter(
        Conversation.last_message_at < cutoff
    ).all()
    for conv in expired:
        db.query(DirectMessage).filter(DirectMessage.conversation_id == conv.id).delete()
        db.delete(conv)

    expired_groups = db.query(GroupConversation).filter(
        GroupConversation.last_message_at < cutoff
    ).all()
    for gconv in expired_groups:
        db.query(DirectMessage).filter(DirectMessage.conversation_id == gconv.id).delete()
        db.query(GroupParticipant).filter(GroupParticipant.conversation_id == gconv.id).delete()
        db.delete(gconv)

    if expired or expired_groups:
        db.commit()
        print(f"[DM] Cleaned up {len(expired)} 1:1 and {len(expired_groups)} group conversations")

    db.close()


# ==========================
# GROUP DM HELPERS
# ==========================

def _has_group_dm_ability(player_id: int) -> bool:
    try:
        from executive import player_has_ability, get_db as get_exec_db
        db = get_exec_db()
        try:
            return player_has_ability(db, player_id, "dm_threeway")
        finally:
            db.close()
    except Exception:
        return False


def create_group_dm(creator_id: int, name: str, initial_ids: list) -> dict:
    if not _has_group_dm_ability(creator_id):
        return {"ok": False, "error": "Requires a Multi-Party DMs executive ability (VP Partnerships or Chief Comms)."}
    name = (name or "Group Chat").strip()[:80]
    participants = list(dict.fromkeys([creator_id] + [int(i) for i in initial_ids if int(i) != creator_id]))
    if len(participants) > MAX_GROUP_PARTICIPANTS:
        return {"ok": False, "error": f"Maximum {MAX_GROUP_PARTICIPANTS} participants allowed."}
    conv_id = "grp_" + uuid.uuid4().hex[:16]
    db = get_db()
    try:
        db.add(GroupConversation(
            id=conv_id, name=name, created_by=creator_id,
            created_at=datetime.utcnow(), last_message_at=datetime.utcnow(),
        ))
        for pid in participants:
            role = "creator" if pid == creator_id else "member"
            db.add(GroupParticipant(conversation_id=conv_id, player_id=pid, role=role))
        db.commit()
        return {"ok": True, "id": conv_id, "name": name, "participants": participants}
    except Exception as e:
        db.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        db.close()


def add_group_participant(conv_id: str, player_id: int, adder_id: int) -> dict:
    db = get_db()
    try:
        conv = db.query(GroupConversation).filter(GroupConversation.id == conv_id).first()
        if not conv:
            return {"ok": False, "error": "Group not found."}
        adder_row = db.query(GroupParticipant).filter(
            GroupParticipant.conversation_id == conv_id,
            GroupParticipant.player_id == adder_id,
        ).first()
        if not adder_row or adder_row.role not in ("creator", "mod"):
            return {"ok": False, "error": "Only the creator or a group mod can add members."}
        count = db.query(GroupParticipant).filter(GroupParticipant.conversation_id == conv_id).count()
        if count >= MAX_GROUP_PARTICIPANTS:
            return {"ok": False, "error": f"Maximum {MAX_GROUP_PARTICIPANTS} participants."}
        exists = db.query(GroupParticipant).filter(
            GroupParticipant.conversation_id == conv_id,
            GroupParticipant.player_id == player_id,
        ).first()
        if exists:
            return {"ok": False, "error": "Player is already in this group."}
        db.add(GroupParticipant(conversation_id=conv_id, player_id=player_id, role="member"))
        db.commit()
        return {"ok": True}
    except Exception as e:
        db.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        db.close()


def remove_group_participant(conv_id: str, player_id: int, remover_id: int) -> dict:
    db = get_db()
    try:
        conv = db.query(GroupConversation).filter(GroupConversation.id == conv_id).first()
        if not conv:
            return {"ok": False, "error": "Group not found."}
        target_row = db.query(GroupParticipant).filter(
            GroupParticipant.conversation_id == conv_id,
            GroupParticipant.player_id == player_id,
        ).first()
        if not target_row:
            return {"ok": False, "error": "Player is not in this group."}
        # Self-leave
        if remover_id == player_id:
            if target_row.role == "creator":
                return {"ok": False, "error": "Transfer ownership before leaving."}
            db.delete(target_row)
            db.commit()
            return {"ok": True}
        # Kicking someone else
        remover_row = db.query(GroupParticipant).filter(
            GroupParticipant.conversation_id == conv_id,
            GroupParticipant.player_id == remover_id,
        ).first()
        if not remover_row:
            return {"ok": False, "error": "You are not in this group."}
        if remover_row.role == "creator":
            pass  # creator can kick anyone
        elif remover_row.role == "mod":
            if target_row.role in ("creator", "mod"):
                return {"ok": False, "error": "Mods can only remove regular members."}
        else:
            return {"ok": False, "error": "Only the creator or a mod can remove members."}
        db.delete(target_row)
        db.commit()
        return {"ok": True}
    except Exception as e:
        db.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        db.close()


def rename_group_dm(conv_id: str, new_name: str, requester_id: int) -> dict:
    db = get_db()
    try:
        conv = db.query(GroupConversation).filter(GroupConversation.id == conv_id).first()
        if not conv:
            return {"ok": False, "error": "Group not found."}
        req_row = db.query(GroupParticipant).filter(
            GroupParticipant.conversation_id == conv_id,
            GroupParticipant.player_id == requester_id,
        ).first()
        if not req_row or req_row.role not in ("creator", "mod"):
            return {"ok": False, "error": "Only the creator or a group mod can rename this group."}
        conv.name = (new_name or "Group Chat").strip()[:80]
        db.commit()
        return {"ok": True, "name": conv.name}
    except Exception as e:
        db.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        db.close()


def get_group_participant_ids(conv_id: str) -> list:
    db = get_db()
    rows = db.query(GroupParticipant).filter(GroupParticipant.conversation_id == conv_id).all()
    result = [r.player_id for r in rows]
    db.close()
    return result


def get_group_participants(conv_id: str) -> list:
    db = get_db()
    rows = db.query(GroupParticipant).filter(GroupParticipant.conversation_id == conv_id).all()
    role_map = {r.player_id: r.role for r in rows}
    ids = list(role_map.keys())
    db.close()
    if not ids:
        return []
    from auth import get_db as get_auth_db, Player
    adb = get_auth_db()
    players = adb.query(Player).filter(Player.id.in_(ids)).all()
    result = [{"id": p.id, "name": p.business_name, "role": role_map.get(p.id, "member")} for p in players]
    adb.close()
    return result


def save_group_dm(conv_id: str, sender_id: int, sender_name: str, content: str) -> Optional[dict]:
    if not content or len(content) > MAX_DM_LENGTH:
        return None
    db = get_db()
    msg = DirectMessage(
        conversation_id=conv_id, sender_id=sender_id,
        sender_name=sender_name, content=content,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    result = {
        "id": msg.id, "conversation_id": msg.conversation_id,
        "sender_id": msg.sender_id, "sender_name": msg.sender_name,
        "content": msg.content, "timestamp": msg.created_at.isoformat(),
    }
    conv = db.query(GroupConversation).filter(GroupConversation.id == conv_id).first()
    if conv:
        conv.last_message_at = datetime.utcnow()
        conv.last_message_preview = content[:80]
        db.commit()
    count = db.query(DirectMessage).filter(DirectMessage.conversation_id == conv_id).count()
    if count > MAX_THREAD_MESSAGES:
        excess = count - MAX_THREAD_MESSAGES
        oldest = db.query(DirectMessage).filter(
            DirectMessage.conversation_id == conv_id
        ).order_by(DirectMessage.created_at.asc()).limit(excess).all()
        for old_msg in oldest:
            db.delete(old_msg)
        db.commit()
    db.close()
    return result


def get_player_group_conversations(player_id: int) -> list:
    db = get_db()
    cutoff = datetime.utcnow() - timedelta(days=CONVERSATION_TTL_DAYS)
    part_rows = db.query(GroupParticipant).filter(GroupParticipant.player_id == player_id).all()
    conv_ids = [r.conversation_id for r in part_rows]
    if not conv_ids:
        db.close()
        return []
    convs = db.query(GroupConversation).filter(
        GroupConversation.id.in_(conv_ids),
        GroupConversation.last_message_at >= cutoff,
    ).order_by(GroupConversation.last_message_at.desc()).all()
    role_by_conv = {r.conversation_id: r.role for r in part_rows}
    result = []
    for c in convs:
        count = db.query(GroupParticipant).filter(GroupParticipant.conversation_id == c.id).count()
        result.append({
            "id": c.id, "name": c.name, "created_by": c.created_by,
            "participant_count": count,
            "my_role": role_by_conv.get(c.id, "member"),
            "last_message_at": c.last_message_at.isoformat() if c.last_message_at else None,
            "last_message_preview": c.last_message_preview or "",
            "is_group": True,
        })
    db.close()
    return result


def get_participant_role(conv_id: str, player_id: int) -> Optional[str]:
    """Return a player's role in a group DM, or None if not a member."""
    db = get_db()
    row = db.query(GroupParticipant).filter(
        GroupParticipant.conversation_id == conv_id,
        GroupParticipant.player_id == player_id,
    ).first()
    role = row.role if row else None
    db.close()
    return role


def set_participant_role(conv_id: str, target_id: int, new_role: str, requester_id: int) -> dict:
    """Promote/demote a member, or transfer ownership. Only the creator can call this.

    new_role values:
      "mod"    — promote a member to DM mod
      "member" — demote a mod back to member
      "creator" — transfer ownership (old creator becomes "mod")
    """
    if new_role not in ("creator", "mod", "member"):
        return {"ok": False, "error": "Invalid role."}
    if target_id == requester_id:
        return {"ok": False, "error": "Use 'transfer ownership' to hand off creator status."}
    db = get_db()
    try:
        req_row = db.query(GroupParticipant).filter(
            GroupParticipant.conversation_id == conv_id,
            GroupParticipant.player_id == requester_id,
        ).first()
        if not req_row or req_row.role != "creator":
            return {"ok": False, "error": "Only the creator can change member roles."}
        target_row = db.query(GroupParticipant).filter(
            GroupParticipant.conversation_id == conv_id,
            GroupParticipant.player_id == target_id,
        ).first()
        if not target_row:
            return {"ok": False, "error": "Player is not in this group."}
        if new_role == "creator":
            # Transfer: old creator becomes mod, new owner becomes creator
            req_row.role = "mod"
            target_row.role = "creator"
            conv = db.query(GroupConversation).filter(GroupConversation.id == conv_id).first()
            if conv:
                conv.created_by = target_id
        else:
            target_row.role = new_role
        db.commit()
        return {"ok": True, "new_role": new_role}
    except Exception as e:
        db.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        db.close()


def delete_group_dm(conv_id: str, requester_id: int) -> dict:
    """Delete the entire group DM (messages, participants, conversation). Creator only.

    Returns participant_ids so the caller can broadcast group_removed to everyone.
    """
    db = get_db()
    try:
        req_row = db.query(GroupParticipant).filter(
            GroupParticipant.conversation_id == conv_id,
            GroupParticipant.player_id == requester_id,
        ).first()
        if not req_row or req_row.role != "creator":
            return {"ok": False, "error": "Only the creator can delete the group."}
        pids = [r.player_id for r in db.query(GroupParticipant).filter(
            GroupParticipant.conversation_id == conv_id,
        ).all()]
        db.query(DirectMessage).filter(DirectMessage.conversation_id == conv_id).delete()
        db.query(GroupParticipant).filter(GroupParticipant.conversation_id == conv_id).delete()
        db.query(GroupConversation).filter(GroupConversation.id == conv_id).delete()
        db.commit()
        return {"ok": True, "participant_ids": pids}
    except Exception as e:
        db.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        db.close()


# ==========================
# CONNECTION MANAGER (DM-specific)
# ==========================

class DMConnectionManager:
    def __init__(self):
        self.connections: Dict[int, object] = {}       # player_id -> WebSocket
        self.player_names: Dict[int, str] = {}         # player_id -> display name
        self.typing_users: Dict[str, Set[int]] = {}    # conv_id -> set of player_ids typing
        self.avatar_cache: Dict[int, Optional[str]] = {}

    async def connect(self, websocket, player_id: int, player_name: str):
        self.connections[player_id] = websocket
        self.player_names[player_id] = player_name
        # Load avatar into cache
        from chat import get_avatar
        self.avatar_cache[player_id] = get_avatar(player_id)
        print(f"[DM] Player {player_id} ({player_name}) connected. Total: {len(self.connections)}")

    async def disconnect(self, player_id: int, websocket=None):
        # Guard: only evict if this is still the active connection.
        if websocket is not None and self.connections.get(player_id) is not websocket:
            return
        self.connections.pop(player_id, None)
        self.player_names.pop(player_id, None)
        self.avatar_cache.pop(player_id, None)
        for conv_id in list(self.typing_users.keys()):
            self.typing_users[conv_id].discard(player_id)
        print(f"[DM] Player {player_id} disconnected. Total: {len(self.connections)}")

    async def send_to_user(self, player_id: int, message: dict):
        ws = self.connections.get(player_id)
        if ws:
            try:
                await ws.send_text(json.dumps(message))
            except Exception as e:
                print(f"[DM] send_to_user failed for player {player_id}: {e}")
                await self.disconnect(player_id)
        else:
            print(f"[DM] send_to_user: player {player_id} not connected, message not delivered")

    def set_typing(self, conv_id: str, player_id: int):
        if conv_id not in self.typing_users:
            self.typing_users[conv_id] = set()
        self.typing_users[conv_id].add(player_id)

    def clear_typing(self, conv_id: str, player_id: int):
        if conv_id in self.typing_users:
            self.typing_users[conv_id].discard(player_id)

    def get_typing_names(self, conv_id: str, exclude_id: int = None) -> list:
        pids = self.typing_users.get(conv_id, set())
        names = []
        for pid in pids:
            if pid != exclude_id:
                name = self.player_names.get(pid)
                if name:
                    names.append(name)
        return names

    def is_online(self, player_id: int) -> bool:
        return player_id in self.connections

    async def broadcast_to_participants(self, participant_ids: list, message: dict):
        for pid in participant_ids:
            if pid in self.connections:
                await self.send_to_user(pid, message)


dm_manager = DMConnectionManager()


# ==========================
# TICK
# ==========================

_tick_counter = 0

def tick(current_tick, now):
    global _tick_counter
    _tick_counter += 1
    # Cleanup expired conversations every 720 ticks (~60 minutes)
    if _tick_counter % 720 == 0:
        cleanup_expired_conversations()
