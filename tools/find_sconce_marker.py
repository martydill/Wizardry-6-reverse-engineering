#!/usr/bin/env python3
"""
Find the sconce marker - should appear exactly 4 times at quadrant corners.
"""

from pathlib import Path

filepath = Path("gamedata/SCENARIO.DBS")
offset = 40960

with open(filepath, 'rb') as f:
    f.seek(offset)
    data = f.read(16 * 16 * 20)

cells = []
for i in range(256):
    cells.append(data[i*20:(i+1)*20])

print('='*80)
print('SCANNING FOR SCONCE MARKER (new feature added at quadrant corners)')
print('='*80)
print()

# For each byte position, count value occurrences
print('Looking for byte values appearing exactly 4 times (new additions)...')
print()

# Track all byte+value combinations and their cell locations
byte_value_locs = {}

for cell_idx in range(256):
    file_col = cell_idx // 16
    file_row = cell_idx % 16
    cell = cells[cell_idx]

    for byte_idx in range(20):
        val = cell[byte_idx]
        if val != 0:
            key = (byte_idx, val)
            if key not in byte_value_locs:
                byte_value_locs[key] = []
            byte_value_locs[key].append((cell_idx, file_row, file_col))

# Find combinations with exactly 4 occurrences
candidates = [(k, v) for k, v in byte_value_locs.items() if len(v) == 4]

# We already know byte 18 = 0xA0 is fountains (4 occurrences)
# So exclude that and look for NEW 4-occurrence patterns

print(f'Found {len(candidates)} byte+value combinations with exactly 4 occurrences')
print()

fountain_marker = (18, 0xA0)

for (byte_idx, val), locs in sorted(candidates):
    if (byte_idx, val) == fountain_marker:
        continue  # Skip known fountain marker

    print(f'Byte {byte_idx:2d}, value 0x{val:02X}:')

    file_cols = [loc[2] for loc in locs]
    file_rows = [loc[1] for loc in locs]

    print(f'  File columns: {sorted(set(file_cols))}')
    print(f'  File rows: {sorted(set(file_rows))}')

    for cell_idx, file_row, file_col in locs:
        print(f'    Cell {cell_idx:3d}: file_col={file_col:2d}, file_row={file_row:2d}')

    # Show full even bytes for these cells
    print(f'  Cell data (even bytes):')
    for cell_idx, file_row, file_col in locs:
        cell = cells[cell_idx]
        even = ' '.join(f'{cell[i]:02X}' for i in range(0, 20, 2))
        print(f'    Cell {cell_idx:3d}: {even}')

    print()

print('='*80)
print('CROSS-REFERENCE: Compare with fountain positions')
print('='*80)
print()

print('Fountain positions (byte 18 = 0xA0):')
for cell_idx, file_row, file_col in byte_value_locs[fountain_marker]:
    print(f'  Cell {cell_idx:3d}: file_col={file_col:2d}, file_row={file_row:2d}')

print()
print('Expected sconce positions (quadrant corners at map center):')
print('  - (7, 7) - bottom-left quad corner')
print('  - (8, 7) - bottom-right quad corner')
print('  - (7, 8) - top-left quad corner')
print('  - (8, 8) - top-right quad corner')
print()
print('These 4 positions form a 2x2 square at the map center.')
