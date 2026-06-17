"""
advisor_ux.py

Wadsworth **Financial Advisor** — a Pro-gated, bring-your-own-key AI assistant.

Architecture & security model (see also the approved plan):
- The advisor is a **stateless proxy**. Players supply their own Google Gemini API key
  (named, switchable wallet); their account bears the cost. The server forwards one request
  and returns the reply — it never stores conversations.
- The model is **pure text-in / text-out**. It is given NO tools and NO database access.
  Everything it can ever know is (a) the hand-written game-knowledge document in
  advisor_knowledge.py and (b) a fixed-allowlist text summary of the *authenticated* player's
  OWN data built by `_build_player_context`. There is therefore no path by which a player
  could extract source code, server secrets, or another player's private data through it.
- API keys are encrypted at rest with AES-256-GCM (pycryptodome, already a dependency — the
  same library used for VAPID). The encryption key lives in env ADVISOR_ENC_KEY or, if unset,
  is generated once and persisted in system_config (mirrors push_ux's VAPID-key pattern).
  Plaintext keys are never returned to the browser (UI shows last-4 only) and never logged.

Owns its own `advisor_credentials` table via run_ddl_migration, mirroring bluesky.py.
"""

import os
import json
import base64
from typing import Optional, List

import requests
from fastapi import APIRouter, Cookie, Form, Body
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse


# ==========================
# CONSTANTS
# ==========================

# Single model id kept here so swapping is one-line. gemini-2.5-flash is free-tier eligible.
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)
HTTP_TIMEOUT = 30  # seconds; the chat call is the only outbound request

_ENC_CONFIG_KEY = "advisor_enc_key"   # system_config row name for the at-rest AES key
_CHAT_COOLDOWN_SECS = 2               # light anti-loop guard (cost is on the player, not us)
_MAX_TURNS = 40                       # cap conversation length forwarded per request


# ==========================
# SCHEMA
# ==========================

def _ensure_table():
    from database import engine, run_ddl_migration
    run_ddl_migration(engine, [
        """CREATE TABLE IF NOT EXISTS advisor_credentials (
                id              SERIAL      PRIMARY KEY,
                player_id       INTEGER     NOT NULL,
                credential_name TEXT        NOT NULL,
                provider        TEXT        NOT NULL DEFAULT 'gemini',
                api_key_enc     TEXT        NOT NULL,
                key_last4       TEXT        NOT NULL,
                is_active       BOOLEAN     NOT NULL DEFAULT FALSE,
                created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE (player_id, credential_name)
            )""",
        "CREATE INDEX IF NOT EXISTS idx_advisor_cred_player ON advisor_credentials (player_id)",
    ])


def initialize():
    _ensure_table()
    print("[Advisor] Financial Advisor module initialized")


# ==========================
# AT-REST ENCRYPTION (AES-256-GCM via pycryptodome)
# ==========================

_enc_key_cache: Optional[bytes] = None


def _get_enc_key() -> bytes:
    """32-byte AES key. Prefers env ADVISOR_ENC_KEY (base64); otherwise loads/creates a key in
    the system_config table so it survives restarts (mirrors push_ux VAPID persistence)."""
    global _enc_key_cache
    if _enc_key_cache is not None:
        return _enc_key_cache

    env = os.environ.get("ADVISOR_ENC_KEY")
    if env:
        try:
            k = base64.b64decode(env)
            if len(k) == 32:
                _enc_key_cache = k
                return k
        except Exception:
            print("[Advisor] ADVISOR_ENC_KEY is set but not valid base64-32; falling back to DB key")

    # Load from / create in system_config
    from database import engine
    from sqlalchemy import text
    try:
        with engine.connect() as c:
            row = c.execute(text(
                "SELECT value FROM system_config WHERE key = :k LIMIT 1"
            ), {"k": _ENC_CONFIG_KEY}).fetchone()
        if row and row[0]:
            k = base64.b64decode(row[0])
            if len(k) == 32:
                _enc_key_cache = k
                return k
    except Exception as e:
        print(f"[Advisor] Could not read enc key from DB: {e}")

    # Generate + persist
    from Crypto.Random import get_random_bytes
    k = get_random_bytes(32)
    try:
        with engine.connect() as c:
            c.execute(text(
                "INSERT INTO system_config (key, value) VALUES (:k, :v) "
                "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value"
            ), {"k": _ENC_CONFIG_KEY, "v": base64.b64encode(k).decode()})
            c.commit()
    except Exception as e:
        print(f"[Advisor] Could not persist enc key to DB: {e}")
    _enc_key_cache = k
    return k


def _encrypt(plain: str) -> str:
    """AES-256-GCM. Token = base64(nonce[12] || tag[16] || ciphertext)."""
    from Crypto.Cipher import AES
    from Crypto.Random import get_random_bytes
    nonce = get_random_bytes(12)
    cipher = AES.new(_get_enc_key(), AES.MODE_GCM, nonce=nonce)
    ct, tag = cipher.encrypt_and_digest(plain.encode("utf-8"))
    return base64.b64encode(nonce + tag + ct).decode("ascii")


