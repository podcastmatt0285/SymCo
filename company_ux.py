"""
company_ux.py

Public-facing company pages (all use the leather ledger theme):
  GET  /sitemap              — Player-facing sitemap with live search
  GET  /company              — Company hub (links to sub-pages)
  GET  /company/whitepaper   — Game whitepaper (About Us)
  GET  /company/careers      — Careers application form
  POST /api/company/careers/apply — Submit application
  GET  /company/press-kit    — Press kit (logos, icons, description)
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Cookie, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from database import engine, SessionLocal

router = APIRouter()
Base = declarative_base()


# ── Model ────────────────────────────────────────────────────────────────────

class CareerSubmission(Base):
    __tablename__ = "career_submissions"
    id           = Column(Integer, primary_key=True, index=True)
    name         = Column(String, nullable=False)
    email        = Column(String, nullable=False)
    instagram    = Column(String, nullable=False)
    description  = Column(Text,   nullable=False)
    position_type = Column(String, nullable=False)  # "freelance" or "paid"
    submitted_at = Column(DateTime, default=datetime.utcnow)
    reviewed     = Column(Boolean, default=False)


def get_db():
    return SessionLocal()


def initialize():
    Base.metadata.create_all(bind=engine)


# ── Shared CSS / helpers ──────────────────────────────────────────────────────

_LEATHER_HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<meta name="theme-color" content="#020617">
<link rel="manifest" href="/manifest.json">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Caveat:wght@400;600;700&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    background: #1a0e06;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 40px 16px 80px;
    font-family: 'Caveat', cursive;
  }

  .ledger {
    position: relative;
    width: 100%;
    max-width: 720px;
    background: #f5ead0;
    background-image:
      repeating-linear-gradient(transparent, transparent 31px, #c9a97a55 31px, #c9a97a55 32px),
      radial-gradient(ellipse at 20% 10%, #e8d5b0 0%, #f5ead0 60%),
      radial-gradient(ellipse at 80% 90%, #dfc99a 0%, #f5ead0 60%);
    border-radius: 4px 12px 12px 4px;
    box-shadow:
      -8px 0 0 #6b3a1f,
      -14px 0 0 #3d1f0a,
      4px 4px 30px rgba(0,0,0,0.7),
      inset 0 0 60px rgba(139,90,43,0.15);
    padding: 52px 52px 52px 64px;
    color: #1a0e06;
    line-height: 2;
  }

  .ledger::before {
    content: '';
    position: absolute;
    top: 0; left: -8px;
    width: 8px; height: 100%;
    background: linear-gradient(to right, #3d1f0a, #6b3a1f);
    border-radius: 4px 0 0 4px;
  }

  .ledger::after {
    content: '';
    position: absolute;
    top: 4px; right: -4px;
    width: 100%; height: 100%;
    background: #c9a97a;
    border-radius: 4px 12px 12px 4px;
    z-index: -1;
  }

  .ledger-title {
    font-size: 2.4rem;
    font-weight: 700;
    color: #3d1f0a;
    border-bottom: 2px solid #c9a97a;
    padding-bottom: 8px;
    margin-bottom: 4px;
    letter-spacing: 0.02em;
  }

  .ledger-subtitle {
    font-size: 1.1rem;
    color: #7a5230;
    margin-bottom: 32px;
    font-style: italic;
  }

  h2 {
    font-size: 1.5rem;
    font-weight: 700;
    color: #3d1f0a;
    margin: 28px 0 4px;
    border-left: 3px solid #c9a97a;
    padding-left: 10px;
  }

  h3 {
    font-size: 1.25rem;
    font-weight: 700;
    color: #4a2510;
    margin: 18px 0 4px;
  }

  p { font-size: 1.15rem; color: #2a1505; margin-bottom: 8px; }

  ul {
    list-style: none;
    padding-left: 8px;
    margin-bottom: 8px;
  }

  ul li {
    font-size: 1.15rem;
    color: #2a1505;
    padding: 2px 0 2px 20px;
    position: relative;
  }

  ul li::before {
    content: '✦';
    position: absolute;
    left: 0;
    color: #c9a97a;
    font-size: 0.75rem;
    top: 6px;
  }

  strong { color: #3d1f0a; font-weight: 700; }
  em { color: #7a5230; }

  .back-link {
    display: inline-block;
    margin-bottom: 20px;
    font-size: 1.1rem;
    color: #6b3a1f;
    text-decoration: none;
  }
  .back-link:hover { text-decoration: underline; }

  .nav-row {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-bottom: 28px;
  }

  .nav-pill {
    font-family: 'Caveat', cursive;
    font-size: 1rem;
    color: #3d1f0a;
    background: rgba(201,169,122,0.25);
    border: 1px solid #c9a97a;
    border-radius: 20px;
    padding: 4px 16px;
    text-decoration: none;
    transition: background .2s;
  }
  .nav-pill:hover, .nav-pill.active { background: rgba(201,169,122,0.55); }

  /* form elements */
  label { font-size: 1.1rem; color: #3d1f0a; display: block; margin-bottom: 2px; }
  input[type=text], input[type=email], textarea {
    width: 100%;
    font-family: 'Caveat', cursive;
    font-size: 1.1rem;
    background: rgba(255,255,255,0.45);
    border: 1px solid #c9a97a;
    border-radius: 4px;
    padding: 6px 10px;
    color: #1a0e06;
    margin-bottom: 14px;
  }
  textarea { min-height: 120px; resize: vertical; }
  input[type=text]:focus, input[type=email]:focus, textarea:focus {
    outline: none;
    border-color: #6b3a1f;
    background: rgba(255,255,255,0.65);
  }

  .radio-row { display: flex; gap: 24px; margin-bottom: 14px; align-items: center; }
  .radio-row label { display: flex; align-items: center; gap: 6px; margin: 0; }

  .submit-btn {
    font-family: 'Caveat', cursive;
    font-size: 1.2rem;
    font-weight: 700;
    background: #6b3a1f;
    color: #f5ead0;
    border: none;
    border-radius: 6px;
    padding: 8px 28px;
    cursor: pointer;
    transition: background .2s;
  }
  .submit-btn:hover { background: #3d1f0a; }

  .msg-ok  { background: #d4edda; border: 1px solid #c9a97a; border-radius:4px; padding: 10px 14px; color:#2a1505; margin-bottom:16px; font-size:1.1rem; }
  .msg-err { background: #fde; border: 1px solid #c9a97a; border-radius:4px; padding: 10px 14px; color:#7a0000; margin-bottom:16px; font-size:1.1rem; }

  /* press kit grid */
  .icon-grid { display: flex; flex-wrap: wrap; gap: 16px; margin: 12px 0 20px; }
  .icon-card {
    background: rgba(201,169,122,0.2);
    border: 1px solid #c9a97a;
    border-radius: 6px;
    padding: 12px;
    text-align: center;
    font-size: 0.9rem;
    color: #3d1f0a;
    text-decoration: none;
  }
  .icon-card img { display: block; margin: 0 auto 6px; image-rendering: crisp-edges; }
  .icon-card:hover { background: rgba(201,169,122,0.4); }

  /* sitemap cards */
  .sitemap-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 12px;
    margin-top: 16px;
  }
  .sitemap-card {
    background: rgba(201,169,122,0.2);
    border: 1px solid #c9a97a;
    border-radius: 6px;
    padding: 12px 16px;
    text-decoration: none;
    color: #3d1f0a;
    transition: background .2s;
  }
  .sitemap-card:hover { background: rgba(201,169,122,0.45); }
  .sitemap-card .sc-title { font-size: 1.2rem; font-weight: 700; display: block; }
  .sitemap-card .sc-desc { font-size: 0.95rem; color: #7a5230; display: block; margin-top: 2px; }
  .sitemap-card.hidden { display: none; }

  .search-wrap { margin-bottom: 20px; }
  .search-wrap input {
    font-family: 'Caveat', cursive;
    font-size: 1.15rem;
    width: 100%;
    padding: 8px 14px;
    background: rgba(255,255,255,0.45);
    border: 1px solid #c9a97a;
    border-radius: 24px;
    color: #1a0e06;
  }
  .search-wrap input:focus { outline: none; border-color: #6b3a1f; background: rgba(255,255,255,0.65); }

  @media (max-width: 600px) {
    .ledger { padding: 36px 24px 36px 36px; }
    .ledger-title { font-size: 1.9rem; }
    .sitemap-grid { grid-template-columns: 1fr 1fr; }
  }
</style>"""

