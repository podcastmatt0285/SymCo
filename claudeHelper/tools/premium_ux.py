"""
Premium UX Manager Tool (Tier 2 Toolbox App)
Handles Premium Theme selection (Admin) and Page Rendering (Public).
"""

import json
import re
from pathlib import Path

# ==========================================================
# MODULE METADATA (Required by Toolbox)
# ==========================================================
META = {
    "name": "Premium UX",
    "icon": "🎨",
    "desc": "Apply premium visual themes"
}

# ==========================================================
# CONFIGURATION
# ==========================================================
TEMPLATES_DIR = Path("premium_ux_templates")

# ==========================================================
# DIGITAL WALLS TEMPLATE ASSETS
# ==========================================================

DIGITAL_WALLS_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;900&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body { 
    min-height: 100vh;
    background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%);
    color: #fff;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    overflow-x: hidden;
}

/* Hero Section */
.hero-section {
    position: relative;
    width: 100%;
    height: 60vh;
    min-height: 400px;
    background-size: cover;
    background-position: center;
    display: flex;
    align-items: flex-end;
    overflow: hidden;
}

.hero-section::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: linear-gradient(180deg, 
        rgba(0,0,0,0.3) 0%, 
        rgba(0,0,0,0.7) 70%,
        rgba(10,10,10,0.95) 100%
    );
    z-index: 1;
}

.hero-content {
    position: relative;
    z-index: 2;
    padding: 40px;
    width: 100%;
    max-width: 1200px;
    margin: 0 auto;
}

.profile-header {
    display: flex;
    align-items: center;
    gap: 25px;
    margin-bottom: 20px;
}

.profile-avatar {
    width: 120px;
    height: 120px;
    border-radius: 50%;
    border: 4px solid #eab308;
    box-shadow: 0 8px 32px rgba(234, 179, 8, 0.3);
    object-fit: cover;
}

.profile-info h1 {
    font-size: 3rem;
    font-weight: 900;
    margin-bottom: 8px;
    background: linear-gradient(135deg, #fff 0%, #eab308 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.profile-bio {
    font-size: 1.1rem;
    line-height: 1.6;
    color: rgba(255,255,255,0.9);
    max-width: 800px;
}

.profile-bio a {
    color: #eab308;
    text-decoration: none;
    font-weight: 600;
    transition: all 0.2s;
}

.profile-bio a:hover {
    color: #fbbf24;
    text-decoration: underline;
}

/* Content Section */
.content-section {
    max-width: 1200px;
    margin: 0 auto;
    padding: 40px 20px 80px;
}

/* Grid System */
.tiles-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 20px;
    margin-top: 30px;
}

.tile {
    position: relative;
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 16px;
    overflow: hidden;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    backdrop-filter: blur(10px);
    min-height: 140px;
    display: flex;
    align-items: center;
    justify-content: center;
    text-decoration: none;
    color: #fff;
}

.tile:hover {
    transform: translateY(-4px);
    border-color: #eab308;
    box-shadow: 0 12px 40px rgba(234, 179, 8, 0.25);
    background: rgba(234, 179, 8, 0.1);
}

.tile--wide {
    grid-column: span 2;
}

.tile--video,
.tile--embed {
    min-height: 300px;
    padding: 0;
}

.tile-content {
    padding: 30px;
    text-align: center;
    width: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
}

.tile-icon {
    width: 48px;
    height: 48px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 32px;
}

.tile-icon img {
    width: 40px;
    height: 40px;
    object-fit: contain;
    border-radius: 8px;
}

.tile-label {
    font-size: 1.1rem;
    font-weight: 700;
    color: #fff;
    text-shadow: 0 2px 10px rgba(0,0,0,0.5);
}

/* Embeds */
.embed-wrapper {
    position: relative;
    width: 100%;
    height: 100%;
    min-height: 300px;
}

.embed-wrapper iframe {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    border: none;
    border-radius: 16px;
}

.embed-label {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    padding: 15px;
    background: linear-gradient(0deg, rgba(0,0,0,0.9) 0%, transparent 100%);
    font-weight: 600;
    font-size: 0.95rem;
}

/* Premium Gallery */
.prem-gallery { 
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
    margin: 20px 0;
}

.prem-item { 
    aspect-ratio: 1;
    border-radius: 12px;
    overflow: hidden;
    cursor: pointer;
    border: 2px solid rgba(255,255,255,0.1);
    transition: all 0.3s;
    background: rgba(255,255,255,0.05);
    background-size: cover;
    background-position: center;
}

