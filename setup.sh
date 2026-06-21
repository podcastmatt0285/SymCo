#!/usr/bin/env bash
# setup.sh — Fresh install / restore for Wadsworth on Penguin (Crostini)
# Run from the project root after cloning.
#
# One-liner for a fresh Penguin terminal after a wipe:
#   sudo apt-get update -qq && sudo apt-get install -y git python3 python3-pip python3-venv postgresql libpq-dev && sudo service postgresql start && git clone https://github.com/podcastmatt0285/SymCo ~/SymCo && cd ~/SymCo && bash setup.sh

set -e
cd "$(dirname "$0")"

echo ""
echo "=== Wadsworth Setup — $(date -u '+%Y-%m-%d %H:%M UTC') ==="

# ── 1. Load .env ──────────────────────────────────────────────────────────────
if [ -f .env ]; then
    set -a; source .env; set +a
    echo "  [ok] Loaded .env"
else
    echo "  [warn] .env not found — using defaults (symco:symco)"
fi

DB_URL="${DATABASE_URL:-postgresql://symco:symco@localhost:5432/wadsworth}"
RES_URL="${RESERVE_DATABASE_URL:-postgresql://symco:symco@localhost:5432/reserve_banks}"

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

# ── 2. Install cloudflared ────────────────────────────────────────────────────
if ! command -v cloudflared &>/dev/null; then
    echo "  Installing cloudflared..."
    curl -fsSL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb \
        -o /tmp/cloudflared.deb
    sudo dpkg -i /tmp/cloudflared.deb
    rm -f /tmp/cloudflared.deb
    echo "  [ok] cloudflared installed"
else
    echo "  [ok] cloudflared already installed ($(cloudflared --version 2>&1 | head -1))"
fi

# ── 3. Start PostgreSQL ───────────────────────────────────────────────────────
echo "  Starting PostgreSQL..."
sudo service postgresql start 2>/dev/null || true
sudo systemctl enable postgresql 2>/dev/null || true  # auto-start on next boot

# ── 4. Create DB user and databases (idempotent) ─────────────────────────────
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

# ── 5. Restore databases ──────────────────────────────────────────────────────
_restore() {
    local dbname="$1"; shift
    # First existing candidate wins — prefer the GZIPPED dumps backup.sh writes.
    local sqlfile=""
    for cand in "$@"; do [ -f "$cand" ] && { sqlfile="$cand"; break; }; done

    if [ -n "$sqlfile" ]; then
        local age_h
        age_h="$(( ( $(date +%s) - $(stat -c %Y "$sqlfile" 2>/dev/null || echo "$(date +%s)") ) / 3600 ))"
        echo "  Restoring '$dbname' from $sqlfile (~${age_h}h old)..."
        [ "$age_h" -gt 24 ] && echo "  [warn] backup is ~${age_h}h old — may not be your latest live data (run ./backup.sh on the source server first)."
        case "$sqlfile" in
            *.gz) gunzip -c "$sqlfile" | sudo -u postgres psql "$dbname" ;;
            *)    sudo -u postgres psql "$dbname" < "$sqlfile" ;;
        esac
        # Refresh planner statistics — pg_dump omits them, and without ANALYZE a fresh
        # restore seq-scans everything (shows up as "SLOW module" ticks / tunnel stalls).
        sudo -u postgres psql "$dbname" -c "ANALYZE;" >/dev/null 2>&1 || true
        echo "  [ok] '$dbname' restored (stats refreshed)"
    else
        echo "  [warn] No backup found for '$dbname' — starting empty (app will create tables)"
    fi
}

_restore "$DB_MAIN" wadsworth_backup.sql.gz     backups/wadsworth.sql     wadsworth_backup.sql
_restore "$DB_RES"  reserve_banks_backup.sql.gz backups/reserve_banks.sql reserve_banks_backup.sql

# ── 6. Transfer ownership + grant privileges (must run AFTER restore) ────────
# pg_dump --no-owner restores tables owned by postgres. Transfer ownership to
# the app user so it can ALTER TABLE for schema migrations, then grant access.
echo "  Transferring table ownership to '$APP_USER'..."

_transfer_ownership() {
    local db="$1"
    sudo -u postgres psql "$db" -c "
DO \$\$
DECLARE r RECORD;
BEGIN
  FOR r IN SELECT tablename FROM pg_tables WHERE schemaname='public' LOOP
    EXECUTE 'ALTER TABLE public.' || quote_ident(r.tablename) || ' OWNER TO \"$APP_USER\"';
  END LOOP;
  FOR r IN SELECT sequence_name FROM information_schema.sequences WHERE sequence_schema='public' LOOP
    EXECUTE 'ALTER SEQUENCE public.' || quote_ident(r.sequence_name) || ' OWNER TO \"$APP_USER\"';
  END LOOP;
END
\$\$;
"
}

_transfer_ownership "$DB_MAIN"
_transfer_ownership "$DB_RES"

echo "  Granting default privileges to '$APP_USER'..."
sudo -u postgres psql "$DB_MAIN" -c "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO \"$APP_USER\"; GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO \"$APP_USER\";"
sudo -u postgres psql "$DB_RES"  -c "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO \"$APP_USER\"; GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO \"$APP_USER\";"
sudo -u postgres psql "$DB_MAIN" -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO \"$APP_USER\"; ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO \"$APP_USER\";"
sudo -u postgres psql "$DB_RES"  -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO \"$APP_USER\"; ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO \"$APP_USER\";"
echo "  [ok] Ownership transferred and privileges granted"

# ── 7. Create venv and install Python dependencies ───────────────────────────
echo "  Creating virtual environment..."
python3 -m venv venv
echo "  Installing Python packages..."
venv/bin/pip install -r requirements.txt --quiet
echo "  [ok] Python packages installed"

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "=== Setup complete ==="
echo ""
echo "  Start the server:"
echo "    cd $PWD && source venv/bin/activate && python3 app.py"
echo ""
echo "  Start Cloudflare tunnel (new terminal):"
echo "    cloudflared tunnel run --token eyJhIjoiYWU3MmMxMWVlNGZlM2IwZDk0MWEzNDE4NGYyZTg0ZDkiLCJ0IjoiMGJjYTI0MTItYzU0Ni00NWU4LWI2ZGItMWU4ZDE4ODMzOGNmIiwicyI6Ik1EYzRZall6Tm1NdFlXRTVOaTAwTkdNM0xUbGpaamt0TTJlbE9XVm1Nelk0TlRRNSJ9"
echo ""
echo "  To back up databases before a future wipe:"
echo "    cd $PWD && ./backup.sh"
echo ""
