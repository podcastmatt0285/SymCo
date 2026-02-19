"""
memecoins_ux.py

Web UI and API endpoints for the meme coin / shitcoin system.

Routes:
  GET  /county/{county_id}/memecoins          - List all meme coins in county
  GET  /memecoins/launch                      - Launch a new meme coin (form)
  POST /api/memecoins/launch                  - Submit launch form
  GET  /memecoins/{symbol}                    - Coin info page (chart, holders, order book)
  POST /api/memecoins/{symbol}/stake          - Stake native tokens to mine
  POST /api/memecoins/unstake                 - Unstake a mining deposit
  POST /api/memecoins/{symbol}/order          - Place buy/sell order
  POST /api/memecoins/cancel-order            - Cancel an open order
  GET  /api/memecoins/{symbol}/candles        - OHLCV data (JSON, for chart)
  GET  /api/memecoins/{symbol}/holders        - Holder distribution (JSON, for pie)
"""

from typing import Optional
from fastapi import APIRouter, Cookie, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse

router = APIRouter()


# ==========================
# HELPER
# ==========================
def get_current_player(session_token: Optional[str]):
    from auth import get_player_from_session, get_db
    db = get_db()
    player = get_player_from_session(db, session_token)
    db.close()
    return player


# ==========================
# STYLES
# ==========================
MEME_STYLES = """
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    background: #020617;
    color: #e5e7eb;
    min-height: 100vh;
    padding: 20px;
}
.container { max-width: 1400px; margin: 0 auto; }
.header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
    padding-bottom: 16px;
    border-bottom: 1px solid #1e293b;
}
.header h1 { font-size: 22px; color: #f59e0b; letter-spacing: 1px; }
.nav-link { color: #38bdf8; text-decoration: none; margin-left: 16px; font-size: 13px; }
.nav-link:hover { text-decoration: underline; }

.card {
    background: #0b1220;
    border: 1px solid #1e293b;
    border-radius: 10px;
    padding: 18px;
    margin-bottom: 14px;
}
.card h2 { font-size: 16px; color: #f59e0b; margin-bottom: 12px; letter-spacing: 0.5px; }
.card h3 { font-size: 14px; color: #94a3b8; margin-bottom: 8px; }

.grid { display: grid; gap: 14px; }
.grid-2 { grid-template-columns: repeat(2, 1fr); }
.grid-3 { grid-template-columns: repeat(3, 1fr); }
.grid-4 { grid-template-columns: repeat(4, 1fr); }
@media(max-width: 900px) { .grid-2, .grid-3, .grid-4 { grid-template-columns: 1fr; } }

.stat { display: flex; justify-content: space-between; padding: 7px 0; border-bottom: 1px solid #1e293b; font-size: 13px; }
.stat:last-child { border-bottom: none; }
.stat-label { color: #94a3b8; }
.stat-value { font-weight: 600; }
.positive { color: #4ade80; }
.negative { color: #f87171; }
.meme-color { color: #f59e0b; }
.native-color { color: #a78bfa; }
.neutral { color: #94a3b8; }

.btn {
    display: inline-block;
    padding: 9px 18px;
    border-radius: 6px;
    border: none;
    cursor: pointer;
    font-family: inherit;
    font-size: 13px;
    font-weight: 600;
    text-decoration: none;
    transition: opacity 0.15s;
}
.btn:hover { opacity: 0.85; }
.btn-buy  { background: #16a34a; color: #fff; }
.btn-sell { background: #dc2626; color: #fff; }
.btn-meme { background: #b45309; color: #fff; }
.btn-cancel { background: #374151; color: #e5e7eb; }
.btn-primary { background: #0369a1; color: #fff; }
.btn-sm { padding: 5px 10px; font-size: 12px; }

.badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.5px;
}
.badge-meme { background: #78350f; color: #fbbf24; }
.badge-native { background: #4c1d95; color: #a78bfa; }
.badge-buy  { background: #14532d; color: #4ade80; }
.badge-sell { background: #7f1d1d; color: #f87171; }
.badge-filled   { background: #1e3a5f; color: #38bdf8; }
.badge-active   { background: #1f2937; color: #94a3b8; }
.badge-partial  { background: #2d3748; color: #f59e0b; }
.badge-cancelled{ background: #1f2937; color: #6b7280; }

.form-group { margin-bottom: 12px; }
.form-group label { display: block; margin-bottom: 5px; font-size: 12px; color: #94a3b8; }
.form-group input, .form-group select, .form-group textarea {
    width: 100%;
    background: #020617;
    border: 1px solid #334155;
    border-radius: 5px;
    padding: 8px 10px;
    color: #e5e7eb;
    font-family: inherit;
    font-size: 13px;
}
.form-group textarea { min-height: 70px; resize: vertical; }
.form-group input:focus, .form-group select:focus { outline: none; border-color: #f59e0b; }

.table { width: 100%; border-collapse: collapse; font-size: 12px; }
.table th { text-align: left; padding: 8px 10px; color: #64748b; border-bottom: 1px solid #1e293b; font-weight: 500; }
.table td { padding: 8px 10px; border-bottom: 1px solid #0f172a; }
.table tr:last-child td { border-bottom: none; }
.table tr:hover td { background: #0f172a; }

.order-book-side { font-size: 12px; }
.order-row { display: flex; justify-content: space-between; padding: 4px 8px; font-size: 12px; border-radius: 3px; }
.bid-row { border-left: 2px solid #16a34a; background: rgba(22,163,74,0.05); }
.ask-row { border-left: 2px solid #dc2626; background: rgba(220,38,38,0.05); }

.alert { padding: 10px 16px; border-radius: 6px; margin-bottom: 14px; font-size: 13px; }
.alert-success { background: #14532d; border: 1px solid #16a34a; color: #4ade80; }
.alert-error { background: #7f1d1d; border: 1px solid #dc2626; color: #f87171; }

.logo-cell { display: inline-block; vertical-align: middle; width: 22px; height: 22px; }
.meme-card {
    background: #0b1220;
    border: 1px solid #1e293b;
    border-radius: 10px;
    padding: 14px;
    transition: border-color 0.15s;
    text-decoration: none;
    display: block;
    color: inherit;
}
.meme-card:hover { border-color: #f59e0b; }

#chart-container {
    width: 100%;
    height: 400px;
    border: 1px solid #1e293b;
    border-radius: 8px;
    overflow: hidden;
    margin-bottom: 14px;
    background: #0b1220;
}

.spread-line {
    text-align: center;
    padding: 6px;
    color: #f59e0b;
    font-size: 13px;
    font-weight: 700;
    background: #0f172a;
    border-top: 1px solid #1e293b;
    border-bottom: 1px solid #1e293b;
}

.pie-legend-item {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 5px;
    font-size: 12px;
}
.pie-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }

.mining-bar-bg {
    background: #1e293b;
    border-radius: 4px;
    height: 8px;
    margin: 6px 0;
}
.mining-bar-fill {
    background: linear-gradient(to right, #f59e0b, #fbbf24);
    border-radius: 4px;
    height: 8px;
    transition: width 0.3s;
}

.price-big { font-size: 28px; font-weight: 700; color: #f59e0b; }
.price-change-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 13px;
    font-weight: 600;
    margin-left: 10px;
}

.tab-bar { display: flex; gap: 0; margin-bottom: 0; border-bottom: 1px solid #1e293b; }
.tab-btn {
    padding: 10px 18px;
    background: none;
    border: none;
    color: #94a3b8;
    cursor: pointer;
    font-family: inherit;
    font-size: 13px;
    border-bottom: 2px solid transparent;
}
.tab-btn.active { color: #f59e0b; border-bottom-color: #f59e0b; }
.tab-content { display: none; }
.tab-content.active { display: block; }

.depth-bar {
    position: absolute;
    right: 0; top: 0; bottom: 0;
    opacity: 0.12;
    border-radius: 2px;
}
.depth-cell { position: relative; }

input[type=range] { accent-color: #f59e0b; }
</style>
"""


