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
        return f'<div style="padding:10px 16px;background:#052e16;border:1px solid #16a34a;color:#4ade80;margin-bottom:16px;border-radius:4px;">{msg}</div>'
    if err:
        return f'<div style="padding:10px 16px;background:#1a0505;border:1px solid #dc2626;color:#f87171;margin-bottom:16px;border-radius:4px;">{err}</div>'
    return ""


def _video_table(tracks, toggle_url, rename_url, delete_url, show_submitter=False):
    if not tracks:
        return '<p style="color:#64748b;padding:20px 0;">No videos in playlist yet.</p>'
    rows = ""
    for t in tracks:
        ytid = t.get("youtube_id", "")
        safe_title = t["title"].replace('"', '&quot;').replace("'", "&#39;")
        is_active = t.get("is_active", True)
        status_badge = (
            '<span class="badge badge-green">Active</span>'
            if is_active else
            '<span class="badge badge-yellow">Hidden</span>'
        )
        submitter_cell = (
            f'<td style="color:#94a3b8;font-size:0.7rem;">{t.get("submitter","")}</td>'
            if show_submitter else ""
        )
        toggle_label = "Disable" if is_active else "Enable"
        toggle_class = "btn btn-gray" if is_active else "btn btn-green"
        new_active_val = "0" if is_active else "1"
        rows += f"""
        <tr>
            <td>
                <a href="{_yt_url(ytid)}" target="_blank" rel="noopener">
                    <img src="{_yt_thumb(ytid)}" style="width:88px;height:50px;object-fit:cover;border-radius:3px;display:block;border:1px solid #1e293b;">
                </a>
            </td>
            <td>
                <span id="mm-title-{t['id']}" style="color:#e5e7eb;">{t['title']}</span>
                <button onclick="mmRenameToggle({t['id']})" title="Rename"
                        style="background:none;border:none;color:#475569;cursor:pointer;font-size:0.8rem;padding:0 4px;vertical-align:middle;">✏️</button>
                <form id="mm-rename-{t['id']}" action="{rename_url}" method="post"
                      style="display:none;margin-top:6px;">
                    <input type="hidden" name="entry_id" value="{t['id']}">
                    <div style="display:flex;gap:4px;flex-wrap:wrap;">
                        <input type="text" name="title" value="{safe_title}" required maxlength="120"
                               style="width:200px;font-size:13px;">
                        <button type="submit" class="btn btn-blue">Save</button>
                        <button type="button" onclick="mmRenameToggle({t['id']})" class="btn btn-gray">Cancel</button>
                    </div>
                </form>
                <div style="font-size:0.65rem;color:#334155;margin-top:2px;">{ytid}</div>
            </td>
            {submitter_cell}
            <td style="text-align:center;">{status_badge}</td>
            <td style="text-align:right;white-space:nowrap;">
                <form action="{toggle_url}" method="post" style="display:inline;">
                    <input type="hidden" name="entry_id" value="{t['id']}">
                    <input type="hidden" name="new_active" value="{new_active_val}">
                    <button class="{toggle_class}" style="margin-right:4px;">{toggle_label}</button>
                </form>
                <form action="{delete_url}" method="post" style="display:inline;"
                      onsubmit="return confirm('Remove this video?')">
                    <input type="hidden" name="entry_id" value="{t['id']}">
                    <button class="btn btn-red">Delete</button>
                </form>
            </td>
        </tr>"""
    extra_th = '<th>Submitted by</th>' if show_submitter else ""
    return f"""
    <div class="table-wrap">
    <table>
        <thead>
            <tr>
                <th>Thumbnail</th>
                <th>Title / ID</th>
                {extra_th}
                <th style="text-align:center;">Status</th>
                <th style="text-align:right;">Actions</th>
            </tr>
        </thead>
        <tbody>{rows}</tbody>
    </table>
    </div>"""


_RENAME_JS = """
<script>
function mmRenameToggle(id) {
    var form = document.getElementById('mm-rename-' + id);
    form.style.display = form.style.display === 'none' ? 'block' : 'none';
}

// Client-side YouTube URL validation
(function() {
    var form = document.getElementById('mattAddForm');
    if (!form) return;
    form.addEventListener('submit', function(e) {
        var raw = document.getElementById('mattUrlInput').value.trim();
        var patterns = [
            /youtu\.be\/([A-Za-z0-9_-]{11})/,
            /youtube\.com\/watch\?.*v=([A-Za-z0-9_-]{11})/,
            /youtube\.com\/embed\/([A-Za-z0-9_-]{11})/,
            /youtube\.com\/v\/([A-Za-z0-9_-]{11})/,
            /youtube\.com\/shorts\/([A-Za-z0-9_-]{11})/,
            /^[A-Za-z0-9_-]{11}$/,
        ];
        var valid = patterns.some(function(p) { return p.test(raw); });
        if (!valid) {
            e.preventDefault();
            var msg = document.getElementById('mattUrlErr');
            if (msg) { msg.style.display = 'block'; msg.textContent = 'Enter a valid YouTube URL or 11-character video ID.'; }
        }
    });
})();
</script>"""


