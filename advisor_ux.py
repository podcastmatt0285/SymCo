"""
advisor_ux.py

Wadsworth **Financial Advisor** — a Pro-gated, bring-your-own-key AI assistant.

Architecture & security model (see also the approved plan):
- The advisor is a **stateless proxy**. Players supply their own Google Gemini API key
  (named, switchable wallet); their account bears the cost. The server forwards one request
  and returns the reply — it never stores conversations.
- The model is **pure text-in / text-out** with NO live tools and NO open database access.
  Everything it sees is assembled server-side from a fixed allowlist of game data helpers
  before the call: (a) the hand-written game-knowledge document (advisor_knowledge.py),
  (b) the asking player's OWN full data, and (c) — this is a competitive-intelligence
  feature — the data of *other players* the asking player references, subject to those
  players' opt-out. There is no path to source code, server secrets, passwords, API keys, or
  session tokens: the data builders simply never read them.
- Cross-player visibility & opt-out: by default every player is "scannable" (their full data
  may be surfaced to another player's advisor). **Subscribers/admins** can opt out
  (advisor_settings.scannable = FALSE); free players cannot. A shielded player is reduced to
  public, leaderboard-level info only, and the advisor is told to infer rather than quote
  their books. A player always sees their OWN data regardless of their own shield.
- API keys are encrypted at rest with AES-256-GCM (pycryptodome, already a dependency — the
  same library used for VAPID). The encryption key lives in env ADVISOR_ENC_KEY or, if unset,
  is generated once and persisted in system_config (mirrors push_ux's VAPID-key pattern).
  Plaintext keys are never returned to the browser (UI shows last-4 only) and never logged.

Owns its own `advisor_credentials` + `advisor_settings` tables via run_ddl_migration,
mirroring bluesky.py.
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
        # Per-player privacy preference. scannable == "another player's Financial Advisor may
        # surface my full data". Defaults TRUE (everyone is scannable). Only subscribers/admins
        # may set it FALSE to shield their books (enforced in the route). A player always sees
        # their own data regardless of this flag.
        """CREATE TABLE IF NOT EXISTS advisor_settings (
                player_id INTEGER PRIMARY KEY,
                scannable BOOLEAN NOT NULL DEFAULT TRUE
            )""",
        # Migrate the earlier column name (share_account_data) if this table predates the
        # competitive-intelligence model. Both are "default scannable / opt-out" booleans.
        "ALTER TABLE advisor_settings RENAME COLUMN share_account_data TO scannable",
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
    """Provider for a key. Gemini is the only provider at launch, so any non-empty key is
    treated as Gemini — we do NOT reject on key shape (Google issues more than one key
    format, and the real validity check is the API call itself, which fails gracefully)."""
    k = (api_key or "").strip()
    return "gemini" if k else None


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
        return False, "Please paste your Google Gemini API key."
    # Self-heal: make sure the table exists (covers a running instance whose startup didn't
    # create it) and that we can build the encryption key before we touch the row.
    try:
        _ensure_table()
        enc = _encrypt(api_key)
    except Exception as e:
        return False, f"Setup error (encryption/storage): {e}"
    from auth import get_db
    from sqlalchemy import text
    db = get_db()
    try:
        # First credential becomes active automatically.
        existing_names = {r[0] for r in db.execute(text(
            "SELECT credential_name FROM advisor_credentials WHERE player_id = :pid"
        ), {"pid": player_id}).all()}
        make_active = len(existing_names) == 0
        # Never silently overwrite a different saved key: if the name is taken, auto-suffix so
        # both keys persist (e.g. "My key", "My key (2)").
        if name in existing_names:
            base = name
            i = 2
            while f"{base} ({i})" in existing_names and i < 99:
                i += 1
            name = f"{base} ({i})"[:60]
        if make_active:
            db.execute(text("UPDATE advisor_credentials SET is_active = FALSE WHERE player_id = :pid"),
                       {"pid": player_id})
        db.execute(text(
            "INSERT INTO advisor_credentials "
            "(player_id, credential_name, provider, api_key_enc, key_last4, is_active) "
            "VALUES (:pid, :name, :prov, :enc, :last4, :active)"
        ), {"pid": player_id, "name": name, "prov": provider,
            "enc": enc, "last4": api_key[-4:], "active": make_active})
        db.commit()
    except Exception as e:
        db.rollback()
        return False, f"Could not save credential: {type(e).__name__}: {e}"
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


def delete_all_credentials(player_id: int) -> int:
    """Remove every saved key for a player (self-serve reset). Returns the count removed."""
    from auth import get_db
    from sqlalchemy import text
    db = get_db()
    try:
        n = db.execute(text("DELETE FROM advisor_credentials WHERE player_id = :pid"),
                       {"pid": player_id}).rowcount
        db.commit()
    finally:
        db.close()
    return n or 0


# ==========================
# PRIVACY PREFERENCE (scannable by other players' advisor — default ON, subscriber opt-out)
# ==========================

def is_scannable(player_id: int) -> bool:
    """True (default) if another player's advisor may surface this player's full data."""
    from auth import get_db
    from sqlalchemy import text
    db = get_db()
    try:
        row = db.execute(text(
            "SELECT scannable FROM advisor_settings WHERE player_id = :pid"
        ), {"pid": player_id}).first()
    finally:
        db.close()
    return True if row is None else bool(row[0])


def set_scannable(player_id: int, on: bool):
    from auth import get_db
    from sqlalchemy import text
    db = get_db()
    try:
        db.execute(text(
            "INSERT INTO advisor_settings (player_id, scannable) VALUES (:pid, :v) "
            "ON CONFLICT (player_id) DO UPDATE SET scannable = EXCLUDED.scannable"
        ), {"pid": player_id, "v": bool(on)})
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


def _public_player_summary(player_id: int) -> str:
    """Leaderboard-level, publicly-inferable info for a SHIELDED player. Deliberately omits
    exact cash, holdings, and transaction history so a shielded player's books stay private."""
    from reserve_banks import get_player_display_currency, fmt_usd
    disp = get_player_display_currency(player_id)
    def money(a):
        try: return fmt_usd(a or 0, disp)
        except Exception: return f"${(a or 0):,.2f}"
    bits = []
    try:
        from auth import Player, get_db as _adb
        db = _adb()
        try:
            p = db.query(Player).filter(Player.id == player_id).first()
        finally:
            db.close()
        bits.append(f"Name: {p.business_name if p else f'Player #{player_id}'} (Player ID #{player_id})")
    except Exception:
        bits.append(f"Player ID #{player_id}")
    try:
        from events import get_player_level
        lv = get_player_level(player_id)
        bits.append(f"Level {lv['level']} · {lv['trophies']:,} trophies")
    except Exception:
        pass
    try:
        from stats_ux import PlayerStats, get_db as _sdb
        sdb = _sdb()
        try:
            ps = sdb.query(PlayerStats).filter(PlayerStats.player_id == player_id).first()
        finally:
            sdb.close()
        if ps:
            bits.append(f"Net worth: {money(ps.total_net_worth)} (public leaderboard, wealth rank #{ps.wealth_rank or '—'})")
            bits.append(f"Visible scale: {ps.lands_owned} plots · {ps.businesses_owned} businesses · {ps.districts_owned} districts")
    except Exception:
        pass
    try:
        from cities import get_player_city
        c = get_player_city(player_id)
        if c: bits.append(f"City: {c.name}")
    except Exception:
        pass
    bits.append("DETAILED BOOKS: SHIELDED — this player has opted out of being scanned. Do NOT "
                "claim to know their exact cash, holdings, or transactions; infer only from the "
                "public standings above.")
    return "\n".join(bits)


