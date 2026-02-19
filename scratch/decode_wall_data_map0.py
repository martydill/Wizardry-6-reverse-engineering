from pathlib import Path


ORIG_PATH = Path("gamedata/NEWGAME_original.DBS")
MOD_PATH = Path("gamedata/NEWGAME.DBS")


# Map 0 wall edit footprint found by diff.
MAP0_DIFF_OFFSETS = [0x220, 0x23E, 0x259, 0x25D, 0x2FE, 0x31A, 0x31B, 0x31C, 0x31D]


def main():
    orig = ORIG_PATH.read_bytes()
    mod = MOD_PATH.read_bytes()

    print("Map 0 low-offset wall diffs:")
    for off in MAP0_DIFF_OFFSETS:
        o = orig[off]
        m = mod[off]
        x = o ^ m
        cell = off // 8
        byte_in_cell = off % 8
        print(f"  0x{off:04X}: {o:02X}->{m:02X} xor={x:02X}  cell={cell} byte={byte_in_cell}")

    print("\nBit-level decode:")
    print("  0x0220 (cell 68 byte0):  +0x02  -> tested vertical edge (x=1, y=7)")
    print("  0x023E (cell 71 byte6):  +0x02  -> tested horizontal edge (x=0, y=7)")
    print("  0x0259 (cell 75 byte1):  +0x80 +0x20 +0x08 +0x02")
    print("  0x025D (cell 75 byte5):  +0x80 +0x20 +0x08 +0x02")
    print("  0x02FE (cell 95 byte6):  +0x02  -> tested horizontal edge (x=0, y=14)")
    print("  0x031A (cell 99 byte2):  +0x80")
    print("  0x031B (cell 99 byte3):  +0x80 +0x08")
    print("  0x031C (cell 99 byte4):  +0x80")
    print("  0x031D (cell 99 byte5):  +0x80 +0x08")
    print("  Total added bits = 14 (two adjacent 2x2 squares with shared center divider)")

    # Parsed as two adjacent 2x2 perimeters in the map's top-right corner.
    # Cells involved: (18,0), (19,0), (18,1), (19,1)
    edges = [
        "(16,0) north",
        "(17,0) north",
        "(18,0) north",
        "(19,0) north",
        "(16,1) south",
        "(17,1) south",
        "(18,1) south",
        "(19,1) south",
        "(16,0) west",
        "(16,1) west",
        "(18,0) west",
        "(18,1) west",
        "(19,0) east",
        "(19,1) east",
    ]
    print("\nParsed perimeter edges (inferred):")
    for e in edges:
        print(" ", e)


if __name__ == "__main__":
    main()
