#!/usr/bin/env python3
"""
Test different wall bit interpretations to find the correct one.
"""

import sys
from pathlib import Path

def read_map_data(filepath):
    """Read map cell data."""
    with open(filepath, 'rb') as f:
        data = f.read(400 * 8)

    cells = []
    for i in range(400):
        cell_data = data[i*8:(i+1)*8]
        cells.append(cell_data if len(cell_data) == 8 else bytes([0] * 8))

    return cells

def show_changed_cells(cells_old, cells_new):
    """Show which cells changed."""
    print("\nCells that changed:")
    print("="*70)

    changes = []
    for i in range(400):
        if cells_old[i] != cells_new[i]:
            row = i // 20
            col = i % 20
            changes.append((row, col, i))

    for row, col, idx in changes:
        print(f"\nCell ({row},{col}) = index {idx}:")
        print(f"  Old: {' '.join(f'{b:02X}' for b in cells_new[idx])}")
        print(f"  New: {' '.join(f'{b:02X}' for b in cells_old[idx])}")

        # Show what changed
        for byte_idx in range(8):
            if cells_old[idx][byte_idx] != cells_new[idx][byte_idx]:
                old = cells_new[idx][byte_idx]
                new = cells_old[idx][byte_idx]
                print(f"  Byte {byte_idx}: 0x{old:02X} -> 0x{new:02X} (binary: {old:08b} -> {new:08b})")

def test_interpretation(cells, interp_name, get_walls_func):
    """Test a wall interpretation."""
    print(f"\n{'='*70}")
    print(f"Testing interpretation: {interp_name}")
    print('='*70)

    # Focus on the changed cells
    test_cells = [(3, 15), (4, 19)]

    for row, col in test_cells:
        cell_idx = row * 20 + col
        cell_data = cells[cell_idx]
        walls = get_walls_func(cell_data)

        wall_str = []
        if walls['N']: wall_str.append('North')
        if walls['S']: wall_str.append('South')
        if walls['E']: wall_str.append('East')
        if walls['W']: wall_str.append('West')

        print(f"\nCell ({row},{col}):")
        print(f"  Bytes: {' '.join(f'{b:02X}' for b in cell_data)}")
        print(f"  Byte 3: 0x{cell_data[3]:02X} = {cell_data[3]:08b}")
        print(f"  Byte 5: 0x{cell_data[5]:02X} = {cell_data[5]:08b}")
        print(f"  Walls detected: {', '.join(wall_str) if wall_str else 'None'}")
        print(f"  Wall count: {len(wall_str)}")

# Different interpretation functions
def interp_v1(cell_data):
    """Current interpretation: byte 3 bit 7=N, bit 6=S, byte 5 bit 7=E, bit 5=W"""
    return {
        'N': bool(cell_data[3] & 0x80),
        'S': bool(cell_data[3] & 0x40),
        'E': bool(cell_data[5] & 0x80),
        'W': bool(cell_data[5] & 0x20),
    }

def interp_v2(cell_data):
    """Byte 5 encodes all 4 walls in one byte using 4 bits"""
    b5 = cell_data[5]
    return {
        'N': bool(b5 & 0x80),  # bit 7
        'S': bool(b5 & 0x40),  # bit 6
        'E': bool(b5 & 0x20),  # bit 5
        'W': bool(b5 & 0x10),  # bit 4
    }

def interp_v3(cell_data):
    """Byte 3 encodes all 4 walls"""
    b3 = cell_data[3]
    return {
        'N': bool(b3 & 0x80),
        'S': bool(b3 & 0x40),
        'E': bool(b3 & 0x20),
        'W': bool(b3 & 0x10),
    }

def interp_v4(cell_data):
    """Both bytes together, different bit assignments"""
    b3, b5 = cell_data[3], cell_data[5]
    return {
        'N': bool(b3 & 0x80) or bool(b5 & 0x80),
        'S': bool(b3 & 0x40) or bool(b5 & 0x40),
        'E': bool(b3 & 0x20) or bool(b5 & 0x20),
        'W': bool(b3 & 0x10) or bool(b5 & 0x10),
    }

def interp_v5(cell_data):
    """Byte 5 low nibble for walls"""
    b5 = cell_data[5]
    return {
        'N': bool(b5 & 0x08),  # bit 3
        'S': bool(b5 & 0x04),  # bit 2
        'E': bool(b5 & 0x02),  # bit 1
        'W': bool(b5 & 0x01),  # bit 0
    }

def interp_v6(cell_data):
    """Byte 3 and 5 high nibbles"""
    b3, b5 = cell_data[3], cell_data[5]
    return {
        'N': bool(b3 & 0x80),  # byte 3 bit 7
        'S': bool(b3 & 0x40),  # byte 3 bit 6
        'E': bool(b5 & 0x80),  # byte 5 bit 7
        'W': bool(b5 & 0x40),  # byte 5 bit 6 (not bit 5!)
    }

def interp_v7(cell_data):
    """Nibble-based: high nibble of byte 5"""
    b5 = cell_data[5]
    high_nibble = (b5 >> 4) & 0x0F
    # 0xA = 1010 in binary
    return {
        'N': bool(high_nibble & 0x08),  # bit 3 of nibble
        'S': bool(high_nibble & 0x04),  # bit 2 of nibble
        'E': bool(high_nibble & 0x02),  # bit 1 of nibble
        'W': bool(high_nibble & 0x01),  # bit 0 of nibble
    }

def main():
    file_old = Path("gamedata/newgameold.dbs")
    file_new = Path("gamedata/newgame.dbs")

    if not file_old.exists() or not file_new.exists():
        print("Error: Files not found")
        sys.exit(1)

    print("Analyzing wall bit encoding...")
    print("="*70)

    cells_old = read_map_data(file_old)
    cells_new = read_map_data(file_new)

    show_changed_cells(cells_old, cells_new)

    print("\n" + "="*70)
    print("TESTING DIFFERENT BIT INTERPRETATIONS")
    print("="*70)
    print("\nLooking for interpretation where ONE cell has ALL 4 walls")

    interpretations = [
        ("v1: Current (b3.7=N, b3.6=S, b5.7=E, b5.5=W)", interp_v1),
        ("v2: Byte 5 only (bits 7,6,5,4 = N,S,E,W)", interp_v2),
        ("v3: Byte 3 only (bits 7,6,5,4 = N,S,E,W)", interp_v3),
        ("v4: Both bytes OR'd (b3|b5 bits 7,6,5,4 = N,S,E,W)", interp_v4),
        ("v5: Byte 5 low nibble (bits 3,2,1,0 = N,S,E,W)", interp_v5),
        ("v6: b3.7=N, b3.6=S, b5.7=E, b5.6=W", interp_v6),
        ("v7: Byte 5 high nibble (0xA0 -> 1010 = N=1,S=0,E=1,W=0)", interp_v7),
    ]

    for name, func in interpretations:
        test_interpretation(cells_old, name, func)

    print("\n" + "="*70)
    print("ANALYSIS:")
    print("="*70)
    print("\nWhich interpretation shows one cell with ALL 4 walls?")
    print("Expected: One of the cells should show North, South, East, West")

if __name__ == "__main__":
    main()
