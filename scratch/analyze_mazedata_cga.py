"""Analyze MAZEDATA.CGA to understand the format.

CGA uses 4 colors (2 bits per pixel) which is simpler than EGA's 16 colors.
This might make the format easier to understand.
"""

import sys
from pathlib import Path
import struct

sys.path.insert(0, str(Path(__file__).parent))

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    import pygame


# CGA palettes
CGA_PALETTE_0_HIGH = [
    (0, 0, 0),       # 0: Black
    (0, 255, 255),   # 1: Cyan
    (255, 0, 255),   # 2: Magenta
    (255, 255, 255), # 3: White
]

CGA_PALETTE_1_HIGH = [
    (0, 0, 0),       # 0: Black
    (0, 255, 0),     # 1: Green
    (255, 0, 0),     # 2: Red
    (255, 255, 0),   # 3: Yellow
]

CGA_PALETTE_0_LOW = [
    (0, 0, 0),       # 0: Black
    (0, 170, 170),   # 1: Cyan (low intensity)
    (170, 0, 170),   # 2: Magenta (low intensity)
    (170, 170, 170), # 3: Light gray
]

CGA_PALETTE_1_LOW = [
    (0, 0, 0),       # 0: Black
    (0, 170, 0),     # 1: Green (low intensity)
    (170, 0, 0),     # 2: Red (low intensity)
    (170, 170, 0),   # 3: Brown
]


