#!/usr/bin/env python3
"""
One-shot cleanup: remove orphaned / government-accumulated share records
left behind by the pre-fix estate liquidation code.

Three categories are cleaned up:

  1. Government brokerage positions (player_id = 0, shares_owned > 0)
     – Shares were transferred to government when a player died. The position
       is deleted and the shares are returned to company.shares_in_float.

  2. Government bank shareholdings (player_id = 0, shares_owned > 0)
     – Same pattern. Holding is deleted and bank.total_shares_issued is
       decremented (shares retired).

  3. Zero-share positions / holdings (shares_owned <= 0, any player_id)
     – Left behind by company delistings before the fix. No shares to return;
       just delete the dead record.

Run with DRY_RUN=True first (the default) to preview, then set DRY_RUN=False
to commit:

    python3 migrate_cleanup_orphan_shares.py            # preview
    DRY_RUN=false python3 migrate_cleanup_orphan_shares.py  # apply
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))

DRY_RUN = os.environ.get("DRY_RUN", "true").lower() != "false"

GOVERNMENT_PLAYER_ID = 0


def run():
    from database import SessionLocal
    from banks import BankShareholding, BankEntity
    from banks.brokerage_firm import ShareholderPosition, CompanyShares

    db = SessionLocal()
    try:
        # ------------------------------------------------------------------ #
        # 1. Government-held brokerage positions                              #
        # ------------------------------------------------------------------ #
        gov_broker_positions = db.query(ShareholderPosition).filter(
            ShareholderPosition.player_id == GOVERNMENT_PLAYER_ID,
            ShareholderPosition.shares_owned > 0,
        ).all()

        print(f"\n=== Government brokerage positions (shares_owned > 0): {len(gov_broker_positions)} ===")
        broker_float_delta: dict[int, int] = {}  # company_shares_id -> shares to return
        for pos in gov_broker_positions:
            company = db.query(CompanyShares).filter(
                CompanyShares.id == pos.company_shares_id
            ).first()
            ticker = company.ticker_symbol if company else f"<id={pos.company_shares_id}>"
            delisted = company.is_delisted if company else "?"
            print(f"  pos_id={pos.id}  {ticker}  shares={pos.shares_owned}  delisted={delisted}")
            if company and not company.is_delisted:
                broker_float_delta[pos.company_shares_id] = (
                    broker_float_delta.get(pos.company_shares_id, 0) + pos.shares_owned
                )

        # ------------------------------------------------------------------ #
        # 2. Government-held bank shareholdings                               #
        # ------------------------------------------------------------------ #
        gov_bank_holdings = db.query(BankShareholding).filter(
            BankShareholding.player_id == GOVERNMENT_PLAYER_ID,
            BankShareholding.shares_owned > 0,
        ).all()

        print(f"\n=== Government bank shareholdings (shares_owned > 0): {len(gov_bank_holdings)} ===")
        bank_retire_delta: dict[str, int] = {}  # bank_id -> shares to retire
        for h in gov_bank_holdings:
            print(f"  holding_id={h.id}  bank={h.bank_id}  shares={h.shares_owned}")
            bank_retire_delta[h.bank_id] = (
                bank_retire_delta.get(h.bank_id, 0) + h.shares_owned
            )

        # ------------------------------------------------------------------ #
        # 3. Zero-share brokerage positions (all players)                     #
        # ------------------------------------------------------------------ #
        zero_broker = db.query(ShareholderPosition).filter(
            ShareholderPosition.shares_owned <= 0,
        ).all()
        print(f"\n=== Zero-share brokerage positions: {len(zero_broker)} ===")
        if zero_broker:
            print(f"  (all will be deleted; no float adjustment needed)")

        # ------------------------------------------------------------------ #
        # 4. Zero-share bank shareholdings (all players)                      #
        # ------------------------------------------------------------------ #
        zero_bank = db.query(BankShareholding).filter(
            BankShareholding.shares_owned <= 0,
        ).all()
        print(f"\n=== Zero-share bank shareholdings: {len(zero_bank)} ===")
        if zero_bank:
            print(f"  (all will be deleted; no share-count adjustment needed)")

        # ------------------------------------------------------------------ #
        # Summary                                                             #
        # ------------------------------------------------------------------ #
        total_deletions = (
            len(gov_broker_positions) + len(gov_bank_holdings) +
            len(zero_broker) + len(zero_bank)
        )
        print(f"\nTotal records to delete: {total_deletions}")

        if broker_float_delta:
            print("\nCompany float increases:")
            for cid, delta in broker_float_delta.items():
                company = db.query(CompanyShares).filter(CompanyShares.id == cid).first()
                if company:
                    print(f"  {company.ticker_symbol}: +{delta} shares "
                          f"(float {company.shares_in_float} → {company.shares_in_float + delta})")

        if bank_retire_delta:
            print("\nBank share retirements:")
            for bank_id, delta in bank_retire_delta.items():
                bank = db.query(BankEntity).filter(BankEntity.bank_id == bank_id).first()
                if bank:
                    print(f"  {bank_id}: -{delta} shares "
                          f"(total_shares_issued {bank.total_shares_issued} → "
                          f"{bank.total_shares_issued - delta})")

        if DRY_RUN:
            print("\n[DRY RUN] No changes committed. "
                  "Set DRY_RUN=false to apply.\n")
            return

        # ------------------------------------------------------------------ #
        # Apply                                                               #
        # ------------------------------------------------------------------ #
        print("\nApplying...")

        for pos in gov_broker_positions:
            company = db.query(CompanyShares).filter(
                CompanyShares.id == pos.company_shares_id
            ).first()
            if company and not company.is_delisted:
                company.shares_in_float += pos.shares_owned
            db.delete(pos)

        for h in gov_bank_holdings:
            bank = db.query(BankEntity).filter(BankEntity.bank_id == h.bank_id).first()
            if bank:
                bank.total_shares_issued -= h.shares_owned
            db.delete(h)

        for pos in zero_broker:
            db.delete(pos)

        for h in zero_bank:
            db.delete(h)

        db.commit()
        print(f"Done. Deleted {total_deletions} records.\n")

    except Exception as e:
        db.rollback()
        print(f"\nERROR: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    print(f"DRY_RUN={'yes — preview only' if DRY_RUN else 'NO — changes will be committed'}")
    run()
