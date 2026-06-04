"""
database.py

Central database configuration for Wadsworth Economic Tycoon Simulator.

Connection settings are read from a .env file in the project root (or from
real environment variables if you prefer).  Copy .env.example to .env and
fill in your values.
"""

import os
import re
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Load .env file if python-dotenv is installed (optional but recommended).
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Connection-pool settings (shared by every module that imports these engines)
# ---------------------------------------------------------------------------
# SQLAlchemy's defaults (pool_size=5, max_overflow=10) cap the WHOLE app at 15
# concurrent connections — shared by every web request AND the 5-second tick
# loop that opens sessions across ~30 modules. That is far too small: under
# load the pool exhausts, every extra checkout blocks for `pool_timeout`
# seconds and then 5xxs (the /government page, which opens ~12 sessions per
# request, starves first). We also enable pre-ping so a connection Postgres
# dropped while idle is transparently replaced instead of handed out dead
# (the cause of pages that "hang every time" after the server has been up a
# while), and recycle connections periodically to avoid staleness.
#
# Sizes are env-overridable so they can be raised toward Postgres'
# max_connections (default 100) — or pointed at a pooler like PgBouncer —
# without code changes. Defaults below keep main+reserve worst-case well under
# 100: main 20+40 = 60, reserve 10+20 = 30.
_POOL_KW = dict(
    pool_pre_ping=True,
    pool_recycle=_int_env("DB_POOL_RECYCLE", 1800),
    pool_timeout=_int_env("DB_POOL_TIMEOUT", 30),
)

# ---------------------------------------------------------------------------
# Main game database  (wadsworth)
# ---------------------------------------------------------------------------
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/wadsworth",
)
engine = create_engine(
    DATABASE_URL,
    pool_size=_int_env("DB_POOL_SIZE", 20),
    max_overflow=_int_env("DB_MAX_OVERFLOW", 40),
    **_POOL_KW,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ---------------------------------------------------------------------------
# Federal-reserve banks database  (reserve_banks)
# ---------------------------------------------------------------------------
RESERVE_DATABASE_URL = os.environ.get(
    "RESERVE_DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/reserve_banks",
)
reserve_engine = create_engine(
    RESERVE_DATABASE_URL,
    pool_size=_int_env("RESERVE_DB_POOL_SIZE", 10),
    max_overflow=_int_env("RESERVE_DB_MAX_OVERFLOW", 20),
    **_POOL_KW,
)
ReserveSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=reserve_engine)


# ---------------------------------------------------------------------------
# DDL migration helper
# ---------------------------------------------------------------------------

def run_ddl_migration(eng, statements, *, admin_env_var="DATABASE_ADMIN_URL"):
    """
    Execute one or more DDL statements (ALTER TABLE ADD COLUMN etc.) using
    AUTOCOMMIT isolation so they are applied immediately without any
    surrounding transaction.

    Each statement is run independently; a non-privilege failure (e.g. the
    column already exists and no IF NOT EXISTS was used) is silently skipped
    so that repeated startups are safe.

    If the app-user connection raises InsufficientPrivilege / "must be owner",
    ALL statements are retried via an admin connection:
      - Uses the DSN in the env var named by `admin_env_var`
        (DATABASE_ADMIN_URL for the main DB,
         RESERVE_DATABASE_ADMIN_URL for the reserve DB).
      - If the env var is not set, substitutes postgres:postgres into the
        engine's own URL as a best-effort fallback.

    Logs outcome to stdout; does not raise.
    """
    stmts = [statements] if isinstance(statements, str) else list(statements)

    def _run(target_eng):
        with target_eng.connect().execution_options(
            isolation_level="AUTOCOMMIT"
        ) as _c:
            for s in stmts:
                try:
                    _c.execute(text(s))
                except Exception as _se:
                    _priv = (
                        "InsufficientPrivilege" in type(_se).__name__
                        or "must be owner" in str(_se)
                    )
                    if _priv:
                        raise  # escalate so the admin-fallback path runs
                    # non-privilege failure (e.g. duplicate column) — skip silently

    # --- attempt 1: app user ---
    try:
        _run(eng)
        return
    except Exception as _e1:
        _priv1 = (
            "InsufficientPrivilege" in type(_e1).__name__
            or "must be owner" in str(_e1)
        )
        if not _priv1:
            print(f"[DDL] Migration error (app user): {_e1}")
            return

    # --- attempt 2: admin/superuser ---
    admin_url = os.environ.get(admin_env_var) or re.sub(
        r"(\w+://)[^:@]+:[^@]*@", r"\1postgres:postgres@", str(eng.url)
    )
    _admin = create_engine(admin_url)
    try:
        _run(_admin)
        print("[DDL] Migration applied via admin connection.")
    except Exception as _e2:
        print(
            "[DDL] MANUAL MIGRATION REQUIRED — app and admin users both lack "
            "ALTER TABLE privilege.\n"
            "  Run the following SQL as the table owner:\n"
            + "\n".join(f"    {s};" for s in stmts) + "\n"
            f"  Or set {admin_env_var} to a superuser DSN.\n"
            f"  Error: {_e2}"
        )
    finally:
        _admin.dispose()
