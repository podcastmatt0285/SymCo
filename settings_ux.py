"""
settings_ux.py — Player settings page.

GET /settings?tab=audio   — tabbed settings hub
Tabs: Audio (more can be added later)
"""

from typing import Optional
from fastapi import APIRouter, Cookie, Query
from fastapi.responses import HTMLResponse, RedirectResponse

router = APIRouter()

_TABS = [
    ("audio", "🎵 Audio"),
]


def _require_auth(session_token):
    try:
        import auth
        db = auth.get_db()
        player = auth.get_player_from_session(db, session_token)
        db.close()
        if not player:
            return RedirectResponse(url="/login", status_code=303)
        return player
    except Exception:
        return RedirectResponse(url="/login", status_code=303)


def _tab_bar(active: str) -> str:
    items = ""
    for key, label in _TABS:
        is_active = key == active
        color     = "#818cf8" if is_active else "#64748b"
        border    = f"border-bottom:2px solid #818cf8;" if is_active else "border-bottom:2px solid transparent;"
        items += (
            f'<a href="/settings?tab={key}" style="padding:10px 18px;{border}color:{color};'
            f'text-decoration:none;font-size:0.85rem;font-weight:{"bold" if is_active else "normal"};'
            f'white-space:nowrap;">{label}</a>'
        )
    return (
        f'<div style="display:flex;gap:0;border-bottom:1px solid #1e293b;margin-bottom:24px;overflow-x:auto;">'
        f'{items}</div>'
    )


