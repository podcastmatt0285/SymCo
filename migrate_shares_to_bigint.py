#!/usr/bin/env python3
"""
One-shot migration: ALTER share-count columns from INTEGER → BIGINT.

Run once inside the app's venv:
    python3 migrate_shares_to_bigint.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from database import engine

STMTS = [
    # company_shares
    "ALTER TABLE company_shares ALTER COLUMN total_shares_authorized TYPE BIGINT",
    "ALTER TABLE company_shares ALTER COLUMN shares_outstanding TYPE BIGINT",
    "ALTER TABLE company_shares ALTER COLUMN shares_held_by_founder TYPE BIGINT",
    "ALTER TABLE company_shares ALTER COLUMN shares_held_by_firm TYPE BIGINT",
    "ALTER TABLE company_shares ALTER COLUMN shares_in_float TYPE BIGINT",
    "ALTER TABLE company_shares ALTER COLUMN founder_class_a_shares TYPE BIGINT",
    "ALTER TABLE company_shares ALTER COLUMN drip_shares_remaining TYPE BIGINT",
    "ALTER TABLE company_shares ALTER COLUMN shelf_shares_remaining TYPE BIGINT",
    # corporate action tables
    "ALTER TABLE buyback_programs ALTER COLUMN max_shares_to_buy TYPE BIGINT",
    "ALTER TABLE buyback_programs ALTER COLUMN shares_bought TYPE BIGINT",
    "ALTER TABLE buyback_programs ALTER COLUMN treasury_shares TYPE BIGINT",
    "ALTER TABLE secondary_offerings ALTER COLUMN shares_to_issue TYPE BIGINT",
    "ALTER TABLE secondary_offerings ALTER COLUMN shares_issued TYPE BIGINT",
    "ALTER TABLE corporate_action_history ALTER COLUMN shares_affected TYPE BIGINT",
    "ALTER TABLE stock_split_history ALTER COLUMN old_shares_outstanding TYPE BIGINT",
    "ALTER TABLE stock_split_history ALTER COLUMN new_shares_outstanding TYPE BIGINT",
    "ALTER TABLE dividend_payment_history ALTER COLUMN shares_at_time TYPE BIGINT",
]

def run():
    with engine.connect() as conn:
        for stmt in STMTS:
            try:
                conn.execute(__import__('sqlalchemy').text(stmt))
                print(f"  OK  {stmt}")
            except Exception as e:
                print(f"  --  {stmt}\n      ({e})")
        conn.commit()
    print("\nDone.")

if __name__ == "__main__":
    run()
