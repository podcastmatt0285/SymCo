"""
wiki.py
Wiki media management (YouTube tutorials & audio deep dives).
DB-backed replacement for wiki_media.json — supports categories,
pinning, ordering, and proper HTML sanitization.
"""

import html
import json
import os
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from database import engine, SessionLocal

Base = declarative_base()

WIKI_KINDS = ("video", "audio")
WIKI_CATEGORIES = (
    "getting-started",
    "economy",
    "land",
    "banks",
    "markets",
    "businesses",
    "districts",
    "institutions",
    "cities",
    "advanced",
    "reference",
)
CATEGORY_LABELS = {
    "getting-started": "Getting Started",
    "economy":         "Economy",
    "land":            "Land",
    "banks":           "Banks",
    "markets":         "Markets",
    "businesses":      "Businesses",
    "districts":       "Districts",
    "institutions":    "Institutions & Mints",
    "cities":          "Cities & Counties",
    "advanced":        "Advanced",
    "reference":       "Reference",
}

_WIKI_JSON_PATH = os.path.join(os.path.dirname(__file__), "wiki_media.json")


class WikiMedia(Base):
    __tablename__ = "wiki_media"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    youtube_id  = Column(String(20), nullable=False)
    kind        = Column(String(10), nullable=False, default="video")  # video | audio
    title       = Column(String(200), nullable=False)
    description = Column(Text, default="")
    category    = Column(String(40), default="reference")
    sort_order  = Column(Integer, default=0)
    pinned      = Column(Boolean, default=False)
    created_at  = Column(DateTime, default=datetime.utcnow)
    created_by  = Column(Integer, default=0)


def _db():
    return SessionLocal()


def _s(text) -> str:
    """Sanitize user input — strip HTML so descriptions can't inject scripts."""
    return html.escape(str(text or "").strip())


def initialize():
    Base.metadata.create_all(bind=engine)
    _migrate_from_json()
    _seed_land_grant_entry()
    _seed_annuity_entries()
    _seed_index_challenge_entry()
    _seed_institution_entries()
    _seed_npc_currency_mandate_entry()
    _seed_market_indices_entry()
    _seed_cities_counties_entries()
    _seed_crypto_entries()
    _seed_wsc_entries()


def _seed_land_grant_entry():
    db = _db()
    try:
        exists = db.query(WikiMedia).filter(WikiMedia.title == "Federal Development Grant").first()
        if exists:
            return
        max_order = db.query(WikiMedia).count()
        db.add(WikiMedia(
            youtube_id="",
            kind="video",
            title="Federal Development Grant",
            description=(
                "The Federal Development Grant is a monthly competition where players spend 425 trophies "
                "to enter and compete on net worth growth percentage over the event window.\n\n"
                "How it works:\n"
                "1. Pay 425 trophies to enter — this is deducted from your trophy count and affects your rank.\n"
                "2. Your net worth is snapshotted at entry time.\n"
                "3. At month end, all entrants are ranked by how much their net worth grew (%) since they entered.\n"
                "4. Top performers win government-owned land plots, matched to your most common terrain type:\n"
                "   • Platinum (top 1): 20 plots + 100 trophies\n"
                "   • Gold (top 2-4): 15 plots + 50 trophies\n"
                "   • Silver (top 5-11): 13 plots + 25 trophies\n"
                "   • Bronze (top 12-26): 10 plots + 10 trophies\n\n"
                "Strategy tips:\n"
                "• Enter early to maximize the growth window.\n"
                "• Winning 10–20 plots gives you the footprint for a full district.\n"
                "• Plots are government-seized land from bankrupt players — they go to active builders.\n"
                "• Land hoarding tax applies to all plots you own, including granted ones.\n"
                "• Executives with the Land Grant Program perk (VP of County Relations) reduce all taxes by 20%, "
                "lowering the cost of holding many plots after winning."
            ),
            category="land",
            sort_order=max_order,
            pinned=False,
        ))
        db.commit()
        print("[Wiki] Seeded Federal Development Grant entry")
    except Exception as e:
        db.rollback()
        print(f"[Wiki] Seed land grant error: {e}")
    finally:
        db.close()


