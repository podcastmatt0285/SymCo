"""
military_migration.py

One-time burn migration: removes InventoryItem and PortAuthorityInventory rows
whose item_type slug is in REMOVED_GENERICS (the old generic military items
replaced by real-life named equivalents).

A flag row in a dedicated table ensures the migration runs only once,
even across restarts.
"""

from sqlalchemy import Column, String, DateTime, text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

from database import engine, SessionLocal

Base = declarative_base()

# ─────────────────────────────────────────────────────────────────────────────
# Persistence flag
# ─────────────────────────────────────────────────────────────────────────────

class MigrationFlag(Base):
    __tablename__ = "migration_flags"
    name       = Column(String, primary_key=True)
    applied_at = Column(DateTime, default=datetime.utcnow)


# ─────────────────────────────────────────────────────────────────────────────
# Generic slugs to burn
# ─────────────────────────────────────────────────────────────────────────────

REMOVED_GENERICS = frozenset({
    "rifle",
    "fighter_jet",
    "tank",
    "submarine",
    "naval_destroyer",
    "military_helicopter",
    "missile",
    "ammunition",
    "ammunition_crate",
    "grenade",
    "grenade_body",
    "smoke_grenade",
    "wp_grenade",
    "incendiary_rocket",
    "explosive_ordnance",
    "det_cord",
    "artillery_shell",
    "torpedo",
    "drone",
    "military_drone",
    "drone_swarm_unit",
    "machine_gun",
    "apc",
    "infantry_fighting_vehicle",
    "armored_car",
    "main_battle_tank",
    "leo2_leopard_tank",
    "scope",
    "targeting_optic",
    "night_vision_optic",
    "missile_warhead",
    "missile_guidance_unit",
    "rocket_motor",
    "self_propelled_artillery",
    "drone_avionics",
})

MIGRATION_NAME = "burn_generic_military_items_v1"


def run_migration():
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        # Check flag
        flag = db.query(MigrationFlag).filter_by(name=MIGRATION_NAME).first()
        # Schema migration — runs every boot, idempotent via IF NOT EXISTS, and
        # independent of the one-time burn flag below. Port Authority became a
        # true Institution built on a special plot, so it needs special_plot_id.
        # Idempotent schema migrations — run every boot
        schema_ddl = [
            "ALTER TABLE port_authority_instances ADD COLUMN IF NOT EXISTS special_plot_id INTEGER",
            "ALTER TABLE port_authority_instances ADD COLUMN IF NOT EXISTS immigration_volume FLOAT DEFAULT 1.0",
            "ALTER TABLE port_authority_instances ADD COLUMN IF NOT EXISTS immigration_wealth FLOAT DEFAULT 1.0",
            # Mission table redesign (new columns alongside old ones for zero-downtime)
            "ALTER TABLE port_authority_missions ADD COLUMN IF NOT EXISTS mission_subtype VARCHAR",
            "ALTER TABLE port_authority_missions ADD COLUMN IF NOT EXISTS target_player_id INTEGER",
            "ALTER TABLE port_authority_missions ADD COLUMN IF NOT EXISTS target_item_type VARCHAR",
            "ALTER TABLE port_authority_missions ADD COLUMN IF NOT EXISTS target_quantity INTEGER DEFAULT 1",
            "ALTER TABLE port_authority_missions ADD COLUMN IF NOT EXISTS items_acquired TEXT",
            # PA contract tables
            """CREATE TABLE IF NOT EXISTS pa_contracts (
                id SERIAL PRIMARY KEY,
                title VARCHAR NOT NULL,
                description TEXT,
                required_items TEXT NOT NULL,
                payment_usd FLOAT NOT NULL,
                security_deposit_usd FLOAT NOT NULL,
                trophy_reward INTEGER DEFAULT 0,
                fulfillment_days INTEGER DEFAULT 14,
                selection_method VARCHAR DEFAULT 'cheapest',
                bid_opens_at TIMESTAMP NOT NULL,
                bid_closes_at TIMESTAMP NOT NULL,
                status VARCHAR DEFAULT 'bidding',
                winner_player_id INTEGER,
                winning_bid_id INTEGER,
                fulfill_deadline TIMESTAMP,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT NOW()
            )""",
            """CREATE TABLE IF NOT EXISTS pa_contract_bids (
                id SERIAL PRIMARY KEY,
                contract_id INTEGER NOT NULL,
                player_id INTEGER NOT NULL,
                bid_price_usd FLOAT DEFAULT 0.0,
                bid_volume_multiplier FLOAT DEFAULT 1.0,
                deposit_paid_usd FLOAT DEFAULT 0.0,
                status VARCHAR DEFAULT 'pending',
                submitted_at TIMESTAMP DEFAULT NOW(),
                deposit_returned BOOLEAN DEFAULT FALSE
            )""",
            # Drop the old procurement_submissions table if it exists
            "DROP TABLE IF EXISTS procurement_submissions",
        ]
        for ddl in schema_ddl:
            try:
                db.execute(text(ddl))
                db.commit()
            except Exception as _ce:
                db.rollback()
                print(f"[migration] DDL failed: {ddl[:60]}... — {_ce}")

        if flag:
            print(f"[migration] {MIGRATION_NAME}: already applied, skipping.")
            return

        slugs = tuple(REMOVED_GENERICS)
        placeholders = ", ".join(f"'{s}'" for s in slugs)

        # Delete from player inventory
        result1 = db.execute(
            text(f"DELETE FROM inventory_items WHERE item_type IN ({placeholders})")
        )

        # Delete from port authority inventory (if table exists)
        try:
            result2 = db.execute(
                text(f"DELETE FROM port_authority_inventory WHERE item_type IN ({placeholders})")
            )
            pa_deleted = result2.rowcount
        except Exception:
            pa_deleted = 0

        db.add(MigrationFlag(name=MIGRATION_NAME, applied_at=datetime.utcnow()))
        db.commit()
        print(
            f"[migration] {MIGRATION_NAME}: burned {result1.rowcount} inventory rows, "
            f"{pa_deleted} PA inventory rows."
        )
    except Exception as e:
        db.rollback()
        print(f"[migration] {MIGRATION_NAME}: ERROR — {e}")
    finally:
        db.close()
