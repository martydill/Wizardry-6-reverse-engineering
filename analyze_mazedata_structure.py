"""Analyze MAZEDATA.EGA as a potential tile-based or indexed format.

Instead of assuming it's a raw planar image, let's investigate if it might be:
1. A tile map with indexed tiles
2. A compressed format
3. A format with metadata/headers similar to MON*.PIC files
"""

import sys
from pathlib import Path
import struct

sys.path.insert(0, str(Path(__file__).parent))


def analyze_as_tile_index():
    """Analyze if MAZEDATA.EGA might be a tile index format."""
    path = Path("gamedata") / "MAZEDATA.EGA"
    if not path.exists():
        print(f"Error: {path} not found")
        return

    data = path.read_bytes()

    print("MAZEDATA.EGA Structure Analysis")
    print("=" * 70)
    print(f"Total file size: {len(data):,} bytes")
    print()

    # Look for header-like structures
    print("Analyzing potential header (first 256 bytes):")
    print("-" * 70)

    # Try interpreting as 16-bit little-endian values
    print("\nAs LE16 words:")
    words = []
    for i in range(0, min(64, len(data)), 2):
        word = struct.unpack_from('<H', data, i)[0]
        words.append(word)

    for i in range(0, min(32, len(words)), 8):
        hex_words = " ".join(f"{w:04X}" for w in words[i:i+8])
        dec_words = " ".join(f"{w:5d}" for w in words[i:i+8])
        print(f"{i*2:04X}: {hex_words}")
        print(f"      {dec_words}")

    # Check if first word might be a count or offset
    first_word = words[0]
    print(f"\nFirst word: 0x{first_word:04X} ({first_word} decimal)")
    print(f"  If count: {first_word} entries")
    print(f"  If offset: points to byte {first_word} (0x{first_word:04X})")

    # Look for repeating patterns or structures
    print("\n" + "=" * 70)
    print("Looking for repeating structures...")
    print("-" * 70)

    # Try different stride lengths to find repeating patterns
    for stride in [4, 6, 8, 10, 12, 16, 32]:
        patterns = {}
        for i in range(0, min(1000, len(data) - stride), stride):
            pattern = tuple(data[i:i+stride])
            patterns[pattern] = patterns.get(pattern, 0) + 1

        # Find most common pattern
        if patterns:
            most_common = max(patterns.items(), key=lambda x: x[1])
            unique_count = len(patterns)
            print(f"\nStride {stride:2d}: {unique_count:4d} unique patterns")
            if most_common[1] > 1:
                pattern_bytes = " ".join(f"{b:02X}" for b in most_common[0])
                print(f"  Most common (appears {most_common[1]} times): {pattern_bytes}")

    # Check for null-byte sequences (padding between structures)
    print("\n" + "=" * 70)
    print("Null byte sequences (potential structure boundaries):")
    print("-" * 70)

    null_runs = []
    in_null_run = False
    null_start = 0
    null_count = 0

    for i, byte in enumerate(data[:32000]):
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
        print(f"First 20 null sequences:")
        for start, count in null_runs[:20]:
            next_byte = data[start + count] if start + count < len(data) else 0
            print(f"  Offset 0x{start:04X}: {count:3d} null bytes (next byte: 0x{next_byte:02X})")

    # Try to find tile-sized chunks (8x8 = 64 pixels = 32 bytes in planar)
    print("\n" + "=" * 70)
    print("Looking for 32-byte tile boundaries...")
    print("-" * 70)

    # Skip potential header and look at data after first null sequence
    if null_runs:
        data_start = null_runs[0][0] + null_runs[0][1]
        print(f"Starting analysis at offset 0x{data_start:04X}")

        # Check if data is organized in 32-byte chunks
        chunk_size = 32
        num_chunks = (len(data) - data_start) // chunk_size
        print(f"Could contain {num_chunks} 32-byte tiles")

        # Show first few potential tiles
        print(f"\nFirst 5 potential tiles (32 bytes each):")
        for tile_idx in range(min(5, num_chunks)):
            offset = data_start + tile_idx * chunk_size
            tile_data = data[offset:offset+chunk_size]

            # Count unique bytes
            unique = len(set(tile_data))
            zeros = sum(1 for b in tile_data if b == 0)

            print(f"\nTile {tile_idx} @ 0x{offset:04X}:")
            print(f"  Unique bytes: {unique}, Zeros: {zeros}")
            print(f"  Data: {' '.join(f'{b:02X}' for b in tile_data[:16])}")
            print(f"        {' '.join(f'{b:02X}' for b in tile_data[16:])}")

    # Check if it might be RLE compressed like MON*.PIC
    print("\n" + "=" * 70)
    print("Checking for RLE compression...")
    print("-" * 70)

    high_bit_bytes = sum(1 for b in data[:1000] if b >= 0x80)
    low_bit_bytes = sum(1 for b in data[:1000] if 0 < b < 0x80)

    print(f"In first 1000 bytes:")
    print(f"  High bit set (0x80-0xFF): {high_bit_bytes} ({high_bit_bytes/10:.1f}%)")
    print(f"  Low bit clear (0x01-0x7F): {low_bit_bytes} ({low_bit_bytes/10:.1f}%)")
    print(f"  Null bytes (0x00): {data[:1000].count(0)} ({data[:1000].count(0)/10:.1f}%)")

    if high_bit_bytes > 100 and low_bit_bytes > 100:
        print("\n  -> High proportion of both high-bit and low-bit bytes")
        print("  -> Could indicate RLE compression (high bit = run, low bit = literal count)")
    else:
        print("\n  -> Distribution doesn't match typical RLE pattern")


