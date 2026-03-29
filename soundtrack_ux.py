"""
soundtrack_ux.py — Soundtrack routes.

Public:
  GET /soundtrack/list          — JSON list of active tracks (used by JS player)

Admin (requires admin session):
  GET  /admin/soundtrack        — manage uploads
  POST /admin/soundtrack/upload      — upload single audio file (custom title)
  POST /admin/soundtrack/bulk_upload — upload multiple audio files at once
  POST /admin/soundtrack/toggle — toggle track active/inactive
  POST /admin/soundtrack/rename — rename a track
  POST /admin/soundtrack/delete — delete track + file
"""

import os
import re
from typing import List, Optional

from fastapi import APIRouter, Cookie, Form, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from starlette.concurrency import run_in_threadpool

router = APIRouter()

ALLOWED_AUDIO_EXTS = {".mp3", ".ogg", ".wav", ".flac", ".m4a", ".aac"}
MAX_FILE_MB = 50

# Shared temp directory for chunked uploads (same as wcpr)
_CHUNK_DIR = os.path.join(os.path.dirname(__file__), "_upload_chunks")


# ──────────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def _admin_guard(session_token):
    from admins import require_admin
    player = require_admin(session_token)
    if not player:
        return None, RedirectResponse(url="/login", status_code=303)
    return player, None


def _safe_filename(name: str) -> str:
    """Sanitize uploaded filename."""
    name = os.path.basename(name)
    name = re.sub(r"[^A-Za-z0-9._\- ]", "_", name)
    return name[:120]


# ──────────────────────────────────────────────────────────────────────────────
# PUBLIC — track list for JS player
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/soundtrack/list")
def soundtrack_list():
    """Return JSON array of active tracks. Consumed by the in-page audio player."""
    from soundtrack import get_tracks
    tracks = get_tracks(active_only=True)
    return JSONResponse([
        {"id": t["id"], "title": t["title"], "url": f"/static/soundtrack/{t['filename']}"}
        for t in tracks
    ])


