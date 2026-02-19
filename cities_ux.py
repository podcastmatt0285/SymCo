"""
cities_ux.py

UX module for the cities system.
Provides web interface and API endpoints for city management.
"""

from typing import Optional, List
from fastapi import APIRouter, Cookie, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse

router = APIRouter()

# ==========================
# HELPER: Get Player
# ==========================
def get_current_player(session_token: Optional[str]):
    """Get player from session token."""
    from auth import get_player_from_session, get_db
    db = get_db()
    player = get_player_from_session(db, session_token)
    db.close()
    return player


# ==========================
# STYLES
# ==========================
CITY_STYLES = """
<style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        background: #0b1220;
        color: #e5e7eb;
        min-height: 100vh;
        padding: 20px;
    }
    .container { max-width: 1200px; margin: 0 auto; }
    .header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 24px;
        padding-bottom: 16px;
        border-bottom: 1px solid #1e293b;
    }
    .header h1 { font-size: 24px; }
    .nav-link {
        color: #38bdf8;
        text-decoration: none;
        margin-left: 16px;
    }
    .nav-link:hover { text-decoration: underline; }
    
    .card {
        background: #020617;
        border: 1px solid #1e293b;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 16px;
    }
    .card h2 {
        font-size: 18px;
        margin-bottom: 12px;
        color: #38bdf8;
    }
    .card h3 {
        font-size: 16px;
        margin-bottom: 8px;
        color: #94a3b8;
    }
    
    .grid { display: grid; gap: 16px; }
    .grid-2 { grid-template-columns: repeat(2, 1fr); }
    .grid-3 { grid-template-columns: repeat(3, 1fr); }
    @media (max-width: 768px) {
        .grid-2, .grid-3 { grid-template-columns: 1fr; }
    }
    
    .stat {
        display: flex;
        justify-content: space-between;
        padding: 8px 0;
        border-bottom: 1px solid #1e293b;
    }
    .stat:last-child { border-bottom: none; }
    .stat-label { color: #94a3b8; }
    .stat-value { font-weight: 600; }
    .stat-value.positive { color: #4ade80; }
    .stat-value.negative { color: #f87171; }
    
    .btn {
        display: inline-block;
        padding: 10px 20px;
        border-radius: 8px;
        font-size: 14px;
        font-weight: 600;
        cursor: pointer;
        text-decoration: none;
        border: none;
        transition: all 0.2s;
    }
    .btn-primary {
        background: #38bdf8;
        color: #020617;
    }
    .btn-primary:hover { background: #0ea5e9; }
    .btn-secondary {
        background: #1e293b;
        color: #e5e7eb;
    }
    .btn-secondary:hover { background: #334155; }
    .btn-danger {
        background: #dc2626;
        color: #fff;
    }
    .btn-danger:hover { background: #b91c1c; }
    .btn-sm { padding: 6px 12px; font-size: 12px; }
    
    .form-group { margin-bottom: 16px; }
    .form-group label {
        display: block;
        margin-bottom: 6px;
        color: #94a3b8;
        font-size: 14px;
    }
    .form-group input, .form-group select {
        width: 100%;
        padding: 10px 12px;
        background: #0b1220;
        border: 1px solid #1e293b;
        border-radius: 6px;
        color: #e5e7eb;
        font-size: 14px;
    }
    .form-group input:focus, .form-group select:focus {
        outline: none;
        border-color: #38bdf8;
    }
    
    .table {
        width: 100%;
        border-collapse: collapse;
    }
    .table th, .table td {
        padding: 12px;
        text-align: left;
        border-bottom: 1px solid #1e293b;
    }
    .table th {
        color: #94a3b8;
        font-weight: 500;
        font-size: 13px;
    }
    .table tr:hover { background: #0b1220; }
    
    .badge {
        display: inline-block;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: 600;
    }
    .badge-success { background: #166534; color: #4ade80; }
    .badge-warning { background: #854d0e; color: #fbbf24; }
    .badge-info { background: #1e40af; color: #60a5fa; }
    .badge-danger { background: #991b1b; color: #fca5a5; }
    
    .alert {
        padding: 12px 16px;
        border-radius: 8px;
        margin-bottom: 16px;
    }
    .alert-success { background: #166534; border: 1px solid #22c55e; }
    .alert-error { background: #991b1b; border: 1px solid #ef4444; }
    .alert-info { background: #1e40af; border: 1px solid #3b82f6; }
    
    .poll-card {
        background: #0b1220;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
    }
    .poll-header {
        display: flex;
        justify-content: space-between;
        margin-bottom: 12px;
    }
    .poll-votes {
        display: flex;
        gap: 16px;
        margin-top: 12px;
    }
    .vote-btn {
        flex: 1;
        padding: 10px;
        border-radius: 6px;
        cursor: pointer;
        text-align: center;
        font-weight: 600;
    }
    .vote-yes { background: #166534; color: #4ade80; border: 1px solid #22c55e; }
    .vote-yes:hover { background: #15803d; }
    .vote-no { background: #991b1b; color: #fca5a5; border: 1px solid #ef4444; }
    .vote-no:hover { background: #b91c1c; }
    
    .member-list {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
    }
    .member-chip {
        background: #1e293b;
        padding: 6px 12px;
        border-radius: 16px;
        font-size: 13px;
    }
    .member-chip.mayor {
        background: #854d0e;
        color: #fbbf24;
    }
    
    .progress-bar {
        height: 8px;
        background: #1e293b;
        border-radius: 4px;
        overflow: hidden;
    }
    .progress-fill {
        height: 100%;
        background: #38bdf8;
        transition: width 0.3s;
    }
</style>
"""


