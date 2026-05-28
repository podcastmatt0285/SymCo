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


def set_tutorial_step(player_id: int, step: int, is_completion: bool = False):
    """Set the player's tutorial step. Pass is_completion=True only on genuine completion (not dismiss)."""
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
    if is_completion:
        try:
            from admin_notifications import notify_tutorial_complete
            notify_tutorial_complete(player_id, 2)  # T1+T2 share this field; step 12 = end of T2
        except Exception:
            pass


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


def get_tutorial_resume_banner_html(player) -> str:
    """
    Return a 'Resume Tutorial' banner for players mid-way through Tutorial 1.
    Shown on the dashboard when step is 1-11 but the overlay doesn't match that page.
    """
    step = getattr(player, "tutorial_step", 0) or 0
    if step <= 0 or step >= 12:
        return ""

    _STEP_LABEL = {
        1:  ("Your Dashboard",              "/"),
        2:  ("Build your first business",   "/land"),
        3:  ("Check your inventory",        "/inventory"),
        4:  ("Build a production chain",    "/land"),
        5:  ("Review your full inventory",  "/inventory"),
        6:  ("Explore production costs",    "/stats/production-costs"),
        7:  ("Trade on the Market",         "/market"),
        8:  ("View your business stats",    "/stats"),
        9:  ("Claim your free land plot",   "/"),
        10: ("Explore the Land Market",     "/land-market"),
        11: ("Hire your First Lady exec",   "/"),
    }
    label, url = _STEP_LABEL.get(step, ("Continue the tutorial", "/"))
    is_here = url == "/"

    if is_here:
        return ""  # overlay will render directly on this page

    return f"""
    <div style="
        background: linear-gradient(135deg, #0a1628, #0f172a);
        border: 2px solid #d4af37;
        border-radius: 6px;
        padding: 16px 20px;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        gap: 16px;
        flex-wrap: wrap;
    ">
        <span style="background:#d4af37;color:#020617;padding:3px 10px;border-radius:10px;font-size:0.7rem;font-weight:bold;white-space:nowrap;">
            TUTORIAL — STEP {step}/11
        </span>
        <span style="color:#94a3b8;font-size:0.9rem;flex:1;">
            You're mid-tutorial. Next: <strong style="color:#e5e7eb;">{label}</strong>
        </span>
        <a href="{url}" style="background:#d4af37;color:#020617;padding:8px 20px;border-radius:4px;font-size:0.85rem;font-weight:bold;text-decoration:none;white-space:nowrap;">
            Resume Tutorial →
        </a>
    </div>
    """


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
            <div style="margin-top:14px;padding-top:12px;border-top:1px solid #1e293b;">
                <p style="color:#475569;font-size:0.8rem;margin:0 0 6px 0;">
                    Plantation not producing? Make sure it has water input and is set to run.
                </p>
                <a href="/api/tutorial/skip-apple-wait"
                   onclick="return confirm('Skip the apple wait? You can still sell on the Market anytime.');"
                   style="color:#475569;font-size:0.78rem;text-decoration:underline;">
                    My plantation isn't working — skip this step
                </a>
            </div>
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
                        onReady: function(e) {{
                            e.target.getIframe().setAttribute('referrerpolicy', 'strict-origin-when-cross-origin');
                        }},
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
           onclick="return confirm('Skip the tutorial? You can resume or restart it anytime from Settings → Tutorials.');"
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


@router.get("/api/tutorial/skip-apple-wait")
def skip_apple_wait(session_token: Optional[str] = Cookie(None)):
    """Step 7 escape hatch: bypass the apple-listing check and advance to step 8."""
    player = _get_player_from_cookie(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)
    if get_tutorial_step(player.id) == 7:
        set_tutorial_step(player.id, 8)
    return RedirectResponse(url=STEP_REDIRECT.get(8, "/"), status_code=303)


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

    if tutorial_number == 5:
        step5 = get_tutorial5_step(player.id)
        if step5 > 0:
            set_tutorial5_step(player.id, 1)
            return RedirectResponse(url="/corporate-actions/dashboard", status_code=303)

    if tutorial_number == 6:
        step6 = get_tutorial6_step(player.id)
        if step6 > 0:
            set_tutorial6_step(player.id, 1)
            return RedirectResponse(url="/districts", status_code=303)

    if tutorial_number == 7:
        step7 = get_tutorial7_step(player.id)
        if step7 > 0:
            set_tutorial7_step(player.id, 1)
            return RedirectResponse(url="/land", status_code=303)

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
    set_tutorial_step(player.id, 12, is_completion=True)
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

    set_tutorial_step(player.id, 12, is_completion=True)
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


def set_tutorial3_step(player_id: int, step: int, is_completion: bool = False):
    """Set the player's Tutorial 3 step. Pass is_completion=True only on genuine completion (not dismiss)."""
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
    if is_completion:
        try:
            from admin_notifications import notify_tutorial_complete
            notify_tutorial_complete(player_id, 3)
        except Exception:
            pass


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
                        onReady: function(e) {{
                            e.target.getIframe().setAttribute('referrerpolicy', 'strict-origin-when-cross-origin');
                        }},
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
        set_tutorial3_step(player.id, 7, is_completion=True)
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


def set_tutorial4_step(player_id: int, step: int, is_completion: bool = False):
    """Set the player's Tutorial 4 step. Pass is_completion=True only on genuine completion (not dismiss)."""
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
    if is_completion:
        try:
            from admin_notifications import notify_tutorial_complete
            notify_tutorial_complete(player_id, 4)
        except Exception:
            pass


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
                        onReady: function(e) {{
                            e.target.getIframe().setAttribute('referrerpolicy', 'strict-origin-when-cross-origin');
                        }},
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

    set_tutorial4_step(player.id, 7, is_completion=True)
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


def set_tutorial5_step(player_id: int, step: int, is_completion: bool = False):
    """Set the player's Tutorial 5 step. Pass is_completion=True only on genuine completion (not dismiss)."""
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
    if is_completion:
        try:
            from admin_notifications import notify_tutorial_complete
            notify_tutorial_complete(player_id, 5)
        except Exception:
            pass


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
                        onReady: function(e) {{
                            e.target.getIframe().setAttribute('referrerpolicy', 'strict-origin-when-cross-origin');
                        }},
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

    set_tutorial5_step(player.id, 7, is_completion=True)
    return RedirectResponse(url="/corporate-actions/dashboard?t5_reward=1", status_code=303)


@router.get("/api/tutorial5/dismiss")
def tutorial5_dismiss(session_token: Optional[str] = Cookie(None)):
    """Dismiss / skip Tutorial 5."""
    player = _get_player_from_cookie(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)
    set_tutorial5_step(player.id, 7)
    return RedirectResponse(url="/", status_code=303)


# ============================================================
# TUTORIAL 6 — District Market
# ============================================================
#
# Steps:
#   0  - Not started (shown in Settings → Tutorials after T5 complete)
#   1  - What are Districts?           (/districts)
#   2  - District Market intro + video (/districts)
#   3  - Browsing the District Market  (/district-market)
#   4  - Buying & Selling              (/district-market)
#   5  - District Strategy             (/district-market)
#   6  - Reward: 15 trophies           (/districts)
#   7  - Complete
#
# Locked until Tutorial 5 is complete (tutorial_5_step >= 7).
# Must be manually started from Settings → Tutorials.
# ============================================================

T6_TOTAL_STEPS = 6
# T6 rewards a free district plot + business (no land tax, no wages, no startup cost, forever)
T6_REWARD_TERRAIN   = "district_food"
T6_REWARD_BIZ_TYPE  = "fast_food_kitchen"
T6_REWARD_BIZ_NAME  = "Fast Food Kitchen"


def get_tutorial6_step(player_id: int) -> int:
    """Return the player's current Tutorial 6 step (0–7)."""
    try:
        from auth import get_db, Player
        db = get_db()
        player = db.query(Player).filter(Player.id == player_id).first()
        db.close()
        if player is None:
            return 0
        step = getattr(player, "tutorial_6_step", 0)
        return step if step is not None else 0
    except Exception as e:
        print(f"[Tutorial6] get_tutorial6_step error: {e}")
        return 0


def set_tutorial6_step(player_id: int, step: int, is_completion: bool = False):
    """Set the player's Tutorial 6 step. Pass is_completion=True only on genuine completion (not dismiss)."""
    try:
        from auth import get_db, Player
        db = get_db()
        player = db.query(Player).filter(Player.id == player_id).first()
        if player:
            player.tutorial_6_step = step
            db.commit()
        db.close()
    except Exception as e:
        print(f"[Tutorial6] set_tutorial6_step error: {e}")
    if is_completion:
        try:
            from admin_notifications import notify_tutorial_complete
            notify_tutorial_complete(player_id, 6)
        except Exception:
            pass


def should_show_tutorial6_banner(player) -> bool:
    """Return True only when T5 is complete and T6 not yet started."""
    t5 = getattr(player, "tutorial_5_step", 0) or 0
    t6 = getattr(player, "tutorial_6_step", 0) or 0
    return t5 >= 7 and t6 == 0


# ── Tutorial 6 overlay HTML generator ─────────────────────────────────────────

