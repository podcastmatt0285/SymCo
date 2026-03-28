
#!/usr/bin/env python3
"""
NotiFly Manager v8.7 (GRANT UPDATE)
- RESTORED: All v8.2 features (CLI, Livestreams, CRM, Banners, Sitemap)
- ADDED: Automatic Cloudflare Tunnel for HQ Server on Subdomain
- ADDED: Full Web-Based Premium Tier Management
- ADDED: Tier 2 Elite Channel Management Interface
- ADDED: Referral Link Generation & Display
- ADDED: One-Click Tier 1 Premium Grants
"""

# --- CLOUDFLARE TUNNEL CONFIG ---
CF_TUNNEL_TOKEN = ""  # Leave empty for temporary tunnel, or paste your tunnel token
MANAGER_SUBDOMAIN = "manager.notifly.cc"  # Change to your subdomain

import sqlite3
import os
import sys
import shutil
import time
import re
import json
import zipfile
import urllib.request
import urllib.error
import threading
import logging
import math
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

# --- OPTIONAL MODULES ---
try: import nsfw_gate
except ImportError: nsfw_gate = None

try: import premium_tier
except ImportError:
    premium_tier = None
    print("[WARNING] premium_tier.py not found. Premium features disabled.")

try: import premium_tier_2
except ImportError:
    premium_tier_2 = None
    print("[WARNING] premium_tier_2.py not found. Tier 2 features disabled.")

try: import banners
except ImportError:
    banners = None
    print("[WARNING] banners.py not found. Banner management disabled.")

try: import livestream
except ImportError:
    livestream = None
    print("[WARNING] livestream.py not found. Stream management disabled.")

try: import portal_dashboard
except ImportError:
    portal_dashboard = None
    print("[WARNING] portal_dashboard.py not found. CRM disabled.")

try: import sitemap_gen
except ImportError:
    sitemap_gen = None
    print("[WARNING] sitemap_gen.py not found.")

# --- IMPORTS ---
try:
    from flask import Flask, render_template_string, send_file, request, redirect, url_for, jsonify, make_response
except ImportError:
    print("CRITICAL: Flask missing. Run: pip install flask")
    sys.exit(1)

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.layout import Layout
    from rich.prompt import Prompt, Confirm, IntPrompt
    from rich.text import Text
    from rich import box
    from rich.progress import track
except ImportError:
    print("CRITICAL: 'rich' missing. Run: pip install rich")
    sys.exit(1)

# --- CONFIG ---
DB_FILE = Path("notifly.db")
AVATAR_DIR = Path("avatars")
BANNER_DIR = Path("banners")
BACKUP_DIR = Path("backups")
PREMIUM_MEDIA_DIR = Path("premium_media")
SERVER_URL = "http://localhost:8080"
HQ_PORT = 9696
console = Console()

if not DB_FILE.exists():
    console.print("[bold red]FATAL:[/bold red] notifly.db not found.")
    sys.exit(1)

AVATAR_DIR.mkdir(exist_ok=True)
BANNER_DIR.mkdir(exist_ok=True)
BACKUP_DIR.mkdir(exist_ok=True)

