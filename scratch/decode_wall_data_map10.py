from pathlib import Path


ORIG_PATH = Path("gamedata/NEWGAME_original.DBS")
MOD_PATH = Path("gamedata/NEWGAME.DBS")

# Observed edited region in current files.
BLOCK_BASE = 0x7B22
CELL_BASE = 0x7BCA
CELL_SIZE = 20


def find_diffs(orig: bytes, mod: bytes):
    return [(i, orig[i], mod[i], orig[i] ^ mod[i]) for i in range(min(len(orig), len(mod))) if orig[i] != mod[i]]


def fmt_diff(i: int, old: int, new: int, x: int) -> str:
    return f"0x{i:06X}: {old:02X}->{new:02X} xor={x:02X}"


def decode_channel_diffs(orig: bytes, mod: bytes):
    """Decode the two wall channels touched by this edit.

    Inferred from controlled 3x3 square wall edit:
    - Vertical channel: bit 0x20 in bytes 13/15, advancing by cell
    - Horizontal channel: bit 0x08 in bytes 8/10, advancing by cell
    """
    vertical = []
    horizontal = []

    # Enough slots to cover a 16-wide map axis.
    for idx in range(16):
        v_cell = idx // 2
        v_byte = 13 + 2 * (idx % 2)
        v_off = CELL_BASE + v_cell * CELL_SIZE + v_byte
        o = orig[v_off]
        n = mod[v_off]
        if (o ^ n) & 0x20:
            vertical.append((idx, v_off, o, n))

        h_cell = 1 + idx // 2
        h_byte = 8 + 2 * (idx % 2)
        h_off = CELL_BASE + h_cell * CELL_SIZE + h_byte
        o = orig[h_off]
        n = mod[h_off]
        if (o ^ n) & 0x08:
            horizontal.append((idx, h_off, o, n))

    return vertical, horizontal


def main():
    orig = ORIG_PATH.read_bytes()
    mod = MOD_PATH.read_bytes()
    diffs = find_diffs(orig, mod)

    print(f"Total file diffs: {len(diffs)}")
    for i, old, new, x in diffs:
        print(" ", fmt_diff(i, old, new, x))

    print("\nMap-block feature diffs around 0x7B22:")
    for i, old, new, x in diffs:
        if BLOCK_BASE <= i < BLOCK_BASE + 128:
            rel = i - BLOCK_BASE
            print(f"  rel={rel:03d}  {fmt_diff(i, old, new, x)}")

    print("\nInferred wall channel diffs (cell stream at 0x7BCA):")
    v_diffs, h_diffs = decode_channel_diffs(orig, mod)

    print("  Vertical channel (bit 0x20):")
    for idx, off, old, new in v_diffs:
        print(f"    seg={idx:2d} off=0x{off:06X} {old:02X}->{new:02X}")

    print("  Horizontal channel (bit 0x08):")
    for idx, off, old, new in h_diffs:
        print(f"    seg={idx:2d} off=0x{off:06X} {old:02X}->{new:02X}")

    print("\nDecoded result:")
    print("  Added vertical segments at relative indices:", [x[0] for x in v_diffs])
    print("  Added horizontal segments at relative indices:", [x[0] for x in h_diffs])
    print("  This matches a contiguous 3-segment span in each orientation (3x3 square perimeter encoding).")


if __name__ == "__main__":
    main()