# ==========================
# COUNTY MEME COIN LIST
# ==========================
@router.get("/county/{county_id}/memecoins", response_class=HTMLResponse)
async def county_memecoins(
    county_id: int,
    session_token: Optional[str] = Cookie(None),
    msg: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
):
    """List all meme coins for a county."""
    player = get_current_player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)

    from memecoins import get_all_meme_coins, MEME_CREATION_FEE_NATIVE
    from counties import get_county_by_id, is_player_in_county, CryptoWallet, get_db as county_get_db

    county = get_county_by_id(county_id)
    if not county:
        return HTMLResponse("<h1>County not found</h1>", status_code=404)

    memes = get_all_meme_coins(county_id)
    is_member = is_player_in_county(player.id, county_id)

    # Get player's native token balance
    county_db = county_get_db()
    native_wallet = county_db.query(CryptoWallet).filter(
        CryptoWallet.player_id == player.id,
        CryptoWallet.crypto_symbol == county.crypto_symbol,
    ).first()
    native_balance = native_wallet.balance if native_wallet else 0.0
    county_db.close()

    alert_html = ""
    if msg:
        alert_html = f'<div class="alert alert-success">{msg}</div>'
    if error:
        alert_html = f'<div class="alert alert-error">{error}</div>'

    can_launch = is_member and native_balance >= MEME_CREATION_FEE_NATIVE
    launch_btn = ""
    if is_member:
        if can_launch:
            launch_btn = f'<a href="/memecoins/launch?county_id={county_id}" class="btn btn-meme">+ Launch Meme Coin</a>'
        else:
            launch_btn = (
                f'<span style="color:#94a3b8;font-size:13px;">'
                f'Need {MEME_CREATION_FEE_NATIVE:.0f} {county.crypto_symbol} to launch '
                f'(you have {native_balance:.4f})</span>'
            )

    # Build meme coin cards
    if memes:
        cards_html = '<div class="grid grid-3">'
        for m in memes:
            logo = m["logo_svg"]
            logo_html = f'<span class="logo-cell">{logo}</span>' if logo else ""
            change = m["price_change_24h"]
            if change > 0:
                chg_html = f'<span class="positive">+{change:.2f}%</span>'
            elif change < 0:
                chg_html = f'<span class="negative">{change:.2f}%</span>'
            else:
                chg_html = '<span class="neutral">0.00%</span>'

            mining_pct = 0
            if m["mining_allocation"] > 0:
                mining_pct = min(100, m["mining_minted"] / m["mining_allocation"] * 100)

            cards_html += f'''
            <a href="/memecoins/{m["symbol"]}" class="meme-card">
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">
                    {logo_html}
                    <div>
                        <span class="badge badge-meme">{m["symbol"]}</span>
                        <span style="margin-left:6px;font-weight:600;">{m["name"]}</span>
                    </div>
                    <div style="margin-left:auto;">{chg_html}</div>
                </div>
                <div style="font-size:20px;font-weight:700;color:#f59e0b;margin-bottom:8px;">
                    {m["last_price"]:.6f} <span style="font-size:12px;color:#a78bfa;">{county.crypto_symbol}</span>
                </div>
                <div style="font-size:11px;color:#94a3b8;margin-bottom:8px;">{(m["description"] or "")[:80]}{"..." if len(m["description"] or "") > 80 else ""}</div>
                <div class="mining-bar-bg"><div class="mining-bar-fill" style="width:{mining_pct:.1f}%"></div></div>
                <div style="display:flex;justify-content:space-between;font-size:11px;color:#64748b;margin-top:4px;">
                    <span>Mining: {mining_pct:.1f}%</span>
                    <span>Holders: {m["holder_count"]}</span>
                    <span>Trades: {m["total_trades"]}</span>
                </div>
                <div style="font-size:11px;color:#475569;margin-top:6px;">by {m["creator_name"]}</div>
            </a>
            '''
        cards_html += '</div>'
    else:
        cards_html = '<div class="card" style="text-align:center;padding:40px;color:#475569;">No meme coins yet. Be the first to launch one!</div>'

    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>{county.name} Meme Coins</title>
    {MEME_STYLES}
</head>
<body>
<div class="container">
    <div class="header">
        <div>
            <h1>🚀 {county.name} Meme Coins</h1>
            <div style="font-size:12px;color:#64748b;margin-top:4px;">
                Layer-2 tokens on the <span class="native-color">{county.crypto_name} ({county.crypto_symbol})</span> blockchain
            </div>
        </div>
        <div style="display:flex;align-items:center;gap:12px;">
            {launch_btn}
            <a href="/county/{county_id}" class="nav-link">County</a>
            <a href="/exchange" class="nav-link">Exchange</a>
            <a href="/" class="nav-link">Dashboard</a>
        </div>
    </div>

    {alert_html}

    <div class="card" style="margin-bottom:14px;">
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;">
            <div>
                <span style="color:#94a3b8;font-size:13px;">{len(memes)} meme coin{"s" if len(memes) != 1 else ""} live on this chain</span>
            </div>
            <div style="font-size:13px;">
                Your <span class="native-color">{county.crypto_symbol}</span>:
                <strong class="native-color">{native_balance:.4f}</strong>
                &nbsp;|&nbsp; Creation fee: <strong class="meme-color">{MEME_CREATION_FEE_NATIVE:.0f} {county.crypto_symbol}</strong> (burned)
            </div>
        </div>
    </div>

    {cards_html}
