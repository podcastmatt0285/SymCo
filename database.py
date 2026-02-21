"""
database.py

Central database configuration for SymCo.

Connection settings are read from a .env file in the project root (or from
real environment variables if you prefer).  Copy .env.example to .env and
fill in your values.
"""

import os
from sqlalchemy import create_engine
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
