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
from sqlalchemy import Column, String, DateTime, Integer, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# ==========================
# DATABASE SETUP
# ==========================
from database import engine, SessionLocal
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
    # Federal Communications Commission (FCC) licence — NULL = none active; datetime = expiry (UTC)
    cco_rental_expires = Column(DateTime, nullable=True, default=None)

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
        "ALTER TABLE players ADD COLUMN IF NOT EXISTS cco_rental_expires TIMESTAMP",
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
    
    return """
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
        <div class="logo"><img src="/static/logo.png" alt="Wadsworth"></div>

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
          <img src="/static/logo.png" alt="" style="width:100%;height:100%;object-fit:contain;filter:drop-shadow(0 0 12px rgba(229,0,0,0.4));">
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
"""

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
    print("[Auth] Module initialized")

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
