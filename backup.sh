#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# backup.sh — Dump all Wadsworth databases and commit to git
#
# Usage (run from project root):
#   ./backup.sh
#
# Cron (hourly — add via: crontab -e):
#   0 * * * * cd /home/maphematics/SymCo && ./backup.sh >> /var/log/wadsworth-backup.log 2>&1
#
# Databases backed up:
#   wadsworth       → backups/wadsworth.sql
#   reserve_banks   → backups/reserve_banks.sql
# ─────────────────────────────────────────────────────────────────────────────
set -e

cd "$(dirname "$0")"

# Read connection strings — fall back to defaults matching database.py
DB_URL="${DATABASE_URL:-postgresql://postgres:postgres@localhost:5432/wadsworth}"
RESERVE_URL="${RESERVE_DATABASE_URL:-postgresql://postgres:postgres@localhost:5432/reserve_banks}"

# Parse each URL into pg_dump args
_pgdump() {
    local url="$1" outfile="$2"
    # postgresql://user:pass@host:port/dbname
    local user pass host port dbname
    user=$(echo "$url"   | sed -n 's|.*://\([^:]*\):.*|\1|p')
    pass=$(echo "$url"   | sed -n 's|.*://[^:]*:\([^@]*\)@.*|\1|p')
    host=$(echo "$url"   | sed -n 's|.*@\([^:/]*\).*|\1|p')
    port=$(echo "$url"   | sed -n 's|.*:\([0-9]*\)/.*|\1|p')
    dbname=$(echo "$url" | sed -n 's|.*/\([^?]*\)|\1|p')

    PGPASSWORD="$pass" pg_dump \
        -h "$host" -p "$port" -U "$user" \
        --clean --if-exists --no-owner --no-privileges \
        "$dbname" > "$outfile"
    echo "  Dumped $dbname → $outfile ($(wc -c < "$outfile" | tr -d ' ') bytes)"
}

echo "=== Wadsworth DB Backup — $(date -u '+%Y-%m-%d %H:%M:%S UTC') ==="

_pgdump "$DB_URL"      "backups/wadsworth.sql"
_pgdump "$RESERVE_URL" "backups/reserve_banks.sql"

# Commit and push
git add backups/wadsworth.sql backups/reserve_banks.sql
if git diff --cached --quiet; then
    echo "  No changes since last backup — nothing to commit."
else
    git commit -m "db backup $(date -u '+%Y-%m-%d %H:%M UTC')"
    git push
    echo "  Backup committed and pushed."
fi

echo "=== Done ==="
