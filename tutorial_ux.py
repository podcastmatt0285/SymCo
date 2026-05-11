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
            A <strong style="color:#38bdf8;">Mixed Fruit &amp; Vegetable Plantation</strong> (Production) converts
            apple seeds, water, paper, and pollen into apples. A <strong style="color:#38bdf8;">Local Grocery Store</strong>
            (Retail) then sells those apples to generate cash revenue.
        </p>
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 12px 0;">
            Together, these form a simple <em>vertical supply chain</em>: you produce the goods yourself
            and control the retail price. More complex chains can span dozens of businesses and item types.
        </p>
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 6px 0;">
            <strong style="color:#d4af37;">Your task:</strong> Build both businesses on vacant plots.
            Your starter inventory already contains all the inputs you need —
            <strong style="color:#84cc16;">apple seeds</strong>, <strong style="color:#38bdf8;">water</strong>,
            <strong style="color:#e5e7eb;">paper</strong>, and <strong style="color:#f59e0b;">pollen</strong>.
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
            <li><strong style="color:#38bdf8;">Water</strong> — being produced by your Water Treatment Facility; also consumed by the Plantation</li>
            <li><strong style="color:#f59e0b;">Energy</strong> — your starter supply, consumed by production</li>
            <li><strong style="color:#22c55e;">Seeds</strong> (apple, orange, and more) — primary inputs for your Plantation</li>
            <li><strong style="color:#fbbf24;">Pollen</strong> — required by the Plantation to grow fruit; your starter supply will last many cycles</li>
            <li><strong style="color:#e5e7eb;">Paper</strong> — packaging material, consumed each production cycle</li>
        </ul>
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 12px 0;">
            Your <strong style="color:#e5e7eb;">Plantation</strong> will produce its first
            <strong style="color:#84cc16;">Apples</strong> in about a minute — it runs one production
            cycle every 60 seconds. Your Grocery Store will then sell them automatically.
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
            With <strong style="color:#e5e7eb;">155 business types</strong> available, you can build anything
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
        _more_tutorials_html = """
        <div style="background:#0a1e3a;border:1px solid #38bdf8;border-radius:6px;
                    padding:12px 16px;margin-bottom:16px;">
            <strong style="color:#38bdf8;">📖 More tutorials available in Settings!</strong>
            <p style="color:#94a3b8;font-size:0.85rem;margin:6px 0 0;line-height:1.6;">
                Tutorials 3, 4, and 5 cover IPO &amp; Banking, ETFs &amp; Market Indices,
                and Acquisitions &amp; Income Stakes — each with unique rewards.
                Start them whenever you're ready from
                <a href="/settings?tab=tutorials" style="color:#38bdf8;font-weight:bold;">
                    Settings → Tutorials
                </a>.
            </p>
        </div>
        """
        if already_has_fl:
            content = f"""
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
        {_more_tutorials_html}
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
        {_more_tutorials_html}

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

    if tutorial_number == 3:
        step3 = get_tutorial3_step(player.id)
        if step3 > 0:
            set_tutorial3_step(player.id, 1)
            return RedirectResponse(url="/banks", status_code=303)

    if tutorial_number == 4:
        step4 = get_tutorial4_step(player.id)
        if step4 > 0:
            set_tutorial4_step(player.id, 1)
            return RedirectResponse(url="/banks/indices", status_code=303)

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
        result = calculate_player_company_valuation(player_id)
        return float(result.get("total_valuation", 0.0))
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
        <form action="/api/tutorial3/advance" method="post" style="display:inline;">
            <button type="submit"
                    style="background:#d4af37;color:#020617;border:none;padding:10px 24px;
                           border-radius:4px;cursor:pointer;font-size:0.9rem;font-weight:bold;">
                Visit the Brokerage Firm →
            </button>
        </form>
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
            <li><strong style="color:#e5e7eb;">Equity trading</strong> — buy and sell shares in player companies on the WPE</li>
            <li><strong style="color:#e5e7eb;">IPO underwriting</strong> — 7 IPO structures to take your company public</li>
            <li><strong style="color:#e5e7eb;">Short selling</strong> — borrow and short shares you don't own</li>
            <li><strong style="color:#e5e7eb;">Margin lending</strong> — borrow against your portfolio to amplify positions</li>
            <li><strong style="color:#e5e7eb;">ETF funds</strong> — invest in themed commodity-backed index funds</li>
            <li><strong style="color:#e5e7eb;">Corporate Actions</strong> — automate buybacks, stock splits, and secondary offerings directly from the dashboard</li>
            <li><strong style="color:#e5e7eb;">Governance</strong> — create and vote on corporate proposals as a shareholder</li>
            <li><strong style="color:#e5e7eb;">Loyalty dividends</strong> — hold shares 30+ days for a +10% dividend bonus, 90+ days for +25%</li>
            <li><strong style="color:#e5e7eb;">Sector perks</strong> — holding shares in Finance, Tech, or other sectors unlocks passive bonuses</li>
            <li><strong style="color:#e5e7eb;">Listing fees</strong> — public companies pay $500/month to stay listed; miss 3 payments and trading halts for 7 days</li>
        </ul>
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 16px 0;">
            When you're ready to take your company public, the Firm handles everything from
            pricing to share distribution. Let's learn how an IPO works.
        </p>
        <form action="/api/tutorial3/advance" method="post" style="display:inline;">
            <button type="submit"
                    style="background:#d4af37;color:#020617;border:none;padding:10px 24px;
                           border-radius:4px;cursor:pointer;font-size:0.9rem;font-weight:bold;">
                Learn About IPOs →
            </button>
        </form>
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
              Flat $5,000 fee · No underwriter · Market-priced · Up to 80% float · Min $25k
              <span style="color:#f59e0b;"> · ⌛ 15-day founder lockup</span>
            </div>
          </div>

          <div style="background:#0f172a;border:1px solid #1e293b;border-left:3px solid #6366f1;
                      padding:10px 14px;border-radius:4px;">
            <div style="color:#e5e7eb;font-weight:bold;font-size:0.9rem;">Underwritten IPO</div>
            <div style="color:#94a3b8;font-size:0.8rem;line-height:1.6;">
              7% discount · Guaranteed capital · Up to 60% float · Min $50k
              <span style="color:#f59e0b;"> · ⌛ 30-day founder lockup</span>
            </div>
          </div>

          <div style="background:#0f172a;border:1px solid #1e293b;border-left:3px solid #22c55e;
                      padding:10px 14px;border-radius:4px;">
            <div style="color:#e5e7eb;font-weight:bold;font-size:0.9rem;">Income Shares IPO</div>
            <div style="color:#94a3b8;font-size:0.8rem;line-height:1.6;">
              3% discount · 10% annual dividend quarterly · Up to 40% float · Min $75k
              <span style="color:#f59e0b;"> · ⌛ 30-day founder lockup</span>
            </div>
          </div>

          <div style="background:#0f172a;border:1px solid #1e293b;border-left:3px solid #f59e0b;
                      padding:10px 14px;border-radius:4px;">
            <div style="color:#e5e7eb;font-weight:bold;font-size:0.9rem;">Dual-Class IPO</div>
            <div style="color:#94a3b8;font-size:0.8rem;line-height:1.6;">
              8% discount · Class B public + Class A founder · Up to 49% float · Min $100k · You keep &gt;51% votes
              <span style="color:#f59e0b;"> · ⌛ 60-day founder lockup</span>
            </div>
          </div>

          <div style="background:#0f172a;border:1px solid #1e293b;border-left:3px solid #ec4899;
                      padding:10px 14px;border-radius:4px;">
            <div style="color:#e5e7eb;font-weight:bold;font-size:0.9rem;">Preferred Share Offering</div>
            <div style="color:#94a3b8;font-size:0.8rem;line-height:1.6;">
              5% discount · Guaranteed quarterly dividends · 1.5× liquidation priority · Callable · Up to 40% float · Min $50k
              <span style="color:#f59e0b;"> · ⌛ 30-day founder lockup</span>
            </div>
          </div>

          <div style="background:#0f172a;border:1px solid #1e293b;border-left:3px solid #a855f7;
                      padding:10px 14px;border-radius:4px;">
            <div style="color:#e5e7eb;font-weight:bold;font-size:0.9rem;">Series A Growth Round</div>
            <div style="color:#94a3b8;font-size:0.8rem;line-height:1.6;">
              12% discount · +20% growth capital bonus · Up to 30% float · Min $150k
              <span style="color:#f59e0b;"> · ⌛ 60-day founder lockup</span>
            </div>
          </div>

          <div style="background:#0f172a;border:1px solid #1e293b;border-left:3px solid #d4af37;
                      padding:10px 14px;border-radius:4px;">
            <div style="color:#e5e7eb;font-weight:bold;font-size:0.9rem;">Quad-Class IPO</div>
            <div style="color:#94a3b8;font-size:0.8rem;line-height:1.6;">
              10% discount · 4 share classes · +15% growth bonus · 10% fixed dividend · 1.2× liquidation priority · Up to 60% float · Min $200k
              <span style="color:#f59e0b;"> · ⌛ 90-day founder lockup</span>
            </div>
          </div>

        <p style="color:#64748b;font-size:0.8rem;margin:8px 0 0 0;">
            ⌛ <strong style="color:#f59e0b;">Founder lockup</strong>: after your IPO, you cannot sell your founder shares until the lockup expires.
            All public companies also pay a <strong style="color:#f59e0b;">$500/month listing fee</strong> billed every 30 days.
        </p>

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
        <div style="background:#1c0f00;border:1px solid #f59e0b;border-radius:4px;padding:10px 14px;margin-bottom:14px;font-size:0.82rem;line-height:1.7;color:#fbbf24;">
            <strong>Know before you launch:</strong><br>
            ⌛ <strong>Founder lockup</strong> — you cannot sell your own shares for a period after IPO (15 to 90 days depending on IPO type). Plan your cash flow accordingly.<br>
            💳 <strong>Listing fee</strong> — your company owes $500/month billed every 30 days to stay listed. Miss 3 payments and trading halts automatically.
        </div>
        {cta}
        """

    elif step == 7:
        import json as _json
        _t3_video_id = "uneqXirAwKQ"  # fallback — "Demystifying IPO"
        try:
            with open("wiki_media.json", "r") as _f:
                _media = _json.load(_f)
            _t3_video_id = _media["videos"][2]["youtube_id"]
        except Exception:
            pass

        title = "IPO Complete — Watch & Claim Your Reward!"
        content = f"""
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 12px 0;">
            Your company is now publicly traded on the <strong style="color:#e5e7eb;">Wadsworth
            Public Exchange</strong>. Shareholders hold real stakes in your holding company,
            and your share price will reflect how well you run it.
        </p>
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 14px 0;">
            Watch the IPO deep-dive video, then claim your Tutorial 3 reward below.
        </p>

        <!-- YouTube IFrame Player -->
        <div style="position:relative;padding-bottom:56.25%;height:0;overflow:hidden;border-radius:6px;border:1px solid #1d2f55;margin-bottom:16px;">
            <div id="yt3-player-container" style="position:absolute;top:0;left:0;width:100%;height:100%;"></div>
        </div>

        <!-- Watch-progress bar -->
        <div id="tut3-watch-bar" style="background:#111c35;border:1px solid #1d2f55;border-radius:4px;height:6px;margin-bottom:12px;overflow:hidden;">
            <div id="tut3-watch-fill" style="background:#d4af37;height:6px;width:0%;transition:width .5s;"></div>
        </div>
        <p id="tut3-watch-label" style="color:#64748b;font-size:0.8rem;margin:0 0 16px 0;text-align:center;">
            ⏳ Watch the video to unlock your reward…
        </p>

        <!-- Reward section — hidden until video watched -->
        <div id="tut3-reward-section" style="display:none;">
            <div style="background:rgba(212,175,55,0.08);border:1px solid rgba(212,175,55,0.35);
                        border-radius:6px;padding:14px 18px;margin-bottom:16px;">
                <strong style="color:#d4af37;">Tutorial 3 Reward — Margin Lending Unlocked</strong>
                <p style="color:#94a3b8;margin:6px 0 0;line-height:1.6;">
                    You can now borrow up to <strong style="color:#e5e7eb;">50% of your equity portfolio value</strong>
                    as a margin loan to amplify your positions. Visit the Brokerage Firm dashboard to access it.
                    Use leverage wisely — margin calls are real.
                </p>
            </div>
            <form action="/api/tutorial3/advance" method="post">
                <button type="submit"
                        style="background:#d4af37;color:#020617;border:none;padding:10px 24px;
                               border-radius:4px;cursor:pointer;font-size:0.9rem;font-weight:bold;">
                    Claim Reward &amp; Complete Tutorial 3 →
                </button>
            </form>
        </div>

        <script>
        (function() {{
            var WATCH_THRESHOLD = 0.90;
            var watched = false;

            function unlockReward() {{
                if (watched) return;
                watched = true;
                document.getElementById('tut3-watch-label').innerHTML =
                    '<span style="color:#4ade80;">✓ Video complete! Claim your reward below.</span>';
                document.getElementById('tut3-watch-fill').style.width = '100%';
                document.getElementById('tut3-reward-section').style.display = 'block';
            }}

            var tag = document.createElement('script');
            tag.src = 'https://www.youtube.com/iframe_api';
            document.head.appendChild(tag);

            var ytPlayer3;
            window.onYouTubeIframeAPIReady = function() {{
                ytPlayer3 = new YT.Player('yt3-player-container', {{
                    videoId: '{_t3_video_id}',
                    playerVars: {{ rel: 0, modestbranding: 1 }},
                    events: {{
                        onStateChange: function(e) {{
                            if (e.data === YT.PlayerState.ENDED) unlockReward();
                        }}
                    }}
                }});
            }};

            var pollTimer = setInterval(function() {{
                if (!ytPlayer3 || typeof ytPlayer3.getCurrentTime !== 'function') return;
                try {{
                    var cur = ytPlayer3.getCurrentTime();
                    var dur = ytPlayer3.getDuration();
                    if (dur > 0) {{
                        var pct = Math.min(cur / dur, 1);
                        document.getElementById('tut3-watch-fill').style.width = (pct * 100).toFixed(1) + '%';
                        if (pct >= WATCH_THRESHOLD) {{ unlockReward(); clearInterval(pollTimer); }}
                    }}
                }} catch(ex) {{}}
            }}, 2000);
        }})();
        </script>
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


# ══════════════════════════════════════════════════════════════════════════════
# TUTORIAL 4 — ETFs & Market Indices
# ══════════════════════════════════════════════════════════════════════════════
#
# Steps:
#   0  — Not started (T4 banner on dashboard after T3 complete)
#   1  — Introduction to Market Indices  (/banks/indices)
#   2  — Explore the grid, then visit WBC-50  (/banks/indices)
#   3  — WBC-50 deep dive  (/banks/indices/WBC50)
#   4  — ETFs vs Indices explained  (/banks/indices/WBC50)
#   5  — Watch Tutorial 4 video  (/banks/indices/WBC50)
#   6  — Claim reward: Tax Voucher $100,000  (/banks/indices/WBC50)
#   7  — Complete  (redirect → /corporate-actions/dashboard)

T4_TOTAL_STEPS = 6


def get_tutorial4_step(player_id: int) -> int:
    """Return the player's current Tutorial 4 step (0–7)."""
    try:
        from auth import get_db, Player
        db = get_db()
        player = db.query(Player).filter(Player.id == player_id).first()
        db.close()
        if player is None:
            return 0
        step = getattr(player, "tutorial_4_step", 0)
        return step if step is not None else 0
    except Exception as e:
        print(f"[Tutorial4] get_tutorial4_step error: {e}")
        return 0


