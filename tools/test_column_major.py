#!/usr/bin/env python3
"""
Test if the map data is stored in column-major order.
"""

import sys
from pathlib import Path

def read_file(filepath):
    with open(filepath, 'rb') as f:
        return f.read()

def main():
    file_new = Path("gamedata/newgame.dbs")
    file_old = Path("gamedata/newgameold.dbs")

    data_new = read_file(file_new)
    data_old = read_file(file_old)

    # Find all differences
    diffs = []
    for i in range(min(len(data_new), len(data_old))):
        if data_new[i] != data_old[i]:
            diffs.append(i)

    print("Testing COLUMN-MAJOR storage hypothesis")
    print("="*80)
    print()

    # Test different cell sizes
    for bytes_per_cell in [10, 20]:
        print(f"\nTesting with {bytes_per_cell} bytes per cell:")
        print("-"*80)

        # Get affected cells
        cells = sorted(set(offset // bytes_per_cell for offset in diffs))
        print(f"Affected cells: {cells}")
        print()

        # Try column-major interpretation (cells go down columns)
        print(f"COLUMN-MAJOR interpretation (cells = [col0: rows 0-19, col1: rows 0-19, ...]):")

        for grid_height in [20]:
            print(f"  Grid height {grid_height}:")

            by_column = {}
            by_row = {}

            for cell_idx in cells:
                col = cell_idx // grid_height
                row = cell_idx % grid_height

                if col not in by_column:
                    by_column[col] = []
                by_column[col].append(row)

                if row not in by_row:
                    by_row[row] = []
                by_row[row].append(col)

            print(f"    Cells by column:")
            for col in sorted(by_column.keys()):
                rows = sorted(by_column[col])
                print(f"      Column {col:2d}: rows {rows}")

            print(f"    Cells by row:")
            for row in sorted(by_row.keys()):
                cols = sorted(by_row[row])
                print(f"      Row {row:2d}: columns {cols}")

            # Check if all in one column
            if len(by_column) == 1:
                col = list(by_column.keys())[0]
                rows = sorted(by_column[col])
                print(f"    *** ALL IN COLUMN {col}! Rows: {min(rows)}-{max(rows)} ***")
                print(f"    This matches: Horizontal walls in column {col}!")

        print()

        # Try row-major interpretation (cells go across rows)
        print(f"ROW-MAJOR interpretation (cells = [row0: cols 0-19, row1: cols 0-19, ...]):")

        for grid_width in [20]:
            print(f"  Grid width {grid_width}:")

            by_row = {}
            by_column = {}

            for cell_idx in cells:
                row = cell_idx // grid_width
                col = cell_idx % grid_width

                if row not in by_row:
                    by_row[row] = []
                by_row[row].append(col)

                if col not in by_column:
                    by_column[col] = []
                by_column[col].append(row)

            print(f"    Cells by row:")
            for row in sorted(by_row.keys()):
                cols = sorted(by_row[row])
                print(f"      Row {row:2d}: columns {cols}")

            print(f"    Cells by column:")
            for col in sorted(by_column.keys()):
                rows = sorted(by_column[col])
                print(f"      Column {col:2d}: rows {rows}")

            # Check if all in one row
            if len(by_row) == 1:
                row = list(by_row.keys())[0]
                cols = sorted(by_row[row])
                print(f"    *** ALL IN ROW {row}! Columns: {min(cols)}-{max(cols)} ***")

        print()

if __name__ == "__main__":
    main()
