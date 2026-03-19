"""
wcpr_ux.py — WCPR 104.1 Talk Radio routes.

Public:
  GET /wcpr/list               — JSON list of active talk radio tracks

Admin (requires admin session):
  GET  /admin/wcpr             — manage WCPR uploads
  POST /admin/wcpr/upload      — upload single audio file (custom title)
  POST /admin/wcpr/bulk_upload — upload multiple audio files at once
  POST /admin/wcpr/toggle      — toggle track active/inactive
  POST /admin/wcpr/rename      — rename a track
  POST /admin/wcpr/delete      — delete track + file
"""

import os
import re
from typing import List, Optional

from fastapi import APIRouter, Cookie, Form, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse

router = APIRouter()

ALLOWED_AUDIO_EXTS = {".mp3", ".ogg", ".wav", ".flac", ".m4a", ".aac"}
MAX_FILE_MB = 200  # talk radio episodes can be larger


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _admin_guard(session_token):
    from admins import require_admin
    player = require_admin(session_token)
    if not player:
        return None, RedirectResponse(url="/login", status_code=303)
    return player, None


def _safe_filename(name: str) -> str:
    name = os.path.basename(name)
    name = re.sub(r"[^A-Za-z0-9._\- ]", "_", name)
    return name[:120]


def _title_from_filename(filename: str) -> str:
    base, _ = os.path.splitext(os.path.basename(filename))
    title = re.sub(r"[_\-]+", " ", base).strip()
    title = re.sub(r"\s+", " ", title)
    return title.title()[:120] or "Untitled"


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC — track list for JS player
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/wcpr/list")
def wcpr_list():
    """Return JSON array of active WCPR tracks."""
    from wcpr import get_tracks
    tracks = get_tracks(active_only=True)
    return JSONResponse([
        {"id": t["id"], "title": t["title"], "url": f"/static/wcpr/{t['filename']}"}
        for t in tracks
    ])


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN — manage tracks
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/admin/wcpr", response_class=HTMLResponse)
def admin_wcpr_page(
    session_token: Optional[str] = Cookie(None),
    msg: str = "",
    err: str = "",
):
    player, redirect = _admin_guard(session_token)
    if redirect:
        return redirect

    from wcpr import get_tracks
    tracks = get_tracks()

    banner = ""
    if msg:
        banner = f'<div style="padding:10px 16px;background:#052e16;border:1px solid #16a34a;color:#4ade80;margin-bottom:16px;">{msg}</div>'
    elif err:
        banner = f'<div style="padding:10px 16px;background:#1a0505;border:1px solid #dc2626;color:#f87171;margin-bottom:16px;">{err}</div>'

    if tracks:
        rows = ""
        for t in tracks:
            active_color = "#22c55e" if t.get("is_active", True) else "#64748b"
            active_label = "Active" if t.get("is_active", True) else "Hidden"
            safe_title = t["title"].replace('"', '&quot;').replace("'", "&#39;")
            rows += f'''
            <tr style="border-bottom:1px solid #0f172a;">
                <td style="padding:10px 8px;color:#e5e7eb;">
                    <span id="wt-{t["id"]}">{t["title"]}</span>
                    <button onclick="wcprRename({t["id"]})" title="Rename"
                            style="background:none;border:none;color:#64748b;cursor:pointer;font-size:0.8rem;padding:0 4px;vertical-align:middle;">✏️</button>
                    <form id="wrf-{t["id"]}" action="/admin/wcpr/rename" method="post"
                          style="display:none;margin-top:6px;">
                        <input type="hidden" name="track_id" value="{t["id"]}">
                        <input type="text" name="title" value="{safe_title}" required maxlength="120"
                               style="background:#020617;border:1px solid #334155;color:#e5e7eb;padding:4px 6px;font-size:0.8rem;width:200px;box-sizing:border-box;">
                        <button type="submit"
                                style="background:#0c4a6e;border:1px solid #0284c7;color:#7dd3fc;padding:3px 8px;font-size:0.75rem;cursor:pointer;border-radius:3px;margin-left:4px;">Save</button>
                        <button type="button" onclick="wcprRename({t["id"]})"
                                style="background:#1e293b;border:1px solid #334155;color:#94a3b8;padding:3px 8px;font-size:0.75rem;cursor:pointer;border-radius:3px;margin-left:2px;">Cancel</button>
                    </form>
                </td>
                <td style="padding:10px 8px;color:#64748b;font-size:0.8rem;">{t["filename"]}</td>
                <td style="padding:10px 8px;">
                    <audio controls preload="none" style="height:28px;width:200px;">
                        <source src="/static/wcpr/{t["filename"]}">
                    </audio>
                </td>
                <td style="padding:10px 8px;text-align:center;">
                    <span style="color:{active_color};font-size:0.8rem;">{active_label}</span>
                </td>
                <td style="padding:10px 8px;text-align:right;">
                    <form action="/admin/wcpr/toggle" method="post" style="display:inline;">
                        <input type="hidden" name="track_id" value="{t["id"]}">
                        <button style="background:#1e293b;border:1px solid #334155;color:#94a3b8;padding:4px 10px;font-size:0.75rem;cursor:pointer;border-radius:3px;margin-right:4px;">
                            {"Disable" if t.get("is_active", True) else "Enable"}
                        </button>
                    </form>
                    <form action="/admin/wcpr/delete" method="post" style="display:inline;"
                          onsubmit="return confirm('Delete &quot;{safe_title}&quot;? This cannot be undone.')">
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
                    <th style="padding:8px;text-align:left;">Episode Title</th>
                    <th style="padding:8px;text-align:left;">Filename</th>
                    <th style="padding:8px;text-align:left;">Preview</th>
                    <th style="padding:8px;text-align:center;">Status</th>
                    <th style="padding:8px;text-align:right;">Actions</th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>'''
    else:
        track_table = '<p style="color:#64748b;padding:20px 0;">No episodes uploaded yet.</p>'

    html = f'''
    <a href="/admin" style="color:#38bdf8;">&larr; Admin Dashboard</a>
    <h1 style="margin:8px 0 4px 0;">📻 WCPR 104.1 — Talk Radio Manager</h1>
    <p style="color:#64748b;margin-bottom:20px;">
        Upload MP3/OGG/WAV talk radio episodes (max {MAX_FILE_MB} MB each).
        Active episodes play in order on WCPR 104.1 in the in-game radio player.
    </p>
    {banner}

    <!-- Upload Form -->
    <div class="card" style="margin-bottom:20px;">
        <h3 style="margin:0 0 14px 0;">Upload Episode</h3>
        <form id="wcpr-upload-form" action="/admin/wcpr/upload" method="post" enctype="multipart/form-data"
              style="display:flex;flex-wrap:wrap;gap:12px;align-items:flex-end;">
            <div style="flex:1;min-width:200px;">
                <label style="font-size:0.75rem;color:#64748b;display:block;margin-bottom:4px;">Episode Title *</label>
                <input type="text" name="title" required placeholder="e.g. The Economics of Districts"
                       style="width:100%;background:#020617;border:1px solid #334155;color:#e5e7eb;padding:8px;box-sizing:border-box;">
            </div>
            <div style="flex:1;min-width:200px;">
                <label style="font-size:0.75rem;color:#64748b;display:block;margin-bottom:4px;">Audio File * (MP3/OGG/WAV/FLAC/M4A/AAC)</label>
                <input type="file" name="file" required accept="audio/*" id="wcpr-file-input"
                       style="width:100%;background:#020617;border:1px solid #334155;color:#e5e7eb;padding:7px;box-sizing:border-box;">
            </div>
            <div style="flex-shrink:0;">
                <button type="submit" id="wcpr-upload-btn" class="btn-blue" style="padding:9px 20px;">Upload Episode</button>
            </div>
        </form>
        <div id="wcpr-upload-status" style="display:none;margin-top:12px;">
            <div id="wcpr-upload-text" style="font-size:0.8rem;color:#94a3b8;margin-bottom:6px;">Starting upload...</div>
            <div style="background:#0f172a;border:1px solid #1e293b;border-radius:4px;height:8px;overflow:hidden;">
                <div id="wcpr-upload-bar" style="background:#38bdf8;height:100%;width:0%;transition:width 0.15s;"></div>
            </div>
        </div>
    </div>

    <!-- Bulk Upload -->
    <div class="card" style="margin-bottom:20px;">
        <h3 style="margin:0 0 6px 0;">Bulk Upload</h3>
        <p style="color:#64748b;font-size:0.8rem;margin:0 0 12px 0;">
            Select multiple files at once. Titles are auto-generated from filenames and can be renamed after upload.
        </p>
        <form id="bulk-form" action="/admin/wcpr/bulk_upload" method="post" enctype="multipart/form-data">
            <div style="margin-bottom:10px;">
                <label style="font-size:0.75rem;color:#64748b;display:block;margin-bottom:4px;">
                    Audio Files * (MP3/OGG/WAV/FLAC/M4A/AAC, max {MAX_FILE_MB} MB each)
                </label>
                <input type="file" name="files" multiple required accept="audio/*" id="wcpr-bulk-input"
                       style="width:100%;background:#020617;border:1px solid #334155;color:#e5e7eb;padding:7px;box-sizing:border-box;">
            </div>
            <div id="wcpr-bulk-preview" style="margin-bottom:10px;display:none;">
                <p style="font-size:0.75rem;color:#64748b;margin:0 0 6px 0;">Files to upload:</p>
                <ul id="wcpr-bulk-list" style="margin:0;padding-left:18px;color:#94a3b8;font-size:0.8rem;"></ul>
            </div>
            <button type="submit" class="btn-blue" style="padding:9px 20px;">Upload All</button>
        </form>
    </div>
    <script>
    // ── Bulk upload file preview ──────────────────────────────────────────
    document.getElementById('wcpr-bulk-input').addEventListener('change', function() {{
        var list = document.getElementById('wcpr-bulk-list');
        var preview = document.getElementById('wcpr-bulk-preview');
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

    // ── Rename toggle ─────────────────────────────────────────────────────
    function wcprRename(id) {{
        var form = document.getElementById('wrf-' + id);
        form.style.display = form.style.display === 'none' ? 'block' : 'none';
    }}

    // ── Single upload with XHR progress bar ──────────────────────────────
    (function() {{
        var form = document.getElementById('wcpr-upload-form');
        var btn  = document.getElementById('wcpr-upload-btn');
        var statusDiv = document.getElementById('wcpr-upload-status');
        var statusTxt = document.getElementById('wcpr-upload-text');
        var bar       = document.getElementById('wcpr-upload-bar');

        form.addEventListener('submit', function(e) {{
            e.preventDefault();

            var titleInput = form.querySelector('input[name="title"]');
            var fileInput  = document.getElementById('wcpr-file-input');
            if (!titleInput.value.trim()) {{ titleInput.focus(); return; }}
            if (!fileInput.files.length)  {{ fileInput.focus();  return; }}

            var xhr = new XMLHttpRequest();
            btn.disabled = true;
            btn.textContent = 'Uploading\u2026';
            statusDiv.style.display = 'block';
            bar.style.width = '0%';
            statusTxt.textContent = 'Starting upload\u2026';

            xhr.upload.addEventListener('progress', function(e) {{
                if (e.lengthComputable) {{
                    var pct    = Math.round(e.loaded / e.total * 100);
                    var loaded = (e.loaded / 1048576).toFixed(1);
                    var total  = (e.total  / 1048576).toFixed(1);
                    bar.style.width = pct + '%';
                    statusTxt.textContent = 'Uploading\u2026 ' + pct + '% (' + loaded + ' / ' + total + ' MB)';
                }}
            }});

            xhr.addEventListener('load', function() {{
                bar.style.width = '100%';
                statusTxt.textContent = 'Processing\u2026';
                window.location.href = xhr.responseURL || '/admin/wcpr';
            }});

            xhr.addEventListener('error', function() {{
                btn.disabled = false;
                btn.textContent = 'Upload Episode';
                statusDiv.style.display = 'none';
                alert('Upload failed \u2014 please check your connection and try again.');
            }});

            xhr.open('POST', '/admin/wcpr/upload');
            xhr.send(new FormData(form));
        }});
    }})();
    </script>

    <!-- Track List -->
    <div class="card">
        <h3 style="margin:0 0 14px 0;">Episodes ({len(tracks)})</h3>
        {track_table}
    </div>

    <p style="color:#475569;font-size:0.75rem;margin-top:16px;">
        Episodes play in order on WCPR 104.1. Players can listen via the Audio tab in Settings.
        Disable an episode to remove it from the rotation without deleting the file.
    </p>
    '''

    from ux import shell
    return HTMLResponse(shell("WCPR Manager", html, 0, player.id))


