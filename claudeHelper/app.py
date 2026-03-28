"""
NotiFly v8.2.2 (Ultimate Edition) - Flask Port
- Added: NSFW Gate, Subscriber Portal, Premium CRM Dashboard
- Fixed: Removed manual ETag quoting that caused 500 Errors on Termux/Flask.
- Status: Fully Operational
"""
import os
import sys
import json
import time
import base64
import queue
import subprocess
import threading
import shutil
import re
import sqlite3
import uuid
from pathlib import Path
from urllib.parse import urlparse
import io

# --- DEPENDENCIES INSTALLER ---
def install_deps():
    try:
        import flask
        import pywebpush
        import cryptography
        from PIL import Image
        import flask_compress  # <--- NEW CHECK
    except ImportError:
        print("Installing missing dependencies...")
        # Added "Flask-Compress" to the command below
        subprocess.run([sys.executable, "-m", "pip", "install", "flask", "pywebpush", "cryptography", "Pillow", "Flask-Compress", "--break-system-packages"], check=True)
        print("Dependencies installed. Restarting...")
        os.execv(sys.executable, ['python3'] + sys.argv)

install_deps()

from flask import Flask, request, Response, send_file, redirect, jsonify, make_response, request
from pywebpush import webpush, WebPushException
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from PIL import Image, ImageFilter

# --- IMPORT MODULES ---
try: import tools.tally as tally_tool
except ImportError: 
    tally_tool = None
    print("[WARNING] tools/tally.py not found.")

try: import tools.tawk as tawk_tool
except ImportError: 
    tawk_tool = None
    print("[WARNING] tools/tawk.py not found.")
    
try: import toolbox
except ImportError:
    toolbox = None
    print("[WARNING] toolbox.py not found. Tools disabled.")

try: import store
except ImportError:
    store = None
    print("[WARNING] store.py not found. Store embeds disabled.")

try: import link_importer
except ImportError:
    link_importer = None
    print("[WARNING] link_importer.py not found.")

try: import shout_out
except ImportError:
    shout_out = None
    print("[WARNING] shout_out.py not found.")

try: import sitemap_gen
except ImportError: 
    sitemap_gen = None
    print("[WARNING] sitemap_gen.py not found.")

try: import premium_tier_2
except ImportError:
    premium_tier_2 = None
    print("[WARNING] premium_tier_2.py not found.")

try: import t2_analytics
except ImportError:
    t2_analytics = None
    print("[WARNING] t2_analytics.py not found. Tier 2 analytics disabled.")

try: import nsfw_gate
except ImportError: nsfw_gate = None

try: import notifly_explore
except ImportError: notifly_explore = None

try: import notifly_analytics
except ImportError: notifly_analytics = None

try: import favicon
except ImportError: favicon = None

try: import email_form
except ImportError: email_form = None

try: import banners
except ImportError: 
    banners = None
    print("[WARNING] banners.py not found. Profile banners disabled.")

try: import premium_tier
except ImportError:
    premium_tier = None
    print("[WARNING] premium_tier.py not found.")

try: import social_cards
except ImportError:
    social_cards = None
    print("[WARNING] social_cards.py not found.")

try: import livestream
except ImportError:
    livestream = None
    print("[WARNING] livestream.py not found.")

try: import sub_portal
except ImportError: 
    sub_portal = None
    print("[WARNING] sub_portal.py not found.")

try: import portal_dashboard
except ImportError:
    portal_dashboard = None
    print("[WARNING] portal_dashboard.py not found.")

# --- CONFIG ---
# Leave empty to force a temporary "TryCloudflare" tunnel
CF_TOKEN = "eyJhIjoiYWU3MmMxMWVlNGZlM2IwZDk0MWEzNDE4NGYyZTg0ZDkiLCJ0IjoiMGJjYTI0MTItYzU0Ni00NWU4LWI2ZGItMWU4ZDE4ODMzOGNmIiwicyI6Ik1EYzRZall6Tm1NdFlXRTVOaTAwTkdNM0xUbGpaamt0TTJGbE9XVm1Nelk0TlRRNSJ9"
CF_DOMAIN = "notifly.cc"

PORT = 8080
DB_FILE = Path("notifly.db")
AVATAR_DIR = Path("avatars")
SKINS_DIR = Path("skins")
GLOBAL_VAPID_DIR = Path("vapid_global")
VIDEO_CACHE_DIR = Path("video_cache")
PREMIUM_MEDIA_DIR = Path("premium_media")
MAX_AVATAR_SIZE = 25 * 1024 * 1024

# --- ESSENTIAL CSS ---
EMBED_CSS = """
/* Storefront Grid */
.store-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 10px;
    margin-top: 20px;
}
.store-item {
    background: #111;
    border: 1px solid #333;
    border-radius: 10px;
    overflow: hidden;
}
.store-embed iframe {
    width: 100%;
    height: 240px;
    border: none;
}
.store-meta {
    padding: 8px;
}
.store-label {
    font-size: 13px;
    font-weight: bold;
    color: #eab308;
}
.store-desc {
    font-size: 11px;
    color: #aaa;
    margin-top: 3px;
}
"""

MENU_CSS = """
/* Circular Nav Styles */
@import url(https://fonts.bunny.net/css?family=jura:300,500);

nav {
    --items: 4;
    --icon-size: 45px;
    --icon-clr: #eee;
    --icon-clr-hover: #eab308;
    --nav-bg-clr: rgba(34, 34, 34, 0.95);
    --nav-toggle-bg-clr: #eab308;
    --nav-trans-duration: 250ms;
    --nav-trans-delay-factor: 0.15;
    
    /* Position fixed in top left */
    position: fixed;
    top: 20px;
    left: 20px;
    z-index: 9999;
    width: var(--icon-size);
    height: var(--icon-size);
    font-family: 'Jura', sans-serif;
}

/* Toggle Button */
nav > button {
    position: absolute;
    top: 0; left: 0;
    width: var(--icon-size);
    height: var(--icon-size);
    border-radius: 50%;
    border: none;
    background-color: var(--nav-toggle-bg-clr);
    color: #111;
    cursor: pointer;
    z-index: 2;
    padding: 0;
    display: grid;
    place-items: center;
    transition: transform 0.2s;
}

nav > button:hover { transform: scale(1.1); }

/* Hamburger Animation Logic */
nav > button svg { width: 60%; height: 60%; overflow: visible; }
nav > button svg path { 
    transition: all 0.3s ease-in-out; 
    transform-origin: center;
    stroke: currentColor;
    stroke-width: 2;
    stroke-linecap: round;
}

/* Transform to 'X' when expanded */
nav > button[aria-expanded="true"] svg path:nth-of-type(1),
nav > button[aria-expanded="true"] svg path:nth-of-type(4) {
    opacity: 0;
    transform: scale(0);
}
nav > button[aria-expanded="true"] svg path:nth-of-type(2) { transform: rotate(-45deg); }
nav > button[aria-expanded="true"] svg path:nth-of-type(3) { transform: rotate(45deg); }

/* Menu Items */
nav > a {
    position: absolute;
    top: 0; left: 0;
    width: var(--icon-size);
    height: var(--icon-size);
    background: var(--nav-bg-clr);
    border-radius: 50%;
    display: grid;
    place-items: center;
    color: var(--icon-clr);
    text-decoration: none;
    opacity: 0;
    pointer-events: none;
    transition: transform var(--nav-trans-duration) ease-in-out, opacity var(--nav-trans-duration);
    transition-delay: calc(var(--nav-trans-duration) * var(--nav-trans-delay-factor) * var(--i));
    box-shadow: 0 4px 10px rgba(0,0,0,0.5);
    border: 1px solid #444;
}

nav > a:hover { color: var(--icon-clr-hover); background: #222; border-color: #eab308; }
nav > a svg { width: 22px; height: 22px; }

/* Expanded State: Fan out items from 0 to 90 degrees */
nav:has([aria-expanded="true"]) > a { opacity: 1; pointer-events: auto; }

/* Item Positions (Top-Left Corner Arc) */
/* 1. Vertical (Down) */
nav:has([aria-expanded="true"]) > a:nth-of-type(1) { transform: translate(0px, 85px); }
/* 2. Angled Down-Right */
nav:has([aria-expanded="true"]) > a:nth-of-type(2) { transform: translate(45px, 75px); }
/* 3. Angled Right-Down */
nav:has([aria-expanded="true"]) > a:nth-of-type(3) { transform: translate(75px, 45px); }
/* 4. Horizontal (Right) */
nav:has([aria-expanded="true"]) > a:nth-of-type(4) { transform: translate(85px, 0px); }

/* To add more later, just uncomment and adjust: */
/* nav:has([aria-expanded="true"]) > a:nth-of-type(5) { transform: translate(110px, 85px); } */
"""

EMBED_CSS = """
.embed-section { margin-top: 15px; padding-top: 15px; border-top: 1px dashed #333; }
.embed-box { margin-bottom: 20px; width: 100%; animation: fadeIn 0.5s; }
.vid-container { position: relative; width: 100%; padding-bottom: 56.25%; height: 0; overflow: hidden; border-radius: 12px; border: 1px solid #333; background: #000; }
.vid-container iframe { position: absolute; top: 0; left: 0; width: 100%; height: 100%; }
.embed-label { font-size: 11px; color: #666; margin-top: 5px; text-align: right; font-style: italic; }
@keyframes fadeIn { from { opacity:0; transform:translateY(10px); } to { opacity:1; transform:translateY(0); } }
.video-thumb { position: relative; cursor: pointer; border-radius: 10px; overflow: hidden; border: 1px solid var(--primary); }
.video-thumb img { width: 100%; display: block; }
.video-thumb .play-btn { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 60px; height: 60px; background: rgba(234, 179, 8, 0.9); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 24px; color: #000; }

/* Premium Gallery Grid */
.prem-gallery { display: grid; grid-template-columns: repeat(3, 1fr); gap: 5px; margin-top: 15px; }
.prem-item { position: relative; aspect-ratio: 1; background: #222; border-radius: 4px; overflow: hidden; cursor: pointer; border: 1px solid #333; }
.prem-item:hover { border-color: var(--primary); }
.prem-icon { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); font-size: 24px; color: #fff; }

/* REELS OVERLAY STYLES */
.prem-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: #000; z-index: 9999; display: flex; flex-direction: column; }
.prem-overlay.hidden { display: none !important; }
.prem-close { position: absolute; top: 20px; left: 20px; color: #fff; font-size: 30px; cursor: pointer; z-index: 10002; text-shadow: 0 0 5px #000; }

/* Snap Scroll Container */
.reels-container { width: 100%; height: 100%; overflow-y: scroll; scroll-snap-type: y mandatory; scroll-behavior: smooth; }
.reel-item { width: 100%; height: 100%; scroll-snap-align: start; position: relative; display: flex; align-items: center; justify-content: center; background: #000; }
.reel-media { max-width: 100%; max-height: 100%; width: 100%; height: auto; object-fit: contain; }

/* Interaction Sidebar */
.reel-actions { position: absolute; right: 10px; bottom: 100px; display: flex; flex-direction: column; gap: 20px; z-index: 10001; align-items: center; }
.action-btn { background: rgba(0,0,0,0.5); border: 1px solid #444; color: #fff; width: 50px; height: 50px; border-radius: 50%; display: flex; flex-direction: column; align-items: center; justify-content: center; cursor: pointer; font-size: 20px; transition: transform 0.1s; }
.action-btn:active { transform: scale(0.9); }
.action-btn.active { color: #eab308; border-color: #eab308; }
.action-count { font-size: 10px; margin-top: 2px; font-weight: bold; }
.reel-info { position: absolute; bottom: 20px; left: 10px; right: 70px; color: #fff; z-index: 10001; text-shadow: 0 1px 3px #000; pointer-events: none; }

/* Switch Styles */
.switch {position: relative;display: inline-block;width: 40px;height: 20px;margin-left:10px}
.switch input {opacity: 0;width: 0;height: 0;}
.slider {position: absolute;cursor: pointer;top: 0;left: 0;right: 0;bottom: 0;background-color: #333;-webkit-transition: .4s;transition: .4s;border-radius: 20px;}
.slider:before {position: absolute;content: "";height: 16px;width: 16px;left: 2px;bottom: 2px;background-color: white;-webkit-transition: .4s;transition: .4s;border-radius: 50%;}
input:checked + .slider {background-color: #eab308;}
input:focus + .slider {box-shadow: 0 0 1px #eab308;}
input:checked + .slider:before {-webkit-transform: translateX(20px);-ms-transform: translateX(20px);transform: translateX(20px);}
"""

DEFAULT_SKIN_CSS = """:root{--bg:#111;--card:#222;--text:#eee;--primary:#eab308;--input:#333}
body{background:var(--bg);color:var(--text);font-family:-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;margin:0;display:flex;justify-content:center;padding:20px;user-select:none;-webkit-tap-highlight-color:transparent}
.box{background:var(--card);width:100%;max-width:400px;padding:30px;border-radius:15px;box-shadow:0 4px 20px rgba(0,0,0,0.5);text-align:center}
h1{margin:0 0 10px 0;color:var(--primary)}
input,textarea,button,select{width:100%;padding:12px;margin:8px 0;border-radius:8px;border:none;box-sizing:border-box}
input,textarea,select{background:var(--input);color:white}
button{background:var(--primary);color:black;font-weight:bold;cursor:pointer;transition:transform 0.1s}
button:active{transform:scale(0.98)}
.hidden{display:none}.toast{color:#4ade80;margin-top:10px;font-size:14px}.err{color:#f87171;margin-top:10px;font-size:14px}
label{display:block;text-align:left;font-size:12px;color:#aaa;margin-top:10px}
a{color:var(--primary)}
.av-prev{width:80px;height:80px;object-fit:cover;border-radius:50%;margin:20px 0;border:2px solid var(--primary)}
.link-stack{display:flex;flex-direction:column;gap:10px;margin-top:20px;border-top:1px solid #333;padding-top:20px}
.link-btn{display:block;background:#333;color:white;text-decoration:none;padding:15px;border-radius:30px;font-weight:bold;border:1px solid #444;transition:0.2s}
.link-btn:hover{background:#444;transform:scale(1.02)}
.link-item{display:flex;gap:5px;margin-bottom:8px;align-items:center;background:#1a1a1a;padding:5px;border-radius:5px;}
input[type="datetime-local"]::-webkit-calendar-picker-indicator { filter: invert(1); cursor: pointer; }
"""

# --- DATABASE CLASS ---
class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        with self.lock:
            self.cursor.execute("PRAGMA foreign_keys = ON")
            try: self.cursor.execute("ALTER TABLE channels ADD COLUMN bio TEXT DEFAULT ''")
            except sqlite3.OperationalError: pass 

            self.cursor.execute("""CREATE TABLE IF NOT EXISTS channels (
                handle TEXT PRIMARY KEY, pin TEXT NOT NULL, skin TEXT DEFAULT 'default', 
                created_at INTEGER, bio TEXT DEFAULT ''
            )""")
            self.cursor.execute("""CREATE TABLE IF NOT EXISTS links (
                id INTEGER PRIMARY KEY AUTOINCREMENT, handle TEXT, label TEXT, url TEXT,
                FOREIGN KEY(handle) REFERENCES channels(handle) ON DELETE CASCADE
            )""")
            self.cursor.execute("""CREATE TABLE IF NOT EXISTS subs (
                endpoint TEXT, handle TEXT, p256dh TEXT, auth TEXT,
                PRIMARY KEY (endpoint, handle),
                FOREIGN KEY(handle) REFERENCES channels(handle) ON DELETE CASCADE
            )""")
            self.cursor.execute("""CREATE TABLE IF NOT EXISTS broadcast_history (
                bid TEXT PRIMARY KEY, handle TEXT, title TEXT, target_url TEXT, 
                sent_count INTEGER, timestamp INTEGER
            )""")
            self.cursor.execute("""CREATE TABLE IF NOT EXISTS analytics_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT, ref_id TEXT, timestamp INTEGER
            )""")
            self.cursor.execute("""CREATE TABLE IF NOT EXISTS scheduled_broadcasts (
                id INTEGER PRIMARY KEY AUTOINCREMENT, handle TEXT, pin TEXT, payload TEXT, run_at INTEGER, created_at INTEGER
            )""")

            if notifly_analytics: notifly_analytics.init_db(self.cursor)
            if nsfw_gate: nsfw_gate.init_db(self.cursor)
            if premium_tier: premium_tier.init_db(self.conn)
            if premium_tier_2: premium_tier_2.init_db(self.conn)
            if email_form: email_form.init_db(self.cursor)
            if livestream: livestream.init_db(self.conn)
            if sub_portal: sub_portal.init_db(self.cursor)
            if portal_dashboard: portal_dashboard.init_db(self.cursor)
            if shout_out: shout_out.init_db(self.conn)
            
            self.conn.commit()

    def query(self, sql, params=(), one=False):
        with self.lock:
            self.cursor.execute(sql, params)
            rv = self.cursor.fetchall()
            return (rv[0] if rv else None) if one else rv

    def execute(self, sql, params=()):
        with self.lock:
            self.cursor.execute(sql, params)
            self.conn.commit()
            return self.cursor.lastrowid

DB = Database()

