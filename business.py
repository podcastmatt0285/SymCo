# business.py (Full Version with Dismantling System and Retail Pricing Patch)
import json
import random
import threading
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Float
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from stats_ux import log_transaction
# Integrated Algebraic Engine
from supplydemand import SupplyDemandEngine

from database import engine, SessionLocal
Base = declarative_base()

# ── Business push-notification helpers ────────────────────────────────────────
_BIZ_PUSH_COOLDOWN = 21600         # notify at most once per 6 hours per issue

def _fire_business_push(player_id: int, biz_id: int, issue_key: str,
                         title: str, body: str) -> None:
    """Send a push notification for a business issue, rate-limited to once per 6 hours.
    Rate limit is persisted in DB so it survives server restarts."""
    from push_ux import push_rate_ok, push_rate_mark
    db_key = f"biz-{biz_id}-{issue_key}"
    if not push_rate_ok(db_key, _BIZ_PUSH_COOLDOWN):
        return
    push_rate_mark(db_key)
    def _send():
        try:
            from push_ux import send_push_notification
            send_push_notification(
                player_id, title, body,
                url="/businesses",
                notif_type="business",
                tag=f"biz-{biz_id}-{issue_key}",
            )
        except Exception as e:
            print(f"[Business] Push error for player {player_id}: {e}")
    threading.Thread(target=_send, daemon=True).start()

def _fmt_item(item: str) -> str:
    """'raw_leather' → 'Raw Leather'"""
    return item.replace("_", " ").title()

# ==========================
# DATABASE MODELS
# ==========================

class Business(Base):
    __tablename__ = "businesses"
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, index=True, nullable=False)
    land_plot_id = Column(Integer, unique=True, nullable=True)
    business_type = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    progress_ticks = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    district_id = Column(Integer, nullable=True)  # District ID if business is on a district
    # Per-line pause: JSON arrays of paused line indices / product keys
    paused_lines = Column(String, default="[]")      # e.g. "[0, 2]"
    paused_products = Column(String, default="[]")   # e.g. '["bread", "milk"]'
    is_tutorial_reward = Column(Boolean, default=False)  # True → permanently wage-free

class RetailPrice(Base):
    __tablename__ = "retail_prices"
    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, index=True, nullable=False)
    item_type = Column(String, index=True, nullable=False)
    price = Column(Float, nullable=False)

class BusinessSale(Base):
    """Tracks businesses being dismantled over time."""
    __tablename__ = "business_sales"
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, index=True, nullable=False)
    owner_id = Column(Integer, index=True, nullable=False)
    total_refund = Column(Float, nullable=False)
    refund_per_tick = Column(Float, nullable=False)
    ticks_remaining = Column(Integer, nullable=False)
    ticks_total = Column(Integer, nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)

# ==========================
# CONFIG & LIFECYCLE
# ==========================

BUSINESS_TYPES = {}
DISMANTLING_TICKS = 100 # Number of ticks to dismantle a business

def load_business_config():
    global BUSINESS_TYPES
    try:
        with open("business_types.json", "r") as f:
            BUSINESS_TYPES = json.load(f)
    except Exception as e:
        print(f"[Business] Config load error: {e}")

def initialize():
    Base.metadata.create_all(bind=engine)
    # Safe migration: add per-line pause columns if they don't exist yet
    from database import run_ddl_migration
    run_ddl_migration(engine, [
        "ALTER TABLE businesses ADD COLUMN IF NOT EXISTS paused_lines TEXT DEFAULT '[]'",
        "ALTER TABLE businesses ADD COLUMN IF NOT EXISTS paused_products TEXT DEFAULT '[]'",
        "ALTER TABLE businesses ADD COLUMN IF NOT EXISTS is_tutorial_reward BOOLEAN DEFAULT FALSE",
    ])
    load_business_config()
    print("[Business] Module initialized with production patches and dismantling system")

def tick(current_tick: int, now: datetime):
    db = SessionLocal()
    try:
        process_business_tick(db)
        process_dismantling_tick(db)
    finally:
        db.close()