def set_tutorial4_step(player_id: int, step: int):
    """Set the player's Tutorial 4 step."""
    try:
        from auth import get_db, Player
        db = get_db()
        player = db.query(Player).filter(Player.id == player_id).first()
        if player:
            player.tutorial_4_step = step
            db.commit()
        db.close()
    except Exception as e:
        print(f"[Tutorial4] set_tutorial4_step error: {e}")


def should_show_tutorial4_banner(player) -> bool:
    """Show the T4 start banner only after Tutorial 3 is complete and T4 not yet started."""
    t3 = getattr(player, "tutorial_3_step", 0) or 0
    t4 = getattr(player, "tutorial_4_step", 0) or 0
    return t3 >= 8 and t4 == 0


# ── Tutorial 4 overlay HTML generator ─────────────────────────────────────────

def get_tutorial4_overlay_html(player, current_page: str) -> str:
    """
    Return the Tutorial 4 overlay panel HTML for the given page.
    `current_page` is one of: 'banks_indices', 'banks_indices_wbc50'.
    Returns empty string if T4 is not active or wrong page.
    """
    step = get_tutorial4_step(player.id)
    if step == 0 or step >= 7:
        return ""

    T4_STEP_PAGE = {
        1: "banks_indices",
        2: "banks_indices",
        3: "banks_indices_wbc50",
        4: "banks_indices_wbc50",
        5: "banks_indices_wbc50",
        6: "banks_indices_wbc50",
    }

    if T4_STEP_PAGE.get(step, "") != current_page:
        return ""

    try:
        from reserve_banks import get_player_display_currency, fmt_usd
        disp = get_player_display_currency(player.id)
        reward_display = fmt_usd(100_000.0, disp)
    except Exception:
        disp = None
        reward_display = "$100,000"

    title = ""
    content = ""

    if step == 1:
        title = "Welcome to the Market Indices"
        content = """
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 12px 0;">
            A <strong style="color:#e5e7eb;">market index</strong> is a composite number that
            summarises the health of a slice of the Wadsworth economy. You're looking at
            <strong style="color:#38bdf8;">19 live indices</strong> — from total market cap
            (WBC-50) to bee populations (BEE) and fear sentiment (GFI).
        </p>
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 14px 0;">
            Each index is calculated automatically from real in-game data and snapshotted
            regularly so you can track trends over time with 30-day history charts and
            hourly candlesticks.
        </p>
        <form action="/api/tutorial4/advance" method="post" style="display:inline;">
            <button type="submit"
                    style="background:#d4af37;color:#020617;border:none;padding:10px 24px;
                           border-radius:4px;cursor:pointer;font-size:0.9rem;font-weight:bold;">
                Continue →
            </button>
        </form>
        """

    elif step == 2:
        title = "Explore the Grid, Then Visit WBC-50"
        content = """
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 12px 0;">
            Each card below shows a live index value, a 24-hour change, and a sparkline.
            Click any card to open the full detail page with charts, composition breakdowns,
            and a distribution heatmap.
        </p>
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 14px 0;">
            Your next stop is the <strong style="color:#38bdf8;">WBC-50 Index</strong> —
            Wadsworth's broadest market-cap measure. Click the <strong>WBC50</strong> card
            to continue your tutorial.
        </p>
        <form action="/api/tutorial4/advance" method="post" style="display:inline;">
            <button type="submit"
                    style="background:#d4af37;color:#020617;border:none;padding:10px 24px;
                           border-radius:4px;cursor:pointer;font-size:0.9rem;font-weight:bold;">
                Go to WBC-50 →
            </button>
        </form>
        """

    elif step == 3:
        title = "The WBC-50 Index — Wadsworth's Benchmark"
        content = """
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 12px 0;">
            The <strong style="color:#38bdf8;">WBC-50</strong> (Wadsworth Benchmark Composite 50)
            tracks the total market capitalisation of the top 50 entities in the economy —
            public companies valued at <em>shares outstanding × current price</em>, plus NPC
            private enterprises estimated by cash + land holdings.
        </p>
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 12px 0;">
            The <strong style="color:#e5e7eb;">30-Day History chart</strong> and
            <strong style="color:#e5e7eb;">7-Day OHLCV candlesticks</strong> let you spot
            growth trends, corrections, and volatility windows. The composition breakdown
            shows which entities hold the most weight.
        </p>
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 14px 0;">
            When WBC-50 rises, economic activity is expanding. When it falls, capital is
            leaving the market — watch it alongside the
            <strong style="color:#e5e7eb;">GFI (Greed &amp; Fear Index)</strong> for full
            sentiment context.
        </p>
        <form action="/api/tutorial4/advance" method="post" style="display:inline;">
            <button type="submit"
                    style="background:#d4af37;color:#020617;border:none;padding:10px 24px;
                           border-radius:4px;cursor:pointer;font-size:0.9rem;font-weight:bold;">
                Continue →
            </button>
        </form>
        """

    elif step == 4:
        title = "ETFs vs Indices — What's the Difference?"
        content = """
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 12px 0;">
            An <strong style="color:#e5e7eb;">index</strong> is a <em>number</em> — a read-only
            measure of the market. You cannot buy an index directly any more than you can
            "buy" the temperature outside.
        </p>
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 12px 0;">
            An <strong style="color:#22c55e;">ETF (Exchange-Traded Fund)</strong> is a
            <em>tradable product</em> designed to track an index. When you buy a WBC-50 ETF
            share, you're getting diversified exposure across the top 50 entities without
            owning each one individually.
        </p>
        <div style="background:#0f1f11;border:1px solid #22c55e;border-radius:4px;
                    padding:10px 14px;margin-bottom:14px;font-size:0.82rem;line-height:1.7;color:#4ade80;">
            <strong>Key rule:</strong> Indices show you what's happening.
            ETFs let you act on it.
        </div>
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 14px 0;">
            In Wadsworth, the Brokerage Firm hosts ETF shares linked to the WBC-50 and other
            indices. Their price floats with the underlying index value. Unlike company shares,
            ETF shares have no founder lockup and no listing fees.
        </p>
        <form action="/api/tutorial4/advance" method="post" style="display:inline;">
            <button type="submit"
                    style="background:#d4af37;color:#020617;border:none;padding:10px 24px;
                           border-radius:4px;cursor:pointer;font-size:0.9rem;font-weight:bold;">
                Watch the Video →
            </button>
        </form>
        """

    elif step == 5:
        import json as _json
        _t4_video_id = None
        try:
            with open("wiki_media.json", "r") as _f:
                _media = _json.load(_f)
            _t4_video_id = _media["videos"][3]["youtube_id"]
        except Exception:
            pass

        if _t4_video_id:
            video_block = f"""
        <!-- YouTube IFrame Player -->
        <div style="position:relative;padding-bottom:56.25%;height:0;overflow:hidden;
                    border-radius:6px;border:1px solid #1d2f55;margin-bottom:16px;">
            <div id="yt4-player-container"
                 style="position:absolute;top:0;left:0;width:100%;height:100%;"></div>
        </div>

        <!-- Watch-progress bar -->
        <div id="tut4-watch-bar" style="background:#111c35;border:1px solid #1d2f55;
                 border-radius:4px;height:6px;margin-bottom:12px;overflow:hidden;">
            <div id="tut4-watch-fill"
                 style="background:#d4af37;height:6px;width:0%;transition:width .5s;"></div>
        </div>
        <p id="tut4-watch-label" style="color:#64748b;font-size:0.8rem;
               margin:0 0 16px 0;text-align:center;">
            ⏳ Watch the video to unlock your reward…
        </p>

        <!-- Reward section — hidden until video watched -->
        <div id="tut4-reward-section" style="display:none;">
            <div style="background:rgba(212,175,55,0.08);border:1px solid rgba(212,175,55,0.35);
                        border-radius:6px;padding:14px 18px;margin-bottom:16px;">
                <strong style="color:#d4af37;">Tutorial 4 Reward — Tax Voucher {reward_display}</strong>
                <p style="color:#94a3b8;margin:6px 0 0;line-height:1.6;">
                    The government is awarding you a
                    <strong style="color:#22c55e;">Tax Voucher worth {reward_display}</strong>
                    for completing the ETFs &amp; Indices tutorial. Redeem it any time in your
                    Corporate Actions dashboard to receive instant cash.
                </p>
            </div>
            <form action="/api/tutorial4/claim-reward" method="post">
                <button type="submit"
                        style="background:#d4af37;color:#020617;border:none;padding:10px 24px;
                               border-radius:4px;cursor:pointer;font-size:0.9rem;font-weight:bold;">
                    Claim Reward &amp; Complete Tutorial 4 →
                </button>
            </form>
        </div>

        <script>
        (function() {{
            var WATCH_THRESHOLD = 0.90;
            var watched = false;

            function unlockReward4() {{
                if (watched) return;
                watched = true;
                document.getElementById('tut4-watch-label').innerHTML =
                    '<span style="color:#4ade80;">✓ Video complete! Claim your reward below.</span>';
                document.getElementById('tut4-watch-fill').style.width = '100%';
                document.getElementById('tut4-reward-section').style.display = 'block';
            }}

            var tag = document.createElement('script');
            tag.src = 'https://www.youtube.com/iframe_api';
            document.head.appendChild(tag);

            var ytPlayer4;
            window.onYouTubeIframeAPIReady = function() {{
                ytPlayer4 = new YT.Player('yt4-player-container', {{
                    videoId: '{_t4_video_id}',
                    playerVars: {{ rel: 0, modestbranding: 1 }},
                    events: {{
                        onStateChange: function(e) {{
                            if (e.data === YT.PlayerState.ENDED) unlockReward4();
                        }}
                    }}
                }});
            }};

            var pollTimer = setInterval(function() {{
                if (!ytPlayer4 || typeof ytPlayer4.getCurrentTime !== 'function') return;
                try {{
                    var cur = ytPlayer4.getCurrentTime();
                    var dur = ytPlayer4.getDuration();
                    if (dur > 0) {{
                        var pct = Math.min(cur / dur, 1);
                        document.getElementById('tut4-watch-fill').style.width =
                            (pct * 100).toFixed(1) + '%';
                        if (pct >= WATCH_THRESHOLD) {{
                            unlockReward4();
                            clearInterval(pollTimer);
                        }}
                    }}
                }} catch(ex) {{}}
            }}, 2000);
        }})();
        </script>
            """
        else:
            # No video uploaded yet — skip straight to reward
            video_block = f"""
        <div style="background:#1c1a00;border:1px solid #ca8a04;border-radius:4px;
                    padding:10px 14px;margin-bottom:16px;font-size:0.82rem;
                    color:#fbbf24;line-height:1.6;">
            ⚠ The Tutorial 4 video hasn't been uploaded yet — check back soon!
        </div>
        <div style="background:rgba(212,175,55,0.08);border:1px solid rgba(212,175,55,0.35);
                    border-radius:6px;padding:14px 18px;margin-bottom:16px;">
            <strong style="color:#d4af37;">Tutorial 4 Reward — Tax Voucher {reward_display}</strong>
            <p style="color:#94a3b8;margin:6px 0 0;line-height:1.6;">
                Claim your <strong style="color:#22c55e;">Tax Voucher worth {reward_display}</strong>
                below. Redeem it any time in your Corporate Actions dashboard for instant cash.
            </p>
        </div>
        <form action="/api/tutorial4/claim-reward" method="post">
            <button type="submit"
                    style="background:#d4af37;color:#020617;border:none;padding:10px 24px;
                           border-radius:4px;cursor:pointer;font-size:0.9rem;font-weight:bold;">
                Claim Reward &amp; Complete Tutorial 4 →
            </button>
        </form>
            """

        title = "Watch &amp; Claim Your Reward"
        content = f"""
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 14px 0;">
            You've explored market indices and learned how ETFs work.
            Watch the video below, then claim your Tax Voucher reward.
        </p>
        {video_block}
        """

    elif step == 6:
        # Shouldn't normally show — step 6 is the claim-reward endpoint
        return ""

    else:
        return ""

    # ── display step counter (steps 1-6, not beyond) ──────────────────────────
    display_step = min(step, T4_TOTAL_STEPS)

    return f"""
    <div id="tutorial4-panel" style="
        background: linear-gradient(135deg, #061620, #0f172a);
        border: 2px solid #38bdf8;
        border-radius: 6px;
        padding: 20px 24px;
        margin-bottom: 24px;
        position: relative;
    ">
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:14px;flex-wrap:wrap;">
            <span style="background:#38bdf8;color:#020617;padding:3px 12px;border-radius:12px;
                         font-size:0.7rem;font-weight:bold;letter-spacing:0.05em;">
                TUTORIAL 4 — STEP {display_step}/{T4_TOTAL_STEPS}
            </span>
            <span style="color:#38bdf8;font-size:0.85rem;font-weight:bold;">Level 4 · ETFs &amp; Market Indices</span>
            <div style="flex:1;background:#1e293b;height:4px;border-radius:2px;min-width:80px;">
                <div style="background:#38bdf8;height:4px;border-radius:2px;
                            width:{int(display_step / T4_TOTAL_STEPS * 100)}%;"></div>
            </div>
        </div>
        <h3 style="color:#38bdf8;margin:0 0 12px 0;font-size:1.05rem;">{title}</h3>
        {content}
        <a href="/api/tutorial4/dismiss"
           onclick="return confirm('Skip Tutorial 4? You can restart it from Settings.');"
           style="position:absolute;top:12px;right:16px;color:#475569;font-size:0.72rem;text-decoration:none;">
            Skip
        </a>
    </div>
    """


