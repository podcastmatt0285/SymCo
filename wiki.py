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
                "• When the event goes live, every NPC business's legal tender is updated to the mandated currency.\n"
                "• The switch is permanent — NPCs stay on the new currency after the event window closes.\n"
                "• For fiat currencies this is a REAL economic change, not cosmetic. The market settlement "
                "engine is already tender-aware for NPCs, so a fiat-mandated NPC genuinely earns its income "
                "in the new currency, holds it, spends it on the market, and pays hoarding tax in it.\n"
                "• Existing NPC balances are not force-converted at switch time — the change takes effect "
                "organically as new income arrives and old holdings are spent.\n"
                "• A future NPC Currency Mandate event can switch NPCs to a different currency again.\n\n"
                "What changes in the market:\n"
                "• NPC forex conversions create live demand for the mandated currency, nudging its exchange "
                "rate up and shifting its reserve-bank bond yields — which real players trade against.\n"
                "• NPC legal tender appears on their profile and in currency stats pages.\n"
                "• The government ledger records how many NPCs were switched and to which currency.\n"
                "• A mass NPC currency shift is a genuine government signal about which currencies the "
                "administration favours — and now has teeth, because ~97 NPCs moving their cash flow into a "
                "currency measurably affects its valuation.\n\n"
                "Available currencies:\n"
                "• All 16 fiat currencies (USD, JPY, EUR, GBP, CHF, CNY, INR, RUB, KRW, MXP, BRL, ZAR, "
                "TRY, SAR, AED, ANA) — each is a full, real switch.\n"
                "• All 6 metal coinage currencies (AU24, AU22, AG999, AG925, PT9995, PT950). Coinage is "
                "hard money: it can only be created by physically minting, so the hard-money rule keeps "
                "mandated-NPC income in USD and NPCs hold no coinage to spend. A coin mandate is therefore "
                "largely symbolic — a hard-money policy signal rather than a cash-flow change.\n\n"
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
