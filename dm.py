"""
dm.py - Direct Message System Backend

P2P direct messaging between players.
- Conversations auto-expire 3 days after the last message
- Max 50 messages per conversation thread
- Player search for starting new DMs
"""

import json
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Set, List

from sqlalchemy import create_engine, Column, String, Float, DateTime, Integer, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# ==========================
# DATABASE SETUP
# ==========================

DATABASE_URL = "sqlite:///./symco.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ==========================
# CONSTANTS
# ==========================

MAX_DM_LENGTH = 500
MAX_THREAD_MESSAGES = 50
CONVERSATION_TTL_DAYS = 3
DM_UPLOAD_BYTES = 10 * 1024 * 1024


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


def get_db():
    return SessionLocal()


def initialize():
    """Initialize the DM module."""
    print("[DM] Creating database tables...")
    Base.metadata.create_all(bind=engine)
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
        db.query(DirectMessage).filter(
            DirectMessage.conversation_id == conv.id
        ).delete()
        db.delete(conv)

    if expired:
        db.commit()
        print(f"[DM] Cleaned up {len(expired)} expired conversations")

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

    async def disconnect(self, player_id: int):
        self.connections.pop(player_id, None)
        self.player_names.pop(player_id, None)
        self.avatar_cache.pop(player_id, None)
        for conv_id in list(self.typing_users.keys()):
            self.typing_users[conv_id].discard(player_id)

    async def send_to_user(self, player_id: int, message: dict):
        ws = self.connections.get(player_id)
        if ws:
            try:
                await ws.send_text(json.dumps(message))
            except Exception:
                await self.disconnect(player_id)

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


dm_manager = DMConnectionManager()


# ==========================
# TICK
# ==========================

_tick_counter = 0

async def tick(current_tick, now):
    global _tick_counter
    _tick_counter += 1
    # Cleanup expired conversations every 720 ticks (~60 minutes)
    if _tick_counter % 720 == 0:
        cleanup_expired_conversations()
