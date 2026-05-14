"""
maph_matt_ux.py — Admin routes for MAPH (CH 46) and MATT (CH 28) playlists.

Public:
  GET /api/maph/list   — active MAPH playlist (JSON, for player)
  GET /api/matt/list   — active MATT playlist (JSON, for player)
  POST /api/matt/submit — player submits a YouTube video for MATT

Admin:
  GET  /admin/maph                  — manage MAPH playlist
  POST /admin/maph/add              — add video
  POST /admin/maph/toggle           — toggle active
  POST /admin/maph/rename           — rename
  POST /admin/maph/delete           — delete

  GET  /admin/matt                  — manage MATT playlist + review submissions
  POST /admin/matt/add              — add video directly
  POST /admin/matt/toggle           — toggle active
  POST /admin/matt/rename           — rename
  POST /admin/matt/delete           — delete
  POST /admin/matt/approve          — approve submission → adds to MATT
  POST /admin/matt/reject           — reject submission
  POST /admin/matt/sub-delete       — delete submission record
"""

from typing import Optional
from fastapi import APIRouter, Cookie, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse

router = APIRouter()


def _admin_guard(session_token):
    from admins import require_admin
    player = require_admin(session_token)
    if not player:
        return None, RedirectResponse(url="/login", status_code=303)
    return player, None


def _require_auth(session_token):
    try:
        import auth
        db = auth.get_db()
        player = auth.get_player_from_session(db, session_token)
        db.close()
        return player
    except Exception:
        return None


def _yt_thumb(ytid: str) -> str:
    return f"https://img.youtube.com/vi/{ytid}/mqdefault.jpg"


def _yt_url(ytid: str) -> str:
    return f"https://www.youtube.com/watch?v={ytid}"


def _banner(msg: str = "", err: str = "") -> str:
    if msg:
        return f'<div style="padding:10px 16px;background:#052e16;border:1px solid #16a34a;color:#4ade80;margin-bottom:16px;">{msg}</div>'
    if err:
        return f'<div style="padding:10px 16px;background:#1a0505;border:1px solid #dc2626;color:#f87171;margin-bottom:16px;">{err}</div>'
    return ""


def _video_table(tracks, toggle_url, rename_url, delete_url, extra_col_header="", extra_col_fn=None):
    if not tracks:
        return '<p style="color:#64748b;padding:20px 0;">No videos in playlist yet.</p>'
    rows = ""
    for t in tracks:
        ytid = t.get("youtube_id", "")
        safe_title = t["title"].replace('"', '&quot;').replace("'", "&#39;")
        active_color = "#22c55e" if t.get("is_active", True) else "#64748b"
        active_label = "Active" if t.get("is_active", True) else "Hidden"
        submitter_cell = f'<td style="padding:8px;color:#64748b;font-size:0.78rem;">{t.get("submitter","")}</td>' if extra_col_header else ""
        rows += f"""
        <tr style="border-bottom:1px solid #0f172a;vertical-align:middle;">
            <td style="padding:8px;">
                <a href="{_yt_url(ytid)}" target="_blank" rel="noopener">
                    <img src="{_yt_thumb(ytid)}" style="width:100px;height:56px;object-fit:cover;border-radius:4px;display:block;">
                </a>
            </td>
            <td style="padding:8px;color:#e5e7eb;">
                <span id="mm-title-{t['id']}">{t['title']}</span>
                <button onclick="mmRenameToggle({t['id']})" title="Rename"
                        style="background:none;border:none;color:#64748b;cursor:pointer;font-size:0.8rem;padding:0 4px;vertical-align:middle;">✏️</button>
                <form id="mm-rename-{t['id']}" action="{rename_url}" method="post"
                      style="display:none;margin-top:6px;">
                    <input type="hidden" name="entry_id" value="{t['id']}">
                    <input type="text" name="title" value="{safe_title}" required maxlength="120"
                           style="background:#020617;border:1px solid #334155;color:#e5e7eb;padding:4px 6px;font-size:0.8rem;width:200px;">
                    <button type="submit"
                            style="background:#0c4a6e;border:1px solid #0284c7;color:#7dd3fc;padding:3px 8px;font-size:0.75rem;cursor:pointer;border-radius:3px;margin-left:4px;">Save</button>
                    <button type="button" onclick="mmRenameToggle({t['id']})"
                            style="background:#1e293b;border:1px solid #334155;color:#94a3b8;padding:3px 8px;font-size:0.75rem;cursor:pointer;border-radius:3px;margin-left:2px;">Cancel</button>
                </form>
                <div style="font-size:0.72rem;color:#475569;margin-top:2px;">{ytid}</div>
            </td>
            {submitter_cell}
            <td style="padding:8px;text-align:center;">
                <span style="color:{active_color};font-size:0.8rem;">{active_label}</span>
            </td>
            <td style="padding:8px;text-align:right;white-space:nowrap;">
                <form action="{toggle_url}" method="post" style="display:inline;">
                    <input type="hidden" name="entry_id" value="{t['id']}">
                    <button style="background:#1e293b;border:1px solid #334155;color:#94a3b8;padding:4px 10px;font-size:0.75rem;cursor:pointer;border-radius:3px;margin-right:4px;">
                        {'Disable' if t.get('is_active', True) else 'Enable'}
                    </button>
                </form>
                <form action="{delete_url}" method="post" style="display:inline;"
                      onsubmit="return confirm('Remove this video?')">
                    <input type="hidden" name="entry_id" value="{t['id']}">
                    <button style="background:#1a0505;border:1px solid #dc2626;color:#f87171;padding:4px 10px;font-size:0.75rem;cursor:pointer;border-radius:3px;">
                        Delete
                    </button>
                </form>
            </td>
        </tr>"""
    extra_th = f'<th style="padding:8px;text-align:left;">Submitted by</th>' if extra_col_header else ""
    return f"""
    <table style="width:100%;border-collapse:collapse;">
        <thead>
            <tr style="border-bottom:1px solid #1e293b;color:#64748b;font-size:0.75rem;">
                <th style="padding:8px;text-align:left;">Thumbnail</th>
                <th style="padding:8px;text-align:left;">Title / ID</th>
                {extra_th}
                <th style="padding:8px;text-align:center;">Status</th>
                <th style="padding:8px;text-align:right;">Actions</th>
            </tr>
        </thead>
        <tbody>{rows}</tbody>
    </table>"""


