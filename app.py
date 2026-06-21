import os
import sys
import subprocess

# ═══════════════════════════════════════════════════════════════════════════════
# BOOTSTRAP — runs before any third-party imports
#   1. Load .env into environment
#   2. Detect package manager; install missing system packages
#   3. Create venv and re-exec inside it (idempotent)
#   4. Ensure PostgreSQL is running with DBs, backups restored, permissions set
#   5. Start Cloudflare tunnel in background
#
# Result: `python3 app.py` is the only command needed on a fresh clone.
# ═══════════════════════════════════════════════════════════════════════════════

_HERE = os.path.dirname(os.path.abspath(__file__))


def _load_dotenv():
    env_path = os.path.join(_HERE, ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if not _line or _line.startswith("#") or "=" not in _line:
                continue
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))


def _detect_pkg_manager():
    """Return the first available package manager, or None."""
    import shutil
    for _pm in ("apt-get", "dnf", "yum", "brew", "apk"):
        if shutil.which(_pm):
            return _pm
    return None


def _ensure_system_deps():
    """Install required system packages if any are missing."""
    import shutil, tempfile

    # If already running inside the venv, system deps were installed before
    # venv creation — no need to check or install anything.
    venv_dir = os.path.join(_HERE, "venv")
    if sys.executable.startswith(venv_dir):
        return

    pm = _detect_pkg_manager()

    needed = []

    # Test whether `python3 -m venv` actually works (not just `import venv` —
    # venv is always importable as stdlib but may lack ensurepip on Debian).
    with tempfile.TemporaryDirectory() as _td:
        _r = subprocess.run([sys.executable, "-m", "venv", _td], capture_output=True)
        if _r.returncode != 0:
            if pm == "apt-get":
                needed += ["python3-venv", "python3-pip"]
            elif pm in ("dnf", "yum"):
                needed.append("python3")         # venv + pip bundled on Fedora/RHEL
            # brew / apk: venv is built into python3

    # pip availability (belt-and-suspenders for Debian minimal installs)
    if pm == "apt-get":
        if subprocess.run([sys.executable, "-m", "pip", "--version"],
                          capture_output=True).returncode != 0:
            if "python3-pip" not in needed:
                needed.append("python3-pip")

    # PostgreSQL server + psql client
    if not shutil.which("psql"):
        if pm == "apt-get":
            needed += ["postgresql", "postgresql-client"]
        elif pm in ("dnf", "yum"):
            needed += ["postgresql-server", "postgresql"]
        elif pm == "brew":
            needed.append("postgresql")
        elif pm == "apk":
            needed += ["postgresql", "postgresql-client"]

    # libpq-dev — needed for psycopg2 to compile during pip install
    if not shutil.which("pg_config"):
        if pm == "apt-get":
            needed.append("libpq-dev")
        elif pm in ("dnf", "yum"):
            needed.append("libpq-devel")
        elif pm == "brew":
            needed.append("libpq")

    # curl — needed to download cloudflared
    if not shutil.which("curl"):
        needed.append("curl")

    # git — needed if not already present
    if not shutil.which("git"):
        needed.append("git")

    if not needed:
        return

    if pm is None:
        print(f"[Bootstrap] WARNING: no known package manager found.")
        print(f"[Bootstrap] Please install manually: python3-venv postgresql libpq-dev curl git")
        return

    print(f"[Bootstrap] Installing system packages: {' '.join(needed)}")
    if pm == "apt-get":
        subprocess.run(["sudo", "apt-get", "update", "-qq"], check=True)
        subprocess.run(["sudo", "apt-get", "install", "-y", "-qq"] + needed, check=True)
    elif pm in ("dnf", "yum"):
        subprocess.run(["sudo", pm, "install", "-y"] + needed, check=True)
        # On Fedora/RHEL, new PostgreSQL install needs data dir initialized
        if "postgresql-server" in needed:
            subprocess.run(["sudo", "postgresql-setup", "--initdb"], capture_output=True)
    elif pm == "brew":
        subprocess.run(["brew", "install"] + needed, check=False)
    elif pm == "apk":
        subprocess.run(["sudo", "apk", "add", "--no-cache"] + needed, check=True)

    print("[Bootstrap] System packages ready")


def _ensure_venv():
    """Create venv if needed and re-exec inside it (replaces current process)."""
    venv_dir = os.path.join(_HERE, "venv")
    venv_py  = os.path.join(venv_dir, "bin", "python3")
    if sys.executable.startswith(venv_dir):
        return  # already running inside venv
    if not os.path.exists(venv_py):
        print("[Bootstrap] Creating virtual environment...")
        subprocess.run([sys.executable, "-m", "venv", venv_dir], check=True)
    # Always sync dependencies — fast no-op if already satisfied, catches the
    # case where the venv exists but pip install never ran (e.g. first clone on
    # a machine where the venv dir was restored from a backup without packages).
    print("[Bootstrap] Installing/verifying dependencies...")
    subprocess.run(
        [venv_py, "-m", "pip", "install", "-r",
         os.path.join(_HERE, "requirements.txt"), "--quiet"],
        check=True,
    )
    print("[Bootstrap] Restarting inside venv...")
    os.execv(venv_py, [venv_py] + sys.argv)  # replaces current process; nothing below runs


