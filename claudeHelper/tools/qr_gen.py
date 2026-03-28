"""
Tool: Themed QR Display
Description: Generates QR code with avatar embedded, matching channel theme.
"""
import re
from pathlib import Path
import io
import base64

META = {
    "name": "Show QR Code",
    "icon": "📱",
    "desc": "Creates themed QR with your avatar embedded."
}

def extract_theme_colors(skin_name):
    """Extract the exact colors used for background and card from CSS."""
    css_path = Path("skins") / f"{skin_name}.css"
    
    # Defaults
    theme = {
        "bg": "111111",        # Background color
        "card": "222222",      # Card/box color (for dots)
        "primary": "eab308"    # Accent color
    }
    
    if not css_path.exists():
        return theme
    
    try:
        css_content = css_path.read_text()
        
        # Extract CSS variables
        var_pattern = r'--([a-zA-Z-]+)\s*:\s*#?([0-9a-fA-F]{6})'
        variables = dict(re.findall(var_pattern, css_content))
        
        # Map variables to theme
        if 'bg' in variables:
            theme['bg'] = variables['bg']
        elif 'bg-color' in variables:
            theme['bg'] = variables['bg-color']
        elif 'bg-dark' in variables:
            theme['bg'] = variables['bg-dark']
        
        if 'card' in variables:
            theme['card'] = variables['card']
        elif 'card-bg' in variables:
            theme['card'] = variables['card-bg']
        
        if 'primary' in variables:
            theme['primary'] = variables['primary']
        elif 'accent' in variables:
            theme['primary'] = variables['accent']
        elif 'text' in variables:
            theme['primary'] = variables['text']
        
    except Exception as e:
        print(f"[QR Theme] Error: {e}")
    
    return theme