# ──────────────────────────────────────────────────────────────────────────────
# ADMIN — manage tracks
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/admin/soundtrack", response_class=HTMLResponse)
def admin_soundtrack_page(
    session_token: Optional[str] = Cookie(None),
    msg: str = "",
    err: str = "",
):
    player, redirect = _admin_guard(session_token)
    if redirect:
        return redirect

    from soundtrack import get_tracks
    tracks = get_tracks()

    banner = ""
    if msg:
        banner = f'<div style="padding:10px 16px;background:#052e16;border:1px solid #16a34a;color:#4ade80;margin-bottom:16px;">{msg}</div>'
    elif err:
        banner = f'<div style="padding:10px 16px;background:#1a0505;border:1px solid #dc2626;color:#f87171;margin-bottom:16px;">{err}</div>'

    # Build track rows
    if tracks:
        rows = ""
        for t in tracks:
            active_color = "#22c55e" if t.get("is_active", True) else "#64748b"
            active_label = "Active" if t.get("is_active", True) else "Hidden"
            safe_title = t["title"].replace('"', '&quot;').replace("'", "&#39;")
            rows += f'''
            <tr style="border-bottom:1px solid #0f172a;">
                <td style="padding:10px 8px;color:#e5e7eb;">
                    <span id="title-text-{t["id"]}">{t["title"]}</span>
                    <button onclick="gsRenameToggle({t["id"]})" title="Rename"
                            style="background:none;border:none;color:#64748b;cursor:pointer;font-size:0.8rem;padding:0 4px;vertical-align:middle;">✏️</button>
                    <form id="rename-form-{t["id"]}" action="/admin/soundtrack/rename" method="post"
                          style="display:none;margin-top:6px;display:none;">
                        <input type="hidden" name="track_id" value="{t["id"]}">
                        <input type="text" name="title" value="{safe_title}" required maxlength="120"
                               style="background:#020617;border:1px solid #334155;color:#e5e7eb;padding:4px 6px;font-size:0.8rem;width:160px;box-sizing:border-box;">
                        <button type="submit"
                                style="background:#0c4a6e;border:1px solid #0284c7;color:#7dd3fc;padding:3px 8px;font-size:0.75rem;cursor:pointer;border-radius:3px;margin-left:4px;">Save</button>
                        <button type="button" onclick="gsRenameToggle({t["id"]})"
                                style="background:#1e293b;border:1px solid #334155;color:#94a3b8;padding:3px 8px;font-size:0.75rem;cursor:pointer;border-radius:3px;margin-left:2px;">Cancel</button>
                    </form>
                </td>
                <td style="padding:10px 8px;color:#64748b;font-size:0.8rem;">{t["filename"]}</td>
                <td style="padding:10px 8px;">
                    <audio controls preload="none" style="height:28px;width:180px;">
                        <source src="/static/soundtrack/{t["filename"]}">
                    </audio>
                </td>
                <td style="padding:10px 8px;text-align:center;">
                    <span style="color:{active_color};font-size:0.8rem;">{active_label}</span>
                </td>
                <td style="padding:10px 8px;text-align:right;">
                    <form action="/admin/soundtrack/toggle" method="post" style="display:inline;">
                        <input type="hidden" name="track_id" value="{t["id"]}">
                        <button style="background:#1e293b;border:1px solid #334155;color:#94a3b8;padding:4px 10px;font-size:0.75rem;cursor:pointer;border-radius:3px;margin-right:4px;">
                            {"Disable" if t.get("is_active", True) else "Enable"}
                        </button>
                    </form>
                    <form action="/admin/soundtrack/delete" method="post" style="display:inline;"
                          onsubmit="return confirm('Delete \"{t["title"]}\"? This cannot be undone.')">
                        <input type="hidden" name="track_id" value="{t["id"]}">
                        <button style="background:#1a0505;border:1px solid #dc2626;color:#f87171;padding:4px 10px;font-size:0.75rem;cursor:pointer;border-radius:3px;">
                            Delete
                        </button>
                    </form>
                </td>
            </tr>'''
        track_table = f'''
        <table style="width:100%;border-collapse:collapse;">
            <thead>
                <tr style="border-bottom:1px solid #1e293b;color:#64748b;font-size:0.75rem;">
                    <th style="padding:8px;text-align:left;">Title</th>
                    <th style="padding:8px;text-align:left;">Filename</th>
                    <th style="padding:8px;text-align:left;">Preview</th>
                    <th style="padding:8px;text-align:center;">Status</th>
                    <th style="padding:8px;text-align:right;">Actions</th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>'''
    else:
        track_table = '<p style="color:#64748b;padding:20px 0;">No tracks uploaded yet.</p>'

    html = f'''
    <a href="/admin" style="color:#38bdf8;">&larr; Admin Dashboard</a>
    <h1 style="margin:8px 0 4px 0;">🎵 WLOL — Music Playlist Manager</h1>
    <p style="color:#64748b;margin-bottom:20px;">
        Upload MP3/OGG/WAV music tracks (max {MAX_FILE_MB} MB each). Active tracks shuffle on WLOL in the in-game radio player.
    </p>
    {banner}

    <!-- Upload Form -->
    <div class="card" style="margin-bottom:20px;">
        <h3 style="margin:0 0 14px 0;">Upload Track</h3>
        <form id="st-upload-form" style="display:flex;flex-wrap:wrap;gap:12px;align-items:flex-end;">
            <div style="flex:1;min-width:200px;">
                <label style="font-size:0.75rem;color:#64748b;display:block;margin-bottom:4px;">Track Title *</label>
                <input type="text" name="title" required placeholder="e.g. Main Theme"
                       style="width:100%;background:#020617;border:1px solid #334155;color:#e5e7eb;padding:8px;box-sizing:border-box;">
            </div>
            <div style="flex:1;min-width:200px;">
                <label style="font-size:0.75rem;color:#64748b;display:block;margin-bottom:4px;">Audio File * (MP3/OGG/WAV/FLAC/M4A/AAC)</label>
                <input type="file" name="file" required accept="audio/*" id="st-file-input"
                       style="width:100%;background:#020617;border:1px solid #334155;color:#e5e7eb;padding:7px;box-sizing:border-box;">
            </div>
            <div style="flex-shrink:0;">
                <button type="submit" id="st-upload-btn" class="btn-blue" style="padding:9px 20px;">Upload Track</button>
            </div>
        </form>
        <div id="st-upload-status" style="display:none;margin-top:12px;">
            <div id="st-upload-text" style="font-size:0.8rem;color:#94a3b8;margin-bottom:6px;">Starting upload...</div>
            <div style="background:#0f172a;border:1px solid #1e293b;border-radius:4px;height:8px;overflow:hidden;">
                <div id="st-upload-bar" style="background:#38bdf8;height:100%;width:0%;transition:width 0.15s;"></div>
            </div>
        </div>
    </div>

    <!-- Bulk Upload -->
    <div class="card" style="margin-bottom:20px;">
        <h3 style="margin:0 0 6px 0;">Bulk Upload</h3>
        <p style="color:#64748b;font-size:0.8rem;margin:0 0 12px 0;">
            Select multiple files at once. Titles are auto-generated from filenames and can be renamed after upload.
        </p>
        <form id="bulk-form" action="/admin/soundtrack/bulk_upload" method="post" enctype="multipart/form-data">
            <div style="margin-bottom:10px;">
                <label style="font-size:0.75rem;color:#64748b;display:block;margin-bottom:4px;">Audio Files * (MP3/OGG/WAV/FLAC/M4A/AAC, max {MAX_FILE_MB} MB each)</label>
                <input type="file" name="files" multiple required accept="audio/*" id="bulk-input"
                       style="width:100%;background:#020617;border:1px solid #334155;color:#e5e7eb;padding:7px;box-sizing:border-box;">
            </div>
            <div id="bulk-preview" style="margin-bottom:10px;display:none;">
                <p style="font-size:0.75rem;color:#64748b;margin:0 0 6px 0;">Files to upload:</p>
                <ul id="bulk-list" style="margin:0;padding-left:18px;color:#94a3b8;font-size:0.8rem;"></ul>
            </div>
            <button type="submit" class="btn-blue" style="padding:9px 20px;">Upload All</button>
        </form>
    </div>
    <script>
    // ── Single upload — chunked to avoid Cloudflare 524 timeouts ─────────
    (function() {{
        var CHUNK_SIZE = 5 * 1024 * 1024;
        var form      = document.getElementById('st-upload-form');
        var btn       = document.getElementById('st-upload-btn');
        var statusDiv = document.getElementById('st-upload-status');
        var statusTxt = document.getElementById('st-upload-text');
        var bar       = document.getElementById('st-upload-bar');

        function randomId() {{
            if (typeof crypto !== 'undefined' && crypto.randomUUID) return crypto.randomUUID();
            return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {{
                var r = Math.random() * 16 | 0;
                return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);
            }});
        }}

        form.addEventListener('submit', function(e) {{
            e.preventDefault();
            var titleInput = form.querySelector('input[name="title"]');
            var fileInput  = document.getElementById('st-file-input');
            if (!titleInput.value.trim()) {{ titleInput.focus(); return; }}
            if (!fileInput.files.length)  {{ fileInput.focus();  return; }}

            var file        = fileInput.files[0];
            var title       = titleInput.value.trim();
            var totalChunks = Math.max(1, Math.ceil(file.size / CHUNK_SIZE));
            var uploadId    = randomId();

            btn.disabled = true;
            btn.textContent = 'Uploading\u2026';
            statusDiv.style.display = 'block';
            bar.style.width = '0%';
            statusTxt.textContent = 'Starting upload\u2026';

            function sendChunk(index) {{
                var start = index * CHUNK_SIZE;
                var slice = file.slice(start, start + CHUNK_SIZE);
                var fd    = new FormData();
                fd.append('upload_id',    uploadId);
                fd.append('chunk_index',  index);
                fd.append('total_chunks', totalChunks);
                fd.append('total_size',   file.size);
                fd.append('filename',     file.name);
                fd.append('title',        title);
                fd.append('chunk',        slice, file.name);

                var xhr = new XMLHttpRequest();
                xhr.upload.addEventListener('progress', function(ev) {{
                    if (ev.lengthComputable) {{
                        var overall = ((index + ev.loaded / ev.total) / totalChunks * 100).toFixed(0);
                        var doneMB  = ((index * CHUNK_SIZE + ev.loaded) / 1048576).toFixed(1);
                        var totalMB = (file.size / 1048576).toFixed(1);
                        bar.style.width = overall + '%';
                        statusTxt.textContent = 'Uploading\u2026 ' + overall + '% (' + doneMB + '\u202f/\u202f' + totalMB + ' MB)';
                    }}
                }});
                xhr.addEventListener('load', function() {{
                    var resp;
                    try {{ resp = JSON.parse(xhr.responseText); }} catch(ex) {{}}
                    if (!resp || !resp.ok) {{
                        var err = (resp && resp.error) || ('Server error ' + xhr.status);
                        window.location.href = '/admin/soundtrack?err=' + encodeURIComponent(err);
                        return;
                    }}
                    if (resp.done) {{
                        bar.style.width = '100%';
                        window.location.href = '/admin/soundtrack?msg=' + encodeURIComponent('Uploaded: ' + resp.title);
                    }} else {{
                        sendChunk(index + 1);
                    }}
                }});
                xhr.addEventListener('error', function() {{
                    btn.disabled = false;
                    btn.textContent = 'Upload Track';
                    statusDiv.style.display = 'none';
                    alert('Upload failed \u2014 please check your connection and try again.');
                }});
                xhr.open('POST', '/admin/soundtrack/upload/chunk');
                xhr.send(fd);
            }}

            sendChunk(0);
        }});
    }})();

    // ── Bulk file preview ─────────────────────────────────────────────────
    document.getElementById('bulk-input').addEventListener('change', function() {{
        var list = document.getElementById('bulk-list');
        var preview = document.getElementById('bulk-preview');
        list.innerHTML = '';
        if (this.files.length) {{
            Array.from(this.files).forEach(function(f) {{
                var li = document.createElement('li');
                li.textContent = f.name + ' (' + (f.size / 1048576).toFixed(1) + ' MB)';
                list.appendChild(li);
            }});
            preview.style.display = 'block';
        }} else {{
            preview.style.display = 'none';
        }}
    }});
    </script>

    <!-- Track List -->
    <div class="card">
        <h3 style="margin:0 0 14px 0;">Uploaded Tracks ({len(tracks)})</h3>
        {track_table}
    </div>
    <script>
    function gsRenameToggle(id) {{
        var form = document.getElementById('rename-form-' + id);
        form.style.display = form.style.display === 'none' ? 'block' : 'none';
    }}
    </script>

    <p style="color:#475569;font-size:0.75rem;margin-top:16px;">
        WLOL shuffles active tracks automatically. Players can adjust volume, enable/disable individual tracks,
        and tune between WLOL and WCPR via the Audio tab in Settings.
    </p>
    '''

    from admins_ux import admin_shell
    return HTMLResponse(admin_shell("WLOL Music Manager", html, player.business_name))


