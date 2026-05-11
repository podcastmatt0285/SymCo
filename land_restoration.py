"""
land_restoration.py

Land Efficiency Restoration system.

Rules:
  - Eligible: plots with efficiency < 30% (not tutorial reward)
  - One active restoration per player at a time; cannot pause, stop, or restart
  - All eligible plots restored simultaneously at 500× the decay rate
  - Target: 150% efficiency (buffer above 100%; wages are still floored at 1× base)
  - Time to complete = time needed by the least efficient plot to reach 150%
  - Cost per plot = wage_multiplier × $1,000 USD (converted to player's legal tender)
  - Payment goes to the Federal Government immediately on start
  - 60-day cooldown after each restoration completes
  - COO executive wages bonus and city wage_savings buff reduce cost (cap 40%)
"""

import json
import threading
from datetime import datetime, timedelta
from typing import Optional, List, Tuple

from sqlalchemy import (Column, Integer, Float, String, Boolean, DateTime,
                        func, create_engine)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./symco.db"
engine       = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base         = declarative_base()

# ── Constants ──────────────────────────────────────────────────────────────────
ELIGIBILITY_THRESHOLD     = 30.0        # efficiency % below which a plot is eligible
RESTORATION_TARGET        = 150.0       # plots restored to 150% efficiency
RESTORATION_COOLDOWN_DAYS = 60          # cooldown days after completion
COST_PER_MULT_USD         = 1_000.0    # cost = wage_multiplier × $1 000 per plot
WAGE_MULT_FLOOR           = 0.005       # matches business.py max(0.005, eff/100)
EFFICIENCY_DECAY_PER_TICK = 0.00001 / 60   # matches land.py (% per second)
RESTORATION_RATE_PER_TICK = 500 * EFFICIENCY_DECAY_PER_TICK  # 500× decay rate

GOVERNMENT_PLAYER_ID = 0


# ── DB Model ───────────────────────────────────────────────────────────────────
class LandRestoration(Base):
    __tablename__ = "land_restorations"
    id               = Column(Integer, primary_key=True, autoincrement=True)
    player_id        = Column(Integer, nullable=False, index=True)
    plot_ids_json    = Column(String, nullable=False)   # JSON: [1, 2, 3]
    plot_starts_json = Column(String, nullable=False)   # JSON: {"1": 12.3, "2": 28.1}
    started_at       = Column(DateTime, default=datetime.utcnow)
    completes_at     = Column(DateTime, nullable=False)
    cooldown_until   = Column(DateTime, nullable=False)
    total_cost_usd   = Column(Float, default=0.0)
    status           = Column(String, default="active")  # "active" | "complete"


# ── DB helpers ─────────────────────────────────────────────────────────────────
def _db():
    return SessionLocal()


def initialize():
    Base.metadata.create_all(engine)
    try:
        from database import run_ddl_migration
        from land import engine as land_engine
        run_ddl_migration(
            land_engine,
            "ALTER TABLE land_plots ADD COLUMN IF NOT EXISTS is_restoring BOOLEAN DEFAULT FALSE"
        )
    except Exception as e:
        print(f"[LandRestoration] Migration warning: {e}")
    print("[LandRestoration] Initialized")


# ── Query helpers ──────────────────────────────────────────────────────────────
def get_active_restoration(player_id: int) -> Optional[LandRestoration]:
    db = _db()
    try:
        return db.query(LandRestoration).filter(
            LandRestoration.player_id == player_id,
            LandRestoration.status    == "active",
        ).first()
    finally:
        db.close()


def get_cooldown_until(player_id: int) -> Optional[datetime]:
    """Return the cooldown expiry for the player's last completed restoration, or None."""
    db = _db()
    try:
        last = db.query(LandRestoration).filter(
            LandRestoration.player_id == player_id,
            LandRestoration.status    == "complete",
        ).order_by(LandRestoration.cooldown_until.desc()).first()
        if last and last.cooldown_until > datetime.utcnow():
            return last.cooldown_until
        return None
    finally:
        db.close()


def get_eligible_plots(player_id: int):
    """LandPlots owned by player with efficiency < 30%, not tutorial reward."""
    from land import get_db as land_db_fn, LandPlot
    db = land_db_fn()
    try:
        return db.query(LandPlot).filter(
            LandPlot.owner_id          == player_id,
            LandPlot.efficiency        < ELIGIBILITY_THRESHOLD,
            LandPlot.is_tutorial_reward == False,
        ).all()
    finally:
        db.close()