# ==========================
# DISMANTLING SYSTEM
# ==========================

def process_dismantling_tick(db):
    """Process one tick of all ongoing business dismantling sales."""
    from auth import Player
    from land import LandPlot
    active_sales = db.query(BusinessSale).all()
    for sale in active_sales:
        if sale.ticks_remaining <= 0:
            continue
        
        # Pay the owner this tick's refund, auto-converting to their legal tender.
        player = db.query(Player).filter(Player.id == sale.owner_id).first()
        if player:
            try:
                from reserve_banks import convert_to_legal_tender
                convert_to_legal_tender(player.id, sale.refund_per_tick)
            except Exception:
                from reserve_banks import credit_usd
                credit_usd(player.id, sale.refund_per_tick)
            sale.ticks_remaining -= 1
        
        # If dismantling is complete
        if sale.ticks_remaining <= 0:
            # Delete the business
            biz = db.query(Business).filter(Business.id == sale.business_id).first()
            if biz:
                # Notify owner before deleting
                try:
                    if biz.district_id or getattr(biz, 'is_tutorial_reward', False):
                        _cfg = get_district_business_types().get(biz.business_type, {})
                    else:
                        _cfg = BUSINESS_TYPES.get(biz.business_type, {})
                    _biz_name = _cfg.get("name", biz.business_type)
                    _fire_business_push(sale.owner_id, biz.id, "dismantled",
                        _biz_name, f"Dismantling complete — full refund of ${sale.total_refund:,.0f} has been paid")
                except Exception:
                    pass
                # Free up the land
                plot = db.query(LandPlot).filter(LandPlot.id == biz.land_plot_id).first()
                if plot:
                    plot.occupied_by_business_id = None
                db.delete(biz)
                print(f"[Business] Dismantling complete for business {sale.business_id}")
            
            # Delete the sale record
            db.delete(sale)
    db.commit()

def start_business_dismantling(player_id: int, business_id: int) -> bool:
    """
    Begin dismantling a business.
    Returns 50% of startup cost paid over DISMANTLING_TICKS.
    """
    db = SessionLocal()
    try:
        from auth import Player
        biz = db.query(Business).filter(
            Business.id == business_id,
            Business.owner_id == player_id
        ).first()
        
        if not biz:
            db.close()
            return False
            
        existing_sale = db.query(BusinessSale).filter(
            BusinessSale.business_id == business_id
        ).first()
        if existing_sale:
            db.close()
            return False 

        # Tutorial reward businesses were free — no refund on dismantling
        if getattr(biz, 'is_tutorial_reward', False):
            total_refund = 0.0
        else:
            if biz.district_id:
                config = get_district_business_types().get(biz.business_type, {})
            else:
                config = BUSINESS_TYPES.get(biz.business_type, {})
            base_cost = config.get("startup_cost", 2500.0)
            older_businesses = db.query(Business).filter(
                Business.owner_id == player_id,
                Business.created_at < biz.created_at
            ).count()
            multiplier = max(1, older_businesses)
            total_refund = (base_cost * multiplier) * 0.5
        refund_per_tick = total_refund / DISMANTLING_TICKS
        
        sale = BusinessSale(
            business_id=business_id,
            owner_id=player_id,
            total_refund=total_refund,
            refund_per_tick=refund_per_tick,
            ticks_remaining=DISMANTLING_TICKS,
            ticks_total=DISMANTLING_TICKS
        )
        db.add(sale)
        biz.is_active = False
        db.commit()
        print(f"[Business] Started dismantling business {business_id}, will pay ${total_refund:.2f} over {DISMANTLING_TICKS} ticks")
        db.close()
        return True
    except Exception as e:
        print(f"[Business] Error starting dismantling: {e}")
        db.close()
        return False