# Players whose names are too generic to safely substring-match get an id/length guard below.
def _resolve_referenced_players(querying_id: int, messages: list) -> list:
    """Find OTHER players the conversation refers to, by business name or #ID, across the
    whole transcript (so follow-ups like 'how do I beat them' still resolve). Returns a list
    of player ids (excluding the asker), capped to keep the prompt bounded."""
    text_blob = " ".join(str(m.get("content", "")) for m in messages if isinstance(m, dict)).lower()
    if not text_blob.strip():
        return []
    import re
    found: list = []

    # Explicit "#123" / "player 123" id references
    for m in re.findall(r"(?:#|player\s+#?)(\d{1,7})", text_blob):
        try:
            pid = int(m)
            if pid > 0 and pid != querying_id and pid not in found:
                found.append(pid)
        except Exception:
            pass

    # Name references
    try:
        from auth import Player, get_db as _adb
        db = _adb()
        try:
            rows = db.query(Player.id, Player.business_name).filter(Player.id > 0).all()
        finally:
            db.close()
        for pid, bname in rows:
            if pid == querying_id or pid in found:
                continue
            nm = (bname or "").strip().lower()
            # length guard avoids matching ultra-short/common names inside other words
            if len(nm) >= 4 and nm in text_blob:
                found.append(pid)
            if len(found) >= 6:
                break
    except Exception:
        pass
    return found[:6]


