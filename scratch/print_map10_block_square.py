from pathlib import Path


DB_PATH = Path("gamedata/NEWGAME.DBS")
BLOCK_BASE = 0x7B22
BLOCK_BYTES = 128


def decode_nibble_grid(buf: bytes) -> list[list[int]]:
    """Decode 16x16 nibble grid stored as four 8x8 quadrants."""
    grid = [[0 for _ in range(16)] for _ in range(16)]
    q_w = 8
    q_h = 8
    bytes_per_q = (q_w * q_h) // 2  # 32

    for qy in range(2):
        for qx in range(2):
            q_idx = qy * 2 + qx
            q = buf[q_idx * bytes_per_q : (q_idx + 1) * bytes_per_q]
            for i in range(64):
                b = q[i // 2]
                v = (b & 0x0F) if (i % 2 == 0) else ((b >> 4) & 0x0F)
                rx = i % q_w
                ry = i // q_w
                x = qx * q_w + rx
                y = qy * q_h + ry
                grid[y][x] = v
    return grid


def print_grid(grid: list[list[int]]) -> None:
    for y in range(16):
        print("".join(f"{grid[y][x]:X}" for x in range(16)))


def nonzero_cells(grid: list[list[int]]) -> list[tuple[int, int, int]]:
    out = []
    for y in range(16):
        for x in range(16):
            v = grid[y][x]
            if v != 0:
                out.append((x, y, v))
    return out


def find_2x2_candidates(grid: list[list[int]]) -> list[tuple[int, int, tuple[int, int, int, int]]]:
    """Find 2x2 windows where all four cells are nonzero."""
    cands = []
    for y in range(15):
        for x in range(15):
            a = grid[y][x]
            b = grid[y][x + 1]
            c = grid[y + 1][x]
            d = grid[y + 1][x + 1]
            if a and b and c and d:
                cands.append((x, y, (a, b, c, d)))
    return cands


def main() -> None:
    raw = DB_PATH.read_bytes()
    block = raw[BLOCK_BASE : BLOCK_BASE + BLOCK_BYTES]
    grid = decode_nibble_grid(block)

    print(f"DB: {DB_PATH}")
    print(f"map10 block chunk: 0x{BLOCK_BASE:X}..0x{BLOCK_BASE + BLOCK_BYTES - 1:X}")
    print("\nDecoded 16x16 block-id grid:")
    print_grid(grid)

    nz = nonzero_cells(grid)
    print(f"\nNonzero cells: {len(nz)}")
    if nz:
        vals = sorted(set(v for _, _, v in nz))
        print("Unique nonzero block IDs:", [f"0x{v:X}" for v in vals])
        print("First 64 nonzero entries as (x,y,id):")
        for t in nz[:64]:
            print(" ", t)

    cands = find_2x2_candidates(grid)
    print(f"\n2x2 all-nonzero candidates: {len(cands)}")
    for x, y, quad in cands[:64]:
        a, b, c, d = quad
        print(f"  top-left=({x},{y}) ids=[{a:X} {b:X}; {c:X} {d:X}]")


if __name__ == "__main__":
    main()

