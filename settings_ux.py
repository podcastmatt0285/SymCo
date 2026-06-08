"""
settings_ux.py — Player settings page.

GET /settings?tab=audio   — tabbed settings hub
Tabs: Audio (more can be added later)

GET /api/deep-dives       — JSON list of audio deep dive entries from wiki_media.json
"""

import json
import os
from typing import Optional
from fastapi import APIRouter, Cookie, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse

router = APIRouter()

_TABS = [
    ("audio",         "🎵 Media"),
    ("tutorials",     "📖 Tutorials"),
    ("notifications", "🔔 Notifications"),
    ("widgets",       "📱 Widgets"),
    ("skins",         "🎨 Skins"),
    ("account",       "👤 Account"),
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


# ── Deep Dives API ────────────────────────────────────────────────────────────

@router.get("/api/deep-dives")
def api_deep_dives():
    """Return JSON array of audio deep dive entries from wiki_media.json."""
    try:
        path = os.path.join(os.path.dirname(__file__), "wiki_media.json")
        with open(path) as f:
            data = json.load(f)
        audio = data.get("audio", [])
        return JSONResponse([
            {"youtube_id": e["youtube_id"], "title": e["title"], "description": e.get("description", "")}
            for e in audio if e.get("youtube_id")
        ])
    except Exception:
        return JSONResponse([])


# ── Audio Tab ─────────────────────────────────────────────────────────────────

def _audio_tab() -> str:
    return """
<style>
#rp-wrap { max-width:760px; font-family:Georgia,'Times New Roman',serif; }
.rp-box {
    position:relative; background:#1A0F0A; border:8px solid #2D1810;
    border-radius:4px; box-shadow:0 40px 100px rgba(0,0,0,0.9);
    overflow:hidden; color:#F5F5DC;
    outline:1px solid rgba(176,141,87,0.3); outline-offset:-12px;
}
.rp-inlay {
    position:absolute; inset:4px; border:1px solid rgba(176,141,87,0.2);
    pointer-events:none; z-index:10; border-radius:2px;
}
.rp-header {
    height:80px; display:flex; flex-direction:column;
    align-items:center; justify-content:center;
    border-bottom:1px solid rgba(176,141,87,0.3);
    background:#241812; padding:0 24px; text-align:center;
}
.rp-station-row { display:flex; align-items:center; gap:12px; }
.rp-station-name {
    font-size:1rem; letter-spacing:0.15em; font-weight:900;
    color:#B08D57; text-transform:uppercase; margin:0;
}
.rp-slogan {
    height:18px; overflow:hidden; font-size:0.62rem; font-style:italic;
    opacity:0.4; text-transform:uppercase; letter-spacing:0.2em; color:#F5F5DC; margin-top:4px;
}
.rp-body {
    display:grid; grid-template-columns:200px 1fr;
    gap:24px; padding:24px;
}
.rp-left { display:flex; flex-direction:column; gap:16px; }
.rp-artwork {
    width:100%; aspect-ratio:1/1; background:black;
    border:2px solid rgba(166,124,0,0.3); border-radius:2px;
    overflow:hidden; display:flex; align-items:center; justify-content:center;
}
.rp-flower-svg {
    width:80%; height:80%;
    animation:rp-rose-sway 6s ease-in-out infinite; transform-origin:center;
}
.rp-trackinfo { border-top:1px solid rgba(176,141,87,0.15); padding-top:14px; }
.rp-track-label {
    font-size:0.55rem; letter-spacing:0.5em; text-transform:uppercase;
    color:#B08D57; font-weight:900; opacity:0.6; margin-bottom:4px;
}
.rp-track-title {
    font-size:0.95rem; font-style:italic; text-transform:uppercase;
    color:white; line-height:1.2; white-space:nowrap;
    overflow:hidden; text-overflow:ellipsis;
}
.rp-track-ref {
    font-size:0.6rem; opacity:0.3; text-transform:uppercase;
    letter-spacing:0.1em; font-weight:bold; color:#F5F5DC; margin-top:2px;
}
.rp-right { display:flex; flex-direction:column; gap:14px; min-width:0; }
.rp-waveform-wrap {
    background:rgba(0,0,0,0.4); border:1px solid rgba(176,141,87,0.1);
    border-radius:2px; padding:12px; position:relative; height:100px;
}
.rp-waveform-label {
    position:absolute; top:8px; left:12px; display:flex; align-items:center;
    gap:6px; opacity:0.3; font-size:0.55rem; text-transform:uppercase;
    letter-spacing:0.15em; color:#B08D57; pointer-events:none;
}
#rp-canvas { width:100%; height:100%; display:block; }
.rp-metrics { display:grid; grid-template-columns:repeat(3,1fr); gap:10px; }
.rp-metric { border-left:2px solid rgba(176,141,87,0.3); padding:4px 12px; }
.rp-metric-label {
    font-size:0.5rem; letter-spacing:0.12em; text-transform:uppercase;
    color:#B08D57; font-weight:900; margin-bottom:2px;
}
.rp-metric-value { font-size:0.85rem; color:#F5F5DC; }
.rp-metric-value.rp-green { color:#22c55e; }
.rp-metric-sub { font-size:0.5rem; text-transform:uppercase; opacity:0.3; font-weight:bold; color:#F5F5DC; }
.rp-controls {
    border-top:1px solid rgba(176,141,87,0.1); padding-top:14px;
    display:flex; align-items:center; gap:12px;
}
.rp-transport { display:flex; align-items:center; gap:10px; flex-shrink:0; }
.rp-pp-btn {
    width:48px; height:48px; border-radius:50%;
    border:1px solid rgba(176,141,87,0.5); background:#241812;
    color:#B08D57; font-size:1.2rem; cursor:pointer;
    display:flex; align-items:center; justify-content:center;
    transition:background 0.2s,color 0.2s;
}
.rp-pp-btn:hover { background:#B08D57; color:black; }
.rp-skip-btn {
    background:none; border:none; color:#B08D57; opacity:0.4;
    cursor:pointer; font-size:1.2rem; transition:opacity 0.2s; padding:0;
}
.rp-skip-btn:hover { opacity:1; }
.rp-progress-wrap { flex:1; min-width:0; }
.rp-progress-header {
    display:flex; justify-content:space-between; font-size:0.52rem;
    text-transform:uppercase; letter-spacing:0.15em; color:#B08D57; opacity:0.6; margin-bottom:6px;
}
.rp-progress-bar { height:2px; background:rgba(0,0,0,0.4); border-radius:999px; overflow:hidden; }
.rp-progress-fill {
    height:100%; background:linear-gradient(to right,#8B4513,#B08D57);
    width:0%; transition:width 0.5s linear;
}
.rp-side-controls { display:flex; align-items:center; gap:14px; flex-shrink:0; }
.rp-tuner { display:flex; flex-direction:column; align-items:center; gap:4px; cursor:pointer; user-select:none; }
.rp-knob {
    width:38px; height:38px; border-radius:50%;
    background:linear-gradient(to bottom,#3d2b1f,#1a0f0a);
    border:1px solid rgba(176,141,87,0.4); position:relative;
    cursor:pointer; box-shadow:0 2px 8px rgba(0,0,0,0.5);
    transition:transform 0.1s;
}
.rp-knob:active { transform:scale(0.93); }
.rp-knob-ind {
    position:absolute; top:4px; left:50%; width:4px; height:12px;
    background:#B08D57; border-radius:999px;
    transform:translateX(-50%) rotate(0deg);
    transform-origin:50% 100%; transition:transform 0.5s ease;
}
.rp-knob-lbl { font-size:0.52rem; text-transform:uppercase; color:#B08D57; font-weight:bold; letter-spacing:0.08em; }
.rp-vol-wrap { display:flex; flex-direction:column; align-items:center; gap:5px; }
.rp-mute-btn { background:none; border:none; color:#B08D57; opacity:0.5; cursor:pointer; font-size:0.95rem; transition:opacity 0.2s; padding:0; }
.rp-mute-btn:hover { opacity:1; }
#rp-vol-slider { width:58px; accent-color:#B08D57; cursor:pointer; }

/* Station panels */
.rp-panel { padding-top:12px; border-top:1px solid rgba(176,141,87,0.1); }
.rp-panel-hdr { font-size:0.58rem; text-transform:uppercase; letter-spacing:0.2em; color:#B08D57; opacity:0.6; margin-bottom:8px; }

/* Deep Dives list */
.rp-dive-item {
    display:flex; align-items:center; gap:10px; padding:8px 10px;
    border-radius:3px; cursor:pointer;
    border-bottom:1px solid rgba(176,141,87,0.06); transition:background 0.15s;
}
.rp-dive-item:hover { background:rgba(176,141,87,0.08); }
.rp-dive-item.rp-active { background:rgba(176,141,87,0.15); }
.rp-dive-num { font-size:0.6rem; color:#B08D57; opacity:0.6; min-width:18px; text-align:right; }
.rp-dive-title { flex:1; font-size:0.78rem; color:#F5F5DC; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.rp-dive-play { font-size:0.65rem; color:#B08D57; opacity:0.35; }
.rp-dive-item.rp-active .rp-dive-play { opacity:1; }

/* YT embed */
.rp-yt-wrap {
    position:relative; width:100%; padding-bottom:38%;
    background:black; border:1px solid rgba(176,141,87,0.15);
    border-radius:2px; overflow:hidden; margin-top:12px; display:none;
}
.rp-yt-wrap iframe { position:absolute; inset:0; width:100%; height:100%; border:none; }

/* Track list (WLOL) */
.rp-tracklist { max-height:200px; overflow-y:auto; }
.rp-track-row {
    display:flex; align-items:center; gap:10px; padding:8px 4px;
    border-bottom:1px solid rgba(176,141,87,0.06); cursor:pointer;
}
.rp-track-row input[type=checkbox] { accent-color:#B08D57; cursor:pointer; width:15px; height:15px; flex-shrink:0; }
.rp-track-name { flex:1; font-size:0.78rem; color:#F5F5DC; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.rp-tl-btns { display:flex; gap:6px; margin-bottom:8px; }
.rp-tl-btn {
    background:#0f172a; border:1px solid #334155; color:#94a3b8;
    padding:3px 9px; font-size:0.7rem; cursor:pointer; border-radius:3px;
}

/* Cog decoration */
.rp-cog {
    position:absolute; bottom:18px; left:18px; opacity:0.05;
    font-size:2.4rem; animation:rp-spin-slow 15s linear infinite;
    color:#B08D57; pointer-events:none; line-height:1;
}

@keyframes rp-rose-sway {
    0%,100% { transform:rotate(-2deg) scale(1); }
    50%      { transform:rotate(2deg)  scale(1.02); }
}
@keyframes rp-fade-slogan {
    0%   { opacity:0; transform:translateY(7px); }
    12%  { opacity:0.4; transform:translateY(0); }
    88%  { opacity:0.4; transform:translateY(0); }
    100% { opacity:0; transform:translateY(-7px); }
}
.rp-slogan-anim { animation:rp-fade-slogan 4s ease-in-out; }
@keyframes rp-spin-slow { from { transform:rotate(0deg); } to { transform:rotate(360deg); } }
@media(max-width:600px){.rp-body{grid-template-columns:1fr;}.rp-left{flex-direction:row;flex-wrap:wrap;gap:12px;}.rp-artwork{max-width:160px;}}
</style>

<div id="rp-wrap">
<div class="rp-box">
    <div class="rp-inlay"></div>

    <!-- Header -->
    <div class="rp-header">
        <div class="rp-station-row">
            <span id="rp-ico" style="color:#B08D57;font-size:1.1rem;">📻</span>
            <h2 class="rp-station-name" id="rp-sname">WCPR 104.1 &mdash; Wadsworth Carter Public Radio</h2>
        </div>
        <div class="rp-slogan"><span id="rp-slogan"></span></div>
    </div>

    <!-- Body -->
    <div class="rp-body">

        <!-- Left: artwork + track info -->
        <div class="rp-left">
            <div class="rp-artwork">
                <svg id="rp-flower" class="rp-flower-svg" viewBox="0 0 201.5 207.54" xmlns="http://www.w3.org/2000/svg">
                    <defs>
                        <linearGradient id="rpLg"><stop id="rpS1" stop-color="#F8BBD0" offset="0"/><stop id="rpS2" stop-color="#F8BBD0" stop-opacity="0" offset="1"/></linearGradient>
                        <radialGradient id="rpRg" xlink:href="#rpLg" gradientUnits="userSpaceOnUse" cy="172.36" cx="342.86" gradientTransform="matrix(1 0 0 1.0417 0 -7.1934)" r="193.09"/>
                    </defs>
                    <g transform="matrix(.15791 0 0 .15791 16.376 41.416)">
                        <path style="fill-rule:evenodd;fill:#2D5A27" d="m470.03 168.72c-34.81 0.55-75.98 25.14-120.23 80.45 287.24-187.49 318.09 308.34-234.97 802.83h105.53c11.37-10.2 22.06-19.9 30.58-28.8 404.11-366.71 376.62-856.94 219.09-854.48z"/>
                        <path style="fill-rule:evenodd;fill:#2D5A27" d="m834.13 625.57c77.98-166.27-189.49-144.42-409.81 189.81l-7.81-53.51c195.76-321.73 564.68-292.21 417.62-136.3z"/>
                        <path style="fill-rule:evenodd;fill:#2D5A27" d="m44.425 533.84c57.285-180.94 245.14 23.08 178.28 431.36l43.44-35.18c76.75-381.56-224.17-617.67-221.72-396.18z"/>
                        <g transform="translate(17.143 -148.57)">
                            <path id="rpP1" style="fill-rule:evenodd;transition:fill 3s ease-in-out" fill="#FFB7B2" d="m357.14 205.1c0.02 71.81-65.23 130.02-145.71 130.02-80.49 0-145.73-58.21-145.72-130.02-0.009-71.81 65.23-130.02 145.72-130.02 80.48-0.002 145.73 58.21 145.71 130.02z" transform="translate(219.15 -163.07)"/>
                            <path id="rpP2" style="fill-rule:evenodd;transition:fill 3s ease-in-out" fill="#FFB7B2" d="m357.14 205.1c0.02 71.81-65.23 130.02-145.71 130.02-80.49 0-145.73-58.21-145.72-130.02-0.009-71.81 65.23-130.02 145.72-130.02 80.48-0.002 145.73 58.21 145.71 130.02z" transform="translate(27.721 -188.78)"/>
                            <path id="rpP3" style="fill-rule:evenodd;transition:fill 3s ease-in-out" fill="#FFB7B2" d="m357.14 205.1c0.02 71.81-65.23 130.02-145.71 130.02-80.49 0-145.73-58.21-145.72-130.02-0.009-71.81 65.23-130.02 145.72-130.02 80.48-0.002 145.73 58.21 145.71 130.02z" transform="translate(-86.565 -45.925)"/>
                            <path id="rpP4" style="fill-rule:evenodd;transition:fill 3s ease-in-out" fill="#FFB7B2" d="m357.14 205.1c0.02 71.81-65.23 130.02-145.71 130.02-80.49 0-145.73-58.21-145.72-130.02-0.009-71.81 65.23-130.02 145.72-130.02 80.48-0.002 145.73 58.21 145.71 130.02z" transform="translate(256.29 14.075)"/>
                            <path id="rpP5" style="fill-rule:evenodd;transition:fill 3s ease-in-out" fill="#FFB7B2" d="m357.14 205.1c0.02 71.81-65.23 130.02-145.71 130.02-80.49 0-145.73-58.21-145.72-130.02-0.009-71.81 65.23-130.02 145.72-130.02 80.48-0.002 145.73 58.21 145.71 130.02z" transform="translate(150.58 151.22)"/>
                            <path id="rpP6" style="fill-rule:evenodd;transition:fill 3s ease-in-out" fill="#FFB7B2" d="m357.14 205.1c0.02 71.81-65.23 130.02-145.71 130.02-80.49 0-145.73-58.21-145.72-130.02-0.009-71.81 65.23-130.02 145.72-130.02 80.48-0.002 145.73 58.21 145.71 130.02z" transform="translate(-12.279 128.36)"/>
                            <path id="rpGrad" style="fill-rule:evenodd;transition:fill 3s ease-in-out" fill="url(#rpRg)" d="m500 300.93c-39.84 48.69-62.4-55.86-121.24-33.61s-6.6 115.57-68.68 105.42c-62.08-10.16 17.18-81.97-31.51-121.81-48.69-39.83-103.38 52.08-125.63-6.76-22.25-58.85 79.57-26.11 89.73-88.2 10.15-62.077-96.79-63.492-56.96-112.18 39.84-48.687 62.4 55.86 121.25 33.613 58.84-22.247 6.59-115.57 68.67-105.42 62.08 10.158-17.17 81.973 31.51 121.81 48.69 39.837 103.39-52.077 125.63 6.767 22.25 58.84-79.57 26.11-89.73 88.19-10.15 62.08 96.8 63.5 56.96 112.18z" transform="matrix(1.2126 0 0 1.2126 -107.6 -19.596)"/>
                            <path style="fill-rule:evenodd;fill:#ffd5d5" d="m514.29 249.39c0.01 44.19-33.25 80.02-74.29 80.02s-74.3-35.83-74.29-80.02c-0.01-44.2 33.25-80.03 74.29-80.03s74.3 35.83 74.29 80.03z" transform="translate(-131.87 -59.983)"/>
                        </g>
                        <g transform="matrix(.37085 .64112 -.64112 .37085 1004.3 1085.6)">
                            <path style="fill-rule:evenodd;fill:#00ff00" d="m-514.29 660.81s-168.57-82.85-5.71-242.85 162.86-154.29 162.86-154.29 97.14 128.57 51.43 242.86c-45.72 114.28-205.72 154.28-208.58 154.28z" transform="translate(-129.42 -54.497)"/>
                            <path style="fill-rule:evenodd;fill:#2D5A27" d="m-385.71 357.96l-148.58 365.71h45.72l102.86-365.71z" transform="translate(-129.42 -54.497)"/>
                        </g>
                    </g>
                </svg>
            </div>

            <div class="rp-trackinfo">
                <div class="rp-track-label" id="rp-track-lbl">Tuning in</div>
                <div class="rp-track-title" id="rp-title">—</div>
                <div class="rp-track-ref" id="rp-ref"></div>
            </div>
        </div>

        <!-- Right: waveform + metrics + controls + station panel -->
        <div class="rp-right">

            <!-- Waveform -->
            <div class="rp-waveform-wrap">
                <div class="rp-waveform-label">&#128246; Broadcast Signal</div>
                <canvas id="rp-canvas"></canvas>
            </div>

            <!-- Metrics -->
            <div class="rp-metrics">
                <div class="rp-metric">
                    <div class="rp-metric-label">Library</div>
                    <div class="rp-metric-value" id="rp-m1">—</div>
                    <div class="rp-metric-sub">Tracks</div>
                </div>
                <div class="rp-metric">
                    <div class="rp-metric-label">Signal</div>
                    <div class="rp-metric-value rp-green">Strong</div>
                    <div class="rp-metric-sub">Status</div>
                </div>
                <div class="rp-metric">
                    <div class="rp-metric-label">Frequency</div>
                    <div class="rp-metric-value" id="rp-m3">104.1 FM</div>
                    <div class="rp-metric-sub">Station</div>
                </div>
            </div>

            <!-- Transport controls -->
            <div class="rp-controls">
                <div class="rp-transport">
                    <button class="rp-pp-btn" id="rp-pp" onclick="rpToggle()">&#9654;</button>
                    <button class="rp-skip-btn" onclick="rpSkip()">&#9197;</button>
                </div>

                <div class="rp-progress-wrap">
                    <div class="rp-progress-header">
                        <span>Playback Sync</span>
                        <span id="rp-time">—</span>
                    </div>
                    <div class="rp-progress-bar">
                        <div class="rp-progress-fill" id="rp-pfill"></div>
                    </div>
                </div>

                <div class="rp-side-controls">
                    <!-- Tuner knob -->
                    <div class="rp-tuner" onclick="rpSwitchStation()">
                        <div class="rp-knob">
                            <div class="rp-knob-ind" id="rp-kind"></div>
                        </div>
                        <span class="rp-knob-lbl" id="rp-klbl">WCPR</span>
                    </div>
                    <!-- Volume -->
                    <div class="rp-vol-wrap">
                        <button class="rp-mute-btn" id="rp-mute" onclick="rpMute()">&#128266;</button>
                        <input type="range" id="rp-vol" min="0" max="100" value="35"
                               oninput="rpSetVol(parseInt(this.value))" style="width:56px;accent-color:#B08D57;cursor:pointer;">
                    </div>
                </div>
            </div>

            <!-- WCPR panel: episode list -->
            <div class="rp-panel" id="rp-wcpr-panel">
                <div class="rp-panel-hdr">&#128251; Talk Radio Episodes</div>
                <div id="rp-dives-list" class="rp-tracklist">
                    <div style="color:#64748b;font-size:0.75rem;padding:12px 0;text-align:center;">Loading episodes…</div>
                </div>
            </div>

            <!-- WLOL panel: track list -->
            <div class="rp-panel" id="rp-wlol-panel" style="display:none;">
                <div class="rp-panel-hdr">&#127925; Music Playlist</div>
                <div class="rp-tl-btns">
                    <button class="rp-tl-btn" onclick="rpSelectAll(true)">Select All</button>
                    <button class="rp-tl-btn" onclick="rpSelectAll(false)">Deselect All</button>
                </div>
                <div style="color:#64748b;font-size:0.7rem;margin-bottom:8px;">
                    Unchecked tracks are skipped during shuffle. Changes take effect immediately.
                </div>
                <div id="rp-tracks-list" class="rp-tracklist">
                    <div style="color:#64748b;font-size:0.75rem;padding:12px 0;text-align:center;">Loading tracks…</div>
                </div>
            </div>

        </div>
    </div>
    <audio id="wcpr-audio" preload="none" style="display:none;"></audio>
    <div class="rp-cog">&#9881;</div>
</div>
</div>

<script>
(function() {

    var PASTELS = [
        "#FFB7B2","#FFDAC1","#E2F0CB","#B5EAD7","#C7CEEA",
        "#FF9AA2","#F8BBD0","#E1BEE7","#D1C4E9","#BBDEFB",
        "#C8E6C9","#F0F4C3","#FFF9C4","#FFE0B2","#F5F5DC"
    ];

    var SLOGANS = [
        "Dream big, work hard.","The sky is the limit.","Believe in yourself.",
        "Seize the day.","Make it happen.","Stay hungry, stay foolish.",
        "Innovation distinguishes leaders.","The best is yet to come.",
        "Focus on the goal.","Everything you imagine is real.",
        "Turn your wounds into wisdom.","Be the change.",
        "Action is the key to success.","Don't wait for opportunity, create it.",
        "Your time is limited.","Follow your heart.","Stay positive.",
        "Work hard in silence.","Success is a journey.","Be original.",
        "Never give up.","Chase your dreams.","Limitless potential.",
        "Mindset is everything.","Prove them wrong.","Good things take time.",
        "Focus on the good.","Be fearless.","The only way out is through.",
        "Rise and grind.","Consistency is key.","Keep moving forward.",
        "Life is what you make it.","Greatness takes time.","Push your limits.",
        "Build your empire.","Vision without action is a dream.",
        "Make every day count.","Lead with purpose.",
        "Excellence is not an act, but a habit.","The power of now.",
        "Unlock your potential.",
        "Great things never come from comfort zones.",
        "Do what you love.","Small steps, big results.",
        "Radiate positivity.","Your only limit is you.",
        "Keep the dream alive.","Focus on your vision.",
        "Success favors the bold."
    ];

    // ── State ────────────────────────────────────────────────────────────────
    var rpStation   = 'wcpr';
    var rpPlaying   = false;
    var rpVolume    = 35;
    var rpMuted     = false;
    var rpSloganIdx = 0;
    var wcprTracks  = [];
    var wcprIdx     = -1;
    var wcprAudio   = null;

    // ── DOM refs ─────────────────────────────────────────────────────────────
    var $ = function(id) { return document.getElementById(id); };

    // ── Helpers ──────────────────────────────────────────────────────────────
    function randPastel() { return PASTELS[Math.floor(Math.random() * PASTELS.length)]; }

    function fmtTime(s) {
        s = Math.floor(s || 0);
        var m = Math.floor(s / 60), sec = s % 60;
        return m + ':' + (sec < 10 ? '0' : '') + sec;
    }

    // ── Petal color cycling ──────────────────────────────────────────────────
    function cyclePetals() {
        var c = randPastel();
        ['rpP1','rpP2','rpP3','rpP4','rpP5','rpP6'].forEach(function(id) {
            var el = document.getElementById(id);
            if (el) el.setAttribute('fill', c);
        });
        var s1 = $('rpS1'), s2 = $('rpS2');
        if (s1) s1.setAttribute('stop-color', randPastel());
        if (s2) s2.setAttribute('stop-color', randPastel());
    }
    setInterval(cyclePetals, 5000);

    // ── Slogan ticker ────────────────────────────────────────────────────────
    function nextSlogan() {
        var el = $('rp-slogan');
        if (!el) return;
        rpSloganIdx = (rpSloganIdx + 1) % SLOGANS.length;
        el.textContent = '"' + SLOGANS[rpSloganIdx] + '"';
        el.classList.remove('rp-slogan-anim');
        void el.offsetHeight;
        el.classList.add('rp-slogan-anim');
    }

    // ── Waveform ─────────────────────────────────────────────────────────────
    var waveOff = 0;
    function drawWave() {
        var canvas = $('rp-canvas');
        if (!canvas) return;
        var ctx = canvas.getContext('2d');
        var W = canvas.width, H = canvas.height, mid = H / 2;
        ctx.clearRect(0, 0, W, H);
        ctx.strokeStyle = 'rgba(197,160,89,0.05)';
        ctx.lineWidth = 1;
        for (var i = 0; i < W; i += 20) {
            ctx.beginPath(); ctx.moveTo(i, 0); ctx.lineTo(i, H); ctx.stroke();
        }
        var amp = rpPlaying ? (20 * (rpMuted ? 0.1 : rpVolume / 100)) : 4;
        ctx.beginPath();
        ctx.strokeStyle = '#B08D57';
        ctx.lineWidth = 1.5;
        ctx.moveTo(0, mid);
        for (var x = 0; x < W; x++) {
            var y = mid + Math.sin(x * 0.02 + waveOff) * amp
                       + Math.sin(x * 0.01 + waveOff * 0.5) * (amp * 0.5);
            ctx.lineTo(x, y);
        }
        ctx.stroke();
        waveOff += rpPlaying ? 0.05 : 0.01;
        requestAnimationFrame(drawWave);
    }

    // ── Station switch ───────────────────────────────────────────────────────
    window.rpSwitchStation = function() {
        rpStation = (rpStation === 'wcpr') ? 'wlol' : 'wcpr';
        var isWlol = (rpStation === 'wlol');

        var kind = $('rp-kind'), klbl = $('rp-klbl');
        if (kind) kind.style.transform = 'translateX(-50%) rotate(' + (isWlol ? 180 : 0) + 'deg)';
        if (klbl) klbl.textContent = isWlol ? 'WLOL' : 'WCPR';

        var ico = $('rp-ico'), sname = $('rp-sname');
        if (ico)   ico.textContent   = isWlol ? '🎵' : '📻';
        if (sname) sname.innerHTML   = isWlol
            ? 'WLOL 92.8 &mdash; Listen Out Loud'
            : 'WCPR 104.1 &mdash; Wadsworth Carter Public Radio';

        var m3 = $('rp-m3');
        if (m3) m3.textContent = isWlol ? '92.8 FM' : '104.1 FM';

        var wcprPanel = $('rp-wcpr-panel'), wlolPanel = $('rp-wlol-panel');
        if (wcprPanel) wcprPanel.style.display = isWlol ? 'none' : 'block';
        if (wlolPanel) wlolPanel.style.display = isWlol ? 'block' : 'none';

        // Pause on station change
        if (rpPlaying) {
            if (!isWlol) {
                try { gsTogglePlay(); } catch(e) {}
            } else {
                wcprPause();
            }
            rpPlaying = false;
        }

        rpUpdateUI();
        if (isWlol) { rpSyncWlol(); rpBuildTrackList(); }
        else        { wcprBuildList(); }
    };

    // ── UI sync ──────────────────────────────────────────────────────────────
    function rpUpdateUI() {
        var btn = $('rp-pp');
        if (btn) btn.innerHTML = rpPlaying ? '&#9646;&#9646;' : '&#9654;';
    }

    // ── WLOL ─────────────────────────────────────────────────────────────────
    function rpSyncWlol() {
        var audio = document.getElementById('gs-audio');
        var titleEl = document.getElementById('gs-title');
        if (!audio) return;
        rpPlaying = !audio.paused;
        var title = $('rp-title'), ref = $('rp-ref'), lbl = $('rp-track-lbl');
        if (title) title.textContent = (titleEl && titleEl.textContent) ? titleEl.textContent : '—';
        if (ref)   ref.textContent   = 'WLOL \u00B7 Shuffle Play';
        if (lbl)   lbl.textContent   = 'Now Playing';
        rpUpdateUI();
    }

    function rpSyncWlolProgress() {
        var audio = document.getElementById('gs-audio');
        if (!audio || !audio.duration) return;
        var pct = (audio.currentTime / audio.duration) * 100;
        var fill = $('rp-pfill'), time = $('rp-time');
        if (fill) fill.style.width = pct.toFixed(1) + '%';
        if (time) time.textContent = fmtTime(audio.currentTime) + ' / ' + fmtTime(audio.duration);
    }

    // ── Track list (WLOL) ────────────────────────────────────────────────────
    function rpBuildTrackList() {
        var list = $('rp-tracks-list');
        if (!list) return;
        fetch('/soundtrack/list')
            .then(function(r) { return r.json(); })
            .then(function(tracks) {
                var m1 = $('rp-m1');
                if (m1) m1.textContent = tracks.length + ' tracks';
                var st = {};
                try { st = JSON.parse(localStorage.getItem('wadsST') || '{}'); } catch(e) {}
                var disabled = Array.isArray(st.disabledIds) ? st.disabledIds : [];
                if (!tracks.length) {
                    list.innerHTML = '<div style="color:#64748b;font-size:0.75rem;padding:12px 0;text-align:center;">No tracks uploaded yet.</div>';
                    return;
                }
                list.innerHTML = tracks.map(function(t) {
                    var chk = disabled.indexOf(t.id) === -1 ? 'checked' : '';
                    return '<label class="rp-track-row">'
                        + '<input type="checkbox" data-id="' + t.id + '" ' + chk
                        + ' onchange="gsSetTrackDisabled(' + t.id + ',!this.checked)">'
                        + '<span class="rp-track-name">' + t.title + '</span>'
                        + '</label>';
                }).join('');
            })
            .catch(function() {
                if (list) list.innerHTML = '<div style="color:#64748b;font-size:0.75rem;padding:12px 0;text-align:center;">Could not load tracks.</div>';
            });
    }

    window.rpSelectAll = function(on) {
        document.querySelectorAll('#rp-tracks-list input[data-id]').forEach(function(cb) {
            var id = parseInt(cb.dataset.id);
            if (cb.checked !== on) { cb.checked = on; gsSetTrackDisabled(id, !on); }
        });
    };

    // ── Play / Pause ─────────────────────────────────────────────────────────
    window.rpToggle = function() {
        if (rpStation === 'wlol') {
            try { gsTogglePlay(); } catch(e) {}
            setTimeout(rpSyncWlol, 80);
        } else {
            wcprToggle();
        }
    };

    // ── Skip ─────────────────────────────────────────────────────────────────
    window.rpSkip = function() {
        if (rpStation === 'wlol') {
            try { gsNext(); } catch(e) {}
            setTimeout(rpSyncWlol, 200);
        } else {
            if (wcprTracks.length) {
                wcprLoad((wcprIdx + 1) % wcprTracks.length);
            }
        }
    };

    // ── Volume ───────────────────────────────────────────────────────────────
    window.rpSetVol = function(v) {
        rpVolume = v; rpMuted = (v === 0);
        var btn = $('rp-mute');
        if (btn) btn.innerHTML = rpMuted ? '&#128263;' : '&#128266;';
        if (rpStation === 'wlol') {
            try { gsSetVolume(v / 100); } catch(e) {}
            var mini = document.getElementById('gs-vol');
            if (mini) mini.value = v / 100;
        } else {
            if (wcprAudio) wcprAudio.volume = (rpMuted ? 0 : v) / 100;
        }
    };

    window.rpMute = function() {
        var vol = $('rp-vol');
        if (rpMuted) {
            rpMuted = false; rpVolume = rpVolume || 35;
            if (vol) vol.value = rpVolume;
            window.rpSetVol(rpVolume);
        } else {
            rpMuted = true;
            var btn = $('rp-mute');
            if (btn) btn.innerHTML = '&#128263;';
            if (rpStation === 'wlol') { try { gsSetVolume(0); } catch(e) {} }
            else { if (wcprAudio) wcprAudio.volume = 0; }
        }
    };

    // ── WCPR native audio ────────────────────────────────────────────────────
    function wcprLoad(idx) {
        if (!wcprTracks.length || idx < 0 || idx >= wcprTracks.length) return;
        wcprIdx = idx;
        var track = wcprTracks[idx];

        document.querySelectorAll('.rp-dive-item').forEach(function(el, i) {
            el.classList.toggle('rp-active', i === idx);
        });

        var title = $('rp-title'), ref = $('rp-ref'), lbl = $('rp-track-lbl');
        if (title) title.textContent = track.title;
        if (ref)   ref.textContent   = 'WCPR 104.1 \u00B7 Talk Radio';
        if (lbl)   lbl.textContent   = 'Now Playing';

        if (wcprAudio) {
            wcprAudio.src    = track.url;
            wcprAudio.volume = (rpMuted ? 0 : rpVolume) / 100;
            wcprAudio.play().catch(function() {});
        }
        rpPlaying = true;
        rpUpdateUI();
    }

    function wcprToggle() {
        if (!wcprAudio) return;
        if (wcprTracks.length && wcprIdx < 0) { wcprLoad(0); return; }
        if (wcprAudio.paused) { wcprAudio.play().catch(function() {}); rpPlaying = true; }
        else                  { wcprAudio.pause(); rpPlaying = false; }
        rpUpdateUI();
    }

    function wcprPause() {
        if (wcprAudio && !wcprAudio.paused) wcprAudio.pause();
        rpPlaying = false;
        rpUpdateUI();
    }

    // ── WCPR track list builder ──────────────────────────────────────────────
    function wcprBuildList() {
        var list = $('rp-dives-list');
        if (!list) return;
        fetch('/wcpr/list')
            .then(function(r) { return r.json(); })
            .then(function(tracks) {
                wcprTracks = tracks || [];
                var m1 = $('rp-m1');
                if (m1 && rpStation === 'wcpr') m1.textContent = wcprTracks.length + ' episodes';
                if (!wcprTracks.length) {
                    list.innerHTML = '<div style="color:#64748b;font-size:0.75rem;padding:12px 0;text-align:center;font-style:italic;">'
                        + 'No episodes uploaded yet.<br><span style="font-size:0.65rem;opacity:0.6;">Admins can upload at /admin/wcpr</span></div>';
                    return;
                }
                list.innerHTML = wcprTracks.map(function(t, i) {
                    return '<div class="rp-dive-item" onclick="wcprLoad(' + i + ')">'
                        + '<span class="rp-dive-num">' + (i + 1) + '</span>'
                        + '<span class="rp-dive-title">' + t.title + '</span>'
                        + '<span class="rp-dive-play">&#9654;</span>'
                        + '</div>';
                }).join('');
            })
            .catch(function() {
                if (list) list.innerHTML = '<div style="color:#64748b;font-size:0.75rem;padding:12px 0;text-align:center;">Could not load episodes.</div>';
            });
    }

    // ── Init ─────────────────────────────────────────────────────────────────
    document.addEventListener('DOMContentLoaded', function() {

        // WCPR audio element
        wcprAudio = $('wcpr-audio');
        if (wcprAudio) {
            wcprAudio.addEventListener('ended', function() {
                if (wcprTracks.length) wcprLoad((wcprIdx + 1) % wcprTracks.length);
                else { rpPlaying = false; rpUpdateUI(); }
            });
            wcprAudio.addEventListener('play',  function() { rpPlaying = true;  rpUpdateUI(); });
            wcprAudio.addEventListener('pause', function() { rpPlaying = false; rpUpdateUI(); });
        }

        // Canvas sizing
        var canvas = $('rp-canvas');
        if (canvas) {
            var wrap = canvas.parentElement;
            canvas.width  = wrap ? (wrap.offsetWidth  || 500) : 500;
            canvas.height = wrap ? (wrap.offsetHeight || 90)  : 90;
        }

        // Initial slogan
        var slogan = $('rp-slogan');
        if (slogan) {
            slogan.textContent = '"' + SLOGANS[rpSloganIdx] + '"';
            slogan.classList.add('rp-slogan-anim');
        }

        // Volume from saved state
        try {
            var st = JSON.parse(localStorage.getItem('wadsST') || '{}');
            if (typeof st.volume === 'number') {
                rpVolume = Math.round(st.volume * 100);
                var vol = $('rp-vol');
                if (vol) vol.value = rpVolume;
            }
        } catch(e) {}

        // Load data
        wcprBuildList();

        // Start waveform
        drawWave();

        // Slogan rotation
        setInterval(nextSlogan, 4000);

        // Progress sync loop
        setInterval(function() {
            if (rpStation === 'wlol') {
                rpSyncWlolProgress();
            } else if (wcprAudio && wcprAudio.duration) {
                var pct = (wcprAudio.currentTime / wcprAudio.duration) * 100;
                var fill = $('rp-pfill'), time = $('rp-time');
                if (fill) fill.style.width = pct.toFixed(1) + '%';
                if (time) time.textContent = fmtTime(wcprAudio.currentTime) + ' / ' + fmtTime(wcprAudio.duration);
            }
        }, 1000);

        // Hook into WLOL audio element events
        var audio = document.getElementById('gs-audio');
        if (audio) {
            audio.addEventListener('play',  function() { if (rpStation === 'wlol') { rpPlaying = true;  rpUpdateUI(); } });
            audio.addEventListener('pause', function() { if (rpStation === 'wlol') { rpPlaying = false; rpUpdateUI(); } });
            audio.addEventListener('ended', function() { if (rpStation === 'wlol') setTimeout(rpSyncWlol, 200); });
        }

        // Expose track list builder for shell compatibility
        window.gsBuildTrackList = rpBuildTrackList;
    });

})();
</script>

<!-- ═══════════════════════════════════════════════════════════════
     MAPH / MATT — Video Channels  (same visual language as the radio)
     MAPH = Markets, Analytics & Player Help  (CH 46)
     MATT = Market Action Trading Theater     (CH 28)
     ═══════════════════════════════════════════════════════════════ -->
<style>
#mm-wrap { max-width:760px; font-family:Georgia,'Times New Roman',serif; }

/* Outer box — identical properties to the radio */
.mm-box {
    position:relative; background:#1A0F0A; border:8px solid #2D1810;
    border-radius:4px; box-shadow:0 40px 100px rgba(0,0,0,0.9);
    overflow:hidden; color:#F5F5DC;
    outline:1px solid rgba(176,141,87,0.3); outline-offset:-12px;
}
.mm-inlay {
    position:absolute; inset:4px; border:1px solid rgba(176,141,87,0.2);
    pointer-events:none; z-index:20; border-radius:2px;
}

/* Header — identical to .rp-header */
.mm-header {
    height:80px; display:flex; flex-direction:column;
    align-items:center; justify-content:center;
    border-bottom:1px solid rgba(176,141,87,0.3);
    background:#241812; padding:0 24px; text-align:center;
}
.mm-station-row { display:flex; align-items:center; gap:12px; }
.mm-station-name {
    font-size:1rem; letter-spacing:0.15em; font-weight:900;
    color:#B08D57; text-transform:uppercase; margin:0;
}
.mm-slogan {
    height:18px; overflow:hidden; font-size:0.62rem; font-style:italic;
    opacity:0.4; text-transform:uppercase; letter-spacing:0.2em;
    color:#F5F5DC; margin-top:4px;
}

/* Body — identical grid to .rp-body */
.mm-body {
    display:grid; grid-template-columns:200px 1fr;
    gap:24px; padding:24px;
}
.mm-left { display:flex; flex-direction:column; gap:16px; }

/* Channel art (replaces album artwork) */
.mm-artwork {
    width:100%; aspect-ratio:1/1; background:black;
    border:2px solid rgba(166,124,0,0.3); border-radius:2px;
    overflow:hidden; display:flex; align-items:center; justify-content:center;
    position:relative;
}
.mm-artwork::before {
    content:''; position:absolute; width:110%; height:110%;
    border:1px solid rgba(176,141,87,0.12); border-radius:50%;
    animation:mm-spin-slow 22s linear infinite;
}
.mm-artwork::after {
    content:''; position:absolute; width:70%; height:70%;
    border:1px solid rgba(176,141,87,0.08); border-radius:50%;
    animation:mm-spin-slow 16s linear infinite reverse;
}
.mm-ch-num {
    font-size:3rem; font-weight:900; line-height:1;
    font-family:'JetBrains Mono','Courier New',monospace;
    color:rgba(176,141,87,0.7);
    text-shadow:0 0 30px rgba(176,141,87,0.3);
    animation:mm-art-pulse 5s ease-in-out infinite; z-index:1;
    display:flex; flex-direction:column; align-items:center;
}
.mm-ch-call {
    font-size:0.52rem; letter-spacing:0.4em; font-weight:900;
    color:rgba(176,141,87,0.5); text-transform:uppercase;
    font-family:'JetBrains Mono','Courier New',monospace; margin-top:6px;
}

/* Track info (identical to .rp-trackinfo) */
.mm-trackinfo { border-top:1px solid rgba(176,141,87,0.15); padding-top:14px; }
.mm-track-label {
    font-size:0.55rem; letter-spacing:0.5em; text-transform:uppercase;
    color:#B08D57; font-weight:900; opacity:0.6; margin-bottom:4px;
}
.mm-track-title {
    font-size:0.95rem; font-style:italic; text-transform:uppercase;
    color:white; line-height:1.2; white-space:nowrap;
    overflow:hidden; text-overflow:ellipsis;
}
.mm-track-ref {
    font-size:0.6rem; opacity:0.3; text-transform:uppercase;
    letter-spacing:0.1em; font-weight:bold; color:#F5F5DC; margin-top:2px;
}

/* Right column */
.mm-right { display:flex; flex-direction:column; gap:14px; min-width:0; }

/* Screen (replaces waveform canvas) */
.mm-screen-wrap {
    background:rgba(0,0,0,0.4); border:1px solid rgba(176,141,87,0.1);
    border-radius:2px; position:relative; aspect-ratio:16/9; overflow:hidden;
}
.mm-screen-wrap::after {
    content:''; position:absolute; inset:0; pointer-events:none; z-index:15;
    background:repeating-linear-gradient(
        0deg, transparent, transparent 2px, rgba(0,0,0,0.05) 2px, rgba(0,0,0,0.05) 4px
    );
}
.mm-static {
    position:absolute; inset:0; z-index:10;
    background:#000; display:flex; align-items:center; justify-content:center;
}
.mm-static canvas { width:100%; height:100%; }
#mmYtContainer { position:absolute; inset:0; z-index:5; }
#mmYtContainer iframe { position:absolute; inset:0; width:100%; height:100%; border:0; }
.mm-ch-badge {
    position:absolute; top:8px; left:10px; z-index:16;
    background:rgba(0,0,0,0.7); border:1px solid rgba(176,141,87,0.25);
    border-radius:3px; padding:2px 7px;
    font-family:'JetBrains Mono','Courier New',monospace;
    font-size:0.62rem; font-weight:700; letter-spacing:0.1em; color:#B08D57;
}
.mm-watermark {
    position:absolute; bottom:8px; right:10px; z-index:16;
    opacity:0.65; pointer-events:none;
}
.mm-watermark-logo {
    width:26px; height:26px; border-radius:50%;
    display:flex; align-items:center; justify-content:center;
    font-size:0.46rem; font-weight:900; letter-spacing:0.05em;
    font-family:'JetBrains Mono','Courier New',monospace;
    color:#fff; text-shadow:0 1px 3px rgba(0,0,0,0.9);
}
.mm-wm-maph .mm-watermark-logo { background:radial-gradient(circle at 35% 35%,#6366f1,#312e81); }
.mm-wm-matt .mm-watermark-logo { background:radial-gradient(circle at 35% 35%,#f59e0b,#92400e); }

/* Metrics (identical to .rp-metrics) */
.mm-metrics { display:grid; grid-template-columns:repeat(3,1fr); gap:10px; }
.mm-metric { border-left:2px solid rgba(176,141,87,0.3); padding:4px 12px; }
.mm-metric-label {
    font-size:0.5rem; letter-spacing:0.12em; text-transform:uppercase;
    color:#B08D57; font-weight:900; margin-bottom:2px;
}
.mm-metric-value { font-size:0.85rem; color:#F5F5DC; }
.mm-metric-value.mm-green { color:#22c55e; }
.mm-metric-sub { font-size:0.5rem; text-transform:uppercase; opacity:0.3; font-weight:bold; color:#F5F5DC; }

/* Transport controls (identical to .rp-controls) */
.mm-controls {
    border-top:1px solid rgba(176,141,87,0.1); padding-top:14px;
    display:flex; align-items:center; gap:12px;
}
.mm-transport { display:flex; align-items:center; gap:10px; flex-shrink:0; }
.mm-pp-btn {
    width:48px; height:48px; border-radius:50%;
    border:1px solid rgba(176,141,87,0.5); background:#241812;
    color:#B08D57; font-size:1.2rem; cursor:pointer;
    display:flex; align-items:center; justify-content:center;
    transition:background 0.2s,color 0.2s;
}
.mm-pp-btn:hover { background:#B08D57; color:black; }
.mm-skip-btn {
    background:none; border:none; color:#B08D57; opacity:0.4;
    cursor:pointer; font-size:1.2rem; transition:opacity 0.2s; padding:0;
}
.mm-skip-btn:hover { opacity:1; }
.mm-prog-wrap { flex:1; min-width:0; }
.mm-prog-header {
    display:flex; justify-content:space-between; font-size:0.52rem;
    text-transform:uppercase; letter-spacing:0.15em; color:#B08D57; opacity:0.6; margin-bottom:6px;
}
.mm-prog-bar { height:2px; background:rgba(0,0,0,0.4); border-radius:999px; overflow:hidden; }
.mm-prog-fill {
    height:100%; background:linear-gradient(to right,#8B4513,#B08D57);
    width:0%; transition:width 0.5s linear;
}

/* Channel tuner (replaces the dial knob) */
.mm-tuner { display:flex; flex-direction:column; align-items:center; gap:4px; flex-shrink:0; }
.mm-tuner-row { display:flex; gap:5px; }
.mm-tuner-btn {
    background:#241812; border:1px solid rgba(176,141,87,0.35); color:#B08D57;
    border-radius:3px; padding:5px 10px; font-size:0.72rem; cursor:pointer;
    font-family:Georgia,serif; transition:background 0.2s,color 0.2s,border-color 0.2s;
    user-select:none; letter-spacing:0.04em;
}
.mm-tuner-btn:hover { background:#B08D57; color:#1A0F0A; }
.mm-tuner-btn.mm-on-maph { background:#1e1b4b; border-color:#6366f1; color:#a5b4fc; }
.mm-tuner-btn.mm-on-matt { background:#1c1007; border-color:#d97706; color:#fcd34d; }
.mm-tuner-lbl {
    font-size:0.52rem; text-transform:uppercase; color:#B08D57;
    font-weight:bold; letter-spacing:0.08em;
}

/* Playlist panel (identical to .rp-panel) */
.mm-panel { padding-top:12px; border-top:1px solid rgba(176,141,87,0.1); }
.mm-panel-hdr {
    font-size:0.58rem; text-transform:uppercase; letter-spacing:0.2em;
    color:#B08D57; opacity:0.6; margin-bottom:8px;
}
.mm-pl-list { max-height:200px; overflow-y:auto; }
.mm-pl-item {
    display:flex; align-items:center; gap:10px; padding:8px 10px;
    border-radius:3px; cursor:pointer;
    border-bottom:1px solid rgba(176,141,87,0.06); transition:background 0.15s;
}
.mm-pl-item:hover { background:rgba(176,141,87,0.08); }
.mm-pl-item.mm-pl-active { background:rgba(176,141,87,0.15); }
.mm-pl-num { font-size:0.6rem; color:#B08D57; opacity:0.6; min-width:18px; text-align:right; }
.mm-pl-title { flex:1; font-size:0.78rem; color:#F5F5DC; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.mm-pl-play { font-size:0.65rem; color:#B08D57; opacity:0.35; }
.mm-pl-item.mm-pl-active .mm-pl-play { opacity:1; }

/* Decorative cog */
.mm-cog {
    position:absolute; bottom:18px; left:18px; opacity:0.05;
    font-size:2.4rem; animation:mm-spin-slow 15s linear infinite;
    color:#B08D57; pointer-events:none; line-height:1;
}

@keyframes mm-art-pulse {
    0%,100% { transform:scale(1); opacity:0.9; }
    50%      { transform:scale(1.04); opacity:1; }
}
@keyframes mm-spin-slow { from { transform:rotate(0deg); } to { transform:rotate(360deg); } }
@keyframes vcr-blink { 0%,100% { opacity:1; } 50% { opacity:0; } }
@media(max-width:600px) {
    .mm-body { grid-template-columns:1fr; }
    .mm-left { flex-direction:row; flex-wrap:wrap; gap:12px; }
    .mm-artwork { max-width:160px; }
}
</style>

<div id="mm-wrap" style="margin-top:40px;">

<!-- ── Main TV set ──────────────────────────────────────────────── -->
<div class="mm-box">
    <div class="mm-inlay"></div>

    <!-- Header -->
    <div class="mm-header">
        <div class="mm-station-row">
            <span id="mmIco" style="color:#B08D57;font-size:1.1rem;">&#128250;</span>
            <h2 class="mm-station-name" id="mmSname">MAPH &mdash; Channel 46</h2>
        </div>
        <div class="mm-slogan"><span id="mmSlogan">Markets, Analytics &amp; Player Help</span></div>
    </div>

    <!-- Body -->
    <div class="mm-body">

        <!-- Left: now-airing info -->
        <div class="mm-left">
            <div class="mm-trackinfo">
                <div class="mm-track-label" id="mmTrackLbl">Now Airing</div>
                <div class="mm-track-title" id="mmTitle">&#8212;</div>
                <div class="mm-track-ref" id="mmTrackRef"></div>
            </div>
        </div>

        <!-- Right: screen + metrics + controls + playlist -->
        <div class="mm-right">

            <!-- Screen -->
            <div class="mm-screen-wrap">
                <div class="mm-static" id="mmStatic">
                    <canvas id="mmStaticCanvas"></canvas>
                </div>
                <div id="mmYtContainer"></div>
                <div class="mm-watermark mm-wm-maph" id="mmWatermark">
                    <div class="mm-watermark-logo" id="mmWatermarkLogo">MAPH</div>
                </div>
            </div>

            <!-- Metrics -->
            <div class="mm-metrics">
                <div class="mm-metric">
                    <div class="mm-metric-label">Library</div>
                    <div class="mm-metric-value" id="mmM1">&#8212;</div>
                    <div class="mm-metric-sub">Videos</div>
                </div>
                <div class="mm-metric">
                    <div class="mm-metric-label">Signal</div>
                    <div class="mm-metric-value mm-green">On Air</div>
                    <div class="mm-metric-sub">Status</div>
                </div>
                <div class="mm-metric">
                    <div class="mm-metric-label">Channel</div>
                    <div class="mm-metric-value" id="mmM3">46</div>
                    <div class="mm-metric-sub" id="mmM3sub">MAPH</div>
                </div>
            </div>

            <!-- Transport controls -->
            <div class="mm-controls">
                <div class="mm-transport">
                    <button class="mm-pp-btn" id="mmPp" onclick="mmPlayPause()">&#9654;</button>
                    <button class="mm-skip-btn" onclick="mmNext()" title="Next">&#9197;</button>
                </div>

                <div class="mm-prog-wrap">
                    <div class="mm-prog-header">
                        <span>On Air</span>
                        <span id="mmCounter">&#8212;</span>
                    </div>
                    <div class="mm-prog-bar">
                        <div class="mm-prog-fill" id="mmProgFill"></div>
                    </div>
                </div>

                <!-- Channel tuner (replaces frequency knob) -->
                <div class="mm-tuner">
                    <div class="mm-tuner-row">
                        <button class="mm-tuner-btn mm-on-maph" id="mmBtnMaph" onclick="mmTune('maph')">CH&nbsp;46</button>
                        <button class="mm-tuner-btn" id="mmBtnMatt" onclick="mmTune('matt')">CH&nbsp;28</button>
                    </div>
                    <span class="mm-tuner-lbl" id="mmTunerLbl">MAPH</span>
                </div>
            </div>

            <!-- Playlist panel -->
            <div class="mm-panel">
                <div class="mm-panel-hdr">&#128250; Playlist</div>
                <div id="mmPlList" class="mm-pl-list">
                    <div style="color:#64748b;font-size:0.75rem;padding:12px 0;text-align:center;">Loading&hellip;</div>
                </div>
            </div>

        </div>
    </div>
    <div class="mm-cog">&#9881;</div>
</div>

<!-- ── Submit card — VCR style, amber accent ──────────────────── -->
<div class="mm-box" style="margin-top:24px;outline-color:rgba(217,119,6,0.2);">
    <div class="mm-inlay" style="border-color:rgba(217,119,6,0.15);"></div>
    <div class="mm-header" style="background:#130A00;">
        <div class="mm-station-row">
            <span style="color:#f59e0b;font-size:1.1rem;">&#128250;</span>
            <h2 class="mm-station-name" style="color:#f59e0b;">Submit to CH 28 &middot; MATT</h2>
        </div>
        <div class="mm-slogan"><span>Community &middot; Market Action Trading Theater</span></div>
    </div>

    <div style="padding:20px 24px 24px;">

        <!-- VCR digital display -->
        <div style="background:#060300;border:1px solid rgba(217,119,6,0.3);border-radius:2px;
                    padding:9px 14px;margin-bottom:10px;
                    display:flex;align-items:center;justify-content:space-between;
                    box-shadow:inset 0 2px 8px rgba(0,0,0,0.9),0 1px 0 rgba(217,119,6,0.08);">
            <div style="font-family:'JetBrains Mono','Courier New',monospace;color:#f59e0b;
                        font-size:0.85rem;letter-spacing:0.22em;
                        text-shadow:0 0 10px rgba(245,158,11,0.65);">
                &#9654;&nbsp;&nbsp;CH 28 &middot; MATT
            </div>
            <div style="display:flex;align-items:center;gap:12px;">
                <span style="font-family:'JetBrains Mono',monospace;font-size:0.5rem;
                             color:#3d2304;letter-spacing:0.12em;">SP&nbsp;&nbsp;&#9646;&#9646;</span>
                <span style="font-family:'JetBrains Mono',monospace;font-size:0.52rem;
                             color:#dc2626;letter-spacing:0.1em;
                             animation:vcr-blink 1.4s step-end infinite;">&#9679;&nbsp;REVIEW</span>
            </div>
        </div>

        <!-- VCR cassette slot groove -->
        <div style="height:5px;background:#060300;border:1px solid rgba(217,119,6,0.07);
                    border-radius:1px;margin-bottom:18px;overflow:hidden;position:relative;">
            <div style="position:absolute;inset:0;
                        background:repeating-linear-gradient(90deg,
                            transparent,transparent 5px,
                            rgba(217,119,6,0.04) 5px,rgba(217,119,6,0.04) 6px);"></div>
        </div>

        <div id="mmSubMsg" style="display:none;padding:8px 12px;border-radius:3px;font-size:0.82rem;margin-bottom:14px;font-family:Georgia,serif;"></div>

        <div style="display:flex;flex-direction:column;gap:12px;">
            <div>
                <div class="mm-track-label" style="margin-bottom:5px;">YouTube URL</div>
                <input type="text" id="mmSubUrl"
                       style="width:100%;box-sizing:border-box;background:#060300;border:1px solid rgba(176,141,87,0.2);color:#F5F5DC;padding:8px 10px;font-size:0.85rem;border-radius:2px;font-family:Georgia,serif;"
                       placeholder="youtube.com/watch?v=&hellip; or youtu.be/&hellip;">
            </div>
            <div>
                <div class="mm-track-label" style="margin-bottom:5px;">Video Title</div>
                <input type="text" id="mmSubTitle" maxlength="120"
                       style="width:100%;box-sizing:border-box;background:#060300;border:1px solid rgba(176,141,87,0.2);color:#F5F5DC;padding:8px 10px;font-size:0.85rem;border-radius:2px;font-family:Georgia,serif;"
                       placeholder="Title (max 120 chars)">
            </div>
            <div>
                <div class="mm-track-label" style="margin-bottom:5px;">Note for Admins</div>
                <input type="text" id="mmSubNote"
                       style="width:100%;box-sizing:border-box;background:#060300;border:1px solid rgba(176,141,87,0.2);color:#F5F5DC;padding:8px 10px;font-size:0.85rem;border-radius:2px;font-family:Georgia,serif;"
                       placeholder="Optional">
            </div>
            <!-- REC-style submit button -->
            <div style="display:flex;align-items:center;gap:14px;padding-top:4px;">
                <button onclick="mmSubmit()"
                        style="background:linear-gradient(to bottom,#2a1200,#170900);
                               border:2px solid rgba(217,119,6,0.65);
                               border-bottom-width:3px;border-bottom-color:rgba(120,55,0,0.9);
                               color:#f59e0b;padding:10px 22px;font-size:0.88rem;
                               border-radius:3px;cursor:pointer;font-family:Georgia,serif;
                               letter-spacing:0.1em;
                               box-shadow:0 4px 10px rgba(0,0,0,0.7),inset 0 1px 0 rgba(245,158,11,0.12);
                               text-shadow:0 0 8px rgba(245,158,11,0.5);transition:all 0.15s;"
                        onmouseover="this.style.background='linear-gradient(to bottom,#f59e0b,#d97706)';this.style.color='#1A0F0A';this.style.textShadow='none';this.style.borderBottomColor='rgba(120,70,0,1)';"
                        onmouseout="this.style.background='linear-gradient(to bottom,#2a1200,#170900)';this.style.color='#f59e0b';this.style.textShadow='0 0 8px rgba(245,158,11,0.5)';this.style.borderBottomColor='rgba(120,55,0,0.9)';">
                    &#9679;&nbsp;&nbsp;SUBMIT FOR REVIEW
                </button>
                <span style="font-family:'JetBrains Mono',monospace;font-size:0.55rem;
                             color:#3d2304;letter-spacing:0.1em;text-transform:uppercase;
                             line-height:1.5;">Admins review<br>before broadcast</span>
            </div>
        </div>

    </div>

    <!-- VCR bezel bottom -->
    <div style="height:10px;background:linear-gradient(to top,#0a0600,#130A00);
                border-top:1px solid rgba(217,119,6,0.08);
                display:flex;align-items:center;justify-content:center;">
        <div style="width:30%;height:2px;background:rgba(217,119,6,0.06);border-radius:1px;"></div>
    </div>
</div>
</div>

<script>
(function () {
    var STORE = 'wadsMM';
    var playlists = { maph: [], matt: [] };
    var state = { channel: 'maph', idx: 0 };

    try {
        var sv = JSON.parse(localStorage.getItem(STORE) || '{}');
        if (sv.channel === 'maph' || sv.channel === 'matt') state.channel = sv.channel;
        if (typeof sv.idx === 'number') state.idx = sv.idx;
    } catch(e) {}

    function save() {
        try { localStorage.setItem(STORE, JSON.stringify({channel:state.channel,idx:state.idx})); } catch(e) {}
    }

    // ── Static noise ─────────────────────────────────────────────────────────
    var canvas   = document.getElementById('mmStaticCanvas');
    var sWrap    = document.getElementById('mmStatic');
    var ctx      = canvas ? canvas.getContext('2d') : null;
    var rafNoise = null;

    function startStatic() {
        if (!ctx || !sWrap) return;
        if (rafNoise) { cancelAnimationFrame(rafNoise); rafNoise = null; }
        sWrap.style.display = 'flex';
        var w = canvas.width  = canvas.parentElement.offsetWidth  || 480;
        var h = canvas.height = canvas.parentElement.offsetHeight || 270;
        function drawNoise() {
            var img = ctx.createImageData(w, h);
            for (var i = 0; i < img.data.length; i += 4) {
                var v = Math.random() * 160 | 0;
                img.data[i] = img.data[i+1] = img.data[i+2] = v;
                img.data[i+3] = 255;
            }
            ctx.putImageData(img, 0, 0);
            rafNoise = requestAnimationFrame(drawNoise);
        }
        drawNoise();
    }

    function stopStatic() {
        if (rafNoise) { cancelAnimationFrame(rafNoise); rafNoise = null; }
        if (sWrap) sWrap.style.display = 'none';
        stopStaticAudio();
    }

    // ── Static audio (Web Audio white noise burst) ────────────────────────────
    var _audioCtx = null, _staticSrc = null;
    function startStaticAudio() {
        try {
            if (!_audioCtx) _audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            if (_staticSrc) { try { _staticSrc.stop(); } catch(e){} _staticSrc = null; }
            var sr = _audioCtx.sampleRate;
            var buf = _audioCtx.createBuffer(1, Math.floor(sr * 0.65), sr);
            var data = buf.getChannelData(0);
            for (var i = 0; i < data.length; i++) data[i] = (Math.random() * 2 - 1);
            var gain = _audioCtx.createGain();
            gain.gain.value = 0.07;
            _staticSrc = _audioCtx.createBufferSource();
            _staticSrc.buffer = buf;
            _staticSrc.connect(gain);
            gain.connect(_audioCtx.destination);
            _staticSrc.start();
        } catch(e) {}
    }
    function stopStaticAudio() {
        try { if (_staticSrc) { _staticSrc.stop(); _staticSrc = null; } } catch(e) {}
    }

    // ── YouTube IFrame API (same approach as tutorials) ───────────────────────
    var ytPlayer  = null;
    var pendingId = null;
    var isPlaying = false;
    var progTimer = null;

    function startProgress() {
        if (progTimer) clearInterval(progTimer);
        progTimer = setInterval(function() {
            if (!ytPlayer || typeof ytPlayer.getCurrentTime !== 'function') return;
            var cur = ytPlayer.getCurrentTime() || 0;
            var dur = ytPlayer.getDuration()    || 0;
            var fill = document.getElementById('mmProgFill');
            if (fill && dur > 0) fill.style.width = (cur / dur * 100).toFixed(1) + '%';
            var ctr = document.getElementById('mmCounter');
            if (ctr && dur > 0) {
                var rem = Math.max(0, Math.floor(dur - cur));
                var m = Math.floor(rem / 60), s = rem % 60;
                ctr.textContent = '-' + m + ':' + (s < 10 ? '0' : '') + s;
            }
        }, 500);
    }

    function stopProgress() {
        if (progTimer) { clearInterval(progTimer); progTimer = null; }
    }

    function updatePpBtn() {
        var btn = document.getElementById('mmPp');
        if (btn) btn.innerHTML = isPlaying ? '&#9646;&#9646;' : '&#9654;';
    }

    (function loadYtApi() {
        if (window.YT && window.YT.Player) { onYtReady(); return; }
        var tag = document.createElement('script');
        tag.src = 'https://www.youtube.com/iframe_api';
        document.head.appendChild(tag);
    })();

    function onYtReady() {
        ytPlayer = new YT.Player('mmYtContainer', {
            width: '100%', height: '100%',
            videoId: '',
            playerVars: { rel: 0, modestbranding: 1, enablejsapi: 1 },
            events: {
                onReady: function(e) {
                    var iframe = e.target.getIframe();
                    iframe.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;border:0;';
                    if (pendingId) { e.target.loadVideoById(pendingId); pendingId = null; }
                },
                onStateChange: function(e) {
                    if (e.data === 1) { isPlaying = true;  stopStatic(); startProgress(); updatePpBtn(); }
                    if (e.data === 2) { isPlaying = false; stopProgress(); updatePpBtn(); }
                    if (e.data === 0) { isPlaying = false; stopProgress(); updatePpBtn(); mmNext(); }
                }
            }
        });
    }

    var _prevReady = window.onYouTubeIframeAPIReady;
    window.onYouTubeIframeAPIReady = function() {
        if (typeof _prevReady === 'function') _prevReady();
        onYtReady();
    };

    // ── UI update ────────────────────────────────────────────────────────────
    function updateUI() {
        var isMatt = state.channel === 'matt';
        var accent = isMatt ? '#f59e0b' : '#B08D57';

        document.getElementById('mmSname').textContent   = isMatt ? 'MATT — Channel 28' : 'MAPH — Channel 46';
        document.getElementById('mmSlogan').textContent  = isMatt ? 'Market Action Trading Theater' : 'Markets, Analytics & Player Help';
        document.getElementById('mmIco').style.color     = accent;
        document.getElementById('mmTrackLbl').style.color = accent;
        document.getElementById('mmWatermark').className = 'mm-watermark ' + (isMatt ? 'mm-wm-matt' : 'mm-wm-maph');
        document.getElementById('mmWatermarkLogo').textContent = isMatt ? 'MATT' : 'MAPH';
        document.getElementById('mmM3').textContent   = isMatt ? '28' : '46';
        document.getElementById('mmM3sub').textContent = isMatt ? 'MATT' : 'MAPH';
        document.getElementById('mmTunerLbl').textContent = isMatt ? 'MATT' : 'MAPH';
        document.getElementById('mmBtnMaph').className = 'mm-tuner-btn' + (state.channel==='maph' ? ' mm-on-maph' : '');
        document.getElementById('mmBtnMatt').className = 'mm-tuner-btn' + (state.channel==='matt' ? ' mm-on-matt' : '');

        var pl  = playlists[state.channel];
        var vid = pl[state.idx];
        document.getElementById('mmTitle').textContent    = vid ? vid.title : '—';
        document.getElementById('mmTrackRef').textContent = vid ? vid.youtube_id : '';
        document.getElementById('mmM1').textContent       = pl.length || '—';
        if (!isPlaying) document.getElementById('mmCounter').textContent = pl.length ? (state.idx+1) + ' / ' + pl.length : '—';
        buildPlaylist();
    }

    function buildPlaylist() {
        var pl   = playlists[state.channel];
        var list = document.getElementById('mmPlList');
        if (!pl.length) {
            list.innerHTML = '<div style="color:#64748b;font-size:0.75rem;padding:12px 0;text-align:center;font-style:italic;">No videos in playlist yet.</div>';
            return;
        }
        list.innerHTML = pl.map(function(v, i) {
            var cls = 'mm-pl-item' + (i === state.idx ? ' mm-pl-active' : '');
            return '<div class="' + cls + '" onclick="mmJump(' + i + ')">'
                + '<span class="mm-pl-num">' + (i+1) + '</span>'
                + '<span class="mm-pl-title">' + v.title.replace(/</g,'&lt;') + '</span>'
                + '<span class="mm-pl-play">&#9654;</span>'
                + '</div>';
        }).join('');
    }

    // ── Playback ─────────────────────────────────────────────────────────────
    function loadVideo() {
        var pl  = playlists[state.channel];
        var vid = pl[state.idx];
        isPlaying = false; stopProgress();
        var fill = document.getElementById('mmProgFill');
        if (fill) fill.style.width = '0%';
        updatePpBtn();
        if (!vid) { startStatic(); updateUI(); return; }
        startStatic();
        updateUI();
        save();
        if (ytPlayer && typeof ytPlayer.loadVideoById === 'function') {
            ytPlayer.loadVideoById(vid.youtube_id);
        } else {
            pendingId = vid.youtube_id;
        }
    }

    function staticBlast(then) {
        isPlaying = false; stopProgress();
        var fill = document.getElementById('mmProgFill');
        if (fill) fill.style.width = '0%';
        updatePpBtn();
        if (ytPlayer && typeof ytPlayer.stopVideo === 'function') ytPlayer.stopVideo();
        startStatic(); startStaticAudio();
        updateUI(); save();
        setTimeout(then, 600);
    }

    window.mmTune = function(ch) {
        if (state.channel === ch) return;
        state.channel = ch; state.idx = 0;
        staticBlast(loadVideo);
    };

    window.mmNext = function() {
        var pl = playlists[state.channel];
        if (!pl.length) return;
        state.idx = (state.idx + 1) % pl.length;
        staticBlast(loadVideo);
    };

    window.mmJump = function(i) {
        state.idx = i;
        staticBlast(loadVideo);
    };

    window.mmPlayPause = function() {
        if (!ytPlayer || typeof ytPlayer.getPlayerState !== 'function') { loadVideo(); return; }
        var s = ytPlayer.getPlayerState();
        if (s === 1)  { ytPlayer.pauseVideo(); }
        else if (s < 0) { loadVideo(); }
        else            { ytPlayer.playVideo(); }
    };

    window.mmReplay = window.mmPlayPause;

    // ── Submit form ───────────────────────────────────────────────────────────
    window.mmSubmit = function() {
        var url   = (document.getElementById('mmSubUrl').value   || '').trim();
        var title = (document.getElementById('mmSubTitle').value || '').trim();
        var note  = (document.getElementById('mmSubNote').value  || '').trim();
        var msgEl = document.getElementById('mmSubMsg');
        if (!url || !title) {
            msgEl.style.cssText = 'display:block;padding:8px 12px;border-radius:3px;font-size:0.82rem;margin-bottom:14px;background:#1a0505;color:#f87171;border:1px solid #dc2626;';
            msgEl.textContent = 'YouTube URL and title are both required.';
            return;
        }
        var fd = new FormData();
        fd.append('youtube_url', url);
        fd.append('title', title);
        fd.append('note', note);
        fetch('/api/matt/submit', {method:'POST', body:fd})
            .then(function(r) { return r.json(); })
            .then(function(d) {
                if (d.ok) {
                    msgEl.style.cssText = 'display:block;padding:8px 12px;border-radius:3px;font-size:0.82rem;margin-bottom:14px;background:#052e16;color:#4ade80;border:1px solid #16a34a;';
                    msgEl.textContent = '✓ Submitted! Admins will review your video before it appears on MATT.';
                    document.getElementById('mmSubUrl').value = document.getElementById('mmSubTitle').value = document.getElementById('mmSubNote').value = '';
                } else {
                    msgEl.style.cssText = 'display:block;padding:8px 12px;border-radius:3px;font-size:0.82rem;margin-bottom:14px;background:#1a0505;color:#f87171;border:1px solid #dc2626;';
                    msgEl.textContent = '✗ ' + (d.error || 'Submission failed.');
                }
            })
            .catch(function() {
                msgEl.style.cssText = 'display:block;padding:8px 12px;border-radius:3px;font-size:0.82rem;margin-bottom:14px;background:#1a0505;color:#f87171;border:1px solid #dc2626;';
                msgEl.textContent = '✗ Network error — please try again.';
            });
    };

    // ── Boot ─────────────────────────────────────────────────────────────────
    Promise.all([
        fetch('/api/maph/list').then(function(r){return r.json();}).catch(function(){return[];}),
        fetch('/api/matt/list').then(function(r){return r.json();}).catch(function(){return[];})
    ]).then(function(results) {
        playlists.maph = results[0] || [];
        playlists.matt = results[1] || [];
        var pl = playlists[state.channel];
        if (state.idx >= pl.length) state.idx = 0;
        startStatic();
        updateUI();
        setTimeout(loadVideo, 400);
    });
})();
</script>
    """


def _tutorials_tab(player) -> str:
    from tutorial_ux import get_tutorial_step, TERRAIN_OPTIONS
    from executive import FIRST_LADY_EXECUTIVES

    step = get_tutorial_step(player.id)

    # ─────────────────────────────────────────────────────────────────────────
    # Helper: render one tutorial card
    # ─────────────────────────────────────────────────────────────────────────
    def _tutorial_card(
        number,        # 1, 2, 3 …
        title,
        description,
        total_steps,
        completed_steps,   # how many steps finished
        current_step,      # step label shown when in-progress ("3 of 9"), or None
        status,            # "not_started" | "in_progress" | "complete" | "locked"
        reward_html,       # inner HTML for the reward area
        can_restart=False, # show a Restart button
    ):
        STATUS_CFG = {
            "not_started": ("#64748b", "#64748b", "Not Started"),
            "in_progress": ("#818cf8", "#818cf8", "In Progress"),
            "complete":    ("#4ade80", "#4ade80", "Complete ✓"),
            "locked":      ("#334155", "#475569", "Locked"),
        }
        bar_color, badge_color, badge_label = STATUS_CFG[status]
        pct = int(completed_steps / total_steps * 100) if total_steps else 0

        step_label = ""
        if status == "in_progress" and current_step is not None:
            step_label = f'<span style="font-size:0.72rem;color:#64748b;">Step {current_step} of {total_steps}</span>'
        elif status == "complete":
            step_label = f'<span style="font-size:0.72rem;color:#4ade80;">{total_steps} of {total_steps} steps</span>'
        elif status == "not_started":
            step_label = f'<span style="font-size:0.72rem;color:#64748b;">0 of {total_steps} steps</span>'
        elif status == "locked":
            step_label = f'<span style="font-size:0.72rem;color:#334155;">Complete tutorial {number - 1} to unlock</span>'

        border = "1px solid #4ade80" if status == "complete" else ("1px solid #818cf8" if status == "in_progress" else "1px solid #1e293b")
        opacity = "opacity:0.5;" if status == "locked" else ""

        return f"""
<div style="background:#0f172a;{border};border-radius:8px;padding:20px 24px;margin-bottom:16px;{opacity}">
  <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin-bottom:14px;">
    <div>
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;">
        <span style="font-size:0.72rem;font-weight:bold;color:#475569;text-transform:uppercase;
                     letter-spacing:.06em;">Tutorial {number}</span>
        <span style="font-size:0.72rem;font-weight:bold;color:{badge_color};padding:2px 8px;
                     background:rgba(255,255,255,0.04);border-radius:99px;border:1px solid {badge_color}22;">
          {badge_label}
        </span>
      </div>
      <div style="font-size:1rem;font-weight:bold;color:#f1f5f9;">{title}</div>
      <div style="font-size:0.78rem;color:#64748b;margin-top:4px;">{description}</div>
    </div>
  </div>
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px;">
    <div style="flex:1;background:#1e293b;border-radius:4px;height:6px;overflow:hidden;">
      <div style="background:{bar_color};height:100%;width:{pct}%;border-radius:4px;transition:width .4s;"></div>
    </div>
    {step_label}
  </div>
  <div style="border-top:1px solid #1e293b;padding-top:14px;">
    <div style="font-size:0.72rem;font-weight:bold;color:#475569;text-transform:uppercase;
                letter-spacing:.06em;margin-bottom:10px;">Reward</div>
    {reward_html}
  </div>
  {f'''<div style="border-top:1px solid #1e293b;padding-top:12px;margin-top:14px;">
    <form method="post" action="/api/tutorial/restart" style="display:inline;">
      <input type="hidden" name="tutorial_number" value="{number}">
      <button type="submit"
              onclick="return confirm('Restart Tutorial {number} from the beginning? Your reward will not be given again.')"
              style="padding:6px 14px;background:transparent;border:1px solid #334155;border-radius:4px;
                     color:#64748b;font-size:0.75rem;cursor:pointer;">
        ↺ Restart Tutorial {number}
      </button>
    </form>
  </div>''' if can_restart else ''}
</div>"""

    # ─────────────────────────────────────────────────────────────────────────
    # Tutorial 1 — Start a Business  (tutorial_step 1–9, complete at step ≥ 10)
    # ─────────────────────────────────────────────────────────────────────────
    T1_STEPS = 9

    if step == 0:
        t1_status  = "not_started"
        t1_done    = 0
        t1_current = None
    elif step >= 10:
        t1_status  = "complete"
        t1_done    = T1_STEPS
        t1_current = None
    else:
        t1_status  = "in_progress"
        t1_done    = step - 1  # steps before the current one are done
        t1_current = step

    # Reward: tax-free land plot
    if step >= 10:
        t1_reward = """
<div style="display:flex;align-items:center;gap:10px;">
  <span style="color:#4ade80;font-size:1rem;">&#10003;</span>
  <div>
    <span style="font-size:0.85rem;font-weight:bold;color:#4ade80;">Tax-Free Land Plot — Claimed</span>
    <div style="font-size:0.72rem;color:#64748b;margin-top:2px;">
      Permanent plot, all proximity features, zero monthly tax.
      View on <a href="/land" style="color:#38bdf8;">Land</a> or
      <a href="/land-market" style="color:#38bdf8;">Land Market</a>.
    </div>
  </div>
</div>"""
    elif step == 9:
        terrain_opts = "".join(
            f'<option value="{k}">{k.title()} — {desc}</option>'
            for k, desc in TERRAIN_OPTIONS
        )
        t1_reward = f"""
<div style="font-size:0.82rem;font-weight:bold;color:#d4af37;margin-bottom:10px;">
  &#127381; Ready to claim — choose your terrain:
</div>
<form method="post" action="/api/tutorial/claim-reward"
      style="display:flex;flex-wrap:wrap;gap:8px;align-items:center;">
  <select name="terrain_type" style="flex:1;min-width:180px;padding:7px 10px;background:#1e293b;
          border:1px solid #334155;border-radius:4px;color:#f1f5f9;font-size:0.78rem;cursor:pointer;">
    {terrain_opts}
  </select>
  <button type="submit" style="padding:8px 18px;background:#d4af37;color:#0f172a;border:none;
          border-radius:4px;font-weight:bold;font-size:0.82rem;cursor:pointer;white-space:nowrap;">
    Claim Land Plot
  </button>
</form>"""
    else:
        remaining = (9 - step) if step > 0 else 9
        t1_reward = f"""
<div style="font-size:0.82rem;color:#475569;">
  &#128274; Tax-Free Land Plot &mdash;
  {"complete the tutorial to unlock" if step == 0 else f"{remaining} step{'s' if remaining != 1 else ''} away"}
</div>"""

    card1 = _tutorial_card(
        number=1,
        title="Start a Business",
        description="Learn how to build land, manage inventory, trade on the market, and earn your first profits.",
        total_steps=T1_STEPS,
        completed_steps=t1_done,
        current_step=t1_current,
        status=t1_status,
        reward_html=t1_reward,
        can_restart=(step > 0),
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Tutorial 2 — Executives  (tutorial_step 10–11, complete at step ≥ 12)
    # ─────────────────────────────────────────────────────────────────────────
    T2_STEPS = 2  # step 10 (land market) + step 11 (executives video)

    if step < 10:
        t2_status  = "locked"
        t2_done    = 0
        t2_current = None
    elif step >= 12:
        t2_status  = "complete"
        t2_done    = T2_STEPS
        t2_current = None
    else:
        t2_status  = "in_progress"
        t2_done    = step - 10       # step 10 → 0 done, step 11 → 1 done
        t2_current = step - 9        # step 10 → "1 of 2", step 11 → "2 of 2"

    # Reward: First Lady executive
    if step >= 12:
        t2_reward = """
<div style="display:flex;align-items:center;gap:10px;">
  <span style="color:#4ade80;font-size:1rem;">&#10003;</span>
  <div>
    <span style="font-size:0.85rem;font-weight:bold;color:#4ade80;">First Lady Executive — Claimed</span>
    <div style="font-size:0.72rem;color:#64748b;margin-top:2px;">
      Permanent executive, wage $0 forever, max level 18.
      View on <a href="/executives" style="color:#38bdf8;">Executives</a>.
    </div>
  </div>
</div>"""
    elif step == 11:
        fl_opts = "".join(
            f'<option value="{fl["key"]}">{fl["name"]} ({fl["years"]}) — {fl["real_role"]}</option>'
            for fl in FIRST_LADY_EXECUTIVES
        )
        t2_reward = f"""
<div style="font-size:0.82rem;font-weight:bold;color:#d4af37;margin-bottom:10px;">
  &#127381; Ready to claim — choose your First Lady:
</div>
<form method="post" action="/api/tutorial/claim-executive"
      style="display:flex;flex-wrap:wrap;gap:8px;align-items:center;">
  <select name="first_lady" style="flex:1;min-width:220px;padding:7px 10px;background:#1e293b;
          border:1px solid #334155;border-radius:4px;color:#f1f5f9;font-size:0.78rem;cursor:pointer;">
    {fl_opts}
  </select>
  <button type="submit" style="padding:8px 18px;background:#d4af37;color:#0f172a;border:none;
          border-radius:4px;font-weight:bold;font-size:0.82rem;cursor:pointer;white-space:nowrap;">
    Claim First Lady
  </button>
</form>"""
    elif step < 10:
        t2_reward = '<div style="font-size:0.82rem;color:#334155;">&#128274; First Lady Executive — complete Tutorial 1 to unlock</div>'
    else:
        t2_reward = '<div style="font-size:0.82rem;color:#475569;">&#128274; First Lady Executive — finish this tutorial to claim</div>'

    card2 = _tutorial_card(
        number=2,
        title="Executives",
        description="Watch the Executives overview, learn how the Land Market works, and hire your first C-suite executive for free.",
        total_steps=T2_STEPS,
        completed_steps=t2_done,
        current_step=t2_current,
        status=t2_status,
        reward_html=t2_reward,
        can_restart=(step >= 10),
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Tutorial 3 — IPO & Banking  (tutorial_3_step 1–6 active, 7=reward, 8=complete)
    # ─────────────────────────────────────────────────────────────────────────
    from tutorial_ux import get_tutorial3_step
    step3 = get_tutorial3_step(player.id)
    T3_STEPS = 6

    if step < 12:
        t3_status  = "locked"
        t3_done    = 0
        t3_current = None
    elif step3 >= 8:
        t3_status  = "complete"
        t3_done    = T3_STEPS
        t3_current = None
    elif step3 == 0:
        t3_status  = "not_started"
        t3_done    = 0
        t3_current = None
    else:
        t3_status  = "in_progress"
        t3_done    = min(step3 - 1, T3_STEPS)
        t3_current = min(step3, T3_STEPS)

    if step3 >= 8:
        t3_reward = """
<div style="display:flex;align-items:center;gap:10px;">
  <span style="color:#4ade80;font-size:1rem;">&#10003;</span>
  <div>
    <span style="font-size:0.85rem;font-weight:bold;color:#4ade80;">Margin Lending — Unlocked</span>
    <div style="font-size:0.72rem;color:#64748b;margin-top:2px;">
      Borrow up to 50% of your portfolio value to amplify positions.
      Available on <a href="/brokerage/trading" style="color:#38bdf8;">Brokerage Trading</a>.
    </div>
  </div>
</div>"""
    elif step3 == 7:
        t3_reward = """
<div style="font-size:0.82rem;font-weight:bold;color:#d4af37;margin-bottom:8px;">
  &#127381; Ready to claim — visit the trading page:
</div>
<a href="/brokerage/trading"
   style="display:inline-block;padding:8px 18px;background:#d4af37;color:#020617;
          border-radius:4px;font-weight:bold;font-size:0.82rem;text-decoration:none;">
  Go Claim Reward →
</a>"""
    elif step < 12:
        t3_reward = '<div style="font-size:0.82rem;color:#334155;">&#128274; Margin Lending — complete Tutorial 2 to unlock</div>'
    else:
        t3_reward = '<div style="font-size:0.82rem;color:#475569;">&#128274; Margin Lending — finish this tutorial to claim</div>'

    card3 = _tutorial_card(
        number=3,
        title="IPO &amp; Banking",
        description="Explore the Banking System and Brokerage Firm, then take your company public on the Wadsworth Public Exchange.",
        total_steps=T3_STEPS,
        completed_steps=t3_done,
        current_step=t3_current,
        status=t3_status,
        reward_html=t3_reward,
        can_restart=(step3 > 0),
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Tutorial 4 — ETFs & Market Indices  (tutorial_4_step 1–5 active, 7=complete)
    # ─────────────────────────────────────────────────────────────────────────
    from tutorial_ux import get_tutorial4_step
    step4 = get_tutorial4_step(player.id)
    T4_STEPS = 6

    if step3 < 8:          # locked until Tutorial 3 complete
        t4_status  = "locked"
        t4_done    = 0
        t4_current = None
    elif step4 >= 7:
        t4_status  = "complete"
        t4_done    = T4_STEPS
        t4_current = None
    elif step4 == 0:
        t4_status  = "not_started"
        t4_done    = 0
        t4_current = None
    else:
        t4_status  = "in_progress"
        t4_done    = min(step4 - 1, T4_STEPS)
        t4_current = min(step4, T4_STEPS)

    if step4 >= 7:
        t4_reward = """
<div style="display:flex;align-items:center;gap:10px;">
  <span style="color:#4ade80;font-size:1rem;">&#10003;</span>
  <div>
    <span style="font-size:0.85rem;font-weight:bold;color:#4ade80;">Tax Voucher — Claimed</span>
    <div style="font-size:0.72rem;color:#64748b;margin-top:2px;">
      $100,000 Tax Voucher deposited. Redeem anytime in
      <a href="/corporate-actions/dashboard" style="color:#38bdf8;">Corporate Actions</a>.
    </div>
  </div>
</div>"""
    elif step4 in (5, 6):
        t4_reward = """
<div style="font-size:0.82rem;font-weight:bold;color:#d4af37;margin-bottom:8px;">
  &#127381; Ready to claim — watch the video on WBC-50:
</div>
<a href="/banks/indices/WBC50"
   style="display:inline-block;padding:8px 18px;background:#d4af37;color:#020617;
          border-radius:4px;font-weight:bold;font-size:0.82rem;text-decoration:none;">
  Go Claim Reward →
</a>"""
    elif step3 < 8:
        t4_reward = '<div style="font-size:0.82rem;color:#334155;">&#128274; Tax Voucher ($100,000) — complete Tutorial 3 to unlock</div>'
    elif step4 == 0:
        t4_reward = """
<div style="font-size:0.82rem;color:#475569;margin-bottom:10px;">&#128274; Tax Voucher ($100,000) — finish this tutorial to claim</div>
<form method="post" action="/api/tutorial4/start" style="display:inline;">
  <button type="submit"
          style="padding:8px 18px;background:#38bdf8;color:#020617;border:none;
                 border-radius:4px;font-weight:bold;font-size:0.82rem;cursor:pointer;">
    Start Tutorial 4 →
  </button>
</form>"""
    else:
        t4_reward = '<div style="font-size:0.82rem;color:#475569;">&#128274; Tax Voucher ($100,000) — finish this tutorial to claim</div>'

    card4 = _tutorial_card(
        number=4,
        title="ETFs &amp; Market Indices",
        description="Learn how the 19 Wadsworth Market Indices work, explore the WBC-50 Benchmark, and discover how ETFs let you invest in the broad market without picking individual stocks.",
        total_steps=T4_STEPS,
        completed_steps=t4_done,
        current_step=t4_current,
        status=t4_status,
        reward_html=t4_reward,
        can_restart=(step4 > 0),
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Tutorial 5 — Acquisitions & Income Stakes
    # ─────────────────────────────────────────────────────────────────────────
    from tutorial_ux import get_tutorial5_step
    step5 = get_tutorial5_step(player.id)
    T5_STEPS = 6

    if step4 < 7:          # locked until Tutorial 4 complete
        t5_status  = "locked"
        t5_done    = 0
        t5_current = None
    elif step5 >= 7:
        t5_status  = "complete"
        t5_done    = T5_STEPS
        t5_current = None
    elif step5 == 0:
        t5_status  = "not_started"
        t5_done    = 0
        t5_current = None
    else:
        t5_status  = "in_progress"
        t5_done    = min(step5 - 1, T5_STEPS)
        t5_current = min(step5, T5_STEPS)

    if step5 >= 7:
        t5_reward = """
<div style="display:flex;align-items:center;gap:10px;">
  <span style="color:#4ade80;font-size:1rem;">&#10003;</span>
  <div>
    <span style="font-size:0.85rem;font-weight:bold;color:#4ade80;">First Lady Executive — Claimed</span>
    <div style="font-size:0.72rem;color:#64748b;margin-top:2px;">
      Permanent executive, wage $0 forever, max level 18.
      View on <a href="/executives" style="color:#f59e0b;">Executives</a>.
    </div>
  </div>
</div>"""
    elif step5 == 6:
        fl_opts5 = "".join(
            f'<option value="{fl["key"]}">{fl["name"]} ({fl["years"]}) — {fl["real_role"]}</option>'
            for fl in FIRST_LADY_EXECUTIVES
        )
        t5_reward = f"""
<div style="font-size:0.82rem;font-weight:bold;color:#f59e0b;margin-bottom:10px;">
  &#127381; Ready to claim — choose your First Lady:
</div>
<form method="post" action="/api/tutorial5/claim-reward"
      style="display:flex;flex-wrap:wrap;gap:8px;align-items:center;">
  <select name="first_lady" style="flex:1;min-width:220px;padding:7px 10px;background:#1e293b;
          border:1px solid #334155;border-radius:4px;color:#f1f5f9;font-size:0.78rem;cursor:pointer;">
    {fl_opts5}
  </select>
  <button type="submit" style="padding:8px 18px;background:#f59e0b;color:#020617;border:none;
          border-radius:4px;font-weight:bold;font-size:0.82rem;cursor:pointer;white-space:nowrap;">
    Claim First Lady
  </button>
</form>"""
    elif step4 < 7:
        t5_reward = '<div style="font-size:0.82rem;color:#334155;">&#128274; First Lady Executive — complete Tutorial 4 to unlock</div>'
    elif step5 == 0:
        t5_reward = """
<div style="font-size:0.82rem;color:#475569;margin-bottom:10px;">&#128274; First Lady Executive — finish this tutorial to claim</div>
<form method="post" action="/api/tutorial5/start" style="display:inline;">
  <button type="submit"
          style="padding:8px 18px;background:#f59e0b;color:#020617;border:none;
                 border-radius:4px;font-weight:bold;font-size:0.82rem;cursor:pointer;">
    Start Tutorial 5 →
  </button>
</form>"""
    else:
        t5_reward = '<div style="font-size:0.82rem;color:#475569;">&#128274; First Lady Executive — finish this tutorial to claim</div>'

    card5 = _tutorial_card(
        number=5,
        title="Acquisitions &amp; Income Stakes",
        description="Learn how to offer shares for a percentage of another player's net income, how escrow protects both sides, how the daily income sweep works across currencies, and how to exit a stake cleanly.",
        total_steps=T5_STEPS,
        completed_steps=t5_done,
        current_step=t5_current,
        status=t5_status,
        reward_html=t5_reward,
        can_restart=(step5 > 0),
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Tutorial 6 — Districts & District Market
    # ─────────────────────────────────────────────────────────────────────────
    from tutorial_ux import get_tutorial6_step
    step6 = get_tutorial6_step(player.id)
    T6_STEPS = 6

    if step5 < 7:          # locked until Tutorial 5 complete
        t6_status  = "locked"
        t6_done    = 0
        t6_current = None
    elif step6 >= 7:
        t6_status  = "complete"
        t6_done    = T6_STEPS
        t6_current = None
    elif step6 == 0:
        t6_status  = "not_started"
        t6_done    = 0
        t6_current = None
    else:
        t6_status  = "in_progress"
        t6_done    = min(step6 - 1, T6_STEPS)
        t6_current = min(step6, T6_STEPS)

    if step6 >= 7:
        t6_reward = """
<div style="display:flex;align-items:center;gap:10px;">
  <span style="color:#38bdf8;font-size:1rem;">&#10003;</span>
  <div>
    <span style="font-size:0.85rem;font-weight:bold;color:#38bdf8;">Free District Plot + Business — Claimed</span>
    <div style="font-size:0.72rem;color:#64748b;margin-top:2px;">
      Your tax-free District Food Plot and wage-free Fast Food Kitchen are on your
      <a href="/districts" style="color:#38bdf8;">Districts</a> page.
    </div>
  </div>
</div>"""
    elif step5 < 7:
        t6_reward = '<div style="font-size:0.82rem;color:#334155;">&#128274; Free District Plot + Business — complete Tutorial 5 to unlock</div>'
    elif step6 == 0:
        t6_reward = """
<div style="font-size:0.82rem;color:#475569;margin-bottom:10px;">&#127961;&#65039; Free District Plot + Business — finish this tutorial to claim</div>
<form method="post" action="/api/tutorial6/start" style="display:inline;">
  <button type="submit"
          style="padding:8px 18px;background:#38bdf8;color:#020617;border:none;
                 border-radius:4px;font-weight:bold;font-size:0.82rem;cursor:pointer;">
    Start Tutorial 6 →
  </button>
</form>"""
    else:
        t6_reward = '<div style="font-size:0.82rem;color:#475569;">&#127961;&#65039; Free District Plot + Business — finish this tutorial to claim</div>'

    card6 = _tutorial_card(
        number=6,
        title="Districts &amp; District Market",
        description="Learn how to merge land plots into Districts, explore the District Market order book, exploit price differences between local and main exchange, and understand district tax dynamics.",
        total_steps=T6_STEPS,
        completed_steps=t6_done,
        current_step=t6_current,
        status=t6_status,
        reward_html=t6_reward,
        can_restart=(step6 > 0),
    )

    # Tutorial 7 — Supply, Demand, Elasticity & Land Efficiency
    # ─────────────────────────────────────────────────────────────────────────
    from tutorial_ux import get_tutorial7_step
    step7 = get_tutorial7_step(player.id)
    T7_STEPS = 7

    if step6 < 7:          # locked until Tutorial 6 complete
        t7_status  = "locked"
        t7_done    = 0
        t7_current = None
    elif step7 >= 8:
        t7_status  = "complete"
        t7_done    = T7_STEPS
        t7_current = None
    elif step7 == 0:
        t7_status  = "not_started"
        t7_done    = 0
        t7_current = None
    else:
        t7_status  = "in_progress"
        t7_done    = min(step7 - 1, T7_STEPS)
        t7_current = min(step7, T7_STEPS)

    if step7 >= 8:
        t7_reward = """
<div style="display:flex;align-items:center;gap:10px;">
  <span style="color:#fb923c;font-size:1rem;">&#10003;</span>
  <div>
    <span style="font-size:0.85rem;font-weight:bold;color:#fb923c;">20 Trophies — Claimed</span>
    <div style="font-size:0.72rem;color:#64748b;margin-top:2px;">
      Reward claimed. Check your trophy balance on the Dashboard.
    </div>
  </div>
</div>"""
    elif step6 < 7:
        t7_reward = '<div style="font-size:0.82rem;color:#334155;">&#128274; 20 Trophies — complete Tutorial 6 to unlock</div>'
    elif step7 == 0:
        t7_reward = """
<div style="font-size:0.82rem;color:#475569;margin-bottom:10px;">&#127942; 20 Trophies — finish this tutorial to claim</div>
<form method="post" action="/api/tutorial7/start" style="display:inline;">
  <button type="submit"
          style="padding:8px 18px;background:#f97316;color:#fff;border:none;
                 border-radius:4px;font-weight:bold;font-size:0.82rem;cursor:pointer;">
    Start Tutorial 7 →
  </button>
</form>"""
    else:
        t7_reward = '<div style="font-size:0.82rem;color:#475569;">&#127942; 20 Trophies — finish this tutorial to claim</div>'

    card7 = _tutorial_card(
        number=7,
        title="Supply, Demand, Elasticity &amp; Land Efficiency",
        description="Master the mechanics behind commodity pricing, learn how price elasticity affects your sales volume, and discover how land efficiency multiplies your business profits.",
        total_steps=T7_STEPS,
        completed_steps=t7_done,
        current_step=t7_current,
        status=t7_status,
        reward_html=t7_reward,
        can_restart=(step7 > 0),
    )

    # ── CTA if nothing started ────────────────────────────────────────────────
    cta = ""
    if step == 0:
        cta = """
<div style="text-align:center;padding:8px 0 4px;">
  <a href="/" style="display:inline-block;padding:11px 28px;background:#818cf8;color:#fff;
     border-radius:6px;text-decoration:none;font-weight:bold;font-size:0.88rem;">
    Start Tutorial 1 on Dashboard
  </a>
</div>"""

    return card1 + card2 + card3 + card4 + card5 + card6 + card7 + cta


# ── Notifications tab ─────────────────────────────────────────────────────────

def _notifications_tab(player, from_tutorial: bool = False) -> str:
    # Notification features require either a CCO exec with p2p_notification OR an active FCC licence.
    # Admins always bypass this gate — they own the server and shouldn't need to hire an exec to
    # configure push on their own account.
    has_cco = False
    rental_expires = None   # datetime (UTC) if rental is active
    try:
        from admins import is_admin as _is_admin
        if _is_admin(player.id):
            has_cco = True
    except Exception:
        pass
    if not has_cco:
        try:
            from executive import player_has_cco, get_db as _exec_db
            _edb = _exec_db()
            has_cco = player_has_cco(_edb, player.id)
            _edb.close()
            # Separately check rental expiry for display
            expires_raw = getattr(player, "cco_rental_expires", None)
            if expires_raw:
                from datetime import datetime
                if expires_raw > datetime.utcnow():
                    rental_expires = expires_raw
        except Exception as e:
            import logging
            logging.getLogger(__name__).exception("has_cco check failed for player %s: %s", getattr(player, 'id', '?'), e)

    # Display-currency formatting for rental prices
    from reserve_banks import get_player_display_currency, fmt_usd as _fmt
    _disp = get_player_display_currency(player.id)
    def _price(usd): return _fmt(usd, _disp, precision=0)

    sounds   = getattr(player, "notif_sounds",         True)
    badge    = getattr(player, "notif_badge",          True)
    push_dms  = getattr(player, "notif_push_dms",          True)
    push_con  = getattr(player, "notif_push_contracts",    True)
    push_biz  = getattr(player, "notif_push_business",     True)
    push_land = getattr(player, "notif_push_land",         True)
    push_exec = getattr(player, "notif_push_execs",        True)
    push_trd  = getattr(player, "notif_push_trades",       True)
    push_corp = getattr(player, "notif_push_corporate",    True)
    push_govt = getattr(player, "notif_push_govt",         True)
    push_tevt = getattr(player, "notif_push_tasks_events", True)

    def _toggle(name: str, checked: bool, label: str, sub: str = "", disabled: bool = False) -> str:
        chk   = "checked" if checked else ""
        dis   = "disabled" if disabled else ""
        opcty = "opacity:0.4;" if disabled else ""
        return f"""
<label style="display:flex;align-items:flex-start;gap:14px;padding:14px 0;
              border-bottom:1px solid #1e293b;cursor:{'default' if disabled else 'pointer'};{opcty}">
  <div style="position:relative;flex-shrink:0;width:44px;height:24px;margin-top:2px;">
    <input type="checkbox" name="{name}" id="{name}" {chk} {dis}
           style="position:absolute;opacity:0;width:0;height:0;"
           onchange="this.form.submit()">
    <div class="ntog" data-for="{name}" style="
      position:absolute;inset:0;border-radius:12px;
      background:{'#6366f1' if checked and not disabled else '#1e293b'};
      border:1px solid {'#6366f1' if checked and not disabled else '#334155'};
      transition:background .2s,border-color .2s;cursor:{'default' if disabled else 'pointer'};">
      <div style="position:absolute;top:2px;left:{'22px' if checked else '2px'};
                  width:18px;height:18px;border-radius:50%;background:white;
                  transition:left .2s;"></div>
    </div>
  </div>
  <div>
    <div style="font-size:0.9rem;color:#f1f5f9;font-weight:500;">{label}</div>
    {'<div style="font-size:0.75rem;color:#64748b;margin-top:2px;">'+sub+'</div>' if sub else ''}
  </div>
</label>"""

    def _section(title: str, body: str) -> str:
        return f"""
<div style="background:#0f172a;border:1px solid #1e293b;border-radius:8px;
            padding:20px 24px;margin-bottom:20px;max-width:640px;">
  <div style="font-size:0.72rem;font-weight:bold;color:#475569;text-transform:uppercase;
              letter-spacing:.08em;margin-bottom:4px;">{title}</div>
  {body}
</div>"""

    # ── CCO / FCC licence banner ──────────────────────────────────────────────
    _btn_style = '<style>.fcc-btn{background:#1e293b;border:1px solid #334155;border-radius:6px;color:#e2e8f0;font-family:inherit;font-size:0.8rem;font-weight:600;padding:10px 6px;cursor:pointer;text-align:center;line-height:1.4;transition:background .15s,border-color .15s;}.fcc-btn:hover{background:#334155;border-color:#6366f1;}</style>'

    def _tier_buttons(prefix=""):
        rows = [
            ("6h",  f"{prefix}6 Hours",  500),
            ("1d",  f"{prefix}1 Day",    1_500),
            ("3d",  f"{prefix}3 Days",   3_500),
            ("1w",  f"{prefix}1 Week",   7_000),
            ("2w",  f"{prefix}2 Weeks",  12_000),
            ("1mo", f"{prefix}1 Month",  20_000),
        ]
        btns = "".join(
            f'<button name="tier" value="{k}" type="submit" class="fcc-btn">'
            f'{lbl}<br><span style="font-size:0.7rem;color:#94a3b8;">{_price(usd)}</span>'
            f'</button>'
            for k, lbl, usd in rows
        )
        return f'<form method="post" action="/api/settings/cco-rental"><div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;">{btns}</div></form>'

    if has_cco and rental_expires:
        _exp_str = rental_expires.strftime("%b %d, %Y %H:%M UTC")
        cco_banner = f"""
<div style="background:#0f2a1a;border:1px solid #166534;border-radius:8px;
            padding:14px 18px;margin-bottom:20px;max-width:640px;
            display:flex;align-items:flex-start;gap:12px;">
  <span style="font-size:1.3rem;flex-shrink:0;">✅</span>
  <div>
    <div style="font-size:0.88rem;font-weight:600;color:#86efac;margin-bottom:4px;">
      Notifications unlocked via CCO executive
    </div>
    <div style="font-size:0.78rem;color:#4ade80;line-height:1.5;">
      You also have a Federal Communications Commission (FCC) licence active until <strong>{_exp_str}</strong>.
    </div>
  </div>
</div>"""
    elif has_cco:
        cco_banner = """
<div style="background:#0f2a1a;border:1px solid #166534;border-radius:8px;
            padding:14px 18px;margin-bottom:20px;max-width:640px;
            display:flex;align-items:flex-start;gap:12px;">
  <span style="font-size:1.3rem;flex-shrink:0;">✅</span>
  <div style="font-size:0.88rem;font-weight:600;color:#86efac;">
    Notifications unlocked via CCO executive
  </div>
</div>"""
    elif rental_expires:
        _exp_str = rental_expires.strftime("%b %d, %Y %H:%M UTC")
        cco_banner = f"""
<div style="background:#1a1a0f;border:1px solid #854d0e;border-radius:8px;
            padding:14px 18px;margin-bottom:20px;max-width:640px;">
  <div style="display:flex;align-items:flex-start;gap:12px;margin-bottom:14px;">
    <span style="font-size:1.3rem;flex-shrink:0;">📡</span>
    <div>
      <div style="font-size:0.88rem;font-weight:600;color:#fde68a;margin-bottom:4px;">
        Federal Communications Commission (FCC) licence active — expires {_exp_str}
      </div>
      <div style="font-size:0.78rem;color:#92400e;line-height:1.5;">
        Extend your licence below, or hire a
        <a href="/executives" style="color:#fbbf24;">CCO executive</a>
        for permanent access at lower long-term cost.
      </div>
    </div>
  </div>
  {_tier_buttons("+")}
</div>{_btn_style}"""
    else:
        cco_banner = f"""
<div style="background:#1e1a2e;border:1px solid #4c1d95;border-radius:8px;
            padding:14px 18px;margin-bottom:20px;max-width:640px;">
  <div style="display:flex;align-items:flex-start;gap:12px;margin-bottom:16px;">
    <span style="font-size:1.3rem;flex-shrink:0;">🔒</span>
    <div>
      <div style="font-size:0.88rem;font-weight:600;color:#c4b5fd;margin-bottom:4px;">
        Chief Communications Officer required
      </div>
      <div style="font-size:0.78rem;color:#7c3aed;line-height:1.5;">
        Hire a <a href="/executives" style="color:#a78bfa;">CCO executive</a> for
        permanent access, or purchase a Federal Communications Commission (FCC)
        licence below for a fixed duration.
        Licences are convenient but cost more over time than keeping a CCO on payroll.
      </div>
    </div>
  </div>
  <div style="font-size:0.72rem;font-weight:bold;color:#475569;text-transform:uppercase;
              letter-spacing:.08em;margin-bottom:8px;">
    Federal Communications Commission (FCC) — Government Licence
  </div>
  {_tier_buttons()}
</div>{_btn_style}"""

    # ── Push Notifications ────────────────────────────────────────────────────
    push_body = f"""
<p style="font-size:0.78rem;color:#64748b;margin:8px 0 16px;">
  Push notifications appear even when the app is closed. Requires browser permission.
</p>
<div id="push-status-row" style="display:flex;align-items:center;gap:10px;margin-bottom:18px;">
  <span id="push-status-dot" style="width:8px;height:8px;border-radius:50%;
        background:#334155;flex-shrink:0;"></span>
  <span id="push-status-label" style="font-size:0.78rem;color:#64748b;">Checking…</span>
  <button id="push-enable-btn" onclick="requestPushPermission()"
          style="display:none;margin-left:auto;padding:6px 16px;background:#6366f1;
                 border:none;border-radius:5px;color:white;font-size:0.78rem;cursor:pointer;">
    Enable Push
  </button>
  <button id="push-disable-btn" onclick="disablePush()"
          style="display:none;margin-left:auto;padding:6px 16px;background:transparent;
                 border:1px solid #334155;border-radius:5px;color:#64748b;
                 font-size:0.78rem;cursor:pointer;">
    Disable Push
  </button>
</div>
<div id="push-toggles">
  {_toggle("notif_push_dms",          push_dms,  "Direct Messages",    "Get notified when someone sends you a DM",                              disabled=not has_cco)}
  {_toggle("notif_push_contracts",    push_con,  "Contract Updates",   "Offers, acceptances, breaches, and completions",                        disabled=not has_cco)}
  {_toggle("notif_push_business",     push_biz,  "Business Alerts",    "Can't afford wages, missing inputs, out of stock, dismantling complete", disabled=not has_cco)}
  {_toggle("notif_push_land",         push_land, "Land Alerts",        "Plot sold, buy order filled, efficiency floor reached",                  disabled=not has_cco)}
  {_toggle("notif_push_execs",        push_exec, "Executive Alerts",   "Hired, fired, quit, salary missed, retired, school sent and complete",   disabled=not has_cco)}
  {_toggle("notif_push_trades",       push_trd,  "Trade Alerts",       "Trusted swap proposed, executed, rejected, or expired",                  disabled=not has_cco)}
  {_toggle("notif_push_corporate",    push_corp, "Corporate Alerts",   "Acquisition offers, counter-offers, diffuse notices, renegotiation proposals, buyout events, and income sweeps", disabled=not has_cco)}
  {_toggle("notif_push_govt",         push_govt, "Government Alerts",  "Hoard tax, district tax failure, liens, city membership changes",        disabled=not has_cco)}
  {_toggle("notif_push_tasks_events", push_tevt, "Tasks &amp; Events", "Task completions, event go-live / ended alerts, and trophy awards",      disabled=not has_cco)}
</div>"""

    # ── Sounds ────────────────────────────────────────────────────────────────
    sounds_body = f"""
<p style="font-size:0.78rem;color:#64748b;margin:8px 0 16px;">
  Play a sound when an in-game notification arrives while you have the app open.
</p>
{_toggle("notif_sounds", sounds, "Notification Sounds", "Short audio cue for incoming alerts", disabled=not has_cco)}"""

    # ── Badging ───────────────────────────────────────────────────────────────
    badge_body = f"""
<p style="font-size:0.78rem;color:#64748b;margin:8px 0 16px;">
  Show your total unread count on the Wadsworth app icon (installed PWA only).
</p>
{_toggle("notif_badge", badge, "App Icon Badge", "Displays unread count on home screen / taskbar icon", disabled=not has_cco)}"""

    form_start = '<form method="post" action="/api/settings/notifications" id="notif-form">'
    form_end   = '</form>'

    # Always rendered: toggle animation + push status indicator
    base_js = """
<script>
// Animate toggle knob on click without waiting for server round-trip
document.querySelectorAll('input[type=checkbox]').forEach(function(cb) {
  cb.addEventListener('change', function() {
    var track = document.querySelector('.ntog[data-for="' + this.id + '"]');
    var knob  = track && track.querySelector('div');
    if (!track || !knob) return;
    var on = this.checked;
    track.style.background    = on ? '#6366f1' : '#1e293b';
    track.style.borderColor   = on ? '#6366f1' : '#334155';
    knob.style.left           = on ? '22px'    : '2px';
  });
});

// Push permission status (always shown so label never stays "Checking…")
(function() {
  var dot   = document.getElementById('push-status-dot');
  var lbl   = document.getElementById('push-status-label');
  var enBtn = document.getElementById('push-enable-btn');
  var disBtn = document.getElementById('push-disable-btn');
  var togs  = document.getElementById('push-toggles');

  function setStatus(perm) {
    if (perm === 'granted') {
      dot.style.background = '#4ade80';
      lbl.textContent = 'Push enabled';
      if (disBtn) disBtn.style.display = 'inline-block';
      enBtn.style.display = 'none';
      if (togs) togs.style.opacity = '1';
    } else if (perm === 'denied') {
      dot.style.background = '#ef4444';
      lbl.textContent = 'Push blocked — allow it in browser site settings';
      enBtn.style.display = 'none';
      if (disBtn) disBtn.style.display = 'none';
      if (togs) { togs.style.opacity = '0.4'; togs.style.pointerEvents = 'none'; }
    } else {
      dot.style.background = '#f59e0b';
      lbl.textContent = 'Push not enabled';
      enBtn.style.display = 'none';
      if (disBtn) disBtn.style.display = 'none';
      if (togs) { togs.style.opacity = '0.4'; togs.style.pointerEvents = 'none'; }
    }
  }

  if (!('Notification' in window)) {
    lbl.textContent = 'Push not supported in this browser';
    if (togs) { togs.style.opacity = '0.4'; togs.style.pointerEvents = 'none'; }
    return;
  }
  setStatus(Notification.permission);
})();
</script>"""

    # CCO-gated: subscribe/enable button logic
    subscribe_js = """
<script>
(function() {
  var lbl = document.getElementById('push-status-label');
  var enBtn = document.getElementById('push-enable-btn');

  function _urlB64ToUint8(b64) {
    var pad = '='.repeat((4 - b64.length % 4) % 4);
    var b   = (b64 + pad).replace(/-/g, '+').replace(/_/g, '/');
    var raw = atob(b);
    var arr = new Uint8Array(raw.length);
    for (var i = 0; i < raw.length; ++i) arr[i] = raw.charCodeAt(i);
    return arr;
  }

  function _subscribePush() {
    lbl.textContent = 'Subscribing\u2026';
    fetch('/api/push/public-key')
      .then(function(r) { return r.text(); })
      .then(function(pubKey) {
        if (!pubKey) throw new Error('No VAPID key from server');
        return navigator.serviceWorker.ready.then(function(reg) {
          return reg.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: _urlB64ToUint8(pubKey),
          });
        });
      })
      .then(function(sub) {
        return fetch('/api/push/subscribe', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify(sub),
          credentials: 'same-origin',
        });
      })
      .then(function(r) { return r.json(); })
      .then(function(d) {
        if (d.ok) {
          lbl.textContent = 'Push enabled';
          var dot = document.getElementById('push-status-dot');
          if (dot) dot.style.background = '#4ade80';
          var disBtn = document.getElementById('push-disable-btn');
          if (disBtn) disBtn.style.display = 'inline-block';
          if (enBtn) enBtn.style.display = 'none';
          var togs = document.getElementById('push-toggles');
          if (togs) togs.style.opacity = '1';
        } else {
          lbl.textContent = 'Subscription error: ' + (d.error || '?');
        }
      })
      .catch(function(err) {
        lbl.textContent = 'Subscription failed: ' + err.message;
        console.error('[Push subscribe]', err);
      });
  }

  // Show enable button now that CCO is unlocked
  if ('Notification' in window && Notification.permission === 'default') {
    if (enBtn) enBtn.style.display = 'inline-block';
  }

  // Auto-subscribe if permission already granted
  if ('Notification' in window && Notification.permission === 'granted') {
    navigator.serviceWorker && navigator.serviceWorker.ready.then(function(reg) {
      reg.pushManager.getSubscription().then(function(existing) {
        if (!existing) _subscribePush();
      });
    });
  }

  window.disablePush = function() {
    navigator.serviceWorker && navigator.serviceWorker.ready.then(function(reg) {
      reg.pushManager.getSubscription().then(function(sub) {
        var unsub = sub ? sub.unsubscribe() : Promise.resolve();
        return unsub.then(function() {
          return fetch('/api/push/unsubscribe', {
            method: 'POST', credentials: 'same-origin',
          });
        });
      }).then(function() {
        var lbl   = document.getElementById('push-status-label');
        var dot   = document.getElementById('push-status-dot');
        var enBtn = document.getElementById('push-enable-btn');
        var disBtn = document.getElementById('push-disable-btn');
        var togs  = document.getElementById('push-toggles');
        if (lbl)   lbl.textContent = 'Push not enabled';
        if (dot)   dot.style.background = '#f59e0b';
        if (enBtn) enBtn.style.display = 'inline-block';
        if (disBtn) disBtn.style.display = 'none';
        if (togs)  { togs.style.opacity = '0.4'; togs.style.pointerEvents = 'none'; }
      }).catch(function(err) {
        console.error('[Push disable]', err);
      });
    });
  };

  window.requestPushPermission = function() {
    lbl.textContent = 'Check your browser \u2014 a permission prompt may have appeared\u2026';
    Notification.requestPermission().then(function(p) {
      if (p === 'granted') _subscribePush();
      else if (p === 'denied') {
        lbl.textContent = 'Push blocked \u2014 allow it in browser site settings';
        var dot = document.getElementById('push-status-dot');
        if (dot) dot.style.background = '#ef4444';
        if (enBtn) enBtn.style.display = 'none';
      }
    }).catch(function(err) {
      lbl.textContent = 'Error: ' + err.message;
      console.error('[Push]', err);
    });
  };
})();
</script>"""

    # Tutorial welcome banner — shown when arriving from Tutorial 1 completion
    from datetime import datetime as _dt
    _rental_expires_raw = getattr(player, "cco_rental_expires", None)
    _trial_days_left = 0
    if _rental_expires_raw and _rental_expires_raw > _dt.utcnow():
        _trial_days_left = max(1, (_rental_expires_raw - _dt.utcnow()).days + 1)

    tutorial_banner = ""
    if from_tutorial and _trial_days_left:
        tutorial_banner = f"""
<div style="background:linear-gradient(135deg,#052e16 0%,#0a3d1f 100%);
            border:1px solid #22c55e;border-radius:8px;padding:20px 24px;margin-bottom:24px;">
  <div style="font-size:1.1rem;font-weight:bold;color:#22c55e;margin-bottom:10px;">
    🎓 Tutorial Complete — Your 30-Day Notification Trial is Active!
  </div>
  <p style="color:#86efac;font-size:0.88rem;line-height:1.7;margin:0 0 14px 0;">
    As a reward for completing <strong>Startup Company</strong>, you have
    <strong>{_trial_days_left} days</strong> of free notification access.
    Configure everything below — no CCO executive needed yet.
  </p>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:14px;">
    <div style="background:#0a1a0f;border:1px solid #166534;border-radius:6px;padding:12px;">
      <div style="color:#4ade80;font-weight:bold;font-size:0.85rem;margin-bottom:6px;">🔔 In-Game Notifications</div>
      <p style="color:#94a3b8;font-size:0.8rem;line-height:1.6;margin:0;">
        Appear as a banner inside the app while you're playing. Stored in your notification bell — always free, never missed.
      </p>
    </div>
    <div style="background:#0a1a0f;border:1px solid #166534;border-radius:6px;padding:12px;">
      <div style="color:#4ade80;font-weight:bold;font-size:0.85rem;margin-bottom:6px;">📲 Push Notifications</div>
      <p style="color:#94a3b8;font-size:0.8rem;line-height:1.6;margin:0;">
        Delivered to your device even when the app is closed — like a text message. Requires browser permission below.
      </p>
    </div>
  </div>
  <p style="color:#64748b;font-size:0.78rem;margin:0;">
    After your trial expires, a <strong>CCO executive</strong> or <strong>FCC licence</strong>
    (available in Settings → Notifications) is required to keep configuring these preferences.
  </p>
</div>"""

    return (
        tutorial_banner
        + cco_banner
        + form_start
        + _section("Push Notifications", push_body)
        + _section("In-App Sounds", sounds_body)
        + _section("App Icon Badge", badge_body)
        + form_end
        + base_js
        + (subscribe_js if has_cco else "")
    )


@router.post("/api/settings/notifications")
def api_save_notifications(
    session_token:           Optional[str] = Cookie(None),
    notif_push_dms:          Optional[str] = Form(None),
    notif_push_contracts:    Optional[str] = Form(None),
    notif_push_business:     Optional[str] = Form(None),
    notif_push_land:         Optional[str] = Form(None),
    notif_push_execs:        Optional[str] = Form(None),
    notif_push_trades:       Optional[str] = Form(None),
    notif_push_corporate:    Optional[str] = Form(None),
    notif_push_govt:         Optional[str] = Form(None),
    notif_push_tasks_events: Optional[str] = Form(None),
    notif_sounds:            Optional[str] = Form(None),
    notif_badge:             Optional[str] = Form(None),
):
    import auth as _auth
    player = _require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    try:
        from executive import player_has_cco, get_db as _exec_db
        _edb = _exec_db()
        _has_cco = player_has_cco(_edb, player.id)
        _edb.close()
    except Exception:
        _has_cco = False
    if _has_cco:
        try:
            db = _auth.get_db()
            p  = db.query(_auth.Player).filter(_auth.Player.id == player.id).first()
            if p:
                p.notif_push_dms          = notif_push_dms          == "on"
                p.notif_push_contracts    = notif_push_contracts    == "on"
                p.notif_push_business     = notif_push_business     == "on"
                p.notif_push_land         = notif_push_land         == "on"
                p.notif_push_execs        = notif_push_execs        == "on"
                p.notif_push_trades       = notif_push_trades       == "on"
                p.notif_push_corporate    = notif_push_corporate    == "on"
                p.notif_push_govt         = notif_push_govt         == "on"
                p.notif_push_tasks_events = notif_push_tasks_events == "on"
                p.notif_sounds            = notif_sounds            == "on"
                p.notif_badge             = notif_badge             == "on"
                db.commit()
            db.close()
        except Exception as e:
            print(f"[Settings] notif save error: {e}")
    return RedirectResponse(url="/settings?tab=notifications", status_code=303)


# Federal Communications Commission (FCC) licence tiers: key → {label, hours, price_usd}
_CCO_RENTAL_TIERS = {
    "6h":  {"label": "6 Hours",  "hours": 6,   "price": 500},
    "1d":  {"label": "1 Day",    "hours": 24,  "price": 1_500},
    "3d":  {"label": "3 Days",   "hours": 72,  "price": 3_500},
    "1w":  {"label": "1 Week",   "hours": 168, "price": 7_000},
    "2w":  {"label": "2 Weeks",  "hours": 336, "price": 12_000},
    "1mo": {"label": "1 Month",  "hours": 720, "price": 20_000},
}


@router.post("/api/settings/cco-rental")
def api_cco_rental(
    session_token: Optional[str] = Cookie(None),
    tier: str = Form(...),
):
    """Purchase or extend a Federal Communications Commission (FCC) licence. Payment goes to the government."""
    player = _require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player

    tier_data = _CCO_RENTAL_TIERS.get(tier)
    if not tier_data:
        return RedirectResponse(url="/settings?tab=notifications&msg=invalid_tier", status_code=303)

    price = tier_data["price"]
    hours = tier_data["hours"]

    # Deduct from player using their legal tender (multi-currency aware)
    from reserve_banks import spend_player_funds, credit_usd
    ok, err = spend_player_funds(player.id, price)
    if not ok:
        return RedirectResponse(url=f"/settings?tab=notifications&msg={err}", status_code=303)

    # Credit government treasury (always USD)
    GOVERNMENT_PLAYER_ID = 0
    credit_usd(GOVERNMENT_PLAYER_ID, price)

    # Set / extend rental expiry
    from datetime import datetime, timedelta
    import auth as _auth
    db = _auth.get_db()
    try:
        p = db.query(_auth.Player).filter(_auth.Player.id == player.id).first()
        if p:
            now = datetime.utcnow()
            current = getattr(p, "cco_rental_expires", None)
            if current and current > now:
                p.cco_rental_expires = current + timedelta(hours=hours)
            else:
                p.cco_rental_expires = now + timedelta(hours=hours)
            db.commit()
    except Exception as e:
        print(f"[Settings] cco_rental update error: {e}")
        db.rollback()
    finally:
        db.close()

    return RedirectResponse(url="/settings?tab=notifications", status_code=303)


def _widgets_tab(player) -> str:
    return """
<div style="max-width:680px;">
    <h2 style="color:#e5e7eb;margin:0 0 6px 0;font-size:1.1rem;">Android Home-Screen Widgets</h2>
    <p style="color:#94a3b8;font-size:0.88rem;margin:0 0 20px 0;">
        Widgets show your live balance, recent transactions, market data, and chat — directly
        on your Android home screen without opening the app.
    </p>

    <!-- Device Link Status -->
    <div id="widget-status-box" style="background:#0f172a;border:1px solid #1e293b;border-radius:8px;padding:16px 18px;margin-bottom:20px;">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">
            <span id="widget-status-icon" style="font-size:1.2rem;">⏳</span>
            <span id="widget-status-text" style="color:#94a3b8;font-size:0.9rem;">Checking device link status…</span>
        </div>
        <button id="widget-link-btn"
                onclick="linkDevice()"
                style="background:#6366f1;color:#fff;border:none;padding:10px 20px;border-radius:6px;
                       cursor:pointer;font-size:0.85rem;font-weight:600;width:100%;">
            Link This Device to My Account
        </button>
        <p style="color:#475569;font-size:0.78rem;margin:10px 0 0 0;">
            Tap this button while logged in to authorise your Android device to display your data
            in home-screen widgets. You only need to do this once per device.
        </p>
    </div>

    <!-- Available Widgets -->
    <h3 style="color:#cbd5e1;font-size:0.95rem;margin:0 0 12px 0;">Available Widgets</h3>
    <div style="display:grid;gap:10px;">
        <div style="background:#0f172a;border:1px solid #1e293b;border-radius:8px;padding:14px 16px;">
            <div style="color:#e2e8f0;font-weight:600;margin-bottom:4px;">Balance + Alerts</div>
            <div style="color:#64748b;font-size:0.82rem;">Your live balance and last 10 transactions. Tap to open the app.</div>
        </div>
        <div style="background:#0f172a;border:1px solid #1e293b;border-radius:8px;padding:14px 16px;">
            <div style="color:#e2e8f0;font-weight:600;margin-bottom:4px;">WBC-50 Index</div>
            <div style="color:#64748b;font-size:0.82rem;">Live Wadsworth Business Composite index value, 7-day sparkline, and top 5 constituents.</div>
        </div>
        <div style="background:#0f172a;border:1px solid #1e293b;border-radius:8px;padding:14px 16px;">
            <div style="color:#e2e8f0;font-weight:600;margin-bottom:4px;">Bond Yields</div>
            <div style="color:#64748b;font-size:0.82rem;">Live yield rates for all reserve-bank currencies with 24-hour change indicators.</div>
        </div>
        <div style="background:#0f172a;border:1px solid #1e293b;border-radius:8px;padding:14px 16px;">
            <div style="color:#e2e8f0;font-weight:600;margin-bottom:4px;">Forex Rates</div>
            <div style="color:#64748b;font-size:0.82rem;">Foreign exchange rates vs USD for all active currencies.</div>
        </div>
        <div style="background:#0f172a;border:1px solid #1e293b;border-radius:8px;padding:14px 16px;">
            <div style="color:#e2e8f0;font-weight:600;margin-bottom:4px;">Global Chat / Trade Chat</div>
            <div style="color:#64748b;font-size:0.82rem;">Live feed of the last 25 messages from the Global or Trade chat rooms.</div>
        </div>
    </div>

    <!-- Setup Instructions -->
    <h3 style="color:#cbd5e1;font-size:0.95rem;margin:20px 0 12px 0;">Setup Instructions</h3>
    <ol style="color:#94a3b8;font-size:0.85rem;line-height:2;padding-left:20px;margin:0;">
        <li>Install the Wadsworth app from the Play Store (or sideload the APK)</li>
        <li>Open the app and log in to your account</li>
        <li>Come to <strong style="color:#e5e7eb;">Settings → Widgets</strong> and tap <em>Link This Device</em></li>
        <li>Long-press your home screen → Widgets → find "Wadsworth" widgets → drag one to your screen</li>
        <li>If a widget shows <em>"Open app to log in"</em>, open the app and tap Link This Device again</li>
    </ol>
</div>

<script>
(function() {
    var stored = null;
    try { stored = sessionStorage.getItem('_wdid'); } catch(e) {}

    var statusIcon = document.getElementById('widget-status-icon');
    var statusText = document.getElementById('widget-status-text');

    if (!stored) {
        statusIcon.textContent = '⚠️';
        statusText.textContent = 'No device ID found. Are you using the Android app? Open the app first, then come back here.';
        statusText.style.color = '#f59e0b';
    } else {
        // Check if this device is already linked
        fetch('/api/widget/status?device_id=' + encodeURIComponent(stored), {credentials:'same-origin'})
            .then(function(r) { return r.json(); })
            .then(function(d) {
                if (d.linked) {
                    statusIcon.textContent = '✅';
                    statusText.textContent = 'This device is linked to your account. Widgets should work!';
                    statusText.style.color = '#4ade80';
                } else {
                    statusIcon.textContent = '🔴';
                    statusText.textContent = 'This device is not linked yet. Tap the button below to link it.';
                    statusText.style.color = '#f87171';
                }
            })
            .catch(function() {
                statusIcon.textContent = '❓';
                statusText.textContent = 'Could not check status. Check your connection.';
            });
    }

    window.linkDevice = function() {
        var btn = document.getElementById('widget-link-btn');
        var wdid = null;
        try { wdid = sessionStorage.getItem('_wdid'); } catch(e) {}
        if (!wdid) {
            alert('No device ID detected. Please open this page from inside the Wadsworth Android app.');
            return;
        }
        btn.textContent = 'Linking…';
        btn.disabled = true;
        fetch('/api/widget/link?device_id=' + encodeURIComponent(wdid), {credentials:'same-origin'})
            .then(function(r) { return r.json(); })
            .then(function(d) {
                if (d.ok) {
                    statusIcon.textContent = '✅';
                    statusText.textContent = 'Device linked! Your widgets will now show live data.';
                    statusText.style.color = '#4ade80';
                    btn.textContent = '✓ Linked!';
                    btn.style.background = '#16a34a';
                } else {
                    btn.textContent = 'Link This Device to My Account';
                    btn.disabled = false;
                    alert('Link failed: ' + (d.error || 'unknown error'));
                }
            })
            .catch(function() {
                btn.textContent = 'Link This Device to My Account';
                btn.disabled = false;
                alert('Network error — check your connection and try again.');
            });
    };
})();
</script>
"""


_scan_skins_cache: list | None = None
_scan_skins_ts: float = 0.0
_SCAN_SKINS_TTL: float = 60.0  # re-read disk at most once per minute


def _scan_skins() -> list:
    """Return list of (key, name, description, tier, accent) for every skin CSS file.
    Result is cached for _SCAN_SKINS_TTL seconds to avoid re-reading files on every
    settings page load and every skin save.
    """
    global _scan_skins_cache, _scan_skins_ts
    import time as _t
    now = _t.monotonic()
    if _scan_skins_cache is not None and (now - _scan_skins_ts) < _SCAN_SKINS_TTL:
        return _scan_skins_cache

    import glob, re
    from skin_utils import _SAFE_SKIN_RE as _safe_re
    skins = []
    for path in sorted(glob.glob("static/skins/*.css")):
        fname = os.path.basename(path)
        if fname == "wadsworth-base.css":
            continue
        key = fname[:-4]
        # Skip files whose names aren't safe identifiers — they can't be injected
        # into JS event-handler attributes without escaping.
        if not _safe_re.match(key):
            continue
        name = key.replace("-", " ").replace("_", " ").title()
        description = ""
        tier = "free"
        accent = ""
        try:
            with open(path, encoding="utf-8") as f:
                content = f.read(8000)  # enough for header comments + :root accent vars
            header = content[:2000]
            m = re.search(r"Wadsworth Skin:\s*(.+)", header)
            if m:
                name = m.group(1).strip()
            m = re.search(r"Description:\s*(.*?)(?=\n\s*\*\s*\w+:|$)", header, re.DOTALL)
            if m:
                raw = m.group(1)
                description = re.sub(r"\n\s*\*\s*", " ", raw).strip()
            m = re.search(r"Tier:\s*(\w+)", header)
            if m:
                tier = m.group(1).strip().lower()
            # Extract primary/secondary/tertiary accent colors for the preview swatch row.
            # Matches #hex, rgb(...), hsl(...), oklch(...) — any valid CSS color function.
            accents = []
            for var in ("--accent", "--accent-2", "--accent-3", "--bg-page"):
                m2 = re.search(
                    rf"{re.escape(var)}\s*:\s*"
                    r"(#[0-9a-fA-F]{3,8}|(?:rgb|hsl|oklch|color)a?\([^)]+\))",
                    content,
                )
                if m2:
                    accents.append(m2.group(1).strip())
            accent = "|".join(accents[:4])  # pipe-separated list of up to 4 colors
        except Exception:
            pass
        skins.append((key, name, description, tier, accent))
    _scan_skins_cache = skins
    _scan_skins_ts = now
    return skins


def _skins_tab(player) -> str:
    from skin_utils import is_pro as _is_pro, _SKIN_V as _skin_v

    is_pro_user = _is_pro(player)
    current_skin = getattr(player, "skin", "default") or "default"

    skins = _scan_skins()

    def _build_card(row):
        key, name, description, tier = row[0], row[1], row[2], row[3]
        accent = row[4] if len(row) > 4 else ""
        is_current = key == current_skin
        locked = tier == "pro" and not is_pro_user

        border_style = "border:2px solid var(--accent)" if is_current else "border:2px solid var(--border)"
        active_indicator = (
            '<span style="display:inline-block;width:7px;height:7px;background:var(--accent);'
            'border-radius:50%;margin-right:5px;"></span>' if is_current else ""
        )
        pro_badge = (
            '<span style="font-size:0.6rem;background:var(--accent-3);color:var(--text-on-danger);'
            'padding:1px 6px;border-radius:8px;font-weight:700;margin-left:5px;">PRO</span>'
            if tier == "pro" else ""
        )

        swatch = ""
        if accent:
            colors = accent.split("|")
            dots = "".join(
                f'<div style="width:14px;height:14px;border-radius:50%;flex-shrink:0;'
                f'background:{c};border:1px solid rgba(0,0,0,0.15);"></div>'
                for c in colors if c
            )
            swatch = f'<div style="display:flex;gap:3px;align-items:center;">{dots}</div>'

        if is_current:
            action_btns = (
                '<button disabled style="flex:1;padding:7px;background:var(--accent);'
                'color:var(--text-on-accent);border:none;border-radius:var(--radius-sm);'
                'font-size:0.8rem;font-weight:700;cursor:default;">✓ Active</button>'
            )
        elif locked:
            action_btns = (
                '<button disabled style="flex:1;padding:7px;background:var(--bg-card-2);'
                'color:var(--text-muted);border:1px solid var(--border);border-radius:var(--radius-sm);'
                'font-size:0.8rem;font-weight:700;cursor:not-allowed;">🔒 Pro Only</button>'
            )
        else:
            action_btns = (
                f'<button onmouseenter="previewSkin(\'{key}\')" onmouseleave="revertPreview()" '
                f'onclick="saveSkin(\'{key}\', this)" '
                f'style="flex:1;padding:7px;background:var(--bg-card-2);color:var(--accent);'
                f'border:1px solid var(--accent);border-radius:var(--radius-sm);'
                f'font-size:0.8rem;font-weight:700;cursor:pointer;transition:background 0.15s;">Apply</button>'
            )

        return f"""
        <div class="skin-card" data-key="{key}" style="background:var(--bg-card);{border_style};
            border-radius:var(--radius-lg);padding:14px;display:flex;flex-direction:column;gap:8px;">
            <div style="display:flex;align-items:center;gap:4px;flex-wrap:wrap;">
                {active_indicator}
                <span style="font-size:0.88rem;font-weight:700;color:var(--text-bright);">{name}</span>
                {pro_badge}
            </div>
            {swatch}
            <p style="font-size:0.75rem;color:var(--text-muted);margin:0;
                min-height:28px;line-height:1.4;">{description or "No description."}</p>
            <div style="display:flex;gap:6px;">{action_btns}</div>
        </div>"""

    free_skins = sorted([r for r in skins if r[3] != "pro"], key=lambda r: r[1].lower())
    pro_skins  = sorted([r for r in skins if r[3] == "pro"],  key=lambda r: r[1].lower())

    free_cards = "".join(_build_card(r) for r in free_skins) or '<p style="color:var(--text-muted);">None available.</p>'
    pro_cards  = "".join(_build_card(r) for r in pro_skins)  or '<p style="color:var(--text-muted);">None available.</p>'

    cards = f"""
    <h4 style="margin:0 0 10px;color:var(--text-secondary);font-size:0.8rem;
        text-transform:uppercase;letter-spacing:0.08em;">Free</h4>
    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:12px;margin-bottom:24px;">
        {free_cards}
    </div>
    <h4 style="margin:0 0 10px;color:var(--accent-3);font-size:0.8rem;
        text-transform:uppercase;letter-spacing:0.08em;">🌟 Pro Subscribers</h4>
    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:12px;">
        {pro_cards}
    </div>"""

    pro_notice = ""
    if not is_pro_user:
        pro_notice = """
        <div id="wds-pro-banner" style="background:var(--accent-3-bg);border:1px solid var(--accent-3);
            border-radius:var(--radius-md);padding:12px 16px;margin-bottom:18px;
            display:flex;align-items:center;gap:12px;">
            <span style="font-size:1.3rem;">🌟</span>
            <div style="flex:1;">
                <strong style="color:var(--accent-3);font-size:0.85rem;">Wadsworth Pro</strong>
                <p style="color:var(--text-muted);font-size:0.78rem;margin:2px 0 0;">
                    Unlock Pro skins and exclusive features.</p>
            </div>
            <button id="wds-sub-btn" onclick="wdsSubscribe()"
                style="background:var(--accent-3);color:#000;border:none;border-radius:6px;
                padding:7px 16px;font-size:0.8rem;font-weight:700;cursor:pointer;
                white-space:nowrap;display:none;">Subscribe</button>
            <span id="wds-sub-status" style="font-size:0.75rem;color:var(--text-muted);"></span>
        </div>
        <script>
        (function() {
          var SUB_ID = 'wads_basic';
          var _service = null;

          async function _getService() {
            if (!('getDigitalGoodsService' in window)) return null;
            try {
              var svc = await window.getDigitalGoodsService('https://play.google.com/billing');
              return svc;
            } catch(e) { return null; }
          }

          async function _verifyToken(token) {
            var r = await fetch('/api/play/verify-subscription', {
              method: 'POST',
              headers: {'Content-Type': 'application/json'},
              credentials: 'same-origin',
              body: JSON.stringify({purchase_token: token})
            });
            // Always return the body so callers can surface the error message.
            try { return await r.json(); } catch(e) { return {ok: false, error: 'no response'}; }
          }

          function _setStatus(msg) {
            var el = document.getElementById('wds-sub-status');
            if (el) el.textContent = msg;
          }

          // On page load: try to restore entitlement from any existing purchase
          // (covers reinstalls, account switches, and cross-device restores).
          async function _tryRestore() {
            var svc = await _getService();
            if (!svc) return;
            _service = svc;
            // Show the subscribe button now that we know billing is available
            var btn = document.getElementById('wds-sub-btn');
            if (btn) btn.style.display = '';

            try {
              var existing = await svc.listPurchases();
              for (var i = 0; i < existing.length; i++) {
                if (existing[i].itemId === SUB_ID) {
                  _setStatus('Restoring…');
                  var result = await _verifyToken(existing[i].purchaseToken);
                  if (result && result.active) {
                    _setStatus('');
                    // Hide banner — subscriber state will show on next full page load
                    var banner = document.getElementById('wds-pro-banner');
                    if (banner) banner.innerHTML =
                      '<span style="font-size:1.3rem;">🌟</span>' +
                      '<strong style="color:var(--accent-3);font-size:0.85rem;margin-left:10px;">' +
                      'Wadsworth Pro Active</strong>';
                    return;
                  }
                  // Found the purchase but the server could not confirm it.
                  var errMsg = (result && result.error) ? result.error : 'unknown error';
                  var stateMsg = (result && result.state) ? ' (state: ' + result.state + ')' : '';
                  _setStatus('Verify failed: ' + errMsg + stateMsg + '. Tap Subscribe to retry.');
                  return;
                }
              }
              // No matching purchase found — nothing to restore.
              _setStatus('');
            } catch(e) { _setStatus(''); }
          }

          window.wdsSubscribe = async function() {
            var btn = document.getElementById('wds-sub-btn');
            if (btn) btn.disabled = true;
            _setStatus('Opening…');
            try {
              var svc = _service || await _getService();
              if (!svc) {
                _setStatus('Billing not available on this device.');
                if (btn) btn.disabled = false;
                return;
              }
              var req = new PaymentRequest(
                [{ supportedMethods: 'https://play.google.com/billing',
                   data: { sku: SUB_ID } }],
                { total: { label: 'Wadsworth Pro', amount: { currency: 'USD', value: '0' } } }
              );
              var response = await req.show();
              var token = response.details.purchaseToken;
              _setStatus('Verifying…');
              var result = await _verifyToken(token);
              await response.complete('success');
              if (result && result.active) {
                _setStatus('');
                var banner = document.getElementById('wds-pro-banner');
                if (banner) banner.innerHTML =
                  '<span style="font-size:1.3rem;">🌟</span>' +
                  '<strong style="color:var(--accent-3);font-size:0.85rem;margin-left:10px;">' +
                  'Wadsworth Pro Active — refresh to apply Pro skins!</strong>';
              } else {
                _setStatus('Verification failed — please try again.');
                if (btn) btn.disabled = false;
              }
            } catch(e) {
              // User cancelled or billing error
              _setStatus(e.name === 'AbortError' ? '' : 'Error: ' + e.message);
              if (btn) btn.disabled = false;
            }
          };

          // Kick off restore attempt silently in background
          _tryRestore();
        })();
        </script>"""
    else:
        pro_notice = """
        <div style="background:var(--accent-3-bg);border:1px solid var(--accent-3);
            border-radius:var(--radius-md);padding:12px 16px;margin-bottom:18px;
            display:flex;align-items:center;gap:10px;">
            <span style="font-size:1.3rem;">🌟</span>
            <strong style="color:var(--accent-3);font-size:0.85rem;">Wadsworth Pro — Active</strong>
        </div>"""

    return f"""
<div style="max-width:680px;">
    <h3 style="margin:0 0 4px;color:var(--text-secondary);font-family:var(--font-serif);">Skins</h3>
    <p style="color:var(--text-muted);font-size:0.82rem;margin:0 0 16px;">
        Choose a visual theme. Hover any skin to preview it. Changes apply on all devices.</p>
    {pro_notice}
    {cards}
    <p id="skin-preview-notice" style="color:var(--text-muted);font-size:0.74rem;
        margin:12px 0 0;display:none;">Previewing — hover away or click Apply to confirm.</p>
</div>
<script>
var _origSkin = document.documentElement.getAttribute('data-skin') || 'default';
var _skinVer = {_skin_v};  /* injected by server so preview URL matches the live cache-bust version */
var _previewActive = false;
var _previewTimer = null;

/* Use the id="skin-link" we stamp on the skin <link> tag — O(1), unambiguous. */
function _getSkinLink() {{
    return document.getElementById('skin-link');
}}

/* Shared revert logic used by both revertPreview() and saveSkin() error path. */
function _doRevert() {{
    document.documentElement.setAttribute('data-skin', _origSkin);
    var link = _getSkinLink();
    if (link && link.dataset.origHref) {{
        link.href = link.dataset.origHref;
        delete link.dataset.origHref;
    }}
    var notice = document.getElementById('skin-preview-notice');
    if (notice) notice.style.display = 'none';
}}

function previewSkin(key) {{
    /* Debounce: only fire the CSS swap after the cursor settles for 120 ms */
    clearTimeout(_previewTimer);
    _previewTimer = setTimeout(function() {{
        _previewActive = true;
        document.documentElement.setAttribute('data-skin', key);
        var link = _getSkinLink();
        if (link) {{
            if (!link.dataset.origHref) link.dataset.origHref = link.href;
            link.href = '/static/skins/' + key + '.css?v=' + _skinVer;
        }}
        var notice = document.getElementById('skin-preview-notice');
        if (notice) notice.style.display = 'block';
    }}, 120);
}}

function revertPreview() {{
    clearTimeout(_previewTimer);
    if (!_previewActive) return;
    _previewActive = false;
    _doRevert();
}}

function saveSkin(key, btn) {{
    clearTimeout(_previewTimer);
    _previewActive = false;  /* prevent mouseLeave from reverting during the save */
    var orig = btn.textContent;
    btn.textContent = '…';
    btn.disabled = true;
    fetch('/api/settings/skin', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/x-www-form-urlencoded'}},
        body: 'skin=' + encodeURIComponent(key)
    }}).then(function(r) {{ return r.json(); }}).then(function(d) {{
        if (d.ok) {{ location.reload(); }}
        else {{ _doRevert(); btn.textContent = d.error || 'Error'; btn.disabled = false; }}
    }}).catch(function() {{ _doRevert(); btn.textContent = orig; btn.disabled = false; }});
}}
</script>
"""


def _account_tab(player) -> str:
    try:
        from corporate_actions import is_player_bankrupt
        _bankrupt = is_player_bankrupt(player.id)
    except Exception:
        _bankrupt = False

    try:
        from ux import fmt_usd
        _restart_amt = fmt_usd(20000, "usd")
    except Exception:
        _restart_amt = "$20,000"

    if _bankrupt:
        bankruptcy_html = """
        <div style="background:#1e293b;border:1px solid #ef4444;border-radius:10px;padding:20px;">
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">
                <span style="font-size:1.4rem;">🔴</span>
                <strong style="color:#ef4444;">Bankruptcy — Active</strong>
            </div>
            <p style="color:#94a3b8;font-size:0.85rem;margin:0;">
                You are currently in a bankruptcy period. A red Q marker is shown next to your
                name on the stock market for the duration of the period.
            </p>
        </div>"""
    else:
        bankruptcy_html = f"""
        <div style="background:#1e293b;border:1px solid #ef4444;border-radius:10px;padding:20px;">
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">
                <span style="font-size:1.4rem;">💀</span>
                <strong style="color:#ef4444;">Declare Bankruptcy</strong>
            </div>
            <p style="color:#94a3b8;font-size:0.85rem;margin:0 0 16px;">
                <strong style="color:#ef4444;">Irreversible.</strong>
                Liquidates all assets — businesses, land, districts, inventory, stocks, crypto,
                executives, and ETF positions. Restarts account with {_restart_amt} + one prairie plot.
                Red Q marker for 30 days.
            </p>
            <form action="/api/corporate-actions/bankruptcy/declare" method="post"
                  onsubmit="return confirm('FINAL WARNING: This permanently liquidates ALL your assets and restarts your account with {_restart_amt}. This CANNOT be undone.') && prompt('Type BANKRUPT to confirm') === 'BANKRUPT'">
                <button type="submit"
                        style="background:#ef4444;color:#fff;border:none;padding:7px 16px;border-radius:6px;
                               font-size:.8rem;font-weight:700;cursor:pointer;font-family:inherit;">
                    💀 Declare Bankruptcy
                </button>
            </form>
        </div>"""

    return f"""
<div style="max-width:600px;">

    <h3 style="margin:0 0 6px;color:#94a3b8;">Estate &amp; Succession</h3>
    <p style="color:#64748b;font-size:0.82rem;margin:0 0 12px;">
        Manage heirs, succession planning, and the deceased player registry.
    </p>
    <a href="/estate"
       style="display:inline-block;padding:8px 20px;background:#1e293b;border:1px solid #94a3b8;
              color:#94a3b8;border-radius:6px;font-size:0.82rem;font-weight:700;text-decoration:none;">
        ⚖️ Open Estate Office
    </a>

    <hr style="border:none;border-top:1px solid #1e293b;margin:28px 0;">

    <h3 style="margin:0 0 6px;color:#ef4444;">Bankruptcy</h3>
    <p style="color:#64748b;font-size:0.82rem;margin:0 0 12px;">
        Nuclear option — permanently liquidates all assets and restarts your account.
    </p>
    {bankruptcy_html}
</div>
"""


@router.post("/api/settings/skin")
def api_save_skin(
    session_token: Optional[str] = Cookie(None),
    skin: str = Form(...),
):
    import auth as _auth
    from skin_utils import is_pro as _is_pro
    player = _require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return JSONResponse({"ok": False, "error": "Not authenticated"}, status_code=403)
    from skin_utils import _SAFE_SKIN_RE as _safe_re
    if not _safe_re.match(skin):
        return JSONResponse({"ok": False, "error": "Invalid skin name"})
    valid = {row[0]: row[3] for row in _scan_skins()}
    if skin not in valid:
        return JSONResponse({"ok": False, "error": "Unknown skin"})
    if valid[skin] == "pro" and not _is_pro(player):
        return JSONResponse({"ok": False, "error": "Pro subscription required"})
    db = None
    try:
        db = _auth.get_db()
        p = db.query(_auth.Player).filter(_auth.Player.id == player.id).first()
        if not p:
            return JSONResponse({"ok": False, "error": "Player not found"})
        p.skin = skin
        db.commit()
        return JSONResponse({"ok": True})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)})
    finally:
        if db is not None:
            try:
                db.close()
            except Exception:
                pass


@router.get("/settings", response_class=HTMLResponse)
def settings_page(
    session_token: Optional[str] = Cookie(None),
    tab: str = Query("audio"),
    from_tutorial: int = Query(0),
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
    elif tab == "tutorials":
        content = _tutorials_tab(player)
    elif tab == "notifications":
        content = _notifications_tab(player, from_tutorial=bool(from_tutorial))
    elif tab == "widgets":
        content = _widgets_tab(player)
    elif tab == "skins":
        content = _skins_tab(player)
    elif tab == "account":
        content = _account_tab(player)
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
