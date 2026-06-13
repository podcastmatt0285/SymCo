#!/usr/bin/env python3
"""
apply_weapons_realism.py
Transforms generic military items in Wadsworth SymCo to real-life named items.
Idempotent - safe to run multiple times.
"""

import json
import copy
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def load_json(filename):
    path = os.path.join(BASE_DIR, filename)
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(filename, data):
    path = os.path.join(BASE_DIR, filename)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  -> Saved {filename}")

# ============================================================
# DEFINITIONS
# ============================================================

NEW_ITEMS = {
    # Ammunition - single rounds
    "556_nato": {"name": "5.56×45mm NATO", "base_price": 0.85, "category": "military",
                 "description": "Standard assault rifle cartridge"},
    "762x39": {"name": "7.62×39mm", "base_price": 0.75, "category": "military",
               "description": "Soviet-pattern intermediate rifle cartridge"},
    "545x39": {"name": "5.45×39mm", "base_price": 0.70, "category": "military",
               "description": "Russian assault rifle cartridge"},
    "762_nato": {"name": "7.62×51mm NATO", "base_price": 1.10, "category": "military",
                 "description": "Battle rifle and machine gun cartridge"},
    "50_bmg": {"name": ".50 BMG", "base_price": 4.50, "category": "military",
               "description": "Heavy machine gun and anti-materiel rifle cartridge"},
    "9mm_para": {"name": "9mm Parabellum", "base_price": 0.55, "category": "military",
                 "description": "Standard pistol and SMG cartridge"},
    # Ammunition crates
    "556_nato_crate": {"name": "5.56 NATO Ammo Crate", "base_price": 950, "category": "military",
                       "description": "1000-round crate of 5.56×45mm NATO"},
    "762x39_crate": {"name": "7.62×39 Ammo Crate", "base_price": 850, "category": "military",
                     "description": "1000-round crate of 7.62×39mm"},
    "545x39_crate": {"name": "5.45×39 Ammo Crate", "base_price": 790, "category": "military",
                     "description": "1000-round crate of 5.45×39mm"},
    "762_nato_crate": {"name": "7.62 NATO Ammo Crate", "base_price": 1250, "category": "military",
                       "description": "1000-round crate of 7.62×51mm NATO"},
    "50_bmg_crate": {"name": ".50 BMG Ammo Crate", "base_price": 5200, "category": "military",
                     "description": "1000-round crate of .50 BMG"},
    "9mm_crate": {"name": "9mm Ammo Crate", "base_price": 620, "category": "military",
                  "description": "1000-round crate of 9mm Parabellum"},
    # Missile components
    "frag_warhead": {"name": "Fragmentation Warhead", "base_price": 8500, "category": "military",
                     "description": "Anti-personnel/materiel fragmentation warhead"},
    "shaped_charge_warhead": {"name": "Shaped Charge Warhead", "base_price": 14000, "category": "military",
                              "description": "Anti-armor shaped charge warhead"},
    "he_warhead": {"name": "HE Warhead", "base_price": 11000, "category": "military",
                   "description": "General-purpose high-explosive warhead"},
    "thermobaric_warhead": {"name": "Thermobaric Warhead", "base_price": 18000, "category": "military",
                            "description": "Thermobaric/fuel-air explosive warhead"},
    "radar_seeker": {"name": "Radar Seeker Head", "base_price": 32000, "category": "military",
                     "description": "Active radar homing seeker for missiles"},
    "ir_seeker": {"name": "IR Seeker Head", "base_price": 22000, "category": "military",
                  "description": "Infrared heat-seeking missile guidance head"},
    "laser_seeker": {"name": "Laser Seeker Head", "base_price": 28000, "category": "military",
                     "description": "Semi-active laser homing seeker"},
    "gps_ins_guidance": {"name": "GPS/INS Guidance Unit", "base_price": 45000, "category": "military",
                         "description": "GPS-aided inertial navigation guidance system"},
    "solid_rocket_motor": {"name": "Solid Rocket Motor", "base_price": 12000, "category": "military",
                           "description": "Solid-propellant rocket motor for missiles"},
    "turbojet_cruise_motor": {"name": "Turbojet Cruise Motor", "base_price": 55000, "category": "military",
                              "description": "Small turbojet engine for cruise missiles"},
    # Air-to-air missiles
    "aim120_amraam": {"name": "AIM-120 AMRAAM", "base_price": 1850000, "category": "military",
                      "description": "Active radar-guided beyond-visual-range air-to-air missile"},
    "aim9_sidewinder": {"name": "AIM-9 Sidewinder", "base_price": 590000, "category": "military",
                        "description": "Short-range infrared-guided air-to-air missile"},
    "r77_missile": {"name": "R-77 Adder", "base_price": 1200000, "category": "military",
                    "description": "Russian active radar-guided air-to-air missile"},
    # Air-to-ground / anti-tank
    "agm114_hellfire": {"name": "AGM-114 Hellfire", "base_price": 115000, "category": "military",
                        "description": "Laser/radar-guided air-to-surface anti-tank missile"},
    "agm65_maverick": {"name": "AGM-65 Maverick", "base_price": 280000, "category": "military",
                       "description": "Electro-optical/IR guided air-to-ground missile"},
    "fgm148_javelin": {"name": "FGM-148 Javelin", "base_price": 175000, "category": "military",
                       "description": "Man-portable fire-and-forget anti-tank missile"},
    # Cruise / land-attack
    "bgm109_tomahawk": {"name": "BGM-109 Tomahawk", "base_price": 2100000, "category": "military",
                        "description": "Long-range subsonic land-attack cruise missile"},
    "kalibr_missile": {"name": "Kalibr Cruise Missile", "base_price": 1350000, "category": "military",
                       "description": "Russian long-range sea/sub-launched cruise missile"},
    "brahmos_missile": {"name": "BrahMos Missile", "base_price": 2800000, "category": "military",
                        "description": "Supersonic cruise missile (India/Russia joint)"},
    # Anti-ship / SAM
    "agm84_harpoon": {"name": "AGM-84 Harpoon", "base_price": 1400000, "category": "military",
                      "description": "Active radar-guided anti-ship missile"},
    "exocet_missile": {"name": "Exocet Missile", "base_price": 1050000, "category": "military",
                       "description": "French sea-skimming anti-ship missile"},
    "sm2_missile": {"name": "SM-2 Standard Missile", "base_price": 2200000, "category": "military",
                    "description": "Long-range ship-based surface-to-air missile"},
    # Grenades
    "frag_grenade_body": {"name": "Frag Grenade Body", "base_price": 18, "category": "military",
                          "description": "Steel fragmentation grenade body shell"},
    "comp_b_filler": {"name": "Comp-B Filler", "base_price": 12, "category": "military",
                      "description": "Composition B explosive filler for grenades"},
    "m67_grenade": {"name": "M67 Grenade", "base_price": 65, "category": "military",
                    "description": "US spherical fragmentation hand grenade"},
    "rgo_grenade": {"name": "RGO Grenade", "base_price": 55, "category": "military",
                    "description": "Russian defensive fragmentation grenade"},
    "dm51_grenade": {"name": "DM51 Grenade", "base_price": 60, "category": "military",
                     "description": "German dual-purpose fragmentation grenade"},
    "arges_hg84": {"name": "Arges HG 84", "base_price": 70, "category": "military",
                   "description": "Swiss fragmentation grenade, NATO-standard"},
    "m18_smoke_grenade": {"name": "M18 Smoke Grenade", "base_price": 45, "category": "military",
                          "description": "US colored smoke signaling grenade"},
    "m15_wp_grenade": {"name": "M15 WP Grenade", "base_price": 85, "category": "military",
                       "description": "US white phosphorus incendiary/screening grenade"},
    "m112_c4": {"name": "M112 C4", "base_price": 180, "category": "military",
                "description": "US standard demolition charge (C4 explosive)"},
    "semtex_charge": {"name": "Semtex Charge", "base_price": 155, "category": "military",
                      "description": "Czech plastic explosive demolition charge"},
    # Artillery
    "m795_shell": {"name": "M795 Artillery Shell", "base_price": 2200, "category": "military",
                   "description": "US 155mm standard high-explosive artillery round"},
    "m982_excalibur": {"name": "M982 Excalibur", "base_price": 68000, "category": "military",
                       "description": "US GPS-guided extended-range 155mm precision shell"},
    # Torpedoes
    "mk48_torpedo": {"name": "Mk 48 Torpedo", "base_price": 3500000, "category": "military",
                     "description": "US heavyweight wire-guided submarine torpedo"},
    "type53_torpedo": {"name": "Type 53 Torpedo", "base_price": 1800000, "category": "military",
                       "description": "Russian standard heavyweight submarine torpedo"},
    # Drones
    "mq9_reaper": {"name": "MQ-9 Reaper", "base_price": 32000000, "category": "military",
                   "description": "US long-endurance armed MALE reconnaissance drone"},
    "bayraktar_tb2": {"name": "Bayraktar TB2", "base_price": 5000000, "category": "military",
                      "description": "Turkish combat drone, laser-guided munitions capable"},
    "wing_loong_2": {"name": "Wing Loong II", "base_price": 8000000, "category": "military",
                     "description": "Chinese MALE combat reconnaissance drone"},
    "switchblade_600": {"name": "Switchblade 600", "base_price": 95000, "category": "military",
                        "description": "US anti-armor loitering munition"},
    "lancet_3": {"name": "Lancet-3", "base_price": 35000, "category": "military",
                 "description": "Russian anti-armor loitering munition"},
    # Machine guns
    "m2_browning": {"name": "M2 Browning", "base_price": 14000, "category": "military",
                    "description": "US .50 caliber heavy machine gun"},
    "m240b": {"name": "M240B", "base_price": 6800, "category": "military",
              "description": "US 7.62mm medium machine gun"},
    "pkm": {"name": "PKM", "base_price": 4500, "category": "military",
            "description": "Russian 7.62mm general-purpose machine gun"},
    "mg3": {"name": "MG3", "base_price": 7200, "category": "military",
            "description": "German 7.62mm general-purpose machine gun"},
    # Ground vehicles
    "m2_bradley": {"name": "M2 Bradley", "base_price": 4200000, "category": "military",
                   "description": "US infantry fighting vehicle, 25mm chain gun"},
    "stryker_apc": {"name": "Stryker APC", "base_price": 4700000, "category": "military",
                    "description": "US wheeled armored personnel carrier"},
    "bmp3_ifv": {"name": "BMP-3 IFV", "base_price": 3100000, "category": "military",
                 "description": "Russian infantry fighting vehicle"},
    "btr82_apc": {"name": "BTR-82A APC", "base_price": 1800000, "category": "military",
                  "description": "Russian wheeled armored personnel carrier"},
    "boxer_apc": {"name": "Boxer APC", "base_price": 5800000, "category": "military",
                  "description": "German/Dutch modular wheeled APC"},
    "puma_ifv": {"name": "Puma IFV", "base_price": 8100000, "category": "military",
                 "description": "German next-generation infantry fighting vehicle"},
    "jltv": {"name": "JLTV", "base_price": 280000, "category": "military",
             "description": "US Joint Light Tactical Vehicle"},
    "oshkosh_fmtv": {"name": "Oshkosh FMTV", "base_price": 185000, "category": "military",
                     "description": "US Family of Medium Tactical Vehicles military truck"},
    "m109_paladin": {"name": "M109 Paladin", "base_price": 6000000, "category": "military",
                     "description": "US self-propelled 155mm howitzer"},
    "pzh2000": {"name": "PzH 2000", "base_price": 8500000, "category": "military",
                "description": "German self-propelled 155mm howitzer"},
    "hmmwv": {"name": "HMMWV", "base_price": 220000, "category": "military",
              "description": "US High Mobility Multipurpose Wheeled Vehicle"},
    # Optics
    "acog_optic": {"name": "ACOG Optic", "base_price": 1400, "category": "military",
                   "description": "Trijicon ACOG 4× fixed-power combat optic"},
    "eotech_holo": {"name": "EOTech Holographic Sight", "base_price": 650, "category": "military",
                    "description": "Holographic weapon sight for CQB"},
    "aimpoint_rds": {"name": "Aimpoint Red Dot Sight", "base_price": 850, "category": "military",
                     "description": "Aimpoint red dot sight for rifles"},
    "sb_sniper_scope": {"name": "Schmidt & Bender Sniper Scope", "base_price": 3800, "category": "military",
                        "description": "High-power precision scope for sniper rifles"},
    "leupold_scope": {"name": "Leupold MK5 Scope", "base_price": 2800, "category": "military",
                      "description": "Leupold Mark 5HD precision rifle scope"},
    "elcan_optic": {"name": "Elcan Specter DR", "base_price": 2200, "category": "military",
                    "description": "Dual-role 1-4× combat optic"},
    "kahles_scope": {"name": "Kahles K525i Scope", "base_price": 4200, "category": "military",
                     "description": "Austrian 5-25× precision long-range scope"},
    "pvs14_nvg": {"name": "PVS-14 NVG", "base_price": 3200, "category": "military",
                  "description": "AN/PVS-14 monocular night vision goggle"},
    "pvs31_nvg": {"name": "PVS-31A NVG", "base_price": 8500, "category": "military",
                  "description": "AN/PVS-31A dual-tube binocular night vision"},
    # Body armor parts
    "esapi_plate": {"name": "ESAPI Plate", "base_price": 400, "category": "military",
                    "description": "Enhanced Small Arms Protective Insert ceramic plate"},
    "plate_carrier": {"name": "Plate Carrier", "base_price": 280, "category": "military",
                      "description": "Modular tactical plate carrier vest"},
    "iotv_vest": {"name": "IOTV Vest", "base_price": 1800, "category": "military",
                  "description": "Improved Outer Tactical Vest with ESAPI plates"},
    # Helmet
    "ach_helmet": {"name": "ACH Helmet", "base_price": 380, "category": "military",
                   "description": "US Advanced Combat Helmet"},
    # Comms
    "anprc152_radio": {"name": "AN/PRC-152 Radio", "base_price": 8500, "category": "military",
                       "description": "Handheld multiband tactical radio"},
    "ky58_crypto": {"name": "KY-58 Crypto Module", "base_price": 12000, "category": "military",
                    "description": "VINSON voice encryption module for secure comms"},
    # Uniform
    "ocp_uniform": {"name": "OCP Uniform", "base_price": 185, "category": "military",
                    "description": "Operational Camouflage Pattern combat uniform"},
}

