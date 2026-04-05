#!/usr/bin/env python3
"""
Massive expansion patch:
- Adds ~200 new items to item_types.json
- Fixes broken recipes
- Adds new production lines to existing businesses
- Adds new district businesses
"""
import json, copy

# ── helpers ──────────────────────────────────────────────────────────────────
def item(name, category, description):
    return {"name": name, "category": category, "description": description}

def line(output_item, output_qty, inputs):
    """inputs = list of (item, quantity) tuples"""
    return {
        "output_item": output_item,
        "output_qty": output_qty,
        "inputs": [{"item": i, "quantity": q} for i, q in inputs]
    }


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 1 — NEW ITEMS FOR item_types.json
# ══════════════════════════════════════════════════════════════════════════════

NEW_ITEMS = {
    # ── TIER 1: NEW ORES ────────────────────────────────────────────────────
    "bauxite":          item("Bauxite",            "ore", "Aluminum-bearing ore; primary feedstock for aluminum smelting."),
    "tin_ore":          item("Tin Ore",             "ore", "Raw tin-bearing rock extracted from mines."),
    "nickel_ore":       item("Nickel Ore",          "ore", "Sulfide or laterite ore containing nickel."),
    "cobalt_ore":       item("Cobalt Ore",          "ore", "Cobalt-bearing ore, often co-mined with copper or nickel."),
    "chromium_ore":     item("Chromium Ore",        "ore", "Chromite rock; source of chromium for stainless steel."),
    "manganese_ore":    item("Manganese Ore",       "ore", "Oxide ore used in steelmaking and battery production."),
    "molybdenum_ore":   item("Molybdenum Ore",      "ore", "Molybdenite concentrate for high-strength alloy steels."),
    "vanadium_ore":     item("Vanadium Ore",        "ore", "Oxide ore refined for high-strength and energy-storage uses."),
    "tungsten_ore":     item("Tungsten Ore",        "ore", "Scheelite or wolframite ore; source of the hardest metal."),
    "titanium_ore":     item("Titanium Ore",        "ore", "Ilmenite or rutile ore for aerospace-grade titanium."),
    "lithium_ore":      item("Lithium Ore",         "ore", "Spodumene or lepidolite bearing lithium carbonate."),
    "uranium_ore":      item("Uranium Ore",         "ore", "Pitchblende bearing fissile uranium oxide."),
    "gold_ore":         item("Gold Ore",            "ore", "Low-grade rock with trace gold; processed by cyanidation."),
    "silver_ore":       item("Silver Ore",          "ore", "Argentiferous galena or native silver in host rock."),
    "platinum_ore":     item("Platinum Ore",        "ore", "PGM-bearing sulphide ore from layered intrusions."),
    "phosphate_rock":   item("Phosphate Rock",      "ore", "Apatite-rich rock; primary source of phosphorus for fertilizers."),
    "fluorite":         item("Fluorite",            "ore", "Calcium fluoride mineral used in metallurgy and chemical production."),
    "sulfur":           item("Sulfur",              "ore", "Elemental sulfur from volcanic or refinery sources."),
    "quartz":           item("Quartz",              "ore", "High-purity silicon dioxide; feedstock for silicon refining."),
    "potash_ore":       item("Potash Ore",          "ore", "Potassium-bearing mineral salt mined for fertilizers."),
    "magnesite":        item("Magnesite",           "ore", "Magnesium carbonate ore for refractory and chemical uses."),
    "coltan_ore":       item("Coltan Ore",          "ore", "Columbite-tantalite ore bearing tantalum and niobium."),
    "beryllium_ore":    item("Beryllium Ore",       "ore", "Beryl mineral bearing lightweight strategic metal."),
    "bismuth_ore":      item("Bismuth Ore",         "ore", "Native bismuth or bismuthinite ore."),
    "antimony_ore":     item("Antimony Ore",        "ore", "Stibnite ore; used in flame retardants and lead alloys."),
    "zircon_ore":       item("Zircon Ore",          "ore", "Zirconium silicate mineral used in ceramics and nuclear."),
    "lree_ore":         item("Light Rare Earth Ore","ore", "Bastnäsite or monazite ore rich in cerium, lanthanum, neodymium."),
    "hree_ore":         item("Heavy Rare Earth Ore","ore", "Xenotime or ion-adsorption ore rich in dysprosium, terbium, europium."),

    # ── TIER 2: REFINED METALS ──────────────────────────────────────────────
    "zinc":             item("Zinc",                "metals", "Refined zinc; used in galvanizing, alloys, and batteries."),
    "tin":              item("Tin",                 "metals", "Refined tin; used in solder, coatings, and bronze alloys."),
    "nickel":           item("Nickel",              "metals", "Refined nickel; critical for stainless steel and battery cathodes."),
    "cobalt":           item("Cobalt",              "metals", "Refined cobalt; essential for lithium-ion battery cathodes."),
    "chromium":         item("Chromium",            "metals", "Refined chromium; primary hardening agent in stainless steel."),
    "manganese":        item("Manganese",           "metals", "Refined manganese; used in steel and battery chemistry."),
    "molybdenum":       item("Molybdenum",          "metals", "Refined molybdenum; adds strength and heat resistance to alloys."),
    "vanadium":         item("Vanadium",            "metals", "Refined vanadium; used in high-strength steels and redox batteries."),
    "tungsten":         item("Tungsten",            "metals", "Refined tungsten; the highest melting point of all metals."),
    "magnesium":        item("Magnesium",           "metals", "Refined magnesium; lightest structural metal."),
    "gold":             item("Gold",                "metals", "Refined gold; monetary metal and electronics conductor."),
    "silver":           item("Silver",              "metals", "Refined silver; highest electrical conductivity of all metals."),
    "platinum":         item("Platinum",            "metals", "Refined platinum; catalytic converter and hydrogen fuel cell metal."),
    "palladium":        item("Palladium",           "metals", "Refined palladium; catalytic converter and electronics plating."),
    "titanium":         item("Titanium",            "metals", "Refined titanium; high strength-to-weight ratio aerospace metal."),
    "lithium":          item("Lithium",             "metals", "Refined lithium carbonate; primary feedstock for all lithium batteries."),
    "silicon":          item("Silicon",             "metals", "Metallurgical-grade silicon refined from quartz."),
    "beryllium":        item("Beryllium",           "metals", "Refined beryllium; extremely lightweight nuclear and aerospace metal."),
    "zirconium":        item("Zirconium",           "metals", "Refined zirconium; used in nuclear reactors and ceramics."),
    "tantalum":         item("Tantalum",            "metals", "Refined tantalum from coltan; essential for electronic capacitors."),
    "niobium":          item("Niobium",             "metals", "Refined niobium from coltan; microalloying steel additive."),
    "uranium_oxide":    item("Uranium Oxide (U3O8)","metals", "Yellowcake uranium concentrate; nuclear fuel precursor."),
    "gallium":          item("Gallium",             "metals", "Trace metal recovered from bauxite processing; used in semiconductors."),
    "germanium":        item("Germanium",           "metals", "Semiconductor metal recovered from zinc smelting."),
    "indium":           item("Indium",              "metals", "Soft metal recovered from zinc/lead smelting; used in ITO displays."),
    "selenium":         item("Selenium",            "metals", "Byproduct of copper refining; used in solar cells and glass."),
    "tellurium":        item("Tellurium",           "metals", "Rare byproduct of copper refining; used in CdTe solar panels."),
    "rhenium":          item("Rhenium",             "metals", "Ultra-rare metal recovered from molybdenum roasting; for jet turbines."),
    # Rare earths
    "cerium":           item("Cerium",              "metals", "Most abundant rare earth; used in catalysts and polishing compounds."),
    "lanthanum":        item("Lanthanum",           "metals", "Rare earth metal used in solid-state batteries and camera lenses."),
    "neodymium":        item("Neodymium",           "metals", "Rare earth metal critical for permanent magnets in EVs and turbines."),
    "praseodymium":     item("Praseodymium",        "metals", "Rare earth alloying element; used in magnets and aircraft engines."),
    "samarium":         item("Samarium",            "metals", "Rare earth used in samarium-cobalt magnets for high-temp applications."),
    "dysprosium":       item("Dysprosium",          "metals", "Heavy rare earth that maintains magnet strength at high temperatures."),
    "terbium":          item("Terbium",             "metals", "Heavy rare earth used in solid-state devices and green phosphors."),
    "europium":         item("Europium",            "metals", "Heavy rare earth producing red phosphors in LEDs and displays."),
    "yttrium":          item("Yttrium",             "metals", "Rare earth used in radar, superconductors, and LED phosphors."),
    "erbium":           item("Erbium",              "metals", "Rare earth used in fiber-optic amplifiers and laser applications."),
    "gadolinium":       item("Gadolinium",          "metals", "Heavy rare earth used in MRI contrast agents and nuclear control rods."),
    "scandium":         item("Scandium",            "metals", "Light rare earth used to strengthen aluminum alloys for aerospace."),
    "holmium":          item("Holmium",             "metals", "Rare earth with strongest magnetic moment; used in nuclear reactors."),

    # ── TIER 3: ALLOYS ──────────────────────────────────────────────────────
    "bronze":               item("Bronze",              "metals", "Copper-tin alloy; corrosion resistant, used in marine and artistic applications."),
    "stainless_steel":      item("Stainless Steel",     "metals", "Iron-chromium-nickel alloy; corrosion resistant structural metal."),
    "titanium_alloy":       item("Titanium Alloy",      "metals", "Ti-6Al-4V aerospace alloy; exceptional strength-to-weight ratio."),
    "tungsten_carbide":     item("Tungsten Carbide",    "metals", "Hardest man-made material; used in cutting tools and armor."),
    "solder":               item("Solder",              "metals", "Tin-lead alloy used to join electronic components to circuit boards."),
    "inconel":              item("Inconel",             "metals", "Nickel-chromium superalloy for jet engines and extreme heat environments."),
    "maraging_steel":       item("Maraging Steel",      "metals", "Ultra-high-strength steel alloy used in missile bodies and tooling."),
    "duralumin":            item("Duralumin",           "metals", "Aluminum-copper-manganese alloy for aircraft frames and armor."),
    "nichrome":             item("Nichrome",            "metals", "Nickel-chromium resistance alloy used in heating elements."),
    "monel":                item("Monel",               "metals", "Nickel-copper alloy; highly corrosion resistant for marine and chemical use."),
    "cupronickel":          item("Cupronickel",         "metals", "Copper-nickel alloy for coinage, heat exchangers, and naval piping."),
    "phosphor_bronze":      item("Phosphor Bronze",     "metals", "Copper-tin-phosphorus alloy for springs, bearings, and connectors."),
    "beryllium_copper":     item("Beryllium Copper",    "metals", "High-strength copper alloy for precision instruments and aerospace fasteners."),
    "nitinol":              item("Nitinol",             "metals", "Nickel-titanium shape-memory alloy for medical devices and actuators."),
    "neodymium_magnet":     item("Neodymium Magnet",    "components", "NdFeB permanent magnet; most powerful type used in motors and speakers."),
    "samarium_cobalt_magnet": item("Samarium-Cobalt Magnet", "components", "High-temperature permanent magnet for aerospace and defense motors."),
    "alnico_magnet":        item("Alnico Magnet",       "components", "Aluminum-nickel-cobalt magnet for sensors, guitars, and instruments."),
    "depleted_uranium":     item("Depleted Uranium",    "metals", "U-238 byproduct from enrichment; used in armor-piercing projectiles and radiation shielding."),
    "boron_carbide":        item("Boron Carbide",       "materials", "Extremely hard ceramic compound; used in body armor and nuclear shielding."),
    "silicon_carbide":      item("Silicon Carbide",     "materials", "Hard ceramic abrasive; used in advanced power electronics and armor."),
    "alumina":              item("Alumina (Al2O3)",     "materials", "Aluminum oxide ceramic; used in armor, electronics substrates, and abrasives."),
    "graphite":             item("Graphite",            "materials", "Carbon allotrope used in lubricants, battery anodes, and nuclear moderators."),
    "carbon_fiber":         item("Carbon Fiber",        "materials", "High-strength, lightweight composite reinforcement for aerospace and defense."),
    "pan_precursor":        item("PAN Precursor",       "materials", "Polyacrylonitrile fiber; intermediate in carbon fiber production."),
    "kevlar_fiber":         item("Kevlar Fiber",        "materials", "Para-aramid fiber; primary ballistic protection material."),
    "ppta_polymer":         item("PPTA Polymer",        "materials", "Poly(p-phenylene terephthalamide); chemical precursor to Kevlar."),
    "activated_carbon":     item("Activated Carbon",   "materials", "Highly porous carbon used in filtration, gas masks, and water treatment."),

    # ── TIER 4: CHEMICALS ───────────────────────────────────────────────────
    "sulfuric_acid":        item("Sulfuric Acid",       "materials", "H2SO4; most produced industrial chemical, used in ore leaching and batteries."),
    "hydrochloric_acid":    item("Hydrochloric Acid",   "materials", "HCl; used in ore processing, metal pickling, and chemical synthesis."),
    "hydrofluoric_acid":    item("Hydrofluoric Acid",   "materials", "HF; critical etchant in semiconductor fabrication."),
    "nitric_acid":          item("Nitric Acid",         "materials", "HNO3; used in explosives production, fertilizers, and metal etching."),
    "ammonia":              item("Ammonia",             "materials", "NH3; primary nitrogen source for fertilizers and chemical synthesis."),
    "caustic_soda":         item("Caustic Soda",        "materials", "NaOH; used in alumina refining, paper, and chemical manufacturing."),
    "chlorine":             item("Chlorine",            "materials", "Cl2; produced by electrolysis; used in PVC, bleach, and water treatment."),
    "hydrogen_peroxide":    item("Hydrogen Peroxide",   "materials", "H2O2; oxidizer and bleaching agent in chemicals and propellants."),
    "phosphoric_acid":      item("Phosphoric Acid",     "materials", "H3PO4; used in LFP batteries, fertilizers, and food additives."),
    "potassium_nitrate":    item("Potassium Nitrate",   "materials", "KNO3; oxidizer component in black powder and fertilizers."),
    "potassium_hydroxide":  item("Potassium Hydroxide", "materials", "KOH; electrolyte in alkaline batteries and chemical synthesis."),
    "acetone":              item("Acetone",             "materials", "Common industrial solvent used in explosives, plastics, and pharmaceuticals."),
    "acrylonitrile":        item("Acrylonitrile",       "materials", "CH2=CHCN; monomer for PAN precursor and ABS plastic production."),
    "nitrocellulose":       item("Nitrocellulose",      "materials", "Gun cotton; used in smokeless powder and lacquers."),
    "nitroglycerin":        item("Nitroglycerin",       "materials", "NG; high-sensitivity explosive and vasodilator active ingredient."),
    "epoxy_resin":          item("Epoxy Resin",         "materials", "Two-part structural adhesive and composite matrix for PCBs and carbon fiber."),
    "fertilizer_npk":       item("NPK Fertilizer",     "materials", "Nitrogen-phosphorus-potassium blended crop fertilizer."),
    "acid_solution":        item("Acid Solution",       "materials", "Dilute mixed acid bath used in metal plating and semiconductor etching."),
    "cellulose":            item("Cellulose",           "materials", "Plant-derived biopolymer used in paper, nitrocellulose, and textiles."),
    "glycerin":             item("Glycerin",            "materials", "Byproduct of biodiesel production; used in pharmaceuticals and explosives."),
    "phenylenediamine":     item("Phenylenediamine",    "materials", "Aromatic diamine monomer; precursor to PPTA polymer for Kevlar."),
    "terephthaloyl_chloride": item("Terephthaloyl Chloride", "materials", "Acid chloride monomer; combines with phenylenediamine to form PPTA."),
    "thermite":             item("Thermite",            "materials", "Iron oxide and aluminum powder mixture; incendiary material."),
    "black_powder":         item("Black Powder",        "materials", "KNO3 + charcoal + sulfur; traditional propellant and blasting agent."),
    "smokeless_powder":     item("Smokeless Powder",    "materials", "Nitrocellulose-based propellant for modern firearms and artillery."),
    "rdx_explosive":        item("RDX Explosive",       "materials", "Cyclonite; military-grade high explosive used in warheads and demolition."),
    "c4_explosive":         item("C-4 Explosive",       "materials", "RDX + plasticizer composition; demolition and warhead explosive."),
    "det_cord":             item("Detonation Cord",     "materials", "PETN-filled cordex line for simultaneous multi-point detonation."),
    "white_phosphorus":     item("White Phosphorus",    "materials", "Incendiary and smoke-generating munition compound."),

    # ── TIER 5: BATTERY CHAIN ───────────────────────────────────────────────
    "silicon_wafer":        item("Silicon Wafer",       "components", "Ultra-pure single-crystal silicon disk; substrate for all microchip fabrication."),
    "pcb_substrate":        item("PCB Substrate",       "components", "FR-4 fiberglass-epoxy laminate; the base material for circuit boards."),
    "gallium_arsenide":     item("Gallium Arsenide Wafer", "components", "GaAs compound semiconductor wafer for high-frequency and solar applications."),
    "gallium_nitride":      item("Gallium Nitride Wafer",  "components", "GaN wide-bandgap semiconductor for power electronics and RF devices."),
    "silicon_carbide_wafer": item("Silicon Carbide Wafer", "components", "SiC power semiconductor substrate for EVs and grid-scale inverters."),
    "lead_acid_battery":    item("Lead-Acid Battery",   "components", "Traditional 12V automotive battery; lead plates in sulfuric acid electrolyte."),
    "lithium_nmc_cell":     item("Lithium NMC Cell",    "components", "Nickel-manganese-cobalt lithium cell; high energy density for EVs and electronics."),
    "lfp_cell":             item("LFP Battery Cell",    "components", "Lithium iron phosphate cell; thermally stable, long-cycle EV and grid battery."),
    "solid_state_cell":     item("Solid-State Cell",    "components", "LLZO ceramic electrolyte lithium cell; next-generation battery technology."),
    "sodium_ion_cell":      item("Sodium-Ion Cell",     "components", "Low-cost sodium-ion battery cell; cobalt-free grid storage alternative."),

    # ── TIER 6: ADVANCED ELECTRONICS / DEFENSE ELECTRONICS ─────────────────
    "radar_system":         item("Radar System",        "components", "Active phased-array radar unit for aircraft, ships, and missile defense."),
    "sonar_system":         item("Sonar System",        "components", "Active/passive hydrophone sonar array for submarine detection."),
    "fire_control_system":  item("Fire Control System", "components", "Computerized targeting and weapons control system for military platforms."),
    "inertial_nav_unit":    item("Inertial Navigation Unit", "components", "IMU providing GPS-independent position and attitude data."),
    "night_vision_optic":   item("Night Vision Optic",  "components", "Image-intensifying monocular or scope for low-light operations."),
    "targeting_optic":      item("Targeting Optic",     "components", "Precision rifle scope or laser rangefinder targeting system."),
    "encrypted_radio":      item("Encrypted Radio",     "components", "Frequency-hopping tactical communications radio."),
    "drone_avionics":       item("Drone Avionics Pack", "components", "Flight controller, GPS, and ESC package for unmanned aerial vehicles."),
    "missile_guidance_unit": item("Missile Guidance Unit", "components", "Inertial/GPS/IR seeker guidance package for precision munitions."),
    "ejection_seat":        item("Ejection Seat",       "components", "Rocket-propelled pilot escape system for combat aircraft."),
    "avionics_suite":       item("Avionics Suite",      "components", "Integrated flight instruments, navigation, and communications package."),
    "jet_turbine_blade":    item("Jet Turbine Blade",   "components", "Single-crystal Inconel turbine blade for jet engine hot section."),

    # ── TIER 7: ARMOR & PROTECTION SYSTEMS ──────────────────────────────────
    "ballistic_plate":      item("Ballistic Plate",     "components", "Ceramic-composite armor plate for body armor and vehicle protection."),
    "explosive_reactive_armor": item("Explosive Reactive Armor", "components", "ERA tile that disrupts shaped-charge jets from RPGs and ATGMs."),
    "composite_armor_panel": item("Composite Armor Panel", "components", "Layered steel-ceramic-kevlar armor panel for vehicle hulls."),
    "blast_resistant_glass": item("Blast-Resistant Glass", "components", "Laminated polycarbonate and glass for armored vehicle viewports."),

    # ── TIER 8: PROPULSION & ENERGY INFRASTRUCTURE ──────────────────────────
    "rocket_motor":         item("Rocket Motor",        "components", "Solid or liquid-propellant rocket motor for missiles and launch vehicles."),
    "turbojet_engine":      item("Turbojet Engine",     "components", "Axial-flow jet engine for combat aircraft and cruise missiles."),
    "turbofan_engine":      item("Turbofan Engine",     "components", "High-bypass jet engine for commercial and military transport aircraft."),
    "diesel_engine":        item("Diesel Engine",       "components", "Heavy-duty compression-ignition engine for trucks and military vehicles."),
    "gas_turbine":          item("Gas Turbine",         "components", "Industrial gas turbine for power generation and naval propulsion."),
    "nuclear_reactor_core": item("Nuclear Reactor Core","components", "Enriched fuel assembly and control rod assembly for power reactors."),
    "solar_panel":          item("Solar Panel",         "components", "Photovoltaic module converting sunlight to DC electricity."),
    "wind_turbine_blade":   item("Wind Turbine Blade",  "components", "Fiberglass-carbon fiber blade set for utility-scale wind turbines."),
    "transformer":          item("Transformer",         "components", "High-voltage power transformer for grid transmission and distribution."),
    "lithium_battery_pack": item("Lithium Battery Pack","components", "Assembled lithium cell array with BMS for EV and grid storage."),
    "hydrogen_fuel_cell":   item("Hydrogen Fuel Cell",  "components", "PEM fuel cell stack converting hydrogen and oxygen to electricity."),

    # ── TIER 9: MILITARY VEHICLES / WEAPONS COMPONENTS ──────────────────────
    "tank_cannon":          item("Tank Cannon",         "components", "120mm smoothbore cannon for main battle tank armament."),
    "tank_hull":            item("Tank Hull",           "components", "Welded composite-armor main battle tank hull and chassis."),
    "tank_turret":          item("Tank Turret",         "components", "Rotating armored turret assembly for main battle tank."),
    "apc_hull":             item("APC Hull",            "components", "Armored personnel carrier hull with troop compartment."),
    "missile_warhead":      item("Missile Warhead",     "components", "High-explosive, shaped-charge, or thermobaric warhead assembly."),
    "rifle_barrel":         item("Rifle Barrel",        "components", "Precision-rifled steel barrel for service rifles."),
    "rifle_receiver":       item("Rifle Receiver",      "components", "Machined aluminum or steel rifle lower and upper receiver set."),
    "grenade_body":         item("Grenade Body",        "components", "Fragmentation sleeve and fuze assembly for hand grenades."),
    "jet_airframe":         item("Jet Airframe",        "components", "Titanium and carbon fiber structural frame for combat jets."),
    "helicopter_rotor":     item("Helicopter Rotor",    "components", "Main and tail rotor assembly for military helicopters."),
    "naval_gun_system":     item("Naval Gun System",    "components", "Automated 76mm or 127mm deck gun system for surface combatants."),
    "torpedo":              item("Torpedo",             "components", "Self-propelled underwater weapon for submarine and surface launch."),
    "submarine_hull":       item("Submarine Hull",      "components", "Pressure-resistant double-hull submarine body section."),
    "destroyer_hull":       item("Destroyer Hull",      "components", "High-strength steel destroyer ship hull and superstructure."),

    # ── TIER 10: MEDICAL / INDUSTRIAL EQUIPMENT ─────────────────────────────
    "mri_machine":          item("MRI Machine",         "industrial", "Magnetic resonance imaging scanner using superconducting magnets."),
    "ct_scanner":           item("CT Scanner",          "industrial", "Computed tomography X-ray scanner for medical diagnosis."),
    "ventilator":           item("Ventilator",          "industrial", "Mechanical ventilator for ICU respiratory support."),
    "surgical_robot":       item("Surgical Robot",      "industrial", "Robotic surgery system for minimally invasive procedures."),
    "dialysis_machine":     item("Dialysis Machine",    "industrial", "Kidney dialysis machine for renal failure patients."),
    "radiation_therapy_unit": item("Radiation Therapy Unit", "industrial", "Linear accelerator for cancer radiation treatment."),
    "industrial_robot_arm": item("Industrial Robot Arm","industrial", "6-axis robotic manipulator for manufacturing automation."),
    "cnc_machine":          item("CNC Machine",         "industrial", "Computer numerically controlled precision machining center."),
    "3d_printer_industrial": item("Industrial 3D Printer","industrial","Large-format metal or polymer additive manufacturing system."),
    "nuclear_waste_container": item("Nuclear Waste Container","industrial","Shielded dry cask for spent nuclear fuel storage."),

    # ── TIER 11: CIVILIAN VEHICLES (NEW) ────────────────────────────────────
    "electric_car":         item("Electric Car",        "vehicles", "Battery-electric passenger vehicle."),
    "hybrid_car":           item("Hybrid Car",          "vehicles", "Gasoline-electric hybrid passenger vehicle."),
    "electric_bus":         item("Electric Bus",        "vehicles", "Zero-emission battery-electric transit bus."),
    "electric_truck":       item("Electric Truck",      "vehicles", "Heavy-duty battery-electric commercial truck."),
    "hydrogen_vehicle":     item("Hydrogen Vehicle",    "vehicles", "Fuel-cell powered passenger or commercial vehicle."),
    "armored_car":          item("Armored Car",         "vehicles", "Ballistic and blast protected executive or cash transport vehicle."),
    "military_truck":       item("Military Truck",      "vehicles", "Heavy military logistics and troop transport truck."),
    "infantry_fighting_vehicle": item("Infantry Fighting Vehicle","vehicles","Tracked IFV combining troop transport with direct fire weapon system."),
    "self_propelled_artillery": item("Self-Propelled Artillery","vehicles","Armored howitzer on a tracked or wheeled self-propelled chassis."),
    "fighter_jet":          item("Fighter Jet",         "vehicles", "Supersonic multi-role combat aircraft."),
    "attack_helicopter":    item("Attack Helicopter",   "vehicles", "Armed rotary-wing close air support and anti-armor aircraft."),
    "transport_helicopter": item("Transport Helicopter","vehicles", "Military medium-lift utility and troop transport helicopter."),
    "naval_destroyer":      item("Naval Destroyer",     "vehicles", "Guided-missile destroyer warship."),
    "submarine":            item("Submarine",           "vehicles", "Diesel-electric or nuclear attack submarine."),
    "military_drone":       item("Military Drone",      "vehicles", "Armed or reconnaissance unmanned aerial vehicle."),
    "drone_swarm_unit":     item("Drone Swarm Unit",    "vehicles", "Coordinated expendable micro-drone swarm for electronic warfare."),
}

