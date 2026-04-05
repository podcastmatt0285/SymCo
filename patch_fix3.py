#!/usr/bin/env python3
"""
Fix patch 3 — closes 104 industrial orphan outputs:

Priority 1: Fix broken weapon sub-component chains
Priority 2: Update fighter_jet to use jet_airframe + turbojet_engine
Priority 3: Add fertilizer_npk to farms
Priority 4: Add solar/wind/transformer/gas_turbine to power_company capital goods
Priority 5: Add grid battery storage products (lfp_cell, sodium_ion_cell, solid_state_cell)
Priority 6: Fix lcd_panel, solar_panel, neodymium_magnet, duralumin recipes (rare earths)
Priority 7: Add specialty metal uses (bronze, tantalum, gold, antimony, cerium, etc.)
Priority 8: Add power electronics products (GaN, SiC wafers downstream)
Priority 9: Fix lead_acid_battery consumption (car_battery → lead_acid_battery)
Priority 10: Add detcord/white_phosphorus/black_powder munitions consumption
"""
import json

def ln(output_item, output_qty, inputs):
    return {"output_item": output_item, "output_qty": output_qty,
            "inputs": [{"item": i, "quantity": q} for i, q in inputs]}

with open("business_types.json") as f:
    biz = json.load(f)
with open("district_businesses.json") as f:
    dbiz = json.load(f)
with open("item_types.json") as f:
    items = json.load(f)

def replace_line(lines, output_item, new_line):
    for i, l in enumerate(lines):
        if l.get("output_item") == output_item:
            lines[i] = new_line
            return True
    return False

def add_if_missing(lines, new_line):
    existing = {l["output_item"] for l in lines}
    if new_line["output_item"] not in existing:
        lines.append(new_line)
        return True
    return False

def add_item_if_missing(key, name, category, description):
    if key not in items:
        items[key] = {"name": name, "category": category, "description": description}
        return True
    return False

# ── PRIORITY 1: Fix weapon sub-component chains ───────────────────────────────
wf = dbiz["weapons_factory"]["production_lines"]

# grenade: add grenade_body as the body, smokeless_powder as propellant
replace_line(wf, "grenade", ln("grenade", 300,
    [("grenade_body",200),("smokeless_powder",100),("det_cord",20),("energy",15000),("paper",15)]))
print("Fixed grenade recipe → uses grenade_body + smokeless_powder + det_cord")

# missile: use missile_warhead + rocket_motor + missile_guidance_unit
replace_line(wf, "missile", ln("missile", 30,
    [("missile_warhead",20),("rocket_motor",15),("missile_guidance_unit",20),
     ("maraging_steel",100),("jet_fuel",50),("energy",100000),("paper",80)]))
print("Fixed missile recipe → uses missile_warhead + rocket_motor + guidance")

# rifle: use rifle_barrel + rifle_receiver
replace_line(wf, "rifle", ln("rifle", 200,
    [("rifle_barrel",200),("rifle_receiver",200),("steel",50),
     ("plastic",50),("energy",30000),("paper",30)]))
print("Fixed rifle recipe → uses rifle_barrel + rifle_receiver")

# ── PRIORITY 2: Fix fighter_jet to use jet_airframe + turbojet_engine ─────────
map_lines = dbiz["military_aircraft_plant"]["production_lines"]
replace_line(map_lines, "fighter_jet", ln("fighter_jet", 3,
    [("jet_airframe",1),("turbojet_engine",2),("avionics_suite",1),
     ("fire_control_system",1),("ejection_seat",1),("radar_system",1),
     ("missile",4),("energy",1000000),("paper",500)]))
print("Fixed fighter_jet recipe → uses jet_airframe + turbojet_engine + ejection_seat")

# military_helicopter: use helicopter_rotor  (already done via attack_helicopter)
# update base military_helicopter to also use rotor
replace_line(map_lines, "military_helicopter", ln("military_helicopter", 5,
    [("helicopter_rotor",1),("turbojet_engine",1),("avionics_suite",1),
     ("fire_control_system",1),("missile",2),("energy",500000),("paper",300)]))
print("Fixed military_helicopter recipe → uses helicopter_rotor + turbojet_engine")

