"""
seed_weekly_tasks.py

Run once on the live server to insert the 3 weekly task GameEvents.
Events are created as inactive (is_active=False); start them from the
admin dashboard at /admin/events when ready.

Usage:
    python3 seed_weekly_tasks.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from events import Base, GameEvent, SessionLocal
from database import engine
from datetime import datetime

Base.metadata.create_all(bind=engine)

WEEKLY_TASKS = [
    {
        "title":          "Meme Token Buyer",
        "description":    (
            "Spend $2,500 USD equivalent buying any meme token on the meme coin "
            "order book. Purchases are tracked in real-time at current native token "
            "prices. Every fill counts — market and limit orders both apply."
        ),
        "duration_class": "weekly",
        "event_type":     "task",
        "task_metric":    "meme_buy_usd",
        "task_target":    2500.0,
        "trophy_reward":  5,
    },
    {
        "title":          "Executive Shuffle",
        "description":    (
            "Fire or hire at least one executive this week. The boardroom never "
            "sleeps — shake up your leadership team to complete this task."
        ),
        "duration_class": "weekly",
        "event_type":     "task",
        "task_metric":    "executive_action",
        "task_target":    1.0,
        "trophy_reward":  3,
    },
    {
        "title":          "Tax Contributor",
        "description":    (
            "Generate $15,000 in city sales tax from your sales in the market or "
            "district market combined. Sell goods in a city that has a sales tax "
            "rate configured — the tax deducted from your proceeds counts toward "
            "this goal. Higher-tax cities help you reach the target faster."
        ),
        "duration_class": "weekly",
        "event_type":     "task",
        "task_metric":    "city_tax_paid_usd",
        "task_target":    15000.0,
        "trophy_reward":  8,
    },
]

db = SessionLocal()
try:
    for data in WEEKLY_TASKS:
        existing = db.query(GameEvent).filter(
            GameEvent.task_metric == data["task_metric"],
            GameEvent.duration_class == "weekly",
        ).first()
        if existing:
            print(f"  Skipped (already exists): '{data['title']}' (metric={data['task_metric']})")
            continue
        ev = GameEvent(
            title          = data["title"],
            description    = data["description"],
            duration_class = data["duration_class"],
            event_type     = data["event_type"],
            task_metric    = data["task_metric"],
            task_target    = data["task_target"],
            trophy_reward  = data["trophy_reward"],
            is_active      = False,
            starts_at      = datetime(9999, 12, 31),  # placeholder; overwritten on Start
            ends_at        = None,
        )
        db.add(ev)
        db.flush()
        print(f"  Created event ID {ev.id}: '{ev.title}'")
    db.commit()
    print("Done. Start events from /admin/events when ready.")
finally:
    db.close()