# ── Tutorial 4 banner (shown on dashboard when T3 done and T4 not started) ────

def get_tutorial4_banner_html(player) -> str:
    """Return the T4 start banner HTML, or empty string if not applicable."""
    if not should_show_tutorial4_banner(player):
        return ""
    return f"""
    <div style="
        background: linear-gradient(135deg, #061620, #0f172a);
        border: 2px solid #38bdf8;
        border-radius: 6px;
        padding: 20px 24px;
        margin-bottom: 24px;
    ">
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:14px;flex-wrap:wrap;">
            <span style="background:#38bdf8;color:#020617;padding:3px 12px;border-radius:12px;
                         font-size:0.7rem;font-weight:bold;letter-spacing:0.05em;">
                NEW TUTORIAL AVAILABLE
            </span>
            <span style="color:#38bdf8;font-size:0.85rem;font-weight:bold;">Level 4 · ETFs &amp; Market Indices</span>
        </div>
        <h3 style="color:#38bdf8;margin:0 0 10px 0;font-size:1.05rem;">
            Understand the Markets
        </h3>
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 16px 0;">
            Tutorial 4 walks you through the <strong style="color:#e5e7eb;">19 Market Indices</strong>,
            the <strong style="color:#e5e7eb;">WBC-50 Benchmark</strong>, and how
            <strong style="color:#e5e7eb;">ETFs</strong> let you invest in the broad market
            without picking individual stocks. Complete it and earn a
            <strong style="color:#22c55e;">Tax Voucher reward</strong>.
        </p>
        <form action="/api/tutorial4/start" method="post" style="display:inline;">
            <button type="submit"
                    style="background:#38bdf8;color:#020617;border:none;padding:10px 24px;
                           border-radius:4px;cursor:pointer;font-size:0.9rem;font-weight:bold;">
                Start Tutorial 4 →
            </button>
        </form>
        <a href="/api/tutorial4/dismiss"
           style="margin-left:16px;color:#475569;font-size:0.82rem;">
            Dismiss
        </a>
    </div>
    """


