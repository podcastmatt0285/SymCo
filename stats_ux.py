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
from sqlalchemy import Column, String, Float, DateTime, Integer, Boolean, desc, func, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from database import engine, SessionLocal
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
        
        # Update cost averages for purchases (any transaction where we paid money for an item)
        _purchase_types = {
            'market_buy', 'cash_out', 'district_market_buy',
            'resource_gain',  # resource_gain with negative amount = paid for resources
        }
        if item_type and quantity > 0 and amount < 0 and transaction_type in _purchase_types:
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

        # Start with USD cash balance, then add foreign currency balances
        # converted to USD so the total is currency-agnostic
        total_cash_usd = player.cash_balance or 0.0
        try:
            from reserve_banks import PlayerCurrencyBalance, StateReserveBank, get_db as get_rb_db
            rb_db = get_rb_db()
            try:
                for row in rb_db.query(PlayerCurrencyBalance).filter(
                    PlayerCurrencyBalance.player_id == player_id,
                    PlayerCurrencyBalance.currency_code != "USD",
                ).all():
                    bank = rb_db.query(StateReserveBank).filter(
                        StateReserveBank.currency_code == row.currency_code
                    ).first()
                    if bank and bank.usd_per_unit:
                        total_cash_usd += row.balance * bank.usd_per_unit
            finally:
                rb_db.close()
        except Exception:
            pass

        stats = {
            "cash_balance": total_cash_usd,
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

def stats_shell(title: str, body: str, balance: float = 0.0, player_name: str = "", player_id: int = None) -> str:
    """Render the stats dashboard shell."""
    disp_sym      = "$"
    disp_balance  = balance
    disp_usd_note = ""
    if player_id:
        try:
            from reserve_banks import get_player_legal_tender, get_player_currency_balances
            tender = get_player_legal_tender(player_id)
            if tender != "USD":
                for b in get_player_currency_balances(player_id):
                    if b["currency_code"] == tender:
                        disp_sym      = b["currency_symbol"]
                        disp_balance  = b["balance"]
                        disp_usd_note = (
                            f' <span style="font-size:0.65em;color:#64748b;">'
                            f'/ ${balance:,.0f} USD</span>'
                        )
                        break
        except Exception:
            pass
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
            <span class="balance">{disp_sym}{disp_balance:,.2f}{disp_usd_note}</span>
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
        <a href="/stats/wiki" style="color:#f5a855;font-weight:600;">📖 Wiki</a>
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

    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)
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
            <div class="card-value">{fmt_usd(stats['total_net_worth'], disp, precision=0)}</div>
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
                <div class="stat-row"><span class="stat-label">Cash</span><span class="stat-value">{fmt_usd(stats['cash_balance'], disp)}</span></div>
                <div class="stat-row"><span class="stat-label">Land Value</span><span class="stat-value">{fmt_usd(stats['land_value'], disp)}</span></div>
                <div class="stat-row"><span class="stat-label">Inventory</span><span class="stat-value">{fmt_usd(stats['inventory_value'], disp)}</span></div>
            </div>
            <div class="card" style="cursor: default;">
                <div class="stat-row"><span class="stat-label">Business Value</span><span class="stat-value">{fmt_usd(stats['business_value'], disp)}</span></div>
                <div class="stat-row"><span class="stat-label">Share Value</span><span class="stat-value">{fmt_usd(stats['share_value'], disp)}</span></div>
                <div class="stat-row"><span class="stat-label">District Value</span><span class="stat-value">{fmt_usd(stats['district_value'], disp)}</span></div>
            </div>
        </div>
    </div>
    """
    
    return HTMLResponse(stats_shell("Dashboard", body, player.cash_balance, player.business_name, player.id))


@router.get("/stats/economy", response_class=HTMLResponse)
async def stats_economy(session_token: Optional[str] = Cookie(None)):
    """Global economy overview."""
    from auth import get_player_from_session
    db = get_db()
    player = get_player_from_session(db, session_token)
    if not player:
        db.close()
        return HTMLResponse('<meta http-equiv="refresh" content="0;url=/login">')
    
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)
    from auth import Player
    
    # Gather economy stats
    total_players = db.query(Player).count()
    # cash_balance is a @property backed by reserve_banks — query that DB directly
    try:
        from reserve_banks import PlayerCurrencyBalance, get_db as get_rb_db
        rb_db = get_rb_db()
        try:
            total_cash = rb_db.query(func.sum(PlayerCurrencyBalance.balance)).filter(
                PlayerCurrencyBalance.currency_code == "USD"
            ).scalar() or 0.0
        finally:
            rb_db.close()
    except Exception:
        total_cash = 0.0
    
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
            <div class="stat-row"><span class="stat-label">Total Money Supply</span><span class="stat-value">{fmt_usd(total_cash, disp, precision=0)}</span></div>
            <div class="stat-row"><span class="stat-label">Avg per Player</span><span class="stat-value">{fmt_usd(total_cash/max(total_players,1), disp, precision=0)}</span></div>
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
            <div class="stat-row"><span class="stat-label">24h Volume</span><span class="stat-value">{fmt_usd(market_volume, disp, precision=0)}</span></div>
            <div class="stat-row"><span class="stat-label">Listed Companies</span><span class="stat-value">{total_companies:,}</span></div>
        </div>
    </div>
    """
    
    return HTMLResponse(stats_shell("Economy", body, player.cash_balance, player.business_name, player.id))