# In-place updates to existing items
ITEM_UPDATES = {
    "body_armor": {"name": "IOTV Body Armor",
                   "description": "Improved Outer Tactical Vest complete assembly"},
    "combat_helmet": {"name": "ACH Combat Helmet",
                      "description": "Advanced Combat Helmet, ballistic protection"},
    "military_radio": {"name": "AN/PRC-152 Radio",
                       "description": "Handheld multiband tactical radio"},
    "encryption_device": {"name": "KY-58 Crypto Module",
                          "description": "VINSON voice encryption module for secure comms"},
    "military_uniform": {"name": "OCP Combat Uniform",
                         "description": "Operational Camouflage Pattern combat uniform"},
    "humvee": {"name": "HMMWV",
               "description": "High Mobility Multipurpose Wheeled Vehicle"},
    "military_truck": {"name": "Oshkosh FMTV",
                       "description": "Oshkosh Family of Medium Tactical Vehicles"},
}

# Items to REMOVE (replaced by specific named items)
ITEMS_TO_REMOVE = {
    "rifle", "fighter_jet", "tank", "submarine", "naval_destroyer", "military_helicopter",
    "missile", "ammunition", "ammunition_crate", "grenade", "grenade_body", "smoke_grenade",
    "wp_grenade", "incendiary_rocket", "explosive_ordnance", "det_cord", "artillery_shell",
    "torpedo", "drone", "military_drone", "drone_swarm_unit", "machine_gun", "apc",
    "infantry_fighting_vehicle", "armored_car", "main_battle_tank", "leo2_leopard_tank",
    "scope", "targeting_optic", "night_vision_optic", "missile_warhead", "missile_guidance_unit",
    "rocket_motor", "self_propelled_artillery", "drone_avionics",
}