# --- SETUP DIRECTORIES ---
def ensure_directories():
    SKINS_DIR.mkdir(exist_ok=True)
    AVATAR_DIR.mkdir(exist_ok=True)
    VIDEO_CACHE_DIR.mkdir(exist_ok=True)
    PREMIUM_MEDIA_DIR.mkdir(exist_ok=True)
    if banners: banners.init()
    default_path = SKINS_DIR / "default.css"
    if not default_path.exists() or default_path.stat().st_size == 0:
        default_path.write_text(DEFAULT_SKIN_CSS)
    
    for size in [192, 512]:
        icon_path = Path(f"icon-{size}.png")
        if not icon_path.exists():
            try:
                temp_svg = Path("temp_icon.svg")
                temp_svg.write_text(ICON_SVG)
                subprocess.run(["ffmpeg", "-y", "-i", str(temp_svg), "-vf", f"scale={size}:{size}", str(icon_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                temp_svg.unlink(missing_ok=True)
            except Exception as e: 
                print(f"[WARNING] IconGen {size}px: {e}")

# --- HELPERS ---
class VideoOptimizer:
    @staticmethod
    def generate_thumbnail(video_path):
        try:
            thumb_path = VIDEO_CACHE_DIR / f"{video_path.stem}_thumb.jpg"
            if thumb_path.exists(): return thumb_path
            subprocess.run(["ffmpeg", "-i", str(video_path), "-vframes", "1", "-vf", "scale=400:-1", "-q:v", "5", str(thumb_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            return thumb_path
        except: return None
    
    @staticmethod
    def get_video_url(video_path): return f"/video/{video_path.name}"

VIDEO_OPT = VideoOptimizer()

class GlobalVAPID:
    def __init__(self):
        GLOBAL_VAPID_DIR.mkdir(exist_ok=True)
        self.priv_path = GLOBAL_VAPID_DIR / "private.pem"
        self.pub_key = None
        self._ensure_keys()
    
    def _ensure_keys(self):
        if not self.priv_path.exists():
            subprocess.run(["openssl", "ecparam", "-name", "prime256v1", "-genkey", "-noout", "-out", str(self.priv_path)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        with open(self.priv_path, "rb") as f:
            private_key = serialization.load_pem_private_key(f.read(), password=None, backend=default_backend())
        public_key = private_key.public_key()
        pub_bytes = public_key.public_bytes(encoding=serialization.Encoding.X962, format=serialization.PublicFormat.UncompressedPoint)
        self.pub_key = base64.urlsafe_b64encode(pub_bytes).decode('utf-8').rstrip('=')
    
    def get_public_key(self): return self.pub_key
    def get_private_key_path(self): return str(self.priv_path)

GLOBAL_VAPID = GlobalVAPID()

# --- ANALYTICS ---
class AnalyticsManager:
    def log_event(self, track_type, ref_id):
        DB.execute("INSERT INTO analytics_events (type, ref_id, timestamp) VALUES (?, ?, ?)", (track_type, ref_id, int(time.time())))

    def get_stats(self, handle):
        history_rows = DB.query("SELECT * FROM broadcast_history WHERE handle = ? ORDER BY timestamp DESC LIMIT 10", (handle,))
        history = []
        for row in history_rows:
            bid = row['bid']
            clicks = DB.query("SELECT COUNT(*) as c FROM analytics_events WHERE type='notif' AND ref_id=?", (bid,), one=True)['c']
            dismissals = DB.query("SELECT COUNT(*) as c FROM analytics_events WHERE type='dismiss' AND ref_id=?", (bid,), one=True)['c']
            failures = DB.query("SELECT COUNT(*) as c FROM analytics_events WHERE type='fail' AND ref_id=?", (bid,), one=True)['c']
            delivered = max(0, row['sent_count'] - failures)
            ctr = round((clicks / delivered * 100), 1) if delivered > 0 else 0
            history.append({ "date": time.strftime('%Y-%m-%d %H:%M', time.localtime(row['timestamp'])), "title": row['title'], "sent": row['sent_count'], "fails": failures, "clicks": clicks, "dismissed": dismissals, "ctr": ctr })

        today = int(time.time())
        chart_data = {"labels": [], "broadcast_sends": [0]*7, "broadcast_clicks": [0]*7, "broadcast_dismiss": [0]*7, "broadcast_fails": [0]*7, "links": []}
        start_of_days = []
        for i in range(6, -1, -1):
            t = today - (i * 86400)
            struct = time.localtime(t)
            chart_data["labels"].append(time.strftime('%b %d', struct))
            s = time.mktime((struct.tm_year, struct.tm_mon, struct.tm_mday, 0, 0, 0, 0, 0, -1))
            start_of_days.append(int(s))
        start_of_days.append(today + 86400)

        bids_rows = DB.query("SELECT bid, timestamp, sent_count FROM broadcast_history WHERE handle=?", (handle,))
        handle_bids = {r['bid']: r['timestamp'] for r in bids_rows}
        
        for r in bids_rows:
            ts = r['timestamp']
            for i in range(7):
                if start_of_days[i] <= ts < start_of_days[i+1]:
                    chart_data["broadcast_sends"][i] += r['sent_count']
        
        if handle_bids:
            placeholders = ','.join(['?'] * len(handle_bids))
            events = DB.query(f"SELECT type, timestamp FROM analytics_events WHERE ref_id IN ({placeholders}) AND type IN ('notif', 'dismiss', 'fail')", tuple(handle_bids.keys()))
            for e in events:
                ts = e['timestamp']
                for i in range(7):
                    if start_of_days[i] <= ts < start_of_days[i+1]:
                        if e['type'] == 'notif': chart_data["broadcast_clicks"][i] += 1
                        elif e['type'] == 'dismiss': chart_data["broadcast_dismiss"][i] += 1
                        elif e['type'] == 'fail': chart_data["broadcast_fails"][i] += 1

        links_rows = DB.query("SELECT id, label FROM links WHERE handle = ?", (handle,))
        for l in links_rows:
            link_id = str(l['id'])
            daily_counts = [0] * 7
            clicks = DB.query("SELECT timestamp FROM analytics_events WHERE type='link' AND ref_id=?", (link_id,))
            total_clicks = 0
            for c in clicks:
                ts = c['timestamp']
                if ts >= start_of_days[0]:
                    total_clicks += 1
                    for i in range(7):
                        if start_of_days[i] <= ts < start_of_days[i+1]: daily_counts[i] += 1
            if total_clicks > 0:
                chart_data["links"].append({"label": l['label'], "data": daily_counts, "total": total_clicks})
        
        chart_data["links"].sort(key=lambda x: x['total'], reverse=True)
        chart_data["links"] = chart_data["links"][:5]
        return {"history": history, "charts": chart_data}

AM = AnalyticsManager()

# --- WORKER ---
class NotificationWorker:
    def __init__(self):
        self.q = queue.PriorityQueue()
        self.running = True
        threading.Thread(target=self._process, daemon=True).start()

    def add_task(self, priority, task_data): self.q.put((priority, task_data))

    def _process(self):
        print("[System] Background Worker Started.")
        while self.running:
            try:
                priority, task = self.q.get()
                try:
                    webpush(subscription_info=task['sub'], data=task['payload'], vapid_private_key=task['priv_key'], vapid_claims=task['claims'], timeout=10)
                except WebPushException as ex:
                    AM.log_event('fail', task.get('bid', 'unknown'))
                    if ex.response is not None and ex.response.status_code in [404, 410]:
                        DB.execute("DELETE FROM subs WHERE endpoint = ? AND handle = ?", (task['sub']['endpoint'], task['handle']))
                    elif ex.response is not None and (ex.response.status_code == 429 or ex.response.status_code >= 500):
                        self._handle_retry(priority, task)
                except Exception:
                    AM.log_event('fail', task.get('bid', 'unknown'))
                    self._handle_retry(priority, task)
                finally:
                    self.q.task_done()
            except Exception as e: print(f"[Worker CRASH] {e}")

    def _handle_retry(self, priority, task):
        if task['attempts'] < 3:
            task['attempts'] += 1
            threading.Timer(10, lambda: self.q.put((priority + 10, task))).start()

WORKER = NotificationWorker()

# --- CHANNEL MANAGER ---
class ChannelManager:
    def create_or_login(self, handle, pin):
        safe_handle = "".join([c for c in handle if c.isalnum() or c in ('-','_')]).lower()
        row = DB.query("SELECT * FROM channels WHERE handle = ?", (safe_handle,), one=True)
        if row:
            if row['pin'] == pin: return {"status": "success", "handle": safe_handle}
            return {"status": "error", "msg": "Incorrect PIN for this channel."}
        else:
            DB.execute("INSERT INTO channels (handle, pin, created_at) VALUES (?, ?, ?)", (safe_handle, pin, int(time.time())))
            return {"status": "success", "handle": safe_handle}

    def update_config(self, handle, pin, data):
        row = DB.query("SELECT pin FROM channels WHERE handle = ?", (handle,), one=True)
        if not row or row['pin'] != pin: return {"success": False, "msg": "Auth Failed"}
        
        if 'skin' in data: DB.execute("UPDATE channels SET skin = ? WHERE handle = ?", (data['skin'], handle))
        if 'bio' in data: DB.execute("UPDATE channels SET bio = ? WHERE handle = ?", (data['bio'], handle))
        if 'links' in data:
            DB.execute("DELETE FROM links WHERE handle = ?", (handle,))
            for link in data['links']:
                DB.execute("INSERT INTO links (handle, label, url) VALUES (?, ?, ?)", (handle, link.get('label'), link.get('url')))
        return {"success": True, "msg": "Profile Updated!"}

    def get_config(self, handle):
        row = DB.query("SELECT * FROM channels WHERE handle = ?", (handle,), one=True)
        if not row: return {}
        links_rows = DB.query("SELECT id, label, url FROM links WHERE handle = ?", (handle,))
        links = [{"id": r['id'], "label": r['label'], "url": r['url']} for r in links_rows]
        return {"pin": row['pin'], "skin": row['skin'], "bio": row['bio'] or "", "links": links}

    def save_avatar(self, handle, pin, image_data):
        row = DB.query("SELECT pin FROM channels WHERE handle = ?", (handle,), one=True)
        if not row or row['pin'] != pin: return {"success": False, "msg": "Auth Failed"}
        try:
            if isinstance(image_data, str):
                if ',' in image_data: image_data = image_data.split(',')[1]
                img_data = base64.b64decode(image_data)
            else:
                img_data = image_data

            if len(img_data) > MAX_AVATAR_SIZE: return {"success": False, "msg": "Image too large"}
            
            img = Image.open(io.BytesIO(img_data))
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P': img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            max_size = (800, 800)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=85, optimize=True)
            (AVATAR_DIR / handle).write_bytes(output.getvalue())
            return {"success": True, "msg": "Avatar updated!"}
        except Exception as e: return {"success": False, "msg": f"Save failed: {str(e)}"}

    def get_avatar_path(self, handle):
        path = AVATAR_DIR / handle
        return path if path.exists() else None

    def get_public_key(self, handle):
        return GLOBAL_VAPID.get_public_key() if DB.query("SELECT 1 FROM channels WHERE handle = ?", (handle,), one=True) else None
    
    def get_sub_count(self, handle):
        res = DB.query("SELECT COUNT(*) as c FROM subs WHERE handle = ?", (handle,), one=True)
        return res['c'] if res else 0

    def add_sub(self, handle, sub_info):
        DB.execute("INSERT OR REPLACE INTO subs (endpoint, handle, p256dh, auth) VALUES (?, ?, ?, ?)", (sub_info['endpoint'], handle, sub_info.get('keys', {}).get('p256dh'), sub_info.get('keys', {}).get('auth')))
        return self.get_sub_count(handle)

    def remove_sub(self, handle, endpoint):
        DB.execute("DELETE FROM subs WHERE endpoint = ? AND handle = ?", (endpoint, handle))

    def verify_sub(self, handle, endpoint):
        return bool(DB.query("SELECT 1 FROM subs WHERE handle = ? AND endpoint = ?", (handle, endpoint), one=True))

        # Replace the broadcast() method in ChannelManager class (around line 580-630)

    def broadcast(self, handle, pin, payload_dict):
        row = DB.query("SELECT pin FROM channels WHERE handle = ?", (handle,), one=True)
        if not row or row['pin'] != pin: return {"success": False, "error": "Auth Failed"}

        # --- SMART FILTERING SYSTEM (FIXED) ---
        filters = payload_dict.get('filters')
        if filters:
            # Join with profiles to get status, tags, and blocked status
            raw_rows = DB.query("""
                SELECT s.endpoint, s.p256dh, s.auth, p.status, p.admin_tags, p.is_blocked 
                FROM subs s 
                LEFT JOIN channel_subscriber_profiles p 
                ON s.endpoint = p.endpoint AND s.handle = p.handle 
                WHERE s.handle = ?
            """, (handle,))
        
            subs_rows = []
            target_tiers = filters.get('tiers', [])
            target_tags = filters.get('tags', [])
            tag_mode = filters.get('tag_mode', 'any')

            for r in raw_rows:
                # Skip blocked users automatically
                if r['is_blocked'] == 1:
                    continue
            
                # Tier filtering (default to 'Silver' if no profile exists)
                user_status = r['status'] if r['status'] else 'Silver'
            
                # Only filter by tier if tiers are specified
                if target_tiers and len(target_tiers) > 0:
                    if user_status not in target_tiers:
                        continue
            
                # Tag filtering (only if tags are specified)
                if target_tags and len(target_tags) > 0:
                    user_tags = json.loads(r['admin_tags'] or '[]')
                    # Case-insensitive comparison
                    user_tags_lower = [t.lower() for t in user_tags]
                    target_tags_lower = [t.lower() for t in target_tags]
                
                    if tag_mode == 'any':
                        # User must have at least ONE of the target tags
                        if not any(t in user_tags_lower for t in target_tags_lower):
                            continue
                    elif tag_mode == 'all':
                        # User must have ALL target tags
                        if not all(t in user_tags_lower for t in target_tags_lower):
                            continue
                    elif tag_mode == 'none':
                        # User must have NONE of the target tags
                        if any(t in user_tags_lower for t in target_tags_lower):
                            continue
            
                # User passed all filters - add to broadcast list
                subs_rows.append(r)
        else:
            # No filters - broadcast to everyone
            subs_rows = DB.query("SELECT endpoint, p256dh, auth FROM subs WHERE handle = ?", (handle,))
    
        if not subs_rows: 
            return {"success": False, "error": "No subscribers match criteria"}

        # --- BROADCAST DELIVERY ---
        bid = str(uuid.uuid4())
        original_url = payload_dict.get('url', '')
        DB.execute("INSERT INTO broadcast_history (bid, handle, title, target_url, sent_count, timestamp) VALUES (?, ?, ?, ?, ?, ?)", 
                   (bid, handle, payload_dict.get('title'), original_url, len(subs_rows), int(time.time())))
    
        payload_dict['url'] = f"/trk/n/{bid}"
        payload = json.dumps(payload_dict)
        admin_email = f"mailto:admin@{handle}.local"
        claims = {"sub": admin_email}
        priv_key_path = GLOBAL_VAPID.get_private_key_path()

        print(f"[{handle}] Queuing {len(subs_rows)} notifications...")
        for i, row in enumerate(subs_rows):
            task = {
                "sub": {"endpoint": row['endpoint'], "keys": {"p256dh": row['p256dh'], "auth": row['auth']}}, 
                "payload": payload, 
                "priv_key": priv_key_path, 
                "claims": claims, 
                "handle": handle, 
                "bid": bid, 
                "attempts": 0
            }
            WORKER.add_task(time.time() + i, task)
    
        return {"success": True, "count": len(subs_rows), "msg": "Queued for delivery"}

class ScheduleManager:
    def __init__(self):
        self.running = True
        threading.Thread(target=self._loop, daemon=True).start()

    def add_schedule(self, handle, pin, payload, run_at):
        DB.execute("INSERT INTO scheduled_broadcasts (handle, pin, payload, run_at, created_at) VALUES (?, ?, ?, ?, ?)", (handle, pin, json.dumps(payload), run_at, int(time.time())))
        return {"success": True, "msg": "Scheduled for future delivery"}

    def get_pending(self, handle):
        rows = DB.query("SELECT id, run_at, payload FROM scheduled_broadcasts WHERE handle = ? ORDER BY run_at ASC", (handle,))
        res = []
        for r in rows:
            try: title = json.loads(r['payload']).get('title', 'Unknown')
            except: title = "Error parsing"
            res.append({"id": r['id'], "date": time.strftime('%Y-%m-%d %H:%M', time.localtime(r['run_at'])), "title": title})
        return res

    def cancel(self, handle, s_id):
        DB.execute("DELETE FROM scheduled_broadcasts WHERE id=? AND handle=?", (s_id, handle))
        return {"success": True}

    def _loop(self):
        print("[System] Scheduler Started.")
        while self.running:
            try:
                now = int(time.time())
                rows = DB.query("SELECT * FROM scheduled_broadcasts WHERE run_at <= ?", (now,))
                for r in rows:
                    try:
                        CM.broadcast(r['handle'], r['pin'], json.loads(r['payload']))
                        DB.execute("DELETE FROM scheduled_broadcasts WHERE id = ?", (r['id'],))
                    except Exception as e: print(f"[Scheduler Error] {e}")
                time.sleep(30)
            except Exception as e: time.sleep(30)

CM = ChannelManager()
SCHEDULER = ScheduleManager()

# --- ASSETS & CONSTANTS ---
ICON_SVG = r"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><rect width="512" height="512" fill="#111"/><path d="M472.5 149.4L85.9 17.1c-11-3.8-22.8 1.7-27.1 12.4-1.9 4.7-1.7 10 .6 14.5l86 172.1 12.9 25.9-12.9 25.9-86 172.1c-2.3 4.5-2.5 9.8-.6 14.5 4.3 10.7 16.1 16.2 27.1 12.4l386.6-132.3c10-3.4 16.6-12.9 16.5-23.6-.1-10.8-6.8-20.2-16.9-23.6zM165.9 256l-59.4-118.7L392.4 256 106.5 374.7 165.9 256z" fill="#eab308"/></svg>"""
BADGE_SVG = r"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><path d="M472.5 149.4L85.9 17.1c-11-3.8-22.8 1.7-27.1 12.4-1.9 4.7-1.7 10 .6 14.5l86 172.1 12.9 25.9-12.9 25.9-86 172.1c-2.3 4.5-2.5 9.8-.6 14.5 4.3 10.7 16.1 16.2 27.1 12.4l386.6-132.3c10-3.4 16.6-12.9 16.5-23.6-.1-10.8-6.8-20.2-16.9-23.6zM165.9 256l-59.4-118.7L392.4 256 106.5 374.7 165.9 256z" fill="#ffffff"/></svg>"""
MANIFEST = json.dumps({
  "name": "NotiFly",
  "short_name": "NotiFly",
  "start_url": "/",
  "description": "Subscribe to channels for instant push notifications, watch exclusive livestreams, browse premium media galleries, and discover new content via the Explore page. Supports rich embeds for YouTube, Spotify, and more.",
  "display": "fullscreen",
  "background_color": "#111111",
  "theme_color": "#111111",
  "orientation": "portrait",
  "icons": [
    {
      "src": "/icon-512.png",
      "sizes": "512x512",
      "type": "image/png"
    },
    {
      "src": "/icon-192.png",
      "sizes": "192x192",
      "type": "image/png"
    }
  ],
  "scope": "/",
  "dir": "ltr",
  "display_override": [
    "window-controls-overlay",
    "fullscreen"
  ],
  "categories": ["entertainment", "lifestyle", "productivity", "social", "utilities"],
  "id": "031920190815201102272010"
})

def get_available_skins(): return [f.stem for f in SKINS_DIR.glob("*.css")]

def get_premium_ux_css(handle):
    """
    Checks if channel has Premium UX enabled and returns custom CSS.
    Returns empty string if disabled or not Tier 2.
    """
    if not premium_tier_2:
        return ""
    
    try:
        from pathlib import Path
        import json
        
        # Check if Premium UX is enabled
        config = premium_tier_2.get_module_config(DB.conn, handle, "premium_ux")
        if not config.get("enabled", False):
            return ""
        
        # Load the template CSS
        template_id = config.get("template", "digital_walls")
        template_path = Path("premium_ux_templates") / f"{template_id}.json"
        
        if not template_path.exists():
            return ""
        
        template_data = json.loads(template_path.read_text())
        custom_css = template_data.get("css", "")
        
        return f"<style>/* Premium UX: {template_id} */\n{custom_css}</style>"
    
    except Exception as e:
        print(f"[Premium UX CSS Error] {e}")
        return ""

def get_head(skin_name="default"):
    if not (SKINS_DIR / f"{skin_name}.css").exists(): skin_name = "default"
    return f"""<meta name="description" content="Subscribe to channels for instant push notifications, watch exclusive livestreams, browse premium media galleries, and discover new content via the Explore page. Supports rich embeds for YouTube, Spotify, and more."><link rel="canonical" href="https://notifly.cc{request.path}"/><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=5,user-scalable="yes"><title>NotiFly</title><link rel="manifest" href="/manifest.json"><link rel="icon" href="/icon.svg"><meta name="theme-color" content="#111"><meta name="apple-mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-status-bar-style" content="black-translucent"><link rel="stylesheet" href="/skins/{skin_name}.css?v=3"><script src="https://cdn.jsdelivr.net/npm/chart.js"></script><style>{EMBED_CSS}</style>"""

def process_links_for_embeds(links_data):
    buttons_html = []
    embeds_html = []
    
    # --- REGEX PATTERNS ---
    # YouTube: Matches standard v=, youtu.be, shorts, live
    yt_regex = r"(?:youtube\.com\/(?:[^/]+\/.+/|(?:v|e(?:mbed)?|shorts|live)\/|.*[?&]v=)|youtu\.be\/)([^\"&?/\s]{11})"
    # Spotify: Matches track, album, playlist, artist, etc.
    sp_regex = r"(?:https?://)?open\.spotify\.com\/(track|album|playlist|artist|episode|show)\/([a-zA-Z0-9]+)"
    # SoundCloud
    sc_regex = r"soundcloud\.com\/[a-zA-Z0-9-]+\/[a-zA-Z0-9-]+"

    for l in links_data:
        try:
            l_id = str(l['id'])
            label = l['label']
            url = str(l['url'] or '')
            
            # Sensitivity Check
            is_sensitive = False
            if nsfw_gate:
                is_sensitive = nsfw_gate.check_url(DB, url)
            
            # Helper to wrap content in blur/gate if needed
            def wrap(content, is_embed=False):
                if not is_sensitive: return content
                c_class = "sensitive-content sensitive-blur"
                return f"""<div class="sensitive-wrapper" id="sens_{l_id}">
                    <div class="{c_class}">{content}</div>
                    <div class="sensitive-overlay">
                        <div class="sensitive-warn">18+ CONTENT</div>
                        <button class="sensitive-btn" onclick="reveal('{l_id}')">
                            MUST BE OVER 18 YEARS OF AGE!!! SHOW?
                        </button>
                    </div>
                </div>"""

            yt_match = re.search(yt_regex, url)
            sp_match = re.search(sp_regex, url)
            sc_match = re.search(sc_regex, url)

            # --- YOUTUBE LOGIC ---
            # We check for yt_match OR "list=" to catch standalone playlist URLs
            if yt_match or "list=" in url:
                vid_id = yt_match.group(1) if yt_match else None
                
                # Playlist detection
                pl_match = re.search(r"[?&]list=([^&]+)", url)
                playlist_id = pl_match.group(1) if pl_match else None

                # Time support (only applies if we have a specific video ID)
                start_param = ""
                if vid_id:
                    start_time = None
                    t_match = re.search(r"[?&]t=(\d+)", url)
                    s_match = re.search(r"[?&]start=(\d+)", url)
                    if t_match: start_time = t_match.group(1)
                    elif s_match: start_time = s_match.group(1)
                    
                    if start_time:
                        start_param = f"&start={start_time}"

                is_shorts = "shorts" in url
                is_live = "live" in url

                # 1. PLAYLIST MODE
                if playlist_id:
                    embed_url = (
                        f"https://www.youtube-nocookie.com/embed/videoseries"
                        f"?list={playlist_id}&rel=0&modestbranding=1"
                    )
                    container_class = "vid-container playlist-container"

                # 2. SINGLE VIDEO MODE
                elif vid_id:
                    embed_url = (
                        f"https://www.youtube-nocookie.com/embed/{vid_id}"
                        f"?rel=0&modestbranding=1&playsinline=1{start_param}"
                    )
                    container_class = "vid-container"
                    if is_shorts: container_class += " shorts-vertical"
                    elif is_live: container_class += " live-video"
                
                # 3. FALLBACK (Malformed URL matched regex but no ID found)
                else:
                    raise ValueError("Invalid YouTube URL")

                html = f"""
                <div class="embed-box">
                    <div class="{container_class}">
                        <iframe 
                            src="{embed_url}" 
                            frameborder="0" 
                            referrerpolicy="strict-origin-when-cross-origin"
                            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
                            allowfullscreen
                            loading="lazy">
                        </iframe>
                    </div>
                    <div class="embed-label">{label}</div>
                </div>
                """
                embeds_html.append(wrap(html, True))

            # --- SPOTIFY LOGIC ---
            elif sp_match:
                sp_type = sp_match.group(1)
                sp_id = sp_match.group(2).split('?')[0].split('&')[0]
                
                # FIXED: Changed http -> https and used official embed domain
                embed_url = f"https://open.spotify.com/embed/{sp_type}/{sp_id}"
                
                html = f"""<div class="embed-box">
                    <iframe style="border-radius:12px" 
                        src="{embed_url}" 
                        width="100%" 
                        height="152" 
                        frameBorder="0" 
                        allowfullscreen="" 
                        allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture" 
                        loading="lazy">
                    </iframe>
                    <div class="embed-label">{label}</div>
                </div>"""
                embeds_html.append(wrap(html, True))

            # --- SOUNDCLOUD LOGIC ---
            elif sc_match:
                sc_url = url
                html = f"""<div class="embed-box">
                    <iframe width="100%" height="166" scrolling="no" frameborder="no" allow="autoplay" 
                        src="https://w.soundcloud.com/player/?url={sc_url}&color=%23eab308&auto_play=false&hide_related=false&show_comments=true&show_user=true&show_reposts=false&show_teaser=true">
                    </iframe>
                    <div class="embed-label">{label}</div>
                </div>"""
                embeds_html.append(wrap(html, True))

            # --- STANDARD BUTTON ---
            else:
                track_url = f"/trk/l/{l_id}"
                icon_html = favicon.get_icon_html(url) if favicon else ""
                btn_html = f'<a href="{track_url}" target="_blank" class="link-btn">{icon_html}<span>{label}</span></a>'
                buttons_html.append(wrap(btn_html, False))

        except Exception as e:
            # Silently fail on bad links so the profile still loads the rest
            print(f"[Embed Error] Link ID {l.get('id')}: {e}")
            continue

    return "".join(buttons_html), "".join(embeds_html)

# --- RENDERING FUNCTIONS ---
def render_guide_page():
    head = get_head("default")
    # CSS to make the long text readable and professional
    guide_css = """
    <style>
        body { background: #111; color: #eee; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
        .guide-container { max-width: 900px; margin: 0 auto; padding: 40px 20px 80px; text-align: left; }
        
        /* Headers */
        .guide-header { text-align: center; margin-bottom: 50px; border-bottom: 1px solid #333; padding-bottom: 30px; }
        .guide-header h1 { color: #eab308; font-size: 36px; margin-bottom: 10px; line-height: 1.2; }
        .guide-intro { font-size: 18px; line-height: 1.6; color: #ccc; max-width: 700px; margin: 0 auto; font-style: italic;}
        
        /* Typography */
        h2 { color: #eab308; margin-top: 60px; border-left: 5px solid #eab308; padding-left: 20px; text-transform: uppercase; font-size: 24px; letter-spacing: 1px; }
        h3 { color: #fff; margin-top: 35px; font-size: 20px; border-bottom: 1px solid #222; padding-bottom: 10px; display: inline-block; }
        h4 { color: #aaa; margin-top: 25px; font-size: 16px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px;}
        p { color: #ccc; line-height: 1.7; font-size: 16px; margin-bottom: 20px; }
        
        /* Lists */
        ul { padding-left: 20px; margin-bottom: 20px; }
        li { color: #ccc; line-height: 1.7; font-size: 16px; margin-bottom: 10px; }
        
        /* Accents */
        .tier-badge { display: inline-block; background: #222; color: #eab308; padding: 4px 12px; border: 1px solid #333; border-radius: 4px; font-size: 12px; font-weight: bold; margin-bottom: 10px; }
        .highlight { color: #fff; font-weight: bold; }
        hr { border: 0; border-top: 1px dashed #333; margin: 60px 0; }
        
        /* Navigation */
        .back-btn { position: fixed; bottom: 30px; right: 30px; background: #eab308; color: #000; padding: 15px 25px; border-radius: 50px; text-decoration: none; font-weight: 900; box-shadow: 0 4px 20px rgba(0,0,0,0.6); z-index: 100; transition: transform 0.2s; }
        .back-btn:hover { transform: scale(1.05); }
    </style>
    """
    
    html_content = f"""
    <div class="guide-container">
        <div class="guide-header">
            <h1>NotiFly: The Ultimate Toolkit<br>for Creator Independence</h1>
            <p class="guide-intro">Own Your Audience, Defy the Algorithm</p>
        </div>

        <p>In a digital landscape dominated by ever-changing algorithms, creators face a constant battle for visibility. Platforms like OnlyFans, while powerful, often impose limitations through algorithmic suppression, restricted discovery, and a fundamental lack of direct audience ownership. Your community, your content, and your income are subject to the whims of a system you cannot control.</p>
        <p>NotiFly is engineered to be the definitive solution to this challenge. It is <b>The Anti-Algorithm Platform</b>, meticulously designed to dismantle these barriers and place control squarely back into the hands of the creator. With NotiFly, you own your audience, bypass unpredictable algorithms, and communicate directly with your community whenever you choose.</p>
        <p>This guide provides a comprehensive overview of the powerful features available to every channel administrator on the NotiFly platform, from the core tools that build your foundation to the elite premium capabilities that can scale your brand into an empire.</p>

        <hr>

        <h2>1.0 The Core Toolkit: Building Your Foundational Hub</h2>
        <span class="tier-badge">STANDARD ADMIN FEATURES</span>
        <p>Establishing a strong, independent, and branded online presence is the first critical step toward true creator independence. NotiFly's standard admin features provide every creator with the essential toolkit to build this foundational hub. These tools empower you to centralize your content, manage your brand's visual identity, and begin engaging directly with your audience on your own terms.</p>

        <h3>1.1 Channel Setup and Visual Branding</h3>
        <p>Your NotiFly channel is your central command center. Customizing its look and feel is crucial for creating a professional and memorable brand experience for your fans.</p>
        <ul>
            <li><span class="highlight">Channel Creation:</span> The process begins by establishing a unique handle (your channel's URL) and a secure pin that serves as your administrative password.</li>
            <li><span class="highlight">Profile Picture:</span> You can upload a channel avatar up to 25MB. The system automatically optimizes the image for fast web performance, ensuring a crisp and professional look.</li>
            <li><span class="highlight">Channel Banner:</span> A custom banner image (up to 15MB) can be uploaded to create a visually striking header for your public channel page, immediately setting the tone for your brand.</li>
            <li><span class="highlight">Creator Bio:</span> Craft a compelling biography to introduce yourself and your content. Strategically embedding #hashtags within your bio is key, as this makes your channel discoverable to a wider audience through the platform's public Explore page.</li>
            <li><span class="highlight">Visual Themes (Skins):</span> Instantly change your channel's entire aesthetic by selecting from a list of available CSS themes. Whether you prefer the cyberpunk vibe of <i>protocol_terminus</i> or the vibrant energy of <i>rainbows</i>, you can choose a skin that perfectly matches your brand identity. <b>Pro Tip:</b> Use the Visual Themes to create a consistent brand identity across all your platforms. If your Twitch overlay is cyberpunk, select <i>protocol_terminus</i> for a seamless fan experience.</li>
        </ul>

        <h3>1.2 Centralizing Your Content: Links and Rich Embeds</h3>
        <p>NotiFly transforms a simple list of links into a dynamic and engaging content hub, making it easy for your audience to find everything you offer in one place.</p>
        <ul>
            <li><span class="highlight">Central Link Hub:</span> Add a stack of customized links to your profile, creating a single destination for fans to access all your social media profiles, storefronts, and other revenue-generating platforms.</li>
            <li><span class="highlight">Rich Media Embeds:</span> The platform is intelligent enough to automatically detect links from popular media sites. When you add a link from YouTube, Spotify, or SoundCloud, it is instantly transformed into a rich, playable media embed directly on your channel page, allowing fans to engage with your content without ever leaving.</li>
            <li><span class="highlight">Import from Bio Link Tool:</span> To make setup effortless, NotiFly includes a powerful import tool. Simply paste the URL of your existing Linktree, Beacons, or other public bio link page, and the system will scrape it to rapidly populate your new NotiFly channel with all your existing links.</li>
        </ul>

        <h3>1.3 Direct Communication: The Broadcast and Scheduling System</h3>
        <p>This is the core of NotiFly's "Anti-Algorithm" philosophy. Seize control of your reach with tools that give you a direct, unfiltered line of communication to your most dedicated fans, completely bypassing social media intermediaries.</p>
        <ul>
            <li><span class="highlight">Instant Push Notifications:</span> The core broadcast function allows you to send a notification with a Title, Message, and an optional Icon or Image URL directly to your subscribers' devices. Every notification automatically includes a Click URL, enabling you to drive traffic to your latest content, product drop, or announcement with a single click.</li>
            <li><span class="highlight">Scheduled Content Drops:</span> Plan your content strategy like a professional. The scheduling feature lets you compose broadcasts in advance and automate their delivery for a specific future date and time. You can also view a list of all pending scheduled broadcasts and cancel them at any time.</li>
        </ul>

        <h3>1.4 Measuring Your Impact: Core Analytics Dashboard</h3>
        <p>Understand your audience and refine your strategy with a built-in analytics dashboard. NotiFly provides essential engagement metrics without requiring complex third-party tools.</p>
        <ul>
            <li><span class="highlight">Broadcast History:</span> A clear, concise table of your recent broadcasts tracks the key performance indicators for each message: the number of notifications sent, delivery fails, audience clicks, dismissals, and the all-important Click-Through Rate (CTR).</li>
            <li><span class="highlight">7-Day Engagement Chart:</span> A visual line chart tracks the performance trends for your broadcast sends, clicks, dismissals, and failures over the past week, giving you an at-a-glance understanding of your audience's activity.</li>
            <li><span class="highlight">Top Link Performance:</span> The dashboard automatically ranks the top 5 most-clicked links on your profile. This powerful insight helps you identify what content, products, or platforms your audience values the most.</li>
        </ul>

        <h3>1.5 Audience Protection: The 18+ Age Gate</h3>
        <p>For creators who produce adult or mature content, audience protection and platform compliance are paramount. NotiFly includes robust, integrated tools for this purpose.</p>
        <ul>
            <li>A simple toggle switch in your admin dashboard enables a mandatory 18+ age verification overlay for all visitors to your public channel page, ensuring a critical layer of access control.</li>
            <li>Crucially, the system also automatically identifies and blurs links to known adult platforms like OnlyFans, Fansly, and Pornhub, requiring an extra click for disclosure. This protection is powered by an extensive internal blocklist, safeguarding your channel and your audience.</li>
        </ul>

        <h3>1.6 Building Your Email List</h3>
        <p>While direct notifications are powerful, building an email list is a crucial step towards creating a truly independent, long-term business asset that you own completely.</p>
        <ul>
            <li>You can enable a "Join Premium Waitlist" modal on your public channel page. This feature is designed to capture leads by collecting names, email addresses, and social links from your most interested fans.</li>
            <li>All collected leads can be easily exported as a downloadable CSV file directly from your admin dashboard, ready to be imported into your email marketing platform of choice.</li>
        </ul>
        
        <p><i>Once this strong foundation is built, it's time to unlock a new level of professional-grade tools designed for dynamic content and community management.</i></p>

        <hr>

        <h2>2.0 Unlocking Superpowers: The Premium Creator Tier</h2>
        <span class="tier-badge">PREMIUM UPGRADE</span>
        <p>Upgrading to the Premium Tier marks the evolution of your channel from a static link page into a dynamic, multimedia-rich fan club. This tier is for creators who want to offer exclusive content and cultivate a deeper relationship with their community. Premium status can be unlocked either by logging in with admin credentials or by redeeming a single-use referral token, perfect for gifting access or onboarding collaborators.</p>

        <h3>2.1 The Premium Media Gallery: Host Exclusive Content</h3>
        <p>Offer exclusive content directly to your fans, provide SFW previews to drive subscriptions on other platforms, or simply create a richer media experience on your central hub.</p>
        <ul>
            <li><span class="highlight">1GB Storage:</span> Activating the Premium Tier immediately unlocks 1GB of private media storage dedicated to your channel.</li>
            <li><span class="highlight">Multimedia Uploads:</span> You can upload videos, images, and audio files directly to your NotiFly storage. The system automatically optimizes all uploaded images for fast loading times and a seamless user experience.</li>
            <li><span class="highlight">Public Gallery:</span> All uploaded media is presented in a modern, engaging reels-container that uses snap-scrolling, allowing fans to swipe through your exclusive content just as they would on TikTok or Instagram. This modern interface includes thumbnails and file information, making it easy for fans to browse your exclusive content.</li>
        </ul>

        <h3>2.2 Advanced Fan Management: The Subscriber CRM</h3>
        <p>Go beyond simple subscriber counts and begin managing your audience with professional-grade Customer Relationship Management (CRM) tools. The Subscriber CRM isn't just a list; it's the central nervous system of your premium channel, the engine that powers precision targeting for broadcasts, identifies top fans for special treatment, and provides the segmentation data needed for effective monetization.</p>
        <ul>
            <li><span class="highlight">Subscriber Profiles:</span> Premium channels unlock a "Subscriber Portal." This allows your fans to move beyond being anonymous endpoints and create their own unique username and bio specifically for your channel, fostering a stronger sense of community identity.</li>
            <li><span class="highlight">CRM Dashboard:</span> As the administrator, you gain access to a "Manage Subscribers" dashboard. This powerful interface allows you to view and manage every subscriber who has created a profile, giving you the tools to segment and reward your community.</li>
            <li><span class="highlight">Assign Tiers:</span> Categorize your fans into different status levels (Silver, Gold, Platinum, Diamond) to organize or reward your top supporters. Use the Diamond tier not just as a label, but as a segment for your most valuable supporters. These are the fans you should target with exclusive pre-sales or personal thank-you messages using the Smart Filter system.</li>
            <li><span class="highlight">Private Notes:</span> Keep private, admin-only notes on individual subscribers to remember key details or interactions.</li>
            <li><span class="highlight">Tagging System:</span> Apply custom tags to segment your audience based on specific interests, purchase history, or engagement behavior.</li>
            <li><span class="highlight">Block Users:</span> If a user becomes problematic, you can permanently block and remove their profile. This action also revokes their ability to receive any future push notifications from your channel.</li>
        </ul>

        <h3>2.3 Precision Broadcasting with Smart Filters</h3>
        <p>The data from your Subscriber CRM directly powers a more sophisticated and targeted notification strategy, ensuring the right message reaches the right audience every time.</p>
        <ul>
            <li><span class="highlight">Target by Tier:</span> Send notifications exclusively to subscribers who belong to one or more specific status tiers. This is perfect for sending a special thank-you message to your "Diamond" tier fans or an exclusive offer to your "Gold" members.</li>
            <li><span class="highlight">Target by Tag:</span> Filter your broadcasts based on the custom tags you've applied, using advanced logic to create highly specific audience segments:
                <ul>
                    <li><i>any:</i> Send to users who have at least one of the selected tags.</li>
                    <li><i>all:</i> Send to users who must have all of the selected tags.</li>
                    <li><i>none:</i> Send to users who have none of the selected tags.</li>
                </ul>
            </li>
        </ul>

        <h3>2.4 Go Live: Real-Time Engagement</h3>
        <p>Connect with your audience in the most direct and engaging way possible: a live broadcast. NotiFly's livestreaming capability is a high-impact tool for hosting Q&As, live performances, or exclusive real-time events.</p>
        <ul>
            <li><span class="highlight">Two Streaming Modes:</span> Creators have the flexibility to go live in two distinct ways:
                <ul>
                    <li><i>Embed Code:</i> Simply paste a standard embed code from a third-party platform like YouTube Live or Twitch to feature your stream on your NotiFly page.</li>
                    <li><i>Webcam Direct:</i> Use the built-in direct streaming option powered by VDO.Ninja (a secure, direct WebRTC streaming technology). This provides you with a private "push" URL to use in your broadcast studio, allowing you to stream directly from your webcam to your audience with no external service required.</li>
                </ul>
            </li>
            <li><span class="highlight">Profile Visibility:</span> Whenever your stream is active, a highly visible "🔴 WATCH LIVESTREAM" button automatically appears at the top of your public channel page, maximizing viewership and engagement.</li>
        </ul>
        
        <p><i>With these premium tools, you can build a thriving community. The next tier is for creators aiming to operate at a professional, business-oriented scale.</i></p>

        <hr>

        <h2>3.0 Elite Status: Professional Tools with Premium Tier 2</h2>
        <span class="tier-badge">ELITE TIER</span>
        <p>Premium Tier 2 represents the pinnacle of the NotiFly platform, a suite of professional modules designed for serious creators who are scaling their brand into a full-fledged business. Access to this tier is granted to select channels, unlocking an "app store" of advanced capabilities that provide deep analytics, monetization tools, and strategic networking opportunities.</p>

        <h3>3.1 Monetization Engine: Storefront Embeds</h3>
        <p>Seamlessly integrate e-commerce into your NotiFly hub. This feature allows you to sell merchandise or digital products directly from your channel page, transforming your central hub into a revenue-generating storefront.</p>
        <ul>
            <li>You can add links to individual product pages from major e-commerce platforms like Shopify, Gumroad, Throne.</li>
            <li>The system's "Heavy Scraper" technology then attempts to automatically fetch the product's image, title, and description. This data is used to create a rich, visually appealing, and shoppable card on your public page, complete with a platform-specific "Buy Now" button to drive sales.</li>
            <li>Announce a new product drop with an Instant Push Notification that links directly to your channel, where fans can see and purchase from your integrated storefront in a single, seamless experience.</li>
        </ul>

        <h3>3.2 Community Networking: The Shout-Out Board</h3>
        <p>This feature is an exclusive networking tool for top-tier creators, designed to facilitate collaborative growth by cross-promoting other elite channels within the NotiFly ecosystem.</p>
        <ul>
            <li><span class="highlight">Admin Controls:</span> Inside the admin panel, a "Shout-Out Board" displays a list of other active Tier 2 channels. A creator can simply toggle a switch next to any channel they wish to feature.</li>
            <li><span class="highlight">Public Slider:</span> Once activated, a "VIP Shout-Outs" slider appears on the creator's public page, elegantly showcasing the channels they have chosen to promote and driving traffic between elite community members.</li>
        </ul>

        <h3>3.3 Strategic Intelligence: Tier 2 Analytics</h3>
        <p>Go beyond standard metrics with a professional-grade intelligence dashboard that provides deep, actionable insights into the health and behavior of your audience.</p>
        <ul>
            <li><span class="highlight">Churn & Retention:</span> This module calculates your Net Retention Rate and Total Churn, critical metrics that help you understand the long-term stability and growth of your subscriber base.</li>
            <li><span class="highlight">The "Golden Hour" Heatmap:</span> A powerful 7-day-by-24-hour heatmap visually identifies the peak engagement times when your audience is most active and likely to click on notifications. Use this heatmap to schedule your most important announcements. Dropping a new merch line during a peak engagement window identified by the "Golden Hour" can dramatically increase your click-through and conversion rates.</li>
            <li><span class="highlight">Viral Score:</span> A proprietary formula ((Clicks * 10) - (Dismissals * 5) + (CTR% * 2)) scores and ranks your recent broadcasts. This helps you instantly identify which types of content are most resonant and effective with your audience, allowing you to refine your content strategy.</li>
        </ul>

        <h3>3.4 The Admin Toolbox: Your On-Demand App Store</h3>
        <p>The Toolbox is an expandable platform that serves as an "app store" for specialized administrative and marketing tools, giving you on-demand access to professional utilities.</p>

        <h4>3.4.1 Campaign Manager Pro</h4>
        <p>This powerful utility is designed for creating, deploying, and analyzing trackable social media marketing campaigns.</p>
        <ul>
            <li>Generate a unique tracking link (/trk/c/{{cid}}) for any marketing initiative.</li>
            <li>Customize the OpenGraph meta tags (og_title, og_desc, og_image) for that specific link, ensuring it has a perfect, eye-catching appearance when shared on platforms like Twitter, Discord, or Facebook.</li>
            <li>Access deep analytics for each campaign link, including a 48-hour activity timeline, a device breakdown (iOS, Android, Windows, etc.), and a list of the top traffic sources (referrers) driving clicks.</li>
        </ul>

        <h4>3.4.2 Themed QR Code Generator</h4>
        <p>This tool is designed to convert offline interactions into online subscribers, directly linking the physical and digital aspects of your brand. Use it at live events, on merchandise, or in videos to seamlessly onboard new fans.</p>
        <ul>
            <li>Instantly generate a high-quality QR code that links directly to your NotiFly channel.</li>
            <li>The QR code is automatically and intelligently styled to match your channel's selected theme (skin), and it features your channel's avatar embedded directly in the center for a highly branded and professional look.</li>
        </ul>

        <h4>3.4.3 Maintenance Tools</h4>
        <p>Essential utilities for large-scale channel management and maintenance.</p>
        <ul>
            <li><span class="highlight">Subscriber Wipe:</span> A function to immediately and permanently remove all subscribers from your channel.</li>
            <li><span class="highlight">Wipe Broadcasts:</span> A tool to completely clear your broadcast history and all associated notification statistics, allowing for a clean slate.</li>
        </ul>

        <hr>

        <div style="text-align:center; padding-bottom:50px;">
            <h2 style="border:none; color:#fff;">Conclusion: Your Independent Creator Empire Awaits</h2>
            <p>NotiFly was built on a simple yet revolutionary premise: creators deserve to own their audience and control their destiny. While mainstream platforms trap you in a cycle of chasing algorithms and fighting for visibility, NotiFly provides the tools, control, and direct audience ownership that are essential for building a sustainable, independent brand.</p>
            <p>From establishing your first branded hub to deploying sophisticated marketing campaigns and monetization strategies, the platform is designed to grow with you at every stage of your journey. It is more than a tool; it is your partner in defying the algorithm. The time has come to stop renting your audience and start building your independent creator empire.</p>
        </div>
    </div>
    <a href="/" class="back-btn">← Back Home</a>
    """
    return f"<!DOCTYPE html><html><head>{head}{guide_css}</head><body>{html_content}</body></html>"

def render_home_page():
    # 1. Base Head & CSS
    # We load the default skin, then inject our custom Splash CSS + Menu CSS
    head = get_head("default")
    
    # CSS INJECTION
    head = head.replace(f"<style>{EMBED_CSS}</style>", f"""<style>{EMBED_CSS}
    /* Splash Specific Styles */
    body {{
        background: radial-gradient(circle at top right, #2a0a0a, #000);
        min-height: 100vh;
        display: flex;
        align-items: center;
        flex-direction: column;
        justify-content: center;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }}
    .hero-title {{
        font-size: 3.5rem;
        line-height: 1.1;
        margin-bottom: 10px;
        background: -webkit-linear-gradient(#fff, #888);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
    }}
    .hero-subtitle {{
        font-size: 1.2rem;
        color: #eab308; /* Primary Yellow */
        font-weight: bold;
        margin-bottom: 20px;
        text-transform: uppercase;
        letter-spacing: 2px;
    }}
    .feature-pill {{
        display: inline-block;
        background: rgba(255,255,255,0.1);
        padding: 6px 16px;
        border-radius: 20px;
        font-size: 12px;
        color: #ccc;
        margin: 5px;
        border: 1px solid #333;
        backdrop-filter: blur(5px);
    }}
    .cta-btn {{
        background: linear-gradient(135deg, #eab308 0%, #d97706 100%);
        color: #000;
        font-weight: 900;
        font-size: 18px;
        padding: 16px 45px;
        border-radius: 50px;
        border: none;
        cursor: pointer;
        transition: transform 0.2s, box-shadow 0.2s;
        box-shadow: 0 4px 20px rgba(234, 179, 8, 0.3);
        margin-top: 25px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }}
    .cta-btn:hover {{
        transform: scale(1.05);
        box-shadow: 0 6px 30px rgba(234, 179, 8, 0.5);
    }}
    /* The Login Form - Hidden Initially */
    .login-form {{
        display: none; 
        animation: slideUp 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        background: #111;
        padding: 30px;
        border-radius: 20px;
        border: 1px solid #333;
        margin-top: 30px;
        width: 100%;
        max-width: 400px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.8);
    }}
    @keyframes slideUp {{
        from {{ opacity: 0; transform: translateY(30px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}
    {MENU_CSS}
    </style>""")

    # 2. Waitlist Integration
    waitlist_ui = ""
    if email_form:
        waitlist_ui = email_form.render_modal("NotiFly HQ")

    # 3. Navigation Menu HTML
    # MODIFIED: Item #2 now triggers Tawk_API and uses a Chat Icon
    nav_html = """
    <nav aria-label="Main navigation">
        <button type="button" id="btn-nav-toggle" aria-expanded="false" aria-label="Menu">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
                <path d="M4 6l16 0" />
                <path d="M4 12l16 0" />
                <path d="M4 12l16 0" />
                <path d="M4 18l16 0" />
            </svg>
        </button>
        <a href="#" onclick="alert('Help: Enter a Channel Name and PIN to create a new channel or login to an existing one.')" title="Help" style="--i: 1">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
        </a>
        
        <a href="#" onclick="if(window.Tawk_API){Tawk_API.toggle()}else{alert('Chat loading...')}; return false;" title="Live Support" style="--i: 2">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
            </svg>
        </a>

        <a href="#" onclick="alert('Features: Instant Push Notifications, 1GB Premium Storage, Live Streaming, Social Cards, and Email Capture.')" title="Features" style="--i: 3">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>
        </a>
        <a href="/guide" title="Creator Toolkit Guide" style="--i: 4">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"></path><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"></path></svg>
        </a>
    </nav>
    """

    # 4. Chat Script
    chat_script = """
    <script type="text/javascript">
    var Tawk_API=Tawk_API||{}, Tawk_LoadStart=new Date();
    (function(){
    var s1=document.createElement("script"),s0=document.getElementsByTagName("script")[0];
    s1.async=true;
    s1.src='https://embed.tawk.to/6954b67ec5fc521979fc493e/1jdpeho1r';
    s1.charset='UTF-8';
    s1.setAttribute('crossorigin','*');
    s0.parentNode.insertBefore(s1,s0);
    })();
    </script>
    """

    # 5. Final HTML Structure
    return f"""<!DOCTYPE html><html lang="en"><head>{head}</head><body>
    {nav_html}
    
    <div style="text-align:center; z-index:10; padding:20px;">
        <div class="hero-subtitle">The Anti-Algorithm Platform</div>
        <div class="hero-title">Own Your<br>Audience.</div>
        
        <div style="margin: 30px 0;">
            <span class="feature-pill">⚡ Instant Push</span>
            <span class="feature-pill">📺 4K Streaming</span>
            <span class="feature-pill">💎 Premium Vault</span>
        </div>

        <p style="color:#aaa; line-height:1.6; font-size:15px; margin-bottom:10px; max-width:500px; margin-left:auto; margin-right:auto;">
            Stop fighting the algorithm. Build a channel where you control the reach. 
            Send notifications directly to your subscribers' devices—free.
        </p>

        <button onclick="showLogin()" class="cta-btn" id="main_cta">START BROADCASTING</button>
        
        <div style="margin-top: 25px; opacity: 0.9; transform: scale(0.9);">
            {waitlist_ui}
        </div>
    </div>

    <div id="login_area" class="login-form">
        <h2 style="color:#fff; margin-top:0; font-size:20px; text-align:center;">🚀 Launch Pad</h2>
        <p style="font-size:13px; color:#888; margin-bottom:20px; text-align:center;">
            Enter a <b>new handle</b> to create a channel,<br>or login to an existing one.
        </p>
        
        <label style="color:#666; font-size:11px; font-weight:bold; text-transform:uppercase;">Channel Handle</label>
        <input id="h" placeholder="e.g. DailyTech" maxlength="20" style="background:#222; border:1px solid #444; color:#fff; padding:12px; border-radius:8px; width:100%; box-sizing:border-box; margin-bottom:15px; font-size:16px;">
        
        <label style="color:#666; font-size:11px; font-weight:bold; text-transform:uppercase;">Secret PIN</label>
        <input id="p" type="password" placeholder="••••••••" maxlength="10" style="background:#222; border:1px solid #444; color:#fff; padding:12px; border-radius:8px; width:100%; box-sizing:border-box; margin-bottom:20px; font-size:16px;">
        
        <button onclick="go()" id="login_btn" style="width:100%; padding:15px; background:#eab308; color:#000; font-weight:bold; border-radius:8px; font-size:16px; border:none; cursor:pointer;">Launch Channel</button>
        <div id="msg" style="margin-top:15px; text-align:center;"></div>
    </div>

    <script>
    if ('serviceWorker' in navigator) {{
        navigator.serviceWorker.register('/sw.js').then(function(reg) {{ console.log('Service Worker Registered'); }});
    }}
    
    // Toggle Logic for Nav
    const btn = document.getElementById('btn-nav-toggle');
    if(btn) {{
        btn.addEventListener('click', () => {{
            const isExpanded = btn.getAttribute('aria-expanded') === 'true';
            btn.setAttribute('aria-expanded', !isExpanded);
        }});
    }}

    // Reveal Login Form
    function showLogin() {{
        // Hide CTA to clean up UI
        document.getElementById('main_cta').style.display = 'none';
        
        const form = document.getElementById('login_area');
        form.style.display = 'block';
        
        // Smooth scroll to form
        form.scrollIntoView({{behavior: 'smooth', block: 'center'}});
        
        // Auto-focus first input
        setTimeout(() => document.getElementById('h').focus(), 100);
    }}

    // Login Action
    async function go(){{ 
        const h=document.getElementById('h').value; 
        const p=document.getElementById('p').value; 
        const btn = document.getElementById('login_btn');
        const msg = document.getElementById('msg');
        
        if(!h || !p) {{
            msg.innerHTML = '<div style="color:#f87171">Please enter both a handle and a PIN.</div>';
            return;
        }}
        
        btn.disabled = true;
        btn.innerText = "Connecting...";
        msg.innerHTML = "";
        
        try {{
            const r=await fetch('/api/login',{{
                method:'POST',
                headers:{{'Content-Type':'application/json'}},
                body:JSON.stringify({{handle:h,pin:p}})
            }}); 
            const j=await r.json(); 
            
            if(j.status==='success') {{
                location.href='/admin/'+j.handle+'?pin='+p; 
            }} else {{
                msg.innerHTML='<div class="err" style="color:#f87171; background:rgba(248,113,113,0.1); padding:10px; border-radius:5px;">'+j.msg+'</div>';
                btn.disabled = false;
                btn.innerText = "Launch Channel";
            }}
        }} catch(e) {{
            console.error(e);
            msg.innerHTML='<div style="color:#f87171">Connection Failed. Check your internet.</div>';
            btn.disabled = false;
            btn.innerText = "Launch Channel";
        }}
    }}
    </script>
    {chat_script}
    </body></html>"""

def render_admin_page(handle, pin, sub_count, has_avatar, config):
    current_skin = config.get('skin', 'default')
    current_bio = config.get('bio', '')
    head = get_head(current_skin)
    
    banner_prev = "background:#444;"
    if banners:
        has_banner = banners.get_banner_path(handle)
        if has_banner:
            banner_prev = f'background-image: url(/banner/{handle}?t={int(time.time())});'
    
    av_html = ""
    if has_avatar:
        av_html = f'''<div style="position:relative;width:80px;height:80px;margin:0 auto 10px;background:#333;border-radius:50%;border:2px solid var(--primary)"><img id="admin_av" src="/avatar/{handle}?t={int(time.time())}" style="width:100%;height:100%;object-fit:cover;border-radius:50%;opacity:0;transition:opacity 0.3s" onload="this.style.opacity=1" onerror="this.style.display='none'"></div>'''
    
    btn_text = "Change" if has_avatar else "Set"
    skin_opts = "".join([f'<option value="{s}" {"selected" if s==current_skin else ""}>{s.title()}</option>' for s in get_available_skins()])
    links_data = config.get('links', [])
    b64_links = base64.b64encode(json.dumps(links_data).encode()).decode()
    enhanced_analytics_html = notifly_analytics.render_enhanced_stats(DB, handle) if notifly_analytics else ""

    tier2_html = ""
    if premium_tier_2 and premium_tier_2.check_tier_2_access(DB.conn, handle):
        # Call the module we just made
        res = premium_tier_2.execute_module(DB.conn, handle, "t2_analytics", "render")
        if res.get("success"):
            tier2_html = res.get("html", "")

    leads_html = ""
    if email_form:
        leads_html = f"""<div style="margin-top:30px; border-top:1px dashed #444; padding-top:20px;"><h2 style="color:#eab308; font-size:18px;">Audience Growth</h2><p style="font-size:12px;color:#888">Export emails collected from your Waitlist.</p><button onclick="window.location.href='/api/export_leads/{handle}?pin={pin}'" style="background:#333; border:1px solid #444; color:#fff; width:100%; font-size:12px;">📥 Download CSV</button></div>"""
    toolbox_html = ""
    
    if premium_tier_2.check_tier_2_access(DB.conn, handle):
        # Fetch the widget
        res = premium_tier_2.execute_module(DB.conn, handle, "toolbox", "render")
        if res['success']:
            toolbox_html = res['html']

    prem_status = {"locked": False}
    if premium_tier: prem_status = premium_tier.get_channel_status(DB.conn, handle)

    prem_html = ""
    if premium_tier:
        if prem_status['locked']:
            usage_pct = (prem_status['storage_used'] / prem_status['storage_max']) * 100
            gallery_items = premium_tier.get_gallery(DB.conn, handle)
            gallery_html = ""
            for item in gallery_items:
                gallery_html += f"""<div style="background:#222; border:1px solid #333; padding:5px; border-radius:4px; display:flex; justify-content:space-between; align-items:center; margin-bottom:4px"><div style="font-size:11px; overflow:hidden; white-space:nowrap; width:150px">{item['name']}</div><div style="display:flex; gap:5px; align-items:center"><span style="font-size:9px;color:#666">{item['size']}</span><button onclick="delMedia({item['id']})" style="background:#f87171; color:#fff; width:20px; height:20px; padding:0; font-size:10px">X</button></div></div>"""
            
            crm_btn = ""
            if portal_dashboard:
                crm_btn = f"""<button onclick="window.open('/admin/crm/{handle}?pin={pin}', '_blank')" style="background:#eab308; color:#000; width:100%; font-weight:bold; margin-top:10px; border:none; padding:10px; border-radius:6px; cursor:pointer">👥 MANAGE SUBSCRIBERS</button>"""

            prem_html = f"""
            <div style="background:#111; border:1px solid #eab308; border-radius:8px; padding:15px; margin-bottom:15px;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px"><span style="color:#eab308;font-weight:bold;font-size:12px">PREMIUM ACTIVE</span><span style="font-size:11px;color:#888">{prem_status['slots_used']}/{prem_status['slots_max']} Slots</span></div>
                <div style="background:#000;padding:10px;border-radius:4px;font-family:monospace;font-size:12px;color:#ccc"><div style="display:flex;justify-content:space-between;margin-bottom:4px"><span>User: <span style="color:#fff">{prem_status['username']}</span></span><button onclick="navigator.clipboard.writeText('{prem_status['username']}')" style="width:auto;padding:2px 6px;font-size:10px;background:#333;border:none;color:#fff;cursor:pointer">Copy</button></div><div style="display:flex;justify-content:space-between"><span>Pass: <span style="color:#fff">{prem_status['password']}</span></span><button onclick="navigator.clipboard.writeText('{prem_status['password']}')" style="width:auto;padding:2px 6px;font-size:10px;background:#333;border:none;color:#fff;cursor:pointer">Copy</button></div></div>
                {crm_btn}
                <hr style="border:0; border-top:1px solid #333; margin:10px 0">
                <div style="font-size:12px;color:#eab308;margin-bottom:5px">PREMIUM MEDIA ({int(usage_pct)}% Full)</div>
                <div style="background:#333; height:4px; width:100%; border-radius:2px; margin-bottom:10px"><div style="background:#eab308; height:100%; width:{usage_pct}%; border-radius:2px"></div></div>
                <div style="display:flex; gap:5px; margin-bottom:10px"><input type="file" id="upmedia" style="width:70%; font-size:10px"><button onclick="upMedia()" style="width:30%; font-size:10px; background:#444">Upload</button></div><div id="mediamsg"></div>
                <div style="max-height:150px; overflow-y:auto; border:1px solid #222; padding:5px; border-radius:4px">{gallery_html if gallery_html else '<div style="font-size:10px;color:#666;text-align:center">No Media</div>'}</div>
            </div>
            <script>
            function upMedia() {{
                const f = document.getElementById('upmedia').files[0];
                if(!f) return alert('Select file');
                if(f.type.startsWith('image/')) {{ document.getElementById('mediamsg').innerText = "Compressing & Uploading..."; compressAndUpload(f, 1920, '/api/upload_premium_media/'+handle, 'mediamsg'); }}
                else {{ const fd = document.createElement('div'); fd.innerHTML = 'Uploading Raw Media...'; document.getElementById('mediamsg').appendChild(fd); const req = new XMLHttpRequest(); req.open("POST", '/api/upload_premium_media/'+handle+'?pin='+pin); req.setRequestHeader("Content-Type", f.type || "application/octet-stream"); req.onload = function() {{ const j = JSON.parse(req.responseText); if(j.success) {{ alert("Uploaded!"); location.reload(); }} else {{ alert(j.msg); document.getElementById('mediamsg').innerHTML = ""; }} }}; req.send(f); }}
            }}
            async function delMedia(id) {{ if(!confirm('Delete?')) return; const r = await fetch('/api/delete_premium_media/'+handle, {{ method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify({{id: id, pin: pin}}) }}); location.reload(); }}
            </script>
            <button onclick="openShoutOuts()" style="background:#222; border:1px solid #eab308; color:#eab308; width:100%; padding:10px; border-radius:6px; margin-top:10px; font-weight:bold; cursor:pointer">
            📢 MANAGE SHOUT-OUTS
            </button>
            <script>
            async function openShoutOuts() {{
                const r = await fetch('/api/tier2/exec/shout_out/'+handle, {{
                    method: 'POST',
                    body: JSON.stringify({{ pin: pin, action: 'render_admin' }})
                }});
                const j = await r.json();
                if(j.success) {{
                    const d = document.createElement('div');
                    d.innerHTML = j.html;
                    document.body.appendChild(d);
                }} else {{ alert(j.msg); }}
            }}
            </script>
            """
        else:
            prem_html = f"""<div style="background:#111; border:1px solid #333; border-radius:8px; padding:15px; margin-bottom:15px;"><h3 style="color:#eab308;font-size:12px;margin:0 0 10px 0;text-transform:uppercase">Premium Activation</h3><div style="font-size:11px;color:#888;margin-bottom:10px">Enter credentials from Manager CLI to unlock 1GB Storage & Gallery.</div><input id="prem_user" placeholder="Admin Username" style="margin-bottom:5px"><input id="prem_pass" type="password" placeholder="Password" style="margin-bottom:10px"><button onclick="activatePremium()" style="background:#333;color:#fff;border:1px solid #444">Activate Premium</button><div id="prem_login_msg" style="margin-top:10px"></div></div><script>async function activatePremium() {{ const u = document.getElementById('prem_user').value; const p = document.getElementById('prem_pass').value; if(!u || !p) return alert('Please enter username and password'); document.getElementById('prem_login_msg').innerHTML = 'Verifying...'; const r = await fetch('/api/premium_login', {{ method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify({{handle: handle, user: u, pwd: p, pin: pin}}) }}); const j = await r.json(); if(j.success) {{ alert(j.msg); location.reload(); }} else {{ document.getElementById('prem_login_msg').innerHTML = '<div class="err">'+j.msg+'</div>'; }} }}</script>"""
    store_ui = ""
    if premium_tier_2 and premium_tier_2.check_tier_2_access(DB.conn, handle):
        # Get existing stores
        store_cfg = premium_tier_2.get_module_config(DB.conn, handle, "store") or {}
        stores_list = store_cfg.get("stores", [])
        stores_json = base64.b64encode(json.dumps(stores_list).encode()).decode()
    
        store_ui = f"""
        <div style="background:#111; border:1px solid #a78bfa; border-radius:8px; padding:15px; margin-bottom:15px;">
            <h3 style="color:#a78bfa; font-size:14px; margin:0 0 10px 0;">🛍️ STOREFRONT EMBEDS (TIER 2)</h3>
            <p style="font-size:11px; color:#888; margin-bottom:10px;">Add store links to your channel. Works best with individual product pages.</p>
        
            <details style="margin-bottom:15px; background:#1a1a1a; padding:10px; border-radius:6px; border:1px solid #333;">
                <summary style="cursor:pointer; font-size:12px; color:#a78bfa; font-weight:bold;">📖 URL Guide by Platform</summary>
                <div style="margin-top:10px; font-size:11px; color:#ccc; line-height:1.6;">
                    <div style="margin-bottom:8px;"><strong style="color:#96bf48;">Shopify:</strong> Use product pages like <code style="background:#333;padding:2px 4px;border-radius:3px;">yourstore.com/products/item-name</code></div>
                    <div style="margin-bottom:8px;"><strong style="color:#ff90e8;">Gumroad:</strong> Use product links like <code style="background:#333;padding:2px 4px;border-radius:3px;">yourname.gumroad.com/l/product</code></div>
                    <div style="margin-bottom:8px;"><strong style="color:#87ceeb;">Throne:</strong> Use product links like <code style="background:#333;padding:2px 4px;border-radius:3px;">throne.com/item-name</code></dev>
                </div>
            </details>
        
            <div id="store_list_ui"></div>
        
            <div style="background:#222; border:1px dashed #444; padding:10px; border-radius:8px; margin-top:10px;">
                <input id="new_store_url" placeholder="Store URL (paste individual product page for best results)" style="margin-bottom:5px;">
                <input id="new_store_label" placeholder="Label (e.g. 'Limited Edition Hoodie')" style="margin-bottom:5px;">
                <textarea id="new_store_desc" rows="2" placeholder="Description (optional)" style="margin-bottom:5px;"></textarea>
                <button onclick="addStore()" style="background:#444; color:#fff;">＋ Add Store</button>
            </div>
        
            <button onclick="saveStores()" style="margin-top:10px; background:#a78bfa; color:#000; font-weight:bold;">
                💾 Update Storefronts
            </button>
            <div id="store_msg" style="margin-top:10px; font-size:12px;"></div>
        </div>
    
        <script>
        let currentStores = [];
        try {{
            currentStores = JSON.parse(atob('{stores_json}'));
        }} catch(e) {{
            currentStores = [];
        }}
    
        function renderStores() {{
            const cont = document.getElementById('store_list_ui');
            if (currentStores.length === 0) {{
                cont.innerHTML = '<div style="font-size:11px; color:#666; padding:10px; text-align:center;">No stores added yet</div>';
                return;
            }}
        
            cont.innerHTML = '';
            currentStores.forEach((store, i) => {{
                const platformBadge = store.type ? `<span style="background:#333; padding:2px 6px; border-radius:4px; font-size:9px; color:#a78bfa;">${{store.type.toUpperCase()}}</span>` : '';
            
                cont.innerHTML += `
                    <div class="link-item" style="flex-direction:column; align-items:stretch; padding:10px;">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:5px;">
                            <div style="font-weight:bold; font-size:12px;">${{store.label || 'Store'}}</div>
                            <div style="display:flex; gap:5px; align-items:center;">
                                ${{platformBadge}}
                                <button onclick="removeStore(${{i}})" style="width:auto; padding:5px 10px; background:#f87171; color:white; font-size:10px;">Remove</button>
                            </div>
                        </div>
                        <input value="${{store.url}}" onchange="currentStores[${{i}}].url=this.value" style="margin:2px 0; font-size:11px;">
                        <input value="${{store.label || ''}}" onchange="currentStores[${{i}}].label=this.value" placeholder="Label" style="margin:2px 0; font-size:11px;">
                        <textarea onchange="currentStores[${{i}}].description=this.value" placeholder="Description" rows="2" style="margin:2px 0; font-size:11px;">${{store.description || ''}}</textarea>
                    </div>
                `;
            }});
        }}
    
        function addStore() {{
            const url = document.getElementById('new_store_url').value.trim();
            const label = document.getElementById('new_store_label').value.trim();
            const desc = document.getElementById('new_store_desc').value.trim();
        
            if (!url) {{
                alert('Store URL is required');
                return;
            }}
        
            if (!label) {{
                alert('Label is required');
                return;
            }}
        
            currentStores.push({{
                url: url,
                label: label,
                description: desc,
                type: detectPlatform(url)
            }});
        
            document.getElementById('new_store_url').value = '';
            document.getElementById('new_store_label').value = '';
            document.getElementById('new_store_desc').value = '';
        
            renderStores();
        }}
    
        function removeStore(index) {{
            if (confirm('Remove this store?')) {{
                currentStores.splice(index, 1);
                renderStores();
            }}
        }}
    
        function detectPlatform(url) {{
            const u = url.toLowerCase();
            if (u.includes('shopify.com')) return 'shopify';
            if (u.includes('etsy.com')) return 'etsy';
            if (u.includes('gumroad.com')) return 'gumroad';
            if (u.includes('ko-fi.com')) return 'kofi';
            if (u.includes('payhip.com')) return 'payhip';
            return 'generic';
        }}
    
        async function saveStores() {{
            const msg = document.getElementById('store_msg');
            msg.innerHTML = '<div style="color:#a78bfa;">Saving...</div>';
        
            try {{
                const r = await fetch('/api/tier2/exec/store/'+handle, {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{
                        pin: pin,
                        action: 'save',
                        payload: {{ stores: currentStores }}
                    }})
                }});
            
                const j = await r.json();
            
                if (j.success) {{
                    msg.innerHTML = '<div style="color:#4ade80;">✅ Storefronts updated!</div>';
                    setTimeout(() => {{
                        msg.innerHTML = '';
                    }}, 3000);
                }} else {{
                    msg.innerHTML = '<div style="color:#f87171;">❌ ' + j.msg + '</div>';
                }}
            }} catch(e) {{
                msg.innerHTML = '<div style="color:#f87171;">Connection error</div>';
            }}
        }}
    
        // Initialize on page load
        renderStores();
        </script>
        """

    gate_html = ""
    if nsfw_gate:
        is_gated = nsfw_gate.get_gate_status(DB, handle)
        gate_checked = "checked" if is_gated else ""
        gate_html = f"""<div style="border-bottom:1px solid #333;padding-bottom:15px;margin-bottom:15px;display:flex;justify-content:space-between;align-items:center"><label style="margin:0;color:#fff">Enable 18+ Age Gate</label><label class="switch"><input type="checkbox" id="age_gate_toggle" {gate_checked} onchange="toggleAgeGate()"><span class="slider round"></span></label></div><script>async function toggleAgeGate() {{ const s = document.getElementById('age_gate_toggle').checked; const r = await fetch('/api/toggle_gate/'+handle, {{ method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify({{pin: pin, enabled: s}}) }}); const j = await r.json(); if(!j.success) alert(j.msg); }}</script>"""

    stream_ui = ""
    if livestream and premium_tier and prem_status['locked']:
         stream_ui = livestream.render_admin_panel(DB.conn, handle)

    return f"""<!DOCTYPE html><html><head>{head}</head><body><div class="box">
    <h1>{handle}</h1>{stream_ui}<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:15px"><span style="font-size:12px;color:#888">ADMIN DASHBOARD</span><span style="background:#333;padding:4px 8px;border-radius:10px;font-size:12px;color:#4ade80">Subs: {sub_count}</span></div>
    {prem_html}{gate_html}{store_ui}
    <div style="border-bottom:1px solid #333;padding-bottom:15px;margin-bottom:15px"><label>Channel Banner</label><div style="width:100%;height:100px;border-radius:10px;margin-bottom:10px;background-size:cover;background-position:center;{banner_prev}"></div><div style="display:flex;gap:10px;"><input type="file" id="upbanner" accept="image/*" style="width:70%"><button onclick="upBanner()" style="width:30%">Set Banner</button></div><div id="bannermsg"></div></div>
    {av_html}<div style="border-bottom:1px solid #333;padding-bottom:15px;margin-bottom:15px"><label>Channel Profile Pic (Max 25MB)</label><div style="display:flex;gap:10px;"><input type="file" id="upfile" accept="image/*" style="width:70%"><button id="av_btn" onclick="upAv()" style="width:30%">{btn_text}</button></div><div id="upmsg"></div></div>
    <div style="border-bottom:1px solid #333;padding-bottom:15px;margin-bottom:15px"><label>Channel Bio (Add #hashtags here!)</label><textarea id="bio_text" rows="2" placeholder="Tell people about your channel... #news #tech">{current_bio}</textarea><button onclick="saveBio()" style="margin-top:5px;width:auto;padding:5px 10px">Save Bio</button></div>
    <div style="border-bottom:1px solid #333;padding-bottom:15px;margin-bottom:15px"><label>Theme / Skin</label><div style="display:flex;gap:10px;"><select id="skin_select" style="width:70%">{skin_opts}</select><button onclick="saveSkin()" style="width:30%">Apply</button></div></div>
    <div style="border-bottom:1px solid #333;padding-bottom:15px;margin-bottom:15px"><label>Your Links & Embeds</label><div id="link_list_ui"></div><div style="background:#222; border:1px dashed #444; padding:10px; border-radius:8px; margin-top:10px"><input id="new_link_label" placeholder="Label"><input id="new_link_url" placeholder="URL (YouTube/Spotify/SoundCloud/Web)"><button onclick="addLink()" style="background:#444; color:#fff">＋ Add Link</button></div><button onclick="saveLinks()" style="margin-top:15px">Update Profile!</button><button onclick="openImportModal()" style="background:#333; border:1px solid #eab308; color:#eab308; margin-top:10px;">📥 Import from Bio Link</button></div>
    <div style="background:#333;padding:10px;border-radius:8px;margin-bottom:20px"><div style="font-size:11px;color:#aaa;margin-bottom:5px">YOUR SHARE LINK:</div><div style="font-size:13px;color:#4ade80;word-break:break-all" id="linkbox">...</div><button style="margin-top:5px;padding:5px;font-size:12px" onclick="cp()">Copy Link</button></div>
    <label>Title</label><input id="t" placeholder="Alert Header"><label>Message</label><textarea id="b" rows="3" placeholder="Content..."></textarea><label>Icon URL</label><input id="ic" placeholder="https://..." value="https://cdn-icons-png.flaticon.com/512/1156/1156948.png"><label>Image URL</label><input id="i" placeholder="https://..."><label>Click URL</label><input id="u" placeholder="https://..."><label>Schedule (Optional)</label><input type="datetime-local" id="schedule_picker" style="color-scheme:dark"><button onclick="send()">BROADCAST / SCHEDULE</button><div id="log"></div><div id="pending_list" style="margin-top:20px; border-top:1px dashed #444; padding-top:10px;"></div>
    <div style="margin-top:30px; border-top:1px dashed #444; padding-top:20px;"><h2 style="color:#eab308; font-size:18px;">Analytics</h2><h3 style="margin-top:10px; font-size:14px; color:#888;">Engagement</h3><canvas id="bcChart" style="max-height:250px"></canvas><br><h3 style="border-top:1px solid #333; padding-top:10px; font-size:14px; color:#888;">Top Link Clicks</h3><canvas id="linkChart" style="max-height:250px"></canvas><br><h3 style="border-top:1px solid #333; padding-top:10px; font-size:14px; color:#888;">History</h3><div id="bc_stats_list" style="font-size:13px; text-align:left"></div>{enhanced_analytics_html}{tier2_html}{toolbox_html}</div>{leads_html}</div>
    <div id="importModal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.9); z-index:10000; overflow:auto;">
        <div style="background:#222; max-width:600px; margin:50px auto; border-radius:15px; border:2px solid #eab308; padding:30px; position:relative;">
            <button onclick="closeImportModal()" style="position:absolute; top:15px; right:15px; background:transparent; border:none; color:#fff; font-size:30px; cursor:pointer; width:auto; padding:5px;">&times;</button>
            
            <h2 style="color:#eab308; margin-top:0;">Import Links from Bio Page</h2>
            <p style="font-size:13px; color:#aaa; margin-bottom:20px;">Paste a Linktree, Beacons, or any bio link URL below:</p>
            
            <div style="display:flex; gap:10px; margin-bottom:20px;">
                <input id="import_url" placeholder="https://linktr.ee/username" style="flex:1;">
                <button onclick="fetchImportLinks()" style="width:auto; padding:10px 20px;">Fetch Links</button>
            </div>
            
            <div id="import_status" style="margin-bottom:15px; font-size:13px;"></div>
            
            <div id="import_results" style="max-height:400px; overflow-y:auto;"></div>
            <button onclick="finishImport()" style="margin-top:15px;width:100%;background:#eab308;color:#111;font-weight:bold;"> Done </button>
        </div>
    </div>
    <script>
    const handle="{handle}";const pin="{pin}";const shareUrl=location.protocol+'//'+location.host+'/c/'+handle;document.getElementById('linkbox').innerText=shareUrl;
    function cp(){{navigator.clipboard.writeText(shareUrl);alert('Copied!');}}
    let currentLinks = []; try {{ currentLinks = JSON.parse(atob('{b64_links}')); }} catch(e) {{ currentLinks = []; }}
    function renderLinks() {{ const cont = document.getElementById('link_list_ui'); cont.innerHTML = ''; currentLinks.forEach((l, i) => {{ cont.innerHTML += `<div class="link-item"><div style="flex-grow:1"><input value="${{l.label}}" onchange="currentLinks[${{i}}].label=this.value" style="width:100%;margin:2px 0"><input value="${{l.url}}" onchange="currentLinks[${{i}}].url=this.value" style="width:100%;margin:2px 0;font-size:11px;color:#aaa"></div><div style="display:flex;flex-direction:column;gap:2px"><button onclick="moveLink(${{i}}, -1)" style="width:30px;padding:5px;font-size:10px;margin:0;background:#444">↑</button><button onclick="moveLink(${{i}}, 1)" style="width:30px;padding:5px;font-size:10px;margin:0;background:#444">↓</button></div><button onclick="removeLink(${{i}})" style="width:30px;background:#f87171;color:white;margin-left:5px">X</button></div>`; }}); }}
    function moveLink(i, dir) {{ if (dir === -1 && i === 0) return; if (dir === 1 && i === currentLinks.length - 1) return; const temp = currentLinks[i]; currentLinks[i] = currentLinks[i + dir]; currentLinks[i + dir] = temp; renderLinks(); }}
    function addLink() {{ const lbl = document.getElementById('new_link_label'); const url = document.getElementById('new_link_url'); if(!lbl.value || !url.value) return alert('Fill fields'); currentLinks.push({{label: lbl.value, url: url.value}}); lbl.value = ''; url.value = ''; renderLinks(); }}
    function removeLink(i) {{ currentLinks.splice(i, 1); renderLinks(); }}
    async function saveLinks() {{ const r = await fetch('/api/update_profile/'+handle, {{ method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify({{pin: pin, links: currentLinks}}) }}); const j = await r.json(); alert(j.msg); }}
    async function saveSkin() {{ const s = document.getElementById('skin_select').value; const r = await fetch('/api/update_profile/'+handle, {{ method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify({{pin: pin, skin: s}}) }}); const j = await r.json(); if(j.success) location.reload(); else alert(j.msg); }}
    async function saveBio() {{ const b = document.getElementById('bio_text').value; const r = await fetch('/api/update_profile/'+handle, {{ method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify({{pin: pin, bio: b}}) }}); const j = await r.json(); alert(j.msg); }}
    function compressAndUpload(file, maxWidth, url, msgId) {{ const reader = new FileReader(); reader.readAsDataURL(file); reader.onload = event => {{ const img = new Image(); img.src = event.target.result; img.onload = () => {{ const elem = document.createElement('canvas'); let width = img.width; let height = img.height; if (width > maxWidth) {{ height = Math.round(height * (maxWidth / width)); width = maxWidth; }} elem.width = width; elem.height = height; const ctx = elem.getContext('2d'); ctx.drawImage(img, 0, 0, width, height); elem.toBlob(async (blob) => {{ document.getElementById(msgId).innerText = "Uploading..."; const r = await fetch(url + '?pin=' + pin, {{ method: 'POST', body: blob }}); const j = await r.json(); if(j.success) {{ document.getElementById(msgId).innerHTML='<div class="toast">Updated!</div>'; setTimeout(()=>location.reload(), 1000); }} else document.getElementById(msgId).innerHTML='<div class="err">'+j.msg+'</div>'; }}, 'image/jpeg', 0.85); }} }} }}
    function upAv(){{ const f = document.getElementById('upfile').files[0]; if(!f) return alert('Select file'); document.getElementById('upmsg').innerText = "Processing..."; compressAndUpload(f, 800, '/api/upload_avatar/'+handle, 'upmsg'); }}
    function upBanner(){{ const f = document.getElementById('upbanner').files[0]; if(!f) return alert('Select file'); document.getElementById('bannermsg').innerText = "Processing..."; compressAndUpload(f, 1200, '/api/upload_banner/'+handle, 'bannermsg'); }}
    async function send(){{ const t=document.getElementById('t').value; const b=document.getElementById('b').value; const picker=document.getElementById('schedule_picker').value; let u=document.getElementById('u').value; if(u && !u.startsWith('http')) u = 'https://' + u; if(!t||!b)return alert('Title/Body required'); let payload = {{pin:pin,title:t,body:b,icon:document.getElementById('ic').value,image:document.getElementById('i').value,url:u}}; if(picker) {{ const dateObj = new Date(picker); payload.schedule_ts = Math.floor(dateObj.getTime() / 1000); document.getElementById('log').innerText="Scheduling..."; }} else {{ document.getElementById('log').innerText="Queuing..."; }} const r=await fetch('/api/broadcast/'+handle,{{ method:'POST', headers: {{'Content-Type': 'application/json'}}, body:JSON.stringify(payload) }}); const j=await r.json(); if(j.success || j.status) {{ if(picker) {{ document.getElementById('log').innerHTML='<div class="toast">'+j.msg+'</div>'; document.getElementById('schedule_picker').value = ""; loadSchedule(); }} else {{ document.getElementById('log').innerHTML='<div class="toast">Queued '+j.count+' msgs!</div>'; }} }} else document.getElementById('log').innerHTML='<div class="err">'+j.error+'</div>'; }}
    async function loadSchedule() {{ const r = await fetch('/api/get_schedule/'+handle+'?pin='+pin); const data = await r.json(); let html = '<h3 style="font-size:14px;color:#eab308">Pending Schedule</h3>'; if(data.length === 0) html += '<div style="font-size:12px;color:#666">No pending posts.</div>'; data.forEach(item => {{ html += `<div style="background:#222;padding:8px;margin-bottom:5px;border-radius:5px;display:flex;justify-content:space-between;align-items:center"><div><div style="font-size:12px;font-weight:bold">${{item.title}}</div><div style="font-size:11px;color:#aaa">Run: ${{item.date}}</div></div><button onclick="cancelSchedule(${{item.id}})" style="width:auto;padding:5px 10px;background:#f87171;font-size:10px">X</button></div>`; }}); document.getElementById('pending_list').innerHTML = html; }}
    async function cancelSchedule(id) {{ if(!confirm("Cancel?")) return; await fetch('/api/cancel_schedule/'+handle, {{ method:'POST', headers: {{'Content-Type': 'application/json'}}, body:JSON.stringify({{id:id, pin:pin}}) }}); loadSchedule(); }}
    async function loadStats(){{ const r = await fetch('/api/stats/'+handle+'?pin='+pin); const d = await r.json(); const charts = d.charts; let bhtml = '<table style="width:100%;border-collapse:collapse;font-size:11px;"><tr><th style="text-align:left">Title</th><th style="text-align:right">Sent</th><th style="text-align:right">Click</th><th style="text-align:right">Dism</th><th style="text-align:right">CTR</th></tr>'; d.history.forEach(h => {{ bhtml += `<tr><td style="border-bottom:1px solid #333;padding:5px"><div style="font-weight:bold">${{h.title}}</div><div style="font-size:10px;color:#666">${{h.date}}</div></td><td style="text-align:right;border-bottom:1px solid #333;padding:5px">${{h.sent}}</td><td style="text-align:right;border-bottom:1px solid #333;padding:5px;color:#4ade80">${{h.clicks}}</td><td style="text-align:right;border-bottom:1px solid #333;padding:5px;color:#f87171">${{h.dismissed}}</td><td style="text-align:right;border-bottom:1px solid #333;padding:5px">${{h.ctr}}%</td></tr>` }}); document.getElementById('bc_stats_list').innerHTML = bhtml + '</table>'; new Chart(document.getElementById('bcChart').getContext('2d'), {{ type: 'line', data: {{ labels: charts.labels, datasets: [ {{ label: 'Sends', data: charts.broadcast_sends, borderColor: '#555', tension: 0.3, borderDash: [5, 5] }}, {{ label: 'Clicks', data: charts.broadcast_clicks, borderColor: '#4ade80', backgroundColor: 'rgba(74, 222, 128, 0.1)', tension: 0.3 }}, {{ label: 'Dismiss', data: charts.broadcast_dismiss, borderColor: '#f87171', tension: 0.3 }}, {{ label: 'Fail', data: charts.broadcast_fails, borderColor: '#fbbf24', tension: 0.3 }} ] }}, options: {{ responsive: true, interaction: {{mode:'index', intersect:false}}, scales: {{ y: {{ beginAtZero: true, grid: {{color:'#333'}} }}, x: {{ grid: {{display:false}} }} }} }} }}); const linkColors = ['#38bdf8', '#fb7185', '#a78bfa', '#34d399', '#fbbf24']; const linkDatasets = charts.links.map((l, i) => ({{ label: l.label, data: l.data, borderColor: linkColors[i % linkColors.length], tension: 0.3 }})); if(linkDatasets.length === 0) linkDatasets.push({{ label: 'No Data', data: [0,0,0,0,0,0,0], borderColor: '#333' }}); new Chart(document.getElementById('linkChart').getContext('2d'), {{ type: 'line', data: {{ labels: charts.labels, datasets: linkDatasets }}, options: {{ responsive: true, interaction: {{mode:'index', intersect:false}}, scales: {{ y: {{ beginAtZero: true, grid: {{color:'#333'}} }}, x: {{ grid: {{display:false}} }} }} }} }}); }}
    // LINK IMPORTER FUNCTIONS
    function openImportModal() {{
        document.getElementById('importModal').style.display = 'block';
        document.body.style.overflow = 'hidden';
    }}

    function closeImportModal() {{
        document.getElementById('importModal').style.display = 'none';
        document.body.style.overflow = 'auto';
    }}

    async function fetchImportLinks() {{
        const url = document.getElementById('import_url').value.trim();
        const status = document.getElementById('import_status');
        const results = document.getElementById('import_results');
        
        if (!url) {{
            status.innerHTML = '<div style="color:#f87171;">Please enter a URL</div>';
            return;
        }}
        
        status.innerHTML = '<div style="color:#eab308;">Fetching links...</div>';
        results.innerHTML = '';
        
        try {{
            const r = await fetch('/api/import_links', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{
                    handle: handle,
                    pin: pin,
                    action: 'fetch',
                    url: url
                }})
            }});
            
            const data = await r.json();
            
            if (data.success) {{
                status.innerHTML = '<div style="color:#4ade80;">' + data.msg + '</div>';
                
                let html = '<div style="background:#111; padding:15px; border-radius:8px; border:1px solid #333;">';
                html += '<div style="font-size:12px; color:#888; margin-bottom:10px;">Toggle switches to add/remove links:</div>';
                
                data.links.forEach((link, idx) => {{
                    const checked = link.exists ? 'checked' : '';
                    const linkId = 'import_link_' + idx;
                    
                    html += '<div style="display:flex; align-items:center; justify-content:space-between; padding:10px; background:#222; margin-bottom:8px; border-radius:6px; border:1px solid #333;">';
                    html += '<div style="flex:1; overflow:hidden;">';
                    html += '<div style="font-weight:bold; font-size:13px; color:#fff; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">' + link.label + '</div>';
                    html += '<div style="font-size:11px; color:#666; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">' + link.url + '</div>';
                    html += '</div>';
                    html += '<label class="switch" style="margin-left:10px;"><input type="checkbox" id="' + linkId + '" ' + checked + ' onchange="toggleImportLink(' + idx + ', this.checked)"><span class="slider round"></span></label>';
                    html += '</div>';
                }});
                
                html += '</div>';
                results.innerHTML = html;
                
                window.importedLinks = data.links;
            }} else {{
                status.innerHTML = '<div style="color:#f87171;">Error: ' + data.msg + '</div>';
                results.innerHTML = '';
            }}
        }} catch (err) {{
            status.innerHTML = '<div style="color:#f87171;">Connection error</div>';
            console.error(err);
        }}
    }}

    async function toggleImportLink(idx, enabled) {{
        const link = window.importedLinks[idx];
        
        try {{
            const r = await fetch('/api/import_links', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{
                    handle: handle,
                    pin: pin,
                    action: 'toggle',
                    label: link.label,
                    url: link.url,
                    enabled: enabled
                }})
            }});
            
            const data = await r.json();
            
            if (data.success) {{
                link.exists = enabled;
            }} else {{
                alert('Error: ' + data.msg);
                document.getElementById('import_link_' + idx).checked = !enabled;
            }}
        }} catch (err) {{
            alert('Connection error');
            document.getElementById('import_link_' + idx).checked = !enabled;
        }}
    }}

    function finishImport() {{
        closeImportModal();
        location.reload();
    }}

    renderLinks(); loadStats(); loadSchedule();
    </script></body></html>"""

def render_public_page(handle, pub_key, config):
    current_skin = config.get('skin', 'default')
    head = get_head(current_skin)
    if nsfw_gate: head += f"<style>{nsfw_gate.get_css()}</style>"
    if favicon: head += f"<style>{favicon.get_css()}</style>"

    links = config.get('links', [])
    bio = config.get('bio', '')
    bio_html = ""
    if bio:
        bio_html = re.sub(r'#(\w+)', r'<a href="/explore/\1">#\1</a>', bio)
        bio_html = f'<div style="margin:10px 0;font-size:14px;color:#ccc;line-height:1.4">{bio_html}</div>'

    buttons_html, embeds_html = process_links_for_embeds(links)
    final_html = '<div class="link-stack">' + buttons_html + '</div>'
    js_inject = nsfw_gate.get_js() if nsfw_gate else ""
    if nsfw_gate and nsfw_gate.get_gate_status(DB, handle): js_inject += nsfw_gate.get_gate_js(handle)
    store_html = ""
    if premium_tier_2 and store:
        res = premium_tier_2.execute_module(DB.conn, handle, "store", "render_public")
        if res.get("success"):
            store_html = res.get("html", "")

    is_premium = False
    if premium_tier:
        p_stat = premium_tier.get_channel_status(DB.conn, handle)
        is_premium = p_stat['locked']

    has_banner = False
    if banners: has_banner = banners.get_banner_path(handle) is not None
    has_avatar = (AVATAR_DIR / handle).exists()

    premium_css = get_premium_ux_css(handle)
    if premium_css:
        head += premium_css
    
    if social_cards:
        # Check if channel is gated
        is_gated = False
        if nsfw_gate:
            is_gated = nsfw_gate.get_gate_status(DB, handle)
            
        meta_tags = social_cards.get_tags(
            handle, 
            config.get('bio', ''), 
            config.get('links', []), 
            has_banner, 
            has_avatar, 
            CF_DOMAIN,
            is_gated=is_gated # Pass the status
        )
        head += meta_tags

    if has_banner:
        visual_header = f'''<div style="position:relative; width:calc(100% + 60px); margin-left:-30px; height:180px; background-image:url(/banner/{handle}); background-size:cover; background-position:center; margin-top:15px; margin-bottom:60px;"><img src="/avatar/{handle}" loading="lazy" onerror="this.style.display='none'" style="width:100px; height:100px; object-fit:cover; border-radius:50%; border:5px solid var(--card); position:absolute; bottom:-50px; left:50%; transform:translateX(-50%); z-index:10; background:var(--card);"></div>'''
    else:
        visual_header = f'''<img src="/avatar/{handle}" class="av-prev" loading="lazy" onerror="this.style.display='none'" style="width:80px;height:80px;object-fit:cover;border-radius:50%;margin:20px auto;border:2px solid var(--primary);display:block;">'''
        
    gallery_html = ""
    if is_premium:
        gallery_items = premium_tier.get_gallery(DB.conn, handle)
        if gallery_items:
            # We serialize the gallery items to JSON so JS can build the Reels UI
            import json
            items_json = json.dumps(gallery_items)
            
            # The Grid View (Thumbnails)
            items_html = ""
            for idx, item in enumerate(gallery_items):
                # Default: Emoji Icon for Video/Audio
                content = f'<div class="prem-icon">{"🎬" if item["type"] == "video" else "🎵"}</div>'
                style = ""

                # Logic: If it is an image, use it as the background
                if item['type'] == 'image':
                    content = "" # Remove the emoji
                    # Use the image URL as the background
                    style = f"background-image: url('{item['url']}'); background-size: cover; background-position: center;"
                
                items_html += f"""<div class="prem-item" onclick="openReels({idx})" style="{style}">{content}</div>"""
            
            # NOTE: We use a standard string here (not f-string) to avoid syntax errors with JS braces
            gallery_template = """
            <div style="margin-top:20px; border-top:1px dashed #333; padding-top:20px">
                <h3 style="color:var(--primary); font-size:14px; margin:0">PREMIUM GALLERY</h3>
                <div class="prem-gallery">__ITEMS_HTML__</div>
            </div>
            
            <div id="reels_overlay" class="hidden prem-overlay">
                <div class="prem-close" onclick="closeReels()">×</div>
                <div id="reels_container" class="reels-container">
                    </div>
            </div>

            <script>
            const galleryData = __ITEMS_JSON__;
            let visitorId = localStorage.getItem('notifly_vid');
            if(!visitorId) { visitorId = Math.random().toString(36).substring(2) + Date.now().toString(36); localStorage.setItem('notifly_vid', visitorId); }

            function openReels(startIndex) {
                const overlay = document.getElementById('reels_overlay');
                const container = document.getElementById('reels_container');
                overlay.classList.remove('hidden');
                document.body.style.overflow = 'hidden'; // Lock body scroll

                container.innerHTML = '';
                
                galleryData.forEach((item, index) => {
                    const reelDiv = document.createElement('div');
                    reelDiv.className = 'reel-item';
                    reelDiv.id = 'reel_' + index;
                    
                    let mediaContent = '';
                    if(item.type === 'video') {
                        // Videos don't autoplay immediately to save data
                        mediaContent = `<video class="reel-media" controls playsinline loop preload="metadata"><source src="${item.url}" type="video/mp4"></video>`;
                    } else if (item.type === 'image') {
                        mediaContent = `<img class="reel-media" src="${item.url}">`;
                    } else {
                        mediaContent = `<audio class="reel-media" controls style="width:80%"><source src="${item.url}"></audio>`;
                    }

                    // Check local storage for vote state
                    const myVote = localStorage.getItem('vote_' + item.id);
                    const likeActive = myVote == '1' ? 'active' : '';
                    const dislikeActive = myVote == '-1' ? 'active' : '';

                    reelDiv.innerHTML = `
                        ${mediaContent}
                        <div class="reel-info">
                            <div style="font-weight:bold">${item.name}</div>
                            <div style="font-size:11px;opacity:0.8">${item.size}</div>
                        </div>
                        <div class="reel-actions">
                            <div class="action-btn ${likeActive}" id="like_btn_${item.id}" onclick="voteMedia(${item.id}, 1)">
                                <span>♥</span>
                                <span class="action-count" id="like_cnt_${item.id}">${item.likes}</span>
                            </div>
                            <div class="action-btn ${dislikeActive}" id="dislike_btn_${item.id}" onclick="voteMedia(${item.id}, -1)">
                                <span>👎</span>
                                <span class="action-count" id="dislike_cnt_${item.id}">${item.dislikes}</span>
                            </div>
                            <div class="action-btn" onclick="shareMedia(${index})">
                                <span>🔗</span>
                                <span class="action-count">Share</span>
                            </div>
                        </div>
                    `;
                    container.appendChild(reelDiv);
                });

                // Scroll to selected
                setTimeout(() => {
                    const target = document.getElementById('reel_' + startIndex);
                    if(target) target.scrollIntoView();
                }, 10);
            }

            function closeReels() {
                document.getElementById('reels_overlay').classList.add('hidden');
                document.getElementById('reels_container').innerHTML = ''; // Clear to stop videos
                document.body.style.overflow = 'auto';
            }

            async function voteMedia(mediaId, val) {
                const currentVote = localStorage.getItem('vote_' + mediaId);
                // Optimistic UI Update
                document.getElementById('like_btn_'+mediaId).classList.remove('active');
                document.getElementById('dislike_btn_'+mediaId).classList.remove('active');
                
                if (val === 1) document.getElementById('like_btn_'+mediaId).classList.add('active');
                else document.getElementById('dislike_btn_'+mediaId).classList.add('active');

                localStorage.setItem('vote_' + mediaId, val);

                const r = await fetch('/api/vote_media', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({id: mediaId, vid: visitorId, vote: val})
                });
                const j = await r.json();
                if(j.success) {
                    document.getElementById('like_cnt_'+mediaId).innerText = j.likes;
                    document.getElementById('dislike_cnt_'+mediaId).innerText = j.dislikes;
                }
            }

            async function shareMedia(index) {
                const item = galleryData[index];
                const fullUrl = location.origin + item.url;
                if (navigator.share) {
                    try {
                        await navigator.share({ title: item.name, text: 'Check out this media on ' + HANDLE, url: fullUrl });
                    } catch (err) { console.error(err); }
                } else {
                    navigator.clipboard.writeText(fullUrl);
                    alert("Media link copied to clipboard!");
                }
            }
            </script>
            """
            
            # Inject the python variables manually
            gallery_html = gallery_template.replace("__ITEMS_HTML__", items_html).replace("__ITEMS_JSON__", items_json)
    
    waitlist_html = ""
    if email_form: waitlist_html = email_form.render_modal(handle)

    live_btn_html = ""
    if livestream:
        status = livestream.get_live_status(DB.conn, handle)
        if status['is_live']:
            live_btn_html = f"""<a href="{status['url']}" style="display:block; margin: 15px 0; padding: 12px; background: #ef4444; color: white; text-align: center; border-radius: 8px; text-decoration: none; font-weight: bold; animation: pulse 1.5s infinite; border: 1px solid #b91c1c;">🔴 WATCH LIVESTREAM</a><style>@keyframes pulse {{ 0% {{ box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7); }} 70% {{ box-shadow: 0 0 0 10px rgba(239, 68, 68, 0); }} 100% {{ box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }} }}</style>"""

    if embeds_html: final_html += '<div class="embed-section">' + embeds_html + '</div>'
    
    # INJECT SHOUT OUT SLIDER
    if premium_tier_2 and shout_out:
        so_res = premium_tier_2.execute_module(DB.conn, handle, "shout_out", "render_public")
        if so_res['success']:
            final_html += so_res['html']

    if premium_tier_2:
        try:
            import tools.premium_ux as premium_ux
            # Note: We don't register an entry_point for Premium UX
            # because it's handled purely client-side via toolbox.py
            print("[Tier 2] Premium UX module loaded")
        except ImportError:
            print("[WARNING] Premium UX module not found")

    if toolbox:
        toolbox.init()

    if tawk_tool:
        final_html += tawk_tool.render_public(DB.conn, handle)

    if tally_tool:
        final_html += tally_tool.render_public(DB.conn, handle)

    portal_js = ""
    if is_premium and sub_portal:
        portal_js = """let portalBtn = document.getElementById('portal-btn'); if (!portalBtn) { portalBtn = document.createElement('a'); portalBtn.id = 'portal-btn'; portalBtn.href = '/portal?h=' + HANDLE; portalBtn.innerText = '👤 Subscriber Portal'; portalBtn.style.cssText = 'display:block; margin:10px 0; background:#222; color:#eab308; text-align:center; padding:10px; border-radius:8px; text-decoration:none; border:1px solid #eab308; font-size:12px; font-weight:bold;'; const btn = document.getElementById('btn'); btn.parentNode.insertBefore(portalBtn, btn.nextSibling); } if(isSub){ portalBtn.style.display = 'block'; } else { portalBtn.style.display = 'none'; }"""

    return f"""<!DOCTYPE html><html><head>{head}</head><body><div class="box"><h1>{handle}</h1><p style="margin-top:0; color:#888; font-size:13px;">Subscribe for updates.</p>{visual_header}{live_btn_html}{bio_html}<button id="btn" onclick="toggle()">Enable Notifications</button><button onclick="shareChannel()" style="margin-top:10px;background:#333;color:#fff;border:1px solid #444">Share Channel 🔗</button><div id="stat" style="margin-top:15px;font-size:13px;color:#888">Checking status...</div>{final_html}{store_html}{gallery_html}{waitlist_html}</div><script>{js_inject}
    const VAPID="{pub_key}";const HANDLE="{handle}";const STORAGE_KEY="notifly_channels";let swReg=null;let isSub=false;
    async function shareChannel() {{ if (navigator.share) {{ try {{ await navigator.share({{ title: 'Check out ' + HANDLE, text: 'Subscribe to ' + HANDLE, url: window.location.href }}); }} catch (err) {{ console.error(err); }} }} else {{ navigator.clipboard.writeText(window.location.href); alert("Link copied to clipboard!"); }} }}
    function urlB64ToUint8Array(base64String){{const padding='='.repeat((4-base64String.length%4)%4);const base64=(base64String+padding).replace(/\\-/g,'+').replace(/_/g,'/');const rawData=window.atob(base64);const outputArray=new Uint8Array(rawData.length);for(let i=0;i<rawData.length;++i)outputArray[i]=rawData.charCodeAt(i);return outputArray}}
    async function init(){{ if(!('serviceWorker' in navigator)) return; swReg = await navigator.serviceWorker.register('/sw.js'); const sub = await swReg.pushManager.getSubscription(); if(sub) {{ const response = await fetch('/api/verify_sub/'+HANDLE, {{ method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify({{endpoint: sub.endpoint}}) }}); const data = await response.json(); isSub = data.subscribed; let localChannels = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]'); if(isSub && !localChannels.includes(HANDLE)) {{ localChannels.push(HANDLE); localStorage.setItem(STORAGE_KEY, JSON.stringify(localChannels)); }} else if(!isSub && localChannels.includes(HANDLE)) {{ localChannels = localChannels.filter(h => h !== HANDLE); localStorage.setItem(STORAGE_KEY, JSON.stringify(localChannels)); }} }} else {{ isSub = false; }} updateUI(); }}
    function updateUI(){{ const btn = document.getElementById('btn'); const stat = document.getElementById('stat'); {portal_js} if(isSub){{ btn.innerText = "Unsubscribe"; btn.style.background = "#333"; btn.style.color = "#fff"; stat.innerText = "✅ You are subscribed to " + HANDLE; }}else{{ btn.innerText = "Subscribe"; btn.style.background = "#eab308"; btn.style.color = "#000"; stat.innerText = "❌ Not subscribed"; }} }}
    async function toggle(){{ const btn=document.getElementById('btn'); btn.disabled=true; let localChannels = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]'); let sub = await swReg.pushManager.getSubscription(); if(isSub){{ if(sub){{ await fetch('/api/sub/'+HANDLE,{{method:'DELETE',headers:{{'Content-Type': 'application/json'}},body:JSON.stringify({{endpoint:sub.endpoint}})}}); }} localChannels = localChannels.filter(h => h !== HANDLE); localStorage.setItem(STORAGE_KEY, JSON.stringify(localChannels)); isSub=false; }}else{{ if(!sub){{ sub=await swReg.pushManager.subscribe({{userVisibleOnly:true,applicationServerKey:urlB64ToUint8Array(VAPID)}}); }} await fetch('/api/sub/'+HANDLE,{{method:'POST',headers:{{'Content-Type': 'application/json'}},body:JSON.stringify(sub)}}); if(!localChannels.includes(HANDLE)){{ localChannels.push(HANDLE); localStorage.setItem(STORAGE_KEY, JSON.stringify(localChannels)); }} isSub=true; }} updateUI(); btn.disabled=false; }}
    init(); </script></body></html>"""

# --- FLASK APP ---
app = Flask(__name__)

from flask_compress import Compress
Compress(app)

@app.route('/')
def home():
    return render_home_page()

@app.route('/guide')
def guide():
    return render_guide_page()

@app.route('/sw.js')
def service_worker():
    return send_file("sw.js", mimetype="application/javascript")

@app.route('/manifest.json')
def manifest():
    return Response(MANIFEST, mimetype="application/json")

@app.route('/robots.txt')
def robots_txt():
    # This tells Google: "Allowed to crawl everything, and my sitemap is here."
    content = "User-agent: *\nAllow: /\nSitemap: https://notifly.cc/sitemap.xml"
    return Response(content, mimetype="text/plain")

@app.route('/icon.svg')
def serve_icon_svg():
    return Response(ICON_SVG, mimetype="image/svg+xml")

@app.route('/icon-192.png')
def serve_icon_png():
    try: return send_file("icon-192.png", mimetype="image/png")
    except FileNotFoundError: return "Icon not found", 404

@app.route('/icon-512.png')
def serve_icon_512():
    try: return send_file("icon-512.png", mimetype="image/png")
    except FileNotFoundError: return "Icon not found", 404

@app.route('/badge.svg')
def serve_badge():
    return Response(BADGE_SVG, mimetype="image/svg+xml")

@app.route('/skins/<path:filename>')
def serve_skin(filename):
    safe_path = SKINS_DIR / filename
    if safe_path.exists() and SKINS_DIR.resolve() in safe_path.resolve().parents:
        return send_file(safe_path, mimetype="text/css")
    return "Skin not found", 404

@app.route('/video/<path:filename>')
def serve_video(filename):
    possible_paths = [Path("readme") / filename, Path(filename)]
    video_path = next((p for p in possible_paths if p.exists()), None)
    if video_path: return send_file(video_path, mimetype="video/mp4")
    return "Video not found", 404

@app.route('/premium_media/<path:filename>')
def serve_premium_media(filename):
    if not premium_tier: return "Premium Not Loaded", 404
    file_path = PREMIUM_MEDIA_DIR / filename
    if file_path.exists():
        if filename.endswith('.mp4'): mime = 'video/mp4'
        elif filename.endswith('.mp3'): mime = 'audio/mpeg'
        elif filename.endswith('.jpg'): mime = 'image/jpeg'
        elif filename.endswith('.png'): mime = 'image/png'
        else: mime = 'application/octet-stream'
        return send_file(file_path, mimetype=mime)
    return "File not found", 404

@app.route('/c/<handle>/blog/<blog_slug>.xml')
def serve_blog_rss(handle, blog_slug):
    """Serve RSS feed for a blog"""
    try:
        # Import blog tool dynamically
        import sys
        from pathlib import Path
        tools_dir = Path("tools")
        if str(tools_dir) not in sys.path:
            sys.path.insert(0, str(tools_dir))
        
        import blog
        
        # Verify channel exists
        pub_key = CM.get_public_key(handle)
        if not pub_key:
            return "Channel not found", 404
        
        # Get blog and generate RSS
        blog_conn = blog.get_blog_conn()
        blog_data = blog.get_blog_by_slug(blog_conn, handle, blog_slug)
        
        if not blog_data:
            blog_conn.close()
            return "Blog not found", 404
        
        posts = blog.get_blog_posts(blog_conn, blog_data['id'])
        rss_xml = blog.generate_rss_feed(blog_data, posts)
        blog_conn.close()
        
        return Response(rss_xml, mimetype="application/rss+xml")
        
    except Exception as e:
        print(f"[RSS Error] {e}")
        return "RSS generation failed", 500

@app.route('/c/<handle>')
def public_channel(handle):
    pub = CM.get_public_key(handle)
    if not pub:
        return "Channel not found.", 404
    
    config = CM.get_config(handle)
    
    # ============================================
    # PREMIUM UX CHECK - ATTEMPT TIER 2 RENDER
    # ============================================
    if premium_tier_2:
        try:
            # Check if Premium UX is enabled
            ux_config = premium_tier_2.get_module_config(DB.conn, handle, "premium_ux")
            
            if ux_config.get("enabled", False):
                # Import the renderer
                import tools.premium_ux as premium_ux_mod
                
                # Build FULL context (same as standard render)
                links = config.get('links', [])
                bio = config.get('bio', '')
                has_avatar = CM.get_avatar_path(handle) is not None
                has_banner = banners.get_banner_path(handle) is not None if banners else False
                
                # Premium status
                is_premium = False
                if premium_tier:
                    p_stat = premium_tier.get_channel_status(DB.conn, handle)
                    is_premium = p_stat['locked']
                
                # Build components (same logic as render_public_page)
                buttons_html, embeds_html = process_links_for_embeds(links)
                
                # Live button
                live_btn_html = ""
                if livestream:
                    status = livestream.get_live_status(DB.conn, handle)
                    if status['is_live']:
                        live_btn_html = f"""<a href="{status['url']}" style="display:block; margin: 15px 0; padding: 12px; background: #ef4444; color: white; text-align: center; border-radius: 8px; text-decoration: none; font-weight: bold; animation: pulse 1.5s infinite; border: 1px solid #b91c1c;">🔴 WATCH LIVESTREAM</a><style>@keyframes pulse {{ 0% {{ box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7); }} 70% {{ box-shadow: 0 0 0 10px rgba(239, 68, 68, 0); }} 100% {{ box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }} }}</style>"""
                
                # Gallery
                gallery_html = ""
                if is_premium and premium_tier:
                    gallery_items = premium_tier.get_gallery(DB.conn, handle)
                    if gallery_items:
                        items_json = json.dumps(gallery_items)
                        items_html = ""
                        for idx, item in enumerate(gallery_items):
                            content = f'<div class="prem-icon">{"🎬" if item["type"] == "video" else "🎵"}</div>'
                            style = ""
                            if item['type'] == 'image':
                                content = ""
                                style = f"background-image: url('{item['url']}'); background-size: cover; background-position: center;"
                            items_html += f"""<div class="prem-item" onclick="openReels({idx})" style="{style}">{content}</div>"""
                        
                        gallery_html = f"""<div style="margin-top:20px; border-top:1px dashed #333; padding-top:20px"><h3 style="color:var(--primary); font-size:14px; margin:0">PREMIUM GALLERY</h3><div class="prem-gallery">{items_html}</div></div>"""
                        # Add reels overlay and JS (you have this in your current code)
                
                # Shout-outs
                shout_outs_html = ""
                if premium_tier_2 and shout_out:
                    so_res = premium_tier_2.execute_module(DB.conn, handle, "shout_out", "render_public")
                    if so_res.get('success'):
                        shout_outs_html = so_res.get('html', '')
                
                # Store
                store_html = ""
                if premium_tier_2 and store:
                    st_res = premium_tier_2.execute_module(DB.conn, handle, "store", "render_public")
                    if st_res.get("success"):
                        store_html = st_res.get("html", "")
                
                # Waitlist
                waitlist_html = ""
                if email_form:
                    waitlist_html = email_form.render_modal(handle)
                
                # NSFW
                nsfw_js = ""
                nsfw_css = ""
                if nsfw_gate:
                    nsfw_css = nsfw_gate.get_css()
                    nsfw_js = nsfw_gate.get_js()
                    if nsfw_gate.get_gate_status(DB, handle):
                        nsfw_js += nsfw_gate.get_gate_js(handle)
                
                # Portal
                portal_js = ""
                if is_premium and sub_portal:
                    portal_js = """let portalBtn = document.getElementById('portal-btn'); if(portalBtn && isSub){ portalBtn.style.display = 'block'; }"""
                
                # Tawk
                tawk_html = ""
                if tawk_tool:
                    tawk_html = tawk_tool.render_public(DB.conn, handle)
                
                # Build context
                context = {
                    'links': links,
                    'bio': bio,
                    'has_avatar': has_avatar,
                    'has_banner': has_banner,
                    'is_premium': is_premium,
                    'pub_key': pub,
                    'live_btn_html': live_btn_html,
                    'gallery_html': gallery_html,
                    'shout_outs_html': shout_outs_html,
                    'store_html': store_html,
                    'waitlist_html': waitlist_html,
                    'nsfw_js': nsfw_js,
                    'nsfw_css': nsfw_css,
                    'portal_js': portal_js,
                    'tawk_html': tawk_html
                }
                
                # Call renderer
                template_id = ux_config.get("template", "digital_walls")
                if template_id == "digital_walls":
                    html = premium_ux_mod.render_digital_walls(handle, context)
                    return html
                    
        except Exception as e:
            print(f"[Premium UX Error] {e}")
            import traceback
            traceback.print_exc()
    
    # ============================================
    # FALLBACK: Standard Rendering
    # ============================================
    return render_public_page(handle, pub, config)

# ============================================================================
# That's the only change needed!
# ============================================================================

# The toolbox.py system will handle everything else automatically:
# - Loading the tool
# - Saving configuration
# - UI rendering in admin panel

# When you add more templates later, just create new .json files in 
# premium_ux_templates/ directory with this structure:
"""
{
  "name": "Template Name",
  "description": "Description of the template",
  "css": "... CSS code ...",
  "js": "... JavaScript code ...",
  "renderer": "function_name_in_premium_ux_py"
}
"""

# Then add the corresponding render function to tools/premium_ux.py:
"""
def render_template_name(handle, links, bio, has_avatar, has_banner):
    # Build your custom HTML here
    return html
"""

@app.route('/c/<handle>/<path:subpath>')
def livestream_viewer(handle, subpath):
    if subpath.startswith('Livestream'):
        if livestream:
            html_content = livestream.render_viewer_page(DB.conn, handle, subpath)
            if html_content: return html_content
            return "Stream Offline or Invalid", 404
        else: return "Livestream module missing", 501
    return redirect(f"/c/{handle}")

@app.route('/admin/crm/<handle>')
def admin_crm_dashboard(handle):
    pin = request.args.get('pin', '')
    check = CM.create_or_login(handle, pin)
    if check['status'] == 'error': return "Access Denied", 403
    if portal_dashboard: return portal_dashboard.render_dashboard(handle, pin)
    return "Module Missing", 501

@app.route('/admin/<handle>')
def admin_page(handle):
    pin = request.args.get('pin', '')
    return render_admin_page(handle, pin, CM.get_sub_count(handle), CM.get_avatar_path(handle) is not None, CM.get_config(handle))

@app.route('/explore/<tag>')
def explore_page(tag):
    if notifly_explore:
        p = int(request.args.get('p', 0))
        return notifly_explore.render(tag, p, DB, GLOBAL_VAPID.get_public_key())
    return "Explore module not loaded.", 500

@app.route('/avatar/<handle>')
def serve_avatar(handle):
    file_path = CM.get_avatar_path(handle)
    if not file_path: return "No Avatar", 404
    
    # Check for blur request
    if request.args.get('blur') == 'true':
        try:
            img = Image.open(file_path)
            # Apply strong Gaussian Blur
            img = img.filter(ImageFilter.GaussianBlur(20))
            
            # Save to memory buffer
            img_io = io.BytesIO()
            img.save(img_io, 'JPEG', quality=80)
            img_io.seek(0)
            return send_file(img_io, mimetype='image/jpeg')
        except Exception as e:
            print(f"[Avatar Blur Error] {e}")
            # Fallback to sending raw if blur fails, or return 500? 
            # Safer to return raw or a placeholder. Let's return raw for now to prevent broken images.
            return send_file(file_path, mimetype="image/jpeg")

    return send_file(file_path, mimetype="image/jpeg")

@app.route('/banner/<handle>')
def serve_banner(handle):
    if not banners: return "Banners not loaded", 501
    file_path = banners.get_banner_path(handle)
    if not file_path: return "No Banner", 404
    
    # Check for blur request
    if request.args.get('blur') == 'true':
        try:
            img = Image.open(file_path)
            img = img.filter(ImageFilter.GaussianBlur(20))
            
            img_io = io.BytesIO()
            img.save(img_io, 'JPEG', quality=80)
            img_io.seek(0)
            return send_file(img_io, mimetype='image/jpeg')
        except Exception as e:
            print(f"[Banner Blur Error] {e}")
            return send_file(file_path, mimetype="image/jpeg")

    return send_file(file_path, mimetype="image/jpeg")

# --- API ROUTES ---
@app.route('/api/import_links', methods=['POST'])
def api_import_links():
    if not link_importer:
        return jsonify({'success': False, 'msg': 'Importer module not loaded'})
    
    body = request.get_json(force=True)
    handle = body.get('handle')
    pin = body.get('pin')
    action = body.get('action')
    
    # Authenticate
    check = CM.create_or_login(handle, pin)
    if check['status'] == 'error':
        return jsonify({'success': False, 'msg': 'Auth Failed'})
    
    if action == 'fetch':
        # Fetch links from URL
        url = body.get('url', '')
        result = link_importer.fetch_links(url)
        
        if result['success']:
            # Mark which links already exist
            existing = link_importer.get_existing_urls(DB.conn, handle)
            for link in result['links']:
                link['exists'] = link['url'] in existing
        
        return jsonify(result)
    
    elif action == 'toggle':
        # Toggle individual link
        label = body.get('label')
        url = body.get('url')
        enabled = body.get('enabled')
        
        result = link_importer.toggle_link(DB.conn, handle, label, url, enabled)
        return jsonify(result)
    
    return jsonify({'success': False, 'msg': 'Invalid action'})

@app.route('/claim/<token>')
def claim_premium_page(token):
    """Renders a page for a user to claim their Premium upgrade via token."""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Claim Premium Upgrade</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ background: #111; color: #eee; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; display: flex; justify-content: center; padding: 20px; margin: 0; }}
            .box {{ background: #222; padding: 30px; border-radius: 15px; border: 1px solid #eab308; width: 100%; max-width: 450px; text-align: center; box-shadow: 0 4px 20px rgba(0,0,0,0.5); }}
            h1 {{ margin-top: 0; color: #eab308; font-size: 24px; }}
            
            /* Info Sections */
            .info-box {{ background: #1a1a1a; padding: 15px; border-radius: 8px; margin: 15px 0; text-align: left; font-size: 13px; color: #ccc; border-left: 3px solid #555; }}
            .info-box h3 {{ margin: 0 0 5px 0; color: #fff; font-size: 14px; }}
            .highlight {{ color: #eab308; font-weight: bold; }}
            
            /* Split Instructions */
            .split-guide {{ display: flex; gap: 10px; margin: 20px 0; text-align: left; }}
            .guide-step {{ flex: 1; background: #333; padding: 10px; border-radius: 8px; font-size: 12px; }}
            .guide-step strong {{ display: block; color: #fff; margin-bottom: 5px; font-size: 13px; }}
            .guide-step a {{ color: #4ade80; text-decoration: none; font-weight: bold; }}

            /* Form Elements */
            input {{ background: #111; color: white; border: 1px solid #444; padding: 12px; width: 100%; box-sizing: border-box; margin: 8px 0; border-radius: 8px; font-size: 14px; }}
            input:focus {{ border-color: #eab308; outline: none; }}
            button {{ background: #eab308; color: black; font-weight: bold; border: none; padding: 15px; width: 100%; border-radius: 8px; cursor: pointer; font-size: 16px; margin-top: 10px; transition: transform 0.1s; }}
            button:active {{ transform: scale(0.98); }}
            
            hr {{ border: 0; border-top: 1px dashed #444; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <div class="box">
            <h1>🎉 Premium Gift Found!</h1>
            
            <div class="info-box" style="border-left-color: #eab308;">
                <h3>🚀 What is NotiFly?</h3>
                NotiFly is a private broadcasting platform. It lets you create a <b>Channel</b> to send push notifications, host <span class="highlight">1GB of Premium Videos/Photos</span>, and share exclusive content with your subscribers.
            </div>

            <div class="split-guide">
                <div class="guide-step">
                    <strong>🆕 I am New</strong>
                    1. Go to the <a href="/" target="_blank">Home Page</a>.<br>
                    2. Create a <b>Channel Name</b> & <b>PIN</b>.<br>
                    3. Come back here.
                </div>
                <div class="guide-step">
                    <strong>😎 I have a Channel</strong>
                    Simply enter your existing <b>Handle</b> and <b>PIN</b> below to unlock Premium features instantly.
                </div>
            </div>

            <hr>

            <div style="text-align:left; font-size:12px; color:#aaa; margin-bottom:5px;">Enter Details to Upgrade:</div>
            <input id="h" placeholder="Channel Handle (e.g. my-cool-channel)">
            <input id="p" type="password" placeholder="Channel PIN">
            <button onclick="claim()">CLAIM UPGRADE 🔓</button>
            <div id="msg" style="margin-top:15px;font-size:13px"></div>
        </div>
        <script>
            async function claim() {{
                const h = document.getElementById('h').value;
                const p = document.getElementById('p').value;
                const msg = document.getElementById('msg');
                if(!h || !p) return alert("Please enter your Channel Handle and PIN first!");
                
                msg.innerHTML = "Verifying...";
                
                try {{
                    const r = await fetch('/api/redeem_token', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{ handle: h, pin: p, token: '{token}' }})
                    }});
                    
                    const j = await r.json();
                    if(j.success) {{
                        msg.innerHTML = '<div style="color:#4ade80; font-weight:bold; font-size:16px">✅ ' + j.msg + '</div><p>Redirecting to Admin...</p>';
                        setTimeout(() => window.location.href = '/admin/' + h + '?pin=' + p, 2000);
                    }} else {{
                        msg.innerHTML = '<div style="color:#f87171">❌ ' + j.msg + '</div>';
                    }}
                }} catch(e) {{
                    msg.innerHTML = '<div style="color:#f87171">Connection Error</div>';
                }}
            }}
        </script>
    </body>
    </html>
    """

@app.route('/api/redeem_token', methods=['POST'])
def api_redeem_token():
    if not premium_tier: return "Not loaded", 501
    body = request.get_json(force=True)
    handle = body.get('handle')
    pin = body.get('pin')
    token = body.get('token')
    
    # Verify Channel Ownership first
    check = CM.create_or_login(handle, pin)
    if check['status'] == 'error': return jsonify({'success': False, 'msg': 'Channel Auth Failed (Wrong PIN)'})
    
    # Redeem Token
    return jsonify(premium_tier.redeem_token(DB.conn, handle, token))

@app.route('/api/stats/<handle>')
def api_stats(handle):
    pin = request.args.get('pin', '')
    row = DB.query("SELECT pin FROM channels WHERE handle = ?", (handle,), one=True)
    if row and row['pin'] == pin: return jsonify(AM.get_stats(handle))
    return jsonify({"error": "Auth Failed"}), 403

@app.route('/api/get_schedule/<handle>')
def api_schedule(handle):
    pin = request.args.get('pin', '')
    row = DB.query("SELECT pin FROM channels WHERE handle = ?", (handle,), one=True)
    if row and row['pin'] == pin: return jsonify(SCHEDULER.get_pending(handle))
    return jsonify({"error": "Auth Failed"}), 403

@app.route('/api/export_leads/<handle>')
def api_export_leads(handle):
    if not email_form: return "Module missing", 501
    pin = request.args.get('pin', '')
    check = CM.create_or_login(handle, pin)
    if check['status'] == 'error': return "Forbidden", 403
    csv_data = email_form.get_leads_csv(DB.conn, handle)
    if csv_data:
        resp = make_response(csv_data)
        resp.headers['Content-Type'] = 'text/csv'
        resp.headers['Content-Disposition'] = f'attachment; filename="leads_{handle}.csv"'
        return resp
    return "No leads found."

@app.route('/trk/l/<link_id>')
def track_link(link_id):
    row = DB.query("SELECT url FROM links WHERE id = ?", (link_id,), one=True)
    if row:
        AM.log_event('link', link_id)
        return redirect(row['url'])
    return "Link not found", 404

@app.route('/trk/n/<bid>')
def track_notification(bid):
    row = DB.query("SELECT target_url FROM broadcast_history WHERE bid = ?", (bid,), one=True)
    if row:
        AM.log_event('notif', bid)
        return redirect(row['target_url'] or "/")
    return "Not found", 404

@app.route('/trk/d/<bid>')
def track_dismiss(bid):
    AM.log_event('dismiss', bid)
    return "OK"
@app.route('/trk/c/<cid>')
def track_campaign_click(cid):
    # 1. Lookup Campaign
    row = DB.query("SELECT target_url, handle, og_title, og_desc, og_image FROM campaigns WHERE id = ?", (cid,), one=True)
    if not row: return "Campaign expired or not found", 404
    
    # 2. Check for Social Bot (Facebook/Twitter/Discord crawlers)
    # If it's a bot, we just render the meta tags and DON'T count the click
    ua = request.user_agent.string.lower()
    bots = ['facebookexternalhit', 'twitterbot', 'linkedinbot', 'discordbot', 'whatsapp', 'telegrambot', 'skypeuripreview', 'slackbot']
    if any(bot in ua for bot in bots):
        # Render OpenGraph Card
        return f"""<!DOCTYPE html><html><head>
            <meta property="og:title" content="{row['og_title']}">
            <meta property="og:description" content="{row['og_desc']}">
            <meta property="og:image" content="{row['og_image']}">
            <meta property="og:url" content="{request.url}">
            <meta name="twitter:card" content="summary_large_image">
        </head><body></body></html>"""

    # 3. Log Analytics (Real User)
    referrer = request.referrer
    if referrer:
        try: referrer = urlparse(referrer).netloc
        except: pass
    
    # Insert granular record
    DB.execute("INSERT INTO campaign_analytics (cid, referrer, user_agent, timestamp) VALUES (?, ?, ?, ?)", 
               (cid, referrer or "", ua, int(time.time())))
    
    # Increment total counter
    DB.execute("UPDATE campaigns SET clicks = clicks + 1 WHERE id = ?", (cid,))
    
    # 4. Redirect
    return redirect(row['target_url'])

@app.route('/sitemap.xml')
def sitemap():
    if sitemap_gen:
        xml_content = sitemap_gen.generate_sitemap(DB, CF_DOMAIN)
        return Response(xml_content, mimetype="application/xml")
    return "Sitemap missing", 501

@app.route('/portal')
def portal():
    h = request.args.get('h', '')
    if not h: return "Missing Channel Handle", 400
    if sub_portal: return sub_portal.render_portal_page(h)
    return "Portal module missing", 501

@app.route('/api/crm/list/<handle>')
def api_crm_list(handle):
    pin = request.args.get('pin', '')
    check = CM.create_or_login(handle, pin)
    if check['status'] == 'error': return "Forbidden", 403
    if portal_dashboard: return jsonify(portal_dashboard.get_subscribers(DB, handle))
    return "CRM missing", 501

# --- POST ROUTES ---
@app.route('/api/upload_avatar/<handle>', methods=['POST'])
def upload_avatar(handle):
    pin = request.args.get('pin', '')
    # request.get_data() gets raw binary body, crucial for the JS compressor
    return jsonify(CM.save_avatar(handle, pin, request.get_data()))

@app.route('/api/upload_banner/<handle>', methods=['POST'])
def upload_banner(handle):
    if not banners: return jsonify({'success': False, 'msg': 'Module missing'})
    pin = request.args.get('pin', '')
    check = CM.create_or_login(handle, pin)
    if check['status'] == 'error': return jsonify({'success': False, 'msg': 'Auth Failed'})
    # request.get_data() gets raw binary body, crucial for the JS compressor
    return jsonify(banners.save_banner(handle, request.get_data()))

@app.route('/api/upload_premium_media/<handle>', methods=['POST'])
def upload_premium_media(handle):
    if not premium_tier: return "Not loaded", 501
    pin = request.args.get('pin', '')
    check = CM.create_or_login(handle, pin)
    if check['status'] == 'error': return jsonify({'success': False, 'msg': 'Auth Failed'})
    
    raw_data = request.get_data()
    length = len(raw_data)
    if length > 200 * 1024 * 1024: return "File too large", 413
    
    content_type = request.headers.get('Content-Type', 'application/octet-stream')
    ext = ".bin"
    if "video" in content_type: ext = ".mp4"
    elif "image" in content_type: ext = ".jpg"
    elif "audio" in content_type: ext = ".mp3"
    filename = f"media_{int(time.time())}{ext}"
    
    return jsonify(premium_tier.upload_media(DB.conn, handle, raw_data, filename, content_type))

@app.route('/api/login', methods=['POST'])
def api_login():
    body = request.get_json(force=True)
    return jsonify(CM.create_or_login(body.get('handle'), body.get('pin')))

@app.route('/api/premium_login', methods=['POST'])
def api_premium_login():
    if not premium_tier: return "Not loaded", 501
    body = request.get_json(force=True)
    return jsonify(premium_tier.login_and_lock(DB.conn, body.get('handle'), body.get('user'), body.get('pwd')))

@app.route('/api/sub/<handle>', methods=['POST', 'DELETE'])
def api_sub(handle):
    body = request.get_json(force=True)
    if request.method == 'POST':
        count = CM.add_sub(handle, body)
        if notifly_analytics:
            client_ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
            notifly_analytics.track_subscriber(DB, handle, body.get('endpoint'), request.headers, client_ip)
        return jsonify({'count': count})
    else:
        CM.remove_sub(handle, body.get('endpoint'))
        return jsonify({'status': 'ok'})

@app.route('/api/waitlist/<handle>', methods=['POST'])
def api_waitlist(handle):
    if not email_form: return "Module missing", 501
    body = request.get_json(force=True)
    return jsonify(email_form.save_lead(DB.conn, handle, body))

@app.route('/api/verify_sub/<handle>', methods=['POST'])
def api_verify_sub(handle):
    body = request.get_json(force=True)
    return jsonify({'subscribed': CM.verify_sub(handle, body.get('endpoint'))})

@app.route('/api/broadcast/<handle>', methods=['POST'])
def api_broadcast(handle):
    body = request.get_json(force=True)
    if 'schedule_ts' in body and body['schedule_ts']:
        return jsonify(SCHEDULER.add_schedule(handle, body.get('pin'), body, int(body['schedule_ts'])))
    return jsonify(CM.broadcast(handle, body.get('pin'), body))

@app.route('/api/cancel_schedule/<handle>', methods=['POST'])
def api_cancel_schedule(handle):
    body = request.get_json(force=True)
    SCHEDULER.cancel(handle, body.get('id'))
    return jsonify({'status': 'ok'})

@app.route('/api/update_profile/<handle>', methods=['POST'])
def api_update_profile(handle):
    body = request.get_json(force=True)
    return jsonify(CM.update_config(handle, body.get('pin'), body))

@app.route('/api/delete_premium_media/<handle>', methods=['POST'])
def api_delete_premium_media(handle):
    if not premium_tier: return "Not loaded", 501
    body = request.get_json(force=True)
    check = CM.create_or_login(handle, body.get('pin'))
    if check['status'] == 'error': return jsonify({'success': False, 'msg': 'Auth Failed'})
    return jsonify(premium_tier.delete_media(DB.conn, handle, body.get('id')))

@app.route('/api/toggle_gate/<handle>', methods=['POST'])
def api_toggle_gate(handle):
    if not nsfw_gate: return "Not loaded", 501
    body = request.get_json(force=True)
    check = CM.create_or_login(handle, body.get('pin'))
    if check['status'] == 'error': return jsonify({'success': False, 'msg': 'Auth Failed'})
    nsfw_gate.set_gate_status(DB, handle, body.get('enabled'))
    return jsonify({'success': True})

@app.route('/api/stream/<action>/<handle>', methods=['POST'])
def api_stream(action, handle):
    if not livestream or not premium_tier: return "Not loaded", 501
    pin = request.args.get('pin', '')
    check = CM.create_or_login(handle, pin)
    if check['status'] == 'error': return jsonify({'success': False, 'msg': 'Auth Failed'})
    
    p_stat = premium_tier.get_channel_status(DB.conn, handle)
    if not p_stat['locked']: return jsonify({'success': False, 'msg': 'Premium Only'})
    
    if action == 'start':
        body = request.get_json(force=True)
        return jsonify(livestream.go_live(DB.conn, handle, body.get('embed', '')))
    elif action == 'direct':
        return jsonify(livestream.go_live_direct(DB.conn, handle))
    elif action == 'stop':
        return jsonify(livestream.end_stream(DB.conn, handle))
    return "Invalid Action", 400

@app.route('/api/portal/get', methods=['POST'])
def api_portal_get():
    if not sub_portal: return "Not loaded", 501
    body = request.get_json(force=True)
    return jsonify(sub_portal.get_profile(DB, body.get('endpoint'), body.get('handle')))

@app.route('/api/portal/save', methods=['POST'])
def api_portal_save():
    if not sub_portal: return "Not loaded", 501
    body = request.get_json(force=True)
    return jsonify(sub_portal.update_profile(DB, body))

@app.route('/api/crm/update', methods=['POST'])
def api_crm_update():
    if not portal_dashboard: return "Not loaded", 501
    body = request.get_json(force=True)
    handle = body.get('handle')
    pin = body.get('pin')
    if CM.create_or_login(handle, pin)['status'] == 'error': return "Forbidden", 403
    return jsonify(portal_dashboard.update_subscriber_meta(DB, body))

@app.route('/api/crm/delete', methods=['POST'])
def api_crm_delete():
    if not portal_dashboard: return "Not loaded", 501
    body = request.get_json(force=True)
    handle = body.get('handle')
    pin = body.get('pin')
    if CM.create_or_login(handle, pin)['status'] == 'error': return "Forbidden", 403
    return jsonify(portal_dashboard.delete_subscriber(DB, body.get('endpoint'), handle))

@app.route('/api/vote_media', methods=['POST'])
def api_vote_media():
    if not premium_tier: return "Not loaded", 501
    body = request.get_json(force=True)
    media_id = body.get('id')
    voter_id = body.get('vid')
    vote = int(body.get('vote')) # 1 or -1
    
    if not media_id or not voter_id: return jsonify({'success': False})
    
    return jsonify(premium_tier.cast_vote(DB.conn, media_id, voter_id, vote))

# --- TIER 2 ROUTES ---

@app.route('/api/tier2/status/<handle>')
def api_tier2_status(handle):
    if not premium_tier_2: return "Not loaded", 501
    pin = request.args.get('pin', '')
    # 1. Authenticate Channel Owner
    check = CM.create_or_login(handle, pin)
    if check['status'] == 'error': return jsonify({'success': False, 'msg': 'Auth Failed'})
    
    # 2. Check Tier 2 Status
    has_access = premium_tier_2.check_tier_2_access(DB.conn, handle)
    modules = premium_tier_2.list_available_modules() if has_access else []
    
    return jsonify({
        "active": has_access,
        "available_modules": modules
    })

@app.route('/api/tier2/exec/<module_key>/<handle>', methods=['POST'])
def api_tier2_exec(module_key, handle):
    if not premium_tier_2: return "Not loaded", 501
    body = request.get_json(force=True)
    pin = body.get('pin', '')
    action = body.get('action', 'default')
    payload = body.get('payload', {})

    # 1. Authenticate
    check = CM.create_or_login(handle, pin)
    if check['status'] == 'error': return jsonify({'success': False, 'msg': 'Auth Failed'})
    
    # 2. Execute via Gateway
    result = premium_tier_2.execute_module(DB.conn, handle, module_key, action, payload)
    return jsonify(result)

# SECRET ROUTE TO GRANT ACCESS (For your use only - or via CLI)
@app.route('/api/tier2/grant/<handle>', methods=['POST'])
def api_tier2_grant(handle):
    if not premium_tier_2: return "Not loaded", 501
    # In production, protect this with a MASTER_KEY check!
    # For now, we'll rely on the channel PIN for simplicity of setup.
    body = request.get_json(force=True)
    pin = body.get('pin', '')
    check = CM.create_or_login(handle, pin)
    if check['status'] == 'error': return jsonify({'success': False, 'msg': 'Auth Failed'})
    
    return jsonify(premium_tier_2.grant_tier_2(DB.conn, handle))

# --- TUNNEL LOGIC ---
def start_tunnel():
    if not shutil.which("cloudflared"): 
        print("\n[CRITICAL] 'cloudflared' not found! Localhost only.")
        return None, None
    
    print("[System] Starting Cloudflare Tunnel...", end=" ", flush=True)
    subprocess.run(["pkill", "cloudflared"], stderr=subprocess.DEVNULL)
    
    if CF_TOKEN and len(CF_TOKEN) > 10:
        token_clean = CF_TOKEN.replace("cloudflared tunnel run --token ", "").strip()
        process = subprocess.Popen(["cloudflared", "tunnel", "run", "--token", token_clean], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("[OK] (Persistent)")
        return f"https://{CF_DOMAIN}", process
    
    process = subprocess.Popen(["cloudflared", "tunnel", "--url", f"http://localhost:{PORT}"], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    url_pattern = re.compile(r"https://[\w-]+\.trycloudflare\.com")
    public_url = None
    
    for _ in range(30):
        line = process.stderr.readline()
        if not line: break
        match = url_pattern.search(line)
        if match: 
            public_url = match.group(0)
            print("[OK]")
            break
            
    return public_url, process

if __name__ == "__main__":
    ensure_directories()
    # REGISTER TIER 2 MODULES ON STARTUP
    if premium_tier_2 and shout_out:
        premium_tier_2.register_module("shout_out", "Shout Out Manager", shout_out.entry_point)
    if toolbox:
        toolbox.init()

    print(f"""
╔═══════════════════════════════════════╗
║      NotiFly v8.2.2 - Flask Edition   ║
╠═══════════════════════════════════════╣
║ ✓ Waitlist & Email Capture System     ║
║ ✓ Fastest Possible Uploads (Raw Bytes)║
║ ✓ Premium Admin Login System          ║
║ ✓ 18+ Age Verification Overlay        ║
╚═══════════════════════════════════════╝
""")
    
    # Start Tunnel
    public_url, proc = start_tunnel()
    if public_url: 
        print("\n" + "="*60 + f"\n    >>> NOTIFLY LIVE: {public_url} <<<\n" + "="*60 + "\n")
    else:
        print(f"\n[!] Tunnel Failed. Local only: http://localhost:{PORT}")
        if proc: proc.kill()

    # Start Flask
    try:
        app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        print("\n[System] Shutting down...")
    finally:
        if proc: proc.terminate()
        print("[System] Goodbye!")