def get_tutorial6_overlay_html(player, current_page: str) -> str:
    """
    Return the Tutorial 6 overlay panel HTML for the given page.
    `current_page`: 'districts' | 'district_market'
    Returns empty string if T6 is not active or wrong page.
    """
    step = get_tutorial6_step(player.id)
    if step == 0 or step >= 7:
        return ""

    T6_STEP_PAGE = {
        1: "districts",
        2: "districts",
        3: "district_market",
        4: "district_market",
        5: "district_market",
        6: "districts",
    }
    expected = T6_STEP_PAGE.get(step, "")
    if expected and current_page != expected:
        return ""

    # ── Step content ──────────────────────────────────────────────────────────

    if step == 1:
        title = "What are Districts?"
        content = """
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 12px 0;">
            <strong style="color:#e5e7eb;">Districts</strong> are specialized local economies inside
            Wadsworth. Each district focuses on a particular category of goods — one might specialize
            in agricultural produce, another in electronics, another in construction materials.
        </p>
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 12px 0;">
            Districts have their own <strong style="color:#38bdf8;">order books</strong> separate from
            the main market. Prices in a district reflect local supply and demand, so a district with
            heavy farming activity will have cheaper produce but may import manufactured goods at a premium.
        </p>
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 16px 0;">
            You can see all available districts on this page. Each card shows its specialization,
            active members, and a link to its market. Let's learn how the District Market works.
        </p>
        <form action="/api/tutorial6/advance" method="post">
            <button type="submit" style="background:#38bdf8;color:#020617;border:none;padding:10px 24px;
                    border-radius:4px;cursor:pointer;font-size:0.9rem;font-weight:bold;">
                OK — Tell Me More →
            </button>
        </form>
        """

    elif step == 2:
        import json as _json
        _video_id = ""
        try:
            with open("wiki_media.json", "r") as _f:
                _media = _json.load(_f)
            if len(_media.get("videos", [])) > 5:
                _video_id = _media["videos"][5]["youtube_id"]
        except Exception:
            pass

        title = "District Market Overview"
        _video_html = ""
        _btn_attrs = ""
        if _video_id:
            _video_html = f"""
        <div id="yt6-player-container" style="aspect-ratio:16/9;border-radius:6px;
             border:1px solid #1d4ed8;margin-bottom:14px;overflow:hidden;background:#000;"></div>
        <script>
        (function() {{
          var WATCH_THRESHOLD = 0.90, unlocked = false;
          function unlockNext6() {{
            if (unlocked) return; unlocked = true;
            var b = document.getElementById('t6-next-btn');
            if (b) {{ b.disabled = false; b.style.opacity = ''; b.style.cursor = ''; b.removeAttribute('title'); }}
          }}
          var tag = document.createElement('script');
          tag.src = 'https://www.youtube.com/iframe_api';
          document.head.appendChild(tag);
          var ytPlayer6;
          window.onYouTubeIframeAPIReady = function() {{
            ytPlayer6 = new YT.Player('yt6-player-container', {{
              videoId: '{_video_id}',
              playerVars: {{ rel: 0, modestbranding: 1 }},
              events: {{
                onReady: function(e) {{ e.target.getIframe().setAttribute('referrerpolicy', 'strict-origin-when-cross-origin'); }},
                onStateChange: function(e) {{ if (e.data === YT.PlayerState.ENDED) unlockNext6(); }}
              }}
            }});
          }};
          setInterval(function() {{
            if (!ytPlayer6 || typeof ytPlayer6.getDuration !== 'function') return;
            var d = ytPlayer6.getDuration(), c = ytPlayer6.getCurrentTime();
            if (d > 0 && c / d >= WATCH_THRESHOLD) {{ unlockNext6(); }}
          }}, 1000);
        }})();
        </script>"""
            _btn_attrs = 'id="t6-next-btn" disabled style="background:#38bdf8;color:#020617;border:none;padding:10px 24px;border-radius:4px;cursor:not-allowed;font-size:0.9rem;font-weight:bold;opacity:0.4;" title="Watch the video to continue"'
        else:
            _video_html = """
        <div style="background:#0f172a;border:1px solid #1e293b;border-radius:6px;
                    padding:12px 16px;margin-bottom:14px;color:#475569;font-size:0.82rem;">
            📹 Video coming soon — check back after your admin adds the Districts overview video.
        </div>"""
            _btn_attrs = 'style="background:#38bdf8;color:#020617;border:none;padding:10px 24px;border-radius:4px;cursor:pointer;font-size:0.9rem;font-weight:bold;"'

        content = f"""
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 12px 0;">
            The <strong style="color:#e5e7eb;">District Market</strong> operates exactly like the main
            market — limit orders, an order book, bid/ask matching — but is scoped to goods relevant
            to that district's specialization. This creates
            <strong style="color:#38bdf8;">price arbitrage opportunities</strong> between districts
            and the main exchange.
        </p>
        {_video_html}
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 16px 0;">
            Head to the <strong style="color:#38bdf8;">District Market</strong> to see it in action.
        </p>
        <form action="/api/tutorial6/advance" method="post">
            <button type="submit" {_btn_attrs}>
                OK — Open District Market →
            </button>
        </form>
        """

    elif step == 3:
        title = "Browsing the District Market"
        content = """
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 12px 0;">
            You're on the <strong style="color:#e5e7eb;">District Market</strong> order book.
            Use the search bar and category tabs to browse available items. Each item shows its
            live bid (highest buy offer) and ask (lowest sell offer).
        </p>
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 12px 0;">
            The <strong style="color:#38bdf8;">spread</strong> between bid and ask is where margin lives.
            Tight spreads mean competitive markets; wide spreads signal opportunity for patient traders.
        </p>
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 16px 0;">
            District market items can be cheaper or more expensive than the main market depending on
            local production levels. Always compare both before committing.
        </p>
        <form action="/api/tutorial6/advance" method="post">
            <button type="submit" style="background:#38bdf8;color:#020617;border:none;padding:10px 24px;
                    border-radius:4px;cursor:pointer;font-size:0.9rem;font-weight:bold;">
                OK — How Do I Place Orders? →
            </button>
        </form>
        """

    elif step == 4:
        title = "Buying &amp; Selling in the District"
        content = """
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 12px 0;">
            Placing orders works identically to the main market: choose an item, set a price per unit,
            and enter quantity. The system matches your order with the best available counter-offer.
        </p>
        <ul style="color:#94a3b8;line-height:2;margin:0 0 12px 0;padding-left:20px;">
            <li><strong style="color:#38bdf8;">Buy orders</strong> — set a maximum price you're willing to pay.
                Fills immediately if a seller is below your limit, otherwise queues.</li>
            <li><strong style="color:#4ade80;">Sell orders</strong> — set a minimum acceptable price.
                Fills against the highest existing buy order.</li>
        </ul>
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 16px 0;">
            District sales are subject to the district's
            <strong style="color:#f59e0b;">local sales tax</strong>, deducted from your proceeds.
            High-tax districts generate city revenue — which is paid to whoever governs that city.
        </p>
        <form action="/api/tutorial6/advance" method="post">
            <button type="submit" style="background:#38bdf8;color:#020617;border:none;padding:10px 24px;
                    border-radius:4px;cursor:pointer;font-size:0.9rem;font-weight:bold;">
                OK — District Strategy →
            </button>
        </form>
        """

    elif step == 5:
        title = "District Trading Strategy"
        content = """
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 12px 0;">
            The most profitable district traders combine two edges:
        </p>
        <ul style="color:#94a3b8;line-height:2;margin:0 0 12px 0;padding-left:20px;">
            <li><strong style="color:#38bdf8;">Supply chain integration</strong> — produce the goods
                your district specializes in, then sell locally where demand is highest.</li>
            <li><strong style="color:#4ade80;">Cross-market arbitrage</strong> — when district prices
                diverge from the main market, buy low in one and sell high in the other. Act fast —
                other players see the same opportunity.</li>
        </ul>
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 12px 0;">
            Keep an eye on district <strong style="color:#f59e0b;">tax rates</strong>. Low-tax districts
            are better for high-volume trading. High-tax districts reduce your margins but benefit
            whoever controls city governance — that could be you.
        </p>
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 16px 0;">
            Head back to the Districts page to claim your reward!
        </p>
        <form action="/api/tutorial6/advance" method="post">
            <button type="submit" style="background:#38bdf8;color:#020617;border:none;padding:10px 24px;
                    border-radius:4px;cursor:pointer;font-size:0.9rem;font-weight:bold;">
                OK — Claim My Reward →
            </button>
        </form>
        """

    elif step == 6:
        title = "Tutorial 6 Complete — Claim Your Reward!"
        content = f"""
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 12px 0;">
            Congratulations on completing the <strong style="color:#e5e7eb;">District Market</strong> tutorial!
            You now know how to navigate local economies, read district order books,
            and exploit price differences between districts and the main exchange.
        </p>
        <div style="background:rgba(56,189,248,0.08);border:1px solid rgba(56,189,248,0.3);
                    border-radius:6px;padding:12px 16px;margin-bottom:16px;">
            <strong style="color:#38bdf8;">&#127961;&#65039; Reward: Free District Plot + Business</strong>
            <ul style="color:#94a3b8;font-size:0.85rem;margin:8px 0 0 0;padding-left:18px;line-height:1.8;">
                <li><strong style="color:#e5e7eb;">District Food Plot</strong> — permanently tax-free, forever</li>
                <li><strong style="color:#e5e7eb;">Fast Food Kitchen</strong> — no startup cost, no wages, ever</li>
                <li>Produces burgers and fast food items for the District Market</li>
                <li>You still need to supply inputs (beef, bread, onions) to run production</li>
            </ul>
        </div>
        <form action="/api/tutorial6/claim-reward" method="post">
            <button type="submit" style="background:#38bdf8;color:#020617;border:none;padding:10px 24px;
                    border-radius:4px;cursor:pointer;font-size:0.9rem;font-weight:bold;">
                Claim Free District Plot &amp; Business! &#127961;&#65039;
            </button>
        </form>
        """

    else:
        return ""

    # ── Wrapper ───────────────────────────────────────────────────────────────
    return f"""
    <div id="tutorial6-panel" style="
        background: linear-gradient(135deg, #0a1628, #0f172a);
        border: 2px solid #38bdf8;
        border-radius: 6px;
        padding: 20px 24px;
        margin-bottom: 24px;
        position: relative;
    ">
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:14px;flex-wrap:wrap;">
            <span style="background:#38bdf8;color:#020617;padding:3px 12px;border-radius:12px;
                         font-size:0.7rem;font-weight:bold;letter-spacing:0.05em;">
                TUTORIAL — STEP {step}/{T6_TOTAL_STEPS}
            </span>
            <span style="color:#38bdf8;font-size:0.85rem;font-weight:bold;">Level 6 &middot; District Market</span>
            <div style="flex:1;background:#1e293b;height:4px;border-radius:2px;min-width:80px;">
                <div style="background:#38bdf8;height:4px;border-radius:2px;
                            width:{int(step / T6_TOTAL_STEPS * 100)}%;"></div>
            </div>
        </div>
        <h3 style="color:#38bdf8;margin:0 0 12px 0;font-size:1.05rem;">{title}</h3>
        {content}
        <a href="/api/tutorial6/dismiss"
           onclick="return confirm('Skip Tutorial 6? You can restart it from Settings → Tutorials.');"
           style="position:absolute;top:12px;right:16px;color:#475569;font-size:0.72rem;text-decoration:none;">
            Skip
        </a>
    </div>
    """


