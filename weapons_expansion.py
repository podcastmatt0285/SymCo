"""
Weapons Expansion Script
- Replaces generic weapons (fighter_jet, rifle, tank, naval_destroyer, submarine, military_helicopter)
  with ~70+ real-world country-specific named variants tied to the 15 reserve banking nations.
- Removes generic production lines from factories.
- Adds named variant production lines.
- Updates military_base_district + tactical_gear_factory downstream consumers.
"""
import json, copy

# ─────────────────────────────────────────────────────────────────────────────
# 1. LOAD ALL FILES
# ─────────────────────────────────────────────────────────────────────────────
with open("district_items.json") as f:
    di = json.load(f)
with open("district_businesses.json") as f:
    db = json.load(f)

# ─────────────────────────────────────────────────────────────────────────────
# 2. NEW ITEM DEFINITIONS — all go into district_items.json
# ─────────────────────────────────────────────────────────────────────────────
NEW_ITEMS = {

    # ── RIFLES ──────────────────────────────────────────────────────────────
    "m4_carbine": {
        "name": "M4A1 Carbine",
        "description": "Standard-issue US assault rifle. Compact, lightweight, and NATO-caliber.",
        "category": "military"
    },
    "m249_saw": {
        "name": "M249 SAW",
        "description": "US squad automatic weapon. Provides sustained fire support at the fireteam level.",
        "category": "military"
    },
    "ak_47": {
        "name": "AK-47",
        "description": "Iconic Russian assault rifle. Renowned for rugged reliability in any environment.",
        "category": "military"
    },
    "ak_74m": {
        "name": "AK-74M",
        "description": "Modernized Russian rifle chambered in 5.45×39mm. Lighter and more accurate than its predecessor.",
        "category": "military"
    },
    "hk416": {
        "name": "HK416",
        "description": "German assault rifle by Heckler & Koch. Short-stroke gas piston system favored by NATO special forces.",
        "category": "military"
    },
    "hk_g36": {
        "name": "HK G36",
        "description": "German polymer-bodied assault rifle. Standard issue for the Bundeswehr.",
        "category": "military"
    },
    "l85a2": {
        "name": "L85A2",
        "description": "British SA80-series bullpup assault rifle. Standard issue for UK armed forces.",
        "category": "military"
    },
    "famas_f1": {
        "name": "FAMAS F1",
        "description": "French bullpup assault rifle. Distinctive silhouette of the Armée de Terre.",
        "category": "military"
    },
    "qbz_95": {
        "name": "QBZ-95",
        "description": "Chinese bullpup assault rifle. Standard infantry weapon of the People's Liberation Army.",
        "category": "military"
    },
    "insas_rifle": {
        "name": "INSAS Assault Rifle",
        "description": "India's domestically designed assault rifle. Produced by the Ordnance Factories Board.",
        "category": "military"
    },
    "k2_rifle": {
        "name": "K2 Assault Rifle",
        "description": "South Korean assault rifle. Standard issue for the Republic of Korea Army.",
        "category": "military"
    },
    "mpt_76": {
        "name": "MPT-76",
        "description": "Turkish assault rifle produced domestically by MKE. Replaces aging G3 rifles in Turkish service.",
        "category": "military"
    },
    "vektor_r4": {
        "name": "Vektor R4",
        "description": "South African assault rifle derived from the Israeli Galil. Standard issue for SANDF troops.",
        "category": "military"
    },
    "howa_type89": {
        "name": "Howa Type 89",
        "description": "Japanese Self-Defense Force assault rifle produced by Howa Machinery. Successor to the Type 64.",
        "category": "military"
    },
    "sig_sg550": {
        "name": "SIG SG 550",
        "description": "Swiss precision assault rifle. Exceptionally accurate and reliable in all conditions.",
        "category": "military"
    },
    "fx05_xiuhcoatl": {
        "name": "FX-05 Xiuhcoatl",
        "description": "Mexican bullpup assault rifle designed and produced by SEDENA. Named for the Aztec fire serpent.",
        "category": "military"
    },
    "imbel_md97": {
        "name": "IMBEL MD97",
        "description": "Brazilian assault rifle developed from the FAL design by IMBEL. Used by Brazilian Army and Marines.",
        "category": "military"
    },
    "caracal_car816": {
        "name": "Caracal CAR 816",
        "description": "UAE-designed modular assault rifle. Adopted by the UAE armed forces and police.",
        "category": "military"
    },

    # ── FIGHTER JETS ─────────────────────────────────────────────────────────
    "f22_raptor": {
        "name": "F-22 Raptor",
        "description": "US 5th-generation stealth air superiority fighter. The most capable air-dominance aircraft ever built.",
        "category": "military"
    },
    "f35_lightning": {
        "name": "F-35 Lightning II",
        "description": "US multirole stealth strike fighter. Three variants serve the USAF, Navy, and Marine Corps.",
        "category": "military"
    },
    "f16_falcon": {
        "name": "F-16 Fighting Falcon",
        "description": "US lightweight multirole fighter. The most widely operated combat aircraft in the world.",
        "category": "military"
    },
    "f15_eagle": {
        "name": "F-15 Eagle",
        "description": "US air superiority fighter with an undefeated 104-0 combat record.",
        "category": "military"
    },
    "su57_felon": {
        "name": "Su-57 Felon",
        "description": "Russian 5th-generation stealth multirole fighter. Sukhoi's most advanced combat aircraft.",
        "category": "military"
    },
    "su35_flanker": {
        "name": "Su-35 Flanker-E",
        "description": "Russian 4++ generation supermaneuverable air superiority fighter. Thrust-vectoring engines give extreme agility.",
        "category": "military"
    },
    "mig29_fulcrum": {
        "name": "MiG-29 Fulcrum",
        "description": "Russian twin-engine tactical fighter. Widely exported and operated across Eastern Europe, Asia, and Africa.",
        "category": "military"
    },
    "rafale": {
        "name": "Dassault Rafale",
        "description": "French omnirole 4.5-generation fighter. Combat-proven over Libya, Mali, Syria, and Iraq.",
        "category": "military"
    },
    "eurofighter_typhoon": {
        "name": "Eurofighter Typhoon",
        "description": "European multirole air superiority fighter. Built jointly by UK, Germany, Italy, and Spain.",
        "category": "military"
    },
    "j20_chengdu": {
        "name": "Chengdu J-20",
        "description": "Chinese 5th-generation stealth fighter. The PLAAF's premier air superiority and strike platform.",
        "category": "military"
    },
    "j16_flanker": {
        "name": "J-16 Strike Flanker",
        "description": "Chinese 4th-generation multirole strike aircraft. Upgraded Flanker derivative with AESA radar.",
        "category": "military"
    },
    "hal_tejas": {
        "name": "HAL Tejas",
        "description": "Indian light combat aircraft designed by HAL and ADA. The IAF's domestically developed 4th-gen fighter.",
        "category": "military"
    },
    "kf21_boramae": {
        "name": "KF-21 Boramae",
        "description": "South Korean 4.5-generation multirole fighter developed by KAI. Advanced AESA radar and IRST.",
        "category": "military"
    },
    "tai_tfx": {
        "name": "TAI TF-X Kaan",
        "description": "Turkish 5th-generation stealth multirole fighter developed by Turkish Aerospace Industries.",
        "category": "military"
    },

    # ── MILITARY HELICOPTERS ─────────────────────────────────────────────────
    "ah64_apache": {
        "name": "AH-64E Apache",
        "description": "US twin-engine attack helicopter. The primary anti-armor helicopter of the US Army.",
        "category": "military"
    },
    "uh60_blackhawk": {
        "name": "UH-60 Black Hawk",
        "description": "US utility tactical transport helicopter. Ubiquitous US Army and special-operations workhorse.",
        "category": "military"
    },
    "ka52_alligator": {
        "name": "Ka-52 Alligator",
        "description": "Russian twin-engine attack helicopter with a unique coaxial rotor system and all-weather capability.",
        "category": "military"
    },
    "mi24_hind": {
        "name": "Mi-24 Hind",
        "description": "Russian gunship and troop transport. Feared as the 'Flying Tank' for its combination of firepower and lift.",
        "category": "military"
    },
    "airbus_h225m": {
        "name": "Airbus H225M Caracal",
        "description": "French medium military helicopter. Used for special-operations insertion and combat search-and-rescue.",
        "category": "military"
    },
    "z10_thunderbolt": {
        "name": "Z-10 Thunderbolt",
        "description": "Chinese dedicated attack helicopter developed by AVIC. The PLAGF's primary anti-armor rotorcraft.",
        "category": "military"
    },
    "t129_atak": {
        "name": "TAI T129 ATAK",
        "description": "Turkish attack helicopter developed jointly with Italy's Leonardo. Derived from the AW129 Mangusta.",
        "category": "military"
    },
    "hal_dhruv": {
        "name": "HAL Dhruv",
        "description": "Indian advanced light helicopter produced by HAL. Serves all four Indian armed services.",
        "category": "military"
    },

    # ── TANKS ────────────────────────────────────────────────────────────────
    "m1a2_abrams": {
        "name": "M1A2 SEPv3 Abrams",
        "description": "US main battle tank. Depleted-uranium armor, 120mm smoothbore gun, and a gas turbine engine.",
        "category": "military"
    },
    "t90m_proryv": {
        "name": "T-90M Proryv",
        "description": "Russian modernized main battle tank. Improved Relikt ERA, Kalina fire-control system, and new turret.",
        "category": "military"
    },
    "t14_armata": {
        "name": "T-14 Armata",
        "description": "Russian next-generation MBT with an unmanned turret and active protection system. Future of Russian armor.",
        "category": "military"
    },
    "leopard_2a7": {
        "name": "Leopard 2A7",
        "description": "German main battle tank. Widely regarded as one of the finest in the world. Rheinmetall 120mm gun.",
        "category": "military"
    },
    "amx_leclerc": {
        "name": "AMX-56 Leclerc",
        "description": "French main battle tank with an integrated autoloader and advanced digital battle management system.",
        "category": "military"
    },
    "challenger_3": {
        "name": "Challenger 3",
        "description": "British main battle tank. Upgraded with a Rheinmetall 120mm smoothbore gun and new fire-control system.",
        "category": "military"
    },
    "type_99a": {
        "name": "Type 99A",
        "description": "Chinese 3rd-generation main battle tank. The PLA's most capable armored platform with active protection.",
        "category": "military"
    },
    "arjun_mk2": {
        "name": "Arjun Mk.2",
        "description": "Indian main battle tank developed by DRDO. Fully domestically designed with reactive armor upgrades.",
        "category": "military"
    },
    "k2_black_panther": {
        "name": "K2 Black Panther",
        "description": "South Korean main battle tank by Hyundai Rotem. Among the world's most technologically advanced MBTs.",
        "category": "military"
    },
    "altay_tank": {
        "name": "Altay MBT",
        "description": "Turkish main battle tank developed by Otokar and BMC. Turkey's first fully indigenous MBT program.",
        "category": "military"
    },
    "type10_tank": {
        "name": "Type 10",
        "description": "Japanese 4th-generation MBT optimized for Japan's mountainous terrain. Light, agile, and highly networked.",
        "category": "military"
    },
    "ee_t1_osorio": {
        "name": "EE-T1 Osório",
        "description": "Brazilian main battle tank designed by Engesa. Powerful export competitor with French GIAT 120mm gun.",
        "category": "military"
    },

    # ── NAVAL VESSELS — Aircraft Carriers ────────────────────────────────────
    "ford_class_carrier": {
        "name": "Gerald R. Ford-class Carrier",
        "description": "US nuclear-powered supercarrier displacing 100,000 tons. The most powerful warship ever built.",
        "category": "military"
    },
    "queen_elizabeth_carrier": {
        "name": "Queen Elizabeth-class Carrier",
        "description": "British conventional carrier capable of deploying 36 F-35B Lightning II fighters.",
        "category": "military"
    },
    "charles_degaulle_carrier": {
        "name": "Charles de Gaulle-class Carrier",
        "description": "French nuclear-powered aircraft carrier. The only nuclear-powered carrier outside the US Navy.",
        "category": "military"
    },
    "fujian_carrier": {
        "name": "Type 003 Fujian-class Carrier",
        "description": "Chinese conventional carrier with three electromagnetic catapult tracks. The PLAN's most powerful vessel.",
        "category": "military"
    },
    "ins_vikrant_carrier": {
        "name": "INS Vikrant-class Carrier",
        "description": "Indian domestically-designed and built aircraft carrier. India's largest-ever warship.",
        "category": "military"
    },

    # ── NAVAL VESSELS — Nuclear Submarines ───────────────────────────────────
    "virginia_class_sub": {
        "name": "Virginia-class Submarine",
        "description": "US nuclear-powered fast attack submarine. Highly capable hunter-killer with Block V expanded payload.",
        "category": "military"
    },
    "astute_class_sub": {
        "name": "Astute-class Submarine",
        "description": "British nuclear-powered attack submarine. The most capable and stealthiest in Royal Navy history.",
        "category": "military"
    },
    "barracuda_class_sub": {
        "name": "Barracuda-class Submarine",
        "description": "French nuclear-powered attack submarine. Successor to the Rubis class with reduced acoustic signature.",
        "category": "military"
    },
    "yasen_class_sub": {
        "name": "Yasen-class Submarine",
        "description": "Russian nuclear-powered multirole attack submarine. Equipped with Kalibr cruise missiles and Onyx anti-ship missiles.",
        "category": "military"
    },
    "type093_sub": {
        "name": "Type 093 Submarine",
        "description": "Chinese nuclear-powered attack submarine. Shang-class PLAAF hunter-killer with improved quieting.",
        "category": "military"
    },
    "arihant_class_sub": {
        "name": "Arihant-class Submarine",
        "description": "Indian nuclear-powered ballistic missile submarine. India's strategic SSBN deterrent platform.",
        "category": "military"
    },

    # ── NAVAL VESSELS — Destroyers, Frigates & Corvettes ─────────────────────
    "arleigh_burke_destroyer": {
        "name": "Arleigh Burke-class Destroyer",
        "description": "US guided-missile destroyer. Backbone of the US surface fleet with Aegis combat system.",
        "category": "military"
    },
    "type045_destroyer": {
        "name": "Type 45 Destroyer",
        "description": "British air-defence destroyer equipped with the Sea Viper missile system. The Royal Navy's premier surface combatant.",
        "category": "military"
    },
    "type055_destroyer": {
        "name": "Type 055 Destroyer",
        "description": "Chinese cruiser-sized guided-missile destroyer. The most powerful surface combatant in Asia.",
        "category": "military"
    },
    "atago_class_destroyer": {
        "name": "Atago-class Destroyer",
        "description": "Japanese Aegis-equipped guided-missile destroyer. The JMSDF's premiere anti-ballistic missile platform.",
        "category": "military"
    },
    "kdx3_destroyer": {
        "name": "KDX-III Destroyer",
        "description": "South Korean Aegis destroyer with ballistic missile defense capability. Batch II variant adds SM-3 interceptors.",
        "category": "military"
    },
    "visakhapatnam_destroyer": {
        "name": "Visakhapatnam-class Destroyer",
        "description": "Indian stealth guided-missile destroyer. Fully domestically designed and built by Mazagon Dock.",
        "category": "military"
    },
    "gorshkov_frigate": {
        "name": "Admiral Gorshkov-class Frigate",
        "description": "Russian multirole guided-missile frigate. Equipped with hypersonic Zircon and Kalibr cruise missiles.",
        "category": "military"
    },
    "milgem_frigate": {
        "name": "MILGEM-class Frigate",
        "description": "Turkish domestically built corvette/frigate. Exported to Pakistan and Ukraine — a key Turkish defense success story.",
        "category": "military"
    },
    "al_riyadh_frigate": {
        "name": "Al Riyadh-class Frigate",
        "description": "Saudi La Fayette-class guided-missile frigate. Operates three vessels as key Saudi Navy surface combatants.",
        "category": "military"
    },
    "baynunah_corvette": {
        "name": "Baynunah-class Corvette",
        "description": "UAE fast attack missile corvette. Stealthy hull design with C-802 anti-ship missiles and Exocet capability.",
        "category": "military"
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# 3. NEW PRODUCTION LINES for district businesses
# ─────────────────────────────────────────────────────────────────────────────

# ── weapons_factory ──────────────────────────────────────────────────────────
# Remove: rifle (generic)  |  Add: 18 named rifle variants
REMOVE_FROM_WEAPONS_FACTORY = {"rifle"}

WEAPONS_FACTORY_NEW_LINES = [
    # USA
    {"inputs": [{"item": "rifle_barrel", "quantity": 100}, {"item": "rifle_receiver", "quantity": 100},
                {"item": "polymer_compound", "quantity": 30}, {"item": "steel", "quantity": 20},
                {"item": "energy", "quantity": 25000}, {"item": "paper", "quantity": 20}],
     "output_item": "m4_carbine", "output_qty": 100},
    {"inputs": [{"item": "rifle_barrel", "quantity": 80}, {"item": "rifle_receiver", "quantity": 80},
                {"item": "steel", "quantity": 60}, {"item": "polymer_compound", "quantity": 20},
                {"item": "energy", "quantity": 30000}, {"item": "paper", "quantity": 25}],
     "output_item": "m249_saw", "output_qty": 80},
    # Russia
    {"inputs": [{"item": "rifle_barrel", "quantity": 100}, {"item": "rifle_receiver", "quantity": 100},
                {"item": "steel", "quantity": 30}, {"item": "polymer_compound", "quantity": 20},
                {"item": "energy", "quantity": 22000}, {"item": "paper", "quantity": 18}],
     "output_item": "ak_47", "output_qty": 100},
    {"inputs": [{"item": "rifle_barrel", "quantity": 100}, {"item": "rifle_receiver", "quantity": 100},
                {"item": "polymer_compound", "quantity": 30}, {"item": "steel", "quantity": 20},
                {"item": "energy", "quantity": 24000}, {"item": "paper", "quantity": 20}],
     "output_item": "ak_74m", "output_qty": 100},
    # Germany (EUR)
    {"inputs": [{"item": "rifle_barrel", "quantity": 100}, {"item": "rifle_receiver", "quantity": 100},
                {"item": "polymer_compound", "quantity": 40}, {"item": "precision_spring", "quantity": 50},
                {"item": "energy", "quantity": 28000}, {"item": "paper", "quantity": 22}],
     "output_item": "hk416", "output_qty": 100},
    {"inputs": [{"item": "rifle_barrel", "quantity": 100}, {"item": "rifle_receiver", "quantity": 100},
                {"item": "polymer_compound", "quantity": 50}, {"item": "steel", "quantity": 15},
                {"item": "energy", "quantity": 26000}, {"item": "paper", "quantity": 20}],
     "output_item": "hk_g36", "output_qty": 100},
    # UK (GBP)
    {"inputs": [{"item": "rifle_barrel", "quantity": 100}, {"item": "rifle_receiver", "quantity": 100},
                {"item": "polymer_compound", "quantity": 40}, {"item": "steel", "quantity": 18},
                {"item": "energy", "quantity": 26000}, {"item": "paper", "quantity": 20}],
     "output_item": "l85a2", "output_qty": 100},
    # France (EUR)
    {"inputs": [{"item": "rifle_barrel", "quantity": 100}, {"item": "rifle_receiver", "quantity": 100},
                {"item": "polymer_compound", "quantity": 40}, {"item": "steel", "quantity": 15},
                {"item": "energy", "quantity": 25000}, {"item": "paper", "quantity": 20}],
     "output_item": "famas_f1", "output_qty": 100},
    # China (CNY)
    {"inputs": [{"item": "rifle_barrel", "quantity": 100}, {"item": "rifle_receiver", "quantity": 100},
                {"item": "polymer_compound", "quantity": 35}, {"item": "steel", "quantity": 20},
                {"item": "energy", "quantity": 22000}, {"item": "paper", "quantity": 18}],
     "output_item": "qbz_95", "output_qty": 100},
    # India (INR)
    {"inputs": [{"item": "rifle_barrel", "quantity": 100}, {"item": "rifle_receiver", "quantity": 100},
                {"item": "steel", "quantity": 25}, {"item": "polymer_compound", "quantity": 25},
                {"item": "energy", "quantity": 22000}, {"item": "paper", "quantity": 18}],
     "output_item": "insas_rifle", "output_qty": 100},
    # South Korea (KRW)
    {"inputs": [{"item": "rifle_barrel", "quantity": 100}, {"item": "rifle_receiver", "quantity": 100},
                {"item": "polymer_compound", "quantity": 35}, {"item": "steel", "quantity": 20},
                {"item": "energy", "quantity": 25000}, {"item": "paper", "quantity": 20}],
     "output_item": "k2_rifle", "output_qty": 100},
    # Turkey (TRY)
    {"inputs": [{"item": "rifle_barrel", "quantity": 100}, {"item": "rifle_receiver", "quantity": 100},
                {"item": "polymer_compound", "quantity": 30}, {"item": "steel", "quantity": 20},
                {"item": "energy", "quantity": 23000}, {"item": "paper", "quantity": 18}],
     "output_item": "mpt_76", "output_qty": 100},
    # South Africa (ZAR)
    {"inputs": [{"item": "rifle_barrel", "quantity": 100}, {"item": "rifle_receiver", "quantity": 100},
                {"item": "steel", "quantity": 30}, {"item": "polymer_compound", "quantity": 20},
                {"item": "energy", "quantity": 21000}, {"item": "paper", "quantity": 16}],
     "output_item": "vektor_r4", "output_qty": 100},
    # Japan (JPY)
    {"inputs": [{"item": "rifle_barrel", "quantity": 100}, {"item": "rifle_receiver", "quantity": 100},
                {"item": "polymer_compound", "quantity": 35}, {"item": "precision_spring", "quantity": 40},
                {"item": "energy", "quantity": 27000}, {"item": "paper", "quantity": 22}],
     "output_item": "howa_type89", "output_qty": 100},
    # Switzerland (CHF)
    {"inputs": [{"item": "rifle_barrel", "quantity": 100}, {"item": "rifle_receiver", "quantity": 100},
                {"item": "precision_spring", "quantity": 60}, {"item": "polymer_compound", "quantity": 30},
                {"item": "energy", "quantity": 30000}, {"item": "paper", "quantity": 24}],
     "output_item": "sig_sg550", "output_qty": 100},
    # Mexico (MXP)
    {"inputs": [{"item": "rifle_barrel", "quantity": 100}, {"item": "rifle_receiver", "quantity": 100},
                {"item": "polymer_compound", "quantity": 35}, {"item": "steel", "quantity": 20},
                {"item": "energy", "quantity": 21000}, {"item": "paper", "quantity": 16}],
     "output_item": "fx05_xiuhcoatl", "output_qty": 100},
    # Brazil (BRL)
    {"inputs": [{"item": "rifle_barrel", "quantity": 100}, {"item": "rifle_receiver", "quantity": 100},
                {"item": "steel", "quantity": 30}, {"item": "polymer_compound", "quantity": 20},
                {"item": "energy", "quantity": 22000}, {"item": "paper", "quantity": 18}],
     "output_item": "imbel_md97", "output_qty": 100},
    # UAE (AED)
    {"inputs": [{"item": "rifle_barrel", "quantity": 100}, {"item": "rifle_receiver", "quantity": 100},
                {"item": "polymer_compound", "quantity": 40}, {"item": "precision_spring", "quantity": 30},
                {"item": "energy", "quantity": 25000}, {"item": "paper", "quantity": 20}],
     "output_item": "caracal_car816", "output_qty": 100},
]

# ── military_aircraft_plant ──────────────────────────────────────────────────
# Remove: fighter_jet, military_helicopter  |  Add: 14 jets + 8 helicopters
REMOVE_FROM_AIRCRAFT_PLANT = {"fighter_jet", "military_helicopter"}

AIRCRAFT_PLANT_NEW_LINES = [
    # ── STEALTH JETS (x1 output — very high cost) ──
    # USA: F-22 Raptor
    {"inputs": [{"item": "jet_airframe", "quantity": 1}, {"item": "turbojet_engine", "quantity": 2},
                {"item": "avionics_suite", "quantity": 1}, {"item": "fire_control_system", "quantity": 1},
                {"item": "ejection_seat", "quantity": 1}, {"item": "radar_system", "quantity": 1},
                {"item": "missile", "quantity": 6}, {"item": "titanium_alloy", "quantity": 300},
                {"item": "carbon_fiber", "quantity": 200}, {"item": "energy", "quantity": 2500000},
                {"item": "paper", "quantity": 1000}],
     "output_item": "f22_raptor", "output_qty": 1},
    # USA: F-35 Lightning II
    {"inputs": [{"item": "jet_airframe", "quantity": 1}, {"item": "turbojet_engine", "quantity": 1},
                {"item": "avionics_suite", "quantity": 1}, {"item": "fire_control_system", "quantity": 1},
                {"item": "ejection_seat", "quantity": 1}, {"item": "radar_system", "quantity": 1},
                {"item": "missile", "quantity": 6}, {"item": "titanium_alloy", "quantity": 250},
                {"item": "carbon_fiber", "quantity": 180}, {"item": "energy", "quantity": 2200000},
                {"item": "paper", "quantity": 900}],
     "output_item": "f35_lightning", "output_qty": 1},
    # Russia: Su-57 Felon
    {"inputs": [{"item": "jet_airframe", "quantity": 1}, {"item": "turbojet_engine", "quantity": 2},
                {"item": "avionics_suite", "quantity": 1}, {"item": "fire_control_system", "quantity": 1},
                {"item": "ejection_seat", "quantity": 1}, {"item": "radar_system", "quantity": 1},
                {"item": "missile", "quantity": 6}, {"item": "titanium_alloy", "quantity": 280},
                {"item": "carbon_fiber", "quantity": 200}, {"item": "energy", "quantity": 2300000},
                {"item": "paper", "quantity": 950}],
     "output_item": "su57_felon", "output_qty": 1},
    # China: J-20 Chengdu
    {"inputs": [{"item": "jet_airframe", "quantity": 1}, {"item": "turbojet_engine", "quantity": 2},
                {"item": "avionics_suite", "quantity": 1}, {"item": "fire_control_system", "quantity": 1},
                {"item": "ejection_seat", "quantity": 1}, {"item": "radar_system", "quantity": 1},
                {"item": "missile", "quantity": 6}, {"item": "titanium_alloy", "quantity": 260},
                {"item": "carbon_fiber", "quantity": 180}, {"item": "energy", "quantity": 2100000},
                {"item": "paper", "quantity": 900}],
     "output_item": "j20_chengdu", "output_qty": 1},
    # Turkey: TAI TF-X Kaan
    {"inputs": [{"item": "jet_airframe", "quantity": 1}, {"item": "turbojet_engine", "quantity": 2},
                {"item": "avionics_suite", "quantity": 1}, {"item": "fire_control_system", "quantity": 1},
                {"item": "ejection_seat", "quantity": 1}, {"item": "radar_system", "quantity": 1},
                {"item": "missile", "quantity": 4}, {"item": "titanium_alloy", "quantity": 220},
                {"item": "carbon_fiber", "quantity": 160}, {"item": "energy", "quantity": 1900000},
                {"item": "paper", "quantity": 800}],
     "output_item": "tai_tfx", "output_qty": 1},

    # ── ADVANCED JETS (x2 output — high cost) ──
    # USA: F-16 Fighting Falcon
    {"inputs": [{"item": "jet_airframe", "quantity": 1}, {"item": "turbojet_engine", "quantity": 1},
                {"item": "avionics_suite", "quantity": 1}, {"item": "fire_control_system", "quantity": 1},
                {"item": "ejection_seat", "quantity": 1}, {"item": "radar_system", "quantity": 1},
                {"item": "missile", "quantity": 8}, {"item": "energy", "quantity": 1400000},
                {"item": "paper", "quantity": 600}],
     "output_item": "f16_falcon", "output_qty": 2},
    # USA: F-15 Eagle
    {"inputs": [{"item": "jet_airframe", "quantity": 1}, {"item": "turbojet_engine", "quantity": 2},
                {"item": "avionics_suite", "quantity": 1}, {"item": "fire_control_system", "quantity": 1},
                {"item": "ejection_seat", "quantity": 1}, {"item": "radar_system", "quantity": 1},
                {"item": "missile", "quantity": 8}, {"item": "energy", "quantity": 1500000},
                {"item": "paper", "quantity": 650}],
     "output_item": "f15_eagle", "output_qty": 2},
    # Russia: Su-35 Flanker-E
    {"inputs": [{"item": "jet_airframe", "quantity": 1}, {"item": "turbojet_engine", "quantity": 2},
                {"item": "avionics_suite", "quantity": 1}, {"item": "fire_control_system", "quantity": 1},
                {"item": "ejection_seat", "quantity": 1}, {"item": "radar_system", "quantity": 1},
                {"item": "missile", "quantity": 8}, {"item": "energy", "quantity": 1500000},
                {"item": "paper", "quantity": 650}],
     "output_item": "su35_flanker", "output_qty": 2},
    # Russia: MiG-29 Fulcrum
    {"inputs": [{"item": "jet_airframe", "quantity": 1}, {"item": "turbojet_engine", "quantity": 2},
                {"item": "avionics_suite", "quantity": 1}, {"item": "fire_control_system", "quantity": 1},
                {"item": "ejection_seat", "quantity": 1}, {"item": "radar_system", "quantity": 1},
                {"item": "missile", "quantity": 6}, {"item": "energy", "quantity": 1200000},
                {"item": "paper", "quantity": 550}],
     "output_item": "mig29_fulcrum", "output_qty": 2},
    # France (EUR): Rafale
    {"inputs": [{"item": "jet_airframe", "quantity": 1}, {"item": "turbojet_engine", "quantity": 2},
                {"item": "avionics_suite", "quantity": 1}, {"item": "fire_control_system", "quantity": 1},
                {"item": "ejection_seat", "quantity": 1}, {"item": "radar_system", "quantity": 1},
                {"item": "missile", "quantity": 6}, {"item": "titanium_alloy", "quantity": 100},
                {"item": "energy", "quantity": 1600000}, {"item": "paper", "quantity": 700}],
     "output_item": "rafale", "output_qty": 2},
    # UK/EUR: Eurofighter Typhoon
    {"inputs": [{"item": "jet_airframe", "quantity": 1}, {"item": "turbojet_engine", "quantity": 2},
                {"item": "avionics_suite", "quantity": 1}, {"item": "fire_control_system", "quantity": 1},
                {"item": "ejection_seat", "quantity": 1}, {"item": "radar_system", "quantity": 1},
                {"item": "missile", "quantity": 6}, {"item": "titanium_alloy", "quantity": 80},
                {"item": "energy", "quantity": 1600000}, {"item": "paper", "quantity": 700}],
     "output_item": "eurofighter_typhoon", "output_qty": 2},
    # China: J-16 Strike Flanker
    {"inputs": [{"item": "jet_airframe", "quantity": 1}, {"item": "turbojet_engine", "quantity": 2},
                {"item": "avionics_suite", "quantity": 1}, {"item": "fire_control_system", "quantity": 1},
                {"item": "ejection_seat", "quantity": 1}, {"item": "radar_system", "quantity": 1},
                {"item": "missile", "quantity": 8}, {"item": "energy", "quantity": 1400000},
                {"item": "paper", "quantity": 600}],
     "output_item": "j16_flanker", "output_qty": 2},
    # India: HAL Tejas
    {"inputs": [{"item": "jet_airframe", "quantity": 1}, {"item": "turbojet_engine", "quantity": 1},
                {"item": "avionics_suite", "quantity": 1}, {"item": "fire_control_system", "quantity": 1},
                {"item": "ejection_seat", "quantity": 1}, {"item": "radar_system", "quantity": 1},
                {"item": "missile", "quantity": 4}, {"item": "energy", "quantity": 1100000},
                {"item": "paper", "quantity": 500}],
     "output_item": "hal_tejas", "output_qty": 2},
    # South Korea: KF-21 Boramae
    {"inputs": [{"item": "jet_airframe", "quantity": 1}, {"item": "turbojet_engine", "quantity": 2},
                {"item": "avionics_suite", "quantity": 1}, {"item": "fire_control_system", "quantity": 1},
                {"item": "ejection_seat", "quantity": 1}, {"item": "radar_system", "quantity": 1},
                {"item": "missile", "quantity": 6}, {"item": "titanium_alloy", "quantity": 80},
                {"item": "energy", "quantity": 1500000}, {"item": "paper", "quantity": 650}],
     "output_item": "kf21_boramae", "output_qty": 2},

    # ── ATTACK HELICOPTERS (x3 output) ──
    # USA: AH-64E Apache
    {"inputs": [{"item": "helicopter_rotor", "quantity": 1}, {"item": "turbofan_engine", "quantity": 2},
                {"item": "avionics_suite", "quantity": 1}, {"item": "fire_control_system", "quantity": 1},
                {"item": "missile", "quantity": 8}, {"item": "titanium_alloy", "quantity": 80},
                {"item": "energy", "quantity": 800000}, {"item": "paper", "quantity": 400}],
     "output_item": "ah64_apache", "output_qty": 3},
    # Russia: Ka-52 Alligator
    {"inputs": [{"item": "helicopter_rotor", "quantity": 2}, {"item": "turbofan_engine", "quantity": 2},
                {"item": "avionics_suite", "quantity": 1}, {"item": "fire_control_system", "quantity": 1},
                {"item": "missile", "quantity": 6}, {"item": "titanium_alloy", "quantity": 70},
                {"item": "energy", "quantity": 750000}, {"item": "paper", "quantity": 380}],
     "output_item": "ka52_alligator", "output_qty": 3},
    # China: Z-10 Thunderbolt
    {"inputs": [{"item": "helicopter_rotor", "quantity": 1}, {"item": "turbofan_engine", "quantity": 2},
                {"item": "avionics_suite", "quantity": 1}, {"item": "fire_control_system", "quantity": 1},
                {"item": "missile", "quantity": 6}, {"item": "titanium_alloy", "quantity": 60},
                {"item": "energy", "quantity": 700000}, {"item": "paper", "quantity": 360}],
     "output_item": "z10_thunderbolt", "output_qty": 3},
    # Turkey: TAI T129 ATAK
    {"inputs": [{"item": "helicopter_rotor", "quantity": 1}, {"item": "turbofan_engine", "quantity": 2},
                {"item": "avionics_suite", "quantity": 1}, {"item": "fire_control_system", "quantity": 1},
                {"item": "missile", "quantity": 4}, {"item": "energy", "quantity": 650000},
                {"item": "paper", "quantity": 340}],
     "output_item": "t129_atak", "output_qty": 3},

    # ── UTILITY / MULTIPURPOSE HELICOPTERS (x5 output) ──
    # USA: UH-60 Black Hawk
    {"inputs": [{"item": "helicopter_rotor", "quantity": 1}, {"item": "turbofan_engine", "quantity": 2},
                {"item": "avionics_suite", "quantity": 1}, {"item": "energy", "quantity": 500000},
                {"item": "paper", "quantity": 300}],
     "output_item": "uh60_blackhawk", "output_qty": 5},
    # Russia: Mi-24 Hind
    {"inputs": [{"item": "helicopter_rotor", "quantity": 1}, {"item": "turbofan_engine", "quantity": 2},
                {"item": "avionics_suite", "quantity": 1}, {"item": "fire_control_system", "quantity": 1},
                {"item": "missile", "quantity": 4}, {"item": "energy", "quantity": 600000},
                {"item": "paper", "quantity": 320}],
     "output_item": "mi24_hind", "output_qty": 5},
    # France (EUR): Airbus H225M Caracal
    {"inputs": [{"item": "helicopter_rotor", "quantity": 1}, {"item": "turbofan_engine", "quantity": 2},
                {"item": "avionics_suite", "quantity": 1}, {"item": "energy", "quantity": 550000},
                {"item": "paper", "quantity": 300}],
     "output_item": "airbus_h225m", "output_qty": 5},
    # India: HAL Dhruv
    {"inputs": [{"item": "helicopter_rotor", "quantity": 1}, {"item": "turbofan_engine", "quantity": 1},
                {"item": "avionics_suite", "quantity": 1}, {"item": "energy", "quantity": 400000},
                {"item": "paper", "quantity": 250}],
     "output_item": "hal_dhruv", "output_qty": 5},
]

# ── military_vehicle_plant ───────────────────────────────────────────────────
# Remove: tank (generic)  |  Add: 12 named MBT variants
REMOVE_FROM_VEHICLE_PLANT = {"tank"}

VEHICLE_PLANT_NEW_LINES = [
    # ── TOP-TIER MBTs (x2 output) ──
    # USA: M1A2 SEPv3 Abrams
    {"inputs": [{"item": "tank_hull", "quantity": 1}, {"item": "tank_turret", "quantity": 1},
                {"item": "tank_cannon", "quantity": 1}, {"item": "diesel_engine", "quantity": 2},
                {"item": "fire_control_system", "quantity": 1}, {"item": "composite_armor_panel", "quantity": 30},
                {"item": "explosive_reactive_armor", "quantity": 30}, {"item": "titanium_alloy", "quantity": 80},
                {"item": "copper_wire", "quantity": 300}, {"item": "energy", "quantity": 600000},
                {"item": "paper", "quantity": 300}],
     "output_item": "m1a2_abrams", "output_qty": 2},
    # Germany (EUR): Leopard 2A7
    {"inputs": [{"item": "tank_hull", "quantity": 1}, {"item": "tank_turret", "quantity": 1},
                {"item": "tank_cannon", "quantity": 1}, {"item": "diesel_engine", "quantity": 2},
                {"item": "fire_control_system", "quantity": 1}, {"item": "composite_armor_panel", "quantity": 28},
                {"item": "titanium_alloy", "quantity": 60}, {"item": "copper_wire", "quantity": 280},
                {"item": "energy", "quantity": 580000}, {"item": "paper", "quantity": 280}],
     "output_item": "leopard_2a7", "output_qty": 2},
    # UK (GBP): Challenger 3
    {"inputs": [{"item": "tank_hull", "quantity": 1}, {"item": "tank_turret", "quantity": 1},
                {"item": "tank_cannon", "quantity": 1}, {"item": "diesel_engine", "quantity": 2},
                {"item": "fire_control_system", "quantity": 1}, {"item": "composite_armor_panel", "quantity": 30},
                {"item": "titanium_alloy", "quantity": 60}, {"item": "copper_wire", "quantity": 280},
                {"item": "energy", "quantity": 580000}, {"item": "paper", "quantity": 280}],
     "output_item": "challenger_3", "output_qty": 2},
    # Russia: T-14 Armata
    {"inputs": [{"item": "tank_hull", "quantity": 1}, {"item": "tank_turret", "quantity": 1},
                {"item": "tank_cannon", "quantity": 1}, {"item": "diesel_engine", "quantity": 2},
                {"item": "fire_control_system", "quantity": 1}, {"item": "composite_armor_panel", "quantity": 25},
                {"item": "explosive_reactive_armor", "quantity": 40}, {"item": "titanium_alloy", "quantity": 60},
                {"item": "copper_wire", "quantity": 300}, {"item": "energy", "quantity": 600000},
                {"item": "paper", "quantity": 300}],
     "output_item": "t14_armata", "output_qty": 2},
    # South Korea: K2 Black Panther
    {"inputs": [{"item": "tank_hull", "quantity": 1}, {"item": "tank_turret", "quantity": 1},
                {"item": "tank_cannon", "quantity": 1}, {"item": "diesel_engine", "quantity": 2},
                {"item": "fire_control_system", "quantity": 1}, {"item": "composite_armor_panel", "quantity": 25},
                {"item": "explosive_reactive_armor", "quantity": 20}, {"item": "titanium_alloy", "quantity": 50},
                {"item": "copper_wire", "quantity": 260}, {"item": "energy", "quantity": 560000},
                {"item": "paper", "quantity": 270}],
     "output_item": "k2_black_panther", "output_qty": 2},

    # ── STANDARD MBTs (x3 output) ──
    # Russia: T-90M Proryv
    {"inputs": [{"item": "tank_hull", "quantity": 1}, {"item": "tank_turret", "quantity": 1},
                {"item": "tank_cannon", "quantity": 1}, {"item": "diesel_engine", "quantity": 2},
                {"item": "fire_control_system", "quantity": 1}, {"item": "composite_armor_panel", "quantity": 20},
                {"item": "explosive_reactive_armor", "quantity": 30}, {"item": "copper_wire", "quantity": 250},
                {"item": "energy", "quantity": 500000}, {"item": "paper", "quantity": 250}],
     "output_item": "t90m_proryv", "output_qty": 3},
    # France (EUR): AMX-56 Leclerc
    {"inputs": [{"item": "tank_hull", "quantity": 1}, {"item": "tank_turret", "quantity": 1},
                {"item": "tank_cannon", "quantity": 1}, {"item": "diesel_engine", "quantity": 2},
                {"item": "fire_control_system", "quantity": 1}, {"item": "composite_armor_panel", "quantity": 22},
                {"item": "titanium_alloy", "quantity": 40}, {"item": "copper_wire", "quantity": 250},
                {"item": "energy", "quantity": 520000}, {"item": "paper", "quantity": 260}],
     "output_item": "amx_leclerc", "output_qty": 3},
    # China: Type 99A
    {"inputs": [{"item": "tank_hull", "quantity": 1}, {"item": "tank_turret", "quantity": 1},
                {"item": "tank_cannon", "quantity": 1}, {"item": "diesel_engine", "quantity": 2},
                {"item": "fire_control_system", "quantity": 1}, {"item": "composite_armor_panel", "quantity": 20},
                {"item": "explosive_reactive_armor", "quantity": 25}, {"item": "copper_wire", "quantity": 240},
                {"item": "energy", "quantity": 500000}, {"item": "paper", "quantity": 250}],
     "output_item": "type_99a", "output_qty": 3},
    # India: Arjun Mk.2
    {"inputs": [{"item": "tank_hull", "quantity": 1}, {"item": "tank_turret", "quantity": 1},
                {"item": "tank_cannon", "quantity": 1}, {"item": "diesel_engine", "quantity": 2},
                {"item": "fire_control_system", "quantity": 1}, {"item": "composite_armor_panel", "quantity": 20},
                {"item": "explosive_reactive_armor", "quantity": 20}, {"item": "copper_wire", "quantity": 240},
                {"item": "energy", "quantity": 490000}, {"item": "paper", "quantity": 245}],
     "output_item": "arjun_mk2", "output_qty": 3},
    # Turkey: Altay MBT
    {"inputs": [{"item": "tank_hull", "quantity": 1}, {"item": "tank_turret", "quantity": 1},
                {"item": "tank_cannon", "quantity": 1}, {"item": "diesel_engine", "quantity": 2},
                {"item": "fire_control_system", "quantity": 1}, {"item": "composite_armor_panel", "quantity": 18},
                {"item": "copper_wire", "quantity": 230}, {"item": "energy", "quantity": 480000},
                {"item": "paper", "quantity": 240}],
     "output_item": "altay_tank", "output_qty": 3},
    # Japan: Type 10
    {"inputs": [{"item": "tank_hull", "quantity": 1}, {"item": "tank_turret", "quantity": 1},
                {"item": "tank_cannon", "quantity": 1}, {"item": "diesel_engine", "quantity": 1},
                {"item": "fire_control_system", "quantity": 1}, {"item": "composite_armor_panel", "quantity": 18},
                {"item": "titanium_alloy", "quantity": 40}, {"item": "copper_wire", "quantity": 230},
                {"item": "energy", "quantity": 480000}, {"item": "paper", "quantity": 240}],
     "output_item": "type10_tank", "output_qty": 3},
    # Brazil: EE-T1 Osório
    {"inputs": [{"item": "tank_hull", "quantity": 1}, {"item": "tank_turret", "quantity": 1},
                {"item": "tank_cannon", "quantity": 1}, {"item": "diesel_engine", "quantity": 2},
                {"item": "fire_control_system", "quantity": 1}, {"item": "composite_armor_panel", "quantity": 16},
                {"item": "copper_wire", "quantity": 200}, {"item": "energy", "quantity": 440000},
                {"item": "paper", "quantity": 220}],
     "output_item": "ee_t1_osorio", "output_qty": 3},
]

# ── naval_shipyard ───────────────────────────────────────────────────────────
# Remove: naval_destroyer, submarine  |  Add: 5 carriers + 6 nuclear subs + 9 destroyers/frigates/corvettes
REMOVE_FROM_NAVAL_SHIPYARD = {"naval_destroyer", "submarine"}

NAVAL_SHIPYARD_NEW_LINES = [
    # ── AIRCRAFT CARRIERS (x1 output — most expensive) ──
    # USA: Gerald R. Ford-class (nuclear)
    {"inputs": [{"item": "destroyer_hull", "quantity": 4}, {"item": "turbofan_engine", "quantity": 12},
                {"item": "nuclear_reactor_core", "quantity": 2}, {"item": "naval_gun_system", "quantity": 6},
                {"item": "radar_system", "quantity": 6}, {"item": "sonar_system", "quantity": 3},
                {"item": "missile", "quantity": 40}, {"item": "marine_piping", "quantity": 400},
                {"item": "titanium_alloy", "quantity": 500}, {"item": "steel", "quantity": 2000},
                {"item": "energy", "quantity": 10000000}, {"item": "paper", "quantity": 3000}],
     "output_item": "ford_class_carrier", "output_qty": 1},
    # UK (GBP): Queen Elizabeth-class (conventional)
    {"inputs": [{"item": "destroyer_hull", "quantity": 3}, {"item": "turbofan_engine", "quantity": 8},
                {"item": "naval_gun_system", "quantity": 4}, {"item": "radar_system", "quantity": 4},
                {"item": "sonar_system", "quantity": 2}, {"item": "missile", "quantity": 30},
                {"item": "marine_piping", "quantity": 300}, {"item": "titanium_alloy", "quantity": 300},
                {"item": "steel", "quantity": 1500}, {"item": "energy", "quantity": 8000000},
                {"item": "paper", "quantity": 2500}],
     "output_item": "queen_elizabeth_carrier", "output_qty": 1},
    # France (EUR): Charles de Gaulle-class (nuclear)
    {"inputs": [{"item": "destroyer_hull", "quantity": 3}, {"item": "turbofan_engine", "quantity": 6},
                {"item": "nuclear_reactor_core", "quantity": 2}, {"item": "naval_gun_system", "quantity": 4},
                {"item": "radar_system", "quantity": 4}, {"item": "sonar_system", "quantity": 2},
                {"item": "missile", "quantity": 30}, {"item": "marine_piping", "quantity": 280},
                {"item": "titanium_alloy", "quantity": 280}, {"item": "steel", "quantity": 1400},
                {"item": "energy", "quantity": 8500000}, {"item": "paper", "quantity": 2500}],
     "output_item": "charles_degaulle_carrier", "output_qty": 1},
    # China (CNY): Type 003 Fujian-class
    {"inputs": [{"item": "destroyer_hull", "quantity": 3}, {"item": "turbofan_engine", "quantity": 8},
                {"item": "naval_gun_system", "quantity": 4}, {"item": "radar_system", "quantity": 4},
                {"item": "sonar_system", "quantity": 2}, {"item": "missile", "quantity": 30},
                {"item": "marine_piping", "quantity": 300}, {"item": "titanium_alloy", "quantity": 280},
                {"item": "steel", "quantity": 1500}, {"item": "energy", "quantity": 8000000},
                {"item": "paper", "quantity": 2500}],
     "output_item": "fujian_carrier", "output_qty": 1},
    # India (INR): INS Vikrant-class
    {"inputs": [{"item": "destroyer_hull", "quantity": 2}, {"item": "turbofan_engine", "quantity": 6},
                {"item": "naval_gun_system", "quantity": 3}, {"item": "radar_system", "quantity": 3},
                {"item": "sonar_system", "quantity": 1}, {"item": "missile", "quantity": 20},
                {"item": "marine_piping", "quantity": 200}, {"item": "titanium_alloy", "quantity": 200},
                {"item": "steel", "quantity": 1000}, {"item": "energy", "quantity": 6500000},
                {"item": "paper", "quantity": 2000}],
     "output_item": "ins_vikrant_carrier", "output_qty": 1},

    # ── NUCLEAR SUBMARINES (x1 output) ──
    # USA: Virginia-class
    {"inputs": [{"item": "submarine_hull", "quantity": 1}, {"item": "nuclear_reactor_core", "quantity": 2},
                {"item": "torpedo", "quantity": 24}, {"item": "sonar_system", "quantity": 4},
                {"item": "fire_control_system", "quantity": 3}, {"item": "missile", "quantity": 12},
                {"item": "titanium_alloy", "quantity": 200}, {"item": "marine_piping", "quantity": 100},
                {"item": "energy", "quantity": 7000000}, {"item": "paper", "quantity": 1400}],
     "output_item": "virginia_class_sub", "output_qty": 1},
    # UK (GBP): Astute-class
    {"inputs": [{"item": "submarine_hull", "quantity": 1}, {"item": "nuclear_reactor_core", "quantity": 1},
                {"item": "torpedo", "quantity": 38}, {"item": "sonar_system", "quantity": 3},
                {"item": "fire_control_system", "quantity": 2}, {"item": "missile", "quantity": 8},
                {"item": "titanium_alloy", "quantity": 180}, {"item": "marine_piping", "quantity": 80},
                {"item": "energy", "quantity": 6500000}, {"item": "paper", "quantity": 1300}],
     "output_item": "astute_class_sub", "output_qty": 1},
    # France (EUR): Barracuda-class
    {"inputs": [{"item": "submarine_hull", "quantity": 1}, {"item": "nuclear_reactor_core", "quantity": 1},
                {"item": "torpedo", "quantity": 20}, {"item": "sonar_system", "quantity": 3},
                {"item": "fire_control_system", "quantity": 2}, {"item": "missile", "quantity": 8},
                {"item": "titanium_alloy", "quantity": 170}, {"item": "marine_piping", "quantity": 75},
                {"item": "energy", "quantity": 6500000}, {"item": "paper", "quantity": 1300}],
     "output_item": "barracuda_class_sub", "output_qty": 1},
    # Russia (RUB): Yasen-class
    {"inputs": [{"item": "submarine_hull", "quantity": 1}, {"item": "nuclear_reactor_core", "quantity": 1},
                {"item": "torpedo", "quantity": 30}, {"item": "sonar_system", "quantity": 4},
                {"item": "fire_control_system", "quantity": 2}, {"item": "missile", "quantity": 16},
                {"item": "titanium_alloy", "quantity": 200}, {"item": "marine_piping", "quantity": 90},
                {"item": "energy", "quantity": 7000000}, {"item": "paper", "quantity": 1400}],
     "output_item": "yasen_class_sub", "output_qty": 1},
    # China (CNY): Type 093
    {"inputs": [{"item": "submarine_hull", "quantity": 1}, {"item": "nuclear_reactor_core", "quantity": 1},
                {"item": "torpedo", "quantity": 22}, {"item": "sonar_system", "quantity": 3},
                {"item": "fire_control_system", "quantity": 2}, {"item": "missile", "quantity": 8},
                {"item": "titanium_alloy", "quantity": 170}, {"item": "marine_piping", "quantity": 75},
                {"item": "energy", "quantity": 6000000}, {"item": "paper", "quantity": 1200}],
     "output_item": "type093_sub", "output_qty": 1},
    # India (INR): Arihant-class
    {"inputs": [{"item": "submarine_hull", "quantity": 1}, {"item": "nuclear_reactor_core", "quantity": 1},
                {"item": "torpedo", "quantity": 12}, {"item": "sonar_system", "quantity": 2},
                {"item": "fire_control_system", "quantity": 2}, {"item": "missile", "quantity": 8},
                {"item": "titanium_alloy", "quantity": 150}, {"item": "marine_piping", "quantity": 70},
                {"item": "energy", "quantity": 5500000}, {"item": "paper", "quantity": 1100}],
     "output_item": "arihant_class_sub", "output_qty": 1},

    # ── DESTROYERS (x1 output) ──
    # USA: Arleigh Burke-class
    {"inputs": [{"item": "destroyer_hull", "quantity": 1}, {"item": "turbofan_engine", "quantity": 4},
                {"item": "naval_gun_system", "quantity": 2}, {"item": "radar_system", "quantity": 2},
                {"item": "sonar_system", "quantity": 2}, {"item": "missile", "quantity": 12},
                {"item": "marine_piping", "quantity": 50}, {"item": "energy", "quantity": 4000000},
                {"item": "paper", "quantity": 900}],
     "output_item": "arleigh_burke_destroyer", "output_qty": 1},
    # UK (GBP): Type 45 Destroyer
    {"inputs": [{"item": "destroyer_hull", "quantity": 1}, {"item": "turbofan_engine", "quantity": 4},
                {"item": "naval_gun_system", "quantity": 2}, {"item": "radar_system", "quantity": 2},
                {"item": "sonar_system", "quantity": 1}, {"item": "missile", "quantity": 10},
                {"item": "marine_piping", "quantity": 45}, {"item": "energy", "quantity": 3800000},
                {"item": "paper", "quantity": 850}],
     "output_item": "type045_destroyer", "output_qty": 1},
    # China (CNY): Type 055
    {"inputs": [{"item": "destroyer_hull", "quantity": 1}, {"item": "turbofan_engine", "quantity": 4},
                {"item": "naval_gun_system", "quantity": 2}, {"item": "radar_system", "quantity": 3},
                {"item": "sonar_system", "quantity": 2}, {"item": "missile", "quantity": 14},
                {"item": "marine_piping", "quantity": 50}, {"item": "energy", "quantity": 4200000},
                {"item": "paper", "quantity": 950}],
     "output_item": "type055_destroyer", "output_qty": 1},
    # Japan (JPY): Atago-class
    {"inputs": [{"item": "destroyer_hull", "quantity": 1}, {"item": "turbofan_engine", "quantity": 4},
                {"item": "naval_gun_system", "quantity": 2}, {"item": "radar_system", "quantity": 2},
                {"item": "sonar_system", "quantity": 1}, {"item": "missile", "quantity": 10},
                {"item": "marine_piping", "quantity": 40}, {"item": "energy", "quantity": 3800000},
                {"item": "paper", "quantity": 850}],
     "output_item": "atago_class_destroyer", "output_qty": 1},
    # South Korea (KRW): KDX-III
    {"inputs": [{"item": "destroyer_hull", "quantity": 1}, {"item": "turbofan_engine", "quantity": 4},
                {"item": "naval_gun_system", "quantity": 2}, {"item": "radar_system", "quantity": 2},
                {"item": "sonar_system", "quantity": 1}, {"item": "missile", "quantity": 10},
                {"item": "marine_piping", "quantity": 40}, {"item": "energy", "quantity": 3700000},
                {"item": "paper", "quantity": 820}],
     "output_item": "kdx3_destroyer", "output_qty": 1},
    # India (INR): Visakhapatnam-class
    {"inputs": [{"item": "destroyer_hull", "quantity": 1}, {"item": "turbofan_engine", "quantity": 4},
                {"item": "naval_gun_system", "quantity": 2}, {"item": "radar_system", "quantity": 2},
                {"item": "sonar_system", "quantity": 1}, {"item": "missile", "quantity": 8},
                {"item": "marine_piping", "quantity": 38}, {"item": "energy", "quantity": 3500000},
                {"item": "paper", "quantity": 800}],
     "output_item": "visakhapatnam_destroyer", "output_qty": 1},

    # ── FRIGATES (x1 output) ──
    # Russia (RUB): Gorshkov-class
    {"inputs": [{"item": "destroyer_hull", "quantity": 1}, {"item": "turbofan_engine", "quantity": 3},
                {"item": "naval_gun_system", "quantity": 2}, {"item": "radar_system", "quantity": 2},
                {"item": "sonar_system", "quantity": 1}, {"item": "missile", "quantity": 10},
                {"item": "marine_piping", "quantity": 35}, {"item": "energy", "quantity": 3500000},
                {"item": "paper", "quantity": 750}],
     "output_item": "gorshkov_frigate", "output_qty": 1},
    # Turkey (TRY): MILGEM-class
    {"inputs": [{"item": "destroyer_hull", "quantity": 1}, {"item": "turbofan_engine", "quantity": 2},
                {"item": "naval_gun_system", "quantity": 1}, {"item": "radar_system", "quantity": 2},
                {"item": "sonar_system", "quantity": 1}, {"item": "missile", "quantity": 6},
                {"item": "marine_piping", "quantity": 25}, {"item": "energy", "quantity": 2500000},
                {"item": "paper", "quantity": 600}],
     "output_item": "milgem_frigate", "output_qty": 1},
    # Saudi Arabia (SAR): Al Riyadh-class
    {"inputs": [{"item": "destroyer_hull", "quantity": 1}, {"item": "turbofan_engine", "quantity": 2},
                {"item": "naval_gun_system", "quantity": 2}, {"item": "radar_system", "quantity": 2},
                {"item": "sonar_system", "quantity": 1}, {"item": "missile", "quantity": 6},
                {"item": "marine_piping", "quantity": 28}, {"item": "energy", "quantity": 2800000},
                {"item": "paper", "quantity": 650}],
     "output_item": "al_riyadh_frigate", "output_qty": 1},

    # ── CORVETTES (x1 output) ──
    # UAE (AED): Baynunah-class
    {"inputs": [{"item": "steel", "quantity": 300}, {"item": "turbofan_engine", "quantity": 2},
                {"item": "naval_gun_system", "quantity": 1}, {"item": "radar_system", "quantity": 1},
                {"item": "missile", "quantity": 4}, {"item": "marine_piping", "quantity": 20},
                {"item": "energy", "quantity": 2000000}, {"item": "paper", "quantity": 500}],
     "output_item": "baynunah_corvette", "output_qty": 1},
]

# ─────────────────────────────────────────────────────────────────────────────
# 4. APPLY CHANGES
# ─────────────────────────────────────────────────────────────────────────────

# 4a. Add new items to district_items
print(f"district_items before: {len(di)}")
for key, val in NEW_ITEMS.items():
    if key not in di:
        di[key] = val
        print(f"  + Added district item: {key}")
    else:
        print(f"  ! Skipped (already exists): {key}")
print(f"district_items after: {len(di)}")


def remove_lines(biz_dict, business_key, output_items_to_remove):
    """Remove production lines with output_item in the given set."""
    biz = biz_dict[business_key]
    before = len(biz["production_lines"])
    biz["production_lines"] = [
        pl for pl in biz["production_lines"]
        if pl.get("output_item") not in output_items_to_remove
    ]
    removed = before - len(biz["production_lines"])
    print(f"  Removed {removed} lines from {business_key} (output items: {output_items_to_remove})")


def add_lines(biz_dict, business_key, new_lines):
    """Append new production lines."""
    biz = biz_dict[business_key]
    biz["production_lines"].extend(new_lines)
    print(f"  Added {len(new_lines)} new lines to {business_key}")


print("\n--- Modifying weapons_factory ---")
remove_lines(db, "weapons_factory", REMOVE_FROM_WEAPONS_FACTORY)
add_lines(db, "weapons_factory", WEAPONS_FACTORY_NEW_LINES)

print("\n--- Modifying military_aircraft_plant ---")
remove_lines(db, "military_aircraft_plant", REMOVE_FROM_AIRCRAFT_PLANT)
add_lines(db, "military_aircraft_plant", AIRCRAFT_PLANT_NEW_LINES)

print("\n--- Modifying military_vehicle_plant ---")
remove_lines(db, "military_vehicle_plant", REMOVE_FROM_VEHICLE_PLANT)
add_lines(db, "military_vehicle_plant", VEHICLE_PLANT_NEW_LINES)

print("\n--- Modifying naval_shipyard ---")
remove_lines(db, "naval_shipyard", REMOVE_FROM_NAVAL_SHIPYARD)
add_lines(db, "naval_shipyard", NAVAL_SHIPYARD_NEW_LINES)

# 4b. Update military_base_district — replace finished weapons inputs with components
print("\n--- Updating military_base_district ---")
mbd = db["military_base_district"]
new_mbd_lines = []
for pl in mbd["production_lines"]:
    if pl["output_item"] == "defense_contract":
        # Replace: fighter_jet x2, tank x3, naval_destroyer x1, rifle x500, submarine x1, military_helicopter x1
        # With component inputs that are still produceable
        pl["inputs"] = [
            {"item": "ammunition_crate", "quantity": 100},   # replaces rifle x500
            {"item": "missile", "quantity": 50},
            {"item": "ammunition", "quantity": 10000},
            {"item": "radar_array", "quantity": 5},
            {"item": "paper", "quantity": 500},
            {"item": "energy", "quantity": 500000},
            {"item": "apc", "quantity": 5},
            {"item": "drone", "quantity": 10},
            {"item": "jet_airframe", "quantity": 2},          # replaces fighter_jet x2
            {"item": "tank_hull", "quantity": 3},             # replaces tank x3
            {"item": "destroyer_hull", "quantity": 1},        # replaces naval_destroyer x1
            {"item": "submarine_hull", "quantity": 1},        # replaces submarine x1
            {"item": "helicopter_rotor", "quantity": 2},      # replaces military_helicopter x1
        ]
        print("  Updated defense_contract inputs (generics → components)")
    elif pl["output_item"] == "military_training":
        # Replace rifle x100 with ammunition_crate x10
        pl["inputs"] = [i for i in pl["inputs"] if i["item"] != "rifle"]
        pl["inputs"].append({"item": "ammunition_crate", "quantity": 10})
        print("  Updated military_training inputs (rifle → ammunition_crate)")
    new_mbd_lines.append(pl)
mbd["production_lines"] = new_mbd_lines

# 4c. Update tactical_gear_factory — replace rifle with rifle components in sniper_kit
print("\n--- Updating tactical_gear_factory ---")
tgf = db["tactical_gear_factory"]
new_tgf_lines = []
for pl in tgf["production_lines"]:
    if pl["output_item"] == "sniper_kit":
        pl["inputs"] = [i for i in pl["inputs"] if i["item"] != "rifle"]
        # Add rifle barrel + rifle receiver as sniper kit components
        pl["inputs"] = [
            {"item": "rifle_barrel", "quantity": 20},
            {"item": "rifle_receiver", "quantity": 20},
            {"item": "targeting_optic", "quantity": 20},
            {"item": "precision_spring", "quantity": 30},
            {"item": "titanium_alloy", "quantity": 20},
            {"item": "energy", "quantity": 20000},
            {"item": "paper", "quantity": 20},
        ]
        print("  Updated sniper_kit inputs (rifle → rifle_barrel + rifle_receiver + components)")
    new_tgf_lines.append(pl)
tgf["production_lines"] = new_tgf_lines

# ─────────────────────────────────────────────────────────────────────────────
# 5. SAVE
# ─────────────────────────────────────────────────────────────────────────────
with open("district_items.json", "w") as f:
    json.dump(di, f, indent=2)
print("\n✓ Saved district_items.json")

with open("district_businesses.json", "w") as f:
    json.dump(db, f, indent=2)
print("✓ Saved district_businesses.json")

# ─────────────────────────────────────────────────────────────────────────────
# 6. VERIFY
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== Verification ===")
with open("district_items.json") as f:
    di2 = json.load(f)
with open("district_businesses.json") as f:
    db2 = json.load(f)

# Check new items present
for key in NEW_ITEMS:
    assert key in di2, f"MISSING item: {key}"
print(f"✓ All {len(NEW_ITEMS)} new items present in district_items")

# Check generics no longer produced (but still exist as items)
factories = {
    "weapons_factory": {"rifle"},
    "military_aircraft_plant": {"fighter_jet", "military_helicopter"},
    "military_vehicle_plant": {"tank"},
    "naval_shipyard": {"naval_destroyer", "submarine"},
}
for biz_key, removed_outputs in factories.items():
    produced = {pl["output_item"] for pl in db2[biz_key]["production_lines"]}
    for item in removed_outputs:
        if item in produced:
            print(f"  ✗ {biz_key} still produces {item}!")
        else:
            print(f"  ✓ {biz_key} no longer produces '{item}'")

# Check named variants produced
spot_checks = [
    ("weapons_factory", "m4_carbine"),
    ("weapons_factory", "ak_47"),
    ("weapons_factory", "sig_sg550"),
    ("military_aircraft_plant", "f22_raptor"),
    ("military_aircraft_plant", "su57_felon"),
    ("military_aircraft_plant", "ah64_apache"),
    ("military_vehicle_plant", "m1a2_abrams"),
    ("military_vehicle_plant", "leopard_2a7"),
    ("naval_shipyard", "ford_class_carrier"),
    ("naval_shipyard", "virginia_class_sub"),
    ("naval_shipyard", "arleigh_burke_destroyer"),
]
for biz_key, item in spot_checks:
    produced = {pl["output_item"] for pl in db2[biz_key]["production_lines"]}
    if item in produced:
        print(f"  ✓ {biz_key} produces {item}")
    else:
        print(f"  ✗ {biz_key} MISSING {item}")

# Check defense_contract no longer uses generic weapons
mbd_dc = next(pl for pl in db2["military_base_district"]["production_lines"] if pl["output_item"] == "defense_contract")
dc_inputs = {i["item"] for i in mbd_dc["inputs"]}
for old in ["fighter_jet", "tank", "naval_destroyer", "rifle", "submarine", "military_helicopter"]:
    if old in dc_inputs:
        print(f"  ✗ defense_contract still uses {old}!")
    else:
        print(f"  ✓ defense_contract no longer requires {old}")

print("\nAll done!")
