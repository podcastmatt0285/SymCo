#!/usr/bin/env python3
"""
Fix patch 2 — closes all remaining gaps found in verification:
1. Add 9 consumed-but-missing items to item_types.json
2. Add bismuth + antimony metal items
3. Fix ammunition_crate: wood → lumber
4. Add chemical production lines for orphaned chemical items
5. Add electric/hybrid vehicle lines to auto_assembly, bus_factory, truck_factory
6. Fix existing tank recipe to use new proper components
"""
import json

def line(output_item, output_qty, inputs):
    return {
        "output_item": output_item,
        "output_qty": output_qty,
        "inputs": [{"item": i, "quantity": q} for i, q in inputs]
    }

with open("item_types.json") as f:
    items = json.load(f)
with open("business_types.json") as f:
    biz = json.load(f)
with open("district_businesses.json") as f:
    dbiz = json.load(f)

# ── 1. Add missing items ──────────────────────────────────────────────────────
NEW_ITEMS_2 = {
    "bismuth":          {"name":"Bismuth",           "category":"metals",    "description":"Soft, low-toxicity heavy metal; used in cosmetics, pharmaceuticals, and lead-free alloys."},
    "antimony":         {"name":"Antimony",          "category":"metals",    "description":"Metalloid used in lead-acid batteries, flame retardants, and alloy hardeners."},
    "machine_gun":      {"name":"Machine Gun",       "category":"military",  "description":"Belt-fed automatic weapon for sustained fire in military applications."},
    "aramid_fabric":    {"name":"Aramid Fabric",     "category":"materials", "description":"Woven para-aramid textile; primary layer in soft body armor vests."},
    "arsenic":          {"name":"Arsenic",           "category":"metals",    "description":"Metalloid refined from copper/gold smelting; used in GaAs semiconductor compounds."},
    "boric_acid":       {"name":"Boric Acid",        "category":"materials", "description":"H3BO3; used in boron carbide production, flame retardants, and glass."},
    "boron":            {"name":"Boron",             "category":"metals",    "description":"Non-metal element used in neodymium magnets, boron carbide armor, and nuclear control rods."},
    "nylon":            {"name":"Nylon",             "category":"materials", "description":"Polyamide synthetic polymer; used in body armor carriers, parachutes, and ropes."},
    "polycarbonate":    {"name":"Polycarbonate",     "category":"materials", "description":"Tough transparent thermoplastic; used in ballistic glazing and riot shields."},
    "silicon_steel":    {"name":"Silicon Steel",     "category":"metals",    "description":"Electrical steel alloyed with silicon; used in transformer and motor cores."},
    "steam":            {"name":"Steam",             "category":"industrial","description":"High-pressure steam; process heat and activation agent in industrial chemical production."},
}

added = 0
for k, v in NEW_ITEMS_2.items():
    if k not in items:
        items[k] = v
        added += 1
        print(f"  Added item: {k}")
    else:
        print(f"  Skip (exists): {k}")
print(f"Added {added} new items")

# ── 2. Fix ammunition_crate: wood → lumber ────────────────────────────────────
wf_lines = dbiz["weapons_factory"]["production_lines"]
for i, l in enumerate(wf_lines):
    if l.get("output_item") == "ammunition_crate":
        for inp in l["inputs"]:
            if inp["item"] == "wood":
                inp["item"] = "lumber"
                print(f"Fixed weapons_factory ammunition_crate: wood → lumber")
                break

# ── 3. Add chemical production lines to chemical_plant for orphaned chemicals ─
chem_lines = dbiz["chemical_plant"]["production_lines"]
existing_chem = {l["output_item"] for l in chem_lines}

NEW_CHEM_LINES = [
    # acetone: from propylene (from oil_refinery plastic stream) or petrochemical
    line("acetone",              400, [("plastic",200),("sulfuric_acid",100),("energy",20000),("paper",15)]),
    # acrylonitrile: from propylene + ammonia (Sohio process)
    line("acrylonitrile",        300, [("ammonia",200),("plastic",200),("energy",30000),("paper",20)]),
    # cellulose: extracted from wood pulp
    line("cellulose",            500, [("lumber",400),("caustic_soda",100),("water",500),("energy",25000),("paper",20)]),
    # glycerin: from bio_fuel/biodiesel production
    line("glycerin",             300, [("bio_fuel",400),("caustic_soda",100),("energy",15000),("paper",10)]),
    # hydrogen_peroxide: anthraquinone process
    line("hydrogen_peroxide",    300, [("water",300),("energy",40000),("paper",20)]),
    # phenylenediamine: from nitrobenzene reduction
    line("phenylenediamine",     200, [("nitric_acid",200),("ammonia",200),("energy",50000),("paper",30)]),
    # potassium_hydroxide: from potash
    line("potassium_hydroxide",  400, [("potash_ore",300),("water",200),("energy",30000),("paper",18)]),
    # terephthaloyl_chloride: from terephthalic acid + chlorine
    line("terephthaloyl_chloride",200,[("chlorine",200),("phosphoric_acid",100),("energy",40000),("paper",25)]),
    # steam: from water + energy (co-generation)
    line("steam",                1000,[("water",500),("energy",10000),("paper",5)]),
    # boric_acid: from borax minerals
    line("boric_acid",           300, [("potash_ore",200),("sulfuric_acid",100),("water",200),("energy",15000),("paper",10)]),
    # arsenic: recovered from copper/gold smelter flue dust
    line("arsenic",               50, [("copper_ore",500),("sulfuric_acid",100),("energy",80000),("paper",40)]),
    # boron: reduced from boric acid
    line("boron",                100, [("boric_acid",300),("energy",60000),("paper",30)]),
    # silicon_steel: allow formation
    line("silicon_steel",        300, [("iron",300),("silicon",50),("energy",60000),("paper",30)]),
    # nylon: from adipic acid (simplified: plastic + ammonia + energy)
    line("nylon",                300, [("plastic",200),("ammonia",100),("energy",40000),("paper",25)]),
    # polycarbonate: from bisphenol A + chlorine
    line("polycarbonate",        250, [("plastic",200),("chlorine",100),("energy",35000),("paper",22)]),
    # aramid_fabric: woven from kevlar_fiber
    line("aramid_fabric",        200, [("kevlar_fiber",300),("energy",20000),("paper",15)]),
]

