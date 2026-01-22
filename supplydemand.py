"""
supplydemand.py

Algebraic engine for retail consumer businesses.
Implements price elasticity of demand for dynamic sales.
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
        
        Args:
            current_price: The price the retailer is charging
            market_price: The average market price for the item
            elasticity: Price elasticity coefficient (higher = more sensitive to price)
        
        Returns:
            Multiplier for sales wait time (higher = slower sales)
        
        Examples:
            - Price = Market: multiplier = 1.0 (normal sales rate)
            - Price > Market: multiplier > 1.0 (slower sales)
            - Price < Market: multiplier < 1.0 (faster sales)
        """
        if market_price <= 0:
            return 9999.0  # Prevent division by zero
        
        ratio = current_price / market_price
        
        # Exponential delay: as price rises above market, wait time explodes
        # As price drops below market, sales accelerate
        multiplier = math.pow(ratio, elasticity)
        
        # Prevent multiplier from going too low (can't sell faster than instant)
        return max(0.1, multiplier)
    
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
            - result = 0.05 (5% chance per tick)
        """
        if multiplier <= 0:
            return 0.0
        
        adjusted_chance = base_chance / multiplier
        
        # Cap at 100% chance
        return min(1.0, adjusted_chance)
    
    @staticmethod
    def estimate_sales_per_hour(base_chance: float, multiplier: float, ticks_per_hour: int = 3600) -> float:
        """
        Estimate expected number of sales per hour.
        
        Args:
            base_chance: Base probability per tick
            multiplier: Sales multiplier
            ticks_per_hour: Number of ticks in an hour (default 3600 for 1 tick/second)
        
        Returns:
            Expected number of sales per hour
        """
        chance_per_tick = SupplyDemandEngine.calculate_chance_per_tick(base_chance, multiplier)
        return chance_per_tick * ticks_per_hour
    
    @staticmethod
    def optimal_price(market_price: float, elasticity: float, markup_preference: float = 1.1) -> float:
        """
        Calculate an optimal price based on elasticity and desired markup.
        
        Args:
            market_price: Average market price
            elasticity: Price elasticity of demand
            markup_preference: Desired markup multiplier (1.1 = 10% markup)
        
        Returns:
            Suggested retail price
        """
        # For elastic goods (elasticity > 1), stay closer to market price
        # For inelastic goods (elasticity < 1), can charge higher markup
        if elasticity > 1.5:
            # Elastic: small markup
            return market_price * min(markup_preference, 1.05)
        elif elasticity < 0.8:
            # Inelastic: larger markup possible
            return market_price * min(markup_preference, 1.25)
        else:
            # Moderate elasticity
            return market_price * markup_preference


# ==========================
# PUBLIC API
# ==========================
__all__ = [
    'SupplyDemandEngine'
]
