#!/usr/bin/env python3
"""
Wizardry 6 - Render Map 10 (16x16)
Loads and renders map from SCENARIO.DBS at offset 40960.
"""

import sys
from pathlib import Path

try:
    import pygame
except ImportError:
    print("Error: pygame not installed. Install with: pip install pygame")
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
        else:
            cells.append(bytes([0] * bytes_per_cell))

    return cells

def decode_walls_all_cells(cells, width, height):
    """
    Decode walls for ALL cells using the unified encoding system.

    For each cell, check odd bytes for wall bits:
      Bit 5 = LEFT position
      Bit 7 = RIGHT position
    """
    # Wall map: [row][col] = {N, S, E, W}
    wall_map = [[{'N': False, 'S': False, 'E': False, 'W': False}
                 for _ in range(width)] for _ in range(height)]

    print(f"Decoding walls for {width}x{height} map...")

    # Process each cell
    for cell_idx in range(min(len(cells), width * height)):
        file_col = cell_idx // height  # Column-major
        file_row = cell_idx % height

        cell = cells[cell_idx]

        # Check all ODD bytes (1,3,5,7,9,11,13,15,17,19)
        for byte_idx in range(1, 20, 2):
            byte_val = cell[byte_idx]

            if byte_val & 0xA0:  # Has bit 5 or 7
                # Calculate which rows this byte represents
                # Byte 1 = rows 0-1, Byte 3 = rows 2-3, etc.
                base_row = (byte_idx - 1) // 2 * 2

                # For a 16x16 map, we need to map file cells to game cells
                # Let's try the simplest mapping: file cell = game cell
                game_col = file_col

                # Bit 7 = right position
                if byte_val & 0x80:
                    for row_offset in range(2):
                        row = base_row + row_offset
                        if 0 <= row < height and 0 <= game_col < width:
                            # Mark east wall (right edge of this cell)
                            wall_map[row][game_col]['E'] = True

                # Bit 5 = left position
                if byte_val & 0x20:
                    for row_offset in range(2):
                        row = base_row + row_offset
                        if 0 <= row < height and 0 <= game_col < width:
                            # Mark west wall (left edge of this cell)
                            wall_map[row][game_col]['W'] = True

    return wall_map

def render_map(cells, width, height, cell_size=32):
    """Render the 16x16 map."""

    pygame.init()

    padding = 60
    window_width = width * cell_size + padding * 2
    window_height = height * cell_size + padding * 2 + 100

    screen = pygame.display.set_mode((window_width, window_height))
    pygame.display.set_caption(f"Wizardry 6 - Map 10 ({width}x{height})")

    # Colors
    COLOR_BG = (245, 245, 240)
    COLOR_FLOOR = (220, 220, 210)
    COLOR_WALL = (60, 60, 60)
    COLOR_GRID = (200, 200, 195)
    COLOR_TEXT = (0, 0, 0)

    font = pygame.font.Font(None, 24)
    font_small = pygame.font.Font(None, 18)

    print("Decoding walls...")
    wall_map = decode_walls_all_cells(cells, width, height)

    # Count walls
    total_walls = 0
    cells_with_walls = 0
    for row in range(height):
        for col in range(width):
            walls = wall_map[row][col]
            wall_count = sum(walls.values())
            total_walls += wall_count
            if wall_count > 0:
                cells_with_walls += 1

    print(f"Total walls: {total_walls}")
    print(f"Cells with walls: {cells_with_walls}/{width*height}")

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
        title = font.render(f"Wizardry 6 - Map 10 ({width}x{height})", True, COLOR_TEXT)
        screen.blit(title, (padding, 10))

        # Subtitle
        subtitle = font_small.render("SCENARIO.DBS @ offset 0xA000", True, COLOR_TEXT)
        screen.blit(subtitle, (padding, 35))

        # Draw floor tiles
        for row in range(height):
            for col in range(width):
                x = padding + col * cell_size
                y = padding + row * cell_size

                pygame.draw.rect(screen, COLOR_FLOOR,
                               (x + 1, y + 1, cell_size - 2, cell_size - 2))

        # Draw grid
        if show_grid:
            for row in range(height + 1):
                y = padding + row * cell_size
                pygame.draw.line(screen, COLOR_GRID,
                               (padding, y),
                               (padding + width * cell_size, y), 1)

            for col in range(width + 1):
                x = padding + col * cell_size
                pygame.draw.line(screen, COLOR_GRID,
                               (x, padding),
                               (x, padding + height * cell_size), 1)

        # Draw walls
        wall_thickness = 3

        for row in range(height):
            for col in range(width):
                x = padding + col * cell_size
                y = padding + row * cell_size

                walls = wall_map[row][col]

                # North wall
                if walls['N']:
                    pygame.draw.line(screen, COLOR_WALL,
                                   (x, y), (x + cell_size, y),
                                   wall_thickness)

                # South wall
                if walls['S']:
                    pygame.draw.line(screen, COLOR_WALL,
                                   (x, y + cell_size),
                                   (x + cell_size, y + cell_size),
                                   wall_thickness)

                # West wall
                if walls['W']:
                    pygame.draw.line(screen, COLOR_WALL,
                                   (x, y), (x, y + cell_size),
                                   wall_thickness)

                # East wall
                if walls['E']:
                    pygame.draw.line(screen, COLOR_WALL,
                                   (x + cell_size, y),
                                   (x + cell_size, y + cell_size),
                                   wall_thickness)

        # Draw row/column labels
        for row in range(height):
            y = padding + row * cell_size + cell_size // 2
            text = font_small.render(f"{row}", True, COLOR_TEXT)
            screen.blit(text, (10, y - 8))

        for col in range(width):
            x = padding + col * cell_size + cell_size // 2
            text = font_small.render(f"{col}", True, COLOR_TEXT)
            screen.blit(text, (x - 8, padding - 20))

        # Info panel
        info_y = padding + height * cell_size + 20

        info_lines = [
            f"Walls: {total_walls} | Cells with walls: {cells_with_walls}/{width*height}",
            f"Grid: {'ON' if show_grid else 'OFF'} (G) | ESC/Q: Quit"
        ]

        for i, line in enumerate(info_lines):
            rendered = font_small.render(line, True, COLOR_TEXT)
            screen.blit(rendered, (padding, info_y + i * 20))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

def main():
    import sys
    
    filepath = Path("gamedata/SCENARIO.DBS")
    offset = 40960
    
    if len(sys.argv) > 1:
        filepath = Path(sys.argv[1])
    if len(sys.argv) > 2:
        offset = int(sys.argv[2])

    if not filepath.exists():
        print(f"Error: {filepath} not found")
        sys.exit(1)

    print("Wizardry 6 - Map 10 Renderer")
    print("="*60)
    print()
    print(f"Loading map from {filepath} @ offset {offset}")
    print("Map size: 16x16")
    print()

    width = 16
    height = 16

    cells = read_map_data(filepath, offset, width, height)
    render_map(cells, width, height)

if __name__ == "__main__":
    main()