@router.post("/admin/soundtrack/upload")
async def admin_soundtrack_upload(
    session_token: Optional[str] = Cookie(None),
    title: str = Form(...),
    file: UploadFile = File(...),
):
    player, redirect = await run_in_threadpool(_admin_guard, session_token)
    if redirect:
        return redirect

    # Validate extension
    _, ext = os.path.splitext(file.filename or "")
    ext = ext.lower()
    if ext not in ALLOWED_AUDIO_EXTS:
        from urllib.parse import quote
        return RedirectResponse(
            f"/admin/soundtrack?err={quote(f'Unsupported file type: {ext}. Use MP3, OGG, WAV, FLAC, M4A, or AAC.')}",
            status_code=303,
        )

    # Read & size-check
    data = await file.read()
    if len(data) > MAX_FILE_MB * 1024 * 1024:
        from urllib.parse import quote
        return RedirectResponse(
            f"/admin/soundtrack?err={quote(f'File too large (max {MAX_FILE_MB} MB).')}",
            status_code=303,
        )

    # Save file (blocking I/O offloaded to thread)
    from soundtrack import SOUNDTRACK_DIR, add_track
    clean_title = title.strip()[:120]
    _fname = file.filename or f"track{ext}"
    _data = data

    def _write_and_register():
        import time
        os.makedirs(SOUNDTRACK_DIR, exist_ok=True)
        sname = _safe_filename(_fname)
        dest = os.path.join(SOUNDTRACK_DIR, sname)
        if os.path.exists(dest):
            base, e = os.path.splitext(sname)
            sname = f"{base}_{int(time.time())}{e}"
            dest = os.path.join(SOUNDTRACK_DIR, sname)
        with open(dest, "wb") as f_out:
            f_out.write(_data)
        return add_track(sname, clean_title)

    track = await run_in_threadpool(_write_and_register)
    from urllib.parse import quote
    msg = quote(f"Uploaded: {track['title']}")
    return RedirectResponse(f"/admin/soundtrack?msg={msg}", status_code=303)


