"""
Premium Tier Logic for NotiFly
Handles admin generation, tokens, authentication, channel locking, Media Gallery, and Voting.
"""
import sqlite3
import random
import string
import time
import os
import io
import uuid
from pathlib import Path

# Media Configuration
MEDIA_DIR = Path("premium_media")
QUOTA_LIMIT = 1024 * 1024 * 1024  # 1 GB in bytes

try:
    from PIL import Image
except ImportError:
    Image = None

def init_db(conn):
    c = conn.cursor()
    MEDIA_DIR.mkdir(exist_ok=True)
    
    # Table for Premium Admin Credentials
    # Added: referral_token column
    c.execute("""CREATE TABLE IF NOT EXISTS premium_admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT, 
        referral_token TEXT UNIQUE,
        slots_max INTEGER DEFAULT 3,
        created_at INTEGER
    )""")
    
    # Migration: Add referral_token to existing admins if missing
    try:
        c.execute("ALTER TABLE premium_admins ADD COLUMN referral_token TEXT")
    except sqlite3.OperationalError:
        pass # Column likely exists

    # Table for Channel Locks
    c.execute("""CREATE TABLE IF NOT EXISTS premium_locks (
        handle TEXT PRIMARY KEY,
        admin_id INTEGER,
        locked_at INTEGER,
        FOREIGN KEY(admin_id) REFERENCES premium_admins(id)
    )""")
    # Table for Premium Media
    c.execute("""CREATE TABLE IF NOT EXISTS premium_media (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admin_id INTEGER,
        handle TEXT,
        filename TEXT,
        filesize INTEGER,
        mime_type TEXT,
        uploaded_at INTEGER,
        FOREIGN KEY(admin_id) REFERENCES premium_admins(id)
    )""")
    # Table for Likes/Dislikes
    c.execute("""CREATE TABLE IF NOT EXISTS media_votes (
        media_id INTEGER,
        voter_id TEXT,
        vote INTEGER,
        PRIMARY KEY (media_id, voter_id),
        FOREIGN KEY(media_id) REFERENCES premium_media(id) ON DELETE CASCADE
    )""")
    conn.commit()

def generate_admin(conn):
    """Generates a new Premium Admin with 3 slots and a referral token."""
    suffix_u = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    suffix_p = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
    username = f"AdminUser_{suffix_u}"
    password = f"Pwd_{suffix_p}"
    token = str(uuid.uuid4()) # Generate unique referral token
    
    c = conn.cursor()
    c.execute("INSERT INTO premium_admins (username, password, referral_token, created_at) VALUES (?, ?, ?, ?)", 
              (username, password, token, int(time.time())))
    conn.commit()
    return username, password, token

def redeem_token(conn, handle, token):
    """Redeems a referral token to lock a channel without password."""
    c = conn.cursor()
    c.row_factory = None
    
    # 1. Find Admin by Token
    c.execute("SELECT id, slots_max FROM premium_admins WHERE referral_token=?", (token,))
    admin = c.fetchone()
    if not admin:
        return {"success": False, "msg": "Invalid Referral Token"}
    
    admin_id, slots_max = admin
    
    # 2. Check if channel is ALREADY locked
    c.execute("SELECT admin_id FROM premium_locks WHERE handle=?", (handle,))
    existing = c.fetchone()
    if existing:
        if existing[0] == admin_id:
            return {"success": True, "msg": "Channel is already premium!"}
        else:
            return {"success": False, "msg": "Channel already owned by another Admin."}

    # 3. Check Slot Limits
    c.execute("SELECT COUNT(*) FROM premium_locks WHERE admin_id=?", (admin_id,))
    used = c.fetchone()[0]
    
    if used >= slots_max:
        return {"success": False, "msg": "This referral link has reached its max uses!"}
        
    # 4. Lock It
    c.execute("INSERT INTO premium_locks (handle, admin_id, locked_at) VALUES (?, ?, ?)", 
              (handle, admin_id, int(time.time())))
    conn.commit()
    return {"success": True, "msg": "Referral Redeemed! Premium Active."}