# ── PRIORITY 3: Add fertilizer_npk to farms ───────────────────────────────────
# Add a fertilized production line to grain_farm, peanut_farm, cotton_fields
def add_fertilized_variant(farm_key, output_item, output_qty, base_inputs):
    """Add a fertilizer-enhanced line if not already present"""
    farm = biz.get(farm_key)
    if not farm:
        return False
    existing = {l["output_item"] for l in farm["production_lines"]}
    fert_key = f"{output_item}_fertilized" if f"{output_item}_fertilized" not in existing else None
    if fert_key is None:
        return False
    # Add fertilized variant with 25% more output
    farm["production_lines"].append(ln(output_item, int(output_qty*1.3), base_inputs + [("fertilizer_npk",50),("energy",1000)]))
    return True

# Also: add fertilizer_npk as consumed by existing lines (update the main line)
# Simplest: just add to grain_farm main wheat line and peanut line
gf_lines = biz["grain_farm"]["production_lines"]
for i, l in enumerate(gf_lines):
    if l["output_item"] == "wheat" and l["output_qty"] >= 8000:
        # Add fertilizer_npk to the large wheat line if not already there
        inp_items = [x["item"] for x in l["inputs"]]
        if "fertilizer_npk" not in inp_items:
            l["inputs"].append({"item":"fertilizer_npk","quantity":100})
            print(f"Added fertilizer_npk to grain_farm {l['output_item']} (qty={l['output_qty']}) line")
            break

# Add fertilizer to peanut_farm
pf_lines = biz["peanut_farm"]["production_lines"]
for l in pf_lines:
    if l["output_item"] == "peanut" and "fertilizer_npk" not in [x["item"] for x in l["inputs"]]:
        l["inputs"].append({"item":"fertilizer_npk","quantity":80})
        print(f"Added fertilizer_npk to peanut_farm {l['output_item']} line")
        break

# Add fertilizer to cotton_fields
cf_lines = biz["cotton_fields"]["production_lines"]
for l in cf_lines:
    if l["output_item"] == "cotton" and "fertilizer_npk" not in [x["item"] for x in l["inputs"]]:
        l["inputs"].append({"item":"fertilizer_npk","quantity":80})
        print(f"Added fertilizer_npk to cotton_fields {l['output_item']} line")
        break

# ── PRIORITY 4: Add capital goods to power_company ────────────────────────────
pc_lines = dbiz["power_company"]["production_lines"]
pc_outs = {l["output_item"] for l in pc_lines}

POWER_COMPANY_LINES = [
    ln("energy", 50000, [("solar_panel",10),("transformer",2),("copper_wire",200),("energy",5000),("paper",10)]),
    ln("energy", 80000, [("wind_turbine_blade",5),("transformer",3),("steel",100),("copper_wire",300),("energy",5000),("paper",15)]),
    ln("energy", 120000,[("gas_turbine",1),("natural_gas",500),("transformer",2),("copper_wire",200),("energy",10000),("paper",20)]),
    ln("energy", 200000,[("nuclear_reactor_core",1),("uranium_oxide",100),("transformer",5),("copper_wire",500),("energy",20000),("paper",50)]),
]
added_pc = 0
for nl in POWER_COMPANY_LINES:
    # Each produces energy but with different inputs — add as distinct lines
    # (energy already has a line, so just append the new input variants)
    pc_lines.append(nl)
    added_pc += 1
print(f"Added {added_pc} capital-goods power lines to power_company")

# ── PRIORITY 5: Grid battery storage products ─────────────────────────────────
# Add new items for grid-scale battery packs
add_item_if_missing("grid_battery_lfp",     "Grid Battery Pack (LFP)", "components",
    "Large-scale lithium iron phosphate battery system for grid energy storage.")
add_item_if_missing("grid_battery_sodium",  "Grid Battery Pack (Sodium-Ion)", "components",
    "Sodium-ion grid storage battery system; cobalt-free and low-cost.")
add_item_if_missing("solid_state_battery_pack","Solid-State Battery Pack", "components",
    "Next-generation solid-state battery assembly for premium EVs and aerospace.")
add_item_if_missing("alkaline_battery",     "Alkaline Battery",           "components",
    "Potassium hydroxide alkaline battery for consumer electronics.")
add_item_if_missing("power_electronics_module","Power Electronics Module","components",
    "GaN or SiC based power converter module for EV inverters and grid equipment.")