_LEATHER_FOOT = """
<div id="nav-loader" style="display:none;position:fixed;inset:0;z-index:9999;background:#0D0806;color:#F5F5DC;font-family:Georgia,serif;align-items:center;justify-content:center;padding:12px;">
  <div style="position:relative;width:100%;max-width:420px;padding:clamp(16px,5vw,40px);background:#1A0F0A;border:4px solid #2D1810;box-shadow:0 25px 50px rgba(0,0,0,.8);display:flex;flex-direction:column;align-items:center;box-sizing:border-box;max-height:92vh;overflow-y:auto;">
    <div style="width:min(90px,22vw);height:min(90px,22vw);flex-shrink:0;">
      <img src="/static/logo.png" alt="" style="width:100%;height:100%;object-fit:contain;filter:drop-shadow(0 0 12px rgba(229,0,0,0.4));">
    </div>
    <p style="font-size:13px;font-style:italic;color:#B08D57;margin:12px 0 6px;text-align:center;">Loading&hellip;</p>
    <div style="width:100%;height:3px;background:#2D1810;border-radius:2px;overflow:hidden;margin-top:4px;">
      <div id="nl-bar-co" style="height:100%;width:0%;background:linear-gradient(90deg,#B08D57,#e5c88a);transition:width .15s linear;border-radius:2px;"></div>
    </div>
  </div>
</div>
<script>
(function(){
  var ov=document.getElementById('nav-loader');
  var bar=document.getElementById('nl-bar-co');
  var prog=0,timer=null;
  function start(){if(timer)clearInterval(timer);prog=0;ov.style.display='flex';timer=setInterval(function(){prog+=5;if(prog>=100)prog=0;bar.style.width=prog+'%';},150);}
  function hide(){ov.style.display='none';clearInterval(timer);timer=null;}
  start();
  document.addEventListener('DOMContentLoaded',hide);
  document.addEventListener('click',function(e){
    var a=e.target.closest('a');if(!a)return;
    if(a.target==='_blank'||a.hasAttribute('download'))return;
    var h=a.getAttribute('href');if(!h||h.charAt(0)==='#'||/^(javascript|mailto|tel):/.test(h))return;
    try{var u=new URL(a.href,location.origin);if(u.origin!==location.origin)return;start();}catch(ex){}
  });
  document.addEventListener('submit',function(e){
    var f=e.target;if(!f)return;
    try{var u=new URL(f.action||location.href,location.origin);if(u.origin!==location.origin)return;start();}catch(ex){}
  });
  window.addEventListener('pageshow',function(e){if(e.persisted)hide();});
})();
</script>
</body>
</html>"""