@router.get("/stats/personal", response_class=HTMLResponse)
async def stats_personal(session_token: Optional[str] = Cookie(None)):
    """Personal business economy dashboard."""
    from auth import get_player_from_session
    db = get_db()
    player = get_player_from_session(db, session_token)
    if not player:
        db.close()
        return HTMLResponse('<meta http-equiv="refresh" content="0;url=/login">')

    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)
    stats = calculate_player_stats(player.id)

    # Fetch last 500 transactions
    txs = db.query(TransactionLog).filter(
        TransactionLog.player_id == player.id
    ).order_by(desc(TransactionLog.timestamp)).limit(500).all()

    # Get cost averages
    averages = db.query(PlayerCostAverage).filter(
        PlayerCostAverage.player_id == player.id,
        PlayerCostAverage.total_quantity > 0
    ).order_by(desc(PlayerCostAverage.total_spent)).limit(200).all()

    # Multi-currency balances
    currency_rows = []
    try:
        from reserve_banks import PlayerCurrencyBalance, StateReserveBank, get_db as get_rb_db
        rb_db = get_rb_db()
        try:
            for row in rb_db.query(PlayerCurrencyBalance).filter(
                PlayerCurrencyBalance.player_id == player.id,
                PlayerCurrencyBalance.balance > 0,
            ).all():
                bank = rb_db.query(StateReserveBank).filter(
                    StateReserveBank.currency_code == row.currency_code
                ).first()
                sym = bank.currency_symbol if bank else row.currency_code
                usd_val = row.balance * bank.usd_per_unit if bank and bank.usd_per_unit else row.balance
                currency_rows.append((row.currency_code, sym, row.balance, usd_val))
        finally:
            rb_db.close()
    except Exception:
        pass

    db.close()

    # ── Relative time helper ──────────────────────────────────────────────────
    def _rel_time(ts) -> str:
        if not ts:
            return ""
        delta = datetime.utcnow() - ts
        s = int(delta.total_seconds())
        if s < 60: return "just now"
        if s < 3600: return f"{s//60}m ago"
        if s < 86400: return f"{s//3600}h ago"
        if s < 604800: return f"{s//86400}d ago"
        return ts.strftime('%b %d')

    # ── Icon & badge-colour maps covering every transaction type ──────────────
    TYPE_ICONS = {
        # Market
        "market_buy": "🛒", "market_sell": "💰",
        "resource_gain": "📦", "resource_loss": "📤", "resource_use": "🔧",
        "cash_in": "💵", "cash_out": "💸",
        # Business
        "retail_sale": "🏪", "business_startup": "🔨",
        # Land
        "land_buy": "🏗️", "land_sell": "🏷️",
        # Districts
        "district_merge": "🏙️", "district_tax": "💲", "district_market_buy": "🏬", "district_market_sell": "🏬",
        # Cities / Counties
        "city_creation": "🌆", "city_application_fee": "📋", "city_application_income": "📋",
        "city_relocation_fee": "🚛", "city_subsidy": "🎁",
        "county_mining_deposit": "⛏️",
        # Crypto
        "crypto_buy": "₿", "crypto_sell": "₿", "crypto_swap": "🔄",
        # Governance
        "governance_proposal": "🗳️", "governance_vote": "🗳️",
        # Treasury
        "treasury_grant": "🏛️",
        # Bonds / Forex
        "bond_purchase": "📜", "bond_sell": "📄", "bond_maturity": "✅", "bond_called": "📣",
        "forex_fee": "💱",
        # Shares / Dividends
        "share_buy": "📈", "share_sell": "📉",
        "dividend": "💸", "dividend_paid": "💸",
        "tax_voucher": "🎫",
        # Corporate
        "corporate": "📊",
        # P2P Contracts
        "p2p_access": "🔑", "p2p_contract_acquired": "📝", "p2p_contract_sold": "📝",
        "p2p_relist_fee": "🔁", "p2p_contract_delivery": "📦",
        "p2p_contract_payment": "💳", "p2p_breach_penalty": "⚠️", "p2p_breach_damages": "⚖️",
        # Estate / Misc
        "inheritance": "📜", "tax": "📋",
    }
    TYPE_BADGE_COLORS = {
        # Market
        "market_buy": "#3b82f6", "market_sell": "#3b82f6",
        "resource_gain": "#0ea5e9", "resource_loss": "#0ea5e9", "resource_use": "#7c3aed",
        "cash_in": "#22c55e", "cash_out": "#ef4444",
        # Business
        "retail_sale": "#8b5cf6", "business_startup": "#7c3aed",
        # Land
        "land_buy": "#84cc16", "land_sell": "#84cc16",
        # Districts / Cities
        "district_merge": "#f59e0b", "district_tax": "#f97316",
        "district_market_buy": "#10b981", "district_market_sell": "#10b981",
        "city_creation": "#38bdf8", "city_application_fee": "#38bdf8",
        "city_application_income": "#22c55e", "city_relocation_fee": "#f97316",
        "city_subsidy": "#22c55e", "county_mining_deposit": "#92400e",
        # Crypto / Governance / Treasury
        "crypto_buy": "#f59e0b", "crypto_sell": "#f59e0b", "crypto_swap": "#f59e0b",
        "governance_proposal": "#6366f1", "governance_vote": "#6366f1",
        "treasury_grant": "#22c55e",
        # Bonds / Forex
        "bond_purchase": "#0891b2", "bond_sell": "#0891b2",
        "bond_maturity": "#10b981", "bond_called": "#10b981", "forex_fee": "#f97316",
        # Shares / Dividends
        "share_buy": "#3b82f6", "share_sell": "#3b82f6",
        "dividend": "#22c55e", "dividend_paid": "#ef4444", "tax_voucher": "#a78bfa",
        # Corporate / P2P / Estate
        "corporate": "#64748b",
        "p2p_access": "#475569", "p2p_contract_acquired": "#6366f1",
        "p2p_contract_sold": "#6366f1", "p2p_relist_fee": "#475569",
        "p2p_contract_delivery": "#0ea5e9", "p2p_contract_payment": "#3b82f6",
        "p2p_breach_penalty": "#ef4444", "p2p_breach_damages": "#22c55e",
        "inheritance": "#a78bfa", "tax": "#f97316",
    }

    # Maps filter-chip key → type-prefix tuples matching actual log_transaction() call sites.
    TAB_FILTERS = {
        # Trading & Markets
        "market":          ("market_buy", "market_sell"),
        "district_market": ("district_market_buy", "district_market_sell"),
        "shares":          ("share_buy", "share_sell"),
        "dividend":        ("dividend",),             # dividend + dividend_paid
        "bonds":           ("bond_",),                # bond_purchase/sell/maturity/called
        "bond_income":     ("bond_maturity", "bond_called"),  # only payout events
        "crypto":          ("crypto_",),
        "forex":           ("forex_",),
        # Business & Income
        "retail":          ("retail_sale",),
        "resources":       ("resource_gain", "resource_loss", "resource_use"),
        "cash":            ("cash_in", "cash_out"),   # land market, brokerage cash side, etc.
        "treasury":        ("treasury_",),
        # Land & Property
        "land":            ("land_buy", "land_sell"),
        "mining":          ("county_mining",),
        # District & City Government
        "district":        ("district_merge", "district_tax"),
        "city":            ("city_", "county_"),      # city_* + county_mining_deposit
        "governance":      ("governance_",),
        "tax":             ("tax",),                  # tax + tax_voucher + district_tax
        # P2P Contracts
        "p2p":             ("p2p_",),
        "p2p_contracts":   ("p2p_contract",),         # acquired/sold/delivery/payment
        "p2p_fees":        ("p2p_access", "p2p_relist_fee", "p2p_breach"),
        # Corporate & Legal
        "corporate":       ("corporate", "business_startup"),
        "inheritance":     ("inheritance",),
    }
    # Build a flat JSON map of type → category list for JS
    type_to_tabs: Dict[str, List[str]] = {}
    for tx in txs:
        tt = tx.transaction_type or ""
        if tt and tt not in type_to_tabs:
            matched = [tab for tab, prefixes in TAB_FILTERS.items()
                       if any(tt.startswith(p) or p in tt for p in prefixes)]
            type_to_tabs[tt] = matched

    # ── Data aggregation ──────────────────────────────────────────────────────
    from datetime import date as _date
    today = datetime.utcnow().date()
    cutoff_30d = datetime.utcnow() - timedelta(days=30)

    # Per-day buckets for the chart
    daily: Dict[_date, Dict] = {}
    for tx in txs:
        if not tx.timestamp or tx.timestamp < cutoff_30d:
            continue
        d = tx.timestamp.date()
        if d not in daily:
            daily[d] = {"inc": 0.0, "exp": 0.0}
        if tx.amount > 0:
            daily[d]["inc"] += tx.amount
        elif tx.amount < 0:
            daily[d]["exp"] += abs(tx.amount)

    chart_days = [
        {"date": today - timedelta(days=i), "inc": 0.0, "exp": 0.0}
        for i in range(29, -1, -1)
    ]
    for cd in chart_days:
        if cd["date"] in daily:
            cd["inc"] = daily[cd["date"]]["inc"]
            cd["exp"] = daily[cd["date"]]["exp"]

    # Category breakdown (30-day)
    cat_income: Dict[str, float] = {}
    cat_expense: Dict[str, float] = {}
    count_by_tab: Dict[str, int] = {}
    for tx in txs:
        if tx.timestamp and tx.timestamp < cutoff_30d:
            continue
        tt = tx.transaction_type or "other"
        grp = tt.split("_")[0]
        if tx.amount > 0:
            cat_income[grp] = cat_income.get(grp, 0.0) + tx.amount
        elif tx.amount < 0:
            cat_expense[grp] = cat_expense.get(grp, 0.0) + abs(tx.amount)
    # count by tab for badges
    for tx in txs:
        tt = tx.transaction_type or ""
        for tab, prefixes in TAB_FILTERS.items():
            if any(tt.startswith(p) or p in tt for p in prefixes):
                count_by_tab[tab] = count_by_tab.get(tab, 0) + 1

    total_income = sum(tx.amount for tx in txs if tx.amount > 0)
    total_expenses = sum(tx.amount for tx in txs if tx.amount < 0)
    net = total_income + total_expenses
    tx_count = len(txs)
    biggest_tx = max(txs, key=lambda t: abs(t.amount), default=None)

    # ── SVG Cash Flow Chart ───────────────────────────────────────────────────
    CW, CH, INNER = 600, 110, 80
    max_daily_val = max(
        (max(d["inc"] for d in chart_days), max(d["exp"] for d in chart_days)),
        default=1
    ) or 1
    slot = CW / 30  # px per day
    svg_bars = ""
    for i, cd in enumerate(chart_days):
        xc = i * slot + slot / 2
        bw = max(slot * 0.32, 2)
        if cd["inc"] > 0:
            h = cd["inc"] / max_daily_val * INNER
            svg_bars += (f'<rect x="{xc:.1f}" y="{INNER - h:.1f}" width="{bw:.1f}" height="{h:.1f}" '
                         f'fill="#22c55e" fill-opacity="0.85" rx="1"/>')
        if cd["exp"] > 0:
            h = cd["exp"] / max_daily_val * INNER
            svg_bars += (f'<rect x="{xc - bw:.1f}" y="{INNER - h:.1f}" width="{bw:.1f}" height="{h:.1f}" '
                         f'fill="#ef4444" fill-opacity="0.75" rx="1"/>')
    # Cumulative net line
    cum = 0.0
    cum_pts = []
    for i, cd in enumerate(chart_days):
        cum += cd["inc"] - cd["exp"]
        cum_pts.append(cum)
    cum_max = max(abs(v) for v in cum_pts) if cum_pts else 1
    cum_max = cum_max or 1
    mid_y = INNER / 2
    net_pts = " ".join(
        f"{i * slot + slot/2:.1f},{mid_y - (v / cum_max * mid_y * 0.85):.1f}"
        for i, v in enumerate(cum_pts)
    )
    last_y = mid_y - (cum_pts[-1] / cum_max * mid_y * 0.85) if cum_pts else mid_y
    line_color = "#22c55e" if (cum_pts[-1] if cum_pts else 0) >= 0 else "#ef4444"
    # X-axis date labels
    svg_labels = ""
    for i, cd in enumerate(chart_days):
        if i % 7 == 0 or i == 29:
            svg_labels += (f'<text x="{i*slot+slot/2:.1f}" y="{CH - 2}" '
                           f'text-anchor="middle" font-size="7" fill="#475569">'
                           f'{cd["date"].strftime("%-m/%-d")}</text>')
    chart_svg = (
        f'<svg viewBox="0 0 {CW} {CH}" style="width:100%;height:{CH}px;display:block;">'
        f'<defs><linearGradient id="netlg" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" stop-color="{line_color}" stop-opacity="0.15"/>'
        f'<stop offset="100%" stop-color="{line_color}" stop-opacity="0"/>'
        f'</linearGradient></defs>'
        f'<line x1="0" y1="{INNER}" x2="{CW}" y2="{INNER}" stroke="#1e293b" stroke-width="1"/>'
        f'<line x1="0" y1="{mid_y:.1f}" x2="{CW}" y2="{mid_y:.1f}" stroke="#1e293b" stroke-width="0.5" stroke-dasharray="3 3"/>'
        f'{svg_bars}'
        f'<polyline points="{net_pts}" fill="none" stroke="{line_color}" stroke-width="1.5" stroke-linejoin="round" stroke-linecap="round"/>'
        f'<circle cx="{29*slot+slot/2:.1f}" cy="{last_y:.1f}" r="3" fill="{line_color}"/>'
        f'{svg_labels}'
        f'</svg>'
    )

    # ── Net Worth donut SVG ───────────────────────────────────────────────────
    NW = stats["total_net_worth"] or 1
    nw_parts = [
        ("Cash",       stats["cash_balance"],    "#22d3ee"),
        ("Inventory",  stats["inventory_value"], "#22c55e"),
        ("Land",       stats["land_value"],      "#84cc16"),
        ("Businesses", stats["business_value"],  "#f59e0b"),
        ("Shares",     stats["share_value"],     "#3b82f6"),
        ("Districts",  stats["district_value"],  "#a855f7"),
    ]
    R, CIRC = 46, 289.0  # 2π×46
    cx2, cy2 = 60, 60
    donut_segs = ""
    donut_legend = ""
    cum_arc = 0.0
    for lbl, val, col in nw_parts:
        if val <= 0:
            continue
        pct = val / abs(NW)
        dash = min(CIRC * pct, CIRC)
        gap = CIRC - dash
        offset = CIRC / 4 - cum_arc
        donut_segs += (
            f'<circle cx="{cx2}" cy="{cy2}" r="{R}" fill="none" stroke="{col}" '
            f'stroke-width="14" stroke-dasharray="{dash:.2f} {gap:.2f}" '
            f'stroke-dashoffset="{offset:.2f}"/>'
        )
        donut_legend += (
            f'<div style="display:flex;align-items:center;gap:6px;margin-bottom:5px;">'
            f'<div style="width:10px;height:10px;border-radius:2px;background:{col};flex-shrink:0;"></div>'
            f'<span style="color:#94a3b8;font-size:0.78rem;">{lbl}</span>'
            f'<span style="color:#e2e8f0;font-size:0.78rem;margin-left:auto;">{fmt_usd(val, disp)}</span>'
            f'</div>'
        )
        cum_arc += dash
    donut_svg = (
        f'<svg viewBox="0 0 120 120" style="width:120px;height:120px;flex-shrink:0;">'
        f'<circle cx="{cx2}" cy="{cy2}" r="{R}" fill="none" stroke="#1e293b" stroke-width="14"/>'
        f'{donut_segs}'
        f'<text x="{cx2}" y="{cy2-6}" text-anchor="middle" font-size="8" fill="#64748b">NET</text>'
        f'<text x="{cx2}" y="{cy2+8}" text-anchor="middle" font-size="9" fill="#e2e8f0" font-weight="bold">WORTH</text>'
        f'</svg>'
    )

    # ── Category breakdown bars ───────────────────────────────────────────────
    all_grps = sorted(
        set(list(cat_income) + list(cat_expense)),
        key=lambda g: cat_income.get(g, 0) + cat_expense.get(g, 0),
        reverse=True
    )[:8]
    cat_max = max(
        (max((cat_income.get(g, 0) for g in all_grps), default=0),
         max((cat_expense.get(g, 0) for g in all_grps), default=0)),
        default=1
    ) or 1
    cat_html = ""
    CAT_COLORS = {
        "market": "#3b82f6", "share": "#6366f1", "bond": "#0891b2",
        "dividend": "#22c55e", "land": "#84cc16", "district": "#f59e0b",
        "city": "#38bdf8", "county": "#92400e", "crypto": "#f59e0b",
        "governance": "#6366f1", "corporate": "#64748b", "treasury": "#10b981",
        "resource": "#0ea5e9", "business": "#7c3aed", "cash": "#22c55e",
        "p2p": "#ec4899", "tax": "#f97316", "inheritance": "#a78bfa",
        "forex": "#f59e0b", "other": "#475569",
    }
    for grp in all_grps:
        inc = cat_income.get(grp, 0)
        exp = cat_expense.get(grp, 0)
        col = CAT_COLORS.get(grp, "#475569")
        inc_w = inc / cat_max * 100
        exp_w = exp / cat_max * 100
        cat_html += f"""
        <div style="margin-bottom:12px;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
            <span style="font-size:0.78rem;font-weight:600;color:{col};text-transform:uppercase;letter-spacing:0.05em;">{grp}</span>
            <div style="font-size:0.75rem;font-family:monospace;">
              {f'<span style="color:#22c55e;">+{fmt_usd(inc,disp)}</span>' if inc else ''}
              {f'<span style="color:#334155;padding:0 4px;">·</span><span style="color:#ef4444;">-{fmt_usd(exp,disp)}</span>' if exp else ''}
            </div>
          </div>
          <div style="height:6px;background:#0f172a;border-radius:3px;overflow:hidden;position:relative;">
            {f'<div style="position:absolute;left:0;top:0;height:100%;width:{inc_w:.1f}%;background:{col};opacity:0.9;border-radius:3px;"></div>' if inc else ''}
          </div>
          {f'<div style="height:4px;background:#0f172a;border-radius:3px;overflow:hidden;margin-top:2px;position:relative;"><div style="position:absolute;left:0;top:0;height:100%;width:{exp_w:.1f}%;background:#ef4444;opacity:0.7;border-radius:3px;"></div></div>' if exp else ''}
        </div>"""
    if not cat_html:
        cat_html = '<p style="color:#475569;font-size:0.85rem;">No activity in the last 30 days.</p>'

    # ── Cost averages table ───────────────────────────────────────────────────
    avg_rows = ""
    for a in averages:
        bar_w = min(a.total_spent / (averages[0].total_spent or 1) * 100, 100) if averages else 0
        avg_rows += f"""
        <tr>
          <td style="padding:8px 10px;color:#e2e8f0;font-size:0.83rem;">{a.item_type.replace('_',' ').title()}</td>
          <td style="padding:8px 10px;text-align:right;font-family:monospace;color:#22d3ee;font-size:0.83rem;">{fmt_usd(a.average_cost,disp)}</td>
          <td style="padding:8px 10px;text-align:right;color:#64748b;font-size:0.8rem;">{a.total_quantity:,.0f}</td>
          <td style="padding:8px 10px;text-align:right;font-family:monospace;color:#94a3b8;font-size:0.8rem;">{fmt_usd(a.total_spent,disp)}</td>
          <td style="padding:8px 10px;min-width:80px;">
            <div style="height:4px;background:#1e293b;border-radius:2px;overflow:hidden;">
              <div style="height:100%;width:{bar_w:.1f}%;background:#22d3ee;border-radius:2px;"></div>
            </div>
          </td>
        </tr>"""

    # ── Transaction ledger rows ───────────────────────────────────────────────
    import html as _html_mod
    def _tx_row(tx) -> str:
        tt = tx.transaction_type or ""
        icon = TYPE_ICONS.get(tt) or next((v for k, v in TYPE_ICONS.items() if tt.startswith(k)), "📝")
        col = TYPE_BADGE_COLORS.get(tt) or next(
            (v for k, v in TYPE_BADGE_COLORS.items() if tt.startswith(k)), "#475569")
        tabs_json = json.dumps(type_to_tabs.get(tt, []))
        desc_full = tx.description or tt
        desc_short = (desc_full[:72] + "…") if len(desc_full) > 72 else desc_full
        is_income = tx.amount > 0
        is_expense = tx.amount < 0
        amt_col = "#22c55e" if is_income else ("#ef4444" if is_expense else "#475569")
        amt_sign = "+" if is_income else ("")
        amt_str = f"{amt_sign}{fmt_usd(abs(tx.amount), disp)}" if tx.amount != 0 else "—"
        # item metadata
        meta = ""
        if getattr(tx, "item_type", None):
            parts = [f'<span style="color:#7dd3fc;">{tx.item_type.replace("_"," ")}</span>']
            qty = getattr(tx, "quantity", 0.0)
            unit_price = getattr(tx, "unit_price", None)
            if qty: parts.append(f'× {qty:,.2f}')
            if unit_price is not None: parts.append(f'@ {fmt_usd(unit_price, disp, precision=4)}')
            meta = f'<div style="font-size:0.75rem;color:#64748b;margin-top:2px;">{" ".join(parts)}</div>'
        ts_str = _rel_time(tx.timestamp)
        ts_abs = tx.timestamp.strftime('%Y-%m-%d %H:%M UTC') if tx.timestamp else ""
        ts_epoch = int(tx.timestamp.timestamp()) if tx.timestamp else 0
        desc_escaped = _html_mod.escape(desc_full.lower())
        return (
            f'<div class="txr" data-type="{tt}" data-tabs=\'{tabs_json}\' data-desc="{desc_escaped}"'
            f' data-amount="{tx.amount:.4f}" data-ts="{ts_epoch}">'
            # left accent bar
            f'<div style="width:3px;background:{col};border-radius:3px 0 0 3px;flex-shrink:0;align-self:stretch;"></div>'
            # icon circle
            f'<div style="width:36px;height:36px;border-radius:50%;background:{col}22;border:1px solid {col}55;'
            f'display:flex;align-items:center;justify-content:center;font-size:1.1rem;flex-shrink:0;">{icon}</div>'
            # main content
            f'<div style="flex:1;min-width:0;">'
            f'<div style="font-size:0.85rem;color:#e2e8f0;font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{desc_short}</div>'
            f'{meta}'
            f'<div style="display:flex;align-items:center;gap:8px;margin-top:3px;">'
            f'<span style="font-size:0.72rem;color:#475569;" title="{ts_abs}">{ts_str}</span>'
            f'<span style="font-size:0.7rem;padding:1px 6px;border-radius:10px;background:{col}22;'
            f'color:{col};border:1px solid {col}44;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:120px;">{tt}</span>'
            f'</div></div>'
            # amount
            f'<div style="text-align:right;flex-shrink:0;">'
            f'<div style="font-size:0.9rem;font-weight:700;font-family:monospace;color:{amt_col};">{amt_str}</div>'
            f'</div>'
            f'</div>'
        )

    tx_html = "".join(_tx_row(tx) for tx in txs)

    # ── Filter chip counts ────────────────────────────────────────────────────
    TABS = [
        ("all",             "All",             tx_count),
        # — Trading & Markets —
        ("market",          "Market",          count_by_tab.get("market", 0)),
        ("district_market", "District Market", count_by_tab.get("district_market", 0)),
        ("shares",          "Shares",          count_by_tab.get("shares", 0)),
        ("dividend",        "Dividends",       count_by_tab.get("dividend", 0)),
        ("bonds",           "Bonds",           count_by_tab.get("bonds", 0)),
        ("bond_income",     "Bond Payouts",    count_by_tab.get("bond_income", 0)),
        ("crypto",          "Crypto",          count_by_tab.get("crypto", 0)),
        ("forex",           "Forex",           count_by_tab.get("forex", 0)),
        # — Business & Income —
        ("retail",          "Retail Sales",    count_by_tab.get("retail", 0)),
        ("resources",       "Resources",       count_by_tab.get("resources", 0)),
        ("cash",            "Cash Flows",      count_by_tab.get("cash", 0)),
        ("treasury",        "Treasury",        count_by_tab.get("treasury", 0)),
        # — Land & Property —
        ("land",            "Land",            count_by_tab.get("land", 0)),
        ("mining",          "Mining",          count_by_tab.get("mining", 0)),
        # — District & City Government —
        ("district",        "District",        count_by_tab.get("district", 0)),
        ("city",            "City/County",     count_by_tab.get("city", 0)),
        ("governance",      "Governance",      count_by_tab.get("governance", 0)),
        ("tax",             "Tax",             count_by_tab.get("tax", 0)),
        # — P2P Contracts —
        ("p2p",             "P2P (All)",       count_by_tab.get("p2p", 0)),
        ("p2p_contracts",   "P2P Contracts",   count_by_tab.get("p2p_contracts", 0)),
        ("p2p_fees",        "P2P Fees",        count_by_tab.get("p2p_fees", 0)),
        # — Corporate & Legal —
        ("corporate",       "Corporate",       count_by_tab.get("corporate", 0)),
        ("inheritance",     "Inheritance",     count_by_tab.get("inheritance", 0)),
    ]
    def _chip(k, label, cnt):
        active_cls = " txchip-active" if k == "all" else ""
        # Always show all chips; dim zero-count ones so users can see every category
        if cnt:
            badge = (f'<span style="margin-left:4px;padding:0 5px;background:rgba(255,255,255,0.12);'
                     f'border-radius:8px;font-size:0.7rem;">{cnt}</span>')
            dim_style = ""
        else:
            badge = ""
            dim_style = ' style="opacity:0.35;cursor:default;"'
        return (f'<button class="txchip{active_cls}"{dim_style} onclick="txFilter(\'{k}\',this)" data-tab="{k}">'
                f'{label}{badge}</button>')
    filter_chips_html = "".join(_chip(k, label, cnt) for k, label, cnt in TABS)

    # ── Net worth multi-currency ──────────────────────────────────────────────
    currency_rows_html = ""
    for code, sym, bal, usd_val in currency_rows:
        currency_rows_html += (
            f'<div style="display:flex;justify-content:space-between;align-items:center;'
            f'padding:5px 0;border-bottom:1px solid #1e293b;">'
            f'<span style="font-size:0.78rem;color:#64748b;">{code}</span>'
            f'<span style="font-size:0.82rem;font-family:monospace;color:#22d3ee;">'
            f'{sym}{bal:,.4f} <span style="color:#475569;font-size:0.75rem;">≈ {fmt_usd(usd_val,disp)}</span></span>'
            f'</div>'
        )

    net_color = "#22c55e" if net >= 0 else "#ef4444"
    net_sign = "+" if net >= 0 else ""
    biggest_str = (
        f'{fmt_usd(abs(biggest_tx.amount), disp)} · {(biggest_tx.description or biggest_tx.transaction_type or "")[:40]}'
        if biggest_tx else "—"
    )

    body = f"""
<style>
.fin-kpi {{
  background:linear-gradient(135deg,#0f172a 0%,#1e293b 100%);
  border:1px solid #1e293b; border-radius:10px; padding:16px 20px;
  position:relative; overflow:hidden;
}}
.fin-kpi::before {{
  content:''; position:absolute; inset:0; border-radius:10px;
  background:var(--kpi-glow,transparent); opacity:0.04; pointer-events:none;
}}
.fin-kpi-label {{ font-size:0.7rem; text-transform:uppercase; letter-spacing:0.08em; color:#64748b; margin-bottom:6px; }}
.fin-kpi-val {{ font-size:1.4rem; font-weight:800; font-family:monospace; line-height:1.1; }}
.fin-kpi-sub {{ font-size:0.72rem; color:#475569; margin-top:4px; }}
.txr {{
  display:flex; align-items:center; gap:10px;
  padding:10px 14px 10px 0;
  border-bottom:1px solid #0f172a;
  transition:background 0.15s;
  cursor:default;
}}
.txr:hover {{ background:#0f172a; }}
.txr:last-child {{ border-bottom:none; }}
.txchip {{
  display:inline-flex; align-items:center;
  padding:4px 10px; border-radius:14px; font-size:0.78rem; font-weight:500;
  border:1px solid #1e293b; background:#0f172a; color:#64748b;
  cursor:pointer; transition:all 0.15s; white-space:nowrap;
}}
.txchip:hover {{ border-color:#334155; color:#94a3b8; }}
.txchip-active {{ background:#1e3a5f; border-color:#3b82f6; color:#93c5fd; }}
.txsort {{
  display:inline-flex; align-items:center;
  padding:3px 9px; border-radius:12px; font-size:0.75rem; font-weight:500;
  border:1px solid #1e293b; background:#0f172a; color:#475569;
  cursor:pointer; transition:all 0.15s; white-space:nowrap;
}}
.txsort:hover {{ border-color:#334155; color:#94a3b8; }}
.txsort-active {{ background:#1a2744; border-color:#6366f1; color:#a5b4fc; }}
.avg-tbl {{ width:100%; border-collapse:collapse; }}
.avg-tbl thead th {{
  padding:8px 10px; text-align:left; font-size:0.72rem; font-weight:600;
  text-transform:uppercase; letter-spacing:0.06em; color:#475569;
  border-bottom:1px solid #1e293b;
}}
.avg-tbl tbody tr:hover td {{ background:#0f172a22; }}
</style>

<div style="margin-bottom:6px;display:flex;align-items:baseline;gap:12px;">
  <h1 style="margin:0;font-size:1.4rem;color:#f1f5f9;font-weight:800;">Financial Statement</h1>
  <span style="font-size:0.78rem;color:#475569;">{player.business_name}</span>
</div>

<!-- KPI strip -->
<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px;">
  <div class="fin-kpi" style="--kpi-glow:#22d3ee;">
    <div class="fin-kpi-label">Net Worth</div>
    <div class="fin-kpi-val" style="color:#22d3ee;">{fmt_usd(stats['total_net_worth'],disp)}</div>
    <div class="fin-kpi-sub">All assets combined</div>
  </div>
  <div class="fin-kpi" style="--kpi-glow:#22c55e;">
    <div class="fin-kpi-label">30-Day Income</div>
    <div class="fin-kpi-val" style="color:#22c55e;">+{fmt_usd(total_income,disp)}</div>
    <div class="fin-kpi-sub">{tx_count} transactions</div>
  </div>
  <div class="fin-kpi" style="--kpi-glow:#ef4444;">
    <div class="fin-kpi-label">30-Day Expenses</div>
    <div class="fin-kpi-val" style="color:#ef4444;">-{fmt_usd(abs(total_expenses),disp)}</div>
    <div class="fin-kpi-sub">Costs & purchases</div>
  </div>
  <div class="fin-kpi" style="--kpi-glow:{net_color};">
    <div class="fin-kpi-label">Net Flow</div>
    <div class="fin-kpi-val" style="color:{net_color};">{net_sign}{fmt_usd(net,disp)}</div>
    <div class="fin-kpi-sub">Largest: {biggest_str[:36]}</div>
  </div>
</div>

<!-- Cash flow chart -->
<div class="card" style="margin-bottom:16px;cursor:default;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
    <div>
      <div style="font-size:0.85rem;font-weight:700;color:#e2e8f0;">30-Day Cash Flow</div>
      <div style="font-size:0.72rem;color:#475569;margin-top:2px;">
        <span style="color:#22c55e;">■</span> Income &nbsp;
        <span style="color:#ef4444;">■</span> Expenses &nbsp;
        <span style="color:{line_color};">— </span> Cumulative net
      </div>
    </div>
    <div style="text-align:right;font-size:0.75rem;color:#475569;">
      Peak day: {fmt_usd(max_daily_val,disp)}
    </div>
  </div>
  {chart_svg}
</div>

<!-- Two-column: Category breakdown + Net Worth donut -->
<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px;">

  <div class="card" style="cursor:default;">
    <div style="font-size:0.85rem;font-weight:700;color:#e2e8f0;margin-bottom:12px;">Income &amp; Expense by Category</div>
    {cat_html}
  </div>

  <div class="card" style="cursor:default;">
    <div style="font-size:0.85rem;font-weight:700;color:#e2e8f0;margin-bottom:12px;">Net Worth Breakdown</div>
    <div style="display:flex;gap:16px;align-items:flex-start;">
      {donut_svg}
      <div style="flex:1;min-width:0;padding-top:4px;">{donut_legend}</div>
    </div>
    {currency_rows_html}
  </div>
</div>

<!-- Cost averages -->
{"" if not averages else f'''
<div class="card" style="margin-bottom:16px;cursor:default;overflow-x:auto;">
  <div style="font-size:0.85rem;font-weight:700;color:#e2e8f0;margin-bottom:10px;">Purchase Cost Averages</div>
  <table class="avg-tbl">
    <thead>
      <tr>
        <th>Item</th>
        <th style="text-align:right;">Avg Cost</th>
        <th style="text-align:right;">Qty</th>
        <th style="text-align:right;">Total Spent</th>
        <th>Relative</th>
      </tr>
    </thead>
    <tbody>{avg_rows}</tbody>
  </table>
</div>'''}

<!-- Transaction ledger -->
<div class="card" style="cursor:default;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;flex-wrap:wrap;gap:10px;">
    <div>
      <div style="font-size:0.85rem;font-weight:700;color:#e2e8f0;">Transaction Ledger</div>
      <div style="font-size:0.72rem;color:#475569;margin-top:2px;">Last {tx_count} transactions</div>
    </div>
    <input type="text" id="tx-search" placeholder="Search…" oninput="txSearch(this.value)"
      style="padding:6px 12px;background:#0f172a;border:1px solid #1e293b;color:#f1f5f9;
             border-radius:20px;font-size:0.82rem;width:200px;outline:none;">
  </div>

  <!-- Sort controls -->
  <div style="display:flex;align-items:center;gap:6px;margin-bottom:10px;flex-wrap:wrap;">
    <span style="font-size:0.72rem;color:#475569;letter-spacing:0.05em;text-transform:uppercase;">Sort:</span>
    <button class="txsort txsort-active" onclick="txSortBy('newest',this)">Newest first</button>
    <button class="txsort" onclick="txSortBy('oldest',this)">Oldest first</button>
    <button class="txsort" onclick="txSortBy('amount_desc',this)">$ High → Low</button>
    <button class="txsort" onclick="txSortBy('amount_asc',this)">$ Low → High</button>
  </div>

  <!-- Filter chips -->
  <div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:14px;">
    {filter_chips_html}
  </div>

  <!-- Ledger rows -->
  <div id="transactions" style="border:1px solid #1e293b;border-radius:8px;overflow:hidden;">
    {tx_html if tx_html else '<div style="padding:32px;text-align:center;color:#475569;">No transactions recorded yet.</div>'}
  </div>

  <div id="tx-pagination" style="display:flex;justify-content:center;align-items:center;gap:6px;margin-top:14px;flex-wrap:wrap;"></div>
</div>

<script>
(function() {{
  var _filter = 'all', _search = '', _page = 0, PAGE = 50;
  var _sort = 'newest';
  var _all = [], _vis = [];

  function _init() {{
    _all = Array.prototype.slice.call(
      document.querySelectorAll('#transactions .txr')
    );
  }}

  function _sortAll() {{
    _all.sort(function(a, b) {{
      var at = +(a.dataset.ts || 0), bt = +(b.dataset.ts || 0);
      var aa = Math.abs(+(a.dataset.amount || 0));
      var ba = Math.abs(+(b.dataset.amount || 0));
      if (_sort === 'oldest')      return at - bt;
      if (_sort === 'amount_desc') return ba - aa;
      if (_sort === 'amount_asc')  return aa - ba;
      return bt - at; // newest (default)
    }});
  }}

  function _build() {{
    _sortAll();
    _vis = _all.filter(function(el) {{
      var tabs = [];
      try {{ tabs = JSON.parse(el.dataset.tabs || '[]'); }} catch(e) {{}}
      var tm = _filter === 'all' || tabs.indexOf(_filter) !== -1;
      var sm = !_search ||
               (el.dataset.desc || '').indexOf(_search) !== -1 ||
               (el.dataset.type || '').indexOf(_search) !== -1;
      return tm && sm;
    }});
    _page = 0;
    _render();
  }}

  function _render() {{
    var cont = document.getElementById('transactions');
    // Hide every row first
    _all.forEach(function(el) {{ el.style.display = 'none'; }});
    // Show + re-order the current page slice via appendChild
    _vis.slice(_page * PAGE, _page * PAGE + PAGE).forEach(function(el) {{
      el.style.display = '';
      cont.appendChild(el);
    }});
    _pages();
  }}

  function _pages() {{
    var tp = Math.ceil(_vis.length / PAGE);
    var c = document.getElementById('tx-pagination');
    if (!c) return;
    var total_lbl = '<span style="color:#475569;font-size:0.78rem;margin-left:4px;">'
                    + _vis.length + ' of {tx_count}</span>';
    if (tp <= 1) {{ c.innerHTML = total_lbl; return; }}
    var h = '';
    for (var i = 0; i < tp; i++) {{
      var a = i === _page;
      h += '<button onclick="txGoto(' + i + ')" style="padding:4px 12px;border:none;border-radius:14px;cursor:pointer;font-size:0.8rem;'
        + (a ? 'background:#3b82f6;color:#fff;' : 'background:#1e293b;color:#64748b;') + '">' + (i+1) + '</button>';
    }}
    h += total_lbl;
    c.innerHTML = h;
  }}

  window.txGoto = function(p) {{
    _page = p; _render();
    document.getElementById('transactions').scrollIntoView({{behavior:'smooth',block:'start'}});
  }};

  window.txFilter = function(k, btn) {{
    _filter = k;
    document.querySelectorAll('.txchip').forEach(function(b) {{ b.classList.remove('txchip-active'); }});
    if (btn) btn.classList.add('txchip-active');
    _build();
  }};

  window.txSortBy = function(s, btn) {{
    _sort = s;
    document.querySelectorAll('.txsort').forEach(function(b) {{ b.classList.remove('txsort-active'); }});
    if (btn) btn.classList.add('txsort-active');
    _build();
  }};

  window.txSearch = function(v) {{ _search = v.toLowerCase(); _build(); }};

  _init();
  _build();
}})();
</script>
"""

    return HTMLResponse(stats_shell("My Business", body, player.cash_balance, player.business_name, player.id))


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
    
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)
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
            <td>{fmt_usd(s.total_net_worth, disp, precision=0)}</td>
            <td>{fmt_usd(s.cash_balance, disp, precision=0)}</td>
            <td>{fmt_usd(s.land_value, disp, precision=0)}</td>
            <td>{fmt_usd(s.inventory_value, disp, precision=0)}</td>
            <td>{fmt_usd(s.share_value, disp, precision=0)}</td>
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
    
    return HTMLResponse(stats_shell("Leaderboard", body, player.cash_balance, player.business_name, player.id))


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
    
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)
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
    
    # Build business list — "All" merges both regular and district businesses
    biz_html = ""
    if category == "district":
        all_businesses = list(district_businesses.items())
    elif category == "all":
        # Merge both dicts; district businesses are tagged so badge reflects correctly
        merged = dict(business_types)
        merged.update(district_businesses)
        all_businesses = list(merged.items())
    else:
        all_businesses = [(k, v) for k, v in business_types.items() if v.get("class") == category]

    district_keys = set(district_businesses.keys())
    for key, biz in sorted(all_businesses, key=lambda x: x[1].get("name", x[0])):
        name = biz.get("name", key.replace("_", " ").title())
        desc = biz.get("description", "")[:80]
        cost = biz.get("startup_cost", 0)
        cycles = biz.get("cycles_to_complete", 1)
        biz_class = biz.get("class", "production")
        is_dist_biz = key in district_keys

        badge_class = "badge-green" if biz_class == "production" else "badge-blue" if biz_class == "retail" else "badge-gray"
        dist_tag = '<span class="badge badge-gray" style="margin-left:4px;font-size:0.6rem;">district</span>' if is_dist_biz else ""

        biz_html += f"""
        <a href="/stats/business/{key}" class="card" style="text-decoration: none;">
            <div class="card-header">
                <span class="card-title">{name}</span>
                <span>{dist_tag}<span class="badge {badge_class}">{biz_class}</span></span>
            </div>
            <div class="card-subtitle">{desc}</div>
            <div class="stat-row" style="margin-top: 8px;">
                <span class="stat-label">Startup</span>
                <span class="stat-value">{fmt_usd(cost, disp, precision=0)}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Cycle Time</span>
                <span class="stat-value">{cycles:,} ticks</span>
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
        {biz_html if biz_html else '<p style="color:#64748b;grid-column:1/-1;">No businesses in this category.</p>'}
    </div>
    <p id="biz-no-results" style="color:#64748b;display:none;margin-top:12px;">No businesses match your search.</p>

    <script>
    function searchBiz(query) {{
        const cards = document.querySelectorAll('#biz-grid .card');
        const q = query.toLowerCase().trim();
        let visible = 0;
        cards.forEach(card => {{
            const match = !q || card.textContent.toLowerCase().includes(q);
            card.style.display = match ? '' : 'none';
            if (match) visible++;
        }});
        document.getElementById('biz-no-results').style.display = (q && visible === 0) ? '' : 'none';
    }}
    </script>
    """
    
    return HTMLResponse(stats_shell("Businesses", body, player.cash_balance, player.business_name, player.id))


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
    
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)
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
        return HTMLResponse(
            stats_shell("Not Found", '<h1 class="page-title">Business not found</h1><a href="/stats/businesses">← Back to Businesses</a>', player.cash_balance, player.business_name, player.id),
            status_code=404,
        )
    
    name = biz.get("name", business_key.replace("_", " ").title())
    desc = biz.get("description", "")
    cost = biz.get("startup_cost", 0)
    cycles = biz.get("cycles_to_complete", 1)
    wage = biz.get("base_wage_cost", 0)
    biz_class = biz.get("class", "production")
    cycles_display = f"{cycles:,} ticks"
    
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
    
    dist_badge = '<span class="badge badge-gray" style="margin-left:6px;">District Business</span>' if is_district else ""
    body = f"""
    <h1 class="page-title">{name}{dist_badge}</h1>
    <p style="color: #94a3b8; margin-bottom: 24px;">{desc}</p>

    <div class="grid">
        <div class="card" style="cursor: default;">
            <div class="card-header">
                <span class="card-title">Statistics</span>
                <span class="badge {'badge-green' if biz_class == 'production' else 'badge-blue'}">{biz_class}</span>
            </div>
            <div class="stat-row"><span class="stat-label">Startup Cost</span><span class="stat-value">{fmt_usd(cost, disp, precision=0)}</span></div>
            <div class="stat-row"><span class="stat-label">Cycle Time</span><span class="stat-value">{cycles_display}</span></div>
            <div class="stat-row"><span class="stat-label">Wage Cost</span><span class="stat-value">{fmt_usd(wage, disp)}/cycle</span></div>
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

    return HTMLResponse(stats_shell(name, body, player.cash_balance, player.business_name, player.id))


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
    
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)
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
            price_str = f"{fmt_usd(price, disp)}" if price else "No market"
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
    
    return HTMLResponse(stats_shell("Items", body, player.cash_balance, player.business_name, player.id))


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
    
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)
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
        return HTMLResponse(stats_shell("Not Found", "<h1>Item not found</h1>", player.cash_balance, player.business_name, player.id))
    
    name = item.get("name", item_key.replace("_", " ").title())
    desc = item.get("description", "")
    cat = item.get("category", "misc")
    
    # Get market price and history
    try:
        from market import get_market_price, Trade
        price = get_market_price(item_key)
        price_str = f"{fmt_usd(price, disp)}" if price else "No market data"
        
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
            bars.append(f'<div class="mini-chart-bar" style="height: {height}px;" title="{fmt_usd(t.price, disp)}"></div>')
        
        chart_html = f"""
        <div class="chart-container">
            <div style="color: #94a3b8; font-size: 0.75rem; margin-bottom: 8px;">7-Day Price History</div>
            <div class="mini-chart">{''.join(bars)}</div>
            <div style="display: flex; justify-content: space-between; color: #64748b; font-size: 0.7rem; margin-top: 4px;">
                <span>Low: {fmt_usd(min_price, disp)}</span>
                <span>High: {fmt_usd(max_price, disp)}</span>
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
        <div class="stat-row"><span class="stat-label">Your Avg Cost</span><span class="stat-value">{fmt_usd(avg.average_cost, disp)}/unit</span></div>
        <div class="stat-row"><span class="stat-label">Total Acquired</span><span class="stat-value">{avg.total_quantity:,.0f} units</span></div>
        <div class="stat-row"><span class="stat-label">Total Spent</span><span class="stat-value">{fmt_usd(avg.total_spent, disp)}</span></div>
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

    return HTMLResponse(stats_shell(name, body, player.cash_balance, player.business_name, player.id))


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

    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)
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
        if not isinstance(biz_cfg, dict):
            continue
        for terrain in biz_cfg.get("allowed_terrain", []):
            terrain_to_biz.setdefault(terrain, []).append(biz_cfg.get("name", biz_key))

    # Build a lookup: terrain_key → list of (biz_name, biz_key) for detail links
    terrain_to_biz_full: Dict[str, list] = {}
    for biz_key, biz_cfg in dist_biz.items():
        if not isinstance(biz_cfg, dict):
            continue
        for terrain in biz_cfg.get("allowed_terrain", []):
            terrain_to_biz_full.setdefault(terrain, []).append((biz_cfg.get("name", biz_key), biz_key))

    cards = ""
    for dtype, cfg in sorted(DISTRICT_TYPES.items(), key=lambda x: x[1]["name"]):
        terrain_key = cfg.get("district_terrain", f"district_{dtype}")
        base_tax = cfg["base_tax"]
        monthly_ex = base_tax * 1.0 * DISTRICT_TAX_MULTIPLIER  # size=1 example
        allowed = ", ".join(t.replace("_", " ").title() for t in cfg.get("allowed_terrain", []))
        desc_text = cfg.get("description", "")
        businesses_here = terrain_to_biz_full.get(terrain_key, [])
        if businesses_here:
            biz_list = "".join(
                f'<li><a href="/stats/business/{bk}" style="color:#38bdf8;font-size:0.7rem;">{bn}</a></li>'
                for bn, bk in sorted(businesses_here)
            )
        else:
            biz_list = '<li style="color:#475569;font-size:0.7rem;">No special businesses</li>'

        cards += f"""
        <div class="card" style="cursor:default;">
            <div class="card-header">
                <span class="card-title">{cfg["name"]}</span>
                <span style="font-size:0.7rem;color:#f59e0b;">{fmt_usd(monthly_ex, disp, precision=0)}/mo*</span>
            </div>
            {('<div class="card-subtitle" style="margin-bottom:10px;">' + desc_text + "</div>") if desc_text else ""}
            <div class="stat-row"><span class="stat-label">Base Tax</span><span class="stat-value">{fmt_usd(base_tax, disp, precision=0)}/mo × {int(DISTRICT_TAX_MULTIPLIER)}</span></div>
            <div class="stat-row"><span class="stat-label">Terrain</span><span class="stat-value" style="font-size:0.75rem;">{allowed}</span></div>
            <div class="stat-row" style="align-items:flex-start;border-bottom:none;">
                <span class="stat-label">Businesses</span>
                <ul style="list-style:none;text-align:right;margin:0;padding:0;">{biz_list}</ul>
            </div>
        </div>"""

    body = f"""
    <h1 class="page-title">🏙️ Districts Encyclopedia</h1>
    <p style="color:#64748b;font-size:0.8rem;margin-bottom:16px;">
        Districts are formed by merging land plots (Fibonacci sequence). Tax = Base Tax × Size × {int(DISTRICT_TAX_MULTIPLIER)}.
        *Example shows size=1, no modifiers.
    </p>
    <div class="grid">{cards}</div>
    <a href="/stats" style="display:inline-block;margin-top:16px;">← Back to Analytics</a>
    """
    return HTMLResponse(stats_shell("Districts", body, player.cash_balance, player.business_name, player.id))


