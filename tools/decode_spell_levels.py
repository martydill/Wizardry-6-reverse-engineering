#!/usr/bin/env python3
"""
Decode and display spell level access for all 14 classes from SCENARIO.DBS.
"""
from pathlib import Path

CLASSES = ["Fighter", "Mage", "Priest", "Thief", "Ranger", "Alchemist",
           "Bard", "Psionic", "Valkyrie", "Bishop", "Lord", "Ninja",
           "Monk", "Samurai"]

# Spell schools
SCHOOLS = {
    "Mage": "Thaumaturgy (Mage Spells)",
    "Priest": "Theology (Priest Spells)",
    "Alchemy": "Alchemy (Alchemist Spells)",
    "Psionic": "Theosophy (Psionic Spells)"
}

def decode_spell_level(value):
    """Decode hex value to spell level (0-7)."""
    if value == 0:
        return "None"

    high_nibble = (value >> 4) & 0x0F
    low_nibble = value & 0x0F

    # Most common pattern: high nibble is the spell level
    if high_nibble > 0:
        if high_nibble == 7 and low_nibble == 7:
            return "7 (Full)"
        elif high_nibble == 7 and low_nibble == 0:
            return "7"
        elif high_nibble == 5 and low_nibble == 0:
            return "5 (Limited)"
        elif high_nibble == 9:  # Special Bard case
            return f"? (0x{value:02X})"
        else:
            return f"{high_nibble}"
    elif low_nibble > 0:
        return f"{low_nibble}"

    return f"? (0x{value:02X})"

def main():
    dbs_path = Path("C:/Users/marty/Documents/code/bane/gamedata/SCENARIO.DBS")

    with open(dbs_path, 'rb') as f:
        data = f.read()

    # Class ability flags table at 0x00A0B3 (14 classes × 16 bytes)
    CLASS_TABLE_OFFSET = 0x00A0B3

    print("=" * 100)
    print("WIZARDRY 6 CLASS SPELL LEVEL ACCESS")
    print("=" * 100)
    print("\nDecoded from SCENARIO.DBS offset 0x00A0B3 (Class Ability Flags Table)\n")

    # Header
    print(f"{'Class':<15s} {'Byte 0':<8s} {'Byte 6':<12s} {'Byte 14':<12s} {'Byte 15':<12s} {'Interpretation':<40s}")
    print("-" * 100)

    for i, class_name in enumerate(CLASSES):
        offset = CLASS_TABLE_OFFSET + (i * 16)
        record = data[offset:offset + 16]

        b0 = record[0]
        b6 = record[6]
        b14 = record[14]
        b15 = record[15]

        # Decode spell levels
        level_b0 = decode_spell_level(b0)
        level_b6 = decode_spell_level(b6)
        level_b14 = decode_spell_level(b14)
        level_b15 = decode_spell_level(b15)

        # Interpretation
        interp = ""
        if b6 > 0 and b14 > 0:
            interp = "Mage + Priest spells"
        elif b6 > 0:
            interp = "Mage spells"
        elif b14 > 0:
            interp = "Priest spells"
        elif b15 > 0:
            interp = "Elite Mage spells (limited)"
        elif b0 == 0x07:
            interp = "Psionic spells?"
        elif b0 == 0x01:
            interp = "Combat only"
        elif all(b == 0 for b in record):
            interp = "No spells, no equipment (pure martial)"
        else:
            interp = "Special abilities"

        print(f"{class_name:<15s} 0x{b0:02X}    {level_b6:<12s} {level_b14:<12s} {level_b15:<12s} {interp:<40s}")

    print("\n" + "=" * 100)
    print("DETAILED SPELL ACCESS BY CLASS")
    print("=" * 100)

    spell_access = {
        "Fighter": "No spells - pure combat class",
        "Mage": "Mage spells (byte 6: 0x50 = level 5 progression?)",
        "Priest": "Priest spells (byte 14: 0x77 = FULL level 7 access)",
        "Thief": "No spells - thieving skills only",
        "Ranger": "Alchemist spells (encoded elsewhere?)",
        "Alchemist": "Alchemist spells (bytes 14-15: 0x9B/0x07)",
        "Bard": "Mage spells + special music (byte 6: 0x92 special) + limited Priest? (byte 14: 0x70)",
        "Psionic": "Psionic spells (byte 0: 0x07 = level 7?)",
        "Valkyrie": "Priest spells (byte 14: 0x77 = FULL level 7 access) + fighter",
        "Bishop": "DUAL: Mage (byte 6: 0x07) + Priest (byte 14: 0x77 FULL)",
        "Lord": "Priest spells (byte 1: 0x07) + elite fighter",
        "Ninja": "Alchemist spells + thief + fighter (10 bytes set!)",
        "Monk": "NO SPELLS, NO EQUIPMENT - pure martial arts (all zeros)",
        "Samurai": "Mage spells LIMITED (byte 15: 0x50 = level 5 cap, SLOW progression)"
    }

    for class_name, access in spell_access.items():
        print(f"\n{class_name}:")
        print(f"  {access}")

    print("\n" + "=" * 100)
    print("KEY FINDINGS")
    print("=" * 100)
    print("\n1. BYTE 14 = PRIEST SPELL LEVEL")
    print("   - Priest, Valkyrie, Bishop: 0x77 (full level 7 access)")
    print("   - Bard: 0x70 (level 7, but different encoding)")
    print("\n2. BYTE 6 = MAGE SPELL LEVEL")
    print("   - Mage: 0x50 (level 5? or standard progression)")
    print("   - Bishop: 0x07 (level 7 via alternate encoding)")
    print("   - Bard: 0x92 (special - includes instrument magic?)")
    print("\n3. BYTE 15 = ELITE CLASS MAGE SPELL LEVEL")
    print("   - Samurai: 0x50 (limited to level 5, SLOW progression)")
    print("   - Confirmed by game guides: 'only tier 4 by level 13'")
    print("\n4. BISHOP IS DUAL-CASTER")
    print("   - Has flags at BOTH byte 6 (Mage) AND byte 14 (Priest)")
    print("   - Only class with access to both spell schools!")
    print("\n5. MONK HAS ZERO FLAGS")
    print("   - All 16 bytes are 0x00")
    print("   - Perfectly matches 'no equipment, no magic' lore")
    print("\n6. HYBRID CLASSES HAVE MOST FLAGS")
    print("   - Bard, Bishop, Ninja: 10 non-zero bytes each")
    print("   - Pure classes: 1 non-zero byte")
    print("   - Hybrid classes: 2-4 non-zero bytes")

if __name__ == "__main__":
    main()
