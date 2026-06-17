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
import secrets
from typing import Optional, List

import requests
from fastapi import APIRouter, Cookie, Form, Body
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse


# ==========================
# CONSTANTS
# ==========================

# Selectable Gemini models (id, label). Works with free or paid keys — a paid key just lifts
# rate limits. The endpoint/auth are identical; only the model id in the URL changes.
GEMINI_MODELS = [
    ("gemini-2.5-pro",        "2.5 Pro — most capable (slower)"),
    ("gemini-2.5-flash",      "2.5 Flash — recommended (fast, free-tier)"),
    ("gemini-2.5-flash-lite", "2.5 Flash-Lite — fastest / cheapest"),
    ("gemini-2.0-flash",      "2.0 Flash"),
    ("gemini-2.0-flash-lite", "2.0 Flash-Lite"),
]
DEFAULT_MODEL = "gemini-2.5-flash"
_VALID_MODELS = {m for m, _ in GEMINI_MODELS}
_GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
HTTP_TIMEOUT = 60  # seconds; single outbound call. Kept under the ~100s edge/proxy limit even
                   # after a fast-retry, so a slow Pro "thinking" response isn't cut off.
_GEMINI_RETRIES = 3            # attempts on transient 5xx / connection blips (Gemini 503s are common)
_GEMINI_TRANSIENT = {500, 502, 503, 504}

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
        # Explicitly-shared advisor transcripts, addressed by an unguessable token. Short-lived
        # (cleaned on a ~3-day TTL matching the DM system) — only created when a player shares.
        """CREATE TABLE IF NOT EXISTS advisor_shared_threads (
                token         TEXT        PRIMARY KEY,
                sharer_id     INTEGER     NOT NULL,
                sharer_name   TEXT        NOT NULL,
                messages_json TEXT        NOT NULL,
                created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )""",
        # Per-key model choice (Gemini model id). Defaults to 2.5 Flash.
        "ALTER TABLE advisor_credentials ADD COLUMN IF NOT EXISTS model TEXT NOT NULL DEFAULT 'gemini-2.5-flash'",
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
            "SELECT id, credential_name, provider, key_last4, is_active, model, created_at "
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
            "SELECT id, credential_name, provider, api_key_enc, key_last4, model "
            "FROM advisor_credentials WHERE player_id = :pid AND is_active = TRUE "
            "ORDER BY created_at DESC LIMIT 1"
        ), {"pid": player_id}).mappings().first()
        if not row:
            row = db.execute(text(
                "SELECT id, credential_name, provider, api_key_enc, key_last4, model "
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


def add_credential(player_id: int, name: str, api_key: str, model: str = DEFAULT_MODEL) -> tuple[bool, str]:
    name = (name or "").strip()[:60] or "My key"
    api_key = (api_key or "").strip()
    model = model if model in _VALID_MODELS else DEFAULT_MODEL
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
            "(player_id, credential_name, provider, api_key_enc, key_last4, is_active, model) "
            "VALUES (:pid, :name, :prov, :enc, :last4, :active, :model)"
        ), {"pid": player_id, "name": name, "prov": provider,
            "enc": enc, "last4": api_key[-4:], "active": make_active, "model": model})
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


def set_credential_model(player_id: int, cred_id: int, model: str):
    if model not in _VALID_MODELS:
        return
    from auth import get_db
    from sqlalchemy import text
    db = get_db()
    try:
        db.execute(text("UPDATE advisor_credentials SET model = :m WHERE id = :cid AND player_id = :pid"),
                   {"m": model, "cid": cred_id, "pid": player_id})
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
# SHARED THREADS (explicitly-shared transcripts behind an unguessable token; short TTL)
# ==========================

_SHARE_TTL_DAYS = 4  # ~matches the DM system's CONVERSATION_TTL_DAYS (3); the link outlives the DM slightly


def _store_shared_thread(sharer_id: int, sharer_name: str, messages: list) -> Optional[str]:
    """Persist a transcript and return its token. Also purges expired rows (cheap, keeps the
    table tiny since it only ever holds the last few days of explicit shares)."""
    token = secrets.token_urlsafe(12)
    from auth import get_db
    from sqlalchemy import text
    db = get_db()
    try:
        db.execute(text(
            "DELETE FROM advisor_shared_threads "
            "WHERE created_at < NOW() - (:days || ' days')::interval"
        ), {"days": _SHARE_TTL_DAYS})
        db.execute(text(
            "INSERT INTO advisor_shared_threads (token, sharer_id, sharer_name, messages_json) "
            "VALUES (:t, :sid, :sn, :mj)"
        ), {"t": token, "sid": sharer_id, "sn": sharer_name[:80],
            "mj": json.dumps(messages)[:200000]})
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[Advisor] Could not store shared thread: {e}")
        return None
    finally:
        db.close()
    return token