.prem-item:hover {
    border-color: #eab308;
    transform: scale(1.05);
}

.prem-icon {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    font-size: 24px;
    color: #fff;
}

/* Store Section */
.store-section {
    margin: 40px 0;
}

.section-title {
    font-size: 1.5rem;
    font-weight: 700;
    margin-bottom: 20px;
    color: #eab308;
    text-transform: uppercase;
    letter-spacing: 1px;
}

/* Live Button */
.live-button {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    padding: 16px 32px;
    background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
    color: white;
    text-decoration: none;
    font-weight: 700;
    border-radius: 50px;
    margin-bottom: 30px;
    box-shadow: 0 8px 24px rgba(239, 68, 68, 0.4);
    animation: pulse 2s infinite;
    transition: transform 0.2s;
}

.live-button:hover {
    transform: scale(1.05);
}

@keyframes pulse {
    0%, 100% { box-shadow: 0 8px 24px rgba(239, 68, 68, 0.4); }
    50% { box-shadow: 0 8px 32px rgba(239, 68, 68, 0.6); }
}

/* Subscribe Button Override */
#btn {
    width: 100%;
    padding: 15px 30px;
    background: linear-gradient(135deg, #eab308 0%, #d97706 100%);
    color: #000;
    border: none;
    border-radius: 50px;
    font-weight: 700;
    font-size: 16px;
    cursor: pointer;
    transition: all 0.2s;
    margin: 20px 0;
    box-shadow: 0 4px 20px rgba(234, 179, 8, 0.3);
}

#btn:hover {
    transform: scale(1.02);
    box-shadow: 0 6px 30px rgba(234, 179, 8, 0.5);
}

/* Status Text */
#stat {
    text-align: center;
    font-size: 14px;
    color: #888;
    margin: 10px 0 20px;
}

/* Responsive */
@media (max-width: 768px) {
    .hero-section {
        height: 50vh;
    }
    
    .profile-header {
        flex-direction: column;
        text-align: center;
    }
    
    .profile-info h1 {
        font-size: 2rem;
    }
    
    .tiles-grid {
        grid-template-columns: 1fr;
        gap: 15px;
    }
    
    .tile--wide {
        grid-column: span 1;
    }
    
    .prem-gallery {
        grid-template-columns: repeat(2, 1fr);
    }
}

/* Scrollbar */
::-webkit-scrollbar {
    width: 10px;
}

::-webkit-scrollbar-track {
    background: #0a0a0a;
}

::-webkit-scrollbar-thumb {
    background: #eab308;
    border-radius: 5px;
}