def _decrypt(token: str) -> Optional[str]:
    from Crypto.Cipher import AES
    try:
        raw = base64.b64decode(token)
        nonce, tag, ct = raw[:12], raw[12:28], raw[28:]
        cipher = AES.new(_get_enc_key(), AES.MODE_GCM, nonce=nonce)
        return cipher.decrypt_and_verify(ct, tag).decode("utf-8")
    except Exception as e:
        print(f"[Advisor] Decrypt failed: {e}")
        return None


# ==========================
# CREDENTIAL WALLET (raw SQL, mirrors bluesky.py)
# ==========================

def _detect_provider(api_key: str) -> Optional[str]:
    """Return the provider for a key, or None if unrecognized. Gemini only at launch."""
    k = (api_key or "").strip()
    if k.startswith("AIza"):
        return "gemini"
    return None


def list_credentials(player_id: int) -> List[dict]:
    """Saved credentials for a player (NO plaintext key — last4 + metadata only)."""
    from auth import get_db
    from sqlalchemy import text
    db = get_db()
    try:
        rows = db.execute(text(
            "SELECT id, credential_name, provider, key_last4, is_active, created_at "
            "FROM advisor_credentials WHERE player_id = :pid ORDER BY created_at"
        ), {"pid": player_id}).mappings().all()
    finally:
        db.close()
    return [dict(r) for r in rows]


def get_active_credential(player_id: int) -> Optional[dict]:
    """The active credential incl. decrypted key, for server-side use only. Never serialized
    to the client. Falls back to the most recent credential if none is flagged active."""
    from auth import get_db
    from sqlalchemy import text
    db = get_db()
    try:
        row = db.execute(text(
            "SELECT id, credential_name, provider, api_key_enc, key_last4 "
            "FROM advisor_credentials WHERE player_id = :pid AND is_active = TRUE "
            "ORDER BY created_at DESC LIMIT 1"
        ), {"pid": player_id}).mappings().first()
        if not row:
            row = db.execute(text(
                "SELECT id, credential_name, provider, api_key_enc, key_last4 "
                "FROM advisor_credentials WHERE player_id = :pid "
                "ORDER BY created_at DESC LIMIT 1"
            ), {"pid": player_id}).mappings().first()
    finally:
        db.close()
    if not row:
        return None
    rec = dict(row)
    rec["api_key"] = _decrypt(rec.pop("api_key_enc"))
    return rec


def add_credential(player_id: int, name: str, api_key: str) -> tuple[bool, str]:
    name = (name or "").strip()[:60] or "My key"
    api_key = (api_key or "").strip()
    provider = _detect_provider(api_key)
    if not provider:
        return False, "That doesn't look like a Google Gemini API key (expected to start with 'AIza')."
    from auth import get_db
    from sqlalchemy import text
    db = get_db()
    try:
        # First credential becomes active automatically.
        existing = db.execute(text(
            "SELECT COUNT(*) FROM advisor_credentials WHERE player_id = :pid"
        ), {"pid": player_id}).scalar() or 0
        make_active = existing == 0
        if make_active:
            db.execute(text("UPDATE advisor_credentials SET is_active = FALSE WHERE player_id = :pid"),
                       {"pid": player_id})
        db.execute(text(
            "INSERT INTO advisor_credentials "
            "(player_id, credential_name, provider, api_key_enc, key_last4, is_active) "
            "VALUES (:pid, :name, :prov, :enc, :last4, :active) "
            "ON CONFLICT (player_id, credential_name) DO UPDATE SET "
            "  api_key_enc = EXCLUDED.api_key_enc, key_last4 = EXCLUDED.key_last4, "
            "  provider = EXCLUDED.provider"
        ), {"pid": player_id, "name": name, "prov": provider,
            "enc": _encrypt(api_key), "last4": api_key[-4:], "active": make_active})
        db.commit()
    except Exception as e:
        db.rollback()
        return False, f"Could not save credential: {e}"
    finally:
        db.close()
    return True, "Saved."


def activate_credential(player_id: int, cred_id: int):
    from auth import get_db
    from sqlalchemy import text
    db = get_db()
    try:
        db.execute(text("UPDATE advisor_credentials SET is_active = FALSE WHERE player_id = :pid"),
                   {"pid": player_id})
        db.execute(text(
            "UPDATE advisor_credentials SET is_active = TRUE "
            "WHERE id = :cid AND player_id = :pid"
        ), {"cid": cred_id, "pid": player_id})
        db.commit()
    finally:
        db.close()


def delete_credential(player_id: int, cred_id: int):
    from auth import get_db
    from sqlalchemy import text
    db = get_db()
    try:
        db.execute(text("DELETE FROM advisor_credentials WHERE id = :cid AND player_id = :pid"),
                   {"cid": cred_id, "pid": player_id})
        db.commit()
    finally:
        db.close()


# ==========================
# PER-PLAYER CONTEXT  (fixed allowlist assembler — the ONLY data the model ever sees)
# ==========================