bg_lines = dbiz["battery_gigafactory"]["production_lines"]
bg_outs = {l["output_item"] for l in bg_lines}

BG_NEW_LINES = [
    ln("grid_battery_lfp",        50, [("lfp_cell",400),("steel",200),("copper_wire",200),("processor",10),("energy",80000),("paper",60)]),
    ln("grid_battery_sodium",     50, [("sodium_ion_cell",400),("steel",200),("copper_wire",200),("processor",10),("energy",60000),("paper",50)]),
    ln("solid_state_battery_pack",20, [("solid_state_cell",200),("titanium",50),("copper_wire",100),("processor",20),("energy",150000),("paper",100)]),
    ln("alkaline_battery",       500, [("potassium_hydroxide",200),("zinc",200),("steel",100),("energy",20000),("paper",20)]),
]
added_bg = 0
for nl in BG_NEW_LINES:
    if nl["output_item"] not in bg_outs:
        bg_lines.append(nl)
        added_bg += 1
print(f"Added {added_bg} new battery products to battery_gigafactory")

# Power electronics module to semiconductor_fab (uses GaN/SiC wafers)
sf_lines = dbiz["semiconductor_fab"]["production_lines"]
sf_outs  = {l["output_item"] for l in sf_lines}
if "power_electronics_module" not in sf_outs:
    sf_lines.append(ln("power_electronics_module",100,
        [("gallium_nitride",40),("silicon_carbide_wafer",30),("copper",100),
         ("energy",80000),("paper",60)]))
    print("Added power_electronics_module to semiconductor_fab")

# ── PRIORITY 6: Fix lcd_panel, solar_panel, neodymium_magnet recipes ──────────
sf_all = dbiz["semiconductor_fab"]["production_lines"]

# lcd_panel: add indium (ITO coating) and europium (phosphors)
replace_line(sf_all, "lcd_panel", ln("lcd_panel", 100,
    [("glass",500),("microchip",25),("copper_wire",100),("indium",20),("europium",10),
     ("energy",60000),("paper",60)]))
print("Updated lcd_panel recipe → adds indium + europium")

# solar_panel: add tellurium or selenium (CdTe / CIGS chemistry)
sp_lines = dbiz["energy_infrastructure_factory"]["production_lines"]
replace_line(sp_lines, "solar_panel", ln("solar_panel", 400,
    [("silicon_wafer",300),("silver",40),("aluminum",150),("glass",200),
     ("selenium",20),("energy",60000),("paper",50)]))
print("Updated solar_panel recipe → adds selenium")

# neodymium_magnet: add dysprosium (thermal stability enhancer)
af_lines = dbiz["alloy_forge"]["production_lines"]
replace_line(af_lines, "neodymium_magnet", ln("neodymium_magnet", 150,
    [("neodymium",100),("iron",100),("boron",50),("dysprosium",15),
     ("energy",80000),("paper",50)]))
print("Updated neodymium_magnet recipe → adds dysprosium")

# duralumin: add scandium (Sc-Al aerospace alloy)
replace_line(af_lines, "duralumin", ln("duralumin", 250,
    [("aluminum",200),("copper",80),("manganese",40),("magnesium",40),("scandium",10),
     ("energy",60000),("paper",40)]))
print("Updated duralumin recipe → adds scandium")

# ── PRIORITY 7: Specialty metal uses ─────────────────────────────────────────

# bronze propeller in marine_factory
marine_lines = biz["marine_factory"]["production_lines"]
replace_line(marine_lines, "propeller", ln("propeller", 50,
    [("bronze",200),("iron",100),("energy",30000),("paper",20)]))
print("Updated marine_factory propeller → uses bronze")

# tantalum capacitor component → used in circuit_board and processor
# Update circuit_board to add tantalum
replace_line(sf_all, "circuit_board", ln("circuit_board", 200,
    [("pcb_substrate",200),("copper",200),("solder",100),
     ("tantalum",20),("gold",5),("energy",40000),("paper",40)]))
print("Updated circuit_board → adds tantalum + gold (plating)")

# gold/palladium → add to semiconductor_fab as plating chemicals
add_item_if_missing("gold_bond_wire", "Gold Bond Wire", "components",
    "Ultra-thin gold wire for chip-to-package electrical bonding.")
