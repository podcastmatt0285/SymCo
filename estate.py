"""
estate.py

Account deletion & estate settlement module for the economic simulation.

Handles:
- Voluntary account deletion ("death" by player choice)
- Automatic deletion for idle players (no login for 30+ days)
- Estate liquidation process (government seizes all assets)
- Government sells assets at market to recoup costs
- Debt settlement (percentage of debts paid from estate)
- Heir designation (up to 3 heirs per player)
- Inheritance distribution with death tax
- Death tax installment payments (over 1 week / 7 days)
- Deceased player records (permanent memorial / death certificate)
"""

from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy import create_engine, Column, String, Float, DateTime, Integer, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from stats_ux import log_transaction

# ==========================
# DATABASE SETUP
# ==========================
DATABASE_URL = "sqlite:///./wadsworth.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ==========================
# CONSTANTS
# ==========================
IDLE_DAYS_BEFORE_DEATH = 30  # Days without login before auto-deletion
IDLE_CHECK_INTERVAL = 3600  # Check every hour (3600 ticks = 5s * 720 = 1 hour)
DEBT_PAYMENT_PERCENTAGE = 0.60  # Gov pays 60% of outstanding debts from estate
DEATH_TAX_RATE = 0.15  # 15% inheritance tax
INSTALLMENT_COUNT = 7  # Pay death tax over 7 days
INSTALLMENT_INTERVAL = 17280  # 1 day in ticks (86400 seconds / 5 seconds per tick)
GOVERNMENT_PLAYER_ID = 0
GOV_LOAN_INTEREST_RATE = 0.0  # Government fronts the money interest-free
LIQUIDATION_DISCOUNT = 0.85  # Assets listed at 85% of market value for faster sale

# ==========================
# DATABASE MODELS
# ==========================

class DeceasedPlayer(Base):
    """Permanent record of a deleted player - the death certificate."""
    __tablename__ = "deceased_players"

    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, unique=True, index=True, nullable=False)
    business_name = Column(String, nullable=False)

    # Death details
    cause_of_death = Column(String, nullable=False)  # "voluntary" or "idle_timeout"
    date_of_death = Column(DateTime, default=datetime.utcnow)
    account_created = Column(DateTime, nullable=True)
    last_login = Column(DateTime, nullable=True)

    # Stats at death (snapshot)
    final_cash = Column(Float, default=0.0)
    final_net_worth = Column(Float, default=0.0)
    final_land_count = Column(Integer, default=0)
    final_business_count = Column(Integer, default=0)
    final_district_count = Column(Integer, default=0)

    # Estate settlement
    total_assets_liquidated = Column(Float, default=0.0)
    total_debts_settled = Column(Float, default=0.0)
    total_inherited = Column(Float, default=0.0)
    total_death_tax = Column(Float, default=0.0)
    government_took_all = Column(Boolean, default=False)

    # Leaderboard position at death
    highest_leaderboard_rank = Column(Integer, default=0)


class HeirDesignation(Base):
    """Player's designated heirs (up to 3)."""
    __tablename__ = "heir_designations"

    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, index=True, nullable=False)  # The player who designated
    heir_player_id = Column(Integer, index=True, nullable=False)  # The heir
    priority = Column(Integer, nullable=False)  # 1, 2, or 3 (1 = primary)
    designated_at = Column(DateTime, default=datetime.utcnow)


class InheritanceInstallment(Base):
    """Death tax installment payments owed by heirs."""
    __tablename__ = "inheritance_installments"

    id = Column(Integer, primary_key=True, index=True)
    heir_player_id = Column(Integer, index=True, nullable=False)
    deceased_player_id = Column(Integer, index=True, nullable=False)

    # Amounts
    total_inherited = Column(Float, default=0.0)
    total_tax_owed = Column(Float, default=0.0)
    total_tax_paid = Column(Float, default=0.0)
    installment_amount = Column(Float, default=0.0)  # Per-installment payment

    # Schedule
    installments_remaining = Column(Integer, default=7)
    next_installment_tick = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    completed = Column(Boolean, default=False)


class GovernmentEstateListing(Base):
    """Items/assets the government is selling from a deceased player's estate."""
    __tablename__ = "government_estate_listings"

    id = Column(Integer, primary_key=True, index=True)
    deceased_player_id = Column(Integer, index=True, nullable=False)
    item_type = Column(String, nullable=False)
    quantity = Column(Float, default=0.0)
    listed_price = Column(Float, default=0.0)
    listed_at = Column(DateTime, default=datetime.utcnow)
    sold = Column(Boolean, default=False)


