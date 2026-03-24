"""
tutorial_ux.py

Startup Company Tutorial for Wadsworth.
Guides new players through core game mechanics in 11 steps.

Tutorial is triggered when a player has:
  - No businesses
  - Only starter inventory (tutorial_step == 0)

Steps:
  0  - Not started (banner shown on dashboard)
  1  - Welcome message
  2  - Land page: build Water Treatment Facility
  3  - Inventory page: see water from facility
  4  - Land page: build Plantation + Grocery Store
  5  - Inventory page: full resource overview
  6  - Production costs page: apple costs explained
  7  - Market page: wait for apple, list it for sale
  8  - Stats/business/free_range_pasture: production chains
  9  - Reward: claim free tax-exempt plot (choose terrain)
  10 - Land market: locations & proximities explained
  11 - Executives: watch video + claim free First Lady executive
  12 - Complete (unlocked)
"""

from typing import Optional
from fastapi import APIRouter, Cookie, Form
from fastapi.responses import HTMLResponse, RedirectResponse

router = APIRouter()

# ==========================
# TUTORIAL STEP DEFINITIONS
# ==========================

TOTAL_STEPS = 11

STEP_REDIRECT = {
    1: "/",          # Welcome on dashboard
    2: "/land",      # Build water facility
    3: "/inventory", # See water
    4: "/land",      # Build plantation + grocery store
    5: "/inventory", # Resource overview
    6: "/stats/production-costs?category=produce",  # Apple costs
    7: "/market?item=apples",  # List apple for sale
    8: "/stats/business/free_range_pasture",  # Production chain demo
    9: "/",          # Reward (dashboard) — player claims via form
    10: "/land-market",  # Land market explanation
    11: "/",         # Executives video + First Lady reward
    12: "/",         # Tutorial complete
}

TERRAIN_OPTIONS = [
    ("prairie", "Prairie — Flat grassland, perfect for farming and diverse businesses"),
    ("forest",  "Forest — Wooded area, excellent for lumber and nature-based industry"),
    ("desert",  "Desert — Arid land, ideal for solar plants and mining operations"),
    ("marsh",   "Marsh — Wetland terrain, unique for water and specialized production"),
    ("mountain","Mountain — Rocky highlands with strong mining and refinery potential"),
    ("tundra",  "Tundra — Cold climate terrain with unique cold-weather production"),
    ("savanna", "Savanna — Tropical grassland great for animal pastures and plantations"),
    ("hills",   "Hills — Rolling terrain supporting a wide variety of businesses"),
    ("island",  "Island — Isolated landmass with coastal access and premium appeal"),
    ("jungle",  "Jungle — Dense vegetation with exotic resources and unique production"),
    ("coastal", "Coastal — Shoreline with ocean access, ideal for fishing and trade"),
    ("lake",    "Lake — Freshwater terrain, excellent for fishing and aquaculture"),
]

ALL_PROXIMITY_FEATURES = "urban,coastal,riverside,lakeside,oasis,hot_springs,caves,volcanic,road,deposits"

# ==========================
# STATE HELPERS
# ==========================

def get_tutorial_step(player_id: int) -> int:
    """Return the player's current tutorial step (0-12)."""
    try:
        from auth import get_db, Player
        db = get_db()
        player = db.query(Player).filter(Player.id == player_id).first()
        db.close()
        if player is None:
            return 0
        step = getattr(player, "tutorial_step", 0)
        return step if step is not None else 0
    except Exception as e:
        print(f"[Tutorial] get_tutorial_step error: {e}")
        return 0


def set_tutorial_step(player_id: int, step: int):
    """Set the player's tutorial step."""
    try:
        from auth import get_db, Player
        db = get_db()
        player = db.query(Player).filter(Player.id == player_id).first()
        if player:
            player.tutorial_step = step
            db.commit()
        db.close()
    except Exception as e:
        print(f"[Tutorial] set_tutorial_step error: {e}")


def player_has_businesses(player_id: int) -> bool:
    """Return True if the player owns at least one business."""
    try:
        from business import Business
        from land import get_db as get_land_db
        db = get_land_db()
        count = db.query(Business).filter(Business.owner_id == player_id).count()
        db.close()
        return count > 0
    except Exception as e:
        print(f"[Tutorial] player_has_businesses error: {e}")
        return True  # Assume has businesses on error to avoid spurious banners


def player_has_only_starter_inventory(player_id: int) -> bool:
    """
    Return True if the player's inventory is only starter items
    (no items beyond what was given at account creation).
    """
    try:
        from market import STARTER_INVENTORY
        import inventory as inv_mod
        inv = inv_mod.get_player_inventory(player_id)
        starter_keys = set(STARTER_INVENTORY.keys())
        for item_type in inv:
            if item_type not in starter_keys:
                return False
        return True
    except Exception as e:
        print(f"[Tutorial] player_has_only_starter_inventory error: {e}")
        return False


def should_show_tutorial_banner(player) -> bool:
    """Return True if the tutorial banner should be displayed on the dashboard."""
    step = getattr(player, "tutorial_step", 0)
    if step is None:
        step = 0
    if step != 0:
        return False
    return not player_has_businesses(player.id) and player_has_only_starter_inventory(player.id)


def player_has_business_type(player_id: int, business_type: str) -> bool:
    """Return True if the player owns a business of the given type."""
    try:
        from business import Business
        from land import get_db as get_land_db
        db = get_land_db()
        count = db.query(Business).filter(
            Business.owner_id == player_id,
            Business.business_type == business_type
        ).count()
        db.close()
        return count > 0
    except Exception as e:
        print(f"[Tutorial] player_has_business_type error: {e}")
        return False


def player_has_apple_in_inventory(player_id: int) -> bool:
    """Return True if the player has at least 1 apple in inventory."""
    try:
        import inventory as inv_mod
        inv = inv_mod.get_player_inventory(player_id)
        return inv.get("apples", 0) >= 1
    except Exception:
        return False


def player_has_apple_market_listing(player_id: int) -> bool:
    """Return True if the player has an active or partially-filled SELL order for apples."""
    try:
        from market import MarketOrder, OrderType, OrderStatus, get_db as get_market_db
        db = get_market_db()
        count = db.query(MarketOrder).filter(
            MarketOrder.player_id == player_id,
            MarketOrder.order_type == OrderType.SELL,
            MarketOrder.item_type == "apples",
            MarketOrder.status.in_([OrderStatus.ACTIVE, OrderStatus.PARTIALLY_FILLED]),
        ).count()
        db.close()
        return count > 0
    except Exception as e:
        print(f"[Tutorial] player_has_apple_market_listing error: {e}")
        return False


def create_tutorial_reward_plot(player_id: int, terrain_type: str) -> int:
    """
    Create the tutorial reward land plot for the given player.
    The plot has all proximity features, zero tax, and is_tutorial_reward=True.
    Returns the new plot's ID.
    """
    from land import LandPlot, get_db as get_land_db
    db = get_land_db()
    plot = LandPlot(
        owner_id=player_id,
        terrain_type=terrain_type,
        proximity_features=ALL_PROXIMITY_FEATURES,
        efficiency=100.0,
        size=1.0,
        monthly_tax=0.0,
        is_starter_plot=False,
        is_government_owned=False,
        is_tutorial_reward=True,
    )
    db.add(plot)
    db.commit()
    db.refresh(plot)
    plot_id = plot.id
    db.close()
    print(f"[Tutorial] Created tutorial reward plot #{plot_id} for player {player_id} ({terrain_type})")
    return plot_id


# ==========================
# OVERLAY HTML GENERATOR
# ==========================