if "gold_bond_wire" not in {l["output_item"] for l in sf_all}:
    sf_all.append(ln("gold_bond_wire", 200,
        [("gold",50),("energy",50000),("paper",30)]))
    print("Added gold_bond_wire to semiconductor_fab")

# palladium → catalytic converter for auto
add_item_if_missing("catalytic_converter","Catalytic Converter","components",
    "Exhaust emission control unit using platinum group metals.")
ap_lines = biz["auto_parts_factory"]["production_lines"]
ap_outs = {l["output_item"] for l in ap_lines}
if "catalytic_converter" not in ap_outs:
    ap_lines.append(ln("catalytic_converter", 50,
        [("palladium",10),("platinum",5),("cerium",20),("steel",50),("energy",20000),("paper",15)]))
    print("Added catalytic_converter to auto_parts_factory (uses palladium + platinum + cerium)")

# Update car recipe to consume catalytic_converter
aa_lines = biz["auto_assembly"]["production_lines"]
for i, l in enumerate(aa_lines):
    if l["output_item"] == "car":
        inp_items = [x["item"] for x in l["inputs"]]
        if "catalytic_converter" not in inp_items:
            l["inputs"].append({"item":"catalytic_converter","quantity":1})
            print("Added catalytic_converter to car recipe in auto_assembly")
        break

# antimony → lead_acid_battery (Pb-Sb grid alloy)
# Update lead_acid_battery to use antimony
bg_la_lines = [l for l in bg_lines if l["output_item"] == "lead_acid_battery"]
if bg_la_lines:
    for inp in bg_la_lines[0]["inputs"]:
        pass  # already has lead, sulfuric_acid, plastic
    replace_line(bg_lines, "lead_acid_battery", ln("lead_acid_battery", 500,
        [("lead",400),("antimony",30),("sulfuric_acid",300),("plastic",200),
         ("energy",50000),("paper",50)]))
    print("Updated lead_acid_battery → adds antimony (Pb-Sb grid alloy)")

# car_battery in auto_parts_factory → use lead_acid_battery as base
replace_line(ap_lines, "car_battery", ln("car_battery", 100,
    [("lead_acid_battery",60),("plastic",50),("copper_wire",20),
     ("energy",10000),("paper",10)]))
print("Updated car_battery → uses lead_acid_battery as base")

# cerium → glass (UV filtering, polishing)
gw_lines = biz["glass_works"]["production_lines"]
gw_outs = {l["output_item"] for l in gw_lines}
add_item_if_missing("optical_glass","Optical Glass","components",
    "Cerium-doped high-purity glass for optics, camera lenses, and display panels.")
if "optical_glass" not in gw_outs:
    gw_lines.append(ln("optical_glass", 100,
        [("glass",300),("cerium",30),("silica",50),("energy",40000),("paper",30)]))
    # silica = sand based
    print("Added optical_glass to glass_works (uses cerium + silica)")
    # silica can come from sand via glass_works or quartz via refinery — check
    # Sand already exists; close enough. Or use quartz:
    replace_line(gw_lines, "optical_glass", ln("optical_glass", 100,
        [("glass",300),("cerium",30),("quartz",50),("energy",40000),("paper",30)]))
    print("  (updated optical_glass to use quartz instead of silica)")

# gadolinium → MRI contrast agent use in mri_machine recipe
mef_lines = dbiz["medical_equipment_factory"]["production_lines"]
replace_line(mef_lines, "mri_machine", ln("mri_machine", 5,
    [("neodymium_magnet",60),("gadolinium",20),("processor",100),("titanium",80),
     ("copper_wire",500),("energy",200000),("paper",150)]))
print("Updated mri_machine → adds gadolinium (MRI contrast agent)")

# germanium → fiber optic component
add_item_if_missing("fiber_optic_cable","Fiber Optic Cable","components",
    "Germanium-doped silica glass fiber for high-speed data transmission.")
sci_lines = dbiz["scientific_equipment_factory"]["production_lines"]
sci_outs = {l["output_item"] for l in sci_lines}
if "fiber_optic_cable" not in sci_outs:
    sci_lines.append(ln("fiber_optic_cable", 200,
        [("germanium",30),("glass",300),("plastic",100),("energy",60000),("paper",40)]))
    print("Added fiber_optic_cable to scientific_equipment_factory (uses germanium)")