# ============================================================
# 1. ITEM_TYPES.JSON
# ============================================================

def update_item_types():
    print("\n=== Updating item_types.json ===")
    data = load_json("item_types.json")

    added = []
    updated = []
    removed = []

    # Add new items (idempotent)
    for slug, info in NEW_ITEMS.items():
        if slug not in data:
            data[slug] = {
                "base_price": info["base_price"],
                "category": info["category"],
                "description": info["description"],
                "name": info["name"],
            }
            added.append(slug)
        else:
            print(f"  [SKIP] {slug} already exists in item_types.json")

    # Update existing items in-place
    for slug, updates in ITEM_UPDATES.items():
        if slug in data:
            for k, v in updates.items():
                data[slug][k] = v
            updated.append(slug)
        else:
            print(f"  [WARN] item to update not found: {slug}")

    # Remove obsolete items
    for slug in ITEMS_TO_REMOVE:
        if slug in data:
            del data[slug]
            removed.append(slug)

    save_json("item_types.json", data)
    print(f"  Added {len(added)} items: {added}")
    print(f"  Updated {len(updated)} items: {updated}")
    print(f"  Removed {len(removed)} items: {removed}")

# ============================================================
# 2. DISTRICT_ITEMS.JSON
# ============================================================

def update_district_items():
    print("\n=== Updating district_items.json ===")
    data = load_json("district_items.json")

    added = []
    updated = []
    removed = []

    # Add new items
    for slug, info in NEW_ITEMS.items():
        if slug not in data:
            data[slug] = {
                "base_price": info["base_price"],
                "base_sale_chance": 0.15,
                "category": info["category"],
                "description": info["description"],
                "elasticity": 1.2,
                "name": info["name"],
            }
            added.append(slug)
        else:
            print(f"  [SKIP] {slug} already exists in district_items.json")

    # Update existing items in-place
    for slug, updates in ITEM_UPDATES.items():
        if slug in data:
            for k, v in updates.items():
                data[slug][k] = v
            updated.append(slug)
        else:
            print(f"  [WARN] item to update not found: {slug}")

    # Remove obsolete items
    for slug in ITEMS_TO_REMOVE:
        if slug in data:
            del data[slug]
            removed.append(slug)

    save_json("district_items.json", data)
    print(f"  Added {len(added)} items: {added}")
    print(f"  Updated {len(updated)} items: {updated}")
    print(f"  Removed {len(removed)} items: {removed}")