</div>
</body>
</html>"""


# ==========================
# LAUNCH MEME COIN FORM
# ==========================
@router.get("/memecoins/launch", response_class=HTMLResponse)
async def launch_meme_form(
    county_id: int = Query(...),
    session_token: Optional[str] = Cookie(None),
    error: Optional[str] = Query(None),
):
    player = get_current_player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)

    from memecoins import MEME_CREATION_FEE_NATIVE, MEME_FOUNDER_ALLOCATION_PCT, MEME_MINING_ALLOCATION_PCT
    from counties import get_county_by_id, is_player_in_county, CryptoWallet, get_db as county_get_db

    county = get_county_by_id(county_id)
    if not county:
        return HTMLResponse("<h1>County not found</h1>", status_code=404)

    if not is_player_in_county(player.id, county_id):
        return HTMLResponse("<h1>You are not a member of this county.</h1>", status_code=403)

    county_db = county_get_db()
    native_wallet = county_db.query(CryptoWallet).filter(
        CryptoWallet.player_id == player.id,
        CryptoWallet.crypto_symbol == county.crypto_symbol,
    ).first()
    native_balance = native_wallet.balance if native_wallet else 0.0
    county_db.close()

    err_html = f'<div class="alert alert-error">{error}</div>' if error else ""

    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Launch Meme Coin</title>
    {MEME_STYLES}
</head>
<body>
<div class="container" style="max-width:700px;">
    <div class="header">
        <h1>🚀 Launch Meme Coin</h1>
        <div>
            <a href="/county/{county_id}/memecoins" class="nav-link">← Back</a>
            <a href="/" class="nav-link">Dashboard</a>
        </div>
    </div>

    {err_html}

    <div class="card">
        <h2>Create a Layer-2 Token on {county.name}</h2>
        <p style="font-size:13px;color:#94a3b8;margin-bottom:16px;">
            Your meme coin lives on the <span class="native-color">{county.crypto_name} ({county.crypto_symbol})</span> blockchain.
            All trading pairs are denominated in <span class="native-color">{county.crypto_symbol}</span>.
            Creation burns <strong class="meme-color">{MEME_CREATION_FEE_NATIVE:.0f} {county.crypto_symbol}</strong> forever.
        </p>

        <div class="card" style="background:#0f172a;margin-bottom:16px;">
            <div class="grid grid-3">
                <div style="text-align:center;">
                    <div style="font-size:22px;font-weight:700;color:#f59e0b;">{int(MEME_FOUNDER_ALLOCATION_PCT*100)}%</div>
                    <div style="font-size:11px;color:#94a3b8;">You receive immediately</div>
                </div>
                <div style="text-align:center;">
                    <div style="font-size:22px;font-weight:700;color:#a78bfa;">{int(MEME_MINING_ALLOCATION_PCT*100)}%</div>
                    <div style="font-size:11px;color:#94a3b8;">To mining pool (stakers earn)</div>
                </div>
                <div style="text-align:center;">
                    <div style="font-size:22px;font-weight:700;color:#f87171;">{MEME_CREATION_FEE_NATIVE:.0f}</div>
                    <div style="font-size:11px;color:#94a3b8;">{county.crypto_symbol} burned (creation fee)</div>
                </div>
            </div>
        </div>

        <form action="/api/memecoins/launch" method="post">
            <input type="hidden" name="county_id" value="{county_id}">

            <div class="grid grid-2">
                <div class="form-group">
                    <label>Token Name (max 40 chars)</label>
                    <input type="text" name="name" maxlength="40" placeholder="e.g., DogWifCoin" required>
                </div>
                <div class="form-group">
                    <label>Ticker Symbol (3-6 uppercase letters)</label>
                    <input type="text" name="symbol" maxlength="6" minlength="3"
                           pattern="[A-Za-z]{{3,6}}" placeholder="e.g., DWC" required
                           style="text-transform:uppercase;">
                </div>
            </div>

            <div class="form-group">
                <label>Description (optional)</label>
                <textarea name="description" placeholder="Describe your meme coin..."></textarea>
            </div>

            <div class="form-group">
                <label>Total Supply</label>
                <select name="total_supply" required>
                    <option value="1000000">1,000,000 (1 Million)</option>
                    <option value="10000000">10,000,000 (10 Million)</option>
                    <option value="100000000">100,000,000 (100 Million)</option>
                    <option value="1000000000" selected>1,000,000,000 (1 Billion) — Recommended</option>
                    <option value="100000000000">100,000,000,000 (100 Billion)</option>
                    <option value="1000000000000">1,000,000,000,000 (1 Trillion)</option>
                </select>
                <div style="font-size:11px;color:#64748b;margin-top:4px;">
                    You receive 10% immediately. 90% goes to the mining pool.
                </div>
            </div>

            <div style="background:#0f172a;border:1px solid #1e293b;border-radius:6px;padding:12px;margin-bottom:16px;font-size:13px;">
                <div style="color:#94a3b8;margin-bottom:6px;">Your {county.crypto_symbol} balance:
                    <strong class="{("native-color" if native_balance >= MEME_CREATION_FEE_NATIVE else "negative")}">{native_balance:.4f}</strong>
                </div>
                {"<div style='color:#4ade80;'>✓ Sufficient balance to launch</div>" if native_balance >= MEME_CREATION_FEE_NATIVE else f'<div style="color:#f87171;">✗ Need {MEME_CREATION_FEE_NATIVE:.0f} {county.crypto_symbol} to launch. Mine or buy more.</div>'}
            </div>

            <button type="submit" class="btn btn-meme"
                    {"" if native_balance >= MEME_CREATION_FEE_NATIVE else "disabled style='opacity:0.5;cursor:not-allowed;'"}>
                🚀 Launch Meme Coin (Burns {MEME_CREATION_FEE_NATIVE:.0f} {county.crypto_symbol})
            </button>
        </form>
    </div>

    <div class="card" style="font-size:12px;color:#64748b;">
        <strong style="color:#94a3b8;">How it works:</strong><br>
        1. Your coin launches on the {county.name} blockchain, trading against {county.crypto_symbol}.<br>
        2. You immediately receive <strong>{int(MEME_FOUNDER_ALLOCATION_PCT*100)}%</strong> of total supply as founder allocation.<br>
        3. The remaining <strong>{int(MEME_MINING_ALLOCATION_PCT*100)}%</strong> is distributed to miners who stake {county.crypto_symbol}.<br>
        4. Anyone can trade your coin on the order book. <strong>2% trading fee</strong>: 1% to you, 0.5% to county treasury, 0.5% burned.<br>
        5. You earn passive income every time someone trades your coin!
    </div>
</div>
</body>
</html>"""