print(f"Defined {len(NEW_ITEMS)} new items")

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 2 — PRODUCTION LINE ADDITIONS / FIXES
# ══════════════════════════════════════════════════════════════════════════════

# Each entry = (file, business_key, action, payload)
# action = 'replace_line' | 'add_line' | 'add_business' | 'fix_field'

# ── mineral_mine: add new ore lines ─────────────────────────────────────────
MINERAL_MINE_NEW_LINES = [
    line("lead_ore",      80,  [("energy",200),("bio_fuel",50),("water",100),("paper",2)]),
    line("bauxite",       90,  [("energy",220),("bio_fuel",55),("water",120),("paper",2)]),
    line("tin_ore",       70,  [("energy",180),("bio_fuel",40),("water",80), ("paper",2)]),
    line("nickel_ore",    60,  [("energy",250),("bio_fuel",60),("water",130),("paper",2)]),
    line("cobalt_ore",    50,  [("energy",280),("bio_fuel",70),("water",140),("paper",2)]),
    line("chromium_ore",  70,  [("energy",200),("bio_fuel",50),("water",100),("paper",2)]),
    line("manganese_ore", 80,  [("energy",160),("bio_fuel",40),("water",80), ("paper",2)]),
    line("molybdenum_ore",40,  [("energy",320),("bio_fuel",80),("water",160),("paper",2)]),
    line("vanadium_ore",  45,  [("energy",300),("bio_fuel",75),("water",150),("paper",2)]),
    line("tungsten_ore",  30,  [("energy",400),("bio_fuel",100),("water",200),("paper",3)]),
    line("titanium_ore",  55,  [("energy",270),("bio_fuel",65),("water",130),("paper",2)]),
    line("lithium_ore",   65,  [("energy",240),("bio_fuel",60),("water",120),("paper",2)]),
    line("gold_ore",      20,  [("energy",500),("bio_fuel",120),("water",250),("paper",3)]),
    line("silver_ore",    35,  [("energy",380),("bio_fuel",90),("water",180),("paper",3)]),
    line("platinum_ore",  10,  [("energy",600),("bio_fuel",150),("water",300),("paper",4)]),
    line("phosphate_rock",120, [("energy",100),("water",60),("paper",1)]),
    line("sulfur",        100, [("energy",80), ("water",40), ("paper",1)]),
    line("quartz",        110, [("energy",90), ("water",50), ("paper",1)]),
    line("potash_ore",    95,  [("energy",110),("water",55), ("paper",1)]),
    line("magnesite",     85,  [("energy",130),("water",65), ("paper",2)]),
    line("fluorite",      75,  [("energy",150),("water",70), ("paper",2)]),
    line("lree_ore",      40,  [("energy",350),("bio_fuel",85),("water",170),("paper",3)]),
    line("hree_ore",      25,  [("energy",450),("bio_fuel",110),("water",220),("paper",3)]),
    line("coltan_ore",    30,  [("energy",420),("bio_fuel",100),("water",210),("paper",3)]),
    line("beryllium_ore", 20,  [("energy",520),("bio_fuel",130),("water",260),("paper",4)]),
    line("zircon_ore",    45,  [("energy",290),("bio_fuel",70),("water",145),("paper",2)]),
    line("uranium_ore",   15,  [("energy",700),("bio_fuel",180),("water",350),("paper",5)]),
    line("bismuth_ore",   60,  [("energy",260),("bio_fuel",65),("water",130),("paper",2)]),
    line("antimony_ore",  55,  [("energy",270),("bio_fuel",68),("water",135),("paper",2)]),
]

