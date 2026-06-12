"""
crypto_theme.py — Shared Trust Wallet × Uniswap design language for ALL
crypto pages (hub + every deep page).

Exports:
  CRYPTO_THEME      — <style> + <script> block. Appended AFTER a page's legacy
                      styles it re-skins every legacy class (.card, .btn,
                      .table, .stat, .badge, forms, order books, tickers…) in
                      the hub's design language, and auto-injects a consistent
                      pill subnav at the top of every crypto page.
  coin_icon(sym)    — deterministic gradient circle token icon.
  swap_card_html()  — the Uniswap-style swap card + self-contained JS router,
                      embeddable on any page (hub and /exchange share it).
"""

import json

# ─────────────────────────────────────────────────────────────────────────────
# Palette + component re-skin. Declared AFTER legacy CSS so it wins the cascade.
# ─────────────────────────────────────────────────────────────────────────────

CRYPTO_THEME = """
<style>
/* ═══ Wadsworth Crypto Theme — Trust Wallet × Uniswap ═══ */
:root {
  --cbg: #05060f; --cpanel: #0c0e1d; --cpanel2: #12152b; --cline: #1c2040;
  --ctxt: #e6e8f5; --cmut: #707694;
  --cgrad: linear-gradient(120deg,#f97316,#a855f7);
  --cgreen: #22c55e; --cred: #ef4444; --caccent: #a855f7; --caccent2: #f97316;
}
body {
  background: var(--cbg) !important; color: var(--ctxt) !important;
  font-family: 'Inter','Segoe UI',system-ui,sans-serif !important;
}
.container { max-width: 1100px !important; }
a { color: #38bdf8; }

/* Header + nav */
.header { border-bottom: 1px solid var(--cline) !important; }
.header h1 { font-size: 1.15rem !important; font-weight: 800 !important; letter-spacing: .01em; }
.nav-link { color: var(--cmut) !important; font-size: .78rem; font-weight: 600; }
.nav-link:hover { color: var(--ctxt) !important; text-decoration: none !important; }

/* Cards → rounded wallet panels */
.card, .poll-card, .proposal-card, .meme-card, .wsc-card, .exchange-panel,
.governance-panel, .mining-node, .wallet-card, .swap-box {
  background: var(--cpanel) !important;
  border: 1px solid var(--cline) !important;
  border-radius: 20px !important;
}
.card h2, .card h3 { color: var(--ctxt) !important; font-weight: 800; }
.card h2 { font-size: .95rem !important; }
.card h3 { font-size: .82rem !important; }
.mining-node { background: linear-gradient(160deg,#160b2e 0%,var(--cpanel) 55%) !important;
  border-color: #2d1d57 !important; }

/* Stats rows */
.stat { border-bottom: 1px solid var(--cline) !important; padding: 9px 0 !important; }
.stat-label, .info-stat-label, .cycle-stat-label { color: var(--cmut) !important; font-size: .74rem !important; }
.stat-value, .info-stat-value, .cycle-stat-value { font-weight: 700 !important; font-size: .85rem; }
.stat-value.positive, .positive { color: var(--cgreen) !important; }
.stat-value.negative, .negative { color: var(--cred) !important; }
.stat-value.crypto { color: #c4b5fd !important; }

/* Buttons → pills; primary gets the gradient */
.btn, .vote-btn, .btn-governance, .pill-btn {
  border-radius: 999px !important; font-weight: 700 !important;
  font-family: inherit !important; transition: opacity .15s, transform .1s !important;
}
.btn:hover { transform: translateY(-1px); }
.btn-primary, .btn-crypto, .btn-meme, .btn-buy, .btn-governance {
  background: var(--cgrad) !important; color: #fff !important; border: none !important;
}
.btn-secondary, .btn-cancel {
  background: var(--cpanel2) !important; color: var(--ctxt) !important;
  border: 1px solid var(--cline) !important;
}
.btn-danger, .btn-sell { background: #3f1120 !important; color: #fda4af !important;
  border: 1px solid #881337 !important; }

/* Forms → dark rounded inputs, violet focus */
.form-group label { color: var(--cmut) !important; font-size: .72rem !important;
  text-transform: uppercase; letter-spacing: .08em; font-weight: 700; }
.form-group input, .form-group select, .burn-input-group input,
input[type="number"], input[type="text"], select, textarea {
  background: var(--cpanel2) !important; border: 1px solid var(--cline) !important;
  border-radius: 14px !important; color: var(--ctxt) !important;
  font-family: inherit !important;
}
.form-group input:focus, .form-group select:focus, input:focus, select:focus, textarea:focus {
  border-color: var(--caccent) !important; outline: none !important;
  box-shadow: 0 0 0 3px rgba(168,85,247,.12) !important;
}

/* Tables → borderless hover rows */
.table th { color: var(--cmut) !important; font-size: .68rem !important;
  text-transform: uppercase; letter-spacing: .1em; border-bottom: 1px solid var(--cline) !important; }
.table td { border-bottom: 1px solid #11142a !important; font-size: .82rem; }
.table tr:hover { background: var(--cpanel2) !important; }

/* Badges → pills */
.badge, .badge-meme, .badge-native, .badge-crypto, .badge-governance,
.phase-indicator, .token-change-badge, .price-change-badge, .ticker-chip {
  border-radius: 999px !important; font-weight: 700 !important;
}
.badge-success { background: #052e16 !important; color: #4ade80 !important; }
.badge-warning { background: #2e2008 !important; color: #fbbf24 !important; }
.badge-info    { background: #0b2447 !important; color: #60a5fa !important; }
.badge-crypto, .badge-meme { background: #1e1038 !important; color: #c4b5fd !important; }

/* Alerts */
.alert { border-radius: 14px !important; font-weight: 600; }
.alert-success { background: #052e16 !important; border-color: #14532d !important; color: #bbf7d0 !important; }
.alert-error   { background: #2d0a12 !important; border-color: #7f1d1d !important; color: #fecaca !important; }
.alert-info    { background: #0b2447 !important; border-color: #1e40af !important; color: #bfdbfe !important; }

/* Vote bars / supply bars / mining bars */
.supply-bar, .vote-bar, .mining-bar-bg { background: var(--cpanel2) !important;
  border-radius: 999px !important; overflow: hidden; }
.supply-bar-fill, .mining-bar-fill { background: var(--cgrad) !important;
  border-radius: 999px !important; }
.vote-bar-yes { background: var(--cgreen) !important; }
.vote-bar-no  { background: var(--cred) !important; }
.vote-yes { background: #052e16 !important; color: #4ade80 !important; border: 1px solid #14532d !important; }
.vote-no  { background: #2d0a12 !important; color: #fda4af !important; border: 1px solid #7f1d1d !important; }

/* Token hero / big prices (token + meme detail pages) */
.token-hero { background: var(--cpanel) !important; border: 1px solid var(--cline) !important;
  border-radius: 24px !important; }
.token-logo { border-radius: 50% !important; }
.token-price-big, .price-big { font-weight: 800 !important; letter-spacing: -.02em; }

/* Order book (meme detail) */
.order-book-side { background: var(--cpanel) !important; border: 1px solid var(--cline) !important;
  border-radius: 16px !important; }
.bid-row { color: var(--cgreen) !important; }
.ask-row { color: var(--cred) !important; }
.depth-bar { opacity: .14 !important; border-radius: 4px; }
.spread-line { color: var(--cmut) !important; }

/* Tabs (meme detail) → segmented pills */
.tab-bar { background: var(--cpanel) !important; border: 1px solid var(--cline) !important;
  border-radius: 999px !important; padding: 4px !important; gap: 4px !important; }
.tab-btn { border-radius: 999px !important; font-weight: 700 !important;
  color: var(--cmut) !important; border: none !important; background: none !important; }
.tab-btn.active { background: var(--cgrad) !important; color: #fff !important; }

/* Tickers */
.crypto-ticker, .wallet-ticker { background: var(--cpanel) !important;
  border: 1px solid var(--cline) !important; border-radius: 999px !important; }
.ticker-up { color: var(--cgreen) !important; } .ticker-down { color: var(--cred) !important; }

/* Holder rows (token page) */
.holder-row { border-bottom: 1px solid #11142a !important; }
.holder-row:hover { background: var(--cpanel2) !important; }

/* ═══ Crypto subnav (auto-injected) ═══ */
#crypto-subnav {
  display: flex; gap: 6px; flex-wrap: wrap; align-items: center;
  max-width: 1100px; margin: 0 auto 18px; padding: 6px;
  background: var(--cpanel); border: 1px solid var(--cline); border-radius: 999px;
}
#crypto-subnav a {
  padding: 7px 14px; border-radius: 999px; font-size: .72rem; font-weight: 700;
  color: var(--cmut); text-decoration: none; white-space: nowrap;
}
#crypto-subnav a:hover { color: var(--ctxt); background: var(--cpanel2); }
#crypto-subnav a.on { background: var(--cgrad); color: #fff; }
@media (max-width: 640px) { #crypto-subnav { overflow-x: auto; flex-wrap: nowrap; } }
</style>
<script>
(function () {
  if (document.getElementById('crypto-subnav')) return;
  var links = [
    ['/crypto',            '🦊 Hub'],
    ['/crypto?tab=swap',   '🔄 Swap'],
    ['/exchange',          '⛓️ Markets'],
    ['/memecoins',         '🚀 Memes'],
    ['/wallet',            '👛 WSC'],
    ['/counties',          '🏛️ Counties'],
    ['/gas-tracker',       '⛽ Gas'],
  ];
  var path = location.pathname;
  function isOn(href) {
    var base = href.split('?')[0];
    if (base === '/crypto') return path === '/crypto' && (href.indexOf('tab=swap') < 0) === (location.search.indexOf('tab=swap') < 0);
    if (base === '/exchange')  return path === '/exchange' || path.indexOf('/token/') === 0;
    if (base === '/memecoins') return path.indexOf('/memecoins') === 0;
    if (base === '/counties')  return path.indexOf('/count') === 0;
    return path === base;
  }
  var nav = document.createElement('nav');
  nav.id = 'crypto-subnav';
  nav.innerHTML = links.map(function (l) {
    return '<a href="' + l[0] + '"' + (isOn(l[0]) ? ' class="on"' : '') + '>' + l[1] + '</a>';
  }).join('');
  function mount() { document.body.insertBefore(nav, document.body.firstChild); }
  if (document.body) mount(); else document.addEventListener('DOMContentLoaded', mount);
})();
</script>
"""