# --- CLOUDFLARE TUNNEL MANAGER ---
class TunnelManager:
    def __init__(self, port, subdomain=None, token=None):
        self.port = port
        self.subdomain = subdomain
        self.token = token
        self.process = None
        self.public_url = None
        
    def check_cloudflared(self):
        """Check if cloudflared is installed"""
        return shutil.which("cloudflared") is not None
    
    def start(self):
        """Start the Cloudflare tunnel"""
        if not self.check_cloudflared():
            console.print("[bold yellow]WARNING:[/bold yellow] cloudflared not installed.")
            console.print("[cyan]Install:[/cyan] https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/")
            console.print(f"[yellow]Using localhost only:[/yellow] http://localhost:{self.port}")
            return f"http://localhost:{self.port}"
        
        console.print("[cyan]Starting Cloudflare Tunnel...[/cyan]", end=" ")
        
        # Kill existing processes
        subprocess.run(["pkill", "-9", "cloudflared"], stderr=subprocess.DEVNULL)
        time.sleep(0.5)
        
        # Persistent tunnel with token
        if self.token and len(self.token) > 10:
            token_clean = self.token.replace("cloudflared tunnel run --token ", "").strip()
            self.process = subprocess.Popen(
                ["cloudflared", "tunnel", "run", "--token", token_clean],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            self.public_url = f"https://{self.subdomain}" if self.subdomain else "https://configured-domain"
            console.print(f"[bold green]OK[/bold green] (Persistent)")
            return self.public_url
        
        # Temporary tunnel
        self.process = subprocess.Popen(
            ["cloudflared", "tunnel", "--url", f"http://localhost:{self.port}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True
        )
        
        url_pattern = re.compile(r"https://[\w-]+\.trycloudflare\.com")
        
        for _ in range(30):
            line = self.process.stderr.readline()
            if not line: break
            
            match = url_pattern.search(line)
            if match:
                self.public_url = match.group(0)
                console.print(f"[bold green]OK[/bold green] (Temporary)")
                return self.public_url
        
        console.print("[bold red]FAILED[/bold red]")
        return f"http://localhost:{self.port}"
    
    def stop(self):
        """Stop the tunnel"""
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()

TUNNEL = TunnelManager(HQ_PORT, MANAGER_SUBDOMAIN, CF_TUNNEL_TOKEN)

# --- UTILS ---
def clear(): os.system('cls' if os.name == 'nt' else 'clear')

def get_db_size():
    size = DB_FILE.stat().st_size
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024: return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} TB"

def ts_to_str(ts):
    return datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M') if ts else "N/A"

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def parse_duration(s):
    units = {'d': 86400, 'h': 3600, 'm': 60}
    match = re.match(r"(\d+)([dhm])", s.lower())
    if match:
        val, unit = match.groups()
        return int(val) * units[unit]
    return 0

# --- DATABASE CORE ---
class DBManager:
    def __init__(self):
        self.conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        self.conn.row_factory = dict_factory
        self.cur = self.conn.cursor()
        self.cur.execute("PRAGMA foreign_keys = ON")
        self.check_migrations()
    
    def check_migrations(self):
        """Auto-fix columns and create metadata tables if missing."""
        try:
            cols_bh = [r['name'] for r in self.query("PRAGMA table_info(broadcast_history)")]
            if 'body' not in cols_bh:
                self.execute("ALTER TABLE broadcast_history ADD COLUMN body TEXT")
            
            self.execute("""
                CREATE TABLE IF NOT EXISTS sub_metadata (
                    endpoint TEXT PRIMARY KEY,
                    country TEXT,
                    os TEXT,
                    device_type TEXT,
                    last_active INTEGER,
                    FOREIGN KEY(endpoint) REFERENCES subs(endpoint) ON DELETE CASCADE
                )
            """)

            cols_sm = [r['name'] for r in self.query("PRAGMA table_info(sub_metadata)")]
            if 'last_active' not in cols_sm:
                self.execute("ALTER TABLE sub_metadata ADD COLUMN last_active INTEGER")
            if 'country' not in cols_sm:
                self.execute("ALTER TABLE sub_metadata ADD COLUMN country TEXT")
            if 'os' not in cols_sm:
                self.execute("ALTER TABLE sub_metadata ADD COLUMN os TEXT")
                
            if livestream: livestream.init_db(self.conn)
            if premium_tier_2: premium_tier_2.init_db(self.conn)
            if premium_tier: premium_tier.init_db(self.conn) # Ensure premium tables exist

        except Exception as e:
            console.print(f"[bold red]Migration Error:[/bold red] {e}")

    def execute(self, sql, params=()):
        self.cur.execute(sql, params)
        self.conn.commit()
        return self.cur.lastrowid

    def query(self, sql, params=()):
        try:
            self.cur.execute(sql, params)
            if sql.strip().upper().startswith("SELECT") or sql.strip().upper().startswith("PRAGMA"):
                return self.cur.fetchall()
            self.conn.commit()
            return self.cur.rowcount
        except Exception as e:
            console.print(f"[bold red]SQL Error:[/bold red] {e}")
            return None

    def close(self):
        self.conn.close()

# --- ANALYTICS & MATH ENGINE ---
def get_daily_volume(db, days=7):
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    data = {}
    for i in range(days):
        d = (today - timedelta(days=i)).strftime("%m-%d")
        data[d] = 0
    cutoff = int((today - timedelta(days=days)).timestamp())
    rows = db.query("SELECT timestamp FROM broadcast_history WHERE timestamp > ?", (cutoff,))
    if rows:
        for r in rows:
            d_str = datetime.fromtimestamp(r['timestamp']).strftime("%m-%d")
            if d_str in data: data[d_str] += 1
    return dict(reversed(list(data.items())))

class SpamHammer:
    @staticmethod
    def detect_anomalies(db):
        rows = db.query("SELECT handle, timestamp FROM broadcast_history ORDER BY timestamp ASC")
        if not rows: return {}
        suspects = {} 
        activity = {}
        for r in rows:
            if r['handle'] not in activity: activity[r['handle']] = []
            activity[r['handle']].append(r['timestamp'])
        for handle, timestamps in activity.items():
            if len(timestamps) < 10: continue
            count = 0
            for i in range(len(timestamps) - 10):
                if (timestamps[i+9] - timestamps[i]) < 60: count += 1
            if count > 0: suspects[handle] = count
        return suspects

class MathEngine:
    @staticmethod
    def get_shannon_entropy(db):
        rows = db.query("SELECT country, COUNT(*) as c FROM sub_metadata GROUP BY country")
        if not rows: return 0.0, "N/A"
        total = sum(r['c'] for r in rows)
        entropy = 0
        for r in rows:
            if r['country']:
                p = r['c'] / total
                if p > 0: entropy -= p * math.log2(p)
        status = "Hyper-Local" if entropy < 1.0 else "Balanced" if entropy < 3.0 else "Global"
        return round(entropy, 3), status

    @staticmethod
    def get_reaction_velocity(db):
        sql = "SELECT b.timestamp as sent_ts, a.timestamp as click_ts FROM analytics_events a JOIN broadcast_history b ON a.ref_id = b.bid WHERE a.type='notif' ORDER BY a.timestamp DESC LIMIT 500"
        rows = db.query(sql)
        if not rows: return 0, "No Data"
        total_delta = 0; count = 0
        for r in rows:
            delta = r['click_ts'] - r['sent_ts']
            if 0 < delta < 86400: total_delta += delta; count += 1
        if count == 0: return 0, "No Data"
        avg = total_delta / count
        if avg < 60: return avg, f"{avg:.1f} sec"
        if avg < 3600: return avg, f"{avg/60:.1f} min"
        return avg, f"{avg/3600:.1f} hrs"

    @staticmethod
    def get_pearson_correlation(db):
        vol_rows = db.query("SELECT strftime('%Y-%m-%d', datetime(timestamp, 'unixepoch')) as d, COUNT(*) as c FROM broadcast_history GROUP BY d")
        vol_map = {r['d']: r['c'] for r in vol_rows} if vol_rows else {}
        click_rows = db.query("SELECT strftime('%Y-%m-%d', datetime(timestamp, 'unixepoch')) as d, COUNT(*) as c FROM analytics_events WHERE type='notif' GROUP BY d")
        click_map = {r['d']: r['c'] for r in click_rows} if click_rows else {}
        dates = sorted(list(set(vol_map.keys()) & set(click_map.keys())))
        if len(dates) < 3: return 0, "Insuff. Data"
        x = [vol_map[d] for d in dates]
        y = [(click_map[d] / vol_map[d] * 100) for d in dates]
        n = len(x); sum_x = sum(x); sum_y = sum(y); sum_xy = sum(i*j for i, j in zip(x,y))
        sum_x2 = sum(i**2 for i in x); sum_y2 = sum(i**2 for i in y)
        denom = math.sqrt((n * sum_x2 - sum_x**2) * (n * sum_y2 - sum_y**2))
        if denom == 0: return 0, "Flatline"
        r = (n * sum_xy - sum_x * sum_y) / denom
        status = "Hungry" if r > 0.3 else "Fatigued" if r < -0.3 else "Neutral"
        return round(r, 3), status

    @staticmethod
    def get_technographics(db):
        rows = db.query("SELECT os, COUNT(*) as c FROM sub_metadata GROUP BY os")
        if not rows: return []
        total = sum(r['c'] for r in rows)
        return [{'os': r['os'] or 'Unknown', 'pct': (r['c']/total)*100} for r in rows]

    @staticmethod
    def detect_ghosts(db):
        cutoff = int(time.time()) - (30 * 86400)
        total_res = db.query("SELECT COUNT(*) as c FROM subs")
        total = total_res[0]['c'] if total_res else 0
        try:
            ghosts = db.query("SELECT COUNT(*) as c FROM sub_metadata WHERE last_active < ? AND last_active IS NOT NULL", (cutoff,))
            ghost_count = ghosts[0]['c'] if ghosts else 0
        except: ghost_count = 0
        churn_rate = (ghost_count / total * 100) if total > 0 else 0
        return ghost_count, churn_rate

    @staticmethod
    def get_channel_metrics(db):
        channels = db.query("SELECT handle, created_at FROM channels")
        if not channels: return []
        sub_counts = defaultdict(int)
        raw_subs = db.query("SELECT handle FROM subs")
        if raw_subs:
            for r in raw_subs: sub_counts[r['handle']] += 1
        sent_counts = defaultdict(int)
        bids_by_channel = defaultdict(list)
        raw_history = db.query("SELECT handle, bid, sent_count, timestamp FROM broadcast_history")
        if raw_history:
            for r in raw_history:
                sent_counts[r['handle']] += (r['sent_count'] or 0); bids_by_channel[r['handle']].append(r)
        click_counts = defaultdict(int)
        clicks_by_bid = defaultdict(int)
        raw_clicks = db.query("SELECT ref_id, timestamp FROM analytics_events WHERE type='notif'")
        if raw_clicks:
            for c in raw_clicks: clicks_by_bid[c['ref_id']] += 1
        for handle, bids in bids_by_channel.items():
            for b in bids: click_counts[handle] += clicks_by_bid.get(b['bid'], 0)
        metrics = []
        for c in channels:
            h = c['handle']; s = sub_counts[h]; sent = sent_counts[h]; clks = click_counts[h]
            ctr = (clks / sent * 100) if sent > 0 else 0.0
            age_days = (time.time() - c['created_at']) / 86400; age_days = max(age_days, 1)
            activity_score = (len(bids_by_channel[h]) / age_days) * 7
            health_score = (ctr * 0.2) + math.log(s + 1) + (activity_score * 0.5)
            metrics.append({'handle': h, 'subs': s, 'sent': sent, 'clicks': clks, 'ctr': ctr, 'activity': activity_score, 'health': health_score})
        return sorted(metrics, key=lambda x: x['health'], reverse=True)

    @staticmethod
    def extract_hashtag_intelligence(db):
        msgs = db.query("SELECT bid, title, body FROM broadcast_history ORDER BY timestamp DESC LIMIT 1000")
        if not msgs: return []
        tag_stats = defaultdict(lambda: {'count': 0, 'bids': []})
        for m in msgs:
            title_txt = m.get('title') or ""; body_txt = m.get('body') or ""; text = title_txt + " " + body_txt
            found_tags = set(re.findall(r"#(\w+)", text))
            for t in found_tags: tag_stats[t]['count'] += 1; tag_stats[t]['bids'].append(m['bid'])
        final_tags = []
        bid_click_vol = defaultdict(int)
        raw_clicks = db.query("SELECT ref_id FROM analytics_events WHERE type='notif'")
        if raw_clicks:
            for r in raw_clicks: bid_click_vol[r['ref_id']] += 1
        for tag, data in tag_stats.items():
            total_clicks_for_tag = sum(bid_click_vol.get(bid, 0) for bid in data['bids'])
            avg_clicks = total_clicks_for_tag / data['count'] if data['count'] > 0 else 0
            final_tags.append({'tag': tag, 'vol': data['count'], 'clicks': total_clicks_for_tag, 'cpt': avg_clicks})
        return sorted(final_tags, key=lambda x: x['cpt'], reverse=True)[:10]

    @staticmethod
    def get_temporal_heatmap(db):
        rows = db.query("SELECT strftime('%H', datetime(timestamp, 'unixepoch')) as hour, COUNT(*) as c FROM analytics_events WHERE type='notif' GROUP BY hour")
        if not rows: return [{'hour': h, 'val': 0, 'opacity': 0.1} for h in range(24)]
        hours = {int(r['hour']): r['c'] for r in rows}
        max_val = max(hours.values()) if hours else 1
        return [{'hour': h, 'val': hours.get(h, 0), 'opacity': hours.get(h, 0)/max_val} for h in range(24)]

# --- WEB HQ SERVER ---
hq_app = Flask(__name__)
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

def get_base_css():
    return """
    :root { 
        --bg: #050505; 
        --card: #121212; 
        --text: #e0e0e0; 
        --accent: #00ff9d; 
        --dim: #333; 
        --danger: #ff4757; 
        --info: #3498db; 
        --warn: #f39c12; 
        --tier2: #a855f7;
    }
    
    * { box-sizing: border-box; }
    
    body { 
        background: var(--bg); 
        color: var(--text); 
        font-family: 'JetBrains Mono', 'Consolas', monospace; 
        margin: 0; 
        padding: 20px; 
        padding-bottom: 60px; 
        overflow-x: hidden;
    }
    
    /* Responsive header */
    h1 { 
        font-size: clamp(1.2rem, 4vw, 2rem); 
        margin: 0 0 20px 0;
        word-break: break-word;
    }
    
    /* Responsive navigation */
    .nav { 
        display: flex; 
        gap: 8px; 
        margin-bottom: 25px; 
        border-bottom: 1px solid var(--dim); 
        padding-bottom: 15px; 
        flex-wrap: wrap;
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
    }
    
    .nav a { 
        color: #888; 
        text-decoration: none; 
        padding: 8px 12px; 
        background: var(--card); 
        border: 1px solid var(--dim); 
        border-radius: 4px; 
        font-weight: 600; 
        transition: 0.2s; 
        font-size: clamp(10px, 2.5vw, 12px); 
        text-transform: uppercase; 
        white-space: nowrap;
        flex-shrink: 0;
    }
    
    .nav a.active, .nav a:hover { 
        background: var(--dim); 
        color: var(--accent); 
        border-color: var(--accent); 
    }
    
    /* Responsive grid */
    .grid { 
        display: grid; 
        grid-template-columns: repeat(auto-fit, minmax(min(100%, 300px), 1fr)); 
        gap: 15px; 
        margin-bottom: 20px; 
    }
    
    .grid-wide { 
        grid-column: span 2; 
    }
    
    @media(max-width: 900px) { 
        .grid { 
            grid-template-columns: 1fr; 
        }
        .grid-wide { 
            grid-column: span 1; 
        } 
    }
    
    /* Responsive cards */
    .card { 
        background: var(--card); 
        border-radius: 6px; 
        padding: clamp(12px, 3vw, 20px); 
        border: 1px solid var(--dim); 
        position: relative; 
        overflow: hidden;
    }
    
    .card h3 { 
        margin: 0 0 15px 0; 
        color: var(--accent); 
        font-size: clamp(10px, 2.5vw, 12px); 
        text-transform: uppercase; 
        letter-spacing: 1px; 
        border-bottom: 1px solid var(--dim); 
        padding-bottom: 8px; 
    }
    
    /* Responsive metrics */
    .metric-val { 
        font-size: clamp(18px, 5vw, 24px); 
        font-weight: bold; 
        color: #fff; 
    }
    
    .metric-lbl { 
        font-size: clamp(9px, 2vw, 11px); 
        color: #666; 
        text-transform: uppercase; 
    }
    
    /* Responsive tables */
    table { 
        width: 100%; 
        border-collapse: collapse; 
        font-size: clamp(10px, 2vw, 12px);
        display: block;
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
    }
    
    thead, tbody, tr { 
        display: table; 
        width: 100%; 
        table-layout: fixed; 
    }
    
    th { 
        text-align: left; 
        color: #888; 
        padding: 8px 4px; 
        border-bottom: 1px solid var(--dim); 
        text-transform: uppercase; 
        font-size: clamp(9px, 2vw, 11px);
    }
    
    td { 
        padding: 8px 4px; 
        border-bottom: 1px solid #222; 
        color: #ccc; 
        word-break: break-word;
    }
    
    tr:hover td { 
        background: #1a1a1a; 
        color: #fff; 
    }
    
    /* Mobile table adjustments */
    @media(max-width: 600px) {
        table { 
            font-size: 10px; 
        }
        th, td { 
            padding: 6px 2px; 
        }
        /* Hide less important columns on mobile */
        .hide-mobile { 
            display: none; 
        }
    }
    
    .tag { 
        display: inline-block; 
        padding: 2px 6px; 
        background: #1a1a1a; 
        border: 1px solid #333; 
        border-radius: 3px; 
        font-size: clamp(9px, 2vw, 10px); 
        margin-right: 4px; 
        color: var(--accent); 
    }
    
    /* Tier 2 Badge */
    .tier2-badge {
        display: inline-block;
        padding: 2px 6px;
        background: var(--tier2);
        color: #000;
        border-radius: 3px;
        font-size: 9px;
        font-weight: bold;
        margin-left: 5px;
    }
    
    /* Responsive charts */
    .chart-box { 
        height: clamp(150px, 40vw, 250px); 
        width: 100%; 
        position: relative;
    }
    
    /* Responsive heatmap */
    .heatmap { 
        display: grid; 
        grid-template-columns: repeat(24, 1fr); 
        gap: clamp(1px, 0.5vw, 2px); 
        margin-top: 10px; 
    }
    
    .hm-cell { 
        height: clamp(15px, 4vw, 20px); 
        background: #222; 
        border-radius: 2px; 
        position: relative; 
    }
    
    .hm-cell:hover::after { 
        content: attr(title); 
        position: absolute; 
        bottom: 100%; 
        left: 50%; 
        transform: translateX(-50%); 
        background: #000; 
        padding: 4px; 
        font-size: 10px; 
        z-index: 10; 
        border: 1px solid var(--accent); 
        white-space: nowrap; 
    }
    
    /* Mobile specific adjustments */
    @media(max-width: 600px) {
        body { 
            padding: 10px; 
            padding-bottom: 40px; 
        }
        
        .nav { 
            gap: 5px; 
            padding-bottom: 10px; 
        }
        
        .grid { 
            gap: 10px; 
        }
        
        .hm-cell:hover::after { 
            display: none; /* Touch devices don't hover well */
        }
    }
    
    /* Image gallery responsive */
    .gallery { 
        display: grid; 
        grid-template-columns: repeat(auto-fill, minmax(min(80px, 100%), 1fr)); 
        gap: 10px; 
    }
    
    .gallery img { 
        width: 100%; 
        height: auto; 
        display: block; 
    }
    
    /* Buttons and links */
    a[style*="padding"] { 
        font-size: clamp(10px, 2.5vw, 11px) !important; 
        padding: clamp(4px, 1vw, 6px) clamp(8px, 2vw, 12px) !important; 
    }
    
    /* Flex containers for headers */
    [style*="display:flex"] { 
        flex-wrap: wrap; 
        gap: 10px; 
    }
    
    /* Ensure canvas is responsive */
    canvas { 
        max-width: 100% !important; 
        height: auto !important; 
    }
    
    /* Tier 2 Input Box */
    .tier2-input {
        display: flex;
        gap: 10px;
        margin-top: 10px;
        padding: 10px;
        background: #0a0a0a;
        border-radius: 6px;
        border: 1px solid var(--tier2);
    }
    
    .tier2-input input {
        flex: 1;
        padding: 8px;
        background: #1a1a1a;
        border: 1px solid var(--dim);
        color: #fff;
        border-radius: 4px;
        font-family: monospace;
    }
    
    .tier2-input button {
        padding: 8px 16px;
        background: var(--tier2);
        color: #000;
        border: none;
        border-radius: 4px;
        font-weight: bold;
        cursor: pointer;
    }
    """

PWA_ICON = "https://cdn-icons-png.flaticon.com/512/1156/1156948.png"
def get_pwa_headers():
    return f"""<link rel="manifest" href="/manifest.json">
    <meta name="theme-color" content="#050505">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <link rel="apple-touch-icon" href="{PWA_ICON}">
    <script>if('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js');</script>"""

@hq_app.route('/manifest.json')
def manifest():
    return jsonify({"name": "NotiFly Manager", "short_name": "NotiFly", "start_url": "/", "display": "standalone", "background_color": "#050505", "theme_color": "#00ff9d", "icons": [{"src": PWA_ICON, "sizes": "512x512", "type": "image/png"}]})

@hq_app.route('/sw.js')
def service_worker():
    js = "self.addEventListener('fetch', (e) => { e.respondWith(fetch(e.request).catch(() => new Response('Offline'))); });"
    response = make_response(js); response.headers['Content-Type'] = 'application/javascript'; return response

def get_hq_db(): return DBManager()

@hq_app.route('/')
def dashboard():
    db = get_hq_db()
    channel_data = MathEngine.get_channel_metrics(db)
    tag_data = MathEngine.extract_hashtag_intelligence(db)
    heatmap = MathEngine.get_temporal_heatmap(db)
    entropy, entropy_status = MathEngine.get_shannon_entropy(db)
    vel_raw, vel_str = MathEngine.get_reaction_velocity(db)
    pearson_r, pearson_status = MathEngine.get_pearson_correlation(db)
    ghost_count, churn_rate = MathEngine.detect_ghosts(db)
    techno_data = MathEngine.get_technographics(db)
    
    scatter_data = json.dumps([{'x': c['subs'], 'y': c['ctr'], 'r': min(max(c['health'] * 2, 5), 30), 'label': c['handle']} for c in channel_data])
    db.close()
    
    rows_html = "".join([f"<tr><td><span style='color:{'#00ff9d' if c['health'] > 5 else '#f39c12' if c['health'] > 2 else '#ff4757'}'>●</span> <b>{c['handle']}</b></td><td>{c['subs']}</td><td>{c['sent']}</td><td>{c['ctr']:.2f}%</td><td>{c['activity']:.1f} /wk</td><td><b>{c['health']:.2f}</b></td></tr>" for c in channel_data])
    tags_html = ""
    if tag_data:
        for t in tag_data:
            # Calculate color intensity based on clicks per tag
            color = "#00ff9d" if t['cpt'] > 10 else "#fff"
            tags_html += f"<tr><td><b style='color:{color}'>#{t['tag']}</b></td><td>{t['vol']}</td><td>{t['clicks']}</td><td>{t['cpt']:.1f}</td></tr>"
    else:
        tags_html = "<tr><td colspan='4' style='text-align:center;color:#666'>No hashtag data available.</td></tr>"
    heatmap_html = "".join([f"<div class='hm-cell' style='opacity:{0.2 + (h['opacity']*0.8)}; background-color:var(--accent)' title='{h['hour']}:00 - {h['val']} clicks'></div>" for h in heatmap])
    techno_js_labels = json.dumps([t['os'] for t in techno_data]); techno_js_data = json.dumps([t['pct'] for t in techno_data])

    html = f"""<!DOCTYPE html><html><head><meta http-equiv="refresh" content="30"><meta name="viewport" content="width=device-width, initial-scale=1"><title>NotiFly HQ</title>{get_pwa_headers()}<script src="https://cdn.jsdelivr.net/npm/chart.js"></script><style>{get_base_css()}</style></head><body>
    <div style="display:flex;justify-content:space-between;align-items:center"><h1 style="color:#fff;margin:0">NOTIFLY <span style="color:var(--info)">ULTIMATE</span></h1><span style="font-family:monospace;color:#666">v8.6</span></div><br>
    <div class="nav"><a href="/" class="active">Analytics</a><a href="/gallery">Assets</a><a href="/streams">Streams</a><a href="/crm">CRM</a><a href="/spam">Threats</a><a href="/waitlist">Waitlist</a><a href="/premium">Premium</a></div>
    <div class="grid" style="grid-template-columns: repeat(2, 1fr);">
        <div class="card"><h3>Shannon Entropy ($H$)</h3><div class="metric-val" style="color:var(--info)">{entropy}</div><div class="metric-lbl">{entropy_status} Diversity</div></div>
        <div class="card"><h3>Reaction Velocity ($v$)</h3><div class="metric-val" style="color:var(--accent)">{vel_str}</div><div class="metric-lbl">Mean Time To React</div></div>
        <div class="card"><h3>Pearson Coeff ($r$)</h3><div class="metric-val" style="color:{'#ff4757' if pearson_r < -0.3 else '#00ff9d'}">{pearson_r}</div><div class="metric-lbl">{pearson_status}</div></div>
        <div class="card"><h3>Ghost Protocol</h3><div class="metric-val" style="color:var(--warn)">{ghost_count}</div><div class="metric-lbl">Churn Risk ({churn_rate:.1f}%)</div></div>
    </div>
    <div class="grid"><div class="card grid-wide"><h3>Channel Matrix</h3><div class="chart-box"><canvas id="scatterChart"></canvas></div></div><div class="card"><h3>Technographics</h3><div class="chart-box" style="height:150px"><canvas id="technoChart"></canvas></div><hr style="border:0;border-top:1px solid #333;margin:15px 0"><h3>Temporal Heatmap</h3><div class="heatmap">{heatmap_html}</div></div></div>
    <div class="card">
    <h3>Hashtag Intelligence</h3>
    <table>
        <tr>
            <th>Tag</th>
            <th>Uses</th>
            <th>Clicks</th>
            <th>CPT (Avg)</th>
        </tr>
        {tags_html}
    </table>
</div>
    <div class="card"><h3>Leaderboard</h3><table><tr><th>Handle</th><th>Subs</th><th>Vol</th><th>CTR %</th><th>Freq</th><th>Health ($H_s$)</th></tr>{rows_html}</table></div>
    <script>Chart.defaults.color='#666';Chart.defaults.borderColor='#222';new Chart(document.getElementById('scatterChart'),{{type:'bubble',data:{{datasets:[{{label:'Channels',data:{scatter_data},backgroundColor:'rgba(0, 255, 157, 0.2)',borderColor:'#00ff9d',borderWidth:1}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}}}},scales:{{x:{{type:'logarithmic'}}}}}}}});new Chart(document.getElementById('technoChart'),{{type:'doughnut',data:{{labels:{techno_js_labels},datasets:[{{data:{techno_js_data},backgroundColor:['#3498db','#e74c3c','#9b59b6','#f1c40f'],borderWidth:0}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{position:'right'}}}}}}}});</script></body></html>"""
    return html

@hq_app.route('/gallery')
def gallery():
    avatars = [f.name for f in AVATAR_DIR.glob("*") if not f.name.startswith('.')]
    banner_files = [f.name for f in BANNER_DIR.glob("*") if not f.name.startswith('.')]
    
    html = f"""<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"><title>Assets</title>{get_pwa_headers()}<style>{get_base_css()}</style></head><body>
    <h1>Asset Gallery</h1>
    <div class="nav"><a href="/">Analytics</a><a href="/gallery" class="active">Assets</a><a href="/streams">Streams</a><a href="/crm">CRM</a><a href="/spam">Threats</a><a href="/waitlist">Waitlist</a><a href="/premium">Premium</a></div>
    <div class="card">
        <h3>Avatars ({len(avatars)})</h3>
        <div class="gallery" style="display:grid;grid-template-columns:repeat(auto-fill, minmax(80px, 1fr));gap:10px;">{''.join([f'<div style="border:1px solid #333"><img src="/raw_avatar/{av}" style="width:100%;display:block" loading="lazy"></div>' for av in avatars])}</div>
    </div>
    <br>
    <div class="card">
        <h3>Banners ({len(banner_files)})</h3>
        <div class="gallery" style="display:grid;grid-template-columns:repeat(auto-fill, minmax(200px, 1fr));gap:10px;">{''.join([f'<div style="border:1px solid #333;height:80px;background-image:url(/raw_banner/{b});background-size:cover;background-position:center"></div>' for b in banner_files])}</div>
    </div>
    </body></html>"""
    return html

@hq_app.route('/streams')
def streams():
    db = get_hq_db()
    active_streams = []
    if livestream:
        active_streams = db.query("SELECT * FROM livestreams WHERE is_live=1")
    db.close()
    
    rows = ""
    if active_streams:
        for s in active_streams:
            dur = int(time.time() - s['start_time']) / 60
            rows += f"<tr><td><span style='color:red'>● LIVE</span> {s['handle']}</td><td>{dur:.1f} min</td><td>{s['viewer_count']}</td><td><a href='/kill_stream/{s['handle']}' style='color:red'>KILL</a></td></tr>"
    else:
        rows = "<tr><td colspan='4' style='text-align:center;color:#666'>No active streams.</td></tr>"

    html = f"""<!DOCTYPE html><html><head><meta http-equiv="refresh" content="10"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Streams</title>{get_pwa_headers()}<style>{get_base_css()}</style></head><body>
    <h1>Livestream Command</h1>
    <div class="nav"><a href="/">Analytics</a><a href="/gallery">Assets</a><a href="/streams" class="active">Streams</a><a href="/crm">CRM</a><a href="/spam">Threats</a><a href="/waitlist">Waitlist</a><a href="/premium">Premium</a></div>
    <div class="card"><h3>Active Broadcasts</h3><table><tr><th>Handle</th><th>Duration</th><th>Viewers</th><th>Action</th></tr>{rows}</table></div></body></html>"""
    return html

@hq_app.route('/crm')
def crm_dash():
    db = get_hq_db()
    try:
        subs = db.query("SELECT s.handle, m.country, m.os, m.last_active FROM subs s LEFT JOIN sub_metadata m ON s.endpoint = m.endpoint ORDER BY m.last_active DESC LIMIT 100")
    except: subs = []
    db.close()
    
    rows = ""
    for s in subs:
        la = ts_to_str(s['last_active']) if s['last_active'] else "Never"
        rows += f"<tr><td>{s['handle']}</td><td>{s['country'] or '?'}</td><td>{s['os'] or '?'}</td><td>{la}</td></tr>"

    html = f"""<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"><title>CRM</title>{get_pwa_headers()}<style>{get_base_css()}</style></head><body>
    <h1>Subscriber CRM</h1>
    <div class="nav"><a href="/">Analytics</a><a href="/gallery">Assets</a><a href="/streams">Streams</a><a href="/crm" class="active">CRM</a><a href="/spam">Threats</a><a href="/waitlist">Waitlist</a><a href="/premium">Premium</a></div>
    <div class="card"><h3>Recent Active Subscribers</h3><table><tr><th>Handle</th><th>Country</th><th>OS</th><th>Last Active</th></tr>{rows}</table></div></body></html>"""
    return html

@hq_app.route('/spam')
def spam():
    db = get_hq_db(); suspects = SpamHammer.detect_anomalies(db); db.close()
    rows_html = "".join([f"<tr><td>{s}</td><td style='color:#ff4757'>{count}</td><td><a href='/ban_channel/{s}' style='color:#ff4757'>NUKE</a></td></tr>" for s, count in suspects.items()])
    html = f"""<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"><title>Threats</title>{get_pwa_headers()}<style>{get_base_css()}</style></head><body>
    <h1 style="color:#ff4757">Threat Detection</h1>
    <div class="nav"><a href="/">Analytics</a><a href="/gallery">Assets</a><a href="/streams">Streams</a><a href="/crm">CRM</a><a href="/spam" class="active">Threats</a><a href="/waitlist">Waitlist</a><a href="/premium">Premium</a></div>
    <div class="card" style="border-top: 2px solid #ff4757"><h3>Anomaly Heuristics</h3><table><tr><th>Handle</th><th>Flags</th><th>Action</th></tr>{rows_html}</table></div></body></html>"""
    return html

@hq_app.route('/waitlist')
def waitlist():
    db = get_hq_db()
    try: leads = db.query("SELECT * FROM email_waitlist ORDER BY timestamp DESC")
    except: leads = []
    db.close()
    rows_html = "".join([f"<tr><td>{l['handle']}</td><td>{l['name']}</td><td><span style='color:#fff'>{l['email']}</span></td><td>{l['socials']}</td><td>{ts_to_str(l['timestamp'])}</td><td><a href='/nuke_lead/{l['id']}' style='color:var(--danger)'>DEL</a></td></tr>" for l in leads]) if leads else "<tr><td colspan='6'>No leads.</td></tr>"
    html = f"""<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"><title>Waitlist</title>{get_pwa_headers()}<style>{get_base_css()}</style></head><body>
    <div style="display:flex;justify-content:space-between;align-items:center"><h1>WAITLIST</h1><div><a href="/export_waitlist" style="padding:6px 12px;background:var(--info);color:#fff;text-decoration:none;border-radius:4px;font-size:11px;font-weight:bold">EXPORT</a> <a href="/nuke_waitlist_confirm" style="padding:6px 12px;background:var(--danger);color:#fff;text-decoration:none;border-radius:4px;font-size:11px;font-weight:bold">NUKE</a></div></div>
    <div class="nav"><a href="/">Analytics</a><a href="/gallery">Assets</a><a href="/streams">Streams</a><a href="/crm">CRM</a><a href="/spam">Threats</a><a href="/waitlist" class="active">Waitlist</a><a href="/premium">Premium</a></div>
    <div class="card"><h3>Captured Leads</h3><table><tr><th>Handle</th><th>Name</th><th>Email</th><th>Socials</th><th>Date</th><th>Action</th></tr>{rows_html}</table></div></body></html>"""
    return html

@hq_app.route('/premium')
def premium_dash():
    if not premium_tier:
        return "<h1 style='color:red'>Premium Module Not Loaded</h1>"
    
    db = get_hq_db()
    admins = premium_tier.get_all_admins(db.conn)
    channels = premium_tier.get_all_premium_channels(db.conn)
    
    # Get Tier 2 channels
    tier2_channels = []
    if premium_tier_2:
        tier2_channels = premium_tier_2.get_all_tier_2_channels(db.conn)
    
    db.close()
    
    # Build Admin Table
    admin_rows = ""
    for a in admins:
        usage_mb = a['storage_used'] / 1024 / 1024
        # REFERRAL LINK DISPLAY
        ref_link = f"https://notifly.cc/claim/{a.get('referral_token', 'ERROR')}"
        
        admin_rows += f"""
        <tr>
            <td>{a['id']}</td>
            <td><span style="color:#fff;font-weight:bold">{a['username']}</span></td>
            <td style="font-family:monospace;color:var(--accent)">{a['password']}</td>
            <td>{a['slots_used']} / <span id="slots_val_{a['id']}">{a['slots_max']}</span> <a href="#" onclick="editSlots({a['id']}, {a['slots_max']})" style="font-size:10px;color:#888">[EDIT]</a></td>
            <td>{usage_mb:.2f} MB</td>
            <td><a href="{ref_link}" target="_blank" style="color:#3498db;font-weight:bold;font-size:11px">REF LINK</a></td>
            <td><a href="/premium/delete_admin/{a['id']}" style="color:var(--danger);font-weight:bold">DELETE</a></td>
        </tr>"""
        
    # Build Overseer Table
    chan_rows = ""
    for c in channels:
        size_mb = c['storage_used'] / 1024 / 1024
        size_str = f"{size_mb:.2f} MB"
        if size_mb > 500: size_str = f"<span style='color:var(--danger)'>{size_str}</span>"
        
        # Check if channel has Tier 2
        tier2_badge = ""
        if premium_tier_2:
            if any(t['handle'] == c['handle'] for t in tier2_channels):
                tier2_badge = '<span class="tier2-badge">TIER 2</span>'
        
        chan_rows += f"""
        <tr>
            <td><span style="color:#eab308">★</span> {c['handle']}{tier2_badge}</td>
            <td>{c['admin']}</td>
            <td>{c['file_count']}</td>
            <td>{size_str}</td>
            <td>
                <a href="/premium/unlock/{c['handle']}" style="color:#fff;background:#333;padding:2px 6px;text-decoration:none;font-size:10px;border-radius:3px">UNLOCK</a>
                <a href="/premium/purge/{c['handle']}" style="color:#fff;background:var(--danger);padding:2px 6px;text-decoration:none;font-size:10px;border-radius:3px;margin-left:5px">PURGE MEDIA</a>
            </td>
        </tr>"""
    
    # Build Tier 2 Section
    tier2_section = ""
    if premium_tier_2:
        tier2_rows = ""
        for t in tier2_channels:
            tier2_rows += f"""
            <tr>
                <td><span style="color:var(--tier2)">◆</span> {t['handle']}</td>
                <td>{ts_to_str(t['granted_at'])}</td>
                <td><span style="color:var(--accent)">{t['status']}</span></td>
                <td><a href="/premium/tier2/revoke/{t['handle']}" style="color:var(--danger);font-weight:bold">REVOKE</a></td>
            </tr>"""
        
        tier2_section = f"""
        <div class="card grid-wide">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:15px;border-bottom:1px solid var(--tier2);padding-bottom:10px">
                <h3 style="margin:0;border:0;color:var(--tier2)">⚡ TIER 2 ELITE CHANNELS</h3>
            </div>
            <div class="tier2-input">
                <input type="text" id="tier2_handle" placeholder="Enter channel handle...">
                <button onclick="grantTier2()">GRANT TIER 2</button>
            </div>
            <table style="margin-top:15px">
                <tr><th>Handle</th><th>Granted</th><th>Status</th><th>Action</th></tr>
                {tier2_rows if tier2_rows else '<tr><td colspan="4" style="text-align:center;color:#666">No Tier 2 channels yet.</td></tr>'}
            </table>
        </div>"""
        
    # Build Tier 1 Section (New)
    tier1_section = f"""
        <div class="card grid-wide">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:15px;border-bottom:1px solid var(--accent);padding-bottom:10px">
                <h3 style="margin:0;border:0;color:var(--accent)">💎 TIER 1 PREMIUM GRANT</h3>
            </div>
            <div class="tier2-input" style="border-color:var(--accent)">
                <input type="text" id="tier1_handle" placeholder="Enter channel handle for Premium..." style="border-color:var(--dim)">
                <button onclick="grantTier1()" style="background:var(--accent);color:#000">GRANT PREMIUM</button>
            </div>
            <p style="font-size:10px;color:#888;margin-top:5px">Generates new Admin credentials and locks the channel to them immediately.</p>
        </div>"""

    html = f"""<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"><title>Premium HQ</title>{get_pwa_headers()}<style>{get_base_css()}</style>
    <script>
    function editSlots(id, old) {{
        let n = prompt("Enter new max slots:", old);
        if(n && !isNaN(n)) window.location.href = "/premium/update_slots/" + id + "/" + n;
    }}
    function grantTier2() {{
        let handle = document.getElementById('tier2_handle').value.trim();
        if(!handle) {{ alert('Enter a channel handle'); return; }}
        if(confirm('Grant Tier 2 access to ' + handle + '?')) {{
            window.location.href = '/premium/tier2/grant/' + handle;
        }}
    }}
    function grantTier1() {{
        let handle = document.getElementById('tier1_handle').value.trim();
        if(!handle) {{ alert('Enter a channel handle'); return; }}
        if(confirm('Grant Tier 1 Premium to ' + handle + '?\\nThis will create new Admin credentials for them.')) {{
            window.location.href = '/premium/tier1/grant/' + handle;
        }}
    }}
    </script>
    </head><body>
    <div style="display:flex;justify-content:space-between;align-items:center"><h1>PREMIUM <span style="color:#eab308">OVERLORD</span></h1></div>
    <div class="nav"><a href="/">Analytics</a><a href="/gallery">Assets</a><a href="/streams">Streams</a><a href="/crm">CRM</a><a href="/spam">Threats</a><a href="/waitlist">Waitlist</a><a href="/premium" class="active">Premium</a></div>
    
    <div class="grid">
        {tier1_section}
        {tier2_section}
        
        <div class="card grid-wide">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:15px;border-bottom:1px solid #333;padding-bottom:10px">
                <h3 style="margin:0;border:0">Premium Admins</h3>
                <a href="/premium/create_admin" style="background:var(--accent);color:#000;padding:6px 12px;border-radius:4px;text-decoration:none;font-weight:bold;font-size:11px">GENERATE NEW</a>
            </div>
            <table>
                <tr><th>ID</th><th>Username</th><th>Password</th><th>Slots</th><th>Storage</th><th>Link</th><th>Action</th></tr>
                {admin_rows if admin_rows else "<tr><td colspan='7' style='text-align:center;color:#666'>No admins found.</td></tr>"}
            </table>
        </div>
        
        <div class="card grid-wide">
            <div style="margin-bottom:15px;border-bottom:1px solid #333;padding-bottom:10px"><h3 style="margin:0;border:0">Channel Overseer</h3></div>
            <table>
                <tr><th>Handle</th><th>Owner</th><th>Files</th><th>Storage</th><th>Actions</th></tr>
                {chan_rows if chan_rows else "<tr><td colspan='5' style='text-align:center;color:#666'>No premium channels.</td></tr>"}
            </table>
        </div>
    </div>
    </body></html>"""
    return html

@hq_app.route('/premium/create_admin')
def premium_create_admin():
    if premium_tier:
        db = get_hq_db()
        premium_tier.generate_admin(db.conn)
        db.close()
    return redirect(url_for('premium_dash'))

@hq_app.route('/premium/tier1/grant/<handle>')
def premium_tier1_grant(handle):
    if not premium_tier: return "Premium Module Not Loaded", 501
    
    db = get_hq_db()
    
    # Check if already locked
    existing = db.query("SELECT * FROM premium_locks WHERE handle=?", (handle,))
    if existing:
        db.close()
        console.print(f"[bold red]✗[/bold red] Channel {handle} is already Premium.")
        return redirect(url_for('premium_dash'))

    # Generate new admin
    u, p, t = premium_tier.generate_admin(db.conn)
    
    # Retrieve the new admin's ID
    arow = db.query("SELECT id FROM premium_admins WHERE username=?", (u,))
    if not arow:
        db.close()
        return "Error creating admin", 500
    
    aid = arow[0]['id']
    
    # Lock channel
    db.execute("INSERT INTO premium_locks (handle, admin_id, locked_at) VALUES (?, ?, ?)", (handle, aid, int(time.time())))
    db.close()
    
    console.print(f"[bold green]✓[/bold green] Granted Tier 1 to {handle}. Creds: {u} / {p}")
    return redirect(url_for('premium_dash'))

@hq_app.route('/premium/delete_admin/<int:id>')
def premium_delete_admin(id):
    if premium_tier:
        db = get_hq_db()
        premium_tier.delete_admin(db.conn, id)
        db.close()
    return redirect(url_for('premium_dash'))

@hq_app.route('/premium/update_slots/<int:id>/<int:slots>')
def premium_update_slots(id, slots):
    if premium_tier:
        db = get_hq_db()
        premium_tier.update_admin_slots(db.conn, id, slots)
        db.close()
    return redirect(url_for('premium_dash'))

@hq_app.route('/premium/unlock/<handle>')
def premium_unlock(handle):
    if premium_tier:
        db = get_hq_db()
        premium_tier.unlock_channel_only(db.conn, handle)
        db.close()
    return redirect(url_for('premium_dash'))

@hq_app.route('/premium/purge/<handle>')
def premium_purge(handle):
    if premium_tier:
        db = get_hq_db()
        files = premium_tier.nuke_channel_media_all(db.conn, handle)
        # Delete physical files
        for f in files:
            path = PREMIUM_MEDIA_DIR / f
            if path.exists():
                try: path.unlink()
                except: pass
        db.close()
    return redirect(url_for('premium_dash'))

@hq_app.route('/premium/tier2/grant/<handle>')
def premium_tier2_grant(handle):
    if not premium_tier_2:
        return "Tier 2 Module Not Loaded", 501
    
    db = get_hq_db()
    result = premium_tier_2.grant_tier_2(db.conn, handle)
    db.close()
    
    if result['success']:
        console.print(f"[bold green]✓[/bold green] Tier 2 granted to {handle}")
    else:
        console.print(f"[bold red]✗[/bold red] {result['msg']}")
    
    return redirect(url_for('premium_dash'))

@hq_app.route('/premium/tier2/revoke/<handle>')
def premium_tier2_revoke(handle):
    if not premium_tier_2:
        return "Tier 2 Module Not Loaded", 501
    
    db = get_hq_db()
    result = premium_tier_2.revoke_tier_2(db.conn, handle)
    db.close()
    
    if result['success']:
        console.print(f"[bold yellow]⚠[/bold yellow] Tier 2 revoked from {handle}")
    else:
        console.print(f"[bold red]✗[/bold red] {result['msg']}")
    
    return redirect(url_for('premium_dash'))

@hq_app.route('/raw_avatar/<path:filename>')
def raw_av(filename): return send_file(AVATAR_DIR / filename)

@hq_app.route('/raw_banner/<path:filename>')
def raw_bn(filename): return send_file(BANNER_DIR / filename)

@hq_app.route('/kill_stream/<handle>')
def kill_stream(handle):
    db = get_hq_db()
    if livestream: livestream.end_stream(db.conn, handle)
    db.close()
    return redirect(url_for('streams'))

@hq_app.route('/ban_channel/<handle>')
def ban_channel(handle):
    delete_channel_completely(handle)
    return redirect(url_for('spam'))

@hq_app.route('/nuke_lead/<int:id>')
def nuke_lead(id):
    db = get_hq_db(); db.execute("DELETE FROM email_waitlist WHERE id=?", (id,)); db.close()
    return redirect(url_for('waitlist'))

@hq_app.route('/nuke_waitlist_confirm')
def nuke_waitlist_confirm():
    html = f"""<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"><style>{get_base_css()}</style></head>
    <body style="display:flex;align-items:center;justify-content:center;height:100vh;flex-direction:column">
        <h1 style="color:var(--danger)">⚠️ DANGER ZONE</h1>
        <p>Are you sure you want to delete ALL waitlist entries?</p>
        <div style="margin-top:20px;display:flex;gap:20px">
            <a href="/nuke_waitlist_execute" style="background:var(--danger);padding:15px 30px;color:#fff;text-decoration:none;border-radius:6px;font-weight:bold">YES, NUKE IT</a>
            <a href="/waitlist" style="background:#333;padding:15px 30px;color:#fff;text-decoration:none;border-radius:6px">CANCEL</a>
        </div>
    </body></html>"""
    return html

@hq_app.route('/nuke_waitlist_execute')
def nuke_waitlist_execute():
    db = get_hq_db()
    try: db.execute("DELETE FROM email_waitlist")
    except: pass
    db.close()
    return redirect(url_for('waitlist'))

@hq_app.route('/export_waitlist')
def export_waitlist():
    db = get_hq_db()
    try: leads = db.query("SELECT * FROM email_waitlist ORDER BY timestamp DESC")
    except: leads = []
    db.close()
    csv_out = "ID,Handle,Name,Email,Socials,Consent,Date\n"
    for l in leads:
        n = str(l['name']).replace(',',' ').replace('"','')
        e = str(l['email']).replace(',',' ')
        s = str(l['socials']).replace(',',' ')
        csv_out += f"{l['id']},{l['handle']},{n},{e},{s},{l['admin_consent']},{datetime.fromtimestamp(l['timestamp'])}\n"
    resp = make_response(csv_out); resp.headers["Content-Disposition"] = "attachment; filename=waitlist.csv"; resp.headers["Content-Type"] = "text/csv"; return resp

def run_hq_server():
    console.print("""
[bold rust]
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║        NOTIFLY ULTIMATE MANAGER HQ v8.7                  ║
║        Cloudflare Tunnel + Tier 2 + Referrals            ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
[/bold rust]
""")
    
    public_url = TUNNEL.start()
    
    console.print(Panel.fit(
        f"[bold white]🌐 HQ Dashboard Live:[/bold white]\n"
        f"[bold green]{public_url}[/bold green]\n\n"
        f"[dim]Local: http://localhost:{HQ_PORT}[/dim]",
        title="[bold cyan]Access URLs[/bold cyan]",
        border_style="cyan"
    ))
    
    try:
        hq_app.run(host='0.0.0.0', port=HQ_PORT, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopping server...[/yellow]")
        TUNNEL.stop()

# --- CLI TOOLS ---
def delete_channel_completely(handle):
    """Deep Clean: Removes DB entries, Avatar, Banner, and Premium Media"""
    db = DBManager()
    
    db.query("DELETE FROM broadcast_history WHERE handle=?", (handle,))
    db.query("DELETE FROM scheduled_broadcasts WHERE handle=?", (handle,))
    db.query("DELETE FROM subs WHERE handle=?", (handle,))
    db.query("DELETE FROM links WHERE handle=?", (handle,))
    db.query("DELETE FROM channels WHERE handle=?", (handle,))
    
    if (AVATAR_DIR / handle).exists(): (AVATAR_DIR / handle).unlink()
    if (BANNER_DIR / handle).exists(): (BANNER_DIR / handle).unlink()
    
    if premium_tier:
        premium_tier.nuke_channel_media_all(db.conn, handle)
    
    if livestream:
        livestream.end_stream(db.conn, handle)
        
    db.close()
    return True

def render_cli_dashboard(db):
    clear()
    total_channels = db.query("SELECT COUNT(*) as c FROM channels")[0]['c']
    total_subs = db.query("SELECT COUNT(*) as c FROM subs")[0]['c']
    total_sent = db.query("SELECT SUM(sent_count) as c FROM broadcast_history")[0]['c'] or 0
    total_clicks = db.query("SELECT COUNT(*) as c FROM analytics_events WHERE type='notif'")[0]['c']
    ctr = (total_clicks / total_sent * 100) if total_sent > 0 else 0
    
    layout = Layout()
    layout.split(Layout(name="header", size=3), Layout(name="main", ratio=1), Layout(name="footer", size=7))
    layout["main"].split_row(Layout(name="stats", ratio=1), Layout(name="chart", ratio=1))
    layout["header"].update(Panel(f"[bold yellow]NOTIFLY ULTIMATE MANAGER v8.7[/bold yellow] | {ts_to_str(time.time())}", style="bold white"))
    
    stats_grid = Table.grid(expand=True, padding=(1, 1))
    stats_grid.add_column("Metric", style="cyan", justify="right"); stats_grid.add_column("Value", style="bold green")
    stats_grid.add_row("Channels", str(total_channels))
    stats_grid.add_row("Subscribers", str(total_subs))
    stats_grid.add_row("Avatars / Banners", f"{len(list(AVATAR_DIR.glob('*')))} / {len(list(BANNER_DIR.glob('*')))}")
    stats_grid.add_row("Total Pushes", str(total_sent))
    stats_grid.add_row("Global CTR", f"{ctr:.1f}%")
    layout["stats"].update(Panel(stats_grid, title="Telemetry"))

    daily_data = get_daily_volume(db)
    max_val = max(daily_data.values()) if daily_data and max(daily_data.values()) > 0 else 1
    chart_str = ""
    for day, count in daily_data.items():
        bar = "█" * int((count / max_val) * 20)
        chart_str += f"[cyan]{day}[/cyan] │ [green]{bar}[/green] {count}\n"
    layout["chart"].update(Panel(chart_str.strip(), title="Broadcast Volume"))
    
    log_table = Table(title="Live Log", expand=True, box=box.SIMPLE_HEAD)
    log_table.add_column("Time", style="dim"); log_table.add_column("Handle", style="cyan"); log_table.add_column("Title"); log_table.add_column("Sent", style="green")
    logs = db.query("SELECT * FROM broadcast_history ORDER BY timestamp DESC LIMIT 3")
    if logs:
        for log in logs: log_table.add_row(ts_to_str(log['timestamp']), log['handle'], (log['title'] or "")[:30], str(log['sent_count']))
    layout["footer"].update(Panel(log_table))
    console.print(layout)

def channel_manager_loop(db):
    while True:
        clear()
        cutoff_new = int(time.time()) - (30 * 86400)
        channels = db.query("SELECT c.*, COUNT(s.endpoint) as sub_count FROM channels c LEFT JOIN subs s ON c.handle = s.handle GROUP BY c.handle ORDER BY sub_count DESC")
        
        table = Table(title=f"CHANNEL MANAGER ({len(channels)})", expand=True)
        table.add_column("Handle", style="cyan"); table.add_column("Status", justify="center"); table.add_column("Subs", style="green"); table.add_column("Assets", justify="center")
        
        for c in channels:
            created_at = c.get('created_at', 0) or 0
            if created_at > cutoff_new:
                days_ago = int((time.time() - created_at) / 86400)
                status_str = f"[bold yellow]NEW ({days_ago}d)[/bold yellow]" if days_ago > 0 else "[bold yellow]NEW (Today)[/bold yellow]"
            else:
                status_str = "[dim]-[/dim]"
            
            assets = []
            if (AVATAR_DIR / c['handle']).exists(): assets.append("AV")
            if (BANNER_DIR / c['handle']).exists(): assets.append("BN")
            
            table.add_row(c['handle'], status_str, str(c['sub_count']), ",".join(assets))
        
        console.print(table)
        console.print("\n[dim]Actions:[/dim] [e]xport | [d]elete | [b]ack")
        ch = Prompt.ask("Action", choices=['e','d','b'], default='b')
        if ch == 'b': return
        if ch == 'e':
            with open('channels.json','w') as f: json.dump(channels,f,indent=2)
            console.print("[green]Exported channels.json[/green]"); time.sleep(1)
        if ch == 'd':
            target = Prompt.ask("Enter Handle to [bold red]NUKE[/bold red]")
            if Confirm.ask(f"NUKE [bold red]{target}[/bold red]?"):
                delete_channel_completely(target)
                console.print(f"[green]Deleted {target}.[/green]"); time.sleep(1)

def bulk_prune_menu(db):
    while True:
        clear()
        console.print(Panel("[bold red]BULK CHANNEL PRUNING[/bold red]", border_style="red"))
        console.print("1. [cyan]Age[/cyan] (Created > X)")
        console.print("2. [cyan]Dormancy[/cyan] (Inactive > X)")
        console.print("b. Back")
        
        mode = Prompt.ask("Select Mode", choices=['1', '2', 'b'], default='b')
        if mode == 'b': return

        presets = ["90d", "60d", "30d", "14d", "7d", "3d", "1d", "12h", "6h", "3h", "1h", "30m", "15m", "5m"]
        console.print(f"\nPresets: {', '.join(presets)}")
        duration_input = Prompt.ask("Enter duration").lower()
        seconds = parse_duration(duration_input)
        if seconds == 0: continue
            
        cutoff_ts = int(time.time()) - seconds
        
        targets = []
        if mode == '1': 
            targets = db.query("SELECT handle, created_at as ts FROM channels WHERE created_at < ?", (cutoff_ts,))
        else: 
            all_ch = db.query("SELECT c.handle, c.created_at, MAX(b.timestamp) as last_active FROM channels c LEFT JOIN broadcast_history b ON c.handle = b.handle GROUP BY c.handle")
            if all_ch:
                for c in all_ch:
                    last_act = c['last_active'] if c['last_active'] else c['created_at']
                    if last_act < cutoff_ts: targets.append({'handle': c['handle'], 'ts': last_act})

        if not targets:
            console.print("[green]No matching channels.[/green]"); time.sleep(1); continue

        console.print(f"\n[bold red]FOUND {len(targets)} CHANNELS[/bold red]")
        if Confirm.ask(f"DELETE {len(targets)} channels?"):
            for t in track(targets, description="Pruning..."):
                delete_channel_completely(t['handle'])
            console.print("[green]Done.[/green]"); time.sleep(1)
def system_maintenance(db):
    clear()
    console.print(Panel("[bold red]STRICT SYSTEM MAINTENANCE[/bold red]", border_style="red"))
    console.print("[dim]Enforcing referential integrity. Deleting data with no valid source.[/dim]\n")
    
    if Confirm.ask("Execute Cleanup?"): 
        # 1. Clean Orphaned Broadcasts (Source of Hashtags)
        # If a channel was deleted, its old messages shouldn't generate hashtags.
        # We assume 'channels' table is the authority.
        console.print("[yellow]1. Checking Broadcast History...[/yellow]")
        bh_orphans = db.query("SELECT COUNT(*) as c FROM broadcast_history WHERE handle NOT IN (SELECT handle FROM channels)")[0]['c']
        if bh_orphans > 0:
            db.execute("DELETE FROM broadcast_history WHERE handle NOT IN (SELECT handle FROM channels)")
            console.print(f"[green]   ✓ Deleted {bh_orphans} messages from dead channels[/green]")
        else:
            console.print("[dim]   - No orphans found[/dim]")

        # 2. Clean Orphaned Links
        # If a channel is deleted, its links are dead.
        console.print("[yellow]2. Checking Link Registry...[/yellow]")
        try:
            link_orphans = db.query("SELECT COUNT(*) as c FROM links WHERE handle NOT IN (SELECT handle FROM channels)")[0]['c']
            if link_orphans > 0:
                db.execute("DELETE FROM links WHERE handle NOT IN (SELECT handle FROM channels)")
                console.print(f"[green]   ✓ Deleted {link_orphans} links from dead channels[/green]")
            else:
                console.print("[dim]   - No orphans found[/dim]")
        except: console.print("[dim]   - Links table not found or compatible[/dim]")

        # 3. Clean Orphaned Notification Analytics
        # If the broadcast message is gone (deleted above or manually), its click stats must go.
        console.print("[yellow]3. Checking Notification Analytics...[/yellow]")
        # Get list of valid BIDs
        valid_bids = [r['bid'] for r in db.query("SELECT bid FROM broadcast_history")]
        if valid_bids:
            ph = ','.join(['?'] * len(valid_bids))
            # Delete events where ref_id is NOT in the valid_bids list
            count = db.query(f"DELETE FROM analytics_events WHERE type='notif' AND ref_id NOT IN ({ph})", valid_bids)
            if count: console.print(f"[green]   ✓ Pruned {count} orphaned analytics events[/green]")
            else: console.print("[dim]   - Analytics healthy[/dim]")
        else:
            # If NO history exists, wipe all stats
            db.execute("DELETE FROM analytics_events WHERE type='notif'")
            console.print("[green]   ✓ History empty. Wiped all notification stats.[/green]")

        # 4. Clean Orphaned Link Analytics
        # If the link entry is gone, its stats must go.
        console.print("[yellow]4. Checking Link Analytics...[/yellow]")
        try:
            valid_links = [str(r['id']) for r in db.query("SELECT id FROM links")]
            if valid_links:
                ph = ','.join(['?'] * len(valid_links))
                count = db.query(f"DELETE FROM analytics_events WHERE type='link' AND ref_id NOT IN ({ph})", valid_links)
                if count: console.print(f"[green]   ✓ Pruned {count} orphaned link clicks[/green]")
                else: console.print("[dim]   - Link stats healthy[/dim]")
            else:
                 # If NO links exist, wipe all link stats
                db.execute("DELETE FROM analytics_events WHERE type='link'")
                console.print("[green]   ✓ No links found. Wiped all link stats.[/green]")
        except: pass

        # 5. Vacuum (Physical cleanup)
        console.print("[yellow]5. Compacting Database...[/yellow]")
        db.execute("VACUUM")
        console.print("[green]   ✓ Database compacted[/green]")
            
    Prompt.ask("\nMaintenance Complete. Press Enter...")

def cli_broadcast(db):
    clear(); console.print(Panel("[bold yellow]CLI Broadcast Station[/bold yellow]"))
    channels = db.query("SELECT handle, pin, (SELECT COUNT(*) FROM subs s WHERE s.handle=c.handle) as subs FROM channels c ORDER BY handle")
    if not channels: return console.print("[red]No channels.[/red]")
    
    console.print("[dim]Type part of a handle to filter, or Enter for all[/dim]")
    search = Prompt.ask("Search Handle").lower()
    matches = [c for c in channels if search in c['handle'].lower()]
    if not matches: console.print("[red]No matches.[/red]"); time.sleep(1); return
    
    for i, c in enumerate(matches): console.print(f"{i+1}. [cyan]{c['handle']}[/cyan] ({c['subs']} subs)")
    idx_raw = Prompt.ask("Select Channel #")
    try: idx = int(idx_raw) - 1
    except: return
    if idx < 0 or idx >= len(matches): return
    target = matches[idx]
    
    console.print(f"\n[bold]Composing for: {target['handle']}[/bold]")
    t = Prompt.ask("Title"); b = Prompt.ask("Body"); u = Prompt.ask("Click URL (opt)")
    
    if Confirm.ask("SEND NOW?"):
        try:
            payload = {"handle": target['handle'], "pin": target['pin'], "title": t, "body": b, "url": u, "icon": "https://cdn-icons-png.flaticon.com/512/1156/1156948.png"}
            req = urllib.request.Request(f"{SERVER_URL}/api/broadcast/{target['handle']}", data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
            urllib.request.urlopen(req); console.print("[green]Sent![/green]")
        except Exception as e: console.print(f"[red]Error: {e}[/red]")
    Prompt.ask("Enter...")

def manage_nsfw_gate(db):
    if nsfw_gate is None:
        console.print("[red]NSFW Gate module missing.[/red]"); time.sleep(1); return
    nsfw_gate.init_db(db)
    while True:
        clear(); console.print(Panel(f"[bold red]NSFW GATE ({len(nsfw_gate.get_all_domains(db))} blocked)[/bold red]"))
        console.print("1. Block Domain\n2. Unblock Domain\nb. Back")
        ch = Prompt.ask("Select", choices=['1','2','b'], default='b')
        if ch == 'b': return
        if ch == '1': d = Prompt.ask("Domain"); nsfw_gate.add_domain(db, d)
        if ch == '2': d = Prompt.ask("Domain"); nsfw_gate.remove_domain(db, d)

def backup_manager(db):
    while True:
        clear(); console.print(Panel("[bold magenta]Backup & Disaster Recovery[/bold magenta]"))
        backups = sorted(list(BACKUP_DIR.glob("*.zip")), key=os.path.getmtime, reverse=True)
        for b in backups[:5]: console.print(f"{b.name} ({b.stat().st_size / (1024*1024):.2f} MB)")
        console.print("\n1. Create NEW Backup\n2. Delete Old (>7d)\nb. Back")
        ch = Prompt.ask("Select", choices=['1','2','b'], default='b')
        if ch == 'b': return
        if ch == '1':
            fname = f"backup_{int(time.time())}.zip"
            with zipfile.ZipFile(BACKUP_DIR / fname, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(DB_FILE, arcname="notifly.db")
                for av in AVATAR_DIR.glob("*"): zipf.write(av, arcname=f"avatars/{av.name}")
                for bn in BANNER_DIR.glob("*"): zipf.write(bn, arcname=f"banners/{bn.name}")
            console.print(f"[green]Saved: {fname}[/green]"); time.sleep(1)
        if ch == '2':
            cutoff = time.time() - (7*86400)
            for b in backups: 
                if b.stat().st_mtime < cutoff: b.unlink()
            console.print("[green]Pruned.[/green]"); time.sleep(1)

def sitemap_cli(db):
    if not sitemap_gen: console.print("[red]Sitemap module missing.[/red]"); time.sleep(1); return
    console.print("[yellow]Generating Sitemap...[/yellow]")
    xml = sitemap_gen.generate_sitemap(db, "notifly.cc")
    with open("sitemap.xml", "w") as f: f.write(xml)
    console.print("[green]Sitemap Generated![/green]"); time.sleep(2)

def livestream_cli(db):
    if not livestream: console.print("[red]Livestream module missing.[/red]"); time.sleep(1); return
    while True:
        clear(); console.print(Panel("[bold red]LIVESTREAM MANAGER[/bold red]"))
        streams = db.query("SELECT * FROM livestreams WHERE is_live=1")
        if not streams: console.print("[dim]No active streams.[/dim]")
        else:
            for s in streams: console.print(f"[green]LIVE[/green] {s['handle']} (Viewers: {s['viewer_count']})")
        console.print("\n[k]ill stream | [b]ack")
        ch = Prompt.ask("Action", choices=['k','b'], default='b')
        if ch == 'b': return
        if ch == 'k':
            h = Prompt.ask("Handle to kill")
            livestream.end_stream(db.conn, h)
            console.print("[red]Stream Killed.[/red]"); time.sleep(1)

def main():
    db = DBManager()
    
    if nsfw_gate: nsfw_gate.init_db(db)
    if premium_tier: premium_tier.init_db(db.conn)
    if premium_tier_2: premium_tier_2.init_db(db.conn)
    if portal_dashboard: portal_dashboard.init_db(db.cur)
    
    while True:
        render_cli_dashboard(db)
        console.print(Panel("""[cyan]1[/cyan]: Channels   [cyan]2[/cyan]: Subs       [cyan]3[/cyan]: SQL      [cyan]4[/cyan]: Backup
[bold red]5[/bold red]: Prune      [cyan]6[/cyan]: Maint      [yellow]B[/yellow]: Brdcast  [red]G[/red]: Gate
[red]L[/red]: Stream     [green]S[/green]: Sitemap    [orange]P[/orange]: Premium  [magenta]T[/magenta]: Tier2
[bold white]9: WEB HQ SERVER[/bold white]""", title="Master Control"))
        
        choice = Prompt.ask("Select", choices=['1','2','3','4','5','6','B','G','L','S','P','T','9','q'], default='9').upper()
        
        if choice == '1': channel_manager_loop(db)
        elif choice == '2': 
            subs = db.query("SELECT * FROM subs")
            t = Table(title="SUBS"); t.add_column("Handle"); t.add_column("Endpoint")
            for s in subs: t.add_row(s['handle'], s['endpoint'][-15:])
            console.print(t); Prompt.ask("Enter...")
        elif choice == '3':
            q = Prompt.ask("SQL>"); 
            try: console.print(db.query(q))
            except Exception as e: console.print(e)
            Prompt.ask("Enter...")
        elif choice == '4': backup_manager(db)
        elif choice == '5': bulk_prune_menu(db)
        elif choice == '6': system_maintenance(db)
        elif choice == 'B': cli_broadcast(db)
        elif choice == 'G': manage_nsfw_gate(db)
        elif choice == 'L': livestream_cli(db)
        elif choice == 'S': sitemap_cli(db)
        elif choice == 'P':
            if not premium_tier:
                console.print("[red]Premium module not loaded.[/red]"); time.sleep(1)
                continue
            
            while True:
                clear()
                console.print(Panel("[bold yellow]PREMIUM ADMIN MANAGEMENT[/bold yellow]"))
                console.print("1. Generate NEW Admin")
                console.print("2. List / Manage Admins")
                console.print("3. Premium Overseer (Channels)")
                console.print("b. Back")
                
                p_ch = Prompt.ask("Select", choices=['1', '2', '3', 'b'], default='b')
                
                if p_ch == 'b': break
                
                if p_ch == '1':
                    if Confirm.ask("Generate new credentials (3 Slots)?"):
                        # Unpack 3 values including token
                        u, p, token = premium_tier.generate_admin(db.conn)
                        console.print(f"\n[bold green]SUCCESS![/bold green]\nUsername: [cyan]{u}[/cyan]\nPassword: [cyan]{p}[/cyan]\nLink: [cyan]https://notifly.cc/claim/{token}[/cyan]")
                        Prompt.ask("Press Enter...")

                if p_ch == '2':
                    clear()
                    admins = premium_tier.get_all_admins(db.conn)
                    t = Table(title=f"PREMIUM ADMINS ({len(admins)})")
                    t.add_column("ID", style="cyan"); t.add_column("Username"); t.add_column("Slots"); t.add_column("Storage (MB)", justify="right"); t.add_column("Ref Token", style="dim")
                    for a in admins:
                        t.add_row(str(a['id']), a['username'], f"{a['slots_used']}/{a['slots_max']}", f"{a['storage_used']/1024/1024:.2f}", a.get('referral_token', 'N/A'))
                    console.print(t)
                    
                    action = Prompt.ask("Action", choices=['d', 'm', 'b'], default='b').lower()
                    if action == 'b': continue
                    if action == 'd':
                        tid = IntPrompt.ask("Admin ID")
                        if Confirm.ask(f"Delete ID {tid}?"): premium_tier.delete_admin(db.conn, tid)
                    if action == 'm':
                        tid = IntPrompt.ask("Admin ID"); slots = IntPrompt.ask("New Slots")
                        premium_tier.update_admin_slots(db.conn, tid, slots)

                if p_ch == '3':
                    clear()
                    channels = premium_tier.get_all_premium_channels(db.conn)
                    
                    ot = Table(title=f"PREMIUM OVERSEER ({len(channels)})", expand=True)
                    ot.add_column("Handle", style="bold yellow"); ot.add_column("Owner", style="dim"); ot.add_column("Files", justify="center"); ot.add_column("Storage", justify="right"); ot.add_column("Status")

                    for c in channels:
                        size_mb = c['storage_used'] / 1024 / 1024
                        size_str = f"[green]{size_mb:.2f} MB[/green]"
                        if size_mb > 500: size_str = f"[red]{size_mb:.2f} MB[/red]"
                        elif size_mb > 100: size_str = f"[yellow]{size_mb:.2f} MB[/yellow]"
                        ot.add_row(c['handle'], c['admin'], str(c['file_count']), size_str, "🔒 Premium")
                    
                    console.print(ot)
                    console.print("\n[dim]Actions:[/dim] [U]nlock Channel | [P]urge Media | [B]ack")
                    o_act = Prompt.ask("Action", choices=['u', 'p', 'b'], default='b').lower()
                    
                    if o_act == 'b': continue
                    target = Prompt.ask("Enter Target Handle")
                    
                    if not any(c['handle'] == target for c in channels):
                        console.print("[red]Handle not found in premium list.[/red]"); time.sleep(1); continue
                    
                    if o_act == 'u':
                        if Confirm.ask(f"Downgrade [bold yellow]{target}[/bold yellow] to Free?"):
                            premium_tier.unlock_channel_only(db.conn, target)
                            console.print("[green]Channel Unlocked.[/green]"); time.sleep(1)
                            
                    if o_act == 'p':
                        if Confirm.ask(f"[bold red]DELETE ALL MEDIA[/bold red] for {target}?"):
                            files = premium_tier.nuke_channel_media_all(db.conn, target)
                            for f in files:
                                path = PREMIUM_MEDIA_DIR / f
                                if path.exists(): path.unlink()
                            console.print(f"[green]Deleted {len(files)} files.[/green]"); time.sleep(1)
        
        elif choice == 'T':
            if not premium_tier_2:
                console.print("[red]Tier 2 module not loaded.[/red]"); time.sleep(1)
                continue
            
            while True:
                clear()
                console.print(Panel("[bold magenta]⚡ TIER 2 ELITE MANAGEMENT[/bold magenta]", border_style="magenta"))
                
                tier2_channels = premium_tier_2.get_all_tier_2_channels(db.conn)
                
                t = Table(title=f"TIER 2 CHANNELS ({len(tier2_channels)})")
                t.add_column("Handle", style="bold magenta")
                t.add_column("Granted", style="dim")
                t.add_column("Status", style="cyan")
                
                for ch in tier2_channels:
                    t.add_row(ch['handle'], ts_to_str(ch['granted_at']), ch['status'].upper())
                
                console.print(t)
                console.print("\n[dim]Actions:[/dim]")
                console.print("[G]rant Tier 2 | [R]evoke Tier 2 | [B]ack")
                
                t_ch = Prompt.ask("Action", choices=['g', 'r', 'b'], default='b').lower()
                
                if t_ch == 'b': break
                
                if t_ch == 'g':
                    handle = Prompt.ask("Enter channel handle to grant Tier 2")
                    if Confirm.ask(f"Grant Tier 2 access to [bold magenta]{handle}[/bold magenta]?"):
                        result = premium_tier_2.grant_tier_2(db.conn, handle)
                        if result['success']:
                            console.print(f"[bold green]✓[/bold green] {result['msg']}")
                        else:
                            console.print(f"[bold red]✗[/bold red] {result['msg']}")
                        time.sleep(2)
                
                if t_ch == 'r':
                    handle = Prompt.ask("Enter channel handle to revoke Tier 2")
                    if Confirm.ask(f"[bold red]REVOKE[/bold red] Tier 2 from {handle}?"):
                        result = premium_tier_2.revoke_tier_2(db.conn, handle)
                        if result['success']:
                            console.print(f"[bold yellow]⚠[/bold yellow] {result['msg']}")
                        else:
                            console.print(f"[bold red]✗[/bold red] {result['msg']}")
                        time.sleep(2)

        elif choice == '9': run_hq_server()
        elif choice == 'Q': db.close(); sys.exit(0)

if __name__ == "__main__":
    main()