def get_tutorial6_banner_html(player) -> str:
    """Return the T6 start banner for Settings → Tutorials. Not auto-shown on dashboard."""
    if not should_show_tutorial6_banner(player):
        return ""
    return """
    <div style="
        background: linear-gradient(135deg, #071829, #0f172a);
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
            <span style="color:#38bdf8;font-size:0.85rem;font-weight:bold;">Level 6 &middot; District Market</span>
        </div>
        <h3 style="color:#38bdf8;margin:0 0 10px 0;font-size:1.05rem;">
            Trade in Local Economies
        </h3>
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 16px 0;">
            Tutorial 6 covers <strong style="color:#e5e7eb;">Districts</strong> and the
            <strong style="color:#e5e7eb;">District Market</strong> — specialized local order books
            with their own supply, demand, and tax dynamics. Learn to exploit price differences
            between districts and the main exchange.
            Complete it to earn a <strong style="color:#38bdf8;">free District Food Plot + Fast Food Kitchen</strong>
            — no land tax, no wages, no startup cost, forever.
        </p>
        <form action="/api/tutorial6/start" method="post" style="display:inline;">
            <button type="submit"
                    style="background:#38bdf8;color:#020617;border:none;padding:10px 24px;
                           border-radius:4px;cursor:pointer;font-size:0.9rem;font-weight:bold;
                           margin-right:12px;">
                Start Tutorial 6 &rarr;
            </button>
        </form>
        <a href="/api/tutorial6/dismiss"
           style="color:#475569;font-size:0.82rem;">
            Dismiss
        </a>
    </div>
    """


# ── Tutorial 6 API routes ─────────────────────────────────────────────────────

@router.post("/api/tutorial6/start")
def tutorial6_start(session_token: Optional[str] = Cookie(None)):
    """Start Tutorial 6 (step 0 → 1). Only allowed after Tutorial 5 complete."""
    player = _get_player_from_cookie(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)
    t5 = getattr(player, "tutorial_5_step", 0) or 0
    if t5 < 7:
        return RedirectResponse(url="/settings?tab=tutorials&error=Complete+Tutorial+5+first",
                                status_code=303)
    if get_tutorial6_step(player.id) == 0:
        set_tutorial6_step(player.id, 1)
    return RedirectResponse(url="/districts", status_code=303)


@router.post("/api/tutorial6/advance")
def tutorial6_advance(session_token: Optional[str] = Cookie(None)):
    """Advance Tutorial 6 to the next step."""
    player = _get_player_from_cookie(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)
    step = get_tutorial6_step(player.id)
    if step == 0 or step >= 7:
        return RedirectResponse(url="/", status_code=303)

    next_step = step + 1
    set_tutorial6_step(player.id, next_step)

    T6_REDIRECT = {
        2: "/districts",       # step 2 overlay is on /districts
        3: "/district-market", # step 3 overlay is on /district-market
        4: "/district-market", # step 4 overlay is on /district-market
        5: "/district-market", # step 5 overlay is on /district-market
        6: "/districts",       # step 6 (reward) is on /districts
        7: "/",
    }
    return RedirectResponse(url=T6_REDIRECT.get(next_step, "/"), status_code=303)


@router.post("/api/tutorial6/claim-reward")
def tutorial6_claim_reward(session_token: Optional[str] = Cookie(None)):
    """Step 6 → 7: Grant a permanent tax-free Food Production Zone district + Fast Food Kitchen."""
    player = _get_player_from_cookie(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)
    if get_tutorial6_step(player.id) != 6:
        return RedirectResponse(url="/", status_code=303)

    try:
        from districts import District, get_db as _dist_db
        from business import Business
        from datetime import datetime as _dt

        db = _dist_db()
        try:
            # Free Food Production Zone district — permanently tax-exempt, no merge cost
            district = District(
                owner_id=player.id,
                district_type="food",
                terrain_type=T6_REWARD_TERRAIN,   # "district_food"
                size=1.0,
                plots_merged=1,
                monthly_tax=0.0,
                is_tutorial_reward=True,
                source_plot_ids="",
                created_at=_dt.utcnow(),
                last_tax_payment=_dt.utcnow(),
            )
            db.add(district)
            db.flush()

            # Free Fast Food Kitchen on the district — permanently wage-free
            biz = Business(
                owner_id=player.id,
                land_plot_id=None,
                district_id=district.id,
                business_type=T6_REWARD_BIZ_TYPE,  # "fast_food_kitchen"
                is_active=True,
                is_tutorial_reward=True,
                created_at=_dt.utcnow(),
            )
            db.add(biz)
            db.flush()

            district.occupied_by_business_id = biz.id
            db.commit()
        finally:
            db.close()

        try:
            from push_ux import send_push_notification
            send_push_notification(
                player.id,
                "🏙️ Tutorial 6 Complete!",
                "You earned a FREE Food Production Zone district + Fast Food Kitchen — "
                "no district tax, no wages, forever. Check your Districts page!",
                url="/districts",
                notif_type="tasks_events",
                tag="tutorial6-complete",
            )
        except Exception:
            pass

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[Tutorial6] Reward grant error: {e}")
        return RedirectResponse(url="/districts?t6_error=1", status_code=303)

    set_tutorial6_step(player.id, 7, is_completion=True)
    return RedirectResponse(url="/districts?t6_complete=1", status_code=303)


@router.post("/api/tutorial6/restart")
def tutorial6_restart(session_token: Optional[str] = Cookie(None)):
    """Restart Tutorial 6 from step 1 (no second reward)."""
    player = _get_player_from_cookie(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)
    if (getattr(player, "tutorial_6_step", 0) or 0) > 0:
        set_tutorial6_step(player.id, 1)
    return RedirectResponse(url="/districts", status_code=303)


@router.get("/api/tutorial6/dismiss")
@router.post("/api/tutorial6/dismiss")
def tutorial6_dismiss(session_token: Optional[str] = Cookie(None)):
    """Dismiss / skip Tutorial 6."""
    player = _get_player_from_cookie(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)
    set_tutorial6_step(player.id, 7)
    return RedirectResponse(url="/", status_code=303)


# ══════════════════════════════════════════════════════════════════════════════
# TUTORIAL 7 — Supply, Demand, Elasticity & Land Efficiency
# ══════════════════════════════════════════════════════════════════════════════

T7_TOTAL_STEPS  = 7
T7_TROPHY_REWARD = 20

# ── Step / progress helpers ───────────────────────────────────────────────────

def get_tutorial7_step(player_id: int) -> int:
    from auth import get_db, Player
    db = get_db()
    try:
        p = db.query(Player).filter(Player.id == player_id).first()
        return int(getattr(p, "tutorial_7_step", 0) or 0)
    finally:
        db.close()

def set_tutorial7_step(player_id: int, step: int, is_completion: bool = False):
    """Set the player's Tutorial 7 step. Pass is_completion=True only on genuine completion (not dismiss)."""
    from auth import get_db, Player
    db = get_db()
    try:
        p = db.query(Player).filter(Player.id == player_id).first()
        if p:
            p.tutorial_7_step = step
            db.commit()
    finally:
        db.close()
    if is_completion:
        try:
            from admin_notifications import notify_tutorial_complete
            notify_tutorial_complete(player_id, 7)
        except Exception:
            pass

def should_show_tutorial7_banner(player) -> bool:
    step6 = get_tutorial6_step(player.id)
    step7 = get_tutorial7_step(player.id)
    return step6 >= 7 and step7 == 0


# ── Overlay HTML (shown on /land page) ───────────────────────────────────────

