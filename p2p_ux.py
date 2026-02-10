"""
p2p_ux.py

Peer-to-Peer UX module for the economic simulation.
Provides:
- P2P Dashboard (entry fee gate)
- Contracts Dashboard (creation + trading market)
- Contract Creation form (multi-item, intervals, lengths)
- Contract Trading Market (listing, bidding, resolution)
- Contract detail views
- Active contract management
"""

from typing import Optional
from fastapi import APIRouter, Cookie, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from datetime import datetime

router = APIRouter()


# ==========================
# HELPERS
# ==========================

def require_auth(session_token):
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
        print(f"[P2P_UX] Auth check failed: {e}")
        return RedirectResponse(url="/login", status_code=303)


def require_p2p_access(player):
    """Check if player has paid the P2P access fee recently. Returns RedirectResponse to gate if not."""
    from p2p import has_p2p_access
    if not has_p2p_access(player.id):
        return RedirectResponse(url="/p2p", status_code=303)
    return None


def shell(title, body, balance=0.0, player_id=None):
    """Re-use the main shell template."""
    from ux import shell as main_shell
    return main_shell(title, body, balance, player_id)


def format_item_name(item_type: str) -> str:
    """Format an item_type key into a readable name."""
    return item_type.replace("_", " ").title()


def get_current_tick():
    """Get the current game tick."""
    import app as app_mod
    return app_mod.current_tick


# ==========================
# P2P DASHBOARD (ENTRY FEE GATE)
# ==========================

@router.get("/p2p", response_class=HTMLResponse)
def p2p_gate(session_token: Optional[str] = Cookie(None)):
    """
    P2P Gateway - shows the fee and asks for confirmation.
    This is the entry point that costs money each time.
    """
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player

    from p2p import P2P_DASHBOARD_FEE

    return shell(
        "Peer to Peer",
        f"""
        <a href="/" style="color: #38bdf8;">&lt;- Dashboard</a>
        <h1>Peer to Peer Network</h1>

        <div class="card" style="border-color: #f59e0b; text-align: center;">
            <h2 style="color: #f59e0b;">ACCESS FEE REQUIRED</h2>
            <p style="font-size: 1.2rem; margin: 20px 0;">
                Entering the P2P Network costs <span style="color: #ef4444; font-weight: bold;">${P2P_DASHBOARD_FEE:,.0f}</span> per visit.
            </p>
            <p style="color: #64748b; margin-bottom: 20px;">
                This fee is paid to the Government and is non-refundable.<br>
                You will gain access to Contracts, and future P2P services.
            </p>
            <p style="color: #64748b; margin-bottom: 20px;">
                Your balance: <span style="color: #22c55e;">${player.cash_balance:,.2f}</span>
            </p>
            <form action="/p2p/enter" method="post" style="display: inline;">
                <button type="submit" class="btn-gold" style="padding: 12px 32px; font-size: 1rem;">
                    Pay ${P2P_DASHBOARD_FEE:,.0f} &amp; Enter
                </button>
            </form>
            <div style="margin-top: 12px;">
                <a href="/" style="color: #64748b;">Cancel</a>
            </div>
        </div>
        """,
        player.cash_balance,
        player.id
    )


