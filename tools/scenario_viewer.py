#!/usr/bin/env python3
"""
Wizardry 6: Bane of the Cosmic Forge — scenario.dbs Extractor
=============================================================
Reverse-engineered binary parser for the master game-data file.

File layout (188,980 bytes):
  0x00000 - 0x0037F : XP tables (14 classes × 16 levels, 32-bit LE each)
  0x00380 - 0x08F1D : Item table  (483 slots × 74 bytes)
  0x08F1E - 0x09408 : Zero padding
  0x09409 - 0x154E5 : Graphic tiles, race/class tables, map/event data (binary)
  0x154E6 - 0x02622F: Monster table (256 slots × 222 bytes)
  0x026230 - end    : Map events, loot tables, and tail data (binary)
"""

import argparse
import struct
import json
import csv
from pathlib import Path
from collections import OrderedDict

# ─── Constants ───────────────────────────────────────────────────────────────

# --- XP Tables ---
XP_TABLE_OFFSET      = 0x0000
XP_LEVELS            = 16       # levels 1-13 (level 1 = 0 xp, stored values are levels 2-16 thresholds?)
XP_ENTRY_SIZE        = 4        # uint32 LE
XP_CLASSES           = 14
XP_ENTRIES_PER_CLASS = 16

CLASS_NAMES = [
    "Fighter", "Mage", "Priest", "Thief",
    "Ranger", "Alchemist", "Bard", "Psionic",
    "Valkyrie", "Bishop", "Lord", "Ninja",
    "Monk", "Samurai"
]

# --- Item Table ---
ITEM_TABLE_OFFSET = 0x0380
ITEM_RECORD_SIZE  = 74     # 0x4A bytes per item
ITEM_SLOT_COUNT   = 483    # total slots (many empty)

# Item equip-slot / category byte (offset +0x3B within record)
ITEM_CATEGORIES = {
    0: "None/Misc",
    1: "Melee Primary",
    2: "Thrown",
    3: "Ranged",
    4: "Extended Range",
    5: "Shield",
    6: "Accessory",
    7: "Quest Item",
    8: "Usable/Consumable",
}

# Byte +0x3A in item record: class equip restrictions (bit-flags)
EQUIP_SLOT_NAMES = {
    0x00: "1H Weapon",
    0x04: "2H Weapon",
    0x08: "Armor (Upper)",
    0x0C: "Armor (Lower)",
    0x10: "Head",
    0x14: "Hands",
    0x18: "Feet",
    0x1C: "Shield",
    0x20: "Cloak/Cape",
    0x24: "Accessory",
    0x28: "Ammo",
}

# --- Monster Table ---
MONSTER_TABLE_OFFSET = 0x154E6
MONSTER_RECORD_SIZE  = 222    # 0xDE bytes per monster
MONSTER_SLOT_COUNT   = 256    # 1-byte monster ID space


# ─── Helpers ─────────────────────────────────────────────────────────────────

def read_cstring(buf: bytes, offset: int, maxlen: int = 16) -> str:
    """Read a null-terminated ASCII string from a byte buffer."""
    raw = buf[offset:offset + maxlen]
    null = raw.find(b'\x00')
    if null >= 0:
        raw = raw[:null]
    try:
        return raw.decode('ascii')
    except UnicodeDecodeError:
        return raw.decode('latin-1', errors='replace')


def u8(buf, off):  return buf[off]
def s8(buf, off):  return struct.unpack_from('<b', buf, off)[0]
def u16(buf, off): return struct.unpack_from('<H', buf, off)[0]
def s16(buf, off): return struct.unpack_from('<h', buf, off)[0]
def u32(buf, off): return struct.unpack_from('<I', buf, off)[0]


# ─── XP Table Parser ────────────────────────────────────────────────────────

def extract_xp_tables(data: bytes) -> list[dict]:
    """Extract the 14-class × 16-level experience-point tables."""
    tables = []
    for cls_idx in range(XP_CLASSES):
        entry = {"class": CLASS_NAMES[cls_idx], "xp_thresholds": []}
        for lvl in range(XP_ENTRIES_PER_CLASS):
            off = XP_TABLE_OFFSET + (cls_idx * XP_ENTRIES_PER_CLASS + lvl) * XP_ENTRY_SIZE
            xp = u32(data, off)
            entry["xp_thresholds"].append(xp)
        tables.append(entry)
    return tables


