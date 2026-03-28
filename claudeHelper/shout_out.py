"""
Shout-Out Module for NotiFly Tier 2
Allows Tier 2 Admins to cross-promote other Tier 2 channels via a slider on their subscribe page.
"""
import sqlite3
import time
import json

# --- DATABASE INIT ---
def init_db(conn):
    """Creates the table to track who is shouting out whom."""
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS tier2_shoutouts (
        source_handle TEXT,
        target_handle TEXT,
        created_at INTEGER,
        PRIMARY KEY (source_handle, target_handle)
    )""")
    conn.commit()

# --- LOGIC ---
def get_candidates(conn, handle):
    """
    Fetches all available Tier 2 channels (candidates) and marks 
    which ones are currently being shouted out by 'handle'.
    """
    c = conn.cursor()
    
    # 1. Get all active Tier 2 handles (excluding self)
    c.execute("SELECT handle FROM tier_2_access WHERE status='active' AND handle != ?", (handle,))
    all_t2 = [r[0] for r in c.fetchall()]
    
    # 2. Get handles currently shouted out by this user
    c.execute("SELECT target_handle FROM tier2_shoutouts WHERE source_handle=?", (handle,))
    shouted = {r[0] for r in c.fetchall()}
    
    results = []
    for h in all_t2:
        results.append({
            "handle": h,
            "active": h in shouted
        })
    return results

def toggle_shoutout(conn, source, target, state):
    """Adds or removes a shout-out record."""
    c = conn.cursor()
    try:
        if state:
            c.execute("INSERT OR REPLACE INTO tier2_shoutouts (source_handle, target_handle, created_at) VALUES (?, ?, ?)",
                      (source, target, int(time.time())))
        else:
            c.execute("DELETE FROM tier2_shoutouts WHERE source_handle=? AND target_handle=?", (source, target))
        conn.commit()
        return {"success": True, "msg": "Saved!"}
    except Exception as e:
        return {"success": False, "msg": str(e)}

# --- UI RENDERERS ---

def render_admin_modal(conn, handle):
    """
    Renders the HTML for the Admin Dashboard Modal.
    Lists all Tier 2 admins with toggle switches.
    """
    candidates = get_candidates(conn, handle)
    c = conn.cursor()
    
    rows = ""
    for cand in candidates:
        is_checked = "checked" if cand['active'] else ""
        target = cand['handle']
        
        # Check Gate Status for Admin View (Optional, but good for safety)
        c.execute("SELECT enabled FROM channel_gates WHERE handle=?", (target,))
        row = c.fetchone()
        is_gated = bool(row and row[0])
        blur_style = "filter: blur(5px);" if is_gated else ""
        warn_badge = "<span style='color:#f87171;font-weight:bold;font-size:10px;margin-left:5px'>(18+)</span>" if is_gated else ""
        
        # This JS runs immediately when the switch is clicked.
        js_logic = (
            f"fetch('/api/tier2/exec/shout_out/{handle}', {{"
            f"method:'POST',"
            f"headers:{{'Content-Type':'application/json'}},"
            f"body:JSON.stringify({{pin:pin, action:'toggle', payload:{{target:'{target}', state:this.checked}}}})"
            f"}}).then(r=>r.json()).then(d=>{{if(!d.success){{alert(d.msg);this.checked=!this.checked}}}}).catch(e=>{{alert('Save Failed');this.checked=!this.checked}})"
        )
        
        rows += f"""
        <div class="so-row">
            <div class="so-info">
                <img src="/avatar/{target}" style="{blur_style}" onerror="this.src='https://cdn-icons-png.flaticon.com/512/1156/1156948.png'">
                <div>
                    <div class="so-h">{target} {warn_badge}</div>
                    <div class="so-sub">Tier 2 Elite</div>
                </div>
            </div>
            <label class="switch">
                <input type="checkbox" {is_checked} onchange="{js_logic}">
                <span class="slider round"></span>
            </label>
        </div>
        """
        
    if not rows:
        rows = "<div style='text-align:center; color:#666; padding:20px; font-style:italic'>No other Tier 2 channels found yet.</div>"

    return f"""
    <div id="shoutout_modal" class="modal-overlay">
        <div class="modal-box">
            <div class="modal-header">
                <h2>📢 SHOUT-OUT BOARD</h2>
                <button onclick="document.getElementById('shoutout_modal').remove()">×</button>
            </div>
            <p style="font-size:12px; color:#888; margin-bottom:15px">
                Toggle switches to feature these Elite channels on your subscribe page.
            </p>
            <div class="so-list">
                {rows}
            </div>
        </div>
        <style>
            .modal-overlay {{ position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.85); z-index:10000; display:flex; align-items:center; justify-content:center; animation: fadeIn 0.2s; }}
            .modal-box {{ background:#111; width:90%; max-width:400px; border:1px solid #eab308; border-radius:12px; padding:20px; max-height:80vh; overflow-y:auto; box-shadow: 0 0 20px rgba(234, 179, 8, 0.2); }}
            .modal-header {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; border-bottom:1px solid #333; padding-bottom:10px; }}
            .modal-header h2 {{ margin:0; color:#eab308; font-size:16px; letter-spacing:1px; }}
            .modal-header button {{ background:none; border:none; color:#fff; font-size:24px; cursor:pointer; }}
            .so-list {{ display:flex; flex-direction:column; gap:10px; }}
            .so-row {{ display:flex; justify-content:space-between; align-items:center; background:#1a1a1a; padding:10px; border-radius:8px; border:1px solid #333; }}
            .so-info {{ display:flex; align-items:center; gap:10px; }}
            .so-info img {{ width:36px; height:36px; border-radius:50%; object-fit:cover; border:1px solid #444; }}
            .so-h {{ font-weight:bold; color:#fff; font-size:13px; display:flex; align-items:center; }}
            .so-sub {{ font-size:10px; color:#eab308; }}
        </style>
    </div>
    """

def render_public_slider(conn, handle):
    """
    Renders the HTML for the Public Subscribe Page Slider.
    """
    c = conn.cursor()
    c.execute("SELECT target_handle FROM tier2_shoutouts WHERE source_handle=?", (handle,))
    targets = [r[0] for r in c.fetchall()]
    
    if not targets: return ""
    
    slides = ""
    for t in targets:
        # --- NSF GATING FIX ---
        # We check the 'channel_gates' table directly since we have the connection
        c.execute("SELECT enabled FROM channel_gates WHERE handle=?", (t,))
        row = c.fetchone()
        is_gated = bool(row and row[0])
        
        # If gated, apply a blur filter to the container
        blur_style = "filter: blur(10px);" if is_gated else ""
        # ----------------------
        
        slides += f"""
        <a href="/c/{t}" class="so-slide" target="_blank">
            <div class="so-img-wrap" style="{blur_style}">
                <img src="/avatar/{t}" onerror="this.src='https://cdn-icons-png.flaticon.com/512/1156/1156948.png'">
            </div>
            <div class="so-name">{t}</div>
            <div class="so-badge">SHOUT OUT</div>
        </a>
        """

    return f"""
    <style>
    .so-wrapper {{ margin: 25px 0; border-top: 1px dashed #333; padding-top: 15px; width:100%; overflow:hidden; }}
    .so-head {{ color: #eab308; font-size: 11px; font-weight: bold; margin-bottom: 12px; letter-spacing: 1px; text-transform: uppercase; display:flex; align-items:center; gap:5px; }}
    .so-track {{ display: flex; gap: 12px; overflow-x: auto; padding-bottom: 5px; scrollbar-width: none; -webkit-overflow-scrolling: touch; }}
    .so-track::-webkit-scrollbar {{ display: none; }}
    .so-slide {{ min-width: 70px; width: 70px; text-decoration: none; display: flex; flex-direction: column; align-items: center; cursor: pointer; transition: transform 0.2s; }}
    .so-slide:hover {{ transform: translateY(-3px); }}
    .so-img-wrap {{ width: 50px; height: 50px; padding: 2px; border: 1px solid #eab308; border-radius: 50%; display:flex; align-items:center; justify-content:center; margin-bottom:6px; background: #000; overflow: hidden; }}
    .so-img-wrap img {{ width: 100%; height: 100%; border-radius: 50%; object-fit: cover; }}
    .so-name {{ color: #eee; font-size: 10px; font-weight: bold; width: 100%; text-align: center; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
    .so-badge {{ font-size: 7px; color: #000; background: #eab308; padding: 1px 3px; border-radius: 3px; margin-top: 2px; font-weight: 800; }}
    </style>
    
    <div class="so-wrapper">
        <div class="so-head">⚡ VIP Shout-Outs</div>
        <div class="so-track">
            {slides}
        </div>
    </div>
    """

# --- GATEWAY ENTRY POINT ---
def entry_point(conn, handle, action, payload):
    """
    Called by premium_tier_2.py's execute_module function.
    """
    if action == 'render_admin':
        return {"success": True, "html": render_admin_modal(conn, handle)}
    
    elif action == 'toggle':
        return toggle_shoutout(conn, handle, payload.get('target'), payload.get('state'))
        
    elif action == 'render_public':
        return {"success": True, "html": render_public_slider(conn, handle)}

    return {"success": False, "msg": "Unknown action"}