def _seed_annuity_entries():
    _ANNUITY_ENTRIES = [
        (
            "What is an Annuity",
            "An annuity is a financial contract where you pay a lump sum (or series of contributions) "
            "to the Wadsworth Brokerage Firm in exchange for guaranteed fixed income payments over a set term.\n\n"
            "Key concepts:\n"
            "• Premium — the upfront amount you pay to open the contract.\n"
            "• Payout — the fixed periodic payments you receive during the payout phase.\n"
            "• Term — the length of the payout period (30, 90, 180, or 365 game-days).\n"
            "• Rate — the annual interest rate applied to your principal (8%–15% depending on term).\n\n"
            "Payments are made in your legal tender — if your account uses JPY, EUR, or another currency, "
            "annuity payouts are automatically converted and credited in that currency.\n\n"
            "Taxes apply to each payment:\n"
            "• Non-qualified: 15% tax on the interest portion only (principal returned tax-free).\n"
            "• Qualified: 20% tax on the full payment, but no 0.25% issuance fee at opening.\n\n"
            "Open an annuity at Brokerage → Annuity Contracts.",
        ),
        (
            "Immediate vs Deferred Annuities",
            "Wadsworth offers two annuity structures:\n\n"
            "IMMEDIATE ANNUITY (SPIA — Single Premium Immediate Annuity)\n"
            "• You pay a single lump-sum premium (minimum 10,000).\n"
            "• Payments start at the very next payment interval.\n"
            "• Choose your term (30/90/180/365 days) and frequency (weekly or monthly).\n"
            "• Longer terms earn higher rates: 30d = 8%, 90d = 10%, 180d = 12%, 365d = 15%.\n"
            "• Good for players who want income to start right away.\n\n"
            "DEFERRED ANNUITY\n"
            "• Open with 0 deposit or an initial amount (minimum 1,000 if depositing at opening).\n"
            "• Add contributions any time (minimum 100 per contribution).\n"
            "• Balance earns 5% annual interest, credited monthly during accumulation.\n"
            "• When your balance reaches 5,000 or more, click Annuitize to convert to a payout stream.\n"
            "• You choose the payout term and frequency at annuitization time.\n"
            "• Set an accumulation term for automatic annuitization at the end of the term.\n\n"
            "Strategy: Use deferred annuities to build up a larger principal over time before locking in "
            "payments, or use an immediate annuity for instant guaranteed income from idle capital.",
        ),
        (
            "Annuity Surrender Charges",
            "You can exit any annuity early by surrendering it, but a surrender charge may apply.\n\n"
            "How surrender charges work:\n"
            "• The charge is based on how long ago the contract was opened.\n"
            "• Charge schedule: Year 1 = 7%, Year 2 = 6%, Year 3 = 5%, Year 4 = 4%, Year 5 = 3%, "
            "Year 6 = 2%, Year 7 = 1%, Year 8+ = 0% (no charge).\n"
            "• Each year in game time equates to approximately 365 in-game days.\n\n"
            "Free withdrawal allowance:\n"
            "• Each contract year, you may withdraw up to 10% of the contract value with no surrender charge.\n"
            "• This resets at the start of each new contract year.\n\n"
            "Surrender payout:\n"
            "• For accumulation-phase contracts: base = current accumulated value.\n"
            "• For payout-phase contracts: base = remaining present value of future payments.\n"
            "• Payout = free portion + charged portion × (1 − charge rate).\n\n"
            "Tip: If you need liquidity, try using the 10% free withdrawal first rather than a full surrender, "
            "especially if you are still within the first few contract years.",
        ),
        (
            "Annuity Tax Treatment",
            "Annuity income is taxable in Wadsworth. The tax treatment depends on whether your contract "
            "is qualified or non-qualified.\n\n"
            "NON-QUALIFIED ANNUITY\n"
            "• 0.25% issuance fee charged at contract opening (paid to the government reserve).\n"
            "• Only the interest portion of each payment is taxed at 15%.\n"
            "• Example: 100 payment, 60 principal return + 40 interest → tax = 40 × 15% = 6.00.\n"
            "• Net payment to you: 94.00.\n\n"
            "QUALIFIED ANNUITY\n"
            "• No issuance fee at opening.\n"
            "• The full payment is taxed at 20%.\n"
            "• Example: 100 payment → tax = 20.00, net to you = 80.00.\n\n"
            "Which is better?\n"
            "• Non-qualified wins when most of your payment is principal return (early in the payout stream).\n"
            "• Qualified wins when the interest portion is high relative to principal (long-term, high-rate contracts).\n\n"
            "Executive bonus: Banking-role executives boost your net payout by their bonus percentage, "
            "applied before tax is deducted — hire a VP of Finance or CFO with banking skills to increase income.",
        ),
    ]

    db = _db()
    try:
        for title, description in _ANNUITY_ENTRIES:
            if db.query(WikiMedia).filter(WikiMedia.title == title).first():
                continue
            max_order = db.query(WikiMedia).count()
            db.add(WikiMedia(
                youtube_id="",
                kind="video",
                title=title,
                description=description,
                category="banks",
                sort_order=max_order,
                pinned=False,
            ))
        db.commit()
        print("[Wiki] Seeded annuity entries")
    except Exception as e:
        db.rollback()
        print(f"[Wiki] Seed annuity error: {e}")
    finally:
        db.close()


