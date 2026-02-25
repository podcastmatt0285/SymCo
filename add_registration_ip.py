"""
One-shot migration: adds the registration_ip column to the players table.

Run from the project root:
    python add_registration_ip.py

Safe to run multiple times (IF NOT EXISTS).
"""
from database import engine
from sqlalchemy import text

with engine.begin() as conn:
    conn.execute(text(
        "ALTER TABLE players ADD COLUMN IF NOT EXISTS registration_ip TEXT"
    ))

print("Done — registration_ip column is ready.")