# ==========================
# MEME COIN DETAIL / TRADING PAGE
# ==========================
@router.get("/memecoins/{symbol}", response_class=HTMLResponse)
async def meme_coin_page(
    symbol: str,
    session_token: Optional[str] = Cookie(None),
    msg: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    tab: Optional[str] = Query("chart"),
):
    player = get_current_player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)

    symbol = symbol.upper()
    from memecoins import (
        get_meme_coin_detail, get_meme_holders,
        get_player_meme_wallets, get_player_mining_deposits,
        get_player_open_orders, MEME_TRADE_FEE_TOTAL,
    )
    from counties import CryptoWallet, get_db as county_get_db

    detail = get_meme_coin_detail(symbol)
    if not detail:
        return HTMLResponse("<h1>Meme coin not found</h1>", status_code=404)

    holders = get_meme_holders(symbol)
    my_deposits = get_player_mining_deposits(player.id, symbol)
    my_orders = get_player_open_orders(player.id, symbol)

    # Player native token balance
    county_db = county_get_db()
    native_wallet = county_db.query(CryptoWallet).filter(
        CryptoWallet.player_id == player.id,
        CryptoWallet.crypto_symbol == detail["native_symbol"],
    ).first()
    native_balance = native_wallet.balance if native_wallet else 0.0
    county_db.close()

    # Player meme coin balance
    from memecoins import get_meme_wallet_balance
    meme_balance = get_meme_wallet_balance(player.id, symbol)

    alert_html = ""
    if msg:
        alert_html = f'<div class="alert alert-success">{msg}</div>'
    if error:
        alert_html = f'<div class="alert alert-error">{error}</div>'

    # Price change styling
    change = detail["price_change_24h"]
    if change > 0:
        chg_html = f'<span class="price-change-badge positive" style="background:#14532d;">+{change:.2f}%</span>'
    elif change < 0:
        chg_html = f'<span class="price-change-badge negative" style="background:#7f1d1d;">{change:.2f}%</span>'
    else:
        chg_html = '<span class="price-change-badge neutral" style="background:#1f2937;">0.00%</span>'

    # Mining progress
    mining_pct = 0.0
    if detail["mining_allocation"] > 0:
        mining_pct = min(100.0, detail["mining_minted"] / detail["mining_allocation"] * 100.0)

    # Order book HTML
    bids = detail["bids"]
    asks = detail["asks"]
    max_bid_qty = max((b["quantity"] for b in bids), default=1)
    max_ask_qty = max((a["quantity"] for a in asks), default=1)

    asks_html = ""
    for a in reversed(asks):  # Show asks top-down (highest first visually)
        depth_pct = min(100, a["quantity"] / max_ask_qty * 100)
        asks_html += f'''
        <div class="order-row ask-row depth-cell">
            <div class="depth-bar" style="width:{depth_pct:.0f}%;background:#dc2626;"></div>
            <span class="negative">{a["price"]:.6f}</span>
            <span style="color:#94a3b8;">{a["quantity"]:,.2f}</span>
            <span style="color:#64748b;">{a["price"]*a["quantity"]:.4f}</span>
        </div>'''

    bids_html = ""
    for b in bids:
        depth_pct = min(100, b["quantity"] / max_bid_qty * 100)
        bids_html += f'''
        <div class="order-row bid-row depth-cell">
            <div class="depth-bar" style="width:{depth_pct:.0f}%;background:#16a34a;"></div>
            <span class="positive">{b["price"]:.6f}</span>
            <span style="color:#94a3b8;">{b["quantity"]:,.2f}</span>
            <span style="color:#64748b;">{b["price"]*b["quantity"]:.4f}</span>
        </div>'''

    best_ask = asks[0]["price"] if asks else None
    best_bid = bids[0]["price"] if bids else None
    spread = ""
    if best_ask and best_bid:
        spread_val = best_ask - best_bid
        spread = f'<div class="spread-line">Spread: {spread_val:.6f} {detail["native_symbol"]}</div>'
    elif best_ask:
        spread = f'<div class="spread-line">Best Ask: {best_ask:.6f} {detail["native_symbol"]}</div>'
    elif best_bid:
        spread = f'<div class="spread-line">Best Bid: {best_bid:.6f} {detail["native_symbol"]}</div>'

    # Recent trades
    trades_html = ""
    for t in detail["recent_trades"]:
        is_buy = True  # Simplified (can't easily tell without player id)
        trades_html += f'''
        <tr>
            <td class="positive">{t["price"]:.6f}</td>
            <td>{t["quantity"]:,.2f}</td>
            <td>{t["native_volume"]:.4f}</td>
            <td style="color:#64748b;font-size:11px;">{t["executed_at"][:16].replace("T"," ")}</td>
        </tr>'''

    # My deposits HTML
    deposits_html = ""
    total_staked = sum(d["quantity"] for d in my_deposits)
    if my_deposits:
        for dep in my_deposits:
            pool_share = (dep["quantity"] / detail["mining_pool_native"] * 100) if detail["mining_pool_native"] > 0 else 0
            deposits_html += f'''
            <div style="background:#0f172a;border:1px solid #1e293b;border-radius:6px;padding:12px;margin-bottom:8px;">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div>
                        <span class="native-color">{dep["quantity"]:.6f} {dep["native_symbol"]}</span>
                        <span style="color:#64748b;font-size:11px;"> staked · {pool_share:.2f}% of pool</span>
                        <div style="font-size:11px;color:#4ade80;margin-top:2px;">Earned: {dep["total_earned"]:,.4f} {symbol}</div>
                    </div>
                    <form action="/api/memecoins/unstake" method="post" style="margin:0;">
                        <input type="hidden" name="deposit_id" value="{dep["id"]}">
                        <button type="submit" class="btn btn-cancel btn-sm">Unstake</button>
                    </form>
                </div>
            </div>'''
    else:
        deposits_html = '<p style="color:#475569;font-size:13px;">No active stakes.</p>'

    # My open orders HTML
    orders_html = ""
    if my_orders:
        for o in my_orders:
            badge_cls = "badge-buy" if o["order_type"] == "buy" else "badge-sell"
            status_cls = f"badge-{o['status']}"
            filled_pct = (o["quantity_filled"] / o["quantity"] * 100) if o["quantity"] > 0 else 0
            orders_html += f'''
            <div style="background:#0f172a;border:1px solid #1e293b;border-radius:6px;padding:10px;margin-bottom:6px;">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div>
                        <span class="badge {badge_cls}">{o["order_type"].upper()}</span>
                        <span class="badge {status_cls}" style="margin-left:4px;">{o["status"]}</span>
                        <span style="margin-left:8px;font-size:13px;">
                            {o["quantity"]:,.4f} @ {f'{o["price"]:.6f}' if o["price"] else "MARKET"}
                        </span>
                        <span style="color:#64748b;font-size:11px;"> ({filled_pct:.0f}% filled)</span>
                    </div>
                    <form action="/api/memecoins/cancel-order" method="post" style="margin:0;">
                        <input type="hidden" name="order_id" value="{o["id"]}">
                        <input type="hidden" name="meme_symbol" value="{symbol}">
                        <button type="submit" class="btn btn-cancel btn-sm">Cancel</button>
                    </form>
                </div>
            </div>'''
    else:
        orders_html = '<p style="color:#475569;font-size:13px;">No open orders.</p>'

    # Pie chart colors
    PIE_COLORS = [
        "#f59e0b", "#38bdf8", "#4ade80", "#a78bfa", "#f87171",
        "#fb923c", "#34d399", "#60a5fa", "#e879f9", "#fbbf24",
    ]
    total_holder_balance = sum(h["balance"] for h in holders)
    pie_legend_html = ""
    for i, h in enumerate(holders[:10]):
        color = PIE_COLORS[i % len(PIE_COLORS)]
        pct = (h["balance"] / total_holder_balance * 100) if total_holder_balance > 0 else 0
        pie_legend_html += f'''
        <div class="pie-legend-item">
            <div class="pie-dot" style="background:{color};"></div>
            <span style="color:#e5e7eb;">{h["name"]}</span>
            <span style="color:#64748b;margin-left:auto;">{pct:.1f}%</span>
        </div>'''

    holder_data_js = "[" + ",".join(
        f'{{"name":"{h["name"]}","balance":{h["balance"]}}}'
        for h in holders[:10]
    ) + "]"

    tab_chart = "active" if tab == "chart" else ""
    tab_trade = "active" if tab == "trade" else ""
    tab_mine  = "active" if tab == "mine" else ""

    price_placeholder = f"{detail['last_price']:.6f}" if detail["last_price"] else "0.000001"
    atl_display = f"{detail['all_time_low']:.6f}" if detail["all_time_low"] else "—"

    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>{detail["name"]} ({symbol})</title>
    {MEME_STYLES}