def get_tutorial_overlay_html(player, current_page: str) -> str:
    """
    Return the HTML for the tutorial overlay panel.
    `current_page` is one of: 'dashboard', 'land', 'inventory', 'market',
    'production_costs', 'stats_business', 'land_market'.
    Returns empty string if tutorial is not active or if this page is not the
    expected page for the current step.
    """
    step = get_tutorial_step(player.id)
    if step == 0 or step >= 12:
        return ""

    # Only show overlay on the expected page(s) for each step.
    # Values may be a string or a list of strings.
    STEP_PAGE = {
        1: "dashboard",
        2: ["land", "businesses"],  # step 2 shows on land OR businesses
        3: "inventory",
        4: ["land", "businesses"],  # step 4 shows on land OR businesses
        5: "inventory",
        6: "production_costs",
        7: "market",
        8: "stats_business",
        9: "dashboard",
        10: "land_market",
        11: "dashboard",
    }
    expected_page = STEP_PAGE.get(step, "")
    if expected_page:
        allowed = expected_page if isinstance(expected_page, list) else [expected_page]
        if current_page not in allowed:
            return ""

    # ── Step content ──────────────────────────────────────────────

    if step == 1:
        title = "Welcome to Wadsworth!"
        content = f"""
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 14px 0;">
            <strong style="color:#e5e7eb;">Wadsworth</strong> is a real-time multiplayer economic simulation.
            As CEO of <em style="color:#38bdf8;">{player.business_name}</em>, you'll build businesses on
            land plots, produce goods, buy and sell on the open market, and compete against other players
            for economic dominance.
        </p>
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 14px 0;">
            The economy runs on its own — prices shift based on real supply and demand, taxes are charged on
            land, and businesses produce goods on a tick-based cycle (one tick every 5 seconds).
            Everything from farming to luxury manufacturing is possible.
        </p>
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 16px 0;">
            This tutorial will walk you through the essentials. Let's start by visiting your
            <strong style="color:#e5e7eb;">Land Portfolio</strong> and building your first facility.
        </p>
        <form action="/api/tutorial/advance" method="post">
            <button type="submit" style="background:#d4af37;color:#020617;border:none;padding:10px 24px;border-radius:4px;cursor:pointer;font-size:0.9rem;font-weight:bold;">
                OK — Let's Go! →
            </button>
        </form>
        """

    elif step == 2:
        has_wf = player_has_business_type(player.id, "water_facility")
        title = "Your Land Portfolio"

        if current_page == "businesses":
            # Player navigated to /businesses — guide them back to /land to build
            if has_wf:
                _step_hint = (
                    "<div style='background:#052e16;border:1px solid #16a34a;padding:10px 14px;"
                    "border-radius:4px;color:#4ade80;margin-bottom:16px;'>"
                    "✓ Water Treatment Facility built! Head back to "
                    "<a href='/land' style='color:#4ade80;font-weight:bold;'>/land</a>"
                    " and click OK to continue.</div>"
                )
            else:
                _step_hint = (
                    "<p style='color:#94a3b8;'>Your task: build a "
                    "<strong style='color:#38bdf8;'>Water Treatment Facility</strong>"
                    " on one of your vacant plots at "
                    "<a href='/land' style='color:#38bdf8;font-weight:bold;'>/land</a>.</p>"
                )
            content = f"""
            <div style="background:#0a1628;border:1px solid #38bdf8;padding:10px 14px;border-radius:4px;color:#93c5fd;margin-bottom:16px;">
                📍 You're on the <strong>Businesses</strong> dashboard (your active businesses).
                To <em>build</em> new businesses you need to go to your
                <a href="/land" style="color:#38bdf8;font-weight:bold;">Land Portfolio (/land)</a>
                and use the build form on a vacant plot.
            </div>
            {_step_hint}
            """
        else:
            content = f"""
            <p style="color:#94a3b8;line-height:1.7;margin:0 0 12px 0;">
                Every business in Wadsworth needs a <strong style="color:#e5e7eb;">land plot</strong> to operate on.
                You start with <strong style="color:#38bdf8;">3 free Prairie plots</strong> — each one is ready for development.
            </p>
            <p style="color:#94a3b8;line-height:1.7;margin:0 0 12px 0;">
                Different terrain types support different businesses. Prairie land is versatile and supports
                farming, facilities, retail, and more. Each plot also earns a monthly tax bill based on size and proximity.
            </p>
            <p style="color:#94a3b8;line-height:1.7;margin:0 0 16px 0;">
                <strong style="color:#d4af37;">Your task:</strong> Build a
                <strong style="color:#38bdf8;">Water Treatment Facility</strong> on one of your vacant plots below.
                Water is a fundamental resource consumed by nearly every production chain.
            </p>
            {"<div style='background:#052e16;border:1px solid #16a34a;padding:10px 14px;border-radius:4px;color:#4ade80;margin-bottom:16px;'>✓ Water Treatment Facility built! Click OK to continue.</div>" if has_wf else "<div style='background:#1a0d00;border:1px solid #f59e0b;padding:10px 14px;border-radius:4px;color:#fbbf24;margin-bottom:16px;'>Scroll down → select <strong>Water Treatment Facility</strong> from the dropdown → click Build.</div>"}
            {"<form action='/api/tutorial/advance' method='post'><button type='submit' style='background:#d4af37;color:#020617;border:none;padding:10px 24px;border-radius:4px;cursor:pointer;font-size:0.9rem;font-weight:bold;'>OK — Check Inventory →</button></form>" if has_wf else "<span style='color:#64748b;font-size:0.85rem;'>Complete the task above to continue.</span>"}
            """

    elif step == 3:
        title = "Your Inventory"
        content = """
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 12px 0;">
            The <strong style="color:#e5e7eb;">Inventory</strong> page shows every item your company owns —
            raw materials, seeds, processed goods, and finished products.
        </p>
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 12px 0;">
            You started with a supply of <strong style="color:#38bdf8;">Water</strong>, <strong style="color:#f59e0b;">Energy</strong>,
            seeds, and paper. Your Water Treatment Facility will now produce additional water each cycle,
            adding to your reserves automatically.
        </p>
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 16px 0;">
            Use the category tabs above to filter items. Items with market value can be listed for sale directly
            from the Market page. Next, let's expand your production capacity.
        </p>
        <form action="/api/tutorial/advance" method="post">
            <button type="submit" style="background:#d4af37;color:#020617;border:none;padding:10px 24px;border-radius:4px;cursor:pointer;font-size:0.9rem;font-weight:bold;">
                OK — Back to Land →
            </button>
        </form>
        """

    elif step == 4:
        has_plantation = player_has_business_type(player.id, "plantation")
        has_grocery = player_has_business_type(player.id, "grocery_store")
        both_built = has_plantation and has_grocery
        title = "Expand Your Operations"
        status_lines = []
        if has_plantation:
            status_lines.append("<span style='color:#4ade80;'>✓ Mixed Fruit &amp; Vegetable Plantation built</span>")
        else:
            status_lines.append("<span style='color:#fbbf24;'>◻ Build a Mixed Fruit &amp; Vegetable Plantation</span>")
        if has_grocery:
            status_lines.append("<span style='color:#4ade80;'>✓ Local Grocery Store built</span>")
        else:
            status_lines.append("<span style='color:#fbbf24;'>◻ Build a Local Grocery Store</span>")
        status_html = "<br>".join(status_lines)

        if current_page == "businesses":
            # Player navigated to /businesses — guide them back to /land to build
            build_hint = """
            <div style="background:#0a1628;border:1px solid #38bdf8;padding:10px 14px;border-radius:4px;color:#93c5fd;margin-bottom:16px;">
                📍 You're on the <strong>Businesses</strong> dashboard (existing businesses).
                To <em>build</em> new businesses you need to go to your
                <a href="/land" style="color:#38bdf8;font-weight:bold;">Land Portfolio (/land)</a>
                and use the build form on each vacant plot.
            </div>
            """
        else:
            build_hint = "<div style='background:#0f172a;border:1px solid #1e293b;padding:10px 14px;border-radius:4px;color:#64748b;margin-bottom:16px;font-size:0.82rem;'>Use the dropdowns below each vacant plot to select a business type, then click Build.</div>"

        content = f"""
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 12px 0;">
            A <strong style="color:#38bdf8;">Mixed Fruit &amp; Vegetable Plantation</strong> (Production) converts water,
            energy, and seeds into apples and oranges over time. A <strong style="color:#38bdf8;">Local Grocery Store</strong>
            (Retail) then sells those fruits to generate cash revenue.
        </p>
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 12px 0;">
            Together, these form a simple <em>vertical supply chain</em>: you produce the goods yourself
            and control the retail price. More complex chains can span dozens of businesses and item types.
        </p>
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 12px 0;">
            <strong style="color:#d4af37;">Your task:</strong> Build both businesses on vacant plots.
        </p>
        {build_hint}
        <div style="background:#0f172a;border:1px solid #1e293b;padding:10px 14px;border-radius:4px;margin-bottom:16px;line-height:1.9;">
            {status_html}
        </div>
        {"<form action='/api/tutorial/advance' method='post'><button type='submit' style='background:#d4af37;color:#020617;border:none;padding:10px 24px;border-radius:4px;cursor:pointer;font-size:0.9rem;font-weight:bold;'>OK — Review Inventory →</button></form>" if both_built else "<span style='color:#64748b;font-size:0.85rem;'>Build both businesses to continue.</span>"}
        """

    elif step == 5:
        title = "Your Growing Portfolio"
        content = """
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 12px 0;">
            Look at your inventory now. You're holding:
        </p>
        <ul style="color:#94a3b8;line-height:2;margin:0 0 12px 0;padding-left:20px;">
            <li><strong style="color:#38bdf8;">Water</strong> — being produced by your Water Treatment Facility</li>
            <li><strong style="color:#f59e0b;">Energy</strong> — your starter supply, consumed by production</li>
            <li><strong style="color:#22c55e;">Seeds</strong> (apple, orange, and more) — inputs for your Plantation</li>
            <li><strong style="color:#a855f7;">Land</strong> — three plots actively hosting your new businesses</li>
        </ul>
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 12px 0;">
            Your <strong style="color:#e5e7eb;">Plantation</strong> will soon begin producing
            <strong style="color:#84cc16;">Apples</strong> and <strong style="color:#f97316;">Oranges</strong>,
            which your Grocery Store can sell. The more efficiently you manage inputs, the higher your margins.
        </p>
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 16px 0;">
            Next, let's look at what it actually <em>costs</em> to produce an apple — so you know whether to
            source inputs from the market or produce them yourself.
        </p>
        <form action="/api/tutorial/advance" method="post">
            <button type="submit" style="background:#d4af37;color:#020617;border:none;padding:10px 24px;border-radius:4px;cursor:pointer;font-size:0.9rem;font-weight:bold;">
                OK — View Production Costs →
            </button>
        </form>
        """

    elif step == 6:
        title = "Understanding Production Costs"
        content = """
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 12px 0;">
            The <strong style="color:#e5e7eb;">Production Cost Explorer</strong> calculates what each item
            costs to make assuming you produce <em>all inputs yourself</em> — full vertical integration.
            This is your baseline cost floor before any market purchases.
        </p>
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 12px 0;">
            Look at <strong style="color:#84cc16;">Apples</strong> in the table below.
            The listed cost reflects water, energy, seeds, land taxes, and labor — all rolled up into a
            per-unit figure. If the market price for apples is <em>above</em> that cost, selling is profitable.
            If it's below, buying from the market may be cheaper than making them.
        </p>
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 16px 0;">
            Smart players use this screen to identify arbitrage opportunities and set competitive retail prices.
            Now let's visit the open market and learn how to list goods for sale.
        </p>
        <form action="/api/tutorial/advance" method="post">
            <button type="submit" style="background:#d4af37;color:#020617;border:none;padding:10px 24px;border-radius:4px;cursor:pointer;font-size:0.9rem;font-weight:bold;">
                OK — Go to Market →
            </button>
        </form>
        """

    elif step == 7:
        has_apple = player_has_apple_in_inventory(player.id)
        has_listing = player_has_apple_market_listing(player.id)
        title = "The Trading Floor"
        if has_listing:
            action_html = """
            <div style="background:#052e16;border:1px solid #16a34a;padding:10px 14px;border-radius:4px;color:#4ade80;margin-bottom:16px;">
                ✓ Apple listing created! Great work. Click OK to continue.
            </div>
            <form action="/api/tutorial/advance" method="post">
                <button type="submit" style="background:#d4af37;color:#020617;border:none;padding:10px 24px;border-radius:4px;cursor:pointer;font-size:0.9rem;font-weight:bold;">
                    OK — Explore Production Chains →
                </button>
            </form>
            """
        elif has_apple:
            action_html = """
            <div style="background:#0a1628;border:1px solid #d4af37;padding:10px 14px;border-radius:4px;color:#fde68a;margin-bottom:16px;">
                🍎 An apple is ready in your inventory! Now place a <strong>SELL limit order</strong> using the form below.
                Choose a price, enter quantity 1, and submit.
            </div>
            <span style="color:#64748b;font-size:0.85rem;">Place your sell order above to continue.</span>
            """
        else:
            action_html = """
            <div style="background:#0f172a;border:1px solid #1e293b;padding:10px 14px;border-radius:4px;color:#64748b;margin-bottom:16px;" id="tut-apple-wait">
                <span id="tut-apple-status">⏳ Waiting for your Plantation to produce an apple… (checks every 10 sec)</span>
            </div>
            <span style="color:#64748b;font-size:0.85rem;">Your plantation is working — this page will notify you when an apple is ready.</span>
            <script>
            (function() {
                var interval = setInterval(function() {
                    fetch('/api/tutorial/check-apple')
                        .then(function(r) { return r.json(); })
                        .then(function(d) {
                            if (d.has_apple) {
                                clearInterval(interval);
                                document.getElementById('tut-apple-status').innerHTML =
                                    '🍎 Apple ready! Scroll up and place a SELL limit order for apples.';
                                document.getElementById('tut-apple-wait').style.borderColor = '#d4af37';
                                document.getElementById('tut-apple-wait').style.color = '#fde68a';
                            }
                        }).catch(function() {});
                }, 10000);
            })();
            </script>
            """

        content = f"""
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 12px 0;">
            The <strong style="color:#e5e7eb;">Market</strong> is where players buy and sell goods with each other.
            It uses a <em>limit order book</em>: you set a price, and the system automatically matches your order
            with the best available counter-offer. Orders can sit open until filled or cancelled.
        </p>
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 12px 0;">
            Browse items using the category tabs on the left. Click any item to view its live order book —
            bids (buy orders) on one side, asks (sell orders) on the other. The spread between them is
            where profit lives.
        </p>
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 12px 0;">
            <strong style="color:#d4af37;">Your task:</strong> Wait for your Plantation to produce an apple,
            then list it for sale using the order form. The market is currently showing <strong style="color:#84cc16;">Apples</strong>.
        </p>
        {action_html}
        """

    elif step == 8:
        title = "The Depth of Production"
        content = """
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 12px 0;">
            Look at the <strong style="color:#e5e7eb;">Animal Pasture</strong> (Free Range Pasture) production lines below.
            To produce <strong style="color:#eab308;">horses</strong>, this business requires
            <strong style="color:#84cc16;">apples</strong> as a feed input — among other things.
        </p>
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 12px 0;">
            This is a glimpse of <em>multi-layer supply chains</em>: your Plantation produces apples →
            apples feed an Animal Pasture → the Pasture produces horses → horses can be sold at market
            or used in even further downstream businesses.
        </p>
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 12px 0;">
            With <strong style="color:#e5e7eb;">106 business types</strong> available, you can build anything
            from a bakery sourcing wheat from your own fields, to a luxury auto plant sourcing steel from
            your own refinery. The deeper your integration, the greater your margin.
        </p>
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 16px 0;">
            You've completed all the core lessons. Time to collect your reward!
        </p>
        <form action="/api/tutorial/advance" method="post">
            <button type="submit" style="background:#d4af37;color:#020617;border:none;padding:10px 24px;border-radius:4px;cursor:pointer;font-size:0.9rem;font-weight:bold;">
                OK — Claim My Reward →
            </button>
        </form>
        """

    elif step == 9:
        title = "Level 1 Complete — Claim Your Reward!"
        already_has_plot = _has_tutorial_reward_plot(player.id)
        if already_has_plot:
            content = """
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 12px 0;">
            You've replayed Tutorial 1 — great job going through it again!
        </p>
        <div style="background:rgba(74,222,128,0.08);border:1px solid rgba(74,222,128,0.3);
                    border-radius:6px;padding:12px 16px;margin-bottom:16px;">
            <strong style="color:#4ade80;">&#10003; Reward already claimed</strong>
            <p style="color:#94a3b8;font-size:0.85rem;margin:6px 0 0;">
                Your tax-free land plot is already in your portfolio.
                Replaying a tutorial doesn't grant a second reward.
            </p>
        </div>
        <form action="/api/tutorial/claim-reward" method="post"
              style="display:flex;gap:12px;align-items:center;flex-wrap:wrap;">
            <input type="hidden" name="terrain_type" value="prairie">
            <button type="submit" style="background:#d4af37;color:#020617;border:none;padding:10px 24px;
                    border-radius:4px;cursor:pointer;font-size:0.9rem;font-weight:bold;">
                Continue to Tutorial 2 →
            </button>
        </form>
        """
        else:
            terrain_options_html = "\n".join(
                f'<option value="{k}">{label}</option>'
                for k, label in TERRAIN_OPTIONS
            )
            content = f"""
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 12px 0;">
            Congratulations on completing Level 1 of the Wadsworth Tutorial!
            As a reward, you'll receive <strong style="color:#d4af37;">one free land plot</strong> with these special properties:
        </p>
        <ul style="color:#94a3b8;line-height:2;margin:0 0 12px 0;padding-left:20px;">
            <li><strong style="color:#22c55e;">Forever Tax-Free</strong> — no monthly land tax, ever</li>
            <li><strong style="color:#38bdf8;">All Proximity Features</strong> — urban, coastal, riverside, lakeside, oasis, hot springs, caves, volcanic, road, and deposits</li>
            <li><strong style="color:#a855f7;">Your Choice of Terrain</strong> — determines which businesses can be built</li>
            <li><strong style="color:#f59e0b;">Sellable</strong> — you can list it on the Land Market at any time</li>
        </ul>
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 16px 0;">
            <strong style="color:#d4af37;">Choose your terrain type and claim your plot:</strong>
        </p>
        <form action="/api/tutorial/claim-reward" method="post" style="display:flex;gap:12px;align-items:center;flex-wrap:wrap;">
            <select name="terrain_type" required style="background:#0f172a;border:1px solid #d4af37;color:#e5e7eb;padding:8px 12px;border-radius:4px;flex:1;min-width:200px;">
                {terrain_options_html}
            </select>
            <button type="submit" style="background:#d4af37;color:#020617;border:none;padding:10px 24px;border-radius:4px;cursor:pointer;font-size:0.9rem;font-weight:bold;white-space:nowrap;">
                Claim Free Plot!
            </button>
        </form>
        """

    elif step == 10:
        title = "The Land Market — Your Final Frontier"
        content = """
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 12px 0;">
            The <strong style="color:#e5e7eb;">Land Market</strong> is where land plots are bought and sold.
            It operates in two modes:
        </p>
        <ul style="color:#94a3b8;line-height:2;margin:0 0 12px 0;padding-left:20px;">
            <li><strong style="color:#f59e0b;">Government Auctions</strong> — use a Dutch auction system. Price starts high and falls over time. Wait for a lower price, but risk losing the plot to another buyer.</li>
            <li><strong style="color:#a855f7;">Player Listings</strong> — fixed-price sales from other players. First come, first served.</li>
        </ul>
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 12px 0;">
            When evaluating a plot, consider:
        </p>
        <ul style="color:#94a3b8;line-height:2;margin:0 0 12px 0;padding-left:20px;">
            <li><strong style="color:#22c55e;">Terrain Type</strong> — determines which businesses you can build</li>
            <li><strong style="color:#38bdf8;">Proximity Features</strong> — bonuses like <em>coastal</em> (trade access), <em>urban</em> (high demand), <em>riverside</em> (water bonus), <em>deposits</em> (resource extraction), and more. Multiple features multiply your options.</li>
            <li><strong style="color:#f59e0b;">Monthly Tax</strong> — ongoing cost. Balance it against the business revenue the plot will generate.</li>
            <li><strong style="color:#a855f7;">Efficiency</strong> — higher efficiency = more output. New plots start at 100% and degrade slowly over time.</li>
        </ul>
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 16px 0;">
            Your tutorial reward plot is already in your land portfolio — head there to start building on it!
            You are now <strong style="color:#d4af37;">free to play</strong> however you like. Good luck, CEO!
        </p>
        <form action="/api/tutorial/advance" method="post">
            <button type="submit" style="background:#d4af37;color:#020617;border:none;padding:10px 24px;border-radius:4px;cursor:pointer;font-size:0.9rem;font-weight:bold;">
                Next: Meet Your Executives →
            </button>
        </form>
        """

    elif step == 11:
        import json as _json
        _video_id = "_uunsDAShzM"  # fallback
        try:
            with open("wiki_media.json", "r") as _f:
                _media = _json.load(_f)
            _video_id = _media["videos"][1]["youtube_id"]
        except Exception:
            pass

        from executive import FIRST_LADY_EXECUTIVES
        fl_cards = ""
        for fl in FIRST_LADY_EXECUTIVES:
            ab_key  = fl["ability"]
            fl_cards += f"""
            <label class="fl-card" for="fl_{fl['key']}" style="
                display:block;cursor:pointer;border:2px solid #1d2f55;border-radius:6px;
                padding:10px 12px;margin-bottom:8px;background:#090e1c;
                transition:border-color .2s;
            ">
                <input type="radio" name="first_lady" id="fl_{fl['key']}" value="{fl['key']}"
                       style="display:none;" required
                       onchange="document.querySelectorAll('.fl-card').forEach(c=>c.style.borderColor='#1d2f55');this.closest('.fl-card').style.borderColor='#d4af37';">
                <div style="display:flex;justify-content:space-between;align-items:baseline;gap:8px;flex-wrap:wrap;">
                    <span style="color:#e5e7eb;font-weight:bold;font-size:0.9rem;">{fl['name']}</span>
                    <span style="color:#64748b;font-size:0.75rem;">{fl['years']}</span>
                </div>
                <div style="color:#94a3b8;font-size:0.78rem;margin-top:2px;">{fl['real_role']}</div>
                <div style="color:#f5a855;font-size:0.76rem;margin-top:4px;">
                    ✦ Unique buff: {fl['flavor'].split('.')[0]}.
                </div>
            </label>"""

        already_has_fl = _has_first_lady(player.id)
        title = "Bonus Step — Executive Hiring"
        if already_has_fl:
            content = """
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 12px 0;">
            You've replayed Tutorial 2 — welcome back!
        </p>
        <div style="background:rgba(74,222,128,0.08);border:1px solid rgba(74,222,128,0.3);
                    border-radius:6px;padding:12px 16px;margin-bottom:16px;">
            <strong style="color:#4ade80;">&#10003; Reward already claimed</strong>
            <p style="color:#94a3b8;font-size:0.85rem;margin:6px 0 0;">
                Your First Lady executive is already on your team.
                Replaying a tutorial doesn't grant a second reward.
            </p>
        </div>
        <form action="/api/tutorial/claim-executive" method="post"
              style="display:inline;">
            <input type="hidden" name="first_lady" value="martha_washington">
            <button type="submit" style="background:#d4af37;color:#020617;border:none;padding:10px 24px;
                    border-radius:4px;cursor:pointer;font-size:0.9rem;font-weight:bold;">
                Finish Tutorial 2 →
            </button>
        </form>
        """
        else:
            content = f"""
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 12px 0;">
            Every great company needs great <strong style="color:#e5e7eb;">Executives</strong>.
            In Wadsworth, executives are living characters — they age, level up through school,
            earn wages, and each brings unique <strong style="color:#f5a855;">ability buffs</strong>
            that give your business a real edge.
        </p>
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 12px 0;">
            Watch the 2-minute executives overview, then claim your free
            <strong style="color:#d4af37;">Former First Lady</strong> executive —
            a forever-free hire who starts age 18, retires at 110, and can level up
            all the way to <strong style="color:#d4af37;">Level 18</strong> through school.
        </p>

        <!-- YouTube IFrame Player -->
        <div style="position:relative;padding-bottom:56.25%;height:0;overflow:hidden;border-radius:6px;border:1px solid #1d2f55;margin-bottom:16px;">
            <div id="yt-player-container" style="position:absolute;top:0;left:0;width:100%;height:100%;"></div>
        </div>

        <!-- Watch-progress indicator -->
        <div id="tut-watch-bar" style="background:#111c35;border:1px solid #1d2f55;border-radius:4px;height:6px;margin-bottom:12px;overflow:hidden;">
            <div id="tut-watch-fill" style="background:#d4af37;height:6px;width:0%;transition:width .5s;"></div>
        </div>
        <p id="tut-watch-label" style="color:#64748b;font-size:0.8rem;margin:0 0 16px 0;text-align:center;">
            ⏳ Watch the video to unlock your First Lady selection…
        </p>

        <!-- First Lady selector — hidden until video watched -->
        <div id="fl-selector" style="display:none;">
            <p style="color:#d4af37;font-weight:bold;margin:0 0 10px 0;">
                Choose your Former First Lady executive:
            </p>
            <div style="max-height:340px;overflow-y:auto;padding-right:4px;margin-bottom:14px;">
                <form id="fl-claim-form" action="/api/tutorial/claim-executive" method="post">
                    {fl_cards}
                    <button type="submit" style="background:#d4af37;color:#020617;border:none;padding:10px 24px;border-radius:4px;cursor:pointer;font-size:0.9rem;font-weight:bold;width:100%;margin-top:4px;">
                        Hire Her — Free Forever! →
                    </button>
                </form>
            </div>
        </div>

        <script>
        // YouTube IFrame Player API — no API key needed
        (function() {{
            var WATCH_THRESHOLD = 0.90;
            var watched = false;

            function unlockSelector() {{
                if (watched) return;
                watched = true;
                document.getElementById('tut-watch-label').innerHTML =
                    '<span style="color:#4ade80;">✓ Video complete! Now choose your First Lady below.</span>';
                document.getElementById('tut-watch-fill').style.width = '100%';
                document.getElementById('fl-selector').style.display = 'block';
            }}

            // Load YT API
            var tag = document.createElement('script');
            tag.src = 'https://www.youtube.com/iframe_api';
            document.head.appendChild(tag);

            var ytPlayer;
            window.onYouTubeIframeAPIReady = function() {{
                ytPlayer = new YT.Player('yt-player-container', {{
                    videoId: '{_video_id}',
                    playerVars: {{ rel: 0, modestbranding: 1 }},
                    events: {{
                        onStateChange: function(e) {{
                            // State 0 = ENDED — counts as watched regardless of duration
                            if (e.data === YT.PlayerState.ENDED) unlockSelector();
                        }}
                    }}
                }});
            }};

            // Poll every 2 s — unlock at 90% of duration
            var pollTimer = setInterval(function() {{
                if (!ytPlayer || typeof ytPlayer.getCurrentTime !== 'function') return;
                try {{
                    var cur = ytPlayer.getCurrentTime();
                    var dur = ytPlayer.getDuration();
                    if (dur > 0) {{
                        var pct = Math.min(cur / dur, 1);
                        document.getElementById('tut-watch-fill').style.width = (pct * 100).toFixed(1) + '%';
                        if (pct >= WATCH_THRESHOLD) {{ unlockSelector(); clearInterval(pollTimer); }}
                    }}
                }} catch(ex) {{}}
            }}, 2000);
        }})();
        </script>
        """

    else:
        return ""

    # ── Wrapper HTML ──────────────────────────────────────────────
    return f"""
    <div id="tutorial-panel" style="
        background: linear-gradient(135deg, #0a1628, #0f172a);
        border: 2px solid #d4af37;
        border-radius: 6px;
        padding: 20px 24px;
        margin-bottom: 24px;
        position: relative;
    ">
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:14px;flex-wrap:wrap;">
            <span style="background:#d4af37;color:#020617;padding:3px 12px;border-radius:12px;font-size:0.7rem;font-weight:bold;letter-spacing:0.05em;">
                TUTORIAL — STEP {step}/{TOTAL_STEPS}
            </span>
            <span style="color:#d4af37;font-size:0.85rem;font-weight:bold;">Level 1 · Startup Company</span>
            <div style="flex:1;background:#1e293b;height:4px;border-radius:2px;min-width:80px;">
                <div style="background:#d4af37;height:4px;border-radius:2px;width:{int(step / TOTAL_STEPS * 100)}%;"></div>
            </div>
        </div>
        <h3 style="color:#d4af37;margin:0 0 12px 0;font-size:1.05rem;">{title}</h3>
        {content}
        <a href="/api/tutorial/dismiss"
           onclick="return confirm('Skip the tutorial? You can always restart by creating a new account.');"
           style="position:absolute;top:12px;right:16px;color:#475569;font-size:0.72rem;text-decoration:none;">
            Skip Tutorial
        </a>
    </div>
    """