def _build_player_context(player_id: int) -> str:
    """Assemble a compact plain-text summary of THIS player's own game data.

    This is a fixed allowlist: it calls only known per-player helpers, every query scoped to
    `player_id`. It never reads secrets, config, os.environ, password hashes, or any other
    player's rows. Each section is independently guarded so a missing module degrades the
    summary instead of breaking it. Mirrors the data sources in
    contacts.build_contact_card_html, but emits text rather than HTML.
    """
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player_id)

    def money(amount) -> str:
        try:
            return fmt_usd(amount or 0, disp)
        except Exception:
            return f"${(amount or 0):,.2f}"

    lines: List[str] = []

    # Identity / level / Pro
    try:
        from auth import Player, get_db as _adb
        db = _adb()
        try:
            p = db.query(Player).filter(Player.id == player_id).first()
            name = p.business_name if p else f"Player #{player_id}"
            cash = p.cash_balance if p else 0
            subscriber = bool(getattr(p, "subscriber", False)) if p else False
        finally:
            db.close()
        lines.append(f"Name: {name} (Player ID #{player_id})")
        lines.append(f"USD cash on hand: {money(cash)}")
    except Exception:
        name, cash, subscriber = f"Player #{player_id}", 0, False

    try:
        from admins import is_admin as _ia
        is_pro = subscriber or bool(_ia(player_id))
    except Exception:
        is_pro = subscriber
    lines.append(f"Wadsworth Pro: {'yes' if is_pro else 'no'}")

    try:
        from events import get_player_level
        lv = get_player_level(player_id)
        lines.append(f"Level {lv['level']} · {lv['trophies']:,} trophies")
    except Exception:
        pass

    # Net worth & leaderboard
    try:
        from stats_ux import PlayerStats, get_db as _sdb
        sdb = _sdb()
        try:
            ps = sdb.query(PlayerStats).filter(PlayerStats.player_id == player_id).first()
        finally:
            sdb.close()
        if ps:
            lines.append("")
            lines.append("NET WORTH & LEADERBOARD:")
            lines.append(f"  Total net worth: {money(ps.total_net_worth)} (wealth rank #{ps.wealth_rank or '—'})")
            lines.append(f"  Land value: {money(ps.land_value)} | Inventory: {money(ps.inventory_value)} "
                         f"| Business: {money(ps.business_value)}")
            lines.append(f"  Share value: {money(ps.share_value)} | District value: {money(ps.district_value or 0)} "
                         f"| Cash (all currencies): {money(ps.cash_balance or 0)}")
            lines.append(f"  Lands owned: {ps.lands_owned} | Businesses: {ps.businesses_owned} "
                         f"| Districts: {ps.districts_owned}")
    except Exception:
        pass

    # Foreign currency balances + legal tender
    try:
        from reserve_banks import PlayerCurrencyBalance, get_db as _rdb
        rdb = _rdb()
        try:
            bals = rdb.query(PlayerCurrencyBalance).filter(
                PlayerCurrencyBalance.player_id == player_id).all()
        finally:
            rdb.close()
        held = [f"{b.currency_code} {b.balance:,.2f}" for b in bals if b.balance and b.balance > 0]
        if held:
            lines.append("  Foreign currency balances: " + ", ".join(held))
    except Exception:
        pass
    lines.append(f"  Legal tender: {disp.get('flag','')} {disp.get('code','USD')} ({disp.get('symbol','$')})")

    # Debt
    try:
        from estate import calculate_total_debts
        from database import SessionLocal as _SL
        ddb = _SL()
        try:
            debt = calculate_total_debts(player_id, ddb)
        finally:
            ddb.close()
        lines.append(f"  Total outstanding debt: {money(debt)}" if debt and debt > 0
                     else "  Total outstanding debt: none")
    except Exception:
        pass

    # Inventory (top holdings)
    try:
        from inventory import get_player_inventory
        inv = {k: v for k, v in (get_player_inventory(player_id) or {}).items() if v and v > 0}
        if inv:
            top = sorted(inv.items(), key=lambda kv: -kv[1])[:15]
            lines.append("")
            lines.append("INVENTORY (top items): " + ", ".join(
                f"{k.replace('_',' ')} {v:,.1f}" for k, v in top))
    except Exception:
        pass

    # Businesses
    try:
        from business import Business, BUSINESS_TYPES
        from database import SessionLocal as _SL2
        bdb = _SL2()
        try:
            bizs = bdb.query(Business).filter(
                Business.owner_id == player_id, Business.is_active == True).all()
        finally:
            bdb.close()
        if bizs:
            names = [BUSINESS_TYPES.get(b.business_type, {}).get("name",
                     b.business_type.replace("_", " ").title()) for b in bizs]
            lines.append("")
            lines.append(f"BUSINESSES ({len(bizs)}): " + ", ".join(names[:20]))
    except Exception:
        pass

    # Land
    try:
        from land import LandPlot
        from database import SessionLocal as _SL3
        ldb = _SL3()
        try:
            plots = ldb.query(LandPlot).filter(LandPlot.owner_id == player_id).all()
        finally:
            ldb.close()
        if plots:
            terr = {}
            for p in plots:
                terr[p.terrain_type] = terr.get(p.terrain_type, 0) + 1
            lines.append(f"LAND: {len(plots)} plots (" +
                         ", ".join(f"{n}× {t.replace('_',' ')}" for t, n in terr.items()) + ")")
    except Exception:
        pass

    # Districts
    try:
        from districts import District
        from database import SessionLocal as _SL4
        ddb2 = _SL4()
        try:
            dists = ddb2.query(District).filter(District.owner_id == player_id).all()
        finally:
            ddb2.close()
        if dists:
            lines.append(f"DISTRICTS ({len(dists)}): " + ", ".join(
                f"{d.district_type.replace('_',' ')} ({d.plots_merged} plots)" for d in dists))
    except Exception:
        pass

    # Institutions
    try:
        from special_plots import get_player_special_plots
        insts = get_player_special_plots(player_id)
        if insts:
            lines.append(f"INSTITUTIONS ({len(insts)}): " + ", ".join(
                f"{sp.special_type.replace('_',' ')} ({sp.plots_merged} plots)" for sp in insts))
    except Exception:
        pass

    # Executives
    try:
        from executive import get_active_executives, get_db as _edb, EXECUTIVE_JOBS
        edb = _edb()
        try:
            execs = get_active_executives(edb, player_id)
        finally:
            edb.close()
        if execs:
            lines.append("")
            lines.append(f"EXECUTIVES ({len(execs)}): " + ", ".join(
                f"{e.first_name} {e.last_name} ({EXECUTIVE_JOBS.get(e.job, {}).get('title', e.job)})"
                for e in execs))
    except Exception:
        pass

    # Stock holdings
    try:
        from banks.brokerage_firm import ShareholderPosition, CompanyShares, get_db as _fdb
        fdb = _fdb()
        try:
            positions = fdb.query(ShareholderPosition).filter(
                ShareholderPosition.player_id == player_id,
                ShareholderPosition.shares_owned > 0).all()
            if positions:
                rows = []
                for pos in positions:
                    co = fdb.query(CompanyShares).filter(
                        CompanyShares.id == pos.company_shares_id).first()
                    ticker = co.ticker_symbol if co else f"#{pos.company_shares_id}"
                    rows.append(f"{ticker} {pos.shares_owned:,.0f}sh @ {money(pos.average_cost_basis or 0)}")
                lines.append("")
                lines.append(f"STOCK HOLDINGS ({len(positions)}): " + ", ".join(rows[:20]))
        finally:
            fdb.close()
    except Exception:
        pass

    # Bonds
    try:
        from reserve_banks import ReserveBankBond, ReserveSessionLocal
        rdb3 = ReserveSessionLocal()
        try:
            bonds = rdb3.query(ReserveBankBond).filter(
                ReserveBankBond.holder_player_id == player_id,
                ReserveBankBond.status == "active").all()
        finally:
            rdb3.close()
        if bonds:
            total_face = sum((b.face_value_wsc or 0) for b in bonds)
            lines.append(f"BONDS ({len(bonds)} active): total face {money(total_face)}")
    except Exception:
        pass

    # Crypto
    try:
        crypto = []
        try:
            from counties import get_player_wallets
            for w in get_player_wallets(player_id):
                if (w.get("balance") or 0) > 0:
                    crypto.append(f"{w['symbol']} {w['balance']:,.2f}")
        except Exception:
            pass
        try:
            from memecoins import MemeCoinWallet
            from database import SessionLocal as _SL5
            mdb = _SL5()
            try:
                memes = mdb.query(MemeCoinWallet).filter(
                    MemeCoinWallet.player_id == player_id, MemeCoinWallet.balance > 0).all()
            finally:
                mdb.close()
            for m in memes:
                crypto.append(f"{m.meme_symbol} {m.balance:,.2f}")
        except Exception:
            pass
        try:
            from wallet import WSCWallet
            from database import SessionLocal as _SL6
            wdb = _SL6()
            try:
                wsc = wdb.query(WSCWallet).filter(WSCWallet.player_id == player_id).first()
            finally:
                wdb.close()
            if wsc and (wsc.balance or 0) > 0:
                crypto.append(f"WSC {wsc.balance:,.2f}")
        except Exception:
            pass
        if crypto:
            lines.append("CRYPTO HOLDINGS: " + ", ".join(crypto))
    except Exception:
        pass

    # Companies founded
    try:
        from banks.brokerage_firm import CompanyShares, get_db as _fdb2
        cdb = _fdb2()
        try:
            cos = cdb.query(CompanyShares).filter(CompanyShares.founder_id == player_id).all()
            if cos:
                lines.append("COMPANIES FOUNDED: " + ", ".join(
                    f"{c.company_name} ({c.ticker_symbol})" for c in cos[:15]))
        finally:
            cdb.close()
    except Exception:
        pass

    # City / county
    try:
        from cities import get_player_city
        city = get_player_city(player_id)
        if city:
            lines.append(f"City: {city.name}")
    except Exception:
        pass
    try:
        from counties import get_player_county
        county = get_player_county(player_id)
        if county:
            lines.append(f"County: {county.name}")
    except Exception:
        pass

    # Recent activity (transaction ledger, last 10)
    try:
        from stats_ux import TransactionLog, get_db as _tdb
        adb = _tdb()
        try:
            logs = adb.query(TransactionLog).filter(
                TransactionLog.player_id == player_id
            ).order_by(TransactionLog.timestamp.desc()).limit(10).all()
        finally:
            adb.close()
        if logs:
            lines.append("")
            lines.append("RECENT TRANSACTIONS (newest first):")
            for l in logs:
                desc = (l.description or (l.transaction_type or "").replace("_", " ").title())[:60]
                lines.append(f"  {desc}: {money(l.amount or 0)}")
    except Exception:
        pass

    return "\n".join(lines) if lines else f"(No data available for Player #{player_id}.)"