</head>
<body>
<div class="container">

    <!-- HEADER -->
    <div class="header">
        <div style="display:flex;align-items:center;gap:12px;">
            <span style="display:inline-block;width:36px;height:36px;">{detail["logo_svg"]}</span>
            <div>
                <h1 style="font-size:20px;">{detail["name"]}</h1>
                <div style="font-size:12px;color:#64748b;">
                    <span class="badge badge-meme">{symbol}</span>
                    <span style="margin-left:6px;">on <a href="/county/{detail["county_id"]}/memecoins" style="color:#a78bfa;text-decoration:none;">{detail["native_symbol"]}</a> chain</span>
                    <span style="margin-left:6px;">by {detail["creator_name"]}</span>
                </div>
            </div>
        </div>
        <div>
            <a href="/county/{detail["county_id"]}/memecoins" class="nav-link">← All Meme Coins</a>
            <a href="/exchange" class="nav-link">Exchange</a>
            <a href="/" class="nav-link">Dashboard</a>
        </div>
    </div>

    {alert_html}

    <!-- PRICE HERO -->
    <div class="card" style="margin-bottom:14px;">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px;">
            <div>
                <div class="price-big">{detail["last_price"]:.6f} <span style="font-size:14px;color:#a78bfa;">{detail["native_symbol"]}</span></div>
                {chg_html}
                <div style="font-size:12px;color:#64748b;margin-top:6px;">
                    24h H: <span class="positive">{detail["high_24h"]:.6f}</span>
                    &nbsp; L: <span class="negative">{detail["low_24h"]:.6f}</span>
                    &nbsp; Vol: <span class="native-color">{detail["volume_24h"]:.4f} {detail["native_symbol"]}</span>
                </div>
            </div>
            <div class="grid grid-4" style="font-size:12px;gap:16px;">
                <div style="text-align:right;">
                    <div style="color:#64748b;">Market Cap</div>
                    <div style="color:#f59e0b;font-weight:600;">{detail["market_cap_native"]:,.2f} {detail["native_symbol"]}</div>
                </div>
                <div style="text-align:right;">
                    <div style="color:#64748b;">Minted Supply</div>
                    <div>{detail["minted_supply"]:,.0f} / {detail["total_supply"]:,.0f}</div>
                </div>
                <div style="text-align:right;">
                    <div style="color:#64748b;">All-Time High</div>
                    <div class="positive">{detail["all_time_high"]:.6f}</div>
                </div>
                <div style="text-align:right;">
                    <div style="color:#64748b;">Holders</div>
                    <div>{detail["holder_count"]}</div>
                </div>
            </div>
        </div>
    </div>

    <!-- WALLET STATUS BAR -->
    <div class="card" style="padding:12px 18px;margin-bottom:14px;">
        <div style="display:flex;gap:24px;flex-wrap:wrap;font-size:13px;">
            <span>Your <span class="badge badge-meme">{symbol}</span>: <strong class="meme-color">{meme_balance:,.4f}</strong></span>
            <span>Your <span class="badge badge-native">{detail["native_symbol"]}</span>: <strong class="native-color">{native_balance:.4f}</strong></span>
            <span style="color:#64748b;">Total staked: <span class="native-color">{total_staked:.4f}</span></span>
        </div>
    </div>

    <!-- MAIN TABS -->
    <div class="tab-bar">
        <button class="tab-btn {tab_chart}" onclick="showTab('chart')">📈 Chart & Order Book</button>
        <button class="tab-btn {tab_trade}" onclick="showTab('trade')">⚡ Trade</button>
        <button class="tab-btn {tab_mine}"  onclick="showTab('mine')">⛏ Mine</button>
        <button class="tab-btn" onclick="showTab('info')">ℹ Info & Holders</button>
    </div>

    <!-- TAB: CHART & ORDER BOOK -->
    <div id="tab-chart" class="tab-content {tab_chart}" style="padding-top:14px;">
        <div class="grid grid-2" style="grid-template-columns:2fr 1fr;gap:14px;">
            <!-- Candlestick Chart -->
            <div>
                <div class="card" style="padding:10px;">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                        <h2 style="margin:0;">{symbol}/{detail["native_symbol"]} — 1H Candles</h2>
                        <div style="font-size:11px;color:#64748b;" id="ohlcv-display">Hover a candle to see OHLCV</div>
                    </div>
                    <div id="chart-container"></div>
                    <!-- Volume histogram rendered in the same chart via TradingView pane -->
                </div>

                <!-- Recent Trades -->
                <div class="card">
                    <h2>Recent Trades</h2>
                    <table class="table">
                        <thead><tr>
                            <th>Price ({detail["native_symbol"]})</th>
                            <th>Amount ({symbol})</th>
                            <th>Volume</th>
                            <th>Time</th>
                        </tr></thead>
                        <tbody>{trades_html if trades_html else '<tr><td colspan="4" style="color:#475569;text-align:center;">No trades yet</td></tr>'}</tbody>
                    </table>
                </div>
            </div>

            <!-- Order Book -->
            <div>
                <div class="card" style="padding:10px;">
                    <h2>Order Book</h2>
                    <div style="display:flex;justify-content:space-between;font-size:11px;color:#64748b;padding:4px 8px;margin-bottom:4px;">
                        <span>Price ({detail["native_symbol"]})</span>
                        <span>Size ({symbol})</span>
                        <span>Total</span>
                    </div>
                    <div class="order-book-side">
                        {asks_html if asks_html else '<div style="color:#475569;text-align:center;padding:12px;font-size:12px;">No sell orders</div>'}
                    </div>
                    {spread}
                    <div class="order-book-side">
                        {bids_html if bids_html else '<div style="color:#475569;text-align:center;padding:12px;font-size:12px;">No buy orders</div>'}
                    </div>
                </div>

                <div class="card" style="padding:10px;">
                    <h2>My Open Orders</h2>
                    {orders_html}
                </div>
            </div>
        </div>
    </div>

    <!-- TAB: TRADE -->
    <div id="tab-trade" class="tab-content {tab_trade}" style="padding-top:14px;">
        <div class="grid grid-2">
            <!-- BUY -->
            <div class="card">
                <h2 style="color:#4ade80;">Buy {symbol}</h2>
                <p style="font-size:12px;color:#94a3b8;margin-bottom:12px;">
                    Pay in <span class="native-color">{detail["native_symbol"]}</span>.
                    2% fee (1% to creator, 0.5% treasury, 0.5% burned).
                </p>
                <form action="/api/memecoins/{symbol}/order" method="post">
                    <input type="hidden" name="order_type" value="buy">
                    <div class="form-group">
                        <label>Order Mode</label>
                        <select name="order_mode" id="buy-mode" onchange="toggleBuyPrice()">
                            <option value="limit">Limit (set your price)</option>
                            <option value="market">Market (fill immediately)</option>
                        </select>
                    </div>
                    <div class="form-group" id="buy-price-group">
                        <label>Price ({detail["native_symbol"]} per {symbol})</label>
                        <input type="number" name="price" min="0.000001" step="0.000001"
                               placeholder="{price_placeholder}"
                               id="buy-price" oninput="calcBuyCost()">
                    </div>
                    <div class="form-group">
                        <label>Quantity ({symbol})</label>
                        <input type="number" name="quantity" min="1" step="1"
                               placeholder="Amount of {symbol} to buy"
                               id="buy-qty" oninput="calcBuyCost()">
                    </div>
                    <div id="buy-cost-display" style="font-size:12px;color:#94a3b8;margin-bottom:12px;"></div>
                    <div style="font-size:12px;color:#64748b;margin-bottom:10px;">
                        Available: <span class="native-color">{native_balance:.4f} {detail["native_symbol"]}</span>
                    </div>
                    <button type="submit" class="btn btn-buy">Buy {symbol}</button>
                </form>
            </div>

            <!-- SELL -->
            <div class="card">
                <h2 style="color:#f87171;">Sell {symbol}</h2>
                <p style="font-size:12px;color:#94a3b8;margin-bottom:12px;">
                    Receive <span class="native-color">{detail["native_symbol"]}</span>.
                    2% fee (1% to creator, 0.5% treasury, 0.5% burned).
                </p>
                <form action="/api/memecoins/{symbol}/order" method="post">
                    <input type="hidden" name="order_type" value="sell">
                    <div class="form-group">
                        <label>Order Mode</label>
                        <select name="order_mode" id="sell-mode" onchange="toggleSellPrice()">
                            <option value="limit">Limit (set your price)</option>
                            <option value="market">Market (fill immediately)</option>
                        </select>
                    </div>
                    <div class="form-group" id="sell-price-group">
                        <label>Price ({detail["native_symbol"]} per {symbol})</label>
                        <input type="number" name="price" min="0.000001" step="0.000001"
                               placeholder="{price_placeholder}"
                               id="sell-price" oninput="calcSellRevenue()">
                    </div>
                    <div class="form-group">
                        <label>Quantity ({symbol})</label>
                        <input type="number" name="quantity" min="1" step="1"
                               placeholder="Amount of {symbol} to sell"
                               id="sell-qty" oninput="calcSellRevenue()">
                    </div>
                    <div id="sell-revenue-display" style="font-size:12px;color:#94a3b8;margin-bottom:12px;"></div>
                    <div style="font-size:12px;color:#64748b;margin-bottom:10px;">
                        Available: <span class="meme-color">{meme_balance:,.4f} {symbol}</span>
                    </div>
                    <button type="submit" class="btn btn-sell">Sell {symbol}</button>
                </form>
            </div>
        </div>

        <div class="card">
            <h2>My Open Orders</h2>
            {orders_html}
        </div>
    </div>

    <!-- TAB: MINE -->
    <div id="tab-mine" class="tab-content {tab_mine}" style="padding-top:14px;">
        <div class="grid grid-2">
            <div class="card">
                <h2>Mining Pool</h2>
                <div class="stat"><span class="stat-label">Pool Status</span>
                    <span class="{"positive" if detail["mining_enabled"] else "negative"}">{"Active" if detail["mining_enabled"] else "Completed"}</span>
                </div>
                <div class="stat"><span class="stat-label">Total Staked</span>
                    <span class="stat-value native-color">{detail["mining_pool_native"]:,.4f} {detail["native_symbol"]}</span>
                </div>
                <div class="stat"><span class="stat-label">Block Reward</span>
                    <span class="stat-value meme-color">{detail["block_reward"]:.4f} {symbol} per {detail["native_symbol"]} staked/hr</span>
                </div>
                <div class="stat"><span class="stat-label">Mining Progress</span>
                    <span class="stat-value">{mining_pct:.2f}%</span>
                </div>
                <div class="mining-bar-bg" style="margin:10px 0;">
                    <div class="mining-bar-fill" style="width:{mining_pct:.1f}%;"></div>
                </div>
                <div style="font-size:11px;color:#64748b;">
                    {detail["mining_minted"]:,.2f} / {detail["mining_allocation"]:,.2f} {symbol} mined
                </div>

                {"" if not detail["mining_enabled"] else f'''
                <hr style="border-color:#1e293b;margin:14px 0;">
                <h3>Stake {detail["native_symbol"]} to Mine</h3>
                <p style="font-size:12px;color:#94a3b8;margin-bottom:10px;">
                    Lock {detail["native_symbol"]} into this mining pool.
                    Earn {symbol} every hour proportional to your share.
                    Unstake any time to get your {detail["native_symbol"]} back.
                </p>
                <form action="/api/memecoins/{symbol}/stake" method="post">
                    <div class="form-group">
                        <label>Amount ({detail["native_symbol"]} to stake)</label>
                        <input type="number" name="native_amount" min="0.000001" step="0.000001"
                               max="{native_balance}" placeholder="e.g., 1.0">
                    </div>
                    <div style="font-size:12px;color:#64748b;margin-bottom:10px;">
                        Available: <span class="native-color">{native_balance:.4f} {detail["native_symbol"]}</span>
                    </div>
                    <button type="submit" class="btn btn-meme">⛏ Stake & Mine</button>
                </form>
                '''}
            </div>

            <div class="card">
                <h2>My Active Stakes</h2>
                {deposits_html}
                {'<div style="font-size:12px;color:#64748b;margin-top:10px;">Your current pool share: <strong class="native-color">' + f'{(total_staked / detail["mining_pool_native"] * 100):.2f}%</strong>' if detail["mining_pool_native"] > 0 and total_staked > 0 else ''}
            </div>
        </div>
    </div>

    <!-- TAB: INFO & HOLDERS -->
    <div id="tab-info" class="tab-content" style="padding-top:14px;">
        <div class="grid grid-2">
            <!-- Token Info -->
            <div class="card">
                <h2>Token Info</h2>
                <div class="stat"><span class="stat-label">Name</span><span class="stat-value">{detail["name"]}</span></div>
                <div class="stat"><span class="stat-label">Symbol</span><span class="stat-value"><span class="badge badge-meme">{symbol}</span></span></div>
                <div class="stat"><span class="stat-label">Chain</span><span class="stat-value native-color">{detail["native_symbol"]}</span></div>
                <div class="stat"><span class="stat-label">Creator</span><span class="stat-value">{detail["creator_name"]}</span></div>
                <div class="stat"><span class="stat-label">Total Supply</span><span class="stat-value">{detail["total_supply"]:,.0f}</span></div>
                <div class="stat"><span class="stat-label">Minted Supply</span><span class="stat-value">{detail["minted_supply"]:,.2f}</span></div>
                <div class="stat"><span class="stat-label">Creation Fee Burned</span><span class="stat-value negative">{detail["creation_fee_burned"]:.2f} {detail["native_symbol"]}</span></div>
                <div class="stat"><span class="stat-label">All-Time High</span><span class="stat-value positive">{detail["all_time_high"]:.6f}</span></div>
                <div class="stat"><span class="stat-label">All-Time Low</span><span class="stat-value negative">{atl_display}</span></div>
                <div class="stat"><span class="stat-label">Total Trades</span><span class="stat-value">{detail["total_trades"]}</span></div>
                <div class="stat"><span class="stat-label">Total Volume</span><span class="stat-value native-color">{detail["total_volume_native"]:,.4f} {detail["native_symbol"]}</span></div>
                <div class="stat"><span class="stat-label">Launched</span><span class="stat-value">{str(detail["created_at"])[:10]}</span></div>
                {"" if not detail["description"] else f'<div style="margin-top:10px;font-size:13px;color:#94a3b8;">{detail["description"]}</div>'}
            </div>

            <!-- Pie Chart -->
            <div class="card">
                <h2>Holder Distribution</h2>
                <div style="display:flex;gap:20px;align-items:flex-start;">
                    <div>
                        <svg id="pie-chart" viewBox="0 0 200 200" width="180" height="180"></svg>
                    </div>
                    <div style="flex:1;">
                        {pie_legend_html if pie_legend_html else '<p style="color:#475569;font-size:12px;">No holders yet</p>'}
                    </div>
                </div>
            </div>
        </div>
    </div>