# ==========================
# API ROUTES
# ==========================

def _get_player_from_cookie(session_token):
    """Authenticate player from session cookie."""
    try:
        from auth import get_db, get_player_from_session
        db = get_db()
        player = get_player_from_session(db, session_token)
        db.close()
        return player
    except Exception:
        return None


@router.post("/api/tutorial/start")
def start_tutorial(session_token: Optional[str] = Cookie(None)):
    """Start the tutorial (step 0 → 1)."""
    player = _get_player_from_cookie(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)
    step = get_tutorial_step(player.id)
    if step == 0:
        set_tutorial_step(player.id, 1)
    return RedirectResponse(url="/", status_code=303)


@router.post("/api/tutorial/advance")
def advance_tutorial(session_token: Optional[str] = Cookie(None)):
    """
    Advance the tutorial to the next step.
    Validates completion conditions where applicable.
    """
    player = _get_player_from_cookie(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)

    step = get_tutorial_step(player.id)

    # Validate conditions before advancing
    if step == 2 and not player_has_business_type(player.id, "water_facility"):
        return RedirectResponse(url="/land?tutorial_error=need_water_facility", status_code=303)
    if step == 4:
        if not player_has_business_type(player.id, "plantation") or not player_has_business_type(player.id, "grocery_store"):
            return RedirectResponse(url="/land?tutorial_error=need_both_businesses", status_code=303)
    if step == 7 and not player_has_apple_market_listing(player.id):
        return RedirectResponse(url="/market?item=apples&tutorial_error=need_apple_listing", status_code=303)

    next_step = step + 1
    set_tutorial_step(player.id, next_step)

    redirect_url = STEP_REDIRECT.get(next_step, "/")
    return RedirectResponse(url=redirect_url, status_code=303)