def _get_shared_thread(token: str) -> Optional[dict]:
    """Return {sharer_name, messages} for a live (non-expired) token, else None."""
    from auth import get_db
    from sqlalchemy import text
    db = get_db()
    try:
        row = db.execute(text(
            "SELECT sharer_name, messages_json FROM advisor_shared_threads "
            "WHERE token = :t AND created_at >= NOW() - (:days || ' days')::interval"
        ), {"t": token, "days": _SHARE_TTL_DAYS}).first()
    finally:
        db.close()
    if not row:
        return None
    try:
        msgs = json.loads(row[1]) or []
    except Exception:
        msgs = []
    return {"sharer_name": row[0], "messages": msgs}


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

    # Subscription detail (Pro renewal/expiry) + skin
    try:
        from play_billing import get_player_subscription
        sub = get_player_subscription(player_id)
        if sub:
            exp = sub.get("expiry_time")
            exps = exp.strftime("%b %d, %Y") if exp else "—"
            lines.append(f"Subscription: {sub.get('sub_state','?')} (product {sub.get('product_id','?')}, "
                         f"through {exps})")
        elif not is_pro:
            lines.append("Subscription: none (free player)")
    except Exception:
        pass
    try:
        from auth import Player, get_db as _adb2
        db2 = _adb2()
        try:
            pp = db2.query(Player).filter(Player.id == player_id).first()
            skin = getattr(pp, "skin", None) if pp else None
        finally:
            db2.close()
        if skin and skin != "default":
            lines.append(f"Skin: {skin}")
    except Exception:
        pass

    # Bluesky / public snapshot status
    try:
        import bluesky as _bsky
        link = _bsky.get_link(player_id)
        if link:
            pub = "public" if link.get("public_profile") else "private"
            h = link.get("handle") or "?"
            lines.append(f"Bluesky: linked as @{h}; handle shown on P2P: "
                         f"{'yes' if link.get('show_on_p2p') else 'no'}; "
                         f"public snapshot page: {pub}")
        else:
            lines.append("Bluesky: not linked (can link in Settings → Account to enable a "
                         "shareable public snapshot page).")
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
    # Text with all tag tokens (@[..]/#[..]/$[..]/%[..]) stripped, so words *inside* a tag (e.g.
    # the "wheat" in #[item|wheat|Wheat]) can't spuriously match a player's business name below.
    clean_blob = re.sub(r"[@#$%/]\[[^\]]*\]", " ", text_blob)

    # @[id|name] mention tokens from the @ autocomplete — exact, unambiguous id resolution.
    for mid in re.findall(r"@\[(\d{1,7})\|", text_blob):
        try:
            pid = int(mid)
            if pid > 0 and pid != querying_id and pid not in found:
                found.append(pid)
        except Exception:
            pass

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
            if not nm:
                continue
            # Emoji/symbol names (e.g. "🌻") are 1-2 code points but distinctive, so match them
            # as a substring regardless of length. Long (>=4) alphanumeric names also match as a
            # plain substring. Short alphanumeric names need word boundaries so they don't match
            # inside longer words (e.g. "jo" should not hit "john").
            has_symbol = any(not (c.isalnum() or c.isspace()) for c in nm)
            if len(nm) >= 4 or has_symbol:
                matched = nm in clean_blob
            else:
                matched = re.search(r"(?<!\w)" + re.escape(nm) + r"(?!\w)", clean_blob) is not None
            if matched:
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

    # Stock market — tradable companies (top by market cap)
    try:
        from banks.brokerage_firm import CompanyShares, get_db as _fdb
        fdb = _fdb()
        try:
            cos = fdb.query(CompanyShares).filter(CompanyShares.current_price > 0).all()
        finally:
            fdb.close()
        if cos:
            cos.sort(key=lambda x: -((x.current_price or 0) * (x.shares_outstanding or 0)))
            lines.append("")
            lines.append(f"STOCK MARKET ({len(cos)} listed companies, top by market cap):")
            for co in cos[:20]:
                cap = (co.current_price or 0) * (co.shares_outstanding or 0)
                lines.append(f"  {co.ticker_symbol} ({co.company_name}): "
                             f"${co.current_price:,.2f}/sh · cap {_compact(cap)}")
    except Exception:
        pass

    # Bank shares
    try:
        from banks import BankEntity
        from database import SessionLocal as _BS
        bdb = _BS()
        try:
            be = bdb.query(BankEntity).all()
        finally:
            bdb.close()
        if be:
            lines.append("BANK SHARES: " + ", ".join(
                f"{b.bank_id} ${(b.share_price or 0):,.2f}/sh" for b in be))
    except Exception:
        pass

    # ETFs / index funds (share price / NAV where exposed)
    try:
        etfs = []
        for _mod, _label in (("city_nav_etf", "CityNav"), ("energy_etf", "Energy"),
                             ("apple_seeds_etf", "AppleSeeds"), ("wbc50_index_fund", "WBC-50 Fund")):
            try:
                m = __import__(f"banks.{_mod}", fromlist=["get_etf_info"])
                info = m.get_etf_info()
                if info and info.get("share_price"):
                    etfs.append(f"{info.get('name', _label)} ${info['share_price']:,.4f}/sh")
            except Exception:
                continue
        if etfs:
            lines.append("ETFs / INDEX FUNDS: " + ", ".join(etfs))
    except Exception:
        pass

    # Annuity products (immediate-rate schedule)
    try:
        from banks.brokerage_firm import ANNUITY_IMMEDIATE_RATES
        if ANNUITY_IMMEDIATE_RATES:
            lines.append("ANNUITY RATES (immediate, by term): " + ", ".join(
                f"{d}d {r*100:.0f}%" for d, r in sorted(ANNUITY_IMMEDIATE_RATES.items())))
    except Exception:
        pass

    # Land market — individual cheapest listings
    try:
        from land_market import LandListing, get_db as _lm2
        db = _lm2()
        try:
            lst = (db.query(LandListing.land_plot_id, LandListing.asking_price)
                   .filter(LandListing.is_active == True)
                   .order_by(LandListing.asking_price.asc()).limit(30).all())
        finally:
            db.close()
        if lst:
            lines.append("LAND LISTINGS (cheapest first): " + ", ".join(
                f"plot #{pid} ${ap:,.0f}" for pid, ap in lst))
    except Exception:
        pass

    # Stock order book — best bid/ask per company (from the brokerage order book)
    try:
        from banks.brokerage_order_book import OrderBook
        from banks.brokerage_firm import CompanyShares
        from database import SessionLocal as _SOB
        db = _SOB()
        try:
            rows = (db.query(OrderBook.company_shares_id, OrderBook.order_side, OrderBook.limit_price)
                    .filter(OrderBook.status.in_(["pending", "partial"]),
                            OrderBook.limit_price.isnot(None)).all())
            book = {}
            for csid, side, price in rows:
                if not price:
                    continue
                b = book.setdefault(csid, {"bid": None, "ask": None})
                if str(side) == "sell":
                    b["ask"] = price if b["ask"] is None else min(b["ask"], price)
                else:
                    b["bid"] = price if b["bid"] is None else max(b["bid"], price)
            if book:
                tickers = dict(db.query(CompanyShares.id, CompanyShares.ticker_symbol)
                               .filter(CompanyShares.id.in_(list(book.keys()))).all())
        finally:
            db.close()
        if book:
            lines.append("")
            lines.append(f"STOCK ORDER BOOK ({len(book)} companies with open orders):")
            for csid in list(book.keys())[:30]:
                b = book[csid]
                tk = tickers.get(csid, f"#{csid}")
                bid = f"bid ${b['bid']:,.2f}" if b["bid"] is not None else "bid —"
                ask = f"ask ${b['ask']:,.2f}" if b["ask"] is not None else "ask —"
                lines.append(f"  {tk}: {bid} / {ask}")
    except Exception:
        pass

    # Meme-coin order book — best bid/ask per coin (priced in native tokens)
    try:
        from memecoins import MemeCoinOrder
        from database import SessionLocal as _SMO
        db = _SMO()
        try:
            rows = (db.query(MemeCoinOrder.meme_symbol, MemeCoinOrder.order_type, MemeCoinOrder.price)
                    .filter(MemeCoinOrder.status.in_(["active", "partial"]),
                            MemeCoinOrder.price.isnot(None)).all())
        finally:
            db.close()
        book = {}
        for sym, otype, price in rows:
            if not price:
                continue
            b = book.setdefault(sym, {"bid": None, "ask": None})
            if str(otype) == "sell":
                b["ask"] = price if b["ask"] is None else min(b["ask"], price)
            else:
                b["bid"] = price if b["bid"] is None else max(b["bid"], price)
        if book:
            lines.append("")
            lines.append(f"MEME-COIN ORDER BOOK ({len(book)} coins, priced in native token):")
            for sym in list(book.keys())[:20]:
                b = book[sym]
                bid = f"bid {b['bid']:,.6f}" if b["bid"] is not None else "bid —"
                ask = f"ask {b['ask']:,.6f}" if b["ask"] is not None else "ask —"
                lines.append(f"  {sym}: {bid} / {ask}")
    except Exception:
        pass

    # WSC stablecoin market
    try:
        from wallet import SWAP_FEE_SELL, SWAP_FEE_BUY, WSC_AMM_FEE
        lines.append("")
        lines.append(f"WSC STABLECOIN: pegged 1 WSC = $1 in-game cash · native↔WSC swap fee "
                     f"{SWAP_FEE_BUY*100:.0f}%/leg · AMM pool fee {WSC_AMM_FEE*100:.1f}% · "
                     f"redeemable 1:1 for cash.")
    except Exception:
        pass

    # Live ORDER BOOKS (open buy/sell orders) for the commodity & district markets. This is the
    # actual listings — best bid/ask plus the highest ask, which exposes a single inflated
    # sell order sitting on the book (the cause of weird "market prices").
    def _book(model, get_db_fn, label):
        try:
            db = get_db_fn()
            try:
                orders = db.query(model.item_type, model.order_type, model.price).filter(
                    model.status.in_(["active", "partial"]), model.price.isnot(None)).all()
            finally:
                db.close()
            book = {}
            for item, otype, price in orders:
                if not price:
                    continue
                b = book.setdefault(item, {"bid": None, "ask": None, "ask_hi": None, "nb": 0, "ns": 0})
                if str(otype) == "sell":
                    b["ns"] += 1
                    b["ask"] = price if b["ask"] is None else min(b["ask"], price)
                    b["ask_hi"] = price if b["ask_hi"] is None else max(b["ask_hi"], price)
                else:
                    b["nb"] += 1
                    b["bid"] = price if b["bid"] is None else max(b["bid"], price)
            if not book:
                return
            lines.append("")
            lines.append(f"{label} ORDER BOOK (open orders — best bid / best ask; 'high ask' flags "
                         f"an inflated listing sitting on the book):")
            for item in sorted(book)[:100]:
                b = book[item]
                bid = f"bid ${b['bid']:,.2f}" if b["bid"] is not None else "bid —"
                ask = f"ask ${b['ask']:,.2f}" if b["ask"] is not None else "ask —"
                hi = (f" · high ask ${b['ask_hi']:,.2f}"
                      if b["ask_hi"] and b["ask"] and b["ask_hi"] > b["ask"] else "")
                lines.append(f"  {item.replace('_',' ')}: {bid} / {ask}{hi} "
                             f"· {b['nb']} buy / {b['ns']} sell orders")
        except Exception:
            pass

    try:
        from market import MarketOrder, get_db as _modb
        _book(MarketOrder, _modb, "COMMODITY")
    except Exception:
        pass
    try:
        from district_market import DistrictMarketOrder, get_db as _ddmdb
        _book(DistrictMarketOrder, _ddmdb, "DISTRICT")
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
                    try:
                        from city_projects import get_city_sales_tax_rate
                        stax = f"{get_city_sales_tax_rate(ct.id)*100:.2f}% sales tax"
                    except Exception:
                        stax = "sales tax —"
                    cur = getattr(ct, "currency_type", None) or "USD"
                    lines.append(f"  {ct.name} — mayor {mname} · {members} members · {stax} · "
                                 f"legal tender {cur} · join fee {_compact(ct.application_fee)}")
            finally:
                adb.close()
    except Exception:
        pass

    # County governance (crypto prices are in the market snapshot; this is the civic side)
    try:
        from counties import get_all_counties
        cos = get_all_counties() or []
        # Merge in the per-county exchange fee (not exposed by get_all_counties).
        fee_map = {}
        try:
            from counties import County, get_db as _ccdb
            ccdb = _ccdb()
            try:
                for cid, fee in ccdb.query(County.id, County.transaction_fee_percent).all():
                    fee_map[cid] = fee
            finally:
                ccdb.close()
        except Exception:
            pass
        if cos:
            lines.append("")
            lines.append(f"COUNTIES ({len(cos)}):")
            for c2 in cos[:15]:
                fee = fee_map.get(c2.get("id"))
                feetxt = f"{fee*100:.1f}% exchange fee" if fee is not None else "exchange fee 2%"
                lines.append(f"  {c2.get('name','?')} — token {c2.get('crypto_symbol','?')} · "
                             f"{c2.get('city_count',0)}/{c2.get('max_cities','?')} cities · "
                             f"{feetxt} · treasury {_compact(c2.get('treasury_balance',0))} · "
                             f"mining pool {c2.get('mining_energy',0):,.0f}")
    except Exception:
        pass

    # Open P2P contract market (LISTED contracts anyone can bid on)
    try:
        from p2p import Contract, ContractItem, ContractStatus, get_db as _pdb
        pdb = _pdb()
        try:
            listed = (pdb.query(Contract)
                      .filter(Contract.status == ContractStatus.LISTED)
                      .order_by(Contract.listed_at.desc()).limit(15).all())
            rows = []
            for ct in listed:
                items = pdb.query(ContractItem).filter(
                    ContractItem.contract_id == ct.id).all()
                idesc = ", ".join(
                    f"{it.item_type.replace('_',' ')}×{it.quantity_per_delivery:,.0f}"
                    for it in items) or "—"
                mode = "price-bid" if ct.contract_mode == "price_bid" else "quantity-bid"
                price = ct.price_per_delivery or ct.minimum_bid or 0
                rows.append(f"  #{ct.id} [{mode}] {idesc} · "
                            f"{ct.total_deliveries or 1} delivery(s) @ {_compact(price)} "
                            f"per {getattr(ct,'delivery_interval','cycle')}")
        finally:
            pdb.close()
        if rows:
            lines.append("")
            lines.append(f"OPEN P2P CONTRACTS ({len(rows)} listed on the trading market):")
            lines.extend(rows)
    except Exception:
        pass

    # Executive marketplace (execs available to hire)
    try:
        from executive import get_marketplace_executives, get_db as _edb, EXECUTIVE_JOBS
        edb = _edb()
        try:
            free = get_marketplace_executives(edb) or []
            rows = []
            for e in free[:20]:
                title = EXECUTIVE_JOBS.get(e.job, {}).get("title", e.job.replace("_", " ").title())
                rows.append(f"  {e.first_name} {e.last_name} — {title} · Lv{e.level} · "
                            f"wage ${e.wage:,.0f}/{e.pay_cycle} · {e.marketplace_reason or 'available'}")
        finally:
            edb.close()
        if rows:
            lines.append("")
            lines.append(f"EXECUTIVE MARKETPLACE ({len(rows)} available to hire; hiring cost scales "
                         "with your net worth):")
            lines.extend(rows)
    except Exception:
        pass

    # Port Authority government contracts (open for bidding)
    try:
        from port_authority import get_open_contracts
        pacs = get_open_contracts() or []
        if pacs:
            lines.append("")
            lines.append(f"PORT AUTHORITY CONTRACTS ({len(pacs)} open for bidding):")
            for pc in pacs[:10]:
                items = pc.get("required_items") or {}
                idesc = ", ".join(f"{k.replace('_',' ')}×{v:,.0f}" for k, v in list(items.items())[:6]) or "—"
                close = pc.get("bid_closes_at", "")[:10]
                lines.append(f"  {pc.get('title','?')}: needs {idesc} · "
                             f"pays {_compact(pc.get('payment_usd',0))} + {pc.get('trophy_reward',0)} trophies "
                             f"· deposit {_compact(pc.get('security_deposit_usd',0))} · bids close {close}")
    except Exception:
        pass

    # WikiWads article index (so the advisor can point players to real in-game articles)
    try:
        import wiki as _wiki
        entries = _wiki.list_entries() or []
        if entries:
            by_cat = {}
            for e in entries:
                by_cat.setdefault(e.get("category", "reference"), []).append(e.get("title", "?"))
            lines.append("")
            lines.append("WIKIWADS ARTICLES (in-game encyclopedia — point players here to learn more):")
            for cat in sorted(by_cat):
                titles = by_cat[cat][:12]
                lines.append(f"  {cat}: " + "; ".join(titles))
    except Exception:
        pass

    snapshot = "\n".join(lines) if lines else ""
    c["t"], c["v"] = _t.time(), snapshot
    return snapshot