def _pg_start():
    """Start PostgreSQL service; tries service, then systemctl, then pg_ctl."""
    import shutil
    # On Fedora/RHEL, enable first so systemctl start works
    pm = _detect_pkg_manager()
    if pm in ("dnf", "yum") and shutil.which("systemctl"):
        subprocess.run(["sudo", "systemctl", "enable", "postgresql"], capture_output=True)

    for cmd in (
        ["sudo", "service", "postgresql", "start"],
        ["sudo", "systemctl", "start", "postgresql"],
        ["sudo", "systemctl", "start", "postgresql@16-main"],
        ["sudo", "systemctl", "start", "postgresql@15-main"],
        ["sudo", "systemctl", "start", "postgresql@14-main"],
        ["sudo", "systemctl", "start", "postgresql@13-main"],
    ):
        r = subprocess.run(cmd, capture_output=True)
        if r.returncode == 0:
            return


def _ensure_postgres():
    """Idempotently start PostgreSQL, create user/DBs, restore backups, fix ownership."""
    import re, shutil
    if not shutil.which("psql"):
        print("[Bootstrap] psql not found — skipping DB setup")
        return

    db_url  = os.environ.get("DATABASE_URL",         "postgresql://symco:symco@localhost:5432/wadsworth")
    res_url = os.environ.get("RESERVE_DATABASE_URL", "postgresql://symco:symco@localhost:5432/reserve_banks")

    def _parse(url):
        m = re.match(r"postgresql://([^:@]+):([^@]*)@[^/]+/(\w+)", url)
        return (m.group(1), m.group(2), m.group(3)) if m else ("symco", "symco", url.rsplit("/", 1)[-1])

    app_user, app_pass, db_main = _parse(db_url)
    _,        _,        db_res  = _parse(res_url)

    def _pg(db, sql):
        subprocess.run(
            ["sudo", "-u", "postgres", "psql", "-v", "ON_ERROR_STOP=0", "-q", db, "-c", sql],
            capture_output=True,
        )

    def _pg_value(sql, db="postgres"):
        r = subprocess.run(["sudo", "-u", "postgres", "psql", db, "-tAc", sql],
                           capture_output=True, text=True)
        return r.stdout.strip()

    _pg_start()

    # Create app user if missing
    _pg("postgres", f"""
        DO $$ BEGIN
          IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{app_user}') THEN
            CREATE USER "{app_user}" WITH PASSWORD '{app_pass}';
          END IF;
        END $$;
    """)

    # Create databases if missing
    for _db in [db_main, db_res]:
        if _pg_value(f"SELECT 1 FROM pg_database WHERE datname='{_db}'") != "1":
            subprocess.run(
                ["sudo", "-u", "postgres", "psql", "-c",
                 f'CREATE DATABASE "{_db}" OWNER "{app_user}";'],
                capture_output=True,
            )

    # Restore from backups only when DB is empty (fresh install)
    def _table_count(dbname):
        r = subprocess.run(
            ["sudo", "-u", "postgres", "psql", "-tAc",
             "SELECT COUNT(*) FROM pg_tables WHERE schemaname='public'", dbname],
            capture_output=True, text=True,
        )
        try:    return int(r.stdout.strip())
        except: return -1

    def _restore(dbname, *paths):
        if _table_count(dbname) > 0:
            return  # already populated
        for p in paths:
            if os.path.exists(p):
                print(f"[Bootstrap] Restoring {dbname} from {os.path.basename(p)}...")
                with open(p) as fh:
                    subprocess.run(["sudo", "-u", "postgres", "psql", dbname],
                                   stdin=fh, capture_output=True)
                break

    _restore(db_main,
             os.path.join(_HERE, "backups", "wadsworth.sql"),
             os.path.join(_HERE, "wadsworth_backup.sql"))
    _restore(db_res,
             os.path.join(_HERE, "backups", "reserve_banks.sql"),
             os.path.join(_HERE, "reserve_banks_backup.sql"))

    # Transfer table ownership + grant privileges only when needed.
    # pg_dump --no-owner restores tables owned by postgres (the restoring role),
    # so symco must own them to run ALTER TABLE schema migrations.
    # Skip this expensive loop when tables are already correctly owned.
    _ownership_sql = f"""
        DO $$ DECLARE r RECORD; BEGIN
          FOR r IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' LOOP
            EXECUTE 'ALTER TABLE public.' || quote_ident(r.tablename) || ' OWNER TO "{app_user}"';
          END LOOP;
          FOR r IN SELECT sequence_name FROM information_schema.sequences
                   WHERE sequence_schema = 'public' LOOP
            EXECUTE 'ALTER SEQUENCE public.' || quote_ident(r.sequence_name) || ' OWNER TO "{app_user}"';
          END LOOP;
        END $$;
        GRANT ALL PRIVILEGES ON ALL TABLES    IN SCHEMA public TO "{app_user}";
        GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO "{app_user}";
        ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES    TO "{app_user}";
        ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO "{app_user}";
    """
    for _db in [db_main, db_res]:
        # Must pass _db explicitly — pg_tables only shows the current DB's tables
        _wrong = _pg_value(
            f"SELECT COUNT(*) FROM pg_tables "
            f"WHERE schemaname='public' AND tableowner != '{app_user}'",
            _db,
        )
        if _wrong and _wrong != "0":
            print(f"[Bootstrap] Fixing table ownership in {_db}...")
            _pg(_db, _ownership_sql)

    print("[Bootstrap] PostgreSQL ready")


