import asyncio
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, Cookie
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

# ==========================
# GLOBAL TICK STATE
# ==========================

TICK_INTERVAL = 5.0  # seconds
current_tick = 0
tick_start_time = None
tick_task = None

# ==========================
# MODULE REGISTRY
# ==========================

modules = {}

def register_module(name: str, module):
    """Register a module with the application."""
    modules[name] = module
    print(f" → {name.capitalize()} registered")

def load_modules():
    """Attempt to load all game modules."""
    module_names = ['auth', 'inventory', 'business', 'market', 'land', 'land_market', 'banks', 'districts', 'district_market', 'cities', 'counties', 'memecoins', 'wallet', 'stats_ux', 'executive', 'estate', 'p2p', 'chat', 'admins', 'dm']
    for name in module_names:
        try:
            mod = __import__(name)
            register_module(name, mod)
        except ModuleNotFoundError:
            pass

# ==========================
# TICK LOOP
# ==========================

async def tick_loop():
    """Global tick loop executing every second."""
    global current_tick
    while True:
        current_tick += 1
        now = datetime.utcnow()
        for name, module in modules.items():
            if hasattr(module, 'tick'):
                try:
                    await module.tick(current_tick, now)
                except Exception as e:
                    print(f"[Tick {current_tick}] ERROR in {name}: {e}")
        
        if current_tick % 60 == 0:
            print(f"[Tick {current_tick}] {now.isoformat()}")
        await asyncio.sleep(TICK_INTERVAL)

# ==========================
# MODULE INITIALIZATION
# ==========================

def initialize_modules():
    """Initialize all registered modules."""
    print("Initializing modules...")
    for name, module in modules.items():
        if hasattr(module, 'initialize'):
            try:
                module.initialize()
                print(f" ✓ {name.capitalize()} initialized")
            except Exception as e:
                print(f" ✗ {name.capitalize()} failed: {e}")
    if not modules:
        print(" (No modules loaded)")
    print("Module initialization complete.")

# ==========================
# LIFESPAN MANAGEMENT
# ==========================

@asynccontextmanager
async def lifespan(app: FastAPI):
    global tick_start_time, tick_task
    print("=" * 50)
    print("Starting Real-Time Economic Simulation")
    print("=" * 50)
    tick_start_time = datetime.utcnow()
    load_modules()
    initialize_modules()
    tick_task = asyncio.create_task(tick_loop())
    print(f"Tick loop started (interval: {TICK_INTERVAL}s)")
    print("=" * 50)
    yield
    print("\nShutting down...")
    if tick_task:
        tick_task.cancel()
        try:
            await tick_task
        except asyncio.CancelledError:
            pass
    print("Shutdown complete.")

# ==========================
# FASTAPI APP
# ==========================

app = FastAPI(
    title="Wadsworth Economic Simulation",
    description="Real-time multiplayer economic simulation",
    version="1.1.2132026",
    lifespan=lifespan
)

app.mount("/static", StaticFiles(directory="static"), name="static")

# ==========================
# SYSTEM ENDPOINTS (PATCHED)
# ==========================
# Update within app.py @app.get("/api/status")
@app.get("/api/status")
async def get_status(session_token: Optional[str] = Cookie(None)):
    from auth import get_player_from_session, get_db
    from business import Business # Add this import
    
    db = get_db()
    player = get_player_from_session(db, session_token)
    
    # Fetch active business progress for this player
    biz_list = []
    if player:
        user_biz = db.query(Business).filter(Business.owner_id == player.id).all()
        # Fetch cycles_to_complete from your BUSINESS_TYPES config
        from business import BUSINESS_TYPES
        for b in user_biz:
            config = BUSINESS_TYPES.get(b.business_type, {})
            biz_list.append({
                "id": b.id,
                "progress_ticks": b.progress_ticks,
                "cycles_to_complete": config.get("cycles_to_complete", 1)
            })

    status_data = {
        "status": "running",
        "current_tick": current_tick,
        "player_balance": player.cash_balance if player else 0,
        "businesses": biz_list, # Now the progress bars can move!
        "modules": {name: True for name in modules.keys()}
    }
    db.close()
    return status_data

@app.get("/api/tick")
async def get_tick():
    return {
        "tick": current_tick,
        "timestamp": datetime.utcnow().isoformat()
    }

# ==========================
# ROUTING
# ==========================

try:
    from auth import router as auth_router
    app.include_router(auth_router)
    print("Auth routes registered")
except ModuleNotFoundError:
    pass

try:
    from ux import router as ux_router
    app.include_router(ux_router)
    print("UX routes registered")
except ModuleNotFoundError:
    @app.get("/")
    async def root():
        return {
            "message": "Wadsworth Economic Simulation",
            "status": "UX module not loaded",
            "tick": current_tick,
            "api_status": "/api/status"
        }

try:
    from corporate_actions_ux import router as corporate_actions_router
    app.include_router(corporate_actions_router)
    print("Corporate Actions routes registered")
except ModuleNotFoundError:
    pass

try:
    from corporate_actions_ui import router as corporate_actions_ui_router
    app.include_router(corporate_actions_ui_router)
    print("Corporate Actions UI routes registered")
except ModuleNotFoundError:
    pass

try:
    from districts_ux import router as districts_ux_router
    app.include_router(districts_ux_router)
    print("Districts UX routes registered")
except ModuleNotFoundError:
    pass

try:
    from stats_ux import router as stats_router
    app.include_router(stats_router)
    print("Stats routes registered")
except ModuleNotFoundError:
    pass

try:
    from cities_ux import router as cities_router
    app.include_router(cities_router)
    print("Cities routes registered")
except ModuleNotFoundError:
    pass

try:
    from counties_ux import router as counties_router
    app.include_router(counties_router)
    print("Counties routes registered")
except ModuleNotFoundError:
    pass

try:
    from executive_ux import router as executive_router
    app.include_router(executive_router)
    print("Executive routes registered")
except ModuleNotFoundError:
    pass

try:
    from estate_ux import router as estate_router
    app.include_router(estate_router)
    print("Estate routes registered")
except ModuleNotFoundError:
    pass

try:
    from p2p_ux import router as p2p_ux_router
    app.include_router(p2p_ux_router)
    print("P2P UX routes registered")
except ModuleNotFoundError:
    pass

try:
    from chat_ux import router as chat_router
    app.include_router(chat_router)
    print("Chat routes registered")
except ModuleNotFoundError:
    pass

try:
    from admins_ux import router as admins_router
    app.include_router(admins_router)
    print("Admin routes registered")
except ModuleNotFoundError:
    pass

try:
    from memecoins_ux import router as memecoins_router
    app.include_router(memecoins_router)
    print("Meme Coins routes registered")
except ModuleNotFoundError:
    pass

try:
    import wallet  # ensures WSC tables are created and tick handler is registered
    print("Wallet module loaded")
except ModuleNotFoundError:
    pass

try:
    from world_map_ux import router as world_map_router
    app.include_router(world_map_router)
    print("World Map routes registered")
except ModuleNotFoundError:
    pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
