"""
chat.py - Chat Room System Backend
Real-time chat with WebSocket support, per-user word filtering, and temporary avatars.
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

DATABASE_URL = "sqlite:///./wadsworth.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ==========================
# CONSTANTS
# ==========================

# Player IDs allowed to post in Updates channel
ADMIN_PLAYER_IDS = {1}

# Static room definitions
STATIC_ROOMS = [
    {"id": "global", "name": "Global Chat", "icon": "🌐", "read_only": False},
    {"id": "trade", "name": "Trade Chat", "icon": "📊", "read_only": False},
    {"id": "qa", "name": "Community Q&A", "icon": "❓", "read_only": False},
    {"id": "recruiting", "name": "City Recruiting", "icon": "🏙️", "read_only": False},
    {"id": "updates", "name": "Updates", "icon": "📢", "read_only": True},
    {"id": "bugs", "name": "Bug Reports & Feedback", "icon": "🐛", "read_only": False},
]

MAX_MESSAGE_LENGTH = 500
MAX_HISTORY = 100
MAX_UPLOAD_BYTES = 10 * 1024 * 1024   # 10MB raw upload limit
AVATAR_SIZE = 128                       # Rendered avatar dimensions (128x128)
AVATAR_QUALITY = 80                     # JPEG compression quality

DEFAULT_BAN_WORDS = [
    # Racial slurs
    "nigger", "nigga", "niggers", "niggas", "coon", "coons", "darkie", "darkies",
    "spic", "spics", "wetback", "wetbacks", "beaner", "beaners", "chink", "chinks",
    "gook", "gooks", "zipperhead", "towelhead", "raghead",
    "kike", "kikes", "hymie", "heeb",
    "wop", "wops", "dago", "dagos",
    "redskin", "redskins", "squaw",
    "paki", "pakis",
    # Homophobic slurs
    "faggot", "faggots", "fag", "fags", "dyke", "dykes", "tranny", "trannies",
    # Sexually explicit
    "pussy", "cock", "cunt", "cunts", "tits", "titties",
    "blowjob", "handjob", "cumshot", "creampie", "gangbang",
    "dildo", "masturbate", "masturbation",
    "pornhub", "xvideos", "xhamster", "brazzers", "onlyfans",
    "fellatio", "cunnilingus",
    "whore", "whores", "slut", "sluts", "skank", "skanks",
    # Other offensive
    "retard", "retards", "retarded",
]


# ==========================
# MODELS
# ==========================

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    room_id = Column(String, index=True, nullable=False)
    sender_id = Column(Integer, index=True, nullable=False)
    sender_name = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class UserBanWord(Base):
    __tablename__ = "user_ban_words"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    player_id = Column(Integer, index=True, nullable=False)
    word = Column(String, nullable=False)


class DirectMessage(Base):
    """Private player-to-player messages."""
    __tablename__ = "direct_messages"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    from_id = Column(Integer, index=True, nullable=False)
    to_id = Column(Integer, index=True, nullable=False)
    from_name = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    is_read = Column(Integer, default=0)  # 0 = unread, 1 = read
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class ChatAvatar(Base):
    __tablename__ = "chat_avatars"
    player_id = Column(Integer, primary_key=True)
    image_data = Column(Text, nullable=False)  # base64 data URI
    updated_at = Column(DateTime, default=datetime.utcnow)


def get_db():
    return SessionLocal()


def initialize():
    Base.metadata.create_all(bind=engine)


# ==========================
# MESSAGE FUNCTIONS
# ==========================

def save_message(room_id: str, sender_id: int, sender_name: str, content: str) -> Optional[dict]:
    """Save a chat message and return it as a dict."""
    if not content or len(content) > MAX_MESSAGE_LENGTH:
        return None
    db = get_db()
    msg = ChatMessage(
        room_id=room_id,
        sender_id=sender_id,
        sender_name=sender_name,
        content=content,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    result = {
        "id": msg.id,
        "room": msg.room_id,
        "sender_id": msg.sender_id,
        "sender_name": msg.sender_name,
        "content": msg.content,
        "timestamp": msg.created_at.isoformat(),
    }
    db.close()
    return result


def get_room_messages(room_id: str, limit: int = MAX_HISTORY) -> list:
    """Get the last N messages for a room."""
    db = get_db()
    messages = db.query(ChatMessage).filter(
        ChatMessage.room_id == room_id
    ).order_by(ChatMessage.created_at.desc()).limit(limit).all()

    result = []
    for msg in reversed(messages):
        result.append({
            "id": msg.id,
            "room": msg.room_id,
            "sender_id": msg.sender_id,
            "sender_name": msg.sender_name,
            "content": msg.content,
            "timestamp": msg.created_at.isoformat(),
        })
    db.close()
    return result


# ==========================
# BAN WORD FUNCTIONS
# ==========================

def get_user_ban_words(player_id: int) -> list:
    db = get_db()
    words = db.query(UserBanWord).filter(UserBanWord.player_id == player_id).all()
    result = [w.word for w in words]
    db.close()
    return result


def initialize_default_ban_words(player_id: int):
    """Set up default ban words for a new chat user."""
    db = get_db()
    existing = db.query(UserBanWord).filter(UserBanWord.player_id == player_id).count()
    if existing > 0:
        db.close()
        return
    for word in DEFAULT_BAN_WORDS:
        db.add(UserBanWord(player_id=player_id, word=word.lower()))
    db.commit()
    db.close()


def set_user_ban_words(player_id: int, words: list):
    """Replace a player's entire ban word list."""
    db = get_db()
    db.query(UserBanWord).filter(UserBanWord.player_id == player_id).delete()
    for word in words:
        w = word.strip().lower()
        if w:
            db.add(UserBanWord(player_id=player_id, word=w))
    db.commit()
    db.close()


