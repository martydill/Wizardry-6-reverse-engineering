#!/usr/bin/env python3
"""
Wizardry 6 - Render ALL Walls
Scans all cells and renders all walls found, showing the actual map data.
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

def scan_all_walls(cells):
    """
    Scan ALL cells for wall data and try to render them.

    We know:
    - Odd bytes (1,3,5,7,9,11,13,15,17,19) store walls
    - Bit 5 = left position
    - Bit 7 = right position
    - Byte position relates to Y-coordinate

    But we don't know the complete cell->coordinate mapping yet.
    So we'll render walls based on the file structure itself.
    """
    # Map: file_row -> file_col -> walls
    # We'll render based on FILE coordinates, not game coordinates
    wall_map = [[{'N': False, 'S': False, 'E': False, 'W': False}
                 for _ in range(20)] for _ in range(20)]

    print("Scanning all cells for walls...")

    cells_with_walls = 0
    total_wall_bits = 0

    # Scan each cell
    for cell_idx in range(400):
        file_col = cell_idx // 20  # Column-major
        file_row = cell_idx % 20

        cell = cells[cell_idx]
        cell_has_walls = False

        # Check all ODD bytes for wall bits
        for byte_idx in range(1, 20, 2):
            byte_val = cell[byte_idx]

            if byte_val & 0xA0:  # Has bit 5 or 7
                cell_has_walls = True

                # For rendering, mark walls in this cell
                # We'll use a simple heuristic:
                if byte_val & 0x20:  # Bit 5 = left/west
                    wall_map[file_row][file_col]['W'] = True
                    total_wall_bits += 1

                if byte_val & 0x80:  # Bit 7 = right/east
                    wall_map[file_row][file_col]['E'] = True
                    total_wall_bits += 1

        if cell_has_walls:
            cells_with_walls += 1

    print(f"Cells with walls: {cells_with_walls}/400")
    print(f"Total wall bits: {total_wall_bits}")

    return wall_map

def render_map(cells, cell_size=32):
    """Render all walls found in the file."""

    pygame.init()

    map_width = 20
    map_height = 20

    padding = 60
    window_width = map_width * cell_size + padding * 2
    window_height = map_height * cell_size + padding * 2 + 140

    screen = pygame.display.set_mode((window_width, window_height))
    pygame.display.set_caption("Wizardry 6 - All Walls (File View)")

    # Colors
    COLOR_BG = (245, 245, 240)
    COLOR_FLOOR = (220, 220, 210)
    COLOR_WALL = (60, 60, 60)
    COLOR_GRID = (200, 200, 195)
    COLOR_TEXT = (0, 0, 0)
    COLOR_HAS_WALLS = (255, 250, 220)  # Light yellow for cells with walls

    font = pygame.font.Font(None, 24)
    font_small = pygame.font.Font(None, 18)

    print("Scanning for walls...")
    wall_map = scan_all_walls(cells)

    # Count cells with walls
    cells_with_walls = sum(1 for row in range(20) for col in range(20)
                          if any(wall_map[row][col].values()))

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
        title = font.render("Wizardry 6 - All Walls (File Coordinates)", True, COLOR_TEXT)
        screen.blit(title, (padding, 10))

        subtitle = font_small.render("Showing file structure, not game coordinates", True, COLOR_TEXT)
        screen.blit(subtitle, (padding, 35))

        # Draw floor
        for row in range(map_height):
            for col in range(map_width):
                x = padding + col * cell_size
                y = padding + row * cell_size

                # Highlight cells that have walls
                has_walls = any(wall_map[row][col].values())
                color = COLOR_HAS_WALLS if has_walls else COLOR_FLOOR

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
        wall_thickness = 3

        for row in range(map_height):
            for col in range(map_width):
                x = padding + col * cell_size
                y = padding + row * cell_size

                walls = wall_map[row][col]

                if walls['W']:
                    pygame.draw.line(screen, COLOR_WALL,
                                   (x, y), (x, y + cell_size),
                                   wall_thickness)

                if walls['E']:
                    pygame.draw.line(screen, COLOR_WALL,
                                   (x + cell_size, y),
                                   (x + cell_size, y + cell_size),
                                   wall_thickness)

        # Labels
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
            f"Cells with wall data: {cells_with_walls}/400",
            "Yellow cells = contain wall bits (5 or 7)",
            "This shows FILE structure, not final game map",
            "",
            "We need the complete cell->coordinate formula to map correctly!",
            f"Grid: {'ON' if show_grid else 'OFF'} (G) | ESC/Q: Quit"
        ]

        for i, line in enumerate(info):
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

    print("Wizardry 6 - All Walls Renderer")
    print("="*60)
    print()
    print("This scans ALL cells and renders all wall bits found.")
    print("Note: This shows FILE structure, not game coordinates!")
    print()

    cells = read_map_data(filepath)
    render_map(cells)

if __name__ == "__main__":
    main()
