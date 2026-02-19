from pathlib import Path


from dump_map0_edges import (
    MAP0_WALL_BASE,
    decode_wall_planes,
    infer_anchor_fixed_origins,
    infer_block_layout,
    load,
    seam_mismatches,
)


ORIG_PATH = Path("gamedata/NEWGAME_original.DBS")
MOD_PATH = Path("gamedata/NEWGAME.DBS")


def run_one(name: str, path: Path, rot: int = 0, map_id: int = 0):
    fields = decode_wall_planes(load(path), MAP0_WALL_BASE)
    base_fields = decode_wall_planes(load(ORIG_PATH), MAP0_WALL_BASE)
    fixed = infer_anchor_fixed_origins(base_fields, fields, block_rot=rot)
    origins = infer_block_layout(fields, fixed_origins=fixed, block_rot=rot)
    mism = seam_mismatches(fields, origins, map_id=map_id)
    print(f"{name}: mismatches={len(mism)} rot={rot}")
    for m in mism[:40]:
        print(" ", m)
    return len(mism)


def main():
    o = run_one("original", ORIG_PATH)
    m = run_one("modified", MOD_PATH)
    if o > 0 or m > 0:
        raise SystemExit(1)
    print("PASS")


if __name__ == "__main__":
    main()

