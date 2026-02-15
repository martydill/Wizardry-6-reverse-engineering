#!/usr/bin/env python3
"""
Examine the region where fountain data is stored.
"""

def hex_dump(data, start_offset, length, base_offset=0):
    """Print hex dump with ASCII."""
    for i in range(0, length, 16):
        offset = base_offset + start_offset + i
        hex_part = ' '.join(f'{b:02X}' for b in data[start_offset+i:start_offset+i+16])
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data[start_offset+i:start_offset+i+16])
        print(f'{offset:08X}  {hex_part:<48}  {ascii_part}')

def analyze_fountain_data(filepath):
    """Analyze the fountain data structure."""
    with open(filepath, 'rb') as f:
        data = f.read()

    # Changed offsets
    changes = [0x7D22, 0x7D45, 0x7D7E, 0x7DA1]

    print("="*80)
    print("ANALYZING FOUNTAIN DATA REGION")
    print("="*80)

    # Find the range
    min_offset = min(changes)
    max_offset = max(changes)

    print(f"\nChanged bytes span: 0x{min_offset:08X} to 0x{max_offset:08X}")
    print(f"Range: {max_offset - min_offset} bytes")
    print(f"Spacing pattern:")
    for i in range(len(changes)-1):
        spacing = changes[i+1] - changes[i]
        print(f"  0x{changes[i]:08X} -> 0x{changes[i+1]:08X} = {spacing} bytes (0x{spacing:02X})")

    # Show broader context
    context_start = min_offset - 128
    context_end = max_offset + 128

    print(f"\n{'='*80}")
    print(f"HEX DUMP: 0x{context_start:08X} to 0x{context_end:08X}")
    print(f"{'='*80}\n")

    hex_dump(data, context_start, context_end - context_start, 0)

    # Analyze spacing
    print(f"\n{'='*80}")
    print("CHANGED BYTES DETAIL:")
    print(f"{'='*80}\n")

    for offset in changes:
        print(f"Offset 0x{offset:08X}: Value = 0x{data[offset]:02X} ({data[offset]:3d})")

        # Show surrounding bytes
        print("  Context (16 bytes before and after):")
        for i in range(offset-16, offset+17):
            if i == offset:
                print(f"    [{i:08X}] = 0x{data[i]:02X} <-- CHANGED")
            else:
                print(f"    [{i:08X}] = 0x{data[i]:02X}")
        print()

    # Look for patterns - are these part of larger structures?
    print(f"\n{'='*80}")
    print("STRUCTURE ANALYSIS:")
    print(f"{'='*80}\n")

    # Try to find record boundaries
    # The spacing of 35 and 57 bytes suggests variable-length records

    # Let's scan back to find where this section starts
    print("Scanning backwards from first change for section start...")

    # Look for padding/delimiter patterns
    for search_offset in range(min_offset - 1, max(0, min_offset - 500), -1):
        # Check if we hit a boundary (multiple zeros)
        if all(data[search_offset + i] == 0 for i in range(min(10, min_offset - search_offset))):
            print(f"  Found zero-padding at 0x{search_offset:08X}")
            if search_offset + 10 < min_offset:
                # Show what's at the start of this section
                section_start = search_offset
                while section_start < min_offset and data[section_start] == 0:
                    section_start += 1

                print(f"  Data starts at 0x{section_start:08X}")
                print(f"  Distance to first change: {min_offset - section_start} bytes")
                break

    # Scan forward for section end
    print("\nScanning forwards from last change for section end...")

    for search_offset in range(max_offset + 1, min(len(data), max_offset + 500)):
        if all(data[search_offset + i] == 0 for i in range(min(10, len(data) - search_offset))):
            print(f"  Found zero-padding at 0x{search_offset:08X}")
            print(f"  Distance from last change: {search_offset - max_offset} bytes")
            break

def compare_with_original():
    """Compare the fountain region in both files."""
    original = 'gamedata/NEWGAME0.DBS'
    modified = 'gamedata/NEWGAME.DBS'

    with open(original, 'rb') as f:
        orig_data = f.read()
    with open(modified, 'rb') as f:
        mod_data = f.read()

    changes = [0x7D22, 0x7D45, 0x7D7E, 0x7DA1]
    min_offset = min(changes) - 64
    max_offset = max(changes) + 64

    print(f"\n{'='*80}")
    print("SIDE-BY-SIDE COMPARISON")
    print(f"{'='*80}\n")

    print("ORIGINAL:")
    hex_dump(orig_data, min_offset, max_offset - min_offset, 0)

    print("\nMODIFIED:")
    hex_dump(mod_data, min_offset, max_offset - min_offset, 0)

def main():
    analyze_fountain_data('gamedata/NEWGAME.DBS')
    compare_with_original()

if __name__ == '__main__':
    main()
