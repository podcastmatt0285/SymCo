#!/usr/bin/env python3
"""
reset_game.py — Soft game reset for SymCo / Wadsworth.

Keeps:   player accounts, bans, admin logs, moderators, ban-word config
Wipes:   everything else (all game state, businesses, land, inventory,
         stocks, cities, counties, wallets, reserve banks, etc.)
Resets:  each player back to $50,000 cash, tutorial at step 0,
         3 fresh starter plots, and starter inventory.

Usage (from /home/user/SymCo, with PostgreSQL running):
    python reset_game.py            # live run
    python reset_game.py --dry-run  # print what would happen, no changes
"""

import os
import sys

# ---------------------------------------------------------------------------
# Set DB URLs before any SymCo module is imported so database.py picks them up.
# Edit these if your credentials differ.
# ---------------------------------------------------------------------------
os.environ.setdefault("DATABASE_URL",         "postgresql://symco:symco@localhost:5432/wadsworth")
os.environ.setdefault("RESERVE_DATABASE_URL", "postgresql://symco:symco@localhost:5432/reserve_banks")

# Add SymCo root to path so all modules resolve
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from database import engine, SessionLocal, reserve_engine, ReserveSessionLocal

# ---------------------------------------------------------------------------
# Tables in the main (wadsworth) DB that must NOT be wiped
# ---------------------------------------------------------------------------
PRESERVE_WADSWORTH = {
    "players",        # keep accounts
    "player_bans",    # keep active bans
    "admin_logs",     # keep audit trail
    "moderators",     # keep mod config
    "user_ban_words", # keep word filter
}

STARTING_CASH        = 50_000.0
STARTING_TUTORIAL    = 0

# ---------------------------------------------------------------------------
DRY_RUN = "--dry-run" in sys.argv
# ---------------------------------------------------------------------------

def banner(msg: str):
    print(f"\n{'='*60}\n  {msg}\n{'='*60}")

def step(msg: str):
    print(f"  → {msg}")


def get_table_names(eng, schema: str = "public") -> list[str]:
    with eng.connect() as conn:
        rows = conn.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname = :s"),
            {"s": schema},
        )
        return [r[0] for r in rows]


def truncate_tables(eng, tables: list[str], label: str):
    if not tables:
        print(f"  (no tables to truncate in {label})")
        return
    quoted = ", ".join(f'"{t}"' for t in sorted(tables))
    sql = f"TRUNCATE TABLE {quoted} RESTART IDENTITY CASCADE"
    step(f"TRUNCATE {len(tables)} tables in {label}")
    if DRY_RUN:
        print(f"    [dry-run] would execute: {sql[:120]}...")
        return
    with eng.connect() as conn:
        conn.execute(text(sql))
        conn.commit()
    step(f"Done — {label} tables cleared.")


def reset_player_accounts() -> list[tuple[int, str]]:
    """Reset cash/tutorial on all real players (id > 0), delete all sessions."""
    step("Resetting player cash and tutorial_step …")
    if not DRY_RUN:
        db = SessionLocal()
        try:
            db.execute(
                text("UPDATE players SET cash_balance = :c, tutorial_step = :t WHERE id > 0"),
                {"c": STARTING_CASH, "t": STARTING_TUTORIAL},
            )
            db.execute(text("DELETE FROM sessions"))
            db.commit()
        finally:
            db.close()

    db = SessionLocal()
    try:
        rows = db.execute(
            text("SELECT id, business_name FROM players WHERE id > 0 ORDER BY id")
        ).fetchall()
        return [(r[0], r[1]) for r in rows]
    finally:
        db.close()


