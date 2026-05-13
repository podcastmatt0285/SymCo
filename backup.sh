#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# backup.sh — Pull latest, dump all Wadsworth databases, commit and push
#
# Usage (run from project root):
#   ./backup.sh
# ─────────────────────────────────────────────────────────────────────────────
set -e

cd "$(dirname "$0")"

echo "=== Wadsworth Backup — $(date -u '+%Y-%m-%d %H:%M:%S UTC') ==="

# Pull first so the dump files are always newer than what's on remote
git pull

sudo -u postgres pg_dump \
    --clean --if-exists --no-owner --no-privileges \
    wadsworth > wadsworth_backup.sql
echo "  Dumped wadsworth → wadsworth_backup.sql"

sudo -u postgres pg_dump \
    --clean --if-exists --no-owner --no-privileges \
    reserve_banks > reserve_banks_backup.sql
echo "  Dumped reserve_banks → reserve_banks_backup.sql"

git add wadsworth_backup.sql reserve_banks_backup.sql tick_state.txt

if git diff --cached --quiet; then
    echo "  No changes since last backup — nothing to commit."
else
    git commit -m "data backup $(date -u '+%Y-%m-%d %H:%M UTC')"
    git push
    echo "  Backup committed and pushed."
fi

echo "=== Done ==="
