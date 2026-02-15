#!/usr/bin/env python3
"""
Show all cells in columns 0 and 15 to visually identify fountains.
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
print('ALL CELLS IN FILE COLUMN 0 (LEFT EDGE):')
print('='*80)
print()

for row in range(16):
    cell_idx = row
    cell = cells[cell_idx]

    # Calculate data "signature" - sum of non-zero even bytes
    even_sum = sum(cell[i] for i in range(0, 20, 2) if cell[i] != 0)

    print(f'File row {row:2d} (cell {cell_idx:3d}) - Even byte sum: {even_sum:4d}')
    print(f'  Even bytes: {" ".join(f"{cell[i]:02X}" for i in range(0, 20, 2))}')
    print(f'  Odd bytes:  {" ".join(f"{cell[i]:02X}" for i in range(1, 20, 2))}')
    print()

print('='*80)
print('ALL CELLS IN FILE COLUMN 15 (RIGHT EDGE):')
print('='*80)
print()

for row in range(16):
    cell_idx = 15 * 16 + row
    cell = cells[cell_idx]

    # Calculate data "signature"
    even_sum = sum(cell[i] for i in range(0, 20, 2) if cell[i] != 0)

    print(f'File row {row:2d} (cell {cell_idx:3d}) - Even byte sum: {even_sum:4d}')
    print(f'  Even bytes: {" ".join(f"{cell[i]:02X}" for i in range(0, 20, 2))}')
    print(f'  Odd bytes:  {" ".join(f"{cell[i]:02X}" for i in range(1, 20, 2))}')
    print()

print('='*80)
print('ANALYSIS: Looking for 4 cells with similar even-byte patterns')
print('='*80)
print()

# Calculate similarity by checking if cells have uncommon byte values
all_cells = []
for col in [0, 15]:
    for row in range(16):
        cell_idx = col * 16 + row if col == 15 else row
        cell = cells[cell_idx]
        even_sum = sum(cell[i] for i in range(0, 20, 2) if cell[i] != 0)
        all_cells.append((col, row, cell_idx, even_sum, cell))

# Sort by even_sum to group similar cells
all_cells.sort(key=lambda x: x[3], reverse=True)

print('Top 10 cells by even-byte activity:')
for i, (col, row, idx, esum, cell) in enumerate(all_cells[:10]):
    print(f'{i+1}. Cell {idx:3d} (col={col:2d}, row={row:2d}): sum={esum:4d}')
print()

print('Cells with moderate even-byte activity (may indicate special features):')
moderate = [c for c in all_cells if 100 <= c[3] <= 500]
for col, row, idx, esum, cell in moderate:
    print(f'  Cell {idx:3d} (col={col:2d}, row={row:2d}): sum={esum:4d}')
