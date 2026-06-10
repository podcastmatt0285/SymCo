"""
banks/indices.py  –  Wadsworth Economic Indices

19 composite market indices tracked across the economy.
Each index has a landing card and a detail page with:
  • Live ticker value + 24 h / 30 d change
  • Line chart (30-day history) via Chart.js
  • Candlestick chart (7-day OHLCV) via TradingView Lightweight Charts
  • Pie chart (composition breakdown) via Chart.js
  • Heatmap (component distribution) – custom CSS/SVG
"""

from __future__ import annotations

import json
import math
import random
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.routing import APIRouter
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, func

from database import engine, SessionLocal
from sqlalchemy.orm import declarative_base

Base = declarative_base()
router = APIRouter()

# ─────────────────────────────────────────────────────────────────────────────
# MODEL
# ─────────────────────────────────────────────────────────────────────────────

class IndexSnapshot(Base):
    __tablename__ = "index_snapshots"

    id         = Column(Integer, primary_key=True)
    index_code = Column(String(16), index=True, nullable=False)
    timestamp  = Column(DateTime, default=datetime.utcnow, index=True)
    value      = Column(Float, default=0.0)
    meta_json  = Column(Text, nullable=True)   # JSON for pie / heatmap breakdown


def _get_db():
    return SessionLocal()


# ─────────────────────────────────────────────────────────────────────────────
# INDEX METADATA
# ─────────────────────────────────────────────────────────────────────────────

INDICES: dict[str, dict] = {
    "WBC50": {
        "name": "Wadsworth Blue-Chip 50",
        "code": "WBC-50",
        "desc": "Top 50 companies by market capitalisation — public players and NPC businesses.",
        "unit": "USD", "icon": "📈", "color": "#38bdf8",
    },
    "GLVI": {
        "name": "Global Land Valuation Index",
        "code": "GLVI",
        "desc": "Average value of all player-owned real estate (monthly_tax × 120).",
        "unit": "USD", "icon": "🏘️", "color": "#22c55e",
    },
    "CCC": {
        "name": "County Crypto Composite",
        "code": "CCC",
        "desc": "Total value of the Layer-1 blockchain ecosystem (native token market caps).",
        "unit": "USD", "icon": "⛓️", "color": "#a78bfa",
    },
    "EPI": {
        "name": "Executive Payroll Index",
        "code": "EPI",
        "desc": "Wage inflation of the global executive workforce.",
        "unit": "USD/hr", "icon": "💼", "color": "#f59e0b",
    },
    "CDI": {
        "name": "Corporate Dilution Index",
        "code": "CDI",
        "desc": "Shares printed (Secondary Offerings) vs shares destroyed (Buyback Programs).",
        "unit": "ratio", "icon": "🖨️", "color": "#fb923c",
    },
    "REGI": {
        "name": "Real Estate Gentrification Index",
        "code": "REGI",
        "desc": "Ratio of raw terrain plots to merged, high-tax mega-districts.",
        "unit": "ratio", "icon": "🏗️", "color": "#84cc16",
    },
    "RBYC": {
        "name": "Reserve Bank Yield Composite",
        "code": "RBYC",
        "desc": "Global average cost of borrowing across all foreign reserve banks.",
        "unit": "%", "icon": "🏦", "color": "#06b6d4",
    },
    "GSI": {
        "name": "Global Solvency Index",
        "code": "GSI",
        "desc": "Combined cash reserves and asset value of the automated banking sector.",
        "unit": "USD", "icon": "🛡️", "color": "#34d399",
    },
    "PCVI": {
        "name": "P2P Contract Velocity Index",
        "code": "PCVI",
        "desc": "Volume and value of active, private Peer-to-Peer delivery contracts.",
        "unit": "USD", "icon": "🤝", "color": "#f472b6",
    },
    "NSCI": {
        "name": "Neighborhood Services Cost Index",
        "code": "NSCI",
        "desc": "Cost of suburban living across all neighbourhood districts.",
        "unit": "USD/mo", "icon": "🏡", "color": "#fbbf24",
    },
    "ASI": {
        "name": "Agricultural Staples Index",
        "code": "ASI",
        "desc": "Aggregate market price index of raw agricultural commodity inputs.",
        "unit": "USD", "icon": "🌾", "color": "#4ade80",
    },
    "GDSI": {
        "name": "Global Defense Spending Index",
        "code": "GDSI",
        "desc": "Economic output of Military Base districts.",
        "unit": "USD", "icon": "⚔️", "color": "#ef4444",
    },
    "WMRI": {
        "name": "WSC Minting Rate Index",
        "code": "WMRI",
        "desc": "Total Wadsworth Stable Coins minted and distribution across treasury pools.",
        "unit": "WSC", "icon": "🪙", "color": "#fde68a",
    },
    "BEE": {
        "name": "Bee Index",
        "code": "BEE",
        "desc": "Total count of bees (workers + queens) in all player inventories.",
        "unit": "bees", "icon": "🐝", "color": "#fcd34d",
    },
    "WEI": {
        "name": "Water & Energy Index",
        "code": "WEI",
        "desc": "Total combined quantity of water and energy in all player inventories.",
        "unit": "units", "icon": "💧", "color": "#60a5fa",
    },
    "GPI": {
        "name": "Grass & Pollen Index",
        "code": "GPI",
        "desc": "Total combined quantity of grass and pollen in all player inventories.",
        "unit": "units", "icon": "🌿", "color": "#86efac",
    },
    "AMP": {
        "name": "Average Market Price",
        "code": "AMP",
        "desc": "Global average price across all commodity market executed trades.",
        "unit": "USD", "icon": "🏪", "color": "#a3e635",
    },
    "SEED": {
        "name": "Seeds Index",
        "code": "SEED",
        "desc": "Total quantity of all seed items in all player inventories.",
        "unit": "seeds", "icon": "🌱", "color": "#6ee7b7",
    },
    "GFI": {
        "name": "Greed & Fear Index",
        "code": "GFI",
        "desc": "Market sentiment gauge from 0 (Extreme Fear) to 100 (Extreme Greed).",
        "unit": "score", "icon": "😱", "color": "#f87171",
    },
}

_SEED_ITEMS = [
    "grape_seeds", "coffee_seeds", "tea_seeds", "barley_seeds", "wheat_seeds",
    "cocoa_seeds", "corn_seeds", "apple_seeds", "orange_seeds", "cotton_seeds",
    "cherry_seeds", "onion_seeds", "rice_seeds", "tomato_seeds", "tobacco_seeds",
]

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _fmt(value: float, unit: str, disp: dict | None = None) -> str:
    """Format a value for display, optionally converting USD to player's display currency."""
    if unit in ("USD", "USD/hr", "USD/mo"):
        if disp:
            try:
                from reserve_banks import fmt_usd as _fmt_usd
                return _fmt_usd(value, disp)
            except Exception:
                pass
        # fallback: hardcoded USD format
        if abs(value) >= 1_000_000_000:
            return f"${value/1_000_000_000:.2f}B"
        if abs(value) >= 1_000_000:
            return f"${value/1_000_000:.2f}M"
        if abs(value) >= 1_000:
            return f"${value/1_000:.1f}K"
        return f"${value:,.2f}"
    if unit == "%":
        return f"{value:.3f}%"
    if unit == "ratio":
        return f"{value:.3f}×"
    if unit == "WSC":
        if abs(value) >= 1_000_000:
            return f"{value/1_000_000:.2f}M WSC"
        return f"{value:,.0f} WSC"
    # generic
    if abs(value) >= 1_000_000:
        return f"{value/1_000_000:.2f}M"
    if abs(value) >= 1_000:
        return f"{value/1_000:.1f}K"
    return f"{value:,.2f}"


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


# ─────────────────────────────────────────────────────────────────────────────
# CALCULATION FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def calc_WBC50() -> tuple[float, dict]:
    """Top-50 market cap sum — public companies + NPC private enterprises."""
    try:
        from banks.brokerage_firm import CompanyShares, get_db as firm_db
        db = firm_db()
        try:
            rows = (db.query(CompanyShares.ticker_symbol,
                             CompanyShares.company_name,
                             CompanyShares.shares_outstanding,
                             CompanyShares.current_price)
                    .filter(CompanyShares.is_delisted == False)
                    .all())
        finally:
            db.close()
        caps = [{"label": r.ticker_symbol, "name": r.company_name,
                 "value": r.shares_outstanding * r.current_price}
                for r in rows if r.shares_outstanding and r.current_price]

        # Add NPC players as private enterprise entries (cash + land value)
        try:
            from auth import Player
            from land import LandPlot
            db_main = _get_db()
            try:
                npc_players = db_main.query(Player).filter(Player.is_npc == True).all()
                if npc_players:
                    npc_ids = [p.id for p in npc_players]
                    land_rows = (db_main.query(LandPlot.owner_id,
                                               func.sum(LandPlot.monthly_tax * 120))
                                 .filter(LandPlot.owner_id.in_(npc_ids))
                                 .group_by(LandPlot.owner_id).all())
                    land_by_id = {row[0]: float(row[1] or 0.0) for row in land_rows}

                    # Value ALL currency holdings in USD, not just the USD row.
                    # get_usd_balance() only reads the USD balance — an NPC whose
                    # legal tender was mandated to TRY/JPY/etc. would otherwise
                    # appear worthless and silently drop out of the index. One
                    # batch query instead of ~97 sequential sessions per snapshot.
                    cash_by_id: dict = {}
                    from database import ReserveSessionLocal
                    from reserve_banks import PlayerCurrencyBalance, StateReserveBank
                    rdb = ReserveSessionLocal()
                    try:
                        rates = {b.currency_code: float(b.usd_per_unit or 0.0)
                                 for b in rdb.query(StateReserveBank).all()}
                        rates.setdefault("USD", 1.0)
                        bal_rows = (rdb.query(PlayerCurrencyBalance.player_id,
                                              PlayerCurrencyBalance.currency_code,
                                              func.sum(PlayerCurrencyBalance.balance))
                                    .filter(PlayerCurrencyBalance.player_id.in_(npc_ids),
                                            PlayerCurrencyBalance.balance > 0)
                                    .group_by(PlayerCurrencyBalance.player_id,
                                              PlayerCurrencyBalance.currency_code)
                                    .all())
                        for pid, ccode, amt in bal_rows:
                            cash_by_id[pid] = (cash_by_id.get(pid, 0.0)
                                               + float(amt or 0.0) * rates.get(ccode, 0.0))
                    finally:
                        rdb.close()

                    for npc in npc_players:
                        npc_val = cash_by_id.get(npc.id, 0.0) + land_by_id.get(npc.id, 0.0)
                        if npc_val > 0:
                            caps.append({"label": npc.business_name,
                                         "name": npc.business_name,
                                         "value": npc_val})
            finally:
                db_main.close()
        except Exception as e:
            print(f"[Indices] WBC50 NPC valuation error: {e}")

        caps.sort(key=lambda x: x["value"], reverse=True)
        top50 = caps[:50]
        total = sum(c["value"] for c in top50)
        breakdown = [{"label": c["label"], "value": round(c["value"], 2)} for c in top50[:15]]
        if len(top50) > 15:
            rest = total - sum(b["value"] for b in breakdown)
            breakdown.append({"label": "Other", "value": round(rest, 2)})
        return total, {"breakdown": breakdown, "total": total, "companies": len(top50)}
    except Exception as e:
        print(f"[Indices] WBC50 error: {e}")
        return 0.0, {}


def calc_GLVI() -> tuple[float, dict]:
    """Average land value (monthly_tax × 120)."""
    try:
        from land import LandPlot
        db = _get_db()
        try:
            rows = (db.query(LandPlot.terrain_type, func.avg(LandPlot.monthly_tax))
                    .filter(LandPlot.is_government_owned == False)
                    .group_by(LandPlot.terrain_type)
                    .all())
            total_avg_row = db.query(func.avg(LandPlot.monthly_tax)).filter(
                LandPlot.is_government_owned == False).scalar()
        finally:
            db.close()
        avg_tax = float(total_avg_row or 0.0)
        avg_value = avg_tax * 120
        breakdown = [{"label": r[0], "value": round(float(r[1]) * 120, 2)} for r in rows]
        breakdown.sort(key=lambda x: x["value"], reverse=True)
        return avg_value, {"breakdown": breakdown, "avg_value": avg_value}
    except Exception as e:
        print(f"[Indices] GLVI error: {e}")
        return 0.0, {}