# ── Tutorial 4 API routes ──────────────────────────────────────────────────────

@router.post("/api/tutorial4/start")
def tutorial4_start(session_token: Optional[str] = Cookie(None)):
    """Start Tutorial 4 (step 0 → 1)."""
    player = _get_player_from_cookie(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)
    if get_tutorial4_step(player.id) == 0:
        set_tutorial4_step(player.id, 1)
    return RedirectResponse(url="/banks/indices", status_code=303)


@router.post("/api/tutorial4/advance")
def tutorial4_advance(session_token: Optional[str] = Cookie(None)):
    """Advance Tutorial 4 to the next step."""
    player = _get_player_from_cookie(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)

    step = get_tutorial4_step(player.id)

    NEXT_REDIRECT = {
        1: "/banks/indices",
        2: "/banks/indices/WBC50",
        3: "/banks/indices/WBC50",
        4: "/banks/indices/WBC50",
        5: "/banks/indices/WBC50",
    }

    if step == 0 or step >= 7:
        return RedirectResponse(url="/", status_code=303)

    set_tutorial4_step(player.id, step + 1)
    redirect_url = NEXT_REDIRECT.get(step, "/banks/indices")
    return RedirectResponse(url=redirect_url, status_code=303)


@router.post("/api/tutorial4/claim-reward")
def tutorial4_claim_reward(session_token: Optional[str] = Cookie(None)):
    """Grant the Tutorial 4 Tax Voucher reward and complete the tutorial."""
    player = _get_player_from_cookie(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)

    step = get_tutorial4_step(player.id)
    if step not in (5, 6):
        return RedirectResponse(url="/banks/indices", status_code=303)

    # Grant a $100,000 USD Tax Voucher (source_dividend_id=None = tutorial grant)
    try:
        from corporate_actions import TaxVoucher, get_db as get_ca_db
        db = get_ca_db()
        voucher = TaxVoucher(player_id=player.id, amount=100_000.0, source_dividend_id=None)
        db.add(voucher)
        db.commit()
        db.close()
    except Exception as e:
        print(f"[Tutorial4] Failed to grant tax voucher for player {player.id}: {e}")

    set_tutorial4_step(player.id, 7)
    return RedirectResponse(url="/corporate-actions/dashboard?t4_reward=1", status_code=303)


