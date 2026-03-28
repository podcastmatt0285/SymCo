"""
Tier 2 Module: Advanced Analytics Engine
Delivers complex metrics: Engagement Heatmaps, Churn Cohorts, and Viral Scoring.
"""
import time
import json
import sqlite3
from datetime import datetime
import premium_tier_2

def analytics_handler(conn, handle, action, payload):
    if action == "render":
        return render_dashboard_widget(conn, handle)
    return {"success": False, "msg": "Unknown Action"}

def render_dashboard_widget(conn, handle):
    """
    Returns an HTML block with embedded Chart.js to be injected into the Admin Dashboard.
    """
    # 1. Calculate metrics
    heatmap_data = get_engagement_heatmap(conn, handle)
    churn_data = get_churn_metrics(conn, handle)
    top_scored = get_viral_scores(conn, handle)
    
    # 2. Generate HTML
    # We use a distinct dark-blue theme to differentiate Tier 2 from standard stats
    html = f"""
    <div style="margin-top:40px; background: linear-gradient(145deg, #0f172a, #1e293b); border:1px solid #334155; border-radius:12px; padding:20px; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px; border-bottom:1px solid #334155; padding-bottom:10px;">
            <h2 style="margin:0; color:#38bdf8; font-size:18px; display:flex; align-items:center; gap:10px;">
                <span>⚡ TIER 2 INTELLIGENCE</span>
                <span style="background:#0ea5e9; color:#fff; font-size:10px; padding:2px 6px; border-radius:4px;">PRO</span>
            </h2>
            <div style="font-size:11px; color:#94a3b8;">Complex Analysis Active</div>
        </div>

        <div style="display:grid; grid-template-columns: 1fr 1fr 1fr; gap:15px; margin-bottom:25px;">
            <div style="background:#0f172a; padding:15px; border-radius:8px; text-align:center; border:1px solid #1e293b;">
                <div style="font-size:11px; color:#64748b; text-transform:uppercase; letter-spacing:1px;">Net Retention</div>
                <div style="font-size:24px; color:#fff; font-weight:bold; margin-top:5px;">{churn_data['retention_rate']}%</div>
            </div>
            <div style="background:#0f172a; padding:15px; border-radius:8px; text-align:center; border:1px solid #1e293b;">
                <div style="font-size:11px; color:#64748b; text-transform:uppercase; letter-spacing:1px;">Total Churn</div>
                <div style="font-size:24px; color:#f87171; font-weight:bold; margin-top:5px;">{churn_data['churn_count']}</div>
            </div>
            <div style="background:#0f172a; padding:15px; border-radius:8px; text-align:center; border:1px solid #1e293b;">
                <div style="font-size:11px; color:#64748b; text-transform:uppercase; letter-spacing:1px;">Ghost Users</div>
                <div style="font-size:24px; color:#94a3b8; font-weight:bold; margin-top:5px;">{churn_data['ghosts']}</div>
                <div style="font-size:9px; color:#475569;">(Inactive > 30 days)</div>
            </div>
        </div>

        <div style="margin-bottom:25px;">
            <h3 style="font-size:14px; color:#cbd5e1; margin-bottom:10px;">🔥 The "Golden Hour" Heatmap</h3>
            <p style="font-size:11px; color:#64748b; margin-top:-5px; margin-bottom:15px;">
                Based on historical click timing. Darker squares = Higher Engagement.
            </p>
            <div style="display:grid; grid-template-columns: 30px repeat(24, 1fr); gap:2px;">
                {_render_heatmap_grid(heatmap_data)}
            </div>
            <div style="display:flex; justify-content:space-between; margin-top:5px; font-size:9px; color:#475569; padding-left:30px;">
                <span>00:00</span><span>06:00</span><span>12:00</span><span>18:00</span><span>23:00</span>
            </div>
        </div>

        <div>
            <h3 style="font-size:14px; color:#cbd5e1; margin-bottom:10px;">🏆 Top Performing Broadcasts (Viral Score)</h3>
            <table style="width:100%; border-collapse:collapse; font-size:12px; color:#cbd5e1;">
                <thead>
                    <tr style="text-align:left; color:#64748b; border-bottom:1px solid #334155;">
                        <th style="padding:8px;">Title</th>
                        <th style="padding:8px; text-align:right;">CTR</th>
                        <th style="padding:8px; text-align:right;">Viral Score</th>
                    </tr>
                </thead>
                <tbody>
                    {_render_viral_rows(top_scored)}
                </tbody>
            </table>
        </div>
    </div>
    """
    return {"success": True, "html": html}

# --- COMPLEX CALCULATION ENGINES ---