@router.post("/p2p/enter", response_class=HTMLResponse)
def p2p_enter(session_token: Optional[str] = Cookie(None)):
    """Process the P2P entry fee and redirect to the P2P dashboard."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player

    from p2p import charge_p2p_access

    if not charge_p2p_access(player.id):
        return shell(
            "Peer to Peer",
            """
            <a href="/" style="color: #38bdf8;">&lt;- Dashboard</a>
            <h1>Peer to Peer Network</h1>
            <div class="card" style="border-color: #ef4444;">
                <h3 style="color: #ef4444;">INSUFFICIENT FUNDS</h3>
                <p>You don't have enough cash to access the P2P Network.</p>
                <a href="/" class="btn-blue">Back to Dashboard</a>
            </div>
            """,
            player.cash_balance,
            player.id
        )

    return RedirectResponse(url="/p2p/dashboard", status_code=303)


@router.get("/p2p/dashboard", response_class=HTMLResponse)
def p2p_dashboard(session_token: Optional[str] = Cookie(None)):
    """
    The P2P Dashboard - hub for all P2P activities.
    Only accessible after paying the entry fee.
    """
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player

    access_redirect = require_p2p_access(player)
    if access_redirect:
        return access_redirect

    return shell(
        "P2P Dashboard",
        f"""
        <a href="/" style="color: #38bdf8;">&lt;- Dashboard</a>
        <h1>P2P Network Dashboard</h1>
        <p style="color: #64748b; margin-bottom: 24px;">Welcome to the Peer-to-Peer Network. Select a service below.</p>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
            <div class="card" style="border-color: #38bdf8;">
                <h3 style="color: #38bdf8;">Contracts</h3>
                <p>Create and trade delivery contracts. Bind other players to deliver commodities on a schedule.</p>
                <p style="color: #64748b; font-size: 0.85rem;">Create contracts with up to 3 items, various delivery intervals, and contract lengths. Trade contracts on the open market.</p>
                <a href="/p2p/contracts" class="btn-blue" style="display: inline-block; padding: 10px 20px; margin-top: 12px;">Contracts Dashboard</a>
            </div>
            <div class="card" style="border-color: #c084fc;">
                <h3 style="color: #c084fc;">Chatrooms</h3>
                <p>Real-time chat rooms for the community. Global, Trade, City, Q&A, Recruiting, and more.</p>
                <p style="color: #64748b; font-size: 0.85rem;">Chat with other players, get market intel, recruit for your city.</p>
                <a href="/chat" class="btn-blue" style="display: inline-block; padding: 10px 20px; margin-top: 12px; background: #c084fc;">Open Chat</a>
            </div>
            <div class="card" style="border-color: #475569; opacity: 0.5;">
                <h3 style="color: #475569;">Direct Messages</h3>
                <p style="color: #475569;">Private player-to-player messaging.</p>
                <p style="color: #475569; font-size: 0.85rem;">Coming soon.</p>
                <span style="display: inline-block; padding: 10px 20px; background: #1e293b; color: #475569; border-radius: 3px; margin-top: 12px;">Locked</span>
            </div>
        </div>
        """,
        player.cash_balance,
        player.id
    )


# ==========================
# CONTRACTS DASHBOARD
# ==========================

@router.get("/p2p/contracts", response_class=HTMLResponse)
def contracts_dashboard(session_token: Optional[str] = Cookie(None), tab: str = "market"):
    """Contracts main view with tabs for Market and My Contracts."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player

    access_redirect = require_p2p_access(player)
    if access_redirect:
        return access_redirect

    from p2p import (
        get_db, Contract, ContractItem, ContractBid, ContractStatus,
        DELIVERY_INTERVALS, CONTRACT_LENGTHS, get_player_contracts
    )

    current_tick = get_current_tick()

    # Tab navigation
    tabs = {
        "market": "Trading Market",
        "my_contracts": "My Contracts",
        "create": "Create Contract",
    }

    tab_html = '<div style="display: flex; gap: 8px; margin-bottom: 20px; overflow-x: auto; white-space: nowrap;">'
    for key, label in tabs.items():
        active_style = "background: #38bdf8; color: #020617; font-weight: bold;" if key == tab else "background: #1e293b; color: #e5e7eb;"
        tab_html += f'<a href="/p2p/contracts?tab={key}" style="padding: 8px 16px; border-radius: 3px; text-decoration: none; {active_style}">{label}</a>'
    tab_html += '</div>'

    content = ""

    if tab == "market":
        content = _render_trading_market(player, current_tick)
    elif tab == "my_contracts":
        content = _render_my_contracts(player, current_tick)
    elif tab == "create":
        content = _render_create_form(player)

    return shell(
        "Contracts",
        f"""
        <a href="/p2p/dashboard" style="color: #38bdf8;">&lt;- P2P Dashboard</a>
        <h1>Contracts: Creation &amp; Trading Market</h1>
        {tab_html}
        {content}
        """,
        player.cash_balance,
        player.id
    )