@router.post("/admin/wcpr/upload")
async def admin_wcpr_upload(
    session_token: Optional[str] = Cookie(None),
    title: str = Form(...),
    file: UploadFile = File(...),
):
    player, redirect = _admin_guard(session_token)
    if redirect:
        return redirect

    _, ext = os.path.splitext(file.filename or "")
    ext = ext.lower()
    if ext not in ALLOWED_AUDIO_EXTS:
        from urllib.parse import quote
        return RedirectResponse(
            f"/admin/wcpr?err={quote(f'Unsupported file type: {ext}. Use MP3, OGG, WAV, FLAC, M4A, or AAC.')}",
            status_code=303,
        )

    await file.seek(0)
    data = await file.read()
    if not data:
        from urllib.parse import quote
        return RedirectResponse("/admin/wcpr?err=No+file+data+received.+Please+try+again.", status_code=303)
    if len(data) > MAX_FILE_MB * 1024 * 1024:
        from urllib.parse import quote
        return RedirectResponse(
            f"/admin/wcpr?err={quote(f'File too large (max {MAX_FILE_MB} MB).')}",
            status_code=303,
        )

    try:
        from wcpr import WCPR_DIR, add_track
        os.makedirs(WCPR_DIR, exist_ok=True)
        safe_name = _safe_filename(file.filename or f"episode{ext}")
        dest = os.path.join(WCPR_DIR, safe_name)
        if os.path.exists(dest):
            import time
            base, e = os.path.splitext(safe_name)
            safe_name = f"{base}_{int(time.time())}{e}"
            dest = os.path.join(WCPR_DIR, safe_name)

        with open(dest, "wb") as f_out:
            f_out.write(data)

        track = add_track(safe_name, title.strip()[:120])
        from urllib.parse import quote
        t_title = track["title"]
        return RedirectResponse(f"/admin/wcpr?msg={quote(f'Uploaded: {t_title}')}", status_code=303)
    except Exception as exc:
        import traceback
        traceback.print_exc()
        from urllib.parse import quote
        return RedirectResponse(f"/admin/wcpr?err={quote(f'Upload failed: {exc}')}", status_code=303)


