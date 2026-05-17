"""
contacts.py — Player contact system.

Each Contact row represents a directed request (requester → recipient).
Once accepted, both parties can see each other's contact card.
Notes are private and directional (requester_notes / recipient_notes).
"""

from datetime import datetime
from typing import Optional, List, Tuple

from sqlalchemy import Column, Integer, String, Text, DateTime, or_, and_
from sqlalchemy.ext.declarative import declarative_base

from database import engine, SessionLocal

Base = declarative_base()

ADMIN_PLAYER_ID = 1          # Admin is everyone's contact; no limit applies
MAX_CONTACTS = 46            # Non-admin players may have at most this many contacts


# ──────────────────────────────────────────────────────────────────────────────
# MODEL
# ──────────────────────────────────────────────────────────────────────────────

class Contact(Base):
    """Bidirectional contact relationship between two players."""
    __tablename__ = "player_contacts"

    id               = Column(Integer, primary_key=True, index=True)
    requester_id     = Column(Integer, index=True, nullable=False)
    recipient_id     = Column(Integer, index=True, nullable=False)
    status           = Column(String(16), default="pending")  # pending | accepted | declined
    requester_notes  = Column(Text, nullable=True)   # private — only requester sees this
    recipient_notes  = Column(Text, nullable=True)   # private — only recipient sees this
    created_at       = Column(DateTime, default=datetime.utcnow)
    updated_at       = Column(DateTime, default=datetime.utcnow)


# ──────────────────────────────────────────────────────────────────────────────
# DB HELPER
# ──────────────────────────────────────────────────────────────────────────────

def get_db():
    return SessionLocal()


# ──────────────────────────────────────────────────────────────────────────────
# CRUD
# ──────────────────────────────────────────────────────────────────────────────

def get_contact_row(player_id: int, other_id: int) -> Optional[Contact]:
    """Return the Contact row between two players (either direction)."""
    db = get_db()
    try:
        return db.query(Contact).filter(
            or_(
                and_(Contact.requester_id == player_id, Contact.recipient_id == other_id),
                and_(Contact.requester_id == other_id,  Contact.recipient_id == player_id),
            )
        ).first()
    finally:
        db.close()


def send_contact_request(requester_id: int, recipient_id: int) -> Tuple[bool, str]:
    if requester_id == recipient_id:
        return False, "Cannot add yourself as a contact."
    # Admin has no contact limit; admin is not counted in others' limits either
    if requester_id != ADMIN_PLAYER_ID:
        current = [oid for (_, oid, _) in get_contacts(requester_id) if oid != ADMIN_PLAYER_ID]
        if len(current) >= MAX_CONTACTS:
            return False, f"Contact limit reached ({MAX_CONTACTS} max). Remove an existing contact to add new ones."
    existing = get_contact_row(requester_id, recipient_id)
    if existing:
        if existing.status == "accepted":
            return False, "Already contacts."
        if existing.status == "pending":
            return False, "Request already pending."
        if existing.status == "declined":
            # Allow re-request — update the row so direction is correct
            db = get_db()
            try:
                row = db.query(Contact).filter(Contact.id == existing.id).first()
                if row:
                    row.requester_id = requester_id
                    row.recipient_id = recipient_id
                    row.status       = "pending"
                    row.updated_at   = datetime.utcnow()
                    db.commit()
                return True, "Contact request sent."
            finally:
                db.close()
    db = get_db()
    try:
        db.add(Contact(requester_id=requester_id, recipient_id=recipient_id))
        db.commit()
        return True, "Contact request sent."
    finally:
        db.close()


def accept_contact_request(recipient_id: int, contact_id: int) -> Tuple[bool, str]:
    # Check acceptor's limit (admin exempt; admin requester doesn't count)
    if recipient_id != ADMIN_PLAYER_ID:
        db_check = get_db()
        try:
            row_check = db_check.query(Contact).filter(Contact.id == contact_id).first()
            requester = row_check.requester_id if row_check else None
        finally:
            db_check.close()
        if requester != ADMIN_PLAYER_ID:
            current = [oid for (_, oid, _) in get_contacts(recipient_id) if oid != ADMIN_PLAYER_ID]
            if len(current) >= MAX_CONTACTS:
                return False, f"You've reached your contact limit ({MAX_CONTACTS} max). Remove an existing contact first."
    db = get_db()
    try:
        row = db.query(Contact).filter(
            Contact.id == contact_id,
            Contact.recipient_id == recipient_id,
            Contact.status == "pending",
        ).first()
        if not row:
            return False, "Request not found."
        row.status     = "accepted"
        row.updated_at = datetime.utcnow()
        db.commit()
        return True, "Contact added."
    finally:
        db.close()