def get_all_restoring_plot_ids() -> List[int]:
    """All plot IDs currently in an active restoration (for decay exclusion)."""
    db = _db()
    try:
        rows = db.query(LandRestoration).filter(
            LandRestoration.status == "active"
        ).all()
        ids: List[int] = []
        for r in rows:
            try:
                ids.extend(json.loads(r.plot_ids_json))
            except Exception:
                pass
        return ids
    finally:
        db.close()


# ── Cost / time helpers ────────────────────────────────────────────────────────
def calculate_plot_cost_usd(efficiency: float) -> float:
    """wage_multiplier × $1 000 for one plot."""
    eff_frac  = max(WAGE_MULT_FLOOR, efficiency / 100.0)
    wage_mult = 1.0 / eff_frac
    return wage_mult * COST_PER_MULT_USD


def calculate_total_time_seconds(plots) -> float:
    """Seconds needed for the least efficient plot to reach 150%."""
    if not plots:
        return 0.0
    min_eff  = min(p.efficiency for p in plots)
    distance = RESTORATION_TARGET - max(0.0, min_eff)
    return distance / RESTORATION_RATE_PER_TICK


def _fmt_duration(seconds: float) -> str:
    days  = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    if days > 0:
        return f"≈{days}d {hours}h"
    if hours > 0:
        return f"≈{hours}h"
    return f"≈{int(seconds // 60)}m"


# ── Push notification ──────────────────────────────────────────────────────────
def _fire_push(player_id: int, title: str, body: str):
    def _send():
        try:
            from push_ux import send_push_notification
            send_push_notification(player_id, title, body, "/land",
                                   notif_type="govt",
                                   tag=f"land-restore-{player_id}")
        except Exception as e:
            print(f"[LandRestoration] Push error: {e}")
    threading.Thread(target=_send, daemon=True).start()


# ── Start restoration ──────────────────────────────────────────────────────────
def start_restoration(player_id: int) -> Tuple[bool, str]:
    """
    Validate eligibility, charge the player, pay government, and create the
    restoration record.  Returns (success, message).
    """
    # Cooldown check
    cooldown = get_cooldown_until(player_id)
    if cooldown:
        days_left = int((cooldown - datetime.utcnow()).total_seconds() / 86400) + 1
        return False, f"Restoration is on cooldown — {days_left} more day(s)."

    # Duplicate check
    if get_active_restoration(player_id):
        return False, "A restoration is already in progress."

    # Eligible plots
    plots = get_eligible_plots(player_id)
    if not plots:
        return False, "No eligible plots (efficiency must be below 30%)."

    plot_ids    = [p.id for p in plots]
    plot_starts = {str(p.id): round(p.efficiency, 4) for p in plots}

    # Base cost
    total_cost_usd = sum(calculate_plot_cost_usd(p.efficiency) for p in plots)

    # Executive discount (COO wages effect)
    exec_discount = 0.0
    try:
        from executive import get_player_job_bonus, get_db as exec_db
        _edb = exec_db()
        exec_discount = get_player_job_bonus(_edb, player_id, "wages")
        _edb.close()
    except Exception:
        pass

    # City wage_savings buff
    city_discount = 0.0
    try:
        from city_projects import get_city_production_buffs
        city_discount = get_city_production_buffs(player_id).get("wage_savings", 0.0)
    except Exception:
        pass

    discount       = min(0.40, exec_discount + city_discount)
    total_cost_usd = total_cost_usd * (1.0 - discount)

    # Fund check
    from reserve_banks import can_afford_usd, spend_player_funds, credit_usd, fmt_usd, get_player_display_currency
    if not can_afford_usd(player_id, total_cost_usd):
        disp = get_player_display_currency(player_id)
        return False, f"Insufficient funds — need {fmt_usd(total_cost_usd, disp)}."

    ok, err = spend_player_funds(player_id, total_cost_usd)
    if not ok:
        return False, err

    # Pay government
    credit_usd(GOVERNMENT_PLAYER_ID, total_cost_usd)

    # Transaction log
    try:
        from stats_ux import log_transaction
        log_transaction(
            player_id=player_id,
            transaction_type="land_restoration",
            category="money",
            amount=-total_cost_usd,
            description=f"Land efficiency restoration — {len(plot_ids)} plot(s)",
        )
    except Exception:
        pass

    # Timing
    time_secs      = calculate_total_time_seconds(plots)
    now            = datetime.utcnow()
    completes_at   = now + timedelta(seconds=time_secs)
    cooldown_until = completes_at + timedelta(days=RESTORATION_COOLDOWN_DAYS)

    # Write restoration record + mark plots
    res_db = _db()
    try:
        restoration = LandRestoration(
            player_id        = player_id,
            plot_ids_json    = json.dumps(plot_ids),
            plot_starts_json = json.dumps(plot_starts),
            started_at       = now,
            completes_at     = completes_at,
            cooldown_until   = cooldown_until,
            total_cost_usd   = total_cost_usd,
            status           = "active",
        )
        res_db.add(restoration)
        res_db.flush()

        from land import get_db as land_db_fn, LandPlot
        ldb = land_db_fn()
        ldb.query(LandPlot).filter(LandPlot.id.in_(plot_ids)).update(
            {"is_restoring": True}, synchronize_session=False
        )
        ldb.commit()
        ldb.close()

        res_db.commit()
    except Exception as e:
        res_db.rollback()
        return False, f"Database error: {e}"
    finally:
        res_db.close()

    _fire_push(
        player_id,
        "Efficiency Restoration Started",
        f"{len(plot_ids)} plot(s) being restored — estimated completion {_fmt_duration(time_secs)}.",
    )
    return True, f"Restoration started for {len(plot_ids)} plot(s)."