@router.get("/api/tutorial/check-apple")
def check_apple(session_token: Optional[str] = Cookie(None)):
    """JSON endpoint: check if player has an apple in inventory (for step 7 polling)."""
    from fastapi.responses import JSONResponse
    player = _get_player_from_cookie(session_token)
    if not player:
        return JSONResponse({"has_apple": False})
    return JSONResponse({"has_apple": player_has_apple_in_inventory(player.id)})


def _has_tutorial_reward_plot(player_id: int) -> bool:
    """Return True if the player has already claimed the Tutorial 1 land-plot reward."""
    try:
        from land import LandPlot, get_db as get_land_db
        db = get_land_db()
        found = db.query(LandPlot).filter(
            LandPlot.owner_id == player_id,
            LandPlot.is_tutorial_reward == True,
        ).first() is not None
        db.close()
        return found
    except Exception:
        return False


def _has_first_lady(player_id: int) -> bool:
    """Return True if the player already has a First Lady executive."""
    try:
        from executive import Executive, SessionLocal as ExecSessionLocal
        db = ExecSessionLocal()
        found = db.query(Executive).filter(
            Executive.player_id == player_id,
            Executive.is_first_lady == True,
        ).first() is not None
        db.close()
        return found
    except Exception:
        return False


@router.post("/api/tutorial/restart")
def restart_tutorial(
    session_token: Optional[str] = Cookie(None),
    tutorial_number: int = Form(...),
):
    """Restart a tutorial from its first step. No reward is given again."""
    player = _get_player_from_cookie(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)

    current = get_tutorial_step(player.id)

    if tutorial_number == 1 and current > 0:
        set_tutorial_step(player.id, 1)
        return RedirectResponse(url="/", status_code=303)

    if tutorial_number == 2 and current >= 10:
        set_tutorial_step(player.id, 10)
        return RedirectResponse(url="/land-market", status_code=303)

    return RedirectResponse(url="/settings?tab=tutorials", status_code=303)


