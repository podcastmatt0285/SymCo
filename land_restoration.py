"""
land_restoration.py  —  Land Efficiency Restoration

Rules:
  - Eligible: plots with efficiency < 30% (not tutorial reward, not already restoring)
  - One active restoration per player at a time; cannot pause, stop, or restart
  - All eligible plots restored simultaneously at 500× the standard decay rate
  - Target per plot = that plot's max_efficiency × 1.5
      · First restoration: max 100% → target 150%
      · Second:            max 150% → target 225%
      · Third:             max 225% → target 337.5%  … and so on
  - After completion max_efficiency is updated to the target, giving more headroom per cycle
  - Wages are floored at 1× base even when efficiency exceeds 100% (no wage reduction above normal)
  - Cost = wage_multiplier × $1,000 USD per plot at start (no discounts apply)
  - Payment goes to the Federal Government immediately; logged as land_restoration transaction
  - 60-day cooldown after each restoration completes
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
ELIGIBILITY_THRESHOLD     = 30.0          # plots below this % are eligible
RESTORATION_MULTIPLIER    = 1.5           # target = max_efficiency × 1.5
RESTORATION_COOLDOWN_DAYS = 60
COST_PER_MULT_USD         = 1_000.0       # wage_multiplier × $1 000, no discounts
WAGE_MULT_FLOOR           = 0.005         # matches business.py
EFFICIENCY_DECAY_PER_TICK = 0.00001 / 60  # matches land.py (% per second)
RESTORATION_RATE_PER_TICK = 500 * EFFICIENCY_DECAY_PER_TICK

GOVERNMENT_PLAYER_ID = 0


# ── DB Model ───────────────────────────────────────────────────────────────────
class LandRestoration(Base):
    __tablename__ = "land_restorations"
    id               = Column(Integer, primary_key=True, autoincrement=True)
    player_id        = Column(Integer, nullable=False, index=True)
    plot_ids_json    = Column(String, nullable=False)   # JSON list of int plot IDs
    plot_starts_json = Column(String, nullable=False)   # JSON {str(id): start_eff}
    plot_targets_json= Column(String, nullable=False)   # JSON {str(id): target_eff}
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
    # Ensure land_plots has the columns we need (land.py also does this, belt-and-suspenders)
    try:
        from database import run_ddl_migration
        from land import engine as land_engine
        for ddl in [
            "ALTER TABLE land_plots ADD COLUMN IF NOT EXISTS is_restoring BOOLEAN DEFAULT FALSE",
            "ALTER TABLE land_plots ADD COLUMN IF NOT EXISTS max_efficiency REAL DEFAULT 100.0",
            "ALTER TABLE land_plots ADD COLUMN IF NOT EXISTS restoration_target REAL",
        ]:
            run_ddl_migration(land_engine, ddl)
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
    """LandPlots owned by player with efficiency < 30%, not tutorial reward, not restoring."""
    from land import get_db as land_db_fn, LandPlot
    db = land_db_fn()
    try:
        return db.query(LandPlot).filter(
            LandPlot.owner_id           == player_id,
            LandPlot.efficiency         < ELIGIBILITY_THRESHOLD,
            LandPlot.is_tutorial_reward == False,
            LandPlot.is_restoring       == False,
        ).all()
    finally:
        db.close()


# ── Cost / time helpers ────────────────────────────────────────────────────────
def _plot_target(plot) -> float:
    """Restoration target for this plot = current max_efficiency × 1.5."""
    return getattr(plot, "max_efficiency", 100.0) * RESTORATION_MULTIPLIER


def _plot_cost_usd(plot) -> float:
    """wage_multiplier × $1 000.  No discounts."""
    eff_frac  = max(WAGE_MULT_FLOOR, plot.efficiency / 100.0)
    wage_mult = 1.0 / eff_frac
    return wage_mult * COST_PER_MULT_USD


def _plot_time_seconds(plot) -> float:
    """Seconds to restore this specific plot from its current efficiency to its target."""
    target   = _plot_target(plot)
    distance = target - max(0.0, plot.efficiency)
    return max(0.0, distance / RESTORATION_RATE_PER_TICK)


def _fmt_duration(seconds: float) -> str:
    days  = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    mins  = int((seconds % 3600) // 60)
    if days > 0:
        return f"~{days}d {hours}h"
    if hours > 0:
        return f"~{hours}h {mins}m"
    return f"~{mins}m"


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
    Validate, charge the player, pay government, and begin the restoration job.
    Returns (success, message).
    """
    # Cooldown check
    cooldown = get_cooldown_until(player_id)
    if cooldown:
        days_left = max(1, int((cooldown - datetime.utcnow()).total_seconds() / 86400) + 1)
        return False, f"Restoration is on cooldown — {days_left} more day(s)."

    # Duplicate check
    if get_active_restoration(player_id):
        return False, "A restoration is already in progress."

    # Eligible plots
    plots = get_eligible_plots(player_id)
    if not plots:
        return False, "No eligible plots (efficiency must be below 30%)."

    plot_ids      = [p.id for p in plots]
    plot_starts   = {str(p.id): round(p.efficiency, 4) for p in plots}
    plot_targets  = {str(p.id): round(_plot_target(p), 4) for p in plots}
    total_cost_usd = sum(_plot_cost_usd(p) for p in plots)

    # Fund check
    from reserve_banks import (can_afford_usd, spend_player_funds,
                                credit_usd, fmt_usd, get_player_display_currency)
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

    # Timing — slowest plot drives the completion time
    total_secs     = max(_plot_time_seconds(p) for p in plots)
    now            = datetime.utcnow()
    completes_at   = now + timedelta(seconds=total_secs)
    cooldown_until = completes_at + timedelta(days=RESTORATION_COOLDOWN_DAYS)

    # Write record and mark plots as restoring
    res_db = _db()
    try:
        restoration = LandRestoration(
            player_id         = player_id,
            plot_ids_json     = json.dumps(plot_ids),
            plot_starts_json  = json.dumps(plot_starts),
            plot_targets_json = json.dumps(plot_targets),
            started_at        = now,
            completes_at      = completes_at,
            cooldown_until    = cooldown_until,
            total_cost_usd    = total_cost_usd,
            status            = "active",
        )
        res_db.add(restoration)
        res_db.flush()

        # Mark each plot and set its per-plot target on the LandPlot row
        from land import get_db as land_db_fn, LandPlot
        ldb = land_db_fn()
        try:
            for p in plots:
                target = _plot_target(p)
                ldb.query(LandPlot).filter(LandPlot.id == p.id).update(
                    {"is_restoring": True, "restoration_target": round(target, 4)},
                    synchronize_session=False,
                )
            ldb.commit()
        finally:
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
        f"{len(plot_ids)} plot(s) now restoring — done in {_fmt_duration(total_secs)}.",
    )
    return True, f"Restoration started for {len(plot_ids)} plot(s)."


