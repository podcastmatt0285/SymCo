import io
import os
from pathlib import Path
import base64

try:
    from PIL import Image
except ImportError:
    Image = None

BANNER_DIR = Path("banners")
MAX_BANNER_WIDTH = 1200
JPEG_QUALITY = 80

def init():
    BANNER_DIR.mkdir(exist_ok=True)

def save_banner(handle, image_data):
    """
    Accepts Base64 string OR Raw Bytes.
    Decodes if string, processes directly if bytes.
    """
    if Image is None:
        return {"success": False, "msg": "Server requires restart to load Image library."}

    try:
        # 1. Determine Input Type (Base64 String vs Raw Bytes)
        if isinstance(image_data, str):
            if ',' in image_data:
                image_data = image_data.split(',')[1]
            img_bytes = base64.b64decode(image_data)
        else:
            # It's already raw bytes (fast upload method)
            img_bytes = image_data
        
        # 2. Security Check on Size
        if len(img_bytes) > 15 * 1024 * 1024:
            return {"success": False, "msg": "Image too large (Max 15MB)"}
            
        img = Image.open(io.BytesIO(img_bytes))
        
        # 3. Convert to RGB
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
            
        # 4. Resize Logic
        if img.width > MAX_BANNER_WIDTH:
            ratio = MAX_BANNER_WIDTH / float(img.width)
            new_height = int(float(img.height) * ratio)
            img = img.resize((MAX_BANNER_WIDTH, new_height), Image.Resampling.LANCZOS)
            
        # 5. Save
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=JPEG_QUALITY, optimize=True)
        
        target_path = BANNER_DIR / handle
        target_path.write_bytes(output.getvalue())
        
        return {"success": True, "msg": "Banner updated!"}

    except Exception as e:
        return {"success": False, "msg": f"Failed: {str(e)}"}

def get_banner_path(handle):
    path = BANNER_DIR / handle
    if path.exists(): return path
    return None
