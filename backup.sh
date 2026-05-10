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

_dbname() {
    echo "$1" | sed -n 's|.*/\([^?]*\)|\1|p'
}

DB_MAIN=$(_dbname "${DATABASE_URL:-postgresql://wadsworth:wadsworth@localhost:5432/wadsworth}")
DB_RES=$(_dbname  "${RESERVE_DATABASE_URL:-postgresql://wadsworth:wadsworth@localhost:5432/reserve_banks}")

echo "=== Wadsworth DB Backup — $(date -u '+%Y-%m-%d %H:%M:%S UTC') ==="

sudo -u postgres pg_dump \
    --clean --if-exists --no-owner --no-privileges \
    "$DB_MAIN" > backups/wadsworth.sql
echo "  Dumped $DB_MAIN → backups/wadsworth.sql ($(wc -c < backups/wadsworth.sql | tr -d ' ') bytes)"

sudo -u postgres pg_dump \
    --clean --if-exists --no-owner --no-privileges \
    "$DB_RES" > backups/reserve_banks.sql
echo "  Dumped $DB_RES → backups/reserve_banks.sql ($(wc -c < backups/reserve_banks.sql | tr -d ' ') bytes)"

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