# ── Tick processing ────────────────────────────────────────────────────────────
def _complete_restoration(restoration: LandRestoration, res_db, ldb):
    """
    Finalise a restoration job:
      - Set each plot's efficiency to its restoration_target
      - Advance max_efficiency to the same value (it grows 1.5× per cycle)
      - Clear restoration_target and is_restoring
      - Mark the record complete and notify the player
    """
    from land import LandPlot
    plot_ids = json.loads(restoration.plot_ids_json)

    # Force each plot to exactly its target, grow max_efficiency, clear flags
    ldb.query(LandPlot).filter(
        LandPlot.id.in_(plot_ids),
        LandPlot.restoration_target != None,
    ).update(
        {
            LandPlot.efficiency:         LandPlot.restoration_target,
            LandPlot.max_efficiency:     LandPlot.restoration_target,
            LandPlot.restoration_target: None,
            LandPlot.is_restoring:       False,
        },
        synchronize_session=False,
    )
    ldb.commit()

    restoration.status = "complete"
    res_db.flush()

    _fire_push(
        restoration.player_id,
        "Efficiency Restoration Complete ✓",
        f"{len(plot_ids)} plot(s) restored. "
        f"{RESTORATION_COOLDOWN_DAYS}-day cooldown starts now.",
    )


def process_tick():
    """Apply restoration gain each tick; complete any jobs whose time has elapsed."""
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

                if now >= restoration.completes_at:
                    # Time up — snap to exact targets and close out
                    _complete_restoration(restoration, db, ldb)
                else:
                    # Increase efficiency, capped per-plot at restoration_target
                    ldb.query(LandPlot).filter(
                        LandPlot.id.in_(plot_ids),
                        LandPlot.restoration_target != None,
                        LandPlot.efficiency < LandPlot.restoration_target,
                    ).update(
                        {LandPlot.efficiency: func.least(
                            LandPlot.restoration_target,
                            LandPlot.efficiency + RESTORATION_RATE_PER_TICK,
                        )},
                        synchronize_session=False,
                    )

            ldb.commit()
            db.commit()
        finally:
            ldb.close()
    finally:
        db.close()


