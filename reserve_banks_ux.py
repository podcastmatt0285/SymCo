"""
reserve_banks_ux.py — HTML dashboards and API routes for State Reserve Banks.

Routes
------
GET  /reserve-banks/bonds                    Bond Market dashboard
GET  /reserve-banks/forex                    Forex informational dashboard (read-only)
POST /api/reserve-banks/bonds/buy            Purchase a bond
POST /api/reserve-banks/bonds/sell/{bond_id} Sell a bond early
POST /api/corporate-actions/legal-tender/set Set player's legal tender

NOTE: There is NO manual forex swap route. All currency conversion is automatic
      and handled by the reserve bank inter-bank settlement system.
"""

from fastapi import APIRouter, Cookie, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import Optional

from auth import get_player_from_session, get_db as get_auth_db
from reserve_banks import (
    get_all_banks, get_player_bonds, get_player_currency_balances,
    get_recent_forex_trades, get_yield_history,
    get_player_legal_tender,
    get_all_bank_reserves, get_interbank_trades,
    purchase_bond, sell_bond,
    BOND_MATURITIES, FOREX_FEE_RATE,
)
from wallet import get_wsc_wallet_info, get_treasury_info, get_player_yield_deposits

router = APIRouter(tags=["reserve-banks"])

# ──────────────────────────────────────────────────────────────────────────────
# SHARED CSS
# ──────────────────────────────────────────────────────────────────────────────

_CSS = """
* { box-sizing: border-box; }
body {
    font-family: 'JetBrains Mono', monospace;
    margin: 0; padding: 20px 16px;
    background: #020617; color: #e5e7eb; font-size: 14px;
}
.container { max-width: 1200px; margin: 0 auto; }
.card {
    background: #0f172a; border: 1px solid #1e293b;
    padding: 20px; margin-bottom: 16px; border-radius: 4px;
}
.grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.grid3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; }
h1 { color: #e5e7eb; margin: 8px 0 4px 0; font-size: 1.4rem; }
h2 { color: #94a3b8; font-size: 1rem; margin: 0 0 16px 0; }
h3 { color: #cbd5e1; font-size: 0.95rem; margin: 0 0 10px 0; }
.nav { color: #38bdf8; text-decoration: none; font-size: 0.85rem; }
.nav:hover { text-decoration: underline; }
.badge {
    display: inline-block; padding: 2px 8px; border-radius: 3px;
    font-size: 0.7rem; font-weight: bold; margin-left: 6px; vertical-align: middle;
}
.badge-pos  { background: #22c55e; color: #020617; }
.badge-neg  { background: #ef4444; color: #fff; }
.badge-zero { background: #64748b; color: #e5e7eb; }
.bank-card {
    background: #0a1628; border: 1px solid #1e293b; border-radius: 4px;
    padding: 16px; margin-bottom: 12px;
}
.bank-header {
    display: flex; align-items: center; gap: 10px;
    margin-bottom: 12px; border-bottom: 1px solid #1e293b; padding-bottom: 8px;
}
.code   { font-size: 1.2rem; font-weight: bold; color: #38bdf8; }
.yield  { font-size: 1rem; color: #22c55e; font-weight: bold; }
.yield-neg { color: #ef4444; }
.rate   { font-size: 0.85rem; color: #94a3b8; }
label   { color: #94a3b8; font-size: 0.8rem; display: block; margin-bottom: 4px; }
input, select {
    background: #020617; color: #e5e7eb;
    border: 1px solid #334155; padding: 6px 10px;
    border-radius: 3px; font-size: 0.85rem;
}
.btn {
    padding: 7px 16px; border: none; cursor: pointer;
    border-radius: 3px; font-size: 0.85rem; font-weight: bold;
    display: inline-block; text-decoration: none; margin: 4px 4px 4px 0;
}
.btn-blue   { background: #38bdf8; color: #020617; }
.btn-green  { background: #22c55e; color: #020617; }
.btn-red    { background: #ef4444; color: #fff; }
.btn-gray   { background: #334155; color: #94a3b8; }
.bond-row {
    background: #0f172a; border-left: 4px solid #38bdf8;
    padding: 12px; margin: 8px 0; border-radius: 2px;
}
.fx-row {
    display: grid; grid-template-columns: 80px 100px 100px 100px 80px 1fr;
    gap: 8px; align-items: center; padding: 6px 0;
    border-bottom: 1px solid #0f172a; font-size: 0.85rem; color: #94a3b8;
}
.fx-row-header { font-size: 0.75rem; color: #475569; font-weight: bold; }
.mini { font-size: 0.75rem; color: #64748b; }
.alert-ok  { background: #052e16; border: 1px solid #166534; color: #4ade80; padding: 10px 14px; border-radius: 3px; margin-bottom: 12px; }
.alert-err { background: #2d1a1a; border: 1px solid #7f1d1d; color: #fca5a5; padding: 10px 14px; border-radius: 3px; margin-bottom: 12px; }
@media (max-width: 700px) {
    .grid2, .grid3 { grid-template-columns: 1fr; }
    .fx-row { grid-template-columns: 1fr 1fr; }
}
"""


