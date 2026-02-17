import os
import sys

def render_map_ascii(data, start_cell, w, h):
    grid = [[" " for _ in range(2 * w + 1)] for _ in range(2 * h + 1)]
    for c in range(w):
        for r in range(h):
            idx = start_cell + c * h + r
            if idx * 8 + 7 >= len(data): continue
            cell_data = data[idx * 8 : (idx + 1) * 8]
            b3, b5 = cell_data[3], cell_data[5]
            ay, ax = 2 * r + 1, 2 * c + 1
            grid[ay][ax] = "."
            if b3 & 0x80:
                grid[ay-1][ax] = "-"
                grid[ay-1][ax-1] = "+"
                grid[ay-1][ax+1] = "+"
            if b3 & 0x40:
                grid[ay+1][ax] = "-"
                grid[ay+1][ax-1] = "+"
                grid[ay+1][ax+1] = "+"
            if b5 & 0x80:
                grid[ay][ax-1] = "|"
                grid[ay-1][ax-1] = "+"
                grid[ay+1][ax-1] = "+"
            if b5 & 0x20:
                grid[ay][ax+1] = "|"
                grid[ay-1][ax+1] = "+"
                grid[ay+1][ax+1] = "+"
    return "\n".join("".join(row) for row in grid)

def main():
    path = "gamedata/NEWGAME.DBS"
    if not os.path.exists(path): return
    with open(path, "rb") as f:
        f.read(14)
        data = f.read()
    total_cells = len(data) // 8
    height = 32
    width = total_cells // height
    block_width = 20
    for col_start in range(0, width, block_width):
        current_w = min(block_width, width - col_start)
        start_cell = col_start * height
        empty = True
        for i in range(start_cell, start_cell + current_w * height):
            if i*8+7 < len(data) and (data[i*8+3] != 0 or data[i*8+5] != 0):
                empty = False
                break
        if empty: continue
        print(f"\n[ SECTOR: Columns {col_start} to {col_start + current_w - 1} ]")
        print(render_map_ascii(data, start_cell, current_w, height))

if __name__ == "__main__":
    main()