def _other_players_block(querying_id: int, messages: list) -> str:
    """Assemble the data block for OTHER players referenced in the conversation, honoring each
    target's opt-out. Empty string if none referenced."""
    ids = _resolve_referenced_players(querying_id, messages)
    if not ids:
        return ""
    chunks = []
    for pid in ids:
        if is_scannable(pid):
            chunks.append(f"--- Player #{pid} (full books) ---\n{_build_player_context(pid)}")
        else:
            chunks.append(f"--- Player #{pid} (SHIELDED) ---\n{_public_player_summary(pid)}")
    return "\n\n".join(chunks)


# ==========================
# MARKET / ECONOMY SNAPSHOT  (global, public game-wide state — included in every chat)
# ==========================

_MKT_CACHE: dict = {}          # {"t": epoch, "v": snapshot_text} — short TTL, off the hot path
_MKT_TTL = 60                  # seconds


def _market_snapshot() -> str:
    """A compact, public, game-wide economic snapshot: headline indices, commodity prices,
    district-item prices, currency yields/FX, crypto (county tokens + meme coins), and the land
    market. This is public market data (the same numbers shown across the game's market pages),
    so it carries no per-player privacy concern. Cached briefly to stay off the request hot
    path. Each section is independently guarded."""
    import time as _t
    c = _MKT_CACHE
    if c.get("v") is not None and (_t.time() - c.get("t", 0)) < _MKT_TTL:
        return c["v"]

    lines: List[str] = []

    # Headline economic indices (the "state of the economy" gauges)
    try:
        from banks import indices as _ix
        rows = []
        for code, meta in _ix.INDICES.items():
            try:
                snap = _ix._get_latest(code)
                if snap is None:
                    continue
                rows.append(f"  {meta.get('name', code)} ({meta.get('code', code)}): "
                            f"{snap.value:,.2f} {meta.get('unit', '')}".rstrip())
            except Exception:
                continue
        if rows:
            lines.append("ECONOMIC INDICES (latest):")
            lines.extend(rows)
    except Exception:
        pass

    # Commodity market prices (open market)
    try:
        from market import get_all_market_prices
        prices = get_all_market_prices() or {}
        items = sorted((k, v) for k, v in prices.items() if v)
        if items:
            lines.append("")
            lines.append(f"COMMODITY MARKET PRICES ({len(items)} items, USD):")
            lines.append("  " + ", ".join(f"{k.replace('_',' ')} ${v:,.2f}" for k, v in items[:160]))
    except Exception:
        pass

    # District-item market prices (sampled)
    try:
        import district_market as _dm
        if not _dm.DISTRICT_ITEMS:
            try:
                _dm.load_district_items()
            except Exception:
                pass
        sample = []
        for k in list(_dm.DISTRICT_ITEMS.keys())[:60]:
            try:
                p = _dm.get_market_price(k)
                if p:
                    sample.append(f"{k.replace('_',' ')} ${p:,.2f}")
            except Exception:
                continue
            if len(sample) >= 30:
                break
        if sample:
            lines.append("")
            lines.append(f"DISTRICT MARKET PRICES (sample of {len(sample)}, USD):")
            lines.append("  " + ", ".join(sample))
        elif _dm.DISTRICT_ITEMS:
            lines.append("")
            lines.append(f"DISTRICT MARKET: {len(_dm.DISTRICT_ITEMS)} district-item types tradable "
                         "(no recent trade prices to quote).")
    except Exception:
        pass

    # Currencies: FX rate + yield
    try:
        from reserve_banks import StateReserveBank, get_db as _rdb
        db = _rdb()
        try:
            banks = db.query(StateReserveBank).all()
        finally:
            db.close()
        if banks:
            lines.append("")
            lines.append("CURRENCIES (USD per unit · annual yield):")
            lines.append("  " + ", ".join(
                f"{b.currency_code} ${b.usd_per_unit:,.4f}/{(b.yield_rate or 0)*100:.1f}%"
                for b in banks))
    except Exception:
        pass

    # Crypto — county tokens (L1)
    try:
        from counties import get_all_counties
        cos = [c2 for c2 in (get_all_counties() or []) if (c2.get("crypto_price") or 0) > 0]
        cos.sort(key=lambda x: -(x.get("market_cap") or 0))
        if cos:
            lines.append("")
            lines.append("COUNTY TOKENS (price · market cap):")
            for c2 in cos[:12]:
                lines.append(f"  {c2.get('crypto_symbol','?')} ({c2.get('name','?')}): "
                             f"${c2.get('crypto_price',0):,.4f} · cap ${c2.get('market_cap',0):,.0f}")
    except Exception:
        pass

    # Crypto — meme coins (top by volume)
    try:
        from memecoins import get_all_meme_coins_global
        memes = get_all_meme_coins_global("volume") or []
        if memes:
            lines.append("TOP MEME COINS (by volume · last price, in native token):")
            for m in memes[:10]:
                lines.append(f"  {m.get('symbol','?')} on {m.get('native_symbol','?')}: "
                             f"{m.get('last_price',0):,.6f}")
    except Exception:
        pass

    # Land market
    try:
        from land_market import LandListing, get_db as _lmdb
        db = _lmdb()
        try:
            asks = [l.asking_price for l in db.query(LandListing).filter(
                LandListing.is_active == True).all() if l.asking_price]
        finally:
            db.close()
        if asks:
            lines.append("")
            lines.append(f"LAND MARKET: {len(asks)} plots listed · "
                         f"asking ${min(asks):,.0f}–${max(asks):,.0f} "
                         f"(avg ${sum(asks)/len(asks):,.0f})")
        else:
            lines.append("")
            lines.append("LAND MARKET: no plots currently listed for sale.")
    except Exception:
        pass

    snapshot = "\n".join(lines) if lines else "(Market data temporarily unavailable.)"
    c["t"], c["v"] = _t.time(), snapshot
    return snapshot


