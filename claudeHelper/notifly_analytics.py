"""
NotiFly Analytics Module v1.1 (Layout Fix)
Handles passive data collection and renders a mobile-friendly vertical dashboard.
"""
import sqlite3
import time
import json
import re
import threading
from urllib.request import urlopen

# --- DATABASE SETUP ---
def init_db(db):
    try:
        db.execute("""CREATE TABLE IF NOT EXISTS sub_metadata (
            endpoint TEXT PRIMARY KEY,
            handle TEXT,
            country TEXT DEFAULT 'Unknown',
            region TEXT DEFAULT 'Unknown',
            city TEXT DEFAULT 'Unknown',
            device_type TEXT DEFAULT 'Desktop',
            os TEXT DEFAULT 'Unknown',
            browser TEXT DEFAULT 'Unknown',
            referrer TEXT DEFAULT 'Direct',
            created_at INTEGER
        )""")
    except Exception as e:
        print(f"[Analytics] DB Init Error: {e}")

# --- PARSING LOGIC ---
class PassiveParser:
    @staticmethod
    def get_geo(ip):
        if ip in ['127.0.0.1', 'localhost', '::1']:
            return "Local", "Local", "Local"
        try:
            with urlopen(f"http://ip-api.com/json/{ip}?fields=country,regionName,city", timeout=3) as url:
                data = json.loads(url.read().decode())
                return data.get('country', 'Unknown'), data.get('regionName', 'Unknown'), data.get('city', 'Unknown')
        except:
            return "Unknown", "Unknown", "Unknown"

    @staticmethod
    def parse_ua(ua):
        ua = ua.lower()
        device = "Desktop"
        os = "Unknown"
        browser = "Unknown"

        if "mobile" in ua or "android" in ua or "iphone" in ua: device = "Mobile"
        elif "tablet" in ua or "ipad" in ua: device = "Tablet"

        if "windows" in ua: os = "Windows"
        elif "android" in ua: os = "Android"
        elif "iphone" in ua or "ipad" in ua: os = "iOS"
        elif "mac os" in ua: os = "macOS"
        elif "linux" in ua: os = "Linux"

        if "firefox" in ua: browser = "Firefox"
        elif "chrome" in ua and "edg" not in ua: browser = "Chrome"
        elif "safari" in ua and "chrome" not in ua: browser = "Safari"
        elif "edg" in ua: browser = "Edge"
        elif "samsungbrowser" in ua: browser = "Samsung"

        return device, os, browser

# --- INGESTION ---
def track_subscriber(db, handle, endpoint, headers, client_ip):
    def _worker():
        try:
            ua_string = headers.get('User-Agent', '')
            ref_string = headers.get('Referer', 'Direct')
            if len(ref_string) > 50: ref_string = ref_string[:50] + "..."
            device, os, browser = PassiveParser.parse_ua(ua_string)
            country, region, city = PassiveParser.get_geo(client_ip)
            db.execute("""INSERT OR REPLACE INTO sub_metadata 
                (endpoint, handle, country, region, city, device_type, os, browser, referrer, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (endpoint, handle, country, region, city, device, os, browser, ref_string, int(time.time())))
        except Exception as e:
            print(f"[Analytics] Tracking Error: {e}")
    threading.Thread(target=_worker, daemon=True).start()

# --- DASHBOARD RENDERING ---
def render_enhanced_stats(db, handle):
    rows = db.query(f"SELECT * FROM sub_metadata WHERE handle = ?", (handle,))
    if not rows:
        return '<div style="padding:20px;text-align:center;color:#666">No advanced subscriber data yet.</div>'

    devices = {}
    geo = {}
    os_data = {}

    for r in rows:
        d = r['device_type']
        devices[d] = devices.get(d, 0) + 1
        g = r['country']
        geo[g] = geo.get(g, 0) + 1
        o = r['os']
        os_data[o] = os_data.get(o, 0) + 1

    def to_js(data_dict):
        return json.dumps(list(data_dict.keys())), json.dumps(list(data_dict.values()))

    dev_l, dev_c = to_js(devices)
    geo_l, geo_c = to_js(geo)
    os_l, os_c = to_js(os_data)

    # UPDATED HTML: Uses simple vertical stacking (no grid) to fit narrow screens.
    return f"""
    <div style="margin-top:30px; border-top:1px dashed #444; padding-top:20px;">
        <h2 style="color:#eab308; font-size:18px;">Visitor Demographics</h2>
        
        <div style="display:flex; flex-direction:column; gap:15px;">
            
            <div style="background:#1a1a1a; padding:15px; border-radius:10px;">
                <h3 style="font-size:12px; color:#aaa; margin:0 0 10px 0; text-align:left;">Device Types</h3>
                <div style="height:200px; display:flex; justify-content:center;">
                    <canvas id="devChart"></canvas>
                </div>
            </div>

            <div style="background:#1a1a1a; padding:15px; border-radius:10px;">
                <h3 style="font-size:12px; color:#aaa; margin:0 0 10px 0; text-align:left;">Operating Systems</h3>
                <div style="height:200px; display:flex; justify-content:center;">
                    <canvas id="osChart"></canvas>
                </div>
            </div>

            <div style="background:#1a1a1a; padding:15px; border-radius:10px;">
                <h3 style="font-size:12px; color:#aaa; margin:0 0 10px 0; text-align:left;">Top Locations</h3>
                <canvas id="geoChart" style="max-height:200px"></canvas>
            </div>
            
        </div>
    </div>
    <script>
    (function(){{
        const commonOpt = {{ 
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{ legend: {{ position: 'right', labels: {{ color: '#aaa', font: {{ size: 11 }} }} }} }} 
        }};
        
        new Chart(document.getElementById('devChart'), {{
            type: 'doughnut',
            data: {{ labels: {dev_l}, datasets: [{{ data: {dev_c}, backgroundColor: ['#38bdf8', '#eab308', '#f87171'], borderWidth:0 }}] }},
            options: commonOpt
        }});

        new Chart(document.getElementById('osChart'), {{
            type: 'pie',
            data: {{ labels: {os_l}, datasets: [{{ data: {os_c}, backgroundColor: ['#a78bfa', '#34d399', '#fbbf24', '#60a5fa', '#94a3b8'], borderWidth:0 }}] }},
            options: commonOpt
        }});

        new Chart(document.getElementById('geoChart'), {{
            type: 'bar',
            data: {{ labels: {geo_l}, datasets: [{{ label: 'Subscribers', data: {geo_c}, backgroundColor: '#eab308', borderRadius: 4 }}] }},
            options: {{ scales: {{ y: {{ beginAtZero:true, grid:{{color:'#333'}} }}, x: {{ grid:{{display:false}} }} }}, plugins: {{ legend: {{ display: false }} }} }}
        }});
    }})();
    </script>
    """
