#!/usr/bin/env python3
"""
Wizardry 6 - Map 10 Comparison Renderer
Renders map 10 two ways to understand byte encoding:
1. Using ALL bytes 1-19
2. Using ONLY bytes 1-15 (valid for 16x16)
"""

import sys
from pathlib import Path

try:
    import pygame
except ImportError:
    print("Error: pygame not installed")
    sys.exit(1)

def read_map_data(filepath, offset, width, height, bytes_per_cell=20):
    """Read map data from specific offset."""
    total_cells = width * height

    with open(filepath, 'rb') as f:
        f.seek(offset)
        data = f.read(total_cells * bytes_per_cell)

    cells = []
    for i in range(total_cells):
        start = i * bytes_per_cell
        end = start + bytes_per_cell
        if end <= len(data):
            cells.append(data[start:end])

    return cells

def decode_walls(cells, width, height, max_byte=19):
    """Decode walls, optionally limiting to certain bytes."""
    wall_map = [[{'N': False, 'S': False, 'E': False, 'W': False}
                 for _ in range(width)] for _ in range(height)]

    for cell_idx in range(min(len(cells), width * height)):
        file_col = cell_idx // height
        file_row = cell_idx % height

        cell = cells[cell_idx]

        # Check odd bytes up to max_byte
        for byte_idx in range(1, min(max_byte + 1, 20), 2):
            byte_val = cell[byte_idx]

            if byte_val & 0xA0:
                # Map file cell to game cell (assume direct mapping for now)
                game_col = file_col
                base_row = (byte_idx - 1) // 2 * 2

                if byte_val & 0x80:  # Right
                    for row_offset in range(2):
                        row = base_row + row_offset
                        if 0 <= row < height and 0 <= game_col < width:
                            wall_map[row][game_col]['E'] = True

                if byte_val & 0x20:  # Left
                    for row_offset in range(2):
                        row = base_row + row_offset
                        if 0 <= row < height and 0 <= game_col < width:
                            wall_map[row][game_col]['W'] = True

    return wall_map

def render_comparison(cells, width, height):
    """Render map two ways side by side."""

    pygame.init()

    cell_size = 28
    padding = 40
    gap = 60  # Gap between the two maps

    map_width_px = width * cell_size
    map_height_px = height * cell_size

    window_width = map_width_px * 2 + padding * 2 + gap
    window_height = map_height_px + padding * 2 + 140

    screen = pygame.display.set_mode((window_width, window_height))
    pygame.display.set_caption("Wizardry 6 - Map 10 Comparison")

    # Colors
    COLOR_BG = (245, 245, 240)
    COLOR_FLOOR = (220, 220, 210)
    COLOR_WALL = (60, 60, 60)
    COLOR_GRID = (200, 200, 195)
    COLOR_TEXT = (0, 0, 0)
    COLOR_WALL_EXTRA = (180, 50, 50)  # Red for extra walls

    font = pygame.font.Font(None, 20)
    font_small = pygame.font.Font(None, 16)

    # Decode both ways
    print("Decoding with bytes 1-19 (ALL)...")
    walls_all = decode_walls(cells, width, height, max_byte=19)

    print("Decoding with bytes 1-15 (valid for 16x16)...")
    walls_valid = decode_walls(cells, width, height, max_byte=15)

    # Count walls
    def count_walls(wall_map):
        total = 0
        cells_with = 0
        for row in range(height):
            for col in range(width):
                w = wall_map[row][col]
                count = sum(w.values())
                total += count
                if count > 0:
                    cells_with += 1
        return total, cells_with

    total_all, cells_all = count_walls(walls_all)
    total_valid, cells_valid = count_walls(walls_valid)

    print(f"ALL bytes: {total_all} walls, {cells_all} cells")
    print(f"VALID bytes: {total_valid} walls, {cells_valid} cells")
    print(f"Difference: {total_all - total_valid} walls from bytes 17-19")

    clock = pygame.time.Clock()
    running = True
    show_grid = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE or event.key == pygame.K_q:
                    running = False
                elif event.key == pygame.K_g:
                    show_grid = not show_grid

        screen.fill(COLOR_BG)

        # Titles
        title = font.render("Map 10 Comparison - Which decoding is correct?", True, COLOR_TEXT)
        screen.blit(title, (padding, 10))

        # Left map title
        left_title = font_small.render(f"ALL bytes (1-19): {total_all} walls", True, COLOR_TEXT)
        screen.blit(left_title, (padding, 35))

        # Right map title
        right_x = padding + map_width_px + gap
        right_title = font_small.render(f"VALID bytes (1-15): {total_valid} walls", True, COLOR_TEXT)
        screen.blit(right_title, (right_x, 35))

        # Draw both maps
        for map_idx, (wall_map, x_offset) in enumerate([
            (walls_all, padding),
            (walls_valid, padding + map_width_px + gap)
        ]):
            # Draw floor
            for row in range(height):
                for col in range(width):
                    x = x_offset + col * cell_size
                    y = padding + row * cell_size + 20

                    pygame.draw.rect(screen, COLOR_FLOOR,
                                   (x + 1, y + 1, cell_size - 2, cell_size - 2))

            # Draw grid
            if show_grid:
                for row in range(height + 1):
                    y = padding + row * cell_size + 20
                    pygame.draw.line(screen, COLOR_GRID,
                                   (x_offset, y),
                                   (x_offset + map_width_px, y), 1)

                for col in range(width + 1):
                    x = x_offset + col * cell_size
                    pygame.draw.line(screen, COLOR_GRID,
                                   (x, padding + 20),
                                   (x, padding + map_height_px + 20), 1)

            # Draw walls
            wall_thickness = 2

            for row in range(height):
                for col in range(width):
                    x = x_offset + col * cell_size
                    y = padding + row * cell_size + 20

                    walls = wall_map[row][col]

                    # For left map, highlight walls that come from bytes 17-19
                    if map_idx == 0:
                        # Check if this position has more walls than the valid version
                        extra_walls = sum(walls.values()) > sum(walls_valid[row][col].values())
                        color = COLOR_WALL_EXTRA if extra_walls else COLOR_WALL
                    else:
                        color = COLOR_WALL

                    if walls['W']:
                        pygame.draw.line(screen, color,
                                       (x, y), (x, y + cell_size),
                                       wall_thickness)

                    if walls['E']:
                        pygame.draw.line(screen, color,
                                       (x + cell_size, y),
                                       (x + cell_size, y + cell_size),
                                       wall_thickness)

        # Info panel
        info_y = padding + map_height_px + 40

        info_lines = [
            "Left: Uses ALL bytes including 17-19 (rows beyond 16x16)",
            "Right: Uses ONLY bytes 1-15 (rows 0-15, valid for 16x16)",
            f"Red walls = come from bytes 17-19",
            "",
            f"Difference: {total_all - total_valid} walls | Grid: {'ON' if show_grid else 'OFF'} (G) | ESC/Q: Quit"
        ]

        for i, line in enumerate(info_lines):
            rendered = font_small.render(line, True, COLOR_TEXT)
            screen.blit(rendered, (padding, info_y + i * 16))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

def main():
    filepath = Path("gamedata/SCENARIO.DBS")

    if not filepath.exists():
        print(f"Error: {filepath} not found")
        sys.exit(1)

    print("Wizardry 6 - Map 10 Comparison Renderer")
    print("="*60)
    print()

    offset = 40960
    width = 16
    height = 16

    cells = read_map_data(filepath, offset, width, height)
    render_comparison(cells, width, height)

if __name__ == "__main__":
    main()