# ── refinery: fix brass, add refined metals ──────────────────────────────────
REFINERY_FIXED_BRASS = line("brass", 125,
    [("copper",65),("zinc",30),("energy",100),("paper",2)])

REFINERY_NEW_LINES = [
    line("zinc",         35,  [("zinc_ore",150),   ("energy",160),("water",50),("paper",2)]),
    line("tin",          30,  [("tin_ore",140),    ("energy",170),("water",55),("paper",2)]),
    line("nickel",       25,  [("nickel_ore",160), ("energy",200),("water",60),("paper",2)]),
    line("cobalt",       20,  [("cobalt_ore",170), ("energy",220),("water",65),("paper",2)]),
    line("chromium",     28,  [("chromium_ore",155),("energy",190),("water",58),("paper",2)]),
    line("manganese",    32,  [("manganese_ore",145),("energy",155),("water",52),("paper",2)]),
    line("molybdenum",   18,  [("molybdenum_ore",180),("energy",280),("water",80),("paper",3)]),
    line("vanadium",     20,  [("vanadium_ore",175),("energy",260),("water",75),("paper",3)]),
    line("tungsten",     12,  [("tungsten_ore",200),("energy",380),("water",100),("paper",4)]),
    line("magnesium",    30,  [("magnesite",160),  ("energy",180),("water",60),("paper",2)]),
    line("gold",          8,  [("gold_ore",220),   ("energy",500),("water",120),("paper",4)]),
    line("silver",       15,  [("silver_ore",200), ("energy",380),("water",100),("paper",3)]),
    line("platinum",      5,  [("platinum_ore",250),("energy",600),("water",150),("paper",5)]),
    line("lead",         35,  [("lead_ore",150),   ("energy",150),("water",50),("paper",2)]),
    line("silicon",      45,  [("quartz",200),     ("energy",350),("water",80),("paper",3)]),
    line("lithium",      25,  [("lithium_ore",180),("energy",300),("water",70),("paper",3)]),
    line("uranium_oxide",10,  [("uranium_ore",250),("energy",700),("water",200),("paper",5)]),
    line("bismuth",      28,  [("bismuth_ore",155),("energy",200),("water",60),("paper",2)]),
    line("antimony",     24,  [("antimony_ore",160),("energy",210),("water",62),("paper",2)]),
]

