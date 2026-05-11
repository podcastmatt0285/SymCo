#!/usr/bin/env python3
"""
One-shot patch: update the 'Tax Contributor' task description to remove
incorrect city/county language.

Run once on the live server:
    python3 patch_tax_contributor_description.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from events import SessionLocal, GameEvent

NEW_DESC = (
    "Accumulate $15,000 in sales tax deducted from your sell orders on "
    "the market and district market combined. Sales tax is automatically "
    "taken from your proceeds each time a sell order fills — no special "
    "setup required. Sell more volume to reach the target faster."
)

db = SessionLocal()
try:
    task = db.query(GameEvent).filter(GameEvent.task_metric == "city_tax_paid_usd").first()
    if not task:
        print("Task not found — nothing to update.")
    else:
        print(f"Found: ID={task.id}  Title='{task.title}'")
        print(f"Old desc: {task.description}")
        task.description = NEW_DESC
        db.commit()
        print(f"Updated description.")
finally:
    db.close()