# ============================================================
# 3. DISTRICT_BUSINESSES.JSON
# ============================================================

def replace_item_in_line(line, old, new):
    """Replace old item slug with new in a production line's inputs."""
    for inp in line.get("inputs", []):
        if inp["item"] == old:
            inp["item"] = new
    if line.get("output_item") == old:
        line["output_item"] = new
    return line

def production_line_output_slugs(business):
    return [pl["output_item"] for pl in business.get("production_lines", [])]

def update_district_businesses():
    print("\n=== Updating district_businesses.json ===")
    data = load_json("district_businesses.json")
    changes = []

    # --- weapons_factory ---
    wf = data.get("weapons_factory", {})
    new_lines_wf = []
    for line in wf.get("production_lines", []):
        out = line["output_item"]
        if out == "ammunition":
            # Replace with 556_nato_crate production line
            if "556_nato_crate" not in production_line_output_slugs(wf):
                new_line = {
                    "inputs": [
                        {"item": "brass", "quantity": 500},
                        {"item": "lead", "quantity": 300},
                        {"item": "copper", "quantity": 200},
                        {"item": "paper", "quantity": 30},
                        {"item": "energy", "quantity": 35000}
                    ],
                    "output_item": "556_nato_crate",
                    "output_qty": 500
                }
                new_lines_wf.append(new_line)
                changes.append("weapons_factory: replaced ammunition line with 556_nato_crate")
                # Also add 762x39_crate
                new_lines_wf.append({
                    "inputs": [
                        {"item": "brass", "quantity": 400},
                        {"item": "lead", "quantity": 250},
                        {"item": "copper", "quantity": 180},
                        {"item": "paper", "quantity": 25},
                        {"item": "energy", "quantity": 30000}
                    ],
                    "output_item": "762x39_crate",
                    "output_qty": 500
                })
                changes.append("weapons_factory: added 762x39_crate line")
                new_lines_wf.append({
                    "inputs": [
                        {"item": "brass", "quantity": 350},
                        {"item": "lead", "quantity": 220},
                        {"item": "copper", "quantity": 150},
                        {"item": "paper", "quantity": 20},
                        {"item": "energy", "quantity": 28000}
                    ],
                    "output_item": "9mm_crate",
                    "output_qty": 600
                })
                changes.append("weapons_factory: added 9mm_crate line")
        elif out == "ammunition_crate":
            # Skip - replaced above
            changes.append("weapons_factory: dropped old ammunition_crate packaging line")
            continue
        elif out == "grenade":
            # Replace with m67_grenade
            line["output_item"] = "m67_grenade"
            # Replace grenade_body input with frag_grenade_body
            for inp in line["inputs"]:
                if inp["item"] == "grenade_body":
                    inp["item"] = "frag_grenade_body"
                if inp["item"] == "det_cord":
                    inp["item"] = "comp_b_filler"
            new_lines_wf.append(line)
            changes.append("weapons_factory: grenade -> m67_grenade")
            # Add rgo_grenade line
            new_lines_wf.append({
                "inputs": [
                    {"item": "frag_grenade_body", "quantity": 200},
                    {"item": "comp_b_filler", "quantity": 100},
                    {"item": "smokeless_powder", "quantity": 80},
                    {"item": "energy", "quantity": 15000},
                    {"item": "paper", "quantity": 15}
                ],
                "output_item": "rgo_grenade",
                "output_qty": 300
            })
            changes.append("weapons_factory: added rgo_grenade line")
        elif out == "missile":
            # Replace with aim120_amraam
            line["output_item"] = "aim120_amraam"
            for inp in line["inputs"]:
                if inp["item"] == "missile_warhead":
                    inp["item"] = "radar_seeker"
                if inp["item"] == "rocket_motor":
                    inp["item"] = "solid_rocket_motor"
                if inp["item"] == "missile_guidance_unit":
                    inp["item"] = "gps_ins_guidance"
            new_lines_wf.append(line)
            changes.append("weapons_factory: missile -> aim120_amraam")
            # Add r77 line
            new_lines_wf.append({
                "inputs": [
                    {"item": "radar_seeker", "quantity": 15},
                    {"item": "solid_rocket_motor", "quantity": 12},
                    {"item": "gps_ins_guidance", "quantity": 15},
                    {"item": "maraging_steel", "quantity": 80},
                    {"item": "jet_fuel", "quantity": 40},
                    {"item": "energy", "quantity": 80000},
                    {"item": "paper", "quantity": 60}
                ],
                "output_item": "r77_missile",
                "output_qty": 25
            })
            changes.append("weapons_factory: added r77_missile line")
            # Add agm114_hellfire line
            new_lines_wf.append({
                "inputs": [
                    {"item": "laser_seeker", "quantity": 20},
                    {"item": "shaped_charge_warhead", "quantity": 20},
                    {"item": "solid_rocket_motor", "quantity": 20},
                    {"item": "maraging_steel", "quantity": 60},
                    {"item": "energy", "quantity": 60000},
                    {"item": "paper", "quantity": 50}
                ],
                "output_item": "agm114_hellfire",
                "output_qty": 30
            })
            changes.append("weapons_factory: added agm114_hellfire line")
        elif out == "grenade_body":
            # Rename to frag_grenade_body
            line["output_item"] = "frag_grenade_body"
            new_lines_wf.append(line)
            changes.append("weapons_factory: grenade_body -> frag_grenade_body")
        elif out == "missile_warhead":
            # Rename to frag_warhead
            line["output_item"] = "frag_warhead"
            for inp in line["inputs"]:
                if inp["item"] == "thermite":
                    pass  # keep
            new_lines_wf.append(line)
            changes.append("weapons_factory: missile_warhead -> frag_warhead")
        elif out == "machine_gun":
            # Replace with m2_browning
            line["output_item"] = "m2_browning"
            new_lines_wf.append(line)
            changes.append("weapons_factory: machine_gun -> m2_browning")
            # Also add pkm
            new_lines_wf.append({
                "inputs": [
                    {"item": "steel", "quantity": 150},
                    {"item": "molybdenum", "quantity": 30},
                    {"item": "rifle_barrel", "quantity": 15},
                    {"item": "energy", "quantity": 40000},
                    {"item": "paper", "quantity": 30}
                ],
                "output_item": "pkm",
                "output_qty": 60
            })
            changes.append("weapons_factory: added pkm line")
        elif out == "det_cord":
            # Replace with semtex_charge
            line["output_item"] = "semtex_charge"
            new_lines_wf.append(line)
            changes.append("weapons_factory: det_cord -> semtex_charge")
            # Add m112_c4
            new_lines_wf.append({
                "inputs": [
                    {"item": "rdx_explosive", "quantity": 150},
                    {"item": "plastic", "quantity": 80},
                    {"item": "energy", "quantity": 12000},
                    {"item": "paper", "quantity": 12}
                ],
                "output_item": "m112_c4",
                "output_qty": 200
            })
            changes.append("weapons_factory: added m112_c4 line")
        elif out == "smoke_grenade":
            line["output_item"] = "m18_smoke_grenade"
            for inp in line["inputs"]:
                if inp["item"] == "grenade_body":
                    inp["item"] = "frag_grenade_body"
            new_lines_wf.append(line)
            changes.append("weapons_factory: smoke_grenade -> m18_smoke_grenade")
        elif out == "wp_grenade":
            line["output_item"] = "m15_wp_grenade"
            for inp in line["inputs"]:
                if inp["item"] == "grenade_body":
                    inp["item"] = "frag_grenade_body"
                if inp["item"] == "det_cord":
                    inp["item"] = "comp_b_filler"
            new_lines_wf.append(line)
            changes.append("weapons_factory: wp_grenade -> m15_wp_grenade")
        elif out == "incendiary_rocket":
            # drop incendiary_rocket line, replace with switchblade_600
            if "switchblade_600" not in [l["output_item"] for l in new_lines_wf]:
                new_lines_wf.append({
                    "inputs": [
                        {"item": "solid_rocket_motor", "quantity": 10},
                        {"item": "shaped_charge_warhead", "quantity": 10},
                        {"item": "gps_ins_guidance", "quantity": 10},
                        {"item": "carbon_fiber", "quantity": 30},
                        {"item": "energy", "quantity": 20000},
                        {"item": "paper", "quantity": 15}
                    ],
                    "output_item": "switchblade_600",
                    "output_qty": 20
                })
                changes.append("weapons_factory: incendiary_rocket -> switchblade_600")
        else:
            new_lines_wf.append(line)

    wf["production_lines"] = new_lines_wf
    data["weapons_factory"] = wf

    # --- military_vehicle_plant ---
    mvp = data.get("military_vehicle_plant", {})
    for line in mvp.get("production_lines", []):
        out = line["output_item"]
        if out == "apc":
            line["output_item"] = "stryker_apc"
            for inp in line["inputs"]:
                if inp["item"] == "machine_gun":
                    inp["item"] = "m2_browning"
            changes.append("military_vehicle_plant: apc -> stryker_apc")
        elif out == "infantry_fighting_vehicle":
            line["output_item"] = "m2_bradley"
            for inp in line["inputs"]:
                if inp["item"] == "missile":
                    inp["item"] = "agm114_hellfire"
            changes.append("military_vehicle_plant: infantry_fighting_vehicle -> m2_bradley")
        elif out == "armored_car":
            line["output_item"] = "jltv"
            changes.append("military_vehicle_plant: armored_car -> jltv")
        elif out == "self_propelled_artillery":
            line["output_item"] = "m109_paladin"
            for inp in line["inputs"]:
                if inp["item"] == "artillery_shell":
                    inp["item"] = "m795_shell"
            changes.append("military_vehicle_plant: self_propelled_artillery -> m109_paladin")
        elif out == "main_battle_tank":
            # keep as-is (main_battle_tank is generic, leave it)
            pass
        elif out == "drone":
            # civil drone in vehicle plant - leave it
            pass

    data["military_vehicle_plant"] = mvp

    # --- military_aircraft_plant ---
    map_ = data.get("military_aircraft_plant", {})
    for line in map_.get("production_lines", []):
        out = line["output_item"]
        if out == "military_drone":
            line["output_item"] = "mq9_reaper"
            for inp in line["inputs"]:
                if inp["item"] == "drone_avionics":
                    inp["item"] = "gps_ins_guidance"
            changes.append("military_aircraft_plant: military_drone -> mq9_reaper")
        elif out == "drone_swarm_unit":
            line["output_item"] = "bayraktar_tb2"
            for inp in line["inputs"]:
                if inp["item"] == "drone_avionics":
                    inp["item"] = "gps_ins_guidance"
            changes.append("military_aircraft_plant: drone_swarm_unit -> bayraktar_tb2")
        elif out == "attack_helicopter":
            for inp in line["inputs"]:
                if inp["item"] == "missile":
                    inp["item"] = "agm114_hellfire"
            changes.append("military_aircraft_plant: replaced missile input in attack_helicopter")
        else:
            # All fighter jets: replace missile input with aim120_amraam
            for inp in line["inputs"]:
                if inp["item"] == "missile":
                    inp["item"] = "aim120_amraam"
                    changes.append(f"military_aircraft_plant: replaced missile->aim120_amraam in {out}")

    data["military_aircraft_plant"] = map_

    # --- naval_shipyard ---
    ns = data.get("naval_shipyard", {})
    for line in ns.get("production_lines", []):
        out = line["output_item"]
        for inp in line["inputs"]:
            if inp["item"] == "missile":
                if "carrier" in out or "destroyer" in out or "frigate" in out:
                    inp["item"] = "bgm109_tomahawk"
                    changes.append(f"naval_shipyard: missile->bgm109_tomahawk in {out}")
                else:
                    inp["item"] = "bgm109_tomahawk"
            if inp["item"] == "torpedo":
                inp["item"] = "mk48_torpedo"
                changes.append(f"naval_shipyard: torpedo->mk48_torpedo in {out}")

    data["naval_shipyard"] = ns

    # --- munitions_depot ---
    md = data.get("munitions_depot", {})
    new_md_lines = []
    for line in md.get("production_lines", []):
        out = line["output_item"]
        if out == "ammunition_crate":
            # Rename to 556_nato_crate
            line["output_item"] = "556_nato_crate"
            new_md_lines.append(line)
            changes.append("munitions_depot: ammunition_crate -> 556_nato_crate")
        elif out == "explosive_ordnance":
            # Replace with m112_c4
            line["output_item"] = "m112_c4"
            for inp in line["inputs"]:
                if inp["item"] == "coal":
                    inp["item"] = "rdx_explosive"
            new_md_lines.append(line)
            changes.append("munitions_depot: explosive_ordnance -> m112_c4")
        elif out == "artillery_shell":
            line["output_item"] = "m795_shell"
            new_md_lines.append(line)
            changes.append("munitions_depot: artillery_shell -> m795_shell")
        elif out == "special_munitions_kit":
            # Update inputs referencing old items
            for inp in line["inputs"]:
                if inp["item"] == "smoke_grenade":
                    inp["item"] = "m18_smoke_grenade"
                if inp["item"] == "wp_grenade":
                    inp["item"] = "m15_wp_grenade"
                if inp["item"] == "incendiary_rocket":
                    inp["item"] = "switchblade_600"
            new_md_lines.append(line)
            changes.append("munitions_depot: updated special_munitions_kit inputs")
        else:
            new_md_lines.append(line)

    # Add mk48_torpedo production line
    if not any(l["output_item"] == "mk48_torpedo" for l in new_md_lines):
        new_md_lines.append({
            "inputs": [
                {"item": "maraging_steel", "quantity": 200},
                {"item": "titanium_alloy", "quantity": 100},
                {"item": "rdx_explosive", "quantity": 150},
                {"item": "gps_ins_guidance", "quantity": 10},
                {"item": "energy", "quantity": 100000},
                {"item": "paper", "quantity": 80}
            ],
            "output_item": "mk48_torpedo",
            "output_qty": 5
        })
        changes.append("munitions_depot: added mk48_torpedo line")

    # Add m982_excalibur line
    if not any(l["output_item"] == "m982_excalibur" for l in new_md_lines):
        new_md_lines.append({
            "inputs": [
                {"item": "steel", "quantity": 300},
                {"item": "rdx_explosive", "quantity": 150},
                {"item": "gps_ins_guidance", "quantity": 20},
                {"item": "brass", "quantity": 100},
                {"item": "energy", "quantity": 50000},
                {"item": "paper", "quantity": 40}
            ],
            "output_item": "m982_excalibur",
            "output_qty": 20
        })
        changes.append("munitions_depot: added m982_excalibur line")

    md["production_lines"] = new_md_lines
    data["munitions_depot"] = md

    # --- defense_electronics_factory ---
    def_ = data.get("defense_electronics_factory", {})
    for line in def_.get("production_lines", []):
        out = line["output_item"]
        if out == "targeting_optic":
            line["output_item"] = "acog_optic"
            changes.append("defense_electronics_factory: targeting_optic -> acog_optic")
        elif out == "night_vision_optic":
            line["output_item"] = "pvs14_nvg"
            changes.append("defense_electronics_factory: night_vision_optic -> pvs14_nvg")

    # Add scope lines if not present
    existing_outputs = [l["output_item"] for l in def_.get("production_lines", [])]
    if "sb_sniper_scope" not in existing_outputs:
        def_["production_lines"].append({
            "inputs": [
                {"item": "optical_glass", "quantity": 100},
                {"item": "titanium_alloy", "quantity": 20},
                {"item": "circuit_board", "quantity": 15},
                {"item": "energy", "quantity": 25000},
                {"item": "paper", "quantity": 20}
            ],
            "output_item": "sb_sniper_scope",
            "output_qty": 50
        })
        changes.append("defense_electronics_factory: added sb_sniper_scope line")

    if "pvs31_nvg" not in existing_outputs:
        def_["production_lines"].append({
            "inputs": [
                {"item": "optical_glass", "quantity": 120},
                {"item": "gallium_arsenide", "quantity": 50},
                {"item": "processor", "quantity": 30},
                {"item": "circuit_board", "quantity": 30},
                {"item": "energy", "quantity": 60000},
                {"item": "paper", "quantity": 50}
            ],
            "output_item": "pvs31_nvg",
            "output_qty": 40
        })
        changes.append("defense_electronics_factory: added pvs31_nvg line")

    data["defense_electronics_factory"] = def_

    # --- tactical_gear_factory ---
    tgf = data.get("tactical_gear_factory", {})
    for line in tgf.get("production_lines", []):
        out = line["output_item"]
        if out == "military_radio":
            line["output_item"] = "anprc152_radio"
            changes.append("tactical_gear_factory: military_radio -> anprc152_radio")
        elif out == "encryption_device":
            line["output_item"] = "ky58_crypto"
            changes.append("tactical_gear_factory: encryption_device -> ky58_crypto")

    data["tactical_gear_factory"] = tgf

    save_json("district_businesses.json", data)
    print(f"  Made {len(changes)} changes:")
    for c in changes:
        print(f"    - {c}")