# ─── Item Parser ─────────────────────────────────────────────────────────────

def parse_item_record(rec: bytes, slot_id: int) -> dict | None:
    """
    Parse a 74-byte item record.

    Byte map (offsets within the 74-byte record):
      +00..+0F (16 B) : Item name (null-terminated ASCII, max 15 chars + NUL)
      +10..+13 ( 4 B) : Price / value (uint32 LE) — verified vs reference
      +14      ( 1 B) : Spell-power / special ability ID
      +15      ( 1 B) : Spell school / effect type
      +16      ( 1 B) : Min STR required
      +17      ( 1 B) : Secondary stat requirement
      +18      ( 1 B) : Damage bonus (+N added to rolled damage) — verified
      +19      ( 1 B) : Unknown
      +1A      ( 1 B) : Damage dice count (e.g. 1 = "1d...") — verified
      +1B      ( 1 B) : Damage die faces (e.g. 6 = "...d6") — verified
      +1C      ( 1 B) : To-hit bonus
      +1D      ( 1 B) : Unknown
      +1E      ( 1 B) : Weight (in 0.1 lb units)
      +1F      ( 1 B) : Unknown
      +20..+35 (22 B) : Special properties, resistances, spell effects
      +36..+37 ( 2 B) : Race equip restrictions (bitmask)
      +38..+39 ( 2 B) : Class equip restrictions (bitmask)
      +3A      ( 1 B) : Weapon skill category
      +3B      ( 1 B) : Handedness/slot flags (4=2H, 8=1H)
      +3C      ( 1 B) : Equip slot type
      +3D      ( 1 B) : Attack modes / to-hit modifier
      +3E..+3F ( 2 B) : Unknown
      +40..+43 ( 4 B) : Unknown (ammo type / special flags)
      +44..+45 ( 2 B) : Spell cast on use / equip effects
      +46      ( 1 B) : AC bonus / armor class — verified vs reference
      +47      ( 1 B) : Special flags
      +48      ( 1 B) : Swings / base number of strikes
      +49      ( 1 B) : Unknown
    """
    name = read_cstring(rec, 0, 16)
    if not name or not any(c.isalpha() for c in name):
        return None

    # Replace '=' with ' of ' in item names (e.g., "CHAIN=DESPAIR" -> "CHAIN OF DESPAIR")
    name = name.replace('=', ' of ')

    # Race restriction bitmask (16-bit)
    race_bits = u16(rec, 0x36)
    RACE_NAMES = ["Human","Elf","Dwarf","Gnome","Hobbit","Faerie","Lizardman","Dracon",
                  "Felpurr","Rawulf","Mook"]
    race_restrictions = []
    if race_bits != 0 and race_bits != 0x07FF:
        for i, rn in enumerate(RACE_NAMES):
            if race_bits & (1 << i):
                race_restrictions.append(rn)

    # Class restriction bitmask (16-bit LE at +0x38, but the 2 bytes often encode
    # up to 14 class bits across +38 and +39)
    class_bits = u16(rec, 0x38)
    class_restrictions = []
    if class_bits != 0 and class_bits != 0x3FFF:
        for i, cn in enumerate(CLASS_NAMES):
            if class_bits & (1 << i):
                class_restrictions.append(cn)

    item = OrderedDict()
    item["slot_id"]        = slot_id
    item["name"]           = name
    item["price"]          = u32(rec, 0x10)
    item["spell_power"]    = u8(rec, 0x14)
    item["spell_school"]   = u8(rec, 0x15)
    item["str_required"]   = u8(rec, 0x16)
    item["stat_req_2"]     = u8(rec, 0x17)
    item["damage_bonus"]   = u8(rec, 0x18)
    item["damage_dice"]    = u8(rec, 0x1A)
    item["damage_faces"]   = u8(rec, 0x1B)
    item["to_hit_bonus"]   = s8(rec, 0x1C)
    item["weight"]         = u8(rec, 0x1E)
    item["ac_bonus"]       = s8(rec, 0x46)
    item["special_props"]  = rec[0x20:0x36].hex()
    item["race_bits"]      = f"0x{race_bits:04x}"
    item["class_bits"]     = f"0x{class_bits:04x}"
    item["weapon_skill"]   = u8(rec, 0x3A)
    item["handedness"]     = u8(rec, 0x3B)
    item["equip_slot"]     = u8(rec, 0x3C)
    item["attack_modes"]   = u8(rec, 0x3D)
    item["special_flags"]  = u8(rec, 0x47)
    item["swings"]         = u8(rec, 0x48)
    item["unknown_49"]     = u8(rec, 0x49)

    if race_restrictions:
        item["race_restrictions"] = race_restrictions
    if class_restrictions:
        item["class_restrictions"] = class_restrictions

    # Derived: damage string (range format matching game display)
    if item["damage_dice"] > 0:
        dice = item["damage_dice"]
        faces = item["damage_faces"]
        bonus = item["damage_bonus"]
        dmg_min = dice + bonus
        dmg_max = dice * faces + bonus
        item["damage_range"] = f"{dmg_min}-{dmg_max}"
        dmg_str = f"{dice}d{faces}"
        if bonus > 0:
            dmg_str += f"+{bonus}"
        item["damage_string"] = dmg_str

    return item


