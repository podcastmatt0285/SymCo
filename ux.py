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
from fastapi import APIRouter, Cookie, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, StreamingResponse
from datetime import timedelta
from datetime import datetime
import json as _json

router = APIRouter()

# ==========================
# PRIVACY POLICY
# ==========================
@router.get("/privacy-policy", response_class=HTMLResponse)
def privacy_policy():
    html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Privacy Policy — Wadsworth</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Caveat:wght@400;600;700&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    background: #1a0e06;
    min-height: 100vh;
    display: flex;
    align-items: flex-start;
    justify-content: center;
    padding: 40px 16px 60px;
    font-family: 'Caveat', cursive;
  }

  .ledger {
    position: relative;
    width: 100%;
    max-width: 720px;
    background: #f5ead0;
    background-image:
      repeating-linear-gradient(transparent, transparent 31px, #c9a97a55 31px, #c9a97a55 32px),
      radial-gradient(ellipse at 20% 10%, #e8d5b0 0%, #f5ead0 60%),
      radial-gradient(ellipse at 80% 90%, #dfc99a 0%, #f5ead0 60%);
    border-radius: 4px 12px 12px 4px;
    box-shadow:
      -8px 0 0 #6b3a1f,
      -14px 0 0 #3d1f0a,
      4px 4px 30px rgba(0,0,0,0.7),
      inset 0 0 60px rgba(139,90,43,0.15);
    padding: 52px 52px 52px 64px;
    color: #1a0e06;
    line-height: 2;
  }

  /* Leather spine */
  .ledger::before {
    content: '';
    position: absolute;
    top: 0; left: -8px;
    width: 8px; height: 100%;
    background: linear-gradient(to right, #3d1f0a, #6b3a1f);
    border-radius: 4px 0 0 4px;
  }

  /* Page edge shadow */
  .ledger::after {
    content: '';
    position: absolute;
    top: 4px; right: -4px;
    width: 100%; height: 100%;
    background: #c9a97a;
    border-radius: 4px 12px 12px 4px;
    z-index: -1;
  }

  .ledger-title {
    font-size: 2.4rem;
    font-weight: 700;
    color: #3d1f0a;
    border-bottom: 2px solid #c9a97a;
    padding-bottom: 8px;
    margin-bottom: 4px;
    letter-spacing: 0.02em;
  }

  .ledger-subtitle {
    font-size: 1.1rem;
    color: #7a5230;
    margin-bottom: 32px;
    font-style: italic;
  }

  h2 {
    font-size: 1.5rem;
    font-weight: 700;
    color: #3d1f0a;
    margin: 28px 0 4px;
    border-left: 3px solid #c9a97a;
    padding-left: 10px;
  }

  p { font-size: 1.15rem; color: #2a1505; margin-bottom: 8px; }

  ul {
    list-style: none;
    padding-left: 8px;
    margin-bottom: 8px;
  }

  ul li {
    font-size: 1.15rem;
    color: #2a1505;
    padding: 2px 0 2px 20px;
    position: relative;
  }

  ul li::before {
    content: '✦';
    position: absolute;
    left: 0;
    color: #c9a97a;
    font-size: 0.75rem;
    top: 6px;
  }

  strong { color: #3d1f0a; font-weight: 700; }

  .back-link {
    display: inline-block;
    margin-bottom: 20px;
    font-size: 1.1rem;
    color: #6b3a1f;
    text-decoration: none;
  }
  .back-link:hover { text-decoration: underline; }

  @media (max-width: 600px) {
    .ledger { padding: 36px 24px 36px 36px; }
    .ledger-title { font-size: 1.9rem; }
  }
</style>
</head>
<body>
<div class="ledger">
  <a href="/" class="back-link">← Back to Wadsworth</a>

  <div class="ledger-title">Privacy Policy</div>
  <div class="ledger-subtitle">Wadsworth Economic Tycoon Simulator &mdash; Last updated March 2026</div>

  <p>Wadsworth Economic Tycoon Simulator ("the Game", "we", "us") is operated by IllinoisJo. This policy
  explains what information we collect, how we use it, and your rights.</p>

  <h2>I. Information We Collect</h2>
  <ul>
    <li><strong>Account information</strong> &mdash; username, email address, and hashed password when you register.</li>
    <li><strong>Game data</strong> &mdash; in-game currency balances, inventory, land holdings, business activity,
        market orders, and all other gameplay actions you take.</li>
    <li><strong>Chat messages</strong> &mdash; messages sent in the Global Chat and Trade Chat rooms are stored on
        our servers and visible to other players.</li>
    <li><strong>Financial transaction records</strong> &mdash; all in-game purchases, sales, market trades, and
        transfers between players.</li>
    <li><strong>Device identifier</strong> &mdash; a one-way hash of your Android device ID, used solely to link
        home-screen widgets to your account. This hash cannot be reversed to identify your device.</li>
    <li><strong>Session data</strong> &mdash; login session tokens stored as secure HTTP-only cookies.</li>
    <li><strong>Server logs</strong> &mdash; IP address and request timestamps retained for up to 30 days for
        security and abuse prevention.</li>
  </ul>

  <h2>II. How We Use Your Information</h2>
  <ul>
    <li>To operate and maintain your game account.</li>
    <li>To display your game data to you and, where applicable, to other players (e.g. public market orders,
        chat messages, leaderboard positions).</li>
    <li>To deliver home-screen widget updates to your Android device.</li>
    <li>To detect and prevent fraud, cheating, or abuse.</li>
    <li>To send transactional notifications (e.g. market fills, alerts) if you have enabled push notifications.</li>
  </ul>

  <h2>III. Information Shared With Third Parties</h2>
  <p>We do <strong>not</strong> sell, rent, or trade your personal information. We do not use third-party
  advertising networks. Your data is not shared with any third party except:</p>
  <ul>
    <li>Hosting and infrastructure providers who process data on our behalf under confidentiality obligations.</li>
    <li>Law enforcement when required by applicable law.</li>
  </ul>

  <h2>IV. In-App Purchases</h2>
  <p>The Game uses Google Play Billing for any in-app purchases. Payment processing is handled entirely by
  Google. We do not receive or store your payment card details.</p>

  <h2>V. Children's Privacy</h2>
  <p>The Game is not directed at children under 13. We do not knowingly collect personal information from
  children under 13. If you believe a child under 13 has provided us with personal information, please
  contact us through the in-game support system and we will delete it promptly.</p>

  <h2>VI. Data Retention</h2>
  <p>Your account data is retained for as long as your account is active. Chat messages are retained
  indefinitely for gameplay purposes. Server logs are deleted after 30 days. You may request deletion of
  your account via the Estate &rarr; Leave Game page inside the game.</p>

  <h2>VII. Your Rights</h2>
  <p>You may request access to, correction of, or deletion of your personal data at any time by using the
  in-game account tools. We will respond within 30 days.</p>

  <h2>VIII. Security</h2>
  <p>Passwords are stored as salted hashes. Session tokens are transmitted over HTTPS only. We take
  reasonable technical measures to protect your data, but no system is perfectly secure.</p>

  <h2>IX. Changes to This Policy</h2>
  <p>We may update this policy from time to time. We will post the updated date at the top of this page.
  Continued use of the Game after changes constitutes acceptance.</p>
</div>
</body>
</html>"""
    return HTMLResponse(html)


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


# ==========================
# SHARED NAV-LOADER
# ==========================

def _nav_loader_html() -> str:
    """Mobile-friendly loading overlay — included in every page shell."""
    return """
        <!-- ═══════════════════════════════════════════════════
             NAVIGATION LOADER — shown on slow server pages
             Triggers on link click, disappears when page arrives.
        ═══════════════════════════════════════════════════ -->
        <div id="nav-loader" style="display:none;position:fixed;inset:0;z-index:9999;background:#0D0806;color:#F5F5DC;font-family:Georgia,serif;align-items:center;justify-content:center;padding:12px;">
          <div id="nl-card" style="position:relative;width:100%;max-width:420px;padding:clamp(16px,5vw,40px);background:#1A0F0A;border:4px solid #2D1810;box-shadow:0 25px 50px rgba(0,0,0,.8);display:flex;flex-direction:column;align-items:center;box-sizing:border-box;max-height:92vh;overflow-y:auto;">
            <!-- brass corners -->
            <div style="position:absolute;top:8px;left:8px;width:16px;height:16px;border-top:1px solid rgba(176,141,87,.4);border-left:1px solid rgba(176,141,87,.4);"></div>
            <div style="position:absolute;top:8px;right:8px;width:16px;height:16px;border-top:1px solid rgba(176,141,87,.4);border-right:1px solid rgba(176,141,87,.4);"></div>
            <div style="position:absolute;bottom:8px;left:8px;width:16px;height:16px;border-bottom:1px solid rgba(176,141,87,.4);border-left:1px solid rgba(176,141,87,.4);"></div>
            <div style="position:absolute;bottom:8px;right:8px;width:16px;height:16px;border-bottom:1px solid rgba(176,141,87,.4);border-right:1px solid rgba(176,141,87,.4);"></div>
            <!-- apple SVG -->
            <div style="width:min(110px,28vw);height:min(110px,28vw);display:flex;align-items:center;justify-content:center;flex-shrink:0;">
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
            <div style="margin-top:20px;width:100%;text-align:center;">
              <p style="font-size:9px;letter-spacing:.5em;text-transform:uppercase;color:#B08D57;font-weight:900;opacity:.4;margin:0 0 10px;">Wadsworth Executive Terminal</p>
              <div id="nl-msgs" style="min-height:60px;display:flex;flex-direction:column-reverse;align-items:center;gap:4px;overflow:hidden;"></div>
            </div>
            <!-- progress bar -->
            <div style="margin-top:16px;width:100%;height:3px;background:rgba(0,0,0,.6);border:1px solid rgba(176,141,87,.1);border-radius:9999px;overflow:hidden;">
              <div id="nl-bar" style="height:100%;width:0%;background:linear-gradient(to right,#8B4513,#B08D57,#F5F5DC);box-shadow:0 0 10px rgba(176,141,87,.5);transition:width .15s linear;"></div>
            </div>
            <!-- footer row -->
            <div style="margin-top:10px;width:100%;display:flex;justify-content:space-between;align-items:center;padding:0 4px;">
              <div style="display:flex;gap:14px;opacity:.2;font-size:13px;">&#9646; &#9632; &#9650;</div>
              <span id="nl-pct" style="font-size:9px;font-family:monospace;opacity:.4;color:#B08D57;">0% SECURED</span>
            </div>
            <div style="margin-top:12px;font-size:9px;letter-spacing:.6em;text-transform:uppercase;opacity:.2;color:#B08D57;" class="nl-pulse">Handshake in Progress</div>
          </div>
        </div>
        <style>
          @keyframes nl-pulse-anim { 0%,100%{opacity:.3} 50%{opacity:.7} }
          .nl-pulse { animation: nl-pulse-anim 2s ease-in-out infinite; }
        </style>
        <script>
        (function() {
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

          function renderMsgs() {
            msgs.innerHTML = msgList.slice(0,4).map(function(m,i) {
              var opacity = i === 0 ? '1' : '0.3';
              var scale   = i === 0 ? '1' : '0.95';
              var prefix  = i === 0 ? '&gt; ' : '';
              return '<p style="font-size:11px;font-style:italic;letter-spacing:-.01em;color:#B08D57;margin:0;transition:all .3s;opacity:'+opacity+';transform:scale('+scale+')">'
                     + prefix + m + '</p>';
            }).join('');
          }

          function startLoader() {
            if (timer) clearInterval(timer);
            prog = 0; msgList = ["Initializing Secure Terminal..."];
            overlay.style.display = 'flex';
            renderMsgs();
            timer = setInterval(function() {
              prog += 5;
              if (prog >= 100) prog = 0;
              if (Math.floor(prog/15) > Math.floor((prog-5)/15)) {
                var next = STEPS[Math.floor(Math.random()*STEPS.length)];
                msgList = [next].concat(msgList).slice(0,4);
                renderMsgs();
              }
              bar.style.width = prog + '%';
              pct.textContent = prog + '% SECURED';
            }, 150);
          }

          function hideLoader() {
            overlay.style.display = 'none';
            clearInterval(timer);
            timer = null;
          }

          // Show loader on every page load; hide once content is ready
          startLoader();
          document.addEventListener('DOMContentLoaded', hideLoader);

          // Show loader on any same-origin link click
          // Skip: new-tab, hash-only, external, download, mailto/tel/javascript
          document.addEventListener('click', function(e) {
            var a = e.target.closest('a');
            if (!a) return;
            if (a.target === '_blank') return;
            if (a.hasAttribute('download')) return;
            var href = a.getAttribute('href');
            if (!href) return;
            if (href.charAt(0) === '#') return;
            if (/^(javascript|mailto|tel):/.test(href)) return;
            try {
              var url = new URL(a.href, location.origin);
              if (url.origin !== location.origin) return;
              // Pure same-page hash scroll — no navigation
              if (url.pathname === location.pathname && url.hash && !url.search) return;
              startLoader();
            } catch(ex) {}
          });

          // Show loader on any same-origin form submit
          // Skip AJAX forms — their onsubmit returns false (preventDefault), no navigation occurs
          document.addEventListener('submit', function(e) {
            if (e.defaultPrevented) return;
            var form = e.target;
            if (!form) return;
            try {
              var action = form.action || location.href;
              var url = new URL(action, location.origin);
              if (url.origin !== location.origin) return;
              startLoader();
            } catch(ex) {}
          });

          window.startLoader = startLoader;
          window.hideLoader  = hideLoader;

          window.addEventListener('pageshow', function(e) {
            if (e.persisted) hideLoader();
          });
        })();
        </script>
        <script>
        // ── In-app notification sound (fires on all pages via service worker message) ──
        if ('serviceWorker' in navigator) {
          navigator.serviceWorker.addEventListener('message', function(event) {
            if (event.data && event.data.type === 'PLAY_NOTIFICATION_SOUND') {
              // Android standalone/TWA already plays the OS channel sound — skip to avoid double play
              if (/android/i.test(navigator.userAgent) &&
                  (window.matchMedia('(display-mode: standalone)').matches ||
                   window.matchMedia('(display-mode: fullscreen)').matches)) return;
              try {
                var snd = new Audio('/static/sounds/notification.mp3');
                snd.volume = 0.6;
                snd.play().catch(function(){});
              } catch(e) {}
            }
          });
        }
        </script>"""


# ==========================
# HTML SHELL
# ==========================

def shell(title: str, body: str, balance: float = 0.0, player_id: int = None) -> str:
    lien_info = get_player_lien_info(player_id) if player_id else {"has_lien": False, "total_owed": 0.0, "status": "ok"}

    # Notification prefs (badge + sounds) — only active if player has CCO exec or FCC licence
    _notif_badge  = "false"
    _notif_sounds = "false"
    if player_id:
        try:
            from executive import player_has_cco, get_db as _exec_db_fn
            _edb = _exec_db_fn()
            _has_cco = player_has_cco(_edb, player_id)
            _edb.close()
            if _has_cco:
                import auth as _auth_mod
                _ndb = _auth_mod.get_db()
                _np  = _ndb.query(_auth_mod.Player).filter_by(id=player_id).first()
                if _np:
                    _notif_badge  = "true" if getattr(_np, "notif_badge",  True) else "false"
                    _notif_sounds = "true" if getattr(_np, "notif_sounds", True) else "false"
                _ndb.close()
        except Exception:
            pass

    # Player level badge for header
    _level_html = ""
    if player_id:
        try:
            from events import get_player_level
            _lvl = get_player_level(player_id)
            _lv  = _lvl["level"]
            _pct = _lvl["progress_pct"]
            _nxt = _lvl["next_threshold"]
            _trp = _lvl["trophies"]
            _tip = (f"Lv {_lv} · {_trp:,} trophies"
                    + (f" · {_pct:.0f}% to Lv {_lv+1}" if _nxt else " · MAX"))
            _level_html = (
                f'<span title="{_tip}" style="'
                f'display:inline-flex;align-items:center;gap:4px;'
                f'background:#1e1b4b;border:1px solid #4338ca;border-radius:12px;'
                f'padding:2px 9px;font-size:0.72rem;font-weight:700;color:#a5b4fc;'
                f'cursor:default;user-select:none;">'
                f'<span style="color:#818cf8;">Lv</span> {_lv}'
                f'</span>'
            )
        except Exception:
            pass

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


    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{title} · Wadsworth</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
        <!-- PWA -->
        <link rel="manifest" href="/manifest.json">
        <meta name="theme-color" content="#020617">
        <meta name="mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
        <meta name="apple-mobile-web-app-title" content="Wadsworth">
        <link rel="apple-touch-icon" href="/static/icons/apple-touch-icon.png">
        <link rel="apple-touch-icon" sizes="57x57"   href="/static/icons/ios/57.png">
        <link rel="apple-touch-icon" sizes="60x60"   href="/static/icons/ios/60.png">
        <link rel="apple-touch-icon" sizes="72x72"   href="/static/icons/ios/72.png">
        <link rel="apple-touch-icon" sizes="76x76"   href="/static/icons/ios/76.png">
        <link rel="apple-touch-icon" sizes="114x114" href="/static/icons/ios/114.png">
        <link rel="apple-touch-icon" sizes="120x120" href="/static/icons/ios/120.png">
        <link rel="apple-touch-icon" sizes="144x144" href="/static/icons/ios/144.png">
        <link rel="apple-touch-icon" sizes="152x152" href="/static/icons/ios/152.png">
        <link rel="apple-touch-icon" sizes="167x167" href="/static/icons/ios/167.png">
        <link rel="apple-touch-icon" sizes="180x180" href="/static/icons/ios/180.png">
        <link rel="apple-touch-icon" sizes="192x192" href="/static/icons/ios/192.png">
        <link rel="apple-touch-icon" sizes="512x512" href="/static/icons/ios/512.png">
        <link rel="apple-touch-icon" sizes="1024x1024" href="/static/icons/ios/1024.png">
        <meta name="msapplication-TileImage" content="/static/icons/windows/Square150x150Logo.scale-100.png">
        <meta name="msapplication-TileColor" content="#020617">
        <meta name="msapplication-square70x70logo"   content="/static/icons/windows/SmallTile.scale-100.png">
        <meta name="msapplication-square150x150logo" content="/static/icons/windows/Square150x150Logo.scale-100.png">
        <meta name="msapplication-wide310x150logo"   content="/static/icons/windows/Wide310x150Logo.scale-100.png">
        <meta name="msapplication-square310x310logo" content="/static/icons/windows/LargeTile.scale-100.png">
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
                /* Push content below OS status bar on iOS (viewport-fit=cover) and
                   below WCO titlebar on desktop */
                padding-top: env(safe-area-inset-top, 0px);
                padding-bottom: calc(60px + env(safe-area-inset-bottom, 0px));
                font-size: 18px;
            }}

            a {{ color: #38bdf8; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}

            .header {{
                border-bottom: 1px solid #1e293b;
                padding: 12px 16px;
                /* On desktop WCO the titlebar area overlays the top of the page —
                   shift content below it so it isn't hidden behind the window controls */
                padding-top: max(12px, env(titlebar-area-height, 12px));
                display: flex;
                justify-content: space-between;
                align-items: center;
                flex-wrap: wrap;
                gap: 8px;
                /* Make the header draggable on desktop so the window can still be moved */
                -webkit-app-region: drag;
            }}
            .header * {{ -webkit-app-region: no-drag; }}

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
                bottom: env(safe-area-inset-bottom, 0px);
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
                body {{ font-size: 15px; }}
                .container {{ padding: 12px 10px; }}
                .card {{ padding: 14px; }}
                input, select {{ font-size: 16px; }}

                /* Stack all common multi-column grid patterns on mobile */
                div[style*="display: grid"][style*="1fr 1fr"],
                div[style*="display: grid"][style*="2fr 1fr"],
                div[style*="display: grid"][style*="1fr 2fr"],
                div[style*="display: grid"][style*="3fr 1fr"],
                div[style*="display: grid"][style*="1fr 3fr"],
                div[style*="display: grid"][style*="repeat(2,"],
                div[style*="display: grid"][style*="repeat(3,"],
                div[style*="display: grid"][style*="repeat(4,"],
                div[style*="display: grid"][style*="repeat(5,"],
                div[style*="display: grid"][style*="repeat(2, "],
                div[style*="display: grid"][style*="repeat(3, "],
                div[style*="display: grid"][style*="repeat(4, "],
                div[style*="display: grid"][style*="repeat(5, "] {{
                    display: flex !important;
                    flex-direction: column !important;
                }}

                /* Tables: horizontal scroll instead of breaking layout */
                table {{
                    display: block;
                    overflow-x: auto;
                    -webkit-overflow-scrolling: touch;
                    width: 100%;
                    max-width: 100%;
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

            @media (max-width: 480px) {{
                body {{ font-size: 14px; }}
                .container {{ padding: 10px 8px; }}
                .card {{ padding: 10px; }}
            }}

        </style>
    </head>
    <body>
        <div class="header">
            <div class="brand"><img src="/static/logo.png" alt="Wadsworth"> Wadsworth</div>
            <div class="header-right">
                {lien_html}
                {_level_html}
                <span class="balance">{disp_sym}{disp_balance:,.2f}{disp_usd_note}</span>
                <a href="/api/logout" style="color: #ef4444; font-size: 0.85rem;">Logout</a>
            </div>
        </div>

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
                /* Never restore paused=true — always start animating on page load */
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

            /* Live-market WS hook: update ticker content without page reload */
            window._tkUpdate = function(newContent) {{
                track.innerHTML = newContent + '     ' + newContent;
                measureHalf();
            }};
        }})();
        </script>
        <script data-cfasync="false">
        /* ── Live Markets WebSocket client ─────────────────────────────────
           Connects to /ws/markets, receives price snapshots every ~30 s,
           updates [data-mkt="<type>:<symbol>"] elements and the ticker bar.
           Reconnects automatically after 15 s on disconnect.
        ── */
        (function() {{
            var _proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
            var _url   = _proto + '//' + location.host + '/ws/markets';
            var _ws, _reconnTimer;

            function _fmt(n, dec) {{ return (+n).toFixed(dec); }}

            function _buildTicker(snap) {{
                /* window._tkCategories = ['commodity','district','forex','stocks','crypto','memes','land']
                   If set, only those categories appear in this page's ticker.
                   If unset/null, all categories are included (default for generic pages). */
                var cats = window._tkCategories || null;
                function want(k) {{ return !cats || cats.indexOf(k) >= 0; }}
                var parts = [];
                if (want('commodity')) (snap.commodities || []).forEach(function(c) {{
                    var chg = (c.change_24h >= 0 ? '+' : '') + _fmt(c.change_24h, 2) + '%';
                    parts.push(c.label.toUpperCase() + ': $' + _fmt(c.price, 4) + ' (' + chg + ')');
                }});
                if (want('district')) (snap.district || []).forEach(function(c) {{
                    var chg = (c.change_24h >= 0 ? '+' : '') + _fmt(c.change_24h, 2) + '%';
                    parts.push('[D] ' + c.label.toUpperCase() + ': $' + _fmt(c.price, 4) + ' (' + chg + ')');
                }});
                if (want('forex')) (snap.forex || []).forEach(function(f) {{
                    var chg = (f.change_24h >= 0 ? '+' : '') + _fmt(f.change_24h, 4) + '%';
                    parts.push(f.pair + ': ' + _fmt(f.rate, 6) + ' (' + chg + ')');
                }});
                if (want('stocks')) (snap.stocks || []).forEach(function(s) {{
                    var chg = (s.change_24h >= 0 ? '+' : '') + _fmt(s.change_24h, 2) + '%';
                    parts.push(s.ticker + ': $' + _fmt(s.price, 4) + ' (' + chg + ')');
                }});
                if (want('crypto')) (snap.crypto || []).forEach(function(c) {{
                    parts.push(c.symbol + ': $' + _fmt(c.price_usd, 6));
                }});
                if (want('memes')) (snap.memes || []).slice(0, 10).forEach(function(m) {{
                    var chg = (m.change_24h >= 0 ? '+' : '') + _fmt(m.change_24h, 2) + '%';
                    parts.push(m.symbol + ': ' + _fmt(m.price, 8) + ' (' + chg + ')');
                }});
                if (want('land') && snap.land && snap.land.active_auctions > 0) {{
                    parts.push('LAND: ' + snap.land.active_auctions + ' auctions · avg $' +
                        Number(snap.land.avg_auction_price).toLocaleString());
                }}
                return parts.length ? parts.join(' │ ') : null;
            }}

            function _applySnap(snap) {{
                document.querySelectorAll('[data-mkt]').forEach(function(el) {{
                    var key = el.getAttribute('data-mkt');
                    var colon = key.indexOf(':');
                    if (colon < 0) return;
                    var kind = key.slice(0, colon);
                    var sym  = key.slice(colon + 1);
                    var val  = null;
                    if (kind === 'commodity') {{
                        var c = (snap.commodities || []).find(function(x) {{ return x.symbol === sym; }});
                        if (c) val = '$' + _fmt(c.price, 4);
                    }} else if (kind === 'district') {{
                        var c = (snap.district || []).find(function(x) {{ return x.symbol === sym; }});
                        if (c) val = '$' + _fmt(c.price, 4);
                    }} else if (kind === 'forex') {{
                        var f = (snap.forex || []).find(function(x) {{ return x.symbol === sym; }});
                        if (f) val = _fmt(f.rate, 6);
                    }} else if (kind === 'stock') {{
                        var s = (snap.stocks || []).find(function(x) {{ return x.ticker === sym; }});
                        if (s) val = '$' + _fmt(s.price, 4);
                    }} else if (kind === 'crypto') {{
                        var c = (snap.crypto || []).find(function(x) {{ return x.symbol === sym; }});
                        if (c) val = '$' + _fmt(c.price_usd, 6);
                    }} else if (kind === 'meme') {{
                        var m = (snap.memes || []).find(function(x) {{ return x.symbol === sym; }});
                        if (m) val = _fmt(m.price, 8);
                    }}
                    if (val !== null) el.textContent = val;
                }});
                var ticker = _buildTicker(snap);
                if (ticker && typeof window._tkUpdate === 'function') window._tkUpdate(ticker);
            }}

            function connect() {{
                _ws = new WebSocket(_url);
                _ws.onmessage = function(e) {{
                    try {{
                        var snap = JSON.parse(e.data);
                        if (snap.type === 'snapshot') _applySnap(snap);
                    }} catch(err) {{}}
                }};
                _ws.onclose = function() {{ _reconnTimer = setTimeout(connect, 15000); }};
                _ws.onerror = function() {{ _ws.close(); }};
            }}

            connect();
            window.addEventListener('pagehide', function() {{
                clearTimeout(_reconnTimer);
                if (_ws) _ws.close();
            }});
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

        {_nav_loader_html()}
        <script>
        // ── Notification Badge & In-App Sound ─────────────────────────────────
        (function() {{
          var BADGE  = {_notif_badge};
          var SOUND  = {_notif_sounds};
          var _last  = -1;
          var _audio = null;

          function _getAudio() {{
            if (!_audio) {{
              _audio = new Audio('/static/sounds/notification.mp3');
              _audio.volume = 0.7;
            }}
            return _audio;
          }}

          function _badge(n) {{
            if (!BADGE) return;
            try {{
              if (n > 0) navigator.setAppBadge && navigator.setAppBadge(n);
              else       navigator.clearAppBadge && navigator.clearAppBadge();
            }} catch(e) {{}}
            // Also update via SW for when the page isn't focused
            try {{
              if (navigator.serviceWorker && navigator.serviceWorker.controller) {{
                navigator.serviceWorker.controller.postMessage({{type:'SET_BADGE', count:n}});
              }}
            }} catch(e) {{}}
          }}

          function _sound() {{
            if (!SOUND) return;
            try {{ _getAudio().currentTime = 0; _getAudio().play().catch(function(){{}}); }} catch(e) {{}}
          }}

          function _poll() {{
            fetch('/api/notifications/unread-count', {{credentials:'same-origin'}})
              .then(function(r) {{ return r.json(); }})
              .then(function(d) {{
                var n = d.count || 0;
                _badge(n);
                if (_last >= 0 && n > _last) _sound();
                _last = n;
              }}).catch(function() {{}});
          }}

          _poll();
          setInterval(_poll, 60000);
          // Expose so WebSocket handlers on other pages can trigger an immediate refresh
          window.wadsworthRefreshNotifs = _poll;
        }})();
        </script>
        <script>
        // Android widget device-link: LauncherActivity appends ?_wdid=sha256(ANDROID_ID)
        // on every TWA launch. We persist it in sessionStorage so it survives navigations
        // (e.g. login → main page), then re-link on every page load while authenticated.
        // This ensures account switches are reflected immediately after re-login.
        (function(){{
            var params = new URLSearchParams(window.location.search);
            var wdid = params.get('_wdid');
            if (wdid) {{
                // Persist for this session across navigations
                try {{ sessionStorage.setItem('_wdid', wdid); }} catch(e) {{}}
                // Remove from visible URL without reloading
                var clean = window.location.pathname +
                    (window.location.search.replace(/[?&]_wdid=[^&]*/g, '').replace(/^\?$/, '') || '') +
                    window.location.hash;
                history.replaceState(null, '', clean);
            }}
            // Re-link on every page load (no-op if not authenticated)
            var stored = wdid || (function(){{ try {{ return sessionStorage.getItem('_wdid'); }} catch(e) {{ return null; }} }})();
            if (stored) {{
                fetch('/api/widget/link?device_id=' + encodeURIComponent(stored),
                      {{credentials:'same-origin'}}).catch(function(){{}});
            }}
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
def home(request: Request, session_token: Optional[str] = Cookie(None)):
    """Main dashboard."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        wdid = request.query_params.get("_wdid")
        if wdid:
            return RedirectResponse(url=f"/login?_wdid={wdid}", status_code=303)
        return player

    # Award daily Active Duty trophies whenever the dashboard is loaded from the app.
    # This catches the common case where the player is already logged in and never
    # hits the login route, so the auth.py TWA hook wouldn't fire.
    if request.headers.get("X-Requested-With", "") == "cc.notifly.wadsworth.twa":
        try:
            from beta import handle_twa_login
            handle_twa_login(player.id)
        except Exception:
            pass
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)

    # Reseed guard: silently re-run registration seeding if a new player has $0
    _reseed_banner = ""
    try:
        _tut_step = getattr(player, "tutorial_step", 0) or 0
        if _tut_step <= 1:
            from reserve_banks import get_usd_balance, credit_usd
            _balance = get_usd_balance(player.id)
            if _balance < 1.0:
                credit_usd(player.id, 50000.0)
                print(f"[Dashboard] Reseeded $50k for player {player.id}")
                try:
                    from land import LandPlot, get_db as _ldb_fn, create_starter_plot
                    _ldb = _ldb_fn()
                    _land_count = _ldb.query(LandPlot).filter(LandPlot.owner_id == player.id).count()
                    _ldb.close()
                    for _ in range(max(0, 3 - _land_count)):
                        create_starter_plot(player.id)
                    print(f"[Dashboard] Reseeded land plots for player {player.id}")
                except Exception as _le:
                    print(f"[Dashboard] Land reseed error: {_le}")
                try:
                    from market import give_starter_inventory
                    give_starter_inventory(player.id)
                    print(f"[Dashboard] Reseeded inventory for player {player.id}")
                except Exception as _ie:
                    print(f"[Dashboard] Inventory reseed error: {_ie}")
                _reseed_banner = """
                <div style="background:linear-gradient(135deg,#052e16,#0a3d20);border:1px solid #16a34a;border-radius:6px;padding:14px 18px;margin-bottom:20px;">
                    <strong style="color:#4ade80;">&#10003; Account setup complete!</strong>
                    <p style="color:#86efac;font-size:0.85rem;margin:6px 0 0;">
                        Your starting resources are ready: <strong>$50,000 USD</strong>, <strong>3 land plots</strong>, and a <strong>starter inventory</strong>.
                        Check your <a href="/wallet" style="color:#4ade80;text-decoration:underline;">Wallet</a> and <a href="/land" style="color:#4ade80;text-decoration:underline;">Land</a> pages to get started.
                    </p>
                </div>"""
    except Exception as _rs_err:
        print(f"[Dashboard] Reseed check error: {_rs_err}")

    # Tutorial banner/overlay
    try:
        from tutorial_ux import (
            should_show_tutorial_banner, get_tutorial_overlay_html,
        )
        tutorial_banner = ""
        tutorial_overlay = get_tutorial_overlay_html(player, "dashboard")
        if not tutorial_overlay:
            if should_show_tutorial_banner(player):
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
            ticker = offer.get("ticker", "")
            share_val = offer.get("share_value", 0.0)
            cash_c = offer.get("cash_component", 0.0)
            total_val = share_val + cash_c
            ticker_str = f" ({ticker})" if ticker else ""
            cash_str = f" + ${cash_c:,.0f} cash" if cash_c > 0 else ""
            memo = offer.get("offer_memo", "").strip()
            banner_parts.append(f"""
            <div style="background:linear-gradient(135deg,#0a1628,#0f172a);border:2px solid #38bdf8;border-radius:6px;padding:16px 20px;margin-bottom:12px;">
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;flex-wrap:wrap;">
                    <span style="background:#38bdf8;color:#020617;padding:2px 10px;border-radius:10px;font-size:0.7rem;font-weight:bold;">ACQUISITION OFFER</span>
                    <span style="color:#64748b;font-size:0.78rem;">from Player #{offer.get('offeror_id','?')}{ticker_str}</span>
                </div>
                <p style="color:#cbd5e1;margin:0 0 8px 0;font-size:0.9rem;">
                    Offering <strong style="color:#38bdf8;">{offer.get('shares_offered',0):,} shares</strong>{cash_str}
                    (≈ <strong style="color:#d4af37;">${total_val:,.0f}</strong> total) for
                    <strong style="color:#38bdf8;">{offer.get('stake_pct',0)*100:.1f}%</strong> of your business income.
                </p>
                {('<p style="color:#94a3b8;font-style:italic;font-size:0.82rem;margin:0 0 10px 0;">' + memo + '</p>') if memo else ''}
                <div style="display:flex;gap:10px;flex-wrap:wrap;">
                    <form action="/api/corporate-actions/acquisition/accept/{offer['id']}" method="post" style="display:inline;">
                        <button type="submit" style="background:#38bdf8;color:#020617;border:none;padding:8px 18px;border-radius:4px;cursor:pointer;font-size:0.85rem;font-weight:bold;">Accept</button>
                    </form>
                    <form action="/api/corporate-actions/acquisition/reject/{offer['id']}" method="post" style="display:inline;">
                        <button type="submit" style="background:#1e293b;color:#94a3b8;border:1px solid #334155;padding:8px 18px;border-radius:4px;cursor:pointer;font-size:0.85rem;">Reject</button>
                    </form>
                    <a href="/corporate-actions/dashboard" style="color:#475569;font-size:0.8rem;line-height:2.2;">Counter / View Details →</a>
                </div>
            </div>""")

        for counter in notifs.get("countered_offers", []):
            ticker = counter.get("ticker", "")
            counter_cash = counter.get("counter_cash", 0.0)
            cash_str = f" + ${counter_cash:,.0f} cash" if counter_cash > 0 else ""
            banner_parts.append(f"""
            <div style="background:linear-gradient(135deg,#0a1628,#0f172a);border:2px solid #a78bfa;border-radius:6px;padding:16px 20px;margin-bottom:12px;">
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
                    <span style="background:#a78bfa;color:#020617;padding:2px 10px;border-radius:10px;font-size:0.7rem;font-weight:bold;">COUNTER-OFFER RECEIVED</span>
                    <span style="color:#64748b;font-size:0.78rem;">from Player #{counter.get('target_id','?')}</span>
                </div>
                <p style="color:#cbd5e1;margin:0 0 12px 0;font-size:0.9rem;">
                    Player #{counter.get('target_id','?')} countered your offer:
                    <strong style="color:#a78bfa;">{counter.get('counter_shares',0):,} {ticker} shares{cash_str}
                    for {(counter.get('counter_stake_pct') or 0)*100:.1f}% income stake</strong>
                    (you originally offered {counter.get('original_shares',0):,} shares for {counter.get('original_stake_pct',0)*100:.1f}%).
                </p>
                <div style="display:flex;gap:10px;flex-wrap:wrap;">
                    <form action="/api/corporate-actions/acquisition/counter/accept/{counter['id']}" method="post" style="display:inline;">
                        <button type="submit" style="background:#a78bfa;color:#020617;border:none;padding:8px 18px;border-radius:4px;cursor:pointer;font-size:0.85rem;font-weight:bold;">Accept Counter</button>
                    </form>
                    <form action="/api/corporate-actions/acquisition/counter/reject/{counter['id']}" method="post" style="display:inline;">
                        <button type="submit" style="background:#1e293b;color:#94a3b8;border:1px solid #334155;padding:8px 18px;border-radius:4px;cursor:pointer;font-size:0.85rem;">Decline Counter</button>
                    </form>
                    <a href="/corporate-actions/dashboard" style="color:#475569;font-size:0.8rem;line-height:2.2;">View Full Details →</a>
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
                <p style="color:#cbd5e1;margin:0;font-size:0.9rem;">Your acquisition offer was <strong style="color:{color};">{status}</strong> by Player #{update.get('target_id','?')}. <a href="/corporate-actions/dashboard" style="color:#38bdf8;">View your active stakes →</a></p>
            </div>""")

        for notice in notifs.get("diffuse_notices", []):
            deadline = notice.get("deadline", "")  # key is "deadline" not "deadline_at"
            banner_parts.append(f"""
            <div style="background:linear-gradient(135deg,#0a1628,#0f172a);border:2px solid #f59e0b;border-radius:6px;padding:16px 20px;margin-bottom:12px;">
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
                    <span style="background:#f59e0b;color:#020617;padding:2px 10px;border-radius:10px;font-size:0.7rem;font-weight:bold;">DIFFUSE NOTICE — ACTION REQUIRED</span>
                </div>
                <p style="color:#cbd5e1;margin:0 0 12px 0;font-size:0.9rem;">
                    An acquirer has ended their stake. You must return
                    <strong style="color:#f59e0b;">{notice.get('shares_to_return',0):,} shares</strong>
                    by <strong style="color:#f59e0b;">{deadline}</strong> or a financial lien will be placed on your account.
                </p>
                <form action="/api/corporate-actions/diffuse/return/{notice['id']}" method="post" style="display:inline;">
                    <button type="submit" style="background:#f59e0b;color:#020617;border:none;padding:8px 18px;border-radius:4px;cursor:pointer;font-size:0.85rem;font-weight:bold;">Return Shares Now</button>
                </form>
            </div>""")

        for resolved in notifs.get("diffuse_resolved", []):
            status = resolved.get("status", "returned")
            if status == "returned":
                color, label, msg = "#22c55e", "DIFFUSE RESOLVED", "Shares have been returned successfully. The stake is fully closed."
            else:
                color, label, msg = "#f59e0b", "DIFFUSE DEFAULTED — LIEN CREATED", "The deadline passed without share return. A financial lien has been placed on the defaulting player's account."
            banner_parts.append(f"""
            <div style="background:linear-gradient(135deg,#0a1628,#0f172a);border:2px solid {color};border-radius:6px;padding:16px 20px;margin-bottom:12px;">
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
                    <span style="background:{color};color:#020617;padding:2px 10px;border-radius:10px;font-size:0.7rem;font-weight:bold;">{label}</span>
                </div>
                <p style="color:#cbd5e1;margin:0;font-size:0.9rem;">{msg} <a href="/corporate-actions/dashboard" style="color:#38bdf8;">View dashboard →</a></p>
            </div>""")

        for reneg in notifs.get("renegotiation_proposals", []):
            proposer = reneg.get("proposed_by", "?")
            new_pct = reneg.get("new_stake_pct", 0) * 100
            new_term = reneg.get("new_term_days")
            term_str = f"{new_term}-day term" if new_term else "perpetual"
            note_str = f' — "{reneg.get("note","")}"' if reneg.get("note") else ""
            reneg_id = reneg.get("id")
            banner_parts.append(f"""
            <div style="background:linear-gradient(135deg,#0a1628,#0f172a);border:2px solid #a78bfa;border-radius:6px;padding:16px 20px;margin-bottom:12px;">
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
                    <span style="background:#a78bfa;color:#020617;padding:2px 10px;border-radius:10px;font-size:0.7rem;font-weight:bold;">RENEGOTIATION PROPOSAL</span>
                </div>
                <p style="color:#cbd5e1;margin:0 0 12px 0;font-size:0.9rem;">
                    Player #{proposer} proposed new stake terms: <strong style="color:#a78bfa;">{new_pct:.1f}% stake, {term_str}{note_str}</strong>.
                </p>
                <div style="display:flex;gap:8px;">
                    <form action="/api/corporate-actions/stake/renegotiate/respond/{reneg_id}" method="post" style="display:inline;">
                        <input type="hidden" name="accept" value="true">
                        <button type="submit" style="background:#22c55e;color:#020617;border:none;padding:8px 16px;border-radius:4px;cursor:pointer;font-size:0.85rem;font-weight:bold;">Accept</button>
                    </form>
                    <form action="/api/corporate-actions/stake/renegotiate/respond/{reneg_id}" method="post" style="display:inline;">
                        <input type="hidden" name="accept" value="false">
                        <button type="submit" style="background:#f59e0b;color:#020617;border:none;padding:8px 16px;border-radius:4px;cursor:pointer;font-size:0.85rem;font-weight:bold;">Decline</button>
                    </form>
                    <a href="/corporate-actions/dashboard" style="color:#38bdf8;font-size:0.85rem;align-self:center;margin-left:8px;">View details →</a>
                </div>
            </div>""")

        for reneg_resp in notifs.get("renegotiation_responses", []):
            r_status = reneg_resp.get("status", "rejected")
            r_color = "#22c55e" if r_status == "accepted" else "#ef4444"
            r_label = "RENEGOTIATION ACCEPTED" if r_status == "accepted" else "RENEGOTIATION DECLINED"
            r_msg = f"Your proposed terms ({reneg_resp.get('new_stake_pct',0)*100:.1f}% stake) were {r_status}."
            banner_parts.append(f"""
            <div style="background:linear-gradient(135deg,#0a1628,#0f172a);border:2px solid {r_color};border-radius:6px;padding:16px 20px;margin-bottom:12px;">
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
                    <span style="background:{r_color};color:#020617;padding:2px 10px;border-radius:10px;font-size:0.7rem;font-weight:bold;">{r_label}</span>
                </div>
                <p style="color:#cbd5e1;margin:0;font-size:0.9rem;">{r_msg} <a href="/corporate-actions/dashboard" style="color:#38bdf8;">View dashboard →</a></p>
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

    # General in-game notification banners (trade pending, market opportunity, etc.)
    game_notif_banners = ""
    try:
        from push_ux import get_game_notifications, mark_game_notifications_seen
        game_notifs = get_game_notifications(player.id)
        gn_parts = []
        _type_meta = {
            "trades":    ("#f59e0b", "MARKET"),
            "corporate": ("#38bdf8", "CORPORATE"),
            "execs":     ("#a78bfa", "EXECUTIVES"),
            "general":   ("#64748b", "NOTICE"),
            "govt":      ("#22c55e", "GOVERNMENT"),
            "business":  ("#fb923c", "BUSINESS"),
            "land":      ("#84cc16", "LAND"),
            "contract":  ("#f472b6", "CONTRACT"),
            "dm":        ("#60a5fa", "MESSAGE"),
        }
        for gn in game_notifs:
            _color, _label = _type_meta.get(gn["notif_type"], ("#64748b", "NOTICE"))
            _view = f'<a href="{gn["url"]}" style="color:#38bdf8;font-size:0.82rem;margin-right:12px;">View →</a>' if gn["url"] and gn["url"] != "/" else ""
            gn_parts.append(f"""
            <div style="background:linear-gradient(135deg,#0a1628,#0f172a);border:2px solid {_color};border-radius:6px;padding:14px 18px;margin-bottom:10px;">
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;flex-wrap:wrap;">
                    <span style="background:{_color};color:#020617;padding:2px 10px;border-radius:10px;font-size:0.7rem;font-weight:bold;">{_label}</span>
                    <span style="color:#94a3b8;font-size:0.85rem;font-weight:600;">{gn["title"]}</span>
                </div>
                <p style="color:#cbd5e1;margin:0;font-size:0.88rem;">{gn["body"]}</p>
                <div style="margin-top:8px;">{_view}<a href="/settings" style="color:#475569;font-size:0.78rem;">Notification settings →</a></div>
            </div>""")
        if gn_parts:
            mark_game_notifications_seen(player.id)
        game_notif_banners = "".join(gn_parts)
    except Exception:
        game_notif_banners = ""

    dashboard_top = _reseed_banner + (tutorial_overlay or tutorial_banner)
    if acq_banners:
        dashboard_top = dashboard_top + acq_banners
    if crypto_inherit_banners:
        dashboard_top = dashboard_top + crypto_inherit_banners
    if game_notif_banners:
        dashboard_top = dashboard_top + game_notif_banners

    # Admin / Mod card — only shown to players with elevated access
    staff_card = ""
    try:
        from admins import is_admin, is_moderator
        if is_admin(player.id):
            staff_card = """
            <a href="/admin" class="dc" style="--c:#ef4444;--g:linear-gradient(90deg,#ef4444,#f87171);--glow:rgba(239,68,68,0.15);--btn:#ef4444;">
                <span class="dc-ico">🛡️</span>
                <div class="dc-t">Admin Command Center</div>
                <div class="dc-d">Full administrative control over the simulation — edit player balances, inventories, land and businesses; issue bans, timeouts, and kicks; post patch notes to the Updates channel; manage the land bank, city projects, ETF banks, bond issuance, and moderator roster. Everything that keeps the game running is in here. Handle with care.</div>
                <span class="dc-btn">Open Admin Panel</span>
            </a>"""
        elif is_moderator(player.id):
            staff_card = """
            <a href="/mod" class="dc" style="--c:#a78bfa;--g:linear-gradient(90deg,#7c3aed,#a78bfa);--glow:rgba(167,139,250,0.15);--btn:#7c3aed;--fg:#fff;">
                <span class="dc-ico">🔰</span>
                <div class="dc-t">Moderator Dashboard</div>
                <div class="dc-d">Your moderation toolkit for keeping the community healthy. Search players and review their recent chat history, issue temporary or permanent chat mutes, lift mutes early, log formal warnings, and delete individual messages that break the rules. Every action you take is recorded in the mod audit log for accountability. You do not have access to financial or balance tools — those remain admin-only.</div>
                <span class="dc-btn">Open Mod Panel</span>
            </a>"""
    except Exception:
        pass

    # ── Events card ───────────────────────────────────────────────────────────
    events_card_html = "Server-wide market effects, player tasks &amp; the Founding Tester program. Daily events reset at midnight UTC."

    # ── Persistent notifications (beta promo codes, etc.) ─────────────────────
    _persist_notif_html = ""
    try:
        from beta import get_player_notifications
        _pnotifs = get_player_notifications(player.id)
        for _pn in _pnotifs:
            _pn_id      = _pn["id"]
            _pn_title   = _pn["title"]
            _pn_body    = _pn["body"]
            _pn_payload = _pn.get("payload", {})
            _pn_code    = _pn_payload.get("code", "")
            _pn_ps_url  = _pn_payload.get("play_store", "")
            _pn_grp_url = _pn_payload.get("group_url", "")

            _code_block = ""
            if _pn_code:
                _code_block = f"""
                <div style="margin:14px 0 10px;background:#0a0f1e;border:1px solid #f59e0b;
                            border-radius:8px;padding:12px 16px;display:flex;align-items:center;
                            justify-content:space-between;gap:12px;flex-wrap:wrap;">
                    <div>
                        <div style="font-size:0.65rem;color:#92400e;letter-spacing:.1em;
                                    text-transform:uppercase;margin-bottom:4px;">Your Promo Code</div>
                        <div id="pn-code-{_pn_id}" style="font-size:1.1rem;font-weight:800;
                             color:#fbbf24;letter-spacing:.15em;font-family:monospace;">{_pn_code}</div>
                    </div>
                    <div style="display:flex;gap:8px;flex-wrap:wrap;">
                        <button onclick="navigator.clipboard.writeText('{_pn_code}');this.textContent='Copied!';setTimeout(()=>this.textContent='Copy Code',1500)"
                                style="background:#f59e0b;color:#020617;border:none;border-radius:6px;
                                       padding:8px 16px;font-size:0.78rem;font-weight:700;cursor:pointer;">
                            Copy Code
                        </button>
                        {'<a href="' + _pn_ps_url + '" target="_blank" rel="noopener" style="background:#1e293b;color:#e2e8f0;border:1px solid #334155;border-radius:6px;padding:8px 16px;font-size:0.78rem;font-weight:600;text-decoration:none;">Open Play Store ↗</a>' if _pn_ps_url else ''}
                    </div>
                </div>
                {'<div style="font-size:0.75rem;color:#78350f;margin-top:6px;">Step 1: <a href="' + _pn_grp_url + '" target="_blank" rel="noopener" style="color:#fbbf24;">Join the Google Group</a> &nbsp;→&nbsp; Step 2: Copy the code above &nbsp;→&nbsp; Step 3: Open the Play Store link and redeem the code &nbsp;→&nbsp; Step 4: Log in from the app to earn your Founding Tester badge!</div>' if _pn_grp_url else ''}"""

            _persist_notif_html += f"""
            <div style="background:linear-gradient(135deg,#1c1008,#1a0f00);border:2px solid #f59e0b;
                        border-radius:12px;padding:18px 20px;margin-bottom:16px;position:relative;">
                <div style="position:absolute;top:0;left:0;right:0;height:3px;
                            background:linear-gradient(90deg,#f59e0b,#fbbf24);border-radius:12px 12px 0 0;"></div>
                <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:12px;">
                    <div style="flex:1;">
                        <div style="font-size:0.95rem;font-weight:700;color:#fbbf24;margin-bottom:6px;">{_pn_title}</div>
                        <div style="font-size:0.80rem;color:#92400e;line-height:1.5;">{_pn_body}</div>
                        {_code_block}
                    </div>
                    <form method="post" action="/api/beta/dismiss" style="flex-shrink:0;">
                        <input type="hidden" name="notif_id" value="{_pn_id}">
                        <button type="submit" title="Dismiss"
                                style="background:transparent;border:1px solid #78350f;color:#92400e;
                                       border-radius:6px;padding:4px 10px;cursor:pointer;font-size:0.8rem;">✕</button>
                    </form>
                </div>
            </div>"""
    except Exception:
        pass

    return shell(
        "Dashboard",
        f"""
        {dashboard_top}
        {_persist_notif_html}
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
                <div class="dc-d">Build and run your production empire — factories, plantations, refineries, and retail shops. Each business consumes inputs, generates revenue every tick, and pays your workers. Set retail prices, monitor output cycles, and scale up to dominate your sector.</div>
                <span class="dc-btn">Open Terminal</span>
            </a>

            <a href="/districts" class="dc" style="--c:#6366f1;--g:linear-gradient(90deg,#6366f1,#818cf8);--glow:rgba(99,102,241,0.12);--btn:#6366f1;">
                <span class="dc-ico">🏘️</span>
                <div class="dc-t">District Businesses</div>
                <div class="dc-d">Merge land plots into specialised districts — industrial zones, commercial hubs, agricultural belts, and more. Districts unlock exclusive business types, share workers across plots, and generate district-level bonuses that scale with size.</div>
                <span class="dc-btn">Manage Districts</span>
            </a>

            <a href="/inventory" class="dc" style="--c:#f5a855;--g:linear-gradient(90deg,#f5a855,#f5d76e);--glow:rgba(245,168,85,0.12);--btn:#f5a855;">
                <span class="dc-ico">📦</span>
                <div class="dc-t">Inventory</div>
                <div class="dc-d">Everything you own that isn't land or cash — raw materials, finished goods, district items, and commodities. Use your stock to supply businesses, list on the Market, lend to other players, or hold for price appreciation.</div>
                <span class="dc-btn">View Stock</span>
            </a>

            <a href="/land" class="dc" style="--c:#22c55e;--g:linear-gradient(90deg,#22c55e,#4ade80);--glow:rgba(34,197,94,0.12);--btn:#22c55e;">
                <span class="dc-ico">🌿</span>
                <div class="dc-t">Land</div>
                <div class="dc-d">Your owned plots are where all production happens. Each plot has a terrain type that determines which businesses can be built on it. Place new businesses, view your plots by county and city, list land for sale, or browse available terrain.</div>
                <span class="dc-btn">Real Estate</span>
            </a>

            <a href="/cities" class="dc" style="--c:#34d399;--g:linear-gradient(90deg,#34d399,#6ee7b7);--glow:rgba(52,211,153,0.12);--btn:#34d399;">
                <span class="dc-ico">🏙️</span>
                <div class="dc-t">Cities</div>
                <div class="dc-d">Urban hubs that unlock advanced buildings, districts, and city-level infrastructure projects. Cities grow with player investment, attract workers, and boost production bonuses for nearby land. Check active projects, population, and development status.</div>
                <span class="dc-btn">View Cities</span>
            </a>

            <a href="/counties" class="dc" style="--c:#a3e635;--g:linear-gradient(90deg,#a3e635,#bef264);--glow:rgba(163,230,53,0.12);--btn:#a3e635;">
                <span class="dc-ico">🗾</span>
                <div class="dc-t">Counties</div>
                <div class="dc-d">The top tier of regional government in Wadsworth. Each county sets its own tax rates, controls land within its borders, and funds public services. View which county your land sits in, who governs it, and how their policies affect your business costs.</div>
                <span class="dc-btn">View Counties</span>
            </a>

            <a href="/market" class="dc" style="--c:#67e8f9;--g:linear-gradient(90deg,#67e8f9,#a5f3fc);--glow:rgba(103,232,249,0.12);--btn:#67e8f9;">
                <span class="dc-ico">📈</span>
                <div class="dc-t">Market</div>
                <div class="dc-d">The Wadsworth Commodity Exchange — a live player-driven market for raw materials and finished goods. Post sell orders, place buy orders, watch prices update in real time, and profit from supply and demand across the economy.</div>
                <span class="dc-btn">Trading Floor</span>
            </a>

            <a href="/district-market" class="dc" style="--c:#a78bfa;--g:linear-gradient(90deg,#a78bfa,#c4b5fd);--glow:rgba(167,139,250,0.12);--btn:#a78bfa;">
                <span class="dc-ico">🏪</span>
                <div class="dc-t">District Market</div>
                <div class="dc-d">A dedicated exchange for district-exclusive goods produced inside specialised zones. Trade district items with other players, browse the order book, and arbitrage price gaps between the commodity market and district supply chains.</div>
                <span class="dc-btn">District Exchange</span>
            </a>

            <a href="/land-market" class="dc" style="--c:#f5d76e;--g:linear-gradient(90deg,#f5d76e,#fde68a);--glow:rgba(245,215,110,0.12);--btn:#f5d76e;">
                <span class="dc-ico">🏗️</span>
                <div class="dc-t">Land Market</div>
                <div class="dc-d">Buy new land to expand your empire. Government plots go to auction at set intervals — bid competitively or browse player-listed land for immediate purchase. Place standing buy orders to automatically snap up plots that meet your price.</div>
                <span class="dc-btn">View Auctions</span>
            </a>

            <a href="/reserve-banks/bonds" class="dc" style="--c:#fbbf24;--g:linear-gradient(90deg,#f59e0b,#fbbf24);--glow:rgba(251,191,36,0.12);--btn:#fbbf24;">
                <span class="dc-ico">📊</span>
                <div class="dc-t">Bond Market</div>
                <div class="dc-d">Buy and sell government bonds issued by the 20+ reserve banks. Bonds pay fixed interest over 7, 14, or 30-day maturities — a lower-risk way to earn yield on idle cash. Rates shift with inflation, credit risk, and inter-bank demand.</div>
                <span class="dc-btn">View Bonds</span>
            </a>

            <a href="/brokerage/trading?mode=etf" class="dc" style="--c:#34d399;--g:linear-gradient(90deg,#10b981,#34d399);--glow:rgba(52,211,153,0.12);--btn:#34d399;">
                <span class="dc-ico">📉</span>
                <div class="dc-t">ETF &amp; Index Funds</div>
                <div class="dc-d">Trade shares in Wadsworth's passive investment funds — Apple Seeds ETF, Energy ETF, City NAV ETF, Land Bank, and the WBC-50 Index Fund. Each fund tracks an underlying commodity or index and pays dividends. Prices set by live order book.</div>
                <span class="dc-btn">ETF Trading Floor</span>
            </a>

            <a href="/banks" class="dc" style="--c:#86efac;--g:linear-gradient(90deg,#86efac,#bbf7d0);--glow:rgba(134,239,172,0.12);--btn:#86efac;">
                <span class="dc-ico">🏦</span>
                <div class="dc-t">Banking</div>
                <div class="dc-d">The full financial system — WPE stock exchange, IPOs, ETF index funds, short selling, commodity lending, credit ratings, margin trading, and the Reserve Bank for bonds and forex. Your financial hub for investing beyond your own business.</div>
                <span class="dc-btn">Open Banking</span>
            </a>

            <a href="/exchange" class="dc" style="--c:#f97316;--g:linear-gradient(90deg,#f97316,#fb923c);--glow:rgba(249,115,22,0.15);--btn:#f97316;">
                <span class="dc-ico">⛓️</span>
                <div class="dc-t">Wadsworth Crypto Exchange</div>
                <div class="dc-d">Buy, sell, and swap county native tokens at oracle-driven prices. Deposit energy to power blockchain nodes and earn block rewards through Bitcoin-like halvings. Each county sets its own exchange fee via governance — deflationary hard-cap assets with real on-chain mechanics.</div>
                <span class="dc-btn">Open Exchange</span>
            </a>

            <a href="/memecoins" class="dc" style="--c:#a855f7;--g:linear-gradient(90deg,#a855f7,#d946ef);--glow:rgba(168,85,247,0.15);--btn:#a855f7;">
                <span class="dc-ico">🚀</span>
                <div class="dc-t">Meme Coins</div>
                <div class="dc-d">Community-launched speculative tokens built on county blockchains. Trade via live order books, mint coins by burning native tokens on the bonding curve, or stake to mine. Any player can buy and trade — county members can also launch their own coin and earn creator fees on every trade.</div>
                <span class="dc-btn">Meme Market</span>
            </a>

            <a href="/wallet" class="dc" style="--c:#fb923c;--g:linear-gradient(90deg,#fb923c,#fdba74);--glow:rgba(251,146,60,0.12);--btn:#fb923c;">
                <span class="dc-ico">💳</span>
                <div class="dc-t">Wallet</div>
                <div class="dc-d">Your personal finances at a glance — current cash balance, full transaction history, multi-currency holdings, and incoming payments. See exactly where your money comes from and where it goes, down to individual ticks.</div>
                <span class="dc-btn">Open Wallet</span>
            </a>

            <a href="/executives" class="dc" style="--c:#c084fc;--g:linear-gradient(90deg,#c084fc,#e879f9);--glow:rgba(192,132,252,0.12);--btn:#c084fc;">
                <span class="dc-ico">👔</span>
                <div class="dc-t">Executives</div>
                <div class="dc-d">Hire C-suite leaders to unlock powerful abilities — CFOs that cut costs, CMOs that boost sales, COOs that speed up production cycles, and more. Train your team over time to gain a compounding edge over rival players.</div>
                <span class="dc-btn">C-Suite</span>
            </a>

            <a href="/p2p" class="dc" style="--c:#f59e0b;--g:linear-gradient(90deg,#f59e0b,#fbbf24);--glow:rgba(245,158,11,0.12);--btn:#f59e0b;">
                <span class="dc-ico">💬</span>
                <div class="dc-t">Peer to Peer</div>
                <div class="dc-d">Trade and communicate directly with other players — write binding P2P contracts, negotiate custom deals, join chatrooms, and send direct messages. Everything off the public market happens here.</div>
                <span class="dc-btn">P2P Network</span>
            </a>

            <a href="/world-map" class="dc" style="--c:#4ade80;--g:linear-gradient(90deg,#22c55e,#4ade80,#86efac);--glow:rgba(74,222,128,0.12);--btn:#4ade80;">
                <span class="dc-ico">🗺️</span>
                <div class="dc-t">World Map</div>
                <div class="dc-d">A live political and geographic atlas of Wadsworth. See every county, city, district, and terrain type. Identify where land is cheap, where cities are booming, which counties have low taxes, and where competitors are building their empires.</div>
                <span class="dc-btn">Open Map</span>
            </a>

            <a href="/events" class="dc" style="--c:#f59e0b;--g:linear-gradient(90deg,#f59e0b,#fbbf24);--glow:rgba(245,158,11,0.14);--btn:#f59e0b;">
                <span class="dc-ico">📅</span>
                <div class="dc-t">Events &amp; Tasks</div>
                <div class="dc-d">{events_card_html}</div>
                <span class="dc-btn">View Events</span>
            </a>

            <a href="/government" class="dc" style="--c:#e2e8f0;--g:linear-gradient(90deg,#94a3b8,#e2e8f0);--glow:rgba(226,232,240,0.12);--btn:#94a3b8;--fg:#020617;">
                <span class="dc-ico">🏛️</span>
                <div class="dc-t">Government</div>
                <div class="dc-d">The Federal Government of Wadsworth — treasury balances across all currencies, bond portfolio, outstanding loans to city banks, government-owned land holdings, fiscal policy rates, and a full directory of every city and county in the simulation.</div>
                <span class="dc-btn">Open Gov</span>
            </a>

            <a href="/stats/wiki" class="dc" style="--c:#f5a855;--g:linear-gradient(90deg,#f5a855,#f5d76e,#90c4f0);--glow:rgba(245,168,85,0.18);--btn:linear-gradient(90deg,#f5a855,#f5d76e);">
                <span class="dc-ico">📖</span>
                <div class="dc-t">Wikiwads</div>
                <div class="dc-d">The living game encyclopedia — look up every business type, input/output chain, district unlock, city project, executive ability, item recipe, and economic stat. Updated automatically as the game evolves. Essential for planning your next move.</div>
                <span class="dc-btn">Open Wiki</span>
            </a>

            <a href="/settings" class="dc" style="--c:#818cf8;--g:linear-gradient(90deg,#818cf8,#a5b4fc);--glow:rgba(129,140,248,0.12);--btn:#818cf8;">
                <span class="dc-ico">⚙️</span>
                <div class="dc-t">Settings</div>
                <div class="dc-d">Personalise your experience — background music, track selection, volume controls, display currency, notification preferences, and account options.</div>
                <span class="dc-btn">Open Settings</span>
            </a>

            {staff_card}

        </div>
        <script>
        // Active Duty daily check-in — fires on every dashboard load.
        // Server deduplicates to once per UTC day per player.
        // Chrome 108+ removed automatic X-Requested-With headers in TWA,
        // so we set it explicitly, gated on standalone display mode.
        (function() {{
            if (!window.matchMedia('(display-mode: standalone)').matches) return;
            var xhr = new XMLHttpRequest();
            xhr.open('GET', '/api/twa-checkin', true);
            xhr.withCredentials = true;
            xhr.setRequestHeader('X-Requested-With', 'cc.notifly.wadsworth.twa');
            xhr.send();
        }})();
        </script>
        """,
        player.cash_balance,
        player.id
    )

@router.get("/government", response_class=HTMLResponse)
def government_dashboard(
    session_token: Optional[str] = Cookie(None),
    success: str = "",
    error: str = "",
):
    """Federal Government of Wadsworth — full fiscal transparency dashboard."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return player
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)
    from datetime import datetime as _dt

    # ── 1. Government balances ────────────────────────────────────────────────
    # auth DB cash_balance: funded by loan repayments, petrodollar customs (50%),
    #                       bond interest sweeps from reserve_banks DB
    # reserve_banks PlayerCurrencyBalance["USD"]: funded by credit_usd calls
    # Both are government money — we show them separately and sum for total treasury
    gov_auth_cash = 0.0
    try:
        from auth import get_db as _adb, Player as _Player
        _db = _adb()
        _gov = _db.query(_Player).filter(_Player.id == 0).first()
        gov_auth_cash = float(_gov.cash_balance or 0) if _gov else 0.0
        _db.close()
    except Exception:
        pass

    gov_usd_reserve = 0.0
    gov_currencies = []
    try:
        from reserve_banks import (
            get_db as _rdb, PlayerCurrencyBalance as _PCB,
            StateReserveBank as _SRB,
        )
        _db = _rdb()
        _bmap = {b.currency_code: b for b in _db.query(_SRB).all()}
        for bal in _db.query(_PCB).filter(_PCB.player_id == 0).all():
            if bal.balance <= 0:
                continue
            bk = _bmap.get(bal.currency_code)
            rate = bk.usd_per_unit if bk else 1.0
            usd_val = bal.balance * rate
            if bal.currency_code == "USD":
                gov_usd_reserve = bal.balance
            gov_currencies.append({
                "code": bal.currency_code,
                "symbol": bk.currency_symbol if bk else "$",
                "flag": bk.flag_emoji if bk else "",
                "balance": bal.balance,
                "rate": rate,
                "usd_value": usd_val,
                "total_earned": bal.total_earned,
            })
        _db.close()
        gov_currencies.sort(key=lambda x: x["usd_value"], reverse=True)
    except Exception:
        pass

    gov_treasury = gov_auth_cash + gov_usd_reserve
    total_foreign_usd = sum(c["usd_value"] for c in gov_currencies if c["code"] != "USD")

    # ── 2. Bond portfolio ─────────────────────────────────────────────────────
    gov_bonds = []
    try:
        from reserve_banks import get_db as _rdb, ReserveBankBond as _RBB, StateReserveBank as _SRB
        _db = _rdb()
        _bmap = {b.id: b for b in _db.query(_SRB).all()}
        for bond in _db.query(_RBB).filter(_RBB.holder_player_id == 0, _RBB.status == "active").all():
            bk = _bmap.get(bond.bank_id)
            days_left = max(0, (bond.matures_at - _dt.utcnow()).days) if bond.matures_at else 0
            gov_bonds.append({
                "id": bond.id,
                "currency": bk.currency_code if bk else "?",
                "symbol": bk.currency_symbol if bk else "$",
                "flag": bk.flag_emoji if bk else "",
                "face_value": bond.face_value_wsc,
                "yield_rate": bond.purchase_yield,
                "interest_accrued": bond.interest_accrued or 0.0,
                "matures_at": bond.matures_at,
                "days_left": days_left,
            })
        _db.close()
        gov_bonds.sort(key=lambda x: x["face_value"], reverse=True)
    except Exception:
        pass

    # ── 3. Government-owned land ──────────────────────────────────────────────
    gov_land_total = 0
    gov_land_by_terrain = {}
    gov_land_tax_by_terrain = {}
    gov_land_value_est = 0.0
    try:
        from land import LandPlot as _LP, get_db as _ldb
        _db = _ldb()
        for p in _db.query(_LP).filter(_LP.is_government_owned == True).all():
            gov_land_total += 1
            t = p.terrain_type
            gov_land_by_terrain[t] = gov_land_by_terrain.get(t, 0) + 1
            gov_land_tax_by_terrain[t] = gov_land_tax_by_terrain.get(t, 0) + (p.monthly_tax or 0)
            gov_land_value_est += (p.monthly_tax or 0) * 12 * 10  # 10× annual tax as rough cap rate
        _db.close()
    except Exception:
        pass

    # ── 4. City bank loans ────────────────────────────────────────────────────
    gov_loans = []
    try:
        from cities import get_db as _cdb, CityBankLoan as _CBL, CityBank as _CB, City as _City
        _db = _cdb()
        _banks  = {b.id: b for b in _db.query(_CB).all()}
        _cities = {c.id: c for c in _db.query(_City).all()}
        for loan in _db.query(_CBL).filter(_CBL.is_active == True).all():
            bk   = _banks.get(loan.city_bank_id)
            city = _cities.get(bk.city_id) if bk else None
            gov_loans.append({
                "city_name": city.name if city else f"Bank #{loan.city_bank_id}",
                "principal": loan.principal,
                "total_owed": loan.total_owed,
                "amount_paid": loan.amount_paid,
                "remaining": loan.total_owed - loan.amount_paid,
                "installments_remaining": loan.installments_remaining,
                "installment_amount": loan.installment_amount,
                "created_at": loan.created_at,
            })
        _db.close()
        gov_loans.sort(key=lambda x: x["remaining"], reverse=True)
    except Exception:
        pass

    # ── 5. Active government land auctions ────────────────────────────────────
    gov_auctions = []
    try:
        from land_market import get_db as _lmdb, GovernmentAuction as _GA
        from land import LandPlot as _LP, get_db as _ldb
        _lm = _lmdb()
        _ld = _ldb()
        for auc in _lm.query(_GA).filter(_GA.is_active == True).order_by(_GA.end_time).all():
            plot = _ld.query(_LP).filter(_LP.id == auc.land_plot_id).first()
            gov_auctions.append({
                "id": auc.id,
                "terrain": plot.terrain_type.replace("_", " ").title() if plot else "Unknown",
                "features": plot.proximity_features if plot else "",
                "size": plot.size if plot else 1.0,
                "start_price": auc.starting_price,
                "current_price": auc.current_price,
                "min_price": auc.minimum_price,
                "ends": auc.end_time,
                "hours_left": max(0, int((auc.end_time - _dt.utcnow()).total_seconds() / 3600)) if auc.end_time else 0,
            })
        _lm.close()
        _ld.close()
    except Exception:
        pass

    # ── 6. All cities with project tax rates ──────────────────────────────────
    all_cities = []
    try:
        from cities import get_db as _cdb, City as _City, CityBank as _CB, CityMember as _CM, CityBankLoan as _CBL
        from city_projects import get_city_sales_tax_rate
        _db = _cdb()
        _banks   = {b.city_id: b for b in _db.query(_CB).all()}
        _members = {}
        for m in _db.query(_CM).all():
            _members[m.city_id] = _members.get(m.city_id, 0) + 1
        for city in _db.query(_City).order_by(_City.name).all():
            bk = _banks.get(city.id)
            loan_total = 0.0
            loan_count = 0
            if bk:
                for ln in _db.query(_CBL).filter(_CBL.city_bank_id == bk.id, _CBL.is_active == True).all():
                    loan_count += 1
                    loan_total += (ln.total_owed - ln.amount_paid)
            try:
                sales_tax_rate = get_city_sales_tax_rate(city.id)
            except Exception:
                sales_tax_rate = 0.0
            all_cities.append({
                "id": city.id,
                "name": city.name,
                "mayor_id": city.mayor_id,
                "currency": city.currency_type or "—",
                "app_fee": city.application_fee or 50000.0,
                "reloc_fee": city.relocation_fee or 10000.0,
                "members": _members.get(city.id, 0),
                "bank_reserves": bk.cash_reserves if bk else 0.0,
                "bank_licenses": bk.city_licenses if bk else 0.0,
                "sales_tax_pct": sales_tax_rate * 100,
                "loans": loan_count,
                "loan_debt": loan_total,
            })
        _db.close()
    except Exception:
        pass

    # ── 7. All counties ───────────────────────────────────────────────────────
    all_counties = []
    try:
        from counties import get_db as _kydb, County as _County
        _db = _kydb()
        for c in _db.query(_County).order_by(_County.name).all():
            circulating = c.total_crypto_minted - c.total_crypto_burned
            all_counties.append({
                "name": c.name,
                "symbol": c.crypto_symbol,
                "token": c.crypto_name,
                "treasury": c.treasury_balance,
                "exchange_fee_pct": (c.transaction_fee_percent or 0.0) * 100,
                "mining_pool": c.mining_energy_pool,
                "minted": c.total_crypto_minted,
                "burned": c.total_crypto_burned,
                "circulating": circulating,
                "gas_price": c.gas_price,
            })
        _db.close()
    except Exception:
        pass

    # ── 8. Commodity inventory ────────────────────────────────────────────────
    gov_commodities = {}
    try:
        from inventory import get_db as _idb, InventoryItem as _II
        _db = _idb()
        for item in _db.query(_II).filter(_II.player_id == 0).all():
            if item.quantity > 0:
                gov_commodities[item.item_type] = gov_commodities.get(item.item_type, 0.0) + item.quantity
        _db.close()
    except Exception:
        pass

    # ── 9. Company equity (ShareholderPosition) ───────────────────────────────
    gov_equity = []
    try:
        from banks.brokerage_firm import get_db as _brdb, ShareholderPosition as _SP, CompanyShares as _CS
        _db = _brdb()
        _cos = {c.id: c for c in _db.query(_CS).all()}
        for pos in _db.query(_SP).filter(_SP.player_id == 0, _SP.shares_owned > 0).all():
            co = _cos.get(pos.company_shares_id)
            if not co:
                continue
            mkt_val = (pos.shares_owned or 0) * (co.current_price or 0.0)
            gov_equity.append({
                "ticker": co.ticker_symbol,
                "name": co.company_name,
                "shares": pos.shares_owned,
                "price": co.current_price or 0.0,
                "mkt_val": mkt_val,
                "cost_basis": (pos.average_cost_basis or 0.0) * (pos.shares_owned or 0),
                "pnl": mkt_val - (pos.average_cost_basis or 0.0) * (pos.shares_owned or 0),
            })
        _db.close()
        gov_equity.sort(key=lambda x: x["mkt_val"], reverse=True)
    except Exception:
        pass

    # ── 10. Bank shareholdings ─────────────────────────────────────────────────
    gov_bank_shares = []
    try:
        from banks import get_db as _bkdb, BankShareholding as _BSH
        _db = _bkdb()
        for sh in _db.query(_BSH).filter(_BSH.player_id == 0, _BSH.shares_owned > 0).all():
            gov_bank_shares.append({
                "bank_id": sh.bank_id,
                "shares": sh.shares_owned,
                "invested": sh.total_invested,
                "dividends": sh.total_dividends_received,
            })
        _db.close()
        gov_bank_shares.sort(key=lambda x: x["invested"], reverse=True)
    except Exception:
        pass

    # ── 11. Crypto holdings (county tokens + WSC + meme coins) ───────────────
    gov_county_crypto = []
    gov_wsc_balance   = 0.0
    gov_meme_coins    = []
    try:
        from counties import get_db as _crydb, CryptoWallet as _CW, County as _Cty, get_crypto_price_by_symbol
        _db = _crydb()
        _cty_map = {c.crypto_symbol: c for c in _db.query(_Cty).all()}
        for w in _db.query(_CW).filter(_CW.player_id == 0, _CW.balance > 0).all():
            price_usd = 0.0
            try:
                price_usd = get_crypto_price_by_symbol(w.crypto_symbol)
            except Exception:
                pass
            cty = _cty_map.get(w.crypto_symbol)
            gov_county_crypto.append({
                "symbol":    w.crypto_symbol,
                "name":      cty.crypto_name if cty else w.crypto_symbol,
                "county":    cty.name if cty else "—",
                "balance":   w.balance,
                "price_usd": price_usd,
                "usd_val":   w.balance * price_usd,
                "bought":    w.total_bought,
                "mined":     w.total_mined,
            })
        _db.close()
        gov_county_crypto.sort(key=lambda x: x["usd_val"], reverse=True)
    except Exception:
        pass
    try:
        from wallet import get_db as _wdb, WSCWallet as _WSCW
        _db = _wdb()
        _wsc = _db.query(_WSCW).filter(_WSCW.player_id == 0).first()
        gov_wsc_balance = float(_wsc.balance or 0) if _wsc else 0.0
        _db.close()
    except Exception:
        pass
    try:
        from memecoins import get_db as _mdb, MemeCoinWallet as _MCW, MemeCoin as _MC
        _db = _mdb()
        _mc_map = {m.symbol: m for m in _db.query(_MC).all()}
        _county_sym_prices = {c["symbol"]: c["price_usd"] for c in gov_county_crypto}
        try:
            from counties import get_db as _crydb2, County as _Cty2
            _cdb2 = _crydb2()
            _county_id_to_sym = {c.id: c.crypto_symbol for c in _cdb2.query(_Cty2).all()}
            _cdb2.close()
        except Exception:
            _county_id_to_sym = {}
        for w in _db.query(_MCW).filter(_MCW.player_id == 0, _MCW.balance > 0).all():
            mc = _mc_map.get(w.meme_symbol)
            meme_price = mc.last_price if mc else 0.0
            county_sym = _county_id_to_sym.get(mc.county_id if mc else 0, "")
            native_usd = _county_sym_prices.get(county_sym, 0.0)
            gov_meme_coins.append({
                "symbol":  w.meme_symbol,
                "name":    mc.name if mc else w.meme_symbol,
                "balance": w.balance,
                "price":   meme_price,
                "usd_val": w.balance * meme_price * native_usd,
            })
        _db.close()
        gov_meme_coins.sort(key=lambda x: x["usd_val"], reverse=True)
    except Exception:
        pass

    # ── 12. Estate listings (government is liquidating) ───────────────────────
    gov_estate = []
    try:
        from estate import get_db as _estdb, GovernmentEstateListing as _GEL
        _db = _estdb()
        for lst in _db.query(_GEL).filter(_GEL.sold == False).order_by(_GEL.listed_at.desc()).all():
            gov_estate.append({
                "item_type":   lst.item_type,
                "quantity":    lst.quantity,
                "price":       lst.listed_price,
                "total_val":   lst.listed_price * lst.quantity,
                "deceased_id": lst.deceased_player_id,
                "listed_at":   lst.listed_at,
            })
        _db.close()
    except Exception:
        pass

    # ── Totals ────────────────────────────────────────────────────────────────
    total_bond_face     = sum(b["face_value"] for b in gov_bonds)
    total_bond_interest = sum(b["interest_accrued"] for b in gov_bonds)
    total_loan_debt     = sum(ln["remaining"] for ln in gov_loans)
    total_equity_val    = sum(e["mkt_val"] for e in gov_equity)
    total_bank_invested = sum(s["invested"] for s in gov_bank_shares)
    total_crypto_usd    = (sum(c["usd_val"] for c in gov_county_crypto)
                           + gov_wsc_balance
                           + sum(m["usd_val"] for m in gov_meme_coins))
    grand_total         = (gov_treasury + total_foreign_usd + total_bond_face
                           + total_bond_interest + gov_land_value_est + total_equity_val
                           + total_bank_invested + total_crypto_usd)

    def _usd(v): return fmt_usd(v, disp)

    # ── KPI cards ─────────────────────────────────────────────────────────────
    def _kpi(label, value, sub, color):
        return f"""<div style="background:#0a0f1e;border:1px solid {color};border-radius:8px;padding:16px 18px;">
            <div style="color:#64748b;font-size:0.7rem;letter-spacing:.06em;margin-bottom:4px;">{label}</div>
            <div style="color:{color};font-size:1.15rem;font-weight:700;">{value}</div>
            {"" if not sub else f'<div style="color:#475569;font-size:0.7rem;margin-top:3px;">{sub}</div>'}
        </div>"""

    kpis = f"""<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:12px;margin-bottom:28px;">
        {_kpi("TREASURY (USD)", _usd(gov_treasury),
              "Petrodollar customs · loan repayments · bond interest", "#e2e8f0")}
        {_kpi("FOREIGN CURRENCIES", _usd(total_foreign_usd),
              f"{len([c for c in gov_currencies if c['code'] != 'USD'])} foreign currencies held", "#38bdf8")}
        {_kpi("BOND PORTFOLIO", _usd(total_bond_face),
              f"{len(gov_bonds)} active · {_usd(total_bond_interest)} interest earned", "#fbbf24")}
        {_kpi("EQUITY & BANK SHARES", _usd(total_equity_val + total_bank_invested),
              f"{len(gov_equity)} stocks · {len(gov_bank_shares)} bank positions", "#818cf8")}
        {_kpi("CRYPTO HOLDINGS", _usd(total_crypto_usd),
              f"{len(gov_county_crypto)} county tokens · {len(gov_meme_coins)} meme · WSC {_usd(gov_wsc_balance)}", "#f472b6")}
        {_kpi("COMMODITIES", f"{len(gov_commodities)} types",
              f"{sum(gov_commodities.values()):,.1f} total units held" if gov_commodities else "None held yet", "#fb923c")}
        {_kpi("LAND HOLDINGS", f"{gov_land_total:,} plots",
              f"~{_usd(gov_land_value_est)} estimated (10× annual tax)", "#22c55e")}
        {_kpi("LOANS TO CITY BANKS", _usd(total_loan_debt),
              f"{len(gov_loans)} active loan{'s' if len(gov_loans) != 1 else ''}", "#f87171")}
        {_kpi("TOTAL ASSETS (EST.)", _usd(grand_total),
              "treasury + currencies + bonds + interest + equity + crypto + land", "#a78bfa")}
    </div>"""

    # ── Shared helpers ────────────────────────────────────────────────────────
    def _sec(title, color, content):
        return f"""<div style="background:#060c1a;border:1px solid {color};border-radius:8px;
                               padding:20px 22px;margin-bottom:20px;">
            <h3 style="color:{color};margin:0 0 16px 0;font-size:0.9rem;
                       letter-spacing:.08em;text-transform:uppercase;">{title}</h3>
            {content}</div>"""

    def _th(label, right=False):
        align = "right" if right else "left"
        return f'<th style="padding:7px 12px;color:#64748b;font-size:0.72rem;letter-spacing:.05em;text-align:{align};font-weight:600;border-bottom:1px solid #1e293b;">{label}</th>'

    def _td(val, color="#cbd5e1", right=False):
        align = "right" if right else "left"
        return f'<td style="padding:7px 12px;color:{color};font-size:0.8rem;text-align:{align};">{val}</td>'

    ts = 'style="width:100%;border-collapse:collapse;"'

    # ── Treasury breakdown ────────────────────────────────────────────────────
    treasury_note = f"""
    <div style="background:#0a1628;border:1px solid #334155;border-radius:6px;padding:12px 16px;margin-bottom:14px;">
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
            <div>
                <div style="color:#64748b;font-size:0.72rem;margin-bottom:4px;">TOTAL USD CASH</div>
                <div style="color:#e2e8f0;font-size:1.2rem;font-weight:700;">{_usd(gov_treasury)}</div>
            </div>
            <div style="color:#475569;font-size:0.75rem;max-width:420px;line-height:1.5;">
                Income: 50% petrodollar customs fee, city bank loan repayments (7% interest),
                bond interest sweeps. Outflows: city bank grants (2% every 12h),
                bond purchases (25% of surplus above {_usd(100_000)}).
            </div>
        </div>
    </div>"""
    if gov_currencies:
        rows = "".join(
            f"<tr style='border-bottom:1px solid #0f1a2e;'>"
            + _td(f"{c['flag']} {c['code']}", "#e2e8f0")
            + _td(f"{c['symbol']} {c['balance']:,.4f}")
            + _td(f"${c['rate']:.6f}")
            + _td(_usd(c["usd_value"]), "#38bdf8", right=True)
            + _td(_usd(c["total_earned"]), "#475569", right=True)
            + "</tr>"
            for c in gov_currencies
        )
        treasury_html = treasury_note + f"<table {ts}><thead><tr>" + "".join(_th(h) for h in ["Currency","Balance","Rate","USD Value","Cumulative Earned"]) + "</tr></thead><tbody>" + rows + "</tbody></table>"
    else:
        treasury_html = treasury_note

    # ── Bond portfolio ────────────────────────────────────────────────────────
    if gov_bonds:
        rows = "".join(
            f"<tr style='border-bottom:1px solid #0f1a2e;'>"
            + _td(f"{b['flag']} {b['currency']}", "#e2e8f0")
            + _td(_usd(b["face_value"]), "#fbbf24", right=True)
            + _td(f"{b['yield_rate']*100:.3f}%", "#4ade80")
            + _td(_usd(b["interest_accrued"]), "#a3e635", right=True)
            + _td(b["matures_at"].strftime("%Y-%m-%d") if b["matures_at"] else "—", "#94a3b8")
            + _td(f"{b['days_left']}d", "#64748b" if b["days_left"] > 7 else "#f87171")
            + "</tr>"
            for b in gov_bonds
        )
        bond_note = f'<p style="color:#475569;font-size:0.75rem;margin:0 0 12px 0;">Government auto-invests surplus cash (&gt;{_usd(100_000)}) into USD bonds at 25% of excess every 12 h. Interest is swept back to operating cash periodically.</p>'
        bond_html = bond_note + f"<table {ts}><thead><tr>" + "".join(_th(h) for h in ["Currency","Face Value","Yield","Interest Earned","Matures","Days Left"]) + "</tr></thead><tbody>" + rows + "</tbody></table>"
    else:
        bond_html = f'<p style="color:#475569;font-size:0.85rem;">No active bonds. Government will auto-invest once operating cash exceeds {_usd(100_000)}.</p>'

    # ── City bank loans ───────────────────────────────────────────────────────
    if gov_loans:
        rows = "".join(
            f"<tr style='border-bottom:1px solid #0f1a2e;'>"
            + _td(ln["city_name"], "#e2e8f0")
            + _td(_usd(ln["principal"]), "#94a3b8", right=True)
            + _td(_usd(ln["total_owed"]), "#94a3b8", right=True)
            + _td(_usd(ln["amount_paid"]), "#4ade80", right=True)
            + _td(_usd(ln["remaining"]), "#f87171", right=True)
            + _td(f"{ln['installments_remaining']} × {_usd(ln['installment_amount'])}", "#64748b")
            + _td(ln["created_at"].strftime("%Y-%m-%d") if ln["created_at"] else "—", "#475569")
            + "</tr>"
            for ln in gov_loans
        )
        loan_note = '<p style="color:#475569;font-size:0.75rem;margin:0 0 12px 0;">Emergency loans issued automatically when a city bank becomes insolvent. Repaid in 30 installments at 7% interest over 15 days.</p>'
        loan_html = loan_note + f"<table {ts}><thead><tr>" + "".join(_th(h) for h in ["City","Principal","Total Owed","Paid","Remaining","Installments","Issued"]) + "</tr></thead><tbody>" + rows + "</tbody></table>"
    else:
        loan_html = '<p style="color:#4ade80;font-size:0.85rem;">No outstanding city bank loans.</p>'

    # ── Land holdings ─────────────────────────────────────────────────────────
    if gov_land_by_terrain:
        rows = "".join(
            f"<tr style='border-bottom:1px solid #0f1a2e;'>"
            + _td(t.replace("_", " ").title(), "#e2e8f0")
            + _td(f"{n:,}", "#22c55e", right=True)
            + _td(_usd(gov_land_tax_by_terrain.get(t, 0) * 12 * 10), "#4ade80", right=True)
            + "</tr>"
            for t, n in sorted(gov_land_by_terrain.items(), key=lambda x: x[1], reverse=True)
        )
        land_note = '<p style="color:#475569;font-size:0.75rem;margin:0 0 12px 0;">Value estimated as 10× annual land tax (cap rate method). Government-owned plots are exempt from monthly tax collection.</p>'
        land_html = land_note + f"<table {ts}><thead><tr>" + "".join(_th(h) for h in ["Terrain","Plots","Est. Value"]) + "</tr></thead><tbody>" + rows + f"<tr style='background:#0a1628;font-weight:700;'>{_td('TOTAL','#94a3b8')}{_td(f'{gov_land_total:,}','#22c55e',right=True)}{_td(_usd(gov_land_value_est),'#4ade80',right=True)}</tr></tbody></table>"
    else:
        land_html = '<p style="color:#475569;font-size:0.85rem;">No government-owned land.</p>'

    # ── Active auctions ───────────────────────────────────────────────────────
    if gov_auctions:
        rows = "".join(
            f"<tr style='border-bottom:1px solid #0f1a2e;'>"
            + _td(f"#{a['id']}", "#64748b")
            + _td(a["terrain"], "#e2e8f0")
            + _td(a["features"] or "—", "#475569")
            + _td(f"{a['size']:.1f}", "#94a3b8", right=True)
            + _td(_usd(a["start_price"]), "#94a3b8", right=True)
            + _td(_usd(a["current_price"]), "#fbbf24", right=True)
            + _td(_usd(a["min_price"]), "#475569", right=True)
            + _td(f"{a['hours_left']}h", "#f87171" if a["hours_left"] < 6 else "#64748b")
            + f'<td style="padding:6px 12px;"><a href="/land-market?tab=auctions" style="color:#f5d76e;font-size:0.78rem;font-weight:600;text-decoration:none;border:1px solid #f5d76e44;border-radius:4px;padding:3px 8px;">Bid →</a></td>'
            + "</tr>"
            for a in gov_auctions
        )
        auction_html = f'<p style="color:#475569;font-size:0.75rem;margin:0 0 12px 0;">Click <strong style="color:#f5d76e;">Bid →</strong> to open the land auction on the market.</p>' + f"<table {ts}><thead><tr>" + "".join(_th(h) for h in ["#","Terrain","Features","Size","Start Price","Current Price","Floor","Ends In",""]) + "</tr></thead><tbody>" + rows + "</tbody></table>"
    else:
        auction_html = f'<p style="color:#475569;font-size:0.85rem;">No active government land auctions. &nbsp;<a href="/land-market?tab=auctions" style="color:#f5d76e;text-decoration:none;">View Land Market →</a></p>'

    # ── Revenue & fiscal mechanics ────────────────────────────────────────────
    def _row(label, value, note="", color="#cbd5e1"):
        return f"<tr style='border-bottom:1px solid #0f1a2e;'>{_td(label,'#94a3b8')}{_td(value,color)}{_td(note,'#475569')}</tr>"

    fiscal_html = f"<table {ts}><thead><tr>{_th('Item')}{_th('Rate / Amount')}{_th('Notes')}</tr></thead><tbody>" + "".join([
        _row("Federal Sales Tax",            "2.02% of trade value",        "Charged on buyer for every filled market &amp; district market order — goes to federal treasury", "#60a5fa"),
        _row("Business Startup Fee",         "Varies (×1.0–×N per business)","One-time fee when a player starts a business — goes to federal treasury", "#34d399"),
        _row("District Startup Fee",         "Varies (×1.0–×N per business)","One-time fee when a player starts a district business — goes to federal treasury", "#6ee7b7"),
        _row("Executive Hire Fee",           "1 daily wage",                "Paid when a player hires an executive — goes to federal treasury", "#a78bfa"),
        _row("Executive School Fee",         "Varies by level &amp; discount","Paid when enrolling an executive in school — goes to federal treasury", "#c084fc"),
        _row("Executive Wages",              "Per pay cycle",               "Regular wage payments flow through federal treasury", "#c084fc"),
        _row("Land Hoarding Tax",            "Fibonacci-scaled hourly",     "Charged on players holding more than 5 plots — goes to federal treasury", "#fb923c"),
        _row("Estate / Death Tax",           "15% of inheritance",          "Deducted from estates before heir payout — kept by federal government", "#f472b6"),
        _row("Forex Transaction Fee",        "3% per party per swap",       "Each reserve bank in an interbank currency swap pays 3% of swap value in USD to federal gov; reserves may go negative", "#38bdf8"),
        _row("Petrodollar Customs Share",    "50% of customs fee",          "Credited to government operating cash when outsiders trade in city currencies", "#4ade80"),
        _row("City Bank Emergency Loans",    "7% interest, 30 installments","Government lends to insolvent city banks; repayments return to operating cash", "#fbbf24"),
        _row("Bond Investment (outflow)",    f"25% of cash above {_usd(100_000)}","Auto-invests surplus into USD reserve bank bonds every 12 h", "#94a3b8"),
        _row("City Bank Grants (outflow)",   "2% of operating cash",        "Distributed equally to all city banks every 12 h to fund bank reserves", "#f87171"),
        _row("City Project Sales Tax",       "0.2%–0.6% per project level", "Charged on market sales of city members — goes to city bank reserves, NOT federal gov", "#475569"),
        _row("Land Monthly Tax",             "Terrain base × size",         "Collected from plot owners monthly — urban $120/plot, coastal $80, prairie $50, etc.", "#475569"),
        _row("County Crypto Exchange Fee",   "0%–10% (governance-set)",     "Exchange fee on native token trades — goes to county treasury, not federal gov", "#475569"),
    ]) + "</tbody></table>"

    # ── Cities directory ──────────────────────────────────────────────────────
    if all_cities:
        rows = "".join(
            f"<tr style='border-bottom:1px solid #0f1a2e;'>"
            + _td(f'<a href="/cities/{c["id"]}" style="color:#34d399;text-decoration:none;">{c["name"]}</a>')
            + _td(f'#{c["mayor_id"]}', "#64748b")
            + _td(str(c["members"]), "#e2e8f0", right=True)
            + _td(c["currency"], "#a3e635")
            + _td(_usd(c["app_fee"]), "#94a3b8", right=True)
            + _td(_usd(c["reloc_fee"]), "#94a3b8", right=True)
            + _td(f'{c["sales_tax_pct"]:.2f}%' if c["sales_tax_pct"] > 0 else "—", "#f59e0b" if c["sales_tax_pct"] > 0 else "#475569", right=True)
            + _td(f'{c["loans"]} loan{"s" if c["loans"] != 1 else ""} · {_usd(c["loan_debt"])} owed' if c["loans"] else "—", "#f87171" if c["loans"] else "#4ade80")
            + "</tr>"
            for c in all_cities
        )
        cities_html = f'<p style="color:#475569;font-size:0.75rem;margin:0 0 12px 0;">Fed. loans column shows money owed back to the federal government — all other figures belong to that city.</p><div style="overflow-x:auto;"><table {ts}><thead><tr>' + "".join(_th(h) for h in ["City","Mayor","Members","Currency","App Fee","Reloc Fee","Sales Tax","Fed. Loans Outstanding"]) + "</tr></thead><tbody>" + rows + "</tbody></table></div>"
    else:
        cities_html = '<p style="color:#475569;font-size:0.85rem;">No cities founded yet.</p>'

    # ── Counties directory ────────────────────────────────────────────────────
    if all_counties:
        rows = "".join(
            f"<tr style='border-bottom:1px solid #0f1a2e;'>"
            + _td(c["name"], "#e2e8f0")
            + _td(f'{c["token"]} ({c["symbol"]})', "#a78bfa")
            + _td(_usd(c["treasury"]), "#fbbf24", right=True)
            + _td(f'{c["exchange_fee_pct"]:.2f}%', "#4ade80", right=True)
            + _td(f'{c["minted"]:,.2f}', "#94a3b8", right=True)
            + _td(f'{c["burned"]:,.2f}', "#f87171", right=True)
            + _td(f'{c["circulating"]:,.2f}', "#38bdf8", right=True)
            + _td(_usd(c["mining_pool"]), "#f59e0b", right=True)
            + _td(f'${c["gas_price"]:.6f}', "#64748b", right=True)
            + "</tr>"
            for c in all_counties
        )
        counties_html = f"<div style='overflow-x:auto;'><table {ts}><thead><tr>" + "".join(_th(h) for h in ["County","Token","Treasury","Exchange Fee","Minted","Burned","Circulating","Mining Pool","Gas Price"]) + "</tr></thead><tbody>" + rows + "</tbody></table></div>"
    else:
        counties_html = '<p style="color:#475569;font-size:0.85rem;">No counties founded yet.</p>'

    # ── Company equity ────────────────────────────────────────────────────────
    if gov_equity:
        rows = "".join(
            f"<tr style='border-bottom:1px solid #0f1a2e;'>"
            + _td(f'<a href="/brokerage" style="color:#818cf8;text-decoration:none;font-weight:600;">{e["ticker"]}</a>')
            + _td(e["name"], "#cbd5e1")
            + _td(f'{e["shares"]:,}', "#94a3b8", right=True)
            + _td(_usd(e["price"]), "#94a3b8", right=True)
            + _td(_usd(e["mkt_val"]), "#818cf8", right=True)
            + _td(_usd(e["cost_basis"]), "#475569", right=True)
            + _td(_usd(e["pnl"]), "#4ade80" if e["pnl"] >= 0 else "#f87171", right=True)
            + "</tr>"
            for e in gov_equity
        )
        equity_html = f"<table {ts}><thead><tr>" + "".join(_th(h) for h in ["Ticker","Company","Shares","Price","Market Value","Cost Basis","P&L"]) + "</tr></thead><tbody>" + rows + f"<tr style='background:#0a1628;font-weight:700;'>" + _td("TOTAL","#94a3b8") + _td("") + _td("") + _td("") + _td(_usd(total_equity_val),"#818cf8",right=True) + _td("") + _td("") + "</tr></tbody></table>"
    else:
        equity_html = '<p style="color:#475569;font-size:0.85rem;">No company shares held. Government accumulates equity through IPO participation and secondary market purchases.</p>'

    # ── Bank shareholdings ────────────────────────────────────────────────────
    if gov_bank_shares:
        rows = "".join(
            f"<tr style='border-bottom:1px solid #0f1a2e;'>"
            + _td(s["bank_id"].replace("_", " ").title(), "#e2e8f0")
            + _td(f'{s["shares"]:,}', "#94a3b8", right=True)
            + _td(_usd(s["invested"]), "#818cf8", right=True)
            + _td(_usd(s["dividends"]), "#4ade80", right=True)
            + "</tr>"
            for s in gov_bank_shares
        )
        bank_shares_html = f"<table {ts}><thead><tr>" + "".join(_th(h) for h in ["Bank","Shares","Total Invested","Dividends Received"]) + "</tr></thead><tbody>" + rows + "</tbody></table>"
    else:
        bank_shares_html = '<p style="color:#475569;font-size:0.85rem;">No bank shares held.</p>'

    # ── Commodity inventory ───────────────────────────────────────────────────
    if gov_commodities:
        rows = "".join(
            f"<tr style='border-bottom:1px solid #0f1a2e;'>"
            + _td(item.replace("_", " ").title(), "#e2e8f0")
            + _td(f"{qty:,.2f}", "#fb923c", right=True)
            + "</tr>"
            for item, qty in sorted(gov_commodities.items(), key=lambda x: x[1], reverse=True)
        )
        commodity_html = f"<table {ts}><thead><tr>" + "".join(_th(h) for h in ["Item","Quantity"]) + "</tr></thead><tbody>" + rows + f"<tr style='background:#0a1628;font-weight:700;'>" + _td("TOTAL","#94a3b8") + _td(f"{sum(gov_commodities.values()):,.2f}","#fb923c",right=True) + "</tr></tbody></table>"
    else:
        commodity_html = '<p style="color:#475569;font-size:0.85rem;">No commodities held. Government will accumulate inventory as it participates in markets and receives estate seizures.</p>'

    # ── Crypto holdings ───────────────────────────────────────────────────────
    crypto_parts = []
    if gov_wsc_balance > 0 or gov_county_crypto or gov_meme_coins:
        if gov_wsc_balance > 0:
            crypto_parts.append(f'<div style="margin-bottom:10px;"><span style="color:#64748b;font-size:0.72rem;">WSC (WADSWORTH STABLE COIN)</span><div style="color:#f472b6;font-size:1rem;font-weight:700;margin-top:2px;">{gov_wsc_balance:,.4f} WSC <span style="color:#475569;font-size:0.75rem;">= {_usd(gov_wsc_balance)}</span></div></div>')
        if gov_county_crypto:
            rows = "".join(
                f"<tr style='border-bottom:1px solid #0f1a2e;'>"
                + _td(f"{c['symbol']}", "#f472b6")
                + _td(f"{c['name']} — {c['county']}", "#cbd5e1")
                + _td(f"{c['balance']:,.6f}", "#94a3b8", right=True)
                + _td(_usd(c["price_usd"]), "#475569", right=True)
                + _td(_usd(c["usd_val"]), "#f472b6", right=True)
                + _td(f"{c['mined']:,.4f} mined / {c['bought']:,.4f} bought", "#475569")
                + "</tr>"
                for c in gov_county_crypto
            )
            crypto_parts.append(f"<p style='color:#64748b;font-size:0.72rem;margin:10px 0 6px 0;'>COUNTY NATIVE TOKENS</p><table {ts}><thead><tr>" + "".join(_th(h) for h in ["Symbol","Token / County","Balance","USD Price","USD Value","Acquisition"]) + "</tr></thead><tbody>" + rows + "</tbody></table>")
        if gov_meme_coins:
            rows = "".join(
                f"<tr style='border-bottom:1px solid #0f1a2e;'>"
                + _td(m["symbol"], "#f472b6")
                + _td(m["name"], "#cbd5e1")
                + _td(f"{m['balance']:,.6f}", "#94a3b8", right=True)
                + _td(f"{m['price']:,.6f} native", "#475569", right=True)
                + _td(_usd(m["usd_val"]) if m["usd_val"] > 0 else "—", "#f472b6", right=True)
                + "</tr>"
                for m in gov_meme_coins
            )
            crypto_parts.append(f"<p style='color:#64748b;font-size:0.72rem;margin:10px 0 6px 0;'>MEME COINS <span style='color:#475569;font-weight:400;'>(priced in county native tokens)</span></p><table {ts}><thead><tr>" + "".join(_th(h) for h in ["Symbol","Name","Balance","Price","USD Value"]) + "</tr></thead><tbody>" + rows + "</tbody></table>")
        crypto_html = "".join(crypto_parts)
    else:
        crypto_html = '<p style="color:#475569;font-size:0.85rem;">No crypto holdings. Government can acquire county tokens, WSC, and meme coins through market participation.</p>'

    # ── Estate listings ───────────────────────────────────────────────────────
    if gov_estate:
        rows = "".join(
            f"<tr style='border-bottom:1px solid #0f1a2e;'>"
            + _td(lst["item_type"].replace("_"," ").title(), "#e2e8f0")
            + _td(f'{lst["quantity"]:,.2f}', "#94a3b8", right=True)
            + _td(_usd(lst["price"]), "#fbbf24", right=True)
            + _td(_usd(lst["total_val"]), "#fbbf24", right=True)
            + _td(f'Player #{lst["deceased_id"]}', "#475569")
            + _td(lst["listed_at"].strftime("%Y-%m-%d") if lst["listed_at"] else "—", "#475569")
            + "</tr>"
            for lst in gov_estate
        )
        estate_html = f'<p style="color:#475569;font-size:0.75rem;margin:0 0 12px 0;">Assets seized from deleted or inactive player accounts being liquidated by the government.</p>' + f"<table {ts}><thead><tr>" + "".join(_th(h) for h in ["Item","Quantity","Unit Price","Total Value","Estate Of","Listed"]) + "</tr></thead><tbody>" + rows + "</tbody></table>"
    else:
        estate_html = '<p style="color:#475569;font-size:0.85rem;">No estate listings active.</p>'

    # ── Government Activity Ledger ────────────────────────────────────────────
    try:
        from govt_ledger import EVENT_META as _LEDGER_META
    except Exception:
        _LEDGER_META = {}
    ledger_html = ""
    try:
        from govt_ledger import get_recent_events
        _ledger_events = get_recent_events(limit=75)
        if _ledger_events:
            _lrows = []
            for ev in _ledger_events:
                meta = _LEDGER_META.get(ev.event_type, (ev.event_type.replace("_"," ").title(), ev.direction, "#94a3b8"))
                label, default_dir, badge_color = meta
                arrow = "↓" if ev.direction == "in" else "↑"
                arrow_color = "#4ade80" if ev.direction == "in" else "#f87171"
                amt_color = "#4ade80" if ev.direction == "in" else "#f87171"
                sign = "+" if ev.direction == "in" else "−"
                ts_str = ev.timestamp.strftime("%m/%d %H:%M") if ev.timestamp else "—"
                counterparty = ev.counterparty or "—"
                desc = ev.description or ""
                _lrows.append(
                    f"<tr style='border-bottom:1px solid #0f1a2e;'>"
                    f"<td style='padding:7px 10px;color:{arrow_color};font-size:1rem;font-weight:700;'>{arrow}</td>"
                    f"<td style='padding:7px 10px;'><span style='background:{badge_color}22;color:{badge_color};border:1px solid {badge_color}44;border-radius:4px;padding:2px 7px;font-size:0.72rem;font-weight:600;white-space:nowrap;'>{label}</span></td>"
                    f"<td style='padding:7px 10px;color:{amt_color};font-weight:700;text-align:right;white-space:nowrap;'>{sign}{ev.currency} {ev.amount:,.2f}</td>"
                    f"<td style='padding:7px 10px;color:#94a3b8;font-size:0.82rem;'>{counterparty}</td>"
                    f"<td style='padding:7px 10px;color:#64748b;font-size:0.78rem;'>{desc}</td>"
                    f"<td style='padding:7px 10px;color:#475569;font-size:0.75rem;white-space:nowrap;'>{ts_str}</td>"
                    f"</tr>"
                )
            ledger_html = (
                f'<p style="color:#475569;font-size:0.75rem;margin:0 0 12px 0;">Showing the 75 most recent government fiscal events. ↓ = money flowing in to federal treasury, ↑ = money flowing out.</p>'
                f'<table style="width:100%;border-collapse:collapse;">'
                f'<thead><tr>'
                + "".join(_th(h) for h in ["", "Event", "Amount", "Counterparty", "Description", "Time"])
                + f'</tr></thead><tbody>'
                + "".join(_lrows)
                + f'</tbody></table>'
            )
        else:
            ledger_html = '<p style="color:#475569;font-size:0.85rem;">No government fiscal events recorded yet. Events will appear here as the economy runs.</p>'
    except Exception as _le:
        ledger_html = f'<p style="color:#475569;font-size:0.85rem;">Ledger unavailable: {_le}</p>'

    # ── Flash messages ────────────────────────────────────────────────────────
    flash_html = ""
    if success:
        flash_html = f'<div style="background:#052e16;border:1px solid #15803d;border-radius:6px;padding:10px 16px;margin-bottom:18px;color:#4ade80;font-size:0.85rem;">✓ {success}</div>'
    elif error:
        flash_html = f'<div style="background:#1c0505;border:1px solid #b91c1c;border-radius:6px;padding:10px 16px;margin-bottom:18px;color:#f87171;font-size:0.85rem;">✗ {error}</div>'

    body = f"""
    <div style="display:flex;align-items:center;gap:14px;margin-bottom:24px;">
        <span style="font-size:2rem;">🏛️</span>
        <div>
            <h2 style="margin:0;color:#e2e8f0;">Federal Government of Wadsworth</h2>
            <p style="margin:4px 0 0;color:#475569;font-size:0.82rem;">
                Federal treasury, holdings, and fiscal operations — updated every page load.
            </p>
        </div>
    </div>
    {flash_html}
    {kpis}
    {_sec("Treasury", "#e2e8f0", treasury_html)}
    {_sec("Bond Portfolio", "#fbbf24", bond_html)}
    {_sec("Company Equity", "#818cf8", equity_html)}
    {_sec("Bank Shareholdings", "#6366f1", bank_shares_html)}
    {_sec("Commodity Inventory", "#fb923c", commodity_html)}
    {_sec("Crypto Holdings", "#f472b6", crypto_html)}
    {_sec("Outstanding Loans to City Banks", "#f87171", loan_html)}
    {_sec("Government-Owned Land", "#22c55e", land_html)}
    {_sec("Active Land Auctions", "#f5d76e", auction_html)}
    {_sec("Estate Liquidation", "#fbbf24", estate_html)}
    {_sec("Revenue &amp; Fiscal Mechanics", "#94a3b8", fiscal_html)}
    {_sec("Government Activity Log", "#38bdf8", ledger_html)}

    <div style="border-top:2px solid #1e293b;margin:32px 0 24px 0;padding-top:20px;">
        <div style="color:#334155;font-size:0.72rem;letter-spacing:.1em;text-transform:uppercase;margin-bottom:4px;">Jurisdictional Overview</div>
        <p style="color:#475569;font-size:0.8rem;margin:0;">
            Cities and counties are independent governments with their own treasuries, banks, and elected officials.
            The data below is federal oversight information — these assets belong to those governments, not to the federal treasury.
        </p>
    </div>
    {_sec("Cities", "#34d399", cities_html)}
    {_sec("Counties", "#a78bfa", counties_html)}
    """
    return shell("Government", body, player.cash_balance, player.id)

@router.post("/api/gov/force-grants")
def gov_force_grants(session_token: Optional[str] = Cookie(None)):
    from fastapi.responses import RedirectResponse as _RR
    player = require_auth(session_token)
    if isinstance(player, _RR): return player
    try:
        from admins import is_admin as _ia
        if not _ia(player.id):
            return _RR("/admin?error=Admin+only", status_code=303)
        from cities import process_government_grants
        process_government_grants(0)
        return _RR("/admin?success=City+grants+distributed+successfully", status_code=303)
    except Exception as e:
        return _RR(f"/admin?error={str(e)[:80]}", status_code=303)


@router.post("/api/gov/force-bond-invest")
def gov_force_bond_invest(session_token: Optional[str] = Cookie(None)):
    from fastapi.responses import RedirectResponse as _RR
    player = require_auth(session_token)
    if isinstance(player, _RR): return player
    try:
        from admins import is_admin as _ia
        if not _ia(player.id):
            return _RR("/admin?error=Admin+only", status_code=303)
        from cities import tick_government_bond_investing
        tick_government_bond_investing(0)
        return _RR("/admin?success=Bond+investment+tick+completed", status_code=303)
    except Exception as e:
        return _RR(f"/admin?error={str(e)[:80]}", status_code=303)


@router.post("/api/gov/force-charter-fees")
def gov_force_charter_fees(session_token: Optional[str] = Cookie(None)):
    from fastapi.responses import RedirectResponse as _RR
    player = require_auth(session_token)
    if isinstance(player, _RR): return player
    try:
        from admins import is_admin as _ia
        if not _ia(player.id):
            return _RR("/admin?error=Admin+only", status_code=303)
        from cities import tick_city_bank_charter_fees
        tick_city_bank_charter_fees(0)
        return _RR("/admin?success=Charter+fees+collected", status_code=303)
    except Exception as e:
        return _RR(f"/admin?error={str(e)[:80]}", status_code=303)


# ── Beta program API routes ───────────────────────────────────────────────────

@router.post("/api/beta/request")
def beta_submit_request(
    session_token: Optional[str] = Cookie(None),
    google_email: str = Form(...),
):
    from fastapi.responses import RedirectResponse as _RR
    player = require_auth(session_token)
    if isinstance(player, _RR): return player
    try:
        from beta import submit_request
        ok, msg = submit_request(player.id, google_email)
        import urllib.parse
        param = "success" if ok else "error"
        return _RR(f"/events?{param}={urllib.parse.quote(msg)}", status_code=303)
    except Exception as e:
        import urllib.parse
        return _RR(f"/events?error={urllib.parse.quote(str(e)[:120])}", status_code=303)


@router.get("/api/public/ticker")
async def public_ticker():
    """Live market data for the login-page tickers — no auth required."""
    from fastapi.responses import JSONResponse as _JR
    result = {"commodities": [], "district": [], "stocks": []}

    # ── Commodity market (last traded price per item type) ────────────────────
    try:
        from market import Trade, get_db as _mdb
        _db = _mdb()
        try:
            rows = (_db.query(Trade.item_type, Trade.price)
                    .order_by(Trade.executed_at.desc())
                    .limit(400).all())
        finally:
            _db.close()
        seen = {}
        for r in rows:
            if r.item_type not in seen:
                seen[r.item_type] = r.price
        result["commodities"] = [
            {"label": k.replace("_", " ").title(), "price": v}
            for k, v in seen.items()
        ][:40]
    except Exception:
        pass

    # ── District market (last traded price per item type) ─────────────────────
    try:
        from district_market import DistrictTrade, get_db as _dmdb
        _db = _dmdb()
        try:
            rows = (_db.query(DistrictTrade.item_type, DistrictTrade.price)
                    .order_by(DistrictTrade.executed_at.desc())
                    .limit(400).all())
        finally:
            _db.close()
        seen = {}
        for r in rows:
            if r.item_type not in seen:
                seen[r.item_type] = r.price
        result["district"] = [
            {"label": k.replace("_", " ").title(), "price": v}
            for k, v in seen.items()
        ][:40]
    except Exception:
        pass

    # ── Stock exchange (listed companies with price > 0) ──────────────────────
    try:
        from banks.brokerage_firm import CompanyShares, get_db as _bfdb
        _db = _bfdb()
        try:
            companies = (_db.query(CompanyShares)
                         .filter(CompanyShares.current_price > 0)
                         .order_by(CompanyShares.ticker_symbol.asc())
                         .limit(60).all())
            result["stocks"] = [
                {"label": c.ticker_symbol, "name": c.company_name, "price": c.current_price}
                for c in companies
            ]
        finally:
            _db.close()
    except Exception:
        pass

    return _JR(result)


@router.get("/api/twa-checkin")
def twa_checkin(request: Request, session_token: Optional[str] = Cookie(None)):
    """Called by client-side XHR on every page load.
    Only awards Active Duty trophies when the TWA header is present
    (Chrome WebView in the Android app sets it automatically)."""
    from fastapi.responses import JSONResponse as _JR
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return _JR({"ok": False}, status_code=401)
    twa_hdr = request.headers.get("X-Requested-With", "")
    if twa_hdr != "cc.notifly.wadsworth.twa":
        return _JR({"ok": True, "twa": False})
    try:
        from beta import handle_twa_login
        handle_twa_login(player.id)
        return _JR({"ok": True, "twa": True})
    except Exception as e:
        return _JR({"ok": False, "error": str(e)})


@router.post("/api/beta/dismiss")
def beta_dismiss_notification(
    session_token: Optional[str] = Cookie(None),
    notif_id: int = Form(...),
):
    from fastapi.responses import RedirectResponse as _RR
    player = require_auth(session_token)
    if isinstance(player, _RR): return player
    try:
        from beta import dismiss_notification
        dismiss_notification(notif_id, player.id)
    except Exception:
        pass
    return _RR("/", status_code=303)


@router.get("/businesses", response_class=HTMLResponse)
def businesses(session_token: Optional[str] = Cookie(None), sort: str = "name", biz_filter: str = "all"):
    return _businesses_impl(session_token, sort, biz_filter)

def _businesses_impl(session_token: Optional[str] = None, sort: str = "name", biz_filter: str = "all"):
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

        # --- Quick Buy panel builder ---
        def _qb_panel(item_type, panel_id, default_qty):
            item_disp = item_type.replace("_", " ").title()
            return (
                f'<div class="qb-panel" id="{panel_id}" data-item="{item_type}">'
                f'<div style="font-size:0.72rem;color:#64748b;margin-bottom:8px;">Quick Buy: '
                f'<b style="color:#e2e8f0;">{item_disp}</b></div>'
                f'<div style="display:flex;gap:8px;flex-wrap:wrap;align-items:flex-end;">'
                f'<div><div style="font-size:0.65rem;color:#64748b;margin-bottom:2px;">Quantity</div>'
                f'<input type="number" class="qb-input qb-qty" value="{default_qty}" min="1" step="1"'
                f' oninput="qbSchedule(this)"></div>'
                f'<div><div style="font-size:0.65rem;color:#64748b;margin-bottom:2px;">Cap price ({disp["code"]})</div>'
                f'<input type="number" class="qb-input qb-cap" min="0.000001" step="any" placeholder="auto"'
                f' oninput="qbSchedule(this)"></div></div>'
                f'<div class="qb-preview" style="margin-top:8px;min-height:30px;"></div>'
                f'<form method="post" action="/api/market/quick-buy/execute" style="margin-top:8px;" onsubmit="return qbSubmit(this)">'
                f'<input type="hidden" name="item_type" value="{item_type}">'
                f'<input type="hidden" name="quantity" value="{default_qty}">'
                f'<input type="hidden" name="cap_price" value="">'
                f'<div style="display:flex;gap:6px;">'
                f'<button type="submit" class="btn-sm btn-sm-blue" style="font-size:0.7rem;">Confirm Buy</button>'
                f'<button type="button" class="btn-sm" style="background:#1e293b;color:#94a3b8;font-size:0.7rem;"'
                f' onclick="document.getElementById(\'{panel_id}\').style.display=\'none\'">Cancel</button>'
                f'</div></form></div>'
            )

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
            is_tut_reward = getattr(biz, 'is_tutorial_reward', False)
            startup_cost = 0 if is_tut_reward else config.get("startup_cost", 0)
            wage_cost    = 0 if is_tut_reward else config.get("base_wage_cost", 0)
            if plot:
                tax_label = '<span style="color:#4ade80;font-weight:bold;">FREE</span>' if getattr(plot, 'is_tutorial_reward', False) else fmt_usd(plot.monthly_tax, disp) + "/mo"
                plot_info = f"Plot #{plot.id} · {plot.terrain_type.replace('_',' ').title()} · Tax: {tax_label}"
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
                    # Build quick-buy buttons for missing inputs on this line
                    missing_html = ""
                    qb_panels    = ""
                    for req in line.get("inputs", []):
                        have = inv.get(req["item"], 0)
                        need = req["quantity"]
                        if have < need:
                            safe  = req["item"].replace("'", "").replace('"', "")
                            pid   = f"qbp-{biz.id}-{li}-{safe}"
                            dqty  = max(1, int(need * 5 - have))
                            iname = req["item"].replace("_", " ").title()
                            missing_html += (
                                f'<span style="font-size:0.68rem;color:#f59e0b;">'
                                f'{iname} {have:,.0f}/{need:,}</span>'
                                f'<button type="button" class="btn-sm btn-sm-blue"'
                                f' style="font-size:0.62rem;padding:2px 5px;"'
                                f' onclick="qbToggle(\'{pid}\')">Buy</button> '
                            )
                            qb_panels += _qb_panel(req["item"], pid, dqty)
                    missing_row = (
                        f'<div style="display:flex;flex-wrap:wrap;gap:5px;align-items:center;'
                        f'padding:3px 8px 3px;background:#0a0e1a;border-radius:0 0 3px 3px;'
                        f'margin-top:-4px;margin-bottom:4px;">'
                        f'<span style="font-size:0.62rem;color:#475569;">Missing:</span> {missing_html}</div>'
                    ) if missing_html else ""

                    lines_html += f'''<div class="line-row{' paused' if lp else ''}" id="line-{biz.id}-{li}">
                        {dot}
                        <span style="font-size:0.78rem;color:#94a3b8;flex:1;">{inp_str} → {out_str}</span>
                        <form action="/api/business/toggle-line?sort={sort}&biz_filter={biz_filter}" method="post" style="flex-shrink:0;display:inline;">
                            <input type="hidden" name="business_id" value="{biz.id}">
                            <input type="hidden" name="line_index" value="{li}">
                            <button type="submit" class="btn-sm {'btn-sm-green' if lp else 'btn-sm-orange'}">{'Resume' if lp else 'Pause'}</button>
                        </form>
                    </div>{missing_row}{qb_panels}'''
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
                    r_safe   = item.replace("'", "").replace('"', "")
                    r_pid    = f"qbp-r-{biz.id}-{r_safe}"
                    r_defqty = max(100, 500 - in_stock)
                    retail_rows += f'''<div class="line-row{' paused' if ip else ''}" id="retail-{biz.id}-{item}" style="flex-wrap:wrap;gap:6px;">
                        <span style="font-size:0.82rem;flex:1;">{item.replace("_"," ").title()} <span style="color:#64748b;font-size:0.75rem;">e={stats.get("elasticity","?")}</span> {dot}</span>
                        <div style="display:flex;gap:5px;align-items:center;flex-wrap:wrap;">
                            <span style="color:#38bdf8;font-size:0.82rem;font-weight:bold;">{cur_p}</span>
                            <form action="/api/retail/set-price?sort={sort}&biz_filter={biz_filter}" method="post" style="display:flex;gap:4px;align-items:center;">
                                <input type="hidden" name="item_type" value="{item}">
                                <input type="number" name="price" step="0.01" min="0.01" placeholder="{disp["code"]}" style="width:90px;padding:3px 5px;font-size:0.78rem;">
                                <button type="submit" class="btn-sm btn-sm-blue">Set</button>
                            </form>
                            <button type="button" class="btn-sm btn-sm-blue" style="font-size:0.72rem;"
                                onclick="qbToggle('{r_pid}')">Restock</button>
                            <form action="/api/business/toggle-retail?sort={sort}&biz_filter={biz_filter}" method="post" style="display:inline;">
                                <input type="hidden" name="business_id" value="{biz.id}">
                                <input type="hidden" name="item_type" value="{item}">
                                <button type="submit" class="btn-sm {'btn-sm-green' if ip else 'btn-sm-orange'}">{'Resume' if ip else 'Pause'}</button>
                            </form>
                        </div>
                    </div>{_qb_panel(item, r_pid, r_defqty)}'''
                detail_html = f'''<div class="biz-card-body">
                    <div style="font-size:0.72rem;color:#64748b;margin-bottom:8px;text-transform:uppercase;letter-spacing:.05em;">Retail Products</div>
                    {retail_rows}
                </div>'''

            stock_btn_html = (
                f'<button type="button" class="btn-sm btn-sm-blue" onclick="spToggle({biz.id})"'
                f' style="font-size:0.8rem;">Stock</button>'
                if biz_class == "production" else ""
            )
            sp_panel_html = (
                f'<div id="sp-{biz.id}" class="sp-panel">'
                f'<div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:10px;">'
                f'<span style="font-size:0.72rem;color:#64748b;">Input deficit for</span>'
                f'<input type="number" class="qb-input" id="sp-nc-{biz.id}" value="5" min="1" max="100" step="1" style="width:54px;">'
                f'<span style="font-size:0.72rem;color:#64748b;">cycles</span>'
                f'<button type="button" class="btn-sm btn-sm-blue" style="font-size:0.7rem;" onclick="spFetch({biz.id})">Recalc</button>'
                f'<button type="button" class="btn-sm" style="background:#1e293b;color:#94a3b8;font-size:0.7rem;"'
                f' onclick="document.getElementById(\'sp-{biz.id}\').style.display=\'none\'">Close</button>'
                f'</div>'
                f'<div id="sp-body-{biz.id}"><span style="color:#475569;font-size:0.8rem;">Loading…</span></div>'
                f'</div>'
            ) if biz_class == "production" else ""

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
                        {stock_btn_html}
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
                {sp_panel_html}
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
.qb-panel{{display:none;margin:0 0 6px;background:#060c18;border:1px solid #334155;border-radius:4px;padding:10px;}}
.sp-panel{{display:none;margin:0 16px 8px;background:#060c18;border:1px solid #334155;border-radius:4px;padding:12px;}}
.qb-input{{padding:4px 6px;font-size:0.78rem;background:#0f172a;border:1px solid #334155;color:#e2e8f0;border-radius:3px;width:100px;}}
</style>
<script>
(function(){{
  var _t = {{}};
  window.qbToggle = function(id) {{
    var p = document.getElementById(id);
    if (!p) return;
    var hidden = p.style.display === 'none' || p.style.display === '';
    document.querySelectorAll('.qb-panel').forEach(function(x){{ x.style.display='none'; }});
    if (hidden) {{ p.style.display='block'; qbFetch(p); }}
  }};
  window.qbSchedule = function(el) {{
    var p = el.closest('.qb-panel'); if (!p) return;
    clearTimeout(_t[p.id]);
    _t[p.id] = setTimeout(function(){{ qbFetch(p); }}, 450);
  }};
  window.qbFetch = function(p) {{
    var item = p.dataset.item;
    var qty  = p.querySelector('.qb-qty').value || '1';
    var cap  = p.querySelector('.qb-cap').value;
    var prev = p.querySelector('.qb-preview');
    prev.innerHTML = '<span style="color:#475569;">Loading…</span>';
    var params = new URLSearchParams({{item_type:item, quantity:qty}});
    if (cap) params.set('cap_price', cap);
    fetch('/api/market/quick-buy/preview?' + params)
      .then(function(r){{ return r.json(); }})
      .then(function(d) {{
        if (d.error) {{ prev.innerHTML='<span style="color:#ef4444;">'+d.error+'</span>'; return; }}
        var capIn = p.querySelector('.qb-cap');
        if (d.suggested_cap_raw != null && !capIn.value) {{
          p.dataset.suggestedCap = d.suggested_cap_raw;
          capIn.placeholder = d.suggested_cap_disp || String(d.suggested_cap_raw);
        }}
        var h = '';
        if (d.fills && d.fills.length) {{
          h += '<div style="color:#64748b;font-size:0.68rem;margin-bottom:2px;">Order book:</div>';
          d.fills.forEach(function(f){{
            h += '<div style="margin-left:8px;color:#94a3b8;font-size:0.7rem;">'+Number(f.qty).toLocaleString()+'× @ '+f.price_disp+'</div>';
          }});
          h += '<div style="margin-top:4px;padding-top:4px;border-top:1px solid #1e293b;font-size:0.72rem;">';
          h += '<span style="color:#22c55e;">'+Number(d.total_filled).toLocaleString()+' filled</span>';
          if (d.avg_price_disp) h += ' @ '+d.avg_price_disp+' avg';
          if (d.immediate_cost_disp) h += ' = <b style="color:#38bdf8;">'+d.immediate_cost_disp+'</b>';
          h += '</div>';
        }}
        if (d.unfilled_qty > 0) {{
          h += '<div style="color:#f59e0b;font-size:0.7rem;margin-top:3px;">'+Number(d.unfilled_qty).toLocaleString()+' unavailable → buy order at cap price</div>';
          if (d.reservation_disp) h += '<div style="color:#64748b;font-size:0.7rem;">Max reservation: '+d.reservation_disp+'</div>';
        }}
        if ((!d.fills || !d.fills.length) && !d.unfilled_qty) h += '<span style="color:#64748b;font-size:0.7rem;">No active sell orders found.</span>';
        if (d.forex_fee_disp) h += '<div style="color:#64748b;font-size:0.7rem;margin-top:2px;">Forex fee: '+d.forex_fee_disp+'</div>';
        prev.innerHTML = h;
      }})
      .catch(function(){{ prev.innerHTML='<span style="color:#ef4444;font-size:0.7rem;">Preview unavailable.</span>'; }});
  }};
  window.qbSubmit = function(form) {{
    var p   = form.closest('.qb-panel');
    var qty = p.querySelector('.qb-qty').value;
    var cap = p.querySelector('.qb-cap').value;
    if (!cap || parseFloat(cap) <= 0) {{
      cap = p.dataset.suggestedCap || '';
      if (!cap || parseFloat(cap) <= 0) {{
        alert('Please enter a cap price before confirming.');
        return false;
      }}
    }}
    var prev = p.querySelector('.qb-preview');
    prev.innerHTML = '<span style="color:#475569;font-size:0.8rem;">Placing order…</span>';
    var data = new FormData(form);
    data.set('quantity', qty);
    data.set('cap_price', cap);
    fetch(form.action, {{method:'POST', body:data}})
      .then(function(r){{ return r.json(); }})
      .then(function(d){{
        if (d.ok) {{
          prev.innerHTML = '<span style="color:#22c55e;font-size:0.8rem;">✓ '+d.message+'</span>';
          setTimeout(function(){{ p.style.display='none'; }}, 2500);
        }} else {{
          prev.innerHTML = '<span style="color:#ef4444;font-size:0.8rem;">'+(d.error||'Order failed.')+'</span>';
        }}
      }})
      .catch(function(){{ prev.innerHTML='<span style="color:#ef4444;font-size:0.8rem;">Request failed.</span>'; }});
    return false;
  }};
  window.spToggle = function(bizId) {{
    var p = document.getElementById('sp-' + bizId);
    if (!p) return;
    var hidden = p.style.display === 'none' || p.style.display === '';
    document.querySelectorAll('.sp-panel').forEach(function(x){{ x.style.display='none'; }});
    if (hidden) {{ p.style.display='block'; spFetch(bizId); }}
  }};
  window.spFetch = function(bizId) {{
    var p    = document.getElementById('sp-' + bizId);
    var body = document.getElementById('sp-body-' + bizId);
    var nc   = document.getElementById('sp-nc-' + bizId);
    if (!body) return;
    body.innerHTML = '<span style="color:#475569;font-size:0.8rem;">Loading…</span>';
    var nCycles = nc ? (nc.value || '5') : '5';
    fetch('/api/market/quick-buy/stock-plan?business_id=' + bizId
          + '&n_cycles=' + encodeURIComponent(nCycles))
      .then(function(r){{ return r.json(); }})
      .then(function(d){{
        if (d.error) {{ body.innerHTML='<span style="color:#ef4444;font-size:0.8rem;">'+d.error+'</span>'; return; }}
        body.innerHTML = d.html || '';
      }})
      .catch(function(){{ body.innerHTML='<span style="color:#ef4444;font-size:0.8rem;">Error loading plan.</span>'; }});
  }};
}})();
</script>
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
    return _inventory_page_impl(session_token, filter, sort, dir)

def _inventory_page_impl(session_token: Optional[str] = None, filter: str = "all", sort: str = "name", dir: str = "asc"):
    """Inventory management view."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return player
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)
    try:
        import inventory as inv_mod
        inv = inv_mod.get_player_inventory(player.id)

        categories = {
            "all":          ("🗃️",  "All"),
            "agriculture":  ("🌾",  "Agriculture"),
            "livestock":    ("🐄",  "Livestock"),
            "food_bev":     ("🍽️",  "Food & Bev"),
            "industrial":   ("🏭",  "Industrial"),
            "construction": ("🏗️",  "Construction"),
            "vehicles":     ("🚗",  "Vehicles & Parts"),
            "consumer":     ("🛍️",  "Consumer Goods"),
            "weaponry":     ("⚔️",  "Weaponry"),
            "luxury":       ("💎",  "Luxury"),
            "services":     ("🤝",  "Services"),
            "finance":      ("📊",  "Finance"),
        }
        cat_colors = {
            "all": "#38bdf8", "agriculture": "#22c55e", "livestock": "#f59e0b",
            "food_bev": "#f97316", "industrial": "#94a3b8", "construction": "#78716c",
            "vehicles": "#60a5fa", "consumer": "#ec4899", "weaponry": "#ef4444",
            "luxury": "#d97706", "services": "#a78bfa", "finance": "#6366f1",
        }

        # Maps item_types.json / district_items.json category → filter tab key
        _json_to_filter = {
            # Agriculture
            "crops": "agriculture", "seeds": "agriculture", "produce": "agriculture",
            # Livestock (live/raw animal products)
            "livestock": "livestock", "seafood": "livestock", "shellfish": "livestock",
            "animals": "livestock", "zoo_supplies": "livestock",
            # Food & Bev (processed/consumed)
            "dairy": "food_bev", "meat": "food_bev", "seafood_product": "food_bev",
            "prepared_food": "food_bev", "baked_goods": "food_bev", "confectionery": "food_bev",
            "food": "food_bev", "canned_goods": "food_bev", "condiments": "food_bev",
            "sweeteners": "food_bev", "beverages": "food_bev", "alcohol": "food_bev",
            "ingredients": "food_bev", "fast_food": "food_bev", "retail_food": "food_bev",
            "food_service": "food_bev",
            # Industrial
            "industrial": "industrial", "components": "industrial", "metals": "industrial",
            "ore": "industrial", "packaging": "industrial", "fuel": "industrial",
            "energy": "industrial", "liquids": "industrial", "electronics": "industrial",
            "utilities": "industrial", "logistics": "industrial", "lab_equipment": "industrial",
            "robotics": "industrial", "medical_equipment": "industrial",
            # Construction
            "construction": "construction", "materials": "construction",
            "prison_infrastructure": "construction", "zoo_infrastructure": "construction",
            "wood": "luxury",  # Scoreboard & Smartboard — miscategorised in data, treated as luxury
            # Vehicles & Parts
            "vehicle": "vehicles", "vehicles": "vehicles", "vehicle_parts": "vehicles",
            # Consumer Goods
            "apparel": "consumer", "textiles": "consumer", "accessories": "consumer",
            "home_goods": "consumer", "health": "consumer", "media": "consumer",
            "tobacco": "consumer", "cured_tobacco": "consumer", "personal_care": "consumer",
            "essential_oils": "consumer", "appliances": "consumer", "pharmaceuticals": "consumer",
            "medical_supplies": "consumer", "education": "consumer", "prison": "consumer",
            "retail_shopping": "consumer", "entertainment": "consumer",
            # Weaponry
            "military": "weaponry", "retail_military": "weaponry", "intelligence": "weaponry",
            # Luxury
            "luxury": "luxury",
            # Services
            "services": "services", "retail_service": "services", "retail_transport": "services",
            "retail_medical": "services", "retail_education": "services",
            "retail_entertainment": "services", "retail_zoo": "services",
            "retail_prison": "services", "hospitality": "services",
            # Finance
            "financial": "finance",
        }

        # Filter tabs — pill style with emoji
        filter_tabs = '<div class="inv-filter-tabs">'
        for k, (emoji, label) in categories.items():
            color = cat_colors.get(k, "#38bdf8")
            if k == filter:
                style = f"background:{color}20;border:1px solid {color};color:{color};"
            else:
                style = "background:transparent;border:1px solid #1e293b;color:#64748b;"
            filter_tabs += f'<a href="/inventory?filter={k}&sort={sort}&dir={dir}" class="inv-filter-tab" style="{style}">{emoji} {label}</a>'
        filter_tabs += '</div>'

        # Sort controls
        sort_controls = '<div class="inv-sort-bar"><span class="inv-sort-label">Sort:</span>'
        for s_key, s_label in [("name", "Name"), ("qty", "Quantity"), ("value", "Value")]:
            if s_key == sort:
                new_dir = "desc" if dir == "asc" else "asc"
                arrow = " ↑" if dir == "asc" else " ↓"
                link_style = "color:#38bdf8;border-bottom:1px solid #38bdf8;"
            else:
                new_dir, arrow = "asc", ""
                link_style = "color:#64748b;"
            sort_controls += f'<a href="/inventory?filter={filter}&sort={s_key}&dir={new_dir}" class="inv-sort-link" style="{link_style}">{s_label}{arrow}</a>'
        sort_controls += '</div>'

        import market as market_mod
        # Filter items — look up item_info first so we can use its category field
        filtered = []
        for item, qty in inv.items():
            item_info = inv_mod.get_item_info(item) or {}
            if filter != "all":
                json_cat = item_info.get("category", "")
                if _json_to_filter.get(json_cat, "consumer") != filter:
                    continue
            try:
                unit_price = market_mod.get_market_price(item) or 0
            except Exception:
                unit_price = 0
            filtered.append((item, qty, item_info, unit_price))

        # Sort items
        if sort == "qty":
            filtered.sort(key=lambda x: x[1], reverse=True)
        elif sort == "value":
            filtered.sort(key=lambda x: x[1] * x[3], reverse=True)
        else:
            filtered.sort(key=lambda x: x[0], reverse=(dir == "desc"))

        # Summary stats
        total_items = len(filtered)
        total_value = sum(qty * up for _, qty, _, up in filtered)
        max_value = max((qty * up for _, qty, _, up in filtered), default=1) or 1
        total_val_display = fmt_usd(total_value, disp) if total_value else "—"

        summary_bar = f'''
        <div class="inv-summary-bar">
            <div class="inv-summary-stats">
                <div class="inv-stat">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" stroke-width="2"><path d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>
                    <span class="inv-stat-val">{total_items}</span>
                    <span class="inv-stat-lbl">items</span>
                </div>
                <div class="inv-stat">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#22c55e" stroke-width="2"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/></svg>
                    <span class="inv-stat-val" style="color:#22c55e;">{total_val_display}</span>
                    <span class="inv-stat-lbl">est. value</span>
                </div>
            </div>
            <div class="inv-search-wrap">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#64748b" stroke-width="2.5"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
                <input type="text" id="inv-search" class="inv-search-input" placeholder="Search items..." oninput="filterItems(this.value)">
            </div>
        </div>'''

        quick_access = '''
        <div class="inv-quick-access">
            <a href="/inventory/trusted-list" class="inv-quick-btn">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0110 0v4"/></svg>
                Trusted Traders
            </a>
            <a href="/inventory/swaps" class="inv-quick-btn inv-quick-btn--swap">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="17 1 21 5 17 9"/><path d="M3 11V9a4 4 0 014-4h14"/><polyline points="7 23 3 19 7 15"/><path d="M21 13v2a4 4 0 01-4 4H3"/></svg>
                Item Swaps
            </a>
        </div>'''

        # Build item cards
        # Rich emoji map keyed to item_types.json category values
        _json_cat_emoji = {
            "accessories": "👜", "alcohol": "🍺", "animals": "🐾",
            "apparel": "👕", "appliances": "🏠", "baked_goods": "🍞",
            "beverages": "🥤", "canned_goods": "🥫", "components": "⚙️",
            "condiments": "🫙", "confectionery": "🍬", "construction": "🏗️",
            "crops": "🌾", "cured_tobacco": "🚬", "dairy": "🥛",
            "education": "📚", "electronics": "💡", "energy": "⚡",
            "entertainment": "🎭", "essential_oils": "🧴", "financial": "📊",
            "food": "🍽️", "food_service": "🍽️", "fuel": "⛽",
            "health": "💊", "home_goods": "🏠", "hospitality": "🏨",
            "industrial": "🏭", "ingredients": "🧂", "intelligence": "🕵️",
            "lab_equipment": "🔬", "liquids": "💧", "livestock": "🐄",
            "logistics": "🚚", "luxury": "💎", "materials": "🪵",
            "meat": "🥩", "media": "📺", "medical_equipment": "🩺",
            "medical_supplies": "🩹", "metals": "🔩", "military": "🎖️",
            "ore": "⛏️", "packaging": "📦", "personal_care": "🧼",
            "pharmaceuticals": "💊", "prepared_food": "🍲", "prison": "🔒",
            "prison_infrastructure": "🏛️", "produce": "🥬", "retail_education": "📚",
            "retail_entertainment": "🎮", "retail_food": "🛒", "retail_medical": "🏥",
            "retail_military": "⚔️", "retail_prison": "🔒", "retail_service": "🏪",
            "retail_shopping": "🛍️", "retail_transport": "🚌", "retail_zoo": "🦁",
            "robotics": "🤖", "seafood": "🐟", "seafood_product": "🦐",
            "seeds": "🌱", "services": "🤝", "shellfish": "🦪",
            "sweeteners": "🍯", "textiles": "🧵", "tobacco": "🌿",
            "utilities": "🔌", "vehicle": "🚗", "vehicle_parts": "🔧",
            "vehicles": "🚛", "wood": "🌲", "zoo_infrastructure": "🏛️",
            "zoo_supplies": "🦁",
        }
        _json_cat_color = {
            # Agriculture
            "seeds": "#22c55e", "crops": "#22c55e", "produce": "#84cc16",
            # Livestock
            "livestock": "#f59e0b", "animals": "#f59e0b",
            "seafood": "#06b6d4", "shellfish": "#06b6d4", "zoo_supplies": "#f59e0b",
            # Food & Bev
            "food": "#f97316", "baked_goods": "#fb923c", "confectionery": "#fb923c",
            "prepared_food": "#f97316", "canned_goods": "#f97316",
            "condiments": "#fbbf24", "sweeteners": "#fbbf24",
            "meat": "#ef4444", "seafood_product": "#06b6d4",
            "dairy": "#cbd5e1", "beverages": "#38bdf8", "alcohol": "#a855f7",
            "ingredients": "#fbbf24", "food_service": "#f97316",
            # Industrial
            "industrial": "#64748b", "energy": "#eab308", "fuel": "#dc2626",
            "liquids": "#06b6d4", "electronics": "#38bdf8", "components": "#6366f1",
            "metals": "#94a3b8", "ore": "#78716c", "packaging": "#64748b",
            "utilities": "#0891b2", "logistics": "#60a5fa", "lab_equipment": "#64748b",
            "robotics": "#6366f1", "medical_equipment": "#10b981",
            # Construction
            "materials": "#94a3b8", "construction": "#8b5cf6",
            "prison_infrastructure": "#78716c", "zoo_infrastructure": "#f59e0b",
            "wood": "#a16207",
            # Vehicles
            "vehicle": "#60a5fa", "vehicles": "#60a5fa", "vehicle_parts": "#60a5fa",
            # Consumer Goods
            "apparel": "#ec4899", "textiles": "#ec4899", "accessories": "#e879f9",
            "home_goods": "#14b8a6", "appliances": "#14b8a6",
            "health": "#22c55e", "personal_care": "#a78bfa", "essential_oils": "#a78bfa",
            "pharmaceuticals": "#22c55e", "medical_supplies": "#22c55e",
            "tobacco": "#a78bfa", "cured_tobacco": "#a78bfa",
            "media": "#8b5cf6", "education": "#38bdf8", "prison": "#64748b",
            "entertainment": "#8b5cf6",
            # Weaponry
            "military": "#dc2626", "retail_military": "#dc2626", "intelligence": "#ef4444",
            # Luxury
            "luxury": "#d97706",
            # Services
            "services": "#a78bfa", "hospitality": "#a78bfa",
            "retail_service": "#a78bfa", "retail_food": "#f97316",
            "retail_shopping": "#ec4899", "retail_entertainment": "#8b5cf6",
            "retail_medical": "#22c55e", "retail_education": "#38bdf8",
            "retail_transport": "#60a5fa", "retail_zoo": "#f59e0b",
            "retail_prison": "#64748b",
            # Finance
            "financial": "#6366f1",
        }

        cards_html = ""
        if not filtered:
            cards_html = '''
            <div class="inv-empty">
                <svg width="52" height="52" viewBox="0 0 24 24" fill="none" stroke="#1e293b" stroke-width="1.5"><path d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>
                <p>No items in this category</p>
            </div>'''
        else:
            for item, qty, item_info, unit_price in filtered:
                json_cat_key = item_info.get("category", "")
                filter_cat = _json_to_filter.get(json_cat_key, "consumer")
                bar_color = cat_colors.get(filter_cat, "#64748b")
                # Use the rich JSON category for the pill
                json_cat = item_info.get("category", "other")
                pill_emoji = _json_cat_emoji.get(json_cat, "📦")
                pill_label = json_cat.replace("_", " ").title()
                pill_color = _json_cat_color.get(json_cat, "#64748b")

                display_name = item_info.get("name") or item.replace("_", " ").title()
                description = item_info.get("description", "No description available.")
                desc_short = description[:82] + "…" if len(description) > 82 else description

                item_value = qty * unit_price
                val_pct = min(100, int((item_value / max_value) * 100)) if max_value else 0

                if unit_price:
                    val_html = f'<div class="inv-card-value">💰 {fmt_usd(item_value, disp)} <span class="inv-unit-price">· {fmt_usd(unit_price, disp)}/unit</span></div>'
                    bar_html = f'<div class="inv-value-bar"><div class="inv-value-fill" style="width:{val_pct}%;background:{bar_color}33;border-right:2px solid {bar_color};"></div></div>'
                else:
                    val_html = '<div class="inv-card-value inv-card-value--none">No market price</div>'
                    bar_html = '<div class="inv-value-bar"></div>'

                form_id = f"invform-{item}"
                if item.endswith("_shares"):
                    market_action_html = '<a href="/brokerage/trading?mode=etf" class="btn-blue" style="font-size:0.75rem;margin-top:6px;display:inline-block;">Trade on ETF Floor →</a>'
                else:
                    market_action_html = (
                        f'<button class="inv-list-toggle" onclick="invToggleForm(\'{form_id}\', this)" type="button">'
                        f'<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>'
                        f' List on Market</button>'
                        f'<div class="inv-list-form" id="{form_id}">'
                        f'<form action="/api/inventory/list" method="post" class="inv-list-inner">'
                        f'<input type="hidden" name="item_type" value="{item}">'
                        f'<div class="inv-list-fields">'
                        f'<input type="number" name="quantity" placeholder="Qty" min="0" max="{qty:.0f}" class="inv-input" required>'
                        f'<input type="number" name="price" step="0.0001" placeholder="Price ({disp["code"]})" class="inv-input" required>'
                        f'<button type="submit" class="btn-blue inv-submit-btn">List →</button>'
                        f'</div></form></div>'
                    )
                cards_html += f'''
                <div class="inv-card" data-name="{display_name.lower()} {item.lower()}">
                    <div class="inv-card-top">
                        <span class="inv-cat-pill" style="color:{pill_color};border-color:{pill_color}40;background:{pill_color}12;">{pill_emoji} {pill_label}</span>
                        <span class="inv-qty-badge">{qty:,.0f}</span>
                    </div>
                    <div class="inv-card-name">{display_name}</div>
                    <div class="inv-card-desc">{desc_short}</div>
                    {val_html}
                    {bar_html}
                    {market_action_html}
                </div>'''

        page_assets = '''<style>
        .inv-page-header { display:flex; align-items:center; gap:10px; margin-bottom:20px; }
        .inv-page-header h1 { margin:0; font-size:1.25rem; color:#f1f5f9; font-weight:700; letter-spacing:-0.01em; }

        .inv-summary-bar {
            display:flex; justify-content:space-between; align-items:center;
            background:#0f172a; border:1px solid #1e293b; border-radius:6px;
            padding:12px 16px; margin-bottom:16px; gap:12px; flex-wrap:wrap;
        }
        .inv-summary-stats { display:flex; gap:24px; align-items:center; }
        .inv-stat { display:flex; align-items:center; gap:6px; }
        .inv-stat-val { font-size:0.95rem; font-weight:700; color:#e2e8f0; }
        .inv-stat-lbl { font-size:0.68rem; color:#64748b; text-transform:uppercase; letter-spacing:0.06em; }
        .inv-search-wrap {
            display:flex; align-items:center; gap:8px;
            background:#020617; border:1px solid #1e293b; border-radius:4px; padding:6px 10px;
        }
        .inv-search-input {
            background:transparent; border:none; color:#e2e8f0; outline:none;
            font-family:inherit; font-size:0.82rem; width:180px;
        }
        .inv-search-input::placeholder { color:#475569; }
        .inv-search-wrap:focus-within { border-color:#38bdf8; }

        .inv-quick-access { display:flex; gap:8px; margin-bottom:18px; flex-wrap:wrap; }
        .inv-quick-btn {
            display:inline-flex; align-items:center; gap:7px;
            background:#1e1b4b; border:1px solid #4c1d95; color:#a78bfa;
            padding:7px 14px; border-radius:5px; text-decoration:none;
            font-size:0.8rem; font-weight:500; transition:background 0.15s, border-color 0.15s;
        }
        .inv-quick-btn:hover { background:#2d1f6e; border-color:#7c3aed; text-decoration:none; }
        .inv-quick-btn--swap { border-color:#5b21b6; color:#c4b5fd; }
        .inv-quick-btn--swap:hover { border-color:#8b5cf6; }

        .inv-filter-tabs { display:flex; flex-wrap:wrap; gap:6px; margin-bottom:14px; }
        .inv-filter-tab {
            display:inline-flex; align-items:center; gap:4px;
            padding:5px 12px; border-radius:20px; text-decoration:none;
            font-size:0.78rem; font-weight:600; transition:opacity 0.15s; white-space:nowrap;
        }
        .inv-filter-tab:hover { text-decoration:none; opacity:0.8; }

        .inv-sort-bar { display:flex; gap:16px; align-items:center; margin-bottom:18px; }
        .inv-sort-label { color:#475569; font-size:0.72rem; text-transform:uppercase; letter-spacing:0.07em; }
        .inv-sort-link { text-decoration:none; font-size:0.8rem; padding-bottom:1px; }
        .inv-sort-link:hover { opacity:0.8; text-decoration:none; }

        .inv-grid {
            display:grid;
            grid-template-columns:repeat(auto-fill, minmax(268px, 1fr));
            gap:10px;
        }
        .inv-card {
            background:#0f172a; border:1px solid #1e293b; border-radius:7px;
            padding:14px 15px; transition:border-color 0.18s, box-shadow 0.18s;
        }
        .inv-card:hover { border-color:#334155; box-shadow:0 4px 18px #00000038; }

        .inv-card-top { display:flex; justify-content:space-between; align-items:center; margin-bottom:9px; }
        .inv-cat-pill {
            font-size:0.67rem; padding:2px 8px; border-radius:10px;
            border:1px solid; font-weight:700; text-transform:uppercase; letter-spacing:0.05em;
        }
        .inv-qty-badge { font-size:1.15rem; font-weight:800; color:#38bdf8; letter-spacing:-0.03em; }

        .inv-card-name { font-size:0.92rem; font-weight:700; color:#f1f5f9; margin-bottom:4px; }
        .inv-card-desc { font-size:0.72rem; color:#94a3b8; margin-bottom:9px; line-height:1.45; min-height:2em; }
        .inv-card-value { font-size:0.76rem; color:#22c55e; margin-bottom:6px; }
        .inv-card-value--none { color:#64748b; }
        .inv-unit-price { color:#64748b; }

        .inv-value-bar { height:3px; background:#0d1b2a; border-radius:2px; margin-bottom:11px; overflow:hidden; }
        .inv-value-fill { height:100%; border-radius:2px; }

        .inv-list-toggle {
            display:flex; align-items:center; justify-content:center; gap:6px; width:100%;
            background:transparent; border:1px solid #1e293b; color:#475569;
            padding:5px 10px; border-radius:4px; cursor:pointer; font-family:inherit;
            font-size:0.74rem; font-weight:500; transition:all 0.15s; margin-top:2px;
        }
        .inv-list-toggle:hover { border-color:#38bdf8; color:#38bdf8; }
        .inv-list-toggle.open { border-color:#38bdf840; color:#38bdf8; background:#38bdf808; }

        .inv-list-form { display:none; margin-top:10px; padding-top:10px; border-top:1px solid #1e293b; }
        .inv-list-inner { display:flex; flex-direction:column; gap:0; }
        .inv-list-fields { display:flex; gap:5px; align-items:center; }
        .inv-input {
            flex:1; min-width:0; background:#020617; border:1px solid #1e293b;
            color:#e2e8f0; padding:5px 7px; border-radius:3px;
            font-size:0.78rem; font-family:inherit;
        }
        .inv-input:focus { outline:none; border-color:#38bdf8; }
        .inv-submit-btn { font-family:inherit; white-space:nowrap; font-size:0.78rem; }

        .inv-empty {
            grid-column:1 / -1; display:flex; flex-direction:column;
            align-items:center; justify-content:center;
            padding:56px 20px; color:#334155; gap:14px;
        }
        .inv-empty p { font-size:0.85rem; margin:0; }

        @media (max-width:600px) {
            .inv-grid { grid-template-columns:1fr; }
            .inv-search-input { width:calc(100vw - 120px) !important; max-width:220px; }
            .inv-search-wrap { flex: 1; }
            .inv-summary-bar { flex-direction:column; align-items:flex-start; }
            .inv-summary-stats { gap:16px; }
            .inv-filter-tabs { overflow-x:auto; flex-wrap:nowrap; padding-bottom:4px; }
            .inv-filter-tabs::-webkit-scrollbar { height:3px; }
            .inv-filter-tabs::-webkit-scrollbar-thumb { background:#334155; border-radius:2px; }
        }
        </style>
        <script>
        function filterItems(q) {
            q = q.toLowerCase().trim();
            document.querySelectorAll("#inv-grid .inv-card").forEach(function(c) {
                c.style.display = (!q || (c.dataset.name || "").includes(q)) ? "" : "none";
            });
        }
        function invToggleForm(id, btn) {
            var form = document.getElementById(id);
            var opening = form.style.display === "none" || form.style.display === "";
            form.style.display = opening ? "block" : "none";
            btn.classList.toggle("open", opening);
            if (opening) {
                btn.innerHTML = \'<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="18 15 12 9 6 15"/></svg> Cancel\';
            } else {
                btn.innerHTML = \'<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg> List on Market\';
            }
        }
        </script>'''

        inv_body = (
            page_assets
            + '<a href="/" style="color:#38bdf8;font-size:0.85rem;">← Dashboard</a>'
            + '<div class="inv-page-header">'
            + '<svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" stroke-width="2"><path d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>'
            + '<h1>Inventory</h1>'
            + '</div>'
            + summary_bar
            + quick_access
            + filter_tabs
            + sort_controls
            + f'<div class="inv-grid" id="inv-grid">{cards_html}</div>'
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
def land(session_token: Optional[str] = Cookie(None), sort: str = "id", order: str = "asc", success: str = "", error: str = "", restoration_msg: str = "", restoration_error: str = ""):
    return _land_impl(session_token, sort, order, success, error, restoration_msg, restoration_error)

def _land_impl(session_token: Optional[str] = None, sort: str = "id", order: str = "asc", success: str = "", error: str = "", restoration_msg: str = "", restoration_error: str = ""):
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

        land_html = '''<style>
        @media (max-width: 600px) {
            .land-card-row { flex-direction: column !important; }
            .land-card-main { min-width: 0 !important; }
            .land-card-actions { min-width: 0 !important; width: 100% !important; }
            .land-eff-bar { width: 100% !important; }
            .land-form-row select { min-width: 0 !important; width: 100% !important; }
        }
        </style>
        <a href="/" style="color: #38bdf8;"><- Dashboard</a>'''

        _land_success = {"listing_cancelled": "Listing cancelled.", "land_listed": "Plot listed on the market."}
        _land_errors = {"cancel_failed": "Could not cancel — listing may already be inactive.", "listing_failed": "Could not list plot. Ensure it is vacant and not already listed."}
        if success in _land_success:
            land_html += f'<div style="padding:10px 16px; background:#052e16; border:1px solid #16a34a; color:#4ade80; margin:8px 0;">{_land_success[success]}</div>'
        elif error in _land_errors:
            land_html += f'<div style="padding:10px 16px; background:#1a0505; border:1px solid #dc2626; color:#f87171; margin:8px 0;">{_land_errors[error]}</div>'
        if restoration_msg:
            land_html += f'<div style="padding:10px 16px; background:#052e16; border:1px solid #16a34a; color:#4ade80; margin:8px 0;">{restoration_msg}</div>'
        if restoration_error:
            land_html += f'<div style="padding:10px 16px; background:#1a0505; border:1px solid #dc2626; color:#f87171; margin:8px 0;">{restoration_error}</div>'

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

            # Efficiency Restoration module
            try:
                from land_restoration import get_restoration_module_html
                land_html += get_restoration_module_html(player, disp)
            except Exception as _re:
                import traceback
                print(f"[Land/Restoration] render error: {_re}")
                traceback.print_exc()

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
                    <div class="land-card-row" style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px;">
                        <div class="land-card-main" style="flex: 1; min-width: 250px;">
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
                                    {'<span style="color:#4ade80;font-weight:bold;">FREE &#127942; Tutorial Reward</span>' if getattr(plot, "is_tutorial_reward", False) else f'<span style="color: #f59e0b;">{fmt_usd(plot.monthly_tax, disp)}/mo</span>'}
                                </div>
                            </div>

                            <div style="margin-top: 8px;">
                                <div style="display: flex; align-items: center; gap: 8px;">
                                    <span style="font-size: 0.8rem; color: #64748b;">Efficiency:</span>
                                    <span style="font-size: 0.85rem; color: {eff_color}; font-weight: bold;">{eff:.3f}%</span>
                                </div>
                                <div class="land-eff-bar" style="background: #020617; height: 6px; border-radius: 3px; margin-top: 4px; width: 200px;">
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
                    land_html += '<div class="land-card-actions" style="display: flex; flex-direction: column; gap: 10px; min-width: 220px;">'
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
            from tutorial_ux import get_tutorial_overlay_html, get_tutorial7_overlay_html
            tut_overlay = get_tutorial_overlay_html(player, "land")
            if not tut_overlay:
                tut_overlay = get_tutorial7_overlay_html(player, "land")
            if tut_overlay:
                land_html = tut_overlay + land_html
        except Exception:
            pass

        return shell("Land", land_html, player.cash_balance, player.id)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return shell("Land", f"Error: {e}", player.cash_balance, player.id)

@router.post("/api/land-restoration/start")
def api_land_restoration_start(session_token: Optional[str] = Cookie(None)):
    """Initiate efficiency restoration for all eligible plots."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    try:
        from land_restoration import start_restoration
        ok, msg = start_restoration(player.id)
        if ok:
            return RedirectResponse(url=f"/land?restoration_msg={msg}", status_code=303)
        return RedirectResponse(url=f"/land?restoration_error={msg}", status_code=303)
    except Exception as e:
        return RedirectResponse(url=f"/land?restoration_error=Server+error:+{e}", status_code=303)


@router.get("/land-market", response_class=HTMLResponse)
def land_market_page(session_token: Optional[str] = Cookie(None), sort: str = "price", order: str = "asc", terrain: str = "all", tab: str = "auctions", success: str = "", error: str = ""):
    return _land_market_page_impl(session_token, sort, order, terrain, tab, success, error)

def _land_market_page_impl(session_token: Optional[str] = None, sort: str = "price", order: str = "asc", terrain: str = "all", tab: str = "auctions", success: str = "", error: str = ""):
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

        # Market stats — use only entries where the land plot was found,
        # so the displayed count matches the number of cards rendered.
        total_auctions = len(auction_plots)
        total_listings = len(listing_plots)
        total_available = total_auctions + total_listings
        avg_auction_price = (sum(a.current_price for a in auctions) / total_auctions) if total_auctions else 0
        avg_listing_price = (sum(l.asking_price for l in listings) / total_listings) if total_listings else 0

        market_html = '''<style>
        @media (max-width: 600px) {
            .lm-card-row { flex-direction: column !important; }
            .lm-card-main { min-width: 0 !important; }
            .lm-card-action { min-width: 0 !important; width: 100% !important; flex-direction: row !important; flex-wrap: wrap !important; }
            .lm-price-row { flex-wrap: wrap !important; gap: 6px !important; }
            .lm-form-row { flex-wrap: wrap !important; }
            .lm-form-row input, .lm-form-row select { width: 100% !important; }
        }
        </style>
        <a href="/" style="color: #38bdf8;"><- Dashboard</a>'''

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
                        <div class="lm-card-row" style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px;">
                            <div class="lm-card-main" style="flex: 1; min-width: 280px;">
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
                                    <div class="lm-price-row" style="display: flex; justify-content: space-between; font-size: 0.8rem; margin-bottom: 6px;">
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
                            <div class="lm-card-action" style="display: flex; flex-direction: column; align-items: center; gap: 8px; min-width: 120px;">
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
                        <div class="lm-card-row" style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px;">
                            <div class="lm-card-main" style="flex: 1; min-width: 280px;">
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
                            <div class="lm-card-action" style="display: flex; flex-direction: column; align-items: center; gap: 8px; min-width: 120px;">'''

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
def market_page(session_token: Optional[str] = Cookie(None), item: str = "apple_seeds", order_err: str = ""):
    return _market_page_impl(session_token, item, order_err)

def _market_page_impl(session_token: Optional[str] = None, item: str = "apple_seeds", order_err: str = ""):
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
            all_my_orders = mkt_db.query(MarketOrder).filter(
                MarketOrder.player_id == player.id,
                MarketOrder.status.in_([OrderStatus.ACTIVE, OrderStatus.PARTIALLY_FILLED])
            ).order_by(MarketOrder.item_type.asc(), MarketOrder.created_at.desc()).all()
            _active_rows = mkt_db.query(MarketOrder.item_type).filter(
                MarketOrder.status.in_([OrderStatus.ACTIVE, OrderStatus.PARTIALLY_FILLED])
            ).distinct().all()
            active_items = sorted({r[0] for r in _active_rows if not r[0].endswith("_shares")})
        finally:
            mkt_db.close()
        
        # Map JSON category → one of the 11 filter groups (mirrors inventory page)
        _mkt_json_to_filter = {
            "crops": "agriculture", "seeds": "agriculture", "produce": "agriculture",
            "livestock": "livestock", "seafood": "livestock", "shellfish": "livestock",
            "animals": "livestock", "zoo_supplies": "livestock",
            "dairy": "food_bev", "meat": "food_bev", "seafood_product": "food_bev",
            "prepared_food": "food_bev", "baked_goods": "food_bev", "confectionery": "food_bev",
            "food": "food_bev", "canned_goods": "food_bev", "condiments": "food_bev",
            "sweeteners": "food_bev", "beverages": "food_bev", "alcohol": "food_bev",
            "ingredients": "food_bev", "fast_food": "food_bev", "retail_food": "food_bev",
            "food_service": "food_bev",
            "industrial": "industrial", "components": "industrial", "metals": "industrial",
            "ore": "industrial", "packaging": "industrial", "fuel": "industrial",
            "energy": "industrial", "liquids": "industrial", "electronics": "industrial",
            "utilities": "industrial", "logistics": "industrial", "lab_equipment": "industrial",
            "robotics": "industrial", "medical_equipment": "industrial",
            "minerals": "industrial", "chemicals": "industrial", "aerospace": "industrial",
            "construction": "construction", "materials": "construction",
            "prison_infrastructure": "construction", "zoo_infrastructure": "construction",
            "wood": "luxury",
            "vehicle": "vehicles", "vehicles": "vehicles", "vehicle_parts": "vehicles",
            "auto_parts": "vehicles", "marine_parts": "vehicles",
            "apparel": "consumer", "textiles": "consumer", "accessories": "consumer",
            "home_goods": "consumer", "health": "consumer", "media": "consumer",
            "tobacco": "consumer", "cured_tobacco": "consumer", "personal_care": "consumer",
            "essential_oils": "consumer", "appliances": "consumer", "pharmaceuticals": "consumer",
            "medical_supplies": "consumer", "education": "consumer", "prison": "consumer",
            "retail_shopping": "consumer", "entertainment": "consumer",
            "military": "weaponry", "retail_military": "weaponry", "intelligence": "weaponry",
            "luxury": "luxury",
            "services": "services", "retail_service": "services", "retail_transport": "services",
            "retail_medical": "services", "retail_education": "services",
            "retail_entertainment": "services", "retail_zoo": "services",
            "retail_prison": "services", "hospitality": "services",
            "financial": "finance",
        }
        # Ordered display metadata for the 11 filter groups
        _filter_meta = [
            ("agriculture",  "#22c55e", "🌾 Agriculture"),
            ("livestock",    "#f59e0b", "🐄 Livestock"),
            ("food_bev",     "#f97316", "🍽️ Food & Bev"),
            ("industrial",   "#64748b", "🏭 Industrial"),
            ("construction", "#8b5cf6", "🏗️ Construction"),
            ("vehicles",     "#60a5fa", "🚗 Vehicles & Parts"),
            ("consumer",     "#ec4899", "🛍️ Consumer Goods"),
            ("weaponry",     "#dc2626", "⚔️ Weaponry"),
            ("luxury",       "#d97706", "💎 Luxury"),
            ("services",     "#a78bfa", "🤝 Services"),
            ("finance",      "#6366f1", "📊 Finance"),
        ]

        # Group items by the 11 filter categories
        categories = {}
        for i in items:
            info = inv_mod.get_item_info(i)
            json_cat = info.get("category", "other") if info else "other"
            filter_cat = _mkt_json_to_filter.get(json_cat, "consumer")
            if filter_cat not in categories:
                categories[filter_cat] = []
            categories[filter_cat].append(i)

        # Per-item color lookup (granular JSON category → color, for item pills if needed)
        cat_colors = {
            "seeds": "#22c55e", "crops": "#22c55e", "produce": "#84cc16",
            "livestock": "#f59e0b", "animals": "#f59e0b",
            "seafood": "#06b6d4", "shellfish": "#06b6d4", "zoo_supplies": "#f59e0b",
            "food": "#f97316", "baked_goods": "#fb923c", "confectionery": "#fb923c",
            "prepared_food": "#f97316", "canned_goods": "#f97316",
            "condiments": "#fbbf24", "sweeteners": "#fbbf24",
            "meat": "#ef4444", "seafood_product": "#06b6d4",
            "dairy": "#cbd5e1", "beverages": "#38bdf8", "beverage": "#38bdf8",
            "alcohol": "#a855f7", "ingredients": "#fbbf24", "food_service": "#f97316",
            "industrial": "#64748b", "energy": "#eab308", "fuel": "#dc2626",
            "liquids": "#06b6d4", "electronics": "#38bdf8", "components": "#6366f1",
            "metals": "#94a3b8", "ore": "#78716c", "packaging": "#64748b",
            "utilities": "#0891b2", "logistics": "#60a5fa", "lab_equipment": "#64748b",
            "robotics": "#6366f1", "medical_equipment": "#10b981",
            "minerals": "#a8a29e", "chemicals": "#ec4899", "aerospace": "#06b6d4",
            "materials": "#94a3b8", "construction": "#8b5cf6",
            "prison_infrastructure": "#78716c", "zoo_infrastructure": "#f59e0b",
            "wood": "#a16207",
            "vehicle": "#60a5fa", "vehicles": "#60a5fa",
            "vehicle_parts": "#60a5fa", "auto_parts": "#3b82f6", "marine_parts": "#0ea5e9",
            "apparel": "#ec4899", "textiles": "#c084fc", "accessories": "#e879f9",
            "home_goods": "#14b8a6", "appliances": "#14b8a6",
            "health": "#22c55e", "personal_care": "#f472b6", "essential_oils": "#a78bfa",
            "pharmaceuticals": "#22c55e", "medical_supplies": "#22c55e",
            "tobacco": "#a78bfa", "cured_tobacco": "#a78bfa",
            "media": "#facc15", "education": "#38bdf8", "prison": "#64748b",
            "entertainment": "#8b5cf6",
            "military": "#dc2626", "retail_military": "#dc2626", "intelligence": "#ef4444",
            "luxury": "#d4af37",
            "services": "#a78bfa", "hospitality": "#a78bfa",
            "retail_service": "#a78bfa", "retail_food": "#f97316",
            "retail_shopping": "#ec4899", "retail_entertainment": "#8b5cf6",
            "retail_medical": "#22c55e", "retail_education": "#38bdf8",
            "retail_transport": "#60a5fa", "retail_zoo": "#f59e0b",
            "retail_prison": "#64748b",
            "financial": "#10b981",
            "other": "#94a3b8",
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
        
        # Build category tabs — ordered by the 11-category scheme
        # Determine which filter category the current item belongs to (for auto-expand)
        _cur_item_info = inv_mod.get_item_info(item)
        _cur_json_cat = _cur_item_info.get("category", "other") if _cur_item_info else "other"
        _cur_filter_cat = _mkt_json_to_filter.get(_cur_json_cat, "consumer")

        filter_tabs = '<div id="itemTabs" style="margin-bottom: 20px; max-width: 100%;">'
        for filter_cat, cat_color, cat_label in _filter_meta:
            cat_items = categories.get(filter_cat)
            if not cat_items:
                continue
            is_open = filter_cat == _cur_filter_cat
            section_id = f"mkt-sec-{filter_cat}"
            chevron_open = "▾" if is_open else "▸"
            items_display = "flex" if is_open else "none"
            filter_tabs += f'''
            <div style="margin-bottom: 8px;">
                <div onclick="mktToggle('{section_id}', this)"
                     style="color: {cat_color}; font-size: 0.75rem; font-weight: bold;
                            margin-bottom: 4px; cursor: pointer; user-select: none;
                            display: flex; align-items: center; gap: 5px;">
                    <span class="mkt-chevron">{chevron_open}</span>{cat_label}
                </div>
                <div id="{section_id}" style="display: {items_display}; flex-wrap: wrap; gap: 6px; padding-left: 4px;">
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
        filter_tabs += '''</div>
        <script>
        function mktToggle(sectionId, header) {
            var sec = document.getElementById(sectionId);
            var chevron = header.querySelector(".mkt-chevron");
            var open = sec.style.display === "none" || sec.style.display === "";
            sec.style.display = open ? "flex" : "none";
            if (chevron) chevron.textContent = open ? "▾" : "▸";
        }
        </script>'''
        
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
        player_item_qty = inv_mod.get_item_quantity(player.id, item)
        
        # Adaptive price formatter: shows enough decimals for small prices
        def _fmt_price(price, d):
            if price is None:
                return "MKT"
            abs_p = abs(price)
            if abs_p == 0:
                prec = 2
            elif abs_p < 0.0001:
                prec = 8
            elif abs_p < 0.01:
                prec = 6
            elif abs_p < 1:
                prec = 4
            else:
                prec = 2
            return fmt_usd(price, d, precision=prec)

        # Build "All My Open Orders" panel (across all items)
        all_orders_html = ""
        if all_my_orders:
            all_rows = ""
            for o in all_my_orders:
                side_color = "#22c55e" if o.order_type == "buy" else "#ef4444"
                rem = o.quantity - o.quantity_filled
                price_str = _fmt_price(o.price, disp)
                item_label = o.item_type.replace("_", " ").title()
                all_rows += f'''<tr style="border-bottom:1px solid #1e293b;">
                    <td style="padding:6px 8px;"><a href="/market?item={o.item_type}" style="color:#38bdf8;text-decoration:none;">{item_label}</a></td>
                    <td style="padding:6px 8px;color:{side_color};font-weight:bold;">{o.order_type.upper()}</td>
                    <td style="padding:6px 8px;">{price_str}</td>
                    <td style="padding:6px 8px;">{o.quantity:,.2f}</td>
                    <td style="padding:6px 8px;color:#f59e0b;">{rem:,.2f}</td>
                    <td style="padding:6px 8px;">
                        <form action="/api/market/cancel-order" method="post" style="display:inline;">
                            <input type="hidden" name="order_id" value="{o.id}">
                            <input type="hidden" name="item_type" value="{o.item_type}">
                            <button type="submit" style="background:#7f1d1d;color:#fca5a5;border:none;padding:2px 8px;border-radius:3px;cursor:pointer;font-size:0.75rem;">Cancel</button>
                        </form>
                    </td>
                </tr>'''
            all_orders_html = f'''<div class="card" style="margin-bottom:20px;">
                <h3 style="margin-top:0;">All My Open Orders ({len(all_my_orders)})</h3>
                <div style="overflow-x:auto;">
                <table style="width:100%;border-collapse:collapse;font-size:0.85rem;">
                    <thead><tr style="border-bottom:1px solid #334155;color:#64748b;text-align:left;">
                        <th style="padding:6px 8px;">Item</th>
                        <th style="padding:6px 8px;">Side</th>
                        <th style="padding:6px 8px;">Price</th>
                        <th style="padding:6px 8px;">Qty</th>
                        <th style="padding:6px 8px;">Remaining</th>
                        <th style="padding:6px 8px;">Action</th>
                    </tr></thead>
                    <tbody>{all_rows}</tbody>
                </table>
                </div>
            </div>'''

        # Build market HTML
        market_html = f'''
        <style>
        @media (max-width: 640px) {{
            .mkt-main-flex {{ flex-direction: column !important; }}
            .mkt-sidebar {{ max-width: 100% !important; flex: none !important; }}
            .mkt-order-form {{ grid-template-columns: 1fr !important; }}
            .mkt-order-book-grid {{ grid-template-columns: 1fr !important; }}
            .mkt-order-book-row {{ grid-template-columns: 1fr 1fr !important; }}
            .mkt-order-book-hdr {{ grid-template-columns: 1fr 1fr !important; }}
            .mkt-orders-wrap {{ overflow-x: auto !important; }}
        }}
        </style>
        <a href="/" style="color: #38bdf8;"><- Dashboard</a>
        {all_orders_html}
        <div class="mkt-main-flex" style="display: flex; gap: 20px; max-width: 100%;">
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
                    {f'<div style="background:#2d0a0a;border:1px solid #ef4444;border-radius:4px;padding:10px 14px;color:#fca5a5;font-size:0.85rem;margin-bottom:12px;">⚠ {order_err}</div>' if order_err else ''}
                    <div style="font-size:0.8rem;color:#64748b;margin-bottom:10px;">
                        You hold: <strong style="color:{'#22c55e' if player_item_qty > 0 else '#64748b'};">{player_item_qty:,.4g} {item_name}</strong>
                    </div>
                    <form action="/api/market/order" method="post" class="mkt-order-form" style="display: grid; grid-template-columns: 1fr 1fr 1fr auto; gap: 10px;">
                        <input type="hidden" name="item_type" value="{item}">
                        <select name="order_type">
                            <option value="sell">SELL</option>
                            <option value="buy">BUY</option>
                        </select>
                        <input type="number" name="quantity" placeholder="Quantity" required>
                        <input type="number" name="price" step="0.0001" placeholder="Price ({disp['code']})" required>
                        <button type="submit" class="btn-blue">Submit</button>
                    </form>
                </div>
                
                <!-- Order Book Grid -->
                <div class="mkt-order-book-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">

                    <!-- BIDS -->
                    <div class="card">
                        <h3 style="color: #22c55e;">Bids (Buy Orders)</h3>
                        <div class="mkt-order-book-hdr" style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; margin-bottom: 8px; padding-bottom: 8px; border-bottom: 1px solid #1e293b; font-size: 0.85rem; color: #64748b;">
                            <span>Price</span>
                            <span>Qty</span>
                            <span>Trader</span>
                        </div>'''
        
        if order_book and order_book.get('bids'):
            for price, qty, order_id, player_name, player_id in order_book['bids'][:10]:
                p_flag = player_flags.get(player_id, "🌐")
                market_html += f'''
                        <div class="mkt-order-book-row" style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; font-size: 0.9rem; padding: 4px 0; color: #22c55e;">
                            <span>{_fmt_price(price, disp)}</span>
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
                        <div class="mkt-order-book-hdr" style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; margin-bottom: 8px; padding-bottom: 8px; border-bottom: 1px solid #1e293b; font-size: 0.85rem; color: #64748b;">
                            <span>Price</span>
                            <span>Qty</span>
                            <span>Trader</span>
                        </div>'''

        if order_book and order_book.get('asks'):
            for price, qty, order_id, player_name, player_id in order_book['asks'][:10]:
                p_flag = player_flags.get(player_id, "🌐")
                market_html += f'''
                        <div class="mkt-order-book-row" style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; font-size: 0.9rem; padding: 4px 0; color: #ef4444;">
                            <span>{_fmt_price(price, disp)}</span>
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
                    <td style="padding: 8px 6px;">{_fmt_price(o.price, disp)}</td>
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
                <div class="mkt-orders-wrap" style="overflow-x: auto;">
                <table style="width:100%;border-collapse:collapse;min-width:420px;">
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
                </div>
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
            <div class="mkt-sidebar" style="flex: 1; min-width: 0; max-width: 280px;">
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
            CompanyShares, ShareholderPosition, CompanyEarningsReport,
            get_db as get_firm_db, SHARE_CLASS_DESCRIPTIONS,
        )
        from auth import Player, get_db as get_auth_db
        from business import Business, BUSINESS_TYPES
        from land import get_db as get_land_db

        db = get_firm_db()
        auth_db = get_auth_db()
        land_db = get_land_db()

        _SECTOR_COLORS = {
            "Technology": "#38bdf8", "Energy": "#f59e0b", "Mining": "#a78bfa",
            "Agriculture": "#4ade80", "Food & Beverage": "#fb923c",
            "Manufacturing": "#94a3b8", "Healthcare": "#f472b6",
            "Retail & Commerce": "#fbbf24", "Finance": "#22d3ee",
            "Construction": "#d97706", "Transport": "#60a5fa",
            "Real Estate": "#c084fc", "Media & Services": "#34d399",
        }

        try:
            companies = db.query(CompanyShares).filter(
                CompanyShares.is_delisted == False,
                CompanyShares.share_class_label == "main",
            ).order_by(CompanyShares.ticker_symbol).all()

            company_data = []
            for company in companies:
                founder = auth_db.query(Player).filter(Player.id == company.founder_id).first()
                founder_name = founder.business_name if founder else f"Player {company.founder_id}"

                business = land_db.query(Business).filter(Business.id == company.business_id).first()
                business_type = BUSINESS_TYPES.get(business.business_type, {}).get("name", "Unknown") if business else "Unknown"

                shareholder_count = db.query(ShareholderPosition).filter(
                    ShareholderPosition.company_shares_id == company.id,
                    ShareholderPosition.shares_owned > 0,
                    ShareholderPosition.player_id != company.founder_id,
                ).count()

                market_cap = company.current_price * company.shares_outstanding

                if company.ipo_price > 0:
                    price_change = ((company.current_price - company.ipo_price) / company.ipo_price) * 100
                else:
                    price_change = 0

                # Annualised dividend yield
                div_yield = 0.0
                div_text = "No dividends"
                if company.dividend_config and company.current_price > 0:
                    freq_mult = {"daily": 365, "weekly": 52, "biweekly": 26, "monthly": 12, "quarterly": 4}
                    annual = 0.0
                    for dc in company.dividend_config:
                        if dc.get("type") == "cash":
                            mult = freq_mult.get(dc.get("frequency", "quarterly"), 4)
                            annual += dc.get("amount", 0.0) * mult
                    if annual > 0:
                        div_yield = (annual / company.current_price) * 100
                        div_text = f"{div_yield:.2f}% yield/yr"
                    else:
                        first_dc = company.dividend_config[0]
                        if first_dc.get("type") == "commodity":
                            div_text = f"{first_dc.get('item', 'item')}/share"
                        elif first_dc.get("type") == "scrip":
                            div_text = f"Stock {first_dc.get('ratio', 0)*100:.1f}%"

                # Latest earnings
                latest_report = db.query(CompanyEarningsReport).filter(
                    CompanyEarningsReport.company_shares_id == company.id,
                ).order_by(CompanyEarningsReport.period_end.desc()).first()

                # Player's position
                my_pos = db.query(ShareholderPosition).filter(
                    ShareholderPosition.company_shares_id == company.id,
                    ShareholderPosition.player_id == player.id,
                ).first()

                company_data.append({
                    "company": company,
                    "founder_name": founder_name,
                    "business_type": business_type,
                    "shareholder_count": shareholder_count,
                    "market_cap": market_cap,
                    "price_change": price_change,
                    "div_yield": div_yield,
                    "div_text": div_text,
                    "latest_report": latest_report,
                    "my_shares": my_pos.shares_owned if my_pos else 0,
                })

        finally:
            db.close()
            auth_db.close()
            land_db.close()

        companies_html = ""
        if company_data:
            for item in company_data:
                company = item["company"]
                change_color = "#22c55e" if item["price_change"] >= 0 else "#ef4444"
                change_arrow = "▲" if item["price_change"] >= 0 else "▼"

                sector = company.sector or "General"
                sector_color = _SECTOR_COLORS.get(sector, "#64748b")
                sc_desc = SHARE_CLASS_DESCRIPTIONS.get(company.share_class, company.share_class)

                badges = f'<span style="background:{sector_color}22;color:{sector_color};border:1px solid {sector_color}44;border-radius:4px;padding:1px 7px;font-size:0.72rem;margin-left:6px;">{sector}</span>'
                if company.is_tbtf:
                    badges += '<span class="badge" style="background:#22c55e;margin-left:5px;">🛡️ TBTF</span>'
                if company.trading_halted_until and datetime.utcnow() < company.trading_halted_until:
                    badges += '<span class="badge" style="background:#ef4444;margin-left:5px;">🛑 HALTED</span>'
                if company.stabilization_active:
                    badges += '<span class="badge" style="background:#8b5cf6;margin-left:5px;">📊 STAB</span>'
                if company.dividend_warning_active:
                    badges += '<span class="badge" style="background:#f59e0b;margin-left:5px;">⚠ DIV WARN</span>'
                # Lockup badge (founder only)
                if company.founder_id == player.id and company.lockup_expires_at and datetime.utcnow() < company.lockup_expires_at:
                    ld = (company.lockup_expires_at - datetime.utcnow()).days + 1
                    badges += f'<span class="badge" style="background:#0f172a;border:1px solid #f59e0b;color:#f59e0b;margin-left:5px;">🔒 LOCKUP {ld}d</span>'

                my_shares_html = ""
                if item["my_shares"] > 0:
                    my_val = item["my_shares"] * company.current_price
                    my_shares_html = f'<div style="color:#22c55e;font-size:0.8rem;margin-top:4px;">✓ You hold {item["my_shares"]:,} shares (≈{fmt_usd(my_val, disp, precision=0)})</div>'

                eps_html = ""
                rpt = item["latest_report"]
                if rpt:
                    eps_html = f'<div style="color:#64748b;font-size:0.78rem;">7d Rev: {fmt_usd(rpt.total_revenue, disp, precision=0)} · EPS: {fmt_usd(rpt.eps, disp, precision=4)}</div>'

                companies_html += f'''
                <div class="card" style="border-left:3px solid {sector_color};">
                    <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px;">
                        <div style="flex:1;min-width:0;">
                            <h3 style="margin:0;display:flex;align-items:center;flex-wrap:wrap;gap:4px;">
                                <a href="/brokerage/company/{company.ticker_symbol}" style="color:#f1f5f9;text-decoration:none;">{company.ticker_symbol}</a>
                                <span style="color:#94a3b8;font-weight:normal;"> — {company.company_name}</span>
                                {badges}
                            </h3>
                            <p style="color:#64748b;margin:5px 0;font-size:0.85rem;">
                                {item["business_type"]} · <span style="color:#94a3b8;">Founded by {item["founder_name"]}</span>
                            </p>
                            <p style="margin:2px 0;font-size:0.8rem;">
                                <span style="color:#94a3b8;" title="{sc_desc}">📋 {company.share_class.replace("_"," ").title()}</span>
                                &nbsp;·&nbsp;
                                <span style="color:{"#22c55e" if item["div_yield"] > 0 else "#64748b"};">💰 {item["div_text"]}</span>
                            </p>
                            {my_shares_html}
                            {eps_html}
                        </div>
                        <div style="text-align:right;white-space:nowrap;">
                            <div style="font-size:1.7rem;font-weight:bold;color:#38bdf8;">{fmt_usd(company.current_price, disp, precision=4)}</div>
                            <div style="color:{change_color};font-size:0.9rem;">{change_arrow} {abs(item["price_change"]):.1f}% from IPO</div>
                            <div style="color:#475569;font-size:0.78rem;">MCap {fmt_usd(item["market_cap"], disp, precision=0)}</div>
                        </div>
                    </div>

                    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:12px;">
                        <div>
                            <div style="color:#64748b;font-size:0.75rem;">Float</div>
                            <div>{company.shares_in_float:,}</div>
                        </div>
                        <div>
                            <div style="color:#64748b;font-size:0.75rem;">Investors</div>
                            <div>{item["shareholder_count"]}</div>
                        </div>
                        <div>
                            <div style="color:#64748b;font-size:0.75rem;">Div Streak</div>
                            <div>{"🔥 " if company.consecutive_dividend_payouts >= 3 else ""}{company.consecutive_dividend_payouts}</div>
                        </div>
                        <div>
                            <div style="color:#64748b;font-size:0.75rem;">52w Range</div>
                            <div style="font-size:0.85rem;">{fmt_usd(company.low_52_week, disp, precision=2)} – {fmt_usd(company.high_52_week, disp, precision=2)}</div>
                        </div>
                    </div>

                    <div style="margin-top:12px;display:flex;gap:8px;flex-wrap:wrap;">
                        <a href="/brokerage/company/{company.ticker_symbol}" class="btn-blue" style="padding:5px 12px;font-size:0.85rem;">📊 Details</a>
                        <a href="/brokerage/trading?ticker={company.ticker_symbol}" class="btn-blue" style="padding:5px 12px;font-size:0.85rem;">Trade</a>
                        <a href="/brokerage/shorts?ticker={company.ticker_symbol}" class="btn-orange" style="padding:5px 12px;font-size:0.85rem;">Short</a>
                    </div>
                </div>
                '''
        else:
            companies_html = '''
            <div class="card">
                <h3>No Companies Listed</h3>
                <p style="color:#64748b;">Be the first to take your business public!</p>
                <a href="/brokerage/ipo" class="btn-blue">Launch an IPO</a>
            </div>
            '''

        body = f'''
        <a href="/banks/brokerage-firm" style="color:#38bdf8;">← Brokerage Firm</a>
        <h1>WPE Listed Companies</h1>
        <p style="color:#64748b;">{len(company_data)} companies · Wadsworth Player Exchange</p>
        {companies_html}
        '''

        return shell("WPE Companies", body, player.cash_balance, player.id)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return shell("WPE Companies", f"Error: {e}", player.cash_balance, player.id)


# ==========================
# COMPANY DETAIL PAGE
# ==========================

@router.get("/brokerage/company/{ticker}", response_class=HTMLResponse)
def brokerage_company_detail(ticker: str, session_token: Optional[str] = Cookie(None)):
    """Detailed view for a single listed company."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)

    try:
        from banks.brokerage_firm import (
            CompanyShares, ShareholderPosition, CompanyEarningsReport,
            CompanyProposal, PriceHistory, get_db as get_firm_db,
            SHARE_CLASS_DESCRIPTIONS,
        )
        from auth import Player, get_db as get_auth_db

        db = get_firm_db()
        auth_db = get_auth_db()
        try:
            company = db.query(CompanyShares).filter(
                CompanyShares.ticker_symbol == ticker.upper(),
                CompanyShares.is_delisted == False,
            ).first()
            if not company:
                return shell("Company Not Found", f'<p>No listed company with ticker <b>{ticker.upper()}</b>.</p><a href="/brokerage/companies" style="color:#38bdf8;">← Back</a>', player.cash_balance, player.id)

            founder = auth_db.query(Player).filter(Player.id == company.founder_id).first()
            founder_name = founder.business_name if founder else f"Player {company.founder_id}"

            # Price history (last 14 data points)
            cutoff = datetime.utcnow() - timedelta(days=14)
            price_history = db.query(PriceHistory).filter(
                PriceHistory.company_shares_id == company.id,
                PriceHistory.recorded_at >= cutoff,
            ).order_by(PriceHistory.recorded_at.asc()).all()

            # Sparkline from price history
            spark_html = ""
            if price_history:
                prices = [p.price for p in price_history]
                mn, mx = min(prices), max(prices)
                rng = mx - mn if mx != mn else 1
                W, H = 260, 40
                pts = []
                for i, p in enumerate(prices):
                    x = int(i / max(len(prices) - 1, 1) * W)
                    y = int(H - (p - mn) / rng * H)
                    pts.append(f"{x},{y}")
                clr = "#22c55e" if prices[-1] >= prices[0] else "#ef4444"
                spark_html = f'<svg width="{W}" height="{H}" style="margin:8px 0;"><polyline points="{" ".join(pts)}" fill="none" stroke="{clr}" stroke-width="1.5"/></svg>'

            # Earnings reports (last 4)
            reports = db.query(CompanyEarningsReport).filter(
                CompanyEarningsReport.company_shares_id == company.id,
            ).order_by(CompanyEarningsReport.period_end.desc()).limit(4).all()

            # Top shareholders
            top_holders = db.query(ShareholderPosition).filter(
                ShareholderPosition.company_shares_id == company.id,
                ShareholderPosition.shares_owned > 0,
            ).order_by(ShareholderPosition.shares_owned.desc()).limit(10).all()

            # Player's own position + loyalty (may not be in top 10)
            my_pos = next((p for p in top_holders if p.player_id == player.id), None)
            if my_pos is None:
                my_pos = db.query(ShareholderPosition).filter(
                    ShareholderPosition.company_shares_id == company.id,
                    ShareholderPosition.player_id == player.id,
                    ShareholderPosition.shares_owned > 0,
                ).first()
            my_loyalty_label = "New holder"
            if my_pos:
                from banks.brokerage_firm import get_loyalty_tier
                _, my_loyalty_label = get_loyalty_tier(my_pos.first_held_at)

            # Open proposals
            open_proposals = db.query(CompanyProposal).filter(
                CompanyProposal.company_shares_id == company.id,
                CompanyProposal.status == "open",
            ).order_by(CompanyProposal.created_at.desc()).limit(5).all()

            # Sub-records (Quad-Class C/D)
            sub_records = db.query(CompanyShares).filter(
                CompanyShares.parent_company_id == company.id,
                CompanyShares.is_delisted == False,
            ).all()

        finally:
            db.close()
            auth_db.close()

        sc_desc = SHARE_CLASS_DESCRIPTIONS.get(company.share_class, company.share_class)
        sector = company.sector or "General"

        # Annualised yield
        div_yield = 0.0
        div_details_html = "<em style='color:#64748b;'>No dividend configured.</em>"
        if company.dividend_config and company.current_price > 0:
            freq_mult = {"daily": 365, "weekly": 52, "biweekly": 26, "monthly": 12, "quarterly": 4}
            rows = []
            for dc in company.dividend_config:
                dtype = dc.get("type", "cash")
                freq = dc.get("frequency", "quarterly")
                if dtype == "cash":
                    mult = freq_mult.get(freq, 4)
                    ann = dc.get("amount", 0.0) * mult
                    div_yield += (ann / company.current_price) * 100
                    req = "Required" if dc.get("required") else "Discretionary"
                    rows.append(f'<tr><td>Cash</td><td>{dc.get("amount", 0):.4f}/share</td><td>{freq.title()}</td><td>{ann/company.current_price*100:.2f}% p.a.</td><td>{req}</td></tr>')
                elif dtype == "commodity":
                    rows.append(f'<tr><td>Commodity</td><td>{dc.get("amount", 1)} {dc.get("item", "item")} per {dc.get("per_shares", 100)} shares</td><td>{freq.title()}</td><td>—</td><td>Discretionary</td></tr>')
                elif dtype == "scrip":
                    rows.append(f'<tr><td>Stock</td><td>{dc.get("ratio", 0)*100:.2f}% new shares</td><td>{freq.title()}</td><td>—</td><td>Discretionary</td></tr>')
            if rows:
                div_details_html = '<table style="width:100%;border-collapse:collapse;font-size:0.85rem;"><tr style="color:#64748b;"><th align="left">Type</th><th align="left">Amount</th><th align="left">Frequency</th><th align="left">Yield</th><th align="left">Status</th></tr>' + "".join(rows) + "</table>"

        # Earnings table
        earnings_html = "<em style='color:#64748b;'>No earnings reports yet.</em>"
        if reports:
            rows = []
            for r in reports:
                pct = r.payout_ratio * 100 if r.payout_ratio else 0
                rows.append(f'<tr><td>{r.period_end.strftime("%b %d")}</td><td>{fmt_usd(r.total_revenue, disp, precision=0)}</td><td>{fmt_usd(r.eps, disp, precision=4)}</td><td>{pct:.1f}%</td></tr>')
            earnings_html = '<table style="width:100%;border-collapse:collapse;font-size:0.85rem;"><tr style="color:#64748b;"><th align="left">Period</th><th align="left">Revenue</th><th align="left">EPS</th><th align="left">Payout</th></tr>' + "".join(rows) + "</table>"

        # Shareholders table
        holder_rows = []
        for pos in top_holders:
            pct = pos.shares_owned / max(company.shares_outstanding, 1) * 100
            role = "Founder" if pos.player_id == company.founder_id else ("You" if pos.player_id == player.id else "Investor")
            holder_rows.append(f'<tr><td>Player {pos.player_id}</td><td>{pos.shares_owned:,}</td><td>{pct:.1f}%</td><td style="color:#94a3b8;">{role}</td></tr>')
        holders_html = '<table style="width:100%;border-collapse:collapse;font-size:0.85rem;"><tr style="color:#64748b;"><th align="left">Holder</th><th align="left">Shares</th><th align="left">%</th><th align="left">Role</th></tr>' + "".join(holder_rows) + "</table>" if holder_rows else "<em style='color:#64748b;'>No shareholders.</em>"

        # Proposals
        prop_html = ""
        for prop in open_proposals:
            ends_in = max(0, (prop.voting_ends_at - datetime.utcnow()).seconds // 3600)
            total_v = (prop.yes_votes or 0) + (prop.no_votes or 0)
            yes_pct = prop.yes_votes / total_v * 100 if total_v > 0 else 0
            prop_html += f'''
            <div style="background:#0f172a;border-radius:6px;padding:12px;margin-bottom:8px;">
                <strong>{prop.title}</strong> <span style="color:#64748b;font-size:0.8rem;">[{prop.proposal_type}]</span>
                <div style="color:#94a3b8;font-size:0.85rem;margin:4px 0;">{prop.description}</div>
                <div style="display:flex;gap:16px;font-size:0.8rem;margin-top:6px;">
                    <span style="color:#22c55e;">✓ {prop.yes_votes:.0f} ({yes_pct:.0f}%)</span>
                    <span style="color:#ef4444;">✗ {prop.no_votes:.0f}</span>
                    <span style="color:#64748b;">Closes in ~{ends_in}h</span>
                </div>
            </div>'''
        if not prop_html:
            prop_html = "<em style='color:#64748b;'>No open proposals.</em>"

        # Lockup notice
        lockup_html = ""
        if company.founder_id == player.id and company.lockup_expires_at and datetime.utcnow() < company.lockup_expires_at:
            ld = (company.lockup_expires_at - datetime.utcnow()).days + 1
            lockup_html = f'<div style="background:#1c1917;border:1px solid #f59e0b;border-radius:6px;padding:10px;margin-bottom:12px;color:#f59e0b;">🔒 Founder lockup active — you cannot sell shares for {ld} more day(s) ({company.lockup_expires_at.strftime("%b %d, %Y")})</div>'

        # My position card
        my_pos_html = ""
        if my_pos:
            my_val = my_pos.shares_owned * company.current_price
            pnl = (company.current_price - my_pos.average_cost_basis) * my_pos.shares_owned if my_pos.average_cost_basis else 0
            pnl_clr = "#22c55e" if pnl >= 0 else "#ef4444"
            my_pos_html = f'''
            <div class="card" style="background:#0f2d0f;border:1px solid #22c55e;">
                <h4 style="margin:0 0 8px;color:#22c55e;">Your Position</h4>
                <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;font-size:0.9rem;">
                    <div><div style="color:#64748b;font-size:0.75rem;">Shares</div>{my_pos.shares_owned:,}</div>
                    <div><div style="color:#64748b;font-size:0.75rem;">Market Value</div>{fmt_usd(my_val, disp, precision=2)}</div>
                    <div><div style="color:#64748b;font-size:0.75rem;">Unrealised P&L</div><span style="color:{pnl_clr};">{fmt_usd(pnl, disp, precision=2)}</span></div>
                    <div><div style="color:#64748b;font-size:0.75rem;">Avg Cost</div>{fmt_usd(my_pos.average_cost_basis or 0, disp, precision=4)}</div>
                    <div><div style="color:#64748b;font-size:0.75rem;">Loyalty Tier</div>{my_loyalty_label}</div>
                    <div><div style="color:#64748b;font-size:0.75rem;">Lendable</div>{my_pos.shares_available_to_lend:,}</div>
                </div>
            </div>'''

        # Sub-class records
        sub_html = ""
        for sr in sub_records:
            sub_html += f'<div style="background:#1e293b;border-radius:6px;padding:8px 12px;margin-bottom:6px;display:flex;justify-content:space-between;"><span style="color:#94a3b8;">{sr.ticker_symbol} — {sr.share_class.replace("_"," ").title()}</span><span style="color:#38bdf8;">{fmt_usd(sr.current_price, disp, precision=4)}</span></div>'

        price_change = ((company.current_price - company.ipo_price) / company.ipo_price * 100) if company.ipo_price > 0 else 0
        change_color = "#22c55e" if price_change >= 0 else "#ef4444"

        body = f'''
        <a href="/brokerage/companies" style="color:#38bdf8;">← All Companies</a>
        <div style="margin-top:16px;display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px;">
            <div>
                <h1 style="margin:0;">{company.ticker_symbol} <span style="color:#64748b;font-weight:normal;font-size:1.2rem;">— {company.company_name}</span></h1>
                <div style="color:#94a3b8;margin-top:4px;">Sector: <strong style="color:#e2e8f0;">{sector}</strong> &nbsp;·&nbsp; Founded by <strong>{founder_name}</strong></div>
            </div>
            <div style="text-align:right;">
                <div style="font-size:2.2rem;font-weight:bold;color:#38bdf8;">{fmt_usd(company.current_price, disp, precision=4)}</div>
                <div style="color:{change_color};">{"▲" if price_change >= 0 else "▼"} {abs(price_change):.1f}% from IPO (${company.ipo_price:.4f})</div>
            </div>
        </div>

        {spark_html}
        {lockup_html}
        {my_pos_html}

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:16px;">
            <div class="card">
                <h4 style="margin:0 0 8px;">Share Class</h4>
                <div style="font-size:1.1rem;color:#e2e8f0;">{company.share_class.replace("_"," ").title()}</div>
                <div style="color:#64748b;font-size:0.85rem;margin-top:4px;">{sc_desc}</div>
                {"<div style='margin-top:6px;font-size:0.85rem;color:#f59e0b;'>📞 Callable</div>" if company.is_callable else ""}
                {"<div style='margin-top:6px;font-size:0.85rem;color:#a78bfa;'>🏛 Dual-Class structure</div>" if company.is_dual_class else ""}
                {sub_html}
            </div>
            <div class="card">
                <h4 style="margin:0 0 8px;">Dividend Yield</h4>
                {"<div style='font-size:1.5rem;font-weight:bold;color:#22c55e;'>" + f"{div_yield:.2f}%" + "</div><div style='color:#64748b;font-size:0.8rem;'>annualised</div>" if div_yield > 0 else "<div style='color:#64748b;'>No cash dividend</div>"}
                <div style="margin-top:8px;">{div_details_html}</div>
                {"<div style='margin-top:6px;font-size:0.8rem;color:#f59e0b;'>⚠ Dividend warning active</div>" if company.dividend_warning_active else f"<div style='margin-top:6px;font-size:0.8rem;color:#22c55e;'>🔥 Consecutive payouts: {company.consecutive_dividend_payouts}</div>"}
            </div>
        </div>

        <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin:16px 0;">
            <div class="card" style="padding:10px;">
                <div style="color:#64748b;font-size:0.72rem;">Market Cap</div>
                <div>{fmt_usd(company.current_price * company.shares_outstanding, disp, precision=0)}</div>
            </div>
            <div class="card" style="padding:10px;">
                <div style="color:#64748b;font-size:0.72rem;">Shares Out</div>
                <div>{company.shares_outstanding:,}</div>
            </div>
            <div class="card" style="padding:10px;">
                <div style="color:#64748b;font-size:0.72rem;">Float</div>
                <div>{company.shares_in_float:,}</div>
            </div>
            <div class="card" style="padding:10px;">
                <div style="color:#64748b;font-size:0.72rem;">52w High</div>
                <div style="color:#22c55e;">{fmt_usd(company.high_52_week, disp, precision=2)}</div>
            </div>
            <div class="card" style="padding:10px;">
                <div style="color:#64748b;font-size:0.72rem;">52w Low</div>
                <div style="color:#ef4444;">{fmt_usd(company.low_52_week, disp, precision=2)}</div>
            </div>
        </div>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">
            <div class="card">
                <h4 style="margin:0 0 8px;">Weekly Earnings</h4>
                {earnings_html}
                <div style="margin-top:8px;font-size:0.8rem;color:#64748b;">7d Revenue: {fmt_usd(company.revenue_7d or 0, disp, precision=0)} &nbsp;·&nbsp; 30d: {fmt_usd(company.revenue_30d or 0, disp, precision=0)}</div>
            </div>
            <div class="card">
                <h4 style="margin:0 0 8px;">Loyalty Tiers</h4>
                <table style="width:100%;font-size:0.82rem;border-collapse:collapse;">
                    <tr><td style="color:#f59e0b;">⭐⭐⭐ 90+ days</td><td style="color:#22c55e;">1.25× dividend</td></tr>
                    <tr><td style="color:#94a3b8;">⭐⭐ 30+ days</td><td style="color:#4ade80;">1.10× dividend</td></tr>
                    <tr><td style="color:#64748b;">⭐ 7+ days</td><td style="color:#94a3b8;">1.00× dividend</td></tr>
                </table>
                <div style="margin-top:8px;color:#64748b;font-size:0.78rem;">Hold longer to earn more from every dividend payout.</div>
            </div>
        </div>

        <div class="card" style="margin-top:16px;">
            <h4 style="margin:0 0 8px;">Top Shareholders</h4>
            {holders_html}
        </div>

        <div class="card" style="margin-top:16px;">
            <h4 style="margin:0 0 8px;">Governance Proposals</h4>
            {prop_html}
        </div>

        <div style="margin-top:16px;display:flex;gap:10px;flex-wrap:wrap;">
            <a href="/brokerage/trading?ticker={company.ticker_symbol}" class="btn-blue">Trade {company.ticker_symbol}</a>
            <a href="/brokerage/shorts?ticker={company.ticker_symbol}" class="btn-orange">Short Sell</a>
            {"<a href='/brokerage/my-companies' class='btn-blue' style='background:#334155;'>Manage My Company</a>" if company.founder_id == player.id else ""}
        </div>
        '''

        return shell(f"{company.ticker_symbol} — {company.company_name}", body, player.cash_balance, player.id)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return shell("Company Detail", f"Error: {e}", player.cash_balance, player.id)


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

                # Lockup notice
                lockup_notice = ""
                if company.lockup_expires_at and datetime.utcnow() < company.lockup_expires_at:
                    ld = (company.lockup_expires_at - datetime.utcnow()).days + 1
                    lockup_notice = f'<div style="background:#1c1917;border:1px solid #f59e0b;border-radius:5px;padding:8px 12px;margin-top:10px;color:#f59e0b;font-size:0.85rem;">🔒 Founder lockup: {ld} day(s) remaining — you cannot sell your shares until {company.lockup_expires_at.strftime("%b %d, %Y")}</div>'

                # Profit siphon form
                siphon_rate_pct = int((company.profit_siphon_rate or 0.0) * 100)
                siphon_form = f'''
                    <div style="margin-top:14px;padding-top:12px;border-top:1px solid #1e293b;">
                        <h4 style="margin:0 0 6px;">Profit Siphon (Escrow)</h4>
                        <p style="color:#64748b;font-size:0.82rem;margin:0 0 8px;">Automatically divert a % of your business revenue into dividend escrow, visible to investors.</p>
                        <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
                            <form action="/api/brokerage/set-siphon" method="post" style="display:flex;gap:8px;align-items:center;">
                                <input type="hidden" name="company_id" value="{company.id}">
                                <input type="number" name="rate_pct" value="{siphon_rate_pct}" min="0" max="10" step="1" style="width:60px;padding:5px;">
                                <span style="color:#94a3b8;font-size:0.9rem;">% of revenue</span>
                                <button type="submit" class="btn-blue" style="padding:5px 12px;">Set</button>
                            </form>
                            <span style="color:#94a3b8;font-size:0.82rem;">Escrow balance: <strong style="color:#22c55e;">{fmt_usd(company.dividend_escrow_balance or 0, disp, precision=2)}</strong></span>
                        </div>
                    </div>'''

                listing_fee_note = ""
                if company.listing_fee_next_due:
                    listing_fee_note = f'<div style="color:#64748b;font-size:0.78rem;margin-top:4px;">Next listing fee: {company.listing_fee_next_due.strftime("%b %d, %Y")} · Missed: {company.listing_fee_missed_count or 0}×</div>'

                companies_html += f'''
                <div class="card">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div>
                            <h3 style="margin: 0;">
                                <a href="/brokerage/company/{company.ticker_symbol}" style="color:#f1f5f9;text-decoration:none;">{company.ticker_symbol}</a>
                                — {company.company_name}
                            </h3>
                            <p style="color: #64748b;">Sector: {company.sector or "General"} · Share class: {company.share_class.replace("_"," ").title()}</p>
                            {listing_fee_note}
                        </div>
                        <div style="text-align: right;">
                            <div style="font-size: 1.5rem; font-weight: bold; color: #38bdf8;">{fmt_usd(company.current_price, disp, precision=4)}</div>
                        </div>
                    </div>

                    {lockup_notice}

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

                    {siphon_form}

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


@router.post("/api/brokerage/set-siphon")
async def brokerage_set_siphon(
    company_id: int = Form(...),
    rate_pct: int = Form(...),
    session_token: Optional[str] = Cookie(None)
):
    """Set the profit siphon rate (0–10%) for a company the player founded."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    try:
        from banks.brokerage_firm import CompanyShares, get_db as get_firm_db
        rate = max(0, min(10, rate_pct)) / 100.0
        db = get_firm_db()
        try:
            company = db.query(CompanyShares).filter(
                CompanyShares.id == company_id,
                CompanyShares.founder_id == player.id,
                CompanyShares.is_delisted == False,
            ).first()
            if not company:
                return RedirectResponse(url="/brokerage/my-companies?error=not_found", status_code=303)
            company.profit_siphon_rate = rate
            db.commit()
        finally:
            db.close()
        return RedirectResponse(url=f"/brokerage/my-companies?success=siphon_set", status_code=303)
    except Exception as e:
        return RedirectResponse(url=f"/brokerage/my-companies?error=siphon_error", status_code=303)


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

        bank_html = '''<style>
        @media (max-width: 600px) {
            .bnk-4col { grid-template-columns: 1fr 1fr !important; }
            .bnk-2col { grid-template-columns: 1fr !important; }
            .bnk-select { min-width: 0 !important; width: 100% !important; }
        }
        </style>
        <a href="/" style="color: #38bdf8;">← Dashboard</a><h1>Banking & Investments</h1>'''
        
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
                
                <div class="bnk-4col" style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-top: 20px;">
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
                <div class="bnk-4col" style="display:grid;grid-template-columns:repeat(4,1fr);gap:15px;margin-top:16px;">
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
                                       padding:6px 10px;border-radius:3px;min-width:320px;font-family:inherit;"
                                class="bnk-select">
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
                <div class="bnk-2col" style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 15px;">
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
        
        tut3 = ""
        try:
            from tutorial_ux import get_tutorial3_overlay_html
            tut3 = get_tutorial3_overlay_html(player, "banks")
        except Exception:
            pass
        return shell("Banks", tut3 + bank_html, player.cash_balance, player.id)
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
                <h3>🏢 Listed Companies</h3>
                <p style="color: #64748b; font-size: 0.9rem;">Browse all public companies, prices, dividends, and detailed profiles</p>
                <a href="/brokerage/companies" class="btn-blue" style="display: inline-block; margin-top: 10px;">View Companies</a>
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
        
        tut3 = ""
        try:
            from tutorial_ux import get_tutorial3_overlay_html
            tut3 = get_tutorial3_overlay_html(player, "brokerage_firm")
        except Exception:
            pass
        return shell(BANK_NAME, tut3 + body, player.cash_balance, player.id)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return shell("Brokerage Firm", f"Error loading brokerage firm: {e}", player.cash_balance, player.id)


@router.get("/brokerage/trading", response_class=HTMLResponse)
def brokerage_trading_page(session_token: Optional[str] = Cookie(None), ticker: str = None, mode: str = "equity",
                           fund: str = None, success: Optional[str] = None, error: Optional[str] = None):
    """WPE equity and ETF trading page."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)

    def _abbr(usd_val, d):
        """Compact format for tight UI spots — abbreviates to K/M/B/T."""
        amt = (usd_val or 0.0) / d["usd_per_unit"]
        sym, code = d["symbol"], d["code"]
        suffix = ""
        for thresh, suf in [(1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")]:
            if abs(amt) >= thresh:
                amt /= thresh; suffix = suf; break
        result = f"{amt:.2f}{suffix}"
        return f"{sym}{result}" if code == "USD" else f"{sym}{result}\u00a0{code}"

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
        
        if not selected_company and mode != "etf":
            body = f'''
            <a href="/banks/brokerage-firm" style="color: #38bdf8;">← Brokerage Firm</a>
            <h1>WPE Trading Floor</h1>
            <p style="color: #64748b;">No companies are currently listed on the exchange.</p>
            <a href="/brokerage/ipo" class="btn-blue">Launch the First IPO</a>
            '''
            return shell("WPE Trading", body, player.cash_balance, player.id)
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
        td_css += '@media(max-width:600px){.td-layout{grid-template-columns:1fr!important;}.td-3col{grid-template-columns:1fr 1fr!important;}.td-2col{grid-template-columns:1fr!important;}.td-portbar{flex-wrap:wrap!important;gap:12px!important;}.td-input-row{flex-wrap:wrap!important;}.td-input-row input{width:100%!important;}.td-depths{grid-template-columns:1fr!important;}}'
        td_css += '</style>'

        # ── ETF mode ─────────────────────────────────────────────────────────────
        if mode == "etf":
            etf_configs = [
                ("apple_seeds_etf",  "Apple Seeds ETF",   "apple_seeds_etf_shares",  "🍎"),
                ("energy_etf",       "Energy ETF",        "energy_etf_shares",        "⚡"),
                ("city_nav_etf",     "City NAV ETF",      "city_nav_etf_shares",      "🏙️"),
                ("land_bank",        "Land Bank",         "land_bank_shares",          "🏦"),
                ("wbc50_index_fund", "WBC-50 Index Fund", "wbc50_index_fund_shares",  "📈"),
            ]
            import banks as _banks_mod
            import inventory as _inv_mod
            import market as _mkt_mod
            from market import Trade as _MktTrade, MarketOrder as _MktOrder, OrderStatus as _MktOS, get_db as _mkt_get_db

            # Determine selected fund
            selected_fund_id = fund if fund and fund in {c[0] for c in etf_configs} else etf_configs[0][0]

            # Gather all fund data
            all_fund_data = []
            sel_fd = None
            for bank_id, name, share_item, icon in etf_configs:
                try:
                    be = _banks_mod.get_bank_entity(bank_id)
                    if not be:
                        continue
                    your_shares = _inv_mod.get_item_quantity(player.id, share_item)
                    mkt_price = _mkt_mod.get_market_price(share_item)
                    nav = (be.cash_reserves or 0) + (be.asset_value or 0)
                    fd = {"bank_id": bank_id, "name": name, "share_item": share_item,
                          "icon": icon, "be": be, "your_shares": your_shares,
                          "mkt_price": mkt_price, "nav": nav,
                          "is_selected": bank_id == selected_fund_id}
                    all_fund_data.append(fd)
                    if bank_id == selected_fund_id:
                        sel_fd = fd
                except Exception:
                    continue

            if not sel_fd and all_fund_data:
                sel_fd = all_fund_data[0]
                selected_fund_id = sel_fd["bank_id"]
            if not sel_fd:
                return shell("ETF Trading", "<p>No ETF funds available.</p>", player.cash_balance, player.id)

            sel_item = sel_fd["share_item"]
            sel_be = sel_fd["be"]
            sel_price = sel_fd["mkt_price"] or sel_be.share_price or 0
            sel_name = sel_fd["name"]
            sel_icon = sel_fd["icon"]
            sel_your_shares = sel_fd["your_shares"]
            sel_nav = sel_fd["nav"]
            fund_link_id = selected_fund_id.replace("_", "-")
            disp_sym = disp["symbol"]
            disp_code = disp["code"]
            default_price = round(sel_price / disp["usd_per_unit"], 6)
            sell_disabled_attr = "disabled" if sel_your_shares <= 0 else ""
            total_shares_issued = sel_be.total_shares_issued or 1
            nav_per_share = sel_nav / total_shares_issued
            sel_name_short = sel_name[:22] if len(sel_name) > 22 else sel_name

            # Order book (named traders)
            etf_ob = _mkt_mod.get_order_book(sel_item)
            etf_bids = etf_ob.get("bids", [])  # (price, qty, order_id, player_name, player_id)
            etf_asks = etf_ob.get("asks", [])
            best_bid = etf_bids[0][0] if etf_bids else None
            best_ask = etf_asks[0][0] if etf_asks else None
            etf_spread = (best_ask - best_bid) if best_bid and best_ask else 0
            etf_spread_pct = (etf_spread / best_bid * 100) if best_bid and etf_spread else 0
            mid_price = ((best_bid + best_ask) / 2) if best_bid and best_ask else sel_price
            premium_discount = ((mid_price - nav_per_share) / nav_per_share * 100) if nav_per_share > 0 else 0
            pd_color = "#22c55e" if premium_discount >= 0 else "#ef4444"
            pd_sign = "+" if premium_discount >= 0 else ""
            mid_price_fmt = fmt_usd(mid_price, disp, precision=4)
            best_bid_fmt = fmt_usd(best_bid, disp, precision=4) if best_bid else "—"
            best_ask_fmt = fmt_usd(best_ask, disp, precision=4) if best_ask else "—"
            etf_spread_fmt = fmt_usd(etf_spread, disp, precision=4)

            # Recent trades for sparkline + time & sales
            _mkt_db = _mkt_get_db()
            try:
                etf_recent_trades = _mkt_db.query(_MktTrade).filter(
                    _MktTrade.item_type == sel_item
                ).order_by(_MktTrade.executed_at.desc()).limit(20).all()

                etf_open_orders = _mkt_db.query(_MktOrder).filter(
                    _MktOrder.player_id == player.id,
                    _MktOrder.item_type == sel_item,
                    _MktOrder.status.in_([_MktOS.ACTIVE, _MktOS.PARTIALLY_FILLED])
                ).order_by(_MktOrder.created_at.desc()).all()
            finally:
                _mkt_db.close()

            # Sparkline SVG
            etf_spark_svg = '<div style="height:70px;display:flex;align-items:center;justify-content:center;color:#334155;font-size:0.75rem;">No trade history yet</div>'
            if len(etf_recent_trades) >= 2:
                spark_prices = [t.price for t in reversed(etf_recent_trades)]
                min_p = min(spark_prices); max_p = max(spark_prices)
                pr = max_p - min_p if max_p != min_p else 1
                pts = []; area = []
                for i, p in enumerate(spark_prices):
                    x = 2 + i / (len(spark_prices) - 1) * 496
                    y = 2 + 66 - ((p - min_p) / pr * 66)
                    pts.append(f"{x:.1f},{y:.1f}"); area.append(f"{x:.1f},{y:.1f}")
                area.extend(["498,70", "2,70"])
                lc = "#22c55e" if spark_prices[-1] >= spark_prices[0] else "#ef4444"
                pts_str = " ".join(pts); area_str = " ".join(area)
                etf_spark_svg = (
                    f'<svg viewBox="0 0 500 70" preserveAspectRatio="none" style="width:100%;height:70px;display:block;">'
                    f'<defs><linearGradient id="esfill" x1="0" y1="0" x2="0" y2="1">'
                    f'<stop offset="0%" stop-color="{lc}" stop-opacity="0.2"/>'
                    f'<stop offset="100%" stop-color="{lc}" stop-opacity="0.01"/>'
                    f'</linearGradient></defs>'
                    f'<polygon points="{area_str}" fill="url(#esfill)"/>'
                    f'<polyline points="{pts_str}" fill="none" stroke="{lc}" stroke-width="1.5" stroke-linejoin="round"/>'
                    f'</svg>'
                )

            # Order book HTML (with TRADER column unique to ETF)
            all_bq = [q for _, q, *_ in etf_bids] + [q for _, q, *_ in etf_asks]
            max_bq = max(all_bq) if all_bq else 1
            etf_ob_html = (
                '<div style="font-size:0.65rem;color:#475569;display:grid;grid-template-columns:1fr 1fr 1fr;'
                'padding:2px 8px;margin-bottom:4px;"><span>PRICE</span>'
                '<span style="text-align:right;">QTY</span>'
                '<span style="text-align:right;">TRADER</span></div>'
            )
            if etf_asks:
                for price, qty, oid, pname, pid in reversed(etf_asks):
                    bw = qty / max_bq * 100
                    sn = (pname[:13] + "…") if len(pname) > 13 else pname
                    p_fmt = fmt_usd(price, disp, precision=4)
                    etf_ob_html += (
                        f'<div style="position:relative;padding:2px 8px;display:grid;grid-template-columns:1fr 1fr 1fr;font-size:0.78rem;">'
                        f'<div style="position:absolute;right:0;top:0;bottom:0;width:{bw:.0f}%;background:rgba(239,68,68,0.1);"></div>'
                        f'<span style="color:#ef4444;position:relative;">{p_fmt}</span>'
                        f'<span style="text-align:right;color:#94a3b8;position:relative;">{qty:,.2f}</span>'
                        f'<span style="text-align:right;color:#475569;position:relative;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{sn}</span>'
                        f'</div>'
                    )
            else:
                etf_ob_html += '<div style="padding:4px 8px;color:#334155;font-size:0.75rem;text-align:center;">No asks</div>'
            etf_ob_html += (
                f'<div style="padding:4px 8px;text-align:center;font-size:0.7rem;color:#64748b;'
                f'border-top:1px solid #1e293b;border-bottom:1px solid #1e293b;background:#0a0f1a;">'
                f'Spread {etf_spread_fmt} ({etf_spread_pct:.2f}%)</div>'
            )
            if etf_bids:
                for price, qty, oid, pname, pid in etf_bids:
                    bw = qty / max_bq * 100
                    sn = (pname[:13] + "…") if len(pname) > 13 else pname
                    p_fmt = fmt_usd(price, disp, precision=4)
                    etf_ob_html += (
                        f'<div style="position:relative;padding:2px 8px;display:grid;grid-template-columns:1fr 1fr 1fr;font-size:0.78rem;">'
                        f'<div style="position:absolute;right:0;top:0;bottom:0;width:{bw:.0f}%;background:rgba(34,197,94,0.1);"></div>'
                        f'<span style="color:#22c55e;position:relative;">{p_fmt}</span>'
                        f'<span style="text-align:right;color:#94a3b8;position:relative;">{qty:,.2f}</span>'
                        f'<span style="text-align:right;color:#475569;position:relative;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{sn}</span>'
                        f'</div>'
                    )
            else:
                etf_ob_html += '<div style="padding:4px 8px;color:#334155;font-size:0.75rem;text-align:center;">No bids</div>'

            # Time & Sales
            etf_ts_html = '<div style="padding:8px;color:#334155;font-size:0.75rem;text-align:center;">No trades yet</div>'
            if etf_recent_trades:
                etf_ts_html = ""
                prev_p = None
                for t in etf_recent_trades[:12]:
                    tc = "#94a3b8"
                    if prev_p is not None:
                        tc = "#22c55e" if t.price >= prev_p else "#ef4444"
                    prev_p = t.price
                    ts_str = t.executed_at.strftime("%H:%M") if t.executed_at else ""
                    p_fmt = fmt_usd(t.price, disp, precision=4)
                    etf_ts_html += (
                        f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr;font-size:0.78rem;padding:2px 8px;">'
                        f'<span style="color:{tc};">{p_fmt}</span>'
                        f'<span style="text-align:right;color:#94a3b8;">{t.quantity:,.2f}</span>'
                        f'<span style="text-align:right;color:#475569;">{ts_str}</span>'
                        f'</div>'
                    )

            # Fund sidebar
            etf_sidebar_html = ""
            for fd in all_fund_data:
                is_sel = fd["is_selected"]
                bg = "#1e293b" if is_sel else "transparent"
                bl = "3px solid #34d399" if is_sel else "3px solid transparent"
                mp = fd["mkt_price"]
                mp_str = _abbr(mp, disp) if mp else "—"
                ys = fd["your_shares"]
                ys_str = f"{ys:,.2f} shs" if ys > 0 else ""
                fn = fd["name"]; fn_short = (fn[:16] + "…") if len(fn) > 16 else fn
                fw = "700" if is_sel else "500"
                etf_sidebar_html += (
                    f'<a href="/brokerage/trading?mode=etf&fund={fd["bank_id"]}" '
                    f'style="display:block;padding:8px 10px;border-left:{bl};background:{bg};text-decoration:none;color:#e5e7eb;">'
                    f'<div style="display:flex;justify-content:space-between;align-items:baseline;min-width:0;gap:4px;">'
                    f'<span style="font-weight:{fw};font-size:0.82rem;flex-shrink:0;">{fd["icon"]} {fn_short}</span>'
                    f'<span style="font-size:0.75rem;color:#94a3b8;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{mp_str}</span>'
                    f'</div>'
                )
                if ys_str:
                    etf_sidebar_html += f'<div style="font-size:0.7rem;color:#64748b;margin-top:2px;">{ys_str}</div>'
                etf_sidebar_html += '</a>'

            # Open orders with cancel
            etf_orders_html = ""
            if etf_open_orders:
                etf_orders_html = f'<div style="margin-top:12px;"><div style="font-size:0.7rem;color:#64748b;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:6px;padding:0 4px;">Open Orders ({len(etf_open_orders)})</div>'
                for ord_ in etf_open_orders:
                    sc = "#22c55e" if ord_.order_type == "buy" else "#ef4444"
                    pd_str = fmt_usd(ord_.price, disp, precision=4) if ord_.price else "MKT"
                    rem = ord_.quantity - ord_.quantity_filled
                    etf_orders_html += (
                        f'<div style="display:flex;justify-content:space-between;align-items:center;'
                        f'padding:5px 4px;border-top:1px solid #0f172a;font-size:0.78rem;">'
                        f'<div><span style="color:{sc};font-weight:600;">{ord_.order_type.upper()}</span> '
                        f'<span style="color:#94a3b8;">{rem:,.2f} @ {pd_str}</span></div>'
                        f'<form action="/api/brokerage/cancel-etf-order" method="post" style="display:inline;margin:0;">'
                        f'<input type="hidden" name="order_id" value="{ord_.id}">'
                        f'<input type="hidden" name="fund" value="{selected_fund_id}">'
                        f'<button type="submit" style="background:none;border:1px solid #334155;color:#94a3b8;padding:1px 6px;font-size:0.7rem;cursor:pointer;">✕</button>'
                        f'</form></div>'
                    )
                etf_orders_html += '</div>'

            # ETF-specific tab CSS (built as plain string — no brace escaping needed)
            etf_tab_css = (
                '<style>'
                '.etf-buy-panel,.etf-sell-panel{display:none;}'
                '#etf-tab-buy:checked~.etf-buy-panel{display:block;}'
                '#etf-tab-sell:checked~.etf-sell-panel{display:block;}'
                '#etf-tab-buy:checked~.etf-tab-bar .etf-tab-buy{background:#16a34a;color:#fff;}'
                '#etf-tab-sell:checked~.etf-tab-bar .etf-tab-sell{background:#dc2626;color:#fff;}'
                '</style>'
            )

            num_funds = len(all_fund_data)
            nav_ps_fmt = fmt_usd(nav_per_share, disp, precision=4)
            nav_fmt = _abbr(sel_nav, disp)
            your_val_fmt = fmt_usd(sel_your_shares * sel_price, disp)

            etf_body = td_css + etf_tab_css + f'''
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px;">
                <a href="/banks/brokerage-firm" style="color:#38bdf8;font-size:0.8rem;">&larr; Brokerage Firm</a>
                <span style="font-size:0.85rem;color:#94a3b8;font-weight:600;">ETF Trading Floor</span>
            </div>
            <!-- Mode tabs -->
            <div style="display:flex;gap:8px;margin-bottom:12px;">
                <a href="/brokerage/trading"
                   style="padding:7px 18px;border-radius:4px;text-decoration:none;background:#1e293b;color:#94a3b8;font-size:.8rem;">
                    WPE Equities
                </a>
                <a href="/brokerage/trading?mode=etf"
                   style="padding:7px 18px;border-radius:4px;text-decoration:none;background:#34d399;color:#020617;font-size:.8rem;font-weight:bold;">
                    ETF &amp; Index Funds
                </a>
            </div>

            <!-- 3-Column Trading Layout -->
            <div class="td-layout">
                <!-- LEFT: Fund Sidebar -->
                <div class="td-sidebar">
                    <div style="padding:8px 10px;border-bottom:1px solid #1e293b;font-size:0.7rem;color:#64748b;text-transform:uppercase;letter-spacing:0.5px;">
                        Funds &middot; {num_funds} Available
                    </div>
                    {etf_sidebar_html}
                </div>

                <!-- CENTER: Fund Detail -->
                <div class="td-main">
                    <!-- Price Header -->
                    <div class="td-section" style="margin-bottom:0;border-bottom:none;">
                        <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px;">
                            <div>
                                <div style="font-size:1.05rem;font-weight:700;color:#e5e7eb;">{sel_icon} {sel_name}</div>
                                <div style="font-size:0.75rem;color:#64748b;margin-top:2px;">
                                    ETF &middot; <a href="/banks/{fund_link_id}" style="color:#a78bfa;font-size:0.75rem;">Fund Details →</a>
                                </div>
                            </div>
                            <div style="text-align:right;">
                                <div style="font-size:1.5rem;font-weight:700;color:#34d399;">{mid_price_fmt}</div>
                                <div style="font-size:0.8rem;color:{pd_color};">{pd_sign}{premium_discount:.2f}% <span style="color:#475569;">vs NAV/share</span></div>
                            </div>
                        </div>
                    </div>

                    <!-- Sparkline -->
                    <div class="td-section" style="margin-top:0;border-top:none;padding-top:0;">
                        {etf_spark_svg}
                    </div>

                    <!-- Key Stats -->
                    <div class="td-section">
                        <div class="td-3col" style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;">
                            <div><div class="td-label">Fund NAV</div><div style="font-size:0.9rem;">{nav_fmt}</div></div>
                            <div><div class="td-label">NAV / Share</div><div style="font-size:0.9rem;">{nav_ps_fmt}</div></div>
                            <div><div class="td-label">Your Shares</div><div style="font-size:0.9rem;color:#38bdf8;">{sel_your_shares:,.4f}</div></div>
                            <div><div class="td-label">Best Bid</div><div style="font-size:0.9rem;color:#22c55e;">{best_bid_fmt}</div></div>
                            <div><div class="td-label">Best Ask</div><div style="font-size:0.9rem;color:#ef4444;">{best_ask_fmt}</div></div>
                            <div><div class="td-label">Spread</div><div style="font-size:0.9rem;">{etf_spread_fmt} ({etf_spread_pct:.2f}%)</div></div>
                        </div>
                    </div>

                    <!-- Depth of Market + Time & Sales -->
                    <div class="td-depths" style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
                        <div class="td-section" style="margin-bottom:0;">
                            <div style="font-size:0.7rem;color:#64748b;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:6px;">Depth of Market</div>
                            {etf_ob_html}
                        </div>
                        <div class="td-section" style="margin-bottom:0;">
                            <div style="font-size:0.7rem;color:#64748b;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:6px;">Time &amp; Sales</div>
                            <div style="font-size:0.7rem;color:#475569;display:grid;grid-template-columns:1fr 1fr 1fr;padding:2px 8px;margin-bottom:4px;"><span>PRICE</span><span style="text-align:right;">QTY</span><span style="text-align:right;">TIME</span></div>
                            {etf_ts_html}
                        </div>
                    </div>
                </div>

                <!-- RIGHT: Trade Panel -->
                <div class="td-panel">
                    <!-- Position Summary -->
                    <div style="margin-bottom:12px;">
                        <div style="font-size:0.7rem;color:#64748b;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:8px;">Your Position</div>
                        <div class="td-2col" style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:0.8rem;">
                            <div><span style="color:#64748b;">Shares</span><div style="color:#38bdf8;font-size:1rem;font-weight:600;">{sel_your_shares:,.4f}</div></div>
                            <div><span style="color:#64748b;">Value</span><div style="font-size:1rem;">{your_val_fmt}</div></div>
                        </div>
                    </div>

                    <div style="border-top:1px solid #1e293b;padding-top:12px;">
                        <input type="radio" id="etf-tab-buy" name="etf-trade-tab" checked style="display:none;">
                        <input type="radio" id="etf-tab-sell" name="etf-trade-tab" style="display:none;">
                        <div class="etf-tab-bar" style="display:grid;grid-template-columns:1fr 1fr;margin-bottom:12px;">
                            <label for="etf-tab-buy" class="etf-tab-buy" style="padding:6px;text-align:center;cursor:pointer;font-size:0.85rem;font-weight:600;background:#1e293b;color:#64748b;border:1px solid #1e293b;">Buy</label>
                            <label for="etf-tab-sell" class="etf-tab-sell" style="padding:6px;text-align:center;cursor:pointer;font-size:0.85rem;font-weight:600;background:#1e293b;color:#64748b;border:1px solid #1e293b;">Sell</label>
                        </div>

                        <div class="etf-buy-panel">
                            <form action="/api/brokerage/etf-order" method="post">
                                <input type="hidden" name="item_type" value="{sel_item}">
                                <input type="hidden" name="order_type" value="buy">
                                <input type="hidden" name="fund" value="{selected_fund_id}">
                                <div style="margin-bottom:10px;">
                                    <label style="display:block;margin-bottom:4px;color:#94a3b8;font-size:0.8rem;">Quantity (shares)</label>
                                    <input type="number" name="quantity" min="0.0001" step="0.0001" value="100" class="td-input">
                                </div>
                                <div style="margin-bottom:10px;">
                                    <label style="display:block;margin-bottom:4px;color:#94a3b8;font-size:0.8rem;">Limit Price ({disp_sym} {disp_code})</label>
                                    <input type="number" name="price" min="0.000001" step="0.000001" value="{default_price}" class="td-input">
                                </div>
                                <div style="font-size:0.7rem;color:#475569;margin-bottom:10px;">Cash: {_abbr(player.cash_balance, disp)}</div>
                                <button type="submit" style="width:100%;padding:10px;background:#16a34a;color:#fff;border:none;font-size:0.85rem;font-weight:600;cursor:pointer;">
                                    Buy {sel_icon} {sel_name_short}
                                </button>
                            </form>
                        </div>

                        <div class="etf-sell-panel">
                            <form action="/api/brokerage/etf-order" method="post">
                                <input type="hidden" name="item_type" value="{sel_item}">
                                <input type="hidden" name="order_type" value="sell">
                                <input type="hidden" name="fund" value="{selected_fund_id}">
                                <div style="margin-bottom:10px;">
                                    <label style="display:block;margin-bottom:4px;color:#94a3b8;font-size:0.8rem;">Quantity (shares)</label>
                                    <input type="number" name="quantity" min="0.0001" step="0.0001" value="100" class="td-input">
                                </div>
                                <div style="margin-bottom:10px;">
                                    <label style="display:block;margin-bottom:4px;color:#94a3b8;font-size:0.8rem;">Limit Price ({disp_sym} {disp_code})</label>
                                    <input type="number" name="price" min="0.000001" step="0.000001" value="{default_price}" class="td-input">
                                </div>
                                <div style="font-size:0.75rem;color:#64748b;margin-bottom:10px;">
                                    Available: {sel_your_shares:,.4f} shares
                                </div>
                                <button type="submit" {sell_disabled_attr} style="width:100%;padding:10px;background:#dc2626;color:#fff;border:none;font-size:0.85rem;font-weight:600;cursor:pointer;">
                                    Sell {sel_icon} {sel_name_short}
                                </button>
                            </form>
                        </div>
                    </div>

                    {etf_orders_html}
                </div>
            </div>
            '''
            return shell("ETF Trading", etf_body, player.cash_balance, player.id)
        # ─────────────────────────────────────────────────────────────────────────

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

        # Total buying power: sum all currency balances converted to USD
        _total_buying_power = player.cash_balance  # fallback
        try:
            from reserve_banks import get_db as _get_rb_db, PlayerCurrencyBalance, StateReserveBank
            _rb_db = _get_rb_db()
            try:
                _bals = _rb_db.query(PlayerCurrencyBalance).filter(
                    PlayerCurrencyBalance.player_id == player.id
                ).all()
                _total_buying_power = 0.0
                for _b in _bals:
                    if (_b.balance or 0.0) > 0:
                        if _b.currency_code == "USD":
                            _total_buying_power += float(_b.balance)
                        else:
                            _bk = _rb_db.query(StateReserveBank).filter(
                                StateReserveBank.currency_code == _b.currency_code
                            ).first()
                            if _bk and _bk.usd_per_unit > 0:
                                _total_buying_power += float(_b.balance) * float(_bk.usd_per_unit)
            finally:
                _rb_db.close()
        except Exception:
            pass

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
                pl_txt = f"{'+'if pd_item['pl']>=0 else ''}{_abbr(pd_item['pl'], disp)}"
            positions_html += f'<a href="/brokerage/trading?ticker={c.ticker_symbol}" style="display:block;padding:8px 10px;border-left:{bl};background:{bg};text-decoration:none;color:#e5e7eb;">'
            positions_html += f'<div style="display:flex;justify-content:space-between;align-items:baseline;min-width:0;gap:4px;"><span style="font-weight:{"700" if is_sel else "500"};font-size:0.85rem;flex-shrink:0;">{c.ticker_symbol}</span><span style="font-size:0.78rem;color:#94a3b8;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{_abbr(c.current_price, disp)}</span></div>'
            if shares_txt or pl_txt:
                positions_html += f'<div style="display:flex;justify-content:space-between;margin-top:2px;font-size:0.7rem;min-width:0;gap:4px;"><span style="color:#64748b;flex-shrink:0;">{shares_txt}</span><span style="color:{plc};white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{pl_txt}</span></div>'
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
        margin_debt_html = f"<div style='min-width:0;'><span class='td-label'>Margin Debt</span><div style='color:#f59e0b;font-size:0.95rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:160px;' title='{fmt_usd(total_margin_debt, disp)}'>{_abbr(total_margin_debt, disp)}</div></div>" if total_margin_debt > 0 else ""



        # Assemble the full dashboard body
        from html import escape as html_escape
        _alert_banner = ""
        _TRADING_MSGS = {
            "buy_order_placed":  ("Order placed.", True),
            "sell_order_placed": ("Order placed.", True),
            "buy_failed":        ("Buy order failed. Check your balance and order size.", False),
            "sell_failed":       ("Sell order failed. You may have exceeded the quantity available to sell, or the order was rejected by the exchange.", False),
            "ipo_created":       ("Your IPO has been listed on the WPE! Your shares are now publicly tradeable.", True),
        }

        # Tutorial 3 — advance to reward step when IPO just completed
        if success == "ipo_created":
            try:
                from tutorial_ux import get_tutorial3_step, set_tutorial3_step, player_has_public_company
                if get_tutorial3_step(player.id) == 6 and player_has_public_company(player.id):
                    set_tutorial3_step(player.id, 7)
            except Exception:
                pass
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
        <div class="td-portbar" style="display:flex;gap:24px;padding:10px 16px;background:#0f172a;border:1px solid #1e293b;font-size:0.8rem;flex-wrap:wrap;">
            <div style="min-width:0;">
                <span class="td-label">Portfolio Value</span>
                <div style="color:#e5e7eb;font-size:0.95rem;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:160px;" title="{fmt_usd(total_portfolio_value, disp)}">{_abbr(total_portfolio_value, disp)}</div>
            </div>
            <div style="min-width:0;">
                <span class="td-label">Total P/L</span>
                <div style="color:{"#22c55e" if total_pl >= 0 else "#ef4444"};font-size:0.95rem;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:180px;" title="{"+" if total_pl >= 0 else ""}{fmt_usd(total_pl, disp)}">{"+" if total_pl >= 0 else ""}{_abbr(total_pl, disp)} <span style="font-size:0.75rem;">({total_pl_pct:+.1f}%)</span></div>
            </div>
            <div style="min-width:0;">
                <span class="td-label">Buying Power</span>
                <div style="color:#22c55e;font-size:0.95rem;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:160px;" title="{fmt_usd(_total_buying_power, disp)}">{_abbr(_total_buying_power, disp)}</div>
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
                    <div class="td-3col" style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;">
                        <div><div class="td-label">Market Cap</div><div style="font-size:0.9rem;">{fmt_usd(selected_company.current_price * selected_company.shares_outstanding, disp, precision=0)}</div></div>
                        <div><div class="td-label">Shares Out</div><div style="font-size:0.9rem;">{selected_company.shares_outstanding:,}</div></div>
                        <div><div class="td-label">Float</div><div style="font-size:0.9rem;">{selected_company.shares_in_float:,}</div></div>
                        <div><div class="td-label">52W Range</div><div style="font-size:0.9rem;">{fmt_usd(selected_company.low_52_week, disp)} &mdash; {fmt_usd(selected_company.high_52_week, disp)}</div></div>
                        <div><div class="td-label">Volume Today</div><div style="font-size:0.9rem;">{selected_company.volume_today:,}</div></div>
                        <div><div class="td-label">Dividends</div><div style="font-size:0.85rem;">{dividend_display}</div></div>
                    </div>
                </div>

                <!-- Depth of Market + Time & Sales -->
                <div class="td-depths" style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
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
                    <div class="td-2col" style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:0.8rem;">
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

        tut3 = ""
        try:
            from tutorial_ux import get_tutorial3_overlay_html
            tut3 = get_tutorial3_overlay_html(player, "brokerage_trading")
        except Exception:
            pass
        return shell(f"Trade {selected_company.ticker_symbol}", tut3 + body, player.cash_balance, player.id)

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
            get_firm_entity, IPO_CONFIG, IPOType, IPO_LOCKUP_DAYS,
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
            # Inject Tutorial 3 overlay — needed when player retakes T3 at step 6
            # (player already has a public company so this is an early return path)
            tut3 = ""
            try:
                from tutorial_ux import get_tutorial3_overlay_html
                tut3 = get_tutorial3_overlay_html(player, "brokerage_ipo")
            except Exception:
                pass
            return shell("IPO Center", tut3 + body, player.cash_balance, player.id)

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
                    <div style="font-size: 0.8rem; color: #64748b; margin-top: 10px;">Min valuation: $25,000 &bull; <span style="color:#f59e0b;">&#8987; {IPO_LOCKUP_DAYS.get("direct_listing", 15)}-day founder lockup</span></div>
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
                    <div style="font-size: 0.8rem; color: #64748b; margin-top: 10px;">Min valuation: $50,000 &bull; <span style="color:#f59e0b;">&#8987; {IPO_LOCKUP_DAYS.get("firm_underwritten", 30)}-day founder lockup</span></div>
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
                    <div style="font-size: 0.8rem; color: #64748b; margin-top: 10px;">Min valuation: $75,000 &bull; Max float: 40% &bull; <span style="color:#f59e0b;">&#8987; {IPO_LOCKUP_DAYS.get("income_shares", 30)}-day founder lockup</span></div>
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
                    <div style="font-size: 0.8rem; color: #64748b; margin-top: 10px;">Min valuation: $100,000 &bull; Max float: 49% &bull; Class A (founder) + Class B (public) &bull; <span style="color:#f59e0b;">&#8987; {IPO_LOCKUP_DAYS.get("dual_class", 60)}-day founder lockup</span></div>
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
                    <div style="font-size: 0.8rem; color: #64748b; margin-top: 10px;">Min valuation: $50,000 &bull; Max float: 40% &bull; Callable preferred shares &bull; <span style="color:#f59e0b;">&#8987; {IPO_LOCKUP_DAYS.get("preferred_offering", 30)}-day founder lockup</span></div>
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
                    <div style="font-size: 0.8rem; color: #64748b; margin-top: 10px;">Min valuation: $150,000 &bull; Max float: 30% &bull; Growth capital injection &bull; <span style="color:#f59e0b;">&#8987; {IPO_LOCKUP_DAYS.get("series_a_growth", 60)}-day founder lockup</span></div>
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
                    <div style="font-size: 0.8rem; color: #64748b; margin-top: 10px;">Min valuation: $200,000 &bull; Max float: 60% &bull; Retain 40%+ as Class A &bull; <span style="color:#f59e0b;">&#8987; {IPO_LOCKUP_DAYS.get("quad_class", 90)}-day founder lockup</span></div>
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

        tut3 = ""
        try:
            from tutorial_ux import get_tutorial3_overlay_html
            tut3 = get_tutorial3_overlay_html(player, "brokerage_ipo")
        except Exception:
            pass
        return shell("IPO Center", tut3 + body, player.cash_balance, player.id)

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
                            <option value="force_dividend_from_escrow">Release Escrow — distribute escrow to minority shareholders</option>
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
                    <div id="gov-param-escrow" style="margin-bottom:12px;display:none;">
                        <label style="color:#94a3b8;display:block;margin-bottom:4px;">Amount to Release from Escrow ($)</label>
                        <input type="number" name="param_escrow_amount" min="0" step="0.01" placeholder="Leave blank to release full escrow balance"
                               style="width:100%;padding:8px;background:#0f172a;color:#e2e8f0;border:1px solid #334155;border-radius:4px;">
                        <p style="color:#64748b;font-size:0.8rem;margin-top:4px;">If passed, the founder's voting power is capped to 1× and the specified amount (or full escrow balance) is distributed proportionally to non-founder shareholders.</p>
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
                    document.getElementById('gov-param-escrow').style.display = type === 'force_dividend_from_escrow' ? '' : 'none';
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
    param_escrow_amount: Optional[str] = Form(None),
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
        elif proposal_type == "force_dividend_from_escrow":
            if param_escrow_amount:
                try:
                    proposal_param["escrow_amount"] = float(param_escrow_amount)
                except ValueError:
                    pass
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
            CompanyShares, ShareholderPosition, get_db as get_firm_db,
            get_loyalty_tier, get_player_shareholder_perks
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
                    loyalty_mult, loyalty_label = get_loyalty_tier(pos.first_held_at)

                    portfolio_data.append({
                        "company": company,
                        "position": pos,
                        "market_value": market_value,
                        "cost_basis_total": cost_basis_total,
                        "pnl": pnl,
                        "pnl_pct": pnl_pct,
                        "loyalty_mult": loyalty_mult,
                        "loyalty_label": loyalty_label,
                    })
                    
                    total_value += market_value
                    total_cost += cost_basis_total
                    total_margin_debt += pos.margin_debt
            
        finally:
            db.close()

        # Fetch shareholder perks (outside db context)
        try:
            shareholder_perks = get_player_shareholder_perks(player.id)
        except Exception:
            shareholder_perks = []

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
                        <th style="padding: 12px 8px;">Loyalty</th>
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
                loyalty_mult = item["loyalty_mult"]
                loyalty_label = item["loyalty_label"]
                loyalty_color = "#22c55e" if loyalty_mult >= 1.20 else ("#f59e0b" if loyalty_mult >= 1.10 else "#94a3b8")
                loyalty_bonus_html = f'<br><span style="font-size:0.75rem;color:{loyalty_color};">+{(loyalty_mult-1)*100:.0f}% div bonus</span>' if loyalty_mult > 1.0 else ""
                loyalty_cell = f'<span style="color:{loyalty_color};font-size:0.85rem;">{loyalty_label}</span>{loyalty_bonus_html}'

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
                    <td style="padding: 12px 8px; vertical-align: top;">
                        {loyalty_cell}
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

        # Build shareholder perks section
        if shareholder_perks:
            perks_rows = ""
            for perk in shareholder_perks:
                perks_rows += f'''
                <tr style="border-bottom:1px solid #1e293b;">
                    <td style="padding:10px 8px;"><strong>{perk["ticker"]}</strong><br><span style="color:#64748b;font-size:0.8rem;">{perk["company_name"]}</span></td>
                    <td style="padding:10px 8px;color:#38bdf8;">{perk["sector"]}</td>
                    <td style="padding:10px 8px;color:#94a3b8;">{perk["perk"]}</td>
                </tr>'''
            perks_html = f'''
        <div class="card" style="margin-top:20px;">
            <h3>Shareholder Perks</h3>
            <p style="font-size:0.85rem;color:#64748b;margin-bottom:12px;">
                Sector-based perks that apply to your equity positions. Finance sector holdings grant bonus credit per dividend payment.
            </p>
            <table style="width:100%;border-collapse:collapse;">
                <thead>
                    <tr style="border-bottom:1px solid #334155;text-align:left;">
                        <th style="padding:10px 8px;">Company</th>
                        <th style="padding:10px 8px;">Sector</th>
                        <th style="padding:10px 8px;">Perk</th>
                    </tr>
                </thead>
                <tbody>{perks_rows}</tbody>
            </table>
        </div>'''
        else:
            perks_html = ""

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
                Loyalty tiers boost your dividend payouts: <strong style="color:#f59e0b;">7+ days</strong> = standard, <strong style="color:#f59e0b;">30+ days</strong> = +10%, <strong style="color:#22c55e;">90+ days</strong> = +25%.
            </p>
            {portfolio_html}
        </div>
        {perks_html}
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

    # ── shared palette — keyed to item_types.json category values ────────────
    cat_colors = {
        "seeds": "#22c55e", "crops": "#22c55e", "produce": "#84cc16",
        "livestock": "#f59e0b", "animals": "#f59e0b",
        "seafood": "#06b6d4", "shellfish": "#06b6d4", "zoo_supplies": "#f59e0b",
        "food": "#f97316", "baked_goods": "#fb923c", "confectionery": "#fb923c",
        "prepared_food": "#f97316", "canned_goods": "#f97316",
        "condiments": "#fbbf24", "sweeteners": "#fbbf24",
        "meat": "#ef4444", "seafood_product": "#06b6d4",
        "dairy": "#cbd5e1", "beverages": "#38bdf8", "beverage": "#38bdf8",
        "alcohol": "#a855f7", "ingredients": "#fbbf24", "food_service": "#f97316",
        "industrial": "#64748b", "energy": "#eab308", "fuel": "#dc2626",
        "liquids": "#06b6d4", "electronics": "#38bdf8", "components": "#6366f1",
        "metals": "#94a3b8", "ore": "#78716c", "packaging": "#64748b",
        "utilities": "#0891b2", "logistics": "#60a5fa", "lab_equipment": "#64748b",
        "robotics": "#6366f1", "medical_equipment": "#10b981",
        "minerals": "#a8a29e", "chemicals": "#ec4899", "aerospace": "#06b6d4",
        "materials": "#94a3b8", "construction": "#8b5cf6",
        "prison_infrastructure": "#78716c", "zoo_infrastructure": "#f59e0b",
        "wood": "#a16207",
        "vehicle": "#60a5fa", "vehicles": "#60a5fa",
        "vehicle_parts": "#60a5fa", "auto_parts": "#3b82f6", "marine_parts": "#0ea5e9",
        "apparel": "#ec4899", "textiles": "#c084fc", "accessories": "#e879f9",
        "home_goods": "#14b8a6", "appliances": "#14b8a6",
        "health": "#22c55e", "personal_care": "#f472b6", "essential_oils": "#a78bfa",
        "pharmaceuticals": "#22c55e", "medical_supplies": "#22c55e",
        "tobacco": "#a78bfa", "cured_tobacco": "#a78bfa",
        "media": "#facc15", "education": "#38bdf8", "prison": "#64748b",
        "entertainment": "#8b5cf6",
        "military": "#dc2626", "retail_military": "#dc2626", "intelligence": "#ef4444",
        "luxury": "#d4af37",
        "services": "#a78bfa", "hospitality": "#a78bfa",
        "retail_service": "#a78bfa", "retail_food": "#f97316",
        "retail_shopping": "#ec4899", "retail_entertainment": "#8b5cf6",
        "retail_medical": "#22c55e", "retail_education": "#38bdf8",
        "retail_transport": "#60a5fa", "retail_zoo": "#f59e0b",
        "retail_prison": "#64748b",
        "financial": "#10b981",
        "unknown": "#64748b",
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
# WIDGET / TICKER DATA API
# ==========================

_WIDGET_SALT = "wadsworth-widget-v1"

def _make_widget_token(player_id: int) -> str:
    import hmac as _hmac, hashlib as _hl
    mac = _hmac.new(_WIDGET_SALT.encode(), str(player_id).encode(), _hl.sha256).hexdigest()
    return f"{player_id}:{mac}"

def _verify_widget_token(token: str):
    """Return Player for a valid widget token, None otherwise."""
    try:
        import hmac as _hmac, hashlib as _hl
        pid_str, mac = token.split(":", 1)
        pid = int(pid_str)
        expected = _hmac.new(_WIDGET_SALT.encode(), str(pid).encode(), _hl.sha256).hexdigest()
        if not _hmac.compare_digest(mac, expected):
            return None
        import auth as _auth
        from auth import Player as _Player
        db = _auth.get_db()
        player = db.query(_Player).filter_by(id=pid).first()
        db.close()
        return player
    except Exception:
        return None

@router.get("/api/widget/token")
def api_widget_token(session_token: Optional[str] = Cookie(None)):
    """Return a stable HMAC widget token for the authenticated player."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return JSONResponse({"error": "not authenticated"}, status_code=401)
    return JSONResponse({"token": _make_widget_token(player.id), "player_id": player.id})

_WIDGET_DEVICE_MAP: dict = {}  # device_hash → player_id, in-memory (survives restarts via file)
import os as _os
_WIDGET_DEVICE_FILE = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "widget_devices.json")

def _load_device_map():
    global _WIDGET_DEVICE_MAP
    import json as _json
    if _os.path.exists(_WIDGET_DEVICE_FILE):
        try:
            with open(_WIDGET_DEVICE_FILE) as _f:
                _WIDGET_DEVICE_MAP = _json.load(_f)
        except Exception:
            pass

def _save_device_map():
    import json as _json
    try:
        with open(_WIDGET_DEVICE_FILE, 'w') as _f:
            _json.dump(_WIDGET_DEVICE_MAP, _f)
    except Exception as _e:
        print(f"[widget] Failed to save device map: {_e}")

_load_device_map()

@router.get("/api/widget/link")
def api_widget_link(device_id: str, session_token: Optional[str] = Cookie(None)):
    """Called by the web app with the device hash appended by LauncherActivity."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return JSONResponse({"error": "not authenticated"}, status_code=401)
    _WIDGET_DEVICE_MAP[device_id] = player.id
    _save_device_map()
    print(f"[widget] Linked device {device_id[:12]}… → player {player.id} ({player.business_name})")
    return JSONResponse({"ok": True})


@router.get("/api/widget/status")
def api_widget_status(device_id: Optional[str] = None,
                      session_token: Optional[str] = Cookie(None)):
    """Return whether the given device_id is linked to any player account."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return JSONResponse({"error": "not authenticated"}, status_code=401)
    if not device_id:
        return JSONResponse({"linked": False, "reason": "no device_id"})
    pid = _WIDGET_DEVICE_MAP.get(device_id)
    if not pid:
        _load_device_map()
        pid = _WIDGET_DEVICE_MAP.get(device_id)
    linked = pid == player.id
    return JSONResponse({"linked": linked, "player_id": pid})

@router.get("/api/widget/data")
def api_widget_data(request: Request, session_token: Optional[str] = Cookie(None),
                    wt: Optional[str] = None,
                    device_id: Optional[str] = None):
    """
    Returns live market data for the PWA widget and the in-page ticker bar.
    Shape:
      { balance, last_alert, last_alert_time,
        tickers: [...],  indices: [...], stocks: [...], bonds: [...], memes: [...] }
    Each ticker item: { label, value, change, up, type }
    """
    from datetime import datetime as _dt
    print(f"[widget/data] device_id={device_id!r} ua={request.headers.get('user-agent','')[:60]!r}", flush=True)

    # Auth: device_id (Android widget) > wt (legacy HMAC token) > session cookie
    if device_id:
        pid = _WIDGET_DEVICE_MAP.get(device_id)
        if not pid:
            # Reload from file in case another worker wrote the link after our last load
            _load_device_map()
            pid = _WIDGET_DEVICE_MAP.get(device_id)
        if not pid:
            return JSONResponse({"error": "not authenticated"}, status_code=401)
        import auth as _auth
        db = _auth.get_db()
        try:
            player = db.query(_auth.Player).filter(_auth.Player.id == pid).first()
        finally:
            db.close()
        if not player:
            return JSONResponse({"error": "not authenticated"}, status_code=401)
    elif wt:
        player = _verify_widget_token(wt)
        if not player:
            return JSONResponse({"error": "not authenticated"}, status_code=401)
    else:
        player = require_auth(session_token)
        if isinstance(player, RedirectResponse):
            return JSONResponse({"error": "not authenticated"}, status_code=401)

    def _ago(dt):
        if not dt:
            return ""
        s = (_dt.utcnow() - dt).total_seconds()
        if s < 60:   return "just now"
        if s < 3600: return f"{int(s/60)}m ago"
        if s < 86400:return f"{int(s/3600)}h ago"
        return f"{int(s/86400)}d ago"

    from reserve_banks import get_player_display_currency, fmt_usd
    _disp = get_player_display_currency(player.id)

    def _url_for_tx_type(tx_type: str) -> str:
        t = (tx_type or "").lower()
        if "brokerage" in t or "stock" in t or "ipo" in t or "etf" in t or "short" in t: return "/brokerage"
        if "market" in t or "commodity" in t: return "/market"
        if "land" in t or "real_estate" in t or "real estate" in t: return "/land"
        if "bank" in t or "loan" in t or "banking" in t: return "/banks"
        if "executive" in t or "exec" in t: return "/executives"
        if "dm" in t or "direct_message" in t or "message" in t: return "/dm"
        if "contract" in t or "p2p" in t or "trust" in t: return "/p2p"
        if "city" in t: return "/cities"
        if "county" in t: return "/counties"
        if "reserve" in t or "bond" in t or "forex" in t: return "/reserve-banks"
        if "memecoin" in t or "meme" in t: return "/memecoins"
        if "business" in t or "production" in t or "retail" in t or "inventory" in t: return "/businesses"
        if "estate" in t or "will" in t or "inheritance" in t: return "/estate"
        return "/stats"

    # Resolve balance the same way shell() does: use PlayerCurrencyBalance,
    # not the legacy player.cash_balance column (which may be 0 / stale).
    try:
        from reserve_banks import (get_usd_balance as _get_usd_bal,
                                   get_player_legal_tender as _get_tender,
                                   get_player_currency_balances as _get_balances)
        _tender = _get_tender(player.id)
        if _tender == "USD":
            _bal_str = fmt_usd(_get_usd_bal(player.id), _disp, precision=2)
        else:
            _bal_str = fmt_usd(_get_usd_bal(player.id), _disp, precision=2)  # fallback
            for _b in _get_balances(player.id):
                if _b["currency_code"] == _tender:
                    _bal_str = f"{_b['currency_symbol']}{_b['balance']:,.2f}\u00a0{_tender}"
                    break
    except Exception:
        _bal_str = fmt_usd(player.cash_balance or 0.0, _disp, precision=2)

    result = {
        "balance": _bal_str,
        "last_alert": "No recent activity",
        "last_alert_time": "",
        "last_alert_url": "/stats",
        "open_url": "/",
        "notifications": [],
        "tickers": [], "indices": [], "stocks": [], "bonds": [], "memes": [],
    }

    try:
        from database import SessionLocal, ReserveSessionLocal
        from stats_ux import TransactionLog
        from banks.indices import IndexSnapshot
        from banks.brokerage_firm import CompanyShares
        from memecoins import MemeCoin
        from reserve_banks import StateReserveBank

        db = SessionLocal()
        try:
            # ── Last 10 transactions as notifications ─────────────────────────
            txs = (db.query(TransactionLog)
                     .filter(TransactionLog.player_id == player.id)
                     .order_by(TransactionLog.timestamp.desc())
                     .limit(10).all())
            if txs:
                result["last_alert"] = (txs[0].description or txs[0].transaction_type or "")[:80]
                result["last_alert_time"] = _ago(txs[0].timestamp)
                result["last_alert_url"] = _url_for_tx_type(txs[0].transaction_type)
                result["notifications"] = [
                    {
                        "text": (t.description or t.transaction_type or "")[:60],
                        "time": _ago(t.timestamp),
                        "amount": fmt_usd(t.amount, _disp, precision=0) if t.amount else "",
                        "positive": (t.amount or 0) >= 0,
                    }
                    for t in txs
                ]

            # ── Indices ───────────────────────────────────────────────────────
            INDEX_CODES = ["WBC50","GLVI","CCC","EPI","CDI","REGI","BEE","WEI","GPI","SEED"]
            for code in INDEX_CODES:
                snap = (db.query(IndexSnapshot)
                          .filter(IndexSnapshot.index_code == code)
                          .order_by(IndexSnapshot.timestamp.desc())
                          .first())
                if not snap:
                    continue
                prev = (db.query(IndexSnapshot)
                          .filter(IndexSnapshot.index_code == code,
                                  IndexSnapshot.timestamp < snap.timestamp)
                          .order_by(IndexSnapshot.timestamp.desc())
                          .first())
                change, up = "", None
                if prev and prev.value:
                    pct   = (snap.value - prev.value) / prev.value * 100
                    change = f"{'+'if pct>=0 else ''}{pct:.2f}%"
                    up     = pct >= 0
                entry = {"label": code.replace("WBC50","WBC-50"),
                         "value": f"{snap.value:,.2f}",
                         "change": change, "up": up, "type": "index"}
                result["indices"].append(entry)
                result["tickers"].append(entry)

            # ── Stocks — top 10 by today's volume ────────────────────────────
            for s in (db.query(CompanyShares)
                        .filter(CompanyShares.current_price > 0)
                        .order_by(CompanyShares.volume_today.desc())
                        .limit(10).all()):
                ref = s.ipo_price or s.current_price
                pct = (s.current_price - ref) / ref * 100 if ref else 0
                entry = {"label": s.ticker_symbol,
                         "value": f"${s.current_price:,.2f}",
                         "change": f"{'+'if pct>=0 else ''}{pct:.2f}%",
                         "up": pct >= 0, "type": "stock"}
                result["stocks"].append(entry)
                result["tickers"].append(entry)

            # ── Memecoins ─────────────────────────────────────────────────────
            for m in (db.query(MemeCoin)
                        .filter(MemeCoin.is_active == True, MemeCoin.last_price > 0)
                        .order_by(MemeCoin.total_volume_native.desc())
                        .all()):
                entry = {"label": m.symbol,
                         "value": f"{m.last_price:.6g}",
                         "change": "", "up": None, "type": "meme"}
                result["memes"].append(entry)
                result["tickers"].append(entry)

        finally:
            db.close()

        # ── Bond yields (reserve DB) ──────────────────────────────────────────
        r_db = ReserveSessionLocal()
        try:
            for b in (r_db.query(StateReserveBank)
                         .filter(StateReserveBank.currency_code.in_(
                             ["USD","EUR","GBP","JPY","CNY","BRL","INR"]))
                         .all()):
                entry = {"label": b.currency_code,
                         "value": f"{b.yield_rate*100:.2f}%",
                         "change": "", "up": None, "type": "bond"}
                result["bonds"].append(entry)
                result["tickers"].append(entry)
        finally:
            r_db.close()

    except Exception as _e:
        print(f"[widget/data] error: {_e}")

    # Land restoration status for Android widget
    try:
        from land_restoration import get_active_restoration as _get_ar
        _ar = _get_ar(player.id)
        if _ar:
            _now2   = _dt.utcnow()
            _tot_s  = max(1.0, (_ar.completes_at - _ar.started_at).total_seconds())
            _elap   = (_now2 - _ar.started_at).total_seconds()
            _pct    = min(100.0, _elap / _tot_s * 100)
            _rem_s  = max(0.0, (_ar.completes_at - _now2).total_seconds())
            _d      = int(_rem_s // 86400)
            _h      = int((_rem_s % 86400) // 3600)
            _rem_str = f"{_d}d {_h}h" if _d else f"{_h}h {int((_rem_s%3600)//60)}m"
            result["restoration"] = {
                "active":       True,
                "progress_pct": round(_pct, 1),
                "completes_at": _ar.completes_at.isoformat(),
                "completes_in": _rem_str,
            }
        else:
            result["restoration"] = {"active": False}
    except Exception:
        result["restoration"] = {"active": False}

    return JSONResponse(result)


@router.get("/api/widget/wbc50")
def api_widget_wbc50(device_id: Optional[str] = None,
                     session_token: Optional[str] = Cookie(None)):
    """WBC-50 index value, 7-day sparkline, and top-5 constituents."""
    if device_id:
        pid = _WIDGET_DEVICE_MAP.get(device_id)
        if not pid:
            _load_device_map()
            pid = _WIDGET_DEVICE_MAP.get(device_id)
        if not pid:
            return JSONResponse({"error": "not authenticated"}, status_code=401)
        import auth as _auth
        _db = _auth.get_db()
        try:
            player = _db.query(_auth.Player).filter(_auth.Player.id == pid).first()
        finally:
            _db.close()
        if not player:
            return JSONResponse({"error": "not authenticated"}, status_code=401)
    else:
        player = require_auth(session_token)
        if isinstance(player, RedirectResponse):
            return JSONResponse({"error": "not authenticated"}, status_code=401)

    from banks.indices import _get_latest, _get_history
    from banks.wbc50_index_fund import get_wbc50_constituents

    # Current value + 24h change
    latest = _get_latest("WBC50")
    current = latest.value if latest else 0.0

    history_24h = _get_history("WBC50", days=1)
    prev_24h = history_24h[0].value if history_24h else current
    change_pct = ((current - prev_24h) / prev_24h * 100) if prev_24h else 0.0

    # 7-day sparkline using Unicode block chars
    history_7d = _get_history("WBC50", days=7)
    BLOCKS = " \u2581\u2582\u2583\u2584\u2585\u2586\u2587\u2588"
    sparkline = ""
    if len(history_7d) >= 2:
        vals = [s.value for s in history_7d]
        lo, hi = min(vals), max(vals)
        rng = hi - lo or 1
        sparkline = "".join(BLOCKS[min(8, int((v - lo) / rng * 8) + 1)] for v in vals[-40:])

    # Top 5 by market cap
    constituents = get_wbc50_constituents()[:5]
    top5 = [{"name": c.company_name, "price": f"${c.current_price:,.2f}"} for c in constituents]

    return JSONResponse({
        "value":      f"${current:,.2f}",
        "change_pct": f"{'+'if change_pct>=0 else ''}{change_pct:.2f}%",
        "up":         change_pct >= 0,
        "sparkline":  sparkline,
        "top5":       top5,
    })


@router.get("/api/widget/chat")
def api_widget_chat(room: str = "global",
                    device_id: Optional[str] = None,
                    session_token: Optional[str] = Cookie(None)):
    """Last 6 chat messages for the home-screen chat widgets."""
    if room not in ("global", "trade", "qa"):
        return JSONResponse({"error": "invalid room"}, status_code=400)

    # Auth — same pattern as api_widget_data
    if device_id:
        pid = _WIDGET_DEVICE_MAP.get(device_id)
        if not pid:
            _load_device_map()
            pid = _WIDGET_DEVICE_MAP.get(device_id)
        if not pid:
            return JSONResponse({"error": "not authenticated"}, status_code=401)
        import auth as _auth
        _db = _auth.get_db()
        try:
            player = _db.query(_auth.Player).filter(_auth.Player.id == pid).first()
        finally:
            _db.close()
        if not player:
            return JSONResponse({"error": "not authenticated"}, status_code=401)
    else:
        player = require_auth(session_token)
        if isinstance(player, RedirectResponse):
            return JSONResponse({"error": "not authenticated"}, status_code=401)

    from chat import get_room_messages
    from datetime import datetime as _dt

    def _ago(iso):
        if not iso:
            return ""
        try:
            s = (_dt.utcnow() - _dt.fromisoformat(iso)).total_seconds()
            if s < 60:    return "just now"
            if s < 3600:  return f"{int(s/60)}m ago"
            if s < 86400: return f"{int(s/3600)}h ago"
            return f"{int(s/86400)}d ago"
        except Exception:
            return ""

    msgs = get_room_messages(room, limit=25)
    return JSONResponse({
        "room": room,
        "messages": [
            {
                "sender": m["sender_name"],
                "text":   m["content"],
                "time":   _ago(m.get("timestamp")),
            }
            for m in reversed(msgs)
            if m.get("message_type", "chat") == "chat"
        ]
    })


@router.get("/api/widget/bonds")
def api_widget_bonds(device_id: Optional[str] = None,
                     session_token: Optional[str] = Cookie(None)):
    """Live bond yields + 24-hour sparkline for all reserve-bank currencies."""
    if device_id:
        pid = _WIDGET_DEVICE_MAP.get(device_id)
        if not pid:
            _load_device_map()
            pid = _WIDGET_DEVICE_MAP.get(device_id)
        if not pid:
            return JSONResponse({"error": "not authenticated"}, status_code=401)
    else:
        player = require_auth(session_token)
        if isinstance(player, RedirectResponse):
            return JSONResponse({"error": "not authenticated"}, status_code=401)

    from database import ReserveSessionLocal
    from reserve_banks import StateReserveBank, BondYieldHistory

    BLOCKS = " \u2581\u2582\u2583\u2584\u2585\u2586\u2587\u2588"

    def _spark(rows_desc):
        vals = [r.yield_rate for r in reversed(rows_desc)]
        if len(vals) < 2:
            return ""
        lo, hi = min(vals), max(vals)
        rng = hi - lo or 0.0001
        return "".join(BLOCKS[min(8, int((v - lo) / rng * 8) + 1)] for v in vals[-24:])

    r_db = ReserveSessionLocal()
    try:
        banks = r_db.query(StateReserveBank).order_by(StateReserveBank.currency_code).all()
        rates = []
        for b in banks:
            hist = (r_db.query(BondYieldHistory)
                       .filter(BondYieldHistory.bank_id == b.id)
                       .order_by(BondYieldHistory.recorded_at.desc())
                       .limit(24).all())
            prev_yield = hist[-1].yield_rate if len(hist) >= 2 else b.yield_rate
            change = b.yield_rate - prev_yield
            rates.append({
                "code":      b.currency_code,
                "name":      b.currency_name,
                "symbol":    b.currency_symbol,
                "flag":      b.flag_emoji,
                "yield_pct": round(b.yield_rate * 100, 3),
                "change_bp": round(change * 10000, 1),
                "up":        change >= 0,
                "sparkline": _spark(hist),
                "min_pct":   round(b.min_yield * 100, 2),
                "max_pct":   round(b.max_yield * 100, 2),
            })
    finally:
        r_db.close()

    return JSONResponse({"rates": rates})


@router.get("/api/widget/forex")
def api_widget_forex(device_id: Optional[str] = None,
                     session_token: Optional[str] = Cookie(None)):
    """Live FX rates (usd_per_unit) for all reserve-bank currencies with 24h change."""
    if device_id:
        pid = _WIDGET_DEVICE_MAP.get(device_id)
        if not pid:
            _load_device_map()
            pid = _WIDGET_DEVICE_MAP.get(device_id)
        if not pid:
            return JSONResponse({"error": "not authenticated"}, status_code=401)
    else:
        player = require_auth(session_token)
        if isinstance(player, RedirectResponse):
            return JSONResponse({"error": "not authenticated"}, status_code=401)

    from database import ReserveSessionLocal
    from reserve_banks import StateReserveBank, BondYieldHistory

    BLOCKS = " \u2581\u2582\u2583\u2584\u2585\u2586\u2587\u2588"

    def _fx_spark(rows_desc):
        vals = [r.usd_per_unit for r in reversed(rows_desc)]
        if len(vals) < 2:
            return ""
        lo, hi = min(vals), max(vals)
        rng = hi - lo or 0.000001
        return "".join(BLOCKS[min(8, int((v - lo) / rng * 8) + 1)] for v in vals[-24:])

    r_db = ReserveSessionLocal()
    try:
        banks = r_db.query(StateReserveBank).order_by(StateReserveBank.currency_code).all()
        pairs = []
        for b in banks:
            hist = (r_db.query(BondYieldHistory)
                       .filter(BondYieldHistory.bank_id == b.id)
                       .order_by(BondYieldHistory.recorded_at.desc())
                       .limit(24).all())
            prev_fx = hist[-1].usd_per_unit if len(hist) >= 2 else b.usd_per_unit
            pct = ((b.usd_per_unit - prev_fx) / prev_fx * 100) if prev_fx else 0.0
            # For display: show units-per-USD for non-USD (easier to read, e.g. ¥149.25/$)
            if b.currency_code == "USD":
                rate_str = "1.0000"
                units_str = "1 USD"
            elif b.usd_per_unit > 0:
                per_usd = 1.0 / b.usd_per_unit
                rate_str = f"{per_usd:,.4f}" if per_usd < 1000 else f"{per_usd:,.2f}"
                units_str = f"{b.currency_symbol}{rate_str}/$"
            else:
                rate_str = "—"
                units_str = "—"
            pairs.append({
                "code":      b.currency_code,
                "name":      b.currency_name,
                "symbol":    b.currency_symbol,
                "flag":      b.flag_emoji,
                "rate_str":  rate_str,
                "units_str": units_str,
                "usd_per_unit": round(b.usd_per_unit, 8),
                "change_pct": round(pct, 3),
                "up":        pct >= 0,
                "sparkline": _fx_spark(hist),
            })
    finally:
        r_db.close()

    return JSONResponse({"pairs": pairs})



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


# ==========================
# QUICK BUY
# ==========================

def _quick_buy_simulate(item_type: str, quantity: float) -> dict:
    """Walk the ask side of the order book and simulate fills. Read-only."""
    from market import MarketOrder, OrderType, OrderStatus, Trade
    from database import SessionLocal
    db = SessionLocal()
    try:
        asks = (db.query(MarketOrder)
                .filter(
                    MarketOrder.order_type == OrderType.SELL,
                    MarketOrder.status.in_([OrderStatus.ACTIVE, OrderStatus.PARTIALLY_FILLED]),
                    MarketOrder.item_type  == item_type,
                )
                .order_by(MarketOrder.price.asc())
                .all())

        fills      = []
        remaining  = float(quantity)
        total_cost = 0.0

        for ask in asks:
            if remaining <= 0:
                break
            avail = ask.quantity - ask.quantity_filled
            if avail <= 0:
                continue
            fill_qty = min(remaining, avail)
            cost     = fill_qty * ask.price
            # Aggregate fills at the same price level
            if fills and fills[-1]["price_usd"] == ask.price:
                fills[-1]["qty"]     += fill_qty
                fills[-1]["cost_usd"] += cost
            else:
                fills.append({"qty": fill_qty, "price_usd": ask.price, "cost_usd": cost})
            total_cost += cost
            remaining  -= fill_qty

        total_filled = float(quantity) - remaining
        avg_price    = (total_cost / total_filled) if total_filled > 0 else 0.0
        last_price   = fills[-1]["price_usd"] if fills else None

        if last_price:
            suggested_cap = round(last_price * 1.10, 8)
        else:
            last_trade = (db.query(Trade)
                          .filter(Trade.item_type == item_type)
                          .order_by(Trade.executed_at.desc())
                          .first())
            suggested_cap = round(last_trade.price * 1.10, 8) if last_trade else None

        return {
            "fills":             fills,
            "total_filled":      total_filled,
            "total_cost_usd":    total_cost,
            "avg_price_usd":     avg_price,
            "unfilled_qty":      remaining,
            "suggested_cap_usd": suggested_cap,
        }
    finally:
        db.close()


@router.get("/api/market/quick-buy/preview")
async def quick_buy_preview(
    item_type:  str            = Query(...),
    quantity:   float          = Query(...),
    cap_price:  Optional[float] = Query(None),
    session_token: Optional[str] = Cookie(None),
):
    """Read-only order book simulation for the quick buy panel."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    if quantity <= 0:
        return JSONResponse({"error": "Quantity must be positive"})

    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)

    try:
        sim = _quick_buy_simulate(item_type, quantity)
    except Exception as e:
        return JSONResponse({"error": f"Preview failed: {e}"})

    fills_disp = [
        {
            "qty":        f["qty"],
            "price_disp": fmt_usd(f["price_usd"], disp, precision=4),
            "cost_disp":  fmt_usd(f["cost_usd"],  disp),
        }
        for f in sim["fills"]
    ]

    sc_usd  = sim["suggested_cap_usd"]
    # User-supplied cap (in display currency) → USD for reservation calc
    if cap_price is not None:
        active_cap_usd = cap_price * disp["usd_per_unit"]
    elif sc_usd:
        active_cap_usd = sc_usd
    else:
        active_cap_usd = None

    forex_fee_usd = sim["total_cost_usd"] * 0.002 if disp["code"] != "USD" else 0.0
    immediate_usd = sim["total_cost_usd"] + forex_fee_usd

    max_reservation_usd = (
        sim["unfilled_qty"] * active_cap_usd
        if (active_cap_usd and sim["unfilled_qty"] > 0) else 0.0
    )

    # Raw display-currency cap (unformatted number) for use as form value
    sc_raw_disp = round(sc_usd / disp["usd_per_unit"], 6) if sc_usd else None

    return JSONResponse({
        "fills":               fills_disp,
        "total_filled":        sim["total_filled"],
        "avg_price_disp":      fmt_usd(sim["avg_price_usd"], disp, precision=4) if sim["avg_price_usd"] else None,
        "immediate_cost_disp": fmt_usd(immediate_usd, disp) if sim["total_filled"] > 0 else None,
        "unfilled_qty":        sim["unfilled_qty"],
        "suggested_cap_disp":  fmt_usd(sc_usd, disp, precision=4) if sc_usd else None,
        "suggested_cap_raw":   sc_raw_disp,
        "reservation_disp":    fmt_usd(max_reservation_usd, disp) if max_reservation_usd > 0 else None,
        "forex_fee_disp":      fmt_usd(forex_fee_usd, disp) if forex_fee_usd > 0 else None,
    })


@router.post("/api/market/quick-buy/execute")
async def quick_buy_execute(
    item_type:   str   = Form(...),
    quantity:    float = Form(...),
    cap_price:   float = Form(...),   # in player's display currency
    session_token: Optional[str] = Cookie(None),
):
    """Place a limit buy order at cap_price (display currency) for the given item."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return JSONResponse({"ok": False, "error": "Not authenticated"}, status_code=401)
    if quantity <= 0 or cap_price <= 0:
        return JSONResponse({"ok": False, "error": "Invalid quantity or price"})

    from reserve_banks import get_player_display_currency, fmt_usd
    from market import create_order, OrderType, OrderMode
    disp    = get_player_display_currency(player.id)
    cap_usd = cap_price * disp["usd_per_unit"]

    try:
        create_order(player.id, OrderType.BUY, OrderMode.LIMIT, item_type, quantity, cap_usd)
        iname = item_type.replace("_", " ").title()
        return JSONResponse({
            "ok":      True,
            "message": f"Order placed: {quantity:,.0f}× {iname} @ {fmt_usd(cap_usd, disp)} cap",
        })
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)})


@router.get("/api/market/quick-buy/stock-plan")
async def quick_buy_stock_plan(
    business_id: int             = Query(...),
    n_cycles:    float           = Query(5.0),
    session_token: Optional[str] = Cookie(None),
):
    """Return HTML fragment listing input deficits for n_cycles of production."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    if n_cycles <= 0:
        return JSONResponse({"error": "n_cycles must be positive"})

    from business import Business, BUSINESS_TYPES, get_district_business_types
    from land import get_db as get_land_db
    from reserve_banks import get_player_display_currency, fmt_usd
    from inventory import get_inventory
    import json as _json

    disp    = get_player_display_currency(player.id)
    land_db = get_land_db()
    try:
        biz = (land_db.query(Business)
               .filter(Business.id == business_id, Business.owner_id == player.id)
               .first())
        if not biz:
            return JSONResponse({"error": "Business not found"})

        all_types = {**BUSINESS_TYPES, **get_district_business_types()}
        config    = all_types.get(biz.business_type, {})
        if config.get("class") != "production":
            return JSONResponse({"error": "Not a production business"})

        paused_line_idxs = set(_json.loads(biz.paused_lines or "[]"))
        inv = get_inventory(player.id)

        # Sum inputs × n_cycles across all non-paused lines
        needed: dict = {}
        for li, line in enumerate(config.get("production_lines", [])):
            if li in paused_line_idxs:
                continue
            for req in line.get("inputs", []):
                item = req["item"]
                needed[item] = needed.get(item, 0.0) + req["quantity"] * n_cycles

        # Compute deficits
        deficits = {}
        for item, total_needed in needed.items():
            have    = float(inv.get(item, 0))
            deficit = total_needed - have
            if deficit > 0:
                deficits[item] = {"needed": total_needed, "have": have, "deficit": deficit}

        if not deficits:
            return JSONResponse({
                "html": (f'<div style="color:#22c55e;font-size:0.8rem;padding:6px 0;">'
                         f'All inputs stocked for {n_cycles:g} cycles. Nothing to buy.</div>')
            })

        parts = []
        for item in sorted(deficits, key=lambda x: -deficits[x]["deficit"]):
            d     = deficits[item]
            iname = item.replace("_", " ").title()
            safe  = item.replace("'", "").replace('"', "")
            pid   = f"qbp-sp-{biz.id}-{safe}"
            dqty  = max(1, int(d["deficit"]))
            try:
                sim      = _quick_buy_simulate(item, d["deficit"])
                cost_str = fmt_usd(sim["total_cost_usd"], disp) if sim["total_cost_usd"] > 0 else "—"
            except Exception:
                cost_str = "?"

            qb_panel_html = (
                f'<div class="qb-panel" id="{pid}" data-item="{item}">'
                f'<div style="font-size:0.72rem;color:#64748b;margin-bottom:8px;">Quick Buy: '
                f'<b style="color:#e2e8f0;">{iname}</b></div>'
                f'<div style="display:flex;gap:8px;flex-wrap:wrap;align-items:flex-end;">'
                f'<div><div style="font-size:0.65rem;color:#64748b;margin-bottom:2px;">Quantity</div>'
                f'<input type="number" class="qb-input qb-qty" value="{dqty}" min="1" step="1" oninput="qbSchedule(this)"></div>'
                f'<div><div style="font-size:0.65rem;color:#64748b;margin-bottom:2px;">Cap price ({disp["code"]})</div>'
                f'<input type="number" class="qb-input qb-cap" min="0.000001" step="any" placeholder="auto" oninput="qbSchedule(this)"></div>'
                f'</div>'
                f'<div class="qb-preview" style="margin-top:8px;min-height:30px;"></div>'
                f'<form method="post" action="/api/market/quick-buy/execute" style="margin-top:8px;" onsubmit="return qbSubmit(this)">'
                f'<input type="hidden" name="item_type" value="{item}">'
                f'<input type="hidden" name="quantity" value="{dqty}">'
                f'<input type="hidden" name="cap_price" value="">'
                f'<div style="display:flex;gap:6px;">'
                f'<button type="submit" class="btn-sm btn-sm-blue" style="font-size:0.7rem;">Confirm Buy</button>'
                f'<button type="button" class="btn-sm" style="background:#1e293b;color:#94a3b8;font-size:0.7rem;"'
                f' onclick="document.getElementById(\'{pid}\').style.display=\'none\'">Cancel</button>'
                f'</div></form></div>'
            )

            parts.append(
                f'<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;'
                f'padding:5px 0;border-bottom:1px solid #1e293b;">'
                f'<span style="font-size:0.8rem;flex:1;color:#e2e8f0;">{iname}</span>'
                f'<span style="font-size:0.7rem;color:#94a3b8;">{d["have"]:,.0f} / {d["needed"]:,.0f}</span>'
                f'<span style="font-size:0.7rem;color:#f59e0b;">need {d["deficit"]:,.0f} more</span>'
                f'<span style="font-size:0.7rem;color:#64748b;">~{cost_str}</span>'
                f'<button type="button" class="btn-sm btn-sm-blue" style="font-size:0.68rem;padding:2px 6px;"'
                f' onclick="qbToggle(\'{pid}\')">Buy</button>'
                f'</div>{qb_panel_html}'
            )

        return JSONResponse({"html": "".join(parts)})
    finally:
        land_db.close()


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
    # ETF/fund shares trade exclusively on the ETF Trading Floor.
    if item_type.endswith("_shares"):
        return RedirectResponse(url="/brokerage/trading?mode=etf", status_code=303)
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
    order = market.create_order(
        player.id,
        market.OrderType.BUY if order_type == "buy" else market.OrderType.SELL,
        market.OrderMode.LIMIT,
        item_type,
        quantity,
        price_usd
    )
    if order is None:
        # Order was rejected — figure out why and surface a clear error
        import inventory as _inv
        import urllib.parse
        if order_type == "sell":
            held = _inv.get_item_quantity(player.id, item_type)
            item_label = item_type.replace("_", " ").title()
            err = f"Order rejected: you have {held:,.4g} {item_label} but tried to sell {quantity:,.4g}."
        else:
            from reserve_banks import get_player_cash_balance
            bal = get_player_cash_balance(player.id)
            err = f"Order rejected: insufficient funds (balance {bal:,.2f}, cost ≈ {quantity * price_usd:,.2f})."
        return RedirectResponse(url=f"/market?item={item_type}&order_err={urllib.parse.quote(err)}", status_code=303)
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
    fund:       str   = Form(""),
    session_token: Optional[str] = Cookie(None),
):
    """Place a limit order for an ETF fund share via the ETF Trading Floor."""
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
    fund_param = f"&fund={fund}" if fund else ""
    return RedirectResponse(url=f"/brokerage/trading?mode=etf{fund_param}", status_code=303)


@router.post("/api/brokerage/cancel-etf-order")
async def brokerage_cancel_etf_order(
    order_id: int = Form(...),
    fund:     str = Form(""),
    session_token: Optional[str] = Cookie(None),
):
    """Cancel an open ETF market order and return to the ETF trading floor."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    import market
    market.cancel_order(order_id, player.id)
    fund_param = f"&fund={fund}" if fund else ""
    return RedirectResponse(url=f"/brokerage/trading?mode=etf{fund_param}", status_code=303)


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
# EVENTS PAGE
# ==========================

@router.get("/events", response_class=HTMLResponse)
def events_page(request: Request,
                session_token: Optional[str] = Cookie(None),
                success: Optional[str] = Query(None),
                error:   Optional[str] = Query(None)):
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player

    # Same TWA detection as the dashboard so navigating directly to /events also counts.
    if request.headers.get("X-Requested-With", "") == "cc.notifly.wadsworth.twa":
        try:
            from beta import handle_twa_login
            handle_twa_login(player.id)
        except Exception:
            pass

    _flash_html = ""
    if success:
        _flash_html = f'<div style="background:#052e16;border:1px solid #15803d;border-radius:6px;padding:10px 16px;margin-bottom:18px;color:#4ade80;font-size:0.85rem;">✓ {success}</div>'
    elif error:
        _flash_html = f'<div style="background:#1c0505;border:1px solid #b91c1c;border-radius:6px;padding:10px 16px;margin-bottom:18px;color:#f87171;font-size:0.85rem;">✗ {error}</div>'

    try:
        from events import get_event_summary, get_player_level, get_player_task_progress_map
        _ev  = get_event_summary()
        _lvl = get_player_level(player.id)
    except Exception:
        _ev  = {"active": [], "upcoming": [], "finished": []}
        _lvl = {"level": 1, "trophies": 0, "next_threshold": None,
                "prev_threshold": 0, "progress_pct": 0.0}

    _BETA_TITLES = {"Founding Operative", "Pocket Empire", "Active Duty"}
    _active   = [e for e in _ev.get("active",   []) if e.get("title") not in _BETA_TITLES]
    _upcoming = [e for e in _ev.get("upcoming", []) if e.get("title") not in _BETA_TITLES]
    _finished = [e for e in _ev.get("finished", []) if e.get("title") not in _BETA_TITLES]

    # Fetch player task progress for all task-type events in one query
    _task_event_ids = [e["id"] for e in _active + _upcoming + _finished if e.get("event_type") == "task"]
    try:
        _prog_map = get_player_task_progress_map(player.id, _task_event_ids)
    except Exception:
        _prog_map = {}

    _TYPE_COLOR = {
        "gov":        "#94a3b8",
        "bank":       "#fbbf24",
        "market":     "#34d399",
        "task":       "#a78bfa",
        "city":       "#38bdf8",
        "production": "#fb923c",
    }
    _DUR_COLOR = {
        "daily":   "#f59e0b",
        "weekly":  "#10b981",
        "monthly": "#6366f1",
        "special": "#ec4899",
        "task":    "#a78bfa",
    }

    def _badge(label, color):
        return (f"<span style='background:{color}22;color:{color};border:1px solid {color}44;"
                f"border-radius:3px;padding:1px 7px;font-size:0.65rem;font-weight:700;"
                f"text-transform:uppercase;letter-spacing:.05em;white-space:nowrap;'>{label}</span>")

    def _ev_card(ev, status_label, status_color):
        dur    = ev.get("duration_class", "")
        etype  = ev.get("event_type", "")
        title  = ev.get("title", "Untitled")
        desc   = ev.get("description", "") or ""
        ends   = ev.get("ends_at")
        starts = ev.get("starts_at")
        trophy = ev.get("trophy_reward", 0)
        from datetime import datetime as _dt
        _now = _dt.utcnow()
        time_str = ""
        try:
            if ends:
                _end = _dt.fromisoformat(ends.replace("Z", ""))
                delta = _end - _now
                if delta.total_seconds() > 0:
                    h, rem = divmod(int(delta.total_seconds()), 3600)
                    m = rem // 60
                    time_str = f"Ends in {h}h {m}m"
                else:
                    time_str = "Ended"
            elif starts:
                _st = _dt.fromisoformat(starts.replace("Z", ""))
                delta = _st - _now
                if delta.total_seconds() > 0:
                    h, rem = divmod(int(delta.total_seconds()), 3600)
                    m = rem // 60
                    time_str = f"Starts in {h}h {m}m"
        except Exception:
            pass
        trophy_html = (f"<span style='color:#fbbf24;font-weight:700;'>+{trophy} ★</span>" if trophy else "")

        # Progress bar for tasks with a numeric target; completion badge for all other tasks
        progress_html = ""
        if etype == "task":
            ev_prog = _prog_map.get(ev.get("id"), {})
            done    = ev_prog.get("completed", False)
            target  = ev.get("task_target") or 0
            current = ev_prog.get("progress", 0.0)
            if target > 0:
                pct       = min(current / target * 100, 100)
                bar_color = "#4ade80" if done else "#a78bfa"
                metric    = ev.get("task_metric", "") or ""
                is_usd    = "_usd" in metric
                def _fmt(v):
                    if is_usd:
                        return f"${v:,.0f}" if v >= 1 else f"${v:,.2f}"
                    return f"{v:,.2f}"
                label_text = (
                    f'<span style="color:#4ade80;font-weight:700;">✓ Complete!</span>'
                    if done else
                    f'<span style="color:#a78bfa;">{_fmt(current)}</span>'
                    f'<span style="color:#475569;"> / {_fmt(target)}</span>'
                )
                progress_html = f"""
                <div style="margin-top:10px;">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
                        <span style="font-size:0.72rem;color:#64748b;text-transform:uppercase;letter-spacing:.05em;">Progress</span>
                        <span style="font-size:0.78rem;">{label_text}</span>
                    </div>
                    <div style="background:#1e293b;border-radius:4px;height:6px;overflow:hidden;">
                        <div style="background:{bar_color};height:100%;width:{pct:.1f}%;border-radius:4px;transition:width 0.4s;"></div>
                    </div>
                    <div style="color:#475569;font-size:0.68rem;margin-top:3px;text-align:right;">{pct:.1f}%</div>
                </div>"""
            elif done:
                progress_html = '<div style="margin-top:8px;"><span style="color:#4ade80;font-weight:700;font-size:0.82rem;">✓ Completed</span></div>'

        return f"""
        <div style="background:#0a0f1e;border:1px solid #1e293b;border-left:3px solid {status_color};
                    border-radius:8px;padding:16px 18px;margin-bottom:10px;">
            <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:12px;flex-wrap:wrap;">
                <div style="flex:1;min-width:0;">
                    <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-bottom:6px;">
                        {_badge(dur, _DUR_COLOR.get(dur, '#94a3b8'))}
                        {_badge(etype, _TYPE_COLOR.get(etype, '#94a3b8'))}
                        {_badge(status_label, status_color)}
                    </div>
                    <div style="font-size:0.95rem;font-weight:700;color:#e2e8f0;margin-bottom:4px;">{title} {trophy_html}</div>
                    <div style="font-size:0.80rem;color:#64748b;line-height:1.5;">{desc}</div>
                    {progress_html}
                </div>
                <div style="color:{status_color};font-size:0.75rem;white-space:nowrap;padding-top:2px;">{time_str}</div>
            </div>
        </div>"""

    def _section(label, color, events, status_label):
        if not events:
            return ""
        rows = "".join(_ev_card(e, status_label, color) for e in events)
        return f"""
        <div style="margin-bottom:28px;">
            <div style="font-size:0.68rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;
                        color:{color};margin-bottom:12px;padding-bottom:6px;
                        border-bottom:1px solid {color}33;">{label}</div>
            {rows}
        </div>"""

    active_html   = _section("Active", "#4ade80", _active, "active")
    upcoming_html = _section("Upcoming", "#38bdf8", _upcoming, "upcoming")
    finished_html = _section("Recently Ended", "#475569", _finished, "ended")

    empty_html = ""
    if not _active and not _upcoming and not _finished:
        empty_html = """
        <div style="text-align:center;padding:60px 0;color:#475569;">
            <div style="font-size:2.5rem;margin-bottom:12px;">🌅</div>
            <div style="font-size:1rem;font-weight:600;color:#64748b;margin-bottom:6px;">No events right now</div>
            <div style="font-size:0.82rem;">Daily and weekly events launch regularly. Check back soon.</div>
        </div>"""

    # Level / trophy progress bar
    lv       = _lvl["level"]
    trophies = _lvl["trophies"]
    nxt      = _lvl["next_threshold"]
    prev     = _lvl["prev_threshold"]
    pct      = _lvl["progress_pct"]
    nxt_str  = f"{nxt:,}" if nxt else "MAX"
    level_html = f"""
    <div style="background:#0a0f1e;border:1px solid #1e293b;border-radius:10px;padding:18px 20px;margin-bottom:28px;">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
            <div style="display:flex;align-items:center;gap:10px;">
                <span style="background:#1e1b4b;border:1px solid #4338ca;border-radius:10px;
                             padding:3px 12px;font-size:0.8rem;font-weight:700;color:#a5b4fc;">
                    <span style="color:#818cf8;">Lv</span> {lv}
                </span>
                <span style="color:#fbbf24;font-weight:700;font-size:0.9rem;">{trophies:,} ★</span>
            </div>
            <span style="color:#475569;font-size:0.75rem;">Next level: {nxt_str} ★</span>
        </div>
        <div style="background:#1e293b;border-radius:4px;height:6px;overflow:hidden;">
            <div style="background:linear-gradient(90deg,#6366f1,#a78bfa);height:100%;
                        width:{pct}%;transition:width 0.4s;border-radius:4px;"></div>
        </div>
        <div style="color:#475569;font-size:0.7rem;margin-top:6px;">
            {prev:,} → {nxt_str} ★ &nbsp;·&nbsp; {pct:.1f}% to level {lv + 1}
        </div>
    </div>"""

    # ── Beta events panel ─────────────────────────────────────────────────────
    beta_panel_html = ""
    try:
        from beta import (get_available_count, get_total_count, get_player_request,
                          FOUNDING_OPERATIVE_TROPHIES, POCKET_EMPIRE_TROPHIES,
                          ACTIVE_DUTY_TROPHIES, PLAY_STORE_URL, GOOGLE_GROUP_URL,
                          has_pocket_empire)
        _avail = get_available_count()
        _total = get_total_count()
        _used  = _total - _avail
        _slots_pct = round(_used / _total * 100) if _total else 100
        _req   = get_player_request(player.id)
        _has_badge = has_pocket_empire(player.id)

        def _beta_ev_card(icon, title, trophies, desc, status_html, color):
            return f"""
            <div style="background:#0a0f1e;border:1px solid {color}44;border-left:3px solid {color};
                        border-radius:8px;padding:16px 18px;margin-bottom:10px;">
                <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:12px;">
                    <div style="flex:1;">
                        <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;flex-wrap:wrap;">
                            <span style="font-size:1.1rem;">{icon}</span>
                            <span style="font-size:0.95rem;font-weight:700;color:{color};">{title}</span>
                            <span style="background:{color}22;color:{color};border:1px solid {color}44;
                                         border-radius:3px;padding:1px 7px;font-size:0.65rem;font-weight:700;
                                         text-transform:uppercase;">SPECIAL</span>
                            <span style="color:#fbbf24;font-size:0.8rem;font-weight:700;">+{trophies} ★</span>
                        </div>
                        <div style="font-size:0.80rem;color:#64748b;line-height:1.5;margin-bottom:10px;">{desc}</div>
                        {status_html}
                    </div>
                </div>
            </div>"""

        # Slots remaining bar
        _slots_bar = f"""
        <div style="background:#0a0f1e;border:1px solid #f59e0b44;border-radius:10px;
                    padding:14px 18px;margin-bottom:16px;">
            <div style="display:flex;justify-content:space-between;margin-bottom:8px;">
                <span style="color:#f59e0b;font-size:0.8rem;font-weight:700;">🎟️ Founding Tester Slots</span>
                <span style="color:{'#ef4444' if _avail == 0 else '#fbbf24'};font-size:0.8rem;font-weight:700;">
                    {'FULL' if _avail == 0 else f'{_avail} of {_total} remaining'}
                </span>
            </div>
            <div style="background:#1e293b;border-radius:4px;height:6px;overflow:hidden;">
                <div style="background:linear-gradient(90deg,#f59e0b,#fbbf24);height:100%;
                            width:{_slots_pct}%;border-radius:4px;"></div>
            </div>
        </div>"""

        # Founding Operative status
        if _req and _req.status == "approved":
            _ev1_status = '<span style="color:#4ade80;font-weight:700;">✓ Completed — check your dashboard notification for your promo code!</span>'
        elif _req and _req.status == "pending":
            _ev1_status = '<span style="color:#fbbf24;">⏳ Verification pending — we\'ll notify you in-game once approved.</span>'
        elif _req and _req.status == "rejected":
            _ev1_status = '<span style="color:#ef4444;">✗ Not approved. Contact support if you believe this is an error.</span>'
        elif _avail == 0:
            _ev1_status = '<span style="color:#475569;">All slots have been filled for this event.</span>'
        else:
            _ev1_status = f"""
            <form method="post" action="/api/beta/request" style="display:flex;gap:8px;flex-wrap:wrap;margin-top:4px;">
                <input type="email" name="google_email" required placeholder="your@gmail.com"
                       style="flex:1;min-width:200px;background:#0f172a;border:1px solid #334155;
                              color:#e2e8f0;border-radius:6px;padding:8px 12px;font-size:0.82rem;">
                <button type="submit"
                        style="background:#f59e0b;color:#020617;border:none;border-radius:6px;
                               padding:8px 16px;font-size:0.82rem;font-weight:700;cursor:pointer;white-space:nowrap;">
                    Request Code
                </button>
            </form>
            <div style="font-size:0.72rem;color:#475569;margin-top:6px;">
                First <a href="{GOOGLE_GROUP_URL}" target="_blank" rel="noopener" style="color:#fbbf24;">join the Wadsworth Tycoon group</a>,
                then enter the Google account email you used to join. We'll verify your membership and send your code.
            </div>"""

        # Pocket Empire status
        if _has_badge:
            _ev2_status = '<span style="color:#4ade80;font-weight:700;">✓ Completed — Founding Tester badge unlocked!</span>'
        elif _req and _req.status == "approved":
            _ev2_status = f'<a href="{PLAY_STORE_URL}" target="_blank" rel="noopener" style="color:#38bdf8;font-weight:600;">Download the app ↗</a><span style="color:#475569;"> then log in from it to complete this event.</span>'
        else:
            _ev2_status = '<span style="color:#475569;">Complete Founding Operative first to unlock your promo code.</span>'

        # Active Duty (daily) — check today's login
        try:
            from beta import DailyTWALogin, _get_db as _bdb
            from datetime import date as _date
            _bdb_c = _bdb()
            _today_login = _bdb_c.query(DailyTWALogin).filter(
                DailyTWALogin.player_id  == player.id,
                DailyTWALogin.login_date == _date.today(),
            ).first()
            _bdb_c.close()
            _duty_status = ('<span style="color:#4ade80;font-weight:700;">✓ Logged in from app today!</span>'
                            if _today_login else
                            '<span style="color:#94a3b8;">Log in from the Android app today to earn trophies.</span>')
        except Exception:
            _duty_status = '<span style="color:#94a3b8;">Log in from the Android app each day to earn daily trophies.</span>'

        beta_panel_html = f"""
        <div style="margin-bottom:28px;">
            <div style="font-size:0.68rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;
                        color:#f59e0b;margin-bottom:12px;padding-bottom:6px;
                        border-bottom:1px solid #f59e0b33;">Founding Tester Program</div>
            {_slots_bar}
            {_beta_ev_card("🕵️", "Founding Operative", FOUNDING_OPERATIVE_TROPHIES,
                "Join the Wadsworth Tycoon Google Group and submit your Google account email. "
                "We'll verify your membership and deliver an exclusive promo code to your dashboard.",
                _ev1_status, "#f59e0b")}
            {_beta_ev_card("📱", "Pocket Empire", POCKET_EMPIRE_TROPHIES,
                "Download the Wadsworth Android app using your promo code and log in from it for the first time. "
                "Earns you permanent Founding Tester status visible on your contact card.",
                _ev2_status, "#38bdf8")}
            {_beta_ev_card("⚔️", "Active Duty", ACTIVE_DUTY_TROPHIES,
                "Log in from the Android app each day to earn daily trophies. Resets at UTC midnight.",
                _duty_status, "#4ade80")}
        </div>"""
    except Exception:
        pass

    body = f"""
    <a href="/" style="color:#64748b;font-size:0.85rem;text-decoration:none;display:inline-block;margin-bottom:16px;">← Dashboard</a>
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:20px;flex-wrap:wrap;gap:10px;">
        <h2 style="margin:0;">Events &amp; Tasks</h2>
        <span style="color:#475569;font-size:0.8rem;">Server-wide events, market effects &amp; player tasks</span>
    </div>
    {_flash_html}
    {level_html}
    {beta_panel_html}
    {active_html}
    {upcoming_html}
    {finished_html}
    {empty_html}
    <script>
    (function() {{
        if (!window.matchMedia('(display-mode: standalone)').matches) return;
        var xhr = new XMLHttpRequest();
        xhr.open('GET', '/api/twa-checkin', true);
        xhr.withCredentials = true;
        xhr.setRequestHeader('X-Requested-With', 'cc.notifly.wadsworth.twa');
        xhr.send();
    }})();
    </script>"""

    return shell("Events & Tasks", body,
                 balance=getattr(player, "cash_balance", 0.0),
                 player_id=player.id)


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