# ── PRIORITY 8: Acid solution consumption ─────────────────────────────────────
# acid_solution consumed by rare_earth_processor ore leach
rp_lines = dbiz["rare_earth_processor"]["production_lines"]
# Add it to the cerium and dysprosium lines (already have sulfuric_acid, but
# acid_solution is a diluted multi-acid bath also used for final wash)
# Instead: add a new ore leaching line
rp_outs = {l["output_item"] for l in rp_lines}
add_item_if_missing("refined_ore_concentrate","Refined Ore Concentrate","materials",
    "Pre-processed ore concentrate after acid leaching, ready for rare earth separation.")
if "refined_ore_concentrate" not in rp_outs:
    rp_lines.insert(0, ln("refined_ore_concentrate", 200,
        [("lree_ore",200),("hree_ore",100),("acid_solution",300),
         ("energy",50000),("water",2000),("paper",30)]))
    print("Added refined_ore_concentrate leaching line to rare_earth_processor")

# ── PRIORITY 9: White phosphorus / black_powder munitions ────────────────────
# black_powder → used in black_powder_rocket or old-style grenade 
# Add white phosphorus grenade to weapons_factory
add_item_if_missing("wp_grenade","White Phosphorus Grenade","military",
    "Smoke and incendiary grenade using white phosphorus fill.")
add_item_if_missing("incendiary_rocket","Incendiary Rocket","military",
    "Unguided rocket with white phosphorus or thermite warhead.")
add_item_if_missing("smoke_grenade","Smoke Grenade","military",
    "Colored smoke grenade for signaling and concealment.")
wf_outs = {l["output_item"] for l in wf}
NEW_WF_MUNITIONS = [
    ln("smoke_grenade",    200, [("grenade_body",150),("white_phosphorus",30),("smokeless_powder",50),("energy",12000),("paper",12)]),
    ln("wp_grenade",       100, [("grenade_body",100),("white_phosphorus",60),("det_cord",20),("energy",12000),("paper",12)]),
    ln("incendiary_rocket", 50, [("rocket_motor",20),("white_phosphorus",80),("thermite",40),("maraging_steel",50),("energy",30000),("paper",25)]),
]
added_mun = 0
for nl in NEW_WF_MUNITIONS:
    if nl["output_item"] not in wf_outs:
        wf.append(nl)
        wf_outs.add(nl["output_item"])
        added_mun += 1
print(f"Added {added_mun} new munitions to weapons_factory (uses white_phosphorus, det_cord)")

# ── PRIORITY 10: Activate remaining metals ───────────────────────────────────
# nichrome → heating element
add_item_if_missing("heating_element","Heating Element","components",
    "Nichrome resistance coil used in industrial ovens, furnaces, and toasters.")
add_item_if_missing("industrial_heater","Industrial Heater","industrial",
    "High-wattage nichrome heating unit for industrial processes and HVAC.")
# monel/cupronickel → marine piping
add_item_if_missing("marine_piping","Marine Piping","components",
    "Corrosion-resistant cupronickel pipe and fitting set for naval vessels.")
# alnico_magnet → guitar pickup / speaker
add_item_if_missing("guitar_pickup","Guitar Pickup","components",
    "Alnico magnet-based electromagnetic transducer for electric guitar.")
# samarium_cobalt_magnet → jet engine motor
# already in jet_engine_factory? Check...
# bismuth → pharmaceutical
add_item_if_missing("bismuth_subsalicylate","Bismuth Subsalicylate","health",
    "Active ingredient in antacid and antidiarrheal medications (e.g. Pepto-Bismol).")
# phosphor_bronze → spring/connector
add_item_if_missing("precision_spring","Precision Spring","components",
    "Phosphor bronze spring for switches, connectors, and precision mechanisms.")
# beryllium_copper → aerospace fastener
add_item_if_missing("aerospace_fastener","Aerospace Fastener","components",
    "Beryllium copper high-strength bolt and nut set for aerospace structural assembly.")
# hydrogen_peroxide → rocket propellant (monopropellant)
add_item_if_missing("monopropellant","Monopropellant","materials",
    "Concentrated hydrogen peroxide rocket monopropellant for reaction control thrusters.")

# Add these to appropriate factories
ef_lines = dbiz["electronics_factory"]["production_lines"]
ef_outs  = {l["output_item"] for l in ef_lines}

