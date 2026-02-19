import argparse
from pathlib import Path

import pygame


ORIG_PATH = Path("gamedata/NEWGAME_original.DBS")
MOD_PATH = Path("gamedata/NEWGAME.DBS")

CELL_BASE = 0x7BCA
CELL_SIZE = 20
MAP_SIZE = 16

# Placement model for the decoded perimeter channels.
# This anchors the edited 3x3 square around the center of the 16x16 map.
INDEX_SHIFT = 7
DEFAULT_TOP_Y = 7
DEFAULT_BOTTOM_Y = 10
DEFAULT_LEFT_X = 7
DEFAULT_RIGHT_X = 10


def load(path: Path) -> bytes:
    return path.read_bytes()


def channel_indices(data: bytes, bit_mask: int, byte_a: int, byte_b: int, cell_start: int):
    """Decode one 16-segment channel from alternating bytes across adjacent cells."""
    out = []
    for i in range(16):
        cell = cell_start + i // 2
        byte_in_cell = byte_a if i % 2 == 0 else byte_b
        off = CELL_BASE + cell * CELL_SIZE + byte_in_cell
        out.append((data[off] & bit_mask) != 0)
    return out


def decode_channels(data: bytes):
    # Four-channel perimeter decode inferred from the diff pattern:
    # Horizontal channels from bytes 13/15:
    # - bit 0x20 = side A
    # - bit 0x80 = side B
    #
    # Vertical channels from bytes 8/10:
    # - bit 0x08 = side A
    # - bit 0x02 = side B
    h_a = channel_indices(data, bit_mask=0x20, byte_a=13, byte_b=15, cell_start=0)
    h_b = channel_indices(data, bit_mask=0x80, byte_a=13, byte_b=15, cell_start=0)
    v_a = channel_indices(data, bit_mask=0x08, byte_a=8, byte_b=10, cell_start=1)
    v_b = channel_indices(data, bit_mask=0x02, byte_a=8, byte_b=10, cell_start=1)
    return {"h_a": h_a, "h_b": h_b, "v_a": v_a, "v_b": v_b}


def draw_grid(screen, origin_x, origin_y, cell_px):
    color = (70, 70, 70)
    for i in range(MAP_SIZE + 1):
        x = origin_x + i * cell_px
        y = origin_y + i * cell_px
        pygame.draw.line(screen, color, (x, origin_y), (x, origin_y + MAP_SIZE * cell_px), 1)
        pygame.draw.line(screen, color, (origin_x, y), (origin_x + MAP_SIZE * cell_px, y), 1)


def shifted(i: int) -> int:
    return (i + INDEX_SHIFT) % MAP_SIZE


def draw_horizontal_channel(screen, origin_x, origin_y, cell_px, seq, y_row, color, thickness, x_min=0, x_max=15):
    for i, enabled in enumerate(seq):
        if not enabled:
            continue
        x_idx = shifted(i)
        if not (x_min <= x_idx <= x_max):
            continue
        x0 = origin_x + x_idx * cell_px
        x1 = x0 + cell_px
        y = origin_y + y_row * cell_px
        pygame.draw.line(screen, color, (x0, y), (x1, y), thickness)


def draw_vertical_channel(screen, origin_x, origin_y, cell_px, seq, x_col, color, thickness, y_min=0, y_max=15):
    for i, enabled in enumerate(seq):
        if not enabled:
            continue
        y_idx = shifted(i)
        if not (y_min <= y_idx <= y_max):
            continue
        y0 = origin_y + y_idx * cell_px
        y1 = y0 + cell_px
        x = origin_x + x_col * cell_px
        pygame.draw.line(screen, color, (x, y0), (x, y1), thickness)


def infer_layout(orig_ch, mod_ch):
    h_added = [shifted(i) for i, (o, m) in enumerate(zip(orig_ch["h_a"], mod_ch["h_a"])) if m and not o]
    v_added = [shifted(i) for i, (o, m) in enumerate(zip(orig_ch["v_a"], mod_ch["v_a"])) if m and not o]

    if h_added:
        x_min, x_max = min(h_added), max(h_added)
    else:
        x_min, x_max = DEFAULT_LEFT_X, DEFAULT_LEFT_X + 2

    if v_added:
        y_min, y_max = min(v_added), max(v_added)
    else:
        y_min, y_max = DEFAULT_TOP_Y, DEFAULT_TOP_Y + 2

    return {
        "x_min": x_min,
        "x_max": x_max,
        "y_min": y_min,
        "y_max": y_max,
        "top_y": y_min,
        "bottom_y": y_max + 1,
        "left_x": x_min,
        "right_x": x_max + 1,
    }


