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
/* TW palette: deep-space bg var(--cbg,#05060f), panels var(--cpanel,#0c0e1d) / var(--cpanel2,#12152b), violet var(--accent,#a855f7), orange var(--accent-2,#f97316) */
/* Uniswap palette: same deep dark, pink accent #fc72ff, but we use TW gradient as brand */
/* Bridge to the skin system: every crypto-local var derives from the player's
   skin variables (loaded earlier in <head>), falling back to the Trust Wallet ×
   Uniswap palette when a skin doesn't define them. Skins stay fully in charge. */
:root {
  --cbg: var(--bg-page, #05060f);
  --cpanel: var(--bg-card, #0c0e1d);
  --cpanel2: var(--bg-card-2, #12152b);
  --cline: var(--border, #1c2040);
  --ctxt: var(--text-primary, #e6e8f5);
  --cmut: var(--text-muted, #707694);
  --cgrad: var(--grad-bar, linear-gradient(120deg,#f97316,#a855f7));
  --cgreen: var(--color-success, #22c55e);
  --cred: var(--color-danger, #ef4444);
  --caccent: var(--accent, #a855f7);
  --caccent2: var(--accent-2, #f97316);
  --shadow-panel: var(--shadow-md, 0 2px 24px rgba(0,0,0,.45));
  --shadow-card: var(--shadow-sm, 0 1px 8px rgba(0,0,0,.35));
  --radius-card: var(--radius-2xl, 24px);
  --radius-btn: var(--radius-pill, 999px);
  --radius-input: var(--radius-lg, 16px);
}

/* ── Reset & base ── */
*, *::before, *::after { box-sizing: border-box !important; }
body {
  background: var(--cbg) !important; color: var(--ctxt) !important;
  font-family: 'Inter','SF Pro Display','Segoe UI',system-ui,sans-serif !important;
  font-size: 14px !important; line-height: 1.5 !important;
  -webkit-font-smoothing: antialiased !important;
}
.container { max-width: 1100px !important; margin: 0 auto !important; padding: 0 16px !important; }
a { color: var(--color-sky,#38bdf8); text-decoration: none; }
a:hover { text-decoration: underline; }

/* ── Header (legacy pages) ── */
.header {
  background: var(--cpanel) !important;
  border-bottom: 1px solid var(--cline) !important;
  padding: 14px 20px !important;
  display: flex !important; align-items: center !important;
  justify-content: space-between !important;
  margin-bottom: 20px !important;
}
.header h1 { font-size: 1.1rem !important; font-weight: 800 !important; letter-spacing: .01em; margin: 0 !important; }
.nav-link { color: var(--cmut) !important; font-size: .75rem !important; font-weight: 600 !important; }
.nav-link:hover { color: var(--ctxt) !important; text-decoration: none !important; }

/* ── Cards → TW rounded wallet panels with shadow ── */
.card, .poll-card, .proposal-card, .meme-card, .wsc-card, .exchange-panel,
.governance-panel, .mining-node, .wallet-card, .swap-box {
  background: var(--cpanel) !important;
  border: 1px solid var(--cline) !important;
  border-radius: var(--radius-card) !important;
  box-shadow: var(--shadow-card) !important;
  padding: 18px 20px !important;
  margin-bottom: 12px !important;
}
.card:hover { border-color: #252850 !important; }
.card h2, .card h3 { color: var(--ctxt) !important; font-weight: 800 !important; }
.card h2 { font-size: .95rem !important; margin: 0 0 12px !important; }
.card h3 { font-size: .82rem !important; margin: 0 0 8px !important; }
.mining-node {
  background: linear-gradient(160deg,#160b2e 0%,var(--cpanel) 55%) !important;
  border-color: #2d1d57 !important;
}

/* ── Meme cards (token grid cards) — TW asset row style ── */
.meme-card {
  display: flex !important; flex-direction: column !important;
  text-decoration: none !important; color: var(--ctxt) !important;
  transition: border-color .15s, transform .12s, box-shadow .12s !important;
  cursor: pointer !important;
}
.meme-card:hover {
  border-color: var(--caccent) !important;
  transform: translateY(-2px) !important;
  box-shadow: 0 8px 32px rgba(168,85,247,.15) !important;
  text-decoration: none !important; color: var(--ctxt) !important;
}

/* ── Stats rows ── */
.stat { border-bottom: 1px solid var(--cline) !important; padding: 9px 0 !important; }
.stat-label, .info-stat-label, .cycle-stat-label { color: var(--cmut) !important; font-size: .72rem !important; text-transform: uppercase; letter-spacing: .06em; }
.stat-value, .info-stat-value, .cycle-stat-value { font-weight: 700 !important; font-size: .85rem !important; }
.positive, .stat-value.positive { color: var(--cgreen) !important; }
.negative, .stat-value.negative { color: var(--cred) !important; }
.neutral { color: var(--cmut) !important; }
.stat-value.crypto { color: #c4b5fd !important; }

/* ── Buttons → pills with exact TW sizing ── */
.btn, .vote-btn, .btn-governance, .pill-btn {
  display: inline-flex !important; align-items: center !important; justify-content: center !important;
  padding: 10px 20px !important; border-radius: var(--radius-btn) !important;
  font-weight: 700 !important; font-size: .85rem !important;
  font-family: inherit !important;
  transition: opacity .15s, transform .1s, box-shadow .15s !important;
  cursor: pointer !important; border: none !important;
  white-space: nowrap !important;
}
.btn:hover:not(:disabled) { opacity: .88 !important; transform: translateY(-1px) !important; box-shadow: 0 4px 16px rgba(0,0,0,.4) !important; }
.btn:active:not(:disabled) { transform: translateY(0) !important; }
.btn:disabled { opacity: .4 !important; cursor: not-allowed !important; }

.btn-primary, .btn-crypto, .btn-meme, .btn-buy, .btn-governance {
  background: var(--cgrad) !important; color: #fff !important;
  box-shadow: 0 2px 12px rgba(168,85,247,.25) !important;
}
.btn-secondary, .btn-cancel {
  background: var(--cpanel2) !important; color: var(--ctxt) !important;
  border: 1px solid var(--cline) !important;
}
.btn-sm { padding: 6px 14px !important; font-size: .75rem !important; }
.btn-danger, .btn-sell {
  background: #3f1120 !important; color: var(--color-danger-light,#fda4af) !important;
  border: 1px solid #881337 !important;
}

/* ── Forms → dark rounded inputs, violet focus ring ── */
.form-group { margin-bottom: 14px !important; }
.form-group label {
  display: block !important; color: var(--cmut) !important;
  font-size: .7rem !important; text-transform: uppercase;
  letter-spacing: .08em; font-weight: 700; margin-bottom: 6px !important;
}
.form-group input, .form-group select, .form-group textarea,
.burn-input-group input,
input[type="number"], input[type="text"], input[type="email"],
input[type="password"], select, textarea {
  background: var(--cpanel2) !important;
  border: 1px solid var(--cline) !important;
  border-radius: var(--radius-input) !important;
  color: var(--ctxt) !important;
  font-family: inherit !important; font-size: .88rem !important;
  padding: 11px 14px !important;
  width: 100% !important;
  transition: border-color .15s, box-shadow .15s !important;
}
.form-group input:focus, .form-group select:focus, .form-group textarea:focus,
input:focus, select:focus, textarea:focus {
  border-color: var(--caccent) !important; outline: none !important;
  box-shadow: 0 0 0 3px rgba(168,85,247,.15) !important;
}
input::placeholder, textarea::placeholder { color: #3a4060 !important; }

/* ── Tables → Uniswap borderless hover rows ── */
.table { border-collapse: collapse !important; width: 100% !important; }
.table th {
  color: var(--cmut) !important; font-size: .68rem !important;
  text-transform: uppercase; letter-spacing: .1em;
  border-bottom: 1px solid var(--cline) !important;
  padding: 10px 14px !important; font-weight: 600 !important;
}
.table td {
  border-bottom: 1px solid #0e1025 !important;
  font-size: .82rem !important; padding: 11px 14px !important;
  vertical-align: middle !important;
}
.table tr:hover td { background: var(--cpanel2) !important; }
.table tr:last-child td { border-bottom: none !important; }

/* ── Badges → pill chips ── */
.badge, .badge-meme, .badge-native, .badge-crypto, .badge-governance,
.badge-buy, .badge-sell, .badge-open, .badge-filled, .badge-cancelled,
.phase-indicator, .token-change-badge, .price-change-badge, .ticker-chip {
  display: inline-flex !important; align-items: center !important;
  border-radius: 999px !important; font-weight: 700 !important;
  font-size: .72rem !important; padding: 2px 10px !important;
  line-height: 1.6 !important;
}
.badge-success { background: var(--color-success-bg,#052e16) !important; color: var(--color-success-light,#4ade80) !important; border: 1px solid var(--color-success-dark,#14532d) !important; }
.badge-warning { background: #2e2008 !important; color: var(--color-warning-light,#fbbf24) !important; border: 1px solid #78350f !important; }
.badge-info    { background: #0b2447 !important; color: #60a5fa !important; border: 1px solid #1e40af !important; }
.badge-crypto, .badge-meme  { background: #1e1038 !important; color: #c4b5fd !important; border: 1px solid #3b1d6e !important; }
.badge-native  { background: #1c2c08 !important; color: #86efac !important; border: 1px solid #166534 !important; }
.badge-buy     { background: var(--color-success-bg,#052e16) !important; color: var(--color-success-light,#4ade80) !important; border: 1px solid var(--color-success-dark,#14532d) !important; }
.badge-sell    { background: var(--color-danger-bg,#2d0a12) !important; color: var(--color-danger-light,#fda4af) !important; border: 1px solid var(--color-danger-dark,#7f1d1d) !important; }
.badge-open    { background: #0b2447 !important; color: #93c5fd !important; border: 1px solid #1e40af !important; }
.badge-filled  { background: var(--color-success-bg,#052e16) !important; color: #6ee7b7 !important; border: 1px solid #065f46 !important; }
.badge-cancelled{ background: #1e1e2e !important; color: #6b7280 !important; border: 1px solid #374151 !important; }

/* ── Alerts ── */
.alert {
  border-radius: 16px !important; font-weight: 600 !important;
  padding: 12px 18px !important; margin-bottom: 14px !important;
  border-width: 1px !important; border-style: solid !important;
}
.alert-success { background: var(--color-success-bg,#052e16) !important; border-color: var(--color-success-dark,#14532d) !important; color: #bbf7d0 !important; }
.alert-error   { background: var(--color-danger-bg,#2d0a12) !important; border-color: var(--color-danger-dark,#7f1d1d) !important; color: var(--color-danger-light,#fecaca) !important; }
.alert-info    { background: #0b2447 !important; border-color: #1e40af !important; color: #bfdbfe !important; }
.alert-warning { background: #1c1400 !important; border-color: #78350f !important; color: #fde68a !important; }

/* ── Progress bars (supply / vote / mining) ── */
.supply-bar, .vote-bar, .mining-bar-bg {
  background: var(--cpanel2) !important; border-radius: 999px !important;
  overflow: hidden !important; height: 6px !important;
}
.supply-bar-fill, .mining-bar-fill {
  background: var(--cgrad) !important; border-radius: 999px !important;
  height: 100% !important; min-width: 2px !important;
  transition: width .4s ease !important;
}
.vote-bar-yes { background: var(--cgreen) !important; height: 100% !important; }
.vote-bar-no  { background: var(--cred) !important; height: 100% !important; }
.vote-yes { background: var(--color-success-bg,#052e16) !important; color: var(--color-success-light,#4ade80) !important; border: 1px solid var(--color-success-dark,#14532d) !important; border-radius: 999px !important; }
.vote-no  { background: var(--color-danger-bg,#2d0a12) !important; color: var(--color-danger-light,#fda4af) !important; border: 1px solid var(--color-danger-dark,#7f1d1d) !important; border-radius: 999px !important; }

/* ── Token hero / big prices ── */
.token-hero {
  background: var(--cpanel) !important; border: 1px solid var(--cline) !important;
  border-radius: 24px !important; box-shadow: var(--shadow-panel) !important;
}
.token-logo { border-radius: 50% !important; }
.token-price-big, .price-big {
  font-size: 2rem !important; font-weight: 800 !important;
  letter-spacing: -.03em !important; line-height: 1.1 !important;
}
.price-change-badge, .token-change-badge {
  font-size: .78rem !important; padding: 3px 10px !important;
  font-weight: 700 !important; border-radius: 999px !important;
}
.token-change-up   { background: var(--color-success-bg,#052e16) !important; color: var(--color-success-light,#4ade80) !important; }
.token-change-down { background: var(--color-danger-bg,#2d0a12) !important; color: var(--color-danger-light,#fda4af) !important; }
.token-change-flat { background: var(--cpanel2) !important; color: var(--cmut) !important; }

/* ── Order book (meme TDP) ── */
.order-book-side {
  background: var(--cpanel) !important; border: 1px solid var(--cline) !important;
  border-radius: 16px !important; overflow: hidden !important;
}
.bid-row { color: var(--cgreen) !important; }
.ask-row { color: var(--cred) !important; }
.depth-bar { opacity: .12 !important; border-radius: 3px !important; }
.spread-line { color: var(--cmut) !important; font-size: .75rem !important; }

/* ── Segmented tab bar (meme detail / hub) ── */
.tab-bar {
  display: flex !important;
  background: var(--cpanel) !important; border: 1px solid var(--cline) !important;
  border-radius: 999px !important; padding: 4px !important; gap: 4px !important;
  margin-bottom: 16px !important;
}
.tab-btn {
  flex: 1 !important; border-radius: 999px !important; font-weight: 700 !important;
  color: var(--cmut) !important; border: none !important; background: none !important;
  padding: 8px 14px !important; font-size: .78rem !important; cursor: pointer !important;
  font-family: inherit !important; transition: background .15s, color .15s !important;
  white-space: nowrap !important;
}
.tab-btn.active { background: var(--cgrad) !important; color: #fff !important; }
.tab-btn:hover:not(.active) { background: var(--cpanel2) !important; color: var(--ctxt) !important; }

/* ── Live ticker bar ── */
.crypto-ticker, .wallet-ticker {
  background: var(--cpanel) !important; border: 1px solid var(--cline) !important;
  border-radius: 999px !important; display: flex !important;
  align-items: center !important; gap: 10px !important;
  padding: 6px 14px !important; overflow-x: auto !important;
  margin-bottom: 12px !important; flex-wrap: nowrap !important;
}
.ticker-chip {
  display: inline-flex !important; align-items: center !important; gap: 4px !important;
  font-size: .72rem !important; padding: 3px 10px !important;
  border-radius: 999px !important; font-weight: 600 !important;
  text-decoration: none !important; white-space: nowrap !important;
  border: 1px solid var(--cline) !important;
}
.ticker-up   { color: var(--cgreen) !important; }
.ticker-down { color: var(--cred) !important; }

/* ── Holder rows (token page) ── */
.holder-row { border-bottom: 1px solid #0e1025 !important; padding: 9px 0 !important; }
.holder-row:hover { background: var(--cpanel2) !important; padding-left: 4px !important; transition: padding .1s; }

/* ── Grid helpers ── */
.grid { display: grid !important; }
/* Intrinsic columns: only form when ~real width exists for each, so narrow
   screens get one readable column even if media queries don't apply
   (WebView desktop-viewport quirks). */
.grid-2 { grid-template-columns: repeat(auto-fit, minmax(min(280px,100%),1fr)) !important; gap: 14px !important; }
.grid-3 { grid-template-columns: repeat(auto-fit, minmax(min(220px,100%),1fr)) !important; gap: 14px !important; }
.grid-4 { grid-template-columns: repeat(auto-fit, minmax(min(180px,100%),1fr)) !important; gap: 14px !important; }
@media (max-width: 640px) {
  .grid-2, .grid-3, .grid-4 { grid-template-columns: 1fr !important; }
}

/* ── Wallet balance display (big number) ── */
.wallet-balance { font-size: clamp(1rem, 4.5vw, 1.6rem) !important; font-weight: 800 !important; letter-spacing: -.02em; overflow-wrap: anywhere; }
.wallet-value   { font-size: .82rem !important; color: var(--cmut) !important; margin-top: 2px; overflow-wrap: anywhere; }

/* ── Huge-balance hardening: 16-digit ANA fortunes must never stretch the page ── */
.card, .uni-card, .grid > *, .header > * { min-width: 0 !important; }
td, th { overflow-wrap: anywhere; }
.table, table { max-width: 100% !important; }
.table-wrap { overflow-x: auto; -webkit-overflow-scrolling: touch; }
.balance-huge { font-size: clamp(1.1rem, 6vw, 2.4rem) !important; overflow-wrap: anywhere; }
@media (max-width: 640px) {
  .card, .poll-card, .meme-card, .wsc-card, .exchange-panel, .mining-node { padding: 14px !important; }
  .table { display: block; overflow-x: auto; white-space: nowrap; }
}

/* ── Privacy banner ── */
.privacy-banner {
  background: linear-gradient(120deg,#0b0b2e,#140a2e) !important;
  border: 1px solid #2d1d57 !important; border-radius: 16px !important;
  padding: 12px 18px !important; margin-bottom: 12px !important;
  display: flex !important; align-items: center !important; gap: 12px !important;
  font-size: .82rem !important;
}

/* ── Wallet balance card (wsc-card) with colored border variant ── */
.wsc-card { box-shadow: 0 0 0 1px var(--cline), var(--shadow-panel) !important; }

</style>
"""

# Standalone pill subnav (styles + auto-inject script) — included by
# CRYPTO_THEME and directly by the /crypto hub (which skips the legacy re-skin).
CRYPTO_SUBNAV = """
<style>
/* ═══ Crypto subnav — Uniswap-style pill tab bar (auto-injected) ═══ */
#crypto-subnav {
  display: flex; gap: 4px; align-items: center;
  max-width: 1100px; margin: 0 auto 18px; padding: 5px;
  background: var(--cpanel); border: 1px solid var(--cline);
  border-radius: 999px; overflow-x: auto; flex-wrap: nowrap;
  scrollbar-width: none; -ms-overflow-style: none;
  position: sticky; top: 0; z-index: 40;
  box-shadow: 0 2px 20px rgba(0,0,0,.6);
}
#crypto-subnav::-webkit-scrollbar { display: none; }
#crypto-subnav a {
  padding: 7px 16px; border-radius: 999px; font-size: .72rem; font-weight: 700;
  color: var(--cmut); text-decoration: none; white-space: nowrap;
  transition: background .15s, color .15s; flex-shrink: 0;
}
#crypto-subnav a:hover { color: var(--ctxt); background: var(--cpanel2); text-decoration: none; }
#crypto-subnav a.on {
  background: var(--cgrad); color: #fff;
  box-shadow: 0 2px 10px rgba(168,85,247,.3);
}
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

CRYPTO_THEME = CRYPTO_THEME + CRYPTO_SUBNAV


_ICON_PALETTES = [
    ("#f97316", "#fb923c"), ("#a855f7", "#c084fc"), ("#38bdf8", "#7dd3fc"),
    ("#22c55e", "#4ade80"), ("#ef4444", "#f87171"), ("#eab308", "#fde047"),
    ("#ec4899", "#f9a8d4"), ("#14b8a6", "#5eead4"),
]


def fmt_compact(n: float, decimals: int = 2) -> str:
    """Abbreviate huge balances (1.5Q, 23.4T, 980.1B…) so 16-digit fortunes
    don't stretch mobile layouts. Full precision belongs in a title attr."""
    for div, suf in ((1e15, "Q"), (1e12, "T"), (1e9, "B"), (1e6, "M")):
        if abs(n) >= div:
            return f"{n / div:,.{decimals}f}{suf}"
    return f"{n:,.{decimals}f}"


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
.uni-sub .mx { cursor: pointer; color: var(--accent,#a855f7); font-weight: 700; }
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
  border-radius: 18px !important; background: linear-gradient(120deg,var(--accent-2,#f97316),var(--accent,#a855f7)) !important;
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
    <div class="irow"><span>Government tax</span><span class="iv" style="color:var(--color-success-light,#4ade80);">0.00% — untracked 🕶️</span></div>
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
  el.style.background = ok ? 'var(--color-success-dark,#14532d)' : 'var(--color-danger-dark,#7f1d1d)';
  el.style.color = ok ? '#bbf7d0' : 'var(--color-danger-light,#fecaca)';
  el.style.border = '1px solid ' + (ok ? 'var(--color-success,#22c55e)' : 'var(--color-danger,#ef4444)');
  el.style.opacity = '1';
  clearTimeout(el._t);
  el._t = setTimeout(function() {{ el.style.opacity = '0'; }}, 4200);
}}
function tokIcon(sym) {{
  var pals = [['var(--accent-2,#f97316)','var(--color-orange,#fb923c)'],['var(--accent,#a855f7)','var(--accent,#c084fc)'],['var(--color-sky,#38bdf8)','var(--color-sky,#7dd3fc)'],['var(--color-success,#22c55e)','var(--color-success-light,#4ade80)'],
              ['var(--color-danger,#ef4444)','var(--color-danger-light,#f87171)'],['#eab308','var(--color-gold,#fde047)'],['var(--color-pink,#ec4899)','var(--color-pink,#f9a8d4)'],['#14b8a6','#5eead4']];
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