def _start_tunnel():
    """Start Cloudflare tunnel in background; auto-installs cloudflared if missing."""
    import shutil, platform

    token = os.environ.get(
        "CLOUDFLARE_TUNNEL_TOKEN",
        "eyJhIjoiYWU3MmMxMWVlNGZlM2IwZDk0MWEzNDE4NGYyZTg0ZDkiLCJ0IjoiMGJjYTI0MTItYzU0Ni00NWU4LWI2ZGItMWU4ZDE4ODMzOGNmIiwicyI6Ik1EYzRZall6Tm1NdFlXRTVOaTAwTkdNM0xUbGpaamt0TTJGbE9XVm1Nelk0TlRRNSJ9",
    )
    if not token:
        return

    # Don't spawn a second tunnel if one is already running (e.g. uvicorn reload).
    # Check the process is still alive, not just that the name exists.
    _pgrep = subprocess.run(["pgrep", "-x", "cloudflared"], capture_output=True)
    if _pgrep.returncode == 0:
        _pid = _pgrep.stdout.decode().strip().split("\n")[0]
        if _pid and os.path.exists(f"/proc/{_pid}"):
            print("[Bootstrap] Cloudflare tunnel already running — skipping")
            return
        # stale entry — proceed to start a fresh one

    if not shutil.which("cloudflared"):
        print("[Bootstrap] Installing cloudflared...")
        _machine = platform.machine().lower()
        _arch    = {"x86_64": "amd64", "amd64": "amd64",
                    "aarch64": "arm64", "arm64": "arm64"}.get(_machine)
        _system  = platform.system().lower()

        if _arch and _system == "linux":
            _base = f"https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-{_arch}"
            if shutil.which("dpkg"):
                _pkg = "/tmp/cloudflared.deb"
                if subprocess.run(["curl", "-fsSL", _base + ".deb", "-o", _pkg]).returncode == 0:
                    subprocess.run(["sudo", "dpkg", "-i", _pkg])
            elif shutil.which("rpm"):
                _pkg = "/tmp/cloudflared.rpm"
                if subprocess.run(["curl", "-fsSL", _base + ".rpm", "-o", _pkg]).returncode == 0:
                    subprocess.run(["rpm", "-i", "--force", _pkg])
            else:
                _bin = "/usr/local/bin/cloudflared"
                if subprocess.run(["curl", "-fsSL", _base, "-o", _bin]).returncode == 0:
                    subprocess.run(["chmod", "+x", _bin])
        elif _system == "darwin" and shutil.which("brew"):
            subprocess.run(["brew", "install", "cloudflared"])
        else:
            print(f"[Bootstrap] cloudflared: unsupported platform {_system}/{_machine}")

    # shutil.which uses Python's PATH which may differ from the shell's PATH.
    # Fall back to common install locations used by the official Cloudflare installer.
    _cf_bin = shutil.which("cloudflared")
    if not _cf_bin:
        for _candidate in [
            "/usr/local/bin/cloudflared",
            "/usr/bin/cloudflared",
            os.path.expanduser("~/.local/bin/cloudflared"),
            "/snap/bin/cloudflared",
        ]:
            if os.path.isfile(_candidate) and os.access(_candidate, os.X_OK):
                _cf_bin = _candidate
                break

    if _cf_bin:
        _log = open(os.path.join(_HERE, "cloudflared.log"), "a")
        proc = subprocess.Popen(
            [_cf_bin, "tunnel", "--protocol", "http2", "run", "--token", token],
            stdout=_log, stderr=_log,
            start_new_session=True,   # detach from uvicorn's process group
        )
        print(f"[Bootstrap] Cloudflare tunnel started (pid {proc.pid}) via {_cf_bin}, log → cloudflared.log")
    else:
        print("[Bootstrap] cloudflared not found — tunnel not started")


_load_dotenv()
_ensure_system_deps()   # detects package manager; installs missing system deps
_ensure_venv()          # may os.execv() — everything below only runs inside venv
_ensure_postgres()
_start_tunnel()

# ═══════════════════════════════════════════════════════════════════════════════

