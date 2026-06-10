"""
auth.py

Authentication module for the economic simulation.
Handles:
- Player login
- Player registration
- Session management
- Password hashing
- Database models for players
- Cash transfers between players
"""

from datetime import datetime, timedelta
from typing import Optional
import secrets
import hashlib
from fastapi import APIRouter, Form, Cookie, Response, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import Column, String, DateTime, Integer, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# ==========================
# DATABASE SETUP
# ==========================
from database import engine, SessionLocal
from skin_utils import skin_links as _skin_links
Base = declarative_base()

# ==========================
# DATABASE MODELS
# ==========================
class Player(Base):
    """Player account model."""
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    business_name = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, default=datetime.utcnow)
    tutorial_step   = Column(Integer, default=0)  # 0=not started, 1-10=active, 11=complete
    tutorial_3_step = Column(Integer, default=0)  # 0=not started, 1-6=active, 7=reward pending, 8=complete
    tutorial_4_step = Column(Integer, default=0)  # 0=not started, 1-6=active, 7=complete
    tutorial_5_step = Column(Integer, default=0)  # 0=not started, 1-6=active, 7=complete
    tutorial_6_step = Column(Integer, default=0)  # 0=not started, 1-6=active, 7=complete
    tutorial_7_step = Column(Integer, default=0)  # 0=not started, 1-7=active, 8=complete
    is_npc = Column(Boolean, default=False)           # True for NPC accounts
    npc_config_key = Column(String, nullable=True)    # Links to npc_configs/<key>.json
    # Notification preferences
    notif_sounds = Column(Boolean, default=True)       # Play sounds for in-game notifications
    notif_badge  = Column(Boolean, default=True)       # Show unread badge on app icon (Badging API)
    notif_push_dms          = Column(Boolean, default=True)  # Push: new DMs
    notif_push_contracts    = Column(Boolean, default=True)  # Push: contract updates
    notif_push_business     = Column(Boolean, default=True)  # Push: business alerts (wages, stock, inputs)
    notif_push_land         = Column(Boolean, default=True)  # Push: land sales and efficiency floor
    notif_push_execs        = Column(Boolean, default=True)  # Push: executive hired/fired/quit/retired/school
    notif_push_trades       = Column(Boolean, default=True)  # Push: trusted trade swap events
    notif_push_corporate    = Column(Boolean, default=True)  # Push: acquisition offers and income sweeps
    notif_push_govt         = Column(Boolean, default=True)  # Push: gov taxes, liens, city membership
    notif_push_tasks_events = Column(Boolean, default=True)  # Push: task completions and event notifications
    notif_push_annuities    = Column(Boolean, default=True)  # Push: annuity maturity
    notif_push_institutions = Column(Boolean, default=True)  # Push: institution/mint alerts (tax, minting)
    notif_push_indices      = Column(Boolean, default=True)  # Push: market index alerts (GFI extremes, WBC-50 moves)
    # Federal Communications Commission (FCC) licence — NULL = none active; datetime = expiry (UTC)
    cco_rental_expires = Column(DateTime, nullable=True, default=None)
    # Cosmetic skin (filename without .css extension; must exist in static/skins/)
    skin       = Column(String(64), default="default", nullable=False)
    # Wadsworth Pro subscriber — set by server after Google Play purchaseToken is verified.
    # Admins are always treated as Pro regardless of this flag (checked via admins.is_admin).
    subscriber = Column(Boolean, default=False, nullable=False)
    # City Perk (Pro subscriber perk) — one-time redemption, two mutually exclusive paths:
    #   city_perk_choice = NULL        → not yet redeemed
    #                    = "free_city"  → redeemed option A (founded a free city)
    #                    = "perks"      → redeemed option B (chose city-wide perks below)
    # city_perks = JSON list of up to 3 perk keys (from city_perks.PERK_CATALOG). These are
    # city-wide buffs that travel with the player: active for whatever city they belong to,
    # dormant when they have no city, and auto-apply when they later join/found one.
    city_perk_choice = Column(String(16), nullable=True, default=None)
    city_perks       = Column(Text, nullable=True, default=None)

    @property
    def cash_balance(self) -> float:
        """USD balance stored in PlayerCurrencyBalance (reserve_banks DB)."""
        try:
            from reserve_banks import get_usd_balance
            return get_usd_balance(self.id)
        except Exception:
            return 0.0

    @cash_balance.setter
    def cash_balance(self, value: float):
        try:
            from reserve_banks import set_usd_balance
            set_usd_balance(self.id, value)
        except Exception as e:
            print(f"[Player] cash_balance setter error for player {self.id}: {e}")


class PlayerRegistrationIP(Base):
    """
    Tracks every IP address a player account was ever registered from.
    Kept in a separate table so we never need to ALTER the players table
    (which requires ownership in PostgreSQL).  One row is written at
    account creation; the multi-account detector queries this table.
    """
    __tablename__ = "player_registration_ips"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    player_id = Column(Integer, index=True, nullable=False)
    ip_address = Column(String, nullable=False, index=True)
    user_agent = Column(String, nullable=True)   # browser fingerprint signal
    registered_at = Column(DateTime, default=datetime.utcnow)


class PushSubscription(Base):
    """Stores browser push subscriptions for web push notifications."""
    __tablename__ = "push_subscriptions"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    player_id  = Column(Integer, index=True, nullable=False)
    endpoint   = Column(String, nullable=False)
    auth       = Column(String, nullable=False)
    p256dh     = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class PlayerLoginIP(Base):
    """
    Records the IP address and user-agent on every successful login.
    Used for post-registration multi-account detection: two accounts that
    repeatedly log in from the same IP are strong candidates for alts even
    if they registered from different IPs (e.g. VPN rotated at registration).
    """
    __tablename__ = "player_login_ips"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    player_id = Column(Integer, index=True, nullable=False)
    ip_address = Column(String, nullable=False, index=True)
    user_agent = Column(String, nullable=True)
    logged_in_at = Column(DateTime, default=datetime.utcnow)


class Session(Base):
    """Session model for authentication."""
    __tablename__ = "sessions"

    session_token = Column(String, primary_key=True, index=True)
    player_id = Column(Integer, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)


class WidgetDeviceLink(Base):
    """Maps a hashed Android device ID to a player — persists across restarts."""
    __tablename__ = "widget_device_links"

    device_hash = Column(String, primary_key=True, index=True)
    player_id   = Column(Integer, nullable=False, index=True)
    linked_at   = Column(DateTime, default=datetime.utcnow)

# ==========================
# SESSION STORAGE
# ==========================
active_sessions = {}
SESSION_DURATION = timedelta(days=7)

# ==========================
# HELPER FUNCTIONS
# ==========================
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, password_hash: str) -> bool:
    return hash_password(password) == password_hash

def create_session_token() -> str:
    return secrets.token_urlsafe(32)

def get_db():
    db = SessionLocal()
    try:
        return db
    except Exception as e:
        print(f"[Auth] Database error: {e}")
        db.close()
        raise


def migrate_player_table():
    """Apply incremental schema migrations for the players table."""
    from database import run_ddl_migration
    run_ddl_migration(engine, [
        "ALTER TABLE players ADD COLUMN IF NOT EXISTS tutorial_step INTEGER DEFAULT 0",
        "ALTER TABLE players ADD COLUMN IF NOT EXISTS tutorial_3_step INTEGER DEFAULT 0",
        "ALTER TABLE players ADD COLUMN IF NOT EXISTS tutorial_4_step INTEGER DEFAULT 0",
        "ALTER TABLE players ADD COLUMN IF NOT EXISTS tutorial_5_step INTEGER DEFAULT 0",
        "ALTER TABLE players ADD COLUMN IF NOT EXISTS tutorial_6_step INTEGER DEFAULT 0",
        "ALTER TABLE players ADD COLUMN IF NOT EXISTS tutorial_7_step INTEGER DEFAULT 0",
        "ALTER TABLE players ADD COLUMN IF NOT EXISTS notif_push_tasks_events BOOLEAN DEFAULT TRUE",
        "ALTER TABLE players ADD COLUMN IF NOT EXISTS is_npc BOOLEAN DEFAULT FALSE",
        "ALTER TABLE players ADD COLUMN IF NOT EXISTS npc_config_key VARCHAR(128)",
        "ALTER TABLE players ADD COLUMN IF NOT EXISTS notif_sounds BOOLEAN DEFAULT TRUE",
        "ALTER TABLE players ADD COLUMN IF NOT EXISTS notif_badge BOOLEAN DEFAULT TRUE",
        "ALTER TABLE players ADD COLUMN IF NOT EXISTS notif_push_dms BOOLEAN DEFAULT TRUE",
        "ALTER TABLE players ADD COLUMN IF NOT EXISTS notif_push_contracts BOOLEAN DEFAULT TRUE",
        "ALTER TABLE players ADD COLUMN IF NOT EXISTS notif_push_business  BOOLEAN DEFAULT TRUE",
        "ALTER TABLE players ADD COLUMN IF NOT EXISTS notif_push_land      BOOLEAN DEFAULT TRUE",
        "ALTER TABLE players ADD COLUMN IF NOT EXISTS notif_push_execs     BOOLEAN DEFAULT TRUE",
        "ALTER TABLE players ADD COLUMN IF NOT EXISTS notif_push_trades    BOOLEAN DEFAULT TRUE",
        "ALTER TABLE players ADD COLUMN IF NOT EXISTS notif_push_corporate BOOLEAN DEFAULT TRUE",
        "ALTER TABLE players ADD COLUMN IF NOT EXISTS notif_push_govt      BOOLEAN DEFAULT TRUE",
        "ALTER TABLE players ADD COLUMN IF NOT EXISTS notif_push_annuities BOOLEAN DEFAULT TRUE",
        "ALTER TABLE players ADD COLUMN IF NOT EXISTS notif_push_institutions BOOLEAN DEFAULT TRUE",
        "ALTER TABLE players ADD COLUMN IF NOT EXISTS notif_push_indices BOOLEAN DEFAULT TRUE",
        "ALTER TABLE players ADD COLUMN IF NOT EXISTS cco_rental_expires TIMESTAMP",
        "ALTER TABLE players ADD COLUMN IF NOT EXISTS skin VARCHAR(64) DEFAULT 'default'",
        "ALTER TABLE players ADD COLUMN IF NOT EXISTS subscriber BOOLEAN DEFAULT FALSE",
        "ALTER TABLE players ADD COLUMN IF NOT EXISTS city_perk_choice VARCHAR(16)",
        "ALTER TABLE players ADD COLUMN IF NOT EXISTS city_perks TEXT",
    ])


def migrate_push_subscriptions():
    """Create the push_subscriptions and system_config tables if they don't exist,
    and seed default VAPID keys so the server never needs to generate them at runtime."""
    from database import run_ddl_migration
    run_ddl_migration(engine, [
        """CREATE TABLE IF NOT EXISTS push_subscriptions (
            id         SERIAL PRIMARY KEY,
            player_id  INTEGER NOT NULL,
            endpoint   TEXT    NOT NULL,
            auth       TEXT    NOT NULL,
            p256dh     TEXT    NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        )""",
        """CREATE TABLE IF NOT EXISTS system_config (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )""",
        # Seed pre-generated VAPID keys so the server never needs pycryptodome at startup.
        # Override by setting VAPID_PUBLIC_KEY + VAPID_PRIVATE_KEY env vars (takes priority).
        """INSERT INTO system_config (key, value)
           VALUES ('vapid_keys', '{"private_key": "-----BEGIN PRIVATE KEY-----\\nMIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQgLpELWaFlOCv7djyF\\nQEMVsSqA7Iaok/xU43IH4/ocbBahRANCAASy4lHt6mu/IWf/UhGLPSZ1XTC521Le\\nns+V/JCQD7HTL1c13Y6HQ4MJsTSchVhFtFSbVAHXPHvYV6ERnWwAfilV\\n-----END PRIVATE KEY-----", "public_key": "BLLiUe3qa78hZ_9SEYs9JnVdMLnbUt6ez5X8kJAPsdMvVzXdjodDgwmxNJyFWEW0VJtUAdc8e9hXoRGdbAB-KVU"}')
           ON CONFLICT (key) DO NOTHING""",
    ])


def migrate_ip_tables():
    """Add columns that were appended to existing IP-tracking tables."""
    from database import run_ddl_migration
    # user_agent was added after the initial table creation.
    run_ddl_migration(
        engine,
        "ALTER TABLE player_registration_ips ADD COLUMN IF NOT EXISTS user_agent TEXT",
    )

    # cash_balance has moved to PlayerCurrencyBalance in the reserve_banks DB.
    # Before dropping the column, rescue any non-zero values into PlayerCurrencyBalance
    # so no player USD is silently lost during migration.
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            col_exists = conn.execute(text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name='players' AND column_name='cash_balance' LIMIT 1"
            )).fetchone()
            if col_exists:
                rows = conn.execute(text(
                    "SELECT id, cash_balance FROM players WHERE cash_balance > 0"
                )).fetchall()
                if rows:
                    from reserve_banks import get_usd_balance, credit_usd
                    for row in rows:
                        pid, legacy_bal = row[0], float(row[1])
                        # Only credit if the player has no PCB USD yet (avoid double-credit)
                        if legacy_bal > 0 and get_usd_balance(pid) == 0:
                            credit_usd(pid, legacy_bal)
                            print(f"[Auth] Rescued ${legacy_bal:,.4f} legacy USD for player {pid} → PlayerCurrencyBalance")
    except Exception as e:
        print(f"[Auth] cash_balance rescue check: {e}")

    run_ddl_migration(
        engine,
        "ALTER TABLE players DROP COLUMN IF EXISTS cash_balance",
    )


# ==========================
# CASH TRANSFER
# ==========================
def transfer_cash(from_player_id: int, to_player_id: int, amount: float) -> bool:
    """
    Safely transfer cash between two players.
    Used by Market module for trades.

    Respects each player's legal tender: the sender pays in their currency
    (via spend_player_funds) and the receiver is credited in theirs
    (via process_income_conversion).  All balances live in PlayerCurrencyBalance.

    Returns:
        True if successful, False if insufficient funds
    """
    if amount <= 0:
        return False

    from reserve_banks import can_afford_usd, spend_player_funds, process_income_conversion

    if not can_afford_usd(from_player_id, amount):
        print(f"[Auth] Transfer failed: Player {from_player_id} has insufficient funds")
        return False

    ok, _err = spend_player_funds(from_player_id, amount)
    if not ok:
        print(f"[Auth] Transfer failed: {_err}")
        return False

    # Credit receiver in their legal tender (process_income_conversion handles all currencies)
    process_income_conversion(to_player_id, amount)

    print(f"[Auth] Transferred ${amount:.2f} from Player {from_player_id} to Player {to_player_id}")
    return True

# ==========================
# BUSINESS NAME FILTER
# ==========================
import os as _os, re as _re, unicodedata as _ud

# Homoglyph characters that survive NFKD decomposition but look like ASCII letters.
# Covers common Unicode bypass attempts: Cyrillic, IPA, Greek, Armenian confusables.
_HOMOGLYPHS = str.maketrans({
    # ── Cyrillic lowercase (most common bypass chars) ──
    "а": "a",  # а Cyrillic a
    "е": "e",  # е Cyrillic ie
    "ё": "e",  # ё Cyrillic io
    "з": "e",  # з Cyrillic ze (looks like 3; map directly to e, skipping leet step)
    "і": "i",  # і Cyrillic byelorussian i
    "о": "o",  # о Cyrillic o
    "р": "p",  # р Cyrillic er
    "с": "c",  # с Cyrillic es
    "у": "y",  # у Cyrillic u
    "х": "x",  # х Cyrillic ha
    "г": "g",  # г Cyrillic ge
    "д": "d",  # д Cyrillic de
    "м": "m",  # м Cyrillic em
    "в": "b",  # в Cyrillic ve (looks like b)
    "ф": "f",  # ф Cyrillic ef
    "ш": "w",  # ш Cyrillic sha
    "ю": "u",  # ю Cyrillic yu
    "я": "a",  # я Cyrillic ya (looks like backwards R, closest to a)
    "ь": "b",  # ь Cyrillic soft sign
    "ъ": "b",  # ъ Cyrillic hard sign
    "н": "h",  # н Cyrillic en (looks like h)
    "ц": "c",  # ц Cyrillic tse
    "п": "n",  # п Cyrillic pe (looks like n)
    "ѕ": "s",  # ѕ Cyrillic dze
    "ј": "j",  # ј Cyrillic je
    "һ": "h",  # һ Cyrillic shha
    # ── Cyrillic uppercase ──
    "А": "a",  # А Cyrillic capital A
    "Е": "e",  # Е Cyrillic capital IE
    "О": "o",  # О Cyrillic capital O
    "Р": "p",  # Р Cyrillic capital ER
    "С": "c",  # С Cyrillic capital ES
    "Х": "x",  # Х Cyrillic capital HA
    "В": "b",  # В Cyrillic capital VE
    "М": "m",  # М Cyrillic capital EM
    "Н": "h",  # Н Cyrillic capital EN
    # ── Greek lowercase ──
    "α": "a",  # α alpha
    "β": "b",  # β beta
    "γ": "g",  # γ gamma
    "δ": "d",  # δ delta
    "ε": "e",  # ε epsilon
    "θ": "o",  # θ theta (closest visual to o)
    "ι": "i",  # ι iota
    "μ": "u",  # μ mu
    "ν": "v",  # ν nu
    "ο": "o",  # ο omicron
    "ρ": "p",  # ρ rho
    "σ": "o",  # σ sigma (visual similarity to o)
    "τ": "t",  # τ tau
    "υ": "u",  # υ upsilon
    "ω": "w",  # ω omega
    # ── Greek uppercase ──
    "Α": "a",  # Α capital alpha
    "Β": "b",  # Β capital beta
    "Ε": "e",  # Ε capital epsilon
    "Ι": "i",  # Ι capital iota
    "Ο": "o",  # Ο capital omicron
    "Ρ": "p",  # Ρ capital rho
    "Τ": "t",  # Τ capital tau
    # ── IPA / Latin extensions ──
    "ɡ": "g",  # ɡ Latin script g (U+0261)
    "ɢ": "g",  # ɢ Latin small capital G
    "ɪ": "i",  # ɪ Latin small capital I
    "ı": "i",  # ı Latin dotless i
    # ── Armenian ──
    "ո": "u",  # ո Armenian vo
    "չ": "c",  # չ Armenian cha
})

