from pathlib import Path


DB = Path("gamedata/NEWGAME.DBS")
HEADER = 0x019E
RECORD = 0x0C0E


def read_u2_field(data: bytes, start: int, idx: int) -> int:
    b = data[start + (idx // 4)]
    return (b >> ((idx % 4) * 2)) & 0x03


def main() -> None:
    data = DB.read_bytes()
    n = max(0, (len(data) - HEADER) // RECORD)
    print(f"file={DB} size=0x{len(data):X} map_records={n}")
    for map_id in range(n):
        base = HEADER + map_id * RECORD
        a0 = base + 0x60
        b0 = base + 0x120
        xs = list(data[base + 0x1E0 : base + 0x1E0 + 12])
        ys = list(data[base + 0x1EC : base + 0x1EC + 12])

        nz_by_block = []
        for blk in range(12):
            nz = 0
            for r in range(8):
                for c in range(8):
                    idx = (blk << 6) + (r << 3) + c
                    if read_u2_field(data, a0, idx) or read_u2_field(data, b0, idx):
                        nz += 1
            nz_by_block.append(nz)

        active = [(b, xs[b], ys[b], nz_by_block[b]) for b in range(12) if xs[b] or ys[b] or nz_by_block[b]]
        print(f"\nmap {map_id:2d} base=0x{base:05X} active={len(active)}")
        for b, x, y, nz in active:
            print(f"  B{b:02d} origin=({x:3d},{y:3d}) nz_cells={nz:2d}")


if __name__ == "__main__":
    main()