def decline_contact_request(recipient_id: int, contact_id: int) -> Tuple[bool, str]:
    db = get_db()
    try:
        row = db.query(Contact).filter(
            Contact.id == contact_id,
            Contact.recipient_id == recipient_id,
            Contact.status == "pending",
        ).first()
        if not row:
            return False, "Request not found."
        row.status     = "declined"
        row.updated_at = datetime.utcnow()
        db.commit()
        return True, "Request declined."
    finally:
        db.close()


def remove_contact(player_id: int, contact_id: int) -> Tuple[bool, str]:
    db = get_db()
    try:
        row = db.query(Contact).filter(
            Contact.id == contact_id,
            Contact.status == "accepted",
            or_(Contact.requester_id == player_id, Contact.recipient_id == player_id),
        ).first()
        if not row:
            return False, "Contact not found."
        db.delete(row)
        db.commit()
        return True, "Contact removed."
    finally:
        db.close()


def update_notes(player_id: int, contact_id: int, notes: str) -> Tuple[bool, str]:
    db = get_db()
    try:
        row = db.query(Contact).filter(
            Contact.id == contact_id,
            Contact.status == "accepted",
            or_(Contact.requester_id == player_id, Contact.recipient_id == player_id),
        ).first()
        if not row:
            return False, "Contact not found."
        if row.requester_id == player_id:
            row.requester_notes = notes[:2000]
        else:
            row.recipient_notes = notes[:2000]
        row.updated_at = datetime.utcnow()
        db.commit()
        return True, "Notes saved."
    finally:
        db.close()


def get_contacts(player_id: int) -> List[Tuple[Contact, int, str]]:
    """Return [(Contact, other_player_id, my_notes)] for all accepted contacts."""
    db = get_db()
    try:
        rows = db.query(Contact).filter(
            Contact.status == "accepted",
            or_(Contact.requester_id == player_id, Contact.recipient_id == player_id),
        ).order_by(Contact.updated_at.desc()).all()
        result = []
        for row in rows:
            if row.requester_id == player_id:
                other_id = row.recipient_id
                my_notes = row.requester_notes or ""
            else:
                other_id = row.requester_id
                my_notes = row.recipient_notes or ""
            result.append((row, other_id, my_notes))
        return result
    finally:
        db.close()


def get_incoming_requests(player_id: int) -> List[Contact]:
    db = get_db()
    try:
        return db.query(Contact).filter(
            Contact.recipient_id == player_id,
            Contact.status == "pending",
        ).order_by(Contact.created_at.desc()).all()
    finally:
        db.close()


def get_outgoing_requests(player_id: int) -> List[Contact]:
    db = get_db()
    try:
        return db.query(Contact).filter(
            Contact.requester_id == player_id,
            Contact.status == "pending",
        ).order_by(Contact.created_at.desc()).all()
    finally:
        db.close()


def ensure_admin_contact(player_id: int) -> None:
    """Ensure player_id has an accepted contact row with the admin (player_id=1).
    Idempotent — safe to call on every login or registration.
    """
    if player_id == ADMIN_PLAYER_ID:
        return
    existing = get_contact_row(player_id, ADMIN_PLAYER_ID)
    if existing and existing.status == "accepted":
        return
    db = get_db()
    try:
        if existing:
            row = db.query(Contact).filter(Contact.id == existing.id).first()
            if row:
                row.status       = "accepted"
                row.updated_at   = datetime.utcnow()
                db.commit()
        else:
            db.add(Contact(
                requester_id=ADMIN_PLAYER_ID,
                recipient_id=player_id,
                status="accepted",
            ))
            db.commit()
    except Exception as e:
        db.rollback()
        print(f"[Contacts] ensure_admin_contact({player_id}) failed: {e}")
    finally:
        db.close()