@router.post("/admin/wcpr/bulk_upload")
async def admin_wcpr_bulk_upload(
    session_token: Optional[str] = Cookie(None),
    files: List[UploadFile] = File(...),
):
    player, redirect = _admin_guard(session_token)
    if redirect:
        return redirect

    from wcpr import WCPR_DIR, add_track
    import time as _time
    from urllib.parse import quote

    try:
        os.makedirs(WCPR_DIR, exist_ok=True)
    except Exception as exc:
        return RedirectResponse(f"/admin/wcpr?err={quote(f'Cannot create upload dir: {exc}')}", status_code=303)

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

        try:
            safe_name = _safe_filename(file.filename or f"episode{ext}")
            dest = os.path.join(WCPR_DIR, safe_name)
            if os.path.exists(dest):
                base, e = os.path.splitext(safe_name)
                safe_name = f"{base}_{int(_time.time())}{e}"
                dest = os.path.join(WCPR_DIR, safe_name)

            with open(dest, "wb") as f_out:
                f_out.write(data)

            title = _title_from_filename(file.filename or safe_name)
            add_track(safe_name, title)
            uploaded.append(title)
        except Exception as exc:
            import traceback
            traceback.print_exc()
            skipped.append(f"{file.filename} (error: {exc})")

    parts = []
    if uploaded:
        parts.append(f"{len(uploaded)} episode(s) uploaded")
    if skipped:
        parts.append(f"{len(skipped)} skipped: {', '.join(skipped)}")

    if not parts:
        return RedirectResponse("/admin/wcpr?err=No+valid+files+selected", status_code=303)

    if skipped:
        return RedirectResponse(f"/admin/wcpr?err={quote('; '.join(parts))}", status_code=303)
    return RedirectResponse(f"/admin/wcpr?msg={quote('; '.join(parts))}", status_code=303)


