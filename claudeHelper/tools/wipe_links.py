"""
Tool: Wipe Links
Description: Clears only link click analytics.
"""
META = {
    "name": "Wipe Click Stats",
    "icon": "🖱️",
    "desc": "Resets click counters for all links."
}

def run(conn, handle, payload):
    cursor = conn.cursor()
    # Delete 'link' events for this channel
    cursor.execute("""
        DELETE FROM analytics_events 
        WHERE type='link' 
        AND ref_id IN (SELECT CAST(id AS TEXT) FROM links WHERE handle=?)
    """, (handle,))
    conn.commit()
    
    return {
        "success": True, 
        "msg": "Link click stats reset.",
        "reload": True
    }
