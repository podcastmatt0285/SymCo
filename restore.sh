#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# restore.sh — Restore Wadsworth databases from backup SQL files
#
# Usage (run from project root):
#   ./restore.sh                  # restore both databases
#   ./restore.sh wadsworth        # restore only the main game DB
#   ./restore.sh reserve_banks    # restore only the reserve banks DB
#
# WARNING: This OVERWRITES the live databases. Stop the app first.
# ─────────────────────────────────────────────────────────────────────────────
set -e

cd "$(dirname "$0")"

_dbname() {
    echo "$1" | sed -n 's|.*/\([^?]*\)|\1|p'
}

DB_MAIN=$(_dbname "${DATABASE_URL:-postgresql://symco:symco@localhost:5432/wadsworth}")
DB_RES=$(_dbname  "${RESERVE_DATABASE_URL:-postgresql://symco:symco@localhost:5432/reserve_banks}")

TARGET="${1:-both}"

echo "=== Wadsworth DB Restore — $(date -u '+%Y-%m-%d %H:%M:%S UTC') ==="
echo "WARNING: This will overwrite live data. Ctrl-C to cancel. Continuing in 5s..."
sleep 5

if [[ "$TARGET" == "both" || "$TARGET" == "wadsworth" ]]; then
    [[ -f backups/wadsworth.sql ]] || { echo "ERROR: backups/wadsworth.sql not found"; exit 1; }
    echo "  Restoring $DB_MAIN..."
    sudo -u postgres psql "$DB_MAIN" < backups/wadsworth.sql
    echo "  Done."
fi

if [[ "$TARGET" == "both" || "$TARGET" == "reserve_banks" ]]; then
    [[ -f backups/reserve_banks.sql ]] || { echo "ERROR: backups/reserve_banks.sql not found"; exit 1; }
    echo "  Restoring $DB_RES..."
    sudo -u postgres psql "$DB_RES" < backups/reserve_banks.sql
    echo "  Done."
fi

echo "=== Restore complete ==="