@router.post("/admin/soundtrack/upload/chunk")
async def admin_soundtrack_upload_chunk(
    session_token: Optional[str] = Cookie(None),
    upload_id: str = Form(...),
    chunk_index: int = Form(...),
    total_chunks: int = Form(...),
    total_size: int = Form(...),
    filename: str = Form(...),
    title: str = Form(...),
    chunk: UploadFile = File(...),
):
    player, redirect = await run_in_threadpool(_admin_guard, session_token)
    if redirect:
        return JSONResponse({"ok": False, "error": "Not authorized"}, status_code=401)

    if not re.match(r'^[a-f0-9\-]{36}$', upload_id):
        return JSONResponse({"ok": False, "error": "Invalid upload ID"}, status_code=400)

    _, ext = os.path.splitext(filename or "")
    ext = ext.lower()
    if ext not in ALLOWED_AUDIO_EXTS:
        return JSONResponse({"ok": False, "error": f"Unsupported file type: {ext}"}, status_code=400)

    if total_size > MAX_FILE_MB * 1024 * 1024:
        return JSONResponse({"ok": False, "error": f"File too large (max {MAX_FILE_MB} MB)."}, status_code=400)

    if not (0 <= chunk_index < total_chunks >= 1):
        return JSONResponse({"ok": False, "error": "Invalid chunk parameters"}, status_code=400)

    chunk_data = await chunk.read()

    def _process_chunk():
        import shutil, time
        chunk_dir = os.path.join(_CHUNK_DIR, upload_id)
        os.makedirs(chunk_dir, exist_ok=True)
        with open(os.path.join(chunk_dir, f"{chunk_index:06d}"), "wb") as f:
            f.write(chunk_data)

        present = os.listdir(chunk_dir)
        if len(present) < total_chunks:
            return None

        from soundtrack import SOUNDTRACK_DIR, add_track
        os.makedirs(SOUNDTRACK_DIR, exist_ok=True)
        safe_name = _safe_filename(filename)
        dest = os.path.join(SOUNDTRACK_DIR, safe_name)
        if os.path.exists(dest):
            base, e = os.path.splitext(safe_name)
            safe_name = f"{base}_{int(time.time())}{e}"
            dest = os.path.join(SOUNDTRACK_DIR, safe_name)

        with open(dest, "wb") as f_out:
            for c in sorted(present):
                with open(os.path.join(chunk_dir, c), "rb") as f_in:
                    f_out.write(f_in.read())

        shutil.rmtree(chunk_dir, ignore_errors=True)
        clean_title = title.strip()[:120] or _title_from_filename(filename)
        return add_track(safe_name, clean_title)

    try:
        track = await run_in_threadpool(_process_chunk)
    except Exception as exc:
        import traceback
        traceback.print_exc()
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)

    if track is None:
        return JSONResponse({"ok": True, "done": False})
    return JSONResponse({"ok": True, "done": True, "title": track["title"]})


