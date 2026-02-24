"""
tutorial_ux.py

Startup Company Tutorial for Wadsworth.
Guides new players through core game mechanics in 10 steps.

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
  11 - Complete (unlocked)
"""

from typing import Optional
from fastapi import APIRouter, Cookie, Form
from fastapi.responses import HTMLResponse, RedirectResponse

router = APIRouter()

# ==========================
# TUTORIAL STEP DEFINITIONS
# ==========================

TOTAL_STEPS = 10

STEP_REDIRECT = {
    1: "/",          # Welcome on dashboard
    2: "/land",      # Build water facility
    3: "/inventory", # See water
    4: "/land",      # Build plantation + grocery store
    5: "/inventory", # Resource overview
    6: "/stats/production-costs?category=fruits",  # Apple costs
    7: "/market?item=apples",  # List apple for sale
    8: "/stats/business/free_range_pasture",  # Production chain demo
    9: "/",          # Reward (dashboard) — player claims via form
    10: "/land-market",  # Land market explanation
    11: "/",         # Tutorial complete
}

TERRAIN_OPTIONS = [
    ("prairie", "Prairie — Flat grassland, perfect for farming and diverse businesses"),
    ("forest",  "Forest — Wooded area, excellent for lumber and nature-based industry"),
    ("desert",  "Desert — Arid land, ideal for solar plants and mining operations"),
    ("marsh",   "Marsh — Wetland terrain, unique for water and specialized production"),
    ("mountain","Mountain — Rocky highlands with strong mining and refinery potential"),
    ("savanna", "Savanna — Tropical grassland great for animal pastures and plantations"),
    ("hills",   "Hills — Rolling terrain supporting a wide variety of businesses"),
    ("island",  "Island — Isolated landmass with coastal access and premium appeal"),
    ("jungle",  "Jungle — Dense vegetation with exotic resources and unique production"),
]

ALL_PROXIMITY_FEATURES = "urban,coastal,riverside,lakeside,oasis,hot_springs,caves,volcanic,road,deposits"

# ==========================
# STATE HELPERS
# ==========================

def get_tutorial_step(player_id: int) -> int:
    """Return the player's current tutorial step (0-11)."""
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
    if step == 0 or step >= 11:
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
            content = f"""
            <div style="background:#0a1628;border:1px solid #38bdf8;padding:10px 14px;border-radius:4px;color:#93c5fd;margin-bottom:16px;">
                📍 You're on the <strong>Businesses</strong> dashboard (your active businesses).
                To <em>build</em> new businesses you need to go to your
                <a href="/land" style="color:#38bdf8;font-weight:bold;">Land Portfolio (/land)</a>
                and use the build form on a vacant plot.
            </div>
            {"<div style='background:#052e16;border:1px solid #16a34a;padding:10px 14px;border-radius:4px;color:#4ade80;margin-bottom:16px;'>✓ Water Treatment Facility built! Head back to <a href=\"/land\" style=\"color:#4ade80;font-weight:bold;\">/land</a> and click OK to continue.</div>" if has_wf else "<p style='color:#94a3b8;'>Your task: build a <strong style=\"color:#38bdf8;\">Water Treatment Facility</strong> on one of your vacant plots at <a href=\"/land\" style=\"color:#38bdf8;font-weight:bold;\">/land</a>.</p>"}
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
        <form action="/api/tutorial/complete" method="post">
            <button type="submit" style="background:#22c55e;color:#020617;border:none;padding:10px 24px;border-radius:4px;cursor:pointer;font-size:0.9rem;font-weight:bold;">
                Complete Tutorial — Start Playing!
            </button>
        </form>
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


@router.post("/api/tutorial/claim-reward")
def claim_tutorial_reward(
    session_token: Optional[str] = Cookie(None),
    terrain_type: str = Form(...)
):
    """Step 9: Create the tutorial reward plot and advance to step 10."""
    player = _get_player_from_cookie(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)

    step = get_tutorial_step(player.id)
    if step != 9:
        return RedirectResponse(url="/", status_code=303)

    valid_terrains = [k for k, _ in TERRAIN_OPTIONS]
    if terrain_type not in valid_terrains:
        terrain_type = "prairie"

    try:
        create_tutorial_reward_plot(player.id, terrain_type)
    except Exception as e:
        print(f"[Tutorial] Error creating reward plot: {e}")
        return RedirectResponse(url="/?tutorial_error=reward_failed", status_code=303)

    set_tutorial_step(player.id, 10)
    return RedirectResponse(url="/land-market", status_code=303)


@router.post("/api/tutorial/complete")
def complete_tutorial(session_token: Optional[str] = Cookie(None)):
    """Step 10 → 11: Mark tutorial as complete."""
    player = _get_player_from_cookie(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)
    set_tutorial_step(player.id, 11)
    return RedirectResponse(url="/", status_code=303)


@router.post("/api/tutorial/dismiss")
def dismiss_tutorial(session_token: Optional[str] = Cookie(None)):
    """Dismiss the tutorial permanently (set to step 11 = complete)."""
    player = _get_player_from_cookie(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)
    set_tutorial_step(player.id, 11)
    return RedirectResponse(url="/", status_code=303)


@router.get("/api/tutorial/dismiss")
def dismiss_tutorial_get(session_token: Optional[str] = Cookie(None)):
    """Dismiss the tutorial via link click (GET)."""
    player = _get_player_from_cookie(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)
    set_tutorial_step(player.id, 11)
    return RedirectResponse(url="/", status_code=303)
