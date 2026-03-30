"""
wcpr.py — WCPR talk radio track management.

Tracks are uploaded as MP3/OGG/WAV files and stored in static/wcpr/.
Metadata is persisted in wcpr_tracks.json.
"""

import os
import json
from typing import List, Dict

_WCPR_JSON = os.path.join(os.path.dirname(__file__), "wcpr_tracks.json")
WCPR_DIR   = os.path.join(os.path.dirname(__file__), "static", "wcpr")


# ─────────────────────────────────────────────────────────────────────────────
# JSON PERSISTENCE
# ─────────────────────────────────────────────────────────────────────────────

def _load() -> List[Dict]:
    try:
        with open(_WCPR_JSON) as f:
            return json.load(f)
    except Exception:
        return []


def _save(tracks: List[Dict]) -> None:
    with open(_WCPR_JSON, "w") as f:
        json.dump(tracks, f, indent=2)


# ─────────────────────────────────────────────────────────────────────────────
# CRUD
# ─────────────────────────────────────────────────────────────────────────────

def get_tracks(active_only: bool = False) -> List[Dict]:
    tracks = _load()
    if active_only:
        return [t for t in tracks if t.get("is_active", True)]
    return tracks


def add_track(filename: str, title: str) -> Dict:
    tracks = _load()
    next_id = max((t["id"] for t in tracks), default=0) + 1
    track = {
        "id":        next_id,
        "filename":  filename,
        "title":     title,
        "is_active": True,
        "order":     len(tracks),
    }
    tracks.append(track)
    _save(tracks)
    return track


def set_active(track_id: int, active: bool) -> bool:
    tracks = _load()
    for t in tracks:
        if t["id"] == track_id:
            t["is_active"] = active
            _save(tracks)
            return True
    return False


def delete_track(track_id: int) -> bool:
    tracks = _load()
    target = next((t for t in tracks if t["id"] == track_id), None)
    if not target:
        return False
    tracks = [t for t in tracks if t["id"] != track_id]
    _save(tracks)
    path = os.path.join(WCPR_DIR, target["filename"])
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass
    return True


def rename_track(track_id: int, new_title: str) -> bool:
    tracks = _load()
    for t in tracks:
        if t["id"] == track_id:
            t["title"] = new_title
            _save(tracks)
            return True
    return False


# ─────────────────────────────────────────────────────────────────────────────
# INIT
# ─────────────────────────────────────────────────────────────────────────────

def initialize():
    os.makedirs(WCPR_DIR, exist_ok=True)
    if not os.path.exists(_WCPR_JSON):
        _save([])
    print("[WCPR] Module initialized")
