"""
Portal Dashboard Module (CRM)
Allows Premium Admins to manage, tag, and grade their subscribers.
"""
import sqlite3
import json
import time

def init_db(cursor):
    """
    Extends the subscriber profile table with Admin-Only columns.
    We use try/except blocks to safely add columns if they don't exist (Migration).
    """
    # 1. Status (Silver, Gold, etc)
    try:
        cursor.execute("ALTER TABLE channel_subscriber_profiles ADD COLUMN status TEXT DEFAULT 'Silver'")
    except sqlite3.OperationalError: pass
    
    # 2. Private Notes
    try:
        cursor.execute("ALTER TABLE channel_subscriber_profiles ADD COLUMN admin_notes TEXT DEFAULT ''")
    except sqlite3.OperationalError: pass
    
    # 3. Tags (JSON list)
    try:
        cursor.execute("ALTER TABLE channel_subscriber_profiles ADD COLUMN admin_tags TEXT DEFAULT '[]'")
    except sqlite3.OperationalError: pass
    
    # 4. Blocked Status
    try:
        cursor.execute("ALTER TABLE channel_subscriber_profiles ADD COLUMN is_blocked INTEGER DEFAULT 0")
    except sqlite3.OperationalError: pass

def get_subscribers(db, handle):
    """Fetches all profiles for a handle to populate the CRM."""
    rows = db.query("SELECT * FROM channel_subscriber_profiles WHERE handle = ?", (handle,))
    return [dict(r) for r in rows]

def update_subscriber_meta(db, data):
    """Updates the admin-side metadata for a subscriber."""
    endpoint = data.get('endpoint')
    handle = data.get('handle')
    
    # Fields to update
    status = data.get('status')
    notes = data.get('notes')
    tags = json.dumps(data.get('tags', []))
    blocked = 1 if data.get('blocked') else 0
    
    if not endpoint or not handle:
        return {"success": False, "msg": "Missing identifiers"}

    try:
        # We only update the admin columns, leaving username/bio alone
        db.execute("""
            UPDATE channel_subscriber_profiles 
            SET status=?, admin_notes=?, admin_tags=?, is_blocked=?
            WHERE endpoint=? AND handle=?
        """, (status, notes, tags, blocked, endpoint, handle))
        
        # If blocked, we should probably remove them from the active 'subs' table too
        # so they stop receiving pushes immediately.
        if blocked:
            db.execute("DELETE FROM subs WHERE endpoint=? AND handle=?", (endpoint, handle))
            
        return {"success": True, "msg": "Subscriber Updated"}
    except Exception as e:
        return {"success": False, "msg": str(e)}

def delete_subscriber(db, endpoint, handle):
    """Permanently removes a subscriber profile."""
    try:
        db.execute("DELETE FROM channel_subscriber_profiles WHERE endpoint=? AND handle=?", (endpoint, handle))
        return {"success": True, "msg": "Profile Deleted"}
    except Exception as e:
        return {"success": False, "msg": str(e)}

