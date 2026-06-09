"""
special_plots.py

Special Plots — subscriber-only mega-facilities created by land sacrifice.
Currently only one special plot type is implemented: the Mint (precious metal
coin-strike facility).

Fibonacci sacrifice sequence: 5, 8, 13, 21, 34, 55 ...
  - Empty plots ARE allowed (occupied status not required)
  - All sacrificed plots must share the same terrain type
  - Tutorial-reward plots cannot be sacrificed
  - Player must have an active Wadsworth Pro subscription

Each special plot gets a unique terrain key ("special_mint") that only mint
businesses are compatible with.
"""

import threading
from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, String, Float, DateTime, Integer, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from database import engine, SessionLocal
Base = declarative_base()

FIBONACCI_START = [5, 8]
BASE_SACRIFICE_COST = 2_000_000.0   # $2 M for first sacrifice
COST_MULTIPLIER = 1.25              # each subsequent costs 1.25× more
GOVERNMENT_PLAYER_ID = 0

SPECIAL_PLOT_TYPES = {
    "mint": {
        "name": "Precious Metal Mint",
        "description": (
            "A sovereign minting facility that converts precious metals into "
            "physical coinage — real in-game currencies backed by commodity prices."
        ),
        "allowed_terrain": [
            "urban", "prairie", "hills", "mountain", "desert",
            "savanna", "forest", "tundra", "jungle", "island", "coastal",
        ],
        "special_terrain": "special_mint",
        "base_tax": 100_000.0,
        "subscriber_only": True,
    }
}


class SpecialPlot(Base):
    __tablename__ = "special_plots"

    id                      = Column(Integer, primary_key=True, index=True)
    owner_id                = Column(Integer, index=True,  nullable=False)
    special_type            = Column(String,  nullable=False)   # "mint"
    terrain_type            = Column(String,  nullable=False)   # "special_mint"
    size                    = Column(Float,   nullable=False)
    plots_merged            = Column(Integer, nullable=False)
    monthly_tax             = Column(Float,   nullable=False)
    last_tax_payment        = Column(DateTime, default=datetime.utcnow)
    occupied_by_business_id = Column(Integer, nullable=True)
    created_at              = Column(DateTime, default=datetime.utcnow)
    source_plot_ids         = Column(Text,    nullable=True)   # comma-separated


class PlayerSpecialPlotStats(Base):
    """Separate Fibonacci counter — independent of district merges."""
    __tablename__ = "player_special_plot_stats"

    player_id                   = Column(Integer, primary_key=True, index=True)
    total_sacrifices_completed  = Column(Integer, default=0)
    current_sacrifice_cost      = Column(Float,   default=BASE_SACRIFICE_COST)
    last_sacrifice_date         = Column(DateTime, nullable=True)


Base.metadata.create_all(engine)


def get_db():
    db = SessionLocal()
    try:
        return db
    except Exception as e:
        print(f"[SpecialPlots] DB error: {e}")
        db.close()
        raise


def calculate_fibonacci_requirement(sacrifice_count: int) -> int:
    """Return plots required for the nth sacrifice (0-indexed). Sequence: 5,8,13,21,34…"""
    if sacrifice_count == 0:
        return FIBONACCI_START[0]
    if sacrifice_count == 1:
        return FIBONACCI_START[1]
    fib = FIBONACCI_START[:]
    for _ in range(2, sacrifice_count + 1):
        fib.append(fib[-1] + fib[-2])
    return fib[sacrifice_count]


def get_player_sacrifice_stats(player_id: int) -> PlayerSpecialPlotStats:
    db = get_db()
    stats = db.query(PlayerSpecialPlotStats).filter(
        PlayerSpecialPlotStats.player_id == player_id
    ).first()
    if not stats:
        stats = PlayerSpecialPlotStats(
            player_id=player_id,
            total_sacrifices_completed=0,
            current_sacrifice_cost=BASE_SACRIFICE_COST,
        )
        db.add(stats)
        db.commit()
        db.refresh(stats)
    db.close()
    return stats


def get_plots_required(player_id: int) -> int:
    stats = get_player_sacrifice_stats(player_id)
    return calculate_fibonacci_requirement(stats.total_sacrifices_completed)


def get_next_sacrifice_cost(player_id: int) -> float:
    stats = get_player_sacrifice_stats(player_id)
    return stats.current_sacrifice_cost


def get_player_special_plots(player_id: int) -> list:
    db = get_db()
    plots = db.query(SpecialPlot).filter(SpecialPlot.owner_id == player_id).all()
    result = list(plots)
    db.close()
    return result


def get_special_plot(plot_id: int) -> Optional[SpecialPlot]:
    db = get_db()
    sp = db.query(SpecialPlot).filter(SpecialPlot.id == plot_id).first()
    db.close()
    return sp