# ── aluminum_foundry: FIX iron_ore → bauxite ─────────────────────────────────
ALUMINUM_FOUNDRY_FIXED_LINE = line("aluminum", 400,
    [("bauxite",1500),("caustic_soda",200),("energy",80000),("water",3000),("paper",40)])

# Also add byproduct recovery lines to aluminum_foundry
ALUMINUM_FOUNDRY_EXTRA_LINES = [
    line("gallium", 5, [("bauxite",2000),("sulfuric_acid",100),("energy",50000),("water",1000),("paper",20)]),
]

# ── semiconductor_fab: fix microchip, circuit_board, battery_cell ─────────────
SEMICONDCTOR_FAB_FIXED_LINES = {
    0: line("microchip", 200,
        [("silicon_wafer",300),("gallium",50),("hydrofluoric_acid",100),("energy",100000),("water",5000),("paper",100)]),
    3: line("circuit_board", 250,
        [("pcb_substrate",200),("copper",200),("solder",100),("energy",40000),("paper",40)]),
    5: line("lead_acid_battery", 150,
        [("lead",300),("sulfuric_acid",200),("plastic",200),("energy",30000),("paper",30)]),
}
SEMICONDUCTOR_FAB_NEW_LINES = [
    line("silicon_wafer",    300, [("silicon",400),("hydrofluoric_acid",200),("energy",150000),("water",8000),("paper",150)]),
    line("pcb_substrate",    400, [("fiberglass",300),("epoxy_resin",200),("energy",20000),("paper",20)]),
    line("lithium_nmc_cell", 200, [("lithium",200),("nickel",150),("manganese",100),("cobalt",80),("graphite",300),("energy",60000),("paper",60)]),
    line("lfp_cell",         200, [("lithium",200),("iron",150),("phosphoric_acid",100),("graphite",300),("energy",50000),("paper",50)]),
    line("solid_state_cell", 100, [("lithium",200),("lanthanum",50),("zirconium",50),("energy",120000),("paper",100)]),
    line("sodium_ion_cell",  200, [("manganese",150),("iron",100),("graphite",250),("energy",40000),("paper",40)]),
    line("gallium_arsenide", 100, [("gallium",100),("arsenic",50),("energy",200000),("water",2000),("paper",200)]),
    line("gallium_nitride",  100, [("gallium",100),("ammonia",150),("energy",180000),("water",2000),("paper",180)]),
    line("silicon_carbide_wafer",80, [("silicon",200),("graphite",100),("energy",250000),("paper",200)]),
]

print("Defined all recipe changes")

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 3 — NEW DISTRICT BUSINESSES
# ══════════════════════════════════════════════════════════════════════════════

def dbusiness(name, description, startup_cost, cycles, wage, terrain, lines_list):
    return {
        "name": name,
        "description": description,
        "startup_cost": startup_cost,
        "cycles_to_complete": cycles,
        "base_wage_cost": wage,
        "allowed_terrain": terrain if isinstance(terrain, list) else [terrain],
        "allowed_proximity": [],
        "class": "production",
        "production_lines": lines_list,
    }

