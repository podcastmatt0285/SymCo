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
    if ! sudo -u postgres pg_dump --clean --if-exists --no-owner --no-privileges "$db" > "$tmp"; then
        echo "  ✗ pg_dump $db FAILED — keeping previous $out" >&2
        rm -f "$tmp"
        return 1
    fi
    # Sanity: a real dump always contains a CREATE/COPY statement and >1KB of text.
    if [ "$(wc -c < "$tmp")" -lt 1024 ] || ! grep -q "CREATE\|COPY\|INSERT" "$tmp"; then
        echo "  ✗ $db dump looks empty/partial — keeping previous $out" >&2
        rm -f "$tmp"
        return 1
    fi
    mv "$tmp" "$out"
    echo "  ✓ Dumped $db → $out ($(wc -c < "$out" | numfmt --to=iec 2>/dev/null || wc -c < "$out") bytes)"
}

dump_db wadsworth     wadsworth_backup.sql
dump_db reserve_banks reserve_banks_backup.sql
# NOTE: counties data is a TABLE inside the wadsworth DB (counties.py uses the
# wadsworth engine), so it is already captured by wadsworth_backup.sql above.
# The legacy separate `counties` database dump was redundant and is dropped.

# ── Stage everything worth keeping ───────────────────────────────────────────
# Explicit dumps + game clock …
git add wadsworth_backup.sql reserve_banks_backup.sql tick_state.txt 2>/dev/null || true
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
    git commit -m "data backup $(date -u '+%Y-%m-%d %H:%M UTC')"
    # Rebase again in case remote moved between our pull and now, then push
    git pull --rebase --autostash && git push
    echo "  Backup committed and pushed."
fi

echo "=== Done ==="