# /stats/production-costs is served by ux.py (production_costs.py calculator)
# The old implementation below was removed — it depended on item_costs.json which no longer exists.
# Redirecting to the canonical implementation for safety.

@router.get("/stats/production-costs-legacy", response_class=HTMLResponse)
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

    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)
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
            _zero = fmt_usd(0, disp)
            cost_str = f'<span style="color:#22c55e;">{_zero}</span>'
            cost_per = f'<span style="color:#22c55e;">{_zero}</span>'
        else:
            cost_str = f'<span style="color:#e5e7eb;">{fmt_usd(cost, disp, precision=4)}</span>' if cost < 1 else f'<span style="color:#e5e7eb;">{fmt_usd(cost, disp)}</span>'
            out_qty = item.get("output_qty") or 1
            per = cost / out_qty
            cost_per = f'{fmt_usd(per, disp, precision=4)}' if per < 1 else f'{fmt_usd(per, disp)}'

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
    return HTMLResponse(stats_shell("Production Costs", body, player.cash_balance, player.business_name, player.id))


# ============================================================
# WIKI — Wadsworth living encyclopedia
# 10 / 30 / 60 colour rule:
#   60 % deep navy  #04070f / #090e1c
#   30 % slate      #111c35 / #0c1528 / #1d2f55
#   10 % accents    #f5a855 orange | #f5d76e yellow | #90c4f0 blue
# ============================================================