NEW_DISTRICT_BUSINESSES = {

    # ── Titanium Smelter ────────────────────────────────────────────────────
    "titanium_smelter": dbusiness(
        "Titanium Smelter", "Kroll process reduction of titanium ore to refined titanium metal.",
        6000000, 28800, 30000, "district_industrial", [
        line("titanium",     200, [("titanium_ore",1200),("magnesium",400),("energy",200000),("water",5000),("paper",60)]),
        line("zirconium",    150, [("zircon_ore",1000), ("chlorine",200), ("energy",180000),("water",4000),("paper",50)]),
        line("beryllium",     50, [("beryllium_ore",800),("caustic_soda",200),("energy",250000),("water",3000),("paper",80)]),
    ]),

    # ── Rare Earth Processor ────────────────────────────────────────────────
    "rare_earth_processor": dbusiness(
        "Rare Earth Processing Plant", "Separates and refines light and heavy rare earth elements from ore concentrates.",
        7000000, 28800, 35000, "district_industrial", [
        # LREE from lree_ore
        line("cerium",       60,  [("lree_ore",400),("sulfuric_acid",200),("energy",80000),("water",2000),("paper",40)]),
        line("lanthanum",    50,  [("lree_ore",400),("hydrochloric_acid",150),("energy",90000),("water",2000),("paper",40)]),
        line("neodymium",    40,  [("lree_ore",500),("sulfuric_acid",250),("energy",100000),("water",2500),("paper",50)]),
        line("praseodymium", 30,  [("lree_ore",500),("sulfuric_acid",250),("energy",100000),("water",2500),("paper",50)]),
        line("samarium",     20,  [("lree_ore",600),("hydrochloric_acid",200),("energy",110000),("water",3000),("paper",55)]),
        # HREE from hree_ore
        line("dysprosium",   15,  [("hree_ore",500),("sulfuric_acid",300),("energy",120000),("water",3000),("paper",60)]),
        line("terbium",      10,  [("hree_ore",600),("sulfuric_acid",350),("energy",130000),("water",3500),("paper",65)]),
        line("europium",      8,  [("hree_ore",600),("sulfuric_acid",350),("energy",130000),("water",3500),("paper",65)]),
        line("yttrium",      20,  [("hree_ore",450),("hydrochloric_acid",250),("energy",110000),("water",2800),("paper",55)]),
        line("erbium",       12,  [("hree_ore",550),("sulfuric_acid",320),("energy",120000),("water",3200),("paper",60)]),
        line("gadolinium",   14,  [("hree_ore",520),("sulfuric_acid",310),("energy",115000),("water",3100),("paper",58)]),
        line("scandium",      8,  [("hree_ore",700),("hydrofluoric_acid",200),("energy",150000),("water",4000),("paper",75)]),
        line("holmium",       6,  [("hree_ore",800),("sulfuric_acid",400),("energy",160000),("water",4500),("paper",80)]),
        # Byproduct metals from LREE/HREE processing
        line("indium",       10,  [("hree_ore",300),("sulfuric_acid",200),("energy",100000),("water",2000),("paper",40)]),
        line("tellurium",     8,  [("lree_ore",300),("nitric_acid",150),("energy",90000),("water",2000),("paper",40)]),
        line("germanium",    12,  [("zinc_ore",500),("hydrochloric_acid",200),("energy",120000),("water",3000),("paper",50)]),
        line("tantalum",     15,  [("coltan_ore",400),("hydrofluoric_acid",200),("energy",140000),("water",3500),("paper",60)]),
        line("niobium",      18,  [("coltan_ore",400),("hydrofluoric_acid",200),("energy",130000),("water",3000),("paper",55)]),
        line("rhenium",       3,  [("molybdenum_ore",800),("energy",300000),("water",5000),("paper",100)]),
        line("palladium",     4,  [("platinum_ore",400),("nitric_acid",200),("energy",500000),("water",5000),("paper",120)]),
        line("selenium",     10,  [("copper_ore",500),("nitric_acid",150),("energy",100000),("water",2500),("paper",45)]),
    ]),

    # ── Chemical Plant ──────────────────────────────────────────────────────
    "chemical_plant": dbusiness(
        "Chemical Manufacturing Plant", "Produces industrial acids, bases, and chemical compounds for manufacturing and defense.",
        5000000, 28800, 28000, "district_industrial", [
        line("sulfuric_acid",    500, [("sulfur",200),("water",300),("energy",30000),("paper",20)]),
        line("hydrochloric_acid",400, [("chlorine",200),("water",200),("energy",25000),("paper",18)]),
        line("nitric_acid",      400, [("ammonia",200),("energy",35000),("water",250),("paper",20)]),
        line("hydrofluoric_acid",300, [("fluorite",300),("sulfuric_acid",200),("energy",40000),("water",200),("paper",25)]),
        line("ammonia",          600, [("natural_gas",400),("water",200),("energy",20000),("paper",15)]),
        line("caustic_soda",     500, [("salt",200),("water",200),("energy",35000),("paper",18)]),
        line("chlorine",         400, [("salt",300),("water",150),("energy",40000),("paper",18)]),
        line("phosphoric_acid",  400, [("phosphate_rock",300),("sulfuric_acid",200),("energy",30000),("paper",18)]),
        line("fertilizer_npk",   600, [("ammonia",200),("phosphoric_acid",150),("potash_ore",200),("energy",20000),("paper",15)]),
        line("epoxy_resin",      300, [("plastic",300),("acetone",200),("energy",25000),("paper",20)]),
        line("nitrocellulose",   200, [("cellulose",300),("nitric_acid",200),("sulfuric_acid",150),("energy",40000),("paper",30)]),
        line("smokeless_powder", 200, [("nitrocellulose",200),("nitroglycerin",100),("acetone",100),("energy",30000),("paper",25)]),
        line("rdx_explosive",    150, [("nitric_acid",300),("ammonia",200),("acetone",150),("energy",60000),("paper",40)]),
        line("c4_explosive",     100, [("rdx_explosive",200),("plastic",100),("energy",20000),("paper",20)]),
        line("black_powder",     300, [("potassium_nitrate",200),("sulfur",100),("coal",150),("energy",15000),("paper",15)]),
        line("thermite",         200, [("aluminum",200),("iron_ore",300),("energy",20000),("paper",15)]),
        line("white_phosphorus", 100, [("phosphate_rock",300),("sulfuric_acid",200),("energy",80000),("paper",40)]),
        line("nitroglycerin",    150, [("glycerin",200),("nitric_acid",200),("sulfuric_acid",150),("energy",50000),("paper",35)]),
        line("det_cord",         200, [("nitroglycerin",150),("plastic",100),("energy",20000),("paper",20)]),
        line("activated_carbon", 400, [("coal",400),("steam",200),("energy",30000),("paper",20)]),
        line("potassium_nitrate",500, [("potash_ore",300),("nitric_acid",200),("energy",20000),("paper",15)]),
        line("acid_solution",    800, [("sulfuric_acid",100),("hydrochloric_acid",100),("water",300),("energy",10000),("paper",10)]),
    ]),

    # ── Alloy Forge ─────────────────────────────────────────────────────────
    "alloy_forge": dbusiness(
        "Alloy Forge", "Produces advanced metal alloys and composite materials from refined metals.",
        5500000, 28800, 27000, "district_industrial", [
        line("stainless_steel", 400, [("steel",300),("chromium",100),("nickel",80),("energy",60000),("paper",40)]),
        line("bronze",          300, [("copper",200),("tin",100),("energy",30000),("paper",20)]),
        line("titanium_alloy",  200, [("titanium",200),("aluminum",100),("vanadium",50),("energy",150000),("paper",80)]),
        line("tungsten_carbide",150, [("tungsten",200),("graphite",150),("energy",200000),("paper",100)]),
        line("solder",          400, [("tin",200),("lead",150),("energy",15000),("paper",10)]),
        line("inconel",         200, [("nickel",200),("chromium",100),("iron",100),("energy",100000),("paper",60)]),
        line("maraging_steel",  150, [("steel",200),("nickel",100),("cobalt",60),("molybdenum",40),("energy",120000),("paper",70)]),
        line("duralumin",       300, [("aluminum",200),("copper",80),("manganese",40),("magnesium",40),("energy",60000),("paper",40)]),
        line("nichrome",        250, [("nickel",150),("chromium",100),("energy",50000),("paper",30)]),
        line("monel",           200, [("nickel",150),("copper",100),("energy",70000),("paper",40)]),
        line("cupronickel",     300, [("copper",200),("nickel",100),("energy",40000),("paper",25)]),
        line("phosphor_bronze", 200, [("copper",200),("tin",80),("phosphate_rock",20),("energy",35000),("paper",20)]),
        line("beryllium_copper",150, [("copper",200),("beryllium",50),("energy",80000),("paper",50)]),
        line("nitinol",         100, [("nickel",100),("titanium",100),("energy",120000),("paper",70)]),
        line("depleted_uranium",80,  [("uranium_oxide",200),("energy",150000),("paper",80)]),
        line("boron_carbide",   100, [("graphite",200),("boric_acid",100),("energy",180000),("paper",90)]),
        line("silicon_carbide", 150, [("silicon",200),("graphite",150),("energy",200000),("paper",100)]),
        line("alumina",         300, [("bauxite",400),("caustic_soda",100),("energy",60000),("water",500),("paper",30)]),
        line("carbon_fiber",    150, [("pan_precursor",300),("energy",200000),("water",1000),("paper",100)]),
        line("pan_precursor",   300, [("acrylonitrile",400),("energy",80000),("paper",50)]),
        line("kevlar_fiber",    150, [("ppta_polymer",300),("sulfuric_acid",100),("energy",100000),("paper",60)]),
        line("ppta_polymer",    200, [("phenylenediamine",200),("terephthaloyl_chloride",200),("energy",60000),("paper",40)]),
        line("neodymium_magnet",200, [("neodymium",100),("iron",100),("boron",50),("energy",80000),("paper",50)]),
        line("samarium_cobalt_magnet",100,[("samarium",100),("cobalt",100),("energy",100000),("paper",60)]),
        line("alnico_magnet",   150, [("aluminum",80),("nickel",80),("cobalt",60),("iron",100),("energy",60000),("paper",40)]),
        line("graphite",        400, [("coal",400),("energy",100000),("paper",50)]),
    ]),

    # ── Battery Gigafactory ──────────────────────────────────────────────────
    "battery_gigafactory": dbusiness(
        "Battery Gigafactory", "Manufactures multiple battery chemistries at massive scale for EVs and grid storage.",
        12000000, 28800, 50000, "district_industrial", [
        line("lead_acid_battery", 500, [("lead",400),("sulfuric_acid",300),("plastic",300),("energy",50000),("paper",50)]),
        line("lithium_nmc_cell",  400, [("lithium",300),("nickel",200),("manganese",150),("cobalt",100),("graphite",400),("energy",100000),("paper",100)]),
        line("lfp_cell",          400, [("lithium",300),("iron",200),("phosphoric_acid",150),("graphite",400),("energy",80000),("paper",80)]),
        line("solid_state_cell",  150, [("lithium",200),("lanthanum",80),("zirconium",80),("energy",200000),("paper",150)]),
        line("sodium_ion_cell",   400, [("manganese",200),("iron",150),("graphite",350),("energy",60000),("paper",60)]),
        line("lithium_battery_pack",200,[("lithium_nmc_cell",300),("copper_wire",200),("plastic",200),("processor",20),("energy",30000),("paper",40)]),
        line("hydrogen_fuel_cell",100, [("platinum",20),("titanium",100),("plastic",150),("copper_wire",100),("energy",80000),("paper",80)]),
    ]),

    # ── Advanced Materials Lab (EXPAND existing) ─────────────────────────────
    # Will update via patch, not add as new

    # ── Defense Electronics Factory ──────────────────────────────────────────
    "defense_electronics_factory": dbusiness(
        "Defense Electronics Factory", "Produces advanced military avionics, sensors, guidance systems, and communications equipment.",
        8000000, 28800, 40000, "district_military", [
        line("radar_system",         50,  [("processor",100),("gallium_arsenide",50),("copper_wire",200),("titanium",50),("energy",80000),("paper",80)]),
        line("sonar_system",         40,  [("processor",80),("copper_wire",300),("titanium",40),("energy",70000),("paper",70)]),
        line("fire_control_system",  60,  [("processor",150),("memory_module",100),("circuit_board",80),("energy",60000),("paper",60)]),
        line("inertial_nav_unit",    80,  [("processor",60),("memory_module",40),("circuit_board",40),("energy",50000),("paper",50)]),
        line("night_vision_optic",  100,  [("gallium_arsenide",30),("processor",20),("circuit_board",20),("energy",40000),("paper",40)]),
        line("targeting_optic",     120,  [("glass",100),("circuit_board",30),("copper_wire",50),("energy",30000),("paper",30)]),
        line("encrypted_radio",     100,  [("processor",40),("circuit_board",50),("copper_wire",100),("energy",40000),("paper",40)]),
        line("missile_guidance_unit",50,  [("processor",80),("gallium_arsenide",30),("inertial_nav_unit",30),("energy",80000),("paper",80)]),
        line("drone_avionics",       80,  [("processor",60),("memory_module",40),("circuit_board",50),("energy",50000),("paper",50)]),
        line("avionics_suite",       30,  [("processor",200),("memory_module",150),("circuit_board",100),("lcd_panel",20),("energy",100000),("paper",100)]),
        line("military_radio",       200, [("processor",30),("circuit_board",40),("copper_wire",80),("energy",30000),("paper",30)]),
    ]),

    # ── Armor Systems Factory ────────────────────────────────────────────────
    "armor_systems_factory": dbusiness(
        "Armor Systems Factory", "Manufactures ballistic protection, vehicle armor panels, and blast-resistant materials.",
        6000000, 28800, 32000, "district_military", [
        line("ballistic_plate",      300, [("boron_carbide",200),("silicon_carbide",100),("kevlar_fiber",150),("energy",60000),("paper",50)]),
        line("body_armor",           400, [("ballistic_plate",200),("kevlar_fiber",300),("nylon",100),("energy",40000),("paper",40)]),
        line("combat_helmet",        600, [("kevlar_fiber",200),("aramid_fabric",100),("energy",30000),("paper",30)]),
        line("composite_armor_panel",100, [("steel",300),("alumina",200),("kevlar_fiber",150),("energy",80000),("paper",60)]),
        line("explosive_reactive_armor",80,[("steel",200),("c4_explosive",50),("energy",40000),("paper",40)]),
        line("blast_resistant_glass",150, [("glass",400),("polycarbonate",200),("energy",50000),("paper",40)]),
        line("depleted_uranium",      50, [("uranium_oxide",150),("energy",120000),("paper",80)]),
    ]),

    # ── Jet Engine Factory ───────────────────────────────────────────────────
    "jet_engine_factory": dbusiness(
        "Jet Engine Factory", "Produces turbojet, turbofan, and rocket motor propulsion systems.",
        10000000, 28800, 45000, "district_aerospace", [
        line("jet_turbine_blade",   200, [("inconel",300),("titanium_alloy",100),("rhenium",10),("energy",200000),("paper",150)]),
        line("turbojet_engine",      30, [("jet_turbine_blade",100),("inconel",200),("titanium_alloy",100),("steel",200),("energy",500000),("paper",300)]),
        line("turbofan_engine",      20, [("jet_turbine_blade",150),("inconel",300),("titanium_alloy",150),("steel",300),("energy",700000),("paper",400)]),
        line("rocket_motor",         50, [("maraging_steel",200),("smokeless_powder",300),("titanium_alloy",100),("energy",300000),("paper",200)]),
        line("gas_turbine",          40, [("inconel",400),("steel",300),("titanium",100),("energy",400000),("paper",250)]),
        line("diesel_engine",       100, [("steel",400),("aluminum",200),("copper",100),("energy",100000),("paper",80)]),
        line("ejection_seat",        30, [("maraging_steel",100),("rocket_motor",10),("titanium_alloy",50),("energy",80000),("paper",60)]),
    ]),

    # ── Weapons Manufacturing (EXPAND existing) ──────────────────────────────
    # Will add lines to existing weapons_factory

    # ── Military Vehicle Plant (EXPAND existing) ─────────────────────────────
    # Will add lines to existing military_vehicle_plant

    # ── Energy Infrastructure Factory ───────────────────────────────────────
    "energy_infrastructure_factory": dbusiness(
        "Energy Infrastructure Factory", "Manufactures power generation and grid infrastructure components.",
        9000000, 28800, 42000, "district_industrial", [
        line("solar_panel",          500, [("silicon_wafer",400),("silver",50),("aluminum",200),("glass",300),("energy",60000),("paper",50)]),
        line("wind_turbine_blade",    50, [("carbon_fiber",300),("fiberglass",500),("epoxy_resin",200),("energy",100000),("paper",80)]),
        line("transformer",          100, [("silicon_steel",300),("copper_wire",500),("steel",300),("energy",80000),("paper",60)]),
        line("nuclear_reactor_core",   5, [("uranium_oxide",500),("zirconium",200),("stainless_steel",300),("energy",500000),("paper",300)]),
        line("nuclear_waste_container",20,[("stainless_steel",400),("depleted_uranium",100),("concrete",300),("energy",100000),("paper",80)]),
    ]),

    # ── Medical Equipment Manufacturing (EXPAND existing) ───────────────────
    # Will add lines to existing medical_equipment_factory

    # ── Shipyard military expansion ──────────────────────────────────────────
    "military_shipyard": dbusiness(
        "Military Shipyard", "Constructs naval destroyers, submarines, and support vessels.",
        20000000, 57600, 80000, "district_shipyard", [
        line("destroyer_hull",    5, [("stainless_steel",2000),("titanium_alloy",500),("aluminum",1000),("energy",2000000),("paper",500)]),
        line("submarine_hull",    3, [("maraging_steel",1500),("titanium_alloy",800),("stainless_steel",1000),("energy",3000000),("paper",600)]),
        line("torpedo",          50, [("maraging_steel",100),("rdx_explosive",80),("rocket_motor",20),("missile_guidance_unit",20),("energy",100000),("paper",80)]),
        line("naval_gun_system", 20, [("steel",400),("titanium_alloy",100),("electronics_package",20),("energy",200000),("paper",100)]),
        line("naval_destroyer",   2, [("destroyer_hull",1),("turbofan_engine",4),("naval_gun_system",4),("radar_system",4),("sonar_system",2),("missile",20),("energy",5000000),("paper",1000)]),
        line("submarine",         1, [("submarine_hull",1),("nuclear_reactor_core",1),("torpedo",20),("sonar_system",4),("fire_control_system",2),("energy",8000000),("paper",1500)]),
    ]),
}