# ==========================
# GEMINI CALL
# ==========================

def _call_gemini(api_key: str, system: str, messages: List[dict]) -> tuple[bool, str]:
    """One stateless generateContent call. Returns (ok, reply_or_error_message)."""
    contents = []
    for m in messages[-_MAX_TURNS:]:
        role = "user" if (m.get("role") == "user") else "model"
        text = str(m.get("content", ""))[:8000]
        if text:
            contents.append({"role": role, "parts": [{"text": text}]})
    if not contents:
        return False, "Say something to your advisor to get started."

    payload = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": contents,
        "generationConfig": {"temperature": 0.6, "maxOutputTokens": 1024},
    }
    try:
        resp = requests.post(
            GEMINI_URL,
            params={"key": api_key},
            json=payload,
            timeout=HTTP_TIMEOUT,
        )
    except requests.Timeout:
        return False, "The advisor took too long to respond. Please try again."
    except Exception as e:
        return False, f"Could not reach the AI service: {e}"

    if resp.status_code == 400:
        return False, "Your Gemini API key was rejected (invalid or malformed). Update it in Settings → Account."
    if resp.status_code in (401, 403):
        return False, "Your Gemini API key is unauthorized or expired. Update it in Settings → Account."
    if resp.status_code == 429:
        return False, "Your Gemini key has hit its rate limit / quota. Try again later or use a different key."
    if resp.status_code != 200:
        return False, f"The AI service returned an error (HTTP {resp.status_code})."

    try:
        data = resp.json()
        cand = (data.get("candidates") or [{}])[0]
        # Safety blocks / empty finish
        parts = (cand.get("content") or {}).get("parts") or []
        reply = "".join(p.get("text", "") for p in parts).strip()
        if not reply:
            fr = cand.get("finishReason") or ""
            if fr == "SAFETY":
                return True, "I can't help with that one. Try rephrasing your question about your Wadsworth strategy."
            return True, "I didn't have a response for that — try rephrasing your question."
        return True, reply
    except Exception as e:
        return False, f"Could not parse the AI response: {e}"