@router.post("/admin/wcpr/toggle")
def admin_wcpr_toggle(
    session_token: Optional[str] = Cookie(None),
    track_id: int = Form(...),
):
    player, redirect = _admin_guard(session_token)
    if redirect:
        return redirect
    from wcpr import get_tracks, set_active
    tracks = get_tracks()
    target = next((t for t in tracks if t["id"] == track_id), None)
    if target:
        set_active(track_id, not target.get("is_active", True))
    return RedirectResponse("/admin/wcpr?msg=Updated", status_code=303)


@router.post("/admin/wcpr/rename")
def admin_wcpr_rename(
    session_token: Optional[str] = Cookie(None),
    track_id: int = Form(...),
    title: str = Form(...),
):
    player, redirect = _admin_guard(session_token)
    if redirect:
        return redirect
    new_title = title.strip()[:120]
    if not new_title:
        return RedirectResponse("/admin/wcpr?err=Title+cannot+be+empty", status_code=303)
    from wcpr import rename_track
    from urllib.parse import quote
    if rename_track(track_id, new_title):
        return RedirectResponse(f"/admin/wcpr?msg={quote(f'Renamed to: {new_title}')}", status_code=303)
    return RedirectResponse("/admin/wcpr?err=Track+not+found", status_code=303)


@router.post("/admin/wcpr/delete")
def admin_wcpr_delete(
    session_token: Optional[str] = Cookie(None),
    track_id: int = Form(...),
):
    player, redirect = _admin_guard(session_token)
    if redirect:
        return redirect
    from wcpr import delete_track, get_tracks
    tracks = get_tracks()
    target = next((t for t in tracks if t["id"] == track_id), None)
    if target:
        delete_track(track_id)
        from urllib.parse import quote
        t_title = target["title"]
        return RedirectResponse(f"/admin/wcpr?msg={quote(f'Deleted: {t_title}')}", status_code=303)
    return RedirectResponse("/admin/wcpr?err=Track+not+found", status_code=303)