def seed_admin_contact_all_players() -> int:
    """Retroactively ensure every existing player has admin as an accepted contact.
    Returns the number of rows created or updated.
    """
    from auth import Player as _Player, get_db as _auth_get_db
    auth_db = _auth_get_db()
    try:
        all_ids = [r.id for r in auth_db.query(_Player.id).filter(_Player.id != ADMIN_PLAYER_ID).all()]
    finally:
        auth_db.close()

    count = 0
    for pid in all_ids:
        existing = get_contact_row(pid, ADMIN_PLAYER_ID)
        if existing and existing.status == "accepted":
            continue
        db = get_db()
        try:
            if existing:
                row = db.query(Contact).filter(Contact.id == existing.id).first()
                if row:
                    row.status     = "accepted"
                    row.updated_at = datetime.utcnow()
                    db.commit()
                    count += 1
            else:
                db.add(Contact(
                    requester_id=ADMIN_PLAYER_ID,
                    recipient_id=pid,
                    status="accepted",
                ))
                db.commit()
                count += 1
        except Exception as e:
            db.rollback()
            print(f"[Contacts] seed_admin_contact_all_players pid={pid} error: {e}")
        finally:
            db.close()
    print(f"[Contacts] seed_admin_contact_all_players: seeded {count}/{len(all_ids)} players")
    return count


def search_players(query: str, viewer_id: int, limit: int = 12) -> list:
    """Search players by business name. Returns list of dicts."""
    from auth import Player, get_db as get_auth_db
    db = get_auth_db()
    try:
        rows = (
            db.query(Player)
            .filter(Player.business_name.ilike(f"%{query}%"), Player.id != viewer_id)
            .limit(limit)
            .all()
        )
        return [{"id": r.id, "name": r.business_name} for r in rows]
    finally:
        db.close()


# ──────────────────────────────────────────────────────────────────────────────
# CONTACT CARD RENDERER
# ──────────────────────────────────────────────────────────────────────────────

def _sec(title: str, body: str, icon: str = "") -> str:
    return f'''
    <div style="margin-bottom:16px;">
        <div style="font-size:0.7rem; font-weight:bold; letter-spacing:0.08em;
                    color:#64748b; text-transform:uppercase; margin-bottom:6px;">
            {icon} {title}
        </div>
        <div style="color:#e5e7eb; font-size:0.85rem;">{body}</div>
    </div>'''


