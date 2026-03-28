import sqlite3
import uuid
import time

# Connect to database
conn = sqlite3.connect("notifly.db")
c = conn.cursor()

print("\n🔍 Checking Admin Database...")

# 1. Fix missing tokens (Backfill existing admins)
# This ensures even admins created months ago get a link now.
try:
    c.execute("SELECT id FROM premium_admins WHERE referral_token IS NULL")
    rows = c.fetchall()
    if rows:
        print(f"   > Generating tokens for {len(rows)} existing admins...")
        for r in rows:
            new_token = str(uuid.uuid4())
            c.execute("UPDATE premium_admins SET referral_token=? WHERE id=?", (new_token, r[0]))
        conn.commit()
except Exception as e:
    print(f"   > Error checking tokens (Table might not exist yet): {e}")

# 2. Print all links
print("\n" + "="*40)
print("   PREMIUM REFERRAL LINKS")
print("="*40)

try:
    c.execute("SELECT username, referral_token, slots_max FROM premium_admins")
    admins = c.fetchall()
    
    if not admins:
        print("No admins found. Run 'manager.py' to create one first!")
    
    for r in admins:
        username = r[0]
        token = r[1]
        slots = r[2]
        
        # Count usage
        c.execute("SELECT COUNT(*) FROM premium_locks WHERE admin_id=(SELECT id FROM premium_admins WHERE username=?)", (username,))
        used = c.fetchone()[0]
        
        print(f"👑 Admin:  {username}")
        print(f"📊 Usage:  {used}/{slots} Slots")
        if token:
            print(f"🔗 Link:   https://notifly.cc/claim/{token}")
        else:
            print("🔗 Link:   (Error: No token found)")
        print("-" * 40)

except Exception as e:
    print(f"Error reading admins: {e}")

conn.close()
