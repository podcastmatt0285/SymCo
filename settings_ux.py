"""
settings_ux.py — Player settings page.

GET /settings?tab=audio   — tabbed settings hub
Tabs: Audio (more can be added later)

GET /api/deep-dives       — JSON list of audio deep dive entries from wiki_media.json
"""

import json
import os
from typing import Optional
from fastapi import APIRouter, Cookie, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse

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


# ── Deep Dives API ────────────────────────────────────────────────────────────

@router.get("/api/deep-dives")
def api_deep_dives():
    """Return JSON array of audio deep dive entries from wiki_media.json."""
    try:
        path = os.path.join(os.path.dirname(__file__), "wiki_media.json")
        with open(path) as f:
            entries = json.load(f)
        dives = [
            {"youtube_id": e["youtube_id"], "title": e["title"], "description": e.get("description", "")}
            for e in entries
            if e.get("kind") == "audio" and e.get("youtube_id")
        ]
        return JSONResponse(dives)
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

            <!-- WCPR panel: deep dives list + YouTube embed -->
            <div class="rp-panel" id="rp-wcpr-panel">
                <div class="rp-panel-hdr">&#128251; Deep Dive Broadcasts</div>
                <div id="rp-dives-list" class="rp-tracklist">
                    <div style="color:#64748b;font-size:0.75rem;padding:12px 0;text-align:center;">Loading broadcasts…</div>
                </div>
                <div class="rp-yt-wrap" id="rp-yt-wrap">
                    <iframe id="rp-yt-iframe" src="" allow="accelerometer;autoplay;clipboard-write;encrypted-media;gyroscope;picture-in-picture" allowfullscreen></iframe>
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
    var rpDeepDives = [];
    var rpCurDive   = -1;
    var rpPending   = null;

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
            ? 'WLOL &mdash; Listen Out Loud'
            : 'WCPR 104.1 &mdash; Wadsworth Carter Public Radio';

        var m3 = $('rp-m3');
        if (m3) m3.textContent = isWlol ? 'WLOL FM' : '104.1 FM';

        var wcprPanel = $('rp-wcpr-panel'), wlolPanel = $('rp-wlol-panel');
        if (wcprPanel) wcprPanel.style.display = isWlol ? 'none' : 'block';
        if (wlolPanel) wlolPanel.style.display = isWlol ? 'block' : 'none';

        // Pause on station change
        if (rpPlaying) {
            if (!isWlol) {
                try { gsTogglePlay(); } catch(e) {}
            } else {
                rpPauseYT();
            }
            rpPlaying = false;
        }

        rpUpdateUI();
        if (isWlol) { rpSyncWlol(); rpBuildTrackList(); }
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
            rpToggleYT();
        }
    };

    // ── Skip ─────────────────────────────────────────────────────────────────
    window.rpSkip = function() {
        if (rpStation === 'wlol') {
            try { gsNext(); } catch(e) {}
            setTimeout(rpSyncWlol, 200);
        } else {
            if (rpDeepDives.length) {
                window.rpPlayDive((rpCurDive + 1) % rpDeepDives.length);
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
        }
    };

    // ── YouTube IFrame API ───────────────────────────────────────────────────
    var ytPlayer  = null;
    var ytReady   = false;
    var ytPollTimer = null;

    function rpLoadYTApi() {
        if (window.YT && window.YT.Player) { ytReady = true; return; }
        if ($('rp-yt-script')) return;
        var tag = document.createElement('script');
        tag.id  = 'rp-yt-script';
        tag.src = 'https://www.youtube.com/iframe_api';
        document.head.appendChild(tag);
    }

    window.onYouTubeIframeAPIReady = function() {
        ytReady = true;
        if (rpPending !== null) {
            window.rpPlayDive(rpPending);
            rpPending = null;
        }
    };

    window.rpPlayDive = function(idx) {
        if (!rpDeepDives.length || idx < 0 || idx >= rpDeepDives.length) return;
        rpCurDive = idx;
        var dive  = rpDeepDives[idx];

        document.querySelectorAll('.rp-dive-item').forEach(function(el, i) {
            el.classList.toggle('rp-active', i === idx);
        });

        var title = $('rp-title'), ref = $('rp-ref'), lbl = $('rp-track-lbl');
        if (title) title.textContent = dive.title;
        if (ref)   ref.textContent   = 'WCPR \u00B7 Deep Dive';
        if (lbl)   lbl.textContent   = 'Now Playing';

        var ytWrap = $('rp-yt-wrap');
        if (ytWrap) ytWrap.style.display = 'block';

        if (!ytReady) { rpPending = idx; rpLoadYTApi(); return; }

        if (ytPlayer) {
            ytPlayer.loadVideoById(dive.youtube_id);
        } else {
            ytPlayer = new YT.Player('rp-yt-iframe', {
                videoId: dive.youtube_id,
                playerVars: { autoplay: 1, rel: 0, modestbranding: 1 },
                events: {
                    onStateChange: function(e) {
                        rpPlaying = (e.data === YT.PlayerState.PLAYING);
                        rpUpdateUI();
                    }
                }
            });
        }
        rpPlaying = true;
        rpUpdateUI();
        rpStartYtPoll();
    };

    function rpToggleYT() {
        if (!ytPlayer) {
            if (rpDeepDives.length) window.rpPlayDive(rpCurDive >= 0 ? rpCurDive : 0);
            return;
        }
        var state = ytPlayer.getPlayerState();
        if (state === 1) { ytPlayer.pauseVideo(); rpPlaying = false; }
        else             { ytPlayer.playVideo();  rpPlaying = true;  }
        rpUpdateUI();
    }

    function rpPauseYT() {
        if (ytPlayer) { try { ytPlayer.pauseVideo(); } catch(e) {} }
        rpPlaying = false;
        rpStopYtPoll();
        rpUpdateUI();
    }

    function rpStartYtPoll() {
        rpStopYtPoll();
        ytPollTimer = setInterval(function() {
            if (!ytPlayer) return;
            try {
                var cur = ytPlayer.getCurrentTime() || 0;
                var dur = ytPlayer.getDuration()    || 0;
                if (dur > 0) {
                    var fill = $('rp-pfill'), time = $('rp-time');
                    if (fill) fill.style.width = ((cur / dur) * 100).toFixed(1) + '%';
                    if (time) time.textContent = fmtTime(cur) + ' / ' + fmtTime(dur);
                }
            } catch(e) {}
        }, 1000);
    }

    function rpStopYtPoll() {
        if (ytPollTimer) { clearInterval(ytPollTimer); ytPollTimer = null; }
    }

    // ── Deep Dives loader ────────────────────────────────────────────────────
    function rpLoadDeepDives() {
        fetch('/api/deep-dives')
            .then(function(r) { return r.json(); })
            .then(function(dives) {
                rpDeepDives = dives || [];
                var m1 = $('rp-m1');
                if (m1 && rpStation === 'wcpr') m1.textContent = rpDeepDives.length + ' broadcasts';
                var list = $('rp-dives-list');
                if (!list) return;
                if (!rpDeepDives.length) {
                    list.innerHTML = '<div style="color:#64748b;font-size:0.75rem;padding:12px 0;text-align:center;font-style:italic;">No broadcasts available yet.<br><span style="font-size:0.65rem;opacity:0.6;">Admins can add audio deep dives at /admin/wiki</span></div>';
                    return;
                }
                list.innerHTML = rpDeepDives.map(function(d, i) {
                    return '<div class="rp-dive-item" onclick="rpPlayDive(' + i + ')">'
                        + '<span class="rp-dive-num">' + (i + 1) + '</span>'
                        + '<span class="rp-dive-title">' + d.title + '</span>'
                        + '<span class="rp-dive-play">&#9654;</span>'
                        + '</div>';
                }).join('');
            })
            .catch(function() {
                var list = $('rp-dives-list');
                if (list) list.innerHTML = '<div style="color:#64748b;font-size:0.75rem;padding:12px 0;text-align:center;">Could not load broadcasts.</div>';
            });
    }

    // ── Init ─────────────────────────────────────────────────────────────────
    document.addEventListener('DOMContentLoaded', function() {

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
        rpLoadYTApi();
        rpLoadDeepDives();

        // Start waveform
        drawWave();

        // Slogan rotation
        setInterval(nextSlogan, 4000);

        // Progress sync loop
        setInterval(function() {
            if (rpStation === 'wlol') rpSyncWlolProgress();
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