def extract_items(data: bytes) -> list[dict]:
    """Extract all non-empty items from the item table."""
    items = []
    for slot in range(ITEM_SLOT_COUNT):
        off = ITEM_TABLE_OFFSET + slot * ITEM_RECORD_SIZE
        if off + ITEM_RECORD_SIZE > len(data):
            break
        rec = data[off:off + ITEM_RECORD_SIZE]
        item = parse_item_record(rec, slot)
        if item:
            items.append(item)
    return items


# ─── Monster Parser ──────────────────────────────────────────────────────────

def parse_monster_record(rec: bytes, slot_id: int) -> dict | None:
    """
    Parse a 222-byte monster record.

    Byte map (offsets within the 222-byte record):
      +00..+01 ( 2 B) : Flags / header bytes
      +02..+11 (16 B) : Name singular (null-terminated ASCII)
      +12..+21 (16 B) : Name plural
      +22..+31 (16 B) : Short name singular (used in combat log)
      +32..+41 (16 B) : Short name plural
      +42..+43 ( 2 B) : Base XP reward (uint16 LE)
      +44..+45 ( 2 B) : Unknown / XP modifier
      +46      ( 1 B) : Level
      +47      ( 1 B) : Hit dice count
      +48..+5B (20 B) : Resistance & ability block
      +5C..+5F ( 4 B) : Unknown
      +60      ( 1 B) : Number of attacks
      +61      ( 1 B) : Unknown
      +62      ( 1 B) : Attack #1 damage dice
      +63      ( 1 B) : Attack #1 damage faces
      +64..+65 ( 2 B) : Group size (min, max)
      +66..+67 ( 2 B) : Attack #1 to-hit, damage bonus
      +68..+6F ( 8 B) : Additional attack data
      +70..+7F (16 B) : Elemental resistances
      +80..+87 ( 8 B) : Condition immunities
      +88..+8F ( 8 B) : Loot table references
      +90      ( 1 B) : Armor Class
      +91..+9F (15 B) : Unknown / AI behavior flags
      +A0..+A7 ( 8 B) : Spell abilities
      +A8..+B7 (16 B) : Ability scores (STR/INT/PIE/VIT/DEX/SPD/PER)
      +B8..+C3 (12 B) : Loot / treasure drop data
      +C4..+DB (24 B) : Unknown / tail data
      +DC..+DD ( 2 B) : Encounter image / sprite ID
    """
    name_s = read_cstring(rec, 0x02, 16)
    if not name_s or not any(c.isalpha() for c in name_s):
        return None

    name_p  = read_cstring(rec, 0x12, 16)
    sname_s = read_cstring(rec, 0x22, 16)
    sname_p = read_cstring(rec, 0x32, 16)

    mon = OrderedDict()
    mon["slot_id"]          = slot_id
    mon["name"]             = name_s
    mon["name_plural"]      = name_p
    mon["short_name"]       = sname_s
    mon["short_name_plural"]= sname_p
    mon["header_flags"]     = f"0x{u16(rec, 0x00):04x}"

    # XP (validated: +42 = uint16 LE XP value, confirmed RAT=150, GIANT RAT=450)
    mon["base_xp"]          = u16(rec, 0x42)
    mon["xp_field_44"]      = u16(rec, 0x44)
    mon["level"]            = u8(rec, 0x48)   # validated: RAT=1, GIANT RAT=2
    mon["hit_dice"]         = u8(rec, 0x49)

    # Combat stats
    mon["num_attacks"]      = u8(rec, 0x78)
    mon["atk1_dice"]        = u8(rec, 0x7A)
    mon["atk1_faces"]       = u8(rec, 0x7C)
    mon["atk1_bonus"]       = u8(rec, 0x79)
    mon["group_size_min"]   = u8(rec, 0x80)
    mon["group_size_max"]   = u8(rec, 0x81)
    mon["to_hit_pct"]       = u8(rec, 0x7E)

    # Armor Class (byte +a8 or nearby — needs more validation)
    mon["armor_class"]      = u8(rec, 0xA8)

    # Ability scores at +88-+8B (validated: Giant Rat STR=6, INT=4, DEX=14, SPD=16)
    stat_labels = ["STR", "INT", "DEX", "SPD"]
    abilities = [rec[0x88 + i] for i in range(4)]
    if any(b > 0 for b in abilities):
        mon["abilities"] = {stat_labels[i]: abilities[i] for i in range(4)}

    # Resistance block
    mon["resistances_hex"]  = rec[0x48:0x5C].hex()

    # Loot references
    mon["loot_refs_hex"]    = rec[0xB8:0xC6].hex()

    # Sprite / image reference
    mon["sprite_id"]        = u16(rec, 0xDC)

    # Damage string
    if mon["atk1_dice"] > 0 and mon["atk1_faces"] > 0:
        dice = mon["atk1_dice"]
        faces = mon["atk1_faces"]
        bonus = mon["atk1_bonus"]
        dmg_min = dice + bonus
        dmg_max = dice * faces + bonus
        mon["attack_damage"] = f"{dmg_min}-{dmg_max}"

    return mon