def _normalize_for_filter(s: str) -> str:
    """
    Normalize for blocklist substring matching:
      1. Strip zero-width / invisible Unicode spacers evaders insert between chars
      2. Explicit homoglyph map for chars that survive NFKD (Cyrillic, IPA, Greek confusables)
      3. Unicode NFKD decomposition — turns fullwidth chars and accented letters into ASCII
      4. Strip diacritics and any remaining non-ASCII
      5. Lowercase
      6. Leet-speak collapse: 0->o 1->i 3->e 4->a 5->s @->a $->s !->i 7->t
      7. Collapse 3+ repeated chars to exactly 2: "fagggot" -> "faggot", "niggggger" -> "nigger"
      8. Strip all punctuation, spaces, separators
    """
    # Zero-width spaces, joiners, soft-hyphens, Arabic/Mongolian formatting marks
    s = _re.sub(r"[­؜᠎​‌‍⁠-⁤﻿]", "", s)
    s = s.translate(_HOMOGLYPHS)
    s = _ud.normalize("NFKD", s)
    s = s.encode("ascii", errors="ignore").decode("ascii")
    s = s.lower()
    for src, dst in [("0","o"),("1","i"),("3","e"),("4","a"),("5","s"),("@","a"),("$","s"),("!","i"),("7","t")]:
        s = s.replace(src, dst)
    # Collapse runs of 3+ identical chars to exactly 2: catches "fagggot"->"faggot",
    # "niggggger"->"niger", while keeping "kkk"->"kk" (not "k") to avoid mass false-positives.
    s = _re.sub(r"(.)\1{2,}", r"\1\1", s)
    s = _re.sub(r"[\s\-_.,!?'\"*/\\|+=#%^&(){}\[\]<>~`]", "", s)
    return s

_BLOCKED_TERMS: set = set()

_BLOCKED_TERMS: set = set()
# Terms long enough for a safe reverse-string check (≥5 chars).
# Short terms like "wop" (3 chars) are excluded because their reverse appears in
# legitimate words — e.g. "wop" reversed is "pow", which is a substring of "power".
_BLOCKED_TERMS_LONG: set = set()

def _load_blocked_terms():
    global _BLOCKED_TERMS, _BLOCKED_TERMS_LONG
    path = _os.path.join(_os.path.dirname(__file__), "blocked_names.txt")
    try:
        with open(path) as f:
            raw = {_normalize_for_filter(line.strip()) for line in f if line.strip() and not line.startswith("#")}
        raw.discard("")
        _BLOCKED_TERMS = raw
        _BLOCKED_TERMS_LONG = {t for t in raw if len(t) >= 5}
    except FileNotFoundError:
        print("[Auth] WARNING: blocked_names.txt not found — content filtering disabled!")

_load_blocked_terms()

def _contains_slur(normalized: str) -> bool:
    """Substring check (forward) + reverse check only for long terms."""
    rev = normalized[::-1]
    for term in _BLOCKED_TERMS:
        if term in normalized:
            return True
    for term in _BLOCKED_TERMS_LONG:
        if term in rev:
            return True
    return False

def validate_business_name(name: str):
    """Returns None if acceptable, or an error string if not."""
    stripped = name.strip()
    if len(stripped) < 2:
        return "Business name must be at least 2 characters"
    if len(stripped) > 40:
        return "Business name must be 40 characters or fewer"
    if _contains_slur(_normalize_for_filter(stripped)):
        return "Business name contains prohibited content"
    return None

def contains_prohibited_content(text: str) -> bool:
    """Returns True if text contains any blocked term (for chat/DM filtering)."""
    return _contains_slur(_normalize_for_filter(text))

# ==========================
# AUTHENTICATION LOGIC
# ==========================
def create_player(db: Session, business_name: str, password: str,
                  ip_address: Optional[str] = None,
                  user_agent: Optional[str] = None) -> Optional[Player]:
    """Create a new player account."""
    existing = db.query(Player).filter(Player.business_name == business_name).first()
    if existing:
        return None

    player = Player(
        business_name=business_name,
        password_hash=hash_password(password),
    )

    db.add(player)
    db.commit()
    db.refresh(player)

    if ip_address:
        db.add(PlayerRegistrationIP(
            player_id=player.id,
            ip_address=ip_address,
            user_agent=user_agent,
        ))
        db.commit()

    player_id = player.id
    print(f"[Auth] Created player {player_id}: {business_name}")
    try:
        from admin_notifications import notify_new_player
        notify_new_player(business_name, player_id)
    except Exception:
        pass

    # Seed starting USD balance in the reserve_banks DB (USD is a reserve currency)
    try:
        from reserve_banks import credit_usd
        credit_usd(player_id, 50000.0)
        print(f"[Auth] Seeded $50,000 USD for player {player_id}")
    except Exception as e:
        print(f"[Auth] Failed to seed starting USD balance: {e}")
        import traceback
        traceback.print_exc()
    
    # Create starter land plot
    try:
        from land import create_starter_plot
        create_starter_plot(player_id)
        create_starter_plot(player_id)
        create_starter_plot(player_id)
        print(f"[Auth] Created 3 starter land plots for player {player_id}")
    except Exception as e:
        print(f"[Auth] Failed to create starter plot: {e}")
        import traceback
        traceback.print_exc()
    
    # Ensure admin is an accepted contact for every new player
    try:
        from contacts import ensure_admin_contact
        ensure_admin_contact(player_id)
        print(f"[Auth] Seeded admin contact for player {player_id}")
    except Exception as e:
        print(f"[Auth] Failed to seed admin contact: {e}")

    # Give starter inventory
    try:
        from market import give_starter_inventory
        starter_items = give_starter_inventory(player_id)
        print(f"[Auth] Gave starter inventory to player {player_id}: {starter_items}")
    except Exception as e:
        print(f"[Auth] Failed to give starter inventory: {e}")
        import traceback
        traceback.print_exc()
    
    return player

def authenticate_player(db: Session, business_name: str, password: str) -> Optional[Player]:
    """Authenticate a player."""
    player = db.query(Player).filter(Player.business_name == business_name).first()
    
    if not player:
        return None
    
    if not verify_password(password, player.password_hash):
        return None
    
    player.last_login = datetime.utcnow()
    db.commit()
    
    return player

def create_session(db: Session, player_id: int) -> str:
    """Create a new session for a player."""
    token = create_session_token()
    expires_at = datetime.utcnow() + SESSION_DURATION
    
    session = Session(
        session_token=token,
        player_id=player_id,
        expires_at=expires_at
    )
    db.add(session)
    db.commit()
    
    active_sessions[token] = player_id
    
    return token

def get_player_from_session(db: Session, session_token: Optional[str]) -> Optional[Player]:
    """Get player from session token."""
    if not session_token:
        return None
    
    # Check memory cache first
    if session_token in active_sessions:
        player_id = active_sessions[session_token]
        player = db.query(Player).filter(Player.id == player_id).first()
        return player
    
    # Check database
    session = db.query(Session).filter(Session.session_token == session_token).first()
    
    if not session:
        return None
    
    # Check if expired
    if session.expires_at < datetime.utcnow():
        db.delete(session)
        db.commit()
        return None
    
    # Load into cache
    active_sessions[session_token] = session.player_id
    
    player = db.query(Player).filter(Player.id == session.player_id).first()
    return player

# ==========================
def validate_session_ws(session_token: str):
    """Validate a session token for WebSocket use. Returns Player or None."""
    try:
        db = get_db()
        player = get_player_from_session(db, session_token)
        db.close()
        return player
    except Exception:
        return None


# ==========================
# ROUTER
# ==========================
router = APIRouter()

