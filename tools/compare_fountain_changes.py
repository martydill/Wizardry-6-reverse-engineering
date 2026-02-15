#!/usr/bin/env python3
"""
Compare original and modified NEWGAME.DBS to identify fountain encoding.
Map 10 is 16x16, fountains added to all 4 corners.
"""

def find_differences(file1_path, file2_path):
    """Find all byte differences between two files."""
    with open(file1_path, 'rb') as f1, open(file2_path, 'rb') as f2:
        data1 = f1.read()
        data2 = f2.read()

    if len(data1) != len(data2):
        print(f"WARNING: File sizes differ: {len(data1)} vs {len(data2)}")
        return []

    differences = []
    for offset in range(len(data1)):
        if data1[offset] != data2[offset]:
            differences.append({
                'offset': offset,
                'old': data1[offset],
                'new': data2[offset],
                'old_hex': f"0x{data1[offset]:02X}",
                'new_hex': f"0x{data2[offset]:02X}"
            })

    return differences

def find_map10_location(data):
    """
    Try to find Map 10 in NEWGAME.DBS.
    We know from SCENARIO.DBS it's at 0xA000, but might differ.
    16x16 map = 256 cells * 20 bytes = 5120 bytes
    """
    # Known patterns from memory:
    # - Maps use column-major storage
    # - 20 bytes per cell
    # - Odd bytes (1,3,5..19) contain wall data

    # Look for sequences that might be map data
    # Map 10 in SCENARIO.DBS starts at 0xA000 = 40960
    print(f"File size: {len(data)} bytes")
    print(f"Checking offset 0xA000 (40960)...")

    # Map 10 is 16x16 = 256 cells * 20 bytes = 5120 bytes
    if len(data) >= 40960 + 5120:
        return 40960

    # If not found, scan for likely map data
    print("Scanning file for map data patterns...")
    return None

def analyze_changes_by_region(differences, map10_offset=None):
    """Group differences by file region."""
    if not differences:
        print("No differences found!")
        return

    print(f"\n{'='*80}")
    print(f"TOTAL DIFFERENCES: {len(differences)} bytes changed")
    print(f"{'='*80}\n")

    # Show all differences with context
    for i, diff in enumerate(differences):
        offset = diff['offset']

        # Calculate map position if in map 10 region
        map_info = ""
        if map10_offset and offset >= map10_offset:
            rel_offset = offset - map10_offset
            if rel_offset < 5120:  # 16x16 * 20 bytes
                cell_index = rel_offset // 20
                byte_in_cell = rel_offset % 20
                file_col = cell_index // 16  # 16 rows per column
                file_row = cell_index % 16

                map_info = f" [Map10 Cell({file_col},{file_row}) Byte {byte_in_cell}]"

        print(f"{i+1}. Offset 0x{offset:08X} ({offset:6d}): "
              f"{diff['old_hex']} -> {diff['new_hex']} "
              f"({diff['old']:3d} -> {diff['new']:3d}){map_info}")

    # Group by byte position within cells (for map data)
    if map10_offset:
        print(f"\n{'='*80}")
        print("GROUPING BY BYTE POSITION IN CELL:")
        print(f"{'='*80}\n")

        byte_positions = {}
        for diff in differences:
            offset = diff['offset']
            if offset >= map10_offset and offset < map10_offset + 5120:
                rel_offset = offset - map10_offset
                byte_in_cell = rel_offset % 20

                if byte_in_cell not in byte_positions:
                    byte_positions[byte_in_cell] = []

                cell_index = rel_offset // 20
                file_col = cell_index // 16
                file_row = cell_index % 16

                byte_positions[byte_in_cell].append({
                    'col': file_col,
                    'row': file_row,
                    'old': diff['old'],
                    'new': diff['new']
                })

        for byte_pos in sorted(byte_positions.keys()):
            changes = byte_positions[byte_pos]
            print(f"\nByte {byte_pos}: {len(changes)} cells changed")
            for change in changes:
                print(f"  Cell({change['col']:2d},{change['row']:2d}): "
                      f"0x{change['old']:02X} -> 0x{change['new']:02X}")

def main():
    original = 'gamedata/NEWGAME0.DBS'
    modified = 'gamedata/NEWGAME.DBS'

    print("Comparing NEWGAME.DBS files to identify fountain encoding...")
    print(f"Original: {original}")
    print(f"Modified: {modified}")
    print()

    differences = find_differences(original, modified)

    # Try to locate Map 10
    with open(modified, 'rb') as f:
        data = f.read()

    map10_offset = find_map10_location(data)

    if map10_offset:
        print(f"Map 10 found at offset 0x{map10_offset:08X}")
    else:
        print("Map 10 location unknown - showing raw differences")

    analyze_changes_by_region(differences, map10_offset)

    # Corner analysis
    if map10_offset and differences:
        print(f"\n{'='*80}")
        print("CORNER CELL ANALYSIS:")
        print(f"{'='*80}\n")
        print("Corners of 16x16 map:")
        print("  (0,0)   = Top-Left")
        print("  (15,0)  = Top-Right")
        print("  (0,15)  = Bottom-Left")
        print("  (15,15) = Bottom-Right")
        print("\nIn column-major storage:")
        print("  Cell index = (file_col * 16) + file_row")

        corners = {
            'Top-Left (0,0)': (0, 0),
            'Top-Right (15,0)': (15, 0),
            'Bottom-Left (0,15)': (0, 15),
            'Bottom-Right (15,15)': (15, 15)
        }

        for corner_name, (x, y) in corners.items():
            cell_index = x * 16 + y
            cell_offset = map10_offset + (cell_index * 20)
            print(f"\n{corner_name}: Cell {cell_index}, Offset 0x{cell_offset:08X}")

            # Show which bytes changed in this cell
            cell_changes = [d for d in differences
                          if cell_offset <= d['offset'] < cell_offset + 20]

            if cell_changes:
                print(f"  {len(cell_changes)} bytes changed in this cell:")
                for change in cell_changes:
                    byte_pos = change['offset'] - cell_offset
                    print(f"    Byte {byte_pos:2d}: 0x{change['old']:02X} -> 0x{change['new']:02X}")
            else:
                print("  No changes in this cell")

if __name__ == '__main__':
    main()