def _compact(n: float) -> str:
    """Abbreviate large money values (1.73Qa, 4.2B, 56.3K)."""
    try:
        n = float(n or 0)
    except Exception:
        return "0"
    for div, suf in ((1e18, "Qi"), (1e15, "Qa"), (1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")):
        if abs(n) >= div:
            return f"${n/div:,.2f}{suf}"
    return f"${n:,.0f}"


_WORLD_CACHE: dict = {}
_WORLD_TTL = 60


def _world_snapshot() -> str:
    """Game-wide non-price public state a player can see: active events & market effects, the
    wealth leaderboard, the cities directory, and county governance. Cached briefly; each
    section independently guarded."""
    import time as _t
    c = _WORLD_CACHE
    if c.get("v") is not None and (_t.time() - c.get("t", 0)) < _WORLD_TTL:
        return c["v"]

    lines: List[str] = []

    # Active events + market-moving effects
    try:
        import events as _ev
        active = _ev.get_active_events() or []
        if active:
            lines.append("ACTIVE EVENTS & TASKS:")
            for e in active[:12]:
                end = e.ends_at.strftime("%b %d") if getattr(e, "ends_at", None) else "ongoing"
                lines.append(f"  [{getattr(e,'event_type','event')}] {getattr(e,'title','?')} "
                             f"— ends {end}")
        else:
            lines.append("ACTIVE EVENTS & TASKS: none right now.")
        # Economy-moving effect modifiers
        try:
            pf = _ev.get_active_market_price_factor()
            if pf and abs(pf - 1.0) > 1e-9:
                lines.append(f"  ⚠ Market price factor in effect: ×{pf:.2f} (event-driven).")
        except Exception:
            pass
        try:
            if _ev.get_active_market_shutdown():
                lines.append("  ⚠ MARKET SHUTDOWN active — trading is currently halted by an event.")
        except Exception:
            pass
        try:
            crises = _ev.get_active_item_crisis_summary() or []
            parts = []
            for x in crises[:12]:
                nm = x.get("item_name") or x.get("item_type", "?")
                if x.get("boost_pct"):
                    parts.append(f"{nm} +{x['boost_pct']}% (boom)")
                elif x.get("drop_pct"):
                    parts.append(f"{nm} -{x['drop_pct']}% (crisis)")
            if parts:
                lines.append("  Item booms/crises affecting production: " + ", ".join(parts))
        except Exception:
            pass
        try:
            upcoming = _ev.get_upcoming_events(3) or []
            if upcoming:
                lines.append("  Upcoming: " + ", ".join(
                    f"{getattr(u,'title','?')} ({u.starts_at.strftime('%b %d')})"
                    if getattr(u, "starts_at", None) else getattr(u, "title", "?")
                    for u in upcoming))
        except Exception:
            pass
    except Exception:
        pass

    # Wealth leaderboard (top players)
    try:
        from stats_ux import PlayerStats, get_db as _sdb
        from auth import Player
        sdb = _sdb()
        try:
            q = (sdb.query(PlayerStats, Player)
                 .join(Player, Player.id == PlayerStats.player_id)
                 .filter(PlayerStats.player_id > 0))
            try:
                q = q.filter(Player.is_npc.isnot(True))
            except Exception:
                pass
            top = q.order_by(PlayerStats.total_net_worth.desc()).limit(10).all()
        finally:
            sdb.close()
        if top:
            lines.append("")
            lines.append("WEALTH LEADERBOARD (top 10 by net worth):")
            for i, (ps, pl) in enumerate(top, 1):
                lines.append(f"  {i}. {pl.business_name} — {_compact(ps.total_net_worth)}")
    except Exception:
        pass

    # Cities directory
    try:
        from cities import City, get_db as _cdb, get_city_members
        cdb = _cdb()
        try:
            cities = cdb.query(City).all()
        finally:
            cdb.close()
        if cities:
            lines.append("")
            lines.append(f"CITIES ({len(cities)}):")
            from auth import Player, get_db as _adb
            adb = _adb()
            try:
                for ct in cities[:15]:
                    try:
                        mayor = adb.query(Player).filter(Player.id == ct.mayor_id).first()
                        mname = mayor.business_name if mayor else f"#{ct.mayor_id}"
                    except Exception:
                        mname = f"#{ct.mayor_id}"
                    try:
                        members = len(get_city_members(ct.id))
                    except Exception:
                        members = "?"
                    lines.append(f"  {ct.name} — mayor {mname} · {members} members · "
                                 f"join fee {_compact(ct.application_fee)}")
            finally:
                adb.close()
    except Exception:
        pass

    # County governance (crypto prices are in the market snapshot; this is the civic side)
    try:
        from counties import get_all_counties
        cos = get_all_counties() or []
        if cos:
            lines.append("")
            lines.append(f"COUNTIES ({len(cos)}):")
            for c2 in cos[:15]:
                lines.append(f"  {c2.get('name','?')} — token {c2.get('crypto_symbol','?')} · "
                             f"{c2.get('city_count',0)}/{c2.get('max_cities','?')} cities · "
                             f"treasury {_compact(c2.get('treasury_balance',0))} · "
                             f"mining pool {c2.get('mining_energy',0):,.0f}")
    except Exception:
        pass

    snapshot = "\n".join(lines) if lines else ""
    c["t"], c["v"] = _t.time(), snapshot
    return snapshot


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


def _redirect_advisor(msg: str = "", err: str = ""):
    from urllib.parse import urlencode
    q = {}
    if msg:
        q["m"] = msg
    if err:
        q["e"] = err
    url = "/advisor" + (("?" + urlencode(q)) if q else "")
    return RedirectResponse(url=url, status_code=303)


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
        return _redirect_advisor(err="The Financial Advisor is a Wadsworth Pro feature.")
    ok, msg = add_credential(player.id, credential_name, api_key)
    # api_key goes out of scope here — only the ciphertext persists.
    return _redirect_advisor(msg="API key saved." if ok else "", err="" if ok else msg)


@router.post("/api/advisor/credentials/activate")
def advisor_cred_activate(
    session_token: Optional[str] = Cookie(None),
    cred_id: int = Form(...),
):
    player = _player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)
    activate_credential(player.id, cred_id)
    return _redirect_advisor()


@router.post("/api/advisor/credentials/delete")
def advisor_cred_delete(
    session_token: Optional[str] = Cookie(None),
    cred_id: int = Form(...),
):
    player = _player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)
    delete_credential(player.id, cred_id)
    return _redirect_advisor()


