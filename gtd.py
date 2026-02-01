import json
from collections import defaultdict

BUSINESS_FILE = "district_businesses.json"

def prettify_name(key):
    return key.replace("_", " ").title()

def find_allowed_terrain(node, results):
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "allowed_terrain" and isinstance(v, list):
                for terrain in v:
                    if isinstance(terrain, str) and terrain.startswith("district_"):
                        key = terrain.replace("district_", "")
                        results.add(key)
            else:
                find_allowed_terrain(v, results)

    elif isinstance(node, list):
        for item in node:
            find_allowed_terrain(item, results)

def generate_district_types():
    with open(BUSINESS_FILE, "r") as f:
        data = json.load(f)

    districts = set()
    find_allowed_terrain(data, districts)

    print("DISTRICT_TYPES = {")
    for key in sorted(districts):
        name = prettify_name(key)

        print(f'    "{key}": {{')
        print(f'        "name": "{name}",')
        print(f'        "description": "{name} district",')
        print(f'        "allowed_terrain": ["prairie"],')
        print(f'        "base_tax": 40000.0')
        print("    },")
    print("}")

if __name__ == "__main__":
    generate_district_types()