import asyncio
from datetime import datetime

# ── Sentry error monitoring ────────────────────────────────────────────────────
# Set SENTRY_DSN env var to activate. Safe no-op if the var is absent or
# sentry-sdk is not installed.
try:
    import sentry_sdk
    _sentry_dsn = os.environ.get("SENTRY_DSN", "")
    if _sentry_dsn:
        sentry_sdk.init(
            dsn=_sentry_dsn,
            traces_sample_rate=0.1,   # 10% of requests traced for performance
            profiles_sample_rate=0.05,
        )
        print("Sentry error monitoring active")
except ImportError:
    pass  # sentry-sdk not installed — monitoring disabled
from typing import Optional
from fastapi import FastAPI, Cookie
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from starlette.concurrency import run_in_threadpool

# ==========================
# GLOBAL TICK STATE
# ==========================

TICK_INTERVAL = 5.0  # seconds
MODULE_TICK_TIMEOUT = 30.0  # circuit breaker: max seconds a single module's tick may take
_tick_profile = {}  # module name → [total_seconds, call_count, max_seconds] (perf diagnostics)
current_tick = 0
tick_start_time = None
tick_task = None

_TICK_STATE_FILE = os.path.join(os.path.dirname(__file__), "tick_state.txt")

def _load_tick_state() -> int:
    """Load persisted tick counter from disk, or 0 if not found."""
    try:
        with open(_TICK_STATE_FILE, "r") as f:
            return int(f.read().strip())
    except Exception:
        return 0

def _save_tick_state(tick: int):
    """Persist tick counter to disk."""
    try:
        with open(_TICK_STATE_FILE, "w") as f:
            f.write(str(tick))
    except Exception as e:
        print(f"[Tick] WARNING: could not save tick state: {e}")

# ==========================
# MODULE REGISTRY
# ==========================

modules = {}

def register_module(name: str, module):
    """Register a module with the application."""
    modules[name] = module
    print(f" → {name.capitalize()} registered")

def load_modules():
    """Attempt to load all game modules."""
    module_names = ['auth', 'inventory', 'wma', 'business', 'market', 'land', 'land_restoration', 'land_market', 'banks', 'districts', 'special_plots', 'district_market', 'cities', 'city_projects', 'counties', 'memecoins', 'wallet', 'city_wallet', 'stats_ux', 'executive', 'estate', 'p2p', 'chat', 'admins', 'dm', 'corporate_actions', 'reserve_banks', 'trusted_trade', 'contacts', 'soundtrack', 'wcpr', 'npc', 'events', 'govt_ledger', 'beta', 'market_ws', 'player_feed_ws', 'port_authority', 'military', 'bluesky', 'profiles_ux', 'advisor_ux']
    for name in module_names:
        try:
            mod = __import__(name)
            register_module(name, mod)
        except ModuleNotFoundError:
            pass

# ==========================
# TICK LOOP
# ==========================

async def tick_loop():
    """Global tick loop executing every second."""
    global current_tick
    import time as _time
    _last_profile = _time.monotonic()
    while True:
        current_tick += 1
        now = datetime.utcnow()
        for name, module in modules.items():
            if hasattr(module, 'tick'):
                _t0 = _time.monotonic()
                try:
                    tick_fn = module.tick
                    # Circuit breaker: never let one module freeze the whole game loop
                    # (e.g. a tick blocking on slow/hung network or a huge query). On
                    # timeout we log and move on; a sync tick's worker thread finishes on
                    # its own. Heavy/network work should run off the loop anyway.
                    if asyncio.iscoroutinefunction(tick_fn):
                        await asyncio.wait_for(tick_fn(current_tick, now),
                                               timeout=MODULE_TICK_TIMEOUT)
                    else:
                        await asyncio.wait_for(run_in_threadpool(tick_fn, current_tick, now),
                                               timeout=MODULE_TICK_TIMEOUT)
                except asyncio.TimeoutError:
                    print(f"[Tick {current_tick}] TIMEOUT module '{name}' (>{MODULE_TICK_TIMEOUT:.0f}s) — skipped, loop continues", flush=True)
                except Exception as e:
                    print(f"[Tick {current_tick}] ERROR in {name}: {e}", flush=True)
                # Warn if a single module monopolises the tick — early signal of a
                # freeze before it starves the whole game loop.
                _elapsed = _time.monotonic() - _t0
                # Cumulative profile so the worst modules are visible over time, not just
                # one-off spikes. Printed periodically below.
                _p = _tick_profile.setdefault(name, [0.0, 0, 0.0])
                _p[0] += _elapsed; _p[1] += 1; _p[2] = max(_p[2], _elapsed)
                if _elapsed > 4.0:
                    print(f"[Tick {current_tick}] SLOW module '{name}': {_elapsed:.1f}s", flush=True)

        if current_tick % 60 == 0:
            print(f"[Tick {current_tick}] {now.isoformat()}", flush=True)
            _save_tick_state(current_tick)

        # Tick profile on a WALL-CLOCK cadence (every ~60s of real time) so it appears even
        # when ticks are slow — and flushed so output buffering can't swallow it. Window
        # resets each print, so the numbers reflect the LAST ~60s, not since boot.
        if _time.monotonic() - _last_profile >= 60.0:
            _last_profile = _time.monotonic()
            _top = sorted(_tick_profile.items(), key=lambda kv: kv[1][0], reverse=True)[:8]
            if _top:
                print(f"[Tick profile] last ~60s — top modules by total time (tick {current_tick}):", flush=True)
                for _n, (_tot, _cnt, _mx) in _top:
                    print(f"    {_n:<22} total {_tot:7.1f}s · avg {_tot/max(_cnt,1):6.2f}s · max {_mx:6.1f}s · {_cnt} calls", flush=True)
            _tick_profile.clear()
        await asyncio.sleep(TICK_INTERVAL)