def add_ban_word(player_id: int, word: str) -> bool:
    w = word.strip().lower()
    if not w:
        return False
    db = get_db()
    existing = db.query(UserBanWord).filter(
        UserBanWord.player_id == player_id,
        UserBanWord.word == w
    ).first()
    if existing:
        db.close()
        return False
    db.add(UserBanWord(player_id=player_id, word=w))
    db.commit()
    db.close()
    return True


def remove_ban_word(player_id: int, word: str) -> bool:
    w = word.strip().lower()
    db = get_db()
    deleted = db.query(UserBanWord).filter(
        UserBanWord.player_id == player_id,
        UserBanWord.word == w
    ).delete()
    db.commit()
    db.close()
    return deleted > 0


# ==========================
# AVATAR FUNCTIONS
# ==========================

def compress_avatar(data_uri: str) -> Optional[str]:
    """
    Take a base64 data URI of any size, resize to 128x128, compress to JPEG,
    and return a small base64 data URI. Returns None on failure.
    """
    import base64
    import io
    try:
        from PIL import Image

        # Parse data URI: "data:image/png;base64,iVBOR..."
        header, b64data = data_uri.split(",", 1)
        raw_bytes = base64.b64decode(b64data)

        img = Image.open(io.BytesIO(raw_bytes))
        img = img.convert("RGB")  # Drop alpha, normalize format

        # Crop to square center then resize
        w, h = img.size
        side = min(w, h)
        left = (w - side) // 2
        top = (h - side) // 2
        img = img.crop((left, top, left + side, top + side))
        img = img.resize((AVATAR_SIZE, AVATAR_SIZE), Image.LANCZOS)

        # Compress to JPEG
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=AVATAR_QUALITY, optimize=True)
        compressed_b64 = base64.b64encode(buf.getvalue()).decode()
        return f"data:image/jpeg;base64,{compressed_b64}"
    except Exception as e:
        print(f"[Chat] Avatar compression failed: {e}")
        return None


