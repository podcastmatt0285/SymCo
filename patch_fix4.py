#!/usr/bin/env python3
"""
Fix patch 4 — address remaining 68 industrial dead-ends.
Real gaps to fix:
- Remaining rare earths: erbium, terbium, praseodymium, niobium, yttrium, holmium, tellurium
- nitinol, optical_glass, gold_bond_wire, fiber_optic_cable need downstream
- explosive_reactive_armor, marine_piping, aerospace_fastener, power_electronics_module
- refined_ore_concentrate should be consumed by REE processing
- black_powder munitions
- monopropellant, solid_state_battery_pack
"""
import json

def ln(output_item, output_qty, inputs):
    return {"output_item": output_item, "output_qty": output_qty,
            "inputs": [{"item": i, "quantity": q} for i, q in inputs]}

def replace_line(lines, oi, new_line):
    for i, l in enumerate(lines):
        if l.get("output_item") == oi:
            lines[i] = new_line
            return True
    return False

def add_if_missing(lines, new_line):
    if new_line["output_item"] not in {l["output_item"] for l in lines}:
        lines.append(new_line)
        return True
    return False

with open("business_types.json") as f:  biz = json.load(f)
with open("district_businesses.json") as f:  dbiz = json.load(f)
with open("item_types.json") as f:  items = json.load(f)

def add_item(key, name, cat, desc):
    if key not in items:
        items[key] = {"name": name, "category": cat, "description": desc}
        return True
    return False

# ── 1. Remaining rare earth downstream uses ───────────────────────────────────
af_lines = dbiz["alloy_forge"]["production_lines"]
sf_lines = dbiz["semiconductor_fab"]["production_lines"]
rp_lines = dbiz["rare_earth_processor"]["production_lines"]

# praseodymium → NdFeB magnets actually use Nd/Pr interchangeably
# Update neodymium_magnet to also accept praseodymium
replace_line(af_lines, "neodymium_magnet", ln("neodymium_magnet", 150,
    [("neodymium",80),("praseodymium",20),("iron",100),("boron",50),("dysprosium",15),
     ("energy",80000),("paper",50)]))
print("Updated neodymium_magnet → adds praseodymium (realistic NdFeB composition)")

# terbium → LED phosphors; add to lcd_panel alongside europium
replace_line(sf_lines, "lcd_panel", ln("lcd_panel", 100,
    [("glass",500),("microchip",25),("copper_wire",100),
     ("indium",20),("europium",10),("terbium",8),("energy",60000),("paper",60)]))
print("Updated lcd_panel → adds terbium (green phosphors)")

# erbium → fiber_optic_cable (Er-doped optical amplifier fiber)
replace_line(dbiz["scientific_equipment_factory"]["production_lines"], "fiber_optic_cable",
    ln("fiber_optic_cable", 200,
        [("germanium",30),("erbium",10),("glass",300),("plastic",100),
         ("energy",60000),("paper",40)]))
print("Updated fiber_optic_cable → adds erbium (Er-doped amplifier fiber)")

# yttrium → YAG laser / radar magnetron; add to radar_system and scientific equipment
de_lines = dbiz["defense_electronics_factory"]["production_lines"]
replace_line(de_lines, "radar_system", ln("radar_system", 50,
    [("processor",100),("gallium_arsenide",50),("yttrium",20),("copper_wire",200),
     ("titanium",50),("energy",80000),("paper",80)]))
print("Updated radar_system → adds yttrium (YAG magnetron)")

# niobium → maraging_steel (niobium HSLA additive)
replace_line(af_lines, "maraging_steel", ln("maraging_steel", 150,
    [("steel",200),("nickel",100),("cobalt",60),("molybdenum",40),("niobium",20),
     ("energy",120000),("paper",70)]))
print("Updated maraging_steel → adds niobium (HSLA additive)")