def generate_qr_with_avatar(handle, theme):
    """Generate QR code image with avatar embedded in center."""
    try:
        from PIL import Image, ImageDraw
        import requests
        
        # Generate base QR code
        url = f"https://notifly.cc/c/{handle}"
        qr_api = f"https://quickchart.io/qr?text={url}&dark={theme['card']}&light={theme['bg']}&margin=2&size=800&ecLevel=H&format=png"
        
        # Fetch QR code
        response = requests.get(qr_api, timeout=10)
        qr_img = Image.open(io.BytesIO(response.content))
        
        # Check if avatar exists
        avatar_path = Path("avatars") / handle
        if avatar_path.exists():
            # Load and resize avatar
            avatar = Image.open(avatar_path)
            
            # Convert to RGB if needed
            if avatar.mode in ('RGBA', 'LA', 'P'):
                if avatar.mode == 'P':
                    avatar = avatar.convert('RGBA')
                # Create white background
                background = Image.new('RGB', avatar.size, (255, 255, 255))
                if avatar.mode == 'RGBA':
                    background.paste(avatar, mask=avatar.split()[-1])
                else:
                    background.paste(avatar)
                avatar = background
            
            # Size avatar to be about 15% of QR code
            avatar_size = int(qr_img.width * 0.15)
            avatar = avatar.resize((avatar_size, avatar_size), Image.Resampling.LANCZOS)
            
            # Create circular mask
            mask = Image.new('L', (avatar_size, avatar_size), 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0, avatar_size, avatar_size), fill=255)
            
            # Create white circle background (slightly larger)
            border_size = int(avatar_size * 1.2)
            white_circle = Image.new('RGB', (border_size, border_size), (255, 255, 255))
            circle_mask = Image.new('L', (border_size, border_size), 0)
            draw = ImageDraw.Draw(circle_mask)
            draw.ellipse((0, 0, border_size, border_size), fill=255)
            
            # Calculate center position
            qr_center = (qr_img.width // 2, qr_img.height // 2)
            white_pos = (qr_center[0] - border_size // 2, qr_center[1] - border_size // 2)
            avatar_pos = (qr_center[0] - avatar_size // 2, qr_center[1] - avatar_size // 2)
            
            # Paste white circle first
            qr_img.paste(white_circle, white_pos, circle_mask)
            
            # Paste avatar on top
            qr_img.paste(avatar, avatar_pos, mask)
        
        # Convert to base64 for embedding
        buffered = io.BytesIO()
        qr_img.save(buffered, format="PNG", optimize=True, quality=95)
        img_base64 = base64.b64encode(buffered.getvalue()).decode()
        
        return f"data:image/png;base64,{img_base64}"
        
    except Exception as e:
        print(f"[QR Gen Error] {e}")
        # Fallback to API-only version
        url = f"https://notifly.cc/c/{handle}"
        return f"https://quickchart.io/qr?text={url}&dark={theme['card']}&light={theme['bg']}&margin=2&size=800&ecLevel=H"

def run(conn, handle, payload):
    cursor = conn.cursor()
    cursor.execute("SELECT skin FROM channels WHERE handle=?", (handle,))
    row = cursor.fetchone()
    skin = row[0] if row else "default"
    
    # Extract theme colors
    theme = extract_theme_colors(skin)
    
    # Generate QR with embedded avatar
    qr_data_url = generate_qr_with_avatar(handle, theme)
    
    url = f"https://notifly.cc/c/{handle}"
    
    html = f"""
    <div style="text-align: center; animation: fadeIn 0.5s;">
        
        <!-- QR Code Preview -->
        <div style="margin-bottom: 20px;">
            <div style="color: #{theme['primary']}; 
                        font-weight: bold; 
                        font-size: 16px; 
                        margin-bottom: 15px;">
                📱 Your Themed QR Code
            </div>
            
            <!-- QR Container -->
            <div style="display: inline-block; 
                        border: 5px solid #{theme['primary']}; 
                        border-radius: 20px; 
                        padding: 10px;
                        background: #{theme['bg']};
                        box-shadow: 0 10px 40px rgba(0,0,0,0.4);">
                
                <img id="qr_preview" 
                     src="{qr_data_url}" 
                     style="display: block; 
                            width: 300px; 
                            height: 300px; 
                            border-radius: 10px;">
            </div>
            
            <div style="margin-top: 15px; 
                        font-size: 12px; 
                        color: #888;">
                Background: <span style="color: #{theme['bg']};">#{theme['bg']}</span> • 
                Dots: <span style="color: #{theme['card']};">#{theme['card']}</span>
            </div>
        </div>
        
        <!-- Share URL -->
        <div style="margin-top: 20px;">
            <input value="{url}" 
                   id="qr_url_input"
                   style="background: #333; 
                          border: 1px solid #555; 
                          color: #aaa; 
                          width: 100%; 
                          text-align: center; 
                          font-size: 12px; 
                          padding: 10px; 
                          border-radius: 8px;
                          font-family: monospace;" 
                   readonly
                   onclick="this.select()">
        </div>
        
        <!-- Action Buttons -->
        <div style="display: flex; gap: 10px; margin-top: 15px;">
            <button onclick="copyQRLink()" 
                    style="flex: 1; 
                           background: #{theme['primary']}; 
                           color: #000; 
                           padding: 12px; 
                           border: none;
                           cursor: pointer; 
                           border-radius: 8px; 
                           font-weight: bold; 
                           font-size: 13px;
                           transition: transform 0.1s;">
                📋 Copy Link
            </button>
            <button onclick="downloadQR()" 
                    style="flex: 1; 
                           background: #333; 
                           color: #fff; 
                           padding: 12px; 
                           border: 1px solid #555;
                           cursor: pointer; 
                           border-radius: 8px; 
                           font-weight: bold; 
                           font-size: 13px;
                           transition: transform 0.1s;">
                💾 Download PNG
            </button>
        </div>
        
        <!-- Info Box -->
        <div style="margin-top: 20px; 
                    padding: 15px; 
                    background: rgba(0,0,0,0.3); 
                    border-radius: 10px; 
                    border: 1px solid #333;">
            <div style="font-size: 11px; color: #888; line-height: 1.6;">
                ✨ This QR code matches your channel's exact color scheme<br>
                🎨 Background: <b style="color: #{theme['bg']}">Channel Background</b><br>
                📦 Dots: <b style="color: #{theme['card']}">Card/Box Color</b><br>
                🖼️ Avatar: Embedded in center (high error correction)
            </div>
        </div>
        
        <button onclick="openToolbox()" 
                style="margin-top: 15px; 
                       background: #222; 
                       color: #fff; 
                       width: 100%; 
                       padding: 12px; 
                       border: 1px solid #444; 
                       cursor: pointer; 
                       border-radius: 8px;
                       font-size: 13px;">
            ← Back to Tools
        </button>
    </div>
    
    <script>
    function copyQRLink() {{
        const input = document.getElementById('qr_url_input');
        input.select();
        navigator.clipboard.writeText(input.value).then(() => {{
            alert('✅ Link copied to clipboard!');
        }});
    }}
    
    function downloadQR() {{
        try {{
            const img = document.getElementById('qr_preview');
            const a = document.createElement('a');
            a.href = img.src;
            a.download = '{handle}_{skin}_qr.png';
            document.body.appendChild(a);
            a.click();
            a.remove();
            
            alert('✅ QR code downloaded with avatar embedded!');
        }} catch(e) {{
            alert('❌ Download failed. Try right-clicking the QR code and selecting "Save Image".');
        }}
    }}
    </script>
    
    <style>
    @keyframes fadeIn {{
        from {{ opacity: 0; transform: translateY(10px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}
    
    button:hover {{
        transform: translateY(-2px);
        opacity: 0.9;
    }}
    
    button:active {{
        transform: translateY(0);
    }}
    </style>
    """
    
    return {"success": True, "html": html}
