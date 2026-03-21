# NPC Configs

Each `.json` file in this directory defines one NPC. The filename (without `.json`)
is the NPC's `config_key`. Files are loaded alphabetically on startup.

## Schema

```json
{
  "player_id": -2001,
  "business_name": "Example Goods Co.",
  "description": "Short description of what this NPC does in the economy.",

  "cash_caps": {
    "hard_high": 25000000,
    "soft_high": 21000000,
    "soft_low":  11000000,
    "hard_low":   6000000
  },

  "seed": {
    "starting_cash": 75000,
    "starting_inventory": {
      "water": 500
    },
    "land_plots": [
      { "terrain_type": "prairie", "size": 1, "efficiency": 100 }
    ]
  },

  "businesses": [
    {
      "business_type": "grain_farm",
      "district_id": null
    }
  ],

  "sell_items": {
    "wheat": {
      "min_inventory_to_keep": 100,
      "max_order_quantity": 500,
      "market": "regular"
    }
  },

  "buy_items": {
    "water": {
      "max_price_multiplier": 1.10,
      "target_inventory": 300,
      "reorder_at": 50,
      "market": "regular"
    }
  }
}
```

## Notes
- `player_id` must be a unique negative integer. Use -2001, -2002, -2003, etc.
- `market` field on buy/sell items: `"regular"` (default) or `"district"`
- Land plots are assigned to businesses in order — first plot to first business, etc.
- NPC accounts are never shown on leaderboards and cannot log in.
- Seed data is only applied once (on first startup when the account doesn't exist).