@router.post("/api/tutorial/claim-reward")
def claim_tutorial_reward(
    session_token: Optional[str] = Cookie(None),
    terrain_type: str = Form(...)
):
    """Step 9: Create the tutorial reward plot (if not already claimed) and advance to step 10."""
    player = _get_player_from_cookie(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)

    step = get_tutorial_step(player.id)
    if step != 9:
        return RedirectResponse(url="/", status_code=303)

    valid_terrains = [k for k, _ in TERRAIN_OPTIONS]
    if terrain_type not in valid_terrains:
        terrain_type = "prairie"

    if not _has_tutorial_reward_plot(player.id):
        try:
            create_tutorial_reward_plot(player.id, terrain_type)
        except Exception as e:
            print(f"[Tutorial] Error creating reward plot: {e}")
            return RedirectResponse(url="/?tutorial_error=reward_failed", status_code=303)
    else:
        print(f"[Tutorial] Player {player.id} already has reward plot — skipping duplicate creation")

    set_tutorial_step(player.id, 10)
    return RedirectResponse(url="/land-market", status_code=303)


@router.post("/api/tutorial/complete")
def complete_tutorial(session_token: Optional[str] = Cookie(None)):
    """Step 11 → 12: Mark tutorial as complete (fallback — normally via claim-executive)."""
    player = _get_player_from_cookie(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)
    set_tutorial_step(player.id, 12)
    return RedirectResponse(url="/", status_code=303)


@router.post("/api/tutorial/dismiss")
def dismiss_tutorial(session_token: Optional[str] = Cookie(None)):
    """Dismiss the tutorial permanently (set to step 12 = complete)."""
    player = _get_player_from_cookie(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)
    set_tutorial_step(player.id, 12)
    return RedirectResponse(url="/", status_code=303)


@router.get("/api/tutorial/dismiss")
def dismiss_tutorial_get(session_token: Optional[str] = Cookie(None)):
    """Dismiss the tutorial via link click (GET)."""
    player = _get_player_from_cookie(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)
    set_tutorial_step(player.id, 12)
    return RedirectResponse(url="/", status_code=303)


