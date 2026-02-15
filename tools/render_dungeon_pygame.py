#!/usr/bin/env python3
"""
Pygame dungeon map renderer with 64x64 pixel cells.
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

def render_dungeon_pygame(cells, cell_size=32):
    """Render dungeon using pygame."""

    # Initialize pygame
    pygame.init()

    # Map dimensions
    map_width = 20
    map_height = 20

    # Calculate window size (add padding for labels)
    padding = 40
    window_width = map_width * cell_size + padding * 2
    window_height = map_height * cell_size + padding * 2

    # Create window
    screen = pygame.display.set_mode((window_width, window_height))
    pygame.display.set_caption("Wizardry 6 - Castle Level 1")

    # Colors
    COLOR_BG = (240, 240, 240)         # Light gray background
    COLOR_WALL = (0, 0, 0)             # Black walls
    COLOR_GRID = (200, 200, 200)       # Light gray grid
    COLOR_TEXT = (0, 0, 0)             # Black text
    COLOR_SPECIAL = (255, 0, 0)        # Red for special tiles
    COLOR_CHANGED = (255, 200, 200)    # Light red for changed cells

    # Font
    font = pygame.font.Font(None, 20)
    font_small = pygame.font.Font(None, 16)

    # Main loop
    clock = pygame.time.Clock()
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE or event.key == pygame.K_q:
                    running = False

        # Clear screen
        screen.fill(COLOR_BG)

        # Draw title
        title = font.render("Wizardry 6 - Castle Level 1", True, COLOR_TEXT)
        screen.blit(title, (padding, 10))

        # Draw grid lines
        for row in range(map_height + 1):
            y = padding + row * cell_size
            pygame.draw.line(screen, COLOR_GRID, (padding, y), (padding + map_width * cell_size, y), 1)

        for col in range(map_width + 1):
            x = padding + col * cell_size
            pygame.draw.line(screen, COLOR_GRID, (x, padding), (x, padding + map_height * cell_size), 1)

        # Draw cells
        for row in range(map_height):
            for col in range(map_width):
                cell_idx = row * 20 + col
                cell_data = cells[cell_idx]

                byte_0 = cell_data[0]
                byte_3 = cell_data[3]
                byte_5 = cell_data[5]

                # Cell position
                x = padding + col * cell_size
                y = padding + row * cell_size

                # Highlight changed cells with light background
                if (row, col) in [(3, 15), (4, 19)]:
                    pygame.draw.rect(screen, COLOR_CHANGED, (x + 1, y + 1, cell_size - 1, cell_size - 1))

                # Get walls
                walls = get_walls(cell_data)

                # Draw walls (thick black lines)
                wall_thickness = 3

                if walls['N']:
                    pygame.draw.line(screen, COLOR_WALL,
                                   (x, y), (x + cell_size, y),
                                   wall_thickness)

                if walls['S']:
                    pygame.draw.line(screen, COLOR_WALL,
                                   (x, y + cell_size), (x + cell_size, y + cell_size),
                                   wall_thickness)

                if walls['W']:
                    pygame.draw.line(screen, COLOR_WALL,
                                   (x, y), (x, y + cell_size),
                                   wall_thickness)

                if walls['E']:
                    pygame.draw.line(screen, COLOR_WALL,
                                   (x + cell_size, y), (x + cell_size, y + cell_size),
                                   wall_thickness)

                # Draw special tile markers (small red dot in center)
                if byte_0 == 0x02:
                    center_x = x + cell_size // 2
                    center_y = y + cell_size // 2
                    pygame.draw.circle(screen, COLOR_SPECIAL, (center_x, center_y), 3)

        # Draw row numbers
        for row in range(map_height):
            y = padding + row * cell_size + cell_size // 2
            text = font_small.render(f"{row}", True, COLOR_TEXT)
            screen.blit(text, (5, y - 8))

        # Draw column numbers
        for col in range(map_width):
            x = padding + col * cell_size + cell_size // 2
            text = font_small.render(f"{col}", True, COLOR_TEXT)
            screen.blit(text, (x - 4, padding - 25))

        # Draw legend
        legend_y = window_height - 30
        legend_x = padding

        # Walls
        pygame.draw.line(screen, COLOR_WALL, (legend_x, legend_y + 10), (legend_x + 30, legend_y + 10), 3)
        text = font_small.render("= Walls", True, COLOR_TEXT)
        screen.blit(text, (legend_x + 35, legend_y + 3))

        # Special
        legend_x += 130
        pygame.draw.circle(screen, COLOR_SPECIAL, (legend_x + 10, legend_y + 10), 3)
        text = font_small.render("= Special tile", True, COLOR_TEXT)
        screen.blit(text, (legend_x + 25, legend_y + 3))

        # Changed
        legend_x += 150
        pygame.draw.rect(screen, COLOR_CHANGED, (legend_x, legend_y, 20, 20))
        text = font_small.render("= Changed cells", True, COLOR_TEXT)
        screen.blit(text, (legend_x + 25, legend_y + 3))

        # Instructions
        info = font_small.render("Press ESC or Q to quit", True, COLOR_TEXT)
        screen.blit(info, (window_width - 180, 10))

        # Update display
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

def main():
    filepath = Path("gamedata/newgameold.dbs")

    if not filepath.exists():
        print(f"Error: {filepath} not found")
        sys.exit(1)

    print("Loading Wizardry 6 map data...")
    cells = read_map_data(filepath)

    print("Starting pygame renderer...")
    print("Controls:")
    print("  ESC or Q - Quit")
    print()
    print("Map features:")
    print("  - Each cell is 32x32 pixels")
    print("  - Walls drawn as thick black lines between cells")
    print("  - Special tiles marked with small red dots")
    print("  - Changed cells (3,15) and (4,19) highlighted")
    print()

    render_dungeon_pygame(cells)

if __name__ == "__main__":
    main()