print(f"Defined {len(NEW_DISTRICT_BUSINESSES)} new district businesses")

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 4 — ADDITIONS TO EXISTING DISTRICT BUSINESSES
# ══════════════════════════════════════════════════════════════════════════════

# Lines to ADD to existing weapons_factory
WEAPONS_FACTORY_NEW_LINES = [
    line("rifle_barrel",     500, [("steel",200),("molybdenum",50),("energy",40000),("paper",30)]),
    line("rifle_receiver",   400, [("aluminum",200),("steel",100),("energy",40000),("paper",30)]),
    line("rifle",            300, [("rifle_barrel",200),("rifle_receiver",200),("steel",100),("energy",30000),("paper",30)]),
    line("grenade_body",     500, [("steel",200),("rdx_explosive",100),("energy",20000),("paper",20)]),
    line("grenade",          400, [("grenade_body",300),("smokeless_powder",100),("energy",15000),("paper",15)]),
    line("missile_warhead",  100, [("rdx_explosive",200),("thermite",50),("maraging_steel",100),("energy",40000),("paper",40)]),
    line("missile",           80, [("missile_warhead",50),("rocket_motor",30),("missile_guidance_unit",30),("maraging_steel",100),("energy",80000),("paper",80)]),
    line("ammunition",      2000, [("brass",400),("lead",200),("smokeless_powder",200),("energy",20000),("paper",20)]),
    line("ammunition_crate",  50, [("ammunition",1000),("wood",100),("steel",50),("energy",5000),("paper",10)]),
    line("det_cord",         200, [("nitroglycerin",100),("plastic",100),("energy",15000),("paper",15)]),
]

# Lines to ADD to existing military_vehicle_plant
MILITARY_VEHICLE_PLANT_NEW_LINES = [
    line("tank_hull",        20, [("stainless_steel",500),("composite_armor_panel",100),("titanium_alloy",100),("energy",200000),("paper",150)]),
    line("tank_turret",      20, [("steel",400),("composite_armor_panel",80),("tungsten_carbide",50),("energy",150000),("paper",120)]),
    line("tank_cannon",      20, [("tungsten_carbide",200),("maraging_steel",200),("energy",100000),("paper",100)]),
    line("tank",              8, [("tank_hull",1),("tank_turret",1),("tank_cannon",1),("diesel_engine",2),("fire_control_system",1),("energy",400000),("paper",200)]),
    line("apc_hull",         30, [("stainless_steel",400),("composite_armor_panel",60),("aluminum",200),("energy",150000),("paper",100)]),
    line("apc",              15, [("apc_hull",1),("diesel_engine",1),("fire_control_system",1),("machine_gun",2),("energy",200000),("paper",150)]),
    line("military_truck",   50, [("steel",300),("diesel_engine",1),("aluminum",100),("energy",80000),("paper",60)]),
    line("infantry_fighting_vehicle",10,[("apc_hull",1),("diesel_engine",1),("fire_control_system",1),("missile",4),("energy",250000),("paper",180)]),
    line("self_propelled_artillery", 5,[("tank_hull",1),("tank_cannon",2),("diesel_engine",2),("fire_control_system",1),("energy",350000),("paper",200)]),
    line("armored_car",      30, [("stainless_steel",200),("blast_resistant_glass",20),("diesel_engine",1),("energy",100000),("paper",80)]),
]