def extract_monsters(data: bytes) -> list[dict]:
    """Extract all non-empty monsters from the monster table."""
    monsters = []
    for slot in range(MONSTER_SLOT_COUNT):
        off = MONSTER_TABLE_OFFSET + slot * MONSTER_RECORD_SIZE
        if off + MONSTER_RECORD_SIZE > len(data):
            break
        rec = data[off:off + MONSTER_RECORD_SIZE]
        mon = parse_monster_record(rec, slot)
        if mon:
            monsters.append(mon)
    return monsters


# ─── Loot Table Scanner ─────────────────────────────────────────────────────

def extract_loot_tables(data: bytes) -> list[dict]:
    """
    Scan for probable loot-table entries in the tail section of the file.
    Loot entries are 54 bytes according to Saturn port analysis: item_id (u16),
    quantity, and spawn-chance percentage. We do a heuristic scan.
    """
    # The tail region after monsters (~0x26230 to end) likely contains loot data,
    # map events, and miscellaneous tables. We scan for patterns that look like
    # loot entries: a 16-bit value matching a known item ID followed by
    # reasonable quantity and chance bytes.

    # First, collect all known item IDs
    items = extract_items(data)
    valid_ids = {it["slot_id"] for it in items}

    # Scan the tail region for sequences of item-ID references
    TAIL_START = MONSTER_TABLE_OFFSET + MONSTER_SLOT_COUNT * MONSTER_RECORD_SIZE
    loot_entries = []

    for off in range(TAIL_START, len(data) - 6, 2):
        item_id = u16(data, off)
        if item_id in valid_ids and item_id > 0:
            qty = u8(data, off + 2)
            chance = u8(data, off + 3)
            if 1 <= qty <= 20 and 1 <= chance <= 100:
                loot_entries.append({
                    "file_offset": f"0x{off:06x}",
                    "item_id": item_id,
                    "item_name": next((it["name"] for it in items if it["slot_id"] == item_id), "?"),
                    "quantity": qty,
                    "chance_pct": chance,
                })

    return loot_entries