def _render_trading_market(player, current_tick):
    """Render the contract trading market - listed contracts available for bidding."""
    from p2p import get_db, Contract, ContractItem, ContractBid, ContractStatus, BidStatus, DELIVERY_INTERVALS, CONTRACT_LENGTHS
    from auth import get_db as get_auth_db, Player

    db = get_db()
    listed = db.query(Contract).filter(Contract.status == ContractStatus.LISTED).order_by(Contract.listed_at.desc()).all()

    if not listed:
        db.close()
        return """
        <div class="card">
            <h3>Contract Trading Market</h3>
            <p style="color: #64748b;">No contracts currently listed. Be the first to <a href="/p2p/contracts?tab=create">create one</a>!</p>
        </div>
        """

    html = '<h3>Contract Trading Market</h3><p style="color: #64748b; margin-bottom: 16px;">Browse and bid on available contracts. For new listings, bids set the contract terms. For relisted contracts, bids are cash offers to acquire.</p>'

    auth_db = get_auth_db()

    for contract in listed:
        items = db.query(ContractItem).filter(ContractItem.contract_id == contract.id).all()
        is_relist = contract.listing_type == "relist"
        is_price_bid = contract.contract_mode == "price_bid"

        # Sort bids appropriately: price_bid initial = ascending (lowest best), otherwise descending
        if not is_relist and is_price_bid:
            active_bids = db.query(ContractBid).filter(
                ContractBid.contract_id == contract.id,
                ContractBid.status == BidStatus.ACTIVE
            ).order_by(ContractBid.bid_amount.asc()).all()
            best_bid = active_bids[0].bid_amount if active_bids else None
        else:
            active_bids = db.query(ContractBid).filter(
                ContractBid.contract_id == contract.id,
                ContractBid.status == BidStatus.ACTIVE
            ).order_by(ContractBid.bid_amount.desc()).all()
            best_bid = active_bids[0].bid_amount if active_bids else None

        bid_count = len(active_bids)

        lister = auth_db.query(Player).filter(Player.id == contract.lister_id).first()
        lister_name = lister.business_name if lister else "Unknown"

        my_bid = db.query(ContractBid).filter(
            ContractBid.contract_id == contract.id,
            ContractBid.bidder_id == player.id,
            ContractBid.status == BidStatus.ACTIVE
        ).first()

        ticks_left = max(0, contract.bid_end_tick - current_tick) if contract.bid_end_tick else 0
        minutes_left = (ticks_left * 5) / 60

        interval_info = DELIVERY_INTERVALS.get(contract.delivery_interval, {})
        length_info = CONTRACT_LENGTHS.get(contract.contract_length, {})

        # Build items display
        items_html = ""
        for item in items:
            qty_display = f"{item.quantity_per_delivery:.1f}x " if item.quantity_per_delivery > 0 else "(qty set by bid) "
            items_html += f'<span style="display: inline-block; background: #1e293b; padding: 2px 8px; border-radius: 3px; margin: 2px; font-size: 0.8rem;">{qty_display}{format_item_name(item.item_type)}</span>'

        # Mode badge and context-specific info
        if is_relist:
            mode_badge = '<span class="badge" style="background: #f59e0b; color: #020617;">RELIST</span>'
            price_display = f'<span style="color: #22c55e;">${contract.price_per_delivery:,.2f}</span>' if contract.price_per_delivery else "TBD"
            bid_label = "Highest Offer"
            bid_value = f"${best_bid:,.0f}" if best_bid else "No bids"
            bid_hint = "Cash offer ($)"
        elif is_price_bid:
            mode_badge = '<span class="badge" style="background: #c084fc; color: #020617;">PRICE BID</span>'
            price_display = f'Max <span style="color: #f59e0b;">${contract.max_price_per_delivery:,.2f}</span>' if contract.max_price_per_delivery else "No cap"
            bid_label = "Best Price"
            bid_value = f"${best_bid:,.2f}/del" if best_bid else "No bids"
            bid_hint = "Your price ($/delivery)"
        else:
            mode_badge = '<span class="badge" style="background: #38bdf8; color: #020617;">QTY BID</span>'
            price_display = f'<span style="color: #22c55e;">${contract.price_per_delivery:,.2f}</span>'
            bid_label = "Best Qty"
            bid_value = f"{best_bid:,.1f} units" if best_bid else "No bids"
            bid_hint = "Qty per delivery"

        total_value_display = ""
        if contract.price_per_delivery:
            tv = contract.price_per_delivery * contract.total_deliveries
            total_value_display = f'<div><span style="color: #64748b;">Total Value:</span> <span style="color: #22c55e;">${tv:,.2f}</span></div>'

        # Build bid section
        bid_section = ""
        if contract.lister_id == player.id:
            bid_section = '<span style="color: #64748b; font-size: 0.85rem;">Your listing</span>'
        elif my_bid:
            if not is_relist and is_price_bid:
                leading = my_bid.bid_amount <= best_bid if best_bid else True
                my_display = f"${my_bid.bid_amount:,.2f}/del"
                update_hint = "Lower your price"
            elif is_relist:
                leading = my_bid.bid_amount >= best_bid if best_bid else True
                my_display = f"${my_bid.bid_amount:,.0f}"
                update_hint = "Raise offer"
            else:
                leading = my_bid.bid_amount >= best_bid if best_bid else True
                my_display = f"{my_bid.bid_amount:,.1f} units"
                update_hint = "Raise quantity"

            status_color = "#22c55e" if leading else "#f59e0b"
            status_text = "Leading" if leading else "Outbid"
            bid_section = f'''
            <div style="font-size: 0.85rem; color: {status_color}; margin-bottom: 8px;">Your bid: {my_display} ({status_text})</div>
            <form action="/p2p/contracts/bid" method="post">
                <input type="hidden" name="contract_id" value="{contract.id}">
                <div style="display: flex; gap: 4px; align-items: center;">
                    <input type="number" name="bid_amount" step="any" placeholder="{update_hint}" required style="width: 120px; font-size: 0.8rem;">
                    <button type="submit" class="btn-orange" style="font-size: 0.75rem;">Update</button>
                </div>
            </form>
            '''
        else:
            default_val = ""
            if not is_relist and is_price_bid and contract.max_price_per_delivery:
                default_val = f' value="{contract.max_price_per_delivery:.2f}"'
            elif contract.minimum_bid > 0:
                default_val = f' value="{contract.minimum_bid:.0f}"'
            bid_section = f'''
            <form action="/p2p/contracts/bid" method="post">
                <input type="hidden" name="contract_id" value="{contract.id}">
                <div style="font-size: 0.75rem; color: #64748b; margin-bottom: 4px;">{bid_hint}</div>
                <input type="number" name="bid_amount" step="any" required{default_val} style="width: 120px; font-size: 0.8rem;">
                <button type="submit" class="btn-blue" style="margin-top: 6px;">Place Bid</button>
            </form>
            '''

        html += f'''
        <div class="card" style="border-color: #1e293b;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px;">
                <div style="flex: 1; min-width: 200px;">
                    <h4 style="margin: 0;">Contract #{contract.id} {mode_badge}</h4>
                    <p style="color: #64748b; font-size: 0.85rem; margin: 4px 0;">Listed by: {lister_name}</p>
                    <div style="margin: 8px 0;">
                        <span style="color: #64748b; font-size: 0.8rem;">Items per delivery:</span><br>
                        {items_html}
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 0.85rem; margin-top: 8px;">
                        <div><span style="color: #64748b;">Interval:</span> {interval_info.get("label", contract.delivery_interval)}</div>
                        <div><span style="color: #64748b;">Length:</span> {length_info.get("label", contract.contract_length)}</div>
                        <div><span style="color: #64748b;">Per Delivery:</span> {price_display}</div>
                        {total_value_display}
                    </div>
                </div>
                <div style="text-align: right; min-width: 160px;">
                    <div style="font-size: 0.85rem; color: #64748b; margin-bottom: 4px;">
                        {bid_label}: <span style="color: #f59e0b; font-weight: bold;">{bid_value}</span> ({bid_count} bid{"s" if bid_count != 1 else ""})
                    </div>
                    <div style="font-size: 0.85rem; color: #64748b; margin-bottom: 10px;">
                        Closes in: <span style="color: #e5e7eb;">{minutes_left:.0f} min</span>
                    </div>
                    {bid_section}
                </div>
            </div>
        </div>
        '''

    auth_db.close()
    db.close()
    return html


