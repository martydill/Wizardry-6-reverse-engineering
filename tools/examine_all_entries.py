#!/usr/bin/env python3
"""
Examine all entries in the fountain/feature table in detail.
"""

def dump_entry(data, offset, entry_num, changed_offsets=None):
    """Dump a single 92-byte entry."""
    entry_size = 92
    entry_data = data[offset:offset + entry_size]

    # Count non-zero bytes
    non_zero = sum(1 for b in entry_data if b != 0)

    if non_zero == 0:
        return False  # Skip empty entries

    print(f"\n{'='*80}")
    print(f"ENTRY #{entry_num} at 0x{offset:08X} ({non_zero} non-zero bytes)")
    print(f"{'='*80}")

    # Show hex dump in rows of 16
    for i in range(0, entry_size, 16):
        row_offset = offset + i
        hex_bytes = ' '.join(f'{b:02X}' for b in entry_data[i:i+16])
        ascii_chars = ''.join(chr(b) if 32 <= b < 127 else '.' for b in entry_data[i:i+16])

        # Mark changed bytes
        marker = ""
        if changed_offsets:
            for j in range(i, min(i+16, entry_size)):
                abs_offset = offset + j
                if abs_offset in changed_offsets:
                    marker = f" ** BYTE {j} CHANGED: 0x{changed_offsets[abs_offset]:02X}"
                    break

        print(f"  +{i:02X}: {hex_bytes:<48}  {ascii_chars}{marker}")

    # Try to decode structure
    print(f"\n  Key bytes:")
    for i, b in enumerate(entry_data):
        if b != 0:
            marker = " <-- CHANGED" if changed_offsets and (offset + i) in changed_offsets else ""
            print(f"    Byte {i:2d} (0x{i:02X}): 0x{b:02X} ({b:3d}){marker}")

    return True

def main():
    with open('gamedata/NEWGAME.DBS', 'rb') as f:
        data = f.read()

    with open('gamedata/NEWGAME0.DBS', 'rb') as f:
        orig_data = f.read()

    # Changed offsets
    changed = {
        0x7D22: 0x04,
        0x7D45: 0x40,
        0x7D7E: 0x04,
        0x7DA1: 0x40
    }

    entry_size = 92
    base_offset = 0x7D22  # First modified entry

    print("="*80)
    print("COMPLETE ENTRY TABLE ANALYSIS")
    print("="*80)

    # Scan backwards for entries with data
    print("\n\nENTRIES BEFORE MODIFIED ENTRIES:")
    print("="*80)

    for i in range(10, 0, -1):
        offset = base_offset - (i * entry_size)
        if offset < 0:
            continue

        found = dump_entry(data, offset, -i, changed)
        if not found and i < 8:
            # If we've scanned 2+ empty entries, assume we're done
            break

    # Scan the modified entries and forward
    print("\n\nMODIFIED AND FOLLOWING ENTRIES:")
    print("="*80)

    for i in range(0, 30):
        offset = base_offset + (i * entry_size)
        if offset + entry_size > len(data):
            break

        found = dump_entry(data, offset, i, changed)

        # Stop after seeing several empty entries
        if not found and i > 15:
            break

    # Now check: are there entries in the original that were non-zero?
    print("\n\n" + "="*80)
    print("CHECKING ORIGINAL FILE FOR PRE-EXISTING FOUNTAINS:")
    print("="*80)

    for i in range(-10, 30):
        offset = base_offset + (i * entry_size)
        if offset < 0 or offset + entry_size > len(orig_data):
            continue

        entry_data_orig = orig_data[offset:offset + entry_size]
        entry_data_new = data[offset:offset + entry_size]

        non_zero_orig = sum(1 for b in entry_data_orig if b != 0)
        non_zero_new = sum(1 for b in entry_data_new if b != 0)

        if non_zero_orig > 0 or non_zero_new > 0:
            print(f"\nEntry #{i} at 0x{offset:08X}:")
            print(f"  Original: {non_zero_orig} non-zero bytes")
            print(f"  Modified: {non_zero_new} non-zero bytes")

            if non_zero_orig != non_zero_new:
                print(f"  ** CHANGED!")
            else:
                print(f"  (No change)")

    # Interesting pattern: byte 0 and byte 35
    print("\n\n" + "="*80)
    print("PATTERN ANALYSIS - Byte 0 and Byte 35 across all entries:")
    print("="*80)

    print("\nModified file:")
    for i in range(-5, 10):
        offset = base_offset + (i * entry_size)
        if offset < 0 or offset + entry_size > len(data):
            continue

        byte_0 = data[offset]
        byte_35 = data[offset + 35]

        if byte_0 != 0 or byte_35 != 0:
            print(f"  Entry #{i:2d}: Byte 0 = 0x{byte_0:02X}, Byte 35 = 0x{byte_35:02X}")

if __name__ == '__main__':
    main()