# ==========================
# HELPERS
# ==========================
def _currency_select_options() -> str:
    """Build a <select> dropdown of all tradeable item types for currency selection."""
    try:
        import inventory
        items = sorted(inventory.ITEM_RECIPES.keys())
    except Exception:
        items = []
    options = '\n'.join(f'<option value="{item}">{item.replace("_", " ").title()}</option>' for item in items)
    return f'<select name="currency" required style="width:100%;padding:10px 12px;background:#0b1220;border:1px solid #1e293b;border-radius:6px;color:#e5e7eb;font-size:14px;">\n<option value="">-- Select Currency --</option>\n{options}\n</select>'


# ==========================
# CITIES LIST
# ==========================
@router.get("/cities", response_class=HTMLResponse)
async def cities_list(session_token: Optional[str] = Cookie(None), msg: Optional[str] = Query(None)):
    """View all cities."""
    player = get_current_player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)
    
    from cities import get_all_cities, get_player_city, get_player_total_value
    from auth import Player, get_db
    
    cities = get_all_cities()
    player_city = get_player_city(player.id)
    
    # Build cities table
    cities_html = ""
    if cities:
        cities_html = """
        <table class="table">
            <thead>
                <tr>
                    <th>City</th>
                    <th>Mayor</th>
                    <th>Members</th>
                    <th>Currency</th>
                    <th>Bank Reserves</th>
                    <th>Action</th>
                </tr>
            </thead>
            <tbody>
        """
        
        db = get_db()
        for city in cities:
            mayor = db.query(Player).filter(Player.id == city['mayor_id']).first()
            mayor_name = mayor.business_name if mayor else f"Player {city['mayor_id']}"
            
            action = ""
            if player_city and player_city.id == city['id']:
                action = '<a href="/city/my" class="btn btn-primary btn-sm">View My City</a>'
            elif not player_city:
                action = f'<a href="/city/{city["id"]}" class="btn btn-secondary btn-sm">View</a>'
            else:
                action = f'<a href="/city/{city["id"]}" class="btn btn-secondary btn-sm">View</a>'
            
            cities_html += f"""
                <tr>
                    <td><strong>{city['name']}</strong></td>
                    <td>{mayor_name}</td>
                    <td>{city['member_count']}/25</td>
                    <td>{city['currency_type'] or 'Not set'}</td>
                    <td>${city['bank_reserves']:,.2f}</td>
                    <td>{action}</td>
                </tr>
            """
        db.close()
        cities_html += "</tbody></table>"
    else:
        cities_html = '<p style="color: #94a3b8;">No cities exist yet. Be the first to create one!</p>'
    
    # Alert message
    alert_html = ""
    if msg:
        alert_html = f'<div class="alert alert-info">{msg}</div>'
    
    # Create city section (only if not in a city)
    create_section = ""
    if not player_city:
        from districts import District, get_db as get_districts_db
        ddb = get_districts_db()
        player_districts = ddb.query(District).filter(District.owner_id == player.id).all()
        ddb.close()
        
        district_options = "".join(
            f'<option value="{d.id}">{d.district_type.title()} District #{d.id}</option>'
            for d in player_districts if d.occupied_by_business_id is None
        )
        
        can_create = len([d for d in player_districts if d.occupied_by_business_id is None]) >= 10
        create_disabled = "" if can_create and player.cash_balance >= 10000000 else "disabled"
        
        create_section = f"""
        <div class="card">
            <h2>🏙️ Create a City</h2>
            <p style="color: #94a3b8; margin-bottom: 16px;">
                Sacrifice 10 districts and $10,000,000 to create your own city and become its Mayor.
            </p>
            <p style="margin-bottom: 16px;">
                <strong>Your vacant districts:</strong> {len([d for d in player_districts if d.occupied_by_business_id is None])}/10 required<br>
                <strong>Your cash:</strong> ${player.cash_balance:,.2f} ($10,000,000 required)
            </p>
            <form action="/api/city/create" method="post">
                <div class="form-group">
                    <label>City Name</label>
                    <input type="text" name="city_name" required placeholder="New City Name">
                </div>
                <div class="form-group">
                    <label>Select 10 Districts to Sacrifice</label>
                    <select name="district_ids" multiple size="6" required style="height: auto;">
                        {district_options}
                    </select>
                    <small style="color: #64748b;">Hold Ctrl/Cmd to select multiple</small>
                </div>
                <button type="submit" class="btn btn-primary" {create_disabled}>Create City ($10M)</button>
            </form>
        </div>
        """
    else:
        create_section = f"""
        <div class="card">
            <h2>🏙️ Your City: {player_city.name}</h2>
            <p style="color: #94a3b8;">You are a member of <strong>{player_city.name}</strong>.</p>
            <a href="/city/my" class="btn btn-primary" style="margin-top: 12px;">View My City</a>
        </div>
        """
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Cities · Wadsworth</title>
        {CITY_STYLES}
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🏙️ Cities</h1>
                <div>
                    <span style="color: #94a3b8;">{player.business_name}</span>
                    <a href="/counties" class="nav-link">Counties</a>
                    <a href="/" class="nav-link">Dashboard</a>
                </div>
            </div>
            
            {alert_html}
            
            {create_section}
            
            <div class="card">
                <h2>All Cities</h2>
                {cities_html}
            </div>
        </div>
    </body>
    </html>
    """


# ==========================
# MY CITY (REDIRECT) - Must be before /city/{city_id}
# ==========================
@router.get("/city/my", response_class=HTMLResponse)
async def my_city(session_token: Optional[str] = Cookie(None)):
    """Redirect to player's city."""
    player = get_current_player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)
    
    from cities import get_player_city
    city = get_player_city(player.id)
    
    if not city:
        return RedirectResponse(url="/cities?msg=You+are+not+in+a+city", status_code=303)
    
    return RedirectResponse(url=f"/city/{city.id}", status_code=303)


