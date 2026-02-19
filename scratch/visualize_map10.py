from pathlib import Path

FEATURE_OFFSET = 0x7D22
FEATURE_SIZE = 128
MAP_WIDTH = 16
MAP_HEIGHT = 16
CELL_SIZE = 20


def decode_4bit_map(data, width, height, q_width, q_height):
    map_grid = [[0 for _ in range(width)] for _ in range(height)]

    bytes_per_q = (q_width * q_height) // 2

    for qy in range(height // q_height):
        for qx in range(width // q_width):
            q_idx = qy * (width // q_width) + qx
            q_start = q_idx * bytes_per_q
            q_data = data[q_start : q_start + bytes_per_q]

            for i in range(q_width * q_height):
                byte_idx = i // 2
                nibble = i % 2
                val = q_data[byte_idx]
                if nibble == 0:
                    val = val & 0x0F
                else:
                    val = (val >> 4) & 0x0F

                rx = i % q_width
                ry = i // q_width

                gx = qx * q_width + rx
                gy = qy * q_height + ry
                map_grid[gy][gx] = val

    return map_grid


def print_map(grid):
    for row in grid:
        print(" ".join(f"{v:X}" for v in row))


def load_bytes(path):
    return Path(path).read_bytes()


def map10_cells(raw, wall_offset):
    cells = []
    base = wall_offset
    for idx in range(MAP_WIDTH * MAP_HEIGHT):
        start = base + idx * CELL_SIZE
        cells.append(raw[start : start + CELL_SIZE])
    return cells


def cell_to_xy(cell_idx):
    x = cell_idx // MAP_HEIGHT  # column-major
    y = cell_idx % MAP_HEIGHT
    return x, y


def describe_wall_diff(cell_idx, byte_idx, old_val, new_val):
    x, y = cell_to_xy(cell_idx)
    bit_delta = old_val ^ new_val
    bits = [bit for bit in (0x80, 0x40, 0x20, 0x10, 0x08, 0x04, 0x02, 0x01) if bit_delta & bit]

    row_band = None
    if byte_idx % 2 == 1:
        row_band = (byte_idx - 1) // 2

    label = []
    if bit_delta & 0x80:
        label.append("bit7(0x80)=vertical-west?")
    if bit_delta & 0x20:
        label.append("bit5(0x20)=vertical-east?")

    return {
        "cell_idx": cell_idx,
        "x": x,
        "y": y,
        "byte_idx": byte_idx,
        "row_band": row_band,
        "old_val": old_val,
        "new_val": new_val,
        "bit_delta": bit_delta,
        "bits": bits,
        "labels": label,
    }


def print_wall_diffs(mod_raw, orig_raw, feature_offset):
    wall_offset = feature_offset + FEATURE_SIZE
    mod_cells = map10_cells(mod_raw, wall_offset)
    orig_cells = map10_cells(orig_raw, wall_offset)

    diffs = []
    for cell_idx in range(MAP_WIDTH * MAP_HEIGHT):
        for byte_idx in range(CELL_SIZE):
            old_val = orig_cells[cell_idx][byte_idx]
            new_val = mod_cells[cell_idx][byte_idx]
            if old_val != new_val:
                diffs.append(describe_wall_diff(cell_idx, byte_idx, old_val, new_val))

    print(f"\nMap Cell Data Diffs (feature=0x{feature_offset:X}, cells=0x{wall_offset:X}):")
    if not diffs:
        print("  No differences found in map 10 cell/wall data.")
        print("  Current NEWGAME.DBS and NEWGAME_original.DBS are byte-identical here.")
        return

    for d in diffs:
        row_band_text = "-" if d["row_band"] is None else str(d["row_band"])
        labels = ", ".join(d["labels"]) if d["labels"] else "unclassified bits"
        bits = ",".join(f"0x{b:02X}" for b in d["bits"])
        print(
            f"  cell={d['cell_idx']:3d} xy=({d['x']:2d},{d['y']:2d}) "
            f"byte={d['byte_idx']:2d} rowBand={row_band_text:>2} "
            f"{d['old_val']:02X}->{d['new_val']:02X} xor={d['bit_delta']:02X} bits=[{bits}] {labels}"
        )


def print_feature_grid(modified_raw, original_raw, feature_offset):
    print(f"\nModified Map 10 Features (@ 0x{feature_offset:X}):")
    data = modified_raw[feature_offset : feature_offset + FEATURE_SIZE]
    grid = decode_4bit_map(data, 16, 16, 8, 8)
    print_map(grid)

    print(f"\nOriginal Map 10 Features (@ 0x{feature_offset:X}):")
    data0 = original_raw[feature_offset : feature_offset + FEATURE_SIZE]
    grid0 = decode_4bit_map(data0, 16, 16, 8, 8)
    print_map(grid0)


def main():
    modified_path = "gamedata/NEWGAME.DBS"
    original_path = "gamedata/NEWGAME_original.DBS"

    modified_raw = load_bytes(modified_path)
    original_raw = load_bytes(original_path)

    print_feature_grid(modified_raw, original_raw, FEATURE_OFFSET)
    print_wall_diffs(modified_raw, original_raw, FEATURE_OFFSET)


if __name__ == "__main__":
    main()