_ICON_PALETTES = [
    ("#f97316", "#fb923c"), ("#a855f7", "#c084fc"), ("#38bdf8", "#7dd3fc"),
    ("#22c55e", "#4ade80"), ("#ef4444", "#f87171"), ("#eab308", "#fde047"),
    ("#ec4899", "#f9a8d4"), ("#14b8a6", "#5eead4"),
]


def coin_icon(symbol: str, size: int = 40) -> str:
    """Deterministic gradient circle icon for a token symbol."""
    c1, c2 = _ICON_PALETTES[sum(ord(ch) for ch in symbol) % len(_ICON_PALETTES)]
    fs = ".72rem" if size >= 36 else ".5rem"
    return (f'<div class="coin-ico" style="width:{size}px;height:{size}px;border-radius:50%;'
            f'display:flex;align-items:center;justify-content:center;font-weight:800;'
            f'color:#fff;flex-shrink:0;font-size:{fs};'
            f'background:linear-gradient(135deg,{c1},{c2});">{symbol[:4]}</div>')


# ─────────────────────────────────────────────────────────────────────────────
# Uniswap swap card — shared by /crypto (Swap tab) and /exchange.
# Self-contained: card HTML + styles + routing JS + toast. Embed once per page.
# ─────────────────────────────────────────────────────────────────────────────