def _page(title, subtitle, back_href, back_label, active_nav, body_html):
    nav = ""
    pages = [
        ("/sitemap",           "Sitemap"),
        ("/company/whitepaper","Whitepaper"),
        ("/company/careers",   "Careers"),
        ("/company/press-kit", "Press Kit"),
        ("/privacy-policy",    "Privacy Policy"),
    ]
    for href, label in pages:
        cls = "nav-pill active" if href == active_nav else "nav-pill"
        nav += f'<a href="{href}" class="{cls}">{label}</a>'
    return f"""{_LEATHER_HEAD}
<title>{title} — Wadsworth</title>
</head>
<body>
<div class="ledger">
  <a href="{back_href}" class="back-link">{back_label}</a>
  <div class="nav-row">{nav}</div>
  <div class="ledger-title">{title}</div>
  <div class="ledger-subtitle">{subtitle}</div>
  {body_html}
</div>
{_LEATHER_FOOT}"""


# ── /sitemap ──────────────────────────────────────────────────────────────────

SITEMAP_ENTRIES = [
    # ── Core ──────────────────────────────────────────────────────────────────
    ("/",                            "Dashboard",              "Your wealth, holdings, and live game alerts at a glance"),
    ("/stats/leaderboard",           "Leaderboard",            "See who owns the most wealth, land, and shares across the server"),
    ("/chat",                        "Global Chat",            "Live community chat — tag items, businesses, and players with # @ $ %"),
    ("/world-map",                   "World Map",              "Explore the entire game map: cities, counties, districts, and land parcels"),
    ("/events",                      "Events & Tasks",         "Active server-wide events, daily tasks, and the Founding Tester beta program"),
    ("/government",                  "Government",             "Federal treasury, sovereign bonds, fiscal policy rates, and the full city/county directory"),
    # ── Production ────────────────────────────────────────────────────────────
    ("/businesses",                  "Businesses",             "Start, manage, and automate production lines that turn raw inputs into revenue"),
    ("/inventory",                   "Inventory",              "View every commodity you hold, list items for sale, or swap goods with other players"),
    ("/inventory/swaps",             "Inventory Swaps",        "Propose or accept direct commodity-for-commodity swaps without using the open market"),
    ("/inventory/trusted-list",      "Trusted Traders",        "Manage your trusted-trader list for automatic swap approvals"),
    ("/executives",                  "Executives",             "Hire and level up NPC executives to boost production, reduce costs, and unlock features"),
    ("/executives/marketplace",      "Exec Marketplace",       "Browse executives available for hire — filter by skill, level, and specialty"),
    # ── Land & Districts ──────────────────────────────────────────────────────
    ("/land",                        "My Land",                "Your owned parcels — terrain types, zoning, and constructed businesses"),
    ("/land-market",                 "Land Market",            "Auction and buy-it-now listings for parcels across the map"),
    ("/districts",                   "Districts",              "Browse player-created districts and apply to join one for shared bonuses"),
    ("/districts/create",            "Create District",        "Found a new district on your land — set type, name, and membership rules"),
    ("/district-market",             "District Market",        "Order book for district-specific goods and specialty commodities"),
    # ── Markets & Finance ─────────────────────────────────────────────────────
    ("/market",                      "Commodity Market",       "Continuous double-auction order book for all raw and finished goods — place limit or market orders"),
    ("/brokerage/trading",           "Brokerage (WPE)",        "Wadsworth Public Exchange — trade company shares, ETFs, and IPOs"),
    ("/brokerage/companies",         "All Companies",          "Browse every IPO-listed company — share price, market cap, and ownership"),
    ("/brokerage/ipo",               "IPO",                    "Launch your company on the exchange — set share price, float, and prospectus"),
    ("/brokerage/commodities",       "Commodity Futures",      "Forward contracts and commodity-linked derivatives on the exchange"),
    ("/brokerage/annuities",         "Annuities",              "Purchase fixed-income annuity products paying periodic returns"),
    ("/brokerage/credit",            "Credit",                 "Credit ratings, debt instruments, and margin facility management"),
    ("/brokerage/governance",        "Exchange Governance",    "Vote on WPE rule proposals and exchange policy changes"),
    ("/banks",                       "Banks & Loans",          "City Bank collateral loans, reserve banks, ETF funds, and the brokerage firm"),
    ("/reserve-banks/bonds",         "Sovereign Bonds",        "Buy and manage sovereign bonds issued by reserve banks"),
    ("/reserve-banks/forex",         "Forex",                  "Live foreign exchange rates and inter-bank currency settlement"),
    ("/wallet",                      "Wallet",                 "Your WSC stable coin balance, yield farming positions, and faucet claims"),
    ("/exchange",                    "Crypto Exchange",        "Buy and sell county-native blockchain tokens and meme coins"),
    ("/memecoins",                   "Meme Coins",             "All active county meme tokens — price charts, holders, and bonding curve data"),
    ("/memecoins/launch",            "Launch Meme Coin",       "Create and deploy a new meme token on your county's bonding curve"),
    ("/gas-tracker",                 "Gas Tracker",            "Live transaction fee monitor for the county blockchain layer"),
    # ── Corporate & Stocks ────────────────────────────────────────────────────
    ("/brokerage/my-companies",      "My Companies",           "Manage your IPO-listed companies — share price, ownership, and issued shares"),
    ("/corporate-actions/dashboard", "Corporate Actions",      "Automate buybacks, stock splits, secondary offerings, and acquisition income stakes"),
    ("/brokerage/portfolio",         "Portfolio",              "Your full share portfolio — positions, unrealised gains, and dividend history"),
    ("/brokerage/shorts",            "Short Selling",          "Open and manage short positions on any listed company"),
    ("/liens",                       "Liens",                  "Outstanding financial liens on your account or ones you hold against others"),
    # ── Governance ────────────────────────────────────────────────────────────
    ("/cities",                      "Cities",                 "Join or found a city, vote in elections, manage currency policy, and raise proposals"),
    ("/city/my",                     "My City",                "Your city's dashboard — treasury, projects, elections, and member list"),
    ("/counties",                    "Counties",               "County governance, blockchain token parameters, and mining node controls"),
    ("/wcpr/list",                   "Press Room",             "Wadsworth City Press Room — official city and county announcements and breaking news"),
    # ── Social & Contracts ────────────────────────────────────────────────────
    ("/p2p",                         "P2P Contracts",          "Peer-to-peer binding trade contracts — escrow commodities, cash, land, or shares"),
    ("/p2p/dashboard",               "P2P Dashboard",          "Overview of all your active, pending, and completed P2P contracts"),
    ("/p2p/dms",                     "Direct Messages",        "Private encrypted messages between players — negotiations, deals, and coordination"),
    ("/contacts",                    "Contacts",               "Full player directory — search by name, city, or company"),
    # ── Account & Legacy ──────────────────────────────────────────────────────
    ("/estate",                      "Estate & Will",          "Draft a will to distribute your assets on death — cash, land, shares, and crypto"),
    ("/estate/heirs",                "Heirs",                  "Manage your designated heirs and their inheritance allocations"),
    ("/settings",                    "Settings",               "Account preferences, push notification controls, display currency, and security"),
    # ── Stats & Wiki ──────────────────────────────────────────────────────────
    ("/stats",                       "Stats Hub",              "Economy-wide analytics, personal performance, and production cost breakdowns"),
    ("/stats/leaderboard",           "Leaderboard",            "Ranked player standings by net worth, land, and share holdings"),
    ("/stats/economy",               "Economy Stats",          "Server-wide economic indicators — trade volume, inflation, and market activity"),
    ("/stats/personal",              "Personal Stats",         "Your own performance metrics — revenue, production output, and trade history"),
    ("/stats/items",                 "Item Stats",             "Price history, volume, and market depth for every commodity"),
    ("/stats/businesses",            "Business Stats",         "Aggregate production data and profitability across all business types"),
    ("/stats/districts",             "District Stats",         "Rankings and output data for all player-created districts"),
    ("/stats/production-costs",      "Production Costs",       "Vertical-integration cost calculator for every producible item"),
    ("/stats/wiki",                  "Wiki",                   "In-game encyclopedia — every item, business type, executive skill, and mechanic explained"),
    ("/stats/wiki/items",            "Wiki: Items",            "Searchable index of every item — category, recipe, and market data"),
    ("/stats/wiki/businesses",       "Wiki: Businesses",       "Every business type — inputs, outputs, land requirements, and costs"),
    ("/stats/wiki/executives",       "Wiki: Executives",       "All executive roles — skills, levels, and hire requirements"),
    ("/stats/wiki/districts",        "Wiki: Districts",        "District types, bonuses, and construction requirements"),
    ("/stats/wiki/banks",            "Wiki: Banks",            "Reserve bank mechanics, bond types, and forex system explained"),
    ("/stats/wiki/crypto",           "Wiki: Crypto",           "County tokens, meme coins, bonding curves, and the WSC stable coin"),
    ("/stats/wiki/counties",         "Wiki: Counties",         "County governance structure, petitions, and blockchain parameters"),
    ("/stats/wiki/city_projects",    "Wiki: City Projects",    "All city project types — costs, bonuses, and build requirements"),
    ("/stats/wiki/production-costs", "Wiki: Production Costs", "How vertical integration costs are calculated and displayed"),
    # ── Company ───────────────────────────────────────────────────────────────
    ("/sitemap",                     "Sitemap",                "Every page in the game, searchable"),
    ("/company/whitepaper",          "Whitepaper",             "Full game design document — economy architecture, mechanics, and systems overview"),
    ("/company/careers",             "Careers",                "Join the Wadsworth team — freelance and paid positions"),
    ("/company/press-kit",           "Press Kit",              "Brand assets, logos, icons, and official game description for media use"),
    ("/privacy-policy",              "Privacy Policy",         "How your data is collected, stored, and used"),
    # ── Media ─────────────────────────────────────────────────────────────────
    ("/settings?tab=audio",          "Media Center",           "MAPH (CH 46) tutorial videos and MATT (CH 28) community trading videos — two in-game broadcast channels"),
]


