"""
soundtrack.py — Game soundtrack management.

Tracks are uploaded as MP3/OGG/WAV files and stored in static/soundtrack/.
Metadata is persisted in soundtrack.json (same pattern as wiki_media.json).
"""

import os
import json
from typing import List, Dict, Optional

_SOUNDTRACK_JSON = os.path.join(os.path.dirname(__file__), "soundtrack.json")
SOUNDTRACK_DIR   = os.path.join(os.path.dirname(__file__), "static", "soundtrack")


# ──────────────────────────────────────────────────────────────────────────────
# JSON PERSISTENCE
# ──────────────────────────────────────────────────────────────────────────────

def _load() -> List[Dict]:
    try:
        with open(_SOUNDTRACK_JSON) as f:
            return json.load(f)
    except Exception:
        return []


def _save(tracks: List[Dict]) -> None:
    with open(_SOUNDTRACK_JSON, "w") as f:
        json.dump(tracks, f, indent=2)


# ──────────────────────────────────────────────────────────────────────────────
# CRUD
# ──────────────────────────────────────────────────────────────────────────────

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
    path = os.path.join(SOUNDTRACK_DIR, target["filename"])
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass
    return True


def reorder_tracks(ordered_ids: List[int]) -> None:
    tracks = _load()
    id_map = {t["id"]: t for t in tracks}
    reordered = []
    for i, tid in enumerate(ordered_ids):
        if tid in id_map:
            id_map[tid]["order"] = i
            reordered.append(id_map[tid])
    # append any not in ordered_ids
    included = set(ordered_ids)
    for t in tracks:
        if t["id"] not in included:
            reordered.append(t)
    _save(reordered)


# ──────────────────────────────────────────────────────────────────────────────
# INIT
# ──────────────────────────────────────────────────────────────────────────────

def initialize():
    os.makedirs(SOUNDTRACK_DIR, exist_ok=True)
    if not os.path.exists(_SOUNDTRACK_JSON):
        _save([])
    print("[Soundtrack] Module initialized")
