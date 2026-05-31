"""
wiki.py
Wiki media management (YouTube tutorials & audio deep dives).
DB-backed replacement for wiki_media.json — supports categories,
pinning, ordering, and proper HTML sanitization.
"""

import html
import json
import os
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from database import engine, SessionLocal

Base = declarative_base()

WIKI_KINDS = ("video", "audio")
WIKI_CATEGORIES = (
    "getting-started",
    "economy",
    "land",
    "banks",
    "markets",
    "businesses",
    "districts",
    "cities",
    "advanced",
    "reference",
)
CATEGORY_LABELS = {
    "getting-started": "Getting Started",
    "economy":         "Economy",
    "land":            "Land",
    "banks":           "Banks",
    "markets":         "Markets",
    "businesses":      "Businesses",
    "districts":       "Districts",
    "cities":          "Cities & Counties",
    "advanced":        "Advanced",
    "reference":       "Reference",
}

_WIKI_JSON_PATH = os.path.join(os.path.dirname(__file__), "wiki_media.json")


class WikiMedia(Base):
    __tablename__ = "wiki_media"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    youtube_id  = Column(String(20), nullable=False)
    kind        = Column(String(10), nullable=False, default="video")  # video | audio
    title       = Column(String(200), nullable=False)
    description = Column(Text, default="")
    category    = Column(String(40), default="reference")
    sort_order  = Column(Integer, default=0)
    pinned      = Column(Boolean, default=False)
    created_at  = Column(DateTime, default=datetime.utcnow)
    created_by  = Column(Integer, default=0)


def _db():
    return SessionLocal()


def _s(text) -> str:
    """Sanitize user input — strip HTML so descriptions can't inject scripts."""
    return html.escape(str(text or "").strip())


def initialize():
    Base.metadata.create_all(bind=engine)
    _migrate_from_json()
    _seed_land_grant_entry()


def _seed_land_grant_entry():
    db = _db()
    try:
        exists = db.query(WikiMedia).filter(WikiMedia.title == "Federal Development Grant").first()
        if exists:
            return
        max_order = db.query(WikiMedia).count()
        db.add(WikiMedia(
            youtube_id="",
            kind="video",
            title="Federal Development Grant",
            description=(
                "The Federal Development Grant is a monthly competition where players spend 425 trophies "
                "to enter and compete on net worth growth percentage over the event window.\n\n"
                "How it works:\n"
                "1. Pay 425 trophies to enter — this is deducted from your trophy count and affects your rank.\n"
                "2. Your net worth is snapshotted at entry time.\n"
                "3. At month end, all entrants are ranked by how much their net worth grew (%) since they entered.\n"
                "4. Top performers win government-owned land plots, matched to your most common terrain type:\n"
                "   • Platinum (top 1): 20 plots + 100 trophies\n"
                "   • Gold (top 2-4): 15 plots + 50 trophies\n"
                "   • Silver (top 5-11): 13 plots + 25 trophies\n"
                "   • Bronze (top 12-26): 10 plots + 10 trophies\n\n"
                "Strategy tips:\n"
                "• Enter early to maximize the growth window.\n"
                "• Winning 10–20 plots gives you the footprint for a full district.\n"
                "• Plots are government-seized land from bankrupt players — they go to active builders.\n"
                "• Land hoarding tax applies to all plots you own, including granted ones.\n"
                "• Executives with the Land Grant Program perk (VP of County Relations) reduce all taxes by 20%, "
                "lowering the cost of holding many plots after winning."
            ),
            category="land",
            sort_order=max_order,
            pinned=False,
        ))
        db.commit()
        print("[Wiki] Seeded Federal Development Grant entry")
    except Exception as e:
        db.rollback()
        print(f"[Wiki] Seed land grant error: {e}")
    finally:
        db.close()


