#!/usr/bin/env python3
"""
Analyze sconce changes to understand feature encoding better.

User added:
- 4 fountains in corners: (0,0), (15,0), (0,15), (15,15)
- 4 sconces in middle square: (7,7), (8,7), (7,8), (8,8)
  (One at the corner of each 8x8 quadrant)
"""

def analyze_changes():
    """Analyze all changes in the file."""
    with open('gamedata/NEWGAME0.DBS', 'rb') as f:
        orig = f.read()
    with open('gamedata/NEWGAME.DBS', 'rb') as f:
        modi = f.read()

    # Find all differences
    changes = []
    for i in range(len(orig)):
        if orig[i] != modi[i]:
            changes.append((i, orig[i], modi[i]))

    print("=" * 80)
    print("COMPLETE CHANGE ANALYSIS")
    print("=" * 80)
    print()

    print(f"Total changes: {len(changes)} bytes")
    print()

    # Group by entry
    entry_size = 92
    entry_0_start = 0x7D22
    entry_1_start = 0x7D7E

    entry_0_changes = []
    entry_1_changes = []
    other_changes = []

    for offset, old_val, new_val in changes:
        if entry_0_start <= offset < entry_0_start + entry_size:
            byte_num = offset - entry_0_start
            entry_0_changes.append((byte_num, old_val, new_val))
        elif entry_1_start <= offset < entry_1_start + entry_size:
            byte_num = offset - entry_1_start
            entry_1_changes.append((byte_num, old_val, new_val))
        else:
            other_changes.append((offset, old_val, new_val))

    print("=" * 80)
    print("ENTRY #0 (0x7D22) CHANGES:")
    print("=" * 80)
    print()

    for byte_num, old_val, new_val in sorted(entry_0_changes):
        print(f"  Byte {byte_num:2d} (0x{byte_num:02X}): 0x{old_val:02X} -> 0x{new_val:02X} ({old_val:3d} -> {new_val:3d})")

    print()
    print("=" * 80)
    print("ENTRY #1 (0x7D7E) CHANGES:")
    print("=" * 80)
    print()

    for byte_num, old_val, new_val in sorted(entry_1_changes):
        print(f"  Byte {byte_num:2d} (0x{byte_num:02X}): 0x{old_val:02X} -> 0x{new_val:02X} ({old_val:3d} -> {new_val:3d})")

    if other_changes:
        print()
        print("=" * 80)
        print("OTHER CHANGES:")
        print("=" * 80)
        print()
        for offset, old_val, new_val in other_changes:
            print(f"  0x{offset:08X}: 0x{old_val:02X} -> 0x{new_val:02X}")

    # Analyze patterns
    print()
    print("=" * 80)
    print("PATTERN ANALYSIS:")
    print("=" * 80)
    print()

    print("Entry #0 bytes:")
    print("  Byte 0:  0x04 = 4   <- Feature type (fountain)")
    print("  Byte 31: 0x30 = 48  <- NEW! (sconce related)")
    print("  Byte 35: 0x40 = 64  <- Enable flag")
    print("  Byte 60: 0x03 = 3   <- NEW! (sconce related)")
    print("  Byte 67: 0x30 = 48  <- NEW! (sconce related)")
    print()

    print("Entry #1 bytes:")
    print("  Byte 0:  0x04 = 4   <- Feature type (fountain)")
    print("  Byte 4:  0x03 = 3   <- NEW! (sconce related)")
    print("  Byte 35: 0x40 = 64  <- Enable flag")
    print()

    print("=" * 80)
    print("HYPOTHESES:")
    print("=" * 80)
    print()

    print("Hypothesis 1: Multiple feature slots per entry")
    print("  - Entry #0 Byte 0 = 0x04 (fountain)")
    print("  - Entry #0 Byte 60 = 0x03 (sconce?)")
    print("  - Entry #1 Byte 0 = 0x04 (fountain)")
    print("  - Entry #1 Byte 4 = 0x03 (sconce?)")
    print("  -> Each entry can hold multiple features!")
    print()

    print("Hypothesis 2: 0x03 = Sconce type ID")
    print("  - 0x04 = Fountain")
    print("  - 0x03 = Sconce")
    print()

    print("Hypothesis 3: 0x30 = Position or attribute data")
    print("  - 0x30 appears at bytes 31 and 67 in Entry #0")
    print("  - 0x30 = 48 decimal = 0b00110000")
    print("  - Could be coordinates or flags")
    print()

    # Check spacing between feature slots
    print("=" * 80)
    print("FEATURE SLOT STRUCTURE:")
    print("=" * 80)
    print()

    print("Entry #0 feature slots:")
    print("  Slot 1: Byte 0 = type")
    print("  Slot 2: Byte 60 = type (60 bytes later)")
    print()

    print("Entry #1 feature slots:")
    print("  Slot 1: Byte 0 = type")
    print("  Slot 2: Byte 4 = type (4 bytes later)")
    print()

    print("This suggests VARIABLE slot sizes or different slot positions!")
    print()

    # Look at the actual data around these bytes
    print("=" * 80)
    print("CONTEXT AROUND CHANGED BYTES:")
    print("=" * 80)
    print()

    def show_context(data, offset, size=8):
        """Show bytes around a position."""
        start = max(0, offset - size)
        end = min(len(data), offset + size + 1)

        for i in range(start, end):
            marker = " <--" if i == offset else ""
            print(f"    0x{i:08X} (+{i-entry_0_start if i >= entry_0_start else '?':3}): 0x{data[i]:02X}{marker}")

    print("\nEntry #0, Byte 31 (0x30):")
    show_context(modi, 0x7D22 + 31)

    print("\nEntry #0, Byte 60 (0x03):")
    show_context(modi, 0x7D22 + 60)

    print("\nEntry #0, Byte 67 (0x30):")
    show_context(modi, 0x7D22 + 67)

    print("\nEntry #1, Byte 4 (0x03):")
    show_context(modi, 0x7D7E + 4)

def show_complete_entries():
    """Show the complete data for both entries."""
    with open('gamedata/NEWGAME.DBS', 'rb') as f:
        data = f.read()

    entry_size = 92
    entry_0_start = 0x7D22
    entry_1_start = 0x7D7E

    print("\n" + "=" * 80)
    print("COMPLETE ENTRY DATA:")
    print("=" * 80)

    for entry_num, entry_start in [(0, entry_0_start), (1, entry_1_start)]:
        print(f"\nEntry #{entry_num} (0x{entry_start:08X}):")
        print()

        entry_data = data[entry_start:entry_start + entry_size]

        # Show hex dump
        for i in range(0, entry_size, 16):
            hex_bytes = ' '.join(f'{b:02X}' for b in entry_data[i:i+16])
            print(f"  +{i:02X}: {hex_bytes}")

        # List all non-zero bytes
        print(f"\n  Non-zero bytes:")
        for i, byte in enumerate(entry_data):
            if byte != 0:
                print(f"    Byte {i:2d} (0x{i:02X}): 0x{byte:02X} ({byte:3d})")

def main():
    analyze_changes()
    show_complete_entries()

if __name__ == '__main__':
    main()