def decode_cga_320x200(data: bytes, palette: list) -> 'Image.Image | pygame.Surface':
    """Decode CGA 320x200 4-color graphics mode.

    Format: 2 bits per pixel, interleaved by scan lines.
    - Even scan lines: bytes 0-8191
    - Odd scan lines: bytes 8192-16383
    Total: 16,000 bytes for 320x200 image
    """
    width, height = 320, 200

    if HAS_PIL:
        img = Image.new('RGB', (width, height))
        pixels = []

        for y in range(height):
            for x in range(0, width, 4):  # 4 pixels per byte
                # Determine which buffer (even/odd lines)
                if y % 2 == 0:
                    offset = (y // 2) * 80 + (x // 4)
                else:
                    offset = 8192 + (y // 2) * 80 + (x // 4)

                if offset >= len(data):
                    pixels.extend([palette[0]] * 4)
                    continue

                byte_val = data[offset]

                # Extract 4 pixels (2 bits each, MSB first)
                for i in range(4):
                    shift = 6 - (i * 2)
                    pixel = (byte_val >> shift) & 0x03
                    pixels.append(palette[pixel])

        img.putdata(pixels)
        return img
    else:
        surf = pygame.Surface((width, height))

        for y in range(height):
            for x in range(0, width, 4):
                if y % 2 == 0:
                    offset = (y // 2) * 80 + (x // 4)
                else:
                    offset = 8192 + (y // 2) * 80 + (x // 4)

                if offset >= len(data):
                    continue

                byte_val = data[offset]

                for i in range(4):
                    shift = 6 - (i * 2)
                    pixel = (byte_val >> shift) & 0x03
                    surf.set_at((x + i, y), palette[pixel])

        return surf


def decode_cga_linear(data: bytes, width: int, height: int, palette: list):
    """Decode CGA data as linear (non-interleaved) format."""
    if HAS_PIL:
        img = Image.new('RGB', (width, height))
        pixels = []

        byte_idx = 0
        for y in range(height):
            for x in range(0, width, 4):
                if byte_idx >= len(data):
                    pixels.extend([palette[0]] * 4)
                    continue

                byte_val = data[byte_idx]
                byte_idx += 1

                for i in range(4):
                    shift = 6 - (i * 2)
                    pixel = (byte_val >> shift) & 0x03
                    pixels.append(palette[pixel])

        img.putdata(pixels)
        return img
    else:
        surf = pygame.Surface((width, height))

        byte_idx = 0
        for y in range(height):
            for x in range(0, width, 4):
                if byte_idx >= len(data):
                    break

                byte_val = data[byte_idx]
                byte_idx += 1

                for i in range(4):
                    shift = 6 - (i * 2)
                    pixel = (byte_val >> shift) & 0x03
                    surf.set_at((x + i, y), palette[pixel])

        return surf


def analyze_cga_structure():
    """Analyze the structure of MAZEDATA.CGA."""
    print("MAZEDATA.CGA Analysis")
    print("=" * 70)

    path = Path("gamedata") / "MAZEDATA.CGA"
    if not path.exists():
        print(f"Error: {path} not found")
        return None

    data = path.read_bytes()

    print(f"File size: {len(data):,} bytes")
    print(f"Expected for 320x200 CGA: 16,000 bytes")
    print(f"Extra data: {len(data) - 16000:,} bytes")
    print()

    # Show first bytes
    print("First 128 bytes:")
    print("-" * 70)
    for i in range(0, min(128, len(data)), 16):
        hex_bytes = " ".join(f"{b:02X}" for b in data[i:i+16])
        print(f"{i:04X}: {hex_bytes}")

    print()

    # Look for patterns
    print("Data characteristics:")
    print("-" * 70)

    # Analyze first 16KB (potential image data)
    sample = data[:16000] if len(data) >= 16000 else data

    byte_counts = [0] * 256
    for b in sample:
        byte_counts[b] += 1

    non_zero = [(i, count) for i, count in enumerate(byte_counts) if count > 0]
    print(f"Unique byte values in first 16KB: {len(non_zero)}")
    print(f"Most common bytes:")
    for val, count in sorted(non_zero, key=lambda x: x[1], reverse=True)[:10]:
        print(f"  0x{val:02X}: {count:5d} times ({count*100/len(sample):.1f}%)")

    print()

    # Check for null sequences
    print("Null byte sequences:")
    print("-" * 70)

    null_runs = []
    in_null_run = False
    null_start = 0
    null_count = 0

    for i, byte in enumerate(data):
        if byte == 0:
            if not in_null_run:
                in_null_run = True
                null_start = i
                null_count = 1
            else:
                null_count += 1
        else:
            if in_null_run and null_count >= 4:
                null_runs.append((null_start, null_count))
            in_null_run = False

    print(f"Found {len(null_runs)} sequences of 4+ null bytes")
    if null_runs:
        print("First 10:")
        for start, count in null_runs[:10]:
            next_byte = data[start + count] if start + count < len(data) else 0
            print(f"  Offset 0x{start:04X}: {count:3d} null bytes (next: 0x{next_byte:02X})")

    return data


def decode_all_variations(data: bytes):
    """Try decoding with all CGA palette variations."""
    print("\n" + "=" * 70)
    print("Decoding Attempts")
    print("=" * 70)

    if not HAS_PIL:
        pygame.init()

    output_dir = Path("cga_tests")
    output_dir.mkdir(exist_ok=True)

    palettes = [
        (CGA_PALETTE_0_HIGH, "Palette0_High"),
        (CGA_PALETTE_1_HIGH, "Palette1_High"),
        (CGA_PALETTE_0_LOW, "Palette0_Low"),
        (CGA_PALETTE_1_LOW, "Palette1_Low"),
    ]

    # Try standard CGA 320x200 interleaved
    print("\n320x200 Interleaved (standard CGA):")
    print("-" * 70)

    for palette, name in palettes:
        try:
            img = decode_cga_320x200(data, palette)
            filename = output_dir / f"cga_320x200_interleaved_{name}.png"

            if HAS_PIL:
                img.save(filename)
            else:
                pygame.image.save(img, str(filename))

            print(f"  [OK] {name} -> {filename}")
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")

    # Try linear (non-interleaved) format
    print("\n320x200 Linear (non-interleaved):")
    print("-" * 70)

    for palette, name in palettes:
        try:
            img = decode_cga_linear(data, 320, 200, palette)
            filename = output_dir / f"cga_320x200_linear_{name}.png"

            if HAS_PIL:
                img.save(filename)
            else:
                pygame.image.save(img, str(filename))

            print(f"  [OK] {name} -> {filename}")
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")

    # Try different dimensions
    print("\nAlternate dimensions:")
    print("-" * 70)

    dimensions = [
        (320, 100),
        (160, 200),
        (256, 128),
        (320, 160),
    ]

    for width, height in dimensions:
        palette = CGA_PALETTE_1_LOW
        try:
            img = decode_cga_linear(data, width, height, palette)
            filename = output_dir / f"cga_{width}x{height}_linear.png"

            if HAS_PIL:
                img.save(filename)
            else:
                pygame.image.save(img, str(filename))

            print(f"  [OK] {width}x{height} -> {filename}")
        except Exception as e:
            print(f"  [FAIL] {width}x{height}: {e}")

    # Try from different offsets
    print("\nFrom different offsets (320x200 linear):")
    print("-" * 70)

    test_offsets = [0, 153, 2000, 4000, 8000, 16000]

    for offset in test_offsets:
        if offset >= len(data):
            continue

        try:
            img = decode_cga_linear(data[offset:], 320, 200, CGA_PALETTE_1_LOW)
            filename = output_dir / f"cga_offset_{offset:04X}_320x200.png"

            if HAS_PIL:
                img.save(filename)
            else:
                pygame.image.save(img, str(filename))

            print(f"  [OK] Offset 0x{offset:04X} -> {filename}")
        except Exception as e:
            print(f"  [FAIL] Offset 0x{offset:04X}: {e}")

    if not HAS_PIL:
        pygame.quit()

    print("\n" + "=" * 70)
    print("All CGA tests saved to: cga_tests/")
    print("=" * 70)


if __name__ == "__main__":
    data = analyze_cga_structure()

    if data:
        decode_all_variations(data)