@router.get("/sitemap", response_class=HTMLResponse)
def player_sitemap():
    cards = ""
    for href, title, desc in SITEMAP_ENTRIES:
        cards += f"""<a href="{href}" class="sitemap-card" data-title="{title.lower()}" data-desc="{desc.lower()}">
  <span class="sc-title">{title}</span>
  <span class="sc-desc">{desc}</span>
</a>"""

    body = f"""
<div class="search-wrap">
  <input type="text" id="siteSearch" placeholder="Search pages..." oninput="filterSitemap(this.value)" autofocus>
</div>
<p style="font-size:1rem;color:#7a5230;margin-bottom:8px;" id="srCount"></p>
<div class="sitemap-grid" id="sitemapGrid">
  {cards}
</div>
<script>
function filterSitemap(q) {{
  q = q.trim().toLowerCase();
  var cards = document.querySelectorAll('.sitemap-card');
  var shown = 0;
  cards.forEach(function(c) {{
    var match = !q || c.dataset.title.includes(q) || c.dataset.desc.includes(q);
    c.classList.toggle('hidden', !match);
    if (match) shown++;
  }});
  document.getElementById('srCount').textContent = q ? shown + ' result' + (shown === 1 ? '' : 's') : '';
}}
</script>"""

    return HTMLResponse(_page(
        "Sitemap", "Every page in Wadsworth",
        "/login", "← Back to login",
        "/sitemap", body
    ))