def _auth(session_token):
    db = get_auth_db()
    p  = get_player_from_session(db, session_token)
    db.close()
    return p


def _page(title: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html><head>
<title>{title} — Reserve Banks</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>{_CSS}</style>
</head><body><div class="container">{body}</div></body></html>"""


# ──────────────────────────────────────────────────────────────────────────────
# BOND MARKET DASHBOARD
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/reserve-banks/bonds", response_class=HTMLResponse)
def bond_market(
    msg: Optional[str]   = None,
    err: Optional[str]   = None,
    session_token: Optional[str] = Cookie(None),
):
    player = _auth(session_token)
    if not player:
        return RedirectResponse("/login")

    from reserve_banks import get_player_display_currency, fmt_usd, get_player_usd_pcb_balance
    disp = get_player_display_currency(player.id)

    banks        = get_all_banks()
    my_bonds     = get_player_bonds(player.id)
    my_balances  = get_player_currency_balances(player.id)
    my_tender    = get_player_legal_tender(player.id)
    wsc_info     = get_wsc_wallet_info(player.id)
    treasury     = get_treasury_info()
    my_deposits  = get_player_yield_deposits(player.id)

    from cities import get_player_stable_coin_balances
    comptroller_coins = get_player_stable_coin_balances(player.id)

    # ── Flash messages ──
    flash = ""
    if msg:
        flash = f'<div class="alert-ok">✓ {msg}</div>'
    if err:
        flash = f'<div class="alert-err">✗ {err}</div>'

    # ── Holdings summary card ──
    # USD balance — player.cash_balance IS get_usd_balance() IS PlayerCurrencyBalance USD.
    # They are the same value (cash_balance was migrated into PlayerCurrencyBalance).
    # We never add both; just read once.
    usd_balance  = player.cash_balance or 0.0

    # my_balances comes from get_player_currency_balances() which includes all
    # non-zero PlayerCurrencyBalance rows. Strip USD from it (we'll add it explicitly
    # so it always shows even when $0, and avoids any double-entry).
    bal_chips_list = [b for b in my_balances if b["currency_code"] != "USD"]

    # Always show USD so players can see their spendable USD balance.
    # PlayerCurrencyBalance USD = all USD earned from income conversion, bond
    # payouts, trading etc. This is the only USD that exists in-game now.
    bal_chips_list.append({
        "flag": "🇺🇸", "currency_code": "USD",
        "currency_symbol": "$", "balance": usd_balance,
        "usd_value": usd_balance,
    })
    # Sort: legal tender first, then by code
    bal_chips_list.sort(key=lambda b: (b["currency_code"] != my_tender, b["currency_code"]))
    if bal_chips_list:
        bal_chips = "".join(
            f'<span style="margin-right:14px;">{b["flag"]} <strong>{b["currency_code"]}</strong> '
            f'<strong style="color:#22c55e;">{b["currency_symbol"]}{b["balance"]:,.4f}</strong> '
            f'<span class="mini">≈ {fmt_usd(b["usd_value"], disp)}</span></span>'
            for b in bal_chips_list
        )
    else:
        bal_chips = '<span style="color:#475569;">None yet — earn income with your legal tender set to a foreign currency.</span>'

    # Yield farming deposits row
    if my_deposits:
        dep_chips = "".join(
            f'<span style="margin-right:14px;"><strong style="color:#a78bfa;">{d["meme_symbol"]}</strong> '
            f'{d["quantity"]:.4f} staked &bull; earned {d["total_earned_wsc"]:.4f} WSC</span>'
            for d in my_deposits
        )
    else:
        dep_chips = '<span style="color:#475569;">No meme coins staked yet.</span>'

    holdings_html = f"""
    <div class="card" style="border-left:3px solid #38bdf8;">
      <h3 style="margin-top:0;">📊 Your Holdings Summary</h3>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin-bottom:14px;">
        <div>
          <div class="mini">Legal tender</div>
          <strong style="color:#38bdf8;font-size:1.1rem;">{my_tender}</strong>
        </div>
        <div>
          <div class="mini">WSC balance</div>
          <strong style="color:#f59e0b;font-size:1.1rem;">{wsc_info['balance']:.4f} WSC</strong>
        </div>
        <div>
          <div class="mini">WSC earned — yield farming</div>
          <span style="color:#22c55e;">{wsc_info['total_earned_yield']:.4f}</span>
        </div>
        <div>
          <div class="mini">WSC earned — faucet</div>
          <span style="color:#22c55e;">{wsc_info['total_earned_faucet']:.4f}</span>
        </div>
        <div>
          <div class="mini">WSC earned — airdrops</div>
          <span style="color:#22c55e;">{wsc_info['total_earned_airdrop']:.4f}</span>
        </div>
        <div>
          <div class="mini">Active bonds</div>
          <strong>{len(my_bonds)}</strong>
        </div>
      </div>
      <div style="margin-bottom:10px;">
        <div class="mini" style="margin-bottom:4px;">Currency balances
          <span style="color:#475569;font-style:italic;"> — spendable cash in each currency (USD = PlayerCurrencyBalance, your in-game wallet)</span>
        </div>
        <div>{bal_chips}</div>
        <div class="mini" style="color:#475569;margin-top:6px;line-height:1.5;">
          💡 <strong style="color:#94a3b8;">How USD works:</strong>
          All USD in the game is stored in your <em>PlayerCurrencyBalance</em> wallet —
          this is the same balance your businesses earn into, bonds pay out to, and trades settle in.
          Bond face values shown on the bond cards below are <em>what a bond will pay when it matures</em>,
          not money you can spend yet.
        </div>
      </div>
      <div style="margin-bottom:10px;">
        <div class="mini" style="margin-bottom:4px;">Yield farming deposits</div>
        <div>{dep_chips}</div>
      </div>
      <div>
        <div class="mini" style="margin-bottom:4px;">Treasury pools (global)</div>
        <span style="margin-right:14px;">⚡ Yield farming: <strong style="color:#a78bfa;">{treasury['yield_farming_pool']:.4f} WSC</strong></span>
        <span style="margin-right:14px;">🚰 Faucet: <strong style="color:#38bdf8;">{treasury['faucet_pool']:.4f} WSC</strong></span>
        <span>✈️ Airdrop: <strong style="color:#22c55e;">{treasury['airdrop_pool']:.4f} WSC</strong></span>
      </div>
    </div>"""

    balances_html = ""  # folded into holdings_html above

    # ── My active bonds ──
    if my_bonds:
        bond_rows = ""
        for b in my_bonds:
            yc      = "#22c55e" if b["current_yield_pct"] >= 0 else "#ef4444"
            delta   = b["current_yield_pct"] - b["purchase_yield_pct"]
            delta_s = f'+{delta:.4f}%' if delta >= 0 else f'{delta:.4f}%'
            sell_confirm = f"Sell bond early? You will receive approx {b['currency_symbol']}{b['sell_value_foreign']:.4f} {b['currency_code']} (face value converted at current FX)."
            bond_rows += f"""
            <div class="bond-row">
                <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
                    <div>
                        <span style="font-size:1.1rem;">{b['flag']}</span>
                        <strong style="color:#38bdf8;">{b['currency_code']}</strong>
                        {b['maturity_days']}-day bond &bull;
                        matures <strong>{b['matures_at']}</strong>
                        ({b['remaining_days']} days left)
                    </div>
                    <div style="text-align:right;">
                        <div>Face value at maturity: <strong>{b['currency_symbol']}{b['maturity_value_foreign']:.4f} {b['currency_code']}</strong>
                            <span class="mini"> (${b['face_value_wsc']:.4f} USD equiv)</span></div>
                        <div class="mini">Sell now: <strong style="color:#f59e0b;">{b['currency_symbol']}{b['sell_value_foreign']:.4f} {b['currency_code']}</strong> (×{b['price_factor']:.4f})</div>
                    </div>
                </div>
                <div style="margin-top:8px;display:flex;gap:20px;flex-wrap:wrap;">
                    <span>Yield at purchase: <strong>{b['purchase_yield_pct']:.4f}%</strong></span>
                    <span>Current yield: <strong style="color:{yc};">{b['current_yield_pct']:.4f}%</strong>
                        <span class="mini">({delta_s})</span></span>
                    <span>Interest accrued: <strong style="color:#22c55e;">{b['currency_symbol']}{b['interest_accrued']:.6f} {b['currency_code']}</strong></span>
                </div>
                <div style="margin-top:8px;">
                    <form action="/api/reserve-banks/bonds/sell/{b['id']}" method="post" style="display:inline;"
                          onsubmit="return confirm('{sell_confirm}')">
                        <button type="submit" class="btn btn-red">Sell Early</button>
                    </form>
                </div>
            </div>"""
        bonds_section = f'<div class="card"><h3>📋 Your Active Bonds</h3>{bond_rows}</div>'
    else:
        bonds_section = '<div class="card"><p style="color:#64748b;">No active bonds. Buy one below.</p></div>'

    # ── "Pay with" options: WSC + any comptroller coins the player holds ──
    pay_with_opts = f'<option value="WSC">WSC ({wsc_info["balance"]:.4f} available)</option>'
    for _cc in comptroller_coins:
        pay_with_opts += (
            f'<option value="{_cc["symbol"]}">'
            f'{_cc["symbol"]} ({_cc["balance"]:.4f} available — {_cc["city_name"]})'
            f'</option>'
        )

    # ── Bank cards with buy form ──
    bank_cards = ""
    maturity_opts = "".join(f'<option value="{d}">{d} days</option>' for d in BOND_MATURITIES)
    for bank in banks:
        yc    = "yield" if bank["yield_pct"] >= 0 else "yield yield-neg"
        badge = ("badge-pos" if bank["yield_pct"] > 0 else
                 "badge-neg" if bank["yield_pct"] < 0 else "badge-zero")
        ystr  = f'{bank["yield_pct"]:+.4f}%'
        hist  = get_yield_history(bank["id"], limit=24)
        sparkline = ""
        if hist:
            rates = [h["yield_pct"] for h in hist]
            mn, mx = min(rates), max(rates)
            span   = mx - mn or 0.001
            pts    = " ".join(
                f'{i*4},{40 - int((r - mn) / span * 38)}'
                for i, r in enumerate(rates)
            )
            sparkline = (
                f'<svg viewBox="0 0 {len(rates)*4} 40" width="100%" height="40" preserveAspectRatio="none" style="margin-top:6px;">'
                f'<polyline points="{pts}" fill="none" stroke="#38bdf8" stroke-width="1.5"/>'
                f'</svg>'
            )
        bank_cards += f"""
        <div class="bank-card">
            <div class="bank-header">
                <span style="font-size:1.5rem;">{bank['flag']}</span>
                <div>
                    <span class="code">{bank['code']}</span>
                    <span class="mini" style="margin-left:6px;">{bank['name']}</span>
                </div>
                <div style="margin-left:auto;text-align:right;">
                    <div class="{yc}">{ystr} <span class="badge {badge}">p.a.</span></div>
                    <div class="rate">1 {bank['code']} = ${bank['usd_per_unit']:.6f} USD</div>
                </div>
            </div>
            <div style="font-size:0.75rem;color:#475569;margin-bottom:6px;">
                {bank['total_bonds']:,} bonds outstanding &bull; ${bank['total_face_wsc']:,.2f} USD-equiv face value &bull;
                floor {bank['min_yield_pct']:+.4f}% &bull; ceiling {bank['max_yield_pct']:+.4f}%
            </div>
            {sparkline}
            <form action="/api/reserve-banks/bonds/buy" method="post"
                  style="display:flex;gap:10px;align-items:flex-end;flex-wrap:wrap;margin-top:12px;">
                <input type="hidden" name="currency_code" value="{bank['code']}">
                <div>
                    <label>Pay with</label>
                    <select name="stable_coin_symbol" style="width:220px;"
                            onchange="this.closest('form').querySelector('.amt-label').textContent='Amount ('+this.value+')'">
                        {pay_with_opts}
                    </select>
                </div>
                <div>
                    <label class="amt-label">Amount (WSC)</label>
                    <input type="number" name="wsc_amount" min="0.01" step="0.01"
                           placeholder="e.g. 500" style="width:130px;" required>
                </div>
                <div>
                    <label>Maturity</label>
                    <select name="maturity_days" style="width:110px;">{maturity_opts}</select>
                </div>
                <button type="submit" class="btn btn-blue">Buy Bond →</button>
            </form>
        </div>"""

    body = f"""
    <a href="/" class="nav">← Dashboard</a>
    <h1>🏦 State Reserve Banks — Bond Market</h1>
    <p style="color:#64748b;margin:0 0 20px 0;">
        Buy bonds with WSC or any comptroller stable coin to earn interest in foreign currencies.
        Auto-conversion routes all business income into your legal tender.
        <a href="/reserve-banks/forex" class="nav">Forex Dashboard →</a>
    </p>
    {flash}
    {holdings_html}
    {bonds_section}
    <h2>Available Reserve Banks</h2>
    {bank_cards}
    """
    return _page("Bond Market", body)


# ──────────────────────────────────────────────────────────────────────────────
# FOREX DASHBOARD
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/reserve-banks/forex", response_class=HTMLResponse)
def forex_dashboard(
    msg: Optional[str]   = None,
    err: Optional[str]   = None,
    session_token: Optional[str] = Cookie(None),
):
    player = _auth(session_token)
    if not player:
        return RedirectResponse("/login")

    from reserve_banks import get_player_display_currency, fmt_usd, get_player_usd_pcb_balance
    disp = get_player_display_currency(player.id)

    banks       = get_all_banks()
    my_balances = get_player_currency_balances(player.id)
    my_tender   = get_player_legal_tender(player.id)
    my_bonds    = get_player_bonds(player.id)
    bank_rsvs   = get_all_bank_reserves()
    ib_trades   = get_interbank_trades(limit=40)
    fx_trades   = get_recent_forex_trades(limit=50)

    flash = ""
    if msg:
        flash = f'<div class="alert-ok">✓ {msg}</div>'
    if err:
        flash = f'<div class="alert-err">✗ {err}</div>'

    # ── Live FX rates table ──
    fx_rows = ""
    for bank in banks:
        usd_rate = bank["usd_per_unit"]
        inv_rate = 1.0 / usd_rate if usd_rate > 0 else 0.0
        yc = "#22c55e" if bank["yield_pct"] >= 0 else "#ef4444"
        fx_rows += f"""
        <div class="fx-row">
            <span>{bank['flag']} <strong style="color:#38bdf8;">{bank['code']}</strong></span>
            <span>${usd_rate:.6f}</span>
            <span>{inv_rate:.2f} {bank['code']}</span>
            <span style="color:{yc};">{bank['yield_pct']:+.4f}%</span>
            <span class="mini">{FOREX_FEE_RATE*100:.1f}% fee</span>
            <span class="mini">{bank['name']}</span>
        </div>"""

    # ── Balance card: all actual currency balances ──
    # player.cash_balance, get_usd_balance(), and get_player_usd_pcb_balance() all read
    # the same PlayerCurrencyBalance USD row — read once to avoid double-counting.
    usd_balance = player.cash_balance or 0.0

    # Strip USD from my_balances (in case PlayerCurrencyBalance had a non-zero USD row)
    # then always add it explicitly so it shows even at $0.
    bal_chips_list = [b for b in my_balances if b["currency_code"] != "USD"]
    bal_chips_list.append({
        "flag": "🇺🇸", "currency_code": "USD",
        "currency_symbol": "$", "balance": usd_balance,
        "usd_value": usd_balance,
    })
    bal_chips_list.sort(key=lambda b: (b["currency_code"] != my_tender, b["currency_code"]))

    if bal_chips_list:
        bal_chips = "".join(
            f'<span style="margin-right:16px;">{b["flag"]} <strong>{b["currency_code"]}</strong> '
            f'<strong style="color:#38bdf8;">{b["currency_symbol"]}{b["balance"]:,.4f}</strong> '
            f'<span class="mini">≈ {fmt_usd(b["usd_value"], disp)}</span></span>'
            for b in bal_chips_list
        )
    else:
        bal_chips = '<span style="color:#475569;">No balances yet.</span>'

    # ── Active bond face values (separate from cash balances) ──
    bond_totals: dict = {}
    for b in my_bonds:
        cc = b["currency_code"]
        if cc not in bond_totals:
            bond_totals[cc] = {"flag": b["flag"], "symbol": b["currency_symbol"], "total": 0.0}
        bond_totals[cc]["total"] += b["maturity_value_foreign"]
    bond_chips = "".join(
        f'<span style="margin-right:12px;">{v["flag"]} {cc} '
        f'<strong style="color:#22c55e;">{v["symbol"]}{v["total"]:,.4f}</strong></span>'
        for cc, v in bond_totals.items()
    ) if bond_totals else '<span style="color:#475569;">No active bonds</span>'

    # ── Bank reserve matrix ──
    reserve_rows = ""
    for br in bank_rsvs:
        if not br["reserves"]:
            continue
        res_items = " ".join(
            f'<span style="margin-right:10px;"><strong style="color:#38bdf8;">{r["currency_code"]}</strong> '
            f'{r["balance"]:,.2f}</span>'
            for r in br["reserves"]
        )
        debt_s = ""
        if br["total_debt_usd"] > 0:
            debt_s = f'<span style="color:#ef4444;font-size:0.75rem;">Debt: {fmt_usd(br["total_debt_usd"], disp)}</span>'
        reserve_rows += f"""
        <div style="padding:8px 0;border-bottom:1px solid #0f172a;display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
            <span style="min-width:60px;">{br['flag']} <strong style="color:#38bdf8;">{br['bank_code']}</strong></span>
            <span style="color:#64748b;font-size:0.75rem;">holds:</span>
            <span>{res_items}</span>
            {debt_s}
        </div>"""

    if reserve_rows:
        reserves_html = f"""
        <div class="card">
            <h3>🏦 Bank Reserve Holdings</h3>
            <p class="mini" style="margin:0 0 8px 0;">
                Reserves accumulated through income-conversion fees and inter-bank bond swaps.
                Low reserves trigger automatic bond swaps (pushing that bank's yield up).
            </p>
            {reserve_rows}
        </div>"""
    else:
        reserves_html = ""

    # ── Inter-bank trade feed ──
    if ib_trades:
        ib_rows = ""
        for t in ib_trades:
            ib_rows += f"""
            <div class="fx-row">
                <span style="color:#a78bfa;">{t['buyer_bank']}</span>
                <span style="color:#64748b;">buys</span>
                <span style="color:#38bdf8;">{t['bond_currency']} bonds</span>
                <span style="color:#94a3b8;">{fmt_usd(t['face_value_usd'], disp)}</span>
                <span style="color:#22c55e;">{t['consideration_curr']} {t['consideration_amount']:,.4f}</span>
                <span style="color:#334155;font-size:0.72rem;">{t['executed_at']} · {t['trigger']}</span>
            </div>"""
        ib_html = f"""
        <div class="card">
            <h3>🔗 Inter-Bank Settlement Feed (last {len(ib_trades)})</h3>
            <p class="mini" style="margin:0 0 8px 0;">
                Banks automatically swap bonds to maintain reserves.
                High settlement activity from a bank raises its yield (more bond demand needed).
            </p>
            <div class="fx-row fx-row-header">
                <span>BUYER BANK</span><span></span><span>BONDS PURCHASED</span>
                <span>USD EQUIV</span><span>CONSIDERATION</span><span>TIME · TRIGGER</span>
            </div>
            {ib_rows}
        </div>"""
    else:
        ib_html = '<div class="card"><p style="color:#64748b;">No inter-bank settlements yet. Settlements occur automatically when bank reserves fall below minimum thresholds.</p></div>'

    # ── Recent player forex transactions ──
    if fx_trades:
        fx_t_rows = ""
        for t in fx_trades:
            pid_label = f"Player&nbsp;{t['player_id']}" if t["player_id"] else "<em>system</em>"
            fx_t_rows += f"""
            <div class="fx-row">
                <span style="color:#a78bfa;">{pid_label}</span>
                <span style="color:#38bdf8;">{t['from_currency']}</span>
                <span style="color:#64748b;">→</span>
                <span style="color:#22c55e;">{t['to_currency']}</span>
                <span style="color:#94a3b8;">{t['amount_from']:,.4f} → {t['amount_to']:,.4f}</span>
                <span style="color:#475569;font-size:0.75rem;">
                    rate&nbsp;{t['rate']:.6f} &bull; fee&nbsp;${t['fee_usd']:.4f}
                </span>
                <span style="color:#334155;font-size:0.72rem;">{t['executed_at']}</span>
            </div>"""
        fx_trades_html = f"""
        <div class="card">
            <h3>📋 Recent Forex Conversions (last {len(fx_trades)})</h3>
            <p class="mini" style="margin:0 0 8px 0;">
                Every automatic income conversion and cross-currency payment is logged here.
                Fee = {FOREX_FEE_RATE*100:.1f}% per conversion, taken by the issuing reserve bank.
            </p>
            <div class="fx-row fx-row-header" style="color:#475569;">
                <span>PLAYER</span><span>FROM</span><span></span><span>TO</span>
                <span>AMOUNTS</span><span>RATE / FEE</span><span>TIME</span>
            </div>
            {fx_t_rows}
        </div>"""
    else:
        fx_trades_html = ""

    body = f"""
    <a href="/" class="nav">← Dashboard</a>
    <h1>💱 Forex Market — Informational</h1>
    <p style="color:#64748b;margin:0 0 4px 0;">
        Exchange rates are set by inter-bank bond demand — no manual player swaps.
        Income is auto-converted to your legal tender ({FOREX_FEE_RATE*100:.1f}% fee via your reserve bank).
        Legal tender: <strong style="color:#38bdf8;">{my_tender}</strong> &bull;
        <a href="/reserve-banks/bonds" class="nav">Bond Market →</a> &bull;
        <a href="/corporate-actions/dashboard" class="nav">Change Legal Tender →</a>
    </p>
    {flash}

    <div class="card" style="border-left:3px solid #38bdf8;margin-bottom:16px;">
        <h3>Your Balances <span class="mini" style="color:#475569;font-style:italic;">— spendable cash in your PlayerCurrencyBalance wallet</span></h3>
        <div style="flex-wrap:wrap;display:flex;gap:8px 4px;">{bal_chips}</div>
        <div class="mini" style="color:#475569;margin-top:6px;line-height:1.5;">
          💡 USD shown is your <em>PlayerCurrencyBalance</em> wallet — the single source of truth for all
          in-game USD (income conversions, bond payouts, trades). Bond face values below are
          <em>future payouts at maturity</em>, not yet spendable.
        </div>
        <div style="margin-top:10px;padding-top:10px;border-top:1px solid #1e293b;">
            <span class="mini" style="display:block;margin-bottom:4px;color:#64748b;">Active bond face values (at maturity — not yet spendable):</span>
            <div style="flex-wrap:wrap;display:flex;gap:4px;">{bond_chips}</div>
        </div>
    </div>

    <div class="card">
        <h3>🌐 Live Exchange Rates (USD base)</h3>
        <p class="mini" style="margin:0 0 8px 0;">
            Rates shift each hour based on net bond demand.
            Buying bonds in a currency = demand for that currency = rate appreciates.
            High outstanding debt in a bank pushes its yield up (risk premium).
        </p>
        <div class="fx-row fx-row-header" style="color:#475569;">
            <span>CURRENCY</span><span>USD VALUE</span><span>INVERSE</span>
            <span>YIELD</span><span>AUTO FEE</span><span>BANK</span>
        </div>
        {fx_rows}
    </div>

    {reserves_html}
    {ib_html}
    {fx_trades_html}
    """
    return _page("Forex Market", body)


# ──────────────────────────────────────────────────────────────────────────────
# API: BUY BOND
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/api/reserve-banks/bonds/buy")
def api_buy_bond(
    currency_code:       str   = Form(...),
    wsc_amount:          float = Form(...),
    maturity_days:       int   = Form(...),
    stable_coin_symbol:  str   = Form("WSC"),
    session_token: Optional[str] = Cookie(None),
):
    player = _auth(session_token)
    if not player:
        return RedirectResponse("/login", status_code=303)

    ok, msg = purchase_bond(player.id, currency_code, wsc_amount, maturity_days, stable_coin_symbol)
    param   = "msg" if ok else "err"
    from urllib.parse import quote
    return RedirectResponse(f"/reserve-banks/bonds?{param}={quote(msg)}", status_code=303)


# ──────────────────────────────────────────────────────────────────────────────
# API: SELL BOND EARLY
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/api/reserve-banks/bonds/sell/{bond_id}")
def api_sell_bond(
    bond_id: int,
    session_token: Optional[str] = Cookie(None),
):
    player = _auth(session_token)
    if not player:
        return RedirectResponse("/login", status_code=303)

    ok, msg = sell_bond(player.id, bond_id)
    param   = "msg" if ok else "err"
    from urllib.parse import quote
    return RedirectResponse(f"/reserve-banks/bonds?{param}={quote(msg)}", status_code=303)


# ──────────────────────────────────────────────────────────────────────────────
# API: LEGAL TENDER
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/api/corporate-actions/legal-tender/set")
def api_set_legal_tender(
    currency_code: str = Form(...),
    session_token: Optional[str] = Cookie(None),
):
    from reserve_banks import set_player_legal_tender
    player = _auth(session_token)
    if not player:
        return RedirectResponse("/login", status_code=303)

    ok, msg = set_player_legal_tender(player.id, currency_code.upper())
    param   = "msg" if ok else "err"
    from urllib.parse import quote
    return RedirectResponse(f"/corporate-actions/dashboard?{param}={quote(msg)}", status_code=303)