def _render_my_contracts(player, current_tick):
    """Render the player's contracts (created, holding, buying)."""
    from p2p import (
        get_db, Contract, ContractItem, ContractBid, ContractStatus, BidStatus,
        DELIVERY_INTERVALS, CONTRACT_LENGTHS, DELIVERY_GRACE_PERIOD,
        BREACH_PENALTY_GOV_PCT, BREACH_PENALTY_DAMAGED_PCT,
        BID_DURATION_OPTIONS, RELIST_FEE
    )
    from auth import get_db as get_auth_db, Player

    db = get_db()
    auth_db = get_auth_db()

    as_buyer = db.query(Contract).filter(Contract.buyer_id == player.id).order_by(Contract.created_at.desc()).all()
    as_holder = db.query(Contract).filter(Contract.holder_id == player.id).order_by(Contract.created_at.desc()).all()
    drafts = db.query(Contract).filter(
        Contract.creator_id == player.id,
        Contract.status == ContractStatus.DRAFT
    ).order_by(Contract.created_at.desc()).all()

    html = '<h3>My Contracts</h3>'

    # Drafts
    if drafts:
        html += '<h4 style="color: #f59e0b; margin-top: 20px;">Drafts (Not Yet Listed)</h4>'
        for contract in drafts:
            items = db.query(ContractItem).filter(ContractItem.contract_id == contract.id).all()
            interval_info = DELIVERY_INTERVALS.get(contract.delivery_interval, {})
            length_info = CONTRACT_LENGTHS.get(contract.contract_length, {})
            is_price_bid = contract.contract_mode == "price_bid"

            if is_price_bid:
                mode_label = "Price Bid"
                items_html = ", ".join([f"{i.quantity_per_delivery:.1f}x {format_item_name(i.item_type)}" for i in items])
                terms_html = f'Max Price: <span style="color: #f59e0b;">${contract.max_price_per_delivery:,.2f}</span>/delivery' if contract.max_price_per_delivery else ""
                min_bid_label = "Min Price ($/del)"
            else:
                mode_label = "Quantity Bid"
                items_html = ", ".join([format_item_name(i.item_type) for i in items])
                terms_html = f'Price: <span style="color: #22c55e;">${contract.price_per_delivery:,.2f}</span>/delivery'
                min_bid_label = "Min Qty (units)"

            bid_dur_options = "".join([f'<option value="{k}">{v["label"]}</option>' for k, v in BID_DURATION_OPTIONS.items()])

            html += f'''
            <div class="card" style="border-color: #f59e0b;">
                <h4>Contract #{contract.id} <span class="badge" style="background: #f59e0b; color: #020617;">DRAFT</span> <span class="badge">{mode_label}</span></h4>
                <p style="font-size: 0.85rem;"><span style="color: #64748b;">Items:</span> {items_html}</p>
                <p style="font-size: 0.85rem;">
                    <span style="color: #64748b;">Interval:</span> {interval_info.get("label", "")} |
                    <span style="color: #64748b;">Length:</span> {length_info.get("label", "")} |
                    {terms_html}
                </p>
                <form action="/p2p/contracts/list" method="post" style="margin-top: 8px;">
                    <input type="hidden" name="contract_id" value="{contract.id}">
                    <div style="display: flex; gap: 8px; align-items: end; flex-wrap: wrap; margin-bottom: 8px;">
                        <div>
                            <label style="font-size: 0.75rem; color: #64748b;">Bid Duration</label>
                            <select name="bid_duration" style="font-size: 0.85rem;">{bid_dur_options}</select>
                        </div>
                        <div>
                            <label style="font-size: 0.75rem; color: #64748b;">{min_bid_label}</label>
                            <input type="number" name="minimum_bid" min="0" step="any" value="0" style="width: 100px; font-size: 0.85rem;">
                        </div>
                        <button type="submit" class="btn-blue">List on Market</button>
                    </div>
                </form>
            </div>
            '''

    # My listings
    my_listings = db.query(Contract).filter(
        Contract.lister_id == player.id,
        Contract.status == ContractStatus.LISTED
    ).order_by(Contract.listed_at.desc()).all()

    if my_listings:
        html += '<h4 style="color: #38bdf8; margin-top: 20px;">My Active Listings</h4>'
        for contract in my_listings:
            items = db.query(ContractItem).filter(ContractItem.contract_id == contract.id).all()
            bid_count = db.query(ContractBid).filter(
                ContractBid.contract_id == contract.id,
                ContractBid.status == BidStatus.ACTIVE
            ).count()
            ticks_left = max(0, contract.bid_end_tick - current_tick) if contract.bid_end_tick else 0
            minutes_left = (ticks_left * 5) / 60
            items_html = ", ".join([f"{format_item_name(i.item_type)}" for i in items])
            listing_type = "Relist" if contract.listing_type == "relist" else contract.contract_mode.replace("_", " ").title()

            html += f'''
            <div class="card" style="border-color: #38bdf8;">
                <h4>Contract #{contract.id} <span class="badge" style="background: #38bdf8; color: #020617;">LISTED</span> <span class="badge">{listing_type}</span></h4>
                <p style="font-size: 0.85rem;"><span style="color: #64748b;">Items:</span> {items_html}</p>
                <p style="font-size: 0.85rem;">
                    {bid_count} bid{"s" if bid_count != 1 else ""} |
                    Closes in: {minutes_left:.0f} min
                </p>
            </div>
            '''

    # Active - Buyer
    active_buying = [c for c in as_buyer if c.status == ContractStatus.ACTIVE]
    if active_buying:
        html += '<h4 style="color: #22c55e; margin-top: 20px;">Active Contracts (Receiving Deliveries)</h4>'
        for contract in active_buying:
            items = db.query(ContractItem).filter(ContractItem.contract_id == contract.id).all()
            holder = auth_db.query(Player).filter(Player.id == contract.holder_id).first()
            holder_name = holder.business_name if holder else "Unknown"
            ticks_until_next = max(0, contract.next_delivery_tick - current_tick) if contract.next_delivery_tick else 0
            mins_until_next = (ticks_until_next * 5) / 60
            progress_pct = (contract.deliveries_completed / contract.total_deliveries * 100) if contract.total_deliveries > 0 else 0
            items_html = ", ".join([f"{i.quantity_per_delivery:.1f}x {format_item_name(i.item_type)}" for i in items])
            price = contract.price_per_delivery or 0

            html += f'''
            <div class="card" style="border-color: #22c55e;">
                <h4>Contract #{contract.id} <span class="badge" style="background: #22c55e; color: #020617;">ACTIVE - BUYER</span></h4>
                <p style="font-size: 0.85rem;"><span style="color: #64748b;">Holder:</span> {holder_name} | <span style="color: #64748b;">Items:</span> {items_html}</p>
                <p style="font-size: 0.85rem;">
                    Deliveries: {contract.deliveries_completed}/{contract.total_deliveries} |
                    Next in: {mins_until_next:.0f} min |
                    Payment: <span style="color: #ef4444;">${price:,.2f}/delivery</span>
                </p>
                <div class="progress" style="margin-top: 8px;">
                    <div class="progress-bar" style="width: {progress_pct:.0f}%; background: #22c55e;"></div>
                </div>
            </div>
            '''

    # Active - Holder
    active_holding = [c for c in as_holder if c.status == ContractStatus.ACTIVE]
    if active_holding:
        html += '<h4 style="color: #c084fc; margin-top: 20px;">Active Contracts (Fulfilling Deliveries)</h4>'
        for contract in active_holding:
            items = db.query(ContractItem).filter(ContractItem.contract_id == contract.id).all()
            buyer = auth_db.query(Player).filter(Player.id == contract.buyer_id).first()
            buyer_name = buyer.business_name if buyer else "Unknown"
            ticks_until_next = max(0, contract.next_delivery_tick - current_tick) if contract.next_delivery_tick else 0
            mins_until_next = (ticks_until_next * 5) / 60
            progress_pct = (contract.deliveries_completed / contract.total_deliveries * 100) if contract.total_deliveries > 0 else 0
            items_html = ", ".join([f"{i.quantity_per_delivery:.1f}x {format_item_name(i.item_type)}" for i in items])
            price = contract.price_per_delivery or 0
            relist_dur_options = "".join([f'<option value="{k}">{v["label"]}</option>' for k, v in BID_DURATION_OPTIONS.items()])

            html += f'''
            <div class="card" style="border-color: #c084fc;">
                <h4>Contract #{contract.id} <span class="badge" style="background: #c084fc; color: #020617;">ACTIVE - HOLDER</span></h4>
                <p style="font-size: 0.85rem;"><span style="color: #64748b;">Buyer:</span> {buyer_name} | <span style="color: #64748b;">Items:</span> {items_html}</p>
                <p style="font-size: 0.85rem;">
                    Deliveries: {contract.deliveries_completed}/{contract.total_deliveries} |
                    Next due in: {mins_until_next:.0f} min |
                    Payment: <span style="color: #22c55e;">${price:,.2f}/delivery</span>
                </p>
                <div class="progress" style="margin-top: 8px;">
                    <div class="progress-bar" style="width: {progress_pct:.0f}%; background: #c084fc;"></div>
                </div>
                <details style="margin-top: 12px;">
                    <summary style="color: #f59e0b; cursor: pointer; font-size: 0.85rem;">Relist Contract (${RELIST_FEE:,.0f} fee)</summary>
                    <form action="/p2p/contracts/relist" method="post" style="margin-top: 8px;">
                        <input type="hidden" name="contract_id" value="{contract.id}">
                        <div style="display: flex; gap: 8px; align-items: end; flex-wrap: wrap; margin-bottom: 8px;">
                            <div>
                                <label style="font-size: 0.75rem; color: #64748b;">Bid Duration</label>
                                <select name="bid_duration" style="font-size: 0.85rem;">{relist_dur_options}</select>
                            </div>
                            <div>
                                <label style="font-size: 0.75rem; color: #64748b;">Min Bid ($)</label>
                                <input type="number" name="minimum_bid" min="0" step="1" value="0" style="width: 100px; font-size: 0.85rem;">
                            </div>
                            <button type="submit" class="btn-orange">Relist (${RELIST_FEE:,.0f})</button>
                        </div>
                        <p style="font-size: 0.75rem; color: #64748b;">Relisting pauses deliveries and puts the contract back on the market for cash bids. Fee paid to Government.</p>
                    </form>
                </details>
            </div>
            '''

    # Completed
    completed = db.query(Contract).filter(
        ((Contract.buyer_id == player.id) | (Contract.holder_id == player.id)),
        Contract.status == ContractStatus.COMPLETED
    ).order_by(Contract.completed_at.desc()).limit(10).all()
    if completed:
        html += '<h4 style="color: #64748b; margin-top: 20px;">Completed Contracts (Last 10)</h4>'
        for contract in completed:
            role = "Buyer" if contract.buyer_id == player.id else "Holder"
            tv = (contract.price_per_delivery or 0) * contract.total_deliveries
            html += f'''
            <div class="card" style="border-color: #475569; opacity: 0.8;">
                <p style="font-size: 0.85rem;">
                    Contract #{contract.id} | Role: {role} | {contract.deliveries_completed} deliveries | Total: ${tv:,.2f}
                    <span class="badge" style="background: #22c55e; color: #020617;">COMPLETED</span>
                </p>
            </div>
            '''

    # Breached
    breached = db.query(Contract).filter(
        ((Contract.buyer_id == player.id) | (Contract.holder_id == player.id) | (Contract.creator_id == player.id)),
        Contract.status == ContractStatus.BREACHED
    ).order_by(Contract.breached_at.desc()).limit(10).all()
    if breached:
        html += '<h4 style="color: #ef4444; margin-top: 20px;">Breached Contracts</h4>'
        for contract in breached:
            breacher_label = '<span style="color: #ef4444;">(You breached)</span>' if contract.breached_by == player.id else '<span style="color: #22c55e;">(Other party breached)</span>'
            tv = (contract.price_per_delivery or 0) * contract.total_deliveries
            penalty = tv * (BREACH_PENALTY_GOV_PCT + BREACH_PENALTY_DAMAGED_PCT)
            html += f'''
            <div class="card" style="border-color: #ef4444; opacity: 0.8;">
                <p style="font-size: 0.85rem;">
                    Contract #{contract.id} | {breacher_label} | Penalty: <span style="color: #ef4444;">${penalty:,.2f}</span> | Reason: {contract.breach_reason or "N/A"}
                    <span class="badge" style="background: #ef4444;">BREACHED</span>
                </p>
            </div>
            '''

    if not drafts and not my_listings and not active_buying and not active_holding and not completed and not breached:
        html += '<div class="card"><p style="color: #64748b;">No contracts yet. <a href="/p2p/contracts?tab=create">Create your first contract</a>!</p></div>'

    auth_db.close()
    db.close()
    return html