# ==========================
# AUTH HELPERS
# ==========================

router = APIRouter()


def _player(session_token):
    import auth
    db = auth.get_db()
    try:
        return auth.get_player_from_session(db, session_token)
    finally:
        db.close()


def _is_pro(player) -> bool:
    try:
        from skin_utils import is_pro
        return bool(is_pro(player))
    except Exception:
        return False


def _redirect_account():
    return RedirectResponse(url="/settings?tab=account", status_code=303)


# ==========================
# CREDENTIAL ROUTES (posted from Settings → Account)
# ==========================

@router.post("/api/advisor/credentials/add")
def advisor_cred_add(
    session_token: Optional[str] = Cookie(None),
    credential_name: str = Form(...),
    api_key: str = Form(...),
):
    player = _player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)
    if not _is_pro(player):
        return _redirect_account()
    add_credential(player.id, credential_name, api_key)
    # api_key goes out of scope here — only the ciphertext persists.
    return _redirect_account()


@router.post("/api/advisor/credentials/activate")
def advisor_cred_activate(
    session_token: Optional[str] = Cookie(None),
    cred_id: int = Form(...),
):
    player = _player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)
    activate_credential(player.id, cred_id)
    return _redirect_account()


@router.post("/api/advisor/credentials/delete")
def advisor_cred_delete(
    session_token: Optional[str] = Cookie(None),
    cred_id: int = Form(...),
):
    player = _player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)
    delete_credential(player.id, cred_id)
    return _redirect_account()


# ==========================
# CHAT ENDPOINT (stateless — nothing persisted)
# ==========================