# ── /company/whitepaper ───────────────────────────────────────────────────────

@router.get("/company/whitepaper", response_class=HTMLResponse)
def whitepaper():
    body = """
<h2>I. Abstract</h2>
<p>Wadsworth Economic Tycoon Simulator is a persistent, real-time multiplayer economic strategy game
in which players build industrial empires, participate in democratic governance, and compete within
a fully interconnected financial ecosystem. Every number in the game represents a real market
interaction — prices emerge from supply and demand, not random number generators.</p>

<h2>II. Core Economic Architecture</h2>
<p>The economy is structured across three tiers:</p>
<ul>
  <li><strong>Microeconomy</strong> — individual businesses, production lines, inventory, and commodity trading.</li>
  <li><strong>Macroeconomy</strong> — city and county governance, monetary policy, and cross-entity trade.</li>
  <li><strong>Meta-economy</strong> — cryptocurrency, reserve banking, bonds, and the Wadsworth Stable Coin (WSC).</li>
</ul>
<p>Cash is sovereign — all in-game wealth begins as <em>in-game dollars</em> earned through production
and trade. Every other asset class (land, inventory, shares, crypto) is ultimately denominated against
the dollar peg.</p>

<h2>III. Production & Commodities</h2>
<p>Players acquire land and construct businesses. Each business type consumes specific input commodities
to produce outputs. Production is tick-driven — every server tick advances all running production lines,
consuming inputs and depositing finished goods into inventory.</p>
<ul>
  <li>Over 40 commodity types spanning agriculture, mining, manufacturing, and energy.</li>
  <li>Production cost curves reward efficiency: higher-tier executives reduce waste and increase yield.</li>
  <li>Retail mode: businesses can sell direct to the public at configurable mark-ups.</li>
</ul>

<h2>IV. Market Systems</h2>
<p>Wadsworth runs three distinct exchange venues:</p>
<ul>
  <li><strong>Commodity Market</strong> — a continuous double-auction order book for all raw and finished goods.
      Limit and market orders; partial fills; live order-book depth.</li>
  <li><strong>Brokerage (WPE)</strong> — a stock exchange where players can take companies public via IPO,
      issue shares, trade equity, short-sell, lend shares, and participate in ETF pools.</li>
  <li><strong>Land Market</strong> — auction and listing system for parcels. Land has terrain types, features,
      and zoning that determine which businesses can be built on it.</li>
</ul>

<h2>V. Banking & Credit</h2>
<p>Players access the City Bank for collateralised loans against inventory and land. Interest accrues
each tick. The State Reserve Banks issue sovereign bonds and run a forex settlement layer that
automatically converts currencies at the prevailing inter-bank rate. Bond yields fluctuate with
monetary conditions — players who time the yield curve correctly are rewarded.</p>

<h2>VI. City & County Governance</h2>
<p>Players found and join cities. A city elects a Mayor via ranked-choice polling. Cities designate a
<strong>petrodollar commodity</strong> — a real in-game commodity whose market price backs the city's
currency. Cities in the same region may federate into a <strong>County</strong>, which mints a native
blockchain token (e.g., WDC) used to power the county's mining node.</p>
<ul>
  <li>Governance proposals are raised by citizens and ratified by vote.</li>
  <li>Customs fees apply when outsiders trade with city members (petrodollar conversion).</li>
  <li>Counties control token parameters: fee rate, mining reward multiplier, max supply.</li>
</ul>

<h2>VII. Cryptocurrency Layer</h2>
<p>Each county operates its own Proof-of-Deposit mining node. City currency deposited as energy
powers the miner and rewards holders with native tokens. On top of county tokens, any city member
may launch a <strong>meme coin</strong> on the county's chain — a deflationary token backed by
burned native tokens with a bonding-curve price model.</p>
<p>The <strong>Wadsworth Stable Coin (WSC)</strong> is a dollar-pegged token minted exclusively from
burned AMM swap fees. WSC is redeemable 1:1 for in-game cash and is distributed via yield farming,
a faucet, and periodic airdrops to petrodollar commodity holders.</p>

<h2>VIII. The Executive System</h2>
<p>Businesses are operated by Executives — recruitable NPCs with skill trees. Executives level up
through schooling and in-field experience. Higher-level executives unlock production bonuses,
reduce operating costs, and are required to operate the most complex facilities. The Chief
Communications Officer (CCO) unlocks the push notification and badge system.</p>

<h2>IX. Social & Contract Layer</h2>
<p>The Peer-to-Peer contract system lets any two players agree on binding in-game transfers —
commodities, cash, land, or shares — with escrowed settlement. Trusted Trade channels allow
pre-agreed commodity routes. Direct Messaging connects players for negotiation. The WCPR
(Wadsworth City Press Room) broadcasts public announcements.</p>

<h2>X. Estate & Legacy</h2>
<p>Every player account has an Estate. Before stepping away, a player can draft a Will that
distributes their assets to named beneficiaries or the Government Treasury. The death mechanic
ensures capital keeps circulating — nothing is permanently locked.</p>

<h2>XI. Technology</h2>
<p>Wadsworth runs on a Python/FastAPI backend with PostgreSQL persistence. The frontend is a
server-rendered PWA — no JavaScript framework, no external CDN dependencies for game logic.
The service worker enables offline-capable home-screen installation, push notifications,
background widget updates, and inline reply actions on Android.</p>
<p>Tick resolution is configurable per deployment. All financial operations are ACID-compliant;
critical balance updates use atomic <em>UPDATE … WHERE balance &ge; amount</em> patterns to
prevent double-spend under concurrent load.</p>
"""
    return HTMLResponse(_page(
        "Whitepaper", "Wadsworth Economic Tycoon Simulator — Design Document",
        "/login", "← Back to login",
        "/company/whitepaper", body
    ))