@router.get("/login", response_class=HTMLResponse)
def login_page(session_token: Optional[str] = Cookie(None)):
    """Login/Register splash screen."""
    db = get_db()
    player = get_player_from_session(db, session_token)
    db.close()
    
    if player:
        return RedirectResponse(url="/", status_code=303)
    
    _skin_tags = _skin_links(None)

    # ── Market Indices card (same data as /banks page card) ──
    _indices_card = ""
    try:
        from banks.indices import INDICES, _get_history, _fmt, _pct_change
        _snaps = _get_history("WBC50", 2)
        _wbc_now  = _snaps[-1].value if _snaps else 0.0
        _wbc_prev = _snaps[0].value  if len(_snaps) >= 2 else _wbc_now
        _wbc_ch   = _pct_change(_wbc_now, _wbc_prev)
        _wbc_str  = _fmt(_wbc_now, "USD")
        _wbc_col  = "#22c55e" if _wbc_ch >= 0 else "#ef4444"
        _wbc_arrow = "▲" if _wbc_ch >= 0 else "▼"
        _gfi_snaps = _get_history("GFI", 1)
        _gfi_val   = _gfi_snaps[-1].value if _gfi_snaps else 50.0
        _gfi_col   = ("#dc2626" if _gfi_val <= 24 else "#f97316" if _gfi_val <= 44
                      else "#eab308" if _gfi_val <= 55 else "#22c55e")
        _gfi_label = ("Extreme Fear" if _gfi_val <= 24 else "Fear" if _gfi_val <= 44
                      else "Neutral" if _gfi_val <= 55 else "Greed" if _gfi_val <= 75
                      else "Extreme Greed")
        _indices_card = f'''
        <div class="card" style="border:1px solid #7c3aed;background:linear-gradient(135deg,#0f172a 0%,#1e1b4b 100%);margin-top:20px;">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                <div>
                    <h3 style="margin:0;">📊 Market Indices</h3>
                    <p style="color:#64748b;margin-top:5px;font-size:.85rem;">
                        {len(INDICES)} composite indices tracking the Wadsworth economy in real time.
                    </p>
                </div>
                <span class="badge" style="background:#7c3aed;">LIVE</span>
            </div>
            <div style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:15px;margin-top:16px;">
                <div>
                    <div style="color:#64748b;font-size:.8rem;">WBC-50</div>
                    <div style="font-size:1.1rem;font-weight:bold;color:#38bdf8;">{_wbc_str}</div>
                    <div style="font-size:.72rem;color:{_wbc_col};">{_wbc_arrow} {abs(_wbc_ch):.2f}%</div>
                </div>
                <div>
                    <div style="color:#64748b;font-size:.8rem;">Greed &amp; Fear</div>
                    <div style="font-size:1.1rem;font-weight:bold;color:{_gfi_col};">{_gfi_val:.0f}</div>
                    <div style="font-size:.72rem;color:{_gfi_col};">{_gfi_label}</div>
                </div>
                <div>
                    <div style="color:#64748b;font-size:.8rem;">Indices</div>
                    <div style="font-size:1.1rem;font-weight:bold;color:#a78bfa;">{len(INDICES)}</div>
                    <div style="font-size:.72rem;color:#64748b;">active</div>
                </div>
                <div>
                    <div style="color:#64748b;font-size:.8rem;">Coverage</div>
                    <div style="font-size:1.1rem;font-weight:bold;color:#34d399;">Global</div>
                    <div style="font-size:.72rem;color:#64748b;">economy</div>
                </div>
            </div>
            <div style="margin-top:16px;">
                <a href="/banks/indices/unloggedin" class="btn-blue" style="background:#7c3aed;">View All Indices</a>
            </div>
        </div>'''
    except Exception:
        pass

    # ── Live leaderboard (read-only preview, same data as /stats/leaderboard) ──
    _leaderboard_section = ""
    try:
        from stats_ux import PlayerStats, get_db as _stats_db
        _sdb = _stats_db()
        _top = (
            _sdb.query(PlayerStats, Player)
            .join(Player, Player.id == PlayerStats.player_id)
            .filter(Player.is_npc.isnot(True), PlayerStats.player_id > 0)
            .order_by(PlayerStats.total_net_worth.desc())
            .limit(50)
            .all()
        )
        _sdb.close()
        # Trophy / level data (separate DB)
        try:
            from events import PlayerRank, SessionLocal as _ESL
            _edb = _ESL()
            _rank_rows = _edb.query(PlayerRank).all()
            _edb.close()
            _tmap = {r.player_id: (r.trophies or 0, r.level or 1) for r in _rank_rows}
        except Exception:
            _tmap = {}

        def _money(v):
            return f"${v or 0:,.0f}"

        _lb_rows = ""
        for _rank, (_s, _p) in enumerate(_top, 1):
            _troph, _lvl = _tmap.get(_p.id, (0, 1))
            if _rank == 1:
                _rank_cell = '<span class="lb-badge lb-gold">1st</span>'
            elif _rank == 2:
                _rank_cell = '<span class="lb-badge lb-silver">2nd</span>'
            elif _rank == 3:
                _rank_cell = '<span class="lb-badge lb-bronze">3rd</span>'
            else:
                _rank_cell = str(_rank)
            _name = (_p.business_name or "—").replace("<", "&lt;").replace(">", "&gt;")
            _lb_rows += (
                f'<tr data-nw="{_s.total_net_worth or 0:.2f}" data-cash="{_s.cash_balance or 0:.2f}" '
                f'data-land="{_s.land_value or 0:.2f}" data-inv="{_s.inventory_value or 0:.2f}" '
                f'data-shares="{_s.share_value or 0:.2f}" data-biz="{_s.business_value or 0:.2f}" '
                f'data-trophies="{_troph:.0f}">'
                f'<td class="lb-rank">{_rank_cell}</td>'
                f'<td class="lb-name">{_name}</td>'
                f'<td data-col="nw">{_money(_s.total_net_worth)}</td>'
                f'<td data-col="cash">{_money(_s.cash_balance)}</td>'
                f'<td data-col="land">{_money(_s.land_value)}</td>'
                f'<td data-col="inv">{_money(_s.inventory_value)}</td>'
                f'<td data-col="shares">{_money(_s.share_value)}</td>'
                f'<td data-col="biz">{_money(_s.business_value)}'
                f'<span style="color:#64748b;"> · {_s.businesses_owned or 0}</span></td>'
                f'<td data-col="trophies"><span class="lb-trophy">{_troph:,}</span> '
                f'<span style="color:#64748b;">&#9733;</span>'
                f'<span class="lb-level">Lv {_lvl}</span></td>'
                f'</tr>'
            )

        if _lb_rows:
            _leaderboard_section = f'''
                <div class="lb-section">
                    <div class="lb-heading">🏆 Live Leaderboard</div>
                    <div class="lb-sub">The top {len(_top)} tycoons in the Wadsworth economy. Tap a category to re-rank.</div>
                    <div class="lb-tabs">
                        <span class="lb-tab active" data-metric="nw"       onclick="lbSort('nw',this)">Net Worth</span>
                        <span class="lb-tab"        data-metric="cash"     onclick="lbSort('cash',this)">Cash</span>
                        <span class="lb-tab"        data-metric="land"     onclick="lbSort('land',this)">Land</span>
                        <span class="lb-tab"        data-metric="inv"      onclick="lbSort('inv',this)">Inventory</span>
                        <span class="lb-tab"        data-metric="shares"   onclick="lbSort('shares',this)">Shares</span>
                        <span class="lb-tab"        data-metric="biz"      onclick="lbSort('biz',this)">Businesses</span>
                        <span class="lb-tab"        data-metric="trophies" onclick="lbSort('trophies',this)">&#9733; Trophies</span>
                    </div>
                    <div class="lb-table-wrap">
                        <table class="lb-table" id="lb-table">
                            <thead>
                                <tr>
                                    <th>#</th>
                                    <th>Tycoon</th>
                                    <th data-col="nw" class="lb-col-active">Net Worth</th>
                                    <th data-col="cash">Cash</th>
                                    <th data-col="land">Land</th>
                                    <th data-col="inv">Inventory</th>
                                    <th data-col="shares">Shares</th>
                                    <th data-col="biz">Businesses</th>
                                    <th data-col="trophies">&#9733; Trophies</th>
                                </tr>
                            </thead>
                            <tbody id="lb-body">{_lb_rows}</tbody>
                        </table>
                    </div>
                </div>'''
            # Mark the Net Worth column cells active on initial render
            _leaderboard_section = _leaderboard_section.replace('<td data-col="nw">', '<td data-col="nw" class="lb-col-active">')
    except Exception:
        pass

    return ("""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Login · Wadsworth</title>
    <link rel="manifest" href="/manifest.json">
    <meta name="theme-color" content="#020617">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-title" content="Wadsworth">
    <link rel="apple-touch-icon" href="/static/icons/apple-touch-icon.png">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@700;900&family=EB+Garamond:ital@0;1&display=swap" rel="stylesheet">
        """ + _skin_tags + """
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #0b1220;
            color: #e5e7eb;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding-bottom: 160px;
        }

        .splash {
            max-width: 600px;
            width: 100%;
            padding: 32px;
        }

        /* ── Market tickers (walnut, fixed above footer) ── */
        .login-tickers {
            position: fixed;
            bottom: 44px; /* fallback — overridden by JS to match actual footer height */
            left: 0;
            right: 0;
            z-index: 100;
            background: #1A0F0A;
            border-top: 2px solid rgba(176,141,87,0.45);
            box-shadow: 0 -12px 40px rgba(0,0,0,0.85);
        }
        .login-ticker {
            width: 100%;
            background: #1A0F0A;
            border-bottom: 1px solid rgba(176,141,87,0.12);
            font-size: 0.76rem;
            color: #c8a96a;
            white-space: nowrap;
            overflow: hidden;
            height: 28px;
            display: flex;
            align-items: center;
            flex-shrink: 0;
            font-family: Georgia, 'Times New Roman', serif;
            letter-spacing: 0.04em;
        }
        .tk-label {
            padding: 0 10px;
            font-size: 0.56rem;
            font-weight: 700;
            letter-spacing: 0.18em;
            flex-shrink: 0;
            border-right: 1px solid rgba(176,141,87,0.28);
            height: 100%;
            display: flex;
            align-items: center;
            min-width: 50px;
            justify-content: center;
            color: #B08D57;
            font-family: Georgia, serif;
            text-transform: uppercase;
        }
        .tk-viewport {
            overflow: hidden;
            flex: 1;
            height: 100%;
            display: flex;
            align-items: center;
        }

        .game-title {
            text-align: center;
            margin-bottom: 16px;
            font-size: 22px;
            font-weight: 700;
            letter-spacing: 0.04em;
            line-height: 1.25;
            background: linear-gradient(90deg, #B08D57, #e5c88a, #B08D57);
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
            text-shadow: 0 1px 12px rgba(176, 141, 87, 0.25);
        }

        .logo {
            text-align: center;
            margin-bottom: 12px;
        }

        .logo img {
            width: 200px;
            height: auto;
        }

        .tagline {
            text-align: center;
            color: #94a3b8;
            margin-bottom: 48px;
            font-size: 14px;
        }

        .panel {
            background: #020617;
            border: 1px solid #1e293b;
            border-radius: 16px;
            padding: 40px;
        }

        .tabs {
            display: flex;
            gap: 8px;
            margin-bottom: 32px;
            background: #0b1220;
            padding: 4px;
            border-radius: 10px;
        }

        .tab {
            flex: 1;
            padding: 10px;
            text-align: center;
            cursor: pointer;
            border-radius: 8px;
            transition: background 0.2s, color 0.2s;
            font-size: 14px;
            font-weight: 500;
        }

        .tab.active {
            background: #38bdf8;
            color: #020617;
        }

        .tab:not(.active) {
            color: #64748b;
        }

        .form {
            display: none;
        }

        .form.active {
            display: block;
        }

        .field {
            margin-bottom: 20px;
        }

        label {
            display: block;
            margin-bottom: 8px;
            font-size: 14px;
            color: #94a3b8;
        }

        input {
            width: 100%;
            padding: 12px 16px;
            background: #0b1220;
            border: 1px solid #1e293b;
            border-radius: 8px;
            color: #e5e7eb;
            font-size: 15px;
            transition: border 0.2s;
        }

        input:focus {
            outline: none;
            border-color: #38bdf8;
        }

        button {
            width: 100%;
            padding: 14px;
            background: #38bdf8;
            color: #020617;
            border: none;
            border-radius: 8px;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.2s;
        }

        button:hover {
            background: #0ea5e9;
        }

        .hint {
            margin-top: 12px;
            font-size: 13px;
            color: #64748b;
            text-align: center;
        }

        .marquee-wrap {
            margin-top: 28px;
            text-align: center;
            min-height: 48px;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .marquee-text {
            font-size: 14px;
            font-style: italic;
            color: #38bdf8;
            opacity: 0;
            transition: opacity 0.9s ease;
            max-width: 480px;
            line-height: 1.5;
            letter-spacing: 0.01em;
        }

        .marquee-text.visible {
            opacity: 1;
        }

        /* ── Hero "Build an Empire" card ── */
        .hero-card {
            position: relative;
            margin-top: 22px;
            padding: 42px 28px 38px;
            text-align: center;
            border-radius: 16px;
            overflow: hidden;
            background:
                radial-gradient(ellipse at 50% 0%, rgba(202,138,4,0.10) 0%, rgba(12,10,9,0) 60%),
                linear-gradient(160deg, #14100c 0%, #0c0a09 55%, #14100c 100%);
            border: 1px solid rgba(176,141,87,0.28);
            box-shadow: 0 22px 60px rgba(0,0,0,0.6),
                        inset 0 1px 0 rgba(255,225,170,0.06);
        }

        .hero-gear {
            position: absolute;
            opacity: 0.06;
            fill: #eab308;
            pointer-events: none;
            z-index: 0;
        }
        .hero-gear.g1 { top: -54px; left: -50px;  width: 200px; height: 200px;
                        animation: hero-gear-rotate 26s linear infinite; }
        .hero-gear.g2 { bottom: -60px; right: -56px; width: 240px; height: 240px;
                        animation: hero-gear-rotate 46s linear infinite reverse; }

        .hero-inner { position: relative; z-index: 1; }

        .hero-breathe { animation: hero-breathe 5s ease-in-out infinite; }

        .hero-title {
            font-family: 'Cinzel', serif;
            font-weight: 900;
            font-size: clamp(2.4rem, 9vw, 3.2rem);
            line-height: 0.96;
            text-transform: uppercase;
            letter-spacing: 0.01em;
            margin: 0;
            background: linear-gradient(90deg,
                #ca8a04 0%, #ca8a04 40%, #fef08a 50%, #ca8a04 60%, #ca8a04 100%);
            background-size: 200% auto;
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
            text-shadow: 0 4px 20px rgba(0,0,0,0.8);
            filter: drop-shadow(0 0 2px rgba(253,224,71,0.45));
            animation: hero-gold-shine 3.4s linear infinite;
        }

        .hero-kicker {
            margin: 12px 0 0;
            color: rgba(202,138,4,0.82);
            font-weight: 700;
            font-size: 0.7rem;
            letter-spacing: 0.32em;
            text-transform: uppercase;
        }

        .hero-divider {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 14px;
            margin: 26px 0;
        }
        .hero-divider .hd-line {
            height: 1px;
            width: 56px;
            background: linear-gradient(90deg, transparent, rgba(234,179,8,0.75));
        }
        .hero-divider .hd-line.right {
            background: linear-gradient(90deg, rgba(234,179,8,0.75), transparent);
        }
        .hero-divider .hd-diamond {
            width: 9px; height: 9px;
            transform: rotate(45deg);
            border: 1px solid #facc15;
            background: rgba(202,138,4,0.4);
        }

        .hero-quote {
            font-family: 'EB Garamond', Georgia, serif;
            font-style: italic;
            font-size: 1.18rem;
            line-height: 1.6;
            color: #e7e2d8;
            margin: 0 auto;
            max-width: 380px;
            text-shadow: 0 1px 6px rgba(0,0,0,0.5);
        }

        .hero-footer {
            margin: 22px 0 0;
            color: #eab308;
            font-size: 0.62rem;
            font-weight: 700;
            letter-spacing: 0.4em;
            text-transform: uppercase;
            opacity: 0.72;
        }

        @keyframes hero-gold-shine { to { background-position: 200% center; } }
        @keyframes hero-breathe {
            0%, 100% { transform: scale(1); }
            50%      { transform: scale(1.025); }
        }
        @keyframes hero-gear-rotate {
            from { transform: rotate(0deg); }
            to   { transform: rotate(360deg); }
        }
        @media (prefers-reduced-motion: reduce) {
            .hero-title, .hero-breathe, .hero-gear { animation: none; }
        }

        /* ── FAQ accordion ── */
        .faq-section {
            margin-top: 36px;
            border-top: 1px solid rgba(176,141,87,0.18);
            padding-top: 28px;
            text-align: left;
        }
        .faq-heading {
            font-family: 'Cinzel', serif;
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.3em;
            text-transform: uppercase;
            color: rgba(202,138,4,0.82);
            text-align: center;
            margin: 0 0 22px;
        }
        .faq-item {
            border-bottom: 1px solid rgba(255,255,255,0.055);
        }
        .faq-item summary {
            padding: 13px 2px;
            cursor: pointer;
            font-size: 0.87rem;
            font-weight: 600;
            color: #e2e8f0;
            list-style: none;
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 10px;
            transition: color 0.15s;
            user-select: none;
        }
        .faq-item summary::-webkit-details-marker { display: none; }
        .faq-item summary:hover { color: #fef08a; }
        .faq-icon {
            flex-shrink: 0;
            margin-top: 1px;
            font-size: 1rem;
            font-weight: 300;
            color: rgba(202,138,4,0.7);
            transition: transform 0.2s;
            line-height: 1;
        }
        .faq-item[open] .faq-icon { transform: rotate(45deg); }
        .faq-answer {
            padding: 2px 4px 16px;
            font-size: 0.82rem;
            color: #94a3b8;
            line-height: 1.72;
        }
        .faq-answer strong { color: #cbd5e1; }
        .faq-answer a { color: #38bdf8; }

        /* ── Live leaderboard (inside hero card) ── */
        .lb-section {
            margin-top: 36px;
            border-top: 1px solid rgba(176,141,87,0.18);
            padding-top: 28px;
            text-align: left;
        }
        .lb-heading {
            font-family: 'Cinzel', serif;
            font-size: 1.05rem;
            font-weight: 700;
            letter-spacing: 0.04em;
            color: #e5c88a;
            text-align: center;
            margin-bottom: 6px;
        }
        .lb-sub {
            text-align: center;
            color: #94a3b8;
            font-size: 0.78rem;
            margin-bottom: 18px;
        }
        .lb-tabs {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            justify-content: center;
            margin-bottom: 16px;
        }
        .lb-tab {
            padding: 6px 12px;
            font-size: 0.74rem;
            font-weight: 600;
            color: #94a3b8;
            background: rgba(30,41,59,0.55);
            border: 1px solid rgba(176,141,87,0.18);
            border-radius: 999px;
            cursor: pointer;
            transition: color .15s, background .15s, border-color .15s;
            user-select: none;
        }
        .lb-tab:hover { color: #e5c88a; border-color: rgba(176,141,87,0.4); }
        .lb-tab.active {
            color: #0b1220;
            background: linear-gradient(90deg, #e5c88a, #B08D57);
            border-color: #e5c88a;
        }
        .lb-table-wrap {
            overflow-x: auto;
            border-radius: 10px;
            border: 1px solid rgba(176,141,87,0.14);
        }
        .lb-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.78rem;
            white-space: nowrap;
        }
        .lb-table th, .lb-table td {
            padding: 8px 12px;
            text-align: right;
            border-bottom: 1px solid rgba(176,141,87,0.10);
        }
        .lb-table th:nth-child(1), .lb-table td:nth-child(1),
        .lb-table th:nth-child(2), .lb-table td:nth-child(2) {
            text-align: left;
        }
        .lb-table thead th {
            color: #c8a96a;
            font-weight: 700;
            font-size: 0.68rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            background: rgba(26,15,10,0.6);
            position: sticky;
            top: 0;
        }
        .lb-table tbody tr:hover { background: rgba(176,141,87,0.06); }
        .lb-col-active { background: rgba(176,141,87,0.10); color: #f1e3c4; }
        .lb-table thead th.lb-col-active { color: #f5d98a; }
        .lb-rank { color: #94a3b8; font-weight: 700; }
        .lb-name { color: #e5e7eb; font-weight: 600; }
        .lb-badge {
            font-size: 0.64rem;
            font-weight: 700;
            padding: 1px 6px;
            border-radius: 4px;
            color: #0b1220;
        }
        .lb-gold   { background: linear-gradient(90deg,#fde68a,#f59e0b); }
        .lb-silver { background: linear-gradient(90deg,#e2e8f0,#94a3b8); }
        .lb-bronze { background: linear-gradient(90deg,#fdba74,#c2742c); color: #fff; }
        .lb-trophy { color: #fbbf24; font-weight: 600; }
        .lb-level {
            background: #1e293b; color: #a78bfa;
            border: 1px solid #4c3d8f; border-radius: 3px;
            padding: 1px 5px; font-size: 0.62rem; font-weight: 700; margin-left: 4px;
        }

        /* ── Indices card support ── */
        .card {
            background: #0f172a;
            border: 1px solid #1e293b;
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 16px;
        }
        .badge {
            font-size: 0.65rem;
            padding: 2px 6px;
            border-radius: 3px;
            background: #1e293b;
            margin-left: 6px;
            white-space: nowrap;
            color: #e2e8f0;
        }
        .btn-blue {
            border: none;
            padding: 8px 16px;
            cursor: pointer;
            font-size: 0.85rem;
            border-radius: 6px;
            font-family: inherit;
            font-weight: 600;
            background: #38bdf8;
            color: #020617;
            text-decoration: none;
            display: inline-block;
        }

        .video-wrap {
            margin-top: 20px;
            border-radius: 12px;
            overflow: hidden;
            position: relative;
            width: 100%;
            aspect-ratio: 16 / 9;
            border: 1px solid #1e293b;
        }

        .video-wrap iframe {
            position: absolute;
            inset: 0;
            width: 100%;
            height: 100%;
            border: 0;
        }
    </style>
</head>

<body>
    <div class="splash">
        <div class="game-title">Wadsworth Economic Tycoon Simulator</div>
        <div class="logo"><img src="/static/logo.png?v=3" alt="Wadsworth"></div>

        <div class="panel">
            <div class="tabs">
                <div class="tab active" onclick="switchTab('login')">Login</div>
                <div class="tab" onclick="switchTab('register')">Register</div>
            </div>

            <form class="form active" id="login-form" method="post" action="/api/login">
                <div class="field">
                    <label>Business Name</label>
                    <input type="text" name="business_name" required autofocus>
                </div>
                <div class="field">
                    <label>Password</label>
                    <input type="password" name="password" required>
                </div>
                <button type="submit">Login</button>
            </form>

            <form class="form" id="register-form" method="post" action="/api/register">
                <div class="field">
                    <label>Business Name</label>
                    <input type="text" name="business_name" required>
                </div>
                <div class="field">
                    <label>Password</label>
                    <input type="password" name="password" required minlength="8">
                </div>
                <div class="field">
                    <label>Confirm Password</label>
                    <input type="password" name="password_confirm" required minlength="8">
                </div>
                <button type="submit">Create Account</button>
                <div class="hint">Password must be at least 8 characters</div>
            </form>
        </div>

        <!-- Rotating tagline -->
        <div class="marquee-wrap">
            <div class="marquee-text" id="marquee"></div>
        </div>

        <!-- Hero tagline card -->
        <div class="hero-card">
            <svg class="hero-gear g1" viewBox="0 0 100 100" aria-hidden="true">
                <path d="M50 25c-1.1 0-2 .9-2 2v4.2c-2.3.5-4.5 1.4-6.4 2.7l-3-3c-.8-.8-2-.8-2.8 0l-3.5 3.5c-.8.8-.8 2 0 2.8l3 3c-1.3 1.9-2.2 4.1-2.7 6.4H27c-1.1 0-2 .9-2 2v5c0 1.1.9 2 2 2h4.2c.5 2.3 1.4 4.5 2.7 6.4l-3 3c-.8.8-.8 2 0 2.8l3.5 3.5c.8.8 2 .8 2.8 0l3-3c1.9 1.3 4.1 2.2 6.4 2.7V73c0 1.1.9 2 2 2h5c1.1 0 2-.9 2-2v-4.2c2.3-.5 4.5-1.4 6.4-2.7l3 3c.8.8 2 .8 2.8 0l3.5-3.5c.8-.8.8-2 0-2.8l-3-3c1.3-1.9 2.2-4.1 2.7-6.4H73c1.1 0 2-.9 2-2v-5c0-1.1-.9-2-2-2h-4.2c-.5-2.3-1.4-4.5-2.7-6.4l3-3c.8-.8.8-2 0-2.8l-3.5-3.5c-.8-.8-2-.8-2.8 0l-3 3c-1.9-1.3-4.1-2.2-6.4-2.7V27c0-1.1-.9-2-2-2h-5zM50 40c5.5 0 10 4.5 10 10s-4.5 10-10 10-10-4.5-10-10 4.5-10 10-10z"/>
            </svg>
            <svg class="hero-gear g2" viewBox="0 0 100 100" aria-hidden="true">
                <path d="M50 25c-1.1 0-2 .9-2 2v4.2c-2.3.5-4.5 1.4-6.4 2.7l-3-3c-.8-.8-2-.8-2.8 0l-3.5 3.5c-.8.8-.8 2 0 2.8l3 3c-1.3 1.9-2.2 4.1-2.7 6.4H27c-1.1 0-2 .9-2 2v5c0 1.1.9 2 2 2h4.2c.5 2.3 1.4 4.5 2.7 6.4l-3 3c-.8.8-.8 2 0 2.8l3.5 3.5c.8.8 2 .8 2.8 0l3-3c1.9 1.3 4.1 2.2 6.4 2.7V73c0 1.1.9 2 2 2h5c1.1 0 2-.9 2-2v-4.2c2.3-.5 4.5-1.4 6.4-2.7l3 3c.8.8 2 .8 2.8 0l3.5-3.5c.8-.8.8-2 0-2.8l-3-3c1.3-1.9 2.2-4.1 2.7-6.4H73c1.1 0 2-.9 2-2v-5c0-1.1-.9-2-2-2h-4.2c-.5-2.3-1.4-4.5-2.7-6.4l3-3c.8-.8.8-2 0-2.8l-3.5-3.5c-.8-.8-2-.8-2.8 0l-3 3c-1.9-1.3-4.1-2.2-6.4-2.7V27c0-1.1-.9-2-2-2h-5zM50 40c5.5 0 10 4.5 10 10s-4.5 10-10 10-10-4.5-10-10 4.5-10 10-10z"/>
            </svg>
            <div class="hero-inner">
                <div class="hero-breathe">
                    <h1 class="hero-title">Build an<br>Empire</h1>
                </div>
                <p class="hero-kicker">From a single storefront</p>
                <div class="hero-divider">
                    <span class="hd-line"></span>
                    <span class="hd-diamond"></span>
                    <span class="hd-line right"></span>
                </div>
                <p class="hero-quote">
                    &ldquo;Trade commodities, float your company on the stock market,
                    and outmaneuver thousands of rival tycoons.&rdquo;
                </p>
                <p class="hero-footer">One living, breathing economy</p>

                <!-- FAQ accordion -->
                <div class="faq-section">
                    <p class="faq-heading">Frequently Asked Questions</p>

                    <details class="faq-item">
                        <summary>What is Wadsworth Economic Tycoon Simulator? <span class="faq-icon">+</span></summary>
                        <div class="faq-answer">Wadsworth is a persistent-world browser and Android economic strategy game. You run a company, build businesses on land you own, produce and trade real commodities, float your company on the stock market, invest in ETFs, bonds, and cryptocurrencies, and compete against thousands of players in one shared, living economy. The game has 138+ business types, 16 currencies, 19 live economic indices, a full multi-layer tax system, and ticks in real time 24/7 whether you&rsquo;re logged in or not.</div>
                    </details>

                    <details class="faq-item">
                        <summary>Is it free to play? <span class="faq-icon">+</span></summary>
                        <div class="faq-answer">Yes. Every economic system — commodity markets, land, businesses, stocks, ETFs, crypto, P2P contracts, foreign exchange, bonds — is fully available free, forever. The optional <strong>Wadsworth Pro</strong> (Supporters) subscription is a way to support development: today it unlocks 3 exclusive cosmetic skins, with more supporter perks on the roadmap. None of it affects core gameplay. See the Supporters FAQ entry below for the full list and what's live versus coming soon.</div>
                    </details>

                    <details class="faq-item">
                        <summary>How do I start making money? <span class="faq-icon">+</span></summary>
                        <div class="faq-answer">Buy a land plot, build a business that matches its terrain type, and activate a production line. Your business automatically produces goods every tick. Sell on the commodity market, set a retail price for direct consumer sales, or negotiate a P2P contract with another player. Raw-resource businesses (farming, basic mining) are the lowest-friction starting point — they need no manufactured inputs and sell quickly.</div>
                    </details>

                    <details class="faq-item">
                        <summary>How do businesses and production lines work? <span class="faq-icon">+</span></summary>
                        <div class="faq-answer">Each of 138+ business types has one or more <strong>production lines</strong> that consume input materials and automatically output goods every game tick. Terrain compatibility is strict — Wheat Farms need prairie, Naval Shipyards need a Military district, Solar Farms need desert. Outputs land in your warehouse ready to sell. Production continues offline as long as your warehouse is stocked with the required inputs.</div>
                    </details>

                    <details class="faq-item">
                        <summary>What happens while I&rsquo;m offline? <span class="faq-icon">+</span></summary>
                        <div class="faq-answer">Production continues uninterrupted as long as your warehouse has the required inputs. Open market orders remain active. Bond interest accrues hourly. Cash earns foreign-currency yield on active bonds. Executives continue aging and drawing wages — a missed wage payment causes them to quit immediately with a severance penalty, so make sure your cash is sufficient before logging off. Notifications accumulate and are waiting in your feed on next login.</div>
                    </details>

                    <details class="faq-item">
                        <summary>What taxes does my company pay? <span class="faq-icon">+</span></summary>
                        <div class="faq-answer">Wadsworth has a layered tax system across every part of the economy:<br><br>
                        &bull; <strong>Federal Sales Tax (2.02%)</strong> — charged to the buyer on every commodity market trade and IPO purchase.<br>
                        &bull; <strong>Land / Property Tax (monthly)</strong> — based on terrain type. Base rates range from $30/mo (desert) to $120/mo (urban) to $500–$900/mo (developed districts). Proximity multipliers apply — coastal and resource-rich plots pay more.<br>
                        &bull; <strong>Hoarding Tax</strong> — your first 5 land plots are surcharge-free. Every additional plot beyond 5 costs an extra <strong>$5,000/month</strong>, deducted hourly. Food carts are exempt.<br>
                        &bull; <strong>Forex Conversion Fee (0.2%)</strong> — charged every time cash is auto-converted between currencies, including when income arrives in a currency other than your legal tender.<br>
                        &bull; <strong>Bond Issuance Fee (0.25%)</strong> — paid when you purchase bonds. Goes to the federal reserve.<br>
                        &bull; <strong>Bond Interest Withholding Tax (15%)</strong> — 15% of all hourly bond interest is withheld by the government. You receive 85%.<br>
                        &bull; <strong>Early Bond Redemption Fee (1.5%)</strong> — flat penalty if you sell a bond within its first 7 days.<br>
                        &bull; <strong>Legal Tender Switch Fee (2%)</strong> — charged on your current foreign-currency balance when switching away from a non-USD legal tender.<br>
                        &bull; <strong>City Sales Tax</strong> — variable per city; a portion of each local sale routes to that city&rsquo;s fund.<br><br>
                        Executives with Tax Shield abilities (General Counsel, Chief Compliance Officer) can reduce many of these. Tax vouchers earned from events can offset federal sales tax.</div>
                    </details>

                    <details class="faq-item">
                        <summary>What&rsquo;s the difference between the market, retail, and P2P contracts? <span class="faq-icon">+</span></summary>
                        <div class="faq-answer"><strong>Commodity market</strong>: open player-to-player order book. Post a sell order; another player buys it. The 2.02% federal sales tax is paid by the buyer. Orders are matched by price then timestamp.<br><br><strong>Retail</strong>: set a price on a retail-capable business; simulated consumer demand buys from you directly. No market fee. Requires a specific retail-type business with stock and a price set via the Businesses page — with no page reload required.<br><br><strong>P2P contract</strong>: agree a price directly with a named player. No market fee, no federal sales tax. Both parties must accept; either can cancel before acceptance with full refund.</div>
                    </details>

                    <details class="faq-item">
                        <summary>How are market orders matched? <span class="faq-icon">+</span></summary>
                        <div class="faq-answer">Orders are matched by <strong>price priority</strong> (lowest ask wins for buys; highest bid wins for sells), then by <strong>timestamp</strong> (older orders fill first at equal prices). Partial fills are supported — your order stays active at the remaining quantity. <strong>Quick Buy</strong> fills at the best current ask immediately. Updating an existing order resets its timestamp, moving it to the back of the queue at that price level.</div>
                    </details>

                    <details class="faq-item">
                        <summary>What are NPCs? <span class="faq-icon">+</span></summary>
                        <div class="faq-answer">NPCs (Non-Player Characters) are 64+ automated bot companies operated by the game itself. They act as market-makers of last resort — always posting sell orders for essential goods at prices slightly above typical player prices, so you&rsquo;re never stuck without inputs. NPC companies cover agriculture, military hardware, electronics, construction materials, financial instruments, district services, and more. Their pricing is intentionally above market to let player sellers stay competitive with profit.</div>
                    </details>

                    <details class="faq-item">
                        <summary>How do I level up and earn trophies? <span class="faq-icon">+</span></summary>
                        <div class="faq-answer">Levels are driven by <strong>trophies</strong>. Earn trophies by completing event tasks — time-limited challenges that might ask you to trade a target volume, enter the WBC-50 index, win a land auction, complete a monthly Index Challenge, or produce a specific quantity of goods. Each completed event awards trophies and levelling up unlocks more of the game. Weekly, monthly, and special events continuously rotate new challenges with different reward tiers.</div>
                    </details>

                    <details class="faq-item">
                        <summary>What are events and tasks? <span class="faq-icon">+</span></summary>
                        <div class="faq-answer">Events are time-limited challenges (daily, weekly, or monthly) with a specific measurable metric — trade volume, production quantity, stock market participation, index entry or exit. The <strong>Index Challenge</strong> is a monthly event with asymmetric goals: players outside the WBC-50 must enter it; players already inside must exit. Both groups complete the same event with opposite objectives. Finishing all steps earns trophy rewards. The Events page shows active challenges, your progress, and leaderboard standings.</div>
                    </details>

                    <details class="faq-item">
                        <summary>What is the WBC-50? <span class="faq-icon">+</span></summary>
                        <div class="faq-answer">The <strong>Wadsworth Blue-Chip 50</strong> is the flagship stock index tracking the 50 highest-market-cap companies — both player companies and NPC enterprises combined. It functions like a real index: rising when top companies grow, falling in downturns. The index rebalances every 10 minutes. You can invest in it passively via the WBC-50 Index Fund ETF, or compete to enter it yourself by growing your company&rsquo;s market capitalisation and displacing a current constituent.</div>
                    </details>

                    <details class="faq-item">
                        <summary>What are districts and why should I build one? <span class="faq-icon">+</span></summary>
                        <div class="faq-answer">Districts are formed by merging multiple land plots of the same terrain type. A merged district unlocks <strong>district-exclusive businesses</strong> — hotels, casinos, military bases, tech startup hubs, seaports, aerospace facilities, and more — that produce high-value services unavailable on raw terrain. Larger districts (more plots merged) unlock more powerful business tiers. District businesses cannot be placed on raw terrain, only on district-type plots. Districts also generate higher monthly land tax income.</div>
                    </details>

                    <details class="faq-item">
                        <summary>How does the stock market work? <span class="faq-icon">+</span></summary>
                        <div class="faq-answer">When eligible, take your company public via an <strong>IPO</strong> through the Brokerage: set an offering price, choose how many shares to sell, and other players can buy in. The 2.02% federal sales tax applies to IPO purchases. Your share price then moves with trading activity. You can also invest in other companies&rsquo; stocks, launch secondary share offerings, run buyback programs to retire shares, vote on corporate governance proposals, or <strong>short-sell</strong> companies you believe are overvalued.</div>
                    </details>

                    <details class="faq-item">
                        <summary>What are ETFs? <span class="faq-icon">+</span></summary>
                        <div class="faq-answer">Five Exchange-Traded Funds track different economy segments, all traded on the Brokerage floor:<br><br>
                        &bull; <strong>Apple Seeds ETF</strong> — agricultural commodity prices<br>
                        &bull; <strong>Energy ETF</strong> — the power sector<br>
                        &bull; <strong>City NAV ETF</strong> — real estate and district values<br>
                        &bull; <strong>Land Bank</strong> — overall land valuations<br>
                        &bull; <strong>WBC-50 Index Fund</strong> — the top 50 companies<br><br>
                        ETFs pay dividends and each ETF bank maintains a standing buyback order at approximately <strong>92% of NAV</strong>, providing a price floor. CFO executives with Dividend Booster abilities earn enhanced returns from ETF holdings.</div>
                    </details>

                    <details class="faq-item">
                        <summary>What are Reserve Banks and the multi-currency system? <span class="faq-icon">+</span></summary>
                        <div class="faq-answer">Wadsworth has <strong>16 currencies</strong>: USD, JPY, MXP, GBP, CHF, CNY, EUR, INR, RUB, KRW, ZAR, BRL, TRY, SAR, AED, and ANA — each issued by a State Reserve Bank. Players choose a <strong>legal tender</strong>; all income auto-converts to it at a 0.2% fee. There is a <strong>7-day cooldown</strong> between legal tender changes and a 2% exit fee when leaving a non-USD currency. Exchange rates move dynamically based on bond demand and yield differentials. (A planned Supporters perk will let subscribers create unique reserve currencies.)</div>
                    </details>

                    <details class="faq-item">
                        <summary>What are bonds? <span class="faq-icon">+</span></summary>
                        <div class="faq-answer">Bonds are fixed-income instruments issued by each of the 16 State Reserve Banks. You loan cash to a bank and receive <strong>hourly interest</strong> in its native currency. Yields are dynamic — more buying pushes them down, less demand lets them drift up. Available maturities: <strong>7, 14, or 30 days</strong>. A <strong>15% withholding tax</strong> applies to all interest earned (you receive 85%). Selling within 7 days incurs a 1.5% early redemption penalty. Banks may force-call a bond (at face value + 3% premium + accrued interest) if the current market yield drops to ≤40% of your purchase yield — protecting you from being stuck in above-market bonds.</div>
                    </details>

                    <details class="faq-item">
                        <summary>What is WSC (Wadsworth Stable Coin)? <span class="faq-icon">+</span></summary>
                        <div class="faq-answer">WSC is the game&rsquo;s internal stable token, soft-pegged to USD. It can be minted with in-game cash, earned via <strong>yield farming pools</strong>, received as periodic airdrops, or traded on the crypto market. WSC is used in certain platform transactions and accrues yield when held in treasury pools. The <strong>WSC Minting Rate Index (WMRI)</strong> on the Market Indices page tracks total supply, circulating amount, and pool distribution in real time.</div>
                    </details>

                    <details class="faq-item">
                        <summary>What are county cryptocurrencies? <span class="faq-icon">+</span></summary>
                        <div class="faq-answer">Each county issues its own native cryptocurrency — a layer-1 token backed by the county&rsquo;s treasury. Token value is driven by treasury balance, circulating supply, and trading volume. Players buy, sell, and hold county tokens on the meme market. The <strong>County Crypto Composite (CCC)</strong> index on the Market Indices page tracks the total crypto market cap across all counties in real time.</div>
                    </details>

                    <details class="faq-item">
                        <summary>What is the Greed &amp; Fear Index? <span class="faq-icon">+</span></summary>
                        <div class="faq-answer">The GFI is a 0&ndash;100 market sentiment gauge calculated from five live signals: <strong>WBC-50 momentum</strong> vs its 30-day moving average, <strong>market breadth</strong> (share of companies above IPO price), <strong>corporate actions</strong> (buybacks vs share issuances), <strong>P2P contract velocity</strong>, and <strong>24-hour trade volume</strong>. Below 25 = Extreme Fear; 25&ndash;44 = Fear; 45&ndash;55 = Neutral; 56&ndash;75 = Greed; above 75 = Extreme Greed. A useful contrarian indicator — extreme fear historically precedes recoveries.</div>
                    </details>

                    <details class="faq-item">
                        <summary>What do the 19 Market Indices track? <span class="faq-icon">+</span></summary>
                        <div class="faq-answer">19 live composite indices update every 10 minutes across the full economy:<br><br>
                        <strong>WBC-50</strong> (blue-chip market cap) · <strong>GLVI</strong> (real estate values) · <strong>CCC</strong> (crypto market cap) · <strong>EPI</strong> (executive payroll) · <strong>CDI</strong> (share dilution ratio) · <strong>REGI</strong> (land gentrification) · <strong>RBYC</strong> (reserve bank yields) · <strong>GSI</strong> (banking solvency) · <strong>PCVI</strong> (P2P contract velocity) · <strong>NSCI</strong> (neighbourhood service costs) · <strong>ASI</strong> (agricultural staples) · <strong>GDSI</strong> (defense spending) · <strong>WMRI</strong> (WSC minting) · <strong>BEE</strong> (bee inventory) · <strong>WEI</strong> (water &amp; energy) · <strong>GPI</strong> (grass &amp; pollen) · <strong>AMP</strong> (average market price) · <strong>SEED</strong> (seed inventory) · <strong>GFI</strong> (greed &amp; fear)<br><br>
                        Every index has 30-day history, candlestick charts, composition breakdowns, and related-index cards. All 19 are publicly viewable right now — no login required — from the <a href="/banks/indices/unloggedin">Market Indices page</a>.</div>
                    </details>

                    <details class="faq-item">
                        <summary>What are executives? <span class="faq-icon">+</span></summary>
                        <div class="faq-answer">Executives are hireable characters across <strong>11 specialisation categories</strong> — Business, Sales, Production, Banking, Taxes, Crypto, Land, Cities, Districts, Counties, and P2P. You can hold up to <strong>8 simultaneously</strong>. Each executive has 3&ndash;5 randomly assigned abilities from their job&rsquo;s pool (a <strong>5% legendary chance</strong> adds a bonus ability with higher values). They are paid on a set cycle; a missed wage payment triggers immediate resignation plus a severance deduction.<br><br>
                        Key roles:<br>
                        &bull; <strong>CFO</strong> — reduces accounting overhead; boosts ETF dividends and banking income<br>
                        &bull; <strong>COO</strong> — reduces administration and operational costs<br>
                        &bull; <strong>General Counsel / Chief Compliance Officer</strong> — reduces all taxes<br>
                        &bull; <strong>VP Land Development</strong> — slows land efficiency decay; reduces hoarding tax<br>
                        &bull; <strong>CTO / CIO</strong> — boosts WSC yield farming and crypto mining<br>
                        &bull; <strong>CCO (Content)</strong> — unlocks broadcast notifications to followers<br><br>
                        Executives age up over time, earning a <strong>7.85% raise</strong> per milestone. Sending them to school (~30 min) awards a <strong>15% permanent boost</strong>.</div>
                    </details>

                    <details class="faq-item">
                        <summary>What is WikiWads? <span class="faq-icon">+</span></summary>
                        <div class="faq-answer">WikiWads is the in-game knowledge base — an admin-curated library of guides, video embeds, and audio content covering all game systems. It is organised into <strong>10 categories</strong>: Getting Started, Economy, Land, Banks, Markets, Businesses, Districts, Cities, Advanced Tactics, and Reference. Entries include embedded YouTube walkthroughs, written explanations, and audio commentary. Access WikiWads from the main menu after logging in. Admins can add, pin, reorder, and update entries at any time, so the library grows with the game.</div>
                    </details>

                    <details class="faq-item">
                        <summary>What is the Transaction Ledger? <span class="faq-icon">+</span></summary>
                        <div class="faq-answer">The <strong>Stats page</strong> contains your full transaction ledger — a timestamped record of every financial event in your company, including market buys and sells, production inputs and outputs, retail sales, bond interest earned, dividends, wages paid, and every tax deduction (federal sales tax, forex fees, bond fees, withholding taxes, reserve balance tax). Each entry shows transaction type, category (money or resource), amount, item type, quantity, unit price, description, and a reference ID. The ledger is your primary tool for tracking cost basis, analysing profitability per product, and understanding exactly where fees are being deducted from your income.</div>
                    </details>

                    <details class="faq-item">
                        <summary>How do push notifications work? <span class="faq-icon">+</span></summary>
                        <div class="faq-answer">Two separate notification systems run in parallel:<br><br>
                        <strong>In-game notifications</strong>: stored in your feed automatically. Triggered by bond maturity and call events, executive events (hiring, aging, retirement, late payment), land efficiency floor warnings, government announcements, P2P contract updates, and major transaction events. These cannot be disabled and accumulate while you&rsquo;re offline.<br><br>
                        <strong>Android / web push notifications</strong>: optional device alerts delivered via the Web Push API when the app is backgrounded or closed. Subscribe via Settings. You receive real-time alerts for the same major events. Opt out anytime in Settings. The Android app (free on Google Play) delivers these as native Android notifications.</div>
                    </details>

                    <details class="faq-item">
                        <summary>What is the Android widget? <span class="faq-icon">+</span></summary>
                        <div class="faq-answer">The Android home screen widget shows your <strong>live balance</strong>, your most recent transaction (description, amount, timestamp, and a tap-link to the relevant page), a scrolling list of recent activity, and live market data — WBC-50 and other index values, top stock prices, bond yields, and memecoin prices.<br><br>
                        To set it up: open the Android app, go to <strong>Settings → Link Widget Device</strong>. The widget refreshes automatically using a secure HMAC token tied to your account. A new Federal Development Grant notice appears on the widget when a grant event is active.</div>
                    </details>

                    <details class="faq-item">
                        <summary>How do I change my game skin / theme? <span class="faq-icon">+</span></summary>
                        <div class="faq-answer">Go to <strong>Settings</strong> and select from 6 visual themes. The change applies instantly with no reload:<br><br>
                        &bull; <strong>Default</strong> — clean modern dark (free)<br>
                        &bull; <strong>Dark Nature</strong> — dark earth tones (free)<br>
                        &bull; <strong>Expressive Nature</strong> — vibrant nature colours (free)<br>
                        &bull; <strong>Kawaii Night</strong> — soft kawaii pastels with particle effects (Supporters)<br>
                        &bull; <strong>Soul Vinyl Dark</strong> — retro dark vinyl aesthetic (Supporters)<br>
                        &bull; <strong>Soul Vinyl Light</strong> — retro light vinyl aesthetic (Supporters)<br><br>
                        Kawaii Night includes animated particle effects. All skins alter colours, typography, and UI components. Supporter skins are shown in the Press Kit with downloadable logo variants for each theme.</div>
                    </details>

                    <!-- KEEP IN SYNC: the "Available now" vs "On the roadmap" perk split below
                         mirrors _PRO_PERKS_LIVE / _PRO_PERKS_SOON in settings_ux.py. When a perk
                         ships, move it up to "Available now" here AND into _PRO_PERKS_LIVE there. -->
                    <details class="faq-item">
                        <summary>What does the Supporters subscription include? <span class="faq-icon">+</span></summary>
                        <div class="faq-answer"><strong>Wadsworth Pro</strong> (Basic Supporter) is a low-cost monthly subscription billed through the Android app (Google Play). It's a way to support development — and it's deliberately limited to cosmetics, convenience, and optional sandbox features, so it never gives a pay-to-win edge.<br><br>
                        <strong>Available now:</strong><br>
                        &bull; 3 exclusive cosmetic skins — <strong>Kawaii Night</strong>, <strong>Soul Vinyl Dark</strong>, and <strong>Soul Vinyl Light</strong><br>
                        &bull; <strong>City perk</strong> — a free city with mayoralship, or perks for your existing city<br>
                        &bull; <strong>Institutions</strong> — sacrifice land to forge a Mint that strikes precious-metal coinage (fully backed by the metals you spend, so it's never wealth from nothing)<br>
                        &bull; <strong>Metal coinage legal tender</strong> — six gold/silver/platinum currencies pegged live to metal prices; subscribers can set one as their legal tender<br><br>
                        <strong>On the roadmap</strong> (planned supporter perks, not yet live):<br>
                        &bull; <strong>Forex Trading Floor</strong> — a currency-exchange dashboard<br>
                        &bull; <strong>Player API</strong> — read access plus buy/sell writes on the commodity &amp; district markets<br>
                        &bull; <strong>Supporter badge</strong> on the leaderboard and your profile<br>
                        &bull; Extra <strong>P2P contact capacity</strong>, a permanent <strong>profile picture</strong>, a higher <strong>trophy multiplier</strong>, a <strong>Trophies Store</strong>, and more<br><br>
                        You can see the current status of every perk — what's active versus coming soon — any time under <strong>Settings → Account</strong>. Anyone can buy sovereign bonds, including the metal-coinage banks; all markets, production, land, stocks, and trading are fully available for free, forever.</div>
                    </details>

                    <details class="faq-item">
                        <summary>Can I create more than one account? <span class="faq-icon">+</span></summary>
                        <div class="faq-answer">No. Multiple accounts are prohibited — it creates an unfair economic advantage. If you want a fresh start, use <strong>Declare Bankruptcy</strong> under <strong>Settings → Account</strong>: it liquidates all your holdings and restarts your company with $20,000 and a starter prairie plot (your account and any Wadsworth Pro subscription stay intact). To permanently close an account, use <strong>Delete Account</strong> in the Estate Office (Settings → Account → Estate Office); it's irreversible and confirmed by typing your business name.</div>
                    </details>

                    <details class="faq-item">
                        <summary>Is there a mobile app? <span class="faq-icon">+</span></summary>
                        <div class="faq-answer">Yes. The Android app is available via Google Play and is currently in <strong>closed testing</strong> during beta. The full game runs in any modern browser (Chrome, Firefox, Safari, Edge) — fully mobile-responsive on phones and tablets. The Android app adds native push notifications and home screen widget support. Web and app share the same account and economy seamlessly.</div>
                    </details>

                    <details class="faq-item">
                        <summary>What is the loading screen? <span class="faq-icon">+</span></summary>
                        <div class="faq-answer">The loading overlay appears on any same-origin page navigation to signal that a new page is loading. It features an animated logo, a brass-themed progress bar, and rotating status messages. While it&rsquo;s on screen, a random <strong>game tip</strong> may appear — tips cover things like ETF dividend strategies, CFO executive bonuses, retail price setting shortcuts, WikiWads guides, and tax voucher redemption. The overlay dismisses automatically when the new page has fully loaded. It does not appear on AJAX actions like setting a retail price.</div>
                    </details>

                    <details class="faq-item">
                        <summary>Where can I explore the game and find help? <span class="faq-icon">+</span></summary>
                        <div class="faq-answer">Several resources are available right from this login screen, no account required:<br><br>
                        &bull; <a href="/banks/indices/unloggedin"><strong>Market Indices</strong></a> — live view of all 19 economic indices with full charts<br>
                        &bull; <a href="/sitemap"><strong>Sitemap</strong></a> — searchable directory of all 40+ game pages with descriptions<br>
                        &bull; <a href="/company/whitepaper"><strong>Whitepaper</strong></a> — full game design document covering economy architecture and every mechanic<br>
                        &bull; <a href="/company/press-kit"><strong>Press Kit</strong></a> — brand assets, downloadable logos for all skins, official game description<br>
                        &bull; <a href="/company/careers"><strong>Careers</strong></a> — freelance and paid positions<br>
                        &bull; <a href="/privacy-policy"><strong>Privacy Policy</strong></a> — data collection and usage<br><br>
                        After logging in, <strong>WikiWads</strong> (in-game knowledge base) covers every mechanic in detail. For bugs or feature requests, use the GitHub Issues link in the footer.</div>
                    </details>

                    <details class="faq-item">
                        <summary>How often is the game updated? <span class="faq-icon">+</span></summary>
                        <div class="faq-answer">Frequently. Small fixes and balance tweaks deploy every few days. Major new features — new index types, business categories, weapons systems, district types, financial instruments, economic events — ship roughly monthly. The game is actively developed and player feedback directly shapes the roadmap. Feature ideas and bug reports are always welcome via the GitHub link in the page footer.</div>
                    </details>

                </div><!-- /faq-section -->

                    <details class="faq-item">
                        <summary>How do businesses and production lines work? <span class="faq-icon">+</span></summary>
                        <div class="faq-answer">Each business type has one or more <strong>production lines</strong> that convert input materials into output goods. A Wheat Farm turns seeds and water into wheat automatically every tick. You activate specific lines, manage your input inventory, and your outputs land in your warehouse ready to sell. Different business types are only available on compatible terrain — a Naval Shipyard needs a Military district; a Flour Mill needs a Farm plot.</div>
                    </details>

                    <details class="faq-item">
                        <summary>What&rsquo;s the difference between the market and retail? <span class="faq-icon">+</span></summary>
                        <div class="faq-answer"><strong>Commodity market</strong>: player-to-player buy and sell orders, matched by price then timestamp. You post a sell order and wait for a buyer, or use Quick Buy to fill at the best available price immediately. A small market fee applies.<br><br><strong>Retail</strong>: direct consumer sales from a business you own. Set a retail price on a retail-capable business and the game&rsquo;s simulated consumer demand automatically purchases from you when your price is competitive. No market fee, but you need the right business type.</div>
                    </details>

                    <details class="faq-item">
                        <summary>What are NPCs? <span class="faq-icon">+</span></summary>
                        <div class="faq-answer">NPCs (Non-Player Characters) are automated bot companies operated by the game itself. Their purpose is to ensure essential goods are always available on the market — they act as market-makers of last resort, posting sell orders slightly above typical player prices so you&rsquo;re never completely stuck without inputs. There are currently 64+ NPC companies covering agriculture, military hardware, electronics, construction, finance, and more.</div>
                    </details>

                    <details class="faq-item">
                        <summary>How do I level up and earn trophies? <span class="faq-icon">+</span></summary>
                        <div class="faq-answer">Levels are driven by <strong>trophies</strong>. You earn trophies by completing event tasks — time-limited challenges that might ask you to trade a certain volume, enter the WBC-50 index, win a land auction, produce a target quantity of goods, or complete a monthly Index Challenge. Each completed task awards trophies, and accumulating enough trophies advances your player level. Weekly, monthly, and special events continuously rotate new challenges.</div>
                    </details>

                    <details class="faq-item">
                        <summary>What is the WBC-50? <span class="faq-icon">+</span></summary>
                        <div class="faq-answer">The <strong>Wadsworth Blue-Chip 50</strong> is the game&rsquo;s flagship stock index tracking the 50 highest-market-cap companies (both player companies and NPC enterprises). It functions like a real-world index — when blue-chip companies do well the WBC-50 rises, and it falls when they decline. You can invest in it passively through the WBC-50 Index Fund ETF, or aim to enter it yourself by growing your own company&rsquo;s market capitalisation.</div>
                    </details>

                    <details class="faq-item">
                        <summary>How does the stock market work? <span class="faq-icon">+</span></summary>
                        <div class="faq-answer">Once you unlock the Brokerage you can take your company public via an <strong>IPO</strong>. Set an offering price, decide how many shares to offer, and other players can buy in. Your share price then moves with trading activity and market sentiment. You can also invest in other companies&rsquo; stocks, participate in secondary share offerings, vote on corporate governance proposals, launch buyback programs to retire shares, or short-sell companies you believe are overvalued.</div>
                    </details>

                    <details class="faq-item">
                        <summary>What are ETFs? <span class="faq-icon">+</span></summary>
                        <div class="faq-answer">Exchange-Traded Funds are passive investment vehicles whose price tracks underlying game assets. Wadsworth has five:<br><br>
                        &bull; <strong>Apple Seeds ETF</strong> — tracks agricultural commodity prices<br>
                        &bull; <strong>Energy ETF</strong> — tracks the power sector<br>
                        &bull; <strong>City NAV ETF</strong> — tracks real estate and district values<br>
                        &bull; <strong>Land Bank</strong> — tracks overall land valuations<br>
                        &bull; <strong>WBC-50 Index Fund</strong> — tracks the top 50 companies<br><br>
                        ETFs pay dividends and are traded on the brokerage order book. They&rsquo;re ideal for players who want market exposure without managing individual commodity or stock positions.</div>
                    </details>

                    <details class="faq-item">
                        <summary>What are districts, and why should I build one? <span class="faq-icon">+</span></summary>
                        <div class="faq-answer">Districts are formed by merging multiple land plots of the same terrain type. A merged district unlocks <strong>district-exclusive businesses</strong> — hotels, casinos, military bases, tech startup hubs, seaports, and more — that produce high-value services not available on raw terrain. Districts also generate higher monthly land tax income and enable production lines inaccessible outside them. The larger the district (more plots merged), the more powerful businesses you can build.</div>
                    </details>

                    <details class="faq-item">
                        <summary>What are executives? <span class="faq-icon">+</span></summary>
                        <div class="faq-answer">Executives are hireable characters with specific skills — CEO, CFO, COO, CMO, and specialist roles like Chief Compliance Officer. Each executive reduces an overhead cost or boosts production in their domain. A <strong>CFO</strong> lowers accounting overhead fees on large cash balances; a <strong>COO</strong> reduces administration costs as your business empire grows. Executives are paid on a set cycle (hourly, daily, weekly, or monthly), so confirm their savings outweigh their wage before hiring.</div>
                    </details>

                    <details class="faq-item">
                        <summary>How do P2P contracts work? <span class="faq-icon">+</span></summary>
                        <div class="faq-answer">Peer-to-peer contracts let you trade directly with another player at an agreed price, bypassing the open market entirely. You specify the item, quantity, price, and recipient. The recipient must accept before goods and cash change hands. Either party can cancel a pending contract for a full refund of goods and cash. P2P contracts carry no market fee, making them ideal for bulk supply arrangements with regular trading partners.</div>
                    </details>

                    <details class="faq-item">
                        <summary>What is land and what do terrain types mean? <span class="faq-icon">+</span></summary>
                        <div class="faq-answer">Land plots are physical locations you own on the game map. Each plot has a <strong>terrain type</strong> — prairie, savanna, forest, mountain, desert, coastal, volcanic, riverbank, and more — which determines which businesses you can build on it. Prairies suit farms; mountains suit mines and quarries; coastal land suits fishing and port operations. Plots also have a monthly tax value that rises as you develop the land, and serves as a proxy for the land&rsquo;s worth on the land market.</div>
                    </details>

                    <details class="faq-item">
                        <summary>What is the Land Market? <span class="faq-icon">+</span></summary>
                        <div class="faq-answer">The Land Market is where players buy and sell plots. You can list owned land at a fixed asking price, place a standing buy order for a specific terrain type at your desired price, or bid in <strong>government land auctions</strong> when new plots are released. Land is a long-term asset — prime terrain with high tax value and district potential tends to appreciate as the economy grows and scarcity increases.</div>
                    </details>

                    <details class="faq-item">
                        <summary>What are county cryptocurrencies? <span class="faq-icon">+</span></summary>
                        <div class="faq-answer">Each county in the game issues its own native cryptocurrency — a layer-1 token backed by the county&rsquo;s treasury. Players can buy, hold, and sell county tokens on the meme/crypto market. Token value is driven by the county&rsquo;s treasury balance, circulating supply, and recent trade volume. The <strong>County Crypto Composite (CCC)</strong> index on the Market Indices page tracks the total crypto market cap across all counties.</div>
                    </details>

                    <details class="faq-item">
                        <summary>What is WSC (Wadsworth Stable Coin)? <span class="faq-icon">+</span></summary>
                        <div class="faq-answer">WSC is the game&rsquo;s internal stable token, soft-pegged to USD. It can be minted using in-game cash, earned through yield farming pools, received via periodic airdrops, or traded on the crypto scam market. WSC acts as a platform-native currency for certain in-game transactions. The <strong>WSC Minting Rate Index (WMRI)</strong> on the Market Indices page tracks total supply, circulating amount, and pool distribution in real time.</div>
                    </details>

                    <details class="faq-item">
                        <summary>What are Reserve Banks and foreign currencies? <span class="faq-icon">+</span></summary>
                        <div class="faq-answer">Wadsworth has a full multi-currency system. Player-created <strong>Reserve Banks</strong> issue foreign currencies — each with its own yield rate and exchange rate vs USD. You can set your preferred <strong>legal tender</strong> so all income auto-converts to your chosen currency, buy foreign-currency bonds to earn yield passively, and trade on the <strong>Forex market</strong>. Holding diverse currencies adds income diversification and exposure to yield rate movements tracked by the Reserve Bank Yield Composite (RBYC) index.</div>
                    </details>

                    <details class="faq-item">
                        <summary>What is the Greed &amp; Fear Index? <span class="faq-icon">+</span></summary>
                        <div class="faq-answer">The GFI is a 0&ndash;100 market sentiment gauge, calculated from five live signals: <strong>WBC-50 momentum</strong> vs its 30-day moving average, <strong>market breadth</strong> (share of companies trading above IPO price), <strong>corporate actions</strong> (buybacks vs share issuances), <strong>P2P contract velocity</strong>, and <strong>24-hour trade volume</strong>. A score below 25 is Extreme Fear; above 75 is Extreme Greed. It&rsquo;s a useful contrarian indicator — historically, extreme fear precedes recoveries and extreme greed precedes corrections.</div>
                    </details>

                    <details class="faq-item">
                        <summary>How are market orders matched? <span class="faq-icon">+</span></summary>
                        <div class="faq-answer">Orders are matched by <strong>price priority</strong> first (lowest ask wins for buys; highest bid wins for sells), then by <strong>timestamp</strong> (older orders fill first at equal prices). If you post a sell order and a matching buy order already exists at that price or better, it fills immediately. <strong>Partial fills</strong> are supported — your order stays active at the remaining quantity. Quick Buy fills at the current best ask instantly, no waiting.</div>
                    </details>

                    <details class="faq-item">
                        <summary>What do the Market Indices track? <span class="faq-icon">+</span></summary>
                        <div class="faq-answer">There are 19 live composite indices covering every corner of the economy — from the <strong>WBC-50</strong> (blue-chip market cap) and <strong>GLVI</strong> (real estate values) to niche indices like the <strong>Bee Index</strong> (total bees in all player inventories) and the <strong>Grass &amp; Pollen Index</strong>. Each index updates every 10 minutes and has full 30-day history, candlestick charts, composition breakdowns, and related-index cards. You can explore all of them from this login page without signing in.</div>
                    </details>

                    <details class="faq-item">
                        <summary>What are events and tasks? <span class="faq-icon">+</span></summary>
                        <div class="faq-answer">Events are time-limited challenges (daily, weekly, or monthly) that award trophies on completion. Each event has a <strong>task metric</strong> — trade a target volume, enter the WBC-50 index, win a land auction, produce a specific quantity, or complete an Index Challenge. Finishing all steps earns trophy rewards and contributes to your level. The Events page shows active challenges, your current progress, and the leaderboard for competitive events.</div>
                    </details>

                    <details class="faq-item">
                        <summary>Can I create more than one account? <span class="faq-icon">+</span></summary>
                        <div class="faq-answer">No. Multiple accounts are prohibited — it creates an unfair economic advantage over other players. If you want a fresh start, use <strong>Declare Bankruptcy</strong> under <strong>Settings → Account</strong>, which liquidates your holdings and restarts your company with $20,000 and a starter prairie plot while keeping your account and any Wadsworth Pro subscription intact.</div>
                    </details>

                    <details class="faq-item">
                        <summary>Is there a mobile app? <span class="faq-icon">+</span></summary>
                        <div class="faq-answer">Yes. Wadsworth is available as an Android app (Trusted Web Activity) on Google Play. The app is free on Google Play — join as a tester via the Founding Operative event. The full game also runs in any modern browser — Chrome, Firefox, Safari, and Edge are all supported. The game is mobile-responsive, so the browser version works well on phones and tablets without the app.</div>
                    </details>

                    <details class="faq-item">
                        <summary>What happens while I&rsquo;m offline? <span class="faq-icon">+</span></summary>
                        <div class="faq-answer">Production continues. Businesses tick every 5 seconds as long as they have input materials in your warehouse, filling your inventory whether you&rsquo;re logged in or not. Open market orders remain active. Your cash earns any applicable yield from bonds or foreign currencies passively. You can log back in hours later and your warehouses will be stocked, ready to sell. Managing your input supply before logging off is a key part of efficient play.</div>
                    </details>

                    <details class="faq-item">
                        <summary>How often is the game updated? <span class="faq-icon">+</span></summary>
                        <div class="faq-answer">Frequently. Small fixes and balance tweaks deploy every few days. Major new features — new index types, new business categories, expanded weapons and military systems, new district types, economic events — ship roughly monthly. The game is actively developed and player feedback directly shapes the roadmap. Feature ideas and bug reports are welcome at the GitHub issues link in the page footer.</div>
                    </details>

                    <details class="faq-item">
                        <summary>Where can I get help? <span class="faq-icon">+</span></summary>
                        <div class="faq-answer">The in-game <strong>Wiki</strong> covers most mechanics in detail with guides for beginners, the market, land, districts, ETFs, crypto, and more — accessible from the main menu after signing in. The in-game <strong>chat</strong> is the fastest way to reach experienced players. For bugs or feature requests, file an issue on <a href="https://github.com/podcastmatt0285/symco/issues">GitHub</a>. You can also reach the developer directly through the contact info in the footer.</div>
                    </details>

                </div><!-- /faq-section -->
                """ + _leaderboard_section + """
            </div>
        </div>

        <!-- Indices card placeholder -->
        """ + _indices_card + """

        <!-- Intro video -->
        <div class="video-wrap">
            <iframe src="https://www.youtube.com/embed/_uunsDAShzM?si=34QJSMx-dj_-Imf3"
                    title="YouTube video player"
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                    referrerpolicy="strict-origin-when-cross-origin"
                    allowfullscreen></iframe>
        </div>
    </div>

    <!-- Market tickers — fixed above footer, walnut aesthetic -->
    <div class="login-tickers">
        <div class="login-ticker">
            <span class="tk-label">MKT</span>
            <div class="tk-viewport">
                <div id="tkMkt" style="display:inline-block;white-space:nowrap;will-change:transform;transform:translateX(0);">Loading&hellip;</div>
            </div>
        </div>
        <div class="login-ticker">
            <span class="tk-label">DM</span>
            <div class="tk-viewport">
                <div id="tkDm" style="display:inline-block;white-space:nowrap;will-change:transform;transform:translateX(0);">Loading&hellip;</div>
            </div>
        </div>
        <div class="login-ticker">
            <span class="tk-label">STCK</span>
            <div class="tk-viewport">
                <div id="tkStk" style="display:inline-block;white-space:nowrap;will-change:transform;transform:translateX(0);">Loading&hellip;</div>
            </div>
        </div>
    </div>

    <footer style="position:fixed;bottom:0;left:0;right:0;padding:6px 16px;text-align:center;font-size:0.72rem;color:#475569;background:#020617;border-top:1px solid #1e293b;">
        <div style="display:flex;flex-wrap:wrap;gap:3px 10px;justify-content:center;margin-bottom:3px;">
            <a href="/sitemap"            style="color:#64748b;text-decoration:underline;">Sitemap</a>
            <a href="/company/whitepaper" style="color:#64748b;text-decoration:underline;">Whitepaper</a>
            <a href="/company/careers"    style="color:#64748b;text-decoration:underline;">Careers</a>
            <a href="/company/press-kit"  style="color:#64748b;text-decoration:underline;">Press Kit</a>
            <a href="/privacy-policy"     style="color:#64748b;text-decoration:underline;">Privacy Policy</a>
        </div>
        <span style="color:#334155;">&copy; 2026 Wadsworth Notifly. All rights reserved.</span>
    </footer>

    <script>
        function switchTab(tab) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            event.target.classList.add('active');

            document.querySelectorAll('.form').forEach(f => f.classList.remove('active'));
            document.getElementById(tab + '-form').classList.add('active');
        }

        // Client-side leaderboard re-ranking (no server round-trip; works logged-out)
        function lbSort(metric, btn) {
            var tbody = document.getElementById('lb-body');
            if (!tbody) return;
            var rows = Array.prototype.slice.call(tbody.querySelectorAll('tr'));
            rows.sort(function (a, b) {
                return parseFloat(b.dataset[metric] || 0) - parseFloat(a.dataset[metric] || 0);
            });
            rows.forEach(function (r, i) {
                tbody.appendChild(r);
                var rk = r.querySelector('.lb-rank');
                if (rk) {
                    if (i === 0)      rk.innerHTML = '<span class="lb-badge lb-gold">1st</span>';
                    else if (i === 1) rk.innerHTML = '<span class="lb-badge lb-silver">2nd</span>';
                    else if (i === 2) rk.innerHTML = '<span class="lb-badge lb-bronze">3rd</span>';
                    else              rk.textContent = (i + 1);
                }
            });
            document.querySelectorAll('.lb-tab').forEach(function (t) { t.classList.remove('active'); });
            if (btn) btn.classList.add('active');
            var tbl = document.getElementById('lb-table');
            if (tbl) {
                tbl.querySelectorAll('.lb-col-active').forEach(function (c) { c.classList.remove('lb-col-active'); });
                tbl.querySelectorAll('[data-col="' + metric + '"]').forEach(function (c) { c.classList.add('lb-col-active'); });
            }
        }

        (function () {
            const lines = [
                "Price is what you pay. Value is what you build.",
                "Every asset has a price. What\u2019s yours?",
                "In Wadsworth, liquidity is king.",
                "Wealth is just a function of time, land, and leverage.",
                "Master the supply chain. Rule the exchange.",
                "Govern cities, manipulate markets, and mint your own wealth.",
                "Real estate. Forex. Total vertical integration.",
                "Trade on the Wadsworth Exchange. Control the world.",
                "Scale your production. Leverage your assets. Crush your rivals.",
                "Corner the market. Liquidate the rest.",
                "Billion-dollar empires aren\u2019t built on good intentions.",
                "Where monopolies rise and margin calls loom.",
                "From a single prairie plot to global corporate hegemony.",
                "Hire the best. Short the rest.",
                "Capitalism, simulated.",
                "Initialize your portfolio.",
                "Build. Trade. Dominate.",
                "Your economic empire starts here.",
                "The market is open."
            ];

            // Fisher-Yates shuffle so the order is fresh each page load
            for (let i = lines.length - 1; i > 0; i--) {
                const j = Math.floor(Math.random() * (i + 1));
                [lines[i], lines[j]] = [lines[j], lines[i]];
            }

            const el = document.getElementById('marquee');
            let idx = 0;

            function showNext() {
                // Fade out
                el.classList.remove('visible');
                setTimeout(() => {
                    el.textContent = '\u201c' + lines[idx] + '\u201d';
                    idx = (idx + 1) % lines.length;
                    // Fade in
                    el.classList.add('visible');
                }, 900); // matches transition duration
            }

            showNext();
            setInterval(showNext, 5000); // 0.9s fade-out + ~3.2s display + 0.9s fade-in
        })();

        // ── Three market tickers (auto-scroll, walnut aesthetic) ──
        (function () {
            var BASE_SPEEDS = [0.9, 0.72, 0.55]; // per-row px/frame

            var tracks     = [document.getElementById('tkMkt'), document.getElementById('tkDm'), document.getElementById('tkStk')];
            var halfWidths = [0, 0, 0];
            var offsets    = [0, 0, 0];

            function step() {
                for (var i = 0; i < tracks.length; i++) {
                    var el = tracks[i];
                    if (!halfWidths[i] && el.scrollWidth > 10) halfWidths[i] = el.scrollWidth / 2;
                    var hw = halfWidths[i] || 1;
                    offsets[i] -= BASE_SPEEDS[i];
                    if (offsets[i] < -hw) offsets[i] += hw;
                    el.style.transform = 'translateX(' + offsets[i] + 'px)';
                }
                requestAnimationFrame(step);
            }

            requestAnimationFrame(step);

            function fmt(v) {
                if (v == null) return '—';
                return v >= 1000 ? '$' + (+v).toLocaleString(undefined, {maximumFractionDigits: 0})
                                 : '$' + (+v).toFixed(2);
            }

            fetch('/api/public/ticker').then(function(r) { return r.json(); }).then(function(d) {
                var mktParts = (d.commodities || []).map(function(it) {
                    return (it.label || it.name || '') + ': ' + fmt(it.price);
                });
                if (!mktParts.length) mktParts.push('MARKET OPENING…');
                var mktText = mktParts.join('  ·  ');
                tracks[0].textContent = mktText + '       ' + mktText;

                var dmParts = (d.district || []).map(function(it) {
                    return (it.label || it.name || '') + ': ' + fmt(it.price);
                });
                if (!dmParts.length) dmParts.push('NO DISTRICT TRADES YET');
                var dmText = dmParts.join('  ·  ');
                tracks[1].textContent = dmText + '       ' + dmText;

                var stkParts = (d.stocks || []).map(function(it) {
                    return (it.label || '') + ' ' + fmt(it.price);
                });
                if (!stkParts.length) stkParts.push('NO STOCKS LISTED');
                var stkText = stkParts.join('  ·  ');
                tracks[2].textContent = stkText + '       ' + stkText;

                halfWidths = [0, 0, 0]; // remeasure after content loads
            }).catch(function() {
                tracks[0].textContent = 'MARKET FEED OFFLINE       MARKET FEED OFFLINE';
                tracks[1].textContent = 'DISTRICT MARKET FEED OFFLINE       DISTRICT MARKET FEED OFFLINE';
                tracks[2].textContent = 'STOCK FEED OFFLINE       STOCK FEED OFFLINE';
                halfWidths = [0, 0, 0];
            });
        })();

        // Pin tickers exactly above the footer regardless of footer height or wrapping
        (function() {
            var footer  = document.querySelector('footer');
            var tickers = document.querySelector('.login-tickers');
            if (!footer || !tickers) return;
            function pin() { tickers.style.bottom = footer.offsetHeight + 'px'; }
            pin();
            window.addEventListener('resize', pin);
            // Re-pin after fonts/images settle
            window.addEventListener('load', pin);
        })();
    </script>
    <script>
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/sw.js').catch(() => {});
        }
    </script>
    <!-- nav-loader: show on every page load and every same-origin navigation -->
    <div id="nav-loader" style="display:none;position:fixed;inset:0;z-index:9999;background:#0D0806;color:#F5F5DC;font-family:Georgia,serif;align-items:center;justify-content:center;padding:12px;">
      <div style="position:relative;width:100%;max-width:420px;padding:clamp(16px,5vw,40px);background:#1A0F0A;border:4px solid #2D1810;box-shadow:0 25px 50px rgba(0,0,0,.8);display:flex;flex-direction:column;align-items:center;box-sizing:border-box;max-height:92vh;overflow-y:auto;">
        <div style="width:min(90px,22vw);height:min(90px,22vw);display:flex;align-items:center;justify-content:center;flex-shrink:0;">
          <img src="/static/logo.png?v=3" alt="" class="nl-logo" style="width:100%;height:100%;object-fit:contain;filter:drop-shadow(0 0 12px rgba(176,141,87,0.5));">
        </div>
        <p style="font-size:13px;font-style:italic;color:#B08D57;margin:12px 0 6px;text-align:center;">Loading&hellip;</p>
        <div style="width:100%;height:3px;background:#2D1810;border-radius:2px;overflow:hidden;margin-top:4px;">
          <div id="nl-bar-login" style="height:100%;width:0%;background:linear-gradient(90deg,#B08D57,#e5c88a);transition:width .15s linear;border-radius:2px;"></div>
        </div>
      </div>
    </div>
    <script>
    (function(){
      var ov=document.getElementById('nav-loader');
      var bar=document.getElementById('nl-bar-login');
      var prog=0,timer=null;
      function start(){
        if(timer)clearInterval(timer);
        prog=0;ov.style.display='flex';
        timer=setInterval(function(){prog+=5;if(prog>=100)prog=0;bar.style.width=prog+'%';},150);
      }
      function hide(){ov.style.display='none';clearInterval(timer);timer=null;}
      start();
      document.addEventListener('DOMContentLoaded',hide);
      document.addEventListener('click',function(e){
        var a=e.target.closest('a');if(!a)return;
        if(a.target==='_blank'||a.hasAttribute('download'))return;
        var h=a.getAttribute('href');if(!h||h.charAt(0)==='#'||/^(javascript|mailto|tel):/.test(h))return;
        try{var u=new URL(a.href,location.origin);if(u.origin!==location.origin)return;start();}catch(ex){}
      });
      document.addEventListener('submit',function(e){
        var f=e.target;if(!f)return;
        try{var u=new URL(f.action||location.href,location.origin);if(u.origin!==location.origin)return;start();}catch(ex){}
      });
      window.addEventListener('pageshow',function(e){if(e.persisted)hide();});
    })();
    </script>
    <script>
    // Android widget device-link: read _wdid from URL (appended by LauncherActivity)
    // and persist it to sessionStorage so the shell JS can link it after login.
    (function(){
      try {
        var p = new URLSearchParams(window.location.search);
        var wdid = p.get('_wdid');
        if (wdid) {
          sessionStorage.setItem('_wdid', wdid);
          // Inject as hidden input into login + register forms so it survives POST
          document.querySelectorAll('form').forEach(function(f) {
            var inp = document.createElement('input');
            inp.type = 'hidden'; inp.name = '_wdid'; inp.value = wdid;
            f.appendChild(inp);
          });
        }
      } catch(e) {}
    })();
    </script>
</body>
</html>
""")