_WIKI_BUFF_LABELS: Dict[str, tuple] = {
    "output":                  ("⬆ Output",         True),
    "wage_savings":            ("⬇ Wages",           True),
    "input_savings":           ("⬇ Input Costs",     True),
    "cycle_speed":             ("⚡ Cycle Speed",     True),
    "market_fee_reduction":    ("⬇ Market Fees",     True),
    "license_production":      ("🔖 Licenses/tick",  False),
    "construction_speed":      ("⬆ Build Speed",     True),
    "loan_interest_reduction": ("⬇ Loan Interest",   True),
}
_WIKI_DEBUFF_LABELS: Dict[str, tuple] = {
    "sales_tax":    ("⬆ Sales Tax",  True),
    "wage_penalty": ("⬆ Wage Cost",  True),
    "input_penalty":("⬆ Input Cost", True),
}


def _wiki_buff(key: str, val: float) -> str:
    lbl, pct = _WIKI_BUFF_LABELS.get(key, (key.replace("_", " ").title(), True))
    v = f"{val*100:.1f}%/lv" if pct else f"{val:g}/lv"
    return f'<span class="buff">{lbl} {v}</span>'


def _wiki_debuff(key: str, val: float) -> str:
    lbl, pct = _WIKI_DEBUFF_LABELS.get(key, (key.replace("_", " ").title(), True))
    v = f"{val*100:.1f}%/lv" if pct else f"{val:g}/lv"
    return f'<span class="debuff">{lbl} {v}</span>'


