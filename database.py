"""
database.py

Central database configuration for SymCo.

Set the following environment variables to configure database connections:
  DATABASE_URL          - Main game database (wadsworth)
  RESERVE_DATABASE_URL  - Federal reserve banks database

Example (PostgreSQL):
  DATABASE_URL=postgresql://postgres:password@localhost:5432/wadsworth
  RESERVE_DATABASE_URL=postgresql://postgres:password@localhost:5432/reserve_banks
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

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
