from __future__ import annotations
import asyncio
import time
from typing import Dict

from fastapi import APIRouter, WebSocket

router = APIRouter()


class _PlayerFeedManager:
    def __init__(self):
        self._conns: Dict[int, WebSocket] = {}

    async def connect(self, ws: WebSocket, player_id: int):
        self._conns[player_id] = ws

    def disconnect(self, player_id: int):
        self._conns.pop(player_id, None)

    @property
    def connected_ids(self):
        return list(self._conns.keys())

    async def send(self, player_id: int, payload: dict):
        ws = self._conns.get(player_id)
        if ws:
            try:
                await ws.send_json(payload)
            except Exception:
                self.disconnect(player_id)


_mgr = _PlayerFeedManager()
_BROADCAST_EVERY = 6  # ticks (~30 s at 5 s/tick)


# ── WebSocket endpoint ──────────────────────────────────────────────────────

@router.websocket("/ws/player-feed")
async def player_feed_ws(websocket: WebSocket):
    await websocket.accept()
    session_token = websocket.cookies.get("session_token")
    if not session_token:
        await websocket.close(code=4001, reason="Not authenticated")
        return
    from auth import validate_session_ws
    player = validate_session_ws(session_token)
    if not player:
        await websocket.close(code=4001, reason="Not authenticated")
        return

    await _mgr.connect(websocket, player.id)
    # Push current balance immediately so the client doesn't wait up to 30 s.
    await _send_state(player.id)
    try:
        while True:
            await websocket.receive_text()  # keep-alive; client sends nothing
    except Exception:
        pass
    finally:
        _mgr.disconnect(player.id)


# ── Tick integration ────────────────────────────────────────────────────────

async def tick(current_tick: int, now):
    if not _mgr.connected_ids:
        return
    if current_tick % _BROADCAST_EVERY != 0:
        return
    loop = asyncio.get_event_loop()
    for pid in list(_mgr.connected_ids):
        loop.create_task(_send_state(pid))


async def _send_state(player_id: int):
    try:
        loop = asyncio.get_event_loop()
        payload = await loop.run_in_executor(None, _build_payload, player_id)
        await _mgr.send(player_id, payload)
    except Exception as e:
        print(f"[PlayerFeed] send error for player {player_id}: {e}")


def _build_payload(player_id: int) -> dict:
    from reserve_banks import (
        get_usd_balance,
        get_player_currency_balances,
        get_player_legal_tender,
    )
    usd_bal = get_usd_balance(player_id)
    tender  = get_player_legal_tender(player_id)

    sym, bal, note = "$", usd_bal, ""
    if tender != "USD":
        try:
            for b in get_player_currency_balances(player_id):
                if b["currency_code"] == tender:
                    sym  = b["currency_symbol"]
                    bal  = b["balance"]
                    note = f" / ${usd_bal:,.2f} USD"
                    break
        except Exception:
            pass

    return {
        "type":    "balance",
        "display": f"{sym}{bal:,.2f}{note}",
        "ts":      int(time.time()),
    }