def wiki_shell(title: str, body: str, player_name: str = "", active: str = "") -> str:
    """Beautiful wiki wrapper — 10/30/60 pastel orange/yellow/blue palette."""
    _NAV_ITEMS = [
        ("hub",           "/stats/wiki",               "◈ Home"),
        ("businesses",    "/stats/wiki/businesses",    "🏭 Businesses"),
        ("districts",     "/stats/wiki/districts",     "🏙️ Districts"),
        ("items",         "/stats/wiki/items",         "📦 Items"),
        ("city_projects", "/stats/wiki/city_projects", "🏗️ City Projects"),
        ("executives",    "/stats/wiki/executives",    "👔 Executives"),
    ]
    nav = "".join(
        f'<a href="{hr}" class="{"active" if active == k else ""}">{lb}</a>'
        for k, hr, lb in _NAV_ITEMS
    )
    player_el = (f"<span class='wh-player'>{player_name}</span>" if player_name else "")

    # CSS as a plain string — no f-string escaping needed for braces
    css = """
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
body{background:#04070f;color:#dde8ff;font-family:'Segoe UI',system-ui,sans-serif;font-size:14px;line-height:1.6;min-height:100vh;}
a{color:#90c4f0;text-decoration:none;}a:hover{color:#f5d76e;}
/* HEADER */
.wh{background:#090e1c;border-bottom:2px solid transparent;border-image:linear-gradient(90deg,#f5a855,#f5d76e 50%,#90c4f0) 1;padding:0 24px;height:56px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100;}
.wh-logo{font-size:1.05rem;font-weight:800;background:linear-gradient(90deg,#f5a855,#f5d76e 60%,#90c4f0);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;letter-spacing:-0.02em;}
.wh-right{display:flex;align-items:center;gap:12px;font-size:0.82rem;}
.wh-player{color:#607098;}
.wh-btn{padding:5px 12px;border:1px solid #1d2f55;border-radius:6px;color:#607098;font-size:0.78rem;transition:all 0.15s;}
.wh-btn:hover{color:#f5a855;border-color:rgba(245,168,85,0.4);}
/* NAV */
.wn{background:#0c1528;border-bottom:1px solid #1d2f55;padding:0 24px;display:flex;gap:2px;overflow-x:auto;scrollbar-width:none;}
.wn::-webkit-scrollbar{display:none;}
.wn a{padding:12px 16px;color:#607098;font-size:0.82rem;font-weight:500;white-space:nowrap;border-bottom:2px solid transparent;transition:all 0.15s;display:block;}
.wn a:hover{color:#f5d76e;border-bottom-color:rgba(245,215,110,0.5);}
.wn a.active{color:#f5a855;border-bottom-color:#f5a855;}
/* MAIN */
.wm{max-width:1320px;margin:0 auto;padding:36px 24px;}
/* PAGE HEADER */
.wpt{font-size:1.8rem;font-weight:800;background:linear-gradient(100deg,#f5a855,#f5d76e 55%,#90c4f0);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;margin-bottom:8px;letter-spacing:-0.025em;}
.wpd{color:#607098;font-size:0.88rem;margin-bottom:28px;line-height:1.6;}
/* SECTION DIVIDER */
.ws{display:flex;align-items:center;gap:12px;margin:36px 0 18px;}
.ws-t{font-size:0.75rem;font-weight:700;color:#f5a855;text-transform:uppercase;letter-spacing:0.1em;white-space:nowrap;}
.ws-l{flex:1;height:1px;background:linear-gradient(90deg,#1d2f55,transparent);}
/* GRIDS */
.wg{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px;}
.wg-lg{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:20px;}
.wg-sm{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:14px;}
/* CARD */
.wc{background:#111c35;border:1px solid #1d2f55;border-radius:12px;padding:20px;display:block;color:inherit;position:relative;overflow:hidden;transition:border-color 0.2s,box-shadow 0.2s,transform 0.2s;}
.wc::after{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,#f5a855,#f5d76e);opacity:0;transition:opacity 0.2s;}
.wc:hover{border-color:#f5a855;box-shadow:0 8px 32px rgba(245,168,85,0.12),0 2px 8px rgba(0,0,0,0.5);transform:translateY(-2px);color:inherit;}
.wc:hover::after{opacity:1;}
.wcs{cursor:default;}.wcs:hover{transform:none;box-shadow:none;border-color:#1d2f55;}.wcs:hover::after{opacity:0;}
.wc-icon{font-size:2rem;margin-bottom:12px;display:block;}
.wc-title{font-size:0.95rem;font-weight:700;color:#dde8ff;margin-bottom:6px;}
.wc-desc{font-size:0.80rem;color:#607098;line-height:1.55;}
.wc-meta{margin-top:14px;padding-top:12px;border-top:1px solid #0f1a30;display:flex;gap:6px;flex-wrap:wrap;}
/* KEY-VALUE ROW */
.wkv{display:flex;justify-content:space-between;align-items:center;padding:7px 0;border-bottom:1px solid #0f1a30;font-size:0.82rem;}
.wkv:last-child{border-bottom:none;}.wk{color:#607098;}.wv{color:#dde8ff;font-weight:500;}
.wv.ora{color:#f5a855;}.wv.yel{color:#f5d76e;}.wv.blu{color:#90c4f0;}
/* BADGES */
.wb{display:inline-block;padding:2px 8px;border-radius:20px;font-size:0.68rem;font-weight:600;letter-spacing:0.04em;}
.wb-o{background:rgba(245,168,85,0.15);color:#f5a855;border:1px solid rgba(245,168,85,0.3);}
.wb-y{background:rgba(245,215,110,0.12);color:#f5d76e;border:1px solid rgba(245,215,110,0.25);}
.wb-b{background:rgba(144,196,240,0.12);color:#90c4f0;border:1px solid rgba(144,196,240,0.25);}
.wb-g{background:rgba(96,112,152,0.18);color:#90a0c8;border:1px solid rgba(96,112,152,0.3);}
.wb-grn{background:rgba(134,239,172,0.12);color:#86efac;border:1px solid rgba(134,239,172,0.25);}
.wb-red{background:rgba(252,165,165,0.12);color:#fca5a5;border:1px solid rgba(252,165,165,0.25);}
/* BUFF / DEBUFF PILLS */
.buff{display:inline-block;padding:2px 7px;border-radius:4px;background:rgba(134,239,172,0.1);color:#86efac;border:1px solid rgba(134,239,172,0.2);font-size:0.67rem;margin:2px;}
.debuff{display:inline-block;padding:2px 7px;border-radius:4px;background:rgba(252,165,165,0.1);color:#fca5a5;border:1px solid rgba(252,165,165,0.2);font-size:0.67rem;margin:2px;}
/* SEARCH & FILTERS */
.wsw{position:relative;margin-bottom:16px;}
.wsw-ico{position:absolute;left:14px;top:50%;transform:translateY(-50%);color:#607098;pointer-events:none;}
.wsbox{width:100%;padding:12px 16px 12px 42px;background:#111c35;border:1px solid #1d2f55;border-radius:8px;color:#dde8ff;font-size:0.9rem;outline:none;transition:border-color 0.2s,box-shadow 0.2s;font-family:inherit;}
.wsbox:focus{border-color:#f5a855;box-shadow:0 0 0 3px rgba(245,168,85,0.1);}
.wfilters{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:20px;}
.wft{padding:6px 14px;border-radius:20px;font-size:0.78rem;font-weight:500;color:#607098;background:#111c35;border:1px solid #1d2f55;text-decoration:none;transition:all 0.15s;cursor:pointer;}
.wft:hover{color:#f5a855;border-color:rgba(245,168,85,0.4);}
.wft.active{color:#f5a855;background:rgba(245,168,85,0.08);border-color:rgba(245,168,85,0.45);}
/* NO-RESULTS */
.wnone{color:#607098;padding:32px;text-align:center;font-style:italic;grid-column:1/-1;}
/* VIDEO CARD */
.wvc{background:#111c35;border:1px solid #1d2f55;border-radius:12px;overflow:hidden;}
.wvc-embed{aspect-ratio:16/9;width:100%;}.wvc-embed iframe{width:100%;height:100%;border:none;display:block;}
.wvc-info{padding:16px;}.wvc-title{font-weight:700;color:#dde8ff;margin-bottom:5px;font-size:0.95rem;}.wvc-desc{font-size:0.80rem;color:#607098;line-height:1.5;}
/* AUDIO CARD */
.wac{background:#111c35;border:1px solid #1d2f55;border-radius:12px;padding:18px 20px;display:flex;gap:14px;align-items:center;}
.wac-ico{width:44px;height:44px;border-radius:50%;flex-shrink:0;background:linear-gradient(135deg,rgba(245,168,85,0.18),rgba(245,215,110,0.08));border:1px solid rgba(245,168,85,0.28);display:flex;align-items:center;justify-content:center;font-size:1.2rem;}
.wac-lbl{font-size:0.68rem;color:#607098;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:3px;}
.wac-title{font-weight:600;color:#dde8ff;font-size:0.88rem;}.wac-soon{font-size:0.72rem;color:#f5d76e;margin-top:3px;}
/* MATERIALS */
.mats{display:flex;flex-wrap:wrap;gap:4px;margin-top:6px;}
.mat{padding:2px 7px;background:#0c1528;border:1px solid #1d2f55;border-radius:4px;font-size:0.67rem;color:#90a0c8;}
/* HERO */
.whero{text-align:center;padding:60px 24px 52px;background:radial-gradient(ellipse at 50% -20%,rgba(245,168,85,0.09) 0%,transparent 65%);border-bottom:1px solid #1d2f55;margin-bottom:44px;}
.whero-tag{display:inline-block;font-size:0.72rem;font-weight:600;text-transform:uppercase;letter-spacing:0.14em;color:#f5a855;background:rgba(245,168,85,0.1);border:1px solid rgba(245,168,85,0.25);border-radius:20px;padding:4px 14px;margin-bottom:20px;}
.whero-title{font-size:2.9rem;font-weight:800;background:linear-gradient(135deg,#f5a855 0%,#f5d76e 45%,#90c4f0 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;margin-bottom:14px;letter-spacing:-0.03em;line-height:1.15;}
.whero-sub{color:#607098;font-size:0.95rem;max-width:520px;margin:0 auto 32px;line-height:1.65;}
.whero-sw{max-width:520px;margin:0 auto;position:relative;}
.whero-sw input{width:100%;padding:15px 20px 15px 50px;background:#111c35;border:1px solid #1d2f55;border-radius:12px;color:#dde8ff;font-size:0.95rem;outline:none;transition:border-color 0.2s,box-shadow 0.2s;font-family:inherit;}
.whero-sw input:focus{border-color:#f5a855;box-shadow:0 0 0 4px rgba(245,168,85,0.1);}
.whero-sw-ico{position:absolute;left:16px;top:50%;transform:translateY(-50%);color:#607098;font-size:1.05rem;pointer-events:none;}
/* EXEC DOT */
.edot{width:8px;height:8px;border-radius:50%;display:inline-block;margin-right:5px;vertical-align:middle;}
@media(max-width:768px){.whero-title{font-size:1.9rem;}.wg,.wg-lg{grid-template-columns:1fr;}.wm{padding:20px 16px;}}
"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} · Wadsworth Wiki</title>
<style>{css}</style>
</head>
<body>
<header class="wh">
    <span class="wh-logo">◈ Wadsworth Wiki</span>
    <div class="wh-right">
        {player_el}
        <a href="/stats" class="wh-btn">← Analytics</a>
        <a href="/" class="wh-btn">Dashboard</a>
    </div>
</header>
<nav class="wn">{nav}</nav>
<main class="wm">{body}</main>
</body></html>"""