SWAP_CARD_STYLES = """
<style>
.uni-card { background: var(--cpanel,#0c0e1d); border: 1px solid var(--cline,#1c2040);
  border-radius: 24px; padding: 14px; max-width: 480px; margin: 14px auto 0; }
.uni-panel { background: var(--cpanel2,#12152b); border: 1px solid transparent; border-radius: 18px;
  padding: 14px 16px; transition: border-color .15s; }
.uni-panel:focus-within { border-color: #2d3460; }
.uni-panel .plbl { font-size: .7rem; color: var(--cmut,#707694); margin-bottom: 8px; }
.uni-row { display: flex; align-items: center; gap: 10px; }
.uni-amt { flex: 1; min-width: 0; background: none !important; border: none !important;
  outline: none !important; box-shadow: none !important; color: var(--ctxt,#e6e8f5);
  font-size: 1.7rem; font-weight: 600; width: 100%; font-family: inherit; }
.uni-amt::placeholder { color: #3a4060; }
.uni-tok { display: flex; align-items: center; gap: 7px; background: var(--cpanel,#0c0e1d);
  border: 1px solid var(--cline,#1c2040); border-radius: 999px; padding: 6px 12px 6px 7px;
  font-weight: 700; font-size: .85rem; cursor: pointer; color: var(--ctxt,#e6e8f5); flex-shrink: 0; }
.uni-tok:hover { background: #181c38; }
.uni-tok .ti { width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center;
  justify-content: center; font-size: .5rem; font-weight: 800; color: #fff; }
.uni-sub { display: flex; justify-content: space-between; font-size: .68rem;
  color: var(--cmut,#707694); margin-top: 8px; }
.uni-sub .mx { cursor: pointer; color: #a855f7; font-weight: 700; }
.uni-flip { display: flex; justify-content: center; margin: -9px 0; position: relative; z-index: 2; }
.uni-flip button { width: 38px; height: 38px; border-radius: 12px; background: var(--cpanel2,#12152b);
  border: 4px solid var(--cpanel,#0c0e1d); color: var(--ctxt,#e6e8f5); font-size: 1rem;
  cursor: pointer; transition: transform .2s; }
.uni-flip button:hover { transform: rotate(180deg); }
.uni-info { font-size: .7rem; color: var(--cmut,#707694); padding: 10px 6px 2px;
  display: flex; flex-direction: column; gap: 4px; }
.uni-info .irow { display: flex; justify-content: space-between; }
.uni-info .iv { color: var(--ctxt,#e6e8f5); }
.uni-btn { width: 100%; margin-top: 12px; padding: 15px; border: none !important;
  border-radius: 18px !important; background: linear-gradient(120deg,#f97316,#a855f7) !important;
  color: #fff !important; font-size: 1rem; font-weight: 800; cursor: pointer;
  font-family: inherit; transition: opacity .15s; }
.uni-btn:disabled { opacity: .45; cursor: not-allowed; }
.tok-menu { position: absolute; background: var(--cpanel,#0c0e1d);
  border: 1px solid var(--cline,#1c2040); border-radius: 16px; padding: 6px; z-index: 50;
  max-height: 290px; overflow-y: auto; width: 230px; box-shadow: 0 12px 40px rgba(0,0,0,.6); }
.tok-menu .tm-it { display: flex; align-items: center; gap: 9px; padding: 9px 10px;
  border-radius: 10px; cursor: pointer; font-size: .82rem; font-weight: 600; }
.tok-menu .tm-it:hover { background: var(--cpanel2,#12152b); }
.tok-menu .tm-bal { margin-left: auto; font-size: .68rem; color: var(--cmut,#707694); }
#cb-toast { position: fixed; bottom: 26px; left: 50%; transform: translateX(-50%);
  padding: 13px 24px; border-radius: 14px; font-size: .88rem; font-weight: 700; z-index: 9999;
  max-width: 92vw; text-align: center; box-shadow: 0 6px 24px rgba(0,0,0,.5);
  transition: opacity .3s; opacity: 0; pointer-events: none; }
@media (max-width: 520px) { .uni-amt { font-size: 1.35rem; } }
</style>
"""