def get_dismantling_status(business_id: int):
    """Get dismantling status for a business."""
    db = SessionLocal()
    sale = db.query(BusinessSale).filter(BusinessSale.business_id == business_id).first()
    db.close()
    if not sale:
        return None
    progress_pct = ((sale.ticks_total - sale.ticks_remaining) / sale.ticks_total) * 100
    return {
        "ticks_remaining": sale.ticks_remaining,
        "ticks_total": sale.ticks_total,
        "progress_pct": progress_pct,
        "total_refund": sale.total_refund,
        "refund_per_tick": sale.refund_per_tick,
        "paid_so_far": sale.refund_per_tick * (sale.ticks_total - sale.ticks_remaining)
    }

# ==========================
# CORE SIMULATION LOGIC
# ==========================

# ==========================
# FIXED process_business_tick FUNCTION
# ==========================
# Replace the process_business_tick function in business.py with this corrected version

def process_business_tick(db):
    from inventory import add_item, remove_item, get_player_inventory
    from land import LandPlot
    from auth import Player
    import market
    
    active_biz = db.query(Business).filter(Business.is_active == True).all()
    for biz in active_biz:
        sale = db.query(BusinessSale).filter(BusinessSale.business_id == biz.id).first()
        if sale:
            continue
        
        # Check if this is a district business and load appropriate config.
        # Tutorial-reward businesses live on a land plot (not a District object) but
        # use district business types, so they also load from district_businesses.json.
        if biz.district_id or getattr(biz, 'is_tutorial_reward', False):
            district_business_types = get_district_business_types()
            config = district_business_types.get(biz.business_type, {})
        else:
            config = BUSINESS_TYPES.get(biz.business_type, {})
        
        cycles = config.get("cycles_to_complete", 1)
        # Apply city cycle-speed buff (reduces effective cycles_to_complete)
        try:
            from city_projects import get_city_production_buffs as _gcpb
            _cs_mult = _gcpb(biz.owner_id).get("cycle_speed_multiplier", 1.0)
            cycles = max(1, int(cycles * _cs_mult))
        except Exception:
            pass
        if biz.progress_ticks < cycles:
            biz.progress_ticks += 1

        if biz.progress_ticks < cycles:
            continue
            
        player = db.query(Player).filter(Player.id == biz.owner_id).first()
        
        # FIXED: For district businesses, skip plot lookup
        if biz.district_id:
            # District businesses don't have plots, use default efficiency
            eff_multiplier = 1.0
        else:
            plot = db.query(LandPlot).filter(LandPlot.id == biz.land_plot_id).first()
            if not plot:
                continue
            eff_multiplier = max(0.005, (plot.efficiency / 100.0))
        
        if not player:
            continue
        
        base_wage = config.get("base_wage_cost", 0.0)
        # Tutorial-reward businesses are permanently wage-free
        if getattr(biz, 'is_tutorial_reward', False):
            wage_cost = 0.0
        else:
            wage_cost = base_wage / eff_multiplier

        # Apply city project production buffs (if player is a city member)
        _city_output_mult = 1.0
        _city_wage_mult = 1.0
        _city_input_mult = 1.0
        try:
            from city_projects import get_city_production_buffs
            _city_buffs = get_city_production_buffs(biz.owner_id)
            _city_output_mult = _city_buffs.get("output_multiplier", 1.0)
            _city_wage_mult   = _city_buffs.get("wage_multiplier",   1.0)
            _city_input_mult  = _city_buffs.get("input_multiplier",  1.0)
        except Exception:
            pass

        if wage_cost > 0:
            wage_cost *= _city_wage_mult
            from reserve_banks import can_afford_usd
            if not can_afford_usd(player.id, wage_cost):
                biz_name = config.get("name", biz.business_type)
                _fire_business_push(player.id, biz.id, "wages",
                    biz_name, f"Can't afford wages — ${wage_cost:,.0f} needed to keep running")
                continue

        player_inv = get_player_inventory(player.id)
        lines_successfully_produced = 0
        total_revenue = 0.0
        has_retail = bool(config.get("products"))
        production_lines = config.get("production_lines", [])

        # Load per-line pause sets
        paused_line_idxs = set(json.loads(biz.paused_lines or "[]"))
        paused_product_keys = set(json.loads(biz.paused_products or "[]"))

        # ===== RETAIL PROCESSING =====
        if has_retail:
            for item, rule in config.get("products", {}).items():
                if item in paused_product_keys:
                    continue
                qty = player_inv.get(item, 0)
                if qty <= 0:
                    biz_name = config.get("name", biz.business_type)
                    _fire_business_push(player.id, biz.id, f"stock-{item}",
                        biz_name, f"{_fmt_item(item)} is out of stock — restock to keep selling")
                    continue

                price_entry = db.query(RetailPrice).filter(
                    RetailPrice.player_id == player.id,
                    RetailPrice.item_type == item
                ).first()

                mkt_p = market.get_market_price(item) or 10.0
                current_p = price_entry.price if price_entry else mkt_p

                try:
                    multiplier = SupplyDemandEngine.get_sales_multiplier(
                        current_p, mkt_p, rule.get("elasticity", 1.0)
                    )
                    chance = SupplyDemandEngine.calculate_chance_per_tick(
                        rule.get("base_sale_chance", 0.05), multiplier
                    )
                except (ValueError, ZeroDivisionError) as e:
                    print(f"[Business] Skipping retail item {item} for biz {biz.id}: {e}")
                    continue

                sold = sum(1 for _ in range(int(qty)) if random.random() < chance)
                if sold > 0:
                    remove_item(player.id, item, sold)
                    total_revenue += sold * current_p
                    lines_successfully_produced += 1

        # ===== PRODUCTION PROCESSING =====
        for line_idx, line in enumerate(production_lines):
            if line_idx in paused_line_idxs:
                continue
            line_can_run = True
            # Apply city project input multiplier (reduces qty needed).
            # round() is used instead of int() so that savings apply correctly
            # to larger quantities (e.g. 4.9 → 5 not 4).  Quantities of exactly
            # 1 are unaffected by savings below 50% — a known integer-rounding
            # limitation of discrete inventory items.
            effective_inputs = [
                {**req, "quantity": max(1, round(req["quantity"] * _city_input_mult))}
                for req in line.get("inputs", [])
            ]
            for req in effective_inputs:
                if player_inv.get(req["item"], 0) < req["quantity"]:
                    line_can_run = False
                    biz_name = config.get("name", biz.business_type)
                    _fire_business_push(player.id, biz.id, f"input-{req['item']}",
                        biz_name,
                        f"Out of {_fmt_item(req['item'])} — need {req['quantity']} to produce")
                    break

            if line_can_run:
                for req in effective_inputs:
                    remove_item(player.id, req["item"], req["quantity"])
                    # Log resource consumption
                    log_transaction(
                        biz.owner_id,
                        "resource_use",
                        "resource",
                        -req["quantity"],  # negative because consumed
                        f"Used {req['quantity']} {req['item']} in production",
                        str(biz.id)
                    )
                    player_inv[req["item"]] -= req["quantity"]
                    # Reduce WMA qty_basis for consumed inputs
                    try:
                        from wma import consume_wma
                        consume_wma(player.id, req["item"], req["quantity"])
                    except Exception:
                        pass
                # Apply city project output multiplier
                effective_output_qty = max(1, round(line["output_qty"] * _city_output_mult))
                add_item(player.id, line["output_item"], effective_output_qty)
                # Update WMA cost basis for the newly produced output
                try:
                    from wma import compute_production_cost_basis, update_wma
                    _cb = compute_production_cost_basis(player.id, config, line)
                    if _cb["unit_cost"] > 0:
                        update_wma(player.id, line["output_item"],
                                   effective_output_qty, _cb["unit_cost"])
                except Exception as _wma_e:
                    print(f"[Business] WMA update error: {_wma_e}")
                # Log resource production
                log_transaction(
                    biz.owner_id,
                    "resource_gain",
                    "resource",
                    effective_output_qty,
                    f"Produced {effective_output_qty} {line['output_item']}",
                    str(biz.id)
                )
                lines_successfully_produced += 1

        # ===== FINALIZE: pay wages once, reset progress, commit =====
        # Retail always finalizes (wages due even with no sales).
        # Pure-production only finalizes when something was produced.
        should_finalize = has_retail or lines_successfully_produced > 0
        if should_finalize:
            # Pay city production subsidy on any production that ran
            if production_lines and lines_successfully_produced > 0:
                try:
                    from cities import pay_production_subsidy
                    production_cost = 0.0
                    for line in production_lines:
                        for req in line.get("inputs", []):
                            item_price = market.get_market_price(req["item"]) or 1.0
                            production_cost += item_price * req["quantity"]

                    subsidy = pay_production_subsidy(player.id, biz.id, production_cost)
                    if subsidy > 0:
                        print(f"[Business] City subsidy: ${subsidy:.2f} to player {player.id}")
                        total_revenue += subsidy
                except ImportError:
                    pass
                except Exception as e:
                    print(f"[Business] Subsidy error: {e}")

            # Apply executive sales bonus to retail revenue
            if has_retail and total_revenue > 0:
                try:
                    from executive import get_player_job_bonus as _exec_gjb
                    _sales_bonus = _exec_gjb(db, player.id, "sales")
                    if _sales_bonus > 0:
                        total_revenue = round(total_revenue * (1.0 + _sales_bonus), 2)
                except Exception:
                    pass

            net_revenue = total_revenue - wage_cost

            # ── Profit siphon: divert a % into the company's dividend escrow ──
            siphon_amount = 0.0
            try:
                from banks.brokerage_firm import SessionLocal as _BrokDB, CompanyShares as _CS
                _bdb = _BrokDB()
                try:
                    _cs = _bdb.query(_CS).filter(
                        _CS.founder_id == player.id,
                        _CS.is_delisted == False,
                        _CS.profit_siphon_rate > 0,
                        _CS.share_class_label == "main",
                    ).first()
                    if _cs and _cs.profit_siphon_rate and net_revenue > 0:
                        siphon_amount = net_revenue * _cs.profit_siphon_rate
                        _cs.dividend_escrow_balance = (_cs.dividend_escrow_balance or 0.0) + siphon_amount
                        _cs.revenue_7d  = (_cs.revenue_7d  or 0.0) + net_revenue
                        _cs.revenue_30d = (_cs.revenue_30d or 0.0) + net_revenue
                        _bdb.commit()
                    elif _cs:
                        _cs.revenue_7d  = (_cs.revenue_7d  or 0.0) + net_revenue
                        _cs.revenue_30d = (_cs.revenue_30d or 0.0) + net_revenue
                        _bdb.commit()
                finally:
                    _bdb.close()
            except Exception:
                pass

            founder_credit = net_revenue - siphon_amount
            # Route income through the reserve bank so JPY (and other legal-
            # tender) players receive their earnings in their chosen currency.
            try:
                from reserve_banks import convert_to_legal_tender
                convert_to_legal_tender(player.id, founder_credit)
            except Exception:
                from reserve_banks import credit_usd
                credit_usd(player.id, founder_credit)
            biz.progress_ticks = 0
            db.commit()
            if net_revenue > 0:
                log_transaction(
                    biz.owner_id,
                    "retail_sale",
                    "money",
                    founder_credit,
                    f"Retail revenue: {biz.business_type}",
                    str(biz.id)
                )

