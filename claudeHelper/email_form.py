import sqlite3
import time
import json

def init_db(cursor):
    """Creates the table for storing email leads."""
    cursor.execute("""CREATE TABLE IF NOT EXISTS email_waitlist (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        handle TEXT,
        name TEXT,
        email TEXT,
        socials TEXT,
        admin_consent INTEGER,
        timestamp INTEGER,
        FOREIGN KEY(handle) REFERENCES channels(handle) ON DELETE CASCADE
    )""")

def save_lead(conn, handle, data):
    """Saves a new lead to the database."""
    try:
        cursor = conn.cursor()
        # Basic Validation
        if not data.get('email') or '@' not in data.get('email'):
            return {"success": False, "msg": "Invalid Email"}
            
        cursor.execute("""INSERT INTO email_waitlist 
            (handle, name, email, socials, admin_consent, timestamp) 
            VALUES (?, ?, ?, ?, ?, ?)""", 
            (handle, data.get('name'), data.get('email'), data.get('socials'), 
             1 if data.get('consent') else 0, int(time.time())))
        conn.commit()
        return {"success": True, "msg": "You're on the list! 🚀"}
    except Exception as e:
        return {"success": False, "msg": f"Error: {str(e)}"}

def get_leads_csv(conn, handle):
    """Exports leads for a specific channel as CSV string."""
    cursor = conn.cursor()
    cursor.execute("SELECT name, email, socials, admin_consent, timestamp FROM email_waitlist WHERE handle=? ORDER BY timestamp DESC", (handle,))
    rows = cursor.fetchall()
    
    csv_data = "Name,Email,Socials,Consent,Date\n"
    for r in rows:
        date_str = time.strftime('%Y-%m-%d %H:%M', time.localtime(r[4]))
        # sanitize CSV fields
        name = str(r[0]).replace(',', ' ')
        email = str(r[1]).replace(',', ' ')
        social = str(r[2]).replace(',', ' ')
        consent = "YES" if r[3] else "NO"
        csv_data += f"{name},{email},{social},{consent},{date_str}\n"
    
    return csv_data