</div>

<!-- TradingView Lightweight Charts -->
<script src="https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>

<script>
// ==========================
// TAB SWITCHING
// ==========================
function showTab(name) {{
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
    document.getElementById('tab-' + name).classList.add('active');
    event.target.classList.add('active');
    if (name === 'chart') initChart();
    if (name === 'info') drawPie();
}}

// ==========================
// CANDLESTICK CHART
// ==========================
let chartInitialized = false;
async function initChart() {{
    if (chartInitialized) return;
    chartInitialized = true;

    const container = document.getElementById('chart-container');
    const chart = LightweightCharts.createChart(container, {{
        width: container.clientWidth,
        height: 380,
        layout: {{
            background: {{ type: 'solid', color: '#0b1220' }},
            textColor: '#94a3b8',
        }},
        grid: {{
            vertLines: {{ color: '#1e293b' }},
            horzLines: {{ color: '#1e293b' }},
        }},
        crosshair: {{ mode: LightweightCharts.CrosshairMode.Normal }},
        rightPriceScale: {{
            borderColor: '#1e293b',
            scaleMargins: {{ top: 0.1, bottom: 0.3 }},
        }},
        timeScale: {{ borderColor: '#1e293b', timeVisible: true }},
    }});

    const candleSeries = chart.addCandlestickSeries({{
        upColor: '#4ade80',
        downColor: '#f87171',
        borderVisible: false,
        wickUpColor: '#4ade80',
        wickDownColor: '#f87171',
    }});

    const volumeSeries = chart.addHistogramSeries({{
        color: '#f59e0b',
        priceFormat: {{ type: 'volume' }},
        priceScaleId: 'volume',
        scaleMargins: {{ top: 0.8, bottom: 0 }},
    }});

    chart.priceScale('volume').applyOptions({{
        scaleMargins: {{ top: 0.8, bottom: 0 }},
    }});

    // Fetch OHLCV data
    try {{
        const res = await fetch('/api/memecoins/{symbol}/candles');
        const candles = await res.json();
        if (candles.length === 0) {{
            container.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:380px;color:#475569;font-size:14px;">No trade history yet. Be the first to trade!</div>';
            return;
        }}
        candleSeries.setData(candles);
        volumeSeries.setData(candles.map(c => ({{
            time: c.time,
            value: c.volume,
            color: c.close >= c.open ? 'rgba(74,222,128,0.4)' : 'rgba(248,113,113,0.4)',
        }})));
        chart.timeScale().fitContent();
    }} catch(e) {{
        container.innerHTML = '<div style="color:#f87171;padding:20px;">Failed to load chart data.</div>';
    }}

    // Show OHLCV on crosshair move
    chart.subscribeCrosshairMove(param => {{
        if (!param.time) return;
        const data = param.seriesData.get(candleSeries);
        if (!data) return;
        document.getElementById('ohlcv-display').innerHTML =
            `O:<span style="color:#e5e7eb">${{data.open.toFixed(6)}}</span> ` +
            `H:<span style="color:#4ade80">${{data.high.toFixed(6)}}</span> ` +
            `L:<span style="color:#f87171">${{data.low.toFixed(6)}}</span> ` +
            `C:<span style="color:#f59e0b">${{data.close.toFixed(6)}}</span>`;
    }});

    // Responsive resize
    window.addEventListener('resize', () => {{
        chart.applyOptions({{ width: container.clientWidth }});
    }});
}}