# ==========================
# GEMINI CALL
# ==========================

def _gen_config(model: str) -> dict:
    """Per-model generationConfig. The 2.5 models are 'thinking' models whose thinking tokens
    count against maxOutputTokens. Flash/Flash-Lite let us disable thinking for complete, fast
    answers; Pro cannot disable thinking, so we just give it a bigger budget. 2.0 models aren't
    thinking models, so we omit thinkingConfig entirely (some reject it)."""
    cfg = {"temperature": 0.6, "maxOutputTokens": 2048}
    if model in ("gemini-2.5-flash", "gemini-2.5-flash-lite"):
        cfg["thinkingConfig"] = {"thinkingBudget": 0}
    elif model == "gemini-2.5-pro":
        cfg["maxOutputTokens"] = 4096  # Pro always thinks; leave room for the visible answer
    return cfg


def _call_gemini(api_key: str, system: str, messages: List[dict],
                 model: str = DEFAULT_MODEL) -> tuple[bool, str]:
    """One stateless generateContent call. Returns (ok, reply_or_error_message)."""
    if model not in _VALID_MODELS:
        model = DEFAULT_MODEL
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
        "generationConfig": _gen_config(model),
    }
    import time
    resp = None
    for attempt in range(_GEMINI_RETRIES):
        try:
            resp = requests.post(
                f"{_GEMINI_BASE}/{model}:generateContent",
                params={"key": api_key},
                json=payload,
                timeout=HTTP_TIMEOUT,
            )
        except requests.Timeout:
            # Timeouts are slow; don't hammer the (already overloaded) endpoint — fail clearly.
            return False, "The advisor took too long to respond. Please try again."
        except Exception as e:
            # Connection blip — brief backoff and retry, since these are usually fast.
            if attempt < _GEMINI_RETRIES - 1:
                time.sleep(0.8 * (attempt + 1))
                continue
            return False, f"Could not reach the AI service: {e}"
        # Gemini frequently returns transient 503 "model is overloaded" / 500s — retry those.
        if resp.status_code in _GEMINI_TRANSIENT and attempt < _GEMINI_RETRIES - 1:
            time.sleep(0.8 * (attempt + 1))
            continue
        break

    if resp.status_code == 400:
        return False, "Your Gemini API key was rejected (invalid or malformed). Update it in Settings → Account."
    if resp.status_code in (401, 403):
        return False, "Your Gemini API key is unauthorized or expired. Update it in Settings → Account."
    if resp.status_code == 429:
        return False, "Your Gemini key has hit its rate limit / quota. Try again later or use a different key."
    if resp.status_code in _GEMINI_TRANSIENT:
        print(f"[Advisor] Gemini transient error after {_GEMINI_RETRIES} tries "
              f"(HTTP {resp.status_code}): {resp.text[:200]}")
        return False, "The AI service is temporarily overloaded. Please try again in a moment."
    if resp.status_code != 200:
        print(f"[Advisor] Gemini HTTP {resp.status_code}: {resp.text[:200]}")
        return False, f"The AI service returned an error (HTTP {resp.status_code})."

    try:
        data = resp.json()
        cand = (data.get("candidates") or [{}])[0]
        # Safety blocks / empty finish
        parts = (cand.get("content") or {}).get("parts") or []
        reply = "".join(p.get("text", "") for p in parts).strip()
        fr = cand.get("finishReason") or ""
        if not reply:
            if fr == "SAFETY":
                return True, "I can't help with that one. Try rephrasing your question about your Wadsworth strategy."
            return True, "I didn't have a response for that — try rephrasing your question."
        if fr == "MAX_TOKENS":
            reply += "\n\n…(reply was long and got cut off — ask me to continue.)"
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
    model: str = Form(DEFAULT_MODEL),
):
    player = _player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)
    if not _is_pro(player):
        return _redirect_advisor(err="The Financial Advisor is a Wadsworth Pro feature.")
    ok, msg = add_credential(player.id, credential_name, api_key, model=model)
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