def calc_CCC() -> tuple[float, dict]:
    """Total county crypto market cap."""
    try:
        from counties import County, CryptoPriceHistory
        db = _get_db()
        try:
            counties = db.query(County).all()
            total = 0.0
            breakdown = []
            for county in counties:
                circ = max(county.total_crypto_minted - county.total_crypto_burned, 0.0)
                # Latest price from history
                snap = (db.query(CryptoPriceHistory)
                        .filter(CryptoPriceHistory.crypto_symbol == county.crypto_symbol)
                        .order_by(CryptoPriceHistory.timestamp.desc())
                        .first())
                if snap:
                    mcap = snap.market_cap or (circ * snap.price)
                elif circ > 0 and county.treasury_balance > 0:
                    price = county.treasury_balance / circ
                    mcap = circ * price
                else:
                    mcap = 0.0
                total += mcap
                breakdown.append({"label": county.crypto_symbol, "name": county.name,
                                   "value": round(mcap, 2)})
        finally:
            db.close()
        breakdown.sort(key=lambda x: x["value"], reverse=True)
        return total, {"breakdown": breakdown, "total": total}
    except Exception as e:
        print(f"[Indices] CCC error: {e}")
        return 0.0, {}


def calc_EPI() -> tuple[float, dict]:
    """Average hourly wage across all hired executives."""
    try:
        from executive import Executive
        db = _get_db()
        try:
            execs = (db.query(Executive)
                     .filter(Executive.player_id.isnot(None),
                             Executive.is_dead == False,
                             Executive.is_retired == False)
                     .all())
        finally:
            db.close()
        CYCLE_HOURS = {"hour": 1.0, "day": 24.0, "week": 168.0, "month": 720.0}
        by_job: dict[str, list] = defaultdict(list)
        hourly_wages = []
        for ex in execs:
            h = CYCLE_HOURS.get(ex.pay_cycle, 1.0)
            hw = ex.wage / h
            hourly_wages.append(hw)
            by_job[ex.job].append(hw)
        avg = (sum(hourly_wages) / len(hourly_wages)) if hourly_wages else 0.0
        breakdown = [{"label": job, "value": round(sum(ws)/len(ws), 2)}
                     for job, ws in by_job.items()]
        breakdown.sort(key=lambda x: x["value"], reverse=True)
        return avg, {"breakdown": breakdown, "avg": avg, "total_execs": len(hourly_wages)}
    except Exception as e:
        print(f"[Indices] EPI error: {e}")
        return 0.0, {}


def calc_CDI() -> tuple[float, dict]:
    """Ratio of shares issued to shares bought back."""
    try:
        from corporate_actions import SecondaryOffering, BuybackProgram
        db = _get_db()
        try:
            total_issued = db.query(func.sum(SecondaryOffering.shares_issued)).scalar() or 0
            total_bought = db.query(func.sum(BuybackProgram.shares_bought)).scalar() or 0
        finally:
            db.close()
        ratio = float(total_issued) / max(float(total_bought), 1.0)
        return ratio, {
            "breakdown": [
                {"label": "Shares Issued", "value": int(total_issued)},
                {"label": "Shares Bought Back", "value": int(total_bought)},
            ],
            "ratio": ratio,
        }
    except Exception as e:
        print(f"[Indices] CDI error: {e}")
        return 1.0, {}


def calc_REGI() -> tuple[float, dict]:
    """Ratio of raw terrain plots to district plots."""
    try:
        from land import LandPlot
        from districts import District
        db = _get_db()
        try:
            raw_by_terrain = (db.query(LandPlot.terrain_type, func.count(LandPlot.id))
                              .filter(~LandPlot.terrain_type.like("district_%"),
                                      LandPlot.is_government_owned == False)
                              .group_by(LandPlot.terrain_type)
                              .all())
            dist_by_type = (db.query(District.district_type, func.count(District.id))
                            .group_by(District.district_type)
                            .all())
            raw_count = sum(r[1] for r in raw_by_terrain)
            dist_count = sum(r[1] for r in dist_by_type)
        finally:
            db.close()
        ratio = float(raw_count) / max(float(dist_count), 1.0)
        breakdown = [{"label": r[0], "value": r[1]} for r in raw_by_terrain]
        breakdown += [{"label": f"[D] {r[0]}", "value": r[1]} for r in dist_by_type]
        return ratio, {"breakdown": breakdown, "raw_plots": raw_count,
                       "districts": dist_count, "ratio": ratio}
    except Exception as e:
        print(f"[Indices] REGI error: {e}")
        return 0.0, {}


def calc_RBYC() -> tuple[float, dict]:
    """Average yield rate across all reserve banks (as %)."""
    try:
        from database import ReserveSessionLocal
        from reserve_banks import StateReserveBank
        db = ReserveSessionLocal()
        try:
            banks = db.query(StateReserveBank).all()
        finally:
            db.close()
        if not banks:
            return 0.0, {}
        avg_yield = sum(b.yield_rate for b in banks) / len(banks) * 100
        breakdown = [{"label": b.currency_code,
                      "value": round(b.yield_rate * 100, 3)} for b in banks]
        breakdown.sort(key=lambda x: x["value"], reverse=True)
        return avg_yield, {"breakdown": breakdown, "avg": avg_yield, "count": len(banks)}
    except Exception as e:
        print(f"[Indices] RBYC error: {e}")
        return 0.0, {}


def calc_GSI() -> tuple[float, dict]:
    """Total reserves + assets of all automated banks."""
    try:
        import banks as banks_mod
        db = _get_db()
        try:
            entities = db.query(banks_mod.BankEntity).filter(
                banks_mod.BankEntity.is_active == True).all()
        finally:
            db.close()
        total = 0.0
        breakdown = []
        for ent in entities:
            nav = ent.cash_reserves + ent.asset_value
            total += nav
            breakdown.append({"label": ent.bank_id.replace("_", " ").title(),
                               "value": round(nav, 2)})
        # Include brokerage firm reserves
        try:
            from banks.brokerage_firm import get_firm_entity
            firm = get_firm_entity()
            if firm:
                total += firm.cash_reserves
                breakdown.append({"label": "Brokerage Firm",
                                   "value": round(firm.cash_reserves, 2)})
        except Exception:
            pass
        breakdown.sort(key=lambda x: x["value"], reverse=True)
        return total, {"breakdown": breakdown, "total": total}
    except Exception as e:
        print(f"[Indices] GSI error: {e}")
        return 0.0, {}


def calc_PCVI() -> tuple[float, dict]:
    """Total value of active P2P delivery contracts."""
    try:
        from p2p import Contract, ContractItem
        db = _get_db()
        try:
            active = (db.query(Contract)
                      .filter(Contract.status == "active")
                      .all())
            total_value = 0.0
            by_interval: dict[str, float] = defaultdict(float)
            for c in active:
                remaining = max(c.total_deliveries - c.deliveries_completed, 0)
                ppd = c.price_per_delivery or 0.0
                val = ppd * remaining
                total_value += val
                by_interval[c.delivery_interval] += val
        finally:
            db.close()
        breakdown = [{"label": k, "value": round(v, 2)}
                     for k, v in by_interval.items()]
        breakdown.sort(key=lambda x: x["value"], reverse=True)
        return total_value, {"breakdown": breakdown, "active_contracts": len(active),
                             "total_value": total_value}
    except Exception as e:
        print(f"[Indices] PCVI error: {e}")
        return 0.0, {}


def calc_NSCI() -> tuple[float, dict]:
    """Total monthly tax of all neighbourhood districts (proxy for service cost)."""
    try:
        from districts import District
        db = _get_db()
        try:
            hoods = (db.query(District)
                     .filter(District.district_type == "neighborhood")
                     .all())
        finally:
            db.close()
        total_tax = sum(d.monthly_tax for d in hoods)
        avg_tax = total_tax / max(len(hoods), 1)
        return avg_tax, {
            "breakdown": [{"label": f"District #{d.id}", "value": round(d.monthly_tax, 2)}
                          for d in hoods],
            "count": len(hoods),
            "avg": avg_tax,
            "total": total_tax,
        }
    except Exception as e:
        print(f"[Indices] NSCI error: {e}")
        return 0.0, {}


def calc_ASI() -> tuple[float, dict]:
    """Average market price of key agricultural commodity inputs."""
    try:
        import market as mkt
        prices = {}
        for item in _SEED_ITEMS:
            p = mkt.get_market_price(item)
            if p:
                prices[item] = p
        if not prices:
            return 0.0, {"no_data": True, "breakdown": []}
        avg = sum(prices.values()) / len(prices)
        breakdown = [{"label": k.replace("_", " ").title(), "value": round(v, 4)}
                     for k, v in sorted(prices.items(), key=lambda x: -x[1])]
        return avg, {"breakdown": breakdown, "avg": avg, "items_tracked": len(prices)}
    except Exception as e:
        print(f"[Indices] ASI error: {e}")
        return 0.0, {}


def calc_GDSI() -> tuple[float, dict]:
    """Total monthly tax from military districts."""
    try:
        from districts import District
        db = _get_db()
        try:
            military = (db.query(District)
                        .filter(District.district_type == "military")
                        .all())
        finally:
            db.close()
        total = sum(d.monthly_tax for d in military)
        return total, {
            "breakdown": [{"label": f"Base #{d.id}", "value": round(d.monthly_tax, 2)}
                          for d in military],
            "count": len(military),
            "total": total,
        }
    except Exception as e:
        print(f"[Indices] GDSI error: {e}")
        return 0.0, {}


def calc_WMRI() -> tuple[float, dict]:
    """Total WSC minted and treasury pool distribution."""
    try:
        from wallet import WSCTreasury
        db = _get_db()
        try:
            treas = db.query(WSCTreasury).first()
        finally:
            db.close()
        if not treas:
            return 0.0, {}
        total = treas.total_minted
        breakdown = [
            {"label": "Yield Pool",   "value": round(treas.yield_farming_pool, 4)},
            {"label": "Faucet Pool",  "value": round(treas.faucet_pool, 4)},
            {"label": "Airdrop Pool", "value": round(treas.airdrop_pool, 4)},
        ]
        in_pool = treas.yield_farming_pool + treas.faucet_pool + treas.airdrop_pool
        circulating = max(total - in_pool, 0.0)
        breakdown.append({"label": "Circulating", "value": round(circulating, 4)})
        return total, {"breakdown": breakdown, "total": total,
                       "circulating": circulating}
    except Exception as e:
        print(f"[Indices] WMRI error: {e}")
        return 0.0, {}


def _inv_sum(item_types: list[str]) -> tuple[float, dict]:
    """Sum inventory quantities for a list of item types."""
    from inventory import InventoryItem
    db = _get_db()
    try:
        rows = (db.query(InventoryItem.item_type, func.sum(InventoryItem.quantity))
                .filter(InventoryItem.item_type.in_(item_types))
                .group_by(InventoryItem.item_type)
                .all())
    finally:
        db.close()
    total = 0.0
    breakdown = []
    for item_type, qty in rows:
        total += (qty or 0.0)
        breakdown.append({"label": item_type.replace("_", " ").title(),
                          "value": round(float(qty or 0.0), 2)})
    breakdown.sort(key=lambda x: x["value"], reverse=True)
    return total, {"breakdown": breakdown, "total": total}


def calc_BEE() -> tuple[float, dict]:
    try:
        return _inv_sum(["bees", "queen_bee"])
    except Exception as e:
        print(f"[Indices] BEE error: {e}")
        return 0.0, {}


def calc_WEI() -> tuple[float, dict]:
    try:
        return _inv_sum(["water", "energy"])
    except Exception as e:
        print(f"[Indices] WEI error: {e}")
        return 0.0, {}


def calc_GPI() -> tuple[float, dict]:
    try:
        return _inv_sum(["grass", "pollen"])
    except Exception as e:
        print(f"[Indices] GPI error: {e}")
        return 0.0, {}


def calc_AMP() -> tuple[float, dict]:
    """Average commodity market trade price (last 30 days)."""
    try:
        from market import Trade
        db = _get_db()
        cutoff = datetime.utcnow() - timedelta(days=30)
        try:
            rows = (db.query(Trade.item_type,
                             func.avg(Trade.price).label("avg_price"),
                             func.count(Trade.id).label("cnt"))
                    .filter(Trade.executed_at >= cutoff)
                    .group_by(Trade.item_type)
                    .all())
        finally:
            db.close()
        if not rows:
            return 0.0, {}
        overall_avg = sum(r.avg_price for r in rows) / len(rows)
        breakdown = [{"label": r.item_type.replace("_", " ").title(),
                      "value": round(float(r.avg_price), 4)}
                     for r in sorted(rows, key=lambda r: -r.avg_price)[:20]]
        return overall_avg, {"breakdown": breakdown, "avg": overall_avg,
                             "trade_count": sum(r.cnt for r in rows)}
    except Exception as e:
        print(f"[Indices] AMP error: {e}")
        return 0.0, {}


