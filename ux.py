"""
ux.py
User interface module for the economic simulation.
Provides:
- HTML shell template with lien indicators
- Navigation routes
- Module-specific pages
- Financial terminal aesthetic
- Business creation and management
- Retail pricing controls
- Banking and investment views
- Lien dashboard
"""

from typing import Optional
from fastapi import APIRouter, Cookie, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, StreamingResponse
from datetime import timedelta
from datetime import datetime
import json as _json

router = APIRouter()

# ==========================
# STREAMING LOADER PAGE
# Yielded immediately for slow server-side pages so the loader renders
# before any computation begins.  A second streaming chunk uses
# document.open/write/close to replace this with the full shell page.
# Note: intentionally has no </body></html> — those arrive in chunk 2.
# ==========================
_STREAM_LOADER = """<!DOCTYPE html>
<html><head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Loading\u2026 \u00b7 Wadsworth</title>
  <style>
    *{box-sizing:border-box}
    body{background:#0D0806;margin:0;font-family:Georgia,serif;color:#F5F5DC}
    @keyframes nl-p{0%,100%{opacity:.3}50%{opacity:.7}}
    .nl-pulse{animation:nl-p 2s ease-in-out infinite}
  </style>
</head><body>
<div style="display:flex;position:fixed;inset:0;z-index:9999;background:#0D0806;color:#F5F5DC;font-family:Georgia,serif;align-items:center;justify-content:center;">
  <div style="position:relative;width:100%;max-width:420px;padding:40px;background:#1A0F0A;border:4px solid #2D1810;box-shadow:0 25px 50px rgba(0,0,0,.8);display:flex;flex-direction:column;align-items:center;box-sizing:border-box;">
    <div style="position:absolute;top:8px;left:8px;width:16px;height:16px;border-top:1px solid rgba(176,141,87,.4);border-left:1px solid rgba(176,141,87,.4)"></div>
    <div style="position:absolute;top:8px;right:8px;width:16px;height:16px;border-top:1px solid rgba(176,141,87,.4);border-right:1px solid rgba(176,141,87,.4)"></div>
    <div style="position:absolute;bottom:8px;left:8px;width:16px;height:16px;border-bottom:1px solid rgba(176,141,87,.4);border-left:1px solid rgba(176,141,87,.4)"></div>
    <div style="position:absolute;bottom:8px;right:8px;width:16px;height:16px;border-bottom:1px solid rgba(176,141,87,.4);border-right:1px solid rgba(176,141,87,.4)"></div>
    <div style="width:120px;height:120px;display:flex;align-items:center;justify-content:center;">
      <svg viewBox="0 0 201.5 207.54" style="width:100%;height:100%;filter:drop-shadow(0 0 20px rgba(229,0,0,0.4))" class="nl-pulse">
        <defs><linearGradient id="sl-lg"><stop style="stop-color:#e50000" offset="0"/><stop style="stop-color:#ff5555;stop-opacity:0" offset="1"/></linearGradient>
        <radialGradient id="sl-rg" cy="172.36" cx="342.86" gradientTransform="matrix(1 0 0 1.0417 0 -7.1934)" r="193.09" gradientUnits="userSpaceOnUse"><stop offset="0" style="stop-color:#e50000"/><stop offset="1" style="stop-color:#ff5555;stop-opacity:0"/></radialGradient></defs>
        <g transform="matrix(.15791 0 0 .15791 16.376 41.416)">
          <path style="fill-rule:evenodd;fill:#008000" d="m470.03 168.72c-34.81 0.55-75.98 25.14-120.23 80.45 287.24-187.49 318.09 308.34-234.97 802.83h105.53c11.37-10.2 22.06-19.9 30.58-28.8 404.11-366.71 376.62-856.94 219.09-854.48z"/>
          <path style="fill-rule:evenodd;fill:#008000" d="m834.13 625.57c77.98-166.27-189.49-144.42-409.81 189.81l-7.81-53.51c195.76-321.73 564.68-292.21 417.62-136.3z"/>
          <path style="fill-rule:evenodd;fill:#008000" d="m44.425 533.84c57.285-180.94 245.14 23.08 178.28 431.36l43.44-35.18c76.75-381.56-224.17-617.67-221.72-396.18z"/>
          <g transform="translate(17.143 -148.57)">
            <path style="fill-rule:evenodd;fill:#ff8e8e" d="m357.14 205.1c0.02 71.81-65.23 130.02-145.71 130.02-80.49 0-145.73-58.21-145.72-130.02-0.009-71.81 65.23-130.02 145.72-130.02 80.48-0.002 145.73 58.21 145.71 130.02z" transform="translate(219.15 -163.07)"/>
            <path style="fill-rule:evenodd;fill:#ff8e8e" d="m357.14 205.1c0.02 71.81-65.23 130.02-145.71 130.02-80.49 0-145.73-58.21-145.72-130.02-0.009-71.81 65.23-130.02 145.72-130.02 80.48-0.002 145.73 58.21 145.71 130.02z" transform="translate(27.721 -188.78)"/>
            <path style="fill-rule:evenodd;fill:#ff8e8e" d="m357.14 205.1c0.02 71.81-65.23 130.02-145.71 130.02-80.49 0-145.73-58.21-145.72-130.02-0.009-71.81 65.23-130.02 145.72-130.02 80.48-0.002 145.73 58.21 145.71 130.02z" transform="translate(-86.565 -45.925)"/>
            <path style="fill-rule:evenodd;fill:#ff8e8e" d="m357.14 205.1c0.02 71.81-65.23 130.02-145.71 130.02-80.49 0-145.73-58.21-145.72-130.02-0.009-71.81 65.23-130.02 145.72-130.02 80.48-0.002 145.73 58.21 145.71 130.02z" transform="translate(256.29 14.075)"/>
            <path style="fill-rule:evenodd;fill:#ff8e8e" d="m357.14 205.1c0.02 71.81-65.23 130.02-145.71 130.02-80.49 0-145.73-58.21-145.72-130.02-0.009-71.81 65.23-130.02 145.72-130.02 80.48-0.002 145.73 58.21 145.71 130.02z" transform="translate(150.58 151.22)"/>
            <path style="fill-rule:evenodd;fill:#ff8e8e" d="m357.14 205.1c0.02 71.81-65.23 130.02-145.71 130.02-80.49 0-145.73-58.21-145.72-130.02-0.009-71.81 65.23-130.02 145.72-130.02 80.48-0.002 145.73 58.21 145.71 130.02z" transform="translate(-12.279 128.36)"/>
            <path style="fill-rule:evenodd;fill:url(#sl-rg)" d="m500 300.93c-39.84 48.69-62.4-55.86-121.24-33.61s-6.6 115.57-68.68 105.42c-62.08-10.16 17.18-81.97-31.51-121.81-48.69-39.83-103.38 52.08-125.63-6.76-22.25-58.85 79.57-26.11 89.73-88.2 10.15-62.077-96.79-63.492-56.96-112.18 39.84-48.687 62.4 55.86 121.25 33.613 58.84-22.247 6.59-115.57 68.67-105.42 62.08 10.158-17.17 81.973 31.51 121.81 48.69 39.837 103.39-52.077 125.63 6.767 22.25 58.84-79.57 26.11-89.73 88.19-10.15 62.08 96.8 63.5 56.96 112.18z" transform="matrix(1.2126 0 0 1.2126 -107.6 -19.596)"/>
            <path style="fill-rule:evenodd;fill:#ffd5d5" d="m514.29 249.39c0.01 44.19-33.25 80.02-74.29 80.02s-74.3-35.83-74.29-80.02c-0.01-44.2 33.25-80.03 74.29-80.03s74.3 35.83 74.29 80.03z" transform="translate(-131.87 -59.983)"/>
          </g>
        </g>
      </svg>
    </div>
    <div style="margin-top:28px;width:100%;text-align:center;">
      <p style="font-size:9px;letter-spacing:.5em;text-transform:uppercase;color:#B08D57;font-weight:900;opacity:.4;margin:0 0 14px;">Wadsworth Executive Terminal</p>
      <div id="sl-msgs" style="height:88px;display:flex;flex-direction:column-reverse;align-items:center;gap:4px;overflow:hidden;"></div>
    </div>
    <div style="margin-top:20px;width:100%;height:3px;background:rgba(0,0,0,.6);border:1px solid rgba(176,141,87,.1);border-radius:9999px;overflow:hidden;">
      <div id="sl-bar" style="height:100%;width:0%;background:linear-gradient(to right,#8B4513,#B08D57,#F5F5DC);box-shadow:0 0 10px rgba(176,141,87,.5);transition:width .15s linear;"></div>
    </div>
    <div style="margin-top:12px;width:100%;display:flex;justify-content:space-between;align-items:center;padding:0 4px;">
      <div style="display:flex;gap:14px;opacity:.2;font-size:13px;">&#9646; &#9632; &#9650;</div>
      <span id="sl-pct" style="font-size:9px;font-family:monospace;opacity:.4;color:#B08D57;">0% SECURED</span>
    </div>
    <div style="position:absolute;bottom:-52px;font-size:9px;letter-spacing:.6em;text-transform:uppercase;opacity:.2;color:#B08D57;" class="nl-pulse">Handshake in Progress</div>
  </div>
</div>
<script>
(function(){
  var STEPS=["Initializing Secure Terminal...","Authenticating Executive Credentials...","Decrypting Asset Valuation Data...","Syncing Broadcast Signal...","Verifying Market Volatility...","Establishing Brass Inlay Connection...","Buffering Liquidity Pools...","Optimizing Yield Curves...","Parsing Capitol Schematics...","Engaging Stealth Protocols...","Allocating Surplus Capital...","Calibrating Brass Resonance...","Updating Ledger Entries...","Deploying Asset Containers...","Finalizing Handshake..."];
  var bar=document.getElementById('sl-bar'),pct=document.getElementById('sl-pct'),msgs=document.getElementById('sl-msgs');
  var prog=0,msgList=["Initializing Secure Terminal..."];
  function render(){msgs.innerHTML=msgList.slice(0,4).map(function(m,i){return'<p style="font-size:11px;font-style:italic;color:#B08D57;margin:0;opacity:'+(i===0?'1':'0.3')+';transform:scale('+(i===0?'1':'0.95')+')">'+(i===0?'&gt; ':'')+m+'</p>';}).join('');}
  render();
  setInterval(function(){prog+=5;if(prog>=100)prog=0;if(Math.floor(prog/15)>Math.floor((prog-5)/15)){msgList=[STEPS[Math.floor(Math.random()*STEPS.length)]].concat(msgList).slice(0,4);render();}bar.style.width=prog+'%';pct.textContent=prog+'% SECURED';},150);
})();
</script>"""

# ==========================
# JOURNEY BAR
# ==========================

_JOURNEY_PIE_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" fill="#000000" viewBox="0 0 64 64" style="fill-rule:evenodd;clip-rule:evenodd;stroke-linejoin:round;stroke-miterlimit:2;width:40px;height:40px;flex-shrink:0;" xml:space="preserve">
  <g transform="matrix(1,0,0,1,-192,-288)">
    <path d="M206.275,343.594L206.275,343.761C206.275,344.861 206.712,345.917 207.49,346.695C208.268,347.473 209.323,347.91 210.424,347.91C216.812,347.91 231.227,347.91 237.615,347.91C238.715,347.91 239.77,347.473 240.548,346.695C241.327,345.917 241.764,344.861 241.764,343.761L241.764,343.594C241.764,343.042 241.316,342.594 240.764,342.594L207.275,342.594C206.723,342.594 206.275,343.042 206.275,343.594Z" style="fill:rgb(181,129,49);"/>
    <path d="M238.479,342.594C238.489,342.651 238.494,342.709 238.494,342.769L238.494,342.937C238.494,344.037 238.057,345.092 237.279,345.87C236.501,346.649 235.446,347.086 234.345,347.086L207.942,347.086C208.654,347.618 209.524,347.91 210.424,347.91C216.812,347.91 231.227,347.91 237.615,347.91C238.715,347.91 239.77,347.473 240.548,346.695C241.327,345.917 241.764,344.861 241.764,343.761L241.764,343.594C241.764,343.042 241.316,342.594 240.764,342.594L238.479,342.594Z" style="fill:rgb(154,110,42);"/>
    <path d="M248.583,334.818L248.583,334.776C248.566,334.24 248.128,333.809 247.587,333.807L200.459,333.628C200.188,333.627 199.928,333.735 199.739,333.93C199.55,334.124 199.447,334.386 199.455,334.657C199.455,334.657 199.471,335.208 199.496,336.037C199.635,340.803 203.538,344.594 208.306,344.594C216.956,344.594 231.026,344.594 239.769,344.594C244.637,344.594 248.583,340.648 248.583,335.78C248.583,335.243 248.583,334.885 248.583,334.818Z" style="fill:rgb(245,240,229);"/>
    <path d="M247.587,333.807L243.247,333.807C243.788,333.809 244.227,334.24 244.243,334.776L244.244,334.818C244.244,334.885 244.244,335.243 244.244,335.78C244.244,340.648 240.297,344.594 235.43,344.594L239.769,344.594C244.637,344.594 248.583,340.648 248.583,335.78C248.583,335.243 248.583,334.885 248.583,334.818L248.583,334.776C248.566,334.24 248.128,333.809 247.587,333.807Z" style="fill:rgb(234,222,199);"/>
    <path d="M201.046,321.538C198.187,323.022 196.3,325.752 196.3,328.848C196.3,333.486 200.579,337.327 205.93,337.327C208.237,337.327 210.352,336.611 212.003,335.428C213.655,336.611 215.77,337.327 218.077,337.327C220.384,337.327 222.499,336.611 224.15,335.428C225.802,336.611 227.917,337.327 230.224,337.327C232.531,337.327 234.646,336.611 236.297,335.428C237.949,336.611 240.064,337.327 242.371,337.327C247.722,337.327 252,333.486 252,328.848C252,325.747 250.106,323.012 247.24,321.531C243.3,314.219 234.753,309.12 224.824,309.12L223.466,309.12C213.534,309.12 204.986,314.221 201.046,321.538Z" style="fill:rgb(248,172,58);"/>
    <path d="M223.828,309.12C230.776,310.836 236.474,315.13 239.484,320.716C242.35,322.197 244.244,324.932 244.244,328.033C244.244,331.814 241.401,335.065 237.45,336.138C238.887,336.891 240.571,337.327 242.371,337.327C247.722,337.327 252,333.486 252,328.848C252,325.747 250.106,323.012 247.24,321.531C243.3,314.219 234.753,309.12 224.824,309.12L223.828,309.12Z" style="fill:rgb(243,148,4);"/>
    <g transform="matrix(-1.02196,0,0,-1.34718,248.058,323.528)">
      <path d="M31.042,15.081L31.7,16.397C31.898,16.795 31.898,17.205 31.7,17.603L30.383,20.235C30.131,20.74 30.131,21.26 30.383,21.765C30.673,22.344 31.042,23.081 31.042,23.081C31.15,23.299 31.668,23.439 32.197,23.394C32.726,23.35 33.067,23.137 32.958,22.919L32.3,21.603C32.102,21.205 32.102,20.795 32.3,20.397L33.617,17.765C33.869,17.26 33.869,16.74 33.617,16.235C33.327,15.656 32.958,14.919 32.958,14.919C32.85,14.701 32.332,14.561 31.803,14.606C31.274,14.65 30.933,14.863 31.042,15.081Z" style="fill:rgb(245,240,229);">
        <animateTransform attributeName="transform" type="translate" values="0,0; -1,5; 0,10; 1,15" dur="3s" repeatCount="indefinite"/>
        <animate attributeName="opacity" values="0;0.7;0" dur="3s" repeatCount="indefinite"/>
      </path>
    </g>
    <g transform="matrix(-1.02196,0,0,-1.34718,256.697,323.528)">
      <path d="M31.042,15.081L31.7,16.397C31.898,16.795 31.898,17.205 31.7,17.603L30.383,20.235C30.131,20.74 30.131,21.26 30.383,21.765C30.673,22.344 31.042,23.081 31.042,23.081C31.15,23.299 31.668,23.439 32.197,23.394C32.726,23.35 33.067,23.137 32.958,22.919L32.3,21.603C32.102,21.205 32.102,20.795 32.3,20.397L33.617,17.765C33.869,17.26 33.869,16.74 33.617,16.235C33.327,15.656 32.958,14.919 32.958,14.919C32.85,14.701 32.332,14.561 31.803,14.606C31.274,14.65 30.933,14.863 31.042,15.081Z" style="fill:rgb(245,240,229);">
        <animateTransform attributeName="transform" type="translate" values="0,0; 1,5; 0,10; -1,15" dur="3s" begin="1s" repeatCount="indefinite"/>
        <animate attributeName="opacity" values="0;0.7;0" dur="3s" begin="1s" repeatCount="indefinite"/>
      </path>
    </g>
    <g transform="matrix(-1.02196,0,0,-1.34718,265.647,323.528)">
      <path d="M31.042,15.081L31.7,16.397C31.898,16.795 31.898,17.205 31.7,17.603L30.383,20.235C30.131,20.74 30.131,21.26 30.383,21.765C30.673,22.344 31.042,23.081 31.042,23.081C31.15,23.299 31.668,23.439 32.197,23.394C32.726,23.35 33.067,23.137 32.958,22.919L32.3,21.603C32.102,21.205 32.102,20.795 32.3,20.397L33.617,17.765C33.869,17.26 33.869,16.74 33.617,16.235C33.327,15.656 32.958,14.919 32.958,14.919C32.85,14.701 32.332,14.561 31.803,14.606C31.274,14.65 30.933,14.863 31.042,15.081Z" style="fill:rgb(245,240,229);">
        <animateTransform attributeName="transform" type="translate" values="0,0; -0.5,4; 0.5,8; 0,12" dur="3.5s" begin="2s" repeatCount="indefinite"/>
        <animate attributeName="opacity" values="0;0.7;0" dur="3.5s" begin="2s" repeatCount="indefinite"/>
      </path>
    </g>
  </g>
</svg>'''


def build_journey_bar(player_id: int) -> str:
    """Build the contextual journey sidebar as a deeply nested collapsible tree.

    Visual design matches the SideNav.tsx template (Playfair Display, radio-box style).
    Shown only on land/district/city/county/crypto pages (JS URL-gated).
    Returns an empty string when no player is logged in.
    """
    if not player_id:
        return ""

    land_count = 0
    district_count = 0
    player_city = None
    player_county = None

    try:
        import land as _land
        land_count = _land.count_player_land(player_id)
    except Exception:
        pass

    try:
        import districts as _dist
        district_count = _dist.count_player_districts(player_id)
    except Exception:
        pass

    try:
        from cities import get_player_city as _gpc
        player_city = _gpc(player_id)
    except Exception:
        pass

    try:
        from counties import get_player_county as _gpco
        player_county = _gpco(player_id)
    except Exception:
        pass

    has_city   = player_city   is not None
    has_county = player_county is not None
    county_id  = player_county.id if has_county else None

    # Next Step CTA
    if land_count == 0:
        next_label, next_href = "Buy your first plot", "/land-market"
    elif district_count == 0:
        next_label, next_href = "Create a district", "/districts/create"
    elif not has_city:
        next_label, next_href = "Join or found a city", "/cities"
    elif not has_county:
        next_label, next_href = "Form a county", "/counties"
    else:
        next_label, next_href = "Mine crypto", f"/county/{county_id}/mining"

    # ── Inline Lucide-style SVG icons ─────────────────────────────────
    _ico = {
        "map":    '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="3 6 9 3 15 6 21 3 21 18 15 21 9 18 3 21"/><line x1="9" y1="3" x2="9" y2="18"/><line x1="15" y1="6" x2="15" y2="21"/></svg>',
        "bag":    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/><path d="M16 10a4 4 0 0 1-8 0"/></svg>',
        "grid":   '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>',
        "store":  '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>',
        "city":   '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="7" width="20" height="15"/><path d="M16 7V5a2 2 0 0 0-4 0v2"/><path d="M12 12v.01"/><path d="M8 11v10"/><path d="M16 11v10"/><path d="M4 11v10"/><path d="M20 11v10"/></svg>',
        "pin":    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>',
        "coins":  '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="8" cy="8" r="6"/><path d="M18.09 10.37A6 6 0 1 1 10.34 18"/><path d="M7 6h1v4"/><line x1="16.71" y1="13.88" x2="17.71" y2="14.88"/></svg>',
        "pick":   '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m3.5 21 6.5-6.5"/><path d="m9 9-6 6 3 3 6-6"/><path d="M17.5 3 21 6.5l-11 11L6.5 14z"/><path d="M14 4l6 6"/></svg>',
        "wallet": '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 12V22H4V12"/><path d="M22 7H2v5h20V7z"/><path d="M12 22V7"/><path d="M12 7H7.5a2.5 2.5 0 0 1 0-5C11 2 12 7 12 7z"/><path d="M12 7h4.5a2.5 2.5 0 0 0 0-5C13 2 12 7 12 7z"/></svg>',
        "trend":  '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>',
        "chevR":  '<svg class="jb-chev-svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>',
    }

    def _trunc(s, n=14):
        return (s[:n] + "\u2026") if s and len(s) > n else (s or "")

    def _row(label, icon_key, level, href=None, locked=False,
             expandable=False, badge=None, dot=False, open_default=False):
        """Render one nav row — button (expandable/locked) or anchor (leaf)."""
        pl = level * 16 + 24
        icon = _ico[icon_key]
        sz = "jb-lv0" if level == 0 else "jb-lv1"
        badge_html = f'<span class="jb-badge">{badge}</span>' if badge is not None else ''
        dot_html   = '<span class="jb-activedot"></span>' if dot else ''

        if locked:
            return (
                f'<div class="jb-row jb-locked" style="padding-left:{pl}px">'
                f'<span class="jb-icon">{icon}</span>'
                f'<span class="jb-label {sz}">{label}</span>'
                f'</div>'
            )
        if expandable:
            # Always use chevR; CSS rotate(90deg) on [data-open="1"] shows the open state
            chev = _ico["chevR"]
            d_open = "1" if open_default else "0"
            return (
                f'<button class="jb-row" onclick="wadsJBToggle(this)"'
                f' data-open="{d_open}" data-href="{href or ""}"'
                f' style="padding-left:{pl}px">'
                f'<span class="jb-icon">{icon}</span>'
                f'<span class="jb-label {sz}">{label}</span>'
                f'{badge_html}'
                f'<span class="jb-chev">{chev}</span>'
                f'</button>'
            )
        # leaf link
        return (
            f'<a class="jb-row" href="{href or "#"}" style="padding-left:{pl}px">'
            f'<span class="jb-icon">{icon}</span>'
            f'<span class="jb-label {sz}">{label}</span>'
            f'{dot_html}{badge_html}'
            f'</a>'
        )

    def _group(inner, open_default=False):
        disp = "block" if open_default else "none"
        return f'<div class="jb-group" style="display:{disp}">{inner}</div>'

    # ── Wallet / Mining / Exchange subtree ────────────────────────────
    if has_county:
        wallet_subtree = _group(
            _row("Wallet", "wallet", 6, href="/wallet"),
            open_default=False,
        )
        mining_subtree = _group(
            _row("Mining", "pick", 5, expandable=True, open_default=False)
            + wallet_subtree
            + _row("Exchange",    "coins", 5, href="/exchange")
            + _row("Gas Tracker", "pin",   5, href="/gas-tracker"),
            open_default=False,
        )
        county_name = _trunc(player_county.name)
        counties_inner = (
            _row(county_name, "pin", 4, href=f"/county/{county_id}", dot=True)
            + _row("Crypto Exchange", "coins", 4, expandable=True, open_default=False)
            + mining_subtree
        )
    elif has_city:
        counties_inner = (
            _row("Browse Counties", "pin", 4, href="/counties")
            + _row("Form a County",  "pin", 4, href="/county/petition/new")
            + _row("Join a County",  "pin", 4, href="/county/petition/join")
        )
    else:
        counties_inner = _row("Need a city first", "pin", 4, locked=True)

    # ── Cities subtree ────────────────────────────────────────────────
    if has_city:
        city_name = _trunc(player_city.name)
        cities_inner = (
            _row(city_name, "city", 3, href=f"/city/{player_city.id}", dot=True)
            + _row("All Cities", "store", 3, href="/cities")
            + _row("Counties", "pin", 3, expandable=True, open_default=False)
            + _group(counties_inner, open_default=False)
        )
    else:
        cities_inner = (
            _row("Browse Cities", "city", 3, href="/cities")
            + _row("Counties", "pin", 3, expandable=True, open_default=False)
            + _group(counties_inner, open_default=False)
        )

    # ── Districts subtree ─────────────────────────────────────────────
    dist_badge = district_count if district_count else None
    districts_inner = (
        _row("District Market",  "store", 2, href="/district-market")
        + _row("Create District", "grid",  2, href="/districts/create")
        + _row("Cities", "city", 2, expandable=True, open_default=False)
        + _group(cities_inner, open_default=False)
    )

    # ── Land root ─────────────────────────────────────────────────────
    land_badge = land_count if land_count else None
    nav_html = (
        _row("Land", "map", 0, href="/land", expandable=True,
             badge=land_badge, open_default=True)
        + _group(
            _row("Land Market", "bag", 1, href="/land-market")
            + _row("Districts", "grid", 1, href="/districts",
                   expandable=True, badge=dist_badge, open_default=True)
            + _group(districts_inner, open_default=True),
            open_default=True,
        )
    )

    # ── Balance footer ────────────────────────────────────────────────
    balance_footer = (
        f'<div id="jb-balance">'
        f'<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">'
        f'<div>'
        f'<div class="jb-bal-lbl">Total Assets</div>'
        f'<div class="jb-bal-val">{land_count + district_count} plots</div>'
        f'</div>'
        f'<div class="jb-bal-icon">{_ico["trend"]}</div>'
        f'</div>'
        f'<div class="jb-bar-wrap"><div class="jb-bar-fill" style="width:{min(100, (land_count + district_count) * 5)}%"></div></div>'
        f'</div>'
    )

    # ── Next Step footer ──────────────────────────────────────────────
    next_html = (
        f'<div id="jb-next">'
        f'<div id="jb-next-lbl">Next Step</div>'
        f'<a href="{next_href}">{next_label} &#8250;</a>'
        f'</div>'
    )

    # ── JS: URL gate + slide-in animation + active highlight + collapse toggle ──
    js = (
        '<script>(function(){'
        'var PATHS=["/land","/land-market","/districts","/district-market","/districts/create",'
        '"/cities","/city/","/counties","/county/","/exchange","/token/","/gas-tracker",'
        '"/wallet","/memecoins"];'
        'var p=location.pathname;'
        'if(!PATHS.some(function(r){return p===r||p.startsWith(r.endsWith("/")?r:r+"/");}))return;'
        'var bar=document.getElementById("journey-bar");'
        'var tab=document.getElementById("jb-tab");'
        'var body=document.getElementById("jb-body");'
        'if(!bar)return;'
        'function showBar(){'
        'bar.style.display="flex";'
        'setTimeout(function(){bar.classList.add("jb-visible");},10);'
        'body.classList.add("jb-on");'
        'if(tab)tab.style.display="none";'
        'localStorage.setItem("wadsJB","open");'
        '}'
        'function hideBar(){'
        'bar.style.display="none";'
        'bar.classList.remove("jb-visible");'
        'body.classList.remove("jb-on");'
        'if(tab)tab.style.display="flex";'
        'localStorage.setItem("wadsJB","closed");'
        '}'
        'if(localStorage.getItem("wadsJB")!=="closed"){showBar();}'
        'else{if(tab)tab.style.display="flex";}'
        'document.getElementById("jb-close").onclick=hideBar;'
        'if(tab)tab.onclick=showBar;'
        'document.querySelectorAll(".jb-row[href]").forEach(function(el){'
        'var h=el.getAttribute("href");'
        'if(!h||h==="#")return;'
        'if(p===h||(h.length>1&&p.startsWith(h)))el.classList.add("jb-active");'
        '});'
        'document.querySelectorAll(".jb-group").forEach(function(grp){'
        'if(grp.querySelector(".jb-active")){'
        'grp.style.display="block";'
        'var prev=grp.previousElementSibling;'
        'if(prev)prev.setAttribute("data-open","1");'
        '}'
        '});'
        '})();\n'
        'function wadsJBToggle(btn){'
        'var grp=btn.nextElementSibling;'
        'if(!grp||!grp.classList.contains("jb-group"))return;'
        'var nowOpen=grp.style.display!=="none";'
        'grp.style.display=nowOpen?"none":"block";'
        'btn.setAttribute("data-open",nowOpen?"0":"1");'
        'var href=btn.getAttribute("data-href");'
        'if(href&&!nowOpen)location.href=href;'
        '}'
        '</script>'
    )

    return (
        f'<button id="jb-tab" aria-label="Open navigation" title="Open navigation">'
        f'<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>'
        f'</button>'
        f'<div id="journey-bar">'
        f'<div id="jb-head">'
        f'<h1 id="jb-wordmark">ESTATE<span style="opacity:0.2">.</span>MGR</h1>'
        f'<p id="jb-submark">Wadsworth Land Dashboard</p>'
        f'<button id="jb-close" aria-label="Close sidebar">&#215;</button>'
        f'</div>'
        f'<nav id="jb-nav">{nav_html}</nav>'
        f'{balance_footer}'
        f'{next_html}'
        f'</div>'
        + js
    )


# ==========================
# HTML SHELL
# ==========================

def shell(title: str, body: str, balance: float = 0.0, player_id: int = None, breadcrumbs: list = None) -> str:
    # breadcrumbs: list of (label, url) tuples or plain strings; last item is current page
    lien_info = get_player_lien_info(player_id) if player_id else {"has_lien": False, "total_owed": 0.0, "status": "ok"}

    # Resolve display balance using player's legal tender so the header always
    # shows the currency the player actually works in (not hardcoded USD).
    disp_sym      = "$"
    disp_balance  = balance
    disp_usd_note = ""
    if player_id:
        try:
            from reserve_banks import get_player_legal_tender, get_player_currency_balances
            tender = get_player_legal_tender(player_id)
            if tender != "USD":
                for b in get_player_currency_balances(player_id):
                    if b["currency_code"] == tender:
                        disp_sym      = b["currency_symbol"]
                        disp_balance  = b["balance"]
                        disp_usd_note = (
                            f' <span style="font-size:0.65em;color:#64748b;">'
                            f'/ ${balance:,.0f} USD</span>'
                        )
                        break
        except Exception:
            pass  # fall back to cash_balance / $ on any error
    # disp dict for fmt_usd in lien/ticker
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player_id) if player_id else {"code": "USD", "symbol": "$", "usd_per_unit": 1.0, "flag": "\U0001f1fa\U0001f1f8"}
    
    lien_html = ""
    if lien_info["has_lien"]:
        status_colors = {"critical": "#dc2626", "warning": "#f59e0b", "ok": "#64748b"}
        lien_color = status_colors.get(lien_info["status"], "#64748b")
        status_icons = {"critical": "🚨", "warning": "⚠️", "ok": "📋"}
        lien_icon = status_icons.get(lien_info["status"], "📋")
        
        lien_html = f'''
        <a href="/liens" style="color: {lien_color}; margin-right: 12px; text-decoration: none; display: inline-flex; align-items: center; gap: 4px; font-size: 0.85rem;">
            <span>{lien_icon}</span>
            <span style="font-weight: 500;">LIEN: {fmt_usd(lien_info["total_owed"], disp, precision=0)}</span>
        </a>
        '''
    
    ticker_html = ""
    try:
        import market as market_mod
        import inventory as inv_mod
        
        all_items = list(inv_mod.ITEM_RECIPES.keys()) if inv_mod.ITEM_RECIPES else list(market_mod.STARTER_INVENTORY.keys())
        
        ticker_items = []
        for item in sorted(all_items):
            price = market_mod.get_market_price(item)
            if price:
                ticker_items.append(f"{item.replace('_', ' ').upper()}: {fmt_usd(price, disp)}")
            else:
                ticker_items.append(f"{item.replace('_', ' ').upper()}: N/A")
        ticker_html = " | ".join(ticker_items) if ticker_items else "MARKET OPENING..."
    except:
        ticker_html = "MARKET FEED OFFLINE"

    journey_bar_html = build_journey_bar(player_id)

    breadcrumb_html = ""
    if breadcrumbs:
        sep = '<span style="color:#B08D57;opacity:0.4;margin:0 4px;">&#8250;</span>'
        parts = []
        for i, c in enumerate(breadcrumbs):
            lbl, url = (c if isinstance(c, (list, tuple)) and len(c) == 2 else (str(c), None))
            if url and i < len(breadcrumbs) - 1:
                parts.append(f'<a href="{url}" style="color:#B08D57;text-decoration:none;">{lbl}</a>')
            else:
                parts.append(f'<span style="color:#E0D5C5;opacity:0.9;">{lbl}</span>')
        breadcrumb_html = f'<div class="jb-breadcrumbs">{sep.join(parts)}</div>'

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{title} · Wadsworth</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <!-- PWA -->
        <link rel="manifest" href="/manifest.json">
        <meta name="theme-color" content="#38bdf8">
        <meta name="mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
        <meta name="apple-mobile-web-app-title" content="Wadsworth">
        <link rel="apple-touch-icon" href="/static/icons/apple-touch-icon.png">
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@700;900&display=swap" rel="stylesheet">
        <style>
            * {{ box-sizing: border-box; }}
            body {{
                background: #020617;
                color: #e5e7eb;
                font-family: 'JetBrains Mono', monospace;
                margin: 0;
                padding-bottom: 60px;
                font-size: 18px;
            }}

            a {{ color: #38bdf8; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}

            .header {{
                border-bottom: 1px solid #1e293b;
                padding: 12px 16px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                flex-wrap: wrap;
                gap: 8px;
            }}

            .brand {{
                font-weight: bold;
                color: #38bdf8;
                display: flex;
                align-items: center;
                gap: 8px;
            }}

            .brand img {{
                height: 28px;
                width: auto;
            }}

            .header-right {{
                display: flex;
                align-items: center;
                gap: 12px;
                flex-wrap: wrap;
            }}

            .balance {{
                color: #22c55e;
                font-size: 0.75rem;
                white-space: nowrap;
            }}

            .container {{
                max-width: 1000px;
                margin: 0 auto;
                padding: 20px 16px;
            }}

            .card {{
                background: #0f172a;
                border: 1px solid #1e293b;
                padding: 20px;
                margin-bottom: 16px;
            }}

            .badge {{
                font-size: 0.65rem;
                padding: 2px 6px;
                border-radius: 3px;
                background: #1e293b;
                margin-left: 6px;
                white-space: nowrap;
            }}

            .btn-blue, .btn-orange, .btn-red, .btn-gold {{
                border: none;
                padding: 6px 12px;
                cursor: pointer;
                font-size: 0.8rem;
                border-radius: 3px;
            }}

            .btn-blue {{ background: #38bdf8; color: #020617; }}
            .btn-orange {{ background: #f59e0b; color: #020617; }}
            .btn-red {{ background: #ef4444; color: #fff; }}
            .btn-gold {{ background: #d4af37; color: #fff; }}

            input, select {{
                background: #020617;
                border: 1px solid #1e293b;
                color: #e5e7eb;
                padding: 6px;
                font-size: 0.9rem;
            }}

            .progress {{
                background: #020617;
                height: 8px;
                margin-top: 8px;
            }}

            .progress-bar {{
                background: #38bdf8;
                height: 100%;
            }}

            .ticker {{
                position: fixed;
                bottom: 0;
                left: 0;
                right: 0;
                background: #0f172a;
                border-top: 1px solid #334155;
                padding: 4px 8px;
                font-size: 0.8rem;
                color: #cbd5e1;
                white-space: nowrap;
                overflow: hidden;
                display: flex;
                align-items: center;
                gap: 0;
                height: 34px;
                z-index: 1000;
            }}

            .ticker-controls {{
                display: flex;
                align-items: center;
                gap: 3px;
                flex-shrink: 0;
                padding-right: 8px;
                margin-right: 8px;
                border-right: 1px solid #334155;
            }}

            .ticker-btn {{
                background: #1e293b;
                border: 1px solid #334155;
                color: #94a3b8;
                border-radius: 3px;
                padding: 2px 5px;
                font-size: 0.7rem;
                cursor: pointer;
                font-family: inherit;
                line-height: 1.5;
                user-select: none;
            }}

            .ticker-btn:hover {{
                background: #334155;
                color: #e2e8f0;
            }}

            .ticker-btn.active {{
                background: #1d4ed8;
                border-color: #3b82f6;
                color: #e2e8f0;
            }}

            #tkViewport {{
                overflow: hidden;
                flex: 1;
                height: 100%;
                display: flex;
                align-items: center;
            }}

            @keyframes lien-pulse {{
                0%, 100% {{ opacity: 1; }}
                50% {{ opacity: 0.6; }}
            }}

            @keyframes gs-scroll-title {{
                0%,  15% {{ transform: translateX(0); }}
                85%, 100% {{ transform: translateX(var(--gs-se, 0px)); }}
            }}

            .lien-critical {{
                animation: lien-pulse 2s ease-in-out infinite;
            }}

            /* Responsive utilities */
            @media (max-width: 640px) {{
                .container {{ padding: 16px 12px; }}
                .card {{ padding: 16px; }}
                input, select {{ font-size: 16px; }}

                /* Stack grids on mobile */
                div[style*="display: grid"][style*="grid-template-columns: 1fr 1fr"] {{
                    display: flex !important;
                    flex-direction: column !important;
                }}

                /* Make flex containers wrap */
                div[style*="display: flex"]:not(.header-right) {{
                    flex-wrap: wrap !important;
                }}

                /* Stack forms vertically */
                form[style*="grid-template-columns"] {{
                    display: flex !important;
                    flex-direction: column !important;
                    gap: 8px !important;
                }}

                /* Wrap filter tabs */
                div[style*="overflow-x: auto"][style*="white-space: nowrap"] {{
                    white-space: normal !important;
                    overflow-x: visible !important;
                    display: flex !important;
                    flex-wrap: wrap !important;
                    gap: 8px !important;
                }}

                /* Make tab links inline-block for wrapping */
                div[style*="overflow-x: auto"] a {{
                    display: inline-block;
                    margin-right: 0 !important;
                    padding: 6px 10px !important;
                    background: #1e293b !important;
                    border-radius: 3px !important;
                }}
            }}

            /* ══════════════════════════════════════════════════════
               JOURNEY BAR — Cinzel, brass, mahogany, 3-D depth
               ══════════════════════════════════════════════════════ */

            /* Keyframes */
            @keyframes jb-slide-in {{
                from {{ transform: translateX(-100%) rotateY(-8deg); opacity: 0; }}
                to   {{ transform: translateX(0)    rotateY(0deg);  opacity: 1; }}
            }}
            @keyframes jb-shimmer {{
                0%   {{ background-position: -300% center; }}
                100% {{ background-position:  300% center; }}
            }}
            @keyframes jb-edge-pulse {{
                0%,100% {{ opacity: 0.35; box-shadow: 4px 0 14px rgba(176,141,87,0.12); }}
                50%     {{ opacity: 0.8;  box-shadow: 4px 0 28px rgba(176,141,87,0.30); }}
            }}
            @keyframes jb-activedot-glow {{
                0%,100% {{ box-shadow: 0 0 4px #B08D57, 0 0 8px rgba(176,141,87,0.4); }}
                50%     {{ box-shadow: 0 0 8px #B08D57, 0 0 20px rgba(176,141,87,0.7); }}
            }}
            @keyframes jb-coin-flip {{
                0%   {{ transform: rotateY(0deg); }}
                50%  {{ transform: rotateY(90deg) scale(0.85); }}
                100% {{ transform: rotateY(360deg); }}
            }}
            @keyframes jb-scanline {{
                0%   {{ transform: translateY(-120%); opacity: 0; }}
                10%  {{ opacity: 0.6; }}
                90%  {{ opacity: 0.6; }}
                100% {{ transform: translateY(120%); opacity: 0; }}
            }}

            #journey-bar {{
                display: none;
                position: fixed;
                left: 0;
                top: 0;
                bottom: 34px;
                width: 248px;
                background: linear-gradient(170deg, #1E1409 0%, #1A0F0A 40%, #140C07 100%);
                border-right: 6px solid #2D1810;
                outline: 2px solid rgba(176,141,87,0.28);
                outline-offset: -10px;
                z-index: 95;
                flex-direction: column;
                font-family: 'Cinzel', Georgia, serif;
                perspective: 900px;
                /* right-edge glow */
                animation: jb-edge-pulse 4s ease-in-out infinite;
            }}
            #journey-bar.jb-visible {{
                animation: jb-slide-in 0.38s cubic-bezier(0.16,1,0.3,1) both,
                           jb-edge-pulse 4s ease-in-out 0.4s infinite;
            }}
            /* scanline sweep every 8 s */
            #journey-bar::before {{
                content: '';
                position: absolute;
                inset: 0;
                background: linear-gradient(to bottom,
                    transparent 0%, rgba(176,141,87,0.06) 50%, transparent 100%);
                height: 60px;
                width: 100%;
                animation: jb-scanline 8s linear infinite;
                pointer-events: none;
                z-index: 1;
            }}

            /* ── Header ── */
            #jb-head {{
                padding: 18px 14px 13px;
                border-bottom: 3px solid rgba(176,141,87,0.35);
                background: linear-gradient(160deg, #2A1A0D 0%, #1E1208 100%);
                text-align: center;
                position: relative;
                flex-shrink: 0;
                overflow: hidden;
            }}
            /* shimmer sweep over header */
            #jb-head::after {{
                content: '';
                position: absolute;
                inset: 0;
                background: linear-gradient(105deg,
                    transparent 30%, rgba(176,141,87,0.12) 50%, transparent 70%);
                background-size: 300% 100%;
                animation: jb-shimmer 5s ease-in-out infinite;
                pointer-events: none;
            }}
            #jb-wordmark {{
                font-family: 'Cinzel', Georgia, serif;
                font-size: 17px;
                font-weight: 900;
                text-transform: uppercase;
                letter-spacing: 0.18em;
                color: #B08D57;
                margin: 0 0 3px;
                line-height: 1;
                text-shadow: 0 0 14px rgba(176,141,87,0.5), 0 1px 3px rgba(0,0,0,0.8);
                position: relative; z-index: 2;
            }}
            #jb-submark {{
                font-family: 'JetBrains Mono', monospace;
                font-size: 8px;
                letter-spacing: 0.28em;
                text-transform: uppercase;
                color: #F5F5DC;
                opacity: 0.35;
                margin: 0;
                position: relative; z-index: 2;
            }}
            #jb-close {{
                position: absolute;
                top: 9px; right: 11px;
                background: none;
                border: 2px solid rgba(176,141,87,0.25);
                border-radius: 3px;
                color: rgba(176,141,87,0.45);
                cursor: pointer;
                font-size: 14px;
                padding: 2px 5px;
                line-height: 1;
                transition: color 0.2s, border-color 0.2s;
                z-index: 2;
            }}
            #jb-close:hover {{ color: #B08D57; border-color: rgba(176,141,87,0.7); }}

            /* ── Scrollable nav ── */
            #jb-nav {{
                flex: 1;
                overflow-y: auto;
                padding: 6px 0;
                scrollbar-width: thin;
                scrollbar-color: rgba(176,141,87,0.18) transparent;
            }}

            /* ── Nav rows ── */
            .jb-row {{
                width: 100%;
                display: flex;
                align-items: center;
                gap: 9px;
                padding: 8px 20px;
                border: none;
                border-bottom: 2px solid rgba(176,141,87,0.08);
                border-left: 3px solid transparent;
                background: transparent;
                color: rgba(245,245,220,0.45);
                text-decoration: none;
                cursor: pointer;
                text-align: left;
                transition: color 0.18s, background 0.18s, transform 0.18s,
                            border-left-color 0.18s, box-shadow 0.18s;
                box-sizing: border-box;
                position: relative;
            }}
            .jb-row:hover {{
                color: #F5F5DC;
                background: rgba(176,141,87,0.07);
                text-decoration: none;
                transform: translateX(5px);
                border-left-color: rgba(176,141,87,0.4);
                box-shadow: -3px 0 0 rgba(0,0,0,0.4),
                             4px 2px 12px rgba(0,0,0,0.5),
                             inset 0 1px 0 rgba(176,141,87,0.08);
            }}
            .jb-row.jb-active {{
                background: rgba(176,141,87,0.13);
                color: #ffffff;
                border-left-color: #B08D57;
                transform: translateX(3px);
                box-shadow: inset 0 1px 0 rgba(176,141,87,0.2),
                             inset 0 -1px 0 rgba(0,0,0,0.4),
                             4px 0 16px rgba(176,141,87,0.14);
            }}
            .jb-row.jb-locked {{
                color: rgba(176,141,87,0.18);
                cursor: default;
                pointer-events: none;
                font-style: italic;
            }}
            .jb-row.jb-locked:hover {{ transform: none; box-shadow: none; }}

            /* ── Icons ── */
            .jb-icon {{
                display: flex;
                align-items: center;
                flex-shrink: 0;
                color: inherit;
                transition: color 0.18s, filter 0.18s;
            }}
            .jb-row:hover .jb-icon {{
                color: #B08D57;
                filter: drop-shadow(0 0 4px rgba(176,141,87,0.6));
            }}
            .jb-row.jb-active .jb-icon {{
                color: #B08D57;
                filter: drop-shadow(0 0 6px rgba(176,141,87,0.8));
            }}

            /* ── Labels ── */
            .jb-label {{
                flex: 1;
                font-family: 'Cinzel', Georgia, serif;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 0.1em;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }}
            .jb-lv0 {{ font-size: 13px; }}
            .jb-lv1 {{ font-size: 10.5px; }}

            /* ── Active dot ── */
            .jb-activedot {{
                width: 5px;
                height: 5px;
                border-radius: 50%;
                background: #B08D57;
                flex-shrink: 0;
                animation: jb-activedot-glow 2s ease-in-out infinite;
            }}

            /* ── Badge ── */
            .jb-badge {{
                font-size: 9px;
                font-family: 'JetBrains Mono', monospace;
                background: rgba(176,141,87,0.18);
                color: #B08D57;
                border: 1px solid rgba(176,141,87,0.3);
                border-radius: 2px;
                padding: 0 5px;
                flex-shrink: 0;
                letter-spacing: 0;
            }}

            /* ── Chevron ── */
            .jb-chev {{
                color: rgba(176,141,87,0.3);
                flex-shrink: 0;
                display: flex;
                align-items: center;
                transition: color 0.18s, transform 0.25s;
            }}
            .jb-row:hover .jb-chev {{ color: #B08D57; }}
            .jb-row[data-open="1"] .jb-chev {{ transform: rotate(90deg); }}

            /* ── Collapsible group ── */
            .jb-group {{
                background: rgba(0,0,0,0.15);
                border-left: 2px solid rgba(176,141,87,0.12);
                margin-left: 12px;
                transition: all 0.25s ease;
            }}

            /* ── Balance widget ── */
            #jb-balance {{
                padding: 12px 14px;
                background: linear-gradient(135deg, #241812 0%, #1A0F0A 100%);
                border-top: 3px solid rgba(176,141,87,0.3);
                flex-shrink: 0;
            }}
            .jb-bal-lbl {{
                font-family: 'JetBrains Mono', monospace;
                font-size: 8px;
                letter-spacing: 0.22em;
                text-transform: uppercase;
                color: #B08D57;
                font-weight: 700;
            }}
            .jb-bal-val {{
                font-family: 'Cinzel', Georgia, serif;
                font-size: 14px;
                font-weight: 900;
                text-transform: uppercase;
                color: #F5F5DC;
                letter-spacing: 0.04em;
                margin-top: 1px;
                text-shadow: 0 0 10px rgba(176,141,87,0.3);
            }}
            .jb-bal-icon {{
                width: 34px;
                height: 34px;
                border-radius: 50%;
                border: 2px solid rgba(176,141,87,0.35);
                display: flex;
                align-items: center;
                justify-content: center;
                color: #B08D57;
                background: rgba(0,0,0,0.5);
                transition: transform 0.6s ease, box-shadow 0.3s;
                transform-style: preserve-3d;
                cursor: default;
            }}
            .jb-bal-icon:hover {{
                animation: jb-coin-flip 0.8s ease-in-out;
                box-shadow: 0 0 14px rgba(176,141,87,0.5);
            }}
            .jb-bar-wrap {{
                margin-top: 8px;
                height: 5px;
                background: rgba(0,0,0,0.7);
                border: 2px solid rgba(176,141,87,0.15);
                border-radius: 9999px;
                overflow: hidden;
            }}
            .jb-bar-fill {{
                height: 100%;
                background: linear-gradient(to right, #5C3D1A, #B08D57, #D4AF6E);
                box-shadow: 0 0 8px rgba(176,141,87,0.5);
                transition: width 1s ease;
            }}

            /* ── Next Step footer ── */
            #jb-next {{
                padding: 9px 14px 11px;
                border-top: 3px solid rgba(176,141,87,0.22);
                background: linear-gradient(135deg, rgba(176,141,87,0.07) 0%, rgba(0,0,0,0.2) 100%);
                flex-shrink: 0;
            }}
            #jb-next-lbl {{
                font-family: 'JetBrains Mono', monospace;
                font-size: 8px;
                letter-spacing: 0.2em;
                text-transform: uppercase;
                color: #f59e0b;
                opacity: 0.6;
                margin-bottom: 4px;
            }}
            #jb-next a {{
                font-family: 'Cinzel', Georgia, serif;
                font-size: 11px;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 0.08em;
                color: #f59e0b;
                text-decoration: none;
                display: block;
                line-height: 1.45;
                transition: color 0.2s, text-shadow 0.2s;
            }}
            #jb-next a:hover {{
                color: #fbbf24;
                text-shadow: 0 0 10px rgba(251,191,36,0.5);
                text-decoration: none;
            }}

            /* ── Breadcrumb strip ── */
            .jb-breadcrumbs {{
                padding: 5px 16px;
                font-size: 11px;
                font-family: Georgia, serif;
                border-bottom: 2px solid rgba(176,141,87,0.15);
                background: rgba(19,12,7,0.6);
                display: flex;
                align-items: center;
                flex-wrap: wrap;
                gap: 2px;
            }}

            /* ── Reopen tab (visible when bar is closed) ── */
            #jb-tab {{
                display: none;          /* shown by JS on journey pages when bar closed */
                position: fixed;
                left: 0;
                top: 50%;
                transform: translateY(-50%);
                z-index: 96;
                align-items: center;
                justify-content: center;
                width: 22px;
                padding: 14px 0;
                background: #241812;
                border: 2px solid rgba(176,141,87,0.55);
                border-left: none;
                border-radius: 0 6px 6px 0;
                color: rgba(176,141,87,0.6);
                cursor: pointer;
                transition: background 0.2s, color 0.2s, border-color 0.2s,
                            box-shadow 0.2s;
                box-shadow: 3px 0 12px rgba(0,0,0,0.6);
            }}
            #jb-tab:hover {{
                background: rgba(176,141,87,0.12);
                color: #B08D57;
                border-color: #B08D57;
                box-shadow: 3px 0 18px rgba(176,141,87,0.2);
            }}
            /* ── Body shift when bar is open ── */
            #jb-body.jb-on {{ padding-left: 248px; }}
            @media (max-width: 768px) {{
                #jb-body.jb-on {{ padding-left: 0; }}
                #journey-bar {{ z-index: 200; width: 100%; max-width: 280px; }}
            }}
        </style>
    </head>
    <body id="jb-body">
        {journey_bar_html}
        <div class="header">
            <div class="brand"><img src="/static/logo.png" alt="Wadsworth"> Wadsworth</div>
            <div class="header-right">
                {lien_html}
                <span class="balance">{disp_sym}{disp_balance:,.2f}{disp_usd_note}</span>
                <a href="/api/logout" style="color: #ef4444; font-size: 0.85rem;">Logout</a>
            </div>
        </div>
        {breadcrumb_html}

        <div class="container">
            {body}
        </div>

        <div class="ticker" id="tickerBar">
            <div class="ticker-controls">
                <button class="ticker-btn" id="tkRestart" title="Restart">&#9198;</button>
                <button class="ticker-btn" id="tkRewind" title="Rewind">&#9194;</button>
                <button class="ticker-btn" id="tkPlay" title="Pause">&#9208;</button>
                <button class="ticker-btn" id="tkSpeed" title="Speed">1&times;</button>
            </div>
            <div id="tkViewport">
                <div id="tkTrack" style="display:inline-block;white-space:nowrap;will-change:transform;transform:translateX(0);">
                    {ticker_html} &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; {ticker_html}
                </div>
            </div>
        </div>
        <script data-cfasync="false">
        (function() {{
            var STORE = 'wadsTickerState';
            var SPEEDS = [0.5, 1, 1.5, 2];
            var BASE_PX = 0.9;

            var state = {{ paused: false, speedIdx: 1, direction: 1, offset: 0 }};

            try {{
                var saved = JSON.parse(localStorage.getItem(STORE) || '{{}}');
                if (typeof saved.paused === 'boolean') state.paused = saved.paused;
                if (typeof saved.speedIdx === 'number' && saved.speedIdx >= 0 && saved.speedIdx < SPEEDS.length) state.speedIdx = saved.speedIdx;
                if (typeof saved.direction === 'number') state.direction = saved.direction;
                if (typeof saved.offset === 'number') state.offset = saved.offset;
            }} catch(e) {{}}

            var track  = document.getElementById('tkTrack');
            var btnPlay    = document.getElementById('tkPlay');
            var btnRewind  = document.getElementById('tkRewind');
            var btnRestart = document.getElementById('tkRestart');
            var btnSpeed   = document.getElementById('tkSpeed');

            var halfWidth = 0;
            var rafId = null;

            function measureHalf() {{
                halfWidth = track.scrollWidth / 2;
            }}

            function saveState() {{
                try {{ localStorage.setItem(STORE, JSON.stringify(state)); }} catch(e) {{}}
            }}

            function updateUI() {{
                btnPlay.innerHTML   = state.paused ? '&#9654;' : '&#9208;';
                btnPlay.title       = state.paused ? 'Play' : 'Pause';
                btnSpeed.innerHTML  = SPEEDS[state.speedIdx] + '&times;';
                btnRewind.classList.toggle('active', state.direction === -1);
            }}

            function applyTransform() {{
                track.style.transform = 'translateX(' + state.offset + 'px)';
            }}

            function step() {{
                if (!state.paused) {{
                    if (!halfWidth) measureHalf();
                    var px = BASE_PX * SPEEDS[state.speedIdx] * state.direction;
                    state.offset -= px;
                    /* seamless loop: keep offset within -halfWidth..0 */
                    if (state.offset < -halfWidth) state.offset += halfWidth;
                    if (state.offset > 0)          state.offset -= halfWidth;
                    applyTransform();
                }}
                rafId = requestAnimationFrame(step);
            }}

            btnPlay.addEventListener('click', function() {{
                state.paused = !state.paused;
                if (!state.paused) state.direction = 1;
                updateUI(); saveState();
            }});

            btnRewind.addEventListener('click', function() {{
                state.direction = state.direction === -1 ? 1 : -1;
                state.paused = false;
                updateUI(); saveState();
            }});

            btnRestart.addEventListener('click', function() {{
                state.offset = 0;
                state.direction = 1;
                state.paused = false;
                applyTransform();
                updateUI(); saveState();
            }});

            btnSpeed.addEventListener('click', function() {{
                state.speedIdx = (state.speedIdx + 1) % SPEEDS.length;
                updateUI(); saveState();
            }});

            applyTransform();
            updateUI();
            measureHalf();
            rafId = requestAnimationFrame(step);

            /* persist position on unload so next page load resumes cleanly */
            window.addEventListener('pagehide', saveState);
            window.addEventListener('beforeunload', saveState);
        }})();
        </script>

        <!-- ══════════════════════════════════════════════════════════
             GAME AUDIO PLAYER  — persists across page loads via localStorage
             State key: wadsST  (enabled, volume, shuffleOrder, trackIdx, time)
             Track cache key: wadsST_tracks (TTL 5 min)
             ══════════════════════════════════════════════════════════ -->
        <audio id="gs-audio" preload="auto" style="display:none;"></audio>
        <audio id="wcpr-shell-audio" preload="none" style="display:none;"></audio>

        <!-- Mini floating player — same size/position as before, mahogany theme -->
        <div id="gs-bar" style="
            position:fixed;bottom:50px;right:12px;z-index:150;
            background:#1A0F0A;border:1px solid #B08D57;border-radius:8px;
            padding:6px 10px;display:flex;align-items:center;gap:8px;
            font-size:0.72rem;color:#F5F5DC;min-width:220px;max-width:300px;
            box-shadow:0 4px 20px rgba(0,0,0,0.7);transition:opacity 0.3s;
            font-family:Georgia,serif;">
            <span id="gsbar-ico" style="font-size:1rem;flex-shrink:0;color:#B08D57;" title="Radio">📻</span>
            <div style="flex:1;min-width:0;overflow:hidden;">
                <div style="font-size:0.55rem;color:#B08D57;opacity:0.7;text-transform:uppercase;letter-spacing:0.1em;white-space:nowrap;" id="gsbar-sname">WLOL 92.8</div>
                <div id="gs-title" style="color:#e5e7eb;white-space:nowrap;display:inline-block;">Loading&hellip;</div>
            </div>
            <button id="gs-pp" onclick="gsBarPlay()" title="Play/Pause"
                    style="background:none;border:none;color:#B08D57;font-size:1rem;cursor:pointer;padding:0;line-height:1;">&#9658;</button>
            <button onclick="gsBarSkip()" title="Next track"
                    style="background:none;border:none;color:#B08D57;opacity:0.5;font-size:0.9rem;cursor:pointer;padding:0;line-height:1;">&#9197;</button>
            <input id="gs-vol" type="range" min="0" max="1" step="0.05"
                   oninput="gsSetVolume(this.value)"
                   style="width:50px;accent-color:#B08D57;cursor:pointer;" title="Volume">
            <!-- Tuner knob -->
            <div onclick="gsBarTune()" title="Switch station" style="
                display:flex;flex-direction:column;align-items:center;gap:1px;
                cursor:pointer;user-select:none;flex-shrink:0;">
                <div style="
                    width:22px;height:22px;border-radius:50%;
                    background:linear-gradient(to bottom,#3d2b1f,#1a0f0a);
                    border:1px solid rgba(176,141,87,0.5);position:relative;
                    box-shadow:0 1px 4px rgba(0,0,0,0.6);">
                    <div id="gsbar-kind" style="
                        position:absolute;top:2px;left:50%;width:2px;height:7px;
                        background:#B08D57;border-radius:999px;
                        transform:translateX(-50%) rotate(180deg);
                        transform-origin:50% 100%;transition:transform 0.5s ease;"></div>
                </div>
                <span id="gsbar-klbl" style="font-size:0.42rem;text-transform:uppercase;color:#B08D57;font-weight:bold;letter-spacing:0.06em;">WLOL</span>
            </div>
        </div>

        <script data-cfasync="false">
        (function() {{
            var PASTELS = ["#FFB7B2","#FFDAC1","#E2F0CB","#B5EAD7","#C7CEEA","#FF9AA2","#F8BBD0","#E1BEE7","#D1C4E9","#BBDEFB","#C8E6C9","#F0F4C3","#FFF9C4","#FFE0B2","#F5F5DC"];
            var SLOGANS = ["Dream big, work hard.","The sky is the limit.","Believe in yourself.","Seize the day.","Make it happen.","Stay hungry, stay foolish.","Innovation distinguishes leaders.","The best is yet to come.","Focus on the goal.","Everything you imagine is real.","Turn your wounds into wisdom.","Be the change.","Action is the key to success.","Don't wait for opportunity, create it.","Your time is limited.","Follow your heart.","Stay positive.","Work hard in silence.","Success is a journey.","Be original.","Never give up.","Chase your dreams.","Limitless potential.","Mindset is everything.","Prove them wrong.","Good things take time.","Focus on the good.","Be fearless.","The only way out is through.","Rise and grind.","Consistency is key.","Keep moving forward.","Life is what you make it.","Greatness takes time.","Push your limits.","Build your empire.","Vision without action is a dream.","Make every day count.","Lead with purpose.","Excellence is not an act, but a habit.","The power of now.","Unlock your potential.","Great things never come from comfort zones.","Do what you love.","Small steps, big results.","Radiate positivity.","Your only limit is you.","Keep the dream alive.","Focus on your vision.","Success favors the bold."];

            var gbStation = (localStorage.getItem('wadsStation') || 'wlol');
            var gbSloganIdx = Math.floor(Math.random() * SLOGANS.length);
            var gbMuted = false;
            var gbVol = 0.35;
            var wcprTracks = [];
            var wcprIdx = -1;
            var wcprAudio = document.getElementById('wcpr-shell-audio');

            // -- Petal cycle ----------------------------------------------
            function randP() {{ return PASTELS[Math.floor(Math.random() * PASTELS.length)]; }}
            function cyclePetals() {{
                var c = randP();
                ['gbP1','gbP2','gbP3','gbP4','gbP5','gbP6'].forEach(function(id) {{
                    var el = document.getElementById(id);
                    if (el) el.setAttribute('fill', c);
                }});
                var s1 = document.getElementById('gbS1'), s2 = document.getElementById('gbS2');
                if (s1) s1.setAttribute('stop-color', randP());
                if (s2) s2.setAttribute('stop-color', randP());
            }}
            setInterval(cyclePetals, 5000);

            // -- Slogan ---------------------------------------------------
            function nextSlogan() {{
                var el = document.getElementById('gsbar-slogan');
                if (!el) return;
                gbSloganIdx = (gbSloganIdx + 1) % SLOGANS.length;
                el.textContent = '"' + SLOGANS[gbSloganIdx] + '"';
                el.className = '';
                void el.offsetHeight;
                el.className = 'gsbar-slogan-anim';
            }}
            (function initSlogan() {{
                var el = document.getElementById('gsbar-slogan');
                if (el) {{ el.textContent = '"' + SLOGANS[gbSloganIdx] + '"'; el.className = 'gsbar-slogan-anim'; }}
            }})();
            setInterval(nextSlogan, 4000);

            // -- Station label --------------------------------------------
            function updateStationLabel() {{
                var sname = document.getElementById('gsbar-sname');
                var kind  = document.getElementById('gsbar-kind');
                var klbl  = document.getElementById('gsbar-klbl');
                var titleEl = document.getElementById('gs-title');
                if (gbStation === 'wlol') {{
                    if (sname) sname.textContent = 'WLOL 92.8 FM';
                    if (kind)  kind.style.transform = 'translateX(-50%) rotate(180deg)';
                    if (klbl)  klbl.textContent = 'WLOL';
                }} else {{
                    if (sname) sname.textContent = 'WCPR 104.1 FM';
                    if (kind)  kind.style.transform = 'translateX(-50%) rotate(0deg)';
                    if (klbl)  klbl.textContent = 'WCPR';
                    if (titleEl && wcprIdx >= 0 && wcprTracks[wcprIdx]) titleEl.textContent = wcprTracks[wcprIdx].title;
                    else if (titleEl && wcprTracks.length) titleEl.textContent = wcprTracks[0].title;
                }}
            }}
            updateStationLabel();

            // -- Progress bar ---------------------------------------------
            function fmtT(s) {{
                s = Math.floor(s||0); var m=Math.floor(s/60); var sec=s%60;
                return m+':'+(sec<10?'0':'')+sec;
            }}
            setInterval(function() {{
                var fill = document.getElementById('gsbar-pfill');
                var time = document.getElementById('gsbar-time');
                var audio;
                if (gbStation === 'wlol') {{
                    audio = document.getElementById('gs-audio');
                }} else {{
                    audio = wcprAudio;
                }}
                if (audio && audio.duration) {{
                    var pct = (audio.currentTime / audio.duration) * 100;
                    if (fill) fill.style.width = pct.toFixed(1) + '%';
                    if (time) time.textContent = fmtT(audio.currentTime) + ' / ' + fmtT(audio.duration);
                }}
            }}, 1000);

            // -- Tuner toggle ---------------------------------------------
            window.gsBarTune = function() {{
                if (gbStation === 'wlol') {{
                    // Switch to WCPR
                    try {{ gsSetEnabled(false); }} catch(e) {{}}
                    gbStation = 'wcpr';
                    localStorage.setItem('wadsStation', 'wcpr');
                    updateStationLabel();
                    wcprStart();
                }} else {{
                    // Switch to WLOL
                    if (wcprAudio) wcprAudio.pause();
                    gbStation = 'wlol';
                    localStorage.setItem('wadsStation', 'wlol');
                    updateStationLabel();
                    try {{ gsSetEnabled(true); }} catch(e) {{}}
                    var ppBtn = document.getElementById('gs-pp');
                    if (ppBtn) ppBtn.innerHTML = '&#9646;&#9646;';
                }}
            }};

            // -- Play/Pause/Skip (station-aware wrappers) -----------------
            window.gsBarPlay = window.gsBarToggle = function() {{
                if (gbStation === 'wlol') {{
                    try {{ gsTogglePlay(); }} catch(e) {{}}
                }} else {{
                    if (!wcprAudio) return;
                    if (wcprTracks.length && wcprIdx < 0) {{ wcprLoad(0); return; }}
                    if (wcprAudio.paused) {{ wcprAudio.play().catch(function(){{}}); }}
                    else                  {{ wcprAudio.pause(); }}
                    var ppBtn = document.getElementById('gs-pp');
                    if (ppBtn) ppBtn.innerHTML = wcprAudio.paused ? '&#9654;' : '&#9646;&#9646;';
                }}
            }};
            window.gsBarSkip = function() {{
                if (gbStation === 'wlol') {{
                    try {{ gsNext(); }} catch(e) {{}}
                }} else {{
                    if (wcprTracks.length) wcprLoad((wcprIdx + 1) % wcprTracks.length);
                }}
            }};
            window.gsBarMute = function() {{
                gbMuted = !gbMuted;
                var btn = document.getElementById('gsbar-mute');
                if (btn) btn.innerHTML = gbMuted ? '&#128263;' : '&#128266;';
                if (gbStation === 'wlol') {{
                    try {{ gsSetVolume(gbMuted ? 0 : gbVol); }} catch(e) {{}}
                    var vol = document.getElementById('gs-vol');
                    if (vol) vol.value = gbMuted ? 0 : gbVol;
                }} else {{
                    if (wcprAudio) wcprAudio.volume = gbMuted ? 0 : gbVol;
                }}
            }};

            // -- WCPR audio -----------------------------------------------
            function wcprLoad(idx) {{
                if (!wcprTracks.length || idx < 0 || idx >= wcprTracks.length) return;
                wcprIdx = idx;
                var t = wcprTracks[idx];
                if (wcprAudio) {{
                    wcprAudio.src    = t.url;
                    wcprAudio.volume = gbMuted ? 0 : gbVol;
                    wcprAudio.play().catch(function(){{}});
                }}
                var titleEl = document.getElementById('gs-title');
                if (titleEl) titleEl.textContent = t.title;
                var ppBtn = document.getElementById('gs-pp');
                if (ppBtn) ppBtn.innerHTML = '&#9646;&#9646;';
            }}
            function wcprStart() {{
                if (wcprTracks.length) {{
                    wcprLoad(wcprIdx >= 0 ? wcprIdx : 0);
                }} else {{
                    fetch('/wcpr/list').then(function(r){{return r.json();}}).then(function(tr){{
                        wcprTracks = tr || [];
                        if (wcprTracks.length) wcprLoad(0);
                        else {{
                            var t = document.getElementById('gs-title');
                            if (t) t.textContent = 'No WCPR episodes yet';
                        }}
                    }}).catch(function(){{}});
                }}
            }}
            if (wcprAudio) {{
                wcprAudio.addEventListener('ended', function() {{
                    if (wcprTracks.length) wcprLoad((wcprIdx+1) % wcprTracks.length);
                }});
            }}

            // -- Volume passthrough ---------------------------------------
            var origGsSetVolume = window.gsSetVolume;
            window.gsSetVolume = function(v) {{
                gbVol = parseFloat(v) || 0;
                if (origGsSetVolume) origGsSetVolume(v);
                if (gbStation === 'wcpr' && wcprAudio) wcprAudio.volume = gbMuted ? 0 : gbVol;
            }};

            // -- Init: restore station ------------------------------------
            if (gbStation === 'wcpr') {{
                updateStationLabel();
                // Don't autostart WCPR on page load -- wait for user interaction
                fetch('/wcpr/list').then(function(r){{return r.json();}}).then(function(tr){{
                    wcprTracks = tr || [];
                }}).catch(function(){{}});
            }}
        }})();
        </script>

        <script data-cfasync="false">
        (function() {{
            var ST_KEY    = 'wadsST';
            var CACHE_KEY = 'wadsST_tracks';
            var CACHE_TTL = 5 * 60 * 1000; // 5 minutes

            var audio  = document.getElementById('gs-audio');
            var bar    = document.getElementById('gs-bar');
            var ppBtn  = document.getElementById('gs-pp');
            var titleEl= document.getElementById('gs-title');
            var volSlider = document.getElementById('gs-vol');

            // -- state --
            var st = {{
                enabled:        true,
                volume:         0.35,
                shuffleOrder:   [],   // rebuilt fresh every page load
                trackIdx:       0,
                time:           0,
                currentTrackId: null, // persisted so we can resume the right song
                disabledIds:    []
            }};

            function loadSt() {{
                try {{
                    var s = JSON.parse(localStorage.getItem(ST_KEY) || '{{}}');
                    if (typeof s.enabled        === 'boolean') st.enabled        = s.enabled;
                    if (typeof s.volume         === 'number')  st.volume         = Math.max(0, Math.min(1, s.volume));
                    if (typeof s.time           === 'number')  st.time           = s.time;
                    if (typeof s.currentTrackId !== 'undefined') st.currentTrackId = s.currentTrackId;
                    if (Array.isArray(s.disabledIds))          st.disabledIds    = s.disabledIds;
                    // NOTE: shuffleOrder is intentionally NOT restored -- always rebuilt
                }} catch(e) {{}}
            }}
            function saveSt() {{
                try {{
                    st.time = audio.currentTime || 0;
                    var cur = currentTrack();
                    st.currentTrackId = cur ? cur.id : st.currentTrackId;
                    localStorage.setItem(ST_KEY, JSON.stringify(st));
                }} catch(e) {{}}
            }}

            // -- track cache --
            var tracks = [];  // {{id, title, url}}

            function loadCache() {{
                try {{
                    var c = JSON.parse(localStorage.getItem(CACHE_KEY) || '{{}}');
                    if (c.ts && (Date.now() - c.ts) < CACHE_TTL && Array.isArray(c.tracks) && c.tracks.length) {{
                        tracks = c.tracks;
                        return true;
                    }}
                }} catch(e) {{}}
                return false;
            }}
            function saveCache() {{
                try {{
                    localStorage.setItem(CACHE_KEY, JSON.stringify({{ts: Date.now(), tracks: tracks}}));
                }} catch(e) {{}}
            }}
            function fetchTracks(cb) {{
                if (loadCache()) {{ cb(); return; }}
                fetch('/soundtrack/list')
                    .then(function(r) {{ return r.json(); }})
                    .then(function(data) {{
                        tracks = data;
                        saveCache();
                        cb();
                    }})
                    .catch(function() {{ bar.style.display = 'none'; }});
            }}

            // -- shuffle --
            function shuffle(arr) {{
                for (var i = arr.length - 1; i > 0; i--) {{
                    var j = Math.floor(Math.random() * (i + 1));
                    var tmp = arr[i]; arr[i] = arr[j]; arr[j] = tmp;
                }}
                return arr;
            }}
            function buildShuffle() {{
                var available = tracks
                    .filter(function(t) {{ return st.disabledIds.indexOf(t.id) === -1; }})
                    .map(function(t) {{ return t.id; }});
                shuffle(available);
                st.shuffleOrder = available;
                st.trackIdx = 0;
            }}
            function getTrackById(id) {{
                return tracks.find(function(t) {{ return t.id === id; }}) || null;
            }}
            function currentTrack() {{
                if (!st.shuffleOrder.length) return null;
                var id = st.shuffleOrder[st.trackIdx % st.shuffleOrder.length];
                return getTrackById(id);
            }}

            // -- playback --
            function startTitleScroll() {{
                titleEl.style.animation = 'none';
                void titleEl.offsetWidth; // force reflow before re-enabling
                var clip = titleEl.parentElement;
                var overflow = titleEl.scrollWidth - clip.clientWidth;
                if (overflow > 4) {{
                    titleEl.style.setProperty('--gs-se', '-' + overflow + 'px');
                    var dur = Math.max(6, overflow / 30); // ~30px/s
                    titleEl.style.animation = 'gs-scroll-title ' + dur + 's ease-in-out infinite alternate';
                }}
            }}

            function applyTrack(t, seek) {{
                if (!t) {{ bar.style.display = 'none'; return; }}
                audio.src = t.url;
                audio.volume = st.volume;
                titleEl.textContent = t.title;
                requestAnimationFrame(startTitleScroll);
                updatePP();
                if (!st.enabled) {{ audio.load(); return; }}
                /* Always wait for canplay so the new src is loaded before
                   we seek/play -- calling play() right after load() races
                   the browser and replays the previous track. */
                audio.addEventListener('canplay', function onCP() {{
                    audio.removeEventListener('canplay', onCP);
                    if (seek > 0) audio.currentTime = seek;
                    audio.play().catch(function() {{}});
                }}, {{once: true}});
                audio.load();
            }}

            function updatePP() {{
                ppBtn.textContent = (st.enabled && !audio.paused) ? '⏸' : '▶';
            }}

            audio.addEventListener('ended', function() {{
                gsNext();
            }});
            audio.addEventListener('pause', updatePP);
            audio.addEventListener('play',  updatePP);

            // save time every 5s
            setInterval(function() {{ if (!audio.paused) saveSt(); }}, 5000);

            // -- public API (used by dashboard audio card) --
            window.gsTogglePlay = function() {{
                if (audio.paused) {{
                    st.enabled = true;
                    audio.play().catch(function() {{}});
                }} else {{
                    st.enabled = false;
                    audio.pause();
                }}
                saveSt();
                updatePP();
            }};
            window.gsNext = function() {{
                st.trackIdx = (st.trackIdx + 1) % (st.shuffleOrder.length || 1);
                saveSt();
                applyTrack(currentTrack(), 0);
            }};
            window.gsSetVolume = function(v) {{
                st.volume = parseFloat(v);
                audio.volume = st.volume;
                saveSt();
            }};
            window.gsSetEnabled = function(on) {{
                st.enabled = !!on;
                if (on) {{ audio.play().catch(function() {{}}); }}
                else    {{ audio.pause(); }}
                saveSt(); updatePP();
            }};
            window.gsSetTrackDisabled = function(id, disabled) {{
                var idx = st.disabledIds.indexOf(id);
                if (disabled && idx === -1)  st.disabledIds.push(id);
                if (!disabled && idx !== -1) st.disabledIds.splice(idx, 1);
                // rebuild shuffle, keep playing something valid
                buildShuffle();
                var cur = currentTrack();
                if (!cur || st.disabledIds.indexOf(cur.id) !== -1) {{
                    applyTrack(currentTrack(), 0);
                }}
                saveSt();
            }};
            window.gsRefreshTracks = function() {{
                try {{ localStorage.removeItem(CACHE_KEY); }} catch(e) {{}}
                fetchTracks(function() {{
                    buildShuffle();
                    applyTrack(currentTrack(), 0);
                    // rebuild dashboard track list if visible
                    if (typeof gsBuildTrackList === 'function') gsBuildTrackList();
                }});
            }};

            // -- init --
            loadSt();
            volSlider.value = st.volume;

            if (!st.enabled) {{
                bar.style.opacity = '0.45';
            }}

            fetchTracks(function() {{
                if (!tracks.length) {{ bar.style.display = 'none'; return; }}

                // Always build a fresh shuffle so new tracks are always included
                buildShuffle();

                // Resume the previously-playing track if it's still available
                if (st.currentTrackId != null) {{
                    var idx = st.shuffleOrder.indexOf(st.currentTrackId);
                    if (idx !== -1) st.trackIdx = idx;
                }}

                applyTrack(currentTrack(), st.time || 0);
            }});

            window.addEventListener('pagehide', saveSt);
            window.addEventListener('beforeunload', saveSt);
        }})();
        </script>
        <script>
        if ('serviceWorker' in navigator) {{
            window.addEventListener('load', () => {{
                navigator.serviceWorker.register('/sw.js').catch(() => {{}});
            }});
        }}
        </script>

        <!-- ═══════════════════════════════════════════════════
             NAVIGATION LOADER — shown on slow server pages
             (production costs calculator, etc.)
             Triggers on click, disappears when new page arrives.
        ═══════════════════════════════════════════════════ -->
        <div id="nav-loader" style="display:none;position:fixed;inset:0;z-index:9999;background:#0D0806;color:#F5F5DC;font-family:Georgia,serif;align-items:center;justify-content:center;">
          <div style="position:relative;width:100%;max-width:420px;padding:40px;background:#1A0F0A;border:4px solid #2D1810;box-shadow:0 25px 50px rgba(0,0,0,.8);display:flex;flex-direction:column;align-items:center;box-sizing:border-box;">
            <!-- brass corners -->
            <div style="position:absolute;top:8px;left:8px;width:16px;height:16px;border-top:1px solid rgba(176,141,87,.4);border-left:1px solid rgba(176,141,87,.4);"></div>
            <div style="position:absolute;top:8px;right:8px;width:16px;height:16px;border-top:1px solid rgba(176,141,87,.4);border-right:1px solid rgba(176,141,87,.4);"></div>
            <div style="position:absolute;bottom:8px;left:8px;width:16px;height:16px;border-bottom:1px solid rgba(176,141,87,.4);border-left:1px solid rgba(176,141,87,.4);"></div>
            <div style="position:absolute;bottom:8px;right:8px;width:16px;height:16px;border-bottom:1px solid rgba(176,141,87,.4);border-right:1px solid rgba(176,141,87,.4);"></div>
            <!-- apple SVG -->
            <div style="width:120px;height:120px;display:flex;align-items:center;justify-content:center;">
              <svg viewBox="0 0 201.5 207.54" style="width:100%;height:100%;filter:drop-shadow(0 0 20px rgba(229,0,0,0.4));" class="nl-pulse">
                <defs>
                  <linearGradient id="nl-lg"><stop style="stop-color:#e50000" offset="0"/><stop style="stop-color:#ff5555;stop-opacity:0" offset="1"/></linearGradient>
                  <radialGradient id="nl-rg" cy="172.36" cx="342.86" gradientTransform="matrix(1 0 0 1.0417 0 -7.1934)" r="193.09" gradientUnits="userSpaceOnUse"><stop offset="0" style="stop-color:#e50000"/><stop offset="1" style="stop-color:#ff5555;stop-opacity:0"/></radialGradient>
                </defs>
                <g transform="matrix(.15791 0 0 .15791 16.376 41.416)">
                  <path style="fill-rule:evenodd;fill:#008000" d="m470.03 168.72c-34.81 0.55-75.98 25.14-120.23 80.45 287.24-187.49 318.09 308.34-234.97 802.83h105.53c11.37-10.2 22.06-19.9 30.58-28.8 404.11-366.71 376.62-856.94 219.09-854.48z"/>
                  <path style="fill-rule:evenodd;fill:#008000" d="m834.13 625.57c77.98-166.27-189.49-144.42-409.81 189.81l-7.81-53.51c195.76-321.73 564.68-292.21 417.62-136.3z"/>
                  <path style="fill-rule:evenodd;fill:#008000" d="m44.425 533.84c57.285-180.94 245.14 23.08 178.28 431.36l43.44-35.18c76.75-381.56-224.17-617.67-221.72-396.18z"/>
                  <g transform="translate(17.143 -148.57)">
                    <path style="fill-rule:evenodd;fill:#ff8e8e" d="m357.14 205.1c0.02 71.81-65.23 130.02-145.71 130.02-80.49 0-145.73-58.21-145.72-130.02-0.009-71.81 65.23-130.02 145.72-130.02 80.48-0.002 145.73 58.21 145.71 130.02z" transform="translate(219.15 -163.07)"/>
                    <path style="fill-rule:evenodd;fill:#ff8e8e" d="m357.14 205.1c0.02 71.81-65.23 130.02-145.71 130.02-80.49 0-145.73-58.21-145.72-130.02-0.009-71.81 65.23-130.02 145.72-130.02 80.48-0.002 145.73 58.21 145.71 130.02z" transform="translate(27.721 -188.78)"/>
                    <path style="fill-rule:evenodd;fill:#ff8e8e" d="m357.14 205.1c0.02 71.81-65.23 130.02-145.71 130.02-80.49 0-145.73-58.21-145.72-130.02-0.009-71.81 65.23-130.02 145.72-130.02 80.48-0.002 145.73 58.21 145.71 130.02z" transform="translate(-86.565 -45.925)"/>
                    <path style="fill-rule:evenodd;fill:#ff8e8e" d="m357.14 205.1c0.02 71.81-65.23 130.02-145.71 130.02-80.49 0-145.73-58.21-145.72-130.02-0.009-71.81 65.23-130.02 145.72-130.02 80.48-0.002 145.73 58.21 145.71 130.02z" transform="translate(256.29 14.075)"/>
                    <path style="fill-rule:evenodd;fill:#ff8e8e" d="m357.14 205.1c0.02 71.81-65.23 130.02-145.71 130.02-80.49 0-145.73-58.21-145.72-130.02-0.009-71.81 65.23-130.02 145.72-130.02 80.48-0.002 145.73 58.21 145.71 130.02z" transform="translate(150.58 151.22)"/>
                    <path style="fill-rule:evenodd;fill:#ff8e8e" d="m357.14 205.1c0.02 71.81-65.23 130.02-145.71 130.02-80.49 0-145.73-58.21-145.72-130.02-0.009-71.81 65.23-130.02 145.72-130.02 80.48-0.002 145.73 58.21 145.71 130.02z" transform="translate(-12.279 128.36)"/>
                    <path style="fill-rule:evenodd;fill:url(#nl-rg)" d="m500 300.93c-39.84 48.69-62.4-55.86-121.24-33.61s-6.6 115.57-68.68 105.42c-62.08-10.16 17.18-81.97-31.51-121.81-48.69-39.83-103.38 52.08-125.63-6.76-22.25-58.85 79.57-26.11 89.73-88.2 10.15-62.077-96.79-63.492-56.96-112.18 39.84-48.687 62.4 55.86 121.25 33.613 58.84-22.247 6.59-115.57 68.67-105.42 62.08 10.158-17.17 81.973 31.51 121.81 48.69 39.837 103.39-52.077 125.63 6.767 22.25 58.84-79.57 26.11-89.73 88.19-10.15 62.08 96.8 63.5 56.96 112.18z" transform="matrix(1.2126 0 0 1.2126 -107.6 -19.596)"/>
                    <path style="fill-rule:evenodd;fill:#ffd5d5" d="m514.29 249.39c0.01 44.19-33.25 80.02-74.29 80.02s-74.3-35.83-74.29-80.02c-0.01-44.2 33.25-80.03 74.29-80.03s74.3 35.83 74.29 80.03z" transform="translate(-131.87 -59.983)"/>
                  </g>
                </g>
              </svg>
            </div>
            <!-- title + messages -->
            <div style="margin-top:28px;width:100%;text-align:center;">
              <p style="font-size:9px;letter-spacing:.5em;text-transform:uppercase;color:#B08D57;font-weight:900;opacity:.4;margin:0 0 14px;">Wadsworth Executive Terminal</p>
              <div id="nl-msgs" style="height:88px;display:flex;flex-direction:column-reverse;align-items:center;gap:4px;overflow:hidden;"></div>
            </div>
            <!-- progress bar -->
            <div style="margin-top:20px;width:100%;height:3px;background:rgba(0,0,0,.6);border:1px solid rgba(176,141,87,.1);border-radius:9999px;overflow:hidden;">
              <div id="nl-bar" style="height:100%;width:0%;background:linear-gradient(to right,#8B4513,#B08D57,#F5F5DC);box-shadow:0 0 10px rgba(176,141,87,.5);transition:width .15s linear;"></div>
            </div>
            <!-- footer -->
            <div style="margin-top:12px;width:100%;display:flex;justify-content:space-between;align-items:center;padding:0 4px;">
              <div style="display:flex;gap:14px;opacity:.2;font-size:13px;">&#9646; &#9632; &#9650;</div>
              <span id="nl-pct" style="font-size:9px;font-family:monospace;opacity:.4;color:#B08D57;">0% SECURED</span>
            </div>
            <div style="position:absolute;bottom:-52px;font-size:9px;letter-spacing:.6em;text-transform:uppercase;opacity:.2;color:#B08D57;" class="nl-pulse">Handshake in Progress</div>
          </div>
        </div>
        <style>
          @keyframes nl-pulse-anim {{ 0%,100%{{opacity:.3}} 50%{{opacity:.7}} }}
          .nl-pulse {{ animation: nl-pulse-anim 2s ease-in-out infinite; }}
        </style>
        <script>
        (function() {{
          var SLOW_PATHS = ['/stats/production-costs'];
          var STEPS = [
            "Initializing Secure Terminal...",
            "Authenticating Executive Credentials...",
            "Decrypting Asset Valuation Data...",
            "Syncing Broadcast Signal...",
            "Verifying Market Volatility...",
            "Establishing Brass Inlay Connection...",
            "Buffering Liquidity Pools...",
            "Optimizing Yield Curves...",
            "Parsing Capitol Schematics...",
            "Engaging Stealth Protocols...",
            "Allocating Surplus Capital...",
            "Calibrating Brass Resonance...",
            "Updating Ledger Entries...",
            "Deploying Asset Containers...",
            "Finalizing Handshake..."
          ];
          var overlay = document.getElementById('nav-loader');
          var bar     = document.getElementById('nl-bar');
          var pct     = document.getElementById('nl-pct');
          var msgs    = document.getElementById('nl-msgs');
          var prog    = 0;
          var timer   = null;
          var msgList = ["Initializing Secure Terminal..."];

          function renderMsgs() {{
            msgs.innerHTML = msgList.slice(0,4).map(function(m,i) {{
              var opacity = i === 0 ? '1' : '0.3';
              var scale   = i === 0 ? '1' : '0.95';
              var prefix  = i === 0 ? '&gt; ' : '';
              return '<p style="font-size:11px;font-style:italic;letter-spacing:-.01em;color:#B08D57;margin:0;transition:all .3s;opacity:'+opacity+';transform:scale('+scale+')">'
                     + prefix + m + '</p>';
            }}).join('');
          }}

          function startLoader() {{
            prog = 0; msgList = ["Initializing Secure Terminal..."];
            overlay.style.display = 'flex';
            renderMsgs();
            timer = setInterval(function() {{
              prog += 5;
              if (prog >= 100) prog = 0;
              if (Math.floor(prog/15) > Math.floor((prog-5)/15)) {{
                var next = STEPS[Math.floor(Math.random()*STEPS.length)];
                msgList = [next].concat(msgList).slice(0,4);
                renderMsgs();
              }}
              bar.style.width = prog + '%';
              pct.textContent = prog + '% SECURED';
            }}, 150);
          }}

          function _isSlowPath(pathname) {{
            for (var i=0; i<SLOW_PATHS.length; i++) {{
              if (pathname.startsWith(SLOW_PATHS[i])) return true;
            }}
            return false;
          }}

          // Show on <a> clicks to known-slow pages
          document.addEventListener('click', function(e) {{
            var a = e.target.closest('a');
            if (!a || !a.href) return;
            try {{
              var url = new URL(a.href);
              if (url.origin !== location.origin) return;
              if (_isSlowPath(url.pathname)) startLoader();
            }} catch(ex) {{}}
          }});

          // Show on form submits to known-slow pages (e.g. search box)
          document.addEventListener('submit', function(e) {{
            var form = e.target;
            if (!form || !form.action) return;
            try {{
              var url = new URL(form.action);
              if (url.origin !== location.origin) return;
              if (_isSlowPath(url.pathname)) startLoader();
            }} catch(ex) {{}}
          }});

          // Expose so inline onclick handlers can trigger it: window.startLoader()
          window.startLoader = startLoader;

          // Hide if user hits back/forward into this page (bfcache)
          window.addEventListener('pageshow', function(e) {{
            if (e.persisted) {{ overlay.style.display='none'; clearInterval(timer); }}
          }});
        }})();
        </script>
    </body>
    </html>
    """

# ==========================
# AUTHENTICATION HELPER
# ==========================

def require_auth(session_token: Optional[str] = Cookie(None)):
    """Check if user is authenticated."""
    try:
        import auth
        db = auth.get_db()
        player = auth.get_player_from_session(db, session_token)
        db.close()
        if not player:
            return RedirectResponse(url="/login", status_code=303)
        return player
    except Exception as e:
        print(f"[UX] Auth check failed: {e}")
        return RedirectResponse(url="/login", status_code=303)

# ==========================
# LIEN HELPER FUNCTIONS
# ==========================
# This now includes brokerage firm liens in addition to bank liens

def get_player_lien_info(player_id: int) -> dict:
    """
    Get comprehensive lien information for display in the UI.
    Includes liens from:
    - Land Bank
    - Apple Seeds ETF
    - Energy ETF
    - Brokerage Firm
    
    Returns:
        dict with keys:
        - has_lien: bool
        - total_owed: float
        - principal: float
        - interest: float
        - interest_rate_per_minute: float (for display)
        - garnishment_rate: float (percentage of cash taken)
        - status: str ("critical", "warning", "ok")
        - lien_count: int
        - sources: list of source names
    """
    try:
        from datetime import datetime
        from database import engine, SessionLocal
        
        all_liens = []
        total_principal = 0.0
        total_interest = 0.0
        total_paid = 0.0
        sources = []
        
        # Check Land Bank liens
        try:
            from banks.land_bank import BankLien as LandBankLien, LIEN_INTEREST_RATE as LB_RATE, LIEN_GARNISHMENT_PERCENTAGE as LB_GARNISH
            db = SessionLocal()
            try:
                land_liens = db.query(LandBankLien).filter(LandBankLien.player_id == player_id).all()
                for lien in land_liens:
                    if lien.principal + lien.interest_accrued - lien.total_paid > 0:
                        all_liens.append(("land_bank", lien, LB_RATE, LB_GARNISH))
                        total_principal += lien.principal
                        total_interest += lien.interest_accrued
                        total_paid += lien.total_paid
                        if "Land Bank" not in sources:
                            sources.append("Land Bank")
            finally:
                db.close()
        except Exception as e:
            print(f"[UX] Land bank lien check error: {e}")
        
        # Check Apple Seeds ETF liens
        try:
            from banks.apple_seeds_etf import BankLien as ETFBankLien, LIEN_INTEREST_RATE as ETF_RATE, LIEN_GARNISHMENT_PERCENTAGE as ETF_GARNISH
            db = SessionLocal()
            try:
                etf_liens = db.query(ETFBankLien).filter(ETFBankLien.player_id == player_id).all()
                for lien in etf_liens:
                    if lien.principal + lien.interest_accrued - lien.total_paid > 0:
                        all_liens.append(("apple_seeds_etf", lien, ETF_RATE, ETF_GARNISH))
                        total_principal += lien.principal
                        total_interest += lien.interest_accrued
                        total_paid += lien.total_paid
                        if "Apple Seeds ETF" not in sources:
                            sources.append("Apple Seeds ETF")
            finally:
                db.close()
        except Exception as e:
            print(f"[UX] ETF lien check error: {e}")
        
        # Check Energy ETF liens
        try:
            from banks.energy_etf import BankLien as EnergyBankLien, LIEN_INTEREST_RATE as EN_RATE, LIEN_GARNISHMENT_PERCENTAGE as EN_GARNISH
            db = SessionLocal()
            try:
                energy_liens = db.query(EnergyBankLien).filter(EnergyBankLien.player_id == player_id).all()
                for lien in energy_liens:
                    if lien.principal + lien.interest_accrued - lien.total_paid > 0:
                        all_liens.append(("energy_etf", lien, EN_RATE, EN_GARNISH))
                        total_principal += lien.principal
                        total_interest += lien.interest_accrued
                        total_paid += lien.total_paid
                        if "Energy ETF" not in sources:
                            sources.append("Energy ETF")
            finally:
                db.close()
        except Exception as e:
            print(f"[UX] Energy ETF lien check error: {e}")
        
        # Check Brokerage Firm liens
        try:
            from banks.brokerage_firm import BrokerageLien, get_credit_interest_rate, get_db as get_firm_db
            db = get_firm_db()
            try:
                broker_liens = db.query(BrokerageLien).filter(BrokerageLien.player_id == player_id).all()
                for lien in broker_liens:
                    balance = lien.principal + lien.interest_accrued - lien.total_paid
                    if balance > 0:
                        # Brokerage firm uses dynamic interest based on credit
                        broker_rate = get_credit_interest_rate(player_id) / 525600  # Per minute
                        all_liens.append(("brokerage_firm", lien, broker_rate, 0.50))
                        total_principal += lien.principal
                        total_interest += lien.interest_accrued
                        total_paid += lien.total_paid
                        if "Brokerage Firm" not in sources:
                            sources.append("Brokerage Firm")
            finally:
                db.close()
        except Exception as e:
            print(f"[UX] Brokerage lien check error: {e}")
        
        # Calculate totals
        total_owed = total_principal + total_interest - total_paid
        
        if total_owed <= 0 or not all_liens:
            return {
                "has_lien": False,
                "total_owed": 0.0,
                "principal": 0.0,
                "interest": 0.0,
                "interest_rate_per_minute": 0.0,
                "garnishment_rate": 0.0,
                "status": "ok",
                "lien_count": 0,
                "sources": []
            }
        
        # Use the highest rate for display (most aggressive)
        max_rate = max(lien[2] for lien in all_liens) * 100  # Convert to percentage
        max_garnish = max(lien[3] for lien in all_liens) * 100  # Convert to percentage
        
        # Determine status based on debt size
        if total_owed > 50000:
            status = "critical"
        elif total_owed > 10000:
            status = "warning"
        else:
            status = "ok"
        
        return {
            "has_lien": True,
            "total_owed": total_owed,
            "principal": total_principal - total_paid,
            "interest": total_interest,
            "interest_rate_per_minute": max_rate,
            "garnishment_rate": max_garnish,
            "status": status,
            "lien_count": len(all_liens),
            "sources": sources
        }
    
    except Exception as e:
        print(f"[UX] Error getting lien info: {e}")
        import traceback
        traceback.print_exc()
        return {
            "has_lien": False,
            "total_owed": 0.0,
            "principal": 0.0,
            "interest": 0.0,
            "interest_rate_per_minute": 0.0,
            "garnishment_rate": 0.0,
            "status": "ok",
            "lien_count": 0,
            "sources": []
        }

# ==========================
# PAGES
# ==========================

@router.get("/dashboard")
def dashboard_redirect():
    """Legacy redirect — the dashboard lives at /."""
    return RedirectResponse(url="/", status_code=301)


@router.get("/", response_class=HTMLResponse)
def home(session_token: Optional[str] = Cookie(None)):
    """Main dashboard."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return player
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)

    # Tutorial banner/overlay
    try:
        from tutorial_ux import should_show_tutorial_banner, get_tutorial_overlay_html
        tutorial_banner = ""
        tutorial_overlay = get_tutorial_overlay_html(player, "dashboard")
        if not tutorial_overlay and should_show_tutorial_banner(player):
            tutorial_banner = f"""
            <div style="
                background: linear-gradient(135deg, #0a1628, #0f172a);
                border: 2px solid #d4af37;
                border-radius: 6px;
                padding: 20px 24px;
                margin-bottom: 24px;
            ">
                <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;flex-wrap:wrap;">
                    <span style="background:#d4af37;color:#020617;padding:3px 12px;border-radius:12px;font-size:0.7rem;font-weight:bold;">TUTORIAL AVAILABLE</span>
                    <span style="color:#d4af37;font-size:0.85rem;font-weight:bold;">Level 1 · Startup Company</span>
                </div>
                <h3 style="color:#d4af37;margin:0 0 10px 0;font-size:1.05rem;">New to Wadsworth? Start the Tutorial!</h3>
                <p style="color:#94a3b8;margin:0 0 16px 0;line-height:1.6;font-size:0.9rem;">
                    Learn how to build businesses, manage your inventory, trade on the market, and unlock advanced
                    production chains. Complete the tutorial to earn a <strong style="color:#d4af37;">free, tax-exempt land plot</strong>
                    with all proximity features — yours to keep or sell.
                </p>
                <form action="/api/tutorial/start" method="post" style="display:inline;">
                    <button type="submit" style="background:#d4af37;color:#020617;border:none;padding:10px 24px;border-radius:4px;cursor:pointer;font-size:0.9rem;font-weight:bold;margin-right:12px;">
                        Begin Tutorial →
                    </button>
                </form>
                <a href="/api/tutorial/dismiss" style="color:#475569;font-size:0.8rem;">Dismiss</a>
            </div>
            """
    except Exception:
        tutorial_banner = ""
        tutorial_overlay = ""

    # Acquisition / diffuse notification banners
    acq_banners = ""
    try:
        from corporate_actions import get_acquisition_notifications, mark_acquisition_notifications_seen
        notifs = get_acquisition_notifications(player.id)
        banner_parts = []
        for offer in notifs.get("incoming_offers", []):
            banner_parts.append(f"""
            <div style="background:linear-gradient(135deg,#0a1628,#0f172a);border:2px solid #38bdf8;border-radius:6px;padding:16px 20px;margin-bottom:12px;">
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;flex-wrap:wrap;">
                    <span style="background:#38bdf8;color:#020617;padding:2px 10px;border-radius:10px;font-size:0.7rem;font-weight:bold;">ACQUISITION OFFER</span>
                </div>
                <p style="color:#cbd5e1;margin:0 0 12px 0;font-size:0.9rem;">
                    A player has offered to acquire <strong style="color:#38bdf8;">{offer.get('stake_pct',0)*100:.1f}%</strong> of your business income in exchange for <strong style="color:#38bdf8;">{offer.get('shares_offered',0):,}</strong> shares of their company. Offer expires in 7 days.
                </p>
                <div style="display:flex;gap:10px;flex-wrap:wrap;">
                    <form action="/api/corporate-actions/acquisition/accept/{offer['id']}" method="post" style="display:inline;">
                        <button type="submit" style="background:#38bdf8;color:#020617;border:none;padding:8px 18px;border-radius:4px;cursor:pointer;font-size:0.85rem;font-weight:bold;">Accept Offer</button>
                    </form>
                    <form action="/api/corporate-actions/acquisition/reject/{offer['id']}" method="post" style="display:inline;">
                        <button type="submit" style="background:#1e293b;color:#94a3b8;border:1px solid #334155;padding:8px 18px;border-radius:4px;cursor:pointer;font-size:0.85rem;">Reject</button>
                    </form>
                    <a href="/corporate-actions/dashboard" style="color:#475569;font-size:0.8rem;line-height:2.2;">View Details</a>
                </div>
            </div>""")
        for update in notifs.get("outgoing_updates", []):
            status = update.get("status", "unknown")
            color = "#22c55e" if status == "accepted" else "#ef4444"
            label = "ACCEPTED" if status == "accepted" else "REJECTED"
            banner_parts.append(f"""
            <div style="background:linear-gradient(135deg,#0a1628,#0f172a);border:2px solid {color};border-radius:6px;padding:16px 20px;margin-bottom:12px;">
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
                    <span style="background:{color};color:#020617;padding:2px 10px;border-radius:10px;font-size:0.7rem;font-weight:bold;">ACQUISITION {label}</span>
                </div>
                <p style="color:#cbd5e1;margin:0;font-size:0.9rem;">Your acquisition offer has been <strong style="color:{color};">{status}</strong>. <a href="/corporate-actions/dashboard" style="color:#38bdf8;">View your active stakes →</a></p>
            </div>""")
        for notice in notifs.get("diffuse_notices", []):
            deadline = notice.get("deadline_at", "")
            banner_parts.append(f"""
            <div style="background:linear-gradient(135deg,#0a1628,#0f172a);border:2px solid #f59e0b;border-radius:6px;padding:16px 20px;margin-bottom:12px;">
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
                    <span style="background:#f59e0b;color:#020617;padding:2px 10px;border-radius:10px;font-size:0.7rem;font-weight:bold;">DIFFUSE NOTICE</span>
                </div>
                <p style="color:#cbd5e1;margin:0 0 12px 0;font-size:0.9rem;">
                    The acquiring party has initiated a diffuse. You must return <strong style="color:#f59e0b;">{notice.get('shares_to_return',0):,} shares</strong> by <strong style="color:#f59e0b;">{deadline}</strong> or a lien will be placed on your account.
                </p>
                <form action="/api/corporate-actions/diffuse/return/{notice['id']}" method="post" style="display:inline;">
                    <button type="submit" style="background:#f59e0b;color:#020617;border:none;padding:8px 18px;border-radius:4px;cursor:pointer;font-size:0.85rem;font-weight:bold;">Return Shares Now</button>
                </form>
            </div>""")
        for resolved in notifs.get("diffuse_resolved", []):
            banner_parts.append(f"""
            <div style="background:linear-gradient(135deg,#0a1628,#0f172a);border:2px solid #22c55e;border-radius:6px;padding:16px 20px;margin-bottom:12px;">
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
                    <span style="background:#22c55e;color:#020617;padding:2px 10px;border-radius:10px;font-size:0.7rem;font-weight:bold;">DIFFUSE COMPLETE</span>
                </div>
                <p style="color:#cbd5e1;margin:0;font-size:0.9rem;">Your diffuse notice has been resolved. The stake has been fully returned. <a href="/corporate-actions/dashboard" style="color:#38bdf8;">View dashboard →</a></p>
            </div>""")
        if banner_parts:
            mark_acquisition_notifications_seen(player.id)
        acq_banners = "".join(banner_parts)
    except Exception:
        acq_banners = ""

    # Crypto inheritance notification banners
    crypto_inherit_banners = ""
    try:
        from estate import get_crypto_inheritance_notifications, mark_crypto_notifications_seen
        crypto_notifs = get_crypto_inheritance_notifications(player.id)
        crypto_banner_parts = []
        for notif in crypto_notifs:
            if notif.crypto_type == "staked_cash":
                crypto_banner_parts.append(f"""
            <div style="background:linear-gradient(135deg,#0a1628,#0f172a);border:2px solid #a78bfa;border-radius:6px;padding:16px 20px;margin-bottom:12px;">
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;flex-wrap:wrap;">
                    <span style="background:#a78bfa;color:#020617;padding:2px 10px;border-radius:10px;font-size:0.7rem;font-weight:bold;">CRYPTO INHERITANCE</span>
                    <span style="color:#64748b;font-size:0.75rem;">Hidden from government — no tax applied</span>
                </div>
                <p style="color:#cbd5e1;margin:0;font-size:0.9rem;">
                    You inherited staked <strong style="color:#a78bfa;">{notif.crypto_symbol}</strong> from <strong style="color:#e2e8f0;">{notif.deceased_name}</strong>'s estate.
                    The staked crypto has been liquidated and <strong style="color:#a78bfa;">{fmt_usd(notif.cash_equivalent, disp)}</strong> has been added to your cash balance.
                </p>
            </div>""")
            else:
                type_label = {"county": "County Token", "wsc": "WSC Stablecoin", "meme": "Meme Coin"}.get(notif.crypto_type, "Crypto")
                crypto_banner_parts.append(f"""
            <div style="background:linear-gradient(135deg,#0a1628,#0f172a);border:2px solid #a78bfa;border-radius:6px;padding:16px 20px;margin-bottom:12px;">
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;flex-wrap:wrap;">
                    <span style="background:#a78bfa;color:#020617;padding:2px 10px;border-radius:10px;font-size:0.7rem;font-weight:bold;">CRYPTO INHERITANCE</span>
                    <span style="color:#64748b;font-size:0.75rem;">Hidden from government — no tax applied</span>
                </div>
                <p style="color:#cbd5e1;margin:0;font-size:0.9rem;">
                    You inherited <strong style="color:#a78bfa;">{notif.amount:,.4f} {notif.crypto_symbol}</strong> ({type_label}) from <strong style="color:#e2e8f0;">{notif.deceased_name}</strong>'s estate
                    (≈ <strong style="color:#a78bfa;">{fmt_usd(notif.cash_equivalent, disp)}</strong> at time of transfer).
                    Check your crypto wallet for the new balance.
                </p>
            </div>""")
        if crypto_banner_parts:
            mark_crypto_notifications_seen(player.id)
        crypto_inherit_banners = "".join(crypto_banner_parts)
    except Exception:
        crypto_inherit_banners = ""

    dashboard_top = tutorial_overlay or tutorial_banner
    if acq_banners:
        dashboard_top = dashboard_top + acq_banners
    if crypto_inherit_banners:
        dashboard_top = dashboard_top + crypto_inherit_banners

    return shell(
        "Dashboard",
        f"""
        {dashboard_top}
        <h2>Welcome, CEO of {player.business_name}</h2>
        <style>
        .dc{{background:linear-gradient(135deg,#0a0f1e,#0f1628);border:1px solid var(--c);border-radius:12px;padding:22px 20px 18px;position:relative;overflow:hidden;transition:transform 0.18s,box-shadow 0.18s;display:block;text-decoration:none;color:inherit;}}
        .dc::before{{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:var(--g);}}
        .dc:hover{{transform:translateY(-3px);box-shadow:0 10px 36px rgba(0,0,0,0.55),0 0 28px var(--glow);text-decoration:none;}}
        .dc-ico{{font-size:1.9rem;margin-bottom:10px;display:block;}}
        .dc-t{{font-size:0.95rem;font-weight:700;color:var(--c);margin-bottom:4px;font-family:'Segoe UI',system-ui,sans-serif;letter-spacing:-0.01em;}}
        .dc-d{{font-size:0.74rem;color:#4a6080;line-height:1.55;margin-bottom:14px;font-family:'Segoe UI',system-ui,sans-serif;}}
        .dc-btn{{display:inline-block;padding:7px 16px;background:var(--btn);color:var(--fg,#020617);border-radius:6px;font-size:0.74rem;font-weight:700;font-family:'Segoe UI',system-ui,sans-serif;text-decoration:none;letter-spacing:0.01em;}}
        </style>
        <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:14px;margin-top:16px;">

            <a href="/businesses" class="dc" style="--c:#38bdf8;--g:linear-gradient(90deg,#38bdf8,#67e8f9);--glow:rgba(56,189,248,0.12);--btn:#38bdf8;">
                <span class="dc-ico">🏭</span>
                <div class="dc-t">Businesses</div>
                <div class="dc-d">Operate factories, plantations, and production chains across your land portfolio</div>
                <span class="dc-btn">Open Terminal</span>
            </a>

            <a href="/inventory" class="dc" style="--c:#f5a855;--g:linear-gradient(90deg,#f5a855,#f5d76e);--glow:rgba(245,168,85,0.12);--btn:#f5a855;">
                <span class="dc-ico">📦</span>
                <div class="dc-t">Inventory</div>
                <div class="dc-d">Raw materials, finished goods, and district items ready to sell or process</div>
                <span class="dc-btn">View Stock</span>
            </a>

            <a href="/land" class="dc" style="--c:#22c55e;--g:linear-gradient(90deg,#22c55e,#4ade80);--glow:rgba(34,197,94,0.12);--btn:#22c55e;">
                <span class="dc-ico">🌿</span>
                <div class="dc-t">Land</div>
                <div class="dc-d">Your owned plots, terrain types, business placement, and land portfolio</div>
                <span class="dc-btn">Real Estate</span>
            </a>

            <a href="/market" class="dc" style="--c:#67e8f9;--g:linear-gradient(90deg,#67e8f9,#a5f3fc);--glow:rgba(103,232,249,0.12);--btn:#67e8f9;">
                <span class="dc-ico">📈</span>
                <div class="dc-t">Market</div>
                <div class="dc-d">Buy and sell commodities with other players on the Wadsworth Exchange</div>
                <span class="dc-btn">Trading Floor</span>
            </a>

            <a href="/land-market" class="dc" style="--c:#f5d76e;--g:linear-gradient(90deg,#f5d76e,#fde68a);--glow:rgba(245,215,110,0.12);--btn:#f5d76e;">
                <span class="dc-ico">🏗️</span>
                <div class="dc-t">Land Market</div>
                <div class="dc-d">Government auctions, player-listed plots, and new land opportunities</div>
                <span class="dc-btn">View Auctions</span>
            </a>

            <a href="/banks" class="dc" style="--c:#86efac;--g:linear-gradient(90deg,#86efac,#bbf7d0);--glow:rgba(134,239,172,0.12);--btn:#86efac;">
                <span class="dc-ico">🏦</span>
                <div class="dc-t">Banks</div>
                <div class="dc-d">ETF investment funds, share trading, dividends, and reserve banking</div>
                <span class="dc-btn">Banking</span>
            </a>

            <a href="/executives" class="dc" style="--c:#c084fc;--g:linear-gradient(90deg,#c084fc,#e879f9);--glow:rgba(192,132,252,0.12);--btn:#c084fc;">
                <span class="dc-ico">👔</span>
                <div class="dc-t">Executives</div>
                <div class="dc-d">Hire C-suite talent, unlock abilities, and train your leadership team</div>
                <span class="dc-btn">C-Suite</span>
            </a>

            <a href="/p2p" class="dc" style="--c:#f59e0b;--g:linear-gradient(90deg,#f59e0b,#fbbf24);--glow:rgba(245,158,11,0.12);--btn:#f59e0b;">
                <span class="dc-ico">💬</span>
                <div class="dc-t">Peer to Peer</div>
                <div class="dc-d">Private contracts, chatrooms, and direct messages between players</div>
                <span class="dc-btn">P2P Network</span>
            </a>

            <a href="/stats/wiki" class="dc" style="--c:#f5a855;--g:linear-gradient(90deg,#f5a855,#f5d76e,#90c4f0);--glow:rgba(245,168,85,0.18);--btn:linear-gradient(90deg,#f5a855,#f5d76e);">
                <span class="dc-ico">📖</span>
                <div class="dc-t">WikaWads</div>
                <div class="dc-d">The living encyclopedia — businesses, districts, items, city projects, executives & analytics</div>
                <span class="dc-btn">Open Wiki</span>
            </a>

            <a href="/world-map" class="dc" style="--c:#4ade80;--g:linear-gradient(90deg,#22c55e,#4ade80,#86efac);--glow:rgba(74,222,128,0.12);--btn:#4ade80;">
                <span class="dc-ico">🗺️</span>
                <div class="dc-t">World Map</div>
                <div class="dc-d">Visualize your economic empire on an interactive grid map of Wadsworth</div>
                <span class="dc-btn">Open Map</span>
            </a>

            <a href="/settings" class="dc" style="--c:#818cf8;--g:linear-gradient(90deg,#818cf8,#a5b4fc);--glow:rgba(129,140,248,0.12);--btn:#818cf8;">
                <span class="dc-ico">⚙️</span>
                <div class="dc-t">Settings</div>
                <div class="dc-d">Audio player controls, track selection, volume, and game preferences</div>
                <span class="dc-btn">Open Settings</span>
            </a>

        </div>
        """,
        player.cash_balance,
        player.id
    )

@router.get("/businesses", response_class=HTMLResponse)
def businesses(session_token: Optional[str] = Cookie(None), sort: str = "name", biz_filter: str = "all"):
    """Business operations view with live progress and retail pricing."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return player
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)
    try:
        from business import Business, BUSINESS_TYPES, get_dismantling_status, DISMANTLING_TICKS, RetailPrice
        from land import LandPlot, get_db as get_land_db
        import json as _json
        import inventory as _inv_mod
        land_db = get_land_db()
        player_businesses = land_db.query(Business).filter(Business.owner_id == player.id).order_by(Business.id).all()
        inv = _inv_mod.get_player_inventory(player.id)  # {item_type: qty}

        if not player_businesses:
            land_db.close()
            return shell("Businesses", "<h3>No businesses found.</h3><a href='/land' class='btn-blue'>Go to Land</a>", player.cash_balance, player.id)

        # Build enriched data list
        biz_data = []
        for biz in player_businesses:
            config = BUSINESS_TYPES.get(biz.business_type)
            if not config:
                from business import get_district_business_types
                district_types = get_district_business_types()
                config = district_types.get(biz.business_type, {})
            biz_name = config.get("name", biz.business_type)
            biz_class = config.get("class", "production")
            cycles_total = config.get("cycles_to_complete", 1)
            progress_pct = (biz.progress_ticks / cycles_total * 100) if cycles_total > 0 else 0
            dismantle_status = get_dismantling_status(biz.id)
            plot = land_db.query(LandPlot).filter(LandPlot.id == biz.land_plot_id).first() if biz.land_plot_id else None
            biz_data.append({"biz": biz, "config": config, "name": biz_name, "cls": biz_class,
                              "cycles_total": cycles_total, "progress_pct": progress_pct,
                              "dismantle": dismantle_status, "plot": plot})

        # Summary stats
        total        = len(biz_data)
        n_active     = sum(1 for d in biz_data if d["biz"].is_active and not d["dismantle"])
        n_paused     = sum(1 for d in biz_data if not d["biz"].is_active and not d["dismantle"])
        n_dismantling= sum(1 for d in biz_data if d["dismantle"])
        n_production = sum(1 for d in biz_data if d["cls"] == "production")
        n_retail     = sum(1 for d in biz_data if d["cls"] == "retail")

        # City production buffs panel
        city_buffs_html = ""
        try:
            from city_projects import get_city_production_buffs
            _cb = get_city_production_buffs(player.id)
            _buff_rows = []
            for _key, _label, _bad in [
                ("output_multiplier", "Output", False), ("wage_multiplier", "Wages", True),
                ("input_multiplier", "Inputs", True), ("cycle_speed_multiplier", "Cycle Speed", True),
                ("market_fee_multiplier", "Market Fees", True), ("loan_interest_multiplier", "Loan Interest", True),
            ]:
                _val = _cb.get(_key, 1.0)
                if abs(_val - 1.0) > 0.001:
                    _pct = (_val - 1.0) * 100
                    _sign = "+" if _pct >= 0 else ""
                    _col = ("#f87171" if _pct > 0 else "#4ade80") if _bad else ("#4ade80" if _pct > 0 else "#f87171")
                    _buff_rows.append(f'<span style="color:{_col};">{_label} {_sign}{_pct:.1f}%</span>')
            if _cb.get("sales_tax_rate", 0.0) > 0:
                _buff_rows.append(f'<span style="color:#f87171;">Sales Tax {_cb["sales_tax_rate"]*100:.2f}%</span>')
            if _buff_rows:
                city_buffs_html = f'''<div class="card" style="margin-bottom:14px;border-color:#334155;padding:10px 16px;">
                    <div style="font-size:11px;color:#64748b;margin-bottom:6px;text-transform:uppercase;letter-spacing:.05em;">City Production Modifiers</div>
                    <div style="display:flex;flex-wrap:wrap;gap:10px;font-size:13px;">{"&nbsp;·&nbsp;".join(_buff_rows)}</div></div>'''
        except Exception:
            pass

        # Build a card for each business
        def make_card(d):
            biz          = d["biz"]
            config       = d["config"]
            biz_name     = d["name"]
            biz_class    = d["cls"]
            cycles_total = d["cycles_total"]
            progress_pct = d["progress_pct"]
            ds           = d["dismantle"]
            plot         = d["plot"]
            startup_cost = config.get("startup_cost", 0)
            wage_cost    = config.get("base_wage_cost", 0)
            if plot:
                plot_info = f"Plot #{plot.id} · {plot.terrain_type.title()}"
            elif getattr(biz, "district_id", None):
                plot_info = f"District #{biz.district_id}"
            else:
                plot_info = "Unknown Location"

            if ds:
                prog = ds["progress_pct"]
                return f'''<div class="biz-card" data-name="{biz_name.lower()}" data-bizclass="{biz_class}" data-active="false" data-dismantling="true" data-progress="0" style="border-color:#ef4444;">
                    <div class="biz-card-header">
                        <div><span class="biz-name" style="font-weight:bold;">{biz_name}</span>
                        <span class="badge" style="background:#ef4444;color:#fff;margin-left:6px;">DISMANTLING</span></div>
                    </div>
                    <div style="padding:0 16px 4px;font-size:0.75rem;color:#64748b;">{plot_info} · ID #{biz.id}</div>
                    <div class="biz-card-progress">
                        <div style="display:flex;justify-content:space-between;font-size:0.75rem;color:#94a3b8;margin-bottom:2px;">
                            <span>Refund Progress</span>
                            <span>{ds["ticks_remaining"]}/{DISMANTLING_TICKS} ticks · {fmt_usd(ds["paid_so_far"], disp)} of {fmt_usd(ds["total_refund"], disp)}</span>
                        </div>
                        <div class="progress-bar-wrap"><div class="progress-bar-fill" style="width:{prog:.1f}%;background:#ef4444;"></div></div>
                    </div>
                </div>'''

            status_color     = "#22c55e" if biz.is_active else "#f59e0b"
            status_label     = "ACTIVE" if biz.is_active else "PAUSED"
            class_color      = "#4ade80" if biz_class == "production" else "#38bdf8"
            toggle_lbl       = "Pause" if biz.is_active else "Resume"
            toggle_cls       = "btn-sm-orange" if biz.is_active else "btn-sm-green"
            paused_line_idxs = set(_json.loads(biz.paused_lines or "[]"))
            paused_prod_keys = set(_json.loads(biz.paused_products or "[]"))

            if biz_class == "production":
                lines_html = ""
                for li, line in enumerate(config.get("production_lines", [])):
                    inp_parts = [f"{req['quantity']:,}× {req['item'].replace('_',' ').title()}" for req in line.get("inputs", [])]
                    inp_str   = " + ".join(inp_parts) if inp_parts else "No inputs"
                    out_str   = f"{line['output_qty']:,}× {line['output_item'].replace('_',' ').title()}"
                    lp        = li in paused_line_idxs
                    # Feasibility: check inventory covers every required input
                    missing = []
                    for req in line.get("inputs", []):
                        have = inv.get(req["item"], 0)
                        need = req["quantity"]
                        if have < need:
                            missing.append(f"{req['item'].replace('_',' ').title()}: {have:,.0f} / {need:,} needed")
                    if not missing:
                        dot = '<span style="color:#22c55e;font-size:0.85rem;flex-shrink:0;" title="All inputs available">●</span>'
                    else:
                        tip = "Missing — " + " | ".join(missing)
                        dot = f'<span style="color:#ef4444;font-size:0.85rem;flex-shrink:0;" title="{tip}">●</span>'
                    lines_html += f'''<div class="line-row{' paused' if lp else ''}" id="line-{biz.id}-{li}">
                        {dot}
                        <span style="font-size:0.78rem;color:#94a3b8;flex:1;">{inp_str} → {out_str}</span>
                        <form action="/api/business/toggle-line?sort={sort}&biz_filter={biz_filter}" method="post" style="flex-shrink:0;display:inline;">
                            <input type="hidden" name="business_id" value="{biz.id}">
                            <input type="hidden" name="line_index" value="{li}">
                            <button type="submit" class="btn-sm {'btn-sm-green' if lp else 'btn-sm-orange'}">{'Resume' if lp else 'Pause'}</button>
                        </form>
                    </div>'''
                detail_html = f'''<div class="biz-card-body">
                    <div style="font-size:0.72rem;color:#64748b;margin-bottom:8px;text-transform:uppercase;letter-spacing:.05em;">Production Lines</div>
                    {lines_html or '<span style="color:#475569;font-size:0.82rem;">No production lines configured</span>'}
                </div>'''
            else:
                retail_rows = ""
                for item, stats in config.get("products", {}).items():
                    pe        = land_db.query(RetailPrice).filter(RetailPrice.player_id == player.id, RetailPrice.item_type == item).first()
                    cur_p     = fmt_usd(pe.price, disp) if pe else "Market"
                    ip        = item in paused_prod_keys
                    safe_item = item.replace("'", "\\'")
                    # Stock feasibility
                    in_stock  = inv.get(item, 0)
                    if in_stock > 0:
                        dot = f'<span style="color:#22c55e;font-size:0.75rem;" title="In stock: {in_stock:,.0f}">● {in_stock:,.0f}</span>'
                    else:
                        dot = '<span style="color:#ef4444;font-size:0.75rem;" title="No stock — nothing to sell">● Out of stock</span>'
                    retail_rows += f'''<div class="line-row{' paused' if ip else ''}" id="retail-{biz.id}-{item}" style="flex-wrap:wrap;gap:6px;">
                        <span style="font-size:0.82rem;flex:1;">{item.replace("_"," ").title()} <span style="color:#64748b;font-size:0.75rem;">e={stats.get("elasticity","?")}</span> {dot}</span>
                        <div style="display:flex;gap:5px;align-items:center;flex-wrap:wrap;">
                            <span style="color:#38bdf8;font-size:0.82rem;font-weight:bold;">{cur_p}</span>
                            <form action="/api/retail/set-price?sort={sort}&biz_filter={biz_filter}" method="post" style="display:flex;gap:4px;align-items:center;">
                                <input type="hidden" name="item_type" value="{item}">
                                <input type="number" name="price" step="0.01" min="0.01" placeholder="{disp["code"]}" style="width:90px;padding:3px 5px;font-size:0.78rem;">
                                <button type="submit" class="btn-sm btn-sm-blue">Set</button>
                            </form>
                            <form action="/api/business/toggle-retail?sort={sort}&biz_filter={biz_filter}" method="post" style="display:inline;">
                                <input type="hidden" name="business_id" value="{biz.id}">
                                <input type="hidden" name="item_type" value="{item}">
                                <button type="submit" class="btn-sm {'btn-sm-green' if ip else 'btn-sm-orange'}">{'Resume' if ip else 'Pause'}</button>
                            </form>
                        </div>
                    </div>'''
                detail_html = f'''<div class="biz-card-body">
                    <div style="font-size:0.72rem;color:#64748b;margin-bottom:8px;text-transform:uppercase;letter-spacing:.05em;">Retail Products</div>
                    {retail_rows}
                </div>'''

            return f'''<div class="biz-card" id="biz-card-{biz.id}" data-name="{biz_name.lower()}" data-bizclass="{biz_class}" data-active="{'true' if biz.is_active else 'false'}" data-dismantling="false" data-progress="{progress_pct:.1f}" data-cycles="{cycles_total}">
                <div class="biz-card-header">
                    <div style="flex:1;min-width:0;">
                        <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
                            <span class="biz-name" style="font-weight:bold;">{biz_name}</span>
                            <span id="status-badge-{biz.id}" class="badge" style="background:{status_color};color:#020617;">{status_label}</span>
                            <span class="badge" style="background:{class_color};color:#020617;">{biz_class.upper()}</span>
                        </div>
                        <div style="font-size:0.75rem;color:#64748b;margin-top:3px;">{plot_info} · ID #{biz.id} · Start {fmt_usd(startup_cost, disp)} · Wage {fmt_usd(wage_cost, disp)}/cycle</div>
                    </div>
                    <div class="biz-actions">
                        <form action="/api/business/toggle?sort={sort}&biz_filter={biz_filter}" method="post" style="display:inline;">
                            <input type="hidden" name="business_id" value="{biz.id}">
                            <button type="submit" class="btn-sm {toggle_cls}">{toggle_lbl}</button>
                        </form>
                        <form action="/api/business/dismantle?sort={sort}&biz_filter={biz_filter}" method="post" style="display:inline;" onsubmit="return confirm('Dismantle this business? You receive 50% of startup cost paid over 100 ticks.')">
                            <input type="hidden" name="business_id" value="{biz.id}">
                            <button type="submit" class="btn-sm btn-sm-red">Dismantle</button>
                        </form>
                    </div>
                </div>
                <div class="biz-card-progress">
                    <div style="display:flex;justify-content:space-between;font-size:0.75rem;color:#94a3b8;margin-bottom:2px;">
                        <span>Cycle Progress</span>
                        <span id="pt-{biz.id}">{biz.progress_ticks:,} / {cycles_total:,} ticks ({progress_pct:.1f}%)</span>
                    </div>
                    <div class="progress-bar-wrap"><div class="progress-bar-fill" id="pb-{biz.id}" style="width:{min(progress_pct,100):.1f}%;"></div></div>
                </div>
                {detail_html}
            </div>'''

        # Apply filter
        if biz_filter == "active":
            filtered = [d for d in biz_data if d["biz"].is_active and not d["dismantle"]]
        elif biz_filter == "paused":
            filtered = [d for d in biz_data if not d["biz"].is_active and not d["dismantle"]]
        elif biz_filter == "production":
            filtered = [d for d in biz_data if d["cls"] == "production"]
        elif biz_filter == "retail":
            filtered = [d for d in biz_data if d["cls"] == "retail"]
        elif biz_filter == "dismantling":
            filtered = [d for d in biz_data if d["dismantle"]]
        else:
            filtered = list(biz_data)

        # Apply sort
        if sort == "status":
            filtered.sort(key=lambda d: (0 if d["dismantle"] else (1 if d["biz"].is_active else 2), d["name"].lower()))
        elif sort == "progress":
            filtered.sort(key=lambda d: -d["progress_pct"])
        else:  # name
            filtered.sort(key=lambda d: d["name"].lower())

        cards_html = "".join(make_card(d) for d in filtered)
        land_db.close()

        # Filter/sort button helpers (href-based, no JS required)
        def fb(fval, label, count):
            ac = " active" if biz_filter == fval else ""
            return f'<a href="/businesses?sort={sort}&biz_filter={fval}" class="biz-filter-btn{ac}">{label} ({count})</a>'
        def sb(sval, label):
            ac = " active" if sort == sval else ""
            return f'<a href="/businesses?sort={sval}&biz_filter={biz_filter}" class="biz-sort-btn{ac}">{label}</a>'

        # No inline JS needed -- all actions use standard form/href submissions

        body = f'''<style>
.biz-summary{{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:16px;}}
.biz-stat{{background:#0f172a;border:1px solid #1e293b;padding:8px 14px;border-radius:4px;text-align:center;min-width:72px;}}
.biz-stat .val{{font-size:1.4rem;font-weight:bold;}} .biz-stat .lbl{{font-size:0.68rem;color:#64748b;letter-spacing:.05em;text-transform:uppercase;}}
.biz-filter-btn{{display:inline-block;padding:4px 10px;border:1px solid #1e293b;background:#0f172a;color:#64748b;border-radius:4px;cursor:pointer;font-size:0.8rem;text-decoration:none;}}
.biz-filter-btn:hover,.biz-filter-btn.active{{border-color:#38bdf8;color:#38bdf8;}}
.biz-sort-btn{{display:inline-block;padding:4px 6px;color:#64748b;cursor:pointer;font-size:0.8rem;text-decoration:underline;}}
.biz-sort-btn.active{{color:#38bdf8;}}
.biz-grid{{display:grid;gap:12px;}}
.biz-card{{background:#0f172a;border:1px solid #1e293b;border-radius:4px;overflow:hidden;}}
.biz-card-header{{padding:14px 16px 8px;display:flex;justify-content:space-between;align-items:flex-start;gap:10px;}}
.biz-card-progress{{padding:0 16px 12px;}}
.biz-card-body{{border-top:1px solid #1e293b;padding:12px 16px;}}
.biz-actions{{display:flex;gap:6px;flex-shrink:0;flex-wrap:wrap;}}
.btn-sm{{padding:5px 10px;font-size:0.78rem;border:none;border-radius:3px;cursor:pointer;font-family:inherit;font-weight:600;}}
.btn-sm-blue{{background:#38bdf8;color:#020617;}} .btn-sm-orange{{background:#f59e0b;color:#020617;}}
.btn-sm-red{{background:#ef4444;color:#fff;}} .btn-sm-green{{background:#22c55e;color:#020617;}}
.progress-bar-wrap{{background:#020617;height:6px;border-radius:3px;overflow:hidden;margin-top:4px;}}
.progress-bar-fill{{height:100%;background:#38bdf8;border-radius:3px;}}
.line-row{{display:flex;justify-content:space-between;align-items:center;padding:6px 8px;background:#020617;border-radius:4px;margin-bottom:4px;gap:8px;}}
.line-row.paused{{opacity:0.4;}}
</style>
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;flex-wrap:wrap;gap:8px;">
    <div style="display:flex;align-items:center;gap:12px;">
        <a href="/" style="color:#64748b;font-size:0.85rem;">← Dashboard</a>
        <h2 style="margin:0;font-size:1.2rem;">Business Terminal</h2>
    </div>
    <a href="/stats/production-costs" class="btn-blue" style="font-size:0.8rem;">📊 Production Costs</a>
</div>
<div class="biz-summary">
    <div class="biz-stat"><div class="val">{total}</div><div class="lbl">Total</div></div>
    <div class="biz-stat" style="border-color:#22c55e;"><div class="val" style="color:#22c55e;">{n_active}</div><div class="lbl">Active</div></div>
    <div class="biz-stat" style="border-color:#f59e0b;"><div class="val" style="color:#f59e0b;">{n_paused}</div><div class="lbl">Paused</div></div>
    <div class="biz-stat" style="border-color:#ef4444;"><div class="val" style="color:#ef4444;">{n_dismantling}</div><div class="lbl">Dismantling</div></div>
    <div class="biz-stat" style="border-color:#4ade80;"><div class="val" style="color:#4ade80;">{n_production}</div><div class="lbl">Production</div></div>
    <div class="biz-stat" style="border-color:#38bdf8;"><div class="val" style="color:#38bdf8;">{n_retail}</div><div class="lbl">Retail</div></div>
</div>
{city_buffs_html}
<div style="display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin-bottom:16px;">
    <span style="color:#64748b;font-size:0.78rem;">Filter:</span>
    {fb("all","All",total)} {fb("active","Active",n_active)} {fb("paused","Paused",n_paused)}
    {fb("production","Production",n_production)} {fb("retail","Retail",n_retail)} {fb("dismantling","Dismantling",n_dismantling)}
    <span style="color:#334155;margin:0 2px;">|</span>
    <span style="color:#64748b;font-size:0.78rem;">Sort:</span>
    {sb("name","Name")} {sb("status","Status")} {sb("progress","Progress")}
</div>
<div id="biz-grid" class="biz-grid">{cards_html}</div>'''

        tut_overlay = ""
        try:
            from tutorial_ux import get_tutorial_overlay_html
            tut_overlay = get_tutorial_overlay_html(player, "businesses")
        except Exception:
            pass
        return shell("Businesses", tut_overlay + body, player.cash_balance, player.id)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return shell("Businesses", f"Error loading terminal: {e}", player.cash_balance, player.id)

@router.get("/inventory", response_class=HTMLResponse)
def inventory_page(session_token: Optional[str] = Cookie(None), filter: str = "all", sort: str = "name", dir: str = "asc"):
    """Inventory management view."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return player
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)
    try:
        import inventory as inv_mod
        inv = inv_mod.get_player_inventory(player.id)

        categories = {"all": "All", "seeds": "Seeds", "fruits": "Fruits", "vegetables": "Vegetables", "liquids": "Liquids", "energy": "Energy", "animals": "Animals", "materials": "Materials", "luxury": "Luxury", "financial": "Financial"}
        filter_tabs = '<div style="margin-bottom: 16px; display: flex; flex-wrap: wrap; gap: 8px;">'
        for k, v in categories.items():
            color = "#38bdf8" if k == filter else "#64748b"
            border = "1px solid #38bdf8" if k == filter else "1px solid #1e293b"
            filter_tabs += f'<a href="/inventory?filter={k}&sort={sort}&dir={dir}" style="color: {color}; border: {border}; padding: 4px 12px; border-radius: 4px; text-decoration: none; font-size: 0.85rem;">{v}</a>'
        filter_tabs += '</div>'

        # Sort controls
        sort_controls = '<div style="margin-bottom: 16px; display: flex; gap: 12px; align-items: center;"><span style="color: #64748b; font-size: 0.85rem;">Sort:</span>'
        sort_options = [("name", "Name"), ("qty", "Quantity"), ("value", "Value")]
        for s_key, s_label in sort_options:
            if s_key == sort:
                new_dir = "desc" if dir == "asc" else "asc"
                arrow = " ↑" if dir == "asc" else " ↓"
                color = "#38bdf8"
            else:
                new_dir = "asc"
                arrow = ""
                color = "#64748b"
            sort_controls += f'<a href="/inventory?filter={filter}&sort={s_key}&dir={new_dir}" style="color: {color}; text-decoration: none; font-size: 0.85rem;">{s_label}{arrow}</a>'
        sort_controls += '</div>'

        # Categorisation helpers
        fruits_list = ["apples", "oranges", "bananas", "grapes", "strawberries", "blueberries", "peaches", "pears", "mangoes", "pineapples"]
        vegetables_list = ["potatoes", "carrots", "tomatoes", "onions", "lettuce", "broccoli", "spinach", "peppers", "cucumbers", "corn"]
        animals_list = ["horses", "cows", "chickens", "pigs", "sheep", "goats", "ducks", "rabbits", "fish", "cattle"]
        materials_list = ["lumber", "steel", "brick", "glass", "coal", "iron", "copper", "stone", "cement", "wood", "ore", "clay", "sand", "gravel"]
        luxury_list = ["diamonds", "gold", "wine", "perfume", "silk", "ivory", "platinum", "jewelry", "fur", "truffles"]
        financial_list = ["shares", "bonds", "certificates", "notes", "tokens", "deeds"]

        def _item_category(item):
            if item.endswith("_seeds"):
                return "seeds"
            if item in fruits_list:
                return "fruits"
            if item in vegetables_list:
                return "vegetables"
            if "water" in item or item.endswith("_juice") or item.endswith("_milk"):
                return "liquids"
            if item == "energy":
                return "energy"
            if item in animals_list:
                return "animals"
            if item in materials_list:
                return "materials"
            if item in luxury_list:
                return "luxury"
            if any(item.startswith(f) or item.endswith(f) for f in financial_list):
                return "financial"
            return "other"

        # Filter items
        filtered = []
        for item, qty in inv.items():
            if filter != "all":
                cat = _item_category(item)
                if cat != filter:
                    continue
            item_info = inv_mod.get_item_info(item) or {}
            unit_price = item_info.get("base_price") or item_info.get("value") or 0
            filtered.append((item, qty, item_info, unit_price))

        # Sort items
        if sort == "qty":
            filtered.sort(key=lambda x: x[1], reverse=True)
        elif sort == "value":
            filtered.sort(key=lambda x: x[1] * x[3], reverse=True)
        else:
            # name sort
            if dir == "desc":
                filtered.sort(key=lambda x: x[0], reverse=True)
            else:
                filtered.sort(key=lambda x: x[0])

        items_html = ""
        for item, qty, item_info, unit_price in filtered:
            est_value_line = ""
            if unit_price:
                est_val = qty * unit_price
                est_value_line = f'<br><small style="color: #22c55e;">Est. Value: {fmt_usd(est_val, disp)} ({fmt_usd(unit_price, disp)}/unit)</small>'
            items_html += f'''
            <div class="card">
                <div style="display: flex; justify-content: space-between;">
                    <div>
                        <strong>{item.replace("_", " ").title()}</strong><br>
                        <small style="color: #64748b;">{item_info.get("description", "No description")}</small>{est_value_line}
                    </div>
                    <div style="text-align: right;">
                        <span style="font-size: 1.2rem; color: #38bdf8;">{qty:.0f} units</span>
                        <form action="/api/inventory/list" method="post" style="margin-top: 10px;">
                            <input type="hidden" name="item_type" value="{item}">
                            <input type="number" name="quantity" placeholder="Qty" style="width: 60px;" required>
                            <input type="number" name="price" step="0.0001" placeholder="Price ({disp['code']})" style="width: 80px;" required>
                            <button type="submit" class="btn-blue">List</button>
                        </form>
                    </div>
                </div>
            </div>'''

        inv_body = (
            f'<a href="/" style="color: #38bdf8;"><- Dashboard</a>'
            f'<h1>Your Inventory</h1>'
            f'<div style="display:flex;gap:10px;margin-bottom:16px;flex-wrap:wrap;">'
            f'<a href="/inventory/trusted-list" style="background:#1e1b4b;border:1px solid #6d28d9;color:#a78bfa;padding:6px 14px;border-radius:4px;text-decoration:none;font-size:0.85rem;">&#128274; Trusted Trader List</a>'
            f'<a href="/inventory/swaps" style="background:#1e1b4b;border:1px solid #7c3aed;color:#c4b5fd;padding:6px 14px;border-radius:4px;text-decoration:none;font-size:0.85rem;">&#8646; Item Swaps</a>'
            f'</div>'
            f'{filter_tabs}{sort_controls}{items_html}'
        )

        # Inject tutorial overlay for inventory-relevant steps
        try:
            from tutorial_ux import get_tutorial_overlay_html
            tut_overlay = get_tutorial_overlay_html(player, "inventory")
            if tut_overlay:
                inv_body = tut_overlay + inv_body
        except Exception:
            pass

        return shell("Inventory", inv_body, player.cash_balance, player.id)
    except Exception as e:
        return shell("Inventory", f"Error: {e}", player.cash_balance, player.id)

@router.get("/land", response_class=HTMLResponse)
def land(session_token: Optional[str] = Cookie(None), sort: str = "id", order: str = "asc", success: str = "", error: str = ""):
    """Land management view with organized layout, sorting, and explanatory info."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return player
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)
    try:
        from land import get_player_land, TERRAIN_TYPES, PROXIMITY_FEATURES, calculate_player_hoarding_tax, HOARDING_FREE_PLOTS
        from business import BUSINESS_TYPES
        plots = get_player_land(player.id)

        # Calculate hoarding tax for this player
        hoarding_info = calculate_player_hoarding_tax(len(plots))

        # Calculate player's business count for cost multiplier
        from business import Business
        from land import get_db as get_land_db
        land_db = get_land_db()
        owned_businesses_count = land_db.query(Business).filter(Business.owner_id == player.id).count()

        # Fetch active listings owned by this player
        from land_market import LandListing
        from database import SessionLocal as _MainSession
        _lm_db = _MainSession()
        _active_listings = _lm_db.query(LandListing).filter(
            LandListing.seller_id == player.id,
            LandListing.is_active == True,
        ).all()
        _lm_db.close()
        listed_plot_ids = {l.land_plot_id for l in _active_listings}
        listing_id_by_plot = {l.land_plot_id: l.id for l in _active_listings}

        # Sort plots
        def sort_key(p):
            if sort == "terrain": return p.terrain_type
            if sort == "efficiency": return p.efficiency
            if sort == "tax": return p.monthly_tax
            if sort == "status": return (0 if p.occupied_by_business_id else 1)
            if sort == "size": return p.size
            return p.id

        reverse = (order == "desc")
        plots = sorted(plots, key=sort_key, reverse=reverse)

        # Compute portfolio stats
        total_plots = len(plots)
        occupied_count = sum(1 for p in plots if p.occupied_by_business_id)
        vacant_count = total_plots - occupied_count
        total_monthly_tax = sum(p.monthly_tax for p in plots)
        avg_efficiency = (sum(p.efficiency for p in plots) / total_plots) if total_plots else 0

        # Terrain colors for visual grouping
        terrain_colors = {
            "prairie": "#22c55e", "forest": "#16a34a", "desert": "#f59e0b",
            "marsh": "#06b6d4", "mountain": "#94a3b8", "tundra": "#38bdf8",
            "jungle": "#10b981", "savanna": "#eab308", "hills": "#a3e635",
            "island": "#3b82f6", "district_food": "#f97316", "district_hospital": "#ef4444",
            "district_industrial": "#64748b", "district_medical": "#ec4899",
            "district_neighborhood": "#a855f7", "district_transport": "#6366f1",
            "district_utilities": "#0ea5e9", "district_zoo": "#84cc16"
        }

        # Build sort toggle helper
        def sort_link(field, label):
            new_order = "desc" if (sort == field and order == "asc") else "asc"
            arrow = ""
            if sort == field:
                arrow = " ▲" if order == "asc" else " ▼"
            return f'<a href="/land?sort={field}&order={new_order}" style="padding: 6px 12px; font-size: 0.8rem; background: {"#1e293b" if sort == field else "#0f172a"}; color: {"#38bdf8" if sort == field else "#94a3b8"}; border: 1px solid #1e293b; border-radius: 3px; text-decoration: none; white-space: nowrap;">{label}{arrow}</a>'

        land_html = '<a href="/" style="color: #38bdf8;"><- Dashboard</a>'

        _land_success = {"listing_cancelled": "Listing cancelled.", "land_listed": "Plot listed on the market."}
        _land_errors = {"cancel_failed": "Could not cancel — listing may already be inactive.", "listing_failed": "Could not list plot. Ensure it is vacant and not already listed."}
        if success in _land_success:
            land_html += f'<div style="padding:10px 16px; background:#052e16; border:1px solid #16a34a; color:#4ade80; margin:8px 0;">{_land_success[success]}</div>'
        elif error in _land_errors:
            land_html += f'<div style="padding:10px 16px; background:#1a0505; border:1px solid #dc2626; color:#f87171; margin:8px 0;">{_land_errors[error]}</div>'

        # Header with navigation
        land_html += '''
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; margin-bottom: 8px;">
            <h1 style="margin: 0;">Land Portfolio</h1>
            <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                <a href="/land-market" class="btn-blue" style="display: inline-flex; align-items: center; gap: 6px; padding: 8px 16px; text-decoration: none;">Buy Land</a>
                <a href="/districts" class="btn-blue" style="display: inline-flex; align-items: center; gap: 6px; padding: 8px 16px; background: #6366f1; text-decoration: none;">Districts</a>
            </div>
        </div>'''

        # Explainer box
        land_html += '''
        <div style="padding: 12px 16px; background: #0f172a; border-left: 4px solid #38bdf8; margin-bottom: 20px; font-size: 0.85rem; color: #94a3b8; line-height: 1.5;">
            Your land plots generate value through the businesses you build on them.
            <strong style="color: #e5e7eb;">Vacant</strong> plots can host new businesses or be listed for sale on the land market.
            <strong style="color: #e5e7eb;">Efficiency</strong> degrades slowly over time and affects business output.
            <strong style="color: #e5e7eb;">Tax</strong> is charged monthly based on terrain type, size, and proximity features.
            <strong style="color: #dc2626;">Hoarding fee:</strong> owning more than {HOARDING_FREE_PLOTS} plots incurs an escalating hourly fee using Fibonacci-scaled tiers.
        </div>'''

        if total_plots == 0:
            land_html += '''
            <div class="card" style="text-align: center; padding: 40px;">
                <p style="font-size: 1.1rem; color: #94a3b8; margin-bottom: 16px;">You don't own any land yet.</p>
                <a href="/land-market" class="btn-blue" style="padding: 12px 24px; font-size: 1rem; text-decoration: none;">Browse the Land Market</a>
            </div>'''
        else:
            # Portfolio Summary Stats
            land_html += f'''
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-bottom: 20px;">
                <div style="background: #0f172a; border: 1px solid #1e293b; padding: 14px; text-align: center;">
                    <div style="font-size: 1.4rem; font-weight: bold; color: #38bdf8;">{total_plots}</div>
                    <div style="font-size: 0.75rem; color: #64748b; margin-top: 4px;">TOTAL PLOTS</div>
                </div>
                <div style="background: #0f172a; border: 1px solid #1e293b; padding: 14px; text-align: center;">
                    <div style="font-size: 1.4rem; font-weight: bold; color: #ef4444;">{occupied_count}</div>
                    <div style="font-size: 0.75rem; color: #64748b; margin-top: 4px;">OCCUPIED</div>
                </div>
                <div style="background: #0f172a; border: 1px solid #1e293b; padding: 14px; text-align: center;">
                    <div style="font-size: 1.4rem; font-weight: bold; color: #22c55e;">{vacant_count}</div>
                    <div style="font-size: 0.75rem; color: #64748b; margin-top: 4px;">VACANT</div>
                </div>
                <div style="background: #0f172a; border: 1px solid #1e293b; padding: 14px; text-align: center;">
                    <div style="font-size: 1.4rem; font-weight: bold; color: #f59e0b;">{fmt_usd(total_monthly_tax, disp, precision=0)}</div>
                    <div style="font-size: 0.75rem; color: #64748b; margin-top: 4px;">MONTHLY TAX</div>
                </div>
                <div style="background: #0f172a; border: 1px solid #1e293b; padding: 14px; text-align: center;">
                    <div style="font-size: 1.4rem; font-weight: bold; color: #a855f7;">{avg_efficiency:.2f}%</div>
                    <div style="font-size: 0.75rem; color: #64748b; margin-top: 4px;">AVG EFFICIENCY</div>
                </div>
                <div style="background: #0f172a; border: 1px solid {'#dc2626' if hoarding_info['excess_plots'] > 0 else '#1e293b'}; padding: 14px; text-align: center;">
                    <div style="font-size: 1.4rem; font-weight: bold; color: {'#dc2626' if hoarding_info['excess_plots'] > 0 else '#22c55e'};">{fmt_usd(hoarding_info['monthly_total'], disp, precision=0)}</div>
                    <div style="font-size: 0.75rem; color: #64748b; margin-top: 4px;">HOARDING FEE/MO</div>
                </div>
            </div>'''

            # Hoarding tax warning banner
            if hoarding_info["excess_plots"] > 0:
                breakdown_rows = ""
                for item in hoarding_info["breakdown"]:
                    breakdown_rows += f'<tr><td style="padding: 4px 8px; color: #e5e7eb;">Plot #{item["plot_number"]}</td><td style="padding: 4px 8px; color: #f59e0b; text-align: right;">{item["multiplier"]:.1f}x</td><td style="padding: 4px 8px; color: #dc2626; text-align: right;">{fmt_usd(item["monthly_tax"], disp, precision=0)}/mo</td></tr>'

                land_html += f'''
            <div style="padding: 14px 18px; background: linear-gradient(135deg, #1a0505, #0f172a); border: 1px solid #dc2626; border-radius: 4px; margin-bottom: 20px;">
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                    <span style="font-size: 1.1rem; font-weight: bold; color: #dc2626;">Land Hoarding Fee Active</span>
                </div>
                <p style="font-size: 0.85rem; color: #94a3b8; margin: 0 0 10px 0; line-height: 1.5;">
                    You own <strong style="color: #e5e7eb;">{total_plots}</strong> plots — <strong style="color: #dc2626;">{hoarding_info["excess_plots"]}</strong> over the {HOARDING_FREE_PLOTS}-plot allowance.
                    Excess plots incur a Fibonacci-scaled hoarding fee of <strong style="color: #dc2626;">{fmt_usd(hoarding_info["monthly_total"], disp, precision=0)}/mo</strong> ({fmt_usd(hoarding_info["hourly_total"], disp)}/hr), paid each hour.
                    Consider creating <a href="/districts" style="color: #6366f1;">districts</a> to consolidate land.
                </p>
                <details style="cursor: pointer;">
                    <summary style="font-size: 0.8rem; color: #64748b;">Fee breakdown per excess plot</summary>
                    <table style="width: 100%; margin-top: 8px; font-size: 0.8rem; border-collapse: collapse;">
                        <thead><tr style="border-bottom: 1px solid #1e293b;"><th style="padding: 4px 8px; text-align: left; color: #64748b;">Plot</th><th style="padding: 4px 8px; text-align: right; color: #64748b;">Multiplier</th><th style="padding: 4px 8px; text-align: right; color: #64748b;">Fee</th></tr></thead>
                        <tbody>{breakdown_rows}</tbody>
                    </table>
                </details>
            </div>'''

            # Sort controls
            land_html += f'''
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 16px; flex-wrap: wrap;">
                <span style="font-size: 0.8rem; color: #64748b;">Sort by:</span>
                {sort_link("id", "Plot ID")}
                {sort_link("terrain", "Terrain")}
                {sort_link("efficiency", "Efficiency")}
                {sort_link("tax", "Tax")}
                {sort_link("status", "Status")}
                {sort_link("size", "Size")}
            </div>'''

            # Plot cards
            for plot in plots:
                status = 'OCCUPIED' if plot.occupied_by_business_id else 'VACANT'
                status_color = "#ef4444" if plot.occupied_by_business_id else "#22c55e"
                terrain_color = terrain_colors.get(plot.terrain_type, "#64748b")
                terrain_info = TERRAIN_TYPES.get(plot.terrain_type, {})
                terrain_desc = terrain_info.get("description", "")

                # Parse proximity features
                features = plot.proximity_features.split(",") if plot.proximity_features else []
                features_html = ""
                if features:
                    for feat in features:
                        feat = feat.strip()
                        feat_info = PROXIMITY_FEATURES.get(feat, {})
                        feat_desc = feat_info.get("description", feat)
                        features_html += f'<span style="font-size: 0.7rem; padding: 2px 6px; background: #1e293b; border: 1px solid #334155; border-radius: 3px; color: #94a3b8;" title="{feat_desc}">{feat.replace("_", " ").title()}</span>'

                # Efficiency color
                eff = plot.efficiency
                if eff >= 90: eff_color = "#22c55e"
                elif eff >= 70: eff_color = "#eab308"
                elif eff >= 50: eff_color = "#f59e0b"
                else: eff_color = "#ef4444"

                # Efficiency bar width
                eff_width = min(100, max(0, eff))

                is_listed = plot.id in listed_plot_ids
                listing_id_for_plot = listing_id_by_plot.get(plot.id)
                listed_badge = '<span class="badge" style="background: #f59e0b; color: #020617;">LISTED</span>' if is_listed else ""

                land_html += f'''
                <div class="card" style="border-left: 4px solid {terrain_color}; margin-bottom: 12px;">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px;">
                        <div style="flex: 1; min-width: 250px;">
                            <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                                <h3 style="margin: 0;">Plot #{plot.id}</h3>
                                <span class="badge" style="background: {status_color}; color: #020617;">{status}</span>
                                {listed_badge}
                                <span class="badge" style="background: {terrain_color}22; color: {terrain_color}; border: 1px solid {terrain_color}44;">{plot.terrain_type.replace("_", " ").title()}</span>
                            </div>
                            <p style="color: #64748b; font-size: 0.8rem; margin: 4px 0;">{terrain_desc}</p>

                            <div style="display: flex; gap: 16px; flex-wrap: wrap; margin-top: 8px; font-size: 0.85rem;">
                                <div>
                                    <span style="color: #64748b;">Size:</span>
                                    <span style="color: #e5e7eb;">{plot.size:.1f}</span>
                                </div>
                                <div>
                                    <span style="color: #64748b;">Tax:</span>
                                    <span style="color: #f59e0b;">{fmt_usd(plot.monthly_tax, disp)}/mo</span>
                                </div>
                            </div>

                            <div style="margin-top: 8px;">
                                <div style="display: flex; align-items: center; gap: 8px;">
                                    <span style="font-size: 0.8rem; color: #64748b;">Efficiency:</span>
                                    <span style="font-size: 0.85rem; color: {eff_color}; font-weight: bold;">{eff:.3f}%</span>
                                </div>
                                <div style="background: #020617; height: 6px; border-radius: 3px; margin-top: 4px; width: 200px;">
                                    <div style="background: {eff_color}; height: 6px; border-radius: 3px; width: {eff_width}%;"></div>
                                </div>
                            </div>'''

                if features:
                    land_html += f'''
                            <div style="display: flex; gap: 6px; flex-wrap: wrap; margin-top: 8px;">
                                <span style="font-size: 0.75rem; color: #64748b;">Features:</span>
                                {features_html}
                            </div>'''

                land_html += '</div>'

                # Actions column
                if not plot.occupied_by_business_id:
                    land_html += '<div style="display: flex; flex-direction: column; gap: 10px; min-width: 220px;">'
                    if is_listed:
                        # Plot is listed — show cancel button; no building allowed while listed
                        land_html += f'''
                            <div style="font-size: 0.8rem; color: #f59e0b; margin-bottom: 4px;">Listed for sale on the market.</div>
                            <form action="/api/land-market/cancel-listing" method="post">
                                <input type="hidden" name="listing_id" value="{listing_id_for_plot}">
                                <button type="submit" class="btn-red" style="width: 100%;">Cancel Listing</button>
                            </form>
                            <a href="/land-market?tab=listings" class="btn-blue" style="text-align:center; padding: 8px 12px; font-size: 0.85rem; text-decoration: none;">View on Market</a>'''
                    else:
                        # Vacant and not listed — show build + list forms
                        land_html += f'''
                            <form action="/api/business/create" method="post" style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
                                <input type="hidden" name="land_plot_id" value="{plot.id}">
                                <select name="business_type" required style="flex: 1; min-width: 140px;">
                                    <option value="">Build Business...</option>'''

                        for btype, config in sorted(BUSINESS_TYPES.items(), key=lambda x: x[1].get("name", x[0])):
                            if plot.terrain_type in config.get("allowed_terrain", []):
                                base_cost = config.get("startup_cost", 2500.0)
                                multiplier = max(1.25, owned_businesses_count)
                                actual_cost = base_cost * multiplier
                                business_name = config.get("name", btype)
                                land_html += f'<option value="{btype}">{business_name} ({fmt_usd(actual_cost, disp, precision=0)})</option>'

                        land_html += f'''</select><button type="submit" class="btn-blue">Build</button>
                            </form>
                            <form action="/api/land-market/list-land" method="post" style="display: flex; gap: 8px; align-items: center;">
                                <input type="hidden" name="land_plot_id" value="{plot.id}">
                                <input type="number" name="asking_price" step="0.01" placeholder="Asking ({disp['code']})" style="width: 110px;" required>
                                <button type="submit" class="btn-orange">List for Sale</button>
                            </form>'''
                    land_html += '</div>'
                else:
                    # Show which business occupies this plot
                    biz = land_db.query(Business).filter(Business.id == plot.occupied_by_business_id).first()
                    biz_name = biz.business_type.replace("_", " ").title() if biz else f"Business #{plot.occupied_by_business_id}"
                    land_html += f'''
                        <div style="min-width: 180px; text-align: right;">
                            <div style="font-size: 0.8rem; color: #64748b;">Business</div>
                            <div style="font-size: 0.9rem; color: #e5e7eb; font-weight: 500;">{biz_name}</div>
                        </div>'''

                land_html += '</div></div>'

        land_db.close()

        # Inject tutorial overlay for land-relevant steps
        try:
            from tutorial_ux import get_tutorial_overlay_html
            tut_overlay = get_tutorial_overlay_html(player, "land")
            if tut_overlay:
                land_html = tut_overlay + land_html
        except Exception:
            pass

        return shell("Land", land_html, player.cash_balance, player.id)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return shell("Land", f"Error: {e}", player.cash_balance, player.id)

@router.get("/land-market", response_class=HTMLResponse)
def land_market_page(session_token: Optional[str] = Cookie(None), sort: str = "price", order: str = "asc", terrain: str = "all", tab: str = "auctions", success: str = "", error: str = ""):
    """Land market view - government auctions and player listings with search, sort, and filter."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return player
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)

    try:
        from land_market import (get_active_auctions, get_active_listings, get_land_bank_plots,
                                  get_recent_sales, get_player_buy_orders, get_all_active_buy_orders)
        from land import get_land_plot, TERRAIN_TYPES, PROXIMITY_FEATURES

        auctions = get_active_auctions()
        listings = get_active_listings()
        bank_plots = get_land_bank_plots()
        recent_sales = get_recent_sales(limit=8)
        my_buy_orders = get_player_buy_orders(player.id)
        all_buy_orders = get_all_active_buy_orders()

        # Terrain colors
        terrain_colors = {
            "prairie": "#22c55e", "forest": "#16a34a", "desert": "#f59e0b",
            "marsh": "#06b6d4", "mountain": "#94a3b8", "tundra": "#38bdf8",
            "jungle": "#10b981", "savanna": "#eab308", "hills": "#a3e635",
            "island": "#3b82f6"
        }

        # Gather all plots for terrain filter tabs
        all_terrains = set()
        auction_plots = {}
        for a in auctions:
            p = get_land_plot(a.land_plot_id)
            if p:
                auction_plots[a.id] = p
                all_terrains.add(p.terrain_type)
        listing_plots = {}
        for l in listings:
            p = get_land_plot(l.land_plot_id)
            if p:
                listing_plots[l.id] = p
                all_terrains.add(p.terrain_type)

        # Market stats
        total_auctions = len(auctions)
        total_listings = len(listings)
        total_available = total_auctions + total_listings
        avg_auction_price = (sum(a.current_price for a in auctions) / total_auctions) if total_auctions else 0
        avg_listing_price = (sum(l.asking_price for l in listings) / total_listings) if total_listings else 0

        market_html = '<a href="/" style="color: #38bdf8;"><- Dashboard</a>'

        if success:
            _success_msgs = {
                "listing_cancelled": "Listing cancelled successfully.",
                "listing_bought": "Purchase complete — the plot is now yours.",
                "auction_bought": "Auction purchase complete — the plot is now yours.",
                "buy_order_placed": "Buy order placed. It will execute automatically when a matching listing appears.",
                "buy_order_cancelled": "Buy order cancelled.",
                "land_listed": "Plot listed on the market.",
            }
            market_html += f'<div style="padding: 10px 16px; background: #052e16; border: 1px solid #16a34a; color: #4ade80; margin-bottom: 12px;">{_success_msgs.get(success, success)}</div>'
        if error:
            _error_msgs = {
                "cancel_failed": "Could not cancel listing — it may already be inactive.",
                "purchase_failed": "Purchase failed — the plot may have been sold or is no longer available.",
                "buy_order_failed": "Could not place buy order. Check that your price is valid.",
                "listing_failed": "Could not create listing.",
            }
            market_html += f'<div style="padding: 10px 16px; background: #1a0505; border: 1px solid #dc2626; color: #f87171; margin-bottom: 12px;">{_error_msgs.get(error, error)}</div>'

        # Header
        market_html += '''
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; margin-bottom: 8px;">
            <h1 style="margin: 0;">Land Market</h1>
            <a href="/land" class="btn-blue" style="display: inline-flex; align-items: center; gap: 6px; padding: 8px 16px; text-decoration: none;">Your Land Portfolio</a>
        </div>'''

        # Explainer
        market_html += '''
        <div style="padding: 12px 16px; background: #0f172a; border-left: 4px solid #f59e0b; margin-bottom: 20px; font-size: 0.85rem; color: #94a3b8; line-height: 1.5;">
            <strong style="color: #f59e0b;">Government Auctions</strong> use a Dutch auction system &mdash; the price starts high and drops over time until someone buys.
            Wait for a lower price, but risk losing the plot to another buyer.
            <strong style="color: #a855f7;">Player Listings</strong> are fixed-price sales from other players.
            Land varies by <strong style="color: #e5e7eb;">terrain type</strong> (which businesses can operate) and
            <strong style="color: #e5e7eb;">proximity features</strong> (bonuses like coastal access or urban demand).
        </div>'''

        # Market stats summary
        market_html += f'''
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-bottom: 20px;">
            <div style="background: #0f172a; border: 1px solid #1e293b; padding: 14px; text-align: center;">
                <div style="font-size: 1.4rem; font-weight: bold; color: #38bdf8;">{total_available}</div>
                <div style="font-size: 0.75rem; color: #64748b; margin-top: 4px;">PLOTS FOR SALE</div>
            </div>
            <div style="background: #0f172a; border: 1px solid #1e293b; padding: 14px; text-align: center;">
                <div style="font-size: 1.4rem; font-weight: bold; color: #f59e0b;">{total_auctions}</div>
                <div style="font-size: 0.75rem; color: #64748b; margin-top: 4px;">GOV AUCTIONS</div>
            </div>
            <div style="background: #0f172a; border: 1px solid #1e293b; padding: 14px; text-align: center;">
                <div style="font-size: 1.4rem; font-weight: bold; color: #a855f7;">{total_listings}</div>
                <div style="font-size: 0.75rem; color: #64748b; margin-top: 4px;">PLAYER LISTINGS</div>
            </div>
            <div style="background: #0f172a; border: 1px solid #1e293b; padding: 14px; text-align: center;">
                <div style="font-size: 1.4rem; font-weight: bold; color: #22c55e;">{fmt_usd(avg_auction_price, disp, precision=0)}</div>
                <div style="font-size: 0.75rem; color: #64748b; margin-top: 4px;">AVG AUCTION PRICE</div>
            </div>
            <div style="background: #0f172a; border: 1px solid #1e293b; padding: 14px; text-align: center;">
                <div style="font-size: 1.4rem; font-weight: bold; color: #10b981;">{len(bank_plots)}</div>
                <div style="font-size: 0.75rem; color: #64748b; margin-top: 4px;">IN LAND BANK</div>
            </div>
        </div>'''

        # Tab navigation (Auctions / Player Listings)
        def tab_style(t):
            if tab == t:
                return "padding: 10px 20px; font-size: 0.9rem; background: #1e293b; color: #e5e7eb; border: 1px solid #334155; border-bottom: 2px solid #38bdf8; text-decoration: none; font-weight: bold;"
            return "padding: 10px 20px; font-size: 0.9rem; background: #0f172a; color: #64748b; border: 1px solid #1e293b; text-decoration: none;"

        market_html += f'''
        <div style="display: flex; gap: 4px; margin-bottom: 16px; flex-wrap: wrap;">
            <a href="/land-market?tab=auctions&sort={sort}&order={order}&terrain={terrain}" style="{tab_style("auctions")}">Government Auctions ({total_auctions})</a>
            <a href="/land-market?tab=listings&sort={sort}&order={order}&terrain={terrain}" style="{tab_style("listings")}">Player Listings ({total_listings})</a>
            <a href="/land-market?tab=orders&sort={sort}&order={order}&terrain={terrain}" style="{tab_style("orders")}">Buy Orders ({len(all_buy_orders)})</a>
            <a href="/land-market?tab=history&sort={sort}&order={order}&terrain={terrain}" style="{tab_style("history")}">Recent Sales</a>
        </div>'''

        # Terrain filter tabs
        if all_terrains:
            market_html += '<div style="margin-bottom: 16px;"><span style="font-size: 0.8rem; color: #64748b; margin-right: 8px;">Filter terrain:</span>'
            all_active = "background: #1e293b; color: #38bdf8; border: 1px solid #38bdf8;" if terrain == "all" else "background: #0f172a; color: #94a3b8; border: 1px solid #1e293b;"
            market_html += f'<a href="/land-market?tab={tab}&sort={sort}&order={order}&terrain=all" style="padding: 4px 10px; font-size: 0.8rem; {all_active} border-radius: 3px; text-decoration: none; display: inline-block; margin: 2px;">All</a>'
            for t in sorted(all_terrains):
                if t.startswith("district_"):
                    continue
                t_color = terrain_colors.get(t, "#64748b")
                is_active = terrain == t
                bg = f"{t_color}" if is_active else "#0f172a"
                fg = "#020617" if is_active else t_color
                border = f"1px solid {t_color}"
                market_html += f'<a href="/land-market?tab={tab}&sort={sort}&order={order}&terrain={t}" style="padding: 4px 10px; font-size: 0.8rem; background: {bg}; color: {fg}; border: {border}; border-radius: 3px; text-decoration: none; display: inline-block; margin: 2px;">{t.replace("_", " ").title()}</a>'
            market_html += '</div>'

        # Sort controls
        def sort_link(field, label):
            new_order = "desc" if (sort == field and order == "asc") else "asc"
            arrow = ""
            if sort == field:
                arrow = " ▲" if order == "asc" else " ▼"
            active = sort == field
            return f'<a href="/land-market?tab={tab}&sort={field}&order={new_order}&terrain={terrain}" style="padding: 6px 12px; font-size: 0.8rem; background: {"#1e293b" if active else "#0f172a"}; color: {"#38bdf8" if active else "#94a3b8"}; border: 1px solid #1e293b; border-radius: 3px; text-decoration: none; white-space: nowrap;">{label}{arrow}</a>'

        if tab in ("auctions", "listings"):
            market_html += f'''
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 16px; flex-wrap: wrap;">
                <span style="font-size: 0.8rem; color: #64748b;">Sort by:</span>
                {sort_link("price", "Price")}
                {sort_link("terrain", "Terrain")}
                {sort_link("efficiency", "Efficiency")}
                {sort_link("tax", "Tax")}
                {sort_link("size", "Size")}
                {sort_link("time", "Time") if tab == "auctions" else ""}
            </div>'''

        # ===== AUCTIONS TAB =====
        if tab == "auctions":
            if not auctions:
                market_html += '''
                <div class="card" style="text-align: center; padding: 30px;">
                    <p style="color: #94a3b8;">No active government auctions at this time.</p>
                    <p style="font-size: 0.8rem; color: #64748b;">New auctions appear as the economy grows. Check back soon.</p>
                </div>'''
            else:
                # Build sortable auction data
                auction_data = []
                for auction in auctions:
                    plot = auction_plots.get(auction.id)
                    if not plot:
                        continue
                    if terrain != "all" and plot.terrain_type != terrain:
                        continue
                    auction_data.append((auction, plot))

                # Sort
                def auction_sort_key(item):
                    a, p = item
                    if sort == "price": return a.current_price
                    if sort == "terrain": return p.terrain_type
                    if sort == "efficiency": return p.efficiency
                    if sort == "tax": return p.monthly_tax
                    if sort == "size": return p.size
                    if sort == "time": return a.end_time.timestamp() if a.end_time else 0
                    return a.current_price
                auction_data.sort(key=auction_sort_key, reverse=(order == "desc"))

                if not auction_data:
                    market_html += f'<p style="color: #64748b;">No auctions match the "{terrain}" terrain filter.</p>'

                for auction, plot in auction_data:
                    time_remaining = auction.end_time - datetime.utcnow()
                    total_secs = max(0, time_remaining.total_seconds())
                    hours_left = int(total_secs / 3600)
                    minutes_left = int((total_secs % 3600) / 60)
                    price_drop_pct = ((auction.starting_price - auction.current_price) / auction.starting_price * 100) if auction.starting_price > 0 else 0
                    terrain_color = terrain_colors.get(plot.terrain_type, "#64748b")
                    terrain_info = TERRAIN_TYPES.get(plot.terrain_type, {})

                    # Parse proximity features
                    features = plot.proximity_features.split(",") if plot.proximity_features else []
                    features_html = ""
                    for feat in features:
                        feat = feat.strip()
                        if not feat:
                            continue
                        feat_info = PROXIMITY_FEATURES.get(feat, {})
                        feat_desc = feat_info.get("description", feat)
                        features_html += f'<span style="font-size: 0.7rem; padding: 2px 6px; background: #1e293b; border: 1px solid #334155; border-radius: 3px; color: #94a3b8;" title="{feat_desc}">{feat.replace("_", " ").title()}</span> '

                    # Urgency color for time
                    if hours_left < 1:
                        time_color = "#ef4444"
                    elif hours_left < 6:
                        time_color = "#f59e0b"
                    else:
                        time_color = "#64748b"

                    # Price progress bar
                    price_range = auction.starting_price - auction.minimum_price
                    price_progress = ((auction.starting_price - auction.current_price) / price_range * 100) if price_range > 0 else 0

                    market_html += f'''
                    <div class="card" style="border-left: 4px solid {terrain_color}; margin-bottom: 12px;">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px;">
                            <div style="flex: 1; min-width: 280px;">
                                <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                                    <h3 style="margin: 0;">Plot #{plot.id}</h3>
                                    <span class="badge" style="background: #f59e0b; color: #020617;">AUCTION</span>
                                    <span class="badge" style="background: {terrain_color}22; color: {terrain_color}; border: 1px solid {terrain_color}44;">{plot.terrain_type.replace("_", " ").title()}</span>
                                </div>
                                <p style="color: #64748b; font-size: 0.8rem; margin: 4px 0;">{terrain_info.get("description", "")}</p>

                                <div style="display: flex; gap: 16px; flex-wrap: wrap; margin-top: 8px; font-size: 0.85rem;">
                                    <div><span style="color: #64748b;">Size:</span> <span style="color: #e5e7eb;">{plot.size:.1f}</span></div>
                                    <div><span style="color: #64748b;">Efficiency:</span> <span style="color: #22c55e;">{plot.efficiency:.2f}%</span></div>
                                    <div><span style="color: #64748b;">Tax:</span> <span style="color: #f59e0b;">{fmt_usd(plot.monthly_tax, disp)}/mo</span></div>
                                </div>'''

                    if features_html:
                        market_html += f'''
                                <div style="display: flex; gap: 6px; flex-wrap: wrap; margin-top: 8px;">
                                    <span style="font-size: 0.75rem; color: #64748b;">Features:</span>
                                    {features_html}
                                </div>'''

                    market_html += f'''
                                <div style="margin-top: 12px; padding: 10px; background: #020617; border-radius: 4px;">
                                    <div style="display: flex; justify-content: space-between; font-size: 0.8rem; margin-bottom: 6px;">
                                        <span style="color: #ef4444;">Start: {fmt_usd(auction.starting_price, disp, precision=0)}</span>
                                        <span style="color: #22c55e; font-weight: bold;">Now: {fmt_usd(auction.current_price, disp, precision=0)}</span>
                                        <span style="color: #64748b;">Floor: {fmt_usd(auction.minimum_price, disp, precision=0)}</span>
                                    </div>
                                    <div style="background: #1e293b; height: 6px; border-radius: 3px;">
                                        <div style="background: linear-gradient(90deg, #ef4444, #22c55e); height: 6px; border-radius: 3px; width: {min(100, price_progress):.0f}%;"></div>
                                    </div>
                                    <div style="display: flex; justify-content: space-between; margin-top: 6px; font-size: 0.75rem;">
                                        <span style="color: #64748b;">Dropped {price_drop_pct:.1f}%</span>
                                        <span style="color: {time_color};">{hours_left}h {minutes_left}m remaining</span>
                                    </div>
                                </div>
                            </div>
                            <div style="display: flex; flex-direction: column; align-items: center; gap: 8px; min-width: 120px;">
                                <div style="text-align: center;">
                                    <div style="font-size: 1.3rem; font-weight: bold; color: #22c55e;">{fmt_usd(auction.current_price, disp, precision=0)}</div>
                                    <div style="font-size: 0.7rem; color: #64748b;">current price</div>
                                </div>
                                <form action="/api/land-market/buy-auction" method="post">
                                    <input type="hidden" name="auction_id" value="{auction.id}">
                                    <button type="submit" class="btn-blue" style="padding: 10px 20px; font-size: 0.9rem;" onclick="return confirm('Buy Plot #{plot.id} for {fmt_usd(auction.current_price, disp)}?')">
                                        Buy Now
                                    </button>
                                </form>
                            </div>
                        </div>
                    </div>'''

        # ===== PLAYER LISTINGS TAB =====
        elif tab == "listings":
            if not listings:
                market_html += '''
                <div class="card" style="text-align: center; padding: 30px;">
                    <p style="color: #94a3b8;">No player listings available.</p>
                    <p style="font-size: 0.8rem; color: #64748b;">Players can list vacant land for sale from their Land Portfolio page.</p>
                </div>'''
            else:
                from auth import get_db as get_auth_db, Player as AuthPlayer

                # Build sortable listing data
                listing_data = []
                for listing in listings:
                    plot = listing_plots.get(listing.id)
                    if not plot:
                        continue
                    if terrain != "all" and plot.terrain_type != terrain:
                        continue
                    listing_data.append((listing, plot))

                # Sort
                def listing_sort_key(item):
                    l, p = item
                    if sort == "price": return l.asking_price
                    if sort == "terrain": return p.terrain_type
                    if sort == "efficiency": return p.efficiency
                    if sort == "tax": return p.monthly_tax
                    if sort == "size": return p.size
                    if sort == "time": return l.listed_at.timestamp() if l.listed_at else 0
                    return l.asking_price
                listing_data.sort(key=listing_sort_key, reverse=(order == "desc"))

                if not listing_data:
                    market_html += f'<p style="color: #64748b;">No listings match the "{terrain}" terrain filter.</p>'

                for listing, plot in listing_data:
                    auth_db = get_auth_db()
                    seller = auth_db.query(AuthPlayer).filter(AuthPlayer.id == listing.seller_id).first()
                    auth_db.close()
                    seller_name = seller.business_name if seller else f"Player {listing.seller_id}"
                    is_own_listing = (listing.seller_id == player.id)

                    terrain_color = terrain_colors.get(plot.terrain_type, "#64748b")
                    terrain_info = TERRAIN_TYPES.get(plot.terrain_type, {})

                    features = plot.proximity_features.split(",") if plot.proximity_features else []
                    features_html = ""
                    for feat in features:
                        feat = feat.strip()
                        if not feat:
                            continue
                        feat_info = PROXIMITY_FEATURES.get(feat, {})
                        feat_desc = feat_info.get("description", feat)
                        features_html += f'<span style="font-size: 0.7rem; padding: 2px 6px; background: #1e293b; border: 1px solid #334155; border-radius: 3px; color: #94a3b8;" title="{feat_desc}">{feat.replace("_", " ").title()}</span> '

                    border_color = "#38bdf8" if is_own_listing else terrain_color
                    own_badge = '<span class="badge" style="background: #38bdf8; color: #020617;">YOUR LISTING</span>' if is_own_listing else ""

                    market_html += f'''
                    <div class="card" style="border-left: 4px solid {border_color}; margin-bottom: 12px;">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px;">
                            <div style="flex: 1; min-width: 280px;">
                                <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                                    <h3 style="margin: 0;">Plot #{plot.id}</h3>
                                    {own_badge}
                                    <span class="badge" style="background: {terrain_color}22; color: {terrain_color}; border: 1px solid {terrain_color}44;">{plot.terrain_type.replace("_", " ").title()}</span>
                                </div>
                                <p style="color: #64748b; font-size: 0.8rem; margin: 4px 0;">{terrain_info.get("description", "")}</p>

                                <div style="display: flex; gap: 16px; flex-wrap: wrap; margin-top: 8px; font-size: 0.85rem;">
                                    <div><span style="color: #64748b;">Size:</span> <span style="color: #e5e7eb;">{plot.size:.1f}</span></div>
                                    <div><span style="color: #64748b;">Efficiency:</span> <span style="color: #22c55e;">{plot.efficiency:.2f}%</span></div>
                                    <div><span style="color: #64748b;">Tax:</span> <span style="color: #f59e0b;">{fmt_usd(plot.monthly_tax, disp)}/mo</span></div>
                                    <div><span style="color: #64748b;">Seller:</span> <span style="color: #94a3b8;">{seller_name}</span></div>
                                </div>'''

                    if features_html:
                        market_html += f'''
                                <div style="display: flex; gap: 6px; flex-wrap: wrap; margin-top: 8px;">
                                    <span style="font-size: 0.75rem; color: #64748b;">Features:</span>
                                    {features_html}
                                </div>'''

                    market_html += '''
                            </div>
                            <div style="display: flex; flex-direction: column; align-items: center; gap: 8px; min-width: 120px;">'''

                    market_html += f'''
                                <div style="text-align: center;">
                                    <div style="font-size: 1.3rem; font-weight: bold; color: #22c55e;">{fmt_usd(listing.asking_price, disp, precision=0)}</div>
                                    <div style="font-size: 0.7rem; color: #64748b;">asking price</div>
                                </div>'''

                    if is_own_listing:
                        market_html += f'''
                                <form action="/api/land-market/cancel-listing" method="post">
                                    <input type="hidden" name="listing_id" value="{listing.id}">
                                    <button type="submit" class="btn-red" style="padding: 10px 20px; font-size: 0.9rem;">Cancel</button>
                                </form>'''
                    else:
                        market_html += f'''
                                <form action="/api/land-market/buy-listing" method="post">
                                    <input type="hidden" name="listing_id" value="{listing.id}">
                                    <button type="submit" class="btn-blue" style="padding: 10px 20px; font-size: 0.9rem;" onclick="return confirm('Buy Plot #{plot.id} for {fmt_usd(listing.asking_price, disp)}?')">Buy Now</button>
                                </form>'''

                    market_html += '</div></div></div>'

        # ===== BUY ORDERS TAB =====
        elif tab == "orders":
            market_html += '''
            <div style="padding: 10px 16px; background: #0f172a; border-left: 4px solid #38bdf8; margin-bottom: 16px; font-size: 0.85rem; color: #94a3b8;">
                <strong style="color: #38bdf8;">Limit Buy Orders</strong> — place a standing bid at your maximum price.
                When a seller lists land at or below your max price (and terrain matches if filtered), the purchase executes automatically.
            </div>'''

            # Place new buy order form — build options dynamically from land constants
            _terrain_opts = "".join(
                f'<option value="{t}">{t.replace("_"," ").title()}</option>'
                for t in sorted(TERRAIN_TYPES.keys())
                if not t.startswith("district_")
            )
            _prox_opts = "".join(
                f'<option value="{p}">{PROXIMITY_FEATURES[p].get("name", p.replace("_"," ").title())}</option>'
                for p in sorted(PROXIMITY_FEATURES.keys())
            )
            market_html += f'''
            <div class="card" style="margin-bottom: 20px;">
                <h3 style="margin: 0 0 12px 0;">Place a Buy Order</h3>
                <form action="/api/land-market/buy-order" method="post" style="display: flex; gap: 10px; flex-wrap: wrap; align-items: flex-end;">
                    <div>
                        <label style="display:block; font-size:0.8rem; color:#64748b; margin-bottom:4px;">Max Price ({disp["code"]})</label>
                        <input type="number" name="max_price" step="0.01" min="1" placeholder="e.g. 50000" required
                               style="width:140px; background:#020617; border:1px solid #334155; color:#e5e7eb; padding:8px;">
                    </div>
                    <div>
                        <label style="display:block; font-size:0.8rem; color:#64748b; margin-bottom:4px;">Terrain (optional)</label>
                        <select name="terrain" style="background:#020617; border:1px solid #334155; color:#e5e7eb; padding:8px;">
                            <option value="">Any terrain</option>
                            {_terrain_opts}
                        </select>
                    </div>
                    <div>
                        <label style="display:block; font-size:0.8rem; color:#64748b; margin-bottom:4px;">Proximity feature (optional)</label>
                        <select name="proximity" style="background:#020617; border:1px solid #334155; color:#e5e7eb; padding:8px;">
                            <option value="">Any proximity</option>
                            {_prox_opts}
                        </select>
                    </div>
                    <button type="submit" class="btn-blue" style="padding: 8px 20px;">Place Order</button>
                </form>
            </div>'''

            # My active buy orders
            if my_buy_orders:
                market_html += '<h3 style="color:#e5e7eb; margin-bottom:10px;">Your Active Buy Orders</h3>'
                for bo in my_buy_orders:
                    terrain_label  = bo.terrain.replace("_"," ").title() if bo.terrain else "Any"
                    prox_label     = PROXIMITY_FEATURES.get(bo.proximity, {}).get("name", bo.proximity.replace("_"," ").title()) if bo.proximity else "Any"
                    placed = bo.created_at.strftime("%b %d, %H:%M") if bo.created_at else ""
                    market_html += f'''
                    <div class="card" style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px; margin-bottom:8px; border-left:4px solid #38bdf8;">
                        <div>
                            <div style="font-size:0.85rem; color:#64748b; margin-bottom:4px;">Max price</div>
                            <div style="font-size:1.2rem; font-weight:bold; color:#38bdf8;">{fmt_usd(bo.max_price, disp, precision=0)}</div>
                            <div style="font-size:0.75rem; color:#64748b; margin-top:4px;">
                                Terrain: {terrain_label} &nbsp;·&nbsp; Proximity: {prox_label} &nbsp;·&nbsp; Placed {placed}
                            </div>
                        </div>
                        <form action="/api/land-market/cancel-buy-order" method="post">
                            <input type="hidden" name="order_id" value="{bo.id}">
                            <button type="submit" class="btn-red" style="padding:8px 16px;">Cancel</button>
                        </form>
                    </div>'''

            # All market buy orders (read-only depth view)
            other_orders = [o for o in all_buy_orders if o.buyer_id != player.id]
            if other_orders:
                market_html += '<h3 style="color:#e5e7eb; margin:20px 0 10px 0;">Open Market Buy Orders</h3>'
                market_html += '''
                <div class="card" style="padding:0; overflow-x:auto;">
                    <table style="width:100%; border-collapse:collapse; font-size:0.85rem;">
                        <thead><tr style="border-bottom:1px solid #1e293b; color:#64748b;">
                            <th style="padding:10px 12px; text-align:left;">Max Price</th>
                            <th style="padding:10px 12px; text-align:left;">Terrain</th>
                            <th style="padding:10px 12px; text-align:left;">Proximity</th>
                            <th style="padding:10px 12px; text-align:right;">Placed</th>
                        </tr></thead><tbody>'''
                for o in other_orders:
                    terrain_label = o.terrain.replace("_"," ").title() if o.terrain else "Any"
                    prox_label    = PROXIMITY_FEATURES.get(o.proximity, {}).get("name", o.proximity.replace("_"," ").title()) if o.proximity else "Any"
                    placed = o.created_at.strftime("%b %d, %H:%M") if o.created_at else ""
                    market_html += f'''
                        <tr style="border-bottom:1px solid #0f172a;">
                            <td style="padding:10px 12px; color:#38bdf8; font-weight:bold;">{fmt_usd(o.max_price, disp, precision=0)}</td>
                            <td style="padding:10px 12px; color:#94a3b8;">{terrain_label}</td>
                            <td style="padding:10px 12px; color:#94a3b8;">{prox_label}</td>
                            <td style="padding:10px 12px; text-align:right; color:#64748b;">{placed}</td>
                        </tr>'''
                market_html += '</tbody></table></div>'

            if not my_buy_orders and not other_orders:
                market_html += '''
                <div class="card" style="text-align:center; padding:30px;">
                    <p style="color:#94a3b8;">No active buy orders. Place one above to get notified when matching land is listed.</p>
                </div>'''

        # ===== RECENT SALES TAB =====
        elif tab == "history":
            market_html += '''
            <div style="padding: 10px 16px; background: #0f172a; border-left: 4px solid #64748b; margin-bottom: 16px; font-size: 0.85rem; color: #94a3b8;">
                Recent land sales help you gauge fair market prices. Government auction sales and player-to-player trades are both shown.
            </div>'''

            if not recent_sales:
                market_html += '''
                <div class="card" style="text-align: center; padding: 30px;">
                    <p style="color: #94a3b8;">No land sales recorded yet.</p>
                </div>'''
            else:
                # Table header
                market_html += '''
                <div class="card" style="padding: 0; overflow-x: auto;">
                    <table style="width: 100%; border-collapse: collapse; font-size: 0.85rem;">
                        <thead>
                            <tr style="border-bottom: 1px solid #1e293b; color: #64748b;">
                                <th style="padding: 12px; text-align: left;">Plot</th>
                                <th style="padding: 12px; text-align: left;">Terrain</th>
                                <th style="padding: 12px; text-align: left;">Type</th>
                                <th style="padding: 12px; text-align: right;">Price</th>
                                <th style="padding: 12px; text-align: right;">Date</th>
                            </tr>
                        </thead>
                        <tbody>'''

                from auth import get_db as get_auth_db, Player as AuthPlayer
                for sale in recent_sales:
                    plot = get_land_plot(sale.land_plot_id)
                    terrain_name = plot.terrain_type.replace("_", " ").title() if plot else "Unknown"
                    t_color = terrain_colors.get(plot.terrain_type, "#64748b") if plot else "#64748b"
                    sale_type_badge = '<span style="color: #f59e0b;">Auction</span>' if sale.sale_type == "government" else '<span style="color: #a855f7;">Player</span>'
                    sale_date = sale.sold_at.strftime("%b %d, %H:%M") if sale.sold_at else "N/A"

                    market_html += f'''
                            <tr style="border-bottom: 1px solid #0f172a;">
                                <td style="padding: 10px 12px; color: #e5e7eb;">#{sale.land_plot_id}</td>
                                <td style="padding: 10px 12px; color: {t_color};">{terrain_name}</td>
                                <td style="padding: 10px 12px;">{sale_type_badge}</td>
                                <td style="padding: 10px 12px; text-align: right; color: #22c55e; font-weight: bold;">{fmt_usd(sale.price, disp, precision=0)}</td>
                                <td style="padding: 10px 12px; text-align: right; color: #64748b;">{sale_date}</td>
                            </tr>'''

                market_html += '</tbody></table></div>'

        # Land Bank status (always shown at bottom)
        if bank_plots:
            market_html += f'''
            <div style="margin-top: 24px; padding: 12px 16px; background: #0f172a; border: 1px solid #1e293b;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div style="font-size: 0.85rem; color: #64748b; font-weight: bold;">Land Bank</div>
                        <div style="font-size: 0.8rem; color: #94a3b8; margin-top: 4px;">{len(bank_plots)} unsold plot(s) awaiting re-auction. These will automatically appear as new auctions soon.</div>
                    </div>
                </div>
            </div>'''

        # Inject tutorial overlay for land-market step
        try:
            from tutorial_ux import get_tutorial_overlay_html
            tut_overlay = get_tutorial_overlay_html(player, "land_market")
            if tut_overlay:
                market_html = tut_overlay + market_html
        except Exception:
            pass

        return shell("Land Market", market_html, player.cash_balance, player.id)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return shell("Land Market", f"Error loading land market: {e}", player.cash_balance, player.id)

def _build_currency_legend_panel(banks_data: list) -> str:
    """Sidebar card: flag, code, and exchange rate for every active reserve bank."""
    rows = '<div style="display:flex;align-items:center;gap:6px;padding:4px 0;border-bottom:1px solid #1e293b;font-size:0.8rem;color:#64748b;font-weight:bold;"><span style="width:24px;">Flag</span><span style="flex:1;">Currency</span><span>Rate (USD)</span></div>'
    # USD row first
    rows += '<div style="display:flex;align-items:center;gap:6px;padding:4px 0;font-size:0.82rem;"><span style="width:24px;">🇺🇸</span><span style="flex:1;color:#e5e7eb;">USD</span><span style="color:#22c55e;">base</span></div>'
    for b in sorted(banks_data, key=lambda x: x["code"]):
        rate = b.get("usd_per_unit", 0)
        rate_str = f"${rate:,.4f}" if rate < 1 else f"${rate:,.2f}"
        rows += f'<div style="display:flex;align-items:center;gap:6px;padding:4px 0;font-size:0.82rem;"><span style="width:24px;">{b["flag"]}</span><span style="flex:1;color:#e5e7eb;">{b["code"]}</span><span style="color:#94a3b8;">{rate_str}</span></div>'
    return f'<div class="card" style="margin-top:16px;"><h3 style="margin-bottom:10px;">Currency Legend</h3>{rows}<p style="margin-top:8px;font-size:0.75rem;color:#475569;">Flags show each trader\'s legal tender. A reserve bank swap may occur if yours differs.</p></div>'


def _build_active_items_panel(active_items: list, current_item: str, base_url: str) -> str:
    """Sidebar card: clickable list of items that currently have active orders."""
    if not active_items:
        return '<div class="card" style="margin-top:16px;"><h3>Active Markets</h3><p style="color:#64748b;font-size:0.85rem;">No active orders.</p></div>'
    links = ""
    for it in active_items:
        display = it.replace("_", " ").title()
        if it == current_item:
            links += f'<div style="padding:4px 6px;background:#1e3a5f;border-left:3px solid #38bdf8;margin-bottom:3px;font-size:0.82rem;color:#38bdf8;border-radius:2px;">{display}</div>'
        else:
            links += f'<a href="{base_url}?item={it}" style="display:block;padding:4px 6px;margin-bottom:3px;font-size:0.82rem;color:#94a3b8;text-decoration:none;border-left:3px solid #1e293b;border-radius:2px;" onmouseover="this.style.color=\'#e5e7eb\'" onmouseout="this.style.color=\'#94a3b8\'">{display}</a>'
    return f'<div class="card" style="margin-top:16px;"><h3 style="margin-bottom:10px;">Active Markets <span style="font-size:0.75rem;color:#64748b;font-weight:normal;">({len(active_items)})</span></h3>{links}</div>'


@router.get("/market", response_class=HTMLResponse)
def market_page(session_token: Optional[str] = Cookie(None), item: str = "apple_seeds"):
    """Market view with full order book including player names."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)

    # ETF/fund shares have their own trading floor — redirect away from /market.
    if item.endswith("_shares"):
        return RedirectResponse(url="/brokerage/trading?mode=etf", status_code=303)

    try:
        import market as market_mod
        import inventory as inv_mod

        items = list(inv_mod.ITEM_RECIPES.keys())
        stats = market_mod.get_market_stats()
        order_book = market_mod.get_order_book(item)

        # Build currency flag map for order book traders
        from reserve_banks import get_player_legal_tender as _get_tender, get_all_banks as _get_banks
        _banks_data = _get_banks()
        _bank_flags = {b["code"]: b["flag"] for b in _banks_data}
        _bank_flags.setdefault("USD", "🇺🇸")
        _order_pids = set()
        if order_book:
            for _e in order_book.get('bids', [])[:10]:
                _order_pids.add(_e[4])
            for _e in order_book.get('asks', [])[:10]:
                _order_pids.add(_e[4])
        player_flags = {pid: _bank_flags.get(_get_tender(pid), "🌐") for pid in _order_pids}

        # Fetch player's own open orders and items with active orders
        from market import MarketOrder, OrderStatus, OrderType, get_db as get_market_db
        mkt_db = get_market_db()
        try:
            my_orders = mkt_db.query(MarketOrder).filter(
                MarketOrder.player_id == player.id,
                MarketOrder.item_type == item,
                MarketOrder.status.in_([OrderStatus.ACTIVE, OrderStatus.PARTIALLY_FILLED])
            ).order_by(MarketOrder.created_at.desc()).all()
            _active_rows = mkt_db.query(MarketOrder.item_type).filter(
                MarketOrder.status.in_([OrderStatus.ACTIVE, OrderStatus.PARTIALLY_FILLED])
            ).distinct().all()
            active_items = sorted({r[0] for r in _active_rows if not r[0].endswith("_shares")})
        finally:
            mkt_db.close()
        
        # Group items by category
        categories = {}
        for i in items:
            info = inv_mod.get_item_info(i)
            cat = info.get("category", "other") if info else "other"
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(i)
        
        # Category colors
        # Category colors
        cat_colors = {
            "seeds": "#22c55e",
            "fruits": "#84cc16",
            "vegetables": "#16a34a",
            "crops": "#eab308",
            "food": "#f97316",
            "prepared_food": "#fb923c",
            "beverage": "#06b6d4",
            "alcohol": "#a855f7",
            "ingredients": "#ec4899",
            "livestock": "#92400e",
            "feed": "#a3e635",
            "health": "#ef4444",
            "personal_care": "#f472b6",
            "industrial": "#64748b",
            "materials": "#78716c",
            "textiles": "#c084fc",
            "wood": "#a16207",
            "ore": "#71717a",
            "metals": "#94a3b8",
            "components": "#6366f1",
            "auto_parts": "#3b82f6",
            "marine_parts": "#0ea5e9",
            "vehicle": "#2563eb",
            "apparel": "#d946ef",
            "accessories": "#e879f9",
            "home_goods": "#14b8a6",
            "packaging": "#737373",
            "media": "#facc15",
            "liquids": "#38bdf8",
            "energy": "#f59e0b",
            "financial": "#10b981",
            "luxury": "#d4af37",
            "minerals": "#a8a29e",
            "other": "#94a3b8"
        }
        
        # Search bar
        search_bar = '''
        <div style="margin-bottom: 16px;">
            <input 
                type="text" 
                id="itemSearch" 
                placeholder="🔍 Search commodities..." 
                style="width: 100%; padding: 12px; background: #0f172a; border: 1px solid #1e293b; color: #e5e7eb; font-family: 'JetBrains Mono', monospace; font-size: 14px; border-radius: 4px;"
                oninput="filterItems()"
                autofocus
            >
            <div id="searchResults" style="color: #64748b; font-size: 0.85rem; margin-top: 8px;"></div>
        </div>
        '''
        
        # Build category tabs
        filter_tabs = '<div id="itemTabs" style="margin-bottom: 20px; max-width: 100%;">'
        
        for cat_name, cat_items in sorted(categories.items()):
            cat_color = cat_colors.get(cat_name, "#64748b")
            filter_tabs += f'''
            <div style="margin-bottom: 12px;">
                <div style="color: {cat_color}; font-size: 0.75rem; font-weight: bold; margin-bottom: 6px; text-transform: uppercase;">
                    {cat_name.replace("_", " ")}
                </div>
                <div style="display: flex; flex-wrap: wrap; gap: 6px;">
            '''
            for i in sorted(cat_items):
                is_selected = i == item
                bg_color = cat_color if is_selected else "#0f172a"
                text_color = "#020617" if is_selected else cat_color
                border = f"1px solid {cat_color}"
                display_name = i.replace("_", " ").title()
                
                filter_tabs += f'''
                <a href="/market?item={i}" 
                   class="item-tab" 
                   data-item="{i}" 
                   data-display="{display_name}"
                   style="padding: 4px 10px; font-size: 0.8rem; background: {bg_color}; color: {text_color}; 
                          border: {border}; border-radius: 3px; text-decoration: none; display: inline-block;">
                    {display_name}
                </a>'''
            filter_tabs += '</div></div>'
        
        filter_tabs += '</div>'
        
        # Search script
        search_script = '''
        <script>
        function filterItems() {
            const searchInput = document.getElementById('itemSearch').value.toLowerCase();
            const tabs = document.querySelectorAll('.item-tab');
            const resultsDiv = document.getElementById('searchResults');
            let visibleCount = 0;
            
            tabs.forEach(tab => {
                const itemName = tab.getAttribute('data-item').toLowerCase();
                const displayName = tab.getAttribute('data-display').toLowerCase();
                
                if (itemName.includes(searchInput) || displayName.includes(searchInput)) {
                    tab.style.display = 'inline-block';
                    visibleCount++;
                } else {
                    tab.style.display = 'none';
                }
            });
            
            if (searchInput && visibleCount === 0) {
                resultsDiv.textContent = '⚠ No items found';
                resultsDiv.style.color = '#ef4444';
            } else if (searchInput) {
                resultsDiv.textContent = `✓ Showing ${visibleCount} item${visibleCount !== 1 ? 's' : ''}`;
                resultsDiv.style.color = '#22c55e';
            } else {
                resultsDiv.textContent = '';
            }
        }
        </script>
        '''
        
        # Item info
        item_info = inv_mod.get_item_info(item)
        item_name = item_info.get("name", item.replace("_", " ").title()) if item_info else item.replace("_", " ").title()
        item_desc = item_info.get("description", "") if item_info else ""
        item_cat = item_info.get("category", "other") if item_info else "other"
        
        # Build market HTML
        market_html = f'''
        <a href="/" style="color: #38bdf8;"><- Dashboard</a>
        <div style="display: flex; gap: 20px; max-width: 100%;">
            <div style="flex: 2; min-width: 0;">
                <h1>📈 Market</h1>
                <div style="margin-bottom: 16px; padding: 12px; background: #0f172a; border-left: 4px solid {cat_colors.get(item_cat, "#64748b")};">
                    <div style="font-size: 1.2rem; font-weight: bold; color: #38bdf8;">{item_name}</div>
                    <div style="color: #64748b; font-size: 0.85rem; margin-top: 4px;">{item_desc}</div>
                    <div style="color: #94a3b8; font-size: 0.75rem; margin-top: 4px;">Category: {item_cat.upper()}</div>
                </div>
                
                {search_bar}
                {filter_tabs}
                {search_script}
                
                <!-- Order Placement Form -->
                <div class="card">
                    <h3>Place Limit Order</h3>
                    <form action="/api/market/order" method="post" style="display: grid; grid-template-columns: 1fr 1fr 1fr auto; gap: 10px;">
                        <input type="hidden" name="item_type" value="{item}">
                        <select name="order_type">
                            <option value="buy">BUY</option>
                            <option value="sell">SELL</option>
                        </select>
                        <input type="number" name="quantity" placeholder="Quantity" required>
                        <input type="number" name="price" step="0.0001" placeholder="Price ({disp['code']})" required>
                        <button type="submit" class="btn-blue">Submit</button>
                    </form>
                </div>
                
                <!-- Order Book Grid -->
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                    
                    <!-- BIDS -->
                    <div class="card">
                        <h3 style="color: #22c55e;">Bids (Buy Orders)</h3>
                        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; margin-bottom: 8px; padding-bottom: 8px; border-bottom: 1px solid #1e293b; font-size: 0.85rem; color: #64748b;">
                            <span>Price</span>
                            <span>Qty</span>
                            <span>Trader</span>
                        </div>'''
        
        if order_book and order_book.get('bids'):
            for price, qty, order_id, player_name, player_id in order_book['bids'][:10]:
                p_flag = player_flags.get(player_id, "🌐")
                market_html += f'''
                        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; font-size: 0.9rem; padding: 4px 0; color: #22c55e;">
                            <span>{fmt_usd(price, disp)}</span>
                            <span>{qty:,.2f}</span>
                            <span style="font-size: 0.8rem; color: #64748b;" title="Legal tender flag">{p_flag} {player_name[:15]}</span>
                        </div>'''
        else:
            market_html += '<p style="color: #64748b; font-size: 0.85rem; padding: 8px 0;">No bids</p>'

        market_html += '''
                    </div>

                    <!-- ASKS -->
                    <div class="card">
                        <h3 style="color: #ef4444;">Asks (Sell Orders)</h3>
                        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; margin-bottom: 8px; padding-bottom: 8px; border-bottom: 1px solid #1e293b; font-size: 0.85rem; color: #64748b;">
                            <span>Price</span>
                            <span>Qty</span>
                            <span>Trader</span>
                        </div>'''

        if order_book and order_book.get('asks'):
            for price, qty, order_id, player_name, player_id in order_book['asks'][:10]:
                p_flag = player_flags.get(player_id, "🌐")
                market_html += f'''
                        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; font-size: 0.9rem; padding: 4px 0; color: #ef4444;">
                            <span>{fmt_usd(price, disp)}</span>
                            <span>{qty:,.2f}</span>
                            <span style="font-size: 0.8rem; color: #64748b;" title="Legal tender flag">{p_flag} {player_name[:15]}</span>
                        </div>'''
        else:
            market_html += '<p style="color: #64748b; font-size: 0.85rem; padding: 8px 0;">No asks</p>'
        
        # Build My Open Orders section
        my_orders_html = ""
        if my_orders:
            my_orders_rows = ""
            for o in my_orders:
                side_color = "#22c55e" if o.order_type == "buy" else "#ef4444"
                remaining = o.quantity - o.quantity_filled
                my_orders_rows += f'''
                <tr style="border-bottom: 1px solid #1e293b;">
                    <td style="padding: 8px 6px; color: {side_color}; font-weight: bold;">{o.order_type.upper()}</td>
                    <td style="padding: 8px 6px;">{'MKT' if o.price is None else f'{fmt_usd(o.price, disp)}'}</td>
                    <td style="padding: 8px 6px;">{o.quantity:,.2f}</td>
                    <td style="padding: 8px 6px; color: #94a3b8;">{o.quantity_filled:,.2f}</td>
                    <td style="padding: 8px 6px; color: #f59e0b;">{remaining:,.2f}</td>
                    <td style="padding: 8px 6px;">
                        <form action="/api/market/cancel-order" method="post" style="display:inline;">
                            <input type="hidden" name="order_id" value="{o.id}">
                            <input type="hidden" name="item_type" value="{item}">
                            <button type="submit" style="background:#7f1d1d;color:#fca5a5;border:none;padding:3px 10px;border-radius:3px;cursor:pointer;font-size:0.8rem;">
                                Cancel
                            </button>
                        </form>
                    </td>
                </tr>'''
            my_orders_html = f'''
            <div class="card" style="margin-top: 20px;">
                <h3>My Open Orders</h3>
                <table style="width:100%;border-collapse:collapse;">
                    <thead>
                        <tr style="border-bottom:1px solid #1e293b;font-size:0.85rem;color:#64748b;text-align:left;">
                            <th style="padding:8px 6px;">Side</th>
                            <th style="padding:8px 6px;">Price</th>
                            <th style="padding:8px 6px;">Qty</th>
                            <th style="padding:8px 6px;">Filled</th>
                            <th style="padding:8px 6px;">Remaining</th>
                            <th style="padding:8px 6px;">Action</th>
                        </tr>
                    </thead>
                    <tbody>{my_orders_rows}</tbody>
                </table>
            </div>'''
        else:
            my_orders_html = '''
            <div class="card" style="margin-top: 20px;">
                <h3>My Open Orders</h3>
                <p style="color:#64748b;font-size:0.85rem;">No open orders for this item.</p>
            </div>'''

        market_html += f'''
                    </div>
                </div>
                {my_orders_html}
            </div>

            <!-- Sidebar -->
            <div style="flex: 1; min-width: 0; max-width: 280px;">
                <div class="card">
                    <h3>Market Stats</h3>
                    <p><strong>24h Volume:</strong><br>{fmt_usd(stats["volume_24h"], disp)}</p>
                    <p style="margin-top: 12px;"><strong>Total Trades:</strong><br>{stats["total_trades"]:,}</p>
                    <p style="margin-top: 12px;"><strong>Active Orders:</strong><br>{stats["active_orders"]:,}</p>
                </div>
                {_build_currency_legend_panel(_banks_data)}
                {_build_active_items_panel(active_items, item, "/market")}
            </div>
        </div>
        '''
        
        # Inject tutorial overlay for market-relevant steps
        try:
            from tutorial_ux import get_tutorial_overlay_html
            tut_overlay = get_tutorial_overlay_html(player, "market")
            if tut_overlay:
                market_html = tut_overlay + market_html
        except Exception:
            pass

        return shell("Market", market_html, player.cash_balance, player.id)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return shell("Market", f"Error loading market: {e}", player.cash_balance, player.id)

# ==========================
# WPE COMPANY LISTINGS PAGE
# ==========================
# Add this route to ux.py for viewing all public companies

@router.get("/brokerage/companies", response_class=HTMLResponse)
def brokerage_companies_page(session_token: Optional[str] = Cookie(None)):
    """View all public companies listed on WPE."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)

    try:
        from banks.brokerage_firm import (
            CompanyShares, ShareholderPosition, get_db as get_firm_db
        )
        from auth import Player, get_db as get_auth_db
        from business import Business, BUSINESS_TYPES
        from land import get_db as get_land_db
        
        db = get_firm_db()
        auth_db = get_auth_db()
        land_db = get_land_db()
        
        try:
            # Get all public companies
            companies = db.query(CompanyShares).filter(
                CompanyShares.is_delisted == False
            ).order_by(CompanyShares.ticker_symbol).all()
            
            company_data = []
            for company in companies:
                # Get founder info
                founder = auth_db.query(Player).filter(Player.id == company.founder_id).first()
                founder_name = founder.business_name if founder else f"Player {company.founder_id}"
                
                # Get business info
                business = land_db.query(Business).filter(Business.id == company.business_id).first()
                business_type = BUSINESS_TYPES.get(business.business_type, {}).get("name", "Unknown") if business else "Unknown"
                
                # Get shareholder count
                shareholder_count = db.query(ShareholderPosition).filter(
                    ShareholderPosition.company_shares_id == company.id,
                    ShareholderPosition.shares_owned > 0
                ).count()
                
                # Calculate market cap
                market_cap = company.current_price * company.shares_outstanding
                
                # Calculate price change from IPO
                if company.ipo_price > 0:
                    price_change = ((company.current_price - company.ipo_price) / company.ipo_price) * 100
                else:
                    price_change = 0
                
                company_data.append({
                    "company": company,
                    "founder_name": founder_name,
                    "business_type": business_type,
                    "shareholder_count": shareholder_count,
                    "market_cap": market_cap,
                    "price_change": price_change
                })
            
        finally:
            db.close()
            auth_db.close()
            land_db.close()
        
        # Build company cards
        companies_html = ""
        if company_data:
            for item in company_data:
                company = item["company"]
                change_color = "#22c55e" if item["price_change"] >= 0 else "#ef4444"
                change_arrow = "▲" if item["price_change"] >= 0 else "▼"
                
                # Status badges
                badges = ""
                if company.is_tbtf:
                    badges += '<span class="badge" style="background: #22c55e; margin-left: 5px;">🛡️ TBTF</span>'
                if company.trading_halted_until and datetime.utcnow() < company.trading_halted_until:
                    badges += '<span class="badge" style="background: #ef4444; margin-left: 5px;">🛑 HALTED</span>'
                if company.stabilization_active:
                    badges += '<span class="badge" style="background: #8b5cf6; margin-left: 5px;">📊 STABILIZED</span>'
                if company.dividend_warning_active:
                    badges += '<span class="badge" style="background: #f59e0b; margin-left: 5px;">⚠️ DIV WARNING</span>'
                
                # Dividend info
                dividend_text = "No dividends"
                if company.dividend_config:
                    div = company.dividend_config[0]
                    if div.get("type") == "cash":
                        dividend_text = f"Cash: {div.get('amount', 0)*100:.1f}% ({div.get('frequency', 'weekly')})"
                    elif div.get("type") == "commodity":
                        dividend_text = f"{div.get('item', 'item')}: {div.get('amount', 0)}/share"
                    elif div.get("type") == "scrip":
                        dividend_text = f"Stock: {div.get('rate', 0)*100:.1f}%"
                
                companies_html += f'''
                <div class="card">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div>
                            <h3 style="margin: 0;">
                                {company.ticker_symbol} - {company.company_name}
                                {badges}
                            </h3>
                            <p style="color: #64748b; margin: 5px 0;">
                                {item["business_type"]} · Founded by {item["founder_name"]} · Class {company.share_class}
                            </p>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-size: 1.8rem; font-weight: bold; color: #38bdf8;">{fmt_usd(company.current_price, disp, precision=4)}</div>
                            <div style="color: {change_color};">
                                {change_arrow} {abs(item["price_change"]):.1f}% from IPO
                            </div>
                        </div>
                    </div>
                    
                    <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 15px; margin-top: 15px;">
                        <div>
                            <div style="color: #64748b; font-size: 0.8rem;">Market Cap</div>
                            <div style="font-size: 1.1rem;">{fmt_usd(item["market_cap"], disp, precision=0)}</div>
                        </div>
                        <div>
                            <div style="color: #64748b; font-size: 0.8rem;">Float</div>
                            <div style="font-size: 1.1rem;">{company.shares_in_float:,}</div>
                        </div>
                        <div>
                            <div style="color: #64748b; font-size: 0.8rem;">Shareholders</div>
                            <div style="font-size: 1.1rem;">{item["shareholder_count"]}</div>
                        </div>
                        <div>
                            <div style="color: #64748b; font-size: 0.8rem;">Dividend Streak</div>
                            <div style="font-size: 1.1rem;">{company.consecutive_dividend_payouts}</div>
                        </div>
                        <div>
                            <div style="color: #64748b; font-size: 0.8rem;">Dividends</div>
                            <div style="font-size: 0.9rem;">{dividend_text}</div>
                        </div>
                    </div>
                    
                    <div style="margin-top: 15px; display: flex; gap: 10px;">
                        <a href="/brokerage/trading?ticker={company.ticker_symbol}" class="btn-blue">Trade</a>
                        <a href="/brokerage/shorts?ticker={company.ticker_symbol}" class="btn-orange">Short</a>
                    </div>
                </div>
                '''
        else:
            companies_html = '''
            <div class="card">
                <h3>No Companies Listed</h3>
                <p style="color: #64748b;">Be the first to take your business public!</p>
                <a href="/brokerage/ipo" class="btn-blue">Launch an IPO</a>
            </div>
            '''
        
        body = f'''
        <a href="/banks/brokerage-firm" style="color: #38bdf8;">← Brokerage Firm</a>
        <h1>WPE Listed Companies</h1>
        <p style="color: #64748b;">{len(company_data)} companies listed on the Wadsworth Player Exchange</p>
        
        {companies_html}
        '''
        
        return shell("WPE Companies", body, player.cash_balance, player.id)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return shell("WPE Companies", f"Error: {e}", player.cash_balance, player.id)


# ==========================
# FOUNDER'S COMPANY MANAGEMENT PAGE
# ==========================
# Add this route for founders to manage their public companies

@router.get("/brokerage/my-companies", response_class=HTMLResponse)
def brokerage_my_companies_page(session_token: Optional[str] = Cookie(None)):
    """Manage companies you've founded."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)

    try:
        from banks.brokerage_firm import (
            CompanyShares, ShareholderPosition, get_db as get_firm_db,
            delist_company, call_shares, CompanyProposal
        )
        
        db = get_firm_db()
        try:
            # Get companies founded by this player (exclude Quad-Class C/D sub-records)
            my_companies = db.query(CompanyShares).filter(
                CompanyShares.founder_id == player.id,
                CompanyShares.is_delisted == False,
                CompanyShares.parent_company_id == None,
            ).all()
            
            company_data = []
            for company in my_companies:
                # Get founder's position
                founder_position = db.query(ShareholderPosition).filter(
                    ShareholderPosition.player_id == player.id,
                    ShareholderPosition.company_shares_id == company.id
                ).first()
                
                founder_shares = founder_position.shares_owned if founder_position else 0
                ownership_pct = (founder_shares / company.shares_outstanding * 100) if company.shares_outstanding > 0 else 0
                
                # Founder can always attempt to go private — delist_company handles the buyback cost
                can_delist = True
                
                # Count open governance proposals for this company
                open_proposals = db.query(CompanyProposal).filter(
                    CompanyProposal.company_shares_id == company.id,
                    CompanyProposal.status == "open",
                ).count()

                company_data.append({
                    "company": company,
                    "founder_shares": founder_shares,
                    "ownership_pct": ownership_pct,
                    "can_delist": can_delist,
                    "open_proposals": open_proposals,
                })
            
            # Get delisted companies
            delisted = db.query(CompanyShares).filter(
                CompanyShares.founder_id == player.id,
                CompanyShares.is_delisted == True
            ).all()
            
        finally:
            db.close()
        
        # Build company cards
        companies_html = ""
        if company_data:
            for item in company_data:
                company = item["company"]
                
                # Dividend configuration form
                current_dividends = ""
                if company.dividend_config:
                    for div in company.dividend_config:
                        current_dividends += f"<li>{div.get('type', 'unknown').title()}: {div.get('amount', 0)} ({div.get('frequency', 'unknown')})</li>"
                else:
                    current_dividends = "<li>No dividends configured</li>"

                # Pre-build conditional forms to avoid nested f-string issues
                buyback_form_html = ""
                if company.shares_in_float > 0:
                    buyback_form_html = f'''
                        <form action="/api/brokerage/buyback" method="post" style="display: inline;">
                            <input type="hidden" name="company_id" value="{company.id}">
                            <input type="number" name="shares" placeholder="Shares to buy" style="width: 100px; padding: 6px;" min="1" max="{company.shares_in_float}">
                            <button type="submit" class="btn-orange">Buyback</button>
                        </form>'''

                go_private_form_html = ""
                if item["can_delist"]:
                    go_private_form_html = f'''
                        <form action="/api/brokerage/go-private" method="post" style="display: inline;">
                            <input type="hidden" name="company_id" value="{company.id}">
                            <button type="submit" class="btn-red" onclick="return confirm('Take company private? This will buy back all public shares at a 10% premium and delist the stock. You cannot re-IPO for 30 days.')">
                                Go Private
                            </button>
                        </form>'''
                else:
                    go_private_form_html = '<span style="color: #64748b; font-size: 0.85rem;">Buy back all shares to go private</span>'

                call_shares_html = ""
                if company.is_callable:
                    call_price = company.current_price * 1.05
                    call_class_label = company.share_class_label.upper() if company.share_class_label != "main" else "public"
                    call_confirm_msg = f"Call all outstanding {call_class_label} shares at {fmt_usd(call_price, disp, precision=4)}/share (5% call premium)?"
                    call_shares_html = f'''
                        <form action="/api/brokerage/call-shares" method="post" style="display: inline;">
                            <input type="hidden" name="company_id" value="{company.id}">
                            <button type="submit" class="btn-orange"
                                onclick="return confirm({repr(call_confirm_msg)})">
                                📞 Call Shares
                            </button>
                        </form>'''

                proposals_badge = ""
                if item["open_proposals"] > 0:
                    proposals_badge = f' <span style="background:#7c3aed;color:#fff;padding:2px 7px;border-radius:10px;font-size:0.75rem;">{item["open_proposals"]} open vote{"s" if item["open_proposals"] != 1 else ""}</span>'

                companies_html += f'''
                <div class="card">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div>
                            <h3 style="margin: 0;">{company.ticker_symbol} - {company.company_name}</h3>
                            <p style="color: #64748b;">You founded this company</p>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-size: 1.5rem; font-weight: bold; color: #38bdf8;">{fmt_usd(company.current_price, disp, precision=4)}</div>
                        </div>
                    </div>
                    
                    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-top: 15px;">
                        <div>
                            <div style="color: #64748b; font-size: 0.8rem;">Your Shares</div>
                            <div style="font-size: 1.2rem;">{item["founder_shares"]:,}</div>
                        </div>
                        <div>
                            <div style="color: #64748b; font-size: 0.8rem;">Your Ownership</div>
                            <div style="font-size: 1.2rem;">{item["ownership_pct"]:.1f}%</div>
                        </div>
                        <div>
                            <div style="color: #64748b; font-size: 0.8rem;">Shares Outstanding</div>
                            <div style="font-size: 1.2rem;">{company.shares_outstanding:,}</div>
                        </div>
                        <div>
                            <div style="color: #64748b; font-size: 0.8rem;">Public Float</div>
                            <div style="font-size: 1.2rem;">{company.shares_in_float:,}</div>
                        </div>
                    </div>
                    
                    <div style="margin-top: 20px; padding-top: 15px; border-top: 1px solid #1e293b;">
                        <h4>Current Dividends</h4>
                        <ul style="color: #94a3b8; margin: 10px 0;">
                            {current_dividends}
                        </ul>
                        <p style="color: #64748b; font-size: 0.85rem;">
                            Dividend streak: {company.consecutive_dividend_payouts} payouts
                            {' | <span style="color: #f59e0b;">⚠️ Warning active</span>' if company.dividend_warning_active else ''}
                        </p>
                    </div>
                    
                    <div style="margin-top: 15px; display: flex; gap: 10px; flex-wrap: wrap; align-items: center;">
                        <a href="/brokerage/trading?ticker={company.ticker_symbol}" class="btn-blue">View Trading</a>
                        <a href="/brokerage/governance?company_id={company.id}" class="btn-blue" style="background:#4c1d95;">
                            🗳 Governance{proposals_badge}
                        </a>
                        {buyback_form_html}
                        {call_shares_html}
                        {go_private_form_html}
                    </div>
                </div>
                '''
        else:
            companies_html = '''
            <div class="card">
                <h3>No Public Companies</h3>
                <p style="color: #64748b;">You haven't taken any businesses public yet.</p>
                <a href="/brokerage/ipo" class="btn-blue">Launch Your First IPO</a>
            </div>
            '''
        
        # Delisted companies section
        delisted_html = ""
        if delisted:
            delisted_html = '<div class="card" style="margin-top: 20px;"><h3>Delisted Companies</h3>'
            for company in delisted:
                can_relist = company.can_relist_after and datetime.utcnow() >= company.can_relist_after
                delisted_html += f'''
                <div style="padding: 10px; margin: 10px 0; background: #020617; border-radius: 4px;">
                    <strong>{company.ticker_symbol}</strong> - {company.company_name}
                    <span style="color: #64748b; margin-left: 10px;">Delisted: {company.delisted_at.strftime("%Y-%m-%d") if company.delisted_at else "N/A"}</span>
                    {f'<span style="color: #22c55e; margin-left: 10px;">✓ Can re-IPO</span>' if can_relist else f'<span style="color: #f59e0b; margin-left: 10px;">Cooldown until {company.can_relist_after.strftime("%Y-%m-%d %H:%M") if company.can_relist_after else "N/A"}</span>'}
                </div>
                '''
            delisted_html += '</div>'
        
        body = f'''
        <a href="/banks/brokerage-firm" style="color: #38bdf8;">← Brokerage Firm</a>
        <h1>My Public Companies</h1>
        <p style="color: #64748b;">Manage companies you've founded and taken public</p>
        
        {companies_html}
        {delisted_html}
        '''
        
        return shell("My Companies", body, player.cash_balance, player.id)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return shell("My Companies", f"Error: {e}", player.cash_balance, player.id)


# ==========================
# ADDITIONAL API ENDPOINTS FOR FOUNDER ACTIONS
# ==========================

@router.post("/api/brokerage/buyback")
async def brokerage_buyback_shares(
    company_id: int = Form(...),
    shares: int = Form(...),
    session_token: Optional[str] = Cookie(None)
):
    """Founder buys back shares from the float."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)
    
    try:
        from banks.brokerage_firm import (
            CompanyShares, ShareholderPosition, buy_shares, get_db as get_firm_db
        )
        
        # Verify founder
        db = get_firm_db()
        try:
            company = db.query(CompanyShares).filter(
                CompanyShares.id == company_id,
                CompanyShares.founder_id == player.id
            ).first()
            
            if not company:
                return RedirectResponse(url="/brokerage/my-companies?error=not_founder", status_code=303)
        finally:
            db.close()
        
        # Use standard buy function
        success = buy_shares(
            buyer_id=player.id,
            company_shares_id=company_id,
            quantity=shares,
            use_margin=False
        )
        
        if success:
            return RedirectResponse(url="/brokerage/my-companies?success=buyback_complete", status_code=303)
        return RedirectResponse(url="/brokerage/my-companies?error=buyback_failed", status_code=303)
        
    except Exception as e:
        print(f"[UX] Buyback error: {e}")
        return RedirectResponse(url="/brokerage/my-companies?error=exception", status_code=303)


# go-private route is defined later at /api/brokerage/go-private (line ~4028)

# ==========================
# UPDATED BANKS PAGE WITH BROKERAGE FIRM
# ==========================
# Banks_page function

@router.get("/banks", response_class=HTMLResponse)
def banks_page(session_token: Optional[str] = Cookie(None)):
    """Banking and investment view with Brokerage Firm."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return player
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)

    try:
        import banks
        
        # Query active bank entities
        db = banks.get_db()
        bank_entities = db.query(banks.BankEntity).filter(banks.BankEntity.is_active == True).all()
        db.close()

        bank_html = '<a href="/" style="color: #38bdf8;">← Dashboard</a><h1>Banking & Investments</h1>'
        
        # ==========================
        # BROKERAGE FIRM CARD (Special - not in BankEntity table)
        # ==========================
        try:
            from banks.brokerage_firm import (
                get_firm_entity, firm_is_solvent, get_player_credit,
                ShareholderPosition, CompanyShares, get_db as get_firm_db
            )
            
            firm = get_firm_entity()
            player_credit = get_player_credit(player.id)
            is_solvent = firm_is_solvent()
            
            # Get player's total equity value
            firm_db = get_firm_db()
            try:
                positions = firm_db.query(ShareholderPosition).filter(
                    ShareholderPosition.player_id == player.id,
                    ShareholderPosition.shares_owned > 0
                ).all()
                
                total_equity_value = 0.0
                for pos in positions:
                    company = firm_db.query(CompanyShares).filter(
                        CompanyShares.id == pos.company_shares_id
                    ).first()
                    if company:
                        total_equity_value += pos.shares_owned * company.current_price
                
                company_count = firm_db.query(CompanyShares).filter(
                    CompanyShares.is_delisted == False
                ).count()
            finally:
                firm_db.close()
            
            # Credit tier colors
            tier_colors = {
                "prime": "#22c55e",
                "standard": "#38bdf8",
                "fair": "#f59e0b",
                "subprime": "#ef4444",
                "junk": "#7f1d1d"
            }
            tier_color = tier_colors.get(player_credit.tier, "#64748b")
            
            bank_html += f'''
            <div class="card" style="border: 2px solid #38bdf8; background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);">
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div>
                        <h3 style="margin: 0;">🏛️ Wadsworth Brokerage Firm</h3>
                        <p style="color: #64748b; margin-top: 5px;">Full-service: IPOs, Margin Trading, Short Selling, Commodity Lending</p>
                    </div>
                    <div style="text-align: right;">
                        <span class="badge" style="background: {'#22c55e' if is_solvent else '#ef4444'};">
                            {'SOLVENT' if is_solvent else 'INSOLVENT'}
                        </span>
                    </div>
                </div>
                
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-top: 20px;">
                    <div>
                        <div style="color: #64748b; font-size: 0.8rem;">Your Credit</div>
                        <div style="font-size: 1.5rem; font-weight: bold; color: {tier_color};">
                            {player_credit.credit_score} <span style="font-size: 0.8rem;">({player_credit.tier.upper()})</span>
                        </div>
                    </div>
                    <div>
                        <div style="color: #64748b; font-size: 0.8rem;">Your Equity</div>
                        <div style="font-size: 1.5rem; font-weight: bold; color: #38bdf8;">{fmt_usd(total_equity_value, disp, precision=0)}</div>
                    </div>
                    <div>
                        <div style="color: #64748b; font-size: 0.8rem;">Firm Reserves</div>
                        <div style="font-size: 1.5rem; font-weight: bold;">{fmt_usd(firm.cash_reserves, disp, precision=0)}</div>
                    </div>
                    <div>
                        <div style="color: #64748b; font-size: 0.8rem;">Listed Companies</div>
                        <div style="font-size: 1.5rem; font-weight: bold; color: #f59e0b;">{company_count}</div>
                    </div>
                </div>
                
                <div style="margin-top: 20px; display: flex; gap: 10px; flex-wrap: wrap;">
                    <a href="/banks/brokerage-firm" class="btn-blue">Open Firm Dashboard</a>
                    <a href="/brokerage/trading" class="btn-blue" style="background: #22c55e;">Trade WPE</a>
                    <a href="/brokerage/ipo" class="btn-orange">Launch IPO</a>
                    <a href="/brokerage/commodities" class="btn-blue" style="background: #8b5cf6;">WCE Commodities</a>
                </div>
            </div>
            '''
        except Exception as e:
            print(f"[UX] Brokerage firm card error: {e}")
            import traceback
            traceback.print_exc()
            bank_html += '''
            <div class="card" style="border: 1px solid #ef4444;">
                <h3>🏛️ Wadsworth Brokerage Firm</h3>
                <p style="color: #ef4444;">Error loading brokerage firm data</p>
            </div>
            '''

        # ==========================
        # INDICES CARD
        # ==========================
        try:
            from banks.indices import INDICES, _get_history, _fmt, _pct_change
            from datetime import timedelta as _td
            import datetime as _dt

            # Grab WBC50 for a quick preview and count data points
            snaps = _get_history("WBC50", 2)
            wbc_now  = snaps[-1].value if snaps else 0.0
            wbc_prev = snaps[0].value  if len(snaps) >= 2 else wbc_now
            wbc_ch   = _pct_change(wbc_now, wbc_prev)
            wbc_str  = _fmt(wbc_now, "USD")
            wbc_col  = "#22c55e" if wbc_ch >= 0 else "#ef4444"
            wbc_arrow = "▲" if wbc_ch >= 0 else "▼"

            # GFI preview
            gfi_snaps = _get_history("GFI", 1)
            gfi_val   = gfi_snaps[-1].value if gfi_snaps else 50.0
            gfi_col   = ("#dc2626" if gfi_val <= 24 else "#f97316" if gfi_val <= 44
                         else "#eab308" if gfi_val <= 55 else "#22c55e")
            gfi_label = ("Extreme Fear" if gfi_val <= 24 else "Fear" if gfi_val <= 44
                         else "Neutral" if gfi_val <= 55 else "Greed" if gfi_val <= 75
                         else "Extreme Greed")

            bank_html += f'''
            <div class="card" style="border:1px solid #7c3aed;background:linear-gradient(135deg,#0f172a 0%,#1e1b4b 100%);">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                    <div>
                        <h3 style="margin:0;">📊 Market Indices</h3>
                        <p style="color:#64748b;margin-top:5px;font-size:.85rem;">
                            {len(INDICES)} composite indices tracking the Wadsworth economy in real time.
                        </p>
                    </div>
                    <span class="badge" style="background:#7c3aed;">LIVE</span>
                </div>
                <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:15px;margin-top:16px;">
                    <div>
                        <div style="color:#64748b;font-size:.8rem;">WBC-50</div>
                        <div style="font-size:1.1rem;font-weight:bold;color:#38bdf8;">{wbc_str}</div>
                        <div style="font-size:.72rem;color:{wbc_col};">{wbc_arrow} {abs(wbc_ch):.2f}%</div>
                    </div>
                    <div>
                        <div style="color:#64748b;font-size:.8rem;">Greed &amp; Fear</div>
                        <div style="font-size:1.1rem;font-weight:bold;color:{gfi_col};">{gfi_val:.0f}</div>
                        <div style="font-size:.72rem;color:{gfi_col};">{gfi_label}</div>
                    </div>
                    <div>
                        <div style="color:#64748b;font-size:.8rem;">Indices</div>
                        <div style="font-size:1.1rem;font-weight:bold;color:#a78bfa;">{len(INDICES)}</div>
                        <div style="font-size:.72rem;color:#64748b;">active</div>
                    </div>
                    <div>
                        <div style="color:#64748b;font-size:.8rem;">Coverage</div>
                        <div style="font-size:1.1rem;font-weight:bold;color:#34d399;">Global</div>
                        <div style="font-size:.72rem;color:#64748b;">economy</div>
                    </div>
                </div>
                <div style="margin-top:16px;">
                    <a href="/banks/indices" class="btn-blue" style="background:#7c3aed;">View All Indices</a>
                </div>
            </div>
            '''
        except Exception as _ie:
            bank_html += '''
            <div class="card" style="border:1px solid #7c3aed;">
                <h3>📊 Market Indices</h3>
                <p style="color:#64748b;font-size:.85rem;">
                    19 composite economic indices — <a href="/banks/indices" style="color:#a78bfa;">View Indices →</a>
                </p>
            </div>
            '''

        # ==========================
        # RESERVE NOTES & BONDS
        # ==========================
        try:
            from reserve_banks import get_all_banks, get_player_legal_tender
            all_banks_rb  = get_all_banks()
            current_code  = get_player_legal_tender(player.id)
            currency_rows = ('<option value="USD"'
                             + (' selected' if current_code == "USD" else '')
                             + '>🇺🇸 USD — Wadsworth Dollar (default)</option>')
            for bk in all_banks_rb:
                sel = ' selected' if current_code == bk["code"] else ''
                currency_rows += (
                    f'<option value="{bk["code"]}"{sel}>'
                    f'{bk["flag"]} {bk["code"]} — {bk["name"]} '
                    f'(yield {bk["yield_pct"]:+.4f}%,  1 {bk["code"]} = ${bk["usd_per_unit"]:.6f})'
                    f'</option>'
                )
            bank_html += f'''
            <div class="card" style="border-top:3px solid #a78bfa;">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px;">
                    <div>
                        <h3 style="margin:0;">🌍 Reserve Notes &amp; Bonds</h3>
                        <p style="color:#64748b;margin:6px 0 0;font-size:.85rem;">
                            Set your legal tender — income is auto-converted to this currency.
                            Currently: <strong style="color:#a78bfa;">{current_code}</strong>.
                            Earn foreign balances via bond interest to unlock new currencies.
                        </p>
                    </div>
                    <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
                        <a href="/reserve-banks/bonds" class="btn-blue">Bond Market</a>
                        <a href="/reserve-banks/forex" class="btn-orange">Forex</a>
                    </div>
                </div>
                <form action="/api/corporate-actions/legal-tender/set" method="post"
                      style="display:flex;gap:10px;align-items:flex-end;flex-wrap:wrap;margin-top:14px;">
                    <div>
                        <label style="color:#94a3b8;font-size:.8rem;display:block;margin-bottom:4px;">Legal Tender Currency</label>
                        <select name="currency_code"
                                style="background:#0f172a;color:#e5e7eb;border:1px solid #334155;
                                       padding:6px 10px;border-radius:3px;min-width:320px;font-family:inherit;">
                            {currency_rows}
                        </select>
                    </div>
                    <button type="submit"
                            style="background:#a78bfa;color:#020617;padding:8px 18px;border:none;
                                   border-radius:3px;cursor:pointer;font-family:inherit;font-weight:bold;">
                        Set Legal Tender
                    </button>
                </form>
            </div>
            '''
        except Exception:
            pass  # reserve_banks not loaded yet

        # ==========================
        # ETF AND OTHER BANKS
        # ==========================
        ETF_EXPLANATIONS = {
            "apple_seeds_etf": """
                <details style="margin-top:14px;">
                <summary style="cursor:pointer;color:#38bdf8;font-size:0.78rem;font-weight:600;letter-spacing:.04em;">HOW THIS ETF WORKS ▾</summary>
                <div style="margin-top:10px;font-size:0.75rem;color:#cbd5e1;line-height:1.7;border-top:1px solid #1e293b;padding-top:10px;">
                <div style="margin-bottom:8px;"><span style="color:#f59e0b;font-weight:600;">Backing</span> — Each share is backed by physical Apple Seeds held by the ETF. NAV = cash&nbsp;+ commodity value.</div>
                <div style="margin-bottom:8px;"><span style="color:#f59e0b;font-weight:600;">Holder Fee</span> — 0.00011918 per share per tick (~3.76 % annually). Collected every 60&nbsp;ticks. Deducted from your share count.</div>
                <div style="margin-bottom:8px;"><span style="color:#f59e0b;font-weight:600;">Dividends</span> — Paid weekly (every 120,960 ticks). Payout = 3 % of cash reserves, distributed pro-rata. Requires ≥ $500,000 cash reserve. Skipped if bank is insolvent.</div>
                <div style="margin-bottom:8px;"><span style="color:#f59e0b;font-weight:600;">Market Making — Buy</span> — Every 300 ticks the ETF checks the Apple Seeds spot price. If price &lt; 98 % of the rolling average it buys 5 % of total market supply at +2 % above spot, using its cash reserves.</div>
                <div style="margin-bottom:8px;"><span style="color:#f59e0b;font-weight:600;">Market Making — Sell</span> — When the ETF's own Apple Seeds inventory reaches ≥ 85 % of total supply it sells 100 % of that inventory at −5 % below market price.</div>
                <div style="margin-bottom:8px;"><span style="color:#f59e0b;font-weight:600;">Stock Split</span> — Triggers at $50/share (5-for-1). Hard cap of 10 billion total shares. Checked every 60 ticks.</div>
                <div style="margin-bottom:8px;"><span style="color:#f59e0b;font-weight:600;">Share Buyback</span> — If share price falls to 50 % of IPO price, the ETF buys back 80 % of outstanding shares. Capped at spending 90 % of cash reserves. Checked every 120 ticks.</div>
                <div style="margin-bottom:8px;"><span style="color:#f59e0b;font-weight:600;">Insolvency &amp; Liens</span> — If cash reserves go negative, the ETF levies shareholders every 60 ticks to recapitalise. Unpaid levies become a lien on your account at 0.01 % annual interest; 50 % of your future dividends are garnished until the lien is cleared.</div>
                <div><span style="color:#f59e0b;font-weight:600;">Quantitative Easing</span> — While insolvent and below 50 % of IPO price, the ETF buys back shares every 360 ticks (15 % of market supply, up to 5 % of absolute cash per cycle) to support the share price.</div>
                </div>
                </details>""",
            "energy_etf": """
                <details style="margin-top:14px;">
                <summary style="cursor:pointer;color:#38bdf8;font-size:0.78rem;font-weight:600;letter-spacing:.04em;">HOW THIS ETF WORKS ▾</summary>
                <div style="margin-top:10px;font-size:0.75rem;color:#cbd5e1;line-height:1.7;border-top:1px solid #1e293b;padding-top:10px;">
                <div style="margin-bottom:8px;"><span style="color:#f59e0b;font-weight:600;">Backing</span> — Each share is backed by Energy units held by the ETF. NAV = cash&nbsp;+ commodity value.</div>
                <div style="margin-bottom:8px;"><span style="color:#f59e0b;font-weight:600;">Holder Fee</span> — 0.00011918 per share per tick (~3.76 % annually). Collected every 60&nbsp;ticks. Deducted from your share count.</div>
                <div style="margin-bottom:8px;"><span style="color:#f59e0b;font-weight:600;">Dividends</span> — Paid weekly (every 120,960 ticks). Payout = 3 % of cash reserves, distributed pro-rata. Requires ≥ $500,000 cash reserve. Skipped if bank is insolvent.</div>
                <div style="margin-bottom:8px;"><span style="color:#f59e0b;font-weight:600;">Market Making — Buy</span> — Every 300 ticks, if Energy spot price &lt; 80 % of the rolling average, the ETF buys 5 % of total market supply at +2 % above spot. <em>Wider 20 % discount trigger vs Apple Seeds (2 %).</em></div>
                <div style="margin-bottom:8px;"><span style="color:#f59e0b;font-weight:600;">Market Making — Sell</span> — When the ETF holds ≥ 33 % of total Energy supply it liquidates 100 % of that inventory at −5 % below market price. <em>Much lower threshold than Apple Seeds (85 %).</em></div>
                <div style="margin-bottom:8px;"><span style="color:#f59e0b;font-weight:600;">Stock Split</span> — Triggers at $50/share (5-for-1). Hard cap of 10 billion total shares. Checked every 60 ticks.</div>
                <div style="margin-bottom:8px;"><span style="color:#f59e0b;font-weight:600;">Share Buyback</span> — If share price falls to 50 % of IPO price, the ETF buys back 80 % of outstanding shares. Capped at 90 % of cash reserves. Checked every 120 ticks.</div>
                <div style="margin-bottom:8px;"><span style="color:#f59e0b;font-weight:600;">Insolvency &amp; Liens</span> — If cash reserves go negative, shareholders are levied every 60 ticks. Unpaid levies become a lien at 0.1 % annual interest (10× higher than Apple Seeds); 33 % of future dividends garnished until cleared.</div>
                <div><span style="color:#f59e0b;font-weight:600;">Quantitative Easing</span> — While insolvent and below 50 % of IPO price, the ETF runs QE every 36 ticks (10 % of supply, up to 5 % of absolute cash). <em>Runs 10× more frequently than Apple Seeds.</em></div>
                </div>
                </details>""",
            "city_nav_etf": """
                <details style="margin-top:14px;">
                <summary style="cursor:pointer;color:#38bdf8;font-size:0.78rem;font-weight:600;letter-spacing:.04em;">HOW THIS ETF WORKS ▾</summary>
                <div style="margin-top:10px;font-size:0.75rem;color:#cbd5e1;line-height:1.7;border-top:1px solid #1e293b;padding-top:10px;">
                <div style="margin-bottom:8px;"><span style="color:#f59e0b;font-weight:600;">Backing</span> — Backed entirely by real land plots. NAV = cash + estimated land portfolio value. Tracks the total Net Asset Value of all cities worldwide.</div>
                <div style="margin-bottom:8px;"><span style="color:#f59e0b;font-weight:600;">Fixed Supply</span> — 420 billion shares issued at IPO. No stock splits, no buybacks, no new issuance — ever. Supply is permanently fixed.</div>
                <div style="margin-bottom:8px;"><span style="color:#f59e0b;font-weight:600;">No Dividends</span> — This ETF pays no dividends. All value accrues through NAV growth as land appreciates.</div>
                <div style="margin-bottom:8px;"><span style="color:#f59e0b;font-weight:600;">No Holder Fee</span> — No periodic fee is charged on shares you hold.</div>
                <div style="margin-bottom:8px;"><span style="color:#f59e0b;font-weight:600;">Cash Reserve Rule</span> — The ETF always keeps ≥ 20 % of NAV as liquid cash. Land purchases stop if buying would push cash below this floor.</div>
                <div style="margin-bottom:8px;"><span style="color:#f59e0b;font-weight:600;">Land Buying</span> — Every 60 ticks (5 min) the ETF buys up to 5 of the cheapest available listings if cash exceeds 20 % of NAV.</div>
                <div style="margin-bottom:8px;"><span style="color:#f59e0b;font-weight:600;">Land Selling</span> — Every 360 ticks (30 min) the ETF lists up to 3 plots for sale at 110 % of estimated value when land > 90 % of NAV.</div>
                <div style="margin-bottom:8px;"><span style="color:#f59e0b;font-weight:600;">Land Valuation</span> — Each plot is valued at the higher of: (a) the most recent recorded sale price, or (b) monthly property tax × 120 (a 10-year capitalisation multiple).</div>
                <div><span style="color:#f59e0b;font-weight:600;">Share Price Updates</span> — Price recalculated every 30 ticks (2.5 min) as NAV / 420B shares.</div>
                </div>
                </details>""",
            "land_bank": """
                <details style="margin-top:14px;">
                <summary style="cursor:pointer;color:#38bdf8;font-size:0.78rem;font-weight:600;letter-spacing:.04em;">HOW THIS ETF WORKS ▾</summary>
                <div style="margin-top:10px;font-size:0.75rem;color:#cbd5e1;line-height:1.7;border-top:1px solid #1e293b;padding-top:10px;">
                <div style="margin-bottom:8px;"><span style="color:#f59e0b;font-weight:600;">Backing</span> — Backed by land holdings. NAV = cash reserves + active auction prices + 90 % of last-sold value of bank-held plots.</div>
                <div style="margin-bottom:8px;"><span style="color:#f59e0b;font-weight:600;">No Holder Fee</span> — No periodic fee is charged on shares you hold.</div>
                <div style="margin-bottom:8px;"><span style="color:#f59e0b;font-weight:600;">Dividends</span> — Paid every 600 ticks (~50 min). Payout = 35 % of cash reserves, distributed pro-rata to all shareholders. Requires ≥ $5,000,000,000 cash reserve. Skipped if bank is insolvent.</div>
                <div style="margin-bottom:8px;"><span style="color:#f59e0b;font-weight:600;">Stock Split</span> — Triggers at $80/share (5-for-1). Hard cap of 50 trillion total shares. Checked every 720 ticks.</div>
                <div style="margin-bottom:8px;"><span style="color:#f59e0b;font-weight:600;">Share Buyback</span> — When cash reserves exceed $750,000,000 the bank buys back 33 % of outstanding shares at +15 % premium. Capped at 20 % of cash reserves per cycle. Checked every 72 ticks.</div>
                <div style="margin-bottom:8px;"><span style="color:#f59e0b;font-weight:600;">Insolvency &amp; Liens</span> — If cash reserves go negative, shareholders are levied every 60 ticks to recapitalise. Unpaid levies become a lien at 0.01 % annual interest; 50 % of your available cash is garnished each minute until cleared.</div>
                <div><span style="color:#f59e0b;font-weight:600;">Quantitative Easing</span> — When share price drops below −$49.99 the bank creates emergency discounted land auctions every 60 ticks. Auction starting price has no markup (vs the normal 1.5× multiplier); floor is set at 75 % of the base terrain price. Stops when the land bank reaches capacity.</div>
                </div>
                </details>""",
            "wbc50_index_fund": """
                <details style="margin-top:14px;">
                <summary style="cursor:pointer;color:#38bdf8;font-size:0.78rem;font-weight:600;letter-spacing:.04em;">HOW THIS ETF WORKS ▾</summary>
                <div style="margin-top:10px;font-size:0.75rem;color:#cbd5e1;line-height:1.7;border-top:1px solid #1e293b;padding-top:10px;">
                <div style="margin-bottom:8px;"><span style="color:#f59e0b;font-weight:600;">Backing</span> — Backed by equity positions in every company in the Wadsworth Blue-Chip 50 (top 50 public companies by market cap). NAV = cash buffer + sum of (shares held × current price) for all 50 constituents.</div>
                <div style="margin-bottom:8px;"><span style="color:#f59e0b;font-weight:600;">Full Replication Strategy</span> — The fund targets holding 19.5 % of each constituent's outstanding shares. A position is only rebalanced when it drifts outside the 18–21 % band, avoiding constant churn. Weights are proportional to each company's share of the total WBC-50 market cap.</div>
                <div style="margin-bottom:8px;"><span style="color:#f59e0b;font-weight:600;">Index Changes</span> — When a company enters the WBC-50 the fund buys to 19.5 % of its outstanding shares. When a company exits the WBC-50 the fund sells its entire position and recycles the proceeds into the cash buffer.</div>
                <div style="margin-bottom:8px;"><span style="color:#f59e0b;font-weight:600;">Rebalancing</span> — Portfolio is checked every 720 ticks (~60 min). Buy and sell orders are executed at current market price directly against the fund's cash reserves.</div>
                <div style="margin-bottom:8px;"><span style="color:#f59e0b;font-weight:600;">Brokerage Firm Funding</span> — Seeded at launch with $50,000,000 from the Brokerage Firm. During each rebalance cycle the Firm may top up the fund's cash by up to $5,000,000 to cover new buy requirements, up to a lifetime cap of $500,000,000.</div>
                <div style="margin-bottom:8px;"><span style="color:#f59e0b;font-weight:600;">Cash Buffer</span> — The fund always keeps ≥ 2 % of NAV as liquid cash to cover redemptions and fees.</div>
                <div style="margin-bottom:8px;"><span style="color:#f59e0b;font-weight:600;">No Dividends</span> — Dividends received from constituent stocks accumulate into NAV rather than being paid out. All returns are reflected in the share price.</div>
                <div style="margin-bottom:8px;"><span style="color:#f59e0b;font-weight:600;">No Splits or Buybacks</span> — Share supply is fixed at 500 million. Share price floats freely with NAV.</div>
                <div style="margin-bottom:8px;"><span style="color:#f59e0b;font-weight:600;">Expense Ratio</span> — 0.5 % annual management fee deducted from NAV every 3,600 ticks (~5 h) and transferred to the Brokerage Firm.</div>
                <div><span style="color:#f59e0b;font-weight:600;">Asset Valuation</span> — Portfolio value is recalculated every 30 ticks (2.5 min) at live market prices.</div>
                </div>
                </details>""",
        }

        for bank in bank_entities:
            # Fetch the player's specific share data from the appropriate bank module
            if bank.bank_id == "apple_seeds_etf":
                from banks.apple_seeds_etf import get_player_shareholding
                market_item = "apple_seeds_etf_shares"
                detail_url = "/banks/apple-seeds-etf"
            elif bank.bank_id == "energy_etf":
                from banks.energy_etf import get_player_shareholding
                market_item = "energy_etf_shares"
                detail_url = "/banks/energy-etf"
            elif bank.bank_id == "city_nav_etf":
                from banks.city_nav_etf import get_player_shareholding
                market_item = "city_nav_etf_shares"
                detail_url = "/banks/city-nav-etf"
            elif bank.bank_id == "wbc50_index_fund":
                from banks.wbc50_index_fund import get_player_shareholding
                market_item = "wbc50_index_fund_shares"
                detail_url = "/banks/wbc50-index-fund"
            else:
                from banks.land_bank import get_player_shareholding
                market_item = "land_bank_shares"
                detail_url = "/banks/land-bank"
            
            holding = get_player_shareholding(player.id)
            
            # Build the display using metrics from the BankEntity model
            etf_explanation = ETF_EXPLANATIONS.get(bank.bank_id, "")
            bank_html += f'''
            <div class="card">
                <h3>{bank.bank_id.replace("_", " ").title()}</h3>
                <p style="color: #64748b;">{bank.description}</p>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 15px;">
                    <div><b>Share Price:</b> {fmt_usd(bank.share_price, disp, precision=4)}</div>
                    <div><b>Market Cap:</b> {fmt_usd(bank.share_price * bank.total_shares_issued, disp)}</div>
                    <div><b>Your Shares:</b> {holding["shares_owned"]:,}</div>
                    <div><b>Your Value:</b> {fmt_usd(holding["current_value"], disp)}</div>
                    <div><b>Ownership:</b> {holding["ownership_percentage"]:.4f}%</div>
                    <div><b>NAV:</b> {fmt_usd((bank.cash_reserves + bank.asset_value), disp)}</div>
                </div>
                {etf_explanation}
                <div style="margin-top: 15px; display: flex; gap: 10px;">
                    <a href="{detail_url}" class="btn-blue">View Details</a>
                    <a href="/brokerage/trading?mode=etf" class="btn-orange">Trade Shares</a>
                </div>
            </div>
            '''
        
        return shell("Banks", bank_html, player.cash_balance, player.id)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return shell("Banks", f"Error loading banking: {e}", player.cash_balance, player.id)

@router.get("/banks/land-bank", response_class=HTMLResponse)
def land_bank_dashboard(session_token: Optional[str] = Cookie(None)):
    """Detailed Land Bank dashboard."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)

    try:
        import banks
        from banks.land_bank import (
            get_player_shareholding, BANK_ID, BANK_NAME, BANK_DESCRIPTION,
            MIN_RESERVE_FOR_DIVIDENDS, DIVIDEND_PAYOUT_PERCENTAGE,
            DIVIDEND_INTERVAL_TICKS, SPLIT_PRICE_THRESHOLD,
        )

        bank_entity = banks.get_bank_entity(BANK_ID)
        player_shares = get_player_shareholding(player.id)

        nav = (bank_entity.cash_reserves or 0) + (bank_entity.asset_value or 0)
        
        # Check if bank is insolvent
        is_insolvent = bank_entity.cash_reserves < 0
        
        body = f"""
        <a href="/banks" style="color:#38bdf8;"><- Banks</a>
        <h1>{BANK_NAME}</h1>
        <p style="color:#64748b;">{BANK_DESCRIPTION}</p>
        
        {"<div class='card' style='border: 2px solid #ef4444; background: #450a0a;'><h3 style='color: #fca5a5;'>⚠️ BANK INSOLVENT</h3><p style='color: #fca5a5;'>This bank is currently insolvent. Shareholders may be subject to solvency levies.</p></div>" if is_insolvent else ""}

        <div class="card">
            <h3>Bank Overview</h3>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                <div>
                    <p><strong>Share Price:</strong> {fmt_usd(bank_entity.share_price, disp)}</p>
                    <p><strong>Total Shares:</strong> {bank_entity.total_shares_issued:,}</p>
                    <p><strong>Market Cap:</strong> {fmt_usd(bank_entity.share_price * bank_entity.total_shares_issued, disp)}</p>
                </div>
                <div>
                    <p><strong>Net Asset Value:</strong> {fmt_usd(nav, disp)}</p>
                    <p><strong>Cash Reserves:</strong> <span style="color: {'#ef4444' if bank_entity.cash_reserves < 0 else '#22c55e'};">{fmt_usd(bank_entity.cash_reserves, disp)}</span></p>
                    <p><strong>Land Assets:</strong> {fmt_usd(bank_entity.asset_value, disp)}</p>
                </div>
            </div>
        </div>

        <div class="card">
            <h3>Your Position</h3>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                <div>
                    <p><strong>Shares Owned:</strong> {player_shares["shares_owned"]:,}</p>
                    <p><strong>Market Value:</strong> {fmt_usd(player_shares["current_value"], disp)}</p>
                </div>
                <div>
                    <p><strong>Ownership:</strong> {player_shares["ownership_percentage"]:.4f}%</p>
                    <p><strong>Lien Balance:</strong> <span style="color: {'#ef4444' if player_shares.get('lien_balance', 0) > 0 else '#22c55e'};">{fmt_usd(player_shares.get("lien_balance", 0), disp)}</span></p>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h3>Bank Statistics</h3>
            <p><strong>Total Dividends Paid:</strong> {fmt_usd(bank_entity.total_dividends_paid, disp)}</p>
            <p><strong>Last Dividend:</strong> {bank_entity.last_dividend_date.strftime("%Y-%m-%d %H:%M") if bank_entity.last_dividend_date else "Never"}</p>
        </div>

        <div style="background: #1e293b; padding: 15px; border-radius: 4px; margin-top: 20px; border-left: 4px solid #f59e0b;">
            <h3 style="margin-top: 0; color: #64748b;">How the Land Bank Works</h3>
            <ul style="color: #94a3b8; line-height: 1.8; margin: 0; padding-left: 20px;">
                <li><strong style="color: #e2e8f0;">Purpose:</strong> The government land auction house and real estate investment fund. It holds land plots in reserve and releases them via public auction at market-discovered prices.</li>
                <li><strong style="color: #e2e8f0;">Backing asset:</strong> Government-owned land. NAV = cash reserves + value of all land held in the land bank.</li>
                <li><strong style="color: #e2e8f0;">Revenue:</strong> Earns revenue every time a land auction closes at a winning bid. Revenue flows into cash reserves.</li>
                <li><strong style="color: #e2e8f0;">Dividends:</strong> Paid out to shareholders when reserves exceed {fmt_usd(MIN_RESERVE_FOR_DIVIDENDS, disp, precision=0)} — {int(DIVIDEND_PAYOUT_PERCENTAGE*100)}% of reserves distributed every {DIVIDEND_INTERVAL_TICKS} ticks.</li>
                <li><strong style="color: #e2e8f0;">Insolvency / solvency levies:</strong> If reserves go negative, shareholders are billed proportionally (reverse dividend). Unpaid levies become liens accruing interest.</li>
                <li><strong style="color: #e2e8f0;">Quantitative easing:</strong> If the share price falls below a crisis threshold, the bank creates emergency discounted land auctions to restore asset value.</li>
                <li><strong style="color: #e2e8f0;">Stock splits:</strong> Shares split when the price exceeds {fmt_usd(SPLIT_PRICE_THRESHOLD, disp, precision=0)}, keeping the price accessible.</li>
                <li><strong style="color: #e2e8f0;">Buybacks:</strong> When reserves are high, the bank repurchases and retires shares to increase per-share value.</li>
            </ul>
        </div>

        <div style="margin-top: 15px; display: flex; gap: 10px;">
            <a href="/brokerage/trading?mode=etf" class="btn-orange">Trade Shares</a>
            <a href="/land-market" class="btn-blue">View Land Market</a>
        </div>
        """

        return shell(
            BANK_NAME,
            body,
            player.cash_balance,
            player.id
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return shell("Bank Error", f"Error loading bank: {e}", player.cash_balance, player.id)

@router.get("/banks/apple-seeds-etf", response_class=HTMLResponse)
def apple_seeds_etf_dashboard(session_token: Optional[str] = Cookie(None)):
    """Detailed Apple Seeds ETF dashboard."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)

    try:
        import banks
        from banks import apple_seeds_etf as etf
        import inventory

        bank_entity = banks.get_bank_entity(etf.BANK_ID)
        player_shares = etf.get_player_shareholding(player.id)

        nav = (bank_entity.cash_reserves or 0) + (bank_entity.asset_value or 0)
        qe_active = bank_entity.share_price < (etf.QE_TRIGGER_SHARE_PRICE or 0)
        is_insolvent = bank_entity.cash_reserves < 0
        
        # Get ETF's commodity holdings
        seeds_held = inventory.get_item_quantity(etf.BANK_PLAYER_ID, etf.TARGET_COMMODITY)
        
        # Get market price
        import market as market_mod
        market_price = market_mod.get_market_price(etf.TARGET_COMMODITY) or 0

        body = f"""
        <a href="/banks" style="color:#38bdf8;"><- Banks</a>
        <h1>{etf.BANK_NAME}</h1>
        <p style="color:#64748b;">{etf.BANK_DESCRIPTION}</p>

        {"<div class='card' style='border: 2px solid #ef4444; background: #450a0a;'><h3 style='color: #fca5a5;'>⚠️ ETF INSOLVENT</h3><p style='color: #fca5a5;'>This ETF is currently insolvent. Shareholders may be subject to solvency levies.</p></div>" if is_insolvent else ""}
        
        {"<div class='card' style='border: 2px solid #f59e0b; background: #451a03;'><h3 style='color: #fbbf24;'>🏦 QUANTITATIVE EASING ACTIVE</h3><p style='color: #fbbf24;'>The ETF is buying commodities to restore asset value.</p></div>" if qe_active else ""}

        <div class="card">
            <h3>ETF Overview</h3>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                <div>
                    <p><strong>Share Price:</strong> {fmt_usd(bank_entity.share_price, disp, precision=6)}</p>
                    <p><strong>Total Shares:</strong> {bank_entity.total_shares_issued:,}</p>
                    <p><strong>Market Cap:</strong> {fmt_usd(bank_entity.share_price * bank_entity.total_shares_issued, disp)}</p>
                </div>
                <div>
                    <p><strong>Net Asset Value:</strong> {fmt_usd(nav, disp)}</p>
                    <p><strong>Cash Reserves:</strong> <span style="color: {'#ef4444' if bank_entity.cash_reserves < 0 else '#22c55e'};">{fmt_usd(bank_entity.cash_reserves, disp)}</span></p>
                    <p><strong>Commodity Backing:</strong> {fmt_usd(bank_entity.asset_value, disp)}</p>
                </div>
            </div>
        </div>

        <div class="card">
            <h3>Commodity Holdings</h3>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                <div>
                    <p><strong>Target Commodity:</strong> {etf.TARGET_COMMODITY.replace("_", " ").title()}</p>
                    <p><strong>Holdings:</strong> {seeds_held:,.0f} units</p>
                </div>
                <div>
                    <p><strong>Market Price:</strong> {fmt_usd(market_price, disp)}</p>
                    <p><strong>Total Value:</strong> {fmt_usd(seeds_held * market_price, disp)}</p>
                </div>
            </div>
        </div>

        <div class="card">
            <h3>Your Position</h3>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                <div>
                    <p><strong>Shares Owned:</strong> {player_shares["shares_owned"]:,}</p>
                    <p><strong>Market Value:</strong> {fmt_usd(player_shares["current_value"], disp)}</p>
                </div>
                <div>
                    <p><strong>Ownership:</strong> {player_shares["ownership_percentage"]:.4f}%</p>
                    <p><strong>Lien Balance:</strong> <span style="color: {'#ef4444' if player_shares.get('lien_balance', 0) > 0 else '#22c55e'};">{fmt_usd(player_shares.get("lien_balance", 0), disp)}</span></p>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h3>ETF Strategy</h3>
            <ul style="color: #94a3b8; line-height: 1.8;">
                <li>Buys {etf.TARGET_COMMODITY} when price drops below {etf.BUY_PRICE_THRESHOLD*100:.0f}% of moving average</li>
                <li>Sells when inventory reaches {etf.SELL_INVENTORY_THRESHOLD*100:.0f}% of total market supply</li>
                <li>Annual holder fee: {etf.HOLDER_FEE_PER_TICK*31536000:.2f}%</li>
                <li>Stock splits at {fmt_usd(etf.SPLIT_PRICE_THRESHOLD, disp)} share price</li>
                <li>Buybacks trigger at 50% of IPO price</li>
            </ul>
        </div>
        """

        return shell(
            etf.BANK_NAME,
            body,
            player.cash_balance,
            player.id
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return shell("ETF Error", f"Error loading ETF: {e}", player.cash_balance, player.id)

@router.get("/banks/energy-etf", response_class=HTMLResponse)
def energy_etf_dashboard(session_token: Optional[str] = Cookie(None)):
    """Detailed Energy ETF dashboard mirrored from Apple Seeds ETF."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)

    try:
        import banks
        from banks import energy_etf as etf
        import inventory

        bank_entity = banks.get_bank_entity(etf.BANK_ID)
        player_shares = etf.get_player_shareholding(player.id)
        nav = (bank_entity.cash_reserves or 0) + (bank_entity.asset_value or 0)
        
        # Check for system status flags
        qe_active = bank_entity.share_price < (etf.QE_TRIGGER_SHARE_PRICE or 0)
        is_insolvent = bank_entity.cash_reserves < 0

        # Get commodity data
        energy_held = inventory.get_item_quantity(etf.BANK_PLAYER_ID, etf.TARGET_COMMODITY)
        import market as market_mod
        market_price = market_mod.get_market_price(etf.TARGET_COMMODITY) or 0

        # Conditional UI elements - Keep these on one line or use multi-line string concatenation
        insolvent_html = f"""
        <div style='background: #450a0a; border: 1px solid #dc2626; color: #f87171; padding: 15px; border-radius: 4px; margin: 20px 0;'>
            <strong>⚠️ ETF INSOLVENT</strong><br>
            This ETF is currently insolvent. Shareholders may be subject to solvency levies.
        </div>""" if is_insolvent else ""

        qe_html = f"""
        <div style='background: #064e3b; border: 1px solid #10b981; color: #34d399; padding: 15px; border-radius: 4px; margin: 20px 0;'>
            <strong>🏦 QUANTITATIVE EASING ACTIVE</strong><br>
            The ETF is buying energy to restore asset value.
        </div>""" if qe_active else ""

        body = f"""
        <a href="/banks" style="color: #64748b; text-decoration: none;">← Banks</a>
        <h1 style="color: #38bdf8; margin: 10px 0;">{etf.BANK_NAME}</h1>
        <p style="color: #94a3b8; font-style: italic;">{etf.BANK_DESCRIPTION}</p>

        {insolvent_html}
        {qe_html}

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 20px;">
            <div style="background: #1e293b; padding: 15px; border-radius: 4px; border-left: 4px solid #38bdf8;">
                <h3 style="margin-top: 0; color: #64748b;">ETF Overview</h3>
                <p>Share Price: <span style="color: #38bdf8; font-family: monospace;">{fmt_usd(bank_entity.share_price, disp, precision=6)}</span></p>
                <p>Total Shares: {bank_entity.total_shares_issued:,}</p>
                <p>Market Cap: {fmt_usd(bank_entity.share_price * bank_entity.total_shares_issued, disp)}</p>
                <p>Net Asset Value: {fmt_usd(nav, disp)}</p>
                <p>Cash Reserves: {fmt_usd(bank_entity.cash_reserves, disp)}</p>
                <p>Commodity Backing: {fmt_usd(bank_entity.asset_value, disp)}</p>
            </div>

            <div style="background: #1e293b; padding: 15px; border-radius: 4px; border-left: 4px solid #f59e0b;">
                <h3 style="margin-top: 0; color: #64748b;">Energy Grid Status</h3>
                <p>Target Commodity: {etf.TARGET_COMMODITY.title()}</p>
                <p>Holdings: {energy_held:,.0f} units</p>
                <p>Market Price: {fmt_usd(market_price, disp)}</p>
                <p>Total Value: {fmt_usd(energy_held * market_price, disp)}</p>
            </div>
        </div>

        <div style="background: #1e293b; padding: 15px; border-radius: 4px; margin-top: 20px; border-left: 4px solid #10b981;">
            <h3 style="margin-top: 0; color: #64748b;">Your Position</h3>
            <p>Shares Owned: {player_shares["shares_owned"]:,}</p>
            <p>Market Value: {fmt_usd(player_shares["current_value"], disp)}</p>
            <p>Ownership: {player_shares["ownership_percentage"]:.4f}%</p>
        </div>

        <div style="margin-top: 20px; padding: 15px; background: #0f172a; border-radius: 4px;">
            <h3 style="margin-top: 0; color: #64748b;">ETF Strategy</h3>
            <ul style="color: #94a3b8; line-height: 1.6;">
                <li>Buys {etf.TARGET_COMMODITY} when price drops below {etf.BUY_PRICE_THRESHOLD*100:.0f}% of moving average</li>
                <li>Sells when inventory reaches {etf.SELL_INVENTORY_THRESHOLD*100:.0f}% of total market supply</li>
                <li>Annual holder fee: {etf.HOLDER_FEE_PER_TICK*31536000:.2f}%</li>
                <li>Stock splits at {fmt_usd(etf.SPLIT_PRICE_THRESHOLD, disp)} share price</li>
            </ul>
        </div>
        """
        return shell(etf.BANK_NAME, body, player.cash_balance, player.id)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return shell("ETF Error", f"Error loading Energy ETF: {e}", player.cash_balance, player.id)

# ==========================
# BROKERAGE FIRM UX ROUTES
# ==========================

@router.get("/banks/city-nav-etf", response_class=HTMLResponse)
def city_nav_etf_dashboard(session_token: Optional[str] = Cookie(None)):
    """City NAV ETF dashboard."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)

    try:
        import banks
        from banks import city_nav_etf as etf

        bank_entity = banks.get_bank_entity(etf.BANK_ID)
        player_shares = etf.get_player_shareholding(player.id)
        etf_info = etf.get_etf_info()

        nav = etf_info["nav"]
        share_price = etf_info["share_price"]
        land_value = etf_info["land_portfolio_value"]
        land_count = etf_info["land_plots_owned"]
        cash = etf_info["cash_reserves"]

        body = f"""
        <a href="/banks" style="color: #64748b; text-decoration: none;">← Banks</a>
        <h1 style="color: #38bdf8; margin: 10px 0;">{etf.BANK_NAME}</h1>
        <p style="color: #94a3b8; font-style: italic;">{etf.BANK_DESCRIPTION}</p>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 20px;">
            <div style="background: #1e293b; padding: 15px; border-radius: 4px; border-left: 4px solid #38bdf8;">
                <h3 style="margin-top: 0; color: #64748b;">ETF Overview</h3>
                <p>Share Price: <span style="color: #38bdf8; font-family: monospace;">{fmt_usd(share_price, disp, precision=10)}</span></p>
                <p>Total Shares: {etf.IPO_SHARES:,}</p>
                <p>Market Cap: {fmt_usd(share_price * etf.IPO_SHARES, disp)}</p>
                <p>Net Asset Value: {fmt_usd(nav, disp)}</p>
                <p>Cash Reserves: {fmt_usd(cash, disp)}</p>
                <p>Land Portfolio Value: {fmt_usd(land_value, disp)}</p>
                <p>Land Plots Owned: {land_count:,}</p>
            </div>

            <div style="background: #1e293b; padding: 15px; border-radius: 4px; border-left: 4px solid #22c55e;">
                <h3 style="margin-top: 0; color: #64748b;">Your Position</h3>
                <p>Shares Owned: {player_shares["shares_owned"]:,}</p>
                <p>Market Value: {fmt_usd(player_shares["current_value"], disp)}</p>
                <p>Ownership: {player_shares["ownership_percentage"]:.8f}%</p>
                <p style="color: #64748b; font-size: 0.85em; margin-top: 10px;">
                    No dividends are paid by this ETF. Returns come entirely from share price appreciation as the City NAV it tracks grows.
                </p>
            </div>
        </div>

        <div style="background: #1e293b; padding: 15px; border-radius: 4px; margin-top: 20px; border-left: 4px solid #f59e0b;">
            <h3 style="margin-top: 0; color: #64748b;">How This ETF Works</h3>
            <ul style="color: #94a3b8; line-height: 1.8; margin: 0; padding-left: 20px;">
                <li><strong style="color: #e2e8f0;">Purpose:</strong> Tracks the total Net Asset Value of every City on the map. As cities accumulate wealth, develop infrastructure, and grow populations, this ETF rises with them.</li>
                <li><strong style="color: #e2e8f0;">Backing asset:</strong> Land plots — this ETF buys and sells land from the open land market, not commodities. Its NAV = cash on hand + market value of all land it holds.</li>
                <li><strong style="color: #e2e8f0;">Peg mechanism:</strong> Share price is always <em>NAV ÷ total shares</em>. No dividends are ever paid — all gains are reflected in the share price.</li>
                <li><strong style="color: #e2e8f0;">Supply:</strong> Fixed forever at {etf.IPO_SHARES:,} shares (420 billion). No splits, no buybacks, no new issuance.</li>
                <li><strong style="color: #e2e8f0;">Seed capital:</strong> {fmt_usd(etf.SEED_CAPITAL, disp, precision=0)} — this ETF starts lean and grows only as it acquires land.</li>
                <li><strong style="color: #e2e8f0;">Land buying rule:</strong> Buys the cheapest available listings when cash exceeds {etf.CASH_RESERVE_RATIO*100:.0f}% of NAV (up to {etf.BUY_MAX_LISTINGS} plots per cycle).</li>
                <li><strong style="color: #e2e8f0;">Land selling rule:</strong> Lists plots for sale at {int(etf.LAND_SELL_MARKUP*100)}% of estimated value when land exceeds 90% of total NAV.</li>
                <li><strong style="color: #e2e8f0;">Land valuation:</strong> Each plot is valued at <em>monthly_tax × 120</em> (10-year capitalisation), or its most recent sale price — whichever is higher.</li>
                <li><strong style="color: #e2e8f0;">No dividends:</strong> This ETF never pays dividends. Returns are purely from price appreciation.</li>
            </ul>
        </div>

        <div style="margin-top: 15px; display: flex; gap: 10px;">
            <a href="/brokerage/trading?mode=etf" class="btn-orange">Trade Shares</a>
            <a href="/land-market" class="btn-blue">View Land Market</a>
        </div>
        """

        return shell(etf.BANK_NAME, body, player.cash_balance, player.id)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return shell("ETF Error", f"Error loading City NAV ETF: {e}", player.cash_balance, player.id)


@router.get("/banks/wbc50-index-fund", response_class=HTMLResponse)
def wbc50_index_fund_dashboard(session_token: Optional[str] = Cookie(None)):
    """WBC-50 Index Fund detail page."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)

    try:
        import banks
        from banks.wbc50_index_fund import (
            get_player_shareholding, BANK_ID, BANK_NAME, BANK_DESCRIPTION,
            TARGET_HOLDING_MIN, TARGET_HOLDING_MAX, TARGET_HOLDING,
            EXPENSE_RATIO_ANNUAL, SEED_CAPITAL, IPO_SHARES,
            BROKERAGE_TOPUP_PER_CYCLE, BROKERAGE_TOTAL_FUNDING_CAP,
            CASH_RESERVE_RATIO, REBALANCE_INTERVAL,
            get_wbc50_constituents, IndexFundHolding, get_db as fund_db,
            total_firm_funding,
        )

        entity       = banks.get_bank_entity(BANK_ID)
        player_pos   = get_player_shareholding(player.id)
        nav          = (entity.cash_reserves + entity.asset_value) if entity else 0.0
        share_price  = entity.share_price if entity else 0.0
        total_shares = entity.total_shares_issued if entity else IPO_SHARES

        # Build holdings table
        constituents = get_wbc50_constituents()
        const_map    = {c.id: c for c in constituents}
        db           = fund_db()
        try:
            holdings = db.query(IndexFundHolding).filter(
                IndexFundHolding.in_index == True,
                IndexFundHolding.shares_held > 0,
            ).order_by(IndexFundHolding.ticker).all()
        finally:
            db.close()

        holding_rows = ""
        for h in holdings:
            co = const_map.get(h.company_id)
            if co:
                mkt_val   = h.shares_held * co.current_price
                pct_held  = h.shares_held / co.shares_outstanding * 100 if co.shares_outstanding else 0
                port_wt   = mkt_val / entity.asset_value * 100 if entity.asset_value else 0
                holding_rows += (
                    f'<tr>'
                    f'<td style="font-weight:600;">{h.ticker}</td>'
                    f'<td style="color:#94a3b8;">{co.company_name}</td>'
                    f'<td>{fmt_usd(co.current_price, disp, precision=4)}</td>'
                    f'<td>{h.shares_held:,}</td>'
                    f'<td>{pct_held:.2f}%</td>'
                    f'<td>{fmt_usd(mkt_val, disp)}</td>'
                    f'<td>{port_wt:.2f}%</td>'
                    f'</tr>'
                )

        holdings_section = f"""
        <div class="card">
            <h3>Portfolio Holdings ({len(holdings)}/50 constituents)</h3>
            <div class="table-wrap">
                <table>
                    <tr>
                        <th>Ticker</th><th>Company</th><th>Price</th>
                        <th>Shares Held</th><th>% of Co.</th>
                        <th>Market Value</th><th>Portfolio Wt.</th>
                    </tr>
                    {holding_rows if holding_rows else '<tr><td colspan="7" style="color:#64748b;">No positions yet — awaiting first rebalance.</td></tr>'}
                </table>
            </div>
        </div>
        """ if True else ""

        body = f"""
        <a href="/banks" style="color:#38bdf8;">← Banks</a>
        <h1>{BANK_NAME}</h1>
        <p style="color:#64748b;">{BANK_DESCRIPTION}</p>

        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin:18px 0;">
            <div class="card" style="padding:14px;">
                <div style="color:#64748b;font-size:0.7rem;">SHARE PRICE</div>
                <div style="font-size:1.3rem;font-weight:700;">{fmt_usd(share_price, disp, precision=6)}</div>
            </div>
            <div class="card" style="padding:14px;">
                <div style="color:#64748b;font-size:0.7rem;">NAV</div>
                <div style="font-size:1.3rem;font-weight:700;">{fmt_usd(nav, disp)}</div>
            </div>
            <div class="card" style="padding:14px;">
                <div style="color:#64748b;font-size:0.7rem;">EQUITY VALUE</div>
                <div style="font-size:1.3rem;font-weight:700;">{fmt_usd(entity.asset_value if entity else 0, disp)}</div>
            </div>
            <div class="card" style="padding:14px;">
                <div style="color:#64748b;font-size:0.7rem;">CASH BUFFER</div>
                <div style="font-size:1.3rem;font-weight:700;">{fmt_usd(entity.cash_reserves if entity else 0, disp)}</div>
            </div>
            <div class="card" style="padding:14px;">
                <div style="color:#64748b;font-size:0.7rem;">TOTAL SHARES</div>
                <div style="font-size:1.3rem;font-weight:700;">{total_shares:,}</div>
            </div>
            <div class="card" style="padding:14px;">
                <div style="color:#64748b;font-size:0.7rem;">FIRM FUNDED</div>
                <div style="font-size:1.3rem;font-weight:700;">{fmt_usd(total_firm_funding, disp)}</div>
            </div>
        </div>

        <div class="card">
            <h3>Your Position</h3>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
                <div><b>Shares Owned:</b> {player_pos["shares_owned"]:,}</div>
                <div><b>Position Value:</b> {fmt_usd(player_pos["current_value"], disp)}</div>
                <div><b>Ownership:</b> {player_pos["ownership_percentage"]:.6f}%</div>
                <div><b>Avg Share Price:</b> {fmt_usd(share_price, disp, precision=6)}</div>
            </div>
            <div style="margin-top:12px;display:flex;gap:10px;">
                <a href="/brokerage/trading?mode=etf" class="btn-blue">Trade Shares</a>
            </div>
        </div>

        <div class="card">
            <h3>Fund Strategy</h3>
            <div style="font-size:0.8rem;color:#cbd5e1;line-height:1.8;">
                <div>• <b>Replication target:</b> {TARGET_HOLDING_MIN*100:.0f}–{TARGET_HOLDING_MAX*100:.0f}% of each WBC-50 constituent's outstanding shares (midpoint {TARGET_HOLDING*100:.1f}%)</div>
                <div>• <b>Weighting:</b> Market-cap proportional within the WBC-50</div>
                <div>• <b>Rebalance frequency:</b> Every {REBALANCE_INTERVAL} ticks (~60 min)</div>
                <div>• <b>Cash buffer:</b> ≥ {CASH_RESERVE_RATIO*100:.0f}% of NAV held liquid at all times</div>
                <div>• <b>Expense ratio:</b> {EXPENSE_RATIO_ANNUAL*100:.2f}% annual, collected every 3,600 ticks and paid to the Brokerage Firm</div>
                <div>• <b>Seed capital:</b> {fmt_usd(SEED_CAPITAL, disp)} from Brokerage Firm at launch</div>
                <div>• <b>Firm top-up:</b> Up to {fmt_usd(BROKERAGE_TOPUP_PER_CYCLE, disp)} per rebalance cycle, lifetime cap {fmt_usd(BROKERAGE_TOTAL_FUNDING_CAP, disp)}</div>
                <div>• <b>No dividends, no splits, no buybacks</b> — all returns flow through NAV</div>
            </div>
        </div>

        {holdings_section}
        """
        return shell(BANK_NAME, body, player.cash_balance, player.id)

    except Exception as e:
        import traceback; traceback.print_exc()
        return shell("ETF Error", f"Error loading WBC-50 Index Fund: {e}", player.cash_balance, player.id)


@router.get("/banks/brokerage-firm", response_class=HTMLResponse)
def brokerage_firm_dashboard(session_token: Optional[str] = Cookie(None)):
    """Main Brokerage Firm dashboard with player share ticker."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)

    try:
        from banks.brokerage_firm import (
            get_firm_entity, firm_is_solvent, get_player_credit, get_credit_tier,
            CompanyShares, ShareholderPosition, CommodityLoan, ShareLoan, BrokerageLien,
            MarginCall, CommodityLoanStatus, ShareLoanStatus, BANK_NAME, BANK_DESCRIPTION,
            BANK_PLAYER_ID, get_db as get_firm_db
        )
        
        firm = get_firm_entity()
        player_credit = get_player_credit(player.id)
        is_solvent = firm_is_solvent()
        
        db = get_firm_db()
        try:
            # Get player's equity positions
            equity_positions = db.query(ShareholderPosition).filter(
                ShareholderPosition.player_id == player.id,
                ShareholderPosition.shares_owned > 0
            ).all()
            
            # Get player's margin positions
            margin_positions = db.query(ShareholderPosition).filter(
                ShareholderPosition.player_id == player.id,
                ShareholderPosition.margin_debt > 0
            ).all()
            
            # Get player's active short positions
            short_positions = db.query(ShareLoan).filter(
                ShareLoan.borrower_player_id == player.id,
                ShareLoan.status == ShareLoanStatus.ACTIVE.value
            ).all()
            
            # Get player's commodity loans (as borrower)
            commodity_loans = db.query(CommodityLoan).filter(
                CommodityLoan.borrower_player_id == player.id,
                CommodityLoan.status.in_([CommodityLoanStatus.ACTIVE.value, CommodityLoanStatus.LATE.value])
            ).all()
            
            # Get player's brokerage liens
            liens = db.query(BrokerageLien).filter(
                BrokerageLien.player_id == player.id
            ).all()
            total_lien_debt = sum(l.principal + l.interest_accrued - l.total_paid for l in liens)
            
            # Get active margin calls
            margin_calls = db.query(MarginCall).filter(
                MarginCall.player_id == player.id,
                MarginCall.is_resolved == False
            ).all()
            
            # Get all public companies for ticker
            public_companies = db.query(CompanyShares).filter(
                CompanyShares.is_delisted == False
            ).all()
            
            # Calculate player's total portfolio value
            total_equity_value = 0.0
            for pos in equity_positions:
                company = db.query(CompanyShares).filter(CompanyShares.id == pos.company_shares_id).first()
                if company:
                    total_equity_value += pos.shares_owned * company.current_price
            
            total_margin_debt = sum(p.margin_debt + p.margin_interest_accrued for p in margin_positions)
            
        finally:
            db.close()
        
        # Build company ticker HTML
        ticker_items = []
        for company in public_companies:
            change_indicator = "▲" if company.current_price >= company.ipo_price else "▼"
            change_color = "#22c55e" if company.current_price >= company.ipo_price else "#ef4444"
            # Make ticker clickable
            ticker_items.append(
                f'<a href="/brokerage/trading?ticker={company.ticker_symbol}" style="color: {change_color}; text-decoration: none; font-weight: bold;">{company.ticker_symbol}</a>: {fmt_usd(company.current_price, disp)} {change_indicator}'
            )
        company_ticker = " &nbsp;│&nbsp; ".join(ticker_items) if ticker_items else "NO LISTED COMPANIES"
        
        # Credit tier badge colors
        tier_colors = {
            "prime": "#22c55e",
            "standard": "#38bdf8",
            "fair": "#f59e0b",
            "subprime": "#ef4444",
            "junk": "#7f1d1d"
        }
        tier_color = tier_colors.get(player_credit.tier, "#64748b")
        
        # Margin call warning
        margin_call_html = ""
        if margin_calls:
            total_required = sum(mc.amount_required for mc in margin_calls)
            margin_call_html = f'''
            <div class="card" style="border: 2px solid #ef4444; background: #450a0a;">
                <h3 style="color: #fca5a5;">&#128222; MARGIN CALL ACTIVE</h3>
                <p style="color: #fca5a5;">You must deposit {fmt_usd(total_required, disp)} or your positions will be liquidated.</p>
                <p style="color: #f87171; font-size: 0.9rem;">Deadline: {margin_calls[0].deadline.strftime("%Y-%m-%d %H:%M UTC")}</p>
                <form action="/api/brokerage/deposit-margin" method="post" style="margin-top: 12px; display: flex; gap: 10px; align-items: flex-end; flex-wrap: wrap;">
                    <div>
                        <label style="font-size: 0.85rem; color: #fca5a5; display: block; margin-bottom: 4px;">Deposit Amount ($)</label>
                        <input type="number" name="amount" min="0.01" step="0.01"
                               value="{total_required:.2f}"
                               style="background: #1a0505; border: 1px solid #ef4444; color: #fca5a5; padding: 8px 12px; border-radius: 4px; width: 180px;">
                    </div>
                    <button type="submit" style="background: #dc2626; color: #fff; border: none; padding: 9px 20px; border-radius: 4px; cursor: pointer; font-weight: bold;">
                        Deposit &amp; Cover Margin Call
                    </button>
                </form>
            </div>
            '''
        
        # Insolvency warning
        insolvency_html = ""
        if not is_solvent:
            insolvency_html = '''
            <div class="card" style="border: 2px solid #ef4444; background: #450a0a;">
                <h3 style="color: #fca5a5;">⚠️ FIRM INSOLVENT</h3>
                <p style="color: #fca5a5;">The Brokerage Firm is currently insolvent. Some operations may be suspended.</p>
            </div>
            '''
        
        body = f'''
        <!-- WPE Company Ticker (slower scroll) -->
        <div style="background: #0f172a; border: 1px solid #1e293b; padding: 8px 0; margin-bottom: 20px; overflow: hidden;">
            <div style="font-size: 0.75rem; color: #64748b; padding: 0 12px; margin-bottom: 4px;">WPE PLAYER EXCHANGE</div>
            <marquee scrollamount="8" style="font-size: 0.85rem; color: #e5e7eb;">
                {company_ticker} &nbsp;&nbsp;&nbsp; {company_ticker}
            </marquee>
        </div>
        
        <a href="/banks" style="color: #38bdf8;">← Banks</a>
        <h1>{BANK_NAME}</h1>
        <p style="color: #64748b;">{BANK_DESCRIPTION}</p>
        
        {insolvency_html}
        {margin_call_html}
        
        <!-- Quick Stats Row -->
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin: 20px 0;">
            <div class="card" style="text-align: center;">
                <div style="font-size: 0.8rem; color: #64748b;">CREDIT RATING</div>
                <div style="font-size: 1.8rem; font-weight: bold; color: {tier_color};">{player_credit.credit_score}</div>
                <div style="font-size: 0.75rem; color: {tier_color}; text-transform: uppercase;">{player_credit.tier}</div>
            </div>
            <div class="card" style="text-align: center;">
                <div style="font-size: 0.8rem; color: #64748b;">PORTFOLIO VALUE</div>
                <div style="font-size: 1.8rem; font-weight: bold; color: #38bdf8;">{fmt_usd(total_equity_value, disp, precision=0)}</div>
                <div style="font-size: 0.75rem; color: #64748b;">{len(equity_positions)} position(s)</div>
            </div>
            <div class="card" style="text-align: center;">
                <div style="font-size: 0.8rem; color: #64748b;">MARGIN DEBT</div>
                <div style="font-size: 1.8rem; font-weight: bold; color: {'#ef4444' if total_margin_debt > 0 else '#22c55e'};">{fmt_usd(total_margin_debt, disp, precision=0)}</div>
                <div style="font-size: 0.75rem; color: #64748b;">{len(margin_positions)} margin position(s)</div>
            </div>
            <div class="card" style="text-align: center;">
                <div style="font-size: 0.8rem; color: #64748b;">LIEN BALANCE</div>
                <div style="font-size: 1.8rem; font-weight: bold; color: {'#ef4444' if total_lien_debt > 0 else '#22c55e'};">{fmt_usd(total_lien_debt, disp, precision=0)}</div>
                <div style="font-size: 0.75rem; color: #64748b;">{len(liens)} active lien(s)</div>
            </div>
        </div>
        
        <!-- Firm Status -->
        <div class="card">
            <h3>Firm Status</h3>
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px;">
                <div>
                    <p><strong>Cash Reserves:</strong> {fmt_usd(firm.cash_reserves, disp)}</p>
                    <p><strong>Status:</strong> <span style="color: {'#22c55e' if is_solvent else '#ef4444'};">{'SOLVENT' if is_solvent else 'INSOLVENT'}</span></p>
                </div>
                <div>
                    <p><strong>IPO Underwriting:</strong> <span style="color: {'#22c55e' if firm.is_accepting_ipos else '#ef4444'};">{'ACTIVE' if firm.is_accepting_ipos else 'SUSPENDED'}</span></p>
                    <p><strong>Margin Trading:</strong> <span style="color: {'#22c55e' if firm.is_accepting_margin else '#ef4444'};">{'ACTIVE' if firm.is_accepting_margin else 'SUSPENDED'}</span></p>
                </div>
                <div>
                    <p><strong>Commodity Lending:</strong> <span style="color: {'#22c55e' if firm.is_accepting_lending else '#ef4444'};">{'ACTIVE' if firm.is_accepting_lending else 'SUSPENDED'}</span></p>
                    <p><strong>Your Max Leverage:</strong> {get_player_credit(player.id).credit_score}x based on credit</p>
                </div>
            </div>
        </div>
        
        <!-- Navigation Cards -->
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-top: 20px;">
            <div class="card">
                <h3>📈 WPE Trading</h3>
                <p style="color: #64748b; font-size: 0.9rem;">Buy and sell player company shares</p>
                <a href="/brokerage/trading" class="btn-blue" style="display: inline-block; margin-top: 10px;">Trade Equities</a>
            </div>
            <div class="card">
                <h3>🏢 IPO Center</h3>
                <p style="color: #64748b; font-size: 0.9rem;">Take your business public</p>
                <a href="/brokerage/ipo" class="btn-blue" style="display: inline-block; margin-top: 10px;">Launch IPO</a>
            </div>
            <div class="card">
                <h3>📊 My Portfolio</h3>
                <p style="color: #64748b; font-size: 0.9rem;">View your equity positions</p>
                <a href="/brokerage/portfolio" class="btn-blue" style="display: inline-block; margin-top: 10px;">View Holdings</a>
            </div>
            <div class="card">
                <h3>📉 Short Selling</h3>
                <p style="color: #64748b; font-size: 0.9rem;">Bet against player companies</p>
                <a href="/brokerage/shorts" class="btn-orange" style="display: inline-block; margin-top: 10px;">Short Stocks</a>
            </div>
            <div class="card">
                <h3>🌾 Commodity Lending</h3>
                <p style="color: #64748b; font-size: 0.9rem;">Borrow or lend commodities</p>
                <a href="/brokerage/commodities" class="btn-orange" style="display: inline-block; margin-top: 10px;">WCE Market</a>
            </div>
            <div class="card">
                <h3>💳 Credit & Liens</h3>
                <p style="color: #64748b; font-size: 0.9rem;">Your credit rating and debts</p>
                <a href="/brokerage/credit" class="btn-blue" style="display: inline-block; margin-top: 10px;">View Credit</a>
            </div>
            <div class="card">
                <h3>⚙️ Corporate Actions</h3>
                <p style="color: #64748b; font-size: 0.9rem;">Automate buybacks, splits, offerings</p>
                <a href="/corporate-actions/dashboard" class="btn-blue" style="display: inline-block; margin-top: 10px;">Manage Actions</a>
            </div>
            <div class="card">
                <h3>🏛 My Public Companies</h3>
                <p style="color: #64748b; font-size: 0.9rem;">Manage companies you've taken public</p>
                <a href="/brokerage/my-companies" class="btn-blue" style="display: inline-block; margin-top: 10px;">My Companies</a>
            </div>
            <div class="card">
                <h3>🗳 Governance</h3>
                <p style="color: #64748b; font-size: 0.9rem;">Propose and vote on company decisions</p>
                <a href="/brokerage/governance" class="btn-blue" style="display: inline-block; margin-top: 10px; background:#4c1d95;">Vote / Propose</a>
            </div>
        </div>
        
        <!-- Active Positions Summary -->
        <div class="card" style="margin-top: 20px;">
            <h3>Active Positions Summary</h3>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                <div>
                    <h4 style="color: #38bdf8; margin-bottom: 10px;">Short Positions ({len(short_positions)})</h4>
                    {generate_short_positions_summary(short_positions, disp) if short_positions else '<p style="color: #64748b;">No active short positions</p>'}
                </div>
                <div>
                    <h4 style="color: #f59e0b; margin-bottom: 10px;">Commodity Loans ({len(commodity_loans)})</h4>
                    {generate_commodity_loans_summary(commodity_loans) if commodity_loans else '<p style="color: #64748b;">No active commodity loans</p>'}
                </div>
            </div>
        </div>
        '''
        
        return shell(BANK_NAME, body, player.cash_balance, player.id)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return shell("Brokerage Firm", f"Error loading brokerage firm: {e}", player.cash_balance, player.id)


@router.get("/brokerage/trading", response_class=HTMLResponse)
def brokerage_trading_page(session_token: Optional[str] = Cookie(None), ticker: str = None, mode: str = "equity",
                           success: Optional[str] = None, error: Optional[str] = None):
    """WPE equity and ETF trading page."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)

    try:
        from banks.brokerage_firm import (
            CompanyShares, ShareholderPosition, get_player_credit,
            calculate_margin_multiplier, get_db as get_firm_db, BANK_PLAYER_ID
        )
        from banks.brokerage_order_book import (
            get_order_book_depth, get_recent_fills, OrderBook, OrderStatus,
            get_db as get_book_db
        )

        db = get_firm_db()
        try:
            # Get all public companies
            companies = db.query(CompanyShares).filter(
                CompanyShares.is_delisted == False
            ).order_by(CompanyShares.ticker_symbol).all()

            # Get player's positions
            player_positions = {
                pos.company_shares_id: pos
                for pos in db.query(ShareholderPosition).filter(
                    ShareholderPosition.player_id == player.id
                ).all()
            }

            # Selected company details
            selected_company = None
            if ticker:
                selected_company = db.query(CompanyShares).filter(
                    CompanyShares.ticker_symbol == ticker.upper(),
                    CompanyShares.is_delisted == False
                ).first()
            elif companies:
                selected_company = companies[0]

            player_credit = get_player_credit(player.id)

        finally:
            db.close()
        
        # Build company selector tabs
        company_tabs = '<div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 20px;">'
        for company in companies:
            is_selected = selected_company and company.id == selected_company.id
            tab_style = "background: #38bdf8; color: #020617;" if is_selected else "background: #1e293b; color: #94a3b8;"
            company_tabs += f'''
            <a href="/brokerage/trading?ticker={company.ticker_symbol}" 
               style="padding: 8px 16px; border-radius: 4px; text-decoration: none; {tab_style}">
                {company.ticker_symbol}
            </a>'''
        company_tabs += '</div>'
        
        if not selected_company:
            body = f'''
            <a href="/banks/brokerage-firm" style="color: #38bdf8;">← Brokerage Firm</a>
            <h1>WPE Trading Floor</h1>
            <p style="color: #64748b;">No companies are currently listed on the exchange.</p>
            <a href="/brokerage/ipo" class="btn-blue">Launch the First IPO</a>
            '''
            return shell("WPE Trading", body, player.cash_balance, player.id)

        # Get order book data for selected company
        order_book = get_order_book_depth(selected_company.id, depth=10)
        recent_trades = get_recent_fills(selected_company.id, limit=10)

        # Get player's pending orders for this company
        book_db = get_book_db()
        try:
            pending_orders = book_db.query(OrderBook).filter(
                OrderBook.player_id == player.id,
                OrderBook.company_shares_id == selected_company.id,
                OrderBook.status.in_([
                    OrderStatus.PENDING.value,
                    OrderStatus.PARTIAL.value
                ])
            ).order_by(OrderBook.created_at.desc()).all()
        finally:
            book_db.close()
        
        # Get player's position in selected company
        player_position = player_positions.get(selected_company.id)
        # shares_lent_out are locked as collateral for active short loans — they
        # cannot be sold until recalled/returned, matching get_player_shares() logic.
        player_shares = max(0, (player_position.shares_owned or 0) - (player_position.shares_lent_out or 0)) if player_position else 0
        player_cost_basis = player_position.average_cost_basis if player_position else 0
        
        # Calculate margin multiplier for this stock
        max_margin = calculate_margin_multiplier(player.id, selected_company.id)
        
        # Trading halted check
        is_halted = selected_company.trading_halted_until and datetime.utcnow() < selected_company.trading_halted_until
        
        # ===== MODERN TRADING DASHBOARD =====

        # Portfolio totals for summary bar
        total_portfolio_value = 0
        total_portfolio_cost = 0
        total_margin_debt = 0
        positions_data = []

        for company in companies:
            pos = player_positions.get(company.id)
            shares = pos.shares_owned if pos else 0
            cost_basis = pos.average_cost_basis if pos else 0
            mkt_val = shares * company.current_price
            cost_total = shares * cost_basis
            pl = mkt_val - cost_total if shares > 0 else 0
            margin_debt_val = 0
            if pos and hasattr(pos, 'margin_debt') and pos.margin_debt:
                margin_debt_val = pos.margin_debt

            total_portfolio_value += mkt_val
            total_portfolio_cost += cost_total
            total_margin_debt += margin_debt_val

            positions_data.append({
                'company': company,
                'shares': shares,
                'cost_basis': cost_basis,
                'mkt_val': mkt_val,
                'pl': pl,
                'is_selected': company.id == selected_company.id
            })

        total_pl = total_portfolio_value - total_portfolio_cost
        total_pl_pct = (total_pl / total_portfolio_cost * 100) if total_portfolio_cost > 0 else 0
        num_positions = sum(1 for p in positions_data if p['shares'] > 0)

        # Price change from IPO
        price_change = selected_company.current_price - selected_company.ipo_price
        price_change_pct = (price_change / selected_company.ipo_price * 100) if selected_company.ipo_price > 0 else 0
        change_color = "#22c55e" if price_change >= 0 else "#ef4444"
        change_sign = "+" if price_change >= 0 else ""

        # Player position metrics for selected stock
        player_mkt_value = player_shares * selected_company.current_price
        player_total_cost = player_shares * player_cost_basis
        player_pl = player_mkt_value - player_total_cost if player_shares > 0 else 0
        player_pl_pct = (player_pl / player_total_cost * 100) if player_total_cost > 0 else 0
        pl_color = "#22c55e" if player_pl >= 0 else "#ef4444"

        # Generate SVG sparkline from recent trades
        sparkline_svg = '<div style="height:80px;display:flex;align-items:center;justify-content:center;color:#334155;font-size:0.75rem;">No trade history</div>'
        if recent_trades:
            spark_prices = [t['price'] for t in reversed(recent_trades)]
            if len(spark_prices) >= 2:
                min_p = min(spark_prices)
                max_p = max(spark_prices)
                pr = max_p - min_p if max_p != min_p else 1
                pts = []
                area = []
                for i, p in enumerate(spark_prices):
                    x = 2 + i / (len(spark_prices) - 1) * 496
                    y = 2 + 76 - ((p - min_p) / pr * 76)
                    pts.append(f"{x:.1f},{y:.1f}")
                    area.append(f"{x:.1f},{y:.1f}")
                area.append("498,80")
                area.append("2,80")
                lc = "#22c55e" if spark_prices[-1] >= spark_prices[0] else "#ef4444"
                sparkline_svg = f'<svg viewBox="0 0 500 80" preserveAspectRatio="none" style="width:100%;height:80px;display:block;"><defs><linearGradient id="sfill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="{lc}" stop-opacity="0.2"/><stop offset="100%" stop-color="{lc}" stop-opacity="0.01"/></linearGradient></defs><polygon points="{" ".join(area)}" fill="url(#sfill)"/><polyline points="{" ".join(pts)}" fill="none" stroke="{lc}" stroke-width="1.5" stroke-linejoin="round"/></svg>'

        # Dividend display
        dividend_display = "None"
        if selected_company.dividend_config:
            div_parts = []
            for div in selected_company.dividend_config:
                dt = div.get("type", "")
                freq = div.get("frequency", "")
                if dt == "cash":
                    div_parts.append(f'Cash {div.get("amount",0)*100:.1f}% ({freq})')
                elif dt == "commodity":
                    div_parts.append(f'{div.get("item","item")}: {div.get("amount",0)}/{div.get("per_shares",100)}shs ({freq})')
                elif dt == "scrip":
                    div_parts.append(f'Stock {div.get("rate",0)*100:.1f}% ({freq})')
            if div_parts:
                dividend_display = " | ".join(div_parts)

        # Build positions sidebar HTML
        positions_html = ""
        for pd_item in positions_data:
            c = pd_item['company']
            is_sel = pd_item['is_selected']
            bg = "#1e293b" if is_sel else "transparent"
            bl = "3px solid #38bdf8" if is_sel else "3px solid transparent"
            shares_txt = f"{pd_item['shares']:,} shs" if pd_item['shares'] > 0 else ""
            pl_txt = ""
            plc = "#64748b"
            if pd_item['shares'] > 0 and pd_item['cost_basis'] > 0:
                plc = "#22c55e" if pd_item['pl'] >= 0 else "#ef4444"
                pl_txt = f"{'+'if pd_item['pl']>=0 else ''}{fmt_usd(pd_item['pl'], disp)}"
            positions_html += f'<a href="/brokerage/trading?ticker={c.ticker_symbol}" style="display:block;padding:8px 10px;border-left:{bl};background:{bg};text-decoration:none;color:#e5e7eb;">'
            positions_html += f'<div style="display:flex;justify-content:space-between;align-items:baseline;"><span style="font-weight:{"700" if is_sel else "500"};font-size:0.85rem;">{c.ticker_symbol}</span><span style="font-size:0.8rem;color:#94a3b8;">{fmt_usd(c.current_price, disp)}</span></div>'
            if shares_txt or pl_txt:
                positions_html += f'<div style="display:flex;justify-content:space-between;margin-top:2px;font-size:0.7rem;"><span style="color:#64748b;">{shares_txt}</span><span style="color:{plc};">{pl_txt}</span></div>'
            positions_html += '</a>'

        # Build order book depth ladder
        spread = order_book['spread']
        spread_pct = order_book['spread_pct']
        all_bq = [q for _, q in order_book['bids']] + [q for _, q in order_book['asks']]
        max_bq = max(all_bq) if all_bq else 1

        ob_html = '<div style="font-size:0.7rem;color:#475569;display:grid;grid-template-columns:1fr 1fr;padding:2px 8px;margin-bottom:4px;"><span>PRICE</span><span style="text-align:right;">QTY</span></div>'
        if order_book['asks']:
            for price, qty in reversed(order_book['asks']):
                bw = qty / max_bq * 100
                ob_html += f'<div style="position:relative;padding:2px 8px;display:grid;grid-template-columns:1fr 1fr;font-size:0.8rem;"><div style="position:absolute;right:0;top:0;bottom:0;width:{bw:.0f}%;background:rgba(239,68,68,0.1);"></div><span style="color:#ef4444;position:relative;">{fmt_usd(price, disp, precision=4)}</span><span style="text-align:right;color:#94a3b8;position:relative;">{qty:,}</span></div>'
        else:
            ob_html += '<div style="padding:4px 8px;color:#334155;font-size:0.75rem;text-align:center;">No asks</div>'
        ob_html += f'<div style="padding:4px 8px;text-align:center;font-size:0.7rem;color:#64748b;border-top:1px solid #1e293b;border-bottom:1px solid #1e293b;background:#0a0f1a;">Spread {fmt_usd(spread, disp, precision=4)} ({spread_pct:.2f}%)</div>'
        if order_book['bids']:
            for price, qty in order_book['bids']:
                bw = qty / max_bq * 100
                ob_html += f'<div style="position:relative;padding:2px 8px;display:grid;grid-template-columns:1fr 1fr;font-size:0.8rem;"><div style="position:absolute;right:0;top:0;bottom:0;width:{bw:.0f}%;background:rgba(34,197,94,0.1);"></div><span style="color:#22c55e;position:relative;">{fmt_usd(price, disp, precision=4)}</span><span style="text-align:right;color:#94a3b8;position:relative;">{qty:,}</span></div>'
        else:
            ob_html += '<div style="padding:4px 8px;color:#334155;font-size:0.75rem;text-align:center;">No bids</div>'

        # Build recent trades (time & sales)
        trades_html = ""
        if recent_trades:
            prev_price = None
            for trade in recent_trades:
                trade_time = trade.get('timestamp', '')
                time_str = ""
                if isinstance(trade_time, str):
                    try:
                        trade_dt = datetime.fromisoformat(trade_time.replace('Z', '+00:00'))
                        time_str = trade_dt.strftime("%H:%M")
                    except:
                        time_str = ""
                elif trade_time:
                    time_str = trade_time.strftime("%H:%M")
                tc = "#94a3b8"
                if prev_price is not None:
                    tc = "#22c55e" if trade['price'] >= prev_price else "#ef4444"
                prev_price = trade['price']
                trades_html += f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr;font-size:0.8rem;padding:2px 8px;"><span style="color:{tc};">{fmt_usd(trade["price"], disp, precision=4)}</span><span style="text-align:right;color:#94a3b8;">{trade["quantity"]:,}</span><span style="text-align:right;color:#475569;">{time_str}</span></div>'
        else:
            trades_html = '<div style="padding:8px;color:#334155;font-size:0.75rem;text-align:center;">No trades yet</div>'

        # Build pending orders
        pending_html = ""
        if pending_orders:
            pending_html = f'<div style="margin-top:12px;"><div style="font-size:0.7rem;color:#64748b;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:6px;padding:0 4px;">Open Orders ({len(pending_orders)})</div>'
            for order in pending_orders:
                sc = "#22c55e" if order.order_side == "BUY" else "#ef4444"
                pd_str = f"{fmt_usd(order.limit_price, disp, precision=4)}" if order.limit_price else "MKT"
                rem = order.quantity - order.filled_quantity
                pending_html += f'<div style="display:flex;justify-content:space-between;align-items:center;padding:5px 4px;border-top:1px solid #0f172a;font-size:0.8rem;"><div><span style="color:{sc};font-weight:600;">{order.order_side}</span> <span style="color:#94a3b8;">{rem:,} @ {pd_str}</span></div><form action="/api/brokerage/cancel-order" method="post" style="display:inline;margin:0;"><input type="hidden" name="order_id" value="{order.id}"><button type="submit" style="background:none;border:1px solid #334155;color:#94a3b8;padding:1px 6px;font-size:0.7rem;cursor:pointer;">X</button></form></div>'
            pending_html += '</div>'

        # Halted banner
        halted_html = ""
        if is_halted:
            halted_html = f'<div style="background:#451a03;border:1px solid #f59e0b;padding:8px 12px;font-size:0.8rem;color:#fbbf24;text-align:center;margin-bottom:12px;">TRADING HALTED - Circuit breaker until {selected_company.trading_halted_until.strftime("%H:%M UTC")}</div>'

        # Margin debt HTML for summary bar
        margin_debt_html = f"<div><span class='td-label'>Margin Debt</span><div style='color:#f59e0b;font-size:0.95rem;'>{fmt_usd(total_margin_debt, disp)}</div></div>" if total_margin_debt > 0 else ""

        # Dashboard CSS (built as regular string to avoid f-string brace conflicts)
        td_css = '<style>'
        td_css += '.container{max-width:1440px!important;}'
        td_css += '.td-layout{display:grid;grid-template-columns:220px 1fr 280px;gap:12px;margin-top:12px;}'
        td_css += '.td-sidebar{background:#0f172a;border:1px solid #1e293b;overflow-y:auto;max-height:calc(100vh - 200px);}'
        td_css += '.td-main{min-width:0;}'
        td_css += '.td-panel{background:#0f172a;border:1px solid #1e293b;padding:14px;}'
        td_css += '.td-section{background:#0f172a;border:1px solid #1e293b;padding:12px;margin-bottom:12px;}'
        td_css += '.td-label{color:#64748b;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.5px;}'
        td_css += '#td-tab-buy,#td-tab-sell{display:none;}'
        td_css += '.td-buy-panel,.td-sell-panel{display:none;}'
        td_css += '#td-tab-buy:checked~.td-buy-panel{display:block;}'
        td_css += '#td-tab-sell:checked~.td-sell-panel{display:block;}'
        td_css += '#td-tab-buy:checked~.td-tab-bar .td-tab-buy{background:#16a34a;color:#fff;}'
        td_css += '#td-tab-sell:checked~.td-tab-bar .td-tab-sell{background:#dc2626;color:#fff;}'
        td_css += '.td-input{width:100%;padding:8px;background:#020617;border:1px solid #1e293b;color:#e5e7eb;font-size:0.85rem;font-family:inherit;}'
        td_css += '.td-input:focus{border-color:#38bdf8;outline:none;}'
        td_css += '@media(max-width:1024px){.td-layout{grid-template-columns:1fr!important;}.td-sidebar{max-height:none;overflow-x:auto;white-space:nowrap;display:flex;}.td-sidebar>a{min-width:140px;white-space:normal;}}'
        td_css += '</style>'

        # ── ETF mode ─────────────────────────────────────────────────────────────
        if mode == "etf":
            etf_configs = [
                ("apple_seeds_etf",   "Apple Seeds ETF",      "apple_seeds_etf_shares",   "🍎"),
                ("energy_etf",        "Energy ETF",           "energy_etf_shares",         "⚡"),
                ("city_nav_etf",      "City NAV ETF",         "city_nav_etf_shares",       "🏙️"),
                ("land_bank",         "Land Bank",            "land_bank_shares",           "🏦"),
                ("wbc50_index_fund",  "WBC-50 Index Fund",    "wbc50_index_fund_shares",   "📈"),
            ]
            import banks as _banks_mod
            import inventory as _inv_mod
            import market as _mkt_mod

            fund_cards = ""
            for bank_id, name, share_item, icon in etf_configs:
                try:
                    be = _banks_mod.get_bank_entity(bank_id)
                    if not be:
                        continue
                    your_shares = _inv_mod.get_item_quantity(player.id, share_item)
                    mkt_price   = _mkt_mod.get_market_price(share_item)
                    nav         = (be.cash_reserves or 0) + (be.asset_value or 0)
                    mkt_price_display = fmt_usd(mkt_price, disp, precision=6) if mkt_price else "—"
                    your_value  = fmt_usd(your_shares * (mkt_price or be.share_price), disp)
                    nav_display = fmt_usd(nav, disp)
                    fund_cards += f'''
                    <div class="card" style="border-top:3px solid #86efac;">
                        <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px;">
                            <div>
                                <h3 style="margin:0;">{icon} {name}</h3>
                                <p style="color:#64748b;font-size:.8rem;margin:4px 0 0;">{be.description or ""}</p>
                            </div>
                            <a href="/banks/{bank_id.replace("_","-")}" class="btn-blue" style="font-size:.75rem;">Details</a>
                        </div>
                        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:14px 0;">
                            <div><div style="color:#64748b;font-size:.75rem;">Market Price</div>
                                 <div style="font-weight:bold;color:#22c55e;">{mkt_price_display}</div></div>
                            <div><div style="color:#64748b;font-size:.75rem;">NAV</div>
                                 <div style="font-weight:bold;">{nav_display}</div></div>
                            <div><div style="color:#64748b;font-size:.75rem;">Your Shares</div>
                                 <div style="font-weight:bold;color:#38bdf8;">{your_shares:,.4f}
                                     <span style="font-size:.7rem;color:#64748b;">({your_value})</span></div></div>
                        </div>
                        <div style="display:flex;gap:12px;flex-wrap:wrap;">
                            <form action="/api/brokerage/etf-order" method="post"
                                  style="display:flex;gap:6px;align-items:flex-end;flex-wrap:wrap;">
                                <input type="hidden" name="item_type"   value="{share_item}">
                                <input type="hidden" name="order_type"  value="buy">
                                <div>
                                    <label style="color:#94a3b8;font-size:.72rem;display:block;margin-bottom:2px;">Qty</label>
                                    <input type="number" name="quantity" min="1" step="1" value="100"
                                           style="width:90px;background:#0f172a;color:#e5e7eb;border:1px solid #334155;padding:5px 8px;border-radius:3px;font-family:inherit;">
                                </div>
                                <div>
                                    <label style="color:#94a3b8;font-size:.72rem;display:block;margin-bottom:2px;">Limit Price ({disp["symbol"]})</label>
                                    <input type="number" name="price" min="0.000001" step="0.000001"
                                           value="{round((mkt_price or be.share_price) / disp["usd_per_unit"], 6)}"
                                           style="width:120px;background:#0f172a;color:#e5e7eb;border:1px solid #334155;padding:5px 8px;border-radius:3px;font-family:inherit;">
                                </div>
                                <button type="submit" style="background:#22c55e;color:#020617;border:none;padding:7px 14px;border-radius:3px;cursor:pointer;font-weight:bold;font-family:inherit;">Buy</button>
                            </form>
                            <form action="/api/brokerage/etf-order" method="post"
                                  style="display:flex;gap:6px;align-items:flex-end;flex-wrap:wrap;">
                                <input type="hidden" name="item_type"   value="{share_item}">
                                <input type="hidden" name="order_type"  value="sell">
                                <div>
                                    <label style="color:#94a3b8;font-size:.72rem;display:block;margin-bottom:2px;">Qty</label>
                                    <input type="number" name="quantity" min="1" step="1" value="100"
                                           style="width:90px;background:#0f172a;color:#e5e7eb;border:1px solid #334155;padding:5px 8px;border-radius:3px;font-family:inherit;">
                                </div>
                                <div>
                                    <label style="color:#94a3b8;font-size:.72rem;display:block;margin-bottom:2px;">Limit Price ({disp["symbol"]})</label>
                                    <input type="number" name="price" min="0.000001" step="0.000001"
                                           value="{round((mkt_price or be.share_price) / disp["usd_per_unit"], 6)}"
                                           style="width:120px;background:#0f172a;color:#e5e7eb;border:1px solid #334155;padding:5px 8px;border-radius:3px;font-family:inherit;">
                                </div>
                                <button type="submit" style="background:#ef4444;color:#fff;border:none;padding:7px 14px;border-radius:3px;cursor:pointer;font-weight:bold;font-family:inherit;">Sell</button>
                            </form>
                        </div>
                    </div>'''
                except Exception:
                    continue

            etf_body = f'''
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
                <a href="/banks/brokerage-firm" style="color:#38bdf8;font-size:.8rem;">&larr; Brokerage Firm</a>
                <span style="font-size:.85rem;color:#94a3b8;font-weight:600;">WPE Trading Floor</span>
            </div>
            <!-- Mode tabs -->
            <div style="display:flex;gap:8px;margin-bottom:16px;">
                <a href="/brokerage/trading"
                   style="padding:7px 18px;border-radius:4px;text-decoration:none;background:#1e293b;color:#94a3b8;font-size:.8rem;">
                    WPE Equities
                </a>
                <a href="/brokerage/trading?mode=etf"
                   style="padding:7px 18px;border-radius:4px;text-decoration:none;background:#22c55e;color:#020617;font-size:.8rem;font-weight:bold;">
                    ETF Funds
                </a>
            </div>
            <h2 style="margin:0 0 4px;">ETF Fund Trading</h2>
            <p style="color:#64748b;font-size:.85rem;margin:0 0 16px;">
                Place limit orders on ETF fund shares via the ETF Trading Floor.
            </p>
            {fund_cards}
            '''
            return shell("ETF Trading", etf_body, player.cash_balance, player.id)
        # ─────────────────────────────────────────────────────────────────────────

        # Assemble the full dashboard body
        from html import escape as html_escape
        _alert_banner = ""
        _TRADING_MSGS = {
            "buy_order_placed":  ("Order placed.", True),
            "sell_order_placed": ("Order placed.", True),
            "buy_failed":        ("Buy order failed. Check your balance and order size.", False),
            "sell_failed":       ("Sell order failed. You may have exceeded the quantity available to sell, or the order was rejected by the exchange.", False),
        }
        if success and success in _TRADING_MSGS:
            _txt, _ = _TRADING_MSGS[success]
            _alert_banner = f'<div style="background:#14532d;color:#86efac;padding:8px 12px;border-radius:4px;margin-bottom:10px;font-size:0.8rem;">{_txt}</div>'
        elif error and error in _TRADING_MSGS:
            _txt, _ = _TRADING_MSGS[error]
            _alert_banner = f'<div style="background:#7f1d1d;color:#fca5a5;padding:8px 12px;border-radius:4px;margin-bottom:10px;font-size:0.8rem;">{_txt}</div>'
        elif error:
            _alert_banner = f'<div style="background:#7f1d1d;color:#fca5a5;padding:8px 12px;border-radius:4px;margin-bottom:10px;font-size:0.8rem;">{html_escape(error)}</div>'

        body = td_css + f'''
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px;">
            <a href="/banks/brokerage-firm" style="color:#38bdf8;font-size:0.8rem;">&larr; Brokerage Firm</a>
            <span style="font-size:0.85rem;color:#94a3b8;font-weight:600;">WPE Trading Floor</span>
        </div>
        {_alert_banner}
        <!-- Mode tabs -->
        <div style="display:flex;gap:8px;margin-bottom:12px;">
            <a href="/brokerage/trading"
               style="padding:7px 18px;border-radius:4px;text-decoration:none;background:#38bdf8;color:#020617;font-size:.8rem;font-weight:bold;">
                WPE Equities
            </a>
            <a href="/brokerage/trading?mode=etf"
               style="padding:7px 18px;border-radius:4px;text-decoration:none;background:#1e293b;color:#94a3b8;font-size:.8rem;">
                ETF Funds
            </a>
        </div>

        <!-- Portfolio Summary Bar -->
        <div style="display:flex;gap:24px;padding:10px 16px;background:#0f172a;border:1px solid #1e293b;font-size:0.8rem;flex-wrap:wrap;">
            <div>
                <span class="td-label">Portfolio Value</span>
                <div style="color:#e5e7eb;font-size:0.95rem;font-weight:600;">{fmt_usd(total_portfolio_value, disp)}</div>
            </div>
            <div>
                <span class="td-label">Total P/L</span>
                <div style="color:{"#22c55e" if total_pl >= 0 else "#ef4444"};font-size:0.95rem;font-weight:600;">{"+" if total_pl >= 0 else ""}{fmt_usd(total_pl, disp)} <span style="font-size:0.75rem;">({total_pl_pct:+.1f}%)</span></div>
            </div>
            <div>
                <span class="td-label">Buying Power</span>
                <div style="color:#22c55e;font-size:0.95rem;font-weight:600;">{fmt_usd(player.cash_balance, disp)}</div>
            </div>
            <div>
                <span class="td-label">Positions</span>
                <div style="color:#e5e7eb;font-size:0.95rem;">{num_positions} / {len(companies)}</div>
            </div>
            {margin_debt_html}
        </div>

        {halted_html}

        <!-- 3-Column Trading Layout -->
        <div class="td-layout">
            <!-- LEFT: Positions / Watchlist Sidebar -->
            <div class="td-sidebar">
                <div style="padding:8px 10px;border-bottom:1px solid #1e293b;font-size:0.7rem;color:#64748b;text-transform:uppercase;letter-spacing:0.5px;">
                    Watchlist &middot; {len(companies)} Listed
                </div>
                {positions_html}
            </div>

            <!-- CENTER: Stock Detail -->
            <div class="td-main">
                <!-- Price Header -->
                <div class="td-section" style="margin-bottom:0;border-bottom:none;">
                    <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px;">
                        <div>
                            <div style="font-size:1.1rem;font-weight:700;color:#e5e7eb;">{selected_company.company_name}</div>
                            <div style="font-size:0.75rem;color:#64748b;margin-top:2px;">
                                {selected_company.ticker_symbol} &middot; Class {selected_company.share_class}{" &middot; TBTF" if selected_company.is_tbtf else ""}
                                &nbsp;&middot;&nbsp; <a href="/brokerage/governance?company_id={selected_company.id}" style="color:#a78bfa;font-size:0.75rem;">🗳 Governance</a>
                            </div>
                        </div>
                        <div style="text-align:right;">
                            <div style="font-size:1.6rem;font-weight:700;color:#38bdf8;">{fmt_usd(selected_company.current_price, disp, precision=4)}</div>
                            <div style="font-size:0.8rem;color:{change_color};">
                                {change_sign}{fmt_usd(price_change, disp, precision=4)} ({price_change_pct:+.2f}%) <span style="color:#475569;">from IPO</span>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Sparkline Chart -->
                <div class="td-section" style="margin-top:0;border-top:none;padding-top:0;">
                    {sparkline_svg}
                </div>

                <!-- Key Stats Grid -->
                <div class="td-section">
                    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;">
                        <div><div class="td-label">Market Cap</div><div style="font-size:0.9rem;">{fmt_usd(selected_company.current_price * selected_company.shares_outstanding, disp, precision=0)}</div></div>
                        <div><div class="td-label">Shares Out</div><div style="font-size:0.9rem;">{selected_company.shares_outstanding:,}</div></div>
                        <div><div class="td-label">Float</div><div style="font-size:0.9rem;">{selected_company.shares_in_float:,}</div></div>
                        <div><div class="td-label">52W Range</div><div style="font-size:0.9rem;">{fmt_usd(selected_company.low_52_week, disp)} &mdash; {fmt_usd(selected_company.high_52_week, disp)}</div></div>
                        <div><div class="td-label">Volume Today</div><div style="font-size:0.9rem;">{selected_company.volume_today:,}</div></div>
                        <div><div class="td-label">Dividends</div><div style="font-size:0.85rem;">{dividend_display}</div></div>
                    </div>
                </div>

                <!-- Depth of Market + Time & Sales -->
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
                    <div class="td-section" style="margin-bottom:0;">
                        <div style="font-size:0.7rem;color:#64748b;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:6px;">Depth of Market</div>
                        {ob_html}
                    </div>
                    <div class="td-section" style="margin-bottom:0;">
                        <div style="font-size:0.7rem;color:#64748b;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:6px;">Time &amp; Sales</div>
                        <div style="font-size:0.7rem;color:#475569;display:grid;grid-template-columns:1fr 1fr 1fr;padding:2px 8px;margin-bottom:4px;"><span>PRICE</span><span style="text-align:right;">QTY</span><span style="text-align:right;">TIME</span></div>
                        {trades_html}
                    </div>
                </div>
            </div>

            <!-- RIGHT: Trade Panel -->
            <div class="td-panel">
                <!-- Position Summary -->
                <div style="margin-bottom:12px;">
                    <div style="font-size:0.7rem;color:#64748b;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:8px;">Your Position &mdash; {selected_company.ticker_symbol}</div>
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:0.8rem;">
                        <div><span style="color:#64748b;">Shares</span><div style="color:#38bdf8;font-size:1rem;font-weight:600;">{player_shares:,}</div></div>
                        <div><span style="color:#64748b;">Value</span><div style="font-size:1rem;">{fmt_usd(player_mkt_value, disp)}</div></div>
                        <div><span style="color:#64748b;">Avg Cost</span><div>{fmt_usd(player_cost_basis, disp, precision=4)}</div></div>
                        <div><span style="color:#64748b;">P/L</span><div style="color:{pl_color};font-weight:600;">{"+" if player_pl >= 0 else ""}{fmt_usd(player_pl, disp)}</div></div>
                    </div>
                </div>

                <div style="border-top:1px solid #1e293b;padding-top:12px;">
                    <!-- CSS-Only Buy/Sell Tab Toggle -->
                    <input type="radio" id="td-tab-buy" name="td-trade-tab" checked>
                    <input type="radio" id="td-tab-sell" name="td-trade-tab">
                    <div class="td-tab-bar" style="display:grid;grid-template-columns:1fr 1fr;margin-bottom:12px;">
                        <label for="td-tab-buy" class="td-tab-buy" style="padding:6px;text-align:center;cursor:pointer;font-size:0.85rem;font-weight:600;background:#1e293b;color:#64748b;border:1px solid #1e293b;">Buy</label>
                        <label for="td-tab-sell" class="td-tab-sell" style="padding:6px;text-align:center;cursor:pointer;font-size:0.85rem;font-weight:600;background:#1e293b;color:#64748b;border:1px solid #1e293b;">Sell</label>
                    </div>

                    <!-- Buy Form -->
                    <div class="td-buy-panel">
                        <form action="/api/brokerage/buy" method="post">
                            <input type="hidden" name="company_id" value="{selected_company.id}">
                            <div style="margin-bottom:10px;">
                                <label style="display:block;margin-bottom:4px;color:#94a3b8;font-size:0.8rem;">Quantity</label>
                                <input type="number" name="quantity" min="1" required class="td-input" placeholder="Shares">
                            </div>
                            <div style="margin-bottom:10px;">
                                <label style="display:block;margin-bottom:4px;color:#94a3b8;font-size:0.8rem;">Limit Price</label>
                                <input type="number" name="limit_price" step="0.0001" class="td-input" placeholder="Market @ {fmt_usd(selected_company.current_price, disp, precision=4)}">
                            </div>
                            <div style="margin-bottom:10px;">
                                <label style="display:flex;align-items:center;gap:6px;color:#94a3b8;font-size:0.8rem;">
                                    <input type="checkbox" name="use_margin" value="1">
                                    Margin ({max_margin:.1f}x)
                                </label>
                                <div style="font-size:0.7rem;color:#475569;margin-top:2px;">
                                    Credit: {player_credit.credit_score} ({player_credit.tier.upper()})
                                </div>
                            </div>
                            <button type="submit" style="width:100%;padding:10px;background:#16a34a;color:#fff;border:none;font-size:0.85rem;font-weight:600;cursor:pointer;" {"disabled" if is_halted else ""}>
                                Buy {selected_company.ticker_symbol}
                            </button>
                        </form>
                    </div>

                    <!-- Sell Form -->
                    <div class="td-sell-panel">
                        <form action="/api/brokerage/sell" method="post">
                            <input type="hidden" name="company_id" value="{selected_company.id}">
                            <div style="margin-bottom:10px;">
                                <label style="display:block;margin-bottom:4px;color:#94a3b8;font-size:0.8rem;">Quantity</label>
                                <input type="number" name="quantity" min="1" max="{player_shares}" required class="td-input" placeholder="Max: {player_shares:,}">
                            </div>
                            <div style="margin-bottom:10px;">
                                <label style="display:block;margin-bottom:4px;color:#94a3b8;font-size:0.8rem;">Limit Price</label>
                                <input type="number" name="limit_price" step="0.0001" class="td-input" placeholder="Market @ {fmt_usd(selected_company.current_price, disp, precision=4)}">
                            </div>
                            <div style="font-size:0.75rem;color:#64748b;margin-bottom:10px;">
                                Available: {player_shares:,} shares
                            </div>
                            <button type="submit" style="width:100%;padding:10px;background:#dc2626;color:#fff;border:none;font-size:0.85rem;font-weight:600;cursor:pointer;" {"disabled" if is_halted or player_shares == 0 else ""}>
                                Sell {selected_company.ticker_symbol}
                            </button>
                        </form>
                    </div>
                </div>

                {pending_html}

                <!-- Short Selling -->
                <div style="margin-top:12px;padding-top:12px;border-top:1px solid #1e293b;">
                    <a href="/brokerage/shorts?ticker={selected_company.ticker_symbol}" style="display:block;text-align:center;padding:6px;border:1px solid #f59e0b;color:#f59e0b;font-size:0.8rem;text-decoration:none;">
                        Short {selected_company.ticker_symbol}
                    </a>
                </div>
            </div>
        </div>
        '''

        return shell(f"Trade {selected_company.ticker_symbol}", body, player.cash_balance, player.id)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return shell("WPE Trading", f"Error: {e}", player.cash_balance, player.id)


# The helper functions need to be INSIDE the route handler

@router.get("/brokerage/ipo", response_class=HTMLResponse)
def brokerage_ipo_page(session_token: Optional[str] = Cookie(None), error: Optional[str] = None):
    """IPO creation page - redesigned for player holding companies."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)

    try:
        from banks.brokerage_firm import (
            get_firm_entity, IPO_CONFIG, IPOType,
            calculate_player_company_valuation, CompanyShares,
            calculate_delisting_cost, get_db as get_firm_db
        )
        from html import escape as html_escape

        firm = get_firm_entity()

        # Check if player already has a public company
        firm_db = get_firm_db()
        try:
            existing_company = firm_db.query(CompanyShares).filter(
                CompanyShares.founder_id == player.id,
                CompanyShares.is_delisted == False
            ).first()
        finally:
            firm_db.close()

        if existing_company:
            # Player already has a public company - show Go Private option
            cost_info, cost_err = calculate_delisting_cost(existing_company.id)
            if cost_info:
                go_private_html = f'''
                <div class="card" style="border-left: 4px solid #ef4444; margin-top: 20px;">
                    <h3>Go Private</h3>
                    <p style="color: #94a3b8; margin-bottom: 15px;">
                        Buy back all outstanding public shares and delist from the exchange.
                        Shareholders will be paid a 10% premium over the current market price.
                    </p>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 15px;">
                        <div>
                            <div style="font-size: 0.8rem; color: #64748b;">PUBLIC SHARES TO BUY BACK</div>
                            <div style="font-size: 1.3rem; font-weight: bold;">{cost_info["public_shares"]:,}</div>
                        </div>
                        <div>
                            <div style="font-size: 0.8rem; color: #64748b;">BUYBACK PRICE (10% PREMIUM)</div>
                            <div style="font-size: 1.3rem; font-weight: bold;">{fmt_usd(cost_info["buyback_price_per_share"], disp)}/share</div>
                        </div>
                        <div>
                            <div style="font-size: 0.8rem; color: #64748b;">SHARE BUYBACK COST</div>
                            <div style="font-size: 1.3rem; font-weight: bold;">{fmt_usd(cost_info["buyback_cost"], disp, precision=0)}</div>
                        </div>
                        <div>
                            <div style="font-size: 0.8rem; color: #64748b;">DELISTING FEE (2% OF MARKET CAP)</div>
                            <div style="font-size: 1.3rem; font-weight: bold;">{fmt_usd(cost_info["delisting_fee"], disp, precision=0)}</div>
                        </div>
                    </div>
                    <div style="background: #0f172a; padding: 12px; border-radius: 8px; margin-bottom: 15px;">
                        <div style="display: flex; justify-content: space-between;">
                            <span style="color: #94a3b8; font-weight: bold;">TOTAL COST TO GO PRIVATE</span>
                            <span style="color: #ef4444; font-weight: bold; font-size: 1.2rem;">{fmt_usd(cost_info["total_cost"], disp, precision=0)}</span>
                        </div>
                    </div>
                    <form action="/api/brokerage/go-private" method="post"
                          onsubmit="return confirm('Are you sure? This will cost {fmt_usd(cost_info["total_cost"], disp, precision=0)} and delist {existing_company.ticker_symbol} from the exchange.');">
                        <input type="hidden" name="company_id" value="{existing_company.id}">
                        <button type="submit" class="btn-blue" style="width: 100%; background: #991b1b; border-color: #ef4444;">
                            Go Private - Delist {existing_company.ticker_symbol}
                        </button>
                    </form>
                </div>'''
            else:
                go_private_html = ""

            error_html = ""
            if error:
                error_html = f'''
                <div class="card" style="border: 2px solid #ef4444; background: #450a0a; margin-bottom: 20px;">
                    <p style="color: #fca5a5; margin: 0;">{html_escape(error)}</p>
                </div>'''

            body = f'''
            <a href="/banks/brokerage-firm" style="color: #38bdf8;">&larr; Brokerage Firm</a>
            <h1>IPO Center</h1>
            {error_html}

            <div class="card" style="border: 2px solid #22c55e; background: #052e16;">
                <h3 style="color: #86efac;">Your Company Is Public</h3>
                <p style="color: #86efac;">
                    <strong>{existing_company.ticker_symbol}</strong> ({existing_company.company_name})
                    is listed on WPE at <strong>{fmt_usd(existing_company.current_price, disp)}</strong>/share.
                </p>
                <p style="color: #86efac; font-size: 0.9rem;">
                    Each player can only have one publicly traded company.
                    You can go private below to delist, then launch a new IPO later.
                </p>
                <a href="/brokerage/trading?ticker={existing_company.ticker_symbol}" class="btn-blue" style="margin-top: 10px;">Trade {existing_company.ticker_symbol}</a>
            </div>

            {go_private_html}
            '''
            return shell("IPO Center", body, player.cash_balance, player.id)

        # Get player's company valuation
        valuation = calculate_player_company_valuation(player.id)

        if not valuation or valuation["total_businesses"] == 0:
            body = '''
            <a href="/banks/brokerage-firm" style="color: #38bdf8;">&larr; Brokerage Firm</a>
            <h1>IPO Center</h1>

            <div class="card" style="border: 2px solid #ef4444; background: #450a0a;">
                <h3 style="color: #fca5a5;">No Businesses to IPO</h3>
                <p style="color: #fca5a5;">You need to build at least one business before going public.</p>
                <a href="/land" class="btn-blue" style="margin-top: 10px;">Get Land & Build</a>
            </div>
            '''
            return shell("IPO Center", body, player.cash_balance, player.id)

        # Build business breakdown
        biz_list_html = ""
        for biz in valuation["businesses_breakdown"]:
            biz_list_html += f'''
            <div style="display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #1e293b;">
                <span style="color: #94a3b8;">{biz["business_name"]}</span>
                <span style="color: #38bdf8;">{fmt_usd(biz["total_value"], disp, precision=0)}</span>
            </div>'''

        # Check if firm is accepting underwritten IPOs
        firm_status = ""
        if not firm.is_accepting_ipos:
            firm_status = '''
            <div class="card" style="border: 1px solid #f59e0b; background: #451a03; margin-bottom: 20px;">
                <p style="color: #fbbf24; margin: 0; font-size: 0.9rem;">
                    The Firm's cash reserves are currently low. All underwritten IPO types are temporarily unavailable. Direct Listing is still available.
                </p>
            </div>'''

        # Build IPO option cards - each with clear tradeoffs
        direct_config = IPO_CONFIG[IPOType.DIRECT_LISTING]
        underwritten_config = IPO_CONFIG[IPOType.FIRM_UNDERWRITTEN]
        income_config = IPO_CONFIG[IPOType.INCOME_SHARES]
        dual_config = IPO_CONFIG[IPOType.DUAL_CLASS]
        preferred_config = IPO_CONFIG[IPOType.PREFERRED_OFFERING]
        series_a_config = IPO_CONFIG[IPOType.SERIES_A_GROWTH]
        quad_config = IPO_CONFIG[IPOType.QUAD_CLASS]

        error_html = ""
        if error:
            error_html = f'''
            <div class="card" style="border: 2px solid #ef4444; background: #450a0a; margin-bottom: 20px;">
                <h3 style="color: #fca5a5; margin: 0 0 5px 0;">IPO Failed</h3>
                <p style="color: #fca5a5; margin: 0;">{html_escape(error)}</p>
            </div>'''

        body = f'''
        <a href="/banks/brokerage-firm" style="color: #38bdf8;">&larr; Brokerage Firm</a>
        <h1>IPO Center</h1>
        {error_html}
        <p style="color: #64748b;">Take <strong>{player.business_name}</strong>'s business empire public on WPE</p>

        <!-- Company Valuation -->
        <div class="card" style="border-left: 4px solid #38bdf8;">
            <h3>Your Company Valuation</h3>
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 20px 0;">
                <div>
                    <div style="font-size: 0.8rem; color: #64748b;">ACTIVE BUSINESSES</div>
                    <div style="font-size: 2rem; font-weight: bold; color: #38bdf8;">{valuation["total_businesses"]}</div>
                </div>
                <div>
                    <div style="font-size: 0.8rem; color: #64748b;">TOTAL VALUATION</div>
                    <div style="font-size: 2rem; font-weight: bold; color: #22c55e;">{fmt_usd(valuation["total_valuation"], disp, precision=0)}</div>
                </div>
                <div>
                    <div style="font-size: 0.8rem; color: #64748b;">SUGGESTED PRICE</div>
                    <div style="font-size: 2rem; font-weight: bold;">{fmt_usd(valuation["suggested_share_price"], disp)}/share</div>
                </div>
            </div>
            <details style="margin-top: 15px;">
                <summary style="cursor: pointer; color: #38bdf8; font-weight: 500;">View Business Breakdown</summary>
                <div style="margin-top: 10px;">{biz_list_html}</div>
            </details>
        </div>

        {firm_status}

        <!-- IPO Type Selection -->
        <div class="card">
            <h3>Choose Your IPO Type</h3>
            <p style="color: #64748b; font-size: 0.9rem; margin-bottom: 20px;">
                Each option has real tradeoffs. Pick the one that fits your strategy.
            </p>

            <div style="display: grid; gap: 20px;">

                <!-- Option 1: Direct Listing -->
                <div class="card ipo-option" data-ipo-type="direct_listing" style="cursor: pointer; border: 2px solid #1e293b; transition: border-color 0.2s;">
                    <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 8px;">
                        <h4 style="margin: 0; color: #22c55e;">Direct Listing</h4>
                        <span style="background: #052e16; color: #22c55e; padding: 3px 10px; border-radius: 4px; font-size: 0.75rem;">$5,000 FLAT FEE</span>
                    </div>
                    <p style="color: #94a3b8; font-size: 0.9rem; line-height: 1.6; margin-bottom: 15px;">
                        {direct_config['description']}
                    </p>
                    <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; font-size: 0.85rem; margin-bottom: 15px;">
                        <div><span style="color: #64748b;">Cost:</span><br><span style="color: #22c55e;">$5,000 flat</span></div>
                        <div><span style="color: #64748b;">Capital:</span><br><span style="color: #f59e0b;">Not guaranteed</span></div>
                        <div><span style="color: #64748b;">Max Float:</span><br><span>80%</span></div>
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 0.85rem; padding-top: 10px; border-top: 1px solid #1e293b;">
                        <div>
                            <span style="color: #22c55e;">Pros:</span>
                            <ul style="margin: 5px 0 0 0; padding-left: 18px; color: #94a3b8;">
                                <li>Cheapest option</li>
                                <li>No ongoing obligations</li>
                                <li>No dependence on the Firm</li>
                            </ul>
                        </div>
                        <div>
                            <span style="color: #ef4444;">Cons:</span>
                            <ul style="margin: 5px 0 0 0; padding-left: 18px; color: #94a3b8;">
                                <li>No guaranteed buyers</li>
                                <li>You sell shares yourself</li>
                                <li>Price may be volatile</li>
                            </ul>
                        </div>
                    </div>
                    <div style="font-size: 0.8rem; color: #64748b; margin-top: 10px;">Min valuation: $25,000</div>
                    <button type="button" class="btn-blue select-ipo-btn" style="width: 100%; margin-top: 15px;">Select Direct Listing</button>
                </div>

                <!-- Option 2: Underwritten IPO -->
                <div class="card ipo-option" data-ipo-type="firm_underwritten" style="cursor: pointer; border: 2px solid #1e293b; transition: border-color 0.2s; {'opacity: 0.5; pointer-events: none;' if not firm.is_accepting_ipos else ''}">
                    <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 8px;">
                        <h4 style="margin: 0; color: #38bdf8;">Underwritten IPO</h4>
                        <span style="background: #0c1a3d; color: #38bdf8; padding: 3px 10px; border-radius: 4px; font-size: 0.75rem;">7% TO THE FIRM</span>
                    </div>
                    <p style="color: #94a3b8; font-size: 0.9rem; line-height: 1.6; margin-bottom: 15px;">
                        {underwritten_config['description']}
                    </p>
                    <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; font-size: 0.85rem; margin-bottom: 15px;">
                        <div><span style="color: #64748b;">Cost:</span><br><span style="color: #f59e0b;">7% discount</span></div>
                        <div><span style="color: #64748b;">Capital:</span><br><span style="color: #22c55e;">Guaranteed</span></div>
                        <div><span style="color: #64748b;">Max Float:</span><br><span>60%</span></div>
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 0.85rem; padding-top: 10px; border-top: 1px solid #1e293b;">
                        <div>
                            <span style="color: #22c55e;">Pros:</span>
                            <ul style="margin: 5px 0 0 0; padding-left: 18px; color: #94a3b8;">
                                <li>Guaranteed immediate cash</li>
                                <li>Firm handles the selling</li>
                                <li>No ongoing obligations</li>
                            </ul>
                        </div>
                        <div>
                            <span style="color: #ef4444;">Cons:</span>
                            <ul style="margin: 5px 0 0 0; padding-left: 18px; color: #94a3b8;">
                                <li>Firm takes 7% cut</li>
                                <li>Requires Firm to have cash</li>
                                <li>Higher min valuation</li>
                            </ul>
                        </div>
                    </div>
                    <div style="font-size: 0.8rem; color: #64748b; margin-top: 10px;">Min valuation: $50,000</div>
                    <button type="button" class="btn-blue select-ipo-btn" style="width: 100%; margin-top: 15px;">Select Underwritten IPO</button>
                </div>

                <!-- Option 3: Income Shares IPO -->
                <div class="card ipo-option" data-ipo-type="income_shares" style="cursor: pointer; border: 2px solid #1e293b; transition: border-color 0.2s; {'opacity: 0.5; pointer-events: none;' if not firm.is_accepting_ipos else ''}">
                    <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 8px;">
                        <h4 style="margin: 0; color: #f59e0b;">Income Shares IPO</h4>
                        <span style="background: #451a03; color: #fbbf24; padding: 3px 10px; border-radius: 4px; font-size: 0.75rem;">3% TO FIRM + DIVIDENDS</span>
                    </div>
                    <p style="color: #94a3b8; font-size: 0.9rem; line-height: 1.6; margin-bottom: 15px;">
                        {income_config['description']}
                    </p>
                    <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; font-size: 0.85rem; margin-bottom: 15px;">
                        <div><span style="color: #64748b;">Cost:</span><br><span style="color: #22c55e;">Only 3% discount</span></div>
                        <div><span style="color: #64748b;">Capital:</span><br><span style="color: #22c55e;">Guaranteed</span></div>
                        <div><span style="color: #64748b;">Dividends:</span><br><span style="color: #ef4444;">10%/year (mandatory)</span></div>
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 0.85rem; padding-top: 10px; border-top: 1px solid #1e293b;">
                        <div>
                            <span style="color: #22c55e;">Pros:</span>
                            <ul style="margin: 5px 0 0 0; padding-left: 18px; color: #94a3b8;">
                                <li>Best upfront price (only 3%)</li>
                                <li>Guaranteed immediate cash</li>
                                <li>Attracts more investors</li>
                            </ul>
                        </div>
                        <div>
                            <span style="color: #ef4444;">Cons:</span>
                            <ul style="margin: 5px 0 0 0; padding-left: 18px; color: #94a3b8;">
                                <li>Must pay dividends every quarter</li>
                                <li>Missing payments hurts credit</li>
                                <li>Ongoing cash drain</li>
                            </ul>
                        </div>
                    </div>
                    <div style="font-size: 0.8rem; color: #64748b; margin-top: 10px;">Min valuation: $75,000 &bull; Max float: 40%</div>
                    <button type="button" class="btn-blue select-ipo-btn" style="width: 100%; margin-top: 15px; background: #92400e; border-color: #f59e0b;">Select Income Shares IPO</button>
                </div>

                <!-- Option 4: Dual-Class IPO -->
                <div class="card ipo-option" data-ipo-type="dual_class" style="cursor: pointer; border: 2px solid #1e293b; transition: border-color 0.2s; {'opacity: 0.5; pointer-events: none;' if not firm.is_accepting_ipos else ''}">
                    <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 8px;">
                        <h4 style="margin: 0; color: #a78bfa;">Dual-Class IPO</h4>
                        <span style="background: #2e1065; color: #c4b5fd; padding: 3px 10px; border-radius: 4px; font-size: 0.75rem;">8% TO FIRM · YOU KEEP CONTROL</span>
                    </div>
                    <p style="color: #94a3b8; font-size: 0.9rem; line-height: 1.6; margin-bottom: 15px;">
                        {dual_config['description']}
                    </p>
                    <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; font-size: 0.85rem; margin-bottom: 15px;">
                        <div><span style="color: #64748b;">Cost:</span><br><span style="color: #f59e0b;">8% discount</span></div>
                        <div><span style="color: #64748b;">Capital:</span><br><span style="color: #22c55e;">Guaranteed</span></div>
                        <div><span style="color: #64748b;">Control:</span><br><span style="color: #22c55e;">Founder retains 51%+</span></div>
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 0.85rem; padding-top: 10px; border-top: 1px solid #1e293b;">
                        <div>
                            <span style="color: #22c55e;">Pros:</span>
                            <ul style="margin: 5px 0 0 0; padding-left: 18px; color: #94a3b8;">
                                <li>Guaranteed upfront capital</li>
                                <li>Permanent voting majority</li>
                                <li>No mandatory dividends</li>
                            </ul>
                        </div>
                        <div>
                            <span style="color: #ef4444;">Cons:</span>
                            <ul style="margin: 5px 0 0 0; padding-left: 18px; color: #94a3b8;">
                                <li>Higher 8% underwriting fee</li>
                                <li>Max 49% float</li>
                                <li>Requires $100,000 valuation</li>
                            </ul>
                        </div>
                    </div>
                    <div style="font-size: 0.8rem; color: #64748b; margin-top: 10px;">Min valuation: $100,000 &bull; Max float: 49% &bull; Class A (founder) + Class B (public)</div>
                    <button type="button" class="btn-blue select-ipo-btn" style="width: 100%; margin-top: 15px; background: #2e1065; border-color: #a78bfa;">Select Dual-Class IPO</button>
                </div>

                <!-- Option 5: Preferred Share Offering -->
                <div class="card ipo-option" data-ipo-type="preferred_offering" style="cursor: pointer; border: 2px solid #1e293b; transition: border-color 0.2s; {'opacity: 0.5; pointer-events: none;' if not firm.is_accepting_ipos else ''}">
                    <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 8px;">
                        <h4 style="margin: 0; color: #fb923c;">Preferred Share Offering</h4>
                        <span style="background: #431407; color: #fdba74; padding: 3px 10px; border-radius: 4px; font-size: 0.75rem;">5% TO FIRM · 12% DIV · 1.5× LIQ</span>
                    </div>
                    <p style="color: #94a3b8; font-size: 0.9rem; line-height: 1.6; margin-bottom: 15px;">
                        {preferred_config['description']}
                    </p>
                    <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; font-size: 0.85rem; margin-bottom: 15px;">
                        <div><span style="color: #64748b;">Cost:</span><br><span style="color: #22c55e;">Only 5% discount</span></div>
                        <div><span style="color: #64748b;">Dividends:</span><br><span style="color: #ef4444;">12%/year (mandatory)</span></div>
                        <div><span style="color: #64748b;">Liquidation:</span><br><span style="color: #22c55e;">1.5× priority payout</span></div>
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 0.85rem; padding-top: 10px; border-top: 1px solid #1e293b;">
                        <div>
                            <span style="color: #22c55e;">Pros:</span>
                            <ul style="margin: 5px 0 0 0; padding-left: 18px; color: #94a3b8;">
                                <li>Cheapest underwriting (5%)</li>
                                <li>Shareholders get 1.5× in bankruptcy</li>
                                <li>Callable — buy shares back anytime</li>
                            </ul>
                        </div>
                        <div>
                            <span style="color: #ef4444;">Cons:</span>
                            <ul style="margin: 5px 0 0 0; padding-left: 18px; color: #94a3b8;">
                                <li>Highest dividend obligation (12%)</li>
                                <li>Missing payments hurts credit</li>
                                <li>Liquidation preference costs you in bankruptcy</li>
                            </ul>
                        </div>
                    </div>
                    <div style="font-size: 0.8rem; color: #64748b; margin-top: 10px;">Min valuation: $50,000 &bull; Max float: 40% &bull; Callable preferred shares</div>
                    <button type="button" class="btn-blue select-ipo-btn" style="width: 100%; margin-top: 15px; background: #431407; border-color: #fb923c;">Select Preferred Offering</button>
                </div>

                <!-- Option 6: Series A Growth Round -->
                <div class="card ipo-option" data-ipo-type="series_a_growth" style="cursor: pointer; border: 2px solid #1e293b; transition: border-color 0.2s; {'opacity: 0.5; pointer-events: none;' if not firm.is_accepting_ipos else ''}">
                    <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 8px;">
                        <h4 style="margin: 0; color: #34d399;">Series A Growth Round</h4>
                        <span style="background: #022c22; color: #6ee7b7; padding: 3px 10px; border-radius: 4px; font-size: 0.75rem;">12% TO FIRM · +20% GROWTH BONUS</span>
                    </div>
                    <p style="color: #94a3b8; font-size: 0.9rem; line-height: 1.6; margin-bottom: 15px;">
                        {series_a_config['description']}
                    </p>
                    <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; font-size: 0.85rem; margin-bottom: 15px;">
                        <div><span style="color: #64748b;">Cost:</span><br><span style="color: #ef4444;">12% discount (steepest)</span></div>
                        <div><span style="color: #64748b;">Capital:</span><br><span style="color: #22c55e;">120% of standard proceeds</span></div>
                        <div><span style="color: #64748b;">Dividends:</span><br><span style="color: #22c55e;">None required</span></div>
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 0.85rem; padding-top: 10px; border-top: 1px solid #1e293b;">
                        <div>
                            <span style="color: #22c55e;">Pros:</span>
                            <ul style="margin: 5px 0 0 0; padding-left: 18px; color: #94a3b8;">
                                <li>Largest total capital injection</li>
                                <li>No dividend obligations</li>
                                <li>20% bonus above proceeds</li>
                            </ul>
                        </div>
                        <div>
                            <span style="color: #ef4444;">Cons:</span>
                            <ul style="margin: 5px 0 0 0; padding-left: 18px; color: #94a3b8;">
                                <li>Steepest underwriting cost (12%)</li>
                                <li>Small float (30% max)</li>
                                <li>Needs $150,000 valuation</li>
                            </ul>
                        </div>
                    </div>
                    <div style="font-size: 0.8rem; color: #64748b; margin-top: 10px;">Min valuation: $150,000 &bull; Max float: 30% &bull; Growth capital injection</div>
                    <button type="button" class="btn-blue select-ipo-btn" style="width: 100%; margin-top: 15px; background: #022c22; border-color: #34d399;">Select Series A Growth Round</button>
                </div>

                <!-- Option 7: Quad-Class IPO -->
                <div class="card ipo-option" data-ipo-type="quad_class" style="cursor: pointer; border: 2px solid #1e293b; transition: border-color 0.2s; {'opacity: 0.5; pointer-events: none;' if not firm.is_accepting_ipos else ''}">
                    <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 8px;">
                        <h4 style="margin: 0; color: #e879f9;">Quad-Class IPO</h4>
                        <span style="background: #2e1065; color: #e879f9; padding: 3px 10px; border-radius: 4px; font-size: 0.75rem;">10% TO FIRM · A/B/C/D · FULL SUITE</span>
                    </div>
                    <p style="color: #94a3b8; font-size: 0.9rem; line-height: 1.6; margin-bottom: 15px;">
                        {quad_config['description']}
                    </p>
                    <div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 8px; font-size: 0.8rem; margin-bottom: 15px;">
                        <div style="background:#1e293b; padding:6px; border-radius:4px;"><span style="color:#e879f9;">Class A</span><br><span style="color:#94a3b8;">Founder<br>Non-lendable</span></div>
                        <div style="background:#1e293b; padding:6px; border-radius:4px;"><span style="color:#38bdf8;">Class B</span><br><span style="color:#94a3b8;">Public<br>Traded</span></div>
                        <div style="background:#1e293b; padding:6px; border-radius:4px;"><span style="color:#fb923c;">Class C</span><br><span style="color:#94a3b8;">Preferred<br>10% div</span></div>
                        <div style="background:#1e293b; padding:6px; border-radius:4px;"><span style="color:#34d399;">Class D</span><br><span style="color:#94a3b8;">Non-voting<br>1.2× liq</span></div>
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 0.85rem; padding-top: 10px; border-top: 1px solid #1e293b;">
                        <div>
                            <span style="color: #22c55e;">Pros:</span>
                            <ul style="margin: 5px 0 0 0; padding-left: 18px; color: #94a3b8;">
                                <li>Highest max float (60%)</li>
                                <li>15% growth capital bonus</li>
                                <li>Voting insulation + div + liq pref</li>
                            </ul>
                        </div>
                        <div>
                            <span style="color: #ef4444;">Cons:</span>
                            <ul style="margin: 5px 0 0 0; padding-left: 18px; color: #94a3b8;">
                                <li>Mandatory 10%/year dividends</li>
                                <li>1.2× liquidation preference exposure</li>
                                <li>Needs $200,000 valuation</li>
                            </ul>
                        </div>
                    </div>
                    <div style="font-size: 0.8rem; color: #64748b; margin-top: 10px;">Min valuation: $200,000 &bull; Max float: 60% &bull; Retain 40%+ as Class A</div>
                    <button type="button" class="btn-blue select-ipo-btn" style="width: 100%; margin-top: 15px; background: #1a0533; border-color: #e879f9;">Select Quad-Class IPO</button>
                </div>
            </div>
        </div>

        <!-- IPO Configuration Form (hidden until type selected) -->
        <div id="ipo-form-section" style="display: none;">
            <div class="card">
                <h3>Configure Your IPO</h3>
                <form action="/api/brokerage/create-player-ipo" method="post">
                    <input type="hidden" name="ipo_type" id="selected-ipo-type" value="">

                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                        <div>
                            <div style="margin-bottom: 15px;">
                                <label style="display: block; margin-bottom: 5px; color: #94a3b8;">Company Name</label>
                                <input type="text" name="company_name" required
                                       style="width: 100%; padding: 10px;"
                                       placeholder="e.g., {player.business_name} Corporation"
                                       value="{player.business_name} Co.">
                            </div>

                            <div style="margin-bottom: 15px;">
                                <label style="display: block; margin-bottom: 5px; color: #94a3b8;">Ticker Symbol (3-5 chars)</label>
                                <input type="text" name="ticker_symbol" required maxlength="5" minlength="3"
                                       style="width: 100%; padding: 10px; text-transform: uppercase;"
                                       placeholder="e.g., {player.business_name[:4].upper()}">
                                <p style="font-size: 0.8rem; color: #64748b; margin-top: 5px;">This will appear on WPE ticker</p>
                            </div>
                        </div>

                        <div>
                            <div style="margin-bottom: 15px;">
                                <label style="display: block; margin-bottom: 5px; color: #94a3b8;">Total Shares to Issue</label>
                                <input type="number" name="total_shares" required min="10000"
                                       value="{valuation['suggested_ipo_shares']}"
                                       style="width: 100%; padding: 10px;">
                                <p style="font-size: 0.8rem; color: #64748b; margin-top: 5px;">
                                    Suggested: {valuation['suggested_ipo_shares']:,} shares
                                </p>
                            </div>

                            <div style="margin-bottom: 15px;">
                                <label style="display: block; margin-bottom: 5px; color: #94a3b8;">Shares to Offer (% of total)</label>
                                <input type="number" name="offer_percentage" required min="10" max="100" value="25"
                                       style="width: 100%; padding: 10px;">
                                <p style="font-size: 0.8rem; color: #64748b; margin-top: 5px;">
                                    You keep the rest. Most IPOs offer 20-40%.
                                </p>
                            </div>
                        </div>
                    </div>

                    <button type="submit" class="btn-blue" style="width: 100%; padding: 15px; margin-top: 20px; font-size: 1.1rem;">
                        Launch IPO
                    </button>
                </form>
            </div>
        </div>

        <script>
            document.querySelectorAll('.select-ipo-btn').forEach(btn => {{
                btn.addEventListener('click', function(e) {{
                    e.stopPropagation();
                    const card = this.closest('.ipo-option');
                    const ipoType = card.dataset.ipoType;

                    document.querySelectorAll('.ipo-option').forEach(c => {{
                        c.style.borderColor = '#1e293b';
                    }});
                    card.style.borderColor = '#38bdf8';

                    document.getElementById('selected-ipo-type').value = ipoType;
                    document.getElementById('ipo-form-section').style.display = 'block';
                    document.getElementById('ipo-form-section').scrollIntoView({{ behavior: 'smooth' }});
                }});
            }});
        </script>
        '''

        return shell("IPO Center", body, player.cash_balance, player.id)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return shell("IPO Center", f"Error: {e}", player.cash_balance, player.id)
# NEW IPO CREATION ENDPOINT
# Add this to ux.py after the existing IPO page

@router.post("/api/brokerage/create-player-ipo")
async def create_player_ipo_endpoint(
    company_name: str = Form(...),
    ticker_symbol: str = Form(...),
    ipo_type: str = Form(...),
    total_shares: int = Form(...),
    offer_percentage: int = Form(...),
    session_token: Optional[str] = Cookie(None)
):
    """
    Create a player holding company IPO.
    
    This replaces the old per-business IPO system with a proper
    holding company structure where players IPO their entire empire.
    """
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)
    
    try:
        from banks.brokerage_firm import (
            create_player_ipo, IPOType, get_db as get_firm_db
        )
        
        # Validate ticker symbol
        ticker_symbol = ticker_symbol.upper().strip()
        if len(ticker_symbol) < 3 or len(ticker_symbol) > 5:
            return RedirectResponse(
                url="/brokerage/ipo?error=invalid_ticker",
                status_code=303
            )
        
        # Validate shares
        if total_shares < 10000:
            return RedirectResponse(
                url="/brokerage/ipo?error=insufficient_shares",
                status_code=303
            )
        
        # Calculate shares to offer
        shares_to_offer = int((offer_percentage / 100) * total_shares)
        
        if shares_to_offer < 1:
            return RedirectResponse(
                url="/brokerage/ipo?error=must_offer_shares",
                status_code=303
            )
        
        # Convert IPO type string to enum
        try:
            ipo_type_enum = IPOType(ipo_type)
        except ValueError:
            return RedirectResponse(
                url="/brokerage/ipo?error=invalid_ipo_type",
                status_code=303
            )
        
        # Create the IPO
        company, error_msg = create_player_ipo(
            founder_id=player.id,
            company_name=company_name,
            ticker_symbol=ticker_symbol,
            ipo_type=ipo_type_enum,
            shares_to_offer=shares_to_offer,
            total_shares=total_shares,
            share_class="A",  # Default to Class A
            dividend_config=None  # Will add dividend config in phase 2
        )

        if not company:
            from urllib.parse import quote
            return RedirectResponse(
                url=f"/brokerage/ipo?error={quote(error_msg or 'IPO creation failed.')}",
                status_code=303
            )
        
        # Success! Redirect to trading page for their new stock
        return RedirectResponse(
            url=f"/brokerage/trading?ticker={ticker_symbol}&success=ipo_created",
            status_code=303
        )
    
    except Exception as e:
        print(f"[UX] IPO creation error: {e}")
        import traceback
        traceback.print_exc()
        return RedirectResponse(
            url="/brokerage/ipo?error=exception",
            status_code=303
        )

@router.post("/api/brokerage/go-private")
async def go_private_endpoint(
    company_id: int = Form(...),
    session_token: Optional[str] = Cookie(None)
):
    """Delist a company and take it private."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)

    try:
        from banks.brokerage_firm import delist_company
        success, error_msg = delist_company(player.id, company_id)

        if success:
            return RedirectResponse(
                url="/brokerage/ipo?error=Company+successfully+taken+private.+You+can+launch+a+new+IPO+after+the+30-day+cooldown.",
                status_code=303
            )
        else:
            from urllib.parse import quote
            return RedirectResponse(
                url=f"/brokerage/ipo?error={quote(error_msg or 'Failed to go private.')}",
                status_code=303
            )
    except Exception as e:
        print(f"[UX] Go private error: {e}")
        import traceback
        traceback.print_exc()
        from urllib.parse import quote
        return RedirectResponse(
            url=f"/brokerage/ipo?error={quote(str(e))}",
            status_code=303
        )


@router.post("/api/brokerage/call-shares")
async def call_shares_endpoint(
    company_id: int = Form(...),
    session_token: Optional[str] = Cookie(None)
):
    """Redeem all outstanding callable shares at current price + 5% call premium."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    try:
        from banks.brokerage_firm import call_shares
        from urllib.parse import quote
        success, message = call_shares(company_id, player.id)
        param = "success" if success else "error"
        return RedirectResponse(
            url=f"/brokerage/my-companies?{param}={quote(message)}",
            status_code=303
        )
    except Exception as e:
        from urllib.parse import quote
        return RedirectResponse(
            url=f"/brokerage/my-companies?error={quote(str(e))}",
            status_code=303
        )


@router.get("/brokerage/governance", response_class=HTMLResponse)
def brokerage_governance_page(
    company_id: int = None,
    session_token: Optional[str] = Cookie(None)
):
    """Governance / shareholder voting page for a company."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)

    try:
        from banks.brokerage_firm import (
            CompanyShares, ShareholderPosition, CompanyProposal, CompanyVote,
            get_db as get_firm_db, get_voting_power, PROPOSAL_DURATION_HOURS,
            CLASS_A_VOTE_MULTIPLIER
        )
        db = get_firm_db()
        try:
            if company_id:
                company = db.query(CompanyShares).filter(
                    CompanyShares.id == company_id,
                    CompanyShares.is_delisted == False,
                    CompanyShares.parent_company_id == None,
                ).first()
            else:
                company = None

            # All companies where this player holds shares (main records only)
            my_positions = db.query(ShareholderPosition).filter(
                ShareholderPosition.player_id == player.id,
                ShareholderPosition.shares_owned > 0,
            ).all()
            held_company_ids = [p.company_shares_id for p in my_positions]
            selectable = db.query(CompanyShares).filter(
                CompanyShares.id.in_(held_company_ids),
                CompanyShares.is_delisted == False,
                CompanyShares.parent_company_id == None,
            ).all()

            proposals = []
            my_votes = set()
            if company:
                proposals = db.query(CompanyProposal).filter(
                    CompanyProposal.company_shares_id == company.id,
                ).order_by(CompanyProposal.created_at.desc()).limit(50).all()
                voted = db.query(CompanyVote).filter(
                    CompanyVote.voter_id == player.id,
                    CompanyVote.proposal_id.in_([p.id for p in proposals]),
                ).all()
                my_votes = {v.proposal_id for v in voted}

        finally:
            db.close()

        # Company selector
        selector_options = "".join(
            f'<option value="{c.id}" {"selected" if company and c.id == company.id else ""}>'
            f'{c.ticker_symbol} — {c.company_name}</option>'
            for c in selectable
        )
        selector_html = f'''
            <form method="get" action="/brokerage/governance" style="margin-bottom:20px;">
                <label style="color:#94a3b8;">Select company:</label>
                <select name="company_id" onchange="this.form.submit()"
                        style="margin-left:10px;padding:8px 12px;background:#0f172a;color:#e2e8f0;border:1px solid #334155;border-radius:4px;">
                    <option value="">— choose —</option>
                    {selector_options}
                </select>
            </form>''' if selectable else '<p style="color:#64748b;">You don\'t hold shares in any listed companies.</p>'

        # Proposal creation form (shown if viewing a company)
        create_form = ""
        if company:
            is_founder = company.founder_id == player.id
            voting_label = ""
            if company.is_dual_class and is_founder:
                voting_label = f'<span style="color:#f59e0b;font-size:0.85rem;">⚡ Your Class A shares carry {CLASS_A_VOTE_MULTIPLIER}× voting weight.</span>'
            elif company.is_dual_class:
                voting_label = f'<span style="color:#94a3b8;font-size:0.85rem;">Founder\'s Class A shares carry {CLASS_A_VOTE_MULTIPLIER}× the voting weight of your Class B shares.</span>'
            create_form = f'''
            <div class="card" style="margin-bottom:20px;">
                <h3>Create Governance Proposal</h3>
                {voting_label}
                <form action="/api/brokerage/create-proposal" method="post" style="margin-top:15px;">
                    <input type="hidden" name="company_id" value="{company.id}">
                    <div style="margin-bottom:12px;">
                        <label style="color:#94a3b8;display:block;margin-bottom:4px;">Proposal Type</label>
                        <select name="proposal_type" id="gov-proposal-type" onchange="govParamToggle(this.value)"
                                style="width:100%;padding:8px;background:#0f172a;color:#e2e8f0;border:1px solid #334155;border-radius:4px;">
                            <option value="dividend_change">Dividend Change — set a new annual dividend rate</option>
                            <option value="secondary_offering">Secondary Offering — issue new shares into the float</option>
                            <option value="trading_halt">Trading Halt — pause all trading temporarily</option>
                            <option value="custom">Custom / Other — advisory, no automatic effect</option>
                        </select>
                    </div>
                    <!-- Dynamic parameter field (shown per type) -->
                    <div id="gov-param-dividend" style="margin-bottom:12px;">
                        <label style="color:#94a3b8;display:block;margin-bottom:4px;">New Annual Dividend Rate (%)</label>
                        <input type="number" name="param_dividend_rate" min="0" max="100" step="0.1" placeholder="e.g. 8 for 8%"
                               style="width:100%;padding:8px;background:#0f172a;color:#e2e8f0;border:1px solid #334155;border-radius:4px;">
                        <p style="color:#64748b;font-size:0.8rem;margin-top:4px;">If passed, the company's dividend rate is updated immediately. Leave 0 to remove dividends.</p>
                    </div>
                    <div id="gov-param-offering" style="margin-bottom:12px;display:none;">
                        <label style="color:#94a3b8;display:block;margin-bottom:4px;">New Shares to Issue</label>
                        <input type="number" name="param_shares" min="1000" step="1000" placeholder="e.g. 50000"
                               style="width:100%;padding:8px;background:#0f172a;color:#e2e8f0;border:1px solid #334155;border-radius:4px;">
                        <p style="color:#64748b;font-size:0.8rem;margin-top:4px;">If passed, these shares are added to the public float. This dilutes existing shareholders.</p>
                    </div>
                    <div id="gov-param-halt" style="margin-bottom:12px;display:none;">
                        <label style="color:#94a3b8;display:block;margin-bottom:4px;">Halt Duration (hours)</label>
                        <input type="number" name="param_halt_hours" min="1" max="168" step="1" value="24"
                               style="width:100%;padding:8px;background:#0f172a;color:#e2e8f0;border:1px solid #334155;border-radius:4px;">
                        <p style="color:#64748b;font-size:0.8rem;margin-top:4px;">If passed, all trading in this company is suspended for the chosen duration (max 168h / 1 week).</p>
                    </div>
                    <div style="margin-bottom:12px;">
                        <label style="color:#94a3b8;display:block;margin-bottom:4px;">Title</label>
                        <input type="text" name="title" required maxlength="120"
                               style="width:100%;padding:8px;background:#0f172a;color:#e2e8f0;border:1px solid #334155;border-radius:4px;"
                               placeholder="Short summary of the proposal">
                    </div>
                    <div style="margin-bottom:12px;">
                        <label style="color:#94a3b8;display:block;margin-bottom:4px;">Description</label>
                        <textarea name="description" required rows="3"
                                  style="width:100%;padding:8px;background:#0f172a;color:#e2e8f0;border:1px solid #334155;border-radius:4px;resize:vertical;"
                                  placeholder="Full details of the proposal..."></textarea>
                    </div>
                    <button type="submit" class="btn-blue">Submit Proposal (voting open {PROPOSAL_DURATION_HOURS}h)</button>
                </form>
                <script>
                function govParamToggle(type) {{
                    document.getElementById('gov-param-dividend').style.display = type === 'dividend_change' ? '' : 'none';
                    document.getElementById('gov-param-offering').style.display = type === 'secondary_offering' ? '' : 'none';
                    document.getElementById('gov-param-halt').style.display = type === 'trading_halt' ? '' : 'none';
                }}
                </script>
            </div>'''

        # Proposals list
        proposals_html = ""
        if company and proposals:
            for p in proposals:
                total_w = p.yes_votes + p.no_votes
                yes_pct = (p.yes_votes / total_w * 100) if total_w > 0 else 0
                no_pct = 100 - yes_pct if total_w > 0 else 0
                status_color = {"open": "#38bdf8", "passed": "#22c55e",
                                "rejected": "#ef4444", "cancelled": "#64748b"}.get(p.status, "#94a3b8")
                already_voted = p.id in my_votes
                vote_form = ""
                if p.status == "open" and not already_voted:
                    vote_form = f'''
                        <form action="/api/brokerage/vote" method="post" style="display:inline;margin-right:8px;">
                            <input type="hidden" name="proposal_id" value="{p.id}">
                            <button name="vote" value="yes" class="btn-blue" style="padding:4px 14px;">✓ Yes</button>
                            <button name="vote" value="no" class="btn-red" style="padding:4px 14px;margin-left:6px;">✗ No</button>
                        </form>'''
                elif already_voted:
                    vote_form = '<span style="color:#64748b;font-size:0.85rem;">✓ You voted</span>'
                ends = p.voting_ends_at.strftime("%b %d %H:%M UTC") if p.voting_ends_at else "—"
                applied_badge = ""
                if p.result_applied:
                    applied_badge = '<span style="color:#22c55e;font-size:0.75rem;margin-left:8px;">✓ Effect applied</span>'
                elif p.status == "passed":
                    applied_badge = '<span style="color:#f59e0b;font-size:0.75rem;margin-left:8px;">Pending effect</span>'
                proposals_html += f'''
                <div class="card" style="margin-bottom:12px;border-left:3px solid {status_color};">
                    <div style="display:flex;justify-content:space-between;align-items:start;">
                        <div>
                            <span style="color:{status_color};font-size:0.75rem;text-transform:uppercase;">{p.status}</span>{applied_badge}
                            <h4 style="margin:4px 0;">{p.title}</h4>
                            <p style="color:#94a3b8;font-size:0.9rem;margin:4px 0;">{p.description}</p>
                            <p style="color:#64748b;font-size:0.8rem;">Type: {p.proposal_type.replace("_"," ").title()} &nbsp;|&nbsp; Closes: {ends} &nbsp;|&nbsp; Voters: {p.total_voters}</p>
                        </div>
                    </div>
                    <div style="margin:10px 0;">
                        <div style="display:flex;gap:4px;height:8px;border-radius:4px;overflow:hidden;background:#1e293b;">
                            <div style="width:{yes_pct:.1f}%;background:#22c55e;"></div>
                            <div style="width:{no_pct:.1f}%;background:#ef4444;"></div>
                        </div>
                        <div style="display:flex;justify-content:space-between;font-size:0.8rem;color:#94a3b8;margin-top:4px;">
                            <span>✓ {p.yes_votes:,.0f} weighted votes</span>
                            <span>✗ {p.no_votes:,.0f} weighted votes</span>
                        </div>
                    </div>
                    {vote_form}
                </div>'''
        elif company:
            proposals_html = '<p style="color:#64748b;">No proposals yet. Be the first to create one.</p>'

        company_header = f"<h2>{company.ticker_symbol} — {company.company_name}</h2>" if company else ""

        body = f'''
        <a href="/brokerage/my-companies" style="color:#38bdf8;">← My Companies</a>
        <h1>Shareholder Governance</h1>
        <p style="color:#64748b;">Propose and vote on company decisions. Dual/Quad-Class founders always maintain voting control via {CLASS_A_VOTE_MULTIPLIER}× Class A weight.</p>
        {selector_html}
        {company_header}
        {create_form}
        {proposals_html}
        '''
        return shell("Governance", body, player.cash_balance, player.id)

    except Exception as e:
        import traceback; traceback.print_exc()
        return shell("Governance", f"Error: {e}", player.cash_balance, player.id)


@router.post("/api/brokerage/create-proposal")
async def create_proposal_endpoint(
    company_id: int = Form(...),
    proposal_type: str = Form(...),
    title: str = Form(...),
    description: str = Form(...),
    param_dividend_rate: Optional[str] = Form(None),
    param_shares: Optional[str] = Form(None),
    param_halt_hours: Optional[str] = Form(None),
    session_token: Optional[str] = Cookie(None)
):
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    from urllib.parse import quote
    try:
        from banks.brokerage_firm import create_proposal
        # Build the structured param dict based on proposal type
        proposal_param: dict = {}
        if proposal_type == "dividend_change" and param_dividend_rate:
            try:
                proposal_param["new_rate"] = float(param_dividend_rate) / 100.0
            except ValueError:
                pass
        elif proposal_type == "secondary_offering" and param_shares:
            try:
                proposal_param["shares"] = int(param_shares)
            except ValueError:
                pass
        elif proposal_type == "trading_halt" and param_halt_hours:
            try:
                proposal_param["hours"] = int(param_halt_hours)
            except ValueError:
                proposal_param["hours"] = 24
        proposal, err = create_proposal(company_id, player.id, proposal_type, title, description, proposal_param)
        if proposal:
            return RedirectResponse(
                url=f"/brokerage/governance?company_id={company_id}&success=Proposal+submitted.",
                status_code=303
            )
        return RedirectResponse(
            url=f"/brokerage/governance?company_id={company_id}&error={quote(err or 'Failed')}",
            status_code=303
        )
    except Exception as e:
        return RedirectResponse(
            url=f"/brokerage/governance?company_id={company_id}&error={quote(str(e))}",
            status_code=303
        )


@router.post("/api/brokerage/vote")
async def cast_vote_endpoint(
    proposal_id: int = Form(...),
    vote: str = Form(...),
    session_token: Optional[str] = Cookie(None)
):
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    from urllib.parse import quote
    try:
        from banks.brokerage_firm import cast_vote, CompanyProposal, get_db as get_firm_db
        db = get_firm_db()
        try:
            p = db.query(CompanyProposal).filter(CompanyProposal.id == proposal_id).first()
            company_id = p.company_shares_id if p else None
        finally:
            db.close()
        success, message = cast_vote(proposal_id, player.id, vote == "yes")
        param = "success" if success else "error"
        return RedirectResponse(
            url=f"/brokerage/governance?company_id={company_id}&{param}={quote(message)}",
            status_code=303
        )
    except Exception as e:
        return RedirectResponse(
            url=f"/brokerage/governance?error={quote(str(e))}",
            status_code=303
        )


@router.get("/brokerage/portfolio", response_class=HTMLResponse)
def brokerage_portfolio_page(session_token: Optional[str] = Cookie(None)):
    """Player's equity portfolio page."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)

    try:
        from banks.brokerage_firm import (
            CompanyShares, ShareholderPosition, get_db as get_firm_db
        )
        
        db = get_firm_db()
        try:
            # Get all player positions
            positions = db.query(ShareholderPosition).filter(
                ShareholderPosition.player_id == player.id,
                ShareholderPosition.shares_owned > 0
            ).all()
            
            portfolio_data = []
            total_value = 0.0
            total_cost = 0.0
            total_margin_debt = 0.0
            
            for pos in positions:
                company = db.query(CompanyShares).filter(
                    CompanyShares.id == pos.company_shares_id
                ).first()
                
                if company:
                    market_value = pos.shares_owned * company.current_price
                    cost_basis_total = pos.shares_owned * pos.average_cost_basis
                    pnl = market_value - cost_basis_total
                    pnl_pct = (pnl / cost_basis_total * 100) if cost_basis_total > 0 else 0
                    
                    portfolio_data.append({
                        "company": company,
                        "position": pos,
                        "market_value": market_value,
                        "cost_basis_total": cost_basis_total,
                        "pnl": pnl,
                        "pnl_pct": pnl_pct
                    })
                    
                    total_value += market_value
                    total_cost += cost_basis_total
                    total_margin_debt += pos.margin_debt
            
        finally:
            db.close()
        
        total_pnl = total_value - total_cost
        total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0
        
        # Build portfolio table
        LEND_OPT_OUT_BASE_FEE = 50_000.0   # flat fee per position to opt out of lending
        LEND_OPT_OUT_PCT      = 0.01        # plus 1 % of position market value

        portfolio_html = ""
        if portfolio_data:
            portfolio_html = '''
            <table style="width: 100%; border-collapse: collapse;">
                <thead>
                    <tr style="border-bottom: 1px solid #1e293b; text-align: left;">
                        <th style="padding: 12px 8px;">Symbol</th>
                        <th style="padding: 12px 8px;">Shares</th>
                        <th style="padding: 12px 8px;">Price</th>
                        <th style="padding: 12px 8px;">Market Value</th>
                        <th style="padding: 12px 8px;">Cost Basis</th>
                        <th style="padding: 12px 8px;">P/L</th>
                        <th style="padding: 12px 8px;">Margin</th>
                        <th style="padding: 12px 8px;">Lending</th>
                        <th style="padding: 12px 8px;">Actions</th>
                    </tr>
                </thead>
                <tbody>'''

            for item in portfolio_data:
                company = item["company"]
                pos = item["position"]
                pnl_color = "#22c55e" if item["pnl"] >= 0 else "#ef4444"
                margin_badge = f'<span class="badge" style="background: #f59e0b;">MARGIN</span>' if pos.is_margin_position else ""

                # Share-lending status cell
                available_to_lend = pos.shares_available_to_lend or 0
                lent_out          = pos.shares_lent_out or 0
                opt_out_fee       = LEND_OPT_OUT_BASE_FEE + item["market_value"] * LEND_OPT_OUT_PCT
                if available_to_lend > 0 or lent_out > 0:
                    recall_btn = ""
                    if lent_out > 0:
                        recall_btn = f'''<br><form action="/api/brokerage/recall-shares" method="post" style="display:inline;"
                              onsubmit="return confirm('Recall all {lent_out:,} lent shares of {company.ticker_symbol}? This force-closes the borrower\\'s short positions immediately.');">
                            <input type="hidden" name="company_shares_id" value="{company.id}">
                            <button type="submit" style="font-size:0.75rem;background:#7c2d12;color:#fdba74;border:none;padding:2px 6px;border-radius:3px;cursor:pointer;">
                                Recall {lent_out:,} shares
                            </button>
                        </form>'''
                    lending_cell = f'''
                        <span style="color:#22c55e;font-size:0.8rem;">&#10003; Lending</span><br>
                        <span style="font-size:0.75rem;color:#94a3b8;">
                            {available_to_lend:,} offered &middot; {lent_out:,} out
                        </span><br>
                        <form action="/api/brokerage/enable-share-lending" method="post" style="display:inline;">
                            <input type="hidden" name="position_id" value="{pos.id}">
                            <input type="number" name="quantity" min="0" max="{pos.shares_owned}" value="{available_to_lend}"
                                   style="width:70px;font-size:0.75rem;background:#0f172a;border:1px solid #334155;color:#e2e8f0;padding:2px 4px;border-radius:3px;">
                            <button type="submit" style="font-size:0.75rem;background:#15803d;color:#fff;border:none;padding:2px 6px;border-radius:3px;cursor:pointer;">
                                Update
                            </button>
                        </form><br>
                        <form action="/api/brokerage/disable-share-lending" method="post" style="display:inline;"
                              onsubmit="return confirm('Opt out of lending for {company.ticker_symbol}? This costs {fmt_usd(opt_out_fee, disp, precision=0)} (base fee + 1% of position value).');">
                            <input type="hidden" name="position_id" value="{pos.id}">
                            <button type="submit" style="font-size:0.75rem;background:#7f1d1d;color:#fca5a5;border:none;padding:2px 6px;border-radius:3px;cursor:pointer;">
                                Opt-Out ({fmt_usd(opt_out_fee, disp, precision=0)})
                            </button>
                        </form>{recall_btn}'''
                else:
                    lending_cell = f'''
                        <span style="color:#ef4444;font-size:0.8rem;">&#10007; Not Lending</span><br>
                        <form action="/api/brokerage/enable-share-lending" method="post" style="display:inline;">
                            <input type="hidden" name="position_id" value="{pos.id}">
                            <input type="hidden" name="quantity" value="{pos.shares_owned}">
                            <button type="submit" style="font-size:0.75rem;background:#15803d;color:#fff;border:none;padding:2px 6px;border-radius:3px;cursor:pointer;">
                                Opt-In (All Shares)
                            </button>
                        </form><br>
                        <form action="/api/brokerage/enable-share-lending" method="post" style="display:inline;">
                            <input type="hidden" name="position_id" value="{pos.id}">
                            <input type="number" name="quantity" min="1" max="{pos.shares_owned}" placeholder="qty"
                                   style="width:60px;font-size:0.75rem;background:#0f172a;border:1px solid #334155;color:#e2e8f0;padding:2px 4px;border-radius:3px;">
                            <button type="submit" style="font-size:0.75rem;background:#1d4ed8;color:#fff;border:none;padding:2px 6px;border-radius:3px;cursor:pointer;">
                                Opt-In Custom
                            </button>
                        </form>'''

                portfolio_html += f'''
                <tr style="border-bottom: 1px solid #1e293b;">
                    <td style="padding: 12px 8px;">
                        <strong>{company.ticker_symbol}</strong> {margin_badge}<br>
                        <span style="color: #64748b; font-size: 0.85rem;">{company.company_name[:20]}</span>
                    </td>
                    <td style="padding: 12px 8px;">{pos.shares_owned:,}</td>
                    <td style="padding: 12px 8px;">{fmt_usd(company.current_price, disp, precision=4)}</td>
                    <td style="padding: 12px 8px;">{fmt_usd(item["market_value"], disp)}</td>
                    <td style="padding: 12px 8px;">{fmt_usd(pos.average_cost_basis, disp, precision=4)}</td>
                    <td style="padding: 12px 8px; color: {pnl_color};">
                        {fmt_usd(item["pnl"], disp)}<br>
                        <span style="font-size: 0.85rem;">({item["pnl_pct"]:+.1f}%)</span>
                    </td>
                    <td style="padding: 12px 8px;">
                        {fmt_usd(pos.margin_debt, disp) if pos.margin_debt > 0 else "-"}
                    </td>
                    <td style="padding: 12px 8px; vertical-align: top;">
                        {lending_cell}
                    </td>
                    <td style="padding: 12px 8px;">
                        <a href="/brokerage/trading?ticker={company.ticker_symbol}" class="btn-blue" style="font-size: 0.8rem; padding: 4px 8px;">Trade</a>
                    </td>
                </tr>'''

            portfolio_html += '</tbody></table>'
        else:
            portfolio_html = '<p style="color: #64748b;">You have no equity positions. <a href="/brokerage/trading">Start trading!</a></p>'

        body = f'''
        <a href="/banks/brokerage-firm" style="color: #38bdf8;">← Brokerage Firm</a>
        <h1>My Portfolio</h1>

        <!-- Portfolio Summary -->
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 20px;">
            <div class="card" style="text-align: center;">
                <div style="font-size: 0.8rem; color: #64748b;">TOTAL VALUE</div>
                <div style="font-size: 1.8rem; font-weight: bold; color: #38bdf8;">{fmt_usd(total_value, disp)}</div>
            </div>
            <div class="card" style="text-align: center;">
                <div style="font-size: 0.8rem; color: #64748b;">TOTAL COST</div>
                <div style="font-size: 1.8rem; font-weight: bold;">{fmt_usd(total_cost, disp)}</div>
            </div>
            <div class="card" style="text-align: center;">
                <div style="font-size: 0.8rem; color: #64748b;">TOTAL P/L</div>
                <div style="font-size: 1.8rem; font-weight: bold; color: {'#22c55e' if total_pnl >= 0 else '#ef4444'};">
                    {fmt_usd(total_pnl, disp)}
                </div>
                <div style="font-size: 0.85rem; color: {'#22c55e' if total_pnl >= 0 else '#ef4444'};">
                    ({total_pnl_pct:+.1f}%)
                </div>
            </div>
            <div class="card" style="text-align: center;">
                <div style="font-size: 0.8rem; color: #64748b;">MARGIN DEBT</div>
                <div style="font-size: 1.8rem; font-weight: bold; color: {'#ef4444' if total_margin_debt > 0 else '#22c55e'};">
                    {fmt_usd(total_margin_debt, disp)}
                </div>
            </div>
        </div>

        <!-- Holdings Table -->
        <div class="card">
            <h3>Holdings &amp; Share Lending</h3>
            <p style="font-size:0.85rem;color:#64748b;margin-bottom:12px;">
                Share lending is <strong style="color:#22c55e;">enabled by default</strong> for all positions.
                Borrowers who request shares receive them proportionally from all opted-in lenders.
                Opting out costs a <strong style="color:#ef4444;">$50,000 base fee plus 1% of position value</strong> per stock.
            </p>
            {portfolio_html}
        </div>
        '''
        
        return shell("My Portfolio", body, player.cash_balance, player.id)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return shell("My Portfolio", f"Error: {e}", player.cash_balance, player.id)


@router.get("/brokerage/shorts", response_class=HTMLResponse)
def brokerage_shorts_page(session_token: Optional[str] = Cookie(None), ticker: str = None):
    """Short selling page."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)

    try:
        from banks.brokerage_firm import (
            CompanyShares, ShareholderPosition, ShareLoan, ShareLoanStatus,
            get_player_credit, get_credit_tier, get_short_borrow_rate,
            SHORT_COLLATERAL_REQUIREMENT, CREDIT_TIERS,
            get_db as get_firm_db
        )

        # Credit tier info for this player
        credit_rating = get_player_credit(player.id)
        credit_tier = get_credit_tier(credit_rating.credit_score)
        borrow_rate_annual = get_short_borrow_rate(player.id)
        credit_tier_name = credit_tier.value.upper()
        # Find next tier requirements
        tier_rows = sorted(CREDIT_TIERS.values(), key=lambda x: x[0])  # sort by min_score

        db = get_firm_db()
        try:
            # Get all public companies
            companies = db.query(CompanyShares).filter(
                CompanyShares.is_delisted == False
            ).order_by(CompanyShares.ticker_symbol).all()

            # Get player's active shorts
            active_shorts = db.query(ShareLoan).filter(
                ShareLoan.borrower_player_id == player.id,
                ShareLoan.status == ShareLoanStatus.ACTIVE.value
            ).all()
            
            # Build short positions data
            short_data = []
            for short in active_shorts:
                company = db.query(CompanyShares).filter(
                    CompanyShares.id == short.company_shares_id
                ).first()
                if company:
                    current_value = short.shares_borrowed * company.current_price
                    original_value = short.shares_borrowed * short.borrow_price
                    pnl = original_value - current_value  # Profit if price dropped
                    short_data.append({
                        "loan": short,
                        "company": company,
                        "current_value": current_value,
                        "original_value": original_value,
                        "pnl": pnl
                    })
            
            # Selected company for new short
            selected_company = None
            available_to_short = 0
            if ticker:
                selected_company = db.query(CompanyShares).filter(
                    CompanyShares.ticker_symbol == ticker.upper()
                ).first()
            
            short_interest_pct = 0.0
            si_multiplier = 1.0
            float_remaining_pct = 1.0
            if selected_company:
                # Find shares available to borrow (firm first, then others)
                available_positions = db.query(ShareholderPosition).filter(
                    ShareholderPosition.company_shares_id == selected_company.id,
                    ShareholderPosition.shares_available_to_lend > 0,
                    ShareholderPosition.player_id != player.id
                ).all()
                available_to_short = sum(p.shares_available_to_lend for p in available_positions)
                # Short interest stats
                from sqlalchemy import func as _func
                from banks.brokerage_firm import ShareLoan as _SL, ShareLoanStatus as _SLS, MAX_SHORT_FLOAT_PCT, get_short_interest_multiplier
                total_shorted = db.query(_func.sum(_SL.shares_borrowed)).filter(
                    _SL.company_shares_id == selected_company.id,
                    _SL.status == _SLS.ACTIVE.value,
                ).scalar() or 0
                if selected_company.shares_in_float:
                    short_interest_pct = total_shorted / selected_company.shares_in_float * 100
                    float_remaining_pct = max(0.0, (selected_company.shares_in_float * MAX_SHORT_FLOAT_PCT - total_shorted) / selected_company.shares_in_float * 100)
                si_multiplier = get_short_interest_multiplier(selected_company.id)

            player_credit = get_player_credit(player.id)
            
        finally:
            db.close()
        
        # Build company selector
        company_options = ""
        for company in companies:
            selected = "selected" if selected_company and company.id == selected_company.id else ""
            company_options += f'<option value="{company.ticker_symbol}" {selected}>{company.ticker_symbol} - {company.company_name}</option>'
        
        # Build active shorts table
        shorts_html = ""
        if short_data:
            shorts_html = '''
            <table style="width: 100%; border-collapse: collapse;">
                <thead>
                    <tr style="border-bottom: 1px solid #1e293b; text-align: left;">
                        <th style="padding: 10px 8px;">Symbol</th>
                        <th style="padding: 10px 8px;">Shares</th>
                        <th style="padding: 10px 8px;">Borrow Price</th>
                        <th style="padding: 10px 8px;">Current Price</th>
                        <th style="padding: 10px 8px;">P/L</th>
                        <th style="padding: 10px 8px;">Collateral Left</th>
                        <th style="padding: 10px 8px;">Borrow Rate</th>
                        <th style="padding: 10px 8px;">Action</th>
                    </tr>
                </thead>
                <tbody>'''
            
            for item in short_data:
                loan = item["loan"]
                company = item["company"]
                pnl_color = "#22c55e" if item["pnl"] >= 0 else "#ef4444"
                # Collateral health: estimate days remaining based on daily borrow fee
                daily_fee = loan.shares_borrowed * loan.borrow_price * loan.borrow_rate_weekly / 7
                days_left = (loan.collateral_locked / daily_fee) if daily_fee > 0 else 9999
                if days_left < 3:
                    coll_color = "#ef4444"
                    coll_label = f"⚠ {fmt_usd(loan.collateral_locked, disp)} (~{days_left:.0f}d)"
                elif days_left < 7:
                    coll_color = "#f59e0b"
                    coll_label = f"{fmt_usd(loan.collateral_locked, disp)} (~{days_left:.0f}d)"
                else:
                    coll_color = "#94a3b8"
                    coll_label = fmt_usd(loan.collateral_locked, disp)
                annual_rate_pct = loan.borrow_rate_weekly * 52 * 100

                shorts_html += f'''
                <tr style="border-bottom: 1px solid #1e293b;">
                    <td style="padding: 10px 8px;"><strong>{company.ticker_symbol}</strong></td>
                    <td style="padding: 10px 8px;">{loan.shares_borrowed:,}</td>
                    <td style="padding: 10px 8px;">{fmt_usd(loan.borrow_price, disp, precision=4)}</td>
                    <td style="padding: 10px 8px;">{fmt_usd(company.current_price, disp, precision=4)}</td>
                    <td style="padding: 10px 8px; color: {pnl_color};">{fmt_usd(item["pnl"], disp)}</td>
                    <td style="padding: 10px 8px; color: {coll_color};">{coll_label}</td>
                    <td style="padding: 10px 8px; color: #64748b;">{annual_rate_pct:.1f}% p.a.</td>
                    <td style="padding: 10px 8px;">
                        <form action="/api/brokerage/close-short" method="post" style="display: inline;">
                            <input type="hidden" name="loan_id" value="{loan.id}">
                            <button type="submit" class="btn-orange" style="padding: 4px 8px; font-size: 0.8rem;">Close</button>
                        </form>
                    </td>
                </tr>'''
            
            shorts_html += '</tbody></table>'
        else:
            shorts_html = '<p style="color: #64748b;">No active short positions.</p>'

        # Pre-build short info to avoid nested f-string syntax issues
        short_info_html = ""
        if selected_company:
            si_color = "#22c55e" if short_interest_pct < 25 else ("#f59e0b" if short_interest_pct < 50 else "#ef4444")
            adjusted_rate_pct = borrow_rate_annual * si_multiplier * 100
            si_warning = ""
            if si_multiplier > 1.0:
                si_warning = f'<p style="color:#ef4444;font-size:0.85rem;margin-top:6px;">⚠ High short interest ({short_interest_pct:.1f}% of float) — borrow rate elevated {si_multiplier:.1f}×</p>'
            cap_warning = ""
            if float_remaining_pct < 10:
                cap_warning = f'<p style="color:#ef4444;font-size:0.85rem;">⚠ Near float cap — only {float_remaining_pct:.1f}% of shortable float remaining</p>'
            short_info_html = f'''
                <div style="margin-top: 15px; padding: 15px; background: #0f172a; border-radius: 4px;">
                    <p><strong>Selected:</strong> {selected_company.ticker_symbol} @ {fmt_usd(selected_company.current_price, disp, precision=4)}</p>
                    <p><strong>Available to borrow:</strong> {available_to_short:,} shares</p>
                    <p><strong>Short Interest:</strong> <span style="color:{si_color};">{short_interest_pct:.1f}% of float</span>
                       &nbsp;(max {MAX_SHORT_FLOAT_PCT*100:.0f}% — {float_remaining_pct:.1f}% remaining capacity)</p>
                    <p><strong>Effective borrow rate:</strong> {adjusted_rate_pct:.1f}% p.a.
                       {f"({borrow_rate_annual*100:.1f}% base × {si_multiplier:.1f}×)" if si_multiplier > 1 else "(base rate)"}</p>
                    {si_warning}{cap_warning}
                    <p style="margin-top:8px;"><strong>Collateral locked (150%):</strong> {fmt_usd(selected_company.current_price * SHORT_COLLATERAL_REQUIREMENT, disp, precision=4)}/share</p>
                    <p><strong>Short-sale proceeds credited (100%):</strong> {fmt_usd(selected_company.current_price, disp, precision=4)}/share</p>
                    <p><strong>Net out-of-pocket (50% additional margin):</strong> {fmt_usd(selected_company.current_price * (SHORT_COLLATERAL_REQUIREMENT - 1.0), disp, precision=4)}/share</p>
                    <p style="color: #f59e0b; font-size: 0.85rem; margin-top: 10px;">
                        Short sellers owe dividends to the lender — dividend payments are deducted from your collateral.
                        If the price rises, your losses are theoretically unlimited. Lenders may recall shares at any time.
                    </p>
                </div>'''

        tier_color = {"prime": "#22c55e", "good": "#38bdf8", "fair": "#f59e0b", "poor": "#f97316", "restricted": "#ef4444"}.get(credit_tier.value, "#94a3b8")
        body = f'''
        <a href="/banks/brokerage-firm" style="color: #38bdf8;">← Brokerage Firm</a>
        <h1>Short Selling</h1>
        <p style="color: #64748b;">Borrow shares, sell them now, buy back later at (hopefully) a lower price.</p>

        <!-- Credit Tier Banner -->
        <div class="card" style="margin-bottom: 20px; padding: 15px; background: #0f172a; border-left: 4px solid {tier_color};">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 15px;">
                <div>
                    <span style="color: #64748b; font-size: 0.85rem;">YOUR CREDIT TIER</span><br>
                    <strong style="color: {tier_color}; font-size: 1.2rem;">{credit_tier_name}</strong>
                    <span style="color: #64748b; margin-left: 8px;">Score: {credit_rating.credit_score}/100</span>
                </div>
                <div style="text-align: center;">
                    <span style="color: #64748b; font-size: 0.85rem;">BORROW RATE</span><br>
                    <strong style="color: #f59e0b;">{borrow_rate_annual*100:.1f}% p.a.</strong>
                </div>
                <div style="text-align: center;">
                    <span style="color: #64748b; font-size: 0.85rem;">DAILY FEE (per $1,000 short)</span><br>
                    <strong style="color: #94a3b8;">{fmt_usd(1000 * borrow_rate_annual / 365, disp, precision=4)}</strong>
                </div>
                <div style="font-size: 0.8rem; color: #64748b; max-width: 300px;">
                    Improve your credit score by closing profitable positions, paying dividends, and repaying loans on time.
                    Higher tiers unlock lower borrow rates and greater leverage.
                </div>
            </div>
        </div>

        <!-- Open New Short -->
        <div class="card">
            <h3>Open Short Position</h3>
            <form action="/api/brokerage/short-sell" method="post">
                <div style="display: grid; grid-template-columns: 1fr 1fr 1fr auto; gap: 15px; align-items: end;">
                    <div>
                        <label style="display: block; margin-bottom: 5px; color: #94a3b8;">Select Stock</label>
                        <select name="ticker" required style="width: 100%; padding: 10px;" onchange="window.location.href='/brokerage/shorts?ticker='+this.value">
                            <option value="">Choose a stock...</option>
                            {company_options}
                        </select>
                    </div>
                    <div>
                        <label style="display: block; margin-bottom: 5px; color: #94a3b8;">Shares to Short</label>
                        <input type="number" name="quantity" min="1" {"max=" + str(available_to_short) if selected_company else ""} required 
                               style="width: 100%; padding: 10px;" placeholder="{"Max: " + str(available_to_short) if selected_company else "Select stock first"}">
                    </div>
                    <div>
                        <label style="display: block; margin-bottom: 5px; color: #94a3b8;">Net Out-of-Pocket (50%)</label>
                        <div style="padding: 10px; background: #020617; border: 1px solid #1e293b; border-radius: 4px;">
                            {f"{fmt_usd(selected_company.current_price * (SHORT_COLLATERAL_REQUIREMENT - 1.0), disp)}/share" if selected_company else "N/A"}
                        </div>
                    </div>
                    <button type="submit" class="btn-red" style="padding: 10px 20px;" {"disabled" if not selected_company or available_to_short == 0 else ""}>
                        Short Sell
                    </button>
                </div>
                
                {short_info_html}
            </form>
        </div>
        
        <!-- Active Short Positions -->
        <div class="card" style="margin-top: 20px;">
            <h3>Active Short Positions</h3>
            {shorts_html}
        </div>
        
        <!-- How It Works -->
        <div class="card" style="margin-top: 20px;">
            <h3>How Short Selling Works</h3>
            <ol style="color: #94a3b8; line-height: 2;">
                <li>You borrow shares from another player. <strong>{SHORT_COLLATERAL_REQUIREMENT*100:.0f}% collateral</strong> is locked from your account and the 100% short-sale proceeds are immediately credited back — your net out-of-pocket is <strong>50% additional margin</strong>.</li>
                <li>You can now hold the proceeds while waiting for the price to fall.</li>
                <li>When you close, you buy back the shares at the current market price.</li>
                <li>Your locked collateral (minus fees) is returned. Profit = original sale price − buyback price − borrow fees.</li>
                <li>Daily borrow fees are deducted from your locked collateral. If collateral runs below ~3 days of fees, the position is <strong>automatically force-closed</strong> and your credit score takes a major hit (−20 pts).</li>
            </ol>
            <p style="color: #ef4444; margin-top: 15px;">
                <strong>Risk Warning:</strong> If the stock price rises, your buyback cost increases and losses are theoretically unlimited.
                Monitor your collateral balance — if it drains to zero the position is liquidated without warning.
            </p>

            <!-- Credit Tier Table -->
            <h4 style="color: #94a3b8; margin-top: 20px; margin-bottom: 10px;">Borrow Rate by Credit Tier</h4>
            <table style="width: 100%; border-collapse: collapse; font-size: 0.85rem;">
                <thead>
                    <tr style="border-bottom: 1px solid #1e293b; text-align: left; color: #64748b;">
                        <th style="padding: 6px 8px;">Tier</th>
                        <th style="padding: 6px 8px;">Score Range</th>
                        <th style="padding: 6px 8px;">Annual Borrow Rate</th>
                        <th style="padding: 6px 8px;">Credit Impact (voluntary close)</th>
                    </tr>
                </thead>
                <tbody>
                    <tr style="border-bottom: 1px solid #1e293b; color: #22c55e;">
                        <td style="padding: 6px 8px;">PRIME</td><td style="padding: 6px 8px;">80–100</td><td style="padding: 6px 8px;">3% p.a.</td><td style="padding: 6px 8px;">+3 (profit) / −1 (loss)</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #1e293b; color: #38bdf8;">
                        <td style="padding: 6px 8px;">GOOD</td><td style="padding: 6px 8px;">60–79</td><td style="padding: 6px 8px;">5% p.a.</td><td style="padding: 6px 8px;">+3 (profit) / −1 (loss)</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #1e293b; color: #f59e0b;">
                        <td style="padding: 6px 8px;">FAIR</td><td style="padding: 6px 8px;">40–59</td><td style="padding: 6px 8px;">8% p.a.</td><td style="padding: 6px 8px;">+3 (profit) / −1 (loss)</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #1e293b; color: #f97316;">
                        <td style="padding: 6px 8px;">POOR</td><td style="padding: 6px 8px;">20–39</td><td style="padding: 6px 8px;">12% p.a.</td><td style="padding: 6px 8px;">+3 (profit) / −1 (loss)</td>
                    </tr>
                    <tr style="color: #ef4444;">
                        <td style="padding: 6px 8px;">RESTRICTED</td><td style="padding: 6px 8px;">0–19</td><td style="padding: 6px 8px;">15% p.a.</td><td style="padding: 6px 8px;">+3 (profit) / −1 (loss)</td>
                    </tr>
                </tbody>
            </table>
            <p style="color: #64748b; font-size: 0.8rem; margin-top: 8px;">
                Force-close (collateral exhausted): −20 pts regardless of P&L.
                Borrow rate is locked at the rate of your tier when you open the position.
            </p>
        </div>
        '''
        
        return shell("Short Selling", body, player.cash_balance, player.id)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return shell("Short Selling", f"Error: {e}", player.cash_balance, player.id)


@router.get("/brokerage/commodities", response_class=HTMLResponse)
def brokerage_commodities_page(session_token: Optional[str] = Cookie(None)):
    """WCE Commodity lending page."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)

    try:
        from banks.brokerage_firm import (
            CommodityListing, CommodityLoan, CommodityLoanStatus,
            COLLATERAL_REQUIREMENT, LENDING_FEE_SPLIT,
            get_db as get_firm_db
        )
        import inventory as inv_mod
        
        db = get_firm_db()
        try:
            # Get all active commodity listings
            listings = db.query(CommodityListing).filter(
                CommodityListing.is_active == True,
                CommodityListing.quantity_available > CommodityListing.quantity_lent_out
            ).all()
            
            # Get player's listings
            player_listings = db.query(CommodityListing).filter(
                CommodityListing.lender_player_id == player.id,
                CommodityListing.is_active == True
            ).all()
            
            # Get player's active loans (as borrower)
            player_loans = db.query(CommodityLoan).filter(
                CommodityLoan.borrower_player_id == player.id,
                CommodityLoan.status.in_([CommodityLoanStatus.ACTIVE.value, CommodityLoanStatus.LATE.value])
            ).all()
            
            # Get player's loans (as lender)
            lent_out = db.query(CommodityLoan).filter(
                CommodityLoan.lender_player_id == player.id,
                CommodityLoan.status.in_([CommodityLoanStatus.ACTIVE.value, CommodityLoanStatus.LATE.value])
            ).all()
            
        finally:
            db.close()
        
        # Get player inventory for listing
        player_inv = inv_mod.get_player_inventory(player.id)
        
        # Build available listings table — exclude fund/ETF shares which belong
        # on the ETF Trading Floor, not the commodity lending market.
        listings_html = ""
        commodity_listings = [l for l in listings if not l.item_type.endswith("_shares")]
        if commodity_listings:
            listings_html = '''
            <table style="width: 100%; border-collapse: collapse;">
                <thead>
                    <tr style="border-bottom: 1px solid #1e293b; text-align: left;">
                        <th style="padding: 10px 8px;">Item</th>
                        <th style="padding: 10px 8px;">Available</th>
                        <th style="padding: 10px 8px;">Weekly Rate</th>
                        <th style="padding: 10px 8px;">Lender</th>
                        <th style="padding: 10px 8px;">Action</th>
                    </tr>
                </thead>
                <tbody>'''

            for listing in commodity_listings:
                available = listing.quantity_available - listing.quantity_lent_out
                is_own = listing.lender_player_id == player.id

                # Pre-build borrow form to avoid nested f-string issues
                borrow_action_html = "-"
                if not is_own:
                    borrow_action_html = f'''
                        <form action="/api/brokerage/borrow-commodity" method="post" style="display: flex; gap: 5px;">
                            <input type="hidden" name="listing_id" value="{listing.id}">
                            <input type="number" name="quantity" min="1" max="{available}" placeholder="Qty" style="width: 80px; padding: 4px;">
                            <button type="submit" class="btn-blue" style="padding: 4px 8px; font-size: 0.8rem;">Borrow</button>
                        </form>'''

                listings_html += f'''
                <tr style="border-bottom: 1px solid #1e293b;">
                    <td style="padding: 10px 8px;"><strong>{listing.item_type.replace("_", " ").title()}</strong></td>
                    <td style="padding: 10px 8px;">{available:,.0f}</td>
                    <td style="padding: 10px 8px;">{listing.weekly_rate*100:.1f}%</td>
                    <td style="padding: 10px 8px;">{"YOU" if is_own else f"Player {listing.lender_player_id}"}</td>
                    <td style="padding: 10px 8px;">
                        {borrow_action_html}
                    </td>
                </tr>'''
            
            listings_html += '</tbody></table>'
        elif not commodity_listings:
            listings_html = '<p style="color: #64748b;">No commodities available for borrowing.</p>'
        
        # Build player's loans table
        loans_html = ""
        if player_loans:
            loans_html = '''
            <table style="width: 100%; border-collapse: collapse;">
                <thead>
                    <tr style="border-bottom: 1px solid #1e293b; text-align: left;">
                        <th style="padding: 10px 8px;">Item</th>
                        <th style="padding: 10px 8px;">Qty</th>
                        <th style="padding: 10px 8px;">Collateral</th>
                        <th style="padding: 10px 8px;">Due</th>
                        <th style="padding: 10px 8px;">Status</th>
                        <th style="padding: 10px 8px;">Actions</th>
                    </tr>
                </thead>
                <tbody>'''
            
            for loan in player_loans:
                status_color = "#f59e0b" if loan.status == CommodityLoanStatus.LATE.value else "#22c55e"
                
                loans_html += f'''
                <tr style="border-bottom: 1px solid #1e293b;">
                    <td style="padding: 10px 8px;"><strong>{loan.item_type.replace("_", " ").title()}</strong></td>
                    <td style="padding: 10px 8px;">{loan.quantity_borrowed:,.0f}</td>
                    <td style="padding: 10px 8px;">{fmt_usd(loan.collateral_locked, disp)}</td>
                    <td style="padding: 10px 8px;">{loan.due_date.strftime("%m/%d %H:%M")}</td>
                    <td style="padding: 10px 8px; color: {status_color};">{loan.status.upper()}</td>
                    <td style="padding: 10px 8px;">
                        <form action="/api/brokerage/return-commodity" method="post" style="display: inline;">
                            <input type="hidden" name="loan_id" value="{loan.id}">
                            <button type="submit" class="btn-blue" style="padding: 4px 8px; font-size: 0.8rem;">Return</button>
                        </form>
                        <form action="/api/brokerage/extend-loan" method="post" style="display: inline; margin-left: 5px;">
                            <input type="hidden" name="loan_id" value="{loan.id}">
                            <button type="submit" class="btn-orange" style="padding: 4px 8px; font-size: 0.8rem;" 
                                    {"disabled" if loan.extensions_used >= loan.max_extensions else ""}>Extend</button>
                        </form>
                    </td>
                </tr>'''
            
            loans_html += '</tbody></table>'
        else:
            loans_html = '<p style="color: #64748b;">You have no active commodity loans.</p>'
        
        # Build inventory for listing — fund/ETF shares (item_type ending in
        # "_shares") belong on the ETF Trading Floor, not the commodity market.
        inv_options = ""
        for item, qty in player_inv.items():
            if qty > 0 and not item.endswith("_shares"):
                inv_options += f'<option value="{item}">{item.replace("_", " ").title()} ({qty:,.0f} available)</option>'
        
        body = f'''
        <a href="/banks/brokerage-firm" style="color: #38bdf8;">← Brokerage Firm</a>
        <h1>WCE Commodity Exchange</h1>
        <p style="color: #64748b;">Borrow commodities from other players or lend your inventory for interest.</p>
        
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
            <!-- List Commodities for Lending -->
            <div class="card">
                <h3>List Your Commodities</h3>
                <form action="/api/brokerage/list-commodity" method="post">
                    <div style="margin-bottom: 15px;">
                        <label style="display: block; margin-bottom: 5px; color: #94a3b8;">Item to Lend</label>
                        <select name="item_type" required style="width: 100%; padding: 10px;">
                            <option value="">Select item...</option>
                            {inv_options}
                        </select>
                    </div>
                    <div style="margin-bottom: 15px;">
                        <label style="display: block; margin-bottom: 5px; color: #94a3b8;">Quantity</label>
                        <input type="number" name="quantity" min="1" required style="width: 100%; padding: 10px;">
                    </div>
                    <div style="margin-bottom: 15px;">
                        <label style="display: block; margin-bottom: 5px; color: #94a3b8;">Weekly Interest Rate (%)</label>
                        <input type="number" name="weekly_rate" min="0.1" step="0.1" value="5" required style="width: 100%; padding: 10px;">
                    </div>
                    <button type="submit" class="btn-blue" style="width: 100%;">List for Lending</button>
                </form>
                <p style="font-size: 0.8rem; color: #64748b; margin-top: 10px;">
                    You receive {(1-LENDING_FEE_SPLIT)*100:.0f}% of fees, Firm keeps {LENDING_FEE_SPLIT*100:.0f}%.
                </p>
            </div>
            
            <!-- Your Listings -->
            <div class="card">
                <h3>Your Active Listings</h3>
                {generate_player_listings_html(player_listings) if player_listings else '<p style="color: #64748b;">No active listings.</p>'}
            </div>
        </div>
        
        <!-- Available to Borrow -->
        <div class="card" style="margin-top: 20px;">
            <h3>Available to Borrow</h3>
            <p style="color: #64748b; margin-bottom: 15px;">Collateral requirement: {COLLATERAL_REQUIREMENT*100:.0f}% of market value</p>
            {listings_html}
        </div>
        
        <!-- Your Active Loans -->
        <div class="card" style="margin-top: 20px;">
            <h3>Your Active Loans (Borrowed)</h3>
            {loans_html}
        </div>
        
        <!-- Lent Out -->
        <div class="card" style="margin-top: 20px;">
            <h3>Your Commodities Lent Out</h3>
            {generate_lent_out_html(lent_out, disp) if lent_out else '<p style="color: #64748b;">None of your commodities are currently lent out.</p>'}
        </div>
        '''
        
        return shell("WCE Commodities", body, player.cash_balance, player.id)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return shell("WCE Commodities", f"Error: {e}", player.cash_balance, player.id)


@router.get("/brokerage/credit", response_class=HTMLResponse)
def brokerage_credit_page(session_token: Optional[str] = Cookie(None)):
    """Credit rating and liens page."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)

    try:
        from banks.brokerage_firm import (
            get_player_credit, get_credit_tier, get_max_leverage_for_player,
            get_credit_interest_rate, BrokerageLien, CREDIT_TIERS, CREDIT_MODIFIERS,
            get_db as get_firm_db
        )
        
        player_credit = get_player_credit(player.id)
        credit_tier = get_credit_tier(player_credit.credit_score)
        max_leverage = get_max_leverage_for_player(player.id)
        interest_rate = get_credit_interest_rate(player.id)
        
        db = get_firm_db()
        try:
            liens = db.query(BrokerageLien).filter(
                BrokerageLien.player_id == player.id
            ).all()
            
            total_lien_debt = sum(l.principal + l.interest_accrued - l.total_paid for l in liens)
        finally:
            db.close()
        
        # Credit tier colors
        tier_colors = {
            "prime": "#22c55e",
            "standard": "#38bdf8",
            "fair": "#f59e0b",
            "subprime": "#ef4444",
            "junk": "#7f1d1d"
        }
        tier_color = tier_colors.get(player_credit.tier, "#64748b")
        
        # Build credit tiers reference
        tiers_html = ""
        for tier, (min_score, max_score, rate, leverage, _) in CREDIT_TIERS.items():
            is_current = tier == credit_tier
            border = f"border: 2px solid {tier_colors.get(tier.value, '#64748b')};" if is_current else ""
            tiers_html += f'''
            <div style="padding: 10px; background: #0f172a; border-radius: 4px; {border}">
                <div style="color: {tier_colors.get(tier.value, '#64748b')}; font-weight: bold;">{tier.value.upper()}</div>
                <div style="font-size: 0.85rem; color: #94a3b8;">Score: {min_score}-{max_score}</div>
                <div style="font-size: 0.85rem; color: #94a3b8;">Rate: {rate*100:.0f}%</div>
                <div style="font-size: 0.85rem; color: #94a3b8;">Leverage: {leverage:.0f}x</div>
            </div>'''
        
        # Build liens table
        liens_html = ""
        if liens:
            liens_html = '''
            <table style="width: 100%; border-collapse: collapse;">
                <thead>
                    <tr style="border-bottom: 1px solid #1e293b; text-align: left;">
                        <th style="padding: 10px 8px;">Source</th>
                        <th style="padding: 10px 8px;">Principal</th>
                        <th style="padding: 10px 8px;">Interest</th>
                        <th style="padding: 10px 8px;">Paid</th>
                        <th style="padding: 10px 8px;">Balance</th>
                        <th style="padding: 10px 8px;">Created</th>
                    </tr>
                </thead>
                <tbody>'''
            
            for lien in liens:
                balance = lien.principal + lien.interest_accrued - lien.total_paid
                liens_html += f'''
                <tr style="border-bottom: 1px solid #1e293b;">
                    <td style="padding: 10px 8px;">{lien.source.upper()}</td>
                    <td style="padding: 10px 8px;">{fmt_usd(lien.principal, disp)}</td>
                    <td style="padding: 10px 8px; color: #ef4444;">{fmt_usd(lien.interest_accrued, disp)}</td>
                    <td style="padding: 10px 8px; color: #22c55e;">{fmt_usd(lien.total_paid, disp)}</td>
                    <td style="padding: 10px 8px; font-weight: bold; color: #ef4444;">{fmt_usd(balance, disp)}</td>
                    <td style="padding: 10px 8px; color: #64748b;">{lien.created_at.strftime("%Y-%m-%d")}</td>
                </tr>'''
            
            liens_html += '</tbody></table>'
        else:
            liens_html = '<p style="color: #22c55e;">No active liens. Your account is in good standing.</p>'

        # Pre-build lien debt info to avoid nested f-string syntax issues
        lien_debt_info_html = ""
        if total_lien_debt > 0:
            lien_debt_info_html = f'''
            <div style="margin-top: 15px; padding: 15px; background: #450a0a; border-radius: 4px; border: 1px solid #7f1d1d;">
                <p style="color: #fca5a5;">
                    <strong>Total Lien Debt: {fmt_usd(total_lien_debt, disp)}</strong><br>
                    The Firm automatically garnishes 50% of your cash every 60 seconds to pay down liens.
                    Interest accrues at {interest_rate*100:.0f}% annually.
                </p>
            </div>'''

        body = f'''
        <a href="/banks/brokerage-firm" style="color: #38bdf8;">← Brokerage Firm</a>
        <h1>Credit Rating & Liens</h1>
        
        <!-- Credit Score Display -->
        <div class="card">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h2 style="margin: 0;">Your Credit Score</h2>
                    <p style="color: #64748b;">Based on your trading history with the Firm</p>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 4rem; font-weight: bold; color: {tier_color};">{player_credit.credit_score}</div>
                    <div style="font-size: 1.2rem; color: {tier_color}; text-transform: uppercase;">{player_credit.tier}</div>
                </div>
            </div>
            
            <!-- Credit Score Bar -->
            <div style="margin-top: 20px; background: #020617; border-radius: 8px; height: 20px; overflow: hidden;">
                <div style="width: {player_credit.credit_score}%; height: 100%; background: linear-gradient(90deg, #ef4444, #f59e0b, #22c55e); border-radius: 8px;"></div>
            </div>
            <div style="display: flex; justify-content: space-between; margin-top: 5px; font-size: 0.8rem; color: #64748b;">
                <span>0 (Junk)</span>
                <span>50 (Fair)</span>
                <span>100 (Prime)</span>
            </div>
        </div>
        
        <!-- Your Benefits -->
        <div class="card" style="margin-top: 20px;">
            <h3>Your Credit Benefits</h3>
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px;">
                <div style="text-align: center; padding: 20px; background: #0f172a; border-radius: 8px;">
                    <div style="font-size: 0.9rem; color: #64748b;">Max Leverage</div>
                    <div style="font-size: 2rem; font-weight: bold; color: #38bdf8;">{max_leverage:.1f}x</div>
                </div>
                <div style="text-align: center; padding: 20px; background: #0f172a; border-radius: 8px;">
                    <div style="font-size: 0.9rem; color: #64748b;">Interest Rate</div>
                    <div style="font-size: 2rem; font-weight: bold; color: {'#22c55e' if interest_rate < 0.05 else '#f59e0b' if interest_rate < 0.10 else '#ef4444'};">{interest_rate*100:.0f}%</div>
                </div>
                <div style="text-align: center; padding: 20px; background: #0f172a; border-radius: 8px;">
                    <div style="font-size: 0.9rem; color: #64748b;">Lien Balance</div>
                    <div style="font-size: 2rem; font-weight: bold; color: {'#ef4444' if total_lien_debt > 0 else '#22c55e'};">{fmt_usd(total_lien_debt, disp, precision=0)}</div>
                </div>
            </div>
        </div>
        
        <!-- Credit History -->
        <div class="card" style="margin-top: 20px;">
            <h3>Credit History</h3>
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px;">
                <div>
                    <div style="color: #64748b; font-size: 0.85rem;">Total Margin Trades</div>
                    <div style="font-size: 1.5rem;">{player_credit.total_margin_trades}</div>
                </div>
                <div>
                    <div style="color: #64748b; font-size: 0.85rem;">Profitable Trades</div>
                    <div style="font-size: 1.5rem; color: #22c55e;">{player_credit.profitable_margin_trades}</div>
                </div>
                <div>
                    <div style="color: #64748b; font-size: 0.85rem;">Commodity Loans</div>
                    <div style="font-size: 1.5rem;">{player_credit.total_commodity_loans}</div>
                </div>
                <div>
                    <div style="color: #64748b; font-size: 0.85rem;">On-Time Returns</div>
                    <div style="font-size: 1.5rem; color: #22c55e;">{player_credit.on_time_returns}</div>
                </div>
            </div>
        </div>
        
        <!-- Active Liens -->
        <div class="card" style="margin-top: 20px;">
            <h3>Brokerage Liens</h3>
            {liens_html}
            {lien_debt_info_html}
        </div>
        
        <!-- Credit Tiers Reference -->
        <div class="card" style="margin-top: 20px;">
            <h3>Credit Tiers Reference</h3>
            <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px;">
                {tiers_html}
            </div>
        </div>
        
        <!-- Credit Modifiers Reference -->
        <div class="card" style="margin-top: 20px;">
            <h3>How to Improve Your Score</h3>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                <div>
                    <h4 style="color: #22c55e;">Positive Actions</h4>
                    <ul style="color: #94a3b8; line-height: 1.8;">
                        <li>Profitable margin trades: +2</li>
                        <li>Return commodities on time: +3</li>
                        <li>Pay dividends to shareholders: +1</li>
                        <li>Successful business IPO: +5</li>
                        <li>Pay off liens: +10</li>
                        <li>Profitable short positions: +2</li>
                    </ul>
                </div>
                <div>
                    <h4 style="color: #ef4444;">Negative Actions</h4>
                    <ul style="color: #94a3b8; line-height: 1.8;">
                        <li>Margin call triggered: -10</li>
                        <li>Commodity default: -20</li>
                        <li>Return commodities late: -5</li>
                        <li>Skip dividend while profitable: -3</li>
                        <li>Lien created: -15</li>
                        <li>Short position default: -15</li>
                        <li>Take company private: -10</li>
                    </ul>
                </div>
            </div>
        </div>
        '''
        
        return shell("Credit & Liens", body, player.cash_balance, player.id)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return shell("Credit & Liens", f"Error: {e}", player.cash_balance, player.id)


# ==========================
# HELPER FUNCTIONS FOR BROKERAGE UX
# ==========================

def generate_short_positions_summary(short_positions, disp=None) -> str:
    from reserve_banks import fmt_usd
    if disp is None:
        disp = {"code": "USD", "symbol": "$", "usd_per_unit": 1.0, "flag": "\U0001f1fa\U0001f1f8"}
    """Generate HTML summary of short positions for dashboard."""
    from banks.brokerage_firm import CompanyShares, get_db as get_firm_db
    
    if not short_positions:
        return '<p style="color: #64748b;">No active shorts</p>'
    
    html = '<ul style="list-style: none; padding: 0; margin: 0;">'
    db = get_firm_db()
    try:
        for short in short_positions[:3]:  # Show top 3
            company = db.query(CompanyShares).filter(
                CompanyShares.id == short.company_shares_id
            ).first()
            if company:
                pnl = (short.borrow_price - company.current_price) * short.shares_borrowed
                pnl_color = "#22c55e" if pnl >= 0 else "#ef4444"
                html += f'''
                <li style="padding: 8px 0; border-bottom: 1px solid #1e293b;">
                    <strong>{company.ticker_symbol}</strong>: {short.shares_borrowed} shares
                    <span style="float: right; color: {pnl_color};">{fmt_usd(pnl, disp, precision=0)}</span>
                </li>'''
    finally:
        db.close()
    
    html += '</ul>'
    if len(short_positions) > 3:
        html += f'<p style="color: #64748b; font-size: 0.85rem; margin-top: 10px;">+{len(short_positions)-3} more</p>'
    
    return html


def generate_commodity_loans_summary(commodity_loans) -> str:
    """Generate HTML summary of commodity loans for dashboard."""
    if not commodity_loans:
        return '<p style="color: #64748b;">No active loans</p>'
    
    html = '<ul style="list-style: none; padding: 0; margin: 0;">'
    for loan in commodity_loans[:3]:  # Show top 3
        status_color = "#f59e0b" if loan.status == "late" else "#38bdf8"
        html += f'''
        <li style="padding: 8px 0; border-bottom: 1px solid #1e293b;">
            <strong>{loan.item_type.replace("_", " ").title()}</strong>: {loan.quantity_borrowed:,.0f}
            <span style="float: right; color: {status_color};">{loan.due_date.strftime("%m/%d")}</span>
        </li>'''
    
    html += '</ul>'
    if len(commodity_loans) > 3:
        html += f'<p style="color: #64748b; font-size: 0.85rem; margin-top: 10px;">+{len(commodity_loans)-3} more</p>'
    
    return html


def generate_player_listings_html(listings) -> str:
    """Generate HTML for player's commodity listings."""
    if not listings:
        return '<p style="color: #64748b;">No active listings.</p>'
    
    html = '<ul style="list-style: none; padding: 0; margin: 0;">'
    for listing in listings:
        available = listing.quantity_available - listing.quantity_lent_out
        html += f'''
        <li style="padding: 10px; margin-bottom: 8px; background: #020617; border-radius: 4px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <strong>{listing.item_type.replace("_", " ").title()}</strong><br>
                    <span style="color: #64748b; font-size: 0.85rem;">
                        {available:,.0f} / {listing.quantity_available:,.0f} available | {listing.weekly_rate*100:.1f}%/week
                    </span>
                </div>
                <form action="/api/brokerage/cancel-listing" method="post">
                    <input type="hidden" name="listing_id" value="{listing.id}">
                    <button type="submit" class="btn-red" style="padding: 4px 8px; font-size: 0.8rem;">Cancel</button>
                </form>
            </div>
        </li>'''
    html += '</ul>'
    return html


def generate_lent_out_html(loans, disp=None) -> str:
    from reserve_banks import fmt_usd
    if disp is None:
        disp = {"code": "USD", "symbol": "$", "usd_per_unit": 1.0, "flag": "\U0001f1fa\U0001f1f8"}
    """Generate HTML for commodities lent out by player."""
    if not loans:
        return '<p style="color: #64748b;">None lent out.</p>'
    
    html = '''
    <table style="width: 100%; border-collapse: collapse;">
        <thead>
            <tr style="border-bottom: 1px solid #1e293b; text-align: left;">
                <th style="padding: 8px;">Item</th>
                <th style="padding: 8px;">Qty</th>
                <th style="padding: 8px;">Borrower</th>
                <th style="padding: 8px;">Due</th>
                <th style="padding: 8px;">Fees Earned</th>
            </tr>
        </thead>
        <tbody>'''
    
    for loan in loans:
        html += f'''
        <tr style="border-bottom: 1px solid #1e293b;">
            <td style="padding: 8px;">{loan.item_type.replace("_", " ").title()}</td>
            <td style="padding: 8px;">{loan.quantity_borrowed:,.0f}</td>
            <td style="padding: 8px;">Player {loan.borrower_player_id}</td>
            <td style="padding: 8px;">{loan.due_date.strftime("%m/%d %H:%M")}</td>
            <td style="padding: 8px; color: #22c55e;">{fmt_usd(loan.fees_to_lender, disp)}</td>
        </tr>'''
    
    html += '</tbody></table>'
    return html

@router.get("/liens", response_class=HTMLResponse)
def liens_page(session_token: Optional[str] = Cookie(None)):
    """Detailed lien dashboard page."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return player
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)
    
    lien_info = get_player_lien_info(player.id)
    
    if not lien_info["has_lien"]:
        return shell(
            "Liens",
            """
            <a href="/" style="color: #38bdf8;">← Dashboard</a>
            <h1>Bank Liens</h1>
            <div class="card">
                <h3 style="color: #22c55e;">✓ No Active Liens</h3>
                <p>You have no outstanding debts to any bank.</p>
            </div>
            """,
            player.cash_balance,
            player.id
        )
    
    # Status-based messaging
    status_messages = {
        "critical": {
            "color": "#dc2626",
            "icon": "🚨",
            "title": "CRITICAL DEBT",
            "message": "Your debt is severely impacting your financial position. The bank is garnishing 50% of all incoming cash."
        },
        "warning": {
            "color": "#f59e0b",
            "icon": "⚠️",
            "title": "MODERATE DEBT",
            "message": "You have a significant lien. Interest is accruing and automatic garnishment is active."
        },
        "ok": {
            "color": "#64748b",
            "icon": "📋",
            "title": "MINOR DEBT",
            "message": "You have a manageable lien. The bank is automatically collecting payments from your cash flow."
        }
    }
    
    status_info = status_messages.get(lien_info["status"], status_messages["ok"])
    
    # Calculate daily interest
    daily_interest = lien_info["total_owed"] * lien_info["interest_rate_per_minute"] * 60 * 24
    
    # Calculate time to pay off at current rate (rough estimate)
    if player.cash_balance > 0:
        estimated_payment_per_day = player.cash_balance * (lien_info["garnishment_rate"] / 100) * 60 * 24
        days_to_payoff = (lien_info["total_owed"] / estimated_payment_per_day) if estimated_payment_per_day > daily_interest else "∞"
        if days_to_payoff != "∞":
            days_to_payoff = f"{days_to_payoff:.1f} days"
    else:
        days_to_payoff = "Cannot estimate (no income)"
    
    lien_html = f"""
    <a href="/" style="color: #38bdf8;">← Dashboard</a>
    <h1>Bank Liens Dashboard</h1>
    
    <div class="card" style="border-color: {status_info['color']}; border-width: 2px;">
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 16px;">
            <span style="font-size: 2rem;">{status_info['icon']}</span>
            <div>
                <h2 style="margin: 0; color: {status_info['color']};">{status_info['title']}</h2>
                <p style="margin: 4px 0 0 0; color: #94a3b8;">{status_info['message']}</p>
            </div>
        </div>
        
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 24px;">
            <div>
                <div style="font-size: 0.85rem; color: #64748b; margin-bottom: 4px;">TOTAL OWED</div>
                <div style="font-size: 2rem; font-weight: bold; color: {status_info['color']};">
                    {fmt_usd(lien_info['total_owed'], disp)}
                </div>
            </div>
            <div>
                <div style="font-size: 0.85rem; color: #64748b; margin-bottom: 4px;">DAILY INTEREST</div>
                <div style="font-size: 2rem; font-weight: bold; color: #ef4444;">
                    +{fmt_usd(daily_interest, disp)}
                </div>
            </div>
        </div>
    </div>
    
    <div class="card">
        <h3>Debt Breakdown</h3>
        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; margin-top: 16px;">
            <div>
                <div style="font-size: 0.85rem; color: #64748b; margin-bottom: 8px;">Principal</div>
                <div style="font-size: 1.5rem; color: #e5e7eb;">{fmt_usd(lien_info['principal'], disp)}</div>
            </div>
            <div>
                <div style="font-size: 0.85rem; color: #64748b; margin-bottom: 8px;">Accrued Interest</div>
                <div style="font-size: 1.5rem; color: #ef4444;">{fmt_usd(lien_info['interest'], disp)}</div>
            </div>
            <div>
                <div style="font-size: 0.85rem; color: #64748b; margin-bottom: 8px;">Active Liens</div>
                <div style="font-size: 1.5rem; color: #38bdf8;">{lien_info['lien_count']}</div>
            </div>
        </div>
    </div>
    
    <div class="card">
        <h3>Payment Terms</h3>
        <div style="margin-top: 16px;">
            <div style="margin-bottom: 12px;">
                <strong style="color: #38bdf8;">Interest Rate:</strong> 
                <span>{lien_info['interest_rate_per_minute']:.4f}% per minute</span>
                <span style="color: #64748b; margin-left: 8px;">(~{lien_info['interest_rate_per_minute'] * 60 * 24:.2f}% daily, ~{lien_info['interest_rate_per_minute'] * 60 * 24 * 365:.1f}% annually)</span>
            </div>
            <div style="margin-bottom: 12px;">
                <strong style="color: #38bdf8;">Garnishment Rate:</strong> 
                <span>{lien_info['garnishment_rate']:.0f}% of available cash every 60 seconds</span>
            </div>
            <div style="margin-bottom: 12px;">
                <strong style="color: #38bdf8;">Estimated Payoff Time:</strong> 
                <span>{days_to_payoff}</span>
            </div>
        </div>
    </div>
    
    <div class="card" style="background: #0f172a; border-color: #1e293b;">
        <h3>How Liens Work</h3>
        <ul style="line-height: 1.8; color: #94a3b8;">
            <li><strong>Origin:</strong> Liens are created when a bank becomes insolvent and shareholders cannot pay their solvency levy.</li>
            <li><strong>Interest:</strong> Your debt grows by {lien_info['interest_rate_per_minute']:.4f}% every minute. This compounds continuously.</li>
            <li><strong>Garnishment:</strong> Every 60 seconds, the bank automatically takes {lien_info['garnishment_rate']:.0f}% of your cash balance to pay down the lien.</li>
            <li><strong>Priority:</strong> Payments are applied to interest first, then principal.</li>
            <li><strong>No Restrictions:</strong> You can continue trading, managing businesses, and operating normally while carrying a lien.</li>
            <li><strong>Payoff:</strong> Once your lien reaches $0.00, it will be automatically cleared from your record.</li>
        </ul>
    </div>
    
    <div class="card" style="background: #450a0a; border-color: #7f1d1d;">
        <h3 style="color: #fca5a5;">⚠️ Warning</h3>
        <p style="color: #fca5a5;">
            While you can continue normal operations, this debt will drain your cash reserves. 
            The longer the lien remains unpaid, the more interest accrues. Consider generating 
            cash flow through business operations or selling assets to accelerate payoff.
        </p>
    </div>
    """
    
    return shell("Liens", lien_html, player.cash_balance, player.id)

"""
PRODUCTION COSTS UX ROUTES
Add these routes to ux.py

Copy everything below into your ux.py file.
"""

# ==========================
# PRODUCTION COSTS PAGES
# ==========================

@router.get("/stats/production-costs", response_class=HTMLResponse)
def production_costs_page(
    session_token: Optional[str] = Cookie(None),
    mode: str = "vertical",
    category: str = "all",
    sort: str = "cost",
    order: str = "asc",
    search: str = ""
):
    """Interactive production cost explorer (vertical integration + WMA cost basis)."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)

    # Normalise mode
    if mode not in ("vertical", "cost_basis"):
        mode = "vertical"

    # ── shared palette ───────────────────────────────────────────────────────
    cat_colors = {
        "seeds": "#22c55e", "fruits": "#84cc16", "vegetables": "#16a34a",
        "crops": "#eab308", "food": "#f97316", "prepared_food": "#fb923c",
        "beverage": "#06b6d4", "alcohol": "#a855f7", "ingredients": "#ec4899",
        "livestock": "#92400e", "feed": "#a3e635", "health": "#ef4444",
        "personal_care": "#f472b6", "industrial": "#64748b", "materials": "#78716c",
        "textiles": "#c084fc", "wood": "#a16207", "ore": "#71717a",
        "metals": "#94a3b8", "components": "#6366f1", "auto_parts": "#3b82f6",
        "marine_parts": "#0ea5e9", "vehicle": "#2563eb", "apparel": "#d946ef",
        "accessories": "#e879f9", "home_goods": "#14b8a6", "packaging": "#737373",
        "media": "#facc15", "liquids": "#38bdf8", "energy": "#f59e0b",
        "financial": "#10b981", "luxury": "#d4af37", "minerals": "#a8a29e",
        "utilities": "#0891b2", "fuel": "#dc2626", "unknown": "#64748b"
    }

    def _cost_color(cost):
        if cost <= 0:   return "#64748b"
        if cost < 1:    return "#22c55e"
        if cost < 100:  return "#38bdf8"
        if cost < 1000: return "#f59e0b"
        return "#ef4444"

    # ── mode switcher (prominent, always visible) ────────────────────────────
    def _ms(m, label, icon, desc):
        active = mode == m
        bg  = "#1e40af" if active else "#1e293b"
        bdr = "2px solid #38bdf8" if active else "2px solid #334155"
        return (
            f'<a href="/stats/production-costs?mode={m}&category={category}'
            f'&sort={sort}&order={order}&search={search}" '
            f'style="display:flex;align-items:center;gap:10px;padding:14px 20px;'
            f'border-radius:8px;text-decoration:none;background:{bg};border:{bdr};'
            f'flex:1;min-width:220px;">'
            f'<span style="font-size:1.5rem;">{icon}</span>'
            f'<span><strong style="color:#e2e8f0;display:block;">{label}</strong>'
            f'<span style="color:#94a3b8;font-size:0.75rem;">{desc}</span></span>'
            f'</a>'
        )

    mode_switcher = f'''
    <div style="display:flex;gap:12px;flex-wrap:wrap;margin:18px 0 22px;">
        {_ms("vertical",   "Vertical Integration",
             "🏭", "Theoretical minimum — you produce every input yourself")}
        {_ms("cost_basis", "My Cost Basis",
             "📈", "Your real economics — built from actual purchase prices & exec/city buffs")}
    </div>'''

    try:
        # ════════════════════════════════════════════════════════════════════
        # MODE A — Vertical Integration (existing calculator)
        # ════════════════════════════════════════════════════════════════════
        if mode == "vertical":
            from production_costs import get_calculator
            calc    = get_calculator()
            summary = calc.get_summary()
            categories = calc.get_categories()

            if search:
                items = calc.search_items(search)
            elif category != "all":
                by_cat = calc.get_by_category()
                items  = by_cat.get(category, [])
            else:
                items = calc.get_all_items_sorted(sort_by=sort, ascending=(order == "asc"))

            # Category tabs
            cat_tabs = (
                f'<a href="/stats/production-costs?mode=vertical&category=all'
                f'&sort={sort}&order={order}" '
                f'style="padding:6px 12px;margin-right:8px;border-radius:4px;'
                f'text-decoration:none;'
                f'background:{"#38bdf8" if category=="all" else "#1e293b"};'
                f'color:{"#020617" if category=="all" else "#94a3b8"};">'
                f'All ({summary["total_items"]})</a>'
            )
            for cat in categories:
                cnt   = len(calc.get_by_category().get(cat, []))
                color = cat_colors.get(cat, "#64748b")
                sel   = category == cat
                cat_tabs += (
                    f'<a href="/stats/production-costs?mode=vertical'
                    f'&category={cat}&sort={sort}&order={order}" '
                    f'style="padding:6px 12px;margin-right:8px;margin-bottom:8px;'
                    f'border-radius:4px;text-decoration:none;display:inline-block;'
                    f'background:{"" + color if sel else "#1e293b"};'
                    f'color:{"#020617" if sel else color};">'
                    f'{cat.replace("_"," ").title()} ({cnt})</a>'
                )

            sort_ind  = "▲" if order == "asc" else "▼"
            next_ord  = "desc" if order == "asc" else "asc"
            base_url  = f"/stats/production-costs?mode=vertical&category={category}&search={search}"

            if items:
                rows = ""
                for item in items:
                    cc = cat_colors.get(item.get("category","unknown"), "#64748b")
                    biz_label = item.get("business", "-") or '<span style="color:#ef4444;">No recipe</span>'
                    rows += (
                        f'<tr style="border-bottom:1px solid #1e293b;cursor:pointer;"'
                        f' onclick="if(window.startLoader)window.startLoader();window.location=\'/stats/production-costs/{item["item_key"]}\'">'
                        f'<td style="padding:12px 8px;"><strong>{item["name"]}</strong><br>'
                        f'<span style="color:#64748b;font-size:0.8rem;">{item["item_key"]}</span></td>'
                        f'<td style="padding:12px 8px;">'
                        f'<span style="padding:2px 8px;border-radius:4px;font-size:0.75rem;'
                        f'background:{cc}20;color:{cc};">'
                        f'{item.get("category","unknown").replace("_"," ").upper()}</span></td>'
                        f'<td style="padding:12px 8px;text-align:right;font-family:monospace;'
                        f'color:{_cost_color(item["cost"])};">'
                        f'{fmt_usd(item["cost"], disp, precision=4)}</td>'
                        f'<td style="padding:12px 8px;color:#64748b;font-size:0.85rem;">'
                        f'{biz_label}</td>'
                        f'<td style="padding:12px 8px;text-align:center;">'
                        f'<a href="/stats/production-costs/{item["item_key"]}" class="btn-blue"'
                        f' style="padding:4px 12px;font-size:0.8rem;">View</a></td></tr>'
                    )
                items_html = (
                    f'<table style="width:100%;border-collapse:collapse;font-size:0.9rem;">'
                    f'<thead><tr style="border-bottom:2px solid #1e293b;text-align:left;">'
                    f'<th style="padding:12px 8px;">'
                    f'<a href="{base_url}&sort=name&order={"asc" if sort!="name" else next_ord}"'
                    f' style="color:#94a3b8;text-decoration:none;">'
                    f'Item {"↕" if sort!="name" else sort_ind}</a></th>'
                    f'<th style="padding:12px 8px;">Category</th>'
                    f'<th style="padding:12px 8px;text-align:right;">'
                    f'<a href="{base_url}&sort=cost&order={"asc" if sort!="cost" else next_ord}"'
                    f' style="color:#94a3b8;text-decoration:none;">'
                    f'Cost {"↕" if sort!="cost" else sort_ind}</a></th>'
                    f'<th style="padding:12px 8px;">Producer</th>'
                    f'<th style="padding:12px 8px;text-align:center;">Details</th>'
                    f'</tr></thead><tbody>{rows}</tbody></table>'
                )
            else:
                items_html = '<p style="color:#64748b;text-align:center;padding:40px;">No items found.</p>'

            table_title = (
                f'Search results for "{search}"' if search
                else f'{category.replace("_"," ").title()} Items' if category != "all"
                else "All Items"
            )

            body = f'''
            <a href="/stats" style="color:#38bdf8;">← Stats Dashboard</a>
            <h1 style="margin-bottom:4px;">📊 Production Cost Explorer</h1>
            {mode_switcher}

            <!-- Summary cards -->
            <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:15px;margin-bottom:20px;">
                <div class="card" style="text-align:center;padding:15px;">
                    <div style="font-size:0.8rem;color:#64748b;">TOTAL ITEMS</div>
                    <div style="font-size:1.8rem;font-weight:bold;color:#38bdf8;">{summary["total_items"]}</div>
                </div>
                <div class="card" style="text-align:center;padding:15px;">
                    <div style="font-size:0.8rem;color:#64748b;">CHEAPEST</div>
                    <div style="font-size:1.8rem;font-weight:bold;color:#22c55e;">{fmt_usd(summary["min_cost"],disp,precision=4)}</div>
                </div>
                <div class="card" style="text-align:center;padding:15px;">
                    <div style="font-size:0.8rem;color:#64748b;">MEDIAN</div>
                    <div style="font-size:1.8rem;font-weight:bold;color:#f59e0b;">{fmt_usd(summary["median_cost"],disp)}</div>
                </div>
                <div class="card" style="text-align:center;padding:15px;">
                    <div style="font-size:0.8rem;color:#64748b;">MOST EXPENSIVE</div>
                    <div style="font-size:1.8rem;font-weight:bold;color:#ef4444;">{fmt_usd(summary["max_cost"],disp,precision=0)}</div>
                </div>
                <div class="card" style="text-align:center;padding:15px;">
                    <div style="font-size:0.8rem;color:#64748b;">MISSING RECIPES</div>
                    <div style="font-size:1.8rem;font-weight:bold;color:#64748b;">{len(summary["missing_items"])}</div>
                </div>
            </div>

            <!-- Search -->
            <div class="card">
                <form action="/stats/production-costs" method="get" style="display:flex;gap:10px;">
                    <input type="hidden" name="mode" value="vertical">
                    <input type="hidden" name="category" value="{category}">
                    <input type="hidden" name="sort" value="{sort}">
                    <input type="hidden" name="order" value="{order}">
                    <input type="text" name="search" value="{search}"
                           placeholder="🔍 Search items..." style="flex:1;padding:12px;font-size:1rem;">
                    <button type="submit" class="btn-blue" style="padding:12px 24px;">Search</button>
                    {f'<a href="/stats/production-costs?mode=vertical&category={category}&sort={sort}&order={order}" class="btn-orange" style="padding:12px 24px;">Clear</a>' if search else ""}
                </form>
            </div>

            <!-- Category filters -->
            <div class="card" style="margin-top:15px;">
                <div style="display:flex;flex-wrap:wrap;gap:8px;">{cat_tabs}</div>
            </div>

            <!-- Items table -->
            <div class="card" style="margin-top:15px;overflow-x:auto;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:15px;">
                    <h3 style="margin:0;">{table_title}
                        <span style="color:#64748b;font-weight:normal;">({len(items)} items)</span>
                    </h3>
                </div>
                {items_html}
            </div>'''

        # ════════════════════════════════════════════════════════════════════
        # MODE B — WMA Cost Basis (player-personalised)
        # ════════════════════════════════════════════════════════════════════
        else:
            from wma import get_player_cost_basis_items, get_all_wma

            all_raw   = get_player_cost_basis_items(player.id)
            wma_data  = get_all_wma(player.id)
            raw_items = list(all_raw)  # copy; filters below will reassign this

            # Apply filters
            if search:
                q = search.lower()
                raw_items = [i for i in raw_items
                             if q in i["item_key"].lower() or q in i["name"].lower()]
            if category != "all":
                raw_items = [i for i in raw_items if i["category"] == category]

            # Sort
            rev = order == "desc"
            if sort == "name":
                raw_items.sort(key=lambda x: x["name"].lower(), reverse=rev)
            elif sort == "category":
                raw_items.sort(key=lambda x: (x["category"], x["unit_cost"]), reverse=rev)
            else:  # cost
                raw_items.sort(key=lambda x: x["unit_cost"], reverse=rev)

            # "complete" = every input has SOME price (WMA or theoretical fallback),
            # OR the player already has a live WMA for the output (they produce it).
            def _is_complete(i):
                if i.get("has_all_priced", i["has_all_wma"]):
                    return True
                rec = wma_data.get(i["item_key"], {})
                return rec.get("wma_cost", 0.0) > 0 and len(i["missing_wma"]) == 0
            complete   = [i for i in raw_items if _is_complete(i)]
            incomplete = [i for i in raw_items if not _is_complete(i)]

            # Summary stats from complete items only
            costs_ok = [i["unit_cost"] for i in complete if i["unit_cost"] > 0]
            if costs_ok:
                costs_ok_s = sorted(costs_ok)
                cb_min    = costs_ok_s[0]
                cb_median = costs_ok_s[len(costs_ok_s) // 2]
                cb_max    = costs_ok_s[-1]
            else:
                cb_min = cb_median = cb_max = 0.0

            n_tracked = len(wma_data)

            def _cb_row(item):
                cb   = item["detail"]
                cc   = cat_colors.get(item.get("category","unknown"), "#64748b")
                cost = item["unit_cost"]
                # WMA coverage badge
                theo_n = item.get("theoretical_fallback_count", 0)
                miss_n = len(item["missing_wma"])
                # Check whether the player has a live WMA record for this OUTPUT item.
                # If they do, their cost is real production data regardless of how
                # individual inputs were priced — "theoretical" should not bleed upward.
                own_rec = wma_data.get(item["item_key"], {})
                has_own_wma = own_rec.get("wma_cost", 0.0) > 0
                if item["has_all_wma"]:
                    cov_badge = '<span style="color:#22c55e;font-size:0.7rem;">● live WMA</span>'
                elif has_own_wma and miss_n == 0:
                    # Player produces this — WMA is live, some inputs just used estimates
                    est_note = (
                        f' <span style="color:#607098;font-size:0.65rem;">'
                        f'{theo_n} input est.</span>'
                        if theo_n > 0 else ""
                    )
                    cov_badge = f'<span style="color:#22c55e;font-size:0.7rem;">● live WMA</span>{est_note}'
                elif miss_n == 0 and theo_n > 0:
                    cov_badge = f'<span style="color:#38bdf8;font-size:0.7rem;">~ {theo_n} theoretical</span>'
                elif miss_n > 0 and any(i["has_wma"] for i in cb["inputs"]):
                    cov_badge = f'<span style="color:#f59e0b;font-size:0.7rem;">⚠ {miss_n} no price</span>'
                else:
                    cov_badge = '<span style="color:#64748b;font-size:0.7rem;">○ no data</span>'

                # Modifier pills
                pills = ""
                if cb["exec_output_bonus"] > 0:
                    pills += f'<span style="padding:1px 5px;border-radius:3px;background:#16a34a20;color:#22c55e;font-size:0.65rem;">+{cb["exec_output_bonus"]*100:.0f}% output</span> '
                if cb["exec_wage_reduction"] > 0:
                    pills += f'<span style="padding:1px 5px;border-radius:3px;background:#1e40af20;color:#60a5fa;font-size:0.65rem;">-{cb["exec_wage_reduction"]*100:.0f}% wages</span> '
                if cb["exec_input_cost_reduction"] > 0:
                    pills += f'<span style="padding:1px 5px;border-radius:3px;background:#7e22ce20;color:#c084fc;font-size:0.65rem;">-{cb["exec_input_cost_reduction"]*100:.0f}% inputs</span> '

                all_priced = item.get("has_all_priced", item["has_all_wma"])
                # Also show cost when the player has their own live WMA for this item
                cost_str = (
                    fmt_usd(cost, disp, precision=4) if (all_priced or has_own_wma) and cost > 0
                    else f'<span style="color:#64748b;">—</span>'
                )

                return (
                    f'<tr style="border-bottom:1px solid #1e293b;">'
                    f'<td style="padding:10px 8px;"><strong>{item["name"]}</strong><br>'
                    f'<span style="color:#64748b;font-size:0.75rem;">{item["item_key"]}</span><br>'
                    f'{cov_badge}</td>'
                    f'<td style="padding:10px 8px;">'
                    f'<span style="padding:2px 8px;border-radius:4px;font-size:0.75rem;'
                    f'background:{cc}20;color:{cc};">'
                    f'{item.get("category","unknown").replace("_"," ").upper()}</span></td>'
                    f'<td style="padding:10px 8px;text-align:right;font-family:monospace;'
                    f'color:{_cost_color(cost)};">{cost_str}</td>'
                    f'<td style="padding:10px 8px;text-align:right;font-family:monospace;'
                    f'color:#64748b;font-size:0.8rem;">'
                    f'{fmt_usd(cb["capex_per_unit"],disp,precision=4) if cb["capex_per_unit"]>0 else "—"}</td>'
                    f'<td style="padding:10px 8px;color:#64748b;font-size:0.8rem;">'
                    f'<div>{item.get("business","-") or "-"}</div>'
                    f'<div style="margin-top:3px;">{pills}</div></td>'
                    f'</tr>'
                )

            # Category set for filter tabs
            all_cats = sorted({i["category"] for i in raw_items})
            cat_tabs = (
                f'<a href="/stats/production-costs?mode=cost_basis&category=all'
                f'&sort={sort}&order={order}" '
                f'style="padding:6px 12px;margin-right:8px;border-radius:4px;'
                f'text-decoration:none;'
                f'background:{"#38bdf8" if category=="all" else "#1e293b"};'
                f'color:{"#020617" if category=="all" else "#94a3b8"};">'
                f'All ({len(all_raw)})</a>'
            )
            for cat in sorted({i["category"] for i in all_raw}):
                cnt   = sum(1 for i in all_raw if i["category"] == cat)
                color = cat_colors.get(cat, "#64748b")
                sel   = category == cat
                cat_tabs += (
                    f'<a href="/stats/production-costs?mode=cost_basis'
                    f'&category={cat}&sort={sort}&order={order}" '
                    f'style="padding:6px 12px;margin-right:8px;margin-bottom:8px;'
                    f'border-radius:4px;text-decoration:none;display:inline-block;'
                    f'background:{"" + color if sel else "#1e293b"};'
                    f'color:{"#020617" if sel else color};">'
                    f'{cat.replace("_"," ").title()} ({cnt})</a>'
                )

            sort_ind = "▲" if order == "asc" else "▼"
            next_ord = "desc" if order == "asc" else "asc"
            base_url = f"/stats/production-costs?mode=cost_basis&category={category}&search={search}"

            def _th(label, s_key, align="left"):
                direction = "asc" if sort != s_key else next_ord
                return (
                    f'<th style="padding:12px 8px;text-align:{align};">'
                    f'<a href="{base_url}&sort={s_key}&order={direction}"'
                    f' style="color:#94a3b8;text-decoration:none;">'
                    f'{label} {"↕" if sort!=s_key else sort_ind}</a></th>'
                )

            complete_rows   = "".join(_cb_row(i) for i in complete) if complete else ""
            incomplete_rows = "".join(_cb_row(i) for i in incomplete) if incomplete else ""

            # Banner for missing WMA data
            missing_banner = ""
            if not wma_data:
                missing_banner = '''
                <div style="background:#78350f20;border:1px solid #92400e;border-radius:8px;
                            padding:16px;margin-bottom:16px;color:#fcd34d;">
                    <strong>No purchase history yet.</strong> Your cost basis builds automatically as you
                    buy items on the market, produce goods, or borrow from the WCE.
                    Prices shown below are $0 until your first transactions are recorded.
                </div>'''
            elif incomplete:
                missing_banner = (
                    f'<div style="background:#1e293b;border:1px solid #334155;border-radius:8px;'
                    f'padding:12px 16px;margin-bottom:16px;color:#94a3b8;font-size:0.8rem;">'
                    f'<strong style="color:#f59e0b;">⚠ {len(incomplete)} items</strong> have inputs '
                    f'with no price in your WMA ledger <em>and</em> no theoretical recipe — '
                    f'they appear at the bottom. All other items show their best available cost '
                    f'(live WMA where you have purchase history, theoretical otherwise).</div>'
                )

            items_section = (
                f'<table style="width:100%;border-collapse:collapse;font-size:0.9rem;">'
                f'<thead><tr style="border-bottom:2px solid #1e293b;text-align:left;">'
                f'{_th("Item","name")} {_th("Category","category")} '
                f'{_th("My Unit Cost","cost","right")} {_th("CapEx/unit","cost","right")} '
                f'<th style="padding:12px 8px;">Producer / Buffs</th>'
                f'</tr></thead><tbody>'
                f'{complete_rows}'
                f'{"<tr><td colspan=5 style=padding:8px;background:#0f172a;color:#475569;font-size:0.75rem;text-transform:uppercase;letter-spacing:.05em;>Incomplete WMA Data</td></tr>" if incomplete else ""}'
                f'{incomplete_rows}'
                f'</tbody></table>'
            ) if (complete or incomplete) else (
                '<p style="color:#64748b;text-align:center;padding:40px;">No items found.</p>'
            )

            body = f'''
            <a href="/stats" style="color:#38bdf8;">← Stats Dashboard</a>
            <h1 style="margin-bottom:4px;">📊 Production Cost Explorer</h1>
            {mode_switcher}

            <!-- Summary cards -->
            <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:15px;margin-bottom:20px;">
                <div class="card" style="text-align:center;padding:15px;">
                    <div style="font-size:0.8rem;color:#64748b;">ITEMS TRACKED</div>
                    <div style="font-size:1.8rem;font-weight:bold;color:#38bdf8;">{n_tracked}</div>
                    <div style="font-size:0.7rem;color:#475569;">in WMA ledger</div>
                </div>
                <div class="card" style="text-align:center;padding:15px;">
                    <div style="font-size:0.8rem;color:#64748b;">MY CHEAPEST</div>
                    <div style="font-size:1.8rem;font-weight:bold;color:#22c55e;">{fmt_usd(cb_min,disp,precision=4) if cb_min else "—"}</div>
                </div>
                <div class="card" style="text-align:center;padding:15px;">
                    <div style="font-size:0.8rem;color:#64748b;">MY MEDIAN</div>
                    <div style="font-size:1.8rem;font-weight:bold;color:#f59e0b;">{fmt_usd(cb_median,disp) if cb_median else "—"}</div>
                </div>
                <div class="card" style="text-align:center;padding:15px;">
                    <div style="font-size:0.8rem;color:#64748b;">MY MOST EXPENSIVE</div>
                    <div style="font-size:1.8rem;font-weight:bold;color:#ef4444;">{fmt_usd(cb_max,disp,precision=0) if cb_max else "—"}</div>
                </div>
            </div>

            {missing_banner}

            <!-- Search -->
            <div class="card">
                <form action="/stats/production-costs" method="get" style="display:flex;gap:10px;">
                    <input type="hidden" name="mode" value="cost_basis">
                    <input type="hidden" name="category" value="{category}">
                    <input type="hidden" name="sort" value="{sort}">
                    <input type="hidden" name="order" value="{order}">
                    <input type="text" name="search" value="{search}"
                           placeholder="🔍 Search items..." style="flex:1;padding:12px;font-size:1rem;">
                    <button type="submit" class="btn-blue" style="padding:12px 24px;">Search</button>
                    {f'<a href="/stats/production-costs?mode=cost_basis&category={category}&sort={sort}&order={order}" class="btn-orange" style="padding:12px 24px;">Clear</a>' if search else ""}
                </form>
            </div>

            <!-- Category filters -->
            <div class="card" style="margin-top:15px;">
                <div style="display:flex;flex-wrap:wrap;gap:8px;">{cat_tabs}</div>
            </div>

            <!-- Items table -->
            <div class="card" style="margin-top:15px;overflow-x:auto;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
                    <h3 style="margin:0;">
                        {"Search: &quot;" + search + "&quot;" if search else category.replace("_"," ").title() + " Items" if category!="all" else "All Items"}
                        <span style="color:#64748b;font-weight:normal;">({len(raw_items)} items — {len(complete)} complete)</span>
                    </h3>
                    <div style="font-size:0.72rem;color:#64748b;">
                        CapEx amortised over 10,000 units &nbsp;|&nbsp;
                        City subsidy (4.75%) applied &nbsp;|&nbsp;
                        Your exec & city buffs included
                    </div>
                </div>
                {items_section}
            </div>

            <!-- Legend -->
            <div class="card" style="margin-top:12px;font-size:0.75rem;color:#64748b;">
                <strong style="color:#94a3b8;">How this works:</strong>
                Each time you buy on the market, borrow from the WCE, or complete a production
                cycle, your WMA (Weighted Moving Average) ledger is updated.
                <em>My Unit Cost</em> = net cost per output unit using the best available input
                price: <span style="color:#22c55e;">● live WMA</span> when you have purchase
                history, or <span style="color:#38bdf8;">~ theoretical</span> (vertical
                integration floor) as a fallback — so you always see a useful estimate.
                Accounts for land efficiency, city buffs, executive bonuses, and the 4.75 %
                city production subsidy. <em>CapEx/unit</em> = startup cost ÷ 10,000 units.
            </div>'''

        # ── tutorial overlay (both modes) ────────────────────────────────────
        try:
            from tutorial_ux import get_tutorial_overlay_html
            tut = get_tutorial_overlay_html(player, "production_costs")
            if tut:
                body = tut + body
        except Exception:
            pass

        return shell("Production Costs", body, player.cash_balance, player.id)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return shell("Production Costs", f"Error: {e}", player.cash_balance, player.id)


@router.get("/stats/production-costs/{item_key}", response_class=HTMLResponse)
def production_cost_detail_page(
    item_key: str,
    session_token: Optional[str] = Cookie(None)
):
    """Detailed cost breakdown for a specific item."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)
    
    try:
        from production_costs import get_calculator
        
        calc = get_calculator()
        breakdown = calc.get_cost_breakdown(item_key)
        
        if not breakdown:
            return shell("Not Found", f"<p>Item '{item_key}' not found.</p>", player.cash_balance, player.id)
        
        # Build inputs breakdown
        inputs_html = ""
        if breakdown['has_recipe'] and breakdown['inputs']:
            inputs_html = '''
            <div class="card">
                <h3>Input Costs Breakdown</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr style="border-bottom: 2px solid #1e293b;">
                            <th style="padding: 10px 8px; text-align: left;">Input</th>
                            <th style="padding: 10px 8px; text-align: right;">Quantity</th>
                            <th style="padding: 10px 8px; text-align: right;">Unit Cost</th>
                            <th style="padding: 10px 8px; text-align: right;">Total Cost</th>
                            <th style="padding: 10px 8px; text-align: right;">% of Batch</th>
                        </tr>
                    </thead>
                    <tbody>'''
            
            for inp in breakdown['inputs']:
                pct = (inp['total_cost'] / breakdown['batch_cost'] * 100) if breakdown['batch_cost'] > 0 else 0
                bar_width = min(pct, 100)
                
                inputs_html += f'''
                <tr style="border-bottom: 1px solid #1e293b;">
                    <td style="padding: 10px 8px;">
                        <a href="/stats/production-costs/{inp['item_key']}" style="color: #38bdf8;">
                            {inp['name']}
                        </a>
                    </td>
                    <td style="padding: 10px 8px; text-align: right; font-family: monospace;">{inp['quantity']:,.2f}</td>
                    <td style="padding: 10px 8px; text-align: right; font-family: monospace;">{fmt_usd(inp['unit_cost'], disp, precision=4)}</td>
                    <td style="padding: 10px 8px; text-align: right; font-family: monospace; color: #f59e0b;">{fmt_usd(inp['total_cost'], disp, precision=4)}</td>
                    <td style="padding: 10px 8px; text-align: right;">
                        <div style="display: flex; align-items: center; justify-content: flex-end; gap: 8px;">
                            <div style="width: 80px; height: 8px; background: #1e293b; border-radius: 4px; overflow: hidden;">
                                <div style="width: {bar_width}%; height: 100%; background: #38bdf8;"></div>
                            </div>
                            <span style="font-size: 0.85rem; color: #94a3b8;">{pct:.1f}%</span>
                        </div>
                    </td>
                </tr>'''
            
            # Add wage row
            wage_pct = breakdown['wage_pct']
            inputs_html += f'''
                <tr style="border-bottom: 1px solid #1e293b; background: #0f172a;">
                    <td style="padding: 10px 8px;"><strong>Labor (Wages)</strong></td>
                    <td style="padding: 10px 8px; text-align: right;">-</td>
                    <td style="padding: 10px 8px; text-align: right;">-</td>
                    <td style="padding: 10px 8px; text-align: right; font-family: monospace; color: #22c55e;">{fmt_usd(breakdown['wage'], disp)}</td>
                    <td style="padding: 10px 8px; text-align: right;">
                        <div style="display: flex; align-items: center; justify-content: flex-end; gap: 8px;">
                            <div style="width: 80px; height: 8px; background: #1e293b; border-radius: 4px; overflow: hidden;">
                                <div style="width: {min(wage_pct, 100)}%; height: 100%; background: #22c55e;"></div>
                            </div>
                            <span style="font-size: 0.85rem; color: #94a3b8;">{wage_pct:.1f}%</span>
                        </div>
                    </td>
                </tr>
                <tr style="background: #1e293b;">
                    <td style="padding: 10px 8px;" colspan="3"><strong>BATCH TOTAL</strong></td>
                    <td style="padding: 10px 8px; text-align: right; font-family: monospace; font-size: 1.1rem; color: #38bdf8;">
                        {fmt_usd(breakdown['batch_cost'], disp, precision=4)}
                    </td>
                    <td style="padding: 10px 8px; text-align: right; color: #64748b;">
                        ÷ {breakdown['output_qty']} = {fmt_usd(breakdown['cost'], disp, precision=4)}/unit
                    </td>
                </tr>
            </tbody></table>
            </div>'''
        elif not breakdown['has_recipe']:
            inputs_html = '''
            <div class="card" style="border-left: 4px solid #ef4444;">
                <h3 style="color: #ef4444;">⚠️ No Production Recipe</h3>
                <p style="color: #94a3b8;">This item cannot be produced. It may be a raw material that needs to be obtained through other means (mining, harvesting, etc.) or the recipe is missing from the configuration.</p>
            </div>'''
        
        # Find items that use this as an input
        used_by = []
        all_items = calc.get_all_items_sorted()
        for item in all_items:
            item_breakdown = calc.get_cost_breakdown(item['item_key'])
            if item_breakdown['has_recipe']:
                for inp in item_breakdown.get('inputs', []):
                    if inp['item_key'] == item_key:
                        used_by.append({
                            'item_key': item['item_key'],
                            'name': item['name'],
                            'cost': item['cost'],
                            'quantity_needed': inp['quantity']
                        })
                        break
        
        used_by_html = ""
        if used_by:
            used_by.sort(key=lambda x: x['cost'], reverse=True)
            used_by_html = '''
            <div class="card" style="margin-top: 15px;">
                <h3>Used In Production Of</h3>
                <div style="display: flex; flex-wrap: wrap; gap: 10px;">'''
            
            for item in used_by[:20]:
                used_by_html += f'''
                <a href="/stats/production-costs/{item['item_key']}" 
                   style="padding: 8px 12px; background: #1e293b; border-radius: 4px; text-decoration: none; color: #94a3b8;">
                    <strong style="color: #38bdf8;">{item['name']}</strong><br>
                    <span style="font-size: 0.8rem;">needs {item['quantity_needed']:,.1f}</span>
                </a>'''
            
            if len(used_by) > 20:
                used_by_html += f'<span style="padding: 8px 12px; color: #64748b;">+{len(used_by)-20} more...</span>'
            
            used_by_html += '</div></div>'

        # Pre-build production method HTML to avoid nested f-string syntax issues
        production_method_html = ""
        if breakdown['has_recipe']:
            production_method_html = f'''
        <div class="card" style="margin-top: 20px;">
            <h3>Production Method</h3>
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px;">
                <div>
                    <div style="font-size: 0.85rem; color: #64748b;">Producer</div>
                    <div style="font-size: 1.2rem;">{breakdown['business_name']}</div>
                </div>
                <div>
                    <div style="font-size: 0.85rem; color: #64748b;">Output per Batch</div>
                    <div style="font-size: 1.2rem;">{breakdown['output_qty']:,} units</div>
                </div>
                <div>
                    <div style="font-size: 0.85rem; color: #64748b;">Batch Cost</div>
                    <div style="font-size: 1.2rem; color: #f59e0b;">{fmt_usd(breakdown['batch_cost'], disp, precision=4)}</div>
                </div>
                <div>
                    <div style="font-size: 0.85rem; color: #64748b;">Wages</div>
                    <div style="font-size: 1.2rem; color: #22c55e;">{fmt_usd(breakdown['wage'], disp)}</div>
                </div>
            </div>
        </div>'''

        body = f'''
        <a href="/stats/production-costs" style="color: #38bdf8;">← Production Costs</a>
        
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-top: 20px;">
            <div>
                <h1 style="margin: 0;">{breakdown['name']}</h1>
                <p style="color: #64748b; margin: 5px 0;">
                    {item_key} · {breakdown.get('category', 'unknown').replace('_', ' ').title()}
                </p>
            </div>
            <div style="text-align: right;">
                <div style="font-size: 3rem; font-weight: bold; color: #38bdf8;">
                    {fmt_usd(breakdown['cost'], disp, precision=4)}
                </div>
                <div style="color: #64748b;">per unit (vertical integration)</div>
            </div>
        </div>
        
        <!-- Production Info -->
        {production_method_html}
        
        {inputs_html}
        
        {used_by_html}
        '''
        
        return shell(f"Cost: {breakdown['name']}", body, player.cash_balance, player.id)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return shell("Production Costs", f"Error: {e}", player.cash_balance, player.id)


# ==========================
# JSON API ENDPOINT
# ==========================

@router.get("/api/production-costs")
async def api_production_costs(
    category: str = None,
    search: str = None,
    session_token: Optional[str] = Cookie(None)
):
    """JSON API for production costs."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return {"error": "Unauthorized"}
    
    try:
        from production_costs import get_calculator
        
        calc = get_calculator()
        
        if search:
            items = calc.search_items(search)
        elif category:
            by_cat = calc.get_by_category()
            items = by_cat.get(category, [])
        else:
            items = calc.get_all_items_sorted()
        
        return {
            "summary": calc.get_summary(),
            "items": items,
            "categories": calc.get_categories()
        }
    except Exception as e:
        return {"error": str(e)}


@router.get("/api/production-costs/{item_key}")
async def api_production_cost_detail(
    item_key: str,
    session_token: Optional[str] = Cookie(None)
):
    """JSON API for single item cost breakdown."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return {"error": "Unauthorized"}
    
    try:
        from production_costs import get_calculator
        
        calc = get_calculator()
        return calc.get_cost_breakdown(item_key)
    except Exception as e:
        return {"error": str(e)}

# ==========================
# API ENDPOINTS
# ==========================

@router.post("/api/business/create")
async def create_business_endpoint(land_plot_id: int = Form(...), business_type: str = Form(...), session_token: Optional[str] = Cookie(None)):
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return player
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)
    from business import create_business
    if create_business(player.id, land_plot_id, business_type): return RedirectResponse(url="/land?built=1", status_code=303)
    return RedirectResponse(url="/land?error=failed", status_code=303)

@router.post("/api/business/toggle")
async def toggle_business_endpoint(business_id: int = Form(...), sort: str = "name", biz_filter: str = "all", session_token: Optional[str] = Cookie(None)):
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return player
    from business import toggle_business
    toggle_business(player.id, business_id)
    return RedirectResponse(url=f"/businesses?sort={sort}&biz_filter={biz_filter}", status_code=303)

@router.post("/api/business/toggle-line")
async def toggle_line_endpoint(business_id: int = Form(...), line_index: int = Form(...), sort: str = "name", biz_filter: str = "all", session_token: Optional[str] = Cookie(None)):
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return player
    from business import toggle_production_line
    toggle_production_line(player.id, business_id, line_index)
    return RedirectResponse(url=f"/businesses?sort={sort}&biz_filter={biz_filter}", status_code=303)

@router.post("/api/business/toggle-retail")
async def toggle_retail_endpoint(business_id: int = Form(...), item_type: str = Form(...), sort: str = "name", biz_filter: str = "all", session_token: Optional[str] = Cookie(None)):
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return player
    from business import toggle_retail_item
    toggle_retail_item(player.id, business_id, item_type)
    return RedirectResponse(url=f"/businesses?sort={sort}&biz_filter={biz_filter}", status_code=303)

@router.post("/api/business/dismantle")
async def dismantle_business_endpoint(business_id: int = Form(...), sort: str = "name", biz_filter: str = "all", session_token: Optional[str] = Cookie(None)):
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return player
    from business import start_business_dismantling
    start_business_dismantling(player.id, business_id)
    return RedirectResponse(url=f"/businesses?sort={sort}&biz_filter={biz_filter}", status_code=303)

@router.post("/api/retail/set-price")
async def set_retail_price_endpoint(item_type: str = Form(...), price: float = Form(...), sort: str = "name", biz_filter: str = "all", session_token: Optional[str] = Cookie(None)):
    """Retail Pricing Patch Endpoint."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return player
    from reserve_banks import get_player_display_currency
    disp = get_player_display_currency(player.id)
    try:
        from business import set_retail_price
        price_usd = price * disp["usd_per_unit"]
        set_retail_price(player.id, item_type, price_usd)
        return RedirectResponse(url=f"/businesses?sort={sort}&biz_filter={biz_filter}", status_code=303)
    except Exception as e:
        print(f"[UX] Retail price error: {e}")
        return RedirectResponse(url=f"/businesses?sort={sort}&biz_filter={biz_filter}&error=price_update_failed", status_code=303)

# ==========================
# AJAX JSON endpoints for /businesses dashboard (no page reload)
# ==========================

@router.post("/api/biz/toggle")
async def biz_toggle_ajax(business_id: int = Form(...), session_token: Optional[str] = Cookie(None)):
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return JSONResponse({"ok": False, "error": "not_authed"})
    from business import toggle_business, Business
    from land import get_db as get_land_db
    ok = toggle_business(player.id, business_id)
    if not ok:
        return JSONResponse({"ok": False, "error": "toggle_failed"})
    db = get_land_db()
    biz = db.query(Business).filter(Business.id == business_id).first()
    is_active = biz.is_active if biz else False
    db.close()
    return JSONResponse({"ok": True, "is_active": is_active})

@router.post("/api/biz/toggle-line")
async def biz_toggle_line_ajax(business_id: int = Form(...), line_index: int = Form(...), session_token: Optional[str] = Cookie(None)):
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return JSONResponse({"ok": False, "error": "not_authed"})
    from business import toggle_production_line
    result = toggle_production_line(player.id, business_id, line_index)
    return JSONResponse(result)

@router.post("/api/biz/toggle-retail")
async def biz_toggle_retail_ajax(business_id: int = Form(...), item_type: str = Form(...), session_token: Optional[str] = Cookie(None)):
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return JSONResponse({"ok": False, "error": "not_authed"})
    from business import toggle_retail_item
    result = toggle_retail_item(player.id, business_id, item_type)
    return JSONResponse(result)

@router.post("/api/biz/dismantle")
async def biz_dismantle_ajax(business_id: int = Form(...), session_token: Optional[str] = Cookie(None)):
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return JSONResponse({"ok": False, "error": "not_authed"})
    from business import start_business_dismantling
    ok = start_business_dismantling(player.id, business_id)
    return JSONResponse({"ok": bool(ok)})

@router.post("/api/biz/set-price")
async def biz_set_price_ajax(item_type: str = Form(...), price: float = Form(...), session_token: Optional[str] = Cookie(None)):
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return JSONResponse({"ok": False, "error": "not_authed"})
    from reserve_banks import get_player_display_currency, fmt_usd
    from business import set_retail_price
    disp = get_player_display_currency(player.id)
    try:
        price_usd = price * disp["usd_per_unit"]
        set_retail_price(player.id, item_type, price_usd)
        return JSONResponse({"ok": True, "display_price": fmt_usd(price_usd, disp)})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)})

@router.get("/api/biz/progress")
async def biz_progress(session_token: Optional[str] = Cookie(None)):
    """Return live progress_ticks for all player businesses."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return JSONResponse([])
    from business import Business, BUSINESS_TYPES, get_district_business_types
    from land import get_db as get_land_db
    db = get_land_db()
    try:
        all_types = {**BUSINESS_TYPES, **get_district_business_types()}
        rows = db.query(Business).filter(Business.owner_id == player.id).all()
        return JSONResponse([
            {"id": b.id,
             "progress_ticks": b.progress_ticks,
             "cycles_to_complete": all_types.get(b.business_type, {}).get("cycles_to_complete", 1),
             "is_active": b.is_active}
            for b in rows
        ])
    finally:
        db.close()

@router.post("/api/inventory/list")
async def list_to_market(item_type: str = Form(...), quantity: float = Form(...), price: float = Form(...), session_token: Optional[str] = Cookie(None)):
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return player
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)
    import market
    price_usd = price * disp["usd_per_unit"]
    market.create_order(player.id, market.OrderType.SELL, market.OrderMode.LIMIT, item_type, quantity, price_usd)
    return RedirectResponse(url="/inventory", status_code=303)

@router.post("/api/market/order")
async def place_order(item_type: str = Form(...), order_type: str = Form(...), quantity: float = Form(...), price: float = Form(...), session_token: Optional[str] = Cookie(None)):
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return player
    # ETF/fund shares trade on the ETF Trading Floor, not the commodity market.
    if item_type.endswith("_shares"):
        return RedirectResponse(url="/brokerage/trading?mode=etf", status_code=303)
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)
    import market
    price_usd = price * disp["usd_per_unit"]
    market.create_order(
        player.id,
        market.OrderType.BUY if order_type == "buy" else market.OrderType.SELL,
        market.OrderMode.LIMIT,
        item_type,
        quantity,
        price_usd
    )
    return RedirectResponse(url=f"/market?item={item_type}", status_code=303)

@router.post("/api/market/cancel-order")
async def cancel_market_order(order_id: int = Form(...), item_type: str = Form(...), session_token: Optional[str] = Cookie(None)):
    """Cancel a player's own open commodity market order."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return player
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)
    import market
    market.cancel_order(order_id, player.id)
    return RedirectResponse(url=f"/market?item={item_type}", status_code=303)

@router.post("/api/land-market/buy-auction")
async def buy_auction_endpoint(auction_id: int = Form(...), session_token: Optional[str] = Cookie(None)):
    """Buy a plot from government auction."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return player
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)
    
    from land_market import buy_auction_land
    if buy_auction_land(player.id, auction_id):
        return RedirectResponse(url="/land-market?success=auction_bought", status_code=303)
    return RedirectResponse(url="/land-market?error=purchase_failed", status_code=303)

@router.post("/api/land-market/buy-listing")
async def buy_listing_endpoint(listing_id: int = Form(...), session_token: Optional[str] = Cookie(None)):
    """Buy a plot from player listing."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return player
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)
    
    from land_market import buy_listed_land
    if buy_listed_land(player.id, listing_id):
        return RedirectResponse(url="/land-market?tab=listings&success=listing_bought", status_code=303)
    return RedirectResponse(url="/land-market?tab=listings&error=purchase_failed", status_code=303)

@router.post("/api/land-market/cancel-listing")
async def cancel_listing_endpoint(listing_id: int = Form(...), session_token: Optional[str] = Cookie(None)):
    """Cancel your own land listing."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return player

    from land_market import cancel_listing
    if cancel_listing(player.id, listing_id):
        return RedirectResponse(url="/land?success=listing_cancelled", status_code=303)
    return RedirectResponse(url="/land?error=cancel_failed", status_code=303)

@router.post("/api/land-market/list-land")
async def list_land_endpoint(land_plot_id: int = Form(...), asking_price: float = Form(...), session_token: Optional[str] = Cookie(None)):
    """List your land for sale."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return player
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)
    
    from land_market import list_land_for_sale
    price_usd = asking_price * disp["usd_per_unit"]
    if list_land_for_sale(player.id, land_plot_id, price_usd):
        return RedirectResponse(url="/land?success=land_listed", status_code=303)
    return RedirectResponse(url="/land?error=listing_failed", status_code=303)

@router.post("/api/land-market/buy-order")
async def place_buy_order_endpoint(
    max_price: float = Form(...),
    terrain: str = Form(""),
    proximity: str = Form(""),
    session_token: Optional[str] = Cookie(None),
):
    """Place a standing limit buy order for land."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return player
    from reserve_banks import get_player_display_currency
    disp = get_player_display_currency(player.id)
    from land_market import place_land_buy_order
    price_usd = max_price * disp["usd_per_unit"]
    result = place_land_buy_order(
        player.id, price_usd,
        terrain=terrain if terrain else None,
        proximity=proximity if proximity else None,
    )
    if result is not False:  # None = auto-executed, LandBuyOrder = standing order
        return RedirectResponse(url="/land-market?tab=orders&success=buy_order_placed", status_code=303)
    return RedirectResponse(url="/land-market?tab=orders&error=buy_order_failed", status_code=303)

@router.post("/api/land-market/cancel-buy-order")
async def cancel_buy_order_endpoint(
    order_id: int = Form(...),
    session_token: Optional[str] = Cookie(None),
):
    """Cancel a standing land buy order."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return player
    from land_market import cancel_land_buy_order
    if cancel_land_buy_order(player.id, order_id):
        return RedirectResponse(url="/land-market?tab=orders&success=buy_order_cancelled", status_code=303)
    return RedirectResponse(url="/land-market?tab=orders&error=cancel_failed", status_code=303)

@router.post("/api/brokerage/etf-order")
async def brokerage_etf_order(
    item_type:  str   = Form(...),
    order_type: str   = Form(...),
    quantity:   float = Form(...),
    price:      float = Form(...),
    session_token: Optional[str] = Cookie(None),
):
    """Place a limit order for an ETF fund share via the ETF Trading Floor, then return to ETF trading view."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    from reserve_banks import get_player_display_currency
    disp = get_player_display_currency(player.id)
    import market
    price_usd = price * disp["usd_per_unit"]
    market.create_order(
        player.id,
        market.OrderType.BUY if order_type == "buy" else market.OrderType.SELL,
        market.OrderMode.LIMIT,
        item_type,
        quantity,
        price_usd,
    )
    return RedirectResponse(url="/brokerage/trading?mode=etf", status_code=303)


@router.post("/api/brokerage/create-ipo")
async def brokerage_create_ipo(
    business_id: int = Form(...),
    company_name: str = Form(...),
    ticker_symbol: str = Form(...),
    share_class: str = Form("A"),
    ipo_type: str = Form(...),
    total_shares: int = Form(...),
    offer_percentage: int = Form(...),
    dividend_type: str = Form(None),
    dividend_amount: float = Form(None),
    dividend_frequency: str = Form("weekly"),
    dividend_commodity: str = Form(None),
    session_token: Optional[str] = Cookie(None)
):
    """Create an IPO for a business."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)
    
    try:
        from banks.brokerage_firm import create_ipo, IPOType
        
        # Parse IPO type
        try:
            ipo_type_enum = IPOType(ipo_type)
        except ValueError:
            return RedirectResponse(url="/brokerage/ipo?error=invalid_ipo_type", status_code=303)
        
        # Calculate shares to offer
        shares_to_offer = int(total_shares * (offer_percentage / 100))
        
        # Build dividend config
        dividend_config = []
        if dividend_type and dividend_amount and dividend_amount > 0:
            div_entry = {
                "type": dividend_type,
                "frequency": dividend_frequency
            }
            
            if dividend_type == "cash":
                div_entry["amount"] = dividend_amount
                div_entry["basis"] = "profit_pct"
            elif dividend_type == "commodity":
                div_entry["item"] = dividend_commodity or "apple_seeds"
                div_entry["amount"] = int(dividend_amount)
                div_entry["per_shares"] = 100
            elif dividend_type == "scrip":
                div_entry["rate"] = dividend_amount
            
            dividend_config.append(div_entry)
        
        # Clean ticker
        ticker_clean = ticker_symbol.upper().strip()[:5]
        
        result, error_msg = create_ipo(
            founder_id=player.id,
            business_id=business_id,
            ipo_type=ipo_type_enum,
            shares_to_offer=shares_to_offer,
            total_shares=total_shares,
            share_class=share_class,
            company_name=company_name,
            ticker_symbol=ticker_clean,
            dividend_config=dividend_config
        )

        if result:
            return RedirectResponse(url=f"/brokerage/trading?ticker={ticker_clean}&success=ipo_created", status_code=303)
        from urllib.parse import quote
        return RedirectResponse(url=f"/brokerage/ipo?error={quote(error_msg or 'IPO creation failed.')}", status_code=303)
        
    except Exception as e:
        print(f"[UX] Create IPO error: {e}")
        import traceback
        traceback.print_exc()
        return RedirectResponse(url="/brokerage/ipo?error=exception", status_code=303)


@router.post("/api/brokerage/short-sell")
async def brokerage_short_sell(
    ticker: str = Form(...),
    quantity: int = Form(...),
    session_token: Optional[str] = Cookie(None)
):
    """Open a short position."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)
    
    try:
        from banks.brokerage_firm import short_sell_shares, CompanyShares, get_db as get_firm_db
        
        # Get company ID from ticker
        db = get_firm_db()
        try:
            company = db.query(CompanyShares).filter(
                CompanyShares.ticker_symbol == ticker.upper()
            ).first()
            
            if not company:
                return RedirectResponse(url=f"/brokerage/shorts?error=company_not_found", status_code=303)
            
            company_id = company.id
        finally:
            db.close()
        
        result = short_sell_shares(
            borrower_id=player.id,
            company_shares_id=company_id,
            quantity=quantity
        )
        
        if result:
            return RedirectResponse(url=f"/brokerage/shorts?ticker={ticker}&success=short_opened", status_code=303)
        return RedirectResponse(url=f"/brokerage/shorts?ticker={ticker}&error=short_failed", status_code=303)
        
    except Exception as e:
        print(f"[UX] Short sell error: {e}")
        import traceback
        traceback.print_exc()
        return RedirectResponse(url="/brokerage/shorts?error=exception", status_code=303)


@router.post("/api/brokerage/close-short")
async def brokerage_close_short(
    loan_id: int = Form(...),
    session_token: Optional[str] = Cookie(None)
):
    """Close a short position."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)
    
    try:
        from banks.brokerage_firm import close_short_position, ShareLoan, get_db as get_firm_db
        
        # Verify ownership
        db = get_firm_db()
        try:
            loan = db.query(ShareLoan).filter(
                ShareLoan.id == loan_id,
                ShareLoan.borrower_player_id == player.id
            ).first()
            
            if not loan:
                return RedirectResponse(url="/brokerage/shorts?error=loan_not_found", status_code=303)
        finally:
            db.close()
        
        success = close_short_position(loan_id)
        
        if success:
            return RedirectResponse(url="/brokerage/shorts?success=short_closed", status_code=303)
        return RedirectResponse(url="/brokerage/shorts?error=close_failed", status_code=303)
        
    except Exception as e:
        print(f"[UX] Close short error: {e}")
        import traceback
        traceback.print_exc()
        return RedirectResponse(url="/brokerage/shorts?error=exception", status_code=303)


@router.post("/api/brokerage/recall-shares")
async def brokerage_recall_shares(
    company_shares_id: int = Form(...),
    session_token: Optional[str] = Cookie(None)
):
    """Recall all active share loans where the current player is the lender."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    from urllib.parse import quote
    try:
        from banks.brokerage_firm import recall_shares
        count, err = recall_shares(player.id, company_shares_id)
        if err:
            return RedirectResponse(
                url=f"/brokerage/portfolio?error={quote(err)}", status_code=303
            )
        return RedirectResponse(
            url=f"/brokerage/portfolio?success={quote(f'Recalled {count} loan(s) successfully.')}",
            status_code=303
        )
    except Exception as e:
        from urllib.parse import quote
        return RedirectResponse(
            url=f"/brokerage/portfolio?error={quote(str(e))}", status_code=303
        )


@router.post("/api/brokerage/list-commodity")
async def brokerage_list_commodity(
    item_type: str = Form(...),
    quantity: float = Form(...),
    weekly_rate: float = Form(...),
    session_token: Optional[str] = Cookie(None)
):
    """List commodities for lending."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)
    
    try:
        # Fund/ETF shares belong on the ETF Trading Floor, not the commodity market.
        if item_type.endswith("_shares"):
            return RedirectResponse(url="/brokerage/commodities?error=list_failed", status_code=303)

        from banks.brokerage_firm import list_commodity_for_lending

        # Convert percentage to decimal
        rate_decimal = weekly_rate / 100.0

        result = list_commodity_for_lending(
            lender_id=player.id,
            item_type=item_type,
            quantity=quantity,
            weekly_rate=rate_decimal
        )
        
        if result:
            return RedirectResponse(url="/brokerage/commodities?success=listed", status_code=303)
        return RedirectResponse(url="/brokerage/commodities?error=list_failed", status_code=303)
        
    except Exception as e:
        print(f"[UX] List commodity error: {e}")
        import traceback
        traceback.print_exc()
        return RedirectResponse(url="/brokerage/commodities?error=exception", status_code=303)


@router.post("/api/brokerage/cancel-listing")
async def brokerage_cancel_listing(
    listing_id: int = Form(...),
    session_token: Optional[str] = Cookie(None)
):
    """Cancel a commodity listing."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)
    
    try:
        from banks.brokerage_firm import CommodityListing, get_db as get_firm_db
        
        db = get_firm_db()
        try:
            listing = db.query(CommodityListing).filter(
                CommodityListing.id == listing_id,
                CommodityListing.lender_player_id == player.id,
                CommodityListing.is_active == True
            ).first()
            
            if not listing:
                return RedirectResponse(url="/brokerage/commodities?error=listing_not_found", status_code=303)
            
            # Check if anything is lent out
            if listing.quantity_lent_out > 0:
                return RedirectResponse(url="/brokerage/commodities?error=items_lent_out", status_code=303)
            
            listing.is_active = False
            db.commit()
            
        finally:
            db.close()
        
        return RedirectResponse(url="/brokerage/commodities?success=listing_cancelled", status_code=303)
        
    except Exception as e:
        print(f"[UX] Cancel listing error: {e}")
        import traceback
        traceback.print_exc()
        return RedirectResponse(url="/brokerage/commodities?error=exception", status_code=303)


@router.post("/api/brokerage/borrow-commodity")
async def brokerage_borrow_commodity(
    listing_id: int = Form(...),
    quantity: float = Form(...),
    session_token: Optional[str] = Cookie(None)
):
    """Borrow commodities from a listing."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)
    
    try:
        from banks.brokerage_firm import borrow_commodity
        
        result = borrow_commodity(
            borrower_id=player.id,
            listing_id=listing_id,
            quantity=quantity
        )
        
        if result:
            return RedirectResponse(url="/brokerage/commodities?success=borrowed", status_code=303)
        return RedirectResponse(url="/brokerage/commodities?error=borrow_failed", status_code=303)
        
    except Exception as e:
        print(f"[UX] Borrow commodity error: {e}")
        import traceback
        traceback.print_exc()
        return RedirectResponse(url="/brokerage/commodities?error=exception", status_code=303)


@router.post("/api/brokerage/return-commodity")
async def brokerage_return_commodity(
    loan_id: int = Form(...),
    session_token: Optional[str] = Cookie(None)
):
    """Return borrowed commodities."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)
    
    try:
        from banks.brokerage_firm import return_commodity, CommodityLoan, get_db as get_firm_db
        
        # Verify ownership
        db = get_firm_db()
        try:
            loan = db.query(CommodityLoan).filter(
                CommodityLoan.id == loan_id,
                CommodityLoan.borrower_player_id == player.id
            ).first()
            
            if not loan:
                return RedirectResponse(url="/brokerage/commodities?error=loan_not_found", status_code=303)
        finally:
            db.close()
        
        success = return_commodity(loan_id)
        
        if success:
            return RedirectResponse(url="/brokerage/commodities?success=returned", status_code=303)
        return RedirectResponse(url="/brokerage/commodities?error=return_failed", status_code=303)
        
    except Exception as e:
        print(f"[UX] Return commodity error: {e}")
        import traceback
        traceback.print_exc()
        return RedirectResponse(url="/brokerage/commodities?error=exception", status_code=303)


@router.post("/api/brokerage/extend-loan")
async def brokerage_extend_loan(
    loan_id: int = Form(...),
    session_token: Optional[str] = Cookie(None)
):
    """Extend a commodity loan."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)
    
    try:
        from banks.brokerage_firm import extend_commodity_loan, CommodityLoan, get_db as get_firm_db
        
        # Verify ownership
        db = get_firm_db()
        try:
            loan = db.query(CommodityLoan).filter(
                CommodityLoan.id == loan_id,
                CommodityLoan.borrower_player_id == player.id
            ).first()
            
            if not loan:
                return RedirectResponse(url="/brokerage/commodities?error=loan_not_found", status_code=303)
        finally:
            db.close()
        
        success = extend_commodity_loan(loan_id)
        
        if success:
            return RedirectResponse(url="/brokerage/commodities?success=extended", status_code=303)
        return RedirectResponse(url="/brokerage/commodities?error=extend_failed", status_code=303)
        
    except Exception as e:
        print(f"[UX] Extend loan error: {e}")
        import traceback
        traceback.print_exc()
        return RedirectResponse(url="/brokerage/commodities?error=exception", status_code=303)


@router.post("/api/brokerage/enable-share-lending")
async def brokerage_enable_share_lending(
    position_id: int = Form(...),
    quantity: int = Form(...),
    session_token: Optional[str] = Cookie(None)
):
    """Enable shares for lending (for short sellers to borrow)."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)
    
    try:
        from banks.brokerage_firm import ShareholderPosition, get_db as get_firm_db
        
        db = get_firm_db()
        try:
            position = db.query(ShareholderPosition).filter(
                ShareholderPosition.id == position_id,
                ShareholderPosition.player_id == player.id
            ).first()
            
            if not position:
                return RedirectResponse(url="/brokerage/portfolio?error=position_not_found", status_code=303)
            
            available = position.shares_owned - position.shares_lent_out
            if quantity > available:
                return RedirectResponse(url="/brokerage/portfolio?error=insufficient_shares", status_code=303)
            
            position.shares_available_to_lend = quantity
            db.commit()
            
        finally:
            db.close()
        
        return RedirectResponse(url="/brokerage/portfolio?success=lending_enabled", status_code=303)
        
    except Exception as e:
        print(f"[UX] Enable lending error: {e}")
        import traceback
        traceback.print_exc()
        return RedirectResponse(url="/brokerage/portfolio?error=exception", status_code=303)


@router.post("/api/brokerage/disable-share-lending")
async def brokerage_disable_share_lending(
    position_id: int = Form(...),
    session_token: Optional[str] = Cookie(None)
):
    """
    Opt a position out of share lending entirely.
    This is intentionally very expensive: a $50,000 flat fee plus 1% of the
    current market value of the position, paid to the government.
    """
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)

    DISABLE_LEND_BASE_FEE = 50_000.0
    DISABLE_LEND_PCT      = 0.01

    try:
        from banks.brokerage_firm import ShareholderPosition, CompanyShares, get_db as get_firm_db
        from auth import Player, get_db as get_auth_db

        db = get_firm_db()
        try:
            position = db.query(ShareholderPosition).filter(
                ShareholderPosition.id == position_id,
                ShareholderPosition.player_id == player.id
            ).first()
            if not position:
                return RedirectResponse(url="/brokerage/portfolio?error=position_not_found", status_code=303)

            company = db.query(CompanyShares).filter(
                CompanyShares.id == position.company_shares_id
            ).first()
            market_value = (position.shares_owned * company.current_price) if company else 0.0
        finally:
            db.close()

        opt_out_fee = DISABLE_LEND_BASE_FEE + market_value * DISABLE_LEND_PCT

        auth_db = get_auth_db()
        try:
            player_record = auth_db.query(Player).filter(Player.id == player.id).first()
            from reserve_banks import can_afford_usd, spend_player_funds
            if not player_record or not can_afford_usd(player.id, opt_out_fee):
                return RedirectResponse(
                    url=f"/brokerage/portfolio?error=insufficient_funds_for_opt_out_fee_{opt_out_fee:.0f}",
                    status_code=303
                )
            ok, _err = spend_player_funds(player_record.id, opt_out_fee)
            if not ok:
                return RedirectResponse(url="/brokerage/portfolio?error=payment_failed", status_code=303)
            # Fee goes to government
            government = auth_db.query(Player).filter(Player.id == 0).first()
            if government:
                government.cash_balance += opt_out_fee
            auth_db.commit()
        finally:
            auth_db.close()

        # Zero out lending for this position
        db2 = get_firm_db()
        try:
            pos2 = db2.query(ShareholderPosition).filter(
                ShareholderPosition.id == position_id,
                ShareholderPosition.player_id == player.id
            ).first()
            if pos2:
                pos2.shares_available_to_lend = 0
            db2.commit()
        finally:
            db2.close()

        return RedirectResponse(url="/brokerage/portfolio?success=lending_disabled", status_code=303)

    except Exception as e:
        print(f"[UX] Disable lending error: {e}")
        import traceback
        traceback.print_exc()
        return RedirectResponse(url="/brokerage/portfolio?error=exception", status_code=303)


@router.post("/api/brokerage/deposit-margin")
async def brokerage_deposit_margin(
    amount: float = Form(...),
    session_token: Optional[str] = Cookie(None)
):
    """Deposit cash to resolve margin calls."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)
    
    try:
        from banks.brokerage_firm import MarginCall, ShareholderPosition, get_db as get_firm_db
        from auth import Player, get_db as get_auth_db
        
        # Check player has funds (supports foreign legal tender)
        auth_db = get_auth_db()
        try:
            player_record = auth_db.query(Player).filter(Player.id == player.id).first()
            from reserve_banks import can_afford_usd, spend_player_funds
            if not player_record or not can_afford_usd(player.id, amount):
                return RedirectResponse(url="/banks/brokerage-firm?error=insufficient_funds", status_code=303)
            ok, _err = spend_player_funds(player_record.id, amount)
            if not ok:
                return RedirectResponse(url="/banks/brokerage-firm?error=payment_failed", status_code=303)
            auth_db.commit()
        finally:
            auth_db.close()
        
        # Apply to margin debt
        db = get_firm_db()
        try:
            # Find positions with margin debt
            positions = db.query(ShareholderPosition).filter(
                ShareholderPosition.player_id == player.id,
                ShareholderPosition.margin_debt > 0
            ).order_by(ShareholderPosition.margin_debt.desc()).all()
            
            remaining = amount
            for pos in positions:
                if remaining <= 0:
                    break
                
                paydown = min(remaining, pos.margin_debt)
                pos.margin_debt -= paydown
                remaining -= paydown
                
                if pos.margin_debt <= 0:
                    pos.is_margin_position = False
                    pos.margin_multiplier_used = 1.0
            
            # Resolve margin calls if debt cleared
            margin_calls = db.query(MarginCall).filter(
                MarginCall.player_id == player.id,
                MarginCall.is_resolved == False
            ).all()
            
            for mc in margin_calls:
                # Recalculate if still needed
                total_debt = sum(p.margin_debt for p in positions)
                if total_debt <= 0:
                    mc.is_resolved = True
                    mc.resolved_at = datetime.utcnow()
                    mc.resolution_type = "deposited"
            
            db.commit()
        finally:
            db.close()
        
        return RedirectResponse(url="/banks/brokerage-firm?success=margin_deposited", status_code=303)
        
    except Exception as e:
        print(f"[UX] Deposit margin error: {e}")
        import traceback
        traceback.print_exc()
        return RedirectResponse(url="/banks/brokerage-firm?error=exception", status_code=303)

# ==========================
# BROKERAGE TRADING API
# ==========================

@router.post("/api/brokerage/buy")
async def brokerage_buy_shares(
    company_id: int = Form(...),
    quantity: int = Form(...),
    use_margin: bool = Form(False),
    limit_price: Optional[float] = Form(None), # Optional: Forms can send this if UI supports it
    session_token: Optional[str] = Cookie(None)
):
    """Place a buy order (Market or Limit)."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return player
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)
    
    try:
        from banks.brokerage_firm import CompanyShares, get_db as get_firm_db
        from banks.brokerage_order_book import player_place_buy_order
        
        # Get ticker for the redirect URL
        db = get_firm_db()
        try:
            company = db.query(CompanyShares).filter(CompanyShares.id == company_id).first()
            ticker = company.ticker_symbol if company else "UNKNOWN"
        finally:
            db.close()
        
        # Execute Order
        # Convert limit_price from the player's display currency back to USD before
        # storing — the order book always works in USD internally, and fmt_usd() on
        # the display side will convert back out again.  Without this step a player
        # whose display currency is JPY (usd_per_unit ≈ 0.0067) would store ¥150
        # as $150, causing the displayed price to be ~22× higher than intended.
        limit_price_usd = (limit_price * disp["usd_per_unit"]) if limit_price is not None else None
        result = player_place_buy_order(
            player_id=player.id,
            company_shares_id=company_id,
            quantity=quantity,
            limit_price=limit_price_usd,  # None = Market Order
            use_margin=use_margin
        )
        
        status = "success" if result else "error"
        msg = "buy_order_placed" if result else "buy_failed"
        
        return RedirectResponse(url=f"/brokerage/trading?ticker={ticker}&{status}={msg}", status_code=303)
        
    except Exception as e:
        print(f"[UX] Buy shares error: {e}")
        return RedirectResponse(url="/brokerage/trading?error=exception", status_code=303)


@router.post("/api/brokerage/sell")
async def brokerage_sell_shares(
    company_id: int = Form(...),
    quantity: int = Form(...),
    limit_price: Optional[float] = Form(None),
    session_token: Optional[str] = Cookie(None)
):
    """Place a sell order (Market or Limit)."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return player
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)
    
    try:
        from banks.brokerage_firm import CompanyShares, get_db as get_firm_db
        from banks.brokerage_order_book import player_place_sell_order
        
        db = get_firm_db()
        try:
            company = db.query(CompanyShares).filter(CompanyShares.id == company_id).first()
            ticker = company.ticker_symbol if company else "UNKNOWN"
        finally:
            db.close()
        
        # Same currency conversion as the buy endpoint — see comment there.
        limit_price_usd = (limit_price * disp["usd_per_unit"]) if limit_price is not None else None
        result = player_place_sell_order(
            player_id=player.id,
            company_shares_id=company_id,
            quantity=quantity,
            limit_price=limit_price_usd
        )
        
        status = "success" if result else "error"
        msg = "sell_order_placed" if result else "sell_failed"
        
        return RedirectResponse(url=f"/brokerage/trading?ticker={ticker}&{status}={msg}", status_code=303)
        
    except Exception as e:
        print(f"[UX] Sell shares error: {e}")
        return RedirectResponse(url="/brokerage/trading?error=exception", status_code=303)


@router.post("/api/brokerage/cancel-order")
async def brokerage_cancel_order(
    order_id: int = Form(...),
    session_token: Optional[str] = Cookie(None)
):
    """Cancel a pending order."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return player
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)
    
    try:
        from banks.brokerage_order_book import cancel_order
        
        success = cancel_order(player.id, order_id)
        
        # Determine where to redirect (trading page or portfolio)
        return RedirectResponse(url=f"/brokerage/portfolio?success={'cancelled' if success else 'cancel_failed'}", status_code=303)
        
    except Exception as e:
        print(f"[UX] Cancel order error: {e}")
        return RedirectResponse(url="/brokerage/portfolio?error=exception", status_code=303)


# ==========================
# DATA ENDPOINTS (JSON)
# ==========================
# These return JSON for potential JS/AJAX usage, but are attached to @router correctly

@router.get("/api/trading/orderbook/{company_shares_id}")
async def get_orderbook_data(
    company_shares_id: int,
    depth: int = 10,
    session_token: Optional[str] = Cookie(None)
):
    """Get raw orderbook data (JSON)."""
    # Auth optional for viewing, but good practice
    from banks.brokerage_order_book import get_order_book_depth
    return get_order_book_depth(company_shares_id, depth)


@router.get("/api/trading/trades/{company_shares_id}")
async def get_recent_trades_data(
    company_shares_id: int,
    limit: int = 20
):
    """Get recent fills (JSON)."""
    from banks.brokerage_order_book import get_recent_fills
    return {"trades": get_recent_fills(company_shares_id, limit)}


@router.get("/api/trading/orders/my")
async def get_my_open_orders(
    session_token: Optional[str] = Cookie(None)
):
    """Get current player's open orders (JSON)."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return {"error": "Unauthorized"}
    
    try:
        from banks.brokerage_order_book import OrderBook, OrderStatus, get_db as get_book_db
        db = get_book_db()
        try:
            orders = db.query(OrderBook).filter(
                OrderBook.player_id == player.id,
                OrderBook.status.in_([
                    OrderStatus.PENDING.value, 
                    OrderStatus.PARTIAL.value
                ])
            ).order_by(OrderBook.created_at.desc()).all()
            
            return {
                "orders": [{
                    "id": o.id,
                    "company_shares_id": o.company_shares_id,
                    "side": o.order_side,
                    "type": o.order_type,
                    "quantity": o.quantity,
                    "filled": o.filled_quantity,
                    "limit_price": o.limit_price,
                    "status": o.status,
                    "created_at": o.created_at.isoformat()
                } for o in orders]
            }
        finally:
            db.close()
    except Exception as e:
        return {"error": str(e)}


# ==========================
# MODULE LIFECYCLE
# ==========================

def initialize():
    """Initialize UX module."""
    print("[UX] Module initialized")

def tick(current_tick: int, now):
    """UX tick handler (no-op)."""
    pass

# ==========================
# PUBLIC API
# ==========================

__all__ = [
    'router',
    'initialize',
    'tick',
    'shell',
    'get_player_lien_info'
]