# ── Wiki: Hub ────────────────────────────────────────────────
@router.get("/stats/wiki", response_class=HTMLResponse)
async def wiki_hub(session_token: Optional[str] = Cookie(None)):
    """Wadsworth Wiki landing page — videos, audio, and reference links."""
    from auth import get_player_from_session
    db = get_db()
    player = get_player_from_session(db, session_token)
    db.close()
    if not player:
        return HTMLResponse('<meta http-equiv="refresh" content="0;url=/login">')

    # Gather live counts for reference cards
    biz_count = 0
    try:
        with open("business_types.json") as f:
            biz_count += sum(1 for v in json.load(f).values() if isinstance(v, dict))
    except Exception:
        pass
    try:
        with open("district_businesses.json") as f:
            biz_count += sum(1 for v in json.load(f).values() if isinstance(v, dict))
    except Exception:
        pass
    item_count = 0
    try:
        with open("item_types.json") as f:
            item_count += sum(1 for v in json.load(f).values() if isinstance(v, dict))
    except Exception:
        pass
    try:
        with open("district_items.json") as f:
            item_count += sum(1 for v in json.load(f).values() if isinstance(v, dict))
    except Exception:
        pass
    dist_count = 17
    try:
        from districts import DISTRICT_TYPES as _DT
        dist_count = len(_DT)
    except Exception:
        pass

    # Audio placeholders
    _AUDIO = [
        ("🏙️", "The Economics of Districts"),
        ("👔", "Executive Strategy Masterclass"),
        ("🏗️", "City Projects &amp; Urban Planning"),
        ("📈", "Market Manipulation 101"),
        ("💰", "Building Your First Production Empire"),
        ("🌐", "Forex, Crypto &amp; Reserve Banking"),
    ]
    audio_html = "".join(
        f'<div class="wac"><div class="wac-ico">{ico}</div>'
        f'<div><div class="wac-lbl">Audio Deep Dive</div>'
        f'<div class="wac-title">{ttl}</div>'
        f'<div class="wac-soon">⏳ Coming soon</div></div></div>'
        for ico, ttl in _AUDIO
    )

    # Reference cards
    _REF = [
        ("businesses",    "🏭", "Businesses",    "All production and retail business types — startup costs, cycles, recipes, and terrain requirements.",     f"{biz_count} types",    "Encyclopedia"),
        ("districts",     "🏙️", "Districts",     "District terrain types, base taxes, allowed businesses, and formation rules.",                             f"{dist_count} types",   "Encyclopedia"),
        ("items",         "📦", "Items",         "Every craftable and tradeable item — categories, descriptions, and live market prices.",                   f"{item_count}+ items",  "Catalog"),
        ("city_projects", "🏗️", "City Projects", "30 municipal mega-projects with buffs, debuffs, construction materials, and NAV contributions.",          "30 projects",           "Reference"),
        ("executives",    "👔", "Executives",    "23 executive roles, ability pools, school system, legendary bonuses, and marketplace mechanics.",          "23 roles",              "Reference"),
    ]
    ref_html = "".join(
        f'<a href="/stats/wiki/{slug}" class="wc">'
        f'<span class="wc-icon">{ico}</span>'
        f'<div class="wc-title">{name}</div>'
        f'<div class="wc-desc">{desc}</div>'
        f'<div class="wc-meta">'
        f'<span class="wb wb-o">{cnt}</span>'
        f'<span class="wb wb-b">{tag}</span>'
        f'</div></a>'
        for slug, ico, name, desc, cnt, tag in _REF
    )

    body = f"""
<div class="whero">
    <div class="whero-tag">Living Encyclopedia</div>
    <h1 class="whero-title">Wadsworth Wiki</h1>
    <p class="whero-sub">The definitive reference for businesses, districts, items, city projects,
    and executives in the Wadsworth economic simulation. Updated every game tick.</p>
    <div class="whero-sw">
        <span class="whero-sw-ico">🔍</span>
        <input type="text" id="hsearch" placeholder="Press Enter to search businesses…"
               onkeydown="if(event.key==='Enter')location.href='/stats/wiki/businesses?q='+encodeURIComponent(this.value)">
    </div>
</div>

<div class="ws"><span class="ws-t">📺 Video Tutorials</span><span class="ws-l"></span></div>
<div class="wg-lg">
    <div class="wvc">
        <div class="wvc-embed">
            <iframe src="https://www.youtube.com/embed/_uunsDAShzM?si=34QJSMx-dj_-Imf3"
                allow="accelerometer;autoplay;clipboard-write;encrypted-media;gyroscope;picture-in-picture;web-share"
                referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>
        </div>
        <div class="wvc-info">
            <div class="wvc-title">Getting Started in Wadsworth</div>
            <div class="wvc-desc">An introduction to the platform — creating your account, navigating the dashboard,
            and making your first land purchase and business decision.</div>
        </div>
    </div>
    <div class="wvc" style="display:flex;flex-direction:column;align-items:center;justify-content:center;
         min-height:220px;border-style:dashed;opacity:0.4;">
        <div style="font-size:2.5rem;margin-bottom:10px;">🎬</div>
        <div style="color:#607098;font-size:0.88rem;">More tutorials coming soon</div>
    </div>
</div>

<div class="ws"><span class="ws-t">🎙️ Audio Deep Dives</span><span class="ws-l"></span></div>
<div class="wg">{audio_html}</div>

<div class="ws"><span class="ws-t">📚 Reference Pages</span><span class="ws-l"></span></div>
<div class="wg-sm">{ref_html}</div>
"""
    return HTMLResponse(wiki_shell("Wiki Home", body, player.business_name, "hub"))