@router.post("/api/advisor/credentials/model")
def advisor_cred_model(
    session_token: Optional[str] = Cookie(None),
    cred_id: int = Form(...),
    model: str = Form(...),
):
    player = _player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)
    set_credential_model(player.id, cred_id, model)
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

    ok, reply = _call_gemini(cred["api_key"], system, messages,
                             model=cred.get("model") or DEFAULT_MODEL)
    if not ok:
        return JSONResponse({"ok": False, "error": reply}, status_code=502)
    return JSONResponse({"ok": True, "reply": reply})


# ==========================
# SHARE TO DM / GROUP DM
# ==========================

def _format_transcript(messages: list) -> list:
    """Normalize the client messages into [{role, content}] (user|model), trimmed."""
    out = []
    for m in messages:
        if not isinstance(m, dict):
            continue
        content = str(m.get("content", "")).strip()
        if not content:
            continue
        role = "user" if m.get("role") == "user" else "model"
        out.append({"role": role, "content": content[:8000]})
    return out


@router.get("/api/advisor/share/targets")
def advisor_share_targets(session_token: Optional[str] = Cookie(None)):
    player = _player(session_token)
    if not player:
        return JSONResponse({"ok": False, "error": "Not signed in."}, status_code=401)
    if not _is_pro(player):
        return JSONResponse({"ok": False, "error": "Pro feature."}, status_code=403)
    targets = []
    try:
        import dm
        from auth import Player, get_db as _adb
        convs = dm.get_player_conversations(player.id) or []
        adb = _adb()
        try:
            for c in convs:
                other = c["player2_id"] if c["player1_id"] == player.id else c["player1_id"]
                if other == player.id:
                    continue
                p = adb.query(Player).filter(Player.id == other).first()
                targets.append({"type": "dm", "id": other,
                                "name": p.business_name if p else f"Player #{other}"})
        finally:
            adb.close()
        for g in (dm.get_player_group_conversations(player.id) or []):
            targets.append({"type": "group", "id": g["id"],
                            "name": g.get("name") or "Group chat"})
    except Exception as e:
        return JSONResponse({"ok": False, "error": f"Could not load conversations: {e}"},
                            status_code=500)
    return JSONResponse({"ok": True, "targets": targets})


