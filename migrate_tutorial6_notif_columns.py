#!/usr/bin/env python3
"""
One-shot migration: add tutorial_6_step and notif_push_tasks_events columns
to the players table.

Run once inside the app's venv:
    python3 migrate_tutorial6_notif_columns.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from database import engine
from sqlalchemy import text

STMTS = [
    # Tutorial 6 step tracker (0=not started, 1-6=active, 7=complete)
    "ALTER TABLE players ADD COLUMN IF NOT EXISTS tutorial_6_step INTEGER DEFAULT 0",
    # Push notification toggle for task completions and event alerts
    "ALTER TABLE players ADD COLUMN IF NOT EXISTS notif_push_tasks_events BOOLEAN DEFAULT TRUE",
]


def run():
    with engine.connect() as conn:
        for stmt in STMTS:
            try:
                conn.execute(text(stmt))
                conn.commit()
                print(f"  OK  {stmt}")
            except Exception as e:
                print(f"  --  {stmt}")
                print(f"      {e}")
    print("Migration complete.")


if __name__ == "__main__":
    run()
