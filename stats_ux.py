"""
stats_ux.py - Comprehensive Stats & Analytics Dashboard

A full-featured analytics system providing:
- Global Economy Overview (total land, cash, stocks, businesses, districts)
- Personal Business Economy (inventory, shares, cash, recent transactions, cost averages)
- Leaderboard (sortable by category: cash, land, inventory, shares, total)
- Business & Item Information (production lines, recipes, terrain requirements, price charts)
- Transaction Logging (retail, production, market, banking)
- 7-day price trend charts for all items
"""

import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from fastapi import APIRouter, Cookie, Query
from fastapi.responses import HTMLResponse
from sqlalchemy import create_engine, Column, String, Float, DateTime, Integer, Boolean, desc, func, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./wadsworth.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ==========================
# DATABASE MODELS
# ==========================

class PlayerStats(Base):
    """Cached player statistics for leaderboard."""
    __tablename__ = "player_stats_cache"

    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, unique=True, index=True, nullable=False)

    cash_balance = Column(Float, default=0.0)
    land_value = Column(Float, default=0.0)
    inventory_value = Column(Float, default=0.0)
    business_value = Column(Float, default=0.0)
    share_value = Column(Float, default=0.0)
    district_value = Column(Float, default=0.0)
    total_net_worth = Column(Float, default=0.0)

    lands_owned = Column(Integer, default=0)
    businesses_owned = Column(Integer, default=0)
    districts_owned = Column(Integer, default=0)

    wealth_rank = Column(Integer, default=0)
    last_updated = Column(DateTime, default=datetime.utcnow)


class TransactionLog(Base):
    """Comprehensive transaction history for all economic activity."""
    __tablename__ = "transaction_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, index=True, nullable=False)
    
    # Transaction categorization
    transaction_type = Column(String, nullable=False)  # market_buy, market_sell, production, retail_sale, banking, dividend, tax
    category = Column(String, nullable=False)  # money, resource
    
    # Transaction details
    item_type = Column(String, index=True, nullable=True)  # Item involved (if applicable)
    quantity = Column(Float, default=0.0)  # Quantity of items
    amount = Column(Float, default=0.0)  # Cash amount (positive = gain, negative = loss)
    unit_price = Column(Float, nullable=True)  # Price per unit (for averaging)
    
    description = Column(String, nullable=True)
    reference_id = Column(String, nullable=True)  # Related order/business ID
    
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)


class PlayerCostAverage(Base):
    """Track average cost per item for each player."""
    __tablename__ = "player_cost_averages"
    
    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, index=True, nullable=False)
    item_type = Column(String, index=True, nullable=False)
    
    total_spent = Column(Float, default=0.0)  # Total cash spent on this item
    total_quantity = Column(Float, default=0.0)  # Total quantity acquired
    average_cost = Column(Float, default=0.0)  # Calculated average
    
    last_updated = Column(DateTime, default=datetime.utcnow)


class PriceSnapshot(Base):
    """Hourly price snapshots for charting."""
    __tablename__ = "price_snapshots"
    
    id = Column(Integer, primary_key=True, index=True)
    item_type = Column(String, index=True, nullable=False)
    
    price = Column(Float, nullable=False)
    volume = Column(Float, default=0.0)  # Trading volume in this period
    
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)


router = APIRouter()

def get_db():
    return SessionLocal()


# ==========================
# TRANSACTION LOGGING
# ==========================

def log_transaction(
    player_id: int,
    transaction_type: str,
    category: str,
    amount: float,
    description: str = None,
    reference_id: str = None,
    item_type: str = None,
    quantity: float = 0.0,
    unit_price: float = None
):
    """
    Log a transaction and update cost averages.
    
    Args:
        player_id: Player involved
        transaction_type: market_buy, market_sell, production, retail_sale, banking, dividend, tax
        category: money or resource
        amount: Cash amount (positive=gain, negative=loss)
        description: Human-readable description
        reference_id: Related order/business ID
        item_type: Item type (for resource transactions)
        quantity: Quantity of items
        unit_price: Price per unit
    """
    if player_id <= 0:  # Skip system accounts
        return
        
    db = get_db()
    try:
        # Create transaction log
        log = TransactionLog(
            player_id=player_id,
            transaction_type=transaction_type,
            category=category,
            item_type=item_type,
            quantity=quantity,
            amount=amount,
            unit_price=unit_price,
            description=description,
            reference_id=reference_id
        )
        db.add(log)
        
        # Update cost averages for purchases
        if item_type and quantity > 0 and amount < 0 and transaction_type in ['market_buy', 'cash_out']:
            update_cost_average(db, player_id, item_type, abs(amount), quantity)
        
        db.commit()
    except Exception as e:
        print(f"[Stats] Transaction log error: {e}")
        db.rollback()
    finally:
        db.close()


def update_cost_average(db, player_id: int, item_type: str, spent: float, quantity: float):
    """Update running cost average for a player's item."""
    avg = db.query(PlayerCostAverage).filter(
        PlayerCostAverage.player_id == player_id,
        PlayerCostAverage.item_type == item_type
    ).first()
    
    if not avg:
        avg = PlayerCostAverage(
            player_id=player_id,
            item_type=item_type,
            total_spent=0.0,
            total_quantity=0.0
        )
        db.add(avg)
    
    avg.total_spent += spent
    avg.total_quantity += quantity
    avg.average_cost = avg.total_spent / avg.total_quantity if avg.total_quantity > 0 else 0.0
    avg.last_updated = datetime.utcnow()


# ==========================
# STATS CALCULATION
# ==========================

def calculate_player_stats(player_id: int) -> dict:
    """Calculate comprehensive stats for a player."""
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
            "district_value": 0.0,
            "lands_owned": 0,
            "businesses_owned": 0,
            "districts_owned": 0
        }

        # Land value - use SQL aggregation instead of loading all plots
        try:
            from land import LandPlot
            from sqlalchemy import func as sqlfunc
            land_agg = db.query(
                sqlfunc.count(LandPlot.id),
                sqlfunc.coalesce(sqlfunc.sum(LandPlot.monthly_tax * 12), 0.0)
            ).filter(LandPlot.owner_id == player_id).first()
            stats["lands_owned"] = land_agg[0] or 0
            stats["land_value"] = land_agg[1] or 0.0
        except:
            pass

        # Inventory value
        try:
            from inventory import InventoryItem
            from market import get_market_price
            items = db.query(InventoryItem).filter(InventoryItem.player_id == player_id).all()
            inventory_val = 0.0
            for item in items:
                if item.quantity > 0:
                    price = get_market_price(item.item_type) or 1.0
                    inventory_val += item.quantity * price
            stats["inventory_value"] = inventory_val
        except:
            pass

        # Business value
        try:
            from business import Business, BUSINESS_TYPES
            businesses = db.query(Business).filter(
                Business.owner_id == player_id,
                Business.is_active == True
            ).all()
            stats["businesses_owned"] = len(businesses)
            biz_val = 0.0
            for biz in businesses:
                config = BUSINESS_TYPES.get(biz.business_type, {})
                biz_val += config.get("startup_cost", 10000)
            stats["business_value"] = biz_val
        except:
            pass

        # District value
        try:
            from districts import District, DISTRICT_TYPES
            districts = db.query(District).filter(District.owner_id == player_id).all()
            stats["districts_owned"] = len(districts)
            district_val = 0.0
            for d in districts:
                config = DISTRICT_TYPES.get(d.district_type, {})
                district_val += config.get("base_tax", 50000) * 12
            stats["district_value"] = district_val
        except:
            pass

        # Share value
        try:
            from banks.brokerage_firm import ShareholderPosition, CompanyShares
            positions = db.query(ShareholderPosition).filter(
                ShareholderPosition.player_id == player_id,
                ShareholderPosition.shares_owned > 0
            ).all()
            share_val = 0.0
            for pos in positions:
                company = db.query(CompanyShares).filter(CompanyShares.id == pos.company_shares_id).first()
                if company:
                    share_val += pos.shares_owned * company.current_price
            stats["share_value"] = share_val
        except:
            pass

        stats["total_net_worth"] = (
            stats["cash_balance"] +
            stats["land_value"] +
            stats["inventory_value"] +
            stats["business_value"] +
            stats["share_value"] +
            stats["district_value"]
        )

        return stats
    finally:
        db.close()


def update_all_rankings():
    """Update rankings for all players."""
    db = get_db()
    try:
        from auth import Player
        players = db.query(Player).all()
        ranked = []

        for p in players:
            stats = calculate_player_stats(p.id)
            if stats:
                ranked.append((p.id, stats))

        # Sort by total net worth
        ranked.sort(key=lambda x: x[1]["total_net_worth"], reverse=True)

        for rank, (pid, stats) in enumerate(ranked, 1):
            cached = db.query(PlayerStats).filter(PlayerStats.player_id == pid).first()
            if not cached:
                cached = PlayerStats(player_id=pid)
                db.add(cached)

            cached.cash_balance = stats["cash_balance"]
            cached.land_value = stats["land_value"]
            cached.inventory_value = stats["inventory_value"]
            cached.business_value = stats["business_value"]
            cached.share_value = stats["share_value"]
            cached.district_value = stats["district_value"]
            cached.total_net_worth = stats["total_net_worth"]
            cached.lands_owned = stats["lands_owned"]
            cached.businesses_owned = stats["businesses_owned"]
            cached.districts_owned = stats["districts_owned"]
            cached.wealth_rank = rank
            cached.last_updated = datetime.utcnow()

        db.commit()
    finally:
        db.close()