def get_tutorial7_overlay_html(player, page_key: str) -> str:
    """Return the Tutorial 7 overlay for the /land page (all steps)."""
    step = get_tutorial7_step(player.id)
    if step == 0 or step >= 8:
        return ""
    if page_key != "land":
        return ""

    # ── Shared CSS + chart helpers ────────────────────────────────────────────
    SHARED_CSS = """
    <style>
    .t7-chart{background:#020617;border:1px solid #1e293b;border-radius:6px;
              padding:12px;margin:10px 0;overflow-x:auto;}
    .t7-table{width:100%;border-collapse:collapse;font-size:0.78rem;}
    .t7-table th{background:#0f172a;color:#94a3b8;padding:6px 10px;
                 text-align:left;font-weight:600;border-bottom:1px solid #1e293b;}
    .t7-table td{padding:5px 10px;border-bottom:1px solid #0f172a;color:#cbd5e1;}
    .t7-table tr:last-child td{border-bottom:none;}
    .t7-bar-wrap{background:#0f172a;border-radius:3px;height:8px;
                 margin:2px 0;overflow:hidden;min-width:80px;}
    .t7-bar{height:8px;border-radius:3px;transition:width .4s ease;}
    .t7-callout{background:rgba(56,189,248,.08);border-left:3px solid #38bdf8;
                padding:8px 12px;margin:8px 0;font-size:0.82rem;color:#cbd5e1;
                border-radius:0 4px 4px 0;}
    .t7-warn{background:rgba(251,191,36,.08);border-left:3px solid #fbbf24;
             padding:8px 12px;margin:8px 0;font-size:0.82rem;color:#cbd5e1;
             border-radius:0 4px 4px 0;}
    .t7-formula{font-family:'JetBrains Mono',monospace;font-size:0.82rem;
                background:#0a0f1a;border:1px solid #1e293b;padding:6px 12px;
                border-radius:4px;color:#4ade80;display:inline-block;margin:4px 0;}
    .t7-anim-bar{animation:t7grow 1.2s ease forwards;}
    @keyframes t7grow{from{width:0}to{width:var(--tw)}}
    .t7-pulse{animation:t7pulse 2s ease-in-out infinite;}
    @keyframes t7pulse{0%,100%{opacity:1}50%{opacity:.5}}
    </style>
    """

    # ── Step content ──────────────────────────────────────────────────────────

    if step == 1:
        title = "What Is Plot Efficiency?"
        import json as _json
        _t7_video_id = ""
        try:
            with open("wiki_media.json", "r") as _f:
                _media = _json.load(_f)
            if len(_media.get("videos", [])) > 6:
                _t7_video_id = _media["videos"][6]["youtube_id"]
        except Exception:
            pass
        if _t7_video_id:
            _t7_video_html = f"""
        <div id="yt7-player-container" style="aspect-ratio:16/9;border-radius:6px;
             border:1px solid #15803d;margin:12px 0 16px;overflow:hidden;background:#000;"></div>
        <script>
        (function() {{
          var WATCH_THRESHOLD = 0.90, unlocked = false;
          function unlockNext7() {{
            if (unlocked) return; unlocked = true;
            var b = document.querySelector('form[action="/api/tutorial7/advance"] button');
            if (b) {{ b.disabled = false; b.style.opacity = ''; b.style.cursor = ''; b.removeAttribute('title'); }}
          }}
          // Disable outer Next button — deferred so the button is in the DOM
          setTimeout(function() {{
            var b = document.querySelector('form[action="/api/tutorial7/advance"] button');
            if (b) {{ b.disabled = true; b.style.opacity = '0.4'; b.style.cursor = 'not-allowed'; b.title = 'Watch the video to continue'; }}
          }}, 0);
          var tag = document.createElement('script');
          tag.src = 'https://www.youtube.com/iframe_api';
          document.head.appendChild(tag);
          var ytPlayer7;
          window.onYouTubeIframeAPIReady = function() {{
            ytPlayer7 = new YT.Player('yt7-player-container', {{
              videoId: '{_t7_video_id}',
              playerVars: {{ rel: 0, modestbranding: 1 }},
              events: {{
                onReady: function(e) {{ e.target.getIframe().setAttribute('referrerpolicy', 'strict-origin-when-cross-origin'); }},
                onStateChange: function(e) {{ if (e.data === YT.PlayerState.ENDED) unlockNext7(); }}
              }}
            }});
          }};
          setInterval(function() {{
            if (!ytPlayer7 || typeof ytPlayer7.getDuration !== 'function') return;
            var d = ytPlayer7.getDuration(), c = ytPlayer7.getCurrentTime();
            if (d > 0 && c / d >= WATCH_THRESHOLD) {{ unlockNext7(); }}
          }}, 1000);
        }})();
        </script>"""
        else:
            _t7_video_html = """
        <div style="background:#0f172a;border:1px solid #1e293b;border-radius:6px;
                    padding:12px 16px;margin:12px 0 16px;color:#475569;font-size:0.82rem;">
            📹 Video overview coming soon.
        </div>"""
        content = f"""
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 10px;">
          Every land plot has an <strong style="color:#e5e7eb;">Efficiency</strong> rating from
          <strong style="color:#4ade80;">0% – 100%</strong>.
          It starts at <strong style="color:#4ade80;">100%</strong> when you buy or receive the plot
          and <em>slowly degrades over time</em> through natural wear and tear.
        </p>
        {_t7_video_html}
        <!-- Efficiency decay animation -->
        <div class="t7-chart">
          <div style="font-size:0.75rem;color:#64748b;margin-bottom:8px;font-weight:600;">
            EFFICIENCY DECAY OVER TIME (animated)
          </div>
          <div style="display:flex;flex-direction:column;gap:6px;">
            <div style="display:flex;align-items:center;gap:8px;font-size:0.75rem;">
              <span style="width:64px;color:#94a3b8;text-align:right;">Today</span>
              <div class="t7-bar-wrap" style="flex:1;">
                <div class="t7-bar t7-anim-bar" style="--tw:100%;background:#22c55e;width:0;"></div>
              </div>
              <span style="color:#22c55e;width:36px;">100%</span>
            </div>
            <div style="display:flex;align-items:center;gap:8px;font-size:0.75rem;">
              <span style="width:64px;color:#94a3b8;text-align:right;">6 months</span>
              <div class="t7-bar-wrap" style="flex:1;">
                <div class="t7-bar t7-anim-bar" style="--tw:97.4%;background:#84cc16;width:0;animation-delay:.2s"></div>
              </div>
              <span style="color:#84cc16;width:36px;">97.4%</span>
            </div>
            <div style="display:flex;align-items:center;gap:8px;font-size:0.75rem;">
              <span style="width:64px;color:#94a3b8;text-align:right;">1 year</span>
              <div class="t7-bar-wrap" style="flex:1;">
                <div class="t7-bar t7-anim-bar" style="--tw:94.7%;background:#eab308;width:0;animation-delay:.4s"></div>
              </div>
              <span style="color:#eab308;width:36px;">94.7%</span>
            </div>
            <div style="display:flex;align-items:center;gap:8px;font-size:0.75rem;">
              <span style="width:64px;color:#94a3b8;text-align:right;">2 years</span>
              <div class="t7-bar-wrap" style="flex:1;">
                <div class="t7-bar t7-anim-bar" style="--tw:89.4%;background:#f59e0b;width:0;animation-delay:.6s"></div>
              </div>
              <span style="color:#f59e0b;width:36px;">89.4%</span>
            </div>
            <div style="display:flex;align-items:center;gap:8px;font-size:0.75rem;">
              <span style="width:64px;color:#94a3b8;text-align:right;">3 years</span>
              <div class="t7-bar-wrap" style="flex:1;">
                <div class="t7-bar t7-anim-bar" style="--tw:84%;background:#ef4444;width:0;animation-delay:.8s"></div>
              </div>
              <span style="color:#ef4444;width:36px;">84.0%</span>
            </div>
          </div>
          <div style="margin-top:8px;font-size:0.72rem;color:#334155;">
            Decay rate: ~7.14% per day (100% → 0% in exactly 14 days)
          </div>
        </div>

        <div class="t7-callout">
          <strong style="color:#38bdf8;">Why does this matter?</strong> Efficiency directly controls
          how much your business pays in wages each production cycle.
          Wages follow <strong style="color:#fbbf24;">wage = base ÷ (efficiency / 100)</strong>.
          At 50% efficiency wages are <strong style="color:#ef4444;">2×</strong>. At 10% they are
          <strong style="color:#ef4444;">10×</strong>. At near-zero efficiency they rocket all the
          way to <strong style="color:#ef4444;">200×</strong> — a business-destroying cost spiral.
          Keep your plots maintained.
        </div>

        <div class="t7-callout" style="border-color:#22c55e;background:#052e16;">
          <strong style="color:#22c55e;">Restoration:</strong> Once a plot drops below
          <strong style="color:#fbbf24;">30% efficiency</strong> it becomes eligible for
          the <strong>Efficiency Restoration</strong> module on your Land dashboard.
          Restoration brings each plot to
          <strong style="color:#4ade80;">1.5× its current maximum</strong> — and that maximum
          grows every time. First restoration: 100% max → 150% target. Second: 150% max → 225%
          target. Third: 225% max → 337.5%, and so on. More decay headroom per cycle.
          Wages stay floored at 1× base even while efficiency exceeds 100%.
          Cost = <strong>wage_multiplier × $1,000</strong> per plot, paid to the Federal Government.
          Runs at 500× the decay rate. <strong>60-day cooldown</strong> after completion.
        </div>

        <div class="t7-chart">
          <div style="font-size:0.75rem;color:#64748b;margin-bottom:8px;font-weight:600;">
            EFFICIENCY → WAGE MULTIPLIER (log scale)
          </div>
          <!-- SVG curve — log-scale y-axis so the 200× peak is visible -->
          <!-- y mapping (log scale): y = 100 - (log(mult)/log(200)) * 90
               x mapping: x = 30 + (eff/100) * 260
               Key points (eff%, mult, x, y):
                 100 → 1.0  → 290, 100
                  75 → 1.33 → 225,  95
                  50 → 2.0  → 160,  88
                  25 → 4.0  →  95,  76
                  10 → 10×  →  56,  61
                   5 → 20×  →  43,  49
                   2 → 50×  →  35,  34
                   1 → 100× →  33,  22
                 0.5 → 200× →  31,  10  (floor)  -->
          <svg viewBox="0 0 300 125" style="width:100%;max-width:420px;display:block;">
            <defs>
              <linearGradient id="t7grad" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%"   stop-color="#ef4444"/>
                <stop offset="30%"  stop-color="#f97316"/>
                <stop offset="60%"  stop-color="#fbbf24"/>
                <stop offset="100%" stop-color="#22c55e"/>
              </linearGradient>
            </defs>
            <!-- axes -->
            <line x1="34" y1="100" x2="290" y2="100" stroke="#334155" stroke-width="1"/>
            <line x1="34" y1="8"   x2="34"  y2="100" stroke="#334155" stroke-width="1"/>
            <!-- axis labels -->
            <text x="162" y="118" fill="#64748b" font-size="8" text-anchor="middle">Efficiency (%)</text>
            <text x="11"  y="54"  fill="#64748b" font-size="7" text-anchor="middle" transform="rotate(-90,11,54)">Wage ×</text>
            <!-- x tick labels -->
            <text x="34"  y="108" fill="#64748b" font-size="7" text-anchor="middle">0</text>
            <text x="95"  y="108" fill="#64748b" font-size="7" text-anchor="middle">25</text>
            <text x="160" y="108" fill="#64748b" font-size="7" text-anchor="middle">50</text>
            <text x="225" y="108" fill="#64748b" font-size="7" text-anchor="middle">75</text>
            <text x="290" y="108" fill="#64748b" font-size="7" text-anchor="middle">100</text>
            <!-- y tick labels (log scale) -->
            <text x="30" y="100" fill="#64748b" font-size="6.5" text-anchor="end">1×</text>
            <text x="30" y="88"  fill="#64748b" font-size="6.5" text-anchor="end">2×</text>
            <text x="30" y="76"  fill="#64748b" font-size="6.5" text-anchor="end">5×</text>
            <text x="30" y="61"  fill="#ef4444" font-size="6.5" text-anchor="end">10×</text>
            <text x="30" y="34"  fill="#ef4444" font-size="6.5" text-anchor="end">50×</text>
            <text x="30" y="10"  fill="#ef4444" font-size="6.5" text-anchor="end">200×</text>
            <!-- curve -->
            <polyline points="31,10 33,22 35,34 43,49 56,61 95,76 160,88 225,95 290,100"
              fill="none" stroke="url(#t7grad)" stroke-width="2.5" stroke-linejoin="round"/>
            <!-- 200× ceiling marker -->
            <line x1="31" y1="10" x2="290" y2="10" stroke="#ef4444" stroke-width="0.8" stroke-dasharray="3,3"/>
            <text x="170" y="9" fill="#ef4444" font-size="6" text-anchor="middle">200× ceiling</text>
            <!-- 50% reference -->
            <line x1="160" y1="10" x2="160" y2="100" stroke="#fbbf24" stroke-width="0.8" stroke-dasharray="3,3"/>
            <text x="162" y="84" fill="#fbbf24" font-size="6">2× at 50%</text>
            <!-- highlight points -->
            <circle cx="290" cy="100" r="3" fill="#22c55e"/>
            <text x="278" y="97" fill="#22c55e" font-size="5.5">1× normal</text>
            <circle cx="31" cy="10" r="3" fill="#ef4444"/>
          </svg>
          <div style="font-size:0.72rem;color:#334155;margin-top:4px;">
            Log-scale y-axis. Wages spiral exponentially — a fully decayed plot costs
            <strong style="color:#ef4444;">200× base wages</strong> per cycle.
          </div>
        </div>
        """

    elif step == 2:
        title = "How the Market Price is Determined"
        content = """
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 10px;">
          The <strong style="color:#e5e7eb;">Market Price</strong> of any item is not set by
          the game — it's discovered through the order book. Players post buy and sell orders;
          when they cross, a trade executes and that price becomes the new market reference.
        </p>

        <!-- animated order book -->
        <div class="t7-chart">
          <div style="font-size:0.75rem;color:#64748b;margin-bottom:8px;font-weight:600;">
            ORDER BOOK — HOW PRICES MEET
          </div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:0.75rem;">
            <div>
              <div style="color:#4ade80;font-weight:700;margin-bottom:4px;">BUY ORDERS (Bids)</div>
              <div style="display:flex;flex-direction:column;gap:3px;">
                <div style="display:flex;justify-content:space-between;background:#052e16;padding:3px 8px;border-radius:3px;">
                  <span style="color:#4ade80;">$9.80</span><span style="color:#94a3b8;">50 units</span>
                </div>
                <div style="display:flex;justify-content:space-between;background:#052e16;padding:3px 8px;border-radius:3px;">
                  <span style="color:#4ade80;">$9.60</span><span style="color:#94a3b8;">120 units</span>
                </div>
                <div style="display:flex;justify-content:space-between;background:#052e16;padding:3px 8px;border-radius:3px;opacity:.7;">
                  <span style="color:#4ade80;">$9.40</span><span style="color:#94a3b8;">200 units</span>
                </div>
              </div>
            </div>
            <div>
              <div style="color:#ef4444;font-weight:700;margin-bottom:4px;">SELL ORDERS (Asks)</div>
              <div style="display:flex;flex-direction:column;gap:3px;">
                <div style="display:flex;justify-content:space-between;background:#1a0505;padding:3px 8px;border-radius:3px;">
                  <span style="color:#ef4444;">$9.80</span><span style="color:#94a3b8;">80 units</span>
                </div>
                <div style="display:flex;justify-content:space-between;background:#1a0505;padding:3px 8px;border-radius:3px;opacity:.7;">
                  <span style="color:#ef4444;">$10.00</span><span style="color:#94a3b8;">150 units</span>
                </div>
                <div style="display:flex;justify-content:space-between;background:#1a0505;padding:3px 8px;border-radius:3px;opacity:.5;">
                  <span style="color:#ef4444;">$10.20</span><span style="color:#94a3b8;">300 units</span>
                </div>
              </div>
            </div>
          </div>
          <div style="margin-top:8px;padding:6px 10px;background:#1e293b;border-radius:4px;
                      font-size:0.78rem;text-align:center;">
            Best bid <strong style="color:#4ade80;">$9.80</strong> meets best ask
            <strong style="color:#ef4444;">$9.80</strong> →
            <strong style="color:#38bdf8;">TRADE at $9.80 ← new market price</strong>
          </div>
        </div>

        <div class="t7-callout">
          <strong>Price discovery priority:</strong><br>
          1. Last executed trade price (most recent)<br>
          2. Midpoint of best bid + best ask (if no recent trades)<br>
          3. Best bid or best ask alone (if only one side active)<br>
          4. No price (if no orders at all — item shows N/A on ticker)
        </div>

        <!-- supply push animation -->
        <div class="t7-chart">
          <div style="font-size:0.75rem;color:#64748b;margin-bottom:8px;font-weight:600;">
            SUPPLY &amp; DEMAND DRIVES THE PRICE
          </div>
          <svg viewBox="0 0 300 140" style="width:100%;max-width:420px;display:block;">
            <!-- axes -->
            <line x1="30" y1="120" x2="280" y2="120" stroke="#334155" stroke-width="1"/>
            <line x1="30" y1="15"  x2="30"  y2="120" stroke="#334155" stroke-width="1"/>
            <text x="155" y="135" fill="#64748b" font-size="8" text-anchor="middle">Quantity</text>
            <text x="12"  y="67"  fill="#64748b" font-size="7" text-anchor="middle" transform="rotate(-90,12,67)">Price</text>
            <!-- demand curve (downsloping) -->
            <polyline points="50,20 100,45 155,70 210,95 260,115"
              fill="none" stroke="#38bdf8" stroke-width="2"/>
            <text x="262" y="118" fill="#38bdf8" font-size="7">Demand</text>
            <!-- supply curve (upsloping) -->
            <polyline points="50,115 100,90 155,65 210,40 260,20"
              fill="none" stroke="#f97316" stroke-width="2"/>
            <text x="262" y="23" fill="#f97316" font-size="7">Supply</text>
            <!-- equilibrium point -->
            <circle cx="155" cy="67" r="4" fill="#4ade80" class="t7-pulse"/>
            <line x1="155" y1="67" x2="155" y2="120" stroke="#4ade80" stroke-width="1" stroke-dasharray="3,2"/>
            <line x1="30"  y1="67" x2="155" y2="67"  stroke="#4ade80" stroke-width="1" stroke-dasharray="3,2"/>
            <text x="157" y="80"  fill="#4ade80" font-size="6.5">Equilibrium</text>
            <text x="157" y="88"  fill="#4ade80" font-size="6.5">price &amp; qty</text>
          </svg>
          <div style="font-size:0.72rem;color:#334155;margin-top:4px;">
            The order book is this chart in real-time. More sellers → price drops. More buyers → price rises.
          </div>
        </div>
        """

    elif step == 3:
        title = "Price Elasticity of Demand"
        content = """
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 10px;">
          <strong style="color:#e5e7eb;">Elasticity</strong> measures how sensitive
          your customers are to your price. It's the most important number in your retail strategy.
          Each item in the game has its own fixed elasticity value built into its config.
        </p>

        <div class="t7-formula">Sales Multiplier = (Your Price ÷ Market Price) ^ Elasticity</div>

        <div class="t7-callout">
          Multiplier = <strong>1.0</strong> → normal sales speed (price = market)<br>
          Multiplier &gt; 1.0 → <strong style="color:#ef4444;">slower</strong> sales (price above market)<br>
          Multiplier &lt; 1.0 → <strong style="color:#4ade80;">faster</strong> sales (price below market, capped at 20×)
        </div>

        <!-- elasticity spectrum -->
        <div class="t7-chart">
          <div style="font-size:0.75rem;color:#64748b;margin-bottom:10px;font-weight:600;">
            ELASTICITY SPECTRUM
          </div>
          <div style="position:relative;height:28px;background:linear-gradient(to right,#22c55e,#38bdf8,#f59e0b,#ef4444);
                      border-radius:4px;margin-bottom:24px;">
            <span style="position:absolute;left:2%;top:6px;font-size:0.65rem;color:#020617;font-weight:700;">0.0</span>
            <span style="position:absolute;left:25%;top:6px;font-size:0.65rem;color:#020617;font-weight:700;">0.5</span>
            <span style="position:absolute;left:50%;top:6px;font-size:0.65rem;color:#020617;font-weight:700;">1.0</span>
            <span style="position:absolute;left:74%;top:6px;font-size:0.65rem;color:#020617;font-weight:700;">1.5</span>
            <span style="position:absolute;right:2%;top:6px;font-size:0.65rem;color:#020617;font-weight:700;">2.0+</span>
          </div>
          <table class="t7-table">
            <tr>
              <th>Elasticity</th><th>Type</th><th>What It Means</th><th>Examples</th>
            </tr>
            <tr>
              <td><strong style="color:#22c55e;">&lt; 0.5</strong></td>
              <td>Highly Inelastic</td>
              <td>Customers barely react to price changes. You can charge 30% above market with minimal sales impact.</td>
              <td>Gasoline (0.4), Diesel (0.3), Religious books (0.3)</td>
            </tr>
            <tr>
              <td><strong style="color:#38bdf8;">0.5 – 1.0</strong></td>
              <td>Moderately Inelastic</td>
              <td>Some sensitivity. 10% markup causes mild slowdown.</td>
              <td>Apple Pie (0.8), Mica (0.8), Agate (1.0)</td>
            </tr>
            <tr>
              <td><strong style="color:#f59e0b;">1.0 – 1.5</strong></td>
              <td>Moderately Elastic</td>
              <td>Customers notice and compare. Keep near market price.</td>
              <td>Produce, electronics, standard goods</td>
            </tr>
            <tr>
              <td><strong style="color:#ef4444;">&gt; 1.5</strong></td>
              <td>Highly Elastic</td>
              <td>Even 3% above market tanks sales significantly. Price competitively or items sit unsold.</td>
              <td>Floral Centerpiece (1.8), Orchid (1.8), Funeral Wreath (1.6)</td>
            </tr>
          </table>
        </div>

        <!-- concrete price impact chart -->
        <div class="t7-chart">
          <div style="font-size:0.75rem;color:#64748b;margin-bottom:8px;font-weight:600;">
            10% PRICE MARKUP — SALES SLOWDOWN BY ELASTICITY
          </div>
          <div style="display:flex;flex-direction:column;gap:5px;font-size:0.75rem;">
            <div style="display:flex;align-items:center;gap:8px;">
              <span style="width:90px;color:#22c55e;">ε = 0.3 (fuel)</span>
              <div class="t7-bar-wrap" style="flex:1;">
                <div class="t7-bar t7-anim-bar" style="--tw:97%;background:#22c55e;width:0;"></div>
              </div>
              <span style="color:#22c55e;width:50px;">−3% sales</span>
            </div>
            <div style="display:flex;align-items:center;gap:8px;">
              <span style="width:90px;color:#38bdf8;">ε = 0.8 (pie)</span>
              <div class="t7-bar-wrap" style="flex:1;">
                <div class="t7-bar t7-anim-bar" style="--tw:92.5%;background:#38bdf8;width:0;animation-delay:.15s"></div>
              </div>
              <span style="color:#38bdf8;width:50px;">−7.5% sales</span>
            </div>
            <div style="display:flex;align-items:center;gap:8px;">
              <span style="width:90px;color:#f59e0b;">ε = 1.2</span>
              <div class="t7-bar-wrap" style="flex:1;">
                <div class="t7-bar t7-anim-bar" style="--tw:88.5%;background:#f59e0b;width:0;animation-delay:.3s"></div>
              </div>
              <span style="color:#f59e0b;width:50px;">−11.5% sales</span>
            </div>
            <div style="display:flex;align-items:center;gap:8px;">
              <span style="width:90px;color:#ef4444;">ε = 1.8 (orchid)</span>
              <div class="t7-bar-wrap" style="flex:1;">
                <div class="t7-bar t7-anim-bar" style="--tw:82%;background:#ef4444;width:0;animation-delay:.45s"></div>
              </div>
              <span style="color:#ef4444;width:50px;">−18% sales</span>
            </div>
          </div>
          <div style="font-size:0.7rem;color:#334155;margin-top:6px;">
            All above: pricing 10% above market. Same markup, very different consequences.
          </div>
        </div>
        """

    elif step == 4:
        title = "Optimal Pricing Strategy"
        content = """
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 10px;">
          The engine computes a <strong style="color:#e5e7eb;">Sales Multiplier</strong> every tick.
          This multiplier divides your base sale probability, so a multiplier of 2.0 means your
          item sells at <em>half</em> the normal rate.
          Here's how to set prices to maximize revenue, not just margin.
        </p>

        <div class="t7-callout">
          <strong>Rule of thumb by elasticity:</strong><br>
          ε &lt; 0.5 → charge up to <strong style="color:#22c55e;">+30%</strong> above market<br>
          ε 0.5–1.0 → up to <strong style="color:#38bdf8;">+10%</strong> is safe<br>
          ε 1.0–1.5 → stay within <strong style="color:#f59e0b;">+8%</strong><br>
          ε &gt; 1.5 → never more than <strong style="color:#ef4444;">+3%</strong>
        </div>

        <!-- worked example: gasoline vs orchid -->
        <div class="t7-chart">
          <div style="font-size:0.75rem;color:#64748b;margin-bottom:8px;font-weight:600;">
            WORKED EXAMPLE: GASOLINE (ε=0.4) AT $11 vs MARKET $10
          </div>
          <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;font-size:0.75rem;text-align:center;">
            <div style="background:#0a0f1a;border:1px solid #1e293b;border-radius:4px;padding:8px;">
              <div style="color:#64748b;font-size:0.65rem;margin-bottom:4px;">MULTIPLIER</div>
              <div style="font-size:1.1rem;font-weight:bold;color:#38bdf8;">(11/10)^0.4</div>
              <div style="color:#4ade80;font-size:0.9rem;margin-top:2px;">= 1.038</div>
            </div>
            <div style="background:#0a0f1a;border:1px solid #1e293b;border-radius:4px;padding:8px;">
              <div style="color:#64748b;font-size:0.65rem;margin-bottom:4px;">SALES SLOWDOWN</div>
              <div style="font-size:1.1rem;font-weight:bold;color:#f59e0b;">−3.8%</div>
              <div style="color:#94a3b8;font-size:0.72rem;margin-top:2px;">barely noticeable</div>
            </div>
            <div style="background:#0a0f1a;border:1px solid #1e293b;border-radius:4px;padding:8px;">
              <div style="color:#64748b;font-size:0.65rem;margin-bottom:4px;">PROFIT GAIN</div>
              <div style="font-size:1.1rem;font-weight:bold;color:#22c55e;">+10%/unit</div>
              <div style="color:#94a3b8;font-size:0.72rem;margin-top:2px;">net positive</div>
            </div>
          </div>
        </div>

        <div class="t7-chart">
          <div style="font-size:0.75rem;color:#64748b;margin-bottom:8px;font-weight:600;">
            SAME MARKUP: ORCHID (ε=1.8) AT $11 vs MARKET $10
          </div>
          <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;font-size:0.75rem;text-align:center;">
            <div style="background:#0a0f1a;border:1px solid #1e293b;border-radius:4px;padding:8px;">
              <div style="color:#64748b;font-size:0.65rem;margin-bottom:4px;">MULTIPLIER</div>
              <div style="font-size:1.1rem;font-weight:bold;color:#38bdf8;">(11/10)^1.8</div>
              <div style="color:#ef4444;font-size:0.9rem;margin-top:2px;">= 1.185</div>
            </div>
            <div style="background:#0a0f1a;border:1px solid #1e293b;border-radius:4px;padding:8px;">
              <div style="color:#64748b;font-size:0.65rem;margin-bottom:4px;">SALES SLOWDOWN</div>
              <div style="font-size:1.1rem;font-weight:bold;color:#ef4444;">−18.5%</div>
              <div style="color:#94a3b8;font-size:0.72rem;margin-top:2px;">significant</div>
            </div>
            <div style="background:#0a0f1a;border:1px solid #1e293b;border-radius:4px;padding:8px;">
              <div style="color:#64748b;font-size:0.65rem;margin-bottom:4px;">NET RESULT</div>
              <div style="font-size:1.1rem;font-weight:bold;color:#ef4444;">NEGATIVE</div>
              <div style="color:#94a3b8;font-size:0.72rem;margin-top:2px;">revenue lost</div>
            </div>
          </div>
        </div>

        <div class="t7-warn">
          <strong style="color:#fbbf24;">Remember:</strong> discounting <em>below</em> market also works.
          Multiplier &lt; 1.0 means faster sales — great for clearing inventory. The sales rate is floored
          at 20× normal speed (multiplier floor = 0.05) so you can't dump infinite inventory instantly.
        </div>

        <!-- sales rate comparison chart -->
        <div class="t7-chart">
          <div style="font-size:0.75rem;color:#64748b;margin-bottom:8px;font-weight:600;">
            APPLE PIE (base_chance=0.04, ε=0.8) — SALES / HOUR AT DIFFERENT PRICES
          </div>
          <table class="t7-table">
            <tr><th>Your Price</th><th>vs Market</th><th>Multiplier</th><th>Sales/hr</th></tr>
            <tr><td>$9.00</td><td style="color:#4ade80;">−10%</td><td>0.921</td>
                <td><span style="color:#4ade80;">156/hr</span></td></tr>
            <tr><td>$10.00</td><td style="color:#94a3b8;">at market</td><td>1.000</td>
                <td><span style="color:#38bdf8;">144/hr</span></td></tr>
            <tr><td>$10.80</td><td style="color:#f59e0b;">+8%</td><td>1.063</td>
                <td><span style="color:#f59e0b;">135/hr</span></td></tr>
            <tr><td>$11.00</td><td style="color:#ef4444;">+10%</td><td>1.078</td>
                <td><span style="color:#ef4444;">134/hr</span></td></tr>
            <tr><td>$12.00</td><td style="color:#ef4444;">+20%</td><td>1.155</td>
                <td><span style="color:#ef4444;">125/hr</span></td></tr>
          </table>
          <div style="font-size:0.7rem;color:#334155;margin-top:4px;">
            Formula: sales/hr = (base_chance / multiplier) × 3600 ticks/hour
          </div>
        </div>
        """

    elif step == 5:
        title = "Terrain Types, Proximity Bonuses & Land Tax"
        content = """
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 10px;">
          The terrain type of a plot determines which businesses you can build on it
          and how much monthly land tax you owe. Proximity features multiply the base tax —
          and usually unlock better business types too.
        </p>

        <!-- terrain tax table -->
        <div class="t7-chart" style="max-height:260px;overflow-y:auto;">
          <div style="font-size:0.75rem;color:#64748b;margin-bottom:6px;font-weight:600;">
            TERRAIN BASE TAX (before proximity modifiers)
          </div>
          <table class="t7-table">
            <tr><th>Terrain</th><th>Base Tax/mo</th><th>Characteristics</th></tr>
            <tr><td>Urban</td>      <td style="color:#ef4444;">$120</td><td>High demand, city-adjacent</td></tr>
            <tr><td>Ocean</td>      <td style="color:#ef4444;">$100</td><td>Offshore operations</td></tr>
            <tr><td>Coastal</td>    <td style="color:#f97316;">$80</td> <td>Ocean access, trade</td></tr>
            <tr><td>Mountain</td>   <td style="color:#f59e0b;">$70</td> <td>Mining potential</td></tr>
            <tr><td>Island</td>     <td style="color:#f59e0b;">$65</td> <td>Isolated, premium</td></tr>
            <tr><td>Lake</td>       <td style="color:#eab308;">$60</td> <td>Fishing, aquaculture</td></tr>
            <tr><td>Forest</td>     <td style="color:#eab308;">$60</td> <td>Lumber, resources</td></tr>
            <tr><td>Jungle</td>     <td style="color:#84cc16;">$55</td> <td>Exotic resources</td></tr>
            <tr><td>Hills</td>      <td style="color:#84cc16;">$52</td> <td>Rolling terrain</td></tr>
            <tr><td>Prairie</td>    <td style="color:#22c55e;">$50</td> <td>Most common, farming</td></tr>
            <tr><td>Savanna</td>    <td style="color:#22c55e;">$45</td> <td>Tropical grassland</td></tr>
            <tr><td>Marsh</td>      <td style="color:#22c55e;">$40</td> <td>Unique resources</td></tr>
            <tr><td>Tundra</td>     <td style="color:#22c55e;">$35</td> <td>Cold, sparse</td></tr>
            <tr><td>Desert</td>     <td style="color:#4ade80;">$30</td> <td>Cheapest non-district</td></tr>
          </table>
        </div>

        <!-- proximity multipliers -->
        <div class="t7-chart">
          <div style="font-size:0.75rem;color:#64748b;margin-bottom:6px;font-weight:600;">
            PROXIMITY FEATURES — TAX MULTIPLIERS
          </div>
          <div style="display:flex;flex-wrap:wrap;gap:6px;font-size:0.74rem;">
            <span style="padding:3px 8px;background:#1a0505;border:1px solid #ef4444;border-radius:3px;color:#ef4444;">urban ×2.0</span>
            <span style="padding:3px 8px;background:#1a0a00;border:1px solid #f97316;border-radius:3px;color:#f97316;">deposits ×1.7</span>
            <span style="padding:3px 8px;background:#0a1219;border:1px solid #f59e0b;border-radius:3px;color:#f59e0b;">oasis ×1.6</span>
            <span style="padding:3px 8px;background:#0a1219;border:1px solid #eab308;border-radius:3px;color:#eab308;">coastal ×1.5</span>
            <span style="padding:3px 8px;background:#091219;border:1px solid #38bdf8;border-radius:3px;color:#38bdf8;">hot springs ×1.4</span>
            <span style="padding:3px 8px;background:#091219;border:1px solid #38bdf8;border-radius:3px;color:#38bdf8;">riverside ×1.3</span>
            <span style="padding:3px 8px;background:#091219;border:1px solid #38bdf8;border-radius:3px;color:#38bdf8;">volcanic ×1.3</span>
            <span style="padding:3px 8px;background:#091219;border:1px solid #94a3b8;border-radius:3px;color:#94a3b8;">road ×1.25</span>
            <span style="padding:3px 8px;background:#091219;border:1px solid #94a3b8;border-radius:3px;color:#94a3b8;">lakeside ×1.2</span>
            <span style="padding:3px 8px;background:#091219;border:1px solid #64748b;border-radius:3px;color:#64748b;">caves ×1.1</span>
            <span style="padding:3px 8px;background:#051a05;border:1px solid #22c55e;border-radius:3px;color:#22c55e;">remote ×0.7 ↓ cheaper!</span>
          </div>
          <div style="font-size:0.7rem;color:#334155;margin-top:6px;">
            Final tax = base_tax × size × proximity_multiplier.
            Starter plots get an additional 50% discount.
          </div>
        </div>

        <!-- hoarding tax -->
        <div class="t7-warn">
          <strong style="color:#fbbf24;">⚠️ Hoarding Tax:</strong>
          Your first 5 plots are free of this tax.
          Beyond 5, each extra plot incurs a <em>Fibonacci-escalating</em> monthly penalty:
          plot 6 = $5,000/mo · plot 7 = $5,500/mo · plot 8 = $6,000/mo · plot 9 = $6,500/mo …
          This tax is collected hourly and scales aggressively.
          Land-executive bonuses can reduce it.
        </div>
        """

    elif step == 6:
        title = "Production Economics — Costs, Margins & the Full Picture"
        content = """
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 10px;">
          Now let's connect everything: your <em>total cost per unit</em> determines your minimum
          viable price. Your elasticity determines how much above cost you can actually charge
          while keeping your sell rate healthy.
        </p>

        <div class="t7-formula">Unit Cost = (Wages + Σ input_item_cost × qty) ÷ output_qty</div>

        <div class="t7-callout">
          Cost is calculated <strong>iteratively</strong> — the game solves circular dependencies
          (e.g., Paper needs Water, Water needs Paper) over up to 50 passes until the answer
          converges within 0.0001 tolerance.
        </div>

        <!-- full worked example -->
        <div class="t7-chart">
          <div style="font-size:0.75rem;color:#64748b;margin-bottom:8px;font-weight:600;">
            FAST FOOD KITCHEN: FULL ECONOMICS BREAKDOWN
          </div>
          <table class="t7-table">
            <tr><th>Component</th><th>Detail</th><th>Amount</th></tr>
            <tr><td>Wages</td><td>$15,000/cycle (waived on tutorial reward biz)</td>
                <td style="color:#f97316;">$15,000</td></tr>
            <tr><td>Inputs</td><td>250 beef + 500 bread + 100 onions + …</td>
                <td style="color:#f97316;">~$8,000</td></tr>
            <tr><td>Total batch cost</td><td>wages + inputs</td>
                <td style="color:#ef4444;font-weight:bold;">~$23,000</td></tr>
            <tr><td>Output</td><td>per production cycle</td>
                <td style="color:#94a3b8;">~400 burgers</td></tr>
            <tr><td>Cost / burger</td><td>$23,000 ÷ 400</td>
                <td style="color:#38bdf8;font-weight:bold;">≈ $57.50</td></tr>
          </table>
          <div style="margin-top:8px;padding:8px;background:#0a0f1a;border-radius:4px;font-size:0.78rem;">
            <strong style="color:#4ade80;">Your Tutorial Reward Kitchen:</strong> wages are $0 forever,
            so your cost is just inputs ÷ output ≈ <strong style="color:#4ade80;">$20/burger</strong>.
            Much better margins!
          </div>
        </div>

        <!-- the full profit flow -->
        <div class="t7-chart">
          <div style="font-size:0.75rem;color:#64748b;margin-bottom:10px;font-weight:600;">
            THE COMPLETE PROFIT FLOW
          </div>
          <div style="display:flex;flex-direction:column;gap:6px;font-size:0.78rem;">
            <div style="display:flex;align-items:center;gap:8px;">
              <div style="width:26px;height:26px;background:#1e293b;border-radius:50%;
                          display:flex;align-items:center;justify-content:center;
                          font-weight:bold;color:#38bdf8;flex-shrink:0;">1</div>
              <div><strong style="color:#e5e7eb;">Land tax</strong>
                <span style="color:#64748b;"> — paid monthly (0 if tutorial reward)</span></div>
            </div>
            <div style="margin-left:13px;width:1px;height:10px;background:#334155;"></div>
            <div style="display:flex;align-items:center;gap:8px;">
              <div style="width:26px;height:26px;background:#1e293b;border-radius:50%;
                          display:flex;align-items:center;justify-content:center;
                          font-weight:bold;color:#38bdf8;flex-shrink:0;">2</div>
              <div><strong style="color:#e5e7eb;">Input costs</strong>
                <span style="color:#64748b;"> — buy raw materials on market</span></div>
            </div>
            <div style="margin-left:13px;width:1px;height:10px;background:#334155;"></div>
            <div style="display:flex;align-items:center;gap:8px;">
              <div style="width:26px;height:26px;background:#1e293b;border-radius:50%;
                          display:flex;align-items:center;justify-content:center;
                          font-weight:bold;color:#38bdf8;flex-shrink:0;">3</div>
              <div><strong style="color:#e5e7eb;">Wages</strong>
                <span style="color:#64748b;"> — paid each production cycle (÷ efficiency multiplier)</span></div>
            </div>
            <div style="margin-left:13px;width:1px;height:10px;background:#334155;"></div>
            <div style="display:flex;align-items:center;gap:8px;">
              <div style="width:26px;height:26px;background:#1e293b;border-radius:50%;
                          display:flex;align-items:center;justify-content:center;
                          font-weight:bold;color:#38bdf8;flex-shrink:0;">4</div>
              <div><strong style="color:#e5e7eb;">Set retail price</strong>
                <span style="color:#64748b;"> — use elasticity to find optimal markup</span></div>
            </div>
            <div style="margin-left:13px;width:1px;height:10px;background:#334155;"></div>
            <div style="display:flex;align-items:center;gap:8px;">
              <div style="width:26px;height:26px;background:#1e293b;border-radius:50%;
                          display:flex;align-items:center;justify-content:center;
                          font-weight:bold;color:#38bdf8;flex-shrink:0;">5</div>
              <div><strong style="color:#e5e7eb;">Sales tax</strong>
                <span style="color:#64748b;"> — deducted from proceeds if you're in a city (contributes to city treasury)</span></div>
            </div>
            <div style="margin-left:13px;width:1px;height:10px;background:#334155;"></div>
            <div style="display:flex;align-items:center;gap:8px;">
              <div style="width:26px;height:26px;background:#22c55e;border-radius:50%;
                          display:flex;align-items:center;justify-content:center;
                          font-weight:bold;color:#020617;flex-shrink:0;">✓</div>
              <div><strong style="color:#4ade80;">Net revenue</strong>
                <span style="color:#64748b;"> = sale price – wages – sales tax. Your profit.</span></div>
            </div>
          </div>
        </div>
        """

    elif step == 7:
        title = "Tutorial 7 Complete — Claim Your Trophies!"
        content = f"""
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 12px;">
          You now understand the full economic engine behind every land plot and retail business
          in Wadsworth. Here's a quick reference card to keep handy:
        </p>

        <div class="t7-chart">
          <div style="font-size:0.75rem;color:#64748b;margin-bottom:8px;font-weight:600;">
            QUICK REFERENCE CARD
          </div>
          <table class="t7-table">
            <tr><th>System</th><th>Key Formula / Rule</th></tr>
            <tr><td>Efficiency</td>
                <td>Starts 100%, decays ~7.14%/day (0% in 14 days). Wages = base ÷ (eff/100). Ceiling 200× at 0%. Tutorial reward plots never decay. Restoration (&lt;30%): target = max × 1.5; max grows each cycle; cost = wage_mult × $1k; 60-day cooldown.</td></tr>
            <tr><td>Market Price</td>
                <td>Last trade &gt; bid-ask midpoint &gt; best single side &gt; N/A</td></tr>
            <tr><td>Elasticity</td>
                <td>Multiplier = (price/market)^ε · &lt;0.5 inelastic · &gt;1.5 very elastic</td></tr>
            <tr><td>Optimal markup</td>
                <td>ε&lt;0.5→+30% · ε&lt;1.0→+10% · ε&lt;1.5→+8% · ε≥1.5→+3%</td></tr>
            <tr><td>Land tax</td>
                <td>base × size × proximity_modifier. First 5 plots free of hoarding tax.</td></tr>
            <tr><td>Unit cost</td>
                <td>(wages ÷ eff_mult + Σ input costs) ÷ output_qty</td></tr>
          </table>
        </div>

        <div style="background:rgba(56,189,248,.08);border:1px solid rgba(56,189,248,.3);
                    border-radius:6px;padding:12px 16px;margin-bottom:16px;">
            <strong style="color:#38bdf8;">&#127942; Reward: {T7_TROPHY_REWARD} Trophies</strong>
            <p style="color:#94a3b8;font-size:0.85rem;margin:6px 0 0;">
                Added to your trophy count toward your player level.
                View on the <a href="/events" style="color:#38bdf8;">Events &amp; Tasks</a> page.
            </p>
        </div>
        <form action="/api/tutorial7/claim-reward" method="post">
            <button type="submit" style="background:#38bdf8;color:#020617;border:none;
                    padding:10px 24px;border-radius:4px;cursor:pointer;
                    font-size:0.9rem;font-weight:bold;">
                Claim {T7_TROPHY_REWARD} Trophies! &#127942;
            </button>
        </form>
        """

    else:
        return ""

    # ── Wrapper ───────────────────────────────────────────────────────────────
    display_step = min(step, T7_TOTAL_STEPS)
    return SHARED_CSS + f"""
    <div id="tutorial7-panel" style="
        background: linear-gradient(135deg, #0a1628, #0f172a);
        border: 2px solid #f97316;
        border-radius: 6px;
        padding: 20px 24px;
        margin-bottom: 24px;
        position: relative;
    ">
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:14px;flex-wrap:wrap;">
            <span style="background:#f97316;color:#020617;padding:3px 12px;border-radius:12px;
                         font-size:0.7rem;font-weight:bold;letter-spacing:0.05em;">
                TUTORIAL — STEP {display_step}/{T7_TOTAL_STEPS}
            </span>
            <span style="color:#f97316;font-size:0.85rem;font-weight:bold;">
                Level 7 &middot; Supply, Demand &amp; Efficiency
            </span>
            <div style="flex:1;background:#1e293b;height:4px;border-radius:2px;min-width:80px;">
                <div style="background:#f97316;height:4px;border-radius:2px;
                            width:{int(display_step / T7_TOTAL_STEPS * 100)}%;"></div>
            </div>
        </div>
        <h3 style="color:#f97316;margin:0 0 12px 0;font-size:1.05rem;">{title}</h3>
        {content}
        <div style="margin-top:14px;">
            <form action="/api/tutorial7/advance" method="post" style="display:inline;">
                <button type="submit" style="background:#f97316;color:#020617;border:none;
                        padding:8px 20px;border-radius:4px;cursor:pointer;
                        font-size:0.88rem;font-weight:bold;">
                    {"Claim Reward →" if step == 7 else "Next →"}
                </button>
            </form>
        </div>
        <a href="/api/tutorial7/dismiss"
           onclick="return confirm('Skip Tutorial 7? Restart anytime from Settings → Tutorials.');"
           style="position:absolute;top:12px;right:16px;color:#475569;
                  font-size:0.72rem;text-decoration:none;">Skip</a>
    </div>
    """