@router.post("/api/advisor/share")
def advisor_share(
    session_token: Optional[str] = Cookie(None),
    payload: dict = Body(...),
):
    player = _player(session_token)
    if not player:
        return JSONResponse({"ok": False, "error": "Not signed in."}, status_code=401)
    if not _is_pro(player):
        return JSONResponse({"ok": False, "error": "The Financial Advisor is a Wadsworth Pro feature."},
                            status_code=403)
    messages = _format_transcript(payload.get("messages") or [])
    if not messages:
        return JSONResponse({"ok": False, "error": "There's no conversation to share yet."},
                            status_code=400)
    target_type = payload.get("target_type")
    target_id = payload.get("target_id")

    import dm
    sharer_name = getattr(player, "business_name", None) or f"Player #{player.id}"

    # Resolve destination + recipients, scoped to the sharer.
    if target_type == "dm":
        try:
            other_id = int(target_id)
        except Exception:
            return JSONResponse({"ok": False, "error": "Bad target."}, status_code=400)
        if other_id == player.id:
            return JSONResponse({"ok": False, "error": "Can't share to yourself."}, status_code=400)
        try:
            dm.get_or_create_conversation(player.id, other_id)
        except Exception:
            pass
        conv_id = dm.make_conversation_id(player.id, other_id)
        recipients = [other_id]
        is_group = False
        # Destination display name
        try:
            from auth import Player, get_db as _adb
            adb = _adb()
            try:
                p = adb.query(Player).filter(Player.id == other_id).first()
                dest_name = p.business_name if p else f"Player #{other_id}"
            finally:
                adb.close()
        except Exception:
            dest_name = f"Player #{other_id}"
    elif target_type == "group":
        conv_id = str(target_id)
        try:
            members = dm.get_group_participant_ids(conv_id) or []
        except Exception:
            members = []
        if player.id not in members:
            return JSONResponse({"ok": False, "error": "You're not in that group."}, status_code=403)
        recipients = [m for m in members if m != player.id]
        is_group = True
        dest_name = "the group"
        try:
            for g in (dm.get_player_group_conversations(player.id) or []):
                if g["id"] == conv_id:
                    dest_name = g.get("name") or "the group"
                    break
        except Exception:
            pass
    else:
        return JSONResponse({"ok": False, "error": "Bad target type."}, status_code=400)

    # Store the transcript behind a token.
    token = _store_shared_thread(player.id, sharer_name, messages)
    if not token:
        return JSONResponse({"ok": False, "error": "Could not prepare the share. Try again."},
                            status_code=500)

    # One short message, attributed to the advisor, with a link to the full thread.
    try:
        from profiles_ux import SITE_BASE as _BASE
    except Exception:
        _BASE = ""
    link = f"{_BASE}/advisor/shared/{token}"
    first_q = next((m["content"] for m in messages if m["role"] == "user"), "")
    preview = (" — “" + first_q[:90] + ("…" if len(first_q) > 90 else "") + "”") if first_q else ""
    content = f"\U0001F4E4 Shared by {sharer_name}{preview}\nOpen the full conversation: {link}"
    if len(content) > 500:
        content = f"\U0001F4E4 Shared by {sharer_name}\nOpen the full conversation: {link}"

    try:
        if is_group:
            saved = dm.save_group_dm(conv_id, player.id, "\U0001F916 Financial Advisor", content)
        else:
            saved = dm.save_dm(conv_id, player.id, "\U0001F916 Financial Advisor", content)
    except Exception as e:
        return JSONResponse({"ok": False, "error": f"Could not send: {e}"}, status_code=500)
    if not saved:
        return JSONResponse({"ok": False, "error": "Could not send the message."}, status_code=500)

    # Notify recipients (save_dm itself doesn't notify).
    try:
        from push_ux import send_push_notification
        body = f"shared a Financial Advisor conversation{preview}"
        for rid in recipients:
            try:
                send_push_notification(rid, f"\U0001F916 Financial Advisor (via {sharer_name})",
                                       body[:120], url="/p2p/dms", notif_type="dm",
                                       tag=f"dm-{conv_id}")
            except Exception:
                pass
    except Exception:
        pass

    return JSONResponse({"ok": True, "name": dest_name})


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
        sel_style = ("background:#020617;border:1px solid #334155;color:#e5e7eb;border-radius:6px;"
                     "padding:4px 6px;font-size:0.72rem;font-family:inherit;cursor:pointer;")
        for c in creds:
            active = c["is_active"]
            cur_model = c.get("model") or DEFAULT_MODEL
            active_tag = ('<span style="background:#052e16;border:1px solid #16a34a;color:#4ade80;'
                          'border-radius:8px;padding:1px 8px;font-size:0.68rem;font-weight:700;'
                          'margin-left:8px;">IN USE</span>' if active else '')
            model_opts = "".join(
                f'<option value="{mid}" {"selected" if mid == cur_model else ""}>{lbl}</option>'
                for mid, lbl in GEMINI_MODELS)
            rows += f"""
            <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap;
                        padding:10px;margin-top:6px;border:1px solid {'#16a34a' if active else '#1e293b'};
                        border-radius:8px;background:{'#0c1f16' if active else '#0b1220'};">
                <form action="/api/advisor/credentials/activate" method="post"
                      style="display:flex;align-items:center;gap:10px;flex:1;min-width:180px;margin:0;">
                    <input type="hidden" name="cred_id" value="{c['id']}">
                    <label style="display:flex;align-items:center;gap:10px;cursor:pointer;">
                        <input type="radio" name="_sel" {"checked" if active else ""}
                               onchange="this.form.submit()"
                               style="width:18px;height:18px;accent-color:#34d399;cursor:pointer;">
                        <span>
                            <span style="color:#e5e7eb;font-weight:600;">{_html.escape(c['credential_name'])}</span>
                            <span style="color:#64748b;font-size:0.75rem;">&nbsp;· ••••{_html.escape(c['key_last4'])}</span>
                            {active_tag}
                        </span>
                    </label>
                </form>
                <form action="/api/advisor/credentials/model" method="post" style="margin:0;">
                    <input type="hidden" name="cred_id" value="{c['id']}">
                    <select name="model" onchange="this.form.submit()" style="{sel_style}">{model_opts}</select>
                </form>
                <form action="/api/advisor/credentials/delete" method="post" style="margin:0;"
                      onsubmit="return confirm('Delete this API key?');">
                    <input type="hidden" name="cred_id" value="{c['id']}">
                    <button type="submit" style="background:#1e293b;border:1px solid #ef4444;color:#fca5a5;
                        border-radius:6px;padding:4px 12px;font-size:0.72rem;cursor:pointer;font-family:inherit;">Delete</button>
                </form>
            </div>"""
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
            <div style="margin-bottom:8px;">
                <label style="display:block;color:#64748b;font-size:0.75rem;margin-bottom:4px;">Model</label>
                <select name="model" style="width:100%;max-width:300px;padding:8px 10px;background:#020617;border:1px solid #1e293b;color:#e5e7eb;border-radius:4px;font-family:inherit;font-size:16px;">
                    {"".join(f'<option value="{mid}" {"selected" if mid == DEFAULT_MODEL else ""}>{lbl}</option>' for mid, lbl in GEMINI_MODELS)}
                </select>
            </div>
            <p style="color:#64748b;font-size:0.74rem;margin:8px 0 12px;line-height:1.5;">
                Your key is encrypted at rest, shown only as ••••last-4, and used only for your advisor chats.
                You can save several keys, pick a model per key, and switch anytime. (Paid keys work too —
                same setup, just higher limits.)
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
    active_model = (cred.get("model") or DEFAULT_MODEL) if cred else DEFAULT_MODEL
    model_label = dict(GEMINI_MODELS).get(active_model, active_model).split("—")[0].strip()
    shielded = not is_scannable(player.id)
    shield_status = "🛡️ your books are shielded" if shielded else "👁️ your books are scannable"
    body = f"""
    <a href="/" style="color:#38bdf8;">&larr; Dashboard</a>
    <div style="display:flex;align-items:baseline;justify-content:space-between;gap:10px;flex-wrap:wrap;">
        <h1 style="margin:8px 0 4px 0;">🤖 Financial Advisor</h1>
        <span style="color:#64748b;font-size:0.78rem;">Powered by: {powered} · {_html.escape(model_label)} · {shield_status} · chats are never saved on our server</span>
    </div>
    {banner}
    <p style="max-width:760px;color:#94a3b8;font-size:0.82rem;margin:4px 0 12px;line-height:1.5;">
        I give in-game guidance about Wadsworth, your own empire, and your rivals — taxes, what to build,
        how a mechanic works, and how you stack up against other players. Tag things inline to be precise —
        <strong>@</strong>player <strong>#</strong>item <strong>$</strong>token <strong>%</strong>TICKER — and I'll
        size them up. I can't trade or move money for you. Manage your keys and privacy below the chat.
    </p>
    <style>
    /* Tag chips + autocomplete — same legend as DMs/chatrooms */
    .mention {{ display:inline; padding:1px 4px; border-radius:3px; font-weight:600; font-size:0.82em; text-decoration:none; }}
    a.mention:hover {{ opacity:0.75; }}
    .mention-player {{ background:rgba(34,197,94,0.15);  color:#22c55e; }}
    .mention-item   {{ background:rgba(56,189,248,0.15); color:#38bdf8; }}
    .mention-crypto {{ background:rgba(251,191,36,0.15); color:#fbbf24; }}
    .mention-stock  {{ background:rgba(249,115,22,0.15); color:#f97316; }}
    .mention-dropdown {{ display:none; position:absolute; bottom:calc(100% + 4px); left:12px; right:64px;
        background:#0f1828; border:1px solid #334155; border-radius:6px; z-index:50; max-height:220px;
        overflow-y:auto; box-shadow:0 -4px 20px rgba(0,0,0,0.5); }}
    .mention-dropdown.show {{ display:block; }}
    .mention-dropdown-header {{ padding:5px 10px 3px; font-size:0.66rem; color:#64748b; text-transform:uppercase;
        letter-spacing:0.05em; border-bottom:1px solid #1e293b; }}
    .mention-option {{ display:flex; align-items:center; gap:8px; padding:7px 10px; cursor:pointer; font-size:0.82rem; }}
    .mention-option:hover, .mention-option.selected {{ background:#1e2d3d; }}
    .mention-trigger-badge {{ font-weight:700; font-size:0.85rem; min-width:12px; }}
    .mention-primary {{ color:#e2e8f0; }}
    .mention-secondary {{ color:#64748b; font-size:0.75rem; margin-left:auto; }}
    </style>
    <div class="card" style="max-width:760px;padding:0;overflow:hidden;">
        <div id="adv-log" style="height:52vh;min-height:320px;overflow-y:auto;padding:18px;display:flex;flex-direction:column;gap:12px;"></div>
        <div style="border-top:1px solid var(--border,#1e293b);padding:12px;display:flex;gap:8px;align-items:flex-end;position:relative;">
            <div id="adv-mention-dd" class="mention-dropdown"></div>
            <textarea id="adv-input" rows="2" placeholder="Ask about taxes, strategy…  tag with @player #item $token %TICKER"
                style="flex:1;resize:vertical;background:var(--bg-page,#020617);border:1px solid var(--border,#334155);
                       color:var(--text-primary,#e5e7eb);border-radius:8px;padding:10px;font-family:inherit;font-size:16px;"></textarea>
            <button id="adv-send" class="btn-blue" style="padding:10px 18px;white-space:nowrap;">Send</button>
        </div>
        <div style="padding:0 12px 10px;font-size:0.7rem;color:#64748b;">
            Tags: <span class="mention mention-player">@player</span>
            <span class="mention mention-item">#item/business</span>
            <span class="mention mention-crypto">$token</span>
            <span class="mention mention-stock">%TICKER</span>
        </div>
    </div>
    <div style="max-width:760px;margin-top:10px;display:flex;gap:8px;flex-wrap:wrap;">
        <button id="adv-download" style="background:#1e293b;border:1px solid #334155;color:#94a3b8;border-radius:6px;
            padding:7px 14px;font-size:0.8rem;cursor:pointer;font-family:inherit;">⬇ Download conversation</button>
        <label style="background:#1e293b;border:1px solid #334155;color:#94a3b8;border-radius:6px;
            padding:7px 14px;font-size:0.8rem;cursor:pointer;">⬆ Import conversation
            <input id="adv-import" type="file" accept="application/json,.json" style="display:none;">
        </label>
        <button id="adv-share" style="background:#1e293b;border:1px solid #334155;color:#94a3b8;border-radius:6px;
            padding:7px 14px;font-size:0.8rem;cursor:pointer;font-family:inherit;">📤 Share to a DM</button>
        <button id="adv-clear" style="background:#1e293b;border:1px solid #334155;color:#94a3b8;border-radius:6px;
            padding:7px 14px;font-size:0.8rem;cursor:pointer;font-family:inherit;">🗑 Clear</button>
    </div>
    <div id="adv-share-box" style="max-width:760px;margin-top:8px;display:none;background:var(--bg-card,#0f172a);
        border:1px solid var(--border,#1e293b);border-radius:8px;padding:12px;">
        <div style="font-size:0.82rem;color:#e5e7eb;margin-bottom:8px;">Share this conversation to a DM or group:</div>
        <div id="adv-share-targets" style="display:flex;flex-wrap:wrap;gap:6px;"></div>
        <div id="adv-share-status" style="font-size:0.78rem;color:#64748b;margin-top:8px;"></div>
    </div>
    <p style="max-width:760px;color:#64748b;font-size:0.75rem;margin-top:8px;">
        Educational, in-game guidance only — not real-world financial advice. Conversations live only in your
        browser (never stored unless you share one, then it's kept a few days behind a private link, like a DM);
        download them to continue later, even on another device.
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
        function fmt(raw) {{
            // Render @player #item/business $token %stock tags as chips/links (matches DMs/chatrooms).
            var re = /@\[([^\]]+)\]|#\[([^\]]+)\]|\/\[([^\]]+)\]|\$\[([^\]]+)\]|%\[([^\]]+)\]/g;
            var escLink = function(s) {{
                return esc(s).replace(/(https?:\/\/[^\s<]+)/g, function(u) {{
                    return '<a href="' + u + '" target="_blank" rel="noopener noreferrer">' + u + '</a>';
                }});
            }};
            var out = '', last = 0, m;
            raw = raw || '';
            while ((m = re.exec(raw)) !== null) {{
                if (m.index > last) out += escLink(raw.slice(last, m.index));
                if (m[1] !== undefined) {{
                    var p1 = m[1].split('|');
                    var name = p1.length >= 2 ? p1[1] : p1[0];
                    var id = p1.length >= 2 ? p1[0] : null;
                    var href = id ? '/contacts?view=' + encodeURIComponent(id) : '/contacts?q=' + encodeURIComponent(name);
                    out += '<a href="' + href + '" class="mention mention-player">@' + esc(name) + '</a>';
                }} else if (m[2] !== undefined) {{
                    var p2 = m[2].split('|');
                    if (p2.length >= 3) {{
                        var wtype = p2[0], key = p2[1], nm2 = p2[2];
                        var href2 = wtype === 'item' ? '/market?item=' + encodeURIComponent(key)
                                  : wtype === 'district_item' ? '/district-market?item=' + encodeURIComponent(key)
                                  : wtype === 'district_biz' ? '/district-market' : '/land';
                        out += '<a href="' + href2 + '" class="mention mention-item">#' + esc(nm2) + '</a>';
                    }} else {{
                        out += '<span class="mention mention-item">#' + esc(p2[0]) + '</span>';
                    }}
                }} else if (m[3] !== undefined) {{
                    out += '<span class="mention mention-item">#' + esc(m[3]) + '</span>';
                }} else if (m[4] !== undefined) {{
                    var cp = m[4].split('|');
                    var csym = cp.length >= 2 ? cp[1] : cp[0];
                    var ctype = cp.length >= 2 ? cp[0] : 'meme';
                    var chref = ctype === 'native' ? '/token/' + encodeURIComponent(csym)
                              : ctype === 'meme' ? '/memecoins/' + encodeURIComponent(csym) : null;
                    if (chref) out += '<a href="' + chref + '" class="mention mention-crypto">$' + esc(csym) + '</a>';
                    else out += '<span class="mention mention-crypto">$' + esc(csym) + '</span>';
                }} else {{
                    out += '<a href="/brokerage/company/' + encodeURIComponent(m[5]) + '" class="mention mention-stock">%' + esc(m[5]) + '</a>';
                }}
                last = m.index + m[0].length;
            }}
            if (last < raw.length) out += escLink(raw.slice(last));
            return out;
        }}
        function bubble(role, text) {{
            var mine = role === 'user';
            var d = document.createElement('div');
            d.style.cssText = 'max-width:85%;padding:10px 14px;border-radius:12px;white-space:pre-wrap;line-height:1.5;font-size:0.9rem;' +
                (mine ? 'align-self:flex-end;background:var(--accent,#2563eb);color:#fff;border-bottom-right-radius:3px;'
                      : 'align-self:flex-start;background:var(--bg-page,#0f172a);border:1px solid var(--border,#1e293b);color:var(--text-primary,#e5e7eb);border-bottom-left-radius:3px;');
            d.innerHTML = fmt(text);
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

        // ── Tag autocomplete: @players  #items/business  $tokens  %stocks (matches DMs/chatrooms) ──
        var ddEl = document.getElementById('adv-mention-dd');
        var mState = null, mSugs = [], mSel = -1, mTimer = null;
        var TRIG_EP    = {{'@':'players','#':'items','$':'crypto','%':'stocks'}};
        var TRIG_LABEL = {{'@':'Players & NPCs','#':'Businesses & Items','$':'Crypto','%':'Stocks'}};
        var TRIG_COLOR = {{'@':'#22c55e','#':'#38bdf8','$':'#fbbf24','%':'#f97316'}};
        function detectTrigger(val, pos) {{
            var before = val.slice(0, pos), m;
            m = before.match(/(?:^|[\s,])(@\S*)$/);
            if (m) return {{ type:'@', start: before.lastIndexOf(m[1]), query: m[1].slice(1) }};
            m = before.match(/(?:^|[\s,])(\$\S*)$/);
            if (m) return {{ type:'$', start: before.lastIndexOf(m[1]), query: m[1].slice(1) }};
            m = before.match(/(?:^|[\s,])(%\S*)$/);
            if (m) return {{ type:'%', start: before.lastIndexOf(m[1]), query: m[1].slice(1) }};
            m = before.match(/(?:^|[\s,])(#[^@$#%]*)$/);
            if (m && m[1].length > 1) return {{ type:'#', start: before.lastIndexOf(m[1]), query: m[1].slice(1) }};
            return null;
        }}
        function closeMD() {{ mState = null; mSugs = []; mSel = -1; ddEl.classList.remove('show'); ddEl.innerHTML = ''; }}
        function renderMD() {{
            if (!mSugs.length) {{ ddEl.classList.remove('show'); ddEl.innerHTML = ''; return; }}
            var type = mState.type, color = TRIG_COLOR[type] || '#e2e8f0';
            var html = '<div class="mention-dropdown-header">' + (TRIG_LABEL[type] || type) + '</div>';
            mSugs.forEach(function(s, i) {{
                var sel = i === mSel ? ' selected' : '', primary, secondary;
                if (type === '@') {{ primary = esc(s.name); secondary = '#' + s.id; }}
                else if (type === '#') {{ primary = esc(s.name); secondary = esc(s.category || ''); }}
                else if (type === '%') {{ primary = esc(s.ticker) + ' · ' + esc(s.name); secondary = 'stock'; }}
                else {{ primary = esc(s.symbol) + ' · ' + esc(s.name); secondary = s.type; }}
                html += '<div class="mention-option' + sel + '" onmousedown="event.preventDefault();window.__advPick(' + i + ')">'
                    + '<span class="mention-trigger-badge" style="color:' + color + '">' + esc(type) + '</span>'
                    + '<span class="mention-primary">' + primary + '</span>'
                    + '<span class="mention-secondary">' + secondary + '</span></div>';
            }});
            ddEl.innerHTML = html; ddEl.classList.add('show');
        }}
        async function fetchMD(type, q) {{
            var ep = TRIG_EP[type]; if (!ep) return;
            try {{
                var r = await fetch('/api/chat/suggest/' + ep + '?q=' + encodeURIComponent(q), {{credentials:'same-origin'}});
                if (!r.ok) return;
                mSugs = await r.json(); mSel = mSugs.length ? 0 : -1; renderMD();
            }} catch(e) {{}}
        }}
        function pickMD(i) {{
            if (!mState || i < 0 || i >= mSugs.length) return;
            var s = mSugs[i], type = mState.type, rep;
            if (type === '@') {{ rep = '@[' + s.id + '|' + s.name + '] '; }}
            else if (type === '#') {{
                var wtype = s.wtype || ((s.category || '').toLowerCase().indexOf('item') >= 0 ? 'item' : 'biz');
                rep = '#[' + wtype + '|' + s.key + '|' + s.name + '] ';
            }} else if (type === '%') {{ rep = '%[' + s.ticker + '] '; }}
            else {{ rep = '$[' + (s.type || 'meme') + '|' + s.symbol + '] '; }}
            var after = input.value.slice(input.selectionStart);
            input.value = input.value.slice(0, mState.start) + rep + after;
            var np = mState.start + rep.length;
            input.setSelectionRange(np, np);
            closeMD(); input.focus();
        }}
        window.__advPick = pickMD;
        input.addEventListener('input', function() {{
            var t = detectTrigger(input.value, input.selectionStart);
            if (!t) {{ closeMD(); return; }}
            mState = t; clearTimeout(mTimer);
            mTimer = setTimeout(function() {{ fetchMD(t.type, t.query); }}, 120);
        }});
        input.addEventListener('blur', function() {{ setTimeout(closeMD, 150); }});

        input.addEventListener('keydown', function(e) {{
            if (mState && ddEl.classList.contains('show') && mSugs.length) {{
                if (e.key === 'ArrowDown') {{ e.preventDefault(); mSel = (mSel + 1) % mSugs.length; renderMD(); return; }}
                if (e.key === 'ArrowUp') {{ e.preventDefault(); mSel = (mSel - 1 + mSugs.length) % mSugs.length; renderMD(); return; }}
                if (e.key === 'Enter' || e.key === 'Tab') {{ e.preventDefault(); pickMD(mSel); return; }}
                if (e.key === 'Escape') {{ e.preventDefault(); closeMD(); return; }}
            }}
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

        // ── Share to a DM / group DM ──
        var shareBox = document.getElementById('adv-share-box');
        var shareTargets = document.getElementById('adv-share-targets');
        var shareStatus = document.getElementById('adv-share-status');
        document.getElementById('adv-share').addEventListener('click', async function() {{
            if (!messages.length) {{ alert('Say something to the advisor first.'); return; }}
            if (shareBox.style.display === 'block') {{ shareBox.style.display = 'none'; return; }}
            shareBox.style.display = 'block';
            shareTargets.innerHTML = ''; shareStatus.textContent = 'Loading your conversations…';
            try {{
                var r = await fetch('/api/advisor/share/targets', {{credentials:'same-origin'}});
                var data = await r.json();
                if (!data.ok) {{ shareStatus.textContent = data.error || 'Could not load conversations.'; return; }}
                if (!data.targets.length) {{
                    shareStatus.textContent = 'No DMs or groups yet — start one from P2P → DMs.'; return;
                }}
                shareStatus.textContent = '';
                data.targets.forEach(function(t) {{
                    var b = document.createElement('button');
                    b.textContent = (t.type === 'group' ? '👥 ' : '💬 ') + t.name;
                    b.style.cssText = 'background:#1e293b;border:1px solid #334155;color:#e5e7eb;border-radius:6px;'
                        + 'padding:5px 12px;font-size:0.8rem;cursor:pointer;font-family:inherit;';
                    b.addEventListener('click', function() {{ doShare(t, b); }});
                    shareTargets.appendChild(b);
                }});
            }} catch(e) {{ shareStatus.textContent = 'Network error loading conversations.'; }}
        }});
        async function doShare(t, btn) {{
            btn.disabled = true; shareStatus.textContent = 'Sharing…';
            try {{
                var r = await fetch('/api/advisor/share', {{
                    method:'POST', headers:{{'Content-Type':'application/json'}}, credentials:'same-origin',
                    body: JSON.stringify({{target_type:t.type, target_id:t.id, messages:messages}})
                }});
                var data = await r.json();
                if (data.ok) {{ shareStatus.textContent = '✓ Shared to ' + (data.name || t.name) + '.'; }}
                else {{ shareStatus.textContent = '⚠ ' + (data.error || 'Could not share.'); btn.disabled = false; }}
            }} catch(e) {{ shareStatus.textContent = '⚠ Network error.'; btn.disabled = false; }}
        }}
    }})();
    </script>
    """
    return HTMLResponse(shell("Financial Advisor", body, player.cash_balance, player.id))