def calc_SEED() -> tuple[float, dict]:
    try:
        return _inv_sum(_SEED_ITEMS)
    except Exception as e:
        print(f"[Indices] SEED error: {e}")
        return 0.0, {}


def calc_GFI() -> tuple[float, dict]:
    """
    Greed & Fear Index (0-100).
    Signals:
      1. Market Momentum      (0-30 pts)  – WBC50 vs 30d SMA
      2. Market Breadth       (0-25 pts)  – companies above IPO price
      3. Corporate Actions    (0-25 pts)  – buybacks vs secondary offerings
      4. P2P Velocity         (0-10 pts)  – active contract count
      5. Trading Volume       (0-10 pts)  – trade count last 24 h
    """
    signals: dict[str, float] = {}

    # 1. Market Momentum
    try:
        db = _get_db()
        cutoff30 = datetime.utcnow() - timedelta(days=30)
        try:
            snaps = (db.query(IndexSnapshot)
                     .filter(IndexSnapshot.index_code == "WBC50",
                             IndexSnapshot.timestamp >= cutoff30)
                     .order_by(IndexSnapshot.timestamp.asc())
                     .all())
        finally:
            db.close()
        if snaps and len(snaps) >= 2:
            current = snaps[-1].value
            sma = sum(s.value for s in snaps) / len(snaps)
            pct = (current - sma) / max(sma, 1.0)
            signals["Momentum"] = _clamp(pct * 150 + 15, 0, 30)
        else:
            signals["Momentum"] = 15.0
    except Exception:
        signals["Momentum"] = 15.0

    # 2. Market Breadth
    try:
        from banks.brokerage_firm import CompanyShares, get_db as firm_db
        db = firm_db()
        try:
            total_cos = db.query(func.count(CompanyShares.id)).filter(
                CompanyShares.is_delisted == False).scalar() or 0
            above_ipo = db.query(func.count(CompanyShares.id)).filter(
                CompanyShares.is_delisted == False,
                CompanyShares.current_price >= CompanyShares.ipo_price).scalar() or 0
        finally:
            db.close()
        ratio = (above_ipo / max(total_cos, 1))
        signals["Breadth"] = _clamp(ratio * 25, 0, 25)
    except Exception:
        signals["Breadth"] = 12.5

    # 3. Corporate Actions
    try:
        from corporate_actions import SecondaryOffering, BuybackProgram
        db = _get_db()
        try:
            issued = db.query(func.sum(SecondaryOffering.shares_issued)).scalar() or 0
            bought = db.query(func.sum(BuybackProgram.shares_bought)).scalar() or 0
        finally:
            db.close()
        if issued == 0 and bought == 0:
            signals["Corp Actions"] = 12.5  # neutral — no data yet
        else:
            ratio = float(bought) / max(float(issued), 1.0)
            signals["Corp Actions"] = _clamp(ratio * 25, 0, 25)
    except Exception:
        signals["Corp Actions"] = 12.5

    # 4. P2P Velocity
    try:
        from p2p import Contract
        db = _get_db()
        try:
            active = db.query(func.count(Contract.id)).filter(
                Contract.status == "active").scalar() or 0
        finally:
            db.close()
        signals["P2P Velocity"] = _clamp(active / 20 * 10, 0, 10)
    except Exception:
        signals["P2P Velocity"] = 5.0

    # 5. Trading Volume
    try:
        from market import Trade
        db = _get_db()
        cutoff24 = datetime.utcnow() - timedelta(hours=24)
        try:
            count = db.query(func.count(Trade.id)).filter(
                Trade.executed_at >= cutoff24).scalar() or 0
        finally:
            db.close()
        signals["Trade Volume"] = _clamp(count / 50 * 10, 0, 10)
    except Exception:
        signals["Trade Volume"] = 5.0

    total = round(sum(signals.values()), 1)

    if total <= 24:
        label = "Extreme Fear"
    elif total <= 44:
        label = "Fear"
    elif total <= 55:
        label = "Neutral"
    elif total <= 75:
        label = "Greed"
    else:
        label = "Extreme Greed"

    breakdown = [{"label": k, "value": round(v, 1)} for k, v in signals.items()]
    return total, {"breakdown": breakdown, "total": total, "label": label,
                   "signals": signals}


_CALCULATORS = {
    "WBC50": calc_WBC50,
    "GLVI":  calc_GLVI,
    "CCC":   calc_CCC,
    "EPI":   calc_EPI,
    "CDI":   calc_CDI,
    "REGI":  calc_REGI,
    "RBYC":  calc_RBYC,
    "GSI":   calc_GSI,
    "PCVI":  calc_PCVI,
    "NSCI":  calc_NSCI,
    "ASI":   calc_ASI,
    "GDSI":  calc_GDSI,
    "WMRI":  calc_WMRI,
    "BEE":   calc_BEE,
    "WEI":   calc_WEI,
    "GPI":   calc_GPI,
    "AMP":   calc_AMP,
    "SEED":  calc_SEED,
    "GFI":   calc_GFI,
}


# ─────────────────────────────────────────────────────────────────────────────
# SNAPSHOT MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

def calculate_all_indices():
    """Calculate all indices and store snapshots. Each index commits independently."""
    for code, fn in _CALCULATORS.items():
        db = _get_db()
        try:
            value, meta = fn()
            snap = IndexSnapshot(
                index_code=code,
                value=float(value),
                meta_json=json.dumps(meta) if meta else None,
            )
            db.add(snap)
            db.commit()
        except Exception as e:
            print(f"[Indices] Snapshot error for {code}: {e}")
            try:
                db.rollback()
            except Exception:
                pass
        finally:
            db.close()

    # Prune snapshots beyond the longest charted window (30 days) plus margin.
    # Without this the table grows ~82k rows/month forever.
    db = _get_db()
    try:
        cutoff = datetime.utcnow() - timedelta(days=90)
        deleted = (db.query(IndexSnapshot)
                   .filter(IndexSnapshot.timestamp < cutoff)
                   .delete(synchronize_session=False))
        db.commit()
        if deleted:
            print(f"[Indices] Pruned {deleted} snapshots older than 90 days.")
    except Exception as e:
        print(f"[Indices] Prune error: {e}")
        try:
            db.rollback()
        except Exception:
            pass
    finally:
        db.close()


def _get_latest(code: str) -> Optional[IndexSnapshot]:
    db = _get_db()
    try:
        return (db.query(IndexSnapshot)
                .filter(IndexSnapshot.index_code == code)
                .order_by(IndexSnapshot.timestamp.desc())
                .first())
    finally:
        db.close()


def _get_history(code: str, days: int) -> list[IndexSnapshot]:
    db = _get_db()
    cutoff = datetime.utcnow() - timedelta(days=days)
    try:
        return (db.query(IndexSnapshot)
                .filter(IndexSnapshot.index_code == code,
                        IndexSnapshot.timestamp >= cutoff)
                .order_by(IndexSnapshot.timestamp.asc())
                .all())
    finally:
        db.close()


def _snap_near_24h(snaps: list) -> "IndexSnapshot | None":
    """Return the snapshot whose timestamp is closest to exactly 24 hours ago."""
    if not snaps:
        return None
    target = datetime.utcnow() - timedelta(hours=24)
    return min(snaps, key=lambda s: abs((s.timestamp - target).total_seconds()))


def _get_alltime_stats(code: str) -> tuple[float, float]:
    """Return (all_time_high, all_time_low) for an index."""
    db = _get_db()
    try:
        row = db.query(func.max(IndexSnapshot.value),
                       func.min(IndexSnapshot.value)
                       ).filter(IndexSnapshot.index_code == code).first()
        return (row[0] or 0.0, row[1] or 0.0)
    finally:
        db.close()


def _get_prev_close(code: str) -> "float | None":
    """Return the last snapshot value from before today (UTC midnight)."""
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    db = _get_db()
    try:
        row = (db.query(IndexSnapshot)
               .filter(IndexSnapshot.index_code == code,
                       IndexSnapshot.timestamp < today_start)
               .order_by(IndexSnapshot.timestamp.desc())
               .first())
        return row.value if row else None
    finally:
        db.close()


def _calc_volatility(snaps: list) -> float:
    """Return std deviation of per-snapshot % returns as a percentage."""
    if len(snaps) < 3:
        return 0.0
    returns = []
    for i in range(1, len(snaps)):
        prev = snaps[i - 1].value
        if prev != 0:
            returns.append((snaps[i].value - prev) / abs(prev))
    if len(returns) < 2:
        return 0.0
    n = len(returns)
    mean = sum(returns) / n
    variance = sum((r - mean) ** 2 for r in returns) / (n - 1)
    return (variance ** 0.5) * 100


_RELATED: dict[str, list[str]] = {
    "WBC50": ["GSI", "CDI", "GFI", "AMP"],
    "GLVI":  ["REGI", "NSCI", "WBC50", "GSI"],
    "CCC":   ["WMRI", "CDI", "WBC50"],
    "EPI":   ["WBC50", "NSCI", "PCVI"],
    "CDI":   ["WBC50", "GFI", "CCC"],
    "REGI":  ["GLVI", "NSCI", "GDSI"],
    "RBYC":  ["GFI", "GSI", "WMRI"],
    "GSI":   ["WBC50", "RBYC", "GFI"],
    "PCVI":  ["WBC50", "AMP", "EPI"],
    "NSCI":  ["GLVI", "REGI", "EPI"],
    "ASI":   ["AMP", "GPI", "WEI"],
    "GDSI":  ["WBC50", "REGI", "GFI"],
    "WMRI":  ["CCC", "RBYC", "GSI"],
    "BEE":   ["GPI", "ASI", "SEED"],
    "WEI":   ["ASI", "GPI", "AMP"],
    "GPI":   ["WEI", "BEE", "ASI"],
    "AMP":   ["ASI", "WBC50", "PCVI"],
    "SEED":  ["ASI", "GPI", "BEE"],
    "GFI":   ["WBC50", "CDI", "RBYC"],
}


def _build_ohlcv(snaps: list[IndexSnapshot], bucket_hours: int = 1) -> list[dict]:
    """Aggregate raw snapshots into hourly OHLCV candles."""
    buckets: dict[int, list[float]] = defaultdict(list)
    for s in snaps:
        hour_ts = int(s.timestamp.replace(minute=0, second=0, microsecond=0).timestamp())
        buckets[hour_ts].append(s.value)
    candles = []
    for ts, vals in sorted(buckets.items()):
        candles.append({
            "time":  ts,
            "open":  vals[0],
            "high":  max(vals),
            "low":   min(vals),
            "close": vals[-1],
        })
    return candles


def _pct_change(current: float, previous: float) -> float:
    if previous == 0:
        return 0.0
    return (current - previous) / abs(previous) * 100


def _sparkline_svg(snaps: list[IndexSnapshot], color: str = "#38bdf8") -> str:
    """Generate a tiny 80×24 SVG sparkline."""
    if not snaps:
        return '<svg width="80" height="24"></svg>'
    vals = [s.value for s in snaps]
    mn, mx = min(vals), max(vals)
    rng = mx - mn or 1.0
    w, h = 80, 24
    pts = []
    for i, v in enumerate(vals):
        x = i / max(len(vals) - 1, 1) * w
        y = h - ((v - mn) / rng) * (h - 2) - 1
        pts.append(f"{x:.1f},{y:.1f}")
    path = "M" + " L".join(pts)
    return (f'<svg width="{w}" height="{h}" style="display:block;">'
            f'<polyline points="{" ".join(pts)}" fill="none" '
            f'stroke="{color}" stroke-width="1.5" stroke-linejoin="round"/>'
            f'</svg>')


# ─────────────────────────────────────────────────────────────────────────────
# PAGE BUILDER – UX HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _shell(title, body, balance=0.0, player_id=None):
    try:
        from ux import shell as ux_shell
        return ux_shell(title, body, balance, player_id)
    except Exception:
        return f"<html><body>{body}</body></html>"