def _audio_tab() -> str:
    return """
    <div style="max-width:560px;">

        <!-- Now Playing -->
        <div class="card" style="margin-bottom:20px;">
            <h3 style="margin:0 0 14px 0;color:#818cf8;">Now Playing</h3>
            <div style="display:flex;align-items:center;gap:14px;">
                <div style="font-size:2rem;">🎵</div>
                <div style="flex:1;min-width:0;">
                    <div id="st-now" style="color:#e5e7eb;font-weight:500;
                         white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
                        Loading…
                    </div>
                    <div style="color:#64748b;font-size:0.75rem;margin-top:2px;">Shuffle play</div>
                </div>
            </div>
            <!-- Transport controls -->
            <div style="display:flex;align-items:center;gap:10px;margin-top:16px;">
                <button id="st-pp" onclick="stToggle()"
                        style="background:#818cf8;border:none;color:#020617;
                               padding:8px 20px;border-radius:6px;font-weight:bold;
                               cursor:pointer;font-size:0.85rem;min-width:90px;">
                    ⏸ Pause
                </button>
                <button onclick="stSkip()"
                        style="background:#1e293b;border:1px solid #334155;color:#94a3b8;
                               padding:8px 14px;border-radius:6px;cursor:pointer;font-size:0.85rem;">
                    ⏭ Skip
                </button>
            </div>
        </div>

        <!-- Volume -->
        <div class="card" style="margin-bottom:20px;">
            <h3 style="margin:0 0 14px 0;">Volume</h3>
            <div style="display:flex;align-items:center;gap:12px;">
                <span style="color:#64748b;font-size:1.1rem;">🔈</span>
                <input id="st-vol" type="range" min="0" max="1" step="0.01"
                       oninput="stSetVol(this.value)"
                       style="flex:1;accent-color:#818cf8;cursor:pointer;height:6px;">
                <span style="color:#64748b;font-size:1.1rem;">🔊</span>
                <span id="st-vol-pct" style="color:#e5e7eb;font-size:0.8rem;min-width:36px;text-align:right;">
                    35%
                </span>
            </div>
        </div>

        <!-- Track List -->
        <div class="card">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
                <h3 style="margin:0;">Tracks</h3>
                <div style="display:flex;gap:8px;">
                    <button onclick="stSelectAll(true)"
                            style="background:#0f172a;border:1px solid #334155;color:#94a3b8;
                                   padding:4px 10px;font-size:0.75rem;cursor:pointer;border-radius:3px;">
                        Select All
                    </button>
                    <button onclick="stSelectAll(false)"
                            style="background:#0f172a;border:1px solid #334155;color:#94a3b8;
                                   padding:4px 10px;font-size:0.75rem;cursor:pointer;border-radius:3px;">
                        Deselect All
                    </button>
                </div>
            </div>
            <p style="color:#64748b;font-size:0.78rem;margin:0 0 12px 0;">
                Unchecked tracks are skipped during shuffle. Changes take effect immediately.
            </p>
            <div id="st-tracklist"
                 style="max-height:400px;overflow-y:auto;">
                <div style="color:#64748b;padding:20px 0;text-align:center;">Loading tracks…</div>
            </div>
        </div>

    </div>

    <script>
    (function() {
        var ST_KEY = 'wadsST';

        function getSt() {
            try { return JSON.parse(localStorage.getItem(ST_KEY) || '{}'); } catch(e) { return {}; }
        }

        // ── sync Now Playing label ──
        function stSyncNow() {
            var el = document.getElementById('st-now');
            var titleEl = document.getElementById('gs-title');
            if (el && titleEl) el.textContent = titleEl.textContent || '—';
        }
        window.stSyncNow = stSyncNow;

        // ── play/pause ──
        window.stToggle = function() {
            gsTogglePlay();
            setTimeout(stSyncUI, 80);
        };

        // ── skip ──
        window.stSkip = function() {
            gsNext();
            setTimeout(stSyncUI, 150);
        };

        function stSyncUI() {
            var audio  = document.getElementById('gs-audio');
            var ppBtn  = document.getElementById('st-pp');
            var volEl  = document.getElementById('st-vol');
            var pctEl  = document.getElementById('st-vol-pct');
            if (!audio) return;
            ppBtn.textContent = audio.paused ? '▶ Play' : '⏸ Pause';
            stSyncNow();
            var st = getSt();
            var vol = typeof st.volume === 'number' ? st.volume : 0.35;
            if (volEl) volEl.value = vol;
            if (pctEl) pctEl.textContent = Math.round(vol * 100) + '%';
        }

        // ── volume ──
        window.stSetVol = function(v) {
            gsSetVolume(v);
            // sync mini-bar slider
            var mini = document.getElementById('gs-vol');
            if (mini) mini.value = v;
            var pctEl = document.getElementById('st-vol-pct');
            if (pctEl) pctEl.textContent = Math.round(v * 100) + '%';
        };

        // ── track list ──
        function buildTrackList() {
            fetch('/soundtrack/list')
                .then(function(r) { return r.json(); })
                .then(function(tracks) {
                    var st = getSt();
                    var disabled = Array.isArray(st.disabledIds) ? st.disabledIds : [];
                    var el = document.getElementById('st-tracklist');
                    if (!tracks.length) {
                        el.innerHTML = '<div style="color:#64748b;padding:20px 0;text-align:center;">No tracks uploaded yet.</div>';
                        return;
                    }
                    el.innerHTML = tracks.map(function(t) {
                        var checked = disabled.indexOf(t.id) === -1 ? 'checked' : '';
                        return '<label style="display:flex;align-items:center;gap:10px;'
                            + 'padding:9px 4px;border-bottom:1px solid #0f172a;cursor:pointer;">'
                            + '<input type="checkbox" data-id="' + t.id + '" ' + checked
                            + ' onchange="gsSetTrackDisabled(' + t.id + ',!this.checked)"'
                            + ' style="accent-color:#818cf8;cursor:pointer;width:16px;height:16px;">'
                            + '<span style="color:#e5e7eb;flex:1;overflow:hidden;'
                            + 'text-overflow:ellipsis;white-space:nowrap;">' + t.title + '</span>'
                            + '</label>';
                    }).join('');
                })
                .catch(function() {
                    document.getElementById('st-tracklist').innerHTML =
                        '<div style="color:#64748b;padding:20px;text-align:center;">Could not load tracks.</div>';
                });
        }
        window.gsBuildTrackList = buildTrackList;

        window.stSelectAll = function(on) {
            document.querySelectorAll('#st-tracklist input[data-id]').forEach(function(cb) {
                var id = parseInt(cb.dataset.id);
                if (cb.checked !== on) {
                    cb.checked = on;
                    gsSetTrackDisabled(id, !on);
                }
            });
        };

        // ── init ──
        document.addEventListener('DOMContentLoaded', function() {
            stSyncUI();
            buildTrackList();
            // keep Now Playing in sync with audio events
            var audio = document.getElementById('gs-audio');
            if (audio) {
                audio.addEventListener('play',  stSyncNow);
                audio.addEventListener('ended', function() { setTimeout(stSyncNow, 200); });
            }
        });
    })();
    </script>
    """


@router.get("/settings", response_class=HTMLResponse)
def settings_page(
    session_token: Optional[str] = Cookie(None),
    tab: str = Query("audio"),
):
    player = _require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player

    # Validate tab
    valid_tabs = [k for k, _ in _TABS]
    if tab not in valid_tabs:
        tab = "audio"

    if tab == "audio":
        content = _audio_tab()
    else:
        content = '<p style="color:#64748b;">Coming soon.</p>'

    body = f"""
    <a href="/" style="color:#38bdf8;">&larr; Dashboard</a>
    <h1 style="margin:8px 0 4px 0;">Settings</h1>
    <p style="color:#64748b;margin-bottom:20px;">Manage your game preferences.</p>
    {_tab_bar(tab)}
    {content}
    """

    from ux import shell
    return HTMLResponse(shell("Settings", body, player.cash_balance, player.id))
