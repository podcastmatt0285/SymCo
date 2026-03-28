"""
Tool: Wipe History
Description: Clears only broadcast logs (sends/opens).
"""
META = {
    "name": "Wipe Broadcasts",
    "icon": "📨",
    "desc": "Deletes broadcast logs & notification stats."
}

def run(conn, handle, payload):
    cursor = conn.cursor()
    # 1. Delete events linked to broadcasts
    cursor.execute("""
        DELETE FROM analytics_events 
        WHERE type IN ('notif', 'dismiss', 'fail') 
        AND ref_id IN (SELECT bid FROM broadcast_history WHERE handle=?)
    """, (handle,))
    
    # 2. Delete the broadcasts
    cursor.execute("DELETE FROM broadcast_history WHERE handle=?", (handle,))
    conn.commit()
    
    return {
        "success": True, 
        "msg": "Broadcast history wiped.",
        "reload": True
    }