def _tokens_to_html(raw: str) -> str:
    """Render @player / #item-or-business / $token / %stock tags as colored chips, escaping
    everything else. Mirrors the DM/chatroom tag legend (read-only, so chips not links)."""
    import re as _re
    import html as _h
    pat = _re.compile(r"@\[([^\]]+)\]|#\[([^\]]+)\]|/\[([^\]]+)\]|\$\[([^\]]+)\]|%\[([^\]]+)\]")

    def chip(bg, fg, text):
        return ('<span style="background:%s;color:%s;border-radius:3px;padding:1px 4px;'
                'font-weight:600;font-size:0.9em;">%s</span>' % (bg, fg, _h.escape(text)))

    out, last = [], 0
    for m in pat.finditer(raw):
        out.append(_h.escape(raw[last:m.start()]))
        if m.group(1) is not None:
            p = m.group(1).split("|"); nm = p[1] if len(p) >= 2 else p[0]
            out.append(chip("rgba(34,197,94,0.15)", "#22c55e", "@" + nm))
        elif m.group(2) is not None:
            p = m.group(2).split("|"); nm = p[2] if len(p) >= 3 else p[0]
            out.append(chip("rgba(56,189,248,0.15)", "#38bdf8", "#" + nm))
        elif m.group(3) is not None:
            out.append(chip("rgba(56,189,248,0.15)", "#38bdf8", "#" + m.group(3)))
        elif m.group(4) is not None:
            p = m.group(4).split("|"); sym = p[1] if len(p) >= 2 else p[0]
            out.append(chip("rgba(251,191,36,0.15)", "#fbbf24", "$" + sym))
        else:
            out.append(chip("rgba(249,115,22,0.15)", "#f97316", "%" + m.group(5)))
        last = m.end()
    out.append(_h.escape(raw[last:]))
    return "".join(out)


