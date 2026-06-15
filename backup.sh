#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# backup.sh — Pull latest, dump all Wadsworth databases, commit and push
#
# Usage (run from project root):
#   ./backup.sh
#
# What it captures, every run:
#   • Postgres dumps of all game databases (wadsworth, reserve_banks)
#   • tick_state.txt (game clock)
#   • ANY tracked source/notes edits made on the server (ADMIN_TODO.md, *.py, …)
#     — so working-tree changes are never silently lost on a restore.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

cd "$(dirname "$0")"

echo "=== Wadsworth Backup — $(date -u '+%Y-%m-%d %H:%M:%S UTC') ==="

# --autostash: the live app rewrites tick_state.txt every tick, so the working
# tree is almost always dirty. Without autostash, pull --rebase aborts here.
git pull --rebase --autostash

# ── Dump databases ───────────────────────────────────────────────────────────
# Dump to a temp file first, verify it is non-empty, then move into place — so a
# failed/partial dump can never overwrite a known-good backup.
dump_db () {
    local db="$1" out="$2" tmp
    tmp="$(mktemp)"
    # Dump and gzip in one pipe — output is ~3-5 MB instead of ~46 MB raw SQL.
    if ! sudo -u postgres pg_dump --clean --if-exists --no-owner --no-privileges "$db" \
         | gzip -9 > "$tmp"; then
        echo "  ✗ pg_dump $db FAILED — keeping previous $out" >&2
        rm -f "$tmp"
        return 1
    fi
    # Sanity: a real gzip dump is always >1KB.
    if [ "$(wc -c < "$tmp")" -lt 1024 ]; then
        echo "  ✗ $db dump looks empty/partial — keeping previous $out" >&2
        rm -f "$tmp"
        return 1
    fi
    mv "$tmp" "$out"
    echo "  ✓ Dumped $db → $out ($(wc -c < "$out" | numfmt --to=iec 2>/dev/null || wc -c < "$out") bytes)"
}

dump_db wadsworth     wadsworth_backup.sql.gz
dump_db reserve_banks reserve_banks_backup.sql.gz
# NOTE: counties data is a TABLE inside the wadsworth DB (counties.py uses the
# wadsworth engine), so it is already captured by wadsworth_backup.sql.gz above.
# Restore command: gunzip -c wadsworth_backup.sql.gz | sudo -u postgres psql wadsworth

# ── Stage everything worth keeping ───────────────────────────────────────────
# Explicit dumps + game clock …
git add wadsworth_backup.sql.gz reserve_banks_backup.sql.gz tick_state.txt 2>/dev/null || true
# … PLUS every tracked file that changed (source edits, ADMIN_TODO.md, configs).
# `-u` stages modifications/deletions to already-tracked files only; it will not
# sweep in untracked junk. This is what prevents working-tree edits from being
# lost on the next server restore.
git add -u

# Warn (don't fail) about untracked files so genuinely new notes aren't missed.
_untracked="$(git ls-files --others --exclude-standard)"
if [ -n "$_untracked" ]; then
    echo "  ⚠ Untracked files NOT backed up (git add them if you want them saved):"
    echo "$_untracked" | sed 's/^/      /'
fi

if git diff --cached --quiet; then
    echo "  No changes since last backup — nothing to commit."
else
    LABEL="data backup $(date -u '+%Y-%m-%d %H:%M UTC')"
    LAST_MSG="$(git log -1 --pretty=%s 2>/dev/null || true)"
    if [[ "$LAST_MSG" == data\ backup* ]]; then
        # Previous commit was also a backup: amend it so the old dump blob is
        # replaced rather than accumulated. One backup blob in history, always.
        git commit --amend -m "$LABEL"
        git pull --rebase --autostash
        git push --force
        echo "  Backup amended and force-pushed (old dump blob replaced, not accumulated)."
    else
        # Last commit was a source change: start a fresh backup commit.
        git commit -m "$LABEL"
        git pull --rebase --autostash && git push
        echo "  Backup committed and pushed."
    fi
fi

echo "=== Done ==="