def create_business(player_id: int, plot_id: int, business_type_key: str):
    """Create a business on a vacant land plot owned by the player."""
    from land import LandPlot
    from auth import Player
    if business_type_key not in BUSINESS_TYPES:
        print(f"[Business] Unknown business type: {business_type_key}")
        return None
        
    config = BUSINESS_TYPES[business_type_key]
    db = SessionLocal()
    try:
        plot = db.query(LandPlot).filter(LandPlot.id == plot_id).first()
        if not plot or plot.owner_id != player_id or plot.occupied_by_business_id is not None:
            print("[Business] Invalid plot, ownership, or occupancy.")
            db.close()
            return None

        # Block building on a plot that is currently listed for sale
        from land_market import LandListing
        active_listing = db.query(LandListing).filter(
            LandListing.land_plot_id == plot_id,
            LandListing.is_active == True,
        ).first()
        if active_listing:
            print(f"[Business] Plot {plot_id} is listed for sale — cancel the listing before building.")
            db.close()
            return None
            
        allowed = config.get("allowed_terrain")
        if allowed and plot.terrain_type not in allowed:
            print(f"[Business] Terrain {plot.terrain_type} not allowed.")
            db.close()
            return None
            
        player = db.query(Player).filter(Player.id == player_id).first()
        if not player:
            db.close()
            return None
        
        base_cost = config.get("startup_cost", 2500.0)
        owned_businesses = db.query(Business).filter(Business.owner_id == player_id).count()
        
        # FIXED: Proper progressive cost increase
        # 0 businesses = 1.0x base cost
        # 1 business = 1.25x base cost
        # 2 businesses = 1.5x base cost
        # 3 businesses = 1.75x base cost, etc.
        multiplier = 1.0 + (owned_businesses * 0.25)
        startup_cost = base_cost * multiplier
        
        print(f"[Business] Startup cost for {business_type_key}: ${base_cost:.2f} × {multiplier:.2f} = ${startup_cost:,.2f}")
        
        from reserve_banks import spend_player_funds
        ok, _err = spend_player_funds(player_id, startup_cost)
        if not ok:
            print(f"[Business] Player {player_id} insufficient funds for startup: {_err}")
            db.close()
            return None
        business = Business(
            owner_id=player_id,
            land_plot_id=plot.id,
            business_type=business_type_key,
            progress_ticks=0,
            is_active=True
        )
        db.add(business)
        db.commit()
        db.refresh(business)
        plot.occupied_by_business_id = business.id
        db.commit()
        
        print(f"[Business] Created {business_type_key} on plot {plot.id} for Player {player_id} (cost: ${startup_cost:,.2f})")
        log_transaction(player_id, "business_startup", "money", -startup_cost,
                        f"Business created: {config.get('name', business_type_key)}",
                        reference_id=str(business.id))
        return business
    except Exception as e:
        print(f"[Business] Error creating business: {e}")
        import traceback
        traceback.print_exc()
        db.close()
        return None
    finally:
        db.close()

