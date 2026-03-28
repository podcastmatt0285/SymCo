"""
Tool: Tawk.to Manager
Description: Inject custom Tawk.to chat widgets per channel.
"""
import sqlite3
import json

META = {
    "name": "Live Chat (Tawk.to)",
    "icon": "💬",
    "desc": "Add your own Tawk.to widget to your page."
}

# --- Database & Admin Logic ---
def run(conn, handle, payload):
    action = payload.get('sub_action')
    
    # Ensure table exists
    conn.execute("CREATE TABLE IF NOT EXISTS channel_tawk (handle TEXT PRIMARY KEY, tawk_id TEXT)")

    if action == 'save':
        tid = payload.get('tawk_id', '').strip()
        conn.execute("INSERT OR REPLACE INTO channel_tawk (handle, tawk_id) VALUES (?, ?)", (handle, tid))
        conn.commit()
        return {"success": True, "reload": True}

    # Render Admin UI
    curr = conn.execute("SELECT tawk_id FROM channel_tawk WHERE handle=?", (handle,)).fetchone()
    curr_id = curr[0] if curr else ""

    html = f"""
    <div style="background:#1a1a1a; padding:15px; border-radius:8px; border:1px solid #333;">
        <h3 style="color:#eab308; margin-top:0;">💬 Tawk.to Chat</h3>
        <p style="font-size:12px; color:#aaa;">Enter your <b>Property ID</b> (e.g. <code>6954.../default</code>) below.</p>
        <input id="t_id" value="{curr_id}" placeholder="6954xxxx/default" style="width:100%; background:#000; color:#fff; padding:10px; border:1px solid #333; margin-bottom:10px;">
        <button onclick="saveTawk()" style="width:100%; background:#eab308; color:#000; font-weight:bold; padding:10px; border:none; cursor:pointer;">SAVE WIDGET</button>
    </div>
    <script>
    async function saveTawk() {{
        const tid = document.getElementById('t_id').value;
        const btn = document.querySelector('button[onclick="saveTawk()"]');
        btn.innerText = "Saving...";
        
        try {{
            const r = await fetch('/api/tier2/exec/toolbox/' + handle, {{
                method: 'POST',
                body: JSON.stringify({{ pin: pin, action: 'exec_tool', payload: {{ tool_id: 'tawk', data: {{ sub_action: 'save', tawk_id: tid }} }} }})
            }});
            const j = await r.json();
            if(j.success) {{
                location.reload(); 
            }} else {{
                alert("Error: " + (j.msg || "Unknown error"));
                btn.innerText = "SAVE WIDGET";
            }}
        }} catch(e) {{
            alert("Connection failed");
            btn.innerText = "SAVE WIDGET";
        }}
    }}
    </script>
    """
    return {"success": True, "html": html}

# --- Public Render Logic (Called by app.py) ---
def render_public(conn, handle):
    try:
        row = conn.execute("SELECT tawk_id FROM channel_tawk WHERE handle=?", (handle,)).fetchone()
        if row and row[0]:
            return f"""
            <script type="text/javascript">
            var Tawk_API=Tawk_API||{{}}, Tawk_LoadStart=new Date();
            (function(){{
            var s1=document.createElement("script"),s0=document.getElementsByTagName("script")[0];
            s1.async=true;
            s1.src='https://embed.tawk.to/{row[0]}';
            s1.charset='UTF-8';
            s1.setAttribute('crossorigin','*');
            s0.parentNode.insertBefore(s1,s0);
            }})();
            </script>
            """
    except: pass
    return ""
