"""Diagnostic script to analyze Wizardry 6 .PIC file binary structure.

Run: python -m scratch.analyze_pic gamedata/MON00.PIC
"""
from __future__ import annotations
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from bane.data.pic_decoder import _decode_rle, _iter_frame_entries


RECORD_SIZE = 24


def hex_dump(data: bytes, offset: int = 0, length: int = 16 * 8) -> None:
    for row in range(0, min(length, len(data)), 16):
        hex_part = " ".join(f"{b:02X}" for b in data[row:row+16])
        asc_part = "".join(chr(b) if 32 <= b < 127 else "." for b in data[row:row+16])
        print(f"  {offset+row:04X}: {hex_part:<48}  {asc_part}")


def analyze(path: Path) -> None:
    raw = path.read_bytes()
    print(f"=== {path.name} ===")
    print(f"Compressed size: {len(raw)} bytes")

    dec = _decode_rle(raw)
    print(f"Decompressed size: {len(dec)} bytes")

    # Header length (first 2 bytes of first record's offset field - also == header_len)
    header_len = struct.unpack("<H", dec[:2])[0]
    print(f"Header size (from first record offset / bytes 0-1): 0x{header_len:04X} = {header_len}")
    print()

    # Dump first 96 bytes of decompressed data to see record pattern
    print("First 96 bytes (records 0-3):")
    hex_dump(dec, offset=0, length=96)
    print()

    # Parse frame records starting at byte 0 (correct alignment)
    print("Frame records (parsed from byte 0, 24 bytes each):")
    entries = _iter_frame_entries(dec, header_len)
    for idx, (offset_val, width_tiles, height_tiles, mask_bytes) in enumerate(entries):
        mask_bits = sum(b.bit_count() for b in mask_bytes)
        mask_hex = mask_bytes.hex()
        # Find first set bit positions
        set_positions = []
        for i, b in enumerate(mask_bytes):
            for bit in range(8):
                if b & (1 << bit):
                    set_positions.append(i * 8 + bit)
        print(f"  Frame {idx}: offset=0x{offset_val:04X} ({offset_val}) "
              f"tiles={width_tiles}w×{height_tiles}h "
              f"({width_tiles*8}×{height_tiles*8}px) "
              f"set_bits={mask_bits} payload={mask_bits*32}B")
        print(f"    mask: {mask_hex}")
        if set_positions:
            print(f"    set tile indices: {set_positions[:20]}{'...' if len(set_positions) > 20 else ''}")
    print()

    # Show raw record bytes for first few
    print("Raw record bytes (from byte 0):")
    for i in range(min(5, header_len // RECORD_SIZE)):
        start = i * RECORD_SIZE
        rec = dec[start:start+RECORD_SIZE]
        print(f"  Record {i}: {rec.hex()}")
    print()

    # Pixel data
    pixel_data = dec[header_len:]
    print(f"Pixel data: offset 0x{header_len:04X}, length={len(pixel_data)} bytes "
          f"= {len(pixel_data)//32} tiles (32B each)")
    print()

    print("First 64 bytes of pixel data:")
    hex_dump(pixel_data, offset=0, length=64)
    print()

    # Interpret first tile as EGA tiled planar
    if len(pixel_data) >= 32:
        tile = pixel_data[:32]
        print("First tile → EGA tiled planar (MSB first) color indices:")
        for row in range(8):
            row_colors = []
            for bit in range(8):
                mask = 0x80 >> bit
                color = 0
                for plane in range(4):
                    if tile[row + plane * 8] & mask:
                        color |= (1 << plane)
                row_colors.append(color)
            print(f"  row {row}: {row_colors}")
        print()

    # Show palette comparison
    from bane.data.sprite_decoder import DEFAULT_16_PALETTE, TITLEPAG_PALETTE
    print("Palette indices found in first tile (tiled planar):")
    indices_seen = set()
    for row in range(8):
        for bit in range(8):
            mask = 0x80 >> bit
            color = 0
            for plane in range(4):
                if pixel_data[row + plane * 8] & mask:
                    color |= (1 << plane)
            indices_seen.add(color)
    for idx in sorted(indices_seen):
        def_rgb = DEFAULT_16_PALETTE[idx] if idx < len(DEFAULT_16_PALETTE) else None
        tp_rgb = TITLEPAG_PALETTE[idx] if idx < len(TITLEPAG_PALETTE) else None
        print(f"  index {idx:2d}: DEFAULT={def_rgb}  TITLEPAG={tp_rgb}")


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("gamedata/MON00.PIC")
    analyze(path)