# Lines to ADD to existing military_aircraft_plant
MILITARY_AIRCRAFT_PLANT_NEW_LINES = [
    line("jet_airframe",     15, [("titanium_alloy",500),("carbon_fiber",400),("duralumin",300),("energy",300000),("paper",200)]),
    line("helicopter_rotor", 20, [("titanium_alloy",200),("carbon_fiber",200),("duralumin",150),("energy",150000),("paper",100)]),
    line("fighter_jet",       5, [("jet_airframe",1),("turbojet_engine",2),("avionics_suite",1),("fire_control_system",1),("ejection_seat",1),("missile",4),("energy",1000000),("paper",500)]),
    line("attack_helicopter", 8, [("helicopter_rotor",1),("turbofan_engine",1),("avionics_suite",1),("fire_control_system",1),("missile",4),("energy",600000),("paper",350)]),
    line("transport_helicopter",10,[("helicopter_rotor",1),("turbofan_engine",1),("avionics_suite",1),("energy",400000),("paper",250)]),
    line("military_drone",   30, [("drone_avionics",1),("carbon_fiber",100),("lithium_battery_pack",2),("encrypted_radio",1),("energy",80000),("paper",60)]),
    line("drone_swarm_unit", 10, [("drone_avionics",5),("carbon_fiber",50),("lithium_battery_pack",5),("encrypted_radio",1),("energy",100000),("paper",80)]),
]

# Lines to ADD to existing medical_equipment_factory
MEDICAL_EQUIPMENT_FACTORY_NEW_LINES = [
    line("mri_machine",        5, [("neodymium_magnet",50),("processor",100),("titanium",100),("copper_wire",500),("energy",200000),("paper",150)]),
    line("ct_scanner",         8, [("processor",80),("tungsten",50),("aluminum",100),("copper_wire",300),("energy",150000),("paper",120)]),
    line("ventilator",        30, [("processor",20),("plastic",100),("copper_wire",50),("energy",30000),("paper",30)]),
    line("surgical_robot",     3, [("processor",200),("titanium_alloy",100),("carbon_fiber",50),("energy",300000),("paper",200)]),
    line("dialysis_machine",  10, [("processor",30),("plastic",150),("copper_wire",100),("energy",60000),("paper",50)]),
    line("radiation_therapy_unit",3,[("processor",100),("tungsten_carbide",50),("titanium",80),("energy",400000),("paper",250)]),
]

# Lines to ADD to advanced_materials_lab
ADVANCED_MATERIALS_LAB_NEW_LINES = [
    line("industrial_robot_arm", 10, [("stainless_steel",200),("titanium_alloy",100),("processor",50),("neodymium_magnet",30),("energy",150000),("paper",100)]),
    line("cnc_machine",         15, [("stainless_steel",300),("tungsten_carbide",100),("processor",40),("energy",120000),("paper",80)]),
    line("3d_printer_industrial",10,[("stainless_steel",200),("processor",30),("titanium_alloy",50),("energy",100000),("paper",80)]),
]

# Lines to ADD to existing electronics_factory
ELECTRONICS_FACTORY_NEW_LINES = [
    line("night_vision_optic", 80, [("gallium_arsenide",30),("processor",20),("circuit_board",20),("energy",40000),("paper",40)]),
    line("targeting_optic",   100, [("glass",100),("circuit_board",30),("copper_wire",50),("energy",30000),("paper",30)]),
]

