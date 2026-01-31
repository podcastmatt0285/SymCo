"""
stats_ux.py - Standalone Stats & Leaderboard System

A plug-and-play stats dashboard that works WITHOUT requiring changes to existing files.
Just add the router to app.py and you're done!
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Cookie
from fastapi.responses import HTMLResponse
from sqlalchemy import create_engine, Column, String, Float, DateTime, Integer, desc, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./symco.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class PlayerStats(Base):
    __tablename__ = "player_stats_cache"

    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, unique=True, index=True, nullable=False)

    cash_balance = Column(Float, default=0.0)
    land_value = Column(Float, default=0.0)
    inventory_value = Column(Float, default=0.0)
    business_value = Column(Float, default=0.0)
    share_value = Column(Float, default=0.0)
    total_net_worth = Column(Float, default=0.0)

    lands_owned = Column(Integer, default=0)
    businesses_owned = Column(Integer, default=0)

    wealth_rank = Column(Integer, default=0)
    last_updated = Column(DateTime, default=datetime.utcnow)

router = APIRouter()

def get_db():
    return SessionLocal()

def calculate_player_stats(player_id: int) -> dict:
    db = get_db()
    try:
        from auth import Player
        player = db.query(Player).filter(Player.id == player_id).first()
        if not player:
            return None

        stats = {
            "cash_balance": player.cash_balance,
            "land_value": 0.0,
            "inventory_value": 0.0,
            "business_value": 0.0,
            "share_value": 0.0,
            "lands_owned": 0,
            "businesses_owned": 0
        }

        try:
            from land import LandPlot
            lands = db.query(LandPlot).filter(LandPlot.owner_id == player_id).all()
            stats["lands_owned"] = len(lands)
            stats["land_value"] = sum(plot.monthly_tax * 12 for plot in lands)
        except:
            pass

        try:
            from inventory import InventoryItem, get_item_info
            items = db.query(InventoryItem).filter(InventoryItem.player_id == player_id).all()
            inventory_val = 0.0
            for item in items:
                info = get_item_info(item.item_type)
                if info and item.quantity > 0:
                    inventory_val += item.quantity * info.get("base_price", 1.0)
            stats["inventory_value"] = inventory_val
        except:
            pass

        try:
            from business import Business
            businesses = db.query(Business).filter(
                Business.owner_id == player_id,
                Business.is_active == True
            ).all()
            stats["businesses_owned"] = len(businesses)
            stats["business_value"] = len(businesses) * 10000
        except:
            pass

        try:
            from banks.brokerage_firm import Holding
            from banks.brokerage_order_book import get_latest_price
            holdings = db.query(Holding).filter(Holding.player_id == player_id).all()
            share_val = 0.0
            for holding in holdings:
                share_val += holding.quantity * (get_latest_price(holding.stock_symbol) or 1.0)
            stats["share_value"] = share_val
        except:
            pass

        stats["total_net_worth"] = (
            stats["cash_balance"] +
            stats["land_value"] +
            stats["inventory_value"] +
            stats["business_value"] +
            stats["share_value"]
        )

        return stats
    finally:
        db.close()

def update_all_rankings():
    db = get_db()
    try:
        from auth import Player
        players = db.query(Player).all()
        ranked = []

        for p in players:
            stats = calculate_player_stats(p.id)
            if stats:
                ranked.append((p.id, stats["total_net_worth"]))

        ranked.sort(key=lambda x: x[1], reverse=True)

        for rank, (pid, _) in enumerate(ranked, 1):
            cached = db.query(PlayerStats).filter(PlayerStats.player_id == pid).first()
            if not cached:
                cached = PlayerStats(player_id=pid)
                db.add(cached)

            fresh = calculate_player_stats(pid)
            if fresh:
                cached.cash_balance = fresh["cash_balance"]
                cached.land_value = fresh["land_value"]
                cached.inventory_value = fresh["inventory_value"]
                cached.business_value = fresh["business_value"]
                cached.share_value = fresh["share_value"]
                cached.total_net_worth = fresh["total_net_worth"]
                cached.lands_owned = fresh["lands_owned"]
                cached.businesses_owned = fresh["businesses_owned"]
                cached.wealth_rank = rank
                cached.last_updated = datetime.utcnow()

        db.commit()
    finally:
        db.close()

@router.get("/api/stats/player")
async def get_player_stats(session_token: Optional[str] = Cookie(None)):
    from auth import get_player_from_session
    db = get_db()
    player = get_player_from_session(db, session_token)
    if not player:
        db.close()
        return {"error": "Not authenticated"}

    stats = calculate_player_stats(player.id)
    cached = db.query(PlayerStats).filter(PlayerStats.player_id == player.id).first()
    stats["wealth_rank"] = cached.wealth_rank if cached else 0
    db.close()
    return stats

@router.get("/api/stats/leaderboard")
async def get_leaderboard(limit: int = 10):
    db = get_db()
    update_all_rankings()
    top = db.query(PlayerStats).order_by(desc(PlayerStats.total_net_worth)).limit(limit).all()
    from auth import Player

    data = []
    for s in top:
        p = db.query(Player).filter(Player.id == s.player_id).first()
        if p:
            data.append({
                "rank": s.wealth_rank,
                "username": p.business_name,
                "net_worth": s.total_net_worth,
                "cash": s.cash_balance,
                "lands": s.lands_owned,
                "businesses": s.businesses_owned
            })
    db.close()
    return data

@router.get("/api/stats/economy")
async def get_economy_stats():
    db = get_db()
    from auth import Player
    total_players = db.query(Player).count()
    total_cash = db.query(func.sum(Player.cash_balance)).scalar() or 0.0

    try:
        from land import LandPlot
        total_plots = db.query(LandPlot).count()
        occupied_plots = db.query(LandPlot).filter(LandPlot.occupied_by_business_id != None).count()
    except:
        total_plots = occupied_plots = 0

    try:
        from business import Business
        total_businesses = db.query(Business).filter(Business.is_active == True).count()
    except:
        total_businesses = 0

    try:
        from market import MarketOrder
        active_orders = db.query(MarketOrder).filter(MarketOrder.status == "active").count()
    except:
        active_orders = 0

    db.close()
    return {
        "total_players": total_players,
        "total_money_supply": total_cash,
        "total_land_plots": total_plots,
        "occupied_plots": occupied_plots,
        "total_businesses": total_businesses,
        "active_market_orders": active_orders
    }

@router.get("/stats", response_class=HTMLResponse)
async def stats_page(session_token: Optional[str] = Cookie(None)):
    from auth import get_player_from_session
    db = get_db()
    player = get_player_from_session(db, session_token)
    db.close()

    if not player:
        return HTMLResponse("""
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body{margin:0;font-family:Inter,system-ui;background:#0f172a;color:#e5e7eb;display:flex;align-items:center;justify-content:center;height:100vh}
a{color:#38bdf8;text-decoration:none}
</style>
</head>
<body>
<div>
<h1>Login required</h1>
<a href="/login">Go to login</a>
</div>
</body>
</html>
""")

    return HTMLResponse("""
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root{
--bg:#0b1220;
--card:#111827;
--border:#1f2937;
--muted:#9ca3af;
--text:#e5e7eb;
--accent:#38bdf8;
}
body{
margin:0;
font-family:Inter,system-ui,-apple-system,BlinkMacSystemFont;
background:linear-gradient(180deg,#0b1220,#020617);
color:var(--text);
}
.header{
padding:32px 16px;
text-align:center;
}
.header h1{
margin:0;
font-size:2rem;
font-weight:700;
}
.header p{
margin-top:8px;
color:var(--muted);
}
.dashboard{
display:grid;
grid-template-columns:1fr;
gap:16px;
padding:16px;
max-width:1200px;
margin:auto;
}
@media(min-width:900px){
.dashboard{grid-template-columns:repeat(3,1fr)}
}
.card{
background:linear-gradient(180deg,#111827,#0b1220);
border:1px solid var(--border);
border-radius:16px;
padding:20px;
box-shadow:0 10px 30px rgba(0,0,0,.35);
}
.card h2{
margin:0 0 16px;
font-size:.8rem;
letter-spacing:.12em;
text-transform:uppercase;
color:var(--muted);
}
.stat-row{
display:flex;
justify-content:space-between;
padding:8px 0;
border-bottom:1px solid var(--border);
}
.stat-row:last-child{border-bottom:none}
.leaderboard-entry{
display:grid;
grid-template-columns:40px 1fr auto;
gap:12px;
align-items:center;
padding:10px 0;
border-bottom:1px solid var(--border);
}
.nav{
text-align:center;
padding:24px;
}
.nav a{
margin:0 12px;
color:var(--accent);
text-decoration:none;
font-weight:500;
}
.hero{
font-size:1.6rem;
font-weight:700;
margin-bottom:12px;
color:white;
}
</style>
</head>
<body>

<div class="header">
<h1>Economic Dashboard</h1>
<p>Live financial and ranking overview</p>
</div>

<div class="dashboard">
<div class="card">
<h2>Your Net Worth</h2>
<div id="player-stats">Loading…</div>
</div>

<div class="card">
<h2>Economy</h2>
<div id="economy-stats">Loading…</div>
</div>

<div class="card">
<h2>Leaderboard</h2>
<div id="leaderboard">Loading…</div>
</div>
</div>

<div class="nav">
<a href="/">Dashboard</a>
<a href="#" onclick="location.reload()">Refresh</a>
</div>

<script>
function money(v){return '$'+v.toFixed(2).replace(/\\B(?=(\\d{3})+(?!\\d))/g,',')}
function num(v){return v.toString().replace(/\\B(?=(\\d{3})+(?!\\d))/g,',')}

async function loadPlayerStats(){
const r=await fetch('/api/stats/player');const d=await r.json();
document.getElementById('player-stats').innerHTML=`
<div class="hero">${money(d.total_net_worth)}</div>
<div class="stat-row"><span>Cash</span><span>${money(d.cash_balance)}</span></div>
<div class="stat-row"><span>Land</span><span>${money(d.land_value)} (${d.lands_owned})</span></div>
<div class="stat-row"><span>Inventory</span><span>${money(d.inventory_value)}</span></div>
<div class="stat-row"><span>Businesses</span><span>${money(d.business_value)} (${d.businesses_owned})</span></div>
<div class="stat-row"><span>Shares</span><span>${money(d.share_value)}</span></div>
<div class="stat-row"><strong>Rank</strong><strong>#${d.wealth_rank}</strong></div>`;
}

async function loadEconomyStats(){
const r=await fetch('/api/stats/economy');const d=await r.json();
document.getElementById('economy-stats').innerHTML=`
<div class="stat-row"><span>Players</span><span>${num(d.total_players)}</span></div>
<div class="stat-row"><span>Money Supply</span><span>${money(d.total_money_supply)}</span></div>
<div class="stat-row"><span>Land Plots</span><span>${num(d.total_land_plots)}</span></div>
<div class="stat-row"><span>Occupied</span><span>${num(d.occupied_plots)}</span></div>
<div class="stat-row"><span>Businesses</span><span>${num(d.total_businesses)}</span></div>
<div class="stat-row"><span>Market Orders</span><span>${num(d.active_market_orders)}</span></div>`;
}

async function loadLeaderboard(){
const r=await fetch('/api/stats/leaderboard?limit=10');const d=await r.json();
document.getElementById('leaderboard').innerHTML=d.map(e=>`
<div class="leaderboard-entry">
<div>#${e.rank}</div>
<div>${e.username}</div>
<div>${money(e.net_worth)}</div>
</div>`).join('');
}

loadPlayerStats();
loadEconomyStats();
loadLeaderboard();
setInterval(()=>{loadPlayerStats();loadEconomyStats();loadLeaderboard()},30000);
</script>
</body>
</html>
""")

def initialize():
    Base.metadata.create_all(bind=engine)

async def tick(current_tick: int, now: datetime):
    if current_tick % 600 == 0:
        update_all_rankings()

def log_transaction(player_id:int,transaction_type:str,category:str,amount:float,description:str,reference_id:str=None):
    pass

__all__ = ["router","initialize","tick","PlayerStats","log_transaction"]