def _seed_institution_entries():
    _INSTITUTION_ENTRIES = [
        (
            "Institutions & Land Sacrifice",
            "Institutions are subscriber-exclusive mega-facilities — the prestige tier above districts. "
            "They are forged by permanently SACRIFICING land plots, not by buying them.\n\n"
            "How it works:\n"
            "• You sacrifice a number of plots set by a Fibonacci progression: 5, then 8, then 13, then 21…\n"
            "• Each successive institution you build requires the next Fibonacci count of plots.\n"
            "• Unlike district merges, the sacrificed plots may be EMPTY — they don't need a business on them.\n"
            "• Plots from DIFFERENT terrains can be mixed freely in a single sacrifice.\n"
            "• Tutorial-reward plots cannot be sacrificed.\n"
            "• There is a cash cost too, which scales 1.25× with each institution you've already built.\n\n"
            "The sacrificed land is destroyed and any businesses on it are removed with no refund, so plan "
            "the sacrifice carefully. In exchange you receive a single large institution plot that hosts a "
            "facility ordinary land can't — currently the Mint.\n\n"
            "Requires an active Wadsworth Pro subscription. Build one at Land → Institutions.",
        ),
        (
            "The Mint & Coinage",
            "The Mint is the first Institution type. It strikes physical precious-metal coinage — real, "
            "spendable in-game currencies whose value is pegged live to commodity-market metal prices.\n\n"
            "Six coinages, one per Mint variant:\n"
            "• AU24 — pure 24-karat gold (99.9% gold)\n"
            "• AU22 — 22-karat gold (22 parts gold, 2 parts copper)\n"
            "• AG999 — fine silver (99.9% silver)\n"
            "• AG925 — sterling silver (92.5% silver, 7.5% copper)\n"
            "• PT9995 — investment-grade platinum (99.95%)\n"
            "• PT950 — 95% platinum, 5% copper\n\n"
            "Each production cycle the Mint consumes the backing metals (plus energy and paper) and credits "
            "the equivalent coinage straight into your currency balance. The amount minted equals the live "
            "USD value of the metal consumed divided by the coin's metal peg — so 10 gold always strikes "
            "exactly 10 AU24, regardless of the gold price at the time.\n\n"
            "Build a Mint on a vacant institution at Land → Institutions → Open → Build Mint.",
        ),
        (
            "Hard Money & Demurrage",
            "Coinage is deliberately designed as HARD MONEY — its supply cannot be inflated.\n\n"
            "The only way coinage is ever created is by physically minting it from real metals you own. "
            "There is no other issuance path:\n"
            "• USD income is never auto-converted into coinage — earnings always land in USD.\n"
            "• Coinage bonds can never pay positive interest. Their yield band is capped at zero.\n"
            "• In fact the default coinage bond yield is NEGATIVE (demurrage): holding a coinage bond slowly "
            "costs you, exactly like paying to store physical bullion in a vault.\n\n"
            "This is the in-game gold standard: to acquire more coinage you must run a Mint and consume "
            "metal. No mint, no new coins. The result is a sound, scarce currency backed 1:1 by the metals "
            "spent to create it.\n\n"
            "Anyone may buy and trade coinage bonds, but only Pro subscribers can set a coinage as their "
            "legal tender (the currency their income is paid and spent in).",
        ),
        (
            "Institution Taxes",
            "Like districts, every Institution pays a monthly tax to the federal government, charged "
            "automatically when the in-game month rolls over.\n\n"
            "• The tax scales with the institution's total size (the combined size of the sacrificed plots).\n"
            "• Payment is taken in your legal tender and routed to the government reserve.\n"
            "• Executive bonuses that reduce DISTRICT taxes also reduce institution taxes — a VP with the "
            "right 'districts' or 'taxes' ability can cut the bill by up to 95%.\n"
            "• If you can't afford the tax you'll get a push notification; keep your account funded to avoid "
            "falling behind.\n\n"
            "Every charge is recorded in your transaction ledger under the Institutions filter, and minting "
            "events appear there too.",
        ),
    ]

    db = _db()
    try:
        for title, description in _INSTITUTION_ENTRIES:
            if db.query(WikiMedia).filter(WikiMedia.title == title).first():
                continue
            max_order = db.query(WikiMedia).count()
            db.add(WikiMedia(
                youtube_id="",
                kind="video",
                title=title,
                description=description,
                category="institutions",
                sort_order=max_order,
                pinned=False,
            ))
        db.commit()
        print("[Wiki] Seeded institution entries")
    except Exception as e:
        db.rollback()
        print(f"[Wiki] Seed institution error: {e}")
    finally:
        db.close()


def _seed_index_challenge_entry():
    db = _db()
    try:
        if db.query(WikiMedia).filter(WikiMedia.title == "Index Challenge Event").first():
            return
        max_order = db.query(WikiMedia).count()
        db.add(WikiMedia(
            youtube_id="",
            kind="video",
            title="Index Challenge Event",
            description=(
                "The Index Challenge is a monthly event that rewards players for crossing the WBC-50 Top 50 "
                "index boundary — in whichever direction they don't currently occupy.\n\n"
                "How it works:\n"
                "• When the event goes live, the system snapshots which player companies are in the WBC-50 index.\n"
                "• Players OUTSIDE the index must ENTER the Top 50 to earn the trophy reward.\n"
                "• Players INSIDE the index must EXIT the Top 50 to earn the trophy reward.\n"
                "• The challenge is personalised — your events page shows whether your goal is to Enter or Exit.\n\n"
                "How the WBC-50 works:\n"
                "• The WBC-50 (Wadsworth Blue-Chip 50) index tracks the top 50 publicly listed companies by market cap.\n"
                "• The index rebalances periodically as stock prices change.\n"
                "• Every rebalance where your company crosses the in/out boundary counts as progress.\n\n"
                "Earning the reward:\n"
                "• Progress is tracked automatically — you don't need to do anything except hold/grow your company.\n"
                "• When the rebalance confirms you've crossed in the correct direction, the task completes (1/1).\n"
                "• You receive the trophy reward instantly, plus an in-game banner notification.\n\n"
                "Strategy tips:\n"
                "• If you need to ENTER: buy shares of your own company (buyback program) to boost market cap, "
                "or expand operations to drive revenue and valuation growth.\n"
                "• If you need to EXIT: dilute the share price by issuing new shares, or let other companies "
                "overtake yours in market cap without intervention.\n"
                "• The event is monthly only — there is one chance per event window.\n"
                "• NPC companies also participate in the index, so their valuations affect whether your rank "
                "is above or below the boundary.\n\n"
                "Note: NPCs cannot complete this event — only real player companies count."
            ),
            category="advanced",
            sort_order=max_order,
            pinned=False,
        ))
        db.commit()
        print("[Wiki] Seeded Index Challenge Event entry")
    except Exception as e:
        db.rollback()
        print(f"[Wiki] Seed index challenge error: {e}")
    finally:
        db.close()