print("Defined all business additions/fixes")

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 5 — MISSING RETAIL/SERVICE ITEMS (produced by district businesses
#            but not currently defined in item_types.json)
# ══════════════════════════════════════════════════════════════════════════════

MISSING_SERVICE_ITEMS = {
    # District outputs that need item_type definitions
    "airline_ticket":           item("Airline Ticket",          "services", "Commercial airline ticket for domestic or international travel."),
    "animal_adoption":          item("Animal Adoption",         "services", "Adoption package for shelter or zoo animal."),
    "bachelors_degree":         item("Bachelor's Degree",       "services", "Four-year undergraduate university degree credential."),
    "base_housing":             item("Base Housing",            "services", "Military on-base housing allocation and support service."),
    "beauty_kit":               item("Beauty Kit",              "retail_shopping", "Personal care and cosmetics bundle."),
    "bedroom_set":              item("Bedroom Set",             "home_goods", "Bed frame, mattress, and dresser furniture package."),
    "behind_scenes_tour":       item("Behind the Scenes Tour",  "services", "Exclusive backstage entertainment venue tour."),
    "beverage_package":         item("Beverage Package",        "retail_food", "Mixed beverage assortment bundle."),
    "casbah_private_dining":    item("Casbah Private Dining",   "services", "Exclusive private dining experience at a Casbah-style venue."),
    "casino_night":             item("Casino Night",            "services", "Casino entertainment package including gaming and dining."),
    "charter_service":          item("Charter Service",         "services", "Private aircraft or vessel charter service."),
    "commissary_package":       item("Commissary Package",      "retail_prison", "Inmate commissary goods bundle from prison store."),
    "concert_package":          item("Concert Package",         "services", "Concert tickets plus backstage access bundle."),
    "conservation_membership":  item("Conservation Membership", "services", "Annual zoo or wildlife conservation membership."),
    "cruise_package":           item("Cruise Package",          "services", "All-inclusive cruise vacation package."),
    "defense_contract":         item("Defense Contract",        "services", "Government defense procurement contract fulfillment."),
    "dessert_sampler":          item("Dessert Sampler",         "retail_food", "Assorted dessert tasting selection."),
    "diagnostic_panel":         item("Diagnostic Panel",        "services", "Comprehensive medical diagnostic test panel."),
    "electronics_package":      item("Electronics Package",     "retail_shopping", "Consumer electronics bundle."),
    "emergency_room_visit":     item("Emergency Room Visit",    "services", "Emergency medical care service."),
    "fashion_bundle":           item("Fashion Bundle",          "retail_shopping", "Curated apparel and accessories package."),
    "fast_food_combo":          item("Fast Food Combo",         "retail_food", "Value meal combo from fast food establishment."),
    "field_gear_set":           item("Field Gear Set",          "services", "Military field equipment and gear package."),
    "freight_contract":         item("Freight Contract",        "services", "Commercial cargo shipping contract."),
    "furnishing_set":           item("Furnishing Set",          "home_goods", "Complete room furnishing bundle."),
    "high_school_diploma":      item("High School Diploma",     "services", "Secondary education completion credential."),
    "home_maintenance_package": item("Home Maintenance Package","services", "Residential maintenance and repair service bundle."),
    "inmate_housing":           item("Inmate Housing",          "retail_prison", "Correctional facility housing and basic services."),
    "international_platter":    item("International Platter",   "retail_food", "Assorted international cuisine food platter."),
    "internet_bundle":          item("Internet Bundle",         "services", "Broadband internet service package."),
    "kids_meal":                item("Kids Meal",               "retail_food", "Children's meal with toy at family restaurant."),
    "kitchen_package":          item("Kitchen Package",         "home_goods", "Kitchen appliance and cookware bundle."),
    "lawn_service":             item("Lawn Service",            "services", "Residential lawn care and landscaping service."),
    "legal_aid":                item("Legal Aid",               "services", "Legal representation and advice service."),
    "living_room_set":          item("Living Room Set",         "home_goods", "Sofa, coffee table, and entertainment unit package."),
    "logistics_contract":       item("Logistics Contract",      "services", "Supply chain and logistics management contract."),
    "masters_degree":           item("Master's Degree",         "services", "Graduate-level academic degree credential."),
    "maternity_package":        item("Maternity Package",       "services", "Prenatal care and delivery medical service bundle."),
    "medical_supply_kit":       item("Medical Supply Kit",      "health", "Emergency and first aid medical supply bundle."),
    "medina_feast":             item("Medina Feast",            "retail_food", "Traditional Medina-style multi-course feast."),
    "military_training":        item("Military Training",       "services", "Military skills and readiness training program."),
    "mint_tea_ceremony":        item("Mint Tea Ceremony",       "retail_food", "Traditional Moroccan mint tea service ceremony."),
    "monthly_utility_bill":     item("Monthly Utility Bill",    "services", "Combined electricity, water, and gas utility service."),
    "moroccan_evening":         item("Moroccan Evening",        "services", "Themed Moroccan cultural dining and entertainment experience."),
    "movie_premier":            item("Movie Premiere",          "services", "Exclusive film premiere event ticket and experience."),
    "nightclub_vip":            item("Nightclub VIP",           "services", "VIP nightclub access and bottle service package."),
    "office_furniture":         item("Office Furniture",        "home_goods", "Desk, chair, and filing cabinet office furniture set."),
    "prescription_bundle":      item("Prescription Bundle",     "health", "Prescribed medication fulfillment package."),
    "rail_pass":                item("Rail Pass",               "services", "Multi-ride railway transit pass."),
    "ration_pack":              item("Ration Pack",             "retail_food", "Military or emergency food ration package."),
    "reentry_package":          item("Reentry Package",         "retail_prison", "Post-incarceration reintegration support bundle."),
    "rehabilitation_program":   item("Rehabilitation Program",  "retail_prison", "Inmate rehabilitation and skills development program."),
    "rental_car":               item("Rental Car",              "services", "Vehicle rental service."),
    "research_grant":           item("Research Grant",          "services", "Academic or industrial research funding award."),
    "safari_tour":              item("Safari Tour",             "services", "Guided wildlife safari experience."),
    "security_clearance":       item("Security Clearance",      "services", "Government security clearance vetting and issuance service."),
    "security_package":         item("Security Package",        "services", "Comprehensive physical security service bundle."),
    "sporting_goods":           item("Sporting Goods",          "retail_shopping", "Sports equipment and athletic gear bundle."),
    "sports_package":           item("Sports Package",          "services", "Sports event tickets and fan experience package."),
    "study_abroad":             item("Study Abroad Program",    "services", "International educational exchange program."),
    "surgery_package":          item("Surgery Package",         "services", "Elective or necessary surgical procedure bundle."),
    "theme_park_pass":          item("Theme Park Pass",         "services", "Multi-day theme park admission pass."),
    "therapy_program":          item("Therapy Program",         "services", "Mental health or physical therapy treatment program."),
    "toy_bundle":               item("Toy Bundle",              "retail_shopping", "Children's toy assortment package."),
    "uniform_kit":              item("Uniform Kit",             "services", "Complete uniform and equipment kit."),
    "veterans_package":         item("Veterans Package",        "services", "Military veteran benefits and support services bundle."),
    "vocational_certificate":   item("Vocational Certificate",  "services", "Vocational training completion credential."),
    "waste_service":            item("Waste Service",           "services", "Municipal waste collection and disposal service."),
    "wildlife_program":         item("Wildlife Program",        "services", "Wildlife conservation and education program."),
    "work_release":             item("Work Release Program",    "retail_prison", "Supervised work release program for qualifying inmates."),
    "zoo_pass":                 item("Zoo Pass",                "services", "Annual zoo admission pass."),
}

print(f"Defined {len(MISSING_SERVICE_ITEMS)} missing service/retail items")

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 6 — APPLY ALL CHANGES
# ══════════════════════════════════════════════════════════════════════════════

print("\n=== Applying changes ===")

# ── Load files ────────────────────────────────────────────────────────────────
with open("item_types.json") as f:
    items = json.load(f)
with open("business_types.json") as f:
    biz = json.load(f)
with open("district_businesses.json") as f:
    dbiz = json.load(f)

# ── 6a. Add all new items to item_types.json ──────────────────────────────────
added_items = 0
for key, val in {**NEW_ITEMS, **MISSING_SERVICE_ITEMS}.items():
    if key not in items:
        items[key] = val
        added_items += 1
    else:
        print(f"  [SKIP] item already exists: {key}")
print(f"Added {added_items} new items to item_types.json")

# ── 6b. Fix mineral_mine: add new ore lines ───────────────────────────────────
existing_mine_outputs = {l["output_item"] for l in biz["mineral_mine"]["production_lines"]}
added_mine = 0
for new_line in MINERAL_MINE_NEW_LINES:
    if new_line["output_item"] not in existing_mine_outputs:
        biz["mineral_mine"]["production_lines"].append(new_line)
        added_mine += 1
print(f"Added {added_mine} ore lines to mineral_mine")

# ── 6c. Fix refinery brass recipe (line index 2 uses zinc_ore → fix to zinc) ─
old_brass = biz["refinery"]["production_lines"][2]
assert old_brass["output_item"] == "brass", f"Expected brass at index 2, got {old_brass['output_item']}"
biz["refinery"]["production_lines"][2] = REFINERY_FIXED_BRASS
print("Fixed brass recipe (zinc_ore → zinc)")

# ── 6d. Add new refined metal lines to refinery ───────────────────────────────
existing_refinery_outputs = {l["output_item"] for l in biz["refinery"]["production_lines"]}
added_ref = 0
for new_line in REFINERY_NEW_LINES:
    if new_line["output_item"] not in existing_refinery_outputs:
        biz["refinery"]["production_lines"].append(new_line)
        added_ref += 1
print(f"Added {added_ref} refined metal lines to refinery")

# ── 6e. Fix aluminum_foundry (iron_ore → bauxite) ────────────────────────────
old_al = dbiz["aluminum_foundry"]["production_lines"][0]
assert old_al["output_item"] == "aluminum", f"Expected aluminum at index 0"
dbiz["aluminum_foundry"]["production_lines"][0] = ALUMINUM_FOUNDRY_FIXED_LINE
# Add gallium byproduct line
existing_al_outputs = {l["output_item"] for l in dbiz["aluminum_foundry"]["production_lines"]}
for nl in ALUMINUM_FOUNDRY_EXTRA_LINES:
    if nl["output_item"] not in existing_al_outputs:
        dbiz["aluminum_foundry"]["production_lines"].append(nl)
print("Fixed aluminum_foundry recipe (iron_ore → bauxite) + gallium byproduct")

# ── 6f. Fix semiconductor_fab lines ──────────────────────────────────────────
for idx, fixed_line in SEMICONDCTOR_FAB_FIXED_LINES.items():
    old = dbiz["semiconductor_fab"]["production_lines"][idx]
    dbiz["semiconductor_fab"]["production_lines"][idx] = fixed_line
    print(f"Fixed semiconductor_fab line {idx}: {old['output_item']} recipe updated")

# Add new semiconductor lines
existing_semi_outputs = {l["output_item"] for l in dbiz["semiconductor_fab"]["production_lines"]}
added_semi = 0
for nl in SEMICONDUCTOR_FAB_NEW_LINES:
    if nl["output_item"] not in existing_semi_outputs:
        dbiz["semiconductor_fab"]["production_lines"].append(nl)
        added_semi += 1
print(f"Added {added_semi} new lines to semiconductor_fab")

# ── 6g. Add lines to existing weapons_factory ────────────────────────────────
existing_wpn_outputs = {l["output_item"] for l in dbiz["weapons_factory"]["production_lines"]}
added_wpn = 0
for nl in WEAPONS_FACTORY_NEW_LINES:
    if nl["output_item"] not in existing_wpn_outputs:
        dbiz["weapons_factory"]["production_lines"].append(nl)
        added_wpn += 1
print(f"Added {added_wpn} new lines to weapons_factory")

# ── 6h. Add lines to existing military_vehicle_plant ─────────────────────────
existing_mvp_outputs = {l["output_item"] for l in dbiz["military_vehicle_plant"]["production_lines"]}
added_mvp = 0
for nl in MILITARY_VEHICLE_PLANT_NEW_LINES:
    if nl["output_item"] not in existing_mvp_outputs:
        dbiz["military_vehicle_plant"]["production_lines"].append(nl)
        added_mvp += 1
print(f"Added {added_mvp} new lines to military_vehicle_plant")

# ── 6i. Add lines to existing military_aircraft_plant ────────────────────────
existing_map_outputs = {l["output_item"] for l in dbiz["military_aircraft_plant"]["production_lines"]}
added_map = 0
for nl in MILITARY_AIRCRAFT_PLANT_NEW_LINES:
    if nl["output_item"] not in existing_map_outputs:
        dbiz["military_aircraft_plant"]["production_lines"].append(nl)
        added_map += 1
print(f"Added {added_map} new lines to military_aircraft_plant")

# ── 6j. Add lines to existing medical_equipment_factory ──────────────────────
existing_med_outputs = {l["output_item"] for l in dbiz["medical_equipment_factory"]["production_lines"]}
added_med = 0
for nl in MEDICAL_EQUIPMENT_FACTORY_NEW_LINES:
    if nl["output_item"] not in existing_med_outputs:
        dbiz["medical_equipment_factory"]["production_lines"].append(nl)
        added_med += 1
print(f"Added {added_med} new lines to medical_equipment_factory")

# ── 6k. Add lines to advanced_materials_lab ──────────────────────────────────
existing_aml_outputs = {l["output_item"] for l in dbiz["advanced_materials_lab"]["production_lines"]}
added_aml = 0
for nl in ADVANCED_MATERIALS_LAB_NEW_LINES:
    if nl["output_item"] not in existing_aml_outputs:
        dbiz["advanced_materials_lab"]["production_lines"].append(nl)
        added_aml += 1
print(f"Added {added_aml} new lines to advanced_materials_lab")

# ── 6l. Add lines to electronics_factory ─────────────────────────────────────
existing_ef_outputs = {l["output_item"] for l in dbiz["electronics_factory"]["production_lines"]}
added_ef = 0
for nl in ELECTRONICS_FACTORY_NEW_LINES:
    if nl["output_item"] not in existing_ef_outputs:
        dbiz["electronics_factory"]["production_lines"].append(nl)
        added_ef += 1
print(f"Added {added_ef} new lines to electronics_factory")

# ── 6m. Add new district businesses ─────────────────────────────────────────
added_dbiz = 0
for key, val in NEW_DISTRICT_BUSINESSES.items():
    if key not in dbiz:
        dbiz[key] = val
        added_dbiz += 1
    else:
        print(f"  [SKIP] district business already exists: {key}")
print(f"Added {added_dbiz} new district businesses")

# ── 6n. Write all files ───────────────────────────────────────────────────────
with open("item_types.json", "w") as f:
    json.dump(items, f, indent=2, sort_keys=True)
print("Saved item_types.json")

with open("business_types.json", "w") as f:
    json.dump(biz, f, indent=2, sort_keys=True)
print("Saved business_types.json")

with open("district_businesses.json", "w") as f:
    json.dump(dbiz, f, indent=2, sort_keys=True)
print("Saved district_businesses.json")

print("\n=== DONE ===")