# ==========================
# MODULE INITIALIZATION
# ==========================

def initialize_modules():
    """Initialize all registered modules."""
    print("Initializing modules...")
    for name, module in modules.items():
        if hasattr(module, 'initialize'):
            try:
                module.initialize()
                print(f" ✓ {name.capitalize()} initialized")
            except Exception as e:
                print(f" ✗ {name.capitalize()} failed: {e}")
    if not modules:
        print(" (No modules loaded)")
    print("Module initialization complete.")

# ==========================
# LIFESPAN MANAGEMENT
# ==========================

@asynccontextmanager
async def lifespan(app: FastAPI):
    global tick_start_time, tick_task, current_tick
    print("=" * 50)
    print("Starting Real-Time Economic Simulation")
    print("=" * 50)
    current_tick = _load_tick_state()
    print(f"Tick counter restored: {current_tick}")
    tick_start_time = datetime.utcnow()
    # DB migrations
    try:
        from auth import migrate_player_table, migrate_ip_tables, migrate_push_subscriptions
        migrate_player_table()
        migrate_ip_tables()
        migrate_push_subscriptions()
        print("DB migrations applied")
    except Exception as _me:
        print(f"DB migration error: {_me}")
    # Burn removed generic military items (one-time migration)
    try:
        from military_migration import run_migration as _run_mil_migration
        _run_mil_migration()
    except Exception as _mme:
        print(f"Military migration error: {_mme}")
    # Wiki DB init (migrates wiki_media.json → DB on first run)
    try:
        import wiki as _wiki_mod
        _wiki_mod.initialize()
        print("Wiki DB initialized")
    except Exception as _we:
        print(f"Wiki init error: {_we}")
    # Retroactively seed admin as accepted contact for all existing players
    try:
        from contacts import seed_admin_contact_all_players
        seed_admin_contact_all_players()
    except Exception as _ce:
        print(f"[App] Admin contact seed error: {_ce}")
    load_modules()
    initialize_modules()
    tick_task = asyncio.create_task(tick_loop())
    print(f"Tick loop started (interval: {TICK_INTERVAL}s)")
    # NPC seeding runs in a background thread — server is ready to accept
    # requests immediately while NPCs seed in parallel.
    npc_seed_task = None
    try:
        import npc as _npc_mod
        npc_seed_task = asyncio.create_task(
            run_in_threadpool(_npc_mod.seed_npcs_background)
        )
        print("[App] NPC background seeding started")
    except ImportError:
        print("[App] NPC module not found — skipping background seeding")
    print("=" * 50)
    yield
    print("\nShutting down...")
    if npc_seed_task and not npc_seed_task.done():
        npc_seed_task.cancel()
        try:
            await npc_seed_task
        except asyncio.CancelledError:
            pass
    if tick_task:
        tick_task.cancel()
        try:
            await tick_task
        except asyncio.CancelledError:
            pass
    print("Shutdown complete.")

# ==========================
# FASTAPI APP
# ==========================

app = FastAPI(
    title="Wadsworth Economic Simulation",
    description="Real-time multiplayer economic simulation",
    version="1.1.2132026",
    lifespan=lifespan
)

app.mount("/static", StaticFiles(directory="static"), name="static")

# PWA — these must be served from the root so the service worker scope covers
# the whole app and browsers can discover the manifest automatically.
# CORS headers are required so PWABuilder and other external validators can
# fetch these files cross-origin.
_PWA_CORS = {
    "Access-Control-Allow-Origin": "*",
    "Cache-Control": "no-cache, no-store, must-revalidate",
    "Pragma": "no-cache",
}

@app.get("/manifest.json", include_in_schema=False)
@app.head("/manifest.json", include_in_schema=False)
async def pwa_manifest():
    return FileResponse("static/manifest.json", media_type="application/manifest+json",
                        headers=_PWA_CORS)

@app.get("/sw.js", include_in_schema=False)
@app.head("/sw.js", include_in_schema=False)
async def pwa_service_worker():
    return FileResponse("static/sw.js", media_type="application/javascript",
                        headers=_PWA_CORS)