# ── /company/careers ──────────────────────────────────────────────────────────

@router.get("/company/careers", response_class=HTMLResponse)
def careers_page(msg: str = "", err: str = ""):
    notice = ""
    if msg:
        notice = f'<div class="msg-ok">✦ {msg}</div>'
    if err:
        notice = f'<div class="msg-err">✦ {err}</div>'

    body = f"""
{notice}
<p>Wadsworth is built by a small team obsessed with emergent economic gameplay.
If you have skills that would make the simulator richer, sharper, or more fun
we want to hear from you. Tell us what you do and how it fits.</p>

<form method="post" action="/api/company/careers/apply" style="margin-top:20px;">
  <label>Your Name *</label>
  <input type="text" name="name" placeholder="Full name or handle" required>

  <label>What you do & how it enhances Wadsworth *</label>
  <textarea name="description" placeholder="Describe your skills, background, and how you'd contribute to the game..." required></textarea>

  <label>Contact Email *</label>
  <input type="email" name="email" placeholder="your@email.com" required>

  <label>Instagram Handle *</label>
  <input type="text" name="instagram" placeholder="@yourhandle" required>

  <label>Position Type *</label>
  <div class="radio-row">
    <label><input type="radio" name="position_type" value="freelance" required> Freelance</label>
    <label><input type="radio" name="position_type" value="paid"> Paid Position</label>
  </div>

  <button type="submit" class="submit-btn">Submit Application ✦</button>
</form>
"""
    return HTMLResponse(_page(
        "Careers", "Come build with us",
        "/login", "← Back to login",
        "/company/careers", body
    ))


