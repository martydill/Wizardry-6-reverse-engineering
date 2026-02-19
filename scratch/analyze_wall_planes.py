from pathlib import Path


ORIG = Path("gamedata/NEWGAME_original.DBS")
MOD = Path("gamedata/NEWGAME.DBS")


def iter_changed_fields(orig: bytes, mod: bytes, base: int, rel: int, count_bytes: int):
    start = base + rel
    for byte_i in range(count_bytes):
        o = orig[start + byte_i]
        m = mod[start + byte_i]
        if o == m:
            continue
        for k in range(4):
            ov = (o >> (2 * k)) & 0b11
            mv = (m >> (2 * k)) & 0b11
            if ov == mv:
                continue
            idx = byte_i * 4 + k
            block = idx // 64
            rem = idx % 64
            row = rem // 8
            col = rem % 8
            yield {
                "off": start + byte_i,
                "idx": idx,
                "block": block,
                "row": row,
                "col": col,
                "old": ov,
                "new": mv,
            }


def dump_map(name: str, base: int, orig: bytes, mod: bytes):
    print(f"\n== {name} base=0x{base:04X} ==")
    for label, rel in [("plane_60", 0x60), ("plane_120", 0x120)]:
        rows = list(iter_changed_fields(orig, mod, base, rel, 0xC0))
        print(f"  {label}: {len(rows)} changed 2-bit fields")
        for r in rows:
            print(
                f"    off=0x{r['off']:06X} idx={r['idx']:3d} "
                f"b={r['block']} r={r['row']} c={r['col']} {r['old']}->{r['new']}"
            )


def main():
    orig = ORIG.read_bytes()
    mod = MOD.read_bytes()

    # Current hypotheses from controlled edits:
    # - Map 0 wall-plane base around 0x01C0
    # - Map 10 edited wall-plane base around 0x7B77
    dump_map("map0_hypothesis", 0x01C0, orig, mod)
    dump_map("map10_hypothesis", 0x7B77, orig, mod)


if __name__ == "__main__":
    main()
