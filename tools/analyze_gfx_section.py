#!/usr/bin/env python3
"""
Analyze the Graphic & Map Data section of scenario.dbs (0x9409 - 0x154E6)
"""
import struct
from pathlib import Path

def u8(buf, off):  return buf[off]
def u16(buf, off): return struct.unpack_from('<H', buf, off)[0]
def u32(buf, off): return struct.unpack_from('<I', buf, off)[0]

def read_cstring(buf, offset, maxlen=16):
    raw = buf[offset:offset + maxlen]
    null = raw.find(b'\x00')
    if null >= 0:
        raw = raw[:null]
    try:
        return raw.decode('ascii')
    except UnicodeDecodeError:
        return raw.decode('latin-1', errors='replace')

# Section boundaries
GFX_START = 0x9409
GFX_END = 0x154E6
GFX_SIZE = GFX_END - GFX_START

def main():
    dbs_path = Path("C:/Users/marty/Documents/code/bane/gamedata/SCENARIO.DBS")

    with open(dbs_path, 'rb') as f:
        data = f.read()

    section = data[GFX_START:GFX_END]

    print("=" * 80)
    print("GRAPHIC & MAP DATA SECTION ANALYSIS")
    print("=" * 80)
    print(f"Section: 0x{GFX_START:06X} - 0x{GFX_END:06X}")
    print(f"Size: {GFX_SIZE:,} bytes ({GFX_SIZE/1024:.1f} KB)\n")

    # Scan for recognizable patterns
    print("-" * 80)
    print("PATTERN SCAN")
    print("-" * 80)

    # Look for runs of non-zero data (likely data blocks)
    blocks = []
    in_block = False
    block_start = 0
    zero_count = 0

    for i in range(len(section)):
        if section[i] != 0:
            if not in_block:
                in_block = True
                block_start = i
            zero_count = 0
        else:
            zero_count += 1
            if in_block and zero_count > 32:
                # End of block
                block_len = i - zero_count - block_start
                if block_len > 16:
                    blocks.append({
                        'rel_offset': block_start,
                        'abs_offset': GFX_START + block_start,
                        'length': block_len,
                        'data': section[block_start:i - zero_count]
                    })
                in_block = False

    # Last block
    if in_block:
        block_len = len(section) - block_start
        blocks.append({
            'rel_offset': block_start,
            'abs_offset': GFX_START + block_start,
            'length': block_len,
            'data': section[block_start:]
        })

    print(f"\nFound {len(blocks)} data blocks:\n")

    for i, blk in enumerate(blocks):
        print(f"Block {i+1}:")
        print(f"  Offset: 0x{blk['abs_offset']:06X} (rel: +0x{blk['rel_offset']:04X})")
        print(f"  Length: {blk['length']:,} bytes")

        # Analyze block content
        d = blk['data']

        # Check if it looks like ASCII strings
        ascii_chars = sum(1 for b in d if 32 <= b < 127)
        ascii_ratio = ascii_chars / len(d) if len(d) > 0 else 0

        # Check if it looks like 4-bit planar data (bytes in 0-15 range)
        low_nibble = sum(1 for b in d if b < 16)
        low_ratio = low_nibble / len(d) if len(d) > 0 else 0

        # Check for structure (repeating patterns)
        if len(d) >= 32:
            # Check if divisible by common sizes
            print(f"  Divisible by: ", end="")
            for size in [8, 16, 32, 64, 128, 256]:
                if len(d) % size == 0:
                    print(f"{size}({len(d)//size}x) ", end="")
            print()

        print(f"  ASCII ratio: {ascii_ratio:.2%}")
        print(f"  Low-byte ratio (<16): {low_ratio:.2%}")

        # Show first 64 bytes
        print(f"  First 64 bytes (hex):")
        for j in range(0, min(64, len(d)), 16):
            hex_str = ' '.join(f'{b:02X}' for b in d[j:j+16])
            ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in d[j:j+16])
            print(f"    {j:04X}: {hex_str:<48s} {ascii_str}")

        # Try to identify what this might be
        print(f"  Likely content: ", end="")
        if ascii_ratio > 0.5:
            print("Text/strings")
        elif low_ratio > 0.9:
            print("4-bit planar graphics")
        elif len(d) % 32 == 0 and len(d) % 64 == 0:
            print("Tile data (8x8 tiles)")
        else:
            print("Binary table/data")

        print()

    # Look for specific patterns
    print("-" * 80)
    print("SEARCHING FOR SPECIFIC PATTERNS")
    print("-" * 80)

    # Race/class tables might have fixed-size records
    print("\nLooking for table structures...")

    # Common record sizes in RPGs: 8, 16, 32, 64, 128
    for rec_size in [8, 11, 16, 20, 32, 64]:
        count = 0
        for blk in blocks:
            if blk['length'] % rec_size == 0 and blk['length'] >= rec_size * 5:
                entries = blk['length'] // rec_size
                if entries <= 50:  # Reasonable table size
                    count += 1
        if count > 0:
            print(f"  {count} blocks divisible by {rec_size} (potential {rec_size}-byte records)")

    # Look for sprite IDs (0-58 based on MON00.PIC - MON58.PIC)
    print("\nLooking for sprite ID references (0-58)...")
    sprite_refs = []
    for i in range(len(section) - 1):
        val = section[i]
        if 0 <= val <= 58:
            # Check if it's in a context that looks like an ID
            if i > 0 and i < len(section) - 1:
                sprite_refs.append((GFX_START + i, val))

    print(f"  Found {len(sprite_refs)} potential sprite ID bytes (0-58)")
    if len(sprite_refs) > 0 and len(sprite_refs) < 100:
        print(f"  First 20 references:")
        for off, val in sprite_refs[:20]:
            print(f"    0x{off:06X}: {val}")

if __name__ == "__main__":
    main()
