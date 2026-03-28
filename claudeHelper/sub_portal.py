"""
Subscriber Portal Module (Channel Specific)
Allows anonymous subscribers to create a unique profile per channel.
"""
import sqlite3
import json
import time

def init_db(cursor):
    """Creates the table to store subscriber identities per channel."""
    # We use a composite primary key (endpoint + handle) so one user can have different bios for different channels
    cursor.execute("""CREATE TABLE IF NOT EXISTS channel_subscriber_profiles (
        endpoint TEXT,
        handle TEXT,
        username TEXT,
        bio TEXT,
        updated_at INTEGER,
        PRIMARY KEY (endpoint, handle)
    )""")

def get_profile(db, endpoint, handle):
    """Fetches the profile for a specific endpoint on a specific channel."""
    if not handle: return {"username": "", "bio": ""}
    
    row = db.query("SELECT username, bio FROM channel_subscriber_profiles WHERE endpoint = ? AND handle = ?", 
                   (endpoint, handle), one=True)
    if row:
        return {"username": row['username'], "bio": row['bio']}
    return {"username": "", "bio": ""}

def update_profile(db, data):
    """Updates or Creates a subscriber profile for a specific channel."""
    endpoint = data.get('endpoint')
    handle = data.get('handle')
    username = data.get('username')
    bio = data.get('bio', '')

    if not endpoint or not handle or not username:
        return {"success": False, "msg": "Username and Handle are required."}

    # Sanitize
    username = username.strip()[:50]
    bio = bio.strip()[:200]

    try:
        db.execute("""INSERT OR REPLACE INTO channel_subscriber_profiles 
            (endpoint, handle, username, bio, updated_at) 
            VALUES (?, ?, ?, ?, ?)""", 
            (endpoint, handle, username, bio, int(time.time())))
        return {"success": True, "msg": "Profile Saved for " + handle + "!"}
    except Exception as e:
        return {"success": False, "msg": f"Database Error: {e}"}

def render_portal_page(handle):
    """Renders the Portal HTML specific to the requested channel."""
    if not handle:
        return "Error: Invalid Channel Link"

    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
    <title>{handle} - Subscriber Portal</title>
    <style>
        :root {{ --bg: #111; --card: #222; --text: #eee; --primary: #eab308; --input: #333; }}
        body {{ background: var(--bg); color: var(--text); font-family: -apple-system, sans-serif; display: flex; justify-content: center; padding: 20px; }}
        .box {{ width: 100%; max-width: 400px; background: var(--card); padding: 30px; border-radius: 15px; border: 1px solid #333; text-align: center; }}
        h1 {{ color: var(--primary); margin-top: 0; font-size: 22px; }}
        h2 {{ font-size: 14px; color: #888; margin-top: -10px; margin-bottom: 20px; font-weight: normal; }}
        input, textarea {{ width: 100%; padding: 12px; margin: 10px 0; background: var(--input); color: white; border: none; border-radius: 8px; box-sizing: border-box; }}
        button {{ width: 100%; padding: 12px; background: var(--primary); color: black; font-weight: bold; border: none; border-radius: 8px; cursor: pointer; margin-top: 10px; }}
        .avatar {{ width: 80px; height: 80px; background: #333; border-radius: 50%; margin: 0 auto 20px; display: flex; align-items: center; justify-content: center; font-size: 30px; border: 2px solid var(--primary); overflow:hidden; }}
        .avatar img {{ width:100%; height:100%; object-fit:cover; }}
        .status {{ margin-top: 15px; font-size: 13px; min-height: 20px; }}
    </style>
</head>
<body>
    <div class="box">
        <div class="avatar">
            <img src="/avatar/{handle}" onerror="this.style.display='none';this.parentNode.innerText='👤'">
        </div>
        <h1>{handle}</h1>
        <h2>Subscriber Profile</h2>
        
        <div id="loading">Connecting to Secure Storage...</div>
        
        <div id="form" style="display:none">
            <label style="display:block;text-align:left;font-size:12px;color:#888">DISPLAY NAME (REQUIRED)</label>
            <input id="u_name" placeholder="How you want to be seen..." maxlength="30">
            
            <label style="display:block;text-align:left;font-size:12px;color:#888">BIO (OPTIONAL)</label>
            <textarea id="u_bio" rows="3" placeholder="A bit about you..." maxlength="150"></textarea>
            
            <button onclick="saveProfile()">UPDATE PROFILE</button>
        </div>
        
        <div id="msg" class="status"></div>
        <button onclick="location.href='/c/{handle}'" style="background:#333; color:#fff; margin-top:20px">Back to Channel</button>
    </div>

    <script>
    const TARGET_HANDLE = "{handle}";

    async function init() {{
        if (!('serviceWorker' in navigator)) {{
            return document.getElementById('loading').innerText = "Not supported on this device.";
        }}
        
        const reg = await navigator.serviceWorker.ready;
        const sub = await reg.pushManager.getSubscription();
        
        if (!sub) {{
            document.getElementById('loading').innerHTML = "You are not subscribed to " + TARGET_HANDLE + "!<br><a href='/c/" + TARGET_HANDLE + "' style='color:#eab308'>Go back and subscribe.</a>";
            return;
        }}

        // Fetch existing profile FOR THIS CHANNEL
        try {{
            const r = await fetch('/api/portal/get', {{
                method: 'POST',
                body: JSON.stringify({{endpoint: sub.endpoint, handle: TARGET_HANDLE}})
            }});
            const data = await r.json();
            
            document.getElementById('u_name').value = data.username || '';
            document.getElementById('u_bio').value = data.bio || '';
            
            document.getElementById('loading').style.display = 'none';
            document.getElementById('form').style.display = 'block';
            
            window.currentEndpoint = sub.endpoint;
        }} catch(e) {{
            document.getElementById('loading').innerText = "Connection Failed.";
        }}
    }}

    async function saveProfile() {{
        const username = document.getElementById('u_name').value;
        const bio = document.getElementById('u_bio').value;
        const msg = document.getElementById('msg');
        
        if(!username) return alert("Username is required");
        
        msg.innerText = "Saving...";
        
        const r = await fetch('/api/portal/save', {{
            method: 'POST',
            body: JSON.stringify({{
                endpoint: window.currentEndpoint,
                handle: TARGET_HANDLE,
                username: username,
                bio: bio
            }})
        }});
        const j = await r.json();
        
        msg.innerText = j.msg;
        msg.style.color = j.success ? "#4ade80" : "#f87171";
    }}

    init();
    </script>
</body>
</html>
"""