# ── Wiki: Businesses ─────────────────────────────────────────
@router.get("/stats/wiki/businesses", response_class=HTMLResponse)
async def wiki_businesses(
    session_token: Optional[str] = Cookie(None),
    category: str = Query("all"),
    q: str = Query(""),
):
    """Business encyclopedia with wiki shell."""
    from auth import get_player_from_session
    db = get_db()
    player = get_player_from_session(db, session_token)
    db.close()
    if not player:
        return HTMLResponse('<meta http-equiv="refresh" content="0;url=/login">')

    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)

    business_types: dict = {}
    district_businesses: dict = {}
    try:
        with open("business_types.json") as f:
            business_types = json.load(f)
    except Exception:
        pass
    try:
        with open("district_businesses.json") as f:
            district_businesses = json.load(f)
    except Exception:
        pass

    dist_keys = set(district_businesses.keys())
    if category == "district":
        pool = {k: v for k, v in district_businesses.items() if isinstance(v, dict)}
    elif category == "all":
        pool = {k: v for k, v in business_types.items() if isinstance(v, dict)}
        pool.update({k: v for k, v in district_businesses.items() if isinstance(v, dict)})
    else:
        pool = {k: v for k, v in business_types.items() if isinstance(v, dict) and v.get("class") == category}

    _BADGE = {"production": "wb-grn", "retail": "wb-b"}
    cards = ""
    for key, biz in sorted(pool.items(), key=lambda x: x[1].get("name", x[0])):
        name    = biz.get("name", key.replace("_", " ").title())
        desc    = biz.get("description", "")[:90]
        cost    = biz.get("startup_cost", 0)
        cycles  = biz.get("cycles_to_complete", 1)
        bclass  = biz.get("class", "production")
        is_dist = key in dist_keys
        bc      = _BADGE.get(bclass, "wb-g")
        dtag    = '<span class="wb wb-o" style="font-size:0.62rem;margin-right:4px;">district</span>' if is_dist else ""
        safe_name = name.lower().replace('"', '')
        safe_desc = desc.lower().replace('"', '')
        cards += (
            f'<a href="/stats/business/{key}" class="wc"'
            f' data-n="{safe_name}" data-d="{safe_desc}" data-c="{bclass}">'
            f'<div style="display:flex;align-items:center;gap:6px;margin-bottom:8px;flex-wrap:wrap;">'
            f'{dtag}<span class="wb {bc}">{bclass}</span>'
            f'<span class="wc-title" style="margin:0;">{name}</span></div>'
            f'<div class="wc-desc">{desc}</div>'
            f'<div class="wkv" style="margin-top:10px;">'
            f'<span class="wk">Startup Cost</span><span class="wv ora">{fmt_usd(cost, disp, precision=0)}</span></div>'
            f'<div class="wkv"><span class="wk">Cycle Time</span>'
            f'<span class="wv">{cycles:,} ticks</span></div>'
            f'</a>'
        )

    filters = ""
    for slug, lbl in [("all", "All"), ("production", "Production"), ("retail", "Retail"), ("district", "District")]:
        act = " active" if category == slug else ""
        filters += f'<a href="/stats/wiki/businesses?category={slug}" class="wft{act}">{lbl}</a>'

    pre_search = f"bizSearch(document.getElementById('bs').value);" if q else ""
    body = f"""
<h1 class="wpt">🏭 Businesses</h1>
<p class="wpd">All production and retail business types in Wadsworth. Click any card for detailed recipes,
terrain requirements, and cost breakdowns.</p>
<div class="wfilters">{filters}</div>
<div class="wsw">
    <span class="wsw-ico">🔍</span>
    <input class="wsbox" id="bs" placeholder="Search businesses…" value="{q}"
           oninput="bizSearch(this.value)">
</div>
<div class="wg" id="bg">
    {cards if cards else '<div class="wnone">No businesses in this category.</div>'}
</div>
<p id="bn" style="color:#607098;text-align:center;margin-top:16px;display:none;">No businesses match your search.</p>
<script>
function bizSearch(q){{
    q=q.toLowerCase().trim();let v=0;
    document.querySelectorAll('#bg .wc').forEach(c=>{{
        const ok=!q||c.dataset.n.includes(q)||c.dataset.d.includes(q)||c.dataset.c.includes(q);
        c.style.display=ok?'':'none';if(ok)v++;
    }});
    document.getElementById('bn').style.display=(q&&v===0)?'':'none';
}}
{pre_search}
</script>
"""
    return HTMLResponse(wiki_shell("Businesses", body, player.business_name, "businesses"))


# ── Wiki: Districts ──────────────────────────────────────────
@router.get("/stats/wiki/districts", response_class=HTMLResponse)
async def wiki_districts_page(session_token: Optional[str] = Cookie(None)):
    """Districts encyclopedia with wiki shell."""
    from auth import get_player_from_session
    db = get_db()
    player = get_player_from_session(db, session_token)
    db.close()
    if not player:
        return HTMLResponse('<meta http-equiv="refresh" content="0;url=/login">')

    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)
    try:
        from districts import DISTRICT_TYPES, DISTRICT_TAX_MULTIPLIER
    except Exception:
        DISTRICT_TYPES = {}
        DISTRICT_TAX_MULTIPLIER = 15.0

    dist_biz: dict = {}
    try:
        with open("district_businesses.json") as f:
            dist_biz = json.load(f)
    except Exception:
        pass

    terrain_map: Dict[str, list] = {}
    for bk, bc in dist_biz.items():
        if not isinstance(bc, dict):
            continue
        for t in bc.get("allowed_terrain", []):
            terrain_map.setdefault(t, []).append((bc.get("name", bk), bk))

    cards = ""
    for dtype, cfg in sorted(DISTRICT_TYPES.items(), key=lambda x: x[1]["name"]):
        tkey  = cfg.get("district_terrain", f"district_{dtype}")
        base  = cfg["base_tax"]
        ex    = base * 1.0 * DISTRICT_TAX_MULTIPLIER
        terr  = ", ".join(t.replace("_", " ").title() for t in cfg.get("allowed_terrain", []))
        desc  = cfg.get("description", "")
        bizz  = terrain_map.get(tkey, [])
        blist = "".join(
            f'<a href="/stats/business/{bk}" style="display:block;font-size:0.72rem;color:#90c4f0;padding:2px 0;">{bn}</a>'
            for bn, bk in sorted(bizz)
        ) if bizz else '<span style="color:#3d5080;font-size:0.72rem;">No special businesses</span>'
        desc_el = f'<div class="wc-desc" style="margin:6px 0 10px;">{desc}</div>' if desc else ""
        cards += (
            f'<div class="wc wcs">'
            f'<div class="wc-title">{cfg["name"]}</div>'
            f'{desc_el}'
            f'<div class="wkv"><span class="wk">Monthly Tax ×{int(DISTRICT_TAX_MULTIPLIER)}</span>'
            f'<span class="wv yel">{fmt_usd(ex, disp, precision=0)}/mo*</span></div>'
            f'<div class="wkv"><span class="wk">Terrain</span>'
            f'<span class="wv" style="font-size:0.75rem;text-align:right;max-width:60%;">{terr}</span></div>'
            f'<div class="wkv" style="align-items:flex-start;">'
            f'<span class="wk" style="padding-top:2px;">Businesses</span>'
            f'<div style="text-align:right;">{blist}</div></div>'
            f'</div>'
        )

    body = f"""
<h1 class="wpt">🏙️ Districts</h1>
<p class="wpd">Districts are formed by merging land plots (Fibonacci sequence).
Monthly tax = Base Tax × Size × {int(DISTRICT_TAX_MULTIPLIER)}.
*Example shows size = 1 with no modifiers.</p>
<div class="wg">{cards if cards else '<div class="wnone">District data unavailable.</div>'}</div>
"""
    return HTMLResponse(wiki_shell("Districts", body, player.business_name, "districts"))


# ── Wiki: Items ──────────────────────────────────────────────
@router.get("/stats/wiki/items", response_class=HTMLResponse)
async def wiki_items_page(
    session_token: Optional[str] = Cookie(None),
    category: str = Query("all"),
):
    """Item catalog with wiki shell."""
    from auth import get_player_from_session
    db = get_db()
    player = get_player_from_session(db, session_token)
    db.close()
    if not player:
        return HTMLResponse('<meta http-equiv="refresh" content="0;url=/login">')

    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)

    items: dict = {}
    try:
        with open("item_types.json") as f:
            items = json.load(f)
    except Exception:
        pass
    try:
        with open("district_items.json") as f:
            items.update(json.load(f))
    except Exception:
        pass

    try:
        from market import get_market_price
    except Exception:
        get_market_price = lambda x: None  # noqa: E731

    cats = sorted({v.get("category", "misc") for v in items.values() if isinstance(v, dict)})
    pool = {k: v for k, v in items.items()
            if isinstance(v, dict) and (category == "all" or v.get("category") == category)}

    filters = (
        f'<a href="/stats/wiki/items?category=all" class="wft {"active" if category=="all" else ""}">'
        f'All ({sum(1 for v in items.values() if isinstance(v, dict))})</a>'
    )
    for cat in cats:
        cnt = sum(1 for v in items.values() if isinstance(v, dict) and v.get("category") == cat)
        act = " active" if category == cat else ""
        filters += (
            f'<a href="/stats/wiki/items?category={cat}" class="wft{act}">'
            f'{cat.replace("_"," ").title()} ({cnt})</a>'
        )

    cards = ""
    for key, item in sorted(pool.items(), key=lambda x: x[1].get("name", x[0])):
        name = item.get("name", key.replace("_", " ").title())
        desc = item.get("description", "")[:80]
        cat  = item.get("category", "misc")
        try:
            price = get_market_price(key)
            price_str = fmt_usd(price, disp) if price else "No market data"
            price_cls = "ora" if price else ""
        except Exception:
            price_str, price_cls = "No market data", ""
        safe = name.lower().replace('"', '')
        cards += (
            f'<div class="wc wcs" data-n="{safe}" data-c="{cat}">'
            f'<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:6px;">'
            f'<div class="wc-title" style="margin:0;">{name}</div>'
            f'<span class="wb wb-g">{cat.replace("_"," ").title()}</span></div>'
            f'<div class="wc-desc">{desc}</div>'
            f'<div class="wkv" style="margin-top:10px;"><span class="wk">Market Price</span>'
            f'<span class="wv {price_cls}">{price_str}</span></div>'
            f'</div>'
        )

    body = f"""
<h1 class="wpt">📦 Items</h1>
<p class="wpd">Every craftable and tradeable item in the Wadsworth economy.
Prices update live from the market.</p>
<div class="wfilters">{filters}</div>
<div class="wsw">
    <span class="wsw-ico">🔍</span>
    <input class="wsbox" id="is" placeholder="Search items…" oninput="itemSearch(this.value)">
</div>
<div class="wg" id="ig">
    {cards if cards else '<div class="wnone">No items found.</div>'}
</div>
<p id="in2" style="color:#607098;text-align:center;margin-top:16px;display:none;">No items match your search.</p>
<script>
function itemSearch(q){{
    q=q.toLowerCase().trim();let v=0;
    document.querySelectorAll('#ig .wc').forEach(c=>{{
        const ok=!q||c.dataset.n.includes(q)||c.dataset.c.includes(q);
        c.style.display=ok?'':'none';if(ok)v++;
    }});
    document.getElementById('in2').style.display=(q&&v===0)?'':'none';
}}
</script>
"""
    return HTMLResponse(wiki_shell("Items", body, player.business_name, "items"))


