"""
crypto_hub_ux.py — Unified Crypto Hub  (/crypto)

Trust Wallet meets Uniswap: ONE page for the entire crypto experience.

  • Wallet tab   — Trust Wallet-style portfolio: total value header, asset
                   rows (native L1 tokens, WSC, meme coins) with live prices.
  • Swap tab     — Uniswap-style swap card. One card routes every swap type:
                   Cash ↔ Native, Native ↔ Native, Native ↔ WSC, WSC → Cash.
  • Earn tab     — Mining nodes, meme mining stakes, WSC yield farming, faucet.
  • Activity tab — The player's crypto transaction ledger (category="crypto").

Deep-dive pages (/exchange, /token/X, /memecoins/X, governance, gas tracker)
remain available and are linked from the hub — the hub is the front door.

DESIGN NOTE — INTENTIONAL TAX HAVEN: crypto is invisible to the government.
No taxes, no government fee routing, ever. The hub shows this as a feature.
"""

import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Cookie, Query
from fastapi.responses import HTMLResponse, RedirectResponse

from ux import _nav_loader_html as _nav_loader
from skin_utils import skin_links as _skin_links

router = APIRouter()


def get_current_player(session_token: Optional[str]):
    from auth import get_player_from_session, get_db
    db = get_db()
    player = get_player_from_session(db, session_token)
    db.close()
    return player


# ─────────────────────────────────────────────────────────────────────────────
# STYLES — Trust Wallet (wallet/asset rows) + Uniswap (swap card)
# ─────────────────────────────────────────────────────────────────────────────

