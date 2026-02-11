"""
production_costs.py

Production Cost Calculator for Wadsworth.
Calculates base production costs assuming full vertical integration.

Handles circular dependencies (e.g., paper <-> water) via iterative convergence.

Usage in UX:
    from production_costs import get_calculator
    calc = get_calculator()
    costs = calc.get_all_costs()
"""

import json
from collections import defaultdict
from pathlib import Path
from typing import Optional

# ==========================
# CONFIGURATION
# ==========================

# Default paths - adjust based on your project structure
DEFAULT_BUSINESS_TYPES = "business_types.json"
DEFAULT_DISTRICT_BUSINESSES = "district_businesses.json"
DEFAULT_ITEM_TYPES = "item_types.json"
DEFAULT_DISTRICT_ITEMS = "district_items.json"


class ProductionCostCalculator:
    """Calculate base production costs for all items with vertical integration."""
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize calculator.
        
        Args:
            config_dir: Directory containing JSON config files. 
                       Defaults to current working directory.
        """
        self.config_dir = config_dir or Path.cwd()
        self.recipes = defaultdict(list)
        self.item_types = {}
        self.cost_cache = {}
        self.recipe_used = {}
        self.missing_items = set()
        self._loaded = False
    
    def _ensure_loaded(self):
        """Lazy load configs on first access."""
        if self._loaded:
            return
        self._load_configs()
        self._build_recipe_graph()
        self._calculate_all_costs()
        self._loaded = True
    
    def _load_configs(self):
        """Load all configuration files."""
        # Load business types
        bt_path = self.config_dir / DEFAULT_BUSINESS_TYPES
        try:
            with open(bt_path, 'r') as f:
                self.business_types = json.load(f)
        except FileNotFoundError:
            print(f"[ProductionCosts] Warning: {bt_path} not found")
            self.business_types = {}
        
        # Merge district businesses
        db_path = self.config_dir / DEFAULT_DISTRICT_BUSINESSES
        try:
            with open(db_path, 'r') as f:
                district_biz = json.load(f)
            self.business_types.update(district_biz)
        except FileNotFoundError:
            pass
        
        # Load item types
        it_path = self.config_dir / DEFAULT_ITEM_TYPES
        try:
            with open(it_path, 'r') as f:
                self.item_types = json.load(f)
        except FileNotFoundError:
            self.item_types = {}
        
        # Merge district items
        di_path = self.config_dir / DEFAULT_DISTRICT_ITEMS
        try:
            with open(di_path, 'r') as f:
                district_items = json.load(f)
            self.item_types.update(district_items)
        except FileNotFoundError:
            pass
    
    def _build_recipe_graph(self):
        """Build production recipe graph from business types."""
        for biz_key, biz_data in self.business_types.items():
            # Skip comment entries
            if not isinstance(biz_data, dict):
                continue
            if biz_data.get('class') != 'production':
                continue
            
            wage = biz_data.get('base_wage_cost', 0)
            
            for line in biz_data.get('production_lines', []):
                output = line.get('output_item')
                if not output:
                    continue
                    
                output_qty = line.get('output_qty', 1)
                inputs = {
                    inp['item']: inp['quantity'] 
                    for inp in line.get('inputs', [])
                }
                
                self.recipes[output].append({
                    'wage': wage,
                    'output_qty': output_qty,
                    'inputs': inputs,
                    'business_key': biz_key,
                    'business_name': biz_data.get('name', biz_key)
                })
    
    def _calculate_all_costs(self, max_iterations=50, tolerance=0.0001):
        """
        Calculate costs for all items using iterative approach.
        Handles circular dependencies by iterating until convergence.
        """
        # Get all items (outputs and inputs)
        all_items = set(self.recipes.keys())
        for recipes in self.recipes.values():
            for recipe in recipes:
                all_items.update(recipe['inputs'].keys())
        
        # Initialize costs to 0
        for item in all_items:
            self.cost_cache[item] = 0.0
        
        # Iteratively calculate until convergence
        for iteration in range(max_iterations):
            max_change = 0.0
            
            for item in all_items:
                if item not in self.recipes:
                    self.missing_items.add(item)
                    continue
                
                # Find cheapest recipe with current costs
                min_cost = float('inf')
                best_recipe = None
                
                for recipe in self.recipes[item]:
                    batch_cost = recipe['wage']
                    
                    for inp_item, inp_qty in recipe['inputs'].items():
                        batch_cost += self.cost_cache.get(inp_item, 0) * inp_qty
                    
                    unit_cost = batch_cost / recipe['output_qty']
                    
                    if unit_cost < min_cost:
                        min_cost = unit_cost
                        best_recipe = recipe
                
                # Track change
                old_cost = self.cost_cache[item]
                change = abs(min_cost - old_cost)
                max_change = max(max_change, change)
                
                # Update
                self.cost_cache[item] = min_cost
                self.recipe_used[item] = best_recipe
            
            # Check convergence
            if max_change < tolerance:
                break
        
        return self.cost_cache
    
    # ==========================
    # PUBLIC API
    # ==========================
    
    def get_cost(self, item: str) -> float:
        """Get cost for a specific item."""
        self._ensure_loaded()
        return self.cost_cache.get(item, 0.0)
    
    def get_all_costs(self) -> dict:
        """Get all calculated costs."""
        self._ensure_loaded()
        return self.cost_cache.copy()
    
    def get_item_name(self, item_key: str) -> str:
        """Get display name for an item."""
        self._ensure_loaded()
        if item_key in self.item_types:
            item_data = self.item_types[item_key]
            if isinstance(item_data, dict):
                return item_data.get('name', item_key.replace('_', ' ').title())
        return item_key.replace('_', ' ').title()
    
    def get_item_category(self, item_key: str) -> str:
        """Get category for an item."""
        self._ensure_loaded()
        if item_key in self.item_types:
            item_data = self.item_types[item_key]
            if isinstance(item_data, dict):
                return item_data.get('category', 'unknown')
        return 'unknown'
    
    def get_cost_breakdown(self, item: str) -> dict:
        """Get detailed cost breakdown for an item."""
        self._ensure_loaded()
        
        recipe = self.recipe_used.get(item)
        if not recipe:
            return {
                'item_key': item,
                'name': self.get_item_name(item),
                'cost': 0,
                'has_recipe': False,
                'is_missing': item in self.missing_items
            }
        
        input_costs = []
        total_input_cost = 0
        for inp_item, inp_qty in recipe['inputs'].items():
            inp_unit_cost = self.cost_cache.get(inp_item, 0)
            inp_total = inp_unit_cost * inp_qty
            total_input_cost += inp_total
            input_costs.append({
                'item_key': inp_item,
                'name': self.get_item_name(inp_item),
                'quantity': inp_qty,
                'unit_cost': inp_unit_cost,
                'total_cost': inp_total
            })
        
        # Sort inputs by total cost descending
        input_costs.sort(key=lambda x: x['total_cost'], reverse=True)
        
        return {
            'item_key': item,
            'name': self.get_item_name(item),
            'category': self.get_item_category(item),
            'cost': self.cost_cache[item],
            'has_recipe': True,
            'business_key': recipe['business_key'],
            'business_name': recipe['business_name'],
            'wage': recipe['wage'],
            'output_qty': recipe['output_qty'],
            'inputs': input_costs,
            'total_input_cost': total_input_cost,
            'batch_cost': recipe['wage'] + total_input_cost,
            'wage_pct': (recipe['wage'] / (recipe['wage'] + total_input_cost) * 100) if (recipe['wage'] + total_input_cost) > 0 else 0
        }
    
    def get_all_items_sorted(self, sort_by='cost', ascending=True) -> list:
        """Get all items with full data, sorted."""
        self._ensure_loaded()
        
        results = []
        for item, cost in self.cost_cache.items():
            results.append({
                'item_key': item,
                'name': self.get_item_name(item),
                'category': self.get_item_category(item),
                'cost': cost,
                'has_recipe': item in self.recipes,
                'business': self.recipe_used.get(item, {}).get('business_name', None) if item in self.recipe_used else None
            })
        
        reverse = not ascending
        if sort_by == 'cost':
            results.sort(key=lambda x: x['cost'], reverse=reverse)
        elif sort_by == 'name':
            results.sort(key=lambda x: x['name'].lower(), reverse=reverse)
        elif sort_by == 'category':
            results.sort(key=lambda x: (x['category'], x['cost']), reverse=reverse)
        
        return results
    
    def get_by_category(self) -> dict:
        """Get items grouped by category."""
        self._ensure_loaded()
        
        categories = defaultdict(list)
        for item, cost in self.cost_cache.items():
            cat = self.get_item_category(item)
            categories[cat].append({
                'item_key': item,
                'name': self.get_item_name(item),
                'cost': cost,
                'has_recipe': item in self.recipes
            })
        
        # Sort items within each category by cost
        for cat in categories:
            categories[cat].sort(key=lambda x: x['cost'])
        
        return dict(categories)
    
    def get_categories(self) -> list:
        """Get list of all categories."""
        self._ensure_loaded()
        categories = set()
        for item in self.cost_cache:
            categories.add(self.get_item_category(item))
        return sorted(categories)
    
    def get_summary(self) -> dict:
        """Get summary statistics."""
        self._ensure_loaded()
        
        costs = [c for c in self.cost_cache.values() if c > 0]
        
        if not costs:
            return {'total_items': 0}
        
        costs_sorted = sorted(costs)
        
        # Find cheapest and most expensive
        all_items = self.get_all_items_sorted(sort_by='cost', ascending=True)
        cheapest = [i for i in all_items if i['cost'] > 0][:5]
        most_expensive = all_items[-5:][::-1]
        
        return {
            'total_items': len(self.cost_cache),
            'items_with_recipes': len(self.recipes),
            'missing_items': list(self.missing_items),
            'min_cost': min(costs),
            'max_cost': max(costs),
            'median_cost': costs_sorted[len(costs_sorted) // 2],
            'avg_cost': sum(costs) / len(costs),
            'under_1': sum(1 for c in costs if c < 1),
            'under_10': sum(1 for c in costs if c < 10),
            'under_100': sum(1 for c in costs if c < 100),
            'over_1000': sum(1 for c in costs if c >= 1000),
            'over_10000': sum(1 for c in costs if c >= 10000),
            'cheapest': cheapest,
            'most_expensive': most_expensive
        }
    
    def search_items(self, query: str) -> list:
        """Search items by name or key."""
        self._ensure_loaded()
        query_lower = query.lower()
        
        results = []
        for item, cost in self.cost_cache.items():
            name = self.get_item_name(item)
            if query_lower in item.lower() or query_lower in name.lower():
                results.append({
                    'item_key': item,
                    'name': name,
                    'category': self.get_item_category(item),
                    'cost': cost,
                    'has_recipe': item in self.recipes
                })
        
        results.sort(key=lambda x: x['cost'])
        return results


# ==========================
# SINGLETON INSTANCE
# ==========================

_calculator: Optional[ProductionCostCalculator] = None


def get_calculator(config_dir: Optional[Path] = None) -> ProductionCostCalculator:
    """
    Get or create singleton calculator instance.
    
    Args:
        config_dir: Directory containing config files. Only used on first call.
    """
    global _calculator
    if _calculator is None:
        _calculator = ProductionCostCalculator(config_dir)
    return _calculator


def reset_calculator():
    """Reset calculator (call after config file changes)."""
    global _calculator
    _calculator = None


# ==========================
# CLI INTERFACE
# ==========================

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Calculate Wadsworth production costs')
    parser.add_argument('--item', type=str, help='Get cost for specific item')
    parser.add_argument('--breakdown', type=str, help='Show cost breakdown for item')
    parser.add_argument('--category', type=str, help='Show items in category')
    parser.add_argument('--search', type=str, help='Search items')
    parser.add_argument('--json', action='store_true', help='Output JSON')
    args = parser.parse_args()
    
    calc = ProductionCostCalculator()
    
    if args.item:
        cost = calc.get_cost(args.item)
        print(f"{args.item}: ${cost:.4f}")
    
    elif args.breakdown:
        breakdown = calc.get_cost_breakdown(args.breakdown)
        print(f"\n{breakdown['name']} (${breakdown['cost']:.4f}/unit)")
        if breakdown['has_recipe']:
            print(f"  via {breakdown['business_name']}")
            print(f"  Wage: ${breakdown['wage']:.2f} for {breakdown['output_qty']} units ({breakdown['wage_pct']:.1f}% of cost)")
            if breakdown['inputs']:
                print(f"  Inputs:")
                for inp in breakdown['inputs']:
                    print(f"    {inp['quantity']:,.1f}x {inp['name']} @ ${inp['unit_cost']:.4f} = ${inp['total_cost']:.4f}")
            print(f"  Batch cost: ${breakdown['batch_cost']:.4f}")
        else:
            print(f"  NO RECIPE (raw material)")
    
    elif args.search:
        results = calc.search_items(args.search)
        print(f"\nSearch results for '{args.search}':")
        for item in results[:20]:
            print(f"  {item['name']:<30} ${item['cost']:>12,.4f}  [{item['category']}]")
    
    elif args.category:
        by_cat = calc.get_by_category()
        if args.category in by_cat:
            print(f"\n{args.category.upper()}:")
            for item in by_cat[args.category]:
                print(f"  {item['name']:<30} ${item['cost']:>12,.4f}")
        else:
            print(f"Category '{args.category}' not found.")
            print(f"Available: {', '.join(sorted(by_cat.keys()))}")
    
    elif args.json:
        print(json.dumps({
            'summary': calc.get_summary(),
            'items': calc.get_all_items_sorted()
        }, indent=2))
    
    else:
        # Default: show summary
        summary = calc.get_summary()
        items = calc.get_all_items_sorted()
        
        print("=" * 60)
        print("WADSWORTH PRODUCTION COSTS (Vertical Integration)")
        print("=" * 60)
        print(f"Total items: {summary['total_items']}")
        print(f"With recipes: {summary['items_with_recipes']}")
        print(f"Missing recipes: {', '.join(summary['missing_items']) or 'None'}")
        print()
        
        print("CHEAPEST 10:")
        for item in items[:10]:
            print(f"  {item['name']:<30} ${item['cost']:>10,.4f}")
        
        print("\nMOST EXPENSIVE 10:")
        for item in items[-10:][::-1]:
            print(f"  {item['name']:<30} ${item['cost']:>12,.2f}")
