"""
Tool: Tally.so Forms Manager
Description: Embed up to 5 Tally.so forms on your channel page.
"""
import sqlite3
import json

META = {
    "name": "Tally Forms",
    "icon": "📋",
    "desc": "Embed custom forms on your page."
}

# --- Database & Admin Logic ---
def run(conn, handle, payload):
    action = payload.get('sub_action')
    
    # Ensure table exists
    conn.execute("""CREATE TABLE IF NOT EXISTS channel_tally (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        handle TEXT NOT NULL,
        form_url TEXT NOT NULL,
        form_title TEXT NOT NULL,
        is_active INTEGER DEFAULT 1,
        display_order INTEGER DEFAULT 0
    )""")
    
    if action == 'save':
        forms = payload.get('forms', [])
        
        print(f"[TALLY DEBUG] Saving {len(forms)} forms for {handle}")
        
        # Validate max 5 forms
        if len(forms) > 5:
            return {"success": False, "msg": "Maximum 5 forms allowed"}
        
        # Clear existing forms
        conn.execute("DELETE FROM channel_tally WHERE handle=?", (handle,))
        print(f"[TALLY DEBUG] Cleared old forms")
        
        # Insert new forms
        for idx, form in enumerate(forms):
            url = form.get('url', '').strip()
            title = form.get('title', '').strip()
            active = 1 if form.get('active') else 0
            
            print(f"[TALLY DEBUG] Form {idx}: url={url}, title={title}, active={active}")
            
            if url and title:
                conn.execute("""
                    INSERT INTO channel_tally (handle, form_url, form_title, is_active, display_order)
                    VALUES (?, ?, ?, ?, ?)
                """, (handle, url, title, active, idx))
                print(f"[TALLY DEBUG] Inserted form {idx}")
        
        conn.commit()
        print(f"[TALLY DEBUG] Committed to database")
        return {"success": True, "msg": "Forms updated!", "reload": True}
    
    # Render Admin UI
    cursor = conn.execute("SELECT * FROM channel_tally WHERE handle=? ORDER BY display_order", (handle,))
    forms = [dict(row) for row in cursor.fetchall()]
    
    forms_json = json.dumps(forms)
    
    html = f"""
    <div style="background:#1a1a1a; padding:15px; border-radius:8px; border:1px solid #333;">
        <h3 style="color:#eab308; margin-top:0;">📋 Tally Forms</h3>
        <p style="font-size:12px; color:#aaa; margin-bottom:15px;">Embed up to 5 custom forms. Paste your Tally.so form URLs below.</p>
        
        <div id="forms_list" style="margin-bottom:15px;"></div>
        
        <button onclick="addForm()" id="add_btn" style="width:100%; background:#333; color:#fff; border:1px dashed #444; padding:10px; cursor:pointer; margin-bottom:10px;">+ Add Form</button>
        <button onclick="saveForms()" style="width:100%; background:#eab308; color:#000; font-weight:bold; padding:10px; border:none; cursor:pointer;">SAVE FORMS</button>
        <div id="msg" style="margin-top:10px; font-size:12px;"></div>
    </div>
    
    <script>
    let forms = {forms_json};
    
    function renderForms() {{
        const container = document.getElementById('forms_list');
        const addBtn = document.getElementById('add_btn');
        
        if (forms.length === 0) {{
            container.innerHTML = '<div style="text-align:center; padding:20px; color:#666; font-size:12px;">No forms added yet</div>';
            addBtn.style.display = 'block';
            return;
        }}
        
        if (forms.length >= 5) {{
            addBtn.style.display = 'none';
        }} else {{
            addBtn.style.display = 'block';
        }}
        
        container.innerHTML = '';
        forms.forEach((form, idx) => {{
            container.innerHTML += `
                <div style="background:#222; border:1px solid #333; border-radius:6px; padding:12px; margin-bottom:10px;">
                    <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:8px;">
                        <div style="font-weight:bold; font-size:13px; color:#fff;">Form ${{idx + 1}}</div>
                        <div style="display:flex; gap:8px; align-items:center;">
                            <label style="font-size:11px; color:#888; margin:0;">Active</label>
                            <label class="switch" style="margin:0;">
                                <input type="checkbox" id="active_${{idx}}" ${{form.active ? 'checked' : ''}}>
                                <span class="slider"></span>
                            </label>
                            <button onclick="removeForm(${{idx}})" style="background:#f87171; color:#fff; border:none; padding:5px 10px; border-radius:4px; cursor:pointer; font-size:11px;">✕</button>
                        </div>
                    </div>
                    <input 
                        id="title_${{idx}}"
                        value="${{form.title || ''}}" 
                        placeholder="Form Title (e.g. 'Contact Us')" 
                        style="width:100%; background:#111; color:#fff; padding:8px; border:1px solid #333; margin-bottom:6px; border-radius:4px; font-size:12px;">
                    <input 
                        id="url_${{idx}}"
                        value="${{form.url || ''}}" 
                        placeholder="Tally Form URL (e.g. https://tally.so/r/xxxxx)"
                        style="width:100%; background:#111; color:#fff; padding:8px; border:1px solid #333; border-radius:4px; font-size:11px; font-family:monospace;">
                </div>
            `;
        }});
    }}
    
    function addForm() {{
        if (forms.length >= 5) {{
            alert('Maximum 5 forms allowed');
            return;
        }}
        forms.push({{ url: '', title: '', active: true }});
        renderForms();
    }}
    
    function removeForm(idx) {{
        if (confirm('Remove this form?')) {{
            forms.splice(idx, 1);
            renderForms();
        }}
    }}
    
    async function saveForms() {{
        const msg = document.getElementById('msg');
        const btn = event.target;
        btn.disabled = true;
        btn.innerText = 'Saving...';
        msg.innerHTML = '';
        
        // Collect current values from DOM
        const validForms = [];
        for (let i = 0; i < forms.length; i++) {{
            const titleEl = document.getElementById('title_' + i);
            const urlEl = document.getElementById('url_' + i);
            const activeEl = document.getElementById('active_' + i);
            
            if (!titleEl || !urlEl) continue;
            
            const url = urlEl.value.trim();
            const title = titleEl.value.trim();
            const active = activeEl ? activeEl.checked : true;
            
            // Skip completely empty forms
            if (!url && !title) continue;
            
            // If partially filled, require both
            if (!url || !title) {{
                msg.innerHTML = '<div style="color:#f87171;">Form ' + (i + 1) + ' needs both title and URL</div>';
                btn.disabled = false;
                btn.innerText = 'SAVE FORMS';
                return;
            }}
            
            if (!url.includes('tally.so')) {{
                msg.innerHTML = '<div style="color:#f87171;">Invalid Tally.so URL in form ' + (i + 1) + '</div>';
                btn.disabled = false;
                btn.innerText = 'SAVE FORMS';
                return;
            }}
            
            validForms.push({{
                url: url,
                title: title,
                active: active
            }});
        }}
        
        try {{
            const r = await fetch('/api/tier2/exec/toolbox/' + handle, {{
                method: 'POST',
                body: JSON.stringify({{ 
                    pin: pin, 
                    action: 'exec_tool', 
                    payload: {{ 
                        tool_id: 'tally', 
                        data: {{ 
                            sub_action: 'save', 
                            forms: validForms 
                        }} 
                    }} 
                }})
            }});
            
            const j = await r.json();
            
            if (j.success) {{
                msg.innerHTML = '<div style="color:#4ade80;">✅ Forms updated!</div>';
                setTimeout(() => location.reload(), 1500);
            }} else {{
                msg.innerHTML = '<div style="color:#f87171;">❌ ' + (j.msg || 'Unknown error') + '</div>';
                btn.disabled = false;
                btn.innerText = 'SAVE FORMS';
            }}
        }} catch(e) {{
            msg.innerHTML = '<div style="color:#f87171;">Connection failed</div>';
            btn.disabled = false;
            btn.innerText = 'SAVE FORMS';
        }}
    }}
    
    renderForms();
    </script>
    """
    
    return {"success": True, "html": html}

