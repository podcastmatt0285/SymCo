import sqlite3
import re
from urllib.parse import urlparse

def init_db(db):
    """Ensures the NSFW table and Age Gate table exist."""
    db.execute("CREATE TABLE IF NOT EXISTS nsfw_domains (domain TEXT PRIMARY KEY)")
    db.execute("CREATE TABLE IF NOT EXISTS channel_gates (handle TEXT PRIMARY KEY, enabled INTEGER DEFAULT 0)")

def add_domain(db, domain):
    """Adds a domain to the blocklist."""
    clean = domain.lower().replace("https://", "").replace("http://", "").split('/')[0]
    try:
        db.execute("INSERT INTO nsfw_domains (domain) VALUES (?)", (clean,))
        return True
    except sqlite3.IntegrityError:
        return False

def remove_domain(db, domain):
    """Removes a domain from the blocklist."""
    db.execute("DELETE FROM nsfw_domains WHERE domain = ?", (domain,))

def get_all_domains(db):
    """Returns a list of all blocked domains."""
    rows = db.query("SELECT domain FROM nsfw_domains ORDER BY domain ASC")
    return [r['domain'] for r in rows]

def check_url(db, url):
    """Checks if a specific URL belongs to a blocked domain."""
    if not url: return False
    
    blocked_domains = get_all_domains(db)
    
    try:
        target_domain = urlparse(url).netloc.lower()
        if not target_domain: return False
        
        for blocked in blocked_domains:
            if blocked in target_domain:
                return True
    except:
        return False
    return False

def set_gate_status(db, handle, status):
    """Sets the age gate status for a channel."""
    val = 1 if status else 0
    db.execute("INSERT OR REPLACE INTO channel_gates (handle, enabled) VALUES (?, ?)", (handle, val))

def get_gate_status(db, handle):
    """Checks if age gate is enabled."""
    res = db.query("SELECT enabled FROM channel_gates WHERE handle = ?", (handle,), one=True)
    return bool(res['enabled']) if res else False

def get_css():
    """Returns the CSS needed for the blurring effect."""
    return """
    .sensitive-wrapper { position: relative; overflow: hidden; border-radius: 12px; margin-bottom: 8px; }
    .sensitive-blur { filter: blur(12px); pointer-events: none; user-select: none; opacity: 0.6; }
    .sensitive-overlay {
        position: absolute; top: 0; left: 0; width: 100%; height: 100%;
        display: flex; flex-direction: column; justify-content: center; align-items: center;
        background: rgba(0,0,0,0.7); z-index: 10; border-radius: 12px;
    }
    .sensitive-btn {
        background: #eab308; color: #000; border: none; padding: 8px 16px;
        border-radius: 20px; font-weight: bold; cursor: pointer; font-size: 12px;
        text-transform: uppercase; letter-spacing: 1px;
    }
    .sensitive-warn { font-size: 10px; color: #fff; margin-bottom: 8px; font-weight: bold; }
    """

def get_js():
    """Returns the JS needed to reveal content."""
    return """
    function reveal(id) {
        const wrapper = document.getElementById('sens_' + id);
        if(wrapper) {
            wrapper.querySelector('.sensitive-overlay').style.display = 'none';
            wrapper.querySelector('.sensitive-content').classList.remove('sensitive-blur');
        }
    }
    """

def get_gate_js(handle):
    """Returns the JS for the 18+ verification overlay."""
    return f"""
    (function() {{
        const key = 'age_verified_{handle}';
        if (!localStorage.getItem(key)) {{
            // Create Overlay
            const ov = document.createElement('div');
            ov.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:#000;z-index:999999;display:flex;flex-direction:column;justify-content:center;align-items:center;padding:20px;box-sizing:border-box;font-family:sans-serif;text-align:center;';
            
            const h = document.createElement('h1');
            h.innerText = 'AGE RESTRICTED';
            h.style.cssText = 'color:#eab308;margin:0 0 10px 0;font-size:24px;text-transform:uppercase;letter-spacing:2px;';
            
            const p = document.createElement('p');
            p.innerText = 'This channel contains content intended for adults only. You must be 18+ to enter.';
            p.style.cssText = 'color:#ccc;margin:0 0 30px 0;font-size:14px;max-width:400px;line-height:1.5;';
            
            const btnBox = document.createElement('div');
            btnBox.style.cssText = 'display:flex;gap:15px;';
            
            const btnYes = document.createElement('button');
            btnYes.innerText = 'I AM 18+';
            btnYes.style.cssText = 'background:#eab308;color:#000;border:none;padding:12px 24px;border-radius:30px;font-weight:bold;cursor:pointer;font-size:14px;';
            
            const btnNo = document.createElement('button');
            btnNo.innerText = 'EXIT';
            btnNo.style.cssText = 'background:transparent;color:#fff;border:1px solid #555;padding:12px 24px;border-radius:30px;font-weight:bold;cursor:pointer;font-size:14px;';
            
            btnYes.onclick = function() {{
                localStorage.setItem(key, 'true');
                ov.style.opacity = '0';
                setTimeout(() => ov.remove(), 300);
            }};
            
            btnNo.onclick = function() {{
                window.location.href = 'https://google.com';
            }};
            
            ov.appendChild(h);
            ov.appendChild(p);
            btnBox.appendChild(btnNo);
            btnBox.appendChild(btnYes);
            ov.appendChild(btnBox);
            
            // Transition
            ov.style.transition = 'opacity 0.3s ease';
            document.body.appendChild(ov);
            
            // Disable scrolling while locked (Doubled braces for f-string literal)
            const style = document.createElement('style');
            style.innerHTML = 'body {{ overflow: hidden !important; }}';
            document.head.appendChild(style);
            
            // Re-enable scroll on verify
            const originalClick = btnYes.onclick;
            btnYes.onclick = function() {{
                style.remove();
                originalClick();
            }};
        }}
    }})();
    """