def _title_from_filename(filename: str) -> str:
    """Derive a human-readable title from an audio filename."""
    base, _ = os.path.splitext(os.path.basename(filename))
    # Replace separators with spaces, collapse runs, title-case
    title = re.sub(r"[_\-]+", " ", base).strip()
    title = re.sub(r"\s+", " ", title)
    return title.title()[:120] or "Untitled"


@router.post("/admin/soundtrack/bulk_upload")
async def admin_soundtrack_bulk_upload(
    session_token: Optional[str] = Cookie(None),
    files: List[UploadFile] = File(...),
):
    player, redirect = _admin_guard(session_token)
    if redirect:
        return redirect

    from soundtrack import SOUNDTRACK_DIR, add_track
    import time as _time
    from urllib.parse import quote

    os.makedirs(SOUNDTRACK_DIR, exist_ok=True)
    uploaded, skipped = [], []

    for file in files:
        _, ext = os.path.splitext(file.filename or "")
        ext = ext.lower()
        if ext not in ALLOWED_AUDIO_EXTS:
            skipped.append(f"{file.filename} (unsupported type)")
            continue

        data = await file.read()
        if len(data) > MAX_FILE_MB * 1024 * 1024:
            skipped.append(f"{file.filename} (too large)")
            continue

        safe_name = _safe_filename(file.filename or f"track{ext}")
        dest = os.path.join(SOUNDTRACK_DIR, safe_name)
        if os.path.exists(dest):
            base, e = os.path.splitext(safe_name)
            safe_name = f"{base}_{int(_time.time())}{e}"
            dest = os.path.join(SOUNDTRACK_DIR, safe_name)

        with open(dest, "wb") as f_out:
            f_out.write(data)

        title = _title_from_filename(file.filename or safe_name)
        add_track(safe_name, title)
        uploaded.append(title)

    parts = []
    if uploaded:
        parts.append(f"{len(uploaded)} track(s) uploaded")
    if skipped:
        parts.append(f"{len(skipped)} skipped: {', '.join(skipped)}")

    if not parts:
        return RedirectResponse("/admin/soundtrack?err=No+valid+files+selected", status_code=303)

    if skipped:
        return RedirectResponse(f"/admin/soundtrack?err={quote('; '.join(parts))}", status_code=303)
    return RedirectResponse(f"/admin/soundtrack?msg={quote('; '.join(parts))}", status_code=303)


