#!/usr/bin/env python3
"""
One-shot migration: re-tag existing TransactionLog rows to use the specific
type strings introduced in the ledger overhaul (market_buy, market_sell,
district_market_buy, district_market_sell, retail_sale) instead of the old
generic types (resource_gain, resource_loss, cash_in, cash_out).

Matching is done on the description prefix which is highly specific — each
source always writes the same prefix so false-positive risk is negligible.

Safe to run multiple times (already-updated rows are excluded via WHERE).
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from database import SessionLocal
from stats_ux import TransactionLog
from sqlalchemy import text

RULES = [
    # (new_type, old_type, description_prefix)
    # ── Global market fills ──────────────────────────────────────────────────
    ("market_buy",           "resource_gain", "Market buy:"),
    ("market_buy",           "cash_out",      "Market purchase:"),
    ("market_sell",          "cash_in",       "Market sale:"),
    ("market_sell",          "resource_loss", "Market sale:"),
    # ── District market fills ────────────────────────────────────────────────
    ("district_market_buy",  "resource_gain", "District market buy:"),
    ("district_market_buy",  "cash_out",      "District market purchase:"),
    ("district_market_sell", "cash_in",       "District market sale:"),
    ("district_market_sell", "resource_loss", "District market sale:"),
    # ── Business retail revenue ──────────────────────────────────────────────
    ("retail_sale",          "cash_in",       "Revenue:"),
]

def run():
    db = SessionLocal()
    total = 0
    try:
        for new_type, old_type, desc_prefix in RULES:
            rows = (
                db.query(TransactionLog)
                .filter(
                    TransactionLog.transaction_type == old_type,
                    TransactionLog.description.like(f"{desc_prefix}%"),
                )
                .all()
            )
            for row in rows:
                row.transaction_type = new_type
            n = len(rows)
            if n:
                print(f"  {old_type!r:20s} → {new_type!r:25s}  ({n} rows)  prefix={desc_prefix!r}")
            total += n
        db.commit()
        print(f"\nMigration complete: {total} rows updated.")
    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("Re-tagging old transaction_type values…\n")
    run()