def _render_create_form(player):
    """Render the contract creation form with two modes."""
    from p2p import DELIVERY_INTERVALS, CONTRACT_LENGTHS, BREACH_PENALTY_GOV_PCT, BREACH_PENALTY_DAMAGED_PCT
    import inventory as inv_mod

    item_options = ""
    if inv_mod.ITEM_RECIPES:
        for key in sorted(inv_mod.ITEM_RECIPES.keys()):
            info = inv_mod.ITEM_RECIPES[key]
            item_options += f'<option value="{key}">{info.get("name", format_item_name(key))}</option>'
    else:
        item_options = '<option value="">No items available</option>'

    interval_options = ""
    for key, info in DELIVERY_INTERVALS.items():
        interval_options += f'<option value="{key}">{info["label"]}</option>'

    length_options = ""
    for key, info in CONTRACT_LENGTHS.items():
        length_options += f'<option value="{key}">{info["label"]}</option>'

    penalty_pct = int((BREACH_PENALTY_GOV_PCT + BREACH_PENALTY_DAMAGED_PCT) * 100)

    return f'''
    <h3>Create New Contract</h3>

    <div class="card" style="border-color: #ef4444; background: #1a0a0a; margin-bottom: 16px;">
        <h4 style="color: #ef4444; margin: 0 0 8px 0;">Breach of Contract Warning</h4>
        <p style="font-size: 0.85rem; color: #fca5a5;">
            If either party breaches (holder fails to deliver or buyer fails to pay),
            the breaching party owes <strong>{penalty_pct}% of the total contract value</strong>:
            {int(BREACH_PENALTY_GOV_PCT * 100)}% to the Government, {int(BREACH_PENALTY_DAMAGED_PCT * 100)}% to the damaged party. Contract voided.
        </p>
    </div>

    <!-- PRICE BID MODE -->
    <div class="card" style="border-color: #c084fc; margin-bottom: 16px;">
        <h4 style="color: #c084fc; margin-top: 0;">Price Bid Contract</h4>
        <p style="color: #64748b; font-size: 0.85rem; margin-bottom: 12px;">
            You define <strong>what items and quantities</strong> you need delivered, and set a <strong>max price</strong> you'll pay per delivery.
            Bidders compete by offering <strong>lower prices</strong>. Lowest bid wins.
        </p>

        <form action="/p2p/contracts/create-price-bid" method="post">
            <h4 style="font-size: 0.9rem;">Delivery Items (1-3 per delivery)</h4>

            <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 8px; margin-bottom: 12px;">
                <div>
                    <label style="font-size: 0.8rem; color: #64748b;">Item 1 (required)</label>
                    <select name="item_1" required style="width: 100%;">{item_options}</select>
                </div>
                <div>
                    <label style="font-size: 0.8rem; color: #64748b;">Quantity</label>
                    <input type="number" name="qty_1" min="1" step="1" value="10" required style="width: 100%;">
                </div>
            </div>
            <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 8px; margin-bottom: 12px;">
                <div>
                    <label style="font-size: 0.8rem; color: #64748b;">Item 2 (optional)</label>
                    <select name="item_2" style="width: 100%;"><option value="">-- None --</option>{item_options}</select>
                </div>
                <div>
                    <label style="font-size: 0.8rem; color: #64748b;">Quantity</label>
                    <input type="number" name="qty_2" min="1" step="1" style="width: 100%;">
                </div>
            </div>
            <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 8px; margin-bottom: 16px;">
                <div>
                    <label style="font-size: 0.8rem; color: #64748b;">Item 3 (optional)</label>
                    <select name="item_3" style="width: 100%;"><option value="">-- None --</option>{item_options}</select>
                </div>
                <div>
                    <label style="font-size: 0.8rem; color: #64748b;">Quantity</label>
                    <input type="number" name="qty_3" min="1" step="1" style="width: 100%;">
                </div>
            </div>

            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; margin-bottom: 16px;">
                <div>
                    <label style="font-size: 0.8rem; color: #64748b;">Delivery Interval</label>
                    <select name="delivery_interval" required style="width: 100%;">{interval_options}</select>
                </div>
                <div>
                    <label style="font-size: 0.8rem; color: #64748b;">Contract Length</label>
                    <select name="contract_length" required style="width: 100%;">{length_options}</select>
                </div>
                <div>
                    <label style="font-size: 0.8rem; color: #c084fc;">Max Price per Delivery ($)</label>
                    <input type="number" name="max_price" min="1" step="0.01" value="1000" required style="width: 100%;">
                </div>
            </div>
            <button type="submit" class="btn-blue" style="padding: 10px 24px; font-size: 0.95rem;">Create Price Bid Draft</button>
        </form>
    </div>

    <!-- QUANTITY BID MODE -->
    <div class="card" style="border-color: #38bdf8;">
        <h4 style="color: #38bdf8; margin-top: 0;">Quantity Bid Contract</h4>
        <p style="color: #64748b; font-size: 0.85rem; margin-bottom: 12px;">
            You set a <strong>fixed price per delivery</strong> and choose an <strong>item type</strong>.
            Bidders compete by offering <strong>more quantity</strong> per delivery. Highest quantity bid wins.
        </p>

        <form action="/p2p/contracts/create-quantity-bid" method="post">
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 16px;">
                <div>
                    <label style="font-size: 0.8rem; color: #64748b;">Item Type</label>
                    <select name="item_type" required style="width: 100%;">{item_options}</select>
                </div>
                <div>
                    <label style="font-size: 0.8rem; color: #38bdf8;">Fixed Price per Delivery ($)</label>
                    <input type="number" name="price_per_delivery" min="1" step="0.01" value="5000" required style="width: 100%;">
                </div>
            </div>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 16px;">
                <div>
                    <label style="font-size: 0.8rem; color: #64748b;">Delivery Interval</label>
                    <select name="delivery_interval" required style="width: 100%;">{interval_options}</select>
                </div>
                <div>
                    <label style="font-size: 0.8rem; color: #64748b;">Contract Length</label>
                    <select name="contract_length" required style="width: 100%;">{length_options}</select>
                </div>
            </div>
            <button type="submit" class="btn-blue" style="padding: 10px 24px; font-size: 0.95rem;">Create Quantity Bid Draft</button>
        </form>
    </div>
    '''