# holmium → nuclear_reactor_core (holmium control rod absorber)
eif_lines = dbiz["energy_infrastructure_factory"]["production_lines"]
replace_line(eif_lines, "nuclear_reactor_core", ln("nuclear_reactor_core", 5,
    [("uranium_oxide",500),("zirconium",200),("stainless_steel",300),("holmium",10),
     ("energy",500000),("paper",300)]))
print("Updated nuclear_reactor_core → adds holmium (control rod absorber)")

# tellurium → solar_panel (CdTe thin film; add alongside selenium)
replace_line(eif_lines, "solar_panel", ln("solar_panel", 400,
    [("silicon_wafer",300),("silver",40),("aluminum",150),("glass",200),
     ("selenium",15),("tellurium",15),("energy",60000),("paper",50)]))
print("Updated solar_panel → adds tellurium (CdTe photovoltaic)")

# ── 2. nitinol → surgical stent / medical device ──────────────────────────────
add_item("surgical_stent","Surgical Stent","health",
    "Nitinol self-expanding coronary or vascular stent for interventional cardiology.")
mef_lines = dbiz["medical_equipment_factory"]["production_lines"]
if add_if_missing(mef_lines, ln("surgical_stent", 200,
    [("nitinol",100),("titanium",50),("energy",60000),("paper",40)])):
    print("Added surgical_stent to medical_equipment_factory (uses nitinol)")

# ── 3. optical_glass → targeting_optic and night_vision_optic ─────────────────
ef_lines = dbiz["electronics_factory"]["production_lines"]
replace_line(ef_lines, "targeting_optic", ln("targeting_optic", 100,
    [("optical_glass",80),("circuit_board",30),("copper_wire",50),
     ("energy",30000),("paper",30)]))
replace_line(ef_lines, "night_vision_optic", ln("night_vision_optic", 80,
    [("optical_glass",60),("gallium_arsenide",30),("processor",20),
     ("circuit_board",20),("energy",40000),("paper",40)]))
replace_line(de_lines, "targeting_optic", ln("targeting_optic", 100,
    [("optical_glass",80),("circuit_board",30),("copper_wire",50),
     ("energy",30000),("paper",30)]))
replace_line(de_lines, "night_vision_optic", ln("night_vision_optic", 80,
    [("optical_glass",60),("gallium_arsenide",30),("processor",20),
     ("circuit_board",20),("energy",40000),("paper",40)]))
print("Updated targeting_optic + night_vision_optic → use optical_glass")

# ── 4. gold_bond_wire → consumed by microchip and processor ───────────────────
replace_line(sf_lines, "microchip", ln("microchip", 200,
    [("silicon_wafer",300),("gallium",50),("gold_bond_wire",20),
     ("hydrofluoric_acid",100),("energy",100000),("water",5000),("paper",100)]))
replace_line(sf_lines, "processor", ln("processor", 100,
    [("microchip",50),("copper",200),("gold_bond_wire",10),
     ("energy",80000),("paper",80)]))
print("Updated microchip + processor → consume gold_bond_wire")

# ── 5. fiber_optic_cable → consumed by data_center and telecom ────────────────
dc_lines = dbiz["data_center"]["production_lines"]
# Update data_center to use fiber_optic_cable
for l in dc_lines:
    if l["output_item"] == "compute_credit":
        if "fiber_optic_cable" not in [x["item"] for x in l["inputs"]]:
            l["inputs"].append({"item":"fiber_optic_cable","quantity":20})
            print("Added fiber_optic_cable to data_center compute_credit line")
        break
for l in dc_lines:
    if l["output_item"] == "cloud_storage_unit":
        if "fiber_optic_cable" not in [x["item"] for x in l["inputs"]]:
            l["inputs"].append({"item":"fiber_optic_cable","quantity":15})
            print("Added fiber_optic_cable to data_center cloud_storage_unit line")
        break

# ── 6. explosive_reactive_armor → tank upgrade line ──────────────────────────
mvp_lines = dbiz["military_vehicle_plant"]["production_lines"]
add_item("main_battle_tank","Main Battle Tank (ERA)","vehicles",
    "Main battle tank with explosive reactive armor package for enhanced RPG protection.")
