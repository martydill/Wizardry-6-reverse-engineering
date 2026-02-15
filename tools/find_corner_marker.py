#!/usr/bin/env python3
"""
Find the fountain marker in edge columns only.
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

print('Even bytes with values appearing exactly 4 times in edge columns (0 and 15):')
print('='*70)
print()

for byte_idx in range(0, 20, 2):
    # Count value occurrences in columns 0 and 15
    col_0_values = {}
    col_15_values = {}

    # Column 0: cells 0-15
    for row in range(16):
        val = cells[row][byte_idx]
        if val != 0:
            col_0_values[val] = col_0_values.get(val, 0) + 1

    # Column 15: cells 240-255
    for row in range(16):
        cell_idx = 15 * 16 + row
        val = cells[cell_idx][byte_idx]
        if val != 0:
            col_15_values[val] = col_15_values.get(val, 0) + 1

    # Find values that appear in both columns with total count <= 4
    all_values = set(col_0_values.keys()) | set(col_15_values.keys())

    for val in sorted(all_values):
        count_0 = col_0_values.get(val, 0)
        count_15 = col_15_values.get(val, 0)
        total = count_0 + count_15

        if total == 4 and count_0 >= 1 and count_15 >= 1:
            print(f'Byte {byte_idx:2d}, value 0x{val:02X}: {count_0} in col-0 + {count_15} in col-15 = 4 total')

            # Show which rows
            rows_0 = [r for r in range(16) if cells[r][byte_idx] == val]
            rows_15 = [r for r in range(16) if cells[15*16+r][byte_idx] == val]

            print(f'  Col-0 rows: {rows_0}')
            print(f'  Col-15 rows: {rows_15}')

            # If 2+2, this is very likely the fountain marker!
            if count_0 == 2 and count_15 == 2:
                print('  >>> PERFECT! 2 corners in each column!')

                # Show full data for these 4 cells
                print()
                for row in rows_0:
                    cell_idx = row
                    cell = cells[cell_idx]
                    print(f'    Cell {cell_idx:3d} (col=0, row={row:2d}):')
                    print(f'      Even: {" ".join(f"{cell[i]:02X}" for i in range(0, 20, 2))}')

                for row in rows_15:
                    cell_idx = 15 * 16 + row
                    cell = cells[cell_idx]
                    print(f'    Cell {cell_idx:3d} (col=15, row={row:2d}):')
                    print(f'      Even: {" ".join(f"{cell[i]:02X}" for i in range(0, 20, 2))}')

            print()