# ============================================================
# 4. BUSINESS_TYPES.JSON
# ============================================================

def update_business_types():
    print("\n=== Updating business_types.json ===")
    data = load_json("business_types.json")
    changes = []

    wf = data.get("weapons_factory", {})
    if wf:
        wf["description"] = "Military arms plant producing assault rifles, machine guns, ammunition crates, grenades, and missiles."
        new_lines = []
        for line in wf.get("production_lines", []):
            out = line["output_item"]
            if out == "rifle":
                # Keep structure but point to m4_carbine (already exists elsewhere, leave it)
                new_lines.append(line)
            elif out == "machine_gun":
                line["output_item"] = "m2_browning"
                for inp in line["inputs"]:
                    if inp["item"] == "copper_wire":
                        pass  # keep
                new_lines.append(line)
                changes.append("business_types weapons_factory: machine_gun -> m2_browning")
            else:
                new_lines.append(line)
        wf["production_lines"] = new_lines
        data["weapons_factory"] = wf

    save_json("business_types.json", data)
    print(f"  Made {len(changes)} changes:")
    for c in changes:
        print(f"    - {c}")

# ============================================================
# 5. NPC CONFIGS
# ============================================================

def update_npc_active_lines(businesses, replacements):
    """Replace items in active_lines lists."""
    changed = []
    for biz in businesses:
        if "active_lines" in biz:
            new_lines = []
            for item in biz["active_lines"]:
                if item in replacements:
                    new_item = replacements[item]
                    new_lines.append(new_item)
                    changed.append(f"{item} -> {new_item}")
                else:
                    new_lines.append(item)
            biz["active_lines"] = new_lines
    return changed