# ── Public API ────────────────────────────────────────────────────────────────

@router.get("/api/maph/list")
def api_maph_list():
    """MAPH pulls from wiki_media DB — same source as /admin/wiki."""
    try:
        import wiki as _wiki
        videos = _wiki.list_entries(kind="video")
        return JSONResponse([
            {"id": v["id"], "youtube_id": v["youtube_id"], "title": v["title"]}
            for v in videos if v.get("youtube_id")
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
    history = [s for s in sub_list() if s.get("status") != "pending"]

    active_count   = sum(1 for t in tracks if t.get("is_active", True))
    approved_count = sum(1 for s in history if s.get("status") == "approved")
    rejected_count = sum(1 for s in history if s.get("status") == "rejected")

    playlist_table = _video_table(
        tracks, "/admin/matt/toggle", "/admin/matt/rename", "/admin/matt/delete",
        show_submitter=True,
    )

    # ── Pending submissions ───────────────────────────────────────────────────
    if pending:
        sub_cards = ""
        for s in pending:
            ytid = s.get("youtube_id", "")
            note_html = f'<div style="margin-top:6px;color:#94a3b8;font-size:0.7rem;font-style:italic;">{s.get("note","")[:100]}</div>' if s.get("note") else ""
            sub_cards += f"""
            <div style="display:flex;gap:12px;align-items:flex-start;padding:12px 0;border-bottom:1px solid #1e293b;flex-wrap:wrap;">
                <a href="{_yt_url(ytid)}" target="_blank" rel="noopener" style="flex-shrink:0;">
                    <img src="{_yt_thumb(ytid)}" style="width:140px;height:79px;object-fit:cover;border-radius:4px;border:1px solid #1e293b;display:block;">
                </a>
                <div style="flex:1;min-width:180px;">
                    <div style="color:#e5e7eb;font-size:0.85rem;font-weight:bold;margin-bottom:4px;">{s['title']}</div>
                    <div style="color:#475569;font-size:0.7rem;margin-bottom:4px;">{ytid}</div>
                    <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
                        <span class="badge badge-blue">{s['player_name']}</span>
                        <span style="color:#475569;font-size:0.65rem;">#{s['player_id']}</span>
                        <span style="color:#475569;font-size:0.65rem;">{s.get('submitted_at','')[:16]}</span>
                    </div>
                    {note_html}
                    <div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:10px;">
                        <form action="/admin/matt/approve" method="post" style="display:inline;">
                            <input type="hidden" name="sub_id" value="{s['id']}">
                            <button class="btn btn-green">&#10003; Approve</button>
                        </form>
                        <form action="/admin/matt/reject" method="post" style="display:inline;">
                            <input type="hidden" name="sub_id" value="{s['id']}">
                            <button class="btn btn-red">&#10005; Reject</button>
                        </form>
                        <form action="/admin/matt/sub-delete" method="post" style="display:inline;"
                              onsubmit="return confirm('Delete this submission record?')">
                            <input type="hidden" name="sub_id" value="{s['id']}">
                            <button class="btn btn-gray">&#128465; Remove</button>
                        </form>
                    </div>
                </div>
            </div>"""
        sub_section = sub_cards
    else:
        sub_section = '<p style="color:#475569;padding:12px 0;">No pending submissions.</p>'

    # ── Submission history ────────────────────────────────────────────────────
    if history:
        hist_rows = ""
        for s in history:
            ytid = s.get("youtube_id", "")
            badge = (
                '<span class="badge badge-green">approved</span>'
                if s["status"] == "approved" else
                '<span class="badge badge-red">rejected</span>'
            )
            hist_rows += f"""
            <tr>
                <td>
                    <a href="{_yt_url(ytid)}" target="_blank" rel="noopener">
                        <img src="{_yt_thumb(ytid)}" style="width:72px;height:40px;object-fit:cover;border-radius:3px;display:block;border:1px solid #1e293b;">
                    </a>
                </td>
                <td style="color:#e5e7eb;">{s['title'][:65]}</td>
                <td style="color:#94a3b8;">{s['player_name']}</td>
                <td>{badge}</td>
                <td style="color:#475569;">{s.get('submitted_at','')[:16]}</td>
                <td style="text-align:right;">
                    <form action="/admin/matt/sub-delete" method="post" style="display:inline;"
                          onsubmit="return confirm('Remove this record?')">
                        <input type="hidden" name="sub_id" value="{s['id']}">
                        <button class="btn btn-gray">Remove</button>
                    </form>
                </td>
            </tr>"""
        hist_table = f"""
        <details style="margin-top:16px;">
            <summary style="color:#475569;font-size:0.75rem;cursor:pointer;user-select:none;padding:8px 0;list-style:none;">
                &#9654; Submission History &mdash; {len(history)} handled
                ({approved_count} approved, {rejected_count} rejected)
            </summary>
            <div style="margin-top:8px;" class="table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th>Video</th>
                            <th>Title</th>
                            <th>Player</th>
                            <th>Status</th>
                            <th>Date</th>
                            <th></th>
                        </tr>
                    </thead>
                    <tbody>{hist_rows}</tbody>
                </table>
            </div>
        </details>"""
    else:
        hist_table = ""

    # ── Pending section border color (urgent red when queue non-empty) ────────
    pending_border = "#7f1d1d" if pending else "#1e293b"
    pending_bg     = "#0d0404" if pending else "#0f172a"

    html = f"""
    <a href="/admin" style="color:#64748b;font-size:0.75rem;">&larr; Admin Dashboard</a>
    <div style="display:flex;align-items:center;gap:10px;margin:10px 0 4px 0;flex-wrap:wrap;">
        <h1 style="font-size:1.1rem;color:#f59e0b;margin:0;">&#128250; MATT &mdash; Channel 28</h1>
        <span class="badge badge-yellow">CH 28</span>
        <span style="color:#475569;font-size:0.75rem;">Community player videos &amp; streams</span>
    </div>

    {_banner(msg, err)}

    <div class="stat-grid" style="grid-template-columns:repeat(4,1fr);margin-bottom:16px;">
        <div class="stat-box">
            <div class="stat-value">{len(tracks)}</div>
            <div class="stat-label">Total Videos</div>
        </div>
        <div class="stat-box" style="border-color:#16a34a30;">
            <div class="stat-value" style="color:#4ade80;">{active_count}</div>
            <div class="stat-label">Active</div>
        </div>
        <div class="stat-box" style="border-color:{'#7f1d1d' if pending else '#1e293b'};">
            <div class="stat-value" style="color:{'#fca5a5' if pending else '#e5e7eb'};">{len(pending)}</div>
            <div class="stat-label">Pending Review</div>
        </div>
        <div class="stat-box">
            <div class="stat-value" style="color:#94a3b8;">{len(history)}</div>
            <div class="stat-label">Handled</div>
        </div>
    </div>

    <div class="card" style="border-color:{pending_border};background:{pending_bg};margin-bottom:16px;">
        <h3 style="color:#fca5a5;border-bottom-color:{pending_border};">
            &#128276; Pending Submissions
            {'<span class="badge badge-red" style="margin-left:8px;">' + str(len(pending)) + ' waiting</span>' if pending else ''}
        </h3>
        {sub_section}
        {hist_table}
    </div>

    <div class="card" style="border-color:#1e3a5f;margin-bottom:16px;">
        <h3 style="color:#93c5fd;">&#43; Add Video Directly to MATT</h3>
        <form id="mattAddForm" action="/admin/matt/add" method="post">
            <div class="form-row">
                <div>
                    <div class="form-label">YouTube URL or Video ID</div>
                    <input id="mattUrlInput" type="text" name="youtube_url" required
                           placeholder="https://youtube.com/watch?v=... or 11-char ID"
                           style="width:100%;">
                </div>
                <div>
                    <div class="form-label">Title</div>
                    <input type="text" name="title" required maxlength="120"
                           placeholder="Video title"
                           style="width:100%;">
                </div>
                <div>
                    <div class="form-label">&nbsp;</div>
                    <button type="submit" class="btn btn-blue" style="width:100%;">Add to MATT</button>
                </div>
            </div>
            <div id="mattUrlErr" style="display:none;color:#f87171;font-size:0.72rem;margin-top:4px;"></div>
        </form>
    </div>

    <div class="card">
        <h3>
            &#127909; MATT Playlist
            <span class="badge badge-green" style="margin-left:8px;">{active_count} active</span>
            <span class="badge badge-yellow" style="margin-left:4px;">{len(tracks) - active_count} hidden</span>
        </h3>
        {playlist_table}
    </div>

    {_RENAME_JS}
    """
    from admins_ux import admin_shell
    return HTMLResponse(admin_shell("MATT — CH 28 Playlist Manager", html, player.business_name, "/admin"))


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
    new_active: int = Form(...),
):
    _, redir = _admin_guard(session_token)
    if redir:
        return redir
    from maph_matt import matt_toggle
    matt_toggle(entry_id, bool(new_active))
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
