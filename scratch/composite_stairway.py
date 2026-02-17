"""Parse MAZEDATA.EGA display list and composite stairway group for tile 68.

The display list (bytes 0x301..0x7FF) contains groups of 4-byte records,
zero-separated. Each record: [b0, tile_id_1indexed, x_bytes, y_pixels].

This script finds the group(s) containing tile 68 and renders a composite view.
"""

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from bane.data.sprite_decoder import decode_mazedata_tiles, TITLEPAG_PALETTE

try:
    from PIL import Image, ImageDraw
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("PIL not available; text output only")


PIXEL_DATA_OFFSET = 0x800
TARGET_TILE_IDX = 68  # 0-indexed tile we want to find


def parse_header(data: bytes):
    """Return (n_tiles, descriptor_list, display_list_start_offset)."""
    n = data[0] | (data[1] << 8)
    descs = []
    for i in range(n):
        base = 4 + i * 5
        if base + 5 > len(data):
            break
        seg = data[base] | (data[base + 1] << 8)
        b2  = data[base + 2]
        w   = data[base + 3]
        h   = data[base + 4]
        descs.append((seg, b2, w, h))
    display_list_start = 4 + n * 5
    return n, descs, display_list_start


def parse_display_list(data: bytes, start: int, end: int):
    """Parse display list into groups of 4-byte records.

    Returns list of groups; each group is a list of (b0, tile_id_1indexed, x_bytes, y_pixels).
    Zero bytes separate groups (any zero in the tile_id position ends a group).
    """
    raw = data[start:end]
    groups = []
    current = []
    i = 0
    while i < len(raw):
        # Try to read a 4-byte record
        if i + 4 > len(raw):
            break
        b0, tile_id, xb, yp = raw[i], raw[i+1], raw[i+2], raw[i+3]
        if tile_id == 0:
            # Group terminator
            if current:
                groups.append(current)
                current = []
            i += 1  # skip the zero byte only (it's a single-byte separator)
        else:
            current.append((b0, tile_id, xb, yp))
            i += 4
    if current:
        groups.append(current)
    return groups


def find_groups_with_tile(groups, tile_idx_0indexed):
    """Return list of (group_idx, groups[group_idx]) where tile appears."""
    tile_1indexed = tile_idx_0indexed + 1
    result = []
    for gi, group in enumerate(groups):
        ids = [rec[1] for rec in group]
        if tile_1indexed in ids:
            result.append((gi, group))
    return result