def get_channel_status(conn, handle):
    """Returns premium data for a channel if locked."""
    c = conn.cursor()
    c.row_factory = None 
    c.execute("""
        SELECT a.username, a.password, a.slots_max, a.id, a.referral_token
        FROM premium_locks l
        JOIN premium_admins a ON l.admin_id = a.id
        WHERE l.handle = ?
    """, (handle,))
    row = c.fetchone()
    
    if row:
        admin_id = row[3]
        c.execute("SELECT COUNT(*) FROM premium_locks WHERE admin_id=?", (admin_id,))
        used_slots = c.fetchone()[0]
        
        c.execute("SELECT SUM(filesize) FROM premium_media WHERE admin_id=?", (admin_id,))
        usage_row = c.fetchone()
        usage = usage_row[0] if usage_row and usage_row[0] else 0
        
        return {
            "locked": True,
            "username": row[0],
            "password": row[1],
            "referral_token": row[4], # Allow admin to see their own token
            "slots_used": used_slots,
            "slots_max": row[2],
            "storage_used": usage,
            "storage_max": QUOTA_LIMIT,
            "admin_id": admin_id
        }
    return {"locked": False}

def login_and_lock(conn, handle, username, password):
    """Attempts to login and lock the current channel."""
    c = conn.cursor()
    c.row_factory = None
    
    c.execute("SELECT id, slots_max FROM premium_admins WHERE username=? AND password=?", (username, password))
    admin = c.fetchone()
    if not admin:
        return {"success": False, "msg": "Invalid Credentials"}
    
    admin_id, slots_max = admin
    
    c.execute("SELECT admin_id FROM premium_locks WHERE handle=?", (handle,))
    existing = c.fetchone()
    if existing:
        if existing[0] == admin_id:
            return {"success": True, "msg": "Channel is already premium!"}
        else:
            return {"success": False, "msg": "Channel locked by another Admin."}
            
    c.execute("SELECT COUNT(*) FROM premium_locks WHERE admin_id=?", (admin_id,))
    used = c.fetchone()[0]
    
    if used >= slots_max:
        return {"success": False, "msg": f"No Slots Left ({used}/{slots_max})"}
        
    c.execute("INSERT INTO premium_locks (handle, admin_id, locked_at) VALUES (?, ?, ?)", 
              (handle, admin_id, int(time.time())))
    conn.commit()
    return {"success": True, "msg": "Premium Activated!"}

def upload_media(conn, handle, file_data, filename, mime_type):
    """Handles media upload with 1GB quota check and simple compression."""
    c = conn.cursor()
    c.row_factory = None
    
    c.execute("SELECT admin_id FROM premium_locks WHERE handle=?", (handle,))
    res = c.fetchone()
    if not res:
        return {"success": False, "msg": "Channel not Premium."}
    admin_id = res[0]
    
    c.execute("SELECT SUM(filesize) FROM premium_media WHERE admin_id=?", (admin_id,))
    usage_row = c.fetchone()
    current_usage = usage_row[0] if usage_row and usage_row[0] else 0
    
    new_size = len(file_data)
    if current_usage + new_size > QUOTA_LIMIT:
        return {"success": False, "msg": "Storage Quota Exceeded (1GB Limit)."}

    final_data = file_data
    if Image and mime_type.startswith('image/'):
        try:
            img = Image.open(io.BytesIO(file_data))
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            if img.width > 1920:
                ratio = 1920 / float(img.width)
                new_h = int(float(img.height) * ratio)
                img = img.resize((1920, new_h), Image.Resampling.LANCZOS)
            
            out = io.BytesIO()
            img.save(out, format='JPEG', quality=85, optimize=True)
            final_data = out.getvalue()
            new_size = len(final_data)
            filename = os.path.splitext(filename)[0] + ".jpg"
            mime_type = "image/jpeg"
        except Exception:
            pass
            
    safe_filename = f"{admin_id}_{int(time.time())}_{filename}".replace(" ", "_")
    target_path = MEDIA_DIR / safe_filename
    target_path.write_bytes(final_data)
    
    c.execute("INSERT INTO premium_media (admin_id, handle, filename, filesize, mime_type, uploaded_at) VALUES (?, ?, ?, ?, ?, ?)",
              (admin_id, handle, safe_filename, new_size, mime_type, int(time.time())))
    conn.commit()
    
    return {"success": True, "msg": "Media Uploaded!"}

def get_gallery(conn, handle):
    """Fetches list of media with like/dislike counts."""
    c = conn.cursor()
    c.row_factory = None
    # Subqueries to get votes
    c.execute("""
        SELECT m.id, m.filename, m.mime_type, m.filesize,
        (SELECT COUNT(*) FROM media_votes WHERE media_id=m.id AND vote=1) as likes,
        (SELECT COUNT(*) FROM media_votes WHERE media_id=m.id AND vote=-1) as dislikes
        FROM premium_media m 
        WHERE m.handle=? 
        ORDER BY m.id DESC
    """, (handle,))
    rows = c.fetchall()
    gallery = []
    for r in rows:
        gallery.append({
            "id": r[0],
            "url": f"/premium_media/{r[1]}",
            "type": "image" if r[2].startswith("image") else "video" if r[2].startswith("video") else "audio",
            "name": r[1],
            "size": f"{r[3]/1024/1024:.2f} MB",
            "likes": r[4],
            "dislikes": r[5]
        })
    return gallery