HUB_STYLES = """
<style>
:root {
  /* Bridged to the skin system — skin vars win, TW/Uniswap palette is the fallback.
     NB: --accent is NOT redefined here; the player's skin (+ modules/crypto.css) owns it. */
  --bg: var(--bg-page, #05060f); --panel: var(--bg-card, #0c0e1d);
  --panel2: var(--bg-card-2, #12152b); --line: var(--border, #1c2040);
  --txt: var(--text-primary, #e6e8f5); --mut: var(--text-muted, #707694);
  --grad: var(--grad-bar, linear-gradient(120deg,#f97316,#a855f7));
  --green: var(--color-success, #22c55e); --red: var(--color-danger, #ef4444);
  --accent2: var(--accent-2, #f97316);
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: var(--bg); color: var(--txt);
       font-family: 'Inter','Segoe UI',system-ui,sans-serif; min-height: 100vh; }
a { color: var(--color-sky,#38bdf8); text-decoration: none; }
.hub-wrap { max-width: 760px; margin: 0 auto; padding: 16px 14px 90px; }

/* ── Header ───────────────────────────────────────────── */
.hub-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.hub-title { font-size: 1.05rem; font-weight: 800; letter-spacing: .02em; }
.hub-title .grad { background: var(--grad); -webkit-background-clip: text; background-clip: text; color: transparent; }
.hub-links { display: flex; gap: 10px; font-size: .72rem; }
.hub-links a { color: var(--mut); }
.hub-links a:hover { color: var(--txt); }

/* ── Total balance (Trust Wallet style) ───────────────── */
.tw-balance { text-align: center; padding: 18px 0 6px; }
.tw-balance .lbl { font-size: .7rem; color: var(--mut); text-transform: uppercase; letter-spacing: .14em; }
.tw-balance .val { font-size: clamp(1.3rem, 7vw, 2.3rem); font-weight: 800; margin-top: 4px; letter-spacing: -.02em; overflow-wrap: anywhere; }
.tw-balance .sub { font-size: .75rem; color: var(--mut); margin-top: 4px; }
.tax-badge { display: inline-flex; align-items: center; gap: 5px; margin-top: 10px;
  background: #052e16; border: 1px solid #14532d; color: #4ade80;
  font-size: .65rem; font-weight: 700; padding: 4px 12px; border-radius: 999px; letter-spacing: .05em; }

/* ── Action row (Trust Wallet pill buttons) ───────────── */
.tw-actions { display: flex; justify-content: center; gap: 22px; margin: 18px 0 6px; }
.tw-act { display: flex; flex-direction: column; align-items: center; gap: 6px;
  background: none; border: none; cursor: pointer; color: var(--mut); font-size: .68rem; }
.tw-act .ico { width: 46px; height: 46px; border-radius: 50%; display: flex; align-items: center;
  justify-content: center; font-size: 1.15rem; background: var(--panel2); border: 1px solid var(--line);
  transition: all .15s; }
.tw-act:hover .ico, .tw-act.active .ico { background: var(--grad); border-color: transparent; color: #fff; }
.tw-act:hover, .tw-act.active { color: var(--txt); }

/* ── Tabs ─────────────────────────────────────────────── */
.hub-tab { display: none; }
.hub-tab.show { display: block; animation: fadein .18s ease; }
@keyframes fadein { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; } }

/* ── Asset rows (Trust Wallet list) ───────────────────── */
.sec-lbl { font-size: .68rem; color: var(--mut); text-transform: uppercase;
  letter-spacing: .12em; margin: 18px 4px 8px; font-weight: 700; }
.asset { display: flex; align-items: center; gap: 12px; padding: 12px 14px;
  background: var(--panel); border: 1px solid var(--line); border-radius: 16px; margin-bottom: 8px;
  transition: background .12s; }
.asset:hover { background: var(--panel2); }
.coin-ico { width: 40px; height: 40px; border-radius: 50%; flex-shrink: 0; display: flex;
  align-items: center; justify-content: center; font-weight: 800; font-size: .72rem; color: #fff; }
.asset .meta { flex: 1; min-width: 0; }
.asset .nm { font-weight: 700; font-size: .88rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.asset .px { font-size: .7rem; color: var(--mut); margin-top: 2px; }
.asset .rhs { text-align: right; flex-shrink: 0; }
.asset .bal { font-weight: 700; font-size: .88rem; }
.asset .usd { font-size: .7rem; color: var(--mut); margin-top: 2px; }
.chg { font-size: .68rem; font-weight: 700; }
.chg.up { color: var(--green); } .chg.dn { color: var(--red); }

/* ── Uniswap swap card ────────────────────────────────── */
.uni-card { background: var(--panel); border: 1px solid var(--line); border-radius: 24px;
  padding: 14px; max-width: 480px; margin: 14px auto 0; }
.uni-panel { background: var(--panel2); border: 1px solid transparent; border-radius: 18px;
  padding: 14px 16px; transition: border-color .15s; }
.uni-panel:focus-within { border-color: #2d3460; }
.uni-panel .plbl { font-size: .7rem; color: var(--mut); margin-bottom: 8px; }
.uni-row { display: flex; align-items: center; gap: 10px; }
.uni-amt { flex: 1; min-width: 0; background: none; border: none; outline: none; color: var(--txt);
  font-size: 1.7rem; font-weight: 600; width: 100%; font-family: inherit; }
.uni-amt::placeholder { color: #3a4060; }
.uni-tok { display: flex; align-items: center; gap: 7px; background: var(--panel);
  border: 1px solid var(--line); border-radius: 999px; padding: 6px 12px 6px 7px;
  font-weight: 700; font-size: .85rem; cursor: pointer; color: var(--txt); flex-shrink: 0; }
.uni-tok:hover { background: #181c38; }
.uni-tok .ti { width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center;
  justify-content: center; font-size: .5rem; font-weight: 800; color: #fff; }
.uni-sub { display: flex; justify-content: space-between; font-size: .68rem; color: var(--mut); margin-top: 8px; }
.uni-sub .mx { cursor: pointer; color: var(--accent); font-weight: 700; }
.uni-flip { display: flex; justify-content: center; margin: -9px 0; position: relative; z-index: 2; }
.uni-flip button { width: 38px; height: 38px; border-radius: 12px; background: var(--panel2);
  border: 4px solid var(--panel); color: var(--txt); font-size: 1rem; cursor: pointer; transition: transform .2s; }
.uni-flip button:hover { transform: rotate(180deg); }
.uni-info { font-size: .7rem; color: var(--mut); padding: 10px 6px 2px; display: flex;
  flex-direction: column; gap: 4px; }
.uni-info .irow { display: flex; justify-content: space-between; }
.uni-info .iv { color: var(--txt); }
.uni-btn { width: 100%; margin-top: 12px; padding: 15px; border: none; border-radius: 18px;
  background: var(--grad); color: #fff; font-size: 1rem; font-weight: 800; cursor: pointer;
  font-family: inherit; transition: opacity .15s; }
.uni-btn:disabled { opacity: .45; cursor: not-allowed; }
.tok-menu { position: absolute; background: var(--panel); border: 1px solid var(--line);
  border-radius: 16px; padding: 6px; z-index: 50; max-height: 290px; overflow-y: auto;
  width: 230px; box-shadow: 0 12px 40px rgba(0,0,0,.6); }
.tok-menu .tm-it { display: flex; align-items: center; gap: 9px; padding: 9px 10px;
  border-radius: 10px; cursor: pointer; font-size: .82rem; font-weight: 600; }
.tok-menu .tm-it:hover { background: var(--panel2); }
.tok-menu .tm-bal { margin-left: auto; font-size: .68rem; color: var(--mut); }

/* ── Earn cards ───────────────────────────────────────── */
.earn-card { background: var(--panel); border: 1px solid var(--line); border-radius: 16px;
  padding: 14px 16px; margin-bottom: 10px; }
.earn-card h4 { font-size: .85rem; margin-bottom: 8px; display: flex; align-items: center; gap: 8px; }
.earn-card .row { display: flex; justify-content: space-between; font-size: .76rem;
  color: var(--mut); padding: 3px 0; }
.earn-card .row b { color: var(--txt); }
.pill-btn { display: inline-block; background: var(--grad); color: #fff; border: none;
  padding: 8px 18px; border-radius: 999px; font-weight: 700; font-size: .76rem; cursor: pointer;
  font-family: inherit; }
.pill-lnk { display: inline-block; background: var(--panel2); border: 1px solid var(--line);
  color: var(--txt); padding: 8px 18px; border-radius: 999px; font-weight: 700; font-size: .76rem; }

/* ── Activity rows ────────────────────────────────────── */
.act-row { display: flex; align-items: center; gap: 12px; padding: 11px 14px;
  background: var(--panel); border: 1px solid var(--line); border-radius: 14px; margin-bottom: 7px; }
.act-ico { width: 34px; height: 34px; border-radius: 50%; background: var(--panel2);
  display: flex; align-items: center; justify-content: center; font-size: .95rem; flex-shrink: 0; }
.act-row .am { flex: 1; min-width: 0; }
.act-row .desc { font-size: .78rem; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.act-row .when { font-size: .65rem; color: var(--mut); margin-top: 2px; }
.act-row .amt { font-weight: 700; font-size: .8rem; flex-shrink: 0; }

/* ── Toast ────────────────────────────────────────────── */
#cb-toast { position: fixed; bottom: 26px; left: 50%; transform: translateX(-50%);
  padding: 13px 24px; border-radius: 14px; font-size: .88rem; font-weight: 700; z-index: 9999;
  max-width: 92vw; text-align: center; box-shadow: 0 6px 24px rgba(0,0,0,.5);
  transition: opacity .3s; opacity: 0; pointer-events: none; }

.empty { color: var(--mut); font-size: .8rem; text-align: center; padding: 26px 0; }
@media (max-width: 520px) {
  .tw-balance .val { font-size: 1.9rem; }
  .tw-actions { gap: 14px; }
  .uni-amt { font-size: 1.35rem; }
}
</style>
"""