def _seed_npc_currency_mandate_entry():
    db = _db()
    try:
        if db.query(WikiMedia).filter(WikiMedia.title == "NPC Currency Mandate Event").first():
            return
        max_order = db.query(WikiMedia).count()
        db.add(WikiMedia(
            youtube_id="",
            kind="video",
            title="NPC Currency Mandate Event",
            description=(
                "The NPC Currency Mandate is a special government event that forces all NPC businesses to "
                "switch their legal tender to a currency chosen by the admin.\n\n"
                "What it does:\n"
                "• When the event goes live, every NPC business is run through the EXACT same legal-tender "
                "switch a human player uses — the only difference is an admin override that waives the switch "
                "cooldown and the Pro-subscriber requirement for coinage.\n"
                "• Just like a player switch, each NPC's existing currency reserves are converted into the "
                "new tender at the live forex rate (a repatriation fee plus forex fees apply), and the NPC "
                "then earns, holds, spends and pays hoarding tax in the new currency from then on.\n"
                "• The switch is permanent — NPCs stay on the new currency after the event window closes.\n"
                "• A future NPC Currency Mandate event can switch NPCs to a different currency again.\n\n"
                "What changes in the market:\n"
                "• With ~97 NPCs converting their reserves at once, the forex demand for the mandated "
                "currency spikes — nudging its exchange rate up and shifting its reserve-bank bond yields, "
                "which real players trade against.\n"
                "• NPC legal tender appears on their profile and in currency stats pages.\n"
                "• The government ledger records how many NPCs were converted and to which currency.\n"
                "• A mass NPC currency shift is a genuine government signal about which currencies the "
                "administration favours — and it has real teeth, because that much cash flow moving into a "
                "currency measurably affects its valuation.\n\n"
                "Available currencies:\n"
                "• All 16 fiat currencies (USD, JPY, EUR, GBP, CHF, CNY, INR, RUB, KRW, MXP, BRL, ZAR, "
                "TRY, SAR, AED, ANA) — each is a full, real switch.\n"
                "• All 6 metal coinage currencies (AU24, AU22, AG999, AG925, PT9995, PT950). Coinage is "
                "hard money — exactly as when a player switches to a coin currency, the NPC's existing "
                "reserves are converted into a queued coinage redemption IOU (filled as the bank acquires "
                "metal), while future income continues to land in USD because coins can only be created by "
                "minting.\n\n"
                "How to trigger it:\n"
                "• Admins create the event from /admin/events using the NPC Currency Mandate quick-form card.\n"
                "• Select the target currency, set a start date, and optionally set an end date for the "
                "event window display. Activate immediately or schedule for a future time.\n"
                "• The event fires once at start_at and is not repeating.\n\n"
                "Strategic implications:\n"
                "• An NPC mandate to a high-yield currency (e.g. TRY, RUB) signals an inflationary "
                "environment — players may want to hedge by buying bonds in that currency.\n"
                "• An NPC mandate to a stable safe-haven currency (CHF, JPY) signals risk-off conditions.\n"
                "• A coinage mandate (AU24) is a strong hard-money signal — expect metal commodity "
                "demand to spike as players respond."
            ),
            category="advanced",
            sort_order=max_order,
            pinned=False,
        ))
        db.commit()
        print("[Wiki] Seeded NPC Currency Mandate Event entry")
    except Exception as e:
        db.rollback()
        print(f"[Wiki] Seed NPC currency mandate error: {e}")
    finally:
        db.close()


def _migrate_from_json():
    if not os.path.exists(_WIKI_JSON_PATH):
        return
    db = _db()
    try:
        if db.query(WikiMedia).count() > 0:
            return
        with open(_WIKI_JSON_PATH) as f:
            data = json.load(f)
        order = 0
        for entry in data.get("videos", []):
            db.add(WikiMedia(
                youtube_id=entry.get("youtube_id", ""),
                kind="video",
                title=entry.get("title", ""),
                description=entry.get("description", ""),
                category="reference",
                sort_order=order,
            ))
            order += 1
        for entry in data.get("audio", []):
            db.add(WikiMedia(
                youtube_id=entry.get("youtube_id", ""),
                kind="audio",
                title=entry.get("title", ""),
                description=entry.get("description", ""),
                category="reference",
                sort_order=order,
            ))
            order += 1
        db.commit()
        print(f"[Wiki] Migrated {order} entries from wiki_media.json")
    except Exception as e:
        print(f"[Wiki] Migration error: {e}")
    finally:
        db.close()


def _to_dict(e: WikiMedia) -> dict:
    return {
        "id":          e.id,
        "youtube_id":  e.youtube_id,
        "kind":        e.kind,
        "title":       e.title,
        "description": e.description,
        "category":    e.category or "reference",
        "sort_order":  e.sort_order,
        "pinned":      bool(e.pinned),
        "created_at":  e.created_at.isoformat() if e.created_at else "",
    }


def list_entries(kind: str = None, category: str = None) -> list:
    db = _db()
    try:
        q = db.query(WikiMedia)
        if kind:
            q = q.filter(WikiMedia.kind == kind)
        if category:
            q = q.filter(WikiMedia.category == category)
        q = q.order_by(WikiMedia.pinned.desc(),
                       WikiMedia.sort_order.asc(),
                       WikiMedia.id.asc())
        return [_to_dict(e) for e in q.all()]
    finally:
        db.close()


