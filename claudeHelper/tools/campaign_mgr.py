META = {
    "name": "Campaign Manager Pro",
    "desc": "Create tracking links with deep analytics (OS, Hourly, Referrers).",
    "icon": "📣"
}

import sqlite3
import time
import uuid
import json
import re
from datetime import datetime, timedelta
import math

# --- INTERNAL ANALYTICS ENGINE ---
class MiniAnalytics:
    @staticmethod
    def parse_ua(ua):
        ua = ua.lower()
        if 'bot' in ua or 'crawl' in ua or 'slurp' in ua or 'spider' in ua: return 'Bot'
        if 'iphone' in ua or 'ipad' in ua or 'ipod' in ua: return 'iOS'
        if 'android' in ua: return 'Android'
        if 'windows' in ua: return 'Windows'
        if 'macintosh' in ua or 'mac os' in ua: return 'Mac'
        if 'linux' in ua: return 'Linux'
        return 'Other'

    @staticmethod
    def get_time_buckets(rows, hours=48):
        # Initialize buckets
        now = int(time.time())
        buckets = [0] * hours
        start_time = now - (hours * 3600)
        
        for r in rows:
            ts = r['timestamp']
            if ts > start_time:
                # Calculate index: (timestamp - start) / 3600
                idx = int((ts - start_time) / 3600)
                if 0 <= idx < hours:
                    buckets[idx] += 1
        return buckets