# ─── Tile / Graphic Data Identifier ─────────────────────────────────────────

def identify_graphic_sections(data: bytes) -> list[dict]:
    """
    Identify regions likely containing 4-bit planar tile graphics
    (the section between 0x9409 and monster data).
    """
    SECTION_START = 0x9409
    SECTION_END   = MONSTER_TABLE_OFFSET

    sections = []
    # Walk through and identify runs of non-zero data separated by zero-padding
    in_block = False
    block_start = 0
    for off in range(SECTION_START, SECTION_END):
        b = data[off]
        if b != 0 and not in_block:
            in_block = True
            block_start = off
        elif b == 0 and in_block:
            # Check if this is just a brief gap
            gap = 0
            while off + gap < SECTION_END and data[off + gap] == 0:
                gap += 1
            if gap > 32:
                # End of a data block
                block_len = off - block_start
                if block_len > 16:
                    sections.append({
                        "offset": f"0x{block_start:06x}",
                        "end":    f"0x{off:06x}",
                        "length": block_len,
                        "desc":   "binary data block (tiles/events/tables)"
                    })
                in_block = False

    return sections


# ─── File Structure Summary ─────────────────────────────────────────────────

def generate_structure_summary(data: bytes, items: list, monsters: list) -> dict:
    """Produce a high-level summary of the file structure."""
    return OrderedDict({
        "file_size_bytes": len(data),
        "file_size_human": f"{len(data):,} bytes ({len(data)/1024:.1f} KB)",
        "sections": [
            {
                "name": "XP Tables",
                "offset": "0x000000",
                "end": f"0x{XP_TABLE_OFFSET + XP_CLASSES * XP_ENTRIES_PER_CLASS * XP_ENTRY_SIZE:06x}",
                "size": XP_CLASSES * XP_ENTRIES_PER_CLASS * XP_ENTRY_SIZE,
                "description": f"{XP_CLASSES} class XP tables × {XP_ENTRIES_PER_CLASS} levels (uint32 LE each)"
            },
            {
                "name": "Item Table",
                "offset": f"0x{ITEM_TABLE_OFFSET:06x}",
                "end": f"0x{ITEM_TABLE_OFFSET + ITEM_SLOT_COUNT * ITEM_RECORD_SIZE:06x}",
                "size": ITEM_SLOT_COUNT * ITEM_RECORD_SIZE,
                "record_size": ITEM_RECORD_SIZE,
                "total_slots": ITEM_SLOT_COUNT,
                "populated_items": len(items),
                "description": f"{ITEM_SLOT_COUNT} slots × {ITEM_RECORD_SIZE} bytes; {len(items)} items found"
            },
            {
                "name": "Zero Padding",
                "offset": "0x008F1E",
                "end": "0x009409",
                "size": 0x9409 - 0x8F1E,
                "description": "Null bytes between item table and graphic/tile data"
            },
            {
                "name": "Graphic & Map Data",
                "offset": "0x009409",
                "end": f"0x{MONSTER_TABLE_OFFSET:06x}",
                "size": MONSTER_TABLE_OFFSET - 0x9409,
                "description": "4-bit planar tile data, race/class tables, sprite indices, map event triggers, and scripting data"
            },
            {
                "name": "Monster Table",
                "offset": f"0x{MONSTER_TABLE_OFFSET:06x}",
                "end": f"0x{MONSTER_TABLE_OFFSET + MONSTER_SLOT_COUNT * MONSTER_RECORD_SIZE:06x}",
                "size": MONSTER_SLOT_COUNT * MONSTER_RECORD_SIZE,
                "record_size": MONSTER_RECORD_SIZE,
                "total_slots": MONSTER_SLOT_COUNT,
                "populated_monsters": len(monsters),
                "description": f"{MONSTER_SLOT_COUNT} slots × {MONSTER_RECORD_SIZE} bytes; {len(monsters)} monsters found"
            },
            {
                "name": "Tail Data (Loot/Events/Maps)",
                "offset": f"0x{MONSTER_TABLE_OFFSET + MONSTER_SLOT_COUNT * MONSTER_RECORD_SIZE:06x}",
                "end": f"0x{len(data):06x}",
                "size": len(data) - (MONSTER_TABLE_OFFSET + MONSTER_SLOT_COUNT * MONSTER_RECORD_SIZE),
                "description": "Loot tables (54-byte entries), map event scripts (288/144-byte blocks), and miscellaneous binary data"
            },
        ]
    })