// Init chart if chart tab is default active
if (document.getElementById('tab-chart').classList.contains('active')) {{
    initChart();
}}

// ==========================
// PIE CHART (SVG)
// ==========================
const PIE_COLORS = [
    "#f59e0b","#38bdf8","#4ade80","#a78bfa","#f87171",
    "#fb923c","#34d399","#60a5fa","#e879f9","#fbbf24"
];

function drawPie() {{
    const holders = {holder_data_js};
    const svg = document.getElementById('pie-chart');
    if (!svg || holders.length === 0) return;

    const total = holders.reduce((s, h) => s + h.balance, 0);
    if (total === 0) return;

    let startAngle = -Math.PI / 2;
    let paths = '';
    const cx = 100, cy = 100, r = 85;

    holders.forEach((h, i) => {{
        const slice = (h.balance / total) * 2 * Math.PI;
        const endAngle = startAngle + slice;
        const x1 = cx + r * Math.cos(startAngle);
        const y1 = cy + r * Math.sin(startAngle);
        const x2 = cx + r * Math.cos(endAngle);
        const y2 = cy + r * Math.sin(endAngle);
        const largeArc = slice > Math.PI ? 1 : 0;
        const color = PIE_COLORS[i % PIE_COLORS.length];
        paths += `<path d="M ${{cx}} ${{cy}} L ${{x1.toFixed(2)}} ${{y1.toFixed(2)}} A ${{r}} ${{r}} 0 ${{largeArc}} 1 ${{x2.toFixed(2)}} ${{y2.toFixed(2)}} Z"
                    fill="${{color}}" stroke="#020617" stroke-width="1.5">
                    <title>${{h.name}}: ${{(h.balance/total*100).toFixed(2)}}%</title>
                  </path>`;
        startAngle = endAngle;
    }});

    // Donut hole
    paths += `<circle cx="${{cx}}" cy="${{cy}}" r="40" fill="#0b1220"/>`;
    paths += `<text x="${{cx}}" y="${{cy}}" text-anchor="middle" dy="5" font-size="11" fill="#94a3b8">${{holders.length}} holders</text>`;

    svg.innerHTML = paths;
}}

