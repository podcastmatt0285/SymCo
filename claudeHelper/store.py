"""
store.py - "Heavy Artillery" Edition
Requires: pip install requests beautifulsoup4
"""
import json
import re
import time
from premium_tier_2 import register_module, get_module_config, set_module_config

# TRY IMPORTING THE "HEAVY ARTILLERY"
try:
    import requests
    from bs4 import BeautifulSoup
    HAS_LIBS = True
except ImportError:
    HAS_LIBS = False
    print("[Store] WARNING: 'requests' and 'bs4' not found. Scraper will be weak.")

MODULE_KEY = "store"

# -------------------------
# The Heavy Scraper
# -------------------------
def fetch_og_image(url):
    print(f"[Store Scraper] Hunting: {url}")
    
    if not HAS_LIBS:
        return None # Fail early if libs missing

    # 1. Fake a Real Browser (Chrome on Windows)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://www.google.com/'
    }

    try:
        # 2. SHOPIFY TRICK (Try .json first)
        if "shopify" in url or "/products/" in url:
            try:
                json_url = url.split('?')[0] + ".json"
                r_api = requests.get(json_url, headers=headers, timeout=5)
                if r_api.status_code == 200:
                    data = r_api.json()
                    img = data.get('product', {}).get('image', {}).get('src')
                    if img: 
                        print(f"[Store] Found via Shopify API: {img}")
                        return img
            except: pass

        # 3. MAIN SCRAPE
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')

        # Priority 1: OpenGraph
        og_img = soup.find('meta', property='og:image')
        if og_img and og_img.get('content'): return og_img['content']

        # Priority 2: Twitter Card
        tw_img = soup.find('meta', name='twitter:image')
        if tw_img and tw_img.get('content'): return tw_img['content']

        # Priority 3: JSON-LD (Schema.org)
        # This is where Etsy/Amazon often hide data
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                data = json.loads(script.string)
                # Handle list of objects or single object
                if isinstance(data, list): items = data
                else: items = [data]

                for item in items:
                    # Look for 'image' key
                    if 'image' in item:
                        img = item['image']
                        # Handle varied formats (list, dict, string)
                        if isinstance(img, list): return img[0]
                        if isinstance(img, dict): return img.get('url')
                        if isinstance(img, str): return img
            except: continue
        
        # Priority 4: First large image on page (Desperation move)
        # Find images larger than 300px width? (Hard to detect without rendering)
        # Let's just look for a product image class
        prod_img = soup.find('img', id=re.compile(r'product|main|hero', re.I))
        if prod_img and prod_img.get('src'): return prod_img['src']

    except Exception as e:
        print(f"[Store] Scraper Failed: {e}")

    return None

# -------------------------
# UI Rendering
# -------------------------
def detect_platform(url):
    u = url.lower()
    if "shopify" in u: return "shopify"
    if "etsy" in u: return "etsy"
    if "gumroad" in u: return "gumroad"
    if "ko-fi" in u: return "kofi"
    if "amazon" in u or "amzn" in u: return "amazon"
    return "generic"

def get_platform_style(platform):
    styles = {
        "shopify": {"color": "#96bf48", "icon": "🛍️", "btn": "Shop"},
        "etsy":    {"color": "#f1641e", "icon": "🧶", "btn": "View"},
        "gumroad": {"color": "#ff90e8", "icon": "💳", "btn": "Buy"},
        "kofi":    {"color": "#13C3FF", "icon": "☕", "btn": "Support"},
        "amazon":  {"color": "#ff9900", "icon": "📦", "btn": "Amazon"},
        "generic": {"color": "#333333", "icon": "🔗", "btn": "Visit"}
    }
    return styles.get(platform, styles["generic"])

def build_card(store):
    url = store.get("url", "")
    label = store.get("label", "Item")
    desc = store.get("description", "")
    platform = store.get("type", "generic")
    image_url = store.get("image_url", "")
    
    # URL Cleanup
    if image_url and image_url.startswith("//"): image_url = "https:" + image_url
    
    style = get_platform_style(platform)
    bg_color = style['color']
    icon = style['icon']

    # VISUAL: Image Layer + Fallback Icon Layer
    visual_area = f"""
    <div style="height:140px; width:100%; position:relative; background:{bg_color}; overflow:hidden;">
        <div style="position:absolute; inset:0; display:flex; align-items:center; justify-content:center; background:#222;">
             <div style="font-size:40px; opacity:0.8;">{icon}</div>
        </div>
        <img src="{image_url}" 
             style="width:100%; height:100%; object-fit:cover; position:relative; z-index:2; transition:opacity 0.2s;"
             onload="this.style.opacity=1"
             onerror="this.style.opacity=0"
             loading="lazy">
        <div style="position:absolute; top:8px; right:8px; z-index:3; background:rgba(0,0,0,0.8); color:#fff; font-size:9px; padding:3px 6px; border-radius:4px; font-weight:bold; border:1px solid rgba(255,255,255,0.2);">
            {platform.upper()}
        </div>
    </div>
    """

    return f"""
    <a href="{url}" target="_blank" style="text-decoration:none; color:inherit; display:block;">
        <div class="store-card" style="background:#1a1a1a; border:1px solid #333; border-radius:12px; overflow:hidden; display:flex; flex-direction:column; height:100%;">
            {visual_area}
            <div style="padding:12px; display:flex; flex-direction:column; flex-grow:1; border-top:1px solid #222;">
                <div style="font-weight:bold; font-size:13px; color:#fff; margin-bottom:4px; line-height:1.3; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">{label}</div>
                {f'<div style="font-size:11px; color:#aaa; margin-bottom:12px; line-height:1.4; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden;">{desc}</div>' if desc else '<div style="flex-grow:1"></div>'}
                <div style="background:{bg_color}; color:#fff; text-align:center; padding:8px; border-radius:6px; font-weight:bold; font-size:12px; margin-top:auto;">
                    {style['btn']}
                </div>
            </div>
        </div>
    </a>
    """

# -------------------------
# Entry Point
# -------------------------
def store_entry(conn, handle, action, payload):
    if action == "render_public":
        cfg = get_module_config(conn, handle, MODULE_KEY)
        stores = cfg.get("stores", [])
        if not stores: return {"success": True, "html": ""}
        
        items = "".join([build_card(s) for s in stores])
        css = "<style>.store-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin-top: 20px; } @media (max-width:350px){ .store-grid { grid-template-columns: 1fr; } }</style>"
        html = f"""{css}<div style="margin-top:30px; border-top:1px dashed #333; padding-top:20px;">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:15px;"><h3 style="color:#a78bfa;font-size:14px;margin:0;">🛍️ STORE</h3></div>
            <div class="store-grid">{items}</div></div>"""
        return {"success": True, "html": html}

    if action == "save":
        stores = payload.get("stores", [])
        cleaned = []
        for s in stores:
            url = s.get("url", "").strip()
            if not url: continue
            if not url.startswith("http"): url = "https://" + url
            
            # Manual Check
            img = s.get("manual_image", "").strip()
            
            # Auto Fetch
            if not img:
                current_img = s.get("image_url", "")
                if current_img: img = current_img 
                else: img = fetch_og_image(url)
                
            cleaned.append({
                "url": url,
                "label": s.get("label", "Item"),
                "description": s.get("description", ""),
                "type": detect_platform(url),
                "image_url": img
            })
            
        set_module_config(conn, handle, MODULE_KEY, {"stores": cleaned})
        return {"success": True, "msg": "Store Updated"}

    return {"success": False}

register_module(MODULE_KEY, "Storefront Embeds", store_entry)