def tick(current_tick: int, now: datetime):
    try:
        process_tick()
    except Exception as e:
        print(f"[LandRestoration] tick error: {e}")


# ── UI renderer ────────────────────────────────────────────────────────────────
_CSS = """
<style>
.lr-card{background:#0a1628;border:1px solid #1e293b;border-radius:10px;
         margin:0 0 20px;overflow:hidden;}
.lr-header{display:flex;justify-content:space-between;align-items:center;
           padding:14px 18px;border-bottom:1px solid #1e293b;}
.lr-title{font-weight:700;font-size:0.95rem;letter-spacing:0.02em;}
.lr-badge{font-size:0.7rem;font-weight:700;padding:4px 10px;border-radius:20px;
          letter-spacing:0.06em;text-transform:uppercase;}
.lr-body{padding:14px 18px;}
.lr-plot-row{padding:10px 0;border-bottom:1px solid #0f1e35;}
.lr-plot-row:last-child{border-bottom:none;}
.lr-plot-name{font-size:0.85rem;font-weight:600;color:#e2e8f0;margin-bottom:4px;}
.lr-plot-meta{font-size:0.75rem;color:#64748b;margin-bottom:6px;}
.lr-bar-track{background:#1e293b;border-radius:6px;height:7px;overflow:hidden;margin-bottom:4px;}
.lr-bar-fill{height:100%;border-radius:6px;transition:width .4s;}
.lr-plot-footer{display:flex;justify-content:space-between;font-size:0.75rem;}
.lr-divider{border:none;border-top:1px solid #1e293b;margin:12px 0;}
.lr-summary-row{display:flex;justify-content:space-between;align-items:baseline;
                margin-bottom:6px;font-size:0.85rem;}
.lr-summary-label{color:#94a3b8;}
.lr-summary-value{font-weight:700;color:#f8fafc;}
.lr-rules{font-size:0.72rem;color:#475569;line-height:1.6;
          background:#060e1a;border:1px solid #1a2540;border-radius:6px;
          padding:10px 12px;margin:10px 0;}
.lr-btn{display:block;width:100%;padding:12px;margin-top:10px;
        border:none;border-radius:8px;font-weight:700;font-size:0.9rem;
        letter-spacing:0.03em;cursor:pointer;text-align:center;}
.lr-progress-wrap{padding:14px 18px 0;}
.lr-progress-bar{background:#1e293b;border-radius:6px;height:12px;overflow:hidden;margin-bottom:8px;}
.lr-progress-fill{height:100%;border-radius:6px;
  background:linear-gradient(90deg,#1d4ed8,#38bdf8,#06b6d4);
  background-size:200% 100%;animation:lr-shimmer 2s linear infinite;}
@keyframes lr-shimmer{0%{background-position:200% 0}100%{background-position:-200% 0}}
.lr-progress-meta{display:flex;justify-content:space-between;
                  font-size:0.78rem;color:#64748b;margin-bottom:14px;}
</style>
"""


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

        plot_ids      = json.loads(active.plot_ids_json)
        plot_starts   = json.loads(active.plot_starts_json)
        plot_targets  = json.loads(active.plot_targets_json)

        from land import get_db as ldb_fn, LandPlot
        ldb = ldb_fn()
        try:
            plots = {str(p.id): p for p in ldb.query(LandPlot).filter(LandPlot.id.in_(plot_ids)).all()}
        finally:
            ldb.close()

        plot_rows = ""
        for pid_int in plot_ids:
            pid     = str(pid_int)
            p       = plots.get(pid)
            if not p:
                continue
            start_e  = plot_starts.get(pid, 0.0)
            target_e = plot_targets.get(pid, 150.0)
            curr_e   = min(p.efficiency, target_e)
            span     = target_e - start_e
            bar_pct  = int(min(100, max(0, (curr_e - start_e) / span * 100))) if span > 0 else 100
            done     = curr_e >= target_e - 0.1
            status   = ('<span style="color:#4ade80;font-weight:600;">✓ Done</span>'
                        if done else
                        '<span style="color:#38bdf8;">Restoring…</span>')
            terrain  = (p.terrain_type or "Plot").replace("_", " ").title()
            plot_rows += f"""<div class="lr-plot-row">
  <div class="lr-plot-name">Plot #{pid_int} &nbsp;·&nbsp; {terrain}</div>
  <div class="lr-plot-meta">
    <span style="color:#ef4444;">{start_e:.1f}%</span> start
    &nbsp;→&nbsp; <span style="color:#38bdf8;">{curr_e:.1f}%</span> now
    &nbsp;→&nbsp; <span style="color:#4ade80;">{target_e:.1f}%</span> target
  </div>
  <div class="lr-bar-track">
    <div class="lr-bar-fill"
         style="width:{bar_pct}%;background:linear-gradient(90deg,#ef4444,#f97316,#22c55e);"></div>
  </div>
  <div class="lr-plot-footer">
    <span style="color:#64748b;font-size:0.72rem;">
      Progress: {bar_pct}%
    </span>
    {status}
  </div>
</div>"""

        bar_w = int(progress)
        compl_str = active.completes_at.strftime("%b %d")
        return f"""{_CSS}<div class="lr-card">
  <div class="lr-header">
    <span class="lr-title" style="color:#38bdf8;">⚙ Efficiency Restoration</span>
    <span class="lr-badge" style="background:#0c2a4a;color:#38bdf8;">In Progress</span>
  </div>
  <div class="lr-progress-wrap">
    <div class="lr-progress-bar">
      <div class="lr-progress-fill" style="width:{bar_w}%;"></div>
    </div>
    <div class="lr-progress-meta">
      <span>{progress:.1f}% complete · cost paid: {fmt_usd(active.total_cost_usd, disp)}</span>
      <span>Done {_fmt_duration(remaining)} · {compl_str}</span>
    </div>
  </div>
  <div class="lr-body">
    {plot_rows}
  </div>
</div>"""

    # ── COOLDOWN ──────────────────────────────────────────────────────────────
    if cooldown:
        days_left     = max(0, int((cooldown - datetime.utcnow()).total_seconds() / 86400))
        available_str = cooldown.strftime("%b %d, %Y")
        return f"""{_CSS}<div class="lr-card">
  <div class="lr-header">
    <span class="lr-title" style="color:#64748b;">⚙ Efficiency Restoration</span>
    <span class="lr-badge" style="background:#0f172a;color:#475569;">Cooldown</span>
  </div>
  <div class="lr-body" style="color:#64748b;font-size:0.85rem;">
    Next restoration available
    <strong style="color:#94a3b8;">{available_str}</strong>
    &nbsp;—&nbsp; {days_left} day(s) remaining.
  </div>
</div>"""

    # ── ELIGIBLE PLOTS ────────────────────────────────────────────────────────
    plots = get_eligible_plots(player.id)
    if not plots:
        return ""

    plot_rows      = ""
    total_cost_usd = 0.0
    max_time_s     = 0.0

    for p in plots:
        cost_usd  = _plot_cost_usd(p)
        target    = _plot_target(p)
        time_s    = _plot_time_seconds(p)
        wage_mult = 1.0 / max(WAGE_MULT_FLOOR, p.efficiency / 100.0)
        curr_max  = getattr(p, "max_efficiency", 100.0)
        total_cost_usd += cost_usd
        if time_s > max_time_s:
            max_time_s = time_s

        # Mini bar: how degraded is this plot (fill = current/eligibility threshold)
        bar_pct = max(0, int(p.efficiency / ELIGIBILITY_THRESHOLD * 100))
        terrain = (p.terrain_type or "Plot").replace("_", " ").title()

        plot_rows += f"""<div class="lr-plot-row">
  <div class="lr-plot-name">
    Plot #{p.id} &nbsp;·&nbsp; {terrain}
  </div>
  <div class="lr-plot-meta">
    Current max: <span style="color:#94a3b8;">{curr_max:.1f}%</span>
    &nbsp;·&nbsp; Wage multiplier: <span style="color:#ef4444;">{wage_mult:.1f}×</span>
  </div>
  <div class="lr-bar-track">
    <div class="lr-bar-fill"
         style="width:{bar_pct}%;background:linear-gradient(90deg,#7f1d1d,#ef4444);"></div>
  </div>
  <div class="lr-plot-footer">
    <span style="color:#64748b;">
      {p.efficiency:.1f}%&nbsp;→&nbsp;<span style="color:#4ade80;">{target:.1f}%</span>
      &nbsp;·&nbsp; new max: <span style="color:#4ade80;">{target:.1f}%</span>
      &nbsp;·&nbsp; {_fmt_duration(time_s)}
    </span>
    <span style="color:#fbbf24;font-weight:700;">{fmt_usd(cost_usd, disp)}</span>
  </div>
</div>"""

    n       = len(plots)
    plural  = "" if n == 1 else "s"
    cost_js = fmt_usd(total_cost_usd, disp).replace("'", "\\'")
    confirm = f"Restore {n} plot{plural} for {cost_js}?\\n\\nThis cannot be undone. One restoration at a time, no pause or stop, 60-day cooldown after completion."

    return f"""{_CSS}<div class="lr-card">
  <div class="lr-header">
    <span class="lr-title" style="color:#f97316;">⚙ Efficiency Restoration</span>
    <span class="lr-badge" style="background:#3b1900;color:#f97316;">
      {n} Plot{plural} Eligible
    </span>
  </div>
  <div class="lr-body">
    <p style="font-size:0.8rem;color:#64748b;margin:0 0 12px;line-height:1.6;">
      The plots below have fallen below <strong style="color:#f8fafc;">30% efficiency</strong>.
      Each is restored to <strong style="color:#4ade80;">1.5× its current maximum</strong> —
      growing the max each time, giving more decay headroom per cycle.
      Wages are floored at 1× base even while efficiency exceeds 100%.
    </p>
    {plot_rows}
    <hr class="lr-divider">
    <div class="lr-summary-row">
      <span class="lr-summary-label">Total cost</span>
      <span class="lr-summary-value" style="color:#fbbf24;font-size:0.95rem;">
        {fmt_usd(total_cost_usd, disp)}
      </span>
    </div>
    <div class="lr-summary-row">
      <span class="lr-summary-label">Est. completion</span>
      <span class="lr-summary-value" style="color:#94a3b8;">{_fmt_duration(max_time_s)}</span>
    </div>
    <div class="lr-rules">
      ⚠&nbsp; Payment is immediate and non-refundable &nbsp;·&nbsp;
      One restoration at a time &nbsp;·&nbsp;
      Cannot be paused, stopped, or restarted &nbsp;·&nbsp;
      {RESTORATION_COOLDOWN_DAYS}-day cooldown after completion &nbsp;·&nbsp;
      Cost paid to Federal Government
    </div>
    <form action="/api/land-restoration/start" method="post">
      <button type="submit" class="lr-btn"
              onclick="return confirm('{confirm}')"
              style="background:#f97316;color:#fff;">
        Restore {n} Plot{plural} &nbsp;—&nbsp; {fmt_usd(total_cost_usd, disp)}
      </button>
    </form>
  </div>
</div>"""