def _migrate_from_json():
    if not os.path.exists(_WIKI_JSON_PATH):
        return
    db = _db()
    try:
        if db.query(WikiMedia).count() > 0:
            return
        with open(_WIKI_JSON_PATH) as f:
            data = json.load(f)
        order = 0
        for entry in data.get("videos", []):
            db.add(WikiMedia(
                youtube_id=entry.get("youtube_id", ""),
                kind="video",
                title=entry.get("title", ""),
                description=entry.get("description", ""),
                category="reference",
                sort_order=order,
            ))
            order += 1
        for entry in data.get("audio", []):
            db.add(WikiMedia(
                youtube_id=entry.get("youtube_id", ""),
                kind="audio",
                title=entry.get("title", ""),
                description=entry.get("description", ""),
                category="reference",
                sort_order=order,
            ))
            order += 1
        db.commit()
        print(f"[Wiki] Migrated {order} entries from wiki_media.json")
    except Exception as e:
        print(f"[Wiki] Migration error: {e}")
    finally:
        db.close()


def _to_dict(e: WikiMedia) -> dict:
    return {
        "id":          e.id,
        "youtube_id":  e.youtube_id,
        "kind":        e.kind,
        "title":       e.title,
        "description": e.description,
        "category":    e.category or "reference",
        "sort_order":  e.sort_order,
        "pinned":      bool(e.pinned),
        "created_at":  e.created_at.isoformat() if e.created_at else "",
    }


def list_entries(kind: str = None, category: str = None) -> list:
    db = _db()
    try:
        q = db.query(WikiMedia)
        if kind:
            q = q.filter(WikiMedia.kind == kind)
        if category:
            q = q.filter(WikiMedia.category == category)
        q = q.order_by(WikiMedia.pinned.desc(),
                       WikiMedia.sort_order.asc(),
                       WikiMedia.id.asc())
        return [_to_dict(e) for e in q.all()]
    finally:
        db.close()


def add_entry(youtube_id: str, kind: str, title: str, description: str,
              category: str, created_by: int = 0) -> dict:
    db = _db()
    try:
        max_order = db.query(WikiMedia).count()
        entry = WikiMedia(
            youtube_id=youtube_id,
            kind=kind if kind in WIKI_KINDS else "video",
            title=_s(title),
            description=_s(description),
            category=category if category in WIKI_CATEGORIES else "reference",
            sort_order=max_order,
            created_by=created_by,
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return _to_dict(entry)
    finally:
        db.close()


def update_entry(entry_id: int, **kwargs) -> bool:
    db = _db()
    try:
        entry = db.query(WikiMedia).filter(WikiMedia.id == entry_id).first()
        if not entry:
            return False
        if "title" in kwargs:
            entry.title = _s(kwargs["title"])
        if "description" in kwargs:
            entry.description = _s(kwargs["description"])
        if "category" in kwargs and kwargs["category"] in WIKI_CATEGORIES:
            entry.category = kwargs["category"]
        if "pinned" in kwargs:
            entry.pinned = bool(kwargs["pinned"])
        if "sort_order" in kwargs:
            entry.sort_order = int(kwargs["sort_order"])
        db.commit()
        return True
    finally:
        db.close()


def delete_entry(entry_id: int) -> bool:
    db = _db()
    try:
        entry = db.query(WikiMedia).filter(WikiMedia.id == entry_id).first()
        if not entry:
            return False
        db.delete(entry)
        db.commit()
        return True
    finally:
        db.close()


def move_entry(entry_id: int, direction: int):
    """Move entry up (-1) or down (+1) within its kind's sort order."""
    db = _db()
    try:
        entry = db.query(WikiMedia).filter(WikiMedia.id == entry_id).first()
        if not entry:
            return
        entries = (db.query(WikiMedia)
                   .filter(WikiMedia.kind == entry.kind)
                   .order_by(WikiMedia.pinned.desc(),
                             WikiMedia.sort_order.asc(),
                             WikiMedia.id.asc())
                   .all())
        idx = next((i for i, e in enumerate(entries) if e.id == entry_id), None)
        if idx is None:
            return
        swap_idx = idx + direction
        if 0 <= swap_idx < len(entries):
            entries[idx].sort_order, entries[swap_idx].sort_order = (
                entries[swap_idx].sort_order, entries[idx].sort_order
            )
            db.commit()
    finally:
        db.close()