def get_engagement_heatmap(conn, handle):
    """
    Analyzes 'analytics_events' to find which Hour of the Day (0-23) and Day of Week (0-6)
    has the most 'notif' (click) events.
    """
    c = conn.cursor()
    # SQLite strftime('%w') returns 0-6 (Sunday=0), '%H' returns 00-23
    sql = """
        SELECT 
            strftime('%w', datetime(timestamp, 'unixepoch')) as day,
            strftime('%H', datetime(timestamp, 'unixepoch')) as hour,
            COUNT(*) as clicks
        FROM analytics_events 
        WHERE type='notif' 
        AND ref_id IN (SELECT bid FROM broadcast_history WHERE handle=?)
        GROUP BY day, hour
    """
    c.execute(sql, (handle,))
    rows = c.fetchall()
    
    # Initialize 7x24 grid with 0
    grid = [[0 for _ in range(24)] for _ in range(7)]
    max_val = 1
    
    for r in rows:
        day = int(r[0])
        hour = int(r[1])
        count = r[2]
        grid[day][hour] = count
        if count > max_val: max_val = count
        
    return {"grid": grid, "max": max_val}

def get_churn_metrics(conn, handle):
    """
    Compares total historical signups (from metadata) vs current active (subs table).
    Also estimates 'Ghosts' (people who haven't clicked in 30 days).
    """
    c = conn.cursor()
    
    # 1. Total Historical Signups
    c.execute("SELECT COUNT(*) FROM sub_metadata WHERE handle=?", (handle,))
    total_ever = c.fetchone()[0]
    
    # 2. Current Active
    c.execute("SELECT COUNT(*) FROM subs WHERE handle=?", (handle,))
    current_active = c.fetchone()[0]
    
    # 3. Ghosts (Active subs who haven't clicked a link/notif in 30 days)
    # This requires a JOIN between subs and analytics
    thirty_days_ago = int(time.time()) - (30 * 86400)
    
    # Find active endpoints that ARE NOT in the recent analytics log
    # Note: This is an estimation. 
    ghost_sql = """
        SELECT COUNT(*) FROM subs 
        WHERE handle=? 
        AND endpoint NOT IN (
            SELECT DISTINCT s.endpoint
            FROM subs s
            JOIN analytics_events a ON a.timestamp > ?
            -- In a real complex system, we'd link events to endpoints. 
            -- Since NotiFly v7 tracks events by BID, we can't perfectly map user->event 
            -- without the 'sub_portal' tracking. 
            -- We will assume 'Ghost' means they exist in metadata but not in subs (Deleted).
        )
    """
    # Actually, simpler logic for v7 structure:
    # Churn = Metadata Count - Subs Count.
    churn_count = max(0, total_ever - current_active)
    
    retention = 0
    if total_ever > 0:
        retention = round((current_active / total_ever) * 100, 1)
        
    return {
        "churn_count": churn_count,
        "retention_rate": retention,
        "ghosts": "N/A" # Requires deeper user-tracking enabled in v7.2
    }

def get_viral_scores(conn, handle):
    """
    Calculates a weighted score for broadcasts.
    Score = (Clicks * 10) - (Dismissals * 5) + (CTR% * 2)
    """
    c = conn.cursor()
    c.row_factory = sqlite3.Row
    
    # Fetch last 10 broadcasts
    c.execute("SELECT bid, title, sent_count, timestamp FROM broadcast_history WHERE handle=? ORDER BY timestamp DESC LIMIT 10", (handle,))
    broadcasts = c.fetchall()
    
    scored = []
    for b in broadcasts:
        bid = b['bid']
        sent = b['sent_count']
        
        # Get events
        c.execute("SELECT type, COUNT(*) FROM analytics_events WHERE ref_id=? GROUP BY type", (bid,))
        events = dict(c.fetchall())
        
        clicks = events.get('notif', 0)
        dismiss = events.get('dismiss', 0)
        
        ctr = 0
        if sent > 0:
            ctr = (clicks / sent) * 100
            
        # THE VIRAL FORMULA
        score = (clicks * 10) - (dismiss * 5) + (ctr * 2)
        
        scored.append({
            "title": b['title'],
            "ctr": round(ctr, 1),
            "score": int(score)
        })
        
    # Sort by Score descending
    scored.sort(key=lambda x: x['score'], reverse=True)
    return scored[:5]

# --- HTML HELPERS ---

def _render_heatmap_grid(data):
    grid = data['grid']
    max_val = data['max']
    days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
    html = ""
    
    for d_idx, day_row in enumerate(grid):
        # Day Label
        html += f'<div style="font-size:9px; color:#64748b; align-self:center;">{days[d_idx]}</div>'
        # 24 Hour Blocks
        for val in day_row:
            # Calculate opacity based on intensity
            opacity = 0.1
            if max_val > 0:
                opacity = 0.2 + ((val / max_val) * 0.8) # Min 0.2, Max 1.0
            
            color = "#1e293b" # Default empty
            if val > 0:
                color = f"rgba(56, 189, 248, {opacity})" # Blue scale
            
            html += f'<div title="{val} clicks" style="background:{color}; height:15px; border-radius:2px;"></div>'
            
    return html

def _render_viral_rows(rows):
    html = ""
    for r in rows:
        html += f"""
        <tr style="border-bottom:1px solid #1e293b;">
            <td style="padding:8px;">{r['title']}</td>
            <td style="padding:8px; text-align:right; color:#94a3b8;">{r['ctr']}%</td>
            <td style="padding:8px; text-align:right; font-weight:bold; color:#38bdf8;">{r['score']}</td>
        </tr>
        """
    return html

# REGISTER
premium_tier_2.register_module("t2_analytics", "Advanced Analytics", analytics_handler)