@router.get("/advisor/shared/{token}", response_class=HTMLResponse)
def advisor_shared_view(token: str, session_token: Optional[str] = Cookie(None)):
    """Read-only viewer for a shared advisor transcript. Login required (any player); the
    unguessable token + short TTL keep it private to whoever holds the DM link."""
    from ux import shell
    import html as _h
    player = _player(session_token)
    if not player:
        return RedirectResponse(url="/login", status_code=303)

    shared = _get_shared_thread(token)
    if not shared:
        body = """
        <a href="/" style="color:#38bdf8;">&larr; Dashboard</a>
        <h1 style="margin:8px 0 4px 0;">🤖 Shared conversation</h1>
        <div class="card" style="max-width:640px;margin-top:16px;padding:30px;text-align:center;">
            <p style="color:#94a3b8;">This shared conversation isn't available — the link may have
            expired (shared threads are kept only a few days, like DMs).</p>
        </div>"""
        return HTMLResponse(shell("Shared conversation", body, player.cash_balance, player.id))

    sharer = _h.escape(shared["sharer_name"])
    bubbles = ""
    for m in shared["messages"]:
        mine = m.get("role") == "user"
        txt = _tokens_to_html(str(m.get("content", "")))
        bubbles += (
            f'<div style="max-width:85%;padding:10px 14px;border-radius:12px;white-space:pre-wrap;'
            f'line-height:1.5;font-size:0.9rem;'
            + ("align-self:flex-end;background:var(--accent,#2563eb);color:#fff;border-bottom-right-radius:3px;"
               if mine else
               "align-self:flex-start;background:var(--bg-page,#0f172a);border:1px solid var(--border,#1e293b);color:var(--text-primary,#e5e7eb);border-bottom-left-radius:3px;")
            + f'">{txt}</div>'
        )

    # Raw JSON for a <script type="application/json"> block (entities are NOT decoded inside
    # <script>, so do NOT html-escape; just neutralize </script> breakout via <).
    payload = json.dumps({"version": 1, "messages": shared["messages"]}).replace("<", "\\u003c")
    body = f"""
    <a href="/" style="color:#38bdf8;">&larr; Dashboard</a>
    <div style="display:flex;align-items:baseline;justify-content:space-between;gap:10px;flex-wrap:wrap;">
        <h1 style="margin:8px 0 4px 0;">🤖 Shared conversation</h1>
        <span style="color:#64748b;font-size:0.8rem;">Shared by {sharer} · read-only</span>
    </div>
    <div class="card" style="max-width:760px;padding:18px;display:flex;flex-direction:column;gap:12px;">
        {bubbles}
    </div>
    <div style="max-width:760px;margin-top:10px;display:flex;gap:8px;flex-wrap:wrap;">
        <button id="sh-download" style="background:#1e293b;border:1px solid #334155;color:#94a3b8;border-radius:6px;
            padding:7px 14px;font-size:0.8rem;cursor:pointer;font-family:inherit;">⬇ Download conversation</button>
        <a href="/advisor" class="btn-blue" style="padding:7px 14px;font-size:0.8rem;text-decoration:none;">Open my Advisor</a>
    </div>
    <p style="max-width:760px;color:#64748b;font-size:0.75rem;margin-top:8px;">
        Download this thread and import it into your own Financial Advisor to continue it. (Pro feature.)
    </p>
    <script>
    (function() {{
        var data = JSON.parse(document.getElementById('sh-data').textContent);
        document.getElementById('sh-download').addEventListener('click', function() {{
            var blob = new Blob([JSON.stringify(data, null, 2)], {{type:'application/json'}});
            var a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = 'wadsworth-advisor-shared.json';
            a.click(); URL.revokeObjectURL(a.href);
        }});
    }})();
    </script>
    <script type="application/json" id="sh-data">{payload}</script>
    """
    return HTMLResponse(shell("Shared conversation", body, player.cash_balance, player.id))
