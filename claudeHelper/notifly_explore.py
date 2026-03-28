import re

# --- EXPLORE LOGIC & RENDERING ---

def search_channels(db, tag, page=0):
    """Searches the database for bios containing the tag, checking for Gate status."""
    limit = 10
    offset = page * limit
    query = f"%#{tag}%"
    
    # Left Join to check gate status in one go
    sql = """
        SELECT c.handle, c.bio, g.enabled 
        FROM channels c 
        LEFT JOIN channel_gates g ON c.handle = g.handle 
        WHERE c.bio LIKE ? 
        LIMIT ? OFFSET ?
    """
    
    rows = db.query(sql, (query, limit, offset))
    
    results = []
    for r in rows:
        is_gated = True if (r['enabled'] and r['enabled'] == 1) else False
        
        results.append({
            "handle": r['handle'],
            "bio": r['bio'],
            "is_gated": is_gated,
            "bio_html": linkify_hashtags(r['bio'])
        })
    return results

def linkify_hashtags(text):
    """Converts #hashtags into clickable links."""
    if not text: return ""
    return re.sub(r'#(\w+)', r'<a href="/explore/\1">#\1</a>', text)

def render(tag, page, db, vapid_key):
    """Renders the Explore Page HTML with Client-Side Age Gating."""
    results = search_channels(db, tag, page)
    
    cards_html = ""
    for res in results:
        h = res['handle']
        
        # --- LOGIC CHANGE ---
        # Instead of redacting content on the server, we markup the HTML 
        # so the Client (JS) can hide/show it based on verification.
        
        if res['is_gated']:
            # NSFW CARD
            card_class = "channel-card nsfw-card hidden" # Hidden by default
            # Load blurred avatar by default
            av_src = f"/avatar/{h}?blur=true"
            # Keep original bio in HTML, but it will be hidden by the container class
            bio_html = res['bio_html']
            badge = " <span class='nsfw-badge'>18+</span>"
        else:
            # SFW CARD
            card_class = "channel-card"
            av_src = f"/avatar/{h}"
            bio_html = res['bio_html']
            badge = ""

        cards_html += f"""
        <div class="{card_class}" data-handle="{h}">
            <div class="cc-head">
                <img src="{av_src}" onerror="this.src='/icon.svg'" class="cc-av">
                <div class="cc-info">
                    <div class="cc-name">{h}{badge}</div>
                    <div class="cc-bio">{bio_html}</div>
                </div>
            </div>
            <div class="cc-actions">
                <a href="/c/{h}" class="cc-btn">Visit Page</a>
                <button class="cc-btn sub-btn" onclick="directSub(this, '{h}')">Subscribe +</button>
            </div>
        </div>"""
    
    if not results:
        cards_html = f'<div style="text-align:center;color:#666;margin-top:50px">No channels found discussing <b>#{tag}</b>.<br><br><a href="/">Go Home</a></div>'

    prev_link = f'<a href="/explore/{tag}?p={page-1}" class="link-btn">« Prev</a>' if page > 0 else ''
    next_link = f'<a href="/explore/{tag}?p={page+1}" class="link-btn">Next »</a>' if len(results) == 10 else ''

    css = """
    :root{--bg:#111;--card:#222;--text:#eee;--primary:#eab308;--input:#333}
    body{background:var(--bg);color:var(--text);font-family:-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;margin:0;padding:20px;display:flex;justify-content:center}
    a{color:var(--primary);text-decoration:none}
    .box{width:100%;max-width:500px}
    h1{color:var(--primary);margin:0 0 5px 0}
    .sub-head{color:#888;font-size:14px;margin-bottom:20px}
    
    .channel-card { background:#1a1a1a; border:1px solid #333; border-radius:12px; padding:15px; margin-bottom:15px; animation:fadeIn 0.5s; }
    
    /* NSFW Logic */
    .nsfw-card.hidden { display:none; } /* Completely hide unverified content */
    .nsfw-badge { font-size:10px; color:#f87171; border:1px solid #f87171; padding:1px 3px; border-radius:3px; margin-left:5px; }
    
    .cc-head { display:flex; gap:15px; align-items:start; }
    .cc-av { width:50px; height:50px; border-radius:50%; object-fit:cover; border:2px solid var(--primary); background:#000; }
    .cc-name { font-size:18px; font-weight:bold; color:#fff; margin-bottom:4px; }
    .cc-bio { font-size:13px; color:#ccc; line-height:1.4; word-break:break-word; }
    .cc-actions { margin-top:15px; display:flex; gap:10px; }
    .cc-btn { flex:1; padding:10px; text-align:center; background:#333; color:white; border-radius:8px; font-size:12px; border:1px solid #444; cursor:pointer; transition:0.2s; }
    .sub-btn { background:var(--primary); color:black; font-weight:bold; border:none; }
    .sub-btn:hover { opacity:0.9; }
    .link-btn { padding:10px 20px; background:#333; border-radius:20px; color:#fff; font-size:12px; border:1px solid #444; }
    
    /* Controls */
    .top-controls { display:flex; justify-content:space-between; align-items:center; margin-bottom:15px; }
    .safe-toggle { background:none; border:1px solid #444; color:#888; padding:5px 12px; border-radius:20px; font-size:11px; cursor:pointer; }
    .safe-toggle.active { border-color:#f87171; color:#f87171; font-weight:bold; }
    
    @keyframes fadeIn { from { opacity:0; transform:translateY(10px); } to { opacity:1; transform:translateY(0); } }
    """

    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
    <title>#{tag} - NotiFly Explore</title>
    <style>{css}</style>
