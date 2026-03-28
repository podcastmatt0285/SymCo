import html
import sqlite3
from flask import request

def get_tags(handle, bio, links, has_banner, has_avatar, domain, is_gated=False):
    """
    Generates Open Graph and Twitter Card meta tags.
    Now supports Campaign Injections via ?cid= query param.
    """
    
    # --- CAMPAIGN HIJACK LOGIC ---
    cid = request.args.get('cid')
    if cid:
        try:
            # We must connect manually as app.py doesn't pass the DB connection here
            conn = sqlite3.connect('notifly.db')
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Fetch Campaign
            row = cursor.execute("SELECT * FROM campaigns WHERE id = ?", (cid,)).fetchone()
            
            if row:
                # 1. Update Click Stats (Naive approach: counts every hit including bots, but simple)
                cursor.execute("UPDATE campaigns SET clicks = clicks + 1 WHERE id = ?", (cid,))
                conn.commit()
                
                # 2. Return Campaign Meta + JS Redirect
                conn.close()
                
                c_title = html.escape(row['og_title'])
                c_desc = html.escape(row['og_desc'] or "Check this out!")
                c_img = row['og_image'] or f"https://{domain}/icon-512.png"
                target = row['target_url']
                
                return f"""
                <meta property="og:title" content="{c_title}">
                <meta property="og:description" content="{c_desc}">
                <meta property="og:image" content="{c_img}">
                <meta property="og:type" content="website">
                <meta name="twitter:card" content="summary_large_image">
                <meta name="twitter:title" content="{c_title}">
                <meta name="twitter:description" content="{c_desc}">
                <meta name="twitter:image" content="{c_img}">
                
                <script>
                    // Small delay to allow analytics to fire if needed, 
                    // but mostly to let the browser process the meta tags first.
                    setTimeout(function() {{
                        window.location.replace("{target}");
                    }}, 100);
                </script>
                <noscript>
                    <meta http-equiv="refresh" content="0;url={target}">
                </noscript>
                """
            conn.close()
        except Exception as e:
            print(f"[Campaign Error] {e}")
            pass # Fallback to standard profile

    # --- STANDARD PROFILE LOGIC (Your original code) ---
    desc_parts = []
    if bio: desc_parts.append(bio)
    
    if links:
        link_labels = [l.get('label', '') for l in links if l.get('label')]
        if link_labels:
            desc_parts.append("Links: " + ", ".join(link_labels))
            
    full_text = " | ".join(desc_parts)

    clean_bio = html.escape(full_text).replace('\n', ' ') if full_text else f"Check out {handle}'s channel on NotiFly."
    if len(clean_bio) > 200: clean_bio = clean_bio[:197] + "..."

    suffix = "?blur=true" if is_gated else ""
    image_url = f"https://{domain}/icon-192.png"
    card_type = "summary" 

    if has_banner:
        image_url = f"https://{domain}/banner/{handle}{suffix}"
        card_type = "summary_large_image"
    elif has_avatar:
        image_url = f"https://{domain}/avatar/{handle}{suffix}"
        card_type = "summary"

    return f"""
    <meta property="og:title" content="{handle}">
    <meta property="og:description" content="{clean_bio}">
    <meta property="og:image" content="{image_url}">
    <meta property="og:url" content="https://{domain}/c/{handle}">
    <meta property="og:type" content="website">
    <meta property="og:site_name" content="NotiFly">

    <meta name="twitter:card" content="{card_type}">
    <meta name="twitter:title" content="{handle}">
    <meta name="twitter:description" content="{clean_bio}">
    <meta name="twitter:image" content="{image_url}">
    """