def record_price_snapshot(item_type: str, price: float, volume: float = 0.0):
    """Record a price snapshot for charting."""
    db = get_db()
    try:
        snapshot = PriceSnapshot(
            item_type=item_type,
            price=price,
            volume=volume
        )
        db.add(snapshot)
        db.commit()
    finally:
        db.close()


def get_price_history(item_type: str, days: int = 7) -> List[dict]:
    """Get price history for an item."""
    db = get_db()
    try:
        cutoff = datetime.utcnow() - timedelta(days=days)
        snapshots = db.query(PriceSnapshot).filter(
            PriceSnapshot.item_type == item_type,
            PriceSnapshot.timestamp >= cutoff
        ).order_by(PriceSnapshot.timestamp.asc()).all()
        
        return [{
            "timestamp": s.timestamp.isoformat(),
            "price": s.price,
            "volume": s.volume
        } for s in snapshots]
    finally:
        db.close()


# ==========================
# HTML SHELL
# ==========================

def stats_shell(title: str, body: str, balance: float = 0.0, player_name: str = "") -> str:
    """Render the stats dashboard shell."""
    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>{title} · Wadsworth Analytics</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            background: #020617;
            color: #e5e7eb;
            font-family: 'JetBrains Mono', 'Courier New', monospace;
            margin: 0;
            padding: 0;
            font-size: 14px;
        }}
        a {{ color: #38bdf8; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        
        .header {{
            border-bottom: 1px solid #1e293b;
            padding: 12px 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: #0f172a;
        }}
        .brand {{ font-weight: bold; color: #38bdf8; font-size: 1.1rem; }}
        .header-right {{
            display: flex;
            align-items: center;
            gap: 16px;
        }}
        .balance {{ color: #22c55e; font-weight: 600; }}
        
        .nav {{
            background: #0f172a;
            border-bottom: 1px solid #1e293b;
            padding: 8px 16px;
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }}
        .nav a {{
            padding: 6px 12px;
            border-radius: 4px;
            background: #1e293b;
            color: #94a3b8;
            font-size: 0.85rem;
        }}
        .nav a:hover, .nav a.active {{
            background: #38bdf8;
            color: #020617;
            text-decoration: none;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px 16px;
        }}
        
        .page-title {{
            font-size: 1.5rem;
            font-weight: 700;
            margin-bottom: 20px;
            color: #f1f5f9;
        }}
        
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 16px;
        }}
        
        .card {{
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 20px;
            cursor: pointer;
            transition: all 0.2s ease;
        }}
        .card:hover {{
            border-color: #38bdf8;
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(56, 189, 248, 0.15);
        }}
        .card-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }}
        .card-title {{
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: #94a3b8;
        }}
        .card-icon {{
            font-size: 1.5rem;
        }}
        .card-value {{
            font-size: 1.75rem;
            font-weight: 700;
            color: #f1f5f9;
            margin-bottom: 8px;
        }}
        .card-subtitle {{
            font-size: 0.8rem;
            color: #64748b;
        }}
        
        .stat-row {{
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #1e293b;
        }}
        .stat-row:last-child {{ border-bottom: none; }}
        .stat-label {{ color: #94a3b8; }}
        .stat-value {{ color: #f1f5f9; font-weight: 500; }}
        .stat-value.positive {{ color: #22c55e; }}
        .stat-value.negative {{ color: #ef4444; }}
        
        .table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.85rem;
        }}
        .table th {{
            text-align: left;
            padding: 12px 8px;
            border-bottom: 2px solid #334155;
            color: #94a3b8;
            font-weight: 500;
            cursor: pointer;
        }}
        .table th:hover {{ color: #38bdf8; }}
        .table td {{
            padding: 10px 8px;
            border-bottom: 1px solid #1e293b;
        }}
        .table tr:hover {{ background: #1e293b; }}
        
        .badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.7rem;
            font-weight: 600;
        }}
        .badge-gold {{ background: #d4af37; color: #000; }}
        .badge-silver {{ background: #c0c0c0; color: #000; }}
        .badge-bronze {{ background: #cd7f32; color: #000; }}
        .badge-blue {{ background: #38bdf8; color: #020617; }}
        .badge-green {{ background: #22c55e; color: #020617; }}
        .badge-gray {{ background: #475569; color: #e5e7eb; }}
        
        .search-box {{
            width: 100%;
            padding: 10px 14px;
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 6px;
            color: #e5e7eb;
            font-size: 0.9rem;
            margin-bottom: 16px;
        }}
        .search-box:focus {{
            outline: none;
            border-color: #38bdf8;
        }}
        
        .filter-tabs {{
            display: flex;
            gap: 8px;
            margin-bottom: 16px;
            flex-wrap: wrap;
        }}
        .filter-tab {{
            padding: 6px 12px;
            border-radius: 4px;
            background: #1e293b;
            color: #94a3b8;
            cursor: pointer;
            font-size: 0.8rem;
            border: none;
        }}
        .filter-tab:hover, .filter-tab.active {{
            background: #38bdf8;
            color: #020617;
        }}
        
        .transaction-item {{
            display: grid;
            grid-template-columns: 1fr auto auto;
            gap: 12px;
            padding: 12px;
            border-bottom: 1px solid #1e293b;
            align-items: center;
        }}
        .transaction-item:hover {{ background: #1e293b; }}
        .transaction-desc {{ color: #e5e7eb; }}
        .transaction-time {{ color: #64748b; font-size: 0.75rem; }}
        .transaction-amount {{ font-weight: 600; }}
        
        .chart-container {{
            background: #0f172a;
            border: 1px solid #1e293b;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 16px;
        }}
        .mini-chart {{
            height: 60px;
            display: flex;
            align-items: flex-end;
            gap: 2px;
        }}
        .mini-chart-bar {{
            flex: 1;
            background: linear-gradient(to top, #38bdf8, #0ea5e9);
            border-radius: 2px 2px 0 0;
            min-height: 4px;
        }}
        
        .detail-section {{
            margin-bottom: 24px;
        }}
        .detail-title {{
            font-size: 1rem;
            font-weight: 600;
            margin-bottom: 12px;
            color: #f1f5f9;
        }}
        
        .recipe-item {{
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 6px 0;
        }}
        .recipe-arrow {{ color: #38bdf8; }}
        
        .terrain-tag {{
            display: inline-block;
            padding: 2px 6px;
            background: #1e293b;
            border-radius: 3px;
            font-size: 0.7rem;
            margin: 2px;
            color: #94a3b8;
        }}
        
        @media (max-width: 640px) {{
            .grid {{ grid-template-columns: 1fr; }}
            .card-value {{ font-size: 1.4rem; }}
            .table {{ font-size: 0.75rem; }}
            .table th, .table td {{ padding: 8px 4px; }}
            .header {{ flex-direction: column; gap: 8px; text-align: center; }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="brand">Wadsworth Analytics</div>
        <div class="header-right">
            <span style="color: #94a3b8;">{player_name}</span>
            <span class="balance">${balance:,.2f}</span>
            <a href="/" style="color: #94a3b8;">← Dashboard</a>
        </div>
    </div>
    
    <div class="nav">
        <a href="/stats">Overview</a>
        <a href="/stats/economy">Economy</a>
        <a href="/stats/personal">My Business</a>
        <a href="/stats/leaderboard">Leaderboard</a>
        <a href="/stats/businesses">Businesses</a>
        <a href="/stats/districts">Districts</a>
        <a href="/stats/items">Items</a>
        <a href="/stats/production-costs">Costs</a>
    </div>
    
    <div class="container">
        {body}
    </div>
    
    <script>
        function money(v) {{ return '$' + v.toFixed(2).replace(/\\B(?=(\\d{{3}})+(?!\\d))/g, ','); }}
        function num(v) {{ return v.toString().replace(/\\B(?=(\\d{{3}})+(?!\\d))/g, ','); }}
        
        function filterTx(type) {{
            const items = document.querySelectorAll('.transaction-item');
            const tabs = document.querySelectorAll('#transactions').length ? 
                document.querySelectorAll('.filter-tabs .filter-tab') : [];
            
            // Update active tab
            tabs.forEach(tab => {{
                tab.classList.remove('active');
                if (tab.textContent.toLowerCase().replace(/\\s+/g, '') === type || 
                    (type === 'all' && tab.textContent === 'All')) {{
                    tab.classList.add('active');
                }}
            }});
            if (event && event.target) event.target.classList.add('active');
            
            items.forEach(item => {{
                const badge = item.querySelector('.badge');
                const txType = badge ? badge.textContent.toLowerCase() : '';
                const desc = item.querySelector('.transaction-desc');
                const descText = desc ? desc.textContent.toLowerCase() : '';
                
                let show = false;
                
                if (type === 'all') {{
                    show = true;
                }} else if (type === 'market') {{
                    show = txType.includes('market') || txType.includes('cash_in') || txType.includes('cash_out');
                }} else if (type === 'production') {{
                    show = txType.includes('production');
                }} else if (type === 'retail') {{
                    show = txType.includes('retail') || txType.includes('sale');
                }} else if (type === 'banking') {{
                    show = txType.includes('banking') || txType.includes('dividend') || 
                           txType.includes('interest') || txType.includes('loan') ||
                           descText.includes('bank') || descText.includes('dividend');
                }} else if (type === 'district') {{
                    show = txType.includes('district') || txType.includes('merge') ||
                           descText.includes('district');
                }} else if (type === 'city') {{
                    show = txType.includes('city') || txType.includes('subsidy') || 
                           txType.includes('poll') || descText.includes('city');
                }} else if (type === 'tax') {{
                    show = txType.includes('tax') || descText.includes('tax');
                }} else {{
                    show = txType.includes(type) || descText.includes(type);
                }}
                
                item.style.display = show ? 'grid' : 'none';
            }});
        }}
    </script>
</body>
</html>
"""


# ==========================
# API ENDPOINTS
# ==========================

@router.get("/api/stats/player")
async def get_player_stats_api(session_token: Optional[str] = Cookie(None)):
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
async def get_leaderboard_api(
    sort_by: str = Query("total_net_worth", enum=["total_net_worth", "cash_balance", "land_value", "inventory_value", "share_value", "business_value"]),
    limit: int = 10
):
    db = get_db()
    update_all_rankings()
    
    sort_column = getattr(PlayerStats, sort_by)
    top = db.query(PlayerStats).order_by(desc(sort_column)).limit(limit).all()
    
    from auth import Player
    data = []
    for rank, s in enumerate(top, 1):
        p = db.query(Player).filter(Player.id == s.player_id).first()
        if p:
            data.append({
                "rank": rank,
                "username": p.business_name,
                "total_net_worth": s.total_net_worth,
                "cash": s.cash_balance,
                "land": s.land_value,
                "inventory": s.inventory_value,
                "shares": s.share_value,
                "businesses": s.businesses_owned,
                "lands": s.lands_owned,
                "districts": s.districts_owned
            })
    db.close()
    return data


@router.get("/api/stats/economy")
async def get_economy_stats_api():
    db = get_db()
    from auth import Player
    
    stats = {
        "total_players": db.query(Player).count(),
        "total_cash": db.query(func.sum(Player.cash_balance)).scalar() or 0.0,
        "total_plots": 0,
        "occupied_plots": 0,
        "total_businesses": 0,
        "active_businesses": 0,
        "total_districts": 0,
        "total_market_orders": 0,
        "market_volume_24h": 0.0,
        "total_companies": 0
    }
    
    try:
        from land import LandPlot
        stats["total_plots"] = db.query(LandPlot).count()
        stats["occupied_plots"] = db.query(LandPlot).filter(LandPlot.occupied_by_business_id != None).count()
    except: pass
    
    try:
        from business import Business
        stats["total_businesses"] = db.query(Business).count()
        stats["active_businesses"] = db.query(Business).filter(Business.is_active == True).count()
    except: pass
    
    try:
        from districts import District
        stats["total_districts"] = db.query(District).count()
    except: pass
    
    try:
        from market import MarketOrder, Trade
        stats["total_market_orders"] = db.query(MarketOrder).filter(MarketOrder.status == "active").count()
        yesterday = datetime.utcnow() - timedelta(days=1)
        trades = db.query(Trade).filter(Trade.executed_at >= yesterday).all()
        stats["market_volume_24h"] = sum(t.quantity * t.price for t in trades)
    except: pass
    
    try:
        from banks.brokerage_firm import CompanyShares
        stats["total_companies"] = db.query(CompanyShares).filter(CompanyShares.is_delisted == False).count()
    except: pass
    
    db.close()
    return stats


@router.get("/api/stats/transactions")
async def get_transactions_api(
    session_token: Optional[str] = Cookie(None),
    limit: int = 50,
    tx_type: Optional[str] = None
):
    from auth import get_player_from_session
    db = get_db()
    player = get_player_from_session(db, session_token)
    if not player:
        db.close()
        return {"error": "Not authenticated"}
    
    query = db.query(TransactionLog).filter(TransactionLog.player_id == player.id)
    if tx_type:
        query = query.filter(TransactionLog.transaction_type == tx_type)
    
    txs = query.order_by(desc(TransactionLog.timestamp)).limit(limit).all()
    
    data = [{
        "id": tx.id,
        "type": tx.transaction_type,
        "category": tx.category,
        "item": tx.item_type,
        "quantity": tx.quantity,
        "amount": tx.amount,
        "description": tx.description,
        "timestamp": tx.timestamp.isoformat()
    } for tx in txs]
    
    db.close()
    return {"transactions": data}


@router.get("/api/stats/cost-averages")
async def get_cost_averages_api(session_token: Optional[str] = Cookie(None)):
    from auth import get_player_from_session
    db = get_db()
    player = get_player_from_session(db, session_token)
    if not player:
        db.close()
        return {"error": "Not authenticated"}
    
    averages = db.query(PlayerCostAverage).filter(
        PlayerCostAverage.player_id == player.id,
        PlayerCostAverage.total_quantity > 0
    ).all()
    
    data = [{
        "item": avg.item_type,
        "total_spent": avg.total_spent,
        "total_quantity": avg.total_quantity,
        "average_cost": avg.average_cost
    } for avg in averages]
    
    db.close()
    return {"averages": data}


@router.get("/api/stats/price-history/{item_type}")
async def get_price_history_api(item_type: str, days: int = 7):
    return {"item": item_type, "history": get_price_history(item_type, days)}


# ==========================
# HTML PAGES
# ==========================

@router.get("/stats", response_class=HTMLResponse)
async def stats_overview(session_token: Optional[str] = Cookie(None)):
    """Main stats dashboard with card navigation."""
    from auth import get_player_from_session
    db = get_db()
    player = get_player_from_session(db, session_token)
    db.close()

    if not player:
        return HTMLResponse("""
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1">
<style>body{margin:0;font-family:monospace;background:#020617;color:#e5e7eb;display:flex;align-items:center;justify-content:center;height:100vh}a{color:#38bdf8}</style>
</head><body><div><h1>Login Required</h1><a href="/login">Go to Login</a></div></body></html>
""")

    stats = calculate_player_stats(player.id)
    
    body = f"""
    <h1 class="page-title">Analytics Dashboard</h1>
    
    <div class="grid">
        <a href="/stats/economy" class="card" style="text-decoration: none;">
            <div class="card-header">
                <span class="card-title">Global Economy</span>
                <span class="card-icon">🌐</span>
            </div>
            <div class="card-value">Overview</div>
            <div class="card-subtitle">Total land, cash, businesses, districts, market activity</div>
        </a>
        
        <a href="/stats/personal" class="card" style="text-decoration: none;">
            <div class="card-header">
                <span class="card-title">Your Business</span>
                <span class="card-icon">💼</span>
            </div>
            <div class="card-value">${stats['total_net_worth']:,.0f}</div>
            <div class="card-subtitle">Net worth, transactions, cost averages</div>
        </a>
        
        <a href="/stats/leaderboard" class="card" style="text-decoration: none;">
            <div class="card-header">
                <span class="card-title">Leaderboard</span>
                <span class="card-icon">🏆</span>
            </div>
            <div class="card-value">Rankings</div>
            <div class="card-subtitle">Top players by category</div>
        </a>
        
        <a href="/stats/businesses" class="card" style="text-decoration: none;">
            <div class="card-header">
                <span class="card-title">Business Encyclopedia</span>
                <span class="card-icon">🏭</span>
            </div>
            <div class="card-value">Production</div>
            <div class="card-subtitle">All businesses, recipes, terrain requirements</div>
        </a>
        
        <a href="/stats/items" class="card" style="text-decoration: none;">
            <div class="card-header">
                <span class="card-title">Item Catalog</span>
                <span class="card-icon">📦</span>
            </div>
            <div class="card-value">Market Data</div>
            <div class="card-subtitle">All items, price charts, categories</div>
        </a>

        <a href="/stats/production-costs" class="card" style="text-decoration: none;">
            <div class="card-header">
                <span class="card-title">Production Costs</span>
                <span class="card-icon">💰</span>
            </div>
            <div class="card-value">Cost Guide</div>
            <div class="card-subtitle">Cheapest recipes for every item including district items</div>
        </a>

        <a href="/stats/districts" class="card" style="text-decoration: none;">
            <div class="card-header">
                <span class="card-title">Districts</span>
                <span class="card-icon">🏙️</span>
            </div>
            <div class="card-value">Encyclopedia</div>
            <div class="card-subtitle">All district types, terrain rules, taxes, businesses</div>
        </a>
    </div>
    
    <div style="margin-top: 32px;">
        <h2 style="font-size: 1rem; color: #94a3b8; margin-bottom: 16px;">Quick Stats</h2>
        <div class="grid">
            <div class="card" style="cursor: default;">
                <div class="stat-row"><span class="stat-label">Cash</span><span class="stat-value">${stats['cash_balance']:,.2f}</span></div>
                <div class="stat-row"><span class="stat-label">Land Value</span><span class="stat-value">${stats['land_value']:,.2f}</span></div>
                <div class="stat-row"><span class="stat-label">Inventory</span><span class="stat-value">${stats['inventory_value']:,.2f}</span></div>
            </div>
            <div class="card" style="cursor: default;">
                <div class="stat-row"><span class="stat-label">Business Value</span><span class="stat-value">${stats['business_value']:,.2f}</span></div>
                <div class="stat-row"><span class="stat-label">Share Value</span><span class="stat-value">${stats['share_value']:,.2f}</span></div>
                <div class="stat-row"><span class="stat-label">District Value</span><span class="stat-value">${stats['district_value']:,.2f}</span></div>
            </div>
        </div>
    </div>
    """
    
    return HTMLResponse(stats_shell("Dashboard", body, player.cash_balance, player.business_name))


@router.get("/stats/economy", response_class=HTMLResponse)
async def stats_economy(session_token: Optional[str] = Cookie(None)):
    """Global economy overview."""
    from auth import get_player_from_session
    db = get_db()
    player = get_player_from_session(db, session_token)
    if not player:
        db.close()
        return HTMLResponse('<meta http-equiv="refresh" content="0;url=/login">')
    
    from auth import Player
    
    # Gather economy stats
    total_players = db.query(Player).count()
    total_cash = db.query(func.sum(Player.cash_balance)).scalar() or 0.0
    
    total_plots = occupied_plots = 0
    try:
        from land import LandPlot
        total_plots = db.query(LandPlot).count()
        occupied_plots = db.query(LandPlot).filter(LandPlot.occupied_by_business_id != None).count()
    except: pass
    
    total_businesses = active_businesses = 0
    try:
        from business import Business
        total_businesses = db.query(Business).count()
        active_businesses = db.query(Business).filter(Business.is_active == True).count()
    except: pass
    
    total_districts = 0
    try:
        from districts import District
        total_districts = db.query(District).count()
    except: pass
    
    active_orders = market_volume = 0
    try:
        from market import MarketOrder, Trade
        active_orders = db.query(MarketOrder).filter(MarketOrder.status == "active").count()
        yesterday = datetime.utcnow() - timedelta(days=1)
        trades = db.query(Trade).filter(Trade.executed_at >= yesterday).all()
        market_volume = sum(t.quantity * t.price for t in trades)
    except: pass
    
    total_companies = 0
    try:
        from banks.brokerage_firm import CompanyShares
        total_companies = db.query(CompanyShares).filter(CompanyShares.is_delisted == False).count()
    except: pass
    
    db.close()
    
    body = f"""
    <h1 class="page-title">🌐 Global Economy</h1>
    
    <div class="grid">
        <div class="card" style="cursor: default;">
            <div class="card-header">
                <span class="card-title">Players & Money</span>
                <span class="card-icon">👥</span>
            </div>
            <div class="stat-row"><span class="stat-label">Total Players</span><span class="stat-value">{total_players:,}</span></div>
            <div class="stat-row"><span class="stat-label">Total Money Supply</span><span class="stat-value">${total_cash:,.0f}</span></div>
            <div class="stat-row"><span class="stat-label">Avg per Player</span><span class="stat-value">${total_cash/max(total_players,1):,.0f}</span></div>
        </div>
        
        <div class="card" style="cursor: default;">
            <div class="card-header">
                <span class="card-title">Land</span>
                <span class="card-icon">🏞️</span>
            </div>
            <div class="stat-row"><span class="stat-label">Total Plots</span><span class="stat-value">{total_plots:,}</span></div>
            <div class="stat-row"><span class="stat-label">Occupied</span><span class="stat-value">{occupied_plots:,}</span></div>
            <div class="stat-row"><span class="stat-label">Occupancy Rate</span><span class="stat-value">{occupied_plots/max(total_plots,1)*100:.1f}%</span></div>
        </div>
        
        <div class="card" style="cursor: default;">
            <div class="card-header">
                <span class="card-title">Businesses</span>
                <span class="card-icon">🏭</span>
            </div>
            <div class="stat-row"><span class="stat-label">Total Businesses</span><span class="stat-value">{total_businesses:,}</span></div>
            <div class="stat-row"><span class="stat-label">Active</span><span class="stat-value">{active_businesses:,}</span></div>
            <div class="stat-row"><span class="stat-label">Districts</span><span class="stat-value">{total_districts:,}</span></div>
        </div>
        
        <div class="card" style="cursor: default;">
            <div class="card-header">
                <span class="card-title">Markets</span>
                <span class="card-icon">📈</span>
            </div>
            <div class="stat-row"><span class="stat-label">Active Orders</span><span class="stat-value">{active_orders:,}</span></div>
            <div class="stat-row"><span class="stat-label">24h Volume</span><span class="stat-value">${market_volume:,.0f}</span></div>
            <div class="stat-row"><span class="stat-label">Listed Companies</span><span class="stat-value">{total_companies:,}</span></div>
        </div>
    </div>
    """
    
    return HTMLResponse(stats_shell("Economy", body, player.cash_balance, player.business_name))


@router.get("/stats/personal", response_class=HTMLResponse)
async def stats_personal(session_token: Optional[str] = Cookie(None)):
    """Personal business economy dashboard."""
    from auth import get_player_from_session
    db = get_db()
    player = get_player_from_session(db, session_token)
    if not player:
        db.close()
        return HTMLResponse('<meta http-equiv="refresh" content="0;url=/login">')
    
    stats = calculate_player_stats(player.id)
    
    # Get recent transactions
    txs = db.query(TransactionLog).filter(
        TransactionLog.player_id == player.id
    ).order_by(desc(TransactionLog.timestamp)).limit(200).all()
    
    # Get cost averages
    averages = db.query(PlayerCostAverage).filter(
        PlayerCostAverage.player_id == player.id,
        PlayerCostAverage.total_quantity > 0
    ).order_by(desc(PlayerCostAverage.total_spent)).limit(200).all()
    
    db.close()
    
    # Build transactions HTML
    TYPE_ICONS = {
        "market_buy": "🛒", "market_sell": "💰", "production": "🏭", "retail_sale": "🏪",
        "banking": "🏦", "dividend": "💸", "tax": "📋", "land": "🏗️", "crypto": "₿",
        "lien": "⚠️", "corporate": "📊", "inheritance": "📜", "city": "🏙️",
        "cash_in": "💵", "cash_out": "💸",
    }
    TYPE_BADGE_COLORS = {
        "market_buy": "#3b82f6", "market_sell": "#3b82f6",
        "production": "#8b5cf6", "retail_sale": "#8b5cf6",
        "banking": "#06b6d4", "dividend": "#22c55e",
        "tax": "#f97316", "land": "#84cc16",
        "crypto": "#f59e0b", "lien": "#ef4444",
        "corporate": "#64748b", "inheritance": "#a78bfa",
        "city": "#38bdf8",
    }

    total_income = sum(tx.amount for tx in txs if tx.amount > 0)
    total_expenses = sum(tx.amount for tx in txs if tx.amount < 0)
    net = total_income + total_expenses

    tx_html = ""
    for tx in txs:
        amount_class = "positive" if tx.amount > 0 else "negative"
        amount_str = f"+${tx.amount:,.2f}" if tx.amount > 0 else f"-${abs(tx.amount):,.2f}"
        border_color = "#22c55e" if tx.amount > 0 else "#ef4444"
        tx_type = tx.transaction_type or ""
        icon = next((v for k, v in TYPE_ICONS.items() if k in tx_type), "📝")
        badge_color = next((v for k, v in TYPE_BADGE_COLORS.items() if k in tx_type), "#475569")
        desc_full = tx.description or tx_type
        desc_short = (desc_full[:60] + "…") if len(desc_full) > 60 else desc_full
        item_line = ""
        if getattr(tx, "item_type", None):
            qty = getattr(tx, "quantity", None)
            unit_price = getattr(tx, "unit_price", None)
            parts = [tx.item_type]
            if qty is not None:
                parts.append(f"× {qty:,.2f}")
            if unit_price is not None:
                parts.append(f"@ ${unit_price:,.4f}")
            item_line = f'<div style="font-size:0.78rem;color:#94a3b8;margin-top:2px;">{" ".join(parts)}</div>'
        tx_html += f"""
        <div class="transaction-item" data-type="{tx_type}" data-desc="{desc_full.lower()}" style="border-left:3px solid {border_color};padding-left:10px;">
            <div style="display:flex;align-items:flex-start;gap:8px;flex:1;min-width:0;">
                <span style="font-size:1.1rem;">{icon}</span>
                <div style="flex:1;min-width:0;">
                    <div class="transaction-desc">{desc_short}</div>
                    {item_line}
                    <div class="transaction-time">{tx.timestamp.strftime('%Y-%m-%d %H:%M')}</div>
                </div>
            </div>
            <div style="display:flex;align-items:center;gap:8px;flex-shrink:0;">
                <span class="badge" style="background:{badge_color};color:#fff;">{tx_type}</span>
                <span class="transaction-amount {amount_class}">{amount_str}</span>
            </div>
        </div>
        """
    
    # Build cost averages HTML
    avg_html = ""
    for avg in averages:
        avg_html += f"""
        <div class="stat-row">
            <span class="stat-label">{avg.item_type.replace('_', ' ').title()}</span>
            <span class="stat-value">${avg.average_cost:.2f}/unit ({avg.total_quantity:,.0f} total)</span>
        </div>
        """
    
    body = f"""
    <h1 class="page-title">💼 Your Business Economy</h1>
    
    <div class="grid">
        <div class="card" style="cursor: default;">
            <div class="card-header">
                <span class="card-title">Net Worth Breakdown</span>
                <span class="card-icon">💰</span>
            </div>
            <div class="card-value">${stats['total_net_worth']:,.2f}</div>
            <div class="stat-row"><span class="stat-label">Cash</span><span class="stat-value">${stats['cash_balance']:,.2f}</span></div>
            <div class="stat-row"><span class="stat-label">Inventory</span><span class="stat-value">${stats['inventory_value']:,.2f}</span></div>
            <div class="stat-row"><span class="stat-label">Land ({stats['lands_owned']})</span><span class="stat-value">${stats['land_value']:,.2f}</span></div>
            <div class="stat-row"><span class="stat-label">Businesses ({stats['businesses_owned']})</span><span class="stat-value">${stats['business_value']:,.2f}</span></div>
            <div class="stat-row"><span class="stat-label">Shares</span><span class="stat-value">${stats['share_value']:,.2f}</span></div>
            <div class="stat-row"><span class="stat-label">Districts ({stats['districts_owned']})</span><span class="stat-value">${stats['district_value']:,.2f}</span></div>
        </div>
        
        <div class="card" style="cursor: default;">
            <div class="card-header">
                <span class="card-title">Cost Averages</span>
                <span class="card-icon">📊</span>
            </div>
            {avg_html if avg_html else '<div class="stat-row"><span class="stat-label">No purchase history yet</span></div>'}
        </div>
    </div>
    
    <div style="margin-top: 24px;">
        <div class="card" style="cursor: default;">
            <div class="card-header">
                <span class="card-title">Recent Transactions</span>
                <span class="card-icon">📝</span>
            </div>
            <div style="display:flex;gap:16px;flex-wrap:wrap;margin:12px 0;padding:10px;background:#0f172a;border-radius:6px;">
                <div><span style="color:#64748b;font-size:0.8rem;">Income</span><br><span style="color:#22c55e;font-weight:bold;">+${total_income:,.2f}</span></div>
                <div><span style="color:#64748b;font-size:0.8rem;">Expenses</span><br><span style="color:#ef4444;font-weight:bold;">${total_expenses:,.2f}</span></div>
                <div><span style="color:#64748b;font-size:0.8rem;">Net</span><br><span style="color:{"#22c55e" if net >= 0 else "#ef4444"};font-weight:bold;">${net:+,.2f}</span></div>
            </div>
            <div style="margin-bottom:10px;">
                <input type="text" id="tx-search" placeholder="Search transactions…" oninput="searchTx(this.value)" style="width:100%;padding:7px 10px;background:#0f172a;border:1px solid #1e293b;color:#f1f5f9;border-radius:4px;font-size:0.85rem;box-sizing:border-box;">
            </div>
            <div class="filter-tabs" style="margin-bottom: 12px; flex-wrap: wrap;">
                <button class="filter-tab active" onclick="filterTx('all',this)">All</button>
                <button class="filter-tab" onclick="filterTx('market_buy',this)">Market Buy</button>
                <button class="filter-tab" onclick="filterTx('market_sell',this)">Market Sell</button>
                <button class="filter-tab" onclick="filterTx('production',this)">Production</button>
                <button class="filter-tab" onclick="filterTx('retail',this)">Retail</button>
                <button class="filter-tab" onclick="filterTx('banking',this)">Banking</button>
                <button class="filter-tab" onclick="filterTx('dividend',this)">Dividend</button>
                <button class="filter-tab" onclick="filterTx('tax',this)">Tax</button>
                <button class="filter-tab" onclick="filterTx('land',this)">Land</button>
                <button class="filter-tab" onclick="filterTx('crypto',this)">Crypto</button>
                <button class="filter-tab" onclick="filterTx('lien',this)">Lien</button>
                <button class="filter-tab" onclick="filterTx('corporate',this)">Corporate</button>
                <button class="filter-tab" onclick="filterTx('inheritance',this)">Inheritance</button>
                <button class="filter-tab" onclick="filterTx('city',this)">City/County</button>
            </div>
            <div id="transactions">
                {tx_html if tx_html else '<div style="padding: 20px; text-align: center; color: #64748b;">No transactions yet</div>'}
            </div>
        </div>
    </div>
    <script>
    var _txFilter = 'all';
    var _txSearch = '';
    function filterTx(type, btn) {{
        _txFilter = type;
        document.querySelectorAll('.filter-tab').forEach(function(b){{ b.classList.remove('active'); }});
        if(btn) btn.classList.add('active');
        _applyTxFilters();
    }}
    function searchTx(val) {{
        _txSearch = val.toLowerCase();
        _applyTxFilters();
    }}
    function _applyTxFilters() {{
        document.querySelectorAll('.transaction-item').forEach(function(el){{
            var typeMatch = _txFilter === 'all' || (el.dataset.type || '').indexOf(_txFilter) !== -1;
            var searchMatch = !_txSearch || (el.dataset.desc || '').indexOf(_txSearch) !== -1;
            el.style.display = (typeMatch && searchMatch) ? '' : 'none';
        }});
    }}
    </script>
    """
    
    return HTMLResponse(stats_shell("My Business", body, player.cash_balance, player.business_name))


@router.get("/stats/leaderboard", response_class=HTMLResponse)
async def stats_leaderboard(
    session_token: Optional[str] = Cookie(None),
    sort: str = Query("total_net_worth")
):
    """Leaderboard with sortable columns."""
    from auth import get_player_from_session, Player
    db = get_db()
    player = get_player_from_session(db, session_token)
    if not player:
        db.close()
        return HTMLResponse('<meta http-equiv="refresh" content="0;url=/login">')
    
    update_all_rankings()
    
    valid_sorts = ["total_net_worth", "cash_balance", "land_value", "inventory_value", "share_value", "business_value"]
    if sort not in valid_sorts:
        sort = "total_net_worth"
    
    sort_column = getattr(PlayerStats, sort)
    top = db.query(PlayerStats).order_by(desc(sort_column)).limit(50).all()
    
    rows_html = ""
    for rank, s in enumerate(top, 1):
        p = db.query(Player).filter(Player.id == s.player_id).first()
        if not p:
            continue
        
        badge = ""
        if rank == 1:
            badge = '<span class="badge badge-gold">1st</span>'
        elif rank == 2:
            badge = '<span class="badge badge-silver">2nd</span>'
        elif rank == 3:
            badge = '<span class="badge badge-bronze">3rd</span>'
        
        highlight = 'style="background: #1e293b;"' if p.id == player.id else ""
        
        rows_html += f"""
        <tr {highlight}>
            <td>{badge or rank}</td>
            <td>{p.business_name}</td>
            <td>${s.total_net_worth:,.0f}</td>
            <td>${s.cash_balance:,.0f}</td>
            <td>${s.land_value:,.0f}</td>
            <td>${s.inventory_value:,.0f}</td>
            <td>${s.share_value:,.0f}</td>
            <td>{s.businesses_owned}</td>
        </tr>
        """
    
    db.close()
    
    def sort_link(field, label):
        active = 'style="color: #38bdf8; font-weight: 700;"' if sort == field else ""
        return f'<th {active}><a href="/stats/leaderboard?sort={field}" style="color: inherit;">{label}</a></th>'
    
    body = f"""
    <h1 class="page-title">🏆 Leaderboard</h1>
    
    <div class="filter-tabs">
        <a href="/stats/leaderboard?sort=total_net_worth" class="filter-tab {'active' if sort == 'total_net_worth' else ''}">Net Worth</a>
        <a href="/stats/leaderboard?sort=cash_balance" class="filter-tab {'active' if sort == 'cash_balance' else ''}">Cash</a>
        <a href="/stats/leaderboard?sort=land_value" class="filter-tab {'active' if sort == 'land_value' else ''}">Land</a>
        <a href="/stats/leaderboard?sort=inventory_value" class="filter-tab {'active' if sort == 'inventory_value' else ''}">Inventory</a>
        <a href="/stats/leaderboard?sort=share_value" class="filter-tab {'active' if sort == 'share_value' else ''}">Shares</a>
        <a href="/stats/leaderboard?sort=business_value" class="filter-tab {'active' if sort == 'business_value' else ''}">Businesses</a>
    </div>
    
    <div class="card" style="cursor: default; overflow-x: auto;">
        <table class="table">
            <thead>
                <tr>
                    <th>#</th>
                    <th>Player</th>
                    {sort_link('total_net_worth', 'Net Worth')}
                    {sort_link('cash_balance', 'Cash')}
                    {sort_link('land_value', 'Land')}
                    {sort_link('inventory_value', 'Inventory')}
                    {sort_link('share_value', 'Shares')}
                    <th>Biz</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
    </div>
    """
    
    return HTMLResponse(stats_shell("Leaderboard", body, player.cash_balance, player.business_name))


@router.get("/stats/businesses", response_class=HTMLResponse)
async def stats_businesses(
    session_token: Optional[str] = Cookie(None),
    category: str = Query("all")
):
    """Business encyclopedia with all production lines."""
    from auth import get_player_from_session
    db = get_db()
    player = get_player_from_session(db, session_token)
    if not player:
        db.close()
        return HTMLResponse('<meta http-equiv="refresh" content="0;url=/login">')
    db.close()
    
    # Load business types
    business_types = {}
    try:
        with open("business_types.json", "r") as f:
            business_types = json.load(f)
    except: pass
    
    district_businesses = {}
    try:
        with open("district_businesses.json", "r") as f:
            district_businesses = json.load(f)
    except: pass
    
    # Build business list
    biz_html = ""
    all_businesses = list(business_types.items())
    if category == "district":
        all_businesses = list(district_businesses.items())
    elif category != "all":
        all_businesses = [(k, v) for k, v in business_types.items() if v.get("class") == category]
    
    for key, biz in sorted(all_businesses, key=lambda x: x[1].get("name", x[0])):
        name = biz.get("name", key.replace("_", " ").title())
        desc = biz.get("description", "")[:80]
        cost = biz.get("startup_cost", 0)
        cycles = biz.get("cycles_to_complete", 1)
        biz_class = biz.get("class", "production")
        
        badge_class = "badge-green" if biz_class == "production" else "badge-blue" if biz_class == "retail" else "badge-gray"
        
        biz_html += f"""
        <a href="/stats/business/{key}" class="card" style="text-decoration: none;">
            <div class="card-header">
                <span class="card-title">{name}</span>
                <span class="badge {badge_class}">{biz_class}</span>
            </div>
            <div class="card-subtitle">{desc}</div>
            <div class="stat-row" style="margin-top: 8px;">
                <span class="stat-label">Startup</span>
                <span class="stat-value">${cost:,.0f}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Cycle Time</span>
                <span class="stat-value">{cycles} ticks</span>
            </div>
        </a>
        """
    
    body = f"""
    <h1 class="page-title">🏭 Business Encyclopedia</h1>
    
    <input type="text" class="search-box" placeholder="Search businesses..." onkeyup="searchBiz(this.value)">
    
    <div class="filter-tabs">
        <a href="/stats/businesses?category=all" class="filter-tab {'active' if category == 'all' else ''}">All</a>
        <a href="/stats/businesses?category=production" class="filter-tab {'active' if category == 'production' else ''}">Production</a>
        <a href="/stats/businesses?category=retail" class="filter-tab {'active' if category == 'retail' else ''}">Retail</a>
        <a href="/stats/businesses?category=district" class="filter-tab {'active' if category == 'district' else ''}">District</a>
    </div>
    
    <div class="grid" id="biz-grid">
        {biz_html}
    </div>
    
    <script>
    function searchBiz(query) {{
        const cards = document.querySelectorAll('#biz-grid .card');
        const q = query.toLowerCase();
        cards.forEach(card => {{
            const text = card.textContent.toLowerCase();
            card.style.display = text.includes(q) ? 'block' : 'none';
        }});
    }}
    </script>
    """
    
    return HTMLResponse(stats_shell("Businesses", body, player.cash_balance, player.business_name))


@router.get("/stats/business/{business_key}", response_class=HTMLResponse)
async def stats_business_detail(
    business_key: str,
    session_token: Optional[str] = Cookie(None)
):
    """Detailed business information with production lines."""
    from auth import get_player_from_session
    db = get_db()
    player = get_player_from_session(db, session_token)
    if not player:
        db.close()
        return HTMLResponse('<meta http-equiv="refresh" content="0;url=/login">')
    db.close()
    
    # Load business data
    biz = None
    is_district = False
    
    try:
        with open("business_types.json", "r") as f:
            business_types = json.load(f)
            biz = business_types.get(business_key)
    except: pass
    
    if not biz:
        try:
            with open("district_businesses.json", "r") as f:
                district_businesses = json.load(f)
                biz = district_businesses.get(business_key)
                is_district = True
        except: pass
    
    if not biz:
        return HTMLResponse(stats_shell("Not Found", "<h1>Business not found</h1>", player.cash_balance, player.business_name))
    
    name = biz.get("name", business_key.replace("_", " ").title())
    desc = biz.get("description", "")
    cost = biz.get("startup_cost", 0)
    cycles = biz.get("cycles_to_complete", 1)
    wage = biz.get("base_wage_cost", 0)
    biz_class = biz.get("class", "production")
    
    # Terrain requirements
    terrain = biz.get("allowed_terrain", [])
    proximity = biz.get("allowed_proximity", [])
    
    terrain_html = "".join([f'<span class="terrain-tag">{t}</span>' for t in terrain])
    proximity_html = "".join([f'<span class="terrain-tag">{p}</span>' for p in proximity])
    
    # Production lines
    prod_html = ""
    if "production_lines" in biz:
        for line in biz["production_lines"]:
            output = line.get("output_item", "?")
            output_qty = line.get("output_qty", 1)
            inputs = line.get("inputs", [])
            
            input_str = ", ".join([f'{inp["quantity"]} {inp["item"]}' for inp in inputs])
            
            prod_html += f"""
            <div class="recipe-item">
                <span>{input_str if input_str else 'No inputs'}</span>
                <span class="recipe-arrow">→</span>
                <strong>{output_qty} {output.replace('_', ' ')}</strong>
            </div>
            """
    
    # Retail products
    retail_html = ""
    if "products" in biz:
        for item, config in biz["products"].items():
            elasticity = config.get("elasticity", 1.0)
            sale_chance = config.get("base_sale_chance", 0.1)
            retail_html += f"""
            <div class="stat-row">
                <span class="stat-label">{item.replace('_', ' ').title()}</span>
                <span class="stat-value">Elasticity: {elasticity} | Sale Chance: {sale_chance*100:.1f}%</span>
            </div>
            """
    
    body = f"""
    <h1 class="page-title">{name}</h1>
    <p style="color: #94a3b8; margin-bottom: 24px;">{desc}</p>
    
    <div class="grid">
        <div class="card" style="cursor: default;">
            <div class="card-header">
                <span class="card-title">Statistics</span>
                <span class="badge {'badge-green' if biz_class == 'production' else 'badge-blue'}">{biz_class}</span>
            </div>
            <div class="stat-row"><span class="stat-label">Startup Cost</span><span class="stat-value">${cost:,.0f}</span></div>
            <div class="stat-row"><span class="stat-label">Cycle Time</span><span class="stat-value">{cycles} ticks</span></div>
            <div class="stat-row"><span class="stat-label">Wage Cost</span><span class="stat-value">${wage:,.2f}/cycle</span></div>
        </div>
        
        <div class="card" style="cursor: default;">
            <div class="card-header">
                <span class="card-title">Location Requirements</span>
            </div>
            <div style="margin-bottom: 8px;"><strong style="color: #94a3b8;">Terrain:</strong><br>{terrain_html or 'Any'}</div>
            <div><strong style="color: #94a3b8;">Proximity:</strong><br>{proximity_html or 'Any'}</div>
        </div>
    </div>
    
    {'<div class="detail-section"><div class="card" style="cursor: default;"><div class="detail-title">Production Lines</div>' + prod_html + '</div></div>' if prod_html else ''}
    
    {'<div class="detail-section"><div class="card" style="cursor: default;"><div class="detail-title">Retail Products</div>' + retail_html + '</div></div>' if retail_html else ''}
    
    <a href="/stats/businesses" style="display: inline-block; margin-top: 16px;">← Back to Businesses</a>
    """
    
    # Inject tutorial overlay for stats_business step (step 8: free_range_pasture)
    try:
        from tutorial_ux import get_tutorial_overlay_html
        tut_overlay = get_tutorial_overlay_html(player, "stats_business")
        if tut_overlay:
            body = tut_overlay + body
    except Exception:
        pass

    return HTMLResponse(stats_shell(name, body, player.cash_balance, player.business_name))


@router.get("/stats/items", response_class=HTMLResponse)
async def stats_items(
    session_token: Optional[str] = Cookie(None),
    category: str = Query("all")
):
    """Item catalog with all items and market data."""
    from auth import get_player_from_session
    db = get_db()
    player = get_player_from_session(db, session_token)
    if not player:
        db.close()
        return HTMLResponse('<meta http-equiv="refresh" content="0;url=/login">')
    db.close()
    
    # Load item types
    items = {}
    try:
        with open("item_types.json", "r") as f:
            items = json.load(f)
    except: pass
    
    # Also load district items
    try:
        with open("district_items.json", "r") as f:
            district_items = json.load(f)
            items.update(district_items)
    except: pass
    
    # Get unique categories
    categories = set()
    for key, item in items.items():
        categories.add(item.get("category", "misc"))
    
    # Filter by category
    filtered_items = items
    if category != "all":
        filtered_items = {k: v for k, v in items.items() if v.get("category") == category}
    
    # Build item list with market prices
    item_html = ""
    try:
        from market import get_market_price
    except:
        get_market_price = lambda x: None
    
    for key, item in sorted(filtered_items.items(), key=lambda x: x[1].get("name", x[0])):
        name = item.get("name", key.replace("_", " ").title())
        desc = item.get("description", "")[:60]
        cat = item.get("category", "misc")
        
        try:
            price = get_market_price(key)
            price_str = f"${price:,.2f}" if price else "No market"
        except:
            price_str = "No market"
        
        item_html += f"""
        <a href="/stats/item/{key}" class="card" style="text-decoration: none;">
            <div class="card-header">
                <span class="card-title">{name}</span>
                <span class="badge badge-gray">{cat}</span>
            </div>
            <div class="card-subtitle">{desc}</div>
            <div class="stat-row" style="margin-top: 8px;">
                <span class="stat-label">Market Price</span>
                <span class="stat-value">{price_str}</span>
            </div>
        </a>
        """
    
    # Build category filter
    cat_html = f'<a href="/stats/items?category=all" class="filter-tab {"active" if category == "all" else ""}">All</a>'
    for cat in sorted(categories):
        active = "active" if category == cat else ""
        cat_html += f'<a href="/stats/items?category={cat}" class="filter-tab {active}">{cat.replace("_", " ").title()}</a>'
    
    body = f"""
    <h1 class="page-title">📦 Item Catalog</h1>
    
    <input type="text" class="search-box" placeholder="Search items..." onkeyup="searchItems(this.value)">
    
    <div class="filter-tabs" style="flex-wrap: wrap;">
        {cat_html}
    </div>
    
    <div class="grid" id="item-grid">
        {item_html}
    </div>
    
    <script>
    function searchItems(query) {{
        const cards = document.querySelectorAll('#item-grid .card');
        const q = query.toLowerCase();
        cards.forEach(card => {{
            const text = card.textContent.toLowerCase();
            card.style.display = text.includes(q) ? 'block' : 'none';
        }});
    }}
    </script>
    """
    
    return HTMLResponse(stats_shell("Items", body, player.cash_balance, player.business_name))


@router.get("/stats/item/{item_key}", response_class=HTMLResponse)
async def stats_item_detail(
    item_key: str,
    session_token: Optional[str] = Cookie(None)
):
    """Detailed item information with price chart."""
    from auth import get_player_from_session
    db = get_db()
    player = get_player_from_session(db, session_token)
    if not player:
        db.close()
        return HTMLResponse('<meta http-equiv="refresh" content="0;url=/login">')
    
    # Load item data
    item = None
    try:
        with open("item_types.json", "r") as f:
            items = json.load(f)
            item = items.get(item_key)
    except: pass
    
    if not item:
        try:
            with open("district_items.json", "r") as f:
                district_items = json.load(f)
                item = district_items.get(item_key)
        except: pass
    
    if not item:
        db.close()
        return HTMLResponse(stats_shell("Not Found", "<h1>Item not found</h1>", player.cash_balance, player.business_name))
    
    name = item.get("name", item_key.replace("_", " ").title())
    desc = item.get("description", "")
    cat = item.get("category", "misc")
    
    # Get market price and history
    try:
        from market import get_market_price, Trade
        price = get_market_price(item_key)
        price_str = f"${price:,.2f}" if price else "No market data"
        
        # Get trade history for chart
        week_ago = datetime.utcnow() - timedelta(days=7)
        trades = db.query(Trade).filter(
            Trade.item_type == item_key,
            Trade.executed_at >= week_ago
        ).order_by(Trade.executed_at.asc()).all()
    except:
        price = None
        price_str = "No market data"
        trades = []
    
    # Build mini chart
    chart_html = ""
    if trades:
        prices = [t.price for t in trades]
        max_price = max(prices) if prices else 1
        min_price = min(prices) if prices else 0
        price_range = max_price - min_price or 1
        
        bars = []
        for t in trades[-30:]:  # Last 30 trades
            height = ((t.price - min_price) / price_range) * 50 + 10
            bars.append(f'<div class="mini-chart-bar" style="height: {height}px;" title="${t.price:.2f}"></div>')
        
        chart_html = f"""
        <div class="chart-container">
            <div style="color: #94a3b8; font-size: 0.75rem; margin-bottom: 8px;">7-Day Price History</div>
            <div class="mini-chart">{''.join(bars)}</div>
            <div style="display: flex; justify-content: space-between; color: #64748b; font-size: 0.7rem; margin-top: 4px;">
                <span>Low: ${min_price:.2f}</span>
                <span>High: ${max_price:.2f}</span>
            </div>
        </div>
        """
    else:
        chart_html = '<div class="chart-container"><div style="color: #64748b; text-align: center; padding: 20px;">No trade history available</div></div>'
    
    # Find which businesses produce this item
    produces_html = ""
    try:
        with open("business_types.json", "r") as f:
            business_types = json.load(f)
            for biz_key, biz in business_types.items():
                for line in biz.get("production_lines", []):
                    if line.get("output_item") == item_key:
                        produces_html += f'<a href="/stats/business/{biz_key}" class="terrain-tag" style="color: #38bdf8;">{biz.get("name", biz_key)}</a>'
    except: pass
    
    # Find which businesses use this item as input
    used_by_html = ""
    try:
        with open("business_types.json", "r") as f:
            business_types = json.load(f)
            for biz_key, biz in business_types.items():
                for line in biz.get("production_lines", []):
                    for inp in line.get("inputs", []):
                        if inp.get("item") == item_key:
                            used_by_html += f'<a href="/stats/business/{biz_key}" class="terrain-tag" style="color: #38bdf8;">{biz.get("name", biz_key)}</a>'
                            break
    except: pass
    
    # Get player's cost average
    avg = db.query(PlayerCostAverage).filter(
        PlayerCostAverage.player_id == player.id,
        PlayerCostAverage.item_type == item_key
    ).first()
    
    avg_html = ""
    if avg and avg.total_quantity > 0:
        avg_html = f"""
        <div class="stat-row"><span class="stat-label">Your Avg Cost</span><span class="stat-value">${avg.average_cost:.2f}/unit</span></div>
        <div class="stat-row"><span class="stat-label">Total Acquired</span><span class="stat-value">{avg.total_quantity:,.0f} units</span></div>
        <div class="stat-row"><span class="stat-label">Total Spent</span><span class="stat-value">${avg.total_spent:,.2f}</span></div>
        """
    
    db.close()
    
    body = f"""
    <h1 class="page-title">{name}</h1>
    <p style="color: #94a3b8; margin-bottom: 24px;">{desc}</p>
    
    <div class="grid">
        <div class="card" style="cursor: default;">
            <div class="card-header">
                <span class="card-title">Market Data</span>
                <span class="badge badge-gray">{cat}</span>
            </div>
            <div class="card-value">{price_str}</div>
            {avg_html}
        </div>
        
        <div>
            {chart_html}
        </div>
    </div>
    
    {'<div class="detail-section"><div class="card" style="cursor: default;"><div class="detail-title">Produced By</div><div style="margin-top: 8px;">' + produces_html + '</div></div></div>' if produces_html else ''}
    
    {'<div class="detail-section"><div class="card" style="cursor: default;"><div class="detail-title">Used By</div><div style="margin-top: 8px;">' + used_by_html + '</div></div></div>' if used_by_html else ''}
    
    <a href="/stats/items" style="display: inline-block; margin-top: 16px;">← Back to Items</a>
    """
    
    return HTMLResponse(stats_shell(name, body, player.cash_balance, player.business_name))


# ==========================
# DISTRICTS ENCYCLOPEDIA
# ==========================

@router.get("/stats/districts", response_class=HTMLResponse)
async def stats_districts(session_token: Optional[str] = Cookie(None)):
    """District types encyclopedia — terrain rules, taxes, and which businesses they support."""
    from auth import get_player_from_session
    db = get_db()
    player = get_player_from_session(db, session_token)
    db.close()
    if not player:
        return HTMLResponse('<meta http-equiv="refresh" content="0;url=/login">')

    try:
        from districts import DISTRICT_TYPES, DISTRICT_TAX_MULTIPLIER
    except Exception:
        DISTRICT_TYPES = {}
        DISTRICT_TAX_MULTIPLIER = 15

    try:
        import json as _json
        with open("district_businesses.json") as f:
            dist_biz = _json.load(f)
    except Exception:
        dist_biz = {}

    # Build a map: district_terrain → list of business names
    terrain_to_biz: Dict[str, list] = {}
    for biz_key, biz_cfg in dist_biz.items():
        for terrain in biz_cfg.get("allowed_terrain", []):
            terrain_to_biz.setdefault(terrain, []).append(biz_cfg.get("name", biz_key))

    cards = ""
    for dtype, cfg in sorted(DISTRICT_TYPES.items(), key=lambda x: x[1]["name"]):
        terrain_key = cfg.get("district_terrain", f"district_{dtype}")
        base_tax = cfg["base_tax"]
        monthly_ex = base_tax * 1.0 * DISTRICT_TAX_MULTIPLIER  # size=1 example
        allowed = ", ".join(t.title() for t in cfg.get("allowed_terrain", []))
        businesses_here = terrain_to_biz.get(terrain_key, [])
        biz_list = "".join(f'<li style="color:#94a3b8;">{b}</li>' for b in sorted(businesses_here)) if businesses_here else '<li style="color:#475569;">No special businesses</li>'

        cards += f"""
        <div class="card" style="cursor:default;">
            <div class="card-header">
                <span class="card-title">{cfg["name"]}</span>
                <span class="card-icon" style="font-size:0.7rem;color:#f59e0b;">${monthly_ex:,.0f}/mo*</span>
            </div>
            <div class="stat-row"><span class="stat-label">Base Tax</span><span class="stat-value">${base_tax:,}/mo × 15</span></div>
            <div class="stat-row"><span class="stat-label">Terrain</span><span class="stat-value" style="font-size:0.75rem;">{allowed}</span></div>
            <div class="stat-row" style="align-items:flex-start;">
                <span class="stat-label">Businesses</span>
                <ul style="list-style:none;text-align:right;margin:0;padding:0;font-size:0.7rem;">{biz_list}</ul>
            </div>
        </div>"""

    body = f"""
    <h1 class="page-title">🏙️ Districts Encyclopedia</h1>
    <p style="color:#64748b;font-size:0.8rem;margin-bottom:16px;">
        Districts are formed by merging {5} land plots (Fibonacci sequence). Tax = Base × Size × 15.
        *Example shows size=1.
    </p>
    <div class="grid">{cards}</div>
    <a href="/stats" style="display:inline-block;margin-top:16px;">← Back to Analytics</a>
    """
    return HTMLResponse(stats_shell("Districts", body, player.cash_balance, player.business_name))


# ==========================
# PRODUCTION COSTS
# ==========================

@router.get("/stats/production-costs", response_class=HTMLResponse)
async def stats_production_costs(
    session_token: Optional[str] = Cookie(None),
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    sort: Optional[str] = Query("cost_asc"),
):
    """Full production cost guide for all items (regular + district) with cheapest recipe."""
    from auth import get_player_from_session
    db = get_db()
    player = get_player_from_session(db, session_token)
    db.close()
    if not player:
        return HTMLResponse('<meta http-equiv="refresh" content="0;url=/login">')

    import json as _json

    # ── Load regular items from item_costs.json ──────────────────────────────
    try:
        with open("item_costs.json") as f:
            cost_data = _json.load(f)
        regular_items = cost_data.get("items", [])
    except Exception:
        regular_items = []

    # ── Load district items from district_businesses.json ────────────────────
    try:
        with open("district_businesses.json") as f:
            dist_biz = _json.load(f)
    except Exception:
        dist_biz = {}

    try:
        with open("district_items.json") as f:
            dist_item_types = _json.load(f)
    except Exception:
        dist_item_types = {}

    # Build district-produced items: item_key → cheapest cost entry
    dist_produced: Dict[str, dict] = {}
    for biz_key, biz_cfg in dist_biz.items():
        for line in biz_cfg.get("production_lines", []):
            out_item = line.get("output_item")
            out_qty = line.get("output_qty", 1) or 1
            inputs = line.get("inputs", [])
            # Wage cost per cycle converted to per-output
            cycles = biz_cfg.get("cycles_to_complete", 1) or 1
            wage_per_cycle = biz_cfg.get("base_wage_cost", 0.0)
            # We can't resolve market input costs here perfectly, so we note the recipe inputs
            if out_item and out_qty > 0:
                entry = {
                    "item_key": out_item,
                    "name": dist_item_types.get(out_item, {}).get("name") or out_item.replace("_", " ").title(),
                    "category": dist_item_types.get(out_item, {}).get("category", "district"),
                    "best_recipe": biz_key,
                    "output_qty": out_qty,
                    "inputs": inputs,
                    "wage_per_cycle": wage_per_cycle,
                    "is_district": True,
                }
                # Keep the recipe with highest output quantity (cheapest per unit)
                existing = dist_produced.get(out_item)
                if not existing or out_qty > existing["output_qty"]:
                    dist_produced[out_item] = entry

    # Merge: regular items take priority; add district-only items after
    regular_keys = {item["item_key"] for item in regular_items}
    all_items = list(regular_items)
    for item_key, entry in dist_produced.items():
        if item_key not in regular_keys:
            # District-exclusive item
            all_items.append({
                "item_key": entry["item_key"],
                "name": entry["name"],
                "category": entry["category"],
                "base_cost": None,  # Can't compute without market prices
                "has_recipe": True,
                "best_recipe": entry["best_recipe"],
                "output_qty": entry["output_qty"],
                "is_district": True,
                "inputs": entry["inputs"],
            })
        else:
            # Regular item also producible in district — annotate it
            for r in all_items:
                if r["item_key"] == item_key:
                    r.setdefault("also_district_recipe", entry["best_recipe"])

    # ── Filtering ─────────────────────────────────────────────────────────────
    categories = sorted({item.get("category", "other") for item in all_items if item.get("category")})

    if search:
        q = search.lower()
        all_items = [i for i in all_items if q in i["item_key"].lower() or q in i.get("name", "").lower()]
    if category and category != "all":
        all_items = [i for i in all_items if i.get("category") == category]

    # ── Sorting ───────────────────────────────────────────────────────────────
    def sort_key(item):
        cost = item.get("base_cost")
        return (cost is None, cost or 0)

    if sort == "cost_asc":
        all_items.sort(key=sort_key)
    elif sort == "cost_desc":
        all_items.sort(key=sort_key, reverse=True)
    elif sort == "name":
        all_items.sort(key=lambda i: i.get("name", i["item_key"]))
    elif sort == "output_desc":
        all_items.sort(key=lambda i: i.get("output_qty") or 0, reverse=True)

    # ── Category filter tabs ──────────────────────────────────────────────────
    cat_active = category or "all"
    cat_tabs = f'<a href="/stats/production-costs?sort={sort}" class="{"active" if cat_active=="all" else ""}">All ({len(cost_data.get("items",[]) if not search else all_items)})</a>'
    for cat in categories:
        cnt = sum(1 for i in (cost_data.get("items", []) + list(dist_produced.values())) if i.get("category") == cat)
        active_cls = "active" if cat_active == cat else ""
        cat_tabs += f'<a href="/stats/production-costs?category={cat}&sort={sort}" class="{active_cls}">{cat.replace("_"," ").title()} ({cnt})</a>'

    # ── Sort links ────────────────────────────────────────────────────────────
    def sort_link(label, s):
        base = f"/stats/production-costs?sort={s}"
        if category:
            base += f"&category={category}"
        if search:
            base += f"&search={search}"
        active = "color:#38bdf8;font-weight:bold;" if sort == s else "color:#64748b;"
        return f'<a href="{base}" style="font-size:0.75rem;{active}">{label}</a>'

    sort_links = " | ".join([
        sort_link("Cost ↑", "cost_asc"),
        sort_link("Cost ↓", "cost_desc"),
        sort_link("Name", "name"),
        sort_link("Output ↓", "output_desc"),
    ])

    # ── Table rows ────────────────────────────────────────────────────────────
    rows = ""
    for item in all_items:
        name = item.get("name") or item["item_key"].replace("_", " ").title()
        cat_badge = f'<span style="font-size:0.6rem;color:#64748b;">{item.get("category","?")}</span>'
        recipe = item.get("best_recipe") or "—"
        recipe_nice = recipe.replace("_", " ").title()

        dist_tag = ""
        if item.get("is_district"):
            dist_tag = ' <span style="font-size:0.55rem;padding:1px 4px;background:#1e3a5f;color:#93c5fd;border-radius:2px;">DISTRICT</span>'
        elif item.get("also_district_recipe"):
            dist_tag = f' <span style="font-size:0.55rem;padding:1px 4px;background:#1c2d1c;color:#86efac;border-radius:2px;" title="Also: {item["also_district_recipe"]}">+DIST</span>'

        cost = item.get("base_cost")
        if cost is None:
            cost_str = '<span style="color:#475569;">market</span>'
            cost_per = '<span style="color:#475569;">—</span>'
        elif cost == 0:
            cost_str = '<span style="color:#22c55e;">$0.00</span>'
            cost_per = '<span style="color:#22c55e;">$0.00</span>'
        else:
            cost_str = f'<span style="color:#e5e7eb;">${cost:,.4f}</span>' if cost < 1 else f'<span style="color:#e5e7eb;">${cost:,.2f}</span>'
            out_qty = item.get("output_qty") or 1
            per = cost / out_qty
            cost_per = f'${per:,.4f}' if per < 1 else f'${per:,.2f}'

        out_qty = item.get("output_qty")
        out_str = f'{out_qty:,}' if out_qty else '—'

        # Show district inputs inline
        inputs_html = ""
        if item.get("is_district") and item.get("inputs"):
            parts = ", ".join(f'{inp["quantity"]:,}× {inp["item"].replace("_"," ")}' for inp in item["inputs"][:4])
            if len(item["inputs"]) > 4:
                parts += f" +{len(item['inputs'])-4} more"
            inputs_html = f'<div style="font-size:0.6rem;color:#475569;margin-top:2px;">{parts}</div>'

        rows += f"""<tr>
            <td>
                <a href="/stats/item/{item['item_key']}" style="font-weight:bold;">{name}</a>{dist_tag}
                {cat_badge}
                {inputs_html}
            </td>
            <td style="color:#94a3b8;">{recipe_nice}</td>
            <td style="text-align:right;">{out_str}</td>
            <td style="text-align:right;">{cost_str}</td>
            <td style="text-align:right;">{cost_per}</td>
        </tr>"""

    search_val = search or ""
    body = f"""
    <h1 class="page-title">💰 Production Cost Guide</h1>
    <p style="color:#64748b;font-size:0.78rem;margin-bottom:12px;">
        Covers {len(all_items):,} items including district-exclusive products.
        Cost = total input cost for one production cycle via the cheapest known recipe.
        District items marked <span style="font-size:0.65rem;padding:1px 4px;background:#1e3a5f;color:#93c5fd;border-radius:2px;">DISTRICT</span> require a district business.
    </p>

    <form method="get" action="/stats/production-costs" style="margin-bottom:10px;display:flex;gap:6px;flex-wrap:wrap;">
        <input type="text" name="search" value="{search_val}" placeholder="Search items..." style="flex:1;min-width:150px;max-width:260px;">
        {'<input type="hidden" name="category" value="' + category + '">' if category else ''}
        <input type="hidden" name="sort" value="{sort}">
        <button type="submit" style="background:#334155;border:none;color:#e5e7eb;padding:6px 10px;cursor:pointer;border-radius:3px;font-size:0.78rem;">Search</button>
        {f'<a href="/stats/production-costs" style="font-size:0.75rem;padding:6px 8px;background:#1e293b;border-radius:3px;color:#94a3b8;">Clear</a>' if search else ''}
    </form>

    <div style="display:flex;gap:8px;margin-bottom:10px;font-size:0.72rem;">{sort_links}</div>

    <div class="tabs" style="margin-bottom:10px;">{cat_tabs}</div>

    <div class="card" style="padding:0;">
        <div class="table-wrap">
            <table>
                <tr>
                    <th>Item</th>
                    <th>Best Recipe</th>
                    <th style="text-align:right;">Output Qty</th>
                    <th style="text-align:right;">Cycle Cost</th>
                    <th style="text-align:right;">Cost/Unit</th>
                </tr>
                {rows if rows else '<tr><td colspan="5" style="text-align:center;color:#64748b;padding:16px;">No items found.</td></tr>'}
            </table>
        </div>
    </div>

    <p style="font-size:0.65rem;color:#475569;margin-top:8px;">
        Costs calculated from item_costs.json (452 items). District items use recipe metadata; actual cost depends on current market prices of input materials.
    </p>
    <a href="/stats" style="display:inline-block;margin-top:8px;">← Back to Analytics</a>
    """
    return HTMLResponse(stats_shell("Production Costs", body, player.cash_balance, player.business_name))


# ==========================
# MODULE LIFECYCLE
# ==========================

def initialize():
    """Initialize stats module."""
    Base.metadata.create_all(bind=engine)
    print("[Stats] Database tables created")
    print("[Stats] Analytics dashboard initialized")


async def tick(current_tick: int, now: datetime):
    """Stats tick handler."""
    # Update rankings every 10 minutes
    if current_tick % 600 == 0:
        update_all_rankings()
    
    # Record price snapshots every hour
    if current_tick % 3600 == 0:
        try:
            from inventory import ITEM_RECIPES
            from market import get_market_price
            
            for item_type in ITEM_RECIPES.keys():
                price = get_market_price(item_type)
                if price:
                    record_price_snapshot(item_type, price)
        except:
            pass


# ==========================
# PUBLIC API
# ==========================

__all__ = [
    "router",
    "initialize",
    "tick",
    "log_transaction",
    "calculate_player_stats",
    "update_all_rankings",
    "get_price_history",
    "PlayerStats",
    "TransactionLog",
    "PlayerCostAverage",
    "PriceSnapshot"
]