# ── Banner (shown on Settings → Tutorials tab) ────────────────────────────────

def get_tutorial7_banner_html(player) -> str:
    if not should_show_tutorial7_banner(player):
        return ""
    return """
    <div style="
        background: linear-gradient(135deg, #150a00, #0f172a);
        border: 2px solid #f97316;
        border-radius: 6px;
        padding: 20px 24px;
        margin-bottom: 24px;
    ">
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:14px;flex-wrap:wrap;">
            <span style="background:#f97316;color:#020617;padding:3px 12px;border-radius:12px;
                         font-size:0.7rem;font-weight:bold;letter-spacing:0.05em;">
                NEW TUTORIAL AVAILABLE
            </span>
            <span style="color:#f97316;font-size:0.85rem;font-weight:bold;">
                Level 7 &middot; Supply, Demand &amp; Efficiency
            </span>
        </div>
        <h3 style="color:#f97316;margin:0 0 10px 0;font-size:1.05rem;">
            Master the Economics Behind Every Business
        </h3>
        <p style="color:#94a3b8;line-height:1.7;margin:0 0 16px 0;">
            Tutorial 7 is the most detailed tutorial in the game. You'll learn
            <strong style="color:#e5e7eb;">price elasticity</strong>,
            <strong style="color:#e5e7eb;">land plot efficiency</strong>,
            <strong style="color:#e5e7eb;">optimal pricing strategy</strong>,
            <strong style="color:#e5e7eb;">supply &amp; demand mechanics</strong>,
            terrain taxes, hoarding penalties, and how to calculate true unit cost.
            Packed with interactive charts and animated examples.
            Complete it to earn <strong style="color:#f97316;">20 trophies</strong>.
        </p>
        <form action="/api/tutorial7/start" method="post" style="display:inline;">
            <button type="submit" style="background:#f97316;color:#020617;border:none;
                    padding:10px 20px;border-radius:4px;font-weight:bold;
                    font-size:0.9rem;cursor:pointer;">
                Start Tutorial 7 →
            </button>
        </form>
    </div>
    """