def build_contact_card_html(subject_id: int, disp: dict, fmt_usd_fn) -> str:
    """
    Assemble a full contact-card HTML panel for subject_id as seen by the viewer.
    Uses try/except per section so a missing module never crashes the whole card.
    """
    from auth import Player, get_db as get_auth_db
    auth_db = get_auth_db()
    try:
        subject = auth_db.query(Player).filter(Player.id == subject_id).first()
        if not subject:
            return '<div style="color:#ef4444;">Player not found.</div>'
        name = subject.business_name
        cash = subject.cash_balance
    finally:
        auth_db.close()

    F = fmt_usd_fn  # shorthand

    parts = []

    # ── Header ──
    _level_badge = ""
    try:
        from events import get_player_level
        _lvl = get_player_level(subject_id)
        _lv  = _lvl["level"]
        _trp = _lvl["trophies"]
        _pct = _lvl["progress_pct"]
        _nxt = _lvl["next_threshold"]
        _tip = (f"{_trp:,} trophies · {_pct:.0f}% to Lv {_lv+1}"
                if _nxt else f"{_trp:,} trophies · MAX LEVEL")
        _level_badge = (
            f'<span title="{_tip}" style="'
            f'display:inline-flex;align-items:center;gap:4px;'
            f'background:#1e1b4b;border:1px solid #4338ca;border-radius:10px;'
            f'padding:2px 8px;font-size:0.72rem;font-weight:700;color:#a5b4fc;">'
            f'<span style="color:#818cf8;">Lv</span> {_lv} ★</span>'
        )
    except Exception:
        pass

    _founding_badge = ""
    try:
        from beta import has_pocket_empire
        if has_pocket_empire(subject_id):
            _founding_badge = (
                '<span title="Founding Tester — one of the original 48 Android beta players" '
                'style="display:inline-flex;align-items:center;gap:4px;'
                'background:#1c1008;border:1px solid #f59e0b;border-radius:10px;'
                'padding:2px 8px;font-size:0.72rem;font-weight:700;color:#fbbf24;">'
                '📱 Founding Tester</span>'
            )
    except Exception:
        pass

    parts.append(f'''
    <div style="display:flex; align-items:center; gap:14px; padding-bottom:16px;
                border-bottom:1px solid #1e293b; margin-bottom:16px;">
        <div style="width:52px; height:52px; background:#0f172a; border:2px solid #334155;
                    border-radius:50%; display:flex; align-items:center; justify-content:center;
                    font-size:1.5rem; font-weight:bold; color:#38bdf8; flex-shrink:0;">
            {name[0].upper() if name else "?"}
        </div>
        <div>
            <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
                <span style="font-size:1.15rem; font-weight:bold; color:#e5e7eb;">{name}</span>
                {_level_badge}
                {_founding_badge}
            </div>
            <div style="font-size:0.75rem; color:#64748b;">Player ID #{subject_id}</div>
        </div>
    </div>''')

    # ── Net Worth / Leaderboard ──
    try:
        from stats_ux import PlayerStats, get_db as get_stats_db
        sdb = get_stats_db()
        try:
            ps = sdb.query(PlayerStats).filter(PlayerStats.player_id == subject_id).first()
        finally:
            sdb.close()
        if ps:
            parts.append(_sec("Net Worth & Leaderboard", f'''
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px;">
                    <div><span style="color:#64748b;">Net Worth</span><br>
                         <span style="color:#22c55e; font-weight:bold;">{F(ps.total_net_worth, disp)}</span></div>
                    <div><span style="color:#64748b;">Wealth Rank</span><br>
                         <span style="color:#f59e0b; font-weight:bold;">#{ps.wealth_rank or "—"}</span></div>
                    <div><span style="color:#64748b;">Land Value</span><br>{F(ps.land_value, disp)}</div>
                    <div><span style="color:#64748b;">Inventory Value</span><br>{F(ps.inventory_value, disp)}</div>
                    <div><span style="color:#64748b;">Business Value</span><br>{F(ps.business_value, disp)}</div>
                    <div><span style="color:#64748b;">Share Value</span><br>{F(ps.share_value, disp)}</div>
                </div>''', "📊"))
    except Exception:
        pass

    # ── Cash Balances ──
    try:
        from reserve_banks import PlayerCurrencyBalance, get_db as get_rb_db
        rb_db = get_rb_db()
        try:
            balances = rb_db.query(PlayerCurrencyBalance).filter(
                PlayerCurrencyBalance.player_id == subject_id
            ).all()
        finally:
            rb_db.close()
        rows = f'<div><span style="color:#64748b;">USD</span> &nbsp;<span style="color:#22c55e;">{F(cash, disp)}</span></div>'
        for b in balances:
            if b.balance and b.balance > 0:
                rows += f'<div><span style="color:#64748b;">{b.currency_code}</span> &nbsp;<span style="color:#22c55e;">{b.balance:,.2f}</span></div>'
        parts.append(_sec("Cash Balances", f'<div style="display:flex; flex-wrap:wrap; gap:12px;">{rows}</div>', "💰"))
    except Exception:
        pass

    # ── Debt ──
    try:
        from reserve_banks import BankDebt, get_db as get_rb_db2
        rdb2 = get_rb_db2()
        try:
            debts = rdb2.query(BankDebt).filter(BankDebt.player_id == subject_id).all()
        finally:
            rdb2.close()
        if debts:
            total_debt = sum(d.amount_owed for d in debts)
            parts.append(_sec("Debt", f'<span style="color:#ef4444; font-weight:bold;">{F(total_debt, disp)}</span> across {len(debts)} loan(s)', "💳"))
        else:
            parts.append(_sec("Debt", '<span style="color:#22c55e;">No outstanding debt</span>', "💳"))
    except Exception:
        pass

    # ── Inventory ──
    try:
        from inventory import get_player_inventory
        inv = get_player_inventory(subject_id)
        if inv:
            inv_html = "".join(
                f'<span style="background:#0f172a; border:1px solid #1e293b; padding:2px 8px; border-radius:3px; margin:2px; display:inline-block;">'
                f'<span style="color:#94a3b8;">{k.replace("_"," ").title()}</span> '
                f'<span style="color:#e5e7eb;">{v:,.2f}</span></span>'
                for k, v in sorted(inv.items()) if v and v > 0
            )
            parts.append(_sec("Full Inventory", inv_html or "Empty", "📦"))
        else:
            parts.append(_sec("Full Inventory", "Empty", "📦"))
    except Exception:
        pass

    # ── Businesses ──
    try:
        from business import Business, BUSINESS_TYPES
        from database import SessionLocal as _MS
        bdb = _MS()
        try:
            bizs = bdb.query(Business).filter(
                Business.owner_id == subject_id, Business.is_active == True
            ).all()
        finally:
            bdb.close()
        if bizs:
            biz_html = "".join(
                f'<div style="padding:4px 0; border-bottom:1px solid #0f172a;">'
                f'<span style="color:#a78bfa;">{BUSINESS_TYPES.get(b.business_type, {}).get("name", b.business_type.replace("_"," ").title())}</span>'
                f' <span style="color:#64748b; font-size:0.8rem;">Plot #{b.land_plot_id}</span></div>'
                for b in bizs
            )
            parts.append(_sec(f"Businesses Owned ({len(bizs)})", biz_html, "🏭"))
        else:
            parts.append(_sec("Businesses Owned", "None", "🏭"))
    except Exception:
        pass

    # ── Land Holdings ──
    try:
        from land import LandPlot
        from database import SessionLocal as _MS2
        ldb = _MS2()
        try:
            plots = ldb.query(LandPlot).filter(LandPlot.owner_id == subject_id).all()
        finally:
            ldb.close()
        if plots:
            occupied_dot = '<span style="color:#ef4444;">●</span>'
            plot_html = "".join(
                f'<span style="background:#0f172a; border:1px solid #1e293b; padding:2px 8px; border-radius:3px; margin:2px; display:inline-block;">'
                f'<span style="color:#94a3b8;">#{p.id}</span> '
                f'<span style="color:#e5e7eb;">{p.terrain_type.replace("_", " ").title()}</span>'
                f'{occupied_dot if p.occupied_by_business_id else ""}'
                f'</span>'
                for p in plots
            )
            parts.append(_sec(f"Land Holdings ({len(plots)} plots)", plot_html, "🌍"))
        else:
            parts.append(_sec("Land Holdings", "No plots owned", "🌍"))
    except Exception:
        pass

    # ── City & County Membership ──
    try:
        from cities import get_player_city
        city = get_player_city(subject_id)
        city_txt = f'<span style="color:#38bdf8;">{city.name}</span>' if city else '<span style="color:#64748b;">No city</span>'
        parts.append(_sec("City Membership", city_txt, "🏙️"))
    except Exception:
        pass

    try:
        from counties import get_player_county
        county = get_player_county(subject_id)
        county_txt = f'<span style="color:#a78bfa;">{county.name}</span>' if county else '<span style="color:#64748b;">No county</span>'
        parts.append(_sec("County Membership", county_txt, "🗺️"))
    except Exception:
        pass

    # ── Executives ──
    try:
        from executive import get_active_executives, get_db as get_exec_db, EXECUTIVE_TYPES
        edb = get_exec_db()
        try:
            execs = get_active_executives(edb, subject_id)
        finally:
            edb.close()
        if execs:
            exec_html = "".join(
                f'<div style="padding:3px 0; border-bottom:1px solid #0f172a;">'
                f'<span style="color:#fbbf24;">{e.name}</span>'
                f' <span style="color:#64748b; font-size:0.8rem;">— {EXECUTIVE_TYPES.get(e.executive_type, {}).get("title", e.executive_type)}</span></div>'
                for e in execs
            )
            parts.append(_sec(f"Executives Employed ({len(execs)})", exec_html, "👔"))
        else:
            parts.append(_sec("Executives Employed", "None", "👔"))
    except Exception:
        pass

    # ── Stock Holdings ──
    try:
        from banks.brokerage_firm import ShareholderPosition, CompanyShares, get_db as get_firm_db
        fdb = get_firm_db()
        try:
            positions = fdb.query(ShareholderPosition).filter(
                ShareholderPosition.player_id == subject_id,
                ShareholderPosition.shares_owned > 0,
            ).all()
            if positions:
                stock_rows = ""
                for pos in positions:
                    co = fdb.query(CompanyShares).filter(CompanyShares.id == pos.company_id).first()
                    ticker = co.ticker_symbol if co else f"#{pos.company_id}"
                    stock_rows += (
                        f'<div style="padding:3px 0; border-bottom:1px solid #0f172a;">'
                        f'<span style="color:#38bdf8;">{ticker}</span>'
                        f' <span style="color:#e5e7eb;">{pos.shares_owned:,.0f} shares</span>'
                        f' <span style="color:#64748b; font-size:0.8rem;">avg {F(pos.average_cost or 0, disp)}/share</span>'
                        f'</div>'
                    )
                parts.append(_sec(f"Stock Holdings ({len(positions)} positions)", stock_rows, "📈"))
            else:
                parts.append(_sec("Stock Holdings", "No positions", "📈"))
        finally:
            fdb.close()
    except Exception:
        pass

    # ── Bond Holdings ──
    try:
        from reserve_banks import ReserveBankBond, get_db as get_rb_db3, ReserveSessionLocal
        rdb3 = ReserveSessionLocal()
        try:
            bonds = rdb3.query(ReserveBankBond).filter(
                ReserveBankBond.holder_player_id == subject_id,
                ReserveBankBond.status == "active",
            ).all()
        finally:
            rdb3.close()
        if bonds:
            bond_html = "".join(
                f'<div style="padding:3px 0; border-bottom:1px solid #0f172a;">'
                f'<span style="color:#f59e0b;">{F(b.face_value, disp)}</span>'
                f' <span style="color:#64748b; font-size:0.8rem;">{b.yield_rate*100:.1f}% yield · matures {b.matures_at.strftime("%b %d %Y") if b.matures_at else "—"}</span>'
                f'</div>'
                for b in bonds
            )
            parts.append(_sec(f"Bond Holdings ({len(bonds)})", bond_html, "🏦"))
        else:
            parts.append(_sec("Bond Holdings", "No active bonds", "🏦"))
    except Exception:
        pass

    # ── Dividends ──
    try:
        from stats_ux import TransactionLog, get_db as get_stats_db2
        sdb2 = get_stats_db2()
        try:
            div_paid = sdb2.query(TransactionLog).filter(
                TransactionLog.player_id == subject_id,
                TransactionLog.transaction_type == "dividend_paid",
            ).all()
            div_received = sdb2.query(TransactionLog).filter(
                TransactionLog.player_id == subject_id,
                TransactionLog.transaction_type == "dividend",
            ).all()
        finally:
            sdb2.close()
        total_paid     = sum(abs(t.amount) for t in div_paid)
        total_received = sum(t.amount for t in div_received if t.amount > 0)
        parts.append(_sec("Dividends", f'''
            <div style="display:flex; gap:20px; flex-wrap:wrap;">
                <div><span style="color:#64748b;">Total Paid Out</span><br>
                     <span style="color:#ef4444;">{F(total_paid, disp)}</span></div>
                <div><span style="color:#64748b;">Total Received</span><br>
                     <span style="color:#22c55e;">{F(total_received, disp)}</span></div>
            </div>''', "💸"))
    except Exception:
        pass

    # ── Land Market Listings ──
    try:
        from land_market import LandListing
        from database import SessionLocal as _MS3
        lmdb = _MS3()
        try:
            listings = lmdb.query(LandListing).filter(
                LandListing.seller_id == subject_id,
                LandListing.is_active == True,
            ).all()
        finally:
            lmdb.close()
        if listings:
            lm_html = "".join(
                f'<div style="padding:3px 0; border-bottom:1px solid #0f172a;">'
                f'Plot #{l.land_plot_id} — <span style="color:#22c55e;">{F(l.asking_price, disp)}</span>'
                f'</div>'
                for l in listings
            )
            parts.append(_sec(f"Land Market Listings ({len(listings)})", lm_html, "🌍"))
        else:
            parts.append(_sec("Land Market Listings", "None active", "🌍"))
    except Exception:
        pass

    # ── Commodity Market Orders ──
    try:
        from market import MarketOrder, OrderStatus, OrderType
        from database import SessionLocal as _MS4
        mdb = _MS4()
        try:
            orders = mdb.query(MarketOrder).filter(
                MarketOrder.player_id == subject_id,
                MarketOrder.status.in_([OrderStatus.ACTIVE, OrderStatus.PARTIALLY_FILLED]),
            ).all()
        finally:
            mdb.close()
        if orders:
            ord_html = "".join(
                f'<div style="padding:3px 0; border-bottom:1px solid #0f172a;">'
                f'<span style="color:{"#22c55e" if o.order_type == OrderType.BUY else "#ef4444"};">'
                f'{"BUY" if o.order_type == OrderType.BUY else "SELL"}</span>'
                f' {o.item_type.replace("_"," ").title()}'
                f' × {o.quantity_remaining:,.2f}'
                f' @ {F(o.price, disp)}</div>'
                for o in orders
            )
            parts.append(_sec(f"Commodity Market Orders ({len(orders)})", ord_html, "📋"))
        else:
            parts.append(_sec("Commodity Market Orders", "None active", "📋"))
    except Exception:
        pass

    # ── District Market Orders ──
    try:
        from district_market import DistrictMarketOrder, get_player_orders
        d_orders = get_player_orders(subject_id)
        if d_orders:
            dm_html = "".join(
                f'<div style="padding:3px 0; border-bottom:1px solid #0f172a;">'
                f'<span style="color:{"#22c55e" if o.order_type == "buy" else "#ef4444"};">'
                f'{o.order_type.upper()}</span>'
                f' {o.item_type.replace("_"," ").title()}'
                f' × {o.quantity:,.2f}'
                f' @ {F(o.price_per_unit, disp)}</div>'
                for o in d_orders
            )
            parts.append(_sec(f"District Market Orders ({len(d_orders)})", dm_html, "🏗️"))
        else:
            parts.append(_sec("District Market Orders", "None active", "🏗️"))
    except Exception:
        pass

    # ── Bankruptcy History ──
    try:
        from corporate_actions import BankruptcyRecord, get_db as get_ca_db
        cadb = get_ca_db()
        try:
            records = cadb.query(BankruptcyRecord).filter(
                BankruptcyRecord.player_id == subject_id
            ).order_by(BankruptcyRecord.filed_at.desc()).all()
        finally:
            cadb.close()
        if records:
            br_html = "".join(
                f'<div style="padding:3px 0; border-bottom:1px solid #0f172a;">'
                f'<span style="color:#{"ef4444" if r.is_active else "64748b"};">'
                f'{"🔴 ACTIVE" if r.is_active else "✅ Discharged"}</span>'
                f' <span style="color:#64748b; font-size:0.8rem;">'
                f'filed {r.filed_at.strftime("%b %d %Y") if r.filed_at else "—"}</span>'
                f'</div>'
                for r in records
            )
            parts.append(_sec(f"Bankruptcy History ({len(records)})", br_html, "⚖️"))
        else:
            parts.append(_sec("Bankruptcy History", '<span style="color:#22c55e;">Clean record</span>', "⚖️"))
    except Exception:
        pass

    # ── Contact List Count ──
    try:
        contacts_count = len(get_contacts(subject_id))
        parts.append(_sec("Contact Network", f'{contacts_count} mutual contact(s)', "🤝"))
    except Exception:
        pass

    return "".join(parts)


# ──────────────────────────────────────────────────────────────────────────────
# INIT
# ──────────────────────────────────────────────────────────────────────────────

def initialize():
    Base.metadata.create_all(bind=engine)
    print("[Contacts] Module initialized")