def compare_with_pic_format():
    """Compare structure with MON*.PIC files."""
    print("\n" + "=" * 70)
    print("Comparing with MON00.PIC structure...")
    print("-" * 70)

    mazedata_path = Path("gamedata") / "MAZEDATA.EGA"
    mon00_path = Path("gamedata") / "MON00.PIC"

    if not mon00_path.exists():
        print("MON00.PIC not found, skipping comparison")
        return

    mazedata = mazedata_path.read_bytes()
    mon00 = mon00_path.read_bytes()

    print(f"\nFile sizes:")
    print(f"  MAZEDATA.EGA: {len(mazedata):,} bytes")
    print(f"  MON00.PIC: {len(mon00):,} bytes")

    print(f"\nFirst 32 bytes comparison:")
    print(f"  MAZEDATA: {' '.join(f'{b:02X}' for b in mazedata[:32])}")
    print(f"  MON00:    {' '.join(f'{b:02X}' for b in mon00[:32])}")

    # MON00.PIC is RLE compressed
    print(f"\nMON00.PIC characteristics (known RLE compressed):")
    print(f"  High-bit bytes: {sum(1 for b in mon00[:1000] if b >= 0x80)}/1000")
    print(f"  Low-bit bytes: {sum(1 for b in mon00[:1000] if 0 < b < 0x80)}/1000")

    print(f"\nMAZEDATA.EGA characteristics:")
    print(f"  High-bit bytes: {sum(1 for b in mazedata[:1000] if b >= 0x80)}/1000")
    print(f"  Low-bit bytes: {sum(1 for b in mazedata[:1000] if 0 < b < 0x80)}/1000")


def try_rlc_decompression():
    """Try RLE decompression on MAZEDATA.EGA."""
    print("\n" + "=" * 70)
    print("Attempting RLE decompression...")
    print("-" * 70)

    path = Path("gamedata") / "MAZEDATA.EGA"
    data = path.read_bytes()

    def decompress_rle(compressed: bytes, max_output: int = 100000) -> bytes:
        """Try decompressing as RLE (high-bit encoding like MON*.PIC)."""
        output = bytearray()
        i = 0

        while i < len(compressed) and len(output) < max_output:
            control = compressed[i]
            i += 1

            if control == 0x00:
                # Terminator
                break
            elif control < 0x80:
                # Literal run: read next 'control' bytes
                if i + control <= len(compressed):
                    output.extend(compressed[i:i+control])
                    i += control
                else:
                    break
            else:
                # Repeat run: repeat next byte (-control) times using two's complement
                if i < len(compressed):
                    repeat_byte = compressed[i]
                    i += 1
                    # Two's complement for repeat count
                    count = (~control + 1) & 0xFF
                    output.extend([repeat_byte] * count)
                else:
                    break

        return bytes(output)

    # Try decompressing from start
    decompressed = decompress_rle(data)

    print(f"Decompressed {len(data)} bytes -> {len(decompressed)} bytes")

    if len(decompressed) > 0:
        print(f"\nFirst 64 bytes of decompressed data:")
        for i in range(0, min(64, len(decompressed)), 16):
            hex_bytes = " ".join(f"{b:02X}" for b in decompressed[i:i+16])
            print(f"  {i:04X}: {hex_bytes}")

        # Check if first 2 bytes might be a header length
        if len(decompressed) >= 2:
            header_len = struct.unpack_from('<H', decompressed, 0)[0]
            print(f"\nFirst word (LE16): 0x{header_len:04X} ({header_len} decimal)")
            if 0 < header_len < len(decompressed):
                print(f"  If header length: payload starts at byte {header_len}")

        # Save decompressed data for inspection
        output_path = Path("mazedata_decompressed.bin")
        output_path.write_bytes(decompressed)
        print(f"\nSaved decompressed data to: {output_path}")
    else:
        print("\nDecompression produced no output - probably not RLE compressed")


if __name__ == "__main__":
    analyze_as_tile_index()
    compare_with_pic_format()
    try_rlc_decompression()

    print("\n" + "=" * 70)
    print("Analysis complete!")
    print("=" * 70)