def save_avatar(player_id: int, image_data: str):
    """Compress and save avatar. Accepts any size data URI."""
    compressed = compress_avatar(image_data)
    if not compressed:
        return False
    db = get_db()
    existing = db.query(ChatAvatar).filter(ChatAvatar.player_id == player_id).first()
    if existing:
        existing.image_data = compressed
        existing.updated_at = datetime.utcnow()
    else:
        db.add(ChatAvatar(player_id=player_id, image_data=compressed, updated_at=datetime.utcnow()))
    db.commit()
    db.close()
    return True


def get_avatar(player_id: int) -> Optional[str]:
    db = get_db()
    avatar = db.query(ChatAvatar).filter(ChatAvatar.player_id == player_id).first()
    result = avatar.image_data if avatar else None
    db.close()
    return result


def delete_avatar(player_id: int):
    db = get_db()
    db.query(ChatAvatar).filter(ChatAvatar.player_id == player_id).delete()
    db.commit()
    db.close()


def cleanup_stale_avatars(minutes: int = 60):
    db = get_db()
    cutoff = datetime.utcnow() - timedelta(minutes=minutes)
    db.query(ChatAvatar).filter(ChatAvatar.updated_at < cutoff).delete()
    db.commit()
    db.close()


# ==========================
# PLAYER CITY LOOKUP
# ==========================

def get_player_city(player_id: int) -> Optional[dict]:
    try:
        from cities import get_db as get_cities_db, CityMember, City
        db = get_cities_db()
        member = db.query(CityMember).filter(CityMember.player_id == player_id).first()
        if not member:
            db.close()
            return None
        city = db.query(City).filter(City.id == member.city_id).first()
        if not city:
            db.close()
            return None
        result = {"id": city.id, "name": city.name}
        db.close()
        return result
    except Exception:
        return None


def get_rooms_for_player(player_id: int) -> list:
    """Get the list of rooms a player can access."""
    rooms = list(STATIC_ROOMS)
    city = get_player_city(player_id)
    if city:
        city_room = {
            "id": f"city_{city['id']}",
            "name": f"{city['name']} City Chat",
            "icon": "🏛️",
            "read_only": False,
        }
        rooms.insert(1, city_room)
    return rooms


# ==========================
# CONNECTION MANAGER
# ==========================

class ConnectionManager:
    def __init__(self):
        self.connections: Dict[int, object] = {}       # player_id -> WebSocket
        self.player_names: Dict[int, str] = {}         # player_id -> display name
        self.player_rooms: Dict[int, Set[str]] = {}    # player_id -> set of room IDs
        self.typing_users: Dict[str, Set[int]] = {}    # room_id -> set of player IDs typing
        self.avatar_cache: Dict[int, Optional[str]] = {}  # player_id -> avatar data URI

    async def connect(self, websocket, player_id: int, player_name: str, rooms: list):
        self.connections[player_id] = websocket
        self.player_names[player_id] = player_name
        self.player_rooms[player_id] = set(r["id"] for r in rooms)
        # Load avatar into cache
        self.avatar_cache[player_id] = get_avatar(player_id)

    async def disconnect(self, player_id: int):
        self.connections.pop(player_id, None)
        self.player_names.pop(player_id, None)
        self.player_rooms.pop(player_id, None)
        self.avatar_cache.pop(player_id, None)
        # Remove from all typing sets
        for room_id in list(self.typing_users.keys()):
            self.typing_users[room_id].discard(player_id)
        # Delete avatar from DB
        delete_avatar(player_id)

    async def broadcast_to_room(self, room_id: str, message: dict):
        """Send a message to all users subscribed to a room."""
        msg_text = json.dumps(message)
        disconnected = []
        for pid, ws in list(self.connections.items()):
            if room_id in self.player_rooms.get(pid, set()):
                try:
                    await ws.send_text(msg_text)
                except Exception:
                    disconnected.append(pid)
        for pid in disconnected:
            await self.disconnect(pid)

    async def send_to_user(self, player_id: int, message: dict):
        ws = self.connections.get(player_id)
        if ws:
            try:
                await ws.send_text(json.dumps(message))
            except Exception:
                await self.disconnect(player_id)

    def get_online_count(self, room_id: str = None) -> int:
        if room_id:
            return sum(1 for pid in self.connections if room_id in self.player_rooms.get(pid, set()))
        return len(self.connections)

    def get_online_users(self, room_id: str) -> list:
        users = []
        for pid in self.connections:
            if room_id in self.player_rooms.get(pid, set()):
                users.append({"id": pid, "name": self.player_names.get(pid, "?")})
        return users

    def set_typing(self, room_id: str, player_id: int):
        if room_id not in self.typing_users:
            self.typing_users[room_id] = set()
        self.typing_users[room_id].add(player_id)

    def clear_typing(self, room_id: str, player_id: int):
        if room_id in self.typing_users:
            self.typing_users[room_id].discard(player_id)

    def get_typing_names(self, room_id: str, exclude_id: int = None) -> list:
        pids = self.typing_users.get(room_id, set())
        names = []
        for pid in pids:
            if pid != exclude_id:
                name = self.player_names.get(pid)
                if name:
                    names.append(name)
        return names