@router.post("/api/advisor/chat")
def advisor_chat(
    session_token: Optional[str] = Cookie(None),
    payload: dict = Body(...),
):
    player = _player(session_token)
    if not player:
        return JSONResponse({"ok": False, "error": "Not signed in."}, status_code=401)
    if not _is_pro(player):
        return JSONResponse(
            {"ok": False, "error": "The Financial Advisor is a Wadsworth Pro feature."},
            status_code=403)

    cred = get_active_credential(player.id)
    if not cred or not cred.get("api_key"):
        return JSONResponse(
            {"ok": False, "error": "Add a Gemini API key in Settings → Account to use the advisor."},
            status_code=400)

    # Light anti-loop guard (the player bears the cost, so this is just sanity, not a quota).
    try:
        from push_ux import push_rate_ok, push_rate_mark
        if not push_rate_ok(f"advisor-{player.id}", _CHAT_COOLDOWN_SECS):
            return JSONResponse({"ok": False, "error": "Slow down a moment, then try again."},
                                status_code=429)
        push_rate_mark(f"advisor-{player.id}")
    except Exception:
        pass

    messages = payload.get("messages") or []
    if not isinstance(messages, list):
        return JSONResponse({"ok": False, "error": "Malformed request."}, status_code=400)

    # Build the private, per-player system prompt. The model sees ONLY this.
    from advisor_knowledge import system_prompt
    context = _build_player_context(player.id)
    system = system_prompt(context)

    ok, reply = _call_gemini(cred["api_key"], system, messages)
    if not ok:
        return JSONResponse({"ok": False, "error": reply}, status_code=502)
    return JSONResponse({"ok": True, "reply": reply})


# ==========================
# ADVISOR PAGE
# ==========================

def _settings_section_html(player) -> str:
    """The Financial Advisor credential-wallet section rendered inside Settings → Account.
    Exposed here so settings_ux.py can include it without duplicating storage logic."""
    import html as _html
    is_pro = _is_pro(player)
    creds = list_credentials(player.id) if is_pro else []

    intro = """
    <h3 style="margin:0 0 6px;color:#34d399;">🤖 Financial Advisor</h3>
    <p style="color:#64748b;font-size:0.82rem;margin:0 0 12px;">
        A private AI advisor that knows the Wadsworth game and your own account, and answers
        your strategy questions. You bring your own free Google Gemini API key — your key is
        encrypted, never shared, and your conversations are never stored on our server.
    </p>"""

    if not is_pro:
        return f"""{intro}
        <div style="background:#0f172a;border:1px solid #1e293b;border-radius:10px;padding:18px 20px;max-width:600px;">
            <p style="color:#fbbf24;font-size:0.85rem;margin:0;">🔒 The Financial Advisor is a Wadsworth Pro feature. Subscribe above to unlock it.</p>
        </div>"""

    # Credential rows
    if creds:
        rows = ""
        for c in creds:
            active = c["is_active"]
            badge = ('<span style="background:#052e16;border:1px solid #16a34a;color:#4ade80;'
                     'border-radius:8px;padding:1px 8px;font-size:0.7rem;font-weight:700;">ACTIVE</span>'
                     if active else
                     f'''<form action="/api/advisor/credentials/activate" method="post" style="display:inline;">
                         <input type="hidden" name="cred_id" value="{c['id']}">
                         <button type="submit" style="background:#1e293b;border:1px solid #334155;color:#94a3b8;
                             border-radius:6px;padding:3px 10px;font-size:0.72rem;cursor:pointer;font-family:inherit;">Use this</button>
                     </form>''')
            rows += f"""
            <div style="display:flex;align-items:center;justify-content:space-between;gap:10px;
                        padding:10px 0;border-top:1px solid #1e293b;">
                <div>
                    <span style="color:#e5e7eb;font-weight:600;">{_html.escape(c['credential_name'])}</span>
                    <span style="color:#64748b;font-size:0.75rem;">&nbsp;· {c['provider']} · ••••{_html.escape(c['key_last4'])}</span>
                </div>
                <div style="display:flex;align-items:center;gap:8px;">
                    {badge}
                    <form action="/api/advisor/credentials/delete" method="post" style="display:inline;"
                          onsubmit="return confirm('Delete this API key?');">
                        <input type="hidden" name="cred_id" value="{c['id']}">
                        <button type="submit" style="background:#1e293b;border:1px solid #ef4444;color:#fca5a5;
                            border-radius:6px;padding:3px 10px;font-size:0.72rem;cursor:pointer;font-family:inherit;">Delete</button>
                    </form>
                </div>
            </div>"""
        creds_block = rows
    else:
        creds_block = ('<p style="color:#64748b;font-size:0.8rem;margin:10px 0 0;">'
                       'No API keys yet. Add one below to start chatting.</p>')

    return f"""{intro}
    <div style="background:#0f172a;border:1px solid #1e293b;border-radius:10px;padding:18px 20px;max-width:600px;">
        {creds_block}
        <form action="/api/advisor/credentials/add" method="post" style="margin-top:14px;border-top:1px solid #1e293b;padding-top:14px;">
            <div style="margin-bottom:10px;">
                <label style="display:block;color:#64748b;font-size:0.75rem;margin-bottom:4px;">Key name</label>
                <input type="text" name="credential_name" placeholder="My Gemini key" required maxlength="60"
                       style="width:100%;max-width:300px;padding:8px 10px;background:#020617;border:1px solid #1e293b;color:#e5e7eb;border-radius:4px;font-family:inherit;font-size:16px;">
            </div>
            <div style="margin-bottom:8px;">
                <label style="display:block;color:#64748b;font-size:0.75rem;margin-bottom:4px;">Google Gemini API key</label>
                <input type="password" name="api_key" placeholder="AIza…" required
                       style="width:100%;max-width:300px;padding:8px 10px;background:#020617;border:1px solid #1e293b;color:#e5e7eb;border-radius:4px;font-family:inherit;font-size:16px;">
            </div>
            <p style="color:#64748b;font-size:0.74rem;margin:8px 0 12px;line-height:1.5;">
                Get a free key at <a href="https://aistudio.google.com/app/apikey" target="_blank"
                rel="noopener noreferrer" style="color:#38bdf8;">Google AI Studio</a> — many players make a
                fresh Google account just for this. Your key is encrypted at rest and used only for your
                advisor chats.
            </p>
            <button type="submit"
                    style="background:#34d399;color:#04261a;border:none;border-radius:6px;padding:8px 18px;
                           font-size:0.82rem;font-weight:700;cursor:pointer;font-family:inherit;">Save key</button>
        </form>
        <div style="margin-top:14px;">
            <a href="/advisor" style="background:#064e3b;border:1px solid #34d399;color:#6ee7b7;border-radius:6px;
               padding:8px 16px;font-size:0.82rem;font-weight:700;text-decoration:none;">💬 Open the Financial Advisor →</a>
        </div>
    </div>"""