# ==========================
# HELPER FUNCTIONS
# ==========================

def get_db():
    return SessionLocal()


def get_player_heirs(player_id: int) -> List[HeirDesignation]:
    """Get a player's designated heirs ordered by priority."""
    db = get_db()
    try:
        heirs = db.query(HeirDesignation).filter(
            HeirDesignation.player_id == player_id
        ).order_by(HeirDesignation.priority.asc()).all()
        return heirs
    finally:
        db.close()


def get_heir_installments(player_id: int) -> List[InheritanceInstallment]:
    """Get pending inheritance tax installments for a player (as heir)."""
    db = get_db()
    try:
        return db.query(InheritanceInstallment).filter(
            InheritanceInstallment.heir_player_id == player_id,
            InheritanceInstallment.completed == False
        ).all()
    finally:
        db.close()


def get_all_deceased() -> List[DeceasedPlayer]:
    """Get all deceased players ordered by date of death."""
    db = get_db()
    try:
        return db.query(DeceasedPlayer).order_by(
            DeceasedPlayer.date_of_death.desc()
        ).all()
    finally:
        db.close()


def is_player_deceased(player_id: int) -> bool:
    """Check if a player has been marked as deceased."""
    db = get_db()
    try:
        return db.query(DeceasedPlayer).filter(
            DeceasedPlayer.player_id == player_id
        ).first() is not None
    finally:
        db.close()


# ==========================
# HEIR MANAGEMENT
# ==========================