# ── Wiki: City Projects ──────────────────────────────────────
@router.get("/stats/wiki/city_projects", response_class=HTMLResponse)
async def wiki_city_projects(
    session_token: Optional[str] = Cookie(None),
    category: str = Query("all"),
):
    """City projects encyclopedia — 30 municipal mega-projects."""
    from auth import get_player_from_session
    db = get_db()
    player = get_player_from_session(db, session_token)
    db.close()
    if not player:
        return HTMLResponse('<meta http-equiv="refresh" content="0;url=/login">')

    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player.id)

    try:
        from city_projects import CITY_PROJECT_TYPES, SPECIAL_KEYS
    except Exception:
        err = '<div class="wnone">City project data unavailable.</div>'
        return HTMLResponse(wiki_shell("City Projects", err, player.business_name, "city_projects"))

    _CAT = {
        "foundation":    ("🏛️", "Foundation"),
        "public_safety": ("🚔", "Public Safety"),
        "utilities":     ("⚡", "Utilities"),
        "transportation":("🚆", "Transportation"),
        "commerce":      ("💹", "Commerce"),
        "education":     ("🎓", "Education"),
        "culture":       ("🎭", "Culture"),
        "industry":      ("🏭", "Industry"),
    }

    all_cats = sorted({v["category"] for v in CITY_PROJECT_TYPES.values()})
    pool = {k: v for k, v in CITY_PROJECT_TYPES.items()
            if category == "all" or v["category"] == category}

    filters = (
        f'<a href="/stats/wiki/city_projects?category=all" class="wft {"active" if category=="all" else ""}">'
        f'All ({len(CITY_PROJECT_TYPES)})</a>'
    )
    for cat in all_cats:
        ico, lbl = _CAT.get(cat, ("🏗️", cat.replace("_", " ").title()))
        cnt = sum(1 for v in CITY_PROJECT_TYPES.values() if v["category"] == cat)
        act = " active" if category == cat else ""
        filters += f'<a href="/stats/wiki/city_projects?category={cat}" class="wft{act}">{ico} {lbl} ({cnt})</a>'

    cards = ""
    for key, proj in sorted(pool.items(), key=lambda x: (x[1]["category"], x[1]["name"])):
        cat   = proj["category"]
        ico, cat_lbl = _CAT.get(cat, ("🏗️", cat.replace("_", " ").title()))
        mats  = proj.get("construction_materials", {})
        buffs = proj.get("buffs", {})
        debs  = proj.get("debuffs", {})
        lic   = proj.get("licenses_per_level", 0)
        val   = proj.get("base_project_value", 0)
        spec  = key in SPECIAL_KEYS

        pills = "".join(_wiki_buff(k, v) for k, v in buffs.items())
        pills += "".join(_wiki_debuff(k, v) for k, v in debs.items())
        mat_tags = "".join(
            f'<span class="mat">{qty:,}× {item.replace("_"," ").title()}</span>'
            for item, qty in mats.items()
        )
        spec_note = (
            '<div style="margin:8px 0;padding:8px 10px;background:rgba(245,215,110,0.06);'
            'border-radius:6px;border:1px solid rgba(245,215,110,0.15);font-size:0.75rem;color:#f5d76e;">'
            '⚡ Special project — see description for unique mechanics.</div>'
        ) if spec else ""

        cards += (
            f'<div class="wc wcs">'
            f'<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;">'
            f'<div class="wc-title" style="margin:0;">{ico} {proj["name"]}</div>'
            f'<span class="wb wb-o">{cat_lbl}</span></div>'
            f'<div class="wc-desc">{proj["description"]}</div>'
            f'{spec_note}'
            f'<div class="wkv"><span class="wk">NAV / Level</span>'
            f'<span class="wv yel">{fmt_usd(val, disp, precision=0)}</span></div>'
            f'<div class="wkv"><span class="wk">Licenses / Level</span>'
            f'<span class="wv">{lic:,}</span></div>'
            + (f'<div style="margin-top:10px;"><div style="font-size:0.68rem;color:#607098;margin-bottom:4px;'
               f'text-transform:uppercase;letter-spacing:0.06em;">Effects per level</div>{pills}</div>'
               if pills else "")
            + (f'<div style="margin-top:8px;"><div style="font-size:0.68rem;color:#607098;margin-bottom:4px;'
               f'text-transform:uppercase;letter-spacing:0.06em;">Construction materials</div>'
               f'<div class="mats">{mat_tags}</div></div>'
               if mat_tags else "")
            + f'</div>'
        )

    body = f"""
<h1 class="wpt">🏗️ City Projects</h1>
<p class="wpd">All 30 municipal mega-projects available to city governments. Buffs and debuffs scale
linearly per level (max level 12). The City Post Office must be constructed first — it generates
the licenses required for every other project.</p>
<div class="wfilters">{filters}</div>
<div class="wsw">
    <span class="wsw-ico">🔍</span>
    <input class="wsbox" id="ps" placeholder="Search projects, materials, effects…"
           oninput="projSearch(this.value)">
</div>
<div class="wg" id="pg">
    {cards if cards else '<div class="wnone">No projects found.</div>'}
</div>
<p id="pn" style="color:#607098;text-align:center;margin-top:16px;display:none;">No projects match your search.</p>
<script>
function projSearch(q){{
    q=q.toLowerCase().trim();let v=0;
    document.querySelectorAll('#pg .wc').forEach(c=>{{
        const ok=!q||c.textContent.toLowerCase().includes(q);
        c.style.display=ok?'':'none';if(ok)v++;
    }});
    document.getElementById('pn').style.display=(q&&v===0)?'':'none';
}}
</script>
"""
    return HTMLResponse(wiki_shell("City Projects", body, player.business_name, "city_projects"))


# ── Wiki: Executives ─────────────────────────────────────────
@router.get("/stats/wiki/executives", response_class=HTMLResponse)
async def wiki_executives(
    session_token: Optional[str] = Cookie(None),
    category: str = Query("all"),
):
    """Executives encyclopedia — 23 roles, abilities, school, marketplace."""
    from auth import get_player_from_session
    db = get_db()
    player = get_player_from_session(db, session_token)
    db.close()
    if not player:
        return HTMLResponse('<meta http-equiv="refresh" content="0;url=/login">')

    try:
        from executive import EXECUTIVE_JOBS, EXECUTIVE_CATEGORIES, EXEC_ABILITIES, JOB_ABILITY_POOLS
    except Exception:
        err = '<div class="wnone">Executive data unavailable.</div>'
        return HTMLResponse(wiki_shell("Executives", err, player.business_name, "executives"))

    pool = {k: v for k, v in EXECUTIVE_JOBS.items()
            if category == "all" or v["category"] == category}

    filters = (
        f'<a href="/stats/wiki/executives?category=all" class="wft {"active" if category=="all" else ""}">'
        f'All ({len(EXECUTIVE_JOBS)})</a>'
    )
    for ck, cc in EXECUTIVE_CATEGORIES.items():
        cnt = sum(1 for v in EXECUTIVE_JOBS.values() if v["category"] == ck)
        if not cnt:
            continue
        act = " active" if category == ck else ""
        clr = cc["color"]
        filters += (
            f'<a href="/stats/wiki/executives?category={ck}" class="wft{act}">'
            f'<span class="edot" style="background:{clr};"></span>{cc["label"]} ({cnt})</a>'
        )

    cards = ""
    for jk, job in sorted(pool.items(), key=lambda x: (x[1]["category"], x[1]["title"])):
        ck  = job["category"]
        cc  = EXECUTIVE_CATEGORIES.get(ck, {"label": ck, "color": "#607098"})
        clr = cc["color"]
        ab_keys = JOB_ABILITY_POOLS.get(jk, [])
        ab_html = "".join(
            f'<span class="wb wb-b" style="font-size:0.63rem;margin:2px;" title="{EXEC_ABILITIES[ak]["desc"]}">'
            f'{EXEC_ABILITIES[ak]["name"]}</span>'
            for ak in ab_keys if ak in EXEC_ABILITIES
        )
        cards += (
            f'<div class="wc wcs">'
            f'<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;">'
            f'<div><div class="wc-title" style="margin:0;">{job["title"]}</div>'
            f'<div style="font-size:0.72rem;color:#607098;margin-top:2px;font-family:monospace;">{job["abbr"]}</div></div>'
            f'<span style="background:rgba(0,0,0,0.35);padding:3px 10px;border-radius:20px;'
            f'font-size:0.68rem;font-weight:600;white-space:nowrap;">'
            f'<span class="edot" style="background:{clr};"></span>{cc["label"]}</span>'
            f'</div>'
            f'<div class="wc-desc">{job["description"]}</div>'
            f'<div class="wkv"><span class="wk">Effect Area</span>'
            f'<span class="wv blu">{job["effect"].replace("_"," ").title()}</span></div>'
            + (f'<div style="margin-top:8px;">'
               f'<div style="font-size:0.68rem;color:#607098;margin-bottom:4px;text-transform:uppercase;'
               f'letter-spacing:0.06em;">Ability Pool ({len(ab_keys)})</div>'
               f'<div style="line-height:2;">{ab_html}</div></div>'
               if ab_html else "")
            + f'</div>'
        )

    mechanics = (
        '<div class="wc wcs" style="grid-column:1/-1;margin-top:8px;'
        'background:rgba(245,215,110,0.03);border-color:rgba(245,215,110,0.18);">'
        '<div class="wc-title" style="color:#f5d76e;margin-bottom:16px;">⚙️ Executive Mechanics</div>'
        '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:20px;">'
        + "".join(
            f'<div><div style="font-size:0.7rem;color:#f5a855;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:0.08em;margin-bottom:6px;">{hd}</div>'
            f'<div style="font-size:0.8rem;color:#90a0c8;line-height:1.7;">{tx}</div></div>'
            for hd, tx in [
                ("Hiring & Pay",
                 "Each exec spawns with 3–5 abilities drawn from their job pool. "
                 "Wages auto-raise 7.85% each year. Late payment triggers immediate quit "
                 "+ full pension and severance. Max 8 executives per player."),
                ("School System",
                 "School boosts existing ability performance — never adds new abilities. "
                 "Base cost: $5,000 · Duration: ~30 min real time. "
                 "Graduation raises wage by 15%."),
                ("Legendary Executives",
                 "5% spawn chance. Legendary execs receive one bonus ability from the "
                 "legendary pool: Double Efficiency, Half Wages, Fast Learner, "
                 "Golden Parachute Refusal, Eternal Youth, Mentor, Market Maker, "
                 "Crisis Manager, Rainmaker, Polymath."),
                ("Marketplace",
                 "Fired, retired, and quit executives re-enter the marketplace. "
                 "New execs spawn every 180 ticks. Marketplace holds up to 20 execs. "
                 "Retirement age: 65 · Max age: 85."),
            ]
        )
        + '</div></div>'
    )

    body = f"""
<h1 class="wpt">👔 Executives</h1>
<p class="wpd">23 executive roles across 11 specialisations. Each exec brings a unique pool of
abilities that scale with level and school training. Legendary executives (5% spawn chance)
receive a bonus ability from the legendary pool. Hover ability badges to see their effects.</p>
<div class="wfilters">{filters}</div>
<div class="wsw">
    <span class="wsw-ico">🔍</span>
    <input class="wsbox" id="es" placeholder="Search executives, abilities…"
           oninput="execSearch(this.value)">
</div>
<div class="wg" id="eg">
    {cards if cards else '<div class="wnone">No executives found.</div>'}
    {mechanics if category == "all" else ""}
</div>
<p id="en" style="color:#607098;text-align:center;margin-top:16px;display:none;">No executives match your search.</p>
<script>
function execSearch(q){{
    q=q.toLowerCase().trim();let v=0;
    document.querySelectorAll('#eg .wcs:not([style*="grid-column"])').forEach(c=>{{
        const ok=!q||c.textContent.toLowerCase().includes(q);
        c.style.display=ok?'':'none';if(ok)v++;
    }});
    document.getElementById('en').style.display=(q&&v===0)?'':'none';
}}
</script>
"""
    return HTMLResponse(wiki_shell("Executives", body, player.business_name, "executives"))


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