def draw_channels(screen, origin_x, origin_y, cell_px, channels, base_color, layout):
    # Primary-channel model:
    # - h_a encodes horizontal span indices; render both top and bottom edges.
    # - v_a encodes vertical span indices; render both left and right edges.
    # Secondary channels are rendered as thin hints only.
    draw_horizontal_channel(screen, origin_x, origin_y, cell_px, channels["h_a"], layout["top_y"], base_color, 3)
    draw_horizontal_channel(screen, origin_x, origin_y, cell_px, channels["h_a"], layout["bottom_y"], base_color, 3)
    draw_vertical_channel(screen, origin_x, origin_y, cell_px, channels["v_a"], layout["left_x"], base_color, 3)
    draw_vertical_channel(screen, origin_x, origin_y, cell_px, channels["v_a"], layout["right_x"], base_color, 3)

    hint_color = (120, 180, 120)
    draw_horizontal_channel(screen, origin_x, origin_y, cell_px, channels["h_b"], layout["bottom_y"], hint_color, 1)
    draw_vertical_channel(screen, origin_x, origin_y, cell_px, channels["v_b"], layout["right_x"], hint_color, 1)


def draw_added(screen, origin_x, origin_y, cell_px, orig_ch, mod_ch, layout):
    add = {
        "h_a": [m and not o for o, m in zip(orig_ch["h_a"], mod_ch["h_a"])],
        "v_a": [m and not o for o, m in zip(orig_ch["v_a"], mod_ch["v_a"])],
    }
    add_color = (255, 80, 80)
    draw_horizontal_channel(screen, origin_x, origin_y, cell_px, add["h_a"], layout["top_y"], add_color, 6)
    draw_horizontal_channel(screen, origin_x, origin_y, cell_px, add["h_a"], layout["bottom_y"], add_color, 6)
    draw_vertical_channel(screen, origin_x, origin_y, cell_px, add["v_a"], layout["left_x"], add_color, 6)
    draw_vertical_channel(screen, origin_x, origin_y, cell_px, add["v_a"], layout["right_x"], add_color, 6)


def main():
    parser = argparse.ArgumentParser(description="Render decoded map-wall channels from NEWGAME.DBS")
    parser.add_argument("--show-original", action="store_true", help="Render original walls as dim overlay")
    args = parser.parse_args()

    orig = load(ORIG_PATH)
    mod = load(MOD_PATH)
    orig_ch = decode_channels(orig)
    mod_ch = decode_channels(mod)
    layout = infer_layout(orig_ch, mod_ch)

    pygame.init()
    screen = pygame.display.set_mode((900, 760))
    pygame.display.set_caption("Map Wall Decoder (0x7BCA channel view)")
    font = pygame.font.SysFont("consolas", 18)
    clock = pygame.time.Clock()

    origin_x, origin_y, cell_px = 70, 90, 36

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

        screen.fill((26, 26, 30))
        draw_grid(screen, origin_x, origin_y, cell_px)

        if args.show_original:
            draw_channels(screen, origin_x, origin_y, cell_px, orig_ch, (90, 90, 140), layout)

        draw_channels(screen, origin_x, origin_y, cell_px, mod_ch, (210, 210, 240), layout)
        draw_added(screen, origin_x, origin_y, cell_px, orig_ch, mod_ch, layout)

        lines = [
            "Decoded wall channels from NEWGAME.DBS block @ 0x7BCA (mirrored-primary model)",
            "Primary: H bit 0x20 (bytes 13/15), V bit 0x08 (bytes 8/10)",
            "Secondary hints: H bit 0x80, V bit 0x02",
            f"Inferred square x={layout['x_min']}..{layout['x_max']} y={layout['y_min']}..{layout['y_max']}",
            "Red = added vs NEWGAME_original.DBS",
            "Esc = quit",
        ]
        for i, text in enumerate(lines):
            surf = font.render(text, True, (220, 220, 220))
            screen.blit(surf, (70, 20 + i * 18))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