_RENAME_JS = """
<script>
function mmRenameToggle(id) {
    var form = document.getElementById('mm-rename-' + id);
    form.style.display = form.style.display === 'none' ? 'block' : 'none';
}
</script>"""


# ── Public API ────────────────────────────────────────────────────────────────

@router.get("/api/maph/list")
def api_maph_list():
    """MAPH pulls directly from wiki_media.json videos — same source as /admin/wiki."""
    import json, os
    try:
        path = os.path.join(os.path.dirname(__file__), "wiki_media.json")
        with open(path) as f:
            data = json.load(f)
        videos = data.get("videos", [])
        return JSONResponse([
            {"id": i, "youtube_id": v["youtube_id"], "title": v["title"]}
            for i, v in enumerate(videos) if v.get("youtube_id")
        ])
    except Exception:
        return JSONResponse([])


@router.get("/api/matt/list")
def api_matt_list():
    from maph_matt import matt_get
    tracks = matt_get(active_only=True)
    return JSONResponse([{"id": t["id"], "youtube_id": t["youtube_id"], "title": t["title"],
                          "submitter": t.get("submitter", "")} for t in tracks])


@router.post("/api/matt/submit")
async def api_matt_submit(
    session_token: Optional[str] = Cookie(None),
    youtube_url: str = Form(...),
    title: str = Form(...),
    note: str = Form(""),
):
    player = _require_auth(session_token)
    if not player:
        return JSONResponse({"ok": False, "error": "Not logged in"}, status_code=401)
    from maph_matt import extract_youtube_id, sub_add
    ytid = extract_youtube_id(youtube_url.strip())
    if not ytid:
        return JSONResponse({"ok": False, "error": "Could not extract a YouTube video ID from that URL."})
    title = title.strip()[:120]
    if not title:
        return JSONResponse({"ok": False, "error": "Title is required."})
    sub_add(player.id, player.business_name, ytid, title, note.strip()[:300])
    return JSONResponse({"ok": True})


# ── Admin: MAPH (CH 46) ───────────────────────────────────────────────────────

@router.get("/admin/maph", response_class=HTMLResponse)
def admin_maph_page(session_token: Optional[str] = Cookie(None)):
    """MAPH plays the wiki_media.json videos — redirect admins to the right place."""
    _, redir = _admin_guard(session_token)
    if redir:
        return redir
    return RedirectResponse(
        "/admin/wiki?msg=MAPH+%28CH+46%29+plays+the+videos+listed+here+%E2%80%94+add+or+remove+them+in+the+Videos+section+below",
        status_code=303,
    )


# ── Admin: MATT (CH 28) ───────────────────────────────────────────────────────