@router.get("/api/tutorial4/dismiss")
def tutorial4_dismiss(session_token: Optional[str] = Cookie(None)):
    """Dismiss / skip Tutorial 4."""
    player = _get_player_from_cookie(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)
    set_tutorial4_step(player.id, 7)
    return RedirectResponse(url="/", status_code=303)


# ══════════════════════════════════════════════════════════════════════════════
# TUTORIAL 5 — Corporate Actions / Acquisitions & Income Stakes
# ══════════════════════════════════════════════════════════════════════════════
#
#   0  — Not started  (banner shown after T4 complete)
#   1  — What is an income stake?           (corporate-actions/dashboard)
#   2  — Making an offer                    (corporate-actions/dashboard)
#   3  — Receiving an offer                 (corporate-actions/dashboard)
#   4  — Counter-offers & income sweep      (corporate-actions/dashboard)
#   5  — Exiting a stake                   (corporate-actions/dashboard)
#   6  — Watch video & claim First Lady     (corporate-actions/dashboard)
#   7  — Complete

T5_TOTAL_STEPS = 6


def should_show_tutorial5_banner(player) -> bool:
    """Show the T5 start banner only after Tutorial 4 is complete and T5 not yet started."""
    t4 = getattr(player, "tutorial_4_step", 0) or 0
    t5 = getattr(player, "tutorial_5_step", 0) or 0
    return t4 >= 7 and t5 == 0


def get_tutorial5_banner_html(player) -> str:
    """Return the T5 start banner HTML, or empty string if not applicable."""
    if not should_show_tutorial5_banner(player):
        return ""
    return """
    <div style="
        background: linear-gradient(135deg, #1a0e00, #0f172a);
        border: 2px solid #f59e0b;
        border-radius: 6px;
        padding: 20px 24px;
        margin-bottom: 24px;
    ">
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:14px;flex-wrap:wrap;">
            <span style="background:#f59e0b;color:#020617;padding:3px 12px;border-radius:12px;
                         font-size:0.7rem;font-weight:bold;letter-spacing:0.05em;">
                NEW TUTORIAL AVAILABLE
            </span>
            <span style="color:#f59e0b;font-size:0.85rem;font-weight:bold;">Level 5 &middot; Acquisitions &amp; Income Stakes</span>
        </div>
        <h3 style="color:#f59e0b;margin:0 0 10px 0;font-size:1.05rem;">
            Master Corporate Acquisitions
        </h3>
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 16px 0;">
            Tutorial 5 covers <strong style="color:#e5e7eb;">Income Stakes</strong> and
            <strong style="color:#e5e7eb;">Corporate Acquisitions</strong> — buy a percentage
            of another player's income stream or acquire their business outright using shares.
            Complete it to earn a <strong style="color:#d4af37;">First Lady executive</strong> reward.
        </p>
        <form action="/api/tutorial5/start" method="post" style="display:inline;">
            <button type="submit"
                    style="background:#f59e0b;color:#020617;border:none;padding:10px 24px;
                           border-radius:4px;cursor:pointer;font-size:0.9rem;font-weight:bold;">
                Start Tutorial 5 &rarr;
            </button>
        </form>
        <a href="/api/tutorial5/dismiss"
           style="margin-left:16px;color:#475569;font-size:0.82rem;">
            Dismiss
        </a>
    </div>
    """