@router.post("/api/advisor/credentials/wipe")
def advisor_cred_wipe(session_token: Optional[str] = Cookie(None)):
    """Self-serve reset: remove ALL of the player's saved keys."""
    player = _player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)
    n = delete_all_credentials(player.id)
    return _redirect_advisor(msg=f"Removed {n} saved key{'s' if n != 1 else ''}.")


@router.post("/api/advisor/privacy")
def advisor_privacy(
    session_token: Optional[str] = Cookie(None),
    shield: Optional[str] = Form(None),
):
    """Set whether OTHER players' advisors may scan this player. Only subscribers/admins may
    shield (set scannable = FALSE); free players stay scannable. The checkbox is "Shield my
    books", so checked == not scannable."""
    player = _player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)
    if not _is_pro(player):
        # Free players cannot opt out — force scannable and bounce back.
        set_scannable(player.id, True)
        return _redirect_advisor()
    set_scannable(player.id, shield is None)  # shield checked → scannable False
    return _redirect_advisor()


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

    # Build the system prompt server-side: the asker's OWN full data, plus the books of any
    # OTHER players they reference (honoring each target's opt-out). The model gets no live
    # tools — only this pre-assembled, allowlisted context. Secrets/passwords are never in it.
    from advisor_knowledge import system_prompt
    own = _build_player_context(player.id)
    others = _other_players_block(player.id, messages)
    market = _market_snapshot()
    world = _world_snapshot()
    context = own
    if others:
        context += f"\n\n# OTHER PLAYERS REFERENCED\n\n{others}"
    if market:
        context += f"\n\n# MARKET & ECONOMY (game-wide, public)\n\n{market}"
    if world:
        context += f"\n\n# WORLD: EVENTS, LEADERBOARD, CITIES & COUNTIES (public)\n\n{world}"
    system = system_prompt(context)

    ok, reply = _call_gemini(cred["api_key"], system, messages)
    if not ok:
        return JSONResponse({"ok": False, "error": reply}, status_code=502)
    return JSONResponse({"ok": True, "reply": reply})


