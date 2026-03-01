"""
Post historical patch notes to the Updates channel.
Run with: PYTHONPATH=venv/lib/python3.12/site-packages python3.12 post_patch_notes.py
"""
import time
from admins import post_update

ADMIN_ID = 1

# Each entry is (title_hint, message).  Messages must be <= 500 chars.
# Listed oldest → newest, matching git history chronological order.
PATCH_NOTES = [
    # ── WSC / AMM price oracle ──────────────────────────────────────────
    (
        "WSC price oracle fix",
        "Backend Fix — Corrected the AMM price oracle that was using "
        "treasury_balance/minted instead of real market price. "
        "Fixed _native_usd_price formula and resolved three WSC bond/forex "
        "system bugs. Native token swaps at /banks/brokerage-firm now price "
        "accurately."
    ),

    # ── Migration infrastructure ────────────────────────────────────────
    (
        "DDL migration infrastructure",
        "Backend Fix — Centralised all schema migrations into a "
        "run_ddl_migration() helper applied across 8 modules. Fixed "
        "PostgreSQL privilege issues by falling back to the admin connection "
        "and using AUTOCOMMIT isolation for ALTER TABLE statements. Also "
        "fixed a pre-existing syntax error on the tutorial page."
    ),

    # ── Multi-currency display rollout ──────────────────────────────────
    (
        "Multi-currency display rollout",
        "Feature — Introduced a fmt_usd() currency formatter so all money "
        "amounts display in your legal tender. Balances on /executives, "
        "/stats, /cities, counties, estate, and brokerage pages now show "
        "your preferred currency symbol. Set your currency at "
        "/reserve-banks/forex."
    ),

    # ── Multi-currency bug fixes ─────────────────────────────────────────
    (
        "Multi-currency bug fixes",
        "Bug Fix — Fixed foreign-currency transaction processing bugs, an "
        "IndentationError on /stats, and extended multi-currency handling to "
        "/cities, districts, counties, and corporate actions. Hardened "
        "inventory transfers and all remaining payment flows for non-USD "
        "players."
    ),

    # ── Market order fixes ───────────────────────────────────────────────
    (
        "Market order cancellation + price conversion",
        "Bug Fix — Partially-filled brokerage orders at /brokerage/trading "
        "are now properly cancelled and prices are converted to USD on "
        "submission. Fixed missing fmt_usd imports that were causing 500 "
        "errors on /cities and /admin."
    ),

    # ── City projects redesign ───────────────────────────────────────────
    (
        "City projects redesign",
        "Feature — City projects at /city/my have been redesigned with "
        "per-project vaults, licenses, and a sales tax system. City buffs "
        "are now active: construction speed, loan interest, and market fee "
        "multipliers. A city bonus panel has been added to /businesses."
    ),

    # ── Corporate actions + exchange multi-currency ──────────────────────
    (
        "Corporate actions & exchange multi-currency",
        "Bug Fix — Corporate actions (/offering, /buyback), /stats, counties, "
        "and the exchange now respect your legal tender. Remaining hardcoded "
        "$ symbols on /brokerage/trading, token info, and wallet pages have "
        "been corrected."
    ),

    # ── EIP-1559 gas fees ────────────────────────────────────────────────
    (
        "Dynamic gas fees (EIP-1559 style)",
        "Feature — Each blockchain now runs dynamic EIP-1559-style gas fees "
        "that adjust based on network demand each tick. Real-time gas cost "
        "visibility has been added across all transaction points in the "
        "crypto exchange and wallet."
    ),

    # ── Crypto exchange multi-currency fixes ─────────────────────────────
    (
        "Crypto exchange multi-currency fixes",
        "Bug Fix — Fixed multi-currency display bugs in the Wadsworth crypto "
        "exchange. Resolved a gas tracker 500 error, a buy-form currency "
        "mismatch, and a JavaScript NameError (cashUsd) that prevented "
        "balances from rendering correctly."
    ),

    # ── Forex display fixes ──────────────────────────────────────────────
    (
        "Forex & reserve banks display fixes",
        "Bug Fix — Fixed WSC peg display (was showing $0 instead of $1). "
        "Eliminated duplicate USD rows in currency balances. True USD total "
        "at /reserve-banks/forex now accounts for all sources. Executive and "
        "loan charges now route through spend_player_funds for legal tender "
        "support."
    ),

    # ── New reserve banks ────────────────────────────────────────────────
    (
        "Six new reserve banks",
        "Feature — Six new currencies are now available at "
        "/reserve-banks/bonds and /reserve-banks/forex:\n"
        "KRW (Korean Won), ZAR (South African Rand), BRL (Brazilian Real), "
        "TRY (Turkish Lira), SAR (Saudi Riyal), AED (UAE Dirham).\n"
        "Buy bonds in any of these to earn interest and hold foreign "
        "currency."
    ),

    # ── New IPO types ────────────────────────────────────────────────────
    (
        "New IPO offering types",
        "Feature — Four IPO structures are now live at /brokerage/ipo:\n"
        "- Dual-Class IPO (now activated)\n"
        "- Preferred Offering (fixed-dividend preference shares)\n"
        "- Series A Growth (venture-stage structure)\n"
        "- Quad-Class IPO (four separate voting tiers)"
    ),

    # ── Leaderboard + USD migration ──────────────────────────────────────
    (
        "USD currency migration & leaderboard fix",
        "Backend — USD balances have been migrated from the players table "
        "into PlayerCurrencyBalance, treating USD as a reserve currency like "
        "all others. The /stats/leaderboard now correctly includes all "
        "foreign currency balances in net-worth calculations."
    ),

    # ── cash_balance property bridge (today) ─────────────────────────────
    (
        "Player cash_balance bridge (backend)",
        "Backend Fix — Added a cash_balance property to the Player model "
        "that bridges to the reserve_banks database. This resolves attribute "
        "errors across 321+ call sites that still referenced the old column. "
        "Balance reads and writes now flow transparently through "
        "PlayerCurrencyBalance."
    ),
]


def main():
    print(f"Posting {len(PATCH_NOTES)} patch notes to the Updates channel...\n")
    for i, (title, content) in enumerate(PATCH_NOTES, 1):
        if len(content) > 500:
            print(f"  WARNING: Message {i} ({title}) is {len(content)} chars — truncating")
            content = content[:497] + "..."
        result = post_update(ADMIN_ID, content)
        status = "OK" if result.get("ok") else f"FAILED: {result.get('error')}"
        print(f"  [{i:02d}/{len(PATCH_NOTES)}] {title[:50]:<50} {status}")
        time.sleep(0.3)   # small delay to preserve ordering in the DB

    print("\nDone.")


if __name__ == "__main__":
    main()