# ─── CSV Writers ─────────────────────────────────────────────────────────────

def write_items_csv(items: list, filepath: Path | str):
    if not items:
        return
    fields = [
        "slot_id", "name", "price", "damage_range", "damage_string",
        "damage_dice", "damage_faces", "damage_bonus",
        "to_hit_bonus", "weight", "ac_bonus", "handedness",
        "swings", "attack_modes", "weapon_skill", "equip_slot",
        "str_required", "stat_req_2", "spell_power", "spell_school",
        "race_bits", "class_bits", "special_props", "special_flags",
        "unknown_49"
    ]
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        w.writeheader()
        for item in items:
            w.writerow(item)


def write_monsters_csv(monsters: list, filepath: Path | str):
    if not monsters:
        return
    fields = [
        "slot_id", "name", "name_plural", "short_name", "short_name_plural",
        "level", "hit_dice", "base_xp", "xp_field_44",
        "armor_class", "num_attacks", "attack_damage",
        "atk1_dice", "atk1_faces", "atk1_bonus", "to_hit_pct",
        "group_size_min", "group_size_max",
        "sprite_id", "header_flags",
        "resistances_hex", "loot_refs_hex"
    ]
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        w.writeheader()
        for mon in monsters:
            w.writerow(mon)


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Extract data from Wizardry 6 scenario.dbs")
    parser.add_argument("dbs_path", help="Path to scenario.dbs (or another DBS file)")
    parser.add_argument("-o", "--output-dir", help="Where to write extracted files (defaults to DBS directory)")
    args = parser.parse_args()

    input_path = Path(args.dbs_path)
    output_dir = Path(args.output_dir) if args.output_dir else input_path.parent

    print(f"Reading: {input_path}")
    with open(input_path, 'rb') as f:
        data = f.read()
    print(f"File size: {len(data):,} bytes\n")

    output_dir.mkdir(parents=True, exist_ok=True)

    # ── XP Tables ──
    print("▸ Extracting XP tables...")
    xp_tables = extract_xp_tables(data)
    print(f"  {len(xp_tables)} class tables extracted")

    # ── Items ──
    print("▸ Extracting items...")
    items = extract_items(data)
    print(f"  {len(items)} items extracted from {ITEM_SLOT_COUNT} slots")

    # ── Monsters ──
    print("▸ Extracting monsters...")
    monsters = extract_monsters(data)
    print(f"  {len(monsters)} monsters extracted from {MONSTER_SLOT_COUNT} slots")

    # ── Loot Tables ──
    print("▸ Scanning for loot-table references...")
    loot = extract_loot_tables(data)
    print(f"  {len(loot)} probable loot entries found")

    # ── Graphic Section IDs ──
    print("▸ Mapping graphic/tile data sections...")
    gfx = identify_graphic_sections(data)
    print(f"  {len(gfx)} data blocks identified")

    # ── File Structure ──
    summary = generate_structure_summary(data, items, monsters)

    # ── Write Outputs ──

    # 1. Master JSON with everything
    master = OrderedDict({
        "file_info": summary,
        "xp_tables": xp_tables,
        "items": items,
        "monsters": monsters,
        "loot_table_refs": loot[:200],  # cap for readability
        "graphic_data_blocks": gfx,
    })
    json_path = output_dir / "scenario_dbs_extracted.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(master, f, indent=2)
    print(f"\n✓ Full JSON:     {json_path}")

    # 2. Items CSV
    items_csv = output_dir / "wiz6_items.csv"
    write_items_csv(items, items_csv)
    print(f"✓ Items CSV:     {items_csv}")

    # 3. Monsters CSV
    mons_csv = output_dir / "wiz6_monsters.csv"
    write_monsters_csv(monsters, mons_csv)
    print(f"✓ Monsters CSV:  {mons_csv}")

    # 4. Human-readable summary text
    txt_path = output_dir / "scenario_dbs_report.txt"
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write("=" * 72 + "\n")
        f.write("  WIZARDRY 6: BANE OF THE COSMIC FORGE — scenario.dbs Analysis\n")
        f.write("=" * 72 + "\n\n")

        f.write(f"File size: {len(data):,} bytes ({len(data)/1024:.1f} KB)\n\n")

        f.write("─" * 72 + "\n")
        f.write("  FILE STRUCTURE MAP\n")
        f.write("─" * 72 + "\n\n")
        for sec in summary["sections"]:
            f.write(f"  {sec['offset']} - {sec['end']}  ({sec['size']:>6,} B)  {sec['name']}\n")
            f.write(f"       {sec['description']}\n\n")

        # XP Tables
        f.write("─" * 72 + "\n")
        f.write("  XP TABLES (14 Classes × 16 Levels)\n")
        f.write("─" * 72 + "\n\n")
        hdr = f"  {'Class':<12s}"
        for lvl in range(1, XP_ENTRIES_PER_CLASS + 1):
            hdr += f" {'Lv'+str(lvl):>9s}"
        f.write(hdr + "\n")
        f.write("  " + "-" * (12 + XP_ENTRIES_PER_CLASS * 10) + "\n")
        for tbl in xp_tables:
            line = f"  {tbl['class']:<12s}"
            for xp in tbl['xp_thresholds']:
                line += f" {xp:>9,}"
            f.write(line + "\n")
        f.write("\n")

        # Items
        f.write("─" * 72 + "\n")
        f.write(f"  ITEMS ({len(items)} found)\n")
        f.write("─" * 72 + "\n\n")
        f.write(f"  {'ID':>3s}  {'Name':<20s} {'Price':>7s} {'Damage':>8s} {'AC':>4s} {'Wt':>4s} {'Swg':>3s}\n")
        f.write("  " + "-" * 60 + "\n")
        for it in items:
            dmg = it.get("damage_range", "-")
            f.write(f"  {it['slot_id']:>3d}  {it['name']:<20s} {it['price']:>7d} {dmg:>8s} {it['ac_bonus']:>4d} {it['weight']:>4d} {it['swings']:>3d}\n")
        f.write("\n")

        # Monsters
        f.write("─" * 72 + "\n")
        f.write(f"  MONSTERS ({len(monsters)} found)\n")
        f.write("─" * 72 + "\n\n")
        f.write(f"  {'ID':>3s}  {'Name':<20s} {'Lvl':>3s} {'HD':>3s} {'AC':>3s} {'Atk':>3s} {'Damage':>8s} {'XP':>6s} {'Group':>7s}\n")
        f.write("  " + "-" * 65 + "\n")
        for m in monsters:
            dmg = m.get("attack_damage", "-")
            grp = f"{m['group_size_min']}-{m['group_size_max']}"
            f.write(f"  {m['slot_id']:>3d}  {m['name']:<20s} {m['level']:>3d} {m['hit_dice']:>3d} {m['armor_class']:>3d} {m['num_attacks']:>3d} {dmg:>8s} {m['base_xp']:>6d} {grp:>7s}\n")
        f.write("\n")

        # Loot
        if loot:
            f.write("─" * 72 + "\n")
            f.write(f"  PROBABLE LOOT REFERENCES ({len(loot)} found, first 50 shown)\n")
            f.write("─" * 72 + "\n\n")
            for entry in loot[:50]:
                f.write(f"  {entry['file_offset']}: Item #{entry['item_id']:>3d} {entry['item_name']:<20s} qty={entry['quantity']} chance={entry['chance_pct']}%\n")
            f.write("\n")

    print(f"✓ Report TXT:    {txt_path}")
    print(f"\nDone. Extracted {len(items)} items, {len(monsters)} monsters, {len(xp_tables)} XP tables.")


if __name__ == "__main__":
    main()
