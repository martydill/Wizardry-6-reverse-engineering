#!/usr/bin/env python3
"""
Analyze potential race data in SCENARIO.DBS Graphic & Map Data section.
Attempt to decode race statistics based on known game mechanics.
"""
from pathlib import Path
import struct

RACES = ["Human", "Elf", "Dwarf", "Gnome", "Hobbit", "Faerie",
         "Lizardman", "Dracon", "Felpurr", "Rawulf", "Mook"]

STATS = ["STR", "INT", "PIE", "VIT", "DEX", "SPD", "PER/KAR"]

# Known facts from online sources:
KNOWN_RACE_INFO = {
    "Human": {"STR": 9, "INT": 8, "PIE": 8, "VIT": 9, "DEX": 8, "SPD": 8},
    "Elf": {"STR": 7, "INT": 10, "PIE": 10, "VIT": 7, "DEX": 9, "SPD": 8},
    "Dwarf": {"STR": 11, "INT": 6, "PIE": 10, "VIT": 12, "DEX": 7, "SPD": 7},
    "Gnome": {"STR": 10, "INT": 7, "PIE": 13, "VIT": 10, "DEX": 6, "SPD": 7},
    "Hobbit": {"STR": 8, "INT": 7, "PIE": 6, "VIT": 9, "DEX": 10, "SPD": 11},
}

def main():
    dbs_path = Path("C:/Users/marty/Documents/code/bane/gamedata/SCENARIO.DBS")

    with open(dbs_path, 'rb') as f:
        data = f.read()

    print("=" * 100)
    print("RACE DATA ANALYSIS - SCENARIO.DBS")
    print("=" * 100)

    # From earlier analysis, we found interesting patterns around 0x009508
    # Let's examine different possible table structures

    candidates = [
        (0x009409, 23, "First index block (23 bytes, 11 unique values)"),
        (0x009508, 11 * 10, "Potential 11 races × 10 bytes"),
        (0x009508, 11 * 11, "Potential 11 races × 11 bytes"),
        (0x009508, 11 * 12, "Potential 11 races × 12 bytes"),
        (0x009512, 11 * 14, "Potential 11 races × 14 bytes (7 stats × 2?)"),
        (0x009512, 11 * 16, "Potential 11 races × 16 bytes"),
    ]

    for offset, size, desc in candidates:
        print(f"\n{'='*100}")
        print(f"{desc} at 0x{offset:06X}")
        print(f"{'='*100}\n")

        block = data[offset:offset + size]

        # Try to find record size
        if "11 races" in desc:
            rec_size = size // 11
            print(f"Interpreting as 11 races × {rec_size} bytes per race\n")
            print(f"{'Race':<12s}", end='')
            for i in range(rec_size):
                print(f" {i:02d}", end='')
            print()
            print("-" * (12 + rec_size * 3))

            for i, race in enumerate(RACES):
                rec = block[i * rec_size:(i + 1) * rec_size]
                print(f"{race:<12s}", end='')
                for b in rec:
                    print(f" {b:02X}", end='')
                print(f"  | ", end='')
                # Show as decimal
                for b in rec:
                    print(f"{b:3d}", end='')
                print()

            # Try to correlate with known stats
            print(f"\n{'='*100}")
            print("CORRELATION ATTEMPT")
            print(f"{'='*100}\n")

            if rec_size >= 6:  # At least 6 bytes for 6+ stats
                print("Trying to match bytes to stats (STR, INT, PIE, VIT, DEX, SPD)...\n")

                for i, race in enumerate(RACES):
                    if race not in KNOWN_RACE_INFO:
                        continue

                    rec = block[i * rec_size:(i + 1) * rec_size]
                    known_stats = KNOWN_RACE_INFO[race]

                    print(f"{race}:")
                    print(f"  Known: STR={known_stats['STR']} INT={known_stats['INT']} PIE={known_stats['PIE']} VIT={known_stats['VIT']} DEX={known_stats['DEX']} SPD={known_stats['SPD']}")
                    print(f"  Bytes: {' '.join(f'{b:3d}' for b in rec[:12])}")

                    # Try to find matching pattern
                    matches = []
                    for byte_idx in range(rec_size - 5):
                        # Check if 6 consecutive bytes match the stats in order
                        if (rec[byte_idx] == known_stats['STR'] and
                            rec[byte_idx + 1] == known_stats['INT'] and
                            rec[byte_idx + 2] == known_stats['PIE'] and
                            rec[byte_idx + 3] == known_stats['VIT'] and
                            rec[byte_idx + 4] == known_stats['DEX'] and
                            rec[byte_idx + 5] == known_stats['SPD']):
                            matches.append(byte_idx)

                    if matches:
                        print(f"  ✅ MATCH at byte position(s): {matches}")
                    else:
                        # Try to find partial matches
                        partial_matches = []
                        for byte_idx in range(rec_size):
                            for stat_name, stat_val in known_stats.items():
                                if rec[byte_idx] == stat_val:
                                    partial_matches.append(f"byte[{byte_idx}]={stat_val} ({stat_name}?)")
                        if partial_matches:
                            print(f"  ⚠️  Partial matches: {', '.join(partial_matches[:6])}")
                    print()

        else:
            # Just show hex dump
            print("Hex dump:")
            for i in range(0, min(size, 256), 16):
                hex_str = ' '.join(f'{b:02X}' for b in block[i:i+16])
                ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in block[i:i+16])
                print(f"  {offset+i:06X}: {hex_str:<48s} {ascii_str}")

    # Special analysis: The 23-byte index block
    print(f"\n{'='*100}")
    print("SPECIAL: 23-byte index block analysis")
    print(f"{'='*100}\n")

    index_block = data[0x009409:0x009409 + 23]
    print("This block has exactly 11 unique values (matches race count!):")
    print(f"Raw bytes: {' '.join(f'{b:02X}' for b in index_block)}")
    print(f"As decimal: {' '.join(f'{b:2d}' for b in index_block)}")
    print(f"Unique values: {sorted(set(index_block))}")
    print(f"\nPossible interpretation: Race ID mapping or lookup table")

if __name__ == "__main__":
    main()