def main():
    path = Path("gamedata/MAZEDATA.EGA")
    if not path.exists():
        path = Path("../gamedata/MAZEDATA.EGA")
    data = path.read_bytes()

    n, descs, dl_start = parse_header(data)
    dl_end = 0x800  # pixel data starts here

    print(f"Tiles: {n}, display list: 0x{dl_start:03X}..0x{dl_end:03X} ({dl_end-dl_start} bytes)")
    print()

    groups = parse_display_list(data, dl_start, dl_end)
    print(f"Display list groups: {len(groups)}")

    # Show group sizes
    size_hist = {}
    for g in groups:
        s = len(g)
        size_hist[s] = size_hist.get(s, 0) + 1
    print(f"Group size histogram: {sorted(size_hist.items())}")
    print()

    # Show all tile IDs for first 10 groups
    print("First 10 groups:")
    for gi, g in enumerate(groups[:10]):
        ids = [rec[1] for rec in g]
        coords = [(rec[2]*8, rec[3]) for rec in g]
        print(f"  Group {gi:3d}: {len(g)} records, tile_ids={ids}, screen_xy={coords}")
    print()

    # Find groups containing tile 68 (1-indexed = 69)
    matching = find_groups_with_tile(groups, TARGET_TILE_IDX)
    print(f"Groups containing tile {TARGET_TILE_IDX} (1-indexed={TARGET_TILE_IDX+1}): {len(matching)}")
    for gi, g in matching:
        ids = [rec[1] for rec in g]
        coords = [(rec[2]*8, rec[3]) for rec in g]
        print(f"  Group {gi:3d}: tile_ids={ids}, screen_xy={coords}")
    print()

    # Also find nearby tiles (65-75)
    print("Groups containing tiles 65-75:")
    for tile_i in range(65, 76):
        m = find_groups_with_tile(groups, tile_i)
        for gi, g in m:
            ids = [rec[1] for rec in g]
            coords = [(rec[2]*8, rec[3]) for rec in g]
            print(f"  tile={tile_i}, group {gi:3d}: tile_ids={ids}, screen_xy={coords}")
    print()

    # Decode all tiles using the correct decode_mazedata_tiles
    sprites = decode_mazedata_tiles(path)
    print(f"Decoded {len(sprites)} sprites")

    # Show tile 68 info
    if TARGET_TILE_IDX < len(descs):
        seg, b2, w, h = descs[TARGET_TILE_IDX]
        print(f"Tile {TARGET_TILE_IDX}: seg=0x{seg:04X}, b2={b2}, w_units={w} ({w*8}px), h={h}px")
        print(f"  abs_off=0x{seg*16+b2:05X}, file_off=0x{PIXEL_DATA_OFFSET+seg*16+b2:05X}")
        print(f"  tile_bytes={4*w*h}")

    if not HAS_PIL:
        print("PIL not available; cannot render composite image")
        return

    # For each group containing tile 68, render a composite view
    if not matching:
        print("Tile 68 not found in any display list group — rendering standalone")
        matching = [(None, [(0, TARGET_TILE_IDX+1, 0, 0)])]

    for gi, g in matching[:3]:  # at most 3 composites
        # Determine canvas size (EGA screen: 320x200)
        canvas_w, canvas_h = 320, 200
        canvas = Image.new("RGB", (canvas_w, canvas_h), (20, 20, 30))

        for rec in g:
            b0, tid, xb, yp = rec
            sprite_idx = tid - 1  # convert to 0-indexed
            if sprite_idx < 0 or sprite_idx >= len(sprites):
                continue
            sp = sprites[sprite_idx]
            x_px = xb * 8
            y_px = yp

            # Convert sprite to PIL image
            img = Image.frombytes("RGB", (sp.width, sp.height), sp.to_rgb_bytes())

            # Paste (may be partially off-screen)
            try:
                canvas.paste(img, (x_px, y_px))
            except Exception as e:
                print(f"  paste error tile {sprite_idx} at ({x_px},{y_px}): {e}")

        # Highlight tile 68's area
        draw = ImageDraw.Draw(canvas)
        tile68_sp = sprites[TARGET_TILE_IDX]
        # Find where tile 68 is placed
        for rec in g:
            b0, tid, xb, yp = rec
            if tid == TARGET_TILE_IDX + 1:
                x_px = xb * 8
                y_px = yp
                draw.rectangle([x_px, y_px, x_px + tile68_sp.width - 1, y_px + tile68_sp.height - 1],
                                outline=(255, 0, 0), width=2)

        label = f"group_{gi}_composite" if gi is not None else "tile68_standalone"
        out_path = Path("scratch/tile68_var") / f"{label}.png"
        out_path.parent.mkdir(exist_ok=True)
        canvas.save(out_path)
        print(f"Saved: {out_path}")

    # Also render tile 68 standalone at 4x scale
    if TARGET_TILE_IDX < len(sprites):
        sp68 = sprites[TARGET_TILE_IDX]
        img68 = Image.frombytes("RGB", (sp68.width, sp68.height), sp68.to_rgb_bytes())
        img68_4x = img68.resize((sp68.width * 4, sp68.height * 4), Image.NEAREST)
        out68 = Path("scratch/tile68_var") / "tile68_standalone_4x.png"
        img68_4x.save(out68)
        print(f"Saved: {out68} ({sp68.width}x{sp68.height})")

    # Render all tiles in all groups that contain tile 68 side by side
    for gi, g in matching[:1]:
        ids_0 = [rec[1] - 1 for rec in g]
        tile_imgs = []
        for i, rec in enumerate(g):
            sid = rec[1] - 1
            if 0 <= sid < len(sprites):
                sp = sprites[sid]
                img = Image.frombytes("RGB", (sp.width, sp.height), sp.to_rgb_bytes())
                tile_imgs.append((rec[1], sp, img))

        if tile_imgs:
            max_h = max(t[2].height for t in tile_imgs)
            total_w = sum(t[2].width + 4 for t in tile_imgs)
            strip = Image.new("RGB", (total_w, max_h + 20), (20, 20, 30))
            draw = ImageDraw.Draw(strip)
            x = 0
            for tid, sp, img in tile_imgs:
                strip.paste(img, (x, 20))
                # Highlight tile 68
                color = (255, 0, 0) if tid == TARGET_TILE_IDX + 1 else (100, 100, 100)
                draw.rectangle([x, 20, x + sp.width - 1, 20 + sp.height - 1], outline=color)
                draw.text((x + 1, 1), str(tid - 1), fill=(200, 200, 200))
                x += sp.width + 4
            out_strip = Path("scratch/tile68_var") / f"group_{gi}_strip.png"
            strip.save(out_strip)
            print(f"Saved: {out_strip}")

    print("Done.")


if __name__ == "__main__":
    main()
