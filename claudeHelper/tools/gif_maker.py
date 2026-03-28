"""
Tool: Video to GIF Converter
Description: Convert video clips to high-quality GIFs with Watermark support.
"""
import base64
import subprocess
import os
import time
from pathlib import Path

META = {
    "name": "Video to GIF Pro",
    "icon": "🎞️",
    "desc": "Convert clips to GIF with trim, FPS control, and watermarks."
}

def run(conn, handle, payload):
    action = payload.get('sub_action')

    # --- 1. PROCESSING LOGIC ---
    if action == 'convert':
        try:
            # Get params
            video_b64 = payload.get('video_data', '')
            start = payload.get('start', 0)
            duration = payload.get('duration', 5)
            fps = payload.get('fps', 10)
            width = payload.get('width', 320)
            text = payload.get('watermark', '').strip() # <--- NEW PARAM
            
            if not video_b64:
                return {"success": False, "msg": "No video data received."}

            # Setup paths
            temp_dir = Path("video_cache")
            temp_dir.mkdir(exist_ok=True)
            timestamp = int(time.time())
            in_path = temp_dir / f"temp_{timestamp}.mp4"
            out_path = temp_dir / f"gif_{timestamp}.gif"
            palette_path = temp_dir / f"palette_{timestamp}.png"

            # Save Input
            if "," in video_b64:
                header, encoded = video_b64.split(",", 1)
                data = base64.b64decode(encoded)
            else:
                data = base64.b64decode(video_b64)     
            in_path.write_bytes(data)

            # --- FFmpeg Filter Construction ---
            # 1. FPS & Scale
            filters = f"fps={fps},scale={width}:-1:flags=lanczos"
            
            # 2. Watermark (drawtext)
            # This places white text with a black shadow in the bottom-right corner
            if text:
                # Escape special characters for FFmpeg
                safe_text = text.replace(":", "\\:").replace("'", "")
                filters += f",drawtext=text='{safe_text}':fontcolor=white:fontsize=12:shadowcolor=black:shadowx=1:shadowy=1:x=w-tw-5:y=h-th-5"

            # Step A: Generate Palette (with filters applied!)
            subprocess.run([
                "ffmpeg", "-y", "-ss", str(start), "-t", str(duration),
                "-i", str(in_path),
                "-vf", f"{filters},palettegen",
                str(palette_path)
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

            # Step B: Render GIF (Apply same filters + Palette)
            subprocess.run([
                "ffmpeg", "-y", "-ss", str(start), "-t", str(duration),
                "-i", str(in_path), "-i", str(palette_path),
                "-lavfi", f"{filters} [x]; [x][1:v] paletteuse",
                str(out_path)
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

            # Read Result
            gif_bytes = out_path.read_bytes()
            gif_b64 = "data:image/gif;base64," + base64.b64encode(gif_bytes).decode('utf-8')

            # Cleanup
            try:
                in_path.unlink()
                out_path.unlink()
                palette_path.unlink()
            except: pass

            return {"success": True, "image": gif_b64}

        except Exception as e:
            return {"success": False, "msg": f"FFmpeg Error: {str(e)}"}

    # --- 2. RENDER UI ---
    return {
        "success": True, 
        "html": """
        <div style="background:#1a1a1a; border:1px solid #333; padding:20px; border-radius:10px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:15px;">
                <h3 style="margin:0; color:#eab308;">🎞️ Video to GIF Pro</h3>
                <span style="font-size:11px; color:#666;">Powered by FFmpeg</span>
            </div>

            <div style="border:2px dashed #444; padding:20px; text-align:center; border-radius:8px; margin-bottom:15px; cursor:pointer;" 
                 onclick="document.getElementById('gif_in').click()">
                <div style="font-size:24px; margin-bottom:10px;">📂</div>
                <div style="color:#aaa; font-size:13px;">Click to select video (Max 15MB)</div>
                <input type="file" id="gif_in" accept="video/*" style="display:none" onchange="loadVideo(this)">
            </div>
            
            <video id="vid_prev" controls style="width:100%; max-height:300px; display:none; border-radius:8px; border:1px solid #333; margin-bottom:15px;"></video>

            <div id="gif_settings" style="display:none; background:#222; padding:15px; border-radius:8px;">
                
                <label style="font-size:11px; color:#aaa; display:block; margin-bottom:5px;">TRIM START (Seconds)</label>
                <div style="display:flex; gap:10px; align-items:center; margin-bottom:10px;">
                    <input type="range" id="rn_start" min="0" value="0" step="0.1" style="flex:1" oninput="upd('val_start', this.value)">
                    <span id="val_start" style="width:30px; text-align:right; font-size:12px; font-family:monospace; color:#eab308;">0.0</span>
                </div>

                <label style="font-size:11px; color:#aaa; display:block; margin-bottom:5px;">DURATION (Seconds)</label>
                <div style="display:flex; gap:10px; align-items:center; margin-bottom:10px;">
                    <input type="range" id="rn_dur" min="1" max="15" value="3" step="0.5" style="flex:1" oninput="upd('val_dur', this.value)">
                    <span id="val_dur" style="width:30px; text-align:right; font-size:12px; font-family:monospace; color:#eab308;">3.0</span>
                </div>

                <label style="font-size:11px; color:#aaa; display:block; margin-bottom:5px;">WATERMARK TEXT (Optional)</label>
                <input id="txt_wm" placeholder="e.g. @MyChannel" style="width:100%; background:#111; border:1px solid #444; color:#fff; padding:8px; border-radius:4px; margin-bottom:15px;">

                <div style="display:grid; grid-template-columns: 1fr 1fr; gap:10px; margin-bottom:15px;">
                    <div>
                        <label style="font-size:11px; color:#aaa;">WIDTH (px)</label>
                        <select id="sel_width" style="width:100%; background:#111; border:1px solid #444; color:#fff; padding:8px; border-radius:4px; margin-top:5px;">
                            <option value="240">240px (Tiny)</option>
                            <option value="320" selected>320px (Email)</option>
                            <option value="480">480px (Social)</option>
                            <option value="640">640px (HD GIF)</option>
                        </select>
                    </div>
                    <div>
                        <label style="font-size:11px; color:#aaa;">FPS (Speed)</label>
                        <select id="sel_fps" style="width:100%; background:#111; border:1px solid #444; color:#fff; padding:8px; border-radius:4px; margin-top:5px;">
                            <option value="5">5 FPS (Retro)</option>
                            <option value="10">10 FPS (Standard)</option>
                            <option value="15" selected>15 FPS (Smooth)</option>
                            <option value="24">24 FPS (Film)</option>
                        </select>
                    </div>
                </div>

                <button onclick="createGif()" id="btn_conv" style="width:100%; padding:12px; background:#eab308; color:#000; font-weight:bold; border:none; border-radius:6px; cursor:pointer;">
                    ⚡ CONVERT TO GIF
                </button>
            </div>

            <div id="gif_result" style="display:none; margin-top:20px; text-align:center; animation: fadeIn 0.5s;">
                <h4 style="color:#4ade80; margin:0 0 10px 0;">🎉 GIF Ready!</h4>
                <img id="final_gif" style="max-width:100%; border-radius:8px; border:2px solid #eab308; box-shadow:0 0 20px rgba(234,179,8,0.2);">
                <a id="down_link" style="display:block; margin-top:10px; color:#fff; text-decoration:underline; font-size:12px; cursor:pointer;">Download GIF</a>
            </div>

        </div>

        <script>
        let rawVideo = "";

        function upd(id, val) { document.getElementById(id).innerText = val; }

        function loadVideo(input) {
            const file = input.files[0];
            if(!file) return;
            if(file.size > 15 * 1024 * 1024) return alert("File too large! Keep it under 15MB.");
            
            const reader = new FileReader();
            reader.onload = function(e) {
                rawVideo = e.target.result;
                const v = document.getElementById('vid_prev');
                v.src = rawVideo;
                v.style.display = 'block';
                document.getElementById('gif_settings').style.display = 'block';
                v.onloadedmetadata = function() {
                    document.getElementById('rn_start').max = v.duration;
                };
            };
            reader.readAsDataURL(file);
        }

        async function createGif() {
            if(!rawVideo) return;
            
            const btn = document.getElementById('btn_conv');
            const originalText = btn.innerText;
            btn.disabled = true;
            btn.innerText = "⏳ Rendering...";
            btn.style.opacity = "0.7";

            try {
                const r = await fetch('/api/tier2/exec/toolbox/' + handle, {
                    method: 'POST',
                    body: JSON.stringify({ 
                        pin: pin, 
                        action: 'exec_tool', 
                        payload: { 
                            tool_id: 'gif_maker', 
                            data: { 
                                sub_action: 'convert', 
                                video_data: rawVideo,
                                start: document.getElementById('rn_start').value,
                                duration: document.getElementById('rn_dur').value,
                                fps: document.getElementById('sel_fps').value,
                                width: document.getElementById('sel_width').value,
                                watermark: document.getElementById('txt_wm').value
                            } 
                        } 
                    })
                });
                
                const j = await r.json();
                
                if(j.image) {
                    const img = document.getElementById('final_gif');
                    const link = document.getElementById('down_link');
                    const res = document.getElementById('gif_result');
                    
                    img.src = j.image;
                    link.href = j.image;
                    link.download = "notifly_" + Date.now() + ".gif";
                    
                    res.style.display = 'block';
                    res.scrollIntoView({behavior: 'smooth'});
                } else {
                    alert("Error: " + j.msg);
                }

            } catch(e) {
                alert("Connection failed.");
                console.error(e);
            }

            btn.disabled = false;
            btn.innerText = originalText;
            btn.style.opacity = "1";
        }
        </script>
        """
    }