@router.post("/api/login")
async def login(
    request: Request,
    response: Response,
    business_name: str = Form(...),
    password: str = Form(...),
    wdid: Optional[str] = Form(None, alias="_wdid")
):
    """Handle login form submission."""
    db = get_db()

    player = authenticate_player(db, business_name, password)

    if not player:
        db.close()
        return RedirectResponse(
            url="/login?error=Invalid%20credentials",
            status_code=303
        )

    # Check for active ban/timeout
    try:
        from admins import get_active_ban
        active_ban = get_active_ban(player.id)
        if active_ban:
            db.close()
            if active_ban["type"] == "ban":
                reason = active_ban.get("reason", "")
                msg = "Your account has been banned."
                if reason:
                    msg += f" Reason: {reason}"
            else:
                expires = active_ban.get("expires_at", "")[:16].replace("T", " ")
                msg = f"Your account is timed out until {expires} UTC."
            import urllib.parse
            return RedirectResponse(
                url=f"/login?error={urllib.parse.quote(msg)}",
                status_code=303
            )
    except ImportError:
        pass

    # Track login IP and detect cross-account IP collisions
    forwarded_for = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
    login_ip = forwarded_for or (request.client.host if request.client else None)
    login_ua = (request.headers.get("User-Agent", "") or "")[:512] or None

    if login_ip:
        try:
            db.add(PlayerLoginIP(
                player_id=player.id,
                ip_address=login_ip,
                user_agent=login_ua,
            ))
            # Check if this IP has recently been used by a DIFFERENT account.
            # We don't auto-ban (shared wifi / NAT is common) but log for admin review.
            collision = (
                db.query(PlayerLoginIP)
                .filter(
                    PlayerLoginIP.ip_address == login_ip,
                    PlayerLoginIP.player_id  != player.id,
                    PlayerLoginIP.logged_in_at >= datetime.utcnow() - timedelta(days=30),
                )
                .first()
            )
            db.commit()
            if collision:
                try:
                    from admins import log_action
                    log_action(
                        admin_id=0,
                        action="suspicious_login_ip",
                        target_player_id=player.id,
                        details=(
                            f"Login from IP {login_ip} also used by "
                            f"player #{collision.player_id} within 30 days."
                        ),
                    )
                except Exception:
                    pass
        except Exception as _lip_err:
            db.rollback()
            print(f"[Auth] Login IP tracking error: {_lip_err}")

    session_token = create_session(db, player.id)
    db.close()

    # Detect TWA (Android app) login and fire beta rewards
    twa_header = request.headers.get("X-Requested-With", "")
    if twa_header == "cc.notifly.wadsworth.twa":
        try:
            from beta import handle_twa_login
            handle_twa_login(player.id)
        except Exception as _twa_err:
            print(f"[Auth] TWA handler error: {_twa_err}")

    dest = "/?_wdid=" + wdid if wdid else "/"
    redirect = RedirectResponse(url=dest, status_code=303)
    redirect.set_cookie(
        key="session_token",
        value=session_token,
        max_age=60 * 60 * 24 * 7,
        httponly=True
    )

    return redirect