def render_dashboard(handle, pin):
    """Renders the CRM Dashboard HTML."""
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Subscriber CRM - {handle}</title>
    <style>
        :root {{ --bg: #0f0f0f; --card: #1a1a1a; --text: #e0e0e0; --primary: #eab308; --border: #333; }}
        body {{ background: var(--bg); color: var(--text); font-family: system-ui, sans-serif; margin:0; padding:20px; }}
        
        /* Layout */
        .header {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:20px; border-bottom:1px solid var(--border); padding-bottom:20px; }}
        h1 {{ margin:0; color: var(--primary); font-size: 20px; text-transform: uppercase; letter-spacing: 1px; }}
        
        /* Grid */
        .sub-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 15px; }}
        
        /* Card */
        .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 15px; position:relative; transition:0.2s; }}
        .card:hover {{ border-color: var(--primary); }}
        .card-head {{ display:flex; gap:10px; align-items:center; margin-bottom:10px; }}
        .av {{ width:40px; height:40px; background:#333; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:20px; }}
        .names {{ flex-grow:1; }}
        .username {{ font-weight:bold; color:#fff; }}
        .status-badge {{ font-size:10px; padding:2px 6px; border-radius:4px; font-weight:bold; text-transform:uppercase; margin-left:5px; }}
        
        /* Status Colors */
        .st-Bronze {{ background: #7c5443; color:#fff; }}
        .st-Silver {{ background: #71717a; color:#fff; }}
        .st-Gold {{ background: #eab308; color:#000; }}
        .st-Platinum {{ background: #e0f2fe; color:#0c4a6e; }}
        .st-Diamond {{ background: linear-gradient(45deg, #06b6d4, #3b82f6); color:#fff; }}
        .st-Blocked {{ background: #ef4444; color:#fff; }}

        .bio {{ font-size:12px; color:#888; margin-bottom:10px; font-style:italic; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
        
        /* Controls */
        .actions {{ display:flex; gap:5px; margin-top:10px; border-top:1px solid #333; padding-top:10px; }}
        .act-btn {{ flex:1; background:#222; border:1px solid #333; color:#ccc; padding:5px; border-radius:4px; cursor:pointer; font-size:11px; }}
        .act-btn:hover {{ background:#333; color:#fff; }}
        .btn-del {{ color:#f87171; }}
        
        /* Modal */
        .modal {{ display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.8); z-index:100; align-items:center; justify-content:center; }}
        .m-box {{ background:#1a1a1a; width:90%; max-width:500px; padding:25px; border-radius:12px; border:1px solid var(--primary); max-height:90vh; overflow-y:auto; }}
        label {{ display:block; color:#888; font-size:11px; margin-top:10px; margin-bottom:4px; text-transform:uppercase; }}
        input, select, textarea {{ width:100%; background:#111; border:1px solid #333; color:#fff; padding:10px; border-radius:6px; box-sizing:border-box; }}
        .tag-container {{ display:flex; flex-wrap:wrap; gap:5px; margin-top:5px; }}
        .tag {{ background:#333; padding:2px 8px; border-radius:10px; font-size:11px; display:flex; align-items:center; gap:5px; }}
        .tag span {{ cursor:pointer; color:#f87171; font-weight:bold; }}
        
        /* Warning Box */
        .warning-box {{ background:#1a1a1a; border:1px solid #fbbf24; border-left:4px solid #fbbf24; padding:12px; border-radius:6px; margin-bottom:15px; font-size:11px; line-height:1.6; }}
        .warning-box strong {{ color:#fbbf24; display:block; margin-bottom:8px; font-size:12px; }}
        .warning-box ul {{ margin:8px 0; padding-left:20px; color:#aaa; }}
        .warning-box ul li {{ margin:4px 0; }}
    </style>
</head>
<body>

<div class="header">
    <h1>Subscriber CRM</h1>
    <div style="display:flex; gap:10px">
        <button onclick="openBroadcastModal()" style="background:var(--primary); border:none; color:#000; padding:8px 16px; border-radius:6px; cursor:pointer; font-weight:bold;">📢 Send to List</button>
        <button onclick="window.close()" style="background:#333; border:1px solid #444; color:#fff; padding:8px 16px; border-radius:6px; cursor:pointer;">Close Tab</button>
    </div>
</div>

<div style="background:#151515; padding:15px; border-radius:8px; border:1px solid #333; margin-bottom:20px;">
    <div style="display:flex; flex-wrap:wrap; gap:20px; align-items:center;">
        <div>
            <label style="margin-top:0">Filter by Tier:</label>
            <div style="display:flex; gap:10px; margin-top:5px;">
                <label style="display:flex;gap:4px;cursor:pointer"><input type="checkbox" class="f-tier" value="Bronze" checked onchange="applyFilters()"> Bronze</label>
                <label style="display:flex;gap:4px;cursor:pointer"><input type="checkbox" class="f-tier" value="Silver" checked onchange="applyFilters()"> Silver</label>
                <label style="display:flex;gap:4px;cursor:pointer"><input type="checkbox" class="f-tier" value="Gold" checked onchange="applyFilters()"> Gold</label>
                <label style="display:flex;gap:4px;cursor:pointer"><input type="checkbox" class="f-tier" value="Platinum" checked onchange="applyFilters()"> Platinum</label>
                <label style="display:flex;gap:4px;cursor:pointer"><input type="checkbox" class="f-tier" value="Diamond" checked onchange="applyFilters()"> Diamond</label>
            </div>
        </div>
        <div style="flex-grow:1; max-width:400px;">
            <label style="margin-top:0">Filter by Tags (comma separated):</label>
            <div style="display:flex; gap:5px; margin-top:5px;">
                <select id="f_tag_mode" style="width:80px;" onchange="applyFilters()">
                    <option value="any">Any</option>
                    <option value="all">All</option>
                    <option value="none">None</option>
                </select>
                <input id="f_tags" placeholder="vip, friend, new..." onkeyup="applyFilters()" style="margin:0;">
            </div>
        </div>
        <div style="margin-left:auto; text-align:right;">
            <div style="font-size:10px; color:#888;">VISIBLE USERS</div>
            <div id="count_display" style="font-size:20px; font-weight:bold; color:var(--primary)">0</div>
        </div>
    </div>
</div>

<div id="grid" class="sub-grid">
    <div style="color:#666">Loading Profiles...</div>
</div>

<div id="editModal" class="modal">
    <div class="m-box">
        <h2 style="margin:0 0 15px 0; color:var(--primary)">Edit Subscriber</h2>
        <input type="hidden" id="e_endpoint">
        
        <label>Status Tier</label>
        <select id="e_status">
            <option value="Bronze">Bronze (Downgrade)</option>
            <option value="Silver">Silver (Default)</option>
            <option value="Gold">Gold (Upgrade)</option>
            <option value="Platinum">Platinum (Favorite)</option>
            <option value="Diamond">Diamond (Top Tier)</option>
        </select>
        
        <label>Private Notes</label>
        <textarea id="e_notes" rows="3" placeholder="Internal notes about this user..."></textarea>
        
        <label>Tags (Press Enter)</label>
        <input id="e_tag_input" placeholder="Add tag...">
        <div id="e_tags" class="tag-container"></div>
        
        <div style="margin-top:20px; padding-top:15px; border-top:1px solid #333; display:flex; justify-content:space-between; align-items:center;">
            <label style="margin:0; display:flex; align-items:center; gap:10px; color:#f87171; cursor:pointer;">
                <input type="checkbox" id="e_block"> BLOCK USER
            </label>
            <button onclick="saveChanges()" style="background:var(--primary); color:#000; border:none; padding:10px 20px; border-radius:6px; font-weight:bold; cursor:pointer;">SAVE CHANGES</button>
        </div>
        <button onclick="closeModal()" style="margin-top:10px; width:100%; background:transparent; border:none; color:#666; cursor:pointer;">Cancel</button>
    </div>
</div>

<div id="broadcastModal" class="modal">
    <div class="m-box">
        <h2 style="margin:0 0 15px 0; color:var(--primary)">Targeted Broadcast</h2>
        
        <div class="warning-box">
            <strong>🚨 Important Note:</strong>
            Users who are in <code>subs</code> table but NOT in <code>channel_subscriber_profiles</code>:
            <ul>
                <li>Will default to <strong>Silver</strong> tier</li>
                <li>Will have <strong>no tags</strong></li>
                <li>Will <strong>NOT be blocked</strong></li>
                <li>Should receive broadcasts when "Silver" is checked</li>
            </ul>
            This is correct behavior since they're valid subscribers who just haven't customized their profile yet.
        </div>
        
        <div style="font-size:12px; color:#aaa; margin-bottom:15px; padding:10px; background:#151515; border-radius:6px; border:1px solid #333;">
            Sending to <span id="b_target_count" style="color:#fff; font-weight:bold; font-size:14px;">0</span> subscribers based on current filters.
        </div>
        
        <label>Title</label>
        <input id="b_title" placeholder="Alert Header">
        
        <label>Message</label>
        <textarea id="b_body" rows="3" placeholder="Content..."></textarea>
        
        <label>Link URL</label>
        <input id="b_url" placeholder="https://...">
        
        <div style="display:flex; gap:10px">
            <div style="flex:1">
                <label>Icon URL</label>
                <input id="b_icon" value="https://cdn-icons-png.flaticon.com/512/1156/1156948.png">
            </div>
            <div style="flex:1">
                <label>Image URL</label>
                <input id="b_image" placeholder="https://...">
            </div>
        </div>

        <button onclick="sendBroadcast()" style="margin-top:20px; width:100%; background:var(--primary); color:#000; border:none; padding:12px; border-radius:6px; font-weight:bold; cursor:pointer;">SEND NOTIFICATION</button>
        <button onclick="closeBroadcastModal()" style="margin-top:10px; width:100%; background:transparent; border:none; color:#666; cursor:pointer;">Cancel</button>
    </div>
</div>

<script>
const HANDLE = "{handle}";
const PIN = "{pin}";
let subscribers = [];
let currentTags = [];
let filteredCount = 0;

async function load() {{
    const r = await fetch('/api/crm/list/'+HANDLE+'?pin='+PIN);
    subscribers = await r.json();
    applyFilters();
}}

function getActiveFilters() {{
    // 1. Tiers
    const tiers = Array.from(document.querySelectorAll('.f-tier:checked')).map(cb => cb.value);
    
    // 2. Tags
    const tagInput = document.getElementById('f_tags').value.toLowerCase();
    const tags = tagInput.split(',').map(t => t.trim()).filter(t => t);
    const tagMode = document.getElementById('f_tag_mode').value;
    
    return {{ tiers, tags, tagMode }};
}}

function applyFilters() {{
    const {{ tiers, tags, tagMode }} = getActiveFilters();
    const grid = document.getElementById('grid');
    grid.innerHTML = '';
    
    let visible = 0;

    if(subscribers.length === 0) {{
        grid.innerHTML = '<div style="grid-column:1/-1; text-align:center; color:#444; padding:50px;">No profiles found.<br>Tell your subscribers to use the Portal!</div>';
        return;
    }}

    subscribers.forEach((sub, idx) => {{
        // --- Filter Logic ---
        const subStatus = sub.status || 'Silver';
        if (!tiers.includes(subStatus)) return;
        
        if (tags.length > 0) {{
            const subTags = JSON.parse(sub.admin_tags || '[]').map(t => t.toLowerCase());
            if (tagMode === 'any' && !tags.some(t => subTags.includes(t))) return;
            if (tagMode === 'all' && !tags.every(t => subTags.includes(t))) return;
            if (tagMode === 'none' && tags.some(t => subTags.includes(t))) return;
        }}
        // --------------------

        visible++;
        const tagsHtml = JSON.parse(sub.admin_tags || '[]').map(t => `<span style="color:#888; font-size:10px;">#${{t}}</span>`).join(' ');
        const isBlocked = sub.is_blocked ? '<span style="color:red; font-weight:bold;">[BLOCKED]</span>' : '';
        
        grid.innerHTML += `
        <div class="card" style="opacity: ${{sub.is_blocked ? 0.5 : 1}}">
            <div class="card-head">
                <div class="av">👤</div>
                <div class="names">
                    <div class="username">${{sub.username}} ${{isBlocked}} <span class="status-badge st-${{sub.status}}">${{sub.status}}</span></div>
                    <div style="font-size:10px; color:#555;">ID: ...${{sub.endpoint.slice(-8)}}</div>
                </div>
            </div>
            <div class="bio">"${{sub.bio || 'No bio'}}"</div>
            <div style="font-size:11px; color:#aaa; min-height:16px;">${{tagsHtml}}</div>
            <div class="actions">
                <button class="act-btn" onclick="openEdit(${{idx}})">✎ Manage</button>
                <button class="act-btn btn-del" onclick="deleteSub('${{sub.endpoint}}')">🗑 Delete</button>
            </div>
        </div>
        `;
    }});
    
    document.getElementById('count_display').innerText = visible;
    filteredCount = visible;
}}

function openEdit(idx) {{
    const sub = subscribers[idx];
    document.getElementById('e_endpoint').value = sub.endpoint;
    document.getElementById('e_status').value = sub.status || 'Silver';
    document.getElementById('e_notes').value = sub.admin_notes || '';
    document.getElementById('e_block').checked = sub.is_blocked == 1;
    
    currentTags = JSON.parse(sub.admin_tags || '[]');
    renderTags();
    
    document.getElementById('editModal').style.display = 'flex';
}}

function closeModal() {{
    document.getElementById('editModal').style.display = 'none';
}}

function renderTags() {{
    const cont = document.getElementById('e_tags');
    cont.innerHTML = '';
    currentTags.forEach((t, i) => {{
        cont.innerHTML += `<div class="tag">${{t}} <span onclick="removeTag(${{i}})">×</span></div>`;
    }});
}}

document.getElementById('e_tag_input').addEventListener('keypress', function (e) {{
    if (e.key === 'Enter') {{
        const val = this.value.trim();
        if(val && !currentTags.includes(val)) {{
            currentTags.push(val);
            renderTags();
        }}
        this.value = '';
    }}
}});

function removeTag(i) {{
    currentTags.splice(i, 1);
    renderTags();
}}

async function saveChanges() {{
    const endpoint = document.getElementById('e_endpoint').value;
    const payload = {{
        handle: HANDLE,
        pin: PIN,
        endpoint: endpoint,
        status: document.getElementById('e_status').value,
        notes: document.getElementById('e_notes').value,
        tags: currentTags,
        blocked: document.getElementById('e_block').checked
    }};
    
    await fetch('/api/crm/update', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify(payload)
    }});
    
    closeModal();
    load();
}}

async function deleteSub(endpoint) {{
    if(!confirm("Permanently delete this profile?")) return;
    await fetch('/api/crm/delete', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{handle: HANDLE, pin: PIN, endpoint: endpoint}})
    }});
    load();
}}

function openBroadcastModal() {{
    if(filteredCount === 0) return alert("No subscribers match your filters.");
    document.getElementById('b_target_count').innerText = filteredCount;
    document.getElementById('broadcastModal').style.display = 'flex';
}}

function closeBroadcastModal() {{
    document.getElementById('broadcastModal').style.display = 'none';
}}

async function sendBroadcast() {{
    const title = document.getElementById('b_title').value;
    const body = document.getElementById('b_body').value;
    if(!title || !body) return alert("Title and Message required.");
    
    const filters = getActiveFilters();
    
    const payload = {{
        pin: PIN,
        title: title,
        body: body,
        url: document.getElementById('b_url').value,
        icon: document.getElementById('b_icon').value,
        image: document.getElementById('b_image').value,
        filters: {{
            tiers: filters.tiers,
            tags: filters.tags,
            tag_mode: filters.tagMode
        }}
    }};
    
    const btn = document.querySelector('#broadcastModal button');
    btn.innerText = "Sending...";
    btn.disabled = true;
    
    const r = await fetch('/api/broadcast/'+HANDLE, {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify(payload)
    }});
    
    const j = await r.json();
    closeBroadcastModal();
    btn.innerText = "SEND NOTIFICATION";
    btn.disabled = false;
    
    if(j.success) alert("✅ Queued " + j.count + " notifications!");
    else alert("❌ Error: " + j.error);
}}

load();
</script>
</body>
</html>
"""