def give_starter_resources(player_id: int, business_name: str):
    """Create 3 starter land plots and give starter inventory for one player."""
    step(f"Setting up starter resources for [{player_id}] {business_name} …")
    if DRY_RUN:
        print(f"    [dry-run] would create 3 plots + starter inventory for player {player_id}")
        return
    try:
        from land import create_starter_plot
        create_starter_plot(player_id)
        create_starter_plot(player_id)
        create_starter_plot(player_id)
    except Exception as e:
        print(f"    [WARN] create_starter_plot failed for {player_id}: {e}")

    try:
        from market import give_starter_inventory
        give_starter_inventory(player_id)
    except Exception as e:
        print(f"    [WARN] give_starter_inventory failed for {player_id}: {e}")


def reinit_main_banks():
    """Re-initialize bank entities (land bank, ETFs, brokerage, etc.)."""
    step("Re-initializing main bank entities …")
    if DRY_RUN:
        print("    [dry-run] would call banks.initialize()")
        return
    try:
        import banks
        banks.initialize()
    except Exception as e:
        print(f"    [WARN] banks.initialize() failed: {e}")
        import traceback; traceback.print_exc()


def reinit_reserve_banks():
    """Re-seed the DEFAULT_BANKS into the now-empty reserve_banks DB."""
    step("Re-seeding reserve banks …")
    if DRY_RUN:
        print("    [dry-run] would call reserve_banks.initialize()")
        return
    try:
        import reserve_banks
        reserve_banks.initialize()
    except Exception as e:
        print(f"    [WARN] reserve_banks.initialize() failed: {e}")
        import traceback; traceback.print_exc()


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    banner("SymCo Soft Game Reset" + (" [DRY RUN]" if DRY_RUN else " [LIVE]"))

    if not DRY_RUN:
        print("\n  WARNING: This will wipe ALL game progress.")
        print("  Player accounts and bans are preserved.")
        ans = input("\n  Type 'yes' to continue: ").strip().lower()
        if ans != "yes":
            print("  Aborted.")
            sys.exit(0)

    # ------------------------------------------------------------------
    # 1. Find tables to truncate in wadsworth
    # ------------------------------------------------------------------
    banner("Step 1: Clearing wadsworth game tables")
    all_wads = get_table_names(engine)
    to_wipe  = [t for t in all_wads if t not in PRESERVE_WADSWORTH]
    step(f"Found {len(all_wads)} total tables; preserving {len(PRESERVE_WADSWORTH)}, wiping {len(to_wipe)}")
    truncate_tables(engine, to_wipe, "wadsworth")

    # ------------------------------------------------------------------
    # 2. Reset player accounts (cash + tutorial) and kill all sessions
    # ------------------------------------------------------------------
    banner("Step 2: Resetting player accounts")
    players = reset_player_accounts()
    step(f"Found {len(players)} player(s) to reset to starting state")

    # ------------------------------------------------------------------
    # 3. Give each player their starter kit
    # ------------------------------------------------------------------
    banner("Step 3: Giving starter kits to all players")
    for pid, bname in players:
        give_starter_resources(pid, bname)

    # ------------------------------------------------------------------
    # 4. Re-initialize main banks (land bank, ETFs, brokerage)
    # ------------------------------------------------------------------
    banner("Step 4: Re-initializing main banks")
    reinit_main_banks()

    # ------------------------------------------------------------------
    # 5. Wipe + re-seed reserve banks (separate DB)
    # ------------------------------------------------------------------
    banner("Step 5: Clearing + re-seeding reserve_banks DB")
    all_reserve = get_table_names(reserve_engine)
    truncate_tables(reserve_engine, all_reserve, "reserve_banks")
    reinit_reserve_banks()

    # ------------------------------------------------------------------
    # Done
    # ------------------------------------------------------------------
    banner("Reset complete!")
    print(f"  Players reset: {len(players)}")
    for pid, bname in players:
        print(f"    [{pid}] {bname} → $50,000 cash, 3 plots, starter inventory")
    print(f"\n  All sessions cleared — everyone will need to log back in.")
    if DRY_RUN:
        print("\n  This was a DRY RUN — no changes were made.")


if __name__ == "__main__":
    main()
