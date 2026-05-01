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

DB_URL="${DATABASE_URL:-postgresql://postgres:postgres@localhost:5432/wadsworth}"
RESERVE_URL="${RESERVE_DATABASE_URL:-postgresql://postgres:postgres@localhost:5432/reserve_banks}"

TARGET="${1:-both}"

_psql() {
    local url="$1" sqlfile="$2"
    local user pass host port dbname
    user=$(echo "$url"   | sed -n 's|.*://\([^:]*\):.*|\1|p')
    pass=$(echo "$url"   | sed -n 's|.*://[^:]*:\([^@]*\)@.*|\1|p')
    host=$(echo "$url"   | sed -n 's|.*@\([^:/]*\).*|\1|p')
    port=$(echo "$url"   | sed -n 's|.*:\([0-9]*\)/.*|\1|p')
    dbname=$(echo "$url" | sed -n 's|.*/\([^?]*\)|\1|p')

    echo "  Restoring $dbname from $sqlfile..."
    PGPASSWORD="$pass" psql -h "$host" -p "$port" -U "$user" "$dbname" < "$sqlfile"
    echo "  Done."
}

echo "=== Wadsworth DB Restore — $(date -u '+%Y-%m-%d %H:%M:%S UTC') ==="
echo "WARNING: This will overwrite live data. Ctrl-C to cancel. Continuing in 5s..."
sleep 5

if [[ "$TARGET" == "both" || "$TARGET" == "wadsworth" ]]; then
    [[ -f backups/wadsworth.sql ]] || { echo "ERROR: backups/wadsworth.sql not found"; exit 1; }
    _psql "$DB_URL" "backups/wadsworth.sql"
fi

if [[ "$TARGET" == "both" || "$TARGET" == "reserve_banks" ]]; then
    [[ -f backups/reserve_banks.sql ]] || { echo "ERROR: backups/reserve_banks.sql not found"; exit 1; }
    _psql "$RESERVE_URL" "backups/reserve_banks.sql"
fi

echo "=== Restore complete ==="