@router.get("/admin/matt", response_class=HTMLResponse)
def admin_matt_page(
    session_token: Optional[str] = Cookie(None),
    msg: str = "", err: str = "",
):
    player, redir = _admin_guard(session_token)
    if redir:
        return redir
    from maph_matt import matt_get, sub_list
    tracks  = matt_get()
    pending = sub_list(status="pending")
    all_subs = sub_list()

    playlist_table = _video_table(
        tracks, "/admin/matt/toggle", "/admin/matt/rename", "/admin/matt/delete",
        extra_col_header="Submitted by",
    )

    # Pending submissions
    if pending:
        sub_rows = ""
        for s in pending:
            ytid = s.get("youtube_id", "")
            sub_rows += f"""
            <tr style="border-bottom:1px solid #0f172a;vertical-align:middle;">
                <td style="padding:8px;">
                    <a href="{_yt_url(ytid)}" target="_blank" rel="noopener">
                        <img src="{_yt_thumb(ytid)}" style="width:100px;height:56px;object-fit:cover;border-radius:4px;">
                    </a>
                </td>
                <td style="padding:8px;color:#e5e7eb;">{s['title']}<div style="font-size:0.72rem;color:#475569;">{ytid}</div></td>
                <td style="padding:8px;color:#94a3b8;font-size:0.82rem;">{s['player_name']}<div style="color:#475569;font-size:0.72rem;">#{s['player_id']}</div></td>
                <td style="padding:8px;color:#64748b;font-size:0.78rem;">{s.get('note','')[:80]}</td>
                <td style="padding:8px;color:#475569;font-size:0.72rem;">{s.get('submitted_at','')[:16]}</td>
                <td style="padding:8px;white-space:nowrap;">
                    <form action="/admin/matt/approve" method="post" style="display:inline;">
                        <input type="hidden" name="sub_id" value="{s['id']}">
                        <button style="background:#052e16;border:1px solid #16a34a;color:#4ade80;padding:4px 10px;font-size:0.75rem;cursor:pointer;border-radius:3px;margin-right:4px;">
                            ✓ Approve
                        </button>
                    </form>
                    <form action="/admin/matt/reject" method="post" style="display:inline;">
                        <input type="hidden" name="sub_id" value="{s['id']}">
                        <button style="background:#1a0505;border:1px solid #dc2626;color:#f87171;padding:4px 10px;font-size:0.75rem;cursor:pointer;border-radius:3px;">
                            ✕ Reject
                        </button>
                    </form>
                </td>
            </tr>"""
        sub_table = f"""
        <table style="width:100%;border-collapse:collapse;">
            <thead>
                <tr style="border-bottom:1px solid #1e293b;color:#64748b;font-size:0.75rem;">
                    <th style="padding:8px;text-align:left;">Thumbnail</th>
                    <th style="padding:8px;text-align:left;">Title</th>
                    <th style="padding:8px;text-align:left;">Player</th>
                    <th style="padding:8px;text-align:left;">Note</th>
                    <th style="padding:8px;text-align:left;">Submitted</th>
                    <th style="padding:8px;text-align:left;">Action</th>
                </tr>
            </thead>
            <tbody>{sub_rows}</tbody>
        </table>"""
    else:
        sub_table = '<p style="color:#64748b;padding:12px 0;">No pending submissions.</p>'

    html = f"""
    <a href="/admin" style="color:#38bdf8;">&larr; Admin Dashboard</a>
    <h1 style="margin:8px 0 4px 0;">📺 MATT — Channel 28 Playlist Manager</h1>
    <p style="color:#64748b;margin-bottom:20px;">
        Community player videos &amp; streams. Review submissions and manage the CH 28 playlist.
    </p>
    {_banner(msg, err)}

    <div style="background:#1c0a0a;border:1px solid #7f1d1d;border-radius:8px;padding:20px;margin-bottom:24px;">
        <h2 style="font-size:0.95rem;color:#fca5a5;margin:0 0 14px 0;">
            Pending Submissions ({len(pending)})
        </h2>
        {sub_table}
    </div>

    <div style="background:#0f172a;border:1px solid #1e293b;border-radius:8px;padding:20px;margin-bottom:24px;">
        <h2 style="font-size:0.95rem;color:#e2e8f0;margin:0 0 14px 0;">Add Video Directly to MATT</h2>
        <form action="/admin/matt/add" method="post" style="display:flex;gap:10px;flex-wrap:wrap;align-items:flex-end;">
            <div>
                <label style="display:block;color:#94a3b8;font-size:0.75rem;margin-bottom:4px;">YouTube URL or ID</label>
                <input type="text" name="youtube_url" required placeholder="https://youtube.com/watch?v=... or video ID"
                       style="background:#020617;border:1px solid #334155;color:#e5e7eb;padding:8px 10px;font-size:0.85rem;border-radius:4px;width:320px;">
            </div>
            <div>
                <label style="display:block;color:#94a3b8;font-size:0.75rem;margin-bottom:4px;">Title</label>
                <input type="text" name="title" required maxlength="120" placeholder="Video title"
                       style="background:#020617;border:1px solid #334155;color:#e5e7eb;padding:8px 10px;font-size:0.85rem;border-radius:4px;width:240px;">
            </div>
            <button type="submit"
                    style="background:#1d4ed8;border:1px solid #3b82f6;color:#e2e8f0;padding:8px 18px;font-size:0.85rem;border-radius:4px;cursor:pointer;">
                Add to MATT
            </button>
        </form>
    </div>

    <div style="background:#0f172a;border:1px solid #1e293b;border-radius:8px;padding:20px;">
        <h2 style="font-size:0.95rem;color:#e2e8f0;margin:0 0 14px 0;">MATT Playlist ({len(tracks)} video{"s" if len(tracks) != 1 else ""})</h2>
        {playlist_table}
    </div>
    {_RENAME_JS}
    """
    from ux import shell
    return HTMLResponse(shell("Admin — MATT CH 28", html, 0, player.id))