@router.post("/api/tutorial/claim-executive")
def claim_first_lady(
    session_token: Optional[str] = Cookie(None),
    first_lady: str = Form(...)
):
    """
    Step 11: Create the chosen First Lady executive and advance to step 12.
    The executive is free, permanent, starts age 18, retires at 110, max level 18.
    """
    player = _get_player_from_cookie(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)

    step = get_tutorial_step(player.id)
    if step != 11:
        return RedirectResponse(url="/", status_code=303)

    from executive import (
        Executive, FIRST_LADY_EXECUTIVES, SessionLocal as ExecSessionLocal,
    )

    fl_data = next((f for f in FIRST_LADY_EXECUTIVES if f["key"] == first_lady), None)
    if fl_data is None:
        return RedirectResponse(url="/?tutorial_error=invalid_first_lady", status_code=303)

    if not _has_first_lady(player.id):
        try:
            db = ExecSessionLocal()

            # Split name into first / last
            name_parts = fl_data["name"].split(" ", 1)
            first_name = name_parts[0]
            last_name  = name_parts[1] if len(name_parts) > 1 else ""

            exec_obj = Executive(
                first_name       = first_name,
                last_name        = last_name,
                player_id        = player.id,
                level            = 1,
                job              = "first_lady",
                wage             = 0.0,         # free forever
                pay_cycle        = "hour",
                current_age      = 18,
                retirement_age   = 110,
                max_age          = 120,
                is_retired       = False,
                is_dead          = False,
                is_special       = False,
                is_first_lady    = True,
                max_level        = 18,
                abilities        = fl_data["ability"],
                bonuses          = "",
                on_marketplace   = False,
                marketplace_reason = "tutorial",
                hired_at         = __import__("datetime").datetime.utcnow(),
            )
            db.add(exec_obj)
            db.commit()
            db.close()
            print(f"[Tutorial] Created First Lady executive '{fl_data['name']}' for player {player.id}")
        except Exception as e:
            print(f"[Tutorial] Error creating First Lady executive: {e}")
            try:
                db.close()
            except Exception:
                pass
            return RedirectResponse(url="/?tutorial_error=exec_failed", status_code=303)
    else:
        print(f"[Tutorial] Player {player.id} already has a First Lady — skipping duplicate creation")

    set_tutorial_step(player.id, 12)
    return RedirectResponse(url="/executives?tutorial_complete=1", status_code=303)


# ============================================================
# TUTORIAL 3 — IPO & Banking
# ============================================================
#
# Steps:
#   0  - Not started (banner shown on dashboard after T1 complete)
#   1  - Banking System overview  (/banks)
#   2  - Brokerage Firm intro      (/banks/brokerage-firm)
#   3  - What is an IPO?           (/brokerage/ipo)
#   4  - IPO Types deep-dive       (/brokerage/ipo)
#   5  - Valuation & prerequisites (/brokerage/ipo)
#   6  - Launch Your IPO           (/brokerage/ipo — prereq check)
#   7  - Reward overlay            (/brokerage/trading after IPO created)
#   8  - Complete
# ============================================================

T3_TOTAL_STEPS = 6


def get_tutorial3_step(player_id: int) -> int:
    """Return the player's current Tutorial 3 step (0–8)."""
    try:
        from auth import get_db, Player
        db = get_db()
        player = db.query(Player).filter(Player.id == player_id).first()
        db.close()
        if player is None:
            return 0
        step = getattr(player, "tutorial_3_step", 0)
        return step if step is not None else 0
    except Exception as e:
        print(f"[Tutorial3] get_tutorial3_step error: {e}")
        return 0


def set_tutorial3_step(player_id: int, step: int):
    """Set the player's Tutorial 3 step."""
    try:
        from auth import get_db, Player
        db = get_db()
        player = db.query(Player).filter(Player.id == player_id).first()
        if player:
            player.tutorial_3_step = step
            db.commit()
        db.close()
    except Exception as e:
        print(f"[Tutorial3] set_tutorial3_step error: {e}")


def should_show_tutorial3_banner(player) -> bool:
    """Show the T3 start banner only after Tutorial 1 is complete and T3 not yet started."""
    t1 = getattr(player, "tutorial_step", 0) or 0
    t3 = getattr(player, "tutorial_3_step", 0) or 0
    return t1 >= 12 and t3 == 0


def player_has_public_company(player_id: int) -> bool:
    """Return True if the player already has an active public company."""
    try:
        from banks.brokerage_firm import CompanyShares, get_db as get_firm_db
        db = get_firm_db()
        count = db.query(CompanyShares).filter(
            CompanyShares.founder_id == player_id,
            CompanyShares.is_delisted == False,
        ).count()
        db.close()
        return count > 0
    except Exception as e:
        print(f"[Tutorial3] player_has_public_company error: {e}")
        return False


def get_player_estimated_valuation(player_id: int) -> float:
    """Estimate player company valuation for prerequisite check."""
    try:
        from banks.brokerage_firm import calculate_player_company_valuation
        val, _ = calculate_player_company_valuation(player_id)
        return val or 0.0
    except Exception:
        return 0.0


# ── Tutorial 3 overlay HTML generator ─────────────────────────────────────────