def toggle_business(player_id: int, business_id: int) -> bool:
    """Toggle a business between active and paused."""
    db = SessionLocal()
    try:
        biz = db.query(Business).filter(Business.id == business_id, Business.owner_id == player_id).first()
        if not biz:
            db.close()
            return False
        sale = db.query(BusinessSale).filter(BusinessSale.business_id == business_id).first()
        if sale:
            db.close()
            return False
        biz.is_active = not biz.is_active
        db.commit()
        db.close()
        return True
    except Exception as e:
        print(f"[Business] Error toggling business: {e}")
        db.close()
        return False


def toggle_production_line(player_id: int, business_id: int, line_index: int) -> dict:
    """Toggle pause/resume on a single production line by index."""
    db = SessionLocal()
    try:
        biz = db.query(Business).filter(Business.id == business_id, Business.owner_id == player_id).first()
        if not biz:
            return {"ok": False, "error": "Business not found"}
        paused = json.loads(biz.paused_lines or "[]")
        if line_index in paused:
            paused.remove(line_index)
            now_paused = False
        else:
            paused.append(line_index)
            now_paused = True
        biz.paused_lines = json.dumps(paused)
        db.commit()
        return {"ok": True, "paused": now_paused}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        db.close()


def toggle_retail_item(player_id: int, business_id: int, item_type: str) -> dict:
    """Toggle pause/resume on a single retail product."""
    db = SessionLocal()
    try:
        biz = db.query(Business).filter(Business.id == business_id, Business.owner_id == player_id).first()
        if not biz:
            return {"ok": False, "error": "Business not found"}
        paused = json.loads(biz.paused_products or "[]")
        if item_type in paused:
            paused.remove(item_type)
            now_paused = False
        else:
            paused.append(item_type)
            now_paused = True
        biz.paused_products = json.dumps(paused)
        db.commit()
        return {"ok": True, "paused": now_paused}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        db.close()