@router.post("/api/register")
async def register(
    request: Request,
    response: Response,
    business_name: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    wdid: Optional[str] = Form(None, alias="_wdid")
):
    """Handle registration form submission."""
    db = get_db()

    if password != password_confirm:
        db.close()
        return RedirectResponse(
            url="/login?error=Passwords%20do%20not%20match",
            status_code=303
        )

    if len(password) < 8:
        db.close()
        return RedirectResponse(
            url="/login?error=Password%20must%20be%20at%20least%208%20characters",
            status_code=303
        )

    # Business name content filter
    import urllib.parse as _up
    name_error = validate_business_name(business_name)
    if name_error:
        db.close()
        return RedirectResponse(
            url=f"/login?error={_up.quote(name_error)}",
            status_code=303,
        )

    # Resolve the client IP, honouring a reverse-proxy X-Forwarded-For header.
    forwarded_for = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
    ip_address = forwarded_for or (request.client.host if request.client else None)
    user_agent = (request.headers.get("User-Agent", "") or "")[:512] or None

    player = create_player(db, business_name.strip(), password,
                           ip_address=ip_address, user_agent=user_agent)

    if not player:
        db.close()
        return RedirectResponse(
            url="/login?error=Business%20name%20already%20exists",
            status_code=303
        )

    # --- Multi-account detection ---
    # If another account was already registered from this IP, this is an alt.
    # Ban the new account immediately and penalise the original account.
    MULTI_ACCOUNT_FINE = 10_000.0
    if ip_address:
        prior_ip_row = (
            db.query(PlayerRegistrationIP)
            .filter(
                PlayerRegistrationIP.ip_address == ip_address,
                PlayerRegistrationIP.player_id != player.id,
            )
            .order_by(PlayerRegistrationIP.registered_at.asc())
            .first()
        )
        prior = (
            db.query(Player).filter(Player.id == prior_ip_row.player_id).first()
            if prior_ip_row else None
        )
        if prior:
            print(
                f"[Auth] Multi-account detected: new #{player.id} ({business_name}) "
                f"shares IP {ip_address} with existing #{prior.id} ({prior.business_name})"
            )
            # Auto-ban the alt account.
            try:
                from admins import ban_player
                ban_player(
                    admin_id=0,
                    player_id=player.id,
                    reason=(
                        f"Alternate account. Primary account: "
                        f"{prior.business_name} (#{prior.id})"
                    ),
                )
            except Exception as e:
                print(f"[Auth] Failed to auto-ban alt account: {e}")

            # Credit-score penalty on the original account.
            try:
                from banks.brokerage_firm import modify_credit_score
                modify_credit_score(prior.id, "multi_account_detected")
            except Exception as e:
                print(f"[Auth] Failed to apply credit penalty: {e}")

            # Cash fine on the original account (respects foreign legal tender).
            try:
                from reserve_banks import spend_player_funds, get_usd_balance
                bal = get_usd_balance(prior.id) or 0.0
                fine = min(MULTI_ACCOUNT_FINE, bal)
                if fine > 0:
                    spend_player_funds(prior.id, fine)
            except Exception as _fine_err:
                print(f"[Auth] Multi-account fine error: {_fine_err}")
            db.commit()

            db.close()
            import urllib.parse
            msg = (
                f"Account banned: an account already exists from this connection. "
                f"Your primary account ({prior.business_name}) has been fined "
                f"${MULTI_ACCOUNT_FINE:,.0f} and received a credit score penalty."
            )
            return RedirectResponse(
                url=f"/login?error={urllib.parse.quote(msg)}",
                status_code=303,
            )
    # --- end multi-account detection ---

    session_token = create_session(db, player.id)
    db.close()

    dest = "/?_wdid=" + wdid if wdid else "/"
    redirect = RedirectResponse(url=dest, status_code=303)
    redirect.set_cookie(
        key="session_token",
        value=session_token,
        max_age=60 * 60 * 24 * 7,
        httponly=True
    )

    return redirect