def get_tutorial3_overlay_html(player, current_page: str) -> str:
    """
    Return the Tutorial 3 overlay panel HTML for the given page.
    `current_page` is one of: 'banks', 'brokerage_firm', 'brokerage_ipo', 'brokerage_trading'.
    Returns empty string if T3 is not active or wrong page.
    """
    step = get_tutorial3_step(player.id)
    if step == 0 or step >= 8:
        return ""

    T3_STEP_PAGE = {
        1: "banks",
        2: "brokerage_firm",
        3: "brokerage_ipo",
        4: "brokerage_ipo",
        5: "brokerage_ipo",
        6: "brokerage_ipo",
        7: "brokerage_trading",
    }
    if T3_STEP_PAGE.get(step, "") != current_page:
        return ""

    # ── per-step content ───────────────────────────────────────────────────────

    if step == 1:
        title = "The Banking System"
        content = """
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 12px 0;">
            Wadsworth has a fully functioning <strong style="color:#e5e7eb;">banking system</strong>
            made up of independent <em style="color:#38bdf8;">Reserve Banks</em>. Each bank issues
            its own currency, backed by commodities and economic activity in its region.
        </p>
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 12px 0;">
            Players hold legal tender with the reserve bank that serves their home region.
            You can buy <strong style="color:#e5e7eb;">government bonds</strong> from a reserve bank
            to earn interest, or take out loans to fund expansion. Banks charge competitive rates
            and adjust them based on inflation and credit risk.
        </p>
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 16px 0;">
            The <strong style="color:#d4af37;">Brokerage Firm</strong> — shown below — is a private
            financial institution separate from the reserve banks. It runs the stock exchange,
            manages IPOs, and lets you trade equity in other player companies.
            Let's visit it next.
        </p>
        <a href="/banks/brokerage-firm"
           onclick="fetch('/api/tutorial3/advance',{method:'POST'}).catch(()=>{})"
           style="display:inline-block;background:#d4af37;color:#020617;padding:10px 24px;
                  border-radius:4px;font-size:0.9rem;font-weight:bold;text-decoration:none;">
            Visit the Brokerage Firm →
        </a>
        """

    elif step == 2:
        title = "The Wadsworth Brokerage Firm"
        content = """
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 12px 0;">
            The <strong style="color:#e5e7eb;">Brokerage Firm</strong> is the financial backbone
            of the Wadsworth exchange. It acts as underwriter, market-maker, and lender for
            publicly traded player companies.
        </p>
        <ul style="color:#94a3b8;line-height:1.9;margin:0 0 14px 24px;padding:0;">
            <li><strong style="color:#e5e7eb;">Equity trading</strong> — buy and sell shares in player companies</li>
            <li><strong style="color:#e5e7eb;">IPO underwriting</strong> — take your company public on the WPE</li>
            <li><strong style="color:#e5e7eb;">Short selling</strong> — borrow and short shares you don't own</li>
            <li><strong style="color:#e5e7eb;">Margin lending</strong> — borrow against your portfolio to amplify positions</li>
            <li><strong style="color:#e5e7eb;">ETF funds</strong> — invest in themed commodity-backed funds</li>
            <li><strong style="color:#e5e7eb;">Governance</strong> — vote on corporate proposals as a shareholder</li>
        </ul>
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 16px 0;">
            When you're ready to take your company public, the Firm handles everything from
            pricing to share distribution. Let's learn how an IPO works.
        </p>
        <a href="/brokerage/ipo"
           onclick="fetch('/api/tutorial3/advance',{method:'POST'}).catch(()=>{})"
           style="display:inline-block;background:#d4af37;color:#020617;padding:10px 24px;
                  border-radius:4px;font-size:0.9rem;font-weight:bold;text-decoration:none;">
            Learn About IPOs →
        </a>
        """

    elif step == 3:
        title = "What is an IPO?"
        content = """
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 12px 0;">
            An <strong style="color:#e5e7eb;">Initial Public Offering (IPO)</strong> is when you
            sell a portion of your company to outside investors by listing shares on the
            Wadsworth Public Exchange (WPE).
        </p>
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 12px 0;">
            Here's how it works:
        </p>
        <ol style="color:#94a3b8;line-height:1.9;margin:0 0 14px 24px;padding:0;">
            <li>You choose an <strong style="color:#e5e7eb;">IPO type</strong> and set how many
                shares to issue and what percentage of the company goes public.</li>
            <li>The Brokerage Firm either buys the shares from you upfront
                (<em style="color:#38bdf8;">underwritten</em>) or lists them for the market to
                absorb (<em style="color:#38bdf8;">direct listing</em>).</li>
            <li>Proceeds land in your account. Public shareholders now own a stake in your
                holding company — entitled to dividends if you issue them, and voting rights
                on proposals you create.</li>
            <li>Your company's share price fluctuates with demand, earnings, and market sentiment.</li>
        </ol>
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 16px 0;">
            Next, let's look at the different IPO structures available to you.
        </p>
        <form action="/api/tutorial3/advance" method="post">
            <button type="submit"
                    style="background:#d4af37;color:#020617;border:none;padding:10px 24px;
                           border-radius:4px;cursor:pointer;font-size:0.9rem;font-weight:bold;">
                See IPO Types →
            </button>
        </form>
        """

    elif step == 4:
        title = "IPO Types — Choose Your Structure"
        content = """
        <p style="color:#94a3b8;margin:0 0 14px 0;">
            Wadsworth offers <strong style="color:#e5e7eb;">7 IPO structures</strong>.
            Each trades off price, risk, control, and capital differently:
        </p>
        <div style="display:grid;gap:8px;margin-bottom:16px;">

          <div style="background:#0f172a;border:1px solid #1e293b;border-left:3px solid #38bdf8;
                      padding:10px 14px;border-radius:4px;">
            <div style="color:#e5e7eb;font-weight:bold;font-size:0.9rem;">Direct Listing</div>
            <div style="color:#94a3b8;font-size:0.8rem;line-height:1.6;">
              Flat $5,000 fee · No underwriter · Market-priced · Up to 80% float · Min valuation $25k
            </div>
          </div>

          <div style="background:#0f172a;border:1px solid #1e293b;border-left:3px solid #6366f1;
                      padding:10px 14px;border-radius:4px;">
            <div style="color:#e5e7eb;font-weight:bold;font-size:0.9rem;">Underwritten IPO</div>
            <div style="color:#94a3b8;font-size:0.8rem;line-height:1.6;">
              7% discount · Guaranteed capital · Up to 60% float · Min valuation $50k
            </div>
          </div>

          <div style="background:#0f172a;border:1px solid #1e293b;border-left:3px solid #22c55e;
                      padding:10px 14px;border-radius:4px;">
            <div style="color:#e5e7eb;font-weight:bold;font-size:0.9rem;">Income Shares IPO</div>
            <div style="color:#94a3b8;font-size:0.8rem;line-height:1.6;">
              3% discount (best price) · 10% annual dividend quarterly · Up to 40% float · Min valuation $75k
            </div>
          </div>

          <div style="background:#0f172a;border:1px solid #1e293b;border-left:3px solid #f59e0b;
                      padding:10px 14px;border-radius:4px;">
            <div style="color:#e5e7eb;font-weight:bold;font-size:0.9rem;">Dual-Class IPO</div>
            <div style="color:#94a3b8;font-size:0.8rem;line-height:1.6;">
              8% discount · Class B public + Class A founder · Up to 49% float · Min valuation $100k · You keep >51% votes
            </div>
          </div>

          <div style="background:#0f172a;border:1px solid #1e293b;border-left:3px solid #ec4899;
                      padding:10px 14px;border-radius:4px;">
            <div style="color:#e5e7eb;font-weight:bold;font-size:0.9rem;">Preferred Share Offering</div>
            <div style="color:#94a3b8;font-size:0.8rem;line-height:1.6;">
              5% discount · Guaranteed quarterly dividends · 1.5× liquidation priority · Callable · Up to 40% float · Min valuation $50k
            </div>
          </div>

          <div style="background:#0f172a;border:1px solid #1e293b;border-left:3px solid #a855f7;
                      padding:10px 14px;border-radius:4px;">
            <div style="color:#e5e7em;font-weight:bold;font-size:0.9rem;">Series A Growth Round</div>
            <div style="color:#94a3b8;font-size:0.8rem;line-height:1.6;">
              12% discount · +20% growth capital bonus · Up to 30% float · Min valuation $150k
            </div>
          </div>

          <div style="background:#0f172a;border:1px solid #1e293b;border-left:3px solid #d4af37;
                      padding:10px 14px;border-radius:4px;">
            <div style="color:#e5e7eb;font-weight:bold;font-size:0.9rem;">Quad-Class IPO</div>
            <div style="color:#94a3b8;font-size:0.8rem;line-height:1.6;">
              10% discount · 4 share classes · +15% growth bonus · 10% fixed dividend · 1.2× liquidation priority · Up to 60% float · Min valuation $200k
            </div>
          </div>

        </div>
        <form action="/api/tutorial3/advance" method="post">
            <button type="submit"
                    style="background:#d4af37;color:#020617;border:none;padding:10px 24px;
                           border-radius:4px;cursor:pointer;font-size:0.9rem;font-weight:bold;">
                Next — Valuation & Requirements →
            </button>
        </form>
        """

    elif step == 5:
        val = get_player_estimated_valuation(player.id)
        val_color = "#4ade80" if val >= 25000 else "#f87171"
        val_note = (
            f'<span style="color:{val_color};font-weight:bold;">'
            f'${val:,.0f}</span>'
        )
        min_note = (
            '<span style="color:#4ade80;">✓ You qualify for at least a Direct Listing!</span>'
            if val >= 25000
            else '<span style="color:#f87171;">⚠ Grow your businesses further to reach the $25,000 minimum.</span>'
        )
        title = "Valuation & Requirements"
        content = f"""
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 12px 0;">
            Your company's <strong style="color:#e5e7eb;">estimated valuation</strong> is
            based on your businesses, land, inventory, and cash.
            The Brokerage Firm calculates it automatically at the time of your IPO.
        </p>
        <div style="background:#0f172a;border:1px solid #1e293b;border-radius:6px;
                    padding:14px 18px;margin-bottom:14px;">
            <div style="font-size:0.75rem;color:#64748b;text-transform:uppercase;
                        letter-spacing:0.08em;margin-bottom:4px;">Your Estimated Valuation</div>
            <div style="font-size:1.4rem;font-weight:bold;">{val_note}</div>
            <div style="margin-top:8px;font-size:0.82rem;">{min_note}</div>
        </div>
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 14px 0;">
            <strong style="color:#e5e7eb;">Other requirements before launching:</strong>
        </p>
        <ul style="color:#94a3b8;line-height:1.9;margin:0 0 16px 24px;padding:0;">
            <li>You cannot already have a public company listed on the WPE</li>
            <li>You must meet the minimum valuation for your chosen IPO type</li>
            <li>You must have enough cash to cover the listing fee (Direct Listing: $5,000 flat)</li>
        </ul>
        <form action="/api/tutorial3/advance" method="post">
            <button type="submit"
                    style="background:#d4af37;color:#020617;border:none;padding:10px 24px;
                           border-radius:4px;cursor:pointer;font-size:0.9rem;font-weight:bold;">
                I'm Ready — Show Me How to Launch →
            </button>
        </form>
        """

    elif step == 6:
        already_public = player_has_public_company(player.id)
        val = get_player_estimated_valuation(player.id)
        can_ipo = not already_public and val >= 25000

        if already_public:
            status_block = """
            <div style="background:#052e16;border:1px solid #16a34a;border-radius:4px;
                        padding:12px 16px;margin-bottom:14px;color:#4ade80;">
                ✓ Your company is already listed on the WPE! You're a public company.
                Head to <a href="/brokerage/my-companies" style="color:#4ade80;font-weight:bold;">My Companies</a>
                to manage your shares.
            </div>
            """
            cta = """
            <form action="/api/tutorial3/advance" method="post">
                <button type="submit"
                        style="background:#d4af37;color:#020617;border:none;padding:10px 24px;
                               border-radius:4px;cursor:pointer;font-size:0.9rem;font-weight:bold;">
                    Continue →
                </button>
            </form>
            """
        elif val < 25000:
            status_block = f"""
            <div style="background:#1c0a0a;border:1px solid #ef4444;border-radius:4px;
                        padding:12px 16px;margin-bottom:14px;color:#f87171;">
                ⚠ Estimated valuation ${val:,.0f} — you need at least $25,000 for a Direct Listing.
                Keep building your businesses and return here when you're ready.
            </div>
            """
            cta = """
            <a href="/land"
               style="display:inline-block;background:#38bdf8;color:#020617;padding:10px 24px;
                      border-radius:4px;font-size:0.9rem;font-weight:bold;text-decoration:none;">
                ← Go Build More Businesses
            </a>
            """
        else:
            status_block = f"""
            <div style="background:#052e16;border:1px solid #16a34a;border-radius:4px;
                        padding:12px 16px;margin-bottom:14px;color:#4ade80;">
                ✓ Estimated valuation ${val:,.0f} — you qualify! Scroll down and use the IPO form below.
            </div>
            """
            cta = """
            <p style="color:#94a3b8;font-size:0.85rem;line-height:1.7;margin:0 0 14px 0;">
                <strong style="color:#e5e7eb;">How to launch:</strong> scroll past this tutorial panel
                to the IPO form. Pick your IPO type, choose a ticker symbol and company name, set your
                share count and float percentage, then click <em>Launch IPO</em>. Once confirmed,
                your shares will appear on the WPE and your reward will unlock.
            </p>
            <p style="color:#64748b;font-size:0.8rem;margin:0;">
                After your IPO completes, visit
                <a href="/brokerage/trading" style="color:#38bdf8;">/brokerage/trading</a>
                to claim your Tutorial 3 reward.
            </p>
            """

        title = "Launch Your IPO"
        content = f"""
        {status_block}
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 12px 0;">
            Taking your company public is one of the most powerful moves in Wadsworth.
            It gives you instant capital, real shareholders, and a market-priced valuation.
        </p>
        {cta}
        """

    elif step == 7:
        title = "IPO Complete — Congratulations!"
        content = """
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 12px 0;">
            Your company is now publicly traded on the <strong style="color:#e5e7eb;">Wadsworth
            Public Exchange</strong>. Shareholders hold real stakes in your holding company,
            and your share price will reflect how well you run it.
        </p>
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 14px 0;">
            <strong style="color:#d4af37;">Tutorial 3 Reward:</strong> you've unlocked the ability
            to access <strong style="color:#e5e7eb;">margin lending</strong> on your portfolio —
            borrow up to 50% of your equity value to amplify positions. Use it wisely.
        </p>
        <form action="/api/tutorial3/advance" method="post">
            <button type="submit"
                    style="background:#d4af37;color:#020617;border:none;padding:10px 24px;
                           border-radius:4px;cursor:pointer;font-size:0.9rem;font-weight:bold;">
                Claim Reward & Complete Tutorial →
            </button>
        </form>
        """

    else:
        return ""

    # ── display step counter (steps 1-6, not the reward step 7) ───────────────
    display_step = min(step, T3_TOTAL_STEPS)

    return f"""
    <div id="tutorial3-panel" style="
        background: linear-gradient(135deg, #0a1628, #0f172a);
        border: 2px solid #d4af37;
        border-radius: 6px;
        padding: 20px 24px;
        margin-bottom: 24px;
        position: relative;
    ">
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:14px;flex-wrap:wrap;">
            <span style="background:#d4af37;color:#020617;padding:3px 12px;border-radius:12px;
                         font-size:0.7rem;font-weight:bold;letter-spacing:0.05em;">
                TUTORIAL 3 — STEP {display_step}/{T3_TOTAL_STEPS}
            </span>
            <span style="color:#d4af37;font-size:0.85rem;font-weight:bold;">Level 3 · IPO &amp; Banking</span>
            <div style="flex:1;background:#1e293b;height:4px;border-radius:2px;min-width:80px;">
                <div style="background:#d4af37;height:4px;border-radius:2px;
                            width:{int(display_step / T3_TOTAL_STEPS * 100)}%;"></div>
            </div>
        </div>
        <h3 style="color:#d4af37;margin:0 0 12px 0;font-size:1.05rem;">{title}</h3>
        {content}
        <a href="/api/tutorial3/dismiss"
           onclick="return confirm('Skip Tutorial 3? You can restart it from Settings.');"
           style="position:absolute;top:12px;right:16px;color:#475569;font-size:0.72rem;text-decoration:none;">
            Skip
        </a>
    </div>
    """


