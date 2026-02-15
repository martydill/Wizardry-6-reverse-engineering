#!/usr/bin/env python3
"""
Wizardry 6 Wall Renderer - Corrected Version
Properly distinguishes between horizontal and vertical walls.
"""

import sys
from pathlib import Path

try:
    import pygame
except ImportError:
    print("Error: pygame not installed. Install with: pip install pygame")
    sys.exit(1)

def read_map_data(filepath, bytes_per_cell=20):
    """Read map data in column-major format."""
    with open(filepath, 'rb') as f:
        data = f.read()

    cells = []
    for i in range(400):
        start = i * bytes_per_cell
        end = start + bytes_per_cell
        if end <= len(data):
            cells.append(data[start:end])
        else:
            cells.append(bytes([0] * bytes_per_cell))

    return cells

def build_wall_map(cells):
    """
    Build wall map with corrected horizontal/vertical detection.

    Based on our discoveries:
    - Horizontal walls: Specific bytes (1,3,5) in certain cells indicate
      horizontal walls at different Y positions
    - Vertical walls: Many bytes across many cells indicate vertical edge walls
    """
    wall_map = [[{'N': False, 'S': False, 'E': False, 'W': False}
                 for _ in range(20)] for _ in range(20)]

    # VERTICAL WALLS (from our edge wall tests)
    # These span the full map height and are in the rightmost column
    # Bytes 1-19 (odd) map to Y-positions 0-19 (2 rows per byte)
    # Bit 5 = left edge, Bit 7 = right edge

    # Check cells that store vertical walls
    # From our tests: cells 30, 35-39 store vertical walls for rightmost column
    vertical_cells = [30, 35, 36, 37, 38, 39]

    for cell_idx in vertical_cells:
        if cell_idx >= len(cells):
            continue

        cell = cells[cell_idx]

        # Check all odd bytes for vertical walls
        for byte_idx in range(1, 20, 2):
            byte_val = cell[byte_idx]

            # Calculate which rows this byte represents
            # Byte 1 = rows 0-1, Byte 3 = rows 2-3, etc.
            base_row = (byte_idx - 1) // 2 * 2

            # For now, mark rightmost column (col 19)
            # Bit 5 = left edge of column, Bit 7 = right edge of column
            if byte_val & 0x80:  # Bit 7 = right edge (east wall)
                for row_offset in range(2):  # Each byte covers 2 rows
                    row = base_row + row_offset
                    if row < 20:
                        wall_map[row][19]['E'] = True

            if byte_val & 0x20:  # Bit 5 = left edge (west wall)
                for row_offset in range(2):
                    row = base_row + row_offset
                    if row < 20:
                        wall_map[row][19]['W'] = True

    # HORIZONTAL WALLS (from our 2x2 block tests)
    # Cell 30, bytes 1,3,5 contain horizontal walls
    # These are walls running East-West in our test area

    # For the test area (approximate position in grid)
    # We know Cell 30 stores horizontal walls for a specific region
    # Let's place them around the middle of the map for visibility
    test_start_row = 10
    test_start_col = 10

    cell_30 = cells[30]

    # Byte 1 = bottom horizontal walls
    if cell_30[1] & 0x20:  # Left column
        wall_map[test_start_row + 2][test_start_col]['S'] = True
    if cell_30[1] & 0x80:  # Right column
        wall_map[test_start_row + 2][test_start_col + 1]['S'] = True

    # Byte 3 = middle horizontal walls
    if cell_30[3] & 0x20:  # Left column
        wall_map[test_start_row + 1][test_start_col]['S'] = True
    if cell_30[3] & 0x80:  # Right column
        wall_map[test_start_row + 1][test_start_col + 1]['S'] = True

    # Byte 5 = top horizontal walls
    if cell_30[5] & 0x20:  # Left column
        wall_map[test_start_row][test_start_col]['N'] = True
    if cell_30[5] & 0x80:  # Right column
        wall_map[test_start_row][test_start_col + 1]['N'] = True

    return wall_map

