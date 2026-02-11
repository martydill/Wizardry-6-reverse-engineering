#!/usr/bin/env python3
"""
Identify specific data structures in the Graphic & Map Data section.
Focus on: Race/Class tables, Map data, Tile graphics
"""
import struct
from pathlib import Path

def u8(buf, off):  return buf[off]
def u16(buf, off): return struct.unpack_from('<H', buf, off)[0]
def u32(buf, off): return struct.unpack_from('<I', buf, off)[0]

# Known constants from the game
RACES = ["Human", "Elf", "Dwarf", "Gnome", "Hobbit", "Faerie", "Lizardman", "Dracon", "Felpurr", "Rawulf", "Mook"]
CLASSES = ["Fighter", "Mage", "Priest", "Thief", "Ranger", "Alchemist", "Bard", "Psionic", "Valkyrie", "Bishop", "Lord", "Ninja", "Monk", "Samurai"]
STATS = ["STR", "INT", "PIE", "VIT", "DEX", "SPD", "KAR"]

# Section boundaries
GFX_START = 0x9409
GFX_END = 0x154E6

def analyze_race_class_tables(data):
    """Look for race/class attribute tables."""
    print("\n" + "=" * 80)
    print("SEARCHING FOR RACE/CLASS TABLES")
    print("=" * 80)

    section = data[GFX_START:GFX_END]

    # Race table: 11 races × N attributes
    # Class table: 14 classes × N attributes

    # Look for blocks that are divisible by 11 or 14
    candidates = []

    for offset in range(0, len(section) - 100):
        # Try different record sizes
        for rec_size in range(4, 50):
            # Check if we have exactly 11 or 14 records
            for count in [11, 14]:
                total_size = count * rec_size
                if offset + total_size > len(section):
                    continue

                block = section[offset:offset + total_size]

                # Skip if too many zeros (likely padding)
                non_zero = sum(1 for b in block if b != 0)
                if non_zero < total_size * 0.3:
                    continue

                # Check if values look like stats (1-30 range is common for initial stats)
                reasonable_values = sum(1 for b in block if 1 <= b <= 100)
                if reasonable_values > total_size * 0.5:
                    candidates.append({
                        'offset': GFX_START + offset,
                        'rec_size': rec_size,
                        'count': count,
                        'type': 'RACE' if count == 11 else 'CLASS',
                        'data': block
                    })

    # Deduplicate overlapping candidates
    seen = set()
    unique = []
    for c in candidates:
        key = (c['offset'], c['rec_size'], c['count'])
        if key not in seen:
            seen.add(key)
            unique.append(c)

    print(f"\nFound {len(unique)} potential race/class tables:\n")

    for i, cand in enumerate(unique[:20]):  # Show first 20
        print(f"Candidate {i+1}:")
        print(f"  Offset: 0x{cand['offset']:06X}")
        print(f"  Type: {cand['type']} table ({cand['count']} entries × {cand['rec_size']} bytes)")

        # Show the table
        d = cand['data']
        print(f"  Data:")
        for row in range(cand['count']):
            off = row * cand['rec_size']
            rec = d[off:off + cand['rec_size']]
            hex_str = ' '.join(f'{b:02X}' for b in rec)
            label = RACES[row] if cand['type'] == 'RACE' and row < len(RACES) else CLASSES[row] if cand['type'] == 'CLASS' and row < len(CLASSES) else f"#{row}"
            print(f"    {label:12s}: {hex_str}")
        print()

def analyze_tile_data(data):
    """Look for 4-bit planar tile data (8x8 tiles = 32 bytes each)."""
    print("\n" + "=" * 80)
    print("SEARCHING FOR TILE GRAPHICS")
    print("=" * 80)

    section = data[GFX_START:GFX_END]

    # Look for blocks that are multiples of 32 bytes and contain 4-bit data
    candidates = []

    for offset in range(0, len(section) - 320, 32):
        block = section[offset:offset + 320]  # 10 tiles

        # Check if it looks like 4-bit planar data
        # In planar format, we often see patterns in each plane
        low_nibble = sum(1 for b in block if b < 16)
        if low_nibble < len(block) * 0.8:  # At least 80% low values
            continue

        # Check for non-uniform data (not all zeros or all same value)
        unique_bytes = len(set(block))
        if unique_bytes < 4:
            continue

        candidates.append({
            'offset': GFX_START + offset,
            'size': 320,
            'tiles': 10
        })

        if len(candidates) >= 10:
            break

    print(f"\nFound {len(candidates)} potential tile blocks:\n")

    for i, cand in enumerate(candidates[:5]):
        print(f"Tile Block {i+1}:")
        print(f"  Offset: 0x{cand['offset']:06X}")
        print(f"  Size: {cand['size']} bytes ({cand['tiles']} tiles)")
        print()

def analyze_map_structure(data):
    """Look for map/dungeon data structures."""
    print("\n" + "=" * 80)
    print("SEARCHING FOR MAP DATA")
    print("=" * 80)

    section = data[GFX_START:GFX_END]

    # Maps in Wizardry are typically grid-based
    # Common sizes: 20×20, 28×28, 32×32
    # Each cell might be 1-4 bytes

    # Look for repeating patterns that might indicate map tiles
    print("\nLooking for repeating byte patterns (wall/floor types)...")

    # Count byte frequency in different parts of the section
    for start in [0, 0x1000, 0x2000, 0x4000, 0x8000]:
        if start >= len(section):
            continue

        chunk = section[start:start + 1000]
        freq = {}
        for b in chunk:
            freq[b] = freq.get(b, 0) + 1

        # Show most common bytes
        sorted_freq = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        print(f"\n  At offset 0x{GFX_START + start:06X}:")
        print(f"    Top 10 bytes: ", end="")
        for val, count in sorted_freq[:10]:
            print(f"{val:02X}({count}) ", end="")
        print()

def main():
    dbs_path = Path("C:/Users/marty/Documents/code/bane/gamedata/SCENARIO.DBS")

    with open(dbs_path, 'rb') as f:
        data = f.read()

    analyze_race_class_tables(data)
    analyze_tile_data(data)
    analyze_map_structure(data)

if __name__ == "__main__":
    main()