@router.get("/advisor", response_class=HTMLResponse)
def advisor_page(session_token: Optional[str] = Cookie(None)):
    from ux import shell
    player = _player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)

    if not _is_pro(player):
        body = """
        <a href="/settings?tab=account" style="color:#38bdf8;">&larr; Settings</a>
        <h1 style="margin:8px 0 4px 0;">🤖 Financial Advisor</h1>
        <div class="card" style="max-width:640px;margin-top:16px;text-align:center;padding:36px;">
            <div style="font-size:2.2rem;margin-bottom:10px;">🔒</div>
            <p style="color:#e5e7eb;font-weight:600;">The Financial Advisor is a Wadsworth Pro feature.</p>
            <p style="color:#94a3b8;font-size:0.88rem;">Get a personal AI that understands the game and your
               own portfolio — bring your own free Gemini key.</p>
            <a href="/settings?tab=account" class="btn-blue" style="display:inline-block;margin-top:12px;padding:10px 22px;">View Wadsworth Pro</a>
        </div>"""
        return HTMLResponse(shell("Financial Advisor", body, player.cash_balance, player.id))

    cred = get_active_credential(player.id)
    has_key = bool(cred and cred.get("api_key"))
    active_name = cred.get("credential_name") if cred else ""

    if not has_key:
        body = """
        <a href="/settings?tab=account" style="color:#38bdf8;">&larr; Settings</a>
        <h1 style="margin:8px 0 4px 0;">🤖 Financial Advisor</h1>
        <div class="card" style="max-width:640px;margin-top:16px;padding:30px;">
            <p style="color:#e5e7eb;font-weight:600;margin-top:0;">One quick step: add a Gemini API key.</p>
            <ol style="color:#94a3b8;font-size:0.9rem;line-height:1.7;">
                <li>Open <a href="https://aistudio.google.com/app/apikey" target="_blank" rel="noopener noreferrer" style="color:#38bdf8;">Google AI Studio</a> and create a free API key (a fresh Google account works great).</li>
                <li>Paste it into <a href="/settings?tab=account" style="color:#38bdf8;">Settings → Account → Financial Advisor</a>.</li>
                <li>Come back here and start chatting.</li>
            </ol>
            <p style="color:#64748b;font-size:0.8rem;">Your key is encrypted, never shared, and your conversations are never stored on our server.</p>
            <a href="/settings?tab=account" class="btn-blue" style="display:inline-block;margin-top:8px;padding:9px 20px;">Add my key</a>
        </div>"""
        return HTMLResponse(shell("Financial Advisor", body, player.cash_balance, player.id))

    import html as _html
    powered = _html.escape(active_name or "your key", quote=True)
    body = f"""
    <a href="/settings?tab=account" style="color:#38bdf8;">&larr; Settings</a>
    <div style="display:flex;align-items:baseline;justify-content:space-between;gap:10px;flex-wrap:wrap;">
        <h1 style="margin:8px 0 4px 0;">🤖 Financial Advisor</h1>
        <span style="color:#64748b;font-size:0.78rem;">Powered by: {powered} · Gemini · chats are never saved on our server</span>
    </div>
    <div class="card" style="max-width:760px;padding:0;overflow:hidden;">
        <div id="adv-log" style="height:52vh;min-height:320px;overflow-y:auto;padding:18px;display:flex;flex-direction:column;gap:12px;"></div>
        <div style="border-top:1px solid var(--border,#1e293b);padding:12px;display:flex;gap:8px;align-items:flex-end;">
            <textarea id="adv-input" rows="2" placeholder="Ask about your taxes, portfolio, strategy…"
                style="flex:1;resize:vertical;background:var(--bg-page,#020617);border:1px solid var(--border,#334155);
                       color:var(--text-primary,#e5e7eb);border-radius:8px;padding:10px;font-family:inherit;font-size:16px;"></textarea>
            <button id="adv-send" class="btn-blue" style="padding:10px 18px;white-space:nowrap;">Send</button>
        </div>
    </div>
    <div style="max-width:760px;margin-top:10px;display:flex;gap:8px;flex-wrap:wrap;">
        <button id="adv-download" style="background:#1e293b;border:1px solid #334155;color:#94a3b8;border-radius:6px;
            padding:7px 14px;font-size:0.8rem;cursor:pointer;font-family:inherit;">⬇ Download conversation</button>
        <label style="background:#1e293b;border:1px solid #334155;color:#94a3b8;border-radius:6px;
            padding:7px 14px;font-size:0.8rem;cursor:pointer;">⬆ Import conversation
            <input id="adv-import" type="file" accept="application/json,.json" style="display:none;">
        </label>
        <button id="adv-clear" style="background:#1e293b;border:1px solid #334155;color:#94a3b8;border-radius:6px;
            padding:7px 14px;font-size:0.8rem;cursor:pointer;font-family:inherit;">🗑 Clear</button>
    </div>
    <p style="max-width:760px;color:#64748b;font-size:0.75rem;margin-top:8px;">
        Educational, in-game guidance only — not real-world financial advice. Conversations live only in your
        browser; download them to continue later, even on another device.
    </p>

    <script>
    (function() {{
        var log = document.getElementById('adv-log');
        var input = document.getElementById('adv-input');
        var sendBtn = document.getElementById('adv-send');
        var messages = [];  // {{role:'user'|'model', content:'...'}} — kept only in this browser

        function esc(s) {{
            return (s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
        }}
        function bubble(role, text) {{
            var mine = role === 'user';
            var d = document.createElement('div');
            d.style.cssText = 'max-width:85%;padding:10px 14px;border-radius:12px;white-space:pre-wrap;line-height:1.5;font-size:0.9rem;' +
                (mine ? 'align-self:flex-end;background:var(--accent,#2563eb);color:#fff;border-bottom-right-radius:3px;'
                      : 'align-self:flex-start;background:var(--bg-page,#0f172a);border:1px solid var(--border,#1e293b);color:var(--text-primary,#e5e7eb);border-bottom-left-radius:3px;');
            d.innerHTML = esc(text);
            log.appendChild(d);
            log.scrollTop = log.scrollHeight;
            return d;
        }}
        function render() {{
            log.innerHTML = '';
            if (!messages.length) {{
                var w = document.createElement('div');
                w.style.cssText = 'color:#64748b;text-align:center;margin:auto;font-size:0.9rem;';
                w.innerHTML = '👋 Ask me anything about your Wadsworth empire — taxes, what to buy next, how a mechanic works, or how your portfolio looks.';
                log.appendChild(w);
                return;
            }}
            messages.forEach(function(m) {{ bubble(m.role, m.content); }});
        }}
        render();

        async function send() {{
            var text = (input.value || '').trim();
            if (!text) return;
            input.value = '';
            messages.push({{role:'user', content:text}});
            render();
            sendBtn.disabled = true;
            var thinking = bubble('model', '…');
            try {{
                var r = await fetch('/api/advisor/chat', {{
                    method:'POST', headers:{{'Content-Type':'application/json'}},
                    credentials:'same-origin', body: JSON.stringify({{messages: messages}})
                }});
                var data = await r.json();
                thinking.remove();
                if (data && data.ok) {{
                    messages.push({{role:'model', content:data.reply}});
                }} else {{
                    bubble('model', '⚠ ' + ((data && data.error) || 'Something went wrong.'));
                }}
                render();
            }} catch(e) {{
                thinking.remove();
                bubble('model', '⚠ Network error. Please try again.');
            }} finally {{
                sendBtn.disabled = false;
                input.focus();
            }}
        }}
        sendBtn.addEventListener('click', send);
        input.addEventListener('keydown', function(e) {{
            if (e.key === 'Enter' && !e.shiftKey) {{ e.preventDefault(); send(); }}
        }});

        document.getElementById('adv-download').addEventListener('click', function() {{
            var blob = new Blob([JSON.stringify({{version:1, messages:messages}}, null, 2)], {{type:'application/json'}});
            var a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = 'wadsworth-advisor-' + new Date().toISOString().slice(0,10) + '.json';
            a.click();
            URL.revokeObjectURL(a.href);
        }});
        document.getElementById('adv-import').addEventListener('change', function(e) {{
            var f = e.target.files[0];
            if (!f) return;
            var reader = new FileReader();
            reader.onload = function() {{
                try {{
                    var parsed = JSON.parse(reader.result);
                    var arr = Array.isArray(parsed) ? parsed : (parsed.messages || []);
                    messages = arr.filter(function(m) {{ return m && m.content && (m.role === 'user' || m.role === 'model'); }})
                                  .map(function(m) {{ return {{role:m.role, content:String(m.content)}}; }});
                    render();
                }} catch(err) {{ alert('Could not read that file — is it a saved advisor conversation?'); }}
            }};
            reader.readAsText(f);
            e.target.value = '';
        }});
        document.getElementById('adv-clear').addEventListener('click', function() {{
            if (confirm('Clear this conversation? (Download it first if you want to keep it.)')) {{
                messages = []; render();
            }}
        }});
    }})();
    </script>
    """
    return HTMLResponse(shell("Financial Advisor", body, player.cash_balance, player.id))
