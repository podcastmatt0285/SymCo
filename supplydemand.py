"""
supplydemand.py

Algebraic engine for retail consumer businesses.
Implements price elasticity of demand for dynamic sales.

ELASTICITY GUIDE (what values mean for items):
  < 0.5  — Highly inelastic: near-necessities like medicine, utilities, staple foods.
            Customers barely react to price changes; you can charge above market with
            little sales impact.  Use sparingly — few goods truly behave this way.
  0.5-1.0 — Moderately inelastic: everyday goods with limited substitutes (bread,
            fuel, some clothing). Some price sensitivity but demand holds reasonably.
  1.0-1.5 — Moderately elastic: normal discretionary goods (produce, electronics,
            standard vehicles). Customers notice price and will compare/delay purchases.
  > 1.5  — Highly elastic: luxury or easily-substituted items (candles, fashion,
            recreational boats, exotic pets). Even a small price premium tanks sales.

BASE_SALE_CHANCE GUIDE (per-item probability each production cycle):
  > 0.05  — Fast-moving consumables: food, beverages, newspapers.
  0.01-0.05 — Regular goods: clothing, books, household items.
  0.001-0.01 — Slow-moving goods: electronics, motorcycles, standard cars.
  < 0.001 — Capital / luxury goods: luxury cars, yachts, specialty equipment.
            A single unit might sell once per day or less.
"""

import math



class SupplyDemandEngine:
    """
    Supply and demand calculator for retail businesses.
    Uses price elasticity of demand to determine sales probability.
    """

    @staticmethod
    def get_sales_multiplier(current_price: float, market_price: float, elasticity: float) -> float:
        """
        Calculates the sales multiplier using Price Elasticity of Demand.

        Formula: (Current Price / Market Price) ^ Elasticity

        The multiplier represents the scaling factor applied to sales wait time:
          - multiplier = 1.0  →  normal sales rate (price equals market)
          - multiplier > 1.0  →  slower sales (price above market)
          - multiplier < 1.0  →  faster sales (price below market / heavy discount)

        Elasticity determines how steeply demand responds to price deviations.
        High elasticity = customers are very price-sensitive (luxury/substitutable goods).
        Low elasticity  = customers barely react to price (necessities/captive market).

        Args:
            current_price: The price the retailer is charging
            market_price: The average market price for the item
            elasticity: Price elasticity coefficient (higher = more sensitive to price)

        Returns:
            Multiplier for sales speed (higher = slower sales)
        """
        if market_price <= 0:
            return 9999.0  # No reference price — treat as unsellable

        if current_price <= 0:
            return 9999.0  # Zero/negative price is invalid

        ratio = current_price / market_price

        # Power-law demand curve: price deviations are amplified by elasticity.
        # Doubling the price on an elastic item (e=2) quadruples the wait time.
        # The same price hike on an inelastic item (e=0.3) barely moves the needle.
        multiplier = math.pow(ratio, elasticity)

        # Floor at 0.05 so even extreme discounts cap at ~20× the base sales rate.
        # This prevents runaway inventory dumps while rewarding competitive pricing.
        return max(0.05, multiplier)

    @staticmethod
    def calculate_chance_per_tick(base_chance: float, multiplier: float) -> float:
        """
        Adjusts the probability of a sale occurring in a single tick.

        Args:
            base_chance: Base probability of sale per tick (at market price)
            multiplier: Sales multiplier from get_sales_multiplier()

        Returns:
            Adjusted probability (0.0 to 1.0)

        Example:
            - base_chance = 0.1 (10% chance per tick at market price)
            - multiplier = 2.0 (price is higher than market)
            - result = 0.05 (5% chance per tick — half as likely to sell)
        """
        if multiplier <= 0:
            return 0.0

        adjusted_chance = base_chance / multiplier

        # Cap at 100% chance per tick
        return min(1.0, adjusted_chance)

    @staticmethod
    def estimate_sales_per_hour(base_chance: float, multiplier: float, ticks_per_hour: int = 3600) -> float:
        """
        Estimate expected number of sales per hour (per unit in inventory).

        Args:
            base_chance: Base probability per tick
            multiplier: Sales multiplier
            ticks_per_hour: Number of ticks in an hour (default 3600 for 1 tick/second)

        Returns:
            Expected number of sales per hour per unit held
        """
        chance_per_tick = SupplyDemandEngine.calculate_chance_per_tick(base_chance, multiplier)
        return chance_per_tick * ticks_per_hour

    @staticmethod
    def optimal_price(market_price: float, elasticity: float, markup_preference: float = 1.1) -> float:
        """
        Calculate an optimal price based on elasticity and desired markup.

        For highly elastic goods you must stay near market price or sales collapse.
        For inelastic goods you have more room to charge a premium.

        Args:
            market_price: Average market price
            elasticity: Price elasticity of demand
            markup_preference: Desired markup multiplier (1.1 = 10% markup)

        Returns:
            Suggested retail price
        """
        if elasticity >= 1.5:
            # Highly elastic: customers will walk if you go over ~2-3% above market
            return market_price * min(markup_preference, 1.03)
        elif elasticity >= 1.0:
            # Moderately elastic: small markup tolerated
            return market_price * min(markup_preference, 1.08)
        elif elasticity >= 0.5:
            # Moderately inelastic: standard markup works
            return market_price * markup_preference
        else:
            # Highly inelastic: larger premium possible without killing demand
            return market_price * min(markup_preference, 1.30)


# ==========================
# PUBLIC API
# ==========================
__all__ = [
    'SupplyDemandEngine'
]