added_chem = 0
for nl in NEW_CHEM_LINES:
    if nl["output_item"] not in existing_chem:
        chem_lines.append(nl)
        existing_chem.add(nl["output_item"])
        added_chem += 1
print(f"Added {added_chem} chemical production lines to chemical_plant")

# ── 4. Add machine_gun to weapons_factory ────────────────────────────────────
wf_outputs = {l["output_item"] for l in dbiz["weapons_factory"]["production_lines"]}
if "machine_gun" not in wf_outputs:
    dbiz["weapons_factory"]["production_lines"].append(
        line("machine_gun", 50, [("stainless_steel",200),("steel",100),("rifle_barrel",20),("energy",50000),("paper",40)])
    )
    print("Added machine_gun to weapons_factory")

# ── 5. Add electric/hybrid vehicles to auto_assembly ─────────────────────────
aa_outputs = {l["output_item"] for l in biz["auto_assembly"]["production_lines"]}

EV_LINES = [
    line("electric_car",   4, [("chassis",1),("transmission",1),("tires",4),("windshield",1),("headlights",1),
                                ("lithium_battery_pack",2),("copper_wire",100),("car_seat",1),("steering_wheel",1),
                                ("glass",1),("neodymium_magnet",10),("energy",80000),("paper",20)]),
    line("hybrid_car",     4, [("chassis",1),("engine",1),("transmission",1),("tires",4),("windshield",1),
                                ("headlights",1),("lithium_nmc_cell",20),("copper_wire",80),("car_seat",1),
                                ("steering_wheel",1),("glass",1),("energy",70000),("paper",20)]),
    line("hydrogen_vehicle",2,[("chassis",1),("hydrogen_fuel_cell",1),("transmission",1),("tires",4),
                                ("windshield",1),("headlights",1),("copper_wire",100),("car_seat",1),
                                ("steering_wheel",1),("glass",1),("energy",100000),("paper",25)]),
]

added_ev = 0
for nl in EV_LINES:
    if nl["output_item"] not in aa_outputs:
        biz["auto_assembly"]["production_lines"].append(nl)
        added_ev += 1
print(f"Added {added_ev} EV lines to auto_assembly")

# ── 6. Add electric_bus to bus_factory, electric_truck to truck_factory ───────
# bus_factory
bus_outputs = {l["output_item"] for l in dbiz["bus_factory"]["production_lines"]}
if "electric_bus" not in bus_outputs:
    dbiz["bus_factory"]["production_lines"].append(
        line("electric_bus", 2, [("bus_chassis",1),("transmission",1),("tires",6),("windshield",1),
                                  ("lithium_battery_pack",4),("copper_wire",200),("neodymium_magnet",20),
                                  ("glass",2),("energy",150000),("paper",40)])
    )
    print("Added electric_bus to bus_factory")

# truck_factory
truck_outputs = {l["output_item"] for l in dbiz["truck_factory"]["production_lines"]}
if "electric_truck" not in truck_outputs:
    dbiz["truck_factory"]["production_lines"].append(
        line("electric_truck", 3, [("chassis",1),("transmission",1),("tires",6),("windshield",1),
                                    ("lithium_battery_pack",4),("copper_wire",200),("neodymium_magnet",20),
                                    ("glass",1),("energy",120000),("paper",35)])
    )
    print("Added electric_truck to truck_factory")

# ── 7. Add boron/arsenic/silicon_steel/nylon/polycarbonate to alloy_forge too ─
alloy_outputs = {l["output_item"] for l in dbiz["alloy_forge"]["production_lines"]}

ALLOY_FORGE_EXTRA = [
    line("silicon_steel", 300, [("iron",300),("silicon",50),("energy",60000),("paper",30)]),
]
for nl in ALLOY_FORGE_EXTRA:
    if nl["output_item"] not in alloy_outputs:
        dbiz["alloy_forge"]["production_lines"].append(nl)

# ── 8. Save files ─────────────────────────────────────────────────────────────
with open("item_types.json","w") as f:
    json.dump(items, f, indent=2, sort_keys=True)
print("Saved item_types.json")

with open("business_types.json","w") as f:
    json.dump(biz, f, indent=2, sort_keys=True)
print("Saved business_types.json")

with open("district_businesses.json","w") as f:
    json.dump(dbiz, f, indent=2, sort_keys=True)
print("Saved district_businesses.json")

print("\n=== FIX PATCH 2 DONE ===")