_ICON_PALETTES = [
    ("#f97316", "#fb923c"), ("#a855f7", "#c084fc"), ("#38bdf8", "#7dd3fc"),
    ("#22c55e", "#4ade80"), ("#ef4444", "#f87171"), ("#eab308", "#fde047"),
    ("#ec4899", "#f9a8d4"), ("#14b8a6", "#5eead4"),
]


def _coin_icon(symbol: str, size: int = 40) -> str:
    """Deterministic gradient circle icon for a token symbol (Trust Wallet style)."""
    c1, c2 = _ICON_PALETTES[sum(ord(ch) for ch in symbol) % len(_ICON_PALETTES)]
    fs = ".72rem" if size >= 36 else ".5rem"
    return (f'<div class="coin-ico" style="width:{size}px;height:{size}px;font-size:{fs};'
            f'background:linear-gradient(135deg,{c1},{c2});">{symbol[:4]}</div>')


def _fmt_ago(ts: datetime) -> str:
    secs = max(0, int((datetime.utcnow() - ts).total_seconds()))
    if secs < 60: return f"{secs}s ago"
    if secs < 3600: return f"{secs // 60}m ago"
    if secs < 86400: return f"{secs // 3600}h ago"
    return f"{secs // 86400}d ago"


# ─────────────────────────────────────────────────────────────────────────────
# THE HUB
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/crypto", response_class=HTMLResponse)
def crypto_hub(session_token: Optional[str] = Cookie(None), tab: str = Query("wallet")):
    player = get_current_player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)

    from reserve_banks import get_player_display_currency, fmt_usd, get_usd_balance
    from counties import get_all_counties, get_player_county, EXCHANGE_FEE_PERCENT
    from memecoins import get_wallet_portfolio
    from wallet import (
        get_wsc_wallet_info, get_player_yield_deposits, get_faucet_status,
        WSC_SYMBOL, WSC_NAME,
    )

    disp        = get_player_display_currency(player.id)
    counties    = get_all_counties()
    portfolio   = get_wallet_portfolio(player.id)
    wsc_info    = get_wsc_wallet_info(player.id)
    my_county   = get_player_county(player.id)
    cash_bal    = get_usd_balance(player.id)

    county_by_sym = {c["crypto_symbol"]: c for c in counties}

    # Executive crypto bonus → effective exchange fee shown on the swap card.
    exec_bonus = 0.0
    try:
        from executive import get_player_job_bonus, get_db as _edb_fn
        _edb = _edb_fn()
        exec_bonus = get_player_job_bonus(_edb, player.id, "crypto") or 0.0
        _edb.close()
    except Exception:
        pass
    eff_fee_pct = EXCHANGE_FEE_PERCENT * (1.0 - exec_bonus) * 100

    # ── Portfolio totals (USD) ───────────────────────────────────────────
    native_rows, total_usd = "", 0.0
    for h in portfolio["native_holdings"]:
        c = county_by_sym.get(h["symbol"])
        price = c["crypto_price"] if c else 0.0
        chg   = c.get("price_change_24h", 0.0) if c else 0.0
        usd   = h["balance"] * price
        total_usd += usd
        chg_cls = "up" if chg >= 0 else "dn"
        chg_txt = f"{'▲' if chg >= 0 else '▼'} {abs(chg):.2f}%"
        native_rows += f'''
        <a class="asset" href="/token/{h["symbol"]}">
            {_coin_icon(h["symbol"])}
            <div class="meta">
                <div class="nm">{c["crypto_name"] if c else h["symbol"]}</div>
                <div class="px">{fmt_usd(price, disp)} · <span class="chg {chg_cls}">{chg_txt}</span></div>
            </div>
            <div class="rhs">
                <div class="bal">{h["balance"]:,.4f} {h["symbol"]}</div>
                <div class="usd">{fmt_usd(usd, disp)}</div>
            </div>
        </a>'''

    wsc_bal  = wsc_info["balance"]
    total_usd += wsc_bal  # WSC redeems 1:1 for cash
    wsc_row = f'''
        <div class="asset">
            {_coin_icon("WSC")}
            <div class="meta">
                <div class="nm">{WSC_NAME}</div>
                <div class="px">{fmt_usd(1.0, disp)} · <span class="chg up">stable peg</span></div>
            </div>
            <div class="rhs">
                <div class="bal">{wsc_bal:,.4f} {WSC_SYMBOL}</div>
                <div class="usd">{fmt_usd(wsc_bal, disp)}</div>
            </div>
        </div>'''

    meme_rows = ""
    for h in portfolio["meme_holdings"]:
        c = county_by_sym.get(h["native_symbol"])
        native_price = c["crypto_price"] if c else 0.0
        usd = h["value_native"] * native_price
        total_usd += usd
        chg = h.get("change_24h", 0.0)
        chg_cls = "up" if chg >= 0 else "dn"
        chg_txt = f"{'▲' if chg >= 0 else '▼'} {abs(chg):.2f}%"
        meme_rows += f'''
        <a class="asset" href="/memecoins/{h["symbol"]}">
            {_coin_icon(h["symbol"])}
            <div class="meta">
                <div class="nm">{h["name"]}</div>
                <div class="px">{h["last_price"]:.6f} {h["native_symbol"]} · <span class="chg {chg_cls}">{chg_txt}</span></div>
            </div>
            <div class="rhs">
                <div class="bal">{h["balance"]:,.2f} {h["symbol"]}</div>
                <div class="usd">{fmt_usd(usd, disp)}</div>
            </div>
        </a>'''

    # ── Uniswap swap card (shared with /exchange via crypto_theme) ──────
    from crypto_theme import build_swap_tokens, swap_card_html
    _swap_tokens, _, _ = build_swap_tokens(player.id)
    swap_card = swap_card_html(_swap_tokens, eff_fee_pct, exec_bonus,
                               redirect="/crypto?tab=swap")

    # ── Earn tab data ────────────────────────────────────────────────────
    yield_deposits = []
    try:
        yield_deposits = get_player_yield_deposits(player.id)
    except Exception:
        pass
    faucet = {"can_claim": False, "remaining_seconds": 0}
    try:
        faucet = get_faucet_status(player.id)
    except Exception:
        pass

    mining_card = ""
    if my_county:
        mining_card = f'''
        <div class="earn-card">
            <h4>⛏️ Mining Node — {my_county.name}</h4>
            <div class="row"><span>Network</span><b>{my_county.crypto_name} ({my_county.crypto_symbol})</b></div>
            <div class="row"><span>Energy pool</span><b>{(my_county.mining_energy_pool or 0):,.2f}</b></div>
            <div style="margin-top:10px;"><a class="pill-lnk" href="/county/{my_county.id}/mining">Open Mining Node →</a>
            <a class="pill-lnk" href="/county/{my_county.id}/governance" style="margin-left:6px;">Governance →</a></div>
        </div>'''
    else:
        mining_card = '''
        <div class="earn-card">
            <h4>⛏️ Mining</h4>
            <div class="row"><span>Your city must join a county to mine its native token.</span></div>
            <div style="margin-top:10px;"><a class="pill-lnk" href="/counties">Browse Counties →</a></div>
        </div>'''

    stake_rows = ""
    for s in portfolio["stakes"]:
        stake_rows += (f'<div class="row"><span><a href="/memecoins/{s["meme_symbol"]}">{s["meme_symbol"]}</a>'
                       f' · staked {s["staked_native"]:,.2f} {s["native_symbol"]}</span>'
                       f'<b>+{s["total_earned"]:,.4f} earned</b></div>')
    yield_rows = ""
    for d in yield_deposits:
        _sym = d.get("meme_symbol", "?")
        yield_rows += (f'<div class="row"><span><a href="/memecoins/{_sym}">{_sym}</a>'
                       f' · {d.get("amount", 0):,.2f} deposited</span>'
                       f'<b>+{d.get("total_earned", 0):,.4f} WSC</b></div>')

    faucet_btn = (
        '<button class="pill-btn" id="faucet-btn" onclick="cbFaucet()">💧 Claim Free WSC</button>'
        if faucet.get("can_claim")
        else f'<span class="pill-lnk" style="opacity:.6;">💧 Faucet in {max(0, faucet.get("remaining_seconds", 0)) // 3600}h '
             f'{(max(0, faucet.get("remaining_seconds", 0)) % 3600) // 60}m</span>'
    )

    # ── Activity tab (crypto ledger) ─────────────────────────────────────
    act_rows = ""
    try:
        from stats_ux import TransactionLog, get_db as _sdb_fn
        _sdb = _sdb_fn()
        try:
            txs = (_sdb.query(TransactionLog)
                   .filter(TransactionLog.player_id == player.id,
                           TransactionLog.category == "crypto")
                   .order_by(TransactionLog.timestamp.desc())
                   .limit(40).all())
        finally:
            _sdb.close()
        _ICONS = {"meme_buy": "🛒", "meme_sell": "💱", "meme_launch": "🚀",
                  "meme_mining_reward": "⛏️", "meme_burn_mint": "🔥",
                  "wsc_redemption": "💵", "wsc_purchase": "🪙"}
        for t in txs:
            ico = _ICONS.get(t.transaction_type, "🔗")
            amt = t.amount or 0.0
            amt_cls = "chg up" if amt >= 0 else "chg dn"
            act_rows += f'''
            <div class="act-row">
                <div class="act-ico">{ico}</div>
                <div class="am">
                    <div class="desc">{t.description or t.transaction_type}</div>
                    <div class="when">{_fmt_ago(t.timestamp)} · {t.transaction_type.replace("_", " ")}</div>
                </div>
                <div class="amt {amt_cls}">{"+" if amt >= 0 else ""}{amt:,.4f}</div>
            </div>'''
    except Exception:
        pass
    if not act_rows:
        act_rows = '<div class="empty">No crypto activity yet — make your first swap!</div>'

    valid_tabs = ("wallet", "swap", "earn", "activity")
    if tab not in valid_tabs:
        tab = "wallet"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Crypto — Wadsworth</title>
{_skin_links(player.id, "crypto")}
{HUB_STYLES}
</head>
<body>
<div class="hub-wrap">

  <div class="hub-head">
    <div class="hub-title">🦊 <span class="grad">Wadsworth Crypto</span></div>
    <div class="hub-links">
      <a href="/exchange">Exchange</a><a href="/memecoins">Memes</a>
      <a href="/gas-tracker">Gas</a><a href="/wallet">Classic</a><a href="/">Home</a>
    </div>
  </div>

  <div class="tw-balance">
    <div class="lbl">Total Crypto Portfolio</div>
    <div class="val">{fmt_usd(total_usd, disp)}</div>
    <div class="sub">L1 tokens + meme coins + WSC · live mark-to-market</div>
    <div class="tax-badge">🕶️ 0% TAX · invisible to the government</div>
  </div>

  <div class="tw-actions">
    <button class="tw-act" data-tab="wallet"><span class="ico">👛</span>Wallet</button>
    <button class="tw-act" data-tab="swap"><span class="ico">🔄</span>Swap</button>
    <button class="tw-act" data-tab="earn"><span class="ico">🌱</span>Earn</button>
    <button class="tw-act" data-tab="activity"><span class="ico">🧾</span>Activity</button>
  </div>

  <!-- ════════ WALLET ════════ -->
  <div class="hub-tab" id="tab-wallet">
    <div class="sec-lbl">Layer-1 · County Native Tokens</div>
    {native_rows or '<div class="empty">No native tokens yet — swap some cash on the Swap tab.</div>'}
    <div class="sec-lbl">Stablecoin</div>
    {wsc_row}
    <div class="sec-lbl">Layer-2 · Meme Coins</div>
    {meme_rows or '<div class="empty">No meme coins yet — <a href="/memecoins">discover the meme market →</a></div>'}
  </div>

  <!-- ════════ SWAP (Uniswap card — shared with /exchange) ════════ -->
  <div class="hub-tab" id="tab-swap">
    {swap_card}
    <p style="text-align:center;font-size:.68rem;color:var(--mut);margin-top:12px;">
      Routes automatically: Cash ↔ L1 · L1 ↔ L1 · L1 ↔ WSC · WSC → Cash.<br>
      Meme coins trade on their own order books — <a href="/memecoins">open the meme market →</a>
    </p>
  </div>

  <!-- ════════ EARN ════════ -->
  <div class="hub-tab" id="tab-earn">
    {mining_card}
    <div class="earn-card">
      <h4>🪙 Meme Mining Stakes</h4>
      {stake_rows or '<div class="row"><span>No active stakes. Stake native tokens on any meme coin page to mine it.</span></div>'}
    </div>
    <div class="earn-card">
      <h4>🌾 WSC Yield Farming</h4>
      {yield_rows or '<div class="row"><span>No yield deposits. Deposit meme coins in the <a href="/wallet">classic wallet</a> to earn WSC hourly.</span></div>'}
    </div>
    <div class="earn-card">
      <h4>💧 WSC Faucet</h4>
      <div class="row"><span>Free WSC on a cooldown — every claim is pure profit.</span></div>
      <div style="margin-top:10px;">{faucet_btn}</div>
    </div>
  </div>

  <!-- ════════ ACTIVITY ════════ -->
  <div class="hub-tab" id="tab-activity">
    <div class="sec-lbl">Crypto Activity · last 40 · <a href="/stats/transactions">full ledger →</a></div>
    {act_rows}
  </div>