@router.get("/founding", response_class=HTMLResponse)
def founding_page():
    """Public landing page for the Founding Operative beta program — no login required."""
    from beta import (
        PLAY_STORE_URL, GOOGLE_GROUP_URL, TESTER_OPTIN_URL,
        FOUNDING_OPERATIVE_TROPHIES, POCKET_EMPIRE_TROPHIES, ACTIVE_DUTY_TROPHIES,
        SUB_TRIAL_DAYS, get_available_count, get_total_count,
    )
    try:
        _available = get_available_count()
        _total     = get_total_count()
        _assigned  = _total - _available
        _slots_pct = int((_assigned / _total) * 100) if _total else 0
        _slots_html = f'''
            <div class="fo-meter-wrap">
                <div class="fo-meter-bar"><div class="fo-meter-fill" style="width:{_slots_pct}%;"></div></div>
                <div class="fo-meter-label">{_assigned} / {_total} Pro bonus slots claimed</div>
            </div>'''
        if _available == 0:
            _cta_html = f'''
            <a href="{TESTER_OPTIN_URL}" class="fo-btn fo-btn-gold" target="_blank" rel="noopener">
                📲&nbsp; Opt In as Tester
            </a>
            <a href="{PLAY_STORE_URL}" class="fo-btn fo-btn-primary" target="_blank" rel="noopener">
                ▶&nbsp; Download FREE on Google Play
            </a>
            <div class="fo-full-msg" style="margin-top:0;">All Pro bonus slots have been filled — but you can still download the free app and join as a tester!</div>'''
        else:
            _cta_html = f'''
            <a href="{TESTER_OPTIN_URL}" class="fo-btn fo-btn-gold" target="_blank" rel="noopener">
                📲&nbsp; Opt In as Tester
            </a>
            <a href="{PLAY_STORE_URL}" class="fo-btn fo-btn-primary" target="_blank" rel="noopener">
                ▶&nbsp; Download FREE on Google Play
            </a>
            <a href="{GOOGLE_GROUP_URL}" class="fo-btn fo-btn-secondary" target="_blank" rel="noopener">
                Join the Google Group
            </a>
            <a href="/login" class="fo-btn fo-btn-secondary">
                Log In &amp; Submit Email for Pro Bonus
            </a>'''
    except Exception:
        _available = 0
        _total     = 48
        _slots_html = ""
        _cta_html = f'''
            <a href="{TESTER_OPTIN_URL}" class="fo-btn fo-btn-gold" target="_blank" rel="noopener">
                📲&nbsp; Opt In as Tester
            </a>
            <a href="{PLAY_STORE_URL}" class="fo-btn fo-btn-primary" target="_blank" rel="noopener">
                ▶&nbsp; Download FREE on Google Play
            </a>
            <a href="{GOOGLE_GROUP_URL}" class="fo-btn fo-btn-secondary" target="_blank" rel="noopener">
                Join the Google Group
            </a>
            <a href="/login" class="fo-btn fo-btn-secondary">
                Log In &amp; Submit Email for Pro Bonus
            </a>'''

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Founding Operative · Wadsworth Tycoon</title>
    <meta name="description" content="Join the Wadsworth Economic Tycoon Simulator as a Founding Tester. The app is FREE — download it, earn 150 trophies, get a permanent badge, and claim 30 days of Wadsworth Pro FREE.">

    <!-- Open Graph / Reddit / Discord rich preview -->
    <meta property="og:type"        content="website">
    <meta property="og:title"       content="🎖️ Founding Operative — Wadsworth Tycoon">
    <meta property="og:description" content="Wadsworth Android is FREE. Join the closed beta, earn 150 trophies, get a permanent Founding Tester badge + {_available} Pro bonus slots remaining.">
    <meta property="og:image"       content="/static/icons/apple-touch-icon.png">
    <meta property="og:url"         content="/founding">
    <meta name="twitter:card"       content="summary">
    <meta name="twitter:title"      content="🎖️ Founding Operative — Wadsworth Tycoon">
    <meta name="twitter:description" content="Wadsworth Android is FREE to download. 150 trophies · exclusive badge · 30 days of Pro FREE. {_available} Pro slots left.">

    <link rel="manifest" href="/manifest.json">
    <meta name="theme-color" content="#020617">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@700;900&family=EB+Garamond:ital@0;1&display=swap" rel="stylesheet">

    <style>
        *{{ margin:0; padding:0; box-sizing:border-box; }}
        body{{
            font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
            background:#0b1220; color:#e5e7eb;
            min-height:100vh; display:flex; flex-direction:column; align-items:center;
            padding:32px 16px 80px;
        }}
        .fo-wrap{{ max-width:560px; width:100%; }}

        /* ── Game title + logo ── */
        .fo-game-title{{
            text-align:center; margin-bottom:12px;
            font-size:18px; font-weight:700; letter-spacing:0.04em; line-height:1.25;
            background:linear-gradient(90deg,#B08D57,#e5c88a,#B08D57);
            -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent;
        }}
        .fo-logo{{ text-align:center; margin-bottom:20px; }}
        .fo-logo img{{ width:80px; height:auto; }}

        /* ── Hero card (same aesthetic as login hero) ── */
        .fo-card{{
            position:relative; padding:40px 28px 36px; text-align:center;
            border-radius:16px; overflow:hidden;
            background:radial-gradient(ellipse at 50% 0%,rgba(202,138,4,.10) 0%,rgba(12,10,9,0) 60%),
                        linear-gradient(160deg,#14100c 0%,#0c0a09 55%,#14100c 100%);
            border:1px solid rgba(176,141,87,0.28);
            box-shadow:0 22px 60px rgba(0,0,0,.6), inset 0 1px 0 rgba(255,225,170,.06);
        }}
        .fo-gear{{
            position:absolute; opacity:0.055; fill:#eab308;
            pointer-events:none; z-index:0;
        }}
        .fo-gear.g1{{ top:-54px; left:-50px;  width:200px; height:200px;
                      animation:fo-gear-rotate 26s linear infinite; }}
        .fo-gear.g2{{ bottom:-60px; right:-56px; width:240px; height:240px;
                      animation:fo-gear-rotate 46s linear infinite reverse; }}
        @keyframes fo-gear-rotate{{ from{{transform:rotate(0deg)}} to{{transform:rotate(360deg)}} }}
        @media(prefers-reduced-motion:reduce){{ .fo-gear{{animation:none}} }}
        .fo-inner{{ position:relative; z-index:1; }}

        .fo-kicker{{
            font-family:'Cinzel',serif; font-size:0.62rem; font-weight:700;
            letter-spacing:0.38em; text-transform:uppercase;
            color:rgba(202,138,4,.78); margin-bottom:14px;
        }}
        .fo-title{{
            font-family:'Cinzel',serif; font-weight:900;
            font-size:clamp(2rem,8vw,2.8rem); line-height:1.0;
            text-transform:uppercase; letter-spacing:0.01em;
            background:linear-gradient(90deg,#ca8a04 0%,#ca8a04 40%,#fef08a 50%,#ca8a04 60%,#ca8a04 100%);
            background-size:200% auto;
            -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent;
            filter:drop-shadow(0 0 2px rgba(253,224,71,.4));
            animation:fo-gold-shine 3.4s linear infinite;
        }}
        @keyframes fo-gold-shine{{ to{{background-position:200% center}} }}

        .fo-divider{{
            display:flex; align-items:center; justify-content:center; gap:14px; margin:22px 0;
        }}
        .fo-divider .hd-line{{
            height:1px; width:56px; background:linear-gradient(90deg,transparent,rgba(234,179,8,.75));
        }}
        .fo-divider .hd-line.right{{
            background:linear-gradient(90deg,rgba(234,179,8,.75),transparent);
        }}
        .fo-divider .hd-diamond{{
            width:9px; height:9px; transform:rotate(45deg);
            border:1px solid #facc15; background:rgba(202,138,4,.4);
        }}

        .fo-subtitle{{
            font-family:'EB Garamond',Georgia,serif; font-style:italic;
            font-size:1.12rem; line-height:1.6; color:#e7e2d8;
            margin:0 auto; max-width:380px; text-shadow:0 1px 6px rgba(0,0,0,.5);
        }}

        /* ── Trophy reward pills ── */
        .fo-rewards{{
            display:flex; flex-wrap:wrap; gap:10px; justify-content:center; margin:24px 0 0;
        }}
        .fo-reward-pill{{
            display:flex; align-items:center; gap:7px;
            background:rgba(30,41,59,.7); border:1px solid rgba(176,141,87,.22);
            border-radius:999px; padding:8px 14px;
        }}
        .fo-reward-icon{{ font-size:1.1rem; }}
        .fo-reward-text{{ font-size:0.78rem; line-height:1.3; text-align:left; }}
        .fo-reward-title{{ font-weight:700; color:#e5c88a; }}
        .fo-reward-sub{{ color:#94a3b8; font-size:0.7rem; }}

        /* ── Slot meter ── */
        .fo-meter-wrap{{ margin:22px 0 0; }}
        .fo-meter-bar{{
            height:6px; background:rgba(255,255,255,.08); border-radius:3px; overflow:hidden;
        }}
        .fo-meter-fill{{
            height:100%; background:linear-gradient(90deg,#B08D57,#e5c88a);
            border-radius:3px; transition:width .6s ease;
        }}
        .fo-meter-label{{
            font-size:0.72rem; color:#94a3b8; margin-top:6px; text-align:center;
        }}

        /* ── CTA buttons ── */
        .fo-cta{{ display:flex; flex-direction:column; gap:12px; margin-top:24px; }}
        .fo-btn{{
            display:block; width:100%; padding:14px 20px;
            border:none; border-radius:10px; font-size:0.92rem; font-weight:700;
            font-family:inherit; cursor:pointer; text-decoration:none; text-align:center;
            transition:opacity .2s, transform .1s;
        }}
        .fo-btn:hover{{ opacity:.88; transform:translateY(-1px); }}
        .fo-btn-primary{{ background:#38bdf8; color:#020617; }}
        .fo-btn-gold{{ background:linear-gradient(90deg,#B08D57,#e5c88a); color:#14100c; }}
        .fo-btn-secondary{{
            background:transparent; color:#94a3b8;
            border:1px solid rgba(176,141,87,.25);
        }}
        .fo-btn-secondary:hover{{ color:#e5c88a; border-color:rgba(176,141,87,.5); }}
        .fo-full-msg{{
            margin-top:20px; padding:14px; border-radius:8px;
            background:rgba(239,68,68,.1); border:1px solid rgba(239,68,68,.25);
            color:#fca5a5; font-size:0.85rem; text-align:center;
        }}

        /* ── Steps accordion ── */
        .fo-steps{{
            margin-top:36px; border-top:1px solid rgba(176,141,87,.18);
            padding-top:28px; text-align:left;
        }}
        .fo-steps-heading{{
            font-family:'Cinzel',serif; font-size:0.72rem; font-weight:700;
            letter-spacing:0.3em; text-transform:uppercase;
            color:rgba(202,138,4,.82); text-align:center; margin-bottom:22px;
        }}
        .fo-step{{
            border-bottom:1px solid rgba(255,255,255,.055);
        }}
        .fo-step summary{{
            padding:13px 2px; cursor:pointer; font-size:0.87rem; font-weight:600;
            color:#e2e8f0; list-style:none;
            display:flex; justify-content:space-between; align-items:flex-start;
            gap:10px; transition:color .15s; user-select:none;
        }}
        .fo-step summary::-webkit-details-marker{{ display:none; }}
        .fo-step summary:hover{{ color:#fef08a; }}
        .fo-step-icon{{
            flex-shrink:0; margin-top:1px; font-size:1rem; font-weight:300;
            color:rgba(202,138,4,.7); transition:transform .2s; line-height:1;
        }}
        .fo-step[open] .fo-step-icon{{ transform:rotate(45deg); }}
        .fo-step-body{{
            padding:2px 4px 16px; font-size:0.82rem; color:#94a3b8; line-height:1.72;
        }}
        .fo-step-body strong{{ color:#cbd5e1; }}
        .fo-step-body a{{ color:#38bdf8; }}

        /* ── Footer ── */
        .fo-footer{{
            margin-top:36px; text-align:center; font-size:0.72rem; color:#334155;
            padding-top:20px; border-top:1px solid rgba(255,255,255,.04);
        }}
        .fo-footer a{{ color:#38bdf8; text-decoration:none; }}
    </style>
</head>
<body>
<div class="fo-wrap">

    <div class="fo-game-title">Wadsworth Economic Tycoon Simulator</div>
    <div class="fo-logo"><img src="/static/logo.png?v=3" alt="Wadsworth"></div>

    <div class="fo-card">
        <!-- decorative gears -->
        <svg class="fo-gear g1" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M12 15.5A3.5 3.5 0 0 1 8.5 12 3.5 3.5 0 0 1 12 8.5a3.5 3.5 0 0 1 3.5 3.5 3.5 3.5 0 0 1-3.5 3.5m7.43-2.92c.04-.34.07-.69.07-1.08s-.03-.74-.07-1.08l2.32-1.81c.21-.16.27-.45.13-.68l-2.2-3.81c-.13-.23-.42-.31-.65-.23l-2.74 1.1c-.57-.44-1.18-.81-1.86-1.08L14 2.42A.517.517 0 0 0 13.5 2h-4.4a.517.517 0 0 0-.5.42l-.41 2.42c-.68.27-1.3.64-1.87 1.08l-2.73-1.1c-.24-.08-.52 0-.65.23L.74 8.86c-.14.23-.08.52.13.68l2.32 1.81C3.15 11.69 3.12 12 3.12 12s.03.69.07 1.08L.87 14.89c-.21.16-.27.45-.13.68l2.2 3.81c.13.23.41.31.65.23l2.73-1.1c.57.44 1.19.81 1.87 1.08l.41 2.42c.07.23.28.42.5.42H13.5c.23 0 .44-.19.5-.42l.41-2.42c.68-.27 1.29-.64 1.86-1.08l2.74 1.1c.23.08.52 0 .65-.23l2.2-3.81c.14-.23.08-.52-.13-.68l-2.3-1.81z"/></svg>
        <svg class="fo-gear g2" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M12 15.5A3.5 3.5 0 0 1 8.5 12 3.5 3.5 0 0 1 12 8.5a3.5 3.5 0 0 1 3.5 3.5 3.5 3.5 0 0 1-3.5 3.5m7.43-2.92c.04-.34.07-.69.07-1.08s-.03-.74-.07-1.08l2.32-1.81c.21-.16.27-.45.13-.68l-2.2-3.81c-.13-.23-.42-.31-.65-.23l-2.74 1.1c-.57-.44-1.18-.81-1.86-1.08L14 2.42A.517.517 0 0 0 13.5 2h-4.4a.517.517 0 0 0-.5.42l-.41 2.42c-.68.27-1.3.64-1.87 1.08l-2.73-1.1c-.24-.08-.52 0-.65.23L.74 8.86c-.14.23-.08.52.13.68l2.32 1.81C3.15 11.69 3.12 12 3.12 12s.03.69.07 1.08L.87 14.89c-.21.16-.27.45-.13.68l2.2 3.81c.13.23.41.31.65.23l2.73-1.1c.57.44 1.19.81 1.87 1.08l.41 2.42c.07.23.28.42.5.42H13.5c.23 0 .44-.19.5-.42l.41-2.42c.68-.27 1.29-.64 1.86-1.08l2.74 1.1c.23.08.52 0 .65-.23l2.2-3.81c.14-.23.08-.52-.13-.68l-2.3-1.81z"/></svg>

        <div class="fo-inner">
            <div class="fo-kicker">Limited Program</div>
            <h1 class="fo-title">Founding<br>Operative</h1>

            <div class="fo-divider">
                <div class="hd-line"></div>
                <div class="hd-diamond"></div>
                <div class="hd-line right"></div>
            </div>

            <p class="fo-subtitle">
                Be among the first to build your empire on Android.
                The app is <strong style="color:#e5c88a;font-style:normal;">FREE to download</strong> —
                join the closed beta, earn a permanent Founding Tester badge,
                and claim <strong style="color:#c4b5fd;font-style:normal;">{SUB_TRIAL_DAYS} days of Wadsworth Pro FREE</strong>.
            </p>

            <div class="fo-rewards">
                <div class="fo-reward-pill">
                    <span class="fo-reward-icon">🎖️</span>
                    <div class="fo-reward-text">
                        <div class="fo-reward-title">{FOUNDING_OPERATIVE_TROPHIES} Trophies</div>
                        <div class="fo-reward-sub">Founding Operative</div>
                    </div>
                </div>
                <div class="fo-reward-pill">
                    <span class="fo-reward-icon">📱</span>
                    <div class="fo-reward-text">
                        <div class="fo-reward-title">{POCKET_EMPIRE_TROPHIES} Trophies</div>
                        <div class="fo-reward-sub">Pocket Empire (first login)</div>
                    </div>
                </div>
                <div class="fo-reward-pill">
                    <span class="fo-reward-icon">⚔️</span>
                    <div class="fo-reward-text">
                        <div class="fo-reward-title">{ACTIVE_DUTY_TROPHIES} Trophies / day</div>
                        <div class="fo-reward-sub">Active Duty (daily login)</div>
                    </div>
                </div>
                <div class="fo-reward-pill">
                    <span class="fo-reward-icon">✨</span>
                    <div class="fo-reward-text">
                        <div class="fo-reward-title">Permanent Badge</div>
                        <div class="fo-reward-sub">Visible on your contact card</div>
                    </div>
                </div>
                <div class="fo-reward-pill" style="border-color:rgba(124,58,237,.45);">
                    <span class="fo-reward-icon">👑</span>
                    <div class="fo-reward-text">
                        <div class="fo-reward-title" style="color:#c4b5fd;">30 Days of Pro — FREE</div>
                        <div class="fo-reward-sub">Basic-tier supporters subscription</div>
                    </div>
                </div>
            </div>

            {_slots_html}

            <div class="fo-cta">
                {_cta_html}
            </div>
        </div>

        <!-- steps -->
        <div class="fo-steps">
            <div class="fo-steps-heading">How It Works</div>

            <details class="fo-step">
                <summary>Step 1 — Create a free account <span class="fo-step-icon">+</span></summary>
                <div class="fo-step-body">
                    <a href="/login">Register at the game</a> — it's free, no credit card needed.
                    You'll start as a new tycoon in the Wadsworth economy with your own land,
                    businesses, and market access. The game runs entirely in the browser; no app
                    required for step 1.
                </div>
            </details>

            <details class="fo-step">
                <summary>Step 2 — Join the Google Group <span class="fo-step-icon">+</span></summary>
                <div class="fo-step-body">
                    Visit <a href="{GOOGLE_GROUP_URL}" target="_blank" rel="noopener">groups.google.com/g/wadstycoon</a>
                    and click <strong>Join group</strong> with your Google account. Google Play
                    uses this group to manage the closed-testing roster — membership is required
                    for the tester download link to work. The group is free to join.
                </div>
            </details>

            <details class="fo-step">
                <summary>Step 3 — Submit your Google email in-game <span class="fo-step-icon">+</span></summary>
                <div class="fo-step-body">
                    Log in, go to <strong>Events &amp; Tasks</strong>, and find the
                    <strong>Founding Operative</strong> event. Submit the Google account email
                    you used to join the group. An admin will verify your membership —
                    usually within a few hours — and send you a dashboard notification with the
                    tester download link <strong>plus a bonus code for
                    <span style="color:#c4b5fd;">{SUB_TRIAL_DAYS} days of Wadsworth Pro FREE</span></strong>.
                </div>
            </details>

            <details class="fo-step">
                <summary>Step 4 — Opt in as a tester &amp; download the free app <span class="fo-step-icon">+</span></summary>
                <div class="fo-step-body">
                    Visit <a href="{TESTER_OPTIN_URL}" target="_blank" rel="noopener">the tester opt-in page</a>
                    and tap <strong>Become a tester</strong>. After that, the
                    <a href="{PLAY_STORE_URL}" target="_blank" rel="noopener">Play Store listing</a>
                    will show a free <strong>Install</strong> button. The app is a Trusted Web
                    Activity (TWA) — the same game you play in the browser, wrapped with native
                    Android notifications and a home-screen widget.
                </div>
            </details>

            <details class="fo-step">
                <summary>Step 5 — Log in from the app &amp; earn your badge <span class="fo-step-icon">+</span></summary>
                <div class="fo-step-body">
                    The first time you load the game from the Android app, the
                    <strong>Pocket Empire</strong> event automatically completes —
                    awarding {POCKET_EMPIRE_TROPHIES} trophies and stamping your permanent
                    <em>Founding Tester</em> badge onto your contact card.
                    From that point on, every daily login from the app earns
                    <strong>{ACTIVE_DUTY_TROPHIES} Active Duty trophies</strong>.
                </div>
            </details>
        </div>
    </div>

    <div class="fo-footer">
        <a href="/login">Play in browser</a> &nbsp;·&nbsp;
        <a href="/banks/indices/unloggedin">Market Indices</a> &nbsp;·&nbsp;
        <a href="{PLAY_STORE_URL}" target="_blank" rel="noopener">Google Play</a>
        <br><br>
        Wadsworth Economic Tycoon Simulator — Android closed testing
    </div>

</div>
</body>
</html>"""


@router.get("/api/logout")
async def logout(session_token: Optional[str] = Cookie(None)):
    """Handle logout."""
    db = get_db()
    
    if session_token:
        active_sessions.pop(session_token, None)
        
        session = db.query(Session).filter(Session.session_token == session_token).first()
        if session:
            db.delete(session)
            db.commit()
    
    db.close()
    
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(key="session_token")
    
    return response

# ==========================
# MODULE LIFECYCLE
# ==========================
def initialize():
    """Initialize auth module."""
    print("[Auth] Creating database tables...")
    Base.metadata.create_all(bind=engine)
    migrate_player_table()
    migrate_ip_tables()
    ensure_government_account()
    print("[Auth] Module initialized")


def ensure_government_account():
    """Ensure the federal government Player row (id=0) exists.

    The government's money lives in PlayerCurrencyBalance(player_id=0) — but
    many subsystems (cities, counties, districts, banks) look up the ORM Player
    row via ``Player.id == 0`` and silently skip when it's missing. Notably the
    admin "Government Fiscal Controls" return "Government account not found"
    when the row is absent. Creating an idempotent placeholder row fixes them
    all at once without touching the balance (which is a property over
    PlayerCurrencyBalance and is therefore unaffected).
    """
    db = get_db()
    try:
        gov = db.query(Player).filter(Player.id == 0).first()
        if gov:
            return gov
        # An account may already occupy the reserved name from a prior partial
        # run — reuse it rather than colliding on the unique business_name.
        existing = db.query(Player).filter(Player.business_name == "Federal Government").first()
        if existing:
            return existing
        gov = Player(
            id=0,
            business_name="Federal Government",
            password_hash=hash_password("!government-no-login!"),
            is_npc=True,
        )
        db.add(gov)
        db.commit()
        print("[Auth] Created federal government account (id=0)")
        return gov
    except Exception as e:
        db.rollback()
        print(f"[Auth] ensure_government_account error: {e}")
        return None
    finally:
        db.close()

def tick(current_tick: int, now):
    """Clean up expired sessions every 5 minutes."""
    if current_tick % 300 == 0:
        db = get_db()
        expired = db.query(Session).filter(Session.expires_at < now).all()
        
        for session in expired:
            active_sessions.pop(session.session_token, None)
            db.delete(session)
        
        if expired:
            db.commit()
            print(f"[Auth] Cleaned {len(expired)} expired sessions")
        
        db.close()

# ==========================
# PUBLIC API
# ==========================
__all__ = [
    'get_player_from_session',
    'transfer_cash',
    'get_db',
    'Player',
    'Session'
]