def render_modal(handle):
    """Returns the HTML, CSS, and JS for the Waitlist Button and Modal."""
    return f"""
    <div style="width:100%; display:flex; justify-content:center; margin-top:20px;">
        <button onclick="openWaitlist()" class="waitlist-trigger">
            ✨ Join Premium Waitlist
        </button>
    </div>

    <div id="wl_modal" class="wl-overlay" style="display:none" onclick="if(event.target===this)closeWaitlist()">
        <div class="wl-box">
            <div class="wl-close" onclick="closeWaitlist()">×</div>
            <h2 class="wl-title">Join the Inner Circle</h2>
            <p class="wl-desc">Get exclusive deals, early access to premium content, and updates directly from <b>{handle}</b>.</p>
            
            <div class="wl-form">
                <input type="text" id="wl_name" class="wl-input" placeholder="Your Name">
                <input type="email" id="wl_email" class="wl-input" placeholder="Email Address (Required)">
                <input type="text" id="wl_social" class="wl-input" placeholder="@SocialHandle (Optional)">
                
                <label class="wl-consent">
                    <input type="checkbox" id="wl_check">
                    <span>I allow Notifly and <b>{handle}</b> to email me deals, promotions, and channel information.</span>
                </label>
                
                <button onclick="submitWaitlist()" id="wl_submit" class="wl-btn">Sign Up Now</button>
            </div>
            <div id="wl_msg"></div>
        </div>
    </div>

    <style>
    /* Button Style */
    .waitlist-trigger {{
        background: linear-gradient(135deg, #FFD700 0%, #FDB931 100%);
        color: #000; border: none; padding: 14px 28px; 
        border-radius: 50px; font-weight: 800; font-size: 14px;
        cursor: pointer; text-transform: uppercase; letter-spacing: 1px;
        box-shadow: 0 4px 15px rgba(253, 185, 49, 0.4);
        transition: transform 0.2s, box-shadow 0.2s;
        width: auto; display: inline-block;
    }}
    .waitlist-trigger:hover {{ transform: translateY(-2px); box-shadow: 0 6px 20px rgba(253, 185, 49, 0.6); }}

    /* Modal Styles */
    .wl-overlay {{
        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background: rgba(0,0,0,0.85); z-index: 10000;
        display: flex; justify-content: center; align-items: center;
        backdrop-filter: blur(8px); animation: fadeIn 0.3s;
    }}
    .wl-box {{
        background: #111; width: 90%; max-width: 400px; padding: 30px;
        border-radius: 20px; border: 1px solid #333; text-align: center;
        position: relative; color: #fff;
        box-shadow: 0 20px 50px rgba(0,0,0,0.7);
        font-family: sans-serif;
    }}
    .wl-close {{
        position: absolute; top: 15px; right: 20px; font-size: 28px;
        cursor: pointer; color: #666; line-height: 1;
    }}
    .wl-close:hover {{ color: #fff; }}
    .wl-title {{ margin: 0 0 10px 0; color: #FFD700; font-size: 22px; }}
    .wl-desc {{ color: #aaa; font-size: 13px; margin-bottom: 25px; line-height: 1.5; }}
    
    .wl-input {{
        width: 100%; padding: 14px; margin-bottom: 12px;
        background: #222; border: 1px solid #333; color: #fff;
        border-radius: 8px; font-size: 14px; box-sizing: border-box;
    }}
    .wl-input:focus {{ outline: none; border-color: #FFD700; background: #000; }}
    
    .wl-consent {{
        display: flex; align-items: start; gap: 10px; text-align: left;
        font-size: 11px; color: #888; margin: 15px 0 20px 0;
        cursor: pointer;
    }}
    .wl-consent input {{ margin-top: 2px; accent-color: #FFD700; }}
    .wl-consent span b {{ color: #ccc; }}
    
    .wl-btn {{
        width: 100%; padding: 14px; background: #FFD700; color: #000;
        border: none; border-radius: 8px; font-weight: bold; font-size: 16px;
        cursor: pointer; transition: 0.2s;
    }}
    .wl-btn:hover {{ background: #fff; }}
    .wl-btn:disabled {{ background: #555; color: #888; cursor: not-allowed; }}
    
    #wl_msg {{ margin-top: 15px; font-size: 13px; font-weight: bold; min-height: 20px; }}
    </style>

    <script>
    function openWaitlist() {{ document.getElementById('wl_modal').style.display = 'flex'; }}
    function closeWaitlist() {{ document.getElementById('wl_modal').style.display = 'none'; }}
    
    async function submitWaitlist() {{
        const btn = document.getElementById('wl_submit');
        const msg = document.getElementById('wl_msg');
        
        const name = document.getElementById('wl_name').value;
        const email = document.getElementById('wl_email').value;
        const socials = document.getElementById('wl_social').value;
        const consent = document.getElementById('wl_check').checked;
        
        if(!email) {{ 
            msg.innerText = "Please enter your email address."; 
            msg.style.color = "#f87171"; 
            return; 
        }}
        
        btn.disabled = true; 
        btn.innerText = "Joining...";
        msg.innerText = "";
        
        try {{
            const r = await fetch('/api/waitlist/{handle}', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{name, email, socials, consent}})
            }});
            const j = await r.json();
            
            msg.innerText = j.msg;
            msg.style.color = j.success ? "#4ade80" : "#f87171";
            
            if(j.success) {{
                btn.innerText = "Joined!";
                setTimeout(closeWaitlist, 2500);
                document.querySelector('.waitlist-trigger').innerText = "You're on the list! ✓";
                document.querySelector('.waitlist-trigger').disabled = true;
                document.querySelector('.waitlist-trigger').style.background = "#333";
                document.querySelector('.waitlist-trigger').style.color = "#fff";
                document.querySelector('.waitlist-trigger').style.boxShadow = "none";
            }} else {{
                btn.disabled = false; 
                btn.innerText = "Try Again";
            }}
        }} catch(e) {{
            console.error(e);
            msg.innerText = "Connection Error";
            msg.style.color = "#f87171";
            btn.disabled = false;
            btn.innerText = "Sign Up Now";
        }}
    }}
    </script>
    """