# ==========================
# ADVISOR PAGE
# ==========================

def _management_panel_html(player) -> str:
    """Key wallet + scan-shield privacy panel, rendered on the /advisor page (collapsed in a
    <details>). Storage logic lives here so the page stays thin. Assumes the caller already
    confirmed the player is Pro."""
    import html as _html
    creds = list_credentials(player.id)

    # Credential rows — an explicit radio selector: the checked row is the active key, and
    # picking another radio immediately switches. Delete is a separate submit on the same row.
    if creds:
        rows = ('<p style="color:#94a3b8;font-size:0.78rem;margin:0 0 6px;">'
                'Select which key the advisor uses:</p>')
        for c in creds:
            active = c["is_active"]
            active_tag = ('<span style="background:#052e16;border:1px solid #16a34a;color:#4ade80;'
                          'border-radius:8px;padding:1px 8px;font-size:0.68rem;font-weight:700;'
                          'margin-left:8px;">IN USE</span>' if active else '')
            rows += f"""
            <form action="/api/advisor/credentials/activate" method="post"
                  style="display:flex;align-items:center;justify-content:space-between;gap:10px;
                         padding:10px;margin-top:6px;border:1px solid {'#16a34a' if active else '#1e293b'};
                         border-radius:8px;background:{'#0c1f16' if active else '#0b1220'};">
                <input type="hidden" name="cred_id" value="{c['id']}">
                <label style="display:flex;align-items:center;gap:10px;cursor:pointer;flex:1;">
                    <input type="radio" name="_sel" {"checked" if active else ""}
                           onchange="this.form.submit()"
                           style="width:18px;height:18px;accent-color:#34d399;cursor:pointer;">
                    <span>
                        <span style="color:#e5e7eb;font-weight:600;">{_html.escape(c['credential_name'])}</span>
                        <span style="color:#64748b;font-size:0.75rem;">&nbsp;· {c['provider']} · ••••{_html.escape(c['key_last4'])}</span>
                        {active_tag}
                    </span>
                </label>
                <button type="submit" formaction="/api/advisor/credentials/delete" formnovalidate
                        onclick="return confirm('Delete this API key?');"
                        style="background:#1e293b;border:1px solid #ef4444;color:#fca5a5;
                            border-radius:6px;padding:4px 12px;font-size:0.72rem;cursor:pointer;font-family:inherit;">Delete</button>
            </form>"""
        creds_block = rows
    else:
        creds_block = ('<p style="color:#64748b;font-size:0.8rem;margin:10px 0 0;">'
                       'No API keys yet. Add one below to start chatting.</p>')

    # Scan-shield toggle — checked == shielded (not scannable). Subscriber-only opt-out.
    shielded = not is_scannable(player.id)
    kl = "22px" if shielded else "2px"
    kb = "#ef4444" if shielded else "#1e293b"
    kbd = "#ef4444" if shielded else "#334155"
    shield_note = (
        "Shielded — other players' advisors can't see your books; they only get your public "
        "leaderboard standing and must infer the rest."
        if shielded else
        "Open — other players' advisors can surface your full books when they ask about you. "
        "(This is the default. Only subscribers can shield.)")
    shield_block = f"""
        <form action="/api/advisor/privacy" method="post" style="margin-top:14px;border-top:1px solid #1e293b;padding-top:12px;">
            <label style="display:flex;align-items:center;gap:12px;cursor:pointer;">
                <div style="position:relative;flex-shrink:0;width:44px;height:24px;">
                    <input type="checkbox" name="shield" {"checked" if shielded else ""}
                           style="position:absolute;opacity:0;width:0;height:0;" onchange="this.form.submit()">
                    <div style="position:absolute;inset:0;border-radius:12px;background:{kb};border:1px solid {kbd};transition:background .2s;">
                        <div style="position:absolute;top:2px;left:{kl};width:18px;height:18px;border-radius:50%;background:white;transition:left .2s;"></div>
                    </div>
                </div>
                <span style="font-size:0.85rem;color:#f1f5f9;">🛡️ Shield my books from other players' advisors</span>
            </label>
            <p style="color:#64748b;font-size:0.74rem;margin:6px 0 0;">{shield_note}</p>
        </form>"""

    # Self-serve diagnostics + reset, so players can recover from a confusing state.
    wipe_block = ""
    if creds:
        wipe_block = f"""
        <div style="margin-top:10px;display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap;">
            <span style="color:#64748b;font-size:0.74rem;">{len(creds)} key{'s' if len(creds)!=1 else ''} saved on your account.</span>
            <form action="/api/advisor/credentials/wipe" method="post" style="display:inline;"
                  onsubmit="return confirm('Delete ALL {len(creds)} saved API key(s)? This cannot be undone — you can re-add keys afterward.');">
                <button type="submit" style="background:#1a0505;border:1px solid #ef4444;color:#fca5a5;
                    border-radius:6px;padding:4px 12px;font-size:0.72rem;cursor:pointer;font-family:inherit;">🗑 Wipe all keys</button>
            </form>
        </div>"""

    return f"""
    <div style="background:#0f172a;border:1px solid #1e293b;border-radius:10px;padding:18px 20px;max-width:600px;">
        <p style="color:#e5e7eb;font-size:0.82rem;font-weight:600;margin:0 0 6px;">Your Gemini API keys</p>
        {creds_block}
        {wipe_block}
        {shield_block}
        <div style="margin-top:14px;border-top:1px solid #1e293b;padding-top:14px;">
            <p style="color:#e5e7eb;font-size:0.82rem;font-weight:600;margin:0 0 6px;">Add a free Google Gemini key</p>
            <ol style="color:#94a3b8;font-size:0.78rem;line-height:1.7;margin:0 0 12px;padding-left:18px;">
                <li>Go to <a href="https://aistudio.google.com/app/apikey" target="_blank" rel="noopener noreferrer" style="color:#38bdf8;">Google AI Studio → API keys</a> (free; many players use a fresh Google account just for this).</li>
                <li>Click <strong>Create API key</strong> and copy the key (usually starts with <code>AIza…</code>).</li>
                <li>Paste it below, give it a name, and Save. Gemini's free tier is plenty for normal chatting; any cost is billed to <em>your</em> Google account, not ours.</li>
            </ol>
        </div>
        <form action="/api/advisor/credentials/add" method="post">
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
                Your key is encrypted at rest, shown only as ••••last-4, and used only for your advisor chats.
                You can save several keys and switch between them anytime.
            </p>
            <button type="submit"
                    style="background:#34d399;color:#04261a;border:none;border-radius:6px;padding:8px 18px;
                           font-size:0.82rem;font-weight:700;cursor:pointer;font-family:inherit;">Save key</button>
        </form>
    </div>"""