</div>

<div id="cb-toast"></div>

<script>
// ───────── Tabs ─────────
function cbTab(t) {{
  document.querySelectorAll('.hub-tab').forEach(function(el) {{ el.classList.remove('show'); }});
  document.querySelectorAll('.tw-act').forEach(function(el) {{ el.classList.remove('active'); }});
  var pane = document.getElementById('tab-' + t);
  if (pane) pane.classList.add('show');
  var btn = document.querySelector('.tw-act[data-tab="' + t + '"]');
  if (btn) btn.classList.add('active');
  try {{ history.replaceState(null, '', '/crypto?tab=' + t); }} catch (e) {{}}
}}
document.querySelectorAll('.tw-act').forEach(function(b) {{
  b.addEventListener('click', function() {{ cbTab(b.dataset.tab); }});
}});
cbTab({json.dumps(tab)});


// ───────── Faucet ─────────
function cbFaucet() {{
  var b = document.getElementById('faucet-btn');
  if (b) {{ b.disabled = true; b.textContent = 'Claiming…'; }}
  var fd = new FormData(); fd.set('ajax', '1');
  fetch('/api/wallet/faucet', {{method: 'POST', body: fd}})
    .then(function(r) {{ return r.json(); }})
    .then(function(d) {{
      cbToast(d.ok ? (d.message || 'Claimed!') : (d.error || 'Claim failed'), !!d.ok);
      if (d.ok) setTimeout(function() {{ location.href = '/crypto?tab=earn'; }}, 1400);
      else if (b) {{ b.disabled = false; b.textContent = '💧 Claim Free WSC'; }}
    }})
    .catch(function() {{ cbToast('Network error.', false); if (b) b.disabled = false; }});
}}
</script>
{_nav_loader()}
</body>
</html>"""
    return HTMLResponse(content=html)