# --- Public Render Logic (Called by app.py) ---
def render_public(conn, handle):
    """Render active forms on the public channel page"""
    try:
        cursor = conn.execute("""
            SELECT form_url, form_title 
            FROM channel_tally 
            WHERE handle=? AND is_active=1 
            ORDER BY display_order
        """, (handle,))
        
        forms = cursor.fetchall()
        
        if not forms:
            return ""
        
        html = """
        <div style="margin-top:30px; border-top:1px dashed #333; padding-top:20px;">
            <h3 style="color:var(--primary); font-size:14px; margin:0 0 15px 0;">📋 FORMS</h3>
        """
        
        for form in forms:
            form_url = form[0]
            form_title = form[1]
            
            # Extract form ID from URL (supports /r/ and /embed/ formats)
            # https://tally.so/r/xxxxx or https://tally.so/embed/xxxxx
            if '/r/' in form_url:
                form_id = form_url.split('/r/')[-1].split('?')[0]
            elif '/embed/' in form_url:
                form_id = form_url.split('/embed/')[-1].split('?')[0]
            else:
                # Fallback - just use last part
                form_id = form_url.split('/')[-1].split('?')[0]
            
            html += f"""
            <details style="background:#1a1a1a; border:1px solid #333; border-radius:8px; padding:15px; margin-bottom:10px;">
                <summary style="cursor:pointer; font-weight:bold; color:#fff; font-size:13px; list-style:none;">
                    <span style="color:var(--primary);">▶</span> {form_title}
                </summary>
                <div style="margin-top:15px;">
                    <iframe 
                        src="https://tally.so/embed/{form_id}?alignLeft=1&hideTitle=1&transparentBackground=1&dynamicHeight=1" 
                        loading="lazy" 
                        width="100%" 
                        height="500" 
                        frameborder="0" 
                        marginheight="0" 
                        marginwidth="0" 
                        title="{form_title}"
                        style="border-radius:6px;">
                    </iframe>
                </div>
            </details>
            """
        
        html += """
        </div>
        """
        
        return html
        
    except Exception as e:
        print(f"[Tally Render Error] {e}")
        return ""