def update_npc_buy_items(buy_items, replacements, remove_keys=None):
    """Replace keys in buy_items dict."""
    changed = []
    keys = list(buy_items.keys())
    for old_key in keys:
        if old_key in replacements:
            new_key = replacements[old_key]
            if new_key not in buy_items:
                buy_items[new_key] = buy_items.pop(old_key)
                changed.append(f"buy {old_key} -> {new_key}")
            else:
                del buy_items[old_key]
                changed.append(f"buy {old_key} removed (new key already exists)")
        elif remove_keys and old_key in remove_keys:
            del buy_items[old_key]
            changed.append(f"buy {old_key} removed")
    return changed

def update_npc_sell_items(sell_items, replacements):
    """Replace keys in sell_items dict."""
    changed = []
    keys = list(sell_items.keys())
    for old_key in keys:
        if old_key in replacements:
            new_key = replacements[old_key]
            if new_key not in sell_items:
                sell_items[new_key] = sell_items.pop(old_key)
                changed.append(f"sell {old_key} -> {new_key}")
            else:
                del sell_items[old_key]
                changed.append(f"sell {old_key} removed (new key already exists)")
    return changed

def update_npc_configs():
    print("\n=== Updating NPC config files ===")

    # npc_043_ironclad_defense
    path = "npc_configs/npc_043_ironclad_defense.json"
    data = load_json(path)
    changes = []

    active_replacements = {
        "machine_gun": "m2_browning",
        "ammunition": "556_nato_crate",
        "grenade": "m67_grenade",
        "missile": "aim120_amraam",
        "ammunition_crate": "556_nato_crate",
        "det_cord": "semtex_charge",
    }
    changes += update_npc_active_lines(data["businesses"], active_replacements)

    buy_replacements = {
        "artillery_shell": "m795_shell",
        "explosive_ordnance": "m112_c4",
        "tank": "m1a2_abrams",
        "targeting_optic": "sb_sniper_scope",
    }
    changes += update_npc_buy_items(data["buy_items"], buy_replacements)

    sell_replacements = {
        "ammunition": "556_nato_crate",
        "apc": "stryker_apc",
        "det_cord": "semtex_charge",
        "drone": "mq9_reaper",
        "grenade": "m67_grenade",
        "machine_gun": "m2_browning",
        "missile": "aim120_amraam",
        # body_armor - keep as-is
    }
    changes += update_npc_sell_items(data["sell_items"], sell_replacements)

    save_json(path, data)
    print(f"  npc_043: {len(changes)} changes: {changes}")

    # npc_065_eagle_defense_industries
    path = "npc_configs/npc_065_eagle_defense_industries.json"
    data = load_json(path)
    changes = []

    active_replacements = {
        "machine_gun": "m2_browning",
        "ammunition": "556_nato_crate",
        "grenade": "m67_grenade",
        "missile": "aim120_amraam",
        "apc": "stryker_apc",
    }
    changes += update_npc_active_lines(data["businesses"], active_replacements)

    sell_replacements = {
        "ammunition": "556_nato_crate",
        "grenade": "m67_grenade",
        "machine_gun": "m2_browning",
    }
    changes += update_npc_sell_items(data["sell_items"], sell_replacements)

    save_json(path, data)
    print(f"  npc_065: {len(changes)} changes: {changes}")

    # npc_067_vostok_arms_federation
    path = "npc_configs/npc_067_vostok_arms_federation.json"
    data = load_json(path)
    changes = []

    active_replacements = {
        "machine_gun": "pkm",
        "ammunition": "762x39_crate",
        "grenade": "rgo_grenade",
        "missile": "r77_missile",
    }
    changes += update_npc_active_lines(data["businesses"], active_replacements)

    buy_replacements = {
        "missile": "r77_missile",
        "rifle": "ak_47",
    }
    changes += update_npc_buy_items(data["buy_items"], buy_replacements)

    save_json(path, data)
    print(f"  npc_067: {len(changes)} changes: {changes}")

    # npc_068_allied_naval_foundry
    path = "npc_configs/npc_068_allied_naval_foundry.json"
    data = load_json(path)
    changes = []

    buy_replacements = {
        "missile": "agm84_harpoon",
        "torpedo": "mk48_torpedo",
    }
    changes += update_npc_buy_items(data["buy_items"], buy_replacements)

    save_json(path, data)
    print(f"  npc_068: {len(changes)} changes: {changes}")

    # npc_045_ironkeel_naval
    path = "npc_configs/npc_045_ironkeel_naval.json"
    data = load_json(path)
    changes = []

    buy_replacements = {
        "missile": "bgm109_tomahawk",
        "torpedo": "mk48_torpedo",
    }
    changes += update_npc_buy_items(data["buy_items"], buy_replacements)

    save_json(path, data)
    print(f"  npc_045: {len(changes)} changes: {changes}")

    # npc_066_pacific_aerospace_group
    path = "npc_configs/npc_066_pacific_aerospace_group.json"
    data = load_json(path)
    changes = []

    buy_replacements = {
        "missile": "aim120_amraam",
    }
    changes += update_npc_buy_items(data["buy_items"], buy_replacements)

    save_json(path, data)
    print(f"  npc_066: {len(changes)} changes: {changes}")

    # npc_094_axleworks_auto_parts
    path = "npc_configs/npc_094_axleworks_auto_parts.json"
    data = load_json(path)
    changes = []

    buy_replacements = {
        "fighter_jet": "f16_falcon",
        "military_helicopter": "uh60_blackhawk",
        "submarine": "virginia_class_sub",
    }
    changes += update_npc_buy_items(data["buy_items"], buy_replacements)

    save_json(path, data)
    print(f"  npc_094: {len(changes)} changes: {changes}")

    # npc_038_continental_motor
    path = "npc_configs/npc_038_continental_motor.json"
    data = load_json(path)
    changes = []

    buy_replacements = {
        "naval_destroyer": "arleigh_burke_destroyer",
        "military_drone": "mq9_reaper",
        "drone_swarm_unit": "bayraktar_tb2",
    }
    changes += update_npc_buy_items(data["buy_items"], buy_replacements)

    save_json(path, data)
    print(f"  npc_038: {len(changes)} changes: {changes}")

# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("apply_weapons_realism.py - Wadsworth SymCo Military Realism")
    print("=" * 60)

    update_item_types()
    update_district_items()
    update_district_businesses()
    update_business_types()
    update_npc_configs()

    print("\n" + "=" * 60)
    print("DONE. All files updated successfully.")
    print("=" * 60)