EF_NEW = [
    ln("heating_element", 200, [("nichrome",200),("ceramic",50),("energy",20000),("paper",15)]),
    ln("marine_piping",   100, [("cupronickel",200),("monel",100),("energy",30000),("paper",20)]),
    ln("precision_spring", 300,[("phosphor_bronze",200),("energy",20000),("paper",15)]),
    ln("guitar_pickup",   100, [("alnico_magnet",50),("copper_wire",100),("energy",15000),("paper",10)]),
]
added_ef = sum(1 for nl in EF_NEW if add_if_missing(ef_lines, nl))
print(f"Added {added_ef} lines to electronics_factory (nichrome/monel/phosphor_bronze/alnico uses)")

# aerospace_fastener to alloy_forge
if add_if_missing(af_lines, ln("aerospace_fastener", 200,
    [("beryllium_copper",100),("titanium_alloy",50),("energy",50000),("paper",30)])):
    print("Added aerospace_fastener to alloy_forge (uses beryllium_copper)")

# bismuth_subsalicylate to pharmaceutical_lab
pharm_lines = biz["pharmaceutical_lab"]["production_lines"]
if add_if_missing(pharm_lines, ln("bismuth_subsalicylate", 200,
    [("bismuth",100),("active_ingredient",50),("energy",20000),("paper",15)])):
    print("Added bismuth_subsalicylate to pharmaceutical_lab (uses bismuth)")

# monopropellant to chemical_plant
chem_lines = dbiz["chemical_plant"]["production_lines"]
if add_if_missing(chem_lines, ln("monopropellant", 100,
    [("hydrogen_peroxide",300),("water",100),("energy",30000),("paper",20)])):
    print("Added monopropellant to chemical_plant (uses hydrogen_peroxide)")

# industrial_heater to advanced_materials_lab
aml_lines = dbiz["advanced_materials_lab"]["production_lines"]
if add_if_missing(aml_lines, ln("industrial_heater", 50,
    [("heating_element",20),("stainless_steel",50),("energy",10000),("paper",10)])):
    print("Added industrial_heater to advanced_materials_lab")

# fiber_optic_cable → consumed by data_center or electronics_factory
dc_lines = dbiz["data_center"]["production_lines"]
print("\nData center lines:")
for l in dc_lines:
    print(f"  {l['output_item']}")

# activated_carbon → water_treatment
wt_lines = dbiz["water_treatment"]["production_lines"]
print("\nwater_treatment lines:")
for l in wt_lines:
    print(f"  {l['output_item']} <- {[x['item'] for x in l['inputs']]}")


# ── add activated_carbon to water_treatment ───────────────────────────────────
for l in wt_lines:
    if l["output_item"] == "water":
        inp_items = [x["item"] for x in l["inputs"]]
        if "activated_carbon" not in inp_items:
            l["inputs"].append({"item":"activated_carbon","quantity":50})
            print("Added activated_carbon to water_treatment water line")
        break

# acid_solution → add to wire_plant for wire pickling
wire_lines = dbiz["wire_plant"]["production_lines"]
for l in wire_lines:
    if l["output_item"] == "copper_wire":
        if "acid_solution" not in [x["item"] for x in l["inputs"]]:
            l["inputs"].append({"item":"acid_solution","quantity":30})
            print("Added acid_solution to wire_plant copper_wire (pickling bath)")
        break

# potassium_hydroxide → alkaline_battery (already added above) ✓
# Also: add to soap/personal_care (KOH saponification)
pc_factory = biz["personal_care_factory"]["production_lines"]
for l in pc_factory:
    if l["output_item"] == "soap":
        if "potassium_hydroxide" not in [x["item"] for x in l["inputs"]]:
            l["inputs"].append({"item":"potassium_hydroxide","quantity":30})
            print("Added potassium_hydroxide to personal_care_factory soap (saponification)")
        break

# ── Save all files ─────────────────────────────────────────────────────────────
with open("item_types.json","w") as f:
    json.dump(items, f, indent=2, sort_keys=True)
with open("business_types.json","w") as f:
    json.dump(biz, f, indent=2, sort_keys=True)
with open("district_businesses.json","w") as f:
    json.dump(dbiz, f, indent=2, sort_keys=True)
print("\nAll files saved.")