@app.head("/", include_in_schema=False)
async def root_head():
    from fastapi.responses import Response
    return Response(status_code=200, headers={"content-type": "text/html; charset=utf-8"})

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("static/icons/icon-48.png", media_type="image/png")

@app.get("/.well-known/assetlinks.json", include_in_schema=False)
async def assetlinks():
    """Required for Android TWA verification and App Links."""
    from fastapi.responses import JSONResponse
    return JSONResponse([{
        "relation": [
            "delegate_permission/common.handle_all_urls",
            "delegate_permission/common.get_login_creds",
        ],
        "target": {
            "namespace": "android_app",
            "package_name": "cc.notifly.wadsworth.twa",
            # List EVERY key that signs a copy of the app users may install, or the
            # TWA fails Digital Asset Links verification (browser URL bar appears,
            # push delegation + get_login_creds break). Two are needed:
            #   1) Google Play App Signing key — Google re-signs the uploaded AAB,
            #      so Play-Store installs present THIS fingerprint.
            #   2) Local upload/release keystore (android/wadsworth-signing.jks) —
            #      signs the directly-distributed wadsworth-signed.apk; without it,
            #      sideloaded / direct-download installs fail verification.
            "sha256_cert_fingerprints": [
                # 1) Google Play App Signing key
                "A7:21:91:A3:04:C4:5A:A2:C8:69:76:EF:7C:C6:3D:56:2D:77:57:94:38:1B:C5:F1:A8:8A:73:6A:B7:D9:DF:03",
                # 2) Local release keystore (android/wadsworth-signing.jks, alias "android")
                "73:E0:0D:08:1F:93:32:4D:A0:59:19:C6:AC:73:9E:F0:C8:4F:BB:C3:11:5D:A3:43:10:46:0B:A6:E0:DF:C7:1D",
            ],
        },
    }])

@app.get("/robots.txt", include_in_schema=False)
async def robots_txt():
    from fastapi.responses import PlainTextResponse
    content = (
        "User-agent: *\n"
        "Disallow: /\n"
        "\n"
        "User-agent: Googlebot\n"
        "Allow: /\n"
        "Disallow: /admin\n"
        "Disallow: /api\n"
        "Disallow: /settings\n"
        "Disallow: /notifications\n"
        "Disallow: /wallet\n"
        "\n"
        "User-agent: Bingbot\n"
        "Allow: /\n"
        "Disallow: /admin\n"
        "Disallow: /api\n"
        "Disallow: /settings\n"
        "Disallow: /notifications\n"
        "Disallow: /wallet\n"
        "\n"
        "User-agent: ClaudeBot\n"
        "Allow: /\n"
        "Disallow: /admin\n"
        "Disallow: /api\n"
        "Disallow: /settings\n"
        "Disallow: /notifications\n"
        "Disallow: /wallet\n"
        "\n"
        "Sitemap: https://wadsworth.notifly.cc/sitemap.xml\n"
    )
    return PlainTextResponse(content, headers={"Cache-Control": "public, max-age=86400"})

