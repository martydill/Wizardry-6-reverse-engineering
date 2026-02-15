#!/usr/bin/env python3
"""
Examine specific data blocks in the Graphic & Map Data section.
"""
import struct
from pathlib import Path

def u8(buf, off):  return buf[off]
def u16(buf, off): return struct.unpack_from('<H', buf, off)[0]

# Known blocks from the scan
INTERESTING_BLOCKS = [
    (0x009409, 23, "First block - very small"),
    (0x009468, 740, "Large block - 740 bytes"),
    (0x0099aa, 758, "Large block - 758 bytes"),
    (0x00a0b3, 224, "224 bytes = 11 races * 20 bytes + 4? Or 14 classes * 16 bytes?"),
    (0x00a609, 25, "25 bytes - interesting size"),
]

def examine_block(data, offset, length, desc):
    print(f"\n{'='*80}")
    print(f"Block at 0x{offset:06X} ({length} bytes) - {desc}")
    print(f"{'='*80}")

    block = data[offset:offset + length]

    # Show hex dump
    print("\nHex dump:")
    for i in range(0, min(256, len(block)), 16):
        hex_str = ' '.join(f'{b:02X}' for b in block[i:i+16])
        ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in block[i:i+16])
        print(f"  {offset+i:06X}: {hex_str:<48s} {ascii_str}")

    # Check for table-like structure
    print(f"\nPotential table interpretations:")

    # Try different record sizes
    for rec_size in [7, 8, 11, 14, 16, 20, 22, 28, 32, 37, 53]:
        if length % rec_size == 0:
            count = length // rec_size
            print(f"  {count} records × {rec_size} bytes")
            if count in [11, 14]:  # Race or class count
                print(f"    ** INTERESTING: This matches {'RACES' if count == 11 else 'CLASSES'} count! **")

    # Statistical analysis
    print(f"\nByte statistics:")
    print(f"  Min value: {min(block)}")
    print(f"  Max value: {max(block)}")
    print(f"  Unique bytes: {len(set(block))}")
    print(f"  Zero bytes: {block.count(0)} ({block.count(0)/len(block)*100:.1f}%)")
    print(f"  Low bytes (<16): {sum(1 for b in block if b < 16)} ({sum(1 for b in block if b < 16)/len(block)*100:.1f}%)")
    print(f"  ASCII printable: {sum(1 for b in block if 32 <= b < 127)} ({sum(1 for b in block if 32 <= b < 127)/len(block)*100:.1f}%)")

def main():
    dbs_path = Path("C:/Users/marty/Documents/code/bane/gamedata/SCENARIO.DBS")

    with open(dbs_path, 'rb') as f:
        data = f.read()

    print("DETAILED EXAMINATION OF SPECIFIC BLOCKS")
    print("=" * 80)

    for offset, length, desc in INTERESTING_BLOCKS:
        examine_block(data, offset, length, desc)

    # Now let's scan for specific patterns
    print(f"\n\n{'='*80}")
    print("SCANNING FOR RACE/CLASS TABLE CANDIDATES")
    print(f"{'='*80}\n")

    section = data[0x9409:0x154E6]

    # Look specifically for 11-entry and 14-entry tables
    # Common RPG stats are in range 3-18, modified stats might be 1-100
    for start in range(0, len(section) - 300):
        for rec_size in range(7, 30):
            # Try 11 races
            size11 = 11 * rec_size
            if start + size11 < len(section):
                block = section[start:start + size11]
                # Check if this looks like stat data (reasonable value ranges)
                valid_stats = sum(1 for b in block if 0 <= b <= 100)
                if valid_stats > size11 * 0.8:  # 80% reasonable values
                    # Check if not too many zeros (stats shouldn't be mostly 0)
                    if block.count(0) < size11 * 0.3:
                        print(f"Potential RACE table: 0x{0x9409+start:06X}, {rec_size} bytes/record")
                        # Show first 3 records
                        for i in range(3):
                            rec = block[i*rec_size:(i+1)*rec_size]
                            hex_str = ' '.join(f'{b:02X}' for b in rec)
                            print(f"  Record {i}: {hex_str}")

            # Try 14 classes
            size14 = 14 * rec_size
            if start + size14 < len(section):
                block = section[start:start + size14]
                valid_stats = sum(1 for b in block if 0 <= b <= 100)
                if valid_stats > size14 * 0.8:
                    if block.count(0) < size14 * 0.3:
                        print(f"Potential CLASS table: 0x{0x9409+start:06X}, {rec_size} bytes/record")
                        for i in range(3):
                            rec = block[i*rec_size:(i+1)*rec_size]
                            hex_str = ' '.join(f'{b:02X}' for b in rec)
                            print(f"  Record {i}: {hex_str}")

if __name__ == "__main__":
    main()