@router.post("/api/company/careers/apply", response_class=HTMLResponse)
def careers_apply(
    name: str = Form(...),
    email: str = Form(...),
    instagram: str = Form(...),
    description: str = Form(...),
    position_type: str = Form(...),
):
    if position_type not in ("freelance", "paid"):
        return RedirectResponse("/company/careers?err=Invalid+position+type", status_code=303)
    db = get_db()
    try:
        sub = CareerSubmission(
            name=name.strip(),
            email=email.strip(),
            instagram=instagram.strip(),
            description=description.strip(),
            position_type=position_type,
        )
        db.add(sub)
        db.commit()
    except Exception as e:
        db.rollback()
        db.close()
        return RedirectResponse(f"/company/careers?err=Submission+failed:+{str(e)[:60]}", status_code=303)
    db.close()
    return RedirectResponse("/company/careers?msg=Application+received!+We'll+be+in+touch.", status_code=303)


# ── /company/press-kit ────────────────────────────────────────────────────────

@router.get("/company/press-kit", response_class=HTMLResponse)
def press_kit():
    icons = [
        ("/static/logo.png",                                   "Logo",          "logo.png",        "auto", 80),
        ("/static/icons/icon-512.png",                         "Icon 512×512",  "icon-512.png",    512, 80),
        ("/static/icons/icon-192.png",                         "Icon 192×192",  "icon-192.png",    192, 80),
        ("/static/icons/icon-144.png",                         "Icon 144×144",  "icon-144.png",    144, 80),
        ("/static/icons/icon-96.png",                          "Icon 96×96",    "icon-96.png",     96,  80),
        ("/static/icons/icon-72.png",                          "Icon 72×72",    "icon-72.png",     72,  72),
        ("/static/icons/icon-48.png",                          "Icon 48×48",    "icon-48.png",     48,  48),
        ("/static/icons/apple-touch-icon.png",                 "Apple Touch",   "apple-touch-icon.png", 180, 80),
        ("/static/icons/android/launchericon-512x512.png",     "Android 512",   "android-512.png", 512, 80),
        ("/static/icons/android/launchericon-192x192.png",     "Android 192 (maskable)", "android-192.png", 192, 80),
    ]

    icon_html = ""
    for src, label, filename, size, disp in icons:
        icon_html += f"""<a href="{src}" download="{filename}" class="icon-card" title="Click to download">
  <img src="{src}" width="{disp}" height="{disp}" alt="{label}" style="max-width:{disp}px;max-height:{disp}px;">
  <div>{label}</div>
  <div style="font-size:0.8rem;color:#7a5230;">↓ download</div>
</a>"""

    body = f"""
<p>All assets below are provided for press, editorial, and promotional use.
Click any image to download.</p>

<h2>I. Brand Assets</h2>
<div class="icon-grid">{icon_html}</div>

<h2>II. About the Game</h2>
<p><strong>Wadsworth Economic Tycoon Simulator</strong> is a persistent real-time multiplayer
economic strategy game. Players build industrial empires, trade commodities, manage equity
portfolios, govern cities, operate county blockchains, and compete on a fully interconnected
financial leaderboard.</p>
<ul>
  <li>Genre: Economic simulation / multiplayer strategy</li>
  <li>Platform: Web (PWA), Android (TWA)</li>
  <li>Availability: Open access at <strong>wadsworth.cc</strong></li>
  <li>Player count: Persistent multiplayer, open world</li>
  <li>Tick-driven real-time simulation engine</li>
</ul>

<h2>III. Key Features</h2>
<ul>
  <li>Continuous double-auction commodity market</li>
  <li>Live stock exchange with IPOs, shorts, and ETFs</li>
  <li>Peer-to-peer land market with terrain and zoning</li>
  <li>City and county governance with democratic voting</li>
  <li>County-native blockchain tokens and meme coins</li>
  <li>Wadsworth Stable Coin (WSC) — dollar-pegged DeFi layer</li>
  <li>Reserve banks, sovereign bonds, and forex</li>
  <li>Full PWA: home-screen install, push notifications, widgets</li>
</ul>

<h2>IV. Technical</h2>
<ul>
  <li>Backend: Python / FastAPI / PostgreSQL</li>
  <li>Frontend: Server-rendered PWA, no JS framework</li>
  <li>Hosting: Persistent cloud deployment</li>
</ul>
"""
    return HTMLResponse(_page(
        "Press Kit", "Media assets & game information",
        "/login", "← Back to login",
        "/company/press-kit", body
    ))