# ==========================
# RETAIL PRICING PATCH
# ==========================

def set_retail_price(player_id: int, item_type: str, price: float) -> bool:
    """Set or update the retail price for a specific item for a player."""
    if price <= 0:
        print(f"[Business] Rejected invalid retail price {price} for player {player_id} ({item_type})")
        return False
    db = SessionLocal()
    try:
        price_entry = db.query(RetailPrice).filter(
            RetailPrice.player_id == player_id,
            RetailPrice.item_type == item_type
        ).first()

        if price_entry:
            price_entry.price = price
        else:
            new_price = RetailPrice(
                player_id=player_id,
                item_type=item_type,
                price=price
            )
            db.add(new_price)
        
        db.commit()
        print(f"[Business] Player {player_id} set retail price for {item_type} to ${price:.2f}")
        return True
    except Exception as e:
        print(f"[Business] Error setting retail price: {e}")
        return False
    finally:
        db.close()

# =========================
# Districts
# =========================

def get_district_business_types():
    """Load district business types from district_businesses.json"""
    try:
        with open('district_businesses.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("[Business] Warning: district_businesses.json not found")
        return {}

# ==========================
# FIXED create_district_business FUNCTION
# ==========================
# Replace the create_district_business function in business.py with this corrected version

def create_district_business(owner_id: int, district_id: int, business_type: str):
    """
    Create a business on a district.
    Similar to create_business() but for districts instead of land plots.
    
    Args:
        owner_id: Player ID who owns the district
        district_id: District ID to build on
        business_type: Type of district business to create
    
    Returns:
        (Business instance or None, error message)
    """
    from districts import get_district, occupy_district
    from auth import Player
    
    db = SessionLocal()  # FIXED: Use SessionLocal() not get_db()
    
    try:
        # Verify district exists and is owned by player
        district = get_district(district_id)
        if not district:
            return None, "District not found"
        
        if district.owner_id != owner_id:
            return None, "You don't own this district"
        
        if district.occupied_by_business_id is not None:
            return None, "District already has a business"
        
        # Load district business types
        district_business_types = get_district_business_types()
        
        if business_type not in district_business_types:
            return None, f"Invalid district business type: {business_type}"
        
        config = district_business_types[business_type]
        
        # Verify terrain compatibility
        district_terrain_key = f"district_{district.district_type}"
        if district_terrain_key not in config.get("allowed_terrain", []):
            return None, f"This business cannot be built on a {district.district_type} district"
        
        # Calculate cost with multiplier
        base_cost = config.get("startup_cost", 2500.0)
        owned_businesses = db.query(Business).filter(Business.owner_id == owner_id).count()
        
        # FIXED: Use same multiplier formula as create_business
        multiplier = 1.0 + (owned_businesses * 0.25)
        total_cost = base_cost * multiplier
        
        # Check player has enough money
        player = db.query(Player).filter(Player.id == owner_id).first()
        if not player:
            return None, "Player not found"
        
        from reserve_banks import spend_player_funds
        ok, err = spend_player_funds(owner_id, total_cost)
        if not ok:
            return None, err

        # Create business
        business = Business(
            owner_id=owner_id,
            business_type=business_type,
            district_id=district_id,  # District businesses use this
            land_plot_id=None,  # No land plot for district businesses (REQUIRES nullable column)
            progress_ticks=0,
            is_active=True
        )
        
        db.add(business)
        db.commit()
        db.refresh(business)
        
        # Occupy the district
        occupy_district(district_id, business.id)
        
        print(f"[Business] Created district business {business.id} ({business_type}) for player {owner_id} on district {district_id}")
        return business, "Success"
        
    except Exception as e:
        print(f"[Business] Error creating district business: {e}")
        import traceback
        traceback.print_exc()
        return None, str(e)
    finally:
        db.close()  # FIXED: Always close the session

# ==========================
# PUBLIC API
# ==========================

__all__ = [
    'Business',
    'RetailPrice',
    'BusinessSale',
    'BUSINESS_TYPES',
    'create_business',
    'toggle_business',
    'start_business_dismantling',
    'get_dismantling_status',
    'set_retail_price',
    'DISMANTLING_TICKS'
]