# ==========================
# CONTRACT ACTIONS
# ==========================

@router.post("/p2p/contracts/create-price-bid", response_class=HTMLResponse)
def create_price_bid_action(
    session_token: Optional[str] = Cookie(None),
    item_1: str = Form(...),
    qty_1: float = Form(...),
    item_2: str = Form(""),
    qty_2: float = Form(0),
    item_3: str = Form(""),
    qty_3: float = Form(0),
    delivery_interval: str = Form(...),
    contract_length: str = Form(...),
    max_price: float = Form(...),
):
    """Create a Price Bid contract draft."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player

    access_redirect = require_p2p_access(player)
    if access_redirect:
        return access_redirect

    from p2p import create_contract_price_bid

    items = [{"item_type": item_1, "quantity": qty_1}]
    if item_2 and qty_2 > 0:
        items.append({"item_type": item_2, "quantity": qty_2})
    if item_3 and qty_3 > 0:
        items.append({"item_type": item_3, "quantity": qty_3})

    contract_id = create_contract_price_bid(
        creator_id=player.id,
        items=items,
        delivery_interval=delivery_interval,
        contract_length=contract_length,
        max_price=max_price,
    )

    if not contract_id:
        return shell(
            "Contract Error",
            """
            <a href="/p2p/contracts?tab=create" style="color: #38bdf8;">&lt;- Back</a>
            <div class="card" style="border-color: #ef4444;">
                <h3 style="color: #ef4444;">Contract Creation Failed</h3>
                <p>Invalid contract parameters. Check your items, interval, length, and price.</p>
            </div>
            """,
            player.cash_balance,
            player.id
        )

    return RedirectResponse(url="/p2p/contracts?tab=my_contracts", status_code=303)


@router.post("/p2p/contracts/create-quantity-bid", response_class=HTMLResponse)
def create_quantity_bid_action(
    session_token: Optional[str] = Cookie(None),
    item_type: str = Form(...),
    price_per_delivery: float = Form(...),
    delivery_interval: str = Form(...),
    contract_length: str = Form(...),
):
    """Create a Quantity Bid contract draft."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player

    access_redirect = require_p2p_access(player)
    if access_redirect:
        return access_redirect

    from p2p import create_contract_quantity_bid

    contract_id = create_contract_quantity_bid(
        creator_id=player.id,
        item_type=item_type,
        delivery_interval=delivery_interval,
        contract_length=contract_length,
        price_per_delivery=price_per_delivery,
    )

    if not contract_id:
        return shell(
            "Contract Error",
            """
            <a href="/p2p/contracts?tab=create" style="color: #38bdf8;">&lt;- Back</a>
            <div class="card" style="border-color: #ef4444;">
                <h3 style="color: #ef4444;">Contract Creation Failed</h3>
                <p>Invalid contract parameters. Check your item, interval, length, and price.</p>
            </div>
            """,
            player.cash_balance,
            player.id
        )

    return RedirectResponse(url="/p2p/contracts?tab=my_contracts", status_code=303)


