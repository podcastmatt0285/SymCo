#!/usr/bin/env bash
# setup.sh — Fresh install / restore for Wadsworth on Penguin (Crostini)
# Run from the project root after cloning.
#
# One-liner for a fresh Penguin terminal after a wipe:
#   sudo apt-get update -qq && sudo apt-get install -y git python3 python3-pip postgresql libpq-dev && git clone https://github.com/podcastmatt0285/SymCo ~/SymCo && cd ~/SymCo && bash setup.sh

set -e
cd "$(dirname "$0")"

echo ""
echo "=== Wadsworth Setup — $(date -u '+%Y-%m-%d %H:%M UTC') ==="

# ── 1. Load .env ──────────────────────────────────────────────────────────────
if [ -f .env ]; then
    set -a; source .env; set +a
    echo "  [ok] Loaded .env"
else
    echo "  [warn] .env not found — using defaults (wadsworth:wadsworth)"
fi

DB_URL="${DATABASE_URL:-postgresql://wadsworth:wadsworth@localhost:5432/wadsworth}"
RES_URL="${RESERVE_DATABASE_URL:-postgresql://wadsworth:wadsworth@localhost:5432/reserve_banks}"

_field() {
    local url="$1"
    case "$2" in
        user)   echo "$url" | sed -n 's|.*://\([^:@]*\):.*|\1|p' ;;
        pass)   echo "$url" | sed -n 's|.*://[^:]*:\([^@]*\)@.*|\1|p' ;;
        host)   echo "$url" | sed -n 's|.*@\([^:/]*\).*|\1|p' ;;
        port)   echo "$url" | sed -n 's|.*:\([0-9]*\)/.*|\1|p' ;;
        dbname) echo "$url" | sed -n 's|.*/\([^?]*\)|\1|p' ;;
    esac
}

APP_USER=$(_field "$DB_URL" user)
APP_PASS=$(_field "$DB_URL" pass)
APP_HOST=$(_field "$DB_URL" host)
APP_PORT=$(_field "$DB_URL" port)
DB_MAIN=$(_field "$DB_URL" dbname)
DB_RES=$(_field "$RES_URL" dbname)

# ── 2. Start PostgreSQL ───────────────────────────────────────────────────────
echo "  Starting PostgreSQL..."
sudo service postgresql start 2>/dev/null || true
sudo systemctl enable postgresql 2>/dev/null || true  # auto-start on next boot

# ── 3. Create DB user and databases (idempotent) ─────────────────────────────
echo "  Setting up user '$APP_USER' and databases '$DB_MAIN', '$DB_RES'..."

sudo -u postgres psql -v ON_ERROR_STOP=0 -q <<SQL
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$APP_USER') THEN
    CREATE USER "$APP_USER" WITH PASSWORD '$APP_PASS';
  END IF;
END
\$\$;
SQL

sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='$DB_MAIN'" | grep -q 1 \
    || sudo -u postgres psql -c "CREATE DATABASE \"$DB_MAIN\" OWNER \"$APP_USER\";"
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='$DB_RES'" | grep -q 1 \
    || sudo -u postgres psql -c "CREATE DATABASE \"$DB_RES\" OWNER \"$APP_USER\";"

echo "  [ok] Databases ready"

# ── 4. Restore databases ──────────────────────────────────────────────────────
_restore() {
    local dbname="$1" primary="$2" fallback="$3"
    local sqlfile=""
    [ -f "$primary" ]  && sqlfile="$primary"
    [ -z "$sqlfile" ] && [ -f "$fallback" ] && sqlfile="$fallback"

    if [ -n "$sqlfile" ]; then
        echo "  Restoring '$dbname' from $sqlfile..."
        sudo -u postgres psql "$dbname" < "$sqlfile"
        echo "  [ok] '$dbname' restored"
    else
        echo "  [warn] No backup found for '$dbname' — starting empty (app will create tables)"
    fi
}

_restore "$DB_MAIN" "backups/wadsworth.sql"     "wadsworth_backup.sql"
_restore "$DB_RES"  "backups/reserve_banks.sql"  "reserve_banks_backup.sql"

# ── 5. Install Python dependencies ────────────────────────────────────────────
echo "  Installing Python packages..."
python3 -m pip install -r requirements.txt --quiet
echo "  [ok] Python packages installed"

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "=== Setup complete ==="
echo ""
echo "  Start the server:"
echo "    cd $PWD && python3 app.py"
echo ""
echo "  To back up databases before a future wipe:"
echo "    cd $PWD && ./backup.sh"
echo ""
