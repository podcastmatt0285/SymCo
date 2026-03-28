"""
Tool: Watermarker
Description: Adds customizable opaque text watermarks to images.
"""
import base64
import io
from PIL import Image, ImageDraw, ImageFont

META = {
    "name": "Watermarker",
    "icon": "💧",
    "desc": "Add text watermarks to images with custom opacity."
}

MAX_PIXELS = 8000 * 8000 

def get_font(size):
    try:
        options = [
            "/system/fonts/Roboto-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "arial.ttf",
            "C:\\Windows\\Fonts\\arial.ttf"
        ]
        for path in options:
            try:
                return ImageFont.truetype(path, size)
            except:
                continue
        return ImageFont.load_default()
    except:
        return ImageFont.load_default()

def process_image(data_url, text, opacity, color_hex, size, pos, tile=False, rotate=0, stroke=False):
    try:
        header, encoded = data_url.split(",", 1)
        img_data = base64.b64decode(encoded)
        base_img = Image.open(io.BytesIO(img_data))
        img_format = base_img.format or "JPEG"
        base_img = base_img.convert("RGBA")

        if base_img.width * base_img.height > MAX_PIXELS:
            raise ValueError("Image too large")

        txt_layer = Image.new("RGBA", base_img.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(txt_layer)
        font = get_font(int(size))
        
        lines = text.split('\n')
        line_sizes = []
        for line in lines:
            try:
                bbox = draw.textbbox((0, 0), line, font=font)
                line_sizes.append((bbox[2] - bbox[0], bbox[3] - bbox[1]))
            except AttributeError:
                w, h = draw.textsize(line, font=font)
                line_sizes.append((w, h))

        text_w = max([x[0] for x in line_sizes])
        text_h = sum([x[1] for x in line_sizes])

        W, H = base_img.size
        padding = int(min(W, H) * 0.05)

        color_hex = color_hex.lstrip('#')
        r, g, b = tuple(int(color_hex[i:i+2], 16) for i in (0, 2, 4))
        alpha = int((int(opacity) / 100) * 255)

        def draw_block(x, y):
            cy = y
            for i, line in enumerate(lines):
                if stroke:
                    stroke_w = max(1, int(int(size) / 15))
                    draw.text((x, cy), line, font=font, fill=(r, g, b, alpha), 
                             stroke_width=stroke_w, stroke_fill=(0, 0, 0, alpha))
                else:
                    draw.text((x, cy), line, font=font, fill=(r, g, b, alpha))
                cy += line_sizes[i][1]

        if tile:
            step_x = int(text_w * 1.5)
            step_y = int(text_h * 4)
            for y_idx, y in enumerate(range(-int(H/2), H + int(H/2), step_y)):
                offset = (step_x // 2) if y_idx % 2 == 0 else 0
                for x in range(-int(W/2), W + int(W/2), step_x):
                    draw_block(x + offset, y)
        else:
            if pos == 'tl': x, y = padding, padding
            elif pos == 'tr': x, y = W - text_w - padding, padding
            elif pos == 'bl': x, y = padding, H - text_h - padding
            elif pos == 'br': x, y = W - text_w - padding, H - text_h - padding
            else: x, y = (W - text_w) // 2, (H - text_h) // 2
            draw_block(x, y)

        if rotate and int(rotate) != 0:
            txt_layer = txt_layer.rotate(int(rotate), resample=Image.BICUBIC, center=(W / 2, H / 2))

        out = Image.alpha_composite(base_img, txt_layer)

        buffered = io.BytesIO()
        if img_format.upper() in ['PNG', 'WEBP']:
            out.save(buffered, format=img_format)
            mime_type = f"image/{img_format.lower()}"
        else:
            out = out.convert("RGB")
            out.save(buffered, format="JPEG", quality=95)
            mime_type = "image/jpeg"

        img_str = base64.b64encode(buffered.getvalue()).decode()
        return f"data:{mime_type};base64,{img_str}"

    except Exception as e:
        print(f"[Watermark Error] {e}")
        return None

def run(conn, handle, payload):
    action = payload.get('sub_action')

    if action == 'generate':
        result_b64 = process_image(
            payload.get('image'),
            payload.get('text', 'Watermark'),
            payload.get('opacity', 50),
            payload.get('color', '#ffffff'),
            payload.get('size', 40),
            payload.get('pos', 'br'),
            tile=payload.get('tile', False),
            rotate=payload.get('rotate', 0),
            stroke=payload.get('stroke', False)
        )

        if result_b64:
            return {"success": True, "image": result_b64}
        else:
            return {"success": False, "msg": "Failed to process image."}

    # UI separated into standard strings to avoid syntax errors
    css = """
    <style>
        .wm-container { color:#eee; font-family:-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        .wm-group { background:#1a1a1a; padding:15px; border-radius:8px; border:1px solid #333; margin-bottom:15px; }
        .wm-label { display:block; font-size:11px; color:#aaa; text-transform:uppercase; font-weight:bold; margin-bottom:8px; }
        
        .range-wrap { display:flex; align-items:center; gap:10px; margin-bottom:10px; }
        input[type=range] { flex-grow:1; accent-color:#eab308; cursor:pointer; }
        .val-badge { background:#333; color:#fff; padding:2px 6px; border-radius:4px; font-size:11px; font-family:monospace; min-width:35px; text-align:center; border:1px solid #444; }

        .color-wrap { display:flex; align-items:center; gap:10px; }
        input[type="color"] { -webkit-appearance: none; border: none; width: 32px; height: 32px; border-radius: 50%; overflow: hidden; padding: 0; cursor: pointer; }
        input[type="color"]::-webkit-color-swatch-wrapper { padding: 0; }
        input[type="color"]::-webkit-color-swatch { border: 2px solid #555; border-radius: 50%; }

        .pos-grid { display:grid; grid-template-columns: repeat(3, 1fr); gap:5px; width:120px; margin: 10px auto; }
        .pos-btn { aspect-ratio:1; background:#333; border:1px solid #444; border-radius:4px; cursor:pointer; display:flex; align-items:center; justify-content:center; transition:0.2s; }
        .pos-btn:hover { background:#444; }
        .pos-btn.active { background:#eab308; border-color:#eab308; color:#000; font-weight:bold; }
        .pos-btn.disabled { opacity:0.3; pointer-events:none; }
        .pos-dot { width:6px; height:6px; background:#888; border-radius:50%; }
        .pos-btn.active .pos-dot { background:#000; }

        .file-drop { border:2px dashed #444; padding:20px; text-align:center; border-radius:8px; cursor:pointer; transition:0.2s; }
        .file-drop:hover { border-color:#eab308; background:rgba(234, 179, 8, 0.05); }
    </style>
    """

    body = """
    <div class="wm-container">
        <div class="wm-group">
            <span class="wm-label">1. Image Source</span>
            <div class="file-drop" onclick="document.getElementById('wm_file').click()">
                <div style="font-size:24px; margin-bottom:5px;">🖼️</div>
                <div id="file_name_disp" style="font-size:13px; color:#aaa;">Click to Select Image</div>
                <input type="file" id="wm_file" accept="image/*" style="display:none" onchange="updateFileName(this)">
            </div>
        </div>

        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:15px;">
            <div>
                <div class="wm-group">
                    <span class="wm-label">2. Text Content</span>
                    <textarea id="wm_text" rows="2" style="width:100%; background:#000; color:#fff; border:1px solid #333; border-radius:4px; padding:8px; box-sizing:border-box;">© NotiFly Exclusive</textarea>
                </div>

                <div class="wm-group">
                    <span class="wm-label">3. Appearance</span>
                    
                    <div style="margin-bottom:12px;">
                        <div class="color-wrap">
                            <input type="color" id="wm_color" value="#ffffff" onchange="document.getElementById('hex_disp').innerText = this.value">
                            <div style="font-size:12px;">
                                <div style="color:#aaa;">Text Color</div>
                                <div id="hex_disp" style="font-family:monospace;">#ffffff</div>
                            </div>
                        </div>
                    </div>

                    <label style="font-size:12px; display:block; margin-bottom:4px;">Opacity</label>
                    <div class="range-wrap">
                        <input id="wm_opacity" type="range" min="10" max="100" value="50" oninput="updateVal('v_op', this.value + '%')">
                        <span id="v_op" class="val-badge">50%</span>
                    </div>

                    <label style="font-size:12px; display:block; margin-bottom:4px;">Size</label>
                    <div class="range-wrap">
                        <input id="wm_size" type="range" min="10" max="200" value="60" oninput="updateVal('v_sz', this.value)">
                        <span id="v_sz" class="val-badge">60</span>
                    </div>
                    
                    <label style="font-size:12px; display:block; margin-bottom:4px;">Rotation</label>
                    <div class="range-wrap">
                        <input id="wm_rotate" type="range" min="-45" max="45" value="0" oninput="updateVal('v_rot', this.value + '°')">
                        <span id="v_rot" class="val-badge">0°</span>
                    </div>

                    <div style="margin-top:10px;">
                        <label style="display:flex; align-items:center; gap:8px; font-size:13px; cursor:pointer;">
                            <input type="checkbox" id="wm_stroke">
                            <span>Add Black Outline</span>
                        </label>
                    </div>
                </div>
            </div>

            <div>
                <div class="wm-group">
                    <span class="wm-label">4. Position</span>
                    <input type="hidden" id="wm_pos" value="br">
                    
                    <div id="pos_grid_ui" class="pos-grid">
                        <div class="pos-btn" onclick="setPos('tl')" id="p_tl"><div class="pos-dot"></div></div>
                        <div class="pos-btn disabled" style="border:none; background:transparent;"></div>
                        <div class="pos-btn" onclick="setPos('tr')" id="p_tr"><div class="pos-dot"></div></div>
                        
                        <div class="pos-btn disabled" style="border:none; background:transparent;"></div>
                        <div class="pos-btn" onclick="setPos('c')" id="p_c"><div class="pos-dot"></div></div>
                        <div class="pos-btn disabled" style="border:none; background:transparent;"></div>
                        
                        <div class="pos-btn" onclick="setPos('bl')" id="p_bl"><div class="pos-dot"></div></div>
                        <div class="pos-btn disabled" style="border:none; background:transparent;"></div>
                        <div class="pos-btn active" onclick="setPos('br')" id="p_br"><div class="pos-dot"></div></div>
                    </div>

                    <div style="margin-top:15px; border-top:1px solid #333; padding-top:10px;">
                        <label style="display:flex; align-items:center; gap:8px; font-size:13px; cursor:pointer;">
                            <input type="checkbox" id="wm_tile" onchange="toggleGrid(this.checked)">
                            <span>Tile Everywhere (Repeated)</span>
                        </label>
                    </div>
                </div>

                <div class="wm-group" style="border-color:#eab308; background:#222;">
                    <span class="wm-label" style="color:#eab308;">5. Generate</span>
                    <button onclick="generateWatermark()" id="wm_btn"
                        style="width:100%; padding:12px; border-radius:6px; background:#eab308; color:#000; font-weight:bold; border:none; cursor:pointer;">
                        PROCESS IMAGE
                    </button>
                    <div id="proc_status" style="text-align:center; font-size:12px; color:#aaa; margin-top:5px; height:15px;"></div>
                </div>
            </div>
        </div>

        <div id="wm_result" style="display:none; animation: fadeIn 0.5s;">
            <div class="wm-group" style="text-align:center;">
                <span class="wm-label" style="color:#4ade80;">Success - Click Image to Download</span>
                <a id="wm_down_link">
                    <img id="wm_preview" style="max-width:100%; border-radius:4px; border:2px solid #4ade80;">
                </a>
            </div>
        </div>
    </div>

    <script>
    function updateFileName(input) {
        if(input.files && input.files[0]) {
            document.getElementById('file_name_disp').innerText = "Selected: " + input.files[0].name;
            document.getElementById('file_name_disp').style.color = "#4ade80";
        }
    }

    function updateVal(id, val) {
        document.getElementById(id).innerText = val;
    }

    function setPos(pos) {
        document.getElementById('wm_pos').value = pos;
        ['tl','tr','c','bl','br'].forEach(p => {
            document.getElementById('p_' + p).className = 'pos-btn';
        });
        document.getElementById('p_' + pos).className = 'pos-btn active';
    }

    function toggleGrid(isTiled) {
        const grid = document.getElementById('pos_grid_ui');
        if(isTiled) {
            grid.style.opacity = '0.3';
            grid.style.pointerEvents = 'none';
        } else {
            grid.style.opacity = '1';
            grid.style.pointerEvents = 'auto';
        }
    }

    async function generateWatermark() {
        const fileInput = document.getElementById('wm_file');
        const btn = document.getElementById('wm_btn');
        const stat = document.getElementById('proc_status');

        if(!fileInput.files[0]) return alert("Please select an image in Step 1.");

        btn.disabled = true;
        btn.style.opacity = "0.5";
        stat.innerText = "Processing high-res image...";

        const reader = new FileReader();
        reader.readAsDataURL(fileInput.files[0]);

        reader.onload = async function() {
            const payload = {
                sub_action: 'generate',
                image: reader.result,
                text: document.getElementById('wm_text').value,
                color: document.getElementById('wm_color').value,
                opacity: document.getElementById('wm_opacity').value,
                size: document.getElementById('wm_size').value,
                pos: document.getElementById('wm_pos').value,
                tile: document.getElementById('wm_tile').checked,
                stroke: document.getElementById('wm_stroke').checked,
                rotate: document.getElementById('wm_rotate').value
            };

            try {
                // 'handle' and 'pin' are globally available in the admin dashboard scope
                const r = await fetch('/api/tier2/exec/toolbox/' + handle, {
                    method: 'POST',
                    body: JSON.stringify({
                        pin: pin,
                        action: 'exec_tool',
                        payload: { tool_id: 'watermark_tool', data: payload }
                    })
                });

                const j = await r.json();
                if(j.image) {
                    const prev = document.getElementById('wm_preview');
                    const link = document.getElementById('wm_down_link');
                    const resDiv = document.getElementById('wm_result');
                    
                    prev.src = j.image;
                    link.href = j.image;
                    link.download = "notifly_watermark_" + Date.now() + ".jpg";
                    
                    resDiv.style.display = 'block';
                    resDiv.scrollIntoView({behavior: "smooth"});
                    stat.innerText = "";
                } else {
                    alert("Error: " + j.msg);
                }
            } catch(e) {
                alert("Connection failed.");
            }
            
            btn.disabled = false;
            btn.style.opacity = "1";
        };
    }
    </script>
    """
    
    # Return concatenation instead of f-string to prevent JS brace errors
    return {"success": True, "html": css + body}