manager = ConnectionManager()


# ==========================
# DIRECT MESSAGE FUNCTIONS
# ==========================

def send_dm(from_id: int, from_name: str, to_id: int, content: str) -> Optional[dict]:
    """Send a direct message. Returns the saved message dict or None."""
    if not content or len(content) > MAX_MESSAGE_LENGTH:
        return None
    if from_id == to_id:
        return None
    db = get_db()
    msg = DirectMessage(
        from_id=from_id,
        to_id=to_id,
        from_name=from_name,
        content=content,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    result = {
        "id": msg.id,
        "from_id": msg.from_id,
        "to_id": msg.to_id,
        "from_name": msg.from_name,
        "content": msg.content,
        "is_read": msg.is_read,
        "created_at": msg.created_at.isoformat(),
    }
    db.close()
    return result


def get_dm_conversations(player_id: int) -> list:
    """Get a list of DM conversations for a player, with last message and unread count."""
    db = get_db()
    # Get all messages involving this player
    from sqlalchemy import or_, func, case
    msgs = db.query(DirectMessage).filter(
        or_(DirectMessage.from_id == player_id, DirectMessage.to_id == player_id)
    ).all()

    # Build conversation map: other_player_id -> {last_msg, unread_count}
    convos = {}
    for m in msgs:
        other_id = m.to_id if m.from_id == player_id else m.from_id
        if other_id not in convos:
            convos[other_id] = {"last_msg": m, "unread": 0, "other_name": ""}
        if m.created_at > convos[other_id]["last_msg"].created_at:
            convos[other_id]["last_msg"] = m
        # Count unread messages sent TO this player
        if m.to_id == player_id and m.is_read == 0:
            convos[other_id]["unread"] += 1

    # Look up player names
    try:
        import auth
        auth_db = auth.get_db()
        for other_id, data in convos.items():
            p = auth_db.query(auth.Player).filter(auth.Player.id == other_id).first()
            data["other_name"] = p.business_name if p else f"Player #{other_id}"
        auth_db.close()
    except Exception:
        pass

    result = []
    for other_id, data in convos.items():
        lm = data["last_msg"]
        result.append({
            "other_id": other_id,
            "other_name": data["other_name"],
            "last_message": lm.content[:80],
            "last_time": lm.created_at.isoformat(),
            "unread": data["unread"],
            "last_from_id": lm.from_id,
        })

    # Sort by most recent message first
    result.sort(key=lambda x: x["last_time"], reverse=True)
    db.close()
    return result


def get_dm_thread(player_id: int, other_id: int, limit: int = 50) -> list:
    """Get messages between two players."""
    db = get_db()
    from sqlalchemy import or_, and_
    msgs = db.query(DirectMessage).filter(
        or_(
            and_(DirectMessage.from_id == player_id, DirectMessage.to_id == other_id),
            and_(DirectMessage.from_id == other_id, DirectMessage.to_id == player_id),
        )
    ).order_by(DirectMessage.created_at.desc()).limit(limit).all()

    result = []
    for m in reversed(msgs):
        result.append({
            "id": m.id,
            "from_id": m.from_id,
            "to_id": m.to_id,
            "from_name": m.from_name,
            "content": m.content,
            "is_read": m.is_read,
            "created_at": m.created_at.isoformat(),
        })
    db.close()
    return result


def mark_dms_read(player_id: int, from_id: int):
    """Mark all DMs from from_id to player_id as read."""
    db = get_db()
    db.query(DirectMessage).filter(
        DirectMessage.from_id == from_id,
        DirectMessage.to_id == player_id,
        DirectMessage.is_read == 0,
    ).update({"is_read": 1})
    db.commit()
    db.close()


def get_unread_dm_count(player_id: int) -> int:
    """Get total unread DM count for a player."""
    db = get_db()
    count = db.query(DirectMessage).filter(
        DirectMessage.to_id == player_id,
        DirectMessage.is_read == 0,
    ).count()
    db.close()
    return count


def get_all_dm_threads_admin(limit: int = 50) -> list:
    """Admin: get recent DM threads overview."""
    db = get_db()
    from sqlalchemy import func
    # Get the most recent DMs grouped by conversation pair
    recent = db.query(DirectMessage).order_by(DirectMessage.created_at.desc()).limit(limit * 2).all()

    # Build unique conversation pairs
    seen_pairs = set()
    threads = []
    for m in recent:
        pair = tuple(sorted([m.from_id, m.to_id]))
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)
        threads.append({
            "player_a": pair[0],
            "player_b": pair[1],
            "last_message": m.content[:80],
            "last_time": m.created_at.isoformat(),
            "last_from": m.from_id,
        })
        if len(threads) >= limit:
            break

    # Look up names
    try:
        import auth
        auth_db = auth.get_db()
        player_ids = set()
        for t in threads:
            player_ids.add(t["player_a"])
            player_ids.add(t["player_b"])
        names = {}
        for pid in player_ids:
            p = auth_db.query(auth.Player).filter(auth.Player.id == pid).first()
            names[pid] = p.business_name if p else f"#{pid}"
        auth_db.close()
        for t in threads:
            t["name_a"] = names.get(t["player_a"], f"#{t['player_a']}")
            t["name_b"] = names.get(t["player_b"], f"#{t['player_b']}")
    except Exception:
        for t in threads:
            t["name_a"] = f"#{t['player_a']}"
            t["name_b"] = f"#{t['player_b']}"

    db.close()
    return threads


def get_dm_thread_admin(player_a: int, player_b: int, limit: int = 100) -> list:
    """Admin: get full DM thread between two players."""
    db = get_db()
    from sqlalchemy import or_, and_
    msgs = db.query(DirectMessage).filter(
        or_(
            and_(DirectMessage.from_id == player_a, DirectMessage.to_id == player_b),
            and_(DirectMessage.from_id == player_b, DirectMessage.to_id == player_a),
        )
    ).order_by(DirectMessage.created_at.desc()).limit(limit).all()

    result = []
    for m in reversed(msgs):
        result.append({
            "id": m.id,
            "from_id": m.from_id,
            "to_id": m.to_id,
            "from_name": m.from_name,
            "content": m.content,
            "created_at": m.created_at.isoformat(),
        })
    db.close()
    return result


# ==========================
# TICK
# ==========================

_tick_counter = 0

async def tick(current_tick, now):
    global _tick_counter
    _tick_counter += 1
    # Cleanup stale avatars every 720 ticks (60 minutes)
    if _tick_counter % 720 == 0:
        cleanup_stale_avatars(60)