if (document.getElementById('tab-info') && document.getElementById('tab-info').classList.contains('active')) {{
    drawPie();
}}

// ==========================
// TRADE FORM CALCULATORS
// ==========================
function toggleBuyPrice() {{
    const mode = document.getElementById('buy-mode').value;
    document.getElementById('buy-price-group').style.display = mode === 'limit' ? '' : 'none';
}}
function toggleSellPrice() {{
    const mode = document.getElementById('sell-mode').value;
    document.getElementById('sell-price-group').style.display = mode === 'limit' ? '' : 'none';
}}

function calcBuyCost() {{
    const price = parseFloat(document.getElementById('buy-price').value) || 0;
    const qty = parseFloat(document.getElementById('buy-qty').value) || 0;
    const cost = price * qty;
    const fee = cost * {MEME_TRADE_FEE_TOTAL};
    const total = cost + fee;
    document.getElementById('buy-cost-display').innerHTML = cost > 0
        ? `Cost: <span style="color:#a78bfa">${{cost.toFixed(6)}} {detail["native_symbol"]}</span>
           + Fee: <span style="color:#f59e0b">${{fee.toFixed(6)}}</span>
           = Total: <strong style="color:#e5e7eb">${{total.toFixed(6)}}</strong>`
        : '';
}}

function calcSellRevenue() {{
    const price = parseFloat(document.getElementById('sell-price').value) || 0;
    const qty = parseFloat(document.getElementById('sell-qty').value) || 0;
    const gross = price * qty;
    const fee = gross * {MEME_TRADE_FEE_TOTAL};
    const net = gross - fee;
    document.getElementById('sell-revenue-display').innerHTML = gross > 0
        ? `Gross: <span style="color:#a78bfa">${{gross.toFixed(6)}} {detail["native_symbol"]}</span>
           - Fee: <span style="color:#f59e0b">${{fee.toFixed(6)}}</span>
           = Net: <strong style="color:#4ade80">${{net.toFixed(6)}}</strong>`
        : '';
}}
</script>
</body>
</html>"""


# ==========================
# API: CANDLE DATA (JSON)
# ==========================
@router.get("/api/memecoins/{symbol}/candles")
async def api_meme_candles(symbol: str, limit: int = Query(168)):
    from memecoins import get_meme_candles
    candles = get_meme_candles(symbol.upper(), limit=min(limit, 500))
    return JSONResponse(content=candles)


@router.get("/api/memecoins/{symbol}/holders")
async def api_meme_holders(symbol: str):
    from memecoins import get_meme_holders
    holders = get_meme_holders(symbol.upper())
    return JSONResponse(content=holders)


# ==========================
# API: LAUNCH MEME COIN
# ==========================
@router.post("/api/memecoins/launch")
async def api_launch_meme(
    county_id: int = Form(...),
    name: str = Form(...),
    symbol: str = Form(...),
    description: str = Form(""),
    total_supply: float = Form(...),
    session_token: Optional[str] = Cookie(None),
):
    player = get_current_player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)

    from memecoins import launch_meme_coin
    meme_symbol, message = launch_meme_coin(
        player_id=player.id,
        name=name,
        symbol=symbol.upper(),
        description=description,
        total_supply=total_supply,
        county_id=county_id,
    )
    if meme_symbol:
        return RedirectResponse(
            url=f"/memecoins/{meme_symbol}?msg={message.replace(' ', '+')}",
            status_code=303,
        )
    else:
        return RedirectResponse(
            url=f"/memecoins/launch?county_id={county_id}&error={message.replace(' ', '+')}",
            status_code=303,
        )


# ==========================
# API: STAKE (MINE)
# ==========================
@router.post("/api/memecoins/{symbol}/stake")
async def api_meme_stake(
    symbol: str,
    native_amount: float = Form(...),
    session_token: Optional[str] = Cookie(None),
):
    player = get_current_player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)

    from memecoins import stake_native_for_mining
    success, message = stake_native_for_mining(
        player_id=player.id,
        meme_symbol=symbol.upper(),
        native_amount=native_amount,
    )
    sym = symbol.upper()
    if success:
        return RedirectResponse(url=f"/memecoins/{sym}?tab=mine&msg={message.replace(' ', '+')}", status_code=303)
    else:
        return RedirectResponse(url=f"/memecoins/{sym}?tab=mine&error={message.replace(' ', '+')}", status_code=303)


# ==========================
# API: UNSTAKE
# ==========================
@router.post("/api/memecoins/unstake")
async def api_meme_unstake(
    deposit_id: int = Form(...),
    session_token: Optional[str] = Cookie(None),
):
    player = get_current_player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)

    from memecoins import unstake_native, MemeCoinMiningDeposit, get_db
    db = get_db()
    dep = db.query(MemeCoinMiningDeposit).filter(MemeCoinMiningDeposit.id == deposit_id).first()
    sym = dep.meme_symbol if dep else "unknown"
    db.close()

    success, message = unstake_native(player_id=player.id, deposit_id=deposit_id)
    if success:
        return RedirectResponse(url=f"/memecoins/{sym}?tab=mine&msg={message.replace(' ', '+')}", status_code=303)
    else:
        return RedirectResponse(url=f"/memecoins/{sym}?tab=mine&error={message.replace(' ', '+')}", status_code=303)


# ==========================
# API: PLACE ORDER
# ==========================
@router.post("/api/memecoins/{symbol}/order")
async def api_meme_order(
    symbol: str,
    order_type: str = Form(...),
    order_mode: str = Form(...),
    quantity: float = Form(...),
    price: Optional[float] = Form(None),
    session_token: Optional[str] = Cookie(None),
):
    player = get_current_player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)

    from memecoins import place_order
    sym = symbol.upper()
    order, message = place_order(
        player_id=player.id,
        meme_symbol=sym,
        order_type=order_type,
        order_mode=order_mode,
        quantity=quantity,
        price=price if order_mode == "limit" else None,
    )
    if order:
        return RedirectResponse(url=f"/memecoins/{sym}?tab=trade&msg={message.replace(' ', '+')}", status_code=303)
    else:
        return RedirectResponse(url=f"/memecoins/{sym}?tab=trade&error={message.replace(' ', '+')}", status_code=303)


# ==========================
# API: CANCEL ORDER
# ==========================
@router.post("/api/memecoins/cancel-order")
async def api_cancel_order(
    order_id: int = Form(...),
    meme_symbol: str = Form(...),
    session_token: Optional[str] = Cookie(None),
):
    player = get_current_player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)

    from memecoins import cancel_order
    success, message = cancel_order(player_id=player.id, order_id=order_id)
    sym = meme_symbol.upper()
    if success:
        return RedirectResponse(url=f"/memecoins/{sym}?tab=trade&msg={message.replace(' ', '+')}", status_code=303)
    else:
        return RedirectResponse(url=f"/memecoins/{sym}?tab=trade&error={message.replace(' ', '+')}", status_code=303)


# ==========================
# PUBLIC API
# ==========================
__all__ = ['router']
