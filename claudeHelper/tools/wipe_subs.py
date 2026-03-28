"""
Tool: Wipe Subscribers
Description: Removes all subscribers for the current channel.
"""
import time

# Metadata used by the Toolbox UI
META = {
    "name": "Subscriber Wipe",
    "icon": "🧹",
    "desc": "DANGER: Removes all subscribers immediately."
}

def run(conn, handle, payload):
    # This function is called by toolbox.py
    cursor = conn.cursor()
    
    # Logic
    cursor.execute("SELECT COUNT(*) FROM subs WHERE handle=?", (handle,))
    count = cursor.fetchone()[0]
    
    if count == 0:
        return {"success": False, "msg": "No subscribers to wipe."}
    
    cursor.execute("DELETE FROM subs WHERE handle=?", (handle,))
    conn.commit()
    
    return {
        "success": True, 
        "msg": f"Wiped {count} subscribers successfully.",
        "reload": True # Tells UI to reload page
    }
