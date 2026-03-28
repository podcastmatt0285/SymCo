"""
Tier 2 Module: Admin Toolbox (App Store UI)
"""
import os
import importlib.util
from pathlib import Path
import premium_tier_2
import json

TOOLS_DIR = Path("tools")

def init():
    TOOLS_DIR.mkdir(exist_ok=True)
    premium_tier_2.register_module("toolbox", "Admin Toolbox", entry_point)

def get_tools_list():
    tools = []
    if not TOOLS_DIR.exists(): return []
    for file in TOOLS_DIR.glob("*.py"):
        if file.name.startswith("_"): continue
        try:
            spec = importlib.util.spec_from_file_location(file.stem, file)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, "META"):
                tools.append({
                    "id": file.stem,
                    "name": mod.META.get("name", file.stem),
                    "icon": mod.META.get("icon", "🔧"),
                    "desc": mod.META.get("desc", "No description")
                })
        except: pass
    
    tools.sort(key=lambda x: x['name'].lower())
    return tools

def run_tool(tool_id, conn, handle, payload):
    file_path = TOOLS_DIR / f"{tool_id}.py"
    if not file_path.exists(): return {"success": False, "msg": "Tool not found"}
    try:
        spec = importlib.util.spec_from_file_location(tool_id, file_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.run(conn, handle, payload)
    except Exception as e:
        return {"success": False, "msg": f"Crash: {str(e)}"}

def entry_point(conn, handle, action, payload):
    if action == "render":
        tools = get_tools_list()
        return {"success": True, "html": render_widget(len(tools))}
    elif action == "list_tools":
        return {"success": True, "tools": get_tools_list()}
    elif action == "exec_tool":
        return run_tool(payload.get("tool_id"), conn, handle, payload.get("data", {}))
    return {"success": False, "msg": "Unknown Action"}

def render_widget(count):
    return f"""
    <div style="background:#222; border:1px solid #444; border-radius:8px; padding:15px; margin-top:20px; display:flex; align-items:center; justify-content:space-between;">
        <div><div style="color:#fff; font-weight:bold; font-size:14px;">🛠️ Admin Toolbox</div><div style="color:#888; font-size:11px;">{count} Apps Installed</div></div>
        <button onclick="openToolbox()" style="background:#eab308; color:#000; font-weight:bold; border:none; padding:8px 15px; border-radius:6px; cursor:pointer;">OPEN</button>
    </div>
    
    <div id="tb_modal" style="display:none; position:fixed; top:0; left:0; width:100vw; height:100vh; background:rgba(0,0,0,0.9); z-index:20000; align-items:center; justify-content:center; backdrop-filter: blur(5px);">
        <div style="background:#111; width:90%; max-width:420px; max-height:85vh; overflow-y:auto; border:1px solid #333; border-radius:20px; padding:25px; position:relative; box-shadow: 0 10px 40px rgba(0,0,0,0.8);">
            
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
                <h2 style="margin:0; color:#fff; font-size:18px; font-weight:800;" id="tb_title">Tier 2 Premium Tools</h2>
                <button onclick="closeToolbox()" style="background:#222; border:1px solid #333; border-radius:50%; width:30px; height:30px; color:#fff; display:flex; align-items:center; justify-content:center; cursor:pointer;">✕</button>
            </div>
            
            <div id="tb_list" style="display:grid; grid-template-columns: repeat(3, 1fr); gap: 15px;"></div>
        </div>
    </div>
    
    <script>
    async function openToolbox() {{
        const m = document.getElementById('tb_modal');
        if(m.parentElement !== document.body) document.body.appendChild(m);
        m.style.display = 'flex';
        document.getElementById('tb_title').innerText = 'Apps';
        
        const list = document.getElementById('tb_list');
        list.style.display = 'flex';
        list.innerHTML = '<div style="color:#666; width:100%; text-align:center; padding:20px;">Loading apps...</div>';
        
        const r = await fetch('/api/tier2/exec/toolbox/' + handle, {{ method: 'POST', body: JSON.stringify({{ pin: pin, action: 'list_tools' }}) }});
        const j = await r.json();
        
        if(j.success) {{
            list.style.display = 'grid';
            list.innerHTML = '';
            j.tools.forEach(t => {{
                list.innerHTML += `
                <div onclick="runTool('${{t.id}}', '${{t.name}}')" style="aspect-ratio: 1; background: #1a1a1a; border-radius: 18px; border: 1px solid #333; cursor: pointer; display: flex; flex-direction: column; align-items: center; justify-content: center; transition: transform 0.1s; padding: 10px;" onmousedown="this.style.transform='scale(0.95)'" onmouseup="this.style.transform='scale(1)'" onmouseleave="this.style.transform='scale(1)'">
                    <div style="font-size: 32px; margin-bottom: 8px;">${{t.icon}}</div>
                    <div style="color: #ccc; font-weight: 500; font-size: 11px; text-align: center; line-height: 1.2; width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${{t.name}}</div>
                </div>`;
            }});
        }}
    }}
    
    function closeToolbox() {{ document.getElementById('tb_modal').style.display = 'none'; }}
    
    async function runTool(id, name) {{
        const list = document.getElementById('tb_list');
        list.style.display = 'block'; 
        list.innerHTML = '<div style="text-align:center; padding:40px; color:#eab308"><div style="font-size:30px;margin-bottom:10px">⏳</div>Opening...</div>';
        
        const r = await fetch('/api/tier2/exec/toolbox/' + handle, {{ method: 'POST', body: JSON.stringify({{ pin: pin, action: 'exec_tool', payload: {{ tool_id: id }} }}) }});
        const j = await r.json();
        
        if (j.html) {{
            document.getElementById('tb_title').innerText = name;
            list.innerHTML = j.html;
            
            // --- FIX IS HERE: Forces Scripts to Run ---
            Array.from(list.querySelectorAll("script")).forEach( oldScript => {{
                const newScript = document.createElement("script");
                Array.from(oldScript.attributes).forEach( attr => newScript.setAttribute(attr.name, attr.value) );
                newScript.appendChild(document.createTextNode(oldScript.innerHTML));
                oldScript.parentNode.replaceChild(newScript, oldScript);
            }});
            
        }} else {{
            alert(j.msg);
            if(j.reload) location.reload();
            else openToolbox(); 
        }}
    }}
    </script>
    """
