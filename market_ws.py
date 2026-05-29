"""
market_ws.py
Real-time market price broadcast via WebSocket (/ws/markets).

Every N game ticks the server pushes a full snapshot to every connected
client so market pages can update prices without a page refresh.
Only runs DB queries when at least one client is connected.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

_connections: Set[WebSocket] = set()
_last_snapshot: dict = {}
_BROADCAST_EVERY = 6   # ticks (~30 s at 5 s/tick)
_snapshot_lock = asyncio.Lock()  # serialises concurrent snapshot writes


# ── WebSocket endpoint ────────────────────────────────────────────────────────

@router.websocket("/ws/markets")
async def markets_ws(ws: WebSocket):
    await ws.accept()
    _connections.add(ws)
    if _last_snapshot:
        try:
            await ws.send_text(json.dumps(_last_snapshot))
        except Exception:
            pass
    try:
        while True:
            try:
                await asyncio.wait_for(ws.receive_text(), timeout=30.0)
            except asyncio.TimeoutError:
                try:
                    await ws.send_text('{"type":"ping"}')
                except Exception:
                    break
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        _connections.discard(ws)


# ── Snapshot collection (sync — runs in executor) ─────────────────────────────

def collect_snapshot() -> dict:
    snap = {
        "type":        "snapshot",
        "ts":          int(time.time()),
        "commodities": [],
        "district":    [],
        "forex":       [],
        "stocks":      [],
        "crypto":      [],
        "memes":       [],
        "land":        {},
    }
    cutoff = datetime.utcnow() - timedelta(hours=24)

    # ── Main DB: commodities + district items + land ──────────────────────────
    try:
        from database import SessionLocal
        from sqlalchemy import func
        db = SessionLocal()
        try:
            # --- Commodity last-trade price per item, with 24 h change -------
            from market import Trade as _CT
            sub = (db.query(_CT.item_type, func.max(_CT.executed_at).label("lat"))
                     .group_by(_CT.item_type).subquery())
            last_c = (db.query(_CT)
                        .join(sub, (_CT.item_type == sub.c.item_type) &
                                   (_CT.executed_at == sub.c.lat)).all())
            sub24c = (db.query(_CT.item_type, func.max(_CT.executed_at).label("lat"))
                        .filter(_CT.executed_at <= cutoff)
                        .group_by(_CT.item_type).subquery())
            old_c = {t.item_type: float(t.price) for t in
                     db.query(_CT).join(sub24c, (_CT.item_type == sub24c.c.item_type) &
                                                (_CT.executed_at == sub24c.c.lat)).all()}
            for t in last_c:
                p = float(t.price or 0)
                o = old_c.get(t.item_type, 0)
                snap["commodities"].append({
                    "symbol":     t.item_type,
                    "label":      t.item_type.replace("_", " ").title(),
                    "price":      round(p, 4),
                    "change_24h": round((p - o) / o * 100, 2) if o > 0 else 0.0,
                })

            # --- District item last-trade price ------------------------------
            from district_market import DistrictTrade as _DT
            dsub = (db.query(_DT.item_type, func.max(_DT.executed_at).label("lat"))
                      .group_by(_DT.item_type).subquery())
            last_d = (db.query(_DT)
                        .join(dsub, (_DT.item_type == dsub.c.item_type) &
                                    (_DT.executed_at == dsub.c.lat)).all())
            dsub24 = (db.query(_DT.item_type, func.max(_DT.executed_at).label("lat"))
                        .filter(_DT.executed_at <= cutoff)
                        .group_by(_DT.item_type).subquery())
            old_d = {t.item_type: float(t.price) for t in
                     db.query(_DT).join(dsub24, (_DT.item_type == dsub24.c.item_type) &
                                                (_DT.executed_at == dsub24.c.lat)).all()}
            for t in last_d:
                p = float(t.price or 0)
                o = old_d.get(t.item_type, 0)
                snap["district"].append({
                    "symbol":     t.item_type,
                    "label":      t.item_type.replace("_", " ").title(),
                    "price":      round(p, 4),
                    "change_24h": round((p - o) / o * 100, 2) if o > 0 else 0.0,
                })

            # --- Land market summary -----------------------------------------
            from land_market import GovernmentAuction as _GA, LandListing as _LL
            a_cnt = db.query(_GA).filter(_GA.is_active == True).count()
            a_avg = db.query(func.avg(_GA.current_price)).filter(_GA.is_active == True).scalar() or 0
            l_cnt = db.query(_LL).filter(_LL.is_active == True).count()
            l_avg = db.query(func.avg(_LL.asking_price)).filter(_LL.is_active == True).scalar() or 0
            snap["land"] = {
                "active_auctions":   a_cnt,
                "avg_auction_price": round(float(a_avg), 2),
                "active_listings":   l_cnt,
                "avg_listing_price": round(float(l_avg), 2),
            }
        finally:
            db.close()
    except Exception as e:
        print(f"[MarketWS] main-db: {e}")

    # ── Reserve DB: forex rates ───────────────────────────────────────────────
    try:
        from database import ReserveSessionLocal
        from reserve_banks import StateReserveBank as _SRB, BondYieldHistory as _BYH
        rdb = ReserveSessionLocal()
        try:
            for bank in rdb.query(_SRB).all():
                rate = float(bank.usd_per_unit or 0)
                chg = 0.0
                try:
                    hist = (rdb.query(_BYH)
                              .filter(_BYH.bank_id == bank.id,
                                      _BYH.recorded_at <= cutoff)
                              .order_by(_BYH.recorded_at.desc()).first())
                    if hist and hist.usd_per_unit and float(hist.usd_per_unit) > 0:
                        chg = round((rate - float(hist.usd_per_unit)) /
                                    float(hist.usd_per_unit) * 100, 4)
                except Exception:
                    pass
                snap["forex"].append({
                    "pair":      f"{bank.currency_code}/USD",
                    "symbol":    bank.currency_code,
                    "name":      getattr(bank, "currency_name", None) or bank.currency_code,
                    "rate":      round(rate, 6),
                    "change_24h": chg,
                })
        finally:
            rdb.close()
    except Exception as e:
        print(f"[MarketWS] forex: {e}")

    # ── Brokerage DB: listed stocks ───────────────────────────────────────────
    try:
        from banks.brokerage_firm import CompanyShares as _CS, get_db as _bdb
        bdb = _bdb()
        try:
            for s in (bdb.query(_CS)
                        .filter(_CS.is_delisted == False, _CS.parent_company_id == None)
                        .all()):
                p = float(s.current_price or 0)
                ipo = float(s.ipo_price or 0)
                snap["stocks"].append({
                    "ticker":     s.ticker_symbol,
                    "name":       s.company_name,
                    "price":      round(p, 4),
                    "change_24h": round((p - ipo) / ipo * 100, 2) if ipo > 0 else 0.0,
                    "volume":     int(getattr(s, "volume_today", 0) or 0),
                })
        finally:
            bdb.close()
    except Exception as e:
        print(f"[MarketWS] stocks: {e}")

    # ── County DB: native tokens ──────────────────────────────────────────────
    try:
        from counties import get_db as _cdb, County as _Cty, get_crypto_price_by_symbol
        cdb = _cdb()
        try:
            for county in cdb.query(_Cty).all():
                try:
                    usd = float(get_crypto_price_by_symbol(county.crypto_symbol) or 0)
                except Exception:
                    usd = 0.0
                snap["crypto"].append({
                    "symbol":    county.crypto_symbol,
                    "name":      getattr(county, "crypto_name", None) or county.name,
                    "county":    county.name,
                    "price_usd": round(usd, 6),
                    "change_24h": 0.0,
                })
        finally:
            cdb.close()
    except Exception as e:
        print(f"[MarketWS] crypto: {e}")

    # ── Meme-coins DB ─────────────────────────────────────────────────────────
    try:
        from memecoins import get_db as _mdb, MemeCoin as _MC, _get_meme_price_change_24h
        mdb = _mdb()
        try:
            for m in (mdb.query(_MC).filter(_MC.is_active == True)
                        .order_by(_MC.total_volume_native.desc()).limit(100).all()):
                try:
                    chg = float(_get_meme_price_change_24h(mdb, m.symbol, m.last_price or 0.0))
                except Exception:
                    chg = 0.0
                snap["memes"].append({
                    "symbol":     m.symbol,
                    "name":       m.name,
                    "price":      round(float(m.last_price or 0), 8),
                    "change_24h": round(chg, 2),
                    "county_id":  m.county_id,
                })
        finally:
            mdb.close()
    except Exception as e:
        print(f"[MarketWS] memes: {e}")

    return snap


# ── Game-tick integration ─────────────────────────────────────────────────────

async def _broadcast(snap: dict) -> None:
    """Serialize _last_snapshot write and fan-out to all connections. Shared by tick() and push."""
    global _last_snapshot, _connections
    async with _snapshot_lock:
        _last_snapshot = snap
        payload = json.dumps(snap)
    dead = set()
    for ws in list(_connections):
        try:
            await ws.send_text(payload)
        except Exception as e:
            print(f"[MarketWS] send failed, dropping connection: {e}")
            dead.add(ws)
    if dead:
        _connections -= dead


async def tick(current_tick: int, now: datetime):
    if current_tick % _BROADCAST_EVERY != 0:
        return
    if not _connections:
        return
    try:
        loop = asyncio.get_running_loop()
        snap = await loop.run_in_executor(None, collect_snapshot)
        await _broadcast(snap)
    except Exception as e:
        print(f"[MarketWS] tick error: {e}")


async def push_market_snapshot_now() -> None:
    """Push an immediate snapshot to all connected market clients (fire-and-forget)."""
    if not _connections:
        return
    try:
        loop = asyncio.get_running_loop()
        snap = await loop.run_in_executor(None, collect_snapshot)
        await _broadcast(snap)
    except Exception as e:
        print(f"[MarketWS] push error: {e}")


def initialize():
    pass
