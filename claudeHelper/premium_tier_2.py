"""
Premium Tier 2 Gateway for NotiFly
Acts as the central registry and access controller for advanced Tier 2 admin modules.
Future modules should register themselves here to be accessible via the API.
"""
import sqlite3
import json
import time

# --- MODULE REGISTRY ---
# Future modules will register here.
# Format: { "module_key": { "name": "Display Name", "entry_point": function_reference } }
_MODULE_REGISTRY = {}

def register_module(key, name, entry_point_func):
    """
    Registers a new Tier 2 module.
    entry_point_func should accept (conn, handle, action, payload) and return a dict.
    """
    _MODULE_REGISTRY[key] = {
        "name": name,
        "entry_point": entry_point_func
    }
    print(f"[Tier 2] Registered module: {name} ({key})")

# --- DATABASE INIT ---
def init_db(conn):
    c = conn.cursor()
    
    # Table to track which channels have Tier 2 Access
    c.execute("""CREATE TABLE IF NOT EXISTS tier_2_access (
        handle TEXT PRIMARY KEY,
        granted_at INTEGER,
        status TEXT DEFAULT 'active' -- 'active', 'suspended'
    )""")
    
    # Table to store configuration/settings for specific modules per channel
    # This allows future modules to save state without needing their own tables immediately
    c.execute("""CREATE TABLE IF NOT EXISTS tier_2_config (
        handle TEXT,
        module_key TEXT,
        settings_json TEXT,
        updated_at INTEGER,
        PRIMARY KEY (handle, module_key),
        FOREIGN KEY(handle) REFERENCES tier_2_access(handle) ON DELETE CASCADE
    )""")
    
    conn.commit()

# --- ACCESS CONTROL ---

def grant_tier_2(conn, handle):
    """Grants Tier 2 status to a specific channel handle."""
    c = conn.cursor()
    try:
        c.execute("INSERT OR REPLACE INTO tier_2_access (handle, granted_at, status) VALUES (?, ?, ?)",
                  (handle, int(time.time()), 'active'))
        conn.commit()
        return {"success": True, "msg": f"Tier 2 Access Granted to {handle}"}
    except Exception as e:
        return {"success": False, "msg": str(e)}

def revoke_tier_2(conn, handle):
    """Revokes Tier 2 status and wipes module configs."""
    c = conn.cursor()
    c.execute("DELETE FROM tier_2_config WHERE handle=?", (handle,))
    c.execute("DELETE FROM tier_2_access WHERE handle=?", (handle,))
    conn.commit()
    return {"success": True, "msg": f"Tier 2 Access Revoked for {handle}"}

def check_tier_2_access(conn, handle):
    """Returns True if the handle has active Tier 2 access."""
    c = conn.cursor()
    # Force tuple mode for simple queries is safer if the factory changes elsewhere
    c.row_factory = None 
    c.execute("SELECT status FROM tier_2_access WHERE handle=?", (handle,))
    row = c.fetchone()
    if row and row[0] == 'active':
        return True
    return False

def get_all_tier_2_channels(conn):
    """Returns a list of all handles with Tier 2 access."""
    c = conn.cursor()
    c.row_factory = None
    c.execute("SELECT handle, granted_at, status FROM tier_2_access")
    rows = c.fetchall()
    return [{"handle": r[0], "granted_at": r[1], "status": r[2]} for r in rows]

# --- CONFIGURATION MANAGEMENT ---

def get_module_config(conn, handle, module_key):
    """Retrieves the configuration dict for a specific module."""
    c = conn.cursor()
    c.row_factory = None
    c.execute("SELECT settings_json FROM tier_2_config WHERE handle=? AND module_key=?", (handle, module_key))
    row = c.fetchone()
    if row:
        try:
            return json.loads(row[0])
        except:
            return {}
    return {}

def set_module_config(conn, handle, module_key, config_dict):
    """Saves configuration for a module."""
    if not check_tier_2_access(conn, handle):
        return {"success": False, "msg": "Tier 2 Access Required"}
        
    c = conn.cursor()
    json_str = json.dumps(config_dict)
    c.execute("INSERT OR REPLACE INTO tier_2_config (handle, module_key, settings_json, updated_at) VALUES (?, ?, ?, ?)",
              (handle, module_key, json_str, int(time.time())))
    conn.commit()
    return {"success": True, "msg": "Configuration Saved"}

# --- GATEWAY / DISPATCHER ---

def list_available_modules():
    """Returns list of registered modules for the frontend/admin panel."""
    return [{"key": k, "name": v["name"]} for k, v in _MODULE_REGISTRY.items()]

def execute_module(conn, handle, module_key, action, payload=None):
    """
    The main gateway function.
    1. Verifies Tier 2 Access.
    2. Checks if module exists.
    3. Dispatches the command to the module's entry point.
    """
    if not check_tier_2_access(conn, handle):
        return {"success": False, "msg": "Access Denied: Tier 2 Subscription Required."}
    
    if module_key not in _MODULE_REGISTRY:
        return {"success": False, "msg": f"Module '{module_key}' not found or not loaded."}
    
    module = _MODULE_REGISTRY[module_key]
    entry_point = module.get("entry_point")
    
    if not callable(entry_point):
        return {"success": False, "msg": "Module entry point is invalid."}
        
    try:
        # Pass the DB connection, handle, specific action, and data payload to the module
        return entry_point(conn, handle, action, payload or {})
    except Exception as e:
        print(f"[Tier 2 Gateway Error] {module_key} crashed: {e}")
        return {"success": False, "msg": f"Module Error: {str(e)}"}