# ── Tick processing ────────────────────────────────────────────────────────────
def _complete_restoration(restoration: LandRestoration, db, ldb):
    """Mark complete, clear is_restoring flags, notify player."""
    from land import LandPlot
    plot_ids = json.loads(restoration.plot_ids_json)
    ldb.query(LandPlot).filter(LandPlot.id.in_(plot_ids)).update(
        {LandPlot.efficiency: RESTORATION_TARGET,
         LandPlot.is_restoring: False},
        synchronize_session=False,
    )
    ldb.commit()
    restoration.status = "complete"
    db.flush()

    _fire_push(
        restoration.player_id,
        "Efficiency Restoration Complete ✓",
        f"{len(plot_ids)} plot(s) restored to 150%. "
        f"{RESTORATION_COOLDOWN_DAYS}-day cooldown begins now.",
    )

    # In-app notification
    try:
        from push_ux import send_push_notification
        from auth import get_db as auth_db_fn
        adb = auth_db_fn()
        try:
            from auth import Player
            p = adb.query(Player).filter(Player.id == restoration.player_id).first()
            notif_enabled = getattr(p, "notif_push_tasks_events", True) if p else True
        finally:
            adb.close()
        if notif_enabled:
            pass  # already sent via _fire_push above
    except Exception:
        pass


def process_tick():
    """Apply restoration gain to all active jobs; complete any that are done."""
    db = _db()
    try:
        active = db.query(LandRestoration).filter(
            LandRestoration.status == "active"
        ).all()
        if not active:
            return

        from land import get_db as land_db_fn, LandPlot
        ldb = land_db_fn()
        try:
            now = datetime.utcnow()
            for restoration in active:
                plot_ids = json.loads(restoration.plot_ids_json)

                # Increase efficiency, cap at RESTORATION_TARGET
                ldb.query(LandPlot).filter(
                    LandPlot.id.in_(plot_ids),
                    LandPlot.efficiency < RESTORATION_TARGET,
                ).update(
                    {LandPlot.efficiency: func.least(
                        RESTORATION_TARGET,
                        LandPlot.efficiency + RESTORATION_RATE_PER_TICK,
                    )},
                    synchronize_session=False,
                )

                if now >= restoration.completes_at:
                    _complete_restoration(restoration, db, ldb)

            ldb.commit()
            db.commit()
        finally:
            ldb.close()
    finally:
        db.close()


def tick(current_tick: int, now: datetime):
    """Module tick entry point."""
    try:
        process_tick()
    except Exception as e:
        print(f"[LandRestoration] tick error: {e}")


# ── UI renderer ────────────────────────────────────────────────────────────────
_CARD = (
    "background:#0f172a;border:1px solid #1e293b;border-radius:8px;"
    "padding:16px;margin:0 0 18px;"
)