@router.post("/p2p/contracts/list", response_class=HTMLResponse)
def list_contract_action(
    session_token: Optional[str] = Cookie(None),
    contract_id: int = Form(...),
    minimum_bid: float = Form(0),
    bid_duration: str = Form("6h"),
):
    """List a draft contract on the trading market."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player

    access_redirect = require_p2p_access(player)
    if access_redirect:
        return access_redirect

    from p2p import list_contract

    success = list_contract(contract_id, player.id, minimum_bid=minimum_bid, bid_duration=bid_duration)
    if not success:
        return shell(
            "Listing Error",
            """
            <a href="/p2p/contracts?tab=my_contracts" style="color: #38bdf8;">&lt;- Back</a>
            <div class="card" style="border-color: #ef4444;">
                <h3 style="color: #ef4444;">Listing Failed</h3>
                <p>Could not list this contract. It may not exist, not be yours, or not be in draft status.</p>
            </div>
            """,
            player.cash_balance,
            player.id
        )

    return RedirectResponse(url="/p2p/contracts?tab=my_contracts", status_code=303)


@router.post("/p2p/contracts/bid", response_class=HTMLResponse)
def bid_contract_action(
    session_token: Optional[str] = Cookie(None),
    contract_id: int = Form(...),
    bid_amount: float = Form(...),
):
    """Place a bid on a listed contract."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player

    access_redirect = require_p2p_access(player)
    if access_redirect:
        return access_redirect

    from p2p import place_bid

    error = place_bid(contract_id, player.id, bid_amount)
    if error:
        return shell(
            "Bid Error",
            f"""
            <a href="/p2p/contracts?tab=market" style="color: #38bdf8;">&lt;- Back</a>
            <div class="card" style="border-color: #ef4444;">
                <h3 style="color: #ef4444;">Bid Failed</h3>
                <p>{error}</p>
            </div>
            """,
            player.cash_balance,
            player.id
        )

    return RedirectResponse(url="/p2p/contracts?tab=market", status_code=303)


@router.post("/p2p/contracts/relist", response_class=HTMLResponse)
def relist_contract_action(
    session_token: Optional[str] = Cookie(None),
    contract_id: int = Form(...),
    minimum_bid: float = Form(0),
    bid_duration: str = Form("6h"),
):
    """Relist an active contract the player holds."""
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player

    access_redirect = require_p2p_access(player)
    if access_redirect:
        return access_redirect

    from p2p import relist_contract, RELIST_FEE

    error = relist_contract(contract_id, player.id, minimum_bid=minimum_bid, bid_duration=bid_duration)
    if error:
        return shell(
            "Relist Error",
            f"""
            <a href="/p2p/contracts?tab=my_contracts" style="color: #38bdf8;">&lt;- Back</a>
            <div class="card" style="border-color: #ef4444;">
                <h3 style="color: #ef4444;">Relist Failed</h3>
                <p>{error}</p>
            </div>
            """,
            player.cash_balance,
            player.id
        )

    return RedirectResponse(url="/p2p/contracts?tab=my_contracts", status_code=303)