::-webkit-scrollbar-thumb:hover {
    background: #fbbf24;
}
"""

DIGITAL_WALLS_JS = """
// Smooth scroll and link handling
document.addEventListener('DOMContentLoaded', function() {
    // Add smooth scroll to all internal links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });
    
    // Background parallax effect
    window.addEventListener('scroll', function() {
        const hero = document.querySelector('.hero-section');
        if (hero) {
            const scrolled = window.pageYOffset;
            hero.style.transform = 'translateY(' + (scrolled * 0.5) + 'px)';
        }
    });
});
"""

# ==========================================================
# INITIALIZATION & TEMPLATE MANAGEMENT
# ==========================================================

def init_templates():
    """Ensures template directory and default template exist"""
    TEMPLATES_DIR.mkdir(exist_ok=True)
    digital = TEMPLATES_DIR / "digital_walls.json"
    if not digital.exists():
        digital.write_text(json.dumps({
            "name": "Digital Walls",
            "description": "Cinematic scrolling wall with animated tiles",
            "renderer": "digital_walls",
            "css": "/* CSS handled by renderer */"
        }, indent=2))

def get_available_templates():
    """Returns list of all available templates"""
    init_templates()
    out = []
    for f in TEMPLATES_DIR.glob("*.json"):
        try:
            d = json.loads(f.read_text())
            out.append({
                "id": f.stem,
                "name": d.get("name", f.stem),
                "description": d.get("description", "")
            })
        except Exception:
            pass
    return out

def get_current_template(conn, handle):
    """Returns (template_id, enabled) for a channel"""
    import premium_tier_2
    cfg = premium_tier_2.get_module_config(conn, handle, "premium_ux")
    return cfg.get("template"), cfg.get("enabled", False)

def set_template(conn, handle, template_id):
    """Activates a template for a channel"""
    import premium_tier_2
    if not (TEMPLATES_DIR / (template_id + ".json")).exists():
        return {"success": False, "msg": "Template not found"}
    return premium_tier_2.set_module_config(
        conn,
        handle,
        "premium_ux",
        {"enabled": True, "template": template_id}
    )

def disable_premium_ux(conn, handle):
    """Disables Premium UX for a channel"""
    import premium_tier_2
    return premium_tier_2.set_module_config(
        conn,
        handle,
        "premium_ux",
        {"enabled": False, "template": None}
    )

# ==========================================================
# ADMIN INTERFACE (Called from Toolbox)
# ==========================================================

def run(conn, handle, payload):
    """
    Main entry point called by toolbox.py
    Handles admin actions for template management
    """
    action = payload.get("action")
    
    if action == "set_template":
        return set_template(conn, handle, payload.get("template_id"))
    
    if action == "disable":
        return disable_premium_ux(conn, handle)

    # Default: Render admin UI
    current, enabled = get_current_template(conn, handle)
    templates = get_available_templates()

    cards = ""
    for t in templates:
        active = enabled and current == t["id"]
        border = "2px solid #eab308" if active else "1px solid #333"
        bg = "#2a1c05" if active else "#181818"
        status_text = "<span style='color:#eab308; font-size:10px; font-weight:bold'>✓ ACTIVE</span>" if active else ""

        cards += f"""
        <div onclick="activateTemplate('{t['id']}')" style="
            padding:14px;
            border-radius:12px;
            background:{bg};
            border:{border};
            cursor:pointer;
            position:relative;
            transition: transform 0.1s;">
            <div style="display:flex; justify-content:space-between; align-items:center">
                <b>{t['name']}</b>
                {status_text}
            </div>
            <span style="font-size:11px;color:#888">{t['description']}</span>
        </div>
        """

    disable_btn = ""
    if enabled:
        disable_btn = """
        <button onclick="disableUX()" style="
            width:100%; 
            padding:10px; 
            background:#f87171; 
            color:#fff; 
            border:none; 
            border-radius:8px; 
            margin-top:15px; 
            font-weight:bold; 
            cursor:pointer;">
            ⚠️ DISABLE PREMIUM THEME
        </button>
        """

    return {
        "success": True,
        "html": f"""
        <div style="padding:10px">
            <h3 style="margin-bottom:5px;">Premium UX Templates</h3>
            <p style="font-size:12px; color:#aaa; margin-bottom:15px">
                Select a high-end visual template for your public page.
            </p>
            <div style="display:grid; gap:10px">{cards}</div>
            {disable_btn}
        </div>
        <script>
        async function activateTemplate(tId) {{
            const container = document.querySelector('#tb_list');
            if(container) container.style.opacity = '0.5';
            try {{
                const r = await fetch('/api/tier2/exec/toolbox/' + handle, {{
                    method: 'POST',
                    body: JSON.stringify({{ 
                        pin: pin, 
                        action: 'exec_tool', 
                        payload: {{ 
                            tool_id: 'premium_ux', 
                            data: {{ 
                                action: 'set_template', 
                                template_id: tId 
                            }} 
                        }} 
                    }})
                }});
                const j = await r.json();
                if(j.success) {{
                    runTool('premium_ux', 'Premium UX');
                }} else {{
                    alert(j.msg);
                    if(container) container.style.opacity = '1';
                }}
            }} catch(e) {{
                alert('Connection Failed');
                if(container) container.style.opacity = '1';
            }}
        }}
        
        async function disableUX() {{
            if(!confirm("Switch back to Standard Theme?")) return;
            const r = await fetch('/api/tier2/exec/toolbox/' + handle, {{
                method: 'POST',
                body: JSON.stringify({{ 
                    pin: pin, 
                    action: 'exec_tool', 
                    payload: {{ 
                        tool_id: 'premium_ux', 
                        data: {{ action: 'disable' }} 
                    }} 
                }})
            }});
            const j = await r.json();
            if(j.success) {{
                runTool('premium_ux', 'Premium UX');
            }} else {{
                alert(j.msg);
            }}
        }}
        </script>
        """
    }

# ==========================================================
# PUBLIC RENDERING FUNCTIONS
# ==========================================================

def _render_tiles(links):
    """Renders links as modern tiles with embed support and tracking"""
    tiles = ""
    
    # Try to import favicon module
    try:
        import favicon
        has_favicon = True
    except ImportError:
        has_favicon = False
    
    for i, l in enumerate(links):
        link_id = str(l.get('id', i))
        label = l.get("label", "")
        url = l.get("url", "#")
        
        # Check for YouTube
        yt = re.search(r"(youtu\.be\/|v=)([^&]+)", url)
        # Check for Spotify
        sp = re.search(r"open\.spotify\.com\/(track|album|playlist)\/([^?]+)", url)
        # Check for SoundCloud
        sc = re.search(r"soundcloud\.com\/[a-zA-Z0-9-]+\/[a-zA-Z0-9-]+", url)
        
        if yt:
            # YouTube Embed
            tiles += f"""
            <div class="tile tile--wide tile--video">
                <div class="embed-wrapper">
                    <iframe src="https://www.youtube.com/embed/{yt.group(2)}" 
                            frameborder="0" 
                            allowfullscreen 
                            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture">
                    </iframe>
                    <div class="embed-label">{label}</div>
                </div>
            </div>
            """
        elif sp:
            # Spotify Embed
            tiles += f"""
            <div class="tile tile--wide tile--embed">
                <iframe src="https://open.spotify.com/embed/{sp.group(1)}/{sp.group(2)}" 
                        frameborder="0" 
                        allowtransparency="true" 
                        allow="encrypted-media">
                </iframe>
            </div>
            """
        elif sc:
            # SoundCloud Embed
            tiles += f"""
            <div class="tile tile--wide tile--embed">
                <iframe width="100%" height="166" scrolling="no" frameborder="no" 
                        allow="autoplay" 
                        src="https://w.soundcloud.com/player/?url={url}&color=%23eab308&auto_play=false&hide_related=false&show_comments=true&show_user=true&show_reposts=false&show_teaser=true">
                </iframe>
            </div>
            """
        else:
            # Regular Link Tile with tracking and favicon
            track_url = f"/trk/l/{link_id}"
            
            # Get favicon icon if module available
            icon_html = ""
            if has_favicon:
                icon_html = favicon.get_icon_html(url)
            
            tiles += f"""
            <a href="{track_url}" target="_blank" class="tile">
                <div class="tile-content">
                    {icon_html}
                    <div class="tile-label">{label}</div>
                </div>
            </a>
            """
    
    return tiles

def render_digital_walls(handle, context):
    """
    Renders the Digital Walls theme
    
    Args:
        handle: Channel handle
        context: Dict containing all rendering data (links, bio, assets, etc.)
    
    Returns:
        Complete HTML page as string
    """
    # Unpack context
    links = context.get('links', [])
    bio = context.get('bio', '')
    has_avatar = context.get('has_avatar', False)
    has_banner = context.get('has_banner', False)
    is_premium = context.get('is_premium', False)
    pub_key = context.get('pub_key', '')
    
    # Build asset URLs
    banner = f"/banner/{handle}" if has_banner else "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=1600&q=80"
    avatar = f"/avatar/{handle}" if has_avatar else f"https://api.dicebear.com/7.x/avataaars/svg?seed={handle}"
    
    # Process bio with clickable hashtags
    bio_html = ""
    if bio:
        bio_processed = re.sub(
            r'#(\w+)', 
            r'<a href="/explore/\1">#\1</a>', 
            bio
        )
        bio_html = f'<div class="profile-bio">{bio_processed}</div>'
    
    # Render tiles from links
    tiles = _render_tiles(links)
    
    # Build section HTML components
    gallery_section = ""
    if is_premium and context.get('gallery_html'):
        gallery_section = f"""
        <div class="store-section">
            <h2 class="section-title">💎 Premium Gallery</h2>
            {context['gallery_html']}
        </div>
        """
    
    store_section = ""
    if context.get('store_html'):
        store_section = f"""
        <div class="store-section">
            <h2 class="section-title">🛍️ Store</h2>
            {context['store_html']}
        </div>
        """
    
    live_button = ""
    if context.get('live_btn_html'):
        live_match = re.search(r'href="([^"]+)"', context.get('live_btn_html', ''))
        if live_match:
            live_url = live_match.group(1)
            live_button = f'<a href="{live_url}" class="live-button">🔴 WATCH LIVESTREAM</a>'
    
    shout_outs = context.get('shout_outs_html', '')
    waitlist = context.get('waitlist_html', '')
    
    # Subscribe button and status
    subscribe_section = f"""
    <button id="btn" onclick="toggle()">Enable Notifications</button>
    <div id="stat" style="margin-top:15px;font-size:13px;color:#888">Checking status...</div>
    """
    
    # Return complete HTML page
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{handle} | NotiFly</title>
<link rel="manifest" href="/manifest.json">
<link rel="icon" href="/icon.svg">
<meta name="theme-color" content="#111">
<style>
{DIGITAL_WALLS_CSS}
{context.get('nsfw_css', '')}
</style>
</head>
<body>
    <!-- Hero Section -->
    <section class="hero-section" style="background-image: url('{banner}');">
        <div class="hero-content">
            <div class="profile-header">
                <img src="{avatar}" alt="{handle}" class="profile-avatar">
                <div class="profile-info">
                    <h1>{handle}</h1>
                    {bio_html}
                </div>
            </div>
        </div>
    </section>

    <!-- Main Content -->
    <main class="content-section">
        {live_button}
        
        {subscribe_section}
        
        {gallery_section}
        
        {store_section}
        
        {shout_outs}
        
        <!-- Links Grid -->
        <div class="tiles-grid">
            {tiles}
        </div>
        
        {waitlist}
    </main>

<script>
{DIGITAL_WALLS_JS}
{context.get('nsfw_js', '')}
{context.get('portal_js', '')}

// NotiFly Subscribe Logic
const VAPID="{pub_key}";
const HANDLE="{handle}";
const STORAGE_KEY="notifly_channels";
let swReg=null;
let isSub=false;

function urlB64ToUint8Array(base64String) {{
    const padding='='.repeat((4-base64String.length%4)%4);
    const base64=(base64String+padding).replace(/\\-/g,'+').replace(/_/g,'/');
    const rawData=window.atob(base64);
    const outputArray=new Uint8Array(rawData.length);
    for(let i=0;i<rawData.length;++i)outputArray[i]=rawData.charCodeAt(i);
    return outputArray;
}}

async function init() {{
    if(!('serviceWorker' in navigator)) return;
    swReg = await navigator.serviceWorker.register('/sw.js');
    const sub = await swReg.pushManager.getSubscription();
    if(sub) {{
        const response = await fetch('/api/verify_sub/'+HANDLE, {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{endpoint: sub.endpoint}})
        }});
        const data = await response.json();
        isSub = data.subscribed;
        let localChannels = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
        if(isSub && !localChannels.includes(HANDLE)) {{
            localChannels.push(HANDLE);
            localStorage.setItem(STORAGE_KEY, JSON.stringify(localChannels));
        }} else if(!isSub && localChannels.includes(HANDLE)) {{
            localChannels = localChannels.filter(h => h !== HANDLE);
            localStorage.setItem(STORAGE_KEY, JSON.stringify(localChannels));
        }}
    }} else {{
        isSub = false;
    }}
    updateUI();
}}

function updateUI() {{
    const btn = document.getElementById('btn');
    const stat = document.getElementById('stat');
    {context.get('portal_js', '')}
    if(isSub) {{
        btn.innerText = "Unsubscribe";
        btn.style.background = "linear-gradient(135deg, #333 0%, #222 100%)";
        btn.style.color = "#fff";
        stat.innerText = "✅ You are subscribed to " + HANDLE;
    }} else {{
        btn.innerText = "Subscribe";
        btn.style.background = "linear-gradient(135deg, #eab308 0%, #d97706 100%)";
        btn.style.color = "#000";
        stat.innerText = "❌ Not subscribed";
    }}
}}

async function toggle() {{
    const btn=document.getElementById('btn');
    btn.disabled=true;
    let localChannels = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
    let sub = await swReg.pushManager.getSubscription();
    if(isSub) {{
        if(sub) {{
            await fetch('/api/sub/'+HANDLE,{{
                method:'DELETE',
                headers:{{'Content-Type': 'application/json'}},
                body:JSON.stringify({{endpoint:sub.endpoint}})
            }});
        }}
        localChannels = localChannels.filter(h => h !== HANDLE);
        localStorage.setItem(STORAGE_KEY, JSON.stringify(localChannels));
        isSub=false;
    }} else {{
        if(!sub) {{
            sub=await swReg.pushManager.subscribe({{
                userVisibleOnly:true,
                applicationServerKey:urlB64ToUint8Array(VAPID)
            }});
        }}
        await fetch('/api/sub/'+HANDLE,{{
            method:'POST',
            headers:{{'Content-Type': 'application/json'}},
            body:JSON.stringify(sub)
        }});
        if(!localChannels.includes(HANDLE)) {{
            localChannels.push(HANDLE);
            localStorage.setItem(STORAGE_KEY, JSON.stringify(localChannels));
        }}
        isSub=true;
    }}
    updateUI();
    btn.disabled=false;
}}

init();
</script>
{context.get('tawk_html', '')}
</body>
</html>
"""