def get_tutorial5_step(player_id: int) -> int:
    """Return the player's current Tutorial 5 step (0–7)."""
    try:
        from auth import get_db, Player
        db = get_db()
        player = db.query(Player).filter(Player.id == player_id).first()
        db.close()
        if player is None:
            return 0
        step = getattr(player, "tutorial_5_step", 0)
        return step if step is not None else 0
    except Exception as e:
        print(f"[Tutorial5] get_tutorial5_step error: {e}")
        return 0


def set_tutorial5_step(player_id: int, step: int):
    """Set the player's Tutorial 5 step."""
    try:
        from auth import get_db, Player
        db = get_db()
        player = db.query(Player).filter(Player.id == player_id).first()
        if player:
            player.tutorial_5_step = step
            db.commit()
        db.close()
    except Exception as e:
        print(f"[Tutorial5] set_tutorial5_step error: {e}")


# ── Tutorial 5 overlay HTML generator ─────────────────────────────────────────

def get_tutorial5_overlay_html(player, current_page: str) -> str:
    """
    Return the Tutorial 5 overlay panel HTML for the given page.
    `current_page` must be 'corporate_actions_dashboard'.
    Returns empty string if T5 is not active or wrong page.
    """
    step = get_tutorial5_step(player.id)
    if step == 0 or step >= 7:
        return ""

    if current_page != "corporate_actions_dashboard":
        return ""

    title = ""
    content = ""

    if step == 1:
        title = "What Is an Income Stake?"
        content = """
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 12px 0;">
            An <strong style="color:#e5e7eb;">income stake</strong> is a contractual right to receive
            a fixed percentage of another player's <em>net business income</em> — every day,
            automatically, for as long as the stake is active.
        </p>
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 12px 0;">
            As the <strong style="color:#f59e0b;">acquirer</strong> you pay the target with shares in
            your own company (plus an optional cash sweetener). In exchange, the target lets you
            <em>sweep</em> a portion of their earnings — retail sales, dividends, bond maturities,
            market sells, and more.
        </p>
        <div style="background:#1a1200;border:1px solid #92400e;border-radius:4px;
                    padding:10px 14px;margin-bottom:14px;font-size:0.82rem;line-height:1.7;color:#fbbf24;">
            <strong>Key rule:</strong> Taxes are excluded from the sweep — only <em>net</em> income
            after taxes is shared with the acquirer.
        </div>
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 14px 0;">
            Stakes can be perpetual or time-limited (30 / 60 / 90 / 180 / 365 days).
            All payouts are made in each player's own legal tender, regardless of which
            currency the deal was struck in.
        </p>
        <form action="/api/tutorial5/advance" method="post" style="display:inline;">
            <button type="submit"
                    style="background:#f59e0b;color:#020617;border:none;padding:10px 24px;
                           border-radius:4px;cursor:pointer;font-size:0.9rem;font-weight:bold;">
                Continue →
            </button>
        </form>
        """

    elif step == 2:
        title = "Making an Acquisition Offer"
        content = """
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 12px 0;">
            To make an offer, scroll down to any of your public companies and open the
            <strong style="color:#e5e7eb;">Acquisitions</strong> tab.
            You'll specify:
        </p>
        <ul style="color:#94a3b8;line-height:1.9;margin:0 0 12px 20px;font-size:0.9rem;">
            <li><strong style="color:#e5e7eb;">Target player</strong> — find their ID on the Leaderboard</li>
            <li><strong style="color:#e5e7eb;">Shares offered</strong> — from your own company's holdings</li>
            <li><strong style="color:#e5e7eb;">Stake %</strong> — 0.1 % to 50 % of net income</li>
            <li><strong style="color:#e5e7eb;">Cash sweetener</strong> — optional extra cash to sweeten the deal</li>
            <li><strong style="color:#e5e7eb;">Term</strong> — perpetual, or 30 / 60 / 90 / 180 / 365 days</li>
            <li><strong style="color:#e5e7eb;">Lock-up</strong> — minimum days before exit is allowed (default 7)</li>
        </ul>
        <div style="background:#0f1a00;border:1px solid #3f6212;border-radius:4px;
                    padding:10px 14px;margin-bottom:14px;font-size:0.82rem;line-height:1.7;color:#86efac;">
            <strong>Escrow:</strong> Any cash sweetener is <em>deducted from your balance immediately</em>
            when the offer is sent. It's held in escrow and returned to you if the target
            rejects or ignores the offer within 7 days.
        </div>
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 14px 0;">
            Once sent, the target has 7 days to accept, reject, or counter. You can cancel a
            pending offer at any time before they respond — the escrow is refunded to your wallet.
        </p>
        <form action="/api/tutorial5/advance" method="post" style="display:inline;">
            <button type="submit"
                    style="background:#f59e0b;color:#020617;border:none;padding:10px 24px;
                           border-radius:4px;cursor:pointer;font-size:0.9rem;font-weight:bold;">
                Continue →
            </button>
        </form>
        """

    elif step == 3:
        title = "Receiving an Offer — Accept, Reject, or Counter"
        content = """
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 12px 0;">
            When another player sends you an offer, you'll see it in your
            <strong style="color:#e5e7eb;">Incoming Offers</strong> section here on the dashboard.
            You have three choices:
        </p>
        <div style="display:grid;gap:10px;margin-bottom:14px;">
            <div style="background:#0f1f11;border:1px solid #166534;border-radius:4px;
                        padding:10px 14px;font-size:0.84rem;color:#86efac;">
                <strong>✓ Accept</strong> — The stake activates immediately. The acquirer's shares
                transfer to you and, if there's a cash sweetener, it's released from escrow
                straight to your wallet.
            </div>
            <div style="background:#1f0f0f;border:1px solid #991b1b;border-radius:4px;
                        padding:10px 14px;font-size:0.84rem;color:#fca5a5;">
                <strong>✗ Reject</strong> — The offer closes. The escrow cash is returned
                to the acquirer automatically in their own legal tender.
            </div>
            <div style="background:#1a1000;border:1px solid #92400e;border-radius:4px;
                        padding:10px 14px;font-size:0.84rem;color:#fcd34d;">
                <strong>⇄ Counter</strong> — Propose new terms: a different stake %,
                different shares, or a different cash component. The original offer is
                put on hold while your counter is reviewed.
            </div>
        </div>
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 14px 0;">
            All three actions can be taken directly from this dashboard
            without needing to navigate anywhere else.
        </p>
        <form action="/api/tutorial5/advance" method="post" style="display:inline;">
            <button type="submit"
                    style="background:#f59e0b;color:#020617;border:none;padding:10px 24px;
                           border-radius:4px;cursor:pointer;font-size:0.9rem;font-weight:bold;">
                Continue →
            </button>
        </form>
        """

    elif step == 4:
        title = "Counter-Offers, Income Sweep &amp; Multi-Currency"
        content = """
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 10px 0;">
            <strong style="color:#e5e7eb;">Counter-offers</strong> work in both directions.
            When you counter an incoming offer, the acquirer can accept, reject <em>your counter</em>,
            or let it expire. Rejecting a counter reverts the original offer back to
            <em>pending</em> — giving the target a second chance to accept or reject the original terms.
        </p>
        <div style="background:#0a1628;border:1px solid #1d4ed8;border-radius:4px;
                    padding:10px 14px;margin-bottom:12px;font-size:0.82rem;line-height:1.7;color:#93c5fd;">
            <strong>Income Sweep — what gets shared:</strong><br>
            Retail sales · Market sells · Dividends · Bond maturities &amp; calls · Bond sells ·
            District market sells · Share sells · P2P contract payments · Crypto sells ·
            City application income.<br>
            <em>Taxes and district taxes are excluded before the split is calculated.</em>
        </div>
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 14px 0;">
            The daily sweep deducts the acquirer's share directly from the target via
            <em>spend_player_funds</em> and credits the acquirer via <em>convert_to_legal_tender</em>
            — so each player always receives and pays in their own currency, no matter what
            currency the original deal was denominated in.
        </p>
        <form action="/api/tutorial5/advance" method="post" style="display:inline;">
            <button type="submit"
                    style="background:#f59e0b;color:#020617;border:none;padding:10px 24px;
                           border-radius:4px;cursor:pointer;font-size:0.9rem;font-weight:bold;">
                Continue →
            </button>
        </form>
        """

    elif step == 5:
        title = "Exiting a Stake — Diffuse &amp; Target Buyout"
        content = """
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 10px 0;">
            Once the lock-up period has passed, either side can exit the stake.
            There are three exit mechanisms:
        </p>
        <div style="display:grid;gap:10px;margin-bottom:16px;">
            <div style="background:#0a1628;border:1px solid #1d4ed8;border-radius:4px;
                        padding:10px 14px;font-size:0.84rem;line-height:1.7;">
                <strong style="color:#93c5fd;">Diffuse — Share Return</strong>
                <p style="color:#94a3b8;margin:4px 0 0;">
                    The acquirer initiates. The target has <strong>30 days</strong> to return
                    the original shares. If they default, a government lien is placed on their
                    assets for the market value of the shares.
                </p>
            </div>
            <div style="background:#0f1f11;border:1px solid #166534;border-radius:4px;
                        padding:10px 14px;font-size:0.84rem;line-height:1.7;">
                <strong style="color:#86efac;">Diffuse — Cash Buyout</strong>
                <p style="color:#94a3b8;margin:4px 0 0;">
                    The acquirer pays the target the current market value of the shares
                    instead of receiving them back. The stake ends immediately — no 30-day window.
                </p>
            </div>
            <div style="background:#1a1000;border:1px solid #92400e;border-radius:4px;
                        padding:10px 14px;font-size:0.84rem;line-height:1.7;">
                <strong style="color:#fcd34d;">Target Buyout</strong>
                <p style="color:#94a3b8;margin:4px 0 0;">
                    A defensive exit for the <em>target</em>. The target pays the acquirer
                    the current market value of the held shares, ending the stake immediately.
                    The acquirer keeps the cash; the target gets their income stream back.
                </p>
            </div>
        </div>
        <form action="/api/tutorial5/advance" method="post" style="display:inline;">
            <button type="submit"
                    style="background:#f59e0b;color:#020617;border:none;padding:10px 24px;
                           border-radius:4px;cursor:pointer;font-size:0.9rem;font-weight:bold;">
                Continue →
            </button>
        </form>
        """

    elif step == 6:
        # Video + First Lady claim (mirrors T4 step 5 pattern)
        _t5_video_id = None
        try:
            import json as _json
            with open("wiki_media.json", "r") as _f:
                _media = _json.load(_f)
            if len(_media.get("videos", [])) > 4:
                _t5_video_id = _media["videos"][4]["youtube_id"]
        except Exception:
            pass

        try:
            from executive import FIRST_LADY_EXECUTIVES as _FL_EXECS
            fl_opts = "".join(
                f'<option value="{fl["key"]}">{fl["name"]} ({fl["years"]}) — {fl["real_role"]}</option>'
                for fl in _FL_EXECS
            )
        except Exception:
            fl_opts = '<option value="martha_washington">Martha Washington</option>'

        fl_form = f"""
        <form action="/api/tutorial5/claim-reward" method="post"
              style="display:flex;flex-wrap:wrap;gap:8px;align-items:center;">
            <select name="first_lady"
                    style="flex:1;min-width:220px;padding:7px 10px;background:#1e293b;
                           border:1px solid #334155;border-radius:4px;color:#f1f5f9;
                           font-size:0.78rem;cursor:pointer;">
                {fl_opts}
            </select>
            <button type="submit"
                    style="background:#f59e0b;color:#020617;border:none;padding:10px 20px;
                           border-radius:4px;cursor:pointer;font-size:0.9rem;font-weight:bold;
                           white-space:nowrap;">
                Claim First Lady &amp; Complete →
            </button>
        </form>
        """

        if _t5_video_id:
            video_block = f"""
        <div style="position:relative;padding-bottom:56.25%;height:0;overflow:hidden;
                    border-radius:6px;border:1px solid #2d1a00;margin-bottom:16px;">
            <div id="yt5-player-container"
                 style="position:absolute;top:0;left:0;width:100%;height:100%;"></div>
        </div>
        <div id="tut5-watch-bar" style="background:#1a0e00;border:1px solid #92400e;
                 border-radius:4px;height:6px;margin-bottom:12px;overflow:hidden;">
            <div id="tut5-watch-fill"
                 style="background:#f59e0b;height:6px;width:0%;transition:width .5s;"></div>
        </div>
        <p id="tut5-watch-label" style="color:#64748b;font-size:0.8rem;
               margin:0 0 16px 0;text-align:center;">
            ⏳ Watch the video to unlock your First Lady selection…
        </p>
        <div id="tut5-reward-section" style="display:none;">
            <div style="background:rgba(245,158,11,0.08);border:1px solid rgba(245,158,11,0.35);
                        border-radius:6px;padding:14px 18px;margin-bottom:16px;">
                <strong style="color:#f59e0b;">Tutorial 5 Reward — First Lady Executive</strong>
                <p style="color:#94a3b8;margin:6px 0 0;line-height:1.6;">
                    Choose a <strong style="color:#d4af37;">Former First Lady</strong> executive —
                    free forever, starts age 18, retires at 110, max level 18.
                </p>
            </div>
            {fl_form}
        </div>
        <script>
        (function() {{
            var WATCH_THRESHOLD = 0.90;
            var watched = false;
            function unlockReward5() {{
                if (watched) return;
                watched = true;
                document.getElementById('tut5-watch-label').innerHTML =
                    '<span style="color:#4ade80;">✓ Video complete! Choose your First Lady below.</span>';
                document.getElementById('tut5-watch-fill').style.width = '100%';
                document.getElementById('tut5-reward-section').style.display = 'block';
            }}
            var tag = document.createElement('script');
            tag.src = 'https://www.youtube.com/iframe_api';
            document.head.appendChild(tag);
            var ytPlayer5;
            window.onYouTubeIframeAPIReady = function() {{
                ytPlayer5 = new YT.Player('yt5-player-container', {{
                    videoId: '{_t5_video_id}',
                    playerVars: {{ rel: 0, modestbranding: 1 }},
                    events: {{
                        onStateChange: function(e) {{
                            if (e.data === YT.PlayerState.ENDED) unlockReward5();
                        }}
                    }}
                }});
            }};
            var pollTimer = setInterval(function() {{
                if (!ytPlayer5 || typeof ytPlayer5.getCurrentTime !== 'function') return;
                try {{
                    var cur = ytPlayer5.getCurrentTime();
                    var dur = ytPlayer5.getDuration();
                    if (dur > 0) {{
                        var pct = Math.min(cur / dur, 1);
                        document.getElementById('tut5-watch-fill').style.width =
                            (pct * 100).toFixed(1) + '%';
                        if (pct >= WATCH_THRESHOLD) {{ unlockReward5(); clearInterval(pollTimer); }}
                    }}
                }} catch(ex) {{}}
            }}, 2000);
        }})();
        </script>
            """
        else:
            # No video uploaded yet — show reward selector directly
            video_block = f"""
        <div style="background:#1c1a00;border:1px solid #ca8a04;border-radius:4px;
                    padding:10px 14px;margin-bottom:16px;font-size:0.82rem;
                    color:#fbbf24;line-height:1.6;">
            ⚠ The Tutorial 5 video hasn't been uploaded yet — check back soon!
        </div>
        <div style="background:rgba(245,158,11,0.08);border:1px solid rgba(245,158,11,0.35);
                    border-radius:6px;padding:14px 18px;margin-bottom:16px;">
            <strong style="color:#f59e0b;">Tutorial 5 Reward — First Lady Executive</strong>
            <p style="color:#94a3b8;margin:6px 0 0;line-height:1.6;">
                Choose a <strong style="color:#d4af37;">Former First Lady</strong> executive —
                free forever, starts age 18, retires at 110, max level 18.
            </p>
        </div>
        {fl_form}
            """

        title = "Watch &amp; Claim Your Reward"
        content = f"""
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 14px 0;">
            You've completed the acquisitions &amp; income stake curriculum.
            Watch the video below, then choose your First Lady executive reward.
        </p>
        {video_block}
        """

    else:
        return ""

    display_step = min(step, T5_TOTAL_STEPS)

    return f"""
    <div id="tutorial5-panel" style="
        background: linear-gradient(135deg, #1a0e00, #0f172a);
        border: 2px solid #f59e0b;
        border-radius: 6px;
        padding: 20px 24px;
        margin-bottom: 24px;
        position: relative;
    ">
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:14px;flex-wrap:wrap;">
            <span style="background:#f59e0b;color:#020617;padding:3px 12px;border-radius:12px;
                         font-size:0.7rem;font-weight:bold;letter-spacing:0.05em;">
                TUTORIAL 5 — STEP {display_step}/{T5_TOTAL_STEPS}
            </span>
            <span style="color:#f59e0b;font-size:0.85rem;font-weight:bold;">Level 5 · Acquisitions &amp; Income Stakes</span>
            <div style="flex:1;background:#1e293b;height:4px;border-radius:2px;min-width:80px;">
                <div style="background:#f59e0b;height:4px;border-radius:2px;
                            width:{int(display_step / T5_TOTAL_STEPS * 100)}%;"></div>
            </div>
        </div>
        <h3 style="color:#f59e0b;margin:0 0 12px 0;font-size:1.05rem;">{title}</h3>
        {content}
        <a href="/api/tutorial5/dismiss"
           onclick="return confirm('Skip Tutorial 5? You can restart it from Settings.');"
           style="position:absolute;top:12px;right:16px;color:#475569;font-size:0.72rem;text-decoration:none;">
            Skip
        </a>
    </div>
    """