def swap_card_html(swap_tokens: list, eff_fee_pct: float, exec_bonus: float = 0.0,
                   redirect: str = "/crypto?tab=swap",
                   default_in: str = None, default_out: str = None) -> str:
    """Return the full Uniswap-style swap card (styles + HTML + JS) for a page.

    swap_tokens: [{"sym","name","type"(cash|wsc|native),"price","balance"}, ...]
    default_in/default_out: pre-select a pair (e.g. token detail pages pass
    default_out=<that token> so the card is ready to buy it, Uniswap-style).
    """
    tokens_json = json.dumps(swap_tokens)
    d_in  = json.dumps(default_in)
    d_out = json.dumps(default_out)
    fee_note = (f'(exec bonus −{exec_bonus * 100:.0f}%)' if exec_bonus > 0 else "")
    return SWAP_CARD_STYLES + f"""
<div class="uni-card">
  <div class="uni-panel">
    <div class="plbl">You pay</div>
    <div class="uni-row">
      <input class="uni-amt" id="amt-in" type="number" min="0" step="any" placeholder="0" oninput="cbQuote()">
      <button class="uni-tok" id="tok-in" onclick="cbMenu('in', event)"></button>
    </div>
    <div class="uni-sub"><span id="bal-in"></span><span class="mx" onclick="cbMax()">MAX</span></div>
  </div>
  <div class="uni-flip"><button onclick="cbFlip()" title="Flip">⇅</button></div>
  <div class="uni-panel">
    <div class="plbl">You receive (estimated)</div>
    <div class="uni-row">
      <input class="uni-amt" id="amt-out" type="text" placeholder="0" readonly>
      <button class="uni-tok" id="tok-out" onclick="cbMenu('out', event)"></button>
    </div>
    <div class="uni-sub"><span id="bal-out"></span><span></span></div>
  </div>
  <div class="uni-info">
    <div class="irow"><span>Rate</span><span class="iv" id="i-rate">—</span></div>
    <div class="irow"><span>Exchange fee {fee_note}</span><span class="iv">{eff_fee_pct:.2f}% + gas</span></div>
    <div class="irow"><span>Government tax</span><span class="iv" style="color:#4ade80;">0.00% — untracked 🕶️</span></div>
  </div>
  <button class="uni-btn" id="swap-btn" onclick="cbSwap()" disabled>Enter an amount</button>
</div>
<div id="cb-toast"></div>
<script>
var TOKENS = {tokens_json};
var FEE = {eff_fee_pct / 100:.6f};
var CB_REDIRECT = {json.dumps(redirect)};
function cbFind(sym) {{
  for (var i = 0; i < TOKENS.length; i++) if (TOKENS[i].sym === sym) return TOKENS[i];
  return null;
}}
var tokIn  = cbFind({d_in})  || TOKENS[0];
var tokOut = cbFind({d_out}) || (TOKENS.length > 2 ? TOKENS[2] : TOKENS[1]);
if (tokIn.sym === tokOut.sym) tokIn = TOKENS[0].sym === tokOut.sym ? TOKENS[1] : TOKENS[0];

function cbToast(msg, ok) {{
  var el = document.getElementById('cb-toast');
  el.textContent = msg;
  el.style.background = ok ? '#14532d' : '#7f1d1d';
  el.style.color = ok ? '#bbf7d0' : '#fecaca';
  el.style.border = '1px solid ' + (ok ? '#22c55e' : '#ef4444');
  el.style.opacity = '1';
  clearTimeout(el._t);
  el._t = setTimeout(function() {{ el.style.opacity = '0'; }}, 4200);
}}
function tokIcon(sym) {{
  var pals = [['#f97316','#fb923c'],['#a855f7','#c084fc'],['#38bdf8','#7dd3fc'],['#22c55e','#4ade80'],
              ['#ef4444','#f87171'],['#eab308','#fde047'],['#ec4899','#f9a8d4'],['#14b8a6','#5eead4']];
  var s = 0; for (var i = 0; i < sym.length; i++) s += sym.charCodeAt(i);
  var p = pals[s % pals.length];
  return '<span class="ti" style="background:linear-gradient(135deg,' + p[0] + ',' + p[1] + ');">' + sym.slice(0,4) + '</span>';
}}
function cbRender() {{
  document.getElementById('tok-in').innerHTML  = tokIcon(tokIn.sym)  + tokIn.sym  + ' ▾';
  document.getElementById('tok-out').innerHTML = tokIcon(tokOut.sym) + tokOut.sym + ' ▾';
  document.getElementById('bal-in').textContent  = 'Balance: ' + tokIn.balance.toLocaleString();
  document.getElementById('bal-out').textContent = 'Balance: ' + tokOut.balance.toLocaleString();
  cbQuote();
}}
function cbRoute() {{
  var a = tokIn.type, b = tokOut.type;
  if (a === 'cash'   && b === 'native') return {{url: '/api/exchange/buy',  f: function(amt) {{ return {{crypto_symbol: tokOut.sym, cash_amount: amt}}; }}}};
  if (a === 'native' && b === 'cash')   return {{url: '/api/exchange/sell', f: function(amt) {{ return {{crypto_symbol: tokIn.sym, amount: amt}}; }}}};
  if (a === 'native' && b === 'native') return {{url: '/api/exchange/swap', f: function(amt) {{ return {{sell_symbol: tokIn.sym, sell_amount: amt, buy_symbol: tokOut.sym}}; }}}};
  if (a === 'native' && b === 'wsc')    return {{url: '/api/wallet/amm/native-to-wsc', f: function(amt) {{ return {{native_symbol: tokIn.sym, native_amount: amt}}; }}}};
  if (a === 'wsc'    && b === 'native') return {{url: '/api/wallet/amm/wsc-to-native', f: function(amt) {{ return {{native_symbol: tokOut.sym, wsc_amount: amt}}; }}}};
  if (a === 'wsc'    && b === 'cash')   return {{url: '/api/wallet/redeem', f: function(amt) {{ return {{amount: amt}}; }}}};
  return null;
}}
function cbQuote() {{
  var amt = parseFloat(document.getElementById('amt-in').value) || 0;
  var btn = document.getElementById('swap-btn');
  var route = cbRoute();
  if (!route) {{
    btn.disabled = true; btn.textContent = 'Pair not supported';
    document.getElementById('amt-out').value = '';
    document.getElementById('i-rate').textContent = '—';
    return;
  }}
  if (amt <= 0) {{
    btn.disabled = true; btn.textContent = 'Enter an amount';
    document.getElementById('amt-out').value = '';
    document.getElementById('i-rate').textContent = '—';
    return;
  }}
  var usdIn = amt * tokIn.price;
  var out = tokOut.price > 0 ? (usdIn * (1 - FEE)) / tokOut.price : 0;
  document.getElementById('amt-out').value = out > 0 ? out.toLocaleString(undefined, {{maximumFractionDigits: 6}}) : '';
  document.getElementById('i-rate').textContent =
    '1 ' + tokIn.sym + ' ≈ ' + (tokOut.price > 0 ? (tokIn.price / tokOut.price).toLocaleString(undefined, {{maximumFractionDigits: 6}}) : '—') + ' ' + tokOut.sym;
  if (amt > tokIn.balance) {{
    btn.disabled = true; btn.textContent = 'Insufficient ' + tokIn.sym + ' balance';
  }} else {{
    btn.disabled = false; btn.textContent = 'Swap ' + tokIn.sym + ' → ' + tokOut.sym;
  }}
}}
function cbMax() {{ document.getElementById('amt-in').value = tokIn.balance; cbQuote(); }}
function cbFlip() {{
  var t = tokIn; tokIn = tokOut; tokOut = t;
  document.getElementById('amt-in').value = '';
  cbRender();
}}
function cbMenu(side, ev) {{
  ev.stopPropagation();
  var old = document.getElementById('tok-menu'); if (old) old.remove();
  var menu = document.createElement('div');
  menu.id = 'tok-menu'; menu.className = 'tok-menu';
  TOKENS.forEach(function(t) {{
    var other = side === 'in' ? tokOut : tokIn;
    if (t.sym === other.sym) return;
    var it = document.createElement('div');
    it.className = 'tm-it';
    it.innerHTML = tokIcon(t.sym) + t.sym + '<span class="tm-bal">' + t.balance.toLocaleString() + '</span>';
    it.onclick = function() {{
      if (side === 'in') tokIn = t; else tokOut = t;
      menu.remove(); cbRender();
    }};
    menu.appendChild(it);
  }});
  var anchor = document.getElementById(side === 'in' ? 'tok-in' : 'tok-out');
  var r = anchor.getBoundingClientRect();
  menu.style.top  = (r.bottom + window.scrollY + 6) + 'px';
  menu.style.left = Math.max(8, r.right + window.scrollX - 230) + 'px';
  document.body.appendChild(menu);
  setTimeout(function() {{
    document.addEventListener('click', function h() {{ menu.remove(); document.removeEventListener('click', h); }});
  }}, 0);
}}
function cbSwap() {{
  var amt = parseFloat(document.getElementById('amt-in').value) || 0;
  var route = cbRoute();
  if (!route || amt <= 0) return;
  var btn = document.getElementById('swap-btn');
  btn.disabled = true; btn.textContent = 'Swapping…';
  var fd = new FormData();
  var fields = route.f(amt);
  for (var k in fields) fd.set(k, fields[k]);
  fd.set('ajax', '1');
  fetch(route.url, {{method: 'POST', body: fd}})
    .then(function(r) {{ return r.json(); }})
    .then(function(d) {{
      if (d.ok) {{
        cbToast(d.message || 'Swap complete!', true);
        setTimeout(function() {{ location.href = CB_REDIRECT; }}, 1400);
      }} else {{
        cbToast(d.error || d.message || 'Swap failed.', false);
        btn.disabled = false; cbQuote();
      }}
    }})
    .catch(function() {{
      cbToast('Network error — please retry.', false);
      btn.disabled = false; cbQuote();
    }});
}}
cbRender();
</script>
"""


