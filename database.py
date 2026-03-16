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

# ---------------------------------------------------------------------------
# Main game database  (wadsworth)
# ---------------------------------------------------------------------------
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/wadsworth",
)
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ---------------------------------------------------------------------------
# Federal-reserve banks database  (reserve_banks)
# ---------------------------------------------------------------------------
RESERVE_DATABASE_URL = os.environ.get(
    "RESERVE_DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/reserve_banks",
)
reserve_engine = create_engine(RESERVE_DATABASE_URL)
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