</head>
<body>
    <div class="box">
        <div class="top-controls">
            <h1>#{tag}</h1>
            <button id="toggleBtn" class="safe-toggle" onclick="toggleSafety()">🔞 Show 18+</button>
        </div>
        
        <div class="sub-head">Discovery Mesh</div>
        
        <div id="results">{cards_html}</div>
        
        <div style="display:flex;justify-content:center;gap:10px;margin-top:20px">{prev_link}{next_link}</div>
        <div style="text-align:center;margin-top:30px"><a href="/" style="font-size:12px;color:#666">Back to Home</a></div>
    </div>
    <script>
    const VAPID="{vapid_key}";
    const KEY_VERIFIED = "notifly_global_18_verified";

    // 1. Check Verification on Load
    function checkAge() {{
        const isVerified = localStorage.getItem(KEY_VERIFIED) === 'true';
        updateUI(isVerified);
    }}

    // 2. Update UI based on status
    function updateUI(verified) {{
        const nsfwCards = document.querySelectorAll('.nsfw-card');
        const btn = document.getElementById('toggleBtn');
        
        if (verified) {{
            // SHOW CONTENT
            nsfwCards.forEach(c => {{
                c.classList.remove('hidden');
                // Optional: Swap avatar to high-res unblurred version if you want
                const img = c.querySelector('img');
                const handle = c.getAttribute('data-handle');
                if(img && handle) img.src = '/avatar/' + handle; 
            }});
            
            btn.classList.add('active');
            btn.innerText = "🔞 18+ Visible";
            // Change action to hide?
            btn.onclick = function() {{
                 localStorage.removeItem(KEY_VERIFIED);
                 location.reload();
            }};
        }} else {{
            // HIDE CONTENT (Default CSS handles display:none, but ensure here)
            nsfwCards.forEach(c => c.classList.add('hidden'));
            
            btn.classList.remove('active');
            btn.innerText = "🔞 Show 18+";
            btn.onclick = toggleSafety;
        }}
    }}

    // 3. Trigger Age Gate
    function toggleSafety() {{
        // Create Overlay (Same style as nsfw_gate.py)
        const ov = document.createElement('div');
        ov.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:#000;z-index:999999;display:flex;flex-direction:column;justify-content:center;align-items:center;padding:20px;box-sizing:border-box;font-family:sans-serif;text-align:center;';
        
        const h = document.createElement('h1');
        h.innerText = 'AGE RESTRICTED';
        h.style.cssText = 'color:#eab308;margin:0 0 10px 0;font-size:24px;text-transform:uppercase;letter-spacing:2px;';
        
        const p = document.createElement('p');
        p.innerText = 'This section may contain content intended for adults only. You must be 18+ to view.';
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
            localStorage.setItem(KEY_VERIFIED, 'true');
            ov.remove();
            checkAge(); // Reveal content immediately
        }};
        
        btnNo.onclick = function() {{
            ov.remove();
        }};
        
        ov.appendChild(h);
        ov.appendChild(p);
        btnBox.appendChild(btnNo);
        btnBox.appendChild(btnYes);
        ov.appendChild(btnBox);
        document.body.appendChild(ov);
    }}

    // --- Subscription Logic (Existing) ---
    function urlB64ToUint8Array(base64String){{
        const padding='='.repeat((4-base64String.length%4)%4);
        const base64=(base64String+padding).replace(/\\-/g,'+').replace(/_/g,'/');
        const rawData=window.atob(base64);
        const outputArray=new Uint8Array(rawData.length);
        for(let i=0;i<rawData.length;++i)outputArray[i]=rawData.charCodeAt(i);
        return outputArray;
    }}
    
    async function directSub(btn, handle) {{
        // ... (Existing Sub Logic kept identical) ...
        const originalText = btn.innerText;
        btn.innerText = "...";
        btn.disabled = true;
        try {{
            if(!('serviceWorker' in navigator)) return alert("Not supported");
            const swReg = await navigator.serviceWorker.register('/sw.js');
            let sub = await swReg.pushManager.getSubscription();
            if(!sub) {{
                sub = await swReg.pushManager.subscribe({{
                    userVisibleOnly: true,
                    applicationServerKey: urlB64ToUint8Array(VAPID)
                }});
            }}
            const v = await fetch('/api/verify_sub/'+handle, {{
                method: 'POST', body: JSON.stringify({{endpoint: sub.endpoint}})
            }});
            const vData = await v.json();
            if(vData.subscribed) {{
                if(confirm("Unsubscribe from " + handle + "?")) {{
                    await fetch('/api/sub/'+handle, {{method:'DELETE', body:JSON.stringify({{endpoint:sub.endpoint}})}});
                    btn.innerText = "Subscribe +";
                    btn.style.background = "var(--primary)";
                }} else {{ btn.innerText = "Subscribed ✓"; }}
            }} else {{
                await fetch('/api/sub/'+handle, {{method:'POST', body:JSON.stringify(sub)}});
                btn.innerText = "Subscribed ✓";
                btn.style.background = "#4ade80"; 
            }}
        }} catch(e) {{
            console.error(e);
            alert("Error: " + e);
            btn.innerText = "Error";
        }} finally {{ btn.disabled = false; }}
    }}
    
    // Init
    checkAge();
    </script>
</body>
</html>"""
