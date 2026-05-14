"""
maph_matt.py — MAPH (CH 46) and MATT (CH 28) video channel management.

MAPH  = Markets, Analytics & Player Help    — tutorial/official content  (CH 46)
MATT  = Market Action Trading Theater       — community player content   (CH 28)

Playlists are JSON-backed (same pattern as soundtrack.py / wcpr.py).
Each entry is a YouTube video ID + title + active flag + order.

Player submissions flow: player submits → pending → admin approves → MATT playlist.
"""

import os
import json
from typing import List, Dict, Optional
from datetime import datetime

_BASE = os.path.dirname(__file__)
_MAPH_JSON   = os.path.join(_BASE, "maph_tracks.json")
_MATT_JSON   = os.path.join(_BASE, "matt_tracks.json")
_SUBS_JSON   = os.path.join(_BASE, "matt_submissions.json")


# ── helpers ───────────────────────────────────────────────────────────────────

def _load(path: str) -> List[Dict]:
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return []


def _save(path: str, data: List[Dict]) -> None:
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def extract_youtube_id(url_or_id: str) -> Optional[str]:
    """Extract YouTube video ID from a URL or return it as-is if already an ID."""
    import re
    url = url_or_id.strip()
    patterns = [
        r'youtu\.be/([A-Za-z0-9_-]{11})',
        r'youtube\.com/watch\?.*v=([A-Za-z0-9_-]{11})',
        r'youtube\.com/embed/([A-Za-z0-9_-]{11})',
        r'youtube\.com/v/([A-Za-z0-9_-]{11})',
        r'youtube\.com/shorts/([A-Za-z0-9_-]{11})',
    ]
    for pat in patterns:
        m = re.search(pat, url)
        if m:
            return m.group(1)
    if re.fullmatch(r'[A-Za-z0-9_-]{11}', url):
        return url
    return None


# ── MAPH playlist (CH 46) ─────────────────────────────────────────────────────

def maph_get(active_only: bool = False) -> List[Dict]:
    tracks = _load(_MAPH_JSON)
    if active_only:
        return [t for t in tracks if t.get("is_active", True)]
    return tracks


def maph_add(youtube_id: str, title: str) -> Dict:
    tracks = _load(_MAPH_JSON)
    next_id = max((t["id"] for t in tracks), default=0) + 1
    entry = {"id": next_id, "youtube_id": youtube_id, "title": title,
             "is_active": True, "order": len(tracks)}
    tracks.append(entry)
    _save(_MAPH_JSON, tracks)
    return entry


def maph_toggle(entry_id: int, active: bool) -> bool:
    tracks = _load(_MAPH_JSON)
    for t in tracks:
        if t["id"] == entry_id:
            t["is_active"] = active
            _save(_MAPH_JSON, tracks)
            return True
    return False


def maph_delete(entry_id: int) -> bool:
    tracks = _load(_MAPH_JSON)
    new = [t for t in tracks if t["id"] != entry_id]
    if len(new) == len(tracks):
        return False
    _save(_MAPH_JSON, new)
    return True


def maph_rename(entry_id: int, title: str) -> bool:
    tracks = _load(_MAPH_JSON)
    for t in tracks:
        if t["id"] == entry_id:
            t["title"] = title
            _save(_MAPH_JSON, tracks)
            return True
    return False


def maph_reorder(ordered_ids: List[int]) -> None:
    tracks = _load(_MAPH_JSON)
    id_map = {t["id"]: t for t in tracks}
    reordered = []
    for i, tid in enumerate(ordered_ids):
        if tid in id_map:
            id_map[tid]["order"] = i
            reordered.append(id_map[tid])
    seen = set(ordered_ids)
    for t in tracks:
        if t["id"] not in seen:
            reordered.append(t)
    _save(_MAPH_JSON, reordered)


# ── MATT playlist (CH 28) ─────────────────────────────────────────────────────

def matt_get(active_only: bool = False) -> List[Dict]:
    tracks = _load(_MATT_JSON)
    if active_only:
        return [t for t in tracks if t.get("is_active", True)]
    return tracks


def matt_add(youtube_id: str, title: str, submitter: str = "") -> Dict:
    tracks = _load(_MATT_JSON)
    next_id = max((t["id"] for t in tracks), default=0) + 1
    entry = {"id": next_id, "youtube_id": youtube_id, "title": title,
             "submitter": submitter, "is_active": True, "order": len(tracks)}
    tracks.append(entry)
    _save(_MATT_JSON, tracks)
    return entry


def matt_toggle(entry_id: int, active: bool) -> bool:
    tracks = _load(_MATT_JSON)
    for t in tracks:
        if t["id"] == entry_id:
            t["is_active"] = active
            _save(_MATT_JSON, tracks)
            return True
    return False


def matt_delete(entry_id: int) -> bool:
    tracks = _load(_MATT_JSON)
    new = [t for t in tracks if t["id"] != entry_id]
    if len(new) == len(tracks):
        return False
    _save(_MATT_JSON, new)
    return True


def matt_rename(entry_id: int, title: str) -> bool:
    tracks = _load(_MATT_JSON)
    for t in tracks:
        if t["id"] == entry_id:
            t["title"] = title
            _save(_MATT_JSON, tracks)
            return True
    return False


def matt_reorder(ordered_ids: List[int]) -> None:
    tracks = _load(_MATT_JSON)
    id_map = {t["id"]: t for t in tracks}
    reordered = []
    for i, tid in enumerate(ordered_ids):
        if tid in id_map:
            id_map[tid]["order"] = i
            reordered.append(id_map[tid])
    seen = set(ordered_ids)
    for t in tracks:
        if t["id"] not in seen:
            reordered.append(t)
    _save(_MATT_JSON, reordered)


# ── Player submissions ────────────────────────────────────────────────────────

def sub_list(status: Optional[str] = None) -> List[Dict]:
    subs = _load(_SUBS_JSON)
    if status:
        return [s for s in subs if s.get("status") == status]
    return subs


def sub_add(player_id: int, player_name: str, youtube_id: str,
            title: str, note: str = "") -> Dict:
    subs = _load(_SUBS_JSON)
    next_id = max((s["id"] for s in subs), default=0) + 1
    sub = {
        "id":           next_id,
        "player_id":    player_id,
        "player_name":  player_name,
        "youtube_id":   youtube_id,
        "title":        title,
        "note":         note,
        "submitted_at": datetime.utcnow().isoformat(),
        "status":       "pending",
        "admin_note":   "",
    }
    subs.append(sub)
    _save(_SUBS_JSON, subs)
    return sub


def sub_review(sub_id: int, action: str, admin_note: str = "") -> bool:
    """action: 'approve' or 'reject'. Approve also adds to MATT playlist."""
    subs = _load(_SUBS_JSON)
    for s in subs:
        if s["id"] == sub_id:
            if action == "approve":
                s["status"] = "approved"
                matt_add(s["youtube_id"], s["title"], submitter=s["player_name"])
            elif action == "reject":
                s["status"] = "rejected"
            s["admin_note"] = admin_note
            _save(_SUBS_JSON, subs)
            return True
    return False


def sub_delete(sub_id: int) -> bool:
    subs = _load(_SUBS_JSON)
    new = [s for s in subs if s["id"] != sub_id]
    if len(new) == len(subs):
        return False
    _save(_SUBS_JSON, new)
    return True
