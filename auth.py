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
from sqlalchemy import Column, String, Float, DateTime, Integer
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
    cash_balance = Column(Float, default=50000.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, default=datetime.utcnow)
    tutorial_step = Column(Integer, default=0)  # 0=not started, 1-10=active, 11=complete
    registration_ip = Column(String, nullable=True, index=True)  # multi-account detection


class Session(Base):
    """Session model for authentication."""
    __tablename__ = "sessions"
    
    session_token = Column(String, primary_key=True, index=True)
    player_id = Column(Integer, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

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


def migrate_tutorial_column():
    """Add tutorial_step column to players table if it doesn't exist."""
    try:
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            conn.execute(
                __import__("sqlalchemy").text(
                    "ALTER TABLE players ADD COLUMN IF NOT EXISTS tutorial_step INTEGER DEFAULT 0"
                )
            )
    except Exception as e:
        print(f"[Auth] Migration warning (tutorial_step): {e}")


def migrate_registration_ip_column():
    """Add registration_ip column to players table if it doesn't exist."""
    try:
        # DDL must run outside a transaction (AUTOCOMMIT) so it cannot be
        # silently rolled back when the connection is returned to the pool.
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            conn.execute(
                __import__("sqlalchemy").text(
                    "ALTER TABLE players ADD COLUMN IF NOT EXISTS registration_ip TEXT"
                )
            )
        print("[Auth] registration_ip column ready")
    except Exception as e:
        print(f"[Auth] Migration error (registration_ip): {e}")


# ==========================
# CASH TRANSFER
# ==========================
def transfer_cash(from_player_id: int, to_player_id: int, amount: float) -> bool:
    """
    Safely transfer cash between two players.
    Used by Market module for trades.
    
    Returns:
        True if successful, False if insufficient funds
    """
    if amount <= 0:
        return False
    
    db = get_db()
    
    sender = db.query(Player).filter(Player.id == from_player_id).first()
    receiver = db.query(Player).filter(Player.id == to_player_id).first()
    
    if not sender or not receiver:
        db.close()
        return False
    
    if sender.cash_balance < amount:
        print(f"[Auth] Transfer failed: Player {from_player_id} has insufficient funds")
        db.close()
        return False
    
    sender.cash_balance -= amount
    receiver.cash_balance += amount
    
    db.commit()
    db.close()
    
    print(f"[Auth] Transferred ${amount:.2f} from Player {from_player_id} to Player {to_player_id}")
    return True

# ==========================
# AUTHENTICATION LOGIC
# ==========================
def create_player(db: Session, business_name: str, password: str, ip_address: Optional[str] = None) -> Optional[Player]:
    """Create a new player account."""
    existing = db.query(Player).filter(Player.business_name == business_name).first()
    if existing:
        return None

    player = Player(
        business_name=business_name,
        password_hash=hash_password(password),
        cash_balance=50000.0,
        registration_ip=ip_address,
    )
    
    db.add(player)
    db.commit()
    db.refresh(player)
    
    player_id = player.id
    print(f"[Auth] Created player {player_id}: {business_name}")
    
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
            align-items: center;
            justify-content: center;
        }

        .splash {
            max-width: 440px;
            width: 100%;
            padding: 32px;
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
    </div>

    <script>
        function switchTab(tab) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            event.target.classList.add('active');

            document.querySelectorAll('.form').forEach(f => f.classList.remove('active'));
            document.getElementById(tab + '-form').classList.add('active');
        }
    </script>
</body>
</html>
"""

@router.post("/api/login")
async def login(
    response: Response,
    business_name: str = Form(...),
    password: str = Form(...)
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

    session_token = create_session(db, player.id)
    db.close()

    redirect = RedirectResponse(url="/", status_code=303)
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
    password_confirm: str = Form(...)
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

    player = create_player(db, business_name.strip(), password, ip_address=ip_address)

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
        prior = (
            db.query(Player)
            .filter(Player.registration_ip == ip_address, Player.id != player.id)
            .order_by(Player.created_at.asc())
            .first()
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

            # Cash fine on the original account.
            prior.cash_balance = max(0.0, prior.cash_balance - MULTI_ACCOUNT_FINE)
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

    redirect = RedirectResponse(url="/", status_code=303)
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
    migrate_tutorial_column()
    migrate_registration_ip_column()
    print("[Auth] Module initialized")

async def tick(current_tick: int, now):
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