def cast_vote(conn, media_id, voter_id, vote_val):
    """Casts a like (1) or dislike (-1) vote."""
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO media_votes (media_id, voter_id, vote) VALUES (?, ?, ?)", 
              (media_id, voter_id, vote_val))
    conn.commit()
    
    c.execute("""
        SELECT 
        (SELECT COUNT(*) FROM media_votes WHERE media_id=? AND vote=1),
        (SELECT COUNT(*) FROM media_votes WHERE media_id=? AND vote=-1)
    """, (media_id, media_id))
    row = c.fetchone()
    return {"success": True, "likes": row[0], "dislikes": row[1]}

def delete_media(conn, handle, media_id):
    c = conn.cursor()
    c.row_factory = None
    c.execute("SELECT filename FROM premium_media WHERE id=? AND handle=?", (media_id, handle))
    row = c.fetchone()
    if not row:
        return {"success": False, "msg": "File not found or access denied."}
    
    filename = row[0]
    file_path = MEDIA_DIR / filename
    
    c.execute("DELETE FROM media_votes WHERE media_id=?", (media_id,))
    c.execute("DELETE FROM premium_media WHERE id=?", (media_id,))
    conn.commit()
    
    if file_path.exists():
        file_path.unlink()
        
    return {"success": True, "msg": "File deleted."}

# --- MANAGEMENT FUNCTIONS ---
def get_all_admins(conn):
    c = conn.cursor()
    c.row_factory = None
    admins = []
    c.execute("SELECT id, username, password, slots_max, created_at, referral_token FROM premium_admins")
    rows = c.fetchall()
    for r in rows:
        aid = r[0]
        c.execute("SELECT COUNT(*) FROM premium_locks WHERE admin_id=?", (aid,))
        locked_count = c.fetchone()[0]
        c.execute("SELECT SUM(filesize) FROM premium_media WHERE admin_id=?", (aid,))
        usage_row = c.fetchone()
        storage = usage_row[0] if usage_row and usage_row[0] else 0
        admins.append({
            "id": aid, "username": r[1], "password": r[2], 
            "slots_max": r[3], "created_at": r[4],
            "referral_token": r[5],
            "slots_used": locked_count, "storage_used": storage
        })
    return admins

def update_admin_slots(conn, admin_id, new_slots):
    c = conn.cursor()
    c.execute("UPDATE premium_admins SET slots_max=? WHERE id=?", (new_slots, admin_id))
    conn.commit()

def delete_admin(conn, admin_id):
    c = conn.cursor()
    c.row_factory = None
    c.execute("SELECT filename FROM premium_media WHERE admin_id=?", (admin_id,))
    files = c.fetchall()
    for f in files:
        path = MEDIA_DIR / f[0]
        if path.exists():
            try: path.unlink()
            except: pass
    c.execute("DELETE FROM premium_media WHERE admin_id=?", (admin_id,))
    c.execute("DELETE FROM premium_locks WHERE admin_id=?", (admin_id,))
    c.execute("DELETE FROM premium_admins WHERE id=?", (admin_id,))
    conn.commit()

# --- OVERSEER FUNCTIONS ---
def get_all_premium_channels(conn):
    c = conn.cursor()
    c.row_factory = None
    c.execute("""
        SELECT l.handle, a.username, l.locked_at,
               (SELECT COUNT(*) FROM premium_media m WHERE m.handle = l.handle) as f_count,
               (SELECT SUM(filesize) FROM premium_media m WHERE m.handle = l.handle) as f_size
        FROM premium_locks l
        JOIN premium_admins a ON l.admin_id = a.id
        ORDER BY f_size DESC
    """)
    rows = c.fetchall()
    channels = []
    for r in rows:
        channels.append({
            "handle": r[0], "admin": r[1], "locked_at": r[2],
            "file_count": r[3] or 0, "storage_used": r[4] or 0
        })
    return channels

def unlock_channel_only(conn, handle):
    c = conn.cursor()
    c.execute("DELETE FROM premium_locks WHERE handle=?", (handle,))
    conn.commit()

def nuke_channel_media_all(conn, handle):
    c = conn.cursor()
    c.row_factory = None
    c.execute("SELECT filename FROM premium_media WHERE handle=?", (handle,))
    files = [r[0] for r in c.fetchall()]
    if files:
        c.execute("DELETE FROM premium_media WHERE handle=?", (handle,))
        conn.commit()
    return files