# --- DB INIT ---
def init_db(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS campaigns (
        id TEXT PRIMARY KEY,
        handle TEXT,
        target_url TEXT,
        og_title TEXT,
        og_desc TEXT,
        og_image TEXT,
        clicks INTEGER DEFAULT 0,
        created_at INTEGER
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS campaign_analytics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cid TEXT,
        referrer TEXT,
        user_agent TEXT,
        timestamp INTEGER
    )""")
    # Cleanup old campaigns (3 days)
    cutoff = int(time.time()) - (3 * 86400)
    conn.execute("DELETE FROM campaigns WHERE created_at < ?", (cutoff,))
    conn.commit()

# --- MAIN RUNNER ---
def run(conn, handle, payload):
    init_db(conn)
    action = payload.get('sub_action')

    # --- ACTIONS ---
    if action == 'delete':
        cid = payload.get('cid')
        conn.execute("DELETE FROM campaigns WHERE id = ? AND handle = ?", (cid, handle))
        conn.execute("DELETE FROM campaign_analytics WHERE cid = ?", (cid,))
        conn.commit()
        return {"success": True, "reload": True}

    if action == 'create':
        cid = str(uuid.uuid4())[:8]
        target = payload.get('target')
        if not target.startswith('http'): target = 'https://' + target
        
        conn.execute("""INSERT INTO campaigns (id, handle, target_url, og_title, og_desc, og_image, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)""",
                     (cid, handle, target, payload.get('title'), payload.get('desc'), payload.get('image'), int(time.time())))
        conn.commit()
        return {"success": True, "reload": True}

    # --- RENDER DASHBOARD ---
    rows = conn.execute("SELECT * FROM campaigns WHERE handle = ? ORDER BY created_at DESC", (handle,)).fetchall()
    
    list_html = ""
    if not rows:
        list_html = "<div style='text-align:center;color:#666;padding:40px'>No active campaigns. Create one above!</div>"
    
    for r in rows:
        cid = r['id']
        # Fetch raw analytics
        logs = conn.execute("SELECT referrer, user_agent, timestamp FROM campaign_analytics WHERE cid = ?", (cid,)).fetchall()
        
        # 1. Process OS Stats
        os_counts = {'iOS': 0, 'Android': 0, 'Windows': 0, 'Mac': 0, 'Linux': 0, 'Other': 0, 'Bot': 0}
        total_real = 0
        for log in logs:
            os_name = MiniAnalytics.parse_ua(log['user_agent'] or "")
            os_counts[os_name] = os_counts.get(os_name, 0) + 1
            if os_name != 'Bot': total_real += 1
            
        # 2. Process Timeline (48h)
        buckets = MiniAnalytics.get_time_buckets(logs, 48)
        max_b = max(buckets) if buckets else 0
        sparkline_html = ""
        for b in buckets:
            h = (b / max_b * 30) + 2 if max_b > 0 else 2 # Height in pixels (min 2)
            bg = "#eab308" if b > 0 else "#333"
            sparkline_html += f'<div style="width:100%;background:{bg};height:{h}px;border-radius:1px;margin:0 1px"></div>'

        # 3. Process Referrers
        refs = {}
        for log in logs:
            rf = log['referrer']
            if not rf: rf = "Direct / Dark"
            refs[rf] = refs.get(rf, 0) + 1
        sorted_refs = sorted(refs.items(), key=lambda x: x[1], reverse=True)[:5]
        
        ref_html = ""
        for site, count in sorted_refs:
            pct = int((count / len(logs) * 100)) if logs else 0
            ref_html += f"""
            <div style="display:flex; align-items:center; margin-bottom:4px; font-size:11px;">
                <div style="width:100px; color:#aaa; overflow:hidden; white-space:nowrap; text-overflow:ellipsis;">{site}</div>
                <div style="flex-grow:1; background:#222; height:6px; border-radius:3px; margin:0 8px;">
                    <div style="width:{pct}%; background:#555; height:100%; border-radius:3px;"></div>
                </div>
                <div style="width:30px; text-align:right; color:#fff;">{count}</div>
            </div>
            """

        # 4. OS Bar
        os_bar_html = ""
        colors = {'iOS': '#fff', 'Android': '#a4c639', 'Windows': '#00a4ef', 'Mac': '#999', 'Linux': '#f0b429', 'Other': '#555', 'Bot': '#f87171'}
        for os_k, os_v in os_counts.items():
            if os_v > 0:
                pct = (os_v / len(logs)) * 100
                os_bar_html += f'<div title="{os_k}: {os_v}" style="width:{pct}%; background:{colors[os_k]}; height:100%;"></div>'

        magic_link = f"https://notifly.cc/trk/c/{cid}"
        age_hours = int((int(time.time()) - r['created_at']) / 3600)
        
        list_html += f"""
        <div style="background:#151515; border:1px solid #333; padding:15px; border-radius:10px; margin-bottom:15px; box-shadow:0 4px 10px rgba(0,0,0,0.3);">
            <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                <div>
                    <div style="font-weight:bold; color:#fff; font-size:14px;">{r['og_title'] or 'Untitled Campaign'}</div>
                    <div style="font-size:11px; color:#666;">Target: <a href="{r['target_url']}" target="_blank" style="color:#666">{r['target_url']}</a></div>
                </div>
                <div style="text-align:right;">
                    <div style="font-size:18px; color:#eab308; font-weight:bold;">{total_real}</div>
                    <div style="font-size:9px; color:#666;">REAL CLICKS</div>
                </div>
            </div>

            <div style="background:#0a0a0a; border:1px solid #333; padding:8px; border-radius:6px; display:flex; gap:10px; align-items:center; margin-bottom:15px;">
                <div style="flex-grow:1; font-family:monospace; font-size:11px; color:#4ade80; overflow:hidden; white-space:nowrap; text-overflow:ellipsis;" id="lnk_{cid}">{magic_link}</div>
                <button onclick="navigator.clipboard.writeText('{magic_link}');this.innerText='✓'" style="background:#333; color:#fff; border:none; padding:4px 8px; border-radius:4px; font-size:10px; cursor:pointer;">COPY</button>
            </div>

            <div style="display:grid; grid-template-columns: 1fr 1fr; gap:15px;">
                <div>
                    <div style="font-size:9px; color:#666; margin-bottom:2px;">ACTIVITY (LAST 48H)</div>
                    <div style="display:flex; align-items:flex-end; height:32px; gap:1px; margin-bottom:15px;">
                        {sparkline_html}
                    </div>
                    
                    <div style="font-size:9px; color:#666; margin-bottom:2px;">DEVICE BREAKDOWN</div>
                    <div style="width:100%; height:8px; background:#222; border-radius:4px; overflow:hidden; display:flex;">
                        {os_bar_html}
                    </div>
                    <div style="display:flex; gap:10px; margin-top:4px; font-size:9px; color:#888;">
                        <span><span style="color:#fff">●</span> iOS</span>
                        <span><span style="color:#a4c639">●</span> Android</span>
                        <span><span style="color:#00a4ef">●</span> Win</span>
                        <span><span style="color:#f87171">●</span> Bot</span>
                    </div>
                </div>
                
                <div style="border-left:1px solid #333; padding-left:15px;">
                    <div style="font-size:9px; color:#666; margin-bottom:5px;">TOP SOURCES</div>
                    {ref_html if ref_html else '<div style="font-size:10px;color:#444">No data yet</div>'}
                </div>
            </div>

            <div style="margin-top:15px; border-top:1px solid #222; padding-top:10px; display:flex; justify-content:space-between; align-items:center;">
                <div style="font-size:10px; color:#555;">Created {age_hours}h ago • {r['clicks']} Total Events</div>
                <button onclick="delCamp('{cid}')" style="background:transparent; border:1px solid #f87171; color:#f87171; padding:4px 10px; border-radius:4px; font-size:10px; cursor:pointer;">DELETE CAMPAIGN</button>
            </div>
        </div>
        """

    html = f"""
    <div style="color:#fff">
        <h3 style="margin-top:0; color:#eab308; display:flex; align-items:center; gap:10px;">
            <span>📣 Campaign Manager Pro</span>
            <span style="font-size:10px; background:#333; color:#aaa; padding:2px 6px; border-radius:4px;">v2.0</span>
        </h3>
        <p style="font-size:12px; color:#aaa; margin-bottom:20px;">Generate tracking links with OpenGraph embeds and real-time OS/Source analytics.</p>
        
        <details style="margin-bottom:20px; background:#111; border:1px solid #333; border-radius:8px; overflow:hidden;">
            <summary style="padding:10px; font-size:12px; font-weight:bold; cursor:pointer; background:#222;">＋ Create New Tracking Link</summary>
            <div style="padding:15px;">
                <div style="display:grid; grid-template-columns: 1fr 1fr; gap:10px; margin-bottom:10px;">
                    <input id="cp_title" placeholder="Title (e.g. 'Summer Sale')" style="background:#000; color:#fff; border:1px solid #333; padding:10px; border-radius:4px;">
                    <input id="cp_desc" placeholder="Description" style="background:#000; color:#fff; border:1px solid #333; padding:10px; border-radius:4px;">
                </div>
                <input id="cp_img" placeholder="Image URL (http...)" style="width:100%; margin-bottom:10px; background:#000; color:#fff; border:1px solid #333; padding:10px; border-radius:4px; box-sizing:border-box;">
                <input id="cp_target" placeholder="Target URL (https://your-shop.com/item)" style="width:100%; margin-bottom:15px; background:#000; color:#eab308; border:1px solid #eab308; padding:10px; border-radius:4px; box-sizing:border-box; font-weight:bold;">
                <button onclick="createCamp(this)" style="width:100%; background:#eab308; color:#000; font-weight:bold; padding:12px; border:none; border-radius:4px; cursor:pointer;">GENERATE LINK</button>
            </div>
        </details>

        <div id="campaign_list">
            {list_html}
        </div>
    </div>

    <script>
    async function createCamp(btn) {{
        const t = document.getElementById('cp_title').value;
        const d = document.getElementById('cp_desc').value;
        const i = document.getElementById('cp_img').value;
        const url = document.getElementById('cp_target').value;
        if(!t || !url) return alert("Title and Target URL are required!");

        btn.disabled = true;
        btn.innerText = "Generating...";

        const r = await fetch('/api/tier2/exec/toolbox/' + handle, {{
            method: 'POST',
            body: JSON.stringify({{ 
                pin: pin, 
                action: 'exec_tool', 
                payload: {{ tool_id: 'campaign_mgr', data: {{ sub_action: 'create', title: t, desc: d, image: i, target: url }} }} 
            }})
        }});
        const j = await r.json();
        if(j.reload) runTool('campaign_mgr', 'Campaign Manager Pro');
        else {{ alert(j.msg); btn.disabled = false; btn.innerText = "Generate Link"; }}
    }}

    async function delCamp(cid) {{
        if(!confirm("Delete this campaign and all its analytics?")) return;
        const r = await fetch('/api/tier2/exec/toolbox/' + handle, {{
            method: 'POST',
            body: JSON.stringify({{ 
                pin: pin, 
                action: 'exec_tool', 
                payload: {{ tool_id: 'campaign_mgr', data: {{ sub_action: 'delete', cid: cid }} }} 
            }})
        }});
        runTool('campaign_mgr', 'Campaign Manager Pro');
    }}
    </script>
    """
    return {"success": True, "html": html}