# ==========================
# VIEW APPLICANT PROFILE - Must be before /city/{city_id}
# ==========================
@router.get("/city/{city_id}/applicant/{applicant_id}", response_class=HTMLResponse)
async def view_applicant_profile(city_id: int, applicant_id: int, session_token: Optional[str] = Cookie(None)):
    """View detailed profile of a city applicant. Only accessible by city members."""
    player = get_current_player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)
    
    from cities import is_city_member, get_city_by_id, get_player_total_value, CityApplication
    from auth import Player, get_db
    from business import Business, BUSINESS_TYPES
    from land import LandPlot
    from districts import District
    from market import Trade
    import inventory
    import market
    
    # Verify viewer is a city member
    if not is_city_member(player.id, city_id):
        return RedirectResponse(url=f"/city/{city_id}?msg=Members+only", status_code=303)
    
    city = get_city_by_id(city_id)
    if not city:
        return RedirectResponse(url="/cities?msg=City+not+found", status_code=303)
    
    db = get_db()
    
    # Get applicant info
    applicant = db.query(Player).filter(Player.id == applicant_id).first()
    if not applicant:
        db.close()
        return RedirectResponse(url=f"/city/{city_id}?msg=Applicant+not+found", status_code=303)
    
    # Get pending application
    application = db.query(CityApplication).filter(
        CityApplication.city_id == city_id,
        CityApplication.applicant_id == applicant_id,
        CityApplication.status == "pending"
    ).first()
    
    if not application:
        db.close()
        return RedirectResponse(url=f"/city/{city_id}?msg=No+pending+application", status_code=303)
    
    # Calculate total value
    total_value = get_player_total_value(applicant_id)
    
    # Get businesses
    businesses = db.query(Business).filter(Business.owner_id == applicant_id).all()
    businesses_html = ""
    if businesses:
        businesses_html = "<table class='table'><thead><tr><th>Type</th><th>Status</th><th>Location</th></tr></thead><tbody>"
        for biz in businesses:
            config = BUSINESS_TYPES.get(biz.business_type, {})
            biz_name = config.get("name", biz.business_type)
            status = "Active" if biz.is_active else "Paused"
            location = f"Plot #{biz.land_plot_id}" if biz.land_plot_id else f"District #{biz.district_id}"
            businesses_html += f"<tr><td>{biz_name}</td><td>{status}</td><td>{location}</td></tr>"
        businesses_html += "</tbody></table>"
    else:
        businesses_html = "<p style='color: #64748b;'>No businesses</p>"
    
    # Get land plots
    plots = db.query(LandPlot).filter(LandPlot.owner_id == applicant_id).all()
    land_html = ""
    if plots:
        land_html = "<table class='table'><thead><tr><th>Plot</th><th>Terrain</th><th>Efficiency</th><th>Status</th></tr></thead><tbody>"
        for plot in plots:
            status = "Occupied" if plot.occupied_by_business_id else "Vacant"
            land_html += f"<tr><td>#{plot.id}</td><td>{plot.terrain_type}</td><td>{plot.efficiency:.0f}%</td><td>{status}</td></tr>"
        land_html += "</tbody></table>"
    else:
        land_html = "<p style='color: #64748b;'>No land plots</p>"
    
    # Get districts
    districts = db.query(District).filter(District.owner_id == applicant_id).all()
    districts_html = ""
    if districts:
        districts_html = "<table class='table'><thead><tr><th>District</th><th>Type</th><th>Size</th><th>Status</th></tr></thead><tbody>"
        for dist in districts:
            status = "Occupied" if dist.occupied_by_business_id else "Vacant"
            districts_html += f"<tr><td>#{dist.id}</td><td>{dist.district_type}</td><td>{dist.size:.0f}</td><td>{status}</td></tr>"
        districts_html += "</tbody></table>"
    else:
        districts_html = "<p style='color: #64748b;'>No districts</p>"
    
    # Get inventory summary (top 10 by value)
    player_inv = inventory.get_player_inventory(applicant_id)
    inv_items = []
    for item_type, qty in player_inv.items():
        if qty > 0:
            price = market.get_market_price(item_type) or 1.0
            value = qty * price
            inv_items.append((item_type, qty, price, value))
    inv_items.sort(key=lambda x: x[3], reverse=True)
    
    inventory_html = ""
    if inv_items:
        inventory_html = "<table class='table'><thead><tr><th>Item</th><th>Quantity</th><th>Market Price</th><th>Value</th></tr></thead><tbody>"
        for item_type, qty, price, value in inv_items[:15]:
            inventory_html += f"<tr><td>{item_type}</td><td>{qty:,.2f}</td><td>${price:,.2f}</td><td>${value:,.2f}</td></tr>"
        if len(inv_items) > 15:
            inventory_html += f"<tr><td colspan='4' style='color:#64748b;'>...and {len(inv_items) - 15} more items</td></tr>"
        inventory_html += "</tbody></table>"
    else:
        inventory_html = "<p style='color: #64748b;'>No inventory</p>"
    
    # Get recent trades (last 20)
    recent_trades = db.query(Trade).filter(
        (Trade.buyer_id == applicant_id) | (Trade.seller_id == applicant_id)
    ).order_by(Trade.executed_at.desc()).limit(20).all()
    
    trades_html = ""
    if recent_trades:
        trades_html = "<table class='table'><thead><tr><th>Date</th><th>Type</th><th>Item</th><th>Qty</th><th>Price</th></tr></thead><tbody>"
        for trade in recent_trades:
            trade_type = "BUY" if trade.buyer_id == applicant_id else "SELL"
            type_color = "#4ade80" if trade_type == "SELL" else "#f87171"
            date_str = trade.executed_at.strftime("%m/%d %H:%M") if trade.executed_at else "?"
            trades_html += f"<tr><td>{date_str}</td><td style='color:{type_color};'>{trade_type}</td><td>{trade.item_type}</td><td>{trade.quantity:,.2f}</td><td>${trade.price:,.2f}</td></tr>"
        trades_html += "</tbody></table>"
    else:
        trades_html = "<p style='color: #64748b;'>No recent trades</p>"
    
    db.close()
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Applicant: {applicant.business_name} · Wadsworth</title>
        {CITY_STYLES}
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📋 Applicant Profile</h1>
                <div>
                    <a href="/city/{city_id}" class="nav-link">← Back to City</a>
                </div>
            </div>
            
            <div class="card">
                <h2>{applicant.business_name}</h2>
                <div class="grid grid-2" style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 16px;">
                    <div>
                        <div class="stat">
                            <span class="stat-label">Player ID</span>
                            <span class="stat-value">#{applicant_id}</span>
                        </div>
                        <div class="stat">
                            <span class="stat-label">Cash Balance</span>
                            <span class="stat-value positive">${applicant.cash_balance:,.2f}</span>
                        </div>
                        <div class="stat">
                            <span class="stat-label">Total Value</span>
                            <span class="stat-value">${total_value:,.2f}</span>
                        </div>
                    </div>
                    <div>
                        <div class="stat">
                            <span class="stat-label">Application Fee</span>
                            <span class="stat-value">${application.calculated_fee:,.2f}</span>
                        </div>
                        <div class="stat">
                            <span class="stat-label">Businesses</span>
                            <span class="stat-value">{len(businesses)}</span>
                        </div>
                        <div class="stat">
                            <span class="stat-label">Land Plots</span>
                            <span class="stat-value">{len(plots)}</span>
                        </div>
                        <div class="stat">
                            <span class="stat-label">Districts</span>
                            <span class="stat-value">{len(districts)}</span>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="card">
                <h2>🏭 Businesses ({len(businesses)})</h2>
                {businesses_html}
            </div>
            
            <div class="card">
                <h2>📦 Inventory (Top 15 by Value)</h2>
                {inventory_html}
            </div>
            
            <div class="card">
                <h2>🏞️ Land Plots ({len(plots)})</h2>
                {land_html}
            </div>
            
            <div class="card">
                <h2>🏛️ Districts ({len(districts)})</h2>
                {districts_html}
            </div>
            
            <div class="card">
                <h2>📈 Recent Trades</h2>
                {trades_html}
            </div>
            
            <div style="text-align: center; margin-top: 20px;">
                <a href="/city/{city_id}" class="btn btn-primary">← Back to City</a>
            </div>
        </div>
    </body>
    </html>
    """


# ==========================
# VIEW CITY DETAIL
# ==========================
@router.get("/city/{city_id}", response_class=HTMLResponse)
async def view_city(city_id: int, session_token: Optional[str] = Cookie(None)):
    """View a specific city's details."""
    player = get_current_player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)
    
    from cities import (
        get_city_by_id, get_city_stats, get_city_members, get_city_bank,
        is_city_member, is_mayor, get_player_total_value, CityPoll, CityApplication,
        PollStatus
    )
    from auth import Player, get_db
    
    city = get_city_by_id(city_id)
    if not city:
        return RedirectResponse(url="/cities?msg=City+not+found", status_code=303)
    
    stats = get_city_stats(city_id)
    members = get_city_members(city_id)
    bank = get_city_bank(city_id)
    
    is_member = is_city_member(player.id, city_id)
    is_city_mayor = is_mayor(player.id, city_id)
    
    db = get_db()
    
    # Get member names
    members_html = '<div class="member-list">'
    for m in members:
        p = db.query(Player).filter(Player.id == m.player_id).first()
        name = p.business_name if p else f"Player {m.player_id}"
        badge_class = "mayor" if m.is_mayor else ""
        prefix = "👑 " if m.is_mayor else ""
        members_html += f'<span class="member-chip {badge_class}">{prefix}{name}</span>'
    members_html += '</div>'
    
    # Active polls
    from cities import CityPoll, CityVote, PollType
    polls = db.query(CityPoll).filter(
        CityPoll.city_id == city_id,
        CityPoll.status == PollStatus.ACTIVE
    ).all()
    
    polls_html = ""
    if polls and is_member:
        polls_html = "<h3>Active Polls</h3>"
        for poll in polls:
            # Check if player has voted
            existing_vote = db.query(CityVote).filter(
                CityVote.poll_id == poll.id,
                CityVote.voter_id == player.id
            ).first()
            
            target_name = ""
            if poll.target_player_id:
                target = db.query(Player).filter(Player.id == poll.target_player_id).first()
                target_name = target.business_name if target else f"Player {poll.target_player_id}"
            
            poll_title = ""
            if poll.poll_type == PollType.APPLICATION:
                poll_title = f"Application: {target_name}"
            elif poll.poll_type == PollType.BANISHMENT:
                poll_title = f"Banishment: {target_name}"
            elif poll.poll_type == PollType.CURRENCY_CHANGE:
                poll_title = f"Currency Change: {poll.proposed_currency}"
            
            time_left = (poll.closes_at - db.query(Player).first().created_at).total_seconds()  # Hack for now
            
            vote_buttons = ""
            if existing_vote:
                vote_buttons = f'<span class="badge badge-info">You voted: {existing_vote.vote.upper()}</span>'
            else:
                vote_buttons = f"""
                <div class="poll-votes">
                    <form action="/api/city/vote" method="post" style="flex:1;">
                        <input type="hidden" name="poll_id" value="{poll.id}">
                        <input type="hidden" name="vote" value="yes">
                        <button type="submit" class="vote-btn vote-yes" style="width:100%;">✓ YES</button>
                    </form>
                    <form action="/api/city/vote" method="post" style="flex:1;">
                        <input type="hidden" name="poll_id" value="{poll.id}">
                        <input type="hidden" name="vote" value="no">
                        <button type="submit" class="vote-btn vote-no" style="width:100%;">✗ NO</button>
                    </form>
                </div>
                """
            
            # Add profile link for application polls
            profile_link = ""
            if poll.poll_type == PollType.APPLICATION and poll.target_player_id:
                profile_link = f'<a href="/city/{city_id}/applicant/{poll.target_player_id}" class="btn btn-secondary btn-sm" style="margin-left: 8px;">📋 View Profile</a>'
            
            polls_html += f"""
            <div class="poll-card">
                <div class="poll-header">
                    <strong>{poll_title}</strong>{profile_link}
                    <span class="badge badge-warning">Closes: {poll.closes_at.strftime('%Y-%m-%d %H:%M')}</span>
                </div>
                {vote_buttons}
            </div>
            """
    elif not polls and is_member:
        polls_html = '<p style="color: #64748b;">No active polls.</p>'
    
    # Application section (for non-members)
    apply_section = ""
    if not is_member:
        from cities import get_player_city
        player_city = get_player_city(player.id)
        
        if player_city:
            apply_section = '<p style="color: #94a3b8;">You are already a member of another city.</p>'
        elif len(members) >= 25:
            apply_section = '<p style="color: #94a3b8;">This city is at maximum capacity.</p>'
        else:
            # Check for pending application
            pending_app = db.query(CityApplication).filter(
                CityApplication.city_id == city_id,
                CityApplication.applicant_id == player.id,
                CityApplication.status == "pending"
            ).first()
            
            if pending_app:
                apply_section = f"""
                <div class="alert alert-info">
                    Your application is pending review. Fee if approved: ${pending_app.calculated_fee:,.2f}
                </div>
                """
            else:
                flat_fee = city.application_fee or 50_000.0

                apply_section = f"""
                <p style="margin-bottom: 12px;">
                    <strong>Application Fee:</strong> ${flat_fee:,.2f} (flat fee)
                </p>
                <form action="/api/city/apply" method="post">
                    <input type="hidden" name="city_id" value="{city_id}">
                    <button type="submit" class="btn btn-primary">Apply to Join</button>
                </form>
                """
    
    # Member actions
    member_actions = ""
    if is_member and not is_city_mayor:
        flat_reloc_fee = city.relocation_fee or 10_000.0

        member_actions = f"""
        <div class="card">
            <h2>Member Actions</h2>
            <p style="color: #94a3b8; margin-bottom: 12px;">
                Relocation fee to leave: ${flat_reloc_fee:,.2f} (flat fee)
            </p>
            <form action="/api/city/leave" method="post" onsubmit="return confirm('Are you sure you want to leave?');">
                <button type="submit" class="btn btn-danger">Leave City</button>
            </form>
        </div>
        """
    
    # Banking section (for all members)
    banking_section = ""
    if is_member:
        from cities import (
            check_member_reserves, get_player_total_value, CityBankLoan, 
            CityDebtAssumption, RESERVE_REQUIREMENT_PERCENT, DEBT_ASSUMPTION_FRACTION
        )
        import inventory
        import market
        
        total_value = get_player_total_value(player.id)
        meets_reserve, shortfall = check_member_reserves(player.id)
        
        # Get player's currency holdings
        currency_type = city.currency_type or "Not set"
        currency_qty = 0.0
        currency_value = 0.0
        required_value = total_value * RESERVE_REQUIREMENT_PERCENT
        
        if city.currency_type:
            currency_qty = inventory.get_item_quantity(player.id, city.currency_type)
            currency_price = market.get_market_price(city.currency_type) or 1.0
            currency_value = currency_qty * currency_price
        
        reserve_status = "✅ Met" if meets_reserve else f"❌ Short ${shortfall:,.2f}"
        reserve_color = "#4ade80" if meets_reserve else "#f87171"
        
        # Get active loans
        loans_html = ""
        if bank:
            loans = db.query(CityBankLoan).filter(
                CityBankLoan.city_bank_id == bank.id,
                CityBankLoan.is_active == True
            ).all()
            
            if loans:
                loans_html = "<h3 style='margin-top: 20px;'>Active Bank Loans</h3>"
                for loan in loans:
                    remaining = loan.total_owed - loan.amount_paid
                    assumable = remaining * DEBT_ASSUMPTION_FRACTION
                    
                    # Check if player already assumed from this loan
                    already_assumed = db.query(CityDebtAssumption).filter(
                        CityDebtAssumption.loan_id == loan.id,
                        CityDebtAssumption.player_id == player.id
                    ).first()
                    
                    assume_btn = ""
                    if not already_assumed:
                        assume_btn = f'''
                        <form action="/api/city/assume-debt" method="post" style="display:inline;">
                            <input type="hidden" name="loan_id" value="{loan.id}">
                            <button type="submit" class="btn btn-secondary btn-sm">Assume ${assumable:,.2f} (1/25th)</button>
                        </form>
                        '''
                    else:
                        assume_btn = '<span class="badge badge-info">Already assumed</span>'
                    
                    loans_html += f'''
                    <div style="padding: 12px; background: #0b1220; border-radius: 8px; margin-top: 8px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <strong>Loan #{loan.id}</strong><br>
                                <span style="color: #94a3b8; font-size: 13px;">
                                    Principal: ${loan.principal:,.2f} | 
                                    Remaining: ${remaining:,.2f} | 
                                    Installments left: {loan.installments_remaining}
                                </span>
                            </div>
                            {assume_btn}
                        </div>
                    </div>
                    '''
            else:
                loans_html = "<p style='color: #64748b; margin-top: 16px;'>No active loans.</p>"
        
        # Exchange currency form
        exchange_form = ""
        if city.currency_type:
            currency_price = market.get_market_price(city.currency_type) or 0
            price_display = f"${currency_price:,.2f}" if currency_price else "No market price"
            
            sell_form = ""
            if currency_qty > 0:
                sell_form = f'''
                <div style="background: #0b1220; padding: 12px; border-radius: 8px; margin-bottom: 12px;">
                    <strong>Sell to Bank</strong>
                    <p style="color: #94a3b8; font-size: 12px; margin: 4px 0 8px 0;">
                        Bank pays market price. You have {currency_qty:,.2f} {city.currency_type}.
                    </p>
                    <form action="/api/city/exchange-currency" method="post" style="display: flex; gap: 8px;">
                        <input type="number" name="quantity" min="0.01" max="{currency_qty}" step="0.01" 
                               placeholder="Quantity" style="flex: 1; padding: 8px;" required>
                        <button type="submit" class="btn btn-primary">Sell</button>
                    </form>
                </div>
                '''
            
            exchange_form = f'''
            <h3 style="margin-top: 20px;">💱 Currency Exchange</h3>
            <p style="color: #94a3b8; font-size: 13px; margin-bottom: 12px;">
                City Currency: <strong>{city.currency_type}</strong> | Market Price: <strong>{price_display}</strong>
            </p>
            
            {sell_form}
            
            <div style="background: #0b1220; padding: 12px; border-radius: 8px;">
                <strong>Buy from Market</strong>
                <p style="color: #94a3b8; font-size: 12px; margin: 4px 0 8px 0;">
                    Purchase {city.currency_type} on the open market to meet reserve requirements.
                </p>
                <a href="/market?item={city.currency_type}" class="btn btn-secondary">Go to Market →</a>
            </div>
            '''
        else:
            exchange_form = '''
            <h3 style="margin-top: 20px;">💱 Currency Exchange</h3>
            <p style="color: #64748b;">No city currency has been set yet. The Mayor must initiate a currency vote.</p>
            '''
        
        banking_section = f'''
        <div class="card">
            <h2>🏦 Your City Banking</h2>
            
            <div class="grid grid-2" style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
                <div>
                    <h3>Reserve Requirement</h3>
                    <div class="stat">
                        <span class="stat-label">City Currency</span>
                        <span class="stat-value">{currency_type}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Your Holdings</span>
                        <span class="stat-value">{currency_qty:,.2f} (${currency_value:,.2f})</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Required (10% of value)</span>
                        <span class="stat-value">${required_value:,.2f}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Status</span>
                        <span class="stat-value" style="color: {reserve_color};">{reserve_status}</span>
                    </div>
                </div>
                
                <div>
                    <h3>Production Subsidy</h3>
                    <p style="color: #94a3b8; font-size: 13px;">
                        As a city member, you receive <strong style="color: #4ade80;">4.75%</strong> of your production costs 
                        back from the city bank each time a business completes a production cycle.
                    </p>
                    <p style="color: #64748b; font-size: 12px; margin-top: 8px;">
                        (Subsidy is paid automatically when production completes)
                    </p>
                </div>
            </div>
            
            {exchange_form}
            
            {loans_html}
        </div>
        '''
    
    # Mayor controls
    mayor_controls = ""
    if is_city_mayor:
        # Get pending applications
        applications = db.query(CityApplication).filter(
            CityApplication.city_id == city_id,
            CityApplication.status == "pending"
        ).all()
        
        apps_html = ""
        if applications:
            apps_html = "<h3>Pending Applications</h3>"
            for app in applications:
                applicant = db.query(Player).filter(Player.id == app.applicant_id).first()
                app_name = applicant.business_name if applicant else f"Player {app.applicant_id}"
                apps_html += f"""
                <div style="padding: 8px 0; border-bottom: 1px solid #1e293b;">
                    <strong>{app_name}</strong> - Fee: ${app.calculated_fee:,.2f}
                </div>
                """
        
        mayor_controls = f"""
        <div class="card">
            <h2>👑 Mayor Controls</h2>
            
            <div class="grid grid-2">
                <div>
                    <h3>Fee Settings</h3>
                    <form action="/api/city/set-fees" method="post">
                        <div class="form-group">
                            <label>Application Fee (flat $)</label>
                            <input type="number" name="app_fee" value="{city.application_fee or 50000}"
                                   min="0" max="1000000" step="100">
                        </div>
                        <div class="form-group">
                            <label>Relocation Fee (flat $)</label>
                            <input type="number" name="reloc_fee" value="{city.relocation_fee or 10000}"
                                   min="0" max="500000" step="100">
                        </div>
                        <button type="submit" class="btn btn-secondary">Update Fees</button>
                    </form>
                </div>
                
                <div>
                    <h3>Currency Change</h3>
                    <form action="/api/city/currency-vote" method="post">
                        <div class="form-group">
                            <label>New Currency (Tradeable Item)</label>
                            {_currency_select_options()}
                        </div>
                        <div class="form-group">
                            <label>Poll Tax (max ${bank.cash_reserves * 0.035:,.2f})</label>
                            <input type="number" name="poll_tax" value="0" min="0" 
                                   max="{bank.cash_reserves * 0.035:.2f}" step="0.01">
                        </div>
                        <button type="submit" class="btn btn-secondary">Start Currency Vote</button>
                    </form>
                </div>
            </div>
            
            <div style="margin-top: 20px;">
                <h3>Initiate Banishment</h3>
                <form action="/api/city/banish" method="post">
                    <div class="form-group">
                        <label>Select Member</label>
                        <select name="target_id">
                            {"".join(f'<option value="{m.player_id}">{db.query(Player).filter(Player.id == m.player_id).first().business_name if db.query(Player).filter(Player.id == m.player_id).first() else m.player_id}</option>' for m in members if m.player_id != player.id)}
                        </select>
                    </div>
                    <button type="submit" class="btn btn-danger">Start Banishment Vote</button>
                </form>
            </div>
            
            {apps_html}
        </div>
        """
    
    db.close()
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>{city.name} · Wadsworth</title>
        {CITY_STYLES}
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🏙️ {city.name}</h1>
                <div>
                    <a href="/counties" class="nav-link">Counties</a>
                    <a href="/cities" class="nav-link">All Cities</a>
                    <a href="/" class="nav-link">Dashboard</a>
                </div>
            </div>
            
            <div class="grid grid-2">
                <div class="card">
                    <h2>City Info</h2>
                    <div class="stat">
                        <span class="stat-label">Members</span>
                        <span class="stat-value">{stats['member_count']}/{stats['max_members']}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Currency</span>
                        <span class="stat-value">{stats['currency_type'] or 'Not set'}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Application Fee</span>
                        <span class="stat-value">${stats['application_fee']:,.2f}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Relocation Fee</span>
                        <span class="stat-value">${stats['relocation_fee']:,.2f}</span>
                    </div>
                </div>
                
                <div class="card">
                    <h2>🏦 City Bank</h2>
                    <div class="stat">
                        <span class="stat-label">Cash Reserves</span>
                        <span class="stat-value positive">${stats['bank_reserves']:,.2f}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Currency Holdings</span>
                        <span class="stat-value">{stats['bank_currency_qty']:,.2f}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Active Loans</span>
                        <span class="stat-value">{stats['active_loans']}/5</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Total Debt</span>
                        <span class="stat-value {'negative' if stats['total_debt'] > 0 else ''}">${stats['total_debt']:,.2f}</span>
                    </div>
                </div>
            </div>
            
            <div class="card">
                <h2>Members</h2>
                {members_html}
            </div>
            
            {"" if not is_member else f'''
            <div class="card">
                <h2>Active Polls</h2>
                {polls_html}
            </div>
            '''}
            
            {"" if is_member else f'''
            <div class="card">
                <h2>Join This City</h2>
                {apply_section}
            </div>
            '''}
            
            {banking_section}
            {member_actions}
            {mayor_controls}
        </div>
    </body>
    </html>
    """


# ==========================
# API ENDPOINTS
# ==========================
@router.post("/api/city/create")
async def api_create_city(
    city_name: str = Form(...),
    district_ids: List[int] = Form(...),
    session_token: Optional[str] = Cookie(None)
):
    """Create a new city."""
    player = get_current_player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)
    
    from cities import create_city
    
    # district_ids comes as List[int] from Form
    if len(district_ids) != 10:
        return RedirectResponse(url=f"/cities?msg=Must+select+exactly+10+districts+(selected+{len(district_ids)})", status_code=303)
    
    city, message = create_city(player.id, city_name, district_ids)
    
    if city:
        return RedirectResponse(url=f"/city/{city.id}?msg=City+created!", status_code=303)
    else:
        return RedirectResponse(url=f"/cities?msg={message.replace(' ', '+')}", status_code=303)


@router.post("/api/city/apply")
async def api_apply(
    city_id: int = Form(...),
    session_token: Optional[str] = Cookie(None)
):
    """Apply to join a city."""
    player = get_current_player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)
    
    from cities import apply_to_city
    
    application, message = apply_to_city(player.id, city_id)
    
    return RedirectResponse(url=f"/city/{city_id}?msg={message.replace(' ', '+')}", status_code=303)


@router.post("/api/city/leave")
async def api_leave(session_token: Optional[str] = Cookie(None)):
    """Leave current city."""
    player = get_current_player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)
    
    from cities import leave_city
    
    success, message = leave_city(player.id)
    
    return RedirectResponse(url=f"/cities?msg={message.replace(' ', '+')}", status_code=303)


@router.post("/api/city/vote")
async def api_vote(
    poll_id: int = Form(...),
    vote: str = Form(...),
    session_token: Optional[str] = Cookie(None)
):
    """Cast a vote on a poll."""
    player = get_current_player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)
    
    from cities import cast_vote, VoteChoice, get_db, CityPoll
    
    vote_choice = VoteChoice.YES if vote == "yes" else VoteChoice.NO
    success, message = cast_vote(player.id, poll_id, vote_choice)
    
    # Get city ID for redirect
    db = get_db()
    poll = db.query(CityPoll).filter(CityPoll.id == poll_id).first()
    city_id = poll.city_id if poll else 0
    db.close()
    
    return RedirectResponse(url=f"/city/{city_id}?msg={message.replace(' ', '+')}", status_code=303)


@router.post("/api/city/set-fees")
async def api_set_fees(
    app_fee: float = Form(...),
    reloc_fee: float = Form(...),
    session_token: Optional[str] = Cookie(None)
):
    """Mayor sets city fees."""
    player = get_current_player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)
    
    from cities import set_application_fee, set_relocation_fee, get_player_city
    
    city = get_player_city(player.id)
    if not city:
        return RedirectResponse(url="/cities?msg=Not+in+a+city", status_code=303)
    
    set_application_fee(player.id, city.id, app_fee)
    set_relocation_fee(player.id, city.id, reloc_fee)
    
    return RedirectResponse(url=f"/city/{city.id}?msg=Fees+updated", status_code=303)


@router.post("/api/city/currency-vote")
async def api_currency_vote(
    currency: str = Form(...),
    poll_tax: float = Form(0),
    session_token: Optional[str] = Cookie(None)
):
    """Mayor initiates currency change vote."""
    player = get_current_player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)
    
    from cities import initiate_currency_change, get_player_city
    
    city = get_player_city(player.id)
    if not city:
        return RedirectResponse(url="/cities?msg=Not+in+a+city", status_code=303)
    
    poll, message = initiate_currency_change(player.id, city.id, currency, poll_tax)
    
    return RedirectResponse(url=f"/city/{city.id}?msg={message.replace(' ', '+')}", status_code=303)


@router.post("/api/city/banish")
async def api_banish(
    target_id: int = Form(...),
    session_token: Optional[str] = Cookie(None)
):
    """Mayor initiates banishment vote."""
    player = get_current_player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)
    
    from cities import initiate_banishment, get_player_city
    
    city = get_player_city(player.id)
    if not city:
        return RedirectResponse(url="/cities?msg=Not+in+a+city", status_code=303)
    
    poll, message = initiate_banishment(player.id, target_id, city.id)
    
    return RedirectResponse(url=f"/city/{city.id}?msg={message.replace(' ', '+')}", status_code=303)


@router.post("/api/city/exchange-currency")
async def api_exchange_currency(
    quantity: float = Form(...),
    session_token: Optional[str] = Cookie(None)
):
    """Member exchanges city currency with the bank."""
    player = get_current_player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)
    
    from cities import exchange_currency_for_member, get_player_city
    
    city = get_player_city(player.id)
    if not city:
        return RedirectResponse(url="/cities?msg=Not+in+a+city", status_code=303)
    
    success, message = exchange_currency_for_member(player.id, quantity)
    
    return RedirectResponse(url=f"/city/{city.id}?msg={message.replace(' ', '+')}", status_code=303)


@router.post("/api/city/assume-debt")
async def api_assume_debt(
    loan_id: int = Form(...),
    session_token: Optional[str] = Cookie(None)
):
    """Member assumes portion of bank debt."""
    player = get_current_player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)
    
    from cities import assume_bank_debt, get_player_city
    
    city = get_player_city(player.id)
    if not city:
        return RedirectResponse(url="/cities?msg=Not+in+a+city", status_code=303)
    
    success, message = assume_bank_debt(player.id, loan_id)
    
    return RedirectResponse(url=f"/city/{city.id}?msg={message.replace(' ', '+')}", status_code=303)


# ==========================
# PUBLIC API
# ==========================
__all__ = ['router']