if add_if_missing(mvp_lines, ln("main_battle_tank", 3,
    [("tank_hull",1),("tank_turret",1),("tank_cannon",1),("diesel_engine",2),
     ("fire_control_system",1),("explosive_reactive_armor",40),
     ("composite_armor_panel",20),("copper_wire",200),
     ("energy",500000),("paper",250)])):
    print("Added main_battle_tank (ERA variant) to military_vehicle_plant")

# ── 7. marine_piping → naval_shipyard consumption ─────────────────────────────
ms_lines = dbiz["military_shipyard"]["production_lines"]
replace_line(ms_lines, "destroyer_hull", ln("destroyer_hull", 5,
    [("stainless_steel",2000),("titanium_alloy",500),("aluminum",1000),
     ("marine_piping",50),("energy",2000000),("paper",500)]))
replace_line(ms_lines, "submarine_hull", ln("submarine_hull", 3,
    [("maraging_steel",1500),("titanium_alloy",800),("stainless_steel",1000),
     ("marine_piping",80),("energy",3000000),("paper",600)]))
# Also commercial shipyard
sy_lines = dbiz["shipyard"]["production_lines"]
for l in sy_lines:
    if l["output_item"] in ("cargo_ship","tanker","container_ship","cruise_ship"):
        if "marine_piping" not in [x["item"] for x in l["inputs"]]:
            l["inputs"].append({"item":"marine_piping","quantity":40})
            print(f"Added marine_piping to shipyard {l['output_item']}")
        break
print("Updated naval hulls → use marine_piping")

# ── 8. aerospace_fastener → aircraft_assembly and jet_engine_factory ──────────
ac_lines = dbiz["aircraft_assembly"]["production_lines"]
for l in ac_lines:
    if "aerospace_fastener" not in [x["item"] for x in l.get("inputs",[])]:
        l["inputs"].append({"item":"aerospace_fastener","quantity":50})
jef_lines = dbiz["jet_engine_factory"]["production_lines"]
for l in jef_lines:
    if l["output_item"] in ("turbojet_engine","turbofan_engine"):
        if "aerospace_fastener" not in [x["item"] for x in l["inputs"]]:
            l["inputs"].append({"item":"aerospace_fastener","quantity":30})
print("Added aerospace_fastener to aircraft_assembly and jet engines")

# ── 9. power_electronics_module → EV and grid uses ───────────────────────────
# Add to electric_car and electric_bus
aa_lines = biz["auto_assembly"]["production_lines"]
for l in aa_lines:
    if l["output_item"] == "electric_car":
        if "power_electronics_module" not in [x["item"] for x in l["inputs"]]:
            l["inputs"].append({"item":"power_electronics_module","quantity":2})
            print("Added power_electronics_module to electric_car")
        break

# ── 10. monopropellant → rocket_motor upgrade ─────────────────────────────────
# Update rocket_motor to have a monopropellant variant
jef_outs = {l["output_item"] for l in jef_lines}
add_item("liquid_rocket_engine","Liquid Rocket Engine","components",
    "Bipropellant liquid rocket engine for launch vehicles and upper stages.")
if add_if_missing(jef_lines, ln("liquid_rocket_engine", 20,
    [("rocket_motor",10),("monopropellant",200),("titanium_alloy",100),
     ("inconel",100),("energy",300000),("paper",200)])):
    print("Added liquid_rocket_engine to jet_engine_factory (uses monopropellant)")

# ── 11. solid_state_battery_pack → premium EV ─────────────────────────────────
add_item("premium_ev","Premium Electric Vehicle","vehicles",
    "High-performance solid-state battery electric vehicle with extended range.")
if add_if_missing(aa_lines, ln("premium_ev", 2,
    [("chassis",1),("transmission",1),("tires",4),("windshield",1),
     ("solid_state_battery_pack",2),("power_electronics_module",4),
     ("neodymium_magnet",20),("copper_wire",200),("car_seat",1),
     ("steering_wheel",1),("glass",1),("energy",120000),("paper",30)])):
    print("Added premium_ev to auto_assembly (uses solid_state_battery_pack)")

