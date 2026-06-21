#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# install-backup-cron.sh — Install a once-daily (00:00 UTC) cron job that runs
# backup.sh, so the committed database dumps are never more than ~24h stale.
#
# Usage (run from the project root, as the user that owns the clone):
#   ./install-backup-cron.sh            # install / update the job
#   ./install-backup-cron.sh --remove   # remove it
#
# Idempotent: re-running replaces the existing Wadsworth backup entry rather than
# adding duplicates. CRON_TZ=UTC is placed immediately before the job line so the
# midnight schedule is UTC regardless of the server's local timezone, and so it
# does NOT change the timezone of any other cron jobs you may have.
#
# Requirements on the server (same as running ./backup.sh by hand):
#   • passwordless sudo for `sudo -u postgres pg_dump` (cron has no TTY to prompt),
#   • git push works non-interactively (cached credential / token in the remote URL).
# If either prompts when you run ./backup.sh manually, fix that first or the cron
# run will fail silently — check backup.log.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

cd "$(dirname "$0")"
PROJ="$(pwd)"
MARKER="# wadsworth-daily-backup"
JOB="0 0 * * * cd $PROJ && ./backup.sh >> $PROJ/backup.log 2>&1 $MARKER"

if [ "${1:-}" = "--remove" ]; then
    crontab -l 2>/dev/null | grep -v -F "$MARKER" | crontab - 2>/dev/null || true
    echo "Removed the Wadsworth daily backup cron job."
    crontab -l 2>/dev/null || echo "(crontab now empty)"
    exit 0
fi

# Rebuild: keep existing entries (minus our prior job and the CRON_TZ=UTC we manage),
# then append CRON_TZ=UTC + the job at the very end so the UTC schedule applies only
# to our line. NOTE: this manages a single `CRON_TZ=UTC`; don't rely on a separate
# global CRON_TZ=UTC for other jobs.
TMP="$(mktemp)"
crontab -l 2>/dev/null | grep -v -F "$MARKER" | grep -v '^CRON_TZ=UTC$' > "$TMP" || true
{ cat "$TMP"; echo "CRON_TZ=UTC"; echo "$JOB"; } | crontab -
rm -f "$TMP"

echo "Installed daily backup cron (00:00 UTC):"
echo "  $JOB"
echo
echo "Current crontab:"
crontab -l
echo
echo "Logs will accumulate in: $PROJ/backup.log"
echo "Test it now with:  cd \"$PROJ\" && ./backup.sh"