def get_restoration_module_html(player, disp: str) -> str:
    """Render the Efficiency Restoration card for the /land dashboard."""
    from reserve_banks import fmt_usd

    active   = get_active_restoration(player.id)
    cooldown = get_cooldown_until(player.id) if not active else None

    # ── ACTIVE ────────────────────────────────────────────────────────────────
    if active:
        now       = datetime.utcnow()
        total_s   = max(1.0, (active.completes_at - active.started_at).total_seconds())
        elapsed_s = (now - active.started_at).total_seconds()
        progress  = min(100.0, elapsed_s / total_s * 100)
        remaining = max(0.0, (active.completes_at - now).total_seconds())
        rem_str   = _fmt_duration(remaining)

        plot_ids    = json.loads(active.plot_ids_json)
        plot_starts = json.loads(active.plot_starts_json)

        from land import get_db as land_db_fn, LandPlot
        ldb = land_db_fn()
        try:
            plots = ldb.query(LandPlot).filter(LandPlot.id.in_(plot_ids)).all()
        finally:
            ldb.close()

        rows = ""
        for p in plots:
            start_eff = plot_starts.get(str(p.id), 0.0)
            done      = p.efficiency >= RESTORATION_TARGET - 0.05
            badge     = ('<span style="color:#4ade80;font-size:0.7rem;">✓ Done</span>'
                         if done else
                         '<span style="color:#38bdf8;font-size:0.7rem;">Restoring…</span>')
            rows += f"""<div style="display:flex;justify-content:space-between;align-items:center;
              padding:6px 0;border-bottom:1px solid #1e293b;font-size:0.8rem;">
  <span style="color:#94a3b8;">
    Plot #{p.id} · {(p.terrain_type or 'Plot').replace('_',' ').title()}
  </span>
  <span style="color:#e5e7eb;">
    {start_eff:.1f}% → {min(p.efficiency, RESTORATION_TARGET):.1f}% {badge}
  </span>
</div>"""

        bar = int(progress)
        return f"""<div style="{_CARD}">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
    <span style="font-weight:700;color:#38bdf8;font-size:0.92rem;">⚙ EFFICIENCY RESTORATION</span>
    <span style="background:#1e3a5f;color:#38bdf8;font-size:0.72rem;
                 padding:3px 8px;border-radius:4px;font-weight:600;">IN PROGRESS</span>
  </div>
  <div style="background:#1e293b;border-radius:4px;height:10px;margin-bottom:6px;overflow:hidden;">
    <div style="height:100%;width:{bar}%;background:linear-gradient(90deg,#3b82f6,#38bdf8);
                border-radius:4px;"></div>
  </div>
  <div style="display:flex;justify-content:space-between;margin-bottom:12px;">
    <span style="font-size:0.75rem;color:#64748b;">{progress:.1f}% complete</span>
    <span style="font-size:0.75rem;color:#94a3b8;">Done in {rem_str}</span>
  </div>
  {rows}
  <div style="margin-top:10px;font-size:0.72rem;color:#475569;">
    Cost paid: {fmt_usd(active.total_cost_usd, disp)} ·
    {RESTORATION_COOLDOWN_DAYS}-day cooldown starts on completion.
  </div>
</div>"""

    # ── COOLDOWN ──────────────────────────────────────────────────────────────
    if cooldown:
        days_left     = max(0, int((cooldown - datetime.utcnow()).total_seconds() / 86400))
        available_str = cooldown.strftime("%b %d, %Y")
        return f"""<div style="{_CARD}">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
    <span style="font-weight:700;color:#94a3b8;font-size:0.92rem;">⚙ EFFICIENCY RESTORATION</span>
    <span style="background:#1a1a2e;color:#64748b;font-size:0.72rem;
                 padding:3px 8px;border-radius:4px;font-weight:600;">COOLDOWN</span>
  </div>
  <div style="font-size:0.82rem;color:#64748b;">
    Next restoration available <strong style="color:#94a3b8;">{available_str}</strong>
    ({days_left} day(s) remaining).
  </div>
</div>"""

    # ── ELIGIBLE PLOTS ────────────────────────────────────────────────────────
    plots = get_eligible_plots(player.id)
    if not plots:
        return ""

    # Discounts
    exec_discount = 0.0
    city_discount = 0.0
    try:
        from executive import get_player_job_bonus, get_db as exec_db
        _edb = exec_db()
        exec_discount = get_player_job_bonus(_edb, player.id, "wages")
        _edb.close()
    except Exception:
        pass
    try:
        from city_projects import get_city_production_buffs
        city_discount = get_city_production_buffs(player.id).get("wage_savings", 0.0)
    except Exception:
        pass
    discount = min(0.40, exec_discount + city_discount)

    plot_rows      = ""
    total_cost_usd = 0.0
    max_time_s     = 0.0
    for p in plots:
        cost_usd = calculate_plot_cost_usd(p.efficiency)
        time_s   = (RESTORATION_TARGET - max(0.0, p.efficiency)) / RESTORATION_RATE_PER_TICK
        total_cost_usd += cost_usd
        if time_s > max_time_s:
            max_time_s = time_s
        wage_mult = 1.0 / max(WAGE_MULT_FLOOR, p.efficiency / 100.0)
        plot_rows += f"""<div style="display:flex;justify-content:space-between;align-items:flex-start;
  padding:8px 0;border-bottom:1px solid #1e293b;">
  <div>
    <div style="color:#e5e7eb;font-size:0.82rem;font-weight:600;">
      Plot #{p.id} · {(p.terrain_type or 'plot').replace('_',' ').title()}
    </div>
    <div style="color:#64748b;font-size:0.72rem;margin-top:2px;">
      Efficiency: <span style="color:#ef4444;">{p.efficiency:.1f}%</span>
      · Wage mult: <span style="color:#ef4444;">{wage_mult:.1f}×</span>
      → Target: <span style="color:#4ade80;">150%</span>
      · ETA: {_fmt_duration(time_s)}
    </div>
  </div>
  <div style="text-align:right;flex-shrink:0;margin-left:12px;">
    <div style="color:#fbbf24;font-size:0.8rem;font-weight:600;">{fmt_usd(cost_usd, disp)}</div>
    <div style="color:#64748b;font-size:0.7rem;">{wage_mult:.1f}× × $1k</div>
  </div>
</div>"""

    total_discounted = total_cost_usd * (1.0 - discount)
    disc_note = ""
    if discount > 0:
        disc_note = f"""<div style="font-size:0.72rem;color:#4ade80;margin-bottom:6px;">
  ✓ {discount * 100:.0f}% discount applied (COO / city buffs):
  <s style="color:#64748b;">{fmt_usd(total_cost_usd, disp)}</s>
  → {fmt_usd(total_discounted, disp)}
</div>"""

    n        = len(plots)
    plural   = "" if n == 1 else "S"
    cost_str = fmt_usd(total_discounted, disp).replace("'", "\\'")
    confirm_msg = f"Start efficiency restoration for {n} plot{plural.lower()}?\\nTotal cost: {cost_str}\\nThis cannot be undone."
    return f"""<div style="{_CARD}">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
    <span style="font-weight:700;color:#f97316;font-size:0.92rem;">⚙ EFFICIENCY RESTORATION</span>
    <span style="background:#431407;color:#f97316;font-size:0.72rem;
                 padding:3px 8px;border-radius:4px;font-weight:600;">
      {n} PLOT{plural} ELIGIBLE
    </span>
  </div>
  <div style="font-size:0.78rem;color:#64748b;margin-bottom:10px;">
    The following plots have fallen below 30% efficiency and can be restored to 150%.
    All plots are restored simultaneously. Wages stay floored at 1× base while above 100%.
  </div>
  {plot_rows}
  <div style="margin-top:12px;padding-top:10px;border-top:1px solid #1e293b;">
    {disc_note}
    <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
      <span style="font-size:0.82rem;color:#94a3b8;">Total cost</span>
      <span style="font-size:0.9rem;font-weight:700;color:#fbbf24;">
        {fmt_usd(total_discounted, disp)}
      </span>
    </div>
    <div style="display:flex;justify-content:space-between;margin-bottom:10px;">
      <span style="font-size:0.82rem;color:#94a3b8;">Est. completion</span>
      <span style="font-size:0.82rem;color:#94a3b8;">{_fmt_duration(max_time_s)}</span>
    </div>
    <div style="font-size:0.72rem;color:#475569;margin-bottom:10px;line-height:1.5;">
      ⚠ Payment is immediate and non-refundable. Restoration cannot be paused, stopped,
      or restarted. One restoration at a time. A {RESTORATION_COOLDOWN_DAYS}-day cooldown
      applies after completion. Cost paid to Federal Government.
    </div>
    <form action="/api/land-restoration/start" method="post">
      <button type="submit"
              onclick="return confirm('{confirm_msg}')"
              style="width:100%;padding:11px;background:#f97316;color:#fff;border:none;
                     border-radius:6px;font-weight:700;font-size:0.88rem;cursor:pointer;
                     letter-spacing:0.03em;">
        Restore {n} Plot{plural} — {fmt_usd(total_discounted, disp)}
      </button>
    </form>
  </div>
</div>"""