def occupy_special_plot(plot_id: int, business_id: int) -> bool:
    db = get_db()
    sp = db.query(SpecialPlot).filter(SpecialPlot.id == plot_id).first()
    if not sp:
        db.close()
        return False
    sp.occupied_by_business_id = business_id
    db.commit()
    db.close()
    return True


def vacate_special_plot(plot_id: int) -> bool:
    db = get_db()
    sp = db.query(SpecialPlot).filter(SpecialPlot.id == plot_id).first()
    if not sp:
        db.close()
        return False
    sp.occupied_by_business_id = None
    db.commit()
    db.close()
    return True


def get_mint_business_types() -> dict:
    """Load mint business configs from mint_businesses.json."""
    import json
    try:
        with open("mint_businesses.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print("[SpecialPlots] Warning: mint_businesses.json not found")
        return {}


def create_special_plot(
    player_id: int,
    special_type: str,
    plot_ids: List[int],
) -> tuple:
    """
    Sacrifice land plots to create a special plot.

    Accepts empty plots (no business required), unlike district merges.
    Returns (SpecialPlot, "ok") on success, (None, error_message) on failure.
    """
    from land import LandPlot
    from auth import Player
    from skin_utils import is_pro

    if special_type not in SPECIAL_PLOT_TYPES:
        return None, f"Unknown special plot type: '{special_type}'"

    cfg = SPECIAL_PLOT_TYPES[special_type]

    # ── Subscriber gate ──────────────────────────────────────────────────────
    try:
        from auth import get_db as auth_get_db
        adb = auth_get_db()
        player_obj = adb.query(Player).filter(Player.id == player_id).first()
        adb.close()
        if not player_obj:
            return None, "Player not found"
        if cfg.get("subscriber_only") and not is_pro(player_obj):
            return None, "Wadsworth Pro subscription required to create a special plot."
    except Exception as e:
        return None, f"Auth check failed: {e}"

    # ── Plot count ───────────────────────────────────────────────────────────
    required_count = get_plots_required(player_id)
    if len(plot_ids) != required_count:
        return None, (
            f"Special plot creation requires exactly {required_count} plot"
            f"{'s' if required_count != 1 else ''} "
            f"(you selected {len(plot_ids)})"
        )

    db = get_db()

    # ── Load and validate plots ──────────────────────────────────────────────
    plots = db.query(LandPlot).filter(LandPlot.id.in_(plot_ids)).all()
    if len(plots) != len(plot_ids):
        db.close()
        return None, "One or more plot IDs are invalid"

    for plot in plots:
        if plot.owner_id != player_id:
            db.close()
            return None, f"Plot {plot.id} is not owned by you"
        if getattr(plot, "is_tutorial_reward", False):
            db.close()
            return None, f"Plot {plot.id} is a Tutorial Reward and cannot be sacrificed"

    # Mixed terrain is allowed — every sacrificed plot's terrain just has to be
    # permitted by this institution type. The resulting plot takes the
    # institution's own special terrain regardless of what went into it.
    allowed = cfg["allowed_terrain"]
    bad = sorted({p.terrain_type for p in plots if p.terrain_type not in allowed})
    if bad:
        db.close()
        return None, f"{cfg['name']} cannot be built from {', '.join(bad)} terrain"

    # ── Cost check ───────────────────────────────────────────────────────────
    sacrifice_cost = get_next_sacrifice_cost(player_id)
    from reserve_banks import can_afford_usd, spend_player_funds, get_usd_balance
    get_usd_balance(player_id)
    if not can_afford_usd(player_id, sacrifice_cost):
        db.close()
        return None, f"Insufficient funds — special plot creation costs ${sacrifice_cost:,.0f}"

    ok, err = spend_player_funds(player_id, sacrifice_cost)
    if not ok:
        db.close()
        return None, err

    # From here on the player has been charged. Any failure must REFUND them and
    # close the session, otherwise they lose the sacrifice cost with no plot.
    try:
        # ── Pay government ───────────────────────────────────────────────────
        try:
            from auth import get_db as auth_get_db
            adb2 = auth_get_db()
            try:
                govt = adb2.query(Player).filter(Player.id == GOVERNMENT_PLAYER_ID).first()
                if govt:
                    govt.cash_balance += sacrifice_cost
                adb2.commit()
            finally:
                adb2.close()
        except Exception:
            pass

        try:
            from stats_ux import log_transaction
            log_transaction(player_id, "special_plot_creation", "money", -sacrifice_cost,
                            f"Special plot sacrifice: {cfg['name']}")
        except Exception:
            pass

        # ── Remove businesses from occupied plots ────────────────────────────
        from business import Business, BusinessSale
        for plot in plots:
            if plot.occupied_by_business_id:
                biz = db.query(Business).filter(Business.id == plot.occupied_by_business_id).first()
                if biz:
                    sale = db.query(BusinessSale).filter(BusinessSale.business_id == biz.id).first()
                    if sale:
                        db.delete(sale)
                    db.delete(biz)
                    print(f"[SpecialPlots] Removed business {biz.id} from plot {plot.id}")

        # ── Create special plot ──────────────────────────────────────────────
        total_size = sum(p.size for p in plots)
        sp = SpecialPlot(
            owner_id=player_id,
            special_type=special_type,
            terrain_type=cfg["special_terrain"],
            size=total_size,
            plots_merged=len(plots),
            monthly_tax=cfg["base_tax"] * total_size,
            source_plot_ids=",".join(str(p.id) for p in plots),
        )
        db.add(sp)

        for plot in plots:
            db.delete(plot)

        # ── Update stats ──────────────────────────────────────────────────────
        stats = db.query(PlayerSpecialPlotStats).filter(
            PlayerSpecialPlotStats.player_id == player_id
        ).first()
        if not stats:
            stats = PlayerSpecialPlotStats(player_id=player_id)
            db.add(stats)
        stats.total_sacrifices_completed += 1
        new_n = stats.total_sacrifices_completed
        stats.current_sacrifice_cost = BASE_SACRIFICE_COST * (COST_MULTIPLIER ** new_n)
        stats.last_sacrifice_date = datetime.utcnow()

        db.commit()
        db.refresh(sp)
    except Exception as e:
        db.rollback()
        # Refund the player so they aren't charged for a plot that never existed
        try:
            from reserve_banks import credit_usd
            credit_usd(player_id, sacrifice_cost)
            print(f"[SpecialPlots] Refunded ${sacrifice_cost:,.0f} to player {player_id} after creation failure")
        except Exception as _re:
            print(f"[SpecialPlots] CRITICAL: refund failed for player {player_id}: {_re}")
        return None, f"Special plot creation failed: {e}"
    finally:
        try:
            db.close()
        except Exception:
            pass

    print(f"[SpecialPlots] Player {player_id} created {special_type} plot #{sp.id} "
          f"({len(plots)} plots sacrificed, ${sacrifice_cost:,.0f} paid)")
    return sp, "ok"


def create_mint_business(owner_id: int, special_plot_id: int, business_type: str):
    """
    Place a mint business on a special plot.

    Returns (Business, "ok") on success, (None, error_message) on failure.
    """
    from auth import Player
    from business import Business, BusinessSale

    db = get_db()

    sp = db.query(SpecialPlot).filter(SpecialPlot.id == special_plot_id).first()
    if not sp:
        db.close()
        return None, "Special plot not found"
    if sp.owner_id != owner_id:
        db.close()
        return None, "You don't own this special plot"
    if sp.occupied_by_business_id is not None:
        db.close()
        return None, "This special plot already has a mint"

    mint_types = get_mint_business_types()
    if business_type not in mint_types:
        db.close()
        return None, f"Unknown mint type: '{business_type}'"

    config = mint_types[business_type]
    if "special_mint" not in config.get("allowed_terrain", []):
        db.close()
        return None, "This business type cannot be placed on a special mint plot"

    # Cost check
    base_cost = config.get("startup_cost", 5_000_000.0)
    from reserve_banks import can_afford_usd, spend_player_funds, get_usd_balance
    get_usd_balance(owner_id)
    if not can_afford_usd(owner_id, base_cost):
        db.close()
        return None, f"Insufficient funds — mint costs ${base_cost:,.0f}"

    ok, err = spend_player_funds(owner_id, base_cost)
    if not ok:
        db.close()
        return None, err

    # Player has been charged — any failure below must refund + close the session.
    try:
        # Route mint startup fee to the federal government (same as district businesses)
        try:
            from reserve_banks import GOVERNMENT_PLAYER_ID as _GOV_ID, credit_usd as _credit_usd
            _credit_usd(_GOV_ID, base_cost)
            from govt_ledger import log_gov_event as _lge
            _lge("special_plot_startup_fee", "in", base_cost, "USD",
                 counterparty=str(owner_id),
                 description=f"Mint construction: {business_type}")
        except Exception as _gfe:
            print(f"[SpecialPlots] Gov mint fee routing error (non-fatal): {_gfe}")

        try:
            from stats_ux import log_transaction
            log_transaction(owner_id, "business_purchase", "money", -base_cost,
                            f"Mint construction: {config['name']}")
        except Exception:
            pass

        from business import Business
        biz = Business(
            owner_id=owner_id,
            land_plot_id=None,
            district_id=None,
            special_plot_id=special_plot_id,
            business_type=business_type,
            is_active=True,
            progress_ticks=0,
        )
        db.add(biz)
        db.flush()

        sp.occupied_by_business_id = biz.id
        db.commit()
        db.refresh(biz)
    except Exception as e:
        db.rollback()
        try:
            from reserve_banks import credit_usd
            credit_usd(owner_id, base_cost)
            print(f"[SpecialPlots] Refunded ${base_cost:,.0f} to player {owner_id} after mint-build failure")
        except Exception as _re:
            print(f"[SpecialPlots] CRITICAL: mint refund failed for player {owner_id}: {_re}")
        return None, f"Mint construction failed: {e}"
    finally:
        try:
            db.close()
        except Exception:
            pass

    _fire_special_push(
        owner_id,
        "Mint Constructed",
        f"Your {config['name']} is online and will mint {config.get('coin_currency', 'coinage')} each production cycle.",
    )
    return biz, "ok"


# ==========================
# PUSH NOTIFICATIONS
# ==========================
def _fire_special_push(player_id: int, title: str, body: str):
    """Fire a special-plots push notification in a background thread."""
    if player_id <= 0:
        return
    def _send():
        try:
            from push_ux import send_push_notification
            send_push_notification(player_id, title, body, url="/special-plots",
                                   notif_type="business",
                                   tag=f"special-{player_id}-{title[:20]}")
        except Exception as e:
            print(f"[SpecialPlots] Push error: {e}")
    threading.Thread(target=_send, daemon=True).start()


# ==========================
# TAX COLLECTION
# ==========================
def collect_special_plot_taxes(current_month: int):
    """Collect monthly taxes from all special plots → federal government.

    Mirrors districts.collect_district_taxes(): joins plots with owners, applies
    the executive 'districts'/'taxes' job bonuses, debits via spend_player_funds,
    credits the government, and logs each charge.
    """
    from auth import Player

    db = get_db()
    try:
        plot_owner_pairs = db.query(SpecialPlot, Player).join(
            Player, SpecialPlot.owner_id == Player.id
        ).all()
        government = db.query(Player).filter(Player.id == GOVERNMENT_PLAYER_ID).first()

        from reserve_banks import can_afford_usd, spend_player_funds
        total = 0.0
        for sp, owner in plot_owner_pairs:
            effective_tax = sp.monthly_tax
            try:
                from executive import get_player_job_bonus
                _d = get_player_job_bonus(db, owner.id, "districts")
                _t = get_player_job_bonus(db, owner.id, "taxes")
                _reduction = min(_d + _t, 0.95)
                if _reduction > 0:
                    effective_tax = round(effective_tax * (1.0 - _reduction), 2)
            except Exception:
                pass

            if can_afford_usd(owner.id, effective_tax):
                ok, _e = spend_player_funds(owner.id, effective_tax)
                if not ok:
                    continue
                if government:
                    government.cash_balance += effective_tax
                total += effective_tax
                sp.last_tax_payment = datetime.utcnow()
                try:
                    from stats_ux import log_transaction
                    log_transaction(owner.id, "special_plot_tax", "money", -effective_tax,
                                    f"Special plot tax: {sp.special_type}",
                                    reference_id=f"special_{sp.id}")
                except Exception:
                    pass
                try:
                    from govt_ledger import log_gov_event
                    log_gov_event("special_plot_tax", "in", effective_tax, "USD",
                                  counterparty=str(owner.id),
                                  description=f"Special plot tax: {sp.special_type}")
                except Exception:
                    pass
                _fire_special_push(
                    owner.id, "Institution Tax Collected",
                    f"${effective_tax:,.0f} monthly tax charged for your {sp.special_type.title()} institution",
                )
            else:
                _fire_special_push(
                    owner.id, "Institution Tax Payment Failed",
                    f"Insufficient funds for ${effective_tax:,.0f} institution tax — fund your account to avoid penalties",
                )
        db.commit()
        print(f"[SpecialPlots] Monthly special-plot tax collection: ${total:,.2f}")
    except Exception as e:
        db.rollback()
        print(f"[SpecialPlots] Tax collection error: {e}")
    finally:
        db.close()


# ==========================
# MODULE LIFECYCLE
# ==========================
def initialize():
    """Initialize the special plots module (create tables, run migrations)."""
    print("[SpecialPlots] Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("[SpecialPlots] Module initialized")


def tick(current_tick: int, now: datetime):
    """Tick handler — collects monthly special-plot taxes on month change."""
    if 'last_sp_tax_month' not in globals():
        globals()['last_sp_tax_month'] = now.month
    current_month = now.month
    if current_month != globals()['last_sp_tax_month']:
        print(f"[SpecialPlots] Month changed: {globals()['last_sp_tax_month']} -> {current_month}")
        collect_special_plot_taxes(current_month)
        globals()['last_sp_tax_month'] = current_month