def render_map(cells, cell_size=32):
    """Render the map with corrected walls."""

    pygame.init()

    map_width = 20
    map_height = 20

    padding = 60
    window_width = map_width * cell_size + padding * 2
    window_height = map_height * cell_size + padding * 2 + 100

    screen = pygame.display.set_mode((window_width, window_height))
    pygame.display.set_caption("Wizardry 6 - Corrected Walls")

    # Colors
    COLOR_BG = (245, 245, 240)
    COLOR_FLOOR = (220, 220, 210)
    COLOR_WALL_H = (200, 50, 50)    # Red for horizontal walls
    COLOR_WALL_V = (50, 50, 200)    # Blue for vertical walls
    COLOR_GRID = (200, 200, 195)
    COLOR_TEXT = (0, 0, 0)

    font = pygame.font.Font(None, 24)
    font_small = pygame.font.Font(None, 18)

    print("Building corrected wall map...")
    wall_map = build_wall_map(cells)

    # Count walls by type
    h_walls = 0
    v_walls = 0
    for row in range(map_height):
        for col in range(map_width):
            if wall_map[row][col]['N'] or wall_map[row][col]['S']:
                h_walls += 1
            if wall_map[row][col]['E'] or wall_map[row][col]['W']:
                v_walls += 1

    print(f"Horizontal walls: {h_walls}")
    print(f"Vertical walls: {v_walls}")

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

        # Title
        title = font.render("Wizardry 6 - Horizontal (Red) & Vertical (Blue) Walls", True, COLOR_TEXT)
        screen.blit(title, (padding - 50, 10))

        # Draw floor
        for row in range(map_height):
            for col in range(map_width):
                x = padding + col * cell_size
                y = padding + row * cell_size
                pygame.draw.rect(screen, COLOR_FLOOR,
                               (x + 1, y + 1, cell_size - 2, cell_size - 2))

        # Draw grid
        if show_grid:
            for row in range(map_height + 1):
                y = padding + row * cell_size
                pygame.draw.line(screen, COLOR_GRID,
                               (padding, y),
                               (padding + map_width * cell_size, y), 1)

            for col in range(map_width + 1):
                x = padding + col * cell_size
                pygame.draw.line(screen, COLOR_GRID,
                               (x, padding),
                               (x, padding + map_height * cell_size), 1)

        wall_thickness = 4

        # Draw walls
        for row in range(map_height):
            for col in range(map_width):
                x = padding + col * cell_size
                y = padding + row * cell_size

                walls = wall_map[row][col]

                # Horizontal walls (RED)
                if walls['N']:
                    pygame.draw.line(screen, COLOR_WALL_H,
                                   (x, y), (x + cell_size, y), wall_thickness)

                if walls['S']:
                    pygame.draw.line(screen, COLOR_WALL_H,
                                   (x, y + cell_size),
                                   (x + cell_size, y + cell_size),
                                   wall_thickness)

                # Vertical walls (BLUE)
                if walls['W']:
                    pygame.draw.line(screen, COLOR_WALL_V,
                                   (x, y), (x, y + cell_size), wall_thickness)

                if walls['E']:
                    pygame.draw.line(screen, COLOR_WALL_V,
                                   (x + cell_size, y),
                                   (x + cell_size, y + cell_size),
                                   wall_thickness)

        # Draw row/col labels
        for row in range(map_height):
            y = padding + row * cell_size + cell_size // 2
            text = font_small.render(f"{row}", True, COLOR_TEXT)
            screen.blit(text, (10, y - 8))

        for col in range(map_width):
            x = padding + col * cell_size + cell_size // 2
            text = font_small.render(f"{col}", True, COLOR_TEXT)
            screen.blit(text, (x - 8, padding - 20))

        # Info
        info_y = padding + map_height * cell_size + 20
        info = [
            f"Horizontal walls (RED): {h_walls} | Vertical walls (BLUE): {v_walls}",
            "Test area: 2x2 block around row 10-12, col 10-11",
            "Right edge: Vertical walls at column 19",
            f"Grid: {'ON' if show_grid else 'OFF'} (G) | ESC/Q to quit"
        ]

        for i, text in enumerate(info):
            rendered = font_small.render(text, True, COLOR_TEXT)
            screen.blit(rendered, (padding, info_y + i * 20))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

def main():
    filepath = Path("gamedata/NEWGAME.DBS")

    if not filepath.exists():
        print(f"Error: {filepath} not found")
        sys.exit(1)

    print("Wizardry 6 Wall Renderer - Corrected Version")
    print("="*60)
    print()
    print("Loading map data...")

    cells = read_map_data(filepath)
    render_map(cells)

if __name__ == "__main__":
    main()
