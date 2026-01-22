"""
ux.py
User interface module for the economic simulation.
Provides:
- HTML shell template with lien indicators
- Navigation routes
- Module-specific pages
- Financial terminal aesthetic
- Business creation and management
- Retail pricing controls
- Banking and investment views
- Lien dashboard
"""

from typing import Optional
from fastapi import APIRouter, Cookie, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from datetime import timedelta
from datetime import datetime

router = APIRouter()

# ==========================
# HTML SHELL
# ==========================

def shell(title: str, body: str, balance: float = 0.0, player_id: int = None) -> str:
    lien_info = get_player_lien_info(player_id) if player_id else {"has_lien": False, "total_owed": 0.0, "status": "ok"}
    
    lien_html = ""
    if lien_info["has_lien"]:
        status_colors = {"critical": "#dc2626", "warning": "#f59e0b", "ok": "#64748b"}
        lien_color = status_colors.get(lien_info["status"], "#64748b")
        status_icons = {"critical": "🚨", "warning": "⚠️", "ok": "📋"}
        lien_icon = status_icons.get(lien_info["status"], "📋")
        
        lien_html = f'''
        <a href="/liens" style="color: {lien_color}; margin-right: 12px; text-decoration: none; display: inline-flex; align-items: center; gap: 4px; font-size: 0.85rem;">
            <span>{lien_icon}</span>
            <span style="font-weight: 500;">LIEN: ${lien_info["total_owed"]:,.0f}</span>
        </a>
        '''
    
    ticker_html = ""
    try:
        import market as market_mod
        import inventory as inv_mod
        
        all_items = list(inv_mod.ITEM_RECIPES.keys()) if inv_mod.ITEM_RECIPES else list(market_mod.STARTER_INVENTORY.keys())
        
        ticker_items = []
        for item in all_items:
            price = market_mod.get_market_price(item)
            if price:
                ticker_items.append(f"{item.replace('_', ' ').upper()}: ${price:,.2f}")
            else:
                ticker_items.append(f"{item.replace('_', ' ').upper()}: N/A")
        ticker_html = " | ".join(ticker_items) if ticker_items else "MARKET OPENING..."
    except:
        ticker_html = "MARKET FEED OFFLINE"
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{title} · SymCo</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            * {{ box-sizing: border-box; }}
            body {{
                background: #020617;
                color: #e5e7eb;
                font-family: 'JetBrains Mono', monospace;
                margin: 0;
                padding-bottom: 60px;
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
                flex-wrap: wrap;
                gap: 8px;
            }}

            .brand {{
                font-weight: bold;
                color: #38bdf8;
            }}

            .header-right {{
                display: flex;
                align-items: center;
                gap: 12px;
                flex-wrap: wrap;
            }}

            .balance {{
                color: #22c55e;
                font-size: 0.9rem;
                white-space: nowrap;
            }}

            .container {{
                max-width: 1000px;
                margin: 0 auto;
                padding: 20px 16px;
            }}

            .card {{
                background: #0f172a;
                border: 1px solid #1e293b;
                padding: 20px;
                margin-bottom: 16px;
            }}

            .badge {{
                font-size: 0.65rem;
                padding: 2px 6px;
                border-radius: 3px;
                background: #1e293b;
                margin-left: 6px;
                white-space: nowrap;
            }}

            .btn-blue, .btn-orange, .btn-red {{
                border: none;
                padding: 6px 12px;
                cursor: pointer;
                font-size: 0.8rem;
                border-radius: 3px;
            }}

            .btn-blue {{ background: #38bdf8; color: #020617; }}
            .btn-orange {{ background: #f59e0b; color: #020617; }}
            .btn-red {{ background: #ef4444; color: #fff; }}

            input, select {{
                background: #020617;
                border: 1px solid #1e293b;
                color: #e5e7eb;
                padding: 6px;
                font-size: 0.9rem;
            }}

            .progress {{
                background: #020617;
                height: 8px;
                margin-top: 8px;
            }}

            .progress-bar {{
                background: #38bdf8;
                height: 100%;
            }}

            .ticker {{
                position: fixed;
                bottom: 0;
                left: 0;
                right: 0;
                background: #020617;
                border-top: 1px solid #1e293b;
                padding: 6px 0;
                font-size: 0.75rem;
                color: #64748b;
                white-space: nowrap;
                overflow: hidden;
            }}

            @keyframes lien-pulse {{
                0%, 100% {{ opacity: 1; }}
                50% {{ opacity: 0.6; }}
            }}

            .lien-critical {{
                animation: lien-pulse 2s ease-in-out infinite;
            }}

            /* Responsive utilities */
            @media (max-width: 640px) {{
                .container {{ padding: 16px 12px; }}
                .card {{ padding: 16px; }}
                input, select {{ font-size: 16px; }}
                
                /* Stack grids on mobile */
                div[style*="display: grid"][style*="grid-template-columns: 1fr 1fr"] {{
                    display: flex !important;
                    flex-direction: column !important;
                }}
                
                /* Make flex containers wrap */
                div[style*="display: flex"]:not(.header-right) {{
                    flex-wrap: wrap !important;
                }}
                
                /* Stack forms vertically */
                form[style*="grid-template-columns"] {{
                    display: flex !important;
                    flex-direction: column !important;
                    gap: 8px !important;
                }}
                
                /* Wrap filter tabs */
                div[style*="overflow-x: auto"][style*="white-space: nowrap"] {{
                    white-space: normal !important;
                    overflow-x: visible !important;
                    display: flex !important;
                    flex-wrap: wrap !important;
                    gap: 8px !important;
                }}
                
                /* Make tab links inline-block for wrapping */
                div[style*="overflow-x: auto"] a {{
                    display: inline-block !important;
                    margin-right: 0 !important;
                    padding: 6px 10px !important;
                    background: #1e293b !important;
                    border-radius: 3px !important;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="brand">SymCo</div>
            <div class="header-right">
                {lien_html}
                <span class="balance">$ {balance:,.2f}</span>
                <a href="/api/logout" style="color: #ef4444;">Logout</a>
            </div>
        </div>

        <div class="container">
            {body}
        </div>

        <div class="ticker">
            <marquee scrollamount="12">{ticker_html} &nbsp;&nbsp;&nbsp; {ticker_html}</marquee>
        </div>
    </body>
    </html>
    """

# ==========================
# AUTHENTICATION HELPER
# ==========================

def require_auth(session_token: Optional[str] = Cookie(None)):
    """Check if user is authenticated."""
    try:
        import auth
        db = auth.get_db()
        player = auth.get_player_from_session(db, session_token)
        db.close()
        if not player:
            return RedirectResponse(url="/login", status_code=303)
        return player
    except Exception as e:
        print(f"[UX] Auth check failed: {e}")
        return RedirectResponse(url="/login", status_code=303)

# ==========================
# LIEN HELPER FUNCTIONS
# ==========================
# This now includes brokerage firm liens in addition to bank liens

def get_player_lien_info(player_id: int) -> dict:
    """
    Get comprehensive lien information for display in the UI.
    Includes liens from:
    - Land Bank
    - Apple Seeds ETF
    - Energy ETF
    - Brokerage Firm
    
    Returns:
        dict with keys:
        - has_lien: bool
        - total_owed: float
        - principal: float
        - interest: float
        - interest_rate_per_minute: float (for display)
        - garnishment_rate: float (percentage of cash taken)
        - status: str ("critical", "warning", "ok")
        - lien_count: int
        - sources: list of source names
    """
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from datetime import datetime
        
        DATABASE_URL = "sqlite:///./symco.db"
        engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        all_liens = []
        total_principal = 0.0
        total_interest = 0.0
        total_paid = 0.0
        sources = []
        
        # Check Land Bank liens
        try:
            from banks.land_bank import BankLien as LandBankLien, LIEN_INTEREST_RATE as LB_RATE, LIEN_GARNISHMENT_PERCENTAGE as LB_GARNISH
            db = SessionLocal()
            try:
                land_liens = db.query(LandBankLien).filter(LandBankLien.player_id == player_id).all()
                for lien in land_liens:
                    if lien.principal + lien.interest_accrued - lien.total_paid > 0:
                        all_liens.append(("land_bank", lien, LB_RATE, LB_GARNISH))
                        total_principal += lien.principal
                        total_interest += lien.interest_accrued
                        total_paid += lien.total_paid
                        if "Land Bank" not in sources:
                            sources.append("Land Bank")
            finally:
                db.close()
        except Exception as e:
            print(f"[UX] Land bank lien check error: {e}")
        
        # Check Apple Seeds ETF liens
        try:
            from banks.apple_seeds_etf import BankLien as ETFBankLien, LIEN_INTEREST_RATE as ETF_RATE, LIEN_GARNISHMENT_PERCENTAGE as ETF_GARNISH
            db = SessionLocal()
            try:
                etf_liens = db.query(ETFBankLien).filter(ETFBankLien.player_id == player_id).all()
                for lien in etf_liens:
                    if lien.principal + lien.interest_accrued - lien.total_paid > 0:
                        all_liens.append(("apple_seeds_etf", lien, ETF_RATE, ETF_GARNISH))
                        total_principal += lien.principal
                        total_interest += lien.interest_accrued
                        total_paid += lien.total_paid
                        if "Apple Seeds ETF" not in sources:
                            sources.append("Apple Seeds ETF")
            finally:
                db.close()
        except Exception as e:
            print(f"[UX] ETF lien check error: {e}")
        
        # Check Energy ETF liens
        try:
            from banks.energy_etf import BankLien as EnergyBankLien, LIEN_INTEREST_RATE as EN_RATE, LIEN_GARNISHMENT_PERCENTAGE as EN_GARNISH
            db = SessionLocal()
            try:
                energy_liens = db.query(EnergyBankLien).filter(EnergyBankLien.player_id == player_id).all()
                for lien in energy_liens:
                    if lien.principal + lien.interest_accrued - lien.total_paid > 0:
                        all_liens.append(("energy_etf", lien, EN_RATE, EN_GARNISH))
                        total_principal += lien.principal
                        total_interest += lien.interest_accrued
                        total_paid += lien.total_paid
                        if "Energy ETF" not in sources:
                            sources.append("Energy ETF")
            finally:
                db.close()
        except Exception as e:
            print(f"[UX] Energy ETF lien check error: {e}")
        
        # Check Brokerage Firm liens
        try:
            from banks.brokerage_firm import BrokerageLien, get_credit_interest_rate, get_db as get_firm_db
            db = get_firm_db()
            try:
                broker_liens = db.query(BrokerageLien).filter(BrokerageLien.player_id == player_id).all()
                for lien in broker_liens:
                    balance = lien.principal + lien.interest_accrued - lien.total_paid
                    if balance > 0:
                        # Brokerage firm uses dynamic interest based on credit
                        broker_rate = get_credit_interest_rate(player_id) / 525600  # Per minute
                        all_liens.append(("brokerage_firm", lien, broker_rate, 0.50))
                        total_principal += lien.principal
                        total_interest += lien.interest_accrued
                        total_paid += lien.total_paid
                        if "Brokerage Firm" not in sources:
                            sources.append("Brokerage Firm")
            finally:
                db.close()
        except Exception as e:
            print(f"[UX] Brokerage lien check error: {e}")
        
        # Calculate totals
        total_owed = total_principal + total_interest - total_paid
        
        if total_owed <= 0 or not all_liens:
            return {
                "has_lien": False,
                "total_owed": 0.0,
                "principal": 0.0,
                "interest": 0.0,
                "interest_rate_per_minute": 0.0,
                "garnishment_rate": 0.0,
                "status": "ok",
                "lien_count": 0,
                "sources": []
            }
        
        # Use the highest rate for display (most aggressive)
        max_rate = max(lien[2] for lien in all_liens) * 100  # Convert to percentage
        max_garnish = max(lien[3] for lien in all_liens) * 100  # Convert to percentage
        
        # Determine status based on debt size
        if total_owed > 50000:
            status = "critical"
        elif total_owed > 10000:
            status = "warning"
        else:
            status = "ok"
        
        return {
            "has_lien": True,
            "total_owed": total_owed,
            "principal": total_principal - total_paid,
            "interest": total_interest,
            "interest_rate_per_minute": max_rate,
            "garnishment_rate": max_garnish,
            "status": status,
            "lien_count": len(all_liens),
            "sources": sources
        }
    
    except Exception as e:
        print(f"[UX] Error getting lien info: {e}")
        import traceback
        traceback.print_exc()
        return {
            "has_lien": False,
            "total_owed": 0.0,
            "principal": 0.0,
            "interest": 0.0,
            "interest_rate_per_minute": 0.0,
            "garnishment_rate": 0.0,
            "status": "ok",
            "lien_count": 0,
            "sources": []
        }

# ==========================
# PAGES
# ==========================

@router.get("/", response_class=HTMLResponse)
def home(session_token: Optional[str] = Cookie(None)):
    """Main dashboard."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return player
    return shell(
        "Dashboard",
        f"""
        <h1>Welcome, CEO of {player.business_name}</h1>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
            <div class="card">
                <h3>Businesses</h3>
                <p>Operate plantations, factories, and services</p>
                <a href="/businesses" class="btn-blue">Open Terminal</a>
            </div>
            <div class="card">
                <h3>Inventory</h3>
                <p>Raw materials, goods, and finished products</p>
                <a href="/inventory" class="btn-blue">View Stock</a>
            </div>
            <div class="card">
                <h3>Land</h3>
                <p>Owned plots and land marketplace</p>
                <a href="/land" class="btn-blue">Real Estate</a>
            </div>
            <div class="card">
                <h3>Market</h3>
                <p>Buy and sell with other players</p>
                <a href="/market" class="btn-blue">Trading Floor</a>
            </div>
            <div class="card">
                <h3>Land Market</h3>
                <p>Government auctions and player land sales</p>
                <a href="/land-market" class="btn-blue">View Market</a>
            </div>
            <div class="card">
                <h3>Banks</h3>
                <p>Investment funds and share trading</p>
                <a href="/banks" class="btn-blue">Banking</a>
            </div>
        </div>
        """,
        player.cash_balance,
        player.id
    )

@router.get("/businesses", response_class=HTMLResponse)
def businesses(session_token: Optional[str] = Cookie(None)):
    """Business operations view with live progress and retail pricing."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return player
    try:
        from business import Business, BUSINESS_TYPES, get_dismantling_status, DISMANTLING_TICKS, RetailPrice
        from land import LandPlot, get_db as get_land_db
        land_db = get_land_db()
        player_businesses = land_db.query(Business).filter(Business.owner_id == player.id).all()

        if not player_businesses:
            land_db.close()
            return shell("Businesses", "<h3>No businesses found.</h3><a href='/land' class='btn-blue'>Go to Land</a>", player.cash_balance, player.id)

        biz_html = '<a href="/" style="color: #38bdf8;"><- Dashboard</a><h1>Business Terminal</h1>'
        for biz in player_businesses:
            config = BUSINESS_TYPES.get(biz.business_type, {})
            biz_name = config.get("name", biz.business_type)
            biz_class = config.get("class", "production")
            cycles_total = config.get("cycles_to_complete", 1)
            plot = land_db.query(LandPlot).filter(LandPlot.id == biz.land_plot_id).first()
            plot_info = f"Plot #{plot.id} ({plot.terrain_type.title()})" if plot else "Unknown Location"

            dismantle_status = get_dismantling_status(biz.id)
            if dismantle_status:
                progress_pct = dismantle_status['progress_pct']
                biz_html += f'''
                <div class="card" style="border-color: #ef4444;">
                    <h3>{biz_name} <span class="badge" style="background: #ef4444;">DISMANTLING</span></h3>
                    <p>{plot_info} | ID: #{biz.id}</p>
                    <p>Ticks Remaining: {dismantle_status['ticks_remaining']}/{DISMANTLING_TICKS} ({progress_pct:.0f}%)</p>
                    <p>Total Refund: ${dismantle_status['total_refund']:.2f} (Paid: ${dismantle_status['paid_so_far']:.2f})</p>
                </div>'''
                continue

            progress_pct = (biz.progress_ticks / cycles_total * 100) if cycles_total > 0 else 0
            status_badge = f'<span class="badge badge-{"active" if biz.is_active else "paused"}">{"ACTIVE" if biz.is_active else "PAUSED"}</span>'
            class_badge = f'<span class="badge" style="background: #38bdf8; color: #020617; margin-left: 5px;">{biz_class.upper()}</span>'

            biz_html += f'''
            <div class="card">
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div>
                        <h3>{biz_name} {status_badge} {class_badge}</h3>
                        <p>{plot_info} | ID: #{biz.id}</p>
                        <p>Progress: {biz.progress_ticks}/{cycles_total} ticks ({progress_pct:.0f}%)</p>
                    </div>
                    <div style="display: flex; gap: 10px;">
                        <form action="/api/business/toggle" method="post">
                            <input type="hidden" name="business_id" value="{biz.id}">
                            <button type="submit" class="{"btn-orange" if biz.is_active else "btn-blue"}">
                                {"Pause" if biz.is_active else "Resume"}
                            </button>
                        </form>
                        <form action="/api/business/dismantle" method="post">
                            <input type="hidden" name="business_id" value="{biz.id}">
                            <button type="submit" class="btn-red" onclick="return confirm('Dismantle for 50% refund over time?')">Dismantle</button>
                        </form>
                    </div>
                </div>'''

            if biz_class == "production":
                biz_html += '<div style="margin-top: 10px; border-top: 1px solid #1e293b; padding-top: 10px;"><strong>Production Lines:</strong>'
                for line in config.get("production_lines", []):
                    inputs = " + ".join([f"{req['quantity']} {req['item'].replace('_', ' ').title()}" for req in line.get("inputs", [])])
                    output = f"{line['output_qty']} {line['output_item'].replace('_', ' ').title()}"
                    biz_html += f'<p style="font-size: 0.9rem; color: #64748b;">→ {inputs or "No inputs"} = {output}</p>'
                biz_html += '</div>'
            
            elif biz_class == "retail":
                biz_html += '<div style="margin-top: 10px; border-top: 1px solid #1e293b; padding-top: 10px;"><strong>Retail Sales & Pricing:</strong>'
                for item, stats in config.get("products", {}).items():
                    # Retail Price Patch: Lookup current price for this player/item
                    price_entry = land_db.query(RetailPrice).filter(RetailPrice.player_id == player.id, RetailPrice.item_type == item).first()
                    current_p = f"${price_entry.price:.2f}" if price_entry else "MKT Default"
                    
                    biz_html += f'''
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; padding: 5px; background: #020617; border-radius: 4px;">
                        <span style="font-size: 0.9rem;">{item.replace("_", " ").title()} (E: {stats["elasticity"]})</span>
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <span style="color: #38bdf8; font-weight: bold;">{current_p}</span>
                            <form action="/api/retail/set-price" method="post" style="display: flex; gap: 4px;">
                                <input type="hidden" name="item_type" value="{item}">
                                <input type="number" name="price" step="0.01" placeholder="Set Price" style="padding: 4px; width: 80px;" required>
                                <button type="submit" class="btn-blue" style="padding: 4px 8px; font-size: 0.8rem;">Update</button>
                            </form>
                        </div>
                    </div>'''
                biz_html += '</div>'
            
            biz_html += '</div>'

        land_db.close()
        return shell("Businesses", biz_html, player.cash_balance, player.id)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return shell("Businesses", f"Error loading terminal: {e}", player.cash_balance, player.id)

@router.get("/inventory", response_class=HTMLResponse)
def inventory_page(session_token: Optional[str] = Cookie(None), filter: str = "all"):
    """Inventory management view."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return player
    try:
        import inventory as inv_mod
        inv = inv_mod.get_player_inventory(player.id)
        
        categories = {"all": "All", "seeds": "Seeds", "fruits": "Fruits", "liquids": "Liquids", "energy": "Energy"}
        filter_tabs = '<div style="margin-bottom: 20px;">'
        for k, v in categories.items():
            color = "#38bdf8" if k == filter else "#64748b"
            filter_tabs += f'<a href="/inventory?filter={k}" style="color: {color}; margin-right: 15px; text-decoration: none;">{v}</a>'
        filter_tabs += '</div>'

        items_html = ""
        for item, qty in inv.items():
            # Filtering logic
            if filter != "all":
                if filter == "seeds" and not item.endswith("_seeds"): continue
                if filter == "fruits" and item not in ["apples", "oranges"]: continue
                if filter == "liquids" and not ("water" in item or "_juice" in item): continue
                if filter == "energy" and item != "energy": continue
            
            item_info = inv_mod.get_item_info(item) or {}
            items_html += f'''
            <div class="card">
                <div style="display: flex; justify-content: space-between;">
                    <div>
                        <strong>{item.replace("_", " ").title()}</strong><br>
                        <small style="color: #64748b;">{item_info.get("description", "No description")}</small>
                    </div>
                    <div style="text-align: right;">
                        <span style="font-size: 1.2rem; color: #38bdf8;">{qty:.0f} units</span>
                        <form action="/api/inventory/list" method="post" style="margin-top: 10px;">
                            <input type="hidden" name="item_type" value="{item}">
                            <input type="number" name="quantity" placeholder="Qty" style="width: 60px;" required>
                            <input type="number" name="price" step="0.01" placeholder="Price" style="width: 80px;" required>
                            <button type="submit" class="btn-blue">List</button>
                        </form>
                    </div>
                </div>
            </div>'''
            
        return shell("Inventory", f'<a href="/" style="color: #38bdf8;"><- Dashboard</a><h1>Your Inventory</h1>{filter_tabs}{items_html if items_html else "<p>No items found.</p>"}', player.cash_balance, player.id)
    except Exception as e:
        return shell("Inventory", f"Error: {e}", player.cash_balance, player.id)

@router.get("/land", response_class=HTMLResponse)
def land(session_token: Optional[str] = Cookie(None)):
    """Land management view with accurate startup cost display."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return player
    try:
        from land import get_player_land, TERRAIN_TYPES
        from business import BUSINESS_TYPES
        plots = get_player_land(player.id)
        
        # Calculate player's business count for cost multiplier
        from business import Business
        from land import get_db as get_land_db
        land_db = get_land_db()
        owned_businesses_count = land_db.query(Business).filter(Business.owner_id == player.id).count()
        
        land_html = '<a href="/" style="color: #38bdf8;"><- Dashboard</a><h1>Land Portfolio</h1>'
        
        for plot in plots:
            status = 'OCCUPIED' if plot.occupied_by_business_id else 'VACANT'
            color = "#ef4444" if plot.occupied_by_business_id else "#22c55e"
            
            land_html += f'''
            <div class="card">
                <div style="display: flex; justify-content: space-between;">
                    <div>
                        <h3>Plot #{plot.id} <span class="badge" style="background: {color}; color: #020617;">{status}</span></h3>
                        <p>{plot.terrain_type.title()} | Eff: {plot.efficiency:.3f}% | Tax: ${plot.monthly_tax:.2f}</p>
                    </div>'''
            
            if not plot.occupied_by_business_id:
                land_html += f'''
                <div style="display: flex; gap: 10px;">
                    <form action="/api/business/create" method="post" style="display: flex; gap: 10px; align-items: center;">
                        <input type="hidden" name="land_plot_id" value="{plot.id}">
                        <select name="business_type" required>
                            <option value="">Build Business...</option>'''
                
                # Calculate actual startup costs for each business type
                for btype, config in BUSINESS_TYPES.items():
                    if plot.terrain_type in config.get("allowed_terrain", []):
                        base_cost = config.get("startup_cost", 2500.0)
                        
                        # CRITICAL FIX: Calculate the ACTUAL cost with multiplier
                        # Match the logic from business.py create_business()
                        multiplier = max(1.25, owned_businesses_count)
                        actual_cost = base_cost * multiplier
                        
                        business_name = config.get("name", btype)
                        land_html += f'<option value="{btype}">{business_name} (${actual_cost:,.0f})</option>'
                
                land_html += '''</select><button type="submit" class="btn-blue">Build</button>
                    </form>
                    <form action="/api/land-market/list-land" method="post" style="display: flex; gap: 10px; align-items: center;">
                    <input type="hidden" name="land_plot_id" value="''' + str(plot.id) + '''">
                    <input type="number" name="asking_price" step="0.01" placeholder="Asking Price" style="width: 120px;" required>
                    <button type="submit" class="btn-orange">List for Sale</button>
                </form>
            </div>'''
            
            land_html += '</div></div>'
        
        land_db.close()
        return shell("Land", land_html, player.cash_balance, player.id)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return shell("Land", f"Error: {e}", player.cash_balance, player.id)

@router.get("/land-market", response_class=HTMLResponse)
def land_market_page(session_token: Optional[str] = Cookie(None)):
    """Land market view - government auctions and player listings."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return player
    
    try:
        from land_market import get_active_auctions, get_active_listings, get_land_bank_plots
        from land import get_land_plot, TERRAIN_TYPES
        
        auctions = get_active_auctions()
        listings = get_active_listings()
        bank_plots = get_land_bank_plots()
        
        market_html = '<a href="/" style="color: #38bdf8;"><- Dashboard</a><h1>Land Market</h1>'
        
        # Government Auctions Section
        market_html += '<h2 style="margin-top: 30px;">Government Auctions (Dutch Auction)</h2>'
        if auctions:
            for auction in auctions:
                plot = get_land_plot(auction.land_plot_id)
                if not plot:
                    continue
                
                time_remaining = auction.end_time - datetime.utcnow()
                hours_left = int(time_remaining.total_seconds() / 3600)
                minutes_left = int((time_remaining.total_seconds() % 3600) / 60)
                
                price_drop_pct = ((auction.starting_price - auction.current_price) / auction.starting_price * 100) if auction.starting_price > 0 else 0
                
                market_html += f'''
                <div class="card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <h3>Plot #{plot.id} - {plot.terrain_type.title()} <span class="badge" style="background: #f59e0b; color: #020617;">AUCTION</span></h3>
                            <p>Size: {plot.size} | Efficiency: {plot.efficiency:.2f}% | Monthly Tax: ${plot.monthly_tax:.2f}</p>
                            <p style="color: #64748b;">Time Remaining: {hours_left}h {minutes_left}m</p>
                            <div style="margin-top: 10px;">
                                <span style="color: #ef4444;">Starting: ${auction.starting_price:,.2f}</span>
                                <span style="margin: 0 10px;">→</span>
                                <span style="color: #22c55e; font-size: 1.2rem; font-weight: bold;">Current: ${auction.current_price:,.2f}</span>
                                <span style="margin: 0 10px;">→</span>
                                <span style="color: #64748b;">Floor: ${auction.minimum_price:,.2f}</span>
                            </div>
                            <p style="font-size: 0.85rem; color: #64748b; margin-top: 5px;">Price dropped {price_drop_pct:.1f}% from start</p>
                        </div>
                        <form action="/api/land-market/buy-auction" method="post">
                            <input type="hidden" name="auction_id" value="{auction.id}">
                            <button type="submit" class="btn-blue" onclick="return confirm('Buy this plot for ${auction.current_price:,.2f}?')">
                                Buy Now<br>${auction.current_price:,.2f}
                            </button>
                        </form>
                    </div>
                </div>'''
        else:
            market_html += '<p style="color: #64748b;">No active government auctions at this time.</p>'
        
        # Player Listings Section
        market_html += '<h2 style="margin-top: 40px;">Player Listings</h2>'
        if listings:
            for listing in listings:
                plot = get_land_plot(listing.land_plot_id)
                if not plot:
                    continue
                
                from auth import get_db as get_auth_db, Player
                auth_db = get_auth_db()
                seller = auth_db.query(Player).filter(Player.id == listing.seller_id).first()
                auth_db.close()
                seller_name = seller.business_name if seller else f"Player {listing.seller_id}"
                
                is_own_listing = (listing.seller_id == player.id)
                
                market_html += f'''
                <div class="card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <h3>Plot #{plot.id} - {plot.terrain_type.title()} {"<span class=\"badge\" style=\"background: #38bdf8; color: #020617;\">YOUR LISTING</span>" if is_own_listing else ""}</h3>
                            <p>Size: {plot.size} | Efficiency: {plot.efficiency:.2f}% | Monthly Tax: ${plot.monthly_tax:.2f}</p>
                            <p style="color: #64748b;">Seller: {seller_name}</p>
                            <p style="color: #22c55e; font-size: 1.2rem; font-weight: bold; margin-top: 10px;">Price: ${listing.asking_price:,.2f}</p>
                        </div>
                        <div style="display: flex; gap: 10px;">'''
                
                if is_own_listing:
                    market_html += f'''
                            <form action="/api/land-market/cancel-listing" method="post">
                                <input type="hidden" name="listing_id" value="{listing.id}">
                                <button type="submit" class="btn-red">Cancel Listing</button>
                            </form>'''
                else:
                    market_html += f'''
                            <form action="/api/land-market/buy-listing" method="post">
                                <input type="hidden" name="listing_id" value="{listing.id}">
                                <button type="submit" class="btn-blue" onclick="return confirm('Buy this plot for ${listing.asking_price:,.2f}?')">
                                    Buy<br>${listing.asking_price:,.2f}
                                </button>
                            </form>'''
                
                market_html += '</div></div></div>'
        else:
            market_html += '<p style="color: #64748b;">No player listings available.</p>'
        
        # Land Bank Info (for debugging/transparency)
        if bank_plots:
            market_html += f'''
            <div style="margin-top: 40px; padding: 15px; background: #0f172a; border: 1px solid #1e293b; border-radius: 8px;">
                <h3 style="color: #64748b; font-size: 0.9rem;">Land Bank Status</h3>
                <p style="color: #64748b; font-size: 0.85rem;">{len(bank_plots)} unsold plot(s) awaiting re-auction</p>
            </div>'''
        
        return shell("Land Market", market_html, player.cash_balance, player.id)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return shell("Land Market", f"Error loading land market: {e}", player.cash_balance, player.id)

@router.get("/market", response_class=HTMLResponse)
def market_page(session_token: Optional[str] = Cookie(None), item: str = "apple_seeds"):
    """Market view with full order book including player names."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): 
        return player
    
    try:
        import market as market_mod
        import inventory as inv_mod
        items = list(inv_mod.ITEM_RECIPES.keys())
        stats = market_mod.get_market_stats()
        order_book = market_mod.get_order_book(item)
        
        # Item filter tabs
        filter_tabs = '<div style="margin-bottom: 20px; overflow-x: auto; white-space: nowrap; border-bottom: 1px solid #1e293b; padding-bottom: 10px;">'
        for i in items:
            color = "#38bdf8" if i == item else "#64748b"
            filter_tabs += f'<a href="/market?item={i}" style="color: {color}; margin-right: 15px; text-decoration: none;">{i.replace("_", " ").upper()}</a>'
        filter_tabs += '</div>'

        # Build market HTML
        market_html = f'''
        <a href="/" style="color: #38bdf8;"><- Dashboard</a>
        <div style="display: flex; gap: 20px;">
            <div style="flex: 2;">
                <h1>Market: {item.replace("_", " ").title()}</h1>
                {filter_tabs}
                
                <!-- Order Placement Form -->
                <div class="card">
                    <h3>Place Limit Order</h3>
                    <form action="/api/market/order" method="post" style="display: grid; grid-template-columns: 1fr 1fr 1fr auto; gap: 10px;">
                        <input type="hidden" name="item_type" value="{item}">
                        <select name="order_type">
                            <option value="buy">BUY</option>
                            <option value="sell">SELL</option>
                        </select>
                        <input type="number" name="quantity" placeholder="Quantity" required>
                        <input type="number" name="price" step="0.01" placeholder="Price" required>
                        <button type="submit" class="btn-blue">Submit</button>
                    </form>
                </div>
                
                <!-- Order Book Grid -->
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                    
                    <!-- BIDS (Buy Orders) -->
                    <div class="card">
                        <h3>Bids (Buy Orders)</h3>
                        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; margin-bottom: 8px; padding-bottom: 8px; border-bottom: 1px solid #1e293b; font-size: 0.85rem; color: #64748b;">
                            <span>Price</span>
                            <span>Qty</span>
                            <span>Trader</span>
                        </div>'''
        
        # Render bid orders
        if order_book['bids']:
            for price, qty, order_id, player_name, player_id in order_book['bids']:
                is_own = (player_id == player.id)
                player_display = f'<strong style="color: #38bdf8;">{player_name}</strong>' if is_own else player_name
                market_html += f'''
                        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; color: #22c55e; font-size: 0.9rem; padding: 4px 0;">
                            <span style="font-weight: bold;">${price:.2f}</span>
                            <span>{qty:.0f}</span>
                            <span style="color: #94a3b8; font-size: 0.85rem;">{player_display}</span>
                        </div>'''
        else:
            market_html += '<p style="color: #64748b; font-size: 0.9rem; padding: 8px 0;">No buy orders</p>'
        
        market_html += '''
                    </div>
                    
                    <!-- ASKS (Sell Orders) -->
                    <div class="card">
                        <h3>Asks (Sell Orders)</h3>
                        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; margin-bottom: 8px; padding-bottom: 8px; border-bottom: 1px solid #1e293b; font-size: 0.85rem; color: #64748b;">
                            <span>Price</span>
                            <span>Qty</span>
                            <span>Trader</span>
                        </div>'''
        
        # Render ask orders
        if order_book['asks']:
            for price, qty, order_id, player_name, player_id in order_book['asks']:
                is_own = (player_id == player.id)
                player_display = f'<strong style="color: #38bdf8;">{player_name}</strong>' if is_own else player_name
                market_html += f'''
                        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; color: #ef4444; font-size: 0.9rem; padding: 4px 0;">
                            <span style="font-weight: bold;">${price:.2f}</span>
                            <span>{qty:.0f}</span>
                            <span style="color: #94a3b8; font-size: 0.85rem;">{player_display}</span>
                        </div>'''
        else:
            market_html += '<p style="color: #64748b; font-size: 0.9rem; padding: 8px 0;">No sell orders</p>'
        
        market_html += '''
                    </div>
                </div>
            </div>
            
            <!-- Market Stats Sidebar -->
            <div style="flex: 1;">
                <div class="card">
                    <h3>Market Stats</h3>
                    <p><strong>24h Volume:</strong><br>${:,.2f}</p>
                    <p style="margin-top: 12px;"><strong>Total Trades:</strong><br>{:,}</p>
                </div>
            </div>
        </div>'''.format(stats["volume_24h"], stats["total_trades"])
        
        return shell("Market", market_html, player.cash_balance, player.id)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return shell("Market", f"Error loading market: {e}", player.cash_balance, player.id)

# ==========================
# SCPE COMPANY LISTINGS PAGE
# ==========================
# Add this route to ux.py for viewing all public companies

@router.get("/brokerage/companies", response_class=HTMLResponse)
def brokerage_companies_page(session_token: Optional[str] = Cookie(None)):
    """View all public companies listed on SCPE."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player

    try:
        from banks.brokerage_firm import (
            CompanyShares, ShareholderPosition, get_db as get_firm_db
        )
        from auth import Player, get_db as get_auth_db
        from business import Business, BUSINESS_TYPES
        from land import get_db as get_land_db
        
        db = get_firm_db()
        auth_db = get_auth_db()
        land_db = get_land_db()
        
        try:
            # Get all public companies
            companies = db.query(CompanyShares).filter(
                CompanyShares.is_delisted == False
            ).order_by(CompanyShares.ticker_symbol).all()
            
            company_data = []
            for company in companies:
                # Get founder info
                founder = auth_db.query(Player).filter(Player.id == company.founder_id).first()
                founder_name = founder.business_name if founder else f"Player {company.founder_id}"
                
                # Get business info
                business = land_db.query(Business).filter(Business.id == company.business_id).first()
                business_type = BUSINESS_TYPES.get(business.business_type, {}).get("name", "Unknown") if business else "Unknown"
                
                # Get shareholder count
                shareholder_count = db.query(ShareholderPosition).filter(
                    ShareholderPosition.company_shares_id == company.id,
                    ShareholderPosition.shares_owned > 0
                ).count()
                
                # Calculate market cap
                market_cap = company.current_price * company.shares_outstanding
                
                # Calculate price change from IPO
                if company.ipo_price > 0:
                    price_change = ((company.current_price - company.ipo_price) / company.ipo_price) * 100
                else:
                    price_change = 0
                
                company_data.append({
                    "company": company,
                    "founder_name": founder_name,
                    "business_type": business_type,
                    "shareholder_count": shareholder_count,
                    "market_cap": market_cap,
                    "price_change": price_change
                })
            
        finally:
            db.close()
            auth_db.close()
            land_db.close()
        
        # Build company cards
        companies_html = ""
        if company_data:
            for item in company_data:
                company = item["company"]
                change_color = "#22c55e" if item["price_change"] >= 0 else "#ef4444"
                change_arrow = "▲" if item["price_change"] >= 0 else "▼"
                
                # Status badges
                badges = ""
                if company.is_tbtf:
                    badges += '<span class="badge" style="background: #22c55e; margin-left: 5px;">🛡️ TBTF</span>'
                if company.trading_halted_until and datetime.utcnow() < company.trading_halted_until:
                    badges += '<span class="badge" style="background: #ef4444; margin-left: 5px;">🛑 HALTED</span>'
                if company.stabilization_active:
                    badges += '<span class="badge" style="background: #8b5cf6; margin-left: 5px;">📊 STABILIZED</span>'
                if company.dividend_warning_active:
                    badges += '<span class="badge" style="background: #f59e0b; margin-left: 5px;">⚠️ DIV WARNING</span>'
                
                # Dividend info
                dividend_text = "No dividends"
                if company.dividend_config:
                    div = company.dividend_config[0]
                    if div.get("type") == "cash":
                        dividend_text = f"Cash: {div.get('amount', 0)*100:.1f}% ({div.get('frequency', 'weekly')})"
                    elif div.get("type") == "commodity":
                        dividend_text = f"{div.get('item', 'item')}: {div.get('amount', 0)}/share"
                    elif div.get("type") == "scrip":
                        dividend_text = f"Stock: {div.get('rate', 0)*100:.1f}%"
                
                companies_html += f'''
                <div class="card">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div>
                            <h3 style="margin: 0;">
                                {company.ticker_symbol} - {company.company_name}
                                {badges}
                            </h3>
                            <p style="color: #64748b; margin: 5px 0;">
                                {item["business_type"]} · Founded by {item["founder_name"]} · Class {company.share_class}
                            </p>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-size: 1.8rem; font-weight: bold; color: #38bdf8;">${company.current_price:.4f}</div>
                            <div style="color: {change_color};">
                                {change_arrow} {abs(item["price_change"]):.1f}% from IPO
                            </div>
                        </div>
                    </div>
                    
                    <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 15px; margin-top: 15px;">
                        <div>
                            <div style="color: #64748b; font-size: 0.8rem;">Market Cap</div>
                            <div style="font-size: 1.1rem;">${item["market_cap"]:,.0f}</div>
                        </div>
                        <div>
                            <div style="color: #64748b; font-size: 0.8rem;">Float</div>
                            <div style="font-size: 1.1rem;">{company.shares_in_float:,}</div>
                        </div>
                        <div>
                            <div style="color: #64748b; font-size: 0.8rem;">Shareholders</div>
                            <div style="font-size: 1.1rem;">{item["shareholder_count"]}</div>
                        </div>
                        <div>
                            <div style="color: #64748b; font-size: 0.8rem;">Dividend Streak</div>
                            <div style="font-size: 1.1rem;">{company.consecutive_dividend_payouts}</div>
                        </div>
                        <div>
                            <div style="color: #64748b; font-size: 0.8rem;">Dividends</div>
                            <div style="font-size: 0.9rem;">{dividend_text}</div>
                        </div>
                    </div>
                    
                    <div style="margin-top: 15px; display: flex; gap: 10px;">
                        <a href="/brokerage/trading?ticker={company.ticker_symbol}" class="btn-blue">Trade</a>
                        <a href="/brokerage/shorts?ticker={company.ticker_symbol}" class="btn-orange">Short</a>
                    </div>
                </div>
                '''
        else:
            companies_html = '''
            <div class="card">
                <h3>No Companies Listed</h3>
                <p style="color: #64748b;">Be the first to take your business public!</p>
                <a href="/brokerage/ipo" class="btn-blue">Launch an IPO</a>
            </div>
            '''
        
        body = f'''
        <a href="/banks/brokerage-firm" style="color: #38bdf8;">← Brokerage Firm</a>
        <h1>SCPE Listed Companies</h1>
        <p style="color: #64748b;">{len(company_data)} companies listed on the SymCo Player Exchange</p>
        
        {companies_html}
        '''
        
        return shell("SCPE Companies", body, player.cash_balance, player.id)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return shell("SCPE Companies", f"Error: {e}", player.cash_balance, player.id)


# ==========================
# FOUNDER'S COMPANY MANAGEMENT PAGE
# ==========================
# Add this route for founders to manage their public companies

@router.get("/brokerage/my-companies", response_class=HTMLResponse)
def brokerage_my_companies_page(session_token: Optional[str] = Cookie(None)):
    """Manage companies you've founded."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player

    try:
        from banks.brokerage_firm import (
            CompanyShares, ShareholderPosition, get_db as get_firm_db, check_delisting
        )
        
        db = get_firm_db()
        try:
            # Get companies founded by this player
            my_companies = db.query(CompanyShares).filter(
                CompanyShares.founder_id == player.id,
                CompanyShares.is_delisted == False
            ).all()
            
            company_data = []
            for company in my_companies:
                # Get founder's position
                founder_position = db.query(ShareholderPosition).filter(
                    ShareholderPosition.player_id == player.id,
                    ShareholderPosition.company_shares_id == company.id
                ).first()
                
                founder_shares = founder_position.shares_owned if founder_position else 0
                ownership_pct = (founder_shares / company.shares_outstanding * 100) if company.shares_outstanding > 0 else 0
                
                # Can delist if founder owns 100%
                can_delist = founder_shares >= company.shares_outstanding
                
                company_data.append({
                    "company": company,
                    "founder_shares": founder_shares,
                    "ownership_pct": ownership_pct,
                    "can_delist": can_delist
                })
            
            # Get delisted companies
            delisted = db.query(CompanyShares).filter(
                CompanyShares.founder_id == player.id,
                CompanyShares.is_delisted == True
            ).all()
            
        finally:
            db.close()
        
        # Build company cards
        companies_html = ""
        if company_data:
            for item in company_data:
                company = item["company"]
                
                # Dividend configuration form
                current_dividends = ""
                if company.dividend_config:
                    for div in company.dividend_config:
                        current_dividends += f"<li>{div.get('type', 'unknown').title()}: {div.get('amount', 0)} ({div.get('frequency', 'unknown')})</li>"
                else:
                    current_dividends = "<li>No dividends configured</li>"
                
                companies_html += f'''
                <div class="card">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div>
                            <h3 style="margin: 0;">{company.ticker_symbol} - {company.company_name}</h3>
                            <p style="color: #64748b;">You founded this company</p>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-size: 1.5rem; font-weight: bold; color: #38bdf8;">${company.current_price:.4f}</div>
                        </div>
                    </div>
                    
                    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-top: 15px;">
                        <div>
                            <div style="color: #64748b; font-size: 0.8rem;">Your Shares</div>
                            <div style="font-size: 1.2rem;">{item["founder_shares"]:,}</div>
                        </div>
                        <div>
                            <div style="color: #64748b; font-size: 0.8rem;">Your Ownership</div>
                            <div style="font-size: 1.2rem;">{item["ownership_pct"]:.1f}%</div>
                        </div>
                        <div>
                            <div style="color: #64748b; font-size: 0.8rem;">Shares Outstanding</div>
                            <div style="font-size: 1.2rem;">{company.shares_outstanding:,}</div>
                        </div>
                        <div>
                            <div style="color: #64748b; font-size: 0.8rem;">Public Float</div>
                            <div style="font-size: 1.2rem;">{company.shares_in_float:,}</div>
                        </div>
                    </div>
                    
                    <div style="margin-top: 20px; padding-top: 15px; border-top: 1px solid #1e293b;">
                        <h4>Current Dividends</h4>
                        <ul style="color: #94a3b8; margin: 10px 0;">
                            {current_dividends}
                        </ul>
                        <p style="color: #64748b; font-size: 0.85rem;">
                            Dividend streak: {company.consecutive_dividend_payouts} payouts
                            {' | <span style="color: #f59e0b;">⚠️ Warning active</span>' if company.dividend_warning_active else ''}
                        </p>
                    </div>
                    
                    <div style="margin-top: 15px; display: flex; gap: 10px; flex-wrap: wrap;">
                        <a href="/brokerage/trading?ticker={company.ticker_symbol}" class="btn-blue">View Trading</a>
                        {f'''
                        <form action="/api/brokerage/buyback" method="post" style="display: inline;">
                            <input type="hidden" name="company_id" value="{company.id}">
                            <input type="number" name="shares" placeholder="Shares to buy" style="width: 100px; padding: 6px;" min="1" max="{company.shares_in_float}">
                            <button type="submit" class="btn-orange">Buyback</button>
                        </form>
                        ''' if company.shares_in_float > 0 else ''}
                        {f'''
                        <form action="/api/brokerage/go-private" method="post" style="display: inline;">
                            <input type="hidden" name="company_id" value="{company.id}">
                            <button type="submit" class="btn-red" onclick="return confirm('Take company private? This will delist the stock and you cannot re-IPO for 7200 ticks.')">
                                Go Private
                            </button>
                        </form>
                        ''' if item["can_delist"] else '<span style="color: #64748b; font-size: 0.85rem;">Buy back all shares to go private</span>'}
                    </div>
                </div>
                '''
        else:
            companies_html = '''
            <div class="card">
                <h3>No Public Companies</h3>
                <p style="color: #64748b;">You haven't taken any businesses public yet.</p>
                <a href="/brokerage/ipo" class="btn-blue">Launch Your First IPO</a>
            </div>
            '''
        
        # Delisted companies section
        delisted_html = ""
        if delisted:
            delisted_html = '<div class="card" style="margin-top: 20px;"><h3>Delisted Companies</h3>'
            for company in delisted:
                can_relist = company.can_relist_after and datetime.utcnow() >= company.can_relist_after
                delisted_html += f'''
                <div style="padding: 10px; margin: 10px 0; background: #020617; border-radius: 4px;">
                    <strong>{company.ticker_symbol}</strong> - {company.company_name}
                    <span style="color: #64748b; margin-left: 10px;">Delisted: {company.delisted_at.strftime("%Y-%m-%d") if company.delisted_at else "N/A"}</span>
                    {f'<span style="color: #22c55e; margin-left: 10px;">✓ Can re-IPO</span>' if can_relist else f'<span style="color: #f59e0b; margin-left: 10px;">Cooldown until {company.can_relist_after.strftime("%Y-%m-%d %H:%M") if company.can_relist_after else "N/A"}</span>'}
                </div>
                '''
            delisted_html += '</div>'
        
        body = f'''
        <a href="/banks/brokerage-firm" style="color: #38bdf8;">← Brokerage Firm</a>
        <h1>My Public Companies</h1>
        <p style="color: #64748b;">Manage companies you've founded and taken public</p>
        
        {companies_html}
        {delisted_html}
        '''
        
        return shell("My Companies", body, player.cash_balance, player.id)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return shell("My Companies", f"Error: {e}", player.cash_balance, player.id)


# ==========================
# ADDITIONAL API ENDPOINTS FOR FOUNDER ACTIONS
# ==========================

@router.post("/api/brokerage/buyback")
async def brokerage_buyback_shares(
    company_id: int = Form(...),
    shares: int = Form(...),
    session_token: Optional[str] = Cookie(None)
):
    """Founder buys back shares from the float."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    
    try:
        from banks.brokerage_firm import (
            CompanyShares, ShareholderPosition, buy_shares, get_db as get_firm_db
        )
        
        # Verify founder
        db = get_firm_db()
        try:
            company = db.query(CompanyShares).filter(
                CompanyShares.id == company_id,
                CompanyShares.founder_id == player.id
            ).first()
            
            if not company:
                return RedirectResponse(url="/brokerage/my-companies?error=not_founder", status_code=303)
        finally:
            db.close()
        
        # Use standard buy function
        success = buy_shares(
            buyer_id=player.id,
            company_shares_id=company_id,
            quantity=shares,
            use_margin=False
        )
        
        if success:
            return RedirectResponse(url="/brokerage/my-companies?success=buyback_complete", status_code=303)
        return RedirectResponse(url="/brokerage/my-companies?error=buyback_failed", status_code=303)
        
    except Exception as e:
        print(f"[UX] Buyback error: {e}")
        return RedirectResponse(url="/brokerage/my-companies?error=exception", status_code=303)


@router.post("/api/brokerage/go-private")
async def brokerage_go_private(
    company_id: int = Form(...),
    session_token: Optional[str] = Cookie(None)
):
    """Take a company private (delist)."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    
    try:
        from banks.brokerage_firm import (
            CompanyShares, ShareholderPosition, check_delisting, get_db as get_firm_db
        )
        
        db = get_firm_db()
        try:
            # Verify founder owns 100%
            company = db.query(CompanyShares).filter(
                CompanyShares.id == company_id,
                CompanyShares.founder_id == player.id
            ).first()
            
            if not company:
                return RedirectResponse(url="/brokerage/my-companies?error=not_founder", status_code=303)
            
            founder_position = db.query(ShareholderPosition).filter(
                ShareholderPosition.player_id == player.id,
                ShareholderPosition.company_shares_id == company_id
            ).first()
            
            founder_shares = founder_position.shares_owned if founder_position else 0
            
            if founder_shares < company.shares_outstanding:
                return RedirectResponse(url="/brokerage/my-companies?error=not_100_percent", status_code=303)
        finally:
            db.close()
        
        # Trigger delisting check
        delisted = check_delisting(company_id)
        
        if delisted:
            return RedirectResponse(url="/brokerage/my-companies?success=went_private", status_code=303)
        return RedirectResponse(url="/brokerage/my-companies?error=delist_failed", status_code=303)
        
    except Exception as e:
        print(f"[UX] Go private error: {e}")
        return RedirectResponse(url="/brokerage/my-companies?error=exception", status_code=303)


# ==========================
# UPDATED BANKS PAGE WITH BROKERAGE FIRM
# ==========================
# Banks_page function

@router.get("/banks", response_class=HTMLResponse)
def banks_page(session_token: Optional[str] = Cookie(None)):
    """Banking and investment view with Brokerage Firm."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return player

    try:
        import banks
        
        # Query active bank entities
        db = banks.get_db()
        bank_entities = db.query(banks.BankEntity).filter(banks.BankEntity.is_active == True).all()
        db.close()

        bank_html = '<a href="/" style="color: #38bdf8;">← Dashboard</a><h1>Banking & Investments</h1>'
        
        # ==========================
        # BROKERAGE FIRM CARD (Special - not in BankEntity table)
        # ==========================
        try:
            from banks.brokerage_firm import (
                get_firm_entity, firm_is_solvent, get_player_credit,
                ShareholderPosition, CompanyShares, get_db as get_firm_db
            )
            
            firm = get_firm_entity()
            player_credit = get_player_credit(player.id)
            is_solvent = firm_is_solvent()
            
            # Get player's total equity value
            firm_db = get_firm_db()
            try:
                positions = firm_db.query(ShareholderPosition).filter(
                    ShareholderPosition.player_id == player.id,
                    ShareholderPosition.shares_owned > 0
                ).all()
                
                total_equity_value = 0.0
                for pos in positions:
                    company = firm_db.query(CompanyShares).filter(
                        CompanyShares.id == pos.company_shares_id
                    ).first()
                    if company:
                        total_equity_value += pos.shares_owned * company.current_price
                
                company_count = firm_db.query(CompanyShares).filter(
                    CompanyShares.is_delisted == False
                ).count()
            finally:
                firm_db.close()
            
            # Credit tier colors
            tier_colors = {
                "prime": "#22c55e",
                "standard": "#38bdf8",
                "fair": "#f59e0b",
                "subprime": "#ef4444",
                "junk": "#7f1d1d"
            }
            tier_color = tier_colors.get(player_credit.tier, "#64748b")
            
            bank_html += f'''
            <div class="card" style="border: 2px solid #38bdf8; background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);">
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div>
                        <h3 style="margin: 0;">🏛️ SymCo Brokerage Firm</h3>
                        <p style="color: #64748b; margin-top: 5px;">Full-service: IPOs, Margin Trading, Short Selling, Commodity Lending</p>
                    </div>
                    <div style="text-align: right;">
                        <span class="badge" style="background: {'#22c55e' if is_solvent else '#ef4444'};">
                            {'SOLVENT' if is_solvent else 'INSOLVENT'}
                        </span>
                    </div>
                </div>
                
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-top: 20px;">
                    <div>
                        <div style="color: #64748b; font-size: 0.8rem;">Your Credit</div>
                        <div style="font-size: 1.5rem; font-weight: bold; color: {tier_color};">
                            {player_credit.credit_score} <span style="font-size: 0.8rem;">({player_credit.tier.upper()})</span>
                        </div>
                    </div>
                    <div>
                        <div style="color: #64748b; font-size: 0.8rem;">Your Equity</div>
                        <div style="font-size: 1.5rem; font-weight: bold; color: #38bdf8;">${total_equity_value:,.0f}</div>
                    </div>
                    <div>
                        <div style="color: #64748b; font-size: 0.8rem;">Firm Reserves</div>
                        <div style="font-size: 1.5rem; font-weight: bold;">${firm.cash_reserves:,.0f}</div>
                    </div>
                    <div>
                        <div style="color: #64748b; font-size: 0.8rem;">Listed Companies</div>
                        <div style="font-size: 1.5rem; font-weight: bold; color: #f59e0b;">{company_count}</div>
                    </div>
                </div>
                
                <div style="margin-top: 20px; display: flex; gap: 10px; flex-wrap: wrap;">
                    <a href="/banks/brokerage-firm" class="btn-blue">Open Firm Dashboard</a>
                    <a href="/brokerage/trading" class="btn-blue" style="background: #22c55e;">Trade SCPE</a>
                    <a href="/brokerage/ipo" class="btn-orange">Launch IPO</a>
                    <a href="/brokerage/commodities" class="btn-blue" style="background: #8b5cf6;">SCCE Commodities</a>
                </div>
            </div>
            '''
        except Exception as e:
            print(f"[UX] Brokerage firm card error: {e}")
            import traceback
            traceback.print_exc()
            bank_html += '''
            <div class="card" style="border: 1px solid #ef4444;">
                <h3>🏛️ SymCo Brokerage Firm</h3>
                <p style="color: #ef4444;">Error loading brokerage firm data</p>
            </div>
            '''

        # ==========================
        # ETF AND OTHER BANKS
        # ==========================
        for bank in bank_entities:
            # Fetch the player's specific share data from the appropriate bank module
            if bank.bank_id == "apple_seeds_etf":
                from banks.apple_seeds_etf import get_player_shareholding
                market_item = "apple_seeds_etf_shares"
                detail_url = "/banks/apple-seeds-etf"
            elif bank.bank_id == "energy_etf":
                from banks.energy_etf import get_player_shareholding
                market_item = "energy_etf_shares"
                detail_url = "/banks/energy-etf"
            else: # Default to land_bank logic
                from banks.land_bank import get_player_shareholding
                market_item = "land_bank_shares"
                detail_url = "/banks/land-bank"
            
            holding = get_player_shareholding(player.id)
            
            # Build the display using metrics from the BankEntity model
            bank_html += f'''
            <div class="card">
                <h3>{bank.bank_id.replace("_", " ").title()}</h3>
                <p style="color: #64748b;">{bank.description}</p>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 15px;">
                    <div><b>Share Price:</b> ${bank.share_price:.4f}</div>
                    <div><b>Market Cap:</b> ${bank.share_price * bank.total_shares_issued:,.2f}</div>
                    <div><b>Your Shares:</b> {holding["shares_owned"]:,}</div>
                    <div><b>Your Value:</b> ${holding["current_value"]:,.2f}</div>
                    <div><b>Ownership:</b> {holding["ownership_percentage"]:.4f}%</div>
                    <div><b>NAV:</b> ${(bank.cash_reserves + bank.asset_value):,.2f}</div>
                </div>
                <div style="margin-top: 15px; display: flex; gap: 10px;">
                    <a href="{detail_url}" class="btn-blue">View Details</a>
                    <a href="/market?item={market_item}" class="btn-orange">Trade Shares</a>
                </div>
            </div>
            '''
        
        return shell("Banks", bank_html, player.cash_balance, player.id)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return shell("Banks", f"Error loading banking: {e}", player.cash_balance, player.id)

@router.get("/banks/land-bank", response_class=HTMLResponse)
def land_bank_dashboard(session_token: Optional[str] = Cookie(None)):
    """Detailed Land Bank dashboard."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player

    try:
        import banks
        from banks.land_bank import get_player_shareholding, BANK_ID, BANK_NAME, BANK_DESCRIPTION

        bank_entity = banks.get_bank_entity(BANK_ID)
        player_shares = get_player_shareholding(player.id)

        nav = (bank_entity.cash_reserves or 0) + (bank_entity.asset_value or 0)
        
        # Check if bank is insolvent
        is_insolvent = bank_entity.cash_reserves < 0
        
        body = f"""
        <a href="/banks" style="color:#38bdf8;"><- Banks</a>
        <h1>{BANK_NAME}</h1>
        <p style="color:#64748b;">{BANK_DESCRIPTION}</p>
        
        {"<div class='card' style='border: 2px solid #ef4444; background: #450a0a;'><h3 style='color: #fca5a5;'>⚠️ BANK INSOLVENT</h3><p style='color: #fca5a5;'>This bank is currently insolvent. Shareholders may be subject to solvency levies.</p></div>" if is_insolvent else ""}

        <div class="card">
            <h3>Bank Overview</h3>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                <div>
                    <p><strong>Share Price:</strong> ${bank_entity.share_price:.2f}</p>
                    <p><strong>Total Shares:</strong> {bank_entity.total_shares_issued:,}</p>
                    <p><strong>Market Cap:</strong> ${bank_entity.share_price * bank_entity.total_shares_issued:,.2f}</p>
                </div>
                <div>
                    <p><strong>Net Asset Value:</strong> ${nav:,.2f}</p>
                    <p><strong>Cash Reserves:</strong> <span style="color: {'#ef4444' if bank_entity.cash_reserves < 0 else '#22c55e'};">${bank_entity.cash_reserves:,.2f}</span></p>
                    <p><strong>Land Assets:</strong> ${bank_entity.asset_value:,.2f}</p>
                </div>
            </div>
        </div>

        <div class="card">
            <h3>Your Position</h3>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                <div>
                    <p><strong>Shares Owned:</strong> {player_shares["shares_owned"]:,}</p>
                    <p><strong>Market Value:</strong> ${player_shares["current_value"]:,.2f}</p>
                </div>
                <div>
                    <p><strong>Ownership:</strong> {player_shares["ownership_percentage"]:.4f}%</p>
                    <p><strong>Lien Balance:</strong> <span style="color: {'#ef4444' if player_shares.get('lien_balance', 0) > 0 else '#22c55e'};">${player_shares.get("lien_balance", 0):,.2f}</span></p>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h3>Bank Statistics</h3>
            <p><strong>Total Dividends Paid:</strong> ${bank_entity.total_dividends_paid:,.2f}</p>
            <p><strong>Last Dividend:</strong> {bank_entity.last_dividend_date.strftime("%Y-%m-%d %H:%M") if bank_entity.last_dividend_date else "Never"}</p>
        </div>
        """

        return shell(
            BANK_NAME,
            body,
            player.cash_balance,
            player.id
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return shell("Bank Error", f"Error loading bank: {e}", player.cash_balance, player.id)

@router.get("/banks/apple-seeds-etf", response_class=HTMLResponse)
def apple_seeds_etf_dashboard(session_token: Optional[str] = Cookie(None)):
    """Detailed Apple Seeds ETF dashboard."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player

    try:
        import banks
        from banks import apple_seeds_etf as etf
        import inventory

        bank_entity = banks.get_bank_entity(etf.BANK_ID)
        player_shares = etf.get_player_shareholding(player.id)

        nav = (bank_entity.cash_reserves or 0) + (bank_entity.asset_value or 0)
        qe_active = bank_entity.share_price < (etf.QE_TRIGGER_SHARE_PRICE or 0)
        is_insolvent = bank_entity.cash_reserves < 0
        
        # Get ETF's commodity holdings
        seeds_held = inventory.get_item_quantity(etf.BANK_PLAYER_ID, etf.TARGET_COMMODITY)
        
        # Get market price
        import market as market_mod
        market_price = market_mod.get_market_price(etf.TARGET_COMMODITY) or 0

        body = f"""
        <a href="/banks" style="color:#38bdf8;"><- Banks</a>
        <h1>{etf.BANK_NAME}</h1>
        <p style="color:#64748b;">{etf.BANK_DESCRIPTION}</p>

        {"<div class='card' style='border: 2px solid #ef4444; background: #450a0a;'><h3 style='color: #fca5a5;'>⚠️ ETF INSOLVENT</h3><p style='color: #fca5a5;'>This ETF is currently insolvent. Shareholders may be subject to solvency levies.</p></div>" if is_insolvent else ""}
        
        {"<div class='card' style='border: 2px solid #f59e0b; background: #451a03;'><h3 style='color: #fbbf24;'>🏦 QUANTITATIVE EASING ACTIVE</h3><p style='color: #fbbf24;'>The ETF is buying commodities to restore asset value.</p></div>" if qe_active else ""}

        <div class="card">
            <h3>ETF Overview</h3>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                <div>
                    <p><strong>Share Price:</strong> ${bank_entity.share_price:.6f}</p>
                    <p><strong>Total Shares:</strong> {bank_entity.total_shares_issued:,}</p>
                    <p><strong>Market Cap:</strong> ${bank_entity.share_price * bank_entity.total_shares_issued:,.2f}</p>
                </div>
                <div>
                    <p><strong>Net Asset Value:</strong> ${nav:,.2f}</p>
                    <p><strong>Cash Reserves:</strong> <span style="color: {'#ef4444' if bank_entity.cash_reserves < 0 else '#22c55e'};">${bank_entity.cash_reserves:,.2f}</span></p>
                    <p><strong>Commodity Backing:</strong> ${bank_entity.asset_value:,.2f}</p>
                </div>
            </div>
        </div>

        <div class="card">
            <h3>Commodity Holdings</h3>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                <div>
                    <p><strong>Target Commodity:</strong> {etf.TARGET_COMMODITY.replace("_", " ").title()}</p>
                    <p><strong>Holdings:</strong> {seeds_held:,.0f} units</p>
                </div>
                <div>
                    <p><strong>Market Price:</strong> ${market_price:.2f}</p>
                    <p><strong>Total Value:</strong> ${seeds_held * market_price:,.2f}</p>
                </div>
            </div>
        </div>

        <div class="card">
            <h3>Your Position</h3>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                <div>
                    <p><strong>Shares Owned:</strong> {player_shares["shares_owned"]:,}</p>
                    <p><strong>Market Value:</strong> ${player_shares["current_value"]:,.2f}</p>
                </div>
                <div>
                    <p><strong>Ownership:</strong> {player_shares["ownership_percentage"]:.4f}%</p>
                    <p><strong>Lien Balance:</strong> <span style="color: {'#ef4444' if player_shares.get('lien_balance', 0) > 0 else '#22c55e'};">${player_shares.get("lien_balance", 0):,.2f}</span></p>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h3>ETF Strategy</h3>
            <ul style="color: #94a3b8; line-height: 1.8;">
                <li>Buys {etf.TARGET_COMMODITY} when price drops below {etf.BUY_PRICE_THRESHOLD*100:.0f}% of moving average</li>
                <li>Sells when inventory reaches {etf.SELL_INVENTORY_THRESHOLD*100:.0f}% of total market supply</li>
                <li>Annual holder fee: {etf.HOLDER_FEE_PER_TICK*31536000:.2f}%</li>
                <li>Stock splits at ${etf.SPLIT_PRICE_THRESHOLD:.2f} share price</li>
                <li>Buybacks trigger at 50% of IPO price</li>
            </ul>
        </div>
        """

        return shell(
            etf.BANK_NAME,
            body,
            player.cash_balance,
            player.id
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return shell("ETF Error", f"Error loading ETF: {e}", player.cash_balance, player.id)

@router.get("/banks/energy-etf", response_class=HTMLResponse)
def energy_etf_dashboard(session_token: Optional[str] = Cookie(None)):
    """Detailed Energy ETF dashboard mirrored from Apple Seeds ETF."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player

    try:
        import banks
        from banks import energy_etf as etf
        import inventory

        bank_entity = banks.get_bank_entity(etf.BANK_ID)
        player_shares = etf.get_player_shareholding(player.id)
        nav = (bank_entity.cash_reserves or 0) + (bank_entity.asset_value or 0)
        
        # Check for system status flags
        qe_active = bank_entity.share_price < (etf.QE_TRIGGER_SHARE_PRICE or 0)
        is_insolvent = bank_entity.cash_reserves < 0

        # Get commodity data
        energy_held = inventory.get_item_quantity(etf.BANK_PLAYER_ID, etf.TARGET_COMMODITY)
        import market as market_mod
        market_price = market_mod.get_market_price(etf.TARGET_COMMODITY) or 0

        # Conditional UI elements - Keep these on one line or use multi-line string concatenation
        insolvent_html = f"""
        <div style='background: #450a0a; border: 1px solid #dc2626; color: #f87171; padding: 15px; border-radius: 4px; margin: 20px 0;'>
            <strong>⚠️ ETF INSOLVENT</strong><br>
            This ETF is currently insolvent. Shareholders may be subject to solvency levies.
        </div>""" if is_insolvent else ""

        qe_html = f"""
        <div style='background: #064e3b; border: 1px solid #10b981; color: #34d399; padding: 15px; border-radius: 4px; margin: 20px 0;'>
            <strong>🏦 QUANTITATIVE EASING ACTIVE</strong><br>
            The ETF is buying energy to restore asset value.
        </div>""" if qe_active else ""

        body = f"""
        <a href="/banks" style="color: #64748b; text-decoration: none;">← Banks</a>
        <h1 style="color: #38bdf8; margin: 10px 0;">{etf.BANK_NAME}</h1>
        <p style="color: #94a3b8; font-style: italic;">{etf.BANK_DESCRIPTION}</p>

        {insolvent_html}
        {qe_html}

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 20px;">
            <div style="background: #1e293b; padding: 15px; border-radius: 4px; border-left: 4px solid #38bdf8;">
                <h3 style="margin-top: 0; color: #64748b;">ETF Overview</h3>
                <p>Share Price: <span style="color: #38bdf8; font-family: monospace;">${bank_entity.share_price:.6f}</span></p>
                <p>Total Shares: {bank_entity.total_shares_issued:,}</p>
                <p>Market Cap: ${bank_entity.share_price * bank_entity.total_shares_issued:,.2f}</p>
                <p>Net Asset Value: ${nav:,.2f}</p>
                <p>Cash Reserves: ${bank_entity.cash_reserves:,.2f}</p>
                <p>Commodity Backing: ${bank_entity.asset_value:,.2f}</p>
            </div>

            <div style="background: #1e293b; padding: 15px; border-radius: 4px; border-left: 4px solid #f59e0b;">
                <h3 style="margin-top: 0; color: #64748b;">Energy Grid Status</h3>
                <p>Target Commodity: {etf.TARGET_COMMODITY.title()}</p>
                <p>Holdings: {energy_held:,.0f} units</p>
                <p>Market Price: ${market_price:.2f}</p>
                <p>Total Value: ${energy_held * market_price:,.2f}</p>
            </div>
        </div>

        <div style="background: #1e293b; padding: 15px; border-radius: 4px; margin-top: 20px; border-left: 4px solid #10b981;">
            <h3 style="margin-top: 0; color: #64748b;">Your Position</h3>
            <p>Shares Owned: {player_shares["shares_owned"]:,}</p>
            <p>Market Value: ${player_shares["current_value"]:,.2f}</p>
            <p>Ownership: {player_shares["ownership_percentage"]:.4f}%</p>
        </div>

        <div style="margin-top: 20px; padding: 15px; background: #0f172a; border-radius: 4px;">
            <h3 style="margin-top: 0; color: #64748b;">ETF Strategy</h3>
            <ul style="color: #94a3b8; line-height: 1.6;">
                <li>Buys {etf.TARGET_COMMODITY} when price drops below {etf.BUY_PRICE_THRESHOLD*100:.0f}% of moving average</li>
                <li>Sells when inventory reaches {etf.SELL_INVENTORY_THRESHOLD*100:.0f}% of total market supply</li>
                <li>Annual holder fee: {etf.HOLDER_FEE_PER_TICK*31536000:.2f}%</li>
                <li>Stock splits at ${etf.SPLIT_PRICE_THRESHOLD:.2f} share price</li>
            </ul>
        </div>
        """
        return shell(etf.BANK_NAME, body, player.cash_balance, player.id)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return shell("ETF Error", f"Error loading Energy ETF: {e}", player.cash_balance, player.id)

# ==========================
# BROKERAGE FIRM UX ROUTES
# ==========================

@router.get("/banks/brokerage-firm", response_class=HTMLResponse)
def brokerage_firm_dashboard(session_token: Optional[str] = Cookie(None)):
    """Main Brokerage Firm dashboard with player share ticker."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player

    try:
        from banks.brokerage_firm import (
            get_firm_entity, firm_is_solvent, get_player_credit, get_credit_tier,
            CompanyShares, ShareholderPosition, CommodityLoan, ShareLoan, BrokerageLien,
            MarginCall, CommodityLoanStatus, ShareLoanStatus, BANK_NAME, BANK_DESCRIPTION,
            BANK_PLAYER_ID, get_db as get_firm_db
        )
        
        firm = get_firm_entity()
        player_credit = get_player_credit(player.id)
        is_solvent = firm_is_solvent()
        
        db = get_firm_db()
        try:
            # Get player's equity positions
            equity_positions = db.query(ShareholderPosition).filter(
                ShareholderPosition.player_id == player.id,
                ShareholderPosition.shares_owned > 0
            ).all()
            
            # Get player's margin positions
            margin_positions = db.query(ShareholderPosition).filter(
                ShareholderPosition.player_id == player.id,
                ShareholderPosition.margin_debt > 0
            ).all()
            
            # Get player's active short positions
            short_positions = db.query(ShareLoan).filter(
                ShareLoan.borrower_player_id == player.id,
                ShareLoan.status == ShareLoanStatus.ACTIVE.value
            ).all()
            
            # Get player's commodity loans (as borrower)
            commodity_loans = db.query(CommodityLoan).filter(
                CommodityLoan.borrower_player_id == player.id,
                CommodityLoan.status.in_([CommodityLoanStatus.ACTIVE.value, CommodityLoanStatus.LATE.value])
            ).all()
            
            # Get player's brokerage liens
            liens = db.query(BrokerageLien).filter(
                BrokerageLien.player_id == player.id
            ).all()
            total_lien_debt = sum(l.principal + l.interest_accrued - l.total_paid for l in liens)
            
            # Get active margin calls
            margin_calls = db.query(MarginCall).filter(
                MarginCall.player_id == player.id,
                MarginCall.is_resolved == False
            ).all()
            
            # Get all public companies for ticker
            public_companies = db.query(CompanyShares).filter(
                CompanyShares.is_delisted == False
            ).all()
            
            # Calculate player's total portfolio value
            total_equity_value = 0.0
            for pos in equity_positions:
                company = db.query(CompanyShares).filter(CompanyShares.id == pos.company_shares_id).first()
                if company:
                    total_equity_value += pos.shares_owned * company.current_price
            
            total_margin_debt = sum(p.margin_debt + p.margin_interest_accrued for p in margin_positions)
            
        finally:
            db.close()
        
        # Build company ticker HTML
        ticker_items = []
        for company in public_companies:
            change_indicator = "▲" if company.current_price >= company.ipo_price else "▼"
            change_color = "#22c55e" if company.current_price >= company.ipo_price else "#ef4444"
            ticker_items.append(
                f'<span style="color: {change_color};">{company.ticker_symbol}</span>: ${company.current_price:.2f} {change_indicator}'
            )
        company_ticker = " &nbsp;│&nbsp; ".join(ticker_items) if ticker_items else "NO LISTED COMPANIES"
        
        # Credit tier badge colors
        tier_colors = {
            "prime": "#22c55e",
            "standard": "#38bdf8",
            "fair": "#f59e0b",
            "subprime": "#ef4444",
            "junk": "#7f1d1d"
        }
        tier_color = tier_colors.get(player_credit.tier, "#64748b")
        
        # Margin call warning
        margin_call_html = ""
        if margin_calls:
            total_required = sum(mc.amount_required for mc in margin_calls)
            margin_call_html = f'''
            <div class="card" style="border: 2px solid #ef4444; background: #450a0a;">
                <h3 style="color: #fca5a5;">📞 MARGIN CALL ACTIVE</h3>
                <p style="color: #fca5a5;">You must deposit ${total_required:,.2f} or your positions will be liquidated.</p>
                <p style="color: #f87171; font-size: 0.9rem;">Deadline: {margin_calls[0].deadline.strftime("%Y-%m-%d %H:%M UTC")}</p>
            </div>
            '''
        
        # Insolvency warning
        insolvency_html = ""
        if not is_solvent:
            insolvency_html = '''
            <div class="card" style="border: 2px solid #ef4444; background: #450a0a;">
                <h3 style="color: #fca5a5;">⚠️ FIRM INSOLVENT</h3>
                <p style="color: #fca5a5;">The Brokerage Firm is currently insolvent. Some operations may be suspended.</p>
            </div>
            '''
        
        body = f'''
        <!-- SCPE Company Ticker (slower scroll) -->
        <div style="background: #0f172a; border: 1px solid #1e293b; padding: 8px 0; margin-bottom: 20px; overflow: hidden;">
            <div style="font-size: 0.75rem; color: #64748b; padding: 0 12px; margin-bottom: 4px;">SCPE PLAYER EXCHANGE</div>
            <marquee scrollamount="8" style="font-size: 0.85rem; color: #e5e7eb;">
                {company_ticker} &nbsp;&nbsp;&nbsp; {company_ticker}
            </marquee>
        </div>
        
        <a href="/banks" style="color: #38bdf8;">← Banks</a>
        <h1>{BANK_NAME}</h1>
        <p style="color: #64748b;">{BANK_DESCRIPTION}</p>
        
        {insolvency_html}
        {margin_call_html}
        
        <!-- Quick Stats Row -->
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin: 20px 0;">
            <div class="card" style="text-align: center;">
                <div style="font-size: 0.8rem; color: #64748b;">CREDIT RATING</div>
                <div style="font-size: 1.8rem; font-weight: bold; color: {tier_color};">{player_credit.credit_score}</div>
                <div style="font-size: 0.75rem; color: {tier_color}; text-transform: uppercase;">{player_credit.tier}</div>
            </div>
            <div class="card" style="text-align: center;">
                <div style="font-size: 0.8rem; color: #64748b;">PORTFOLIO VALUE</div>
                <div style="font-size: 1.8rem; font-weight: bold; color: #38bdf8;">${total_equity_value:,.0f}</div>
                <div style="font-size: 0.75rem; color: #64748b;">{len(equity_positions)} position(s)</div>
            </div>
            <div class="card" style="text-align: center;">
                <div style="font-size: 0.8rem; color: #64748b;">MARGIN DEBT</div>
                <div style="font-size: 1.8rem; font-weight: bold; color: {'#ef4444' if total_margin_debt > 0 else '#22c55e'};">${total_margin_debt:,.0f}</div>
                <div style="font-size: 0.75rem; color: #64748b;">{len(margin_positions)} margin position(s)</div>
            </div>
            <div class="card" style="text-align: center;">
                <div style="font-size: 0.8rem; color: #64748b;">LIEN BALANCE</div>
                <div style="font-size: 1.8rem; font-weight: bold; color: {'#ef4444' if total_lien_debt > 0 else '#22c55e'};">${total_lien_debt:,.0f}</div>
                <div style="font-size: 0.75rem; color: #64748b;">{len(liens)} active lien(s)</div>
            </div>
        </div>
        
        <!-- Firm Status -->
        <div class="card">
            <h3>Firm Status</h3>
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px;">
                <div>
                    <p><strong>Cash Reserves:</strong> ${firm.cash_reserves:,.2f}</p>
                    <p><strong>Status:</strong> <span style="color: {'#22c55e' if is_solvent else '#ef4444'};">{'SOLVENT' if is_solvent else 'INSOLVENT'}</span></p>
                </div>
                <div>
                    <p><strong>IPO Underwriting:</strong> <span style="color: {'#22c55e' if firm.is_accepting_ipos else '#ef4444'};">{'ACTIVE' if firm.is_accepting_ipos else 'SUSPENDED'}</span></p>
                    <p><strong>Margin Trading:</strong> <span style="color: {'#22c55e' if firm.is_accepting_margin else '#ef4444'};">{'ACTIVE' if firm.is_accepting_margin else 'SUSPENDED'}</span></p>
                </div>
                <div>
                    <p><strong>Commodity Lending:</strong> <span style="color: {'#22c55e' if firm.is_accepting_lending else '#ef4444'};">{'ACTIVE' if firm.is_accepting_lending else 'SUSPENDED'}</span></p>
                    <p><strong>Your Max Leverage:</strong> {get_player_credit(player.id).credit_score}x based on credit</p>
                </div>
            </div>
        </div>
        
        <!-- Navigation Cards -->
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-top: 20px;">
            <div class="card">
                <h3>📈 SCPE Trading</h3>
                <p style="color: #64748b; font-size: 0.9rem;">Buy and sell player company shares</p>
                <a href="/brokerage/trading" class="btn-blue" style="display: inline-block; margin-top: 10px;">Trade Equities</a>
            </div>
            <div class="card">
                <h3>🏢 IPO Center</h3>
                <p style="color: #64748b; font-size: 0.9rem;">Take your business public</p>
                <a href="/brokerage/ipo" class="btn-blue" style="display: inline-block; margin-top: 10px;">Launch IPO</a>
            </div>
            <div class="card">
                <h3>📊 My Portfolio</h3>
                <p style="color: #64748b; font-size: 0.9rem;">View your equity positions</p>
                <a href="/brokerage/portfolio" class="btn-blue" style="display: inline-block; margin-top: 10px;">View Holdings</a>
            </div>
            <div class="card">
                <h3>📉 Short Selling</h3>
                <p style="color: #64748b; font-size: 0.9rem;">Bet against player companies</p>
                <a href="/brokerage/shorts" class="btn-orange" style="display: inline-block; margin-top: 10px;">Short Stocks</a>
            </div>
            <div class="card">
                <h3>🌾 Commodity Lending</h3>
                <p style="color: #64748b; font-size: 0.9rem;">Borrow or lend commodities</p>
                <a href="/brokerage/commodities" class="btn-orange" style="display: inline-block; margin-top: 10px;">SCCE Market</a>
            </div>
            <div class="card">
                <h3>💳 Credit & Liens</h3>
                <p style="color: #64748b; font-size: 0.9rem;">Your credit rating and debts</p>
                <a href="/brokerage/credit" class="btn-blue" style="display: inline-block; margin-top: 10px;">View Credit</a>
            </div>
        </div>
        
        <!-- Active Positions Summary -->
        <div class="card" style="margin-top: 20px;">
            <h3>Active Positions Summary</h3>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                <div>
                    <h4 style="color: #38bdf8; margin-bottom: 10px;">Short Positions ({len(short_positions)})</h4>
                    {generate_short_positions_summary(short_positions) if short_positions else '<p style="color: #64748b;">No active short positions</p>'}
                </div>
                <div>
                    <h4 style="color: #f59e0b; margin-bottom: 10px;">Commodity Loans ({len(commodity_loans)})</h4>
                    {generate_commodity_loans_summary(commodity_loans) if commodity_loans else '<p style="color: #64748b;">No active commodity loans</p>'}
                </div>
            </div>
        </div>
        '''
        
        return shell(BANK_NAME, body, player.cash_balance, player.id)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return shell("Brokerage Firm", f"Error loading brokerage firm: {e}", player.cash_balance, player.id)


@router.get("/brokerage/trading", response_class=HTMLResponse)
def brokerage_trading_page(session_token: Optional[str] = Cookie(None), ticker: str = None):
    """SCPE equity trading page."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player

    try:
        from banks.brokerage_firm import (
            CompanyShares, ShareholderPosition, get_player_credit,
            calculate_margin_multiplier, get_db as get_firm_db, BANK_PLAYER_ID
        )
        
        db = get_firm_db()
        try:
            # Get all public companies
            companies = db.query(CompanyShares).filter(
                CompanyShares.is_delisted == False
            ).order_by(CompanyShares.ticker_symbol).all()
            
            # Get player's positions
            player_positions = {
                pos.company_shares_id: pos 
                for pos in db.query(ShareholderPosition).filter(
                    ShareholderPosition.player_id == player.id
                ).all()
            }
            
            # Selected company details
            selected_company = None
            if ticker:
                selected_company = db.query(CompanyShares).filter(
                    CompanyShares.ticker_symbol == ticker.upper(),
                    CompanyShares.is_delisted == False
                ).first()
            elif companies:
                selected_company = companies[0]
            
            player_credit = get_player_credit(player.id)
            
        finally:
            db.close()
        
        # Build company selector tabs
        company_tabs = '<div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 20px;">'
        for company in companies:
            is_selected = selected_company and company.id == selected_company.id
            tab_style = "background: #38bdf8; color: #020617;" if is_selected else "background: #1e293b; color: #94a3b8;"
            company_tabs += f'''
            <a href="/brokerage/trading?ticker={company.ticker_symbol}" 
               style="padding: 8px 16px; border-radius: 4px; text-decoration: none; {tab_style}">
                {company.ticker_symbol}
            </a>'''
        company_tabs += '</div>'
        
        if not selected_company:
            body = f'''
            <a href="/banks/brokerage-firm" style="color: #38bdf8;">← Brokerage Firm</a>
            <h1>SCPE Trading Floor</h1>
            <p style="color: #64748b;">No companies are currently listed on the exchange.</p>
            <a href="/brokerage/ipo" class="btn-blue">Launch the First IPO</a>
            '''
            return shell("SCPE Trading", body, player.cash_balance, player.id)
        
        # Get player's position in selected company
        player_position = player_positions.get(selected_company.id)
        player_shares = player_position.shares_owned if player_position else 0
        player_cost_basis = player_position.average_cost_basis if player_position else 0
        
        # Calculate margin multiplier for this stock
        max_margin = calculate_margin_multiplier(player.id, selected_company.id)
        
        # Trading halted check
        is_halted = selected_company.trading_halted_until and datetime.utcnow() < selected_company.trading_halted_until
        
        # Build dividend info
        dividend_html = ""
        if selected_company.dividend_config:
            dividend_html = '<div style="margin-top: 15px;"><strong>Dividends:</strong><ul style="margin: 5px 0; padding-left: 20px;">'
            for div in selected_company.dividend_config:
                div_type = div.get("type", "unknown")
                freq = div.get("frequency", "unknown")
                if div_type == "cash":
                    dividend_html += f'<li>Cash: {div.get("amount", 0)*100:.1f}% {div.get("basis", "fixed")} ({freq})</li>'
                elif div_type == "commodity":
                    dividend_html += f'<li>{div.get("item", "item")}: {div.get("amount", 0)} per {div.get("per_shares", 100)} shares ({freq})</li>'
                elif div_type == "scrip":
                    dividend_html += f'<li>Stock dividend: {div.get("rate", 0)*100:.1f}% ({freq})</li>'
            dividend_html += '</ul></div>'
        
        body = f'''
        <a href="/banks/brokerage-firm" style="color: #38bdf8;">← Brokerage Firm</a>
        <h1>SCPE Trading Floor</h1>
        
        {company_tabs}
        
        {"<div class='card' style='border: 2px solid #f59e0b; background: #451a03;'><h3 style='color: #fbbf24;'>🛑 TRADING HALTED</h3><p style='color: #fbbf24;'>Circuit breaker active until " + selected_company.trading_halted_until.strftime("%H:%M UTC") + "</p></div>" if is_halted else ""}
        
        <!-- Company Info Card -->
        <div class="card">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <h2 style="margin: 0;">{selected_company.company_name}</h2>
                    <p style="color: #64748b; margin: 5px 0;">
                        {selected_company.ticker_symbol} · Class {selected_company.share_class} · 
                        {"🛡️ TBTF Protected" if selected_company.is_tbtf else "Standard"}
                    </p>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 2rem; font-weight: bold; color: #38bdf8;">${selected_company.current_price:.4f}</div>
                    <div style="font-size: 0.85rem; color: #64748b;">
                        IPO: ${selected_company.ipo_price:.4f} | 
                        52W: ${selected_company.low_52_week:.2f} - ${selected_company.high_52_week:.2f}
                    </div>
                </div>
            </div>
            
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-top: 20px;">
                <div>
                    <div style="color: #64748b; font-size: 0.8rem;">Market Cap</div>
                    <div style="font-size: 1.2rem;">${selected_company.current_price * selected_company.shares_outstanding:,.0f}</div>
                </div>
                <div>
                    <div style="color: #64748b; font-size: 0.8rem;">Shares Outstanding</div>
                    <div style="font-size: 1.2rem;">{selected_company.shares_outstanding:,}</div>
                </div>
                <div>
                    <div style="color: #64748b; font-size: 0.8rem;">Float (Tradeable)</div>
                    <div style="font-size: 1.2rem;">{selected_company.shares_in_float:,}</div>
                </div>
                <div>
                    <div style="color: #64748b; font-size: 0.8rem;">Dividend Streak</div>
                    <div style="font-size: 1.2rem;">{selected_company.consecutive_dividend_payouts}</div>
                </div>
            </div>
            
            {dividend_html}
        </div>
        
        <!-- Your Position -->
        <div class="card">
            <h3>Your Position</h3>
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px;">
                <div>
                    <div style="color: #64748b; font-size: 0.8rem;">Shares Owned</div>
                    <div style="font-size: 1.5rem; color: #38bdf8;">{player_shares:,}</div>
                </div>
                <div>
                    <div style="color: #64748b; font-size: 0.8rem;">Market Value</div>
                    <div style="font-size: 1.5rem;">${player_shares * selected_company.current_price:,.2f}</div>
                </div>
                <div>
                    <div style="color: #64748b; font-size: 0.8rem;">Avg Cost Basis</div>
                    <div style="font-size: 1.5rem;">${player_cost_basis:.4f}</div>
                </div>
                <div>
                    <div style="color: #64748b; font-size: 0.8rem;">P/L</div>
                    <div style="font-size: 1.5rem; color: {'#22c55e' if (selected_company.current_price - player_cost_basis) >= 0 else '#ef4444'};">
                        ${(selected_company.current_price - player_cost_basis) * player_shares:,.2f}
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Trading Forms -->
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 20px;">
            <!-- Buy Form -->
            <div class="card" style="border-left: 4px solid #22c55e;">
                <h3 style="color: #22c55e;">Buy Shares</h3>
                <form action="/api/brokerage/buy" method="post">
                    <input type="hidden" name="company_id" value="{selected_company.id}">
                    
                    <div style="margin-bottom: 15px;">
                        <label style="display: block; margin-bottom: 5px; color: #94a3b8;">Quantity</label>
                        <input type="number" name="quantity" min="1" required 
                               style="width: 100%; padding: 10px;" placeholder="Number of shares">
                    </div>
                    
                    <div style="margin-bottom: 15px;">
                        <label style="display: flex; align-items: center; gap: 8px; color: #94a3b8;">
                            <input type="checkbox" name="use_margin" value="1">
                            Use Margin (up to {max_margin:.1f}x leverage)
                        </label>
                        <p style="font-size: 0.8rem; color: #64748b; margin-top: 5px;">
                            Your credit: {player_credit.credit_score} ({player_credit.tier.upper()})
                        </p>
                    </div>
                    
                    <button type="submit" class="btn-blue" style="width: 100%; padding: 12px; background: #22c55e;" 
                            {"disabled" if is_halted else ""}>
                        Buy at ${selected_company.current_price:.4f}
                    </button>
                </form>
            </div>
            
            <!-- Sell Form -->
            <div class="card" style="border-left: 4px solid #ef4444;">
                <h3 style="color: #ef4444;">Sell Shares</h3>
                <form action="/api/brokerage/sell" method="post">
                    <input type="hidden" name="company_id" value="{selected_company.id}">
                    
                    <div style="margin-bottom: 15px;">
                        <label style="display: block; margin-bottom: 5px; color: #94a3b8;">Quantity</label>
                        <input type="number" name="quantity" min="1" max="{player_shares}" required 
                               style="width: 100%; padding: 10px;" placeholder="Max: {player_shares}">
                    </div>
                    
                    <p style="color: #64748b; font-size: 0.85rem; margin-bottom: 15px;">
                        Available to sell: {player_shares:,} shares
                    </p>
                    
                    <button type="submit" class="btn-red" style="width: 100%; padding: 12px;" 
                            {"disabled" if is_halted or player_shares == 0 else ""}>
                        Sell at ${selected_company.current_price:.4f}
                    </button>
                </form>
            </div>
        </div>
        
        <!-- Short Selling Link -->
        <div class="card" style="margin-top: 20px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h3>Short This Stock</h3>
                    <p style="color: #64748b;">Borrow shares and sell them, betting the price will drop.</p>
                </div>
                <a href="/brokerage/shorts?ticker={selected_company.ticker_symbol}" class="btn-orange">
                    Open Short Position
                </a>
            </div>
        </div>
        '''
        
        return shell(f"Trade {selected_company.ticker_symbol}", body, player.cash_balance, player.id)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return shell("SCPE Trading", f"Error: {e}", player.cash_balance, player.id)


@router.get("/brokerage/ipo", response_class=HTMLResponse)
def brokerage_ipo_page(session_token: Optional[str] = Cookie(None)):
    """IPO creation page."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player

    try:
        from banks.brokerage_firm import (
            get_firm_entity, IPO_CONFIG, IPOType, DividendType, DividendFrequency,
            calculate_business_valuation, CompanyShares, get_db as get_firm_db
        )
        from business import Business, BUSINESS_TYPES
        from land import get_db as get_land_db
        
        firm = get_firm_entity()
        
        # Get player's businesses that aren't already public
        land_db = get_land_db()
        firm_db = get_firm_db()
        try:
            player_businesses = land_db.query(Business).filter(
                Business.owner_id == player.id
            ).all()
            
            # Filter out already-public businesses
            public_business_ids = {
                cs.business_id for cs in firm_db.query(CompanyShares).filter(
                    CompanyShares.is_delisted == False
                ).all()
            }
            
            eligible_businesses = [
                b for b in player_businesses 
                if b.id not in public_business_ids
            ]
            
        finally:
            land_db.close()
            firm_db.close()
        
        # Build IPO type options
        direct_ipos = []
        underwritten_ipos = []
        for ipo_type, config in IPO_CONFIG.items():
            ipo_html = f'''
            <option value="{ipo_type.value}" data-underwritten="{1 if config['firm_underwritten'] else 0}">
                {config['name']} - {config['description'][:50]}...
            </option>'''
            if config['firm_underwritten']:
                underwritten_ipos.append(ipo_html)
            else:
                direct_ipos.append(ipo_html)
        
        # Build business selector
        business_options = ""
        for biz in eligible_businesses:
            config = BUSINESS_TYPES.get(biz.business_type, {})
            valuation = calculate_business_valuation(biz.id)
            val_str = f"${valuation['total_valuation']:,.0f}" if valuation else "N/A"
            business_options += f'<option value="{biz.id}">{config.get("name", biz.business_type)} (ID: {biz.id}) - Est. Value: {val_str}</option>'
        
        body = f'''
        <a href="/banks/brokerage-firm" style="color: #38bdf8;">← Brokerage Firm</a>
        <h1>IPO Center</h1>
        <p style="color: #64748b;">Take your business public on the SymCo Player Exchange (SCPE)</p>
        
        {"<div class='card' style='border: 2px solid #f59e0b; background: #451a03;'><p style='color: #fbbf24;'>⚠️ The Firm is not currently accepting IPO underwriting. Only direct-to-market IPOs are available.</p></div>" if not firm.is_accepting_ipos else ""}
        
        <div class="card">
            <h3>Create IPO</h3>
            
            {f"<p style='color: #ef4444;'>You have no eligible businesses. Build a business first!</p><a href='/land' class='btn-blue'>Go to Land</a>" if not eligible_businesses else f'''
            <form action="/api/brokerage/create-ipo" method="post">
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                    <div>
                        <div style="margin-bottom: 15px;">
                            <label style="display: block; margin-bottom: 5px; color: #94a3b8;">Select Business</label>
                            <select name="business_id" required style="width: 100%; padding: 10px;">
                                <option value="">Choose a business...</option>
                                {business_options}
                            </select>
                        </div>
                        
                        <div style="margin-bottom: 15px;">
                            <label style="display: block; margin-bottom: 5px; color: #94a3b8;">Company Name</label>
                            <input type="text" name="company_name" required style="width: 100%; padding: 10px;" 
                                   placeholder="e.g., Acme Corporation">
                        </div>
                        
                        <div style="margin-bottom: 15px;">
                            <label style="display: block; margin-bottom: 5px; color: #94a3b8;">Ticker Symbol (3-5 chars)</label>
                            <input type="text" name="ticker_symbol" required maxlength="5" style="width: 100%; padding: 10px; text-transform: uppercase;" 
                                   placeholder="e.g., ACME">
                        </div>
                        
                        <div style="margin-bottom: 15px;">
                            <label style="display: block; margin-bottom: 5px; color: #94a3b8;">Share Class</label>
                            <select name="share_class" style="width: 100%; padding: 10px;">
                                <option value="A">Class A (Standard)</option>
                                <option value="B">Class B (Reduced Voting)</option>
                                <option value="Preferred">Preferred (Priority Dividend)</option>
                            </select>
                        </div>
                    </div>
                    
                    <div>
                        <div style="margin-bottom: 15px;">
                            <label style="display: block; margin-bottom: 5px; color: #94a3b8;">IPO Type</label>
                            <select name="ipo_type" required style="width: 100%; padding: 10px;">
                                <optgroup label="Direct-to-Market (No Firm Commitment)">
                                    {"".join(direct_ipos)}
                                </optgroup>
                                <optgroup label="Firm-Underwritten (Guaranteed Sale)">
                                    {"".join(underwritten_ipos)}
                                </optgroup>
                            </select>
                        </div>
                        
                        <div style="margin-bottom: 15px;">
                            <label style="display: block; margin-bottom: 5px; color: #94a3b8;">Total Shares to Authorize</label>
                            <input type="number" name="total_shares" required min="1000" value="10000" 
                                   style="width: 100%; padding: 10px;">
                        </div>
                        
                        <div style="margin-bottom: 15px;">
                            <label style="display: block; margin-bottom: 5px; color: #94a3b8;">Shares to Offer (% of total)</label>
                            <input type="number" name="offer_percentage" required min="1" max="100" value="25" 
                                   style="width: 100%; padding: 10px;">
                            <p style="font-size: 0.8rem; color: #64748b; margin-top: 5px;">
                                You keep the rest. Offering more = more capital raised.
                            </p>
                        </div>
                    </div>
                </div>
                
                <!-- Dividend Configuration -->
                <div style="margin-top: 20px; padding-top: 20px; border-top: 1px solid #1e293b;">
                    <h4>Dividend Configuration (Optional)</h4>
                    <p style="color: #64748b; font-size: 0.85rem; margin-bottom: 15px;">
                        Dividends attract investors but commit you to regular payments.
                    </p>
                    
                    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px;">
                        <div>
                            <label style="display: block; margin-bottom: 5px; color: #94a3b8;">Type</label>
                            <select name="dividend_type" style="width: 100%; padding: 10px;">
                                <option value="">No Dividend</option>
                                <option value="cash">Cash</option>
                                <option value="commodity">Commodity</option>
                                <option value="scrip">Stock (Scrip)</option>
                            </select>
                        </div>
                        <div>
                            <label style="display: block; margin-bottom: 5px; color: #94a3b8;">Amount/Rate</label>
                            <input type="number" name="dividend_amount" step="0.01" min="0" 
                                   style="width: 100%; padding: 10px;" placeholder="e.g., 0.05 for 5%">
                        </div>
                        <div>
                            <label style="display: block; margin-bottom: 5px; color: #94a3b8;">Frequency</label>
                            <select name="dividend_frequency" style="width: 100%; padding: 10px;">
                                <option value="weekly">Weekly</option>
                                <option value="biweekly">Bi-Weekly</option>
                                <option value="monthly">Monthly</option>
                                <option value="quarterly">Quarterly</option>
                            </select>
                        </div>
                        <div>
                            <label style="display: block; margin-bottom: 5px; color: #94a3b8;">Commodity (if applicable)</label>
                            <input type="text" name="dividend_commodity" style="width: 100%; padding: 10px;" 
                                   placeholder="e.g., apple_seeds">
                        </div>
                    </div>
                </div>
                
                <button type="submit" class="btn-blue" style="width: 100%; padding: 15px; margin-top: 20px; font-size: 1.1rem;">
                    🚀 Launch IPO
                </button>
            </form>
            '''}
        </div>
        
        <!-- IPO Types Reference -->
        <div class="card" style="margin-top: 20px;">
            <h3>IPO Types Reference</h3>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                <div>
                    <h4 style="color: #38bdf8;">Direct-to-Market</h4>
                    <ul style="color: #94a3b8; line-height: 1.8;">
                        <li><strong>Dutch Auction:</strong> Players bid, highest bids win at clearing price (3% fee)</li>
                        <li><strong>Private Placement:</strong> Sell to one specific player (1% fee)</li>
                        <li><strong>Rights Offering:</strong> Existing shareholders only (2% fee)</li>
                        <li><strong>Direct Listing:</strong> List existing shares, no new capital ($5k flat)</li>
                    </ul>
                </div>
                <div>
                    <h4 style="color: #f59e0b;">Firm-Underwritten</h4>
                    <ul style="color: #94a3b8; line-height: 1.8;">
                        <li><strong>Standard:</strong> Firm buys at 85%, resells (guaranteed capital)</li>
                        <li><strong>Best Efforts:</strong> Firm tries to sell, returns unsold (8% fee)</li>
                        <li><strong>Bought Deal:</strong> Firm buys ALL at 80% (higher risk premium)</li>
                        <li><strong>Stabilized:</strong> Price floor protection (88% + commitment)</li>
                        <li><strong>Drip Release:</strong> Scarcity strategy, 5%/week release (75%)</li>
                        <li><strong>Shelf Registration:</strong> Draw down over time (10%/tranche)</li>
                    </ul>
                </div>
            </div>
        </div>
        '''
        
        return shell("IPO Center", body, player.cash_balance, player.id)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return shell("IPO Center", f"Error: {e}", player.cash_balance, player.id)


@router.get("/brokerage/portfolio", response_class=HTMLResponse)
def brokerage_portfolio_page(session_token: Optional[str] = Cookie(None)):
    """Player's equity portfolio page."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player

    try:
        from banks.brokerage_firm import (
            CompanyShares, ShareholderPosition, get_db as get_firm_db
        )
        
        db = get_firm_db()
        try:
            # Get all player positions
            positions = db.query(ShareholderPosition).filter(
                ShareholderPosition.player_id == player.id,
                ShareholderPosition.shares_owned > 0
            ).all()
            
            portfolio_data = []
            total_value = 0.0
            total_cost = 0.0
            total_margin_debt = 0.0
            
            for pos in positions:
                company = db.query(CompanyShares).filter(
                    CompanyShares.id == pos.company_shares_id
                ).first()
                
                if company:
                    market_value = pos.shares_owned * company.current_price
                    cost_basis_total = pos.shares_owned * pos.average_cost_basis
                    pnl = market_value - cost_basis_total
                    pnl_pct = (pnl / cost_basis_total * 100) if cost_basis_total > 0 else 0
                    
                    portfolio_data.append({
                        "company": company,
                        "position": pos,
                        "market_value": market_value,
                        "cost_basis_total": cost_basis_total,
                        "pnl": pnl,
                        "pnl_pct": pnl_pct
                    })
                    
                    total_value += market_value
                    total_cost += cost_basis_total
                    total_margin_debt += pos.margin_debt
            
        finally:
            db.close()
        
        total_pnl = total_value - total_cost
        total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0
        
        # Build portfolio table
        portfolio_html = ""
        if portfolio_data:
            portfolio_html = '''
            <table style="width: 100%; border-collapse: collapse;">
                <thead>
                    <tr style="border-bottom: 1px solid #1e293b; text-align: left;">
                        <th style="padding: 12px 8px;">Symbol</th>
                        <th style="padding: 12px 8px;">Shares</th>
                        <th style="padding: 12px 8px;">Price</th>
                        <th style="padding: 12px 8px;">Market Value</th>
                        <th style="padding: 12px 8px;">Cost Basis</th>
                        <th style="padding: 12px 8px;">P/L</th>
                        <th style="padding: 12px 8px;">Margin</th>
                        <th style="padding: 12px 8px;">Actions</th>
                    </tr>
                </thead>
                <tbody>'''
            
            for item in portfolio_data:
                company = item["company"]
                pos = item["position"]
                pnl_color = "#22c55e" if item["pnl"] >= 0 else "#ef4444"
                margin_badge = f'<span class="badge" style="background: #f59e0b;">MARGIN</span>' if pos.is_margin_position else ""
                
                portfolio_html += f'''
                <tr style="border-bottom: 1px solid #1e293b;">
                    <td style="padding: 12px 8px;">
                        <strong>{company.ticker_symbol}</strong> {margin_badge}<br>
                        <span style="color: #64748b; font-size: 0.85rem;">{company.company_name[:20]}</span>
                    </td>
                    <td style="padding: 12px 8px;">{pos.shares_owned:,}</td>
                    <td style="padding: 12px 8px;">${company.current_price:.4f}</td>
                    <td style="padding: 12px 8px;">${item["market_value"]:,.2f}</td>
                    <td style="padding: 12px 8px;">${pos.average_cost_basis:.4f}</td>
                    <td style="padding: 12px 8px; color: {pnl_color};">
                        ${item["pnl"]:,.2f}<br>
                        <span style="font-size: 0.85rem;">({item["pnl_pct"]:+.1f}%)</span>
                    </td>
                    <td style="padding: 12px 8px;">
                        {"${:,.2f}".format(pos.margin_debt) if pos.margin_debt > 0 else "-"}
                    </td>
                    <td style="padding: 12px 8px;">
                        <a href="/brokerage/trading?ticker={company.ticker_symbol}" class="btn-blue" style="font-size: 0.8rem; padding: 4px 8px;">Trade</a>
                    </td>
                </tr>'''
            
            portfolio_html += '</tbody></table>'
        else:
            portfolio_html = '<p style="color: #64748b;">You have no equity positions. <a href="/brokerage/trading">Start trading!</a></p>'
        
        body = f'''
        <a href="/banks/brokerage-firm" style="color: #38bdf8;">← Brokerage Firm</a>
        <h1>My Portfolio</h1>
        
        <!-- Portfolio Summary -->
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 20px;">
            <div class="card" style="text-align: center;">
                <div style="font-size: 0.8rem; color: #64748b;">TOTAL VALUE</div>
                <div style="font-size: 1.8rem; font-weight: bold; color: #38bdf8;">${total_value:,.2f}</div>
            </div>
            <div class="card" style="text-align: center;">
                <div style="font-size: 0.8rem; color: #64748b;">TOTAL COST</div>
                <div style="font-size: 1.8rem; font-weight: bold;">${total_cost:,.2f}</div>
            </div>
            <div class="card" style="text-align: center;">
                <div style="font-size: 0.8rem; color: #64748b;">TOTAL P/L</div>
                <div style="font-size: 1.8rem; font-weight: bold; color: {'#22c55e' if total_pnl >= 0 else '#ef4444'};">
                    ${total_pnl:,.2f}
                </div>
                <div style="font-size: 0.85rem; color: {'#22c55e' if total_pnl >= 0 else '#ef4444'};">
                    ({total_pnl_pct:+.1f}%)
                </div>
            </div>
            <div class="card" style="text-align: center;">
                <div style="font-size: 0.8rem; color: #64748b;">MARGIN DEBT</div>
                <div style="font-size: 1.8rem; font-weight: bold; color: {'#ef4444' if total_margin_debt > 0 else '#22c55e'};">
                    ${total_margin_debt:,.2f}
                </div>
            </div>
        </div>
        
        <!-- Holdings Table -->
        <div class="card">
            <h3>Holdings</h3>
            {portfolio_html}
        </div>
        '''
        
        return shell("My Portfolio", body, player.cash_balance, player.id)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return shell("My Portfolio", f"Error: {e}", player.cash_balance, player.id)


@router.get("/brokerage/shorts", response_class=HTMLResponse)
def brokerage_shorts_page(session_token: Optional[str] = Cookie(None), ticker: str = None):
    """Short selling page."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player

    try:
        from banks.brokerage_firm import (
            CompanyShares, ShareholderPosition, ShareLoan, ShareLoanStatus,
            get_player_credit, SHORT_COLLATERAL_REQUIREMENT,
            get_db as get_firm_db
        )
        
        db = get_firm_db()
        try:
            # Get all public companies
            companies = db.query(CompanyShares).filter(
                CompanyShares.is_delisted == False
            ).order_by(CompanyShares.ticker_symbol).all()
            
            # Get player's active shorts
            active_shorts = db.query(ShareLoan).filter(
                ShareLoan.borrower_player_id == player.id,
                ShareLoan.status == ShareLoanStatus.ACTIVE.value
            ).all()
            
            # Build short positions data
            short_data = []
            for short in active_shorts:
                company = db.query(CompanyShares).filter(
                    CompanyShares.id == short.company_shares_id
                ).first()
                if company:
                    current_value = short.shares_borrowed * company.current_price
                    original_value = short.shares_borrowed * short.borrow_price
                    pnl = original_value - current_value  # Profit if price dropped
                    short_data.append({
                        "loan": short,
                        "company": company,
                        "current_value": current_value,
                        "original_value": original_value,
                        "pnl": pnl
                    })
            
            # Selected company for new short
            selected_company = None
            available_to_short = 0
            if ticker:
                selected_company = db.query(CompanyShares).filter(
                    CompanyShares.ticker_symbol == ticker.upper()
                ).first()
            
            if selected_company:
                # Find shares available to borrow
                available_positions = db.query(ShareholderPosition).filter(
                    ShareholderPosition.company_shares_id == selected_company.id,
                    ShareholderPosition.shares_available_to_lend > 0,
                    ShareholderPosition.player_id != player.id
                ).all()
                available_to_short = sum(p.shares_available_to_lend for p in available_positions)
            
            player_credit = get_player_credit(player.id)
            
        finally:
            db.close()
        
        # Build company selector
        company_options = ""
        for company in companies:
            selected = "selected" if selected_company and company.id == selected_company.id else ""
            company_options += f'<option value="{company.ticker_symbol}" {selected}>{company.ticker_symbol} - {company.company_name}</option>'
        
        # Build active shorts table
        shorts_html = ""
        if short_data:
            shorts_html = '''
            <table style="width: 100%; border-collapse: collapse;">
                <thead>
                    <tr style="border-bottom: 1px solid #1e293b; text-align: left;">
                        <th style="padding: 10px 8px;">Symbol</th>
                        <th style="padding: 10px 8px;">Shares</th>
                        <th style="padding: 10px 8px;">Borrow Price</th>
                        <th style="padding: 10px 8px;">Current Price</th>
                        <th style="padding: 10px 8px;">P/L</th>
                        <th style="padding: 10px 8px;">Collateral</th>
                        <th style="padding: 10px 8px;">Due Date</th>
                        <th style="padding: 10px 8px;">Action</th>
                    </tr>
                </thead>
                <tbody>'''
            
            for item in short_data:
                loan = item["loan"]
                company = item["company"]
                pnl_color = "#22c55e" if item["pnl"] >= 0 else "#ef4444"
                
                shorts_html += f'''
                <tr style="border-bottom: 1px solid #1e293b;">
                    <td style="padding: 10px 8px;"><strong>{company.ticker_symbol}</strong></td>
                    <td style="padding: 10px 8px;">{loan.shares_borrowed:,}</td>
                    <td style="padding: 10px 8px;">${loan.borrow_price:.4f}</td>
                    <td style="padding: 10px 8px;">${company.current_price:.4f}</td>
                    <td style="padding: 10px 8px; color: {pnl_color};">${item["pnl"]:,.2f}</td>
                    <td style="padding: 10px 8px;">${loan.collateral_locked:,.2f}</td>
                    <td style="padding: 10px 8px;">{loan.due_date.strftime("%m/%d %H:%M")}</td>
                    <td style="padding: 10px 8px;">
                        <form action="/api/brokerage/close-short" method="post" style="display: inline;">
                            <input type="hidden" name="loan_id" value="{loan.id}">
                            <button type="submit" class="btn-orange" style="padding: 4px 8px; font-size: 0.8rem;">Close</button>
                        </form>
                    </td>
                </tr>'''
            
            shorts_html += '</tbody></table>'
        else:
            shorts_html = '<p style="color: #64748b;">No active short positions.</p>'
        
        body = f'''
        <a href="/banks/brokerage-firm" style="color: #38bdf8;">← Brokerage Firm</a>
        <h1>Short Selling</h1>
        <p style="color: #64748b;">Borrow shares, sell them now, buy back later at (hopefully) a lower price.</p>
        
        <!-- Open New Short -->
        <div class="card">
            <h3>Open Short Position</h3>
            <form action="/api/brokerage/short-sell" method="post">
                <div style="display: grid; grid-template-columns: 1fr 1fr 1fr auto; gap: 15px; align-items: end;">
                    <div>
                        <label style="display: block; margin-bottom: 5px; color: #94a3b8;">Select Stock</label>
                        <select name="ticker" required style="width: 100%; padding: 10px;" onchange="window.location.href='/brokerage/shorts?ticker='+this.value">
                            <option value="">Choose a stock...</option>
                            {company_options}
                        </select>
                    </div>
                    <div>
                        <label style="display: block; margin-bottom: 5px; color: #94a3b8;">Shares to Short</label>
                        <input type="number" name="quantity" min="1" {"max=" + str(available_to_short) if selected_company else ""} required 
                               style="width: 100%; padding: 10px;" placeholder="{"Max: " + str(available_to_short) if selected_company else "Select stock first"}">
                    </div>
                    <div>
                        <label style="display: block; margin-bottom: 5px; color: #94a3b8;">Collateral Required</label>
                        <div style="padding: 10px; background: #020617; border: 1px solid #1e293b; border-radius: 4px;">
                            {f"${selected_company.current_price * SHORT_COLLATERAL_REQUIREMENT:,.2f}/share" if selected_company else "N/A"}
                        </div>
                    </div>
                    <button type="submit" class="btn-red" style="padding: 10px 20px;" {"disabled" if not selected_company or available_to_short == 0 else ""}>
                        Short Sell
                    </button>
                </div>
                
                {f'''
                <div style="margin-top: 15px; padding: 15px; background: #0f172a; border-radius: 4px;">
                    <p><strong>Selected:</strong> {selected_company.ticker_symbol} @ ${selected_company.current_price:.4f}</p>
                    <p><strong>Available to borrow:</strong> {available_to_short:,} shares</p>
                    <p><strong>Collateral requirement:</strong> {SHORT_COLLATERAL_REQUIREMENT*100:.0f}% (${selected_company.current_price * SHORT_COLLATERAL_REQUIREMENT:.4f}/share)</p>
                    <p style="color: #f59e0b; font-size: 0.9rem; margin-top: 10px;">
                        ⚠️ Short selling is risky. If the price rises, your losses are theoretically unlimited.
                    </p>
                </div>
                ''' if selected_company else ""}
            </form>
        </div>
        
        <!-- Active Short Positions -->
        <div class="card" style="margin-top: 20px;">
            <h3>Active Short Positions</h3>
            {shorts_html}
        </div>
        
        <!-- How It Works -->
        <div class="card" style="margin-top: 20px;">
            <h3>How Short Selling Works</h3>
            <ol style="color: #94a3b8; line-height: 2;">
                <li>You borrow shares from another player and lock {SHORT_COLLATERAL_REQUIREMENT*100:.0f}% collateral</li>
                <li>You sell the borrowed shares at the current price</li>
                <li>Later, you buy shares back (hopefully at a lower price)</li>
                <li>Return the shares and get your collateral back</li>
                <li>Your profit = Original sale price - Buyback price - Fees</li>
            </ol>
            <p style="color: #ef4444; margin-top: 15px;">
                <strong>Risk Warning:</strong> If the stock price rises, you must still buy back shares to return them. 
                Your potential loss is unlimited.
            </p>
        </div>
        '''
        
        return shell("Short Selling", body, player.cash_balance, player.id)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return shell("Short Selling", f"Error: {e}", player.cash_balance, player.id)


@router.get("/brokerage/commodities", response_class=HTMLResponse)
def brokerage_commodities_page(session_token: Optional[str] = Cookie(None)):
    """SCCE Commodity lending page."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player

    try:
        from banks.brokerage_firm import (
            CommodityListing, CommodityLoan, CommodityLoanStatus,
            COLLATERAL_REQUIREMENT, LENDING_FEE_SPLIT,
            get_db as get_firm_db
        )
        import inventory as inv_mod
        
        db = get_firm_db()
        try:
            # Get all active commodity listings
            listings = db.query(CommodityListing).filter(
                CommodityListing.is_active == True,
                CommodityListing.quantity_available > CommodityListing.quantity_lent_out
            ).all()
            
            # Get player's listings
            player_listings = db.query(CommodityListing).filter(
                CommodityListing.lender_player_id == player.id,
                CommodityListing.is_active == True
            ).all()
            
            # Get player's active loans (as borrower)
            player_loans = db.query(CommodityLoan).filter(
                CommodityLoan.borrower_player_id == player.id,
                CommodityLoan.status.in_([CommodityLoanStatus.ACTIVE.value, CommodityLoanStatus.LATE.value])
            ).all()
            
            # Get player's loans (as lender)
            lent_out = db.query(CommodityLoan).filter(
                CommodityLoan.lender_player_id == player.id,
                CommodityLoan.status.in_([CommodityLoanStatus.ACTIVE.value, CommodityLoanStatus.LATE.value])
            ).all()
            
        finally:
            db.close()
        
        # Get player inventory for listing
        player_inv = inv_mod.get_player_inventory(player.id)
        
        # Build available listings table
        listings_html = ""
        if listings:
            listings_html = '''
            <table style="width: 100%; border-collapse: collapse;">
                <thead>
                    <tr style="border-bottom: 1px solid #1e293b; text-align: left;">
                        <th style="padding: 10px 8px;">Item</th>
                        <th style="padding: 10px 8px;">Available</th>
                        <th style="padding: 10px 8px;">Weekly Rate</th>
                        <th style="padding: 10px 8px;">Lender</th>
                        <th style="padding: 10px 8px;">Action</th>
                    </tr>
                </thead>
                <tbody>'''
            
            for listing in listings:
                available = listing.quantity_available - listing.quantity_lent_out
                is_own = listing.lender_player_id == player.id
                
                listings_html += f'''
                <tr style="border-bottom: 1px solid #1e293b;">
                    <td style="padding: 10px 8px;"><strong>{listing.item_type.replace("_", " ").title()}</strong></td>
                    <td style="padding: 10px 8px;">{available:,.0f}</td>
                    <td style="padding: 10px 8px;">{listing.weekly_rate*100:.1f}%</td>
                    <td style="padding: 10px 8px;">{"YOU" if is_own else f"Player {listing.lender_player_id}"}</td>
                    <td style="padding: 10px 8px;">
                        {f'''
                        <form action="/api/brokerage/borrow-commodity" method="post" style="display: flex; gap: 5px;">
                            <input type="hidden" name="listing_id" value="{listing.id}">
                            <input type="number" name="quantity" min="1" max="{available}" placeholder="Qty" style="width: 80px; padding: 4px;">
                            <button type="submit" class="btn-blue" style="padding: 4px 8px; font-size: 0.8rem;">Borrow</button>
                        </form>
                        ''' if not is_own else "-"}
                    </td>
                </tr>'''
            
            listings_html += '</tbody></table>'
        else:
            listings_html = '<p style="color: #64748b;">No commodities available for borrowing.</p>'
        
        # Build player's loans table
        loans_html = ""
        if player_loans:
            loans_html = '''
            <table style="width: 100%; border-collapse: collapse;">
                <thead>
                    <tr style="border-bottom: 1px solid #1e293b; text-align: left;">
                        <th style="padding: 10px 8px;">Item</th>
                        <th style="padding: 10px 8px;">Qty</th>
                        <th style="padding: 10px 8px;">Collateral</th>
                        <th style="padding: 10px 8px;">Due</th>
                        <th style="padding: 10px 8px;">Status</th>
                        <th style="padding: 10px 8px;">Actions</th>
                    </tr>
                </thead>
                <tbody>'''
            
            for loan in player_loans:
                status_color = "#f59e0b" if loan.status == CommodityLoanStatus.LATE.value else "#22c55e"
                
                loans_html += f'''
                <tr style="border-bottom: 1px solid #1e293b;">
                    <td style="padding: 10px 8px;"><strong>{loan.item_type.replace("_", " ").title()}</strong></td>
                    <td style="padding: 10px 8px;">{loan.quantity_borrowed:,.0f}</td>
                    <td style="padding: 10px 8px;">${loan.collateral_locked:,.2f}</td>
                    <td style="padding: 10px 8px;">{loan.due_date.strftime("%m/%d %H:%M")}</td>
                    <td style="padding: 10px 8px; color: {status_color};">{loan.status.upper()}</td>
                    <td style="padding: 10px 8px;">
                        <form action="/api/brokerage/return-commodity" method="post" style="display: inline;">
                            <input type="hidden" name="loan_id" value="{loan.id}">
                            <button type="submit" class="btn-blue" style="padding: 4px 8px; font-size: 0.8rem;">Return</button>
                        </form>
                        <form action="/api/brokerage/extend-loan" method="post" style="display: inline; margin-left: 5px;">
                            <input type="hidden" name="loan_id" value="{loan.id}">
                            <button type="submit" class="btn-orange" style="padding: 4px 8px; font-size: 0.8rem;" 
                                    {"disabled" if loan.extensions_used >= loan.max_extensions else ""}>Extend</button>
                        </form>
                    </td>
                </tr>'''
            
            loans_html += '</tbody></table>'
        else:
            loans_html = '<p style="color: #64748b;">You have no active commodity loans.</p>'
        
        # Build inventory for listing
        inv_options = ""
        for item, qty in player_inv.items():
            if qty > 0:
                inv_options += f'<option value="{item}">{item.replace("_", " ").title()} ({qty:,.0f} available)</option>'
        
        body = f'''
        <a href="/banks/brokerage-firm" style="color: #38bdf8;">← Brokerage Firm</a>
        <h1>SCCE Commodity Exchange</h1>
        <p style="color: #64748b;">Borrow commodities from other players or lend your inventory for interest.</p>
        
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
            <!-- List Commodities for Lending -->
            <div class="card">
                <h3>List Your Commodities</h3>
                <form action="/api/brokerage/list-commodity" method="post">
                    <div style="margin-bottom: 15px;">
                        <label style="display: block; margin-bottom: 5px; color: #94a3b8;">Item to Lend</label>
                        <select name="item_type" required style="width: 100%; padding: 10px;">
                            <option value="">Select item...</option>
                            {inv_options}
                        </select>
                    </div>
                    <div style="margin-bottom: 15px;">
                        <label style="display: block; margin-bottom: 5px; color: #94a3b8;">Quantity</label>
                        <input type="number" name="quantity" min="1" required style="width: 100%; padding: 10px;">
                    </div>
                    <div style="margin-bottom: 15px;">
                        <label style="display: block; margin-bottom: 5px; color: #94a3b8;">Weekly Interest Rate (%)</label>
                        <input type="number" name="weekly_rate" min="0.1" step="0.1" value="5" required style="width: 100%; padding: 10px;">
                    </div>
                    <button type="submit" class="btn-blue" style="width: 100%;">List for Lending</button>
                </form>
                <p style="font-size: 0.8rem; color: #64748b; margin-top: 10px;">
                    You receive {(1-LENDING_FEE_SPLIT)*100:.0f}% of fees, Firm keeps {LENDING_FEE_SPLIT*100:.0f}%.
                </p>
            </div>
            
            <!-- Your Listings -->
            <div class="card">
                <h3>Your Active Listings</h3>
                {generate_player_listings_html(player_listings) if player_listings else '<p style="color: #64748b;">No active listings.</p>'}
            </div>
        </div>
        
        <!-- Available to Borrow -->
        <div class="card" style="margin-top: 20px;">
            <h3>Available to Borrow</h3>
            <p style="color: #64748b; margin-bottom: 15px;">Collateral requirement: {COLLATERAL_REQUIREMENT*100:.0f}% of market value</p>
            {listings_html}
        </div>
        
        <!-- Your Active Loans -->
        <div class="card" style="margin-top: 20px;">
            <h3>Your Active Loans (Borrowed)</h3>
            {loans_html}
        </div>
        
        <!-- Lent Out -->
        <div class="card" style="margin-top: 20px;">
            <h3>Your Commodities Lent Out</h3>
            {generate_lent_out_html(lent_out) if lent_out else '<p style="color: #64748b;">None of your commodities are currently lent out.</p>'}
        </div>
        '''
        
        return shell("SCCE Commodities", body, player.cash_balance, player.id)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return shell("SCCE Commodities", f"Error: {e}", player.cash_balance, player.id)


@router.get("/brokerage/credit", response_class=HTMLResponse)
def brokerage_credit_page(session_token: Optional[str] = Cookie(None)):
    """Credit rating and liens page."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player

    try:
        from banks.brokerage_firm import (
            get_player_credit, get_credit_tier, get_max_leverage_for_player,
            get_credit_interest_rate, BrokerageLien, CREDIT_TIERS, CREDIT_MODIFIERS,
            get_db as get_firm_db
        )
        
        player_credit = get_player_credit(player.id)
        credit_tier = get_credit_tier(player_credit.credit_score)
        max_leverage = get_max_leverage_for_player(player.id)
        interest_rate = get_credit_interest_rate(player.id)
        
        db = get_firm_db()
        try:
            liens = db.query(BrokerageLien).filter(
                BrokerageLien.player_id == player.id
            ).all()
            
            total_lien_debt = sum(l.principal + l.interest_accrued - l.total_paid for l in liens)
        finally:
            db.close()
        
        # Credit tier colors
        tier_colors = {
            "prime": "#22c55e",
            "standard": "#38bdf8",
            "fair": "#f59e0b",
            "subprime": "#ef4444",
            "junk": "#7f1d1d"
        }
        tier_color = tier_colors.get(player_credit.tier, "#64748b")
        
        # Build credit tiers reference
        tiers_html = ""
        for tier, (min_score, max_score, rate, leverage) in CREDIT_TIERS.items():
            is_current = tier == credit_tier
            border = f"border: 2px solid {tier_colors.get(tier.value, '#64748b')};" if is_current else ""
            tiers_html += f'''
            <div style="padding: 10px; background: #0f172a; border-radius: 4px; {border}">
                <div style="color: {tier_colors.get(tier.value, '#64748b')}; font-weight: bold;">{tier.value.upper()}</div>
                <div style="font-size: 0.85rem; color: #94a3b8;">Score: {min_score}-{max_score}</div>
                <div style="font-size: 0.85rem; color: #94a3b8;">Rate: {rate*100:.0f}%</div>
                <div style="font-size: 0.85rem; color: #94a3b8;">Leverage: {leverage:.0f}x</div>
            </div>'''
        
        # Build liens table
        liens_html = ""
        if liens:
            liens_html = '''
            <table style="width: 100%; border-collapse: collapse;">
                <thead>
                    <tr style="border-bottom: 1px solid #1e293b; text-align: left;">
                        <th style="padding: 10px 8px;">Source</th>
                        <th style="padding: 10px 8px;">Principal</th>
                        <th style="padding: 10px 8px;">Interest</th>
                        <th style="padding: 10px 8px;">Paid</th>
                        <th style="padding: 10px 8px;">Balance</th>
                        <th style="padding: 10px 8px;">Created</th>
                    </tr>
                </thead>
                <tbody>'''
            
            for lien in liens:
                balance = lien.principal + lien.interest_accrued - lien.total_paid
                liens_html += f'''
                <tr style="border-bottom: 1px solid #1e293b;">
                    <td style="padding: 10px 8px;">{lien.source.upper()}</td>
                    <td style="padding: 10px 8px;">${lien.principal:,.2f}</td>
                    <td style="padding: 10px 8px; color: #ef4444;">${lien.interest_accrued:,.2f}</td>
                    <td style="padding: 10px 8px; color: #22c55e;">${lien.total_paid:,.2f}</td>
                    <td style="padding: 10px 8px; font-weight: bold; color: #ef4444;">${balance:,.2f}</td>
                    <td style="padding: 10px 8px; color: #64748b;">{lien.created_at.strftime("%Y-%m-%d")}</td>
                </tr>'''
            
            liens_html += '</tbody></table>'
        else:
            liens_html = '<p style="color: #22c55e;">✓ No active liens. Your account is in good standing.</p>'
        
        body = f'''
        <a href="/banks/brokerage-firm" style="color: #38bdf8;">← Brokerage Firm</a>
        <h1>Credit Rating & Liens</h1>
        
        <!-- Credit Score Display -->
        <div class="card">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h2 style="margin: 0;">Your Credit Score</h2>
                    <p style="color: #64748b;">Based on your trading history with the Firm</p>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 4rem; font-weight: bold; color: {tier_color};">{player_credit.credit_score}</div>
                    <div style="font-size: 1.2rem; color: {tier_color}; text-transform: uppercase;">{player_credit.tier}</div>
                </div>
            </div>
            
            <!-- Credit Score Bar -->
            <div style="margin-top: 20px; background: #020617; border-radius: 8px; height: 20px; overflow: hidden;">
                <div style="width: {player_credit.credit_score}%; height: 100%; background: linear-gradient(90deg, #ef4444, #f59e0b, #22c55e); border-radius: 8px;"></div>
            </div>
            <div style="display: flex; justify-content: space-between; margin-top: 5px; font-size: 0.8rem; color: #64748b;">
                <span>0 (Junk)</span>
                <span>50 (Fair)</span>
                <span>100 (Prime)</span>
            </div>
        </div>
        
        <!-- Your Benefits -->
        <div class="card" style="margin-top: 20px;">
            <h3>Your Credit Benefits</h3>
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px;">
                <div style="text-align: center; padding: 20px; background: #0f172a; border-radius: 8px;">
                    <div style="font-size: 0.9rem; color: #64748b;">Max Leverage</div>
                    <div style="font-size: 2rem; font-weight: bold; color: #38bdf8;">{max_leverage:.1f}x</div>
                </div>
                <div style="text-align: center; padding: 20px; background: #0f172a; border-radius: 8px;">
                    <div style="font-size: 0.9rem; color: #64748b;">Interest Rate</div>
                    <div style="font-size: 2rem; font-weight: bold; color: {'#22c55e' if interest_rate < 0.05 else '#f59e0b' if interest_rate < 0.10 else '#ef4444'};">{interest_rate*100:.0f}%</div>
                </div>
                <div style="text-align: center; padding: 20px; background: #0f172a; border-radius: 8px;">
                    <div style="font-size: 0.9rem; color: #64748b;">Lien Balance</div>
                    <div style="font-size: 2rem; font-weight: bold; color: {'#ef4444' if total_lien_debt > 0 else '#22c55e'};">${total_lien_debt:,.0f}</div>
                </div>
            </div>
        </div>
        
        <!-- Credit History -->
        <div class="card" style="margin-top: 20px;">
            <h3>Credit History</h3>
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px;">
                <div>
                    <div style="color: #64748b; font-size: 0.85rem;">Total Margin Trades</div>
                    <div style="font-size: 1.5rem;">{player_credit.total_margin_trades}</div>
                </div>
                <div>
                    <div style="color: #64748b; font-size: 0.85rem;">Profitable Trades</div>
                    <div style="font-size: 1.5rem; color: #22c55e;">{player_credit.profitable_margin_trades}</div>
                </div>
                <div>
                    <div style="color: #64748b; font-size: 0.85rem;">Commodity Loans</div>
                    <div style="font-size: 1.5rem;">{player_credit.total_commodity_loans}</div>
                </div>
                <div>
                    <div style="color: #64748b; font-size: 0.85rem;">On-Time Returns</div>
                    <div style="font-size: 1.5rem; color: #22c55e;">{player_credit.on_time_returns}</div>
                </div>
            </div>
        </div>
        
        <!-- Active Liens -->
        <div class="card" style="margin-top: 20px;">
            <h3>Brokerage Liens</h3>
            {liens_html}
            {f'''
            <div style="margin-top: 15px; padding: 15px; background: #450a0a; border-radius: 4px; border: 1px solid #7f1d1d;">
                <p style="color: #fca5a5;">
                    <strong>Total Lien Debt: ${total_lien_debt:,.2f}</strong><br>
                    The Firm automatically garnishes 50% of your cash every 60 seconds to pay down liens.
                    Interest accrues at {interest_rate*100:.0f}% annually.
                </p>
            </div>
            ''' if total_lien_debt > 0 else ""}
        </div>
        
        <!-- Credit Tiers Reference -->
        <div class="card" style="margin-top: 20px;">
            <h3>Credit Tiers Reference</h3>
            <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px;">
                {tiers_html}
            </div>
        </div>
        
        <!-- Credit Modifiers Reference -->
        <div class="card" style="margin-top: 20px;">
            <h3>How to Improve Your Score</h3>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                <div>
                    <h4 style="color: #22c55e;">Positive Actions</h4>
                    <ul style="color: #94a3b8; line-height: 1.8;">
                        <li>Profitable margin trades: +2</li>
                        <li>Return commodities on time: +3</li>
                        <li>Pay dividends to shareholders: +1</li>
                        <li>Successful business IPO: +5</li>
                        <li>Pay off liens: +10</li>
                        <li>Profitable short positions: +2</li>
                    </ul>
                </div>
                <div>
                    <h4 style="color: #ef4444;">Negative Actions</h4>
                    <ul style="color: #94a3b8; line-height: 1.8;">
                        <li>Margin call triggered: -10</li>
                        <li>Commodity default: -20</li>
                        <li>Return commodities late: -5</li>
                        <li>Skip dividend while profitable: -3</li>
                        <li>Lien created: -15</li>
                        <li>Short position default: -15</li>
                        <li>Take company private: -10</li>
                    </ul>
                </div>
            </div>
        </div>
        '''
        
        return shell("Credit & Liens", body, player.cash_balance, player.id)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return shell("Credit & Liens", f"Error: {e}", player.cash_balance, player.id)


# ==========================
# HELPER FUNCTIONS FOR BROKERAGE UX
# ==========================

def generate_short_positions_summary(short_positions) -> str:
    """Generate HTML summary of short positions for dashboard."""
    from banks.brokerage_firm import CompanyShares, get_db as get_firm_db
    
    if not short_positions:
        return '<p style="color: #64748b;">No active shorts</p>'
    
    html = '<ul style="list-style: none; padding: 0; margin: 0;">'
    db = get_firm_db()
    try:
        for short in short_positions[:3]:  # Show top 3
            company = db.query(CompanyShares).filter(
                CompanyShares.id == short.company_shares_id
            ).first()
            if company:
                pnl = (short.borrow_price - company.current_price) * short.shares_borrowed
                pnl_color = "#22c55e" if pnl >= 0 else "#ef4444"
                html += f'''
                <li style="padding: 8px 0; border-bottom: 1px solid #1e293b;">
                    <strong>{company.ticker_symbol}</strong>: {short.shares_borrowed} shares
                    <span style="float: right; color: {pnl_color};">${pnl:,.0f}</span>
                </li>'''
    finally:
        db.close()
    
    html += '</ul>'
    if len(short_positions) > 3:
        html += f'<p style="color: #64748b; font-size: 0.85rem; margin-top: 10px;">+{len(short_positions)-3} more</p>'
    
    return html


def generate_commodity_loans_summary(commodity_loans) -> str:
    """Generate HTML summary of commodity loans for dashboard."""
    if not commodity_loans:
        return '<p style="color: #64748b;">No active loans</p>'
    
    html = '<ul style="list-style: none; padding: 0; margin: 0;">'
    for loan in commodity_loans[:3]:  # Show top 3
        status_color = "#f59e0b" if loan.status == "late" else "#38bdf8"
        html += f'''
        <li style="padding: 8px 0; border-bottom: 1px solid #1e293b;">
            <strong>{loan.item_type.replace("_", " ").title()}</strong>: {loan.quantity_borrowed:,.0f}
            <span style="float: right; color: {status_color};">{loan.due_date.strftime("%m/%d")}</span>
        </li>'''
    
    html += '</ul>'
    if len(commodity_loans) > 3:
        html += f'<p style="color: #64748b; font-size: 0.85rem; margin-top: 10px;">+{len(commodity_loans)-3} more</p>'
    
    return html


def generate_player_listings_html(listings) -> str:
    """Generate HTML for player's commodity listings."""
    if not listings:
        return '<p style="color: #64748b;">No active listings.</p>'
    
    html = '<ul style="list-style: none; padding: 0; margin: 0;">'
    for listing in listings:
        available = listing.quantity_available - listing.quantity_lent_out
        html += f'''
        <li style="padding: 10px; margin-bottom: 8px; background: #020617; border-radius: 4px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <strong>{listing.item_type.replace("_", " ").title()}</strong><br>
                    <span style="color: #64748b; font-size: 0.85rem;">
                        {available:,.0f} / {listing.quantity_available:,.0f} available | {listing.weekly_rate*100:.1f}%/week
                    </span>
                </div>
                <form action="/api/brokerage/cancel-listing" method="post">
                    <input type="hidden" name="listing_id" value="{listing.id}">
                    <button type="submit" class="btn-red" style="padding: 4px 8px; font-size: 0.8rem;">Cancel</button>
                </form>
            </div>
        </li>'''
    html += '</ul>'
    return html


def generate_lent_out_html(loans) -> str:
    """Generate HTML for commodities lent out by player."""
    if not loans:
        return '<p style="color: #64748b;">None lent out.</p>'
    
    html = '''
    <table style="width: 100%; border-collapse: collapse;">
        <thead>
            <tr style="border-bottom: 1px solid #1e293b; text-align: left;">
                <th style="padding: 8px;">Item</th>
                <th style="padding: 8px;">Qty</th>
                <th style="padding: 8px;">Borrower</th>
                <th style="padding: 8px;">Due</th>
                <th style="padding: 8px;">Fees Earned</th>
            </tr>
        </thead>
        <tbody>'''
    
    for loan in loans:
        html += f'''
        <tr style="border-bottom: 1px solid #1e293b;">
            <td style="padding: 8px;">{loan.item_type.replace("_", " ").title()}</td>
            <td style="padding: 8px;">{loan.quantity_borrowed:,.0f}</td>
            <td style="padding: 8px;">Player {loan.borrower_player_id}</td>
            <td style="padding: 8px;">{loan.due_date.strftime("%m/%d %H:%M")}</td>
            <td style="padding: 8px; color: #22c55e;">${loan.fees_to_lender:,.2f}</td>
        </tr>'''
    
    html += '</tbody></table>'
    return html

@router.get("/liens", response_class=HTMLResponse)
def liens_page(session_token: Optional[str] = Cookie(None)):
    """Detailed lien dashboard page."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return player
    
    lien_info = get_player_lien_info(player.id)
    
    if not lien_info["has_lien"]:
        return shell(
            "Liens",
            """
            <a href="/" style="color: #38bdf8;">← Dashboard</a>
            <h1>Bank Liens</h1>
            <div class="card">
                <h3 style="color: #22c55e;">✓ No Active Liens</h3>
                <p>You have no outstanding debts to any bank.</p>
            </div>
            """,
            player.cash_balance,
            player.id
        )
    
    # Status-based messaging
    status_messages = {
        "critical": {
            "color": "#dc2626",
            "icon": "🚨",
            "title": "CRITICAL DEBT",
            "message": "Your debt is severely impacting your financial position. The bank is garnishing 50% of all incoming cash."
        },
        "warning": {
            "color": "#f59e0b",
            "icon": "⚠️",
            "title": "MODERATE DEBT",
            "message": "You have a significant lien. Interest is accruing and automatic garnishment is active."
        },
        "ok": {
            "color": "#64748b",
            "icon": "📋",
            "title": "MINOR DEBT",
            "message": "You have a manageable lien. The bank is automatically collecting payments from your cash flow."
        }
    }
    
    status_info = status_messages.get(lien_info["status"], status_messages["ok"])
    
    # Calculate daily interest
    daily_interest = lien_info["total_owed"] * lien_info["interest_rate_per_minute"] * 60 * 24
    
    # Calculate time to pay off at current rate (rough estimate)
    if player.cash_balance > 0:
        estimated_payment_per_day = player.cash_balance * (lien_info["garnishment_rate"] / 100) * 60 * 24
        days_to_payoff = (lien_info["total_owed"] / estimated_payment_per_day) if estimated_payment_per_day > daily_interest else "∞"
        if days_to_payoff != "∞":
            days_to_payoff = f"{days_to_payoff:.1f} days"
    else:
        days_to_payoff = "Cannot estimate (no income)"
    
    lien_html = f"""
    <a href="/" style="color: #38bdf8;">← Dashboard</a>
    <h1>Bank Liens Dashboard</h1>
    
    <div class="card" style="border-color: {status_info['color']}; border-width: 2px;">
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 16px;">
            <span style="font-size: 2rem;">{status_info['icon']}</span>
            <div>
                <h2 style="margin: 0; color: {status_info['color']};">{status_info['title']}</h2>
                <p style="margin: 4px 0 0 0; color: #94a3b8;">{status_info['message']}</p>
            </div>
        </div>
        
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 24px;">
            <div>
                <div style="font-size: 0.85rem; color: #64748b; margin-bottom: 4px;">TOTAL OWED</div>
                <div style="font-size: 2rem; font-weight: bold; color: {status_info['color']};">
                    ${lien_info['total_owed']:,.2f}
                </div>
            </div>
            <div>
                <div style="font-size: 0.85rem; color: #64748b; margin-bottom: 4px;">DAILY INTEREST</div>
                <div style="font-size: 2rem; font-weight: bold; color: #ef4444;">
                    +${daily_interest:,.2f}
                </div>
            </div>
        </div>
    </div>
    
    <div class="card">
        <h3>Debt Breakdown</h3>
        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; margin-top: 16px;">
            <div>
                <div style="font-size: 0.85rem; color: #64748b; margin-bottom: 8px;">Principal</div>
                <div style="font-size: 1.5rem; color: #e5e7eb;">${lien_info['principal']:,.2f}</div>
            </div>
            <div>
                <div style="font-size: 0.85rem; color: #64748b; margin-bottom: 8px;">Accrued Interest</div>
                <div style="font-size: 1.5rem; color: #ef4444;">${lien_info['interest']:,.2f}</div>
            </div>
            <div>
                <div style="font-size: 0.85rem; color: #64748b; margin-bottom: 8px;">Active Liens</div>
                <div style="font-size: 1.5rem; color: #38bdf8;">{lien_info['lien_count']}</div>
            </div>
        </div>
    </div>
    
    <div class="card">
        <h3>Payment Terms</h3>
        <div style="margin-top: 16px;">
            <div style="margin-bottom: 12px;">
                <strong style="color: #38bdf8;">Interest Rate:</strong> 
                <span>{lien_info['interest_rate_per_minute']:.4f}% per minute</span>
                <span style="color: #64748b; margin-left: 8px;">(~{lien_info['interest_rate_per_minute'] * 60 * 24:.2f}% daily, ~{lien_info['interest_rate_per_minute'] * 60 * 24 * 365:.1f}% annually)</span>
            </div>
            <div style="margin-bottom: 12px;">
                <strong style="color: #38bdf8;">Garnishment Rate:</strong> 
                <span>{lien_info['garnishment_rate']:.0f}% of available cash every 60 seconds</span>
            </div>
            <div style="margin-bottom: 12px;">
                <strong style="color: #38bdf8;">Estimated Payoff Time:</strong> 
                <span>{days_to_payoff}</span>
            </div>
        </div>
    </div>
    
    <div class="card" style="background: #0f172a; border-color: #1e293b;">
        <h3>How Liens Work</h3>
        <ul style="line-height: 1.8; color: #94a3b8;">
            <li><strong>Origin:</strong> Liens are created when a bank becomes insolvent and shareholders cannot pay their solvency levy.</li>
            <li><strong>Interest:</strong> Your debt grows by {lien_info['interest_rate_per_minute']:.4f}% every minute. This compounds continuously.</li>
            <li><strong>Garnishment:</strong> Every 60 seconds, the bank automatically takes {lien_info['garnishment_rate']:.0f}% of your cash balance to pay down the lien.</li>
            <li><strong>Priority:</strong> Payments are applied to interest first, then principal.</li>
            <li><strong>No Restrictions:</strong> You can continue trading, managing businesses, and operating normally while carrying a lien.</li>
            <li><strong>Payoff:</strong> Once your lien reaches $0.00, it will be automatically cleared from your record.</li>
        </ul>
    </div>
    
    <div class="card" style="background: #450a0a; border-color: #7f1d1d;">
        <h3 style="color: #fca5a5;">⚠️ Warning</h3>
        <p style="color: #fca5a5;">
            While you can continue normal operations, this debt will drain your cash reserves. 
            The longer the lien remains unpaid, the more interest accrues. Consider generating 
            cash flow through business operations or selling assets to accelerate payoff.
        </p>
    </div>
    """
    
    return shell("Liens", lien_html, player.cash_balance, player.id)

# ==========================
# API ENDPOINTS
# ==========================

@router.post("/api/business/create")
async def create_business_endpoint(land_plot_id: int = Form(...), business_type: str = Form(...), session_token: Optional[str] = Cookie(None)):
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return player
    from business import create_business
    if create_business(player.id, land_plot_id, business_type): return RedirectResponse(url="/businesses", status_code=303)
    return RedirectResponse(url="/land?error=failed", status_code=303)

@router.post("/api/business/toggle")
async def toggle_business_endpoint(business_id: int = Form(...), session_token: Optional[str] = Cookie(None)):
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return player
    from business import toggle_business
    toggle_business(player.id, business_id)
    return RedirectResponse(url="/businesses", status_code=303)

@router.post("/api/business/dismantle")
async def dismantle_business_endpoint(business_id: int = Form(...), session_token: Optional[str] = Cookie(None)):
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return player
    from business import start_business_dismantling
    start_business_dismantling(player.id, business_id)
    return RedirectResponse(url="/businesses", status_code=303)

@router.post("/api/retail/set-price")
async def set_retail_price_endpoint(item_type: str = Form(...), price: float = Form(...), session_token: Optional[str] = Cookie(None)):
    """Retail Pricing Patch Endpoint."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return player
    try:
        from business import set_retail_price
        set_retail_price(player.id, item_type, price)
        return RedirectResponse(url="/businesses", status_code=303)
    except Exception as e:
        print(f"[UX] Retail price error: {e}")
        return RedirectResponse(url="/businesses?error=price_update_failed", status_code=303)

@router.post("/api/inventory/list")
async def list_to_market(item_type: str = Form(...), quantity: float = Form(...), price: float = Form(...), session_token: Optional[str] = Cookie(None)):
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return player
    import market
    market.create_order(player.id, market.OrderType.SELL, market.OrderMode.LIMIT, item_type, quantity, price)
    return RedirectResponse(url="/inventory", status_code=303)

@router.post("/api/market/order")
async def place_order(item_type: str = Form(...), order_type: str = Form(...), quantity: float = Form(...), price: float = Form(...), session_token: Optional[str] = Cookie(None)):
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return player
    import market
    market.create_order(
        player.id, 
        market.OrderType.BUY if order_type == "buy" else market.OrderType.SELL, 
        market.OrderMode.LIMIT, 
        item_type, 
        quantity, 
        price
    )
    return RedirectResponse(url=f"/market?item={item_type}", status_code=303)

@router.post("/api/land-market/buy-auction")
async def buy_auction_endpoint(auction_id: int = Form(...), session_token: Optional[str] = Cookie(None)):
    """Buy a plot from government auction."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return player
    
    from land_market import buy_auction_land
    if buy_auction_land(player.id, auction_id):
        return RedirectResponse(url="/land-market?success=auction_bought", status_code=303)
    return RedirectResponse(url="/land-market?error=purchase_failed", status_code=303)

@router.post("/api/land-market/buy-listing")
async def buy_listing_endpoint(listing_id: int = Form(...), session_token: Optional[str] = Cookie(None)):
    """Buy a plot from player listing."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return player
    
    from land_market import buy_listed_land
    if buy_listed_land(player.id, listing_id):
        return RedirectResponse(url="/land-market?success=listing_bought", status_code=303)
    return RedirectResponse(url="/land-market?error=purchase_failed", status_code=303)

@router.post("/api/land-market/cancel-listing")
async def cancel_listing_endpoint(listing_id: int = Form(...), session_token: Optional[str] = Cookie(None)):
    """Cancel your own land listing."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return player
    
    from land_market import cancel_listing
    if cancel_listing(player.id, listing_id):
        return RedirectResponse(url="/land-market?success=listing_cancelled", status_code=303)
    return RedirectResponse(url="/land-market?error=cancel_failed", status_code=303)

@router.post("/api/land-market/list-land")
async def list_land_endpoint(land_plot_id: int = Form(...), asking_price: float = Form(...), session_token: Optional[str] = Cookie(None)):
    """List your land for sale."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return player
    
    from land_market import list_land_for_sale
    if list_land_for_sale(player.id, land_plot_id, asking_price):
        return RedirectResponse(url="/land-market?success=land_listed", status_code=303)
    return RedirectResponse(url="/land-market?error=listing_failed", status_code=303)

@router.post("/api/brokerage/create-ipo")
async def brokerage_create_ipo(
    business_id: int = Form(...),
    company_name: str = Form(...),
    ticker_symbol: str = Form(...),
    share_class: str = Form("A"),
    ipo_type: str = Form(...),
    total_shares: int = Form(...),
    offer_percentage: int = Form(...),
    dividend_type: str = Form(None),
    dividend_amount: float = Form(None),
    dividend_frequency: str = Form("weekly"),
    dividend_commodity: str = Form(None),
    session_token: Optional[str] = Cookie(None)
):
    """Create an IPO for a business."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    
    try:
        from banks.brokerage_firm import create_ipo, IPOType
        
        # Parse IPO type
        try:
            ipo_type_enum = IPOType(ipo_type)
        except ValueError:
            return RedirectResponse(url="/brokerage/ipo?error=invalid_ipo_type", status_code=303)
        
        # Calculate shares to offer
        shares_to_offer = int(total_shares * (offer_percentage / 100))
        
        # Build dividend config
        dividend_config = []
        if dividend_type and dividend_amount and dividend_amount > 0:
            div_entry = {
                "type": dividend_type,
                "frequency": dividend_frequency
            }
            
            if dividend_type == "cash":
                div_entry["amount"] = dividend_amount
                div_entry["basis"] = "profit_pct"
            elif dividend_type == "commodity":
                div_entry["item"] = dividend_commodity or "apple_seeds"
                div_entry["amount"] = int(dividend_amount)
                div_entry["per_shares"] = 100
            elif dividend_type == "scrip":
                div_entry["rate"] = dividend_amount
            
            dividend_config.append(div_entry)
        
        # Clean ticker
        ticker_clean = ticker_symbol.upper().strip()[:5]
        
        result = create_ipo(
            founder_id=player.id,
            business_id=business_id,
            ipo_type=ipo_type_enum,
            shares_to_offer=shares_to_offer,
            total_shares=total_shares,
            share_class=share_class,
            company_name=company_name,
            ticker_symbol=ticker_clean,
            dividend_config=dividend_config
        )
        
        if result:
            return RedirectResponse(url=f"/brokerage/trading?ticker={ticker_clean}&success=ipo_created", status_code=303)
        return RedirectResponse(url="/brokerage/ipo?error=ipo_failed", status_code=303)
        
    except Exception as e:
        print(f"[UX] Create IPO error: {e}")
        import traceback
        traceback.print_exc()
        return RedirectResponse(url="/brokerage/ipo?error=exception", status_code=303)


@router.post("/api/brokerage/short-sell")
async def brokerage_short_sell(
    ticker: str = Form(...),
    quantity: int = Form(...),
    session_token: Optional[str] = Cookie(None)
):
    """Open a short position."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    
    try:
        from banks.brokerage_firm import short_sell_shares, CompanyShares, get_db as get_firm_db
        
        # Get company ID from ticker
        db = get_firm_db()
        try:
            company = db.query(CompanyShares).filter(
                CompanyShares.ticker_symbol == ticker.upper()
            ).first()
            
            if not company:
                return RedirectResponse(url=f"/brokerage/shorts?error=company_not_found", status_code=303)
            
            company_id = company.id
        finally:
            db.close()
        
        result = short_sell_shares(
            borrower_id=player.id,
            company_shares_id=company_id,
            quantity=quantity
        )
        
        if result:
            return RedirectResponse(url=f"/brokerage/shorts?ticker={ticker}&success=short_opened", status_code=303)
        return RedirectResponse(url=f"/brokerage/shorts?ticker={ticker}&error=short_failed", status_code=303)
        
    except Exception as e:
        print(f"[UX] Short sell error: {e}")
        import traceback
        traceback.print_exc()
        return RedirectResponse(url="/brokerage/shorts?error=exception", status_code=303)


@router.post("/api/brokerage/close-short")
async def brokerage_close_short(
    loan_id: int = Form(...),
    session_token: Optional[str] = Cookie(None)
):
    """Close a short position."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    
    try:
        from banks.brokerage_firm import close_short_position, ShareLoan, get_db as get_firm_db
        
        # Verify ownership
        db = get_firm_db()
        try:
            loan = db.query(ShareLoan).filter(
                ShareLoan.id == loan_id,
                ShareLoan.borrower_player_id == player.id
            ).first()
            
            if not loan:
                return RedirectResponse(url="/brokerage/shorts?error=loan_not_found", status_code=303)
        finally:
            db.close()
        
        success = close_short_position(loan_id)
        
        if success:
            return RedirectResponse(url="/brokerage/shorts?success=short_closed", status_code=303)
        return RedirectResponse(url="/brokerage/shorts?error=close_failed", status_code=303)
        
    except Exception as e:
        print(f"[UX] Close short error: {e}")
        import traceback
        traceback.print_exc()
        return RedirectResponse(url="/brokerage/shorts?error=exception", status_code=303)


@router.post("/api/brokerage/list-commodity")
async def brokerage_list_commodity(
    item_type: str = Form(...),
    quantity: float = Form(...),
    weekly_rate: float = Form(...),
    session_token: Optional[str] = Cookie(None)
):
    """List commodities for lending."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    
    try:
        from banks.brokerage_firm import list_commodity_for_lending
        
        # Convert percentage to decimal
        rate_decimal = weekly_rate / 100.0
        
        result = list_commodity_for_lending(
            lender_id=player.id,
            item_type=item_type,
            quantity=quantity,
            weekly_rate=rate_decimal
        )
        
        if result:
            return RedirectResponse(url="/brokerage/commodities?success=listed", status_code=303)
        return RedirectResponse(url="/brokerage/commodities?error=list_failed", status_code=303)
        
    except Exception as e:
        print(f"[UX] List commodity error: {e}")
        import traceback
        traceback.print_exc()
        return RedirectResponse(url="/brokerage/commodities?error=exception", status_code=303)


@router.post("/api/brokerage/cancel-listing")
async def brokerage_cancel_listing(
    listing_id: int = Form(...),
    session_token: Optional[str] = Cookie(None)
):
    """Cancel a commodity listing."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    
    try:
        from banks.brokerage_firm import CommodityListing, get_db as get_firm_db
        
        db = get_firm_db()
        try:
            listing = db.query(CommodityListing).filter(
                CommodityListing.id == listing_id,
                CommodityListing.lender_player_id == player.id,
                CommodityListing.is_active == True
            ).first()
            
            if not listing:
                return RedirectResponse(url="/brokerage/commodities?error=listing_not_found", status_code=303)
            
            # Check if anything is lent out
            if listing.quantity_lent_out > 0:
                return RedirectResponse(url="/brokerage/commodities?error=items_lent_out", status_code=303)
            
            listing.is_active = False
            db.commit()
            
        finally:
            db.close()
        
        return RedirectResponse(url="/brokerage/commodities?success=listing_cancelled", status_code=303)
        
    except Exception as e:
        print(f"[UX] Cancel listing error: {e}")
        import traceback
        traceback.print_exc()
        return RedirectResponse(url="/brokerage/commodities?error=exception", status_code=303)


@router.post("/api/brokerage/borrow-commodity")
async def brokerage_borrow_commodity(
    listing_id: int = Form(...),
    quantity: float = Form(...),
    session_token: Optional[str] = Cookie(None)
):
    """Borrow commodities from a listing."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    
    try:
        from banks.brokerage_firm import borrow_commodity
        
        result = borrow_commodity(
            borrower_id=player.id,
            listing_id=listing_id,
            quantity=quantity
        )
        
        if result:
            return RedirectResponse(url="/brokerage/commodities?success=borrowed", status_code=303)
        return RedirectResponse(url="/brokerage/commodities?error=borrow_failed", status_code=303)
        
    except Exception as e:
        print(f"[UX] Borrow commodity error: {e}")
        import traceback
        traceback.print_exc()
        return RedirectResponse(url="/brokerage/commodities?error=exception", status_code=303)


@router.post("/api/brokerage/return-commodity")
async def brokerage_return_commodity(
    loan_id: int = Form(...),
    session_token: Optional[str] = Cookie(None)
):
    """Return borrowed commodities."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    
    try:
        from banks.brokerage_firm import return_commodity, CommodityLoan, get_db as get_firm_db
        
        # Verify ownership
        db = get_firm_db()
        try:
            loan = db.query(CommodityLoan).filter(
                CommodityLoan.id == loan_id,
                CommodityLoan.borrower_player_id == player.id
            ).first()
            
            if not loan:
                return RedirectResponse(url="/brokerage/commodities?error=loan_not_found", status_code=303)
        finally:
            db.close()
        
        success = return_commodity(loan_id)
        
        if success:
            return RedirectResponse(url="/brokerage/commodities?success=returned", status_code=303)
        return RedirectResponse(url="/brokerage/commodities?error=return_failed", status_code=303)
        
    except Exception as e:
        print(f"[UX] Return commodity error: {e}")
        import traceback
        traceback.print_exc()
        return RedirectResponse(url="/brokerage/commodities?error=exception", status_code=303)


@router.post("/api/brokerage/extend-loan")
async def brokerage_extend_loan(
    loan_id: int = Form(...),
    session_token: Optional[str] = Cookie(None)
):
    """Extend a commodity loan."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    
    try:
        from banks.brokerage_firm import extend_commodity_loan, CommodityLoan, get_db as get_firm_db
        
        # Verify ownership
        db = get_firm_db()
        try:
            loan = db.query(CommodityLoan).filter(
                CommodityLoan.id == loan_id,
                CommodityLoan.borrower_player_id == player.id
            ).first()
            
            if not loan:
                return RedirectResponse(url="/brokerage/commodities?error=loan_not_found", status_code=303)
        finally:
            db.close()
        
        success = extend_commodity_loan(loan_id)
        
        if success:
            return RedirectResponse(url="/brokerage/commodities?success=extended", status_code=303)
        return RedirectResponse(url="/brokerage/commodities?error=extend_failed", status_code=303)
        
    except Exception as e:
        print(f"[UX] Extend loan error: {e}")
        import traceback
        traceback.print_exc()
        return RedirectResponse(url="/brokerage/commodities?error=exception", status_code=303)


@router.post("/api/brokerage/enable-share-lending")
async def brokerage_enable_share_lending(
    position_id: int = Form(...),
    quantity: int = Form(...),
    session_token: Optional[str] = Cookie(None)
):
    """Enable shares for lending (for short sellers to borrow)."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    
    try:
        from banks.brokerage_firm import ShareholderPosition, get_db as get_firm_db
        
        db = get_firm_db()
        try:
            position = db.query(ShareholderPosition).filter(
                ShareholderPosition.id == position_id,
                ShareholderPosition.player_id == player.id
            ).first()
            
            if not position:
                return RedirectResponse(url="/brokerage/portfolio?error=position_not_found", status_code=303)
            
            available = position.shares_owned - position.shares_lent_out
            if quantity > available:
                return RedirectResponse(url="/brokerage/portfolio?error=insufficient_shares", status_code=303)
            
            position.shares_available_to_lend = quantity
            db.commit()
            
        finally:
            db.close()
        
        return RedirectResponse(url="/brokerage/portfolio?success=lending_enabled", status_code=303)
        
    except Exception as e:
        print(f"[UX] Enable lending error: {e}")
        import traceback
        traceback.print_exc()
        return RedirectResponse(url="/brokerage/portfolio?error=exception", status_code=303)


@router.post("/api/brokerage/deposit-margin")
async def brokerage_deposit_margin(
    amount: float = Form(...),
    session_token: Optional[str] = Cookie(None)
):
    """Deposit cash to resolve margin calls."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    
    try:
        from banks.brokerage_firm import MarginCall, ShareholderPosition, get_db as get_firm_db
        from auth import Player, get_db as get_auth_db
        
        # Check player has funds
        auth_db = get_auth_db()
        try:
            player_record = auth_db.query(Player).filter(Player.id == player.id).first()
            if not player_record or player_record.cash_balance < amount:
                return RedirectResponse(url="/banks/brokerage-firm?error=insufficient_funds", status_code=303)
            
            player_record.cash_balance -= amount
            auth_db.commit()
        finally:
            auth_db.close()
        
        # Apply to margin debt
        db = get_firm_db()
        try:
            # Find positions with margin debt
            positions = db.query(ShareholderPosition).filter(
                ShareholderPosition.player_id == player.id,
                ShareholderPosition.margin_debt > 0
            ).order_by(ShareholderPosition.margin_debt.desc()).all()
            
            remaining = amount
            for pos in positions:
                if remaining <= 0:
                    break
                
                paydown = min(remaining, pos.margin_debt)
                pos.margin_debt -= paydown
                remaining -= paydown
                
                if pos.margin_debt <= 0:
                    pos.is_margin_position = False
                    pos.margin_multiplier_used = 1.0
            
            # Resolve margin calls if debt cleared
            margin_calls = db.query(MarginCall).filter(
                MarginCall.player_id == player.id,
                MarginCall.is_resolved == False
            ).all()
            
            for mc in margin_calls:
                # Recalculate if still needed
                total_debt = sum(p.margin_debt for p in positions)
                if total_debt <= 0:
                    mc.is_resolved = True
                    mc.resolved_at = datetime.utcnow()
                    mc.resolution_type = "deposited"
            
            db.commit()
        finally:
            db.close()
        
        return RedirectResponse(url="/banks/brokerage-firm?success=margin_deposited", status_code=303)
        
    except Exception as e:
        print(f"[UX] Deposit margin error: {e}")
        import traceback
        traceback.print_exc()
        return RedirectResponse(url="/banks/brokerage-firm?error=exception", status_code=303)

# ==========================
# BROKERAGE TRADING API
# ==========================

@router.post("/api/brokerage/buy")
async def brokerage_buy_shares(
    company_id: int = Form(...),
    quantity: int = Form(...),
    use_margin: bool = Form(False),
    limit_price: Optional[float] = Form(None), # Optional: Forms can send this if UI supports it
    session_token: Optional[str] = Cookie(None)
):
    """Place a buy order (Market or Limit)."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return player
    
    try:
        from banks.brokerage_firm import (
            player_place_buy_order, CompanyShares, get_db as get_firm_db
        )
        
        # Get ticker for the redirect URL
        db = get_firm_db()
        try:
            company = db.query(CompanyShares).filter(CompanyShares.id == company_id).first()
            ticker = company.ticker_symbol if company else "UNKNOWN"
        finally:
            db.close()
        
        # Execute Order
        result = player_place_buy_order(
            player_id=player.id,
            company_shares_id=company_id,
            quantity=quantity,
            limit_price=limit_price, # None = Market Order
            use_margin=use_margin
        )
        
        status = "success" if result else "error"
        msg = "buy_order_placed" if result else "buy_failed"
        
        return RedirectResponse(url=f"/brokerage/trading?ticker={ticker}&{status}={msg}", status_code=303)
        
    except Exception as e:
        print(f"[UX] Buy shares error: {e}")
        return RedirectResponse(url="/brokerage/trading?error=exception", status_code=303)


@router.post("/api/brokerage/sell")
async def brokerage_sell_shares(
    company_id: int = Form(...),
    quantity: int = Form(...),
    limit_price: Optional[float] = Form(None),
    session_token: Optional[str] = Cookie(None)
):
    """Place a sell order (Market or Limit)."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return player
    
    try:
        from banks.brokerage_firm import (
            player_place_sell_order, CompanyShares, get_db as get_firm_db
        )
        
        db = get_firm_db()
        try:
            company = db.query(CompanyShares).filter(CompanyShares.id == company_id).first()
            ticker = company.ticker_symbol if company else "UNKNOWN"
        finally:
            db.close()
        
        result = player_place_sell_order(
            player_id=player.id,
            company_shares_id=company_id,
            quantity=quantity,
            limit_price=limit_price
        )
        
        status = "success" if result else "error"
        msg = "sell_order_placed" if result else "sell_failed"
        
        return RedirectResponse(url=f"/brokerage/trading?ticker={ticker}&{status}={msg}", status_code=303)
        
    except Exception as e:
        print(f"[UX] Sell shares error: {e}")
        return RedirectResponse(url="/brokerage/trading?error=exception", status_code=303)


@router.post("/api/brokerage/cancel-order")
async def brokerage_cancel_order(
    order_id: int = Form(...),
    session_token: Optional[str] = Cookie(None)
):
    """Cancel a pending order."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return player
    
    try:
        from brokerage_order_book import cancel_order
        
        success = cancel_order(player.id, order_id)
        
        # Determine where to redirect (trading page or portfolio)
        return RedirectResponse(url=f"/brokerage/portfolio?success={'cancelled' if success else 'cancel_failed'}", status_code=303)
        
    except Exception as e:
        print(f"[UX] Cancel order error: {e}")
        return RedirectResponse(url="/brokerage/portfolio?error=exception", status_code=303)


# ==========================
# DATA ENDPOINTS (JSON)
# ==========================
# These return JSON for potential JS/AJAX usage, but are attached to @router correctly

@router.get("/api/trading/orderbook/{company_shares_id}")
async def get_orderbook_data(
    company_shares_id: int,
    depth: int = 10,
    session_token: Optional[str] = Cookie(None)
):
    """Get raw orderbook data (JSON)."""
    # Auth optional for viewing, but good practice
    from brokerage_order_book import get_order_book_depth
    return get_order_book_depth(company_shares_id, depth)


@router.get("/api/trading/trades/{company_shares_id}")
async def get_recent_trades_data(
    company_shares_id: int,
    limit: int = 20
):
    """Get recent fills (JSON)."""
    from brokerage_order_book import get_recent_fills
    return {"trades": get_recent_fills(company_shares_id, limit)}


@router.get("/api/trading/orders/my")
async def get_my_open_orders(
    session_token: Optional[str] = Cookie(None)
):
    """Get current player's open orders (JSON)."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return {"error": "Unauthorized"}
    
    try:
        from brokerage_order_book import OrderBook, OrderStatus, get_db as get_book_db
        db = get_book_db()
        try:
            orders = db.query(OrderBook).filter(
                OrderBook.player_id == player.id,
                OrderBook.status.in_([
                    OrderStatus.PENDING.value, 
                    OrderStatus.PARTIAL.value
                ])
            ).order_by(OrderBook.created_at.desc()).all()
            
            return {
                "orders": [{
                    "id": o.id,
                    "company_shares_id": o.company_shares_id,
                    "side": o.order_side,
                    "type": o.order_type,
                    "quantity": o.quantity,
                    "filled": o.filled_quantity,
                    "limit_price": o.limit_price,
                    "status": o.status,
                    "created_at": o.created_at.isoformat()
                } for o in orders]
            }
        finally:
            db.close()
    except Exception as e:
        return {"error": str(e)}


# ==========================
# MODULE LIFECYCLE
# ==========================

def initialize():
    """Initialize UX module."""
    print("[UX] Module initialized")

async def tick(current_tick: int, now):
    """UX tick handler (no-op)."""
    pass

# ==========================
# PUBLIC API
# ==========================

__all__ = [
    'router',
    'initialize',
    'tick',
    'shell',
    'get_player_lien_info'
]
