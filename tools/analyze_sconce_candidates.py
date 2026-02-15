#!/usr/bin/env python3
"""
Analyze the most promising sconce candidates.
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
print('ANALYZING SCONCE CANDIDATES')
print('='*80)
print()

# Expected sconce positions (quadrant corners at center):
# (7, 7), (8, 7), (7, 8), (8, 8)

print('Expected sconce positions (2x2 square at map center):')
print('  (7, 7) - bottom-left quad corner')
print('  (8, 7) - bottom-right quad corner')
print('  (7, 8) - top-left quad corner')
print('  (8, 8) - top-right quad corner')
print()

# Top candidates based on file column distribution
candidates = [
    (0, 0xA0, "byte 0 = 0xA0", [65, 69, 72, 136]),  # Cols 4,4,4,8
]

print('='*80)
print('TOP CANDIDATE: Byte 0 = 0xA0')
print('='*80)
print()

candidate_cells = [65, 69, 72, 136]

for cell_idx in candidate_cells:
    file_col = cell_idx // 16
    file_row = cell_idx % 16
    cell = cells[cell_idx]

    print(f'Cell {cell_idx:3d}: file_col={file_col:2d}, file_row={file_row:2d}')
    print(f'  Even bytes: {" ".join(f"{cell[i]:02X}" for i in range(0, 20, 2))}')
    print(f'  Odd bytes:  {" ".join(f"{cell[i]:02X}" for i in range(1, 20, 2))}')
    print()

# Check file column distribution
file_cols = [c // 16 for c in candidate_cells]
file_rows = [c % 16 for c in candidate_cells]

print(f'File column distribution: {sorted(set(file_cols))}')
print(f'File row distribution: {sorted(set(file_rows))}')
print()

# Cell 136 is particularly interesting (col=8, row=8 - exactly center of file!)
print('='*80)
print('SPECIAL ATTENTION: Cell 136 (file_col=8, file_row=8)')
print('='*80)
print()
print('This cell is at the EXACT CENTER of the file coordinates!')
print('If quadrants meet at the map center, this is a key position.')
print()

# Now let's look for OTHER byte positions that might mark sconces
# Check if there's a pattern across multiple bytes

print('='*80)
print('COMPARING SCONCE CANDIDATE CELLS:')
print('='*80)
print()

print('Looking for common byte patterns across all 4 candidates...')
print()

# Check each even byte
for byte_idx in range(0, 20, 2):
    values = [cells[c][byte_idx] for c in candidate_cells]
    non_zero = [v for v in values if v != 0]

    if len(non_zero) >= 3:  # At least 3 have non-zero
        print(f'Byte {byte_idx:2d}: {" ".join(f"0x{v:02X}" for v in values)}')
        if len(set(non_zero)) == 1:
            print(f'  >>> All non-zero values are 0x{non_zero[0]:02X}!')

print()
print('='*80)
print('MAPPING TO GAME COORDINATES:')
print('='*80)
print()

# If we assume these are the sconces, can we derive the mapping?
print('If cells 65, 69, 72, 136 are the 4 sconces at (7,7), (8,7), (7,8), (8,8):')
print()

test_mappings = [
    ((65, 4, 1), (7, 7)),
    ((69, 4, 5), (8, 7)),
    ((72, 4, 8), (7, 8)),
    ((136, 8, 8), (8, 8)),
]

for (cell_idx, file_col, file_row), (game_x, game_y) in test_mappings:
    print(f'Cell {cell_idx:3d} (file col={file_col:2d}, row={file_row:2d}) -> game ({game_x:2d}, {game_y:2d})')

print()
print('Can we find a formula?')
print()

# Try to find pattern
for (cell_idx, file_col, file_row), (game_x, game_y) in test_mappings:
    print(f'Cell {cell_idx:3d}:')
    print(f'  file_col={file_col:2d} -> game_x={game_x:2d} (diff={game_x - file_col:+3d})')
    print(f'  file_row={file_row:2d} -> game_y={game_y:2d} (diff={game_y - file_row:+3d})')
