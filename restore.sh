#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# restore.sh — Restore Wadsworth databases from the backups produced by backup.sh
#
# Usage (run from project root):
#   ./restore.sh                  # restore both databases
#   ./restore.sh wadsworth        # restore only the main game DB
#   ./restore.sh reserve_banks    # restore only the reserve banks DB
#
# backup.sh writes GZIPPED dumps in the project root:
#   wadsworth_backup.sql.gz  and  reserve_banks_backup.sql.gz
# This script restores from those (decompressing on the fly). It also reports how
# OLD each backup is, so you immediately notice if you're about to restore stale
# data — the usual cause of "the game looked days old" is that ./backup.sh was not
# run on the SOURCE server right before migrating.
#
# WARNING: This OVERWRITES the live databases. Stop the app first.
# ─────────────────────────────────────────────────────────────────────────────
set -e

cd "$(dirname "$0")"

# Pick up DATABASE_URL / RESERVE_DATABASE_URL from .env if present.
[ -f .env ] && { set -a; . ./.env; set +a; }

_dbname() { echo "$1" | sed -n 's|.*/\([^?]*\)|\1|p'; }
DB_MAIN=$(_dbname "${DATABASE_URL:-postgresql://symco:symco@localhost:5432/wadsworth}")
DB_RES=$(_dbname  "${RESERVE_DATABASE_URL:-postgresql://symco:symco@localhost:5432/reserve_banks}")

TARGET="${1:-both}"

# Restore $1 from the first existing candidate file in $2.. (prefers the .gz that
# backup.sh writes; falls back to legacy uncompressed paths). Reports file age and
# warns if the backup is stale; auto-creates the database if it doesn't exist.
_restore_one() {
    local db="$1"; shift
    local src=""
    for cand in "$@"; do [ -f "$cand" ] && { src="$cand"; break; }; done
    if [ -z "$src" ]; then
        echo "  ✗ No backup file found for '$db' (looked for: $*)" >&2
        return 1
    fi

    local mtime age_h
    mtime="$(date -r "$src" -u '+%Y-%m-%d %H:%M UTC' 2>/dev/null || echo '?')"
    age_h="$(( ( $(date +%s) - $(stat -c %Y "$src" 2>/dev/null || echo "$(date +%s)") ) / 3600 ))"
    echo "  → Restoring '$db' from $src  (dated $mtime · ~${age_h}h old)"
    if [ "$age_h" -gt 24 ]; then
        echo "  ⚠ WARNING: this backup is ~${age_h}h old. It may NOT be your latest live data."
        echo "    Run ./backup.sh on the SOURCE server (then git pull here) before restoring."
    fi

    # Ensure the target database exists (a fresh server may not have it yet).
    sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='$db'" | grep -q 1 \
        || sudo -u postgres psql -c "CREATE DATABASE \"$db\";"

    # Pipe the dump into psql, decompressing if it's gzipped.
    case "$src" in
        *.gz) gunzip -c "$src" | sudo -u postgres psql "$db" ;;
        *)    sudo -u postgres psql "$db" < "$src" ;;
    esac
    echo "  ✓ '$db' restored."
}

echo "=== Wadsworth DB Restore — $(date -u '+%Y-%m-%d %H:%M:%S UTC') ==="
echo "WARNING: This will OVERWRITE live data. Stop the app first. Ctrl-C to cancel. Continuing in 5s..."
sleep 5

if [[ "$TARGET" == "both" || "$TARGET" == "wadsworth" ]]; then
    _restore_one "$DB_MAIN" wadsworth_backup.sql.gz backups/wadsworth.sql wadsworth_backup.sql
fi

if [[ "$TARGET" == "both" || "$TARGET" == "reserve_banks" ]]; then
    _restore_one "$DB_RES" reserve_banks_backup.sql.gz backups/reserve_banks.sql reserve_banks_backup.sql
fi

echo "=== Restore complete ==="
echo "Tip: if the data looks old, the committed backup was stale — run ./backup.sh on the"
echo "source server, 'git pull' here, then ./restore.sh again."