# ── Tutorial 5 API routes ──────────────────────────────────────────────────────

@router.post("/api/tutorial5/start")
def tutorial5_start(session_token: Optional[str] = Cookie(None)):
    """Start Tutorial 5 (step 0 → 1)."""
    player = _get_player_from_cookie(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)
    if get_tutorial5_step(player.id) == 0:
        set_tutorial5_step(player.id, 1)
    return RedirectResponse(url="/corporate-actions/dashboard", status_code=303)


@router.post("/api/tutorial5/advance")
def tutorial5_advance(session_token: Optional[str] = Cookie(None)):
    """Advance Tutorial 5 to the next step."""
    player = _get_player_from_cookie(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)

    step = get_tutorial5_step(player.id)

    if step == 0 or step >= 7:
        return RedirectResponse(url="/", status_code=303)

    set_tutorial5_step(player.id, step + 1)
    return RedirectResponse(url="/corporate-actions/dashboard", status_code=303)


@router.post("/api/tutorial5/claim-reward")
def tutorial5_claim_reward(
    session_token: Optional[str] = Cookie(None),
    first_lady: str = Form(...),
):
    """Grant the Tutorial 5 First Lady executive reward and complete the tutorial."""
    player = _get_player_from_cookie(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)

    step = get_tutorial5_step(player.id)
    if step not in (6, 7):
        return RedirectResponse(url="/corporate-actions/dashboard", status_code=303)

    try:
        from executive import (
            Executive, FIRST_LADY_EXECUTIVES, SessionLocal as ExecSessionLocal,
        )
        fl_data = next((f for f in FIRST_LADY_EXECUTIVES if f["key"] == first_lady), None)
        if fl_data is None:
            fl_data = FIRST_LADY_EXECUTIVES[0]

        first_name, *rest = fl_data["name"].split(" ", 1)
        last_name = rest[0] if rest else ""

        db = ExecSessionLocal()
        exec_obj = Executive(
            first_name       = first_name,
            last_name        = last_name,
            player_id        = player.id,
            level            = 1,
            job              = "first_lady",
            wage             = 0.0,
            pay_cycle        = "hour",
            current_age      = 18,
            retirement_age   = 110,
            is_retired       = False,
            is_dead          = False,
            is_special       = False,
            is_first_lady    = True,
            max_level        = 18,
            abilities        = fl_data["ability"],
            bonuses          = "",
        )
        db.add(exec_obj)
        db.commit()
        db.close()
        print(f"[Tutorial5] Created First Lady '{fl_data['name']}' for player {player.id}")
    except Exception as e:
        print(f"[Tutorial5] Failed to create First Lady for player {player.id}: {e}")

    set_tutorial5_step(player.id, 7)
    return RedirectResponse(url="/corporate-actions/dashboard?t5_reward=1", status_code=303)


@router.get("/api/tutorial5/dismiss")
def tutorial5_dismiss(session_token: Optional[str] = Cookie(None)):
    """Dismiss / skip Tutorial 5."""
    player = _get_player_from_cookie(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)
    set_tutorial5_step(player.id, 7)
    return RedirectResponse(url="/", status_code=303)