# ── 12. black_powder → consumed by munitions_depot ───────────────────────────
md_lines = dbiz["munitions_depot"]["production_lines"]
print("\nmunitions_depot existing lines:")
for l in md_lines:
    print(f"  {l['output_item']}: {[x['item'] for x in l['inputs'][:3]]}")
md_outs = {l["output_item"] for l in md_lines}
# black_powder is a classic propellant; add a black_powder_charge round
add_item("artillery_shell","Artillery Shell","military",
    "Large-caliber howitzer round with smokeless or black powder propellant charge.")
if add_if_missing(md_lines, ln("artillery_shell", 100,
    [("steel",200),("rdx_explosive",100),("black_powder",100),
     ("brass",100),("energy",30000),("paper",25)])):
    print("Added artillery_shell to munitions_depot (uses black_powder)")

# Also: self_propelled_artillery should consume artillery_shell
for l in dbiz["military_vehicle_plant"]["production_lines"]:
    if l["output_item"] == "self_propelled_artillery":
        if "artillery_shell" not in [x["item"] for x in l["inputs"]]:
            l["inputs"].append({"item":"artillery_shell","quantity":20})
            print("Added artillery_shell to self_propelled_artillery recipe")
        break

# ── 13. refined_ore_concentrate → feed back into REE lines ────────────────────
# Update a few REE lines to also accept refined_ore_concentrate as alternative
# Add a second processing pass using the concentrate
rp_outs = {l["output_item"] for l in rp_lines}
add_item("mixed_rare_earth_oxide","Mixed Rare Earth Oxide","materials",
    "Partially separated mixed rare earth oxide precipitate; intermediate in REE refining.")
if add_if_missing(rp_lines, ln("mixed_rare_earth_oxide", 300,
    [("refined_ore_concentrate",200),("sulfuric_acid",150),("caustic_soda",100),
     ("energy",60000),("water",2000),("paper",40)])):
    print("Added mixed_rare_earth_oxide to rare_earth_processor (uses refined_ore_concentrate)")
# Make mixed_rare_earth_oxide an alternative input to some REE lines
if add_if_missing(rp_lines, ln("neodymium", 40,
    [("mixed_rare_earth_oxide",200),("sulfuric_acid",100),("energy",80000),("paper",40)])):
    print("Added neodymium line from mixed_rare_earth_oxide")
if add_if_missing(rp_lines, ln("lanthanum", 30,
    [("mixed_rare_earth_oxide",150),("hydrochloric_acid",80),("energy",70000),("paper",35)])):
    print("Added lanthanum line from mixed_rare_earth_oxide")

# ── 14. nails → consumed by construction / furniture ─────────────────────────
# Nails should be consumed by furniture/wood products
lumber_lines = biz["lumber_mill"]["production_lines"]
for l in lumber_lines:
    if "nails" not in [x["item"] for x in l.get("inputs",[])]:
        pass  # lumber_mill produces nails? No, fastener_factory does.
# Add nails to chassis_factory
cf_lines = biz["chassis_factory"]["production_lines"]
for l in cf_lines:
    if "nails" not in [x["item"] for x in l.get("inputs",[])]:
        l["inputs"].append({"item":"nails","quantity":20})
        print(f"Added nails to chassis_factory {l['output_item']}")
        break

# envelope → packaging at bookbindery - ok as end product
# rice_sack → packaging at rope_works - ok as end product

# ── Save all files ────────────────────────────────────────────────────────────
with open("item_types.json","w") as f:
    json.dump(items, f, indent=2, sort_keys=True)
with open("business_types.json","w") as f:
    json.dump(biz, f, indent=2, sort_keys=True)
with open("district_businesses.json","w") as f:
    json.dump(dbiz, f, indent=2, sort_keys=True)
print("\nAll files saved.")
