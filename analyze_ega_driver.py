"""Analyze EGA.DRV for palette or color mapping information."""

import sys
from pathlib import Path
import struct

def analyze_ega_driver():
    """Analyze EGA.DRV file for palette/color information."""
    path = Path("gamedata") / "EGA.DRV"

    if not path.exists():
        print(f"Error: {path} not found")
        return

    data = path.read_bytes()

    print("EGA.DRV Analysis")
    print("=" * 70)
    print(f"File size: {len(data)} bytes")
    print()

    # Look for palette data (RGB triplets or color tables)
    print("First 256 bytes:")
    print("-" * 70)
    for i in range(0, min(256, len(data)), 16):
        hex_bytes = " ".join(f"{b:02X}" for b in data[i:i+16])
        print(f"{i:04X}: {hex_bytes}")

    # Look for potential 16-color palette (48 bytes = 16 colors * 3 bytes RGB)
    print("\n" + "=" * 70)
    print("Looking for palette structures (16 colors * 3 bytes = 48 bytes):")
    print("-" * 70)

    for offset in range(0, min(1000, len(data) - 48), 1):
        # Check if this could be RGB palette data
        chunk = data[offset:offset+48]

        # VGA palette values are 0-63 (6-bit)
        if all(b <= 63 for b in chunk):
            print(f"\nPossible VGA palette at offset {offset} (0x{offset:04X}):")
            for i in range(0, 48, 3):
                r, g, b = chunk[i], chunk[i+1], chunk[i+2]
                # Convert to 8-bit
                r8, g8, b8 = r << 2, g << 2, b << 2
                print(f"  Color {i//3:2d}: R={r:2d} G={g:2d} B={b:2d} -> ({r8:3d}, {g8:3d}, {b8:3d})")

            # Only show first few matches
            if offset > 100:
                break

    # Look for EGA color mappings (16 possible colors)
    print("\n" + "=" * 70)
    print("Looking for color index mappings:")
    print("-" * 70)

    # Check for sequences that might be color remapping tables
    for offset in range(0, min(500, len(data) - 16)):
        chunk = list(data[offset:offset+16])

        # Check if it's a permutation of 0-15
        if sorted(chunk) == list(range(16)):
            print(f"\nPotential color remap at offset {offset} (0x{offset:04X}):")
            print(f"  {' '.join(f'{b:2d}' for b in chunk)}")

    print("\n" + "=" * 70)


def compare_mazedata_versions():
    """Compare MAZEDATA.EGA and MAZEDATA.CGA files."""
    print("\nComparing MAZEDATA versions")
    print("=" * 70)

    ega_path = Path("gamedata") / "MAZEDATA.EGA"
    cga_path = Path("gamedata") / "MAZEDATA.CGA"

    if not ega_path.exists() or not cga_path.exists():
        print("One or both files not found")
        return

    ega_data = ega_path.read_bytes()
    cga_data = cga_path.read_bytes()

    print(f"MAZEDATA.EGA: {len(ega_data):,} bytes")
    print(f"MAZEDATA.CGA: {len(cga_data):,} bytes")
    print()

    # Compare structures
    print("First 64 bytes comparison:")
    print("-" * 70)
    print("EGA: " + " ".join(f"{b:02X}" for b in ega_data[:64]))
    print("CGA: " + " ".join(f"{b:02X}" for b in cga_data[:64]))
    print()

    # Check if CGA version has similar structure
    min_len = min(len(ega_data), len(cga_data))

    # Find where they differ
    first_diff = None
    for i in range(min_len):
        if ega_data[i] != cga_data[i]:
            first_diff = i
            break

    if first_diff:
        print(f"First difference at byte {first_diff} (0x{first_diff:04X})")
        print(f"  EGA[{first_diff}] = 0x{ega_data[first_diff]:02X}")
        print(f"  CGA[{first_diff}] = 0x{cga_data[first_diff]:02X}")
    else:
        if len(ega_data) == len(cga_data):
            print("Files are identical!")
        else:
            print(f"Files match up to {min_len} bytes")

    # Try decoding CGA version
    # CGA uses 4 colors (2 bits per pixel)
    print("\n" + "=" * 70)
    print("CGA format characteristics:")
    print("-" * 70)

    # CGA 320x200 4-color mode uses 16,000 bytes (2 bits per pixel)
    expected_cga_size = 320 * 200 // 4
    print(f"Expected size for 320x200 CGA: {expected_cga_size} bytes")

    # Check if file matches any known CGA format
    if len(cga_data) >= expected_cga_size:
        print(f"File could contain CGA 320x200 image")


if __name__ == "__main__":
    analyze_ega_driver()
    compare_mazedata_versions()
