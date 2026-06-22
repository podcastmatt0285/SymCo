# Wadsworth Simulator — Performance Brainstorming Report

An analysis of the local Wadsworth simulation (`app.py`, CPU usage ~45%) reveals several systemic bottlenecks in the tick loop that cause the CLI to print `[Tick X] SLOW module '...'` warnings (which trigger whenever a module's tick exceeds 4.0 seconds). 

The root cause of these warnings is **database session connection churn** combined with **redundant O(N) loops performing sequential database queries** on every 5-second tick.

---

## 1. Redundant Order Matching on Every Tick (`market`, `district_market`, `brokerage_order_book`)

The commodity market, district market, and brokerage stock system all attempt to run matching engines on a scheduler (every 5-second tick), resulting in massive database read/write amplification.

### The Mechanism
* **Commodity & District Markets:** In [market.py:L1142](file:///home/maphematics/SymCo/market.py#L1142) and [district_market.py:L736](file:///home/maphematics/SymCo/district_market.py#L736), the `tick()` function queries the database for up to 100 or 200 active/partially-filled orders and sequentially calls `match_order()` for each. Inside `match_order()`, a new query is executed to search the database for crossing counter-orders.
* **Brokerage Stock Book:** In [brokerage_order_book.py:L1172](file:///home/maphematics/SymCo/banks/brokerage_order_book.py#L1172), the `tick()` function queries all active companies, and for *each* company, it calls `match_orders(company.id)`, which opens a brand new DB session (`get_db()`) and queries active buy/sell orders.

### Why It is Slow
1. **Redundancy:** In a standard double-auction limit order book, orders are matched *synchronously* immediately upon creation. If a buy order is placed, it matches with existing sells. If it cannot match, it sits in the book. It will **never** match in the future unless a *new* sell order is placed. 
2. **Infinite Re-matching:** Rematching existing open orders on every tick does nothing but re-prove that they still do not cross, executing hundreds of useless queries on every single tick.
3. **Session Overhead:** Opening a separate DB session for every company (N+1 sessions) or running 200 matchmaking queries sequentially inside a single thread blocks the tick loop.

---

## 2. Coin Peg Cache Misses on Every Tick (`reserve_banks.py` + `market.py`)

The metal coin peg system triggers an avalanche of cache-missed database queries on every single 5-second tick.

### The Mechanism
* In [reserve_banks.py:L645](file:///home/maphematics/SymCo/reserve_banks.py#L645), the `tick()` function calls `_refresh_coin_pegs(now)` on **every single tick** (not just on the `RESERVE_BANKS_TICK_INTERVAL` cadence).
* `_refresh_coin_pegs()` opens a database session, queries the 6 coin currencies, and calls `get_live_coin_usd_per_unit(code)` for each.
* `get_live_coin_usd_per_unit()` queries the composition of the coin (metals like gold, silver, copper, platinum) and calls `_mkt.get_market_price(metal)` for each metal.
* `get_market_price(item_type)` in [market.py:L1020](file:///home/maphematics/SymCo/market.py#L1020) checks an in-memory cache `_PRICE_CACHE` before querying the DB. The cache has a TTL of **3.0 seconds** (`_PRICE_CACHE_TTL = 3.0`).

### Why It is Slow
1. **The TTL Mismatch:** The global tick loop runs every **5.0 seconds** (`TICK_INTERVAL = 5.0`). Because the cache TTL is only 3.0 seconds, **the price cache is guaranteed to be expired on every tick**.
2. **Query Cascade:** Every coin peg refresh (every 5 seconds) triggers a cache miss for every backing metal. This causes `get_market_price()` to open its own database session and query the `MarketOrder` table twice (once for bid, once for ask) plus the `Trade` table if order books are empty. 
3. **Connection Churn:** For 6 coins and multiple backing metals, the simulator opens and closes **6 to 12 separate database sessions** sequentially, running dozens of raw database scans just to check metal values that rarely change.

---

## 3. Sequential Legal Tender Conversion in Business Production (`business.py` + `reserve_banks.py`)

Although the business production tick was recently optimized to batch updates for the business entities themselves, it still performs sequential, unbatched updates for player balances.

### The Mechanism
* At the end of `process_business_tick()` in [business.py:L856](file:///home/maphematics/SymCo/business.py#L856), the system flushes accumulated revenue to players:
  ```python
  if _pending_credits:
      for _pid, _amt in _pending_credits.items():
          convert_to_legal_tender(_pid, _amt)
  ```
* `convert_to_legal_tender()` delegates to `process_income_conversion()`, which opens a **fresh database session** (`get_db()`) inside a loop for each unique player.
* Inside `process_income_conversion()`, it performs multiple queries (loading exchange rates, updating bank reserves, writing forex audit logs, and draining coin queues) and calls `db.commit()` and `db.close()`.

### Why It is Slow
* If 30 different players have businesses that produce revenue in a given tick, the tick loop sequentially opens, queries, commits, and closes **30 independent database sessions** in a blocking loop.

---

## 4. NPC Tick Connection Churn (`npc.py`)

Spreading the NPCs across ticks (by increasing the interval from 12 to 48) reduced burst CPU usage, but the individual NPC cycles remain highly database-intensive.

### The Mechanism
* For every NPC processed in a given tick, `_run_npc_cycle()` calls:
  1. `get_spendable_usd(player_id)`: Opens up to **4 separate DB sessions** sequentially to check USD balance, rescue legacy balances from the auth DB, resolve legal tender, and calculate conversions.
  2. `_load_inventory_map(player_id)`: Opens a fresh DB session.
  3. `_load_orders_map(...)`: Opens a fresh DB session per market table.
  4. `_manage_sell_orders()` / `_manage_buy_orders()`: Loops over items and calls `create_order()`, which internally checks blockades, verifies available inventory (another query), and commits.

### Why It is Slow
* Even a small slice of 4–5 NPCs executing in a single tick will check out and release dozens of database connections in a blocking, sequential chain.

---

## 🚀 Brainstorming Recommendations (Fixes)

If we were to optimize this without adding heavy code footprint, here is how we would restructure these hot paths:

1. **Eliminate Tick-Based Order Matching:**
   * Remove the O(N) active order matching loop from `market.py`, `district_market.py`, and `brokerage_order_book.py` ticks entirely.
   * Trust the synchronous matching on order creation. Matching only needs to occur when a new order is inserted, not on a timer.

2. **Align Cache TTL with Tick Cadence:**
   * Increase `_PRICE_CACHE_TTL` in `market.py` from `3.0` to `6.0` (or `10.0`) seconds. 
   * This simple change ensures that the coin peg refresh (running every 5.0 seconds) hits the in-memory cache instead of querying the database.

3. **Pass the Database Session Context:**
   * Refactor balance, inventory, and order book helpers (e.g., `get_spendable_usd`, `convert_to_legal_tender`, `_load_inventory_map`) to accept an optional `db` session argument.
   * If a session is passed, reuse it instead of opening and closing a new connection. This would allow the business production tick and the NPC cycle to run all their logic inside a single, unified database transaction per tick.