def _guest_shell(title: str, body: str) -> str:
    """Minimal HTML shell for unauthenticated visitors — no game nav."""
    from skin_utils import skin_links
    skin_tags = skin_links(None)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · Wadsworth</title>
{skin_tags}
<style>
body {{ max-width:1200px; margin:0 auto; padding:20px 20px 80px; }}
</style>
</head>
<body>
{body}
</body>
</html>"""


def _gfi_color(score: float) -> str:
    if score <= 24:   return "#dc2626"
    if score <= 44:   return "#f97316"
    if score <= 55:   return "#eab308"
    if score <= 75:   return "#22c55e"
    return "#16a34a"


def _heatmap_color(ratio: float) -> str:
    """ratio 0→1, returns red→green hex."""
    r = int(239 - ratio * (239 - 34))
    g = int(68  + ratio * (197 - 68))
    b = int(68  + ratio * (94  - 68))
    return f"#{r:02x}{g:02x}{b:02x}"


# ─────────────────────────────────────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/banks/indices", response_class=HTMLResponse)
def indices_landing(session_token: Optional[str] = Cookie(None)):
    try:
        from ux import require_auth
        player = require_auth(session_token)
        if isinstance(player, RedirectResponse):
            return player
    except Exception:
        return RedirectResponse(url="/login", status_code=303)

    try:
        from reserve_banks import get_player_display_currency
        disp = get_player_display_currency(player.id)
    except Exception:
        disp = None

    # Build cards for all 19 indices
    cards_html = ""
    for code, meta in INDICES.items():
        snaps30 = _get_history(code, 30)
        snap_now = snaps30[-1] if snaps30 else None

        current  = snap_now.value if snap_now else 0.0
        fmted    = _fmt(current, meta["unit"], disp)

        snap_24h = _snap_near_24h(snaps30)
        if snap_24h is snap_now:
            snap_24h = None
        snap_7d  = None
        if snaps30:
            t7 = datetime.utcnow() - timedelta(days=7)
            snap_7d = min(snaps30, key=lambda s: abs((s.timestamp - t7).total_seconds()))
            if snap_7d is snap_now:
                snap_7d = None
        snap_30d = snaps30[0] if len(snaps30) >= 2 else None

        ch24  = _pct_change(current, snap_24h.value)  if snap_24h  else None
        ch7   = _pct_change(current, snap_7d.value)   if snap_7d   else None
        ch30  = _pct_change(current, snap_30d.value)  if snap_30d  else None

        def _chip(label: str, pct: "float | None") -> str:
            if pct is None:
                return f'<span class="perf-chip perf-na">{label} —</span>'
            c = "#22c55e" if pct >= 0 else "#ef4444"
            a = "▲" if pct >= 0 else "▼"
            return (f'<span class="perf-chip" style="color:{c};">'
                    f'{label} {a}{abs(pct):.1f}%</span>')

        pt_change = current - snap_24h.value if snap_24h else None
        pt_str = ""
        if pt_change is not None:
            pt_col = "#22c55e" if pt_change >= 0 else "#ef4444"
            pt_fmt = _fmt(abs(pt_change), meta["unit"], disp)
            sign   = "+" if pt_change >= 0 else "−"
            pt_str = f'<span style="color:{pt_col};font-size:.7rem;">{sign}{pt_fmt}</span>'

        svg = _sparkline_svg(snaps30[-48:], meta["color"]) if snaps30 else ""

        cards_html += f"""
        <a href="/banks/indices/{code}" class="idx-card" style="--c:{meta['color']};">
          <div class="idx-top">
            <span class="idx-icon">{meta['icon']}</span>
            <span class="idx-code">{meta['code']}</span>
          </div>
          <div class="idx-name">{meta['name']}</div>
          <div class="idx-value">{fmted} {pt_str}</div>
          <div class="idx-perfs">{_chip("24h",ch24)}{_chip("7D",ch7)}{_chip("30D",ch30)}</div>
          <div class="idx-spark">{svg}</div>
        </a>"""

    body = f"""
    <style>
      .idx-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
        gap: 14px;
        margin-top: 16px;
      }}
      .idx-card {{
        background: #0f172a;
        border: 1px solid #1e293b;
        border-top: 3px solid var(--c,#38bdf8);
        border-radius: 8px;
        padding: 14px;
        text-decoration: none;
        color: #e2e8f0;
        display: flex;
        flex-direction: column;
        gap: 5px;
        transition: border-color .15s, background .15s;
      }}
      .idx-card:hover {{ background:#1e293b; border-color: var(--c,#38bdf8); text-decoration:none; }}
      .idx-top {{ display:flex; justify-content:space-between; align-items:center; }}
      .idx-icon {{ font-size:1.4rem; }}
      .idx-code {{ font-size:.7rem; color:var(--c,#38bdf8); font-weight:bold;
                   background:rgba(255,255,255,.06); padding:2px 6px; border-radius:4px; }}
      .idx-name {{ font-size:.78rem; color:#94a3b8; margin-top:2px; }}
      .idx-value {{ font-size:1.2rem; font-weight:bold; color:var(--c,#38bdf8);
                    display:flex; align-items:baseline; gap:6px; }}
      .idx-perfs {{ display:flex; gap:4px; flex-wrap:wrap; margin-top:2px; }}
      .perf-chip {{ font-size:.65rem; background:rgba(255,255,255,.05);
                    border-radius:3px; padding:1px 5px; white-space:nowrap; }}
      .perf-na   {{ color:#475569; }}
      .idx-spark {{ margin-top:4px; }}
    </style>

    <a href="/banks" style="color:#38bdf8;font-size:.85rem;">← Banks</a>
    <h1 style="margin:10px 0 4px;">Market Indices</h1>
    <p style="color:#64748b;font-size:.85rem;margin:0 0 4px;">
      {len(INDICES)} live composite indices tracking the Wadsworth economy.
    </p>
    <div class="idx-grid">{cards_html}</div>
    """

    tut4 = ""
    try:
        from tutorial_ux import get_tutorial4_overlay_html
        tut4 = get_tutorial4_overlay_html(player, "banks_indices")
    except Exception:
        pass

    return _shell("Market Indices", tut4 + body + "<script>window._tkCategories=['stocks'];</script>", getattr(player, 'cash_balance', 0), getattr(player, 'id', None))


@router.get("/banks/indices/unloggedin", response_class=HTMLResponse)
def indices_landing_unloggedin():
    """Same indices grid as /banks/indices but for unauthenticated visitors."""
    cards_html = ""
    for code, meta in INDICES.items():
        snaps30 = _get_history(code, 30)
        snap_now = snaps30[-1] if snaps30 else None

        current  = snap_now.value if snap_now else 0.0
        fmted    = _fmt(current, meta["unit"])

        snap_24h = _snap_near_24h(snaps30)
        if snap_24h is snap_now:
            snap_24h = None
        snap_7d = None
        if snaps30:
            t7 = datetime.utcnow() - timedelta(days=7)
            snap_7d = min(snaps30, key=lambda s: abs((s.timestamp - t7).total_seconds()))
            if snap_7d is snap_now:
                snap_7d = None
        snap_30d = snaps30[0] if len(snaps30) >= 2 else None

        ch24  = _pct_change(current, snap_24h.value) if snap_24h else None
        ch7   = _pct_change(current, snap_7d.value)  if snap_7d  else None
        ch30  = _pct_change(current, snap_30d.value) if snap_30d else None

        def _chip(label: str, pct: "float | None") -> str:
            if pct is None:
                return f'<span class="perf-chip perf-na">{label} —</span>'
            c = "#22c55e" if pct >= 0 else "#ef4444"
            a = "▲" if pct >= 0 else "▼"
            return (f'<span class="perf-chip" style="color:{c};">'
                    f'{label} {a}{abs(pct):.1f}%</span>')

        pt_change = current - snap_24h.value if snap_24h else None
        pt_str = ""
        if pt_change is not None:
            pt_col = "#22c55e" if pt_change >= 0 else "#ef4444"
            pt_fmt = _fmt(abs(pt_change), meta["unit"])
            sign   = "+" if pt_change >= 0 else "−"
            pt_str = f'<span style="color:{pt_col};font-size:.7rem;">{sign}{pt_fmt}</span>'

        svg = _sparkline_svg(snaps30[-48:], meta["color"]) if snaps30 else ""

        cards_html += f"""
        <a href="/banks/indices/{code}/unloggedin" class="idx-card" style="--c:{meta['color']};">
          <div class="idx-top">
            <span class="idx-icon">{meta['icon']}</span>
            <span class="idx-code">{meta['code']}</span>
          </div>
          <div class="idx-name">{meta['name']}</div>
          <div class="idx-value">{fmted} {pt_str}</div>
          <div class="idx-perfs">{_chip("24h",ch24)}{_chip("7D",ch7)}{_chip("30D",ch30)}</div>
          <div class="idx-spark">{svg}</div>
        </a>"""

    body = f"""
    <style>
      .idx-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
        gap: 14px;
        margin-top: 16px;
      }}
      .idx-card {{
        background: #0f172a;
        border: 1px solid #1e293b;
        border-top: 3px solid var(--c,#38bdf8);
        border-radius: 8px;
        padding: 14px;
        text-decoration: none;
        color: #e2e8f0;
        display: flex;
        flex-direction: column;
        gap: 5px;
        transition: border-color .15s, background .15s;
      }}
      .idx-card:hover {{ background:#1e293b; border-color: var(--c,#38bdf8); text-decoration:none; }}
      .idx-top {{ display:flex; justify-content:space-between; align-items:center; }}
      .idx-icon {{ font-size:1.4rem; }}
      .idx-code {{ font-size:.7rem; color:var(--c,#38bdf8); font-weight:bold;
                   background:rgba(255,255,255,.06); padding:2px 6px; border-radius:4px; }}
      .idx-name {{ font-size:.78rem; color:#94a3b8; margin-top:2px; }}
      .idx-value {{ font-size:1.2rem; font-weight:bold; color:var(--c,#38bdf8);
                    display:flex; align-items:baseline; gap:6px; }}
      .idx-perfs {{ display:flex; gap:4px; flex-wrap:wrap; margin-top:2px; }}
      .perf-chip {{ font-size:.65rem; background:rgba(255,255,255,.05);
                    border-radius:3px; padding:1px 5px; white-space:nowrap; }}
      .perf-na   {{ color:#475569; }}
      .idx-spark {{ margin-top:4px; }}
    </style>

    <a href="/login" style="color:#38bdf8;font-size:.85rem;">← Back to Login</a>
    <h1 style="margin:10px 0 4px;">Market Indices</h1>
    <p style="color:#64748b;font-size:.85rem;margin:0 0 4px;">
      {len(INDICES)} live composite indices tracking the Wadsworth economy.
    </p>
    <div class="idx-grid">{cards_html}</div>
    """

    return _guest_shell("Market Indices", body)


@router.get("/banks/indices/{code}", response_class=HTMLResponse)
def index_detail(code: str, session_token: Optional[str] = Cookie(None)):
    try:
        from ux import require_auth
        player = require_auth(session_token)
        if isinstance(player, RedirectResponse):
            return player
    except Exception:
        return RedirectResponse(url="/login", status_code=303)

    code = code.upper()
    if code not in INDICES:
        return _shell("Not Found", "<p>Index not found. <a href='/banks/indices'>← Back</a></p>",
                      getattr(player, 'cash_balance', 0), getattr(player, 'id', None))

    try:
        from reserve_banks import get_player_display_currency
        disp = get_player_display_currency(player.id)
    except Exception:
        disp = None

    meta  = INDICES[code]
    color = meta["color"]

    # ── Fetch all three timeframes
    snaps30  = _get_history(code, 30)
    snaps7   = _get_history(code, 7)
    snaps1   = _get_history(code, 1)
    snap_now = snaps30[-1] if snaps30 else None

    current = snap_now.value if snap_now else 0.0
    fmted   = _fmt(current, meta["unit"], disp)

    # ── Reference snapshots for % changes
    snap_24h = _snap_near_24h(snaps30)
    if snap_24h is snap_now:
        snap_24h = None
    snap_7d = None
    if snaps30:
        t7 = datetime.utcnow() - timedelta(days=7)
        snap_7d = min(snaps30, key=lambda s: abs((s.timestamp - t7).total_seconds()))
        if snap_7d is snap_now:
            snap_7d = None
    snap_30d = snaps30[0] if len(snaps30) >= 2 else None

    ch24 = _pct_change(current, snap_24h.value) if snap_24h else None
    ch7  = _pct_change(current, snap_7d.value)  if snap_7d  else None
    ch30 = _pct_change(current, snap_30d.value) if snap_30d else None

    # Feature 1: absolute point change (24h)
    pt_change = (current - snap_24h.value) if snap_24h else None

    # Features 2–4: day open / high / low from intraday history
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    snaps_today = [s for s in snaps1 if s.timestamp >= today_start]
    day_open = snaps_today[0].value  if snaps_today else None
    day_high = max(s.value for s in snaps_today) if snaps_today else None
    day_low  = min(s.value for s in snaps_today) if snaps_today else None

    # Feature 5: previous close
    prev_close = _get_prev_close(code)

    # Features 6–7: all-time high / low
    ath, atl = _get_alltime_stats(code) if snaps30 else (None, None)

    # Feature 8: 7-day volatility
    vol7 = _calc_volatility(snaps7)

    # 30-day high / low
    high30 = max(s.value for s in snaps30) if snaps30 else None
    low30  = min(s.value for s in snaps30) if snaps30 else None

    # Position within ATH/ATL range (0–100%)
    range_pct: float | None = None
    if ath and atl and ath > atl:
        range_pct = round((current - atl) / (ath - atl) * 100, 1)

    # Last-updated label + snapshot count
    last_updated = snap_now.timestamp.strftime("%b %d, %H:%M UTC") if snap_now else "—"
    snap_count   = len(snaps30)

    # Mini sparkline for the header
    header_spark = _sparkline_svg(snaps30[-48:], color) if len(snaps30) >= 2 else ""

    # Latest breakdown for pie + heatmap
    breakdown: list[dict] = []
    latest_meta: dict = {}
    if snap_now and snap_now.meta_json:
        try:
            latest_meta = json.loads(snap_now.meta_json)
            breakdown = latest_meta.get("breakdown", [])
        except Exception:
            pass

    # Feature 10: three timeframe datasets for the switchable line chart
    def _cjson(snaps):
        return (json.dumps([s.timestamp.strftime("%m/%d %H:%M") for s in snaps]),
                json.dumps([round(s.value, 6) for s in snaps]))

    lbl24, val24 = _cjson(snaps1)
    lbl7,  val7  = _cjson(snaps7)
    lbl30, val30 = _cjson(snaps30)

    # ── Candlestick (7d)
    ohlcv     = _build_ohlcv(snaps7)
    candle_js = json.dumps(ohlcv)

    # ── Pie chart
    pie_labels = json.dumps([b["label"] for b in breakdown[:12]])
    pie_vals   = json.dumps([b["value"] for b in breakdown[:12]])
    _palette = [
        "#38bdf8","#22c55e","#f59e0b","#a78bfa","#f472b6","#34d399",
        "#fb923c","#84cc16","#06b6d4","#fcd34d","#ef4444","#60a5fa",
    ]
    pie_colors = json.dumps((_palette * 3)[:len(breakdown)])

    heatmap_html = _build_heatmap(code, breakdown, latest_meta, color, meta["unit"], disp)
    no_history   = len(snaps30) < 2

    # ── Display helpers
    def _sv(v):
        if v is None:
            return '<span style="color:#475569;">—</span>'
        return _fmt(v, meta["unit"], disp)

    def _pf(lbl, pct):
        if pct is None:
            return (f'<div class="pf-cell"><span class="pf-lbl">{lbl}</span>'
                    f'<span class="pf-val pf-na">—</span></div>')
        c = "#22c55e" if pct >= 0 else "#ef4444"
        a = "▲" if pct >= 0 else "▼"
        return (f'<div class="pf-cell"><span class="pf-lbl">{lbl}</span>'
                f'<span class="pf-val" style="color:{c};">{a} {abs(pct):.2f}%</span></div>')

    pt_color = "#22c55e" if pt_change is None or pt_change >= 0 else "#ef4444"
    if pt_change is None:
        pt_disp = "—"
    else:
        pt_sign = "+" if pt_change >= 0 else "−"
        pt_disp = f'{pt_sign}{_fmt(abs(pt_change), meta["unit"], disp)}'

    # ── Related indices mini-cards (bonus)
    related_html = ""
    related_codes = _RELATED.get(code, [])
    if related_codes:
        rcards = ""
        for rc in related_codes:
            if rc not in INDICES:
                continue
            rm   = INDICES[rc]
            rs   = _get_latest(rc)
            rv   = rs.value if rs else 0.0
            rfmt = _fmt(rv, rm["unit"], disp)
            rcards += (
                f'<a href="/banks/indices/{rc}" class="rel-card">'
                f'<span style="font-size:1.2rem;flex-shrink:0;">{rm["icon"]}</span>'
                f'<div style="flex:1;min-width:0;">'
                f'<div style="font-size:.6rem;color:{rm["color"]};font-weight:bold;">{rm["code"]}</div>'
                f'<div style="font-size:.7rem;color:#cbd5e1;white-space:nowrap;overflow:hidden;'
                f'text-overflow:ellipsis;">{rm["name"]}</div>'
                f'<div style="font-size:.75rem;color:{rm["color"]};font-weight:bold;">{rfmt}</div>'
                f'</div></a>'
            )
        related_html = (
            '<div style="margin-top:24px;">'
            '<h4 style="color:#94a3b8;font-size:.78rem;text-transform:uppercase;'
            'letter-spacing:.05em;margin:0 0 10px;">Related Indices</h4>'
            f'<div class="rel-grid">{rcards}</div>'
            '</div>'
        )

    body = f"""
    <style>
      .chart-grid {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 16px;
        margin-top: 16px;
      }}
      @media(max-width:700px) {{ .chart-grid {{ grid-template-columns:1fr; }} }}
      .chart-box {{
        background: #0f172a;
        border: 1px solid #1e293b;
        border-radius: 8px;
        padding: 14px;
      }}
      .chart-box h4 {{
        margin: 0 0 10px;
        color: #94a3b8;
        font-size: .78rem;
        text-transform: uppercase;
        letter-spacing: .05em;
      }}
      .stat-row {{
        display: flex; gap: 8px; flex-wrap: wrap; margin: 8px 0;
      }}
      .stat-box {{
        background: #0f172a; border:1px solid #1e293b; border-radius:6px;
        padding: 8px 13px; min-width: 80px;
      }}
      .stat-lbl {{ color:#64748b; font-size:.65rem; text-transform:uppercase;
                   letter-spacing:.04em; white-space:nowrap; }}
      .stat-val {{ font-size:.95rem; font-weight:bold; margin-top:2px; }}
      .perf-row {{ display:flex; gap:0; margin:8px 0; background:#0f172a;
                   border:1px solid #1e293b; border-radius:6px; overflow:hidden; }}
      .pf-cell  {{ flex:1; padding:8px 10px; border-right:1px solid #1e293b; text-align:center; }}
      .pf-cell:last-child {{ border-right:none; }}
      .pf-lbl   {{ font-size:.65rem; color:#64748b; text-transform:uppercase; display:block; }}
      .pf-val   {{ font-size:.85rem; font-weight:bold; display:block; margin-top:2px; }}
      .pf-na    {{ color:#475569; }}
      .method-box {{
        background:#0f172a; border:1px solid #1e293b; border-left:3px solid {color};
        border-radius:6px; padding:9px 13px; margin:8px 0;
        font-size:.78rem; color:#94a3b8; line-height:1.5;
      }}
      .method-box strong {{ color:#e2e8f0; }}
      .tf-tabs  {{ display:flex; gap:5px; }}
      .tf-btn   {{ padding:3px 10px; border-radius:4px; border:1px solid #334155;
                   background:transparent; color:#64748b; font-size:.7rem;
                   cursor:pointer; transition:all .15s; }}
      .tf-btn.active {{ background:{color}22; border-color:{color}; color:{color}; font-weight:bold; }}
      .rel-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(155px, 1fr));
        gap: 10px;
      }}
      .rel-card {{
        background:#0f172a; border:1px solid #1e293b; border-radius:6px;
        padding:10px 12px; text-decoration:none; color:#e2e8f0;
        display:flex; align-items:center; gap:8px;
        transition:background .15s;
      }}
      .rel-card:hover {{ background:#1e293b; text-decoration:none; }}
      .bd-list {{ display:flex; flex-direction:column; gap:5px;
                  max-height:220px; overflow-y:auto; }}
      .bd-row  {{ display:flex; align-items:center; gap:8px; font-size:.72rem; }}
      .bd-label {{ flex:0 0 110px; color:#cbd5e1; white-space:nowrap; overflow:hidden;
                   text-overflow:ellipsis; text-align:right; }}
      .bd-bar-wrap {{ flex:1; background:#1e293b; border-radius:3px; height:14px; }}
      .bd-bar {{ height:100%; border-radius:3px; min-width:2px; }}
      .bd-val  {{ flex:0 0 70px; text-align:right; color:#94a3b8; font-size:.68rem; }}
    </style>

    <a href="/banks/indices" style="color:#38bdf8;font-size:.85rem;">← Indices</a>

    <!-- Header -->
    <div style="margin-top:10px;display:flex;align-items:center;gap:12px;flex-wrap:wrap;justify-content:space-between;">
      <div style="display:flex;align-items:center;gap:12px;">
        <span style="font-size:1.8rem;">{meta['icon']}</span>
        <div>
          <div style="font-size:.7rem;color:{color};font-weight:bold;letter-spacing:.08em;">{meta['code']}</div>
          <h2 style="margin:0;font-size:1.2rem;">{meta['name']}</h2>
        </div>
      </div>
      <div style="display:flex;flex-direction:column;align-items:flex-end;gap:4px;">
        {header_spark}
        <div style="font-size:.63rem;color:#475569;">
          Updated {last_updated} &nbsp;·&nbsp; {snap_count} snapshots (30d)
        </div>
      </div>
    </div>

    <!-- Methodology card -->
    <div class="method-box"><strong>Methodology:</strong> {meta['desc']}</div>

    <!-- Stat row 1: current / point change (feature 1) / day high (feature 3) / day low (feature 4) -->
    <div class="stat-row">
      <div class="stat-box" style="border-top:2px solid {color};">
        <div class="stat-lbl">Current</div>
        <div class="stat-val" style="color:{color};">{fmted}</div>
      </div>
      <div class="stat-box">
        <div class="stat-lbl">Change (24h)</div>
        <div class="stat-val" style="color:{pt_color};">{pt_disp}</div>
      </div>
      <div class="stat-box">
        <div class="stat-lbl">Day High</div>
        <div class="stat-val" style="color:#22c55e;">{_sv(day_high)}</div>
      </div>
      <div class="stat-box">
        <div class="stat-lbl">Day Low</div>
        <div class="stat-val" style="color:#ef4444;">{_sv(day_low)}</div>
      </div>
    </div>

    <!-- Stat row 2: open (feature 2) / prev close (feature 5) / ATH (feature 6) / ATL (feature 7) / vol (feature 8) -->
    <div class="stat-row">
      <div class="stat-box">
        <div class="stat-lbl">Open</div>
        <div class="stat-val">{_sv(day_open)}</div>
      </div>
      <div class="stat-box">
        <div class="stat-lbl">Prev Close</div>
        <div class="stat-val">{_sv(prev_close)}</div>
      </div>
      <div class="stat-box">
        <div class="stat-lbl">All-Time High</div>
        <div class="stat-val" style="color:#22c55e;">{_sv(ath)}</div>
      </div>
      <div class="stat-box">
        <div class="stat-lbl">All-Time Low</div>
        <div class="stat-val" style="color:#ef4444;">{_sv(atl)}</div>
      </div>
      <div class="stat-box">
        <div class="stat-lbl">Volatility (7d)</div>
        <div class="stat-val">{f"{vol7:.2f}%" if vol7 > 0 else '<span style="color:#475569;">—</span>'}</div>
      </div>
    </div>

    <!-- Stat row 3: 30d high / 30d low + ATH/ATL range bar -->
    <div class="stat-row">
      <div class="stat-box">
        <div class="stat-lbl">30D High</div>
        <div class="stat-val" style="color:#22c55e;">{_sv(high30)}</div>
      </div>
      <div class="stat-box">
        <div class="stat-lbl">30D Low</div>
        <div class="stat-val" style="color:#ef4444;">{_sv(low30)}</div>
      </div>
      <div class="stat-box" style="flex:2;min-width:160px;">
        <div class="stat-lbl">Position (ATL → ATH)</div>
        {'<div style="margin-top:5px;"><div style="background:#1e293b;border-radius:4px;height:8px;position:relative;"><div style="position:absolute;left:0;top:0;height:100%;border-radius:4px;background:' + color + ';width:' + str(range_pct) + '%;opacity:.85;"></div></div><div style="display:flex;justify-content:space-between;margin-top:3px;font-size:.6rem;color:#475569;"><span>' + _sv(atl) + '</span><span style="color:' + color + ';font-weight:bold;">' + str(range_pct) + '%</span><span>' + _sv(ath) + '</span></div></div>' if range_pct is not None else '<span style="color:#475569;font-size:.75rem;">—</span>'}
      </div>
    </div>

    <!-- Feature 9: performance band 1D / 7D / 30D -->
    <div class="perf-row">
      {_pf("1D", ch24)}
      {_pf("7D", ch7)}
      {_pf("30D", ch30)}
    </div>

    {'<p style="color:#f59e0b;font-size:.8rem;margin:8px 0;">⚠ Insufficient history for charts — check back once the index has more data.</p>' if no_history else ''}

    <!-- Feature 10: line chart with 24H / 7D / 30D timeframe tabs -->
    <div class="chart-box" style="margin-top:14px;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
        <h4 style="margin:0;">📈 Price History</h4>
        <div class="tf-tabs">
          <button class="tf-btn active" id="tf-24h" onclick="setTf('24H')">24H</button>
          <button class="tf-btn"        id="tf-7d"  onclick="setTf('7D')">7D</button>
          <button class="tf-btn"        id="tf-30d" onclick="setTf('30D')">30D</button>
        </div>
      </div>
      <canvas id="lineChart" height="150"></canvas>
    </div>

    <div class="chart-grid">
      <!-- CANDLESTICK -->
      <div class="chart-box">
        <h4>🕯️ 7-Day OHLCV (Hourly Candles)</h4>
        <div id="candleChart" style="height:180px;"></div>
      </div>

      <!-- PIE CHART -->
      <div class="chart-box">
        <h4>🥧 Composition</h4>
        <canvas id="pieChart" height="180"></canvas>
      </div>

      <!-- BREAKDOWN (full width) -->
      <div class="chart-box" style="grid-column:1/-1;">
        <h4>📊 Top Components</h4>
        <p style="color:#64748b;font-size:.68rem;margin:0 0 8px;">
          Sorted largest to smallest — bar width shows each component's share of the biggest value.
        </p>
        {heatmap_html}
      </div>
    </div>

    {related_html}

    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <script src="https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>

    <script>
    (function() {{
      const COLOR     = {json.dumps(color)};
      const CANDLES   = {candle_js};
      const P_LBL     = {pie_labels};
      const P_VAL     = {pie_vals};
      const P_COL     = {pie_colors};
      const IDX_UNIT  = {json.dumps(meta["unit"])};
      const DISP_SYM  = {json.dumps(disp["symbol"] if disp else "$")};
      const DISP_RATE = {json.dumps(disp["usd_per_unit"] if disp else 1.0)};

      const TF_DATA = {{
        "24H": {{ labels: {lbl24}, vals: {val24} }},
        "7D":  {{ labels: {lbl7},  vals: {val7}  }},
        "30D": {{ labels: {lbl30}, vals: {val30} }},
      }};

      function fmtTick(v) {{
        if (IDX_UNIT === "USD" || IDX_UNIT === "USD/hr" || IDX_UNIT === "USD/mo") {{
          const conv = v / DISP_RATE;
          if (Math.abs(conv) >= 1e9) return DISP_SYM + (conv/1e9).toFixed(1) + 'B';
          if (Math.abs(conv) >= 1e6) return DISP_SYM + (conv/1e6).toFixed(1) + 'M';
          if (Math.abs(conv) >= 1e3) return DISP_SYM + (conv/1e3).toFixed(1) + 'K';
          return DISP_SYM + conv.toFixed(2);
        }}
        if (IDX_UNIT === "%") return v.toFixed(2) + '%';
        if (IDX_UNIT === "ratio") return v.toFixed(3) + '×';
        if (IDX_UNIT === "WSC") return v >= 1e6 ? (v/1e6).toFixed(2)+'M WSC' : v.toFixed(0)+' WSC';
        return v >= 1e6 ? (v/1e6).toFixed(2)+'M' : v >= 1e3 ? (v/1e3).toFixed(1)+'K' : v.toFixed(2);
      }}

      // ── Line chart with timeframe switching
      let lineChart = null;

      function buildLineChart(tf) {{
        const d = TF_DATA[tf];
        const ctx = document.getElementById('lineChart').getContext('2d');
        if (lineChart) lineChart.destroy();
        if (!d || d.vals.length < 2) {{
          ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
          return;
        }}
        lineChart = new Chart(ctx, {{
          type: 'line',
          data: {{
            labels: d.labels,
            datasets: [{{
              data: d.vals,
              borderColor: COLOR,
              backgroundColor: COLOR + '18',
              borderWidth: 1.5,
              fill: true,
              pointRadius: 0,
              tension: 0.3,
            }}]
          }},
          options: {{
            responsive: true,
            plugins: {{
              legend: {{ display: false }},
              tooltip: {{ callbacks: {{ label: c => fmtTick(c.parsed.y) }} }}
            }},
            scales: {{
              x: {{ display: false }},
              y: {{
                grid: {{ color: '#1e293b' }},
                ticks: {{ color: '#64748b', font: {{ size: 10 }}, callback: fmtTick }},
              }}
            }}
          }}
        }});
      }}

      window.setTf = function(tf) {{
        document.querySelectorAll('.tf-btn').forEach(b => b.classList.remove('active'));
        const btn = document.getElementById('tf-' + tf.toLowerCase());
        if (btn) btn.classList.add('active');
        buildLineChart(tf);
      }};

      buildLineChart("24H");

      // ── Candlestick
      if (CANDLES.length >= 2) {{
        const container = document.getElementById('candleChart');
        const chart = LightweightCharts.createChart(container, {{
          width: container.clientWidth || 400, height: 180,
          layout: {{ background: {{ color: '#0f172a' }}, textColor: '#94a3b8' }},
          grid: {{ vertLines: {{ color: '#1e293b' }}, horzLines: {{ color: '#1e293b' }} }},
          rightPriceScale: {{ borderColor: '#1e293b' }},
          timeScale: {{ borderColor: '#1e293b', timeVisible: true }},
          localization: {{ priceFormatter: fmtTick }},
        }});
        const series = chart.addCandlestickSeries({{
          upColor: '#22c55e', downColor: '#ef4444',
          borderUpColor: '#22c55e', borderDownColor: '#ef4444',
          wickUpColor: '#22c55e', wickDownColor: '#ef4444',
          priceFormat: {{ type: 'custom', formatter: fmtTick }},
        }});
        series.setData(CANDLES);
        chart.timeScale().fitContent();
      }} else {{
        document.getElementById('candleChart').innerHTML =
          '<p style="color:#64748b;font-size:.75rem;text-align:center;padding-top:60px;">Insufficient candle data</p>';
      }}

      // ── Pie chart
      if (P_VAL.length > 0 && P_VAL.some(v => v > 0)) {{
        const ctx2 = document.getElementById('pieChart').getContext('2d');
        new Chart(ctx2, {{
          type: 'doughnut',
          data: {{
            labels: P_LBL,
            datasets: [{{ data: P_VAL, backgroundColor: P_COL,
                          borderColor: '#0f172a', borderWidth: 2 }}]
          }},
          options: {{
            responsive: true,
            plugins: {{
              legend: {{
                position: 'right',
                labels: {{ color: '#94a3b8', font: {{ size: 10 }}, boxWidth: 10 }},
              }}
            }}
          }}
        }});
      }} else {{
        document.getElementById('pieChart').style.display = 'none';
        document.getElementById('pieChart').insertAdjacentHTML('afterend',
          '<p style="color:#64748b;font-size:.75rem;">No breakdown data yet.</p>');
      }}
    }})();
    </script>
    """

    tut4 = ""
    try:
        from tutorial_ux import get_tutorial4_overlay_html
        if code == "WBC50":
            tut4 = get_tutorial4_overlay_html(player, "banks_indices_wbc50")
    except Exception:
        pass

    return _shell(meta["name"], tut4 + body + "<script>window._tkCategories=['stocks'];</script>",
                  getattr(player, 'cash_balance', 0), getattr(player, 'id', None))


@router.get("/banks/indices/{code}/unloggedin", response_class=HTMLResponse)
def index_detail_unloggedin(code: str):
    """Same index detail page as /banks/indices/{code} but for unauthenticated visitors."""
    code = code.upper()
    if code not in INDICES:
        return _guest_shell("Not Found", "<p>Index not found. <a href='/banks/indices/unloggedin'>← Back</a></p>")

    disp = None  # no player currency preference for guests

    meta  = INDICES[code]
    color = meta["color"]

    snaps30  = _get_history(code, 30)
    snaps7   = _get_history(code, 7)
    snaps1   = _get_history(code, 1)
    snap_now = snaps30[-1] if snaps30 else None

    current = snap_now.value if snap_now else 0.0
    fmted   = _fmt(current, meta["unit"], disp)

    snap_24h = _snap_near_24h(snaps30)
    if snap_24h is snap_now:
        snap_24h = None
    snap_7d = None
    if snaps30:
        t7 = datetime.utcnow() - timedelta(days=7)
        snap_7d = min(snaps30, key=lambda s: abs((s.timestamp - t7).total_seconds()))
        if snap_7d is snap_now:
            snap_7d = None
    snap_30d = snaps30[0] if len(snaps30) >= 2 else None

    ch24 = _pct_change(current, snap_24h.value) if snap_24h else None
    ch7  = _pct_change(current, snap_7d.value)  if snap_7d  else None
    ch30 = _pct_change(current, snap_30d.value) if snap_30d else None

    pt_change = (current - snap_24h.value) if snap_24h else None

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    snaps_today = [s for s in snaps1 if s.timestamp >= today_start]
    day_open = snaps_today[0].value  if snaps_today else None
    day_high = max(s.value for s in snaps_today) if snaps_today else None
    day_low  = min(s.value for s in snaps_today) if snaps_today else None

    prev_close = _get_prev_close(code)
    ath, atl   = _get_alltime_stats(code) if snaps30 else (None, None)
    vol7       = _calc_volatility(snaps7)

    high30 = max(s.value for s in snaps30) if snaps30 else None
    low30  = min(s.value for s in snaps30) if snaps30 else None

    range_pct: float | None = None
    if ath and atl and ath > atl:
        range_pct = round((current - atl) / (ath - atl) * 100, 1)

    last_updated = snap_now.timestamp.strftime("%b %d, %H:%M UTC") if snap_now else "—"
    snap_count   = len(snaps30)
    header_spark = _sparkline_svg(snaps30[-48:], color) if len(snaps30) >= 2 else ""

    breakdown: list[dict] = []
    latest_meta: dict = {}
    if snap_now and snap_now.meta_json:
        try:
            latest_meta = json.loads(snap_now.meta_json)
            breakdown = latest_meta.get("breakdown", [])
        except Exception:
            pass

    def _cjson(snaps):
        return (json.dumps([s.timestamp.strftime("%m/%d %H:%M") for s in snaps]),
                json.dumps([round(s.value, 6) for s in snaps]))

    lbl24, val24 = _cjson(snaps1)
    lbl7,  val7  = _cjson(snaps7)
    lbl30, val30 = _cjson(snaps30)

    ohlcv     = _build_ohlcv(snaps7)
    candle_js = json.dumps(ohlcv)

    pie_labels = json.dumps([b["label"] for b in breakdown[:12]])
    pie_vals   = json.dumps([b["value"] for b in breakdown[:12]])
    _palette = [
        "#38bdf8","#22c55e","#f59e0b","#a78bfa","#f472b6","#34d399",
        "#fb923c","#84cc16","#06b6d4","#fcd34d","#ef4444","#60a5fa",
    ]
    pie_colors = json.dumps((_palette * 3)[:len(breakdown)])

    heatmap_html = _build_heatmap(code, breakdown, latest_meta, color, meta["unit"], disp)
    no_history   = len(snaps30) < 2

    def _sv(v):
        if v is None:
            return '<span style="color:#475569;">—</span>'
        return _fmt(v, meta["unit"], disp)

    def _pf(lbl, pct):
        if pct is None:
            return (f'<div class="pf-cell"><span class="pf-lbl">{lbl}</span>'
                    f'<span class="pf-val pf-na">—</span></div>')
        c = "#22c55e" if pct >= 0 else "#ef4444"
        a = "▲" if pct >= 0 else "▼"
        return (f'<div class="pf-cell"><span class="pf-lbl">{lbl}</span>'
                f'<span class="pf-val" style="color:{c};">{a} {abs(pct):.2f}%</span></div>')

    pt_color = "#22c55e" if pt_change is None or pt_change >= 0 else "#ef4444"
    if pt_change is None:
        pt_disp = "—"
    else:
        pt_sign = "+" if pt_change >= 0 else "−"
        pt_disp = f'{pt_sign}{_fmt(abs(pt_change), meta["unit"], disp)}'

    related_html = ""
    related_codes = _RELATED.get(code, [])
    if related_codes:
        rcards = ""
        for rc in related_codes:
            if rc not in INDICES:
                continue
            rm   = INDICES[rc]
            rs   = _get_latest(rc)
            rv   = rs.value if rs else 0.0
            rfmt = _fmt(rv, rm["unit"], disp)
            rcards += (
                f'<a href="/banks/indices/{rc}/unloggedin" class="rel-card">'
                f'<span style="font-size:1.2rem;flex-shrink:0;">{rm["icon"]}</span>'
                f'<div style="flex:1;min-width:0;">'
                f'<div style="font-size:.6rem;color:{rm["color"]};font-weight:bold;">{rm["code"]}</div>'
                f'<div style="font-size:.7rem;color:#cbd5e1;white-space:nowrap;overflow:hidden;'
                f'text-overflow:ellipsis;">{rm["name"]}</div>'
                f'<div style="font-size:.75rem;color:{rm["color"]};font-weight:bold;">{rfmt}</div>'
                f'</div></a>'
            )
        related_html = (
            '<div style="margin-top:24px;">'
            '<h4 style="color:#94a3b8;font-size:.78rem;text-transform:uppercase;'
            'letter-spacing:.05em;margin:0 0 10px;">Related Indices</h4>'
            f'<div class="rel-grid">{rcards}</div>'
            '</div>'
        )

    body = f"""
    <style>
      .chart-grid {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 16px;
        margin-top: 16px;
      }}
      @media(max-width:700px) {{ .chart-grid {{ grid-template-columns:1fr; }} }}
      .chart-box {{
        background: #0f172a;
        border: 1px solid #1e293b;
        border-radius: 8px;
        padding: 14px;
      }}
      .chart-box h4 {{
        margin: 0 0 10px;
        color: #94a3b8;
        font-size: .78rem;
        text-transform: uppercase;
        letter-spacing: .05em;
      }}
      .stat-row {{
        display: flex; gap: 8px; flex-wrap: wrap; margin: 8px 0;
      }}
      .stat-box {{
        background: #0f172a; border:1px solid #1e293b; border-radius:6px;
        padding: 8px 13px; min-width: 80px;
      }}
      .stat-lbl {{ color:#64748b; font-size:.65rem; text-transform:uppercase;
                   letter-spacing:.04em; white-space:nowrap; }}
      .stat-val {{ font-size:.95rem; font-weight:bold; margin-top:2px; }}
      .perf-row {{ display:flex; gap:0; margin:8px 0; background:#0f172a;
                   border:1px solid #1e293b; border-radius:6px; overflow:hidden; }}
      .pf-cell  {{ flex:1; padding:8px 10px; border-right:1px solid #1e293b; text-align:center; }}
      .pf-cell:last-child {{ border-right:none; }}
      .pf-lbl   {{ font-size:.65rem; color:#64748b; text-transform:uppercase; display:block; }}
      .pf-val   {{ font-size:.85rem; font-weight:bold; display:block; margin-top:2px; }}
      .pf-na    {{ color:#475569; }}
      .method-box {{
        background:#0f172a; border:1px solid #1e293b; border-left:3px solid {color};
        border-radius:6px; padding:9px 13px; margin:8px 0;
        font-size:.78rem; color:#94a3b8; line-height:1.5;
      }}
      .method-box strong {{ color:#e2e8f0; }}
      .tf-tabs  {{ display:flex; gap:5px; }}
      .tf-btn   {{ padding:3px 10px; border-radius:4px; border:1px solid #334155;
                   background:transparent; color:#64748b; font-size:.7rem;
                   cursor:pointer; transition:all .15s; }}
      .tf-btn.active {{ background:{color}22; border-color:{color}; color:{color}; font-weight:bold; }}
      .rel-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(155px, 1fr));
        gap: 10px;
      }}
      .rel-card {{
        background:#0f172a; border:1px solid #1e293b; border-radius:6px;
        padding:10px 12px; text-decoration:none; color:#e2e8f0;
        display:flex; align-items:center; gap:8px;
        transition:background .15s;
      }}
      .rel-card:hover {{ background:#1e293b; text-decoration:none; }}
      .bd-list {{ display:flex; flex-direction:column; gap:5px;
                  max-height:220px; overflow-y:auto; }}
      .bd-row  {{ display:flex; align-items:center; gap:8px; font-size:.72rem; }}
      .bd-label {{ flex:0 0 110px; color:#cbd5e1; white-space:nowrap; overflow:hidden;
                   text-overflow:ellipsis; text-align:right; }}
      .bd-bar-wrap {{ flex:1; background:#1e293b; border-radius:3px; height:14px; }}
      .bd-bar {{ height:100%; border-radius:3px; min-width:2px; }}
      .bd-val  {{ flex:0 0 70px; text-align:right; color:#94a3b8; font-size:.68rem; }}
    </style>

    <a href="/banks/indices/unloggedin" style="color:#38bdf8;font-size:.85rem;">← Indices</a>

    <!-- Header -->
    <div style="margin-top:10px;display:flex;align-items:center;gap:12px;flex-wrap:wrap;justify-content:space-between;">
      <div style="display:flex;align-items:center;gap:12px;">
        <span style="font-size:1.8rem;">{meta['icon']}</span>
        <div>
          <div style="font-size:.7rem;color:{color};font-weight:bold;letter-spacing:.08em;">{meta['code']}</div>
          <h2 style="margin:0;font-size:1.2rem;">{meta['name']}</h2>
        </div>
      </div>
      <div style="display:flex;flex-direction:column;align-items:flex-end;gap:4px;">
        {header_spark}
        <div style="font-size:.63rem;color:#475569;">
          Updated {last_updated} &nbsp;·&nbsp; {snap_count} snapshots (30d)
        </div>
      </div>
    </div>

    <!-- Methodology card -->
    <div class="method-box"><strong>Methodology:</strong> {meta['desc']}</div>

    <!-- Stat row 1 -->
    <div class="stat-row">
      <div class="stat-box" style="border-top:2px solid {color};">
        <div class="stat-lbl">Current</div>
        <div class="stat-val" style="color:{color};">{fmted}</div>
      </div>
      <div class="stat-box">
        <div class="stat-lbl">Change (24h)</div>
        <div class="stat-val" style="color:{pt_color};">{pt_disp}</div>
      </div>
      <div class="stat-box">
        <div class="stat-lbl">Day High</div>
        <div class="stat-val" style="color:#22c55e;">{_sv(day_high)}</div>
      </div>
      <div class="stat-box">
        <div class="stat-lbl">Day Low</div>
        <div class="stat-val" style="color:#ef4444;">{_sv(day_low)}</div>
      </div>
    </div>

    <!-- Stat row 2 -->
    <div class="stat-row">
      <div class="stat-box">
        <div class="stat-lbl">Open</div>
        <div class="stat-val">{_sv(day_open)}</div>
      </div>
      <div class="stat-box">
        <div class="stat-lbl">Prev Close</div>
        <div class="stat-val">{_sv(prev_close)}</div>
      </div>
      <div class="stat-box">
        <div class="stat-lbl">All-Time High</div>
        <div class="stat-val" style="color:#22c55e;">{_sv(ath)}</div>
      </div>
      <div class="stat-box">
        <div class="stat-lbl">All-Time Low</div>
        <div class="stat-val" style="color:#ef4444;">{_sv(atl)}</div>
      </div>
      <div class="stat-box">
        <div class="stat-lbl">Volatility (7d)</div>
        <div class="stat-val">{f"{vol7:.2f}%" if vol7 > 0 else '<span style="color:#475569;">—</span>'}</div>
      </div>
    </div>

    <!-- Stat row 3 -->
    <div class="stat-row">
      <div class="stat-box">
        <div class="stat-lbl">30D High</div>
        <div class="stat-val" style="color:#22c55e;">{_sv(high30)}</div>
      </div>
      <div class="stat-box">
        <div class="stat-lbl">30D Low</div>
        <div class="stat-val" style="color:#ef4444;">{_sv(low30)}</div>
      </div>
      <div class="stat-box" style="flex:2;min-width:160px;">
        <div class="stat-lbl">Position (ATL → ATH)</div>
        {'<div style="margin-top:5px;"><div style="background:#1e293b;border-radius:4px;height:8px;position:relative;"><div style="position:absolute;left:0;top:0;height:100%;border-radius:4px;background:' + color + ';width:' + str(range_pct) + '%;opacity:.85;"></div></div><div style="display:flex;justify-content:space-between;margin-top:3px;font-size:.6rem;color:#475569;"><span>' + _sv(atl) + '</span><span style="color:' + color + ';font-weight:bold;">' + str(range_pct) + '%</span><span>' + _sv(ath) + '</span></div></div>' if range_pct is not None else '<span style="color:#475569;font-size:.75rem;">—</span>'}
      </div>
    </div>

    <!-- Performance band -->
    <div class="perf-row">
      {_pf("1D", ch24)}
      {_pf("7D", ch7)}
      {_pf("30D", ch30)}
    </div>

    {'<p style="color:#f59e0b;font-size:.8rem;margin:8px 0;">⚠ Insufficient history for charts — check back once the index has more data.</p>' if no_history else ''}

    <!-- Line chart -->
    <div class="chart-box" style="margin-top:14px;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
        <h4 style="margin:0;">📈 Price History</h4>
        <div class="tf-tabs">
          <button class="tf-btn active" id="tf-24h" onclick="setTf('24H')">24H</button>
          <button class="tf-btn"        id="tf-7d"  onclick="setTf('7D')">7D</button>
          <button class="tf-btn"        id="tf-30d" onclick="setTf('30D')">30D</button>
        </div>
      </div>
      <canvas id="lineChart" height="150"></canvas>
    </div>

    <div class="chart-grid">
      <div class="chart-box">
        <h4>🕯️ 7-Day OHLCV (Hourly Candles)</h4>
        <div id="candleChart" style="height:180px;"></div>
      </div>
      <div class="chart-box">
        <h4>🥧 Composition</h4>
        <canvas id="pieChart" height="180"></canvas>
      </div>
      <div class="chart-box" style="grid-column:1/-1;">
        <h4>📊 Top Components</h4>
        <p style="color:#64748b;font-size:.68rem;margin:0 0 8px;">
          Sorted largest to smallest — bar width shows each component's share of the biggest value.
        </p>
        {heatmap_html}
      </div>
    </div>

    {related_html}

    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <script src="https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>

    <script>
    (function() {{
      const COLOR     = {json.dumps(color)};
      const CANDLES   = {candle_js};
      const P_LBL     = {pie_labels};
      const P_VAL     = {pie_vals};
      const P_COL     = {pie_colors};
      const IDX_UNIT  = {json.dumps(meta["unit"])};
      const DISP_SYM  = "$";
      const DISP_RATE = 1.0;

      const TF_DATA = {{
        "24H": {{ labels: {lbl24}, vals: {val24} }},
        "7D":  {{ labels: {lbl7},  vals: {val7}  }},
        "30D": {{ labels: {lbl30}, vals: {val30} }},
      }};

      function fmtTick(v) {{
        if (IDX_UNIT === "USD" || IDX_UNIT === "USD/hr" || IDX_UNIT === "USD/mo") {{
          const conv = v / DISP_RATE;
          if (Math.abs(conv) >= 1e9) return DISP_SYM + (conv/1e9).toFixed(1) + 'B';
          if (Math.abs(conv) >= 1e6) return DISP_SYM + (conv/1e6).toFixed(1) + 'M';
          if (Math.abs(conv) >= 1e3) return DISP_SYM + (conv/1e3).toFixed(1) + 'K';
          return DISP_SYM + conv.toFixed(2);
        }}
        if (IDX_UNIT === "%") return v.toFixed(2) + '%';
        if (IDX_UNIT === "ratio") return v.toFixed(3) + '×';
        if (IDX_UNIT === "WSC") return v >= 1e6 ? (v/1e6).toFixed(2)+'M WSC' : v.toFixed(0)+' WSC';
        return v >= 1e6 ? (v/1e6).toFixed(2)+'M' : v >= 1e3 ? (v/1e3).toFixed(1)+'K' : v.toFixed(2);
      }}

      let lineChart = null;

      function buildLineChart(tf) {{
        const d = TF_DATA[tf];
        const ctx = document.getElementById('lineChart').getContext('2d');
        if (lineChart) lineChart.destroy();
        if (!d || d.vals.length < 2) {{
          ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
          return;
        }}
        lineChart = new Chart(ctx, {{
          type: 'line',
          data: {{
            labels: d.labels,
            datasets: [{{
              data: d.vals,
              borderColor: COLOR,
              backgroundColor: COLOR + '18',
              borderWidth: 1.5,
              fill: true,
              pointRadius: 0,
              tension: 0.3,
            }}]
          }},
          options: {{
            responsive: true,
            plugins: {{
              legend: {{ display: false }},
              tooltip: {{ callbacks: {{ label: c => fmtTick(c.parsed.y) }} }}
            }},
            scales: {{
              x: {{ display: false }},
              y: {{
                grid: {{ color: '#1e293b' }},
                ticks: {{ color: '#64748b', font: {{ size: 10 }}, callback: fmtTick }},
              }}
            }}
          }}
        }});
      }}

      window.setTf = function(tf) {{
        document.querySelectorAll('.tf-btn').forEach(b => b.classList.remove('active'));
        const btn = document.getElementById('tf-' + tf.toLowerCase());
        if (btn) btn.classList.add('active');
        buildLineChart(tf);
      }};

      buildLineChart("24H");

      if (CANDLES.length >= 2) {{
        const container = document.getElementById('candleChart');
        const chart = LightweightCharts.createChart(container, {{
          width: container.clientWidth || 400, height: 180,
          layout: {{ background: {{ color: '#0f172a' }}, textColor: '#94a3b8' }},
          grid: {{ vertLines: {{ color: '#1e293b' }}, horzLines: {{ color: '#1e293b' }} }},
          rightPriceScale: {{ borderColor: '#1e293b' }},
          timeScale: {{ borderColor: '#1e293b', timeVisible: true }},
          localization: {{ priceFormatter: fmtTick }},
        }});
        const series = chart.addCandlestickSeries({{
          upColor: '#22c55e', downColor: '#ef4444',
          borderUpColor: '#22c55e', borderDownColor: '#ef4444',
          wickUpColor: '#22c55e', wickDownColor: '#ef4444',
          priceFormat: {{ type: 'custom', formatter: fmtTick }},
        }});
        series.setData(CANDLES);
        chart.timeScale().fitContent();
      }} else {{
        document.getElementById('candleChart').innerHTML =
          '<p style="color:#64748b;font-size:.75rem;text-align:center;padding-top:60px;">Insufficient candle data</p>';
      }}

      if (P_VAL.length > 0 && P_VAL.some(v => v > 0)) {{
        const ctx2 = document.getElementById('pieChart').getContext('2d');
        new Chart(ctx2, {{
          type: 'doughnut',
          data: {{
            labels: P_LBL,
            datasets: [{{ data: P_VAL, backgroundColor: P_COL,
                          borderColor: '#0f172a', borderWidth: 2 }}]
          }},
          options: {{
            responsive: true,
            plugins: {{
              legend: {{
                position: 'right',
                labels: {{ color: '#94a3b8', font: {{ size: 10 }}, boxWidth: 10 }},
              }}
            }}
          }}
        }});
      }} else {{
        document.getElementById('pieChart').style.display = 'none';
        document.getElementById('pieChart').insertAdjacentHTML('afterend',
          '<p style="color:#64748b;font-size:.75rem;">No breakdown data yet.</p>');
      }}
    }})();
    </script>
    """

    return _guest_shell(meta["name"], body)


def _build_heatmap(code: str, breakdown: list[dict],
                   meta: dict, color: str, unit: str,
                   disp: dict | None = None) -> str:
    """Build a ranked horizontal bar list of index components."""
    if code == "GFI":
        return _gfi_gauge(meta)

    if meta.get("no_data"):
        return '<p style="color:#64748b;font-size:.8rem;">No market trades recorded yet — check back once the economy is active.</p>'

    if not breakdown:
        return '<p style="color:#64748b;font-size:.8rem;">No component data available.</p>'

    sorted_bd = sorted(breakdown, key=lambda b: abs(b["value"]), reverse=True)[:20]
    max_v = max(abs(b["value"]) for b in sorted_bd) or 1.0

    rows = ""
    for b in sorted_bd:
        ratio = abs(b["value"]) / max_v
        pct   = f"{ratio * 100:.0f}%"
        val_disp = _fmt(b["value"], unit, disp)
        rows += (
            f'<div class="bd-row">'
            f'<span class="bd-label" title="{b["label"]}">{b["label"][:16]}</span>'
            f'<div class="bd-bar-wrap">'
            f'<div class="bd-bar" style="width:{pct};background:{color};opacity:.85;"></div>'
            f'</div>'
            f'<span class="bd-val">{val_disp}</span>'
            f'</div>'
        )

    return f'<div class="bd-list">{rows}</div>'


def _gfi_gauge(meta: dict) -> str:
    """SVG arc gauge for Greed & Fear Index."""
    score = meta.get("total", 50)
    label = meta.get("label", "Neutral")
    col   = _gfi_color(score)
    signals = meta.get("breakdown", [])

    # SVG arc (semicircle)
    angle = (score / 100) * 180 - 90  # degrees; -90=left, 90=right
    rad   = math.radians(angle)
    cx, cy, r = 80, 75, 60
    nx = cx + r * math.cos(rad)
    ny = cy + r * math.sin(rad)

    sig_rows = "".join(
        f'<div style="display:flex;justify-content:space-between;padding:2px 0;'
        f'border-bottom:1px solid #1e293b;">'
        f'<span style="color:#94a3b8;font-size:.65rem;">{s["label"]}</span>'
        f'<span style="color:{_gfi_color(s["value"]/(30 if s["label"]=="Momentum" else 25 if s["label"] in ("Breadth","Corp Actions") else 10)*100)};'
        f'font-size:.65rem;font-weight:bold;">{s["value"]:.1f}</span></div>'
        for s in signals
    )

    zone_colors = [
        ("#7f1d1d","Extreme Fear",  "0%"),
        ("#c2410c","Fear",          "25%"),
        ("#ca8a04","Neutral",       "45%"),
        ("#15803d","Greed",         "56%"),
        ("#166534","Extreme Greed", "76%"),
    ]
    zone_html = "".join(
        f'<span style="color:{zc};font-size:.6rem;">{zl}</span>'
        for zc, zl, _ in zone_colors
    )

    return f"""
    <div style="display:flex;gap:12px;flex-wrap:wrap;align-items:flex-start;">
      <div style="text-align:center;">
        <svg width="160" height="90" viewBox="0 0 160 90">
          <!-- Background arc (red→yellow→green) -->
          <defs>
            <linearGradient id="gfiGrad" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%"   stop-color="#dc2626"/>
              <stop offset="25%"  stop-color="#f97316"/>
              <stop offset="50%"  stop-color="#eab308"/>
              <stop offset="75%"  stop-color="#22c55e"/>
              <stop offset="100%" stop-color="#16a34a"/>
            </linearGradient>
          </defs>
          <path d="M20,75 A60,60 0 0,1 140,75"
                fill="none" stroke="url(#gfiGrad)" stroke-width="10"
                stroke-linecap="round"/>
          <!-- Needle -->
          <line x1="{cx}" y1="{cy}"
                x2="{nx:.1f}" y2="{ny:.1f}"
                stroke="{col}" stroke-width="2.5" stroke-linecap="round"/>
          <circle cx="{cx}" cy="{cy}" r="4" fill="{col}"/>
          <!-- Score label -->
          <text x="{cx}" y="88" text-anchor="middle"
                fill="{col}" font-size="13" font-weight="bold">{score:.0f}</text>
        </svg>
        <div style="color:{col};font-weight:bold;font-size:.8rem;margin-top:2px;">{label}</div>
      </div>
      <div style="flex:1;min-width:120px;">
        <div style="font-size:.65rem;color:#64748b;margin-bottom:4px;">SIGNAL BREAKDOWN</div>
        {sig_rows}
      </div>
    </div>"""


# ─────────────────────────────────────────────────────────────────────────────
# LIFECYCLE
# ─────────────────────────────────────────────────────────────────────────────

_tick_counter = 0
SAMPLE_EVERY  = 120   # 120 ticks × 5 s = 10 minutes

# ── Index push alerts (GFI zone transitions, large WBC-50 daily moves) ────────

WBC50_ALERT_PCT = 5.0    # alert when |24h move| reaches this percentage

_last_gfi_zone: Optional[str] = None     # zone at the previous snapshot
_last_wbc50_alert_day: Optional[str] = None   # UTC date of the last WBC-50 alert


def _gfi_zone(score: float) -> str:
    if score <= 24: return "Extreme Fear"
    if score <= 44: return "Fear"
    if score <= 55: return "Neutral"
    if score <= 75: return "Greed"
    return "Extreme Greed"


def _broadcast_index_alert(title: str, body: str, tag: str) -> None:
    """Push an index alert to every subscribed player (respects the
    notif_push_indices preference via send_push_notification)."""
    try:
        from push_ux import send_push_notification
        from auth import get_db as _adb, PushSubscription
        adb = _adb()
        try:
            pids = [r[0] for r in adb.query(PushSubscription.player_id).distinct().all()]
        finally:
            adb.close()
        for pid in pids:
            try:
                send_push_notification(pid, title, body, url="/banks/indices",
                                       notif_type="indices", tag=tag)
            except Exception:
                pass
    except Exception as e:
        print(f"[Indices] alert broadcast failed: {e}")


def _check_index_alerts():
    """Run after each snapshot cycle. Fires:
    • GFI alert when sentiment TRANSITIONS into an extreme zone.
    • WBC-50 alert when the 24h move first reaches ±WBC50_ALERT_PCT (max once/day).
    State is in-memory; a server restart at most repeats one alert (same push tag
    collapses duplicates on the device)."""
    global _last_gfi_zone, _last_wbc50_alert_day
    try:
        # ── GFI zone transition ───────────────────────────────────────────────
        gfi = _get_latest("GFI")
        if gfi:
            zone = _gfi_zone(gfi.value)
            if _last_gfi_zone is None:
                _last_gfi_zone = zone   # baseline only — no alert on first cycle
            elif zone != _last_gfi_zone:
                if zone in ("Extreme Fear", "Extreme Greed"):
                    emoji = "🚨" if zone == "Extreme Fear" else "🔥"
                    _broadcast_index_alert(
                        f"{emoji} Market Sentiment: {zone}",
                        f"The Greed & Fear Index hit {gfi.value:.0f} — {zone}. "
                        + ("Extreme fear has historically preceded recoveries."
                           if zone == "Extreme Fear" else
                           "Markets may be overheated — consider taking profits."),
                        tag=f"gfi-{zone.lower().replace(' ', '-')}",
                    )
                _last_gfi_zone = zone

        # ── WBC-50 large 24h move ─────────────────────────────────────────────
        today = datetime.utcnow().strftime("%Y-%m-%d")
        if _last_wbc50_alert_day != today:
            snaps = _get_history("WBC50", 1)
            if len(snaps) >= 2 and snaps[0].value:
                pct = (snaps[-1].value - snaps[0].value) / abs(snaps[0].value) * 100
                if abs(pct) >= WBC50_ALERT_PCT:
                    arrow = "📈" if pct > 0 else "📉"
                    _broadcast_index_alert(
                        f"{arrow} WBC-50 {'+' if pct > 0 else ''}{pct:.1f}% in 24h",
                        f"The Wadsworth Blue-Chip 50 moved {pct:+.1f}% over the last "
                        f"24 hours to {_fmt(snaps[-1].value, 'USD')}.",
                        tag=f"wbc50-move-{today}",
                    )
                    _last_wbc50_alert_day = today
    except Exception as e:
        print(f"[Indices] alert check error: {e}")


def initialize():
    """Create table and take an initial snapshot if none exist."""
    Base.metadata.create_all(engine)
    db = _get_db()
    try:
        count = db.query(IndexSnapshot).count()
    finally:
        db.close()
    if count == 0:
        print("[Indices] No snapshots found – seeding initial data…")
        calculate_all_indices()
    else:
        print(f"[Indices] {count} snapshots found.")


async def tick(tick_number: int, now: datetime):
    global _tick_counter
    _tick_counter += 1
    if _tick_counter >= SAMPLE_EVERY:
        _tick_counter = 0
        calculate_all_indices()
        _check_index_alerts()
