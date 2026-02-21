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
        <title>{title} · Wadsworth</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            * {{ box-sizing: border-box; }}
            body {{
                background: #020617;
                color: #e5e7eb;
                font-family: 'JetBrains Mono', monospace;
                margin: 0;
                padding-bottom: 60px;
                font-size: 18px;
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
                display: flex;
                align-items: center;
                gap: 8px;
            }}

            .brand img {{
                height: 28px;
                width: auto;
            }}

            .header-right {{
                display: flex;
                align-items: center;
                gap: 12px;
                flex-wrap: wrap;
            }}

            .balance {{
                color: #22c55e;
                font-size: 0.75rem;
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

            .btn-blue, .btn-orange, .btn-red, .btn-gold {{
                border: none;
                padding: 6px 12px;
                cursor: pointer;
                font-size: 0.8rem;
                border-radius: 3px;
            }}

            .btn-blue {{ background: #38bdf8; color: #020617; }}
            .btn-orange {{ background: #f59e0b; color: #020617; }}
            .btn-red {{ background: #ef4444; color: #fff; }}
            .btn-gold {{ background: #d4af37; color: #fff; }}

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
                font-size: 0.85rem;
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
                    display: inline-block;
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
            <div class="brand"><img src="/static/logo.png" alt="Wadsworth"> Wadsworth</div>
            <div class="header-right">
                {lien_html}
                <span class="balance">$ {balance:,.2f}</span>
                <a href="/api/logout" style="color: #ef4444; font-size: 0.85rem;">Logout</a>
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
        
        DATABASE_URL = "sqlite:///./wadsworth.db"
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

    # Tutorial banner/overlay
    try:
        from tutorial_ux import should_show_tutorial_banner, get_tutorial_overlay_html
        tutorial_banner = ""
        tutorial_overlay = get_tutorial_overlay_html(player, "dashboard")
        if not tutorial_overlay and should_show_tutorial_banner(player):
            tutorial_banner = f"""
            <div style="
                background: linear-gradient(135deg, #0a1628, #0f172a);
                border: 2px solid #d4af37;
                border-radius: 6px;
                padding: 20px 24px;
                margin-bottom: 24px;
            ">
                <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;flex-wrap:wrap;">
                    <span style="background:#d4af37;color:#020617;padding:3px 12px;border-radius:12px;font-size:0.7rem;font-weight:bold;">TUTORIAL AVAILABLE</span>
                    <span style="color:#d4af37;font-size:0.85rem;font-weight:bold;">Level 1 · Startup Company</span>
                </div>
                <h3 style="color:#d4af37;margin:0 0 10px 0;font-size:1.05rem;">New to Wadsworth? Start the Tutorial!</h3>
                <p style="color:#94a3b8;margin:0 0 16px 0;line-height:1.6;font-size:0.9rem;">
                    Learn how to build businesses, manage your inventory, trade on the market, and unlock advanced
                    production chains. Complete the tutorial to earn a <strong style="color:#d4af37;">free, tax-exempt land plot</strong>
                    with all proximity features — yours to keep or sell.
                </p>
                <form action="/api/tutorial/start" method="post" style="display:inline;">
                    <button type="submit" style="background:#d4af37;color:#020617;border:none;padding:10px 24px;border-radius:4px;cursor:pointer;font-size:0.9rem;font-weight:bold;margin-right:12px;">
                        Begin Tutorial →
                    </button>
                </form>
                <a href="/api/tutorial/dismiss" style="color:#475569;font-size:0.8rem;">Dismiss</a>
            </div>
            """
    except Exception:
        tutorial_banner = ""
        tutorial_overlay = ""

    # Acquisition / diffuse notification banners
    acq_banners = ""
    try:
        from corporate_actions import get_acquisition_notifications, mark_acquisition_notifications_seen
        notifs = get_acquisition_notifications(player.id)
        banner_parts = []
        for offer in notifs.get("incoming_offers", []):
            banner_parts.append(f"""
            <div style="background:linear-gradient(135deg,#0a1628,#0f172a);border:2px solid #38bdf8;border-radius:6px;padding:16px 20px;margin-bottom:12px;">
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;flex-wrap:wrap;">
                    <span style="background:#38bdf8;color:#020617;padding:2px 10px;border-radius:10px;font-size:0.7rem;font-weight:bold;">ACQUISITION OFFER</span>
                </div>
                <p style="color:#cbd5e1;margin:0 0 12px 0;font-size:0.9rem;">
                    A player has offered to acquire <strong style="color:#38bdf8;">{offer.get('stake_pct',0)*100:.1f}%</strong> of your business income in exchange for <strong style="color:#38bdf8;">{offer.get('shares_offered',0):,}</strong> shares of their company. Offer expires in 7 days.
                </p>
                <div style="display:flex;gap:10px;flex-wrap:wrap;">
                    <form action="/api/corporate-actions/acquisition/accept/{offer['id']}" method="post" style="display:inline;">
                        <button type="submit" style="background:#38bdf8;color:#020617;border:none;padding:8px 18px;border-radius:4px;cursor:pointer;font-size:0.85rem;font-weight:bold;">Accept Offer</button>
                    </form>
                    <form action="/api/corporate-actions/acquisition/reject/{offer['id']}" method="post" style="display:inline;">
                        <button type="submit" style="background:#1e293b;color:#94a3b8;border:1px solid #334155;padding:8px 18px;border-radius:4px;cursor:pointer;font-size:0.85rem;">Reject</button>
                    </form>
                    <a href="/corporate-actions/dashboard" style="color:#475569;font-size:0.8rem;line-height:2.2;">View Details</a>
                </div>
            </div>""")
        for update in notifs.get("outgoing_updates", []):
            status = update.get("status", "unknown")
            color = "#22c55e" if status == "accepted" else "#ef4444"
            label = "ACCEPTED" if status == "accepted" else "REJECTED"
            banner_parts.append(f"""
            <div style="background:linear-gradient(135deg,#0a1628,#0f172a);border:2px solid {color};border-radius:6px;padding:16px 20px;margin-bottom:12px;">
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
                    <span style="background:{color};color:#020617;padding:2px 10px;border-radius:10px;font-size:0.7rem;font-weight:bold;">ACQUISITION {label}</span>
                </div>
                <p style="color:#cbd5e1;margin:0;font-size:0.9rem;">Your acquisition offer has been <strong style="color:{color};">{status}</strong>. <a href="/corporate-actions/dashboard" style="color:#38bdf8;">View your active stakes →</a></p>
            </div>""")
        for notice in notifs.get("diffuse_notices", []):
            deadline = notice.get("deadline_at", "")
            banner_parts.append(f"""
            <div style="background:linear-gradient(135deg,#0a1628,#0f172a);border:2px solid #f59e0b;border-radius:6px;padding:16px 20px;margin-bottom:12px;">
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
                    <span style="background:#f59e0b;color:#020617;padding:2px 10px;border-radius:10px;font-size:0.7rem;font-weight:bold;">DIFFUSE NOTICE</span>
                </div>
                <p style="color:#cbd5e1;margin:0 0 12px 0;font-size:0.9rem;">
                    The acquiring party has initiated a diffuse. You must return <strong style="color:#f59e0b;">{notice.get('shares_to_return',0):,} shares</strong> by <strong style="color:#f59e0b;">{deadline}</strong> or a lien will be placed on your account.
                </p>
                <form action="/api/corporate-actions/diffuse/return/{notice['id']}" method="post" style="display:inline;">
                    <button type="submit" style="background:#f59e0b;color:#020617;border:none;padding:8px 18px;border-radius:4px;cursor:pointer;font-size:0.85rem;font-weight:bold;">Return Shares Now</button>
                </form>
            </div>""")
        for resolved in notifs.get("diffuse_resolved", []):
            banner_parts.append(f"""
            <div style="background:linear-gradient(135deg,#0a1628,#0f172a);border:2px solid #22c55e;border-radius:6px;padding:16px 20px;margin-bottom:12px;">
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
                    <span style="background:#22c55e;color:#020617;padding:2px 10px;border-radius:10px;font-size:0.7rem;font-weight:bold;">DIFFUSE COMPLETE</span>
                </div>
                <p style="color:#cbd5e1;margin:0;font-size:0.9rem;">Your diffuse notice has been resolved. The stake has been fully returned. <a href="/corporate-actions/dashboard" style="color:#38bdf8;">View dashboard →</a></p>
            </div>""")
        if banner_parts:
            mark_acquisition_notifications_seen(player.id)
        acq_banners = "".join(banner_parts)
    except Exception:
        acq_banners = ""

    dashboard_top = tutorial_overlay or tutorial_banner
    if acq_banners:
        dashboard_top = dashboard_top + acq_banners

    return shell(
        "Dashboard",
        f"""
        {dashboard_top}
        <h2>Welcome, CEO of {player.business_name}</h2>
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
            <div class="card">
                <h3>Executives</h3>
                <p>Hire and manage high-level employees</p>
                <a href="/executives" class="btn-purple" style="display:inline-block;padding:10px 20px;background:#c084fc;color:#020617;text-decoration:none;border-radius:6px;font-weight:bold;">Executives</a>
            </div>
            <div class="card" style="border-color: #f59e0b;">
                <h3 style="color: #f59e0b;">Peer to Peer</h3>
                <p>Contracts, chatrooms, and direct messages</p>
                <a href="/p2p" style="display:inline-block;padding:10px 20px;background:#f59e0b;color:#020617;text-decoration:none;border-radius:6px;font-weight:bold;">P2P Network</a>
            </div>
            <div class="card">
                <h3>Stats & Leaderboard</h3>
                <p>Statistics, Leaderboard and Data</p>
                <a href="/stats" class="btn-gold">📊 Stats 🪙</a>
            </div>
            <div class="card">
                <h3>Estate & Succession</h3>
                <p>Heirs, account deletion, and deceased registry</p>
                <a href="/estate" style="display:inline-block;padding:10px 20px;background:#475569;color:#e5e7eb;text-decoration:none;border-radius:6px;font-weight:bold;">Estate</a>
            </div>
            <div class="card" style="border-color: #22c55e;">
                <h3 style="color: #22c55e;">World Map</h3>
                <p>Visualize your economic empire on an interactive grid map</p>
                <a href="/world-map" style="display:inline-block;padding:10px 20px;background:#22c55e;color:#020617;text-decoration:none;border-radius:6px;font-weight:bold;">Open Map</a>
            </div>
        </div>
        """,
        player.cash_balance,
        player.id
    )

@router.get("/businesses", response_class=HTMLResponse)
def businesses(session_token: Optional[str] = Cookie(None), sort: str = "name", biz_filter: str = "all"):
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

        # Build list of (biz, config, biz_name, biz_class, progress_pct) tuples for sorting/filtering
        biz_tuples = []
        for biz in player_businesses:
            config = BUSINESS_TYPES.get(biz.business_type)
            if not config:
                from business import get_district_business_types
                district_types = get_district_business_types()
                config = district_types.get(biz.business_type, {})
            biz_name = config.get("name", biz.business_type)
            biz_class = config.get("class", "production")
            cycles_total = config.get("cycles_to_complete", 1)
            progress_pct = (biz.progress_ticks / cycles_total * 100) if cycles_total > 0 else 0
            dismantle_status = get_dismantling_status(biz.id)
            biz_tuples.append((biz, config, biz_name, biz_class, progress_pct, dismantle_status))

        # Apply biz_filter
        if biz_filter == "active":
            biz_tuples = [(b, c, n, cl, p, d) for b, c, n, cl, p, d in biz_tuples if b.is_active and not d]
        elif biz_filter == "paused":
            biz_tuples = [(b, c, n, cl, p, d) for b, c, n, cl, p, d in biz_tuples if not b.is_active and not d]
        elif biz_filter == "production":
            biz_tuples = [(b, c, n, cl, p, d) for b, c, n, cl, p, d in biz_tuples if cl == "production"]
        elif biz_filter == "retail":
            biz_tuples = [(b, c, n, cl, p, d) for b, c, n, cl, p, d in biz_tuples if cl == "retail"]
        elif biz_filter == "dismantling":
            biz_tuples = [(b, c, n, cl, p, d) for b, c, n, cl, p, d in biz_tuples if d]

        # Apply sort
        if sort == "status":
            biz_tuples.sort(key=lambda x: (0 if x[0].is_active else 1, x[2]))
        elif sort == "type":
            biz_tuples.sort(key=lambda x: (x[3], x[2]))
        elif sort == "progress":
            biz_tuples.sort(key=lambda x: x[4], reverse=True)
        else:
            # name sort
            biz_tuples.sort(key=lambda x: x[2])

        # Filter/sort bar
        def _f_link(f_val, label):
            color = "#38bdf8" if biz_filter == f_val else "#64748b"
            border = "1px solid #38bdf8" if biz_filter == f_val else "1px solid #1e293b"
            return f'<a href="/businesses?sort={sort}&biz_filter={f_val}" style="color:{color};border:{border};padding:4px 10px;border-radius:4px;text-decoration:none;font-size:0.82rem;">{label}</a>'

        def _s_link(s_val, label):
            color = "#38bdf8" if sort == s_val else "#64748b"
            return f'<a href="/businesses?sort={s_val}&biz_filter={biz_filter}" style="color:{color};text-decoration:none;font-size:0.82rem;">{label}</a>'

        filter_sort_bar = f'''
        <div style="margin-bottom:16px;display:flex;flex-wrap:wrap;gap:8px;align-items:center;">
            <span style="color:#64748b;font-size:0.82rem;">Filter:</span>
            {_f_link("all","All")} {_f_link("active","Active")} {_f_link("paused","Paused")} {_f_link("production","Production")} {_f_link("retail","Retail")} {_f_link("dismantling","Dismantling")}
            <span style="color:#1e293b;margin:0 4px;">|</span>
            <span style="color:#64748b;font-size:0.82rem;">Sort:</span>
            {_s_link("name","Name")} {_s_link("status","Status")} {_s_link("type","Type")} {_s_link("progress","Progress")}
        </div>'''

        biz_html = f'<a href="/" style="color: #38bdf8;"><- Dashboard</a><h1>Business Terminal</h1><a href="/stats/production-costs" class="btn-blue">📊 Production Costs</a>{filter_sort_bar}'
        for biz, config, biz_name, biz_class, progress_pct, dismantle_status in biz_tuples:
            cycles_total = config.get("cycles_to_complete", 1)
            plot = land_db.query(LandPlot).filter(LandPlot.id == biz.land_plot_id).first()
            plot_info = f"Plot #{plot.id} ({plot.terrain_type.title()})" if plot else "Unknown Location"

            if dismantle_status:
                biz_html += f'''
                <div class="card" style="border-color: #ef4444;">
                    <h3>{biz_name} <span class="badge" style="background: #ef4444;">DISMANTLING</span></h3>
                    <p>{plot_info} | ID: #{biz.id}</p>
                    <p>Ticks Remaining: {dismantle_status['ticks_remaining']}/{DISMANTLING_TICKS} ({dismantle_status['progress_pct']:.0f}%)</p>
                    <p>Total Refund: ${dismantle_status['total_refund']:.2f} (Paid: ${dismantle_status['paid_so_far']:.2f})</p>
                </div>'''
                continue
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

            import json as _json
            paused_line_idxs = set(_json.loads(biz.paused_lines or "[]"))
            paused_product_keys = set(_json.loads(biz.paused_products or "[]"))

            if biz_class == "production":
                biz_html += '<div style="margin-top: 10px; border-top: 1px solid #1e293b; padding-top: 10px;"><strong>Production Lines:</strong>'
                for li, line in enumerate(config.get("production_lines", [])):
                    inputs = " + ".join([f"{req['quantity']} {req['item'].replace('_', ' ').title()}" for req in line.get("inputs", [])])
                    output = f"{line['output_qty']} {line['output_item'].replace('_', ' ').title()}"
                    line_paused = li in paused_line_idxs
                    pause_label = "Resume" if line_paused else "Pause"
                    pause_color = "#22c55e" if line_paused else "#f59e0b"
                    line_style = "opacity:0.45;" if line_paused else ""
                    biz_html += f'''
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;padding:5px;background:#020617;border-radius:4px;{line_style}">
                        <span style="font-size:0.85rem;color:#64748b;">→ {inputs or "No inputs"} = {output}</span>
                        <form action="/api/business/toggle-line" method="post" style="margin-left:8px;flex-shrink:0;">
                            <input type="hidden" name="business_id" value="{biz.id}">
                            <input type="hidden" name="line_index" value="{li}">
                            <button type="submit" style="padding:3px 8px;font-size:0.75rem;background:{pause_color};color:#020617;border:none;border-radius:3px;cursor:pointer;font-weight:bold;">{pause_label}</button>
                        </form>
                    </div>'''
                biz_html += '</div>'

            elif biz_class == "retail":
                biz_html += '<div style="margin-top: 10px; border-top: 1px solid #1e293b; padding-top: 10px;"><strong>Retail Sales & Pricing:</strong>'
                for item, stats in config.get("products", {}).items():
                    price_entry = land_db.query(RetailPrice).filter(RetailPrice.player_id == player.id, RetailPrice.item_type == item).first()
                    current_p = f"${price_entry.price:.2f}" if price_entry else "MKT Default"
                    item_paused = item in paused_product_keys
                    pause_label = "Resume" if item_paused else "Pause"
                    pause_color = "#22c55e" if item_paused else "#f59e0b"
                    row_style = "opacity:0.45;" if item_paused else ""
                    biz_html += f'''
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; padding: 5px; background: #020617; border-radius: 4px;{row_style}">
                        <span style="font-size: 0.9rem;">{item.replace("_", " ").title()} (E: {stats["elasticity"]})</span>
                        <div style="display: flex; align-items: center; gap: 6px;">
                            <span style="color: #38bdf8; font-weight: bold;">{current_p}</span>
                            <form action="/api/retail/set-price" method="post" style="display: flex; gap: 4px;">
                                <input type="hidden" name="item_type" value="{item}">
                                <input type="number" name="price" step="0.01" placeholder="Set Price" style="padding: 4px; width: 80px;" required>
                                <button type="submit" class="btn-blue" style="padding: 4px 8px; font-size: 0.8rem;">Update</button>
                            </form>
                            <form action="/api/business/toggle-retail" method="post">
                                <input type="hidden" name="business_id" value="{biz.id}">
                                <input type="hidden" name="item_type" value="{item}">
                                <button type="submit" style="padding:4px 8px;font-size:0.8rem;background:{pause_color};color:#020617;border:none;border-radius:3px;cursor:pointer;font-weight:bold;">{pause_label}</button>
                            </form>
                        </div>
                    </div>'''
                biz_html += '</div>'
            
            biz_html += '</div>'

        land_db.close()
        tut_overlay = ""
        try:
            from tutorial_ux import get_tutorial_overlay_html
            tut_overlay = get_tutorial_overlay_html(player, "businesses")
        except Exception:
            pass
        return shell("Businesses", tut_overlay + biz_html, player.cash_balance, player.id)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return shell("Businesses", f"Error loading terminal: {e}", player.cash_balance, player.id)

@router.get("/inventory", response_class=HTMLResponse)
def inventory_page(session_token: Optional[str] = Cookie(None), filter: str = "all", sort: str = "name", dir: str = "asc"):
    """Inventory management view."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return player
    try:
        import inventory as inv_mod
        inv = inv_mod.get_player_inventory(player.id)

        categories = {"all": "All", "seeds": "Seeds", "fruits": "Fruits", "vegetables": "Vegetables", "liquids": "Liquids", "energy": "Energy", "animals": "Animals", "materials": "Materials", "luxury": "Luxury", "financial": "Financial"}
        filter_tabs = '<div style="margin-bottom: 16px; display: flex; flex-wrap: wrap; gap: 8px;">'
        for k, v in categories.items():
            color = "#38bdf8" if k == filter else "#64748b"
            border = "1px solid #38bdf8" if k == filter else "1px solid #1e293b"
            filter_tabs += f'<a href="/inventory?filter={k}&sort={sort}&dir={dir}" style="color: {color}; border: {border}; padding: 4px 12px; border-radius: 4px; text-decoration: none; font-size: 0.85rem;">{v}</a>'
        filter_tabs += '</div>'

        # Sort controls
        sort_controls = '<div style="margin-bottom: 16px; display: flex; gap: 12px; align-items: center;"><span style="color: #64748b; font-size: 0.85rem;">Sort:</span>'
        sort_options = [("name", "Name"), ("qty", "Quantity"), ("value", "Value")]
        for s_key, s_label in sort_options:
            if s_key == sort:
                new_dir = "desc" if dir == "asc" else "asc"
                arrow = " ↑" if dir == "asc" else " ↓"
                color = "#38bdf8"
            else:
                new_dir = "asc"
                arrow = ""
                color = "#64748b"
            sort_controls += f'<a href="/inventory?filter={filter}&sort={s_key}&dir={new_dir}" style="color: {color}; text-decoration: none; font-size: 0.85rem;">{s_label}{arrow}</a>'
        sort_controls += '</div>'

        # Categorisation helpers
        fruits_list = ["apples", "oranges", "bananas", "grapes", "strawberries", "blueberries", "peaches", "pears", "mangoes", "pineapples"]
        vegetables_list = ["potatoes", "carrots", "tomatoes", "onions", "lettuce", "broccoli", "spinach", "peppers", "cucumbers", "corn"]
        animals_list = ["horses", "cows", "chickens", "pigs", "sheep", "goats", "ducks", "rabbits", "fish", "cattle"]
        materials_list = ["lumber", "steel", "brick", "glass", "coal", "iron", "copper", "stone", "cement", "wood", "ore", "clay", "sand", "gravel"]
        luxury_list = ["diamonds", "gold", "wine", "perfume", "silk", "ivory", "platinum", "jewelry", "fur", "truffles"]
        financial_list = ["shares", "bonds", "certificates", "notes", "tokens", "deeds"]

        def _item_category(item):
            if item.endswith("_seeds"):
                return "seeds"
            if item in fruits_list:
                return "fruits"
            if item in vegetables_list:
                return "vegetables"
            if "water" in item or item.endswith("_juice") or item.endswith("_milk"):
                return "liquids"
            if item == "energy":
                return "energy"
            if item in animals_list:
                return "animals"
            if item in materials_list:
                return "materials"
            if item in luxury_list:
                return "luxury"
            if any(item.startswith(f) or item.endswith(f) for f in financial_list):
                return "financial"
            return "other"

        # Filter items
        filtered = []
        for item, qty in inv.items():
            if filter != "all":
                cat = _item_category(item)
                if cat != filter:
                    continue
            item_info = inv_mod.get_item_info(item) or {}
            unit_price = item_info.get("base_price") or item_info.get("value") or 0
            filtered.append((item, qty, item_info, unit_price))

        # Sort items
        if sort == "qty":
            filtered.sort(key=lambda x: x[1], reverse=True)
        elif sort == "value":
            filtered.sort(key=lambda x: x[1] * x[3], reverse=True)
        else:
            # name sort
            if dir == "desc":
                filtered.sort(key=lambda x: x[0], reverse=True)
            else:
                filtered.sort(key=lambda x: x[0])

        items_html = ""
        for item, qty, item_info, unit_price in filtered:
            est_value_line = ""
            if unit_price:
                est_val = qty * unit_price
                est_value_line = f'<br><small style="color: #22c55e;">Est. Value: ${est_val:,.2f} (${unit_price:.2f}/unit)</small>'
            items_html += f'''
            <div class="card">
                <div style="display: flex; justify-content: space-between;">
                    <div>
                        <strong>{item.replace("_", " ").title()}</strong><br>
                        <small style="color: #64748b;">{item_info.get("description", "No description")}</small>{est_value_line}
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

        inv_body = f'<a href="/" style="color: #38bdf8;"><- Dashboard</a><h1>Your Inventory</h1>{filter_tabs}{sort_controls}{items_html}'

        # Inject tutorial overlay for inventory-relevant steps
        try:
            from tutorial_ux import get_tutorial_overlay_html
            tut_overlay = get_tutorial_overlay_html(player, "inventory")
            if tut_overlay:
                inv_body = tut_overlay + inv_body
        except Exception:
            pass

        return shell("Inventory", inv_body, player.cash_balance, player.id)
    except Exception as e:
        return shell("Inventory", f"Error: {e}", player.cash_balance, player.id)

@router.get("/land", response_class=HTMLResponse)
def land(session_token: Optional[str] = Cookie(None), sort: str = "id", order: str = "asc"):
    """Land management view with organized layout, sorting, and explanatory info."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return player
    try:
        from land import get_player_land, TERRAIN_TYPES, PROXIMITY_FEATURES, calculate_player_hoarding_tax, HOARDING_FREE_PLOTS
        from business import BUSINESS_TYPES
        plots = get_player_land(player.id)

        # Calculate hoarding tax for this player
        hoarding_info = calculate_player_hoarding_tax(len(plots))

        # Calculate player's business count for cost multiplier
        from business import Business
        from land import get_db as get_land_db
        land_db = get_land_db()
        owned_businesses_count = land_db.query(Business).filter(Business.owner_id == player.id).count()

        # Sort plots
        def sort_key(p):
            if sort == "terrain": return p.terrain_type
            if sort == "efficiency": return p.efficiency
            if sort == "tax": return p.monthly_tax
            if sort == "status": return (0 if p.occupied_by_business_id else 1)
            if sort == "size": return p.size
            return p.id

        reverse = (order == "desc")
        plots = sorted(plots, key=sort_key, reverse=reverse)

        # Compute portfolio stats
        total_plots = len(plots)
        occupied_count = sum(1 for p in plots if p.occupied_by_business_id)
        vacant_count = total_plots - occupied_count
        total_monthly_tax = sum(p.monthly_tax for p in plots)
        avg_efficiency = (sum(p.efficiency for p in plots) / total_plots) if total_plots else 0

        # Terrain colors for visual grouping
        terrain_colors = {
            "prairie": "#22c55e", "forest": "#16a34a", "desert": "#f59e0b",
            "marsh": "#06b6d4", "mountain": "#94a3b8", "tundra": "#38bdf8",
            "jungle": "#10b981", "savanna": "#eab308", "hills": "#a3e635",
            "island": "#3b82f6", "district_food": "#f97316", "district_hospital": "#ef4444",
            "district_industrial": "#64748b", "district_medical": "#ec4899",
            "district_neighborhood": "#a855f7", "district_transport": "#6366f1",
            "district_utilities": "#0ea5e9", "district_zoo": "#84cc16"
        }

        # Build sort toggle helper
        def sort_link(field, label):
            new_order = "desc" if (sort == field and order == "asc") else "asc"
            arrow = ""
            if sort == field:
                arrow = " ▲" if order == "asc" else " ▼"
            return f'<a href="/land?sort={field}&order={new_order}" style="padding: 6px 12px; font-size: 0.8rem; background: {"#1e293b" if sort == field else "#0f172a"}; color: {"#38bdf8" if sort == field else "#94a3b8"}; border: 1px solid #1e293b; border-radius: 3px; text-decoration: none; white-space: nowrap;">{label}{arrow}</a>'

        land_html = '<a href="/" style="color: #38bdf8;"><- Dashboard</a>'

        # Header with navigation
        land_html += '''
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; margin-bottom: 8px;">
            <h1 style="margin: 0;">Land Portfolio</h1>
            <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                <a href="/land-market" class="btn-blue" style="display: inline-flex; align-items: center; gap: 6px; padding: 8px 16px; text-decoration: none;">Buy Land</a>
                <a href="/districts" class="btn-blue" style="display: inline-flex; align-items: center; gap: 6px; padding: 8px 16px; background: #6366f1; text-decoration: none;">Districts</a>
            </div>
        </div>'''

        # Explainer box
        land_html += '''
        <div style="padding: 12px 16px; background: #0f172a; border-left: 4px solid #38bdf8; margin-bottom: 20px; font-size: 0.85rem; color: #94a3b8; line-height: 1.5;">
            Your land plots generate value through the businesses you build on them.
            <strong style="color: #e5e7eb;">Vacant</strong> plots can host new businesses or be listed for sale on the land market.
            <strong style="color: #e5e7eb;">Efficiency</strong> degrades slowly over time and affects business output.
            <strong style="color: #e5e7eb;">Tax</strong> is charged monthly based on terrain type, size, and proximity features.
            <strong style="color: #dc2626;">Hoarding fee:</strong> owning more than {HOARDING_FREE_PLOTS} plots incurs an escalating hourly fee using Fibonacci-scaled tiers.
        </div>'''

        if total_plots == 0:
            land_html += '''
            <div class="card" style="text-align: center; padding: 40px;">
                <p style="font-size: 1.1rem; color: #94a3b8; margin-bottom: 16px;">You don't own any land yet.</p>
                <a href="/land-market" class="btn-blue" style="padding: 12px 24px; font-size: 1rem; text-decoration: none;">Browse the Land Market</a>
            </div>'''
        else:
            # Portfolio Summary Stats
            land_html += f'''
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-bottom: 20px;">
                <div style="background: #0f172a; border: 1px solid #1e293b; padding: 14px; text-align: center;">
                    <div style="font-size: 1.4rem; font-weight: bold; color: #38bdf8;">{total_plots}</div>
                    <div style="font-size: 0.75rem; color: #64748b; margin-top: 4px;">TOTAL PLOTS</div>
                </div>
                <div style="background: #0f172a; border: 1px solid #1e293b; padding: 14px; text-align: center;">
                    <div style="font-size: 1.4rem; font-weight: bold; color: #ef4444;">{occupied_count}</div>
                    <div style="font-size: 0.75rem; color: #64748b; margin-top: 4px;">OCCUPIED</div>
                </div>
                <div style="background: #0f172a; border: 1px solid #1e293b; padding: 14px; text-align: center;">
                    <div style="font-size: 1.4rem; font-weight: bold; color: #22c55e;">{vacant_count}</div>
                    <div style="font-size: 0.75rem; color: #64748b; margin-top: 4px;">VACANT</div>
                </div>
                <div style="background: #0f172a; border: 1px solid #1e293b; padding: 14px; text-align: center;">
                    <div style="font-size: 1.4rem; font-weight: bold; color: #f59e0b;">${total_monthly_tax:,.0f}</div>
                    <div style="font-size: 0.75rem; color: #64748b; margin-top: 4px;">MONTHLY TAX</div>
                </div>
                <div style="background: #0f172a; border: 1px solid #1e293b; padding: 14px; text-align: center;">
                    <div style="font-size: 1.4rem; font-weight: bold; color: #a855f7;">{avg_efficiency:.2f}%</div>
                    <div style="font-size: 0.75rem; color: #64748b; margin-top: 4px;">AVG EFFICIENCY</div>
                </div>
                <div style="background: #0f172a; border: 1px solid {'#dc2626' if hoarding_info['excess_plots'] > 0 else '#1e293b'}; padding: 14px; text-align: center;">
                    <div style="font-size: 1.4rem; font-weight: bold; color: {'#dc2626' if hoarding_info['excess_plots'] > 0 else '#22c55e'};">${hoarding_info['monthly_total']:,.0f}</div>
                    <div style="font-size: 0.75rem; color: #64748b; margin-top: 4px;">HOARDING FEE/MO</div>
                </div>
            </div>'''

            # Hoarding tax warning banner
            if hoarding_info["excess_plots"] > 0:
                breakdown_rows = ""
                for item in hoarding_info["breakdown"]:
                    breakdown_rows += f'<tr><td style="padding: 4px 8px; color: #e5e7eb;">Plot #{item["plot_number"]}</td><td style="padding: 4px 8px; color: #f59e0b; text-align: right;">{item["multiplier"]:.1f}x</td><td style="padding: 4px 8px; color: #dc2626; text-align: right;">${item["monthly_tax"]:,.0f}/mo</td></tr>'

                land_html += f'''
            <div style="padding: 14px 18px; background: linear-gradient(135deg, #1a0505, #0f172a); border: 1px solid #dc2626; border-radius: 4px; margin-bottom: 20px;">
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                    <span style="font-size: 1.1rem; font-weight: bold; color: #dc2626;">Land Hoarding Fee Active</span>
                </div>
                <p style="font-size: 0.85rem; color: #94a3b8; margin: 0 0 10px 0; line-height: 1.5;">
                    You own <strong style="color: #e5e7eb;">{total_plots}</strong> plots — <strong style="color: #dc2626;">{hoarding_info["excess_plots"]}</strong> over the {HOARDING_FREE_PLOTS}-plot allowance.
                    Excess plots incur a Fibonacci-scaled hoarding fee of <strong style="color: #dc2626;">${hoarding_info["monthly_total"]:,.0f}/mo</strong> (${hoarding_info["hourly_total"]:,.2f}/hr), paid each hour.
                    Consider creating <a href="/districts" style="color: #6366f1;">districts</a> to consolidate land.
                </p>
                <details style="cursor: pointer;">
                    <summary style="font-size: 0.8rem; color: #64748b;">Fee breakdown per excess plot</summary>
                    <table style="width: 100%; margin-top: 8px; font-size: 0.8rem; border-collapse: collapse;">
                        <thead><tr style="border-bottom: 1px solid #1e293b;"><th style="padding: 4px 8px; text-align: left; color: #64748b;">Plot</th><th style="padding: 4px 8px; text-align: right; color: #64748b;">Multiplier</th><th style="padding: 4px 8px; text-align: right; color: #64748b;">Fee</th></tr></thead>
                        <tbody>{breakdown_rows}</tbody>
                    </table>
                </details>
            </div>'''

            # Sort controls
            land_html += f'''
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 16px; flex-wrap: wrap;">
                <span style="font-size: 0.8rem; color: #64748b;">Sort by:</span>
                {sort_link("id", "Plot ID")}
                {sort_link("terrain", "Terrain")}
                {sort_link("efficiency", "Efficiency")}
                {sort_link("tax", "Tax")}
                {sort_link("status", "Status")}
                {sort_link("size", "Size")}
            </div>'''

            # Plot cards
            for plot in plots:
                status = 'OCCUPIED' if plot.occupied_by_business_id else 'VACANT'
                status_color = "#ef4444" if plot.occupied_by_business_id else "#22c55e"
                terrain_color = terrain_colors.get(plot.terrain_type, "#64748b")
                terrain_info = TERRAIN_TYPES.get(plot.terrain_type, {})
                terrain_desc = terrain_info.get("description", "")

                # Parse proximity features
                features = plot.proximity_features.split(",") if plot.proximity_features else []
                features_html = ""
                if features:
                    for feat in features:
                        feat = feat.strip()
                        feat_info = PROXIMITY_FEATURES.get(feat, {})
                        feat_desc = feat_info.get("description", feat)
                        features_html += f'<span style="font-size: 0.7rem; padding: 2px 6px; background: #1e293b; border: 1px solid #334155; border-radius: 3px; color: #94a3b8;" title="{feat_desc}">{feat.replace("_", " ").title()}</span>'

                # Efficiency color
                eff = plot.efficiency
                if eff >= 90: eff_color = "#22c55e"
                elif eff >= 70: eff_color = "#eab308"
                elif eff >= 50: eff_color = "#f59e0b"
                else: eff_color = "#ef4444"

                # Efficiency bar width
                eff_width = min(100, max(0, eff))

                land_html += f'''
                <div class="card" style="border-left: 4px solid {terrain_color}; margin-bottom: 12px;">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px;">
                        <div style="flex: 1; min-width: 250px;">
                            <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                                <h3 style="margin: 0;">Plot #{plot.id}</h3>
                                <span class="badge" style="background: {status_color}; color: #020617;">{status}</span>
                                <span class="badge" style="background: {terrain_color}22; color: {terrain_color}; border: 1px solid {terrain_color}44;">{plot.terrain_type.replace("_", " ").title()}</span>
                            </div>
                            <p style="color: #64748b; font-size: 0.8rem; margin: 4px 0;">{terrain_desc}</p>

                            <div style="display: flex; gap: 16px; flex-wrap: wrap; margin-top: 8px; font-size: 0.85rem;">
                                <div>
                                    <span style="color: #64748b;">Size:</span>
                                    <span style="color: #e5e7eb;">{plot.size:.1f}</span>
                                </div>
                                <div>
                                    <span style="color: #64748b;">Tax:</span>
                                    <span style="color: #f59e0b;">${plot.monthly_tax:,.2f}/mo</span>
                                </div>
                            </div>

                            <div style="margin-top: 8px;">
                                <div style="display: flex; align-items: center; gap: 8px;">
                                    <span style="font-size: 0.8rem; color: #64748b;">Efficiency:</span>
                                    <span style="font-size: 0.85rem; color: {eff_color}; font-weight: bold;">{eff:.3f}%</span>
                                </div>
                                <div style="background: #020617; height: 6px; border-radius: 3px; margin-top: 4px; width: 200px;">
                                    <div style="background: {eff_color}; height: 6px; border-radius: 3px; width: {eff_width}%;"></div>
                                </div>
                            </div>'''

                if features:
                    land_html += f'''
                            <div style="display: flex; gap: 6px; flex-wrap: wrap; margin-top: 8px;">
                                <span style="font-size: 0.75rem; color: #64748b;">Features:</span>
                                {features_html}
                            </div>'''

                land_html += '</div>'

                # Actions column
                if not plot.occupied_by_business_id:
                    land_html += f'''
                        <div style="display: flex; flex-direction: column; gap: 10px; min-width: 220px;">
                            <form action="/api/business/create" method="post" style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
                                <input type="hidden" name="land_plot_id" value="{plot.id}">
                                <select name="business_type" required style="flex: 1; min-width: 140px;">
                                    <option value="">Build Business...</option>'''

                    # Calculate actual startup costs for each business type
                    for btype, config in sorted(BUSINESS_TYPES.items(), key=lambda x: x[1].get("name", x[0])):
                        if plot.terrain_type in config.get("allowed_terrain", []):
                            base_cost = config.get("startup_cost", 2500.0)
                            multiplier = max(1.25, owned_businesses_count)
                            actual_cost = base_cost * multiplier
                            business_name = config.get("name", btype)
                            land_html += f'<option value="{btype}">{business_name} (${actual_cost:,.0f})</option>'

                    land_html += '''</select><button type="submit" class="btn-blue">Build</button>
                            </form>
                            <form action="/api/land-market/list-land" method="post" style="display: flex; gap: 8px; align-items: center;">
                                <input type="hidden" name="land_plot_id" value="''' + str(plot.id) + '''">
                                <input type="number" name="asking_price" step="0.01" placeholder="Asking $" style="width: 110px;" required>
                                <button type="submit" class="btn-orange">List for Sale</button>
                            </form>
                        </div>'''
                else:
                    # Show which business occupies this plot
                    biz = land_db.query(Business).filter(Business.id == plot.occupied_by_business_id).first()
                    biz_name = biz.business_type.replace("_", " ").title() if biz else f"Business #{plot.occupied_by_business_id}"
                    land_html += f'''
                        <div style="min-width: 180px; text-align: right;">
                            <div style="font-size: 0.8rem; color: #64748b;">Business</div>
                            <div style="font-size: 0.9rem; color: #e5e7eb; font-weight: 500;">{biz_name}</div>
                        </div>'''

                land_html += '</div></div>'

        land_db.close()

        # Inject tutorial overlay for land-relevant steps
        try:
            from tutorial_ux import get_tutorial_overlay_html
            tut_overlay = get_tutorial_overlay_html(player, "land")
            if tut_overlay:
                land_html = tut_overlay + land_html
        except Exception:
            pass

        return shell("Land", land_html, player.cash_balance, player.id)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return shell("Land", f"Error: {e}", player.cash_balance, player.id)

@router.get("/land-market", response_class=HTMLResponse)
def land_market_page(session_token: Optional[str] = Cookie(None), sort: str = "price", order: str = "asc", terrain: str = "all", tab: str = "auctions"):
    """Land market view - government auctions and player listings with search, sort, and filter."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return player

    try:
        from land_market import get_active_auctions, get_active_listings, get_land_bank_plots, get_recent_sales
        from land import get_land_plot, TERRAIN_TYPES, PROXIMITY_FEATURES

        auctions = get_active_auctions()
        listings = get_active_listings()
        bank_plots = get_land_bank_plots()
        recent_sales = get_recent_sales(limit=8)

        # Terrain colors
        terrain_colors = {
            "prairie": "#22c55e", "forest": "#16a34a", "desert": "#f59e0b",
            "marsh": "#06b6d4", "mountain": "#94a3b8", "tundra": "#38bdf8",
            "jungle": "#10b981", "savanna": "#eab308", "hills": "#a3e635",
            "island": "#3b82f6"
        }

        # Gather all plots for terrain filter tabs
        all_terrains = set()
        auction_plots = {}
        for a in auctions:
            p = get_land_plot(a.land_plot_id)
            if p:
                auction_plots[a.id] = p
                all_terrains.add(p.terrain_type)
        listing_plots = {}
        for l in listings:
            p = get_land_plot(l.land_plot_id)
            if p:
                listing_plots[l.id] = p
                all_terrains.add(p.terrain_type)

        # Market stats
        total_auctions = len(auctions)
        total_listings = len(listings)
        total_available = total_auctions + total_listings
        avg_auction_price = (sum(a.current_price for a in auctions) / total_auctions) if total_auctions else 0
        avg_listing_price = (sum(l.asking_price for l in listings) / total_listings) if total_listings else 0

        market_html = '<a href="/" style="color: #38bdf8;"><- Dashboard</a>'

        # Header
        market_html += '''
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; margin-bottom: 8px;">
            <h1 style="margin: 0;">Land Market</h1>
            <a href="/land" class="btn-blue" style="display: inline-flex; align-items: center; gap: 6px; padding: 8px 16px; text-decoration: none;">Your Land Portfolio</a>
        </div>'''

        # Explainer
        market_html += '''
        <div style="padding: 12px 16px; background: #0f172a; border-left: 4px solid #f59e0b; margin-bottom: 20px; font-size: 0.85rem; color: #94a3b8; line-height: 1.5;">
            <strong style="color: #f59e0b;">Government Auctions</strong> use a Dutch auction system &mdash; the price starts high and drops over time until someone buys.
            Wait for a lower price, but risk losing the plot to another buyer.
            <strong style="color: #a855f7;">Player Listings</strong> are fixed-price sales from other players.
            Land varies by <strong style="color: #e5e7eb;">terrain type</strong> (which businesses can operate) and
            <strong style="color: #e5e7eb;">proximity features</strong> (bonuses like coastal access or urban demand).
        </div>'''

        # Market stats summary
        market_html += f'''
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-bottom: 20px;">
            <div style="background: #0f172a; border: 1px solid #1e293b; padding: 14px; text-align: center;">
                <div style="font-size: 1.4rem; font-weight: bold; color: #38bdf8;">{total_available}</div>
                <div style="font-size: 0.75rem; color: #64748b; margin-top: 4px;">PLOTS FOR SALE</div>
            </div>
            <div style="background: #0f172a; border: 1px solid #1e293b; padding: 14px; text-align: center;">
                <div style="font-size: 1.4rem; font-weight: bold; color: #f59e0b;">{total_auctions}</div>
                <div style="font-size: 0.75rem; color: #64748b; margin-top: 4px;">GOV AUCTIONS</div>
            </div>
            <div style="background: #0f172a; border: 1px solid #1e293b; padding: 14px; text-align: center;">
                <div style="font-size: 1.4rem; font-weight: bold; color: #a855f7;">{total_listings}</div>
                <div style="font-size: 0.75rem; color: #64748b; margin-top: 4px;">PLAYER LISTINGS</div>
            </div>
            <div style="background: #0f172a; border: 1px solid #1e293b; padding: 14px; text-align: center;">
                <div style="font-size: 1.4rem; font-weight: bold; color: #22c55e;">${avg_auction_price:,.0f}</div>
                <div style="font-size: 0.75rem; color: #64748b; margin-top: 4px;">AVG AUCTION PRICE</div>
            </div>
            <div style="background: #0f172a; border: 1px solid #1e293b; padding: 14px; text-align: center;">
                <div style="font-size: 1.4rem; font-weight: bold; color: #10b981;">{len(bank_plots)}</div>
                <div style="font-size: 0.75rem; color: #64748b; margin-top: 4px;">IN LAND BANK</div>
            </div>
        </div>'''

        # Tab navigation (Auctions / Player Listings)
        def tab_style(t):
            if tab == t:
                return "padding: 10px 20px; font-size: 0.9rem; background: #1e293b; color: #e5e7eb; border: 1px solid #334155; border-bottom: 2px solid #38bdf8; text-decoration: none; font-weight: bold;"
            return "padding: 10px 20px; font-size: 0.9rem; background: #0f172a; color: #64748b; border: 1px solid #1e293b; text-decoration: none;"

        market_html += f'''
        <div style="display: flex; gap: 4px; margin-bottom: 16px; flex-wrap: wrap;">
            <a href="/land-market?tab=auctions&sort={sort}&order={order}&terrain={terrain}" style="{tab_style("auctions")}">Government Auctions ({total_auctions})</a>
            <a href="/land-market?tab=listings&sort={sort}&order={order}&terrain={terrain}" style="{tab_style("listings")}">Player Listings ({total_listings})</a>
            <a href="/land-market?tab=history&sort={sort}&order={order}&terrain={terrain}" style="{tab_style("history")}">Recent Sales</a>
        </div>'''

        # Terrain filter tabs
        if all_terrains:
            market_html += '<div style="margin-bottom: 16px;"><span style="font-size: 0.8rem; color: #64748b; margin-right: 8px;">Filter terrain:</span>'
            all_active = "background: #1e293b; color: #38bdf8; border: 1px solid #38bdf8;" if terrain == "all" else "background: #0f172a; color: #94a3b8; border: 1px solid #1e293b;"
            market_html += f'<a href="/land-market?tab={tab}&sort={sort}&order={order}&terrain=all" style="padding: 4px 10px; font-size: 0.8rem; {all_active} border-radius: 3px; text-decoration: none; display: inline-block; margin: 2px;">All</a>'
            for t in sorted(all_terrains):
                if t.startswith("district_"):
                    continue
                t_color = terrain_colors.get(t, "#64748b")
                is_active = terrain == t
                bg = f"{t_color}" if is_active else "#0f172a"
                fg = "#020617" if is_active else t_color
                border = f"1px solid {t_color}"
                market_html += f'<a href="/land-market?tab={tab}&sort={sort}&order={order}&terrain={t}" style="padding: 4px 10px; font-size: 0.8rem; background: {bg}; color: {fg}; border: {border}; border-radius: 3px; text-decoration: none; display: inline-block; margin: 2px;">{t.replace("_", " ").title()}</a>'
            market_html += '</div>'

        # Sort controls
        def sort_link(field, label):
            new_order = "desc" if (sort == field and order == "asc") else "asc"
            arrow = ""
            if sort == field:
                arrow = " ▲" if order == "asc" else " ▼"
            active = sort == field
            return f'<a href="/land-market?tab={tab}&sort={field}&order={new_order}&terrain={terrain}" style="padding: 6px 12px; font-size: 0.8rem; background: {"#1e293b" if active else "#0f172a"}; color: {"#38bdf8" if active else "#94a3b8"}; border: 1px solid #1e293b; border-radius: 3px; text-decoration: none; white-space: nowrap;">{label}{arrow}</a>'

        if tab in ("auctions", "listings"):
            market_html += f'''
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 16px; flex-wrap: wrap;">
                <span style="font-size: 0.8rem; color: #64748b;">Sort by:</span>
                {sort_link("price", "Price")}
                {sort_link("terrain", "Terrain")}
                {sort_link("efficiency", "Efficiency")}
                {sort_link("tax", "Tax")}
                {sort_link("size", "Size")}
                {sort_link("time", "Time") if tab == "auctions" else ""}
            </div>'''

        # ===== AUCTIONS TAB =====
        if tab == "auctions":
            if not auctions:
                market_html += '''
                <div class="card" style="text-align: center; padding: 30px;">
                    <p style="color: #94a3b8;">No active government auctions at this time.</p>
                    <p style="font-size: 0.8rem; color: #64748b;">New auctions appear as the economy grows. Check back soon.</p>
                </div>'''
            else:
                # Build sortable auction data
                auction_data = []
                for auction in auctions:
                    plot = auction_plots.get(auction.id)
                    if not plot:
                        continue
                    if terrain != "all" and plot.terrain_type != terrain:
                        continue
                    auction_data.append((auction, plot))

                # Sort
                def auction_sort_key(item):
                    a, p = item
                    if sort == "price": return a.current_price
                    if sort == "terrain": return p.terrain_type
                    if sort == "efficiency": return p.efficiency
                    if sort == "tax": return p.monthly_tax
                    if sort == "size": return p.size
                    if sort == "time": return a.end_time.timestamp() if a.end_time else 0
                    return a.current_price
                auction_data.sort(key=auction_sort_key, reverse=(order == "desc"))

                if not auction_data:
                    market_html += f'<p style="color: #64748b;">No auctions match the "{terrain}" terrain filter.</p>'

                for auction, plot in auction_data:
                    time_remaining = auction.end_time - datetime.utcnow()
                    total_secs = max(0, time_remaining.total_seconds())
                    hours_left = int(total_secs / 3600)
                    minutes_left = int((total_secs % 3600) / 60)
                    price_drop_pct = ((auction.starting_price - auction.current_price) / auction.starting_price * 100) if auction.starting_price > 0 else 0
                    terrain_color = terrain_colors.get(plot.terrain_type, "#64748b")
                    terrain_info = TERRAIN_TYPES.get(plot.terrain_type, {})

                    # Parse proximity features
                    features = plot.proximity_features.split(",") if plot.proximity_features else []
                    features_html = ""
                    for feat in features:
                        feat = feat.strip()
                        if not feat:
                            continue
                        feat_info = PROXIMITY_FEATURES.get(feat, {})
                        feat_desc = feat_info.get("description", feat)
                        features_html += f'<span style="font-size: 0.7rem; padding: 2px 6px; background: #1e293b; border: 1px solid #334155; border-radius: 3px; color: #94a3b8;" title="{feat_desc}">{feat.replace("_", " ").title()}</span> '

                    # Urgency color for time
                    if hours_left < 1:
                        time_color = "#ef4444"
                    elif hours_left < 6:
                        time_color = "#f59e0b"
                    else:
                        time_color = "#64748b"

                    # Price progress bar
                    price_range = auction.starting_price - auction.minimum_price
                    price_progress = ((auction.starting_price - auction.current_price) / price_range * 100) if price_range > 0 else 0

                    market_html += f'''
                    <div class="card" style="border-left: 4px solid {terrain_color}; margin-bottom: 12px;">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px;">
                            <div style="flex: 1; min-width: 280px;">
                                <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                                    <h3 style="margin: 0;">Plot #{plot.id}</h3>
                                    <span class="badge" style="background: #f59e0b; color: #020617;">AUCTION</span>
                                    <span class="badge" style="background: {terrain_color}22; color: {terrain_color}; border: 1px solid {terrain_color}44;">{plot.terrain_type.replace("_", " ").title()}</span>
                                </div>
                                <p style="color: #64748b; font-size: 0.8rem; margin: 4px 0;">{terrain_info.get("description", "")}</p>

                                <div style="display: flex; gap: 16px; flex-wrap: wrap; margin-top: 8px; font-size: 0.85rem;">
                                    <div><span style="color: #64748b;">Size:</span> <span style="color: #e5e7eb;">{plot.size:.1f}</span></div>
                                    <div><span style="color: #64748b;">Efficiency:</span> <span style="color: #22c55e;">{plot.efficiency:.2f}%</span></div>
                                    <div><span style="color: #64748b;">Tax:</span> <span style="color: #f59e0b;">${plot.monthly_tax:,.2f}/mo</span></div>
                                </div>'''

                    if features_html:
                        market_html += f'''
                                <div style="display: flex; gap: 6px; flex-wrap: wrap; margin-top: 8px;">
                                    <span style="font-size: 0.75rem; color: #64748b;">Features:</span>
                                    {features_html}
                                </div>'''

                    market_html += f'''
                                <div style="margin-top: 12px; padding: 10px; background: #020617; border-radius: 4px;">
                                    <div style="display: flex; justify-content: space-between; font-size: 0.8rem; margin-bottom: 6px;">
                                        <span style="color: #ef4444;">Start: ${auction.starting_price:,.0f}</span>
                                        <span style="color: #22c55e; font-weight: bold;">Now: ${auction.current_price:,.0f}</span>
                                        <span style="color: #64748b;">Floor: ${auction.minimum_price:,.0f}</span>
                                    </div>
                                    <div style="background: #1e293b; height: 6px; border-radius: 3px;">
                                        <div style="background: linear-gradient(90deg, #ef4444, #22c55e); height: 6px; border-radius: 3px; width: {min(100, price_progress):.0f}%;"></div>
                                    </div>
                                    <div style="display: flex; justify-content: space-between; margin-top: 6px; font-size: 0.75rem;">
                                        <span style="color: #64748b;">Dropped {price_drop_pct:.1f}%</span>
                                        <span style="color: {time_color};">{hours_left}h {minutes_left}m remaining</span>
                                    </div>
                                </div>
                            </div>
                            <div style="display: flex; flex-direction: column; align-items: center; gap: 8px; min-width: 120px;">
                                <div style="text-align: center;">
                                    <div style="font-size: 1.3rem; font-weight: bold; color: #22c55e;">${auction.current_price:,.0f}</div>
                                    <div style="font-size: 0.7rem; color: #64748b;">current price</div>
                                </div>
                                <form action="/api/land-market/buy-auction" method="post">
                                    <input type="hidden" name="auction_id" value="{auction.id}">
                                    <button type="submit" class="btn-blue" style="padding: 10px 20px; font-size: 0.9rem;" onclick="return confirm('Buy Plot #{plot.id} for ${auction.current_price:,.2f}?')">
                                        Buy Now
                                    </button>
                                </form>
                            </div>
                        </div>
                    </div>'''

        # ===== PLAYER LISTINGS TAB =====
        elif tab == "listings":
            if not listings:
                market_html += '''
                <div class="card" style="text-align: center; padding: 30px;">
                    <p style="color: #94a3b8;">No player listings available.</p>
                    <p style="font-size: 0.8rem; color: #64748b;">Players can list vacant land for sale from their Land Portfolio page.</p>
                </div>'''
            else:
                from auth import get_db as get_auth_db, Player as AuthPlayer

                # Build sortable listing data
                listing_data = []
                for listing in listings:
                    plot = listing_plots.get(listing.id)
                    if not plot:
                        continue
                    if terrain != "all" and plot.terrain_type != terrain:
                        continue
                    listing_data.append((listing, plot))

                # Sort
                def listing_sort_key(item):
                    l, p = item
                    if sort == "price": return l.asking_price
                    if sort == "terrain": return p.terrain_type
                    if sort == "efficiency": return p.efficiency
                    if sort == "tax": return p.monthly_tax
                    if sort == "size": return p.size
                    if sort == "time": return l.listed_at.timestamp() if l.listed_at else 0
                    return l.asking_price
                listing_data.sort(key=listing_sort_key, reverse=(order == "desc"))

                if not listing_data:
                    market_html += f'<p style="color: #64748b;">No listings match the "{terrain}" terrain filter.</p>'

                for listing, plot in listing_data:
                    auth_db = get_auth_db()
                    seller = auth_db.query(AuthPlayer).filter(AuthPlayer.id == listing.seller_id).first()
                    auth_db.close()
                    seller_name = seller.business_name if seller else f"Player {listing.seller_id}"
                    is_own_listing = (listing.seller_id == player.id)

                    terrain_color = terrain_colors.get(plot.terrain_type, "#64748b")
                    terrain_info = TERRAIN_TYPES.get(plot.terrain_type, {})

                    features = plot.proximity_features.split(",") if plot.proximity_features else []
                    features_html = ""
                    for feat in features:
                        feat = feat.strip()
                        if not feat:
                            continue
                        feat_info = PROXIMITY_FEATURES.get(feat, {})
                        feat_desc = feat_info.get("description", feat)
                        features_html += f'<span style="font-size: 0.7rem; padding: 2px 6px; background: #1e293b; border: 1px solid #334155; border-radius: 3px; color: #94a3b8;" title="{feat_desc}">{feat.replace("_", " ").title()}</span> '

                    border_color = "#38bdf8" if is_own_listing else terrain_color
                    own_badge = '<span class="badge" style="background: #38bdf8; color: #020617;">YOUR LISTING</span>' if is_own_listing else ""

                    market_html += f'''
                    <div class="card" style="border-left: 4px solid {border_color}; margin-bottom: 12px;">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px;">
                            <div style="flex: 1; min-width: 280px;">
                                <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                                    <h3 style="margin: 0;">Plot #{plot.id}</h3>
                                    {own_badge}
                                    <span class="badge" style="background: {terrain_color}22; color: {terrain_color}; border: 1px solid {terrain_color}44;">{plot.terrain_type.replace("_", " ").title()}</span>
                                </div>
                                <p style="color: #64748b; font-size: 0.8rem; margin: 4px 0;">{terrain_info.get("description", "")}</p>

                                <div style="display: flex; gap: 16px; flex-wrap: wrap; margin-top: 8px; font-size: 0.85rem;">
                                    <div><span style="color: #64748b;">Size:</span> <span style="color: #e5e7eb;">{plot.size:.1f}</span></div>
                                    <div><span style="color: #64748b;">Efficiency:</span> <span style="color: #22c55e;">{plot.efficiency:.2f}%</span></div>
                                    <div><span style="color: #64748b;">Tax:</span> <span style="color: #f59e0b;">${plot.monthly_tax:,.2f}/mo</span></div>
                                    <div><span style="color: #64748b;">Seller:</span> <span style="color: #94a3b8;">{seller_name}</span></div>
                                </div>'''

                    if features_html:
                        market_html += f'''
                                <div style="display: flex; gap: 6px; flex-wrap: wrap; margin-top: 8px;">
                                    <span style="font-size: 0.75rem; color: #64748b;">Features:</span>
                                    {features_html}
                                </div>'''

                    market_html += '''
                            </div>
                            <div style="display: flex; flex-direction: column; align-items: center; gap: 8px; min-width: 120px;">'''

                    market_html += f'''
                                <div style="text-align: center;">
                                    <div style="font-size: 1.3rem; font-weight: bold; color: #22c55e;">${listing.asking_price:,.0f}</div>
                                    <div style="font-size: 0.7rem; color: #64748b;">asking price</div>
                                </div>'''

                    if is_own_listing:
                        market_html += f'''
                                <form action="/api/land-market/cancel-listing" method="post">
                                    <input type="hidden" name="listing_id" value="{listing.id}">
                                    <button type="submit" class="btn-red" style="padding: 10px 20px; font-size: 0.9rem;">Cancel</button>
                                </form>'''
                    else:
                        market_html += f'''
                                <form action="/api/land-market/buy-listing" method="post">
                                    <input type="hidden" name="listing_id" value="{listing.id}">
                                    <button type="submit" class="btn-blue" style="padding: 10px 20px; font-size: 0.9rem;" onclick="return confirm('Buy Plot #{plot.id} for ${listing.asking_price:,.2f}?')">Buy Now</button>
                                </form>'''

                    market_html += '</div></div></div>'

        # ===== RECENT SALES TAB =====
        elif tab == "history":
            market_html += '''
            <div style="padding: 10px 16px; background: #0f172a; border-left: 4px solid #64748b; margin-bottom: 16px; font-size: 0.85rem; color: #94a3b8;">
                Recent land sales help you gauge fair market prices. Government auction sales and player-to-player trades are both shown.
            </div>'''

            if not recent_sales:
                market_html += '''
                <div class="card" style="text-align: center; padding: 30px;">
                    <p style="color: #94a3b8;">No land sales recorded yet.</p>
                </div>'''
            else:
                # Table header
                market_html += '''
                <div class="card" style="padding: 0; overflow-x: auto;">
                    <table style="width: 100%; border-collapse: collapse; font-size: 0.85rem;">
                        <thead>
                            <tr style="border-bottom: 1px solid #1e293b; color: #64748b;">
                                <th style="padding: 12px; text-align: left;">Plot</th>
                                <th style="padding: 12px; text-align: left;">Terrain</th>
                                <th style="padding: 12px; text-align: left;">Type</th>
                                <th style="padding: 12px; text-align: right;">Price</th>
                                <th style="padding: 12px; text-align: right;">Date</th>
                            </tr>
                        </thead>
                        <tbody>'''

                from auth import get_db as get_auth_db, Player as AuthPlayer
                for sale in recent_sales:
                    plot = get_land_plot(sale.land_plot_id)
                    terrain_name = plot.terrain_type.replace("_", " ").title() if plot else "Unknown"
                    t_color = terrain_colors.get(plot.terrain_type, "#64748b") if plot else "#64748b"
                    sale_type_badge = '<span style="color: #f59e0b;">Auction</span>' if sale.sale_type == "government" else '<span style="color: #a855f7;">Player</span>'
                    sale_date = sale.sold_at.strftime("%b %d, %H:%M") if sale.sold_at else "N/A"

                    market_html += f'''
                            <tr style="border-bottom: 1px solid #0f172a;">
                                <td style="padding: 10px 12px; color: #e5e7eb;">#{sale.land_plot_id}</td>
                                <td style="padding: 10px 12px; color: {t_color};">{terrain_name}</td>
                                <td style="padding: 10px 12px;">{sale_type_badge}</td>
                                <td style="padding: 10px 12px; text-align: right; color: #22c55e; font-weight: bold;">${sale.price:,.0f}</td>
                                <td style="padding: 10px 12px; text-align: right; color: #64748b;">{sale_date}</td>
                            </tr>'''

                market_html += '</tbody></table></div>'

        # Land Bank status (always shown at bottom)
        if bank_plots:
            market_html += f'''
            <div style="margin-top: 24px; padding: 12px 16px; background: #0f172a; border: 1px solid #1e293b;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div style="font-size: 0.85rem; color: #64748b; font-weight: bold;">Land Bank</div>
                        <div style="font-size: 0.8rem; color: #94a3b8; margin-top: 4px;">{len(bank_plots)} unsold plot(s) awaiting re-auction. These will automatically appear as new auctions soon.</div>
                    </div>
                </div>
            </div>'''

        # Inject tutorial overlay for land-market step
        try:
            from tutorial_ux import get_tutorial_overlay_html
            tut_overlay = get_tutorial_overlay_html(player, "land_market")
            if tut_overlay:
                market_html = tut_overlay + market_html
        except Exception:
            pass

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
        
        # Group items by category
        categories = {}
        for i in items:
            info = inv_mod.get_item_info(i)
            cat = info.get("category", "other") if info else "other"
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(i)
        
        # Category colors
        # Category colors
        cat_colors = {
            "seeds": "#22c55e",
            "fruits": "#84cc16",
            "vegetables": "#16a34a",
            "crops": "#eab308",
            "food": "#f97316",
            "prepared_food": "#fb923c",
            "beverage": "#06b6d4",
            "alcohol": "#a855f7",
            "ingredients": "#ec4899",
            "livestock": "#92400e",
            "feed": "#a3e635",
            "health": "#ef4444",
            "personal_care": "#f472b6",
            "industrial": "#64748b",
            "materials": "#78716c",
            "textiles": "#c084fc",
            "wood": "#a16207",
            "ore": "#71717a",
            "metals": "#94a3b8",
            "components": "#6366f1",
            "auto_parts": "#3b82f6",
            "marine_parts": "#0ea5e9",
            "vehicle": "#2563eb",
            "apparel": "#d946ef",
            "accessories": "#e879f9",
            "home_goods": "#14b8a6",
            "packaging": "#737373",
            "media": "#facc15",
            "liquids": "#38bdf8",
            "energy": "#f59e0b",
            "financial": "#10b981",
            "luxury": "#d4af37",
            "minerals": "#a8a29e",
            "other": "#94a3b8"
        }
        
        # Search bar
        search_bar = '''
        <div style="margin-bottom: 16px;">
            <input 
                type="text" 
                id="itemSearch" 
                placeholder="🔍 Search commodities..." 
                style="width: 100%; padding: 12px; background: #0f172a; border: 1px solid #1e293b; color: #e5e7eb; font-family: 'JetBrains Mono', monospace; font-size: 14px; border-radius: 4px;"
                oninput="filterItems()"
                autofocus
            >
            <div id="searchResults" style="color: #64748b; font-size: 0.85rem; margin-top: 8px;"></div>
        </div>
        '''
        
        # Build category tabs
        filter_tabs = '<div id="itemTabs" style="margin-bottom: 20px; max-width: 100%;">'
        
        for cat_name, cat_items in sorted(categories.items()):
            cat_color = cat_colors.get(cat_name, "#64748b")
            filter_tabs += f'''
            <div style="margin-bottom: 12px;">
                <div style="color: {cat_color}; font-size: 0.75rem; font-weight: bold; margin-bottom: 6px; text-transform: uppercase;">
                    {cat_name.replace("_", " ")}
                </div>
                <div style="display: flex; flex-wrap: wrap; gap: 6px;">
            '''
            for i in sorted(cat_items):
                is_selected = i == item
                bg_color = cat_color if is_selected else "#0f172a"
                text_color = "#020617" if is_selected else cat_color
                border = f"1px solid {cat_color}"
                display_name = i.replace("_", " ").title()
                
                filter_tabs += f'''
                <a href="/market?item={i}" 
                   class="item-tab" 
                   data-item="{i}" 
                   data-display="{display_name}"
                   style="padding: 4px 10px; font-size: 0.8rem; background: {bg_color}; color: {text_color}; 
                          border: {border}; border-radius: 3px; text-decoration: none; display: inline-block;">
                    {display_name}
                </a>'''
            filter_tabs += '</div></div>'
        
        filter_tabs += '</div>'
        
        # Search script
        search_script = '''
        <script>
        function filterItems() {
            const searchInput = document.getElementById('itemSearch').value.toLowerCase();
            const tabs = document.querySelectorAll('.item-tab');
            const resultsDiv = document.getElementById('searchResults');
            let visibleCount = 0;
            
            tabs.forEach(tab => {
                const itemName = tab.getAttribute('data-item').toLowerCase();
                const displayName = tab.getAttribute('data-display').toLowerCase();
                
                if (itemName.includes(searchInput) || displayName.includes(searchInput)) {
                    tab.style.display = 'inline-block';
                    visibleCount++;
                } else {
                    tab.style.display = 'none';
                }
            });
            
            if (searchInput && visibleCount === 0) {
                resultsDiv.textContent = '⚠ No items found';
                resultsDiv.style.color = '#ef4444';
            } else if (searchInput) {
                resultsDiv.textContent = `✓ Showing ${visibleCount} item${visibleCount !== 1 ? 's' : ''}`;
                resultsDiv.style.color = '#22c55e';
            } else {
                resultsDiv.textContent = '';
            }
        }
        </script>
        '''
        
        # Item info
        item_info = inv_mod.get_item_info(item)
        item_name = item_info.get("name", item.replace("_", " ").title()) if item_info else item.replace("_", " ").title()
        item_desc = item_info.get("description", "") if item_info else ""
        item_cat = item_info.get("category", "other") if item_info else "other"
        
        # Build market HTML
        market_html = f'''
        <a href="/" style="color: #38bdf8;"><- Dashboard</a>
        <div style="display: flex; gap: 20px; max-width: 100%;">
            <div style="flex: 2; min-width: 0;">
                <h1>📈 Market</h1>
                <div style="margin-bottom: 16px; padding: 12px; background: #0f172a; border-left: 4px solid {cat_colors.get(item_cat, "#64748b")};">
                    <div style="font-size: 1.2rem; font-weight: bold; color: #38bdf8;">{item_name}</div>
                    <div style="color: #64748b; font-size: 0.85rem; margin-top: 4px;">{item_desc}</div>
                    <div style="color: #94a3b8; font-size: 0.75rem; margin-top: 4px;">Category: {item_cat.upper()}</div>
                </div>
                
                {search_bar}
                {filter_tabs}
                {search_script}
                
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
                    
                    <!-- BIDS -->
                    <div class="card">
                        <h3 style="color: #22c55e;">Bids (Buy Orders)</h3>
                        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; margin-bottom: 8px; padding-bottom: 8px; border-bottom: 1px solid #1e293b; font-size: 0.85rem; color: #64748b;">
                            <span>Price</span>
                            <span>Qty</span>
                            <span>Trader</span>
                        </div>'''
        
        if order_book and order_book.get('bids'):
            for price, qty, order_id, player_name, player_id in order_book['bids'][:10]:
                market_html += f'''
                        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; font-size: 0.9rem; padding: 4px 0; color: #22c55e;">
                            <span>${price:.2f}</span>
                            <span>{qty:,.2f}</span>
                            <span style="font-size: 0.8rem; color: #64748b;">{player_name[:15]}</span>
                        </div>'''
        else:
            market_html += '<p style="color: #64748b; font-size: 0.85rem; padding: 8px 0;">No bids</p>'
        
        market_html += '''
                    </div>
                    
                    <!-- ASKS -->
                    <div class="card">
                        <h3 style="color: #ef4444;">Asks (Sell Orders)</h3>
                        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; margin-bottom: 8px; padding-bottom: 8px; border-bottom: 1px solid #1e293b; font-size: 0.85rem; color: #64748b;">
                            <span>Price</span>
                            <span>Qty</span>
                            <span>Trader</span>
                        </div>'''
        
        if order_book and order_book.get('asks'):
            for price, qty, order_id, player_name, player_id in order_book['asks'][:10]:
                market_html += f'''
                        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; font-size: 0.9rem; padding: 4px 0; color: #ef4444;">
                            <span>${price:.2f}</span>
                            <span>{qty:,.2f}</span>
                            <span style="font-size: 0.8rem; color: #64748b;">{player_name[:15]}</span>
                        </div>'''
        else:
            market_html += '<p style="color: #64748b; font-size: 0.85rem; padding: 8px 0;">No asks</p>'
        
        market_html += f'''
                    </div>
                </div>
            </div>
            
            <!-- Sidebar -->
            <div style="flex: 1; min-width: 0; max-width: 280px;">
                <div class="card">
                    <h3>Market Stats</h3>
                    <p><strong>24h Volume:</strong><br>${stats["volume_24h"]:,.2f}</p>
                    <p style="margin-top: 12px;"><strong>Total Trades:</strong><br>{stats["total_trades"]:,}</p>
                    <p style="margin-top: 12px;"><strong>Active Orders:</strong><br>{stats["active_orders"]:,}</p>
                </div>
            </div>
        </div>
        '''
        
        # Inject tutorial overlay for market-relevant steps
        try:
            from tutorial_ux import get_tutorial_overlay_html
            tut_overlay = get_tutorial_overlay_html(player, "market")
            if tut_overlay:
                market_html = tut_overlay + market_html
        except Exception:
            pass

        return shell("Market", market_html, player.cash_balance, player.id)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return shell("Market", f"Error loading market: {e}", player.cash_balance, player.id)

# ==========================
# WPE COMPANY LISTINGS PAGE
# ==========================
# Add this route to ux.py for viewing all public companies

@router.get("/brokerage/companies", response_class=HTMLResponse)
def brokerage_companies_page(session_token: Optional[str] = Cookie(None)):
    """View all public companies listed on WPE."""
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
        <h1>WPE Listed Companies</h1>
        <p style="color: #64748b;">{len(company_data)} companies listed on the Wadsworth Player Exchange</p>
        
        {companies_html}
        '''
        
        return shell("WPE Companies", body, player.cash_balance, player.id)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return shell("WPE Companies", f"Error: {e}", player.cash_balance, player.id)


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
            CompanyShares, ShareholderPosition, get_db as get_firm_db, delist_company
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

                # Pre-build conditional forms to avoid nested f-string issues
                buyback_form_html = ""
                if company.shares_in_float > 0:
                    buyback_form_html = f'''
                        <form action="/api/brokerage/buyback" method="post" style="display: inline;">
                            <input type="hidden" name="company_id" value="{company.id}">
                            <input type="number" name="shares" placeholder="Shares to buy" style="width: 100px; padding: 6px;" min="1" max="{company.shares_in_float}">
                            <button type="submit" class="btn-orange">Buyback</button>
                        </form>'''

                go_private_form_html = ""
                if item["can_delist"]:
                    go_private_form_html = f'''
                        <form action="/api/brokerage/go-private" method="post" style="display: inline;">
                            <input type="hidden" name="company_id" value="{company.id}">
                            <button type="submit" class="btn-red" onclick="return confirm('Take company private? This will delist the stock and you cannot re-IPO for 7200 ticks.')">
                                Go Private
                            </button>
                        </form>'''
                else:
                    go_private_form_html = '<span style="color: #64748b; font-size: 0.85rem;">Buy back all shares to go private</span>'

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
                        {buyback_form_html}
                        {go_private_form_html}
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
            CompanyShares, ShareholderPosition, delist_company, get_db as get_firm_db
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
        success, error_msg = delist_company(player.id, company_id)
        
        if success:
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
                        <h3 style="margin: 0;">🏛️ Wadsworth Brokerage Firm</h3>
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
                    <a href="/brokerage/trading" class="btn-blue" style="background: #22c55e;">Trade WPE</a>
                    <a href="/brokerage/ipo" class="btn-orange">Launch IPO</a>
                    <a href="/brokerage/commodities" class="btn-blue" style="background: #8b5cf6;">WCE Commodities</a>
                </div>
            </div>
            '''
        except Exception as e:
            print(f"[UX] Brokerage firm card error: {e}")
            import traceback
            traceback.print_exc()
            bank_html += '''
            <div class="card" style="border: 1px solid #ef4444;">
                <h3>🏛️ Wadsworth Brokerage Firm</h3>
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
            # Make ticker clickable
            ticker_items.append(
                f'<a href="/brokerage/trading?ticker={company.ticker_symbol}" style="color: {change_color}; text-decoration: none; font-weight: bold;">{company.ticker_symbol}</a>: ${company.current_price:.2f} {change_indicator}'
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
        <!-- WPE Company Ticker (slower scroll) -->
        <div style="background: #0f172a; border: 1px solid #1e293b; padding: 8px 0; margin-bottom: 20px; overflow: hidden;">
            <div style="font-size: 0.75rem; color: #64748b; padding: 0 12px; margin-bottom: 4px;">WPE PLAYER EXCHANGE</div>
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
                <h3>📈 WPE Trading</h3>
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
                <a href="/brokerage/commodities" class="btn-orange" style="display: inline-block; margin-top: 10px;">WCE Market</a>
            </div>
            <div class="card">
                <h3>💳 Credit & Liens</h3>
                <p style="color: #64748b; font-size: 0.9rem;">Your credit rating and debts</p>
                <a href="/brokerage/credit" class="btn-blue" style="display: inline-block; margin-top: 10px;">View Credit</a>
            </div>
            <div class="card">
                <h3>⚙️ Corporate Actions</h3>
                <p style="color: #64748b; font-size: 0.9rem;">Automate buybacks, splits, offerings</p>
                <a href="/corporate-actions/dashboard" class="btn-blue" style="display: inline-block; margin-top: 10px;">Manage Actions</a>
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
    """WPE equity trading page."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player

    try:
        from banks.brokerage_firm import (
            CompanyShares, ShareholderPosition, get_player_credit,
            calculate_margin_multiplier, get_db as get_firm_db, BANK_PLAYER_ID
        )
        from banks.brokerage_order_book import (
            get_order_book_depth, get_recent_fills, OrderBook, OrderStatus,
            get_db as get_book_db
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
            <h1>WPE Trading Floor</h1>
            <p style="color: #64748b;">No companies are currently listed on the exchange.</p>
            <a href="/brokerage/ipo" class="btn-blue">Launch the First IPO</a>
            '''
            return shell("WPE Trading", body, player.cash_balance, player.id)

        # Get order book data for selected company
        order_book = get_order_book_depth(selected_company.id, depth=10)
        recent_trades = get_recent_fills(selected_company.id, limit=10)

        # Get player's pending orders for this company
        book_db = get_book_db()
        try:
            pending_orders = book_db.query(OrderBook).filter(
                OrderBook.player_id == player.id,
                OrderBook.company_shares_id == selected_company.id,
                OrderBook.status.in_([
                    OrderStatus.PENDING.value,
                    OrderStatus.PARTIAL.value
                ])
            ).order_by(OrderBook.created_at.desc()).all()
        finally:
            book_db.close()
        
        # Get player's position in selected company
        player_position = player_positions.get(selected_company.id)
        player_shares = player_position.shares_owned if player_position else 0
        player_cost_basis = player_position.average_cost_basis if player_position else 0
        
        # Calculate margin multiplier for this stock
        max_margin = calculate_margin_multiplier(player.id, selected_company.id)
        
        # Trading halted check
        is_halted = selected_company.trading_halted_until and datetime.utcnow() < selected_company.trading_halted_until
        
        # ===== MODERN TRADING DASHBOARD =====

        # Portfolio totals for summary bar
        total_portfolio_value = 0
        total_portfolio_cost = 0
        total_margin_debt = 0
        positions_data = []

        for company in companies:
            pos = player_positions.get(company.id)
            shares = pos.shares_owned if pos else 0
            cost_basis = pos.average_cost_basis if pos else 0
            mkt_val = shares * company.current_price
            cost_total = shares * cost_basis
            pl = mkt_val - cost_total if shares > 0 else 0
            margin_debt_val = 0
            if pos and hasattr(pos, 'margin_debt') and pos.margin_debt:
                margin_debt_val = pos.margin_debt

            total_portfolio_value += mkt_val
            total_portfolio_cost += cost_total
            total_margin_debt += margin_debt_val

            positions_data.append({
                'company': company,
                'shares': shares,
                'cost_basis': cost_basis,
                'mkt_val': mkt_val,
                'pl': pl,
                'is_selected': company.id == selected_company.id
            })

        total_pl = total_portfolio_value - total_portfolio_cost
        total_pl_pct = (total_pl / total_portfolio_cost * 100) if total_portfolio_cost > 0 else 0
        num_positions = sum(1 for p in positions_data if p['shares'] > 0)

        # Price change from IPO
        price_change = selected_company.current_price - selected_company.ipo_price
        price_change_pct = (price_change / selected_company.ipo_price * 100) if selected_company.ipo_price > 0 else 0
        change_color = "#22c55e" if price_change >= 0 else "#ef4444"
        change_sign = "+" if price_change >= 0 else ""

        # Player position metrics for selected stock
        player_mkt_value = player_shares * selected_company.current_price
        player_total_cost = player_shares * player_cost_basis
        player_pl = player_mkt_value - player_total_cost if player_shares > 0 else 0
        player_pl_pct = (player_pl / player_total_cost * 100) if player_total_cost > 0 else 0
        pl_color = "#22c55e" if player_pl >= 0 else "#ef4444"

        # Generate SVG sparkline from recent trades
        sparkline_svg = '<div style="height:80px;display:flex;align-items:center;justify-content:center;color:#334155;font-size:0.75rem;">No trade history</div>'
        if recent_trades:
            spark_prices = [t['price'] for t in reversed(recent_trades)]
            if len(spark_prices) >= 2:
                min_p = min(spark_prices)
                max_p = max(spark_prices)
                pr = max_p - min_p if max_p != min_p else 1
                pts = []
                area = []
                for i, p in enumerate(spark_prices):
                    x = 2 + i / (len(spark_prices) - 1) * 496
                    y = 2 + 76 - ((p - min_p) / pr * 76)
                    pts.append(f"{x:.1f},{y:.1f}")
                    area.append(f"{x:.1f},{y:.1f}")
                area.append("498,80")
                area.append("2,80")
                lc = "#22c55e" if spark_prices[-1] >= spark_prices[0] else "#ef4444"
                sparkline_svg = f'<svg viewBox="0 0 500 80" preserveAspectRatio="none" style="width:100%;height:80px;display:block;"><defs><linearGradient id="sfill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="{lc}" stop-opacity="0.2"/><stop offset="100%" stop-color="{lc}" stop-opacity="0.01"/></linearGradient></defs><polygon points="{" ".join(area)}" fill="url(#sfill)"/><polyline points="{" ".join(pts)}" fill="none" stroke="{lc}" stroke-width="1.5" stroke-linejoin="round"/></svg>'

        # Dividend display
        dividend_display = "None"
        if selected_company.dividend_config:
            div_parts = []
            for div in selected_company.dividend_config:
                dt = div.get("type", "")
                freq = div.get("frequency", "")
                if dt == "cash":
                    div_parts.append(f'Cash {div.get("amount",0)*100:.1f}% ({freq})')
                elif dt == "commodity":
                    div_parts.append(f'{div.get("item","item")}: {div.get("amount",0)}/{div.get("per_shares",100)}shs ({freq})')
                elif dt == "scrip":
                    div_parts.append(f'Stock {div.get("rate",0)*100:.1f}% ({freq})')
            if div_parts:
                dividend_display = " | ".join(div_parts)

        # Build positions sidebar HTML
        positions_html = ""
        for pd_item in positions_data:
            c = pd_item['company']
            is_sel = pd_item['is_selected']
            bg = "#1e293b" if is_sel else "transparent"
            bl = "3px solid #38bdf8" if is_sel else "3px solid transparent"
            shares_txt = f"{pd_item['shares']:,} shs" if pd_item['shares'] > 0 else ""
            pl_txt = ""
            plc = "#64748b"
            if pd_item['shares'] > 0 and pd_item['cost_basis'] > 0:
                plc = "#22c55e" if pd_item['pl'] >= 0 else "#ef4444"
                pl_txt = f"{'+'if pd_item['pl']>=0 else ''}${pd_item['pl']:,.2f}"
            positions_html += f'<a href="/brokerage/trading?ticker={c.ticker_symbol}" style="display:block;padding:8px 10px;border-left:{bl};background:{bg};text-decoration:none;color:#e5e7eb;">'
            positions_html += f'<div style="display:flex;justify-content:space-between;align-items:baseline;"><span style="font-weight:{"700" if is_sel else "500"};font-size:0.85rem;">{c.ticker_symbol}</span><span style="font-size:0.8rem;color:#94a3b8;">${c.current_price:.2f}</span></div>'
            if shares_txt or pl_txt:
                positions_html += f'<div style="display:flex;justify-content:space-between;margin-top:2px;font-size:0.7rem;"><span style="color:#64748b;">{shares_txt}</span><span style="color:{plc};">{pl_txt}</span></div>'
            positions_html += '</a>'

        # Build order book depth ladder
        spread = order_book['spread']
        spread_pct = order_book['spread_pct']
        all_bq = [q for _, q in order_book['bids']] + [q for _, q in order_book['asks']]
        max_bq = max(all_bq) if all_bq else 1

        ob_html = '<div style="font-size:0.7rem;color:#475569;display:grid;grid-template-columns:1fr 1fr;padding:2px 8px;margin-bottom:4px;"><span>PRICE</span><span style="text-align:right;">QTY</span></div>'
        if order_book['asks']:
            for price, qty in reversed(order_book['asks']):
                bw = qty / max_bq * 100
                ob_html += f'<div style="position:relative;padding:2px 8px;display:grid;grid-template-columns:1fr 1fr;font-size:0.8rem;"><div style="position:absolute;right:0;top:0;bottom:0;width:{bw:.0f}%;background:rgba(239,68,68,0.1);"></div><span style="color:#ef4444;position:relative;">${price:.4f}</span><span style="text-align:right;color:#94a3b8;position:relative;">{qty:,}</span></div>'
        else:
            ob_html += '<div style="padding:4px 8px;color:#334155;font-size:0.75rem;text-align:center;">No asks</div>'
        ob_html += f'<div style="padding:4px 8px;text-align:center;font-size:0.7rem;color:#64748b;border-top:1px solid #1e293b;border-bottom:1px solid #1e293b;background:#0a0f1a;">Spread ${spread:.4f} ({spread_pct:.2f}%)</div>'
        if order_book['bids']:
            for price, qty in order_book['bids']:
                bw = qty / max_bq * 100
                ob_html += f'<div style="position:relative;padding:2px 8px;display:grid;grid-template-columns:1fr 1fr;font-size:0.8rem;"><div style="position:absolute;right:0;top:0;bottom:0;width:{bw:.0f}%;background:rgba(34,197,94,0.1);"></div><span style="color:#22c55e;position:relative;">${price:.4f}</span><span style="text-align:right;color:#94a3b8;position:relative;">{qty:,}</span></div>'
        else:
            ob_html += '<div style="padding:4px 8px;color:#334155;font-size:0.75rem;text-align:center;">No bids</div>'

        # Build recent trades (time & sales)
        trades_html = ""
        if recent_trades:
            prev_price = None
            for trade in recent_trades:
                trade_time = trade.get('timestamp', '')
                time_str = ""
                if isinstance(trade_time, str):
                    try:
                        trade_dt = datetime.fromisoformat(trade_time.replace('Z', '+00:00'))
                        time_str = trade_dt.strftime("%H:%M")
                    except:
                        time_str = ""
                elif trade_time:
                    time_str = trade_time.strftime("%H:%M")
                tc = "#94a3b8"
                if prev_price is not None:
                    tc = "#22c55e" if trade['price'] >= prev_price else "#ef4444"
                prev_price = trade['price']
                trades_html += f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr;font-size:0.8rem;padding:2px 8px;"><span style="color:{tc};">${trade["price"]:.4f}</span><span style="text-align:right;color:#94a3b8;">{trade["quantity"]:,}</span><span style="text-align:right;color:#475569;">{time_str}</span></div>'
        else:
            trades_html = '<div style="padding:8px;color:#334155;font-size:0.75rem;text-align:center;">No trades yet</div>'

        # Build pending orders
        pending_html = ""
        if pending_orders:
            pending_html = f'<div style="margin-top:12px;"><div style="font-size:0.7rem;color:#64748b;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:6px;padding:0 4px;">Open Orders ({len(pending_orders)})</div>'
            for order in pending_orders:
                sc = "#22c55e" if order.order_side == "BUY" else "#ef4444"
                pd_str = f"${order.limit_price:.4f}" if order.limit_price else "MKT"
                rem = order.quantity - order.filled_quantity
                pending_html += f'<div style="display:flex;justify-content:space-between;align-items:center;padding:5px 4px;border-top:1px solid #0f172a;font-size:0.8rem;"><div><span style="color:{sc};font-weight:600;">{order.order_side}</span> <span style="color:#94a3b8;">{rem:,} @ {pd_str}</span></div><form action="/api/brokerage/cancel-order" method="post" style="display:inline;margin:0;"><input type="hidden" name="order_id" value="{order.id}"><button type="submit" style="background:none;border:1px solid #334155;color:#94a3b8;padding:1px 6px;font-size:0.7rem;cursor:pointer;">X</button></form></div>'
            pending_html += '</div>'

        # Halted banner
        halted_html = ""
        if is_halted:
            halted_html = f'<div style="background:#451a03;border:1px solid #f59e0b;padding:8px 12px;font-size:0.8rem;color:#fbbf24;text-align:center;margin-bottom:12px;">TRADING HALTED - Circuit breaker until {selected_company.trading_halted_until.strftime("%H:%M UTC")}</div>'

        # Margin debt HTML for summary bar
        margin_debt_html = f"<div><span class='td-label'>Margin Debt</span><div style='color:#f59e0b;font-size:0.95rem;'>${total_margin_debt:,.2f}</div></div>" if total_margin_debt > 0 else ""

        # Dashboard CSS (built as regular string to avoid f-string brace conflicts)
        td_css = '<style>'
        td_css += '.container{max-width:1440px!important;}'
        td_css += '.td-layout{display:grid;grid-template-columns:220px 1fr 280px;gap:12px;margin-top:12px;}'
        td_css += '.td-sidebar{background:#0f172a;border:1px solid #1e293b;overflow-y:auto;max-height:calc(100vh - 200px);}'
        td_css += '.td-main{min-width:0;}'
        td_css += '.td-panel{background:#0f172a;border:1px solid #1e293b;padding:14px;}'
        td_css += '.td-section{background:#0f172a;border:1px solid #1e293b;padding:12px;margin-bottom:12px;}'
        td_css += '.td-label{color:#64748b;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.5px;}'
        td_css += '#td-tab-buy,#td-tab-sell{display:none;}'
        td_css += '.td-buy-panel,.td-sell-panel{display:none;}'
        td_css += '#td-tab-buy:checked~.td-buy-panel{display:block;}'
        td_css += '#td-tab-sell:checked~.td-sell-panel{display:block;}'
        td_css += '#td-tab-buy:checked~.td-tab-bar .td-tab-buy{background:#16a34a;color:#fff;}'
        td_css += '#td-tab-sell:checked~.td-tab-bar .td-tab-sell{background:#dc2626;color:#fff;}'
        td_css += '.td-input{width:100%;padding:8px;background:#020617;border:1px solid #1e293b;color:#e5e7eb;font-size:0.85rem;font-family:inherit;}'
        td_css += '.td-input:focus{border-color:#38bdf8;outline:none;}'
        td_css += '@media(max-width:1024px){.td-layout{grid-template-columns:1fr!important;}.td-sidebar{max-height:none;overflow-x:auto;white-space:nowrap;display:flex;}.td-sidebar>a{min-width:140px;white-space:normal;}}'
        td_css += '</style>'

        # Assemble the full dashboard body
        body = td_css + f'''
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px;">
            <a href="/banks/brokerage-firm" style="color:#38bdf8;font-size:0.8rem;">&larr; Brokerage Firm</a>
            <span style="font-size:0.85rem;color:#94a3b8;font-weight:600;">WPE Trading Floor</span>
        </div>

        <!-- Portfolio Summary Bar -->
        <div style="display:flex;gap:24px;padding:10px 16px;background:#0f172a;border:1px solid #1e293b;font-size:0.8rem;flex-wrap:wrap;">
            <div>
                <span class="td-label">Portfolio Value</span>
                <div style="color:#e5e7eb;font-size:0.95rem;font-weight:600;">${total_portfolio_value:,.2f}</div>
            </div>
            <div>
                <span class="td-label">Total P/L</span>
                <div style="color:{"#22c55e" if total_pl >= 0 else "#ef4444"};font-size:0.95rem;font-weight:600;">{"+" if total_pl >= 0 else ""}${total_pl:,.2f} <span style="font-size:0.75rem;">({total_pl_pct:+.1f}%)</span></div>
            </div>
            <div>
                <span class="td-label">Buying Power</span>
                <div style="color:#22c55e;font-size:0.95rem;font-weight:600;">${player.cash_balance:,.2f}</div>
            </div>
            <div>
                <span class="td-label">Positions</span>
                <div style="color:#e5e7eb;font-size:0.95rem;">{num_positions} / {len(companies)}</div>
            </div>
            {margin_debt_html}
        </div>

        {halted_html}

        <!-- 3-Column Trading Layout -->
        <div class="td-layout">
            <!-- LEFT: Positions / Watchlist Sidebar -->
            <div class="td-sidebar">
                <div style="padding:8px 10px;border-bottom:1px solid #1e293b;font-size:0.7rem;color:#64748b;text-transform:uppercase;letter-spacing:0.5px;">
                    Watchlist &middot; {len(companies)} Listed
                </div>
                {positions_html}
            </div>

            <!-- CENTER: Stock Detail -->
            <div class="td-main">
                <!-- Price Header -->
                <div class="td-section" style="margin-bottom:0;border-bottom:none;">
                    <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px;">
                        <div>
                            <div style="font-size:1.1rem;font-weight:700;color:#e5e7eb;">{selected_company.company_name}</div>
                            <div style="font-size:0.75rem;color:#64748b;margin-top:2px;">
                                {selected_company.ticker_symbol} &middot; Class {selected_company.share_class}{" &middot; TBTF" if selected_company.is_tbtf else ""}
                            </div>
                        </div>
                        <div style="text-align:right;">
                            <div style="font-size:1.6rem;font-weight:700;color:#38bdf8;">${selected_company.current_price:.4f}</div>
                            <div style="font-size:0.8rem;color:{change_color};">
                                {change_sign}${price_change:.4f} ({price_change_pct:+.2f}%) <span style="color:#475569;">from IPO</span>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Sparkline Chart -->
                <div class="td-section" style="margin-top:0;border-top:none;padding-top:0;">
                    {sparkline_svg}
                </div>

                <!-- Key Stats Grid -->
                <div class="td-section">
                    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;">
                        <div><div class="td-label">Market Cap</div><div style="font-size:0.9rem;">${selected_company.current_price * selected_company.shares_outstanding:,.0f}</div></div>
                        <div><div class="td-label">Shares Out</div><div style="font-size:0.9rem;">{selected_company.shares_outstanding:,}</div></div>
                        <div><div class="td-label">Float</div><div style="font-size:0.9rem;">{selected_company.shares_in_float:,}</div></div>
                        <div><div class="td-label">52W Range</div><div style="font-size:0.9rem;">${selected_company.low_52_week:.2f} &mdash; ${selected_company.high_52_week:.2f}</div></div>
                        <div><div class="td-label">Volume Today</div><div style="font-size:0.9rem;">{selected_company.volume_today:,}</div></div>
                        <div><div class="td-label">Dividends</div><div style="font-size:0.85rem;">{dividend_display}</div></div>
                    </div>
                </div>

                <!-- Depth of Market + Time & Sales -->
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
                    <div class="td-section" style="margin-bottom:0;">
                        <div style="font-size:0.7rem;color:#64748b;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:6px;">Depth of Market</div>
                        {ob_html}
                    </div>
                    <div class="td-section" style="margin-bottom:0;">
                        <div style="font-size:0.7rem;color:#64748b;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:6px;">Time &amp; Sales</div>
                        <div style="font-size:0.7rem;color:#475569;display:grid;grid-template-columns:1fr 1fr 1fr;padding:2px 8px;margin-bottom:4px;"><span>PRICE</span><span style="text-align:right;">QTY</span><span style="text-align:right;">TIME</span></div>
                        {trades_html}
                    </div>
                </div>
            </div>

            <!-- RIGHT: Trade Panel -->
            <div class="td-panel">
                <!-- Position Summary -->
                <div style="margin-bottom:12px;">
                    <div style="font-size:0.7rem;color:#64748b;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:8px;">Your Position &mdash; {selected_company.ticker_symbol}</div>
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:0.8rem;">
                        <div><span style="color:#64748b;">Shares</span><div style="color:#38bdf8;font-size:1rem;font-weight:600;">{player_shares:,}</div></div>
                        <div><span style="color:#64748b;">Value</span><div style="font-size:1rem;">${player_mkt_value:,.2f}</div></div>
                        <div><span style="color:#64748b;">Avg Cost</span><div>${player_cost_basis:.4f}</div></div>
                        <div><span style="color:#64748b;">P/L</span><div style="color:{pl_color};font-weight:600;">{"+" if player_pl >= 0 else ""}${player_pl:,.2f}</div></div>
                    </div>
                </div>

                <div style="border-top:1px solid #1e293b;padding-top:12px;">
                    <!-- CSS-Only Buy/Sell Tab Toggle -->
                    <input type="radio" id="td-tab-buy" name="td-trade-tab" checked>
                    <input type="radio" id="td-tab-sell" name="td-trade-tab">
                    <div class="td-tab-bar" style="display:grid;grid-template-columns:1fr 1fr;margin-bottom:12px;">
                        <label for="td-tab-buy" class="td-tab-buy" style="padding:6px;text-align:center;cursor:pointer;font-size:0.85rem;font-weight:600;background:#1e293b;color:#64748b;border:1px solid #1e293b;">Buy</label>
                        <label for="td-tab-sell" class="td-tab-sell" style="padding:6px;text-align:center;cursor:pointer;font-size:0.85rem;font-weight:600;background:#1e293b;color:#64748b;border:1px solid #1e293b;">Sell</label>
                    </div>

                    <!-- Buy Form -->
                    <div class="td-buy-panel">
                        <form action="/api/brokerage/buy" method="post">
                            <input type="hidden" name="company_id" value="{selected_company.id}">
                            <div style="margin-bottom:10px;">
                                <label style="display:block;margin-bottom:4px;color:#94a3b8;font-size:0.8rem;">Quantity</label>
                                <input type="number" name="quantity" min="1" required class="td-input" placeholder="Shares">
                            </div>
                            <div style="margin-bottom:10px;">
                                <label style="display:block;margin-bottom:4px;color:#94a3b8;font-size:0.8rem;">Limit Price</label>
                                <input type="number" name="limit_price" step="0.0001" class="td-input" placeholder="Market @ ${selected_company.current_price:.4f}">
                            </div>
                            <div style="margin-bottom:10px;">
                                <label style="display:flex;align-items:center;gap:6px;color:#94a3b8;font-size:0.8rem;">
                                    <input type="checkbox" name="use_margin" value="1">
                                    Margin ({max_margin:.1f}x)
                                </label>
                                <div style="font-size:0.7rem;color:#475569;margin-top:2px;">
                                    Credit: {player_credit.credit_score} ({player_credit.tier.upper()})
                                </div>
                            </div>
                            <button type="submit" style="width:100%;padding:10px;background:#16a34a;color:#fff;border:none;font-size:0.85rem;font-weight:600;cursor:pointer;" {"disabled" if is_halted else ""}>
                                Buy {selected_company.ticker_symbol}
                            </button>
                        </form>
                    </div>

                    <!-- Sell Form -->
                    <div class="td-sell-panel">
                        <form action="/api/brokerage/sell" method="post">
                            <input type="hidden" name="company_id" value="{selected_company.id}">
                            <div style="margin-bottom:10px;">
                                <label style="display:block;margin-bottom:4px;color:#94a3b8;font-size:0.8rem;">Quantity</label>
                                <input type="number" name="quantity" min="1" max="{player_shares}" required class="td-input" placeholder="Max: {player_shares:,}">
                            </div>
                            <div style="margin-bottom:10px;">
                                <label style="display:block;margin-bottom:4px;color:#94a3b8;font-size:0.8rem;">Limit Price</label>
                                <input type="number" name="limit_price" step="0.0001" class="td-input" placeholder="Market @ ${selected_company.current_price:.4f}">
                            </div>
                            <div style="font-size:0.75rem;color:#64748b;margin-bottom:10px;">
                                Available: {player_shares:,} shares
                            </div>
                            <button type="submit" style="width:100%;padding:10px;background:#dc2626;color:#fff;border:none;font-size:0.85rem;font-weight:600;cursor:pointer;" {"disabled" if is_halted or player_shares == 0 else ""}>
                                Sell {selected_company.ticker_symbol}
                            </button>
                        </form>
                    </div>
                </div>

                {pending_html}

                <!-- Short Selling -->
                <div style="margin-top:12px;padding-top:12px;border-top:1px solid #1e293b;">
                    <a href="/brokerage/shorts?ticker={selected_company.ticker_symbol}" style="display:block;text-align:center;padding:6px;border:1px solid #f59e0b;color:#f59e0b;font-size:0.8rem;text-decoration:none;">
                        Short {selected_company.ticker_symbol}
                    </a>
                </div>
            </div>
        </div>
        '''

        return shell(f"Trade {selected_company.ticker_symbol}", body, player.cash_balance, player.id)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return shell("WPE Trading", f"Error: {e}", player.cash_balance, player.id)


# The helper functions need to be INSIDE the route handler

@router.get("/brokerage/ipo", response_class=HTMLResponse)
def brokerage_ipo_page(session_token: Optional[str] = Cookie(None), error: Optional[str] = None):
    """IPO creation page - redesigned for player holding companies."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player

    try:
        from banks.brokerage_firm import (
            get_firm_entity, IPO_CONFIG, IPOType,
            calculate_player_company_valuation, CompanyShares,
            calculate_delisting_cost, get_db as get_firm_db
        )
        from html import escape as html_escape

        firm = get_firm_entity()

        # Check if player already has a public company
        firm_db = get_firm_db()
        try:
            existing_company = firm_db.query(CompanyShares).filter(
                CompanyShares.founder_id == player.id,
                CompanyShares.is_delisted == False
            ).first()
        finally:
            firm_db.close()

        if existing_company:
            # Player already has a public company - show Go Private option
            cost_info, cost_err = calculate_delisting_cost(existing_company.id)
            if cost_info:
                go_private_html = f'''
                <div class="card" style="border-left: 4px solid #ef4444; margin-top: 20px;">
                    <h3>Go Private</h3>
                    <p style="color: #94a3b8; margin-bottom: 15px;">
                        Buy back all outstanding public shares and delist from the exchange.
                        Shareholders will be paid a 10% premium over the current market price.
                    </p>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 15px;">
                        <div>
                            <div style="font-size: 0.8rem; color: #64748b;">PUBLIC SHARES TO BUY BACK</div>
                            <div style="font-size: 1.3rem; font-weight: bold;">{cost_info["public_shares"]:,}</div>
                        </div>
                        <div>
                            <div style="font-size: 0.8rem; color: #64748b;">BUYBACK PRICE (10% PREMIUM)</div>
                            <div style="font-size: 1.3rem; font-weight: bold;">${cost_info["buyback_price_per_share"]:,.2f}/share</div>
                        </div>
                        <div>
                            <div style="font-size: 0.8rem; color: #64748b;">SHARE BUYBACK COST</div>
                            <div style="font-size: 1.3rem; font-weight: bold;">${cost_info["buyback_cost"]:,.0f}</div>
                        </div>
                        <div>
                            <div style="font-size: 0.8rem; color: #64748b;">DELISTING FEE (2% OF MARKET CAP)</div>
                            <div style="font-size: 1.3rem; font-weight: bold;">${cost_info["delisting_fee"]:,.0f}</div>
                        </div>
                    </div>
                    <div style="background: #0f172a; padding: 12px; border-radius: 8px; margin-bottom: 15px;">
                        <div style="display: flex; justify-content: space-between;">
                            <span style="color: #94a3b8; font-weight: bold;">TOTAL COST TO GO PRIVATE</span>
                            <span style="color: #ef4444; font-weight: bold; font-size: 1.2rem;">${cost_info["total_cost"]:,.0f}</span>
                        </div>
                    </div>
                    <form action="/api/brokerage/go-private" method="post"
                          onsubmit="return confirm('Are you sure? This will cost ${cost_info["total_cost"]:,.0f} and delist {existing_company.ticker_symbol} from the exchange.');">
                        <input type="hidden" name="company_id" value="{existing_company.id}">
                        <button type="submit" class="btn-blue" style="width: 100%; background: #991b1b; border-color: #ef4444;">
                            Go Private - Delist {existing_company.ticker_symbol}
                        </button>
                    </form>
                </div>'''
            else:
                go_private_html = ""

            error_html = ""
            if error:
                error_html = f'''
                <div class="card" style="border: 2px solid #ef4444; background: #450a0a; margin-bottom: 20px;">
                    <p style="color: #fca5a5; margin: 0;">{html_escape(error)}</p>
                </div>'''

            body = f'''
            <a href="/banks/brokerage-firm" style="color: #38bdf8;">&larr; Brokerage Firm</a>
            <h1>IPO Center</h1>
            {error_html}

            <div class="card" style="border: 2px solid #22c55e; background: #052e16;">
                <h3 style="color: #86efac;">Your Company Is Public</h3>
                <p style="color: #86efac;">
                    <strong>{existing_company.ticker_symbol}</strong> ({existing_company.company_name})
                    is listed on WPE at <strong>${existing_company.current_price:,.2f}</strong>/share.
                </p>
                <p style="color: #86efac; font-size: 0.9rem;">
                    Each player can only have one publicly traded company.
                    You can go private below to delist, then launch a new IPO later.
                </p>
                <a href="/brokerage/trading?ticker={existing_company.ticker_symbol}" class="btn-blue" style="margin-top: 10px;">Trade {existing_company.ticker_symbol}</a>
            </div>

            {go_private_html}
            '''
            return shell("IPO Center", body, player.cash_balance, player.id)

        # Get player's company valuation
        valuation = calculate_player_company_valuation(player.id)

        if not valuation or valuation["total_businesses"] == 0:
            body = '''
            <a href="/banks/brokerage-firm" style="color: #38bdf8;">&larr; Brokerage Firm</a>
            <h1>IPO Center</h1>

            <div class="card" style="border: 2px solid #ef4444; background: #450a0a;">
                <h3 style="color: #fca5a5;">No Businesses to IPO</h3>
                <p style="color: #fca5a5;">You need to build at least one business before going public.</p>
                <a href="/land" class="btn-blue" style="margin-top: 10px;">Get Land & Build</a>
            </div>
            '''
            return shell("IPO Center", body, player.cash_balance, player.id)

        # Build business breakdown
        biz_list_html = ""
        for biz in valuation["businesses_breakdown"]:
            biz_list_html += f'''
            <div style="display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #1e293b;">
                <span style="color: #94a3b8;">{biz["business_name"]}</span>
                <span style="color: #38bdf8;">${biz["total_value"]:,.0f}</span>
            </div>'''

        # Check if firm is accepting underwritten IPOs
        firm_status = ""
        if not firm.is_accepting_ipos:
            firm_status = '''
            <div class="card" style="border: 1px solid #f59e0b; background: #451a03; margin-bottom: 20px;">
                <p style="color: #fbbf24; margin: 0; font-size: 0.9rem;">
                    The Firm's cash reserves are currently low. Underwritten and Income Shares IPOs
                    are temporarily unavailable. Direct Listing is still available.
                </p>
            </div>'''

        # Build IPO option cards - each with clear tradeoffs
        direct_config = IPO_CONFIG[IPOType.DIRECT_LISTING]
        underwritten_config = IPO_CONFIG[IPOType.FIRM_UNDERWRITTEN]
        income_config = IPO_CONFIG[IPOType.INCOME_SHARES]

        error_html = ""
        if error:
            error_html = f'''
            <div class="card" style="border: 2px solid #ef4444; background: #450a0a; margin-bottom: 20px;">
                <h3 style="color: #fca5a5; margin: 0 0 5px 0;">IPO Failed</h3>
                <p style="color: #fca5a5; margin: 0;">{html_escape(error)}</p>
            </div>'''

        body = f'''
        <a href="/banks/brokerage-firm" style="color: #38bdf8;">&larr; Brokerage Firm</a>
        <h1>IPO Center</h1>
        {error_html}
        <p style="color: #64748b;">Take <strong>{player.business_name}</strong>'s business empire public on WPE</p>

        <!-- Company Valuation -->
        <div class="card" style="border-left: 4px solid #38bdf8;">
            <h3>Your Company Valuation</h3>
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 20px 0;">
                <div>
                    <div style="font-size: 0.8rem; color: #64748b;">ACTIVE BUSINESSES</div>
                    <div style="font-size: 2rem; font-weight: bold; color: #38bdf8;">{valuation["total_businesses"]}</div>
                </div>
                <div>
                    <div style="font-size: 0.8rem; color: #64748b;">TOTAL VALUATION</div>
                    <div style="font-size: 2rem; font-weight: bold; color: #22c55e;">${valuation["total_valuation"]:,.0f}</div>
                </div>
                <div>
                    <div style="font-size: 0.8rem; color: #64748b;">SUGGESTED PRICE</div>
                    <div style="font-size: 2rem; font-weight: bold;">${valuation["suggested_share_price"]:.2f}/share</div>
                </div>
            </div>
            <details style="margin-top: 15px;">
                <summary style="cursor: pointer; color: #38bdf8; font-weight: 500;">View Business Breakdown</summary>
                <div style="margin-top: 10px;">{biz_list_html}</div>
            </details>
        </div>

        {firm_status}

        <!-- IPO Type Selection -->
        <div class="card">
            <h3>Choose Your IPO Type</h3>
            <p style="color: #64748b; font-size: 0.9rem; margin-bottom: 20px;">
                Each option has real tradeoffs. Pick the one that fits your strategy.
            </p>

            <div style="display: grid; gap: 20px;">

                <!-- Option 1: Direct Listing -->
                <div class="card ipo-option" data-ipo-type="direct_listing" style="cursor: pointer; border: 2px solid #1e293b; transition: border-color 0.2s;">
                    <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 8px;">
                        <h4 style="margin: 0; color: #22c55e;">Direct Listing</h4>
                        <span style="background: #052e16; color: #22c55e; padding: 3px 10px; border-radius: 4px; font-size: 0.75rem;">$5,000 FLAT FEE</span>
                    </div>
                    <p style="color: #94a3b8; font-size: 0.9rem; line-height: 1.6; margin-bottom: 15px;">
                        {direct_config['description']}
                    </p>
                    <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; font-size: 0.85rem; margin-bottom: 15px;">
                        <div><span style="color: #64748b;">Cost:</span><br><span style="color: #22c55e;">$5,000 flat</span></div>
                        <div><span style="color: #64748b;">Capital:</span><br><span style="color: #f59e0b;">Not guaranteed</span></div>
                        <div><span style="color: #64748b;">Max Float:</span><br><span>80%</span></div>
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 0.85rem; padding-top: 10px; border-top: 1px solid #1e293b;">
                        <div>
                            <span style="color: #22c55e;">Pros:</span>
                            <ul style="margin: 5px 0 0 0; padding-left: 18px; color: #94a3b8;">
                                <li>Cheapest option</li>
                                <li>No ongoing obligations</li>
                                <li>No dependence on the Firm</li>
                            </ul>
                        </div>
                        <div>
                            <span style="color: #ef4444;">Cons:</span>
                            <ul style="margin: 5px 0 0 0; padding-left: 18px; color: #94a3b8;">
                                <li>No guaranteed buyers</li>
                                <li>You sell shares yourself</li>
                                <li>Price may be volatile</li>
                            </ul>
                        </div>
                    </div>
                    <div style="font-size: 0.8rem; color: #64748b; margin-top: 10px;">Min valuation: $25,000</div>
                    <button type="button" class="btn-blue select-ipo-btn" style="width: 100%; margin-top: 15px;">Select Direct Listing</button>
                </div>

                <!-- Option 2: Underwritten IPO -->
                <div class="card ipo-option" data-ipo-type="firm_underwritten" style="cursor: pointer; border: 2px solid #1e293b; transition: border-color 0.2s; {'opacity: 0.5; pointer-events: none;' if not firm.is_accepting_ipos else ''}">
                    <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 8px;">
                        <h4 style="margin: 0; color: #38bdf8;">Underwritten IPO</h4>
                        <span style="background: #0c1a3d; color: #38bdf8; padding: 3px 10px; border-radius: 4px; font-size: 0.75rem;">7% TO THE FIRM</span>
                    </div>
                    <p style="color: #94a3b8; font-size: 0.9rem; line-height: 1.6; margin-bottom: 15px;">
                        {underwritten_config['description']}
                    </p>
                    <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; font-size: 0.85rem; margin-bottom: 15px;">
                        <div><span style="color: #64748b;">Cost:</span><br><span style="color: #f59e0b;">7% discount</span></div>
                        <div><span style="color: #64748b;">Capital:</span><br><span style="color: #22c55e;">Guaranteed</span></div>
                        <div><span style="color: #64748b;">Max Float:</span><br><span>60%</span></div>
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 0.85rem; padding-top: 10px; border-top: 1px solid #1e293b;">
                        <div>
                            <span style="color: #22c55e;">Pros:</span>
                            <ul style="margin: 5px 0 0 0; padding-left: 18px; color: #94a3b8;">
                                <li>Guaranteed immediate cash</li>
                                <li>Firm handles the selling</li>
                                <li>No ongoing obligations</li>
                            </ul>
                        </div>
                        <div>
                            <span style="color: #ef4444;">Cons:</span>
                            <ul style="margin: 5px 0 0 0; padding-left: 18px; color: #94a3b8;">
                                <li>Firm takes 7% cut</li>
                                <li>Requires Firm to have cash</li>
                                <li>Higher min valuation</li>
                            </ul>
                        </div>
                    </div>
                    <div style="font-size: 0.8rem; color: #64748b; margin-top: 10px;">Min valuation: $50,000</div>
                    <button type="button" class="btn-blue select-ipo-btn" style="width: 100%; margin-top: 15px;">Select Underwritten IPO</button>
                </div>

                <!-- Option 3: Income Shares IPO -->
                <div class="card ipo-option" data-ipo-type="income_shares" style="cursor: pointer; border: 2px solid #1e293b; transition: border-color 0.2s; {'opacity: 0.5; pointer-events: none;' if not firm.is_accepting_ipos else ''}">
                    <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 8px;">
                        <h4 style="margin: 0; color: #f59e0b;">Income Shares IPO</h4>
                        <span style="background: #451a03; color: #fbbf24; padding: 3px 10px; border-radius: 4px; font-size: 0.75rem;">3% TO FIRM + DIVIDENDS</span>
                    </div>
                    <p style="color: #94a3b8; font-size: 0.9rem; line-height: 1.6; margin-bottom: 15px;">
                        {income_config['description']}
                    </p>
                    <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; font-size: 0.85rem; margin-bottom: 15px;">
                        <div><span style="color: #64748b;">Cost:</span><br><span style="color: #22c55e;">Only 3% discount</span></div>
                        <div><span style="color: #64748b;">Capital:</span><br><span style="color: #22c55e;">Guaranteed</span></div>
                        <div><span style="color: #64748b;">Dividends:</span><br><span style="color: #ef4444;">10%/year (mandatory)</span></div>
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 0.85rem; padding-top: 10px; border-top: 1px solid #1e293b;">
                        <div>
                            <span style="color: #22c55e;">Pros:</span>
                            <ul style="margin: 5px 0 0 0; padding-left: 18px; color: #94a3b8;">
                                <li>Best upfront price (only 3%)</li>
                                <li>Guaranteed immediate cash</li>
                                <li>Attracts more investors</li>
                            </ul>
                        </div>
                        <div>
                            <span style="color: #ef4444;">Cons:</span>
                            <ul style="margin: 5px 0 0 0; padding-left: 18px; color: #94a3b8;">
                                <li>Must pay dividends every quarter</li>
                                <li>Missing payments hurts credit</li>
                                <li>Ongoing cash drain</li>
                            </ul>
                        </div>
                    </div>
                    <div style="font-size: 0.8rem; color: #64748b; margin-top: 10px;">Min valuation: $75,000 &bull; Max float: 40%</div>
                    <button type="button" class="btn-blue select-ipo-btn" style="width: 100%; margin-top: 15px; background: #92400e; border-color: #f59e0b;">Select Income Shares IPO</button>
                </div>
            </div>
        </div>

        <!-- IPO Configuration Form (hidden until type selected) -->
        <div id="ipo-form-section" style="display: none;">
            <div class="card">
                <h3>Configure Your IPO</h3>
                <form action="/api/brokerage/create-player-ipo" method="post">
                    <input type="hidden" name="ipo_type" id="selected-ipo-type" value="">

                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                        <div>
                            <div style="margin-bottom: 15px;">
                                <label style="display: block; margin-bottom: 5px; color: #94a3b8;">Company Name</label>
                                <input type="text" name="company_name" required
                                       style="width: 100%; padding: 10px;"
                                       placeholder="e.g., {player.business_name} Corporation"
                                       value="{player.business_name} Co.">
                            </div>

                            <div style="margin-bottom: 15px;">
                                <label style="display: block; margin-bottom: 5px; color: #94a3b8;">Ticker Symbol (3-5 chars)</label>
                                <input type="text" name="ticker_symbol" required maxlength="5" minlength="3"
                                       style="width: 100%; padding: 10px; text-transform: uppercase;"
                                       placeholder="e.g., {player.business_name[:4].upper()}">
                                <p style="font-size: 0.8rem; color: #64748b; margin-top: 5px;">This will appear on WPE ticker</p>
                            </div>
                        </div>

                        <div>
                            <div style="margin-bottom: 15px;">
                                <label style="display: block; margin-bottom: 5px; color: #94a3b8;">Total Shares to Issue</label>
                                <input type="number" name="total_shares" required min="10000"
                                       value="{valuation['suggested_ipo_shares']}"
                                       style="width: 100%; padding: 10px;">
                                <p style="font-size: 0.8rem; color: #64748b; margin-top: 5px;">
                                    Suggested: {valuation['suggested_ipo_shares']:,} shares
                                </p>
                            </div>

                            <div style="margin-bottom: 15px;">
                                <label style="display: block; margin-bottom: 5px; color: #94a3b8;">Shares to Offer (% of total)</label>
                                <input type="number" name="offer_percentage" required min="10" max="100" value="25"
                                       style="width: 100%; padding: 10px;">
                                <p style="font-size: 0.8rem; color: #64748b; margin-top: 5px;">
                                    You keep the rest. Most IPOs offer 20-40%.
                                </p>
                            </div>
                        </div>
                    </div>

                    <button type="submit" class="btn-blue" style="width: 100%; padding: 15px; margin-top: 20px; font-size: 1.1rem;">
                        Launch IPO
                    </button>
                </form>
            </div>
        </div>

        <script>
            document.querySelectorAll('.select-ipo-btn').forEach(btn => {{
                btn.addEventListener('click', function(e) {{
                    e.stopPropagation();
                    const card = this.closest('.ipo-option');
                    const ipoType = card.dataset.ipoType;

                    document.querySelectorAll('.ipo-option').forEach(c => {{
                        c.style.borderColor = '#1e293b';
                    }});
                    card.style.borderColor = '#38bdf8';

                    document.getElementById('selected-ipo-type').value = ipoType;
                    document.getElementById('ipo-form-section').style.display = 'block';
                    document.getElementById('ipo-form-section').scrollIntoView({{ behavior: 'smooth' }});
                }});
            }});
        </script>
        '''

        return shell("IPO Center", body, player.cash_balance, player.id)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return shell("IPO Center", f"Error: {e}", player.cash_balance, player.id)
# NEW IPO CREATION ENDPOINT
# Add this to ux.py after the existing IPO page

@router.post("/api/brokerage/create-player-ipo")
async def create_player_ipo_endpoint(
    company_name: str = Form(...),
    ticker_symbol: str = Form(...),
    ipo_type: str = Form(...),
    total_shares: int = Form(...),
    offer_percentage: int = Form(...),
    session_token: Optional[str] = Cookie(None)
):
    """
    Create a player holding company IPO.
    
    This replaces the old per-business IPO system with a proper
    holding company structure where players IPO their entire empire.
    """
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    
    try:
        from banks.brokerage_firm import (
            create_player_ipo, IPOType, get_db as get_firm_db
        )
        
        # Validate ticker symbol
        ticker_symbol = ticker_symbol.upper().strip()
        if len(ticker_symbol) < 3 or len(ticker_symbol) > 5:
            return RedirectResponse(
                url="/brokerage/ipo?error=invalid_ticker",
                status_code=303
            )
        
        # Validate shares
        if total_shares < 10000:
            return RedirectResponse(
                url="/brokerage/ipo?error=insufficient_shares",
                status_code=303
            )
        
        # Calculate shares to offer
        shares_to_offer = int((offer_percentage / 100) * total_shares)
        
        if shares_to_offer < 1:
            return RedirectResponse(
                url="/brokerage/ipo?error=must_offer_shares",
                status_code=303
            )
        
        # Convert IPO type string to enum
        try:
            ipo_type_enum = IPOType(ipo_type)
        except ValueError:
            return RedirectResponse(
                url="/brokerage/ipo?error=invalid_ipo_type",
                status_code=303
            )
        
        # Create the IPO
        company, error_msg = create_player_ipo(
            founder_id=player.id,
            company_name=company_name,
            ticker_symbol=ticker_symbol,
            ipo_type=ipo_type_enum,
            shares_to_offer=shares_to_offer,
            total_shares=total_shares,
            share_class="A",  # Default to Class A
            dividend_config=None  # Will add dividend config in phase 2
        )

        if not company:
            from urllib.parse import quote
            return RedirectResponse(
                url=f"/brokerage/ipo?error={quote(error_msg or 'IPO creation failed.')}",
                status_code=303
            )
        
        # Success! Redirect to trading page for their new stock
        return RedirectResponse(
            url=f"/brokerage/trading?ticker={ticker_symbol}&success=ipo_created",
            status_code=303
        )
    
    except Exception as e:
        print(f"[UX] IPO creation error: {e}")
        import traceback
        traceback.print_exc()
        return RedirectResponse(
            url="/brokerage/ipo?error=exception",
            status_code=303
        )

@router.post("/api/brokerage/go-private")
async def go_private_endpoint(
    company_id: int = Form(...),
    session_token: Optional[str] = Cookie(None)
):
    """Delist a company and take it private."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player

    try:
        from banks.brokerage_firm import delist_company
        success, error_msg = delist_company(player.id, company_id)

        if success:
            return RedirectResponse(
                url="/brokerage/ipo?error=Company+successfully+taken+private.+You+can+launch+a+new+IPO+after+the+30-day+cooldown.",
                status_code=303
            )
        else:
            from urllib.parse import quote
            return RedirectResponse(
                url=f"/brokerage/ipo?error={quote(error_msg or 'Failed to go private.')}",
                status_code=303
            )
    except Exception as e:
        print(f"[UX] Go private error: {e}")
        import traceback
        traceback.print_exc()
        from urllib.parse import quote
        return RedirectResponse(
            url=f"/brokerage/ipo?error={quote(str(e))}",
            status_code=303
        )


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

        # Pre-build short info to avoid nested f-string syntax issues
        short_info_html = ""
        if selected_company:
            short_info_html = f'''
                <div style="margin-top: 15px; padding: 15px; background: #0f172a; border-radius: 4px;">
                    <p><strong>Selected:</strong> {selected_company.ticker_symbol} @ ${selected_company.current_price:.4f}</p>
                    <p><strong>Available to borrow:</strong> {available_to_short:,} shares</p>
                    <p><strong>Collateral requirement:</strong> {SHORT_COLLATERAL_REQUIREMENT*100:.0f}% (${selected_company.current_price * SHORT_COLLATERAL_REQUIREMENT:.4f}/share)</p>
                    <p style="color: #f59e0b; font-size: 0.9rem; margin-top: 10px;">
                        Short selling is risky. If the price rises, your losses are theoretically unlimited.
                    </p>
                </div>'''

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
                
                {short_info_html}
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
    """WCE Commodity lending page."""
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

                # Pre-build borrow form to avoid nested f-string issues
                borrow_action_html = "-"
                if not is_own:
                    borrow_action_html = f'''
                        <form action="/api/brokerage/borrow-commodity" method="post" style="display: flex; gap: 5px;">
                            <input type="hidden" name="listing_id" value="{listing.id}">
                            <input type="number" name="quantity" min="1" max="{available}" placeholder="Qty" style="width: 80px; padding: 4px;">
                            <button type="submit" class="btn-blue" style="padding: 4px 8px; font-size: 0.8rem;">Borrow</button>
                        </form>'''

                listings_html += f'''
                <tr style="border-bottom: 1px solid #1e293b;">
                    <td style="padding: 10px 8px;"><strong>{listing.item_type.replace("_", " ").title()}</strong></td>
                    <td style="padding: 10px 8px;">{available:,.0f}</td>
                    <td style="padding: 10px 8px;">{listing.weekly_rate*100:.1f}%</td>
                    <td style="padding: 10px 8px;">{"YOU" if is_own else f"Player {listing.lender_player_id}"}</td>
                    <td style="padding: 10px 8px;">
                        {borrow_action_html}
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
        <h1>WCE Commodity Exchange</h1>
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
        
        return shell("WCE Commodities", body, player.cash_balance, player.id)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return shell("WCE Commodities", f"Error: {e}", player.cash_balance, player.id)


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
        for tier, (min_score, max_score, rate, leverage, _) in CREDIT_TIERS.items():
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
            liens_html = '<p style="color: #22c55e;">No active liens. Your account is in good standing.</p>'

        # Pre-build lien debt info to avoid nested f-string syntax issues
        lien_debt_info_html = ""
        if total_lien_debt > 0:
            lien_debt_info_html = f'''
            <div style="margin-top: 15px; padding: 15px; background: #450a0a; border-radius: 4px; border: 1px solid #7f1d1d;">
                <p style="color: #fca5a5;">
                    <strong>Total Lien Debt: ${total_lien_debt:,.2f}</strong><br>
                    The Firm automatically garnishes 50% of your cash every 60 seconds to pay down liens.
                    Interest accrues at {interest_rate*100:.0f}% annually.
                </p>
            </div>'''

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
            {lien_debt_info_html}
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

"""
PRODUCTION COSTS UX ROUTES
Add these routes to ux.py

Copy everything below into your ux.py file.
"""

# ==========================
# PRODUCTION COSTS PAGES
# ==========================

@router.get("/stats/production-costs", response_class=HTMLResponse)
def production_costs_page(
    session_token: Optional[str] = Cookie(None),
    category: str = "all",
    sort: str = "cost",
    order: str = "asc",
    search: str = ""
):
    """Interactive production cost explorer."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    
    try:
        from production_costs import get_calculator
        
        calc = get_calculator()
        summary = calc.get_summary()
        categories = calc.get_categories()
        
        # Get items based on filters
        if search:
            items = calc.search_items(search)
        elif category != "all":
            by_cat = calc.get_by_category()
            items = by_cat.get(category, [])
        else:
            items = calc.get_all_items_sorted(sort_by=sort, ascending=(order == "asc"))
        
        # Category filter tabs
        cat_colors = {
            "seeds": "#22c55e", "fruits": "#84cc16", "vegetables": "#16a34a",
            "crops": "#eab308", "food": "#f97316", "prepared_food": "#fb923c",
            "beverage": "#06b6d4", "alcohol": "#a855f7", "ingredients": "#ec4899",
            "livestock": "#92400e", "feed": "#a3e635", "health": "#ef4444",
            "personal_care": "#f472b6", "industrial": "#64748b", "materials": "#78716c",
            "textiles": "#c084fc", "wood": "#a16207", "ore": "#71717a",
            "metals": "#94a3b8", "components": "#6366f1", "auto_parts": "#3b82f6",
            "marine_parts": "#0ea5e9", "vehicle": "#2563eb", "apparel": "#d946ef",
            "accessories": "#e879f9", "home_goods": "#14b8a6", "packaging": "#737373",
            "media": "#facc15", "liquids": "#38bdf8", "energy": "#f59e0b",
            "financial": "#10b981", "luxury": "#d4af37", "minerals": "#a8a29e",
            "utilities": "#0891b2", "fuel": "#dc2626", "unknown": "#64748b"
        }
        
        # Build category tabs
        cat_tabs = f'''
        <a href="/stats/production-costs?category=all&sort={sort}&order={order}" 
           style="padding: 6px 12px; margin-right: 8px; border-radius: 4px; text-decoration: none;
                  background: {'#38bdf8' if category == 'all' else '#1e293b'}; 
                  color: {'#020617' if category == 'all' else '#94a3b8'};">
            All ({summary['total_items']})
        </a>'''
        
        for cat in categories:
            cat_count = len(calc.get_by_category().get(cat, []))
            color = cat_colors.get(cat, "#64748b")
            is_selected = category == cat
            cat_tabs += f'''
            <a href="/stats/production-costs?category={cat}&sort={sort}&order={order}" 
               style="padding: 6px 12px; margin-right: 8px; margin-bottom: 8px; border-radius: 4px; 
                      text-decoration: none; display: inline-block;
                      background: {color if is_selected else '#1e293b'}; 
                      color: {'#020617' if is_selected else color};">
                {cat.replace('_', ' ').title()} ({cat_count})
            </a>'''
        
        # Build items table
        items_html = ""
        if items:
            # Sort controls
            sort_indicator = "▲" if order == "asc" else "▼"
            next_order = "desc" if order == "asc" else "asc"
            
            items_html = f'''
            <table style="width: 100%; border-collapse: collapse; font-size: 0.9rem;">
                <thead>
                    <tr style="border-bottom: 2px solid #1e293b; text-align: left;">
                        <th style="padding: 12px 8px;">
                            <a href="/stats/production-costs?category={category}&sort=name&order={next_order if sort == 'name' else 'asc'}&search={search}" 
                               style="color: #94a3b8; text-decoration: none;">
                                Item {'↕' if sort != 'name' else sort_indicator}
                            </a>
                        </th>
                        <th style="padding: 12px 8px;">Category</th>
                        <th style="padding: 12px 8px; text-align: right;">
                            <a href="/stats/production-costs?category={category}&sort=cost&order={next_order if sort == 'cost' else 'asc'}&search={search}" 
                               style="color: #94a3b8; text-decoration: none;">
                                Cost {'↕' if sort != 'cost' else sort_indicator}
                            </a>
                        </th>
                        <th style="padding: 12px 8px;">Producer</th>
                        <th style="padding: 12px 8px; text-align: center;">Details</th>
                    </tr>
                </thead>
                <tbody>'''
            
            for item in items:
                cat_color = cat_colors.get(item.get('category', 'unknown'), '#64748b')
                cost_color = "#22c55e" if item['cost'] < 1 else "#38bdf8" if item['cost'] < 100 else "#f59e0b" if item['cost'] < 1000 else "#ef4444"
                
                items_html += f'''
                <tr style="border-bottom: 1px solid #1e293b; cursor: pointer;" 
                    onclick="window.location='/stats/production-costs/{item['item_key']}'">
                    <td style="padding: 12px 8px;">
                        <strong>{item['name']}</strong><br>
                        <span style="color: #64748b; font-size: 0.8rem;">{item['item_key']}</span>
                    </td>
                    <td style="padding: 12px 8px;">
                        <span style="padding: 2px 8px; border-radius: 4px; font-size: 0.75rem;
                                     background: {cat_color}20; color: {cat_color};">
                            {item.get('category', 'unknown').replace('_', ' ').upper()}
                        </span>
                    </td>
                    <td style="padding: 12px 8px; text-align: right; font-family: monospace; color: {cost_color};">
                        ${item['cost']:,.4f}
                    </td>
                    <td style="padding: 12px 8px; color: #64748b; font-size: 0.85rem;">
                        {item.get('business', '-') or '<span style="color: #ef4444;">No recipe</span>'}
                    </td>
                    <td style="padding: 12px 8px; text-align: center;">
                        <a href="/stats/production-costs/{item['item_key']}" class="btn-blue" 
                           style="padding: 4px 12px; font-size: 0.8rem;">View</a>
                    </td>
                </tr>'''
            
            items_html += '</tbody></table>'
        else:
            items_html = '<p style="color: #64748b; text-align: center; padding: 40px;">No items found.</p>'
        
        body = f'''
        <a href="/stats" style="color: #38bdf8;">← Stats Dashboard</a>
        <h1>📊 Production Cost Explorer</h1>
        <p style="color: #64748b;">Base production costs assuming full vertical integration (you produce all inputs yourself).</p>
        
        <!-- Summary Cards -->
        <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 15px; margin: 20px 0;">
            <div class="card" style="text-align: center; padding: 15px;">
                <div style="font-size: 0.8rem; color: #64748b;">TOTAL ITEMS</div>
                <div style="font-size: 1.8rem; font-weight: bold; color: #38bdf8;">{summary['total_items']}</div>
            </div>
            <div class="card" style="text-align: center; padding: 15px;">
                <div style="font-size: 0.8rem; color: #64748b;">CHEAPEST</div>
                <div style="font-size: 1.8rem; font-weight: bold; color: #22c55e;">${summary['min_cost']:.4f}</div>
            </div>
            <div class="card" style="text-align: center; padding: 15px;">
                <div style="font-size: 0.8rem; color: #64748b;">MEDIAN</div>
                <div style="font-size: 1.8rem; font-weight: bold; color: #f59e0b;">${summary['median_cost']:.2f}</div>
            </div>
            <div class="card" style="text-align: center; padding: 15px;">
                <div style="font-size: 0.8rem; color: #64748b;">MOST EXPENSIVE</div>
                <div style="font-size: 1.8rem; font-weight: bold; color: #ef4444;">${summary['max_cost']:,.0f}</div>
            </div>
            <div class="card" style="text-align: center; padding: 15px;">
                <div style="font-size: 0.8rem; color: #64748b;">MISSING RECIPES</div>
                <div style="font-size: 1.8rem; font-weight: bold; color: #64748b;">{len(summary['missing_items'])}</div>
            </div>
        </div>
        
        <!-- Search -->
        <div class="card">
            <form action="/stats/production-costs" method="get" style="display: flex; gap: 10px;">
                <input type="hidden" name="category" value="{category}">
                <input type="hidden" name="sort" value="{sort}">
                <input type="hidden" name="order" value="{order}">
                <input type="text" name="search" value="{search}" placeholder="🔍 Search items..." 
                       style="flex: 1; padding: 12px; font-size: 1rem;">
                <button type="submit" class="btn-blue" style="padding: 12px 24px;">Search</button>
                {f'<a href="/stats/production-costs?category={category}&sort={sort}&order={order}" class="btn-orange" style="padding: 12px 24px;">Clear</a>' if search else ''}
            </form>
        </div>
        
        <!-- Category Filters -->
        <div class="card" style="margin-top: 15px;">
            <div style="display: flex; flex-wrap: wrap; gap: 8px;">
                {cat_tabs}
            </div>
        </div>
        
        <!-- Items Table -->
        <div class="card" style="margin-top: 15px; overflow-x: auto;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                <h3 style="margin: 0;">
                    {f'Search results for "{search}"' if search else f'{category.replace("_", " ").title()} Items' if category != 'all' else 'All Items'}
                    <span style="color: #64748b; font-weight: normal;">({len(items)} items)</span>
                </h3>
            </div>
            {items_html}
        </div>
        '''
        
        # Inject tutorial overlay for production-costs step
        try:
            from tutorial_ux import get_tutorial_overlay_html
            tut_overlay = get_tutorial_overlay_html(player, "production_costs")
            if tut_overlay:
                body = tut_overlay + body
        except Exception:
            pass

        return shell("Production Costs", body, player.cash_balance, player.id)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return shell("Production Costs", f"Error: {e}", player.cash_balance, player.id)


@router.get("/stats/production-costs/{item_key}", response_class=HTMLResponse)
def production_cost_detail_page(
    item_key: str,
    session_token: Optional[str] = Cookie(None)
):
    """Detailed cost breakdown for a specific item."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    
    try:
        from production_costs import get_calculator
        
        calc = get_calculator()
        breakdown = calc.get_cost_breakdown(item_key)
        
        if not breakdown:
            return shell("Not Found", f"<p>Item '{item_key}' not found.</p>", player.cash_balance, player.id)
        
        # Build inputs breakdown
        inputs_html = ""
        if breakdown['has_recipe'] and breakdown['inputs']:
            inputs_html = '''
            <div class="card">
                <h3>Input Costs Breakdown</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr style="border-bottom: 2px solid #1e293b;">
                            <th style="padding: 10px 8px; text-align: left;">Input</th>
                            <th style="padding: 10px 8px; text-align: right;">Quantity</th>
                            <th style="padding: 10px 8px; text-align: right;">Unit Cost</th>
                            <th style="padding: 10px 8px; text-align: right;">Total Cost</th>
                            <th style="padding: 10px 8px; text-align: right;">% of Batch</th>
                        </tr>
                    </thead>
                    <tbody>'''
            
            for inp in breakdown['inputs']:
                pct = (inp['total_cost'] / breakdown['batch_cost'] * 100) if breakdown['batch_cost'] > 0 else 0
                bar_width = min(pct, 100)
                
                inputs_html += f'''
                <tr style="border-bottom: 1px solid #1e293b;">
                    <td style="padding: 10px 8px;">
                        <a href="/stats/production-costs/{inp['item_key']}" style="color: #38bdf8;">
                            {inp['name']}
                        </a>
                    </td>
                    <td style="padding: 10px 8px; text-align: right; font-family: monospace;">{inp['quantity']:,.2f}</td>
                    <td style="padding: 10px 8px; text-align: right; font-family: monospace;">${inp['unit_cost']:,.4f}</td>
                    <td style="padding: 10px 8px; text-align: right; font-family: monospace; color: #f59e0b;">${inp['total_cost']:,.4f}</td>
                    <td style="padding: 10px 8px; text-align: right;">
                        <div style="display: flex; align-items: center; justify-content: flex-end; gap: 8px;">
                            <div style="width: 80px; height: 8px; background: #1e293b; border-radius: 4px; overflow: hidden;">
                                <div style="width: {bar_width}%; height: 100%; background: #38bdf8;"></div>
                            </div>
                            <span style="font-size: 0.85rem; color: #94a3b8;">{pct:.1f}%</span>
                        </div>
                    </td>
                </tr>'''
            
            # Add wage row
            wage_pct = breakdown['wage_pct']
            inputs_html += f'''
                <tr style="border-bottom: 1px solid #1e293b; background: #0f172a;">
                    <td style="padding: 10px 8px;"><strong>Labor (Wages)</strong></td>
                    <td style="padding: 10px 8px; text-align: right;">-</td>
                    <td style="padding: 10px 8px; text-align: right;">-</td>
                    <td style="padding: 10px 8px; text-align: right; font-family: monospace; color: #22c55e;">${breakdown['wage']:,.2f}</td>
                    <td style="padding: 10px 8px; text-align: right;">
                        <div style="display: flex; align-items: center; justify-content: flex-end; gap: 8px;">
                            <div style="width: 80px; height: 8px; background: #1e293b; border-radius: 4px; overflow: hidden;">
                                <div style="width: {min(wage_pct, 100)}%; height: 100%; background: #22c55e;"></div>
                            </div>
                            <span style="font-size: 0.85rem; color: #94a3b8;">{wage_pct:.1f}%</span>
                        </div>
                    </td>
                </tr>
                <tr style="background: #1e293b;">
                    <td style="padding: 10px 8px;" colspan="3"><strong>BATCH TOTAL</strong></td>
                    <td style="padding: 10px 8px; text-align: right; font-family: monospace; font-size: 1.1rem; color: #38bdf8;">
                        ${breakdown['batch_cost']:,.4f}
                    </td>
                    <td style="padding: 10px 8px; text-align: right; color: #64748b;">
                        ÷ {breakdown['output_qty']} = ${breakdown['cost']:,.4f}/unit
                    </td>
                </tr>
            </tbody></table>
            </div>'''
        elif not breakdown['has_recipe']:
            inputs_html = '''
            <div class="card" style="border-left: 4px solid #ef4444;">
                <h3 style="color: #ef4444;">⚠️ No Production Recipe</h3>
                <p style="color: #94a3b8;">This item cannot be produced. It may be a raw material that needs to be obtained through other means (mining, harvesting, etc.) or the recipe is missing from the configuration.</p>
            </div>'''
        
        # Find items that use this as an input
        used_by = []
        all_items = calc.get_all_items_sorted()
        for item in all_items:
            item_breakdown = calc.get_cost_breakdown(item['item_key'])
            if item_breakdown['has_recipe']:
                for inp in item_breakdown.get('inputs', []):
                    if inp['item_key'] == item_key:
                        used_by.append({
                            'item_key': item['item_key'],
                            'name': item['name'],
                            'cost': item['cost'],
                            'quantity_needed': inp['quantity']
                        })
                        break
        
        used_by_html = ""
        if used_by:
            used_by.sort(key=lambda x: x['cost'], reverse=True)
            used_by_html = '''
            <div class="card" style="margin-top: 15px;">
                <h3>Used In Production Of</h3>
                <div style="display: flex; flex-wrap: wrap; gap: 10px;">'''
            
            for item in used_by[:20]:
                used_by_html += f'''
                <a href="/stats/production-costs/{item['item_key']}" 
                   style="padding: 8px 12px; background: #1e293b; border-radius: 4px; text-decoration: none; color: #94a3b8;">
                    <strong style="color: #38bdf8;">{item['name']}</strong><br>
                    <span style="font-size: 0.8rem;">needs {item['quantity_needed']:,.1f}</span>
                </a>'''
            
            if len(used_by) > 20:
                used_by_html += f'<span style="padding: 8px 12px; color: #64748b;">+{len(used_by)-20} more...</span>'
            
            used_by_html += '</div></div>'

        # Pre-build production method HTML to avoid nested f-string syntax issues
        production_method_html = ""
        if breakdown['has_recipe']:
            production_method_html = f'''
        <div class="card" style="margin-top: 20px;">
            <h3>Production Method</h3>
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px;">
                <div>
                    <div style="font-size: 0.85rem; color: #64748b;">Producer</div>
                    <div style="font-size: 1.2rem;">{breakdown['business_name']}</div>
                </div>
                <div>
                    <div style="font-size: 0.85rem; color: #64748b;">Output per Batch</div>
                    <div style="font-size: 1.2rem;">{breakdown['output_qty']:,} units</div>
                </div>
                <div>
                    <div style="font-size: 0.85rem; color: #64748b;">Batch Cost</div>
                    <div style="font-size: 1.2rem; color: #f59e0b;">${breakdown['batch_cost']:,.4f}</div>
                </div>
                <div>
                    <div style="font-size: 0.85rem; color: #64748b;">Wages</div>
                    <div style="font-size: 1.2rem; color: #22c55e;">${breakdown['wage']:,.2f}</div>
                </div>
            </div>
        </div>'''

        body = f'''
        <a href="/stats/production-costs" style="color: #38bdf8;">← Production Costs</a>
        
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-top: 20px;">
            <div>
                <h1 style="margin: 0;">{breakdown['name']}</h1>
                <p style="color: #64748b; margin: 5px 0;">
                    {item_key} · {breakdown.get('category', 'unknown').replace('_', ' ').title()}
                </p>
            </div>
            <div style="text-align: right;">
                <div style="font-size: 3rem; font-weight: bold; color: #38bdf8;">
                    ${breakdown['cost']:,.4f}
                </div>
                <div style="color: #64748b;">per unit (vertical integration)</div>
            </div>
        </div>
        
        <!-- Production Info -->
        {production_method_html}
        
        {inputs_html}
        
        {used_by_html}
        '''
        
        return shell(f"Cost: {breakdown['name']}", body, player.cash_balance, player.id)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return shell("Production Costs", f"Error: {e}", player.cash_balance, player.id)


# ==========================
# JSON API ENDPOINT
# ==========================

@router.get("/api/production-costs")
async def api_production_costs(
    category: str = None,
    search: str = None,
    session_token: Optional[str] = Cookie(None)
):
    """JSON API for production costs."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return {"error": "Unauthorized"}
    
    try:
        from production_costs import get_calculator
        
        calc = get_calculator()
        
        if search:
            items = calc.search_items(search)
        elif category:
            by_cat = calc.get_by_category()
            items = by_cat.get(category, [])
        else:
            items = calc.get_all_items_sorted()
        
        return {
            "summary": calc.get_summary(),
            "items": items,
            "categories": calc.get_categories()
        }
    except Exception as e:
        return {"error": str(e)}


@router.get("/api/production-costs/{item_key}")
async def api_production_cost_detail(
    item_key: str,
    session_token: Optional[str] = Cookie(None)
):
    """JSON API for single item cost breakdown."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return {"error": "Unauthorized"}
    
    try:
        from production_costs import get_calculator
        
        calc = get_calculator()
        return calc.get_cost_breakdown(item_key)
    except Exception as e:
        return {"error": str(e)}

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

@router.post("/api/business/toggle-line")
async def toggle_line_endpoint(business_id: int = Form(...), line_index: int = Form(...), session_token: Optional[str] = Cookie(None)):
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return player
    from business import toggle_production_line
    toggle_production_line(player.id, business_id, line_index)
    return RedirectResponse(url="/businesses", status_code=303)

@router.post("/api/business/toggle-retail")
async def toggle_retail_endpoint(business_id: int = Form(...), item_type: str = Form(...), session_token: Optional[str] = Cookie(None)):
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return player
    from business import toggle_retail_item
    toggle_retail_item(player.id, business_id, item_type)
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
        
        result, error_msg = create_ipo(
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
        from urllib.parse import quote
        return RedirectResponse(url=f"/brokerage/ipo?error={quote(error_msg or 'IPO creation failed.')}", status_code=303)
        
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
        from banks.brokerage_firm import CompanyShares, get_db as get_firm_db
        from banks.brokerage_order_book import player_place_buy_order
        
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
        from banks.brokerage_firm import CompanyShares, get_db as get_firm_db
        from banks.brokerage_order_book import player_place_sell_order
        
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
        from banks.brokerage_order_book import cancel_order
        
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
    from banks.brokerage_order_book import get_order_book_depth
    return get_order_book_depth(company_shares_id, depth)


@router.get("/api/trading/trades/{company_shares_id}")
async def get_recent_trades_data(
    company_shares_id: int,
    limit: int = 20
):
    """Get recent fills (JSON)."""
    from banks.brokerage_order_book import get_recent_fills
    return {"trades": get_recent_fills(company_shares_id, limit)}


@router.get("/api/trading/orders/my")
async def get_my_open_orders(
    session_token: Optional[str] = Cookie(None)
):
    """Get current player's open orders (JSON)."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): return {"error": "Unauthorized"}
    
    try:
        from banks.brokerage_order_book import OrderBook, OrderStatus, get_db as get_book_db
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