def add_entry(youtube_id: str, kind: str, title: str, description: str,
              category: str, created_by: int = 0) -> dict:
    db = _db()
    try:
        max_order = db.query(WikiMedia).count()
        entry = WikiMedia(
            youtube_id=youtube_id,
            kind=kind if kind in WIKI_KINDS else "video",
            title=_s(title),
            description=_s(description),
            category=category if category in WIKI_CATEGORIES else "reference",
            sort_order=max_order,
            created_by=created_by,
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return _to_dict(entry)
    finally:
        db.close()


def update_entry(entry_id: int, **kwargs) -> bool:
    db = _db()
    try:
        entry = db.query(WikiMedia).filter(WikiMedia.id == entry_id).first()
        if not entry:
            return False
        if "title" in kwargs:
            entry.title = _s(kwargs["title"])
        if "description" in kwargs:
            entry.description = _s(kwargs["description"])
        if "category" in kwargs and kwargs["category"] in WIKI_CATEGORIES:
            entry.category = kwargs["category"]
        if "pinned" in kwargs:
            entry.pinned = bool(kwargs["pinned"])
        if "sort_order" in kwargs:
            entry.sort_order = int(kwargs["sort_order"])
        db.commit()
        return True
    finally:
        db.close()


def delete_entry(entry_id: int) -> bool:
    db = _db()
    try:
        entry = db.query(WikiMedia).filter(WikiMedia.id == entry_id).first()
        if not entry:
            return False
        db.delete(entry)
        db.commit()
        return True
    finally:
        db.close()


def move_entry(entry_id: int, direction: int):
    """Move entry up (-1) or down (+1) within its kind's sort order."""
    db = _db()
    try:
        entry = db.query(WikiMedia).filter(WikiMedia.id == entry_id).first()
        if not entry:
            return
        entries = (db.query(WikiMedia)
                   .filter(WikiMedia.kind == entry.kind)
                   .order_by(WikiMedia.pinned.desc(),
                             WikiMedia.sort_order.asc(),
                             WikiMedia.id.asc())
                   .all())
        idx = next((i for i, e in enumerate(entries) if e.id == entry_id), None)
        if idx is None:
            return
        swap_idx = idx + direction
        if 0 <= swap_idx < len(entries):
            entries[idx].sort_order, entries[swap_idx].sort_order = (
                entries[swap_idx].sort_order, entries[idx].sort_order
            )
            db.commit()
    finally:
        db.close()


def _seed_market_indices_entry():
    db = _db()
    try:
        if db.query(WikiMedia).filter(WikiMedia.title == "The 19 Market Indices Explained").first():
            return
        max_order = db.query(WikiMedia).count()
        db.add(WikiMedia(
            youtube_id="",
            kind="video",
            title="The 19 Market Indices Explained",
            description=(
                "Wadsworth tracks 19 live composite indices that update every 10 minutes. They are "
                "viewable by everyone — even logged-out visitors — from the Market Indices page "
                "(/banks/indices). Every index has 30-day history, candlestick charts, a composition "
                "breakdown, and related-index links. All dollar values are computed in USD and shown "
                "in your chosen display currency.\n\n"
                "EQUITY & CORPORATE\n"
                "• WBC-50 (Wadsworth Blue-Chip 50) — combined market capitalization of the 50 most "
                "valuable enterprises: public companies (shares outstanding × share price) plus NPC "
                "private businesses (all currency holdings valued in USD + land value). The flagship "
                "index; the WBC-50 Index Fund ETF tracks it, and the monthly Index Challenge event "
                "rewards entering or exiting it.\n"
                "• CDI (Corporate Dilution Index) — ratio of new shares issued to shares bought back. "
                "Rising CDI means companies are diluting shareholders; falling means buybacks dominate.\n"
                "• GSI (Global Solvency Index) — aggregate reserves of the banking system: ETF "
                "banks plus the 16 State Reserve Banks, whose foreign-currency reserves are valued "
                "in USD at live forex rates. Falling GSI warns of systemic stress.\n\n"
                "LAND & REAL ESTATE\n"
                "• GLVI (Global Land Valuation Index) — the TOTAL value of all player-owned real "
                "estate: raw plots plus merged districts (monthly tax × 120). Rising GLVI = the "
                "map's property wealth is growing. The per-plot average is on the detail page.\n"
                "• REGI (Real Estate Gentrification Index) — ratio of raw plots to merged district "
                "plots. Falling REGI means more land is being upgraded into districts.\n"
                "• NSCI (Neighborhood Services Cost Index) — average price of district-market "
                "services (hotel nights, casino packages, port leases…). The cost-of-living gauge.\n\n"
                "CURRENCY, CRYPTO & BANKING\n"
                "• RBYC (Reserve Bank Yield Composite) — average bond yield across all 16 State "
                "Reserve Banks. The economy's interest-rate dial: NPC currency mandates and heavy "
                "bond buying move it.\n"
                "• CCC (County Crypto Composite) — total market cap of all county layer-1 tokens.\n"
                "• WMRI (WSC Minting Rate Index) — WSC stablecoin supply: total minted, circulating, "
                "and pool distribution.\n\n"
                "LABOR & CONTRACTS\n"
                "• EPI (Executive Payroll Index) — average hourly wage of the executive workforce. "
                "Wage inflation gauge; raises from aging executives push it up.\n"
                "• PCVI (P2P Contract Velocity Index) — total value flowing through player-to-player "
                "contracts. High PCVI = an active deal-making economy.\n\n"
                "COMMODITIES & PRODUCTION\n"
                "• AMP (Average Market Price) — broad average of commodity market prices. The "
                "headline inflation number.\n"
                "• ASI (Agricultural Staples Index) — basket of farm staples (wheat, corn, etc.).\n"
                "• SEED (Seed Inventory Index) — seed stock across the economy; a leading indicator "
                "of future agricultural output.\n"
                "• BEE (Bee Index) — total bee inventory. Bees pollinate; collapse here precedes "
                "crop problems.\n"
                "• GPI (Grass & Pollen Index) — grass and pollen stocks, the inputs to the "
                "pollination chain.\n"
                "• WEI (Water & Energy Index) — water and energy prices, the universal production "
                "inputs. Rising WEI squeezes every manufacturer's margins.\n"
                "• GDSI (Global Defense Spending Index) — military hardware market activity "
                "(weapons, vehicles, aircraft, naval).\n\n"
                "SENTIMENT\n"
                "• GFI (Greed & Fear Index) — a 0–100 sentiment gauge built from five live signals: "
                "WBC-50 momentum vs its 30-day average, market breadth (share of companies above IPO "
                "price), corporate actions (buybacks vs issuance), P2P velocity, and 24-hour trade "
                "volume. Below 25 = Extreme Fear, 25–44 Fear, 45–55 Neutral, 56–75 Greed, above 75 "
                "= Extreme Greed. A contrarian indicator — extreme fear has historically preceded "
                "recoveries.\n\n"
                "READING THE PAGE\n"
                "• Each card shows the current value, 24-hour change, and a sparkline.\n"
                "• Detail pages add 24h/7d/30d performance chips, hourly candlesticks, volatility, "
                "and the index's composition breakdown.\n"
                "• Index values are recalculated every 10 minutes from live game data — nothing is "
                "simulated or random.\n\n"
                "STRATEGY\n"
                "• Watch RBYC before buying bonds: a falling composite means yields are compressing.\n"
                "• Rising WEI + rising AMP = inflationary squeeze; raise your retail prices.\n"
                "• GFI extremes are entry/exit signals for the stock market.\n"
                "• SEED and BEE lead ASI: shortages upstream show up in food prices weeks later.\n"
                "• The Index Challenge event (monthly) pays trophies for crossing the WBC-50 boundary "
                "in either direction — grow market cap to enter, or divest to exit."
            ),
            category="banks",
            sort_order=max_order,
            pinned=False,
        ))
        db.commit()
        print("[Wiki] Seeded Market Indices entry")
    except Exception as e:
        db.rollback()
        print(f"[Wiki] Seed market indices error: {e}")
    finally:
        db.close()


# ===========================================================================
# CITIES & COUNTIES
# ===========================================================================

def _seed_cities_counties_entries():
    _ENTRIES = [
        (
            "Cities — Founding & Governance",
            "cities",
            "A city is a player-run collective that pools resources, earns shared tax revenue, "
            "and unlocks county-level features.\n\n"
            "REQUIREMENTS TO FOUND A CITY\n"
            "• Net worth ≥ $10 million.\n"
            "• Own at least 10 land plots across at least 3 different district types.\n"
            "• Pay a one-time founding fee (deducted from your balance on success).\n\n"
            "HOW CITIES WORK\n"
            "• The founder becomes Mayor automatically.\n"
            "• Other players join by applying; the Mayor approves or rejects.\n"
            "• Each city has a shared treasury fed by a configurable income-tax rate on members.\n"
            "• Mayors can grant or revoke tax exemptions, set the rate, and spend treasury funds "
            "on city projects.\n"
            "• City members earn perks (stat bonuses chosen at join-time) and can vote on projects.\n\n"
            "CITY PROJECTS\n"
            "Projects are one-time investments that upgrade the whole city — better resource yields, "
            "reduced fees, production bonuses. Some projects require a minimum member count to unlock.\n\n"
            "CITY MILESTONES\n"
            "Reach treasury and member thresholds to tier up your city, unlocking higher project "
            "slots and larger bonuses.\n\n"
            "TAXES & REVENUE\n"
            "• The city income tax is deducted from members automatically each tick.\n"
            "• A portion of market transactions made inside the city flows to the city treasury.\n"
            "• Treasury funds can only be spent by the Mayor on approved projects or grants.",
        ),
        (
            "Counties — Formation & Blockchain",
            "cities",
            "A county is a federation of cities that launches its own layer-1 blockchain token. "
            "Counties are the gateway to crypto, meme coins, and decentralised governance.\n\n"
            "HOW A COUNTY FORMS\n"
            "1. A city Mayor files a petition — either to create a brand-new county (requires "
            "enough districts and treasury balance) or to join an existing one.\n"
            "2. The petition enters a 24-hour government review.\n"
            "3a. New county: auto-approved, county is created immediately.\n"
            "3b. Joining existing: all current county members vote; simple majority decides.\n"
            "Each county may contain up to the configured maximum number of cities.\n\n"
            "THE COUNTY TOKEN\n"
            "Every county mints exactly one native cryptocurrency (you name it at petition time).\n"
            "Token supply is capped at 21 million, following Bitcoin's halving schedule — the "
            "block reward halves every 500 000 tokens minted. After all coins are mined, no new "
            "supply is ever created.\n\n"
            "COUNTY TREASURY\n"
            "Exchange fees on the county's crypto stay inside the county treasury — they are "
            "never shared with the national government. This makes the county treasury the primary "
            "self-funding mechanism for county governance projects.\n\n"
            "COUNTY GOVERNANCE\n"
            "County members can propose and vote on on-chain governance proposals: fee changes, "
            "token supply tweaks, treasury grants. Proposals that pass are executed automatically. "
            "Voting power is proportional to the native tokens burned in the vote.",
        ),
        (
            "Petitions — Filing & Results",
            "cities",
            "A petition is the formal mechanism for a city to enter the county system.\n\n"
            "FILING A PETITION\n"
            "• Only the city Mayor can file.\n"
            "• Choose: form a brand-new county (name + token details) OR apply to join an existing one.\n"
            "• The petition costs a small filing fee from the city treasury.\n\n"
            "PETITION LIFECYCLE\n"
            "1. PENDING GOVERNMENT REVIEW — waits up to 24 hours.\n"
            "2a. GOV APPROVED (new county) — county created, token launched. Mayor receives a "
            "push notification instantly.\n"
            "2b. POLL ACTIVE (joining) — county members vote for 24 hours.\n"
            "3a. POLL PASSED — city is admitted, all existing county members keep their tokens; "
            "the new city's members can now mine and trade. Mayor notified.\n"
            "3b. POLL FAILED / GOV REJECTED — petition closes, a new one can be filed after the "
            "cooldown. Mayor notified with the reason.\n\n"
            "NOTIFICATIONS\n"
            "All petition state changes trigger a push notification to the petitioning Mayor "
            "(enable Crypto Alerts in Settings to receive them on your Android device).",
        ),
    ]

    db = _db()
    try:
        for title, category, description in _ENTRIES:
            if db.query(WikiMedia).filter(WikiMedia.title == title).first():
                continue
            max_order = db.query(WikiMedia).count()
            db.add(WikiMedia(
                youtube_id="", kind="video",
                title=title, description=description,
                category=category, sort_order=max_order, pinned=False,
            ))
        db.commit()
        print("[Wiki] Seeded cities/counties entries")
    except Exception as e:
        db.rollback()
        print(f"[Wiki] Seed cities/counties error: {e}")
    finally:
        db.close()


# ===========================================================================
# CRYPTO — COUNTY TOKEN, MINING, STAKING, MEME COINS
# ===========================================================================

def _seed_crypto_entries():
    _ENTRIES = [
        (
            "County Crypto — Buying, Selling & Swapping",
            "cities",
            "Every county runs its own blockchain with a finite-supply native token. "
            "Any player in that county can buy, sell, or swap tokens on the county exchange.\n\n"
            "BUYING TOKENS\n"
            "• Pay USD → receive native tokens at the current market price.\n"
            "• The buy price is derived from the county treasury's backing ratio: "
            "total USD ever deposited divided by circulating supply.\n"
            "• A 2% exchange fee is deducted from the crypto amount you receive.\n\n"
            "SELLING TOKENS\n"
            "• Pay native tokens → receive USD from the county treasury.\n"
            "• The same 2% fee applies, deducted before crediting your balance.\n\n"
            "SWAPPING TOKENS\n"
            "• Trade one county's token directly for another's in a single atomic swap.\n"
            "• Both legs are priced at their respective market prices; the fee is applied once.\n\n"
            "EXCHANGE FEES & THE TREASURY\n"
            "Exchange fees stay inside the county — the government has no visibility into "
            "crypto transactions of any kind. The treasury grows from fees, providing a "
            "deeper backing pool over time.\n\n"
            "GAS FEES\n"
            "Every transaction also charges a small dynamic gas fee (EIP-1559 style) that "
            "goes into the county mining energy pool, increasing mining rewards for that cycle. "
            "Gas rises with transaction volume and drops back to base when activity is low.",
        ),
        (
            "Mining — How to Earn County Tokens",
            "cities",
            "Mining is the primary way to earn county native tokens without spending USD.\n\n"
            "HOW IT WORKS\n"
            "1. You stake native tokens into the county mining pool (this is a deposit, not a burn).\n"
            "2. Every mining cycle (roughly every hour) the pool distributes a block reward.\n"
            "3. Your share of the reward is proportional to your stake vs the total pool.\n"
            "4. Rewards land directly in your crypto wallet.\n\n"
            "BLOCK REWARD & HALVING\n"
            "The block reward follows a Bitcoin-style halving schedule tied to tokens minted, "
            "not time. Every 500 000 tokens minted the reward halves. This means early miners "
            "earn far more per cycle than late ones — the supply curve is deflationary by design.\n\n"
            "UNSTAKING\n"
            "You can unstake at any time; there is no lock-up period. Unstaked tokens return "
            "to your wallet immediately.\n\n"
            "EXECUTIVE BONUS\n"
            "A CTO or CIO executive with a crypto specialisation increases your mining yield "
            "by their bonus percentage. Hire one from the Executives page to amplify returns.\n\n"
            "NOTIFICATIONS\n"
            "Enable Crypto Alerts in Settings → Notifications to receive a push notification "
            "when your mining payout lands (throttled to at most once every 6 hours).",
        ),
        (
            "Meme Coins — Launching & Trading",
            "cities",
            "Meme coins are player-created micro-tokens launched on a county blockchain. "
            "They are separate from the county native token and have their own order book.\n\n"
            "LAUNCHING A MEME COIN\n"
            "• You must hold the county native token (minimum 30 tokens burned as creation fee).\n"
            "• Choose a name, ticker (3–6 chars), total supply, and description.\n"
            "• 10% of supply goes to you as a founder allocation immediately.\n"
            "• 90% is reserved for mining by stakers of the native token.\n"
            "• An SVG logo is generated automatically from the symbol.\n\n"
            "BACKING PRICE\n"
            "The implicit value floor of a meme coin is determined by how many native tokens "
            "have been burned into it (creation fee + direct burns). "
            "backing_price = total_burned / circulating_minted_supply.\n\n"
            "TRADING\n"
            "• Buy/sell via limit or market orders on the per-coin order book.\n"
            "• A 2% fee is split: 50% to the coin creator, 25% to the county treasury, 25% burned.\n"
            "• All trades appear in your transaction ledger under category 'crypto'.\n\n"
            "MEME COIN MINING\n"
            "Stake native tokens in the meme coin mining pool to earn the coin each cycle, "
            "following the same halving schedule as the county token but per-coin.\n\n"
            "TAX STATUS — INTENTIONAL DESIGN\n"
            "Crypto and meme coin activity is completely invisible to the national government's "
            "tax and fee system. No government fee is ever taken from any crypto transaction. "
            "This is a deliberate feature — county tokens are a tax shelter. Players who "
            "accumulate wealth in crypto avoid the income tax that USD-denominated activity "
            "incurs. The county treasury benefits instead.\n\n"
            "DISCOVERY\n"
            "Browse all active meme coins across every county at /memecoins. The Android "
            "widget also has a paginated Meme Coin feed showing price, 24h change, volume, "
            "holders, backing price, and mining pool data for every token in the game.",
        ),
        (
            "Meme Coin Mining — Staking for Yield",
            "cities",
            "Besides mining the county native token, you can mine specific meme coins by "
            "staking native tokens into that coin's mining pool.\n\n"
            "SETUP\n"
            "1. Navigate to a meme coin's detail page.\n"
            "2. Stake any amount of the county native token.\n"
            "3. Rewards pay out every mining cycle in the meme coin itself.\n\n"
            "REWARD SCHEDULE\n"
            "Each meme coin has its own halving interval based on its total supply. "
            "The block reward shrinks over time as more of the mining allocation is minted. "
            "Mining ends automatically when the mining allocation is exhausted.\n\n"
            "UNSTAKING\n"
            "Unstake at any time. Your staked native tokens return immediately; "
            "any pending rewards are paid out in the same transaction.\n\n"
            "STRATEGY\n"
            "• Early-stage coins pay the highest rewards — the block reward is at its peak.\n"
            "• Watch the mining_minted_pct on the widget feed; once it nears 100% "
            "mining returns collapse to zero.\n"
            "• Coins with many stakers dilute your share — smaller pools are more lucrative "
            "if you can be an early staker.",
        ),
        (
            "Crypto Tax Haven — How It Works",
            "cities",
            "One of Wadsworth's most strategic mechanics: the national government has zero "
            "visibility into any crypto activity.\n\n"
            "WHAT THIS MEANS\n"
            "• Buying, selling, swapping county tokens → no government fee, ever.\n"
            "• Trading or launching meme coins → no government fee.\n"
            "• Mining rewards → no income tax deducted.\n"
            "• County exchange fees stay in the county treasury, not the federal coffers.\n\n"
            "WHY THIS EXISTS\n"
            "The county system is designed to be a parallel shadow economy. Players who "
            "build wealth through the county layer pay effectively 0% tax — all activity "
            "flows through the county treasury, which is governed by its own members.\n\n"
            "STRATEGIC IMPLICATIONS\n"
            "• High-income players can park USD in county tokens to avoid income tax on "
            "future gains (buy once, hold as crypto, sell back to USD only when needed).\n"
            "• County treasuries grow purely from internal fees — counties with high trading "
            "volume become self-funding for governance projects.\n"
            "• The national government's only levers are on USD-denominated activity. "
            "If enough wealth migrates to crypto, the tax base shrinks — a real political "
            "dynamic that players can influence.\n\n"
            "NOTE FOR DEVELOPERS\n"
            "This is an intentional game design decision, not a bug or missing integration. "
            "Government fee routing was deliberately removed from all county exchange and "
            "meme coin paths. Do not re-add it.",
        ),
    ]

    db = _db()
    try:
        for title, category, description in _ENTRIES:
            if db.query(WikiMedia).filter(WikiMedia.title == title).first():
                continue
            max_order = db.query(WikiMedia).count()
            db.add(WikiMedia(
                youtube_id="", kind="video",
                title=title, description=description,
                category=category, sort_order=max_order, pinned=False,
            ))
        db.commit()
        print("[Wiki] Seeded crypto entries")
    except Exception as e:
        db.rollback()
        print(f"[Wiki] Seed crypto error: {e}")
    finally:
        db.close()


# ===========================================================================
# WSC STABLECOIN
# ===========================================================================

def _seed_wsc_entries():
    _ENTRIES = [
        (
            "WSC — The Wadsworth Stablecoin",
            "economy",
            "WSC (Wadsworth Stable Coin) is the in-game algorithmic stablecoin. "
            "It is pegged 1:1 to USD and earns yield through farming pools.\n\n"
            "HOW WSC IS MINTED\n"
            "• Deposit USD at any WSC Wallet endpoint to receive an equal amount of WSC.\n"
            "• WSC is not backed by a reserve — it is algorithmic and maintained by "
            "community demand and the yield-farming incentive.\n\n"
            "YIELD FARMING\n"
            "• Lock WSC into one of the available farming pools for a set duration.\n"
            "• At maturity, you receive your WSC back plus an APY reward paid in WSC.\n"
            "• APY rates vary by pool duration and current protocol reserves.\n\n"
            "CROSS-CHAIN SWAPS\n"
            "• WSC can be swapped directly for any county native token at market rate.\n"
            "• Swaps are settled atomically — no counterparty needed.\n\n"
            "MINTING RATE INDEX (WMRI)\n"
            "The WMRI market index tracks total WSC minted, circulating supply, and pool "
            "distribution. Watch it under Market Indices to gauge stablecoin demand.\n\n"
            "CTO / CIO BONUS\n"
            "A CTO or CIO executive with a smart-contract specialisation boosts your WSC "
            "yield-farming APY by their bonus percentage.\n\n"
            "FAUCET & AIRDROPS\n"
            "Small amounts of WSC can be claimed periodically from the faucet (rate-limited). "
            "Occasional community airdrops distribute WSC to active players — watch the "
            "Updates channel for announcements.",
        ),
        (
            "WSC Wallet — Features & Rewards",
            "economy",
            "The WSC Wallet page (/wsc-wallet or via the Crypto section) is your dashboard "
            "for all stablecoin activity.\n\n"
            "DASHBOARD PANELS\n"
            "• Balance — current WSC holdings and USD equivalent.\n"
            "• Yield Farms — open and completed farming positions, APY, and maturity dates.\n"
            "• Swap — instant WSC ↔ county token exchange at live prices.\n"
            "• Airdrop History — log of all WSC airdrops you have received.\n"
            "• Faucet — claim your next drip (timer shown when on cooldown).\n\n"
            "LIVE TICKER\n"
            "The wallet page embeds the same live price ticker as the main trading floor, "
            "filtered to crypto and WSC instruments.\n\n"
            "TRANSACTION LEDGER\n"
            "All WSC activity (minting, farming, swaps, faucet claims) appears in your "
            "transaction ledger under category 'crypto'. Because crypto is a tax haven, "
            "none of these transactions generate a government tax event.",
        ),
    ]

    db = _db()
    try:
        for title, category, description in _ENTRIES:
            if db.query(WikiMedia).filter(WikiMedia.title == title).first():
                continue
            max_order = db.query(WikiMedia).count()
            db.add(WikiMedia(
                youtube_id="", kind="video",
                title=title, description=description,
                category=category, sort_order=max_order, pinned=False,
            ))
        db.commit()
        print("[Wiki] Seeded WSC entries")
    except Exception as e:
        db.rollback()
        print(f"[Wiki] Seed WSC error: {e}")
    finally:
        db.close()