# ── API routes ────────────────────────────────────────────────────────────────

@router.post("/api/tutorial7/start")
def tutorial7_start(session_token: Optional[str] = Cookie(None)):
    player = _get_player_from_cookie(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)
    if get_tutorial7_step(player.id) == 0:
        set_tutorial7_step(player.id, 1)
    return RedirectResponse(url="/land", status_code=303)


@router.post("/api/tutorial7/advance")
def tutorial7_advance(session_token: Optional[str] = Cookie(None)):
    player = _get_player_from_cookie(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)
    step = get_tutorial7_step(player.id)
    if 1 <= step <= T7_TOTAL_STEPS:
        next_step = step + 1
        set_tutorial7_step(player.id, next_step)
        if next_step > T7_TOTAL_STEPS:
            return RedirectResponse(url="/land", status_code=303)
    return RedirectResponse(url="/land", status_code=303)


@router.post("/api/tutorial7/claim-reward")
def tutorial7_claim_reward(session_token: Optional[str] = Cookie(None)):
    """Step 7 → 8: Award trophies."""
    player = _get_player_from_cookie(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)
    if get_tutorial7_step(player.id) != 7:
        return RedirectResponse(url="/", status_code=303)

    try:
        from events import PlayerRank, SessionLocal as _ev_session, LEVEL_THRESHOLDS
        from datetime import datetime as _dt
        _db = _ev_session()
        rank = _db.query(PlayerRank).filter(PlayerRank.player_id == player.id).first()
        if not rank:
            rank = PlayerRank(player_id=player.id, trophies=0, level=1)
            _db.add(rank)
        rank.trophies = (rank.trophies or 0) + T7_TROPHY_REWARD
        rank.updated_at = _dt.utcnow()
        level = 1
        for i, threshold in enumerate(LEVEL_THRESHOLDS):
            if rank.trophies >= threshold:
                level = i + 2
            else:
                break
        rank.level = level
        _db.commit()
        _db.close()
        try:
            from push_ux import send_push_notification
            send_push_notification(
                player.id,
                "🏆 Tutorial 7 Complete!",
                f"You earned {T7_TROPHY_REWARD} trophies for mastering Supply, Demand & Efficiency!",
                url="/events",
                notif_type="tasks_events",
                tag="tutorial7-complete",
            )
        except Exception:
            pass
    except Exception as e:
        print(f"[Tutorial7] Trophy award error: {e}")

    set_tutorial7_step(player.id, 8, is_completion=True)
    return RedirectResponse(url="/land?t7_complete=1", status_code=303)


@router.post("/api/tutorial7/restart")
def tutorial7_restart(session_token: Optional[str] = Cookie(None)):
    player = _get_player_from_cookie(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)
    if (getattr(player, "tutorial_7_step", 0) or 0) > 0:
        set_tutorial7_step(player.id, 1)
    return RedirectResponse(url="/land", status_code=303)


@router.get("/api/tutorial7/dismiss")
@router.post("/api/tutorial7/dismiss")
def tutorial7_dismiss(session_token: Optional[str] = Cookie(None)):
    player = _get_player_from_cookie(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)
    set_tutorial7_step(player.id, 8)
    return RedirectResponse(url="/", status_code=303)