@router.get("/advisor", response_class=HTMLResponse)
def advisor_page(
    session_token: Optional[str] = Cookie(None),
    m: str = "",
    e: str = "",
):
    from ux import shell
    import html as _h
    player = _player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)

    # Status banner from a prior action (save / wipe / error). Capped + escaped.
    banner = ""
    if e:
        banner = (f'<div style="max-width:760px;margin:10px 0;padding:10px 14px;background:#1a0505;'
                  f'border:1px solid #ef4444;color:#fca5a5;border-radius:8px;font-size:0.85rem;">'
                  f'⚠ {_h.escape(e[:300])}</div>')
    elif m:
        banner = (f'<div style="max-width:760px;margin:10px 0;padding:10px 14px;background:#052e16;'
                  f'border:1px solid #16a34a;color:#4ade80;border-radius:8px;font-size:0.85rem;">'
                  f'✓ {_h.escape(m[:300])}</div>')

    if not _is_pro(player):
        body = """
        <a href="/" style="color:#38bdf8;">&larr; Dashboard</a>
        <h1 style="margin:8px 0 4px 0;">🤖 Financial Advisor</h1>
        <div class="card" style="max-width:640px;margin-top:16px;text-align:center;padding:36px;">
            <div style="font-size:2.2rem;margin-bottom:10px;">🔒</div>
            <p style="color:#e5e7eb;font-weight:600;">The Financial Advisor is a Wadsworth Pro feature.</p>
            <p style="color:#94a3b8;font-size:0.88rem;">Get a personal AI that understands the game, your
               own empire, and your rivals' standings — bring your own free Gemini key.</p>
            <a href="/settings?tab=account" class="btn-blue" style="display:inline-block;margin-top:12px;padding:10px 22px;">View Wadsworth Pro</a>
        </div>"""
        return HTMLResponse(shell("Financial Advisor", body, player.cash_balance, player.id))

    cred = get_active_credential(player.id)
    has_key = bool(cred and cred.get("api_key"))
    active_name = cred.get("credential_name") if cred else ""

    if not has_key:
        body = f"""
        <a href="/" style="color:#38bdf8;">&larr; Dashboard</a>
        <h1 style="margin:8px 0 4px 0;">🤖 Financial Advisor</h1>
        {banner}
        <p style="max-width:600px;color:#94a3b8;font-size:0.9rem;margin:0 0 16px;line-height:1.6;">
            A private AI that understands the Wadsworth game, your own empire, and your rivals' standings,
            so it can help you plan, compete, and outmaneuver. It runs on your own free Google Gemini key,
            so it's free to use and your conversations are never stored on our server. Add a key to begin:
        </p>
        {_management_panel_html(player)}"""
        return HTMLResponse(shell("Financial Advisor", body, player.cash_balance, player.id))

    import html as _html
    powered = _html.escape(active_name or "your key", quote=True)
    shielded = not is_scannable(player.id)
    shield_status = "🛡️ your books are shielded" if shielded else "👁️ your books are scannable"
    body = f"""
    <a href="/" style="color:#38bdf8;">&larr; Dashboard</a>
    <div style="display:flex;align-items:baseline;justify-content:space-between;gap:10px;flex-wrap:wrap;">
        <h1 style="margin:8px 0 4px 0;">🤖 Financial Advisor</h1>
        <span style="color:#64748b;font-size:0.78rem;">Powered by: {powered} · Gemini · {shield_status} · chats are never saved on our server</span>
    </div>
    {banner}
    <p style="max-width:760px;color:#94a3b8;font-size:0.82rem;margin:4px 0 12px;line-height:1.5;">
        I give in-game guidance about Wadsworth, your own empire, and your rivals — taxes, what to build,
        how a mechanic works, and how you stack up against other players (name a player and I'll size them
        up). I can't trade or move money for you. Manage your keys and privacy below the chat.
    </p>
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

    <h2 style="max-width:760px;margin:22px 0 8px;font-size:1.05rem;color:#34d399;">⚙️ Your keys &amp; privacy</h2>
    {_management_panel_html(player)}

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
