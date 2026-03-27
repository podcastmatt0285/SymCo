import pandas as pd
import time
# Load JSON and export to CSV
pd.read_json('business_types.json').to_csv('business_types_json.csv', index=False)
pd.read_json('district_businesses.json').to_csv('district_businesses_json.csv', index=False)
pd.read_json('district_items.json').to_csv('district_items_json.csv', index=False)
pd.read_json('item_types.json').to_csv('item_types_json.csv', index=False)

# 1. Print confirmation
print("Task completed. Closing in 5 seconds...")

# 2. Wait a moment (e.g., 3 seconds)
time.sleep(5)

# 3. Close (Script exits naturally here)
print("Goodbye!")