def set_heir(player_id: int, heir_player_id: int, priority: int) -> bool:
    """
    Designate a player as heir at the given priority (1-3).
    Returns True if successful.
    """
    if priority < 1 or priority > 3:
        return False
    if player_id == heir_player_id:
        return False

    db = get_db()
    try:
        # Verify the heir exists and is alive
        from auth import Player
        heir = db.query(Player).filter(Player.id == heir_player_id).first()
        if not heir:
            return False

        # Check heir isn't already deceased
        deceased = db.query(DeceasedPlayer).filter(
            DeceasedPlayer.player_id == heir_player_id
        ).first()
        if deceased:
            return False

        # Remove existing designation at this priority
        existing = db.query(HeirDesignation).filter(
            HeirDesignation.player_id == player_id,
            HeirDesignation.priority == priority
        ).first()
        if existing:
            db.delete(existing)

        # Also remove if this heir is already designated at another priority
        dupe = db.query(HeirDesignation).filter(
            HeirDesignation.player_id == player_id,
            HeirDesignation.heir_player_id == heir_player_id
        ).first()
        if dupe:
            db.delete(dupe)

        # Create new designation
        designation = HeirDesignation(
            player_id=player_id,
            heir_player_id=heir_player_id,
            priority=priority
        )
        db.add(designation)
        db.commit()
        return True
    except Exception as e:
        print(f"[Estate] Error setting heir: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def remove_heir(player_id: int, priority: int) -> bool:
    """Remove an heir designation at the given priority."""
    db = get_db()
    try:
        existing = db.query(HeirDesignation).filter(
            HeirDesignation.player_id == player_id,
            HeirDesignation.priority == priority
        ).first()
        if existing:
            db.delete(existing)
            db.commit()
            return True
        return False
    finally:
        db.close()


# ==========================
# ESTATE LIQUIDATION ENGINE
# ==========================

def calculate_estate_value(player_id: int, db) -> dict:
    """Calculate the total value of a player's estate."""
    from auth import Player
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        return {"total": 0.0, "cash": 0.0, "inventory": 0.0, "land": 0.0,
                "businesses": 0.0, "shares": 0.0, "districts": 0.0}

    estate = {
        "cash": player.cash_balance,
        "inventory": 0.0,
        "land": 0.0,
        "businesses": 0.0,
        "shares": 0.0,
        "districts": 0.0,
        "land_count": 0,
        "business_count": 0,
        "district_count": 0,
    }

    # Inventory value
    try:
        from inventory import InventoryItem
        from market import get_market_price
        items = db.query(InventoryItem).filter(
            InventoryItem.player_id == player_id,
            InventoryItem.quantity > 0
        ).all()
        for item in items:
            price = get_market_price(item.item_type) or 1.0
            estate["inventory"] += item.quantity * price
    except Exception as e:
        print(f"[Estate] Inventory valuation error: {e}")

    # Land value
    try:
        from land import LandPlot
        plots = db.query(LandPlot).filter(LandPlot.owner_id == player_id).all()
        estate["land_count"] = len(plots)
        for plot in plots:
            estate["land"] += (plot.monthly_tax or 50.0) * 12
    except Exception as e:
        print(f"[Estate] Land valuation error: {e}")

    # Business value
    try:
        from business import Business, BUSINESS_TYPES
        businesses = db.query(Business).filter(
            Business.owner_id == player_id,
            Business.is_active == True
        ).all()
        estate["business_count"] = len(businesses)
        for biz in businesses:
            config = BUSINESS_TYPES.get(biz.business_type, {})
            estate["businesses"] += config.get("startup_cost", 10000)
    except Exception as e:
        print(f"[Estate] Business valuation error: {e}")

    # District value
    try:
        from districts import District, DISTRICT_TYPES
        districts = db.query(District).filter(District.owner_id == player_id).all()
        estate["district_count"] = len(districts)
        for d in districts:
            config = DISTRICT_TYPES.get(d.district_type, {})
            estate["districts"] += config.get("base_tax", 50000) * 12
    except Exception as e:
        print(f"[Estate] District valuation error: {e}")

    # Share value (bank shares + brokerage shares)
    try:
        from banks import BankShareholding, BankEntity
        holdings = db.query(BankShareholding).filter(
            BankShareholding.player_id == player_id,
            BankShareholding.shares_owned > 0
        ).all()
        for h in holdings:
            bank = db.query(BankEntity).filter(BankEntity.bank_id == h.bank_id).first()
            if bank:
                estate["shares"] += h.shares_owned * (bank.share_price or 0)
    except Exception as e:
        print(f"[Estate] Bank share valuation error: {e}")

    try:
        from banks.brokerage_firm import ShareholderPosition, CompanyShares
        positions = db.query(ShareholderPosition).filter(
            ShareholderPosition.player_id == player_id,
            ShareholderPosition.shares_owned > 0
        ).all()
        for pos in positions:
            company = db.query(CompanyShares).filter(
                CompanyShares.id == pos.company_shares_id
            ).first()
            if company:
                estate["shares"] += pos.shares_owned * (company.current_price or 0)
    except Exception as e:
        print(f"[Estate] Brokerage share valuation error: {e}")

    estate["total"] = (
        estate["cash"] + estate["inventory"] + estate["land"] +
        estate["businesses"] + estate["shares"] + estate["districts"]
    )

    return estate


def calculate_total_debts(player_id: int, db) -> float:
    """Calculate total outstanding debts for a player."""
    total_debts = 0.0

    # Bank liens
    try:
        from banks.land_bank import BankLien
        liens = db.query(BankLien).filter(BankLien.player_id == player_id).all()
        for lien in liens:
            owed = lien.principal + lien.interest_accrued - lien.total_paid
            if owed > 0:
                total_debts += owed
    except Exception as e:
        print(f"[Estate] Bank lien calculation error: {e}")

    # Brokerage liens
    try:
        from banks.brokerage_firm import BrokerageLien
        b_liens = db.query(BrokerageLien).filter(
            BrokerageLien.player_id == player_id
        ).all()
        for lien in b_liens:
            owed = lien.principal + lien.interest_accrued - lien.total_paid
            if owed > 0:
                total_debts += owed
    except Exception as e:
        print(f"[Estate] Brokerage lien calculation error: {e}")

    # Margin debt
    try:
        from banks.brokerage_firm import ShareholderPosition
        margin_positions = db.query(ShareholderPosition).filter(
            ShareholderPosition.player_id == player_id,
            ShareholderPosition.is_margin_position == True,
            ShareholderPosition.margin_debt > 0
        ).all()
        for pos in margin_positions:
            total_debts += pos.margin_debt
    except Exception as e:
        print(f"[Estate] Margin debt calculation error: {e}")

    return total_debts


def liquidate_estate(player_id: int, cause: str, current_tick: int) -> Optional[DeceasedPlayer]:
    """
    Execute the full estate liquidation process:
    1. Snapshot player stats for death certificate
    2. Government seizes all assets
    3. Liquidate inventory/shares at market value
    4. Pay percentage of debts
    5. Distribute remainder to heirs (or government if no heirs)
    6. Create death tax installments for heirs
    7. Delete player account
    8. Create permanent deceased record
    """
    db = get_db()
    try:
        from auth import Player
        player = db.query(Player).filter(Player.id == player_id).first()
        if not player:
            return None

        # Prevent double-death
        existing = db.query(DeceasedPlayer).filter(
            DeceasedPlayer.player_id == player_id
        ).first()
        if existing:
            return existing

        print(f"[Estate] Beginning estate liquidation for {player.business_name} (ID: {player_id})")

        # 1. Snapshot stats
        estate = calculate_estate_value(player_id, db)
        total_debts = calculate_total_debts(player_id, db)

        # Get leaderboard rank
        try:
            from stats_ux import PlayerStats
            cached_stats = db.query(PlayerStats).filter(
                PlayerStats.player_id == player_id
            ).first()
            leaderboard_rank = cached_stats.wealth_rank if cached_stats else 0
        except:
            leaderboard_rank = 0

        # 2. Government seizes all assets - calculate total liquidation value
        liquidation_value = estate["cash"]

        # Liquidate inventory (sell to government at discounted market price)
        try:
            from inventory import InventoryItem
            from market import get_market_price
            items = db.query(InventoryItem).filter(
                InventoryItem.player_id == player_id,
                InventoryItem.quantity > 0
            ).all()
            for item in items:
                price = get_market_price(item.item_type) or 1.0
                value = item.quantity * price * LIQUIDATION_DISCOUNT
                liquidation_value += value

                # Create government estate listing for these items
                listing = GovernmentEstateListing(
                    deceased_player_id=player_id,
                    item_type=item.item_type,
                    quantity=item.quantity,
                    listed_price=price * LIQUIDATION_DISCOUNT
                )
                db.add(listing)

                # Transfer items to government (player 0)
                item.player_id = GOVERNMENT_PLAYER_ID
                print(f"[Estate] Seized {item.quantity:.0f} {item.item_type} (${value:,.2f})")
        except Exception as e:
            print(f"[Estate] Inventory liquidation error: {e}")

        # Liquidate bank shares
        try:
            from banks import BankShareholding, BankEntity
            holdings = db.query(BankShareholding).filter(
                BankShareholding.player_id == player_id,
                BankShareholding.shares_owned > 0
            ).all()
            for h in holdings:
                bank = db.query(BankEntity).filter(BankEntity.bank_id == h.bank_id).first()
                if bank and bank.share_price:
                    value = h.shares_owned * bank.share_price * LIQUIDATION_DISCOUNT
                    liquidation_value += value
                    # Transfer shares to government
                    h.player_id = GOVERNMENT_PLAYER_ID
                    print(f"[Estate] Seized {h.shares_owned} {h.bank_id} shares (${value:,.2f})")
        except Exception as e:
            print(f"[Estate] Bank share liquidation error: {e}")

        # Liquidate brokerage positions
        try:
            from banks.brokerage_firm import ShareholderPosition, CompanyShares
            positions = db.query(ShareholderPosition).filter(
                ShareholderPosition.player_id == player_id,
                ShareholderPosition.shares_owned > 0
            ).all()
            for pos in positions:
                company = db.query(CompanyShares).filter(
                    CompanyShares.id == pos.company_shares_id
                ).first()
                if company and company.current_price:
                    value = pos.shares_owned * company.current_price * LIQUIDATION_DISCOUNT
                    liquidation_value += value
                    # Transfer shares to government
                    pos.player_id = GOVERNMENT_PLAYER_ID
                    print(f"[Estate] Seized {pos.shares_owned} {company.ticker_symbol} shares (${value:,.2f})")
        except Exception as e:
            print(f"[Estate] Brokerage liquidation error: {e}")

        # Liquidate land (transfer to government for auction)
        try:
            from land import LandPlot
            from business import Business, BusinessSale
            plots = db.query(LandPlot).filter(LandPlot.owner_id == player_id).all()
            for plot in plots:
                plot_value = (plot.monthly_tax or 50.0) * 12 * LIQUIDATION_DISCOUNT
                liquidation_value += plot_value

                # Remove any businesses on this land
                biz = db.query(Business).filter(Business.land_plot_id == plot.id).first()
                if biz:
                    # Cancel any dismantling in progress
                    sale = db.query(BusinessSale).filter(BusinessSale.business_id == biz.id).first()
                    if sale:
                        db.delete(sale)
                    db.delete(biz)
                    plot.occupied_by_business_id = None

                # Transfer plot to government
                plot.owner_id = GOVERNMENT_PLAYER_ID
                print(f"[Estate] Seized land plot #{plot.id} ({plot.terrain_type}) (${plot_value:,.2f})")
        except Exception as e:
            print(f"[Estate] Land liquidation error: {e}")

        # Liquidate districts
        try:
            from districts import District, DISTRICT_TYPES
            districts = db.query(District).filter(District.owner_id == player_id).all()
            for d in districts:
                config = DISTRICT_TYPES.get(d.district_type, {})
                district_value = config.get("base_tax", 50000) * 12 * LIQUIDATION_DISCOUNT
                liquidation_value += district_value
                d.owner_id = GOVERNMENT_PLAYER_ID
                print(f"[Estate] Seized district {d.id} ({d.district_type}) (${district_value:,.2f})")
        except Exception as e:
            print(f"[Estate] District liquidation error: {e}")

        # 3. Pay debts from estate (60% of debts)
        debt_payment = min(total_debts * DEBT_PAYMENT_PERCENTAGE, liquidation_value * 0.5)

        # Pay bank liens
        try:
            from banks.land_bank import BankLien
            liens = db.query(BankLien).filter(BankLien.player_id == player_id).all()
            remaining_payment = debt_payment
            for lien in liens:
                owed = lien.principal + lien.interest_accrued - lien.total_paid
                if owed > 0 and remaining_payment > 0:
                    payment = min(owed, remaining_payment)
                    lien.total_paid += payment
                    remaining_payment -= payment
                    print(f"[Estate] Paid ${payment:,.2f} on bank lien #{lien.id}")
                # Mark lien as settled regardless
                db.delete(lien)
        except Exception as e:
            print(f"[Estate] Bank lien payment error: {e}")

        # Pay brokerage liens
        try:
            from banks.brokerage_firm import BrokerageLien
            b_liens = db.query(BrokerageLien).filter(
                BrokerageLien.player_id == player_id
            ).all()
            for lien in b_liens:
                owed = lien.principal + lien.interest_accrued - lien.total_paid
                if owed > 0 and remaining_payment > 0:
                    payment = min(owed, remaining_payment)
                    lien.total_paid += payment
                    remaining_payment -= payment
                    print(f"[Estate] Paid ${payment:,.2f} on brokerage lien #{lien.id}")
                db.delete(lien)
        except Exception as e:
            print(f"[Estate] Brokerage lien payment error: {e}")

        # Clear margin positions
        try:
            from banks.brokerage_firm import ShareholderPosition
            margin_pos = db.query(ShareholderPosition).filter(
                ShareholderPosition.player_id == player_id,
                ShareholderPosition.is_margin_position == True
            ).all()
            for pos in margin_pos:
                pos.margin_debt = 0.0
                pos.is_margin_position = False
        except:
            pass

        # 4. Calculate remainder after debts
        remainder = max(0.0, liquidation_value - debt_payment)

        # 5. Distribute to heirs
        heirs = db.query(HeirDesignation).filter(
            HeirDesignation.player_id == player_id
        ).order_by(HeirDesignation.priority.asc()).all()

        # Filter out any deceased heirs
        living_heirs = []
        for h in heirs:
            heir_deceased = db.query(DeceasedPlayer).filter(
                DeceasedPlayer.player_id == h.heir_player_id
            ).first()
            if not heir_deceased:
                heir_player = db.query(Player).filter(Player.id == h.heir_player_id).first()
                if heir_player:
                    living_heirs.append(h)

        total_inherited = 0.0
        total_death_tax = 0.0
        government_took_all = len(living_heirs) == 0

        if living_heirs and remainder > 0:
            # Split equally among heirs
            per_heir = remainder / len(living_heirs)

            for heir in living_heirs:
                heir_player = db.query(Player).filter(Player.id == heir.heir_player_id).first()
                if not heir_player:
                    continue

                death_tax = per_heir * DEATH_TAX_RATE
                inheritance_after_tax = per_heir - death_tax

                # Pay inheritance immediately
                heir_player.cash_balance += inheritance_after_tax
                total_inherited += inheritance_after_tax
                total_death_tax += death_tax

                # Create death tax installments (heir pays tax over 7 days)
                installment_amount = death_tax / INSTALLMENT_COUNT
                installment = InheritanceInstallment(
                    heir_player_id=heir.heir_player_id,
                    deceased_player_id=player_id,
                    total_inherited=per_heir,
                    total_tax_owed=death_tax,
                    total_tax_paid=0.0,
                    installment_amount=installment_amount,
                    installments_remaining=INSTALLMENT_COUNT,
                    next_installment_tick=current_tick + INSTALLMENT_INTERVAL
                )
                db.add(installment)

                log_transaction(
                    player_id=heir.heir_player_id,
                    transaction_type="inheritance",
                    category="money",
                    amount=inheritance_after_tax,
                    description=f"Inherited from {player.business_name} (before tax: ${per_heir:,.2f})"
                )

                print(f"[Estate] Heir {heir.heir_player_id} receives ${inheritance_after_tax:,.2f} "
                      f"(tax: ${death_tax:,.2f} in {INSTALLMENT_COUNT} installments)")
        else:
            # No heirs - government takes everything
            gov = db.query(Player).filter(Player.id == GOVERNMENT_PLAYER_ID).first()
            if gov:
                gov.cash_balance += remainder
                print(f"[Estate] No heirs - government receives ${remainder:,.2f}")
            government_took_all = True

        # 6. Create deceased player record (death certificate)
        deceased = DeceasedPlayer(
            player_id=player_id,
            business_name=player.business_name,
            cause_of_death=cause,
            date_of_death=datetime.utcnow(),
            account_created=player.created_at,
            last_login=player.last_login,
            final_cash=estate["cash"],
            final_net_worth=estate["total"],
            final_land_count=estate["land_count"],
            final_business_count=estate["business_count"],
            final_district_count=estate["district_count"],
            total_assets_liquidated=liquidation_value,
            total_debts_settled=debt_payment,
            total_inherited=total_inherited,
            total_death_tax=total_death_tax,
            government_took_all=government_took_all,
            highest_leaderboard_rank=leaderboard_rank
        )
        db.add(deceased)

        # 7. Clean up player data
        # Remove market orders
        try:
            from market import MarketOrder
            db.query(MarketOrder).filter(
                MarketOrder.player_id == player_id,
                MarketOrder.status == "active"
            ).update({"status": "cancelled"})
        except:
            pass

        # Remove heir designations (they're the deceased's designations)
        db.query(HeirDesignation).filter(
            HeirDesignation.player_id == player_id
        ).delete()

        # Remove any designations where deceased was someone else's heir
        db.query(HeirDesignation).filter(
            HeirDesignation.heir_player_id == player_id
        ).delete()

        # Remove sessions
        try:
            from auth import Session as AuthSession, active_sessions
            sessions = db.query(AuthSession).filter(AuthSession.player_id == player_id).all()
            for s in sessions:
                active_sessions.pop(s.session_token, None)
                db.delete(s)
        except:
            pass

        # Remove retail prices
        try:
            from business import RetailPrice
            db.query(RetailPrice).filter(RetailPrice.player_id == player_id).delete()
        except:
            pass

        # Remove stats cache
        try:
            from stats_ux import PlayerStats, PlayerCostAverage
            db.query(PlayerStats).filter(PlayerStats.player_id == player_id).delete()
            db.query(PlayerCostAverage).filter(PlayerCostAverage.player_id == player_id).delete()
        except:
            pass

        # Remove city memberships
        try:
            from cities import CityMember, CityApplication
            db.query(CityMember).filter(CityMember.player_id == player_id).delete()
            db.query(CityApplication).filter(CityApplication.player_id == player_id).delete()
        except:
            pass

        # Remove executive assignments
        try:
            from executive import Executive
            db.query(Executive).filter(Executive.employer_id == player_id).update(
                {"employer_id": None}
            )
        except:
            pass

        # Finally, delete the player record
        db.delete(player)

        db.commit()

        print(f"[Estate] Estate liquidation complete for {deceased.business_name}")
        print(f"[Estate]   Liquidated: ${liquidation_value:,.2f}")
        print(f"[Estate]   Debts Paid: ${debt_payment:,.2f}")
        print(f"[Estate]   Inherited:  ${total_inherited:,.2f}")
        print(f"[Estate]   Death Tax:  ${total_death_tax:,.2f}")
        print(f"[Estate]   Gov Took All: {government_took_all}")

        return deceased
    except Exception as e:
        print(f"[Estate] CRITICAL ERROR in liquidation: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return None
    finally:
        db.close()


# ==========================
# TICK PROCESSING
# ==========================

def process_installments(current_tick: int):
    """Process death tax installment payments each tick."""
    db = get_db()
    try:
        from auth import Player

        pending = db.query(InheritanceInstallment).filter(
            InheritanceInstallment.completed == False,
            InheritanceInstallment.next_installment_tick <= current_tick
        ).all()

        for inst in pending:
            heir = db.query(Player).filter(Player.id == inst.heir_player_id).first()
            if not heir:
                # Heir no longer exists, mark completed
                inst.completed = True
                continue

            payment = inst.installment_amount
            # Take what we can from the heir
            actual_payment = min(payment, heir.cash_balance)

            if actual_payment > 0:
                heir.cash_balance -= actual_payment
                inst.total_tax_paid += actual_payment
                inst.installments_remaining -= 1
                inst.next_installment_tick = current_tick + INSTALLMENT_INTERVAL

                # Pay to government
                gov = db.query(Player).filter(Player.id == GOVERNMENT_PLAYER_ID).first()
                if gov:
                    gov.cash_balance += actual_payment

                log_transaction(
                    player_id=inst.heir_player_id,
                    transaction_type="death_tax",
                    category="money",
                    amount=-actual_payment,
                    description=f"Death tax installment ({inst.installments_remaining} remaining)"
                )

                print(f"[Estate] Heir {inst.heir_player_id} paid ${actual_payment:,.2f} "
                      f"death tax ({inst.installments_remaining} installments remaining)")
            else:
                # Can't pay - push to next cycle
                inst.next_installment_tick = current_tick + INSTALLMENT_INTERVAL
                print(f"[Estate] Heir {inst.heir_player_id} insufficient funds for death tax installment")

            if inst.installments_remaining <= 0 or inst.total_tax_paid >= inst.total_tax_owed:
                inst.completed = True
                print(f"[Estate] Death tax installments complete for heir {inst.heir_player_id}")

        db.commit()
    except Exception as e:
        print(f"[Estate] Installment processing error: {e}")
        db.rollback()
    finally:
        db.close()


def check_idle_players(current_tick: int):
    """Check for players who haven't logged in for too long and auto-delete them."""
    db = get_db()
    try:
        from auth import Player
        cutoff = datetime.utcnow() - timedelta(days=IDLE_DAYS_BEFORE_DEATH)

        idle_players = db.query(Player).filter(
            Player.last_login < cutoff,
            Player.id > 0  # Don't delete government
        ).all()

        for player in idle_players:
            # Check if already deceased
            existing = db.query(DeceasedPlayer).filter(
                DeceasedPlayer.player_id == player.id
            ).first()
            if existing:
                continue

            print(f"[Estate] Player {player.business_name} (ID: {player.id}) "
                  f"last login: {player.last_login} - triggering auto-deletion")
            db.close()
            liquidate_estate(player.id, "idle_timeout", current_tick)
            db = get_db()  # Reopen since liquidate_estate closes db

    except Exception as e:
        print(f"[Estate] Idle check error: {e}")
    finally:
        db.close()


# ==========================
# MODULE LIFECYCLE
# ==========================

def initialize():
    """Initialize estate module."""
    print("[Estate] Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("[Estate] Account deletion & estate system initialized")


async def tick(current_tick: int, now):
    """Estate system tick handler."""
    # Process death tax installments every 60 ticks (5 minutes)
    if current_tick % 60 == 0:
        process_installments(current_tick)

    # Check for idle players every hour
    if current_tick % IDLE_CHECK_INTERVAL == 0:
        check_idle_players(current_tick)


# ==========================
# PUBLIC API
# ==========================

__all__ = [
    'DeceasedPlayer',
    'HeirDesignation',
    'InheritanceInstallment',
    'GovernmentEstateListing',
    'get_player_heirs',
    'get_heir_installments',
    'get_all_deceased',
    'is_player_deceased',
    'set_heir',
    'remove_heir',
    'liquidate_estate',
    'calculate_estate_value',
    'calculate_total_debts',
    'initialize',
    'tick'
]