@app.get("/sitemap.xml", include_in_schema=False)
async def sitemap_xml():
    from fastapi.responses import Response
    from datetime import datetime as _dt
    base = "https://wadsworth.notifly.cc"
    lastmod = _dt.utcnow().strftime("%Y-%m-%d")

    # Only genuinely public, content-rich pages belong in the sitemap.
    # Login-gated pages serve an identical "Login Required" stub (duplicate /
    # soft-404 content), private pages redirect to /login, and a few legacy
    # paths have no route at all — none of those should be submitted to Search
    # Console. Each entry: (path, changefreq, priority).
    pages = [
        ("/",                          "daily",   "1.0"),
        ("/login",                     "monthly", "0.9"),
        ("/wiki",                      "weekly",  "0.8"),
        ("/founding",                  "monthly", "0.7"),
        ("/banks/indices/unloggedin",  "daily",   "0.7"),
        ("/company/whitepaper",        "monthly", "0.6"),
        ("/company/careers",           "monthly", "0.5"),
        ("/company/press-kit",         "monthly", "0.5"),
        ("/sitemap",                   "monthly", "0.4"),
        ("/privacy-policy",            "yearly",  "0.3"),
    ]

    # Enrich with the public per-index detail pages — each is a distinct,
    # crawlable market page with unique content.
    try:
        from banks.indices import INDICES
        for code in INDICES.keys():
            pages.append((f"/banks/indices/{code}/unloggedin", "daily", "0.6"))
    except Exception:
        pass

    items = "\n".join(
        f"  <url>\n"
        f"    <loc>{base}{path}</loc>\n"
        f"    <lastmod>{lastmod}</lastmod>\n"
        f"    <changefreq>{freq}</changefreq>\n"
        f"    <priority>{prio}</priority>\n"
        f"  </url>"
        for path, freq, prio in pages
    )
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{items}
</urlset>"""
    return Response(content=xml, media_type="application/xml",
                    headers={"Cache-Control": "public, max-age=86400"})

# ==========================
# SYSTEM ENDPOINTS (PATCHED)
# ==========================
# Update within app.py @app.get("/api/status")
@app.get("/api/status")
async def get_status(session_token: Optional[str] = Cookie(None)):
    from auth import get_player_from_session, get_db
    from business import Business # Add this import
    
    db = get_db()
    player = get_player_from_session(db, session_token)
    
    # Fetch active business progress for this player.
    # district_businesses.json must be merged with the standard BUSINESS_TYPES
    # dict so that high-tier district businesses report the correct
    # cycles_to_complete instead of falling back to 1 (which makes their
    # progress bars appear instantly complete/broken).
    biz_list = []
    if player:
        user_biz = db.query(Business).filter(Business.owner_id == player.id).all()
        from business import BUSINESS_TYPES, get_district_business_types
        all_business_types = {**BUSINESS_TYPES, **get_district_business_types()}
        for b in user_biz:
            config = all_business_types.get(b.business_type, {})
            biz_list.append({
                "id": b.id,
                "progress_ticks": b.progress_ticks,
                "cycles_to_complete": config.get("cycles_to_complete", 1)
            })

    status_data = {
        "status": "running",
        "current_tick": current_tick,
        "player_balance": player.cash_balance if player else 0,
        "businesses": biz_list, # Now the progress bars can move!
        "modules": {name: True for name in modules.keys()}
    }
    db.close()
    return status_data

@app.get("/api/tick")
async def get_tick():
    return {
        "tick": current_tick,
        "timestamp": datetime.utcnow().isoformat()
    }

# ==========================
# ROUTING
# ==========================

try:
    from auth import router as auth_router
    app.include_router(auth_router)
    print("Auth routes registered")
except ModuleNotFoundError:
    pass

try:
    from ux import router as ux_router
    app.include_router(ux_router)
    print("UX routes registered")
except ModuleNotFoundError:
    @app.get("/")
    async def root():
        return {
            "message": "Wadsworth Economic Simulation",
            "status": "UX module not loaded",
            "tick": current_tick,
            "api_status": "/api/status"
        }

try:
    from corporate_actions_ux import router as corporate_actions_router
    app.include_router(corporate_actions_router)
    print("Corporate Actions routes registered")
except ModuleNotFoundError:
    pass

try:
    from corporate_actions_ui import router as corporate_actions_ui_router
    app.include_router(corporate_actions_ui_router)
    print("Corporate Actions UI routes registered")
except ModuleNotFoundError:
    pass

try:
    from districts_ux import router as districts_ux_router
    app.include_router(districts_ux_router)
    print("Districts UX routes registered")
except ModuleNotFoundError:
    pass

try:
    from stats_ux import router as stats_router
    app.include_router(stats_router)
    print("Stats routes registered")
except ModuleNotFoundError:
    pass

try:
    from cities_ux import router as cities_router
    app.include_router(cities_router)
    print("Cities routes registered")
except ModuleNotFoundError:
    pass

try:
    from counties_ux import router as counties_router
    app.include_router(counties_router)
    print("Counties routes registered")
except ModuleNotFoundError:
    pass

try:
    from executive_ux import router as executive_router
    app.include_router(executive_router)
    print("Executive routes registered")
except ModuleNotFoundError:
    pass

try:
    from estate_ux import router as estate_router
    app.include_router(estate_router)
    print("Estate routes registered")
except ModuleNotFoundError:
    pass

try:
    from dm_ux import router as dm_ux_router
    app.include_router(dm_ux_router)
    print("DM UX routes registered")
except ModuleNotFoundError:
    pass

try:
    from p2p_ux import router as p2p_ux_router
    app.include_router(p2p_ux_router)
    print("P2P UX routes registered")
except ModuleNotFoundError:
    pass

try:
    from chat_ux import router as chat_router
    app.include_router(chat_router)
    print("Chat routes registered")
except ModuleNotFoundError:
    pass

try:
    from admins_ux import router as admins_router
    app.include_router(admins_router)
    print("Admin routes registered")
except ModuleNotFoundError:
    pass

try:
    from mod_ux import router as mod_router
    app.include_router(mod_router)
    print("Mod routes registered")
except ModuleNotFoundError:
    pass

try:
    from memecoins_ux import router as memecoins_router
    app.include_router(memecoins_router)
    print("Meme Coins routes registered")
except ModuleNotFoundError:
    pass

try:
    from crypto_hub_ux import router as crypto_hub_router
    app.include_router(crypto_hub_router)
    print("Crypto Hub routes registered")
except ModuleNotFoundError:
    pass

try:
    import wallet  # ensures WSC tables are created and tick handler is registered
    print("Wallet module loaded")
except ModuleNotFoundError:
    pass


try:
    from tutorial_ux import router as tutorial_router
    app.include_router(tutorial_router)
    print("Tutorial routes registered")
except ModuleNotFoundError:
    pass

try:
    from reserve_banks_ux import router as reserve_banks_router
    app.include_router(reserve_banks_router)
    print("Reserve Banks routes registered")
except ModuleNotFoundError:
    pass

try:
    from trusted_trade_ux import router as trusted_trade_router
    app.include_router(trusted_trade_router)
    print("Trusted Trade routes registered")
except ModuleNotFoundError:
    pass

try:
    from banks import indices as indices_mod
    app.include_router(indices_mod.router)
    modules['indices'] = indices_mod
    print("Indices routes registered")
except Exception as _ie:
    print(f"Indices failed to load: {_ie}")

try:
    from contacts_ux import router as contacts_router
    app.include_router(contacts_router)
    print("Contacts routes registered")
except ModuleNotFoundError:
    pass

try:
    from soundtrack_ux import router as soundtrack_router
    app.include_router(soundtrack_router)
    print("Soundtrack routes registered")
except ModuleNotFoundError:
    pass

try:
    from wcpr_ux import router as wcpr_router
    app.include_router(wcpr_router)
    print("WCPR routes registered")
except ModuleNotFoundError:
    pass

try:
    from maph_matt_ux import router as maph_matt_router
    app.include_router(maph_matt_router)
    print("MAPH/MATT routes registered")
except ModuleNotFoundError:
    pass

try:
    from settings_ux import router as settings_router
    app.include_router(settings_router)
    print("Settings routes registered")
except ModuleNotFoundError:
    pass

try:
    from bluesky import router as bluesky_router
    app.include_router(bluesky_router)
    print("Bluesky routes registered")
except ModuleNotFoundError:
    pass

try:
    from profiles_ux import router as profiles_router
    app.include_router(profiles_router)
    print("Public player profile routes registered")
except ModuleNotFoundError:
    pass

try:
    from advisor_ux import router as advisor_router
    app.include_router(advisor_router)
    print("Financial Advisor routes registered")
except ModuleNotFoundError:
    pass

try:
    from push_ux import router as push_router, _ensure_rate_limit_table
    app.include_router(push_router)
    _ensure_rate_limit_table()
    print("Push notification routes registered")
except ModuleNotFoundError:
    pass

try:
    from world_map_ux import router as world_map_router
    app.include_router(world_map_router)
    print("World Map routes registered")
except ModuleNotFoundError:
    pass

try:
    from market_ws import router as market_ws_router
    app.include_router(market_ws_router)
    print("Market WebSocket routes registered")
except ModuleNotFoundError:
    pass

try:
    from player_feed_ws import router as player_feed_router
    app.include_router(player_feed_router)
    print("Player Feed WebSocket routes registered")
except ModuleNotFoundError:
    pass

try:
    from company_ux import router as company_router, initialize as company_init
    company_init()
    app.include_router(company_router)
    print("Company/Sitemap routes registered")
except ModuleNotFoundError:
    pass

try:
    import play_billing as _pb_mod
    _pb_mod.init()
    app.include_router(_pb_mod.router)
    register_module("play_billing", _pb_mod)
    print("Play Billing routes registered")
except ModuleNotFoundError:
    pass

try:
    from special_plots_ux import router as special_plots_router
    app.include_router(special_plots_router)
    print("Special Plots routes registered")
except ModuleNotFoundError:
    pass

# Register these three routers INDEPENDENTLY. They were previously grouped in
# one try/except, which meant a single import failure (e.g. a transient DB
# error during port_authority's import-time init_db) silently skipped the
# remaining include_router() calls — 404-ing every endpoint on the others.
# Each gets its own guard now, and failures log a real traceback.
try:
    from port_authority import router as port_authority_router
    app.include_router(port_authority_router)
    print("Port Authority API routes registered")
except ModuleNotFoundError:
    pass
except Exception as _pa_err:
    import traceback
    print(f"[PortAuthority] API routes FAILED to register: {_pa_err}")
    traceback.print_exc()

try:
    from port_authority_ux import router as port_authority_ux_router
    app.include_router(port_authority_ux_router)
    print("Port Authority UX routes registered")
except ModuleNotFoundError:
    pass
except Exception as _pax_err:
    import traceback
    print(f"[PortAuthority] UX routes FAILED to register: {_pax_err}")
    traceback.print_exc()

try:
    from military import router as military_router
    app.include_router(military_router)
    print("Military (Branch Warfare) routes registered")
except ModuleNotFoundError:
    pass
except Exception as _mil_err:
    import traceback
    print(f"[Military] routes FAILED to register: {_mil_err}")
    traceback.print_exc()

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    reload = os.environ.get("ENV", "production") == "development"
    # Bind to all IPv4 interfaces. Cloudflare tunnel connects via 127.0.0.1
    # (IPv4). On systems with IPV6_V6ONLY=1 (e.g. Google Cloud), binding to
    # "::" only accepts IPv6, breaking the tunnel. 0.0.0.0 works everywhere.
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=reload)
