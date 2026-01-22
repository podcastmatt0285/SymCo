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
from fastapi import APIRouter, Form, Cookie, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import create_engine, Column, String, Float, DateTime, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# ==========================
# DATABASE SETUP
# ==========================
DATABASE_URL = "sqlite:///./symco.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
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
def create_player(db: Session, business_name: str, password: str) -> Optional[Player]:
    """Create a new player account."""
    existing = db.query(Player).filter(Player.business_name == business_name).first()
    if existing:
        return None
    
    player = Player(
        business_name=business_name,
        password_hash=hash_password(password),
        cash_balance=50000.0
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
    <title>Login · SymCo</title>
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
            font-size: 48px;
            font-weight: 700;
            text-align: center;
            margin-bottom: 12px;
            letter-spacing: -0.03em;
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
        <div class="logo">SymCo</div>
        <div class="tagline">Real-Time Economic Simulation</div>

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
    
    player = create_player(db, business_name, password)
    
    if not player:
        db.close()
        return RedirectResponse(
            url="/login?error=Business%20name%20already%20exists",
            status_code=303
        )
    
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
