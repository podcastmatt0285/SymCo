"""
districts_ux.py

User interface for Districts Management System.
Provides:
- Districts overview dashboard
- District creation wizard with plot selection
- Individual district management
- Merge cost and requirements display
- Business creation for districts
- Dark terminal aesthetic
"""

from typing import Optional, List
from fastapi import APIRouter, Cookie, Form
from fastapi.responses import HTMLResponse, RedirectResponse

router = APIRouter()

# ==========================
# HELPER FUNCTIONS
# ==========================

def require_auth(session_token):
    """Check authentication and return player or redirect."""
    from auth import get_db, get_player_from_session
    db = get_db()
    player = get_player_from_session(db, session_token)
    db.close()
    if not player:
        return RedirectResponse(url="/login", status_code=303)
    return player

def shell(title: str, body: str, balance: float = 0.0, player_id: int = None) -> str:
    """Reuse shell from ux.py for consistent styling."""
    # Import shell from ux for consistency
    try:
        from ux import shell as ux_shell
        return ux_shell(title, body, balance, player_id)
    except:
        # Fallback minimal shell if ux not available
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{title} · SymCo Districts</title>
            <style>
                body {{ background: #020617; color: #e5e7eb; font-family: monospace; padding: 20px; }}
                .container {{ max-width: 1000px; margin: 0 auto; }}
            </style>
        </head>
        <body>
            <div class="container">
                {body}
            </div>
        </body>
        </html>
        """

# ==========================
# DISTRICTS DASHBOARD
# ==========================

@router.get("/districts", response_class=HTMLResponse)
def districts_dashboard(session_token: Optional[str] = Cookie(None)):
    """Main districts management dashboard."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): 
        return player
    
    try:
        from districts import (
            get_player_districts, 
            get_next_merge_cost, 
            get_plots_required,
            DISTRICT_TYPES,
            get_player_merge_stats
        )
        from land import get_player_land
        
        districts = get_player_districts(player.id)
        plots = get_player_land(player.id)
        merge_stats = get_player_merge_stats(player.id)
        
        next_cost = get_next_merge_cost(player.id)
        plots_required = get_plots_required(player.id)
        
        html = f'''
        <a href="/land" style="color: #38bdf8;"><- Land Portfolio</a>
        <h1>🏛️ Districts Management System</h1>

        <div style="margin-bottom: 16px;">
            <a href="/district-market" class="btn-blue" style="display: inline-block; padding: 10px 20px; font-size: 1rem;">
                📈 District Market
            </a>
            <a href="/cities" class="btn-blue" style="display: inline-block; padding: 10px 20px; font-size: 1rem;">
                🏙️ Cities
            </a>
        </div>
        
        <div class="card" style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border-left: 4px solid #38bdf8;">
            <h2 style="margin-top: 0; color: #38bdf8;">📊 District Overview</h2>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-top: 16px;">
                <div>
                    <div style="color: #64748b; font-size: 0.8rem;">TOTAL DISTRICTS</div>
                    <div style="font-size: 2rem; font-weight: bold; color: #22c55e;">{len(districts)}</div>
                </div>
                <div>
                    <div style="color: #64748b; font-size: 0.8rem;">MERGES COMPLETED</div>
                    <div style="font-size: 2rem; font-weight: bold; color: #38bdf8;">{merge_stats.total_merges_completed}</div>
                </div>
                <div>
                    <div style="color: #64748b; font-size: 0.8rem;">OCCUPIED</div>
                    <div style="font-size: 2rem; font-weight: bold; color: #f59e0b;">{sum(1 for d in districts if d.occupied_by_business_id)}</div>
                </div>
                <div>
                    <div style="color: #64748b; font-size: 0.8rem;">VACANT</div>
                    <div style="font-size: 2rem; font-weight: bold; color: #64748b;">{sum(1 for d in districts if not d.occupied_by_business_id)}</div>
                </div>
            </div>
        </div>
        
        <div class="card" style="background: #0f172a; border-left: 4px solid #f59e0b;">
            <h2 style="margin-top: 0; color: #f59e0b;">💰 Next Merge Requirements</h2>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 16px; margin-top: 16px;">
                <div>
                    <div style="color: #64748b; font-size: 0.8rem; margin-bottom: 4px;">PLOTS REQUIRED (FIBONACCI)</div>
                    <div style="font-size: 1.8rem; font-weight: bold; color: #38bdf8;">{plots_required} plots</div>
                    <div style="color: #64748b; font-size: 0.75rem; margin-top: 4px;">Must be same terrain & occupied</div>
                </div>
                <div>
                    <div style="color: #64748b; font-size: 0.8rem; margin-bottom: 4px;">MERGE COST (ESCALATING)</div>
                    <div style="font-size: 1.8rem; font-weight: bold; color: #f59e0b;">${next_cost:,.0f}</div>
                    <div style="color: #64748b; font-size: 0.75rem; margin-top: 4px;">Cost × 1.25 per merge completed</div>
                </div>
                <div>
                    <div style="color: #64748b; font-size: 0.8rem; margin-bottom: 4px;">AVAILABLE PLOTS</div>
                    <div style="font-size: 1.8rem; font-weight: bold; color: {"#22c55e" if len(plots) >= plots_required else "#ef4444"};">{len(plots)} plots</div>
                    <div style="color: #64748b; font-size: 0.75rem; margin-top: 4px;">
                        {"✓ Sufficient" if len(plots) >= plots_required else "⚠ Need more plots"}
                    </div>
                </div>
            </div>
            <div style="margin-top: 20px;">
                <a href="/districts/create" class="btn-blue" style="display: inline-block; padding: 10px 20px; font-size: 1rem;">
                    ⚡ Create New District
                </a>
            </div>
        </div>
        '''
        
        # Show existing districts
        if districts:
            html += '<h2 style="color: #38bdf8; margin-top: 32px;">🏛️ Your Districts</h2>'
            
            for district in districts:
                district_config = DISTRICT_TYPES.get(district.district_type, {})
                district_name = district_config.get("name", district.district_type.replace("_", " ").title())
                district_desc = district_config.get("description", "")
                
                status = "OCCUPIED" if district.occupied_by_business_id else "VACANT"
                status_color = "#22c55e" if district.occupied_by_business_id else "#64748b"
                
                # Calculate monthly tax
                monthly_tax = district.monthly_tax
                
                html += f'''
                <div class="card" style="border-left: 4px solid {status_color};">
                    <div style="display: flex; justify-content: space-between; align-items: start; flex-wrap: wrap; gap: 16px;">
                        <div style="flex: 1; min-width: 300px;">
                            <h3 style="margin: 0; color: #38bdf8; font-size: 1.3rem;">
                                {district_name}
                                <span class="badge" style="background: {status_color}; color: #020617; margin-left: 8px;">
                                    {status}
                                </span>
                            </h3>
                            <p style="color: #64748b; margin: 8px 0; font-size: 0.9rem;">{district_desc}</p>
                            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-top: 12px;">
                                <div>
                                    <div style="color: #64748b; font-size: 0.7rem;">TERRAIN</div>
                                    <div style="color: #e5e7eb; font-size: 0.85rem;">{district.terrain_type.title()}</div>
                                </div>
                                <div>
                                    <div style="color: #64748b; font-size: 0.7rem;">SIZE</div>
                                    <div style="color: #e5e7eb; font-size: 0.85rem;">{district.size:.1f} units</div>
                                </div>
                                <div>
                                    <div style="color: #64748b; font-size: 0.7rem;">PLOTS MERGED</div>
                                    <div style="color: #e5e7eb; font-size: 0.85rem;">{district.plots_merged}</div>
                                </div>
                                <div>
                                    <div style="color: #64748b; font-size: 0.7rem;">MONTHLY TAX</div>
                                    <div style="color: #ef4444; font-size: 0.85rem; font-weight: bold;">${monthly_tax:,.0f}</div>
                                </div>
                            </div>
                        </div>
                        <div style="display: flex; flex-direction: column; gap: 8px;">
                            <a href="/districts/{district.id}" class="btn-blue" style="display: inline-block; padding: 8px 16px; text-align: center;">
                                View Details
                            </a>
                        </div>
                    </div>
                </div>
                '''
        else:
            html += '''
            <div class="card" style="text-align: center; padding: 40px; background: #0f172a;">
                <h3 style="color: #64748b; margin: 0;">No Districts Yet</h3>
                <p style="color: #64748b; margin: 16px 0;">Districts are permanent mega-facilities created by merging multiple land plots.</p>
                <p style="color: #64748b; margin: 16px 0;">They cannot be sold or dismantled once created.</p>
                <a href="/districts/create" class="btn-blue" style="display: inline-block; padding: 10px 20px; margin-top: 16px;">
                    Create Your First District
                </a>
            </div>
            '''
        
        return shell("Districts", html, player.cash_balance, player.id)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return shell("Districts", f"<h3>Error</h3><p>{e}</p>", player.cash_balance, player.id)


# ==========================
# CREATE DISTRICT
# ==========================

@router.get("/districts/create", response_class=HTMLResponse)
def create_district_page(session_token: Optional[str] = Cookie(None)):
    """District creation wizard with plot selection."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): 
        return player
    
    try:
        from districts import (
            get_next_merge_cost, 
            get_plots_required,
            DISTRICT_TYPES
        )
        from land import get_player_land
        
        plots = get_player_land(player.id)
        next_cost = get_next_merge_cost(player.id)
        plots_required = get_plots_required(player.id)
        
        # Group plots by terrain type (only occupied plots)
        occupied_plots = [p for p in plots if p.occupied_by_business_id]
        plots_by_terrain = {}
        for plot in occupied_plots:
            if plot.terrain_type not in plots_by_terrain:
                plots_by_terrain[plot.terrain_type] = []
            plots_by_terrain[plot.terrain_type].append(plot)
        
        html = f'''
        <a href="/districts" style="color: #38bdf8;"><- Districts Dashboard</a>
        <h1>⚡ Create New District</h1>
        
        <div class="card" style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border-left: 4px solid #f59e0b;">
            <h2 style="margin-top: 0; color: #f59e0b;">⚠️ Requirements</h2>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-top: 16px;">
                <div>
                    <div style="color: #64748b; font-size: 0.8rem;">PLOTS NEEDED</div>
                    <div style="font-size: 1.5rem; font-weight: bold; color: #38bdf8;">{plots_required}</div>
                </div>
                <div>
                    <div style="color: #64748b; font-size: 0.8rem;">MERGE COST</div>
                    <div style="font-size: 1.5rem; font-weight: bold; color: #f59e0b;">${next_cost:,.0f}</div>
                </div>
                <div>
                    <div style="color: #64748b; font-size: 0.8rem;">YOUR BALANCE</div>
                    <div style="font-size: 1.5rem; font-weight: bold; color: {"#22c55e" if player.cash_balance >= next_cost else "#ef4444"};">${player.cash_balance:,.0f}</div>
                </div>
            </div>
            <div style="margin-top: 16px; padding: 12px; background: #020617; border-left: 3px solid #64748b;">
                <div style="color: #64748b; font-size: 0.85rem;">
                    ⚠️ <strong>All plots must:</strong> (1) Have the same terrain type, (2) Be occupied by a business, (3) Match district terrain requirements<br>
                    🚨 <strong>Warning:</strong> Districts are PERMANENT. They cannot be sold or dismantled. Businesses on plots will be removed.
                </div>
            </div>
        </div>
        '''
        
        # Show available district types
        html += '''
        <div class="card">
            <h2 style="margin-top: 0; color: #38bdf8;">🏛️ Available District Types</h2>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 12px; margin-top: 16px;">
        '''
        
        for dtype, config in DISTRICT_TYPES.items():
            name = config["name"]
            desc = config["description"]
            terrains = ", ".join(config["allowed_terrain"])
            tax = config["base_tax"]
            
            html += f'''
            <div style="padding: 12px; background: #020617; border-left: 3px solid #38bdf8;">
                <div style="font-weight: bold; color: #38bdf8; margin-bottom: 4px;">{name}</div>
                <div style="font-size: 0.8rem; color: #64748b; margin-bottom: 8px;">{desc}</div>
                <div style="font-size: 0.75rem; color: #64748b;">
                    <strong>Terrain:</strong> {terrains}<br>
                    <strong>Base Tax:</strong> ${tax:,.0f}/mo × 15 (district multiplier)
                </div>
            </div>
            '''
        
        html += '</div></div>'
        
        # Show plot selection by terrain
        if not occupied_plots:
            html += '''
            <div class="card" style="text-align: center; background: #0f172a;">
                <h3 style="color: #ef4444;">❌ No Occupied Plots Available</h3>
                <p style="color: #64748b;">You need occupied land plots to create a district.</p>
                <a href="/land" class="btn-blue" style="display: inline-block; padding: 8px 16px; margin-top: 12px;">Go to Land Portfolio</a>
            </div>
            '''
        else:
            html += f'''
            <form action="/api/districts/create" method="post">
                <div class="card">
                    <h2 style="margin-top: 0; color: #38bdf8;">📍 Select Plots ({plots_required} Required)</h2>
                    
                    <div style="margin-bottom: 16px;">
                        <label style="display: block; margin-bottom: 8px; color: #64748b; font-size: 0.9rem;">District Type:</label>
                        <select name="district_type" required style="width: 100%; max-width: 400px; padding: 8px; font-size: 1rem;">
                            <option value="">Select District Type...</option>
            '''
            
            for dtype, config in DISTRICT_TYPES.items():
                html += f'<option value="{dtype}">{config["name"]}</option>'
            
            html += '''
                        </select>
                    </div>
                    
                    <div style="margin-top: 20px;">
                        <div style="color: #64748b; font-size: 0.9rem; margin-bottom: 12px;">
                            Select plots (all must be same terrain):
                        </div>
            '''
            
            # Show plots grouped by terrain
            for terrain, terrain_plots in plots_by_terrain.items():
                if len(terrain_plots) >= plots_required:
                    html += f'''
                    <div style="margin-bottom: 20px; padding: 12px; background: #020617; border-left: 3px solid #22c55e;">
                        <div style="font-weight: bold; color: #22c55e; margin-bottom: 8px;">
                            {terrain.title()} Terrain ({len(terrain_plots)} plots available)
                        </div>
                        <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 8px;">
                    '''
                    
                    for plot in terrain_plots:
                        html += f'''
                        <label style="display: flex; align-items: center; gap: 8px; padding: 8px; background: #0f172a; cursor: pointer; border: 1px solid #1e293b;">
                            <input type="checkbox" name="plot_ids" value="{plot.id}" style="cursor: pointer;">
                            <div>
                                <div style="font-size: 0.85rem;">Plot #{plot.id}</div>
                                <div style="font-size: 0.7rem; color: #64748b;">Size: {plot.size:.1f} | Tax: ${plot.monthly_tax:.0f}/mo</div>
                            </div>
                        </label>
                        '''
                    
                    html += '</div></div>'
                else:
                    html += f'''
                    <div style="margin-bottom: 12px; padding: 12px; background: #020617; border-left: 3px solid #64748b; opacity: 0.6;">
                        <div style="color: #64748b; margin-bottom: 4px;">
                            {terrain.title()} Terrain ({len(terrain_plots)} plots available)
                        </div>
                        <div style="font-size: 0.8rem; color: #64748b;">
                            ⚠️ Need {plots_required - len(terrain_plots)} more {terrain} plots
                        </div>
                    </div>
                    '''
            
            html += '''
                    </div>
                </div>
                
                <div class="card" style="background: #0f172a; text-align: center;">
                    <button type="submit" class="btn-blue" style="padding: 12px 32px; font-size: 1.1rem;">
                        🏛️ Create District
                    </button>
                    <div style="margin-top: 12px; color: #64748b; font-size: 0.8rem;">
                        This action is PERMANENT and cannot be undone
                    </div>
                </div>
            </form>
            '''
        
        return shell("Create District", html, player.cash_balance, player.id)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return shell("Create District", f"<h3>Error</h3><p>{e}</p>", player.cash_balance, player.id)


# ==========================
# DISTRICT DETAILS
# ==========================

# ==========================
# UPDATED DISTRICT DETAILS ROUTE
# ==========================
# Replace the district_details function in districts_ux.py with this version
# This adds a working business creation form with district-specific businesses

@router.get("/districts/{district_id}", response_class=HTMLResponse)
def district_details(district_id: int, session_token: Optional[str] = Cookie(None)):
    """Individual district management page."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): 
        return player
    
    try:
        from districts import get_district, DISTRICT_TYPES
        from business import get_district_business_types
        from auth import get_db
        
        district = get_district(district_id)
        
        if not district:
            return shell("District Not Found", 
                '<h3>District not found</h3><a href="/districts" class="btn-blue">Back to Districts</a>',
                player.cash_balance, player.id)
        
        if district.owner_id != player.id:
            return shell("Access Denied", 
                '<h3>Access denied</h3><a href="/districts" class="btn-blue">Back to Districts</a>',
                player.cash_balance, player.id)
        
        district_config = DISTRICT_TYPES.get(district.district_type, {})
        district_name = district_config.get("name", district.district_type.replace("_", " ").title())
        district_desc = district_config.get("description", "")
        
        status = "OCCUPIED" if district.occupied_by_business_id else "VACANT"
        status_color = "#22c55e" if district.occupied_by_business_id else "#64748b"
        
        html = f'''
        <a href="/districts" style="color: #38bdf8;"><- Districts Dashboard</a>
        <h1>🏛️ {district_name}</h1>
        
        <div class="card" style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border-left: 4px solid {status_color};">
            <h2 style="margin-top: 0; color: #38bdf8;">
                District #{district.id}
                <span class="badge" style="background: {status_color}; color: #020617; margin-left: 8px;">
                    {status}
                </span>
            </h2>
            <p style="color: #64748b; font-size: 0.95rem; margin: 12px 0;">{district_desc}</p>
            
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-top: 20px;">
                <div>
                    <div style="color: #64748b; font-size: 0.75rem;">TERRAIN TYPE</div>
                    <div style="color: #e5e7eb; font-size: 1.1rem; font-weight: bold;">{district.terrain_type.title()}</div>
                </div>
                <div>
                    <div style="color: #64748b; font-size: 0.75rem;">TOTAL SIZE</div>
                    <div style="color: #e5e7eb; font-size: 1.1rem; font-weight: bold;">{district.size:.1f} units</div>
                </div>
                <div>
                    <div style="color: #64748b; font-size: 0.75rem;">PLOTS MERGED</div>
                    <div style="color: #38bdf8; font-size: 1.1rem; font-weight: bold;">{district.plots_merged}</div>
                </div>
                <div>
                    <div style="color: #64748b; font-size: 0.75rem;">MONTHLY TAX</div>
                    <div style="color: #ef4444; font-size: 1.1rem; font-weight: bold;">${district.monthly_tax:,.0f}</div>
                </div>
                <div>
                    <div style="color: #64748b; font-size: 0.75rem;">CREATED</div>
                    <div style="color: #e5e7eb; font-size: 0.9rem;">{district.created_at.strftime("%Y-%m-%d")}</div>
                </div>
                <div>
                    <div style="color: #64748b; font-size: 0.75rem;">LAST TAX PAID</div>
                    <div style="color: #e5e7eb; font-size: 0.9rem;">{district.last_tax_payment.strftime("%Y-%m-%d")}</div>
                </div>
            </div>
        </div>
        '''
        
        # Show business if occupied or creation form if vacant
        db = get_db()
        
        if district.occupied_by_business_id:
            from business import Business, BUSINESS_TYPES
            business = db.query(Business).filter(Business.id == district.occupied_by_business_id).first()
            
            if business:
                # Try to get config from district businesses first, fall back to regular
                try:
                    district_biz_types = get_district_business_types()
                    biz_config = district_biz_types.get(business.business_type, {})
                except:
                    biz_config = BUSINESS_TYPES.get(business.business_type, {})
                
                biz_name = biz_config.get("name", business.business_type.replace("_", " ").title())
                biz_class = biz_config.get("class", "unknown")
                cycles = biz_config.get("cycles_to_complete", 1)
                progress_pct = (business.progress_ticks / cycles) * 100 if cycles > 0 else 0
                
                html += f'''
                <div class="card" style="border-left: 4px solid #22c55e;">
                    <h3 style="margin-top: 0; color: #22c55e;">🏭 Current Business</h3>
                    <div style="display: flex; justify-content: space-between; align-items: start; flex-wrap: wrap; gap: 16px;">
                        <div style="flex: 1;">
                            <div style="font-size: 1.2rem; font-weight: bold; color: #e5e7eb;">{biz_name}</div>
                            <div style="color: #64748b; font-size: 0.85rem; margin-top: 4px;">
                                Class: {biz_class.upper()} | Progress: {progress_pct:.1f}%
                            </div>
                            <div class="progress" style="margin-top: 8px; width: 300px; max-width: 100%;">
                                <div class="progress-bar" style="width: {progress_pct}%;"></div>
                            </div>
                        </div>
                        <a href="/businesses" class="btn-blue">Manage Business</a>
                    </div>
                </div>
                '''
        else:
            # Show business creation form
            try:
                district_businesses = get_district_business_types()
                district_terrain_key = f"district_{district.district_type}"
                
                # DEBUG: Show what we're working with
                html += f'''
                <div class="card" style="background: #1e1e2e; border-left: 4px solid #f59e0b;">
                    <h4 style="margin: 0 0 8px 0; color: #f59e0b;">🔍 Debug Info</h4>
                    <div style="font-size: 0.8rem; color: #94a3b8; font-family: monospace;">
                        <div>district.district_type = "{district.district_type}"</div>
                        <div>district.terrain_type = "{district.terrain_type}"</div>
                        <div>district_terrain_key = "{district_terrain_key}"</div>
                        <div>district_businesses loaded = {len(district_businesses)} types</div>
                    </div>
                </div>
                '''
                
                # Get owned businesses count for cost calculation
                from business import Business
                owned_businesses_count = db.query(Business).filter(Business.owner_id == player.id).count()
                
                html += f'''
                <div class="card">
                    <h3 style="margin-top: 0; color: #38bdf8;">🏭 Build District Business</h3>
                    <form action="/api/business/create-district" method="post" style="display: flex; gap: 12px; align-items: center; flex-wrap: wrap;">
                        <input type="hidden" name="district_id" value="{district.id}">
                        <select name="business_type" required style="flex: 1; min-width: 250px; padding: 10px;">
                            <option value="">Select Business Type...</option>
                '''
                
                available_businesses = []
                for btype, config in district_businesses.items():
                    if not isinstance(config, dict):
                        continue
                    if district_terrain_key in config.get("allowed_terrain", []):
                        base_cost = config.get("startup_cost", 2500.0)
                        multiplier = 1.0 + (owned_businesses_count * 0.25)
                        actual_cost = base_cost * multiplier
                        
                        business_name = config.get("name", btype)
                        html += f'<option value="{btype}">{business_name} (${actual_cost:,.0f})</option>'
                        available_businesses.append(btype)
                
                html += '</select>'
                
                if available_businesses:
                    html += '<button type="submit" class="btn-blue" style="padding: 10px 20px;">Build Business</button>'
                else:
                    html += '<div style="color: #ef4444;">No businesses available for this district type</div>'
                
                html += '</form>'
                
                # Show available business types details
                if available_businesses:
                    html += '<div style="margin-top: 20px;"><h4 style="color: #64748b; margin-bottom: 12px;">Available Businesses:</h4>'
                    
                    for btype in available_businesses:
                        config = district_businesses[btype]
                        name = config.get("name", btype)
                        desc = config.get("description", "")
                        biz_class = config.get("class", "unknown")
                        base_cost = config.get("startup_cost", 2500.0)
                        multiplier = 1.0 + (owned_businesses_count * 0.25)
                        actual_cost = base_cost * multiplier
                        
                        html += f'''
                        <div style="padding: 12px; margin-bottom: 8px; background: #020617; border-left: 3px solid #38bdf8;">
                            <div style="font-weight: bold; color: #38bdf8;">{name}</div>
                            <div style="font-size: 0.85rem; color: #64748b; margin-top: 4px;">{desc}</div>
                            <div style="font-size: 0.75rem; color: #64748b; margin-top: 4px;">
                                Class: {biz_class.upper()} | Cost: ${actual_cost:,.0f}
                            </div>
                        </div>
                        '''
                    
                    html += '</div>'
                
                html += '</div>'
                
            except Exception as e:
                import traceback
                traceback.print_exc()
                html += f'<div class="card"><p style="color: #ef4444;">Error loading business types: {e}</p></div>'
        
        db.close()
        
        # Show permanent warning
        html += '''
        <div class="card" style="background: #0f172a; border-left: 4px solid #ef4444;">
            <h3 style="margin-top: 0; color: #ef4444;">⚠️ District Rules</h3>
            <ul style="color: #64748b; margin: 0; padding-left: 20px;">
                <li>Districts are PERMANENT and cannot be sold or dismantled</li>
                <li>Districts pay 15× the standard land tax rate</li>
                <li>Only district-specific businesses can be built here</li>
                <li>Original plots cannot be recovered once merged</li>
            </ul>
        </div>
        '''
        
        return shell(f"District #{district.id}", html, player.cash_balance, player.id)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return shell("Error", f"<h3>Error</h3><p>{e}</p><pre>{traceback.format_exc()}</pre>", player.cash_balance, player.id)

# ==========================
# API ENDPOINTS
# ==========================

# ==========================
# ADD THIS TO districts_ux.py
# ==========================
# Add this endpoint to your districts_ux.py file (in the API ENDPOINTS section)

@router.post("/api/business/create-district")
async def api_create_district_business(
    district_id: int = Form(...),
    business_type: str = Form(...),
    session_token: Optional[str] = Cookie(None)
):
    """API endpoint to create a business on a district."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): 
        return player
    
    try:
        from business import create_district_business
        
        business, message = create_district_business(player.id, district_id, business_type)
        
        if business:
            return RedirectResponse(url=f"/districts/{district_id}?success=business_created", status_code=303)
        else:
            # URL encode the error message
            import urllib.parse
            error_msg = urllib.parse.quote(message)
            return RedirectResponse(url=f"/districts/{district_id}?error={error_msg}", status_code=303)
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        import urllib.parse
        error_msg = urllib.parse.quote(str(e))
        return RedirectResponse(url=f"/districts/{district_id}?error={error_msg}", status_code=303)

@router.post("/api/districts/create")
async def api_create_district(
        district_type: str = Form(...),
        plot_ids: list[str] = Form(...),
        session_token: Optional[str] = Cookie(None)
    ):
    """API endpoint to create a district."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse): 
        return player
    
    try:
        from districts import create_district
        
        # Convert plot_ids to integers
        plot_id_list = [int(pid) for pid in plot_ids]
        
        district, message = create_district(player.id, district_type, plot_id_list)
        
        if district:
            return RedirectResponse(url=f"/districts/{district.id}?success=created", status_code=303)
        else:
            return RedirectResponse(url=f"/districts/create?error={message}", status_code=303)
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return RedirectResponse(url=f"/districts/create?error={str(e)}", status_code=303)

# ==========================
# DISTRICT MARKET PAGE
# ==========================

@router.get("/district-market", response_class=HTMLResponse)
def district_market_page(session_token: Optional[str] = Cookie(None), item: str = "steel"):
    """District market view with order book."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    
    try:
        import district_market as dm
        
        items = list(dm.DISTRICT_ITEMS.keys())
        
        if item not in items and items:
            item = items[0]
        
        stats = dm.get_market_stats()
        order_book = dm.get_order_book(item)
        
        # Group items by category
        categories = {}
        for i in items:
            info = dm.get_district_item_info(i)
            cat = info.get("category", "other") if info else "other"
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(i)
        
        # Category colors
        cat_colors = {
            "metals": "#f59e0b",
            "industrial": "#64748b",
            "utilities": "#22c55e",
            "fuel": "#ef4444",
            "construction": "#8b5cf6",
            "electronics": "#38bdf8",
            "chemicals": "#ec4899",
            "aerospace": "#06b6d4",
            "military": "#dc2626",
            "medical": "#10b981",
            "food": "#f97316",
            "other": "#94a3b8"
        }
        
        # Search bar
        search_bar = '''
        <div style="margin-bottom: 16px;">
            <input 
                type="text" 
                id="itemSearch" 
                placeholder="🔍 Search district items..." 
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
                <a href="/district-market?item={i}" 
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
        item_info = dm.get_district_item_info(item)
        item_name = item_info.get("name", item.replace("_", " ").title()) if item_info else item.replace("_", " ").title()
        item_desc = item_info.get("description", "") if item_info else ""
        item_cat = item_info.get("category", "other") if item_info else "other"
        
        # Build market HTML
        market_html = f'''
        <a href="/districts" style="color: #38bdf8;"><- Districts Dashboard</a>
        <div style="display: flex; gap: 20px; max-width: 100%;">
            <div style="flex: 2; min-width: 0;">
                <h1>📈 District Market</h1>
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
                    <form action="/api/district-market/order" method="post" style="display: grid; grid-template-columns: 1fr 1fr 1fr auto; gap: 10px;">
                        <input type="hidden" name="item_type" value="{item}">
                        <select name="order_type">
                            <option value="buy">BUY</option>
                            <option value="sell">SELL</option>
                        </select>
                        <input type="number" name="quantity" placeholder="Quantity" step="0.01" required>
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
                    <h3>District Market Stats</h3>
                    <p><strong>24h Volume:</strong><br>${stats["volume_24h"]:,.2f}</p>
                    <p style="margin-top: 12px;"><strong>Total Trades:</strong><br>{stats["total_trades"]:,}</p>
                    <p style="margin-top: 12px;"><strong>Active Orders:</strong><br>{stats["active_orders"]:,}</p>
                </div>
            </div>
        </div>
        
        {dm.get_district_ticker_html()}
        '''
        
        return shell("District Market", market_html, player.cash_balance, player.id)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return shell("District Market", f"Error loading district market: {e}", player.cash_balance, player.id)


@router.post("/api/district-market/order")
async def api_district_market_order(
    item_type: str = Form(...),
    order_type: str = Form(...),
    quantity: float = Form(...),
    price: float = Form(...),
    session_token: Optional[str] = Cookie(None)
):
    """Place a district market order."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    
    try:
        import district_market as dm
        
        ot = dm.OrderType.BUY if order_type == "buy" else dm.OrderType.SELL
        order = dm.create_order(
            player_id=player.id,
            order_type=ot,
            order_mode=dm.OrderMode.LIMIT,
            item_type=item_type,
            quantity=quantity,
            price=price
        )
        
        if order:
            return RedirectResponse(url=f"/district-market?item={item_type}&success=order_placed", status_code=303)
        else:
            return RedirectResponse(url=f"/district-market?item={item_type}&error=order_failed", status_code=303)
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return RedirectResponse(url=f"/district-market?item={item_type}&error={str(e)}", status_code=303)


@router.post("/api/district-market/cancel")
async def api_district_market_cancel(
    order_id: int = Form(...),
    item_type: str = Form(...),
    session_token: Optional[str] = Cookie(None)
):
    """Cancel a district market order."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player
    
    try:
        import district_market as dm
        
        success = dm.cancel_order(order_id, player.id)
        
        if success:
            return RedirectResponse(url=f"/district-market?item={item_type}&success=order_cancelled", status_code=303)
        else:
            return RedirectResponse(url=f"/district-market?item={item_type}&error=cancel_failed", status_code=303)
            
    except Exception as e:
        return RedirectResponse(url=f"/district-market?item={item_type}&error={str(e)}", status_code=303)
