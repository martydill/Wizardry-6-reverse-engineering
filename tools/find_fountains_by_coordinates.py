#!/usr/bin/env python3
"""
Find fountains at known global coordinates: (0,0), (15,0), (0,15), (15,15).
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
print('FOUNTAIN LOCATIONS (based on quadrant coordinates):')
print('='*80)
print()

# Fountains at global (0,0), (15,0), (0,15), (15,15)
# With file_col = game_col, need to find file_row for each game_row

fountains = [
    ("Bottom-left", 0, 0),   # Quad 8 (0,0)
    ("Bottom-right", 15, 0), # Quad 9 (7,0)
    ("Top-left", 0, 15),     # Quad 10 (0,7)
    ("Top-right", 15, 15),   # Quad 11 (7,7)
]

print("Searching for fountain markers in files...")
print()

# For each fountain position (assuming file_col = game_col)
# We need to find which file_row stores game_row data

for name, game_col, game_row in fountains:
    print(f"{name} corner: game position ({game_col}, {game_row})")
    print(f"  File column (assumed): {game_col}")
    print(f"  Looking for file_row that stores game_row={game_row}...")
    print()

    # Check all file rows in this column for unusual data
    file_col = game_col

    candidates = []
    for file_row in range(16):
        cell_idx = file_col * 16 + file_row
        cell = cells[cell_idx]

        # Count non-zero even bytes (potential feature marker)
        non_zero_even = sum(1 for i in range(0, 20, 2) if cell[i] != 0)
        even_sum = sum(cell[i] for i in range(0, 20, 2) if cell[i] != 0)

        if non_zero_even >= 3:
            candidates.append((file_row, non_zero_even, even_sum, cell))

    print(f"  Candidate file rows with data:")
    for file_row, count, esum, cell in candidates:
        print(f"    Row {file_row:2d}: {count} non-zero even bytes, sum={esum:4d}")

    print()

print('='*80)
print('CROSS-REFERENCE: Find common byte values across all 4 fountains')
print('='*80)
print()

# Strategy: Find a byte+value combination that appears in exactly 4 cells
# AND those 4 cells are in columns 0 or 15

print("Scanning for byte values appearing exactly 4 times...")
print()

# Count all byte+value combinations
byte_value_counts = {}
for cell_idx in range(256):
    file_col = cell_idx // 16
    file_row = cell_idx % 16

    # Only check edge columns
    if file_col not in [0, 15]:
        continue

    cell = cells[cell_idx]

    for byte_idx in range(0, 20, 2):  # Even bytes only
        val = cell[byte_idx]
        if val != 0:
            key = (byte_idx, val)
            if key not in byte_value_counts:
                byte_value_counts[key] = []
            byte_value_counts[key].append((cell_idx, file_row, file_col))

# Find entries with exactly 4 occurrences
candidates_4 = [(k, v) for k, v in byte_value_counts.items() if len(v) == 4]

print(f"Found {len(candidates_4)} byte+value combinations appearing exactly 4 times")
print()

for (byte_idx, val), cells_list in candidates_4[:20]:  # Show first 20
    cols = [c[2] for c in cells_list]
    rows = [c[1] for c in cells_list]

    # Check if it's in both columns
    if 0 in cols and 15 in cols:
        count_0 = cols.count(0)
        count_15 = cols.count(15)

        print(f"Byte {byte_idx:2d}, value 0x{val:02X}:")
        print(f"  {count_0} in col-0, {count_15} in col-15")

        for cell_idx, file_row, file_col in cells_list:
            print(f"    Cell {cell_idx:3d}: file_col={file_col:2d}, file_row={file_row:2d}")

        # Show the actual cell data
        print(f"  Cell data:")
        for cell_idx, file_row, file_col in cells_list:
            cell = cells[cell_idx]
            print(f"    Cell {cell_idx:3d}: Even bytes = {' '.join(f'{cell[i]:02X}' for i in range(0, 20, 2))}")

        print()