def build_swap_tokens(player_id: int) -> tuple:
    """Build the shared swap token list + fee numbers for a player.

    Returns (swap_tokens list, eff_fee_pct, exec_bonus).
    """
    from reserve_banks import get_player_display_currency, get_usd_balance
    from counties import get_all_counties, EXCHANGE_FEE_PERCENT
    from memecoins import get_wallet_portfolio
    from wallet import get_wsc_wallet_info, WSC_SYMBOL, WSC_NAME

    disp      = get_player_display_currency(player_id)
    counties  = get_all_counties()
    portfolio = get_wallet_portfolio(player_id)
    wsc_bal   = get_wsc_wallet_info(player_id)["balance"]
    cash_bal  = get_usd_balance(player_id)

    exec_bonus = 0.0
    try:
        from executive import get_player_job_bonus, get_db as _edb_fn
        _edb = _edb_fn()
        exec_bonus = get_player_job_bonus(_edb, player_id, "crypto") or 0.0
        _edb.close()
    except Exception:
        pass
    eff_fee_pct = EXCHANGE_FEE_PERCENT * (1.0 - exec_bonus) * 100

    native_bal = {h["symbol"]: h["balance"] for h in portfolio["native_holdings"]}
    tokens = [
        {"sym": "CASH", "name": f"Cash ({disp['code']})", "type": "cash",
         "price": 1.0, "balance": round(cash_bal, 2)},
        {"sym": WSC_SYMBOL, "name": WSC_NAME, "type": "wsc",
         "price": 1.0, "balance": round(wsc_bal, 6)},
    ] + [
        {"sym": c["crypto_symbol"], "name": c["crypto_name"], "type": "native",
         "price": round(c["crypto_price"], 8),
         "balance": round(native_bal.get(c["crypto_symbol"], 0.0), 6)}
        for c in counties
    ]
    return tokens, eff_fee_pct, exec_bonus
