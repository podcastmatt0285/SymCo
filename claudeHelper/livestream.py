"""
Livestream Module for NotiFly
Handles live status, secure stream URLs, and viewer pages.
"""
import sqlite3
import random
import string
import time
import json
import html

def init_db(conn):
    c = conn.cursor()
    # Table to store active stream sessions
    c.execute("""CREATE TABLE IF NOT EXISTS streams (
        handle TEXT PRIMARY KEY,
        stream_key TEXT,
        embed_content TEXT,
        is_live INTEGER DEFAULT 0,
        started_at INTEGER
    )""")
    conn.commit()

def generate_stream_key():
    """Generates a random URL suffix."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=12))

def go_live(conn, handle, embed_code):
    """Activates the stream with a new random key."""
    c = conn.cursor()
    # Sanitize inputs strictly if needed, but here we assume admin knows what they are doing (e.g., pasting iframes)
    # Basic protection against breaking the layout
    if not embed_code.strip():
        return {"success": False, "msg": "Embed code cannot be empty."}

    stream_key = generate_stream_key()
    
    c.execute("INSERT OR REPLACE INTO streams (handle, stream_key, embed_content, is_live, started_at) VALUES (?, ?, ?, 1, ?)",
              (handle, stream_key, embed_code, int(time.time())))
    conn.commit()
    
    return {
        "success": True, 
        "stream_url": f"/c/{handle}/Livestream{stream_key}",
        "msg": "You are LIVE! Button is now visible on your profile."
    }

def go_live_direct(conn, handle):
    """Activates a direct WebRTC stream using VDO.Ninja."""
    c = conn.cursor()
    
    # Generate a unique room ID based on handle and randomness
    room_id = f"notifly_{handle}_{''.join(random.choices(string.ascii_letters + string.digits, k=6))}"
    
    # Construct VDO.Ninja URLs
    # UPDATED: Removed '&clean' and '&autostart' so the admin sees controls and setup options.
    push_url = f"https://vdo.ninja/?push={room_id}&label={handle}"
    
    # View URL: Embedded in the NotiFly viewer page (Viewers still get a clean feed)
    embed_code = f'<iframe src="https://vdo.ninja/?view={room_id}&clean&autoplay" style="width:100%;height:100%;border:none" allow="autoplay; camera; microphone; fullscreen"></iframe>'
    
    stream_key = generate_stream_key()
    
    c.execute("INSERT OR REPLACE INTO streams (handle, stream_key, embed_content, is_live, started_at) VALUES (?, ?, ?, 1, ?)",
              (handle, stream_key, embed_code, int(time.time())))
    conn.commit()
    
    return {
        "success": True, 
        "stream_url": f"/c/{handle}/Livestream{stream_key}",
        "push_url": push_url,
        "msg": "Direct Stream Active! Opening Studio..."
    }

def end_stream(conn, handle):
    """Deactivates the stream."""
    c = conn.cursor()
    c.execute("UPDATE streams SET is_live = 0 WHERE handle = ?", (handle,))
    conn.commit()
    return {"success": True, "msg": "Stream ended. Button removed from profile."}

def get_live_status(conn, handle):
    """Checks if a handle is live and returns the key."""
    c = conn.cursor()
    c.execute("SELECT stream_key, is_live FROM streams WHERE handle = ? AND is_live = 1", (handle,))
    row = c.fetchone()
    if row:
        return {"is_live": True, "key": row[0], "url": f"/c/{handle}/Livestream{row[0]}"}
    return {"is_live": False}

def render_admin_panel(conn, handle):
    """Renders the dashboard controls for streaming."""
    status = get_live_status(conn, handle)
    
    if status['is_live']:
        return f"""
        <div style="background:#2a0a0a; border:1px solid #f87171; border-radius:8px; padding:15px; margin-bottom:20px; text-align:center;">
            <div style="color:#f87171; font-weight:bold; font-size:16px; margin-bottom:10px; animation: pulse 2s infinite;">
                🔴 BROADCASTING LIVE
            </div>
            <div style="font-size:12px; color:#ccc; margin-bottom:15px;">
                Viewer Link: <a href="{status['url']}" target="_blank" style="color:#fff; text-decoration:underline;">{status['url']}</a>
            </div>
            <button onclick="stopStream()" style="background:#f87171; color:#fff; width:100%; font-weight:bold;">END STREAM</button>
        </div>
        <script>
        async function stopStream() {{
            if(!confirm('End the livestream?')) return;
            const r = await fetch('/api/stream/stop/{handle}?pin=' + pin, {{ method: 'POST' }});
            const j = await r.json();
            alert(j.msg);
            location.reload();
        }}
        </script>
        """
    else:
        return f"""
        <div style="background:#111; border:1px solid #333; border-radius:8px; padding:15px; margin-bottom:20px;">
            <div style="color:#eab308; font-weight:bold; font-size:14px; margin-bottom:5px;">
                📡 GO LIVE
            </div>
            <div style="font-size:11px; color:#888; margin-bottom:10px;">
                Paste your Embed Code (YouTube Live, Twitch, etc) below OR use the Direct Cam button.
            </div>
            <textarea id="stream_embed" rows="3" placeholder='<iframe src="https://www.youtube.com/embed/..." ...></iframe>' style="font-family:monospace; font-size:11px;"></textarea>
            <div style="display:flex; gap:5px; margin-top:5px;">
                <button onclick="startStream()" style="flex:1; background:#333; color:#eab308; border:1px solid #eab308;">USE EMBED CODE</button>
                <button onclick="startDirect()" style="flex:1; background:#eab308; color:#000; border:1px solid #eab308; font-weight:bold;">🎥 WEBCAM DIRECT</button>
            </div>
        </div>
        <script>
        async function startStream() {{
            const code = document.getElementById('stream_embed').value;
            if(!code) return alert('Enter embed code!');
            const r = await fetch('/api/stream/start/{handle}?pin=' + pin, {{ 
                method: 'POST',
                body: JSON.stringify({{embed: code}}) 
            }});
            const j = await r.json();
            if(j.success) location.reload();
            else alert(j.msg);
        }}
        async function startDirect() {{
            if(!confirm("Start a direct webcam stream? A new window will open for you to broadcast.")) return;
            
            const win = window.open('', 'NotiFly Broadcast', 'width=1280,height=720');
            if (!win) return alert("Popup blocked! Please allow popups for NotiFly.");
            
            win.document.write('<body style="background:#111;color:#eee;font-family:sans-serif;display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;"><h2>🚀 Initializing Studio...</h2><p>Connecting...</p></body>');

            try {{
                const r = await fetch('/api/stream/direct/{handle}?pin=' + pin, {{ method: 'POST' }});
                if (!r.ok) throw new Error("Server Error " + r.status);
                const j = await r.json();
                
                if(j.success) {{
                    win.location.href = j.push_url;
                    setTimeout(() => location.reload(), 1000);
                }} else {{
                    throw new Error(j.msg);
                }}
            }} catch (e) {{
                win.close();
                alert("Stream Error: " + e.message);
            }}
        }}
        </script>
        """

def render_viewer_page(conn, handle, request_path_suffix):
    """Renders the actual viewer page if the URL matches."""
    # Suffix comes in as "Livestream<RandomString>"
    # We strip "Livestream" to get the key
    key_attempt = request_path_suffix.replace("Livestream", "")
    
    c = conn.cursor()
    c.execute("SELECT embed_content, is_live FROM streams WHERE handle = ? AND stream_key = ?", (handle, key_attempt))
    row = c.fetchone()
    
    if not row or row[1] == 0:
        return None # 404 Not Found or Stream Ended
        
    embed_content = row[0]
    
    # Simple CSS for the theater mode
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
    <title>{handle} is LIVE</title>
    <style>
        body {{ background-color: #000; color: #fff; margin: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; font-family: sans-serif; }}
        .player-container {{ width: 100%; max-width: 1200px; aspect-ratio: 16/9; background: #111; position: relative; }}
        .player-container iframe {{ width: 100%; height: 100%; border: none; }}
        .header {{ width: 100%; max-width: 1200px; padding: 15px; display: flex; justify-content: space-between; align-items: center; box-sizing: border-box; }}
        .live-badge {{ background: #f87171; color: #000; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; animation: pulse 2s infinite; }}
        .back-link {{ color: #888; text-decoration: none; font-size: 14px; }}
        @keyframes pulse {{ 0% {{ opacity: 1; }} 50% {{ opacity: 0.5; }} 100% {{ opacity: 1; }} }}
    </style>
</head>
<body>
    <div class="header">
        <a href="/c/{handle}" class="back-link">← Back to {handle}</a>
        <div class="live-badge">LIVE</div>
    </div>
    <div class="player-container">
        {embed_content}
    </div>
</body>
</html>
    """
