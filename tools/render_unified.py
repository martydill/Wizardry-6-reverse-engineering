#!/usr/bin/env python3
"""
Wizardry 6 Wall Renderer - Unified Encoding System
Uses the complete decoded format:
  - Byte = Y-position (0-19)
  - Bit 5 = LEFT position
  - Bit 7 = RIGHT position
  - Works for BOTH horizontal and vertical walls!
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

def decode_walls_unified(cells):
    """
    Decode walls using the unified encoding system.

    For rightmost column (game X=19):
      - File cells 26-30, 35-39
      - Bit 7 = walls at X=19
      - All odd bytes = Y-positions 0-19
    """
    # Wall map: [row][col] = {N, S, E, W}
    wall_map = [[{'N': False, 'S': False, 'E': False, 'W': False}
                 for _ in range(20)] for _ in range(20)]

    # Cells that store rightmost column walls (from our tests)
    right_cells = [26, 27, 28, 29, 30, 35, 36, 37, 38, 39]

    # Decode walls for rightmost column (X=19)
    for cell_idx in right_cells:
        if cell_idx >= len(cells):
            continue

        cell = cells[cell_idx]

        # Check all ODD bytes (1,3,5,7,9,11,13,15,17,19)
        for byte_idx in range(1, 20, 2):
            byte_val = cell[byte_idx]

            # Calculate which rows this byte represents
            # Byte 1 = rows 0-1, Byte 3 = rows 2-3, etc.
            base_row = (byte_idx - 1) // 2 * 2

            # Bit 7 = right position (X=19)
            if byte_val & 0x80:
                for row_offset in range(2):
                    row = base_row + row_offset
                    if 0 <= row < 20:
                        # This bit indicates walls at position (19, row)
                        # Could be horizontal wall or vertical wall
                        # For rendering, mark both E wall and horizontal walls
                        wall_map[row][19]['E'] = True  # East wall (right edge)

                        # Also mark horizontal walls in rightmost column
                        # These appear as walls between rows
                        if row > 0:
                            wall_map[row][19]['N'] = True  # North wall

            # Bit 5 = left position (X=0 or left edge of X=19)
            if byte_val & 0x20:
                for row_offset in range(2):
                    row = base_row + row_offset
                    if 0 <= row < 20:
                        # This could be left edge or left of rightmost column
                        wall_map[row][19]['W'] = True  # West wall
                        if row > 0:
                            wall_map[row][19]['N'] = True

    return wall_map

def render_map(cells, cell_size=32):
    """Render the map with unified wall encoding."""

    pygame.init()

    map_width = 20
    map_height = 20

    padding = 60
    window_width = map_width * cell_size + padding * 2
    window_height = map_height * cell_size + padding * 2 + 120

    screen = pygame.display.set_mode((window_width, window_height))
    pygame.display.set_caption("Wizardry 6 - Unified Wall System")

    # Colors
    COLOR_BG = (245, 245, 240)
    COLOR_FLOOR = (220, 220, 210)
    COLOR_WALL = (60, 60, 60)           # Dark gray walls
    COLOR_EDGE = (180, 50, 50)          # Red for edge walls
    COLOR_GRID = (200, 200, 195)
    COLOR_TEXT = (0, 0, 0)
    COLOR_HIGHLIGHT = (255, 240, 200)   # Highlight rightmost column

    font = pygame.font.Font(None, 24)
    font_small = pygame.font.Font(None, 18)
    font_tiny = pygame.font.Font(None, 14)

    print("Decoding walls with unified system...")
    wall_map = decode_walls_unified(cells)

    # Count walls
    total_walls = 0
    edge_walls = 0
    for row in range(map_height):
        for col in range(map_width):
            walls = wall_map[row][col]
            wall_count = sum(walls.values())
            total_walls += wall_count
            if col == 19:
                edge_walls += wall_count

    print(f"Total walls: {total_walls}")
    print(f"Rightmost column walls: {edge_walls}")

    clock = pygame.time.Clock()
    running = True
    show_grid = True
    show_coords = False

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE or event.key == pygame.K_q:
                    running = False
                elif event.key == pygame.K_g:
                    show_grid = not show_grid
                elif event.key == pygame.K_c:
                    show_coords = not show_coords

        screen.fill(COLOR_BG)

        # Title
        title = font.render("Wizardry 6 - Unified Wall Encoding", True, COLOR_TEXT)
        screen.blit(title, (padding, 10))

        # Subtitle
        subtitle = font_small.render("Byte=Y, Bit5=Left, Bit7=Right", True, COLOR_TEXT)
        screen.blit(subtitle, (padding, 35))

        # Draw floor tiles
        for row in range(map_height):
            for col in range(map_width):
                x = padding + col * cell_size
                y = padding + row * cell_size

                # Highlight rightmost column
                if col == 19:
                    color = COLOR_HIGHLIGHT
                else:
                    color = COLOR_FLOOR

                pygame.draw.rect(screen, color,
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

        # Draw walls
        wall_thickness = 4

        for row in range(map_height):
            for col in range(map_width):
                x = padding + col * cell_size
                y = padding + row * cell_size

                walls = wall_map[row][col]

                # Use red for edge walls in rightmost column
                wall_color = COLOR_EDGE if col == 19 else COLOR_WALL

                # North wall
                if walls['N']:
                    pygame.draw.line(screen, wall_color,
                                   (x, y), (x + cell_size, y),
                                   wall_thickness)

                # South wall
                if walls['S']:
                    pygame.draw.line(screen, wall_color,
                                   (x, y + cell_size),
                                   (x + cell_size, y + cell_size),
                                   wall_thickness)

                # West wall
                if walls['W']:
                    pygame.draw.line(screen, wall_color,
                                   (x, y), (x, y + cell_size),
                                   wall_thickness)

                # East wall
                if walls['E']:
                    pygame.draw.line(screen, wall_color,
                                   (x + cell_size, y),
                                   (x + cell_size, y + cell_size),
                                   wall_thickness)

                # Show coordinates if enabled
                if show_coords and (col == 19 or col == 0):
                    coord_text = font_tiny.render(f"{row}", True, COLOR_TEXT)
                    screen.blit(coord_text, (x + 2, y + 2))

        # Draw row labels
        for row in range(map_height):
            y = padding + row * cell_size + cell_size // 2
            text = font_small.render(f"{row}", True, COLOR_TEXT)
            screen.blit(text, (10, y - 8))

        # Draw column labels
        for col in range(map_width):
            x = padding + col * cell_size + cell_size // 2
            text = font_small.render(f"{col}", True, COLOR_TEXT)
            text_color = COLOR_EDGE if col == 19 else COLOR_TEXT
            text = font_small.render(f"{col}", True, text_color)
            screen.blit(text, (x - 8, padding - 20))

        # Info panel
        info_y = padding + map_height * cell_size + 20

        info_lines = [
            f"Total walls: {total_walls} | Rightmost column (red): {edge_walls}",
            "Encoding: Byte 1-19 = Y-pos | Bit 5 = Left | Bit 7 = Right",
            "Rightmost column highlighted in tan",
            "",
            f"Grid: {'ON' if show_grid else 'OFF'} (G) | Coords: {'ON' if show_coords else 'OFF'} (C) | ESC/Q: Quit"
        ]

        for i, line in enumerate(info_lines):
            rendered = font_small.render(line, True, COLOR_TEXT)
            screen.blit(rendered, (padding, info_y + i * 18))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

def main():
    filepath = Path("gamedata/NEWGAME.DBS")

    if not filepath.exists():
        print(f"Error: {filepath} not found")
        sys.exit(1)

    print("Wizardry 6 - Unified Wall Encoding Renderer")
    print("="*60)
    print()
    print("Unified System:")
    print("  Byte position = Y-coordinate (rows 0-19)")
    print("  Bit 5 = LEFT position")
    print("  Bit 7 = RIGHT position")
    print()
    print("Loading map...")

    cells = read_map_data(filepath)
    render_map(cells)

if __name__ == "__main__":
    main()
