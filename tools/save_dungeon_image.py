#!/usr/bin/env python3
"""
Save dungeon map as PNG image.
"""

import sys
from pathlib import Path

try:
    import pygame
except ImportError:
    print("Error: pygame not installed. Install with: pip install pygame")
    sys.exit(1)

def read_map_data(filepath, start_offset=0):
    """Read map cell data."""
    with open(filepath, 'rb') as f:
        f.seek(start_offset)
        data = f.read(400 * 8)

    cells = []
    for i in range(400):
        cell_data = data[i*8:(i+1)*8]
        cells.append(cell_data if len(cell_data) == 8 else bytes([0] * 8))

    return cells

def get_walls(cell_data):
    """Get wall flags for a cell."""
    byte_3 = cell_data[3]
    byte_5 = cell_data[5]

    return {
        'N': bool(byte_3 & 0x80),
        'S': bool(byte_3 & 0x40),
        'E': bool(byte_5 & 0x80),
        'W': bool(byte_5 & 0x20),
    }

def save_dungeon_image(cells, output_path, cell_size=32):
    """Save dungeon map as PNG image."""

    pygame.init()

    # Map dimensions
    map_width = 20
    map_height = 20

    # Calculate image size (add padding for labels)
    padding = 40
    width = map_width * cell_size + padding * 2
    height = map_height * cell_size + padding * 2

    # Create surface
    surface = pygame.Surface((width, height))

    # Colors
    COLOR_BG = (240, 240, 240)
    COLOR_WALL = (0, 0, 0)
    COLOR_GRID = (200, 200, 200)
    COLOR_TEXT = (0, 0, 0)
    COLOR_SPECIAL = (255, 0, 0)
    COLOR_CHANGED = (255, 200, 200)

    # Font
    font = pygame.font.Font(None, 20)
    font_small = pygame.font.Font(None, 16)

    # Clear background
    surface.fill(COLOR_BG)

    # Draw title
    title = font.render("Wizardry 6 - Castle Level 1", True, COLOR_TEXT)
    surface.blit(title, (padding, 10))

    # Draw grid lines
    for row in range(map_height + 1):
        y = padding + row * cell_size
        pygame.draw.line(surface, COLOR_GRID, (padding, y), (padding + map_width * cell_size, y), 1)

    for col in range(map_width + 1):
        x = padding + col * cell_size
        pygame.draw.line(surface, COLOR_GRID, (x, padding), (x, padding + map_height * cell_size), 1)

    # Draw cells
    for row in range(map_height):
        for col in range(map_width):
            cell_idx = row * 20 + col
            cell_data = cells[cell_idx]

            byte_0 = cell_data[0]

            # Cell position
            x = padding + col * cell_size
            y = padding + row * cell_size

            # Highlight changed cells
            if (row, col) in [(3, 15), (4, 19)]:
                pygame.draw.rect(surface, COLOR_CHANGED, (x + 1, y + 1, cell_size - 1, cell_size - 1))

            # Get walls
            walls = get_walls(cell_data)

            # Draw walls
            wall_thickness = 3

            if walls['N']:
                pygame.draw.line(surface, COLOR_WALL,
                               (x, y), (x + cell_size, y),
                               wall_thickness)

            if walls['S']:
                pygame.draw.line(surface, COLOR_WALL,
                               (x, y + cell_size), (x + cell_size, y + cell_size),
                               wall_thickness)

            if walls['W']:
                pygame.draw.line(surface, COLOR_WALL,
                               (x, y), (x, y + cell_size),
                               wall_thickness)

            if walls['E']:
                pygame.draw.line(surface, COLOR_WALL,
                               (x + cell_size, y), (x + cell_size, y + cell_size),
                               wall_thickness)

            # Draw special tile markers
            if byte_0 == 0x02:
                center_x = x + cell_size // 2
                center_y = y + cell_size // 2
                pygame.draw.circle(surface, COLOR_SPECIAL, (center_x, center_y), 3)

    # Draw row numbers
    for row in range(map_height):
        y = padding + row * cell_size + cell_size // 2
        text = font_small.render(f"{row}", True, COLOR_TEXT)
        surface.blit(text, (5, y - 8))

    # Draw column numbers
    for col in range(map_width):
        x = padding + col * cell_size + cell_size // 2
        text = font_small.render(f"{col}", True, COLOR_TEXT)
        surface.blit(text, (x - 4, padding - 25))

    # Draw legend
    legend_y = height - 30
    legend_x = padding

    pygame.draw.line(surface, COLOR_WALL, (legend_x, legend_y + 10), (legend_x + 30, legend_y + 10), 3)
    text = font_small.render("= Walls", True, COLOR_TEXT)
    surface.blit(text, (legend_x + 35, legend_y + 3))

    legend_x += 130
    pygame.draw.circle(surface, COLOR_SPECIAL, (legend_x + 10, legend_y + 10), 3)
    text = font_small.render("= Special tile", True, COLOR_TEXT)
    surface.blit(text, (legend_x + 25, legend_y + 3))

    legend_x += 150
    pygame.draw.rect(surface, COLOR_CHANGED, (legend_x, legend_y, 20, 20))
    text = font_small.render("= Changed cells", True, COLOR_TEXT)
    surface.blit(text, (legend_x + 25, legend_y + 3))

    # Save image
    pygame.image.save(surface, str(output_path))
    print(f"Map saved to: {output_path}")

    pygame.quit()

def main():
    filepath = Path("gamedata/newgameold.dbs")
    output = Path("wizardry6_map.png")

    if not filepath.exists():
        print(f"Error: {filepath} not found")
        sys.exit(1)

    print("Loading Wizardry 6 map data...")
    cells = read_map_data(filepath)

    print("Rendering map to image...")
    save_dungeon_image(cells, output)

    print("\nDone! View the image at: wizardry6_map.png")

if __name__ == "__main__":
    main()