# ── Tutorial 3 banner (shown on dashboard when T1 done and T3 not started) ────

def get_tutorial3_banner_html(player) -> str:
    """Return the T3 start banner HTML, or empty string if not applicable."""
    if not should_show_tutorial3_banner(player):
        return ""
    return f"""
    <div style="
        background: linear-gradient(135deg, #0a1628, #0f172a);
        border: 2px solid #d4af37;
        border-radius: 6px;
        padding: 20px 24px;
        margin-bottom: 24px;
    ">
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:14px;flex-wrap:wrap;">
            <span style="background:#d4af37;color:#020617;padding:3px 12px;border-radius:12px;
                         font-size:0.7rem;font-weight:bold;letter-spacing:0.05em;">
                NEW TUTORIAL AVAILABLE
            </span>
            <span style="color:#d4af37;font-size:0.85rem;font-weight:bold;">Level 3 · IPO &amp; Banking</span>
        </div>
        <h3 style="color:#d4af37;margin:0 0 10px 0;font-size:1.05rem;">
            Ready to Go Public?
        </h3>
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 16px 0;">
            Tutorial 3 walks you through the <strong style="color:#e5e7eb;">Banking System</strong>,
            the <strong style="color:#e5e7eb;">Brokerage Firm</strong>, and how to launch your
            company's <strong style="color:#e5e7eb;">Initial Public Offering</strong> on the
            Wadsworth Public Exchange.
        </p>
        <form action="/api/tutorial3/start" method="post" style="display:inline;">
            <button type="submit"
                    style="background:#d4af37;color:#020617;border:none;padding:10px 24px;
                           border-radius:4px;cursor:pointer;font-size:0.9rem;font-weight:bold;">
                Start Tutorial 3 →
            </button>
        </form>
        <a href="/api/tutorial3/dismiss"
           style="margin-left:16px;color:#475569;font-size:0.82rem;">
            Dismiss
        </a>
    </div>
    """


# ── Tutorial 3 API routes ──────────────────────────────────────────────────────

@router.post("/api/tutorial3/start")
def tutorial3_start(session_token: Optional[str] = Cookie(None)):
    """Start Tutorial 3 (step 0 → 1)."""
    player = _get_player_from_cookie(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)
    if get_tutorial3_step(player.id) == 0:
        set_tutorial3_step(player.id, 1)
    return RedirectResponse(url="/banks", status_code=303)


@router.post("/api/tutorial3/advance")
def tutorial3_advance(session_token: Optional[str] = Cookie(None)):
    """Advance Tutorial 3 to the next step."""
    player = _get_player_from_cookie(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)

    step = get_tutorial3_step(player.id)

    NEXT_REDIRECT = {
        1: "/banks/brokerage-firm",
        2: "/brokerage/ipo",
        3: "/brokerage/ipo",
        4: "/brokerage/ipo",
        5: "/brokerage/ipo",
        6: "/brokerage/trading",
        7: "/brokerage/trading",
    }

    if step == 0 or step >= 8:
        return RedirectResponse(url="/", status_code=303)

    set_tutorial3_step(player.id, step + 1)
    redirect_url = NEXT_REDIRECT.get(step, "/")
    return RedirectResponse(url=redirect_url, status_code=303)


@router.get("/api/tutorial3/dismiss")
def tutorial3_dismiss(session_token: Optional[str] = Cookie(None)):
    """Dismiss / skip Tutorial 3."""
    player = _get_player_from_cookie(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)
    set_tutorial3_step(player.id, 8)
    return RedirectResponse(url="/", status_code=303)


@router.post("/api/tutorial3/check-ipo-done")
def tutorial3_check_ipo_done(session_token: Optional[str] = Cookie(None)):
    """
    Called after an IPO is created.  If T3 is on step 6, advance to step 7
    (reward) and redirect to the trading page.
    """
    player = _get_player_from_cookie(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)
    step = get_tutorial3_step(player.id)
    if step == 6 and player_has_public_company(player.id):
        set_tutorial3_step(player.id, 7)
    return RedirectResponse(url="/brokerage/trading?success=ipo_created", status_code=303)