@router.post("/admin/soundtrack/toggle")
def admin_soundtrack_toggle(
    session_token: Optional[str] = Cookie(None),
    track_id: int = Form(...),
):
    player, redirect = _admin_guard(session_token)
    if redirect:
        return redirect
    from soundtrack import get_tracks, set_active
    tracks = get_tracks()
    target = next((t for t in tracks if t["id"] == track_id), None)
    if target:
        new_state = not target.get("is_active", True)
        set_active(track_id, new_state)
    return RedirectResponse("/admin/soundtrack?msg=Updated", status_code=303)


@router.post("/admin/soundtrack/rename")
def admin_soundtrack_rename(
    session_token: Optional[str] = Cookie(None),
    track_id: int = Form(...),
    title: str = Form(...),
):
    player, redirect = _admin_guard(session_token)
    if redirect:
        return redirect
    new_title = title.strip()[:120]
    if not new_title:
        return RedirectResponse("/admin/soundtrack?err=Title+cannot+be+empty", status_code=303)
    from soundtrack import rename_track
    from urllib.parse import quote
    if rename_track(track_id, new_title):
        return RedirectResponse(f"/admin/soundtrack?msg={quote(f'Renamed to: {new_title}')}", status_code=303)
    return RedirectResponse("/admin/soundtrack?err=Track+not+found", status_code=303)


@router.post("/admin/soundtrack/delete")
def admin_soundtrack_delete(
    session_token: Optional[str] = Cookie(None),
    track_id: int = Form(...),
):
    player, redirect = _admin_guard(session_token)
    if redirect:
        return redirect
    from soundtrack import delete_track, get_tracks
    tracks = get_tracks()
    target = next((t for t in tracks if t["id"] == track_id), None)
    if target:
        delete_track(track_id)
        from urllib.parse import quote
        msg = quote(f"Deleted: {target['title']}")
        return RedirectResponse(f"/admin/soundtrack?msg={msg}", status_code=303)
    return RedirectResponse("/admin/soundtrack?err=Track+not+found", status_code=303)