@router.post("/admin/matt/add")
async def admin_matt_add(
    session_token: Optional[str] = Cookie(None),
    youtube_url: str = Form(...),
    title: str = Form(...),
):
    _, redir = _admin_guard(session_token)
    if redir:
        return redir
    from maph_matt import extract_youtube_id, matt_add
    ytid = extract_youtube_id(youtube_url.strip())
    if not ytid:
        return RedirectResponse("/admin/matt?err=Could+not+extract+YouTube+ID", status_code=303)
    matt_add(ytid, title.strip()[:120])
    return RedirectResponse("/admin/matt?msg=Video+added+to+MATT", status_code=303)


@router.post("/admin/matt/toggle")
async def admin_matt_toggle(
    session_token: Optional[str] = Cookie(None),
    entry_id: int = Form(...),
):
    _, redir = _admin_guard(session_token)
    if redir:
        return redir
    from maph_matt import matt_get, matt_toggle
    tracks = matt_get()
    t = next((x for x in tracks if x["id"] == entry_id), None)
    if t:
        matt_toggle(entry_id, not t.get("is_active", True))
    return RedirectResponse("/admin/matt", status_code=303)


@router.post("/admin/matt/rename")
async def admin_matt_rename(
    session_token: Optional[str] = Cookie(None),
    entry_id: int = Form(...),
    title: str = Form(...),
):
    _, redir = _admin_guard(session_token)
    if redir:
        return redir
    from maph_matt import matt_rename
    matt_rename(entry_id, title.strip()[:120])
    return RedirectResponse("/admin/matt?msg=Renamed", status_code=303)


@router.post("/admin/matt/delete")
async def admin_matt_delete(
    session_token: Optional[str] = Cookie(None),
    entry_id: int = Form(...),
):
    _, redir = _admin_guard(session_token)
    if redir:
        return redir
    from maph_matt import matt_delete
    matt_delete(entry_id)
    return RedirectResponse("/admin/matt?msg=Video+removed", status_code=303)


@router.post("/admin/matt/approve")
async def admin_matt_approve(
    session_token: Optional[str] = Cookie(None),
    sub_id: int = Form(...),
    admin_note: str = Form(""),
):
    _, redir = _admin_guard(session_token)
    if redir:
        return redir
    from maph_matt import sub_review
    sub_review(sub_id, "approve", admin_note)
    return RedirectResponse("/admin/matt?msg=Submission+approved+and+added+to+MATT", status_code=303)


@router.post("/admin/matt/reject")
async def admin_matt_reject(
    session_token: Optional[str] = Cookie(None),
    sub_id: int = Form(...),
    admin_note: str = Form(""),
):
    _, redir = _admin_guard(session_token)
    if redir:
        return redir
    from maph_matt import sub_review
    sub_review(sub_id, "reject", admin_note)
    return RedirectResponse("/admin/matt?msg=Submission+rejected", status_code=303)


@router.post("/admin/matt/sub-delete")
async def admin_matt_sub_delete(
    session_token: Optional[str] = Cookie(None),
    sub_id: int = Form(...),
):
    _, redir = _admin_guard(session_token)
    if redir:
        return redir
    from maph_matt import sub_delete
    sub_delete(sub_id)
    return RedirectResponse("/admin/matt", status_code=303)
